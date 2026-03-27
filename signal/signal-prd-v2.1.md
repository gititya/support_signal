# Signal — PRD v2.1
## Support Signal → Corroborated Evidence → Product Action

**Purpose of this document**: Build spec for a personal portfolio project called Signal. Paste into Claude Code as persistent context. Every design decision encodes domain expertise from years of doing this workflow manually at McAfee. The output brief is the product.

**What changed from v2**: Tightened Phase 1 scope (CFPB-only, Google Play moves to Phase 2). Reframed diagnostic reasoning as hypothesis generation, not diagnosis. Added "What This Is Not" to the brief template. Made competitive differentiation claims more honest. Added hallucination/overconfidence guardrails. Added README spec.

---

## Problem Statement

At B2C companies with high support volume, support data is rich but politically low-status. It rarely reaches product teams in a form they act on.

The person who sits between support and product (the user of this tool) already knows what's coming in through tickets. What they lack is:
1. A fast way to check whether the same pattern appears across independent listening posts
2. Reasoning that separates root causes hiding inside similar complaint language — framed as hypotheses for the user to validate, not as conclusions
3. A brief that translates support signal into the language product teams act on

Signal is a corroboration engine with diagnostic intelligence and brief generation. The user brings the signal. Signal brings the evidence and the narrative.

---

## How This Is Different From Enterpret / Chattermill / DevRev

These tools answer: **"What are customers saying across channels?"**
Signal answers: **"Is what support is hearing real, how big is it, and what should product do about it?"**

Specifically:
- **Enterpret** ($25M raised, 50+ source integrations) does multi-source ingestion, adaptive taxonomy, and cohort-level analytics integration via Amplitude/Mixpanel. It's an enterprise platform requiring integration setup. It likely does some version of root-cause separation within its clustering — they just don't market it that way. **The honest difference**: Signal is a lightweight personal tool that does a focused version of this workflow without enterprise integration, and its primary output is a narrative brief, not a dashboard or query interface.
- **Chattermill** does unified sentiment analysis with anomaly detection. CX/support-team focused, not product-team focused.
- **DevRev** ($100M+ raised) bridges support tickets to engineering work items. It's about workflow integration, not signal intelligence.

Signal's differentiators for the demo:
1. **Root-cause hypothesis generation**: "500 complaints about login problems" → suggests 3 possible distinct root causes (token bug, password confusion, bad error message) each requiring a different team. Framed as hypotheses for the analyst to confirm, not as diagnoses.
2. **Confidence ladder framing**: Every signal is explicitly labeled by confidence level — directional (single source), corroborated (multiple independent sources), validated (confirmed against product analytics). No existing tool makes epistemic honesty a first-class feature.
3. **The brief as product**: Output is a narrative document routed to the right audience, not a dashboard.
4. **The iceberg calculation** (Phase 3, future): Expressing complaint volume as a percentage of total behaviorally-affected users. 300 complaints about checkout → analytics shows 15,000 users abandoned at same step → real impact is 50x. Deferred but architecturally planned.

**What this demonstrates to a hiring manager**: Domain expertise in the support-to-product workflow, ability to build with AI agents, and the judgment to scope a real problem into a working tool. The portfolio value is in the taste and the execution, not in defensibility.

---

## The User

**You.** A support analyst, product supportability lead, or CX person who sits between support and product. You live in the ticket queue. You already see the patterns. You need a tool that:
- Confirms whether the pattern shows up in other channels (or is support-only noise)
- Suggests possible root causes hiding in similar complaint language (you validate)
- Generates a first-draft brief you can edit and send to the right stakeholder

You are not building dashboards. You are building a case.

---

## Workflow (The Confidence Ladder)

### Step 1: You Bring the Signal
You either:
- **Describe a pattern** in your own words: "We're seeing a spike in complaints about failed transfers after the app update"
- **Upload a batch of tickets** (Phase 2) and the tool helps surface candidate themes from the data

Phase 1 supports the describe path only. Upload is a Phase 2 addition.

### Step 2: The Tool Searches for Corroboration
For each signal, the tool searches independent listening posts:
- Phase 1: CFPB Consumer Complaint Database only
- Phase 2 adds: Google Play reviews, Apple App Store reviews, Reddit

It's looking for: are other people, in other channels, reporting the same pattern independently?

