#!/usr/bin/env python3
"""Smoke test: use an installed `qengine` package (pip install .) or a dev build (cmake -> qengine/*.so)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

# Running `python scripts/this.py` puts `scripts/` on sys.path, not the repo root
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def main() -> int:
    try:
        import qengine
    except ImportError as e:
        print(
            f"Import failed ({e}). Install the package (pip install .) or build with CMake so "
            "qengine/qengine.*.so exists next to qengine/__init__.py.",
            file=sys.stderr,
        )
        return 1

    call = qengine.bs_price(100.0, 100.0, 1.0, 0.05, 0.2, True)
    put = qengine.bs_price(100.0, 100.0, 1.0, 0.05, 0.2, False)
    batch_list = qengine.bs_price(
        [100.0, 100.0],
        [100.0, 110.0],
        [1.0, 1.0],
        [0.05, 0.05],
        [0.2, 0.2],
        [True, False],
    )

    assert math.isfinite(call) and math.isfinite(put)
    assert len(batch_list) == 2 and all(math.isfinite(x) for x in batch_list)

    print("qengine.bs_price (call):", call)
    print("qengine.bs_price (put):", put)
    print("qengine.bs_price (list batch):", list(batch_list))

    try:
        import numpy as np
    except ImportError:
        print("ok: overloads callable (NumPy not installed; skipped ndarray batch test).")
        return 0

    s = np.array([100.0, 100.0], dtype=np.float64)
    k = np.array([100.0, 110.0], dtype=np.float64)
    t = np.array([1.0, 1.0], dtype=np.float64)
    r = np.array([0.05, 0.05], dtype=np.float64)
    sig = np.array([0.2, 0.2], dtype=np.float64)
    opt = np.array([True, False], dtype=bool)
    batch_np = qengine.bs_price(s, k, t, r, sig, opt)
    assert len(batch_np) == 2 and all(math.isfinite(float(x)) for x in batch_np)
    print("qengine.bs_price (ndarray batch):", [float(x) for x in batch_np])
    print("ok: overloads callable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
