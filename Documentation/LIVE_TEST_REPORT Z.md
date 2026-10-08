# Research skill live end-to-end test report

**Local test artifacts:** Test-run folders referenced here but excluded from the repository, including `scratch/`, `scratch z/`, and `test_reports/`, were local test folders. Their paths are plain-text evidence references, not repository downloads. Statements about retained files describe the recorded run date. Published project files keep their normal links.

**Test dates:** 30 September – 1 October 2026
**Skill under test:** project copy at `D:\Research skill` (revision compared with `ecc1b24`, uncommitted)
**Mode:** live interview, confirmed brief, full research workflow, external CLI validation, report

This report records the first live run of the revised skill. The earlier testing in [FINAL_TEST_REPORT.md](FINAL_TEST_REPORT.md) covered probes, dispatch mechanics, and fixture exports; this run exercised the branching interview with the user, the deterministic gate, real research, external validation with gap filling, and a real report.

## Setup

- The user directed that all working files live in a new untracked directory `scratch z/` (the shipped `scratch/` directory stayed untouched). The user stated `scratch z/` will be removed after the test on their instruction.
- Topic: rerun of the leftover legal-AI feature-research topic from the same day's earlier session. Scope: full workflow.
- Delegation was selected fresh by the user, not reused from the earlier run: validator = OpenCode in Docker, model `deepseek/deepseek-flash` (no prior live probe); gap filler = OpenCode in Docker, model `opencode/mimo-v2.6-flash-free` (source access verified 30 September). Both roles in the running `opencode` container (OpenCode 1.18.33).
- Dispatcher configuration lived at `scratch z/local_dispatch_config.json` (untracked), with run directories under `scratch z/runs/`.

## Interview behavior assessment

The interview ran in five grilling-style rounds over the decision map, with the prior run's recorded answers offered only as recommendations under each question.

| Round | Coverage |
|---|---|
| 1 | Topic and research type; the three research questions; population, cohorts, and selection rules; geography — where the interview pinned down that "GCC" meant the six member states, which the prior record had left vague; evidence period |
| 2 | AI definition; non-AI treatment; feature taxonomy; cell evidence standard; comparison dimensions; frequency bands and fallback |
| 3 | Depth; report format, exclusions, and save path; source leads (explicit "none"); review checkpoints |
| 4 | Validation mode (single-question round: target questions deferred until the mode was settled) |
| 5 | Validator and gap-filler targets, transports, and models, presented with tested/untested status per route |

Assessment against the intended behavior:

- No relevant branch was silently assumed. Every base decision and branch question was put to the user, and "all as recommended" / "keep" were treated as explicit confirmations, never as defaults accepted from silence.
- Corrections reopened branches. The user's fresh choices differed from the prior run's record where it mattered (validator model), and the newly asked GCC definition changed the record.
- No research began while a question was open. The interview, brief display, and confirmation preceded the intake gate; the gate preceded the search plan; the search plan was approved separately before any searching; the findings, validation, and report checkpoints were each honored.
- The brief was shown in full twice (once written, once in chat), confirmed explicitly, and the SHA-256 of the exact bytes was recorded; `check_intake.py` passed before the search plan was drafted.

## Research execution

Discovery, eligibility screening, and per-product harvest produced a verified sample of 7 systems across 9 documented deployments (4 bank-cohort systems, 4 enterprise-legal-department systems, Icertis in both cohorts; GCC portion 2 systems / 3 deployments, shortfall stated). Screening rejected anonymized deployers, out-of-window sources, law firms, government entities, and category mismatches. Findings were recorded claim-by-claim (`D-`/`F-`/`N-` IDs, URLs, dates, retrieval dates) in `scratch z/raw_findings.md` and approved by the user at the findings checkpoint.

## Delegation and validation record

