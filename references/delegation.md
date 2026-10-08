# External research delegation

The originating agent does all general research and owns the report. A validator
checks staged claims against sources. A gap filler addresses identified issues.
Each dispatch starts a fresh `agy`, `opencode`, or `codex` CLI process; no resume or
continuation option is used. The same CLI product may fill both roles, but each pass
uses a separate run. Prefer a different product for validation when configured.

## Before dispatch

The confirmed intake names the validator and gap-filler targets. Configure each in a
local, uncommitted JSON file as documented in README. Confirm the executable and
version, authentication, source access, chosen model where needed, and access to the
staged directory. A version/help command proves command routing only. A harmless
headless prompt with a readable source and result proves the usable route.

Run `scripts/preflight_delegate.py --config <local-config.json> --record
<intake.json> --brief <research_brief.md>` before the search plan. It checks routing
for both selected targets. It cannot prove authentication or source access; run a
harmless headless probe in the target environment before relying on delegation.

Direct CLI is the standard transport. Docker is optional and requires a user-supplied
container name plus a host directory mounted at a known container path. The project
dispatcher runs `docker exec` only against that configured container; it does not
infer names or launch an interactive terminal. Users start stopped containers using
their own commands. `docker start -ai <container-name>` attaches interactively and
is not itself a headless dispatch command.

The dispatcher uses argument arrays and `shell=False`. It never executes arbitrary
configured shell text. It records the command and result files in a private run
directory. Keep credentials out of configuration and staged material. Use each CLI's
ordinary permission policy; do not grant unrestricted shell or Docker access to
solve routing failures.

## Dispatch contract

Run from the project skill directory:

```text
python scripts/research_dispatch.py --config <local-config.json> --record <intake.json> --brief <research_brief.md> --role validate --target <target-name> --input <raw_findings.md> --run-dir <run-directory>
python scripts/research_dispatch.py --config <local-config.json> --record <intake.json> --brief <research_brief.md> --role gap_fill --target <target-name> --input <gap_report.md> --run-dir <run-directory>
```

The intake checker runs again on each dispatch. A new directory contains only the
brief, role input, and prompt. The CLI returns one JSON object. The dispatcher
requires a matching role, a verdict, and the role's issue or change list, then saves
`result.json`, `stdout.txt`, `stderr.txt`, and `dispatch.json`. Failed, timed out,
empty, and malformed runs do not count as validation. The research agent reviews
the artifact and makes the final evidence judgment.

The validator result has `role: "validate"`, `verdict` of `approved`,
`approved_with_limits`, `gaps_found`, or `blocked`, a `summary`, `issues`,
`checked_claim_ids`, and source `checks`. `approved_with_limits` requires a
`limitations` list of `{claim_id, reason}` for each partial or unverifiable check;
it is only for nonmaterial uncertainty, never a mismatch or material gap. Each check
names the claim, source URL, brief source-grounded evidence, and a verdict. Each issue
names a claim or gap and the supporting or contradictory source URLs. The gap-filler result has
`role: "gap_fill"`, `verdict` of `completed` or `blocked`, `summary`, `changes`, and
`unresolved`. Each change names the gap ID, corrected finding, and source URLs.

After material changes, dispatch a new validator run using the updated findings.
Continue while evidence progress is possible. Record unresolved source limitations
and conflicting claims explicitly. Ask the user for a choice if the treatment would
change the agreed scope. An unavailable CLI stops this delegated route; changing CLI,
transport, or validation mode requires a new user choice.

## Container-originated research

Host-to-container dispatch uses `docker exec` from a host process with Docker access.
A containerized originating agent can use direct CLI for targets installed in its own
container. Sibling-container dispatch needs a host-side route because the container
does not automatically have Docker control. Use a narrowly scoped host dispatcher
and a shared staged directory only after that route has been tested. Do not expose an
unauthenticated Docker API or mount the Docker socket into the research container.
The included shared-folder host bridge implements this route, but each installation
must prove the mounts, host worker, headless CLI, source access, and returned artifact
before claiming container-to-container delegation works there.
