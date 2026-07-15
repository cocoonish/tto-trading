"""News fetcher: Google News RSS with date filtering (historical + real-time)."""

import json
import os
import re
import time
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

import feedparser

import config


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation for dedup."""
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _parse_date(entry) -> str:
    """Return ISO-format UTC datetime string from a feedparser entry."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        from calendar import timegm
        ts = timegm(entry.published_parsed)
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# Google News RSS — with date range support
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_news(query: str, max_results: int = 100,
               after: str = None, before: str = None) -> list[dict]:
    """
    Fetch headlines from Google News RSS.
    after/before: date strings like "2025-06-01" to filter by date range.
    """
    q = query
    if after:
        q += f" after:{after}"
    if before:
        q += f" before:{before}"

    url = (
        f"https://news.google.com/rss/search?"
        f"q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
    )
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:max_results]:
        source = ""
        if hasattr(entry, "source") and hasattr(entry.source, "title"):
            source = entry.source.title
        results.append({
            "title": entry.title,
            "published": _parse_date(entry),
            "link": entry.link,
            "source": source,
        })
    return results


def fetch_news_turkish(query: str, max_results: int = 100,
                       after: str = None, before: str = None) -> list[dict]:
    """Fetch headlines from Google News RSS with Turkish locale."""
    q = query
    if after:
        q += f" after:{after}"
    if before:
        q += f" before:{before}"
    url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=tr&gl=TR&ceid=TR:tr"
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:max_results]:
        source = ""
        if hasattr(entry, "source") and hasattr(entry.source, "title"):
            source = entry.source.title
        results.append({
            "title": entry.title,
            "published": _parse_date(entry),
            "link": entry.link,
            "source": source,
            "language": "tr",
        })
    return results


_translate_cache = {}

def _translate_title(title: str, source_lang: str = "tr") -> str:
    """Translate a title to English for FinBERT scoring. Cached."""
    if title in _translate_cache:
        return _translate_cache[title]
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source=source_lang, target="en").translate(title)
        _translate_cache[title] = translated
        return translated
    except Exception:
        _translate_cache[title] = title
        return title


def fetch_finviz_news(ticker: str = None, max_results: int = 50) -> list[dict]:
    """Fetch news from Finviz RSS feed."""
    try:
        url = f"https://finviz.com/news_export.ashx?t={ticker}" if ticker else "https://finviz.com/news_export.ashx"
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:max_results]:
            results.append({
                "title": entry.title,
                "published": _parse_date(entry),
                "link": entry.link,
                "source": "Finviz",
                "data_source": "finviz",
            })
        return results
    except Exception:
        return []


def fetch_reddit_posts(subreddit: str, query: str, limit: int = 25,
                       min_score: int = 5) -> list[dict]:
    """Fetch Reddit posts. Requires REDDIT_CLIENT_ID/SECRET env vars. Skips if not set."""
    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    if not client_id:
        return []  # Skip if no credentials
    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
            user_agent="MarketTranslator/1.0",
        )
        results = []
        for post in reddit.subreddit(subreddit).search(query, sort="relevance",
                                                        time_filter="week", limit=limit):
            if post.score < min_score:
                continue
            results.append({
                "title": post.title,
                "published": datetime.fromtimestamp(post.created_utc, tz=timezone.utc).isoformat(),
                "link": f"https://reddit.com{post.permalink}",
                "source": f"r/{subreddit}",
                "data_source": "reddit",
                "upvotes": post.score,
            })
        return results
    except Exception:
        return []


def fetch_twitter_posts(cashtag: str, limit: int = 20) -> list[dict]:
    """Fetch tweets via ntscraper. Disabled by default (unreliable). Set ENABLE_TWITTER=1 to enable."""
    if not os.environ.get("ENABLE_TWITTER", ""):
        return []  # Disabled by default
    try:
        from ntscraper import Nitter
        scraper = Nitter()
        tweets = scraper.get_tweets(cashtag, mode="term", number=limit)
        results = []
        for tweet in tweets.get("tweets", []):
            results.append({
                "title": tweet.get("text", "")[:512],
                "published": tweet.get("date", datetime.now(timezone.utc).isoformat()),
                "link": tweet.get("link", ""),
                "source": "Twitter/X",
                "data_source": "twitter",
            })
        return results
    except Exception:
        return []


