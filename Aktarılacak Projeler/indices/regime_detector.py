"""Cross-asset regime detection — Risk-On / Risk-Off based on basket spread."""

import numpy as np
import pandas as pd

import config


def build_sentiment_matrix(
    all_sentiment_series: dict[str, pd.Series],
    unify_direction: bool = False,
) -> pd.DataFrame:
    """Align all asset sentiment series into a single DataFrame.
    If unify_direction=True, invert USDXXX pairs so all sentiments share
    the same macro direction (risk-on = positive).
    """
    df = pd.DataFrame(all_sentiment_series)
    df = df.sort_index().ffill().dropna(how="all")

    if unify_direction:
        for col in df.columns:
            if col in config.PC1_INVERT_ASSETS:
                df[col] = -df[col]

    return df


def compute_basket_spread(
    sentiment_df: pd.DataFrame,
    window: int = None,
) -> pd.Series:
    """
    Risk-Off spread = avg(safe haven sentiments) - avg(risk asset sentiments).
    Positive = risk-off (safe havens bullish, risk assets bearish).
    Negative = risk-on (risk assets bullish).

    NOT: sentiment_df YON-BIRLESTIRILMIS matris olmalidir (unify_direction=True).
    Guvenli liman sepetindeki USDJPY/USDCHF paritelerinde ham seri USD yonunu
    olcer; yen/frank gucu (klasik risk-off) ancak terslenmis seriyle dogru
    isarete oturur. Ham matrisle bu iki bacak spread'i tersine kirletir.
    """
    if window is None:
        window = config.REGIME_WINDOW

    risk_off_cols = [c for c in config.RISK_OFF_ASSETS if c in sentiment_df.columns]
    risk_on_cols = [c for c in config.RISK_ON_ASSETS if c in sentiment_df.columns]

    if not risk_off_cols or not risk_on_cols:
        return pd.Series(dtype=float)

    safe_avg = sentiment_df[risk_off_cols].mean(axis=1)
    risk_avg = sentiment_df[risk_on_cols].mean(axis=1)
    spread = safe_avg - risk_avg

    # Smooth with rolling mean
    spread_smooth = spread.rolling(window, min_periods=5).mean()
    return spread_smooth


def classify_regime(spread_value: float) -> str:
    """Classify based on basket spread value."""
    t = config.REGIME_THRESHOLDS
    if spread_value > t["risk_off"]:
        return "Risk-Off"
    elif spread_value < t["risk_on"]:
        return "Risk-On"
    return "Transitioning"


def compute_average_correlation(
    sentiment_df: pd.DataFrame,
    window: int = None,
) -> pd.Series:
    """Average pairwise correlation.

    NOT: sentiment_df YON-BIRLESTIRILMIS matris olmalidir. Ham matriste
    USD-bazli paritelerin makro yonu ters oldugundan pozitif/negatif
    korelasyonlar birbirini goturur ve ortalama yapisal olarak ~0 cikar —
    tema konsantrasyonu gorunmez olur. (16.07.2026 duzeltmesi)
    """
    if window is None:
        window = config.REGIME_WINDOW
    n_assets = len(sentiment_df.columns)
    if n_assets < 2:
        return pd.Series(dtype=float)

    avg_corrs = []
    dates = []
    for i in range(window, len(sentiment_df)):
        window_data = sentiment_df.iloc[i - window:i]
        corr_matrix = window_data.corr()
        mask = np.triu(np.ones(corr_matrix.shape, dtype=bool), k=1)
        upper = corr_matrix.where(mask)
        avg_corrs.append(upper.stack().mean())
        dates.append(sentiment_df.index[i])

    return pd.Series(avg_corrs, index=dates, name="avg_correlation")


def compute_pca_sentiment(
    sentiment_df: pd.DataFrame,
    window: int = 60,
) -> pd.Series:
    """First principal component — market-wide sentiment factor."""
    try:
        from sklearn.decomposition import PCA
    except ImportError:
        return pd.Series(dtype=float)

    if len(sentiment_df) < window or len(sentiment_df.columns) < 3:
        return pd.Series(dtype=float)

    pc1_values = []
    dates = []
    for i in range(window, len(sentiment_df)):
        window_data = sentiment_df.iloc[i - window:i].dropna(axis=1, how="any")
        if window_data.shape[1] < 3:
            pc1_values.append(0.0)
            dates.append(sentiment_df.index[i])
            continue
        try:
            pca = PCA(n_components=1)
            components = pca.fit_transform(window_data)
            pc1_values.append(float(components[-1, 0]))
        except Exception:
            pc1_values.append(0.0)
        dates.append(sentiment_df.index[i])

    return pd.Series(pc1_values, index=dates, name="pc1_sentiment")


def compute_regime(
    all_sentiment_series: dict[str, pd.Series],
    window: int = None,
) -> dict:
    """Main entry point for regime detection using basket spread."""
    if window is None:
        window = config.REGIME_WINDOW

    # YON-BIRLESTIRILMIS matris (USDXXX terslenir): spread, korelasyon ve PCA
    # ucu de bu matrisi kullanir. Gerekce: USDJPY bullish = yen zayif; guvenli
    # liman okumasi ve capraz korelasyon ancak ortak makro yonde anlamlidir.
    # (16.07.2026 duzeltmesi — onceden spread ve korelasyon ham matristeydi)
    sent_df = build_sentiment_matrix(all_sentiment_series, unify_direction=False)
    sent_df_unified = build_sentiment_matrix(all_sentiment_series, unify_direction=True)

    # Basket spread (primary regime signal) — unified directions
    basket_spread = compute_basket_spread(sent_df_unified, window)

    # Average correlation — unified directions
    avg_corr_series = compute_average_correlation(sent_df_unified, window)

    # PCA — unified direction (USDXXX inverted)
    pc1_series = compute_pca_sentiment(sent_df_unified)

    # Current regime
    current_spread = float(basket_spread.iloc[-1]) if len(basket_spread) > 0 else 0.0
    current_regime = classify_regime(current_spread)

    # Heatmap — yon-birlestirilmis (USDXXX etiketlerinde terslendigi belirtilmeli)
    if len(sent_df_unified) >= window:
        heatmap = sent_df_unified.iloc[-window:].corr()
    else:
        heatmap = sent_df_unified.corr()

    # Regime history from basket spread
    regime_history = basket_spread.apply(classify_regime) if len(basket_spread) > 0 else pd.Series(dtype=str)

    return {
        "regime": current_regime,
        "basket_spread": current_spread,
        "basket_spread_series": basket_spread,
        "avg_corr_series": avg_corr_series,
        "pc1_series": pc1_series,
        "heatmap": heatmap,
        "regime_history": regime_history,
    }
