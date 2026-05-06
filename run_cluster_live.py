"""
Temporary live runner for Step 3 verification.
Calls load_and_filter() + cluster_complaints() and prints diagnostics.
Delete after Step 3 is confirmed.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.ingest import load_and_filter
from src.cluster import cluster_complaints, _cache_key, _CACHE_DIR

PATTERN = "customers unable to dispute incorrect information on their credit report"
TAXONOMY_PATH = Path("config/taxonomy/transunion.yaml")


def main():
    print("=" * 60)
    print("Signal — Live Cluster Runner")
    print(f"Pattern: {PATTERN}")
    print("=" * 60)

    # Step 1 — ingest
    print("\n[ingest]")
    df, metadata = load_and_filter(PATTERN)
    total = metadata["used_in_analysis"]
    print(f"  used_in_analysis: {total:,}")

    # Step 2 — check legacy cache before clustering
    key = _cache_key(PATTERN, total)
    cache_path = Path(key)
    if cache_path.exists():
        print(f"\n[cache] Legacy free-clustering cache exists: {cache_path.name}")
    else:
        print(f"\n[cache] No legacy free-clustering cache found at {cache_path.name}")

    # Step 3 — bucket + synthesize
    print("\n[cluster]")
    clusters = cluster_complaints(PATTERN, df, taxonomy_path=TAXONOMY_PATH)

    # Step 4 — print results
    print(f"\n[results] {len(clusters)} PM-facing signals (sorted by complaint_count desc)")
    print("-" * 60)
    for i, c in enumerate(clusters):
        name = c.get("signal_name", c.get("name", "<no name>"))
        bucket = c.get("evidence_bucket_name", "<no bucket>")
        count = c.get("complaint_count", 0)
        hypotheses = c.get("hypotheses", [])
        first_hyp = hypotheses[0] if hypotheses else "<no hypothesis>"
        marker = " <-- largest" if i == 0 else ""
        print(f"  {i+1:2d}. [{count:4d}] {name}{marker}")
        print(f"        Bucket: {bucket}")
        if i == 0:
            print(f"        Hypothesis: {first_hyp}")
    print("-" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