### Step 3: Clustering & Root-Cause Hypothesis Generation
The tool clusters signal from all available sources into problem themes. It then generates root-cause hypotheses:

The tool doesn't just group by similar language. It suggests whether complaints that sound different might share a root cause, and whether complaints that sound similar might actually be different problems.

Example: "app crashes when I try to pay" and "biometric login keeps failing" might both stem from the same authentication flow issue. "I can't log in" might be three different problems: a technical failure, a confusing password reset flow, and users not realizing they need to verify email first.

**CRITICAL: These are hypotheses, not diagnoses.** The tool frames them as "Possible root cause: ..." and "This may indicate ..." — never as certain conclusions. The user validates against their product knowledge and analytics. Overconfident root-cause attribution that turns out to be wrong is worse than no attribution at all, because it sends teams down the wrong path.

The output is X ranked themes (however many emerge), each with:
- A problem description
- Evidence from each source that contributed
- Corroboration strength: how many independent channels, growing or isolated
- Root-cause hypothesis: what the underlying problem might be (framed as hypothesis)

### Step 4: You Check Product Analytics (Manual Step)
You take the top themes and go to Amplitude / Mixpanel / whatever your company uses. You check:
- Is there a funnel drop-off at the step support is hearing about?
- How many total users hit that flow vs. how many complained?
- Is the behavioral data consistent with the complaint pattern?

You bring the key numbers back into Signal.

> **⚠️ ARCHITECTURE CROSSROADS — Analytics Integration**
> 
> This step is currently manual. Three future options exist, and the choice depends on deployment context:
>
> **Option A: Stay manual (current)**  
> You go to Amplitude, check the data, come back. Signal has a form field where you input key metrics (affected users, funnel drop-off %, time period). Simplest. Respects that choosing the right metric requires human judgment.
>
> **Option B: Paste/upload analytics data**  
> You export a CSV or screenshot from Amplitude and feed it back into Signal. The tool incorporates it into the brief automatically. More integrated, still human-driven.
>
> **Option C: Direct API integration**  
> Signal connects to Amplitude/Mixpanel and pulls relevant metrics automatically. Enterprise product version. Massive scope expansion.
>
> **Why this doesn't block the build**: All three options produce the same downstream output — a set of numbers (affected user count, funnel drop-off %, behavioral confirmation) that get woven into the brief. The brief template has a section for analytics-validated impact regardless of how the numbers arrive. Swapping the input mechanism later is a contained module change.
>
> **For the demo**: Use mock/synthetic analytics data to show the full brief output including the iceberg calculation.

### Step 5: Classification (Always Last)
Only after all evidence is assembled does the tool classify. Classification determines who acts on it and how:

- **Defect**: Something is broken. Telemetry confirms abnormal behavior. → Engineering
- **UX Friction**: It works but the experience is confusing or frustrating. → Design
- **Knowledge Gap**: The product works fine; users don't understand it. → PM / Content / Onboarding
- **Monetization Opportunity**: Users asking for something that doesn't exist. Willingness to pay/switch implied. → Growth / PM

Classification is the *conclusion*, not a step. It happens after you've seen all the evidence, not before.

### Step 6: Brief Generation
The tool generates a first-draft narrative brief tailored to the classified audience. You edit, add context the tool can't know, and ship it.

The templates are opinionated. They encode domain knowledge about what each audience cares about and how they make decisions. The first draft should be 70-80% there.

**Where the domain knowledge actually lives**: The prompts that generate the brief content — not the template structure — are where the real expertise gets encoded. The prompts should include framing instructions specific to each audience type, examples of what good vs. bad briefs look like, and the editorial voice that makes the output read like it was written by someone who's done this job, not by a generic AI summary.

---

## Phase Breakdown

### Phase 1: Signal Engine — CFPB Only (One Weekend, 6-10 hrs)
**Must be independently impressive. Must ship by end of weekend.**

**What it does**: You describe a support pattern → the tool searches CFPB complaints for corroboration → clusters the signal → generates root-cause hypotheses → produces a markdown brief.

**Input**: Free-text description of a support pattern + a target company name.

**Data source**:
- CFPB Consumer Complaint Database (free API, no key, real narratives)
  - API: `https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/`
  - Fields: complaint_id, date_received, product, sub_product, issue, sub_issue, consumer_complaint_narrative, company, company_response, timely, consumer_disputed
  - **CRITICAL**: Download CSV snapshot immediately as fallback. Agency under severe political pressure — database still active as of early 2026 but future uncertain. Staff cut 88%, funding halved by law (July 2025 reconciliation bill). Complaint portal still open but capacity degraded.
  - Target: 500-2,000 complaints with narratives for a single company.

