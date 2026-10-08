# Research skill revision: final test report

**Local test artifacts:** Test-run folders referenced here but excluded from the repository, including `scratch/`, `scratch z/`, and `test_reports/`, were local test folders. Their paths are plain-text evidence references, not repository downloads. Statements about retained files describe the recorded run date. Published project files keep their normal links.

**Test date:** 30 September 2026\
**Project copy:** `D:\Research skill`\
**Scope:** Research intake, external CLI delegation, optional Docker routes, and report output.

## Retained artifacts

| Artifact | Purpose |
|---|---|
| [Management report Markdown](../examples/sample_research.md) | Fictional management-report example in Markdown. |
| [Management report Word](../examples/sample_research.docx) | Word export of the fictional management-report example. |

This test report retains the observed outcomes and limits. The five reconstructed JSON
result and receipt files were removed at the user's request after the report was
written. Original raw stdout, stderr, and dispatch metadata had already been removed
with the temporary probe directories. The two management-report examples above are
pre-existing project fixtures and were not part of that cleanup.

## Result summary

| Test | Result | Evidence and limit |
|---|---|---|
| Intake gate and dispatcher unit tests | Passed before the final documentation and shell-client edits | Ten tests passed in the earlier implementation run. They were not rerun after the final edits because a later command approval was declined. The Python-free shell client was exercised in the live container bridge test. |
| Direct Codex validation | Passed in an earlier implementation run | Fresh Codex CLI returned a structured result outside the sandbox. Its original probe output was not retained here. |
| Docker command and container inventory | Passed | Docker Desktop client and server responded from the Windows host. Both agent containers exposed their CLIs. Both were returned to their original stopped state after testing. |
| Host to OpenCode container: validation | Passed | A fresh OpenCode process returned `verdict: approved` for one claim about `json.dumps`, citing the official Python documentation URL. |
| Host to OpenCode container: gap filling | Passed | A separate process returned `verdict: completed` with a correction stating that `json.dumps` returns a string. |
| Host to OpenCode container: revalidation | Passed | Another fresh process returned `verdict: approved` for the same documentation claim. |
| Agent container to OpenCode container: validation | Passed | The originating container wrote a fixed job to the shared folder; the host worker launched OpenCode in the sibling container and returned an approved result. |
| Agent container to OpenCode container: gap filling | Passed at the worker/receipt level | The bridge returned `status: completed` and a result path. The full result content was not retained. |
| Antigravity container: source checking | Blocked by existing permissions | Headless Antigravity launched and accepted the inline research input but reported a denied `read_url` action when it tried to access the cited page. No permission settings were changed, as requested. |
| OpenCode container: first listed free model | Failed at provider endpoint | `opencode/ling-3.0-flash-fin-free` returned `Upstream request failed: Endpoint is unavailable.` The later runs used `opencode/mimo-v2.6-flash-free`. |
| Reverse container route into Antigravity | Unverified | No successful source-check result is available because Antigravity's URL read remained blocked. |
| Word report export | Passed in the earlier implementation run | The sample DOCX was generated and its text/tables were checked. Visual rendering was not available because LibreOffice was absent. |

The CLI result text observed during the tests stated that OpenCode fetched the official Python documentation. Its tool-event logs and result files are no longer retained, so this report records the returned source-check claims rather than independently proving every network request. The example management report uses fictional vendors; it is a format and language sample, not real market research.

## What the live Docker tests establish

Host-to-container delegation works for the tested OpenCode configuration. The shared-folder mailbox also carries a fixed validation or gap-fill request from one agent container to a host worker, which starts a fresh OpenCode process in a second container and returns a result path. The originating container did not need Python or Docker-socket access; it used `scripts/submit_research_job.sh` on the shared mount. The host worker used Docker access on the Windows host.

Antigravity can start as a headless CLI in its container, but its headless permission policy denied reading the cited URL. Its [headless documentation](https://antigravity.google/docs/cli/headless/) explains that actions requiring approval are soft-denied without an interactive prompt. That route cannot yet serve as an independently source-checking validator in this installation. The user's Antigravity settings remain unchanged. A different user's container still needs its own model, authentication, mount, permission, and live source-access checks.

## How to review or reproduce

1. Read the [management report example](../examples/sample_research.md) or open the [Word version](../examples/sample_research.docx). Check that it contains sourced descriptive findings and no recommendation or agent-process section.
2. Review the result summary above and its limits. The original result and receipt files are no longer retained.
3. Use the generic local-config examples in [README](../README.md). Start a user's own container with their startup command, then run `python tests/manual_live_dispatch.py --config <local-config.json> --target <target-name> --role validate` and repeat with `--role gap_fill`. These commands may consume provider usage.
4. For container-to-container testing, run the host `research_mailbox.py worker` and submit with `submit_research_job.sh` as shown in README. Check both the printed receipt and the result JSON before counting the run as successful.

The project copy has not been pushed or synced to the separate shared skill installation.

A live end-to-end test followed on 30 September – 1 October 2026: branching interview, intake gate, real research, external CLI validation with gap filling, and a delivered report. Its record, including a fail counted against the original dispatcher parser, is in [LIVE_TEST_REPORT Z.md](LIVE_TEST_REPORT%20Z.md).

## Subsequent live-test outcome, 1–2 October 2026

The [Codex A live test](LIVE_TEST_REPORT_CODEX_A.md) exercised a second full branching interview, exact brief confirmation, intake checker, separate search-plan approval, originating-agent research, findings review, fresh Docker-hosted OpenCode validation and gap filling, and a user-approved Markdown report. This test surfaced an interview ambiguity over testimonial-grade named-bank deployment evidence; the user resolved it explicitly and reconfirmed the amended brief. The intake guide and skill now include that branch.

External validation of the corrected real-research findings **failed to obtain a valid approved verdict** across four validator activations. Activation 1's dispatcher crashed on Windows `cp1252` decoding of UTF-8 stderr, although its complete validator JSON was recovered separately with ten issues. One fresh gap-filler run completed corrections. Activation 2 timed out after 900 seconds, leaving a container child that was later stopped. Activation 3 returned an invalid `approved_with_limits` plus open issues and falsely claimed a prior-day source-check date. Activation 4 had no verdict by the user's additional two-minute limit and was manually stopped. The [run record](live_test_run_codex/validation_failures.md) gives the timestamps, durations, exact failures, and bounded suspected causes.

The user chose to draft from the corrected sourced findings with visible evidence limits after reviewing the failed validation checkpoint. The final Markdown report (local test artifact: `test_reports/legal_ai_management_2026.md`) was approved; the previous report was retained under a separate filename. Its matrix counts reconcile, and its English voice has no Methodology section, recommendations, opportunities, suggested actions, or internal agent/skill process notes. Word export was not requested for this run.

The project copy now includes a single-object narrated-output parser, an explicit `approved_with_limits` contract, UTF-8 stream decoding, Docker stage-scoped timeout cleanup, run-time metadata, and clearer date/verdict prompts. The complete workflow suite passed **13/13 tests** after the changes. The timeout cleanup and prompt amendments have not been verified by another live validator run. Direct host OpenCode remains untested; Antigravity's denied URL permission remains unchanged. The repository remains on main with uncommitted changes, with no push or separate installed-skill sync.
