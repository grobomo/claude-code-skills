"""
mcp_server_manager.py - WRAPPER manager for MCP servers.

Reads servers.yaml directly for listing/verification.
Provides native start/stop via subprocess for server lifecycle.
"""
import sys
import os
import subprocess
import signal
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.configuration_paths import find_servers_yaml, SUPER_MANAGER_DIR
from shared.logger import create_logger
from shared.config_file_handler import read_yaml_servers
from shared.file_operations import archive_file

log = create_logger("mcp-server-manager")

# PID tracking file for started servers
_PID_FILE = os.path.join(SUPER_MANAGER_DIR, "logs", "server-pids.json")


def _read_pids():
    """Read server PID tracking file."""
    if os.path.isfile(_PID_FILE):
        try:
            with open(_PID_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _write_pids(pids):
    """Write server PID tracking file."""
    os.makedirs(os.path.dirname(_PID_FILE), exist_ok=True)
    with open(_PID_FILE, "w", encoding="utf-8") as f:
        json.dump(pids, f, indent=2)


def _is_pid_running(pid):
    """Check if a process with given PID is running."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", "PID eq {}".format(pid)],
                capture_output=True, text=True, timeout=5
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.TimeoutExpired):
        return False


def list_all():
    """List all MCP servers from servers.yaml."""
    yaml_path = find_servers_yaml()
    if not yaml_path:
        log.warn("servers.yaml not found in any known location")
        return {"items": [], "summary": "0 servers (servers.yaml not found)"}

    servers = read_yaml_servers(yaml_path)
    pids = _read_pids()
    items = []
    for name, config in servers.items():
        running = False
        pid = pids.get(name)
        if pid and _is_pid_running(pid):
            running = True

        items.append({
            "name": name,
            "enabled": config.get("enabled", False),
            "description": config.get("description", ""),
            "command": config.get("command", config.get("url", "")),
            "auto_start": config.get("auto_start", False),
            "tags": config.get("tags", []),
            "status": "running" if running else ("healthy" if config.get("enabled", False) else "disabled"),
            "pid": pid if running else None,
        })

    enabled_count = sum(1 for i in items if i["enabled"])
    running_count = sum(1 for i in items if i["status"] == "running")
    log.info("LIST: {} servers ({} enabled, {} running)".format(len(items), enabled_count, running_count))
    return {
        "items": items,
        "summary": "{} servers ({} enabled, {} running)".format(len(items), enabled_count, running_count),
    }


def add_item(name, command="", description="", args=None, tags=None, enabled=False):
    """Add a server to servers.yaml."""
    yaml_path = find_servers_yaml()
    if not yaml_path:
        return {"success": False, "message": "servers.yaml not found"}

    if not command:
        return {"success": False, "message": "command is required"}

    servers = read_yaml_servers(yaml_path)
    if name in servers:
        return {"success": False, "message": "Server '{}' already exists".format(name)}

    # Append to servers.yaml
    entry_lines = [
        "",
        "  {}:".format(name),
        '    description: "{}"'.format(description),
        '    command: "{}"'.format(command),
    ]
    if args:
        args_str = ", ".join('"{}"'.format(a) for a in args)
        entry_lines.append("    args: [{}]".format(args_str))
    if tags:
        tags_str = ", ".join('"{}"'.format(t) for t in tags)
        entry_lines.append("    tags: [{}]".format(tags_str))
    entry_lines.append("    enabled: {}".format("true" if enabled else "false"))

    with open(yaml_path, "a", encoding="utf-8") as f:
        f.write("\n".join(entry_lines) + "\n")

    log.info("ADD: {} -> {}".format(name, command))
    return {"success": True, "message": "Added server '{}'".format(name)}


def remove_item(name):
    """Remove a server from servers.yaml."""
    yaml_path = find_servers_yaml()
    if not yaml_path:
        return {"success": False, "message": "servers.yaml not found"}

    with open(yaml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    found = False
    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if indent == 2 and stripped.endswith(":") and not stripped.startswith("#"):
            server_name = stripped[:-1].strip()
            if server_name == name:
                skip = True
                found = True
                continue
            else:
                skip = False

        if skip and indent > 2:
            continue
        elif skip and indent <= 2:
            skip = False

        if not skip:
            new_lines.append(line)

    if not found:
        return {"success": False, "message": "Server '{}' not found".format(name)}

    with open(yaml_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    log.info("REMOVE: {}".format(name))
    return {"success": True, "message": "Removed server '{}' from servers.yaml".format(name)}


def enable_item(name):
    """Enable a server in servers.yaml."""
    yaml_path = find_servers_yaml()
    if not yaml_path:
        return {"success": False, "message": "servers.yaml not found"}
    return _set_enabled(yaml_path, name, True)


def disable_item(name):
    """Disable a server in servers.yaml."""
    yaml_path = find_servers_yaml()
    if not yaml_path:
        return {"success": False, "message": "servers.yaml not found"}
    return _set_enabled(yaml_path, name, False)


def _set_enabled(yaml_path, name, enabled):
    """Toggle enabled flag for a server in servers.yaml (in-place edit)."""
    with open(yaml_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    found_server = False
    in_target = False
    modified = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if indent == 2 and stripped.endswith(":") and " " not in stripped:
            server_name = stripped[:-1]
            in_target = (server_name == name)
            if in_target:
                found_server = True
            continue

        if in_target and stripped.startswith("enabled:"):
            old_value = "true" if "true" in stripped else "false"
            new_value = "true" if enabled else "false"
            if old_value != new_value:
                lines[i] = line.replace("enabled: {}".format(old_value), "enabled: {}".format(new_value))
                modified = True
            break

    if not found_server:
        log.error("ENABLE/DISABLE: server '{}' not found in servers.yaml".format(name))
        return {"success": False, "message": "Server '{}' not found".format(name)}

    if modified:
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        action = "ENABLE" if enabled else "DISABLE"
        log.info("{}: {}".format(action, name))
        return {"success": True, "message": "Server '{}' {}".format(name, "enabled" if enabled else "disabled")}
    else:
        state = "enabled" if enabled else "disabled"
        return {"success": True, "message": "Server '{}' already {}".format(name, state)}


def verify_all(name=None):
    """Check MCP servers for issues."""
    yaml_path = find_servers_yaml()
    if not yaml_path:
        return {"healthy": [], "issues": [{"item": "servers.yaml", "problem": "servers.yaml not found", "fix": "Check MCP_SERVERS_YAML_PATHS"}]}

    servers = read_yaml_servers(yaml_path)
    issues = []

    for srv_name, config in servers.items():
        if name and srv_name != name:
            continue

        if config.get("enabled") and config.get("command"):
            cmd = config["command"]
            try:
                result = subprocess.run(
                    ["which", cmd], capture_output=True, text=True, timeout=5
                )
                if result.returncode != 0:
                    issues.append({
                        "item": srv_name,
                        "problem": "command '{}' not found on PATH".format(cmd),
                        "fix": "Check binary installation",
                    })
            except Exception:
                pass

        if not config.get("command") and not config.get("url"):
            issues.append({
                "item": srv_name,
                "problem": "no command or url configured",
                "fix": "Add command to servers.yaml",
            })

    healthy_list = [s for s in servers.keys() if not any(i.get("item") == s for i in issues)]
    log.info("VERIFY: {} servers checked, {} issues".format(len(servers), len(issues)))
    return {"healthy": healthy_list, "issues": issues}


def start_server(name):
    """Start a server by reading its config from servers.yaml and launching the process."""
    yaml_path = find_servers_yaml()
    if not yaml_path:
        return {"success": False, "message": "servers.yaml not found"}

    servers = read_yaml_servers(yaml_path)
    if name not in servers:
        return {"success": False, "message": "Server '{}' not found in servers.yaml".format(name)}

    config = servers[name]
    command = config.get("command", "")
    if not command:
        url = config.get("url", "")
        if url:
            return {"success": True, "message": "Server '{}' is URL-based ({}) - no process to start".format(name, url)}
        return {"success": False, "message": "Server '{}' has no command configured".format(name)}

    # Check if already running
    pids = _read_pids()
    existing_pid = pids.get(name)
    if existing_pid and _is_pid_running(existing_pid):
        return {"success": True, "message": "Server '{}' already running (PID {})".format(name, existing_pid)}

    # Build command line
    args = config.get("args", [])
    cmd_list = [command] + args

    # Build environment
    env = os.environ.copy()
    server_env = config.get("env", {})
    if server_env:
        env.update(server_env)

    try:
        log.info("START: {} -> {}".format(name, " ".join(cmd_list)))

        # Start process - MCP servers use stdio protocol so stdin must stay open
        # Use PIPE for stdin (server blocks waiting for input = stays alive)
        # Use DEVNULL for stdout/stderr (we don't read MCP responses from CLI)
        kwargs = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.PIPE,
            "env": env,
        }
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

        proc = subprocess.Popen(cmd_list, **kwargs)

        # Give it a moment to see if it crashes immediately
        time.sleep(1)
        if proc.poll() is not None:
            return {"success": False, "message": "Server '{}' exited immediately (code {})".format(name, proc.returncode)}

        # Track PID
        pids[name] = proc.pid
        _write_pids(pids)

        log.info("START: {} running as PID {}".format(name, proc.pid))
        return {"success": True, "message": "Started '{}' (PID {})".format(name, proc.pid)}

    except FileNotFoundError:
        return {"success": False, "message": "Command '{}' not found".format(command)}
    except Exception as e:
        log.error("START failed for {}: {}".format(name, e))
        return {"success": False, "message": "Failed to start '{}': {}".format(name, e)}


def stop_server(name):
    """Stop a running server by PID."""
    pids = _read_pids()
    pid = pids.get(name)

    if not pid:
        return {"success": False, "message": "No PID tracked for '{}' - server may not have been started by super-manager".format(name)}

    if not _is_pid_running(pid):
        del pids[name]
        _write_pids(pids)
        return {"success": True, "message": "Server '{}' (PID {}) was already stopped".format(name, pid)}

    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=10)
        else:
            os.kill(pid, signal.SIGTERM)
            time.sleep(2)
            if _is_pid_running(pid):
                os.kill(pid, signal.SIGKILL)

        del pids[name]
        _write_pids(pids)
        log.info("STOP: {} (PID {})".format(name, pid))
        return {"success": True, "message": "Stopped '{}' (PID {})".format(name, pid)}

    except Exception as e:
        log.error("STOP failed for {}: {}".format(name, e))
        return {"success": False, "message": "Failed to stop '{}': {}".format(name, e)}


def reload_all():
    """Reload - stop all tracked servers and restart enabled ones."""
    pids = _read_pids()
    stopped = []
    started = []

    # Stop all tracked
    for name in list(pids.keys()):
        result = stop_server(name)
        if result.get("success"):
            stopped.append(name)

    # Start all enabled
    yaml_path = find_servers_yaml()
    if yaml_path:
        servers = read_yaml_servers(yaml_path)
        for name, config in servers.items():
            if config.get("enabled") and config.get("auto_start") and config.get("command"):
                result = start_server(name)
                if result.get("success"):
                    started.append(name)

    msg = "Reload: stopped {}, started {}".format(len(stopped), len(started))
    log.info(msg)
    return {"success": True, "message": msg}
