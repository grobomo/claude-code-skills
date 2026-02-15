---
name: hook-maker
description: Create Claude Code hooks with correct schema. Use when user asks to "make a hook", "create a hook", or "add a hook".
---

# Hook Maker

Create Claude Code hooks with correct schema.

## Hook Event Types

| Event | When It Fires | Uses Matcher? |
|-------|---------------|---------------|
| `UserPromptSubmit` | Before user prompt is processed | NO - omit matcher |
| `Stop` | When Claude stops | NO - omit matcher |
| `SubagentStop` | When subagent completes | NO - omit matcher |
| `PreToolUse` | Before tool execution | YES - use matcher |
| `PostToolUse` | After tool execution | YES - use matcher |
| `Notification` | On notifications | YES - use matcher |

## CRITICAL: Matcher Rules

**Events WITHOUT matcher (omit the field entirely):**
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": "python script.py", "timeout": 5}
        ]
      }
    ]
  }
}
```

**Events WITH matcher (tool-based events):**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "echo 'Bash was used'"}
        ]
      }
    ]
  }
}
```

## Hook Types

### Command Hook
Runs a shell command. Script output goes to Claude as context.
```json
{
  "type": "command",
  "command": "bash -c 'python \"$HOME/.claude/hooks/my-hook.py\"'",
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

## Environment Variables Available

| Variable | Description |
|----------|-------------|
| `$HOME` | User home directory |
| `$CLAUDE_PROJECT_DIR` | Current project root |
| `$CLAUDE_USER_PROMPT` | The user's input (UserPromptSubmit only) |

## Settings File Locations

| Scope | Path |
|-------|------|
| Global | `~/.claude/settings.json` |
| Project | `.claude/settings.json` |

Project settings merge with global settings.

## Hook Script Template

```python
#!/usr/bin/env python3
"""
Hook: [description]
Event: UserPromptSubmit
"""
import os
import sys
import json

def main():
    # Get user prompt (for UserPromptSubmit hooks)
    user_prompt = os.environ.get("CLAUDE_USER_PROMPT", "")

    # Your logic here
    if "keyword" in user_prompt.lower():
        # Output goes to Claude as context
        print("[Hook Context]")
        print("Relevant information here...")

    # Exit 0 = success, non-zero = hook failed
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Common Mistakes

1. **Adding matcher to UserPromptSubmit** - WRONG, causes "Expected string" error
2. **Using matcher: {}** - WRONG, matcher must be string or omitted
3. **Using matcher: ""** - Works but unnecessary, just omit it
4. **Forgetting timeout** - Defaults to 60s for commands, 30s for prompts
5. **Not quoting paths with spaces** - Use `"$HOME/.claude/hooks/script.py"`

## Workflow

1. Create hook script in appropriate location:
   - Global: `~/.claude/hooks/`
   - Project: `.claude/hooks/`

2. Add to settings.json with correct schema

3. Restart Claude Code to load new hooks

## Example: Create a UserPromptSubmit Hook

```bash
# 1. Create hooks folder
mkdir -p ~/.claude/hooks

# 2. Create hook script
cat > ~/.claude/hooks/my-hook.py << 'EOF'
#!/usr/bin/env python3
import os
prompt = os.environ.get("CLAUDE_USER_PROMPT", "")
if "deploy" in prompt.lower():
    print("[Deploy Context]")
    print("Remember to run tests before deploying!")
EOF
chmod +x ~/.claude/hooks/my-hook.py

# 3. Add to settings (merge with existing)
```

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'python \"$HOME/.claude/hooks/my-hook.py\"'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```
