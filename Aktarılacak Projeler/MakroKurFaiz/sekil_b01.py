#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 1 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)

GOLGE = "rgba(138,138,138,0.17)"
VAKA = "rgba(184,134,11,0.30)"


def _bloklar(tarihler: list, bayrak: list) -> list:
    """Ardışık doğru haftaların [ilk, son] aralıkları."""
    out, ac = [], None
    for i, b in enumerate(bayrak):
        if b and ac is None:
            ac = i
        if not b and ac is not None:
            out.append((tarihler[ac], tarihler[i - 1]))
            ac = None
    if ac is not None:
        out.append((tarihler[ac], tarihler[-1]))
    return out


def s01_abd_korelasyon(o: dict) -> None:
    b = o["b01"]
    s = b["sekil_01"]
    t, k = s["tarih"], s["kor"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4], vertical_spacing=0.11,
                        subplot_titles=("Korelasyon (60 iş günü): ABD 10 yıllık ile dolar",
                                        "VIX: 60 iş günlük ortalama ve eşik"))
    fig.add_trace(go.Scatter(x=t, y=[max(x, 0.0) for x in k], mode="lines", line=dict(width=0), fill="tozeroy",
                             fillcolor=ACIK_MAVI, hoverinfo="skip", showlegend=False), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=[min(x, 0.0) for x in k], mode="lines", line=dict(width=0), fill="tozeroy",
                             fillcolor="rgba(140,47,57,0.24)", hoverinfo="skip", showlegend=False), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=k, mode="lines", name="korelasyon (artı: faiz yükselirken dolar değer kazanır)",
                             line=dict(color=MAVI, width=1.3),
                             hovertemplate="%{x|%d.%m.%Y}: %{y:.2f}<extra>korelasyon</extra>"), 1, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.8), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=s["vix60"], mode="lines", name="VIX, 60 iş günlük ortalama",
                             line=dict(color=TURUNCU, width=1.5),
                             hovertemplate="%{x|%d.%m.%Y}: %{y:.1f}<extra>VIX ortalaması</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=t, y=s["vix60_q75"], mode="lines",
                             name="eşik: 1990'dan o güne biriken ortalamaların 75. yüzdeliği",
                             line=dict(color=MUREKKEP, width=1.1, dash="dash"),
                             hovertemplate="%{x|%d.%m.%Y}: %{y:.1f}<extra>eşik</extra>"), 2, 1)
    # gölgelerin lejantı (boş izler)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="gri gölge: VIX ortalaması eşiğin üstünde",
                             marker=dict(symbol="square", size=12, color="rgba(138,138,138,0.35)")), 1, 1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="sarı gölge: vaka penceresi",
                             marker=dict(symbol="square", size=12, color=VAKA)), 1, 1)
    # gölgeler izlerden SONRA eklenir (boş alt grafiğe şekil konmaz); katmanı izlerin altında
    # yüksek VIX haftaları: 60 günlük ortalama, o güne kadar biriken dağılımın 75. yüzdeliğinin üstünde
    for x0, x1 in _bloklar(t, [v > q for v, q in zip(s["vix60"], s["vix60_q75"])]):
        fig.add_vrect(x0=x0, x1=x1, fillcolor=GOLGE, line_width=0, layer="below", row="all", col=1)
    vaka_ad = {"guvenli_liman_2011": "2011 sonu: güvenli liman", "kurumsal_risk_2025": "Nisan 2025: kurumsal risk"}
    for v in s["vakalar"]:
        fig.add_vrect(x0=v["ilk"], x1=v["son"], fillcolor=VAKA, line_width=0, layer="below", row="all", col=1)
        yeni = v["ilk"] >= "2020"
        fig.add_annotation(x=v["ilk"], y=0.93 if yeni else -0.93, xref="x", yref="y", text=vaka_ad[v["ad"]],
                           showarrow=False, xanchor="right", xshift=-3, font=dict(size=11, color="#7a5a08"))
    for a in fig.layout.annotations:          # alt grafik başlıkları sola, dar ekrana sığacak boyda
        if a.yanchor == "bottom" and a.yref == "paper":
            a.update(x=0, xanchor="left", font=dict(size=13))
    fig.update_yaxes(range=[-1, 1], dtick=0.5, tickformat=".1f", title_text="korelasyon", row=1, col=1)
    fig.update_yaxes(title_text="VIX (endeks puanı)", row=2, col=1)
    # x aralığı veriden: vaka etiketleri eksen aralığını kendiliğinden genişletiyordu (390 px'te 1997'ye)
    fig.update_xaxes(range=[s["ilk"], s["son"]], row="all", col=1)
    fig.update_layout(legend=dict(y=-0.12), title=dict(text=(
        "Şekil 01 — ABD faizi ile dolar çoğunlukla<br>aynı yöne gider; VIX yükseldikçe işaret daha<br>"
        "sık döner, ama her dönüş VIX'le gelmez"
        "<br><sub>ABD Hazinesi 10 yıllık getirisinin günlük değişimi (bp) ile altı G10<br>"
        "kurundan eşit ağırlıklı dolar sepetinin günlük değişimi (artış: dolar<br>"
        "değer kazanır) · kurlar CNBC, New York 17:00 · VIX Yahoo Finance<br>"
        f"60 iş günlük kayan pencere, haftanın son iş günü · {tarih(s['ilk'])}–{tarih(s['son'])}</sub>")))
    _yaz(fig, "01_abd_korelasyon.html", 720)
