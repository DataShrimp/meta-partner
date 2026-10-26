import { readFileSync, existsSync } from 'node:fs'
import { resolve } from 'node:path'

export interface MetaPartnerConfig {
  /** Absolute path to the universal meta-partner directory. */
  readonly metaPartnerDir?: string
  /** Absolute path to the meta-prompt skill directory. */
  readonly metaPromptSkillDir?: string
  /** Prompt section order for SOUL.md (default: 50, right after personaPrefix). */
  readonly soulSectionOrder?: number
  /** Prompt section order for declarative MEMORY.md (default: 9500, before environment suffix). */
  readonly memorySectionOrder?: number
}

const DEFAULT_PARTNER_DIR = '/Users/ryan/Workspace/skills/MetaPrompt/meta-partner'
const DEFAULT_META_PROMPT_DIR = '/Users/ryan/Workspace/skills/MetaPrompt/meta-prompt'

function readSafe(filePath: string): string {
  if (!existsSync(filePath)) {
    throw new Error(`[dsh-plugin-meta-partner] Required role file missing: ${filePath}`)
  }
  return readFileSync(filePath, 'utf-8').trim()
}

/**
 * Cordis plugin entry for DeepSeek Harness (`dsh`).
 *
 * Bridges three architectural gaps in DSH:
 * 1. Injects `SOUL.md` into `ctx.systemPrompt.section` with `interpolate: false` so
 *    prompt templates containing `{{VAR}}` never crash `renderPrompt()` assembly and
 *    remain KV-Cache prefix-stable.
 * 2. Bridges `MEMORY.md` into the session prompt (`dsh-agent-instructions` only
 *    auto-loads `AGENTS.md` / `CLAUDE.md`, ignoring `MEMORY.md`).
 * 3. Registers both `meta-partner` and `meta-prompt` into `ctx.skills` so they are
 *    available across all workspaces without manual copying.
 */
export const name = 'dsh-plugin-meta-partner'
export const inject = ['systemPrompt', 'skills'] as const

export function apply(ctx: any, config: MetaPartnerConfig = {}): void {
  const partnerDir = resolve(config.metaPartnerDir ?? DEFAULT_PARTNER_DIR)
  const metaPromptDir = resolve(config.metaPromptSkillDir ?? DEFAULT_META_PROMPT_DIR)
  const soulOrder = config.soulSectionOrder ?? 50
  const memoryOrder = config.memorySectionOrder ?? 9500

  const soulPath = resolve(partnerDir, 'SOUL.md')
  const memoryPath = resolve(partnerDir, 'MEMORY.md')
  const partnerSkillPath = resolve(partnerDir, 'adapters/deepseek-harness/SKILL.md')
  const metaPromptSkillPath = resolve(metaPromptDir, 'SKILL.md')

  // 1. Register KV-Cache prefix-stable SOUL.md section (interpolate: false is mandatory)
  ctx.effect(() =>
    ctx.systemPrompt.section({
      name: 'meta-partner:soul',
      order: soulOrder,
      interpolate: false,
      text: readSafe(soulPath),
    }),
  )

  // 2. Register Declarative MEMORY.md section (re-read per assembly via text callback)
  ctx.effect(() =>
    ctx.systemPrompt.section({
      name: 'meta-partner:memory',
      order: memoryOrder,
      interpolate: false,
      text: () => readSafe(memoryPath),
    }),
  )

  // 3. Register runtime skills into ctx.skills registry
  ctx.effect(() =>
    ctx.skills.register({
      name: 'meta-partner',
      description:
        'AI Flywheel Meta-Partner that orchestrates the meta-prompt compiler in Dual-Track Parallel mode (Track 1: immediate runnable MVP Prompt/Skill/Role + Track 2: 4-Axis Blind-Spot Warning Radar). DO NOT TRIGGER on trivial single-line code edits.',
      path: partnerSkillPath,
      source: 'runtime',
      resourceBase: { kind: 'directory', path: partnerDir },
      content: readSafe(partnerSkillPath),
    }),
  )

  ctx.effect(() =>
    ctx.skills.register({
      name: 'meta-prompt',
      description:
        'Self-evolving Meta-Prompt, Modular Agent Skill (SKILL.md), and Cross-Platform Agent Role compiler and 100-point evaluator. Trigger when building/optimizing prompts, skills, SOUL.md/AGENTS.md roles, or running A/B evals. DO NOT TRIGGER on normal business code implementation.',
      path: metaPromptSkillPath,
      source: 'runtime',
      resourceBase: { kind: 'directory', path: metaPromptDir },
      content: readSafe(metaPromptSkillPath),
    }),
  )
}
