---
name: skill-creator
description: Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch, edit, or optimize an existing skill, run evals to test a skill, benchmark skill performance with variance analysis, or optimize a skill's description for better triggering accuracy.
---

# Skill Creator (Anthropic Official Agent Skill Reference)

> Source: https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md

A skill for creating new skills and iteratively improving them.

At a high level, the process of creating a skill goes like this:

- Decide what you want the skill to do and roughly how it should do it
- Write a draft of the skill
- Create a few test prompts and run claude-with-access-to-the-skill on them
- Help the user evaluate the results both qualitatively and quantitatively
  - While the runs happen in the background, draft some quantitative evals if there aren't any.
  - Use the `eval-viewer/generate_review.py` script to show the user the results for them to look at, and also let them look at the quantitative metrics
- Rewrite the skill based on feedback from the user's evaluation of the results (and also if there are any glaring flaws that become apparent from the quantitative benchmarks)
- Repeat until you're satisfied
- Expand the test set and try again at larger scale

## Creating a skill

### Capture Intent

Start by understanding the user's intent. The current conversation might already contain a workflow the user wants to capture (e.g., they say "turn this into a skill"). If so, extract answers from the conversation history first — the tools used, the sequence of steps, corrections the user made, input/output formats observed.

1. What should this skill enable Claude to do?
2. When should this skill trigger? (what user phrases/contexts)
3. What's the expected output format?
4. Should we set up test cases to verify the skill works? Skills with objectively verifiable outputs (file transforms, data extraction, code generation, fixed workflow steps) benefit from test cases. Skills with subjective outputs (writing style, art) often don't need them.

### Write the SKILL.md

Based on the user interview, fill in these components:

- **name**: Skill identifier (lowercase letters, numbers, hyphens)
- **description**: When to trigger, what it does. This is the primary triggering mechanism - include both what the skill does AND specific contexts for when to use it. All "when to use" info goes here, not in the body. Note: currently Claude has a tendency to "undertrigger" skills -- to not use them when they'd be useful. To combat this, please make the skill descriptions a little bit "pushy".
- **compatibility**: Required tools, dependencies (optional, rarely needed)

## Skill Writing Guide

### Anatomy of a Skill

```text
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

### Progressive Disclosure

Skills use a three-level loading system:
1. **Metadata** (`name` + `description`) - Always in context (~100 words)
2. **SKILL.md body** - In context whenever skill triggers (<500 lines ideal)
3. **Bundled resources** - As needed (unlimited, scripts can execute without loading their source into context)

**Key patterns:**
- Keep `SKILL.md` under 500 lines; if you're approaching this limit, add an additional layer of hierarchy along with clear pointers about where the model using the skill should go next to follow up.
- Reference files clearly from `SKILL.md` with guidance on when to read them.
- For large reference files (>300 lines), include a table of contents.

**Domain organization**: When a skill supports multiple domains/frameworks, organize by variant:
```text
cloud-deploy/
├── SKILL.md (workflow + selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```
Claude reads only the relevant reference file.

### Writing Style & Theory of Mind

1. **Generalize from the feedback**: Create skills that can be used across many different prompts rather than overfitting to 2-3 test examples.
2. **Keep the prompt lean**: Remove things that aren't pulling their weight. Read the execution transcripts, not just the final outputs — if the skill makes the model waste time on unproductive steps, prune those instructions.
3. **Explain the why**: Explain the reasoning behind what you're asking the model to do so the model can generalize intelligently across edge cases.
4. **Look for repeated work across test cases**: If subagents across multiple test runs independently write similar helper scripts (e.g., `create_docx.py` or `build_chart.py`), bundle that script once in `scripts/` and instruct `SKILL.md` to invoke it.

## Running and Evaluating Test Cases

- **Step 1: Spawn parallel runs (with-skill AND baseline) in the same turn**: Compare `with_skill` against `without_skill` (for new skills) or `old_skill` snapshot (when upgrading an existing skill).
- **Step 2: Draft quantitative assertions (`evals.json`)**: Assertions should be objectively verifiable (`text`, `passed`, `evidence`).
- **Step 3: Capture timing and token usage (`timing.json`)**: Record `total_tokens` and `duration_ms` to analyze cost/latency trade-offs alongside quality.
- **Step 4: Grade, aggregate (`benchmark.json`), and analyze**: Surface non-discriminating assertions, high-variance flaky evals, and token/time regressions.
- **Step 5: Description Optimization (Trigger Eval Set)**: Build 20 realistic queries (8-10 `should_trigger: true` with diverse/casual phrasing + 8-10 `should_trigger: false` near-miss queries in adjacent domains) to optimize the frontmatter `description` for precision and recall.