1. Preflight passed for both targets (container running, `opencode --version` = 1.18.33).
2. Harmless source-reading probes passed for both targets: the validator probe (deepseek) returned an approved structured result citing the live Python documentation; the gap-filler probe (mimo) returned a completed structured result.
3. **Original dispatcher parser: FAIL.** Two validation dispatches through `scripts/research_dispatch.py` failed with "external CLI did not return one JSON object". The validator model emitted two lines of narration before its JSON; the parser requires stdout to be exactly one JSON object. Both runs (run IDs `323b154f…`, `bed93981…`) are preserved under `scratch z/runs/validation/dispatch/`. Per the user's instruction, this is counted as a **fail** for the original parser in this test record.
4. **Fix (user-directed):** a patched copy was created at `scratch z/fixes/research_dispatch.py`. It tries the original strict parse first, then extracts the last complete JSON object from surrounding narration; full role-schema validation is unchanged, so malformed or truncated output still fails. The project `scripts/` file was not modified.
5. Validation (fixed parser) returned `gaps_found` after 33 claim checks (25 confirmed, 1 partial, and the sample-construction claims): four real defects in the findings — a deployment miscount (8 stated, 9 logged), a systems-vs-deployments conflation in the vendor-concentration limit, unsupported Sirion figures that had been taken from a search snippet rather than the case study, and a missing explicit rules/OCR treatment.
6. Gap filling (mimo, fresh process) returned evidence-backed corrections for all four gaps, including zero-hit searches for OCR across every fetched source and the archive URL for the Sirion case study; one item was returned unresolved (the live Sirion page returns HTTP 403).
7. Corrections were incorporated into `raw_findings.md` and a fresh validator pass re-checked them. Two revalidation runs were rejected at the verdict gate: `approved` combined with one `unverifiable` check, then `approved` combined with open issues. The verdict schema admits no "approved with labeled residual uncertainties" state, and this model reliably produces that judgment. **Design limit, left unpatched by user decision:** the loop stalled, and the user chose to reconcile — the two preserved runs substantively support every claim, and the two residual uncertainties (archive-derived Sirion figures; the interpretive mapping behind Contra's review/risk matrix cell) were carried into the report as stated limits.

## Report

The report was written to `test_reports/legal_ai_management_2026.md` (the path confirmed in the brief) and preserved after the later Codex A test as `legal_ai_management_2026_prior_z.md` (local test artifact: `test_reports/legal_ai_management_2026_prior_z.md`): executive summary with scope line, sample and deployments, ten feature-by-feature findings, feature coverage matrix, documented coverage counts with no band applied anywhere (every denominator contains Unknown, per the confirmed fallback rule), the separate non-AI section including the explicit OCR absence-of-documentation statement, observed gaps, material evidence limits, and thirteen dated references.

Voice conformance: an automated scan found no recommendations, opportunities, suggested actions, methodology section, agent or skill process terms, claim IDs, scratch paths, or placeholders. Every matrix row matches its stated count, and every material statement traces to a numbered reference. Word export was not part of the confirmed deliverable; after the user requested it post-review, the report was exported in all three styles (`corporate`, `academic`, `minimal`) to `test_reports/` and inspected programmatically: no placeholders, comments, or broken tables, with all three tables at the correct dimensions. User visual verification (1 October 2026): the **corporate** export passed, with layout and styling noted as possible improvements; the **academic** and **minimal** exports render almost identically and are flagged as candidates for merging into a single style. The exporter ran with system Python plus python-docx 1.2.0 because `uv` is not installed on this machine (the README's `uv run` instruction also works when python-docx is present).

## Defects and design findings

| # | Finding | Status |
|---|---|---|
| 1 | The intake guide does not state that `validator_model`/`gap_filler_model` answers must exactly equal the configured model IDs; the dispatcher enforces exact equality, and annotated answers (including the prior run's own record) fail dispatch. | Documented; worked around by normalizing the test record's answers. Project files unchanged. |
| 2 | Original dispatcher parser rejected valid-but-narrated validator output twice; strict single-JSON-object contract is too brittle for chatty models on long tasks. | **FAIL recorded for the original parser** per user instruction. Patched copy at `scratch z/fixes/research_dispatch.py`; project file untouched. |
| 3 | The verdict schema has no state for "approved with labeled residual uncertainties"; honest validator output is structurally rejected, stalling the loop when no new evidence is available. | Documented as an open design limit; user chose reconciliation over patching. |
| 4 | The brief does not define deployments-versus-systems counting for multi-deployment vendors; the interview's cohort rules resolved it in practice (count each system once; cohort tallies follow documented deployments). | Observation for a future revision. |
| 5 | `scratch z/` is not gitignored, so test evidence shows as untracked in git. | User chose to retain the directory and remove it after the test. |
| 6 | Word styles: academic and minimal render almost identically in user visual verification; corporate passed with layout and styling improvement notes. | User visual verification, 1 October 2026. Merging academic and minimal into one style is a candidate change for a future revision. |
| 7 | `dispatch.json` records the command, PID, exit code, and error but no start or end times; per-session durations are only reconstructable from staged-file timestamps. | Observation for a future revision: record `started_at`/`finished_at` in the dispatch record. |

## External session timings

Wall-clock duration of each fresh external CLI session on 1 October 2026 (local time), reconstructed from the staged-file timestamps in each run directory — start is the staged-input write, end is the final dispatch record write, accurate to about a second:

| Start | Session | Outcome | Duration |
|---|---|---|---|
| 00:38:09 | Validator probe (deepseek) | Approved | 10 s |
| 00:38:57 | Gap-filler probe (mimo) | Completed | 24 s |
| 00:39:53 | Validation run 1 (deepseek) | Failed — parser | 1 m 48 s |
| 00:43:07 | Validation run 2 (deepseek) | Failed — parser | 1 m 33 s |
| 00:59:29 | Validation run 3 (deepseek) | Completed — gaps_found | 1 m 31 s |
| 01:02:30 | Gap fill (mimo) | Completed — all 4 gaps | 4 m 38 s |
| 01:10:46 | Revalidation 1 (deepseek) | Failed — verdict gate | 2 m 40 s |
| 01:15:58 | Revalidation 2 (deepseek) | Failed — verdict gate | 1 m 30 s |

The two parser-failed runs performed essentially the same source-checking work as the successful validation run; only their output form was rejected. The gap fill was the longest session, consistent with its re-fetching of all sources plus the explicit OCR searches.

## Automated tests

The ten workflow tests (`tests/test_workflow.py`) were rerun on 1 October 2026 with the `unittest` runner: **10/10 passed**. This closes the earlier gap where the suite had not been rerun after the final documentation and shell-client edits.

## Artifacts retained

- `scratch z/`: `intake.json`, `research_brief.md`, `search_plan.md`, `raw_findings.md`, `gap_report.md`, `local_dispatch_config.json`, `fixes/research_dispatch.py`, and `runs/` with all probe, validation, gap-fill, and revalidation artifacts (including the two rejected original-parser runs and the two rejected revalidation runs).
- `test_reports/legal_ai_management_2026_prior_z.md`: preserved copy of the delivered report at its original user-chosen path, which the later Codex A test reused.
- The pre-existing `scratch/` directory from the earlier session was not modified.

The project copy remains uncommitted and unpushed, and the separately installed skill under `D:\AI-agents\skills` remains untouched. `scratch z/` is retained as the evidence trail until the user removes it.

## What this test establishes, and its limits

The branching interview held up against a live user: branches were asked, not assumed; silence and defaults were never treated as answers; corrections reopened branches; and both hard gates (intake checker, separate search-plan approval) held before any research. External CLI validation and gap filling ran end-to-end on real research through fresh container processes, and the delivered report passed the voice-guide review. The limits are equally concrete: one machine, one interview, one research run; the deepseek verdict-wording behavior is observed on one model; Arabic-language coverage was limited by the US-locale search; the verdict-schema mismatch is documented but unresolved; and the Word exports carry the user's visual verdict — corporate passed with layout and styling improvement notes, while academic and minimal render almost identically.
