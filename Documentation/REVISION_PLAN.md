# Research Pipeline revision plan and verification record

> **Implementation status (2026-09-30):** The project copy includes branching intake and a checker, direct CLI and optional Docker dispatch, a shared-folder host bridge, report guidance, revised templates, and tests. A direct Codex validation probe passed outside the sandbox. A Docker-hosted OpenCode validator, gap filler, and fresh revalidator checked a public documentation claim. A job submitted from a separate agent container through the host bridge also completed validation and gap filling in OpenCode. Antigravity launched headlessly but its source check was denied by the container's URL permission policy; the user chose to leave those settings unchanged. Reverse container-to-container source validation through Antigravity therefore remains unverified. Word export completed, but visual rendering is unverified because LibreOffice is unavailable here. The separate installed skill remains untouched. A live end-to-end test (branching interview, intake gate, real research, external CLI validation, gap filling, delivered report) completed on 30 September – 1 October 2026; it recorded a fail for the original dispatcher parser and an open verdict-schema design limit, and the ten automated tests were rerun and passed. See [LIVE_TEST_REPORT Z.md](LIVE_TEST_REPORT%20Z.md).

> **Live test update (2026-10-02):** A second full research trial used the project copy, a new branching interview, a separately approved search plan, and a freshly chosen Docker/OpenCode model. The user approved the final report, but external validation did not reach a valid approved verdict after four real validator activations. The test exposed an ambiguous testimonial-deployment threshold, a Windows UTF-8 decoding crash, Docker child processes surviving a dispatcher timeout, and an external model's invalid verdict/date claims. The project copy now has explicit testimonial intake guidance, stricter verdict handling, UTF-8 decoding, scoped timeout cleanup, run timestamps, and revised prompt wording. Thirteen workflow tests pass; the timeout cleanup and prompt changes still need a live follow-up. See [LIVE_TEST_REPORT_CODEX_A.md](LIVE_TEST_REPORT_CODEX_A.md) and the [run failure record](live_test_run_codex/validation_failures.md). No push or installed-skill sync occurred.

## Agreed decisions

- Keep the skill portable across users and agent CLIs. Directly installed external CLIs are the standard delegation path; Docker is optional.
- `delegate` means a separate external CLI process. A native subagent does not satisfy this mode.
- Support three target CLIs: Antigravity (`agy`), OpenCode (`opencode`), and Codex (`codex`), whether directly installed or reached through a verified user-configured container route.
- For optional Docker setups, let each user configure their own container names and commands. Show generic syntax such as `docker start -ai <container-name>` for interactive startup, while testing a separate noninteractive command for delegation.
- The agent from which the user invokes the skill performs the research. External CLIs perform validation and gap filling.
- Intake is a branching research interview. The user confirms a complete research brief before research begins.
- Deliver the management report in formal, direct English. It presents information and evidence only, with no recommendations, opportunities, next steps, or suggested actions.

## Goal

Make the skill interview the user until the research scope is clear and confirmed; make a chosen delegation mode launch genuinely separate external CLI sessions; and deliver a sourced, descriptive management report without agent or skill process notes.

## Feasibility and limits

- Intake and report changes: high feasibility. The instructions and templates are within this repository. A checker can reject an incomplete or unconfirmed research brief when the pipeline calls it. A skill file alone cannot intercept every search or tool call in every agent runtime, so the strongest technical guarantee requires a controller or tool boundary that refuses Phase A until the check passes.
- Direct CLI delegation: feasible when the chosen executable is installed, authenticated, able to access sources, and able to write result artifacts. This path must work without Docker.
- Host-to-container delegation: verified with a Docker-hosted OpenCode CLI in this installation. Other CLIs and installations require their own headless source-access test.
- Container-to-container delegation: verified from one agent container through the shared-folder host bridge to Docker-hosted OpenCode for validation and gap filling. The reverse source-check route remains blocked by Antigravity's URL permission policy in this installation. A container cannot directly invoke another container or host CLI without a configured route.
- Publication-ready writing: high feasibility as an editorial and evidence-review process. It cannot honestly guarantee human authorship or that every reader will judge the prose human-written.

## Implementation order

