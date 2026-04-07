---
description: "Manually trigger knowledge base compilation — compiles all new/changed daily logs into structured knowledge articles. /memory:compile"
---

Run the knowledge base compilation manually using the Bash tool:

```bash
uv run python scripts/compile.py
```

After it completes, briefly summarize:
- How many daily logs were processed
- How many concept articles were created or updated
- The total cost reported
- Any errors

If the user passes `--all` or `force`, use `uv run python scripts/compile.py --all` to recompile everything.
If they pass `--dry-run`, use `--dry-run` to preview without writing.
