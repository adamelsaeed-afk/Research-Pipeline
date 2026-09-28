<!--
================================================================================
TEMPLATE: Comprehensive Research Report (feature analysis)

AGENT INSTRUCTIONS — remove this comment block and every per-section HTML comment
(whole blocks between comment markers) as you fill the template:

1. Copy this file to scratch/draft_report.md and fill every section, replacing
   every [placeholder] with real content. Do not ship brackets.
2. Apply the ADAPTATION TABLE below for the selected mode/sub-type BEFORE
   filling: skip, add, or rename sections as instructed, and record what you
   adapted in the Methodology section.
3. Apply ALL report content rules from SKILL.md while filling:
   - No vendor/marketing language — neutral, standardized descriptions only.
   - Frequency-backed standards — an adoption count for every standard claim.
   - Feature-first organization — features first, vendors second.
   - Structured pricing — comparable tables, normalized units.
   - Abbreviations — expand on first use as Full Name (ABBREVIATION); the
     Executive Summary is the report's first text, so start there.
4. Before submitting for review (Phase F): all applicable sections present,
   adoption counts match the Entity Coverage Matrix, no marketing language,
   every claim traceable to the References section.
================================================================================
-->

<!-- ADAPTATION TABLE — how to use this template per mode/sub-type:

| Mode / Sub-Type                                  | How to adapt                                                                              |
|--------------------------------------------------|-------------------------------------------------------------------------------------------|
| Market — Feature Research                        | Use as written (this template's native shape)                                             |
| Market — Competitive Analysis                    | Use as written; a Positioning summary may be added under Differentiating Features          |
| Market — Gap Analysis                            | Use as written, with Gaps & Opportunities as the core section — evidence per gap           |
| Market — Market Sizing / TAM                     | SKIP: Entity Coverage Matrix, Feature-by-Feature Deep Dive, Differentiating Features.      |
|                                                  | ADD: Market Size & Growth (TAM/SAM/SOM), Segmentation, Key Market Drivers.                 |
|                                                  | Pricing Comparison only if vendor pricing is in scope.                                     |
| Technical — tool/framework evaluation            | Use coverage-matrix sections when comparing discrete options; skip them for                |
|                                                  | single-technology deep-dives                                                              |
| Technical — architecture / how-it-works dive     | SKIP vendor-dimension sections (Coverage Matrix, Pricing Comparison, Differentiating       |
|                                                  | Features); organize the deep dive by technical topic instead of by feature                 |

The Simple template (templates/simple.md) applies to any mode when the user selects it.
-->

# [Research Title]

## Executive Summary

<!-- 2-3 paragraphs: overview of key findings, the major standards identified
(with their adoption counts), and notable gaps or opportunities. Neutral
language only. Expand abbreviations here on first use — Full Name (ABBREVIATION).
-->

[2-3 paragraph overview of key findings, major standards identified, and notable gaps]

## Methodology

<!-- State each item below. The thresholds are the defaults; use the user's
adjusted values if they overrode them at intake. The adaptations line is
mandatory: state which sections you skipped, added, or renamed per the
adaptation table, and why — or state "None; used as written".
-->

- Sources searched: [list the source types and key sites consulted]
- Time scope: [e.g., last 2 years]
- Geographic scope: [e.g., global]
- Entities analyzed: [count]: [Entity A], [Entity B], [Entity C]
- Classification thresholds: Universal (70%+), Emerging (30-69%), Differentiator (<30%)
- Template adaptations applied: [state sections added/skipped/renamed and why]

## Market Standards

### Universal Standards (70%+ adoption)

<!-- For each feature: a neutral description of what it does, the adoption count
(X/Y entities, percentage), and which entities offer it. Include only features
meeting the Universal threshold. Frequency-backed claims rule applies: no
"standard" claim without a count.
-->

### [Feature Name]

[Neutral description of what the feature does.]

- **Adoption**: X/Y entities (Z%)
- **Offered by**: [Entity A], [Entity B], [Entity C]

### Emerging Standards (30-69% adoption)

<!-- Same format as Universal Standards, for features meeting the Emerging
threshold.
-->

### [Feature Name]

[Neutral description of what the feature does.]

- **Adoption**: X/Y entities (Z%)
- **Offered by**: [Entity A], [Entity B]

## Category-Specific Standards *(optional — include only if the user requested a category breakdown at intake; delete this entire section otherwise)*

<!-- Standards specific to one product category (e.g., a CLM-specific or
LMS-specific standard set), using the same format as Market Standards. If the
research spans multiple product categories and the user asked for a breakdown,
repeat this section per category.
-->

### [Category Name] Standards

[Standards specific to this product category, same format as Market Standards.]

## Differentiating Features (<30% adoption)

<!-- Features that set specific entities apart. Attribute each feature to the
entity that offers it. Neutral descriptions — state what the feature does, not
how the vendor markets it.
-->

### [Feature Name] — [Entity Name]

[Neutral description of the feature, how it differs from the standard set, and
which entity offers it.]

## Feature-by-Feature Deep Dive

<!-- One subsection per feature catalogued in Market Standards and Differentiating
Features. Describe implementations per entity neutrally: what it does and how,
not promotional claims.
-->

### [Feature Name]

- **Description**: [Neutral, standardized description]
- **Adoption**: X/Y entities (percentage%)
- **Implementation Variations**:
  - [Entity A]: [How they implement it]
  - [Entity B]: [How they implement it]

## Entity Coverage Matrix

<!-- One row per feature; one column per entity (from intake, Question 3).
Mark each cell with ✓ (offered) or ✗ (not offered), or a short qualifier such as
"partial". The counts stated in the text MUST match this matrix.
-->

| Feature | [Entity A] | [Entity B] | [Entity C] |
|---------|------------|------------|------------|
| [Feature 1] | ✓ | ✗ | ✓ |
| [Feature 2] | ✗ | ✓ | ✓ |

## Pricing Comparison

<!-- Normalize every price to the same unit (e.g., per user/month) and mark
"Custom quote" where pricing is not publicly listed. Pricing is volatile data:
cite the source and note when each figure was verified (the time scope from
intake applies).
-->

| Entity | Model | [Basic tier] | [Pro tier] | [Enterprise] |
|--------|-------|--------------|------------|--------------|
| [Entity A] | Per user/month | $X | $Y | Custom quote |
| [Entity B] | Credits/month | $X (N credits) | $Y (N credits) | Custom quote |

## Gaps & Opportunities

<!-- Features missing from most or all entities, unmet needs, and market white
spaces. Ground every gap in the coverage matrix or validated findings — no
speculation without evidence.
-->

[Features missing from most entities, unmet needs, market white spaces]

## References

<!-- All source URLs, grouped by entity or by topic. Every claim in the report
must trace to at least one reference here. Give each source a short neutral
description.
-->

### [Entity or Topic]

- [Short neutral source description]: [URL]
