#!/usr/bin/env python3
"""Canli ozet (ozet.json) — gunluk.csv + haftalik_rezerv.csv'den, internetsiz."""
import json, os
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
g = pd.read_csv(os.path.join(BASE, "gunluk.csv"), parse_dates=["Tarih"])
h = pd.read_csv(os.path.join(BASE, "haftalik_rezerv.csv"), parse_dates=["Tarih"])
gs, hs = g.iloc[-1], h.iloc[-1]
ozet = {
    "_tarih": gs["Tarih"].strftime("%d.%m.%Y"),
    "g_tarih": gs["Tarih"].strftime("%d.%m.%Y"),
    "g_net": round(float(gs["net_rezerv_usd"]), 1),
    "g_swap_haric": round(float(gs["swap_haric_net_rezerv_usd"]), 1),
    "g_kur": round(float(gs["usdtry"]), 2),
    "h_tarih": hs["Tarih"].strftime("%d.%m.%Y"),
    "h_brut": round(float(hs["brut_rezerv_usd"]), 1),
    "h_net": round(float(hs["net_rezerv_usd"]), 1),
    "h_swap_haric": round(float(g[g["Tarih"] == hs["Tarih"]]["swap_haric_net_rezerv_usd"].iloc[-1])
                          if (g["Tarih"] == hs["Tarih"]).any() else float(gs["swap_haric_net_rezerv_usd"]), 1),
}
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
