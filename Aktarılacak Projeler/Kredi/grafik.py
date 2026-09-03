# -*- coding: utf-8 -*-
"""Kredi & parasal büyüklükler — grafik katmanı (Plotly, site ev stili).

Kurallar (site sözleşmesi):
  · Çok panelli figürlerde paneller ALT ALTA (rows=N, cols=1). Yan yana panel YOK.
  · Panel başına ~340 px + başlık/lejant payı; buradaki `height` MDX'teki
    `yukseklik={}` ile AYNI olmak zorunda — tek kaynak cikti/yukseklikler.json.
  · Başlık solda, iki satır: "<b>Başlık</b><br><sup>alt başlık</sup>".
  · Lejant altta yatay, beyaz zemin, include_plotlyjs="cdn",
    config: responsive=True, displaylogo=False.
  · Şekil numarası BELGE SIRASINI izler; dosya adı = şekil no (NN_ad.html).
  · Her grafiğin başlığında VERİ TARİHİ vardır (bayat grafik gözle görülür).
  · Bir figür üretilemezse hat DURUR — siteye kopyalama yapılmaz.

Koşum:  python3 grafik.py   (önce veri.py → metrik.py)
"""
from __future__ import annotations

import json
import pathlib
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import veri
from veri import VERI, ad_gun

CIKTI = veri.PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

# Ev stili jetonları — site/tools/plotly_stil.py ve diğer hatlarla aynı
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
LACI, MOR, YESIL, GRI = "#2f4b7c", "#665191", "#7a9e7e", "#8a8a8a"
PALET = [TEAL, CLARET, GOLD, LACI, MOR, "#a05195", YESIL, GRI]

PANEL_PX = 340
KAYNAK = "Kaynak: TCMB EVDS3"

# Pencereler. Haftalık kredi KIRILIMI 28.06.2024'te başlıyor; uzun tarihçe
# yalnız birleştirilmiş toplam seride var. Pencere sabitleri buradan okunur,
# panel başlıklarına düz metin yıl GÖMÜLMEZ.
UZUN_BAS = "2006-01-01"
ORTA_BAS = "2018-01-01"
YAKIN_BAS = "2024-06-01"
# Para arzı momentum panelleri için ayrı pencere: Aralık 2021 kur şokunda ham M2'nin
# 13 haftalık yıllıklandırılmış momentumu %300'ü aşıyor ve tüm tarihçeyi tek eksene
# koymak bugünkü %20–30 bandını okunamaz hâle getiriyordu (Enflasyon hattındaki
# MOM_BAS ile aynı gerekçe). Seviye ve çarpan panelleri ORTA_BAS'ta kalıyor.
PARA_BAS = "2022-07-01"


def _yil(tarih: str) -> int:
    return int(str(tarih)[:4])


# --------------------------------------------------------------------------- düzen
def _lejant_satir(fig) -> int:
    gorulen, toplam = set(), 0
    for tr in fig.data:
        if getattr(tr, "showlegend", None) is False:
            continue
        ad = getattr(tr, "name", "") or ""
        grup = getattr(tr, "legendgroup", None) or ad
        if grup in gorulen:
            continue
        gorulen.add(grup)
        toplam += len(ad) + 8
    return max(1, -(-toplam // 105))


def _duzen(fig, baslik: str, alt: list[str], n_panel: int,
           ek_yukseklik: int = 0) -> go.Figure:
    """Ev stili düzeni.

    Açıklama satırları BAŞLIK bloğunda (<sup>) taşınır, figür içi ek açıklama
    olarak DEĞİL: site/tools/plotly_stil.py çalışma zamanında legend.y=−0,1 ve
    margin.b=110 dayatıyor, uzun figürlerde sabit konumlu dipnot lejantın
    üstüne biniyor. Ev stili her <br> için üst marjı büyütüyor; çakışma olmuyor.
    """
    for satir in alt:
        if len(re.sub("<[^>]+>", "", satir)) > 155:
            print(f"    UYARI: alt başlık satırı {len(satir)} karakter, taşabilir: "
                  f"{satir[:60]}…")
    l_satir = _lejant_satir(fig)
    # ÜST MARJ İNCE AYARI: plotly_stil.py margin.t'yi önce 92'ye çeker, sonra
    # YALNIZCA mevcut değer gerekenden KÜÇÜKSE yükseltir. Doğru değeri buraya
    # yazmak ters teper; bir eksik yazılır, ev stili kendi hesabıyla yükseltir.
    ust = 92 + 26 * len(alt) + 25
    b = 110 + max(0, l_satir - 1) * 24
    h = PANEL_PX * n_panel + ust + b + ek_yukseklik
    baslik_metni = f"<b>{baslik}</b>" + "".join(f"<br><sup>{x}</sup>" for x in alt)
    fig.update_layout(
        title=dict(text=baslik_metni, x=0, xanchor="left",
                   font=dict(size=15, color=INK, family="Georgia, serif")),
        height=h,
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Georgia, serif", size=12, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.1, x=0,
                    font=dict(size=11), tracegroupgap=2,
                    bgcolor="rgba(255,255,255,0)"),
        margin=dict(l=64, r=64, t=ust, b=b),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor=GRID),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=GRID,
                     automargin=True)
    return fig


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


def _cizgi(fig, s: pd.Series, ad: str, renk: str, row=1, col=1, kalin=2.0,
           kesik=None, ikincil=None, doldur=None, gorunur=True, birim="%"):
    s = s.dropna()
    if s.empty:
        return
    ek = {}
    if ikincil is not None:
        ek["secondary_y"] = ikincil
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, name=ad, mode="lines", showlegend=gorunur,
        line=dict(color=renk, width=kalin, dash=kesik), fill=doldur,
        hovertemplate="%{y:,.2f}" + birim + "<extra>" + ad + "</extra>"),
        row=row, col=col, **ek)


