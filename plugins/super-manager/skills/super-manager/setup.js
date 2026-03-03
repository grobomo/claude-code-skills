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
// Phase 2.5: Install bundled rules
// ---------------------------------------------------------------------------

/**
 * Install publish-sanitize rule to ~/.claude/rules/UserPromptSubmit/
 * Ensures the sanitization scan rule is always present, even without rule-manager.
 * Skips if identical file already exists.
 *
 * @param {Object} paths - Path object from resolvePaths()
 * @returns {Object} { installed: [], skipped: [], warnings: [] }
 */
function installRules(paths) {
  var result = { installed: [], skipped: [], warnings: [] };
  var rulesDir = path.join(paths.claudeDir, 'rules', 'UserPromptSubmit');

  // Ensure rules directory exists
  try {
    fs.mkdirSync(rulesDir, { recursive: true });
  } catch (e) {
    result.warnings.push('Could not create rules dir: ' + e.message);
    return result;
  }

  // Bundled rules to install
  var bundledRules = [
    {
      filename: 'publish-sanitize.md',
      content: [
        '---',
        'id: publish-sanitize',
        'name: Sanitize Before Publishing',
        'keywords: [publish, marketplace, plugin, ship, push, deploy, skill, public, repo]',
        'description: "WHY: Published plugins shipped with hardcoded personal paths that broke on other machines. WHAT: Mandatory sanitization scan before any publish to marketplace or public repo."',
        'enabled: true',
        'priority: 5',
        'action: Scan for hardcoded paths before publishing',
        'min_matches: 2',
        '---',
        '',
        '# Sanitize Before Publishing',
        '',
        '## WHY',
        '',
        'Published plugins contained hardcoded personal paths (`C:/Users/username/...`, `OneDrive - OrgName/...`,',
        'personal namespaces). These paths break on every other machine and leak org/identity info.',
        '',
        '## Rule',
        '',
        'Before committing files to any public or shared repo (marketplace, GitHub public, plugin publish):',
        '',
        '### 1. Scan for personal paths',
        '',
        'Run this check on ALL files being published:',
        '',
        '```bash',
        'grep -rn "C:/Users/\\|C:\\\\\\\\Users\\\\\\\\\\|OneDrive -" <dir> \\',
        '  --include="*.py" --include="*.js" --include="*.json" --include="*.md" \\',
        '  --include="*.sh" --include="*.yaml" --include="*.yml"',
        '```',
        '',
        '### 2. Fix any hits',
        '',
        '| Pattern found | Replace with |',
        '|--------------|-------------|',
        '| Hardcoded home paths | `os.path.join(os.homedir(), ...)` or `$HOME/...` |',
        '| Org-specific paths | Dynamic discovery via `glob` patterns |',
        '| Personal GitHub usernames | `grobomo` or generic placeholder |',
        '| Personal namespaces | Generic placeholders (`my-namespace`, `my-account`) |',
        '| Personal IPs, AWS account IDs | Remove or use `<your-ip>` placeholders |',
        '',
        '### 3. Check registry/data files',
        '',
        'Registry files (`hook-registry.json`, `skill-registry.json`, etc.) must be empty templates:',
        '```json',
        '{"hooks": [], "version": "1.0"}',
        '```',
        'These are populated at runtime by setup.js. Never ship pre-populated registries.',
        '',
        '### 4. Verify no secrets',
        '',
        '```bash',
        'grep -rn "TOKEN=\\|KEY=\\|SECRET=\\|PASSWORD=" <dir> --include="*.py" --include="*.js" --include="*.json" --include="*.env"',
        '```',
        ''
      ].join('\n')
    }
  ];

  for (var rule of bundledRules) {
    var destPath = path.join(rulesDir, rule.filename);

    if (fs.existsSync(destPath)) {
      // Check if content is identical
      try {
        var existing = fs.readFileSync(destPath, 'utf8');
        if (existing.trim() === rule.content.trim()) {
          result.skipped.push(rule.filename + ' (identical)');
          continue;
        }
        // Different content -- don't overwrite user customizations
        result.skipped.push(rule.filename + ' (exists, preserving customizations)');
        continue;
      } catch (e) {
        result.warnings.push(rule.filename + ': read error - ' + e.message);
        continue;
      }
    }

    // Install the rule
    try {
      fs.writeFileSync(destPath, rule.content, 'utf8');
      result.installed.push(rule.filename);
    } catch (e) {
      result.warnings.push(rule.filename + ': write error - ' + e.message);
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Phase 2.75: Install GitHub Actions quality gate on marketplace repos
// ---------------------------------------------------------------------------

/**
 * Scan marketplace repos and install quality-gate.yml if missing.
 * Uses templates/quality-gate.yml as the source template.
 * Generic template with universal patterns -- user adds personal patterns after.
 *
 * @param {Object} paths - Path object from resolvePaths()
 * @returns {Object} { installed: [], skipped: [], warnings: [] }
 */
function installQualityGate(paths) {
  var result = { installed: [], skipped: [], warnings: [] };

  // Find the template relative to this script
  var templatePath = path.join(__dirname, 'templates', 'quality-gate.yml');
  if (!fs.existsSync(templatePath)) {
    result.warnings.push('Template not found: templates/quality-gate.yml');
    return result;
  }

  var templateContent;
  try {
    templateContent = fs.readFileSync(templatePath, 'utf8');
  } catch (e) {
    result.warnings.push('Cannot read template: ' + e.message);
    return result;
  }

  // Scan for marketplace repos
  var marketplacesDir = path.join(paths.claudeDir, 'plugins', 'marketplaces');
  if (!fs.existsSync(marketplacesDir)) {
    result.skipped.push('No marketplaces directory');
    return result;
  }

  var entries;
  try {
    entries = fs.readdirSync(marketplacesDir);
  } catch (e) {
    result.warnings.push('Cannot read marketplaces dir: ' + e.message);
    return result;
  }

  for (var entry of entries) {
    var repoDir = path.join(marketplacesDir, entry);
    var stat;
    try { stat = fs.statSync(repoDir); } catch (e) { continue; }
    if (!stat.isDirectory()) continue;

    // Must have plugins/ dir to be a marketplace repo
    var pluginsDir = path.join(repoDir, 'plugins');
    if (!fs.existsSync(pluginsDir)) continue;

    // Check if any quality gate workflow already exists
    var workflowDir = path.join(repoDir, '.github', 'workflows');
    var gateExists = false;
    if (fs.existsSync(workflowDir)) {
      try {
        var wfFiles = fs.readdirSync(workflowDir);
        for (var wf of wfFiles) {
          if (wf.indexOf('quality-gate') !== -1) {
            gateExists = true;
            break;
          }
        }
      } catch (e) { /* ignore */ }
    }

    if (gateExists) {
      result.skipped.push(entry + ' (quality gate exists)');
      continue;
    }

    // Install the quality gate workflow
    try {
      fs.mkdirSync(workflowDir, { recursive: true });
      var destPath = path.join(workflowDir, 'quality-gate.yml');
      fs.writeFileSync(destPath, templateContent, 'utf8');
      result.installed.push(entry);
    } catch (e) {
      result.warnings.push(entry + ': ' + e.message);
    }
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

  // Check 5: Marketplace repos have quality gates
  var qgValid = true;
  var qgMsg = '';
  var marketplacesDir = path.join(paths.claudeDir, 'plugins', 'marketplaces');
  if (fs.existsSync(marketplacesDir)) {
    var missing = [];
    try {
      var mpEntries = fs.readdirSync(marketplacesDir);
      for (var mpe of mpEntries) {
        var mpDir = path.join(marketplacesDir, mpe);
        try {
          if (!fs.statSync(mpDir).isDirectory()) continue;
        } catch (e) { continue; }
        if (!fs.existsSync(path.join(mpDir, 'plugins'))) continue;
        var wfDir = path.join(mpDir, '.github', 'workflows');
        var hasGate = false;
        if (fs.existsSync(wfDir)) {
          try {
            var wfs = fs.readdirSync(wfDir);
            for (var w of wfs) {
              if (w.indexOf('quality-gate') !== -1) { hasGate = true; break; }
            }
          } catch (e) { /* ignore */ }
        }
        if (!hasGate) missing.push(mpe);
      }
    } catch (e) { /* ignore */ }
    if (missing.length > 0) {
      qgValid = false;
      qgMsg = 'Missing quality gate: ' + missing.join(', ');
    } else {
      qgMsg = 'All marketplace repos have quality gates';
    }
  } else {
    qgMsg = 'No marketplaces (OK)';
  }
  checks.push({
    name: 'Quality gates installed',
    passed: qgValid,
    message: qgMsg
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
  var rules = results.rules;
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

  // Rules installed
  if (rules) {
    console.log('[setup] Bundled rules:');
    if (rules.installed.length > 0) {
      for (var rli of rules.installed) console.log('[setup]   Installed: ' + rli);
    }
    if (rules.skipped.length > 0) {
      for (var rls of rules.skipped) console.log('[setup]   Skipped: ' + rls);
    }
    console.log('');
  }

  // Quality gate
  var qualityGate = results.qualityGate;
  if (qualityGate) {
    console.log('[setup] Quality gates:');
    if (qualityGate.installed.length > 0) {
      for (var qgi of qualityGate.installed) console.log('[setup]   Installed: ' + qgi);
    }
    if (qualityGate.skipped.length > 0) {
      for (var qgs of qualityGate.skipped) console.log('[setup]   Skipped: ' + qgs);
    }
    if (qualityGate.warnings.length > 0) {
      for (var qgw of qualityGate.warnings) console.log('[setup:warn]   ' + qgw);
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

  // 6. Install bundled rules
  console.log('\n[setup] Installing bundled rules...');
  const rules = installRules(paths);
  for (var ri of rules.installed) console.log('[setup]   Installed: ' + ri);
  for (var rs of rules.skipped) console.log('[setup]   Skipped: ' + rs);
  for (var rw of rules.warnings) console.warn('[setup:warn]   ' + rw);

  // 7. Install quality gate on marketplace repos
  console.log('\n[setup] Checking marketplace repos for quality gates...');
  const qualityGate = installQualityGate(paths);
  for (var qi of qualityGate.installed) console.log('[setup]   Installed: ' + qi);
  for (var qs of qualityGate.skipped) console.log('[setup]   Skipped: ' + qs);
  for (var qw of qualityGate.warnings) console.warn('[setup:warn]   ' + qw);

  // 8. Discover skills & extract keywords (delegated to skill-manager)
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

  // 9. Health check
  console.log('\n[setup] Running health check...');
  const health = healthCheck(paths);

  // 10. Print summary
  printSummary({ platform, paths, snapshot, hooks, settings, rules, qualityGate, skills, registry, health });

  return { platform, paths, snapshot, hooks, settings, rules, qualityGate, skills, registry, health };
}

// Export all functions
module.exports = {
  detectPlatform,
  resolvePaths,
  snapshotConfig,
  installHooks,
  mergeSettings,
  installRules,
  installQualityGate,
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
