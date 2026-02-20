# Super-Manager

## Vision & Purpose

**Goal: Improve Claude Code UX for everyone on Mac, Windows, and Linux.**

The problem: Claude Code has skills, hooks, MCP servers, and instructions - but Claude doesn't know WHEN to use them. Users have to explicitly say "use X skill" or "/skill-name" instead of Claude automatically recognizing what tools are available and selecting the right one based on context.

Super-manager solves this by:
1. **Auto-detecting user intent** - keyword matching on every prompt to identify which skills/MCPs/instructions are relevant
2. **Auto-injecting context** - loading SKILL.md content and MCP suggestions into Claude's context so it knows what's available
3. **Enforcing tool usage** - blocking general tools (Bash, Edit, etc.) when a specialized skill exists for the task
4. **Managing all configuration** - single system to discover, register, and health-check all Claude Code components

### Design Principles
- **Cross-platform**: Pure Node.js for core (no Python dependency for setup/hooks). Python only for sub-managers that need keyring/etc.
- **Non-destructive**: Always snapshot existing config before changes. Rollback capability for everything.
- **Distributable**: Installable from marketplace as a skill. No post-install hooks - SKILL.md must be self-explanatory.
- **Intent-based keywords**: Skills are matched by what the USER wants to do, not by skill name. "scan my network" triggers network-scan, not typing "network-scan".
- **Zero-config onboarding**: setup.js handles everything - install hooks, patch settings.json, extract keywords, build registries.

### Target Users
Anyone using Claude Code who installs skills, MCP servers, or hooks. Super-manager makes all of these discoverable and auto-triggered so users don't have to memorize skill names.

## Architecture

### Hook Pipeline (how auto-detection works)

```
User types prompt
  |
  v
UserPromptSubmit (tool-reminder.js)
  |-- Scans prompt for skill keywords -> injects SKILL.md content
  |-- Scans prompt for MCP keywords -> suggests MCP servers
  |-- Scans prompt for instruction keywords -> injects instruction body
  |-- Writes pending suggestions -> state/super-manager-pending-suggestions.json
  |-- TUI output: "[SM] Loaded N skill(s): ..."
  |
  v
Claude processes prompt (with injected context)
  |
  v
PreToolUse (super-manager-enforcement-gate.js)
  |-- Reads pending suggestions from state file
  |-- Loads skill scopes from skill-registry.json
  |-- SCOPE MATCH + UNFULFILLED = HARD BLOCK (exit 2, tool denied)
  |-- NO SCOPE MATCH = SOFT WARN (exit 0, tool proceeds with advisory)
  |
  v
PostToolUse (super-manager-check-enforcement.js)
  |-- Marks suggestions as fulfilled when Skill/Task tools are used
```

### Scope System

Skills can declare file paths they "own" in skill-registry.json:
```json
{
  "id": "hooks",
  "scope": { "paths": [".claude/hooks/"], "description": "Hook script files" }
}
```
When a skill owns a path, Claude MUST invoke that skill before touching those files.

### Keyword System

Keywords in skill-registry.json map USER INTENT to skills:
- BAD: `["network-scan", "network scan"]` (just the skill name)
- GOOD: `["scan network", "find devices", "who's on my network", "nmap", "discover hosts"]`

Keywords are auto-extracted from SKILL.md files by setup.js during installation.

## Enforcement Details

### Three Observability Channels
1. **TUI** - console.log from hooks -> system-reminder in conversation
2. **Log file** - hooks.log + enforcement.log at logs/
3. **Status-line-cache** - JSON at state/status-line-cache.json

### Exit Codes
- enforcement-gate exit 0 = SOFT WARN (tool proceeds, advisory message)
- enforcement-gate exit 2 = HARD BLOCK (tool denied, must invoke skill first)

### Bootstrap Safety
Gate skips its own meta-files to prevent deadlock:
- `super-manager/state/`, `super-manager/logs/`
- `status-line-cache`, `super-manager-pending-suggestions`, `super-manager-enforcement`
- `.claude/plans/`, `.planning/`

## Credential Manager (5th sub-manager)

Secrets stored in OS credential store (Windows Credential Manager / macOS Keychain), NOT plaintext .env files.

- `credentials list` - show stored keys (names only, never values)
- `credentials verify` - check all credentials are resolvable
- `credentials audit` - find plaintext tokens in .env files
- `credentials store <service/KEY> --clipboard` - user stores token (NOT Claude)
- `credentials migrate <.env> <service>` - import .env into credential store
- NEVER read .env files directly - they may contain secrets
- NEVER output credential values in chat, logs, or memory
- Helper libraries: `credentials/claude_cred.py` (Python), `credentials/claude-cred.js` (Node.js)

## Setup & Installation

### For New Installs (from marketplace)
```bash
node ~/.claude/super-manager/setup.js
```
This:
1. Snapshots existing config to ~/.claude/backups/before-super-manager/
2. Installs hook scripts to ~/.claude/hooks/
3. Patches settings.json (merge, not replace)
4. Scans all SKILL.md files and extracts intent-based keywords
5. Builds/updates skill-registry.json
6. Runs health check
7. Prints summary + rollback command

### Rollback
```bash
node ~/.claude/super-manager/rollback.js
```
Restores everything from snapshot.

### Sub-Manager Commands
```bash
python super_manager.py hooks list|add|remove|enable|disable|verify
python super_manager.py skills list|add|remove|enable|disable|verify
python super_manager.py mcp list|enable|disable|verify
python super_manager.py instructions list|add|remove|enable|disable|verify|match
python super_manager.py credentials list|store|migrate|verify|audit|remove
python super_manager.py discover    # Find and register all components
python super_manager.py status      # Dashboard
python super_manager.py doctor      # Find and fix issues
```

## Rules for Claude

- ALWAYS use matched skills/MCPs before falling back to general tools
- NEVER read .env files that may contain secrets - use credential manager
- Run `discover` on first install to register existing components
- Run `doctor` to find configuration issues
- Keywords in skill-registry.json are USER INTENT, not skill names

## Folder Structure

```
super-manager/
|   # Core
|-- super_manager.py          # CLI router / entry point
|-- setup.js                  # Cross-platform installer (Node.js)
|-- rollback.js               # Undo setup.js changes
|-- CLAUDE.md                 # This file (technical reference)
|-- SKILL.md                  # Skill definition for Claude Code
|   # Sub-managers
|-- managers/                 # 5 Python manager modules
|-- commands/                 # Orchestration (status, doctor, discover)
|-- shared/                   # Shared Python utilities
|   # Registry & config
|-- hooks/                    # Hook registry metadata
|-- skills/                   # Skill registry metadata
|-- mcp/                      # Bundled mcpm package
|-- instructions/             # Context-aware instruction .md files
|-- credentials/              # Credential helpers (Python + Node.js)
|-- registries/               # Combined registry files
|   # Runtime
|-- state/                    # Runtime state (gitignored)
|-- logs/                     # Per-manager + enforcement logs
|-- reports/                  # Generated config reports
+-- archive/                  # Archived items (never deleted)
```

## Bug History

- **enforcement-gate exit 0**: Original gate was advisory-only. Fixed: scope-aware exit 2 for hard blocking.
- **Bootstrap deadlock**: Gate blocked its own state/log files. Fixed: skip meta-file paths.
- **Background task notifications**: Task completions triggered UserPromptSubmit hooks injecting stale context. Fixed: isBackgroundNotification() guard in tool-reminder.js.
