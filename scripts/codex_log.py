"""Parse Codex session JSONL logs (~/.codex/sessions/**/*.jsonl) for token deltas."""
import glob
import json
import os
from datetime import datetime, timezone

SESSIONS_DIR = os.path.expanduser(
    os.environ.get("CODEX_SESSIONS_DIR", "~/.codex/sessions")
)

FIELDS = [
    ("input_tokens", "输入"),
    ("cached_input_tokens", "缓存读"),
    ("output_tokens", "输出"),
]


def parse_ts(ts, use_local=True):
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone() if use_local else dt.astimezone(timezone.utc)


def parse_cumulative(total_usage):
    if not isinstance(total_usage, dict):
        return None
    return {
        "input_tokens": total_usage.get("input_tokens", 0),
        "cached_input_tokens": total_usage.get("cached_input_tokens", 0),
        "output_tokens": total_usage.get("output_tokens", 0),
    }


def compute_delta(prev, current):
    if prev is None:
        return current
    return {
        "input_tokens": max(0, current["input_tokens"] - prev["input_tokens"]),
        "cached_input_tokens": max(
            0, current["cached_input_tokens"] - prev["cached_input_tokens"]
        ),
        "output_tokens": max(0, current["output_tokens"] - prev["output_tokens"]),
    }


def delta_is_zero(delta):
    return all(delta.get(key, 0) == 0 for key, _ in FIELDS)


def iter_deltas(sessions_dir=None, use_local=True):
    """Yield (datetime, delta_dict) for each non-zero token_count delta."""
    root = sessions_dir or SESSIONS_DIR
    pattern = os.path.join(root, "**", "*.jsonl")
    for fp in sorted(glob.glob(pattern, recursive=True)):
        prev = None
        with open(fp) as fh:
            for line in fh:
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") != "event_msg":
                    continue
                payload = ev.get("payload") or {}
                if payload.get("type") != "token_count":
                    continue
                info = payload.get("info") or {}
                current = parse_cumulative(info.get("total_token_usage"))
                if current is None:
                    continue
                delta = compute_delta(prev, current)
                prev = current
                if delta_is_zero(delta):
                    continue
                dt = parse_ts(ev.get("timestamp"), use_local)
                if dt is None:
                    continue
                yield dt, delta


def summarize(since=None, until=None, use_local=True, sessions_dir=None):
    """Return compact summary dict or None if sessions dir missing."""
    root = sessions_dir or SESSIONS_DIR
    if not os.path.isdir(root):
        return None

    agg = {"n": 0, "total": 0}
    for key, _ in FIELDS:
        agg[key] = 0

    for dt, delta in iter_deltas(root, use_local):
        day = dt.strftime("%Y-%m-%d")
        if since and day < since:
            continue
        if until and day > until:
            continue
        agg["n"] += 1
        for key, _ in FIELDS:
            v = delta.get(key, 0)
            agg[key] += v
            agg["total"] += v
    return agg
