"""Grid search optimization — daily sentiment vs configurable return horizon."""

import itertools
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from scipy import stats

import config
import index_builder
import news_fetcher
import price_fetcher
import sentiment_analyzer


def compute_correlation(index_series: pd.Series, return_series: pd.Series,
                        lag: int = 0) -> dict:
    """Pearson and Spearman correlation. lag>0 = sentiment leads price by N days."""
    idx = index_series.shift(lag) if lag > 0 else index_series
    combined = pd.DataFrame({"index": idx, "returns": return_series}).dropna()

    if len(combined) < 10:
        return {"pearson_r": 0.0, "pearson_p": 1.0,
                "spearman_r": 0.0, "spearman_p": 1.0, "n_obs": len(combined)}

    pr, pp = stats.pearsonr(combined["index"], combined["returns"])
    sr, sp = stats.spearmanr(combined["index"], combined["returns"])

    return {
        "pearson_r": round(float(pr), 4),
        "pearson_p": round(float(pp), 4),
        "spearman_r": round(float(sr), 4),
        "spearman_p": round(float(sp), 4),
        "n_obs": len(combined),
    }


def rolling_correlation(index_series: pd.Series, return_series: pd.Series,
                        window: int = 20) -> pd.Series:
    combined = pd.DataFrame({"index": index_series, "returns": return_series}).dropna()
    if len(combined) < window:
        return pd.Series(dtype=float)
    return combined["index"].rolling(window).corr(combined["returns"])


def _build_param_combos() -> list[dict]:
    grid = config.PARAM_GRID
    keys = list(grid.keys())
    values = list(grid.values())
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def _flatten_weekly_articles(weekly_articles: dict[str, list[dict]]) -> list[dict]:
    all_articles = []
    for articles in weekly_articles.values():
        all_articles.extend(articles)
    return all_articles


def _apply_inversion(articles: list[dict], asset_key: str) -> list[dict]:
    """Invert sentiment scores for assets with invert_sentiment=True (e.g. bonds)."""
    if config.ASSETS.get(asset_key, {}).get("invert_sentiment", False):
        for a in articles:
            if "score" in a:
                a["score"] = -a["score"]
                a["positive"], a["negative"] = a.get("negative", 0), a.get("positive", 0)
    return articles


def _score_all_articles(weekly_articles: dict[str, list[dict]]) -> dict[str, list[dict]]:
    sentiment_analyzer.load_model()
    for week_key, articles in weekly_articles.items():
        if articles and "score" not in articles[0]:
            sentiment_analyzer.analyze_articles(articles)
    return weekly_articles


def grid_search(
    asset_key: str,
    all_articles: list[dict],
    prices_df: pd.DataFrame,
    return_col: str = "Return_5d",
) -> pd.DataFrame:
    """Grid search: daily sentiment vs given return horizon."""
    if prices_df.empty or not all_articles or return_col not in prices_df.columns:
        return pd.DataFrame()

    combos = _build_param_combos()
    results = []
    total = len(combos)

    start_date = prices_df.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
    end_date = prices_df.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)

    for i, params in enumerate(combos):
        if (i + 1) % 100 == 0:
            print(f"  [{asset_key}] {i+1}/{total}...")

        daily_series = index_builder.build_daily_index_series(
            all_articles, params, start_date, end_date
        )

        idx_s = pd.Series(daily_series)
        idx_s.index = pd.to_datetime(idx_s.index)

        ret_series = prices_df[return_col]
        lag = params.get("lag_days", 0)
        corr = compute_correlation(idx_s, ret_series, lag=lag)

        roll = rolling_correlation(idx_s, ret_series, window=20).dropna()
        corr["rolling_mean"] = round(float(roll.mean()), 4) if len(roll) > 0 else 0.0

        result = {**params, **corr}
        results.append(result)

    df = pd.DataFrame(results)
    df["abs_spearman"] = df["spearman_r"].abs()
    df = df.sort_values("rolling_mean", ascending=False).reset_index(drop=True)
    return df


