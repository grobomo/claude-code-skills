#!/usr/bin/env node
/**
 * Super-Manager Setup
 * Platform detection, path resolution, config snapshot, hook installation,
 * skill discovery, keyword extraction, health check, and summary.
 *
 * Purpose: Enable zero-manual-step installation from marketplace
 * Pure Node.js only (fs, path, os) - no npm dependencies
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

// Delegate skill scanning to skill-manager (single source of truth)
var skillManagerPath = path.join(os.homedir(), '.claude', 'skills', 'skill-manager', 'setup.js');

// ---------------------------------------------------------------------------
// Phase 1: Platform detection, path resolution, config snapshot
// ---------------------------------------------------------------------------

/**
 * Detect platform and shell environment
 * @returns {{ os: string, platform: string, pathSep: string, shell: string }}
 */
function detectPlatform() {
  const platform = process.platform;
  let osName = 'unknown';
  let shell = 'bash';

  if (platform === 'win32') {
    osName = 'windows';
    shell = 'git-bash';
  } else if (platform === 'darwin') {
    osName = 'macos';
    shell = 'bash';
  } else if (platform === 'linux') {
    osName = 'linux';
    shell = 'bash';
  }

  return {
    os: osName,
    platform: platform,
    pathSep: path.sep,
    shell: shell
  };
}

/**
 * Resolve all key paths used by super-manager
 * All paths constructed with path.join() and os.homedir() - no hardcoded separators
 * @returns {Object} Object with all resolved paths
 */
function resolvePaths() {
  const home = os.homedir();
  const claudeDir = path.join(home, '.claude');
  const hooksDir = path.join(claudeDir, 'hooks');
  const skillsDir = path.join(claudeDir, 'skills');
  const backupsDir = path.join(claudeDir, 'backups');
  const superManagerDir = path.join(claudeDir, 'super-manager');
  const backupDir = path.join(backupsDir, 'before-super-manager');

  return {
    home: home,
    claudeDir: claudeDir,
    settingsJson: path.join(claudeDir, 'settings.json'),
    hooksDir: hooksDir,
    hookRegistry: path.join(hooksDir, 'hook-registry.json'),
    skillRegistry: path.join(hooksDir, 'skill-registry.json'),
    skillsDir: skillsDir,
    superManagerDir: superManagerDir,
    backupsDir: backupsDir,
    backupDir: backupDir
  };
}

/**
 * Create atomic snapshot of current config
 * @param {Object} paths - Paths object from resolvePaths()
 * @param {Object} options - Options: { force: boolean }
 * @returns {Object} Snapshot result
 */
function snapshotConfig(paths, options = {}) {
  const { force = false } = options;

  if (fs.existsSync(paths.backupDir)) {
    if (!force) {
      return { skipped: true, dir: paths.backupDir };
    } else {
      fs.rmSync(paths.backupDir, { recursive: true, force: true });
    }
  }

  const sourceFiles = [
    { src: paths.settingsJson, name: 'settings.json' },
    { src: paths.hookRegistry, name: 'hook-registry.json' },
    { src: paths.skillRegistry, name: 'skill-registry.json' }
  ];

  const copiedFiles = [];

  try {
    fs.mkdirSync(paths.backupDir, { recursive: true });

    for (const file of sourceFiles) {
      if (fs.existsSync(file.src)) {
        const dest = path.join(paths.backupDir, file.name);
        fs.copyFileSync(file.src, dest);
        copiedFiles.push(file.name);
      }
    }

    const platform = detectPlatform();
    const metadata = {
      timestamp: new Date().toISOString(),
      platform: platform,
      files: copiedFiles
    };

    const metadataPath = path.join(paths.backupDir, 'metadata.json');
    fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2), 'utf8');

    return {
      success: true,
      dir: paths.backupDir,
      files: copiedFiles,
      timestamp: metadata.timestamp
    };

  } catch (error) {
    console.error('[setup:error] Snapshot failed: ' + error.message);
    try {
      if (fs.existsSync(paths.backupDir)) {
        fs.rmSync(paths.backupDir, { recursive: true, force: true });
      }
    } catch (cleanupError) {
      console.error('[setup:error] Cleanup failed: ' + cleanupError.message);
    }
    throw error;
  }
}

