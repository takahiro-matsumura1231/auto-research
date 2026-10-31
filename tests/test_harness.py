"""Self-tests for the harness: the append-only hook and the number verifier.

    python3 -m pytest -q tests/
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude/hooks/guard_records.py"
VERIFY = ROOT / "tools/verify_doc_numbers.py"
SNAP = ROOT / "tools/snapshot_sources.py"


def run_hook(tmp: Path, payload: dict) -> int:
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp)}
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload), text=True,
                          env=env, capture_output=True).returncode


def make_repo(tmp: Path) -> None:
    (tmp / "docs/decisions").mkdir(parents=True)
    (tmp / "docs/decisions/decision_log.md").write_text("# Log\n\n## 0001 — a\n", encoding="utf-8")
    (tmp / "docs/rounds/r1").mkdir(parents=True)
    (tmp / "docs/rounds/r1/progress.md").write_text("# P\n\nline\n", encoding="utf-8")
    (tmp / "docs/rounds/_template").mkdir(parents=True)
    (tmp / "docs/rounds/_template/progress.md").write_text("# T\n", encoding="utf-8")
    (tmp / "docs/protocols").mkdir(parents=True)
    (tmp / "docs/protocols/e1_protocol.md").write_text("# E1\n\n状態: 登録済（2026-01-01）\n\nbody\n", encoding="utf-8")
    (tmp / "docs/protocols/e2_protocol.md").write_text("# E2\n\n状態: 下書き\n\nbody\n", encoding="utf-8")
    (tmp / "configs").mkdir()
    (tmp / "configs/e1.yaml").write_text("id: e1\nregistered: true\n", encoding="utf-8")
    (tmp / "configs/e2.yaml").write_text("id: e2\nregistered: false\n", encoding="utf-8")


def edit(path: str, old: str, new: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "old_string": old, "new_string": new}}


def test_hook_append_only(tmp_path: Path) -> None:
    make_repo(tmp_path)
    log = "docs/decisions/decision_log.md"
    assert run_hook(tmp_path, edit(log, "## 0001 — a\n", "## 0001 — a\n\n## 0002 — b\n")) == 0
    assert run_hook(tmp_path, edit(log, "## 0001 — a", "## 0001 — changed")) == 2
    assert run_hook(tmp_path, edit(str(tmp_path / log), "# Log", "# X")) == 2  # absolute path too
    prog = "docs/rounds/r1/progress.md"
    assert run_hook(tmp_path, edit(prog, "line", "replaced")) == 2
    w_ok = {"tool_name": "Write", "tool_input": {"file_path": prog, "content": "# P\n\nline\n\nmore\n"}}
    w_bad = {"tool_name": "Write", "tool_input": {"file_path": prog, "content": "# new\n"}}
    assert run_hook(tmp_path, w_ok) == 0
    assert run_hook(tmp_path, w_bad) == 2
    # templates are editable
    assert run_hook(tmp_path, edit("docs/rounds/_template/progress.md", "# T", "# U")) == 0


def test_hook_protocols_and_configs(tmp_path: Path) -> None:
    make_repo(tmp_path)
    assert run_hook(tmp_path, edit("docs/protocols/e1_protocol.md", "body", "new body")) == 2
    assert run_hook(tmp_path, edit("docs/protocols/e1_protocol.md", "body\n", "body\n\n## 追補\n")) == 0
    assert run_hook(tmp_path, edit("docs/protocols/e2_protocol.md", "body", "anything")) == 0
    assert run_hook(tmp_path, edit("configs/e1.yaml", "id: e1", "id: e1\nx: 1")) == 2
    assert run_hook(tmp_path, edit("configs/e2.yaml", "id: e2", "id: e3")) == 0


def test_hook_bash(tmp_path: Path) -> None:
    make_repo(tmp_path)
    bash = lambda c: {"tool_name": "Bash", "tool_input": {"command": c}}  # noqa: E731
    assert run_hook(tmp_path, bash("sed -i 's/a/b/' docs/decisions/decision_log.md")) == 2
    assert run_hook(tmp_path, bash("echo x > docs/rounds/r1/progress.md")) == 2
    assert run_hook(tmp_path, bash("echo x >> docs/rounds/r1/progress.md")) == 0
    assert run_hook(tmp_path, bash("cat docs/decisions/decision_log.md")) == 0


def test_verify_doc_numbers(tmp_path: Path) -> None:
    (tmp_path / "s.json").write_text(json.dumps({"a": {"mae": 2.29405, "w": [0.2955]}}), encoding="utf-8")
    (tmp_path / "t.tsv").write_text("arm\tmae\nx\t1.5\ny\t2.25\n", encoding="utf-8")
    good = tmp_path / "good.md"
    good.write_text(
        "MAE 2.2941<!-- verify: s.json:a.mae round=4 -->, "
        "w 29.55%<!-- verify: s.json:a.w[0] scale=100 -->, "
        "y **2.25**<!-- verify: t.tsv:mae@arm=y -->\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("MAE 2.30<!-- verify: s.json:a.mae -->\n", encoding="utf-8")
    r = lambda d: subprocess.run([sys.executable, str(VERIFY), d.name], cwd=tmp_path,  # noqa: E731
                                 capture_output=True, text=True)
    res = r(good)
    assert res.returncode == 0, res.stdout
    assert r(bad).returncode == 1


def test_snapshot_roundtrip(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("1", encoding="utf-8")
    run = lambda *a: subprocess.run([sys.executable, str(SNAP), *a], cwd=tmp_path,  # noqa: E731
                                    capture_output=True, text=True).returncode
    assert run("--out", "snap.sha256", "a.txt") == 0
    assert run("--check", "snap.sha256") == 0
    (tmp_path / "a.txt").write_text("2", encoding="utf-8")
    assert run("--check", "snap.sha256") == 1
