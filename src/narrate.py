from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

import anthropic
from jinja2 import Environment, FileSystemLoader, StrictUndefined


NARRATE_MODEL = "claude-sonnet-4-6"
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
TEMPLATE_NAME = "brief_pm.md.j2"
HYPOTHESIS_PREFIXES = (
    "This may indicate",
    "Evidence suggests",
    "This pattern is consistent with",
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "signal-brief"


def _safe_output_path(pattern: str, output_dir: Path = OUTPUT_DIR) -> Path:
    output_root = output_dir.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = (output_root / f"pm_brief_{_slugify(pattern)}_{timestamp}.md").resolve()
    if output_root not in path.parents:
        raise ValueError(f"Output path escaped output directory: {path}")
    return path


def _parse_model_json(raw: str) -> dict:
    cleaned = raw.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Narration response must be a JSON object.")
    return data


def _validate_hypotheses(signals: list[dict]) -> None:
    for signal in signals:
        for hypothesis in signal.get("root_cause_hypotheses", signal.get("hypotheses", [])):
            if not isinstance(hypothesis, str) or not hypothesis.startswith(HYPOTHESIS_PREFIXES):
                raise ValueError(f"Root-cause hypothesis is not cautiously framed: {hypothesis!r}")


def _build_examples(signal: dict, df, limit: int = 4) -> list[dict]:
    chosen = list(signal.get("supporting_indices") or [])
    if not chosen:
        chosen = list(signal.get("complaint_indices") or [])[:limit]
    examples = []
    for idx in chosen[:limit]:
        row = df.iloc[idx]
        narrative = str(row.get("Consumer complaint narrative", "")).strip()
        examples.append({
            "complaint_id": str(row.get("Complaint ID", "")),
            "date_received": str(row.get("Date received", ""))[:10],
            "state": str(row.get("State", "")),
            "cfpb_issue": str(row.get("Issue", "")),
            "cfpb_sub_issue": str(row.get("Sub-issue", "")),
            "narrative_excerpt": narrative[:900],
        })
    return examples


def _prepare_signals(signals: list[dict], df, limit: int = 5) -> list[dict]:
    prepared = []
    for signal in signals[:limit]:
        hypotheses = signal.get("root_cause_hypotheses", signal.get("hypotheses", []))
        prepared.append({
            "signal_name": signal.get("signal_name", signal.get("name", "")),
            "signal_description": signal.get("signal_description", signal.get("description", "")),
            "bucket_distinction": signal.get("bucket_distinction", ""),
            "evidence_bucket_name": signal.get("evidence_bucket_name", ""),
            "evidence_bucket_description": signal.get("evidence_bucket_description", ""),
            "signal_type": signal.get("signal_type", ""),
            "recommended_audience": signal.get("recommended_audience", ""),
            "classification_rationale": signal.get("classification_rationale", ""),
            "complaint_count": signal.get("complaint_count", 0),
            "severity": signal.get("severity", ""),
            "volume_label": signal.get("volume_label", ""),
            "confidence": signal.get("confidence", ""),
            "source_status": signal.get("source_status", ""),
            "scoring_rationale": signal.get("scoring_rationale", ""),
            "root_cause_hypotheses": hypotheses,
            "examples": _build_examples(signal, df),
        })
    return prepared


def _make_narration_prompt(pattern: str, metadata: dict, display_signals: list[dict], total_signal_count: int) -> str:
    brief_facts = {
        "pattern": pattern,
        "company": metadata.get("company"),
        "date_start": metadata.get("date_start"),
        "date_end": metadata.get("date_end"),
        "used_in_analysis": metadata.get("used_in_analysis"),
        "source_status": "CFPB complaints only",
        "confidence": "Directional (single source)",
        "total_signals": total_signal_count,
        "signals_in_brief": len(display_signals),
        "signals": [
            {
                "signal_name": s["signal_name"],
                "signal_description": s["signal_description"],
                "complaint_count": s["complaint_count"],
                "severity": s["severity"],
                "signal_type": s["signal_type"],
                "evidence_bucket_name": s["evidence_bucket_name"],
                "root_cause_hypotheses": s["root_cause_hypotheses"],
            }
            for s in display_signals
        ],
    }
    return (
        "You are writing concise narrative framing for a PM brief from fixed evidence.\n"
        "Use only the facts below. Do not invent analytics numbers, affected-user counts, "
        "certainty, extra sources, product telemetry, or new evidence. Keep confidence explicitly "
        "directional and single-source.\n"
        "Do not claim consumers correctly completed every required process step. Do not use phrases "
        "like 'confirmed victims', 'statutory violation', 'persistent and patterned', or 'legal rights' "
        "unless those exact claims are in the facts. Do not say there are exactly five signals unless "
        "total_signals is five.\n\n"
        f"Facts:\n{json.dumps(brief_facts, indent=2)}\n\n"
        "Return ONLY valid JSON with exactly these keys:\n"
        "{\n"
        '  "executive_summary": "2-3 short sentences a PM can understand quickly",\n'
        '  "recommended_action": "specific next product/support investigation action grounded in the evidence",\n'
        '  "narrative_framing": "one sentence framing why this signal matters without overclaiming"\n'
        "}\n"
    )


def _validate_narration(narration: dict) -> None:
    required = {"executive_summary", "recommended_action", "narrative_framing"}
    missing = required - set(narration)
    if missing:
        raise ValueError(f"Narration response is missing keys: {sorted(missing)}")
    for key in required:
        if not isinstance(narration[key], str) or not narration[key].strip():
            raise ValueError(f"Narration response has blank {key}.")
    lower = " ".join(narration[key].lower() for key in required)
    disallowed = (
        "correctly execute",
        "correctly invoked",
        "confirmed victims",
        "statutory violation",
        "persistent and patterned",
        "legal rights",
        "affected users",
        "product telemetry shows",
    )
    for phrase in disallowed:
        if phrase in lower:
            raise ValueError(f"Narration overclaimed with disallowed phrase: {phrase!r}")


def _call_narration_model(prompt: str, client: anthropic.Anthropic) -> dict:
    response = client.messages.create(
        model=NARRATE_MODEL,
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "max_tokens":
        raise ValueError("Narration response was truncated.")
    narration = _parse_model_json(response.content[0].text)
    _validate_narration(narration)
    return narration


def _fallback_narration(pattern: str, signals: list[dict]) -> dict:
    main = signals[0] if signals else {}
    return {
        "executive_summary": (
            f"Signal found {main.get('complaint_count', 0)} CFPB complaint narratives around "
            f"{main.get('signal_name', pattern)}. Confidence is directional because this brief uses "
            "one public complaint source and does not include product telemetry."
        ),
        "recommended_action": (
            "Review the strongest complaint samples with product, support, and compliance owners; "
            "map the reported failure point to the current dispute workflow; then decide what internal "
            "telemetry or case review is needed before sizing impact."
        ),
        "narrative_framing": "This is a product-readiness brief from public complaint evidence, not a measured incident report.",
    }


def _render_template(context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(TEMPLATE_NAME)
    return template.render(**context)


def generate_pm_brief(
    pattern: str,
    metadata: dict,
    signals: list[dict],
    df,
    client: anthropic.Anthropic | None = None,
    output_path: Path | None = None,
) -> Path:
    if not signals:
        raise ValueError("Cannot generate a PM brief without signals.")
    _validate_hypotheses(signals)

    prepared_signals = _prepare_signals(signals, df)
    if client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            client = anthropic.Anthropic(api_key=api_key)

    if client is None:
        narration = _fallback_narration(pattern, prepared_signals)
    else:
        prompt = _make_narration_prompt(pattern, metadata, prepared_signals, len(signals))
        narration = _call_narration_model(prompt, client)

    context = {
        "pattern": pattern,
        "metadata": metadata,
        "signals": prepared_signals,
        "total_signal_count": len(signals),
        "main_signal": prepared_signals[0],
        "narration": narration,
    }
    markdown = _render_template(context)
    path = output_path.resolve() if output_path else _safe_output_path(pattern)
    path.parent.mkdir(parents=True, exist_ok=True)
    output_root = OUTPUT_DIR.resolve()
    if output_root not in path.parents:
        raise ValueError(f"Output path escaped output directory: {path}")
    path.write_text(markdown, encoding="utf-8")
    return path
