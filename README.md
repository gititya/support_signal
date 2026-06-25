# Signal

Signal is a B2C support-intelligence proof of work: it turns public CFPB complaint narratives into a PM-ready brief about a recurring customer support pattern.

The demo artifact is the generated brief: [`output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md`](output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md).

For the current run, Signal analyzes TransUnion CFPB complaints about customers who say they cannot dispute incorrect information on their credit report. It clusters complaint narratives into evidence buckets, synthesizes product-facing signals, classifies each signal, scores severity, and renders a concise PM brief with examples and cautious root-cause hypotheses.

## Why this exists

Support data is rich but politically low-status: it often contains early product evidence, but it arrives as messy narratives, escalations, and repeated complaints rather than clean analytics. Signal shows how support-originated evidence can be translated into product language without pretending it is telemetry.

This repo is intentionally B2C and CFPB-shaped. It started from a consumer-finance support domain, not an internal B2B ticketing workflow. Multi-source corroboration is future work; Phase 1 uses CFPB complaint narratives only and labels confidence as directional.

## What the generated brief shows

The committed brief gives a hiring manager or reviewer the product result without requiring an API key or paid model run:

- The investigated pattern and source window.
- The strongest PM-facing signal.
- Severity and confidence.
- Evidence buckets and complaint volume.
- Cautiously framed root-cause hypotheses.
- Raw complaint samples.
- A clear "what this is not" section to prevent overclaiming.

The current demo brief remains single-source. It does not claim total affected users, product telemetry, proof of root cause, or evidence beyond CFPB complaints.

## How it works

Signal's current architecture is frozen around a buckets-first, narrative-first pipeline:

1. `src/ingest.py` loads CFPB complaint CSV data, filters to TransUnion, keyword-filters the support pattern, and caps analysis at 2,000 rows.
2. `src/cluster.py` assigns complaint narratives into curated evidence buckets from `config/taxonomy/transunion.yaml`, using CFPB `Issue` and `Sub-issue` as grounding context rather than source of truth.
3. `src/cluster.py` then synthesizes PM-facing signals from populated buckets.
4. `src/classify.py` classifies signals after evidence assembly.
5. `src/score.py` applies deterministic severity and confidence scoring.
6. `src/narrate.py` renders the final PM brief with `templates/brief_pm.md.j2`.

Earlier free-form clustering was abandoned after real failure modes: consolidation hit token ceilings, recursive merging did not converge, and name-based cluster matching scrambled complaint indices. Those incidents are documented in [`docs/engineering-log.md`](docs/engineering-log.md). The point of the current design is not another taxonomy rewrite; it is a stable extraction layer that produces an inspectable brief.

## Reusable engine vs. domain layer

The reusable engine is segment-agnostic: corroborate against an independent listening post, assign evidence buckets, synthesize hypothesis-framed signals, apply a confidence ladder, and generate a narrative brief. The B2C domain layer is CFPB-specific: the public complaint CSV, the TransUnion taxonomy in `config/taxonomy/transunion.yaml`, and consumer-finance framing such as FCRA dispute language. To make this B2B, swap the listening post from CFPB complaints to internal tickets, NPS comments, or CSM notes; replace `config/taxonomy/` with a taxonomy for that workflow; keep the engine in `src/ingest.py`, `src/cluster.py`, `src/classify.py`, `src/score.py`, and `src/narrate.py`.

## Run it locally

Use the project virtual environment:

```bash
/Users/aditya/venvs/signal_venv/bin/python -m unittest discover -v
```

To run the live pipeline, set `ANTHROPIC_API_KEY` and provide the CFPB complaints CSV at `data/complaints.csv`:

```bash
/Users/aditya/venvs/signal_venv/bin/python signal.py
```

The default pattern is:

```text
customers unable to dispute incorrect information on their credit report
```

You can pass another pattern:

```bash
/Users/aditya/venvs/signal_venv/bin/python signal.py "customers receiving repeated identity theft denials"
```

Live runs send complaint narratives to the Claude API. The offline unit tests do not require an API key; the live key smoke test skips when `ANTHROPIC_API_KEY` is absent.

## Run it on your own support data

Signal currently expects a CFPB-shaped CSV. Required columns are:

```text
Date received
Consumer complaint narrative
Company
Complaint ID
Product
Sub-product
Issue
Sub-issue
Company response to consumer
Timely response?
Consumer disputed?
State
```

To try your own CFPB-format data, place the CSV at `data/complaints.csv`, make sure `Company` contains `TRANSUNION INTERMEDIATE HOLDINGS, INC.` or update the company constant in `src/ingest.py`, then run:

```bash
/Users/aditya/venvs/signal_venv/bin/python signal.py "customers unable to dispute incorrect information on their credit report"
```

The `--company` option does not exist yet; company selection is currently a code constant. The free-text pattern controls which rows survive keyword filtering, and the taxonomy controls how matched narratives become evidence buckets. For non-CFPB support data, adapt the CSV into this contract or change `src/ingest.py`, then replace `config/taxonomy/transunion.yaml` with buckets that fit the new domain.

Do not commit real customer support data. Real tickets and support narratives can contain customer PII. The repo ignores `data/`, generated `output/` files, `.env*`, and common credential file patterns; keep real datasets and exports out of git.

## What to look at

- Demo brief: [`output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md`](output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md)
- Engineering incidents: [`docs/engineering-log.md`](docs/engineering-log.md)
- Taxonomy: [`config/taxonomy/transunion.yaml`](config/taxonomy/transunion.yaml)
- Golden eval gate: [`eval_bucket_golden.py`](eval_bucket_golden.py)

## Status

Signal is a proof of work, not a production analytics product. The closeout target is a reviewer-readable repo with a credible generated brief, offline-runnable tests, and a clear seam between the reusable evidence engine and the CFPB-specific domain layer.
