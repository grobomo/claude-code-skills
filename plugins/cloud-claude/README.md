# Cloud Claude

Launch Claude Code on AWS EC2 spot instances with one command. Auto-provisions SSH keys, security groups, Docker container with Chrome and MCP support.

## Features

- One-command launch: `/cloud-claude` or "launch a cloud instance"
- Multi-instance: run multiple named instances simultaneously
- Inter-instance messaging via S3
- Chrome + Xvfb for headless browser automation
- Session logging with persistent storage
- Push updates to running instances
- ~$0.03-0.06/hr on spot pricing

## Prerequisites

- AWS CLI configured (`aws configure`)
- Claude Code running locally (for OAuth token extraction)

## Usage

Just tell Claude: "launch a cloud instance called dev" -- the skill handles everything automatically:
1. Clones the repo
2. Creates SSH key pair if needed
3. Extracts your OAuth tokens
4. Launches a spot EC2 instance
5. Waits for container to be ready
6. Opens a terminal tab with Claude running

## Source

https://github.com/grobomo/claude-portable