def _sifir_cizgi(fig, row=1):
    fig.add_hline(y=0, line=dict(color=GRI, width=1), row=row, col=1)


def _kirilma(fig, tarih, row, metin="tanım değişikliği"):
    """Seri kırılmasını GÖRÜNÜR yap: iki farklı tanımın birleştiği hafta."""
    if tarih is None:
        return
    fig.add_vline(x=pd.Timestamp(tarih), line=dict(color=GRI, width=1, dash="dot"),
                  row=row, col=1)
    fig.add_annotation(x=pd.Timestamp(tarih), y=1, yref=f"y{'' if row == 1 else row} domain",
                       text=metin, showarrow=False, xanchor="left", yanchor="top",
                       font=dict(size=9, color=GRI), row=row, col=1)


# --------------------------------------------------------------------------- veri
def _yukle():
    M = pd.read_csv(VERI / "metrik_haftalik.csv", index_col=0, parse_dates=True)
    P = pd.read_csv(VERI / "para.csv", index_col=0, parse_dates=True)
    D = pd.read_csv(VERI / "dolarizasyon.csv", index_col=0, parse_dates=True)
    F = pd.read_csv(VERI / "faiz.csv", index_col=0, parse_dates=True)
    A = pd.read_csv(VERI / "metrik_aylik.csv", index_col=0, parse_dates=True)
    K = pd.read_csv(VERI / "kur.csv", index_col=0, parse_dates=True)
    AY = pd.read_csv(VERI / "ayristirma.csv", index_col=0, parse_dates=True)
    H = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    C = pd.read_csv(VERI / "ceyreklik.csv", index_col=0, parse_dates=True)
    U = (pd.read_csv(VERI / "uzun.csv", index_col=0, parse_dates=True)
         if (VERI / "uzun.csv").exists() else pd.DataFrame())
    CU = (pd.read_csv(VERI / "capraz_uzun.csv", index_col=0, parse_dates=True)
          if (VERI / "capraz_uzun.csv").exists() else pd.DataFrame())
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    return M, P, D, F, A, K, AY, H, C, U, CU, o


def _pen(s: pd.Series, bas: str) -> pd.Series:
    """Pencere sabitleri SUNUM tercihidir, ölçüm değil — ama serinin gerçek
    başlangıcının GERİSİNE düşmemeleri gerekir: düşerlerse eksen boş bir
    kuyruk çizer ve okur 'veri var ama sıfır' sanır."""
    if s.empty:
        return s
    bas_t = max(pd.Timestamp(bas), s.dropna().index[0]) if s.notna().any() \
        else pd.Timestamp(bas)
    return s[s.index >= bas_t]


def _kirilma_tr(o: dict, H: pd.DataFrame) -> str:
    """Haftalık kredi kırılımı tablosunun başlangıcı — VERİDEN.

    Bu tarih grafik notuna elle yazılırsa TCMB tabloyu revize ettiğinde not
    sessizce yanlışa döner. metrik_ozet.json'daki `uzun.kirilma` zaten
    veriden türetilmiş hâlde duruyor; yoksa panelin kendi ilk dolu haftası
    kullanılır.
    """
    t = (o.get("uzun") or {}).get("kirilma")
    if not t:
        kol = next((k for k in ("k_ticari_tl", "k_tuketici", "takip_toplam")
                    if k in H.columns and H[k].notna().any()), None)
        if kol is None:
            return "tablonun ilk haftası"
        t = H[kol].dropna().index[0]
    t = pd.Timestamp(t)
    return f"{t.day:02d}.{t.month:02d}.{t.year}"


# ===========================================================================
#  Şekil 01 — ANA GRAFİK: kur etkisinden arındırılmış kredi büyümesi
# ===========================================================================
def sekil_01(M, U, o, damga):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.11,
                        subplot_titles=(
                            "Kur etkisinden arındırılmış kredi büyümesi — toplam, TL ve YP "
                            "(13 haftalık, yıllıklandırılmış)",
                            f"Uzun tarihçe: toplam kredi, arındırılmış "
                            f"({_yil(UZUN_BAS)}→) — arşiv ve yeni tablolar büyüme oranı "
                            "düzeyinde birleştirildi"))
    _cizgi(fig, _pen(M["g_ar_13y"], YAKIN_BAS), "Toplam (arındırılmış)", TEAL, 1, kalin=2.6)
    _cizgi(fig, _pen(M["g_tl_13y"], YAKIN_BAS), "TL krediler", LACI, 1)
    _cizgi(fig, _pen(M["g_yp_ar_13y"], YAKIN_BAS),
           "YP krediler (döviz cinsinden)", GOLD, 1)
    _cizgi(fig, _pen(M["g_ar_52"], YAKIN_BAS), "Toplam, 52 haftalık (yıllık)",
           CLARET, 1, kalin=1.6, kesik="dash")
    _sifir_cizgi(fig, 1)
    if len(U):
        _cizgi(fig, _pen(U["g_ar_13y"], UZUN_BAS), "Toplam kredi (birleştirilmiş)",
               TEAL, 2, kalin=1.8)
        _cizgi(fig, _pen(U["g_ham_13y"], UZUN_BAS), "Ham (arındırılmamış)",
               GRI, 2, kalin=1.2, kesik="dot")
        _kirilma(fig, (o.get("uzun") or {}).get("kirilma"), 2, "tablo değişimi")
    _sifir_cizgi(fig, 2)
    fig.update_yaxes(title_text="%, yıllıklandırılmış", row=1, col=1)
    fig.update_yaxes(title_text="%, yıllıklandırılmış", row=2, col=1)
    return _duzen(fig, f"Kredi büyümesi — kur etkisinden arındırılmış · veri {damga}", [
        "Sıra bağlayıcı: önce haftalık arındırma, sonra zincirleme, sonra yıllıklandırma "
        "(13 haftalık bileşik, üs 52/13 = 4). Basit ölçekleme kullanılmaz.",
        "Kur: zorunlu karşılığa tabi DTH'dan ima edilen sepet (TP.ZORUNDTH.KB8/KB7).",
        "Kapsam: yurt içi yerleşiklere kullandırılan krediler · yurt içi şubeler · katılım bankaları DAHİL.",
        "TCMB'nin makro ihtiyati kredi büyüme sınırı çizilmez: referans kuru, oranı ve kapsamı "
        "tebliğde belirlenir, EVDS'te seri olarak yayımlanmaz.",
        KAYNAK + " · bie_hpbitablo2 (yeni), bie_kredi (arşiv), bie_zorundth (kur)."],
        n_panel=2)


