---
name: research-pipeline
description: >-
  Structured multi-agent research skill supporting technical and market research.
  Use when the user asks to research a topic or technology, compare tools, vendors,
  or products, run a competitive analysis, gap analysis, or feature research, or
  estimate market size (TAM). Guides agents through intake, search planning,
  multi-phase validation, and report compilation with frequency-backed feature
  analysis. Exports to Word.
---

# Research Pipeline

A structured, multi-agent research pipeline that takes a request from intake through
validation to a publication-ready report. It supports two modes:

- **Technical research** — evaluating tools, frameworks, Application Programming
  Interfaces (APIs), architectures, and developer ecosystems.
- **Market research** — analyzing products, competitors, features, and positioning,
  in four sub-types: Gap Analysis, Competitive Analysis, Feature Research, and
  market sizing (Total Addressable Market, TAM).

Three agent roles cooperate through the pipeline:

- **Research Agent** (orchestrator) — searches, gathers, and cites findings.
- **Validator** — checks accuracy, recency, links, and source quality; flags gaps.
- **Gap-Filler** — resolves the gaps the Validator identifies.

Activation is driven by the YAML `description` above. The intended trigger phrases,
kept here as documentation, include: "Research X", "Do a competitive analysis of...",
"What features do competitors offer for...", "Analyze the market for...", "Compare
X vs Y vs Z", "Do a gap analysis for...", "Feature research for...".

These instructions are Command-Line Interface (CLI) agnostic: they use no
CLI-specific features, and delegation is described as a workflow pattern, not tied
to any implementation.

## Step 0 — Activation Confirmation

When a trigger phrase matches, ask the user FIRST:

> "This looks like a research task. Do you want me to run the structured research
> pipeline (intake, validation, formal report), or should I just answer directly?"

- **Decline** → answer normally, without this skill. No intake, no pipeline, no
  scratch files.
- **Accept** → begin the intake questions below.

The pipeline is all-or-nothing — there is no separate fast mode inside the skill.
Simple or casual questions are handled by declining at this gate.

## Intake (10 Questions)

Ask all questions BEFORE starting any research, one at a time or in small logical
groups. Save the answers to `scratch/intake.md`.

1. **Research Type**: "Is this technical research or market/business research?"
   - If market → ask question 2. If technical → skip to question 3.
2. **Market Sub-Type**: "What kind of market research is this?" — Gap Analysis,
   Competitive Analysis, Feature Research, or Market Sizing / TAM Estimation.
   Briefly explain what each sub-type encompasses.
3. **Targets**: "What specific companies, products, technologies, or topics should
   I research?" The user provides the list of entities to analyze.
4. **Geographic Scope**: "Should this research be global, or focused on specific
   regions/countries?"
5. **Time Scope**: "How recent should sources be? (e.g., last 6 months, 1 year,
   2 years)"
6. **Depth & Involvement**: "Do you want a surface-level overview or a deep dive?"
   Also confirm review granularity for validation checkpoints: (a) review after
   every validation phase (default), (b) review at major checkpoints only, or
   (c) review the final report only.
7. **Report Template**: "Which report structure do you prefer?" Show the full
   structure of each option when asking, not just the names:
   - **Comprehensive**: Executive Summary → Methodology → Market Standards (with
     frequency data) → Category-Specific Standards (optional) → Differentiating
     Features → Feature-by-Feature Deep Dive → Entity Coverage Matrix → Pricing
     Comparison → Gaps & Opportunities → References
   - **Simple**: Executive Summary → Findings → Conclusion → Sources
   - **Custom**: "Describe the structure you want"
8. **Specific Questions**: "Are there specific questions you want this research to
   answer?"
9. **Known Sources**: "Do you have any starting points — URLs, documents, or leads
   I should begin with?"
