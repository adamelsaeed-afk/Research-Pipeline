# Independent simulated-interview trial report

**Local test artifacts:** Test-run folders referenced here but excluded from the repository, including `scratch/`, `scratch z/`, and `test_reports/`, were local test folders. Their paths are plain-text evidence references, not repository downloads. Statements about retained files describe the recorded run date. Published project files keep their normal links.

**Dates:** 3–4 October 2026. **Frozen input:** `scratch/new_trials/frozen_skill/`; all 23 manifest entries matched their SHA-256 hashes after preparation and the Trial Z retry. The work used the trial plan in [NEXT_TEST_PLAN.md](NEXT_TEST_PLAN.md). No core skill file was changed during these trials.

## What was tested

Two independent research runs used the same frozen project skill and topic: SQLite FTS5 versus PostgreSQL 16 text search for an 18,000-page English, Spanish, and Arabic internal documentation app. A native subagent acted as the stakeholder. Its approvals were simulated scenario input, not human sponsor approvals. Trial Z and the Codex trial used separate folders, interview records, findings, dispatcher configurations, and reports.

The trial checked branching intake and exact brief confirmation, the deterministic intake gate, separate search-plan approval, primary-source research, Mimo validation, DeepSeek gap filling, fresh Mimo revalidation, and a descriptive report. The stakeholder's actual corpus, deployed search implementations, and latency measurements were unavailable, so this test cannot establish production relevance, security, or performance.

## Trial Z outcome

- The simulated participant refined and confirmed the brief, approved the search plan with an extension-scope correction, identified three additional gaps, and approved the corrected report. Interview transcript (local test artifact: `scratch/new_trials/z/interview_transcript.md`) · Report (local test artifact: `scratch/new_trials/z/report.md`)
- `check_intake.py` passed before source research. The direct Docker/OpenCode preflight passed for both configured targets. A harmless Mimo validation probe and a harmless DeepSeek gap-fill probe each returned structured, cited results.
- Fresh Mimo validation approved 12 primary-source findings. Result (local test artifact: `scratch/new_trials/z/runs/validation/dispatch/a3e4a60a53834166b39e413942f72b5f/result.json`)
- Fresh DeepSeek gap filling returned completed changes for the three stakeholder gaps: Arabic normalization test, authorization before result limiting and snippets, and two-local-index consistency. The originating agent excluded an extension-based suggestion that fell outside the confirmed brief and checked retained claims against official sources. Result (local test artifact: `scratch/new_trials/z/runs/gapfill/dispatch/c28c1a1d99bf41818e1f3995c413e055/result.json`)
- Fresh full Mimo revalidation of the expanded 15-claim file exceeded 300 seconds. A second, focused pass on the three new claims exceeded 240 seconds. Both were recorded as failed; neither produced a valid final verdict. The timeout traces show active source inspection and no observed quota error. The dispatcher reported scoped cleanup of one matching process for each timeout. Full timeout (local test artifact: `scratch/new_trials/z/runs/revalidation/dispatch/44058ad108fd402aa02be335fbbb8297/dispatch.json`) · Focused timeout (local test artifact: `scratch/new_trials/z/runs/revalidation_focus/dispatch/3fb617b68a584347a281edcb67b523d7/dispatch.json`)
- A later focused retry on F13–F15 completed in 177 seconds with `approved`, nine confirmed source checks, and no open issues. With the earlier F01–F12 approval, all 15 Trial Z claims have external validation across two successful passes. The two timed-out attempts remain useful latency evidence, not quota evidence. Retry result (local test artifact: `scratch/new_trials/z/runs/revalidation_retry/dispatch/c99b1a9cf0cc4d6b96d31c64e7ac3741/result.json`)
- The final report states documented functions and a reproducible benchmark protocol. It does not claim that the app meets the Arabic, security, or p95 target. Trial log (local test artifact: `scratch/new_trials/z/trial_log.md`)

## Independent Codex trial outcome

