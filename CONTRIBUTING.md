# Contributing to ENCODE MCP Connector

Thank you for your interest in contributing to the ENCODE MCP Connector! This guide covers how to add new skills, improve existing ones, and submit changes.

## Skill Architecture

Each skill lives in `skills/{skill-name}/` with this structure:

```
skills/my-skill/
├── SKILL.md              # Required: Main skill file
├── references/           # Optional: Supplementary docs loaded on demand
│   └── detailed-guide.md
├── scripts/              # Optional: Executable code
│   └── validate.py
└── assets/               # Optional: Templates, configs
```

## SKILL.md Template

Every skill MUST include these sections:

```yaml
---
name: skill-name
description: >-
  One paragraph describing when this skill triggers and what it does.
  Include specific keywords that should activate this skill.
---
```

### Required Sections

1. **Overview** -- What the skill does and when to use it
2. **Key Literature** -- At least 2 peer-reviewed papers with DOIs and citation counts
3. **Workflow / Steps** -- Numbered steps with tool calls and parameters
4. **Code Examples** -- At least 1 complete workflow example
5. **Pitfalls & Edge Cases** -- At least 3 common mistakes with solutions
6. **Presenting Results** -- How to format and present outputs to the user
7. **Related Skills** -- Table linking to complementary skills
8. **$ARGUMENTS** -- Footer declaring skill arguments

### Literature Requirements

Every skill that provides scientific guidance MUST cite peer-reviewed literature:

- Include DOI for every citation
- Prefer papers with >100 citations for core methodology
- Include citation count as a credibility signal
- Use format: `Author et al., Year (Journal, ~N citations)`
- Reference ENCODE consortium papers where applicable

### Quality Standards

- Every workflow step must specify which MCP tool to use
- Code examples must be copy-pasteable (no pseudocode)
- Pitfalls must include the solution, not just the problem
- Presenting Results must specify format (table, list, narrative)
- Related Skills table must link to at least 3 other skills

## Adding External Database Skills

When adding a skill for an external database (GTEx, ClinVar, GWAS Catalog, etc.):

1. Use the database's public REST API -- no authentication required
2. Show how to cross-reference with ENCODE data
3. Include the database's canonical citation
4. Explain what biological question the integration answers
5. Add the skill to cross-reference Related Skills table

## Adding Pipeline Skills

Pipeline skills are children of `pipeline-guide` (the parent):

1. Create `skills/pipeline-{assay}/` with SKILL.md + references/ + scripts/
2. Include Nextflow DSL2 pipeline in `scripts/main.nf`
3. Include Dockerfile in `scripts/Dockerfile`
4. Include `scripts/nextflow.config` with local/slurm/gcp/aws profiles
5. Break stages into reference files (01-qc-trimming.md, 02-alignment.md, etc.)
6. Update the parent `pipeline-guide/SKILL.md` to reference the new child

## Code Style

- Python: Follow PEP 8, use type hints
- Nextflow: DSL2, one process per stage
- R: tidyverse style
- Bash: Use set -euo pipefail

## Pull Request Process

1. Create a feature branch: `git checkout -b add-{skill-name}`
2. Run verification: `python -m encode_connector.server.main` (must start)
3. Check skill completeness: all required sections present
4. Update CLAUDE.md skill count and table
5. Update CHANGELOG.md with your additions
6. Submit PR with description of what the skill enables

## Testing

- Verify the MCP server starts: `python -m encode_connector.server.main`
- Verify skill has all required sections
- Verify code examples reference correct tool names
- Verify literature citations have DOIs
- For pipeline skills: verify Nextflow syntax with `nextflow -version`

## Questions?

Open an issue or reach out to the maintainers.
