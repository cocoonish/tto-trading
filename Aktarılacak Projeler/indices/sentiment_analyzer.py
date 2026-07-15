"""FinBERT-based financial sentiment analysis with VADER fallback."""

import json
import os
from datetime import datetime, timezone

import config

_pipeline = None


def load_model():
    """Load FinBERT pipeline. Falls back to VADER if torch/transformers unavailable."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    try:
        import os as _os
        _os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
        from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline as hf_pipeline
        model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        _pipeline = hf_pipeline(
            "sentiment-analysis",
            model=model,
            tokenizer=tokenizer,
            top_k=None,
            device=-1,  # CPU
        )
        _pipeline._model_type = "finbert"
        print("[sentiment] FinBERT loaded successfully")
    except Exception as e:
        print(f"[sentiment] FinBERT unavailable ({e}), falling back to VADER")
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _pipeline = SentimentIntensityAnalyzer()
            _pipeline._model_type = "vader"
        except ImportError:
            raise RuntimeError(
                "Neither transformers/torch nor vaderSentiment installed. "
                "Install with: pip install transformers torch  OR  pip install vaderSentiment"
            )
    return _pipeline


def _score_finbert(headlines: list[str], pipe) -> list[dict]:
    """Score headlines using FinBERT. Returns list of score dicts."""
    results = pipe(headlines, batch_size=32, truncation=True, max_length=512)
    scored = []
    for headline, result in zip(headlines, results):
        probs = {r["label"]: r["score"] for r in result}
        pos = probs.get("positive", 0)
        neg = probs.get("negative", 0)
        neu = probs.get("neutral", 0)
        composite = pos - neg  # range [-1, +1]
        scored.append({
            "headline": headline,
            "positive": round(pos, 4),
            "negative": round(neg, 4),
            "neutral": round(neu, 4),
            "score": round(composite, 4),
        })
    return scored


def _score_vader(headlines: list[str], analyzer) -> list[dict]:
    """Score headlines using VADER. Maps compound score to [-1, +1]."""
    scored = []
    for headline in headlines:
        vs = analyzer.polarity_scores(headline)
        compound = vs["compound"]  # already [-1, +1]
        scored.append({
            "headline": headline,
            "positive": round(max(0, compound), 4),
            "negative": round(abs(min(0, compound)), 4),
            "neutral": round(1 - abs(compound), 4),
            "score": round(compound, 4),
        })
    return scored


def analyze_headlines(headlines: list[str]) -> list[dict]:
    """Score a list of headlines. Auto-selects FinBERT or VADER."""
    pipe = load_model()
    if getattr(pipe, "_model_type", "") == "finbert":
        return _score_finbert(headlines, pipe)
    else:
        return _score_vader(headlines, pipe)


def analyze_articles(articles: list[dict]) -> list[dict]:
    """Score articles (with 'title' field). Adds sentiment fields in-place."""
    headlines = [a["title"] for a in articles]
    scores = analyze_headlines(headlines)
    for article, score_data in zip(articles, scores):
        article["positive"] = score_data["positive"]
        article["negative"] = score_data["negative"]
        article["neutral"] = score_data["neutral"]
        article["score"] = score_data["score"]
        article["sentiment_label"] = get_sentiment_label(score_data["score"])
    return articles


def get_sentiment_label(score: float) -> str:
    """Map composite score to category label."""
    t = config.SENTIMENT_THRESHOLDS
    if score < t["extremely_bearish"]:
        return "Extremely Bearish"
    elif score < t["bearish"]:
        return "Bearish"
    elif score <= t["bullish"]:
        return "Neutral"
    elif score <= t["extremely_bullish"]:
        return "Bullish"
    else:
        return "Extremely Bullish"


# ── Cache ──────────────────────────────────────────────────────────────────────

def save_scores(asset_key: str, scored_articles: list[dict]):
    """Persist scored articles to disk."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    cache = {}
    if os.path.exists(config.SENTIMENT_SCORES):
        with open(config.SENTIMENT_SCORES, "r") as f:
            cache = json.load(f)
    cache[asset_key] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "articles": scored_articles,
    }
    with open(config.SENTIMENT_SCORES, "w") as f:
        json.dump(cache, f, indent=2, default=str)


def load_scores(asset_key: str) -> list[dict] | None:
    """Load cached scores if available."""
    if not os.path.exists(config.SENTIMENT_SCORES):
        return None
    with open(config.SENTIMENT_SCORES, "r") as f:
        cache = json.load(f)
    entry = cache.get(asset_key)
    if entry:
        return entry["articles"]
    return None


if __name__ == "__main__":
    test_headlines = [
        "Fed signals aggressive rate cuts boosting market confidence",
        "Gold prices surge amid global uncertainty and inflation fears",
        "S&P 500 drops sharply as recession fears mount",
        "Euro strengthens against dollar on positive EU economic data",
        "Markets tumble as trade war escalates further",
    ]
    scores = analyze_headlines(test_headlines)
    for s in scores:
        label = get_sentiment_label(s["score"])
        print(f"  [{s['score']:+.3f}] [{label:20s}] {s['headline']}")
