---
name: v1-api
description: Query Vision One APIs directly. Use when user asks about V1, Vision One, alerts, endpoints, threats, blocklist, or security data.
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

## Saved Queries (Ready-to-Run Scripts)

Pre-built scripts for common V1 admin tasks. Run directly or share with colleagues.

| Script | Description | Usage |
|--------|-------------|-------|
| `spf_check.py` | SPF/DKIM/DMARC authentication report — counts failures by domain, day, sender IP. Outputs CSV. | `python saved-queries/spf_check.py --days 30` |

Output CSVs are saved to `reports/`.

**To add more:** Drop a Python script in `saved-queries/`. It should use `V1_API_KEY` config at top (same pattern as spf_check.py) so users just paste their key and run.

### Planned saved queries:
- `oat_report.py` — OAT detection summary by technique, severity, endpoint
- `policy_review.py` — Best practice review of email/endpoint security policies
- `endpoint_health.py` — Agent connectivity and version compliance report

## Folder Structure

```
v1-api/
├── SKILL.md           # This file
├── setup.py           # First-time setup wizard
├── executor.py        # Runs API calls (standalone, no deps except requests/yaml)
├── .env               # V1_API_KEY, V1_REGION (created by setup.py)
├── api_reference.md   # Find the right API by use case
├── api_index/         # YAML configs per operation (74 operations)
│   ├── list_alerts/config.yaml
│   ├── search_endpoint_logs/config.yaml
│   └── ...
├── saved-queries/     # Ready-to-run scripts for V1 admins
│   └── spf_check.py  # Email auth (SPF/DKIM/DMARC) report
└── reports/           # Output directory for CSV/JSON results
```

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
