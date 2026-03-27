# Signal — Session State

## ✅ Blockers resolved (2026-03-27)

### Billing — resolved
Topped up. API calls working.

### Step 3 — cluster.py consolidation — resolved after 3 failures (~$10+ spent)
**What failed:** Recursive hierarchical consolidation. The model never reduced cluster count enough per pass (216→131→103), causing infinite looping and eventual max_tokens failures.
**What was done:** Replaced recursive consolidation with a single names-only call. Strips input to `name + description[:80]`, asks for EXACTLY 15 output clusters. Output bounded at ~3k tokens — can never hit max_tokens. See memory for full incident log.
**Deviation from plan:** Hypotheses are regenerated fresh in the consolidation call rather than preserved from batch output. Minor quality tradeoff, functionally equivalent.
**Batch cache:** 20 batches / 216 clusters cached at `.batch_cache/batches_511254be1c14.json` — intact.

---

## Current phase
**Phase 1 — Build**

| Step | File | Status |
|------|------|--------|
| 1 | File structure + requirements.txt | ✅ Done |
| 2 | src/ingest.py | ✅ Done + verified |
| 3 | src/cluster.py | 🔴 Fix in place — needs one clean run to verify (billing topped up, run test_cluster.py) |
| 4 | src/classify.py | ⏳ Next |
| 5 | src/score.py | ⏳ Pending |
| 6 | templates/brief_pm.md.j2 | ⏳ Pending |
| 7 | src/narrate.py | ⏳ Pending |
| 8 | signal.py | ⏳ Pending |

## Next step after blockers resolved
**Step 4 — src/classify.py**
Classify each cluster by signal type (Defect / UX Friction / Knowledge Gap / Monetization Opportunity) using Haiku. Runs AFTER clustering output is confirmed. See plan at `/Users/aditya/.claude/plans/jazzy-gathering-gosling.md` for full spec.

## Key constraints (never violate)
- Classification runs AFTER clustering — never before
- Root-cause hypotheses always start with "This may indicate", "Evidence suggests", or "This pattern is consistent with"
- Model constants at top of each file
- Phase 1 confidence always "Directional (single source)"
