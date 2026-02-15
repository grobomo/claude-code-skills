# Claude Code Skills

Public skill marketplace for Claude Code CLI.

## Install

```bash
# Add this marketplace
claude plugin marketplace add grobomo/claude-code-skills

# Install a skill
claude plugin install super-manager@grobomo-marketplace --scope user
```

## Available Skills

| Skill | Description |
|-------|-------------|
| **super-manager** | Unified config manager for hooks, skills, MCP servers, and instructions |

## Usage (super-manager)

After installing, use `/super-manager` in Claude Code or run directly:

```bash
python ~/.claude/skills/super-manager/super_manager.py status
python ~/.claude/skills/super-manager/super_manager.py doctor --fix
python ~/.claude/skills/super-manager/super_manager.py report
```

## Publishing Your Own Skills

Fork this repo and add plugins following the structure:

```
plugins/your-skill/
  .claude-plugin/plugin.json
  skills/your-skill/SKILL.md
```