10. **Validation Mechanism**: "How should validation run?"
    - **In-session isolation** (default): you validate your own findings via strict
      role-isolated passes — reading ONLY the findings file and source URLs, none
      of your own search reasoning. No extra setup required.
    - **Delegate fresh-session**: validation runs in separate agent sessions via
      the user's installed delegate-skills adapters. Prerequisites: delegate-skills
      installed, a second agent CLI **with web access**, Node 18+, and git. Explain
      these prerequisites. If the user chooses this option but a prerequisite is
      missing, say exactly what is missing and offer in-session isolation instead.
      Never silently downgrade.

## Pipeline (Phases A–G)

| Phase | What happens | Human checkpoint |
|---|---|---|
| **A — Research Plan** | Build a search plan (keywords, sources, strategy) from the intake answers; write `scratch/search_plan.md` | User approves the plan before any searching begins |
| **B — Research Execution** | Execute the approved plan against priority sources for the mode; document every finding with its source Uniform Resource Locator (URL); write `scratch/raw_findings.md` (findings + URLs only — no search narrative or justifications) | — |
| **C — Validation** | Run the 5 validation phases (summary below) | Review points per intake granularity (Q6) |
| **D — Gap Filling** | Validator ⇄ Gap-Filler loop, capped at 3 iterations | User reviews the complete, validated findings |
| **E — Report Compilation** | Compile findings into the chosen template, applying all Content Rules; write `scratch/draft_report.md` | — |
| **F — Report Review** | Validator reviews the compiled report | User reviews and approves the final report |
| **G — Export** | Word export, only after explicit approval | User explicitly approves the export |

### Validation Isolation (chosen at intake, Q10)

- **In-session isolation**: switch roles strictly. As the Validator, read ONLY
  `scratch/raw_findings.md` and the source URLs it cites — never your own search
  notes or reasoning from earlier in the session. Write `scratch/validation_log.md`
  and `scratch/gap_report.md`. As the Gap-Filler, read ONLY the gap report.
- **Delegate fresh-session**: dispatch validation to a fresh session via the user's
  delegate-skills adapter. Briefs must be self-contained with absolute file paths:
  what to validate, the absolute path to `raw_findings.md`, and the absolute paths
  where `validation_log.md` and `gap_report.md` must be written. The fresh session
  receives only the findings file plus source URLs — no search history, no
  reasoning traces, no prior context.

### Phase C — The 5 Validation Phases (summary)

1. **Link Accessibility** — every cited URL must resolve. A 403/429 response is
   usually bot protection, not a dead link: try fetching the content directly; if
   it still cannot be verified, flag it as "could not verify automatically". With
   30+ links, process in batches of 5.
2. **Content Accuracy** — visit each cited source and confirm the claim actually
   appears there. Process in batches and verify high-stakes claims first: pricing
   figures, adoption counts, standards classifications.
3. **Recency** — check sources against the user's time scope. Recency applies to
   volatile facts (pricing, market data, releases); stable evergreen references
   are exempt unless the user's scope says otherwise.
4. **Cross-Reference & Completeness** — every factual claim needs at least one
   supporting source; verify against 2+ independent sources where possible;
   identify coverage gaps.
5. **Source Quality** — prefer primary sources (official sites, documentation)
   over secondary reporting; flag findings backed only by blogs or forums.

After each phase, offer a review point according to the intake granularity.
**Read `references/validation_protocol.md` when Phase C begins** — it contains the
full procedures, the validation log and gap report formats, and the report-review
checklist.

### Gap Filling (Phase D)

1. The Validator produces `scratch/gap_report.md` listing all issues found.
2. The Gap-Filler addresses each gap (replacement sources, corrections, missing
   data), reading ONLY the gap report, and writes `scratch/gap_fills.md`.
3. The Validator re-validates the additions.
4. Loop until the Validator approves all findings — **maximum 3 iterations**. If
   gaps remain after 3 iterations, stop and escalate to the user with the list of
   unresolved gaps instead of looping indefinitely.

## Report Content Rules

These rules apply to ALL output — the research report, any sample output, and the
README.

1. **No vendor/marketing language.** Never copy marketing copy from vendor
   websites; describe what each feature actually does, neutrally and in a
   standardized way.
   - Bad: "frontier-class legal AI models fine-tuned specifically for top-tier law firms"
   - Good: "Legal-domain fine-tuned language models for document analysis and drafting"
