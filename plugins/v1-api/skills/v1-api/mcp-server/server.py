#!/usr/bin/env python3
"""
v1-lite - Lightweight Vision One API Wrapper

YAML-driven router for all Vision One API operations.
Operations are defined in api_index/*.yaml files.
Templates in templates/ handle common API patterns.

## Usage
    v1("list_alerts", {"days": 7, "severity": "critical"})
    v1("search_endpoint_logs", {"hours": 24, "limit": 100})
    v1("get_device", {"device_id": "abc-123"})

## Structure
    api_index/          - YAML files per API endpoint
    templates/          - Python templates for API patterns
    api_reference.md    - Quick reference by use case
"""

import os
import json
import yaml
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

# Load environment
# Try credential store first (if super-manager installed), fall back to plain .env
import sys as _sys
try:
    _sys.path.insert(0, os.path.expanduser('~/.claude/super-manager/credentials'))
    from claude_cred import load_env
    load_env()
except (ImportError, FileNotFoundError):
    _env_file = Path(__file__).parent / ".env"
    if _env_file.exists():
        for line in _env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

# Import templates
from templates.base import api_request, get_base_url, get_headers
from templates.base import build_date_range, build_pagination, build_odata_filters


# ============ YAML Loading ============

API_INDEX_DIR = Path(__file__).parent / "api_index"
OPERATIONS: Dict[str, dict] = {}

# API Groups for test organization
API_GROUPS = {
    "ALERTS_ACTIVITY_LOGS": {
        "description": "Workbench alerts, OAT detections, and activity log searches",
        "apis": ["list_alerts", "get_alert", "get_alert_notes", "update_alert", "add_alert_note",
                 "list_oat", "search_endpoint_logs", "search_network_logs", "search_email_logs",
                 "search_identity_logs", "search_cloud_audit_logs", "search_mobile_logs"]
    },
    "ASSET_INVENTORY": {
        "description": "Endpoint and asset management",
        "apis": ["list_endpoints", "get_endpoint", "list_devices", "get_device", "list_cloud_assets"]
    },
    "RISK_MANAGEMENT": {
        "description": "Attack surface and risk scoring",
        "apis": ["list_high_risk_users", "list_domain_accounts", "list_public_ips", "list_fqdns", "list_local_apps"]
    },
    "THREAT_INTEL": {
        "description": "IOC and threat intelligence",
        "apis": ["list_blocklist", "add_to_blocklist", "remove_from_blocklist", "list_intel_reports", "get_sandbox_result"]
    },
    "CLOUD_SECURITY": {
        "description": "Cloud accounts and posture",
        "apis": ["list_aws_accounts", "list_gcp_accounts", "list_azure_accounts", "list_cspm_accounts", "list_k8s_clusters"]
    },
    "RESPONSE_ACTIONS": {
        "description": "Endpoint and email response",
        "apis": ["isolate_endpoint", "restore_endpoint", "collect_file", "terminate_process", "quarantine_email"]
    },
    "EMAIL_SECURITY": {
        "description": "Cloud Email and Collaboration Protection (CECP)",
        "apis": ["list_email_accounts", "list_email_domains"]
    },
    "ADMIN": {
        "description": "Administration and IAM",
        "apis": ["list_accounts", "list_roles", "list_api_keys"]
    }
}

# Performance metrics tracking
METRICS = {
    "calls": 0,
    "errors": 0,
    "total_time_ms": 0,
    "by_operation": {}
}


def load_operations():
    """Load all operations from YAML files.

    Supports two structures:
    - api_index/operation.yaml (legacy flat files)
    - api_index/operation/config.yaml (new folder structure with example.py, response.json)
    """
    global OPERATIONS
    OPERATIONS = {}

    # Load flat YAML files (legacy)
    for yaml_file in API_INDEX_DIR.glob("*.yaml"):
        if yaml_file.name.startswith("_"):
            continue

        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "name" in data:
                    OPERATIONS[data["name"]] = data
        except Exception as e:
            print(f"Warning: Failed to load {yaml_file.name}: {e}")

    # Load folder-based configs (new structure, takes precedence)
    for folder in API_INDEX_DIR.iterdir():
        if not folder.is_dir() or folder.name.startswith("_"):
            continue

        config_file = folder / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "name" in data:
                        OPERATIONS[data["name"]] = data
            except Exception as e:
                print(f"Warning: Failed to load {config_file}: {e}")

    return len(OPERATIONS)


# Load operations at module init
op_count = load_operations()


# ============ Template Execution ============

