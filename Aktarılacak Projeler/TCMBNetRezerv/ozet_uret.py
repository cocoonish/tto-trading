#!/usr/bin/env python3
"""Canli ozet (ozet.json) — gunluk.csv + haftalik_rezerv.csv'den, internetsiz."""
import json, os
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
g = pd.read_csv(os.path.join(BASE, "gunluk.csv"), parse_dates=["Tarih"])
h = pd.read_csv(os.path.join(BASE, "haftalik_rezerv.csv"), parse_dates=["Tarih"])
gs, hs = g.iloc[-1], h.iloc[-1]
# Swap hariç seri, son IRFCL gözleminden ~3 hafta sonra bilerek NaN'a düşüyor
# (sahte uzatma yok) — özet için son GEÇERLİ noktalar alınır.
gsh = g.dropna(subset=["swap_haric_net_rezerv_usd"]).iloc[-1]
hsh = h.dropna(subset=["swap_haric_net_rezerv_usd"]).iloc[-1]
# Swap düzeltmesinin (II.2+II.3) en son YAYIMLANDIĞI gün
gozlem = g[g["swap_gozlem"].astype(str).str.lower().isin(["true", "1"])]
# Son 20 iş gününde mutlak değerce en büyük üç günlük hareket (net rezerv, mlr USD).
# Sayfadaki "öne çıkan hareketler" cümlesi bu üç çiftten okunur — elle yazılmaz.
PENCERE = 20
son = g.dropna(subset=["net_rezerv_usd"]).tail(PENCERE + 1).copy()
son["d"] = son["net_rezerv_usd"].diff()
uclar = son.dropna(subset=["d"]).reindex(
    son.dropna(subset=["d"])["d"].abs().sort_values(ascending=False).index
).head(3).sort_values("Tarih")
uc_alanlar = {}
for i, (_, r) in enumerate(uclar.iterrows(), start=1):
    uc_alanlar[f"u{i}_tarih"] = r["Tarih"].strftime("%d.%m")
    uc_alanlar[f"u{i}_delta"] = round(float(r["d"]), 1)
ozet = {
    "_tarih": gs["Tarih"].strftime("%d.%m.%Y"),
    "pencere_gun": PENCERE,
    **uc_alanlar,
    # Grafikteki gerçek IRFCL gözlem işaretçisi sayısı (günlük seri penceresinde)
    "irfcl_nokta": int(len(gozlem)),
    "g_tarih": gs["Tarih"].strftime("%d.%m.%Y"),
    "g_net": round(float(gs["net_rezerv_usd"]), 1),
    "g_swap_haric_tarih": gsh["Tarih"].strftime("%d.%m.%Y"),
    "g_swap_haric": round(float(gsh["swap_haric_net_rezerv_usd"]), 1),
    "g_kur": round(float(gs["usdtry"]), 2),
    "h_tarih": hs["Tarih"].strftime("%d.%m.%Y"),
    "h_brut": round(float(hs["brut_rezerv_usd"]), 1),
    "h_net": round(float(hs["net_rezerv_usd"]), 1),
    "h_swap_haric": round(float(hsh["swap_haric_net_rezerv_usd"]), 1),
    # Swap düzeltmesi artık tarihe göre değişen gerçek IRFCL verisi
    "swap_duzeltme": round(float(gsh["swap_duzeltme_usd"]), 1),
    "irfcl_tarih": (gozlem.iloc[-1]["Tarih"].strftime("%d.%m.%Y")
                    if len(gozlem) else "-"),
}
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
