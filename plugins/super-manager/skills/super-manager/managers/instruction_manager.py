"""
instruction_manager.py - Native manager for instruction .md files with YAML frontmatter.

Instructions are markdown files in ~/.claude/super-manager/instructions/ that contain
contextual guidance injected into prompts when keyword matches occur.

Each .md file has YAML frontmatter:
  ---
  id: bash-scripting
  name: Bash Scripting Safety
  keywords: [bash, script, heredoc, js, javascript]
  enabled: true
  priority: 10
  ---
  # Content here...

Functions are standalone (no class) - matching the pattern of other managers.
"""
import sys
import os
import glob

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.configuration_paths import INSTRUCTIONS_DIR
from shared.logger import create_logger
from shared.config_file_handler import read_frontmatter, write_frontmatter
from shared.file_operations import archive_file, ensure_directory

log = create_logger("instruction-manager")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _instruction_path(instruction_id):
    """Build the full file path for an instruction ID."""
    return os.path.join(INSTRUCTIONS_DIR, instruction_id + ".md")


def _scan_all():
    """
    Scan INSTRUCTIONS_DIR for .md files and parse frontmatter from each.
    Returns list of (file_path, metadata_dict) tuples.
    Skips files with no valid frontmatter.
    """
    ensure_directory(INSTRUCTIONS_DIR)
    results = []
    for md_file in sorted(glob.glob(os.path.join(INSTRUCTIONS_DIR, "*.md"))):
        meta = read_frontmatter(md_file)
        if meta is None:
            log.warn("Skipping file with no frontmatter: " + md_file)
            continue
        meta["_file_path"] = md_file
        results.append((md_file, meta))
    return results


