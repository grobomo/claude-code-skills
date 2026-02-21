#!/usr/bin/env node
/**
 * trend-docs-mcp setup
 * Auto-configures the MCP server on plugin install.
 *
 * Strategy:
 *   1. Find the installed server.py path (same directory as this script)
 *   2. If mcpm available: use mcpm to add the server
 *   3. If no mcpm: add directly to ~/.claude/.mcp.json
 *
 * Pure Node.js (fs, path, os, child_process) - no npm dependencies.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const SERVER_NAME = 'trend-docs';
const DESCRIPTION = 'Search and read Trend Micro docs (JS SPA pages via Playwright)';
const REQUIRED_PACKAGES = ['mcp', 'ddgs', 'playwright'];

function log(msg) { console.log('[trend-docs-mcp:setup] ' + msg); }
function warn(msg) { console.warn('[trend-docs-mcp:setup:warn] ' + msg); }

/**
 * Install Python dependencies required by server.py
 */
function installDeps() {
  for (const pkg of REQUIRED_PACKAGES) {
    try {
      execSync(`python -c "import ${pkg === 'mcp' ? 'mcp.server.fastmcp' : pkg}"`, { stdio: 'pipe', timeout: 10000 });
      log(pkg + ': already installed');
    } catch {
      log(pkg + ': installing...');
      try {
        execSync(`python -m pip install ${pkg} -q`, { stdio: 'pipe', timeout: 120000 });
        log(pkg + ': installed');
      } catch (e) {
        warn(pkg + ': install failed - ' + e.message);
      }
    }
  }

  // Playwright needs chromium browser
  try {
    execSync('python -c "from playwright.sync_api import sync_playwright"', { stdio: 'pipe', timeout: 10000 });
    log('playwright chromium: checking...');
    try {
      execSync('python -m playwright install chromium', { stdio: 'pipe', timeout: 120000 });
      log('playwright chromium: ready');
    } catch (e) {
      warn('playwright chromium install failed - will auto-install on first use');
    }
  } catch {
    // playwright not installed yet, will be handled by server.py auto-install
  }
}

/**
 * Find server.py - it's in the same directory as this setup.js
 */
function findServerPy() {
  const serverPy = path.join(__dirname, 'server.py');
  if (fs.existsSync(serverPy)) return serverPy;
  return null;
}

/**
 * Check if mcpm CLI is available
 */
