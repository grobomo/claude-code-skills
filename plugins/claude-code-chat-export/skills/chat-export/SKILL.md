---

name: chat-export
description: |
  Export Claude Code conversations to styled HTML with search, landing page,
  and optional Markdown output. Strips system noise, formats tool calls concisely.
keywords:
  - export chat
  - export transcript
  - export session
  - chat export
  - share session
  - save conversation
  - transcript
  - session history
  - export markdown

---

# Chat Export

Export Claude Code JSONL conversations to polished terminal-styled HTML pages with full-text search, expandable tool calls, screenshot galleries, and raw text export. Optional Markdown output for pasting in Slack, wiki, or docs.

## Usage

```bash
# Export current session to HTML (default)
python3 export.py

# Export current session to Markdown
python3 export.py --format md

# Export specific JSONL file
python3 export.py path/to/session.jsonl

# Export all sessions for current project
python3 export.py --all

# Export all sessions as Markdown
python3 export.py --all --format md

# Regenerate landing page only
python3 export.py --landing

# Custom output path
python3 export.py --out ~/Desktop/my-session.html
python3 export.py --format md --out ~/Desktop/my-session.md
```

## Output Formats

| Format | Flag | Features |
|--------|------|----------|
| HTML (default) | `--format html` | Terminal dark theme, search, expandable tool calls, screenshot gallery, Export Raw TXT button, landing page |
| Markdown | `--format md` | Clean headers, collapsible tool results, concise tool formatting, ready for wiki/Slack |

## What It Does

1. Parses Claude Code JSONL transcripts (two-pass: collect tool results, then build turns)
2. Strips system-reminder tags, hook noise, local-command wrappers
3. Formats tool calls concisely (bash inline, file paths for Read, diffs for Edit)
4. Auto-detects session, project name, branch, and working directory
5. HTML: generates self-contained styled page with search and landing page
6. Markdown: generates clean `.md` with collapsible details blocks

## Installation

```bash
git clone https://github.com/grobomo/claude-code-chat-export.git
cd claude-code-chat-export
python3 export.py --format md
```

No pip dependencies required -- uses only Python stdlib.
