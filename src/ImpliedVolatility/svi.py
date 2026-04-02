from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import least_squares, minimize

# ---------------------------------------------------------------------------
# Core SVI math
# ---------------------------------------------------------------------------


def svi_total_variance(
    k: np.ndarray,
    a: float,
    b: float,
    rho: float,
    m: float,
    sigma: float,
) -> np.ndarray:
    """Total variance w(k) = a + b * (rho * (k - m) + sqrt((k - m)^2 + sigma^2))."""
    km = k - m
    root = np.sqrt(km**2 + sigma**2)
    return a + b * (rho * km + root)


def svi_jacobian_params(
    k: np.ndarray, a: float, b: float, rho: float, m: float, sigma: float
) -> np.ndarray:
    """Jacobian (n, 5): columns [da, db, drho, dm, dsigma] of w(k)."""
    km = k - m
    root = np.maximum(np.sqrt(km**2 + sigma**2), 1e-14)
    return np.column_stack(
        [
            np.ones_like(k),
            rho * km + root,
            b * km,
            -b * (rho + km / root),
            b * (sigma / root),
        ]
    )


def log_forward_moneyness(
    strike: np.ndarray,
    spot: np.ndarray,
    T: np.ndarray,
    r: float,
) -> np.ndarray:
    """k = log(K / F) with F = S * exp(r * T)."""
    fwd = spot * np.exp(r * np.asarray(T, dtype=np.float64))
    return np.log(np.asarray(strike, dtype=np.float64) / fwd)


def total_variance_from_iv(iv: np.ndarray, T: np.ndarray) -> np.ndarray:
    """w = sigma^2 * T."""
    iv = np.asarray(iv, dtype=np.float64)
    T = np.asarray(T, dtype=np.float64)
    return iv**2 * T


# ---------------------------------------------------------------------------
# Data preparation (load_data.merge + compute_iv output)
# ---------------------------------------------------------------------------


def prepare_svi_inputs(
    df: pd.DataFrame,
    *,
    spot_col: str = "spot",
    strike_col: str = "strike",
    T_col: str = "T",
    iv_col: str = "iv",
    r: float = 0.05,
    spread_col: Optional[str] = "spread",
) -> pd.DataFrame:
    """
    Add columns ``log_moneyness`` (k = log K/F) and ``total_var`` (w = iv^2 T).
    If ``spread_col`` is present, adds ``svi_weight`` ~ 1 / spread^2 for weighted fits.
    Drops rows with non-finite inputs or non-positive T.
    """
    out = df.copy()
    S = out[spot_col].to_numpy(dtype=np.float64)
    K = out[strike_col].to_numpy(dtype=np.float64)
    T = out[T_col].to_numpy(dtype=np.float64)
    iv = out[iv_col].to_numpy(dtype=np.float64)

    valid = (
        np.isfinite(S)
        & np.isfinite(K)
        & np.isfinite(T)
        & np.isfinite(iv)
        & (S > 0)
        & (K > 0)
        & (T > 0)
        & (iv > 0)
    )
    out = out.loc[valid].copy()
    S = out[spot_col].to_numpy(dtype=np.float64)
    K = out[strike_col].to_numpy(dtype=np.float64)
    T = out[T_col].to_numpy(dtype=np.float64)
    iv = out[iv_col].to_numpy(dtype=np.float64)

    out["log_moneyness"] = log_forward_moneyness(K, S, T, r)
    out["total_var"] = total_variance_from_iv(iv, T)
    if spread_col and spread_col in out.columns:
        sp = out[spread_col].to_numpy(dtype=np.float64)
        out["svi_weight"] = 1.0 / np.maximum(sp**2, 1e-12)
    return out


# ---------------------------------------------------------------------------
# Loss helpers (optional smooth Huber-style path via L-BFGS-B)
# ---------------------------------------------------------------------------


def huber_loss(residual: np.ndarray, delta: float = 0.01) -> np.ndarray:
    ar = np.abs(residual)
    return np.where(ar < delta, 0.5 * residual**2, delta * (ar - 0.5 * delta))


def svi_huber_objective(
    x: np.ndarray,
    k: np.ndarray,
    w_obs: np.ndarray,
    sqrt_wts: np.ndarray,
    lam: float,
) -> float:
    a, b, rho, m, sigma = x
    if b <= 0 or sigma <= 0 or abs(rho) >= 1.0:
        return 1e12
    w_fit = svi_total_variance(k, a, b, rho, m, sigma)
    resid = w_fit - w_obs
    loss = np.mean(huber_loss(sqrt_wts * resid / (np.mean(sqrt_wts) + 1e-12)))
    reg = lam * (a**2 + b**2 + m**2 + sigma**2)
    return float(loss + reg)


