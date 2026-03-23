---

name: cloud-claude
description: Launch Claude Code on AWS EC2 spot instances. Auto-provisions everything -- SSH keys, security groups, Docker container with Chrome and MCP servers. Multi-instance support with inter-instance messaging.
keywords:
  - cloud
  - ec2
  - spot
  - remote
  - portable
  - aws
  - cloud-claude
  - launch
  - instance
  - server

---

# Cloud Claude

Launch Claude Code on AWS EC2 spot instances. Fully automated -- from zero to running Claude in one command.

## Prerequisites

- AWS CLI configured (`aws configure` done, with a default region)
- Claude Code running locally (for OAuth token extraction)
- Git installed

## What This Skill Does Automatically

When the user says "launch cloud claude", "spin up a cloud instance", "cloud-claude", etc., do ALL of the following without asking:

### 1. Check/Install Prerequisites

```bash
# Verify AWS CLI works
aws sts get-caller-identity --query Account --output text

# Verify Claude credentials exist locally
cat ~/.claude/.credentials.json 2>/dev/null
```

If AWS CLI is not configured, tell the user to run `aws configure` first. If Claude credentials don't exist, the user needs to log into Claude Code first.

### 2. Clone the Repo (if not already present)

```bash
PROJ_DIR="$HOME/claude-portable"  # or wherever projects live
if [ ! -d "$PROJ_DIR" ]; then
  git clone https://github.com/grobomo/claude-portable.git "$PROJ_DIR"
fi
cd "$PROJ_DIR"
```

### 3. Create SSH Key Pair (if needed)

```bash
KEY_NAME="claude-portable-key"
# Check if key pair exists in AWS
if ! aws ec2 describe-key-pairs --key-names "$KEY_NAME" &>/dev/null; then
  aws ec2 create-key-pair --key-name "$KEY_NAME" --query 'KeyMaterial' --output text > ~/.ssh/claude-portable.pem
  chmod 600 ~/.ssh/claude-portable.pem
  echo "Created SSH key pair: $KEY_NAME"
fi
```

### 4. Write .env with Fresh OAuth Tokens

Extract tokens from the user's running Claude Code session:

```bash
# Read local Claude credentials
CREDS=$(cat ~/.claude/.credentials.json)
ACCESS_TOKEN=$(echo "$CREDS" | python3 -c "import json,sys; print(json.load(sys.stdin)['claudeAiOauth']['accessToken'])")
REFRESH_TOKEN=$(echo "$CREDS" | python3 -c "import json,sys; print(json.load(sys.stdin)['claudeAiOauth']['refreshToken'])")
EXPIRES_AT=$(echo "$CREDS" | python3 -c "import json,sys; print(json.load(sys.stdin)['claudeAiOauth']['expiresAt'])")

# Get GitHub token if available
GH_TOKEN=$(gh auth token 2>/dev/null || echo "")

# Get the repo URL
REPO_URL="https://github.com/grobomo/claude-portable.git"
if [ -n "$GH_TOKEN" ]; then
  REPO_URL="https://x-access-token:${GH_TOKEN}@github.com/grobomo/claude-portable.git"
fi

# Write .env
cat > .env << ENVEOF
CLAUDE_OAUTH_ACCESS_TOKEN=$ACCESS_TOKEN
CLAUDE_OAUTH_REFRESH_TOKEN=$REFRESH_TOKEN
CLAUDE_OAUTH_EXPIRES_AT=$EXPIRES_AT
GITHUB_TOKEN=$GH_TOKEN
REPO_URL=$REPO_URL
ENVEOF
```

### 5. Launch the Instance

```bash
# Use --name if user specified one, otherwise auto-generate
./run.sh --name <name>
```

### 6. Wait for Container to Be Ready

After the CF stack completes, the Docker image still needs to build (~2-3 min). Poll until container is running:

```bash
SSH_KEY="~/.ssh/claude-portable.pem"
# Get IP from stack outputs
IP=$(aws cloudformation describe-stacks --stack-name "claude-portable-<name>" \
  --query "Stacks[0].Outputs[?OutputKey=='PublicIP'].OutputValue" --output text)

# Wait for Docker container
for i in $(seq 1 30); do
  STATUS=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i "$SSH_KEY" ubuntu@$IP \
    "docker ps --filter name=claude-portable --format '{{.Status}}'" 2>/dev/null || echo "")
  if [[ "$STATUS" == Up* ]]; then
    echo "Container is running!"
    break
  fi
  sleep 10
done
```

### 7. Push Fresh Credentials to Container

```bash
# The .env tokens may be stale by the time container builds. Push fresh ones.
CREDS=$(cat ~/.claude/.credentials.json)
ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" ubuntu@$IP \
  "docker exec claude-portable bash -c 'cat > /home/claude/.claude/.credentials.json << CREDEOF
$CREDS
CREDEOF'"
```

### 8. Set Up Trusted Directories

```bash
ssh -i "$SSH_KEY" ubuntu@$IP 'docker exec -u root claude-portable python3 -c "
import json
p = \"/home/claude/.claude/settings.local.json\"
try: d = json.load(open(p))
except: d = {}
d[\"trustedDirectories\"] = [\"/workspace\", \"/home/claude\", \"/tmp\"]
d[\"hasCompletedOnboarding\"] = True
json.dump(d, open(p, \"w\"), indent=2)
"'
```

### 9. Open Terminal Tab (if on Windows Terminal)

```bash
wt.exe -w 0 new-tab --title "<name> ($IP)" ssh -o StrictHostKeyChecking=no -i "$SSH_KEY" ubuntu@$IP -t "docker exec -it claude-portable claude"
```

On macOS/Linux, just print the SSH command.

## Management Commands

When user says "list cloud instances":
```bash
cd <project-dir> && bash list.sh
```

When user says "terminate <name>" or "kill cloud instances":
```bash
cd <project-dir> && bash terminate.sh --name <name>
# or
cd <project-dir> && bash terminate.sh --all
```

When user says "push updates to cloud":
```bash
cd <project-dir> && bash push.sh --all
# or for specific file:
cd <project-dir> && bash push.sh scripts/msg.sh
```

## Inter-Instance Messaging

When user wants instances to communicate, deploy `msg` to instances:
```bash
cd <project-dir> && bash push.sh scripts/msg.sh
```

Then inside each instance:
```bash
msg send <other-instance> "message"
msg inbox
msg who
```

## Important Notes

- Spot instances cost ~$0.03-0.06/hr for t3.large
- OAuth tokens expire every ~5-6 hours -- push fresh credentials if session runs long
- The container has Chrome + Xvfb for headless browser automation
- Session logs persist in Docker volumes but are lost if the EC2 is terminated
- Use `msg` for inter-instance communication (messages go through S3)