// ---------------------------------------------------------------------------
// Phase 2: Hook installation and settings merge
// ---------------------------------------------------------------------------

/**
 * Install super-manager hook scripts to ~/.claude/hooks/
 * Skips if identical version exists, warns if different version exists
 *
 * @param {Object} paths - Path object from resolvePaths()
 * @returns {Object} { installed: [], skipped: [], warnings: [] }
 */
function installHooks(paths) {
  const hooksSrcDir = path.join(paths.superManagerDir, 'hooks-src');
  const hooksDestDir = paths.hooksDir;

  const hookFiles = [
    'tool-reminder.js',
    'super-manager-enforcement-gate.js',
    'super-manager-check-enforcement.js'
  ];

  const result = { installed: [], skipped: [], warnings: [] };

  // Ensure hooks destination directory exists
  if (!fs.existsSync(hooksDestDir)) {
    fs.mkdirSync(hooksDestDir, { recursive: true });
  }

  for (const hookFile of hookFiles) {
    const srcPath = path.join(hooksSrcDir, hookFile);
    const destPath = path.join(hooksDestDir, hookFile);

    // Check if source exists
    if (!fs.existsSync(srcPath)) {
      result.warnings.push('Source not found: ' + hookFile);
      continue;
    }

    // Check if destination exists
    if (fs.existsSync(destPath)) {
      const srcContent = fs.readFileSync(srcPath, 'utf8');
      const destContent = fs.readFileSync(destPath, 'utf8');

      if (srcContent === destContent) {
        result.skipped.push(hookFile + ' (identical)');
        continue;
      } else {
        result.warnings.push(hookFile + ' exists with different content - preserving customizations');
        result.skipped.push(hookFile + ' (modified)');
        continue;
      }
    }

    // Copy file
    fs.copyFileSync(srcPath, destPath);
    result.installed.push(hookFile);
  }

  return result;
}

/**
 * Merge super-manager hook entries into settings.json
 * Preserves all existing hooks, adds super-manager hooks if not present
 *
 * @param {Object} paths - Path object from resolvePaths()
 * @returns {Object} { added: [], existed: [], errors: [] }
 */
function mergeSettings(paths) {
  const settingsPath = paths.settingsJson;
  const result = { added: [], existed: [], errors: [] };

  // Read existing settings
  var settings;
  try {
    const content = fs.readFileSync(settingsPath, 'utf8');
    settings = JSON.parse(content);
  } catch (err) {
    result.errors.push('Failed to read settings.json: ' + err.message);
    return result;
  }

  // Ensure hooks object exists
  if (!settings.hooks) {
    settings.hooks = {};
  }

  // Build cross-platform command paths at runtime
  function hookCommand(hookFile) {
    return 'node "' + path.join(paths.hooksDir, hookFile).replace(/\\/g, '/') + '"';
  }

  // Define super-manager hook entries
  const superManagerHooks = [
    {
      event: 'UserPromptSubmit',
      matcher: '*',
      hookFile: 'tool-reminder.js',
      hook: { type: 'command', command: hookCommand('tool-reminder.js') }
    },
    {
      event: 'PreToolUse',
      matcher: 'Bash|Edit|Write|Read|Glob|Grep|WebFetch|WebSearch',
      hookFile: 'super-manager-enforcement-gate.js',
      hook: { type: 'command', command: hookCommand('super-manager-enforcement-gate.js') }
    },
    {
      event: 'PostToolUse',
      matcher: 'Skill|Task',
      hookFile: 'super-manager-check-enforcement.js',
      hook: { type: 'command', command: hookCommand('super-manager-check-enforcement.js') }
    }
  ];

  for (const smHook of superManagerHooks) {
    // Ensure event array exists
    if (!settings.hooks[smHook.event]) {
      settings.hooks[smHook.event] = [];
    }

    // Check if this hook already exists (by filename in command string)
    var alreadyRegistered = false;
    for (const entry of settings.hooks[smHook.event]) {
      if (!entry.hooks) continue;
      for (const h of entry.hooks) {
        if (h.command && h.command.indexOf(smHook.hookFile) !== -1) {
          alreadyRegistered = true;
          break;
        }
      }
      if (alreadyRegistered) break;
    }

    if (alreadyRegistered) {
      result.existed.push(smHook.event + ':' + smHook.hookFile);
      continue;
    }

    // Find or create matcher entry
    var matcherEntry = null;
    for (const entry of settings.hooks[smHook.event]) {
      if (entry.matcher === smHook.matcher) {
        matcherEntry = entry;
        break;
      }
    }

    if (!matcherEntry) {
      matcherEntry = { matcher: smHook.matcher, hooks: [] };
      settings.hooks[smHook.event].push(matcherEntry);
    }

    // Add hook to matcher's hooks array
    matcherEntry.hooks.push(smHook.hook);
    result.added.push(smHook.event + ':' + smHook.hookFile);
  }

  // Write back settings.json
  try {
    fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf8');
  } catch (err) {
    result.errors.push('Failed to write settings.json: ' + err.message);
    return result;
  }

  return result;
}

