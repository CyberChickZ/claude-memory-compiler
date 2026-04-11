"""
SessionStart hook - injects multi-layer knowledge + behavioral protocol.

Layers injected:
  L1 docs/paper_notes/    — paper annotations (you wrote)
  L2 docs/research_*.md   — synthesis & decisions (you wrote)
  L3 daily/               — conversation traces (auto-captured)
  L4 knowledge/index.md   — compiled knowledge (LLM-derived)

The protocol enforces:
  - Quote specific insights with citations, not file names
  - Active learning: read sources when memory is empty, don't ask
  - No hedging language ("你说得对", "我那句话偷懒了", "要我去 search 吗")
  - Append findings to research_journal.md proactively

Configure in .claude/settings.json:
{
    "hooks": {
        "SessionStart": [{
            "matcher": "",
            "command": "uv run python hooks/session-start.py"
        }]
    }
}
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Recursion guard: if we were spawned by flush.py → Agent SDK → bundled claude,
# do not inject memory protocol (it tells the bundled claude to use tools,
# which blows max_turns=2 and returns exit code 1).
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

# CWD-aware ROOT: use the project dir if it has memory framework deployed,
# otherwise fallback to the canonical repo (where this script lives).
_CWD = Path(os.getcwd())
_CANONICAL = Path(__file__).resolve().parent.parent
ROOT = _CWD if (_CWD / "scripts" / "flush.py").exists() else _CANONICAL
KNOWLEDGE_DIR = ROOT / "knowledge"
DAILY_DIR = ROOT / "daily"
DOCS_DIR = ROOT / "docs"
PAPER_NOTES_DIR = DOCS_DIR / "paper_notes"
INDEX_FILE = KNOWLEDGE_DIR / "index.md"
JOURNAL_FILE = DOCS_DIR / "research_journal.md"
PLAN_FILE = DOCS_DIR / "research_plan.md"
SUMMARY_FILE = DOCS_DIR / "research_summary.md"
RELATED_FILE = DOCS_DIR / "related_work.md"

MAX_CONTEXT_CHARS = 22_000
MAX_LOG_LINES = 25
MAX_JOURNAL_LINES = 80
MAX_PLAN_LINES = 50

PROTOCOL = """## ⚠️ MULTI-LAYER MEMORY PROTOCOL — read this first, every session

This project uses a 4-layer knowledge architecture. You must understand it BEFORE answering anything.

### The layers
- **L1 Sources**: external (papers, upstream code, datasets). You annotate them in `docs/paper_notes/*.md`.
- **L2 Synthesis**: Harry's thinking — `docs/research_journal.md` (insights/decisions), `docs/research_plan.md` (sprint), `docs/research_summary.md` (field map), `docs/related_work.md` (paper survey). **You are invited to write to research_journal.md proactively.**
- **L3 Conversation Trace**: `daily/YYYY-MM-DD.md` — auto-captured by the SessionEnd hook.
- **L4 Compiled KB**: `knowledge/concepts/`, `connections/`, `qa/` — LLM-extracted concepts, with `knowledge/index.md` as the master catalog.

### Hard behavioral rules

1. **CITATION RULE**. When you reference a paper, you MUST quote the specific insight from `docs/paper_notes/{file}.md` with line number. Format: `LARP shows X (paper_notes/03_LARP.md:42)`. **If you don't have the citation handy, READ the paper_notes file first** before making the claim. Never say "according to LARP" without the quote. Never say "memory has these candidates" by listing only filenames.

2. **ACTIVE LEARNING RULE**. If a question needs info that is NOT in CLAUDE.md / docs/ / knowledge/, you MUST fetch it yourself (Read the source code, grep the codebase, WebFetch the arXiv abstract, search the upstream repo). Then **append the findings to `docs/research_journal.md` or `knowledge/concepts/`** so it persists. **Never ask the user "要我去 search 吗?" / "你给绿灯我就去查"** — for cheap research operations, just do them and report what you found.

3. **NO HEDGING LANGUAGE**.
   - Banned: "你说得对", "我那句话偷懒了", "我先 flag 一下", "我不确定，需要查"（unless followed immediately by the query）.
   - Instead: state the corrected position and the new evidence directly. Apologies waste tokens.
   - Banned: rhetorical bullet lists summarizing your own emotional state. Just give the technical content.

