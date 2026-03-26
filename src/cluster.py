import os
import json
import re
import hashlib
import tempfile
from pathlib import Path

import anthropic

CLUSTER_MODEL = "claude-sonnet-4-6"
BATCH_SIZE = 100
SNIPPET_LEN = 500

# GUARDRAIL: Maximum clusters allowed in a single consolidation call.
# Exceeding this triggers hierarchical consolidation automatically.
# Root cause of $4 / 1.5hr failure on 2026-03-27: 214 clusters sent in one call
# exceeded max_tokens=8096, truncating the JSON mid-stream and crashing the parse.
# Never raise this above 30 without re-testing. Each cluster ~400 tokens in output.
MAX_CLUSTERS_PER_CONSOLIDATION = 30

_CACHE_DIR = Path(__file__).parent.parent / ".batch_cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _cache_key(pattern: str, total: int) -> str:
    h = hashlib.md5(f"{pattern}:{total}:{CLUSTER_MODEL}".encode()).hexdigest()[:12]
    return str(_CACHE_DIR / f"batches_{h}.json")


def _load_cache(key: str):
    p = Path(key)
    if p.exists():
        return json.loads(p.read_text())
    return None


def _save_cache(key: str, data):
    Path(key).write_text(json.dumps(data))


def _make_cluster_prompt(pattern: str, snippets: list[dict]) -> str:
    return (
        f"You are analyzing consumer complaints to identify thematic clusters and generate "
        f"root-cause hypotheses for a product team.\n\n"
        f"Support pattern under investigation: \"{pattern}\"\n\n"
        f"Below are consumer complaint excerpts. Group them into thematic clusters. "
        f"For each cluster:\n"
        f"- Give it a short descriptive name\n"
        f"- Write a 1-2 sentence description of the common thread\n"
        f"- List the complaint indices (from the 'idx' field) that belong to this cluster\n"
        f"- Generate 1-3 root-cause hypotheses. Each hypothesis MUST begin with one of: "
        f"\"This may indicate\", \"Evidence suggests\", or \"This pattern is consistent with\". "
        f"Never state a root cause as a fact or conclusion.\n\n"
        f"Complaints:\n{json.dumps(snippets, indent=2)}\n\n"
        f"Return ONLY valid JSON — an array of cluster objects with this exact shape:\n"
        f"[\n"
        f"  {{\n"
        f"    \"name\": \"...\",\n"
        f"    \"description\": \"...\",\n"
        f"    \"complaint_indices\": [0, 3, 7],\n"
        f"    \"hypotheses\": [\"This may indicate...\", \"Evidence suggests...\"]\n"
        f"  }}\n"
        f"]\n"
        f"No markdown fences, no commentary — raw JSON only."
    )


def _make_consolidation_prompt(pattern: str, slim_clusters: list[dict]) -> str:
    """
    Consolidation input strips complaint_indices to keep token count manageable.
    complaint_indices are rebuilt programmatically after merging via source_names.
    """
    return (
        f"You are consolidating complaint clusters from multiple batches into a final set "
        f"of distinct thematic clusters.\n\n"
        f"Support pattern: \"{pattern}\"\n\n"
        f"Below are clusters generated from separate batches (complaint indices omitted). "
        f"Merge clusters that cover the same theme. Preserve the strongest hypotheses. "
        f"For each merged cluster, list the exact original cluster names that were merged "
        f"into it (field: 'source_names') so indices can be reconstructed.\n\n"
        f"Input clusters:\n{json.dumps(slim_clusters, indent=2)}\n\n"
        f"Return ONLY valid JSON — an array of merged cluster objects with this shape:\n"
        f"[\n"
        f"  {{\n"
        f"    \"name\": \"...\",\n"
        f"    \"description\": \"...\",\n"
        f"    \"source_names\": [\"Exact Original Name A\", \"Exact Original Name B\"],\n"
        f"    \"hypotheses\": [\"This may indicate...\", \"Evidence suggests...\"]\n"
        f"  }}\n"
        f"]\n"
        f"No markdown fences, no commentary — raw JSON only."
    )


def _parse_json(raw: str) -> list[dict]:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


