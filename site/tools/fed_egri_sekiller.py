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


# CME FedWatch koşullu toplantı olasılıkları, 13.09.2026 okuması.
# Sütun = hedef aralık (bp); hücre = o toplantıda o aralığın olasılığı (%).
# HAZİNE EĞRİSİ 11.09, FEDWATCH 13.09 — iki gün ayrık, damga iki parçalı yazılır.
FW_TARIH = "13.09.2026"
FW_ARALIK = [(350, 375), (375, 400), (400, 425), (425, 450), (450, 475),
             (475, 500), (500, 525), (525, 550), (550, 575)]
FW_ORTA = [(a + b) / 200 for a, b in FW_ARALIK]
FW = [
    ("16.09.26", [12.7, 87.3,  0.0,  0.0,  0.0,  0.0, None, None, None]),
    ("28.10.26", [ 6.5, 51.0, 42.5,  0.0,  0.0,  0.0,  0.0,  0.0,  0.0]),
    ("09.12.26", [ 2.3, 22.1, 48.0, 27.6,  0.0,  0.0,  0.0,  0.0,  0.0]),
    ("27.01.27", [ 1.4, 14.4, 37.9, 35.6, 10.8,  0.0,  0.0,  0.0,  0.0]),
    ("17.03.27", [ 0.6,  6.8, 24.2, 36.9, 25.2,  6.3,  0.0,  0.0,  0.0]),
    ("28.04.27", [ 0.4,  5.1, 19.4, 33.4, 28.5, 11.5,  1.7,  0.0,  0.0]),
    ("09.06.27", [ 0.3,  3.6, 14.9, 29.0, 30.0, 16.8,  4.8,  0.5,  0.0]),
    ("28.07.27", [ 0.3,  3.3, 13.7, 27.5, 29.9, 18.2,  6.1,  1.0,  0.1]),
    ("15.09.27", [ 0.2,  3.1, 13.1, 26.7, 29.7, 18.9,  6.8,  1.3,  0.1]),
    ("27.10.27", [ 0.2,  3.1, 13.1, 26.7, 29.7, 18.9,  6.8,  1.3,  0.1]),
    ("08.12.27", [ 0.5,  3.9, 14.2, 26.9, 28.9, 18.0,  6.4,  1.2,  0.1]),
]
# Ölçülen vade primiyle yeniden türetilen tepe bandı (bkz. yazının 3. bölümü).
FW_BANT = (4.66, 4.89)


def fw_beklenen() -> list[float]:
    """Her toplantı için olasılık ağırlıklı beklenen politika faizi."""
    return [sum(FW_ORTA[i] * (x / 100) for i, x in enumerate(p) if x is not None)
            for _, p in FW]


def fw_dogrula() -> None:
    """Her satır %100'e toplamalı — transkripsiyon kapısı, uydurma sayı yayına girmesin."""
    for g, p in FW:
        t = sum(x for x in p if x is not None)
        if abs(t - 100) > 0.35:
            raise ValueError(f"FedWatch {g}: olasılıklar {t:.1f}% — %100'e toplamıyor")


fw_dogrula()

# Ev paleti (site/src/styles/global.css).
MUREKKEP, CLARET, MAVI, GRI = "#1a1a1a", "#8c2f39", "#2f5d8c", "#8a8a8a"


def _vir(x: float, basamak: int = 2) -> str:
    """Ondalık virgül — YALNIZ sayıya uygulanır.

    `f"...{tarih}...{sayi}".replace(".", ",")` kalıbı bir kez tarihi de bozdu
    (13.09.2026 → 13,09,2026) ve figür o hâliyle yayına gitti: Python örtük
    dizge birleştirmesinde metot bütün zincire bağlanıyor. Sayı buradan
    biçimlenir, dizge zincirine replace UYGULANMAZ; kapısı `_damga_denetle`.
    """
    return f"{x:.{basamak}f}".replace(".", ",")


