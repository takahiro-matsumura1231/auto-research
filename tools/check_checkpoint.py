#!/usr/bin/env python3
"""Confirm a saved checkpoint reloads and predicts, before spending GPU time on a full run.

You provide a loader: a function `load(checkpoint_path) -> predictor`, where
`predictor(sample) -> number | list | dict | array`. This script

  1. checks the checkpoint file (or directory) exists and records its SHA-256,
  2. loads it twice, independently, and runs the predictor on the sample each time,
  3. requires the two outputs to agree (determinism of the reload path),
  4. optionally compares with the prediction the training process produced in memory
     (--expected, a JSON file holding that output), within --atol,
  5. checks the required components are present if the checkpoint is a dict-like
     torch file or a directory (--require backbone head scaler config ...).

    python3 tools/check_checkpoint.py \
        --checkpoint /data/ckpt/e01/seed0/outer0/model.pt \
        --loader mypkg.infer:load_predictor \
        --sample data/sample_input.npy \
        --expected results/e01/smoke/expected_pred.json \
        --require backbone head scaler config provenance

Writes a small JSON report next to --report (default: print only). Exit 1 on any failure.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    files = sorted(f for f in p.rglob("*") if f.is_file()) if p.is_dir() else [p]
    for f in files:
        h.update(f.relative_to(p).as_posix().encode() if p.is_dir() else b"")
        with f.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
    return h.hexdigest()


def flatten(x) -> list[float]:
    if hasattr(x, "detach"):
        x = x.detach().cpu().numpy()
    if hasattr(x, "tolist"):
        x = x.tolist()
    if isinstance(x, dict):
        return [v for k in sorted(x) for v in flatten(x[k])]
    if isinstance(x, (list, tuple)):
        return [v for item in x for v in flatten(item)]
    return [float(x)]


def close(a, b, atol: float) -> bool:
    fa, fb = flatten(a), flatten(b)
    return len(fa) == len(fb) and all(math.isclose(x, y, abs_tol=atol, rel_tol=0) for x, y in zip(fa, fb))


def components(p: Path) -> set[str]:
    if p.is_dir():
        return {f.stem for f in p.iterdir()}
    try:
        import torch  # noqa: PLC0415

        obj = torch.load(p, map_location="cpu", weights_only=False)
        return set(obj) if isinstance(obj, dict) else set()
    except Exception:  # noqa: BLE001
        return set()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--loader", required=True, help="module:function returning a predictor")
    ap.add_argument("--sample", required=True, help="passed to the predictor as-is (usually a path)")
    ap.add_argument("--expected", type=Path)
    ap.add_argument("--atol", type=float, default=1e-6)
    ap.add_argument("--require", nargs="*", default=[])
    ap.add_argument("--report", type=Path)
    a = ap.parse_args()

    sys.path.insert(0, str(Path.cwd()))
    sys.path.insert(0, str(Path.cwd() / "src"))
    report: dict = {"checkpoint": str(a.checkpoint), "ok": False}
    fail: list[str] = []

    if not a.checkpoint.exists():
        sys.exit(f"FAIL checkpoint not found: {a.checkpoint}")
    report["sha256"] = sha256(a.checkpoint)

    if a.require:
        have = components(a.checkpoint)
        missing = [c for c in a.require if c not in have]
        report["missing_components"] = missing
        if missing:
            fail.append(f"missing components: {missing} (found: {sorted(have)})")

    mod, _, fn = a.loader.partition(":")
    load = getattr(importlib.import_module(mod), fn)
    out1 = load(str(a.checkpoint))(a.sample)
    out2 = load(str(a.checkpoint))(a.sample)
    report["prediction"] = flatten(out1)[:20]
    if not close(out1, out2, a.atol):
        fail.append("two independent reloads gave different predictions")
    if a.expected:
        exp = json.loads(a.expected.read_text(encoding="utf-8"))
        if not close(out1, exp, a.atol):
            fail.append(f"reloaded prediction differs from expected (atol {a.atol})")

    report["ok"] = not fail
    report["failures"] = fail
    text = json.dumps(report, indent=2, ensure_ascii=False)
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(text + "\n", encoding="utf-8")
    print(text)
    sys.exit(0 if not fail else 1)


if __name__ == "__main__":
    main()
