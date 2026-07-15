"""Price data fetcher using yfinance (free, no API key)."""

import pandas as pd
import yfinance as yf

import config


def fetch_prices(ticker: str, period_days: int = None) -> pd.DataFrame:
    """Fetch historical daily price data with multi-day returns."""
    if period_days is None:
        period_days = config.HISTORY_DAYS

    if period_days <= 7:
        period = "7d"
    elif period_days <= 30:
        period = "1mo"
    elif period_days <= 90:
        period = "3mo"
    elif period_days <= 180:
        period = "6mo"
    else:
        period = "1y"

    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Close"]].copy()
    df = df.ffill()

    for days in [1, 2, 3, 5]:
        df[f"Return_{days}d"] = df["Close"].pct_change(days)

    df.dropna(subset=["Return_1d"], inplace=True)
    return df


def fetch_weekly_prices(ticker: str, weeks: int = None) -> pd.DataFrame:
    """Fetch 1yr daily data, resample to Friday close, compute weekly returns."""
    if weeks is None:
        weeks = config.HISTORY_WEEKS

    df = yf.download(ticker, period="1y", auto_adjust=True, progress=False)

    if df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Close"]].copy().ffill()

    # Resample to weekly (Friday close)
    weekly = df["Close"].resample("W-FRI").last().to_frame()
    weekly["Return_weekly"] = weekly["Close"].pct_change()
    weekly.dropna(subset=["Return_weekly"], inplace=True)

    return weekly


def fetch_all_prices() -> dict[str, pd.DataFrame]:
    """Fetch daily prices for all assets."""
    prices = {}
    for asset_key, asset_cfg in config.ASSETS.items():
        df = fetch_prices(asset_cfg["ticker"])
        prices[asset_key] = df
        if not df.empty:
            latest = df["Close"].iloc[-1]
            ret_1d = df["Return_1d"].iloc[-1] * 100
            print(f"[price] {asset_key}: {latest:.4f} ({ret_1d:+.2f}% 1d)")
    return prices


def fetch_all_weekly_prices() -> dict[str, pd.DataFrame]:
    """Fetch weekly-resampled prices for all assets."""
    prices = {}
    for asset_key, asset_cfg in config.ASSETS.items():
        df = fetch_weekly_prices(asset_cfg["ticker"])
        prices[asset_key] = df
        if not df.empty:
            latest = df["Close"].iloc[-1]
            ret_w = df["Return_weekly"].iloc[-1] * 100
            print(f"[weekly] {asset_key}: {latest:.4f} ({ret_w:+.2f}% weekly)")
    return prices


def get_latest_price(asset_key: str) -> dict:
    """Get latest price and return for a single asset."""
    ticker = config.ASSETS[asset_key]["ticker"]
    df = fetch_prices(ticker, period_days=7)
    if df.empty:
        return {"price": None, "return_1d": None}
    return {
        "price": float(df["Close"].iloc[-1]),
        "return_1d": float(df["Return_1d"].iloc[-1]),
    }


if __name__ == "__main__":
    print("=== Daily Prices ===")
    fetch_all_prices()
    print("\n=== Weekly Prices ===")
    wp = fetch_all_weekly_prices()
    for k, df in wp.items():
        print(f"  {k}: {len(df)} weeks, {df.index[0].date()} to {df.index[-1].date()}")
