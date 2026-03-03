# pm-report

Generate evidence-based technical analysis reports for Product Management audiences.

## What It Does

Builds professional PDF reports with:
- Cover page, table of contents, section headers
- Coverage tables with colored status indicators (green/yellow/red)
- ASCII bar charts for visual comparison
- Score cards with pass/warn/fail indicators
- Evidence blocks showing API/CLI results with OK/GAP tags
- Screenshot embedding with captions
- Tiered recommendations (Tier 1/2/3 by business impact)
- Source documentation reference tables
- Metric blocks with value/target/status

## Install

```bash
claude plugin install pm-report@grobomo-marketplace --scope user
pip install reportlab
```

## Usage

Tell Claude what you want analyzed. The skill handles the rest:

```
"Generate a PM report on our API coverage gaps"
"Create a technical analysis report comparing Feature X across vendors"
"Build an executive report on our security posture"
```

Claude will:
1. Investigate the subject (API calls, doc reads, web searches)
2. Collect evidence (working vs broken, screenshots, metrics)
3. Rank findings by business impact
4. Generate PDF with proof embedded throughout
5. Output to `reports/` directory

## Report Formula

Every report follows this evidence-based structure:

```
Cover Page -> TOC -> Executive Summary -> Methodology ->
Coverage Overview -> Priority Findings -> Evidence ->
Screenshots -> Recommendations -> Bridge Table -> Sources
```

## Dependencies

- Python 3.8+
- reportlab (pip install reportlab)

## Project Structure

```
pm-report/
+-- SKILL.md              # Skill instructions (report formula + PM writing rules)
+-- generator.py           # PMReport class with fluent API
+-- templates/
    +-- __init__.py
    +-- styles.py          # Color palette + paragraph styles
    +-- cover.py           # Cover page, TOC, structural elements
    +-- evidence.py        # API evidence, screenshots, metrics
    +-- tables.py          # Coverage, comparison, bridge, source tables
    +-- charts.py          # Bar charts, score cards
    +-- recommendations.py # Tiered recs, action items, next steps
```

## Quick Test

```bash
python generator.py --demo
```

Generates an 8-page demo PDF with all components to verify the engine works.
