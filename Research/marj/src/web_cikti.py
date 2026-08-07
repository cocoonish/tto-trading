# -*- coding: utf-8 -*-
"""Plotly web çıktısı — TTO Trading proje sayfası için.

src/grafikler.py 14 adet matplotlib PNG üretir (yerel/ofline referans). Bu modül
AYNI serileri site konvansiyonuyla (Plotly, ev stili, CDN'den plotly.js) yeniden
çizer ve output/web/ altına yazar. Bilgi kaybı olmaması için PNG'lerin taşıdığı
her seri burada da var; yakın akraba paneller tek grafikte birleştirildi
(ör. dört konseptin maliyet endeksi tek şekilde, seçmeli değil üst üste).

Kaynak: output/seriler.xlsx sekmeleri (analiz.py üretir). Ham veriye dokunulmaz.
"""
import os
import pandas as pd
import plotly.graph_objects as go

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
XLSX = os.path.join(BASE, "output", "seriler.xlsx")
CIKTI = os.path.join(BASE, "output", "web")

# Ev stili — site/tools/plotly_stil.py ile aynı jetonlar
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
PALET = [TEAL, CLARET, GOLD, "#2f4b7c", "#665191", "#a05195", "#7a9e7e"]

KONSEPT_AD = {
    "ev_yemekleri": "Ev yemekleri",
    "kirmizi_et": "Kırmızı et",
    "tavuk": "Tavuk",
    "fast_food": "Fast-food",
}


def _duzen(fig, baslik, y_baslik, alt_not=""):
    """Ev stili: başlık solda, lejant altta yatay, beyaz zemin, responsive."""
    fig.update_layout(
        title=dict(text=baslik, x=0, xanchor="left",
                   font=dict(size=15, color=INK, family="Georgia, serif")),
        yaxis_title=y_baslik,
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Georgia, serif", size=12, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
        margin=dict(l=60, r=20, t=52, b=80),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor=GRID),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, automargin=True)
    if alt_not:
        fig.add_annotation(text=alt_not, xref="paper", yref="paper", x=0, y=-0.28,
                           showarrow=False, xanchor="left",
                           font=dict(size=10, color="#6b6b6b"))
    return fig


def _yaz(fig, ad):
    os.makedirs(CIKTI, exist_ok=True)
    yol = os.path.join(CIKTI, ad)
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazildi: {yol}")
    return yol


def _oku(sekme):
    d = pd.read_excel(XLSX, sheet_name=sekme, index_col=0)
    try:
        d.index = pd.to_datetime(d.index)
    except (ValueError, TypeError):
        pass
    return d


