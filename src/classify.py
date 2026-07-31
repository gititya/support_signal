import json
import re
from pathlib import Path

import openai
import yaml

from src.llm_client import get_client

CLASSIFY_MODEL = "anthropic/claude-haiku-4.5"

# Company-specific classification guidance lives in config/company_classification/<slug>.yaml.
# Categories, definitions, and examples are tuned per company and apply across all sources
# (CFPB, support tickets, app reviews, etc.) for that company.
# A different company may use different categories and/or definitions entirely.
_CONFIG_DIR = Path(__file__).parent.parent / "config" / "company_classification"

CONFIDENCE = "Directional"  # Phase 1 is always single-source


def _load_company_config(company_slug: str) -> dict:
    path = _CONFIG_DIR / f"{company_slug}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No classification config found for: {path}")
    return yaml.safe_load(path.read_text())


def _build_category_lines(categories: dict) -> str:
    lines = []
    for name, meta in categories.items():
        examples = ", ".join(f'"{e}"' for e in meta.get("examples", []))
        lines.append(f"- {name}: {meta['definition']} (e.g. {examples})")
    return "\n".join(lines)


def _make_classify_prompt(clusters: list[dict], categories: dict) -> str:
    slim = [
        {
            "i": i,
            "name": c["name"],
            "description": c.get("description", ""),
            "hypotheses": c.get("hypotheses", []),
        }
        for i, c in enumerate(clusters)
    ]
    valid_labels = ", ".join(f'"{k}"' for k in categories)
    category_lines = _build_category_lines(categories)
    return (
        f"Classify each complaint cluster below into exactly one signal type.\n"
        f"The categories and examples below are tuned for this company and source. "
        f"Another company may use different categories and definitions.\n\n"
        f"Signal types:\n{category_lines}\n\n"
        f"For each cluster return:\n"
        f"- signal_type: one of {valid_labels}, exactly as written\n"
        f"- rationale: one sentence explaining why\n\n"
        f"Clusters:\n{json.dumps(slim, indent=2)}\n\n"
        f"Return ONLY a JSON array of {len(clusters)} objects in the same order as the input:\n"
        f"[{{\"i\": 0, \"signal_type\": \"...\", \"rationale\": \"...\"}}]\n"
        f"No markdown, no prose, raw JSON only."
    )


def _parse_json(raw: str) -> list[dict]:
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    return json.loads(raw)


def _validate_classifications(result: list[dict], n: int, valid_types: set) -> None:
    if not isinstance(result, list) or len(result) != n:
        raise ValueError(f"Classification returned {len(result) if isinstance(result, list) else type(result)} items, expected {n}.")
    for item in result:
        i = item.get("i")
        if not isinstance(i, int) or not (0 <= i < n):
            raise ValueError(f"Classification result has invalid index: {i!r}")
        st = item.get("signal_type")
        if st not in valid_types:
            raise ValueError(f"Classification result for index {i} has unknown signal_type: {st!r}")
        if not isinstance(item.get("rationale"), str) or not item["rationale"].strip():
            raise ValueError(f"Classification result for index {i} is missing rationale.")


def classify_clusters(clusters: list[dict], company_slug: str = "transunion", client: openai.OpenAI = None) -> list[dict]:
    """
    Classify each cluster by signal type using company-specific category definitions.
    Loads category config from config/company_classification/<company_slug>.yaml.
    Appends signal_type, classification_rationale, recommended_audience, confidence to each cluster dict.
    Returns the same list (mutated in place).
    """
    if not clusters:
        return clusters

    config = _load_company_config(company_slug)
    categories = config["categories"]
    valid_types = set(categories.keys())

    # recommended_audience is defined per-category in the YAML if present,
    # otherwise falls back to the category name itself.
    audience_map = {
        name: meta.get("recommended_audience", name)
        for name, meta in categories.items()
    }

    if client is None:
        client = get_client()

    print(f"  Classifying {len(clusters)} clusters via {CLASSIFY_MODEL} ({config['company']})...")

    prompt = _make_classify_prompt(clusters, categories)
    response = client.chat.completions.create(
        model=CLASSIFY_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.choices[0].finish_reason == "length":
        raise ValueError("Classification response was truncated (hit max_tokens).")

    raw = response.choices[0].message.content
    try:
        result = _parse_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Classification returned invalid JSON. Preview: {raw[:200]!r}. Error: {e}") from e

    _validate_classifications(result, len(clusters), valid_types)

    for item in result:
        c = clusters[item["i"]]
        c["signal_type"] = item["signal_type"]
        c["classification_rationale"] = item["rationale"]
        c["recommended_audience"] = audience_map[item["signal_type"]]
        c["confidence"] = CONFIDENCE

    return clusters