**Why CFPB only in Phase 1**: Adding Google Play scraping introduces a second integration point, rate limit debugging, and the hard problem of matching app review themes to complaint themes. That's scope that threatens shippability. The architecture is ready for more sources — Phase 2 plugs them in. Phase 1 proves the pipeline works end-to-end with one source.

**Pipeline**:
1. Parse user's signal description → extract key terms and pattern
2. Search/filter CFPB complaints for matching company + relevant issues
3. Send user's signal description + matching complaints to Claude → cluster into themes with root-cause hypotheses
4. Score each theme: volume, trend, sentiment, hypothesis confidence
5. Classify signal type (defect / UX friction / knowledge gap / monetization opportunity)
6. Generate brief using PM template via Jinja2
7. Render as markdown file

**Minimum viable version (ruthlessly scoped)**:
- Hardcode one company — pick before build session starts (see Demo Company section below)
- Input: a text string typed by the user (no upload, no CLI flags)
- Data: pre-downloaded CSV, not live API calls (eliminates network dependency during build)
- One LLM call for clustering + hypothesis generation (if <100 complaints in filtered set) or batched (if >100)
- One output template (PM brief only)
- No config files. No error handling beyond basics.
- **The demo is the contrast**: show the raw CSV → show the brief. That's it.

**Success criteria**: A person with no context reads the output brief and can answer:
1. What is the problem?
2. How confident should I be that it's real?
3. How bad is it?
4. What should I do about it?

If any answer is unclear, the brief has failed.

---

### Phase 2: Corroboration + Batch Upload (One Weekend)
**Depends on**: Phase 1

**What it adds**:
- Google Play reviews as second corroboration source (`google-play-scraper`, no key)
- Reddit as third source (`praw`, free OAuth)
- Apple App Store reviews as optional fourth (`app-store-scraper`)
- Upload a batch of tickets (CSV) instead of describing a pattern
- Brief now shows cross-source corroboration evidence
- Confidence label upgrades from "Directional" to "Corroborated" when multiple sources agree

**New dependencies**: `google-play-scraper`, `praw` (requires OAuth app at reddit.com/prefs/apps), `app-store-scraper`

**The demo upgrade**: "Phase 1 found this pattern in CFPB data. Phase 2 found the same pattern independently in Google Play reviews and Reddit. Confidence just went up."

---

### Phase 3: Analytics Stub + Audience Routing (One Weekend)
**Depends on**: Phase 1 (Phase 2 is nice-to-have)

**What it adds**:
- Analytics input section: manual form field for key metrics from Amplitude/Mixpanel
- Iceberg calculation: complaint volume as % of total affected users (mock data for demo)
- Multiple brief templates: Engineering, PM, Design, Growth
- Each template emphasizes different aspects of the same signal
- Routing logic: Defect → Engineering, UX Friction → Design, Knowledge Gap → PM/Content, Monetization → Growth/PM

**Engineering Brief**: Technical reproduction context, affected platforms, severity as system impact. Action: investigate/reproduce/hotfix.

**PM Brief**: User impact, revenue/churn risk, strategic alignment. Action: prioritize/deprioritize/needs-more-data.

**Design Brief**: User journey breakdown, expectation vs. reality, friction points. Action: audit flow/user research/redesign.

**Growth Brief**: Churn signal, acquisition vs. retention impact. Action: retention problem or onboarding problem?

---

### Phase 4: Live Pipeline (DO NOT BUILD YET)
Only if Phases 1-3 are proven and there's a real deployment target.

---

## Demo Company Selection

**Pick before the build session starts.** You need a company with:
- Rich CFPB complaint narratives (many complaints with consumer-submitted text)
- Ideally a Google Play app (for Phase 2)
- A product with enough complexity that support complaints span multiple root causes

**Strong candidates** (verify CFPB volume before committing):
- **Cash App** (Block/Square) — high complaint volume, mobile app, payment flow issues
- **Chime** — neobank, high complaint volume, mobile-first
- **Venmo** (PayPal) — payments, transfer issues, app reviews
- **PayPal** — massive complaint volume, broad product surface area

