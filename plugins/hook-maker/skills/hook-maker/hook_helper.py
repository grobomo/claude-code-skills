#!/usr/bin/env python3
"""
Hook Helper - Validate and generate Claude Code hooks.
"""
import json
import sys
from pathlib import Path

# Events that do NOT use matcher (omit the field)
NO_MATCHER_EVENTS = {"UserPromptSubmit", "Stop", "SubagentStop"}

# Events that use matcher (string pattern for tool name)
MATCHER_EVENTS = {"PreToolUse", "PostToolUse", "Notification"}


def validate_settings(settings_path: str) -> list:
    """Validate a settings.json file for hook schema errors."""
    errors = []

    try:
        with open(settings_path) as f:
            settings = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]
    except FileNotFoundError:
        return [f"File not found: {settings_path}"]

    hooks = settings.get("hooks", {})

    for event_name, event_hooks in hooks.items():
        if event_name not in NO_MATCHER_EVENTS and event_name not in MATCHER_EVENTS:
            errors.append(f"Unknown event type: {event_name}")
            continue

        if not isinstance(event_hooks, list):
            errors.append(f"{event_name}: Expected array, got {type(event_hooks).__name__}")
            continue

        for i, hook_group in enumerate(event_hooks):
            if not isinstance(hook_group, dict):
                errors.append(f"{event_name}[{i}]: Expected object, got {type(hook_group).__name__}")
                continue

            # Check matcher field
            if "matcher" in hook_group:
                if event_name in NO_MATCHER_EVENTS:
                    errors.append(
                        f"{event_name}[{i}]: 'matcher' field should be OMITTED "
                        f"(this event doesn't use matchers)"
                    )
                elif not isinstance(hook_group["matcher"], str):
                    errors.append(
                        f"{event_name}[{i}]: 'matcher' must be a string, "
                        f"got {type(hook_group['matcher']).__name__}"
                    )
            elif event_name in MATCHER_EVENTS:
                # Matcher is optional for tool events, but warn if missing
                pass  # This is fine, empty matcher matches all

            # Check hooks array
            if "hooks" not in hook_group:
                errors.append(f"{event_name}[{i}]: Missing 'hooks' array")
                continue

            if not isinstance(hook_group["hooks"], list):
                errors.append(f"{event_name}[{i}].hooks: Expected array")
                continue

            for j, hook in enumerate(hook_group["hooks"]):
                if "type" not in hook:
                    errors.append(f"{event_name}[{i}].hooks[{j}]: Missing 'type' field")
                elif hook["type"] == "command" and "command" not in hook:
                    errors.append(f"{event_name}[{i}].hooks[{j}]: Missing 'command' field")
                elif hook["type"] == "prompt" and "prompt" not in hook:
                    errors.append(f"{event_name}[{i}].hooks[{j}]: Missing 'prompt' field")

    return errors


def generate_hook_config(event: str, script_path: str, timeout: int = 5) -> dict:
    """Generate a valid hook configuration."""
    hook_entry = {
        "hooks": [
            {
                "type": "command",
                "command": f"bash -c 'python \"{script_path}\"'",
                "timeout": timeout
            }
        ]
    }

    # Only add matcher for events that use it
    if event in MATCHER_EVENTS:
        hook_entry["matcher"] = ""  # Empty string matches all tools

    return {
        "hooks": {
            event: [hook_entry]
        }
    }


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python hook_helper.py validate <settings.json>")
        print("  python hook_helper.py generate <event> <script_path> [timeout]")
        print()
        print("Events without matcher (omit field):")
        print(f"  {', '.join(sorted(NO_MATCHER_EVENTS))}")
        print()
        print("Events with matcher (string pattern):")
        print(f"  {', '.join(sorted(MATCHER_EVENTS))}")
        sys.exit(1)

    command = sys.argv[1]

    if command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python hook_helper.py validate <settings.json>")
            sys.exit(1)

        errors = validate_settings(sys.argv[2])
        if errors:
            print("Validation FAILED:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print("Validation PASSED")
            sys.exit(0)

    elif command == "generate":
        if len(sys.argv) < 4:
            print("Usage: python hook_helper.py generate <event> <script_path> [timeout]")
            sys.exit(1)

        event = sys.argv[2]
        script_path = sys.argv[3]
        timeout = int(sys.argv[4]) if len(sys.argv) > 4 else 5

        config = generate_hook_config(event, script_path, timeout)
        print(json.dumps(config, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