def substitute_path_params(endpoint: str, params: dict) -> str:
    """Substitute path parameters like {alert_id} with actual values."""
    result = endpoint
    for key in list(params.keys()):
        placeholder = f"{{{key}}}"
        if placeholder in result:
            result = result.replace(placeholder, str(params.pop(key)))
    return result


def execute_standard_list(endpoint: str, params: dict, config: dict) -> dict:
    """Execute standard list API call."""
    query_params = {}

    # Build date range
    date_cfg = config.get("date_params")
    if date_cfg:
        unit = date_cfg.get("unit", "days")
        if unit == "days" and "days" in params:
            end = datetime.utcnow()
            start = end - timedelta(days=params.pop("days"))
            query_params[date_cfg["start"]] = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            query_params[date_cfg["end"]] = end.strftime('%Y-%m-%dT%H:%M:%SZ')
        elif unit == "hours" and "hours" in params:
            end = datetime.utcnow()
            start = end - timedelta(hours=params.pop("hours"))
            query_params[date_cfg["start"]] = start.strftime('%Y-%m-%dT%H:%M:%SZ')
            query_params[date_cfg["end"]] = end.strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        params.pop("days", None)
        params.pop("hours", None)

    # Build pagination
    pag = config.get("pagination")
    if pag and "limit" in params:
        limit = params.pop("limit")
        if pag.get("type") == "enum" and "values" in pag:
            values = pag["values"]
            top_val = min(values, key=lambda x: abs(x - limit) if limit <= x else float('inf'))
            if limit > max(values):
                top_val = max(values)
            query_params[pag["param"]] = str(top_val)
        elif pag.get("type") == "int" and "max" in pag:
            query_params[pag["param"]] = str(min(limit, pag["max"]))
    elif "limit" in params:
        params.pop("limit")

    # Build OData filters
    filters = []
    filter_mappings = {
        "severity": "severity eq '{}'",
        "status": "investigationStatus eq '{}'",
        "risk_level": "riskLevel eq '{}'",
        "provider": "provider eq '{}'",
        "ioc_type": "type eq '{}'",
        "endpoint_name": "endpointName eq '{}'",
        "key": "key eq '{}'",
    }
    for param, template in filter_mappings.items():
        if param in params and params[param]:
            filters.append(template.format(params.pop(param)))

    if "risk_score" in params and params["risk_score"] > 0:
        filters.append(f"latestRiskScore ge {params.pop('risk_score')}")

    if "filter" in params and params["filter"]:
        filters.append(params.pop("filter"))
    elif "filter" in params:
        params.pop("filter")

    # Handle different filter styles
    extra_headers = {}
    filter_style = config.get("filter_style", "odata")

    if filters:
        filter_expr = " and ".join(filters)
        if filter_style == "odata":
            query_params["filter"] = filter_expr
        elif filter_style == "header":
            # Some APIs (like OAT) use TMV1-Filter header instead of query param
            filter_header = config.get("filter_header", "TMV1-Filter")
            extra_headers[filter_header] = filter_expr

    if config.get("order_by"):
        query_params["orderBy"] = config["order_by"]

    return api_request("GET", endpoint, params=query_params, headers=extra_headers if extra_headers else None)


def execute_search(endpoint: str, params: dict, config: dict) -> dict:
    """Execute search API call with TMV1-Query header."""
    query_params = {}
    extra_headers = {}

    # Build date range (hours)
    date_cfg = config.get("date_params")
    if date_cfg and "hours" in params:
        end = datetime.utcnow()
        start = end - timedelta(hours=params.pop("hours"))
        query_params[date_cfg["start"]] = start.strftime('%Y-%m-%dT%H:%M:%SZ')
        query_params[date_cfg["end"]] = end.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Build pagination
    pag = config.get("pagination")
    if pag and "limit" in params:
        limit = params.pop("limit")
        query_params[pag["param"]] = str(min(limit, pag.get("max", 200)))
    elif "limit" in params:
        params.pop("limit")

    # Handle TMV1-Query header
    if "filter" in params and params["filter"]:
        extra_headers["TMV1-Query"] = params.pop("filter")
    else:
        params.pop("filter", None)
        extra_headers["TMV1-Query"] = config.get("default_filter", "*")

    return api_request("GET", endpoint, params=query_params, headers=extra_headers)


def execute_single_get(endpoint: str, params: dict, config: dict) -> dict:
    """Execute single resource GET."""
    return api_request("GET", endpoint, params=params if params else None)


