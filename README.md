# Research Pipeline

A skill for sourced technical and market research. The agent interviews you until
the research brief is clear, asks you to confirm that brief and a separate search
plan, conducts the research, validates the evidence, and writes a formal English
report ready for management review. Reports contain findings and limitations, with
no recommendations or internal agent process.

The originating agent performs the research. Validation can run in that session or
in fresh external CLI processes. External delegation supports Antigravity (`agy`),
OpenCode (`opencode`), and Codex (`codex`) for validation and gap filling. The skill
does not require a separate delegation skill, Node.js, or Git for that route.

## Install

Install with the Skills CLI:

```text
npx skills add adamelsaeed-afk/Research-Pipeline
```

Or copy this repository's skill files to the skills directory used by your agent.
Use the documentation for your agent to locate that directory. Python 3.10 or later
is needed for the intake checker and external dispatcher. Word export additionally
uses [uv](https://docs.astral.sh/uv/).

## Run a research project

Invoke the skill with the research question. For example:

> Compare documented automation features in three project-management platforms.

The agent derives follow-up questions from your research question, intended use,
and constraints, and asks only about unresolved choices that affect the research.
Questions about the subjects' capabilities become research questions for the agent
to investigate. It then shows the complete brief for your confirmation. A local checker rejects an
incomplete or changed brief and changes to recorded decisions. Confirmation binds
both the brief and the intake decisions. Validation routing choices and confirmation
also need a user-message reference and supporting quote. Older records without these
fields must be reviewed against actual conversation evidence, with unresolved choices
returned to the user (see [intake guide](references/intake.md)). The checker validates
recorded evidence and hashes; it cannot authenticate messages or prove consent.
The agent explicitly presents same-session and external CLI validation unless you
already chose or authorized it to choose. It checks the environment before claiming
CLI availability. After you separately approve the search plan, or explicitly authorize
proceeding without that checkpoint, the
originating agent researches and cites the findings. The chosen validation route
checks the evidence, and the agent prepares the descriptive report.

The report can use the comprehensive, simple, or an agreed custom structure. At
delivery, the agent offers Word export unless you already requested or declined it.
Word styles are `corporate`, `academic`, and `minimal`:

```text
uv run scripts/export_to_word.py --input report.md --output report.docx --template corporate
```

`examples/sample_research.md` is an illustrative layout with fictional entities,
prices, and `.example` URLs. It is not an evidence source or a real market report.

## Direct external CLI delegation

Direct CLI is the standard route and needs no Docker. Install and authenticate the
selected target CLIs in the environment where the originating agent runs. Check
each target's version/help command, then prove a harmless headless run can read a
source and return a result. A command appearing on `PATH` alone does not establish
authentication, source access, or permission to create artifacts.

After the research brief is confirmed and before the search plan, run:

```text
python scripts/preflight_delegate.py --config <local-config.json> --record <intake.json> --brief <research_brief.md>
```

This checks routing for the selected validator and gap filler. The harmless
source-reading probe is a separate acceptance check. Run it once per configured
target and inspect its `checks` and `stderr.txt` for actual source access. It uses a
small live CLI request and may consume model usage:

```text
python tests/manual_live_dispatch.py --config <local-config.json> --target <target-name>
```

Each probe has its own input directory, including Docker probes. A blocked verdict,
unresolved correction or unrelated source fails probe acceptance. Passing its
structured checks still requires inspecting source-reading evidence in the logs.

Dispatch exit codes distinguish execution from evidence: 0 is approval or resolved
gap completion, 3 is a valid result requiring attention, 2 is execution/contract
failure, and 130 is cancellation. Gap completion always needs fresh validation.
The dispatcher and mailbox return the verdict, unchecked IDs and a user notice;
the originating agent must surface attention notices before advancing.

Keep configuration in an ignored local file outside untrusted shared directories.
Configuration can select executable paths, so review it as executable authority.
Use native CLI binaries rather than shell/batch shims. Runtime environment variables
are restricted; opt in to additional authentication variable names with a target's
`environment_allowlist`, never by placing secret values in prompts or configuration.
See the [delegation security boundaries](references/delegation.md) for limits.

Research sources and delegated text are untrusted evidence, not authority to run
commands or change permissions. A fresh session does not isolate files. Apply the
host's permission controls and keep research logs private. These controls reduce
risk; they do not guarantee immunity to prompt injection or a clean scanner rating.

Create a local JSON configuration outside version control. Target names must match
the confirmed `validator_cli` and `gap_filler_cli` answers in `intake.json`. When a
model is configured, the corresponding `validator_model` or `gap_filler_model`
answer must exactly match its model ID. Keep annotations such as "tested
successfully" in a separate note:

```json
{
  "targets": {
    "validator": {
      "cli": "agy",
      "transport": "direct",
      "executable": "agy"
    },
    "gap_filler": {
      "cli": "opencode",
      "transport": "direct",
      "executable": "opencode",
      "model": "<provider>/<model>"
    },
    "second_validator": {
      "cli": "codex",
      "transport": "direct",
      "executable": "codex"
    }
  }
}
```

The examples are alternative target entries; configure only the targets you use.
Choose the OpenCode provider/model from the models available in that installation.
Each dispatcher call creates a new process and staged directory. It does not reuse
a CLI conversation. A validator can be called again after gap filling, with the
updated findings, for an independent recheck.

```text
python scripts/check_intake.py --record <intake.json> --brief <research_brief.md>
python scripts/research_dispatch.py --config <local-config.json> --record <intake.json> --brief <research_brief.md> --role validate --target validator --input <raw_findings.md> --run-dir <run-directory>
python scripts/research_dispatch.py --config <local-config.json> --record <intake.json> --brief <research_brief.md> --role gap_fill --target gap_filler --input <gap_report.md> --run-dir <run-directory>
```

The output path printed by the dispatcher points to `result.json`. Its sibling
`dispatch.json` records the command, target, transport, start and finish times,
elapsed seconds, exit status, and any error.
It also saves `input_ids.json` with the expected IDs and staged input SHA-256.
Legacy records such as `## C1 Finding` and `G1: Verify the claim` work directly.
For a custom table or other ambiguous layout, add `--input-ids <ids.json>` containing
a JSON list such as `["clio-chat", "filevine-chat"]`. IDs must occur in the input
and the list must include every material record; the originating agent is responsible
for completeness. Ambiguous input without an explicit list fails before launch.
Approving validation must cover all expected IDs; partial nonapproval records
unaccounted IDs in `dispatch.json`. Gap completion must account for every supplied
gap through changes, unresolved reasons or both. See the
[delegation contract](references/delegation.md) for document citations and schemas.
An interrupted dispatch records `cancelled`, the cancellation reason, and finish
time. Stdout and stderr are captured continuously in `stdout.txt` and `stderr.txt`,
retaining output emitted before cancellation. The dispatcher stops the host
process and, for Docker, attempts the scoped container cleanup described below.
Cleanup errors are recorded in `dispatch.json`. A cancelled run does not count as
completed validation, even if its captured output contains a proposed verdict.
Empty or malformed output is a failure; the dispatcher never silently changes to a
native subagent. If a selected CLI is unavailable, correct its installation or
configuration, or make a new explicit validation choice with the user.

## Optional Docker route

Docker can run a configured target CLI in a container while the originating agent
runs on the host. Each user supplies their own container name, startup command,
mounted directory, container mount path, CLI executable, and model where required.
Do not copy another user's container names or credentials into shared files.

An interactive startup command can look like `docker start -ai <container-name>`.
It is not the delegation command. The container must stay running so the dispatcher
can launch a fresh noninteractive CLI process with `docker exec`. Configure a host
directory mounted in the container; place the run directory beneath that host path:

```json
{
  "targets": {
    "container_validator": {
      "cli": "agy",
      "transport": "docker",
      "executable": "agy",
      "docker": {
        "executable": "docker",
        "container": "<container-name>",
        "host_mount": "<absolute-host-shared-directory>",
        "container_mount": "/research-shared",
        "start_argv": ["docker", "start", "<container-name>"]
      }
    }
  }
}
```

`start_argv` documents the user's local startup command; the dispatcher does not
run it. Start and authenticate the container according to its own setup. Confirm
`docker exec <container-name> <cli> --version` works, then run a harmless headless
prompt that reads a permitted source and produces a result in the shared directory.
Test validation, gap filling, and a fresh revalidation separately. Docker permission,
authentication, mounts, and networking differ by installation; support for a
particular setup is established only by those end-to-end runs.
On a dispatcher timeout or interruption, the Docker route targets processes carrying
that run's inherited `RESEARCH_DISPATCH_ID` marker, with the unique staged working
directory retained as a fallback. The marker follows children after directory or
parent changes. This cleanup uses `sh`, `tr`, `grep`, `readlink`, and Linux `/proc`; a
container lacking them reports a cleanup error in `dispatch.json` and requires
manual process inspection.
Local dispatches use a Windows Job Object or POSIX process group to stop descendants.
The POSIX guarantee covers children retaining that group, and Docker's marker must
remain inherited/readable; deliberate detachment or marker removal is outside this
cleanup guarantee. These mechanisms do not provide filesystem isolation.

The same live probe can exercise a Docker target from the host when its container
and shared mount are ready. It creates a test run beneath `host_mount/probe`.

For research originating inside one container and delegating to a sibling container,
the host can run `research_mailbox.py worker` against a shared directory. The
originating container writes a fixed research job with the included shell client; the host worker
checks the intake and uses only configured targets. Both containers need access to
the staged files, and the host worker needs Docker access. This route does not mount
the Docker socket into the originating container or accept arbitrary shell commands.
Use a shared directory writable only by trusted participants.

On the host:

```text
python scripts/research_mailbox.py worker --shared-root <absolute-host-shared-directory> --config <local-config.json>
```

From a Linux originating container, with the same directory mounted at
`/research-shared` and this skill directory available there. The shell client
requires no Python installation in the container; the host worker requires Python:

```text
sh /research-shared/scripts/submit_research_job.sh /research-shared intake.json research_brief.md validate container_validator raw_findings.md
```

The client prints a job ID, waits for the host worker, and prints its response.
Paths in the request are relative to the shared root; the response gives the
result path relative to that root. The originating agent must read the result
before proceeding. If Python is installed in the container, the equivalent
`research_mailbox.py submit` command is also available. A version/help probe
verifies routing only; a complete source check and result are needed to establish
support for a particular installation. For Antigravity headless runs, URL reads
that require approval are denied unless the user configures a suitable scoped
`read_url(domain)` permission for the research sources.

The Python mailbox client accepts `--input-ids <ids.json>` under the shared root.
The shell client accepts an eighth relative INPUT_IDS path after TIMEOUT; existing
six/seven-argument calls remain supported.
Both clients attach a queue expiry of submission time plus TIMEOUT and 30 seconds.
Late queued requests return `expired`; execution uses the remaining deadline.
Requests from older clients without an expiry fail and need explicit resubmission.
The worker holds an exclusive lock for its shared root. On restart it reports
abandoned `.processing` requests as `interrupted`, retaining the request and any
existing response without automatically rerunning the model.

## Verification status

On 23 October 2026, the six focused readiness repairs passed 77 tests on Windows
(three platform/privilege skips) and 77 on Ubuntu (no skips). A new bounded
Docker/OpenCode trial caught a seeded false claim, corrected it and checked the
correction in a fresh validator process using actual source fetches. It used
OpenCode 1.18.35 with `opencode/mimo-v2.6-flash-free`. Bandit reported zero
high/medium and six reviewed low findings; pip-audit found no known advisories in
the six installed exporter dependencies. These results do not clear the historical
Snyk indirect prompt injection warning or establish universal attack resistance.
See the [V1.2 change log](Documentation/V1.2_CHANGE_LOG.md) for scope and limits.

The route table below preserves the development evidence through 8 October 2026.
The 9 October V1.2 trial subsequently completed four-claim Docker/OpenCode validation
in two batches and inspected its new Word output. The 19 October contract and
lifecycle repairs have separate local regression checks; they do not establish
fresh verification of every CLI or research mode. See the V1.2 change log.
Implementing an adapter does not establish that every installation can use it.

| Route | Recorded evidence |
|---|---|
| Docker-hosted OpenCode | Live validation, gap filling, and fresh revalidation completed. Other revalidation runs timed out or returned invalid results; the latest Z trial covered all 15 claims across two successful passes, while the independent Codex trial retained partial coverage. |
| Shared-folder host bridge to Docker OpenCode | Validation and gap-fill jobs returned result artifacts from a separate originating container. Some original artifacts were not retained. |
| Direct Codex | An earlier validation probe completed outside the sandbox. Its raw output was not retained; it does not establish a complete direct research workflow. |
| Direct OpenCode | No successful direct-host trial is recorded. |
| Docker-hosted Antigravity | The CLI launched, but its source read was denied by that installation's permission policy. Source-checking validation remained blocked there. |
| Direct Antigravity and Docker-hosted Codex | No successful source-checking trial is recorded. |

The 3–4 October trials used simulated stakeholders, rather than human sponsor
approvals, and did not measure the target application's production behavior.
The 8 October cancellation change passed the 16-test workflow suite, including a
real local child-process interruption. Docker cancellation was tested with mocks;
earlier live timeout records exercised scoped Docker cleanup. Bounded validation
batches have since completed with manual intervention. Automatic resumable
orchestration remains deferred.

Run the source-access probe with your own configured CLI, model, permissions, and
transport before relying on delegation. Detailed outcomes are in the reports below.

## Revision documentation

- [Change report](Documentation/CHANGE_REPORT.md): what changed and how the revised workflow runs.
- [V1.1 test report](Documentation/V1.1_TEST_REPORT.md): partial-pass verdict and current shortcomings observed in the legal-AI trial.
- [V1.2 implementation plan](Documentation/V1.2_IMPLEMENTATION_PLAN.md): approved focused repair scope and acceptance checks.
- [V1.2 change log](Documentation/V1.2_CHANGE_LOG.md): exact edits, verification results and remaining limits.
- [Revision plan](Documentation/REVISION_PLAN.md): agreed decisions and implementation plan.
- [Final test report](Documentation/FINAL_TEST_REPORT.md): observed results and remaining limits.
- [Z live test](Documentation/LIVE_TEST_REPORT%20Z.md): the first real-research trial, its corrections, and validation limits.
- [Codex A live test](Documentation/LIVE_TEST_REPORT_CODEX_A.md): the second real-research trial and dispatcher failures.
- [Combined live-test problems](Documentation/COMBINED_LIVE_TEST_PROBLEMS.md): comparison of the two original trials.
- [Independent Codex/Z trials](Documentation/NEW_TRIAL_REPORT.md): the 3–4 October simulated interviews and later intake clarification.

These reports summarize historical runs. Test-run folders referenced in them but
excluded from the repository, including `scratch/`, `scratch z/`, and
`test_reports/`, were local test folders. Their artifact paths are plain-text
evidence references rather than download links. Statements about retained files
describe the recorded run date. Current agent instructions live in `SKILL.md` and
`references/`. Track outstanding fixes and verification work in repository issues.

## Repository files

- `SKILL.md`: skill workflow and gates.
- `references/intake.md`: branching interview and confirmed record.
- `references/delegation.md`: external CLI roles and transport contract.
- `references/validation_protocol.md`: evidence checks and revalidation.
- `references/report_voice.md`: formal English report editing.
- `scripts/check_intake.py`: deterministic recorded-intake gate.
- `scripts/strict_json.py`: bounded JSON/text reads; rejects duplicate keys and nonfinite numbers.
- `scripts/process_tree.py`: owns local CLI descendants for scoped cleanup.
- `scripts/preflight_delegate.py`: direct or Docker command-routing check.
- `scripts/research_dispatch.py`: direct CLI and host-to-container dispatch.
- `scripts/research_mailbox.py`: shared-folder host bridge for container-originated runs.
- `scripts/submit_research_job.sh`: Python-free Linux container mailbox client.
- `templates/`: Markdown report structures and Word styles.
- `examples/sample_research.md`: fictional formatting example.
