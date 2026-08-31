# -*- coding: utf-8 -*-
"""Büyüme hattı — GRAFİK katmanı (Plotly, ev stili).

Dört şekil. Ev stili: başlık solda, lejant altta yatay, beyaz zemin,
include_plotlyjs="cdn" (gömülü plotly.js dosyayı ~4,6 MB yapıyor).

Şekil 02'de yığılmış çubukların toplamı ile ölçülen büyüme çizgisi AYNI
figürde duruyor: ayrışma varsa okur görür. Artık ayrı bir çubuk olarak
çiziliyor, bileşenlere dağıtılmıyor.
"""
from __future__ import annotations

import json
import pathlib

import plotly.graph_objects as go

PROJE = pathlib.Path(__file__).resolve().parent
DATA = PROJE / "data"
CIKTI = PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

INK = "#211b12"
GRID = "#d9d2c2"
CLARET = "#8e1f2f"
TEAL = "#1d5c5c"
GOLD = "#9a7327"
INDIGO = "#34456e"
PLUM = "#6d3a5d"
OLIVE = "#5a6b3a"


def _duzen(fig, baslik: str, alt: list[str], h: int = 460, y_baslik: str = ""):
    ust = 92 + 26 * len(alt) + 25
    metin = f"<b>{baslik}</b>" + "".join(f"<br><sup>{x}</sup>" for x in alt)
    fig.update_layout(
        title=dict(text=metin, x=0, xanchor="left", y=1.0, yanchor="top",
                   yref="container", pad=dict(t=14, l=0),
                   font=dict(size=15, color=INK, family="Georgia, serif")),
        height=h, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Georgia, serif", size=12, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0,
                    font=dict(size=11), bgcolor="rgba(255,255,255,0)"),
        margin=dict(l=64, r=48, t=ust, b=110),
        hovermode="x unified", bargap=0.15,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=INK,
                     zerolinewidth=1.1, automargin=True, title_text=y_baslik)
    return fig


def _yaz(fig, ad: str):
    fig.write_html(CIKTI / ad, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}")


def sekil_01(M):
    t = M["tarihce"]
    x = [k["ceyrek"] for k in t]
    fig = go.Figure()
    fig.add_bar(x=x, y=[k["ceyreklik"] for k in t], name="Çeyreklik (mevsim ve takvim ar.)",
                marker_color=GOLD, opacity=0.55)
    fig.add_scatter(x=x, y=[k["yillik"] for k in t], name="Yıllık (takvim ar.)",
                    mode="lines", line=dict(color=CLARET, width=2.4))
    son = t[-1]
    fig.add_scatter(x=[son["ceyrek"]], y=[son["yillik"]], mode="markers+text",
                    marker=dict(color=CLARET, size=9), showlegend=False,
                    text=[f"  %{son['yillik']:.1f}".replace(".", ",")],
                    textposition="middle right", textfont=dict(size=12, color=CLARET))
    _duzen(fig, "Büyüme patikası — yıllık ve çeyreklik",
           ["Yıllık oran takvim etkisinden arındırılmış zincirlenmiş hacim "
            "endeksinden; çeyreklik oran mevsim VE takvim arındırılmış endeksten.",
            f"Son gözlem {son['ceyrek']}. Kaynak: TCMB EVDS (TÜİK ulusal hesapları)."],
           h=470, y_baslik="%")
    _yaz(fig, "01-buyume-patikasi.html")


