"""
run_doctor.py - Find and auto-fix problems across all 4 managed components.

Runs verify_all() on each manager, collects issues, and offers fixes.
Usage: python -m commands.run_doctor [--fix]
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.output_formatter import table
from shared.logger import create_logger

log = create_logger("run-doctor")


def _explain_issue(problem):
    """Return a human-readable explanation of why this issue happened."""
    p = problem.lower()
    if "not found on disk" in p or "skill.md not found" in p:
        return "Registry has an entry but the actual file was deleted or moved. Stale registry entry."
    if "not registered" in p or "orphaned-disk" in p or "exists on disk but" in p:
        return "Skill was created on disk (manually or by skill-maker) but never added to the registry."
    if "orphaned-settings" in p or "not in hook-registry" in p:
        return "Hook is in settings.json but was never registered in hook-registry.json. Likely added manually."
    if "orphaned-registry" in p or "not in settings" in p:
        return "Hook is in registry but was removed from settings.json. Disabled or stale."
    if "command not found" in p:
        return "The binary for this server is not installed or not on PATH."
    if "no command or url" in p:
        return "Server entry in servers.yaml has no command or url - incomplete configuration."
    if "syntax" in p:
        return "Script has a JavaScript/Python syntax error. Needs manual code fix."
    if "file not found" in p:
        return "Hook script file was deleted or moved but still referenced in settings.json."
    return ""



def _check_manager(name, module_path):
    """Run verify_all() on one manager, return issues list."""
    try:
        mod = __import__(module_path, fromlist=["verify_all"])
        result = mod.verify_all()
        issues = result.get("issues", [])
        healthy = result.get("healthy", [])
        return {
            "name": name,
            "module": module_path,
            "healthy_count": len(healthy),
            "issues": issues,
            "error": None,
        }
    except Exception as e:
        log.error(f"Doctor failed for {name}: {e}")
        return {
            "name": name,
            "module": module_path,
            "healthy_count": 0,
            "issues": [{"item": name, "problem": f"Manager failed to load: {e}", "fix": "Check module imports"}],
            "error": str(e),
        }


def _attempt_fix(issue, module_path):
    """Try to auto-fix a known issue type."""
    problem = issue.get("problem", "")
    item = issue.get("item", issue.get("name", "unknown"))
    p = problem.lower()

    # Stale registry entry (registered but file not on disk) -> remove from registry
    if "not found on disk" in p or "skill.md not found" in p:
        try:
            mod = __import__(module_path, fromlist=["remove_item"])
            mod.remove_item(item)
            log.info(f"Auto-fixed: removed stale registry entry for '{item}'")
            return True, f"Removed stale registry entry for '{item}'"
        except Exception as e:
            return False, f"Could not remove '{item}': {e}"

    # Disk-only skill (exists on disk but not registered) -> register it
    if "not registered" in p or "exists on disk but" in p:
        try:
            mod = __import__(module_path, fromlist=["add_item"])
            # Build the skill path from the name
            import os
            home = os.environ.get("HOME") or os.environ.get("USERPROFILE", "")
            skill_path = os.path.join(home, ".claude", "skills", item, "SKILL.md")
            if os.path.isfile(skill_path):
                mod.add_item(item, skill_path, keywords=[item.replace("-", " ")])
                log.info(f"Auto-fixed: registered disk skill '{item}'")
                return True, f"Registered '{item}' from disk"
            else:
                return False, f"SKILL.md not found at expected path for '{item}'"
        except Exception as e:
            return False, f"Could not register '{item}': {e}"

    # Orphaned settings hook -> can offer to register but needs event/command info
    if "orphaned-settings" in p or "not in hook-registry" in p:
        log.warn(f"Cannot auto-fix orphaned settings hook '{item}' - register manually")
        return False, f"Hook '{item}' needs manual registration (event + command required)"

    # Orphaned registry hook -> remove from registry
    if "orphaned-registry" in p or "not in settings" in p:
        try:
            mod = __import__(module_path, fromlist=["remove_item"])
            mod.remove_item(item)
            log.info(f"Auto-fixed: removed orphaned registry entry for '{item}'")
            return True, f"Removed orphaned registry entry for '{item}'"
        except Exception as e:
            return False, f"Could not remove '{item}': {e}"

    # Missing file or syntax error - manual fix needed
    if "file not found" in p or "syntax" in p:
        return False, f"'{item}' needs manual fix"

    return False, f"Unknown issue type for '{item}' - needs manual review"


def run(auto_fix=False):
    """Run doctor across all managers."""
    managers = [
        ("Hook Manager", "managers.hook_manager"),
        ("Skill Manager", "managers.skill_manager"),
        ("MCP Server Manager", "managers.mcp_server_manager"),
        ("Instruction Manager", "managers.instruction_manager"),
    ]

    all_issues = []
    total_healthy = 0

    print("\nSuper Manager Doctor")
    print("=" * 60)

    for display_name, module_path in managers:
        result = _check_manager(display_name, module_path)
        total_healthy += result["healthy_count"]

        if result["error"]:
            print(f"\n[ERROR] {display_name}: {result['error']}")
        elif not result["issues"]:
            print(f"\n[OK] {display_name}: {result['healthy_count']} items, all healthy")
        else:
            print(f"\n[WARN] {display_name}: {result['healthy_count']} healthy, {len(result['issues'])} issues")
            for issue in result["issues"]:
                item_name = issue.get('item', issue.get('name', '?'))
                problem = issue.get('problem', '?')
                explanation = _explain_issue(problem)
                print(f"  - {item_name}: {problem}")
                if explanation:
                    print(f"    WHY: {explanation}")
                if auto_fix:
                    fixed, msg = _attempt_fix(issue, module_path)
                    status = "FIXED" if fixed else "SKIP"
                    print(f"    [{status}] {msg}")

        for issue in result["issues"]:
            issue["manager"] = display_name
        all_issues.extend(result["issues"])

    # Duplicate detection
    print("\n--- Duplicate Scan ---")
    try:
        from commands.detect_duplicates import find_skill_duplicates, compare_projects
        duplicates = find_skill_duplicates()
        if duplicates:
            print(f"  Found {len(duplicates)} potential duplicate(s):")
            for dup in duplicates:
                items = dup["items"]
                print(f"  [{dup['type']}] {' <-> '.join(items)}")
                print(f"    Reason: {dup['reason']}")
                if "paths" in dup and len(dup["paths"]) == 2:
                    pa = os.path.dirname(dup["paths"][0]) if dup["paths"][0] else ""
                    pb = os.path.dirname(dup["paths"][1]) if dup["paths"][1] else ""
                    if pa and pb and os.path.isdir(pa) and os.path.isdir(pb):
                        compare_projects(pa, pb)
        else:
            print("  No duplicates detected")
    except Exception as e:
        print(f"  Duplicate scan failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"Total: {total_healthy} healthy, {len(all_issues)} issues")

    if all_issues and not auto_fix:
        print("\nRun with --fix to attempt auto-repair")

    log.info(f"Doctor: {total_healthy} healthy, {len(all_issues)} issues, auto_fix={auto_fix}")
    return {"healthy": total_healthy, "issues": all_issues}


if __name__ == "__main__":
    auto_fix = "--fix" in sys.argv
    run(auto_fix=auto_fix)
