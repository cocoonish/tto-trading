"""Build sentiment indices from scored headlines — daily and weekly."""

import json
import math
import os
from datetime import datetime, timezone, timedelta

import numpy as np

import config
import news_fetcher
import sentiment_analyzer


# ── Score Transforms ───────────────────────────────────────────────────────────

def apply_transform(score: float, method: str) -> float:
    if method == "sigmoid":
        return 2.0 / (1.0 + math.exp(-3.0 * score)) - 1.0
    elif method == "tanh":
        return math.tanh(2.0 * score)
    elif method == "amplify":
        sign = 1.0 if score >= 0 else -1.0
        return sign * (abs(score) ** 0.5)
    return score


# ── Time Weights ───────────────────────────────────────────────────────────────

def compute_time_weights(published_dates: list[str], halflife: float,
                         reference_time: datetime = None) -> np.ndarray:
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)
    lam = math.log(2) / max(halflife, 0.1)
    weights = []
    for d in published_dates:
        try:
            pub = datetime.fromisoformat(d)
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            pub = reference_time
        age_days = max(0, (reference_time - pub).total_seconds() / 86400)
        weights.append(math.exp(-lam * age_days))
    return np.array(weights)


# ── Aggregation Methods ────────────────────────────────────────────────────────

def aggregate_weighted_mean(scores: np.ndarray, weights: np.ndarray) -> float:
    if len(scores) == 0 or weights.sum() == 0:
        return 0.0
    return float(np.average(scores, weights=weights))


def aggregate_bull_bear_ratio(scores: np.ndarray, weights: np.ndarray) -> float:
    bull_weight = weights[scores > 0].sum()
    bear_weight = weights[scores < 0].sum()
    total = bull_weight + bear_weight
    if total == 0:
        return 0.0
    return float((bull_weight - bear_weight) / total)


def aggregate_intensity_ratio(scores: np.ndarray, weights: np.ndarray) -> float:
    pos_mask = scores > 0
    neg_mask = scores < 0
    pos_intensity = (scores[pos_mask] * weights[pos_mask]).sum() if pos_mask.any() else 0.0
    neg_intensity = (np.abs(scores[neg_mask]) * weights[neg_mask]).sum() if neg_mask.any() else 0.0
    total = pos_intensity + neg_intensity
    if total == 0:
        return 0.0
    return float((pos_intensity - neg_intensity) / total)


def aggregate_directional_strength(scores: np.ndarray, weights: np.ndarray) -> float:
    strong_mask = np.abs(scores) > 0.3
    if strong_mask.any():
        return float(np.average(scores[strong_mask], weights=weights[strong_mask]))
    if len(scores) > 0 and weights.sum() > 0:
        return float(np.average(scores, weights=weights))
    return 0.0


AGGREGATORS = {
    "mean": lambda s, w: float(np.mean(s)) if len(s) > 0 else 0.0,
    "weighted_mean": aggregate_weighted_mean,
    "median": lambda s, w: float(np.median(s)) if len(s) > 0 else 0.0,
    "bull_bear_ratio": aggregate_bull_bear_ratio,
    "intensity_ratio": aggregate_intensity_ratio,
    "directional_strength": aggregate_directional_strength,
}


# ── Momentum ───────────────────────────────────────────────────────────────────

