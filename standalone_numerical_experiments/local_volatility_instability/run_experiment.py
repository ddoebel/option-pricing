#!/usr/bin/env python3
"""
Local-volatility instability experiment (Gatheral total variance in log-moneyness).

We compare the analytic local variance σ²(y) from a quadratic total variance
w(y,T) = T(α + βy + γy²) to σ² reconstructed from a noisy discrete surface
w̃(y_i) = w(y_i)(1 + ε_i) using finite differences in y, for several levels of
multiplicative noise σ_noise. This script only produces the figure: RMSE of the
FD reconstruction vs σ_noise (log–log), with a y = σ reference line of slope 1.

Dependencies: numpy, matplotlib only (see INDEPENDENT_STANDALONE.txt).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Literal

# Prevent accidental imports from the parent repository
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT in sys.path:
    sys.path.remove(_REPO_ROOT)

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from gatheral_local_vol import (
    add_multiplicative_noise,
    analytic_local_variance_quadratic,
    central_first_derivative_uniform,
    local_variance_from_derivatives,
    quadratic_total_variance,
    second_derivative_uniform,
)

# ---------------------------------------------------------------------------
# Defaults (quadratic total variance, positive w on y ∈ [-0.5, 0.5])
# ---------------------------------------------------------------------------

ALPHA = 0.04
BETA = 0.0
GAMMA = 0.1
T_MATURITY = 1.0
Y_MIN = -0.5
Y_MAX = 0.5
N_GRID = 201


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def log_uniform_sigma_grid(n_points: int, sigma_min: float, sigma_max: float) -> np.ndarray:
    """
    Return `n_points` values of σ_noise with log₁₀(σ) equally spaced.

    This is the correct sampling for a log–log RMSE plot; it is not linspace(σ_min, σ_max).
    """
    n_points = max(4, n_points)
    if sigma_min <= 0 or sigma_max <= 0 or sigma_max < sigma_min:
        raise ValueError("Require 0 < sigma_min <= sigma_max.")
    return np.logspace(np.log10(sigma_min), np.log10(sigma_max), n_points)


def relative_pointwise_error(
    sigma2_analytic: np.ndarray, sigma2_fd: np.ndarray, eps: float = 1e-12
) -> np.ndarray:
    return (sigma2_fd - sigma2_analytic) / np.maximum(np.abs(sigma2_analytic), eps)


def rmse_absolute(
    sigma2_analytic: np.ndarray,
    sigma2_fd: np.ndarray,
    interior: slice,
) -> float:
    """RMSE of (σ²_FD − σ²_analytic) on interior indices."""
    sa = np.asarray(sigma2_analytic, dtype=float)[interior]
    sf = np.asarray(sigma2_fd, dtype=float)[interior]
    m = np.isfinite(sa) & np.isfinite(sf)
    if not np.any(m):
        return float("nan")
    d = sf[m] - sa[m]
    return float(np.sqrt(np.mean(d * d)))


def rmse_relative(
    sigma2_analytic: np.ndarray,
    sigma2_fd: np.ndarray,
    interior: slice,
    eps: float = 1e-12,
) -> float:
    """RMSE over grid points of relative error (σ²_FD − σ²_analytic) / |σ²_analytic|."""
    re = relative_pointwise_error(sigma2_analytic, sigma2_fd, eps=eps)[interior]
    m = np.isfinite(re)
    if not np.any(m):
        return float("nan")
    return float(np.sqrt(np.mean(re[m] ** 2)))


def local_variance_one_draw(
    y: np.ndarray,
    h: float,
    alpha: float,
    beta: float,
    gamma: float,
    T: float,
    sigma_noise: float,
    rng: np.random.Generator,
    dT_mode: Literal["exact", "noisy_ratio"],
) -> tuple[np.ndarray, np.ndarray]:
    """One noisy surface and FD local variance; returns (σ²_analytic, σ²_FD)."""
    w_true, dT_w_true, _, _ = quadratic_total_variance(y, alpha, beta, gamma, T)
    sigma2_a = analytic_local_variance_quadratic(y, alpha, beta, gamma, T)

    w_tilde = add_multiplicative_noise(w_true, sigma_noise, rng)
    dy = central_first_derivative_uniform(w_tilde, h)
    dyy = second_derivative_uniform(w_tilde, h)

    if dT_mode == "exact":
        dT = dT_w_true
    elif dT_mode == "noisy_ratio":
        dT = w_tilde / T
    else:
        raise ValueError(dT_mode)

    sigma2_fd = local_variance_from_derivatives(y, w_tilde, dy, dyy, dT)
    return sigma2_a, sigma2_fd


def rmse_curves_averaged(
    y: np.ndarray,
    h: float,
    alpha: float,
    beta: float,
    gamma: float,
    T: float,
    sigma_grid: np.ndarray,
    rng: np.random.Generator,
    dT_mode: Literal["exact", "noisy_ratio"],
    interior: slice,
    trials_per_sigma: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    For each σ in `sigma_grid`, average RMSE (relative and absolute) over
    `trials_per_sigma` independent noise draws.
    """
    rel: list[float] = []
    abs_: list[float] = []
    trials_per_sigma = max(1, trials_per_sigma)

    for sig in sigma_grid:
        tr: list[float] = []
        ta: list[float] = []
        for _ in range(trials_per_sigma):
            sa, sf = local_variance_one_draw(
                y, h, alpha, beta, gamma, T, float(sig), rng, dT_mode
            )
            tr.append(rmse_relative(sa, sf, interior))
            ta.append(rmse_absolute(sa, sf, interior))
        rel.append(float(np.nanmean(tr)))
        abs_.append(float(np.nanmean(ta)))

    return np.asarray(rel, dtype=float), np.asarray(abs_, dtype=float)


