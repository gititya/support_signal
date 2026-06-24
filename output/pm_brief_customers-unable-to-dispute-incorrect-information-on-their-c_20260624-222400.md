# PM Brief: Investigation Closed Without Error Correction

## At a glance

- **Pattern investigated:** customers unable to dispute incorrect information on their credit report
- **Company/source:** TRANSUNION INTERMEDIATE HOLDINGS, INC. / CFPB complaint narratives
- **Date range:** 2025-12-18 to 2026-03-09
- **Complaints analyzed:** 2000
- **Signals found:** 11 (top 5 shown)
- **Main signal:** Investigation Closed Without Error Correction
- **Severity:** High (High volume)
- **Confidence:** Directional (single source)

## Executive summary

Across 2,000 CFPB complaints sampled between December 2025 and March 2026, five signals totaling 1,531 complaints point to a consistent breakdown at TransUnion: consumers who initiate formal disputes — including those citing specific FCRA provisions and submitting documentation — report receiving no corrective outcome. The failure appears concentrated not at dispute initiation but at resolution, where investigations close without errors being removed or updated. This analysis is directional and draws from a single source (CFPB complaints), so the full scope is unknown.

Consumers are reaching the formal dispute channel and still reporting no correction, which suggests the resolution layer — not dispute access — is where the process breaks down for TransUnion.

## Main signal

**Investigation Closed Without Error Correction**

Users submitted disputes with supporting documentation, received confirmation that an investigation occurred, but found the reported errors unchanged afterward — leaving them with no corrective outcome and no clear path forward. The process appears to close on paper while the underlying inaccuracy remains on the report.

- **Signal type:** Defect
- **Evidence bucket:** Investigation Did Not Fix Error
- **Complaint volume:** 556
- **Scoring rationale:** High severity based on high volume (556 CFPB complaints across 82 days, 2025-12-18 to 2026-03-09), signal type Defect, and evidence bucket 'Investigation Did Not Fix Error'. Confidence remains directional (single source) because this uses CFPB complaints only with 5 supporting samples and no product telemetry.

## Evidence

### 1. Investigation Closed Without Error Correction

Users submitted disputes with supporting documentation, received confirmation that an investigation occurred, but found the reported errors unchanged afterward — leaving them with no corrective outcome and no clear path forward. The process appears to close on paper while the underlying inaccuracy remains on the report.

- **Evidence bucket:** Investigation Did Not Fix Error
- **Bucket distinction:** Unlike buckets capturing disputes that are ignored or never acknowledged, this bucket specifically captures cases where an investigation was formally completed yet yielded no correction, meaning the failure occurs at the resolution stage rather than the intake or acknowledgment stage.
- **Signal type:** Defect
- **Severity:** High
- **Volume:** High volume (556 complaints)
- **Confidence:** Directional (single source)

### 2. Personal Record Inaccuracies That Survive Formal FCRA Disputes

Users are filing legally-framed disputes citing specific FCRA provisions to correct inaccurate personal information—unknown addresses, outdated records, unverified account details—yet the errors remain on their credit files, suggesting the dispute process is not producing corrections. The failure is not in initiating a dispute but in receiving a substantive, compliant outcome.

- **Evidence bucket:** Personal or Public Record Information Incorrect
- **Bucket distinction:** Unlike buckets focused on account-level errors such as incorrect balances or payment history, this bucket centers on personal and public record inaccuracies—wrong addresses, identity-adjacent data, and public record entries—where consumers invoke specific FCRA sections and report that corrections are not materializing despite formal submission.
- **Signal type:** Defect
- **Severity:** High
- **Volume:** High volume (317 complaints)
- **Confidence:** Directional (single source)

### 3. Incorrect Credit Account Data Goes Uncorrected Despite Formal FCRA Disputes

Users are filing legally-grounded formal disputes citing specific FCRA statutes to challenge inaccurate account details — including late payment dates, unverifiable collection entries, and data-breach-related errors — but the underlying data remains uncorrected on their credit files. The failure is not just awareness of inaccuracy; users have taken structured action and still report no resolution.

