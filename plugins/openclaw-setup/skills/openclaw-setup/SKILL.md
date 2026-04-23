---
name: openclaw-setup
description: Install and configure OpenClaw AI assistant with guided setup, secure secret management, and repeatable automation
triggers:
  - install openclaw
  - setup openclaw
  - deploy openclaw
  - openclaw setup
  - configure openclaw
  - openclaw install
---

# OpenClaw Setup Skill

You help users install, configure, and maintain OpenClaw -- a self-hosted AI assistant
that connects to messaging platforms (Slack, Discord, Telegram, Signal, WhatsApp, etc.).

## What You Do

1. **Install OpenClaw** on macOS, Linux, or WSL2 (Windows)
2. **Interview the user** about their preferences:
   - Model provider (Anthropic, OpenAI, OpenRouter, custom endpoint, Ollama)
   - Which channels to connect (Slack, Discord, Telegram, Signal, etc.)
   - Guide them to get tokens (with links to official setup pages)
3. **Configure everything** using `openclaw config set` commands (NEVER edit JSON directly)
4. **Store secrets securely** in `~/.openclaw/.env` with proper permissions
5. **Verify the deployment** with `openclaw doctor` and `openclaw gateway status`
6. **Track all changes** in a local git repo for rollback capability

## Critical Rules

### Secret Safety
- NEVER store API keys, tokens, or passwords in `openclaw.json`
- ALWAYS use env var references: `${VAR_NAME}` in config, actual values in `~/.openclaw/.env`
- Set `chmod 600 ~/.openclaw/.env` and `chmod 700 ~/.openclaw/`
- Tell users to NEVER commit `.env` files to git

### Config Safety (Prevents the #1 OpenClaw Failure Mode)
- ALWAYS use `openclaw config set` to change configuration
- NEVER edit `openclaw.json` directly (agents corrupt JSON syntax -- Bug #6028)
- ALWAYS stop gateway before manual config edits: `openclaw gateway stop`
- Run `openclaw config validate` after any changes
- Run `openclaw doctor --fix` to catch schema drift

### Recovery
If config gets corrupted:
```bash
openclaw doctor --fix                                          # auto-repair
cp ~/.openclaw/openclaw.json.bak ~/.openclaw/openclaw.json     # restore backup
openclaw config validate                                       # verify
```

## Setup Flow

```
1. Check Node.js 22.16+ installed
2. Install: npm install -g openclaw@latest
3. Onboard: openclaw onboard --install-daemon
4. Configure model provider via openclaw config set
5. Store API keys in ~/.openclaw/.env
6. Configure channels via openclaw config set
7. Store channel tokens in ~/.openclaw/.env
8. Start: openclaw gateway start
9. Verify: openclaw doctor && openclaw gateway status
```

## Automation Script

For batch deployments, run:
```bash
bash scripts/openclaw-setup.sh [--config config.env] [--skip-install] [--dry-run]
```

The script interviews the user, stores secrets securely, configures via CLI, and verifies.

## Channel Token Guide

### Slack
1. Create app at https://api.slack.com/apps
2. Enable Socket Mode -> get App Token (xapp-...)
3. Add Bot Token Scopes: chat:write, channels:history, groups:history, im:history, users:read
4. Install to workspace -> get Bot Token (xoxb-...)
5. Store both in ~/.openclaw/.env

### Telegram
1. Message @BotFather on Telegram
2. /newbot -> follow prompts -> copy token
3. Store in ~/.openclaw/.env as TELEGRAM_BOT_TOKEN

### Discord
1. https://discord.com/developers/applications -> New Application
2. Bot section -> Reset Token -> copy
3. Enable Message Content Intent
4. Store in ~/.openclaw/.env as DISCORD_BOT_TOKEN

### Signal
- Uses signal-cli, no token needed
- Default pairing mode: unknown senders get a pairing code

## Reference
- [Official Docs](https://docs.openclaw.ai/start/getting-started)
- [Configuration Reference](https://docs.openclaw.ai/gateway/configuration)
- [Security Guide](https://www.freecodecamp.org/news/how-to-build-and-secure-a-personal-ai-agent-with-openclaw/)
- [Production Gotchas](https://kaxo.io/insights/openclaw-production-gotchas/)
