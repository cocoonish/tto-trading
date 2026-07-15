"""Streamlit dashboard — daily sentiment vs 5-day returns."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

import config
import news_fetcher
import sentiment_analyzer
import index_builder
import price_fetcher
import correlation_optimizer
import volume_analyzer
import regime_detector

st.set_page_config(page_title="Sentiment Index Dashboard", page_icon="📊", layout="wide")
st.title("News Sentiment Index Dashboard")
st.caption(f"{len(config.ASSETS)} assets — Daily sentiment vs 5-day returns (1 year history)")

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")
    if st.button("Refresh Real-time", type="primary", width="stretch"):
        st.cache_data.clear()
        if os.path.exists(config.NEWS_CACHE):
            os.remove(config.NEWS_CACHE)
        st.rerun()

    if st.button("Update Historical (new days)", width="stretch"):
        """Fetch only missing recent weeks, score them. Won't re-fetch cached data.
        Only completes up to yesterday (today's sentiment not final until day ends)."""
        progress = st.progress(0, text="Updating...")
        n_assets = len(config.ASSETS)
        cached = news_fetcher._load_historical_cache()
        for i, ak in enumerate(config.ASSETS):
            progress.progress((i) / n_assets, text=f"Updating {ak}...")
            # Only fetch last 2 weeks (new data)
            weekly = news_fetcher.fetch_historical_news(ak, weeks=2)
            # Score new articles
            for wk, arts in weekly.items():
                if arts and "score" not in arts[0]:
                    sentiment_analyzer.analyze_articles(arts)
            # Save incrementally
            c = news_fetcher._load_historical_cache()
            if ak in c:
                for wk, entry in c[ak].items():
                    arts = entry.get("articles", [])
                    if arts and "score" not in arts[0]:
                        sentiment_analyzer.analyze_articles(arts)
                news_fetcher._save_historical_cache(c)
        progress.progress(1.0, text="Done!")
        st.success("Historical data updated (up to yesterday)")
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("Parameters")
    opt_params = correlation_optimizer.load_optimized_params()
    use_optimized = bool(opt_params) and st.toggle("Use Optimized Parameters", value=bool(opt_params))

    if not use_optimized:
        halflife = st.slider("Time Decay Half-life (days)", 1.0, 7.0, 2.0, 0.5)
        agg = st.selectbox("Aggregation", ["bull_bear_ratio", "intensity_ratio",
                                            "directional_strength", "weighted_mean"])
        transform = st.selectbox("Transform", ["raw", "sigmoid", "tanh", "amplify"])
        lag = st.slider("Lag (days)", 0, 2, 0)
        nf = st.slider("Neutral Filter", 0.0, 0.3, 0.1, 0.05)
        mw = st.slider("Momentum Weight", 0.0, 0.5, 0.3, 0.1)
        manual_params = {"time_decay_halflife": halflife, "aggregation": agg,
                         "score_transform": transform, "lag_days": lag,
                         "neutral_filter": nf, "momentum_weight": mw, "volume_normalize": False}

    st.divider()
    st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

# ── Data Loading ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_model():
    return sentiment_analyzer.load_model()

@st.cache_data(ttl=3600)
def load_realtime():
    get_model()
    data = {}
    for ak in config.ASSETS:
        arts = news_fetcher.fetch_all_news_cached(ak)
        if arts and "score" not in arts[0]:
            sentiment_analyzer.analyze_articles(arts)
        data[ak] = arts
    return data

@st.cache_data(ttl=86400)
def load_historical():
    """Read-only from cache. Never fetches — use 'Update Historical' button to fetch."""
    import re
    data = {}
    cached = news_fetcher._load_historical_cache()
    for ak in config.ASSETS:
        if ak not in cached or not cached[ak]:
            continue
        flat = []
        for wk_data in cached[ak].values():
            flat.extend(wk_data.get("articles", []))

        # Score any unscored articles (from previous incomplete runs)
        unscored = [a for a in flat if "score" not in a]
        if unscored:
            get_model()
            sentiment_analyzer.analyze_articles(unscored)

        # Invert sentiment for bonds
        if config.ASSETS[ak].get("invert_sentiment", False):
            for a in flat:
                if "score" in a:
                    a["score"] = -a["score"]
                    a["positive"], a["negative"] = a.get("negative", 0), a.get("positive", 0)

        data[ak] = flat
    return data

@st.cache_data(ttl=3600)
def load_prices():
    return price_fetcher.fetch_all_prices()

hist_available = os.path.exists(config.GDELT_CACHE)
with st.spinner("Loading..."):
    rt_articles = load_realtime()
    prices = load_prices()

def get_params(ak):
    if use_optimized and ak in opt_params:
        return opt_params[ak]
    elif not use_optimized:
        return manual_params
    return config.DEFAULT_PARAMS.copy()

# Overview: real-time snapshot (today included, from Google RSS)
rt_indices = {}
for ak in config.ASSETS:
    params = get_params(ak)
    arts = rt_articles.get(ak, [])
    # Invert for bonds
    if config.ASSETS[ak].get("invert_sentiment", False):
        arts = [dict(a, score=-a.get("score", 0)) for a in arts if "score" in a]
    rt_indices[ak] = index_builder.build_index(arts, params)

# ── Tabs ───────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5, t6 = st.tabs(["Overview", "Time Series", "Correlation", "Regime", "Optimization", "News Feed"])

# ═══ TAB 1: OVERVIEW ══════════════════════════════════════════════════════════
with t1:
    n_assets = len(rt_indices)
    n_cols = min(4, n_assets)
    cols = st.columns(n_cols)
    for i, (ak, idx) in enumerate(rt_indices.items()):
        with cols[i % n_cols]:
            name = config.ASSETS[ak]["name"]
            v, cat = idx["value"], idx["category"]
            color = config.SENTIMENT_COLORS.get(cat, "#90a4ae")
            pdf = prices.get(ak)
            if pdf is not None and not pdf.empty:
                st.metric(name, f"{pdf['Close'].iloc[-1]:.4f}" if ak != "SPX" else f"{pdf['Close'].iloc[-1]:.2f}",
                          f"{pdf['Return_1d'].iloc[-1]*100:+.2f}%")
            else:
                st.metric(name, "N/A")

            fig = go.Figure(go.Indicator(mode="gauge+number", value=v,
                number={"suffix": f"  {cat}", "font": {"size": 14}},
                gauge={"axis": {"range": [-1, 1]}, "bar": {"color": color},
                       "steps": [{"range": [-1, -0.25], "color": "#ffcdd2"},
                                 {"range": [-0.25, -0.05], "color": "#ffe0b2"},
                                 {"range": [-0.05, 0.05], "color": "#e0e0e0"},
                                 {"range": [0.05, 0.25], "color": "#c8e6c9"},
                                 {"range": [0.25, 1], "color": "#a5d6a7"}]},
                title={"text": "Sentiment"}))
            fig.update_layout(height=250, margin=dict(t=50, b=10, l=30, r=30),
                              template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, width="stretch", key=f"gauge_{ak}")
            st.caption(f"{idx['n_articles']} articles (real-time)")

# ═══ TAB 2: TIME SERIES ══════════════════════════════════════════════════════
with t2:
    if not hist_available:
        st.warning("No historical data. Go to **Optimization** tab → **Fetch Historical Data**.")
    else:
        with st.spinner("Building daily sentiment series..."):
            hist = load_historical()
        for ak in config.ASSETS:
            name = config.ASSETS[ak]["name"]
            pdf = prices.get(ak)
            arts = hist.get(ak, [])
            if pdf is None or pdf.empty or not arts:
                continue
            params = get_params(ak)
            start = pdf.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
            end = pdf.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
            daily = index_builder.build_daily_index_series(arts, params, start, end)
            idx_s = pd.Series(daily)
            idx_s.index = pd.to_datetime(idx_s.index)

            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=pdf.index, y=pdf["Close"], name=f"{name} Price",
                                     line=dict(color="#636EFA", width=2)), secondary_y=False)
            colors = ["#d32f2f" if v < -0.05 else "#66bb6a" if v > 0.05 else "#90a4ae"
                       for v in idx_s.values]
            fig.add_trace(go.Bar(x=idx_s.index, y=idx_s.values, name="Daily Sentiment",
                                 marker_color=colors, opacity=0.6), secondary_y=True)
            fig.update_layout(title=f"{name} — Price vs Daily Sentiment (1 year)",
                              height=400, template="plotly_dark", hovermode="x unified",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02))
            fig.update_yaxes(title_text="Price", secondary_y=False)
            fig.update_yaxes(title_text="Sentiment", range=[-1, 1], secondary_y=True)
            st.plotly_chart(fig, width="stretch", key=f"ts_{ak}")

