#!/usr/bin/env node
/**
 * mcp-manager setup
 * Auto-configures the mcpm MCP server on plugin install.
 *
 * Strategy:
 *   1. Backup existing settings.json and .mcp.json
 *   2. npm install runtime deps (same directory as build/index.js)
 *   3. Add mcp-manager to settings.json mcpServers
 *   4. Copy template servers.yaml if none exists
 *   5. Create instruction files OR inject CLAUDE.md fallback
 *
 * Pure Node.js (fs, path, os, child_process) - no external dependencies.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

function log(msg) { console.log('[mcp-manager:setup] ' + msg); }
function warn(msg) { console.warn('[mcp-manager:setup:warn] ' + msg); }

// ---- Paths ----

const SKILL_DIR = __dirname;
const BUILD_INDEX = path.join(SKILL_DIR, 'build', 'index.js');
const HOME = os.homedir();
const CLAUDE_DIR = path.join(HOME, '.claude');
const SETTINGS_PATH = path.join(CLAUDE_DIR, 'settings.json');
const CLAUDE_MD_PATH = path.join(CLAUDE_DIR, 'CLAUDE.md');
const INSTRUCTIONS_DIR = path.join(CLAUDE_DIR, 'instructions', 'UserPromptSubmit');
const BACKUPS_DIR = path.join(CLAUDE_DIR, 'backups', 'mcp-manager');

// ---- Backup & Restore ----

function createBackup() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const backupDir = path.join(BACKUPS_DIR, timestamp);
  fs.mkdirSync(backupDir, { recursive: true });

  const manifest = { timestamp, files: {}, created: [] };

  // Backup settings.json
  if (fs.existsSync(SETTINGS_PATH)) {
    const dest = path.join(backupDir, 'settings.json');
    fs.copyFileSync(SETTINGS_PATH, dest);
    manifest.files['settings.json'] = SETTINGS_PATH;
    log('Backed up settings.json');
  }

  // Backup CLAUDE.md
  if (fs.existsSync(CLAUDE_MD_PATH)) {
    const dest = path.join(backupDir, 'CLAUDE.md');
    fs.copyFileSync(CLAUDE_MD_PATH, dest);
    manifest.files['CLAUDE.md'] = CLAUDE_MD_PATH;
    log('Backed up CLAUDE.md');
  }

  // Backup project .mcp.json if it exists
  const mcpJsonPath = path.join(process.cwd(), '.mcp.json');
  if (fs.existsSync(mcpJsonPath)) {
    const dest = path.join(backupDir, 'mcp.json');
    fs.copyFileSync(mcpJsonPath, dest);
    manifest.files['mcp.json'] = mcpJsonPath;
    log('Backed up .mcp.json');
  }

  fs.writeFileSync(path.join(backupDir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
  log('Backup dir: ' + backupDir);
  return { backupDir, manifest };
}

function trackCreatedFile(backupDir, filePath) {
  const manifestPath = path.join(backupDir, 'manifest.json');
  try {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    if (!manifest.created) manifest.created = [];
    manifest.created.push(filePath);
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), 'utf8');
  } catch {}
}

// ---- Step 1: Install npm dependencies ----

function installDeps() {
  if (!fs.existsSync(path.join(SKILL_DIR, 'package.json'))) {
    warn('No package.json found - skipping npm install');
    return false;
  }

  const nodeModules = path.join(SKILL_DIR, 'node_modules');
  const requiredPkgs = ['@modelcontextprotocol/sdk', 'yaml', 'zod'];
  const allInstalled = requiredPkgs.every(pkg => {
    try {
      const pkgPath = path.join(nodeModules, ...pkg.split('/'));
      return fs.existsSync(pkgPath);
    } catch { return false; }
  });

  if (allInstalled) {
    log('Dependencies already installed');
    return true;
  }

  log('Installing npm dependencies...');
  try {
    execSync('npm install --production --no-optional', {
      cwd: SKILL_DIR,
      stdio: 'pipe',
      timeout: 120000,
    });
    log('Dependencies installed');
    return true;
  } catch (e) {
    warn('npm install failed: ' + e.message);
    return false;
  }
}

// ---- Step 2: Configure settings.json ----

function configureSettings(backupDir) {
  const indexPath = BUILD_INDEX.replace(/\\/g, '/');

  if (!fs.existsSync(indexPath)) {
    warn('build/index.js not found at ' + indexPath);
    return false;
  }

  if (!fs.existsSync(CLAUDE_DIR)) {
    fs.mkdirSync(CLAUDE_DIR, { recursive: true });
  }

  let settings = {};
  try {
    settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8'));
  } catch {}

  if (!settings.mcpServers) settings.mcpServers = {};

  if (settings.mcpServers['mcp-manager']) {
    log('mcp-manager already in settings.json');
    return true;
  }

  settings.mcpServers['mcp-manager'] = {
    command: 'node',
    args: [indexPath],
    env: {},
    servers: [],
  };

  fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2), 'utf8');
  log('Added mcp-manager to ' + SETTINGS_PATH);
  return true;
}

// ---- Step 3: Configure .mcp.json (project-level) ----

function configureProjectMcpJson() {
  const mcpJsonPath = path.join(process.cwd(), '.mcp.json');
  const indexPath = BUILD_INDEX.replace(/\\/g, '/');

  let content = { mcpServers: {} };
  try {
    content = JSON.parse(fs.readFileSync(mcpJsonPath, 'utf8'));
    if (!content.mcpServers) content.mcpServers = {};
  } catch {}

  if (content.mcpServers['mcp-manager']) {
    log('.mcp.json already has mcp-manager');
    return true;
  }

  content.mcpServers['mcp-manager'] = {
    command: 'node',
    args: [indexPath],
    env: {},
    servers: [],
  };

  fs.writeFileSync(mcpJsonPath, JSON.stringify(content, null, 2) + '\n', 'utf8');
  log('Added mcp-manager to ' + mcpJsonPath);
  return true;
}

// ---- Step 4: Copy servers.yaml template ----

function copyServersYaml() {
  const templatePath = path.join(SKILL_DIR, 'servers.yaml');

  if (!fs.existsSync(templatePath)) {
    warn('No servers.yaml template found');
    return false;
  }

  log('servers.yaml template ready at ' + templatePath);
  return true;
}

// ---- Step 5: Create instruction files OR CLAUDE.md fallback ----

const INSTRUCTIONS = {
  'mcpm-only-in-mcp-json': {
    name: 'Only mcpm in .mcp.json',
    keywords: ['mcp.json', 'mcp server', 'add mcp', 'remote mcp', 'http mcp', 'configure mcp'],
    content: `# Rule: Only mcpm in .mcp.json

## WHY

NEVER add any MCP server entry in .mcp.json except mcp-manager (mcpm). All servers - local stdio, remote HTTP, SSE - must go through mcpm. Single source of truth.

## What To Do

- **NEVER** add a direct MCP server entry to .mcp.json
- **ALWAYS** add servers to mcpm's \`servers\` list in .mcp.json AND configure them in servers.yaml
- If a server needs HTTP/SSE transport, mcpm proxies it natively

## .mcp.json Format (always)

\`\`\`json
{
  "mcpServers": {
    "mcp-manager": {
      "command": "node",
      "args": ["path/to/build/index.js"],
      "servers": ["server1", "server2"]
    }
  }
}
\`\`\`

No other top-level entries. Ever.`,
  },
  'mcpm-reload-flow': {
    name: 'mcpm reload flow',
    keywords: ['reload mcp', 'restart mcp', 'mcp not working', 'reconnect mcp', 'mcp config', 'mcp changed', 'new mcp server'],
    content: `# How to Reload mcpm After Config Changes

## WHY

When servers.yaml or .mcp.json changes, the running mcpm process has stale config.

## Reload Flow

Tell the user to run \`/mcp\`, select \`mcp-manager\`, and click reconnect. Then \`mcpm reload\` picks up servers.yaml changes.

**Steps:**
1. \`/mcp\` -> select mcp-manager -> Reconnect
2. \`mcpm reload\` (picks up servers.yaml changes)
3. \`mcpm start <server>\` (start any new servers)

## NEVER

- Never tell the user to restart Claude Code for mcpm changes
- Never add MCP servers directly to .mcp.json (only mcpm goes there)`,
  },
};

const CLAUDE_MD_MARKER = '<!-- mcp-manager-rules -->';
const CLAUDE_MD_FALLBACK = `
${CLAUDE_MD_MARKER}
## MCP Server Rules (auto-added by mcp-manager)

- All MCP servers managed by mcpm -- NEVER run \`claude mcp add\`, \`mcpm\` in Bash, or edit .mcp.json directly
- Use ONE tool: \`mcp__mcp-manager__mcpm(operation="...")\` -- no other tool names exist
- Add servers to mcpm's \`servers.yaml\` (in the mcp-manager skill directory), then \`/mcp\` -> Reconnect -> reload
- Store tokens via credential-manager if installed, otherwise keep them in servers.yaml env section
- **NEVER** add MCP server entries to .mcp.json except mcp-manager itself
${CLAUDE_MD_MARKER}
`;

function injectClaudeMdFallback(backupDir) {
  // Create CLAUDE.md if it doesn't exist
  if (!fs.existsSync(CLAUDE_MD_PATH)) {
    fs.mkdirSync(path.dirname(CLAUDE_MD_PATH), { recursive: true });
    fs.writeFileSync(CLAUDE_MD_PATH, '', 'utf8');
  }

  const content = fs.readFileSync(CLAUDE_MD_PATH, 'utf8');
  if (content.indexOf(CLAUDE_MD_MARKER) !== -1) {
    log('CLAUDE.md already has mcp-manager rules');
    return false;
  }

  fs.writeFileSync(CLAUDE_MD_PATH, content + CLAUDE_MD_FALLBACK, 'utf8');
  log('Injected MCP rules into CLAUDE.md (no instruction-manager detected)');
  return true;
}

function removeClaudeMdFallback() {
  if (!fs.existsSync(CLAUDE_MD_PATH)) return false;
  const content = fs.readFileSync(CLAUDE_MD_PATH, 'utf8');
  const startIdx = content.indexOf(CLAUDE_MD_MARKER);
  if (startIdx === -1) return false;
  const endIdx = content.indexOf(CLAUDE_MD_MARKER, startIdx + CLAUDE_MD_MARKER.length);
  if (endIdx === -1) return false;
  const endOfMarker = endIdx + CLAUDE_MD_MARKER.length;
  const before = content.slice(0, startIdx).replace(/\n+$/, '\n');
  const after = content.slice(endOfMarker).replace(/^\n+/, '\n');
  fs.writeFileSync(CLAUDE_MD_PATH, before + after, 'utf8');
  return true;
}

function createInstructions(backupDir) {
  if (!fs.existsSync(INSTRUCTIONS_DIR)) {
    log('No instruction-manager found (no ' + INSTRUCTIONS_DIR + ')');
    log('Using CLAUDE.md fallback instead');
    injectClaudeMdFallback(backupDir);
    return false;
  }

  // instruction-manager is installed - use instruction files and clean up any fallback
  removeClaudeMdFallback();

  let created = 0;
  for (const [id, inst] of Object.entries(INSTRUCTIONS)) {
    const filePath = path.join(INSTRUCTIONS_DIR, id + '.md');
    if (fs.existsSync(filePath)) {
      log('Instruction ' + id + ' already exists');
      continue;
    }

    const frontmatter = [
      '---',
      'id: ' + id,
      'name: ' + inst.name,
      'keywords:',
      ...inst.keywords.map(k => '  - ' + k),
      'trigger: always',
      '---',
      '',
    ].join('\n');

    try {
      fs.writeFileSync(filePath, frontmatter + inst.content + '\n', 'utf8');
      created++;
      log('Created instruction: ' + id);
      if (backupDir) trackCreatedFile(backupDir, filePath);
    } catch (e) {
      warn('Failed to create instruction ' + id + ': ' + e.message);
    }
  }

  if (created > 0) log('Created ' + created + ' instruction(s)');
  return true;
}

// ---- Main ----

function main() {
  log('Setting up mcp-manager MCP server...');

  // Verify build exists
  if (!fs.existsSync(BUILD_INDEX)) {
    warn('build/index.js not found at ' + BUILD_INDEX);
    warn('Plugin may be incomplete. Try reinstalling.');
    process.exit(1);
  }
  log('Server: ' + BUILD_INDEX);

  // Step 0: Backup existing config
  const { backupDir } = createBackup();

  // Step 1: Install deps
  const depsOk = installDeps();
  if (!depsOk) {
    warn('Dependencies failed to install. mcpm may not start correctly.');
    warn('Run manually: cd "' + SKILL_DIR + '" && npm install --production');
  }

  // Step 2: Configure settings.json (user-level)
  configureSettings(backupDir);

  // Step 3: Configure .mcp.json (project-level, if in a project)
  const cwdMcpJson = path.join(process.cwd(), '.mcp.json');
  if (fs.existsSync(cwdMcpJson) || fs.existsSync(path.join(process.cwd(), 'CLAUDE.md'))) {
    configureProjectMcpJson();
  }

  // Step 4: servers.yaml
  copyServersYaml();

  // Step 5: Instructions or CLAUDE.md fallback
  createInstructions(backupDir);

  log('');
  log('Setup complete!');
  log('Backup stored at: ' + backupDir);
  log('');
  log('Next steps:');
  log('  1. Run /mcp -> select mcp-manager -> Connect');
  log('  2. Add servers to servers.yaml: ' + path.join(SKILL_DIR, 'servers.yaml'));
  log('  3. mcpm reload -> mcpm start <server>');
  log('');
  log('To add a server:');
  log('  mcpm add my-server --command=python --args=\'["path/to/server.py"]\' --description="My server"');
  log('');
  log('To uninstall:');
  log('  node "' + path.join(SKILL_DIR, 'uninstall.js') + '"');

  // Check what companion plugins are missing and recommend super-manager
  const hasCredentialManager = fs.existsSync(path.join(HOME, '.claude', 'skills', 'credential-manager', 'SKILL.md'));
  const hasSuperManager = fs.existsSync(path.join(HOME, '.claude', 'skills', 'super-manager', 'SKILL.md'))
    || fs.existsSync(path.join(HOME, '.claude', 'super-manager', 'SKILL.md'));
  const hasInstructionManager = fs.existsSync(INSTRUCTIONS_DIR);

  const missing = [];
  if (!hasCredentialManager) missing.push('credential-manager (secure API token storage)');
  if (!hasInstructionManager) missing.push('instruction-manager (context-aware prompt injection)');

  if (missing.length > 0 || !hasSuperManager) {
    log('');
    log('------------------------------------------------------------');
    log('  mcp-manager works standalone, but you will get a better');
    log('  experience with super-manager installed. It includes:');
    if (!hasCredentialManager) log('    - credential-manager: store API tokens in OS keychain');
    if (!hasInstructionManager) log('    - instruction-manager: inject MCP rules on every prompt');
    log('    - skill-manager: auto-detect which tools to use');
    log('    - hook-manager: manage Claude Code hooks safely');
    log('');
    log('  Install super-manager (includes all of the above):');
    log('    claude plugin install super-manager@grobomo-marketplace');
    log('------------------------------------------------------------');
  }
}

module.exports = { main, installDeps, configureSettings, createInstructions, createBackup, removeClaudeMdFallback };

if (require.main === module) {
  main();
}
