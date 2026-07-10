#!/usr/bin/env python3
"""按时间维度统计 ~/.codex/sessions/**/*.jsonl 的 token 用量。

从 event_msg.token_count 的 total_token_usage 累计值计算每次调用的 delta。

示例：
  python3 codex_token_stats_by_period.py --by day
  python3 codex_token_stats_by_period.py --by day --since 2026-07-01
  python3 codex_token_stats_by_period.py            # 仅总计
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from codex_log import FIELDS, SESSIONS_DIR, iter_deltas


def bucket_key(dt, by):
    if by == "day":
        return dt.strftime("%Y-%m-%d")
    if by == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    if by == "month":
        return dt.strftime("%Y-%m")
    return "全部"


def disp_width(s):
    import unicodedata

    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, width, align=">"):
    s = str(s)
    gap = max(0, width - disp_width(s))
    return (" " * gap + s) if align == ">" else (s + " " * gap)


def fmt_row(cells, widths, aligns):
    return "  ".join(pad(c, w, a) for c, w, a in zip(cells, widths, aligns))


def new_agg():
    a = {"n": 0, "total": 0}
    for key, _ in FIELDS:
        a[key] = 0
    return a


def add_delta(agg, delta):
    agg["n"] += 1
    for key, _ in FIELDS:
        v = delta.get(key, 0)
        agg[key] += v
        agg["total"] += v


def load_rows(args):
    rows = []
    if not os.path.isdir(SESSIONS_DIR):
        return rows
    use_local = args.tz == "local"
    for dt, delta in iter_deltas(SESSIONS_DIR, use_local):
        day = dt.strftime("%Y-%m-%d")
        if args.since and day < args.since:
            continue
        if args.until and day > args.until:
            continue
        if args.tz == "utc":
            dt = dt.astimezone(timezone.utc)
        rows.append({"_dt": dt, **delta})
    return rows


def main():
    ap = argparse.ArgumentParser(description="统计 Codex 会话日志 token 用量")
    ap.add_argument("--by", choices=["day", "week", "month", "all"], default="all")
    ap.add_argument("--since", help="YYYY-MM-DD（含）")
    ap.add_argument("--until", help="YYYY-MM-DD（含）")
    ap.add_argument("--tz", choices=["utc", "local"], default="local")
    args = ap.parse_args()

    if not os.path.isdir(SESSIONS_DIR):
        print("暂无 Codex 会话目录:", SESSIONS_DIR)
        return

    rows = load_rows(args)
    if not rows:
        print("无匹配记录。")
        return

    buckets = defaultdict(new_agg)
    grand = new_agg()
    for r in rows:
        k = bucket_key(r["_dt"], args.by)
        for agg in (buckets[k], grand):
            add_delta(agg, r)

    columns = [("区间", None, "<"), ("调用", lambda a: f"{a['n']:,} 次", ">")]
    columns += [(name, (lambda k: lambda a: f"{a[k]:,}")(key), ">") for key, name in FIELDS]
    columns += [("合计", lambda a: f"{a['total']:,}", ">")]

    headers = [c[0] for c in columns]
    aligns = [c[2] for c in columns]

    def row_cells(label, agg):
        return [label] + [fn(agg) for _, fn, _ in columns[1:]]

    all_rows = [row_cells(k, buckets[k]) for k in sorted(buckets)]
    all_rows.append(row_cells("合计", grand))

    widths = [
        max([disp_width(headers[i])] + [disp_width(r[i]) for r in all_rows])
        for i in range(len(headers))
    ]

    tz_label = "本地时区" if args.tz == "local" else "UTC"
    by_label = {"day": "按天", "week": "按周(ISO)", "month": "按月", "all": "总计"}[args.by]
    scope = []
    if args.since:
        scope.append(f"since={args.since}")
    if args.until:
        scope.append(f"until={args.until}")
    print(
        f"# Codex token 用量 · {by_label} · 时区={tz_label}"
        + (f" · {' '.join(scope)}" if scope else "")
    )

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