# ═══ TAB 3: CORRELATION ══════════════════════════════════════════════════════
with t3:
    if not hist_available:
        st.warning("No historical data. Fetch first.")
    else:
        with st.spinner("Computing correlations..."):
            hist = load_historical()

        # Load full optimized data for return_col info
        opt_full = correlation_optimizer.load_optimized_full()

        def _build_corr_table(return_col_label, return_col):
            """Build correlation table for a given return horizon."""
            data = []
            for ak in config.ASSETS:
                pdf = prices.get(ak)
                arts = hist.get(ak, [])
                if pdf is None or pdf.empty or not arts or return_col not in pdf.columns:
                    continue
                params = get_params(ak)
                start = pdf.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
                end = pdf.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
                daily = index_builder.build_daily_index_series(arts, params, start, end)
                idx_s = pd.Series(daily)
                idx_s.index = pd.to_datetime(idx_s.index)
                lag = params.get("lag_days", 0)
                corr = correlation_optimizer.compute_correlation(idx_s, pdf[return_col], lag=lag)
                roll = correlation_optimizer.rolling_correlation(idx_s, pdf[return_col], window=20).dropna()
                corr["rolling_mean"] = round(float(roll.mean()), 4) if len(roll) > 0 else 0.0
                corr["pct_positive"] = round(float((roll > 0).mean() * 100), 1) if len(roll) > 0 else 0.0
                corr["asset"] = ak
                data.append(corr)
            return data

        # ── Daily (1d) Correlation ──
        st.subheader("Daily Sentiment vs 1-Day Return")
        corr_1d = _build_corr_table("1d", "Return_1d")
        if corr_1d:
            df1 = pd.DataFrame(corr_1d).set_index("asset")
            st.dataframe(df1.style.format({
                "pearson_r": "{:.4f}", "pearson_p": "{:.4f}",
                "spearman_r": "{:.4f}", "spearman_p": "{:.4f}",
                "rolling_mean": "{:.4f}", "pct_positive": "{:.1f}%",
            }), width="stretch")

        # ── Weekly (5d) Correlation ──
        st.subheader("Daily Sentiment vs 5-Day Return")
        corr_5d = _build_corr_table("5d", "Return_5d")
        if corr_5d:
            df5 = pd.DataFrame(corr_5d).set_index("asset")
            st.dataframe(df5.style.format({
                "pearson_r": "{:.4f}", "pearson_p": "{:.4f}",
                "spearman_r": "{:.4f}", "spearman_p": "{:.4f}",
                "rolling_mean": "{:.4f}", "pct_positive": "{:.1f}%",
            }), width="stretch")

        # ── Comparison Summary ──
        if corr_1d and corr_5d:
            st.subheader("1d vs 5d Comparison")
            comp_rows = []
            d1 = {r["asset"]: r for r in corr_1d}
            d5 = {r["asset"]: r for r in corr_5d}
            for ak in config.ASSETS:
                if ak in d1 and ak in d5:
                    rm1 = d1[ak]["rolling_mean"]
                    rm5 = d5[ak]["rolling_mean"]
                    best = "1d" if rm1 > rm5 else "5d"
                    saved = opt_full.get(ak, {}).get("best_horizon", "")
                    comp_rows.append({
                        "asset": ak,
                        "1d_roll_mean": rm1,
                        "5d_roll_mean": rm5,
                        "best": best,
                        "optimized_for": saved if saved else "N/A",
                    })
            if comp_rows:
                comp_df = pd.DataFrame(comp_rows).set_index("asset")
                st.dataframe(comp_df.style.format({
                    "1d_roll_mean": "{:.4f}", "5d_roll_mean": "{:.4f}",
                }), width="stretch")

        # ── Rolling Correlation (5d) ──
        st.subheader("Rolling Correlation — 5d Return (20-day window)")
        fig_r = go.Figure()
        for ak in config.ASSETS:
            pdf = prices.get(ak)
            arts = hist.get(ak, [])
            if pdf is None or pdf.empty or not arts:
                continue
            params = get_params(ak)
            start = pdf.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
            end = pdf.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
            daily = index_builder.build_daily_index_series(arts, params, start, end)
            idx_s = pd.Series(daily)
            idx_s.index = pd.to_datetime(idx_s.index)
            roll = correlation_optimizer.rolling_correlation(idx_s, pdf["Return_5d"], window=20)
            if not roll.empty:
                fig_r.add_trace(go.Scatter(x=roll.index, y=roll.values, name=ak))
        fig_r.update_layout(height=500, template="plotly_dark", yaxis_title="Correlation",
                            hovermode="x unified")
        fig_r.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_r, width="stretch")

