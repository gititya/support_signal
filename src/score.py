from __future__ import annotations

from datetime import datetime


CONFIDENCE = "Directional (single source)"
SOURCE_STATUS = "CFPB complaints only"

_SIGNAL_TYPE_WEIGHT = {
    "Defect": 2,
    "UX Friction": 1,
    "Knowledge Gap": 1,
    "Monetization Opportunity": 0,
}


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _volume_label(complaint_count: int) -> str:
    if complaint_count >= 250:
        return "High volume"
    if complaint_count >= 75:
        return "Medium volume"
    return "Low volume"


def _volume_points(complaint_count: int) -> int:
    if complaint_count >= 250:
        return 3
    if complaint_count >= 75:
        return 2
    if complaint_count >= 15:
        return 1
    return 0


def _severity_label(points: int) -> str:
    if points >= 5:
        return "High"
    if points >= 3:
        return "Medium"
    return "Low"


def _format_date_range(metadata: dict | None) -> str:
    if not metadata:
        return "date range unavailable"
    start = metadata.get("date_start") or "unknown"
    end = metadata.get("date_end") or "unknown"
    if start == "unknown" and end == "unknown":
        return "date range unavailable"
    return f"{start} to {end}"


def _date_span_days(metadata: dict | None) -> int | None:
    if not metadata:
        return None
    start = metadata.get("date_start")
    end = metadata.get("date_end")
    try:
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
    return max(1, (end_dt - start_dt).days + 1)


def score_signal(signal: dict, metadata: dict | None = None, source_status: str = SOURCE_STATUS) -> dict:
    complaint_count = _as_int(signal.get("complaint_count"))
    signal_type = signal.get("signal_type", "Unclassified")
    points = _volume_points(complaint_count) + _SIGNAL_TYPE_WEIGHT.get(signal_type, 0)
    if signal.get("is_other_bucket"):
        points = max(0, points - 1)

    volume_label = _volume_label(complaint_count)
    severity = _severity_label(points)
    date_range = _format_date_range(metadata)
    span_days = _date_span_days(metadata)
    span_text = f" across {span_days} days" if span_days else ""
    sample_count = len(signal.get("supporting_indices") or [])
    bucket = signal.get("evidence_bucket_name", "unknown evidence bucket")

    rationale = (
        f"{severity} severity based on {volume_label.lower()} ({complaint_count} CFPB complaints"
        f"{span_text}, {date_range}), signal type {signal_type}, and evidence bucket '{bucket}'. "
        f"Confidence remains {CONFIDENCE.lower()} because this uses {source_status} "
        f"with {sample_count} supporting samples and no product telemetry."
    )

    signal["severity"] = severity
    signal["volume_label"] = volume_label
    signal["confidence"] = CONFIDENCE
    signal["source_status"] = source_status
    signal["scoring_rationale"] = rationale
    return signal


def score_signals(signals: list[dict], metadata: dict | None = None, source_status: str = SOURCE_STATUS) -> list[dict]:
    for signal in signals:
        score_signal(signal, metadata=metadata, source_status=source_status)
    return signals
