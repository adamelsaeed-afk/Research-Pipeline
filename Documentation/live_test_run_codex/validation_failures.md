# Codex A live test: validation failures and timings

**Local test artifacts:** Test-run folders referenced here but excluded from the repository, including `scratch/`, `scratch z/`, and `test_reports/`, were local test folders. Their paths are plain-text evidence references, not repository downloads. Statements about retained files describe the recorded run date. Published project files keep their normal links.

This running record was completed with the workflow. The full outcome is in [LIVE_TEST_REPORT_CODEX_A.md](../LIVE_TEST_REPORT_CODEX_A.md). All timestamps are Africa/Cairo local time, derived from retained run-file creation and dispatch-result timestamps except the bounded manual stop time.

| Run | Run ID | Start | End | Elapsed | Recorded outcome |
| --- | --- | --- | --- | --- | --- |
| Initial full validation | `a9c985587bb448b1808da5d9ddffde82` | 2026-10-01 23:54:12 | 2026-10-02 00:06:20 | 12 min 08 sec | **Dispatch failed.** Complete OpenCode JSON was recovered separately at 00:07:14 with `gaps_found` and ten issues; the failed dispatch remains failed. |
| Gap filling | `784a4dee32a64f58a50705a661ae857c` | 2026-10-02 00:09:02 | 2026-10-02 00:14:28 | 5 min 26 sec | Completed with ten corrections and zero unresolved items. |
| Full revalidation | `89c528a9f9d84025a54b0478b05dad06` | 2026-10-02 00:18:08 | 2026-10-02 00:33:08 | 15 min 00 sec | **Failed:** external CLI exceeded the configured 900-second limit; no result or verdict was returned. |
| Focused revalidation | `b34c613a659847eb9876903dce351bdf` | 2026-10-02 00:35:04 | 2026-10-02 00:40:56 | 5 min 52 sec | **Failed schema validation:** CLI exited successfully, but the output was not an approved validator result. |
| Focused revalidation with complete source URLs | `260fa1480232449dacd6f2f00f48c7b0` | 2026-10-02 00:45:45 | User cutoff 00:54:56; container process stopped by about 00:57:09 | 9 min 11 sec to cutoff; about 11 min 24 sec until confirmed stopped | **Failed:** no verdict by the user's two-minute extension. The dispatcher session was interrupted and the exact container process was terminated. |

## Why the initial full validation dispatch failed

The Windows Python dispatcher opened the Docker/OpenCode streams in text mode without selecting UTF-8. Windows used its `cp1252` default to decode UTF-8 stderr. The stream reader raised `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d in position 6076`. The dispatcher then received `None` instead of stderr text and raised `TypeError: data must be str, not NoneType`. The process left `dispatch.json` at `status: started`. A complete validator object existed in retained stdout, but that did not turn the failed dispatch into a success. The project copy now sets `encoding='utf-8', errors='replace'` on `subprocess.Popen` and records dispatcher exceptions.

## Why the focused revalidation failed

The external OpenCode response used `verdict: "approved_with_limits"` while also returning a nonempty `issues` list. The dispatcher correctly rejected that contradiction with `approved_with_limits cannot contain open issues`. The stdout also contained repeated/competing JSON output and claimed its sources were fetched on **2026-10-01**, although this run occurred on **2026-10-02**. The date claim is chronologically false. A research as-of cutoff of 1 October does not imply a validation check happened that day. The narrowed input omitted unchanged claim URLs, leading the validator to flag derived counts as unverifiable in that pass. No approved result was recorded from this run.

The project prompt now states the host validation date, distinguishes that date from the research as-of cutoff, requests exactly one complete JSON object, and requires `issues=[]` for `approved_with_limits`. The schema remains strict; it was not relaxed to accept this output. The full stdout, stderr and dispatch metadata remain at `scratch/delegate_runs/focused_revalidation/dispatch/b34c613a659847eb9876903dce351bdf/`.

## Why the final focused attempt failed and what remains uncertain

The fourth validator activation returned no verdict by 00:54:56 on 2026-10-02, two minutes after the user's stop instruction. It had been running since 00:45:45. The dispatcher session was interrupted shortly after the cutoff, but Docker's child OpenCode process remained active. The originating agent identified the exact child by its working directory and sent `TERM`; a second inspection showed it had stopped by about 00:57:09. No stdout, stderr, result JSON, or verdict was written for this attempt; the automatically written `dispatch.json` still says `started`, so this running test record is the failure record. The retained input and prompt are under `scratch/delegate_runs/focused_revalidation_2/dispatch/260fa1480232449dacd6f2f00f48c7b0/`.

**Observed reason:** the external OpenCode process had not finished source validation by the user-set cutoff. The available artifacts do not establish whether the model provider, source fetching, or its own analysis caused the delay. **Suspected contributor, not proven cause:** the earlier full revalidation that had timed out at the dispatcher was still running inside the container at the same time. That process was also terminated by its exact working-directory PID. The dispatcher had killed the host `docker exec` client on timeout but left the container child running. The project copy now sends `TERM`, then `KILL` if needed, only to container processes whose working directory equals that unique dispatch stage before ending the host client; it records cleanup results and preserves timeout stdout/stderr. This fix has a passing unit test, but a subsequent live timeout test has not been run. The older run lasted 15 minutes to the dispatch timeout and approximately 39 minutes until its orphaned child was discovered and stopped.

Across this live research, the validator was activated **four times**: initial full validation, full revalidation, focused revalidation, and focused revalidation with complete URLs. There was **one separate gap-filler activation**. The first validator's recovered JSON is diagnostic evidence, and none of the subsequent validator activations produced a valid approved result.

The user explicitly confirmed that the Leah/Mashreq testimonial qualifies when labeled testimonial-grade, and reconfirmed the revised complete brief. The intake checker passed after that confirmation. Validation remains in progress.
