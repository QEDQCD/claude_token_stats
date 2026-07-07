# claude-token-stats

一个 Claude Code **skill**：自动记录并统计 Claude Code 自身的 token 用量，支持按
天 / 周 / 月汇总，可按 session、模型、日期区间过滤，时间戳自动转本地时区。

导入 Claude Code 后，直接问「本月用了多少 token」「按天统计一下用量」「哪个 session 最费 token」
即可触发。

---

## 对话示例

导入 skill 后，直接用自然语言提问即可触发。例如：

> **用户**：本月用了多少 token
>
> Claude 会自动运行 `python3 ~/.claude/token_stats_by_period.py --by day --since 2026-07-01`，
> 然后给出（示例）：

```
# token 用量 · 按天 · 时区=本地时区 · since=2026-07-01
区间            调用        输入       输出  缓存写       缓存读         合计
-----------------------------------------------------------------------------
2026-07-01    268 次     199,520    153,370       0   19,635,325   19,988,215
2026-07-02    849 次   3,314,970    503,777       0   86,258,319   90,077,066
2026-07-03    630 次   2,260,624    859,033       0   53,310,293   56,429,950
2026-07-04    147 次     839,030    171,534       0   14,617,664   15,628,228
2026-07-05    237 次   1,042,106    253,850       0   23,151,296   24,447,252
2026-07-06    755 次   6,016,861    436,416       0   73,752,261   80,205,538
-----------------------------------------------------------------------------
合计        2,886 次  13,673,111  2,377,980       0  270,725,158  286,776,249
```

> **本月合计 2.87 亿 tokens、2,886 次调用**，其中缓存读 2.71 亿（占约 94%，长上下文命中缓存的
> 正常现象）；真正新增输入 1,367 万、输出 238 万。费用主要看输入/输出，缓存读单价通常很低。

其它可直接说的话术：「按天统计一下用量」「这个月哪天最费 token」「按模型拆一下」
「只看某个 session 的用量」——都会命中本 skill。

---

## 安装

### 方式一：作为 skill 导入（推荐）

把整个目录放到 Claude Code 的 skills 目录，让 Claude 能自动发现并调用：

```bash
cp -r claude-token-stats ~/.claude/skills/
```

然后运行内置安装脚本，注册 Stop hook 并把统计脚本装到 `~/.claude/`：

```bash
python3 ~/.claude/skills/claude-token-stats/scripts/install.py
```

安装脚本是**幂等**的：
- 复制 `log_token_usage.py`、`token_stats.py`、`token_stats_by_period.py` 到 `~/.claude/`；
- 在 `~/.claude/settings.json` 的 `hooks.Stop` 注册 hook（已存在则跳过，不影响其它 hook）；
- 改动前自动备份 `settings.json` → `settings.json.bak`。

> ⚠️ 记录从**安装后新开的会话**结束时开始。已经进行中的会话不会补记。

### 方式二：只用命令行工具（不作为 skill）

只想手动跑统计，同样执行 `install.py` 即可；之后用下面的命令查看。

### 卸载

```bash
python3 ~/.claude/skills/claude-token-stats/scripts/install.py --uninstall
```

只移除 Stop hook，**保留**已产生的日志与脚本。

---

## 使用

安装后脚本位于 `~/.claude/`，直接运行：

```bash
# 按天（默认本地时区）
python3 ~/.claude/token_stats_by_period.py --by day

# 本月按天
python3 ~/.claude/token_stats_by_period.py --by day --since 2026-07-01

# 按周（ISO 周） / 按月
python3 ~/.claude/token_stats_by_period.py --by week
python3 ~/.claude/token_stats_by_period.py --by month

# 只看某个 session
python3 ~/.claude/token_stats_by_period.py --by day --session <SESSION_ID>

# 只看某个模型
python3 ~/.claude/token_stats_by_period.py --by month --model glm-5.2

# 仅总计
python3 ~/.claude/token_stats_by_period.py

# 简版总计 + 按模型
python3 ~/.claude/token_stats.py
```

### 参数

| 参数 | 说明 | 默认 |
|---|---|---|
| `--by {day,week,month,all}` | 统计维度 | `all`（仅总计） |
| `--tz {local,utc}` | 分桶时区 | `local` |
| `--since YYYY-MM-DD` | 起始日期（含） | 无 |
| `--until YYYY-MM-DD` | 结束日期（含） | 无 |
| `--session ID` | 只统计某 session | 无 |
| `--model NAME` | 只统计某模型 | 无 |

### 输出示例

```
# token 用量 · 按天 · 时区=本地时区
区间           调用          输入        输出   缓存写       缓存读        合计
------------------------------------------------------------------------------
2026-07-01    268 次      199,520    153,370       0   19,635,325   19,988,215
2026-07-02    849 次    3,314,970    503,777       0   86,258,319   90,077,066
------------------------------------------------------------------------------
合计        4,831 次  103,699,955  4,177,097       0  408,966,914  516,843,966
```

---

## 它是怎么工作的

```
会话结束 (Stop 事件)
      │
      ▼
log_token_usage.py            ← Stop hook：读本次会话 transcript，
      │                          把每条 assistant 消息的 usage 按 uuid 去重
      ▼
~/.claude/token_usage.jsonl   ← 一行一条记录的用量日志（UTC 时间戳）
      │
      ├─► token_stats.py               总计 + 按模型拆分
      └─► token_stats_by_period.py     按 天/周/月 统计，多维过滤 + 本地时区
```

日志每行示例（见 `examples/token_usage.sample.jsonl`）：

```json
{"uuid":"...","session_id":"...","timestamp":"2026-07-01T03:21:25.075Z","model":"auto","input_tokens":2,"output_tokens":214,"cache_creation_input_tokens":0,"cache_read_input_tokens":0}
```

---

## 时区说明

日志里的 `timestamp` 是 **UTC**（末尾带 `Z`），所以**直接打开 `token_usage.jsonl`
看到的时间**会和本地时间相差你所在时区的偏移（如东八区差 8 小时）。

统计脚本默认 `--tz local`，读入后用 `datetime.astimezone()` 转成本机时区再分桶，
表头标注「时区=本地时区」。只有当某天存在**跨零点的边界记录**时，`local` 与 `utc`
的分桶结果才会出现差异。

---

## 用示例数据试跑（不动真实日志）

三个脚本都支持用环境变量 `TOKEN_LOG` 覆盖日志路径：

```bash
TOKEN_LOG=./examples/token_usage.sample.jsonl \
  python3 ./scripts/token_stats_by_period.py --by day
```

---

## 目录结构

```
claude-token-stats/
├── SKILL.md                          # skill 元数据 + 触发词 + 用法（供 Claude 读取）
├── README.md                         # 本文件
├── scripts/
│   ├── install.py                    # 幂等安装/卸载
│   ├── log_token_usage.py            # Stop hook：写日志
│   ├── token_stats.py                # 总计 + 按模型
│   └── token_stats_by_period.py      # 按天/周/月统计
└── examples/
    └── token_usage.sample.jsonl      # 脱敏示例数据
```

---

## 隐私与安全

- 日志只包含 token 计数、模型名、session id、UTC 时间戳，**不含任何提示词内容、也不含 API key**。
- 安装脚本会备份并最小化改动 `settings.json`，不会打印任何密钥。
- `token_usage.jsonl` 是你的个人用量数据，请勿提交到公开仓库。

---

## 实测备注

- 用本工具实测：**火山（Volcano）的 coding plan 实际额度，只有官网宣称（6000 次 / 5 小时）的三分之一左右**。可自行核对。
