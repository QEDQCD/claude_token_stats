#!/usr/bin/env python3
"""安装 claude-token-stats：把统计脚本装到 ~/.claude/，并在 settings.json 注册 Stop hook。

用法：
  python3 install.py              # 安装（幂等，可重复执行）
  python3 install.py --uninstall  # 卸载（移除 hook，保留脚本与日志）
  python3 install.py --uninstall --purge  # 卸载 hook 并删除脚本与 bin 链接

做了什么：
  1. 复制统计脚本到 ~/.claude/（Claude + Codex + 统一报告）
  2. 在 ~/.claude/settings.json 的 hooks.Stop 里注册 log_token_usage.py
  3. 在 ~/.local/bin/ 创建 token-report / tokens-detail / codex-token-stats 符号链接
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
HOOK_SCRIPT = "log_token_usage.py"
HOOK_CMD = f"python3 {HOOK_TARGET}"

SCRIPTS = [
    "log_token_usage.py",
    "token_stats.py",
    "token_stats_by_period.py",
    "codex_log.py",
    "codex_token_stats.py",
    "codex_token_stats_by_period.py",
    "token_report.py",
    "tokens_detail.py",
]

BIN_LINKS = {
    "token-report": "token_report.py",
    "tokens-detail": "tokens_detail.py",
    "codex-token-stats": "codex_token_stats_by_period.py",
}


def read_script_bytes(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if b"\r" in data:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def is_our_hook(command):
    """匹配本工具 Stop hook（允许 python3 路径前缀不同）。"""
    if not isinstance(command, str) or HOOK_SCRIPT not in command:
        return False
    for part in command.split():
        if not part.endswith(HOOK_SCRIPT):
            continue
        norm = os.path.normpath(part)
        if norm == os.path.normpath(HOOK_TARGET):
            return True
        if part.replace("\\", "/").endswith(f".claude/{HOOK_SCRIPT}"):
            return True
    return False


def load_settings(*, strict=True):
    if not os.path.exists(SETTINGS):
        return {}
    try:
        with open(SETTINGS) as fh:
            return json.load(fh)
    except (json.JSONDecodeError, ValueError):
        if strict:
            print(f"! {SETTINGS} 不是合法 JSON，已中止，请先修复。")
            if os.path.exists(SETTINGS + ".bak"):
                print(f"  可尝试恢复: cp {SETTINGS}.bak {SETTINGS}")
            sys.exit(1)
        return None


def save_settings(data):
    if os.path.exists(SETTINGS):
        shutil.copy2(SETTINGS, SETTINGS + ".bak")
    with open(SETTINGS, "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def prune_empty_hooks(settings):
    hooks = settings.get("hooks")
    if hooks == {}:
        settings.pop("hooks", None)


def stop_has_hook(settings):
    for group in settings.get("hooks", {}).get("Stop", []):
        for h in group.get("hooks", []):
            if is_our_hook(h.get("command")):
                return True
    return False


def remove_stop_hooks(settings):
    stop = settings.get("hooks", {}).get("Stop", [])
    new_stop = []
    removed = 0
    for group in stop:
        group_hooks = [
            h for h in group.get("hooks", []) if not is_our_hook(h.get("command"))
        ]
        removed += len(group.get("hooks", [])) - len(group_hooks)
        if group_hooks:
            group["hooks"] = group_hooks
            new_stop.append(group)
    if removed:
        if new_stop:
            settings.setdefault("hooks", {})["Stop"] = new_stop
        else:
            settings.get("hooks", {}).pop("Stop", None)
        prune_empty_hooks(settings)
    return removed


def install_scripts():
    os.makedirs(CLAUDE_DIR, exist_ok=True)
    for name in SCRIPTS:
        src = os.path.join(HERE, name)
        dst = os.path.join(CLAUDE_DIR, name)
        data = read_script_bytes(src)
        with open(dst, "wb") as fh:
            fh.write(data)
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


def purge_scripts():
    for name in SCRIPTS:
        path = os.path.join(CLAUDE_DIR, name)
        if os.path.isfile(path):
            os.remove(path)
            print(f"✓ 已删除 {path}")


def purge_bin_links():
    for cmd in BIN_LINKS:
        link = os.path.join(LOCAL_BIN, cmd)
        if os.path.lexists(link):
            if os.path.islink(link):
                target = os.readlink(link)
                if not is_our_bin_target(target):
                    print(f"· 跳过 {link}（非本工具链接）。")
                    continue
            os.remove(link)
            print(f"✓ 已删除 {link}")


def is_our_bin_target(target):
    norm = os.path.normpath(target)
    for script in BIN_LINKS.values():
        if norm == os.path.normpath(os.path.join(CLAUDE_DIR, script)):
            return True
    return False


def install(register_claude_hook=True):
    settings = {}
    need_hook = False
    if register_claude_hook:
        settings = load_settings(strict=True)
        need_hook = not stop_has_hook(settings)

    install_scripts()
    install_bin_links()

    if register_claude_hook:
        if need_hook:
            hooks = settings.setdefault("hooks", {})
            stop = hooks.setdefault("Stop", [])
            stop.append({
                "hooks": [{"type": "command", "command": HOOK_CMD, "timeout": 30}]
            })
            save_settings(settings)
            print(f"✓ 已在 {SETTINGS} 注册 Stop hook（原文件备份为 settings.json.bak）")
        else:
            print("✓ Stop hook 已存在，跳过注册。")
    else:
        print("· 跳过 Claude Stop hook（--codex-only 模式）。")

    print("\n完成。查看用量：")
    print("  token-report              # Claude + Codex 汇总")
    print("  tokens-detail             # 含本月按天明细")
    print("  codex-token-stats --by day")
    print(f"  python3 {os.path.join(CLAUDE_DIR, 'token_stats_by_period.py')} --by day")
    print(f"  python3 {os.path.join(CLAUDE_DIR, 'codex_token_stats_by_period.py')} --by day")

    path_dirs = os.environ.get("PATH", "").split(os.pathsep)
    if LOCAL_BIN not in path_dirs:
        print(f"\n! 提示：{LOCAL_BIN} 不在 PATH 中，直接运行 token-report / codex-token-stats 可能报 command not found。")
        print(f"  可执行: export PATH=\"{LOCAL_BIN}:$PATH\"")
        print("  或写入 ~/.bashrc / ~/.zshrc 永久生效。")
        print(f"  也可直接用: python3 {os.path.join(CLAUDE_DIR, 'token_report.py')}")


def uninstall(*, purge=False):
    settings = load_settings(strict=False)
    hook_removed = 0

    if settings is None:
        print(f"! {SETTINGS} 不是合法 JSON，无法自动移除 Stop hook。")
        if os.path.exists(SETTINGS + ".bak"):
            print(f"  可尝试恢复: cp {SETTINGS}.bak {SETTINGS}")
        if not purge:
            sys.exit(1)
    else:
        hook_removed = remove_stop_hooks(settings)
        if hook_removed:
            save_settings(settings)
            print(f"✓ 已移除 {hook_removed} 个 Stop hook（脚本与日志默认保留）。")
        else:
            print("· 未发现本工具的 Stop hook，无需改动 settings。")

    if purge:
        purge_scripts()
        purge_bin_links()
        print("✓ --purge：已删除统计脚本与 bin 链接（token_usage.jsonl 保留）。")
    elif hook_removed == 0 and settings is not None:
        print("  提示：如需删除脚本与命令，请使用 --uninstall --purge")


def main():
    ap = argparse.ArgumentParser(description="安装/卸载 claude-token-stats")
    ap.add_argument("--uninstall", action="store_true", help="移除 Stop hook（默认保留脚本与日志）")
    ap.add_argument(
        "--purge",
        action="store_true",
        help="与 --uninstall 合用：同时删除 ~/.claude/ 统计脚本与 ~/.local/bin 链接",
    )
    ap.add_argument(
        "--codex-only",
        action="store_true",
        help="仅安装统计脚本与命令行入口，不注册 Claude Stop hook（适合只装 Codex CLI 的用户）",
    )
    args = ap.parse_args()
    if args.purge and not args.uninstall:
        print("! --purge 须与 --uninstall 一起使用。")
        sys.exit(1)
    if args.uninstall:
        uninstall(purge=args.purge)
    else:
        install(register_claude_hook=not args.codex_only)


if __name__ == "__main__":
    main()
