import os
import json
import re
import hashlib
from collections import Counter
from pathlib import Path

import anthropic

CLUSTER_MODEL = "claude-sonnet-4-6"
BATCH_SIZE = 100
SNIPPET_LEN = 500
DESCRIPTION_SNIPPET_LEN = 140
OVER_AGGREGATION_WARN_THRESHOLD = 0.5
HYPOTHESIS_PREFIXES = (
    "This may indicate",
    "Evidence suggests",
    "This pattern is consistent with",
)

# GUARDRAIL: Maximum clusters allowed in a single consolidation call.
# Exceeding this triggers hierarchical consolidation automatically.
# Root cause of $4 / 1.5hr failure on 2026-03-27: 214 clusters sent in one call
# exceeded max_tokens=8096, truncating the JSON mid-stream and crashing the parse.
# Lowered to 15 (was 20) after recursive passes still hit max_tokens — accumulated
# hypotheses across merge levels caused output bloat. Each cluster ~400 tokens in output.
# Never raise above 15 without re-testing on a large dataset.
MAX_CLUSTERS_PER_CONSOLIDATION = 15

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


def _assign_cluster_ids(clusters: list[dict], batch_idx: int) -> list[dict]:
    for cluster_idx, cluster in enumerate(clusters):
        cluster["cluster_id"] = f"b{batch_idx:02d}_c{cluster_idx:02d}"
    return clusters


def _prepare_description(raw_description: str) -> str:
    description = str(raw_description).strip()
    if not description:
        raise ValueError("Raw cluster description is missing or blank before consolidation.")
    return description[:DESCRIPTION_SNIPPET_LEN]


def _validate_raw_clusters(batch_clusters: list[list[dict]]) -> list[str]:
    raw_cluster_ids: list[str] = []
    for batch in batch_clusters:
        for cluster in batch:
            cluster_id = cluster.get("cluster_id")
            if not isinstance(cluster_id, str) or not cluster_id.strip():
                raise ValueError("Every raw cluster must have a non-empty cluster_id before consolidation.")
            raw_cluster_ids.append(cluster_id)

    if len(set(raw_cluster_ids)) != len(raw_cluster_ids):
        raise ValueError("Duplicate raw cluster_id detected before consolidation.")

    return raw_cluster_ids


def _validate_merged_clusters(merged_clusters: list[dict], raw_cluster_ids: list[str]) -> None:
    if not isinstance(merged_clusters, list):
        raise ValueError("Consolidation output must be a list of merged theme objects.")

    raw_cluster_id_set = set(raw_cluster_ids)
    assigned_cluster_ids: list[str] = []
    total_raw_clusters = len(raw_cluster_ids)

    print(f"  total raw clusters: {total_raw_clusters}")
    print(f"  total merged clusters: {len(merged_clusters)}")

    # NOTE: Keeping exact-15 behavior for now to match current product behavior,
    # though a fixed target may degrade clustering quality when the natural number differs.
    if len(merged_clusters) != MAX_CLUSTERS_PER_CONSOLIDATION:
        raise ValueError(
            f"Consolidation must return exactly {MAX_CLUSTERS_PER_CONSOLIDATION} themes; "
            f"got {len(merged_clusters)}."
        )

    for idx, merged in enumerate(merged_clusters):
        name = merged.get("name")
        description = merged.get("description")
        cluster_ids = merged.get("cluster_ids")
        hypotheses = merged.get("hypotheses")

        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"Merged theme {idx} is missing a non-empty name.")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Merged theme '{name}' is missing a non-empty description.")
        if not isinstance(cluster_ids, list) or not cluster_ids:
            raise ValueError(f"Merged theme '{name}' must include a non-empty cluster_ids list.")
        if any(not isinstance(cluster_id, str) or not cluster_id.strip() for cluster_id in cluster_ids):
            raise ValueError(f"Merged theme '{name}' contains an invalid cluster_id.")
        if not isinstance(hypotheses, list) or not hypotheses:
            raise ValueError(f"Merged theme '{name}' must include a non-empty hypotheses list.")
        if any(not isinstance(h, str) or not h.strip() for h in hypotheses):
            raise ValueError(f"Merged theme '{name}' contains an empty or non-string hypothesis.")

        for hypothesis in hypotheses:
            if not hypothesis.startswith(HYPOTHESIS_PREFIXES):
                print(f"  Warning: hypothesis prefix mismatch in theme '{name}': {hypothesis}")

        if len(cluster_ids) == 1:
            print(f"  Warning: theme '{name}' has a single cluster_id and may be under-clustered.")

        share = len(cluster_ids) / total_raw_clusters if total_raw_clusters else 0
        if share > OVER_AGGREGATION_WARN_THRESHOLD:
            print(
                f"  Warning: theme '{name}' owns {len(cluster_ids)}/{total_raw_clusters} raw clusters "
                f"({share:.1%}), which may indicate over-aggregation."
            )

        assigned_cluster_ids.extend(cluster_ids)

    assigned_cluster_id_set = set(assigned_cluster_ids)
    cluster_id_counts = Counter(assigned_cluster_ids)
    duplicate_cluster_ids = sorted(
        cluster_id for cluster_id, count in cluster_id_counts.items() if count > 1
    )
    unknown_cluster_ids = sorted(assigned_cluster_id_set - raw_cluster_id_set)
    missing_cluster_ids = sorted(raw_cluster_id_set - assigned_cluster_id_set)

    if duplicate_cluster_ids:
        print(
            f"  cluster_id coverage: FAILED ({len(assigned_cluster_id_set)}/{len(raw_cluster_id_set)} assigned)."
        )
        raise ValueError(f"Consolidation assigned cluster_ids multiple times: {duplicate_cluster_ids}")
    if unknown_cluster_ids:
        print(
            f"  cluster_id coverage: FAILED ({len(assigned_cluster_id_set)}/{len(raw_cluster_id_set)} assigned)."
        )
        raise ValueError(f"Consolidation returned unknown cluster_ids: {unknown_cluster_ids}")
    if missing_cluster_ids:
        print(
            f"  cluster_id coverage: FAILED ({len(assigned_cluster_id_set)}/{len(raw_cluster_id_set)} assigned)."
        )
        raise ValueError(f"Consolidation omitted raw cluster_ids: {missing_cluster_ids}")
    if len(assigned_cluster_id_set) != len(raw_cluster_id_set):
        print(
            f"  cluster_id coverage: FAILED ({len(assigned_cluster_id_set)}/{len(raw_cluster_id_set)} assigned)."
        )
        raise ValueError("Consolidation cluster_id coverage does not match raw cluster count.")

    print(f"  cluster_id coverage: OK ({len(raw_cluster_id_set)}/{len(raw_cluster_id_set)} assigned exactly once)")


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


