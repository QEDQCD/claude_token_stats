#!/usr/bin/env python3
"""按时间维度统计 ~/.claude/token_usage.jsonl 的 token 用量。

统计维度：--by {day,week,month,all}（默认 all，即只出总计）。
可叠加过滤：--session ID、--model NAME、--since YYYY-MM-DD、--until YYYY-MM-DD。
时区：--tz {utc,local}（默认 local，把 UTC 时间戳转本地时区分桶）。

示例：
  python3 token_stats_by_period.py --by day
  python3 token_stats_by_period.py --by week --since 2026-06-01
  python3 token_stats_by_period.py --by month --model glm-5.2
  python3 token_stats_by_period.py            # 仅总计
"""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

LOG = os.path.expanduser(os.environ.get("TOKEN_LOG", "~/.claude/token_usage.jsonl"))

FIELDS = [
    ("input_tokens", "输入"),
    ("output_tokens", "输出"),
    ("cache_creation_input_tokens", "缓存写"),
    ("cache_read_input_tokens", "缓存读"),
]


def parse_ts(ts, use_local):
    """把 ISO8601 (UTC, 带 Z) 解析成 datetime；use_local=True 转本地时区。"""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone() if use_local else dt.astimezone(timezone.utc)


def bucket_key(dt, by):
    if by == "day":
        return dt.strftime("%Y-%m-%d")
    if by == "week":
        iso = dt.isocalendar()  # (year, week, weekday)
        return f"{iso[0]}-W{iso[1]:02d}"
    if by == "month":
        return dt.strftime("%Y-%m")
    return "全部"


def load_rows(args):
    rows = []
    with open(LOG) as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if args.session and r.get("session_id") != args.session:
                continue
            if args.model and r.get("model") != args.model:
                continue
            dt = parse_ts(r.get("timestamp"), args.tz == "local")
            if dt is None:
                continue
            day = dt.strftime("%Y-%m-%d")
            if args.since and day < args.since:
                continue
            if args.until and day > args.until:
                continue
            r["_dt"] = dt
            rows.append(r)
    return rows


def disp_width(s):
    """字符串在等宽终端里的显示宽度：CJK/全角字符算 2 格。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, width, align=">"):
    """按显示宽度补空格对齐（left/right），修正中文双宽导致的错位。"""
    s = str(s)
    gap = max(0, width - disp_width(s))
    return (" " * gap + s) if align == ">" else (s + " " * gap)


def fmt_row(cells, widths, aligns):
    return "  ".join(pad(c, w, a) for c, w, a in zip(cells, widths, aligns))


def main():
    ap = argparse.ArgumentParser(description="按 天/周/月/全部 统计 token 用量")
    ap.add_argument("--by", choices=["day", "week", "month", "all"], default="all")
    ap.add_argument("--session")
    ap.add_argument("--model")
    ap.add_argument("--since", help="YYYY-MM-DD（含）")
    ap.add_argument("--until", help="YYYY-MM-DD（含）")
    ap.add_argument("--tz", choices=["utc", "local"], default="local")
    args = ap.parse_args()

    if not os.path.exists(LOG):
        print("暂无日志:", LOG)
        return

    rows = load_rows(args)
    if not rows:
        print("无匹配记录。")
        return

    def new_agg():
        a = {"n": 0, "total": 0}
        for key, _ in FIELDS:
            a[key] = 0
        return a

    buckets = defaultdict(new_agg)
    grand = new_agg()
    for r in rows:
        k = bucket_key(r["_dt"], args.by)
        for agg in (buckets[k], grand):
            agg["n"] += 1
            for key, _ in FIELDS:
                v = r.get(key) or 0
                agg[key] += v
                agg["total"] += v

    # 每列：(表头, 取值函数, 对齐)。所有行走同一套列定义，避免表头/数据错位。
    columns = [("区间", None, "<"), ("调用", lambda a: f"{a['n']:,} 次", ">")]
    columns += [(name, (lambda k: lambda a: f"{a[k]:,}")(key), ">") for key, name in FIELDS]
    columns += [("合计", lambda a: f"{a['total']:,}", ">")]

    headers = [c[0] for c in columns]
    aligns = [c[2] for c in columns]

    def row_cells(label, agg):
        return [label] + [fn(agg) for _, fn, _ in columns[1:]]

    all_rows = [row_cells(k, buckets[k]) for k in sorted(buckets)]
    all_rows.append(row_cells("合计", grand))

    # 列宽 = 该列所有单元格（含表头）显示宽度的最大值
    widths = [
        max([disp_width(headers[i])] + [disp_width(r[i]) for r in all_rows])
        for i in range(len(headers))
    ]

    tz_label = "本地时区" if args.tz == "local" else "UTC"
    by_label = {"day": "按天", "week": "按周(ISO)", "month": "按月", "all": "总计"}[args.by]
    scope = []
    if args.session:
        scope.append(f"session={args.session}")
    if args.model:
        scope.append(f"model={args.model}")
    if args.since:
        scope.append(f"since={args.since}")
    if args.until:
        scope.append(f"until={args.until}")
    print(f"# token 用量 · {by_label} · 时区={tz_label}" + (f" · {' '.join(scope)}" if scope else ""))

    header_line = fmt_row(headers, widths, aligns)
    sep = "-" * disp_width(header_line)
    print(header_line)
    print(sep)

    if args.by != "all":
        for r in all_rows[:-1]:
            print(fmt_row(r, widths, aligns))
        print(sep)
    print(fmt_row(all_rows[-1], widths, aligns))


if __name__ == "__main__":
    main()
