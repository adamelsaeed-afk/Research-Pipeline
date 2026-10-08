# Codex A live research-pipeline test

**Local test artifacts:** Test-run folders referenced here but excluded from the repository, including `scratch/`, `scratch z/`, and `test_reports/`, were local test folders. Their paths are plain-text evidence references, not repository downloads. Statements about retained files describe the recorded run date. Published project files keep their normal links.

**Test period:** 1–2 October 2026 (Africa/Cairo)\
**Skill under test:** project copy at `D:\Research skill`\
**Mode:** full research workflow with fresh Docker-hosted OpenCode processes\
**Research as-of date:** 1 October 2026\
**Final report:** AI features in legal management systems (local test artifact: `test_reports/legal_ai_management_2026.md`)

This record covers the second live legal-AI research test of the revised project skill. The earlier independent run is retained in [LIVE_TEST_REPORT Z.md](LIVE_TEST_REPORT%20Z.md). The separately installed skill at `D:\AI-agents\skills` and Antigravity's permission settings were not changed. Nothing was pushed to main.

## Outcome

The branching interview, exact-brief confirmation, deterministic intake gate, separate search-plan approval, originating-agent research, findings checkpoint, gap filling, final report, and report review all occurred. The user approved the final Markdown report. External validation of the corrected findings **did not reach a valid approved verdict**. The user reviewed that failure at the validation checkpoint and explicitly chose to proceed with a report grounded in the corrected sources and visible evidence limits. The report does not claim external validation.

The [live run failure record](live_test_run_codex/validation_failures.md) preserves each activation's time and the observed or suspected reason for failure. Source and dispatch artifacts remain under `../scratch/`; the prior run's `../scratch z/` artifacts and its report copy remain preserved.

## Interview and phase-gate assessment

The user chose the topic, “AI features in legal management systems,” and the full research workflow. The branching interview resolved the report question, in-house matter/litigation/contract/legal-operations categories, GCC and global sample, named bank and enterprise legal-department evidence, 12-system target and shortfall rule, model-driven AI definition, Yes/No/Unknown standard, feature denominator and bands, 2024–2026 evidence period, non-AI treatment, report depth and path, review checkpoints, and both external roles. The user selected Docker-hosted OpenCode for both roles and later explicitly switched the model to `opencode/mimo-v2.6-flash-free`; it was not silently reused from another test.

The complete brief was shown and explicitly confirmed. `scripts/check_intake.py` passed before the search plan was drafted. The user approved the search plan (local test artifact: `scratch/search_plan.md`) separately before research. No research began while a recorded interview branch remained pending. The user approved the sourced findings (local test artifact: `scratch/raw_findings.md`) at the findings checkpoint.

**Interview defect found during validation:** “documented deployment by a named bank” did not establish whether a public participant testimonial that Leah had been “brought into” Mashreq Group Legal met the threshold. The first findings treated it as testimonial-grade qualifying evidence before that interpretive threshold had been expressly settled. The user later chose to include Leah with a visible testimonial-grade label. The affected decision was added to the intake record (local test artifact: `scratch/intake.json`), the entire amended brief (local test artifact: `scratch/research_brief.md`) was displayed and explicitly reconfirmed, and the checker passed again. The project [intake guide](../references/intake.md) and [SKILL.md](../SKILL.md) now direct future interviews to settle testimonial evidence thresholds before screening named deployments. Thus the recorded gate worked, but semantic completeness of the original interview was imperfect.

The confirmed final scope targeted twelve systems, roughly eight GCC-linked and four global, with at least four named-bank and four named non-bank enterprise legal deployments. The sourced sample has eight products, four GCC-linked and four global. The four-bank count depends on the user-accepted Mashreq testimonial. All four primary product categories occur. The report states the sample shortfall and testimonial limitation.

## External delegation and timings