def execute_simple_list(endpoint: str, params: dict, config: dict) -> dict:
    """Execute simple list with no params."""
    return api_request("GET", endpoint)


def execute_response_action(endpoint: str, params: dict, config: dict) -> dict:
    """Execute response action POST with array body."""
    builder_name = config.get("body_builder", "endpoint_action")

    body_builders = {
        "endpoint_action": lambda p: [{"agentGuid": p["endpoint_guid"], "description": p.get("description", "")}],
        "file_collect": lambda p: [{"agentGuid": p["endpoint_guid"], "filePath": p["file_path"], "description": p.get("description", "")}],
        "process_terminate": lambda p: [{"agentGuid": p["endpoint_guid"], "fileSha1": p["file_sha1"], "description": p.get("description", "")}],
        "email_action": lambda p: [{"messageId": p["message_id"], "mailbox": p["mailbox"], "description": p.get("description", "")}],
        "blocklist_add": lambda p: [{"type": p["ioc_type"], "value": p["value"], "riskLevel": p.get("risk_level", "high"), "description": p.get("description", ""), "daysToExpiration": p.get("days_to_expiration", 0)}],
        "blocklist_remove": lambda p: [{"type": p["ioc_type"], "value": p["value"]}],
    }

    builder = body_builders.get(builder_name)
    if not builder:
        return {"error": f"Unknown body builder: {builder_name}"}

    return api_request("POST", endpoint, body=builder(params))


def execute_post_action(endpoint: str, params: dict, config: dict) -> dict:
    """Execute POST action with object body."""
    builder_name = config.get("body_builder", "empty")

    body_builders = {
        "alert_note": lambda p: {"content": p["content"]},
        "script_run": lambda p: {"scriptId": p["script_id"], "agentGuids": p["endpoint_guids"], "parameter": p.get("parameters", "")},
        "iac_scan": lambda p: {"type": p["template_type"], "content": p["content"]},
        "empty": lambda p: {},
    }

    builder = body_builders.get(builder_name, body_builders["empty"])
    return api_request("POST", endpoint, body=builder(params))


def execute_patch_update(endpoint: str, params: dict, config: dict) -> dict:
    """Execute PATCH update."""
    builder_name = config.get("body_builder", "alert_update")

    body_builders = {
        "alert_update": lambda p: {"investigationStatus": p.get("status"), **({"investigationResult": p["result"]} if p.get("result") else {})},
    }

    builder = body_builders.get(builder_name)
    if not builder:
        return {"error": f"Unknown body builder: {builder_name}"}

    return api_request("PATCH", endpoint, body=builder(params))


TEMPLATE_EXECUTORS = {
    "standard_list": execute_standard_list,
    "search": execute_search,
    "single_get": execute_single_get,
    "simple_list": execute_simple_list,
    "response_action": execute_response_action,
    "post_action": execute_post_action,
    "patch_update": execute_patch_update,
}


# ============ Validation ============

def validate_params(operation: str, params: dict) -> tuple[bool, str]:
    """Validate parameters against operation schema."""
    if operation not in OPERATIONS:
        similar = [op for op in OPERATIONS if operation.lower() in op.lower()]
        if similar:
            return False, f"Unknown operation '{operation}'. Did you mean: {', '.join(similar[:5])}?"
        return False, f"Unknown operation '{operation}'. Use v1_help() to see available operations."

    op = OPERATIONS[operation]
    schema_params = op.get("params", {})

    # Check required params
    for param_def in schema_params.get("required", []):
        if param_def["name"] not in params:
            return False, f"Missing required parameter: {param_def['name']} ({param_def['description']})"

    # Apply defaults for optional params
    for param_def in schema_params.get("optional", []):
        if param_def["name"] not in params and "default" in param_def:
            params[param_def["name"]] = param_def["default"]

    return True, ""


# ============ Result Formatting ============

