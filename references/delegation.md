# External research delegation

The originating agent owns the brief, the plan, every checkpoint, and the report. Four
delegated roles run through the dispatcher: the researcher (only when the confirmed research
mode is `delegated`), the validator, the gap filler, and the revalidator — a fresh validation
pass over corrected findings that by default reuses the confirmed validator routing. Each
dispatch starts a fresh `agy`, `opencode`, or `codex` CLI process; no resume or
continuation option is used. Each pass uses a separate run; prefer a different product for
validation when configured.

## Before dispatch

During intake, inspect the active environment before asserting that a CLI is present
or absent. An unchecked route is unknown; finding an executable is only discovery.
Complete the following usability checks after the user selects external validation.

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

Configuration is executable authority: its executable paths and container settings
must be reviewed by the host operator and kept outside directories writable by
untrusted participants. The declared CLI name does not authenticate an executable.
Native programs are required; implicit `.cmd`, `.bat`, `.ps1` and `.sh` launchers
are rejected. On Windows, configure the installed native CLI binary when a PATH
entry is only a batch shim. Container names and mount paths must be ordinary values,
not option switches. Source text is never evaluated as command text.

Child processes receive runtime paths, locale, proxy/certificate and Docker settings
from a restricted environment. Required additional authentication variable **names**
can be listed in a target's `environment_allowlist`, for example
`["OPENAI_API_KEY"]`; values stay in the host environment and are not written into
configuration or prompts. Startup-code hooks such as `NODE_OPTIONS`, `PYTHONPATH`
and `LD_PRELOAD` are rejected. Existing CLI credential stores remain governed by
their own permissions. This minimizes inherited variables; it is not a file sandbox.

Contract JSON, brief/input text and parsed streams are bounded to 4 MiB. JSON rejects
duplicate members, nonfinite numbers and nesting deeper than 64 levels. Raw streams are
retained on disk, so provide a bounded workspace/quota when the CLI itself is not
trusted. POSIX run directories use mode 0700; Windows uses inherited host ACLs.
Logs and research artifacts may contain private research content: keep their parent
directories private and share only reviewed material. Never stage credentials.

## Dispatch contract

Run from the project skill directory:

```text
python scripts/research_dispatch.py --config <local-config.json> --record <intake.json> --brief <research_brief.md> --role validate --target <target-name> --input <raw_findings.md> --run-dir <run-directory>
python scripts/research_dispatch.py --config <local-config.json> --record <intake.json> --brief <research_brief.md> --role gap_fill --target <target-name> --input <gap_report.md> --run-dir <run-directory>
```

The intake checker runs again on each dispatch. A new directory contains the
brief, role input, prompt and input ID inventory bound to the staged input's SHA-256.
Roles are `validate`, `gap_fill`, `revalidate` (a validation pass over corrected
findings; input `findings.md`), and `research` (only with confirmed research mode
`delegated`; input `questions.md` carrying question IDs). A research result accounts for
every question through findings or explicit unanswered entries, and its findings require
validation before use.
Legacy ID headings such as `## C1 Finding` or records such as `G1: Verify the claim`
work directly. References in prose, tables and fenced examples do not create IDs.
For other layouts, add `--input-ids <ids.json>` with a nonempty JSON string list of
every material claim or gap ID. Each ID must label a record: a heading, an `ID:`
record (optionally bulleted), a standalone ID line, or the first cell of a table row. Fenced/inline code,
HTML comments, block quotes and prose references cannot establish ID presence.
The list must be unique and include recognized records. Ambiguous input without this list fails before
launching a CLI. The agent must still identify every material statement.

The CLI returns one complete top-level JSON object. Plain narration may precede a
standalone final object, but no text may follow it. Quoted/fenced examples, nested
results, arrays and incomplete JSON wrappers are rejected; the parser never searches
inside them for an approval. Supported CLI transport envelopes are decoded separately.
The dispatcher requires a matching role, typed
fields, valid source locators and coverage of supplied IDs, then saves
`result.json`, `stdout.txt`, `stderr.txt`, and `dispatch.json`. Failed, timed out,
empty, and malformed runs do not count as validation. The research agent reviews
the artifact and makes the final evidence judgment.

The dispatcher preserves the result path on stdout. Exit 0 means an approving
validation or gap completion without unresolved entries; gap completion still needs
fresh validation. Exit 3 means a valid role response needs attention (`blocked`,
`gaps_found`, or completed gap filling with unresolved items). Exit 2 is an execution
or contract failure; exit 130 is cancellation. Dispatch metadata includes
`role_verdict`, `requires_attention`, `unaccounted_input_ids` and a `user_notice`;
stderr prints the notice.
Relay attention notices to the user before advancing the checkpoint. They are
caller-visible feedback, not a standalone notification service.

Every dispatch appends two lines to the run ledger (`--ledger`, defaulting beside the run
directories): a launch line (role, target, model, staged input bytes, timeout) and a complete
line (exit code, verdict, duration, tokens the CLI actually printed). Approved run counts
(`approved_run_counts`) and parallel-launch caps (`approved_concurrency`) are intake decisions
checked before staging: a dispatch beyond an approved count or cap is refused with the count
named and the required user evidence — never queued. A crashed dispatch's parallel slot is
reclaimed automatically; failed runs count toward limits; a retry is a new run. Synthetic
intake fixtures and schema-mapping wrappers that make a checker accept an unconfirmed
arrangement are contract violations, not implementation choices: if the record cannot
honestly support a dispatch, obtain the user decision that makes it honest.