def sekil_02(M):
    k = M["katkilar"]
    sira = ["P311", "P32", "P51G", "P6", "P7", "P312"]
    renk = {"P311": CLARET, "P32": INDIGO, "P51G": TEAL, "P6": GOLD,
            "P7": PLUM, "P312": OLIVE}
    fig = go.Figure()
    for kod in sira:
        if kod not in k:
            continue
        v = k[kod]
        fig.add_bar(x=[v["ad"]], y=[v["katki"]], name=v["ad"],
                    marker_color=renk.get(kod, INK),
                    text=[f"{v['katki']:+.2f}".replace(".", ",")],
                    textposition="outside", cliponaxis=False)
    fig.add_bar(x=["Stok + zincirleme artığı"], y=[M["artik"]],
                name="Stok + zincirleme artığı", marker_color=GRID,
                marker_line=dict(color=INK, width=1),
                text=[f"{M['artik']:+.2f}".replace(".", ",")],
                textposition="outside", cliponaxis=False)
    fig.add_hline(y=M["buyume_yillik"], line=dict(color=INK, width=1.4, dash="dot"),
                  annotation_text=f"ölçülen büyüme %{M['buyume_yillik']:.1f}".replace(".", ","),
                  annotation_position="top right",
                  annotation_font=dict(size=11, color=INK))
    _duzen(fig, f"Yıllık büyümeye katkılar — {M['_ceyrek']}",
           ["Katkı = bileşenin bir yıl önceki CARİ fiyatlı GSYH payı × bileşenin "
            "reel yıllık büyümesi. İthalat kimlikte eksi girer.",
            "Zincirlenmiş hacim endeksleri toplanmadığı için artık ayrı çizilir: "
            "stok değişimi ve zincirleme tutarsızlığı. Bileşenlere DAĞITILMAZ.",
            f"Ağırlık dönemi {M['agirlik_donemi']}. Kaynak: TCMB EVDS."],
           h=520, y_baslik="puan")
    _yaz(fig, "02-katkilar.html")


def sekil_03(M):
    s = [v for v in M["sektorler"].values() if v.get("buyume") is not None]
    s.sort(key=lambda v: v["buyume"])
    fig = go.Figure()
    fig.add_bar(x=[v["buyume"] for v in s], y=[v["ad"] for v in s],
                orientation="h", marker_color=[CLARET if v["buyume"] < 0 else TEAL
                                               for v in s],
                text=[f"%{v['buyume']:.1f}".replace(".", ",")
                      + (f"  · pay %{v['agirlik']:.0f}".replace(".", ",")
                         if v.get("agirlik") else "")
                      for v in s],
                textposition="outside", cliponaxis=False, showlegend=False)
    _duzen(fig, f"Sektör büyümesi — {M['_ceyrek']}, yıllık",
           ["Üretim yöntemiyle, iktisadi faaliyet kollarına (A10) göre "
            "zincirlenmiş hacim; pay bir yıl önceki cari fiyatlı GSYH içindeki ağırlık.",
            "İmalat, sanayinin İÇİNDE yer alır — toplama iki kez girmez.",
            "Kaynak: TCMB EVDS (TÜİK ulusal hesapları)."],
           h=540, y_baslik="")
    fig.update_layout(margin=dict(l=210, r=110))
    fig.update_xaxes(title_text="%")
    _yaz(fig, "03-sektorler.html")


def sekil_04(M):
    d = M["dayaniklilik"]
    sira = ["P311", "P312", "P313", "P314"]
    ad = [d[k]["ad"] for k in sira if k in d]
    buy = [d[k]["nominal_buyume"] for k in sira if k in d]
    pay = [d[k]["pay"] for k in sira if k in d]
    fig = go.Figure()
    fig.add_bar(x=ad, y=buy, marker_color=[CLARET, GOLD, TEAL, INDIGO][:len(ad)],
                text=[f"%{b:.1f}".replace(".", ",") for b in buy],
                textposition="outside", cliponaxis=False, showlegend=False,
                customdata=pay,
                hovertemplate="%{x}<br>nominal büyüme %{y:.1f}%"
                              "<br>tüketim içindeki pay %{customdata:.1f}%<extra></extra>")
    _duzen(fig, f"Hanehalkı tüketimi, dayanıklılık türüne göre — {M['_ceyrek']}",
           ["CARİ fiyatlarla yayımlanıyor: buradaki oranlar NOMİNALDİR, reel "
            "büyüme değildir. Enflasyondan arındırılmamıştır.",
            "Faize en duyarlı kalem dayanıklı mal; kredi koşullarındaki "
            "değişim önce burada görünür.",
            "Kaynak: TCMB EVDS (TÜİK ulusal hesapları)."],
           h=490, y_baslik="% (nominal)")
    _yaz(fig, "04-dayaniklilik.html")


def main() -> int:
    M = json.loads((DATA / "metrik.json").read_text(encoding="utf-8"))
    print("── Büyüme hattı · grafikler")
    sekil_01(M)
    sekil_02(M)
    sekil_03(M)
    sekil_04(M)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
