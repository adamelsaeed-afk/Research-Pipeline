# Research Pipeline change report

**Local test artifacts:** Test-run folders referenced here but excluded from the repository, including `scratch/`, `scratch z/`, and `test_reports/`, were local test folders. Their paths are plain-text evidence references, not repository downloads. Statements about retained files describe the recorded run date. Published project files keep their normal links.

**Status:** Uncommitted project revision, compared with `ecc1b24` on `main`\
**Date:** 30 September 2026\
**Scope:** `D:\Research skill` project copy only

## Summary

The skill now defines a branching research interview, a recorded intake check,
research-only external CLI delegation, and a descriptive report format. The agent
that receives the skill conducts the research. If the user chooses external
validation, separate Antigravity (`agy`), OpenCode (`opencode`), or Codex (`codex`)
CLI processes check findings and fill identified gaps. Direct CLI execution is the
standard route; Docker is an optional transport configured for each installation.

The report instructions now produce formal, direct English for a management reader.
Delivered research reports contain findings, citations, and material evidence
limits. They do not contain a Methodology section, recommendations, opportunities,
next steps, agent roles, skill names, or validation logs.

## Behavior changes

| Area | Previous workflow | Current workflow |
|---|---|---|
| Research intake | A fixed ten-question list preceded research. | Questions form a branching interview. Existing user answers count; unclear or newly relevant decisions remain open until answered. The user confirms the complete brief. |
| Phase gate | Progress depended on following the written instructions. | `check_intake.py` rejects recorded pending or unclear decisions, open branches, an empty brief, and a confirmation hash that does not match the brief. The skill calls it before the search plan, browsing, or delegation. |
| Research plan | A plan approval checkpoint existed. | The plan remains a separate user approval after the confirmed brief. The originating agent performs the searches and keeps sourced claim IDs. |
| Delegation | A fresh-session pattern depended on separate coding delegate skills. | The project dispatches research validator and gap-filler roles directly to fresh `agy`, `opencode`, or `codex` CLI processes. A native subagent does not satisfy the selected external-CLI mode. |
| Delegation failure | The old workflow described prerequisites and fallback choices. | Preflight checks routing. Dispatch records the selected target, command, output, and error; empty, malformed, timed-out, or denied runs do not count as validation. Changing the selected route requires a new user choice. |
| Gap loop | The previous workflow capped gap filling at three passes. | The gap filler returns cited corrections; a new validator process checks material changes. The loop continues while evidence improves and records unresolved evidence when progress stops. |
| Delivered report | Templates included Methodology, opportunities, recommendations, and internal template notes. | Templates use descriptive findings, documented coverage, observed gaps, and factual summaries. Process instructions remain in the skill and references, outside the delivered report. |

## How the revised skill runs

1. The agent reads the request and asks unresolved research questions in rounds. It
   records base decisions and relevant branches in `scratch/intake.json`. An optional
   question still needs an explicit answer such as “none”; a branch marked
   `not_applicable` needs a reason. Silence and timeouts do not count as answers.
2. The agent shows `scratch/research_brief.md` to the user. Explicit confirmation is
   tied to the exact file bytes by a SHA-256 digest. A changed brief invalidates the
   confirmation. The intake checker must pass before a search plan or research work.
3. The user separately approves the search plan. The originating agent researches,
   writes claim-level findings with source locators and dates, and distinguishes
   documented capability coverage from market adoption.
4. The chosen validation mode runs. In `same_session`, the originating agent conducts
   a separate review pass. In `external_cli`, preflight checks the configured route
   and the dispatcher starts fresh CLI processes for validation and gap filling.
   Validation checks source access, accuracy, recency, completeness, and quality.
5. The agent incorporates only evidence-backed corrections, revalidates material
   changes, and writes the selected comprehensive, simple, or agreed custom report.
   An English editorial pass removes formulaic or promotional wording while keeping
   claims, citations, figures, and uncertainty intact. Word export remains optional
   and follows report approval.

The recorded intake check is a practical phase gate, not a universal runtime lock.
It cannot discover every unstated branch, judge semantic clarity, verify that a user
actually gave each recorded answer, or intercept every tool call in every agent host.
Those parts still depend on agent behavior and need a live research trial.

## Delegation and installation paths

`scripts/preflight_delegate.py` checks selected executables or running containers and
their version commands. It does not prove authentication or source access. A harmless
live source-reading run is required for each configured target. OpenCode requires an
explicit provider/model ID. `scripts/research_dispatch.py` accepts only the three
named CLI products and the `validate` and `gap_fill` roles. It stages the confirmed
brief and role input, launches with an argument array rather than shell evaluation,
requires a structured role result, and saves a dispatch record.

For a host agent targeting a container, Docker dispatch uses a configured container
name and a shared host/container path, then starts a fresh headless process with
`docker exec`. An interactive startup command such as `docker start -ai
<container-name>` only starts and attaches to the container; it is not the research
dispatch command. For an originating agent inside a Linux container,
`scripts/submit_research_job.sh` writes a fixed request to the shared folder without
requiring Python in that container. The host `research_mailbox.py` worker validates
the request and launches the configured target. The bridge does not pass arbitrary
shell commands or give the originating container Docker-socket access. Direct CLI
users need no Docker setup.

