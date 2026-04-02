import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from option_pricing.src.data.ingestion.db_connect import db_engine
from option_pricing.src.ImpliedVolatility.compute_vls import implied_vol


def _normalize_quote_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns and "quote_timestamp" in df.columns:
        return df.rename(columns={"quote_timestamp": "timestamp"})
    return df


def _normalize_price_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns and "price_timestamp" in df.columns:
        return df.rename(columns={"price_timestamp": "timestamp"})
    return df


def load_data():
    engine = db_engine()
    underlyings = pd.read_sql("SELECT * FROM underlyings;", engine)
    underlying_prices = _normalize_price_timestamp(
        pd.read_sql("SELECT * FROM underlying_prices;", engine)
    )
    option_quotes = _normalize_quote_timestamp(pd.read_sql("SELECT * FROM option_quotes;", engine))
    option_contracts = pd.read_sql("SELECT * FROM option_contracts;", engine)
    return underlyings, underlying_prices, option_quotes, option_contracts


def clean_data(data: pd.DataFrame):
    data.dropna(inplace=True)
    data = data[data["volume"] > 0]
    data = data[data["open_interest"] > 10]
    data["spread"] = data["ask"] - data["bid"]
    #data = data[data["spread"] / data["mid"] < 1]
    return data


def merge_quotes_contracts(option_quotes: pd.DataFrame, option_contracts: pd.DataFrame):
    if "timestamp" not in option_quotes.columns:
        raise KeyError("option_quotes needs a quote time column ('timestamp' or 'quote_timestamp')")

    option_quotes = option_quotes.groupby(["contract_id", "timestamp"], as_index=False).agg(
        {
            "bid": "mean",
            "ask": "mean",
            "mid": "mean",
            "last_price": "mean",
            "implied_vol": "mean",
            "volume": "sum",
            "open_interest": "sum",
        }
    )
    option_quotes = option_quotes.merge(
        option_contracts, left_on="contract_id", right_on="id", how="left"
    )
    option_quotes["timestamp"] = pd.to_datetime(option_quotes["timestamp"])
    option_quotes["expiration_date"] = pd.to_datetime(option_quotes["expiration_date"])
    option_quotes["T"] = (
        option_quotes["expiration_date"] - option_quotes["timestamp"]
    ).dt.total_seconds() / (365 * 24 * 3600)
    return option_quotes


def compute_iv(option_quotes_contracts, underlying_prices):
    df = option_quotes_contracts.copy()
    up = _normalize_price_timestamp(underlying_prices.copy())

    up["timestamp"] = pd.to_datetime(up["timestamp"])
    up = up.sort_values("timestamp").drop_duplicates(
        ["underlying_id", "timestamp"], keep="last"
    )

    mask = df["T"] > 0
    if not mask.any():
        df["iv"] = np.nan
        return df

    sub = df.loc[mask].copy()
    sub["_idx"] = sub.index

    merged = sub.merge(
        up[["underlying_id", "timestamp", "price"]],
        on=["underlying_id", "timestamp"],
        how="left",
        validate="many_to_one",
    )

    # assign back using explicit index
    df["spot"] = np.nan
    df.loc[merged["_idx"], "spot"] = merged["price"].to_numpy()

    price = merged["mid"].to_numpy(dtype=np.float64)
    S = merged["price"].to_numpy(dtype=np.float64)
    K = merged["strike"].to_numpy(dtype=np.float64)
    T = merged["T"].to_numpy(dtype=np.float64)
    call = (merged["option_type"] == "call").to_numpy()


    df["iv"] = np.nan
    df.loc[sub.index, "iv"] = implied_vol(price, S, K, T, 0.05, call)
    return df

