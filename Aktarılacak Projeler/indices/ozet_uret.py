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
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
