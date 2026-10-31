#!/usr/bin/env python3
"""PreToolUse hook: keep append-only research records append-only.

Protected:
  * docs/decisions/decision_log.md          append-only
  * docs/rounds/*/progress.md               append-only
  * docs/protocols/*_protocol.md            append-only once it contains a "registered" marker
  * configs/*.yaml with `registered: true`  frozen (no change at all; raise the version instead)

An Edit is allowed on an append-only file only when `new_string` starts with `old_string`
(i.e. text is added after an existing anchor, nothing is removed or rewritten). A Write is
allowed only when the new content starts with the current content.

Bash commands that obviously rewrite these files in place (sed -i, truncating redirection,
rm, mv, truncate) are blocked too. This is a best-effort guard, not a sandbox.

Exit code 2 blocks the tool call and shows stderr to the agent.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import Path

APPEND_ONLY_GLOBS = [
    "docs/decisions/decision_log.md",
    "docs/rounds/*/progress.md",
]
PROTOCOL_GLOB = "docs/protocols/*_protocol.md"
CONFIG_GLOB = "configs/*.yaml"
REGISTERED_PROTOCOL = re.compile(r"^(状態|Status)\s*[:：]\s*\**\s*(登録済|registered)", re.M | re.I)
REGISTERED_CONFIG = re.compile(r"^registered\s*:\s*true\b", re.M | re.I)


def repo_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()


def rel(path: str) -> str | None:
    root = repo_root()
    p = Path(path)
    if not p.is_absolute():
        p = root / p
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def classify(relpath: str) -> str | None:
    """Return 'append', 'frozen' or None for a repo-relative path."""
    if "/_template" in relpath:
        return None
    if any(fnmatch.fnmatch(relpath, g) for g in APPEND_ONLY_GLOBS):
        return "append"
    full = repo_root() / relpath
    if fnmatch.fnmatch(relpath, PROTOCOL_GLOB) and full.exists():
        if REGISTERED_PROTOCOL.search(full.read_text(encoding="utf-8", errors="replace")):
            return "append"
    if fnmatch.fnmatch(relpath, CONFIG_GLOB) and full.exists():
        if REGISTERED_CONFIG.search(full.read_text(encoding="utf-8", errors="replace")):
            return "frozen"
    return None


def block(msg: str) -> None:
    print(msg, file=sys.stderr)
    sys.exit(2)


def check_edits(relpath: str, kind: str, edits: list[dict]) -> None:
    if kind == "frozen":
        block(
            f"{relpath} は登録済み（registered: true）の設定です。変更せず、版を上げた新しい設定ファイルを作り、"
            "判断ログに理由を追記してください。"
        )
    for e in edits:
        old, new = e.get("old_string", ""), e.get("new_string", "")
        if not new.startswith(old):
            block(
                f"{relpath} は追記専用です。既存の文を変更・削除する編集は許可されていません。"
                "old_string の後ろに追記する形（new_string が old_string で始まる）にするか、"
                "訂正は新しい項目として末尾に追記してください。"
            )


def check_write(relpath: str, kind: str, content: str) -> None:
    full = repo_root() / relpath
    if not full.exists():
        return
    if kind == "frozen":
        check_edits(relpath, kind, [])
    current = full.read_text(encoding="utf-8", errors="replace")
    if not content.startswith(current.rstrip("\n")):
        block(
            f"{relpath} は追記専用です。Write で全体を書き換えるときは、既存の内容をそのまま先頭に残し、"
            "末尾に追記してください。"
        )


BASH_DANGER = re.compile(r"(sed\s+(-[a-zA-Z]*i|--in-place)|(?<![>])>(?!>)\s*\S|\btruncate\b|\brm\b|\bmv\b|\bperl\s+-[a-zA-Z]*i)")


def check_bash(command: str) -> None:
    targets = ["decision_log.md", "progress.md", "_protocol.md"]
    if not any(t in command for t in targets):
        return
    if BASH_DANGER.search(command):
        block(
            "判断ログ・progress・プロトコルを Bash で上書き・削除・in-place 編集するコマンドは止めています。"
            "追記は Edit ツールか `>>` で行ってください。"
        )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}

    if tool == "Bash":
        check_bash(ti.get("command", ""))
        return

    path = ti.get("file_path") or ti.get("notebook_path")
    if not path:
        return
    relpath = rel(path)
    if relpath is None:
        return
    kind = classify(relpath)
    if kind is None:
        return

    if tool == "Edit":
        check_edits(relpath, kind, [ti])
    elif tool == "MultiEdit":
        check_edits(relpath, kind, ti.get("edits", []))
    elif tool == "Write":
        check_write(relpath, kind, ti.get("content", ""))


if __name__ == "__main__":
    main()
