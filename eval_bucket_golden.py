import csv
from pathlib import Path

import pandas as pd

from src.cluster import _assign_evidence_buckets_with_model, load_taxonomy
from src.llm_client import get_client

PATTERN = "customers unable to dispute incorrect information on their credit report"
TAXONOMY_PATH = Path("config/taxonomy/transunion.yaml")
GOLDEN_PATH = Path("fixtures/golden_bucket_examples.csv")


def main() -> int:
    rows = list(csv.DictReader(GOLDEN_PATH.open(newline="", encoding="utf-8")))
    df = pd.DataFrame([
        {
            "Issue": row["cfpb_issue"],
            "Sub-issue": row["cfpb_sub_issue"],
            "Consumer complaint narrative": row["narrative_excerpt"],
        }
        for row in rows
    ])

    taxonomy = load_taxonomy(TAXONOMY_PATH)
    client = get_client()
    buckets = _assign_evidence_buckets_with_model(PATTERN, df, taxonomy, client)

    assigned_by_idx = {}
    rationale_by_idx = {}
    for bucket in buckets:
        for idx in bucket["complaint_indices"]:
            assigned_by_idx[idx] = bucket["name"]
            rationale_by_idx[idx] = bucket.get("assignment_rationales", {}).get(idx, "")

    failures = []
    for idx, row in enumerate(rows):
        expected = row["expected_evidence_bucket"]
        actual = assigned_by_idx.get(idx, "")
        ok = actual == expected
        status = "PASS" if ok else "FAIL"
        print(
            f"{status} {row['case_id']}: expected={expected!r}, actual={actual!r}, "
            f"rationale={rationale_by_idx.get(idx, '')}",
            flush=True,
        )
        if not ok:
            failures.append((row["case_id"], expected, actual))

    if failures:
        print(f"\nGolden bucket eval failed: {len(failures)}/{len(rows)} cases failed.", flush=True)
        return 1

    print(f"\nGolden bucket eval passed: {len(rows)}/{len(rows)} cases.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