# ═══ TAB 4: REGIME DETECTION ════════════════════════════════════════════════
with t4:
    st.subheader("Cross-Asset Regime Detection")
    if not hist_available:
        st.warning("No historical data. Fetch first.")
    else:
        with st.spinner("Computing regime..."):
            hist = load_historical()
            all_series = {}
            for ak in config.ASSETS:
                pdf = prices.get(ak)
                arts = hist.get(ak, [])
                if pdf is None or pdf.empty or not arts:
                    continue
                params = get_params(ak)
                start = pdf.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
                end = pdf.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
                daily = index_builder.build_daily_index_series(arts, params, start, end)
                s = pd.Series(daily)
                s.index = pd.to_datetime(s.index)
                all_series[ak] = s

            if len(all_series) >= 3:
                regime_result = regime_detector.compute_regime(all_series)

                # Current regime badge
                regime = regime_result["regime"]
                color = config.REGIME_COLORS.get(regime, "#90a4ae")
                spread = regime_result.get("basket_spread", 0)
                st.markdown(f"### Current Regime: <span style='color:{color};font-size:1.5em'>{regime}</span> "
                            f"(basket spread: {spread:+.3f})",
                            unsafe_allow_html=True)
                st.caption(
                    "Basket Spread = avg(safe havens) - avg(risk assets). "
                    "Safe Havens: Gold, Silver, US Treasury 2Y/10Y, JPY, CHF "
                    "(sentiment inverted: bullish = USD zayifliyor / guvenli limanlara kacis). "
                    "Risk Assets: SPX, AUD, NZD "
                    "(bullish = risk istahi yuksek). "
                    "Spread > 0.15 = Risk-Off, Spread < -0.10 = Risk-On."
                )

                # Correlation heatmap
                st.subheader("Cross-Asset Correlation Heatmap")
                hm = regime_result["heatmap"]
                fig_hm = go.Figure(go.Heatmap(
                    z=hm.values, x=hm.columns, y=hm.index,
                    colorscale="RdYlGn", zmin=-1, zmax=1,
                    text=np.round(hm.values, 2), texttemplate="%{text}",
                ))
                fig_hm.update_layout(height=500, template="plotly_dark")
                st.plotly_chart(fig_hm, width="stretch")

                # Basket spread time series
                basket = regime_result.get("basket_spread_series", pd.Series())
                if len(basket) > 0:
                    st.subheader("Risk-Off Basket Spread Over Time")
                    fig_bs = go.Figure()
                    bs_colors = ["#d32f2f" if v > config.REGIME_THRESHOLDS["risk_off"]
                                 else "#66bb6a" if v < config.REGIME_THRESHOLDS["risk_on"]
                                 else "#ffa726" for v in basket.values]
                    fig_bs.add_trace(go.Bar(x=basket.index, y=basket.values,
                                            marker_color=bs_colors, opacity=0.7))
                    fig_bs.add_hline(y=config.REGIME_THRESHOLDS["risk_off"],
                                     line_dash="dash", line_color="red", annotation_text="Risk-Off")
                    fig_bs.add_hline(y=config.REGIME_THRESHOLDS["risk_on"],
                                     line_dash="dash", line_color="green", annotation_text="Risk-On")
                    fig_bs.add_hline(y=0, line_dash="solid", line_color="gray")
                    fig_bs.update_layout(height=400, template="plotly_dark",
                                         yaxis_title="Spread (Safe Haven - Risk)")
                    st.plotly_chart(fig_bs, width="stretch")

                # PC1 sentiment
                pc1 = regime_result["pc1_series"]
                if len(pc1) > 0:
                    st.subheader("Market-Wide Sentiment Factor (PC1)")
                    st.caption(
                        "PC1 = tum asset sentimentlerinin birinci temel bileseni (Principal Component). "
                        "Yuksek |PC1| = asset'ler arasi sentiment senkronizasyonu guclu "
                        "(tum piyasa ayni yone hareket ediyor). "
                        "Dusuk |PC1| = asset sentimentleri birbirinden bagimsiz. "
                        "NOT: Bullish/bearish yon gostermez — sadece hareket yogunlugunu olcer."
                    )
                    fig_pc = go.Figure(go.Scatter(x=pc1.index, y=pc1.values, fill="tozeroy",
                                                   fillcolor="rgba(0,204,150,0.15)"))
                    fig_pc.update_layout(height=300, template="plotly_dark", yaxis_title="PC1")
                    st.plotly_chart(fig_pc, width="stretch")
            else:
                st.info("Need at least 3 assets with historical data.")

