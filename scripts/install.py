#!/usr/bin/env python3
"""安装 claude-token-stats：把统计脚本装到 ~/.claude/，并在 settings.json 注册 Stop hook。

用法：
  python3 install.py            # 安装（幂等，可重复执行）
  python3 install.py --uninstall # 卸载（移除 hook，保留已产生的日志与脚本）

做了什么：
  1. 复制统计脚本到 ~/.claude/（Claude + Codex + 统一报告）
  2. 在 ~/.claude/settings.json 的 hooks.Stop 里注册 log_token_usage.py
  3. 在 ~/.local/bin/ 创建 token-report / codex-token-stats 符号链接
  4. 备份改动前的 settings.json 到 settings.json.bak

不会碰 token_usage.jsonl（你的真实用量数据），也不会打印任何密钥。
"""
import argparse
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.expanduser("~/.claude")
LOCAL_BIN = os.path.expanduser("~/.local/bin")
SETTINGS = os.path.join(CLAUDE_DIR, "settings.json")
HOOK_TARGET = os.path.join(CLAUDE_DIR, "log_token_usage.py")
HOOK_CMD = f"python3 {HOOK_TARGET}"

SCRIPTS = [
    "log_token_usage.py",
    "token_stats.py",
    "token_stats_by_period.py",
    "codex_log.py",
    "codex_token_stats.py",
    "codex_token_stats_by_period.py",
    "token_report.py",
]

# ~/.local/bin 下的命令名 → ~/.claude/ 里的脚本名
BIN_LINKS = {
    "token-report": "token_report.py",
    "codex-token-stats": "codex_token_stats_by_period.py",
}


def load_settings():
    if not os.path.exists(SETTINGS):
        return {}
    try:
        with open(SETTINGS) as fh:
            return json.load(fh)
    except (json.JSONDecodeError, ValueError):
        print(f"! {SETTINGS} 不是合法 JSON，已中止，请先修复。")
        sys.exit(1)


def save_settings(data):
    if os.path.exists(SETTINGS):
        shutil.copy2(SETTINGS, SETTINGS + ".bak")
    with open(SETTINGS, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def stop_has_hook(settings):
    for group in settings.get("hooks", {}).get("Stop", []):
        for h in group.get("hooks", []):
            if h.get("command") == HOOK_CMD:
                return True
    return False


def install_scripts():
    os.makedirs(CLAUDE_DIR, exist_ok=True)
    for name in SCRIPTS:
        src = os.path.join(HERE, name)
        dst = os.path.join(CLAUDE_DIR, name)
        shutil.copy2(src, dst)
        os.chmod(dst, 0o755)
        print(f"✓ 已安装 {dst}")


def install_bin_links():
    os.makedirs(LOCAL_BIN, exist_ok=True)
    for cmd, script in BIN_LINKS.items():
        target = os.path.join(CLAUDE_DIR, script)
        link = os.path.join(LOCAL_BIN, cmd)
        if os.path.islink(link) or os.path.isfile(link):
            if os.path.realpath(link) == os.path.realpath(target):
                print(f"✓ {link} 已指向正确目标，跳过。")
                continue
            os.remove(link)
        os.symlink(target, link)
        print(f"✓ 已链接 {link} → {target}")


def install():
    install_scripts()
    install_bin_links()

    settings = load_settings()
    if stop_has_hook(settings):
        print("✓ Stop hook 已存在，跳过注册。")
    else:
        hooks = settings.setdefault("hooks", {})
        stop = hooks.setdefault("Stop", [])
        stop.append({
            "hooks": [{"type": "command", "command": HOOK_CMD, "timeout": 30}]
        })
        save_settings(settings)
        print(f"✓ 已在 {SETTINGS} 注册 Stop hook（原文件备份为 settings.json.bak）")

    print("\n完成。查看用量：")
    print("  token-report              # Claude + Codex 汇总")
    print("  token-report --detail     # 含本月按天明细")
    print(f"  python3 {os.path.join(CLAUDE_DIR, 'token_stats_by_period.py')} --by day")
    print(f"  python3 {os.path.join(CLAUDE_DIR, 'codex_token_stats_by_period.py')} --by day")


def uninstall():
    settings = load_settings()
    stop = settings.get("hooks", {}).get("Stop", [])
    new_stop = []
    removed = False
    for group in stop:
        group_hooks = [h for h in group.get("hooks", []) if h.get("command") != HOOK_CMD]
        if len(group_hooks) != len(group.get("hooks", [])):
            removed = True
        if group_hooks:
            group["hooks"] = group_hooks
            new_stop.append(group)
    if removed:
        if new_stop:
            settings["hooks"]["Stop"] = new_stop
        else:
            settings["hooks"].pop("Stop", None)
        save_settings(settings)
        print("✓ 已移除 Stop hook（脚本与日志保留）。")
    else:
        print("· 未发现本工具的 Stop hook，无需改动。")


def main():
    ap = argparse.ArgumentParser(description="安装/卸载 claude-token-stats")
    ap.add_argument("--uninstall", action="store_true", help="移除 Stop hook（保留脚本与日志）")
    args = ap.parse_args()
    if args.uninstall:
        uninstall()
    else:
        install()


if __name__ == "__main__":
    main()
