# instructions/

Context-aware instruction files with frontmatter metadata.

## Contents

- `.md` files with YAML frontmatter (id, name, keywords)
- Matched by keyword and injected into Claude's conversation context

## Format

```markdown
---
id: unique-instruction-id
name: Human-Readable Name
keywords: [keyword1, keyword2, keyword3]
---

Instruction content here...
```

## Important

- `tool-reminder.js` matches user prompts against keywords in frontmatter.
- Matched instructions are injected as context alongside skill/MCP suggestions.
- `instruction_manager.py` in `managers/` handles CRUD operations on these files.
- Each file must have a unique `id` in its frontmatter.
