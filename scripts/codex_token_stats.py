#!/usr/bin/env python3
"""Summarize Codex token usage from ~/.codex/sessions/**/*.jsonl.

Usage: python3 codex_token_stats.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codex_log import FIELDS, SESSIONS_DIR, summarize


def main():
    if not os.path.isdir(SESSIONS_DIR):
        print("暂无 Codex 会话目录:", SESSIONS_DIR)
        return

    agg = summarize()
    if agg is None or agg["n"] == 0:
        print("无匹配记录。")
        return

    print(f"调用次数:   {agg['n']:,}")
    for key, label in FIELDS:
        print(f"{label} tokens: {agg[key]:,}")
    print(f"合计:       {agg['total']:,}")


if __name__ == "__main__":
    main()