# ---------------------------------------------------------------------------
# Fitting
# ---------------------------------------------------------------------------


@dataclass
class SVIParams:
    a: float
    b: float
    rho: float
    m: float
    sigma: float

    def total_var(self, k: np.ndarray) -> np.ndarray:
        return svi_total_variance(k, self.a, self.b, self.rho, self.m, self.sigma)


@dataclass
class SVISliceFit:
    """Single-expiry calibration result."""

    params: SVIParams
    success: bool
    cost: float
    message: str
    n_points: int
    T_mean: float
    group_key: str


@dataclass
class SVISurfaceFit:
    slices: list[SVISliceFit]
    meta: Mapping[str, object]


def _butterfly_constraints_ok(a: float, b: float, rho: float, m: float, sigma: float) -> bool:
    """
    Gatheral-style no-butterfly constraints for raw SVI:

    - b > 0, sigma > 0, |rho| < 1
    - a + b*sigma*sqrt(1-rho^2) >= 0   (minimum variance >= 0)
    - b*(1+|rho|) < 2                  (wing slopes controlled)
    """
    if not (b > 0.0 and sigma > 0.0 and abs(rho) < 1.0):
        return False
    if a + b * sigma * np.sqrt(max(1.0 - rho * rho, 0.0)) < 0.0:
        return False
    if b * (1.0 + abs(rho)) >= 2.0:
        return False
    return True


def _butterfly_violation_terms(a: float, b: float, rho: float, m: float, sigma: float) -> np.ndarray:
    """
    Soft butterfly / wing violations as non-negative terms v_i such that
    sum(v_i**2) is the arbitrage penalty used in the loss.
    """
    # minimum variance >= 0
    min_var = a + b * sigma * np.sqrt(max(1.0 - rho * rho, 0.0))
    v_min = max(0.0, -min_var)
    # wing slope constraint b(1+|rho|) < 2
    wing = b * (1.0 + abs(rho)) - 2.0
    v_wing = max(0.0, wing)
    return np.array([v_min, v_wing], dtype=np.float64)


def _initial_guess(k: np.ndarray, w: np.ndarray) -> np.ndarray:
    m0 = float(np.average(k, weights=np.clip(w, 1e-6, None)))
    a0 = float(np.clip(np.percentile(w, 35), 1e-6, None))
    b0 = 0.25
    rho0 = -0.4
    sigma0 = 0.15
    return np.array([a0, b0, rho0, m0, sigma0], dtype=np.float64)


