# claude-code-skills — Task Tracker

## Blocked

- [ ] T015: Sync mcp-manager to marketplace — source at broken junction (MCP/mcp-manager). Need user to identify actual source repo.

## Completed

### CI & Quality (T009-T011, T016-T018)
- [x] T009: Add secret-scan.yml CI workflow (PR #11)
- [x] T010: Add .gitignore entries for SESSION_STATE.md and .workflow-state.json (PR #11)
- [x] T011: Add plugin.json for 5 plugins + fix CI failures (PR #12) — root cause fix for README table loss
- [x] T016: Fix instruction-manager plugin.json + add validation test script (PR #16)
- [x] T017: Add CONTRIBUTING.md for plugin authors (PR #17)
- [x] T018: Add author.name validation to CI plugin-quality-gate (PR #18)
- [x] T019: Consolidate TODO.md — reorganize sections, archive completed tasks

### Marketplace Sync (T001-T006, T012, T014)
- [x] T001: Sync hook-runner v2.15.1 to plugins/hook-runner/
- [x] T002: Sync hook-runner README.md (included in T003)
- [x] T003: Sync hook-runner v2.20.0
- [x] T004: Sync hook-runner v2.26.0 (PR #6)
- [x] T006: Sync hook-runner v2.32.0 (PR #8)
- [x] T012: Sync hook-runner v2.54.0 (PR #13, 64 files, 1589+/338-)
- [x] T014: Audit plugin versions (PR #15) — only mcp-manager stale

### Plugin Fixes (T005, T007-T008, T013)
- [x] T005: Add missing plugins to README table (PR #7)
- [x] T007: Publish openclaw skill (PR #9)
- [x] T008: Fix README table — squash merges lost entries (PR #10)
- [x] T013: Clean up leftover backup file (PR #14)
