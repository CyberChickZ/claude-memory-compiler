# INSTALL — Claude Memory Compiler 部署指南

把 AI 对话自动编译成可搜索的个人知识库. 零 API 费用 (Claude Max/Team/Enterprise 订阅即可).

---

## 0. 前置条件

| 依赖 | 用途 | 安装 |
|------|------|------|
| [Claude Code](https://claude.ai/code) | CLI, hooks 宿主 | `npm install -g @anthropic-ai/claude-code` |
| [uv](https://docs.astral.sh/uv/) | Python 环境 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python ≥ 3.12 | 脚本运行 | uv 自动处理 |
| Git | 版本控制 | 已有 |
| (可选) [Obsidian](https://obsidian.md/) | 可视化知识库 | 官网下载 |

---

## 1. 获取框架源码

```bash
# 方案 A: Fork (推荐, 之后能 pull upstream 更新)
gh repo fork coleam00/claude-memory-compiler --clone --remote
cd claude-memory-compiler

# 方案 B: 直接 clone (不需要贡献回去)
git clone https://github.com/coleam00/claude-memory-compiler.git
cd claude-memory-compiler
```

安装依赖:

```bash
uv sync
```

---

## 2. 部署到你的项目

假设你有一个项目在 `~/git/my-project/`:

```bash
PROJECT=~/git/my-project
SRC=~/git/claude-memory-compiler  # 或你 fork 的路径

# 复制框架文件
cp -r "$SRC/hooks" "$PROJECT/"
cp -r "$SRC/scripts" "$PROJECT/"
cp "$SRC/pyproject.toml" "$PROJECT/"
cp "$SRC/uv.lock" "$PROJECT/"
cp "$SRC/AGENTS.md" "$PROJECT/"

# 复制 hook 配置 + slash commands
mkdir -p "$PROJECT/.claude/commands"
cp "$SRC/.claude/settings.json" "$PROJECT/.claude/"
cp -r "$SRC/.claude/commands/memory" "$PROJECT/.claude/commands/"

# 创建记忆目录
mkdir -p "$PROJECT"/{daily,docs,knowledge/concepts,knowledge/connections}

# 安装 Python 依赖
cd "$PROJECT" && uv sync
```

---

## 3. 配置 hooks

如果你的项目已有 `.claude/settings.json`, 把下面的 hooks **合并**进去 (不要覆盖):

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python hooks/session-start.py",
            "timeout": 15
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python hooks/pre-compact.py",
            "timeout": 10
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run python hooks/session-end.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

如果没有已有的 settings.json, 直接用上面步骤 2 复制的那个就行.

---

## 4. 配置 .gitignore (倒置策略)

**核心理念**: 框架是可重新部署的 (从 upstream fork `cp` 一下就行), 真正有价值的是你的记忆数据. 所以 **git track 记忆, ignore 框架**:

在 `.gitignore` 中添加:

```gitignore
# claude-memory-compiler — INVERTED: track memories, ignore framework
# Source: github.com/<your-fork>/claude-memory-compiler
# Re-deploy: cp -r ../claude-memory-compiler/{hooks,scripts,pyproject.toml,uv.lock,AGENTS.md} .

/hooks/
/scripts/
/AGENTS.md
/pyproject.toml
/uv.lock
/reports/
/.venv/
/.claude/

# Track (these are your unique knowledge):
#   CLAUDE.md
#   daily/                   ← auto-captured conversation traces
#   knowledge/               ← LLM-compiled concept articles
#   docs/*.md                ← your manual synthesis
```

> **为什么?** 如果你 push 到 GitHub (即使 private), daily logs 包含你的对话内容. 如果这让你不舒服, 也 ignore `daily/`, 只 track `knowledge/` (编译后的, 去除了原始对话).

---

## 5. 创建 CLAUDE.md

在项目根目录创建 `CLAUDE.md`, 至少包含:

```markdown
# <项目名>

<一句话描述>

## 4 层记忆系统

​```
L1 Sources    : docs/paper_notes/*.md   (外部资料标注)
L2 Synthesis  : docs/research_*.md      (你的思考)
L3 Trace      : daily/YYYY-MM-DD.md     (SessionEnd hook 自动 capture)
L4 Compiled   : knowledge/concepts/     (LLM 编译, knowledge/index.md 入口)
​```

### 记忆操作
- `/memory:flush` — 强制提取当前对话到 daily log
- `/memory:compile` — daily logs → knowledge concepts
- `/memory:query "..."` — 查询知识库
- `/memory:lint` — 健康检查
```

你可以根据项目需要添加更多 context (行为准则、研究方向、技术约束等), 参考 `AGENTS.md` 里的完整技术文档.

---

## 6. 创建初始文件

```bash
cd ~/git/my-project

# 知识库索引
cat > knowledge/index.md << 'EOF'
# Knowledge Base Index

> Auto-compiled from `daily/` by `claude-memory-compiler`.

| Article | Summary | Compiled From | Updated |
|---------|---------|---------------|---------|
| _(empty — run `/memory:compile` after first daily log)_ | | | |
EOF

# 研究日志 (L2, 可选但推荐)
cat > docs/research_journal.md << 'EOF'
# Research Journal

> Insights, decisions, gotchas. Claude 学到新事实时应立即 append.
EOF
```

---

## 7. (可选) Obsidian 可视化

1. 打开 Obsidian → **Open folder as vault** → 选项目根目录 (e.g. `~/git/my-project/`)
2. `.obsidian/` 会自动创建在项目根
3. 加 `.obsidian/` 到 `.gitignore` (vault config 是本地状态)
4. 知识库文件使用 `[[wikilinks]]` 交叉引用, Obsidian 原生支持 graph view

---

## 8. 验证

```bash
cd ~/git/my-project
claude   # 或 claude --dangerously-skip-permissions
```

启动后检查:
- **SessionStart hook** 应该注入 L1-L4 context (你会在对话开头看到 memory protocol)
- 跑一会后, 退出 (`Ctrl+C` 或 `/exit`)
- 检查 `daily/$(date +%Y-%m-%d).md` 是否生成了 (SessionEnd hook 自动 flush)
- 检查 `scripts/flush.log` 看 flush 是否成功

手动测试编译:

```bash
uv run python scripts/compile.py
# 会读取 daily/ 里的 log, 编译成 knowledge/concepts/*.md
# 编译结果记录在 knowledge/index.md
```

---

## 9. 日常使用

### 自动 (无需干预)

| 事件 | 触发 | 效果 |
|------|------|------|
| 对话中 context 满了 | PreCompact hook | 增量 flush 到 daily log |
| 退出 Claude Code | SessionEnd hook | 增量 flush 到 daily log |
| 下午 4 点后的 flush | flush.py | 自动触发 compile.py |
| 下次打开 Claude Code | SessionStart hook | 注入 L1-L4 最新切片 |

### 手动 (slash commands)

在 Claude Code 对话中输入:
- `/memory:flush` — 立即 flush 当前对话 (不等退出)
- `/memory:compile` — 立即编译 daily logs → knowledge
- `/memory:query "什么是 X?"` — 用 index-guided retrieval 查知识库
- `/memory:lint` — 检查知识库健康 (broken links, orphans, stale articles)

### 增量 flush

flush 是增量的 — 每次只提取自上次 flush 以来的新内容. 长对话中手动 `/memory:flush` 多次完全 OK, 不会重复提取.

---

## 10. 自定义

### 时区 & 编译时间

```bash
export MEMORY_TZ="America/New_York"       # 默认 America/Los_Angeles
export MEMORY_COMPILE_HOUR=18              # 默认 16 (下午 4 点)
```

### SessionStart 注入内容

编辑 `hooks/session-start.py`:
- `PROTOCOL` 字符串: 行为准则 (citation rule, active learning 等)
- `build_context()`: 控制注入哪些 L1-L4 文件
- `MAX_CONTEXT_CHARS`: 注入上限 (默认 22K chars)
- 文件路径常量: 适配你项目的目录结构

### flush 参数

编辑 `hooks/session-end.py` 和 `hooks/pre-compact.py`:
- `MAX_CONTEXT_CHARS`: 单次 flush 上限 (默认 50K)
- `MIN_TURNS_TO_FLUSH`: 最少几个 turn 才 flush (session-end: 1, pre-compact: 3)

### 多项目共享

框架源码在一个 repo (或 fork), 部署到多个项目:

```
~/git/claude-memory-compiler/     ← 源 (git tracked)
~/git/project-A/hooks/ scripts/   ← 部署 (gitignored)
~/git/project-B/hooks/ scripts/   ← 部署 (gitignored)
```

更新时:
```bash
SRC=~/git/claude-memory-compiler
for P in ~/git/project-A ~/git/project-B; do
  cp -r "$SRC"/{hooks,scripts,pyproject.toml,uv.lock,AGENTS.md} "$P/"
done
```

---

## 架构速览

```
你的项目/
├── CLAUDE.md                    ← 项目说明 (你写)
├── docs/
│   ├── research_journal.md      ← L2: 你的 insights (你+Claude 写)
│   └── paper_notes/*.md         ← L1: 论文标注 (你写)
├── daily/
│   └── 2026-04-09.md            ← L3: 对话 trace (自动)
├── knowledge/
│   ├── index.md                 ← L4 入口: 概念索引 (自动)
│   ├── concepts/*.md            ← L4: 概念文章 (自动)
│   └── connections/*.md         ← L4: 交叉连接 (自动)
│
│  ── 以下 gitignored, 从 upstream fork 部署 ──
├── hooks/
│   ├── session-start.py         ← SessionStart: 注入 L1-L4
│   ├── pre-compact.py           ← PreCompact: 增量 flush
│   └── session-end.py           ← SessionEnd: 增量 flush
├── scripts/
│   ├── flush.py                 ← LLM 提取 → daily log
│   ├── compile.py               ← daily logs → knowledge articles
│   ├── query.py                 ← index-guided 查询
│   ├── lint.py                  ← 知识库健康检查
│   ├── config.py                ← 时区/路径/编译时间
│   └── utils.py                 ← 共享工具
├── .claude/
│   ├── settings.json            ← hook 注册
│   └── commands/memory/*.md     ← slash commands
├── pyproject.toml               ← uv 依赖声明
├── uv.lock                      ← 锁定依赖版本
└── AGENTS.md                    ← 完整技术参考
```

---

## FAQ

**Q: 需要 API key 吗?**
A: 不需要. Claude Agent SDK 用你的 Claude 订阅 (Max/Team/Enterprise). 无额外费用.

**Q: daily log 会包含敏感信息吗?**
A: 会 — daily log 是对话原文的摘要. 如果 push 到 GitHub, 建议 repo 设为 private. 或者在 `.gitignore` 里也 ignore `daily/`.

**Q: compile 一次多少钱?**
A: 包含在 Claude 订阅里 (Agent SDK 调用). 实测一次 compile 处理 ~50KB daily log 约消耗 15K input + 8K output tokens.

**Q: 能跟已有的 Claude Code hooks 共存吗?**
A: 能. 在 `.claude/settings.json` 里每个 hook event (SessionStart/PreCompact/SessionEnd) 是数组, 多个 hooks 并行执行.

**Q: Obsidian 必须吗?**
A: 不是. Obsidian 只是让 `[[wikilinks]]` 可视化. 纯命令行 + `/memory:query` 也完全能用.