def _make_consolidation_prompt(pattern: str, name_clusters: list[dict]) -> str:
    """
    Names-only consolidation prompt. Input is stripped to name + 80-char description.
    No hypotheses in input — model generates fresh ones from descriptions.
    Asks for EXACTLY 15 output clusters to force aggressive merging and bound output tokens.
    Output: ~15 clusters × ~300 tokens (inc. source_names lists) = ~4-5k tokens. Use max_tokens=8096.
    """
    all_ids = [c["cluster_id"] for c in name_clusters]
    return (
        f"You are consolidating {len(name_clusters)} complaint cluster names into exactly 15 distinct themes.\n\n"
        f"Support pattern: \"{pattern}\"\n\n"
        f"Below are cluster IDs, names, and brief descriptions from separate analysis batches. "
        f"Merge clusters that cover the same theme into one. "
        f"You MUST produce EXACTLY 15 output clusters — merge aggressively.\n\n"
        f"STRICT RULES — violating any of these makes the output invalid:\n"
        f"1. Every cluster_id in the input list MUST appear in exactly one output theme's cluster_ids array.\n"
        f"2. No cluster_id may appear in more than one theme.\n"
        f"3. Do not invent, modify, or abbreviate cluster_ids — copy them verbatim.\n"
        f"4. The union of all output cluster_ids arrays must equal the full input list exactly.\n\n"
        f"Complete list of all {len(all_ids)} cluster_ids you must assign (each exactly once):\n"
        f"{json.dumps(all_ids)}\n\n"
        f"For each output cluster:\n"
        f"- Give it a clear, specific name\n"
        f"- Write a 1-2 sentence description of the common thread\n"
        f"- List the exact input cluster_ids merged into it (field: 'cluster_ids')\n"
        f"- Generate 2 root-cause hypotheses. Each MUST begin with one of: "
        f"\"This may indicate\", \"Evidence suggests\", or \"This pattern is consistent with\".\n\n"
        f"Input clusters:\n{json.dumps(name_clusters, indent=2)}\n\n"
        f"Return ONLY valid JSON — an array of exactly 15 cluster objects:\n"
        f"[\n"
        f"  {{\n"
        f"    \"name\": \"...\",\n"
        f"    \"description\": \"...\",\n"
        f"    \"cluster_ids\": [\"b00_c00\", \"b00_c01\"],\n"
        f"    \"hypotheses\": [\"This may indicate...\", \"Evidence suggests...\"]\n"
        f"  }}\n"
        f"]\n"
        f"No markdown fences, no commentary — raw JSON only. Exactly 15 objects."
    )