# ===========================================================================
#  Şekil 02 — ham vs arındırılmış: kur etkisinin büyüklüğü
# ===========================================================================
def sekil_02(M, K, AY, o, damga):
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.09,
                        specs=[[{"secondary_y": False}], [{"secondary_y": True}],
                               [{"secondary_y": False}]],
                        subplot_titles=(
                            "Ham ve arındırılmış kredi büyümesi (13 haftalık, yıllıklandırılmış)",
                            "Kur etkisinin büyüklüğü: ham − arındırılmış (puan) ve sepet kurunun "
                            "13 haftalık değişimi",
                            "Laspeyres ayrıştırma: haftalık kur etkisi (Γ) ve gerçek kredi akımı (Λ), "
                            "13 haftalık toplam"))
    _cizgi(fig, _pen(M["g_ham_13y"], YAKIN_BAS), "Ham (arındırılmamış)", CLARET, 1, kalin=2.4)
    _cizgi(fig, _pen(M["g_ar_13y"], YAKIN_BAS), "Arındırılmış — sepet kuru (ana seri)",
           TEAL, 1, kalin=2.4)
    _cizgi(fig, _pen(M["g_ar_usd_13y"], YAKIN_BAS), "Tanı: arındırılmış, USD kuru",
           GOLD, 1, kalin=1.4, kesik="dash")
    _cizgi(fig, _pen(M["g_cipa_13y"], YAKIN_BAS), "Tanı: çıpalı (sabit kur) arındırma",
           MOR, 1, kalin=1.4, kesik="dot")
    _sifir_cizgi(fig, 1)

    ke = _pen(M["kur_etkisi_13y"], YAKIN_BAS).dropna()
    fig.add_trace(go.Bar(x=ke.index, y=ke.values, name="Kur etkisi (puan)",
                         marker_color=GOLD, opacity=0.55,
                         hovertemplate="%{y:,.2f} puan<extra>Kur etkisi</extra>"),
                  row=2, col=1, secondary_y=False)
    kur13 = (K["sepet"] / K["sepet"].shift(13) - 1) * 100
    _cizgi(fig, _pen(kur13, YAKIN_BAS), "Sepet kuru, 13 haftalık değişim",
           LACI, 2, kalin=1.8, ikincil=True)
    _sifir_cizgi(fig, 2)

    g13 = _pen(AY["gama"].rolling(13).sum(), YAKIN_BAS)
    l13 = _pen(AY["lamda"].rolling(13).sum(), YAKIN_BAS)
    _cizgi(fig, g13, "Γ — kur etkisi (mlr TL, 13 haftalık toplam)", GOLD, 3,
           kalin=2.0, birim=" mlr TL")
    _cizgi(fig, l13, "Λ — gerçek kredi akımı (mlr TL, 13 haftalık toplam)", TEAL, 3,
           kalin=2.0, birim=" mlr TL")
    _cizgi(fig, _pen(AY["delta"].rolling(13).sum(), YAKIN_BAS),
           "ΔK — yayımlanan seviye değişimi", GRI, 3, kalin=1.2, kesik="dot",
           birim=" mlr TL")
    _sifir_cizgi(fig, 3)
    fig.update_yaxes(title_text="%, yıllıklandırılmış", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="%", row=2, col=1, secondary_y=True,
                     showgrid=False)
    fig.update_yaxes(title_text="milyar TL", row=3, col=1)
    ayr = o.get("ayristirma") or {}
    return _duzen(fig, f"Kur etkisinin büyüklüğü · veri {damga}", [
        "Ham büyüme iki bileşenin toplamıdır: gerçek kredi akımı + YP kredinin yeniden değerlemesi. "
        "Arındırma ikinciyi dışarıda bırakır.",
        f"Laspeyres kimliği Γ + Λ = ΔK · en büyük bağıl artık "
        f"{ayr.get('artik_bagil_maks', float('nan')):.1e} (makine hassasiyeti).",
        f"Zincirleme sapması D<sub>T</sub> = {ayr.get('d_zincir_mlr', float('nan')):,.1f} mlr TL — "
        "yayımlanmaz, denetlenir. Çıpalı ile zincirleme aynı sayıyı vermez; ana seri zincirlemedir.",
        KAYNAK + " · bie_hpbitablo2, bie_zorundth."], n_panel=3)


