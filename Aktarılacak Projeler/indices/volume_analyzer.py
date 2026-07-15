"""Volume spike detection — news article count as a supplementary signal."""

from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd

import config


def compute_daily_volume(
    scored_articles: list[dict],
    start_date: datetime,
    end_date: datetime,
) -> dict[str, int]:
    """Count articles per day within the date range."""
    counts = {}
    current = start_date
    while current <= end_date:
        day_key = current.strftime("%Y-%m-%d")
        day_start = current.replace(hour=0, minute=0, second=0)
        day_end = current.replace(hour=23, minute=59, second=59)
        count = 0
        for a in scored_articles:
            try:
                pub = datetime.fromisoformat(a["published"])
                if pub.tzinfo is None:
                    pub = pub.replace(tzinfo=timezone.utc)
                if day_start <= pub <= day_end:
                    count += 1
            except (ValueError, TypeError, KeyError):
                continue
        counts[day_key] = count
        current += timedelta(days=1)
    return counts


def compute_volume_zscore(
    daily_counts: dict[str, int],
    window: int = None,
) -> dict[str, float]:
    """Rolling z-score of daily article count."""
    if window is None:
        window = config.VOLUME_ROLLING_WINDOW
    s = pd.Series(daily_counts)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index().astype(float)

    roll_mean = s.rolling(window, min_periods=5).mean()
    roll_std = s.rolling(window, min_periods=5).std()
    roll_std = roll_std.replace(0, 1)  # avoid division by zero

    zscore = (s - roll_mean) / roll_std
    return {k.strftime("%Y-%m-%d"): round(float(v), 4) if not np.isnan(v) else 0.0
            for k, v in zscore.items()}


def detect_volume_spikes(
    volume_zscores: dict[str, float],
    threshold: float = None,
) -> dict[str, bool]:
    """Mark days where volume z-score exceeds threshold."""
    if threshold is None:
        threshold = config.VOLUME_SPIKE_THRESHOLD
    return {k: v > threshold for k, v in volume_zscores.items()}


def build_volume_series(
    scored_articles: list[dict],
    start_date: datetime,
    end_date: datetime,
    window: int = None,
) -> pd.DataFrame:
    """Full pipeline: daily count -> z-score -> spike flag."""
    counts = compute_daily_volume(scored_articles, start_date, end_date)
    zscores = compute_volume_zscore(counts, window)
    spikes = detect_volume_spikes(zscores)

    df = pd.DataFrame({
        "count": pd.Series(counts),
        "zscore": pd.Series(zscores),
        "is_spike": pd.Series(spikes),
    })
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df


if __name__ == "__main__":
    import news_fetcher
    import sentiment_analyzer

    sentiment_analyzer.load_model()

    for asset in ["XAUUSD", "SPX"]:
        weekly = news_fetcher.fetch_historical_news(asset, weeks=52)
        flat = []
        for arts in weekly.values():
            flat.extend(arts)

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=365)
        vol_df = build_volume_series(flat, start, now)

        spikes = vol_df[vol_df["is_spike"]]
        print(f"{asset}: {len(vol_df)} days, {len(spikes)} spike days")
        if not spikes.empty:
            for idx, row in spikes.head(5).iterrows():
                print(f"  {idx.date()}: {int(row['count'])} articles (z={row['zscore']:.1f})")
