"""Fiyat — panelin ve kosunun okudugu kapanislar (kaynak: fiyat.py).

Kapanislar fiyat.py'den gelir: dovizde saatlik bardan New York 17:00, obur
enstrumanlarda olculmus kapanis anli gunluk bar. Yahoo'nun gunluk doviz barinin
"Close"u gunun BASIDIR ve bir gun kayiktir (bkz. fiyat.py baslik notu).
SOZLESME KORUNUR: indirme duserse bos tablo doner ve sebep yazilir — canli
kosu fiyat yuzunden durmaz (fiyat burada yalniz bilgidir).
Return_* sutunlari GERIYE donuktur (D'de BITEN getiri); ileri getiri fiyat.py'de.
"""

import pandas as pd

import config
import fiyat


def fetch_prices(ticker: str, period_days: int = None) -> pd.DataFrame:
    """Fetch historical daily price data with multi-day returns."""
    if period_days is None:
        period_days = config.HISTORY_DAYS
    try:
        seri = fiyat.kapanislar(ticker, gun=period_days + 10).seri
    except Exception as exc:  # noqa: BLE001 — sozlesme: bos tablo, sebep adiyla
        print(f"[price] {ticker}: kapanış alınamadı ({type(exc).__name__}: {exc})")
        return pd.DataFrame()
    if seri.empty:
        return pd.DataFrame()

    df = seri.to_frame("Close")

    for days in [1, 2, 3, 5]:
        df[f"Return_{days}d"] = df["Close"].pct_change(days)

    df.dropna(subset=["Return_1d"], inplace=True)
    return df


def fetch_weekly_prices(ticker: str, weeks: int = None) -> pd.DataFrame:
    """Fetch 1yr daily data, resample to Friday close, compute weekly returns."""
    if weeks is None:
        weeks = config.HISTORY_WEEKS

    df = fetch_prices(ticker, period_days=366)
    if df.empty:
        return pd.DataFrame()

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