Download the CSV for your chosen company NOW. Filter for narratives only (`has_narrative=true`). Aim for 500-2,000 complaints.

---

## Output Template — Signal Brief

```markdown
# SIGNAL BRIEF
**[Company Name]** — [Product/Sub-product] — [Date Range]

**Prepared by**: Signal (AI-powered product intelligence)
**Generated**: [timestamp]

---

## At a Glance
| Field | Value |
|-------|-------|
| Signal Type | [Defect / UX Friction / Knowledge Gap / Monetization Opportunity] |
| Confidence | [Directional (single source) / Corroborated (X independent sources) / Validated (analytics-confirmed)] |
| Severity | [Critical / High / Medium / Low] |
| Volume | [N] signals across [X] channels |
| Trend | [↑ Increasing / → Stable / ↓ Declining] |
| Recommended Audience | [Engineering / PM / Design / Growth] |

---

## Executive Summary
[3-4 sentences. Lead with "so what." A PM reads this in 10 seconds and decides whether to keep reading. No jargon. No hedging. State the finding, the confidence level, the impact, and the recommended action.]

---

## Signal
[What is the pattern? Describe in plain language. Include the root-cause hypothesis — what the underlying problem might be. Be specific about the failure mode, the user experience, or the gap. Frame root causes as "This pattern is consistent with..." or "Evidence suggests this may stem from..." — never as certain diagnosis.]

---

## Evidence

### Support Signal (User-Provided)
[Summary of what the user described or what emerged from ticket batch analysis]

### Corroboration
For each secondary source:
- **[Source Name]**: [N] of [M] signals match ([X]%). Corroboration strength: [Strong/Moderate/Weak/None].
- Representative: "[short quote]"

[If Phase 1 / single source: "Corroboration pending — this analysis is based on a single data source (CFPB complaints). Treat as directional signal until validated against independent listening posts."]

### Root-Cause Hypotheses
[If the tool identified multiple possible root causes within similar complaints:]
"These [N] complaints about '[similar language]' may represent [X] distinct problems:
1. **[Hypothesis A]**: [evidence and reasoning]. Suggested owner: [team].
2. **[Hypothesis B]**: [evidence and reasoning]. Suggested owner: [team].
3. **[Hypothesis C]**: [evidence and reasoning]. Suggested owner: [team].

These are hypotheses based on complaint language patterns. Validate against product architecture knowledge and telemetry before acting."

### Counter-Evidence
[Anything that contradicts the signal? Company response data suggests resolution? Other signals point to improvement? Be honest — credibility comes from acknowledging complexity.]

---

## Impact Assessment
- **Who is affected**: [User segment, platform, geography if available]
- **Corroboration confidence**: [How many independent sources agree? Is the signal growing?]
- **Iceberg estimate** (if analytics available): [X] complaints represent an estimated [Y] affected users ([Z]% of users who hit this flow). [Or: "Analytics data not yet available — treat complaint volume as directional only."]
- **Business risk**: [Churn signal? Rating decline? Regulatory exposure?]
- **If ignored**: [What happens in 30/60/90 days?]

---

## Recommended Action
[Specific. Actionable. Addressed to the right team. Not "investigate further." Include interim mitigation if applicable.]

---

## Raw Signal Samples
[3-5 representative excerpts. Choose for diversity — clearest, most emotional, most detailed, edge case. These are the receipts.]

1. > "[Excerpt]" — [Source], [date]
2. > "[Excerpt]" — [Source], [date]  
3. > "[Excerpt]" — [Source], [date]

---

## What This Is Not
This analysis is based on consumer complaint data, which represents a small fraction of total users. Complainants are self-selected and not representative of all user experiences. Root-cause hypotheses are inferred from complaint language patterns and should be validated against product telemetry and architecture knowledge before driving engineering decisions. Confidence level reflects corroboration status, not certainty.

---

## Methodology
This analysis was generated from user-described support signal corroborated against [N] CFPB consumer complaints filed between [start] and [end], filtered for [company] / [product]. Complaints without consumer narratives were excluded. Signal clustering and root-cause hypothesis generation performed via Claude API (Anthropic). [If Phase 2+: Corroboration checked against [N] Google Play reviews, [N] Reddit threads from r/[sub], etc.]

Confidence levels: Directional (single source, treat as hypothesis), Corroborated (2+ independent sources agree), Validated (analytics data confirms population-level impact).

Signal types: Defect (technical failure), UX Friction (confusing/frustrating experience), Knowledge Gap (user education problem), Monetization Opportunity (unmet need with willingness to pay/switch).
```