def format_result(operation: str, result: dict) -> str:
    """Format API result for human readability."""
    if "error" in result:
        return f"API Error: {result['error']}"

    items = result.get("items", result.get("data", []))
    total = result.get("totalCount", result.get("count", len(items) if isinstance(items, list) else 0))

    if isinstance(items, list) and items:
        lines = [f"Results ({total}):"]
        for item in items[:10]:
            if isinstance(item, dict):
                if "alertId" in item or "workbenchId" in item:
                    lines.append(f"  {item.get('alertId', item.get('workbenchId'))} - {item.get('severity', '')} - {item.get('model', item.get('alertName', ''))[:50]}")
                elif "endpointName" in item:
                    lines.append(f"  {item.get('endpointName')} - {item.get('osPlatform', '')} ({item.get('isolationStatus', '')})")
                elif "deviceName" in item:
                    lines.append(f"  {item.get('deviceName')} - Risk: {item.get('latestRiskScore', 'N/A')}")
                elif "value" in item and "type" in item:
                    lines.append(f"  [{item.get('type')}] {item.get('value')[:50]}")
                else:
                    lines.append(f"  {json.dumps(item)[:100]}...")
            else:
                lines.append(f"  {str(item)[:100]}")
        if len(items) > 10:
            lines.append(f"  ... and {len(items) - 10} more")
        return "\n".join(lines)
    elif isinstance(result, dict):
        return json.dumps(result, indent=2)[:1000]
    else:
        return str(result)[:1000]


# ============ MCP Server ============

def generate_instructions() -> str:
    """Generate instructions from loaded operations."""
    lines = [
        "# V1-Lite MCP Server",
        "",
        f"YAML-driven router for {len(OPERATIONS)} Vision One API operations.",
        "",
        "## Usage",
        "  v1('list_alerts', {'days': 7, 'severity': 'critical'})",
        "  v1('search_endpoint_logs', {'hours': 24, 'limit': 100})",
        "",
        "## Templates",
    ]

    # Count by template
    template_counts = {}
    for op in OPERATIONS.values():
        tmpl = op.get("template", "unknown")
        template_counts[tmpl] = template_counts.get(tmpl, 0) + 1

    for tmpl, count in sorted(template_counts.items()):
        lines.append(f"  - {tmpl}: {count} operations")

    lines.extend([
        "",
        "## Quick Reference",
        "See api_reference.md for use-case based groupings.",
        "",
        "Use v1_help() to list all operations.",
        "Use v1_help('operation_name') for detailed help.",
    ])

    return "\n".join(lines)


mcp = FastMCP("v1-lite", instructions=generate_instructions())


@mcp.tool()
def v1(operation: str, params: dict = {}) -> str:
    """Execute Vision One API operation.

    Args:
        operation: Operation name (e.g., 'list_alerts', 'get_device')
        params: Operation parameters as dict

    Returns:
        Formatted API response

    Examples:
        v1("list_alerts", {"days": 7, "severity": "critical"})
        v1("search_endpoint_logs", {"hours": 24, "limit": 100})
        v1("get_device", {"device_id": "abc-123"})
    """
    import time
    start_time = time.time()

    # Make a copy to avoid mutating original
    params = dict(params)

    # Validate
    valid, error = validate_params(operation, params)
    if not valid:
        METRICS["calls"] += 1
        METRICS["errors"] += 1
        return f"Validation Error: {error}\n\nTIP: Use v1_help('{operation}') for parameter documentation"

    op = OPERATIONS[operation]
    template = op.get("template", "standard_list")
    config = op.get("template_config", {})

    # Substitute path parameters
    endpoint = substitute_path_params(op["endpoint"], params)

    # Get executor
    executor = TEMPLATE_EXECUTORS.get(template)
    if not executor:
        return f"Unknown template: {template}"

    # Execute
    result = executor(endpoint, params, config)

    # Track metrics
    elapsed_ms = int((time.time() - start_time) * 1000)
    METRICS["calls"] += 1
    METRICS["total_time_ms"] += elapsed_ms
    if "error" in result:
        METRICS["errors"] += 1

    if operation not in METRICS["by_operation"]:
        METRICS["by_operation"][operation] = {"calls": 0, "errors": 0, "total_ms": 0, "last_ms": 0}
    op_metrics = METRICS["by_operation"][operation]
    op_metrics["calls"] += 1
    op_metrics["total_ms"] += elapsed_ms
    op_metrics["last_ms"] = elapsed_ms
    if "error" in result:
        op_metrics["errors"] += 1

    return format_result(operation, result)