1. Implement the branching intake interview, research-brief confirmation, and phase gate, including target selection for validator and gap-filler.
2. Build a portable, research-only dispatcher with direct-process adapters for `agy`, OpenCode, and Codex. Prove validation → gap filling → revalidation without Docker first.
3. Add an optional Docker transport to the same dispatcher, driven by each user's local container commands and file-transfer configuration. Prove host-to-container, then container-to-container, without changing the direct-process path.
4. Revise report templates and create a focused English editorial guide, then run an end-to-end report and Word export review.
5. Update README for direct delegation and, only after Docker dispatch is verified, for user-configured Docker delegation. Verify the full package in this project folder.
6. Leave the separate skill installation under `D:\AI-agents\skills` untouched. It is updated after the repository changes are pushed, as the user specified.

## 1. Interview until the research brief is complete

- Use the existing ten questions as an initial map, not a fixed checklist or a limit. Build a decision tree from the user's request. Ask questions in rounds: each round covers the decisions that can be made with the answers already known; answers may open new branches. For example, market sizing may need segment and base-year choices, while a technical comparison may need evaluation criteria and target environment.
- Track each relevant decision as `pending`, `unclear`, `answered`, or `not_applicable`, including branches discovered during the interview. An answer already supplied in the user's request counts. An optional answer can explicitly be "none"; a conditional branch can be not applicable with a recorded reason. Never infer a choice from silence or an offered default.
- Clarify vague or conflicting answers and keep asking until every branch needed to define this research is resolved. If the user asks the agent to choose, propose a concrete value and get the user's confirmation. Do not ask hypothetical questions that cannot change the research brief.
- Present a concise research brief that states the research questions, targets, scope, exclusions, evidence period, comparison or sizing dimensions, report form, and validation arrangement. Ask the user to correct or confirm it. New corrections reopen the affected branches. The interview ends only when no relevant branch remains open and the user confirms the brief.
- Do not create the search plan, search, delegate, or compile a report before the confirmed brief passes a deterministic completeness check. Keep search-plan approval as a separate later checkpoint. The checker validates recorded fields and confirmation; the agent judges whether the interview resolved the meaning of the request.
- Route phase transitions through this check. If an agent runtime can still browse independently, test and describe that instruction-level limit honestly rather than claiming a skill file can technically block all tools.

**Pass:** In dry runs with omitted, vague, conflicting, and newly branching answers, the agent continues the interview. An unconfirmed brief cannot enter Phase A; a complete brief confirmed by the user can.

## 2. Define what “delegate” means and make it observable

- Rename the validation choices to `same-session validation` and `external CLI validation and gap filling`. A native subagent is never substituted for an external CLI request. The originating agent always owns research and final report compilation.
- At intake, ask which CLI will validate and which will fill gaps. They may be the same CLI product, but must run in separate fresh sessions for the two roles. Check each executable, authentication, network and source access, working directory, and output permissions before research starts. For OpenCode, also record the allowed provider/model instead of guessing. Report the exact missing prerequisite and wait for the user's choice if a target cannot run.
- Prefer a validator using a different CLI product from the researcher when available; distinct sessions of the same product still satisfy external delegation, but provide less independent judgment. State the selected roles in the internal run record.
- Build a research dispatcher for both roles. Stage a separate validation directory containing the brief, findings, cited source list, and output location; keep search plans and notes out of it. Stage a separate gap-filling directory containing the gap report and relevant finding/source identifiers. Use each target CLI's read/write restrictions where available. Capture the command, process ID or session ID, exit status, output file paths, and verdict in an internal dispatch record. Require real output artifacts before advancing.
- After gap filling, invoke the validator again in a fresh session to check proposed corrections. Never treat the gap-filler's own report as validation. Continue while a pass adds material evidence or resolves a finding. If repeated attempts add no evidence, a source is inaccessible, or a contradiction cannot be resolved, stop retrying that issue and present the precise uncertainty to the user. Do not publish an unsupported claim as verified or end the entire research run merely because an arbitrary retry count was reached.
- Reconstruct only the useful dispatch pattern from `delegate-skills` inside this research skill: self-contained brief, separate CLI session, result artifact, exit/error capture, and review by the originating agent. Remove coding tasks, diffs, commits, worktree assumptions, and unrelated implementer tools. Build only the `agy`, OpenCode, and Codex adapters needed for research validation and gap filling.
- Keep the orchestrator responsible for reviewing the returned validation work and deciding whether gaps are resolved.

**Pass:** A user selecting external delegation sees separate CLI runs and artifacts for validation, gap filling, and revalidation. The loop resolves each issue, records an evidence-backed uncertainty, or asks the user about an impasse. An unavailable CLI produces a clear stop and options; it never becomes an in-process validator or native subagent without a new user choice. Research remains with the originating agent.

