# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does
Signal is a CLI tool that takes a free-text support pattern description, filters CFPB complaint CSV data for a target company, clusters complaints via Claude API with root-cause hypothesis generation, classifies by signal type, scores severity, and renders a Jinja2 markdown PM brief.

## Commands
```bash
# Install dependencies (use the signal_venv)
pip install -r requirements.txt

# Run the tool
python signal.py

# Run a single module test
python test_cluster.py   # or any test_*.py in project root
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

---

## Incidents and architectural decisions
See `docs/engineering-log.md` for full incident history (consolidation token failures, cluster identity bug fix).

## Install safety
See global CLAUDE.md and shared_context.md for NPM install safety rules.

## Closeout state (2026-06-25)

The taxonomy branch now includes scoring, PM brief rendering, and a committed demo brief. Treat extraction as frozen unless a concrete verification blocker appears. Closeout work should focus on packaging: reviewer-readable README, offline `unittest` coverage, stale duplicate cleanup, and accurate safety notes for CFPB-shaped bring-your-own data. `test_key.py` is a live Anthropic smoke test and should skip when `ANTHROPIC_API_KEY` is absent.

## Provider swap — OpenRouter (2026-07-31)

All four model call sites now go through OpenRouter instead of the Anthropic SDK directly. `src/llm_client.py` holds the one shared client constructor (`get_client()`), reading `OPENROUTER_API_KEY` and pointing the `openai` SDK at `https://openrouter.ai/api/v1`. This replaces the per-file `anthropic.Anthropic(api_key=...)` construction described in "Commands"/"Model constants" above.

The "Model constants" table above is now stale: it lists pre-swap Anthropic-native model IDs. Current constants hold OpenRouter model slugs instead:
- `ingest.py` `FILTER_MODEL` → `anthropic/claude-haiku-4.5`
- `cluster.py` `CLUSTER_MODEL` → `anthropic/claude-sonnet-4.5`
- `classify.py` `CLASSIFY_MODEL` → `anthropic/claude-haiku-4.5`
- `narrate.py` `NARRATE_MODEL` → `anthropic/claude-sonnet-4.5`

Response parsing also changed: OpenAI-style `response.choices[0].message.content` and `response.choices[0].finish_reason` (`"length"` on truncation) replace Anthropic's `response.content[0].text` / `response.stop_reason` (`"max_tokens"`). `test_key.py` is now a live OpenRouter smoke test and skips when `OPENROUTER_API_KEY` is absent.
