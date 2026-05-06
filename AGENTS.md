# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## What this project does
Signal is a CLI tool that takes a free-text support pattern description, filters CFPB complaint CSV data for a target company, clusters complaints via Anthropic API with root-cause hypothesis generation, classifies by signal type, scores severity, and renders a Jinja2 markdown PM brief.

## Commands
```bash
# Use the project venv when default python is missing dependencies
/Users/aditya/venvs/signal_venv/bin/python -m pip install -r requirements.txt

# Run the tool
/Users/aditya/venvs/signal_venv/bin/python signal.py

# Run a single module test
/Users/aditya/venvs/signal_venv/bin/python test_cluster.py   # or any test_*.py in project root
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
- Assign complaints by exact taxonomy lookup only. Put unmatched complaints in `Other/Unclassified`; do not send unmatched rows to an LLM to choose the closest bucket.
- Generate PM-facing signals from narratives inside each populated evidence bucket. Signals must be more useful than raw CFPB labels.
- Keep LLM value focused on signal synthesis and hypothesis generation after deterministic bucket assignment.
- Keep classification after evidence assembly and signal synthesis.

Read-only validation on 2026-05-06 confirmed the CFPB taxonomy is strong enough to anchor themes: full TransUnion top 8 Issue/Sub-issue combinations cover 91.5% of rows, top 10 cover 94.3%, and top 12 cover 95.9%. The current dispute-pattern reproduction showed top 8 coverage of 92.8%, top 10 of 95.1%, and top 15 of 98.1%.

---

## Incidents and architectural decisions
See `docs/engineering-log.md` for full incident history (consolidation token failures, cluster identity bug fix).
