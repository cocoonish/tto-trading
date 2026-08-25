#!/usr/bin/env python3
"""Sayfa metni icin canli ozet metrikleri (ozet.json) — CSV ciktilarindan, internetsiz."""
import json, os
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
oku = lambda ad: pd.read_csv(os.path.join(BASE, ad), encoding="utf-8-sig")

ih = oku("hazine_ihale_verileri.csv")
hg = oku("hazine_hedef_gerceklesme.csv")
va = oku("hazine_vade_analizi.csv")
pl = oku("hazine_planlanan_ihaleler.csv")
td = oku("hazine_tahmin_dogrulama.csv")

ih["t"] = pd.to_datetime(ih["İhale Tarihi"], dayfirst=True)
ih["ay"] = ih["t"].dt.to_period("M")
son_ay = ih["ay"].max()

def agirlikli_maliyet(g):
    g = g[~g["Senet Tanımı"].str.contains("TÜFE", na=False)].dropna(
        subset=["Ortalama Yıllık Bileşik(Gerçekleşme)", "Toplam(Gerçekleşme)"])
    if g.empty: return None
    return float((g["Ortalama Yıllık Bileşik(Gerçekleşme)"] * g["Toplam(Gerçekleşme)"]).sum()
                 / g["Toplam(Gerçekleşme)"].sum())

gercek = hg[pd.to_numeric(hg["Gerçekleşen Borçlanma (Milyar TL)"], errors="coerce") > 0]
son12 = ih[ih["ay"] > son_ay - 12]
sa = ih[ih["ay"] == son_ay]

td["t"] = pd.to_datetime(td["İhale Tarihi"], dayfirst=True)
td12 = td[td["t"] > td["t"].max() - pd.DateOffset(months=12)]
td["ayp"] = td["t"].dt.to_period("M")
aylik = td.groupby("ayp")[["Gerçek Gerçekleşme (Milyon TL)", "Tahmin-Ham (Milyon TL)"]].sum()
aylik = aylik[aylik["Gerçek Gerçekleşme (Milyon TL)"] > 0]
aylik_ham_mape = float((abs(aylik["Tahmin-Ham (Milyon TL)"] / aylik["Gerçek Gerçekleşme (Milyon TL)"] - 1)).mean() * 100)

pl_ihale = pl[pl["Yöntem"].astype(str).str.contains("hale", na=False)]
plt = pd.to_numeric(pl_ihale["Tahmini Gerçekleşme (Milyon TL)"], errors="coerce")

ozet = {
    "_tarih": ih["t"].max().strftime("%d.%m.%Y"),
    "n_ihale": int(len(ih)),
    "toplam_mlr": round(float(ih["Toplam(Gerçekleşme)"].sum()) / 1000, 1),
    "gerceklesme_ort": round(float(pd.to_numeric(gercek["Gerçekleşme Oranı (%)"], errors="coerce").mean()), 1),
    "n_ay": int(len(gercek)),
    "b2c_son": round(float(sa["Toplam(Teklif)"].sum() / sa["Toplam(Gerçekleşme)"].sum()), 2),
    "b2c_12ay": round(float(son12.groupby("ay").apply(
        lambda g: g["Toplam(Teklif)"].sum() / g["Toplam(Gerçekleşme)"].sum()).mean()), 2),
    "kabul_son": round(float(sa["Toplam(Gerçekleşme)"].sum() / sa["Toplam(Teklif)"].sum() * 100), 1),
    "kabul_tum": round(float(ih["Toplam(Gerçekleşme)"].sum() / ih["Toplam(Teklif)"].sum() * 100), 1),
    "maliyet_son": round(agirlikli_maliyet(sa), 2),
    "wam_son": round(float(va["Ağırlıklı Ortalama Vade (Yıl)"].iloc[-1]), 2),
    "wam_3ay": round(float(va["3 Aylık Ağırlıklı Ortalama Vade"].iloc[-1]), 2),
    "plan_adet": int(len(pl)),
    "plan_ihale_adet": int(len(pl_ihale)),
    "plan_toplam_mlr": round(float(plt.sum()) / 1000, 1),
    "plan_bas": str(pl["İhale Tarihi"].iloc[0]),
    "plan_son": str(pl["İhale Tarihi"].iloc[-1]),
    "backtest_n": int(len(td)),
    "medyan_sapma": round(float(abs(pd.to_numeric(td["Tutar Sapma % (düzeltilmiş)"], errors="coerce")).median()), 1),
    "son12_mape": round(float(abs(pd.to_numeric(td12["Tutar Sapma % (düzeltilmiş)"], errors="coerce")).mean()), 1),
    "b2c_mape": round(float(abs(pd.to_numeric(td["B2C Sapma %"], errors="coerce")).mean()), 1),
    "aylik_ham_mape": round(aylik_ham_mape, 1),
}
yol = os.path.join(BASE, "ozet.json")
json.dump(ozet, open(yol, "w"), ensure_ascii=False, indent=1)
print("yazildi:", yol); print(json.dumps(ozet, ensure_ascii=False))
