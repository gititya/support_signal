# Signal

Signal turns customer support noise into product action — corroborating support signal across independent listening posts and generating narrative briefs that product teams act on.

*(Full README coming at end of build session — see PRD spec)*

---

## ⚠ Known limitation: LLM consolidation token ceiling

When clustering large complaint sets (e.g. 2,000 complaints → 20 batches → 214 raw clusters), sending all clusters to a single consolidation call will exceed the model's output token limit and truncate the response mid-JSON.

**The fix is in place:** `cluster.py` enforces a hard limit of 30 clusters per consolidation call and automatically uses hierarchical consolidation when the count exceeds it. Do not remove or raise `MAX_CLUSTERS_PER_CONSOLIDATION` without re-testing with a large dataset first.
