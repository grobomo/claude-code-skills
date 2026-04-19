# claude-code-skills — Pending Tasks

## Completed
- [x] T001: Sync hook-runner v2.15.1 to plugins/hook-runner/ (done in hook-runner session, 36 files)

## Marketplace Sync
- [x] T002: Sync hook-runner README.md to plugins/hook-runner/ (included in T003 sync)
- [x] T003: Sync hook-runner v2.20.0 to marketplace — new modules (hook-system-reminder), fixes (cwd-drift-detector, worktree-gate), shtd.yml update, version bump
- [x] T004: Sync hook-runner v2.26.0 to marketplace — PRs #351 + #352 (commit-counter branch awareness, hook-editing-gate expansion, publish-json-guard creation mode, openclaw-tmemu-guard, stop-message.txt sync, worktree-gate refactor)

## Pending

- [x] T005: Add missing plugins to README.md — hook-runner, cloud-claude, claude-report, jumpbox (PR #7)
- [x] T006: Sync hook-runner v2.32.0 to marketplace — v2.26.0 → v2.32.0 (PR #8)
- [x] T007: Publish openclaw skill to marketplace (PR #9)
- [x] T008: Fix README table — squash merges lost plugin entries (PR #10)
- [x] T009: Add secret-scan.yml CI workflow (PR #11)
- [x] T010: Add .gitignore entries for SESSION_STATE.md and .workflow-state.json (PR #11)
- [x] T011: Add plugin.json for 5 plugins + fix CI failures (PR #12) — root cause fix for README table loss
- [x] T012: Sync hook-runner v2.54.0 to marketplace — v2.32.0 → v2.54.0 (PR #13, 64 files, 1589+/338-)
- [x] T013: Clean up leftover SKILL.md.bak.archive from openclaw plugin (PR #14)
- [ ] T014: Audit plugin versions — check which plugins have stale marketplace versions vs source repos
  - Finding: mcp-manager v1.1.0 → v1.23.0 (source at _grobomo/ccc-manager) — 22 versions behind
  - All other plugins are developed in-place or have no separate source repo
- [ ] T015: Sync mcp-manager to marketplace — source location unclear. ccc-manager is a different project (fleet manager). MCP/mcp-manager path in .mcp.json is a broken junction. Need user to identify source repo.