def uret():
    yollar = []

    # --- 01: Fiyat/maliyet oranı — dört konsept (PNG 09-13'ün özü) ---
    oran = _oku("Fiyat_maliyet_orani")
    fig = go.Figure()
    for i, k in enumerate(["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"]):
        if k in oran.columns:
            fig.add_trace(go.Scatter(x=oran.index, y=oran[k], name=KONSEPT_AD[k],
                                     line=dict(color=PALET[i], width=2)))
    fig.add_hline(y=1.0, line=dict(color=INK, width=1, dash="dot"))
    _duzen(fig, "Fiyat / maliyet oranı — dört konsept (2013 Ocak = 1)", "oran",
           "1,0 çizgisi 2013 Ocak çıpası. Oran kâr marjı SEVİYESİ değil, o çıpaya göre göreli seviyedir.")
    yollar.append(_yaz(fig, "oran_konseptler.html"))

    # --- 02: Konsept maliyet endeksleri (PNG 05-08) ---
    mal = _oku("Konsept_maliyet")
    fig = go.Figure()
    for i, k in enumerate([c for c in mal.columns if c in KONSEPT_AD]):
        fig.add_trace(go.Scatter(x=mal.index, y=mal[k], name=KONSEPT_AD[k],
                                 line=dict(color=PALET[i], width=2)))
    _duzen(fig, "Konsept maliyet endeksleri (2013 Ocak = 100)", "endeks",
           "Ağırlıklar: %21 işgücü · %49 gıda · %5 enerji · %10 kira · %15 diğer (notun Tablo 4'ü).")
    fig.update_yaxes(type="log")
    yollar.append(_yaz(fig, "maliyet_endeksleri.html"))

    # --- 03: Konsept fiyat endeksleri ---
    fiy = _oku("Konsept_fiyat")
    fig = go.Figure()
    for i, k in enumerate([c for c in fiy.columns if c in KONSEPT_AD]):
        fig.add_trace(go.Scatter(x=fiy.index, y=fiy[k], name=KONSEPT_AD[k],
                                 line=dict(color=PALET[i], width=2)))
    _duzen(fig, "Konsept fiyat endeksleri (2013 Ocak = 100)", "endeks",
           "Nisan 2022 sonrası madde fiyatı yayını durduğu için COICOP-2018 5'li grup endeksleriyle uzatıldı (PROXY 2).")
    fig.update_yaxes(type="log")
    yollar.append(_yaz(fig, "fiyat_endeksleri.html"))

    # --- 04: Maliyet bileşenleri (işgücü/gıda/enerji/kira/diğer) ---
    bil = _oku("Maliyet_bilesenleri")
    fig = go.Figure()
    for i, c in enumerate(bil.columns):
        fig.add_trace(go.Scatter(x=bil.index, y=bil[c], name=str(c),
                                 line=dict(color=PALET[i % len(PALET)], width=2)))
    _duzen(fig, "Maliyet bileşenleri (2013 Ocak = 100)", "endeks",
           "İşgücü: brüt asgari ücret · Kira: TÜFE-kira (duyarlılıkta Yeni Kiracı Kira Endeksi) · Enerji ve diğer: TÜFE alt kalemleri.")
    fig.update_yaxes(type="log")
    yollar.append(_yaz(fig, "maliyet_bilesenleri.html"))

    # --- 05: Katkı ayrıştırması (Tem-24 → Tem-26) yığılı bar ---
    kat = pd.read_csv(os.path.join(BASE, "output", "katki_ayristirma.csv"), index_col=0)
    kalemler = [c for c in kat.columns if c.upper() != "TOPLAM"]
    fig = go.Figure()
    for i, c in enumerate(kalemler):
        fig.add_trace(go.Bar(x=[KONSEPT_AD.get(k, k) for k in kat.index],
                             y=kat[c], name=str(c).capitalize(),
                             marker_color=PALET[i % len(PALET)]))
    fig.update_layout(barmode="stack")
    _duzen(fig, "Maliyet artışının kalem katkıları, Tem-2024 → Tem-2026", "puan",
           "Toplam sütun yüksekliği iki yıllık maliyet artışıdır (%).")
    yollar.append(_yaz(fig, "katki_ayristirma.html"))

    # --- 06: Food-cost oranları (çıpasız doğrulama) ---
    fc = pd.read_csv(os.path.join(BASE, "output", "food_cost_orani.csv"), index_col=0)
    fc.index = pd.to_datetime(fc.index)
    fig = go.Figure()
    for i, c in enumerate(fc.columns):
        fig.add_trace(go.Scatter(x=fc.index, y=fc[c], name=str(c),
                                 line=dict(color=PALET[i % len(PALET)], width=1.8)))
    _duzen(fig, "Food-cost oranı — porsiyon gramajıyla, çıpasız", "%",
           "Gıda maliyeti / satış fiyatı. Çıpa varsayımı içermez; oranın düşmesi marjın genişlemesi yönünde kanıttır.")
    yollar.append(_yaz(fig, "food_cost.html"))

    # --- 07: İma edilen kârlılık — merkez senaryo ve bant ---
    try:
        merkez = _oku("Ima_marj_%22.5_merkez")
        fig = go.Figure()
        for i, c in enumerate([x for x in merkez.columns if x in KONSEPT_AD]):
            fig.add_trace(go.Scatter(x=merkez.index, y=merkez[c], name=KONSEPT_AD[c],
                                     line=dict(color=PALET[i], width=2)))
        _duzen(fig, "İma edilen satış kârlılığı — merkez senaryo (m₀ = %22,5)", "%",
               "marj(t) = 1 − (1−m₀)·R̄/R(t). Mekanik türetimdir: kalite ve kompozisyon değişimini de 'marj' sayar.")
        yollar.append(_yaz(fig, "ima_marj.html"))
    except Exception as exc:
        print(f"  UYARI: ima marj grafigi atlandi: {exc}")

    # --- 08: Duyarlılık — 18 koşuda güncel oran dağılımı ---
    duy = pd.read_csv(os.path.join(BASE, "output", "duyarlilik.csv"))
    fig = go.Figure()
    for i, k in enumerate(["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"]):
        kol = f"oran26_{k}"
        if kol in duy.columns:
            fig.add_trace(go.Box(y=duy[kol], name=KONSEPT_AD[k],
                                 marker_color=PALET[i], boxpoints="all", jitter=0.4))
    _duzen(fig, "Duyarlılık: 18 senaryoda Temmuz 2026 fiyat/maliyet oranı", "oran",
           "3 ağırlık seti × 3 kira göstergesi × tür kaması açık/kapalı. Dar kutu = bulgunun varsayımlara dayanıklı olduğu.")
    yollar.append(_yaz(fig, "duyarlilik.html"))

    print(f"\n{len(yollar)} grafik uretildi.")
    return yollar


if __name__ == "__main__":
    uret()
