# Signal — Verified One-Pager

Last verified: 2026-05-25

## What Signal is

Signal is a CLI workflow that turns a support pattern into evidence-grounded product insight.

The user starts with a suspected problem they are hearing from support. Signal checks whether that pattern also appears in CFPB complaints for a target company, groups the evidence into grounded buckets, synthesizes PM-facing signals from the narratives, classifies the type of problem, and produces an artifact a product team can review.

In plain terms: Signal helps answer, "Is this support pain real, how is it showing up in the data, and what should product pay attention to?"

## What we are trying to achieve

Signal is trying to do three things well:

1. Corroborate support intuition with external evidence instead of relying on anecdote.
2. Translate noisy complaint data into clearer product signals that are more useful than raw CFPB labels.
3. Produce an output that helps a PM, designer, or engineer understand the problem, its likely shape, and what kind of action it points toward.

## Current product approach

The current repo direction is:

- Start with a free-text support pattern plus a target company dataset.
- Filter CFPB complaints for the company and the pattern.
- Assign each complaint deterministically into a curated evidence bucket using CFPB `Issue` + `Sub-issue`.
- Use the LLM after bucket assignment to synthesize one PM-facing signal per populated bucket.
- Keep root-cause language hypothesis-based, never factual.
- Run classification after signal synthesis, not before.

This is intentionally different from the earlier free-form clustering approach. The current architecture is "buckets first, signals second."

## What Signal is not trying to be

- Not a generic dashboard or voice-of-customer platform.
- Not an autonomous root-cause detector that claims certainty.
- Not a system that lets the model guess complaint buckets when the evidence does not fit.

The point is disciplined translation from evidence to product signal, not broad analytics theater.

## What the output should look like

### Target output

The intended end-state output is a narrative product brief. That brief should make four things immediately clear:

1. What user problem is showing up.
2. What evidence supports it.
3. What type of problem it appears to be.
4. What action the receiving team should consider.

At minimum, the brief should contain:

- The original support pattern being investigated
- The company and evidence window
- A ranked set of product signals
- For each signal:
  - signal name
  - short signal description
  - grounded evidence bucket
  - complaint volume
  - example complaint excerpts
  - root-cause hypotheses framed as hypotheses
  - signal type
  - recommended audience
  - classification rationale
- A short summary of what product should pay attention to next

### Current implemented output

As of 2026-05-25, the repo's working artifact is not yet the final narrative brief. The current concrete output is a review/export CSV at:

`output/theme_eval_taxonomy_signals.csv`

That file already contains the core structured ingredients for the future brief, including:

- `signal_name`
- `signal_description`
- `bucket_distinction`
- `evidence_bucket_name`
- `cfpb_issue`
- `cfpb_sub_issue`
- `root_cause_hypotheses`
- `signal_type`
- `recommended_audience`
- `classification_rationale`
- `complaint_count`
- `narrative_excerpt`

So the current state is:

- The evidence-grounding and signal-generation layer exists.
- The classification layer exists.
- The final brief-rendering layer is still the intended product output, not the current shipped artifact.

## Success criteria

Signal is succeeding if a product team can read the output and quickly answer:

1. What is the user problem?
2. Why should we believe it is real?
3. What kind of problem is it?
4. Which team should care first?
5. What should we investigate next?

If the output cannot answer those questions cleanly, it is not done.
