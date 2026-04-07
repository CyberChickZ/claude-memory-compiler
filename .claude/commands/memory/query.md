---
description: "Query the knowledge base — index-guided retrieval, no RAG. Pass the question as args. /memory:query <question>"
---

Run a query against the knowledge base:

```bash
uv run python scripts/query.py "$ARGUMENTS"
```

If the user wants the answer saved back to the KB as a Q&A article, add `--file-back`:

```bash
uv run python scripts/query.py "$ARGUMENTS" --file-back
```

After the query completes, present the answer cleanly. If `--file-back` was used, mention the new qa article path.