def optimize_asset(
    asset_key: str,
    all_articles: list[dict],
    prices_df: pd.DataFrame,
    return_col: str = "Return_5d",
    split_ratio: float = 0.7,
) -> dict:
    """Grid search with in-sample/out-of-sample split for a given return horizon."""
    if prices_df.empty:
        return {"error": f"No price data for {asset_key}"}

    n = len(prices_df)
    split_idx = int(n * split_ratio)

    is_prices = prices_df.iloc[:split_idx]
    is_results = grid_search(asset_key, all_articles, is_prices, return_col=return_col)

    if is_results.empty:
        return {"error": f"No results for {asset_key}"}

    best_row = is_results.iloc[0]
    best_params = {}
    for key in config.PARAM_GRID.keys():
        val = best_row[key]
        if hasattr(val, 'item'):
            val = val.item()
        best_params[key] = val

    # Out-of-sample
    oos_prices = prices_df.iloc[split_idx:]
    oos_corr = {"pearson_r": None, "spearman_r": None, "n_obs": 0}
    if len(oos_prices) > 10:
        oos_start = oos_prices.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
        oos_end = oos_prices.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
        oos_series = index_builder.build_daily_index_series(
            all_articles, best_params, oos_start, oos_end
        )
        oos_idx = pd.Series(oos_series)
        oos_idx.index = pd.to_datetime(oos_idx.index)
        oos_corr = compute_correlation(oos_idx, oos_prices[return_col],
                                       lag=best_params.get("lag_days", 0))

    # Default baseline
    default_start = prices_df.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
    default_end = prices_df.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    default_series = index_builder.build_daily_index_series(
        all_articles, config.DEFAULT_PARAMS, default_start, default_end
    )
    default_idx = pd.Series(default_series)
    default_idx.index = pd.to_datetime(default_idx.index)
    default_corr = compute_correlation(default_idx, prices_df[return_col],
                                       lag=config.DEFAULT_PARAMS.get("lag_days", 0))

    return {
        "asset": asset_key,
        "return_col": return_col,
        "best_params": best_params,
        "in_sample": {
            "pearson_r": float(best_row["pearson_r"]),
            "spearman_r": float(best_row["spearman_r"]),
            "rolling_mean": float(best_row.get("rolling_mean", 0)),
            "n_obs": int(best_row["n_obs"]),
        },
        "out_of_sample": oos_corr,
        "default_correlation": {
            "pearson_r": default_corr["pearson_r"],
            "spearman_r": default_corr["spearman_r"],
        },
        "top_10": is_results.head(10).to_dict("records"),
        "total_combos_tested": len(is_results),
    }


def optimize_all_dual() -> dict:
    """Optimize each asset for both daily (1d) and weekly (5d) return horizons."""
    print("Loading historical data for dual optimization...")

    all_results = {}
    for asset_key in config.ASSETS:
        print(f"\n{'='*60}")
        print(f"Optimizing {asset_key} (daily + weekly)...")

        weekly_articles = news_fetcher.fetch_historical_news(asset_key, weeks=config.HISTORY_WEEKS)
        total_articles = sum(len(v) for v in weekly_articles.values())
        print(f"  {len(weekly_articles)} weeks, {total_articles} articles")

        weekly_articles = _score_all_articles(weekly_articles)
        all_articles = _flatten_weekly_articles(weekly_articles)
        all_articles = _apply_inversion(all_articles, asset_key)

        prices = price_fetcher.fetch_prices(config.ASSETS[asset_key]["ticker"])
        print(f"  {len(prices)} daily price obs")

        # Optimize for both horizons
        print(f"  [1d] Optimizing vs Return_1d...")
        result_1d = optimize_asset(asset_key, all_articles, prices, return_col="Return_1d")

        print(f"  [5d] Optimizing vs Return_5d...")
        result_5d = optimize_asset(asset_key, all_articles, prices, return_col="Return_5d")

        # Pick the best horizon by rolling_mean
        rm_1d = result_1d.get("in_sample", {}).get("rolling_mean", 0) if "error" not in result_1d else 0
        rm_5d = result_5d.get("in_sample", {}).get("rolling_mean", 0) if "error" not in result_5d else 0

        best_horizon = "1d" if rm_1d > rm_5d else "5d"
        best_result = result_1d if best_horizon == "1d" else result_5d

        all_results[asset_key] = {
            "daily": result_1d,
            "weekly": result_5d,
            "best_horizon": best_horizon,
            "best_params": best_result.get("best_params", config.DEFAULT_PARAMS),
            "best_return_col": f"Return_{best_horizon}",
            "rolling_mean_1d": rm_1d,
            "rolling_mean_5d": rm_5d,
        }

        print(f"  1d roll_mean={rm_1d:.4f}, 5d roll_mean={rm_5d:.4f} → BEST: {best_horizon}")

    save_optimized_params_dual(all_results)
    return all_results


