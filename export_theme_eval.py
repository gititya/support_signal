import csv
import json
from pathlib import Path

from src.ingest import load_and_filter
from src.cluster import cluster_complaints
from src.classify import classify_clusters

PATTERN = "customers unable to dispute incorrect information on their credit report"
TAXONOMY_PATH = Path("config/taxonomy/transunion.yaml")
OUTPUT_PATH = Path("output/theme_eval_taxonomy_signals.csv")
NARRATIVE_LEN = 500

OUTPUT_PATH.parent.mkdir(exist_ok=True)

df, _ = load_and_filter(PATTERN)
print(f"Loaded {len(df):,} filtered complaints.", flush=True)
clusters = cluster_complaints(PATTERN, df, taxonomy_path=TAXONOMY_PATH)
print(f"Generated {len(clusters):,} taxonomy signals.", flush=True)
classify_clusters(clusters)
print("Classified taxonomy signals.", flush=True)

rows = []
for signal_num, c in enumerate(clusters, start=1):
    for idx in c["complaint_indices"]:
        row_data = df.iloc[idx]
        narrative = str(row_data.get("Consumer complaint narrative", ""))
        rows.append({
            "signal_number": signal_num,
            "signal_name": c["signal_name"],
            "signal_description": c["signal_description"],
            "bucket_distinction": c["bucket_distinction"],
            "evidence_bucket_name": c["evidence_bucket_name"],
            "evidence_bucket_description": c["evidence_bucket_description"],
            "evidence_bucket_assignment_rationale": c.get("evidence_bucket_assignment_rationales", {}).get(idx, ""),
            "cfpb_issue": row_data.get("Issue", ""),
            "cfpb_sub_issue": row_data.get("Sub-issue", ""),
            "root_cause_hypotheses": json.dumps(c["root_cause_hypotheses"], ensure_ascii=False),
            "supporting_indices": json.dumps(c["supporting_indices"]),
            "signal_type": c["signal_type"],
            "recommended_audience": c["recommended_audience"],
            "classification_rationale": c["classification_rationale"],
            "complaint_count": c["complaint_count"],
            "complaint_index": idx,
            "complaint_id": row_data.get("Complaint ID", ""),
            "date_received": row_data.get("Date received", ""),
            "product": row_data.get("Product", ""),
            "sub_product": row_data.get("Sub-product", ""),
            "state": row_data.get("State", ""),
            "narrative_excerpt": narrative[:NARRATIVE_LEN],
        })

with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}", flush=True)
