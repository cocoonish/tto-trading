# -*- coding: utf-8 -*-
"""El Niño hattı — GRAFİK katmanı (Plotly, ev stili).

Dört şekil. Üçüncüsü ve dördüncüsü bilerek yan yana durur: biri ilişkinin
gecikme profilini gösterir ama kalıcılık yanlısıdır, diğeri o yanlılıktan
geçmeyen epizot kanıtını verir. Okur ikisini birlikte görmeli.
"""
from __future__ import annotations

import json
import pathlib

import plotly.graph_objects as go

PROJE = pathlib.Path(__file__).resolve().parent
DATA = PROJE / "data"
CIKTI = PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

INK = "#211b12"; GRID = "#d9d2c2"; CLARET = "#8e1f2f"; TEAL = "#1d5c5c"
GOLD = "#9a7327"; INDIGO = "#34456e"; PLUM = "#6d3a5d"


def _duzen(fig, baslik, alt, h=470, y_baslik=""):
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
        margin=dict(l=64, r=64, t=ust, b=110), hovermode="x unified", bargap=0.15,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=INK,
                     zerolinewidth=1.1, automargin=True, title_text=y_baslik)
    return fig


def _yaz(fig, ad):
    fig.write_html(CIKTI / ad, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}")


def sekil_01(M, oni_tam):
    x = [k["ay"] for k in oni_tam]
    v = [k["oni"] for k in oni_tam]
    fig = go.Figure()
    fig.add_bar(x=x, y=[max(0, z) if z is not None else None for z in v],
                name="El Niño (ONI > 0)", marker_color=CLARET)
    fig.add_bar(x=x, y=[min(0, z) if z is not None else None for z in v],
                name="La Niña (ONI < 0)", marker_color=TEAL)
    for esik, ad in ((1.5, "güçlü"), (2.0, "çok güçlü")):
        fig.add_hline(y=esik, line=dict(color=INK, width=1, dash="dot"),
                      annotation_text=ad, annotation_position="right",
                      annotation_font=dict(size=10, color=INK))
    _duzen(fig, "Oceanic Niño Index — 1950'den bugüne",
           ["Niño 3.4 bölgesi deniz yüzeyi sıcaklık anomalisinin üç aylık kayan "
            "ortalaması (°C). Etiket ortadaki aya karşılık gelir.",
            f"Son ölçüm {M['oni_son_ay']}: {M['oni_son']:+.2f} °C. "
            "Kaynak: NOAA Climate Prediction Center."],
           h=430, y_baslik="°C")
    fig.update_layout(barmode="relative")
    _yaz(fig, "01-oni-tarihce.html")


def sekil_02(M):
    t = M["tarihce"]
    x = [k["ay"] for k in t]
    fig = go.Figure()
    fig.add_scatter(x=x, y=[k["goreceli_gida"] for k in t], name="Göreceli gıda enflasyonu (sağ)",
                    mode="lines", line=dict(color=CLARET, width=2), yaxis="y2")
    fig.add_scatter(x=x, y=[k["oni"] for k in t], name="ONI (sol)",
                    mode="lines", line=dict(color=INDIGO, width=1.6))
    fig.update_layout(yaxis=dict(title="ONI, °C", gridcolor=GRID),
                      yaxis2=dict(title="puan", overlaying="y", side="right",
                                  showgrid=False, zeroline=False))
    _duzen(fig, "El Niño ile Türkiye'de gıdanın göreceli fiyatı",
           ["Göreceli gıda enflasyonu = gıda yıllık enflasyonu − manşet TÜFE yıllık. "
            "Ortak parasal trend iki taraftan da düşer;",
            "geriye gıdayı sepetin geri kalanından AYRIŞTIRAN şok kalır — ENSO'nun "
            "iddia ettiği kanal budur.",
            "Kaynak: NOAA CPC (ONI), TCMB EVDS / TÜİK (TÜFE)."],
           h=470)
    _yaz(fig, "02-oni-goreceli-gida.html")


