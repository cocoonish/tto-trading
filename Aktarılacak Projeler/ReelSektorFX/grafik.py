#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reel sektör FX — üç grafik; veri yoksa yer tutucu HTML üretir."""
from __future__ import annotations

from pathlib import Path

from hesap import hesapla

BURASI = Path(__file__).resolve().parent
CFG = {"displayModeBar": False, "responsive": True}
KIRMIZI, YESIL, GRI = "#8e1f2f", "#1d5c5c", "#8a8578"
DOSYALAR = ("pozisyon.html", "bilesim.html", "kisa_vade.html")

YER_TUTUCU = """<!doctype html><html lang="tr"><head><meta charset="utf-8">
<style>body{{font-family:Georgia,serif;background:#f5f0e6;color:rgba(33,27,18,.72);
display:flex;align-items:center;justify-content:center;height:96vh;margin:0}}
div{{max-width:34rem;text-align:center;line-height:1.6}}</style></head><body><div>
<strong>{baslik}</strong><br>Bu hat ilk veri çekimini bekliyor. EVDS koşusu
tamamlandığında grafik burada kendiliğinden görünecek; ölçülmemiş veri yerine
taslak grafik basılmaz.</div></body></html>"""


def main():
    d, ozet = hesapla()
    if d is None:
        for ad in DOSYALAR:
            (BURASI / ad).write_text(
                YER_TUTUCU.format(baslik=ad.replace(".html", "")), encoding="utf-8")
        print("veri yok — yer tutucular yazıldı")
        return

    import plotly.graph_objects as go
    def yaz(fig, ad):
        # Sabit div kimliği: Plotly rastgele id üretiyor ve veri değişmese de HTML her
    # koşuda değişip commit üretiyordu (01.09: bir günde beş boş commit).
        fig.write_html(BURASI / ad, include_plotlyjs="cdn", config=CFG, div_id=ad.replace(".html", ""))
        print(" ", ad)

    mlr = d / 1000.0
    f = go.Figure()
    f.add_trace(go.Scatter(x=mlr.index, y=mlr["net_pozisyon"], name="Net pozisyon",
                           line=dict(color=KIRMIZI, width=1.8)))
    if "kv_net" in mlr:
        f.add_trace(go.Scatter(x=mlr.index, y=mlr["kv_net"], name="Kısa vadeli net",
                               line=dict(color=YESIL, width=1.5)))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="Finansal kesim dışı firmaların net döviz pozisyonu (mlr USD)",
                    yaxis_title="mlr USD")
    yaz(f, "pozisyon.html")

    f = go.Figure()
    f.add_trace(go.Scatter(x=mlr.index, y=mlr["varlik_toplam"], name="Varlıklar",
                           line=dict(color=YESIL, width=1.5)))
    f.add_trace(go.Scatter(x=mlr.index, y=mlr["yukumluluk_toplam"], name="Yükümlülükler",
                           line=dict(color=KIRMIZI, width=1.5)))
    f.update_layout(title="Döviz varlık ve yükümlülükleri (mlr USD)", yaxis_title="mlr USD")
    yaz(f, "bilesim.html")

    f = go.Figure()
    if "kv_varlik" in mlr and "kv_yukumluluk" in mlr:
        f.add_trace(go.Scatter(x=mlr.index, y=mlr["kv_varlik"], name="KV varlık",
                               line=dict(color=YESIL, width=1.5)))
        f.add_trace(go.Scatter(x=mlr.index, y=mlr["kv_yukumluluk"], name="KV yükümlülük",
                               line=dict(color=KIRMIZI, width=1.5)))
    f.update_layout(title="Kısa vadeli varlık ve yükümlülükler (mlr USD)", yaxis_title="mlr USD")
    yaz(f, "kisa_vade.html")


if __name__ == "__main__":
    main()