def _xlog(v: float) -> float:
    """LOG eksende bir açıklamanın x'i, veri değeri değil LOG10'udur.

    Plotly `add_annotation(x=...)` çağrısını eksenin KENDİ birimiyle okur; log
    eksende bu birim log10'dur. Ham değer verilince x=30 açıklaması 10^30'a
    gider, eksen onu kapsamak için otomatik genişler ve gerçek veri (0,25–30)
    sol uca ezilir — figür "kaymış" görünür ama kusur yerleşimde değil BİRİMDE.
    İzler ham değer alır, açıklamalar buradan geçer; kapısı `_eksen_denetle`.
    """
    import math

    return math.log10(v)


def _damga_denetle() -> None:
    """Üretilen figürlerde virgülle bozulmuş tarih kaldıysa DÜŞ.

    Ölçüt çıktıya bakar, kaynağa değil: aynı kalıp bu dosyada on yerde geçiyor
    ve biri bir gün yeniden tarihi kapsarsa kaynak taraması onu göremez.
    """
    import re

    # (a) ÇIKTI: virgülle bozulmuş tarih — tam (13,09,2026) ve kısa (10,09) hâli.
    #     Kısa hâl parantez içinde aranır; çıplak "10,09" meşru bir ondalık sayı olabilir.
    bozuk = []
    for y in sorted(CIKTI.glob("*.html")):
        h = y.read_text(encoding="utf-8")
        if re.search(r"\d{2},\d{2},\d{4}", h) or re.search(r"\(\d{2},\d{2}\)", h):
            bozuk.append(y.name)
    if bozuk:
        raise SystemExit(f"‼ virgülle bozulmuş tarih: {', '.join(bozuk)}")

    # (b) KAYNAK: ham nokta→virgül dönüşümü yalnız _vir içinde kalabilir. Çıktı
    #     taraması kısa tarihi ancak parantez içinde görebiliyor; kalıbın kendisi
    #     yasaklanmazsa yarın parantezsiz bir yazımda sessizce geri gelir.
    #     Soru AST'ye sorulur, metne DEĞİL: ilk yazımda düz metin taraması bu
    #     kuralı ANLATAN belge dizgesini ve yorumu ihlal saydı — bir kapının
    #     yanlış alarmı, ölçtüğü kusurla aynı sınıftan bir arızadır.
    import ast

    agac = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    disarida = []
    for dugum in ast.walk(agac):
        if not (isinstance(dugum, ast.Call)
                and isinstance(dugum.func, ast.Attribute)
                and dugum.func.attr == "replace"
                and len(dugum.args) == 2
                and all(isinstance(a, ast.Constant) for a in dugum.args)
                and dugum.args[0].value == "." and dugum.args[1].value == ","):
            continue
        icinde = next((f.name for f in ast.walk(agac)
                       if isinstance(f, ast.FunctionDef)
                       and f.lineno <= dugum.lineno <= (f.end_lineno or f.lineno)), None)
        if icinde != "_vir":
            disarida.append(f"satır {dugum.lineno} ({icinde or 'modül düzeyi'})")
    if disarida:
        raise SystemExit(f"‼ _vir dışında ham virgül dönüşümü: {', '.join(disarida)}")

    print("  ✓ damga denetimi: bozuk tarih yok · virgül dönüşümü tek yerde")