function hasMcpm() {
  try {
    execSync('mcpm --version', { stdio: 'pipe', timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if mcpm MCP server is configured (in any .mcp.json)
 */
function hasMcpmMcp() {
  const locations = [
    path.join(process.cwd(), '.mcp.json'),
    path.join(os.homedir(), '.claude', '.mcp.json'),
    path.join(os.homedir(), '.mcp.json'),
  ];
  for (const loc of locations) {
    try {
      const content = JSON.parse(fs.readFileSync(loc, 'utf8'));
      if (content.mcpServers && content.mcpServers['mcp-manager']) return loc;
    } catch {}
  }
  return null;
}

/**
 * Add server via mcpm CLI
 */
function addViaMcpm(serverPyPath) {
  const pyPath = serverPyPath.replace(/\\/g, '/');
  try {
    execSync(
      `mcpm add ${SERVER_NAME} --command=python --args='["${pyPath}"]' --description="${DESCRIPTION}"`,
      { stdio: 'pipe', timeout: 10000 }
    );
    log('Added via mcpm');
    return true;
  } catch (e) {
    warn('mcpm add failed: ' + e.message);
    return false;
  }
}

/**
 * Add server to .mcp.json that has mcp-manager (append to servers list)
 */
function addToMcpmProject(mcpJsonPath, serverPyPath) {
  try {
    const content = JSON.parse(fs.readFileSync(mcpJsonPath, 'utf8'));
    const mgr = content.mcpServers['mcp-manager'];

    if (!mgr.servers) mgr.servers = [];

    if (mgr.servers.includes(SERVER_NAME)) {
      log('Already in mcp-manager servers list: ' + mcpJsonPath);
      return true;
    }

    mgr.servers.push(SERVER_NAME);
    fs.writeFileSync(mcpJsonPath, JSON.stringify(content, null, 2) + '\n', 'utf8');
    log('Added to mcp-manager servers list: ' + mcpJsonPath);
    log('NOTE: Also add trend-docs entry to servers.yaml for mcp-manager to find it');
    return true;
  } catch (e) {
    warn('Failed to update ' + mcpJsonPath + ': ' + e.message);
    return false;
  }
}

/**
 * Add server directly to settings.json mcpServers (user-level config)
 * Claude Code reads MCP config from settings.json, not ~/.claude/.mcp.json
 */
function addToSettingsJson(serverPyPath) {
  const settingsPath = path.join(os.homedir(), '.claude', 'settings.json');
  const pyPath = serverPyPath.replace(/\\/g, '/');

  let settings = {};
  try {
    settings = JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
  } catch {}

  if (!settings.mcpServers) settings.mcpServers = {};

  if (settings.mcpServers[SERVER_NAME]) {
    log('Already configured in settings.json');
    return true;
  }

  settings.mcpServers[SERVER_NAME] = {
    command: 'python',
    args: [pyPath],
    env: { PYTHONIOENCODING: 'utf-8' }
  };

  // Ensure directory exists
  const dir = path.dirname(settingsPath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf8');
  log('Added to ' + settingsPath);
  return true;
}

/**
 * Also write to ~/.mcp.json (project-agnostic fallback)
 */
function addToHomeMcpJson(serverPyPath) {
  const mcpJsonPath = path.join(os.homedir(), '.mcp.json');
  const pyPath = serverPyPath.replace(/\\/g, '/');

  let content = { mcpServers: {} };
  try {
    content = JSON.parse(fs.readFileSync(mcpJsonPath, 'utf8'));
    if (!content.mcpServers) content.mcpServers = {};
  } catch {}

  if (content.mcpServers[SERVER_NAME]) {
    log('Already in ' + mcpJsonPath);
    return true;
  }

  content.mcpServers[SERVER_NAME] = {
    command: 'python',
    args: [pyPath],
    env: { PYTHONIOENCODING: 'utf-8' }
  };

  fs.writeFileSync(mcpJsonPath, JSON.stringify(content, null, 2) + '\n', 'utf8');
  log('Added to ' + mcpJsonPath);
  return true;
}

/**
 * If mcp-manager exists, ensure servers.yaml has the trend-docs entry
 */
function ensureServersYaml(serverPyPath) {
  // Search common locations for servers.yaml
  const candidates = [
    path.join(os.homedir(), '.claude', 'servers.yaml'),
    path.join(os.homedir(), 'servers.yaml'),
  ];

  // Also check MCPM_PROJECT_PATH env
  if (process.env.MCPM_PROJECT_PATH) {
    candidates.unshift(path.join(process.env.MCPM_PROJECT_PATH, '..', 'MCP', 'mcp-manager', 'servers.yaml'));
  }

  for (const yamlPath of candidates) {
    if (!fs.existsSync(yamlPath)) continue;

    try {
      const content = fs.readFileSync(yamlPath, 'utf8');
      if (content.includes('trend-docs:')) {
        log('trend-docs already in servers.yaml: ' + yamlPath);
        return true;
      }

      // Append trend-docs entry before 'defaults:' section or at end of servers block
      const pyPath = serverPyPath.replace(/\\/g, '/');
      const entry = `  trend-docs:
    command: python
    args:
      - ${pyPath}
    description: ${DESCRIPTION}
    env:
      PYTHONIOENCODING: utf-8
    enabled: true
    auto_start: false
    tags:
      - docs
      - trend-micro
    keywords:
      - trend docs
      - documentation
      - trendmicro
`;

      // Insert before 'defaults:' line if it exists
      if (content.includes('\ndefaults:')) {
        const updated = content.replace('\ndefaults:', '\n' + entry + 'defaults:');
        fs.writeFileSync(yamlPath, updated, 'utf8');
      } else {
        fs.writeFileSync(yamlPath, content + '\n' + entry, 'utf8');
      }

      log('Added trend-docs to servers.yaml: ' + yamlPath);
      return true;
    } catch (e) {
      warn('Failed to update servers.yaml: ' + e.message);
    }
  }

  return false;
}

function main() {
  log('Setting up trend-docs MCP server...');

  // 0. Install Python dependencies
  log('Checking Python dependencies...');
  installDeps();

  // 1. Find server.py
  const serverPy = findServerPy();
  if (!serverPy) {
    warn('server.py not found in ' + __dirname);
    warn('Manual setup required: add trend-docs to .mcp.json');
    process.exit(1);
  }
  log('Server: ' + serverPy);

  // 2. Try mcpm CLI first
  if (hasMcpm()) {
    log('mcpm CLI found, adding via mcpm...');
    if (addViaMcpm(serverPy)) {
      log('Done! Server will be available after mcpm reload or session restart.');
      return;
    }
    // Fall through if mcpm add failed
  }

  // 3. Check if mcp-manager is configured in any .mcp.json
  const mcpmProject = hasMcpmMcp();
  if (mcpmProject) {
    log('mcp-manager found in ' + mcpmProject);
    addToMcpmProject(mcpmProject, serverPy);
    ensureServersYaml(serverPy);
    log('Done! Run "mcpm reload" or restart session to activate.');
    return;
  }

  // 4. No mcpm at all - add to settings.json + ~/.mcp.json
  log('No mcp-manager found, configuring directly...');
  let ok = false;
  ok = addToSettingsJson(serverPy) || ok;
  ok = addToHomeMcpJson(serverPy) || ok;
  if (ok) {
    log('Done! Restart Claude Code session to activate.');
    return;
  }

  warn('Setup failed. Manual config required.');
  warn('Add to settings.json mcpServers: {"trend-docs": {"command": "python", "args": ["' + serverPy.replace(/\\/g, '/') + '"]}}');
  process.exit(1);
}

module.exports = { main, findServerPy, hasMcpm, hasMcpmMcp, addToSettingsJson, addToHomeMcpJson };

if (require.main === module) {
  main();
}
