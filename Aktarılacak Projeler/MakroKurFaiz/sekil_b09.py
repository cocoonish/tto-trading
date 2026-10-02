#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 9 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)


def s16_kur_baskisi(o: dict) -> None:
    b = o["b09"]
    s = b["sekil_16"]
    d = b["p9b"]["donemler"]
    fig = make_subplots(rows=2, cols=1, row_heights=[0.66, 0.34], vertical_spacing=0.16,
                        subplot_titles=("Kur baskısı endeksinin aylık bileşenleri (σ birimi)",
                                        "Dönem dönem bileşen payları: cov(bileşen, endeks) / var(endeks)"))
    for ad, renk, etiket in (("kur", MAVI, "kur (TL değer kaybı)"), ("rezerv", CLARET, "rezerv kaybı"),
                             ("faiz", TURUNCU, "fonlama maliyeti artışı")):
        fig.add_trace(go.Bar(x=s["tarih"], y=s[ad], name=etiket, marker_color=renk, marker_line_width=0,
                             hovertemplate="%{x|%m.%Y}: %{y:.2f}<extra>" + etiket + "</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["emp"], mode="lines", name="endeks (toplam)",
                             line=dict(color=MUREKKEP, width=1.2)), 1, 1)
    fig.update_layout(barmode="relative", bargap=0.05)
    fig.update_yaxes(title_text="σ", row=1, col=1)
    adlar = list(d.keys())
    kisa = [a.replace("yönetilen kur (2021-12 … 2023-06)", "yönetilen kur").replace(" (Kasım'a kadar)", "") for a in adlar]
    for ad, renk in (("kur", MAVI), ("rezerv", CLARET), ("faiz", TURUNCU)):
        fig.add_trace(go.Bar(y=kisa, x=[d[a]["pay"][ad] for a in adlar], orientation="h", marker_color=renk,
                             showlegend=False, marker_line_width=0,
                             text=[yuzde(d[a]["pay"][ad] * 100, 0) if d[a]["pay"][ad] >= 0.05 else "" for a in adlar], textposition="inside",
                             insidetextanchor="middle", textfont=dict(color="white", size=11),
                             hovertemplate="%{y}: %{x:.2f}<extra>" + ad + "</extra>"), 2, 1)
    fig.update_xaxes(range=[-0.1, 1.05], title_text="pay", row=2, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)
    fig.update_layout(title=dict(text=(
        "Şekil 16 — Baskı kura mı yazılıyor, rezerve mi, faize mi?"
        f"<br><sub>Haftalık, {tarih(b['p9b']['ilk'])}–{tarih(b['p9b']['son'])} · kur USD/TRY, rezerv TCMB swap hariç net "
        "(brüt rezerve oranla), faiz TCMB ağırlıklı ortalama fonlama maliyeti · ağırlıklar bileşenin σ'sının tersi</sub>")))
    _yaz(fig, "16_kur_baskisi.html", 760)
