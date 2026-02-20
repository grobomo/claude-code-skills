# instruction-manager

Manage context-aware instruction files with keyword matching. Conditional context injection for Claude Code sessions.

> Part of [**super-manager**](https://github.com/grobomo/claude-code-skills/tree/main/plugins/super-manager). Installed automatically with super-manager, or independently.

## Install

```bash
claude plugin marketplace add grobomo/claude-code-skills
claude plugin install instruction-manager@grobomo-marketplace --scope user
```

Manage context-aware instruction .md files with YAML frontmatter. Part of super-manager.

## What Are Instructions?

Markdown files in `~/.claude/super-manager/instructions/` that contain contextual guidance. Each has YAML frontmatter with keywords - when a prompt matches keywords, the instruction content is injected as context.

### Frontmatter Format

```yaml
---
id: bash-scripting
name: Bash Scripting Safety
keywords: [bash, script, heredoc, js, javascript]
enabled: true
priority: 10
---
# Content here...
```

## WHY This System Exists

### The Problem: Context Drift
As Claude's context window fills during long sessions, it enters "completion mode" - rushing through work and ignoring instructions. CLAUDE.md instructions read at session start get buried under thousands of lines of conversation. Claude stops following rules it read 50 messages ago.

### The Solution: Persistent Re-injection
tool-reminder.js (UserPromptSubmit hook) re-injects CLAUDE.md content on EVERY prompt as a system-reminder. This acts like a persistent system prompt that Claude can never "forget."

### The Architecture: Two Tiers
**Tier 1 - Global (CLAUDE.md):** Injected on EVERY prompt. Must be small (~45 lines). Contains only rules that apply to ALL interactions: communication style, environment paths, critical rules, core operation basics.

**Tier 2 - Conditional (instruction files):** Injected only when prompt keywords match. Contains detailed "when X do Y" rules: how to write JS from bash, OneDrive file operation restrictions, MCP management details, formatting conventions, config awareness system details, etc.

### Why Two Tiers?
- Token budget: Injecting 100+ lines every prompt wastes tokens on irrelevant rules
- Signal-to-noise: When everything is emphasized, nothing is. Fewer global rules = each rule gets more attention
- Conditional loading: "Writing JS from bash" rules only matter when the prompt mentions JS/bash/heredoc

### The "Always Document WHY" Rule
Every instruction file and every rule should explain WHY it exists, not just WHAT to do. When Claude understands the reason behind a rule, it follows the spirit even in edge cases the rule doesn't explicitly cover. When creating or editing instruction files, always include a brief WHY explanation.

## Commands

```bash
# List all instructions
python ~/.claude/super-manager/super_manager.py instructions list

# Add a new instruction
python ~/.claude/super-manager/super_manager.py instructions add INSTRUCTION_ID

# Remove (archives, never deletes)
python ~/.claude/super-manager/super_manager.py instructions remove INSTRUCTION_ID

# Enable/disable
python ~/.claude/super-manager/super_manager.py instructions enable INSTRUCTION_ID
python ~/.claude/super-manager/super_manager.py instructions disable INSTRUCTION_ID

# Verify all instructions healthy
python ~/.claude/super-manager/super_manager.py instructions verify

# Test keyword matching
python ~/.claude/super-manager/super_manager.py instructions match "some prompt text"
```

## Current Instructions

| ID | Keywords | Description |
|----|----------|-------------|
| background-tasks | background, task, zombie | Background task management |
| bash-scripting | bash, script, heredoc, js | Safe patterns for writing JS from bash |
| config-awareness | config, awareness, hash, registry | Config Awareness System details |
| file-operations | file, onedrive, write, edit | File operation rules for OneDrive |
| formatting | format, list, tree | Output formatting conventions |
| mcp-management | mcp, server, reload | MCP server management rules |

## Architecture

Two directories exist - keep them in sync:

```
~/.claude/instructions/UserPromptSubmit/   # LIVE - tool-reminder.js reads from here
~/.claude/super-manager/instructions/       # CANONICAL - instruction_manager.py manages here
```

The live directory is what gets loaded into context. The super-manager directory is the source of truth for instruction_manager.py CRUD commands. When adding/editing instructions, update BOTH locations.

### File Layout

```
~/.claude/super-manager/
├── instructions/              # .md files with YAML frontmatter
│   ├── background-tasks.md
│   ├── bash-scripting.md
│   ├── config-awareness.md
│   ├── file-operations.md
│   ├── formatting.md
│   └── mcp-management.md
└── managers/
    └── instruction_manager.py # CRUD + keyword matching
```

## Dependency

Part of **super-manager** (`~/.claude/super-manager/`).
