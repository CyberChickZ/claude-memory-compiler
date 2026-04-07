---
description: "Force-flush the current conversation to today's daily log immediately, without waiting for SessionEnd. /memory:flush"
---

Manually trigger a memory flush of the current conversation. The user wants the current session's important content extracted to today's daily log NOW, not at session end.

Steps:

1. Find the current session's transcript path. It's typically at `~/.claude/projects/{project-key}/{session-id}.jsonl` where project-key is the cwd with `/` replaced by `-`.

2. Run flush.py manually with that transcript:

```bash
SESSION_ID=$(ls -t ~/.claude/projects/$(pwd | sed 's|/|-|g')/*.jsonl 2>/dev/null | head -1 | xargs -I {} basename {} .jsonl)
TRANSCRIPT=~/.claude/projects/$(pwd | sed 's|/|-|g')/${SESSION_ID}.jsonl

# Extract context using the same logic as session-end.py
python3 -c "
import json, sys
from pathlib import Path
turns = []
with open('${TRANSCRIPT}') as f:
    for line in f:
        try:
            entry = json.loads(line)
            msg = entry.get('message', {})
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role not in ('user', 'assistant'): continue
            if isinstance(content, list):
                content = '\n'.join(b.get('text','') for b in content if isinstance(b, dict) and b.get('type')=='text')
            if isinstance(content, str) and content.strip():
                label = 'User' if role == 'user' else 'Assistant'
                turns.append(f'**{label}:** {content.strip()}\n')
        except: pass
context = '\n'.join(turns[-30:])[-15000:]
Path('scripts/manual-flush-context.md').write_text(context)
print(f'Wrote {len(context)} chars, {len(turns)} turns')
"

uv run python scripts/flush.py scripts/manual-flush-context.md "${SESSION_ID}-manual"
```

3. Report what was extracted (read the newly-appended section in `daily/$(date +%Y-%m-%d).md`).