// ---------------------------------------------------------------------------
// Phase 3: Skill discovery (delegated to skill-manager)
// ---------------------------------------------------------------------------
// 2/18/26: Removed ~447 lines of duplicated functions:
//   getTooGenericWords, discoverSkills, extractKeywords,
//   extractVerbPhrases, filterKeywords, buildSkillRegistry
// skill-manager/setup.js is the single source of truth for keyword operations


// ---------------------------------------------------------------------------
// Phase 4: Health check and summary
// ---------------------------------------------------------------------------

/**
 * Verify system health after installation
 * @param {Object} paths - Paths object from resolvePaths()
 * @returns {Object} { healthy: boolean, checks: [{name, passed, message}] }
 */
function healthCheck(paths) {
  var checks = [];

  // Check 1: Hook files exist
  var hookFiles = [
    'tool-reminder.js',
    'super-manager-enforcement-gate.js',
    'super-manager-check-enforcement.js'
  ];
  var allHooksExist = true;
  var missingHooks = [];
  for (var hf of hookFiles) {
    var hookPath = path.join(paths.hooksDir, hf);
    if (!fs.existsSync(hookPath)) {
      allHooksExist = false;
      missingHooks.push(hf);
    } else {
      // Also check non-empty
      try {
        var stat = fs.statSync(hookPath);
        if (stat.size === 0) {
          allHooksExist = false;
          missingHooks.push(hf + ' (empty)');
        }
      } catch (e) {
        allHooksExist = false;
        missingHooks.push(hf + ' (unreadable)');
      }
    }
  }
  checks.push({
    name: 'Hook files exist',
    passed: allHooksExist,
    message: allHooksExist ? 'All hooks present' : 'Missing: ' + missingHooks.join(', ')
  });

  // Check 2: skill-registry.json valid
  var skillRegValid = false;
  var skillRegMsg = '';
  try {
    if (fs.existsSync(paths.skillRegistry)) {
      var srContent = JSON.parse(fs.readFileSync(paths.skillRegistry, 'utf8'));
      if (srContent && Array.isArray(srContent.skills)) {
        skillRegValid = true;
        skillRegMsg = 'Valid JSON with ' + srContent.skills.length + ' skills';
      } else {
        skillRegMsg = 'Invalid structure (missing skills array)';
      }
    } else {
      skillRegMsg = 'File not found';
    }
  } catch (err) {
    skillRegMsg = 'Parse error: ' + err.message;
  }
  checks.push({
    name: 'skill-registry.json valid',
    passed: skillRegValid,
    message: skillRegMsg
  });

  // Check 3: hook-registry.json valid
  var hookRegValid = false;
  var hookRegMsg = '';
  try {
    if (fs.existsSync(paths.hookRegistry)) {
      var hrContent = JSON.parse(fs.readFileSync(paths.hookRegistry, 'utf8'));
      if (hrContent) {
        hookRegValid = true;
        var hookCount = Array.isArray(hrContent.hooks) ? hrContent.hooks.length :
                        Array.isArray(hrContent) ? hrContent.length : 'unknown';
        hookRegMsg = 'Valid JSON (' + hookCount + ' entries)';
      } else {
        hookRegMsg = 'Empty JSON';
      }
    } else {
      hookRegMsg = 'File not found (may not be created yet)';
      hookRegValid = true; // Not critical - may not exist yet
    }
  } catch (err) {
    hookRegMsg = 'Parse error: ' + err.message;
  }
  checks.push({
    name: 'hook-registry.json valid',
    passed: hookRegValid,
    message: hookRegMsg
  });

  // Check 4: settings.json has SM hooks registered
  var settingsValid = false;
  var settingsMsg = '';
  try {
    if (fs.existsSync(paths.settingsJson)) {
      var settingsContent = JSON.parse(fs.readFileSync(paths.settingsJson, 'utf8'));
      var hooks = settingsContent.hooks || {};
      var foundHooks = [];

      // Check for tool-reminder.js in UserPromptSubmit
      var ups = hooks.UserPromptSubmit || [];
      for (var u of ups) {
        for (var h of (u.hooks || [])) {
          if (h.command && h.command.indexOf('tool-reminder.js') !== -1) {
            foundHooks.push('tool-reminder.js');
          }
        }
      }

      // Check for enforcement-gate in PreToolUse
      var ptu = hooks.PreToolUse || [];
      for (var p of ptu) {
        for (var ph of (p.hooks || [])) {
          if (ph.command && ph.command.indexOf('super-manager-enforcement-gate.js') !== -1) {
            foundHooks.push('enforcement-gate.js');
          }
        }
      }

      // Check for check-enforcement in PostToolUse
      var ptou = hooks.PostToolUse || [];
      for (var po of ptou) {
        for (var poh of (po.hooks || [])) {
          if (poh.command && poh.command.indexOf('super-manager-check-enforcement.js') !== -1) {
            foundHooks.push('check-enforcement.js');
          }
        }
      }

      if (foundHooks.length >= 3) {
        settingsValid = true;
        settingsMsg = 'All SM hooks registered';
      } else {
        settingsMsg = 'Found ' + foundHooks.length + '/3 SM hooks';
      }
    } else {
      settingsMsg = 'settings.json not found';
    }
  } catch (err) {
    settingsMsg = 'Parse error: ' + err.message;
  }
  checks.push({
    name: 'settings.json has SM hooks',
    passed: settingsValid,
    message: settingsMsg
  });

  // Overall health
  var allPassed = checks.every(function(c) { return c.passed; });

  return {
    healthy: allPassed,
    checks: checks
  };
}