def fit_ivsimle(option_quotes_contracts):
    from scipy.interpolate import UnivariateSpline

    sort = option_quotes_contracts.sort_values("log_moneyness").dropna()
    x = sort["log_moneyness"]
    y = sort["iv"]
    y_yahoo = sort["implied_vol"]
    print(f"fit_ivsimle: fitting splines on {len(sort)} quotes (log-moneyness range [{x.min():.4f}, {x.max():.4f}]).")
    f = UnivariateSpline(x, y, s=None)
    f_yahoo = UnivariateSpline(x, y_yahoo, s=None)
    x_lin = np.linspace(x.min(), x.max(), 200)

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(x_lin, f(x_lin), lw=2.0, label="Spline on inverted IV (qengine + Brent)")
    ax.plot(x_lin, f_yahoo(x_lin), lw=2.0, ls="--", label="Spline on Yahoo-reported IV")
    ax.set_xlabel(r"Log-moneyness $\log(K/F)$")
    ax.set_ylabel("Implied volatility")
    ax.set_title(
        "Nonparametric smile comparison: inverted IV vs provider IV\n"
        "(same strike/expiry sample as pipeline, filtered |log moneyness| < 0.2 in prior step)"
    )
    ax.grid(alpha=0.3)
    ax.legend(loc="best", framealpha=0.95)
    fig.tight_layout()
    fig.savefig("iv_smile_fit.pdf", bbox_inches="tight")
    plt.close(fig)

    return f

def calibrate_svi_surface(option_quotes_contracts: pd.DataFrame, r: float = 0.05, **kwargs):
    """
    Fit SVI per expiry on ``iv`` from :func:`compute_iv` and plot diagnostics.

    See :func:`option_pricing.src.ImpliedVolatility.svi.calibrate_from_option_frame`.
    """
    from option_pricing.src.ImpliedVolatility.svi import calibrate_from_option_frame

    return calibrate_from_option_frame(option_quotes_contracts, r=r, **kwargs)

def clean_before_svi(option_quotes_contracts: pd.DataFrame):
    option_quotes_contracts = option_quotes_contracts[option_quotes_contracts["T"] > 0.05]
    return option_quotes_contracts


