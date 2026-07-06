#!/usr/bin/env python3
"""Stop hook: append per-call token usage from the session transcript to a JSONL log.

stdin (from Claude Code Stop hook): {"session_id":..., "transcript_path":..., ...}
Dedups by assistant-message uuid, so repeated Stop events never double-count.
"""
import json
import os
import sys

LOG = os.path.expanduser(os.environ.get("TOKEN_LOG", "~/.claude/token_usage.jsonl"))


def load_seen():
    seen = set()
    if os.path.exists(LOG):
        with open(LOG) as fh:
            for line in fh:
                try:
                    seen.add(json.loads(line)["uuid"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return seen


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    tpath = payload.get("transcript_path")
    if not tpath or not os.path.exists(tpath):
        return

    seen = load_seen()
    new_rows = []
    with open(tpath) as fh:
        for line in fh:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            uuid = entry.get("uuid")
            if not uuid or uuid in seen:
                continue
            usage = (entry.get("message") or {}).get("usage")
            if not usage:
                continue
            new_rows.append({
                "uuid": uuid,
                "session_id": payload.get("session_id", ""),
                "timestamp": entry.get("timestamp", ""),
                "model": (entry.get("message") or {}).get("model", ""),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
            })
            seen.add(uuid)

    if new_rows:
        with open(LOG, "a") as fh:
            for row in new_rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
