#!/usr/bin/env python3
"""统一查看 Claude Code + Codex 的 token 消耗。

默认输出：今日用量 + 本月累计 + 历史总计。
加 --detail 附带本月按天明细表（等同 tokens-detail 别名）。
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codex_log import SESSIONS_DIR, summarize as codex_summarize

CLAUDE_LOG = os.path.expanduser(
    os.environ.get("TOKEN_LOG", "~/.claude/token_usage.jsonl")
)
CLAUDE_DIR = os.path.expanduser("~/.claude")
CLAUDE_STATS = os.path.join(CLAUDE_DIR, "token_stats_by_period.py")
CODEX_STATS = os.path.join(CLAUDE_DIR, "codex_token_stats_by_period.py")

CLAUDE_FIELDS = [
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
]


def today_local():
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def month_start_local():
    now = datetime.now().astimezone()
    return now.strftime("%Y-%m-01")


def section(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def run_script(script, args):
    if not os.path.isfile(script):
        print(f"脚本不存在: {script}")
        return 1
    result = subprocess.run(
        [sys.executable, script, *args],
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0 and result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)
    return result.returncode


def claude_summary(since=None, until=None):
    if not os.path.exists(CLAUDE_LOG):
        return None
    agg = {"n": 0, "total": 0}
    for key in CLAUDE_FIELDS:
        agg[key] = 0
    with open(CLAUDE_LOG) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = r.get("timestamp")
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
            except ValueError:
                continue
            day = dt.strftime("%Y-%m-%d")
            if since and day < since:
                continue
            if until and day > until:
                continue
            agg["n"] += 1
            for key in CLAUDE_FIELDS:
                v = r.get(key) or 0
                agg[key] += v
                agg["total"] += v
    return agg


def print_compact(label, agg, kind):
    if agg is None:
        print(f"{label}: 暂无数据")
        return
    if agg["n"] == 0:
        print(f"{label}: 无记录")
        return
    if kind == "claude":
        print(
            f"{label}: {agg['n']:,} 次 | "
            f"输入 {agg['input_tokens']:,} | "
            f"输出 {agg['output_tokens']:,} | "
            f"缓存读 {agg['cache_read_input_tokens']:,} | "
            f"合计 {agg['total']:,}"
        )
    else:
        print(
            f"{label}: {agg['n']:,} 次 | "
            f"输入 {agg['input_tokens']:,} | "
            f"缓存读 {agg['cached_input_tokens']:,} | "
            f"输出 {agg['output_tokens']:,} | "
            f"合计 {agg['total']:,}"
        )


def main():
    ap = argparse.ArgumentParser(description="Claude Code + Codex token 用量报告")
    ap.add_argument(
        "--detail",
        action="store_true",
        help="附带按天明细表（本月）",
    )
    ap.add_argument(
        "--since",
        help="自定义起始日期 YYYY-MM-DD（默认本月 1 日用于「本月」统计）",
    )
    args = ap.parse_args()

    today = today_local()
    month_start = args.since or month_start_local()
    now_str = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    print(f"Token 用量报告  ·  {now_str}")

    section("Claude Code")
    print_compact("今日", claude_summary(since=today, until=today), "claude")
    print_compact("本月", claude_summary(since=month_start), "claude")
    print_compact("全部", claude_summary(), "claude")

    section("Codex")
    print_compact("今日", codex_summarize(since=today, until=today), "codex")
    print_compact("本月", codex_summarize(since=month_start), "codex")
    print_compact("全部", codex_summarize(), "codex")

    section("Cursor")
    print("本地 CLI 无 token 日志，请查看: https://cursor.com/settings → Usage")

    if args.detail:
        if os.path.exists(CLAUDE_LOG):
            section("Claude Code · 本月按天")
            run_script(CLAUDE_STATS, ["--by", "day", "--since", month_start])
        else:
            section("Claude Code · 本月按天")
            print(f"暂无日志: {CLAUDE_LOG}")

        if os.path.isdir(SESSIONS_DIR):
            section("Codex · 本月按天")
            run_script(CODEX_STATS, ["--by", "day", "--since", month_start])
        else:
            section("Codex · 本月按天")
            print(f"暂无 Codex 会话目录: {SESSIONS_DIR}")

    print()


if __name__ == "__main__":
    main()
