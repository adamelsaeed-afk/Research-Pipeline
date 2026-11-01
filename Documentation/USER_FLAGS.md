# User flags

Started: 21 October 2026, Africa/Cairo. Scope: flags raised from this point in this
project conversation. Earlier findings remain in the 20 October audit under
test_reports/security_and_test_audit_2026-10-20/AUDIT.md; they are not automatically
new implementation requests.

Append subsequent user flags with their date, meaning and status. When the user asks
for the flags, report all recorded items and distinguish requirements, questions,
completed changes and unresolved decisions. A question or concern alone does not
authorize a redesign.

## F001 — Separate validation responsibilities inside the skill

- Date: 21 October 2026.
- User requirement: "it has to be separated in the skill itself not your wording."
- Meaning: distinguish the AI validator's substantive evidence checking from the
  dispatcher's deterministic response checks in the actual skill instructions.
- Status: clarified in SKILL.md, phase 3. The AI validator checks source access and
  factual support; the dispatcher checks response structure, locator syntax and ID
  coverage. Accepted JSON alone is insufficient to treat findings as validated.
- Boundary: documentation clarification only; no script behavior or live validation
  result changed. This is not proof that every model follows its instructions.

## F002 — Value and effort of adversarial testing

- Date: 21 October 2026.
- User concern: "since neither make sure no attack happens then the test is pointless
  no unless we test multiple scenarios and see which ones fail but that's tedious".
- Meaning: a single scenario supplies limited evidence; consider whether multiple
  scenarios can find useful failures without tedious manual work.
- Status: the subsequent six-fix authorization covered bounded automated testing.
  Four harmless instruction-manipulation fixtures now test deterministic data
  boundaries, with additional malformed-result/configuration tests. A limited live
  trial also rejected a benign instruction to approve without checking sources.
- Boundary: these tests detect known failures; they do not prove universal attack
  resistance. No dangerous payload, credential, upload or exploit was used. Broad
  security testing remains outside this focused batch.

## F003 — Clarify who checks source accessibility

- Date: 21 October 2026.
- User question: "how does the skill behave in validation the script validates that
  the sites work and the agent tasked with validation makes sure the findings are
  correct?"
- Current answer: the script checks locator syntax, not HTTP reachability. The AI
  validator opens the cited source and checks both accessibility and factual support,
  then reports gaps. Gap filling and a fresh validation pass follow material changes.
- Status: clarified in this conversation and in the F001 skill wording.
- Boundary: this question does not by itself request a separate HTTP-link checker.

## F004 — AI validation of gap corrections

- Date: 23 October 2026.
- User requirement: "He should also be an agent that checks that the fillings where
  correct just like the first validation phase".
- Meaning: revalidation is substantive AI source checking of the gap corrections
  and affected findings, using the initial validation's evidence standard.
- Status: made explicit in SKILL.md phase 3 and references/validation_protocol.md.
  External CLI mode uses a fresh validator process; same-session mode retains a
  separate AI review pass. A gap filler's completed response is not approval.
- Verification update: the authorized readiness batch subsequently ran an actual
  three-process Docker/OpenCode loop. The initial validator caught a false claim,
  the gap filler corrected it and a fresh validator read the official source and
  confirmed both corrected findings. This verifies the selected route in a bounded
  trial; other CLI routes and the validation-mode choice remain as documented.

## F005 — Six readiness fixes, security and no push

- Date: 23 October 2026.
- User requirement: fix the six proposed points, apply security best practices,
  record everything in the current implementation document and do not push until
  explicitly told.
- Status: implemented and verified. The six items and acceptance results are in
  V1.2_IMPLEMENTATION_PLAN.md; exact changes, security findings, tests and residual
  limits are recorded in V1.2_CHANGE_LOG.md. Windows/Ubuntu each ran 77 tests.
- Security boundary: no high/medium Bandit findings, six retained low findings,
  no known advisories for the six audited installed dependencies, and no matches
  in a limited source-text secret scan. The historical Snyk W011 indirect prompt
  injection warning was not rescanned or declared cleared. No zero-risk promise.
- Publication update, 23 October: the author subsequently authorized commit/push
  and confirmed inclusion of the required untracked code, tests and documentation,
  ignoring only local artifacts. The earlier push hold is superseded for the
  current branch. Installation sync, main-branch changes and release remain outside
  this request. The live trial kept OpenCode 1.18.35 with
  opencode/mimo-v2.6-flash-free.
