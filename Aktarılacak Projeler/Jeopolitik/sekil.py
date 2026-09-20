#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JEOPOLİTİK ENERJİ ŞOKU — analiz figürleri.

Bu bir HAT DEĞİL, tek bir analizin ölçüm ve çizim katmanı. Panolar canlıdır,
analizler yayımlandıkları günün metnidir (karar 08.09.2026) — o yüzden
figürler `site/public/analiz/<slug>/` altına, DONMUŞ olarak yazılır ve
sayfa damgası basmaz. Hat figürlerinden ayrı tutulmasının sebebi budur:
`/projeler/` altındaki her figür sayfa sınavının şekil saat defterine
girer ve her koşuda tazelenmesi beklenir; bunlar tazelenmez.

GİRDİ TEK YERDEN: `olcum.py`. Sayıyı üreten yer tektir — figür ile metin
iki ayrı hesaptan beslenseydi bir gün sessizce ayrışırdı. Ölçümün kendi
girdisi de tek dosya: `veri/defter.json`, keşif koşusunun arşivi. Her
çizimde yeniden indirilen bir seri figürü kaynağın o günkü hâline
bağımlı kılar.

Koşum:  python3 "Aktarılacak Projeler/Jeopolitik/sekil.py"
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
SLUG = "hurmuz-rusya-enerji-2026-09-20"
CIKTI = KOK / "site/public/analiz" / SLUG
VERI = BURASI / "veri"

sys.path.insert(0, str(KOK / "ortak"))
sys.path.insert(0, str(BURASI))
import bicim  # noqa: E402
import olcum  # noqa: E402

# Ev paleti — site jetonlarıyla aynı (global.css: --claret, --ink).
MUREKKEP = "#1a1a1a"
CLARET = "#8b1e3f"
MAVI = "#2f5d8a"
GRI = "#9a9a9a"
ACIK = "#d9d9d9"
YESIL = "#4a7c59"
KEHRIBAR = "#c08a2e"


def _duzen(f: go.Figure, baslik: str, alt: str, y_baslik: str = "",
           yuksek: int = 430) -> go.Figure:
    f.update_layout(
        title=dict(text=f"<b>{baslik}</b><br><span style='font-size:12px;color:#666'>{alt}</span>",
                   x=0, xanchor="left", font=dict(size=15, color=MUREKKEP)),
        height=yuksek, margin=dict(l=62, r=24, t=76, b=54),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="IBM Plex Mono, ui-monospace, monospace", size=11, color=MUREKKEP),
        legend=dict(orientation="h", y=-0.17, x=0, font=dict(size=10)),
        hovermode="x unified")
    f.update_xaxes(showgrid=False, linecolor=ACIK, ticks="outside", tickcolor=ACIK)
    f.update_yaxes(title=y_baslik, gridcolor="#eee", zeroline=False,
                   linecolor=ACIK, ticks="outside", tickcolor=ACIK)
    return f


def _yaz(f: go.Figure, ad: str) -> None:
    CIKTI.mkdir(parents=True, exist_ok=True)
    f.write_html(CIKTI / ad, include_plotlyjs="cdn", full_html=True,
                 config={"displayModeBar": False, "responsive": True})
    print(f"  ✓ {ad}")


# ── veri ──────────────────────────────────────────────────────────────────
def enerji(E) -> tuple[list[str], dict[str, list[float]]]:
    """Figürler yazının veri gününde BİTER: 18.09 vade devri günü ve o gün
    iki bağımsız indirme farklı sözleşmeyi gösteriyor (ölçüldü). Bir figür
    yazının anlatmadığı bir günü çizmemeli."""
    g = [x for x in E.gunler if x <= olcum.SON_GUN]
    return g, {
        "brent": [E.BZ[t] for t in g], "wti": [E.CL[t] for t in g],
        "distilat": [E.distilat(t) for t in g],
        "benzin": [E.benzin(t) for t in g],
        "crack321": [E.c321(t) for t in g],
        "ho_urun": [E.urun(t) for t in g],
    }


# ── figürler ──────────────────────────────────────────────────────────────
def sekil_01(g, E):
    """Rafineri marjı: distilat crack'in bir yıllık seyri, rejim işaretli."""
    f = go.Figure()
    f.add_trace(go.Scatter(x=g, y=E["distilat"], name="Distilat crack (HO−WTI)",
                           line=dict(color=CLARET, width=2)))
    f.add_trace(go.Scatter(x=g, y=E["benzin"], name="Benzin crack (RBOB−WTI)",
                           line=dict(color=MAVI, width=1.6)))
    f.add_trace(go.Scatter(x=g, y=E["crack321"], name="3:2:1 rafineri marjı",
                           line=dict(color=GRI, width=1.4, dash="dot")))
    f.add_vline(x="2026-03-02", line=dict(color=MUREKKEP, width=1, dash="dash"))
    f.add_annotation(x="2026-03-02", y=max(E["distilat"]) * 0.97, text=" 2 Mart",
                     showarrow=False, xanchor="left", font=dict(size=10, color=MUREKKEP))
    _duzen(f, "Distilat marjı üç yıllık medyanın 3,4 katında",
           "Ham petrolden ürün üretmenin varil başına getirisi · ham ön vade kapanışları",
           "USD/varil")
    _yaz(f, "01_crack.html")


