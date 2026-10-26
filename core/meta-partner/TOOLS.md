# TOOLS.md — Environment Paths, Meta-Prompt Compiler & DeepSeek Harness Map

## 1. Local Workspace & Meta-Compiler Paths
- **Meta-Partner Root**: `/Users/ryan/Documents/projects/meta-partner/core/meta-partner`
- **Meta-Prompt Skill Root**: `/Users/ryan/Documents/projects/meta-partner/skills/meta-prompt`
  - Main Skill Spec: `/Users/ryan/Documents/projects/meta-partner/skills/meta-prompt/SKILL.md`
  - Role Adapters Reference: `/Users/ryan/Documents/projects/meta-partner/skills/meta-prompt/references/agent_role_adapters.md`
  - Evaluation Rubric Reference: `/Users/ryan/Documents/projects/meta-partner/skills/meta-prompt/references/eval_workflow.md`
  - Deterministic Validator CLI:
    `python3 /Users/ryan/Documents/projects/meta-partner/skills/meta-prompt/scripts/validate_artifact.py --input <target_file> --mode <prompt|skill|openclaw-soul|openclaw-agents|openclaw-memory|hermes-soul|hermes-agents|claude-subagent|codex-agents>`

## 2. DeepSeek Harness (`dsh`) Integration Endpoints
- **Instruction Auto-Load Chain (`@deepseek-ai/dsh-agent-instructions`)**:
  - Global instructions: `~/.dsh/AGENTS.md` (`$DSH_HOME/AGENTS.md`)
  - Project instructions: `<projectRoot>/AGENTS.md` or `<projectRoot>/CLAUDE.md`
- **Skill Discovery Roots (`@deepseek-ai/dsh-skill-filesystem`, by Rank Priority)**:
  - Rank 100 (Project DSH): `<projectRoot>/.dsh/skills/<skill-name>/SKILL.md`
  - Rank 200 (Project Agents): `<projectRoot>/.agents/skills/<skill-name>/SKILL.md`
  - Rank 400 (User DSH): `~/.dsh/skills/<skill-name>/SKILL.md`
  - Rank 500 (User Agents): `~/.agents/skills/<skill-name>/SKILL.md`
- **Agent Presets Root (`@deepseek-ai/dsh-agent-presets`)**:
  - User Presets: `~/.dsh/.agent-presets/<preset-id>/agent.cordis.yml` & `preset.yml`
- **Cordis Plugin Adapter Bundle**:
  - Local Plugin Source: `/Users/ryan/Documents/projects/meta-partner/core/meta-partner/adapters/deepseek-harness/dsh-plugin-meta-partner`
  - Installer Script: `bash /Users/ryan/Documents/projects/meta-partner/core/meta-partner/adapters/deepseek-harness/install_to_dsh.sh`