2. **Frequency-backed standards.** Every feature classified as a "standard" must
   include adoption frequency data across the analyzed entities:
   | Classification | Threshold |
   |---|---|
   | Universal Standard | 70%+ of analyzed entities |
   | Emerging Standard | 30–69% of analyzed entities |
   | Differentiator | <30% of analyzed entities |
   State counts explicitly, e.g. "Document RAG: 7/7 vendors (100%)". The user may
   override these thresholds at intake — if they do, use their values.
3. **Feature-first organization** (comprehensive template): organize the report
   around features, not vendors. Each feature section describes what the feature
   does (neutrally), then which entities offer it and how implementations vary.
   The Entity Coverage Matrix provides the at-a-glance vendor view.
4. **Structured pricing.** Present pricing in tables for side-by-side comparison,
   normalized to the same unit (e.g., per user/month), and note when pricing is a
   "custom/enterprise quote" vs. publicly listed.
5. **Category-specific standards (optional).** If the research spans multiple
   product categories, ask at intake whether a category breakdown is needed.
6. **Abbreviations.** Expand every abbreviation on first use as
   `Full Name (ABBREVIATION)`, then the abbreviation alone may be used — e.g.,
   "Natural Language Processing (NLP)".

## Report Templates

- `templates/comprehensive.md` — the full feature-analysis structure. Follow the
  adaptation guidance at the top of that file for the selected mode/sub-type
  (e.g., TAM estimations skip the vendor matrix and add sizing/segmentation
  sections; technical deep-dives skip vendor-dimension sections).
- `templates/simple.md` — Executive Summary, Findings, Conclusion, Sources.
- **Custom** — build to the user's described structure while applying all Content
  Rules.

The Methodology section always states which template adaptations were applied and
why.

## Word Export

Only after the user explicitly approves the final report (Phase G), and after the
user selects a Word template:

```bash
uv run scripts/export_to_word.py --input report.md --output report.docx --template corporate
```

- Word templates: `corporate`, `academic`, `minimal`.
- The first run may pause briefly while `uv` installs the script's dependencies
  automatically.
- After export, clean up the scratch directory (see File Management).

## Error Handling

**Search errors** — if a search returns no relevant results, try alternative
keywords (rephrase, broaden, synonyms). After 3 failed attempts, escalate to the
user with what was tried.

**Source errors** — paywalled source → note it as "[Paywalled source]" and move
on; a source returns 404/error → flag it for the Gap-Filler to find an
alternative; sources contradict each other → flag the contradiction for human
review.

**Agent errors** — stuck or looping → escalate to the user with context of what
went wrong; validation batching fails mid-batch → save progress, report what was
validated, continue from where it stopped.

## Research Continuation Mode

After the report is approved and exported, the user may request refinements.
Re-run only the relevant pipeline phases, not the full pipeline:

- "Dig deeper into section X" → re-run the pipeline for just that section
- "Add more competitors/entities" → research and validate the new entities, update
  the report
- "Expand the pricing analysis" → focused research on pricing only
- "Update with newer data" → re-validate recency, search for more recent sources

Load the existing approved report, identify which sections need updating, run only
the relevant phases, validate only the new or changed content, present the updated
report for approval, and re-export to Word if approved.

## File Management

All intermediate work products go to a **scratch directory**, created fresh at the
start of each research run. Default location: `./scratch/` under the current
working directory, unless the user specifies another location.

```
./scratch/
├── intake.md          # User's intake responses
├── search_plan.md     # Approved search plan
├── raw_findings.md    # Raw research findings
├── validation_log.md  # Validator's phase-by-phase report
├── gap_report.md      # Gaps identified by Validator
├── gap_fills.md       # Gap-Filler's additions
└── draft_report.md    # Pre-approval draft
```

After final approval and export, the scratch directory is **deleted**. Only the
final Markdown (`.md`) report and Word (`.docx`) document remain, written to the
working directory or a user-specified location.
