---
name: v1-api
description: Query Vision One APIs directly. Use when user asks about V1, Vision One, alerts, endpoints, threats, blocklist, or security data.
keywords:
  - v1
  - vision
  - workbench
  - alerts
  - oat
  - observed
  - attack
  - techniques
  - endpoints
  - quarantine
  - email
  - blocklist
  - detection
  - network
  - suspicious
---

# Vision One API Skill

Query V1 APIs directly without MCP server overhead.

## Usage

User says: "list alerts", "search endpoint logs", "block this IP", "V1 status", etc.

## First-Time Setup

```bash
python setup.py
```

This prompts for:
- Vision One region (US, EU, JP, etc.)
- API key (from V1 Console > Administration > API Keys)

## How to Use

1. **Find the right API** - Read `api_reference.md` or run `python executor.py --list`
2. **Run the query** - Execute `python executor.py {operation} [params]`

## Quick Reference

```bash
# List operations
python executor.py --list

# List alerts from last 7 days
python executor.py list_alerts days=7 severity=critical limit=10

# Search endpoint logs
python executor.py search_endpoint_logs hours=24 filter="processName:powershell*"

# List OAT detections
python executor.py list_oat days=7 limit=10

# Block an IP
python executor.py add_to_blocklist ioc_type=ip value=192.168.1.100
```

## Folder Structure

```
v1-api/
├── SKILL.md           # This file
├── setup.py           # First-time setup wizard
├── executor.py        # Runs API calls (standalone, no deps except requests/yaml)
├── .env               # V1_API_KEY, V1_REGION (created by setup.py)
├── api_reference.md   # Find the right API by use case
└── api_index/         # YAML configs per operation (74 operations)
    ├── list_alerts/config.yaml
    ├── search_endpoint_logs/config.yaml
    └── ...
```

## Keyword to Operation Map

| User Says | Operation | Notes |
|-----------|-----------|-------|
| workbench, alerts, workbench alerts | `list_alerts` | Workbench = Alerts in V1 |
| OAT, observed attack techniques, OAT detections | `list_oat` | |
| email, quarantine, quarantined emails | `search_email_logs` | Filter by scanType or action |
| endpoint logs, process, powershell | `search_endpoint_logs` | |
| network logs, network detection | `search_network_logs` | |
| blocklist, block IP, block domain | `add_to_blocklist` | |
| suspicious object, suspicious objects | `list_suspicious_objects` | |
| endpoints, agents, endpoint list | `list_endpoints` | |

## Common Operations

| Task | Operation | Key Params |
|------|-----------|------------|
| List alerts | `list_alerts` | days, severity, status, limit |
| List OAT | `list_oat` | days, limit |
| Search endpoint logs | `search_endpoint_logs` | hours, filter |
| Search network logs | `search_network_logs` | hours, filter |
| Block IOC | `add_to_blocklist` | ioc_type, value |
| List endpoints | `list_endpoints` | limit |
| Get high-risk users | `list_high_risk_users` | risk_score, limit |

## API Key Permissions

For full access, create an API key with:
- Workbench (View, Filter)
- Attack Surface Risk Management (View)
- Observed Attack Techniques (View)
- Response Management (View, Filter, Run response actions)

For full API list, read `api_reference.md`.

## Tips

- **Auto-pagination:** All list/search operations automatically follow `nextLink` and poll `progressRate` to return complete results in a single call. No need for manual page-by-page fetching.
- **Product questions?** Use the **TrendGPT MCP** (`trendgpt`) for V1 product documentation, feature explanations, how-to guides, and best practices. v1-api is for querying live data; TrendGPT is for understanding the product.
