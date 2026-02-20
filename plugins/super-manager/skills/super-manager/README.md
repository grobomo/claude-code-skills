# Super-Manager

Unified configuration management for Claude Code with enforcement hooks.

## Problem

Claude Code has skills, MCP servers, and instruction files that get matched to prompts and injected as context. But Claude can ignore these suggestions and use general tools instead. There is no enforcement mechanism.

## Solution

Super-Manager adds enforcement hooks that fire BEFORE Claude uses general tools. If a skill or MCP was matched for the current task, Claude sees a blocking warning and must invoke the matched tool first.

## Install

1. Copy this folder to `~/.claude/super-manager/`
2. Run discovery: `python super_manager.py discover --auto`
3. Enforcement hooks are registered in `~/.claude/settings.json`

## Usage

```bash
# Quick health check
python super_manager.py status

# Find configuration issues
python super_manager.py doctor

# Auto-discover and register existing components
python super_manager.py discover --auto

# Generate configuration report
python super_manager.py report

# Find duplicate registrations
python super_manager.py duplicates
```

## Architecture

```
super-manager/
│   # Core
├── super_manager.py          # CLI router / entry point
├── CLAUDE.md                 # Technical reference for Claude
├── README.md                 # This file
├── SKILL.md                  # Skill definition
│   # Sub-managers (Python modules)
├── managers/
│   ├── hook_manager.py       # Hook registry operations
│   ├── skill_manager.py      # Skill registry operations
│   ├── mcp_server_manager.py # MCP server config operations
│   └── instruction_manager.py# Instruction file operations
│   # Orchestration commands
├── commands/
│   ├── status.py             # Quick health check
│   ├── doctor.py             # Configuration diagnostics
│   ├── report.py             # Generate dashboard
│   ├── discover.py           # Auto-register components
│   └── duplicates.py         # Find duplicate entries
│   # Shared utilities
├── shared/
│   ├── configuration_paths.py
│   ├── config_file_handler.py
│   ├── file_operations.py
│   ├── logger.py
│   └── output_formatter.py
│   # Registry & config
├── hooks/                    # Hook registry metadata
├── skills/                   # Skill registry metadata
├── mcp/                      # Bundled mcpm package
├── instructions/             # Context-aware .md files
├── registries/               # Combined registry files
│   # Runtime (gitignored)
├── state/                    # Pending suggestions, temp state
├── logs/                     # Audit + per-manager logs
├── reports/                  # Generated markdown reports
└── archive/                  # Archived items (timestamped)
```

## Enforcement Flow

```
User prompt
  -> tool-reminder.js (UserPromptSubmit)
     -> matches keywords -> writes state/super-manager-pending-suggestions.json
     -> injects context

Claude uses Bash/Edit/Write
  -> super-manager-enforcement-gate.js (PreToolUse)
     -> checks pending suggestions
     -> BLOCKS if unfulfilled skill/MCP match exists

Claude uses Skill/Task
  -> super-manager-check-enforcement.js (PostToolUse)
     -> marks suggestion fulfilled
     -> logs to logs/super-manager-enforcement.log
```