def sekil_03(M):
    fig = go.Figure()
    # Örneklem aynıysa tek eğri: iki kez çizmek sahte sağlamlık izlenimi verir.
    seriler = ([("modern", f"{M.get('orneklem_bas','')} → {M.get('orneklem_son','')}", CLARET)]
               if M.get("orneklem_ayni")
               else [("modern", "2005'ten bugüne", CLARET), ("tam", "tam örneklem", GOLD)])
    for etiket, ad, renk in seriler:
        c = M.get(f"capraz_{etiket}")
        if not c:
            continue
        fig.add_scatter(x=[d["gecikme"] for d in c], y=[d["korelasyon"] for d in c],
                        name=ad, mode="lines+markers",
                        line=dict(color=renk, width=2), marker=dict(size=5))
    en = M.get("capraz_modern_en_iyi_gecikme")
    if en is not None:
        fig.add_vline(x=en, line=dict(color=INK, width=1.2, dash="dot"),
                      annotation_text=f"en güçlü: {en} ay",
                      annotation_font=dict(size=11, color=INK))
    _duzen(fig, "Gecikme profili — ONI kaç ay sonra gıdaya vuruyor",
           ["Yatay eksen: ONI'nin kaç ay ÖNCEKİ değeri alındığı. Dikey eksen: o "
            "gecikmedeki korelasyon.",
            "UYARI: iki seri de kalıcı olduğundan katsayılar YUKARI YANLIDIR ve tek "
            "başına kanıt sayılmaz; şekil yalnız gecikmenin NEREDE olduğunu gösterir.",
            "Kanıt için Şekil 04'e bakınız."],
           h=450, y_baslik="korelasyon")
    _yaz(fig, "03-gecikme-profili.html")


def sekil_04(M):
    kayit = M.get("epizot_sonrasi") or []
    if not kayit:
        return
    fig = go.Figure()
    fig.add_bar(x=[k["zirve"] for k in kayit], y=[k["goreceli_gida_ort"] for k in kayit],
                marker_color=[CLARET if k["goreceli_gida_ort"] > 0 else TEAL for k in kayit],
                text=[f"{k['goreceli_gida_ort']:+.1f}".replace(".", ",") for k in kayit],
                textposition="outside", cliponaxis=False, showlegend=False,
                customdata=[k["zirve_oni"] for k in kayit],
                hovertemplate="zirve %{x}<br>ONI %{customdata:+.2f} °C"
                              "<br>sonraki 18 ay göreceli gıda %{y:+.2f} puan<extra></extra>")
    fig.add_hline(y=M["kosulsuz_ortalama"], line=dict(color=INK, width=1.4, dash="dot"),
                  annotation_text=f"koşulsuz ortalama {M['kosulsuz_ortalama']:+.2f}".replace(".", ","),
                  annotation_position="top left", annotation_font=dict(size=11))
    _duzen(fig, "Epizot çalışması — güçlü El Niño zirvelerinden sonraki 18 ay",
           ["Her çubuk bir güçlü El Niño epizodunun (ONI ≥ 1,5 °C, en az beş ay) "
            "zirvesinden sonraki 18 ayda",
            "göreceli gıda enflasyonunun ortalamasıdır. Noktalı çizgi bütün "
            "dönemlerin ortalaması.",
            "Kalıcılık yanlılığı bu ölçütten GEÇMEZ — tezin dayandığı kanıt budur."],
           h=470, y_baslik="puan")
    _yaz(fig, "04-epizot.html")


def main() -> int:
    import pandas as pd
    M = json.loads((DATA / "metrik.json").read_text(encoding="utf-8"))
    oni = pd.read_csv(DATA / "oni.csv", index_col=0, parse_dates=True)["oni"]
    oni_tam = [{"ay": f"{t:%Y-%m}", "oni": None if pd.isna(v) else round(float(v), 2)}
               for t, v in oni.items()]
    print("── El Niño hattı · grafikler")
    sekil_01(M, oni_tam)
    sekil_02(M)
    sekil_03(M)
    sekil_04(M)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