def fetch_weekly_news(asset_key: str, week_start: datetime,
                      week_end: datetime) -> list[dict]:
    """Fetch & deduplicate headlines for one asset for one week. Supports Turkish."""
    asset_cfg = config.ASSETS[asset_key]
    lang = asset_cfg.get("language", "en")
    fetch_fn = fetch_news_turkish if lang == "tr" else fetch_news

    after_str = week_start.strftime("%Y-%m-%d")
    before_str = (week_end + timedelta(days=1)).strftime("%Y-%m-%d")

    all_articles = []
    seen = set()

    # For non-English assets: use English queries FIRST (fast, no translation needed)
    # Then optionally add translated Turkish queries
    if lang != "en":
        # English queries first (fast)
        for query in asset_cfg.get("queries_en", []):
            articles = fetch_news(query, after=after_str, before=before_str)
            for article in articles:
                key = _normalize(article["title"])
                if key and key not in seen:
                    seen.add(key)
                    article["asset"] = asset_key
                    article["data_source"] = "google_news"
                    article["source_weight"] = config.SOURCE_WEIGHTS.get("google_news", 1.0)
                    all_articles.append(article)
            time.sleep(1)
        # Skip Turkish queries in historical fetch (translation too slow for batch)
    else:
        # English asset: fetch normally
        for query in asset_cfg["queries"]:
            articles = fetch_news(query, after=after_str, before=before_str)
            for article in articles:
                key = _normalize(article["title"])
                if key and key not in seen:
                    seen.add(key)
                    article["asset"] = asset_key
                    article["data_source"] = "google_news"
                    article["source_weight"] = config.SOURCE_WEIGHTS.get("google_news", 1.0)
                    all_articles.append(article)
            time.sleep(1)

    # English queries for English assets (if queries_en exists)
    if lang == "en":
        for query in asset_cfg.get("queries_en", []):
            articles = fetch_news(query, after=after_str, before=before_str)
            for article in articles:
                key = _normalize(article["title"])
                if key and key not in seen:
                    seen.add(key)
                    article["asset"] = asset_key
                    article["data_source"] = "google_news"
                    article["source_weight"] = config.SOURCE_WEIGHTS.get("google_news", 1.0)
                    all_articles.append(article)
            time.sleep(1)

    # Finviz (for real-time, not historical — skip in weekly historical fetch)
    # Reddit/Twitter only for real-time

    all_articles.sort(key=lambda x: x["published"], reverse=True)
    return all_articles


