---
status: "in-progress"
current_phase: "Signal taxonomy redesign review; initial generated output review looks good so far."
next_action: "Proceed from trusted taxonomy/signal extraction into scoring and PM brief generation."
things_to_know:
  - "Narrative complaint text should outrank metadata."
  - "Generated CSV/output files can be stale even when tests pass."
  - "Adi's first pass on the taxonomy signal export looked good so far."
---

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
| 3 | src/cluster.py | ✅ Done + verified (cluster_id fix applied) |
| 4 | src/classify.py | ✅ Done + verified |
| 5 | src/score.py | ⏳ Pending |
| 6 | templates/brief_pm.md.j2 | ⏳ Pending |
| 7 | src/narrate.py | ⏳ Pending |
| 8 | signal.py | ⏳ Pending |

## Current status (2026-04-01)
Steps 1–4 complete. 15 themes produced from 2,000 TransUnion complaints, classified by signal type and exported to `output/theme_eval.csv`.

**In progress:** Manual evaluation of theme quality — verifying theme names, signal types, and classification rationale against complaint narratives.

**Pending confirmation before proceeding:**
- [ ] Quality of `output/theme_eval.csv` confirmed acceptable
- [ ] Delete `run_cluster_live.py` and `run_classify_live.py` (scratch scripts, no longer needed once quality is confirmed)

**Next step (after quality confirmed):** Step 5 — `src/score.py` (heuristic severity scoring, no LLM)

## Key constraints (never violate)
- Classification runs AFTER clustering — never before
- Root-cause hypotheses always start with "This may indicate", "Evidence suggests", or "This pattern is consistent with"
- Model constants at top of each file
- Phase 1 confidence always "Directional (single source)"

---

## Claude Code handoff — taxonomy redesign (2026-05-06)

Tell Claude Code:

Codex implemented the Signal taxonomy redesign on branch `codex-signal-taxonomy-redesign`. The new architecture is buckets first, signals second: CFPB `Issue` + `Sub-issue` now deterministically assigns complaints into curated TransUnion evidence buckets, then Sonnet synthesizes PM-facing signals and root-cause hypotheses from narratives inside each populated bucket. CFPB buckets are grounding metadata, not the final product insight.

Durable context to preserve:
- Do not return to free-form LLM theme assignment as the default; keep it only as legacy/debug comparison.
- Do not use LLM fallback assignment for unmatched rows; unknown combos go to `Other/Unclassified`.
- The new review export path is `output/theme_eval_taxonomy_signals.csv`, so the existing `output/theme_eval.csv` and `output/theme_eval - myfirstfeedback.csv` are not overwritten by the taxonomy/signal run.
- `AGENTS.md` is now the Codex context file and includes the revised taxonomy state.

## Codex update — taxonomy assignment reliability (2026-06-18)

Correction to the older handoff above: taxonomy evidence-bucket assignment is now narrative-first model classification against curated buckets, not deterministic CFPB combo assignment. CFPB `Issue` + `Sub-issue` remains grounding context only.

Current stabilization work:
- Row-level taxonomy assignments are cached under `.batch_cache/taxonomy_assignments_*.json` after every assignment batch, so a killed export can resume without paying for completed rows again.
- `eval_bucket_golden.py` is the cheap pre-export gate for known hard cases before running the full `export_theme_eval.py`.
- The taxonomy export still writes to `output/theme_eval_taxonomy_signals.csv` and does not overwrite `output/theme_eval.csv`.

## Codex sync — taxonomy output review checkpoint (2026-06-24)

Adi reported the generated taxonomy/signal output looks good so far. Treat this as initial review confidence, not a final exhaustive row-by-row audit.

Current state:
- The active review artifact is `output/theme_eval_taxonomy_signals.csv`.
- Evidence bucket assignment is narrative-first against curated buckets, with CFPB fields used as grounding context.
- Known hard cases passed the golden eval: identity-theft blocking, cross-bureau inconsistency, unauthorized inquiry/report use, investigation-not-fixed, and account-status wrong.
- Long taxonomy assignment runs are resumable through `.batch_cache/taxonomy_assignments_*.json`.

Next implementation direction:
- Continue to Phase 1 scoring and PM brief generation now that the extraction layer is credible enough to build on.
- Keep classification after evidence assembly and signal synthesis.
- Do not overwrite `output/theme_eval.csv`; taxonomy review output remains `output/theme_eval_taxonomy_signals.csv`.

## Codex closeout update — packaging and reviewer readiness (2026-06-25)

The older "Current phase" table above is superseded for closeout purposes: `src/score.py`, `templates/brief_pm.md.j2`, `src/narrate.py`, and `signal.py` now exist on the taxonomy branch and generate a scored PM brief.

Current closeout direction:
- Freeze extraction. Do not reopen taxonomy, clustering, scoring, or signal synthesis unless verification finds a concrete blocker.
- Treat `output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md` as the committed demo artifact.
- Keep offline verification on `unittest`; `pytest` is not a project dependency.
- `test_key.py` is a live API smoke test and should skip cleanly when `ANTHROPIC_API_KEY` is absent.
- The README is the front door for reviewers: lead with the generated brief, B2C/CFPB framing, the engineering log, the reusable engine/domain seam, and PII/API caveats for bring-your-own data.
