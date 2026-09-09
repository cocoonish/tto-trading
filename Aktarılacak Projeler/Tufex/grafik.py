#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TÜFEX defteri — beş Plotly grafiği. CDN'li, ev stiline sonra çevrilir.

Figür adları `hesap.SEKILLER`den gelir: şekil saat defteri o listeden yazılır
ve burada o listede olmayan bir dosya yazılamaz — defterde girdisi olmayan
figür sayfada hattın ana saatiyle damgalanır, aylık bir figür için o damga
yalan söyler (09.09.2026'da mevsim figürü günlük saat taşıyordu).
"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from hesap import hesapla, SEKILLER, VADELER

BURASI = Path(__file__).resolve().parent
CFG = {"displayModeBar": False, "responsive": True}
KIRMIZI, YESIL, GRI, ALTIN = "#8e1f2f", "#1d5c5c", "#8a8578", "#9a7327"


def figurler(d, mevsim, ozet) -> dict[str, go.Figure]:
    """Dosya adı → figür. Yazmaz; duman sınaması metinleri buradan okur."""
    f_ = {}
    anket_ad = ozet.get("pka_ay_ad", "—")

    # 01 — Başabaş vs anket, 2y. Anket izinin adı yürürlükteki anketin ayını
    # taşır: iz günlüğe basamak olarak yayılmıştır ve bugüne kadar uzanır ama
    # bilgisi o ayın anketidir; sayfadaki damga ile aynı anahtardan gelir.
    f = go.Figure()
    f.add_trace(go.Scatter(x=d.index, y=d["be_2y"], name="2y başabaş (piyasa)",
                           line=dict(color=KIRMIZI, width=1.6)))
    f.add_trace(go.Scatter(x=d.index, y=d["pka_ort_2y"],
                           name=f"Anket ({anket_ad}), 2y ufka eşlenmiş ortalama",
                           line=dict(color=YESIL, width=1.6)))
    f.add_trace(go.Scatter(x=d.index, y=d["be_7y"], name="7y başabaş",
                           line=dict(color=KIRMIZI, width=1.2, dash="dot")))
    f.add_trace(go.Scatter(x=d.index, y=d["pka_ort_7y"],
                           name=f"Anket ({anket_ad}), 7y ufka eşlenmiş",
                           line=dict(color=YESIL, width=1.2, dash="dot")))
    f.update_layout(title="Piyasanın fiyatladığı enflasyon ile anketin beklediği (%)",
                    yaxis_title="%")
    f_["basabas_anket.html"] = f

    # 02 — Risk primi: bugünkü vade yapısı + tarihçe
    f = go.Figure()
    kesit = [ozet.get(f"prim_{v}") for v in VADELER]
    f.add_trace(go.Bar(x=list(VADELER), y=kesit, name="Bugünkü kesit",
                       marker_color=KIRMIZI))
    f.update_layout(title="Enflasyon risk primi vade yapısı — başabaş eksi anket (puan)",
                    yaxis_title="puan")
    f_["prim_kesit.html"] = f

    f = go.Figure()
    for v, renk, cizgi in (("2y", KIRMIZI, None), ("3y", ALTIN, None), ("7y", YESIL, "dot")):
        f.add_trace(go.Scatter(x=d.index, y=d[f"prim_{v}"], name=f"{v} prim",
                               line=dict(color=renk, width=1.4, dash=cizgi)))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="Risk priminin tarihçesi (puan)", yaxis_title="puan")
    f_["prim_tarihce.html"] = f

    # 03 — Reel getiri tarihçesi
    f = go.Figure()
    for v, renk, cizgi in (("1y", ALTIN, "dot"), ("2y", KIRMIZI, None), ("7y", YESIL, None)):
        f.add_trace(go.Scatter(x=d.index, y=d[f"r{v}"], name=f"{v} reel",
                               line=dict(color=renk, width=1.4, dash=cizgi)))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="TÜFEX reel getirileri (%)", yaxis_title="%")
    f_["reel_tarihce.html"] = f

    # 04 — Mevsimsel desen
    aylar = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
    f = go.Figure(go.Bar(
        x=aylar, y=mevsim["mean"], marker_color=[KIRMIZI if v > 0 else YESIL for v in mevsim["mean"]],
        error_y=dict(type="data", array=mevsim["std"], color=GRI, thickness=1)))
    f.add_hline(y=0, line=dict(color=GRI, width=1))
    f.update_layout(title=f"Aylık TÜFE'nin takvim deseni — ham eksi arındırılmış, son {int(mevsim['count'].max()//1)} gözlemli aylar (puan)",
                    yaxis_title="puan", showlegend=False)
    f_["mevsim.html"] = f
    return f_


def yaz(fig, ad):
    if ad not in SEKILLER:
        raise KeyError(f"{ad} şekil saat defterinde yok — önce hesap.SEKILLER'e ekle")
    # Sabit div kimliği: Plotly rastgele id üretiyor ve veri değişmese de HTML her
    # koşuda değişip commit üretiyordu (01.09: bir günde beş boş commit).
    fig.write_html(BURASI / ad, include_plotlyjs="cdn", config=CFG, div_id=ad.replace(".html", ""))
    print(" ", ad)


def main():
    d, mevsim, ozet = hesapla()
    for ad, fig in figurler(d, mevsim, ozet).items():
        yaz(fig, ad)


if __name__ == "__main__":
    main()
