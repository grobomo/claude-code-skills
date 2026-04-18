---
name: openclaw
description: Talk to local OpenClaw instances via HTTP API. OpenAI-compatible chat completions endpoint running in WSL.
keywords:
  - openclaw
  - local llm
  - chat
  - wsl
  - rdsec
---

# OpenClaw Skill

Query local OpenClaw gateway instances via their OpenAI-compatible HTTP API. OpenClaw routes requests to configured LLM backends (e.g. Claude via RDsec).

## Prerequisites

- OpenClaw installed in WSL (`openclaw` binary on PATH)
- Gateway running: `wsl -e systemctl --user status openclaw-gateway`
- Config exists: `~/.openclaw/openclaw.json` (inside WSL)

## API Endpoint

```
POST http://localhost:18789/v1/chat/completions
```

OpenAI-compatible. Works with any HTTP client or OpenAI SDK.

## Authentication

Bearer token required even on localhost. Get it from WSL config:

```bash
# Read token from WSL
TOKEN=$(wsl -e bash -c "cat ~/.openclaw/openclaw.json | python3 -c \"import sys,json; print(json.load(sys.stdin)['auth']['token'])\"")
```

The config file (`~/.openclaw/openclaw.json`) looks like:

```json
{
  "auth": {
    "mode": "token",
    "token": "oc_..."
  }
}
```

## Usage

### curl

```bash
TOKEN=$(wsl -e bash -c "cat ~/.openclaw/openclaw.json | python3 -c \"import sys,json; print(json.load(sys.stdin)['auth']['token'])\"")

curl -s http://localhost:18789/v1/chat/completions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openclaw",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Python (requests)

```python
import json, subprocess, requests

# Get token from WSL
raw = subprocess.check_output(["wsl", "-e", "bash", "-c", "cat ~/.openclaw/openclaw.json"])
token = json.loads(raw)["auth"]["token"]

resp = requests.post(
    "http://localhost:18789/v1/chat/completions",
    headers={"Authorization": f"Bearer {token}"},
    json={"model": "openclaw", "messages": [{"role": "user", "content": "Hello"}]}
)
print(resp.json()["choices"][0]["message"]["content"])
```

### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:18789/v1",
    api_key="oc_..."  # token from openclaw.json
)

response = client.chat.completions.create(
    model="openclaw",
    messages=[{"role": "user", "content": "Hello"}]
)
print(response.choices[0].message.content)
```

## Model

Use `"model": "openclaw"` — this routes to whichever backend is configured in the gateway (currently Claude Opus 4.6 via RDsec).

## Gotchas

1. **Auth required on localhost** — Returns `401 Unauthorized` without Bearer token, even though it's a local service.

2. **CLI vs HTTP are different** — `openclaw agent` CLI requires env vars (`RDSEC_API_KEY`, `SLACK_BOT_TOKEN`) that only the systemd service has. CLI calls fail with missing env warnings. Use the HTTP API instead.

3. **CLI requires flags** — `openclaw agent` needs `--to`, `--session-id`, or `--agent` — there's no default session. Another reason to prefer HTTP.

4. **Gateway must be running** — If requests fail, check the service:
   ```bash
   wsl -e systemctl --user status openclaw-gateway
   # Restart if needed:
   wsl -e systemctl --user restart openclaw-gateway
   ```

5. **WSL proxy warning** — You may see proxy-related warnings from WSL. These are cosmetic and don't affect functionality.

6. **Token path** — The config lives inside WSL at `~/.openclaw/openclaw.json`, not on the Windows filesystem. Access it via `wsl -e cat ...`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401 Unauthorized` | Add `Authorization: Bearer <token>` header |
| `Connection refused` on `:18789` | Start gateway: `wsl -e systemctl --user restart openclaw-gateway` |
| `openclaw agent` fails with env errors | Don't use CLI — use HTTP API |
| Slow first response | Gateway cold start; subsequent requests are fast |
| Token not found in config | Check `wsl -e cat ~/.openclaw/openclaw.json` — verify `auth.token` exists |

## Reference

- OpenClaw docs: https://docs.openclaw.ai/cli
- Config: `wsl -e cat ~/.openclaw/openclaw.json`
- Gateway status: `wsl -e systemctl --user status openclaw-gateway`
