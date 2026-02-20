---
id: file-operations
keywords: [read file, write file, edit file, modify file, update file, search, find file]
tools: [Read, Write, Edit]
description: File operation rules for OneDrive-synced environments
name: File operation rules for OneDrive-synced environments
enabled: true
priority: 10
---

# File Operations Instructions

## CRITICAL: No Read/Write/Edit Tools

OneDrive sync causes race conditions with Claude's Read/Write/Edit tools.

| Instead of | Use |
|-----------|-----|
| Read tool | `cat file.txt` |
| Write tool | `cat > file.txt << 'DELIM' ... DELIM` |
| Edit tool | `sed -i 's/old/new/g' file.txt` |
| Grep tool | `grep -r "pattern" .` |
| Glob tool | `find . -name "*.py"` |

Always use bash equivalents for all file operations.

**NEVER use temp directories** (C:\temp, /tmp, $TEMP) - use project `.tmp/` subfolder instead. Clean up after.

**Read/Write/Edit tools ARE safe for non-OneDrive paths** (e.g. ~/.claude/, ~/.config/) - use them when heredocs fail.