---

## README.md Spec

The README is the first thing a hiring manager sees. It must sell the project in 30 seconds.

**Structure**:
1. **One-liner**: "Signal turns customer support noise into product action — corroborating support signal across independent listening posts and generating narrative briefs that product teams act on."
2. **The contrast** (visual): Show a screenshot or text block of raw complaint data (messy, 1,200 rows) next to the generated brief (clean, 3 pages, actionable). This is the entire pitch.
3. **Why this exists**: 2-3 sentences on the problem — support data is rich but politically low-status, nobody translates it into product-team language.
4. **How it works**: The confidence ladder in 4 bullet points. You bring the signal → tool corroborates → tool hypothesizes root causes → tool generates a routed brief.
5. **What I built with**: Python, Claude API, public data sources. "Built with AI agents (Claude Code) — I designed the workflow and domain logic, the AI wrote the code."
6. **Run it yourself**: `pip install`, set API key, `python signal.py`.
7. **What's next**: Brief mention of Phase 2/3 roadmap.

**Do not include**: lengthy technical architecture explanations, dependency lists longer than 5 items, or anything that reads like documentation instead of a pitch.

---

## Technical Stack

- **Language**: Python 3.10+
- **LLM**: Claude API (Anthropic) — claude-sonnet-4-5-20250514 for clustering/corroboration, same or opus for narrative generation
- **Key libraries**: `anthropic`, `pandas`, `jinja2`, `markdown`
- **Phase 2 additions**: `google-play-scraper`, `praw` (Reddit), `app-store-scraper`
- **No frontend for Phase 1**. Output is rendered markdown or HTML. This is a pipeline, not a web app.
- **No database**. CSV/JSON files as data store. Keep it simple.

---

## File Structure (Target)

```
signal/
├── README.md
├── requirements.txt
├── signal.py              # Main entry point
├── data/
│   └── complaints.csv     # Downloaded CFPB data (git-ignored)
├── src/
│   ├── __init__.py
│   ├── ingest.py          # Load and clean data from all sources
│   ├── corroborate.py     # Search external listening posts (Phase 2+)
│   ├── cluster.py         # LLM-powered clustering with root-cause hypotheses
│   ├── classify.py        # Signal type classification (always last)
│   ├── score.py           # Severity and corroboration strength scoring
│   ├── narrate.py         # Brief generation
│   └── analytics.py       # Phase 3: analytics input handling + iceberg calc
├── templates/
│   ├── brief_pm.md.j2     # PM brief template
│   ├── brief_eng.md.j2    # Engineering brief (Phase 3)
│   ├── brief_design.md.j2 # Design brief (Phase 3)
│   └── brief_growth.md.j2 # Growth brief (Phase 3)
└── output/
    └── (generated briefs go here)
```

---

## Day-One Checklist

1. Pick demo company (see Demo Company Selection above)
2. Download CFPB complaint CSV for that company (narratives only)
3. Set `ANTHROPIC_API_KEY` environment variable
4. `pip install anthropic pandas jinja2`
5. Paste this PRD into Claude Code as context
6. Build.

---

## Constraints & Principles

1. **Output is the product.** Every decision: "Does this make the brief more useful to a PM?" If not, skip it.
2. **Each phase is independently demoable.** Phase 1 alone must be impressive.
3. **No dashboards.** The output is a narrative document. PMs act on stories backed by evidence, not charts.
4. **Depth over breadth.** One company analyzed brilliantly beats five analyzed superficially.
5. **The LLM is the engine, not the product.** The workflow design is the IP. The LLM powers each step.
6. **Public data only.** CFPB, app store reviews, Reddit. No enterprise access required.
7. **Weekend-buildable phases.** If it can't be built in 6-10 hours, scope down.
8. **Classification is always last.** It's the conclusion, not a starting point.
9. **Honesty builds credibility.** Every brief labels its confidence level. Root causes are hypotheses. The tool never overstates what it knows.
10. **Hypotheses, not diagnoses.** Root-cause suggestions are framed as possibilities for the analyst to validate, never as certain conclusions. Overconfident wrong answers are worse than no answer.