@mcp.tool()
def v1_help(operation: str = "") -> str:
    """Get help on Vision One operations.

    Args:
        operation: Specific operation name, or empty for overview

    Returns:
        Help text with parameters and examples
    """
    if not operation:
        # List all operations grouped by template
        by_template = {}
        for op_name, op_def in OPERATIONS.items():
            tmpl = op_def.get("template", "unknown")
            if tmpl not in by_template:
                by_template[tmpl] = []
            by_template[tmpl].append(op_name)

        lines = [f"# V1-Lite Operations ({len(OPERATIONS)} total)", ""]
        for tmpl, ops in sorted(by_template.items()):
            lines.append(f"## {tmpl} ({len(ops)})")
            for op in sorted(ops):
                desc = OPERATIONS[op].get("description", "")[:40]
                lines.append(f"  - {op}: {desc}")
            lines.append("")
        return "\n".join(lines)

    if operation not in OPERATIONS:
        return f"Unknown operation: {operation}"

    op = OPERATIONS[operation]
    lines = [
        f"# {operation}",
        "",
        f"**Description:** {op.get('description', '')}",
        f"**Template:** {op.get('template', '')}",
        f"**Method:** {op.get('method', '')}",
        f"**Endpoint:** {op.get('endpoint', '')}",
    ]

    # Test status
    test = op.get("test", {})
    if test:
        lines.append(f"**Test Status:** {test.get('status', 'untested')} (last: {test.get('last_run', 'never')})")

    lines.append("")
    lines.append("## Parameters")

    params = op.get("params", {})
    for param in params.get("required", []):
        lines.append(f"  - **{param['name']}** ({param.get('type', 'str')}, required): {param.get('description', '')}")
    for param in params.get("optional", []):
        lines.append(f"  - **{param['name']}** ({param.get('type', 'str')}, default={param.get('default', 'none')}): {param.get('description', '')}")

    # Notes/gotchas
    notes = op.get("notes", [])
    if notes:
        lines.append("")
        lines.append("## Gotchas")
        for note in notes:
            lines.append(f"  - {note}")

    # Example
    example = op.get("example_request", {}).get("params", {})
    if example:
        lines.append("")
        lines.append("## Example")
        lines.append(f"  v1('{operation}', {json.dumps(example)})")

    # Categories
    categories = op.get("categories", [])
    if categories:
        lines.append("")
        lines.append(f"## Categories: {', '.join(categories)}")

    return "\n".join(lines)


@mcp.tool()
def v1_reload() -> str:
    """Reload operations from YAML files.

    Use after modifying api_index/*.yaml files.

    Returns:
        Count of loaded operations
    """
    count = load_operations()
    return f"Reloaded {count} operations from {API_INDEX_DIR}"


@mcp.tool()
def v1_metrics(reset: bool = False) -> str:
    """Get API performance metrics and statistics.

    Args:
        reset: If True, reset all metrics after returning

    Returns:
        Performance report with call counts, error rates, and timing

    Use for:
        - Monitoring API health
        - Identifying slow endpoints
        - Tracking error rates over time
    """
    lines = ["# V1-Lite API Metrics", ""]

    # Overall stats
    total_calls = METRICS["calls"]
    total_errors = METRICS["errors"]
    total_time = METRICS["total_time_ms"]
    error_rate = (total_errors / total_calls * 100) if total_calls > 0 else 0
    avg_time = (total_time / total_calls) if total_calls > 0 else 0

    lines.append("## Summary")
    lines.append(f"  Total calls: {total_calls}")
    lines.append(f"  Total errors: {total_errors} ({error_rate:.1f}%)")
    lines.append(f"  Total time: {total_time}ms")
    lines.append(f"  Avg response: {avg_time:.0f}ms")
    lines.append("")

    # Per-operation stats (sorted by call count)
    if METRICS["by_operation"]:
        lines.append("## By Operation (sorted by calls)")
        lines.append("```")
        lines.append(f"{'Operation':<35} {'Calls':>6} {'Errors':>7} {'Avg ms':>8} {'Last ms':>8}")
        lines.append("-" * 70)

        sorted_ops = sorted(
            METRICS["by_operation"].items(),
            key=lambda x: x[1]["calls"],
            reverse=True
        )

        for op_name, stats in sorted_ops[:20]:
            avg = stats["total_ms"] / stats["calls"] if stats["calls"] > 0 else 0
            lines.append(f"{op_name:<35} {stats['calls']:>6} {stats['errors']:>7} {avg:>8.0f} {stats['last_ms']:>8}")

        lines.append("```")
        lines.append("")

        # Slowest operations
        lines.append("## Slowest Operations (by avg response)")
        lines.append("```")
        slowest = sorted(
            [(op, s["total_ms"] / s["calls"]) for op, s in METRICS["by_operation"].items() if s["calls"] > 0],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        for op_name, avg_ms in slowest:
            lines.append(f"  {op_name}: {avg_ms:.0f}ms avg")
        lines.append("```")

    if reset:
        METRICS["calls"] = 0
        METRICS["errors"] = 0
        METRICS["total_time_ms"] = 0
        METRICS["by_operation"] = {}
        lines.append("")
        lines.append("_Metrics reset_")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
