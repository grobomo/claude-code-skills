---

name: hook-manager
description: "Create and manage Claude Code hooks - correct schema, all event formats (including Stop), stdin/stdout contracts, enable/disable/verify. Knowledge base for hook development."
keywords:
  - hook
  - hooks
  - settings
  - registry
  - SessionStart
  - SessionEnd
  - PreToolUse
  - PostToolUse
  - UserPromptSubmit
  - matcher
  - debug

---

# Hook Manager

Create and manage Claude Code hooks. Enforces correct schema, tracks registry, enable/disable/verify.

## WHY THIS SKILL EXISTS

Hooks have specific stdin/stdout contracts per event type. Getting these wrong causes silent failures (hook runs but output is ignored). This skill stores the CORRECT formats so future sessions dont re-learn through trial and error. Always consult this before creating or debugging hooks.

**Official docs:** https://code.claude.com/docs/en/hooks

## Hook Event Types

| Event | When It Fires | Uses Matcher? | stdin Format |
|-------|---------------|---------------|-------------|
| UserPromptSubmit | Before user prompt is processed | NO | `{session_id, user_prompt}` |
| Stop | When Claude finishes responding | NO | `{session_id, stop_hook_active, last_assistant_message, transcript_path}` |
| SubagentStop | When subagent completes | NO | `{session_id, stop_hook_active, last_assistant_message, transcript_path}` |
| PreToolUse | Before tool execution | YES | `{session_id, tool_name, tool_input}` |
| PostToolUse | After tool execution | YES | `{session_id, tool_name, tool_input, tool_response}` |
| Notification | On notifications | YES | `{session_id, title, message}` |

## CRITICAL: Stop Hook Contract

**stdin (JSON on stdin):**
```json
{
  "session_id": "abc-123",
  "stop_hook_active": false,
  "last_assistant_message": "Full text of Claude response...",
  "transcript_path": "/path/to/transcript.jsonl"
}
```

**MUST check stop_hook_active to prevent infinite loops:**
```javascript
var input = JSON.parse(require("fs").readFileSync(0, "utf-8"));
// if (input.stop_hook_active) process.exit(0); // Only if patterns are broad enough to re-trigger
```

**stdout to block (make Claude continue):**
```json
{"decision": "block", "reason": "Explanation shown to Claude"}
```

**stdout to allow (do nothing):** Exit 0 with no output, or empty string.

## CRITICAL: PreToolUse Hook Contract

**stdin:**
```json
{
  "session_id": "abc-123",
  "tool_name": "Bash",
  "tool_input": {"command": "rm -rf /"}
}
```

**stdout to block tool:**
```json
{"hookSpecificOutput": {"decision": "deny", "reason": "Blocked because..."}}
```

**stdout to allow tool:**
```json
{"hookSpecificOutput": {"decision": "allow"}}
```

**stdout to ask user:**
```json
{"hookSpecificOutput": {"decision": "ask", "message": "Are you sure?"}}
```

NOTE: PreToolUse uses `hookSpecificOutput` wrapper, NOT top-level `decision`.

## CRITICAL: Matcher Rules

**Events WITHOUT matcher (omit the field entirely):**
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": "node script.js", "timeout": 5}
        ]
      }
    ]
  }
}
```

**Events WITH matcher (tool-based events only):**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "echo done"}
        ]
      }
    ]
  }
}
```

## Hook Types

### Command Hook
Runs a shell command. Script output goes to Claude as context (system-reminder).
```json
{
  "type": "command",
  "command": "node \"$HOME/.claude/hooks/my-hook.js\"",
  "timeout": 5
}
```

### Prompt Hook
Sends output to an LLM for processing.
```json
{
  "type": "prompt",
  "prompt": "Analyze this output and suggest improvements"
}
```

## Environment Variables

| Variable | Available In | Description |
|----------|-------------|-------------|
| `$HOME` | All | User home directory |
| `$CLAUDE_PROJECT_DIR` | All | Current project root |

## Node.js Hook Template (Synchronous - REQUIRED)