def _eksen_denetle() -> None:
    """LOG eksende açıklamalar verinin aralığında mı.

    Aralık dışına düşen bir açıklama ekseni otomatik genişletir ve gerçek veriyi
    bir köşeye ezer — figür üretilir, koşu yeşil biter, hiçbir sayı yanlış
    değildir ve okur çizilen şeyi göremez. Ölçüt ÇIKTIYA bakar, çağrı yerine
    değil: kural yarın başka bir figürde yeniden bozulabilir.
    """
    import json
    import math
    import re

    kusur = []
    for y in sorted(CIKTI.glob("*.html")):
        h = y.read_text(encoding="utf-8")
        m = re.search(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\]),\s*(\{.*?\}),\s*\{"displayModeBar"',
                      h, re.S)
        if not m:
            continue
        veri, yer = json.loads(m.group(1)), json.loads(m.group(2))
        if yer.get("xaxis", {}).get("type") != "log":
            continue
        xs = [v for t in veri for v in t.get("x", []) if isinstance(v, (int, float))]
        if not xs:
            continue
        alt, ust = math.log10(min(xs)), math.log10(max(xs))
        for a in yer.get("annotations", []):
            if a.get("xref") not in (None, "x") or not isinstance(a.get("x"), (int, float)):
                continue
            if not (alt - 0.35 <= a["x"] <= ust + 0.35):
                kusur.append(f"{y.name}: x={a['x']} (veri log aralığı {alt:.2f}–{ust:.2f})")
    if kusur:
        raise SystemExit("‼ log eksende aralık dışı açıklama:\n    " + "\n    ".join(kusur))
    print("  ✓ eksen denetimi: log eksende aralık dışı açıklama yok")


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
                  annotation_text=f"SOFR %{_vir(SOFR, 2)} (10.09)",
                  annotation_position="bottom right")
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers+text", name="ABD Hazine eğrisi (11.09.2026)",
        line=dict(color=CLARET, width=2.4), marker=dict(size=9),
        text=[f"%{_vir(g, 2)}" for _, g in ABD_EGRI],
        textposition="top center", textfont=dict(size=12)))
    for (v, g), et in zip(ABD_EGRI, ABD_ETIKET):
        fig.add_annotation(x=_xlog(v), y=SOFR, ay=-18, ax=0, showarrow=False,
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
                                      "<br><sub>11 Eylül 2026 eğrisinden · gri bant bugünkü hedef aralığı 3,50–3,75 · patika doğrusal varsayımıyla</sub>"))
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
                  annotation_text="vade primi VARSAYIMIYLA tepe bandı %4,70–5,02 (2. bölüm)",
                  annotation_position="top left",
                  annotation_font=dict(size=11, color=MAVI))
    fig.add_hline(y=SOFR, line=dict(color=GRI, width=1.4, dash="dot"),
                  annotation_text=f"SOFR %{_vir(SOFR, 2)}",
                  annotation_position="bottom right")
    fig.add_trace(go.Scatter(
        x=[v for v, _ in ABD_EGRI], y=[g for _, g in ABD_EGRI],
        mode="lines+markers", name="spot getiri eğrisi",
        line=dict(color=GRI, width=1.8), marker=dict(size=7)))
    fig.add_trace(go.Scatter(
        x=orta, y=ileri, mode="lines+markers+text", name="ileri faiz — par getiriden",
        line=dict(color=CLARET, width=2.4), marker=dict(size=10, symbol="diamond"),
        text=[f"%{_vir(o, 2)}" for o in ileri],
        textposition="bottom center", textfont=dict(size=12)))
    fig.add_trace(go.Scatter(
        x=orta, y=sifir, mode="lines+markers+text",
        name="ileri faiz — bootstrap edilmiş sıfır getiriden",
        line=dict(color=MUREKKEP, width=1.8, dash="dash"),
        marker=dict(size=9, symbol="diamond-open"),
        text=[f"%{_vir(o, 2)}" for o in sifir],
        textposition="top center", textfont=dict(size=11, color=MUREKKEP)))
    for o, (_, _, ad) in zip(orta, donem):
        fig.add_annotation(x=_xlog(o), y=3.95, text=ad, showarrow=False,
                           font=dict(size=10, color=MUREKKEP))
    fig.update_xaxes(type="log", tickvals=[v for v, _ in ABD_EGRI], ticktext=ABD_ETIKET,
                     title_text="vade")
    fig.update_yaxes(title_text="faiz (%)", range=[3.4, 6.35])
    fig.update_layout(title=dict(
        text="Şekil 03 — İma edilen ileri faizler tepe bandının üzerinde"
             "<br><sub>11 Eylül 2026 · patika varsayımı taşımaz · par tabanı yukarı eğimli eğride ileri faizi KÜÇÜK gösterir</sub>"))
    _yaz(fig, "03_ileri.html")