def _normalize_bool(value):
    """Normalize a frontmatter boolean value to Python bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_all():
    """
    List all instructions with metadata.
    Returns dict with items list and summary string.
    """
    entries = _scan_all()
    items = []
    enabled_count = 0
    disabled_count = 0

    for file_path, meta in entries:
        is_enabled = _normalize_bool(meta.get("enabled", False))
        body = meta.get("body", "")
        has_content = len(body.strip()) > 10

        if is_enabled:
            enabled_count += 1
        else:
            disabled_count += 1

        items.append({
            "id": meta.get("id", os.path.splitext(os.path.basename(file_path))[0]),
            "name": meta.get("name", ""),
            "keywords": meta.get("keywords", []),
            "enabled": is_enabled,
            "priority": int(meta.get("priority", 50)),
            "file_path": file_path,
            "has_content": has_content,
        })

    total = len(items)
    summary = (
        str(total) + " instructions, "
        + str(enabled_count) + " enabled, "
        + str(disabled_count) + " disabled"
    )
    log.info("list_all: " + summary)
    return {"items": items, "summary": summary}


def add_item(instruction_id, name, keywords, content, priority=10):
    """
    Create a new instruction .md file with frontmatter.
    instruction_id becomes the filename (e.g., bash-scripting -> bash-scripting.md).
    """
    ensure_directory(INSTRUCTIONS_DIR)
    file_path = _instruction_path(instruction_id)

    if os.path.exists(file_path):
        log.warn("add_item: instruction already exists: " + instruction_id)
        return {
            "success": False,
            "error": "Instruction " + repr(instruction_id) + " already exists",
        }

    meta = {
        "id": instruction_id,
        "name": name,
        "keywords": keywords if isinstance(keywords, list) else [keywords],
        "enabled": "true",
        "priority": str(priority),
    }
    write_frontmatter(file_path, meta, content)
    log.info("add_item: created instruction " + repr(instruction_id) + " (" + name + ")")
    return {"success": True, "id": instruction_id, "file_path": file_path}


def remove_item(instruction_id):
    """Archive an instruction (never delete). Moves to archive/ with timestamp."""
    file_path = _instruction_path(instruction_id)

    if not os.path.exists(file_path):
        log.warn("remove_item: instruction not found: " + instruction_id)
        return {
            "success": False,
            "error": "Instruction " + repr(instruction_id) + " not found",
        }

    archive_path = archive_file(file_path, reason="removed")
    log.info(
        "remove_item: archived instruction "
        + repr(instruction_id) + " -> " + str(archive_path)
    )
    return {"success": True, "id": instruction_id, "archived_to": archive_path}


def enable_item(instruction_id):
    """Set enabled: true in frontmatter."""
    file_path = _instruction_path(instruction_id)
    meta = read_frontmatter(file_path)

    if meta is None:
        log.warn("enable_item: instruction not found: " + instruction_id)
        return {
            "success": False,
            "error": "Instruction " + repr(instruction_id) + " not found",
        }

    body = meta.pop("body", "")
    meta["enabled"] = "true"
    write_frontmatter(file_path, meta, body)
    log.info("enable_item: enabled instruction " + repr(instruction_id))
    return {"success": True, "id": instruction_id, "enabled": True}


def disable_item(instruction_id):
    """Set enabled: false in frontmatter."""
    file_path = _instruction_path(instruction_id)
    meta = read_frontmatter(file_path)

    if meta is None:
        log.warn("disable_item: instruction not found: " + instruction_id)
        return {
            "success": False,
            "error": "Instruction " + repr(instruction_id) + " not found",
        }

    body = meta.pop("body", "")
    meta["enabled"] = "false"
    write_frontmatter(file_path, meta, body)
    log.info("disable_item: disabled instruction " + repr(instruction_id))
    return {"success": True, "id": instruction_id, "enabled": False}


def get_item(instruction_id):
    """Return full instruction content + metadata."""
    file_path = _instruction_path(instruction_id)
    meta = read_frontmatter(file_path)

    if meta is None:
        log.warn("get_item: instruction not found: " + instruction_id)
        return {
            "success": False,
            "error": "Instruction " + repr(instruction_id) + " not found",
        }

    body = meta.get("body", "")
    return {
        "success": True,
        "id": meta.get("id", instruction_id),
        "name": meta.get("name", ""),
        "keywords": meta.get("keywords", []),
        "enabled": _normalize_bool(meta.get("enabled", False)),
        "priority": int(meta.get("priority", 50)),
        "file_path": file_path,
        "has_content": len(body.strip()) > 10,
        "content": body,
    }


def get_matching_instructions(prompt_text):
    """
    Find all enabled instructions whose keywords match the prompt text.
    Returns list of matching instructions sorted by priority (lower = higher priority).
    """
    prompt_lower = prompt_text.lower()
    entries = _scan_all()
    matches = []

    for file_path, meta in entries:
        if not _normalize_bool(meta.get("enabled", False)):
            continue

        keywords = meta.get("keywords", [])
        if not isinstance(keywords, list):
            keywords = [keywords]

        matched_keywords = [kw for kw in keywords if kw.lower() in prompt_lower]
        if not matched_keywords:
            continue

        body = meta.get("body", "")
        priority = int(meta.get("priority", 50))
        matches.append({
            "id": meta.get("id", os.path.splitext(os.path.basename(file_path))[0]),
            "name": meta.get("name", ""),
            "priority": priority,
            "matched_keywords": matched_keywords,
            "content": body,
        })

    matches.sort(key=lambda m: m["priority"])
    log.info(
        "get_matching_instructions: " + str(len(matches))
        + " matches from " + str(len(entries)) + " instructions"
    )
    return matches


def verify_all():
    """
    Health check - validate all instruction .md files.
    Checks: valid frontmatter, required fields, no duplicate IDs.
    Returns dict with {healthy: [], issues: []}.
    """
    ensure_directory(INSTRUCTIONS_DIR)
    healthy = []
    issues = []
    seen_ids = {}
    required_fields = ["id", "name", "keywords", "enabled"]

    for md_file in sorted(glob.glob(os.path.join(INSTRUCTIONS_DIR, "*.md"))):
        basename = os.path.basename(md_file)
        meta = read_frontmatter(md_file)

        if meta is None:
            issues.append({"file": basename, "issue": "No valid YAML frontmatter"})
            continue

        # Check required fields
        missing = [f for f in required_fields if f not in meta or meta[f] == ""]
        if missing:
            issues.append({
                "file": basename,
                "issue": "Missing fields: " + ", ".join(missing),
            })
            continue

        # Check for duplicate IDs
        inst_id = meta.get("id", "")
        if inst_id in seen_ids:
            issues.append({
                "file": basename,
                "issue": "Duplicate ID " + repr(inst_id) + " (also in " + seen_ids[inst_id] + ")",
            })
            continue

        seen_ids[inst_id] = basename
        healthy.append({
            "id": inst_id,
            "name": meta.get("name", ""),
            "file": basename,
        })

    log.info(
        "verify_all: " + str(len(healthy)) + " healthy, "
        + str(len(issues)) + " issues"
    )
    return {"healthy": healthy, "issues": issues}