def plot_smoothed_svi_surface(prep: pd.DataFrame, params: pd.DataFrame, r: float = 0.05):
    """
    Plot independent slice fits after maturity smoothing.

    Outputs:
    - svi_smoothed_surface.pdf
    - svi_calendar_violation_heatmap.pdf
    """
    from option_pricing.src.ImpliedVolatility.svi import (
        calendar_violation_matrix,
        smooth_svi_parameters,
    )

    # Build smoothed maturity-parameter curves from calibrated slice parameters
    curves = smooth_svi_parameters(
        params,
        T_col="T_mean",
        smooth_factor_a=1e-4,
        smooth_factor_m=1e-4,
        smooth_factor_others=0.0,
        min_T=0.05,
        weight_col="n_points",
    )

    # Overlay market points and smoothed model by maturity
    plot_df = prep.copy()
    if "T" not in plot_df.columns or "total_var" not in plot_df.columns:
        raise KeyError("prep must include columns 'T' and 'total_var'")

    T_grid = np.sort(params.loc[params["success"], "T_mean"].to_numpy(dtype=np.float64))
    if T_grid.size < 2:
        return
    k_grid = np.linspace(
        float(plot_df["log_moneyness"].quantile(0.02)),
        float(plot_df["log_moneyness"].quantile(0.98)),
        180,
    )

    fig, ax = plt.subplots(figsize=(11, 7))
    cmap = plt.colormaps["viridis"]
    nT = max(len(T_grid), 1)
    for i, Ti in enumerate(T_grid):
        color = cmap(i / max(nT - 1, 1)) if nT > 1 else cmap(0.5)
        near = np.isclose(plot_df["T"].to_numpy(dtype=np.float64), Ti, rtol=0.03, atol=2e-3)
        sub = plot_df.loc[near]
        if sub.empty:
            continue
        iv_mkt = np.sqrt(
            np.maximum(sub["total_var"].to_numpy(dtype=np.float64), 0.0)
            / np.maximum(Ti, 1e-12)
        )
        ax.scatter(
            sub["log_moneyness"].to_numpy(dtype=np.float64),
            iv_mkt,
            s=12,
            alpha=0.4,
            color=color,
            edgecolors="none",
        )
        w_model = curves.total_var(k_grid, np.array([Ti], dtype=np.float64))[0]
        iv_model = np.sqrt(np.maximum(w_model, 0.0) / np.maximum(Ti, 1e-12))
        ax.plot(k_grid, iv_model, color=color, lw=2.2, label=f"Smoothed SVI slice T={Ti:.3f}")

    ax.set_xlabel(r"Log-moneyness $\log(K/F)$", fontsize=11)
    ax.set_ylabel("Implied volatility", fontsize=11)
    ax.set_title(
        "SVI surface after maturity smoothing\n"
        "Scatter: observed total variance converted to IV; lines: smoothed-parameter SVI slices",
        fontsize=12,
    )
    ax.grid(alpha=0.3)
    ax.legend(
        fontsize=8,
        ncol=2,
        loc="upper right",
        framealpha=0.95,
        title="Smoothed SVI slices (lines); scatter = market IV",
    )
    fig.tight_layout()
    fig.savefig("svi_smoothed_surface.pdf", bbox_inches="tight")
    plt.close(fig)

    cal_diff = calendar_violation_matrix(curves, T_grid, k_grid)
    fig2, ax2 = plt.subplots(figsize=(11, 4.5))
    im = ax2.imshow(
        cal_diff,
        aspect="auto",
        origin="lower",
        cmap="coolwarm",
        vmin=-0.02,
        vmax=0.02,
        extent=[k_grid.min(), k_grid.max(), 0, cal_diff.shape[0]],
    )
    cbar = fig2.colorbar(im, ax=ax2)
    cbar.set_label(r"$\Delta w$ = $w(T_{j+1},k) - w(T_j,k)$  (total variance)", fontsize=10)
    ax2.set_xlabel(r"Log-moneyness $\log(K/F)$", fontsize=11)
    ax2.set_ylabel(r"Maturity step index $j$ (pair $T_j \to T_{j+1}$)", fontsize=11)
    ax2.set_title(
        "Calendar spread diagnostic on smoothed surface\n"
        "(negative values indicate potential calendar arbitrage in $w$)",
        fontsize=12,
    )
    fig2.tight_layout()
    fig2.savefig("svi_calendar_violation_heatmap.pdf", bbox_inches="tight")
    plt.close(fig2)


