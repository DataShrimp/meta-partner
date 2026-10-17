# Prompt Templates Reference

Full template library for Prompt Master. Read the relevant template when the user's task type matches. Do not load all templates at once — only the one you need.

## Table of Contents

| Template | Best For |
| :--- | :--- |
| A — RTF | Simple one-shot tasks |
| B — CO-STAR | Professional documents, business writing |
| C — RISEN | Complex multi-step projects |
| D — CRISPE | Creative work, brand voice |
| E — Auditable Reasoning | Logic, math, analysis, debugging |
| F — Few-Shot | Consistent structured output, pattern replication |
| G — File-Scope | Cursor, Windsurf, Copilot — code editing AI |
| H — ReAct + Stop Conditions | Claude Code, Devin — autonomous agents |
| I — Visual Descriptor | Midjourney, DALL-E, Stable Diffusion, Sora |
| J — Reference Image Editing | Editing an existing image with a reference |
| K — ComfyUI | ComfyUI node-based image workflows |
| L — Prompt Decompiler | Breaking down, adapting, or splitting existing prompts |
| M — Current Claude Task Brief | Complex, multi-step, or agentic task on current Claude models |

---

## Template A — RTF

Role, Task, Format. Use for fast one-shot tasks where the request is clear and simple.

```text
Role: [One sentence defining who the AI is]
Task: [Precise verb + what to produce]
Format: [Exact output format and length]
```

## Template B — CO-STAR

Context, Objective, Style, Tone, Audience, Response. Use for professional documents, business writing, reports, and marketing content where full context control matters.

```text
Context: [Background the AI needs to understand the situation]
Objective: [Exact goal — what success looks like]
Style: [Writing style: formal / conversational / technical / narrative]
Tone: [Emotional register: authoritative / empathetic / urgent / neutral]
Audience: [Who reads this — their knowledge level and expectations]
Response: [Format, length, and structure of the output]
```

## Template C — RISEN

Role, Instructions, Steps, End Goal, Narrowing. Use for complex projects, multi-step tasks, and any output that requires a clear sequence of actions.

```text
Role: [Expert identity the AI should adopt]
Instructions: [Overall task in plain terms]
Steps:
1. [First action]
2. [Second action]
3. [Continue as needed]
End Goal: [What the final output must achieve]
Narrowing: [Constraints, scope limits, what to exclude]
```

## Template D — CRISPE

Capacity, Role, Insight, Statement, Personality, Experiment. Use for creative work, brand voice writing, and any task where personality, tone, and iteration matter.

```text
Capacity: [What capability or expertise the AI should have]
Role: [Specific persona to adopt]
Insight: [Key background insight that shapes the response]
Statement: [The core task or question]
Personality: [Tone and style — witty / authoritative / casual / sharp]
Experiment: [Request variants or alternatives to explore]
```

## Template E — Auditable Reasoning

Use for logic-heavy tasks, math, debugging, and multi-factor analysis where the result must be checkable without requesting private reasoning.

```text
[Task statement]

Return:
1. Conclusion
2. Assumptions
3. Evidence or intermediate results needed to audit the conclusion
4. Verification checks performed
5. Remaining uncertainty, if any

Do not reveal hidden chain-of-thought or private reasoning. Keep the rationale concise and decision-relevant.
```

## Template F — Few-Shot

Use when the output format is easier to show than describe. Examples outperform written instructions for format-sensitive tasks every time.

```xml
[Task instruction]

Here are examples of the exact format needed:
<examples>
  <example>
    <input>[example input 1]</input>
    <output>[example output 1]</output>
  </example>
  <example>
    <input>[example input 2]</input>
    <output>[example output 2]</output>
  </example>
</examples>

Now apply this exact pattern to: [actual input]
```

## Template G — File-Scope

Use for Cursor, Windsurf, GitHub Copilot, and any AI that edits code inside a codebase.

```text
File: [exact/path/to/file.ext]
Function/Component: [exact name]
Current Behavior: [What this code does right now — be specific]
Desired Change: [What it should do after the edit — be specific]
Scope: Only modify [function / component / section]. Do NOT touch: [list everything to leave unchanged]
Constraints:
- Language/framework: [specify version]
- Do not add dependencies not in [package.json / requirements.txt]
- Preserve existing [type signatures / API contracts / variable names]
Done When: [Exact condition that confirms the change worked correctly]
```

## Template H — ReAct + Stop Conditions