# ===========================================================================
#  Şekil 03 — kredi türü kırılımı, katılım bankaları, eğilim anketi
# ===========================================================================
def sekil_03(M, H, A, C, o, damga):
    fig = make_subplots(rows=4, cols=1, vertical_spacing=0.065,
                        specs=[[{"secondary_y": False}], [{"secondary_y": False}],
                               [{"secondary_y": True}], [{"secondary_y": False}]],
                        subplot_titles=(
                            "Kredi türüne göre büyüme (13 haftalık, yıllıklandırılmış)",
                            "Stok kompozisyonu (milyar TL) — yurt içi şubeler",
                            "Katılım bankaları dahil ve hariç: 12 aylık büyüme (aylık seri, HAM)",
                            "Banka Kredileri Eğilim Anketi — standartlar ve talep (net yüzde değişim)"))
    for ad, kol, renk in (("Tüketici (TL+YP birleşik)", "g_tuketici_13y", CLARET),
                          ("Ticari (arındırılmış)", "g_ticari_13y", TEAL),
                          ("KOBİ (arındırılmış)", "g_kobi_13y", LACI),
                          ("Bireysel kredi kartı", "g_bkk_13y", GOLD),
                          ("Kurumsal kredi kartı", "g_kurumsal_kart_13y", MOR)):
        if kol in M.columns:
            _cizgi(fig, _pen(M[kol], YAKIN_BAS), ad, renk, 1)
    _sifir_cizgi(fig, 1)

    for ad, kol, renk in (("Tüketici", "k_tuketici", CLARET),
                          ("Ticari — TL", "k_ticari_tl", TEAL),
                          ("Ticari — YP (TL karşılığı)", "k_ticari_yp", GOLD),
                          ("Bireysel kredi kartı", "k_bkk", LACI),
                          ("Kurumsal kredi kartı", "k_kurumsal_kart", MOR),
                          ("Finansal kuruluşlara", "k_finansal", GRI)):
        if kol in H.columns:
            _cizgi(fig, _pen(H[kol] / 1e6, YAKIN_BAS), ad, renk, 2, kalin=1.8,
                   birim=" mlr TL")

    if "g_kh_toplam_yil" in A.columns:
        _cizgi(fig, _pen(A["g_kh_toplam_yil"], ORTA_BAS),
               "Bankacılık sektörü — katılım DAHİL", TEAL, 3, kalin=2.2)
        _cizgi(fig, _pen(A["g_kh_haric_yil"], ORTA_BAS),
               "Katılım bankaları HARİÇ", CLARET, 3, kalin=2.2)
        _cizgi(fig, _pen(A["g_kh_katilim_yil"], ORTA_BAS),
               "Yalnız katılım bankaları", GOLD, 3, kalin=1.6, kesik="dash")
        _cizgi(fig, _pen(A["katilim_pay"], ORTA_BAS), "Katılım payı (sağ eksen)",
               LACI, 3, kalin=1.4, kesik="dot", ikincil=True)
    _sifir_cizgi(fig, 3)

    for ad, kol, renk in (("İşletme kredisi standartları", "bkea_std_isletme", TEAL),
                          ("KOBİ standartları", "bkea_std_kobi", LACI),
                          ("İşletme kredi talebi", "bkea_talep", CLARET),
                          ("Talep — gelecek çeyrek beklentisi", "bkea_talep_bek", GOLD),
                          ("Bireysel — konut standartları", "bkea_std_konut", MOR)):
        if kol in C.columns:
            _cizgi(fig, _pen(C[kol], ORTA_BAS), ad, renk, 4, kalin=1.8,
                   birim="")
    _sifir_cizgi(fig, 4)
    fig.update_yaxes(title_text="%, yıllıklandırılmış", row=1, col=1)
    fig.update_yaxes(title_text="milyar TL", row=2, col=1)
    fig.update_yaxes(title_text="%, 12 aylık", row=3, col=1, secondary_y=False)
    fig.update_yaxes(title_text="%", row=3, col=1, secondary_y=True, showgrid=False)
    fig.update_yaxes(title_text="net yüzde", row=4, col=1)
    return _duzen(fig, f"Kredi kırılımı ve kredi arzı–talebi · veri {damga}", [
        "Tüketici kalemleri EVDS'te TL+YP BİRLEŞİK yayımlanıyor; o seriler HAM'dır. Ticari ve "
        "KOBİ'de TL/YP ayrı olduğu için arındırma uygulanmıştır.",
        "Aylık seri TL/YP kırılımı taşımaz: üçüncü paneldeki büyümeler HAM'dır ve "
        "birinci panelin arındırılmış serileriyle aynı cümlede okunmaz.",
        "BKEA net yüzde değişimdir, seviye değildir; standart serilerinde işaret sıkılaşma/gevşeme "
        "yönünü, talep serilerinde artış/azalış yönünü gösterir.",
        KAYNAK + " · bie_hpbitablo6, bie_krehacbs, bie_bkea."], n_panel=4)


