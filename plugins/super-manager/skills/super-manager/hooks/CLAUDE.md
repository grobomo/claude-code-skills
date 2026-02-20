# hooks/

Hook registry metadata for Super-Manager.

## Contents

- `hook-registry.json` - Registry of all managed hooks (name, event, description, enabled)

## Important

- Super-Manager does NOT own hook files. Actual hook scripts live in `~/.claude/hooks/`.
- This folder only contains the registry that tracks and cross-references them.
- The registry maps hook names to their events (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse).
- `hook_manager.py` in `managers/` reads/writes this registry.
- Hooks are normalized to `{ event, matcher, name, async }` for hash comparison.