## 3. Make direct CLI delegation work; add Docker as an optional transport

- The dispatcher accepts a target CLI and a transport. `direct` starts the target executable in a fresh local process and requires no Docker installation. `docker` uses a user-configured container route. Both transports use the same research briefs, staged input/output contract, result checks, and validation loop.
- Discover direct executables from the user's environment or an explicit executable path. Check version, authentication, source access, working directory, model selection where required, and output permissions. A missing target stops that delegated run with a precise prerequisite; it never silently changes to a native subagent or another transport.
- Keep Docker commands out of the shared skill defaults. Each Docker user supplies the command or structured command arguments needed to start their container, run the agent CLI noninteractively, and exchange input/output files. Validate the configuration before research starts. A start/attach command alone does not prove delegation works.
- For a configured Docker setup, inspect each selected container and test a noninteractive route through `docker exec` after it is running. If a container exits when detached or lacks file access, adapt its lifecycle or use another explicitly configured route. Never assume a container name from its CLI name.
- For container-originated research that delegates to a sibling container or host CLI, use a narrowly scoped host dispatcher only if that route proves necessary. Test access from each container; avoid giving agent containers unrestricted Docker control. Direct delegation remains usable for people who run their agents and target CLIs in the same environment.
- Use structured argument lists or a narrowly specified launcher instead of evaluating arbitrary configuration through a shell. Keep credentials out of committed configuration. Follow the active agent runtime's permission and network rules; a skill instruction cannot cross a denied boundary.

**Pass:** Each of `agy`, OpenCode, and Codex can perform validator and gap-filler roles via direct CLI execution on a suitable machine without Docker. Docker users can supply and verify their own container commands. When a Docker route is unavailable, the dispatcher reports exactly why; the direct route still works. External delegation never falls back to a native subagent without a new user choice.

### Delegation acceptance matrix

| Target | Direct CLI test | Optional Docker test |
|---|---|---|
| `agy` | Fresh headless run returns a nonempty structured result and role artifact | User-configured container run returns the same contract; detect hangs, auth failure, and denied writes |
| `opencode` | Fresh `opencode run` with an explicitly allowed model returns a role artifact | User-configured container run returns the same contract; detect missing model and file-access failure |
| `codex` | Fresh `codex exec` returns a role artifact under the active sandbox | Container route only if that user has configured and verified it |

For each available target, test validator, gap-filler, and fresh-session revalidation. Also test absent executables, failed authentication, source-network failures, and malformed or missing artifacts.

## 4. Make the report descriptive and ready for management

- Remove `Methodology` from the comprehensive template, sample structure, intake template preview, and report-review rules. Remove template-adaptation notes, agent roles, skill names, scratch paths, validation logs, and other process language from delivered reports. Keep validation details internal.
- Remove recommendations, proposed actions, next steps, prescriptive implications, and opportunity language from every final report type. Rename `Gaps & Opportunities` to a descriptive heading such as `Observed gaps`; make the simple template's conclusion a factual summary. An internal gap report may still tell the gap-filler what evidence to check, but that operational text never enters the delivered report.
- Put the necessary research context in the executive summary or a brief scope line: entities, geography, and as-of date. Keep claims traceable through normal citations and a references section. State material evidence limits as facts, without advising the reader what to do.
- For estimates such as Total Addressable Market, keep necessary assumptions and calculation bases next to the finding or in concise notes. Removing the `Methodology` heading must not hide information management needs to judge a number.
- Reconstruct the useful editing principles from `humanizer-zh` as a short, self-contained English report-voice reference: direct sentences, concrete claims, natural rhythm, no stock AI phrasing, and no promotional copy. Do not require the Chinese-language skill or its unrelated output format. Keep formal, direct English and preserve factual meaning; do not add anecdotes, opinions, or facts during rewriting.
- Revalidate numbers, citations, classifications, and the absence of prescriptive wording after the editorial pass. Check Markdown and exported Word output for visible template comments, placeholders, and process notes.

**Pass:** A reader can send the report to management as delivered. It answers the research questions with sourced information, including material uncertainty, and contains no recommendations, suggested actions, agent or skill names, prompts, template adaptations, or internal validation phases.

## 5. Update and verify the package

