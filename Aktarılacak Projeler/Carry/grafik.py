#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TL taşıma defteri — dört Plotly grafiği.

plotly.js gömülmez, CDN'den gelir: gömülü hâli dosya başına ~4,6 MB, sayfada
dört grafik var. Site çevrimiçi servis edildiği için CDN varsayımı güvenli.
Üretimden sonra `python3 site/tools/plotly_stil.py --hepsi` ev stiline çevirir.
"""
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from hesap import hesapla, tarihe_cevir

BURASI = Path(__file__).resolve().parent
CFG = {"displayModeBar": False, "responsive": True}
KIRMIZI, YESIL, GRI, MAVI = "#8e1f2f", "#1d5c5c", "#8a8578", "#9a7327"


def eksen_tarihi(okur_tarihi: str) -> str:
    """Özetin okur tarihini (GG.AA.YYYY) Plotly'nin eksen yazımına (ISO) çevirir.

    Özet okura yazılır (ortak/bicim sözleşmesi); çizim kütüphanesi ISO ister.
    Okur yazımı doğrudan verilseydi dikey çizgi tarih ekseninde değil, kategori
    olarak düşer ve şekil sessizce bozulurdu. Çözüm tek tanımdan (bicim).
    """
    t = tarihe_cevir(okur_tarihi)
    if t is None:
        raise ValueError(f"çözülemeyen tarih: {okur_tarihi!r}")
    return t.isoformat()


def yaz(fig, ad):
    # Sabit div kimliği: Plotly rastgele id üretiyor ve veri değişmese de HTML her
    # koşuda değişip commit üretiyordu (01.09: bir günde beş boş commit).
    fig.write_html(BURASI / ad, include_plotlyjs="cdn", config=CFG, div_id=ad.replace(".html", ""))
    print(" ", ad)


def main():
    d, e, ozet = hesapla()
    d19 = d[d.index >= "2019-01-01"]

    # 01 — İleriye bakan taşıma makası
    f = go.Figure()
    f.add_trace(go.Scatter(x=d19.index, y=d19["makas_politika_d1a"], name="Politika − 1a deval hızı",
                           line=dict(color=KIRMIZI, width=1.6)))
    f.add_trace(go.Scatter(x=d19.index, y=d19["makas_tlref_b_d3a"], name="TLREF (bileşik) − 3a deval hızı",
                           line=dict(color=YESIL, width=1.6)))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="TL taşıma makası — faiz eksi kur hızı (puan)",
                    yaxis_title="puan")
    yaz(f, "makas.html")

    # 02 — Gerçekleşen carry endeksi + zirveden düşüş
    f = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32],
                      vertical_spacing=0.06)
    f.add_trace(go.Scatter(x=e.index, y=e["endeks"], name="Carry endeksi (USD bazlı)",
                           line=dict(color=KIRMIZI, width=1.6)), 1, 1)
    f.add_hline(y=100, line=dict(color=GRI, width=1, dash="dot"), row=1, col=1)
    for x in ozet["kotu_aylar"]:
        f.add_vline(x=eksen_tarihi(x["tarih"]), line=dict(color=GRI, width=1, dash="dot"))
    f.add_trace(go.Scatter(x=e.index, y=e["zirveden"], name="Zirveden düşüş (%)",
                           fill="tozeroy", line=dict(color=YESIL, width=1)), 2, 1)
    f.update_layout(title="Hedge'siz TL taşıma: 1 USD'nin TLREF'te değerlenip USD'ye dönmesi "
                          f"(100 = {ozet['endeks_bas']})")
    f.update_yaxes(title_text="endeks", row=1, col=1)
    f.update_yaxes(title_text="%", row=2, col=1)
    yaz(f, "endeks.html")

    # 03 — Nakit taşıma vs tahvil taşıması
    f = go.Figure()
    f.add_trace(go.Scatter(x=d19.index, y=d19["makas_tlref_b_d1a"], name="Nakit: TLREF (bileşik) − 1a deval",
                           line=dict(color=KIRMIZI, width=1.4)))
    f.add_trace(go.Scatter(x=d19.index, y=d19["carry_2y_tlref"], name="Tahvil: 2y DİBS − TLREF (bileşik)",
                           line=dict(color=YESIL, width=1.4)))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="Aynı paranın iki taşıması — nakit kârlı, tahvil zararlı olabilir (puan)",
                    yaxis_title="puan")
    yaz(f, "nakit_tahvil.html")

    # 04 — Konvansiyon farkı: aynı taşıma, iki hesap
    f = go.Figure()
    son2y = d[d.index >= "2023-01-01"]
    f.add_trace(go.Scatter(x=son2y.index, y=son2y["carry_2y_tlref"], name="Bileşik konvansiyon (doğru)",
                           line=dict(color=KIRMIZI, width=1.6)))
    f.add_trace(go.Scatter(x=son2y.index, y=son2y["carry_2y_tlref_basit"], name="Basit faizle (yanlış)",
                           line=dict(color=GRI, width=1.4, dash="dash")))
    f.add_hline(y=0, line=dict(color=GRI, width=1, dash="dot"))
    f.update_layout(title="2y DİBS taşıması: basit faizle hesap işareti bile ters çevirebilir (puan)",
                    yaxis_title="puan")
    yaz(f, "konvansiyon.html")


if __name__ == "__main__":
    main()
