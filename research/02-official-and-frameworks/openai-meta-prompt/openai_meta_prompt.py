"""
OpenAI Official Meta-Prompt & Iterative Evaluation Loop
Sources:
1. OpenAI Playground Prompt Generation Guide:
   https://developers.openai.com/api/docs/guides/prompt-generation
2. OpenAI Cookbook — Enhance your prompts with meta prompting:
   https://developers.openai.com/cookbook/examples/enhance_your_prompts_with_meta_prompting

Core Principles:
- Enforces "Reasoning Before Conclusions" (reverses example order if conclusions appear first)
- Preserves user-supplied constants, rubrics, and examples (prompt injection resilience)
- Standardizes output structure: [Task Line] -> # Steps -> # Output Format -> # Examples -> # Notes
- Combines Meta-Prompt generation with Structured Output LLM-as-a-Judge (`ScoreCard`) for closed-loop iteration
"""

from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

# 1. Official OpenAI Playground System Meta-Prompt (Text-out)
OPENAI_SYSTEM_META_PROMPT = """
Given a task description or existing prompt, produce a detailed system prompt to guide a language model in completing the task effectively.

# Guidelines

- Understand the Task: Grasp the main objective, goals, requirements, constraints, and expected output.
- Minimal Changes: If an existing prompt is provided, improve it only if it's simple. For complex prompts, enhance clarity and add missing elements without altering the original structure.
- Reasoning Before Conclusions**: Encourage reasoning steps before any conclusions are reached. ATTENTION! If the user provides examples where the reasoning happens afterward, REVERSE the order! NEVER START EXAMPLES WITH CONCLUSIONS!
    - Reasoning Order: Call out reasoning portions of the prompt and conclusion parts (specific fields by name). For each, determine the ORDER in which this is done, and whether it needs to be reversed.
    - Conclusion, classifications, or results should ALWAYS appear last.
- Examples: Include high-quality examples if helpful, using placeholders [in brackets] for complex elements.
    - What kinds of examples may need to be included, how many, and whether they are complex enough to benefit from placeholders.
- Clarity and Conciseness: Use clear, specific language. Avoid unnecessary instructions or bland statements.
- Formatting: Use markdown features for readability. DO NOT USE ``` CODE BLOCKS UNLESS SPECIFICALLY REQUESTED.
- Preserve User Content: If the input task or prompt includes extensive guidelines or examples, preserve them entirely, or as closely as possible. If they are vague, consider breaking down into sub-steps. Keep any details, guidelines, examples, variables, or placeholders provided by the user.
- Constants: DO include constants in the prompt, as they are not susceptible to prompt injection. Such as guides, rubrics, and examples.
- Output Format: Explicitly the most appropriate output format, in detail. This should include length and syntax (e.g. short sentence, paragraph, JSON, etc.)
    - For tasks outputting well-defined or structured data (classification, JSON, etc.) bias toward outputting a JSON.
    - JSON should never be wrapped in code blocks (```) unless explicitly requested.

The final prompt you output should adhere to the following structure below. Do not include any additional commentary, only output the completed system prompt. SPECIFICALLY, do not include any additional messages at the start or end of the prompt. (e.g. no "---")

[Concise instruction describing the task - this should be the first line in the prompt, no section header]

[Additional details as needed.]

[Optional sections with headings or bullet points for detailed steps.]

# Steps [optional]

[optional: a detailed breakdown of the steps necessary to accomplish the task]

# Output Format

[Specifically call out how the output should be formatted, be it response length, structure e.g. JSON, markdown, etc]

# Examples [optional]

[Optional: 1-3 well-defined examples with placeholders if necessary. Clearly mark where examples start and end, and what the input and output are. Use placeholders as necessary.]
[If the examples are shorter than what a realistic example is expected to be, make a reference with () explaining how real examples should be longer / shorter / different. AND USE PLACEHOLDERS! ]

# Notes [optional]

[optional: edge cases, details, and an area to call or repeat out specific important considerations]
""".strip()


def generate_system_prompt(task_or_prompt: str, model: str = "gpt-5.6-sol") -> str:
    """Generate or refine a production system prompt using OpenAI's official Meta-Prompt."""
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": OPENAI_SYSTEM_META_PROMPT},
            {"role": "user", "content": "Task, Goal, or Current Prompt:\n" + task_or_prompt},
        ],
    )
    return completion.choices[0].message.content


# 2. OpenAI Cookbook: Structured LLM-as-a-Judge Evaluation Schema for Prompt Iteration
class PromptEvaluationScoreCard(BaseModel):
    """Notice 'justification' comes BEFORE numeric scores, adhering to Reasoning-Before-Conclusions."""
    justification: str
    task_adherence: int
    constraint_compliance: int
    clarity_and_structure: int
    completeness: int
    anti_hallucination_grounding: int


EVALUATION_META_TEMPLATE = """
You are an expert evaluator tasked with assessing the quality of an LLM output generated by a candidate prompt.
Below is the original input and the generated output to be evaluated:

**Original Input**: {original_input}
**Generated Output**: {generated_output}

Evaluate the output on a scale of 1 to 5 (1 being the lowest and 5 being the highest) across each dimension in the schema.
Be critical in your evaluation and only give high scores (5/5) for exceptional outputs.
Provide your detailed justification first before assigning numeric scores.
""".strip()


def evaluate_candidate_output(original_input: str, generated_output: str, judge_model: str = "gpt-4o") -> PromptEvaluationScoreCard:
    """Evaluate a prompt's output using structured Pydantic parsing (LLM-as-a-Judge)."""
    response = client.beta.chat.completions.parse(
        model=judge_model,
        messages=[
            {
                "role": "user",
                "content": EVALUATION_META_TEMPLATE.format(
                    original_input=original_input,
                    generated_output=generated_output,
                ),
            }
        ],
        response_format=PromptEvaluationScoreCard,
    )
    return response.choices[0].message.parsed
