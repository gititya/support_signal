# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this project does
Signal is a CLI tool that takes a free-text support pattern description, filters CFPB complaint CSV data for a target company, clusters complaints via Anthropic API with root-cause hypothesis generation, classifies by signal type, scores severity, and renders a Jinja2 markdown PM brief.

## Commands
```bash
# Use the project venv when default python is missing dependencies
/Users/aditya/venvs/support/bin/python -m pip install -r requirements.txt

# Run the tool
/Users/aditya/venvs/support/bin/python signal.py

# Run a single module test
/Users/aditya/venvs/support/bin/python test_cluster.py   # or any test_*.py in project root
```

## Architecture
```
signal.py          ← CLI entry point, wires all modules
src/
  ingest.py        ← Load CSV → filter company → keyword match → cap at 2,000 rows
  cluster.py       ← Batch clustering via Sonnet → names-only single-pass consolidation (15 themes)
  classify.py      ← Signal type classification via Haiku (runs AFTER clustering)
  score.py         ← Heuristic severity scoring, no LLM
  narrate.py       ← Exec summary + recommended action via Sonnet → render Jinja2 brief
templates/
  brief_pm.md.j2   ← PM brief template
data/
  complaints.csv   ← CFPB dataset (49,407 rows, 13,533 TransUnion)
output/            ← Generated briefs saved here
```

## Model constants (one per file, at the top)
| File | Constant | Model |
|------|----------|-------|
| ingest.py | FILTER_MODEL | claude-haiku-4-5-20251001 |
| cluster.py | CLUSTER_MODEL | claude-sonnet-4-6 |
| classify.py | CLASSIFY_MODEL | claude-haiku-4-5-20251001 |
| narrate.py | NARRATE_MODEL | claude-sonnet-4-6 |

## Strict sequencing rule
Classification (`classify.py`) MUST run after clustering (`cluster.py`). Never reverse this order.

## Root-cause hypothesis framing
All hypotheses must begin with one of:
- "This may indicate"
- "Evidence suggests"
- "This pattern is consistent with"

Never state root causes as facts.

## CSV column names (actual — differ from PRD notation)
`Date received`, `Consumer complaint narrative`, `Company`, `Complaint ID`, `Product`, `Sub-product`, `Issue`, `Sub-issue`, `Company response to consumer`, `Timely response?`, `Consumer disputed?`, `State`

## Current taxonomy redesign state
`output/theme_eval.csv` was generated after clustering and classification. Adi reviewed `output/theme_eval - myfirstfeedback.csv` and added 98 feedback notes showing systematic theme and signal misclassification, including complaints tagged into the wrong theme and dispute complaints mislabeled as repeated/persistent behavior.

Claude wrote `/Users/aditya/.claude/plans/eager-puzzling-puppy.md`, then revised that plan in `/Users/aditya/.claude/projects/-Users-aditya-Documents-Projects-signal/memory/project_taxonomy_redesign.md` after adversarial review. Treat the revised memory as the active handoff until this section is updated again.

Do not implement the original hybrid plan as written. The active direction is:
- Use CFPB `Issue` + `Sub-issue` as the evidence-bucket grounding layer, not as the final product insight.
- Mine taxonomy from the full TransUnion company dataset, not only the current pattern-filtered subset.
- Require a curated company-level taxonomy file; do not silently fall back to free clustering when it is missing.
- Assign complaints to curated evidence buckets using narrative-first model classification. CFPB `Issue` + `Sub-issue` is a hint, not the source of truth, because CFPB rows can be misfiled.
- Do not let the model invent buckets. It must choose from the curated taxonomy plus `Other/Unclassified`.
- Use row-level assignment rationales so incorrect bucket placement is auditable in `output/theme_eval_taxonomy_signals.csv`.
- Generate PM-facing signals from narratives inside each populated evidence bucket. Signals must be more useful than raw CFPB labels.
- Keep LLM value focused on narrative-first bucket assignment, signal synthesis, and hypothesis generation. CFPB metadata is only grounding context.
- Keep classification after evidence assembly and signal synthesis.

Read-only validation on 2026-05-06 confirmed the CFPB taxonomy is strong enough to anchor themes: full TransUnion top 8 Issue/Sub-issue combinations cover 91.5% of rows, top 10 cover 94.3%, and top 12 cover 95.9%. The current dispute-pattern reproduction showed top 8 coverage of 92.8%, top 10 of 95.1%, and top 15 of 98.1%.

---

## Incidents and architectural decisions
See `docs/engineering-log.md` for full incident history (consolidation token failures, cluster identity bug fix, taxonomy assignment cache/resume behavior).

## Current eval gates
Run `/Users/aditya/venvs/support/bin/python eval_bucket_golden.py` before the expensive taxonomy export when changing taxonomy prompts or bucket definitions. It checks known hard cases such as identity-theft blocking, cross-bureau inconsistency, improper report use, and investigation-not-fixed.

## Current review checkpoint
As of 2026-06-24, Adi's first pass on `output/theme_eval_taxonomy_signals.csv` looked good so far. This is enough to continue building scoring and PM brief generation, but not a claim that every exported row has been exhaustively audited.

## Install safety
See global AGENTS.md and shared_context.md for NPM install safety rules.

## Provider swap — OpenRouter (2026-07-31)

All four model call sites now go through OpenRouter instead of the Anthropic SDK directly. `src/llm_client.py` holds the one shared client constructor (`get_client()`), reading `OPENROUTER_API_KEY` and pointing the `openai` SDK at `https://openrouter.ai/api/v1`.

The "Model constants" table above is now stale: it lists pre-swap Anthropic-native model IDs. Current constants hold OpenRouter model slugs instead:
- `ingest.py` `FILTER_MODEL` → `anthropic/claude-haiku-4.5`
- `cluster.py` `CLUSTER_MODEL` → `anthropic/claude-sonnet-4.5`
- `classify.py` `CLASSIFY_MODEL` → `anthropic/claude-haiku-4.5`
- `narrate.py` `NARRATE_MODEL` → `anthropic/claude-sonnet-4.5`

Response parsing also changed: OpenAI-style `response.choices[0].message.content` / `response.choices[0].finish_reason` (`"length"` on truncation) replace Anthropic's `response.content[0].text` / `response.stop_reason` (`"max_tokens"`). `test_key.py` is now a live OpenRouter smoke test and skips when `OPENROUTER_API_KEY` is absent.