4. **MEMORY CITATION RULE**. When referencing past decisions, use specific dates and file pointers. Format: `On 2026-04-04 you decided Mamba3 d128 (research_journal.md:67)`. Never say "之前你提到过" without the date and line.

5. **PROACTIVE NOTE-TAKING**. When you learn something new during the conversation that isn't in any doc — a verified fact, a confirmed gotcha, a decision rationale — **append it to `docs/research_journal.md` immediately**, not at session end. Use this format:
   ```
   ## YYYY-MM-DD HH:MM — {topic}
   {1-3 sentence insight with source citations}
   ```

6. **NO BROAD QUESTIONS WHEN ANSWERS EXIST**. Before asking "你想做哪个方向" or "你要 A 还是 B", check: did the user's recent research_journal entries already specify a direction? If yes, proceed on that direction and only ask if you find an actual contradiction.

### What's in this injection (below)
Sections L1/L2/L3/L4 with the most recent / highest-signal content from each layer. **You still need to Read the full files when relevant** — these excerpts are pointers, not substitutes.
"""


def tail_lines(path: Path, n: int) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-n:] if len(lines) > n else lines)


def get_recent_log() -> str:
    today = datetime.now(timezone.utc).astimezone()
    for offset in range(2):
        date = today - timedelta(days=offset)
        log_path = DAILY_DIR / f"{date.strftime('%Y-%m-%d')}.md"
        if log_path.exists():
            return tail_lines(log_path, MAX_LOG_LINES)
    return "(no recent daily log)"


def list_paper_notes() -> str:
    if not PAPER_NOTES_DIR.exists():
        return "(no paper_notes/ directory)"
    notes = sorted(PAPER_NOTES_DIR.glob("*.md"))
    if not notes:
        return "(empty)"
    rows = ["| File | Title |", "|------|-------|"]
    for note in notes:
        try:
            title = ""
            for line in note.read_text(encoding="utf-8").splitlines():
                stripped = line.strip().lstrip("#").strip()
                if stripped:
                    title = stripped[:90]
                    break
            rows.append(f"| `docs/paper_notes/{note.name}` | {title} |")
        except Exception:
            rows.append(f"| `docs/paper_notes/{note.name}` | (read error) |")
    rows.append("")
    rows.append("**Reminder**: do not list these as 'candidates'. To cite any of them you must Read the file first.")
    return "\n".join(rows)


def build_context() -> str:
    parts = []

    today = datetime.now(timezone.utc).astimezone()
    parts.append(f"## Today\n{today.strftime('%A, %B %d, %Y')}")
    parts.append(PROTOCOL)

    if JOURNAL_FILE.exists():
        journal_excerpt = tail_lines(JOURNAL_FILE, MAX_JOURNAL_LINES)
        parts.append(
            f"## L2: Recent research_journal.md (last {MAX_JOURNAL_LINES} lines)\n\n"
            f"_The full file is the source of truth. Read it when in doubt._\n\n"
            f"```markdown\n{journal_excerpt}\n```"
        )
    else:
        parts.append("## L2: research_journal.md\n\n(file does not exist yet)")

    if PLAN_FILE.exists():
        plan_excerpt = tail_lines(PLAN_FILE, MAX_PLAN_LINES)
        parts.append(
            f"## L2: Recent research_plan.md (last {MAX_PLAN_LINES} lines)\n\n"
            f"```markdown\n{plan_excerpt}\n```"
        )

    parts.append(f"## L1: Paper Notes Inventory\n\n{list_paper_notes()}")

    if INDEX_FILE.exists():
        index_content = INDEX_FILE.read_text(encoding="utf-8")
        parts.append(f"## L4: Compiled Knowledge Base Index\n\n{index_content}")
    else:
        parts.append("## L4: Compiled Knowledge Base Index\n\n(empty — run `/memory:compile` after the first daily log accumulates)")

    parts.append(f"## L3: Recent Conversation Trace\n\n{get_recent_log()}")

    context = "\n\n---\n\n".join(parts)

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated — Read the full files)"

    return context


def main():
    context = build_context()
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