# ═══ TAB 5: OPTIMIZATION ═════════════════════════════════════════════════════
with t5:
    st.subheader("Parameter Optimization")
    st.caption("Daily sentiment vs 5-day forward return — 720 combos × ~250 daily observations")

    if st.button("Fetch Historical Data (1 year)", type="secondary"):
        with st.spinner("Fetching 52 weeks of news..."):
            for ak in config.ASSETS:
                st.text(f"Fetching {ak}...")
                news_fetcher.fetch_historical_news(ak, weeks=config.HISTORY_WEEKS)
        st.success("Historical data fetched and cached!")
        st.cache_data.clear()
        st.rerun()

    if opt_params:
        st.success("Optimized parameters loaded!")
        for ak, p in opt_params.items():
            with st.expander(f"{ak}"):
                st.json(p)

    if st.button("Run Optimization", type="primary"):
        if not hist_available:
            st.error("Fetch historical data first!")
        else:
            with st.spinner("Running grid search..."):
                results = correlation_optimizer.optimize_all()
            for ak, res in results.items():
                st.subheader(ak)
                if "error" in res:
                    st.error(res["error"])
                    continue
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("IS Spearman", f"{res['in_sample']['spearman_r']:.4f}")
                with c2:
                    oos = res["out_of_sample"].get("spearman_r")
                    st.metric("OOS Spearman", f"{oos:.4f}" if oos else "N/A")
                with c3:
                    st.metric("N observations", res["in_sample"]["n_obs"])
                st.json(res["best_params"])
                if res.get("top_10"):
                    st.dataframe(pd.DataFrame(res["top_10"]).drop(columns=["abs_spearman"], errors="ignore"),
                                 width="stretch")
            st.cache_data.clear()
            st.rerun()

# ═══ TAB 6: NEWS FEED ════════════════════════════════════════════════════════
with t6:
    st.subheader("Recent Headlines")
    af = st.multiselect("Asset", list(config.ASSETS.keys()), default=list(config.ASSETS.keys()))
    sf = st.multiselect("Sentiment", config.SENTIMENT_LABELS, default=config.SENTIMENT_LABELS)
    rows = []
    for ak in af:
        for a in rt_articles.get(ak, []):
            lbl = a.get("sentiment_label", sentiment_analyzer.get_sentiment_label(a.get("score", 0)))
            if lbl in sf:
                rows.append({"Asset": ak, "Date": a.get("published", "")[:16],
                             "Headline": a.get("title", ""), "Score": a.get("score", 0),
                             "Sentiment": lbl, "Source": a.get("source", "")})
    if rows:
        df = pd.DataFrame(rows).sort_values("Date", ascending=False).reset_index(drop=True)
        def cs(v):
            return f"color: {config.SENTIMENT_COLORS.get(v, '#90a4ae')}; font-weight: bold"
        st.dataframe(df.style.map(cs, subset=["Sentiment"]).format({"Score": "{:.3f}"}),
                     width="stretch", height=600)
        st.caption(f"{len(df)} headlines")
