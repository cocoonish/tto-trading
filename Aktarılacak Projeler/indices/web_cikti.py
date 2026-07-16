#!/usr/bin/env python3
"""Statik web ciktisi ureticisi — FX haber-duyarlilik endeksi.

INTERNETSIZ calisir; yalnizca data/index_history.json okur ve iki Plotly HTML
dosyasi uretir (site standardi: include_plotlyjs='cdn', beyaz zemin, lejant
altta, baslik solda):

  cikti/endeks_tarihce.html — her parite icin endeks tarihcesi (cizgi)
  cikti/endeks_son.html     — son snapshot, degere gore sirali yatay bar

Kullanim:  python3 web_cikti.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plotly.graph_objects as go

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(config.DATA_DIR, "index_history.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "cikti")

# Ev stili renkler
TEAL = "#1d5c5c"      # pozitif / bullish
CLARET = "#8e1f2f"    # negatif / bearish
INK = "#1a1a1a"
GRID = "#e8e4dc"

# Kategori esikleri (config.SENTIMENT_THRESHOLDS ile ayni: +-0.3 / +-0.7)
ESIK_1 = 0.3
ESIK_2 = 0.7

# 15 parite icin ayirt edilebilir cizgi paleti
CIZGI_RENKLERI = [
    "#1d5c5c", "#8e1f2f", "#b8860b", "#2f4b7c", "#665191",
    "#a05195", "#d45087", "#f95d6a", "#ff7c43", "#7a9e7e",
    "#4d7ea8", "#c46210", "#5c5346", "#3a7ca5", "#9b2226",
]

KATEGORI_TR = {
    "Extremely Bullish": "Asiri Alici",
    "Bullish": "Alici",
    "Neutral": "Notr",
    "Bearish": "Satici",
    "Extremely Bearish": "Asiri Satici",
}


def _gorunen_ad(anahtar):
    """Parite anahtarini okunur ada cevir (config.ASSETS varsa oradan)."""
    varlik = config.ASSETS.get(anahtar)
    if varlik and varlik.get("name"):
        return varlik["name"]
    return anahtar


def _ortak_stil(fig, baslik):
    """Site ev stili: beyaz zemin, baslik solda, lejant yatay ve altta."""
    fig.update_layout(
        title=dict(text=baslik, x=0.02, xanchor="left",
                   font=dict(size=17, color=INK)),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans, Helvetica, Arial, sans-serif",
                  size=12, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.12,
                    xanchor="left", x=0),
        margin=dict(l=60, r=30, t=60, b=60),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def yukle_tarihce():
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def ciz_tarihce(tarihce, cikti_yolu):
    """Her parite bir cizgi; y=0 referans, +-0.3/+-0.7 kategori bantlari."""
    # parite -> (x, y) serileri
    seriler = {}
    for kayit in tarihce:
        ts = kayit.get("timestamp")
        for parite, veri in kayit.get("indices", {}).items():
            seriler.setdefault(parite, {"x": [], "y": []})
            seriler[parite]["x"].append(ts)
            seriler[parite]["y"].append(veri.get("value"))

    # Eksen siniri: endeks tipik olarak [-1, 1] ama tasarsa genislet
    tum_degerler = [d for s in seriler.values() for d in s["y"] if d is not None]
    sinir = max(1.0, max(abs(d) for d in tum_degerler)) * 1.05

    fig = go.Figure()
    for i, (parite, s) in enumerate(sorted(seriler.items())):
        fig.add_trace(go.Scatter(
            x=s["x"], y=s["y"],
            mode="lines+markers",
            name=_gorunen_ad(parite),
            line=dict(width=1.8, color=CIZGI_RENKLERI[i % len(CIZGI_RENKLERI)]),
            marker=dict(size=4),
            hovertemplate="%{y:+.4f}",
        ))

    # Kategori bantlari: soluk yatay bolgeler
    bantlar = [
        (ESIK_1, ESIK_2, TEAL, 0.06),      # Bullish
        (ESIK_2, sinir, TEAL, 0.12),       # Extremely Bullish
        (-ESIK_2, -ESIK_1, CLARET, 0.06),  # Bearish
        (-sinir, -ESIK_2, CLARET, 0.12),   # Extremely Bearish
    ]
    for y0, y1, renk, opaklik in bantlar:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=renk, opacity=opaklik,
                      line_width=0, layer="below")

    # y=0 referans cizgisi
    fig.add_hline(y=0, line_color=INK, line_width=1, opacity=0.5)
    # Esik cizgileri (ince, kesikli)
    for esik in (ESIK_1, ESIK_2, -ESIK_1, -ESIK_2):
        fig.add_hline(y=esik, line_color=INK, line_width=0.5,
                      line_dash="dot", opacity=0.25)

    _ortak_stil(fig, "FX haber-duyarlılık endeksi — tarihçe")
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title_text="Endeks değeri", range=[-sinir, sinir])
    fig.update_xaxes(title_text=None)

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def ciz_son_snapshot(tarihce, cikti_yolu):
    """Son snapshot: degere gore sirali yatay bar + kategori etiketi."""
    son = tarihce[-1]
    ts = son.get("timestamp", "")
    kayitlar = sorted(son.get("indices", {}).items(),
                      key=lambda kv: kv[1].get("value", 0))

    adlar = [_gorunen_ad(k) for k, _ in kayitlar]
    degerler = [v.get("value", 0) for _, v in kayitlar]
    kategoriler = [v.get("category", "") for _, v in kayitlar]
    renkler = [TEAL if d >= 0 else CLARET for d in degerler]
    etiketler = [f"{d:+.2f}  {k}" for d, k in zip(degerler, kategoriler)]

    fig = go.Figure(go.Bar(
        x=degerler, y=adlar,
        orientation="h",
        marker=dict(color=renkler),
        text=etiketler,
        textposition="outside",
        textfont=dict(size=11),
        customdata=kategoriler,
        hovertemplate="%{y}: %{x:+.4f} (%{customdata})<extra></extra>",
        showlegend=False,
    ))

    fig.add_vline(x=0, line_color=INK, line_width=1, opacity=0.5)

    tarih_kisa = ts[:16].replace("T", " ") if ts else ""
    _ortak_stil(fig, f"FX haber-duyarlılık endeksi — son okuma ({tarih_kisa} UTC)")
    fig.update_layout(
        height=max(420, 34 * len(adlar) + 120),
        margin=dict(l=90, r=140, t=60, b=40),
    )
    # Dis etiketlere (deger + kategori) yer birakmak icin genis sinir
    sinir = max(1.0, max(abs(d) for d in degerler)) * 1.15
    fig.update_xaxes(title_text="Endeks değeri", range=[-sinir, sinir])
    fig.update_yaxes(gridcolor="#ffffff")

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def uret(cikti_dizini=None):
    """Iki HTML ciktisini uret; uretilen dosya yollarini dondur."""
    hedef = cikti_dizini or OUTPUT_DIR
    os.makedirs(hedef, exist_ok=True)
    tarihce = yukle_tarihce()
    if not tarihce:
        raise ValueError(f"Bos tarihce: {HISTORY_FILE}")
    yollar = [
        ciz_tarihce(tarihce, os.path.join(hedef, "endeks_tarihce.html")),
        ciz_son_snapshot(tarihce, os.path.join(hedef, "endeks_son.html")),
    ]
    return yollar


def main():
    yollar = uret()
    for yol in yollar:
        print(f"  Yazildi: {yol}")


if __name__ == "__main__":
    main()
