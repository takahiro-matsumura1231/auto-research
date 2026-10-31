#!/usr/bin/env python3
"""SessionStart hook: print a short brief so every session starts from the current state.

Prints the project name, the latest decision-log entries and the open rows of every round
ledger. Output goes to the agent's context. Keeps quiet if the files are missing.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
out: list[str] = []

proj = root / "project.yaml"
if proj.exists():
    text = proj.read_text(encoding="utf-8")
    m = re.search(r'^\s*name:\s*"?([^"\n]+)"?', text, re.M)
    if m:
        out.append(f"Project: {m.group(1).strip()}")
    if "TODO" in text:
        out.append("project.yaml に TODO が残っています。scripts/setup.sh を実行するか、ユーザーに値を確認してください。")

log = root / "docs/decisions/decision_log.md"
if log.exists():
    heads = re.findall(r"^## (\d{4} .*)$", log.read_text(encoding="utf-8"), re.M)
    if heads:
        out.append("Latest decisions: " + " | ".join(heads[-3:]))
        out.append(f"Next decision number: {int(heads[-1][:4]) + 1:04d}")

OPEN = ("候補", "未着手", "調査中", "設計中", "登録済", "実行中", "分析中", "保留")
for ledger in sorted((root / "docs/rounds").glob("*/README.md")):
    if ledger.parent.name.startswith("_"):
        continue
    rows = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and any(c in OPEN for c in cells):
            rows.append(f"  {cells[0]} {cells[2] if len(cells) > 2 else ''} [{next(c for c in cells if c in OPEN)}]")
    if rows:
        out.append(f"Open items in {ledger.parent.name}:")
        out.extend(rows[:12])

if out:
    print("\n".join(["[research-harness brief]"] + out + ["作業前に AGENTS.md と docs/handover.md を確認すること。"]))