# ===========================================================================
#  Şekil 04 — kredi faizleri, politika faizi/AOFM ve makaslar
# ===========================================================================
def sekil_04(F, o, damga):
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "Kredi faizleri, mevduat faizi ve TCMB fiyatları (haftalık akım, "
                            "yıllıklandırılmış ağırlıklı ortalama)",
                            "Makaslar: kredi − mevduat, kredi − politika faizi, kredi − AOFM (puan)",
                            "Reel kredi ve mevduat faizi — TAM FISHER, PKA 12 aylık beklentisiyle"))
    for ad, kol, renk, kalin in (
            ("Ticari TL kredi", "f_ticari_tl", TEAL, 2.4),
            ("İhtiyaç kredisi", "f_ihtiyac", CLARET, 1.8),
            ("Konut kredisi", "f_konut", LACI, 1.6),
            ("Taşıt kredisi", "f_tasit", MOR, 1.4),
            ("TL mevduat", "mev_tl", GOLD, 2.0),
            ("Politika faizi (1 hafta repo kotasyonu)", "politika", INK, 1.6),
            ("AOFM", "aofm", GRI, 1.4)):
        if kol in F.columns:
            _cizgi(fig, _pen(F[kol], ORTA_BAS), ad, renk, 1, kalin=kalin,
                   kesik="dash" if kol in ("politika", "aofm") else None)
    for ad, kol, renk in (("Koridor alt (O/N alış)", "koridor_alt", GRI),
                          ("Koridor üst (O/N satış)", "koridor_ust", GRI)):
        if kol in F.columns:
            _cizgi(fig, _pen(F[kol], ORTA_BAS), ad, renk, 1, kalin=0.9, kesik="dot")

    for ad, kol, renk in (("Kredi − mevduat (aracılık marjı)", "makas_kredi_mevduat", TEAL),
                          ("Kredi − politika faizi", "spread_politika", CLARET),
                          ("Kredi − AOFM", "spread_aofm", GOLD)):
        if kol in F.columns:
            _cizgi(fig, _pen(F[kol], ORTA_BAS), ad, renk, 2, kalin=2.0, birim=" puan")
    _sifir_cizgi(fig, 2)

    for ad, kol, renk, kesik in (
            ("Reel ticari kredi faizi (tam Fisher)", "reel_ticari", TEAL, None),
            ("Reel tüketici kredi faizi", "reel_tuketici", CLARET, None),
            ("Reel TL mevduat faizi", "reel_mevduat", GOLD, None),
            ("Tanı: i − π yaklaşımı (kullanılmaz)", "reel_ticari_yaklasik", GRI, "dot")):
        if kol in F.columns:
            _cizgi(fig, _pen(F[kol], ORTA_BAS), ad, renk, 3, kalin=1.8, kesik=kesik)
    _sifir_cizgi(fig, 3)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    fig.update_yaxes(title_text="%", row=3, col=1)
    return _duzen(fig, f"Kredi faizleri ve spread'ler · veri {damga}", [
        "Faizler YENİ KULLANDIRIM (akım) faizleridir, stok değil. Politika faizi tek başına "
        "çizilmez; koridor ve AOFM ile birlikte okunur.",
        "Reel faiz TAM FISHER ile hesaplanır: (1+i)/(1+π<sup>e</sup>) − 1. Bu düzeyde (i − π) yaklaşımı "
        f"{abs((o.get('reel_ticari') or 0) - (o.get('reel_ticari_yaklasik') or 0)):.1f} puan sapıyor.",
        "Beklenti girdisi Piyasa Katılımcıları Anketi'nin 12 ay sonrası TÜFE beklentisidir (aylık); "
        "haftalık eksene son yayımlanan değer taşınır.",
        KAYNAK + " · bie_kt100h, bie_mt100h, bie_pyintbnk, bie_apifon, bie_beklenti."], n_panel=3)


# ===========================================================================
#  Şekil 05 — parasal büyüklükler ve para çarpanı
# ===========================================================================
def sekil_05(P, o, damga):
    fig = make_subplots(rows=4, cols=1, vertical_spacing=0.065,
                        subplot_titles=(
                            f"M1 / M2 / M3 büyümesi — TCMB'nin kur etkisinden ARINDIRILMIŞ "
                            f"endeksleri (13 haftalık, yıllıklandırılmış, {_yil(PARA_BAS)}→)",
                            "Yöntem kıyası: bu çalışmanın arındırdığı M2 ile TCMB'nin ARIM2 endeksi",
                            "Para çarpanı (M / rezerv para)",
                            "Rezerv para bileşenleri (milyar TL)"))
    for ad, kol, renk in (("M1 (ARIM1)", "tcmb_ar_m1_13y", LACI),
                          ("M2 (ARIM2)", "tcmb_ar_m2_13y", TEAL),
                          ("M3 (ARIM3)", "tcmb_ar_m3_13y", CLARET)):
        if kol in P.columns:
            _cizgi(fig, _pen(P[kol], PARA_BAS), ad, renk, 1, kalin=2.0)
    if "tcmb_ham_m2_13y" in P.columns:
        _cizgi(fig, _pen(P["tcmb_ham_m2_13y"], PARA_BAS), "M2 — ham (HAMM2)",
               GRI, 1, kalin=1.3, kesik="dot")
    _sifir_cizgi(fig, 1)

    _cizgi(fig, _pen(P["g_m2_ar_13y"], PARA_BAS),
           "Bu çalışmanın arındırması (zincirleme, sepet kuru)", GOLD, 2, kalin=2.0)
    _cizgi(fig, _pen(P["tcmb_ar_m2_13y"], PARA_BAS), "TCMB ARIM2", TEAL, 2, kalin=2.0)
    _cizgi(fig, _pen(P["g_m2_ham_13y"], PARA_BAS), "Ham (kimlik sınavı)", GRI, 2,
           kalin=1.2, kesik="dot")
    _sifir_cizgi(fig, 2)

    for ad, kol, renk in (("m1 = M1/RP", "carpan_m1", LACI),
                          ("m2 = M2/RP", "carpan_m2", TEAL),
                          ("m3 = M3/RP", "carpan_m3", CLARET)):
        if kol in P.columns:
            _cizgi(fig, _pen(P[kol], ORTA_BAS), ad, renk, 3, kalin=2.0, birim="")

    for ad, kol, renk in (("Emisyon", "emisyon_mlr", CLARET),
                          ("Zorunlu karşılık bloke hesabı", "zk_bloke_mlr", TEAL),
                          ("Bankalar serbest mevduatı", "serbest_mevduat_mlr", GOLD),
                          ("Rezerv para", "rezerv_para_mlr", INK)):
        if kol in P.columns:
            _cizgi(fig, _pen(P[kol], ORTA_BAS), ad, renk, 4, kalin=1.8,
                   birim=" mlr TL")
    fig.update_yaxes(title_text="%, yıllıklandırılmış", row=1, col=1)
    fig.update_yaxes(title_text="%, yıllıklandırılmış", row=2, col=1)
    fig.update_yaxes(title_text="kat", row=3, col=1)
    fig.update_yaxes(title_text="milyar TL", row=4, col=1)
    a2 = ((o.get("dogrulama") or {}).get("arindirilmis") or {}).get("m2") or {}
    return _duzen(fig, f"Parasal büyüklükler ve para çarpanı · veri {damga}", [
        "Türkiye'nin M1'i YP VADESİZ MEVDUATI içerir; bu, M1'i kur hareketine duyarlı kılar: "
        "arındırılmamış bir 'M1 patladı' cümlesi çoğu zaman kur cümlesidir.",
        "Birinci panel TCMB'nin KENDİ arındırdığı endekslerdir. İkinci panel bu çalışmanın "
        f"arındırmasını kıyaslar: yanlılık {a2.get('yanlilik_pp', float('nan')):+.2f} puan, "
        f"korelasyon {a2.get('korel', float('nan')):.2f}.",
        f"İlk iki panel {_yil(PARA_BAS)}'den başlar: Aralık 2021 kur şokunda ham M2 momentumu %300'ü "
        "aşıyor ve tüm tarihçe tek eksene sığdırıldığında bugünkü bant okunamıyor.",
        "Para çarpanı davranış parametresi değil bir orandır: paydası ZK oranı değişince idari olarak "
        "sıçrar. Bu yüzden altında ZK bloke hesabı da çizilir.",
        KAYNAK + " · bie_hpbitablo1 (seviye), bie_kavramsal (endeks), bie_abanlbil."], n_panel=4)