def compute_momentum(scored_articles: list[dict], reference_time: datetime,
                     lookback_days: int = 7) -> float:
    recent_cutoff = reference_time - timedelta(days=2)
    old_cutoff = reference_time - timedelta(days=lookback_days)
    recent_scores, older_scores = [], []
    for a in scored_articles:
        try:
            pub = datetime.fromisoformat(a["published"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        score = a.get("score", 0)
        if pub >= recent_cutoff:
            recent_scores.append(score)
        elif pub >= old_cutoff:
            older_scores.append(score)
    recent_avg = np.mean(recent_scores) if recent_scores else 0.0
    older_avg = np.mean(older_scores) if older_scores else 0.0
    return float(recent_avg - older_avg)


# ── Core Index Computation ─────────────────────────────────────────────────────

def _compute_index_value(scored_articles: list[dict], params: dict,
                         reference_time: datetime = None) -> tuple[float, int]:
    """Core computation. Returns (index_value, n_articles_used)."""
    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    lookback = timedelta(days=config.LOOKBACK_DAYS)
    cutoff = reference_time - lookback

    filtered = []
    for a in scored_articles:
        try:
            pub = datetime.fromisoformat(a["published"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if cutoff <= pub <= reference_time:
                filtered.append(a)
        except (ValueError, TypeError, KeyError):
            continue

    if not filtered:
        return 0.0, 0

    raw_scores = np.array([a.get("score", 0) for a in filtered])

    # Neutral filter
    neutral_thresh = params.get("neutral_filter", 0.0)
    if neutral_thresh > 0:
        mask = np.abs(raw_scores) >= neutral_thresh
        if mask.any():
            filtered = [a for a, m in zip(filtered, mask) if m]
            raw_scores = raw_scores[mask]

    n_articles = len(filtered)
    if n_articles == 0:
        return 0.0, 0

    transform = params.get("score_transform", "raw")
    transformed = np.array([apply_transform(s, transform) for s in raw_scores])

    dates = [a["published"] for a in filtered]
    weights = compute_time_weights(dates, params.get("time_decay_halflife", 2.0),
                                   reference_time=reference_time)

    # Apply source weights (Google=1.0, Reddit=0.7, Finviz=0.9, etc.)
    source_weights = np.array([a.get("source_weight", 1.0) for a in filtered])
    weights = weights * source_weights

    agg_method = params.get("aggregation", "bull_bear_ratio")
    aggregator = AGGREGATORS.get(agg_method, aggregate_intensity_ratio)
    index_value = aggregator(transformed, weights)

    if params.get("volume_normalize", False):
        vol_factor = min(1.0, n_articles / config.EXPECTED_ARTICLES)
        index_value *= vol_factor

    momentum_w = params.get("momentum_weight", 0.0)
    if momentum_w > 0:
        momentum = compute_momentum(filtered, reference_time)
        index_value = (1 - momentum_w) * index_value + momentum_w * momentum

    index_value = max(-1.0, min(1.0, index_value))
    return index_value, n_articles


# ── Build Index (single snapshot) ──────────────────────────────────────────────

def build_index(scored_articles: list[dict], params: dict = None,
                reference_time: datetime = None) -> dict:
    """Build a single sentiment index value."""
    if params is None:
        params = config.DEFAULT_PARAMS.copy()

    index_value, n_articles = _compute_index_value(scored_articles, params, reference_time)
    category = sentiment_analyzer.get_sentiment_label(index_value)

    dates = []
    cutoff = (reference_time or datetime.now(timezone.utc)) - timedelta(days=config.LOOKBACK_DAYS)
    for a in scored_articles:
        try:
            pub = datetime.fromisoformat(a["published"])
            if pub.tzinfo is None:
                pub = pub.replace(tzinfo=timezone.utc)
            if pub >= cutoff:
                dates.append(a["published"])
        except (ValueError, TypeError, KeyError):
            continue

    return {
        "value": round(index_value, 4),
        "category": category,
        "n_articles": n_articles,
        "date_range": [min(dates), max(dates)] if dates else [None, None],
        "params": params,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Build Weekly Index Series (for correlation) ───────────────────────────────

def build_weekly_index_series(
    weekly_articles: dict[str, list[dict]],
    params: dict,
) -> dict[str, float]:
    """
    Build weekly sentiment series from pre-segmented weekly articles.
    No look-ahead bias: only uses articles from current + prior weeks.
    """
    sorted_weeks = sorted(weekly_articles.keys())
    series = {}
    lookback = params.get("lookback_weeks", 1)

    for i, week_date in enumerate(sorted_weeks):
        # Combine articles from lookback_weeks
        combined = []
        for j in range(max(0, i - lookback + 1), i + 1):
            combined.extend(weekly_articles[sorted_weeks[j]])

        if not combined:
            series[week_date] = 0.0
            continue

        # Reference time = end of this week (Sunday 23:59)
        try:
            ref_date = datetime.fromisoformat(week_date)
        except ValueError:
            ref_date = datetime.strptime(week_date, "%Y-%m-%d")
        ref_time = ref_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)

        val, _ = _compute_index_value(combined, params, reference_time=ref_time)
        series[week_date] = round(val, 4)

    return series


# ── Z-Score Normalization ──────────────────────────────────────────────────────

def normalize_index_series(series: dict[str, float]) -> dict[str, float]:
    """
    Z-score normalize + tanh scale to spread signal across [-1, +1].
    Monotonic transform → preserves Spearman correlation.
    """
    vals = np.array(list(series.values()))
    nonzero = vals[vals != 0]
    if len(nonzero) < 10:
        return series

    mean, std = nonzero.mean(), nonzero.std()
    if std < 1e-6:
        return series

    normalized = {}
    for k, v in series.items():
        z = (v - mean) / std
        normalized[k] = round(float(np.tanh(z * 0.5)), 4)
    return normalized


def smooth_series(series: dict[str, float], span: int = 5) -> dict[str, float]:
    """Apply EMA smoothing to reduce day-to-day noise while preserving trend."""
    import pandas as pd
    s = pd.Series(series)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()
    smoothed = s.ewm(span=span, min_periods=1).mean()
    return {k.strftime("%Y-%m-%d"): round(float(v), 4) for k, v in smoothed.items()}


# ── Sentiment Derivatives (Momentum & Acceleration) ───────────────────────────

def compute_derivatives(daily_series: dict[str, float], ema_span: int = 5) -> dict:
    """
    Compute velocity (1st derivative) and acceleration (2nd derivative).
    Returns: {velocity: {date: float}, acceleration: {date: float}, signals: {date: str}}
    """
    import pandas as pd
    s = pd.Series(daily_series)
    s.index = pd.to_datetime(s.index)
    s = s.sort_index()

    velocity = s.diff(1).ewm(span=ema_span, min_periods=1).mean()
    acceleration = velocity.diff(1).ewm(span=ema_span, min_periods=1).mean()

    signals = {}
    for date in s.index:
        v = velocity.get(date, 0)
        a = acceleration.get(date, 0)
        if abs(v) < 0.01:
            sig = "Neutral"
        elif v > 0 and a > 0:
            sig = "Accelerating Bullish"
        elif v > 0:
            sig = "Decelerating Bullish"
        elif v < 0 and a < 0:
            sig = "Accelerating Bearish"
        else:
            sig = "Decelerating Bearish"
        signals[date.strftime("%Y-%m-%d")] = sig

    return {
        "velocity": {k.strftime("%Y-%m-%d"): round(float(v), 4) for k, v in velocity.items()},
        "acceleration": {k.strftime("%Y-%m-%d"): round(float(v), 4) for k, v in acceleration.items()},
        "signals": signals,
    }


def get_momentum_arrow(signal: str) -> str:
    """Unicode arrow for momentum signal."""
    return {
        "Accelerating Bullish": "↗↗",
        "Decelerating Bullish": "→↘",
        "Accelerating Bearish": "↘↘",
        "Decelerating Bearish": "→↗",
        "Neutral": "→",
    }.get(signal, "→")


# ── Build Daily Index Series ───────────────────────────────────────────────────

def build_daily_index_series(
    scored_articles: list[dict],
    params: dict,
    start_date: datetime,
    end_date: datetime,
) -> dict[str, float]:
    """Build daily time series with volume amplification, z-score normalization + EMA smoothing.
    Excludes today (current UTC date) — sentiment score is only final after day ends."""
    series = {}
    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    current = start_date
    while current <= end_date:
        day_key = current.strftime("%Y-%m-%d")
        if day_key >= today_utc:
            break  # don't compute today or future — day not complete
        val, _ = _compute_index_value(scored_articles, params, reference_time=current)
        series[day_key] = round(val, 4)
        current += timedelta(days=1)

    # Volume amplification (before normalization)
    vol_amp = params.get("volume_amplification", 0.0)
    if vol_amp > 0:
        import volume_analyzer
        vol_counts = volume_analyzer.compute_daily_volume(scored_articles, start_date, end_date)
        vol_zscores = volume_analyzer.compute_volume_zscore(vol_counts)
        for dk in series:
            vz = vol_zscores.get(dk, 0.0)
            if vz > 0:
                series[dk] *= (1 + vz * vol_amp)
                series[dk] = max(-1.0, min(1.0, series[dk]))

    # Z-score normalize to spread signal, then smooth to reduce noise
    normalized = normalize_index_series(series)
    return smooth_series(normalized, span=3)


# ── Build All (real-time snapshot) ─────────────────────────────────────────────

def build_all_indices(params: dict = None) -> dict:
    """Build indices for all assets using Google News RSS (real-time)."""
    indices = {}
    for asset_key in config.ASSETS:
        articles = news_fetcher.fetch_all_news_cached(asset_key)
        if articles and "score" not in articles[0]:
            articles = sentiment_analyzer.analyze_articles(articles)
            sentiment_analyzer.save_scores(asset_key, articles)
        idx = build_index(articles, params)
        indices[asset_key] = idx
    return indices


# ── History Persistence ────────────────────────────────────────────────────────

def save_index_snapshot(indices: dict, regime: dict = None):
    """Append snapshot to index history. Optional `regime` dict
    (label / basket_spread / avg_correlation / pc1_share / as_of) is stored
    alongside so a regime time series can be charted later."""
    os.makedirs(config.DATA_DIR, exist_ok=True)

    # Kismi kosu (or. run.py --asset EURUSD) tarihceye YAZILMAZ. Boyle bir
    # snapshot 15 varlikli seriyle ayni eksende sahte tarihce uretir; ustelik
    # asagidaki gun-basina-tek kurali yuzunden o gunun tam kaydini ezerdi.
    kapsam = len(indices)
    if kapsam < len(config.ASSETS):
        print(f"  Tarihceye yazilmadi: kismi kosu ({kapsam}/{len(config.ASSETS)} varlik).")
        return

    history = []
    if os.path.exists(config.INDEX_HISTORY):
        with open(config.INDEX_HISTORY, "r") as f:
            history = json.load(f)
    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "indices": {k: {"value": v["value"], "category": v["category"]}
                    for k, v in indices.items()},
    }
    # SNAPSHOT'IN KENDI SAATI. Bu dosyada iki ayri olcum yan yana duruyor ve
    # saatleri farkli: `indices` degerleri Google RSS akisindan, kosu anindan
    # geriye 7 gunluk pencereyle kuruluyor; `regime` ise GDELT haftalik
    # onbelleginden geliyor ve onun ucu son TAM haftadir (Pazar). Ikisini tek
    # bir "kosu zamani" damgasiyla anlatmak, 26.08 Carsamba kosan bir hattin
    # rejim panelini de 26.08 gibi gostermek demek — oysa o panel 23.08'i
    # olcuyor (bkz. CLAUDE.md "Kurucu ilke - saat").
    #
    # Bu yuzden snapshot kendi veri ucunu YAZAR: endekse giren en yeni
    # makalenin yayim zamani. Olculen sey budur; kosu saati ayri alanda kalir.
    uclar = []
    for v in indices.values():
        if not isinstance(v, dict):
            continue
        aralik = v.get("date_range") or [None, None]
        uc = aralik[1] if len(aralik) > 1 else None
        if uc:
            uclar.append(uc)
    if uclar:
        snapshot["veri_sonu"] = max(uclar)

    if regime:
        snapshot["regime"] = regime

    # Gun basina TEK snapshot. Ayni gun icindeki ikinci kosu bagimsiz bir gozlem
    # degil, ayni gunun yeniden hesabidir (or. parametreler yenilendikten sonra
    # tekrar kosmak); ucunu birden cizmek rejim tarihcesini carpitir. Ayni gune
    # ait onceki kayit varsa uzerine yazilir.
    gun = snapshot["timestamp"][:10]
    history = [s for s in history if s.get("timestamp", "")[:10] != gun]
    history.append(snapshot)
    history.sort(key=lambda s: s.get("timestamp", ""))

    with open(config.INDEX_HISTORY, "w") as f:
        json.dump(history, f, indent=2)


if __name__ == "__main__":
    indices = build_all_indices()
    save_index_snapshot(indices)
    print("\nFinal Index Summary:")
    for k, v in indices.items():
        print(f"  {k}: {v['value']:+.4f} ({v['category']}) [{v['n_articles']} articles]")
