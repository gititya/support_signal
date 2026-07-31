"""Bucket the Wispr Flow corpus. Clustering only — no classify, score, or narrate.

Reads the consolidated CSV from wispr-scrape, assigns every row to a bucket in
config/taxonomy/wispr.yaml, and writes counts plus the assigned rows.

    export OPENROUTER_API_KEY=sk-or-...
    python run_wispr_cluster.py                # full corpus
    python run_wispr_cluster.py --sample 200   # cheap dry run first

Costs money. Run --sample first and read the assignments before the full pass.
"""

import argparse
import json
import os
from collections import Counter
from pathlib import Path

import pandas as pd

from src.cluster import CLUSTER_MODEL, cluster_complaints
from src.llm_client import get_client

CORPUS = Path("/Users/aditya/Documents/Projects/wispr-scrape/data/wispr_corpus.csv")
TAXONOMY = Path(__file__).parent / "config" / "taxonomy" / "wispr.yaml"
OUTDIR = Path(__file__).parent / "output"

# The taxonomy carries the routing logic; this only frames the job.
PATTERN = (
    "Users report problems with Wispr Flow, a voice dictation app for macOS, "
    "Windows, iOS and Android. Assign each report to the bucket describing the "
    "user's actual grievance."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, help="cluster only the first N rows")
    args = ap.parse_args()

    if not os.environ.get("OPENROUTER_API_KEY"):
        raise SystemExit("OPENROUTER_API_KEY not set. export it and re-run.")

    df = pd.read_csv(CORPUS)
    if args.sample:
        # Stratify so the sample isn't all Play Store. groupby.head keeps every
        # column; groupby.apply would consume "Product" as the grouping key.
        per = max(1, args.sample // df["Product"].nunique())
        df = df.groupby("Product").head(per).reset_index(drop=True)
    print(f"{len(df):,} rows | model {CLUSTER_MODEL}")
    print(df["Product"].value_counts().to_string(), "\n")

    clusters = cluster_complaints(
        PATTERN, df,
        client=get_client(),
        taxonomy_path=TAXONOMY,
    )

    OUTDIR.mkdir(exist_ok=True)
    tag = f"sample{len(df)}" if args.sample else "full"
    raw = OUTDIR / f"wispr_clusters_{tag}.json"
    raw.write_text(json.dumps(clusters, indent=2, default=str))

    print(f"\n{'BUCKET':<48} {'ROWS':>6}  {'SHARE':>6}")
    print("-" * 64)
    total = sum(len(c.get("complaint_indices", [])) for c in clusters)
    rows = []
    for c in sorted(clusters, key=lambda c: -len(c.get("complaint_indices", []))):
        idxs = c.get("complaint_indices", [])
        n = len(idxs)
        if not n:
            continue
        print(f"{c['name'][:47]:<48} {n:>6}  {n / max(total, 1):>5.1%}")
        by_src = Counter(df.iloc[i]["Product"] for i in idxs if i < len(df))
        for i in idxs:
            if i < len(df):
                rows.append({
                    "bucket": c["name"],
                    "source": df.iloc[i]["Product"],
                    "date": df.iloc[i]["Date received"],
                    "text": df.iloc[i]["Consumer complaint narrative"],
                })
        print(f"{'':>4}{dict(by_src)}")

    csv_out = OUTDIR / f"wispr_bucketed_{tag}.csv"
    pd.DataFrame(rows).to_csv(csv_out, index=False)
    print(f"\n{total:,} assigned -> {csv_out}\n              raw -> {raw}")


if __name__ == "__main__":
    main()
