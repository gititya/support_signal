import os, sys                                                                                            
sys.path.insert(0, "/Users/aditya/Documents/Projects/signal")
from src.ingest import load_and_filter                                                                    
from src.cluster import cluster_complaints
                                                                                                            
df, meta = load_and_filter("customers unable to dispute incorrect information on their credit report")    
clusters = cluster_complaints(meta["pattern"], df)
                                                                                                            
print(f"\nClusters found: {len(clusters)}")                                                               
for c in clusters:                  
    print(f"  [{c['complaint_count']:>4}] {c['name']}")                                                   
                                                                                                            
largest = clusters[0]               
print(f"\nFirst hypothesis of largest cluster (\"{largest['name']}\"):")                                  
print(f"  {largest['hypotheses'][0]}")
