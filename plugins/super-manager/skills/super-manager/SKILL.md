---
name: super-manager
description: Unified manager for all Claude Code configuration - hooks, skills, MCP servers, and instructions. Use when user asks about config status, hook management, skill management, or needs to diagnose configuration issues.
---

# Super Manager

Unified CLI for managing all 4 Claude Code configuration components.

## Quick Commands

```bash
# Dashboard - see health of all components
python ~/.claude/super-manager/super_manager.py status

# Verbose - see every item
python ~/.claude/super-manager/super_manager.py status --verbose

# Doctor - find and fix issues
python ~/.claude/super-manager/super_manager.py doctor
python ~/.claude/super-manager/super_manager.py doctor --fix

# Report - generate markdown config report
python ~/.claude/super-manager/super_manager.py report
```

## Sub-Managers

### Hooks (native)
```bash
python ~/.claude/super-manager/super_manager.py hooks list
python ~/.claude/super-manager/super_manager.py hooks add <name> --event <event> --command <cmd>
python ~/.claude/super-manager/super_manager.py hooks remove <name>
python ~/.claude/super-manager/super_manager.py hooks enable <name>
python ~/.claude/super-manager/super_manager.py hooks disable <name>
python ~/.claude/super-manager/super_manager.py hooks verify
```

### Skills (wrapper)
```bash
python ~/.claude/super-manager/super_manager.py skills list
python ~/.claude/super-manager/super_manager.py skills add <name> --path <path> [--keywords <kw1,kw2>]
python ~/.claude/super-manager/super_manager.py skills remove <name>
python ~/.claude/super-manager/super_manager.py skills enable <name>
python ~/.claude/super-manager/super_manager.py skills disable <name>
python ~/.claude/super-manager/super_manager.py skills verify
```

### MCP Servers (wrapper)
```bash
python ~/.claude/super-manager/super_manager.py mcp list
python ~/.claude/super-manager/super_manager.py mcp enable <name>
python ~/.claude/super-manager/super_manager.py mcp disable <name>
python ~/.claude/super-manager/super_manager.py mcp verify
```

### Instructions (native)
```bash
python ~/.claude/super-manager/super_manager.py instructions list
python ~/.claude/super-manager/super_manager.py instructions add <id> --name <name> --keywords <kw1,kw2>
python ~/.claude/super-manager/super_manager.py instructions remove <id>
python ~/.claude/super-manager/super_manager.py instructions enable <id>
python ~/.claude/super-manager/super_manager.py instructions disable <id>
python ~/.claude/super-manager/super_manager.py instructions match <prompt text>
python ~/.claude/super-manager/super_manager.py instructions verify
```

## Architecture

```
~/.claude/super-manager/
├── super_manager.py          # CLI entry point
├── SKILL.md                  # This file
├── shared/                   # 5 shared modules
│   ├── configuration_paths.py
│   ├── config_file_handler.py
│   ├── file_operations.py
│   ├── logger.py
│   └── output_formatter.py
├── managers/                 # 4 sub-managers
│   ├── hook_manager.py
│   ├── skill_manager.py
│   ├── mcp_server_manager.py
│   └── instruction_manager.py
├── commands/                 # 3 orchestration commands
│   ├── show_status.py
│   ├── run_doctor.py
│   └── generate_report.py
├── registries/               # Centralized registries
├── instructions/             # Instruction .md files
├── reports/                  # Generated reports
├── logs/                     # Per-manager logs
└── archive/                  # Archived items (never deleted)
```

## Key Principles

- **Never delete, always archive** - all removals go to archive/ with timestamp
- **Atomic writes** - write to .tmp then rename to prevent corruption
- **Cross-reference** - each manager checks both registry AND filesystem
- **Consistent interface** - all 4 managers have list/add/remove/enable/disable/verify
- **Centralized logging** - every action logged to per-manager log files