The originating agent searched, screened candidates, and wrote claim-level findings. External processes were fresh Docker-hosted OpenCode CLI runs. Harmless role probes established a working Mimo route before live delegation. DeepSeek was not silently replaced: its earlier headless probe timed out, and the user explicitly confirmed the switch to Mimo in a revised brief. Antigravity's source read remained blocked by its existing permission policy and was not used or reconfigured.

The validator was activated **four times for the real research**. There were also **three validator probes** before research delegation (one DeepSeek timeout and two successful Mimo probes). The gap filler had one successful real run and one successful Mimo probe. Times below are local Africa/Cairo; earlier dispatch durations are reconstructed from staged-input and dispatch-file timestamps to about a second. The final run's stop time is bounded because it was manually interrupted.

| Purpose | Run ID | Start | End or cutoff | Duration | Result |
| --- | --- | --- | --- | --- | --- |
| DeepSeek validator probe | `fc4c1573b769400caa0c43e295ffb097` | 1 Oct 23:21:57 | 23:24:57 | 3 min 00 sec | Failed: 180-second timeout. |
| Mimo validator probe | `5db864ae75ae4fa4bb600a8762ef6581` | 1 Oct 23:32:36 | 23:33:08 | 32 sec | Completed. |
| Mimo gap-filler probe | `0f64e40903bf47dc8909abbf7e849d20` | 1 Oct 23:33:20 | 23:33:55 | 35 sec | Completed. |
| Mimo fresh-validator probe | `f7fac53d0be84c419f49b6d7342329e9` | 1 Oct 23:34:24 | 23:35:08 | 44 sec | Completed. |
| Real full validation, activation 1 | `a9c985587bb448b1808da5d9ddffde82` | 1 Oct 23:54:12 | 2 Oct 00:06:20 | 12 min 08 sec | **Dispatcher failed**; complete validator JSON was separately recovered with `gaps_found` and ten issues. |
| Real gap filling | `784a4dee32a64f58a50705a661ae857c` | 2 Oct 00:09:02 | 00:14:28 | 5 min 26 sec | Completed: ten corrections, zero unresolved items. |
| Real full revalidation, activation 2 | `89c528a9f9d84025a54b0478b05dad06` | 2 Oct 00:18:08 | 00:33:08 | 15 min 00 sec at dispatcher | Failed: 900-second timeout, no verdict. Its container child continued running until manually stopped about 00:57. |
| Real focused revalidation, activation 3 | `b34c613a659847eb9876903dce351bdf` | 2 Oct 00:35:04 | 00:40:56 | 5 min 52 sec | Failed schema validation: `approved_with_limits` combined with open issues. |
| Real focused revalidation with complete source URLs, activation 4 | `260fa1480232449dacd6f2f00f48c7b0` | 2 Oct 00:45:45 | User cutoff 00:54:56; confirmed stopped by about 00:57:09 | 9 min 11 sec to cutoff; about 11 min 24 sec to confirmed stop | Failed: no verdict by the user's additional two-minute limit; exact container process stopped. |

### Failure causes and observed limits

**Activation 1: dispatcher crash.** Windows Python decoded Docker/OpenCode's UTF-8 stderr with its default `cp1252` codec. The stream reader raised `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 6076`. A later `TypeError: data must be str, not NoneType` followed because stderr text was unavailable. `dispatch.json` remained at `started`. A complete stdout validator object was retained and recovered as diagnostic evidence; the dispatch itself remains recorded as failed. The project dispatcher now selects UTF-8 with replacement for undecodable bytes and records exceptions.

**Activation 2: timeout and orphan.** The Docker/OpenCode CLI exceeded 900 seconds without a result. Killing the host `docker exec` client left the OpenCode child alive in the container. The child was identified by the unique dispatch working directory and terminated later. This is a dispatcher cleanup defect, in addition to the unknown cause of the slow validator. The project dispatcher now sends `TERM`, then `KILL` if necessary, only to processes whose container working directory is that dispatch stage. This fix has a unit test but no subsequent live timeout test.

