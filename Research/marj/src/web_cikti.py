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

# Dönem etiketleri: 'güncel ay' ve 'iki yıl önce' VERİDEN okunur (seriler.xlsx'in
# son dolu ayı), sabit yazılmaz. veri.py'deki tanımla aynı; burada yinelenmesinin
# nedeni web_cikti'nin internetsiz/bağımsız koşabilmesi.
_AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
          7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
_AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
            7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def _ad_uzun(t):
    t = pd.Timestamp(t); return f"{_AY_TR[t.month]} {t.year}"


def _ad_kisa(t):
    t = pd.Timestamp(t); return f"{_AY_KISA[t.month]}-{t.year}"


def _donem(df):
    """(son, once): df'in son dolu ayı ve 24 ay öncesi (Timestamp)."""
    son = df.dropna(how="all").index[-1]
    return son, son - pd.DateOffset(months=24)

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
        # <br> iceren notlar iki satir: alt bosluk ve konum ona gore
        satir = alt_not.count("<br>") + 1
        fig.update_layout(margin=dict(l=60, r=20, t=52, b=80 + 16 * (satir - 1)))
        fig.add_annotation(text=alt_not, xref="paper", yref="paper", x=0,
                           y=-0.28 - 0.05 * (satir - 1),
                           showarrow=False, xanchor="left", align="left",
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

    # --- 05: Katkı ayrıştırması (iki yıl önce → güncel ay) yığılı bar ---
    kat = pd.read_csv(os.path.join(BASE, "output", "katki_ayristirma.csv"), index_col=0)
    _son, _once = _donem(_oku("Fiyat_maliyet_orani"))
    kalemler = [c for c in kat.columns if c.upper() != "TOPLAM"]
    fig = go.Figure()
    for i, c in enumerate(kalemler):
        fig.add_trace(go.Bar(x=[KONSEPT_AD.get(k, k) for k in kat.index],
                             y=kat[c], name=str(c).capitalize(),
                             marker_color=PALET[i % len(PALET)]))
    fig.update_layout(barmode="stack")
    _duzen(fig, f"Maliyet artışının kalem katkıları, {_ad_kisa(_once)} → {_ad_kisa(_son)}", "puan",
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
        kol = f"oran_son_{k}"
        if kol in duy.columns:
            fig.add_trace(go.Box(y=duy[kol], name=KONSEPT_AD[k],
                                 marker_color=PALET[i], boxpoints="all", jitter=0.4))
    _duzen(fig, f"Duyarlılık: {len(duy)} senaryoda {_ad_uzun(_son)} fiyat/maliyet oranı", "oran",
           "3 ağırlık seti × 3 kira göstergesi × tür kaması açık/kapalı. Dar kutu = bulgunun varsayımlara dayanıklı olduğu.")
    yollar.append(_yaz(fig, "duyarlilik.html"))

    print(f"\n{len(yollar)} grafik uretildi.")
    return yollar


# ─────────────────────────────────────────────────────────────────────────────
# Aşağıdaki dört grafik, matplotlib setindeki Grafik 1-4 ve 14'ün karşılığıdır.
# İlk sürümde atlanmışlardı; sayfadaki üç iddia (talep göstergeleri, "lokanta-
# oteller manşetle eşitlendi", konseptler arası ayrışma) doğrudan bunlara dayanır.
# Kaynak fonksiyonlar grafikler.py'de: hizmet_ciro_oku(), gida_yemek_haric_tufe().
# ─────────────────────────────────────────────────────────────────────────────

def _tufe_serileri():
    """Grafik 2-4'ün üç serisi: gıda+yemek hariç TÜFE, gıda, yemek hizmetleri."""
    import grafikler, veri
    evds = veri.tum_evds()
    return {
        "Gıda ve yemek hariç TÜFE": grafikler.gida_yemek_haric_tufe(evds),
        "Gıda ve alkolsüz içecekler": evds["gida_alkolsuz"],
        "Yemek hizmetleri": evds["yemek_111"],
    }


def uret_ek():
    """Grafik 1-4 ve 14'ün Plotly karşılıkları."""
    yollar = []
    RENK = [TEAL, CLARET, GOLD]

    # --- Hizmet ciro endeksi (PNG 01) ---
    try:
        import grafikler
        import numpy as np
        ciro = grafikler.hizmet_ciro_oku()
        # Veri ZATEN yillik ortalama (indeks = yil); resample YAPILMAZ.
        yillik = ciro.pct_change() * 100
        yillik.index = [int(y) for y in yillik.index]
        sut = [c for c in yillik.columns if str(c).split(" ")[0] in list("HIJLMN")][:6]
        etk = {c: str(c).split(" - ")[-1][:22] for c in sut}
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[etk[c] for c in sut], y=yillik.loc[2020, sut],
                             name="2020", marker_color=TEAL))
        fig.add_trace(go.Bar(x=[etk[c] for c in sut], y=yillik.loc[[2021, 2022], sut].mean(),
                             name="2021–2022 ort.", marker_color=CLARET))
        fig.update_layout(barmode="group")
        _duzen(fig, "Hizmet ciro endeksleri — yıllık % değişim", "%",
               "TÜİK Ticaret ve Hizmet Ciro Endeksleri (2015=100). Cari fiyatlarla, arındırılmamış endekslerin yıllık ortalamalarından.")
        yollar.append(_yaz(fig, "hizmet_ciro.html"))
    except Exception as exc:
        print(f"  UYARI: hizmet ciro grafigi atlandi: {exc}")

    # --- TÜFE üçlüsü: endeks / aylık / yıllık (PNG 02-04) ---
    try:
        ser = _tufe_serileri()
        baz = pd.Timestamp("2019-12-01")

        fig = go.Figure()
        for (ad, s), r in zip(ser.items(), RENK):
            sb = (s / s.loc[baz] * 100).loc["2019-12-01":]
            fig.add_trace(go.Scatter(x=sb.index, y=sb.values, name=ad, line=dict(color=r, width=2)))
        _duzen(fig, "TÜFE fiyat endeksleri (2019 Aralık = 100)", "endeks",
               "Gıda ve yemek hariç TÜFE, yıllık resmî ağırlıklarla zincirlenerek hesaplanmıştır.")
        yollar.append(_yaz(fig, "tufe_endeks.html"))

        fig = go.Figure()
        for (ad, s), r in zip(ser.items(), RENK):
            mm = (s.pct_change(fill_method=None) * 100).loc["2019-12-01":]
            fig.add_trace(go.Scatter(x=mm.index, y=mm.values, name=ad, line=dict(color=r, width=1.6)))
        _duzen(fig, "TÜFE fiyat endeksleri — aylık % değişim", "%")
        yollar.append(_yaz(fig, "tufe_aylik.html"))

        fig = go.Figure()
        for (ad, s), r in zip(ser.items(), RENK):
            yy = (s.pct_change(12, fill_method=None) * 100).loc["2019-12-01":]
            fig.add_trace(go.Scatter(x=yy.index, y=yy.values, name=ad, line=dict(color=r, width=2)))
        _duzen(fig, "TÜFE fiyat endeksleri — yıllık % değişim", "%",
               "Yemek hizmetleri ile manşet arasındaki farkın kapanması, akım fiyatlamada normalleşme sinyalidir.")
        yollar.append(_yaz(fig, "tufe_yillik.html"))
    except Exception as exc:
        print(f"  UYARI: TUFE grafikleri atlandi: {exc}")

    # --- Normalize oranlar, ev yemekleri = 1 (PNG 14) ---
    try:
        oran = _oku("Fiyat_maliyet_orani")
        uzun = oran.loc["2013-01-01":"2022-12-31"].mean()
        _son, _once = _donem(oran)
        t24 = oran.loc[_once]
        t26 = oran.loc[_son]
        ks = [k for k in ["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"] if k in oran.columns]
        etk = [KONSEPT_AD[k] for k in ks]
        fig = go.Figure()
        for ad, seri, renk in [("2013–2022 ort.", uzun, TEAL), (_ad_uzun(_once), t24, CLARET),
                               (_ad_uzun(_son), t26, GOLD)]:
            n = seri[ks] / seri["ev_yemekleri"]
            fig.add_trace(go.Bar(x=etk, y=n.values, name=ad, marker_color=renk,
                                 text=[f"{v:.2f}" for v in n.values], textposition="outside"))
        fig.update_layout(barmode="group")
        fig.add_hline(y=1.0, line=dict(color=INK, width=1, dash="dash"))
        _duzen(fig, "Fiyat/maliyet oranları — ev yemekleri = 1", "oran",
               "Konseptler arası ayrışma: 1'in üstü, o konseptin ev yemeklerinden daha çok açıldığını gösterir.")
        yollar.append(_yaz(fig, "oran_normalize.html"))
    except Exception as exc:
        print(f"  UYARI: normalize oran grafigi atlandi: {exc}")

    return yollar


