"""
configuration_paths.py - Every file and folder path the super-manager needs.

All paths are centralized here so no other file has magic strings.
Import paths from here: from shared.configuration_paths import HOOKS_DIR, SETTINGS_JSON, etc.
"""
import os
import glob

# Base directories
HOME = os.environ.get("HOME") or os.environ.get("USERPROFILE", "")
CLAUDE_DIR = os.path.join(HOME, ".claude")
SUPER_MANAGER_DIR = os.path.join(CLAUDE_DIR, "super-manager")

# Super-manager subdirectories
REGISTRIES_DIR = os.path.join(SUPER_MANAGER_DIR, "registries")
INSTRUCTIONS_DIR = os.path.join(SUPER_MANAGER_DIR, "instructions")
LOGS_DIR = os.path.join(SUPER_MANAGER_DIR, "logs")
REPORTS_DIR = os.path.join(SUPER_MANAGER_DIR, "reports")
ARCHIVE_DIR = os.path.join(SUPER_MANAGER_DIR, "archive")
TESTS_DIR = os.path.join(SUPER_MANAGER_DIR, "tests")
CREDENTIALS_DIR = os.path.join(SUPER_MANAGER_DIR, "credentials")

# Registry files (inside super-manager)
HOOK_REGISTRY = os.path.join(REGISTRIES_DIR, "hook-registry.json")
SKILL_REGISTRY = os.path.join(REGISTRIES_DIR, "skill-registry.json")
CONFIG_HASH_FILE = os.path.join(REGISTRIES_DIR, "last-known-config-hash.txt")
CREDENTIAL_REGISTRY = os.path.join(CREDENTIALS_DIR, "credential-registry.json")

# Report file
CONFIG_REPORT = os.path.join(REPORTS_DIR, "config-report.md")

# Claude Code's own settings (NOT inside super-manager - stays in ~/.claude/)
SETTINGS_JSON = os.path.join(CLAUDE_DIR, "settings.json")

# Hook scripts directory (stays in ~/.claude/hooks/ - Claude Code reads from here)
HOOKS_DIR = os.path.join(CLAUDE_DIR, "hooks")

# Skill directories (Claude Code discovers skills here)
GLOBAL_SKILLS_DIR = os.path.join(CLAUDE_DIR, "skills")


def _find_mcp_dirs():
    """Discover MCP server directories from common locations."""
    candidates = [
        os.path.join(HOME, "mcp"),
        os.path.join(HOME, "MCP"),
    ]
    # Also search Documents/*/MCP and OneDrive*/Documents/*/MCP patterns
    for doc_dir in glob.glob(os.path.join(HOME, "Documents", "*", "MCP")):
        candidates.append(doc_dir)
    for doc_dir in glob.glob(os.path.join(HOME, "OneDrive*", "Documents", "*", "MCP")):
        candidates.append(doc_dir)
    return [d for d in candidates if os.path.isdir(d)]


def _find_servers_yaml_paths():
    """Build servers.yaml search paths dynamically."""
    paths = []
    for mcp_dir in _find_mcp_dirs():
        paths.append(os.path.join(mcp_dir, "mcp-manager", "servers.yaml"))
    paths.append(os.path.join(REGISTRIES_DIR, "servers.yaml"))
    return paths


# MCP servers.yaml (search order: discovered locations, then local registries fallback)
MCP_SERVERS_YAML_PATHS = _find_servers_yaml_paths()

# Existing tools (originals, not touched)
SKILL_MGR_CLI = os.path.join(GLOBAL_SKILLS_DIR, "skill-marketplace", "cli", "skill-mgr")

# Valid Claude Code hook events
VALID_HOOK_EVENTS = [
    "SessionStart", "SessionEnd", "UserPromptSubmit",
    "PreToolUse", "PostToolUse", "PreCompact",
    "Stop", "SubAgentSop", "PermissionRequest",
]

def find_servers_yaml():
    """Find the first existing servers.yaml path."""
    for path in MCP_SERVERS_YAML_PATHS:
        if os.path.exists(path):
            return path
    return None


def _discover_env_files():
    """Discover .env files in MCP server directories dynamically."""
    env_files = []
    for mcp_dir in _find_mcp_dirs():
        for entry in os.listdir(mcp_dir):
            env_path = os.path.join(mcp_dir, entry, ".env")
            if os.path.isfile(env_path):
                env_files.append((entry, env_path))
    return env_files


# Known .env file locations for credential scanning (discovered at import time)
KNOWN_ENV_FILES = _discover_env_files()

# Patterns that indicate a value is a secret (not a URL, username, etc.)
SECRET_PATTERNS = [
    "TOKEN", "KEY", "SECRET", "PASSWORD", "PASS", "AUTH",
]
