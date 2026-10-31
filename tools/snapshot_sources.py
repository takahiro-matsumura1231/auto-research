#!/usr/bin/env python3
"""Record (or check) SHA-256 of the files a run depends on.

Before a registered run starts, snapshot every config, script, code file and input it reads:

    python3 tools/snapshot_sources.py --out results/<id>/run_sources.sha256 \
        configs/<id>.yaml tools/<id>_report.py src/ data/manifest.tsv

Directories are walked recursively (files under .git, __pycache__ and *.pyc are skipped).
The output is in `sha256sum` format, so `sha256sum -c` works on it too.

After the run, check nothing changed:

    python3 tools/snapshot_sources.py --check results/<id>/run_sources.sha256

Exit status 1 if any file is missing or differs.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ipynb_checkpoints"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def expand(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for p in map(Path, paths):
        if p.is_dir():
            files.extend(
                f for f in sorted(p.rglob("*"))
                if f.is_file() and not (set(f.parts) & SKIP_DIRS) and f.suffix != ".pyc"
            )
        elif p.is_file():
            files.append(p)
        else:
            sys.exit(f"not found: {p}")
    return files


def write(out: Path, paths: list[str]) -> None:
    files = expand(paths)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by tools/snapshot_sources.py"]
    lines += [f"{sha256(f)}  {f.as_posix()}" for f in files]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(files)} hashes to {out}")


def check(snapshot: Path) -> int:
    bad = 0
    n = 0
    for line in snapshot.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        digest, name = line.split(None, 1)
        name = name.lstrip("*").strip()
        n += 1
        p = Path(name)
        if not p.exists():
            print(f"MISSING  {name}")
            bad += 1
        elif sha256(p) != digest:
            print(f"CHANGED  {name}")
            bad += 1
    print(f"{n - bad}/{n} files match")
    return 1 if bad else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--check", type=Path)
    a = ap.parse_args()
    if a.check:
        sys.exit(check(a.check))
    if not a.out or not a.paths:
        ap.error("give --out and paths, or --check")
    write(a.out, a.paths)


if __name__ == "__main__":
    main()
