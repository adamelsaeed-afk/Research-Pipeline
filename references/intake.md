# Research interview and intake record

The interview is a branching decision tree, not a fixed number of questions. Start
with what the user already said. Ask the smallest group of unanswered questions that
can determine the next branch. Summarize interpretations that would change the
research and ask the user to correct them. Repeat until the research can be described
without meaningful ambiguity.

## Decision map

Always resolve research type, exact questions, targets or inclusion criteria,
geography, time and evidence period, depth, report format, known source leads (including
an explicit “none”), review granularity, and validation mode. Market research also
needs its subtype. Follow relevant branches:

- Comparisons: population, categories, inclusion and exclusion rules, comparison
  dimensions, and how to treat undocumented capabilities.
- When comparison eligibility requires a named customer deployment, resolve the
  minimum acceptable evidence. Ask whether a public participant testimonial that a
  product was brought into a named team qualifies, and whether rollout or continued
  use must be documented. Record the answer as a branch decision; label weaker
  qualifying evidence in the brief and report rather than silently equating it with
  a detailed deployment case study.
- Feature frequency: feature definitions, denominator, categories, and thresholds.
- Market sizing: segment definition, geography, base year, currency, sizing measure,
  and acceptable estimation assumptions.
- Technical research: target versions, deployment environment, performance or
  compatibility criteria, and any required evaluation conditions.
- External CLI validation: target CLI for validation, target CLI for gap filling,
  configured transport, and OpenCode provider/model when selected. These are
  operational choices; they never appear in the management report.

## Derive task-specific branches

Use the user's research question, intended use of the findings, and constraints to
identify additional decisions. The decision map is a starting point. For each
plausible ambiguity, ask whether different answers would change the subjects included,
counting units, evidence standard, comparison criteria, or report coverage. Ask a
follow-up only when that difference matters and the user has not already resolved it.
Derive branches from the current request; each question needs a specific relevance
to that request.

Distinguish choices and context the user must supply from facts the agent should
research. Ask the user to settle their requirements and scope. Carry unanswered
questions about the subjects' capabilities or behavior into the research brief for
investigation; the user need not supply the findings. If the user cannot provide a
relevant detail about their own context, confirm how to treat that unknown before
proceeding, such as researching alternatives or stating a limit.

Before presenting the brief, review its scope for materially different plausible
interpretations. Resolve those that would change the research and record the
resulting branch decisions. This review is necessary even when the recorded fields
are complete: the checker cannot discover a branch the interviewer never records.

Other answers may create new branches. Add each to `required_branches` and
`decisions`. A branch is `not_applicable` only with an explicit reason. When a user
says “you decide,” propose a concrete answer and get their confirmation. If a term
remains vague, ask again. Do not use silence to accept a default.

## Complete brief

Write a concise `research_brief.md` with the research questions, subjects and
inclusion rules, geography, period, depth, requested comparison or sizing dimensions,
exclusions, report structure, validation arrangement, and any relevant branch choices.
Show it to the user and ask for explicit confirmation. Record confirmation of this
exact version by storing its SHA-256 digest in `intake.json`. If the brief changes,
confirmation becomes invalid and must be renewed.

Example record shape (the digest below is a placeholder):

```json
{
  "required_branches": ["feature_definition", "comparison_denominator"],
  "open_branches": [],
  "decisions": {
    "research_type": {"state": "answered", "answer": "market"},
    "market_subtype": {"state": "answered", "answer": "feature_research"},
    "research_questions": {"state": "answered", "answer": "Which capabilities are documented?"},
    "targets": {"state": "answered", "answer": "Products matching the agreed inclusion rule"},
    "geography": {"state": "answered", "answer": "Global"},
    "time_scope": {"state": "answered", "answer": "Current as of the report date"},
    "depth": {"state": "answered", "answer": "Detailed"},
    "report_format": {"state": "answered", "answer": "Comprehensive Markdown"},
    "source_leads": {"state": "answered", "answer": "none"},
    "review_granularity": {"state": "answered", "answer": "Major checkpoints"},
    "validation_mode": {"state": "answered", "answer": "same_session"},
    "feature_definition": {"state": "answered", "answer": "Documented end-user capability"},
    "comparison_denominator": {"state": "answered", "answer": "Eligible products in the agreed sample"}
  },
  "confirmation": {"confirmed": true, "brief_sha256": "<sha256-of-exact-brief-file>"}
}
```

When `validation_mode` is `external_cli`, also resolve `validator_cli`,
`gap_filler_cli`, `validator_transport`, `gap_filler_transport`, `validator_model`,
and `gap_filler_model`. Their CLI answers must match configured dispatcher target
names. When a model is configured, its recorded answer must exactly match the
configured model ID; keep annotations in a separate note. A model decision may be
`not_applicable` with a reason when the installed
CLI's default model is acceptable; OpenCode needs an explicit provider/model. Run
`scripts/check_intake.py` before any search-plan or research phase. The
checker catches missing states and confirmation; the interviewing agent must still
notice unstated branches and contradictory meanings.
