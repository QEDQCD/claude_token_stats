#!/usr/bin/env python3
"""Summarize ~/.claude/token_usage.jsonl. Usage: python3 token_stats.py [--session ID]"""
import json
import os
import sys
from collections import defaultdict

LOG = os.path.expanduser(os.environ.get("TOKEN_LOG", "~/.claude/token_usage.jsonl"))

# Ark 定价未知时按 0 处理；如需估算改这里 (输入/输出 每 token 单价)
PRICE_IN = float(os.environ.get("TOK_PRICE_IN", "0"))
PRICE_OUT = float(os.environ.get("TOK_PRICE_OUT", "0"))


def main():
    session_filter = None
    if "--session" in sys.argv:
        session_filter = sys.argv[sys.argv.index("--session") + 1]

    if not os.path.exists(LOG):
        print("no log yet:", LOG)
        return

    rows = []
    with open(LOG) as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if session_filter:
        rows = [r for r in rows if r.get("session_id") == session_filter]

    def s(key):
        return sum((r.get(key) or 0) for r in rows)

    ti, to = s("input_tokens"), s("output_tokens")
    cr = s("cache_read_input_tokens")
    denom = ti + cr
    hit = f"{100.0 * cr / denom:.1f}%" if denom > 0 else "-"

    print(f"调用次数:   {len(rows):,}")
    print(f"输入 tokens: {ti:,}")
    print(f"输出 tokens: {to:,}")
    print(f"缓存读取:   {cr:,}")
    print(f"缓存命中率: {hit}")
    if PRICE_IN or PRICE_OUT:
        print(f"预估费用:   {ti * PRICE_IN + to * PRICE_OUT:.4f}")

    by_model = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        m = by_model[r.get("model", "?")]
        m[0] += 1
        m[1] += r.get("input_tokens") or 0
        m[2] += r.get("output_tokens") or 0
    print("\n按模型:")
    for model, (n, i, o) in sorted(by_model.items()):
        print(f"  {model}: {n} 次  in={i:,}  out={o:,}")


if __name__ == "__main__":
    main()