def uret_konsept_oranlari():
    """PNG 09-12: her konsept icin AYRI oran grafigi.

    Birlesik grafikte (oran_konseptler.html) olmayan uc katman burada var:
      · konsepte ozgu 2013-2022 ortalama cizgisi, degeri etiketli
      · Nisan 2022 splice isareti (fiyat tarafi proxy'ye gectigi an)
      · iki yil once ve guncel ay noktalarinin isaretlenip etiketlenmesi
    """
    import endeks as _e
    ETIKET = {"kirmizi_et": "Kırmızı et ağırlıklı", "tavuk": "Tavuk eti ağırlıklı",
              "ev_yemekleri": "Ev yemekleri", "fast_food": "Fast-food"}
    RENK = {"ev_yemekleri": TEAL, "kirmizi_et": CLARET, "tavuk": GOLD, "fast_food": "#2f4b7c"}
    SPLICE = pd.Timestamp("2022-04-01")

    oran = _oku("Fiyat_maliyet_orani")
    uzun = oran.loc["2013-01-01":"2022-12-31"].mean()
    yollar = []

    for k in ["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"]:
        if k not in oran.columns:
            print(f"  UYARI: {k} sutunu yok, atlandi"); continue
        srs = oran[k].dropna()
        renk = RENK[k]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=srs.index, y=srs.values, name="Fiyat / maliyet",
                                 line=dict(color=renk, width=2.4)))
        # uzun donem ortalama
        ort = float(uzun[k])
        fig.add_hline(y=ort, line=dict(color="#90a4ae", width=1.4, dash="dash"),
                      annotation_text=f"2013–2022 ort. {ort:.2f}".replace(".", ","),
                      annotation_position="bottom right",
                      annotation_font=dict(size=11, color="#6b6b6b"))
        # splice isareti
        # add_vline'in annotation'i datetime ekseninde pandas ile catisiyor
        # (Timestamp + int); cizgi ile etiket AYRI eklenir.
        fig.add_shape(type="line", x0=SPLICE, x1=SPLICE, y0=0, y1=1, yref="paper",
                      line=dict(color="#90a4ae", width=1, dash="dot"))
        fig.add_annotation(x=SPLICE, y=1.02, yref="paper", showarrow=False,
                           text="Nis 2022: fiyat tarafı proxy'ye geçer",
                           xanchor="left", font=dict(size=10, color="#6b6b6b"))
        # iki kilit nokta: iki yıl önce ve güncel ay
        for ts in _donem(oran)[::-1]:
            if ts not in srs.index: continue
            v = float(srs.loc[ts])
            fig.add_trace(go.Scatter(x=[ts], y=[v], mode="markers+text",
                                     marker=dict(color=renk, size=9),
                                     text=[f"{v:.2f}".replace(".", ",")],
                                     textposition="top center",
                                     textfont=dict(color=renk, size=12),
                                     showlegend=False, hoverinfo="skip"))
        _duzen(fig, f"Fiyat / maliyet oranı — {ETIKET[k]} (2013 Ocak = 1)", "oran",
               "Oran kâr marjı SEVİYESİNİ göstermez; 2013 Ocak'a göre göreli seviyedir.<br>"
               "Nis 2022 sonrası fiyat tarafı 11111/11112 endeksleriyle uzatılmış proxy'dir.")
        yollar.append(_yaz(fig, f"oran_{k}.html"))
    return yollar


if __name__ == "__main__":
    y = uret()
    y += uret_ek()
    y += uret_konsept_oranlari()
    print(f"\nTOPLAM {len(y)} grafik.")
