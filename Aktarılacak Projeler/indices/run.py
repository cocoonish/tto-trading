#!/usr/bin/env python3
"""CLI entry point for the weekly sentiment index pipeline."""

import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import news_fetcher
import sentiment_analyzer
import index_builder
import price_fetcher
import correlation_optimizer


def main():
    parser = argparse.ArgumentParser(description="News Sentiment Index Builder (Weekly)")
    parser.add_argument("--fetch-history", action="store_true",
                        help="Fetch 52 weeks of GDELT historical news")
    parser.add_argument("--optimize", action="store_true",
                        help="Run weekly grid search optimization")
    parser.add_argument("--asset", choices=list(config.ASSETS.keys()),
                        help="Run for single asset")
    parser.add_argument("--output", choices=["json", "table"], default="table")
    args = parser.parse_args()

    os.makedirs(config.DATA_DIR, exist_ok=True)
    assets = [args.asset] if args.asset else list(config.ASSETS.keys())

    # Step 1: Fetch GDELT historical data (if requested)
    if args.fetch_history:
        print("=" * 60)
        print("STEP 1: Fetching GDELT Historical News (52 weeks)")
        print("=" * 60)
        for asset_key in assets:
            print(f"\n  {asset_key}:")
            weekly = news_fetcher.fetch_historical_news(asset_key, weeks=config.HISTORY_WEEKS)
            total = sum(len(v) for v in weekly.values())
            print(f"  Total: {len(weekly)} weeks, {total} articles")

        print("\n  Scoring all articles with FinBERT...")
        sentiment_analyzer.load_model()
        for asset_key in assets:
            cache = news_fetcher._load_historical_cache()
            asset_cache = cache.get(asset_key, {})
            scored = 0
            for week_key, entry in asset_cache.items():
                articles = entry.get("articles", [])
                if articles and "score" not in articles[0]:
                    sentiment_analyzer.analyze_articles(articles)
                    scored += len(articles)
            if scored:
                news_fetcher._save_historical_cache(cache)
                print(f"  {asset_key}: {scored} articles scored", flush=True)

    # Step 2: Real-time news (Google RSS)
    print("\n" + "=" * 60)
    print("STEP 2: Real-time News (Google RSS)")
    print("=" * 60)
    all_articles = {}
    for asset_key in assets:
        articles = news_fetcher.fetch_all_news_cached(asset_key)
        if articles and "score" not in articles[0]:
            articles = sentiment_analyzer.analyze_articles(articles)
            sentiment_analyzer.save_scores(asset_key, articles)
        all_articles[asset_key] = articles
        print(f"  {asset_key}: {len(articles)} articles")

    # Step 3: Build real-time indices
    print("\n" + "=" * 60)
    print("STEP 3: Real-time Sentiment Indices")
    print("=" * 60)
    opt_params = correlation_optimizer.load_optimized_params()
    indices = {}
    for asset_key in assets:
        params = opt_params.get(asset_key, config.DEFAULT_PARAMS.copy())
        idx = index_builder.build_index(all_articles[asset_key], params)
        indices[asset_key] = idx

    # Rejim ozeti: her kosuda index_history kaydina eklenir (rejim tarihcesi
    # ileride cizilebilsin). Agir hesap (gunluk duyarlilik matrisi) —
    # basarisiz olursa snapshot rejimsiz kaydedilir, pipeline durmaz.
    rejim_bilgi = None
    try:
        import web_cikti
        rejim_bilgi = web_cikti.rejim_ozeti()
        print(f"\n  Rejim: {rejim_bilgi['label']} "
              f"(spread {rejim_bilgi['basket_spread']:+.3f}, "
              f"ort. korelasyon {rejim_bilgi['avg_correlation']:+.3f}, "
              f"PC1 payi {rejim_bilgi['pc1_share']:.1%})")
    except Exception as exc:
        print(f"\n  UYARI: rejim hesaplanamadi: {exc}")

    index_builder.save_index_snapshot(indices, regime=rejim_bilgi)

    if args.output == "json":
        print(json.dumps(indices, indent=2, default=str))
    else:
        for asset_key, idx in indices.items():
            name = config.ASSETS[asset_key]["name"]
            print(f"\n  {name} ({asset_key})")
            print(f"    Index Value : {idx['value']:+.4f}")
            print(f"    Category    : {idx['category']}")
            print(f"    Articles    : {idx['n_articles']}")

    # Step 4: Dual optimization (if requested)
    if args.optimize:
        print("\n" + "=" * 60)
        print("STEP 4: Dual Optimization (1d + 5d return horizons)")
        print("=" * 60)

        if not os.path.exists(config.GDELT_CACHE):
            print("  ERROR: No cache found. Run with --fetch-history first.")
            return

        results = correlation_optimizer.optimize_all_dual()

        print("\n" + "=" * 70)
        print("DUAL OPTIMIZATION RESULTS")
        print("=" * 70)
        print(f"{'Asset':<10} {'1d Roll':>8} {'5d Roll':>8} {'Best':>5}")
        print("-" * 35)
        for asset_key, res in results.items():
            rm1 = res["rolling_mean_1d"]
            rm5 = res["rolling_mean_5d"]
            best = res["best_horizon"]
            print(f"  {asset_key:<10} {rm1:>8.4f} {rm5:>8.4f} {best:>5}")

    # Step 5: Prices
    print("\n" + "=" * 60)
    print("CURRENT PRICES")
    print("=" * 60)
    for asset_key in assets:
        info = price_fetcher.get_latest_price(asset_key)
        if info["price"]:
            name = config.ASSETS[asset_key]["name"]
            ret = info["return_1d"] * 100 if info["return_1d"] else 0
            print(f"  {name}: {info['price']:.4f} ({ret:+.2f}%)")

    # Step 6: Static web output (Plotly HTML for the site).
    # Rejim ozeti yukarida hesaplandiysa yeniden hesaplanmaz; agir adimlar
    # (rejim matrisi, yfinance sacilimi) web_cikti icinde try/except ile
    # opsiyoneldir — hata pipeline'i durdurmaz.
    try:
        import web_cikti
        yollar = web_cikti.uret(rejim=rejim_bilgi)
        print("\nWeb ciktisi yenilendi:")
        for yol in yollar:
            print(f"  {yol}")
    except Exception as exc:  # web ciktisi hatasi pipeline'i durdurmasin
        print(f"\nUYARI: web ciktisi uretilemedi: {exc}")

    print("\nDone. Run 'streamlit run dashboard.py' for the interactive dashboard.")


if __name__ == "__main__":
    main()