Use for Claude Code, Devin, AutoGPT, and any AI that takes autonomous actions.

```text
Objective: [Single, unambiguous goal in one sentence]
Starting State: [Current file structure / codebase state / environment]
Target State: [What should exist when the agent is done]
Allowed Actions:
- [Specific action the agent may take]
- Install only packages listed in [requirements.txt / package.json]
Forbidden Actions:
- Do NOT modify files outside [directory/scope]
- Do NOT run the dev server or deploy
- Do NOT push to git
- Do NOT delete files without showing a diff first
- Do NOT make architecture decisions without human approval
Stop Conditions: Pause and ask for human review when:
- A file would be permanently deleted
- A new external service or API needs to be integrated
- Two valid implementation paths exist and the choice affects architecture
- An error cannot be resolved in 2 attempts
- The task requires changes outside the stated scope
Checkpoints: After each major step, output: ✅ [what was completed]
At the end, output a full summary of every file changed.
```

## Template I — Visual Descriptor

Use for Midjourney, DALL-E 3, Stable Diffusion, Sora, Runway, and any image or video generation tool.

```text
Subject: [Main subject — specific, not vague]
Action/Pose: [What the subject is doing]
Setting: [Where the scene takes place]
Style: [photorealistic / cinematic / anime / oil painting / vector / etc.]
Mood: [dramatic / serene / eerie / joyful / etc.]
Lighting: [golden hour / studio / neon / overcast / candlelight / etc.]
Color Palette: [dominant colors or named palette]
Composition: [wide shot / close-up / aerial / Dutch angle / etc.]
Aspect Ratio: [16:9 / 1:1 / 9:16 / 4:3]
Negative Prompts: [blurry, watermark, extra fingers, distortion, low quality]
Style Reference: [artist / film / aesthetic reference if applicable]
```

## Template J — Reference Image Editing

```text
Reference image: [attached / URL]
What to keep exactly the same: [list everything that must not change]
What to change: [specific edit only — be precise]
How much to change: [subtle / moderate / significant]
Style consistency: maintain the exact style, lighting, and mood of the reference
Negative prompt: [what to avoid introducing]
```

## Template K — ComfyUI

```text
POSITIVE PROMPT: [subject], [style], [mood], [lighting], [composition], [quality boosters: highly detailed, sharp focus, 8k]
NEGATIVE PROMPT: [what to exclude: blurry, low quality, watermark, extra limbs, bad anatomy, distorted, oversaturated]
CHECKPOINT: [model name]
SAMPLER: Euler a (recommended starting point)
CFG SCALE: 7 (increase for stricter prompt adherence)
STEPS: 20-30
RESOLUTION: [width x height — must be divisible by 64]
```

## Template L — Prompt Decompiler

Use when the user pastes an existing prompt and wants to break it down, adapt it for a different tool, simplify it, or understand its structure.

```text
Original prompt: [paste]
Structure analysis:
- Role/Identity: [what role is assigned and why]
- Task: [what action is being requested]
- Constraints: [what limits are set]
- Format: [what output shape is expected]
- Weaknesses: [what is missing or could cause wrong output]
Recommended fix: [rewritten version with gaps filled]
```

## Template M — Current Claude Task Brief

Use for complex, multi-step, or agentic tasks on current Claude models—Claude.ai, API, or Claude Code.

```markdown
## Objective
[What needs to be built, fixed, or produced — one clear sentence. Add WHY if it affects approach.]

## Context
[What exists now — relevant files, current behavior, stack already in place, what was tried and failed]

## Target State
[What done looks like — specific files changed, behavior produced, tests passing. Binary where possible.]

## Scope
- Work only in: [specific files and directories]
- Do NOT touch: [forbidden files — .env, package-lock.json, configs, anything outside scope]

## Constraints
- [Stack version, naming conventions, no new dependencies without asking]
- Only make changes directly requested. Do not add features, abstractions, or files beyond what was asked.

## Acceptance Criteria
- [ ] [Binary check 1]
- [ ] [Binary check 2]
- [ ] [Binary check 3]

## Action Boundaries
- Proceed with reversible, in-scope inspection, edits, and validation.
- Stop and ask before destructive or irreversible actions, external writes, purchases, material scope expansion, or decisions that require user-only input.

## Progress Evidence
For long-running work, report progress only when it changes or when a checkpoint is reached. Ground every completion claim in a tool result, changed artifact, or verification output.
```