def _get_bad_cluster_ids(broken_merged: list[dict], raw_cluster_ids: list[str]) -> list[str]:
    """Return the sorted union of duplicated and missing cluster_ids."""
    assigned = [cid for m in broken_merged for cid in m.get("cluster_ids", [])]
    counts = Counter(assigned)
    duplicates = {cid for cid, n in counts.items() if n > 1}
    missing = set(raw_cluster_ids) - set(assigned)
    return sorted(duplicates | missing)


def _make_repair_prompt(broken_merged: list[dict], bad_cluster_ids: list[str]) -> str:
    """
    Targeted repair prompt. Asks Claude only to assign each bad cluster_id
    (duplicated or missing) to one theme index. Output is minimal:
    [{"cluster_id": "b00_c00", "theme_i": 3}, ...]
    Claude never touches correctly assigned cluster_ids.
    """
    themes = [
        {"i": i, "name": m["name"], "description": m.get("description", "")[:80]}
        for i, m in enumerate(broken_merged)
    ]
    return (
        f"Assign each cluster_id below to exactly one theme index. "
        f"Return ONLY a JSON array. No prose, no markdown, no explanation.\n\n"
        f"cluster_ids to assign: {json.dumps(bad_cluster_ids)}\n\n"
        f"Available themes:\n{json.dumps(themes, indent=2)}\n\n"
        f"Return exactly {len(bad_cluster_ids)} objects:\n"
        f"[{{\"cluster_id\": \"b00_c00\", \"theme_i\": 3}}, ...]"
    )


def _validate_repair_mapping(
    repair_result: list[dict],
    bad_cluster_ids: list[str],
    n_themes: int,
) -> None:
    """Validate that repair_result is a well-formed list of {cluster_id, theme_i} mappings."""
    if not isinstance(repair_result, list):
        raise ValueError("Repair result must be a JSON array.")
    bad_set = set(bad_cluster_ids)
    seen = set()
    for item in repair_result:
        cid = item.get("cluster_id")
        theme_i = item.get("theme_i")
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError(f"Repair mapping entry has invalid cluster_id: {cid!r}")
        if cid not in bad_set:
            raise ValueError(f"Repair mapping contains unknown cluster_id: {cid!r}")
        if cid in seen:
            raise ValueError(f"Repair mapping assigns cluster_id more than once: {cid!r}")
        if not isinstance(theme_i, int) or not (0 <= theme_i < n_themes):
            raise ValueError(f"Repair mapping for {cid!r} has invalid theme_i: {theme_i!r}")
        seen.add(cid)
    unassigned = sorted(bad_set - seen)
    if unassigned:
        raise ValueError(f"Repair mapping did not assign these cluster_ids: {unassigned}")


def _apply_repair_mapping(
    broken_merged: list[dict],
    repair_result: list[dict],
    bad_cluster_ids: list[str],
) -> list[dict]:
    """
    Apply a targeted repair mapping onto broken_merged:
    1. Strip all bad cluster_ids from every theme (removes duplicates; missing ones aren't present).
    2. Append each bad cluster_id to its assigned theme.
    Correctly assigned cluster_ids are never touched.
    """
    bad_set = set(bad_cluster_ids)
    for theme in broken_merged:
        theme["cluster_ids"] = [cid for cid in theme.get("cluster_ids", []) if cid not in bad_set]
    for item in repair_result:
        broken_merged[item["theme_i"]]["cluster_ids"].append(item["cluster_id"])
    return broken_merged


def _strip_json_fences(raw: str) -> str:
    stripped = raw.strip()
    stripped = re.sub(r'^```(?:json)?\s*', '', stripped)
    stripped = re.sub(r'\s*```$', '', stripped)
    return stripped


def _preview_text(raw: str, limit: int = 200) -> str:
    return raw.strip().replace("\n", "\\n")[:limit]


def _parse_json(raw: str) -> list[dict]:
    raw = _strip_json_fences(raw)
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


