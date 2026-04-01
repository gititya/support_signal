# Signal — Engineering Log

Incidents, bugs, and architectural decisions that shaped the codebase.
Read this before changing clustering, consolidation, or index-rebuild logic.

---

## Incident 1 — Consolidation token ceiling (2026-03-27, ~$10+ spent)

### What failed and why
1. Single consolidation call with 216 clusters → `max_tokens` hit, JSON truncated mid-stream, parser crashed
2. Recursive hierarchical consolidation → model never reduced count aggressively enough (216→131→103), loop ran for 2+ hours
3. Depth cap with forced final call on 103 clusters → `max_tokens` again

**Root cause:** Passing hypotheses into consolidation input bloats output tokens unpredictably across recursive passes. LLMs don't reliably reduce cluster count enough per pass to converge within bounded depth.

### What was done
Replaced all recursive consolidation with a single names-only call:
- Strip ALL input clusters to `name + description[:80]` — no hypotheses, no indices
- Ask for EXACTLY 15 output clusters in the prompt — forces aggressive merging
- Output is bounded: 15 clusters × ~200 tokens = ~3k tokens, can never hit `max_tokens`
- One API call, no recursion, no sub-groups

**Deviation from original plan:** Hypotheses are regenerated fresh in the consolidation call rather than preserved from batch output. Minor quality tradeoff, functionally equivalent for the PM brief.

### Rules for future work
- Never pass hypotheses into a consolidation prompt — they bloat output unpredictably
- Always constrain output cluster count explicitly ("produce EXACTLY N")
- Never use recursive consolidation — the model won't converge reliably
- Batch cache at `.batch_cache/` is permanent, keyed by pattern+count+model — always load before re-running

---

## Incident 2 — Cluster identity bug: name-based matching broke index rebuild (2026-04-01)

### The bug
After the consolidation call produced 15 merged themes, `_rebuild_indices` tried to map complaints back to themes by matching on cluster **name strings**. This was brittle for two reasons:

1. Different batches independently generate clusters with identical or near-identical names (e.g. "Dispute Not Processed" appearing in batch 3 and batch 11 as separate clusters). Name matching would silently merge them or miss one entirely.
2. The consolidation model could paraphrase or slightly reword a name, causing a lookup miss and zeroing out that theme's complaint indices.

The result: complaint indices were scrambled — some themes had too many complaints, some had zero, and the output silently passed validation.

### What was fixed (by Codex)
Every raw cluster is stamped with a unique machine ID **before** any consolidation or name processing happens:

```
b{batch_index:02d}_c{cluster_index:02d}
```

Examples: `b00_c00`, `b03_c05`, `b19_c11`

These IDs are opaque — they carry no semantic meaning. The consolidation prompt is given the full list of all IDs and told to assign each one to exactly one output theme (field: `cluster_ids`). The model is forbidden from inventing, modifying, or omitting any ID.

`_rebuild_indices` now follows `cluster_ids` arrays, not names. Complaint coverage is verified after rebuild — if any index is lost, it raises immediately.

### Validation added
- `_validate_raw_clusters` — checks every raw cluster has a unique, non-empty `cluster_id` before consolidation
- `_validate_merged_clusters` — checks every ID appears exactly once across all output themes; raises on duplicates, unknowns, or missing IDs
- `_rebuild_indices` — raises if any theme resolves to zero complaint indices; verifies total coverage equals raw count
- Repair path — if consolidation produces a bad ID assignment, a targeted repair prompt reassigns only the bad IDs (not a full rewrite), then re-validates

### Key functions in `src/cluster.py`
| Function | Purpose |
|---|---|
| `_assign_cluster_ids` | Stamps `cluster_id` onto each raw cluster after batch call |
| `_validate_raw_clusters` | Pre-consolidation: verifies all IDs present and unique |
| `_validate_merged_clusters` | Post-consolidation: verifies full ID coverage |
| `_get_bad_cluster_ids` | Finds duplicated + missing IDs for repair |
| `_make_repair_prompt` | Asks model to reassign only bad IDs |
| `_validate_repair_mapping` | Validates repair response shape |
| `_apply_repair_mapping` | Strips bad IDs, appends corrected assignments |
| `_rebuild_indices` | Follows `cluster_ids` → complaint indices |