Mailbox receipts retain execution `status` and add the same role feedback; updated
waiting Python and shell clients return 3 for attention. A completed receipt alone
never establishes approval. The source probe is stricter: it needs a fully confirmed
check of its expected public source or a resolved, cited gap correction. Inspect its
tool logs independently; an accepted response cannot prove an actual source read.

The validator result has `role: "validate"`, `verdict` of `approved`,
`approved_with_limits`, `gaps_found`, or `blocked`, a `summary`, `issues`,
`checked_claim_ids`, and source `checks`. `approved_with_limits` requires a
`limitations` list of `{claim_id, reason}` for each partial or unverifiable check;
it is only for nonmaterial uncertainty, never a mismatch or material gap. Each check
names the claim, source locator, brief source-grounded evidence, and a verdict. Each
issue requires `{id, claim_id, problem, evidence_urls, severity}`: a stable gap ID,
an ID from the supplied claims, a precise problem, a list of evidence locators, and
severity of `material` or `nonmaterial`. A material issue can change a finding or
its interpretation; a nonmaterial issue affects a minor qualifier. Any open issue
still uses `gaps_found`; severity never bypasses revalidation. The gap-filler result has
`role: "gap_fill"`, `verdict` of `completed` or `blocked`, `summary`, `changes`, and
`unresolved`. Each change names the gap ID, corrected finding, and source URLs.

Source fields retain their names (`source_url`, `source_urls`, `evidence_urls`) and
accept HTTP(S) URLs or supplied document file locators (whole files or with a
page/section), such as `Policy.pdf`, `Policy.pdf#page=7`, or `capture.html#FAQ`.
Named references also work as `document:Policy#section=Retention`. This syntax check does
not prove access, accuracy or authenticity. Missing evidence remains explicit;
an issue's evidence list may be empty when access failed.

Approval requires every expected claim ID with evidence checks, without unknown or
duplicate checked IDs. Multiple sources for one claim remain valid. A `blocked` or
`gaps_found` result can cover a subset; dispatch metadata lists unaccounted IDs.
If an authentication, tool or access problem prevents all checks, a validator may
return `blocked` with `checked_claim_ids: []`, `checks: []`, and an explanatory
nonempty summary. Use `issues: []` for a run-wide blocker; do not invent checks.
Every supplied claim remains unaccounted for. Other verdicts cannot use zero checks.
This is a nonapproval result. The summary is a model assertion, not proof of tool
failure: inspect retained streams for supporting evidence before accepting the
explanation. An unsupported blockage requires investigation, never skipped claims.
Completed gap filling must account for each supplied gap through a correction,
an unresolved reason or both. Unknown gaps and within-list duplicates fail. A
correction and residual uncertainty for the same gap remain valid. Completion
does not approve the corrected research; a fresh validator does that.

After material changes, dispatch a new validator run using the updated findings.
Continue while evidence progress is possible. Record unresolved source limitations
and conflicting claims explicitly. Ask the user for a choice if the treatment would
change the agreed scope. An unavailable CLI stops this delegated route; changing CLI,
transport, or validation mode requires a new user choice.

## Recovering work from disk artifacts

Everything a dispatch needs lives in its run directory: `brief.md`, the staged
input, `prompt.txt`, `dispatch.json`, `stdout.txt`, `stderr.txt`, and
`result.json` when the contract passed. The ledger and in-flight registry sit
beside the run directories. When a run dies — coordinator restart, timeout,
crash — recover from these artifacts, in this order:

1. Derive the run states from the ledger and registry: completed runs keep
   their verdicts; failed runs keep their retained streams; orphaned runs (a
   launch without a complete line) are the recovery targets.
2. For an orphaned run, read the retained `stdout.txt`/`stderr.txt` for
   partial output. A final role JSON can exist in the stream even when
   `result.json` is absent; the contract parser can be applied to the
   retained stream without relaunching the CLI.
3. For checkpoint exports from a long interactive session, resume from the
   newest complete export file. Exports are snapshots of another program's
   state with truncation risk — evidence to review, never a completeness
   guarantee.
4. Record recovered material as a new ledger event; never rewrite history.
   A retry is a new run and consumes budget like any other.

Never read a CLI application's internal store (its conversation database,
SQLite or protobuf files) to recover work. That is an unusual method requiring
the user's explicit approval before it runs, with its scope and exclusions
stated first; read-only mode reduces mutation risk but does not make the
method routine. Artifact-only recovery is the standard, and the database was
only ever the fallback when no artifacts existed.

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

Mailbox clients attach an absolute expiry of submission time plus the role timeout
and 30 seconds. Expired queued work returns `expired` without launching a CLI;
execution is also bounded by the remaining deadline. Legacy queued requests without
an expiry are rejected and need explicit resubmission with the updated client.
Only one worker may own a shared root. After a crash, its replacement marks stranded
`.processing` requests `interrupted`, retains them as `.interrupted`, preserves any
already-written response, and does not replay them. Inspect the saved run and logs
before deciding whether to submit a new job.