- **Evidence bucket:** Account Information Incorrect
- **Bucket distinction:** Unlike buckets centered on dispute process confusion or identity theft, this bucket is defined by users who already know their legal rights, cite specific FCRA provisions, and have submitted formal dispute letters — yet the factual inaccuracy in the reported account data itself remains unaddressed by creditors or bureaus.
- **Signal type:** Defect
- **Severity:** Medium
- **Volume:** Medium volume (242 complaints)
- **Confidence:** Directional (single source)

### 4. Foreign Account Data Blocking Dispute Resolution

Users discover accounts, inquiries, and addresses on their credit reports that they assert belong to someone else or were added without their authorization, and their attempts to dispute or remove this data through formal FCRA channels appear to go unresolved. The core failure is not just inaccurate data but the system's inability to act on disputes when the consumer cannot claim any relationship to the reported item.

- **Evidence bucket:** Information Belongs to Someone Else
- **Bucket distinction:** Unlike general inaccuracy disputes where the consumer acknowledges some connection to an account but contests a detail, this bucket centers on consumers who assert zero ownership or authorization—the disputed item is entirely foreign to them, often tied to identity theft—making standard verification workflows structurally inadequate because there is no legitimate account record on the consumer's side to reconcile against.
- **Signal type:** Defect
- **Severity:** Medium
- **Volume:** Medium volume (213 complaints)
- **Confidence:** Directional (single source)

### 5. Identity Theft Victims Blocked from Enforcing Statutory Credit Report Corrections

Users who have experienced identity theft or data breaches are invoking specific federal statutes (FCRA 605B) demanding bureau action within legally required timeframes, yet the fraudulent accounts and unauthorized inquiries remain on their reports despite submitted documentation. The failure point is not dispute awareness but bureau non-compliance with a legally mandated removal workflow.

- **Evidence bucket:** Fraud Alert or Security Freeze Problems
- **Bucket distinction:** Unlike general dispute-loop complaints, this bucket is specifically anchored to identity theft and data breach victims attempting to exercise a distinct statutory right (block under 15 U.S.C. 1681c-2) rather than disputing factual inaccuracies, making the failure a legal compliance gap at the credit bureau level rather than a data accuracy or furnisher problem.
- **Signal type:** Defect
- **Severity:** Medium
- **Volume:** Medium volume (203 complaints)
- **Confidence:** Directional (single source)

## Root-cause hypotheses

- This may indicate that bureaus are closing investigations procedurally — logging them as complete without conducting the substantive reinvestigation FCRA requires — effectively treating closure as resolution.
- Evidence suggests that furnishers are not updating or correcting data when dispute notifications are received from bureaus, and bureaus are accepting non-responses or unchanged data as sufficient to close the case.
- This pattern is consistent with a systemic gap where dispute outcomes are not communicated with enough specificity for consumers to understand why an error was retained, leaving them unable to escalate or provide targeted counter-evidence.

## Impact assessment

This appears most relevant to **Engineering** because the system is malfunctioning by closing investigations procedurally without conducting substantive reinvestigation or communicating corrective outcomes, failing to perform the core dispute resolution function.

The evidence is strong enough to justify investigation, but not strong enough to size affected users or business impact. This brief uses public CFPB complaint narratives only.

## Recommended action

Audit the end-to-end dispute resolution workflow — specifically the handoff between bureau intake, furnisher notification, and case closure logic — to determine whether investigations are being marked complete without substantive reinvestigation; prioritize the 605B identity theft intake path as a discrete sub-workflow to assess whether it is being routed through general dispute channels rather than a dedicated removal process.

## Raw complaint samples

### Sample 1 — CFPB complaint 20092971
- **Date:** 2026-03-09
- **State:** LA
- **CFPB category:** Incorrect information on your report / Information belongs to someone else

