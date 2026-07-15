import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ── Asset Definitions ──────────────────────────────────────────────────────────
ASSETS = {
    "EURUSD": {
        "queries": [
            "EURUSD forex market",
            "euro dollar exchange rate outlook",
            "EUR USD trading forecast",
        ],
        "ticker": "EURUSD=X",
        "name": "EUR/USD",
    },
    "USDJPY": {
        "queries": [
            "USDJPY forex market",
            "dollar yen exchange rate outlook",
            "USD JPY trading forecast",
        ],
        "ticker": "USDJPY=X",
        "name": "USD/JPY",
    },
    "USDCHF": {
        "queries": [
            "USDCHF forex market",
            "dollar franc exchange rate outlook",
            "USD CHF trading forecast",
        ],
        "ticker": "USDCHF=X",
        "name": "USD/CHF",
    },
    "GBPUSD": {
        "queries": [
            "GBPUSD forex market",
            "pound dollar exchange rate outlook",
            "GBP USD trading forecast",
        ],
        "ticker": "GBPUSD=X",
        "name": "GBP/USD",
    },
    "AUDUSD": {
        "queries": [
            "AUDUSD forex market",
            "australian dollar exchange rate outlook",
            "AUD USD trading forecast",
        ],
        "ticker": "AUDUSD=X",
        "name": "AUD/USD",
    },
    "NZDUSD": {
        "queries": [
            "NZDUSD forex market",
            "new zealand dollar exchange rate outlook",
            "NZD USD trading forecast",
        ],
        "ticker": "NZDUSD=X",
        "name": "NZD/USD",
    },
    "USDCAD": {
        "queries": [
            "USDCAD forex market",
            "dollar canadian exchange rate outlook",
            "USD CAD trading forecast",
        ],
        "ticker": "USDCAD=X",
        "name": "USD/CAD",
    },
    "USDNOK": {
        "queries": [
            "Norwegian krone forex outlook",
            "Norway economy currency forecast",
            "Norges Bank interest rate NOK",
        ],
        "ticker": "USDNOK=X",
        "name": "USD/NOK",
    },
    "USDSEK": {
        "queries": [
            "USDSEK forex market",
            "dollar swedish krona outlook",
            "USD SEK trading forecast",
        ],
        "ticker": "USDSEK=X",
        "name": "USD/SEK",
    },
    "XAUUSD": {
        "queries": [
            "gold price forecast outlook",
            "XAUUSD gold market trading",
            "gold price analysis today",
        ],
        "ticker": "GC=F",
        "name": "Gold (XAU/USD)",
    },
    "XAGUSD": {
        "queries": [
            "silver price forecast outlook",
            "XAGUSD silver market trading",
            "silver price analysis today",
        ],
        "ticker": "SI=F",
        "name": "Silver (XAG/USD)",
    },
    "SPX": {
        "queries": [
            "S&P 500 market outlook",
            "SPX stock market forecast",
            "S&P 500 trading analysis",
        ],
        "ticker": "^GSPC",
        "name": "S&P 500",
    },
    "UST2Y": {
        "queries": [
            "US 2 year treasury bond price",
            "short term treasury buying demand",
            "Fed rate cut bond rally",
        ],
        "ticker": "ZT=F",
        "name": "US Treasury 2Y",
        "invert_sentiment": True,
    },
    "UST10Y": {
        "queries": [
            "US 10 year treasury bond price",
            "treasury bond buying demand",
            "treasury yields falling bond rally",
        ],
        "ticker": "ZN=F",
        "name": "US Treasury 10Y",
        "invert_sentiment": True,
    },
    "BIST100": {
        "queries": [
            "BIST 100 borsa Istanbul",
            "Borsa Istanbul endeks analiz",
            "BIST100 hisse senedi piyasa",
        ],
        "queries_en": [
            "Turkey stock market",
            "Turkish equities market economy",
            "Istanbul stock exchange BIST",
        ],
        "ticker": "XU100.IS",
        "name": "BIST 100",
        "language": "tr",
    },
}

# ── Sentiment Thresholds ───────────────────────────────────────────────────────
# Calibrated to z-score normalized distribution:
# Extremely = top/bottom ~15% (P15/P85)
# Bullish/Bearish = next ~25% each
# Neutral = middle ~20%
SENTIMENT_THRESHOLDS = {
    "extremely_bearish": -0.50,
    "bearish": -0.10,
    "bullish": 0.10,
    "extremely_bullish": 0.50,
}

SENTIMENT_LABELS = [
    "Extremely Bearish",
    "Bearish",
    "Neutral",
    "Bullish",
    "Extremely Bullish",
]

SENTIMENT_COLORS = {
    "Extremely Bearish": "#d32f2f",
    "Bearish": "#ff7043",
    "Neutral": "#90a4ae",
    "Bullish": "#66bb6a",
    "Extremely Bullish": "#2e7d32",
}