def sekil_04_fedwatch() -> None:
    """Vadeli piyasanın kendi dağılımı: olasılık ısı haritası + beklenen patika."""
    g = [ad for ad, _ in FW]
    bekl = fw_beklenen()
    z = [[(p[i] if i < len(p) and p[i] is not None else None) for _, p in FW]
         for i in range(len(FW_ORTA))]

    fig = go.Figure()
    fig.add_trace(go.Heatmap(
        x=g, y=FW_ORTA, z=z, zmin=0, zmax=90,
        colorscale=[[0, "#ffffff"], [0.12, "#f0e2e4"], [0.4, "#d09aa1"], [1, CLARET]],
        xgap=2, ygap=2, hoverongaps=False,
        colorbar=dict(title=dict(text="olasılık<br>(%)", side="top"), thickness=12,
                      len=0.55, y=0.5, tickvals=[0, 30, 60, 90]),
        hovertemplate="%{x} · %{y:.3f}%<br>olasılık %{z:.1f}%<extra></extra>"))
    fig.add_hrect(y0=FW_BANT[0], y1=FW_BANT[1], line_width=0, fillcolor=MAVI, opacity=0.16,
                  annotation_text="ÖLÇÜLEN vade primiyle tepe bandı %4,66–4,89 (3. bölüm)",
                  annotation_position="top left", annotation_font=dict(size=11, color=MAVI))
    fig.add_trace(go.Scatter(
        x=g, y=bekl, mode="lines+markers", name="beklenen (olasılık ağırlıklı) faiz",
        line=dict(color=MUREKKEP, width=2.6), marker=dict(size=7, color=MUREKKEP)))
    fig.add_hline(y=SOFR, line=dict(color=GRI, width=1.4, dash="dot"),
                  annotation_text="bugünkü gecelik çıpa", annotation_position="bottom right",
                  annotation_font=dict(size=11, color=GRI))
    fig.update_xaxes(title_text="FOMC toplantısı", tickangle=-45)
    fig.update_yaxes(title_text="hedef aralık orta noktası (%)",
                     tickvals=FW_ORTA, ticktext=[f"%{_vir(v, 3)}" for v in FW_ORTA])
    fig.update_layout(title=dict(
        text="Şekil 04 — Vadeli piyasanın fiyatladığı politika faizi dağılımı"
             f"<br><sub>CME FedWatch, {FW_TARIH} · renk o toplantıda o aralığın olasılığı · "
             "siyah çizgi olasılık ağırlıklı beklenti</sub>"))
    _yaz(fig, "04_fedwatch.html", 520)


