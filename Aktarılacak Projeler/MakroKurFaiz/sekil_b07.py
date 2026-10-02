#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 7 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)


def s12_redk(o: dict) -> None:
    b = o["b07"]
    s = b["sekil_12"]
    a = b["p7a"]["tufe"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.64, 0.36], horizontal_spacing=0.10,
                        subplot_titles=("TÜFE bazlı REDK ve dönüş yelpazesi", "Yarı ömür (yıl): kestirim ve %90 aralığı"))
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["redk_tufe"], mode="lines", name="REDK (TÜFE bazlı, 2025=100)",
                             line=dict(color=MAVI, width=2), hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra></extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=[s["tarih"][0], s["fan_tarih"][-1]], y=[s["ortalama_endeks"]] * 2, mode="lines",
                             name=f"1994–2026 ortalaması ({vir(s['ortalama_endeks'], 1)})",
                             line=dict(color=GRI, width=1.4, dash="dash")), 1, 1)
    f = s["fan"]
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["alt90"], mode="lines", line=dict(width=0), showlegend=False,
                             hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["ust90"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=ACIK_CLARET, name="%90 aralığının yolları (60 ay)", hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["mu"], mode="lines", name="medyan-yansız ρ ile sönüm",
                             line=dict(color=CLARET, width=2, dash="dot")), 1, 1)
    fig.update_yaxes(title_text="endeks (artış: TL reel değer kazancı)", row=1, col=1)

    satir = [("1994–2026", a["tam"])] + [(v["etiket"].split(" ")[0], v) for v in a["donemler"].values()]
    tavan = 20.0
    for i, (ad, v) in enumerate(satir):
        mu = v["yari_omur_mu_yil"]
        alt = v["yari_omur_alt90_yil"]
        ust = v["yari_omur_ust90_yil"]
        mu_c = tavan if mu is None else min(mu, tavan)
        ust_c = tavan if (ust is None or v.get("ust_sonsuz")) else min(ust, tavan)
        fig.add_trace(go.Scatter(x=[alt, ust_c], y=[ad, ad], mode="lines", line=dict(color=GRI, width=6),
                                 showlegend=(i == 0), name="%90 aralığı (sağ uç ∞ ise eksen tavanında)",
                                 hoverinfo="skip"), 1, 2)
        fig.add_trace(go.Scatter(x=[mu_c], y=[ad], mode="markers", marker=dict(color=CLARET, size=10),
                                 showlegend=(i == 0), name="medyan-yansız kestirim",
                                 hovertemplate=f"{ad}: {'∞' if mu is None else vir(mu, 1)} yıl<extra></extra>"), 1, 2)
        fig.add_trace(go.Scatter(x=[v["yari_omur_ols_yil"]], y=[ad], mode="markers",
                                 marker=dict(color=MAVI, size=8, symbol="diamond"), showlegend=(i == 0),
                                 name="sıradan en küçük kareler (aşağı yanlı)",
                                 hovertemplate=f"{ad}: {vir(v['yari_omur_ols_yil'], 1)} yıl<extra></extra>"), 1, 2)
    fig.update_xaxes(range=[0, tavan * 1.04], title_text="yıl", row=1, col=2)
    fig.update_yaxes(autorange="reversed", row=1, col=2)
    fig.update_layout(title=dict(text=(
        "Şekil 12 — Türkiye reel efektif kuru: ortalamadan uzak, dönüşü yavaş ve belirsiz"
        f"<br><sub>TCMB REDK (TÜFE bazlı), aylık {ay(s['tarih'][0])}–{ay(s['tarih'][-1])} · yelpaze bugünkü log "
        "sapmanın ρʰ ile sönümü, tahmin değil · aralık benzetimle (medyan-yansız)</sub>")))
    _yaz(fig, "12_redk.html", 540)
