---
status: "in-progress"
current_state: "Signal Phase 1 now generates scored PM briefs from the taxonomy signal pipeline."
next_action: "Review the generated PM brief for usefulness and decide whether Phase 1 is close enough to package."
things_to_know:
  - "Narrative complaint text should outrank metadata."
  - "Generated CSV/output files can be stale even when tests pass."
  - "The active review artifact is output/theme_eval_taxonomy_signals.csv, not the old theme_eval.csv."
  - "The latest generated PM brief is output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md."
what_it_is: "CLI that clusters CFPB complaint narratives into product evidence and PM-ready briefs."
read_next:
  - "README.md"
  - "SKILL.md"
  - "signal-prd-v2.1.md"
  - "eval_bucket_golden.py"
  - "output/"
agent_notes:
  - "Narrative complaint text should outrank metadata."
  - "Generated CSV/output files can be stale even when tests pass."
  - "Review actual outputs before claiming taxonomy quality."
safe_first_action: "Use the latest taxonomy output and golden eval before changing classification logic."
updated_at: "2026-06-24"
updated_by: "codex"
---

## Build inbox
Free-write feature ideas, follow-ups, and "do this next" notes here. Keep coding-agent implementation detail in `SKILL.md`.
