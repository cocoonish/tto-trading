#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""13 Eylül 2026 Fed analizi — şekilleri üretir.

Bu bir hat değil, TARİHLİ bir analizin donmuş şekil setidir. Girdiler ölçülmüş
sayılar olarak burada durur; her biri kaynağı ve günüyle yazılıdır. Analiz
yayımlandığı günün metnidir (karar 08.09.2026), o yüzden şekiller de o günün
ölçümünü dondurur ve çıktı statik yola yazılır — `site/public/arastirma/`
altında özet dosyası yoktur, bu yüzden GrafikEmbed altyazıya tarih BASMAZ ve
her figür kendi tarihini kendi alt başlığında taşır.

  python3 site/tools/fed_egri_sekiller.py
  python3 site/tools/plotly_stil.py site/public/arastirma/fed-artirim-dongusu-2026-09-13/*.html
"""

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

KOK = Path(__file__).resolve().parents[2]
CIKTI = KOK / "site" / "public" / "arastirma" / "fed-artirim-dongusu-2026-09-13"
PLOTLY_JS = "/js/plotly-4.0.0.min.js"

# ── Ölçülen girdiler ────────────────────────────────────────────────────────
# ABD Hazinesi günlük getiri eğrisi, 11.09.2026, YATIRIM bazı.
ABD_EGRI = [(0.25, 4.01), (1.0, 4.32), (2.0, 4.63), (10.0, 4.98), (30.0, 5.36)]
ABD_ETIKET = ["3 ay", "1 yıl", "2 yıl", "10 yıl", "30 yıl"]

# New York Fed SOFR sabitlemesi, 10.09.2026. Politika bandı 3,50–3,75.
SOFR = 3.62
BANT = (3.50, 3.75)

# Bülten piyasa anlık görüntüleri. Anahtar: bülten sayısının günü; ölçüm bir
# ÖNCEKİ kapanışa aittir (bülten sabah koşar). 2 YILLIK SERİ DIŞARIDA: 11.09
# için %4,375 yazıyor, resmî eğri %4,63 — 25 baz puanlık sapma doğrulandı.
TARIHCE = [
    ("22.08", 3.710, 4.424, 4.738, 5.276), ("23.08", 3.710, 4.424, 4.738, 5.276),
    ("24.08", 3.705, 4.353, 4.647, 5.180), ("25.08", 3.705, 4.351, 4.639, 5.174),
    ("26.08", 3.690, 4.381, 4.664, 5.186), ("27.08", 3.678, 4.396, 4.672, 5.191),
    ("29.08", 3.730, 4.481, 4.720, 5.206), ("30.08", 3.730, 4.481, 4.720, 5.206),
    ("31.08", 3.732, 4.507, 4.758, 5.249), ("01.09", 3.772, 4.557, 4.796, 5.268),
    ("02.09", 3.772, 4.552, 4.796, 5.267), ("03.09", 3.740, 4.509, 4.762, 5.243),
    ("05.09", 3.757, 4.550, 4.784, 5.246), ("06.09", 3.757, 4.550, 4.784, 5.246),
    ("07.09", 3.757, 4.550, 4.784, 5.246), ("08.09", 3.775, 4.573, 4.806, 5.264),
    ("09.09", 3.805, 4.614, 4.837, 5.286), ("10.09", 3.845, 4.733, 4.944, 5.361),
]

# TL eğrisi, DİBS spot bileşik, 10.09.2026 kapanışı (TCMB EVDS / BIST).
TL_EGRI = [(0.25, 37.33), (1.0, 39.07), (2.0, 39.97), (5.0, 35.04), (9.0, 30.53)]
TL_ETIKET = ["3 ay", "1 yıl", "2 yıl", "5 yıl", "9 yıl"]
TL_POLITIKA = 37.0

# Ev paleti (site/src/styles/global.css).
MUREKKEP, CLARET, MAVI, GRI = "#1a1a1a", "#8c2f39", "#2f5d8c", "#8a8a8a"


def _yaz(fig: go.Figure, ad: str, yukseklik: int = 460) -> None:
    fig.update_layout(
        height=yukseklik, margin=dict(l=64, r=28, t=76, b=64),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        title=dict(x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.26, x=0),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor="#d8d4cc", ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs=PLOTLY_JS, full_html=True,
                   config={"displayModeBar": False, "responsive": True})
    print(f"  ✓ {yol.relative_to(KOK)}")


def sekil_01_egri() -> None:
    """Eğrinin tamamı gecelik çıpanın üzerinde: artırım fiyatlaması."""
    x = [v for v, _ in ABD_EGRI]
    y = [g for _, g in ABD_EGRI]
    fig = go.Figure()
    fig.add_hrect(y0=BANT[0], y1=BANT[1], fillcolor=GRI, opacity=0.14, line_width=0)
    fig.add_hline(y=SOFR, line=dict(color=GRI, width=1.4, dash="dot"),
                  annotation_text=f"SOFR %{SOFR:.2f} (10.09)".replace(".", ","),
                  annotation_position="bottom right")
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers+text", name="ABD Hazine eğrisi (11.09.2026)",
        line=dict(color=CLARET, width=2.4), marker=dict(size=9),
        text=[f"%{g:.2f}".replace(".", ",") for _, g in ABD_EGRI],
        textposition="top center", textfont=dict(size=12)))
    for (v, g), et in zip(ABD_EGRI, ABD_ETIKET):
        fig.add_annotation(x=v, y=SOFR, ay=-18, ax=0, showarrow=False,
                           text=f"+{round((g - SOFR) * 100)} bp", yshift=-22,
                           font=dict(size=11, color=MAVI))
    fig.update_xaxes(type="log", tickvals=x, ticktext=ABD_ETIKET, title_text="vade")
    fig.update_yaxes(title_text="getiri (%)", range=[3.3, 5.7])
    fig.update_layout(title=dict(text="Şekil 01 — ABD getiri eğrisi ve gecelik çıpa"
                                      "<br><sub>11 Eylül 2026 · yatırım bazı · mavi sayılar SOFR'a fark</sub>"))
    _yaz(fig, "01_egri.html")


def sekil_02_patika() -> None:
    """1 yıllık ve 2 yıllıktan türetilen ima edilen politika patikası."""
    ay = list(range(0, 25))

    def ramp(tepe: float) -> list[float]:
        return [SOFR + (tepe - SOFR) * min(a, 12) / 12 for a in ay]

    fig = go.Figure()
    fig.add_hrect(y0=BANT[0], y1=BANT[1], fillcolor=GRI, opacity=0.14, line_width=0)
    fig.add_trace(go.Scatter(x=ay, y=ramp(5.02), mode="lines", name="1 yıllıktan ima: tepe %5,02",
                             line=dict(color=CLARET, width=2.4)))
    fig.add_trace(go.Scatter(x=ay, y=ramp(4.97), mode="lines", name="2 yıllıktan ima: tepe %4,97",
                             line=dict(color=MAVI, width=2.4, dash="dash")))
    fig.add_trace(go.Scatter(x=ay, y=ramp(4.70), mode="lines",
                             name="20 bp vade primi varsayımıyla: tepe %4,70",
                             line=dict(color=GRI, width=1.8, dash="dot")))
    fig.add_annotation(x=18, y=5.02, text="ima edilen tepe bandı<br>%4,70 – %5,02",
                       showarrow=False, font=dict(size=12, color=MUREKKEP), yshift=18)
    fig.update_xaxes(title_text="bugünden itibaren ay", tickvals=[0, 6, 12, 18, 24])
    fig.update_yaxes(title_text="politika faizi (%)", range=[3.3, 5.4])
    fig.update_layout(title=dict(text="Şekil 02 — Eğriden türetilen ima edilen politika patikası"
                                      "<br><sub>Gri bant bugünkü hedef aralığı 3,50–3,75 · patika doğrusal varsayımıyla</sub>"))
    _yaz(fig, "02_patika.html")


def _par(t: float) -> float:
    """Par getiri eğrisi, düğümler arasında doğrusal."""
    v = [x for x, _ in ABD_EGRI]
    g = [y for _, y in ABD_EGRI]
    for i in range(len(v) - 1):
        if v[i] <= t <= v[i + 1]:
            p = (t - v[i]) / (v[i + 1] - v[i])
            return g[i] + p * (g[i + 1] - g[i])
    return g[-1] if t > v[-1] else g[0]


def _sifir_egri() -> dict[float, float]:
    """Par eğrisinden bootstrap edilmiş sıfır getiriler (yarım yıllık düğüm, kupon 2/yıl).

    Hazine'nin yayımladığı eğri PAR getiridir; ileri faiz özdeşliği SIFIR getiri
    ister. Yukarı eğimli bir eğride par'ı doğrudan kullanmak ileri faizi sistematik
    olarak küçük gösterir — sapma varsayılmaz, burada ölçülür.
    """
    dusum, iskonto = [], {}
    t = 0.5
    while t <= 30.0 + 1e-9:
        dusum.append(round(t, 1))
        t += 0.5
    for i, t in enumerate(dusum):
        k = _par(t) / 200                      # yarım dönem kupon
        onceki = sum(iskonto[dusum[j]] for j in range(i))
        iskonto[t] = (1 - k * onceki) / (1 + k)
    return {t: (d ** (-1 / t) - 1) * 100 for t, d in iskonto.items()}


SIFIR = _sifir_egri()


def _ileri(t1: float, t2: float, taban: str = "par") -> float:
    """t1 ile t2 arası ima edilen ileri faiz (yıllık bileşik özdeşliği)."""
    # İlk kupon döneminden kısa vade TEK nakit akışlıdır, yani zaten sıfır getiridir.
    g = _par if taban == "par" else (lambda t: _par(t) if t < 0.5 else SIFIR[round(t, 1)])
    a = (1 + g(t1) / 100) ** t1
    b = (1 + g(t2) / 100) ** t2
    return ((b / a) ** (1 / (t2 - t1)) - 1) * 100


def sekil_03_ileri() -> None:
    """İleri faizler patika varsayımı gerektirmez; tepe bandının üzerinde duruyorlar."""
    donem = [(0.25, 1.0, "3 ay → 1 yıl"), (1.0, 2.0, "1 yıl → 2 yıl"),
             (2.0, 10.0, "2 yıl → 10 yıl"), (10.0, 30.0, "10 yıl → 30 yıl")]
    orta = [(a + b) / 2 for a, b, _ in donem]
    ileri = [_ileri(a, b) for a, b, _ in donem]
    sifir = [_ileri(a, b, "sifir") for a, b, _ in donem]

    fig = go.Figure()
    fig.add_hrect(y0=4.70, y1=5.02, fillcolor=MAVI, opacity=0.10, line_width=0,
                  annotation_text="eğriden ima edilen tepe bandı %4,70–5,02",
                  annotation_position="top left",
                  annotation_font=dict(size=11, color=MAVI))
    fig.add_hline(y=SOFR, line=dict(color=GRI, width=1.4, dash="dot"),
                  annotation_text=f"SOFR %{SOFR:.2f}".replace(".", ","),
                  annotation_position="bottom right")
    fig.add_trace(go.Scatter(
        x=[v for v, _ in ABD_EGRI], y=[g for _, g in ABD_EGRI],
        mode="lines+markers", name="spot getiri eğrisi",
        line=dict(color=GRI, width=1.8), marker=dict(size=7)))
    fig.add_trace(go.Scatter(
        x=orta, y=ileri, mode="lines+markers+text", name="ileri faiz — par getiriden",
        line=dict(color=CLARET, width=2.4), marker=dict(size=10, symbol="diamond"),
        text=[f"%{o:.2f}".replace(".", ",") for o in ileri],
        textposition="bottom center", textfont=dict(size=12)))
    fig.add_trace(go.Scatter(
        x=orta, y=sifir, mode="lines+markers+text",
        name="ileri faiz — bootstrap edilmiş sıfır getiriden",
        line=dict(color=MUREKKEP, width=1.8, dash="dash"),
        marker=dict(size=9, symbol="diamond-open"),
        text=[f"%{o:.2f}".replace(".", ",") for o in sifir],
        textposition="top center", textfont=dict(size=11, color=MUREKKEP)))
    for o, (_, _, ad) in zip(orta, donem):
        fig.add_annotation(x=o, y=3.95, text=ad, showarrow=False,
                           font=dict(size=10, color=MUREKKEP))
    fig.update_xaxes(type="log", tickvals=[v for v, _ in ABD_EGRI], ticktext=ABD_ETIKET,
                     title_text="vade")
    fig.update_yaxes(title_text="faiz (%)", range=[3.4, 6.35])
    fig.update_layout(title=dict(
        text="Şekil 03 — İma edilen ileri faizler tepe bandının üzerinde"
             "<br><sub>11 Eylül 2026 · patika varsayımı taşımaz · par tabanı yukarı eğimli eğride ileri faizi KÜÇÜK gösterir</sub>"))
    _yaz(fig, "03_ileri.html")


def sekil_04_tarihce() -> None:
    """Ağustos sonundan eylül ortasına eğrinin kayması."""
    g = [t[0] for t in TARIHCE]
    fig = go.Figure()
    for i, (ad, renk) in enumerate([("3 ay", GRI), ("5 yıl", MAVI),
                                    ("10 yıl", CLARET), ("30 yıl", MUREKKEP)], start=1):
        fig.add_trace(go.Scatter(x=g, y=[t[i] for t in TARIHCE], mode="lines+markers",
                                 name=ad, line=dict(color=renk, width=2.2),
                                 marker=dict(size=5)))
    fig.update_xaxes(title_text="bülten sayısının günü")
    fig.update_yaxes(title_text="getiri (%)")
    fig.update_layout(title=dict(
        text="Şekil 04 — Eğri ağustos sonundan bu yana yukarı kaydı"
             "<br><sub>Ölçüm bir önceki kapanışa aittir · 2 yıllık seri sapmalı olduğu için dışarıda</sub>"))
    _yaz(fig, "04_tarihce.html")


def sekil_05_senaryo() -> None:
    """2 yıllık getirinin senaryo yelpazesi: yukarı dar, aşağı geniş."""
    senaryo = [
        ("Fiyatlama tamamen geri alınır", -93),
        ("Şok gevşer, döngü iki adımda biter", -48),
        ("Fed tam fiyatlandığı kadar yapar", 0),
        ("Tepe %5,02'ye revize", 7),
        ("Tepe %5,50'ye revize (geçişkenlik)", 42),
    ]
    ad = [s for s, _ in senaryo]
    bp = [b for _, b in senaryo]
    fig = go.Figure(go.Bar(
        x=bp, y=ad, orientation="h",
        marker=dict(color=[CLARET if b < 0 else MAVI for b in bp]),
        text=[f"{'−' if b < 0 else '+'}{abs(b)} bp" if b else "0" for b in bp],
        textposition="outside", cliponaxis=False))
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=1.2))
    fig.update_xaxes(title_text="2 yıllık getiride değişim (baz puan)", range=[-115, 65])
    fig.update_yaxes(title_text="")
    fig.update_layout(showlegend=False, margin=dict(l=250),
                      title=dict(text="Şekil 05 — 2 yıllık getirinin senaryo yelpazesi"
                                      "<br><sub>Çıpa: %4,63 (11.09.2026) · yukarı alan 7–42 bp, aşağı alan 48–93 bp</sub>"))
    _yaz(fig, "05_senaryo.html", 440)


def sekil_06_ayristirma() -> None:
    """10 yıllığın içinde politika beklentisi ile vade primi."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["10 yıllık getiri"], y=[3.50], name="beklenen ortalama gecelik faiz (~%3,50)",
                         marker_color=MAVI, text=["%3,50"], textposition="inside"))
    fig.add_trace(go.Bar(x=["10 yıllık getiri"], y=[1.48], name="artık: vade primi (~148 bp)",
                         marker_color=CLARET, text=["148 bp"], textposition="inside"))
    fig.update_layout(barmode="stack", bargap=0.62,
                      title=dict(text="Şekil 06 — %4,98'in içinde ne var"
                                      "<br><sub>Nötr faiz %3,00–3,50 varsayımından artık olarak · ±50 bp hata payı</sub>"))
    fig.update_yaxes(title_text="getiri (%)", range=[0, 5.6])
    fig.add_annotation(x=0, y=4.98, text="%4,98", showarrow=False, yshift=16,
                       font=dict(size=14, color=MUREKKEP))
    _yaz(fig, "06_ayristirma.html", 440)


def sekil_07_tr_abd() -> None:
    """İki eğri ters yöne bakıyor."""
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.13,
                        subplot_titles=("ABD — yukarı eğimli (artırım fiyatlanıyor)",
                                        "Türkiye — ters eğimli (indirim fiyatlanıyor)"))
    fig.add_trace(go.Scatter(x=[v for v, _ in ABD_EGRI], y=[g for _, g in ABD_EGRI],
                             mode="lines+markers", line=dict(color=CLARET, width=2.4),
                             marker=dict(size=8), name="ABD Hazine"), row=1, col=1)
    fig.add_hline(y=SOFR, line=dict(color=GRI, width=1.2, dash="dot"), row=1, col=1)
    fig.add_trace(go.Scatter(x=[v for v, _ in TL_EGRI], y=[g for _, g in TL_EGRI],
                             mode="lines+markers", line=dict(color=MAVI, width=2.4),
                             marker=dict(size=8), name="DİBS spot"), row=1, col=2)
    fig.add_hline(y=TL_POLITIKA, line=dict(color=GRI, width=1.2, dash="dot"), row=1, col=2)
    fig.update_xaxes(type="log", tickvals=[v for v, _ in ABD_EGRI], ticktext=ABD_ETIKET,
                     title_text="vade", row=1, col=1)
    fig.update_xaxes(type="log", tickvals=[v for v, _ in TL_EGRI], ticktext=TL_ETIKET,
                     title_text="vade", row=1, col=2)
    fig.update_yaxes(title_text="getiri (%)", range=[3.3, 5.7], row=1, col=1)
    fig.update_yaxes(title_text="getiri (%)", range=[28, 42], row=1, col=2)
    fig.update_layout(showlegend=False,
                      title=dict(text="Şekil 07 — İki eğri ters yöne bakıyor"
                                      "<br><sub>ABD 11.09.2026 · TL 10.09.2026 · kesikli çizgiler gecelik çıpa ve politika faizi</sub>"))
    _yaz(fig, "07_tr_abd.html", 480)


if __name__ == "__main__":
    print("▶ Fed analizi şekilleri")
    sekil_01_egri()
    sekil_02_patika()
    sekil_03_ileri()
    sekil_04_tarihce()
    sekil_05_senaryo()
    sekil_06_ayristirma()
    sekil_07_tr_abd()
    print("  7 şekil yazıldı — ev stili için: python3 site/tools/plotly_stil.py <dosyalar>")