/**
 * Print installation summary with health status and rollback command
 * @param {Object} results - Combined results from all setup phases
 */
function printSummary(results) {
  var platform = results.platform;
  var paths = results.paths;
  var snapshot = results.snapshot;
  var hooks = results.hooks;
  var settings = results.settings;
  var skills = results.skills;
  var registry = results.registry;
  var health = results.health;

  console.log('');
  console.log('[setup] ============================================');
  console.log('[setup] Super-Manager Installation Complete');
  console.log('[setup] ============================================');
  console.log('');

  // Platform
  console.log('[setup] Platform: ' + platform.os + ' (' + platform.platform + ') - ' + platform.shell);
  console.log('');

  // Snapshot
  if (snapshot && !snapshot.skipped && snapshot.files) {
    console.log('[setup] Config snapshot:');
    console.log('[setup]   Location: ' + snapshot.dir);
    for (var f of snapshot.files) {
      console.log('[setup]   - ' + f);
    }
    console.log('[setup]   Backed up at: ' + snapshot.timestamp);
  } else if (snapshot && snapshot.skipped) {
    console.log('[setup] Config snapshot: Using existing at ' + snapshot.dir);
  }
  console.log('');

  // Hooks installed
  if (hooks) {
    console.log('[setup] Hook scripts:');
    if (hooks.installed.length > 0) {
      for (var hi of hooks.installed) console.log('[setup]   Installed: ' + hi);
    }
    if (hooks.skipped.length > 0) {
      for (var hs of hooks.skipped) console.log('[setup]   Skipped: ' + hs);
    }
    console.log('');
  }

  // Settings merge
  if (settings) {
    console.log('[setup] Settings.json hooks:');
    if (settings.added.length > 0) {
      for (var sa of settings.added) console.log('[setup]   Added: ' + sa);
    }
    if (settings.existed.length > 0) {
      for (var se of settings.existed) console.log('[setup]   Exists: ' + se);
    }
    console.log('');
  }

  // Skills
  if (skills && registry) {
    console.log('[setup] Skills: ' + registry.total + ' total (' + registry.updated + ' updated, ' + registry.added + ' new)');
    console.log('');
  }

  // Health check
  if (health) {
    var passedCount = health.checks.filter(function(c) { return c.passed; }).length;
    var totalCount = health.checks.length;

    if (health.healthy) {
      console.log('[setup] System health: HEALTHY (' + passedCount + '/' + totalCount + ' checks passed)');
    } else {
      console.log('[setup] System health: ISSUES FOUND (' + passedCount + '/' + totalCount + ' checks passed)');
    }

    for (var ch of health.checks) {
      var symbol = ch.passed ? '[OK]' : '[!!]';
      console.log('[setup]   ' + symbol + ' ' + ch.name + ' - ' + ch.message);
    }
    console.log('');
  }

  // Rollback command
  console.log('[setup] To rollback:');
  console.log('[setup]   node ~/.claude/super-manager/rollback.js');
  console.log('');
  console.log('[setup] ============================================');
}