- Update `SKILL.md`, both report templates, the validation reference, README, and the sample consistently. Add only a research-brief checker, three research CLI adapters, the optional Docker transport, and the focused English style reference. Keep the public workflow concise; put transport detail in a conditional reference.
- Add a README delegation setup section with two clear routes: **direct CLI** (no Docker, target CLI installed and authenticated) and **optional Docker** (each user supplies their own start command, noninteractive execution command, file-transfer or shared-path arrangement, and any required model). Use generic placeholders in all published examples; never include a user's actual container names. Explain the preflight test and what happens when a route is unavailable. Document Docker support as verified only after end-to-end tests pass.
- Run skill structural validation, branching-intake scenarios, direct delegation success/failure scenarios, stalled-evidence scenarios, and one end-to-end report export with visual review. Then run Docker-specific host-to-container and container-to-container scenarios separately. Review the report for prescriptive wording as well as process leaks.
- Make changes only in `D:\Research skill`. Do not sync the Codex-installed copy or the separate installation under `D:\AI-agents\skills` during this revision. Update the latter after the repository changes are pushed, as the user specified.

## Evidence to collect during implementation

1. On a machine with direct installations, prove each available target CLI can launch headlessly, access a harmless source, and return a staged artifact without Docker. Use a harmless local fake executable to test missing/failed/malformed-result behavior where a real target is unavailable.
2. Locate the working Docker executable and daemon connection in the local Windows PowerShell test environment; determine why the agent session cannot see `docker`.
3. Inspect the configured containers' running state, entrypoint, workspace mounts, and availability of `agy` or `opencode`. Check whether they stay running without interactive attachment.
4. Run harmless headless CLI and source-access probes inside each container and with host Codex. Confirm the approved OpenCode model at runtime.
   - For Antigravity, check the installed version and require a non-TTY `agy -p` run with machine-readable output to exit, return a nonempty result, and honor the intended permissions. Its documented headless mode makes this plausible, but version-specific hangs have been reported.
   - For OpenCode, prove `opencode run` with the selected model returns output from the container without entering its terminal interface.
5. Prove the host-side dispatch path works when the originating agent is inside each container. If a path fails, record the exact barrier and revise that path before claiming support.

### Optional Docker feasibility test, in order

1. **Read-only host inventory:** in the local Windows PowerShell test environment, identify the Docker command, daemon version, and current state/image of each configured container. Do not start or alter containers yet.
2. **Host → container launch:** for each already running container, run only a CLI version/help command through `docker exec`. If stopped, first inspect its lifecycle; then start it only for a test the user has agreed to. This proves command routing, not agent functionality.
3. **Headless agent result:** run a bounded, harmless prompt through `agy` and `opencode`, capture exit code and nonempty structured output, and confirm no interactive prompt or hang. Test a permitted source URL and a staged file separately.
4. **Container → host reachability:** from each originating container, test name resolution and connection to a temporary host endpoint via `host.docker.internal`. This proves transport only; do not expose Docker control or credentials through it.
5. **Container → container dispatch:** use the narrowly scoped host dispatcher to submit one harmless validator job from each container to the other target, then confirm the job ID, fresh external process, output artifact, and error path. Repeat for the gap-filler role before declaring the route supported.

Mock executables test dispatcher behavior only. Do not claim a particular direct CLI adapter is verified until it has run against that real CLI in a direct installation; document any unverified adapter honestly in the README.

Every relevant branch of the research interview needs an explicit, clear resolution. A clear answer already supplied in the initial request counts. An ambiguous answer or "you decide" requires a concrete proposed value and user confirmation. The final gate is the user's confirmation of the complete research brief, not merely completion of ten predefined fields.

## Reference points

- The repository currently requires `Methodology` in the comprehensive report template and describes delegation only as a workflow pattern.
- The linked `delegate-skills` package describes a coding-task workflow. This plan borrows only the separate-session dispatch idea and does not retain its diff or commit workflow: https://github.com/amElnagdy/delegate-skills
- Official Codex guidance supports native Windows execution with bounded permissions: https://learn.chatgpt.com/docs/windows/windows-sandbox
- Official Codex permission guidance treats local command execution and external integrations as separate controlled surfaces: https://learn.chatgpt.com/docs/permissions
- Docker documents `start -ai` as starting and attaching to the container's primary process, while `exec` launches a separate command in a running container: https://docs.docker.com/reference/cli/docker/container/start/ and https://docs.docker.com/reference/cli/docker/container/exec/
- Docker Desktop documents `host.docker.internal` as a route from a container to a host service: https://docs.docker.com/desktop/features/networking/networking-how-tos/
- Antigravity documents headless output and errors, and OpenCode documents noninteractive `run`: https://antigravity.google/docs/cli/headless/ and https://opencode.ai/v2/docs/cli