# ===========================================================================
#  Şekil 06 — mevduat kompozisyonu ve dolarizasyon
# ===========================================================================
def sekil_06(D, o, damga):
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "Mevduat kompozisyonu — TL ve döviz tevdiat hesapları (milyar TL, "
                            "zorunlu karşılığa tabi taban)",
                            "Dolarizasyon: DTH payı — ham ve kur etkisinden arındırılmış",
                            "Döviz mevduatı, döviz cinsinden (milyar ABD doları) — davranışsal ölçü"))
    _cizgi(fig, _pen(D["mevduat_tl_mlr"], ORTA_BAS), "TL mevduat", TEAL, 1,
           kalin=2.0, birim=" mlr TL")
    _cizgi(fig, _pen(D["mevduat_yp_mlr"], ORTA_BAS), "DTH (TL karşılığı)", CLARET, 1,
           kalin=2.0, birim=" mlr TL")
    if "mevduat_yp_sabit_mlr" in D.columns:
        _cizgi(fig, _pen(D["mevduat_yp_sabit_mlr"], ORTA_BAS),
               "DTH — çıpa haftasının kuruyla", GOLD, 1, kalin=1.4, kesik="dash",
               birim=" mlr TL")

    _cizgi(fig, _pen(D["dth_pay_ham"], ORTA_BAS), "DTH payı — ham", CLARET, 2, kalin=2.2)
    _cizgi(fig, _pen(D["dth_pay_ar"], ORTA_BAS),
           "DTH payı — kur etkisinden arındırılmış", TEAL, 2, kalin=2.2)
    if "bilanco_pay_ham" in D.columns:
        _cizgi(fig, _pen(D["bilanco_pay_ham"], ORTA_BAS),
               "Kıyas: sektör bilançosundan ham pay", GRI, 2, kalin=1.2, kesik="dot")
    dol = o.get("dolarizasyon") or {}
    if dol.get("cipa"):
        _kirilma(fig, dol["cipa"], 2, "arındırma çıpası")

    if "mevduat_yp_usd_mia" in D.columns:
        _cizgi(fig, _pen(D["mevduat_yp_usd_mia"], ORTA_BAS),
               "Yurt içi yerleşiklerin döviz mevduatı", LACI, 3, kalin=2.2,
               birim=" mia USD")
    fig.update_yaxes(title_text="milyar TL", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    fig.update_yaxes(title_text="milyar ABD doları", row=3, col=1)
    return _duzen(fig, f"Mevduat kompozisyonu ve dolarizasyon · veri {damga}", [
        "Ham pay DTH'ın TL KARŞILIĞI üzerinden hesaplandığı için kur yükselirken kendiliğinden yükselir. "
        "Arındırılmış pay DTH'ı çıpa kuruyla yeniden değerler.",
        f"Arındırma çıpası: {dol.get('cipa', '—')} (kur {dol.get('cipa_kur', float('nan')):.4f}); "
        "takvim yılının ilk gözlemidir ve yıl dönünce kendiliğinden ilerler.",
        "Arındırılmış seri ÇIPADAN ÖNCESİNE UZATILMAZ: sabit kurla değerlenmiş pay çıpaya göre "
        "tanımlıdır, geriye uzatıldığında dolarizasyon değil kur okunur.",
        "Kur: DTH'ın TL ve USD karşılıklarının oranından ima edilen SEPET kuru — mevduat tarafında "
        "sepet doğrudan ölçülebiliyor. Taban altın hesaplarını da içerir.",
        KAYNAK + " · bie_tldthvade, bie_zorundth, bie_hpbitablo2."], n_panel=3)


# ===========================================================================
#  Şekil 07 — KKM stoku ve erime hızı
# ===========================================================================
def sekil_07(A, o, damga):
    kkm = o.get("kkm") or {}
    aktif = bool(kkm.get("aktif"))
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12,
                        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
                        subplot_titles=(
                            "Kur Korumalı Mevduat stoku — TL KKM (sol) ve döviz dönüşümlü KKM (sağ)",
                            "Aylık değişim: KKM stokunun erime hızı (milyar TL/ay)"))
    if "kkm_tl_mlr" in A.columns:
        _cizgi(fig, A["kkm_tl_mlr"], "TL KKM (milyar TL)", TEAL, 1, kalin=2.4,
               birim=" mlr TL")
    if "kkm_usd_mia" in A.columns:
        _cizgi(fig, A["kkm_usd_mia"], "DDKKM (milyar ABD doları, sağ eksen)",
               CLARET, 1, kalin=2.0, ikincil=True, birim=" mia USD")
    if kkm.get("zirve_tarih"):
        _kirilma(fig, kkm["zirve_tarih"], 1, "stok zirvesi")
    d = A["kkm_tl_degisim"].dropna() if "kkm_tl_degisim" in A.columns else pd.Series(dtype=float)
    if len(d):
        fig.add_trace(go.Bar(x=d.index, y=d.values, name="Aylık değişim (mlr TL)",
                             marker_color=[TEAL if v >= 0 else CLARET for v in d.values],
                             hovertemplate="%{y:,.1f} mlr TL<extra>Aylık değişim</extra>"),
                      row=2, col=1)
    _sifir_cizgi(fig, 2)
    fig.update_yaxes(title_text="milyar TL", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="milyar USD", row=1, col=1, secondary_y=True,
                     showgrid=False)
    fig.update_yaxes(title_text="milyar TL", row=2, col=1)
    durum = ("Program hâlâ açık; stok ve aylık değişim güncel akımı ölçer." if aktif else
             "Program fiilen KAPANMIŞTIR: bu şekil bitmiş bir rejimin tarihidir; güncel "
             "dolarizasyon yorumunda 'KKM çıkışı' gerekçesi kullanılmaz.")
    return _duzen(fig, f"Kur Korumalı Mevduat — stok ve çıkış · veri {damga}", [
        "KKM TL cinsinden açılan ama getirisi kur artışına endeksli bir mevduattır: M2'nin TL "
        "bacağında durur, YP bacağında değil.",
        "Çıkışı üç yere birden gidebilir — TL mevduata (dolarizasyon değişmez), DTH'ye (yükselir) "
        "ya da sistem dışına (M2 küçülür, M3'ün fon kalemleri büyür).",
        durum,
        KAYNAK + " · bie_kkm (aylık stok; EVDS'te haftalık KKM serisi yoktur)."], n_panel=2)


