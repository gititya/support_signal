# Signal

**Free-form clustering of complaints failed three ways before I gave the model a fixed set of buckets and made it write only inside them. The brief carries a "what this is not" section on purpose.**

Signal turns public CFPB complaint narratives into a PM-ready brief about a recurring customer support pattern.

Demo brief, no key required: [`output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md`](output/pm_brief_customers-unable-to-dispute-incorrect-information-on-their-c_20260624-222400.md)

## The problem

Support data carries early product evidence, but it arrives as narratives, not analytics. Most attempts to mine it produce a confident theme list a PM cannot act on and cannot check: the themes look plausible, but nobody can see why a given complaint landed in a given theme.

I built Signal to do the narrower, checkable version of that job for one domain: TransUnion credit-report disputes, from the public CFPB complaint database.

## What it does

1. `src/ingest.py` loads the CFPB complaint CSV, filters to the target company, and keyword-matches the support pattern, capped at 2,000 rows.
2. `src/cluster.py` assigns each matched complaint into a curated evidence bucket, using the narrative first and the CFPB `Issue`/`Sub-issue` fields as a hint, not a source of truth.
3. `src/cluster.py` synthesizes a PM-facing signal from each populated bucket, with a cautiously framed root-cause hypothesis.
4. `src/classify.py` classifies each signal by type (Defect, UX Friction, Knowledge Gap, Monetization Opportunity), after evidence assembly, never before.
5. `src/score.py` applies deterministic severity scoring — same inputs, same score, every time.
6. `src/narrate.py` renders the PM brief from `templates/brief_pm.md.j2`.

Only one domain has been run: TransUnion credit-report disputes from a CFPB CSV. The pipeline shape may be reusable, but a new domain would need a new source, taxonomy, configuration, and validation; this repo does not prove that transfer.

| Constant | File | Model (via OpenRouter) |
|---|---|---|
| `FILTER_MODEL` | `src/ingest.py` | `anthropic/claude-haiku-4.5` |
| `CLUSTER_MODEL` | `src/cluster.py` | `anthropic/claude-sonnet-4.5` |
| `CLASSIFY_MODEL` | `src/classify.py` | `anthropic/claude-haiku-4.5` |
| `NARRATE_MODEL` | `src/narrate.py` | `anthropic/claude-sonnet-4.5` |

## What I decided and why

1. **Buckets before signals.** A curated taxonomy assigns evidence into named buckets; the model only synthesises a signal within a bucket that already has complaints in it. Cost: the taxonomy is hand-written per domain, so a new domain is real work up front.
2. **Free-form clustering was abandoned after it failed three ways.** A single consolidation call hit the token ceiling on 216 clusters. Recursive merging never converged. Name-based matching between merge passes scrambled complaint indices. Full detail in [`docs/engineering-log.md`](docs/engineering-log.md). Cost: bucket assignment is less automatic, and it will not discover a theme nobody put in the taxonomy.
3. **Severity scoring is deterministic, not model-judged.** Same inputs, same score, and the rationale string states which rule fired. Cost: it cannot weigh a signal the rules do not encode.
4. **Single-source findings are labelled directional, and the brief carries a "what this is not" section.** Cost: the output is less quotable. That is the point — the fastest way to lose Product's trust is one confident number that turns out wrong.

## Evaluation

| What I tested | What happened |
|---|---|
| Bucket assignment against golden hard cases (`eval_bucket_golden.py`) | Checks known-hard rows — identity-theft blocking, cross-bureau inconsistency, improper report use, investigation-not-fixed — against `fixtures/golden_bucket_examples.csv`. Fails on any drift from the expected bucket. |
| Offline unit suite (`python -m unittest discover`) | 52 tests, no API key required: ingest filtering, cluster ID assignment and validation, taxonomy loading, classification, scoring, brief rendering. |
| Saved run behind the committed brief | 2,000 CFPB complaints, Dec 2025 – Mar 2026, TransUnion. Five signals covering 1,531 of the 2,000 complaints; top bucket (Investigation Did Not Fix Error) carried 556. |

There is no ground truth for signal quality — nothing checks whether the synthesised PM signal is the right read of a bucket's complaints. Bucket assignment is the only stage with an evaluation gate.

## Run it

Offline, no API key:

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -v
```

Model-backed, with an OpenRouter key and a CFPB CSV at `data/complaints.csv`:

```bash
export OPENROUTER_API_KEY
python signal.py "customers unable to dispute incorrect information on their credit report"
```

`--company` does not exist; company selection is a code constant in `src/ingest.py`.

## Run it on your own data

Required CSV columns:

```text
Date received, Consumer complaint narrative, Company, Complaint ID, Product, Sub-product,
Issue, Sub-issue, Company response to consumer, Timely response?, Consumer disputed?, State
```

Place the CSV at `data/complaints.csv`, match `Company` to the value checked in `src/ingest.py` (or edit that constant), and replace `config/taxonomy/transunion.yaml` with a curated bucket list for the new domain. Do not commit real support data — the repo ignores `data/`, `output/`, `.env*`, and common credential file patterns.

## Known limitations

1. Single source. No product telemetry, no independent listening post to corroborate against.
2. No ground truth for signal quality — only bucket assignment has an evaluation gate.
3. Company selection is a code constant, not a CLI flag.
4. The taxonomy is hand-written per company and does not transfer to a new domain without new work.
5. No claim about total affected users or proof of root cause. Hypotheses are framed as hypotheses, not findings.

## What would be needed to go further

Complaint narratives tell you who complained, not how many were affected. A stronger version would need a customer denominator and product evidence. Signal stops at the narrative half; no further build is planned in this portfolio pass.

## Copyright

Copyright © 2026 Aditya. All rights reserved.

This repository is public for review. No license is granted to reuse, modify, or distribute its contents.
