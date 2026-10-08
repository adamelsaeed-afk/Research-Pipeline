# Independent live-trial plan and execution record

**Local test artifacts:** Test-run folders referenced here but excluded from the repository, including `scratch/`, `scratch z/`, and `test_reports/`, were local test folders. Their paths are plain-text evidence references, not repository downloads. Statements about retained files describe the recorded run date. Published project files keep their normal links.

Observed outcomes are recorded in [NEW_TRIAL_REPORT.md](NEW_TRIAL_REPORT.md).

## Purpose

Exercise the revised research pipeline twice on one real technical research question. These are **simulated stakeholder interviews with native subagents**, not interviews or approvals by the human sponsor. The originating agent performs each trial's research. Fresh Docker-hosted OpenCode processes run Mimo for validation, DeepSeek for gap filling, and Mimo again for revalidation. The model outputs are evidence leads; the originating agent checks material claims against primary sources.

## Frozen input and preservation

The frozen project skill is `scratch/new_trials/frozen_skill/`, with its SHA-256 manifest at `scratch/new_trials/frozen_skill_manifest.sha256`. Trial Z writes only under `scratch/new_trials/z/`; the second independent Codex trial writes only under `scratch/new_trials/codex/`. Each trial has its own `dispatch_config.json`, interview transcript, intake, brief, plan, findings, runs, and report. The original `scratch/` and `scratch z/` evidence remains in place because earlier documentation links to it.

## Shared question and evidence rules

The topic is SQLite FTS5 versus PostgreSQL 16 full-text search for an internal documentation app with English, Spanish, and Arabic pages. Each trial independently resolves the stakeholder's corpus, deployment, permissions, required Arabic behavior, latency target, source window, and report form through a branching interview. Both use official SQLite and PostgreSQL 16 documentation first. A source claim requires a claim ID and URL. Application behavior, Arabic recall, security, and latency remain unmeasured until tested on the stakeholder's corpus. The report is descriptive and includes a reproducible benchmark protocol; it makes no recommendation.

## Gates and acceptance checks

1. Save exact simulated interview Q/A. The stakeholder confirms the complete brief; `check_intake.py` must pass on that exact file before source research.
2. Obtain separate simulated approval of the search plan. Record any scope correction and update the plan before source research.
3. Run a real headless source-access probe for both configured external models. A version response alone is insufficient.
4. Save source-grounded findings. Record stakeholder-identified gaps before dispatch. Dispatch Mimo in a fresh session; retain `dispatch.json`, `stdout.txt`, `stderr.txt`, and `result.json`. A malformed, absent, or timed-out result is a failure, not approval.
5. Send specific gaps to DeepSeek in a separate fresh session. Check its proposed corrections against primary sources, update the findings, and dispatch fresh Mimo revalidation. Report any unresolved issue accurately.
6. Produce a descriptive Markdown report and benchmark protocol. Review claim support, numbers, citations, and whether the report accidentally recommends an option.
7. Render image captures from the saved interview transcripts in `scratch/new_trials/session_screenshots/`. Label them as rendered transcript screenshots, not native chat captures, and link the underlying exact transcripts.

The two trials share the frozen skill and research scope, but start with fresh interviews, independent findings, and separate run artifacts. A passing workflow check does not establish measured search quality, latency, or production safety.

## After the trials

The test operator records observed pass/fail outcomes and model/tool limits with links to the artifacts. The human sponsor can review both reports and transcripts. Core-skill changes are recommended from the evidence and implemented only on a later explicit request. Preserve old scratch evidence until its documentation links can be updated safely.