# ===========================================================================
#  Şekil 08 — takipteki alacaklar
# ===========================================================================
def sekil_08(M, H, o, damga):
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12,
                        specs=[[{"secondary_y": False}], [{"secondary_y": True}]],
                        subplot_titles=(
                            "Takipteki alacak oranı — toplam, tüketici ve ticari",
                            "Takipteki alacak stoku (milyar TL) ve karşılık oranı"))
    for ad, kol, renk in (("Toplam", "npl", TEAL),
                          ("Tüketici kredileri", "npl_tuketici", CLARET),
                          ("Ticari ve diğer", "npl_ticari", LACI)):
        if kol in M.columns:
            _cizgi(fig, _pen(M[kol], YAKIN_BAS), ad, renk, 1, kalin=2.2)
    if "takip_toplam" in H.columns:
        _cizgi(fig, _pen(H["takip_toplam"] / 1e6, YAKIN_BAS),
               "Takipteki alacaklar (mlr TL)", CLARET, 2, kalin=2.2, birim=" mlr TL")
    if "karsilik_orani" in M.columns:
        _cizgi(fig, _pen(M["karsilik_orani"], YAKIN_BAS),
               "Karşılık oranı (sağ eksen)", TEAL, 2, kalin=1.8, ikincil=True)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="milyar TL", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="%", row=2, col=1, secondary_y=True, showgrid=False)
    return _duzen(fig, f"Takipteki alacaklar ve karşılıklar · veri {damga}", [
        "Oran, takipteki alacakların KREDİ + TAKİP toplamına bölümüdür; paydaya takibin kendisi de "
        "girdiği için krediyi tek başına kullanan ölçüden düşüktür.",
        "Karşılık oranı, özel VE BEKLENEN ZARAR karşılıklarının takip stokuna oranıdır; beklenen zarar "
        "canlı krediler için de ayrıldığından oran %100'ü aşabilir.",
        "Takipteki alacak SATIŞI oranı mekanik olarak düşürür; oranın gerilemesi tek başına kredi "
        "kalitesinin iyileştiği anlamına gelmez.",
        (f"Haftalık kredi kırılımı tablosu {_kirilma_tr(o, H)}'te başlar; "
         "şekil o tarihten itibaren çizilir."),
        KAYNAK + " · bie_hpbitablo2, bie_hpbitablo6."], n_panel=2)


