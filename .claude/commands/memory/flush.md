---
description: "Force-flush the current conversation to today's daily log immediately, without waiting for SessionEnd. Incremental — only flushes content since the last flush. /memory:flush"
---

Manually trigger a memory flush of the current conversation. The user wants the current session's important content extracted to today's daily log NOW, not at session end.

This flush is **incremental**: it reads from the byte offset where the last flush stopped (stored in `scripts/last-flush.json`), so long conversations are captured in chunks, not just the tail.

Steps:

1. Find the current session's transcript path. It's typically at `~/.claude/projects/{project-key}/{session-id}.jsonl` where project-key is the cwd with `/` replaced by `-`.

2. Run the incremental extraction + flush:

```bash
SESSION_ID=$(ls -t ~/.claude/projects/$(pwd | sed 's|/|-|g')/*.jsonl 2>/dev/null | head -1 | xargs -I {} basename {} .jsonl)
TRANSCRIPT=~/.claude/projects/$(pwd | sed 's|/|-|g')/${SESSION_ID}.jsonl

echo "SESSION_ID=$SESSION_ID"
echo "TRANSCRIPT exists: $(test -f "$TRANSCRIPT" && echo yes || echo no)"

# Incremental extraction: read from last flush offset
python3 -c "
import json, sys, time
from pathlib import Path

state_file = Path('scripts/last-flush.json')
state = {}
if state_file.exists():
    try: state = json.loads(state_file.read_text())
    except: pass

session_id = '${SESSION_ID}'
start_offset = 0
if state.get('session_id') == session_id:
    start_offset = state.get('byte_offset', 0)

turns = []
with open('${TRANSCRIPT}', encoding='utf-8') as f:
    f.seek(start_offset)
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
    new_offset = f.tell()

context = '\n'.join(turns)[:50000]
Path('scripts/manual-flush-context.md').write_text(context)

# Update state with new offset
state_file.write_text(json.dumps({
    'session_id': session_id,
    'timestamp': time.time(),
    'byte_offset': new_offset
}))

print(f'Wrote {len(context)} chars, {len(turns)} turns (offset {start_offset}→{new_offset})')
"

uv run python scripts/flush.py scripts/manual-flush-context.md "${SESSION_ID}-manual-$(date +%s)"
```

3. Report what was extracted (read the newly-appended section in `daily/$(date +%Y-%m-%d).md`).
