# Research Pipeline

A structured, multi-agent research skill for agent Command-Line Interfaces (CLIs).
It guides an agent through a complete research pipeline — structured intake, search
planning, multi-phase validation, and report compilation — and exports the final
report to Word. Use cases range from tool comparisons and competitive analysis to
Artificial Intelligence (AI) feature research.

Two research modes are supported through a mode switch at intake:

- **Technical research** — evaluating tools, frameworks, Application Programming
  Interfaces (APIs), architectures, and developer ecosystems.
- **Market research** — four sub-types: Gap Analysis, Competitive Analysis, Feature
  Research, and market sizing (Total Addressable Market, TAM).

Every report is compiled under strict content rules: no vendor or marketing language,
frequency-backed standards (each "standard" claim carries an adoption count across the
analyzed entities, e.g. "Automated Status Reporting: 3/4 tools (75%)"), feature-first
organization, a features-by-vendors coverage matrix, structured pricing comparison,
and abbreviations expanded on first use.

## What the pipeline looks like

1. **Activation gate** — when a research request triggers the skill, the agent first
   asks whether you want the structured pipeline or a direct answer. Declining means
   the agent simply answers normally; simple questions never enter the pipeline.
2. **Intake** — ten structured questions: research type, sub-type, targets, geography,
   time scope, depth and review granularity, report template, specific questions,
   known sources, and how validation should run.
3. **Search plan** — the agent presents keywords, sources, and strategy for your
   approval before searching anything.
4. **Research** — findings gathered with a source URL for every claim.
5. **Validation** — five sequential phases: link accessibility, content accuracy,
   recency, cross-reference and completeness, and source quality. You choose how often
   the agent pauses for your review.
6. **Gap filling** — an iterative loop that fixes what validation flagged, capped at
   three iterations before escalating to you.
7. **Report and export** — the report is compiled into your chosen template, reviewed,
   and exported to Word only after your explicit approval.

## Requirements

| Component | Requirement |
|-----------|-------------|
| Core skill | Any agent CLI that supports the skills format (Claude Code, Antigravity, Codex, Gemini CLI, and others) |
| Word export | [uv](https://docs.astral.sh/uv/) — the export script's Python dependencies install automatically on first run |
| Fresh-session validation *(optional)* | [delegate-skills](https://github.com/amElnagdy/delegate-skills) plus a second agent CLI **with web access**, Node 18+, and git |

Fresh-session validation is **optional**. By default the skill validates in-session:
the same agent runs role-isolated validation passes that read only the findings file
and its cited sources, with no extra setup. Use delegation when you want validation to
run in a completely separate agent session.

## Installation

Install with the Skills CLI:

```bash
npx skills add adamelsaeed-afk/Research-Pipeline
```

Or install manually: clone this repository and copy it into your agent CLI's skills
directory (each CLI keeps skills in its own location — see your CLI's documentation).

For optional fresh-session validation, also install the delegate-skills package the
same way:

```bash
npx skills add amElnagdy/delegate-skills
```

## Quick start

Trigger the skill with a research request, for example:

> Do a feature research on AI features in CRM systems — compare Salesforce, HubSpot,
> and Zoho

The agent will ask whether to run the structured pipeline, then walk through the
intake questions one at a time. After you approve the search plan, it researches,
validates, and compiles the report. When you approve the final report, export it to
Word:

```bash
uv run scripts/export_to_word.py --input report.md --output report.docx --template corporate
```

Three Word style templates are available: `corporate`, `academic`, and `minimal`.

## Repository structure

```
├── SKILL.md                    # The skill — the file your CLI reads
├── README.md
├── LICENSE
├── scripts/
│   └── export_to_word.py       # Markdown → Word export with three style templates
├── references/
│   └── validation_protocol.md  # Detailed five-phase validation procedure
├── templates/
│   ├── comprehensive.md        # Feature-analysis report template
│   ├── simple.md               # Simple report template
│   └── word/                   # corporate / academic / minimal style modules
└── examples/
    ├── sample_research.md      # Complete sample report (fictional entities)
    └── sample_research.docx    # The sample exported to Word (corporate style)
```

See [SKILL.md](SKILL.md) for the full skill specification, and
[references/validation_protocol.md](references/validation_protocol.md) for the
validation procedure in detail.

## License

Released under the [MIT License](LICENSE).
