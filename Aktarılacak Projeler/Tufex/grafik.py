#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TÜFEX defteri — dört Plotly grafiği. CDN'li, ev stiline sonra çevrilir."""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from hesap import hesapla, VADELER

BURASI = Path(__file__).resolve().parent
CFG = {"displayModeBar": False, "responsive": True}
KIRMIZI, YESIL, GRI, ALTIN = "#8e1f2f", "#1d5c5c", "#8a8578", "#9a7327"


def yaz(fig, ad):
    # Sabit div kimliği: Plotly rastgele id üretiyor ve veri değişmese de HTML her
    # koşuda değişip commit üretiyordu (01.09: bir günde beş boş commit).
    fig.write_html(BURASI / ad, include_plotlyjs="cdn", config=CFG, div_id=ad.replace(".html", ""))
    print(" ", ad)


def main():
    d, mevsim, ozet = hesapla()

    # 01 — Başabaş vs anket, 2y
    f = go.Figure()
    f.add_trace(go.Scatter(x=d.index, y=d["be_2y"], name="2y başabaş (piyasa)",
                           line=dict(color=KIRMIZI, width=1.6)))
    f.add_trace(go.Scatter(x=d.index, y=d["pka_ort_2y"], name="Anket, 2y ufka eşlenmiş ortalama",
                           line=dict(color=YESIL, width=1.6)))
    f.add_trace(go.Scatter(x=d.index, y=d["be_7y"], name="7y başabaş",
                           line=dict(color=KIRMIZI, width=1.2, dash="dot")))
    f.add_trace(go.Scatter(x=d.index, y=d["pka_ort_7y"], name="Anket, 7y ufka eşlenmiş",
                           line=dict(color=YESIL, width=1.2, dash="dot")))
    f.update_layout(title="Piyasanın fiyatladığı enflasyon ile anketin beklediği (%)",
                    yaxis_title="%")
    yaz(f, "basabas_anket.html")

    # 02 — Risk primi: bugünkü vade yapısı + tarihçe
    f = go.Figure()
    kesit = [ozet.get(f"prim_{v}") for v in VADELER]
    f.add_trace(go.Bar(x=list(VADELER), y=kesit, name="Bugünkü kesit",
                       marker_color=KIRMIZI))
    f.update_layout(title="Enflasyon risk primi vade yapısı — başabaş eksi anket (puan)",
                    yaxis_title="puan")
    yaz(f, "prim_kesit.html")

    f = go.Figure()
    for v, renk, cizgi in (("2y", KIRMIZI, None), ("3y", ALTIN, None), ("7y", YESIL, "dot")):
        f.add_trace(go.Scatter(x=d.index, y=d[f"prim_{v}"], name=f"{v} prim",
                               line=dict(color=renk, width=1.4, dash=cizgi)))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="Risk priminin tarihçesi (puan)", yaxis_title="puan")
    yaz(f, "prim_tarihce.html")

    # 03 — Reel getiri tarihçesi
    f = go.Figure()
    for v, renk, cizgi in (("1y", ALTIN, "dot"), ("2y", KIRMIZI, None), ("7y", YESIL, None)):
        f.add_trace(go.Scatter(x=d.index, y=d[f"r{v}"], name=f"{v} reel",
                               line=dict(color=renk, width=1.4, dash=cizgi)))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="TÜFEX reel getirileri (%)", yaxis_title="%")
    yaz(f, "reel_tarihce.html")

    # 04 — Mevsimsel desen
    aylar = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
    f = go.Figure(go.Bar(
        x=aylar, y=mevsim["mean"], marker_color=[KIRMIZI if v > 0 else YESIL for v in mevsim["mean"]],
        error_y=dict(type="data", array=mevsim["std"], color=GRI, thickness=1)))
    f.add_hline(y=0, line=dict(color=GRI, width=1))
    f.update_layout(title=f"Aylık TÜFE'nin takvim deseni — ham eksi arındırılmış, son {int(mevsim['count'].max()//1)} gözlemli aylar (puan)",
                    yaxis_title="puan", showlegend=False)
    yaz(f, "mevsim.html")


if __name__ == "__main__":
    main()
