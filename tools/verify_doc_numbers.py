#!/usr/bin/env python3
"""Check every annotated number in a document against the file it comes from.

Annotate a number by putting a verify comment right after it:

    Markdown:  MAE was 2.2941<!-- verify: results/e01/summary.json:arms.candidate.mae round=4 -->
    LaTeX:     MAE was 2.29 % verify: results/e01/summary.json:arms.candidate.mae round=2

Source forms:
    file.json:a.b[2].c            dotted path into JSON (list index in brackets)
    file.tsv:col@key=value        column `col` of the single row where column `key` == value
    file.csv:col@k1=v1,k2=v2      several filters; .tsv is tab-separated, .csv comma-separated

Options after the source (space separated):
    round=N      compare after rounding the source to N decimals (default: decimals shown in the doc)
    scale=X      multiply the source by X first (e.g. scale=100 for a fraction shown as percent)
    tol=X        accept |doc - source| <= X instead of exact match after rounding

Paths are relative to the repository root (the current directory).

    python3 tools/verify_doc_numbers.py docs/results/e01_result.md [more docs...]

Exit status 0 when every annotated number matches, 1 otherwise. Unannotated numbers are not
checked; use --strict-tables to also report table cells with numbers but no annotation.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal
from pathlib import Path

NUM = r"([-−+]?\d[\d,]*(?:\.\d+)?)"
MD = re.compile(NUM + r"\s*%?\s*\**\s*<!--\s*verify:\s*(.+?)\s*-->")
TEX = re.compile(NUM + r"\s*\\?%?\s*\}?\s*%\s*verify:\s*(.+?)\s*$", re.M)

_cache: dict[Path, object] = {}


def load(path: Path):
    if path not in _cache:
        if path.suffix == ".json":
            _cache[path] = json.loads(path.read_text(encoding="utf-8"))
        elif path.suffix in (".tsv", ".csv"):
            with path.open(newline="", encoding="utf-8") as fh:
                _cache[path] = list(csv.DictReader(fh, delimiter="\t" if path.suffix == ".tsv" else ","))
        else:
            raise ValueError(f"unsupported source type: {path}")
    return _cache[path]


def lookup(spec: str) -> float:
    fname, _, key = spec.partition(":")
    path = Path(fname)
    if not path.exists():
        raise FileNotFoundError(fname)
    data = load(path)
    if isinstance(data, list) and path.suffix in (".tsv", ".csv"):
        col, _, filt = key.partition("@")
        rows = data
        for cond in filter(None, filt.split(",")):
            k, _, v = cond.partition("=")
            rows = [r for r in rows if r.get(k) == v]
        if len(rows) != 1:
            raise KeyError(f"{spec}: {len(rows)} rows match (need exactly 1)")
        return float(rows[0][col])
    cur = data
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", key):
        cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
    return float(cur)


def decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def check_one(shown: str, directive: str) -> tuple[bool, str]:
    parts = directive.split()
    spec, opts = parts[0], dict(p.split("=", 1) for p in parts[1:] if "=" in p)
    doc_val = Decimal(shown.replace(",", "").replace("−", "-"))
    src = Decimal(repr(lookup(spec))) * Decimal(opts.get("scale", "1"))
    if "tol" in opts:
        ok = abs(doc_val - src) <= Decimal(opts["tol"])
        return ok, f"doc {doc_val} vs source {src} (tol {opts['tol']})"
    nd = int(opts.get("round", decimals(shown.replace(",", ""))))
    q = Decimal(1).scaleb(-nd)
    up, even = src.quantize(q, ROUND_HALF_UP), src.quantize(q, ROUND_HALF_EVEN)
    ok = doc_val in (up, even)
    return ok, f"doc {doc_val} vs source {src} -> {up}"


def scan(doc: Path, strict_tables: bool) -> tuple[int, int, list[str]]:
    text = doc.read_text(encoding="utf-8")
    pattern = TEX if doc.suffix == ".tex" else MD
    n = bad = 0
    msgs: list[str] = []
    for m in pattern.finditer(text):
        n += 1
        line = text.count("\n", 0, m.start()) + 1
        try:
            ok, info = check_one(m.group(1), m.group(2))
        except Exception as e:  # noqa: BLE001 - report every failure kind the same way
            ok, info = False, f"{type(e).__name__}: {e}"
        if not ok:
            bad += 1
            msgs.append(f"{doc}:{line}: MISMATCH {m.group(1)} [{m.group(2)}] {info}")
    if strict_tables and doc.suffix == ".md":
        for i, line in enumerate(text.splitlines(), 1):
            if line.startswith("|") and re.search(r"\d\.\d", line) and "verify:" not in line and not re.match(r"^\|[\s:|-]+\|$", line):
                msgs.append(f"{doc}:{i}: UNANNOTATED table row")
    return n, bad, msgs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docs", nargs="+", type=Path)
    ap.add_argument("--strict-tables", action="store_true")
    a = ap.parse_args()
    total = total_bad = 0
    for d in a.docs:
        n, bad, msgs = scan(d, a.strict_tables)
        total, total_bad = total + n, total_bad + bad
        for msg in msgs:
            print(msg)
    print(f"{total - total_bad}/{total} annotated numbers match")
    if total == 0:
        print("warning: no verify annotations found", file=sys.stderr)
    sys.exit(1 if total_bad else 0)


if __name__ == "__main__":
    main()