# ── Momentum / Acceleration ────────────────────────────────────────────────────
MOMENTUM_COLORS = {
    "Accelerating Bullish": "#2e7d32",
    "Decelerating Bullish": "#ffa726",
    "Accelerating Bearish": "#d32f2f",
    "Decelerating Bearish": "#42a5f5",
    "Neutral": "#90a4ae",
}
DERIVATIVE_EMA_SPAN = 5

# ── Volume Spike ───────────────────────────────────────────────────────────────
VOLUME_SPIKE_THRESHOLD = 2.0
VOLUME_AMPLIFICATION = 0.3
VOLUME_ROLLING_WINDOW = 20

# ── Regime Detection ───────────────────────────────────────────────────────────
REGIME_THRESHOLDS = {"risk_off": 0.15, "risk_on": -0.10}

# Risk-off = safe havens bullish while risk assets bearish
RISK_OFF_ASSETS = ["XAUUSD", "XAGUSD", "UST10Y", "UST2Y", "USDJPY", "USDCHF"]
RISK_ON_ASSETS = ["SPX", "AUDUSD", "NZDUSD"]

# Assets whose sentiment must be INVERTED for unified PC1/regime direction
# USDXXX: bullish news = USD strong = invert for "risk-on = positive" convention
# UST: already inverted via invert_sentiment (yield→price), no extra flip needed
PC1_INVERT_ASSETS = ["USDJPY", "USDCHF", "USDCAD", "USDNOK", "USDSEK"]
REGIME_COLORS = {
    "Risk-Off": "#d32f2f",
    "Risk-On": "#66bb6a",
    "Transitioning": "#ffa726",
}
REGIME_WINDOW = 20

# ── Alternative Data Sources ──────────────────────────────────────────────────
ALTERNATIVE_SOURCES = {
    "SPX": {"reddit_subs": ["wallstreetbets", "stocks"], "finviz_tickers": ["SPY"], "twitter_cashtags": ["$SPX"]},
    "XAUUSD": {"reddit_subs": ["Gold", "investing"], "finviz_tickers": ["GLD"], "twitter_cashtags": ["$GOLD"]},
    "XAGUSD": {"reddit_subs": ["investing"], "finviz_tickers": ["SLV"], "twitter_cashtags": ["$SILVER"]},
    "EURUSD": {"reddit_subs": ["forex"], "twitter_cashtags": ["$EURUSD"]},
    "GBPUSD": {"reddit_subs": ["forex"], "twitter_cashtags": ["$GBPUSD"]},
    "USDJPY": {"reddit_subs": ["forex"], "twitter_cashtags": ["$USDJPY"]},
}
SOURCE_WEIGHTS = {"google_news": 1.0, "reddit": 0.7, "finviz": 0.9, "twitter": 0.5}

# ── Default Index Parameters ───────────────────────────────────────────────────
DEFAULT_PARAMS = {
    "time_decay_halflife": 2.0,
    "aggregation": "directional_strength",
    "score_transform": "raw",
    "lag_days": 0,
    "neutral_filter": 0.0,
    "momentum_weight": 0.0,
    "volume_normalize": False,
}

# ── Optimization Grid ─────────────────────────────────────────────────────────
# Optimized for rolling 20-day correlation mean (not overall Spearman)
# Total: 4×4×3×2×2×2 = 384 combinations
PARAM_GRID = {
    "time_decay_halflife": [1, 2, 3, 5],
    "aggregation": [
        "weighted_mean",
        "bull_bear_ratio",
        "intensity_ratio",
        "directional_strength",
    ],
    "score_transform": ["raw", "tanh", "amplify"],
    "lag_days": [0, 1],
    "neutral_filter": [0.0, 0.1],
    "momentum_weight": [0.0, 0.2],
}

# ── Time Windows ───────────────────────────────────────────────────────────────
LOOKBACK_DAYS = 7        # sentiment window per week
HISTORY_DAYS = 365       # price history
HISTORY_WEEKS = 52       # weeks for correlation analysis
EXPECTED_ARTICLES = 50   # baseline for volume normalization

# ── GDELT Configuration ───────────────────────────────────────────────────────
GDELT_CONFIG = {
    "base_url": "https://api.gdeltproject.org/api/v2/doc/doc",
    "max_records": 250,
    "rate_limit_seconds": 6,
}

# ── Cache Settings ─────────────────────────────────────────────────────────────
CACHE_TTL_SECONDS = 3600  # 1 hour (for real-time Google RSS)

# ── File Paths ─────────────────────────────────────────────────────────────────
NEWS_CACHE = os.path.join(DATA_DIR, "news_cache.json")
SENTIMENT_SCORES = os.path.join(DATA_DIR, "sentiment_scores.json")
INDEX_HISTORY = os.path.join(DATA_DIR, "index_history.json")
OPTIMIZED_PARAMS = os.path.join(DATA_DIR, "optimized_params.json")
GDELT_CACHE = os.path.join(DATA_DIR, "gdelt_cache.json")
WEEKLY_SCORES = os.path.join(DATA_DIR, "weekly_scores.json")
