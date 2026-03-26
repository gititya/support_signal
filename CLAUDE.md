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
  cluster.py       ← Batch clustering via Sonnet → hierarchical consolidation
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

## ⚠ Known limitation: LLM consolidation token ceiling

**What happened:** On 2026-03-27, clustering 2,000 complaints across 20 batches of 100 produced 214 raw clusters. Sending all 214 to a single consolidation call exceeded the model's output token limit (even at max_tokens=8096), truncating the JSON mid-stream and crashing the parser. This cost $4 and 1.5 hours.

**Root cause:** Each cluster in the consolidation output costs ~400 tokens. With 214 input clusters, the model's attempt to produce ~50 output clusters easily blows past 8096 tokens.

**Guardrail in place (`cluster.py`):**
- `MAX_CLUSTERS_PER_CONSOLIDATION = 30` — hard limit per consolidation call
- `stop_reason == "max_tokens"` check in `_call_model` — raises a descriptive error immediately instead of silently passing broken JSON to `json.loads`
- `_consolidate()` automatically uses hierarchical consolidation when cluster count exceeds the limit: splits into sub-groups → consolidates each → final pass

**Rule for future work:** Never send more than 30 clusters to a single consolidation call. If you change `BATCH_SIZE` or the clustering prompt produces more clusters per batch, check the math: `(2000 / BATCH_SIZE) × avg_clusters_per_batch` must stay ≤ 30 for single-pass consolidation, or hierarchical kicks in automatically.

**Batch caching:** `cluster.py` caches batch results to `/tmp/signal_batch_cache/` keyed by pattern + complaint count + model. If consolidation fails, reruns skip the expensive batch phase.