def _bounds(k: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    w_max = float(np.max(w) * 1.5 + 0.1)
    km = float(np.max(np.abs(k)) + 0.25)
    lo = np.array([0.0, 1e-5, -0.999, -km, 1e-4], dtype=np.float64)
    hi = np.array([w_max, 10.0, 0.999, km, 5.0], dtype=np.float64)
    return lo, hi


def fit_svi_slice(
    k: np.ndarray,
    w_obs: np.ndarray,
    *,
    weights: Optional[np.ndarray] = None,
    sqrt_weights: Optional[np.ndarray] = None,
    huber_delta: float = 0.02,
    reg_lambda: float = 1e-6,
    method: str = "least_squares",
    verbose: int = 0,
) -> tuple[SVIParams, object]:
    """
    Calibrate one SVI slice.

    Parameters
    ----------
    method
        ``least_squares`` — recommended (soft_l1 + analytic Jacobian).
        ``lbfgs`` — smooth Huber objective with L-BFGS-B (bounds).
    """
    k = np.asarray(k, dtype=np.float64).ravel()
    w_obs = np.asarray(w_obs, dtype=np.float64).ravel()
    if k.shape != w_obs.shape:
        raise ValueError("k and w_obs must have the same shape")

    if sqrt_weights is not None:
        sw = np.asarray(sqrt_weights, dtype=np.float64).ravel()
    elif weights is not None:
        wts = np.asarray(weights, dtype=np.float64).ravel()
        sw = np.sqrt(np.maximum(wts, 1e-12))
    else:
        sw = np.ones_like(w_obs)

    mask = np.isfinite(k) & np.isfinite(w_obs) & (w_obs > 0) & np.isfinite(sw)
    k, w_obs, sw = k[mask], w_obs[mask], sw[mask]
    if k.size < 5:
        raise ValueError("Need at least 5 valid points to fit SVI")

    x0 = _initial_guess(k, w_obs)
    lo, hi = _bounds(k, w_obs)

    if method == "least_squares":

        def residuals(x: np.ndarray) -> np.ndarray:
            a, b, rho, m, sig = x
            wf = svi_total_variance(k, a, b, rho, m, sig)
            if not np.all(np.isfinite(wf)) or np.any(wf <= 0.0):
                return np.full_like(w_obs, 1e3)
            return sw * (wf - w_obs)

        def jac(x: np.ndarray) -> np.ndarray:
            a, b, rho, m, sig = x
            jw = svi_jacobian_params(k, a, b, rho, m, sig)
            return sw[:, None] * jw

        sol = least_squares(
            lambda x: np.concatenate(
                [
                    residuals(x),
                    (
                        np.sqrt(reg_lambda) * _butterfly_violation_terms(*x)
                        if reg_lambda > 0.0
                        else np.zeros(2, dtype=np.float64)
                    ),
                ]
            ),
            x0,
            bounds=(lo, hi),
            loss="soft_l1",
            f_scale=huber_delta,
            ftol=1e-10,
            xtol=1e-10,
            gtol=1e-10,
            verbose=verbose,
            max_nfev=2000,
        )
        x = sol.x
        params = SVIParams(float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        return params, sol

    if method == "lbfgs":

        def obj_lbfgs(x: np.ndarray) -> float:
            a, b, rho, m, sig = x
            base = svi_huber_objective(x, k, w_obs, sw, reg_lambda)
            # soft butterfly / wing penalty (same reg_lambda weight)
            if reg_lambda > 0.0:
                v = _butterfly_violation_terms(a, b, rho, m, sig)
                base += reg_lambda * float(np.sum(v * v))
            return base

        sol = minimize(
            obj_lbfgs,
            x0,
            method="L-BFGS-B",
            bounds=list(zip(lo, hi)),
            options={"ftol": 1e-12, "maxiter": 1500},
        )
        x = sol.x
        params = SVIParams(float(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]))
        return params, sol

    raise ValueError(f"Unknown method: {method}")


def fit_svi_surface(
    df: pd.DataFrame,
    *,
    group_col: str = "expiration_date",
    T_col: str = "T",
    weight_col: Optional[str] = "svi_weight",
    min_points: int = 5,
    fit_kwargs: Optional[dict] = None,
) -> SVISurfaceFit:
    """
    Fit one SVI slice per expiry (or other grouping column).

    Expects columns from :func:`prepare_svi_inputs`: ``log_moneyness``, ``total_var``.
    """
    fit_kwargs = fit_kwargs or {}
    need = {"log_moneyness", "total_var"}
    missing = need - set(df.columns)
    if missing:
        raise KeyError(f"DataFrame missing columns {missing}; run prepare_svi_inputs first")

    slices: list[SVISliceFit] = []

    # sort groups by average maturity (for convenience only; no calendar coupling here)
    grouped: list[tuple[object, pd.DataFrame, float]] = []
    for key, g in df.groupby(group_col, sort=True):
        g = g.sort_values("log_moneyness")
        T_mean = float(g[T_col].mean()) if T_col in g.columns else float("nan")
        grouped.append((key, g, T_mean))

    grouped.sort(key=lambda tup: tup[2])

    for key, g, T_mean in grouped:
        k = g["log_moneyness"].to_numpy(dtype=np.float64)
        w = g["total_var"].to_numpy(dtype=np.float64)
        if len(g) < min_points:
            continue
        try:
            slice_kwargs = dict(fit_kwargs) if fit_kwargs else {}
            if weight_col and weight_col in g.columns:
                slice_kwargs = {**slice_kwargs, "weights": g[weight_col].to_numpy(dtype=np.float64)}
            params, raw = fit_svi_slice(k, w, **slice_kwargs)
            if hasattr(raw, "success"):
                success = bool(raw.success)  # type: ignore[attr-defined]
                msg = str(getattr(raw, "message", ""))
                cost = float(getattr(raw, "cost", np.nan))  # type: ignore[arg-type]
            else:
                success = True
                msg = ""
                cost = float("nan")
        except ValueError as e:
            slices.append(
                SVISliceFit(
                    params=SVIParams(0, 0, 0, 0, 1),
                    success=False,
                    cost=float("nan"),
                    message=str(e),
                    n_points=len(g),
                    T_mean=T_mean,
                    group_key=str(key),
                )
            )
            continue

        slices.append(
            SVISliceFit(
                params=params,
                success=success,
                cost=cost,
                message=msg,
                n_points=len(g),
                T_mean=T_mean,
                group_key=str(key),
            )
        )

    meta = {"group_col": group_col, "n_slices_attempted": df[group_col].nunique()}
    return SVISurfaceFit(slices=slices, meta=meta)


# ---------------------------------------------------------------------------
# Output tables
# ---------------------------------------------------------------------------


def surface_params_dataframe(fit: SVISurfaceFit) -> pd.DataFrame:
    """Wide table of calibrated parameters per slice."""
    rows = []
    for s in fit.slices:
        p = s.params
        rows.append(
            {
                "group_key": s.group_key,
                "T_mean": s.T_mean,
                "n_points": s.n_points,
                "success": s.success,
                "cost": s.cost,
                "a": p.a,
                "b": p.b,
                "rho": p.rho,
                "m": p.m,
                "sigma": p.sigma,
                "message": s.message,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Parameter smoothing across maturity (for calendar consistency diagnostics)
# ---------------------------------------------------------------------------


@dataclass
class SmoothedSVICurves:
    T_knots: np.ndarray
    a_spline: "UnivariateSpline"
    logb_spline: "UnivariateSpline"
    u_spline: "UnivariateSpline"  # atanh(rho)
    m_spline: "UnivariateSpline"
    logsig_spline: "UnivariateSpline"

    def params_at(self, T: np.ndarray | float) -> SVIParams | list[SVIParams]:
        T_arr = np.asarray(T, dtype=np.float64).ravel()
        a = self.a_spline(T_arr)
        b = np.exp(self.logb_spline(T_arr))
        rho = np.tanh(self.u_spline(T_arr))
        m = self.m_spline(T_arr)
        sigma = np.exp(self.logsig_spline(T_arr))
        if T_arr.size == 1:
            # a, b, rho, m, sigma are 1D arrays here; index the single element
            return SVIParams(
                float(a[0]),
                float(b[0]),
                float(rho[0]),
                float(m[0]),
                float(sigma[0]),
            )
        return [SVIParams(float(ai), float(bi), float(ri), float(mi), float(si)) for ai, bi, ri, mi, si in zip(a, b, rho, m, sigma)]

    def total_var(self, k: np.ndarray, T: np.ndarray | float) -> np.ndarray:
        T_arr = np.asarray(T, dtype=np.float64)
        if T_arr.ndim == 0:
            p = self.params_at(float(T_arr))
            return p.total_var(np.asarray(k, dtype=np.float64))
        # broadcast over grid (T_i, k_j)
        k_arr = np.asarray(k, dtype=np.float64).ravel()
        out = np.empty((T_arr.size, k_arr.size), dtype=np.float64)
        for i, Ti in enumerate(T_arr.ravel()):
            p = self.params_at(float(Ti))
            out[i, :] = p.total_var(k_arr)
        return out


def smooth_svi_parameters(
    params_df: pd.DataFrame,
    *,
    T_col: str = "T_mean",
    smooth_factor_a: float = 1e-4,
    smooth_factor_m: float = 1e-4,
    smooth_factor_others: float = 0.0,
    min_T: float = 0.0,
    weight_col: str = "n_points",
) -> SmoothedSVICurves:
    """
    Phase 4–5 from the note:

    - take per-slice parameter table (T, a, b, rho, m, sigma)
    - apply transformations (log b, atanh rho, log sigma)
    - spline-smooth each vs T.
    """
    from scipy.interpolate import UnivariateSpline

    df = params_df.copy()
    df = df[df["success"]].copy()
    df = df[np.isfinite(df[T_col])]
    df = df[df[T_col] > min_T]
    if df.empty:
        raise ValueError("smooth_svi_parameters: no valid slices after filtering.")

    df = df.sort_values(T_col).drop_duplicates(T_col)
    T = df[T_col].to_numpy(dtype=np.float64)
    a = df["a"].to_numpy(dtype=np.float64)
    b = df["b"].to_numpy(dtype=np.float64)
    rho = df["rho"].to_numpy(dtype=np.float64)
    m = df["m"].to_numpy(dtype=np.float64)
    sigma = df["sigma"].to_numpy(dtype=np.float64)

    # transformed parameters
    # normalize b and sigma by sqrt(T) to stabilize term-structure behaviour
    sqrtT = np.sqrt(np.maximum(T, 1e-8))
    logb = np.log(np.maximum(b / sqrtT, 1e-8))
    u = np.arctanh(np.clip(rho, -0.999, 0.999))
    logsig = np.log(np.maximum(sigma / sqrtT, 1e-6))

    w = df[weight_col].to_numpy(dtype=np.float64) if weight_col in df.columns else None

    # first-pass light smoothing per parameter
    a_spl_1 = UnivariateSpline(T, a, w=w, s=smooth_factor_a)
    logb_spl_1 = UnivariateSpline(T, logb, w=w, s=smooth_factor_others)
    u_spl_1 = UnivariateSpline(T, u, w=w, s=smooth_factor_others)
    m_spl_1 = UnivariateSpline(T, m, w=w, s=smooth_factor_m)
    logsig_spl_1 = UnivariateSpline(T, logsig, w=w, s=smooth_factor_others)

    a_s = a_spl_1(T)
    logb_s = logb_spl_1(T)
    u_s = u_spl_1(T)
    m_s = m_spl_1(T)
    logsig_s = logsig_spl_1(T)

    # enforce monotone ATM total variance by adjusting a(T) only
    atm_w_raw = []
    for i, (ai, lbi, ui, mi, lsi) in enumerate(zip(a_s, logb_s, u_s, m_s, logsig_s)):
        Ti = float(T[i])
        scale = np.sqrt(max(1e-8, Ti))
        pi = SVIParams(
            float(ai),
            float(np.exp(lbi) * scale),
            float(np.tanh(ui)),
            float(mi),
            float(np.exp(lsi) * scale),
        )
        atm_w_raw.append(pi.total_var(np.array([0.0], dtype=np.float64))[0])
    atm_w_raw = np.asarray(atm_w_raw, dtype=np.float64)
    atm_w_mono = np.maximum.accumulate(atm_w_raw)
    delta_a = atm_w_mono - atm_w_raw
    a_corr = a_s + delta_a

    # final splines built from corrected / smoothed arrays (with very small or zero extra smoothing)
    a_spl = UnivariateSpline(T, a_corr, w=w, s=0.0)
    logb_spl = UnivariateSpline(T, logb_s, w=w, s=0.0)
    u_spl = UnivariateSpline(T, u_s, w=w, s=0.0)
    m_spl = UnivariateSpline(T, m_s, w=w, s=0.0)
    logsig_spl = UnivariateSpline(T, logsig_s, w=w, s=0.0)

    return SmoothedSVICurves(
        T_knots=T,
        a_spline=a_spl,
        logb_spline=logb_spl,
        u_spline=u_spl,
        m_spline=m_spl,
        logsig_spline=logsig_spl,
    )


def calendar_violation_matrix(
    curves: SmoothedSVICurves,
    T_grid: np.ndarray,
    k_grid: np.ndarray,
) -> np.ndarray:
    """
    Phase 6–7 diagnostic:

    On a (T, k) grid, compute w(T_{j+1}, k) - w(T_j, k).
    Negative entries indicate calendar violations.
    """
    T_grid = np.asarray(T_grid, dtype=np.float64).ravel()
    k_grid = np.asarray(k_grid, dtype=np.float64).ravel()
    if T_grid.size < 2:
        raise ValueError("Need at least two maturities in T_grid for calendar diagnostics.")
    w = curves.total_var(k_grid, T_grid)  # shape (nT, nK)
    diff = w[1:, :] - w[:-1, :]
    return diff


def evaluate_surface_on_grid(
    fit: SVISurfaceFit,
    k_grid: np.ndarray,
    *,
    valid_only: bool = True,
) -> pd.DataFrame:
    """
    Evaluate each successful slice on ``k_grid``. Returns long DataFrame:
    ``group_key``, ``T_mean``, ``log_moneyness``, ``total_var_model``.
    """
    k_grid = np.asarray(k_grid, dtype=np.float64).ravel()
    parts = [] 
    for s in fit.slices:
        if valid_only and not s.success:
            continue
        w = s.params.total_var(k_grid)
        parts.append(
            pd.DataFrame(
                {
                    "group_key": s.group_key,
                    "T_mean": s.T_mean,
                    "log_moneyness": k_grid,
                    "total_var_model": w,
                    "iv_model": np.sqrt(np.maximum(w, 0) / np.maximum(s.T_mean, 1e-12)),
                }
            )
        )
    if not parts:
        return pd.DataFrame(
            columns=[
                "group_key",
                "T_mean",
                "log_moneyness",
                "total_var_model",
                "iv_model",
            ]
        )
    return pd.concat(parts, ignore_index=True)


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------


def plot_svi_surface_fit(
    df_prep: pd.DataFrame,
    fit: SVISurfaceFit,
    *,
    group_col: str = "expiration_date",
    n_grid: int = 120,
    iv_space: bool = True,
    figsize: tuple[float, float] = (10, 6),
    save_path: Optional[str] = None,
    show: bool = False,
) -> tuple[object, object]:
    """
    Plot market total variance (or IV) vs k with SVI overlays per expiry.

    Parameters
    ----------
    df_prep
        Output of :func:`prepare_svi_inputs` (must include ``log_moneyness``, ``total_var``, ``T``).
    """
    import matplotlib.pyplot as plt

    try:
        cmap = plt.colormaps["viridis"]
    except (AttributeError, KeyError):
        from matplotlib import cm as _cm

        cmap = _cm.get_cmap("viridis")

    fig, ax = plt.subplots(figsize=figsize)
    k_all = df_prep["log_moneyness"].to_numpy()
    k_min, k_max = float(np.min(k_all)), float(np.max(k_all))
    pad = 0.05 * (k_max - k_min + 1e-6)
    k_grid = np.linspace(k_min - pad, k_max + pad, n_grid)

    ok = [s for s in fit.slices if s.success]
    if not ok:
        ax.set_title("SVI surface fit (no successful slices)")
        return fig, ax

    n_ok = max(len(ok), 1)
    for i, s in enumerate(sorted(ok, key=lambda x: x.T_mean)):
        color = cmap(i / max(n_ok - 1, 1)) if n_ok > 1 else cmap(0.5)
        Tm = s.T_mean
        if group_col in df_prep.columns:
            sub = df_prep[df_prep[group_col].astype(str) == str(s.group_key)]
        else:
            sub = (
                df_prep[np.isclose(df_prep["T"], Tm, rtol=0.02, atol=1e-4)]
                if "T" in df_prep.columns
                else df_prep
            )

        k_m = sub["log_moneyness"].to_numpy()
        w_m = sub["total_var"].to_numpy()
        if iv_space:
            iv_m = np.sqrt(np.maximum(w_m, 0) / np.maximum(Tm, 1e-12))
            ax.scatter(k_m, iv_m, s=18, alpha=0.6, color=color, marker="o", label=None)
            wg = s.params.total_var(k_grid)
            iv_g = np.sqrt(np.maximum(wg, 0) / np.maximum(Tm, 1e-12))
            ax.plot(k_grid, iv_g, color=color, lw=2, label=f"T≈{Tm:.3f} ({s.group_key})")
            ax.set_ylabel("implied vol")
        else:
            ax.scatter(k_m, w_m, s=18, alpha=0.6, color=color, marker="o", label=None)
            ax.plot(k_grid, s.params.total_var(k_grid), color=color, lw=2, label=f"T≈{Tm:.3f}")
            ax.set_ylabel("total variance w")

    ax.set_xlabel("log moneyness log(K/F)")
    ax.legend(loc="best", fontsize=8)
    ax.set_title("SVI slices vs market")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    if show:
        plt.show()
    return fig, ax


def plot_residual_heatmap(
    df_prep: pd.DataFrame,
    fit: SVISurfaceFit,
    *,
    figsize: tuple[float, float] = (9, 4),
    save_path: Optional[str] = None,
    show: bool = False,
) -> tuple[object, object]:
    """Simple heatmap of (w_model - w_market) / w_market by slice and moneyness bin."""
    import matplotlib.pyplot as plt

    rows = []
    for _, row in df_prep.iterrows():
        k = float(row["log_moneyness"])
        w = float(row["total_var"])
        Tm = float(row["T"]) if "T" in row.index else float("nan")
        gkey = str(row.get("expiration_date", ""))
        match = None
        for s in fit.slices:
            if s.success and (str(s.group_key) == gkey or np.isclose(s.T_mean, Tm, rtol=0.05, atol=1e-3)):
                match = s
                break
        if match is None:
            continue
        w_hat = float(match.params.total_var(np.array([k]))[0])
        rel = (w_hat - w) / max(w, 1e-12)
        rows.append({"T_mean": Tm, "k": k, "rel_err": rel, "group_key": gkey})

    if not rows:
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title("No overlap for residual map")
        return fig, ax

    rdf = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=figsize)
    sc = ax.scatter(rdf["k"], rdf["T_mean"], c=rdf["rel_err"], cmap="coolwarm", s=35, vmin=-0.2, vmax=0.2)
    fig.colorbar(sc, ax=ax, label="relative w error (model - mkt) / mkt")
    ax.set_xlabel("log(K/F)")
    ax.set_ylabel("T (years)")
    ax.set_title("SVI relative variance residuals")
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, bbox_inches="tight")
    if show:
        plt.show()
    return fig, ax


# ---------------------------------------------------------------------------
# Finplot plotting (interactive)
# ---------------------------------------------------------------------------


def _rgba_to_hex(rgba: tuple[float, float, float, float]) -> str:
    r, g, b, _a = rgba
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def _maybe_import_finplot():
    try:
        import finplot as fplt  # type: ignore

        return fplt
    except Exception:
        return None


def plot_svi_surface_fit_finplot(
    df_prep: pd.DataFrame,
    fit: SVISurfaceFit,
    *,
    group_col: str = "expiration_date",
    n_grid: int = 120,
    iv_space: bool = True,
    show: bool = True,
    title: str = "SVI slices (finplot)",
):
    """
    Interactive finplot rendering of per-expiry SVI curves.

    Note: finplot is primarily interactive; saving to PDF/PNG is not implemented here.
    """
    fplt = _maybe_import_finplot()
    if fplt is None:
        raise ImportError("finplot is not installed. Use plot_backend='matplotlib' or install finplot.")

    import matplotlib.pyplot as plt

    k_all = df_prep["log_moneyness"].to_numpy(dtype=np.float64)
    k_min, k_max = float(np.min(k_all)), float(np.max(k_all))
    pad = 0.05 * (k_max - k_min + 1e-6)
    k_grid = np.linspace(k_min - pad, k_max + pad, n_grid)

    ok = [s for s in fit.slices if s.success]
    if not ok:
        ax = fplt.create_plot(title=title)
        if hasattr(ax, "setTitle"):
            ax.setTitle(title)
        if show:
            fplt.show()
        return ax, None

    try:
        cmap = plt.colormaps["viridis"]
    except (AttributeError, KeyError):
        cmap = plt.cm.get_cmap("viridis")

    # finplot uses an x/y scatter/plot model; feed numeric x arrays directly.
    ax = fplt.create_plot(title=title, rows=1)

    n_ok = max(len(ok), 1)
    for i, s in enumerate(sorted(ok, key=lambda x: x.T_mean)):
        # pick a stable color per slice index
        c = cmap(i / max(n_ok - 1, 1)) if n_ok > 1 else cmap(0.5)
        color_hex = _rgba_to_hex(c)
        Tm = s.T_mean

        if group_col in df_prep.columns:
            sub = df_prep[df_prep[group_col].astype(str) == str(s.group_key)]
        else:
            # fallback to matching close maturities
            sub = df_prep[
                np.isclose(df_prep["T"].to_numpy(dtype=np.float64), Tm, rtol=0.02, atol=1e-4)
            ]

        if sub.empty:
            continue

        k_m = sub["log_moneyness"].to_numpy(dtype=np.float64)
        if iv_space:
            y_m = np.sqrt(np.maximum(sub["total_var"].to_numpy(dtype=np.float64), 0) / max(Tm, 1e-12))
            y_g = np.sqrt(
                np.maximum(s.params.total_var(k_grid), 0) / max(Tm, 1e-12)
            )
            fplt.plot(k_m, y_m, ax=ax, style="o", color=color_hex, width=3)
            try:
                fplt.plot(
                    k_grid,
                    y_g,
                    ax=ax,
                    color=color_hex,
                    width=2,
                    legend=f"T≈{Tm:.3f}",
                )
            except TypeError:
                fplt.plot(k_grid, y_g, ax=ax, color=color_hex, width=2)
            if hasattr(ax, "setLabel"):
                ax.setLabel("left", "implied vol")
        else:
            y_m = sub["total_var"].to_numpy(dtype=np.float64)
            y_g = s.params.total_var(k_grid)
            fplt.plot(k_m, y_m, ax=ax, style="o", color=color_hex, width=3)
            try:
                fplt.plot(
                    k_grid,
                    y_g,
                    ax=ax,
                    color=color_hex,
                    width=2,
                    legend=f"T≈{Tm:.3f}",
                )
            except TypeError:
                fplt.plot(k_grid, y_g, ax=ax, color=color_hex, width=2)
            if hasattr(ax, "setLabel"):
                ax.setLabel("left", "total variance w")

    if hasattr(ax, "setLabel"):
        ax.setLabel("bottom", "log moneyness log(K/F)")
    if show:
        fplt.show()
    return ax, None


def plot_residual_heatmap_finplot(
    df_prep: pd.DataFrame,
    fit: SVISurfaceFit,
    *,
    show: bool = True,
    title: str = "SVI residuals (finplot)",
    vmin: float = -0.2,
    vmax: float = 0.2,
    n_bins: int = 11,
    max_points: int = 8000,
):
    """
    Interactive finplot residual visualization.

    Creates a color-binned scatter of relative w error (model - mkt) / mkt.
    """
    fplt = _maybe_import_finplot()
    if fplt is None:
        raise ImportError("finplot is not installed. Use plot_backend='matplotlib' or install finplot.")

    import matplotlib.pyplot as plt

    rows = []
    for _, row in df_prep.iterrows():
        k = float(row["log_moneyness"])
        w = float(row["total_var"])
        if not np.isfinite(k) or not np.isfinite(w) or w <= 0:
            continue
        Tm = float(row["T"]) if "T" in row.index else float("nan")
        gkey = str(row.get("expiration_date", ""))
        match = None
        for s in fit.slices:
            if s.success and (str(s.group_key) == gkey or np.isclose(s.T_mean, Tm, rtol=0.05, atol=1e-3)):
                match = s
                break
        if match is None:
            continue
        w_hat = float(match.params.total_var(np.array([k], dtype=np.float64))[0])
        rel = (w_hat - w) / max(w, 1e-12)
        rows.append((k, Tm, rel))

    if not rows:
        ax = fplt.create_plot(title=title)
        if show:
            fplt.show()
        return ax, None

    # optional downsampling for interactivity
    if len(rows) > max_points:
        rows = rows[:: int(np.ceil(len(rows) / max_points))]

    xs = np.array([r[0] for r in rows], dtype=np.float64)
    ys = np.array([r[1] for r in rows], dtype=np.float64)
    zs = np.array([r[2] for r in rows], dtype=np.float64)

    try:
        cmap = plt.colormaps["coolwarm"]
    except (AttributeError, KeyError):
        cmap = plt.cm.get_cmap("coolwarm")

    bins = np.linspace(vmin, vmax, n_bins + 1)
    b_idx = np.digitize(zs, bins) - 1

    ax = fplt.create_plot(title=title, rows=1)
    if hasattr(ax, "setLabel"):
        ax.setLabel("bottom", "log(K/F)")
        ax.setLabel("left", "T (years)")

    for bi in range(n_bins):
        msk = b_idx == bi
        if not np.any(msk):
            continue
        z_mid = (bins[bi] + bins[bi + 1]) / 2.0
        # map z_mid into [0,1]
        t = (z_mid - vmin) / max(vmax - vmin, 1e-12)
        rgba = cmap(np.clip(t, 0.0, 1.0))
        color_hex = _rgba_to_hex(rgba)
        fplt.plot(xs[msk], ys[msk], ax=ax, style="o", color=color_hex, width=4)

    if show:
        fplt.show()
    return ax, None


# ---------------------------------------------------------------------------
# Pipeline entrypoint for load_data-style frames
# ---------------------------------------------------------------------------


def calibrate_from_option_frame(
    option_quotes_contracts: pd.DataFrame,
    *,
    r: float = 0.05,
    group_col: str = "expiration_date",
    fit_method: str = "least_squares",
    plot: bool = True,
    plot_backend: str = "matplotlib",
    plot_path: Optional[str] = "svi_surface_fit.pdf",
    residual_path: Optional[str] = "svi_residuals.pdf",
    finplot_show: bool = True,
) -> tuple[pd.DataFrame, SVISurfaceFit, pd.DataFrame]:
    """
    Full pipeline: prepare inputs, fit SVI surface, return (prepared_df, fit, params_table).

    ``option_quotes_contracts`` should be the merged quotes frame after
    :func:`compute_iv` (columns ``spot``, ``strike``, ``T``, ``iv``, ``expiration_date``, …).
    """
    prep = prepare_svi_inputs(option_quotes_contracts, r=r)
    fit = fit_svi_surface(
        prep,
        group_col=group_col,
        fit_kwargs={"method": fit_method, "reg_lambda": 0.01},
    )
    params_df = surface_params_dataframe(fit)
    if plot and len(fit.slices) > 0:
        backend = plot_backend.lower().strip()
        fplt = _maybe_import_finplot()
        use_finplot = backend in {"finplot", "auto"} and fplt is not None
        if backend in {"finplot"} and fplt is None:
            raise ImportError("plot_backend='finplot' requested but finplot is not installed.")

        if use_finplot:
            # interactive (finplot)
            plot_svi_surface_fit_finplot(
                prep, fit, group_col=group_col, show=finplot_show
            )
            plot_residual_heatmap_finplot(prep, fit, show=finplot_show)

            # still save PDFs if requested (matplotlib backend)
            if plot_path:
                plot_svi_surface_fit(prep, fit, group_col=group_col, save_path=plot_path, show=False)
            if residual_path:
                plot_residual_heatmap(prep, fit, save_path=residual_path, show=False)
        else:
            # file-based (matplotlib)
            plot_svi_surface_fit(prep, fit, group_col=group_col, save_path=plot_path, show=False)
            plot_residual_heatmap(prep, fit, save_path=residual_path, show=False)
    return prep, fit, params_df

