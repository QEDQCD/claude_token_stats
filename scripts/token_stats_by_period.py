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
import sys
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


# GitHub 贡献墙风格：字符高度 + 颜色双通道。
# 高度递增的方块（· ▂ ▄ ▆ █）即使在只有 8 色/无色的终端（如 tmux TERM=screen）
# 也能靠“填充高度”清晰区分档位，不依赖 256 色。
_HEAT_GLYPHS = ["·", "▂", "▄", "▆", "█"]  # 空 → 越来越高
# 颜色：优先 256 色亮绿梯度；若终端只有 8 色，降级到基础色（见 _color_mode）。
_HEAT_256 = [240, 34, 40, 46, 118]
_HEAT_8 = [90, 32, 32, 92, 92]  # 灰、绿、绿、亮绿、亮绿（8/16 色可用）


def _color_mode():
    """返回 '256' / '8' / 'none'：探测终端色深。"""
    if not sys.stdout.isatty():
        return "none"
    if os.environ.get("NO_COLOR"):
        return "none"
    term = os.environ.get("TERM", "")
    ct = os.environ.get("COLORTERM", "")
    if "256" in term or ct in ("truecolor", "24bit"):
        return "256"
    if term and term != "dumb":
        return "8"
    return "none"


_COLOR_MODE = _color_mode()


def _heat_level(v, thresholds):
    """按分档阈值把数值映射到 0..(len(_HEAT_GLYPHS)-1)。"""
    if v <= 0:
        return 0
    for i, t in enumerate(thresholds):
        if v <= t:
            return min(i + 1, len(_HEAT_GLYPHS) - 1)
    return len(_HEAT_GLYPHS) - 1


def _paint(level):
    g = _HEAT_GLYPHS[level]
    if _COLOR_MODE == "256":
        return f"\033[1;38;5;{_HEAT_256[level]}m{g}\033[0m"
    if _COLOR_MODE == "8":
        return f"\033[1;{_HEAT_8[level]}m{g}\033[0m"
    return g


def render_heatmap(day_totals, value_key="total"):
    """把 {YYYY-MM-DD: agg} 渲染成 GitHub 贡献墙式日历（列=周，行=周一..周日）。"""
    from datetime import date, timedelta

    days = sorted(day_totals)
    if not days:
        return "无数据。"
    start = date.fromisoformat(days[0])
    end = date.fromisoformat(days[-1])
    # 对齐到起始周的周一
    grid_start = start - timedelta(days=start.weekday())

    vals = sorted(day_totals[d][value_key] for d in days if day_totals[d][value_key] > 0)
    # 4 个分位阈值 → 5 档
    if vals:
        qs = [vals[min(len(vals) - 1, int(len(vals) * q))] for q in (0.25, 0.5, 0.75, 0.9)]
        thresholds = sorted(set(qs)) or [vals[-1]]
    else:
        thresholds = [1]

    # 逐列（周）构建
    weeks = []
    cur = grid_start
    while cur <= end:
        col = []
        for _ in range(7):
            key = cur.isoformat()
            if start <= cur <= end and key in day_totals:
                col.append((cur, _heat_level(day_totals[key][value_key], thresholds)))
            else:
                col.append((cur, -1))  # 空档（范围外或无数据）
            cur += timedelta(days=1)
        weeks.append(col)

    weekday_labels = ["一", "二", "三", "四", "五", "六", "日"]
    lines = []
    # 月份标注行：在每个月第一次出现的周列上方标月份
    month_row = [" "] * len(weeks)
    seen_month = None
    for wi, col in enumerate(weeks):
        d0 = col[0][0]
        if d0.month != seen_month:
            seen_month = d0.month
            month_row[wi] = f"{d0.month:>2}月"
    # 每列宽 2（方块+空格），月标签占位对齐
    mlbl = "     "  # 行首留给周标签
    mline = mlbl
    wi = 0
    while wi < len(weeks):
        tag = month_row[wi].strip()
        if tag:
            mline += pad(tag, 4, "<")
            wi += 2
        else:
            mline += "  "
            wi += 1
    lines.append(mline.rstrip())

    for row in range(7):
        cells = []
        for col in weeks:
            _, lvl = col[row]
            cells.append("  " if lvl < 0 else _paint(lvl) + " ")
        lines.append(f"{weekday_labels[row]}   " + "".join(cells).rstrip())

    # 图例
    legend = "少 " + "".join(_paint(i) + " " for i in range(len(_HEAT_GLYPHS))) + "多"
    lines.append("")
    lines.append(legend)
    return "\n".join(lines)


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
    ap.add_argument("--heatmap", action="store_true",
                    help="额外输出 GitHub 贡献墙式的按天 token 热力图")
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

    if args.heatmap:
        day_totals = defaultdict(new_agg)
        for r in rows:
            d = r["_dt"].strftime("%Y-%m-%d")
            agg = day_totals[d]
            agg["n"] += 1
            for key, _ in FIELDS:
                v = r.get(key) or 0
                agg[key] += v
                agg["total"] += v
        print()
        print("# 按天 token 热力图（合计 tokens · GitHub 贡献墙风格）")
        print(render_heatmap(day_totals, "total"))


if __name__ == "__main__":
    main()