def plot_rmse_vs_noise(
    sigma_grid: np.ndarray,
    rmse_rel: np.ndarray,
    rmse_abs: np.ndarray,
    *,
    h: float,
    T: float,
    dT_mode: str,
    trials_per_sigma: int,
) -> mpl.figure.Figure:
    """
    Log–log plot: RMSE (relative and absolute in σ²) vs σ_noise, reference y = σ.
    """
    fig, ax = plt.subplots(figsize=(5.8, 3.8), constrained_layout=True)

    x = np.asarray(sigma_grid, dtype=float)
    pos = x > 0
    n = len(x)
    ms = 3.5 if n > 50 else 4.5

    ax.loglog(
        x[pos],
        rmse_rel[pos],
        "o-",
        ms=ms,
        lw=1.25,
        label=r"RMSE of relative error $(\sigma^2_{\mathrm{FD}}-\sigma^2_{\mathrm{nat}})/|\sigma^2_{\mathrm{nat}}|$",
        zorder=3,
    )
    ax.loglog(
        x[pos],
        rmse_abs[pos],
        "s--",
        ms=ms - 1,
        lw=1.0,
        alpha=0.9,
        label=r"RMSE of $\sigma^2$ error $|\sigma^2_{\mathrm{FD}}-\sigma^2_{\mathrm{nat}}|$",
        zorder=2,
    )

    s_lo, s_hi = float(x[pos].min()), float(x[pos].max())
    ax.loglog([s_lo, s_hi], [s_lo, s_hi], ":", color="0.4", lw=2.0, zorder=1, label=r"reference slope 1: $y=\sigma_{\mathrm{noise}}$")

    ax.set_xlabel(r"$\sigma_{\mathrm{noise}}$ (multiplicative noise on $\tilde{w}$)")
    ax.set_ylabel("RMSE (interior $y$)")
    subtitle = f"$T={T}$, $h={h:.4f}$, $\\partial_T w$: {dT_mode}"
    if trials_per_sigma > 1:
        subtitle += f", mean over {trials_per_sigma} draws per $\\sigma$"
    ax.set_title("FD local variance: RMSE vs noise\n" + subtitle, fontsize=10)
    ax.grid(True, which="both", alpha=0.35)
    ax.legend(loc="best", fontsize=8, framealpha=0.95)

    return fig


def configure_matplotlib_style() -> None:
    """Conservative defaults suitable for print."""
    mpl.rcParams.update(
        {
            "figure.dpi": 120,
            "savefig.dpi": 300,
            "font.size": 10,
            "axes.labelsize": 10,
            "axes.titlesize": 10,
            "legend.fontsize": 8,
            "axes.grid": True,
        }
    )


def main() -> None:
    configure_matplotlib_style()

    parser = argparse.ArgumentParser(
        description="RMSE of finite-difference local variance vs multiplicative noise (single figure).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed.")
    parser.add_argument(
        "--out",
        type=str,
        default="lv_rmse.png",
        help="Output image path.",
    )
    parser.add_argument(
        "--dT-mode",
        choices=("exact", "noisy_ratio"),
        default="exact",
        help="Treatment of ∂_T w when w is replaced by noisy w̃ on the grid.",
    )
    parser.add_argument("--rmse-points", type=int, default=35, help="Number of σ_noise values (log-uniform).")
    parser.add_argument("--rmse-sigma-min", type=float, default=1e-5, help="Smallest σ_noise.")
    parser.add_argument("--rmse-sigma-max", type=float, default=5e-4, help="Largest σ_noise.")
    parser.add_argument(
        "--rmse-trials",
        type=int,
        default=50,
        help="Independent noisy surfaces per σ_noise; RMSE is averaged.",
    )
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    y = np.linspace(Y_MIN, Y_MAX, N_GRID)
    h = float(y[1] - y[0])
    interior = slice(1, -1)

    sigma_grid = log_uniform_sigma_grid(args.rmse_points, args.rmse_sigma_min, args.rmse_sigma_max)
    rmse_rel, rmse_abs = rmse_curves_averaged(
        y,
        h,
        ALPHA,
        BETA,
        GAMMA,
        T_MATURITY,
        sigma_grid,
        rng,
        args.dT_mode,
        interior,
        args.rmse_trials,
    )

    fig = plot_rmse_vs_noise(
        sigma_grid,
        rmse_rel,
        rmse_abs,
        h=h,
        T=T_MATURITY,
        dT_mode=args.dT_mode,
        trials_per_sigma=args.rmse_trials,
    )

    ensure_parent_dir(args.out)
    fig.savefig(args.out, bbox_inches="tight")
    print(f"Wrote {args.out}")
    plt.close(fig)


if __name__ == "__main__":
    main()