**Activation 3: invalid result and false date.** The CLI returned `verdict: approved_with_limits` while listing open issues. The schema correctly rejected it with `approved_with_limits cannot contain open issues`. Its stdout also contained competing JSON output and claimed source checks on 1 October, although the run occurred on 2 October. That date claim is false. The prompt now states the host validation date, distinguishes it from the research cutoff, and instructs the model to return one schema-consistent object. Those prompt changes were not proven by another successful external result.

**Activation 4: user-set cutoff.** No result was returned by the two-minute extension the user granted after asking for a stop. The dispatcher session was interrupted and the exact Docker child was terminated. No stdout, stderr, or result JSON was produced. The automatically written `dispatch.json` retains `started`; a separate manual stop record (local test artifact: `scratch/delegate_runs/focused_revalidation_2/dispatch/260fa1480232449dacd6f2f00f48c7b0/manual_stop.json`) records the failure. The available artifacts do not identify whether model-provider latency, source fetching, or analysis caused the delay. The concurrently running orphan from activation 2 is a plausible contributor, not a demonstrated cause.

The first recovered validator found ten issues in the initial findings. The fresh gap filler returned source-backed corrections; the originating agent checked consequential source passages and updated the matrix to Yes/No/Unknown counts of 3/0/5, 3/0/5, 6/0/2, 5/0/3, 5/0/3, 4/0/4, 1/0/7, and 1/0/7. Every row retains Unknown, so no frequency band applies. The later invalid validator output contained useful source observations but no valid approved verdict; it was not treated as approval.

## Project changes and checks

- The dispatcher now accepts one complete role JSON object surrounded by CLI narration while rejecting partial or duplicate objects. The prior run's saved narrated output parses under this fix; its original failure remains recorded.
- `approved_with_limits` now has an explicit claim-level limitation contract and rejects mismatches or open issues. The invalid focused run was correctly rejected.
- UTF-8 decoding and exception recording fix the Windows crash observed in activation 1.
- Timeout cleanup targets the unique Docker dispatch stage and preserves any stdout/stderr returned at timeout. Dispatch records now include start time, finish time, and elapsed seconds for future runs. Older timing data remains reconstructed from file timestamps.
- The validator prompt now distinguishes source-check date from research as-of date and asks for one schema-consistent result.
- The intake guide now explicitly branches on testimonial-grade named-deployment evidence.

The project workflow suite passed **13/13 tests** after these changes. The intake checker passed on the final, reconfirmed brief. The timeout cleanup fix and revised prompt have not been proven by another live validator run, because the user ended validation after activation 4.

## Report and voice review

The approved Markdown report (local test artifact: `test_reports/legal_ai_management_2026.md`) contains an executive summary, named deployments, detailed AI feature findings, an eight-product matrix, counts and evidence limits, a separate non-model-driven section, and dated or labeled-undated sources. The matrix was mechanically recounted and all eight rows matched their Yes/No/Unknown totals. A voice scan and editorial review found no Methodology section, recommendations, opportunities, suggested actions, internal agent or skill process notes, or validation claims. The report distinguishes vendor-published product capabilities from customer use and labels the Mashreq entry testimonial-grade. The user approved it at the final-report checkpoint. Word export was outside this confirmed deliverable and was not run.

The prior report at the same requested path was preserved as legal_ai_management_2026_prior_z.md (local test artifact: `test_reports/legal_ai_management_2026_prior_z.md`) before this run's report was written. Scratch evidence, source captures, dispatch metadata, stdout/stderr where available, gap-fill output, and the prior `scratch z` run remain intact.

## Remaining limits

This is one live interview and one real research question. The original interview missed a material sub-branch about testimonial deployment strength; it was corrected only after validation raised it. The final sourced report was user-approved despite the external validation failure, so this run does not establish that long-form real-research validation reliably completes through the chosen Docker/OpenCode model. The new Docker timeout cleanup and prompt wording are covered by tests and code review but lack a successful follow-up live run. Direct host OpenCode was not tested. Antigravity URL access remains denied under its unchanged policy. The project copy remains on main with uncommitted changes; no push or installed-skill sync occurred.