```javascript
#!/usr/bin/env node
"use strict";
var fs = require("fs");
var path = require("path");

// Read stdin SYNCHRONOUSLY - never use async/promises in hooks
var input = JSON.parse(fs.readFileSync(0, "utf-8"));

// For Stop hooks: optionally check stop_hook_active to prevent loops
if (input.stop_hook_active) process.exit(0);

// Your logic here
var response = input.last_assistant_message || input.user_prompt || "";

// To block/continue: output JSON
// To allow silently: output nothing
if (shouldBlock) {
  var out = JSON.stringify({decision: "block", reason: "Why..."});
  process.stdout.write(out);
}
```

**IMPORTANT:** Always use synchronous code. Never use async/await, Promises, or callbacks. Hooks must complete synchronously.

## Settings File Locations

| Scope | Path |
|-------|------|
| Global | `~/.claude/settings.json` |
| Project | `.claude/settings.json` |

## Registry

`~/.claude/hooks/hook-registry.json` - tracks all hooks with metadata.

| Field | Description |
|-------|-------------|
| name | Hook filename (without extension) |
| event | UserPromptSubmit, Stop, SubagentStop, PreToolUse, PostToolUse |
| matcher | Tool matcher pattern (only for Pre/PostToolUse) |
| managed | true = registered in hook-registry.json |
| description | What the hook does |

## Common Mistakes

1. **Adding matcher to UserPromptSubmit/Stop** - WRONG, causes "Expected string" error
2. **Using matcher: {}** - WRONG, matcher must be string or omitted
3. **stop_hook_active** - Set to true when hook already blocked once this turn. Check it if your patterns are broad enough to re-trigger on corrected responses. Skip the check if you WANT looping until Claude gets it right (recommended for specific patterns).
4. **Using async/promises in hooks** - Hook exits before async completes, output lost
5. **Wrong output format for PreToolUse** - Must use `hookSpecificOutput` wrapper
6. **Reading transcript instead of last_assistant_message** - Stop hook gets the response directly in stdin
7. **Outputting XML/text instead of JSON** - Claude only processes JSON output from hooks

## Instruction System Architecture

Instructions are organized in `~/.claude/instructions/` with subfolders per event:
```
~/.claude/instructions/
  UserPromptSubmit/   # Injected before processing user prompt
  Stop/               # Checked against Claude response text
  PreToolUse/         # (future) Checked before tool calls
```

Each event hook reads ALL .md files in its corresponding folder. The folder name IS the event - no JSON field needed.

## Creating a Hook

1. Create hook script in `~/.claude/hooks/`
2. Register in `settings.json` under the appropriate event
3. Add entry to `hook-registry.json` with description
4. Run config-awareness to update report

## Management Commands

```bash
# List all hooks
python ~/.claude/super-manager/super_manager.py hooks list

# Enable/disable
python ~/.claude/super-manager/super_manager.py hooks enable HOOK_NAME
python ~/.claude/super-manager/super_manager.py hooks disable HOOK_NAME

# Verify all hooks healthy
python ~/.claude/super-manager/super_manager.py hooks verify
```

## Dependency

Part of **super-manager** (`~/.claude/super-manager/`).

## Instruction Frontmatter Fields

Instructions in `~/.claude/instructions/<EventFolder>/` use YAML frontmatter:

| Field | Format | Description |
|-------|--------|-------------|
| `id` | string | Unique identifier |
| `pattern` | string (regex) | Combinatorial regex - use for permutations with quantifiers like `{0,10}` |
| `keywords` | [array] | Comma-separated substring matches - use for simple exact phrases |
| `description` | string | What the instruction enforces |

**Use `pattern` (not `keywords`) when matching permutations:**
```yaml
# BAD: listing every permutation
keywords: [should I fix, want me to fix, shall I fix, should I test, want me to test, ...]

# GOOD: one regex covers all permutations
pattern: (should|want|shall|would you like|do you want)\s.{0,10}(I|me)\s.{0,15}(test|run|fix|update|check|verify)
```

**Use `keywords` for simple exact phrases:** `[let me know if, is that okay, sound good]`