def optimize_all() -> dict:
    """Single-horizon optimization (backward compat). Uses Return_5d."""
    return _optimize_all_single("Return_5d")


def _optimize_all_single(return_col: str) -> dict:
    print(f"Loading historical data (return_col={return_col})...")
    all_results = {}
    for asset_key in config.ASSETS:
        print(f"\n{'='*60}")
        print(f"Optimizing {asset_key}...")
        weekly_articles = news_fetcher.fetch_historical_news(asset_key, weeks=config.HISTORY_WEEKS)
        weekly_articles = _score_all_articles(weekly_articles)
        all_articles = _flatten_weekly_articles(weekly_articles)
        all_articles = _apply_inversion(all_articles, asset_key)
        prices = price_fetcher.fetch_prices(config.ASSETS[asset_key]["ticker"])
        result = optimize_asset(asset_key, all_articles, prices, return_col=return_col)
        all_results[asset_key] = result
        if "error" not in result:
            print(f"  Best: {result['best_params']}")
            print(f"  IS roll_mean: {result['in_sample'].get('rolling_mean', 0):.4f}")
    save_optimized_params(all_results)
    return all_results


# ── Save / Load ────────────────────────────────────────────────────────────────

def save_optimized_params_dual(results: dict):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    params_to_save = {}
    for asset_key, result in results.items():
        params_to_save[asset_key] = {
            "params": result["best_params"],
            "return_col": result["best_return_col"],
            "best_horizon": result["best_horizon"],
            "rolling_mean_1d": result["rolling_mean_1d"],
            "rolling_mean_5d": result["rolling_mean_5d"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _convert(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_,)): return bool(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(config.OPTIMIZED_PARAMS, "w") as f:
        json.dump(params_to_save, f, indent=2, default=_convert)
    print(f"\nDual optimized params saved to {config.OPTIMIZED_PARAMS}")


def save_optimized_params(results: dict):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    params_to_save = {}
    for asset_key, result in results.items():
        if "error" not in result:
            params_to_save[asset_key] = {
                "params": result["best_params"],
                "return_col": result.get("return_col", "Return_5d"),
                "in_sample_spearman": result["in_sample"]["spearman_r"],
                "rolling_mean": result["in_sample"].get("rolling_mean", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    def _convert(obj):
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, (np.bool_,)): return bool(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    with open(config.OPTIMIZED_PARAMS, "w") as f:
        json.dump(params_to_save, f, indent=2, default=_convert)
    print(f"\nOptimized params saved to {config.OPTIMIZED_PARAMS}")


def load_optimized_params() -> dict:
    """Load optimized params. Returns {asset: params_dict}."""
    if os.path.exists(config.OPTIMIZED_PARAMS):
        with open(config.OPTIMIZED_PARAMS, "r") as f:
            data = json.load(f)
        return {k: v["params"] for k, v in data.items()}
    return {}


def load_optimized_full() -> dict:
    """Load full optimized data including return_col and rolling means."""
    if os.path.exists(config.OPTIMIZED_PARAMS):
        with open(config.OPTIMIZED_PARAMS, "r") as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    results = optimize_all_dual()
    print("\n" + "="*70)
    print("DUAL OPTIMIZATION COMPLETE")
    print("="*70)
    print(f"{'Asset':<10} {'1d Roll':>8} {'5d Roll':>8} {'Best':>5} {'Params'}")
    print("-"*70)
    for asset, res in results.items():
        rm1 = res["rolling_mean_1d"]
        rm5 = res["rolling_mean_5d"]
        best = res["best_horizon"]
        params = res["best_params"]
        agg = params.get("aggregation", "?")
        hl = params.get("time_decay_halflife", "?")
        print(f"{asset:<10} {rm1:>8.4f} {rm5:>8.4f} {best:>5} hl={hl} {agg}")
