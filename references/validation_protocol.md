# Validation Protocol

Detailed operating procedure for validation in the research pipeline — Phases C
(5-phase validation), D (gap filling), and F (report review). The orchestrating
agent reads this file when Phase C begins. A delegated fresh session receives this
file's path in its dispatch brief and works only from the files the brief names.

## 1. Role Context

You may be running in one of two modes (chosen at intake, Question 10):

- **In-session role pass** — you are the same agent that performed the research,
  now acting as the Validator. Role isolation is mandatory (below).
- **Delegated fresh session** — you were dispatched via the user's delegate-skills
  adapter. You have no access to the research session; work only from the files
  named in your brief, which include absolute paths.

**Role isolation (mandatory in both modes):**

- Read ONLY `scratch/raw_findings.md` and the source URLs it cites. Do NOT read
  search notes, plans, or reasoning produced during the research phase (for
  example, `scratch/search_plan.md`).
- Judge every claim solely against what the cited sources actually say — never
  against your own recollection of the research or your beliefs about the topic.
- Write your outputs to `scratch/validation_log.md` and `scratch/gap_report.md`
  using the formats in Section 4.

## 2. Inputs

`scratch/raw_findings.md` contains the findings with their source URLs — findings
and URLs only, no search narrative or justifications. If a finding lacks a source
URL, that is itself a gap (record it in Phase 4).

## 3. The Five Validation Phases

Work through the phases strictly in order. After each phase, offer the human a
review point according to the review granularity chosen at intake (Question 6):
after every phase (default), at major checkpoints only, or before the final report
only. State which phase you completed and what you found before offering the review.

### Phase 1 — Link Accessibility

- Verify every cited URL resolves successfully (Hypertext Transfer Protocol (HTTP)
  status 200).
- A 403/429 response usually indicates bot protection, not a dead link. Try
  fetching the page content directly (reader/fetch capability). If the content
  still cannot be retrieved, record the link as "could not verify automatically" —
  do not classify it as broken.
- With 30+ links, process in batches of 5 to prevent overload. If a batch fails
  mid-way, save progress, report what was validated, and continue from where it
  stopped.
- Record broken links for the Gap-Filler.

### Phase 2 — Content Accuracy

- For each finding, open the cited source and verify the claimed information
  actually appears in the source content. This is NOT link checking — read the
  source and confirm the claim matches what the source says, including numbers,
  plan names, and quoted capabilities.
- Process in batches (as in Phase 1). Prioritize high-stakes claims first: pricing
  figures, adoption counts, and standards classifications.
- Record mismatches — what the finding claims vs. what the source actually says —
  for correction.

### Phase 3 — Recency

- Check each source against the user's time scope from intake (Question 5).
- Recency applies to **volatile facts**: pricing, market data, release notes,
  funding, adoption figures. Stable evergreen references (e.g., official product
  documentation describing how a feature works) are exempt unless the user's
  scope says otherwise.
- Record outdated sources for replacement.

### Phase 4 — Cross-Reference & Completeness

- Check that every factual claim has at least one supporting source.
- Where feasible, verify claims against 2+ independent sources.
- Identify coverage gaps, for example: an entity mentioned but not fully analyzed;
  a feature classified as a standard but observed in few entities; missing pricing
  for an entity; a sub-topic from the user's specific questions (Question 8) with
  no findings.

### Phase 5 — Source Quality

- Prioritize primary sources (official vendor sites, documentation, filings) over
  secondary reporting (blogs, news articles, forums).
- Flag findings that rely solely on blogs or forums without primary backing.
- For company/competitor information, verify against official sources where
  possible.

## 4. Output Formats

### `scratch/validation_log.md`

```markdown
# Validation Log — [research title]

## Phase 1 — Link Accessibility
| # | URL | Status | Notes |
|---|-----|--------|-------|
| 1 | https://... | OK / BOT-BLOCK (could not verify automatically) / BROKEN | |

## Phase 2 — Content Accuracy
| # | Claim (short) | Source | Verdict | Notes |
|---|---------------|--------|---------|-------|
| 1 | ... | URL | CONFIRMED / MISMATCH / PARTIAL | |

## Phase 3 — Recency
| # | Source | Scope fit | Notes |
|---|--------|-----------|-------|
| 1 | URL | WITHIN / OUTSIDE / EVERGREEN | |

## Phase 4 — Cross-Reference & Completeness
- Claims lacking any source: [list]
- Claims verified by 2+ independent sources: X/Y
- Coverage gaps: [list]

## Phase 5 — Source Quality
- Findings relying on secondary-only sources: [list]

## Verdict
APPROVED — or — GAPS FOUND (N gaps, see gap_report.md)
```

### `scratch/gap_report.md`

```markdown
# Gap Report

| ID | Phase | Severity | Description | Suggested action |
|----|-------|----------|-------------|------------------|
| G1 | 2 | HIGH | Pricing claim for entity X does not appear in cited source | Re-verify against the official pricing page or replace the source |
```

Severity guide: **HIGH** = wrong or unsupported factual claim; **MEDIUM** = claim
backed by a single low-quality source, or outdated volatile fact; **LOW** =
coverage or completeness improvement.

## 5. Gap-Filling Loop (Phase D)

1. The Validator finalizes `gap_report.md` (Section 4).
2. Switch to the **Gap-Filler** role: read ONLY `gap_report.md`, address each gap
   (find replacement sources, correct claims, fill missing data), and write
   `scratch/gap_fills.md` in the same findings format as `raw_findings.md`.
3. Switch back to the **Validator** role: re-validate the additions with the same
   5-phase procedure, focused on the new content.
4. **Maximum 3 iterations.** If gaps remain after 3 iterations, stop and escalate
   to the human with the list of unresolved gaps instead of looping indefinitely.
5. **Human checkpoint**: present the complete, validated findings for review.

## 6. Report Review (Phase F)

After the report is compiled (Phase E), run a validation pass over the compiled
report itself:

- **Structural completeness** — every section of the chosen template is present,
  including any adaptations documented in the Methodology section.
- **Consistency** — no contradictions between sections; adoption counts in the
  text match the Entity Coverage Matrix; pricing matches the pricing table.
- **Neutral language** — no marketing or vendor copy (spot-check against Content
  Rule 1).
- **Proper citations** — every claim is traceable to a reference; every
  abbreviation is expanded on first use (Content Rule 6).

Then the **human checkpoint**: the user reviews and approves the final report.

## 7. When to Escalate

Stop and involve the human when:

- Gaps remain after the 3 gap-fill iterations.
- Sources contradict each other and the evidence does not resolve the conflict.
- Validation cannot proceed (e.g., no fetch capability is available and every link
  is unverifiable).
- Batching fails repeatedly despite saving progress.
