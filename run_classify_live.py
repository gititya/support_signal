from src.ingest import load_and_filter
from src.cluster import cluster_complaints
from src.classify import classify_clusters

pattern = "customers unable to dispute incorrect information on their credit report"
df, _ = load_and_filter(pattern)
clusters = cluster_complaints(pattern, df)
classify_clusters(clusters)
for c in clusters:
    print(f'[{c["signal_type"]:25s}] [{c["recommended_audience"]:12s}] {c["name"]}')