def _call_model_raw(prompt: str, client: anthropic.Anthropic, max_tokens: int = 4096) -> tuple[str, str | None]:
    """Like _call_model but returns raw text and stop_reason without parsing."""
    response = client.messages.create(
        model=CLUSTER_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "max_tokens":
        raise ValueError(
            f"Repair response hit max_tokens={max_tokens} and was truncated."
        )
    return response.content[0].text, response.stop_reason


def _consolidate(pattern: str, batch_clusters: list[list[dict]], client: anthropic.Anthropic) -> list[dict]:
    """
    Single-pass names-only consolidation. Strips all input clusters to name + 80-char
    description before sending — no hypotheses, no indices. Output is bounded at ~3k tokens
    (15 clusters × ~200 tokens), so max_tokens is never an issue regardless of input size.
    On cluster_id coverage failure, retries once with a targeted repair prompt.
    """
    raw_cluster_ids = _validate_raw_clusters(batch_clusters)
    name_only = [
        {
            "cluster_id": c["cluster_id"],
            "name": c["name"],
            "description": _prepare_description(c["description"]),
        }
        for batch in batch_clusters for c in batch
    ]
    n = len(name_only)
    print(f"  Consolidating {n} raw clusters → 15 themes (single call, names-only)...")
    prompt = _make_consolidation_prompt(pattern, name_only)
    merged = _call_model(prompt, client, max_tokens=8096)

    try:
        _validate_merged_clusters(merged, raw_cluster_ids)
    except ValueError as first_err:
        print(f"  Consolidation validation failed: {first_err}")
        print(f"  Retrying with targeted repair prompt (1 attempt)...")
        bad_cluster_ids = _get_bad_cluster_ids(merged, raw_cluster_ids)
        print(f"  Bad cluster_ids to reassign: {bad_cluster_ids}")
        repair_prompt = _make_repair_prompt(merged, bad_cluster_ids)
        raw_repair, repair_stop_reason = _call_model_raw(repair_prompt, client, max_tokens=1024)
        cleaned_repair = _strip_json_fences(raw_repair)
        preview = _preview_text(raw_repair)
        if not cleaned_repair:
            raise ValueError(
                "Repair prompt returned empty response — consolidation still failed. "
                f"stop_reason={repair_stop_reason!r}, preview={preview!r}"
            ) from first_err
        try:
            repair_result = json.loads(cleaned_repair)
        except (json.JSONDecodeError, ValueError) as parse_err:
            raise ValueError(
                "Repair prompt returned invalid JSON — consolidation still failed. "
                f"stop_reason={repair_stop_reason!r}, preview={preview!r}, parse_error={parse_err}"
            ) from parse_err
        try:
            _validate_repair_mapping(repair_result, bad_cluster_ids, len(merged))
        except ValueError as repair_err:
            raise ValueError(
                f"Repair mapping invalid — consolidation still failed. "
                f"stop_reason={repair_stop_reason!r}, preview={preview!r}, error={repair_err}"
            ) from repair_err
        merged = _apply_repair_mapping(merged, repair_result, bad_cluster_ids)
        _validate_merged_clusters(merged, raw_cluster_ids)

    return merged


def _rebuild_indices(merged_clusters: list[dict], batch_clusters: list[list[dict]]) -> list[dict]:
    """
    Map complaint_indices back onto merged clusters using cluster_ids.
    """
    cluster_id_to_indices: dict[str, set] = {}
    raw_indices = set()

    for batch in batch_clusters:
        for c in batch:
            cluster_id = c["cluster_id"]
            indices = set(c.get("complaint_indices", []))
            raw_indices.update(indices)
            if cluster_id in cluster_id_to_indices:
                cluster_id_to_indices[cluster_id].update(indices)
            else:
                cluster_id_to_indices[cluster_id] = indices

    rebuilt_indices = set()
    for merged in merged_clusters:
        gathered = set()
        for cluster_id in merged["cluster_ids"]:
            gathered.update(cluster_id_to_indices[cluster_id])
        if not gathered:
            raise ValueError(f"Merged theme '{merged['name']}' resolved to zero complaint_indices.")
        merged["complaint_indices"] = sorted(gathered)
        rebuilt_indices.update(gathered)

    if rebuilt_indices != raw_indices:
        print(f"  complaint coverage: FAILED ({len(rebuilt_indices)}/{len(raw_indices)} complaint indices preserved)")
        raise ValueError("Complaint index coverage shrank during consolidation rebuild.")

    print(f"  complaint coverage: OK ({len(rebuilt_indices)}/{len(raw_indices)} complaint indices preserved)")

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
        _assign_cluster_ids(clusters, 0)
    else:
        cache_key = _cache_key(pattern, total)
        cached = _load_cache(cache_key)
        if cached:
            print(f"  Loaded batch clusters from cache (skipping API calls).")
            batch_clusters = cached
            for b_idx, batch in enumerate(batch_clusters):
                _assign_cluster_ids(batch, b_idx)
        else:
            batches = [snippets[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
            print(f"  Splitting into {len(batches)} batches of ~{BATCH_SIZE}...")
            batch_clusters = []
            for b_idx, batch in enumerate(batches):
                print(f"    Batch {b_idx + 1}/{len(batches)}...")
                prompt = _make_cluster_prompt(pattern, batch)
                batch_result = _call_model(prompt, client)
                _assign_cluster_ids(batch_result, b_idx)
                batch_clusters.append(batch_result)
            _save_cache(cache_key, batch_clusters)
            print(f"  Batch results cached.")

        merged = _consolidate(pattern, batch_clusters, client)
        clusters = _rebuild_indices(merged, batch_clusters)

    for c in clusters:
        c["complaint_count"] = len(c.get("complaint_indices", []))

    clusters.sort(key=lambda c: c["complaint_count"], reverse=True)

    return clusters
