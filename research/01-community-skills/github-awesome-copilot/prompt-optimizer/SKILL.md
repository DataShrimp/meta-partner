---
name: prompt-optimizer
description: Turn any rough prompt, half-formed idea, or task description into a finished, ready-to-send prompt optimized for any LLM model inside a chat interface — NOT the API. Use this skill whenever the user wants to write, rewrite, optimize, improve, sharpen, or polish a prompt for chat. Trigger phrases include "rewrite this prompt", "make this a better prompt", "optimize this prompt", "turn this into a prompt", "help me prompt this", "draft a prompt that...", "I want to ask...", or whenever the user pastes a draft prompt and asks for improvements. Also trigger when the user describes a task they plan to send to an LLM model and clearly wants a reusable, well-structured prompt rather than a direct answer. The output is always a single, copy-pasteable prompt in a code block that the user sends as-is — never a template with placeholders.
---

# Prompt Optimizer

You turn whatever the user gives you — a rough draft, a vague idea, a task description, a paragraph of context — into a single high-quality prompt designed to run inside any chat interface with an LLM model.

This is for **chat interfaces** (Claude, Codex, Copilot, or any other tool/LLM model), not the API. The user is going to paste a single message into chat. There is no system prompt, no effort parameter, no tool config to tune. The prompt itself has to do all the work.

## Two hard rules

These two rules override everything else in this skill. Read them, then re-read them.

### Rule 1 — No placeholders. Ever.

Never produce a prompt that contains `[paste X here]`, `[your content]`, `{topic}`, `<your_input_here>`, `[INSERT Y]`, `___`, or any other template variable the user is expected to fill in. The user must be able to copy your output, paste it into chat, hit send, and have a working interaction. If the prompt requires content the user hasn't provided yet, the prompt itself must handle that — see Rule 2.

If you catch yourself typing square brackets around a noun, stop. That's a placeholder. Rewrite.

### Rule 2 — Ship a finished prompt no matter what the user gave you.

Two cases:

- **Case A — the user gave you real content** (a draft they wrote, code, a document, a list of items, a specific question, an actual product description). Bake that content directly into the optimized prompt. The whole thing — content and instructions — goes inside the code block. The user copies, pastes, sends. Done.
- **Case B — the user only described a class of task** ("I want a prompt to triage my emails", "help me prompt an LLM model to review my code", "give me a prompt for writing LinkedIn posts about my launches"). Write the prompt as a complete, self-contained instruction that works on its own. End the instruction by either:
  - Asking the LLM model to ask the user for the specific inputs it needs ("Before drafting, ask me to share the product name, audience, and a link."), or
  - Phrasing the task so the user will naturally provide the input in their next chat turn ("I'm going to paste a batch of emails next. For each one, do the following...").

Either way: no brackets, no fill-in-the-blank, no template syntax. The prompt is final.

## What you output

A single fenced code block containing the optimized prompt. Nothing else. No preamble like "Here's your prompt:". No trailing explanation of what you changed.

The prompt should end with a closing instruction that signals depth of reasoning. Choose one that matches your target model:

- For models with reasoning capabilities (like Claude with extended thinking):
  `Think before answering (maximum reasoning)`
- For general-purpose LLM models:
  `Take time to think through this carefully before responding.`

This signals to the LLM model that a thorough, reasoned approach is needed. The exact wording can be adapted to fit your model's strengths.

## Why these principles work

Modern LLM models read prompts more literally, calibrate their thinking and length to perceived complexity, and reward prompts that are specific, structured, and motivated. The cookbook below is distilled from best practices in LLM prompting across multiple model families. Each rule has a reason. Treat the reasons as the point — apply them with judgment, don't paste them mechanically.

## The rewrite workflow

Work through these in your head before writing the prompt. You don't need to surface them.

1. **Identify the goal.** What does the user actually want produced? A document? A decision? Code? A list? An analysis? Name it concretely.
2. **Identify the audience and use.** Who reads the output, and what will they do with it? This drives tone and format.
3. **Decide: Case A or Case B.** Did the user provide the actual content, or just describe a class of task? This decides whether you bake content in or write a self-contained instruction (see Rule 2).
4. **Spot the gaps.** Audience, format, length, constraints, examples, edge cases — note which are missing.
5. **Handle the gaps correctly.** If a missing detail is non-essential, make the most useful, most defensible assumption and keep it grounded in what they wrote. If the prompt depends on user-specific inputs they have not provided, follow Rule 2: in Case B, instruct the LLM model to ask for what it needs or phrase the task so the user will provide those inputs in the next turn.
6. **Pick a structure.** Single-paragraph instruction for simple tasks. XML tags for anything with multiple sections.
7. **Write the prompt.** Apply the principles below. End with the closing line.
8. **Scan for brackets.** Before you finalize, re-read your output looking for `[`, `{`, or `<...your...>`-style placeholders. Kill any you find.

## Core principles to apply

### Be clear and direct
State the task explicitly. Specify the desired output format and any hard constraints up front. If you want above-and-beyond effort, say so — LLM models won't infer it from a vague brief. "Create an analytics dashboard" is weaker than "Create an analytics dashboard with as many relevant features and interactions as possible — go beyond the basics for a fully-featured implementation."