- The simulated participant separately chose the pipeline, answered a branching technical interview, added a Debian 12 detail at brief review, reconfirmed the amended exact brief, and approved a separate search plan. The intake checker passed before source research. Exact Q/A transcript (local test artifact: `scratch/new_trials/codex/interview_transcript.md`) · Brief (local test artifact: `scratch/new_trials/codex/research_brief.md`) · Plan (local test artifact: `scratch/new_trials/codex/search_plan.md`)
- The second trial started fresh findings rather than copying Trial Z's claims. Its first Mimo run approved two consequential source claims about FTS5 Arabic tokenization and PostgreSQL row-security caveats in 50.8 seconds. That result does not validate the entire report. Focused approval (local test artifact: `scratch/new_trials/codex/runs/dispatch/f26e1c4af14c42a3b598f8718ba975aa/result.json`)
- DeepSeek returned source-linked suggestions for three gaps in 52.0 seconds and left the fourth, which requires app-specific measurements, unresolved. The originating agent retained source-checked corrections and excluded an overstrong custom-tokenizer claim. Gap-fill result (local test artifact: `scratch/new_trials/codex/runs/dispatch/43f395594fda4457b065187c60b4716d/result.json`)
- Fresh Mimo revalidation of the three corrected claims exceeded 300 seconds. Its dispatch is failed, with scoped cleanup `matched=1`; it produced no valid verdict. Timeout dispatch (local test artifact: `scratch/new_trials/codex/runs/dispatch/c2561e243b3b44deaf3f6288e3f104c2/dispatch.json`)
- A fresh retry on corrected permission claim F09 returned `approved` in 41.4 seconds. This is claim-specific approval; other corrected claims remain without a final Mimo verdict. Focused revalidation (local test artifact: `scratch/new_trials/codex/runs/dispatch/39a85befc42c4a0aab49ddc85a5ebba7/result.json`)
- At the simulated gap checkpoint, the participant clarified a previously missed deployment branch: Git is the document source of truth, PostgreSQL receives imported search rows in one candidate, and SQLite may build or publish local indexes from Git in the other. PostgreSQL holds project memberships in both designs. The second trial amended the brief and plan, reconfirmed the exact brief, and reran `check_intake.py`; the gate passed. Earlier model results remain labeled against the prior brief version. This shows that the mechanical gate passed an interview whose meaning was not yet complete. Amended brief (local test artifact: `scratch/new_trials/codex/research_brief.md`) · Updated intake (local test artifact: `scratch/new_trials/codex/intake.json`)
- The simulated stakeholder reviewed the final report, requested one sentence defining when a dedicated search engine becomes a follow-up category, and explicitly approved the revised report as simulated input. Final report (local test artifact: `scratch/new_trials/codex/report.md`) · Trial log (local test artifact: `scratch/new_trials/codex/trial_log.md`) · Interview transcript (local test artifact: `scratch/new_trials/codex/interview_transcript.md`)

## Verification and limits

The frozen skill's 13 workflow tests passed. The `agent-reach` skill's documented `dl` Conda environment was absent on this host, so the research used the web tool to read official SQLite and PostgreSQL documentation. The interview images in the gallery (local test artifact: `scratch/new_trials/session_screenshots/gallery.md`) are rendered from saved transcripts and clearly labeled; they are not native chat screenshots. The Trial Z transcript keeps early rounds verbatim and condenses later checkpoint prompts for display; the Codex trial saved its exact Q/A transcript.

The first Trial Z Mimo approval covered F01–F12; the subsequent successful focused retry covered F13–F15. The earlier timeouts were failed attempts, not evidence of a quota limit. The independent Codex trial's approvals and gaps remain attributable only to its own inputs. Its external runs preceded the Git-ingestion clarification, so they do not validate the revised end-to-end deployment design.

## Warranted core-skill revisions for later review

1. The intake decision map should explicitly ask, when comparing storage or search topologies, which system is the source of truth and how every candidate receives creates, edits, deletes, permission changes, and rebuilds. The second simulated interview found this only at a later checkpoint; deterministic completeness cannot catch a branch the interviewer never records.
2. External validation needs a bounded, resumable claim batch contract. Mimo approved focused inputs in 41–51 seconds and a 12-claim file within its limit, but broader revalidation and one three-claim pass timed out while inspecting sources. The dispatcher correctly rejected those runs; a claim/source budget with partial progress artifacts would make the result more useful without weakening verdict rules.

These are recommendations from this test, not edits to the frozen or installed core skill.

## Intake revision follow-up, 8 October 2026

The user clarified that the storage/search questions above are specific to database
selection or implementation research when those details affect the comparison. The
knowledge-base documents stored in Git belong to this trial's application scenario.
They are not the research skill's working files or an assumed storage arrangement
for other users.

The trial-specific questions above remain historical test evidence. The reusable
correction is to derive branches from each current request. Active interview
instructions are maintained in the intake guide rather than this test report.

The project [intake guide](../references/intake.md) now directs the agent to derive
branches from the user's research question, intended use, and constraints, and to
resolve ambiguities that change inclusion, counting, evidence, comparison criteria,
or report coverage. It also separates context and scope choices for the user from
facts for the agent to research. The [skill entrypoint](../SKILL.md) points to this
guidance during the interview. The frozen trial copy and its results remain as tested;
the validation batching recommendation above is still pending.