# ===========================================================================
#  Şekil 09 — kredi büyümesi ↔ enflasyon momentumu
# ===========================================================================
def sekil_09(CU, o, damga):
    if CU.empty:
        return None
    tani = o.get("uzun_capraz") or {}
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12,
                        subplot_titles=(
                            "Kur etkisinden arındırılmış kredi büyümesi ve enflasyon momentumu "
                            "(aylık ortalama)",
                            "Gecikmeli korelasyon: kredi büyümesi (t) ile enflasyon momentumu (t+k)"))
    _cizgi(fig, _pen(CU["kredi_ar_13y"], UZUN_BAS),
           "Kredi büyümesi — 13 haftalık yıllıklandırılmış, arındırılmış", TEAL, 1, kalin=2.2)
    if "enf_6a" in CU.columns:
        _cizgi(fig, _pen(CU["enf_6a"], UZUN_BAS),
               "TÜFE momentumu — 6 aylık SAAR", CLARET, 1, kalin=2.0)
    if "enf_3a" in CU.columns:
        _cizgi(fig, _pen(CU["enf_3a"], UZUN_BAS), "TÜFE momentumu — 3 aylık SAAR",
               GOLD, 1, kalin=1.2, kesik="dot")
    if "enf_yillik" in CU.columns:
        _cizgi(fig, _pen(CU["enf_yillik"], UZUN_BAS), "TÜFE — 12 aylık", GRI, 1,
               kalin=1.2, kesik="dash")
    _sifir_cizgi(fig, 1)

    korel = tani.get("korel") or {}
    if korel:
        k = sorted((int(a), b) for a, b in korel.items())
        x = [a for a, _ in k]
        y = [b for _, b in k]
        en = tani.get("en_iyi_gecikme")
        fig.add_trace(go.Bar(
            x=x, y=y, name="Korelasyon katsayısı",
            marker_color=[CLARET if a == en else TEAL for a in x], opacity=0.85,
            hovertemplate="k = %{x} ay · r = %{y:.3f}<extra></extra>"), row=2, col=1)
        _sifir_cizgi(fig, 2)
        fig.update_xaxes(title_text="k (ay) — pozitif: kredi öncül, negatif: enflasyon öncül",
                         row=2, col=1)
    fig.update_yaxes(title_text="%, yıllıklandırılmış", row=1, col=1)
    fig.update_yaxes(title_text="r", row=2, col=1)
    en_g = tani.get("en_iyi_gecikme")
    en_r = tani.get("en_iyi_korel")
    yon = ("enflasyon momentumu kredi büyümesinin ÖNÜNDE" if (en_g or 0) < 0
           else "kredi büyümesi enflasyon momentumunun ÖNÜNDE")
    return _duzen(fig, f"Kredi büyümesi ve enflasyon momentumu · veri {damga}", [
        "Bu bir NEDENSELLİK İDDİASI DEĞİLDİR; gecikmeli korelasyon ölçüsüdür. Aynı pencerede her iki "
        "seriyi de kur hareketi besliyor olabilir.",
        f"Örneklem {tani.get('bas', '—')[:7]} → {tani.get('son', '—')[:7]} ({tani.get('n', 0)} ay). "
        f"En yüksek mutlak korelasyon k = {en_g} ayda (r = {en_r:.2f}): bu örneklemde {yon}.",
        f"Eşanlı korelasyon r = {tani.get('esanli_korel', float('nan')):.2f}. Kredi serisi aylığa ay "
        "ortalamasıyla indirgenmiştir; momentum Enflasyon hattının SAAR çıktısıdır.",
        KAYNAK + " · bie_hpbitablo2 + bie_kredi · momentum: Enflasyon hattı (TÜİK/TCMB)."],
        n_panel=2)


# ===========================================================================
SEKILLER = [
    ("01_kredi_buyume.html", 2),
    ("02_kur_etkisi.html", 3),
    ("03_kredi_kirilim.html", 4),
    ("04_faiz_spread.html", 3),
    ("05_para_arzi.html", 4),
    ("06_dolarizasyon.html", 3),
    ("07_kkm.html", 2),
    ("08_takip.html", 2),
    ("09_kredi_enflasyon.html", 2),
]


def kos() -> None:
    M, P, D, F, A, K, AY, H, C, U, CU, o = _yukle()
    damga = ad_gun(pd.Timestamp(o["son_hafta"]))
    print(f"Kredi & parasal büyüklükler — grafikler · veri {damga}")
    ciktilar = [
        (sekil_01(M, U, o, damga), "01_kredi_buyume.html"),
        (sekil_02(M, K, AY, o, damga), "02_kur_etkisi.html"),
        (sekil_03(M, H, A, C, o, damga), "03_kredi_kirilim.html"),
        (sekil_04(F, o, damga), "04_faiz_spread.html"),
        (sekil_05(P, o, damga), "05_para_arzi.html"),
        (sekil_06(D, o, damga), "06_dolarizasyon.html"),
        (sekil_07(A, o, damga), "07_kkm.html"),
        (sekil_08(M, H, o, damga), "08_takip.html"),
        (sekil_09(CU, o, damga), "09_kredi_enflasyon.html"),
    ]
    n = 0
    for fig, ad in ciktilar:
        if fig is None:
            print(f"  ATLANDI: {ad} — girdisi üretilemedi (uyarilar.json'a bakın)")
            continue
        _yaz(fig, ad)
        n += 1
    # MDX'teki yukseklik={} ile bu dosya AYNI kaynaktan beslenir.
    (CIKTI / "yukseklikler.json").write_text(json.dumps(
        {ad: int(fig.layout.height) for fig, ad in ciktilar if fig is not None},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {n}/{len(ciktilar)} grafik yazıldı → {CIKTI}")
    # SESSİZ BAYATLAMA YASAK: bir figür üretilemediyse eskisi site/public'te
    # yerinde kalır ve sayfanın geri kalanı tazelenir — grafik bayat, metin taze.
    if n < len(ciktilar):
        eksik = [ad for fig, ad in ciktilar if fig is None]
        raise SystemExit(
            f"DUR: {len(eksik)} figür üretilemedi ({', '.join(eksik)}). "
            "Siteye kopyalama YAPILMAZ — eski grafikle taze metin yayımlanmasın. "
            "Nedeni için uyarilar.json'a bakın.")


if __name__ == "__main__":
    kos()
