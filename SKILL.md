# Signal — Session State

## 🔴 BEFORE ANYTHING ELSE: Two blockers to resolve in order

### 1. Fix billing
API calls are failing with "credit balance too low" even though balance shows $7.06 at platform.claude.com/settings/billing. This was unresolved at end of last session. **Verify this works first by running:**
```bash
cd /Users/aditya/Documents/Projects/signal
source ~/.zshrc
python test_key.py
```
If it still fails — contact Anthropic support before spending any more time.

### 2. Re-run the 20 batches (Step 3 — cluster.py)
The batch cache in `.batch_cache/` is empty — it was cleared before it could be saved. Once billing is confirmed working, re-run the cluster step:
```bash
python test_cluster.py
```
This will:
- Run 20 batches of ~100 complaints each (~45 mins, ~$2)
- Cache results to `.batch_cache/` (permanent this time)
- Run hierarchical consolidation automatically
- Print cluster names + first hypothesis of largest cluster

**Only proceed to Step 4 after this completes successfully.**

---

## Current phase
**Phase 1 — Build**

| Step | File | Status |
|------|------|--------|
| 1 | File structure + requirements.txt | ✅ Done |
| 2 | src/ingest.py | ✅ Done + verified |
| 3 | src/cluster.py | ✅ Code done — needs verified run |
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