def sekil_02(g, E):
    """Ayrıştırma: distilat ürün fiyatının ne kadarı ham petrol, ne kadarı marj."""
    f = go.Figure()
    f.add_trace(go.Scatter(x=g, y=E["wti"], name="Ham petrol (WTI)", stackgroup="a",
                           line=dict(width=0), fillcolor="#c9d6e4"))
    f.add_trace(go.Scatter(x=g, y=E["distilat"], name="Rafineri marjı", stackgroup="a",
                           line=dict(width=0), fillcolor="#e4b9c6"))
    f.add_trace(go.Scatter(x=g, y=E["ho_urun"], name="Distilat ürün fiyatı",
                           line=dict(color=MUREKKEP, width=1.8)))
    _duzen(f, "Haziran'dan bu yana motorindeki artışın %72'si rafineri marjından",
           "Distilat ürün fiyatı = ham petrol + rafineri marjı · 1 varil = 42 galon",
           "USD/varil")
    _yaz(f, "02_ayristirma.html")


def sekil_03(P):
    """Hürmüz: aylık günlük ortalama geçiş ve tanker."""
    sat = olcum.hurmuz_aylik(P)
    ay = [r["ay"] for r in sat]
    f = go.Figure()
    f.add_trace(go.Bar(x=ay, y=[r["gemi"] for r in sat], name="Günlük toplam gemi",
                       marker_color=ACIK))
    f.add_trace(go.Bar(x=ay, y=[r["tanker"] for r in sat], name="Bunun tankeri",
                       marker_color=CLARET))
    f.add_vline(x=5.5, line=dict(color=MUREKKEP, width=1, dash="dash"))
    f.add_annotation(x=5.5, y=max(r["gemi"] for r in sat) * 0.96, text=" Mart 2026",
                     showarrow=False, xanchor="left", font=dict(size=10))
    _duzen(f, "Hürmüz Boğazı'nda günlük geçiş: Şubat 78, Mart 3",
           "Aylık ortalama günlük gemi sayısı · kaynak: IMF PortWatch günlük darboğaz sayımı",
           "gemi / gün")
    f.update_layout(barmode="overlay")
    _yaz(f, "03_hurmuz.html")


RENK_ROL = {"savas": CLARET, "savas_komsusu": KEHRIBAR, "rota": YESIL,
            "kontrol": GRI}


def sekil_04(P):
    """Yirmi sekiz darboğazın tamamı: hangisi çöktü, hangisi yerinde.

    Kontrol grubu elle seçilmiyor — kaynağın saydığı 28 darboğazın savaş
    rotasında olmayan hepsi. Eksen kırpılmıyor; Bering Boğazı'nın +%328'i
    MEVSİMSEL ve figürde görünür durması gerekiyor (kesilirse kontrol
    grubunun dağılımı olduğundan dar görünür)."""
    sat = olcum.darbogazlar(P)
    deg = [r["gemi_degisim"] for r in sat]
    f = go.Figure(go.Bar(
        x=deg, y=[r["ad"] for r in sat], orientation="h",
        marker_color=[RENK_ROL[r["rol"]] for r in sat],
        text=[bicim.yuzde(x, 1, isaret=True) for x in deg],
        textposition="outside", textfont=dict(size=9)))
    k = olcum.kontrol(P)
    _duzen(f, "Düşüş savaş rotasına özgü: 22 kontrol darboğazının medyanı "
           + bicim.yuzde(k["medyan"], 1, isaret=True),
           "Savaş öncesi ortalamaya göre günlük geçiş değişimi · kırmızı: çatışma "
           "bölgesi, turuncu: savaş rotası, yeşil: yükün kaydığı yol, gri: kontrol",
           "", 900)
    f.update_xaxes(title="değişim", ticksuffix="%",
                   range=[min(deg) - 14, max(deg) + 42])
    f.update_yaxes(tickfont=dict(size=9))
    _yaz(f, "04_darbogaz.html")


def sekil_05(g, E):
    """Ham petrol ile ürün marjının ayrışması — endeks."""
    i0 = g.index(olcum.TABAN_GUN)
    f = go.Figure()
    for ad, anah, renk in (("Brent ham petrol", "brent", MAVI),
                           ("Distilat rafineri marjı", "distilat", CLARET),
                           ("Benzin rafineri marjı", "benzin", KEHRIBAR)):
        taban = E[anah][i0]
        f.add_trace(go.Scatter(x=g[i0:], y=[v / taban * 100 for v in E[anah][i0:]],
                               name=ad, line=dict(color=renk, width=2)))
    f.add_hline(y=100, line=dict(color=ACIK, width=1))
    _duzen(f, "Şubat başı = 100: marj ham petrolün üç buçuk katı hızla açıldı",
           "Aynı tabana göre endekslenmiş seyir", "endeks (2 Şubat 2026 = 100)")
    _yaz(f, "05_endeks.html")


def main() -> int:
    print(f"Jeopolitik analiz figürleri → {CIKTI}")
    P = olcum.defter()
    g, E = enerji(olcum.Enerji(P))
    print(f"  enerji: {g[0]} → {g[-1]} ({len(g)} gün) · "
          f"darboğaz: {P['kapsam']['bas']} → {P['kapsam']['son_kayit']}")
    sekil_01(g, E)
    sekil_02(g, E)
    sekil_03(P)
    sekil_04(P)
    sekil_05(g, E)
    return 0


if __name__ == "__main__":
    sys.exit(main())
