---
status: "shipped"
current_state: "Signal closeout complete: README front door, offline tests, generated PM brief, and OpenRouter provider swap are all in main. Branches reviewed, nothing hanging."
next_action: "None pending. Signal is not an active build; revisit only if a new brief/pattern is requested."
things_to_know:
  - "Narrative complaint text should outrank metadata."
  - "Generated CSV/output files can be stale even when tests pass."
  - "The active review artifact is output/theme_eval_taxonomy_signals.csv, not the old theme_eval.csv."
  - "The latest generated PM brief is output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md."
  - "LLM calls go through OpenRouter (OPENROUTER_API_KEY) via src/llm_client.py, not the anthropic SDK directly."
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
updated_at: "2026-08-12"
updated_by: "codex"
---

## Build inbox
Free-write feature ideas, follow-ups, and "do this next" notes here. Keep coding-agent implementation detail in `SKILL.md`.

- 2026-07-31: Closeout pass — swapped Anthropic SDK for OpenRouter across all four model call sites, updated CLAUDE.md/AGENTS.md/SKILL.md/README.md, confirmed `codex-signal-taxonomy-redesign` and `codex/signal-closeout` were both already fully merged into `origin/main`, and merged this session's changes to `main` via a clean PR.
- 2026-08-28: Public release prep per `signal-release-plan.md` — fixed the `other_bucket_index` KeyError noted below, removed hardcoded `/Users/aditya` paths from tests/AGENTS.md/README.md, deleted the Wispr taxonomy/script, rewrote README.md to match the voice-support-case-study house style, and flagged `signal-prd-v2.1.md` as stale with a preface note. All 51 offline tests pass; `test_key.py` skips without a key. Repo visibility flip to public is pending Adi's go-ahead.
