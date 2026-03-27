import sys; sys.path.insert(0, ".")
from src.ingest import load_and_filter

print("=== Test 1 ===")
df, meta = load_and_filter("customers unable to dispute incorrect information on their credit report")
print(f"\nMetadata: {meta}\n")
for _, row in df.head(3).iterrows():
    date = row['Date received']
    print(f"[{date}] {row['Issue']}")
    print(f"  {str(row['Consumer complaint narrative'])[:200]}\n")

print("=== Test 2 ===")
try:                                                                                                      
      load_and_filter("customers complaining about airline baggage fees")
except (ValueError, EnvironmentError) as e:                                                               
      print(f"Clean error (no traceback): {e}")
