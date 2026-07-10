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

```bash
cp -r claude-token-stats ~/.claude/skills/
python3 ~/.claude/skills/claude-token-stats/scripts/install.py
```

安装脚本（**幂等**）：
- 复制全部统计脚本到 `~/.claude/`
- 在 `~/.claude/settings.json` 注册 Claude Stop hook
- 在 `~/.local/bin/` 创建 `token-report`、`codex-token-stats` 符号链接
- 备份 `settings.json` → `settings.json.bak`

> Claude 记录从**安装后新开的会话**结束时开始。Codex 直接读已有会话，无需 hook。

### 卸载

```bash
python3 ~/.claude/skills/claude-token-stats/scripts/install.py --uninstall
```

只移除 Stop hook，**保留**已产生的日志与脚本。

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
