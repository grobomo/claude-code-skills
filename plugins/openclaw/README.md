# openclaw

Talk to local OpenClaw instances via HTTP API. OpenAI-compatible chat completions endpoint running in WSL.

## Install

```bash
claude plugin marketplace add grobomo/claude-code-skills
claude plugin install openclaw@grobomo-marketplace --scope user
```

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
TOKEN=$(wsl -e bash -c "cat ~/.openclaw/openclaw.json | python3 -c \"import sys,json; print(json.load(sys.stdin)['auth']['token'])\"")
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

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401 Unauthorized` | Add `Authorization: Bearer <token>` header |
| `Connection refused` on `:18789` | Start gateway: `wsl -e systemctl --user restart openclaw-gateway` |
| Slow first response | Gateway cold start; subsequent requests are fast |
| Token not found in config | Check `wsl -e cat ~/.openclaw/openclaw.json` |

## Reference

- Source: [grobomo/openclaw-skill](https://github.com/grobomo/openclaw-skill)
- OpenClaw docs: https://docs.openclaw.ai/cli
