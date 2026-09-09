#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Makroihtiyati iz — dört Plotly grafiği. CDN'li; ev stiline sonra çevrilir."""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from hesap import SEKILLER, hesapla

BURASI = Path(__file__).resolve().parent
CFG = {"displayModeBar": False, "responsive": True}
KIRMIZI, YESIL, GRI, ALTIN = "#8e1f2f", "#1d5c5c", "#8a8578", "#9a7327"


def yaz(fig, ad):
    # YAPISAL KİLİT: defterde olmayan figür yazılamaz. Şekil saat defteri
    # (hesap.SEKILLER) hangi figürün hangi bacağın saatini taşıdığını söyler;
    # deftere girmemiş bir figür sayfada hattın ANA saatiyle damgalanır ve
    # bayat bir bacak taze görünür (09.09.2026'da anket bacağında ölçüldü).
    if ad not in SEKILLER:
        raise KeyError(f"{ad} şekil saat defterinde yok (hesap.SEKILLER)")
    # Sabit div kimliği: Plotly rastgele id üretiyor ve veri değişmese de HTML her
    # koşuda değişip commit üretiyordu (01.09: bir günde beş boş commit).
    fig.write_html(BURASI / ad, include_plotlyjs="cdn", config=CFG, div_id=ad.replace(".html", ""))
    print(" ", ad)


def main():
    h, f, b, ozet = hesapla()
    h22 = h[h.index >= "2022-01-01"]
    f19 = f[f.index >= "2019-01-01"]

    # 01 — Kanal bazlı ayrışma
    fig = go.Figure()
    for kolon, ad, renk, cizgi in (
        ("g_tuketici_13y", "Tüketici", KIRMIZI, None),
        ("g_ticari_13y", "Ticari", YESIL, None),
        ("g_kobi_13y", "KOBİ", ALTIN, None),
        ("g_ar_13y", "Toplam (kur arındırılmış)", GRI, "dot"),
    ):
        fig.add_trace(go.Scatter(x=h22.index, y=h22[kolon], name=ad,
                                 line=dict(color=renk, width=1.5, dash=cizgi)))
    fig.update_layout(title="Kredi büyümesinde kanal ayrışması — 13 hafta yıllıklandırılmış (%)",
                      yaxis_title="%")
    yaz(fig, "ayrisma.html")

    # 02 — Kısıt kaçağı
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=h22.index, y=h22["kacak_bkk"],
                             name="Bireysel kart − tüketici kredisi",
                             line=dict(color=KIRMIZI, width=1.6)))
    fig.add_trace(go.Scatter(x=h22.index, y=h22["kacak_kurumsal_kart"],
                             name="Kurumsal kart − ticari kredi",
                             line=dict(color=YESIL, width=1.6)))
    fig.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    fig.update_layout(title="Kısıt kaçağı — kapsam dışı kanalın kapsanandan büyüme farkı (puan)",
                      yaxis_title="puan")
    yaz(fig, "kacak.html")

    # 03 — Fiyat izi: faiz makasları
    fig = go.Figure()
    for kolon, ad, renk, cizgi in (
        ("makas_ihtiyac", "İhtiyaç kredisi − politika", KIRMIZI, None),
        ("makas_ticari_tl", "Ticari kredi − politika", YESIL, None),
        ("makas_mevduat", "TL mevduat − politika", ALTIN, None),
    ):
        fig.add_trace(go.Scatter(x=f19.index, y=f19[kolon], name=ad,
                                 line=dict(color=renk, width=1.5, dash=cizgi)))
    fig.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    fig.update_layout(title="Kısıtın gölge fiyatı — akım faizlerin politika faizinden makası (puan)",
                      yaxis_title="puan")
    yaz(fig, "makas.html")

    # 04 — BKEA: bankaların kendi beyanı
    fig = go.Figure()
    b13 = b[b.index >= "2013-01-01"]
    for kolon, ad, renk, cizgi in (
        ("bkea_std_isletme", "İşletme kredisi standartları", KIRMIZI, None),
        ("bkea_std_konut", "Konut", ALTIN, "dot"),
        ("bkea_talep", "İşletme kredisi talebi", YESIL, None),
    ):
        fig.add_trace(go.Scatter(x=b13.index, y=b13[kolon], name=ad,
                                 line=dict(color=renk, width=1.5, dash=cizgi)))
    fig.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    fig.update_layout(title="Banka Kredileri Eğilim Anketi — net yüzde (pozitif = gevşeme / talep artışı)",
                      yaxis_title="net %")
    yaz(fig, "bkea.html")


if __name__ == "__main__":
    main()