## Files changed or added

| Files | Role |
|---|---|
| `SKILL.md`, `README.md` | Main workflow and portable setup instructions. |
| `references/intake.md`, `scripts/check_intake.py` | Branching interview record and deterministic completeness/confirmation check. |
| `references/delegation.md`, `scripts/preflight_delegate.py`, `scripts/research_dispatch.py` | External role contract, route preflight, and fresh-process execution. |
| `scripts/research_mailbox.py`, `scripts/submit_research_job.sh` | Optional shared-folder route for container-originated jobs. |
| `references/validation_protocol.md` | Source checks, gap correction, revalidation, and final report review. |
| `references/report_voice.md` | Focused English editing principles adapted from `humanizer-zh`; the Chinese skill is not a runtime dependency. |
| `templates/comprehensive.md`, `templates/simple.md` | Descriptive report structures without Methodology or advice sections. |
| `examples/sample_research.md`, `examples/sample_research.docx` | Revised fictional example and Word export. The entities, prices, and `.example` URLs are placeholders. |
| `tests/test_workflow.py`, `tests/manual_live_dispatch.py` | Intake, dispatcher, and mailbox tests plus an optional live CLI probe. |
| `Documentation/REVISION_PLAN.md`, `Documentation/FINAL_TEST_REPORT.md` | Agreed plan and observed test record. |

## Verification and remaining limits

Ten workflow tests passed earlier in the revision, and the suite was rerun on 1 October 2026 after the final edits: all ten passed. A direct Codex validation probe
passed outside the sandbox. Docker-hosted OpenCode completed a validator run, a
gap-fill run, and a fresh revalidation using
`opencode/mimo-v2.6-flash-free`. A separate agent container submitted validation
and gap-fill jobs through the host bridge to OpenCode. These results apply to the
tested setup; OpenCode was not tested as a direct host installation. The initially
tried `opencode/ling-3.0-flash-fin-free` endpoint was unavailable.

Antigravity started headlessly in its container but denied the cited URL read under
its current permission policy. The user chose to leave that setting unchanged, so
Antigravity source validation and the reverse container route remain unverified.
The sample Word document was exported and its text and tables were checked; visual
rendering was unavailable. Full raw probe logs and the reconstructed JSON
copies were removed; [the final test report](FINAL_TEST_REPORT.md) retains the
observed outcomes and evidence limits.

A live end-to-end test on 30 September – 1 October 2026 then exercised the
branching interview with the user, the intake gate, the separate search-plan
approval, real research, external CLI validation with gap filling, and a real
report. It recorded a fail for the original dispatcher parser (superseded by a
patched copy in the test workspace) and an open verdict-schema design limit; the
outcomes are in [the earlier live test report](LIVE_TEST_REPORT%20Z.md). The separate
installed skill under `D:\AI-agents\skills` has not been updated, and this
project revision has not been committed or pushed.

## Codex A live-test changes, 2 October 2026

The next full research trial is recorded in [LIVE_TEST_REPORT_CODEX_A.md](LIVE_TEST_REPORT_CODEX_A.md). It found a missed interview sub-branch: a named bank deployment rule did not say whether a participant testimonial that a product was brought into a legal team qualified. The user explicitly accepted Leah/Mashreq at testimonial grade, reconfirmed the amended full brief, and the intake checker passed again. `SKILL.md` and `references/intake.md` now require that evidence threshold to be settled before named-deployment screening.

The real Docker/OpenCode validator was activated four times. The first emitted a `gaps_found` object but the Windows dispatcher crashed while decoding UTF-8 stderr as `cp1252`; the second timed out at 900 seconds and left an OpenCode child running in the container; the third returned a contradictory `approved_with_limits` result with open issues and a false check date; the fourth had no verdict by the user's cutoff and was stopped. One fresh gap-filler process completed ten corrections. The exact run IDs, durations, failure causes, and suspected contributors are in [validation_failures.md](live_test_run_codex/validation_failures.md). No real-research revalidation obtained a valid approved verdict.

The project dispatcher now accepts a single narrated role object, records errors under UTF-8 decoding, rejects contradictory approvals, terminates only the timed-out dispatch stage inside Docker, preserves timeout output, and writes start/finish/elapsed metadata for future runs. Its prompt separates validation date from research as-of date. `references/delegation.md` and `references/validation_protocol.md` describe the `approved_with_limits` contract. The final workflow suite passes 13 tests. The new Docker timeout cleanup and prompt changes have not been live-proven after the user ended validation.

The user approved the sourced eight-system Markdown report at legal_ai_management_2026.md (local test artifact: `test_reports/legal_ai_management_2026.md`) after choosing to proceed from the failed validation checkpoint with explicit evidence limits. The previous report at that path was preserved as legal_ai_management_2026_prior_z.md (local test artifact: `test_reports/legal_ai_management_2026_prior_z.md`). Research and dispatch evidence remain in `scratch/` and `scratch z/`. No Word export was requested for this run; the installed skill, Antigravity settings, and main remote remain untouched.
