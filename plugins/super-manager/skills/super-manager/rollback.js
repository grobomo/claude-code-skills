#!/usr/bin/env node
/**
 * Super-Manager Rollback
 * Restores config from snapshot or removes SM entries from settings.json
 *
 * Mode 1: Snapshot exists -> restore files from backup
 * Mode 2: No snapshot -> parse settings.json, remove only SM hook entries
 *
 * Pure Node.js only (fs, path, os) - no npm dependencies
 */

const fs = require('fs');
const path = require('path');
const { resolvePaths, detectPlatform } = require('./setup.js');

// SM hook filenames used for identification
const SM_HOOK_FILES = [
  'tool-reminder.js',
  'super-manager-enforcement-gate.js',
  'super-manager-check-enforcement.js'
];

/**
 * Restore config files from snapshot backup
 * @param {Object} paths - Paths from resolvePaths()
 * @returns {Object} { mode, filesRestored, warnings }
 */
function restoreFromSnapshot(paths) {
  const result = { mode: 'snapshot', filesRestored: [], warnings: [] };
  const backupDir = paths.backupDir;

  // Read metadata to know what was backed up
  const metadataPath = path.join(backupDir, 'metadata.json');
  var metadata;
  try {
    metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
  } catch (err) {
    result.warnings.push('Could not read backup metadata: ' + err.message);
    // Fall back to known file list
    metadata = { files: ['settings.json', 'hook-registry.json', 'skill-registry.json'] };
  }

  // Map backup filenames to their restore destinations
  var fileDestinations = {
    'settings.json': paths.settingsJson,
    'hook-registry.json': paths.hookRegistry,
    'skill-registry.json': paths.skillRegistry
  };

  for (var fileName of (metadata.files || [])) {
    var srcPath = path.join(backupDir, fileName);
    var destPath = fileDestinations[fileName];

    if (!destPath) {
      result.warnings.push('Unknown backup file: ' + fileName);
      continue;
    }

    if (!fs.existsSync(srcPath)) {
      result.warnings.push('Backup file missing: ' + fileName);
      continue;
    }

    try {
      // Ensure destination directory exists
      var destDir = path.dirname(destPath);
      if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
      }

      fs.copyFileSync(srcPath, destPath);
      result.filesRestored.push(fileName);
    } catch (err) {
      result.warnings.push('Failed to restore ' + fileName + ': ' + err.message);
    }
  }

  return result;
}

/**
 * Remove only super-manager hook entries from settings.json
 * Preserves all user-added hooks
 * @param {Object} paths - Paths from resolvePaths()
 * @returns {Object} { mode, entriesRemoved, warnings }
 */
function removeSuperManagerEntries(paths) {
  const result = { mode: 'entries', entriesRemoved: [], warnings: [] };

  if (!fs.existsSync(paths.settingsJson)) {
    result.warnings.push('settings.json not found - nothing to remove');
    return result;
  }

  var settings;
  try {
    settings = JSON.parse(fs.readFileSync(paths.settingsJson, 'utf8'));
  } catch (err) {
    result.warnings.push('Failed to parse settings.json: ' + err.message);
    return result;
  }

  if (!settings.hooks) {
    result.warnings.push('No hooks section in settings.json');
    return result;
  }

  // For each event type, filter out SM hooks
  for (var event of Object.keys(settings.hooks)) {
    var entries = settings.hooks[event];
    if (!Array.isArray(entries)) continue;

    for (var i = entries.length - 1; i >= 0; i--) {
      var entry = entries[i];
      if (!entry.hooks || !Array.isArray(entry.hooks)) continue;

      // Filter hooks array: remove SM hooks, keep others
      var originalLen = entry.hooks.length;
      entry.hooks = entry.hooks.filter(function(h) {
        if (!h.command) return true; // Keep non-command hooks

        // Check if this hook command matches any SM hook file
        for (var smFile of SM_HOOK_FILES) {
          if (h.command.indexOf(smFile) !== -1) {
            result.entriesRemoved.push(event + ':' + smFile);
            return false; // Remove it
          }
        }
        return true; // Keep non-SM hooks
      });

      // If matcher entry has no hooks left, remove it entirely
      if (entry.hooks.length === 0) {
        entries.splice(i, 1);
      }
    }

    // If event array is empty, remove it
    if (entries.length === 0) {
      delete settings.hooks[event];
    }
  }

  // Write back
  try {
    fs.writeFileSync(paths.settingsJson, JSON.stringify(settings, null, 2), 'utf8');
  } catch (err) {
    result.warnings.push('Failed to write settings.json: ' + err.message);
  }

  return result;
}

/**
 * Main rollback entry point
 */
function main() {
  console.log('[rollback] Super-Manager Rollback\n');

  const platform = detectPlatform();
  console.log('[rollback] Platform: ' + platform.os + ' (' + platform.shell + ')');

  const paths = resolvePaths();
  var result;

  if (fs.existsSync(paths.backupDir)) {
    // Mode 1: Restore from snapshot
    console.log('[rollback] Found snapshot at: ' + paths.backupDir);
    console.log('[rollback] Restoring from snapshot...\n');
    result = restoreFromSnapshot(paths);

    if (result.filesRestored.length > 0) {
      console.log('[rollback] Restored files:');
      for (var f of result.filesRestored) {
        console.log('[rollback]   - ' + f);
      }
    }
  } else {
    // Mode 2: Remove SM entries
    console.log('[rollback] No snapshot found at: ' + paths.backupDir);
    console.log('[rollback] Removing super-manager entries from settings.json...\n');
    result = removeSuperManagerEntries(paths);

    if (result.entriesRemoved.length > 0) {
      console.log('[rollback] Removed entries:');
      for (var e of result.entriesRemoved) {
        console.log('[rollback]   - ' + e);
      }
    } else {
      console.log('[rollback] No super-manager entries found to remove');
    }
  }

  // Print warnings
  if (result.warnings && result.warnings.length > 0) {
    console.log('\n[rollback:warn] Warnings:');
    for (var w of result.warnings) {
      console.log('[rollback:warn]   ' + w);
    }
  }

  console.log('\n[rollback] Done.');
  return result;
}

module.exports = { main, restoreFromSnapshot, removeSuperManagerEntries };

if (require.main === module) {
  try {
    main();
  } catch (err) {
    console.error('[rollback:error]', err.message);
    process.exit(1);
  }
}