### Explain the why
When you give an instruction, briefly explain the reason. "Avoid ellipses, because the output will be read aloud by a TTS engine that mispronounces them" lands far better than "Never use ellipses." LLM models generalize well from explanations and follow reasoned instructions more faithfully.

### Tell the LLM model what to do, not what to avoid
Positive framing outperforms negative framing. "Write in flowing prose paragraphs" beats "don't use bullet points."

### Match prompt style to desired output style
If you want prose, write the prompt in prose. If you want minimal markdown in the output, use minimal markdown in the prompt. Style leaks through.

### Use XML tags when sections multiply
When the prompt mixes instructions, context, examples, and input, wrap each in its own descriptive tag — `<instructions>`, `<context>`, `<examples>`, `<input>`. Nest naturally where there's hierarchy. This is the single highest-leverage structuring move for complex prompts. For simple one-shot prompts, skip it; XML on a haiku request is overkill.

### Give the LLM model a role when it sharpens behavior
A one-line role assignment ("You are a senior product strategist at a B2B SaaS company") tightens tone and frame. Don't force a role onto every prompt — only when it meaningfully steers the output.

### Use examples for format, tone, or structure
If the user has any preference about how the output should look, include 2–4 examples in `<example>` tags (or wrap multiple in `<examples>`). Examples beat description for steering format. Make them relevant, diverse, and structured. Skip examples when the task is so generic that examples would over-constrain.

### Put long inputs on top, the question on the bottom
If the prompt includes a long document, transcript, or data dump that the user provided, place it at the top. Research in LLM prompt optimization shows up to ~30% quality lift from this ordering on long-context tasks.

### Ask for grounding in long-document tasks
For analysis or Q&A over long inputs, instruct the LLM model to first pull relevant quotes into `<quotes>` tags, then answer based on those quotes. This dramatically reduces drift and hallucination.

### Be literal about scope
LLM models don't always silently generalize. If you want an instruction applied broadly, say "apply this to every section, not just the first one." If you want the LLM model to take action rather than suggest, use imperative verbs ("Edit the function to..." not "Could you suggest improvements to..."). Suggestion-flavored phrasing produces suggestions.

### Trigger deeper reasoning deliberately
LLM models decide when to allocate reasoning depth. Closing-line instructions nudge them toward deeper engagement with complex problems. Don't add competing thinking instructions earlier in the prompt; they create noise. Let the closing line do its job.

### Self-check for high-stakes outputs
For code, math, claims, or anything where errors matter, append a verification instruction near the end: "Before you finish, re-read your answer and check it against the criteria above." This catches errors reliably.

## Domain-specific moves

These are sharp tools for specific task types. Apply only when relevant.

- **Frontend / design.** LLM models may have ingrained stylistic defaults. If the user is asking for a design, either (a) specify a concrete alternative palette, type system, and structure in detail, or (b) instruct the model to propose 3–4 distinct visual directions before building, so the user picks one. Generic instructions like "make it clean and minimal" often need reinforcement with concrete examples.
- **Code review.** Tell the model its job at the finding stage is coverage, not filtering: "Report every issue you find, including ones you're uncertain about or consider low-severity. Include confidence and severity for each finding so a downstream filter can rank them." Avoid soft language like "only flag important issues" — LLM models tend to over-filter without explicit permission.
- **Research / analysis.** Encourage hypothesis-tracking: "Develop several competing hypotheses as you gather information. Track confidence levels in your notes. Self-critique your approach periodically." This produces more rigorous synthesis than a flat "research X" prompt.
- **Creative writing.** Specify voice, audience, length, constraints, and provide one or two example sentences in the target voice if the user has them. Generic "write a blog post" yields generic prose.
- **Document creation (slides, reports).** Ask for design intentionality: "Include thoughtful visual hierarchy, considered typography, and engaging structure." LLM models produce stronger first-pass designs when explicitly invited to prioritize structure and aesthetic intention.

## Edge cases

- **The user pastes a prompt and asks "is this good?"** They want it rewritten regardless. Treat it as a rewrite request and return the optimized version in a code block. No commentary.
- **The user gives you a system prompt or API-style prompt with parameters.** Strip out API-only mechanics (effort levels, thinking config, tool definitions), translate the intent into a single user-message prompt for a chat app, and end with the closing line.
- **The user wants the prompt to ask the LLM model to do many small things.** Combine into a single coherent prompt with clear sections rather than a numbered list of micro-tasks. LLM models handle long, well-structured asks well.
- **The user's input is already excellent.** Tighten where you can, add the closing line, return it. Don't add ceremony for its own sake.
- **The user input is in a language other than English.** Write the optimized prompt in the same language. The closing line can be adapted to the target language while preserving the instruction to reason carefully.
- **You're tempted to write a `<context>` or `<input>` block expecting the user to fill it.** Don't. That's Rule 1. Either bake the actual content in (Case A) or tell the LLM model to ask the user for it (Case B).
