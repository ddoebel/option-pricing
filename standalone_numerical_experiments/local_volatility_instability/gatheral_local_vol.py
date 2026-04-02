"""
Gatheral local variance in total-variance / log-moneyness form (practitioner's guide).

sigma^2 = (d_T w) / ( 1 - (y/w) d_y w
            + (1/4)(-1/4 - 1/w + y^2/w^2) (d_y w)^2
            + (1/2) d_yy w )

where w = omega is total implied variance, y is log-moneyness (convention as in the note).
"""

from __future__ import annotations

import numpy as np


def local_variance_from_derivatives(
    y: np.ndarray,
    w: np.ndarray,
    dy_w: np.ndarray,
    dyy_w: np.ndarray,
    dT_w: np.ndarray,
    *,
    eps: float = 1e-14,
) -> np.ndarray:
    """Vectorized Gatheral formula. Invalid / near-singular points become nan."""
    y = np.asarray(y, dtype=float)
    w = np.asarray(w, dtype=float)
    dy_w = np.asarray(dy_w, dtype=float)
    dyy_w = np.asarray(dyy_w, dtype=float)
    dT_w = np.asarray(dT_w, dtype=float)

    out = np.full_like(y, np.nan, dtype=float)
    ok = np.isfinite(w) & (np.abs(w) > eps) & np.isfinite(dy_w) & np.isfinite(dyy_w) & np.isfinite(dT_w)

    denom = np.empty_like(w)
    denom[ok] = (
        1.0
        - (y[ok] / w[ok]) * dy_w[ok]
        + 0.25 * (-0.25 - 1.0 / w[ok] + (y[ok] ** 2) / (w[ok] ** 2)) * (dy_w[ok] ** 2)
        + 0.5 * dyy_w[ok]
    )

    ok2 = ok & (np.abs(denom) > eps)
    out[ok2] = dT_w[ok2] / denom[ok2]
    return out


def quadratic_total_variance(
    y: np.ndarray,
    alpha: float,
    beta: float,
    gamma: float,
    T: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    w(y,T) = T * (alpha + beta*y + gamma*y^2), with derivatives as in the note:

      d_T w = alpha + beta*y + gamma*y^2
      d_y w = T * (beta + 2*gamma*y)
      d_yy w = 2*gamma*T
    """
    y = np.asarray(y, dtype=float)
    f = alpha + beta * y + gamma * y ** 2
    w = T * f
    dT_w = f
    dy_w = T * (beta + 2.0 * gamma * y)
    dyy_w = np.full_like(y, 2.0 * gamma * T)
    return w, dT_w, dy_w, dyy_w


def analytic_local_variance_quadratic(
    y: np.ndarray,
    alpha: float,
    beta: float,
    gamma: float,
    T: float,
) -> np.ndarray:
    """Closed form from the note (equivalent to plugging derivatives into Gatheral)."""
    y = np.asarray(y, dtype=float)
    w, dT_w, dy_w, dyy_w = quadratic_total_variance(y, alpha, beta, gamma, T)
    return local_variance_from_derivatives(y, w, dy_w, dyy_w, dT_w)


def central_first_derivative_uniform(w: np.ndarray, h: float) -> np.ndarray:
    """Interior (w[i+1]-w[i-1])/(2h); endpoints nan."""
    w = np.asarray(w, dtype=float)
    out = np.full_like(w, np.nan)
    out[1:-1] = (w[2:] - w[:-2]) / (2.0 * h)
    return out


def second_derivative_uniform(w: np.ndarray, h: float) -> np.ndarray:
    """Interior second difference / h^2; endpoints nan."""
    w = np.asarray(w, dtype=float)
    out = np.full_like(w, np.nan)
    out[1:-1] = (w[2:] - 2.0 * w[1:-1] + w[:-2]) / (h ** 2)
    return out


def add_multiplicative_noise(
    w: np.ndarray,
    sigma_noise: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """tilde w(y_i) = w(y_i) * (1 + eps), eps ~ N(0, sigma_noise^2)."""
    w = np.asarray(w, dtype=float)
    eps = rng.normal(0.0, sigma_noise, size=w.shape)
    return w * (1.0 + eps)
