import csv
from pathlib import Path

from src.ingest import load_and_filter
from src.cluster import cluster_complaints
from src.classify import classify_clusters

PATTERN = "customers unable to dispute incorrect information on their credit report"
OUTPUT_PATH = Path("output/theme_eval.csv")
NARRATIVE_LEN = 500

OUTPUT_PATH.parent.mkdir(exist_ok=True)

df, _ = load_and_filter(PATTERN)
clusters = cluster_complaints(PATTERN, df)
classify_clusters(clusters)

rows = []
for theme_num, c in enumerate(clusters, start=1):
    for idx in c["complaint_indices"]:
        row_data = df.iloc[idx]
        narrative = str(row_data.get("Consumer complaint narrative", ""))
        rows.append({
            "theme_number": theme_num,
            "theme_name": c["name"],
            "signal_type": c["signal_type"],
            "recommended_audience": c["recommended_audience"],
            "classification_rationale": c["classification_rationale"],
            "complaint_count": c["complaint_count"],
            "complaint_index": idx,
            "complaint_id": row_data.get("Complaint ID", ""),
            "date_received": row_data.get("Date received", ""),
            "issue": row_data.get("Issue", ""),
            "product": row_data.get("Product", ""),
            "sub_product": row_data.get("Sub-product", ""),
            "state": row_data.get("State", ""),
            "narrative_excerpt": narrative[:NARRATIVE_LEN],
        })

with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Wrote {len(rows)} rows to {OUTPUT_PATH}")
