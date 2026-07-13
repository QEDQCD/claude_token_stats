---
name: claude-token-stats
description: >
  MUST USE when the user asks about Claude Code or Codex token usage / 用量 / token 统计 /
  用了多少 token / token 花费 / 用量报表, or wants a breakdown by day/week/month,
  by session, or by model. Also use for "本月用了多少 token", "今天的 token 用量",
  "按天统计 token", "哪个 session 最费 token", "Codex 用了多少", "Claude 和 Codex 合计用量".

  Claude Code: records per-call token usage via a Stop hook into ~/.claude/token_usage.jsonl.
  Codex: reads ~/.codex/sessions/**/*.jsonl event_msg.token_count deltas (no hook needed).
  Unified report via token-report / token-report --detail.

  NOT for: real-time cost of the current turn (use /context); Cursor IDE usage (no local log,
  check cursor.com/settings → Usage); pricing lookups for external APIs.
metadata:
  openclaw:
    homepage: local
---

# Claude Code + Codex Token Stats

统计 **Claude Code** 与 **Codex CLI** 的本机 token 用量。

| 来源 | 数据路径 | 采集方式 |
|---|---|---|
| Claude Code | `~/.claude/token_usage.jsonl` | Stop hook 自动写入 |
| Codex | `~/.codex/sessions/**/*.jsonl` | 读取已有会话日志（无需安装 hook） |
| Cursor | 无本地日志 | 请查看 https://cursor.com/settings → Usage |

## 组成

| 文件 | 作用 |
|---|---|
| `scripts/log_token_usage.py` | Stop hook：Claude transcript → JSONL 日志 |
| `scripts/token_stats.py` | Claude 快速总计 + 按模型拆分 |
| `scripts/token_stats_by_period.py` | Claude 按 天/周/月 统计 |
| `scripts/codex_log.py` | Codex 会话日志解析（共享模块） |
| `scripts/codex_token_stats.py` | Codex 快速总计 |
| `scripts/codex_token_stats_by_period.py` | Codex 按 天/周/月 统计 |
| `scripts/token_report.py` | 统一报告：今日/本月/全部（Claude + Codex + Cursor 提示） |
| `scripts/tokens_detail.py` | `tokens-detail` 命令入口（等同 `token-report --detail`） |
| `scripts/install.py` | 幂等安装/卸载 |

安装后还会在 `~/.local/bin/` 创建：
- `token-report` → 统一报告
- `tokens-detail` → 含本月按天明细（等同 `token-report --detail`）
- `codex-token-stats` → Codex 按周期统计

## 首次安装（仅一次）

```bash
python3 <skill_dir>/scripts/install.py
```

安装：复制脚本到 `~/.claude/`；注册 Claude Stop hook；创建 `~/.local/bin` 符号链接。
Codex 无需 hook，只要本机有 `~/.codex/sessions/` 即可统计。

## 回答用量问题

**优先用统一报告**（最快概览 Claude + Codex）：

```bash
token-report                  # 今日 + 本月 + 全部
token-report --detail         # 再加本月按天明细
```

**分项查询**：

```bash
# Claude 按天
python3 ~/.claude/token_stats_by_period.py --by day

# Codex 按天
python3 ~/.claude/codex_token_stats_by_period.py --by day
# 或
codex-token-stats --by day

# Claude 本月
python3 ~/.claude/token_stats_by_period.py --by day --since 2026-07-01

# Codex 本月
codex-token-stats --by day --since 2026-07-01

# 简版总计
python3 ~/.claude/token_stats.py          # Claude
python3 ~/.claude/codex_token_stats.py    # Codex
```

Claude 参数：`--by {day,week,month,all}`、`--tz {local,utc}`、`--since/--until`、`--session`、`--model`

Codex 参数：`--by {day,week,month,all}`、`--tz {local,utc}`、`--since/--until`
（Codex 日志无 session/model 字段，暂不支持这两项过滤）

## Codex 数据说明

Codex 会话 JSONL 中 `event_msg.token_count` 的 `total_token_usage` 是**会话累计值**。
统计脚本对相邻事件做 delta，得到每次调用的增量。字段：输入、缓存读、输出（无 cache_creation）。

环境变量：
- `TOKEN_LOG` — Claude 日志路径（默认 `~/.claude/token_usage.jsonl`）
- `CODEX_SESSIONS_DIR` — Codex 会话目录（默认 `~/.codex/sessions`）

## 时区要点

Claude 日志 `timestamp` 是 UTC（末尾 `Z`）。两个统计脚本默认 `--tz local`，转本地时区后分桶。

## Cursor 用量

`cursor-agent` CLI **不提供**本地 token 统计命令（`about`/`status` 仅显示账号与版本）。
Cursor IDE 用量需在网页 https://cursor.com/settings → Usage 查看。统一报告会提示这一点。

## 回答规范

- **称呼**：回答用户问题时必须称呼用户「**主人**」。
- **必报字段**：无论问的是哪个区间，回答都要同时给出「**调用次数**」和「**token 用量**」。
  - Claude：输入/输出/缓存读/缓存写及合计
  - Codex：输入/缓存读/输出及合计
- 用户问「全部工具用量」时，分别报 Claude 和 Codex，并说明 Cursor 需网页查看。
- 报数时说明口径：区间、时区、数据来源。
- token 数用千分位；缓存读通常远大于输入，属正常。
- 不要臆造未记录的时间段；日志为空或 hook 未安装时，如实说明并给出安装命令。
- 绝不打印或写入任何 API key、token 密钥。