// ---------------------------------------------------------------------------
// Main orchestrator
// ---------------------------------------------------------------------------

/**
 * Main orchestrator function
 * @returns {Promise<Object>} Result object with all phase results
 */
async function main() {
  console.log('[setup] Super-Manager Setup v1.0\n');

  const args = process.argv.slice(2);
  const force = args.includes('--force');

  // 1. Detect platform
  const platform = detectPlatform();
  console.log('[setup] Platform: ' + platform.os + ' (' + platform.shell + ')');

  // 2. Resolve paths
  const paths = resolvePaths();

  // 3. Snapshot existing config
  console.log('\n[setup] Creating config snapshot...');
  const snapshot = snapshotConfig(paths, { force });
  if (snapshot.skipped) {
    console.log('[setup]   Snapshot exists, skipping (use --force to overwrite)');
  } else {
    console.log('[setup]   Files backed up: ' + (snapshot.files || []).join(', '));
  }

  // 4. Install hooks
  console.log('\n[setup] Installing hook scripts...');
  const hooks = installHooks(paths);
  for (var h of hooks.installed) console.log('[setup]   Installed: ' + h);
  for (var hs of hooks.skipped) console.log('[setup]   Skipped: ' + hs);
  for (var hw of hooks.warnings) console.warn('[setup:warn]   ' + hw);

  // 5. Merge settings
  console.log('\n[setup] Merging settings.json...');
  const settings = mergeSettings(paths);
  for (var sa of settings.added) console.log('[setup]   Added: ' + sa);
  for (var se of settings.existed) console.log('[setup]   Exists: ' + se);
  for (var serr of settings.errors) console.error('[setup:error]   ' + serr);

  // 6. Discover skills & extract keywords (delegated to skill-manager)
  var skills = [];
  var registry = { total: 0, updated: 0, added: 0 };
  try {
    var smModule = require(skillManagerPath);
    console.log('\n[setup] Delegating skill scan to skill-manager...');
    var smResult = smModule.main();
    skills = smResult && smResult.skills ? smResult.skills : [];
    registry = smResult && smResult.registry ? smResult.registry : registry;
    console.log('[setup] skill-manager: ' + (smResult ? smResult.skillCount + ' skills scanned' : 'done'));
  } catch(e) {
    console.warn('[setup:warn] skill-manager not available: ' + e.message);
    console.log('[setup] Install skill-manager for keyword enrichment');
  }

  // 7. Health check
  console.log('\n[setup] Running health check...');
  const health = healthCheck(paths);

  // 8. Print summary
  printSummary({ platform, paths, snapshot, hooks, settings, skills, registry, health });

  return { platform, paths, snapshot, hooks, settings, skills, registry, health };
}

// Export all functions
module.exports = {
  detectPlatform,
  resolvePaths,
  snapshotConfig,
  installHooks,
  mergeSettings,
  healthCheck,
  printSummary,
  main
};

// Run main if executed directly
if (require.main === module) {
  main().catch(function(err) {
    console.error('[setup:error]', err.message);
    process.exit(1);
  });
}