def _week_boundaries(ref_date: datetime) -> tuple[datetime, datetime]:
    """Return Monday 00:00 and Sunday 23:59:59 for the week containing ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


# ═══════════════════════════════════════════════════════════════════════════════
# Historical News — Week by week with permanent cache
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_historical_news(asset_key: str, weeks: int = 52,
                          progress_cb=None) -> dict[str, list[dict]]:
    """
    Fetch week-by-week historical news for the past N weeks.
    Uses permanent cache: historical weeks never re-fetched.
    Returns {week_end_date_iso: [articles]}.
    """
    cache = _load_historical_cache()
    asset_cache = cache.get(asset_key, {})
    result = {}
    now = datetime.now(timezone.utc)

    for i in range(weeks):
        ref = now - timedelta(weeks=i + 1)
        week_start, week_end = _week_boundaries(ref)
        week_key = week_end.strftime("%Y-%m-%d")

        # Use cache if available (past weeks are immutable)
        if week_key in asset_cache and asset_cache[week_key].get("articles"):
            result[week_key] = asset_cache[week_key]["articles"]
            if progress_cb:
                progress_cb(i + 1, weeks, cached=True)
            continue

        # Fetch from Google News RSS with date filter
        articles = fetch_weekly_news(asset_key, week_start, week_end)
        result[week_key] = articles

        # Cache permanently
        asset_cache[week_key] = {
            "articles": articles,
            "fetched_at": now.isoformat(),
            "n_articles": len(articles),
        }

        if progress_cb:
            progress_cb(i + 1, weeks, cached=False)

        print(f"  [{asset_key}] Week {week_key}: {len(articles)} articles", flush=True)

    # Save cache
    cache[asset_key] = asset_cache
    _save_historical_cache(cache)
    return result


# ── Historical Cache ───────────────────────────────────────────────────────────

def _load_historical_cache() -> dict:
    if os.path.exists(config.GDELT_CACHE):
        try:
            with open(config.GDELT_CACHE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_historical_cache(data: dict):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.GDELT_CACHE, "w") as f:
        json.dump(data, f, indent=1, default=str)


# ═══════════════════════════════════════════════════════════════════════════════
# Real-time (current week, no date filter)
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_all_news(asset_key: str) -> list[dict]:
    """Fetch & deduplicate from all sources: Google News + Finviz + Reddit + Twitter."""
    asset_cfg = config.ASSETS[asset_key]
    lang = asset_cfg.get("language", "en")
    fetch_fn = fetch_news_turkish if lang == "tr" else fetch_news

    all_articles = []
    seen = set()

    def _add(article, source_type="google_news", translate=False):
        key = _normalize(article["title"])
        if key and key not in seen:
            seen.add(key)
            article["asset"] = asset_key
            article["data_source"] = source_type
            article["source_weight"] = config.SOURCE_WEIGHTS.get(source_type, 1.0)
            if translate and lang != "en" and "title_original" not in article:
                article["title_original"] = article["title"]
                article["title"] = _translate_title(article["title"], lang)
            all_articles.append(article)

    # 1. For non-English assets: use English queries only for real-time (fast)
    #    Turkish queries + translation used only in historical fetch
    if lang != "en":
        for query in asset_cfg.get("queries_en", []):
            for a in fetch_news(query):
                _add(a, "google_news")
            time.sleep(1)
    else:
        for query in asset_cfg["queries"]:
            for a in fetch_news(query):
                _add(a, "google_news")
            time.sleep(1)

    # 3. Finviz RSS
    alt_cfg = config.ALTERNATIVE_SOURCES.get(asset_key, {})
    for ticker in alt_cfg.get("finviz_tickers", []):
        for a in fetch_finviz_news(ticker):
            _add(a, "finviz")

    # 4. Reddit (if credentials available)
    for sub in alt_cfg.get("reddit_subs", []):
        for query in alt_cfg.get("reddit_queries", [asset_key]):
            for a in fetch_reddit_posts(sub, query):
                _add(a, "reddit")

    # 5. Twitter (stretch, graceful degradation)
    for cashtag in alt_cfg.get("twitter_cashtags", []):
        for a in fetch_twitter_posts(cashtag):
            _add(a, "twitter")

    all_articles.sort(key=lambda x: x["published"], reverse=True)
    return all_articles


def _load_cache() -> dict:
    if os.path.exists(config.NEWS_CACHE):
        with open(config.NEWS_CACHE, "r") as f:
            return json.load(f)
    return {}


def _save_cache(data: dict):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.NEWS_CACHE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_all_news_cached(asset_key: str) -> list[dict]:
    """Return cached Google News if fresh, otherwise fetch and cache."""
    cache = _load_cache()
    now = datetime.now(timezone.utc).timestamp()
    cache_entry = cache.get(asset_key, {})
    cached_ts = cache_entry.get("timestamp", 0)
    if now - cached_ts < config.CACHE_TTL_SECONDS and cache_entry.get("articles"):
        return cache_entry["articles"]
    articles = fetch_all_news(asset_key)
    cache[asset_key] = {"timestamp": now, "articles": articles}
    _save_cache(cache)
    return articles


if __name__ == "__main__":
    # Test historical fetch for 3 weeks
    print("Testing historical fetch (3 weeks)...")
    for asset in list(config.ASSETS.keys()):
        weekly = fetch_historical_news(asset, weeks=3)
        total = sum(len(v) for v in weekly.values())
        print(f"  {asset}: {len(weekly)} weeks, {total} articles")