def _fit_slice_with_svi_py_model(
    model: object,
    model_name: str,
    k: np.ndarray,
    w: np.ndarray,
    T: float,
    *,
    theta_ref: float,
    prev_params: dict | None,
    k_eval: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Fit one slice with a specific pysvi model and evaluate total variance on k_eval."""
    T = float(T)
    k = np.asarray(k, dtype=np.float64)
    w = np.asarray(w, dtype=np.float64)
    k_eval = np.asarray(k_eval, dtype=np.float64)

    # ATM total variance proxy for models requiring theta
    theta = float(np.interp(0.0, np.sort(k), w[np.argsort(k)]))
    theta = max(theta, 1e-8)

    kwargs: dict = {}
    if model_name == "ssvi":
        kwargs["theta"] = theta
    elif model_name == "essvi":
        kwargs["theta"] = theta
        kwargs["theta_ref"] = max(float(theta_ref), 1e-8)
    elif model_name in {"jumpwings", "jw"}:
        kwargs["T"] = max(T, 1e-8)

    # Option B: calendar penalty uses pysvi internal 200-point grid per current slice.
    # Build w_prev on that exact grid to avoid shape mismatch.
    if prev_params is not None:
        k_cal = np.linspace(float(k.min()) - 0.5, float(k.max()) + 0.5, 200)
        kwargs["w_prev"] = np.asarray(model.total_variance(k_cal, prev_params), dtype=np.float64)

    params = model.calibrate(k, w, **kwargs)
    if params is None:
        raise RuntimeError(f"pysvi {model_name} calibration failed")
    w_eval = model.total_variance(k_eval, params)
    return np.asarray(w_eval, dtype=np.float64), params


def compare_vs_svi_py(prep: pd.DataFrame, params: pd.DataFrame):
    """
    Compare in-house SVI fit against pysvi models with explicit no-arbitrage flags.

    Outputs:
    - svi_vs_pysvi_<model>_comparison.pdf for model in {svi, ssvi, essvi, jumpwings}
    - svi_vs_pysvi_metrics.csv
    """
    from option_pricing.src.ImpliedVolatility.svi import SVIParams
    from pysvi import ArbitrageFreedom, get_model

    ok_params = params[params["success"]].copy()
    if ok_params.empty:
        print("compare_vs_svi_py: no successful in-house slices; skipping.")
        return

    k_min = float(prep["log_moneyness"].quantile(0.02))
    k_max = float(prep["log_moneyness"].quantile(0.98))
    k_grid = np.linspace(k_min, k_max, 180)

    models = ["svi", "ssvi", "essvi", "jumpwings"]
    rows: list[dict] = []

    # reference theta for eSSVI from in-house successful slices
    theta_ref = float(np.median(ok_params["T_mean"].to_numpy(dtype=np.float64) * 0 + 1.0))
    # Better theta_ref proxy from observed market ATM if available
    theta_vals = []
    for _, row in ok_params.iterrows():
        Ti = float(row["T_mean"])
        near = np.isclose(prep["T"].to_numpy(dtype=np.float64), Ti, rtol=0.03, atol=2e-3)
        sub = prep.loc[near].sort_values("log_moneyness")
        if len(sub) < 10:
            continue
        ks = sub["log_moneyness"].to_numpy(dtype=np.float64)
        ws = sub["total_var"].to_numpy(dtype=np.float64)
        theta_vals.append(float(np.interp(0.0, np.sort(ks), ws[np.argsort(ks)])))
    if theta_vals:
        theta_ref = float(np.median(theta_vals))

    sorted_rows = list(ok_params.sort_values("T_mean").iterrows())
    for model_name in models:
        flags = ArbitrageFreedom.NO_BUTTERFLY | ArbitrageFreedom.NO_CALENDAR
        model = get_model(model_name, flags)
        plt.figure(figsize=(11, 7))
        cmap = plt.colormaps["tab20"]
        prev_params = None
        n_used = 0
        for _, row in sorted_rows:
            Ti = float(row["T_mean"])
            near = np.isclose(prep["T"].to_numpy(dtype=np.float64), Ti, rtol=0.03, atol=2e-3)
            sub = prep.loc[near].sort_values("log_moneyness")
            if len(sub) < 10:
                continue
            k = sub["log_moneyness"].to_numpy(dtype=np.float64)
            w = sub["total_var"].to_numpy(dtype=np.float64)

            p_ours = SVIParams(
                float(row["a"]), float(row["b"]), float(row["rho"]), float(row["m"]), float(row["sigma"])
            )
            w_ours = p_ours.total_var(k_grid)
            rmse_ours = float(np.sqrt(np.mean((p_ours.total_var(k) - w) ** 2)))

            try:
                w_ext, ext_params = _fit_slice_with_svi_py_model(
                    model,
                    model_name,
                    k,
                    w,
                    Ti,
                    theta_ref=theta_ref,
                    prev_params=prev_params,
                    k_eval=k_grid,
                )
                rmse_ext = float(np.sqrt(np.mean((np.interp(k, k_grid, w_ext) - w) ** 2)))
                rows.append(
                    {
                        "model": model_name,
                        "T_mean": Ti,
                        "rmse_ours": rmse_ours,
                        "rmse_pysvi": rmse_ext,
                        "delta_rmse": rmse_ext - rmse_ours,
                        "ext_params": str(ext_params),
                    }
                )
                color = cmap(n_used % 20)
                n_used += 1
                plt.plot(k_grid, np.sqrt(np.maximum(w_ours, 0) / max(Ti, 1e-12)), color=color, lw=2, alpha=0.9)
                plt.plot(k_grid, np.sqrt(np.maximum(w_ext, 0) / max(Ti, 1e-12)), color=color, lw=1.5, ls="--", alpha=0.9)
                prev_params = ext_params
            except Exception as exc:
                print(f"compare_vs_svi_py[{model_name}]: skipping T={Ti:.4f}, reason: {exc}")
                continue

        if n_used == 0:
            plt.close()
            continue

        plt.xlabel(r"Log-moneyness $\log(K/F)$", fontsize=11)
        plt.ylabel("Implied volatility", fontsize=11)
        plt.title(
            f"Slice-wise implied vol: in-house SVI (solid) vs pysvi '{model_name}' (dashed)\n"
            "Each color is a different expiry; dashed uses no-arbitrage-constrained pysvi calibration.",
            fontsize=12,
        )
        plt.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"svi_vs_pysvi_{model_name}_comparison.pdf", bbox_inches="tight")
        plt.clf()

    out = pd.DataFrame(rows)
    if out.empty:
        print("compare_vs_svi_py: no slices compared (pysvi unavailable or incompatible).")
        return
    out = out.sort_values(["model", "T_mean"])
    out.to_csv("svi_vs_pysvi_metrics.csv", index=False)
    print(out.groupby("model")[["rmse_ours", "rmse_pysvi", "delta_rmse"]].mean())


def plot_ivsmile(option_quotes_contracts):
    option_quotes_contracts = option_quotes_contracts.sort_values("strike")
    option_quotes_contracts["log_moneyness"] = np.log(
        option_quotes_contracts["spot"] * np.exp(0.05 * option_quotes_contracts["T"])/option_quotes_contracts["strike"]
    )
    option_quotes_contracts = option_quotes_contracts[option_quotes_contracts["log_moneyness"].abs() < 0.2]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(
        option_quotes_contracts["strike"],
        option_quotes_contracts["iv"],
        ".",
        alpha=0.35,
        markersize=4,
        label="Inverted IV (Black–Scholes, r = 5%, mid price)",
    )
    ax.plot(
        option_quotes_contracts["strike"],
        option_quotes_contracts["implied_vol"],
        ".",
        alpha=0.35,
        markersize=4,
        label="Yahoo-reported implied volatility",
    )
    ax.set_xlabel("Strike price", fontsize=11)
    ax.set_ylabel("Implied volatility", fontsize=11)
    ax.set_title(
        "Volatility smile near the money\n"
        r"(filter: $\left|\log(K/F)\right| < 0.2$ on forward $F = S e^{rT}$)",
        fontsize=12,
    )
    ax.grid(alpha=0.3)
    ax.legend(loc="best", framealpha=0.95)
    fig.tight_layout()
    fig.savefig("iv_smile.pdf", bbox_inches="tight")
    plt.close(fig)
    return option_quotes_contracts





if __name__ == "__main__":
    underlyings, underlying_prices, option_quotes, option_contracts = load_data()
    option_quotes_contracts = merge_quotes_contracts(option_quotes, option_contracts)
    option_quotes_contracts = clean_data(option_quotes_contracts)
    option_quotes_contracts = compute_iv(option_quotes_contracts, underlying_prices)
    mask = option_quotes_contracts["iv"].notna()
    print(option_quotes_contracts)
    print(option_quotes_contracts.columns)
    #plt.plot(option_quotes_contracts["contract_id"][mask], option_quotes_contracts["implied_vol"][mask], label="i. iv")
    #plt.plot(option_quotes_contracts["contract_id"][mask],option_quotes_contracts["iv"][mask], label="comp. iv")
    #plt.legend()
    #plt.show()
    option_quotes_contracts = plot_ivsmile(option_quotes_contracts)
    fit_ivsimle(option_quotes_contracts)
    prep, svi_fit, params = calibrate_svi_surface(
        clean_before_svi(option_quotes_contracts),
        r=0.05,
        plot_backend="matplotlib",
        finplot_show=True,
        # optionally: plot_path=None to avoid matplotlib PDF output
    )
    print(svi_fit)
    plot_smoothed_svi_surface(prep, params, r=0.05)
    compare_vs_svi_py(prep, params)

