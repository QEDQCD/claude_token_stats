# claude-token-stats

一个 Claude Code **skill**：自动记录并统计 **Claude Code** 与 **Codex CLI** 的本机 token 用量，
支持按天 / 周 / 月汇总，可按 session、模型、日期区间过滤（Claude），时间戳自动转本地时区。

导入 Claude Code 后，直接问「本月用了多少 token」「Claude 和 Codex 各用了多少」「按天统计一下用量」
即可触发。

---

## 数据来源

| 工具 | 日志位置 | 采集方式 |
|---|---|---|
| **Claude Code** | `~/.claude/token_usage.jsonl` | Stop hook 自动记录 |
| **Codex CLI** | `~/.codex/sessions/**/*.jsonl` | 读取会话中的 `token_count` 事件 |
| **Cursor** | 无本地日志 | 网页 [cursor.com/settings → Usage](https://cursor.com/settings) |

> `cursor-agent` CLI 不提供 token 统计命令，本工具不覆盖 Cursor IDE 用量。

---

## 对话示例

> **用户**：本月 Claude 和 Codex 各用了多少 token
>
> Claude 运行 `token-report`，给出：

```
Token 用量报告  ·  2026-07-10 10:21 CST

============================================================
  Claude Code
============================================================
今日: 340 次 | 输入 1,495,557 | 输出 236,097 | 缓存读 30,880,024 | 合计 32,611,678
本月: 5,357 次 | 输入 30,712,822 | 输出 3,990,898 | 缓存读 526,393,088 | 合计 561,096,808
全部: ...

============================================================
  Codex
============================================================
今日: 无记录
本月: 42 次 | 输入 2,826,165 | 缓存读 2,423,040 | 输出 42,775 | 合计 5,291,980
全部: ...

============================================================
  Cursor
============================================================
本地 CLI 无 token 日志，请查看: https://cursor.com/settings → Usage
```

其它可直接说的话术：「按天统计 Codex 用量」「token-report 明细」「这个月哪天最费 token」。

---

## 安装

### 系统要求

| 项目 | 说明 |
|---|---|
| **操作系统** | **Linux 或 macOS**（依赖 `~/.claude`、`~/.codex` 等 Unix 路径与符号链接；**不支持 Windows**） |
| **Python** | 3.7+（脚本均为 `python3` 标准库，无第三方依赖；用到 `datetime.fromisoformat`） |
| **Claude 统计** | 需已安装 [Claude Code](https://docs.anthropic.com/en/docs/claude-code)（**可选**，与 Codex 二选一或兼有） |
| **Codex 统计** | 需已安装 [Codex CLI](https://github.com/openai/codex) 且有过会话（**可选**，与 Claude 二选一或兼有） |
| **PATH** | `token-report`、`codex-token-stats` 安装在 `~/.local/bin/`，需该目录在 PATH 中（见下方说明） |

macOS 与 Linux 安装步骤相同；macOS 用户若命令找不到，在 `~/.zshrc` 加入
`export PATH="$HOME/.local/bin:$PATH"` 后 `source ~/.zshrc` 即可。

### 一句话让 Agent 帮你装

把下面整段复制给你的 Agent（Claude Code / Cursor / Codex 均可）：

> 请先阅读 https://github.com/QEDQCD/claude_token_stats 的 README.md「系统要求」，确认本机满足（Linux/macOS、Python 3.7+、已装 Claude Code 和/或 Codex CLI、~/.local/bin 在 PATH）；不满足则先告知我缺什么。满足后：克隆到 `~/.claude/skills/claude-token-stats`（用 Cursor 再复制到 `~/.cursor/skills/claude-token-stats`），运行 `python3 ~/.claude/skills/claude-token-stats/scripts/install.py`，验证 `token-report` 与 `codex-token-stats --by day` 能正常输出；命令找不到则帮我把 `~/.local/bin` 加入 PATH。

### 手动安装

```bash
git clone https://github.com/QEDQCD/claude_token_stats.git ~/.claude/skills/claude-token-stats
python3 ~/.claude/skills/claude-token-stats/scripts/install.py
```

安装脚本（**幂等**，可重复执行）会自动完成：

| 步骤 | 内容 |
|---|---|
| 1 | 复制全部统计脚本到 `~/.claude/` |
| 2 | 在 `~/.local/bin/` 创建 **`token-report`**、**`codex-token-stats`** 符号链接 |
| 3 | 在 `~/.claude/settings.json` 注册 Claude Stop hook |
| 4 | 备份 `settings.json` → `settings.json.bak` |

**安装后立即可用的命令**（PATH 含 `~/.local/bin` 时）：

```bash
token-report                  # Claude + Codex 汇总
token-report --detail         # 含本月按天明细
codex-token-stats --by day    # 仅 Codex 按天
codex-token-stats             # Codex 总计
```

若 PATH 未配置，可直接用 Python 调用（不依赖符号链接）：

```bash
python3 ~/.claude/token_report.py
python3 ~/.claude/codex_token_stats_by_period.py --by day
```

### Claude Code

1. 复制 skill 到 `~/.claude/skills/claude-token-stats/`（见上方手动安装）
2. 运行 `install.py` 注册 **Stop hook**
3. **新开** Claude Code 会话，会话结束后才会开始写入 `~/.claude/token_usage.jsonl`

### Codex CLI

Codex **不需要 Stop hook**，只要本机 Codex 有过会话、`~/.codex/sessions/` 存在即可统计。

```bash
# 推荐：只装 Codex 时用 --codex-only，跳过 Claude Stop hook
python3 ~/.claude/skills/claude-token-stats/scripts/install.py --codex-only
codex-token-stats --by day
```

### Cursor

```bash
cp -r ~/.claude/skills/claude-token-stats ~/.cursor/skills/
# install.py 与 Claude 共用，无需重复运行
```

之后在 Cursor Agent 对话中说「本月 token 用量」或 `/claude-token-stats` 即可触发 skill。

### 验证安装

```bash
python3 ~/.claude/skills/claude-token-stats/scripts/install.py   # 应显示「已存在，跳过」
token-report                                                     # 应输出 Claude + Codex 汇总
codex-token-stats --by day                                       # 应输出 Codex 按天表（有会话时）
```

### 卸载

```bash
python3 ~/.claude/skills/claude-token-stats/scripts/install.py --uninstall
```

只移除 Stop hook，**保留**已产生的日志与脚本。

### 只装了一个 CLI 时的兼容性

本工具**不要求** Claude 与 Codex 同时安装。缺少某一侧数据时，脚本**不会报错退出**，
只会显示「暂无数据 / 暂无日志 / 暂无目录」等提示，另一侧正常统计。

| 场景 | 安装命令 | 可用命令 | 缺失侧表现 |
|---|---|---|---|
| **只有 Claude Code** | `install.py`（默认） | `token-report`、`python3 ~/.claude/token_stats*.py` | Codex 段显示「暂无数据」 |
| **只有 Codex CLI** | `install.py --codex-only` | `codex-token-stats`、`token-report` | Claude 段显示「暂无数据」 |
| **两者都有** | `install.py`（默认） | 全部命令 | 均有数据时正常汇总 |

**实测行为**（缺文件/目录时 exit code 仍为 0）：

```text
# 无 ~/.claude/token_usage.jsonl
token-report          → Claude 段：「暂无数据」；Codex 段正常
token_stats*.py       → 「暂无日志: ...」

# 无 ~/.codex/sessions/
token-report          → Codex 段：「暂无数据」；Claude 段正常
codex-token-stats     → 「暂无 Codex 会话目录: ...」
```

**Skill / Agent**：仍可安装并触发。Agent 跑 `token-report` 时会看到一侧「暂无数据」，
不影响另一侧结果；问「Codex 用量」时优先用 `codex-token-stats`，问 Claude 时用 `token_stats*.py`。

**注意**：
- 脚本安装目录固定为 `~/.claude/`（历史原因），即使用户只装 Codex 也会创建该目录，**不依赖** Claude Code 是否已安装。
- `--codex-only` 仅跳过 Stop hook 注册；若之后安装了 Claude Code，再跑一次默认 `install.py` 即可补上 hook。
- 有目录但尚无会话记录（空目录）时，显示「无记录」而非报错。

---

## 使用

### 统一报告（推荐）

```bash
token-report                  # 今日 + 本月 + 全部
token-report --detail         # 含本月按天明细（bash 别名 tokens-detail）
```

### Claude Code

```bash
python3 ~/.claude/token_stats_by_period.py --by day
python3 ~/.claude/token_stats_by_period.py --by day --since 2026-07-01
python3 ~/.claude/token_stats_by_period.py --by month --model glm-5.2
python3 ~/.claude/token_stats.py
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `--by {day,week,month,all}` | 统计维度 | `all` |
| `--tz {local,utc}` | 分桶时区 | `local` |
| `--since / --until` | 日期区间（含端点） | 无 |
| `--session ID` | 只统计某 session | 无 |
| `--model NAME` | 只统计某模型 | 无 |

### Codex CLI

```bash
codex-token-stats --by day
codex-token-stats --by day --since 2026-07-01
python3 ~/.claude/codex_token_stats.py
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `--by {day,week,month,all}` | 统计维度 | `all` |
| `--tz {local,utc}` | 分桶时区 | `local` |
| `--since / --until` | 日期区间（含端点） | 无 |

Codex 从 `event_msg.token_count` 的累计值计算 delta，字段为输入 / 缓存读 / 输出。

环境变量 `CODEX_SESSIONS_DIR` 可覆盖默认的 `~/.codex/sessions`。

---

## 架构

```
Claude 会话结束 (Stop)
      │
      ▼
log_token_usage.py  ──► ~/.claude/token_usage.jsonl
                              │
                              ├─► token_stats.py / token_stats_by_period.py
                              │
Codex 会话日志 ───────────────┤
~/.codex/sessions/*.jsonl     │
      │                       │
      ▼                       ▼
codex_log.py (解析 delta) ──► codex_token_stats*.py
                              │
                              └─► token_report.py (统一报告)
```

---

## 目录结构

```
claude-token-stats/
├── SKILL.md
├── README.md
├── scripts/
│   ├── install.py
│   ├── log_token_usage.py              # Claude Stop hook
│   ├── token_stats.py                  # Claude 总计
│   ├── token_stats_by_period.py        # Claude 按周期
│   ├── codex_log.py                    # Codex 解析模块
│   ├── codex_token_stats.py            # Codex 总计
│   ├── codex_token_stats_by_period.py  # Codex 按周期
│   └── token_report.py                 # 统一报告
└── examples/
    └── token_usage.sample.jsonl
```

---

## 隐私与安全

- Claude 日志只含 token 计数、模型名、session id、UTC 时间戳，**不含提示词与 API key**。
- Codex 只读本地会话 JSONL 中的 token 计数字段，不修改任何文件。
- `token_usage.jsonl` 是个人用量数据，请勿提交到公开仓库。
