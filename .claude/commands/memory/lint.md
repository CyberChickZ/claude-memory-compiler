---
description: "Run knowledge base health checks — broken links, orphans, contradictions, staleness. /memory:lint"
---

Run lint checks on the knowledge base:

```bash
uv run python scripts/lint.py
```

If the user wants only structural checks (skips the LLM-based contradiction detection, free):

```bash
uv run python scripts/lint.py --structural-only
```

After completion, summarize the report:
- Errors / warnings / suggestions counts
- Most critical issues
- Path to the full report file in `reports/`
