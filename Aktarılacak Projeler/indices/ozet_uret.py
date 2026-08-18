#!/usr/bin/env python3
"""Canli ozet — index_history.json + sentiment_scores.json'dan, internetsiz."""
import json, os
BASE = os.path.dirname(os.path.abspath(__file__))
h = json.load(open(os.path.join(BASE, "data", "index_history.json")))
son = h[-1]
ozet = {
    "_tarih": son["timestamp"][:16].replace("T", " ") + " UTC",
    "snapshot_sayisi": len(h),
    "varlik_sayisi": len(son.get("indices", {})),
}
try:
    sk = json.load(open(os.path.join(BASE, "data", "sentiment_scores.json")))
    ozet["makale_toplam"] = sum(len(v.get("articles", [])) for v in sk.values())
except Exception:
    pass
rej = son.get("regime")
if rej:
    ozet.update({"rejim": rej.get("label"), "spread": rej.get("basket_spread"),
                 "ort_korelasyon": rej.get("avg_correlation"), "pc1": rej.get("pc1_share")})

# ── Sayfa metnindeki uçlar ve makale sayıları: son snapshot'tan, elle yazılmaz ──
AD_TR = {"EURUSD": "EUR/USD", "USDJPY": "USD/JPY", "USDCHF": "USD/CHF", "GBPUSD": "GBP/USD",
         "AUDUSD": "AUD/USD", "NZDUSD": "NZD/USD", "USDCAD": "USD/CAD", "USDNOK": "USD/NOK",
         "USDSEK": "USD/SEK", "XAUUSD": "altın", "XAGUSD": "gümüş", "SPX": "S&P 500",
         "UST2Y": "ABD 2Y", "UST10Y": "ABD 10Y", "BIST100": "BIST 100"}
KAT_TR = {"Extremely Bullish": "Aşırı Alıcı", "Bullish": "Alıcı", "Neutral": "Nötr",
          "Bearish": "Satıcı", "Extremely Bearish": "Aşırı Satıcı"}
ind = son.get("indices", {})
# Grafik hover'ıyla AYNI tanım: yalnız "score" alanı olan (skorlanmış) makaleler
try:
    makale = {k: sum(1 for m in v.get("articles", []) if "score" in m) for k, v in sk.items()}
except Exception:
    makale = {}
sirali = sorted(((k, v["value"], v.get("category", "")) for k, v in ind.items()
                 if isinstance(v, dict) and v.get("value") is not None), key=lambda t: t[1])
if len(sirali) >= 4:
    for etiket, (k, v, kat) in zip(("ust1", "ust2"), (sirali[-1], sirali[-2])):
        ozet.update({f"{etiket}_ad": AD_TR.get(k, k), f"{etiket}_deger": round(v, 2),
                     f"{etiket}_kat": KAT_TR.get(kat, kat), f"{etiket}_makale": makale.get(k)})
    for etiket, (k, v, kat) in zip(("alt1", "alt2"), (sirali[0], sirali[1])):
        ozet.update({f"{etiket}_ad": AD_TR.get(k, k), f"{etiket}_deger": round(v, 2),
                     f"{etiket}_kat": KAT_TR.get(kat, kat), f"{etiket}_makale": makale.get(k)})
    # En düşük varlığın bir önceki snapshot'taki değeri (koşudan koşuya dönüş örneği)
    k0 = sirali[0][0]
    if len(h) >= 2 and k0 in h[-2].get("indices", {}):
        ozet["alt1_onceki_deger"] = round(h[-2]["indices"][k0]["value"], 2)
        ozet["alt1_onceki_tarih"] = ".".join(reversed(h[-2]["timestamp"][:10].split("-")))
        ozet["alt1_donus_bp"] = int(round(abs(sirali[0][1] - h[-2]["indices"][k0]["value"]) * 100))
    # En az makaleli varlık: "kategori etiketi değil makale sayısı okunur" örneği
    if makale:
        az = min(ind, key=lambda k: makale.get(k, 10**9))
        ozet.update({"az_ad": AD_TR.get(az, az), "az_makale": makale.get(az),
                     "az_deger": round(ind[az]["value"], 2),
                     "az_kat": KAT_TR.get(ind[az].get("category", ""), ind[az].get("category", ""))})
        # Aynı varlığın bir önceki snapshot'taki değeri (örneklem gürültüsü örneği)
        if len(h) >= 2 and az in h[-2].get("indices", {}):
            ozet["az_onceki_deger"] = round(h[-2]["indices"][az]["value"], 2)
            ozet["az_onceki_tarih"] = h[-2]["timestamp"][:10]

# ── Grid search (optimizasyon) özeti: liderler, kalibrasyon tarihi, ufuk dağılımı ──
try:
    opt = json.load(open(os.path.join(BASE, "data", "optimized_params.json")))
    satir = [(k, v.get("rolling_mean_5d") if v.get("best_horizon") == "5d" else v.get("rolling_mean_1d"),
              v.get("best_horizon"), v.get("timestamp", "")) for k, v in opt.items() if isinstance(v, dict) and "params" in v]
    satir = [t for t in satir if t[1] is not None]
    if satir:
        lider = sorted(satir, key=lambda t: t[1], reverse=True)[:3]
        for i, (k, r, hz, _) in enumerate(lider, start=1):
            ozet[f"opt{i}_ad"] = AD_TR.get(k, k); ozet[f"opt{i}_kor"] = round(float(r), 2)
        ts = max(t[3] for t in satir)[:10]
        ozet["opt_kalibrasyon"] = ".".join(reversed(ts.split("-"))) if ts else None
        ozet["opt_varlik"] = len(satir)
        ozet["opt_5g"] = sum(1 for t in satir if t[2] == "5d")
        ozet["opt_istisna"] = ", ".join(AD_TR.get(t[0], t[0]) for t in satir if t[2] != "5d") or "—"
except Exception as e:
    print(f"optimized_params okunamadı: {e}")

# ── Rejim/korelasyon panellerinin veri sonu (önbellek ucu): web_cikti.py sidecar'ı ──
try:
    ro = json.load(open(os.path.join(BASE, "cikti", "rejim_ozet.json")))
    if ro.get("as_of"):
        ozet["veri_sonu"] = ".".join(reversed(ro["as_of"].split("-")))
    if ro.get("n_assets"):
        ozet["rejim_varlik"] = ro["n_assets"]
except Exception:
    pass
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
