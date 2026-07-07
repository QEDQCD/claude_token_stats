---
name: claude-token-stats
description: >
  MUST USE when the user asks about Claude Code token usage / 用量 / token 统计 /
  用了多少 token / token 花费 / 用量报表, or wants a breakdown by day/week/month,
  by session, or by model. Also use for "本月用了多少 token", "今天的 token 用量",
  "按天统计 token", "哪个 session 最费 token".

  Records per-call token usage via a Stop hook into ~/.claude/token_usage.jsonl,
  then reports totals or time-bucketed stats (day/week/month) with local-timezone
  conversion, session/model filtering, and date ranges.

  NOT for: real-time cost of the current turn (use /context); pricing lookups for
  external APIs; anything unrelated to Claude Code's own token log.
metadata:
  openclaw:
    homepage: local
---

# Claude Code Token Stats

统计 Claude Code 自身的 token 用量。数据来自一个 **Stop hook**：每次会话结束时，把该会话
transcript 里每条 assistant 消息的 `usage`（输入/输出/缓存读/缓存写 tokens）按 uuid 去重后
追加写入 `~/.claude/token_usage.jsonl`。统计脚本再按需汇总。

## 组成

| 文件 | 作用 |
|---|---|
| `scripts/log_token_usage.py` | Stop hook：读 transcript，去重后把每条 assistant 消息的 usage 追加到日志 |
| `scripts/token_stats.py` | 快速总计：总量 + 按模型拆分（可选 `--session`，可选定价估算） |
| `scripts/token_stats_by_period.py` | 按 天/周/月/全部 统计，支持时区、session、model、日期区间过滤 |
| `scripts/install.py` | 幂等安装/卸载：复制脚本到 `~/.claude/`，注册/移除 Stop hook |

日志字段：`uuid, session_id, timestamp(UTC，带 Z), model, input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens`。

## 首次安装（仅一次）

如果 `~/.claude/token_usage.jsonl` 还不存在，或 `~/.claude/settings.json` 里没有对应
Stop hook，先安装：

```bash
python3 <skill_dir>/scripts/install.py
```

安装做三件事：把三个脚本复制到 `~/.claude/`；在 `settings.json` 的 `hooks.Stop` 注册
`log_token_usage.py`（去重，不动已有其它 hook）；备份原 `settings.json` 为 `.bak`。
安装后**新的会话结束**才会开始记录。

## 回答用量问题

优先用 `token_stats_by_period.py`（脚本已装到 `~/.claude/`，直接跑）：

```bash
# 按天（默认本地时区）
python3 ~/.claude/token_stats_by_period.py --by day

# 本月按天
python3 ~/.claude/token_stats_by_period.py --by day --since 2026-07-01

# 按周 / 按月
python3 ~/.claude/token_stats_by_period.py --by week
python3 ~/.claude/token_stats_by_period.py --by month

# 只看某个 session / 某个模型
python3 ~/.claude/token_stats_by_period.py --by day --session <SESSION_ID>
python3 ~/.claude/token_stats_by_period.py --by month --model glm-5.2

# 仅总计（不加 --by）
python3 ~/.claude/token_stats_by_period.py

# 简版总计 + 按模型拆分
python3 ~/.claude/token_stats.py
```

参数：
- `--by {day,week,month,all}`（默认 `all`）
- `--tz {local,utc}`（默认 `local`，把 UTC 时间戳转本地时区再分桶）
- `--since / --until YYYY-MM-DD`（含端点，按分桶时区的日期比较）
- `--session ID` / `--model NAME`

## 时区要点（常见疑问）

日志里 `timestamp` 是 **UTC**（末尾 `Z`），直接看原文件会比本地时间早/晚若干小时。
统计脚本默认 `--tz local`，读入后用 `datetime.astimezone()` 转成本机时区再分桶，
表头会标注「时区=本地时区」。只有某天存在跨零点的边界记录时，local 与 utc 结果才会不同。

## 演示（用内置示例数据，不碰真实日志）

```bash
TOKEN_LOG=<skill_dir>/examples/token_usage.sample.jsonl \
  python3 <skill_dir>/scripts/token_stats_by_period.py --by day
```

（三个脚本都支持 `TOKEN_LOG` 环境变量覆盖日志路径，默认 `~/.claude/token_usage.jsonl`。）

## 回答规范

- **必报字段**：无论问的是哪个区间，回答都要同时给出「**调用次数**」和「**token 用量**」（输入/输出/缓存读/缓存写及合计）。调用次数即脚本输出里的「调用」列，不能省略。
- 报数时说明口径：区间、时区、是否过滤了 session/model。
- token 数用千分位；缓存读通常远大于输入，属正常（长上下文命中缓存）。
- 不要臆造未记录的时间段；日志为空或 hook 未安装时，如实说明并给出安装命令。
- 绝不打印或写入任何 API key、token 密钥（本工具日志本就不含密钥）。