def _call_model(prompt: str, client: anthropic.Anthropic, max_tokens: int = 4096) -> list[dict]:
    response = client.messages.create(
        model=CLUSTER_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text
    # GUARDRAIL: detect truncation before attempting parse
    if response.stop_reason == "max_tokens":
        raise ValueError(
            f"Consolidation response hit max_tokens={max_tokens} and was truncated. "
            f"Reduce input cluster count or raise max_tokens. "
            f"Never send more than {MAX_CLUSTERS_PER_CONSOLIDATION} clusters per consolidation call."
        )
    return _parse_json(raw)


def _consolidate(pattern: str, slim_clusters: list[dict], client: anthropic.Anthropic) -> list[dict]:
    """
    Hierarchical consolidation: if slim_clusters exceeds MAX_CLUSTERS_PER_CONSOLIDATION,
    split into sub-groups, consolidate each, then do one final pass.
    Prevents the max_tokens truncation failure that caused the $4 / 1.5hr incident.
    """
    n = len(slim_clusters)

    if n <= MAX_CLUSTERS_PER_CONSOLIDATION:
        prompt = _make_consolidation_prompt(pattern, slim_clusters)
        return _call_model(prompt, client, max_tokens=4096)

    # Split into sub-groups and consolidate each
    sub_groups = [
        slim_clusters[i:i + MAX_CLUSTERS_PER_CONSOLIDATION]
        for i in range(0, n, MAX_CLUSTERS_PER_CONSOLIDATION)
    ]
    print(f"  Hierarchical consolidation: {n} clusters → {len(sub_groups)} sub-groups of ≤{MAX_CLUSTERS_PER_CONSOLIDATION}...")

    intermediate = []
    for g_idx, group in enumerate(sub_groups):
        print(f"    Sub-group {g_idx + 1}/{len(sub_groups)} ({len(group)} clusters)...")
        prompt = _make_consolidation_prompt(pattern, group)
        result = _call_model(prompt, client, max_tokens=4096)
        # Keep slim for the next pass
        intermediate.extend([
            {"name": c["name"], "description": c["description"], "hypotheses": c["hypotheses"]}
            for c in result
        ])

    print(f"  Final consolidation pass ({len(intermediate)} intermediate clusters)...")
    prompt = _make_consolidation_prompt(pattern, intermediate)
    return _call_model(prompt, client, max_tokens=4096)


def _rebuild_indices(merged_clusters: list[dict], batch_clusters: list[list[dict]]) -> list[dict]:
    """
    Map complaint_indices back onto merged clusters using source_names.
    Walks the full name chain: final cluster → intermediate → original batch clusters.
    """
    name_to_indices: dict[str, set] = {}
    for batch in batch_clusters:
        for c in batch:
            name = c["name"]
            indices = set(c.get("complaint_indices", []))
            if name in name_to_indices:
                name_to_indices[name].update(indices)
            else:
                name_to_indices[name] = indices

    for merged in merged_clusters:
        gathered = set()
        for src_name in merged.get("source_names", []):
            gathered.update(name_to_indices.get(src_name, set()))
        if not gathered:
            gathered.update(name_to_indices.get(merged["name"], set()))
        merged["complaint_indices"] = sorted(gathered)

    return merged_clusters


def cluster_complaints(pattern: str, df, client: anthropic.Anthropic = None) -> list[dict]:
    """
    Cluster filtered complaints and generate root-cause hypotheses.

    Returns list of cluster dicts: {name, description, complaint_indices, hypotheses, complaint_count}
    """
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY environment variable not set.")
        client = anthropic.Anthropic(api_key=api_key)

    narratives = df["Consumer complaint narrative"].tolist()
    total = len(narratives)
    print(f"  Clustering {total:,} complaints via {CLUSTER_MODEL}...")

    snippets = [
        {"idx": i, "text": str(narratives[i])[:SNIPPET_LEN]}
        for i in range(total)
    ]

    if total <= BATCH_SIZE:
        prompt = _make_cluster_prompt(pattern, snippets)
        clusters = _call_model(prompt, client)
    else:
        cache_key = _cache_key(pattern, total)
        cached = _load_cache(cache_key)
        if cached:
            print(f"  Loaded batch clusters from cache (skipping API calls).")
            batch_clusters = cached
        else:
            batches = [snippets[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
            print(f"  Splitting into {len(batches)} batches of ~{BATCH_SIZE}...")
            batch_clusters = []
            for b_idx, batch in enumerate(batches):
                print(f"    Batch {b_idx + 1}/{len(batches)}...")
                prompt = _make_cluster_prompt(pattern, batch)
                batch_result = _call_model(prompt, client)
                batch_clusters.append(batch_result)
            _save_cache(cache_key, batch_clusters)
            print(f"  Batch results cached.")

        slim = [
            {"name": c["name"], "description": c["description"], "hypotheses": c["hypotheses"]}
            for batch in batch_clusters for c in batch
        ]
        raw_count = len(slim)

        # GUARDRAIL: log cluster count so oversized consolidations are visible
        print(f"  {raw_count} raw clusters to consolidate (limit per call: {MAX_CLUSTERS_PER_CONSOLIDATION})")
        if raw_count > MAX_CLUSTERS_PER_CONSOLIDATION:
            print(f"  ⚠ Exceeds single-call limit — using hierarchical consolidation to avoid token truncation.")

        merged = _consolidate(pattern, slim, client)
        clusters = _rebuild_indices(merged, batch_clusters)

    for c in clusters:
        c["complaint_count"] = len(c.get("complaint_indices", []))

    clusters.sort(key=lambda c: c["complaint_count"], reverse=True)

    return clusters
