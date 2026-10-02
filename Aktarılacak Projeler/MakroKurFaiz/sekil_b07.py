#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 7 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)


def _paneller_sola(fig, boyut: int = 13) -> None:
    """Panel başlıkları sola yaslanır: dar ekranda ortalı başlık iki uçtan birden kırpılıyordu."""
    for an in fig.layout.annotations:
        if an.yref == "paper" and an.yanchor == "bottom" and an.xref == "paper":
            an.update(x=0, xanchor="left", font=dict(size=boyut, color=MUREKKEP))


def s12_redk(o: dict) -> None:
    b = o["b07"]
    s = b["sekil_12"]
    a = b["p7a"]["tufe"]
    # iki panel ALT ALTA: yan yana dizilince dar ekranda panel başlıkları üst üste biniyordu
    fig = make_subplots(rows=2, cols=1, row_heights=[0.64, 0.36], vertical_spacing=0.13,
                        subplot_titles=("TÜFE bazlı REDK ve dönüş yelpazesi",
                                        "Yarı ömür (yıl): kestirim ve %90 aralığı"))
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["redk_tufe"], mode="lines", name="REDK (TÜFE bazlı, 2025=100)",
                             line=dict(color=MAVI, width=2), hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra></extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=[s["tarih"][0], s["fan_tarih"][-1]], y=[s["ortalama_endeks"]] * 2, mode="lines",
                             showlegend=False, line=dict(color=GRI, width=1.4, dash="dash"), hoverinfo="skip"), 1, 1)
    # kısa etiket: dönem adı çizginin kendisinde (bütün örneklemi kaplıyor); uzun etiket dar ekranda seriyi örtüyordu
    fig.add_annotation(x=s["fan_tarih"][-1], y=s["ortalama_endeks"], xanchor="right", yanchor="bottom", showarrow=False,
                       text=f"geometrik ortalama {vir(s['ortalama_endeks'], 1)}",
                       font=dict(size=11, color=GRI), bgcolor="rgba(255,255,255,0.85)", row=1, col=1)
    f = s["fan"]
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["alt90"], mode="lines", line=dict(width=0), showlegend=False,
                             hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["ust90"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=ACIK_CLARET, name=f"%90 aralığının yolları ({s['fan_n'] - 1} ay)",
                             hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["mu"], mode="lines", name="medyan-yansız ρ ile sönüm",
                             line=dict(color=CLARET, width=2, dash="dot"),
                             hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra>sönüm yolu</extra>"), 1, 1)
    fig.update_yaxes(title_text="endeks (artış: TL reel değer kazancı)", row=1, col=1)
    fig.update_xaxes(zeroline=False, row=1, col=1)

    satir = [(f"{a['tam']['ilk'][:4]}–{a['tam']['son'][:4]}", a["tam"])] + \
            [(v["etiket"].split(" ")[0], v) for v in a["donemler"].values()]
    tavan = 20.0
    for i, (ad, v) in enumerate(satir):
        mu = v["yari_omur_mu_yil"]
        alt = v["yari_omur_alt90_yil"]
        ust = v["yari_omur_ust90_yil"]
        sonsuz = ust is None or v.get("ust_sonsuz")
        mu_c = tavan if mu is None else min(mu, tavan)
        ust_c = tavan if sonsuz else min(ust, tavan)
        fig.add_trace(go.Scatter(x=[alt, ust_c], y=[ad, ad], mode="lines", line=dict(color=GRI, width=6),
                                 showlegend=(i == 0), name="%90 aralığı (∞: üst uç sonsuz)",
                                 hovertemplate=f"{ad}: %90 aralığı {vir(alt, 1)} – {'∞' if sonsuz else vir(ust, 1)} yıl"
                                               "<extra></extra>"), 2, 1)
        if sonsuz:
            fig.add_annotation(x=tavan, y=ad, text="∞", showarrow=False, xanchor="left", xshift=4,
                               font=dict(size=13, color=GRI), row=2, col=1)
        # değer etiketi: tavana yakın bir kestirim (1994–2026: 19,6 yıl) tavanda kırpılmış sanılmasın
        fig.add_trace(go.Scatter(x=[mu_c], y=[ad], mode="markers+text", marker=dict(color=CLARET, size=10),
                                 text=["∞" if mu is None else vir(mu, 1)], textposition="top center",
                                 textfont=dict(size=11, color=CLARET),
                                 showlegend=(i == 0), name="medyan-yansız kestirim",
                                 hovertemplate=f"{ad}: {'∞' if mu is None else vir(mu, 1)} yıl<extra></extra>"), 2, 1)
        fig.add_trace(go.Scatter(x=[v["yari_omur_ols_yil"]], y=[ad], mode="markers",
                                 marker=dict(color=MAVI, size=8, symbol="diamond"), showlegend=(i == 0),
                                 name="sıradan en küçük kareler (aşağı yanlı)",
                                 hovertemplate=f"{ad}: {vir(v['yari_omur_ols_yil'], 1)} yıl<extra></extra>"), 2, 1)
    fig.update_xaxes(range=[0, tavan * 1.06], title_text="yarı ömür (yıl)", zeroline=False, row=2, col=1)
    # ters sıralı kategori ekseni, üstte pay: ilk satırın değer etiketi çizim alanının üstünde kırpılıyordu
    fig.update_yaxes(range=[len(satir) - 0.5, -0.75], row=2, col=1)
    _paneller_sola(fig)
    fig.update_layout(title=dict(text=(
        "Şekil 12 — Türkiye reel efektif kuru: ortalamadan uzak, dönüşü yavaş ve belirsiz"
        f"<br><sub>TCMB REDK (TÜFE bazlı, 2025=100), aylık {ay(s['tarih'][0])}–{ay(s['tarih'][-1])} · artış: TL'nin "
        "reel değer kazancı</sub>"
        "<br><sub>log REDK'de AR(1), yarı ömür = ln 0,5 / ln ρ · yelpaze: bugünkü log sapmanın ρʰ ile sönümü, "
        "tahmin değil</sub>"
        "<br><sub>aralık benzetimle; medyan-yansız kestirim, çünkü küçük örneklemde en küçük kareler ρ'yu aşağı "
        "çeker</sub>")))
    _yaz(fig, "12_redk.html", 820)
