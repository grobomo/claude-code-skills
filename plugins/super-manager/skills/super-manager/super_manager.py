"""
super_manager.py - Unified CLI for managing all Claude Code configuration.

4 sub-managers: hooks, skills, mcp-servers, instructions
3 orchestration commands: status, doctor, report
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.logger import create_logger
from shared.output_formatter import item_list

log = create_logger("super-manager")


def _get_manager(name):
    mapping = {
        "hooks": "managers.hook_manager",
        "skills": "managers.skill_manager",
        "mcp": "managers.mcp_server_manager",
        "instructions": "managers.instruction_manager",
    }
    module_path = mapping.get(name)
    if not module_path:
        print(f"Unknown manager: {name}")
        sys.exit(1)
    return __import__(module_path, fromlist=["list_all"])


def _get_flag(args, flag, default=None):
    try:
        idx = args.index(flag)
        return args[idx + 1]
    except (ValueError, IndexError):
        return default


def cmd_status(args):
    from commands.show_status import run
    verbose = "--verbose" in args or "-v" in args
    run(verbose=verbose)


def cmd_doctor(args):
    from commands.run_doctor import run
    auto_fix = "--fix" in args
    run(auto_fix=auto_fix)


def cmd_report(args):
    from commands.generate_report import run
    run()


def cmd_duplicates(args):
    from commands.detect_duplicates import run, compare_projects
    verbose = "--verbose" in args or "-v" in args
    compare_paths = None
    if "--compare" in args:
        idx = args.index("--compare")
        if idx + 2 < len(args):
            compare_paths = [args[idx + 1], args[idx + 2]]
    run(verbose=verbose, compare_paths=compare_paths)


def cmd_manager_action(manager_name, action, args):
    mgr = _get_manager(manager_name)

    if action == "list":
        result = mgr.list_all()
        items = result.get("items", [])
        summary = result.get("summary", "")
        print()
        print(f"{manager_name.title()}: {summary}")
        print()
        if items:
            skip = {"command", "file_exists", "in_settings", "in_registry",
                    "skill_path", "file_path", "has_content", "on_disk", "keywords"}
            cols = [(k, k.replace("_", " ").title()) for k in items[0].keys() if k not in skip][:5]
            print(item_list(items, cols))
        print()

    elif action == "add":
        _do_add(manager_name, mgr, args)

    elif action == "remove":
        name = args[0] if args else None
        if not name:
            print(f"Usage: {manager_name} remove <name>")
            sys.exit(1)
        result = mgr.remove_item(name)
        print(result.get("message", "Done"))

    elif action == "enable":
        name = args[0] if args else None
        if not name:
            print(f"Usage: {manager_name} enable <name>")
            sys.exit(1)
        result = mgr.enable_item(name)
        print(result.get("message", "Done"))

    elif action == "disable":
        name = args[0] if args else None
        if not name:
            print(f"Usage: {manager_name} disable <name>")
            sys.exit(1)
        result = mgr.disable_item(name)
        print(result.get("message", "Done"))

    elif action == "verify":
        result = mgr.verify_all()
        healthy = result.get("healthy", [])
        issues = result.get("issues", [])
        print()
        print(f"{manager_name.title()} Verification")
        print(f"Healthy: {len(healthy)}, Issues: {len(issues)}")
        for issue in issues:
            item_name = issue.get("item", "?")
            problem = issue.get("problem", "?")
            print(f"  [ISSUE] {item_name}: {problem}")
        if not issues:
            print("  All items healthy")
        print()

    elif action == "match" and manager_name == "instructions":
        prompt = " ".join(args) if args else ""
        if not prompt:
            print("Usage: instructions match <prompt text>")
            sys.exit(1)
        matches = mgr.get_matching_instructions(prompt)
        print()
        print("Matching instructions:")
        for m in matches:
            mid = m.get("id", "?")
            mname = m.get("name", "?")
            print(f"  - {mid}: {mname}")
        if not matches:
            print("  (no matches)")
        print()

    elif action == "start" and manager_name == "mcp":
        name = args[0] if args else None
        if not name:
            print("Usage: mcp start <name>")
            sys.exit(1)
        result = mgr.start_server(name)
        print(result.get("message", "Done"))

    elif action == "stop" and manager_name == "mcp":
        name = args[0] if args else None
        if not name:
            print("Usage: mcp stop <name>")
            sys.exit(1)
        result = mgr.stop_server(name)
        print(result.get("message", "Done"))

    elif action == "reload" and manager_name == "mcp":
        result = mgr.reload_all()
        print(result.get("message", "Done"))

    else:
        print(f"Unknown action: {action}")
        print("Available: list, add, remove, enable, disable, verify")
        if manager_name == "mcp":
            print("MCP-specific: start, stop, reload")
        sys.exit(1)


def _do_add(manager_name, mgr, args):
    if manager_name == "hooks":
        name = args[0] if args else None
        event = _get_flag(args, "--event")
        command = _get_flag(args, "--command")
        desc = _get_flag(args, "--description", "")
        matcher = _get_flag(args, "--matcher", "*")
        if not all([name, event, command]):
            print("Usage: hooks add <name> --event <event> --command <cmd>")
            sys.exit(1)
        result = mgr.add_item(name, event, command, description=desc, matcher=matcher)
        print(result.get("message", "Done"))
    elif manager_name == "skills":
        name = args[0] if args else None
        path = _get_flag(args, "--path")
        desc = _get_flag(args, "--description", "")
        kw = _get_flag(args, "--keywords", "")
        keywords = [k.strip() for k in kw.split(",")] if kw else []
        if not all([name, path]):
            print("Usage: skills add <name> --path <path> [--keywords <kw1,kw2>]")
            sys.exit(1)
        result = mgr.add_item(name, path, description=desc, keywords=keywords)
        print(result.get("message", "Done"))
    elif manager_name == "instructions":
        inst_id = args[0] if args else None
        name = _get_flag(args, "--name")
        kw = _get_flag(args, "--keywords", "")
        keywords = [k.strip() for k in kw.split(",")] if kw else []
        content = _get_flag(args, "--content", "")
        if not all([inst_id, name]):
            print("Usage: instructions add <id> --name <name> --keywords <kw1,kw2>")
            sys.exit(1)
        result = mgr.add_item(inst_id, name, keywords, content)
        print(result.get("message", "Done"))
    else:
        print(f"Add not supported for {manager_name}")


def main():
    if len(sys.argv) < 2:
        print("Super Manager - Unified Claude Code Configuration")
        print()
        print("Orchestration:")
        print("  status [--verbose]    Show dashboard for all components")
        print("  doctor [--fix]        Find and fix configuration issues")
        print("  report                Generate markdown config report")
        print("  duplicates [--verbose] Find duplicate skills/projects")
        print("  duplicates --compare <path_a> <path_b>")
        print()
        print("Sub-managers:")
        print("  hooks <action>        Manage Claude Code hooks")
        print("  skills <action>       Manage Claude Code skills")
        print("  mcp <action>          Manage MCP servers")
        print("  instructions <action> Manage context-aware instructions")
        print()
        print("Actions: list, add, remove, enable, disable, verify")
        sys.exit(0)

    command = sys.argv[1]
    rest = sys.argv[2:]

    if command == "status":
        cmd_status(rest)
    elif command == "doctor":
        cmd_doctor(rest)
    elif command == "report":
        cmd_report(rest)
    elif command == "duplicates":
        cmd_duplicates(rest)
    elif command in ("hooks", "skills", "mcp", "instructions"):
        if not rest:
            print(f"Usage: super_manager.py {command} <action>")
            print("Actions: list, add, remove, enable, disable, verify")
            sys.exit(1)
        action = rest[0]
        action_args = rest[1:]
        cmd_manager_action(command, action, action_args)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