> I am submitting this complaint because my TransUnion credit report contains information that appears inaccurate or unverifiable. I have attempted to dispute these items previously, yet they continue to appear without proper validation. 
> 
> The following accounts require investigation : Charged-Off Accounts XXXX  Account Number : XXXX Date Opened : XX/XX/XXXX Balance : {$0.00} XXXX  Account Number : XXXX Date Opened : XX/XX/XXXX Balance : {$560.00} XXXX XXXX  Account Number : XXXX Date Opened : XX/XX/XXXX Balance : {$180.00} XXXX XXXX  Account Number : XXXX Date Opened : XX/XX/XXXX Balance : {$430.00} Late Payment Reporting XXXX XXXX Account Number : XXXX XXXX XXXX Account Number : XXXX The late payment reporting associated with these accounts appears inaccurate or incomplete. I am requesting proper verification of the payment history being reported.
> 
> I respectfully request that TransUnion 

### Sample 2 — CFPB complaint 18335263
- **Date:** 2025-12-29
- **State:** AL
- **CFPB category:** Incorrect information on your report / Personal information incorrect

> Formal Notice of Sham Investigation and Continued FCRA Noncompliance To : Experian Information Solutions , Inc., TransUnion LLC, Equifax Information Services LLC, This letter serves as formal notice of your continued failure to comply with the Fair Credit Reporting Act ( FCRA ) and your engagement in what constitutes a sham investigation in response to my prior disputes. 
> Despite my submission of clear, detailed disputes supported by documentation, you failed to conduct a reasonable reinvestigation as mandated by 15 U.S.C. 1681i ( a ) ( 1 ). Instead of performing an independent and good-faith review, you relied on automated responses and unverifiable furnisher confirmations, while disregarding the evidence I provided. Such conduct does not satisfy the statutory standard of reasonableness and materially misrepresents the results of your so-called investigation. 
> Your ongoing violations in

### Sample 3 — CFPB complaint 18247103
- **Date:** 2025-12-23
- **State:** CA
- **CFPB category:** Problem with a company's investigation into an existing problem / Their investigation did not fix an error on your report

> The reported entries are inaccurate and do not reflect my true payment history. I have made several attempts to have these discrepancies reviewed and corrected, but no substantial action has been taken. Even after submitting all required documentation and following up multiple times, the errors remain unresolved. This situation has created financial hardship and has significantly impacted my well-being. Addressing these inaccuracies has become a stressful and exhausting process. 
> According to the Fair Credit Reporting Act ( FCRA ), I am entitled to a credit report that truthfully represents my financial history, including the prompt correction of any outdated or incorrect information. I respectfully request immediate action to correct or remove these late payment entries. Failure to do so would constitute a violation of my rights under federal law. 
> Thank you for your prompt attention to

### Sample 4 — CFPB complaint 18218233
- **Date:** 2025-12-22
- **State:** CA
- **CFPB category:** Problem with a company's investigation into an existing problem / Their investigation did not fix an error on your report

> The listed entries remain unverified and appear inaccurate. Despite numerous efforts to have these discrepancies properly addressed, no substantial action has been taken. I have submitted all necessary documentation and followed up multiple times, yet the errors continue to appear. This ongoing inaction has resulted in financial difficulties and has negatively impacted my overall well-being. The XXXX  and XXXX  strain caused by these unresolved issues has been considerable. Under the Fair Credit Reporting Act ( FCRA ), I have the right to an accurate and fair credit report, which includes the removal of any incorrect or unverified information. I strongly urge you to take prompt action to investigate and correct these items, as continued failure to do so may constitute a violation of my rights under federal law.

## What this is not

- Not a claim about total affected users.
- Not product telemetry.
- Not proof of root cause.
- Not a replacement for reviewing internal cases, logs, or support tickets.
- Not evidence from sources beyond CFPB complaints.

## Methodology

Signal filtered CFPB complaints for the target company and support pattern, assigned complaint narratives into curated evidence buckets, synthesized PM-facing signals from populated buckets, classified each signal after evidence assembly, and scored severity with deterministic heuristics. Root causes are preserved as hypotheses, and confidence remains directional because Phase 1 uses one public source.