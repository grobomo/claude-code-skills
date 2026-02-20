---
name: credential-manager
description: Store and retrieve API tokens/secrets in OS credential store (Windows Credential Manager / macOS Keychain)
keywords:
  - credential
  - secret
  - token
  - store token
  - api key
  - keyring
  - vault
  - migrate credentials
---

# Credential Manager

Stores API tokens/secrets in the OS credential store instead of plaintext files. Part of super-manager.

## Rules

- **NEVER** output credential values in chat, logs, or memory
- **NEVER** read .env files (may contain secrets)

## Storing Credentials

When user wants to store a token/key/secret:

1. Determine key name from context (e.g. "github token" -> `service/VARIABLE`)
2. Launch GUI: `python ~/.claude/super-manager/credentials/store_gui.py KEY_NAME`
3. If key name unclear, omit it -- GUI prompts for both name and value

GUI pops up with masked field. User pastes, clicks Store. Memory zeroed after.

## Commands

```bash
# Store (GUI popup)
python ~/.claude/super-manager/credentials/store_gui.py SERVICE/KEY

# List stored (names only)
python ~/.claude/super-manager/super_manager.py credentials list

# Verify store health
python ~/.claude/super-manager/super_manager.py credentials verify

# Audit .env files for plaintext secrets
python ~/.claude/super-manager/super_manager.py credentials audit

# Migrate .env to credential store
python ~/.claude/super-manager/super_manager.py credentials migrate "/path/.env" SERVICE

# First-time setup
python ~/.claude/super-manager/credentials/setup.py
```

## Integration

### .env files -- non-secrets stay plaintext, secrets use `credential:` prefix:
```
API_URL=https://example.com
API_TOKEN=credential:my-service/API_TOKEN
```

### Python (MCP servers/skills):
```python
import sys, os
sys.path.insert(0, os.path.expanduser('~/.claude/super-manager/credentials'))
from claude_cred import load_env
load_env()  # Resolves credential: prefixes from .env
```

### Node.js:
```javascript
const { loadEnvFile } = require(
  require('path').join(require('os').homedir(), '.claude/super-manager/credentials/claude-cred.js')
);
loadEnvFile(__dirname + '/.env');
```

## Storage

| Platform | Backend | Encryption |
|----------|---------|------------|
| Windows | Credential Manager (DPAPI) | AES-256 tied to user login |
| macOS | Keychain | AES-256 with secure enclave |

Service name: `claude-code`. Key format: `SERVICE/VARIABLE`.

## Files

```
~/.claude/super-manager/credentials/
├── store_gui.py              # Secure GUI for storing credentials
├── claude_cred.py            # Python resolver (credential: prefix)
├── claude-cred.js            # Node.js resolver
├── credential-registry.json  # Key name index (no secrets)
└── setup.py                  # First-time setup + verification
```

Requires `keyring` Python package (auto-installed by setup.py).
