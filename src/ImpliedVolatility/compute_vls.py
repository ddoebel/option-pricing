import numpy as np
import qengine
from scipy.optimize import brentq


def implied_vol(price, S, K, T, r, call):
    """
    Implied vol for each row. Arguments may be scalars or 1-D arrays-like (same length).
    """
    price = np.asarray(price, dtype=np.float64)
    S = np.asarray(S, dtype=np.float64)
    K = np.asarray(K, dtype=np.float64)
    T = np.asarray(T, dtype=np.float64)
    call = np.asarray(call, dtype=bool)
    r = float(r)

    scalar_in = price.ndim == 0
    if scalar_in:
        price = np.atleast_1d(price)
        S = np.atleast_1d(S)
        K = np.atleast_1d(K)
        T = np.atleast_1d(T)
        call = np.atleast_1d(call)

    n = price.shape[0]
    if (S.shape[0] != n or K.shape[0] != n or T.shape[0] != n or call.shape[0] != n):
        raise ValueError(
            f"implied_vol: length mismatch price={n}, S={S.shape[0]}, K={K.shape[0]}, "
            f"T={T.shape[0]}, call={call.shape[0]}"
        )

    out = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        p, s, k, t, c = float(price[i]), float(S[i]), float(K[i]), float(T[i]), bool(call[i])
        if not np.isfinite(p) or not np.isfinite(s) or not np.isfinite(k) or not np.isfinite(t):
            continue
        if s <= 0 or k <= 0 or t <= 0:
            continue
        try:
            def f(sig: float) -> float:
                return qengine.bs_price(s, k, t, r, sig, c) - p

            out[i] = brentq(f, 1e-6, 5.0)
        except (ValueError, RuntimeError):
            out[i] = np.nan

    if scalar_in:
        return float(out[0])
    return out
