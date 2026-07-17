#!/usr/bin/env python3
"""Canli ozet — reer_analysis_data.csv'den, internetsiz."""
import json, os
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(BASE, "reer_analysis_data.csv"), parse_dates=["Dönem"])
s = df.dropna(subset=["Deviation_10Y_Pct"]).iloc[-1]
ozet = {
    "_tarih": s["Dönem"].strftime("%m.%Y"),
    "donem": s["Dönem"].strftime("%B %Y").replace("January","Ocak").replace("February","Şubat").replace("March","Mart").replace("April","Nisan").replace("May","Mayıs").replace("June","Haziran").replace("July","Temmuz").replace("August","Ağustos").replace("September","Eylül").replace("October","Ekim").replace("November","Kasım").replace("December","Aralık"),
    "redk": round(float(s["Composite_REER"]), 1),
    "sapma10": round(float(s["Deviation_10Y_Pct"]), 1),
    "sapma5": round(float(s["Deviation_5Y_Pct"]), 1),
    "ppi10": round(float(s["PPI_Deviation_10Y_Pct"]), 1),
    "cpi10": round(float(s["CPI_Deviation_10Y_Pct"]), 1),
}
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
