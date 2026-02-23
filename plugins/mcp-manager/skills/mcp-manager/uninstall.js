#!/usr/bin/env node
/**
 * mcp-manager uninstall
 * Restores config from backup and removes all files created by setup.
 *
 * What it does:
 *   1. Finds the latest backup in ~/.claude/backups/mcp-manager/
 *   2. Restores settings.json, CLAUDE.md, .mcp.json from backup
 *   3. Removes instruction files that setup created
 *   4. Removes CLAUDE.md fallback markers if present
 *   5. Prints summary
 *
 * Pure Node.js - no external dependencies.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

function log(msg) { console.log('[mcp-manager:uninstall] ' + msg); }
function warn(msg) { console.warn('[mcp-manager:uninstall:warn] ' + msg); }

const HOME = os.homedir();
const CLAUDE_DIR = path.join(HOME, '.claude');
const CLAUDE_MD_PATH = path.join(CLAUDE_DIR, 'CLAUDE.md');
const BACKUPS_DIR = path.join(CLAUDE_DIR, 'backups', 'mcp-manager');
const CLAUDE_MD_MARKER = '<!-- mcp-manager-rules -->';

function findLatestBackup() {
  if (!fs.existsSync(BACKUPS_DIR)) return null;

  const entries = fs.readdirSync(BACKUPS_DIR)
    .filter(e => {
      const full = path.join(BACKUPS_DIR, e);
      return fs.statSync(full).isDirectory() && fs.existsSync(path.join(full, 'manifest.json'));
    })
    .sort()
    .reverse();

  if (entries.length === 0) return null;
  return path.join(BACKUPS_DIR, entries[0]);
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

function main() {
  log('Starting uninstall...');

  const backupDir = findLatestBackup();
  if (!backupDir) {
    warn('No backup found in ' + BACKUPS_DIR);
    warn('Manual cleanup required:');
    warn('  1. Remove "mcp-manager" from ~/.claude/settings.json mcpServers');
    warn('  2. Remove "mcp-manager" from .mcp.json mcpServers');
    warn('  3. Delete instruction files: ~/.claude/instructions/UserPromptSubmit/mcpm-*.md');

    // Still try to clean up CLAUDE.md fallback
    if (removeClaudeMdFallback()) {
      log('Removed CLAUDE.md fallback rules');
    }
    return;
  }

  log('Restoring from backup: ' + backupDir);

  let manifest;
  try {
    manifest = JSON.parse(fs.readFileSync(path.join(backupDir, 'manifest.json'), 'utf8'));
  } catch (e) {
    warn('Failed to read manifest: ' + e.message);
    return;
  }

  // Restore backed-up files
  let restored = 0;
  for (const [backupName, originalPath] of Object.entries(manifest.files || {})) {
    const backupFile = path.join(backupDir, backupName);
    if (!fs.existsSync(backupFile)) {
      warn('Backup file missing: ' + backupName);
      continue;
    }

    try {
      fs.copyFileSync(backupFile, originalPath);
      restored++;
      log('Restored: ' + originalPath);
    } catch (e) {
      warn('Failed to restore ' + originalPath + ': ' + e.message);
    }
  }

  // Remove files that setup created (instruction files)
  let removed = 0;
  for (const filePath of (manifest.created || [])) {
    if (fs.existsSync(filePath)) {
      try {
        fs.unlinkSync(filePath);
        removed++;
        log('Removed: ' + filePath);
      } catch (e) {
        warn('Failed to remove ' + filePath + ': ' + e.message);
      }
    }
  }

  // Clean up CLAUDE.md fallback markers
  if (removeClaudeMdFallback()) {
    log('Removed CLAUDE.md fallback rules');
  }

  log('');
  log('Uninstall complete!');
  log('  Restored: ' + restored + ' file(s)');
  log('  Removed: ' + removed + ' created file(s)');
  log('');
  log('To fully remove the plugin:');
  log('  claude plugin uninstall mcp-manager');
}

module.exports = { main, findLatestBackup, removeClaudeMdFallback };

if (require.main === module) {
  main();
}
