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

    # Step 2 — check cache before clustering
    key = _cache_key(PATTERN, total)
    cache_path = Path(key)
    if cache_path.exists():
        print(f"\n[cache] REUSING cached batch clusters: {cache_path.name}")
    else:
        print(f"\n[cache] No cache found at {cache_path.name} — will run batch API calls")

    # Step 3 — cluster
    print("\n[cluster]")
    clusters = cluster_complaints(PATTERN, df)

    # Step 4 — print results
    print(f"\n[results] {len(clusters)} final clusters (sorted by complaint_count desc)")
    print("-" * 60)
    for i, c in enumerate(clusters):
        name = c.get("name", "<no name>")
        count = c.get("complaint_count", 0)
        hypotheses = c.get("hypotheses", [])
        first_hyp = hypotheses[0] if hypotheses else "<no hypothesis>"
        marker = " <-- largest" if i == 0 else ""
        print(f"  {i+1:2d}. [{count:4d}] {name}{marker}")
        if i == 0:
            print(f"        Hypothesis: {first_hyp}")
    print("-" * 60)
    print("Done.")


if __name__ == "__main__":
    main()