def sekil_05_dagilim() -> None:
    """Zirvedeki dağılım SOLA çarpık: aşağı alan yukarı alandan geniş."""
    _, p = FW[8]                                    # 15.09.2027
    bekl = fw_beklenen()[8]
    mod = max(range(len(p)), key=lambda i: p[i] if p[i] is not None else -1)
    alt = sum(x for i, x in enumerate(p) if x and i < mod)
    ust = sum(x for i, x in enumerate(p) if x and i > mod)

    renk = [GRI if i < mod else (CLARET if i == mod else MAVI) for i in range(len(p))]
    fig = go.Figure(go.Bar(
        x=[f"%{_vir(v, 3)}" for v in FW_ORTA], y=p, marker_color=renk,
        text=[f"%{_vir(x, 1)}" if x else "" for x in p],
        textposition="outside", cliponaxis=False,
        hovertemplate="orta nokta %{x}<br>olasılık %{y:.1f}%<extra></extra>"))
    fig.add_vline(x=mod, line=dict(color=CLARET, width=1.2, dash="dot"))
    fig.add_annotation(x=mod, y=36.4, showarrow=False, font=dict(size=12, color=CLARET),
                       text=f"mod: 4 adım · %{_vir(FW_ORTA[mod], 3)}")
    fig.add_annotation(x=1.4, y=26, showarrow=False, font=dict(size=12, color=GRI),
                       text=f"moddan AŞAĞI<br>toplam %{_vir(alt, 1)}")
    fig.add_annotation(x=6.6, y=26, showarrow=False, font=dict(size=12, color=MAVI),
                       text=f"moddan YUKARI<br>toplam %{_vir(ust, 1)}")
    fig.update_xaxes(title_text="hedef aralık orta noktası (%)")
    fig.update_yaxes(title_text="olasılık (%)", range=[0, 40])
    fig.update_layout(showlegend=False, title=dict(
        text=("Şekil 05 — Zirvedeki dağılım aşağı doğru geniş, yukarı doğru dar"
              f"<br><sub>15 Eylül 2027 toplantısı · CME FedWatch, {FW_TARIH} · "
              f"ortalama %{_vir(bekl)} mod'un altında kalıyor</sub>")))
    _yaz(fig, "05_dagilim.html", 470)


def sekil_06_tarihce() -> None:
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
        text="Şekil 06 — Eğri ağustos sonundan bu yana yukarı kaydı"
             "<br><sub>22 Ağustos – 10 Eylül 2026 · ölçüm bir önceki kapanışa aittir · 2 yıllık seri sapmalı olduğu için dışarıda</sub>"))
    _yaz(fig, "06_tarihce.html")


def sekil_07_senaryo() -> None:
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
                      title=dict(text="Şekil 07 — 2 yıllık getirinin senaryo yelpazesi"
                                      "<br><sub>Çıpa: %4,63 (11.09.2026) · yukarı alan 7–42 bp, aşağı alan 48–93 bp</sub>"))
    _yaz(fig, "07_senaryo.html", 440)


def sekil_08_ayristirma() -> None:
    """10 yıllığın içinde politika beklentisi ile vade primi."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=["10 yıllık getiri"], y=[3.50], name="beklenen ortalama gecelik faiz (~%3,50)",
                         marker_color=MAVI, text=["%3,50"], textposition="inside"))
    fig.add_trace(go.Bar(x=["10 yıllık getiri"], y=[1.48], name="artık: vade primi (~148 bp)",
                         marker_color=CLARET, text=["148 bp"], textposition="inside"))
    fig.update_layout(barmode="stack", bargap=0.62,
                      title=dict(text="Şekil 08 — %4,98'in içinde ne var"
                                      "<br><sub>11 Eylül 2026 · nötr faiz %3,00–3,50 varsayımından artık olarak · ±50 bp hata payı</sub>"))
    fig.update_yaxes(title_text="getiri (%)", range=[0, 5.6])
    fig.add_annotation(x=0, y=4.98, text="%4,98", showarrow=False, yshift=16,
                       font=dict(size=14, color=MUREKKEP))
    _yaz(fig, "08_ayristirma.html", 440)


def sekil_09_tr_abd() -> None:
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
                      title=dict(text="Şekil 09 — İki eğri ters yöne bakıyor"
                                      "<br><sub>ABD 11.09.2026 · TL 10.09.2026 · kesikli çizgiler gecelik çıpa ve politika faizi</sub>"))
    _yaz(fig, "09_tr_abd.html", 480)


if __name__ == "__main__":
    print("▶ Fed analizi şekilleri")
    sekil_01_egri()
    sekil_02_patika()
    sekil_03_ileri()
    sekil_04_fedwatch()
    sekil_05_dagilim()
    sekil_06_tarihce()
    sekil_07_senaryo()
    sekil_08_ayristirma()
    sekil_09_tr_abd()
    _damga_denetle()
    _eksen_denetle()
    print("  9 şekil yazıldı — ev stili için: python3 site/tools/plotly_stil.py <dosyalar>")
