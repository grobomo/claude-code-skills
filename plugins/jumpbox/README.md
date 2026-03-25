# Jumpbox

Windows EC2 jumpbox manager for Claude Code. Provisions Win Server 2022 with Chrome, Git Bash, SSM, and configurable timezone. Handles RDP with auto credential injection and publisher warning bypass.

## Install

Copy the skill to your Claude skills directory:

```bash
cp -r plugins/jumpbox/skills/jumpbox ~/.claude/skills/
bash ~/.claude/skills/jumpbox/install.sh
```

## Setup

```bash
jumpbox setup --name mybox --timezone "Central Standard Time"
```

Creates: EC2 instance, security group, SSH key, IAM role for SSM, installs Chrome + Git Bash.

## Usage

Say "jumpbox" or "rdp" to Claude, or run directly:

```bash
jumpbox              # Connect (starts if stopped, auto-RDP)
jumpbox stop         # Stop ($0/hr)
jumpbox status       # Show state
jumpbox run "cmd"    # Run PowerShell via SSM
jumpbox snapshot     # Create EBS snapshot
jumpbox list         # List all jumpboxes
```

## Prerequisites

- AWS CLI configured
- Python 3 with `pywinauto` (auto-installed)

## How it works

1. Setup creates Win2022 EC2 with Chrome, Git Bash, SSM, timezone
2. Config saved to `~/.jumpbox/<name>.json` (no secrets stored)
3. On connect: starts instance, decrypts password live via EC2 API, stores in Windows Credential Manager, trusts self-signed cert, launches mstsc, auto-dismisses publisher warning via pywinauto
