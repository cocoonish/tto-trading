# -*- coding: utf-8 -*-
"""Ödemeler dengesi ve dış finansman — grafik katmanı (Plotly, site ev stili).

Kurallar (site sözleşmesi):
  · Çok panelli figürlerde paneller ALT ALTA (rows=N, cols=1). YAN YANA PANEL YOK.
  · Panel başına ~340 px + başlık/lejant payı; buradaki `height` MDX'teki
    `yukseklik={}` ile AYNI olmak zorunda (cikti/yukseklikler.json tek kaynak).
  · Başlık solda, iki satır: "<b>Başlık</b><br><sup>alt başlık</sup>".
  · Lejant altta yatay, beyaz zemin, include_plotlyjs="cdn",
    config: responsive=True, displaylogo=False.
  · Tarih ekseni TÜRKÇE ay adlarıyla etiketlenir (Plotly'nin varsayılanı
    İngilizce; `tickmode="array"` ile elle yazılır). İmleç etiketinde de ay
    adı geçmesin diye tarih biçimi SAYISALDIR (%m.%Y / %d.%m.%Y).
  · Her figürde SON GÖZLEM anotasyonla işaretlidir ve başlıkta veri tarihi
    yazar (bayat grafik gözle görülür).
  · Şekil numarası BELGE SIRASINI izler; dosya adı = şekil no (NN_ad.html).
  · Bir figür üretilemezse hat DURUR — eski grafik + taze metin yayımlanmasın.

İŞARET UYARISI: giriş/çıkış işaret çevirmesi metrik.py'de TEK YERDE yapıldı.
Bu dosya kolonları OLDUĞU GİBİ çizer; burada bir daha çevrilirse seri iki kez
çevrilir ve sessizce ters yöne bakar.

BİRİM: 12 aylık ve aylık akımlar MİLYAR USD olarak çizilir (metrik katmanı
milyon USD üretir; dönüşüm /1000 ve yalnız burada, `_mia` ile). Haftalık borç
ödeme takvimi MİLYON USD kalır — milyar ölçeğinde okunamayacak kadar küçük.

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
from veri import VERI, AY_KISA, ay_ad, ceyrek_ad, gun_ad

CIKTI = veri.PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

# Ev stili jetonları — site/tools/plotly_stil.py ve diğer hatlarla aynı
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
LACI, MOR, YESIL, GRI = "#2f4b7c", "#665191", "#7a9e7e", "#8a8a8a"
PEMBE, TURUNCU = "#a05195", "#c2703d"
PALET = [TEAL, CLARET, GOLD, LACI, MOR, PEMBE, YESIL, TURUNCU, GRI]

PANEL_PX = 340

# Pencereler. Sabitler burada; panel başlıklarındaki yıllar bu sabitlerden
# TÜRETİLİR — sabit değişince başlık da değişsin, sessizce yanlışa dönmesin.
CEKIRDEK_BAS = "1997-01-01"   # bie_hariccariacik 1996-01'de başlıyor, 12 aylık toplam 1996-12'den
TAM_BAS = "1990-01-01"
ANA_BAS = "2010-01-01"        # eurobond serileri 2010'da başlıyor
ROLL_BAS = "2007-06-01"       # ODEROLL 2006-06'da başlıyor, 12 aylık toplam 2007-05'ten
YAKIN_BAS = "2018-01-01"
HAFTA_BAS = "2013-01-01"
TUREV_BAS = "2014-01-01"      # finansal türevler kalemi bu tarihte BAŞLIYOR (öncesi YOK, sıfır değil)


def _yil(t: str) -> int:
    return int(str(t)[:4])


def _mia(s):
    """Milyon USD → milyar USD. Dönüşüm TEK yerde; grafikte 'milyar' yazıyorsa
    sayı buradan geçmiş demektir."""
    return s / 1000.0


# --------------------------------------------------------------------------- düzen
SATIR_SINIR = 140     # başlık bloğunda bir <sup> satırına sığan yaklaşık karakter
# (ölçüldü: 1100 px genişlikte Georgia 15 px ile 150 karakter sağdan taşıyor)


def _sayi(x, ondalik: int = 0) -> str:
    """Türkçe sayı biçimi: binlik ayracı nokta, ondalık ayracı virgül."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _bol(metin: str, sinir: int = SATIR_SINIR) -> list[str]:
    """Uzun alt başlık satırını KELİME sınırından böler (Plotly satır sarmaz)."""
    duz = re.sub("<[^>]+>", "", metin)
    if len(duz) <= sinir:
        return [metin]
    parcalar, o_an = [], ""
    for kelime in metin.split(" "):
        aday = (o_an + " " + kelime).strip()
        if len(re.sub("<[^>]+>", "", aday)) > sinir and o_an:
            parcalar.append(o_an)
            o_an = kelime
        else:
            o_an = aday
    if o_an:
        parcalar.append(o_an)
    return parcalar


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
           y_baslik: str = "", ek_yukseklik: int = 0) -> go.Figure:
    """Ev stili düzeni.

    DİPNOT NEDEN GRAFİĞİN İÇİNDE DEĞİL: site/tools/plotly_stil.py her HTML'e
    çalışma zamanında `legend.y = −0,1` ve `margin.b = 110` dayatıyor; sabit
    konumlu bir dipnot uzun figürlerde lejantın üstüne biner. Bu yüzden
    açıklama satırları BAŞLIK bloğunda (<sup>) taşınır — ev stili başlıktaki
    her <br> için üst marjı büyütür, çakışma imkânsızdır.
    """
    alt = [parca for satir in alt for parca in _bol(satir)]
    l_satir = _lejant_satir(fig)
    # ÜST MARJ İNCE AYARI: plotly_stil.py margin.t'yi önce koşulsuz 92'ye çeker,
    # sonra YALNIZCA mevcut değer gerekenden KÜÇÜKSE yükseltir. Doğru değeri
    # buraya yazmak ters teper; bir eksik yazılır, ev stili tamamlar.
    ust = 92 + 26 * len(alt) + 25
    b = 110 + max(0, l_satir - 1) * 24
    h = PANEL_PX * n_panel + ust + b + ek_yukseklik
    metin = f"<b>{baslik}</b>" + "".join(f"<br><sup>{x}</sup>" for x in alt)
    gereken_t = 92 + 26 * len(alt) + 26          # plotly_stil.py'nin hesabı
    blok_px = 22 + 19 * len(alt)                 # ölçüldü: satır ~18,5 px
    dolgu_t = int(max(12, (gereken_t - blok_px) / 2))
    fig.update_layout(
        title=dict(text=metin, x=0, xanchor="left", y=1.0, yanchor="top",
                   yref="container", pad=dict(t=dolgu_t, l=0),
                   font=dict(size=15, color=INK, family="Georgia, serif")),
        height=h, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Georgia, serif", size=12, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.1, x=0,
                    font=dict(size=11), tracegroupgap=2,
                    bgcolor="rgba(255,255,255,0)"),
        margin=dict(l=64, r=64, t=ust, b=b),
        hovermode="x unified",
        barmode="relative",      # yığılmış çubuk; negatifler aşağı yığılır
        bargap=0.12,
        hoverlabel=dict(bgcolor="white", bordercolor=GRID))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=GRID,
                     zerolinewidth=1.2, automargin=True)
    if y_baslik:
        fig.update_yaxes(title_text=y_baslik)
    return fig


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


# --------------------------------------------------------------------------- eksen
def _eksen_tr(fig, satirlar: list[int], x0, x1, gunluk: bool = False) -> None:
    """Tarih eksenini TÜRKÇE ay adlarıyla etiketler.

    Plotly'nin yerelleştirmesi yok; varsayılan "Jun 2026" basıyor. Etiketler
    burada elle üretilir. İmleç (hover) etiketinde de İngilizce ay adı
    çıkmasın diye tarih biçimi SAYISAL bırakılır.
    """
    x0, x1 = pd.Timestamp(x0), pd.Timestamp(x1)
    yil = max((x1 - x0).days / 365.25, 0.1)
    if yil > 24:
        adim, tip = 48, "yil"
    elif yil > 12:
        adim, tip = 24, "yil"
    elif yil > 6:
        adim, tip = 12, "yil"
    elif yil > 3:
        adim, tip = 6, "ay"
    elif yil > 1.5:
        adim, tip = 3, "ay"
    else:
        adim, tip = 1, "ay"
    bas = pd.Timestamp(year=x0.year, month=x0.month, day=1)
    tik = pd.date_range(bas, x1 + pd.offsets.MonthEnd(1), freq=f"{adim}MS")
    if tip == "yil":
        # Yıllık adımda etiketler yıl başına çekilir; "Oca-14, Oca-16" yerine
        # "2014, 2016" okunur.
        tik = pd.date_range(pd.Timestamp(year=x0.year, month=1, day=1),
                            x1 + pd.offsets.YearEnd(1),
                            freq=f"{adim // 12}YS")
        etiket = [str(t.year) for t in tik]
    else:
        etiket = [f"{AY_KISA[t.month]}-{str(t.year)[2:]}" for t in tik]
    for s in satirlar:
        fig.update_xaxes(tickmode="array", tickvals=list(tik), ticktext=etiket,
                         tickangle=0, range=[x0, x1],
                         hoverformat="%d.%m.%Y" if gunluk else "%m.%Y",
                         row=s, col=1)


def _son_isaret(fig, satir: int, x, y, metin: str, renk: str = INK,
                ay: int = -34, ax: int = -58) -> None:
    """Son gözlemi noktayla ve etiketle işaretler (bayatlık gözle görülsün)."""
    if y is None or (isinstance(y, float) and not np.isfinite(y)):
        return
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", showlegend=False,
                             marker=dict(color=renk, size=7,
                                         line=dict(color="white", width=1.2)),
                             hoverinfo="skip"),
                  row=satir, col=1)
    fig.add_annotation(x=x, y=y, text=metin, showarrow=True, arrowhead=0,
                       arrowwidth=1, arrowcolor=renk, ax=ax, ay=ay,
                       font=dict(size=11, color=renk),
                       bgcolor="rgba(255,255,255,0.82)", borderpad=2,
                       row=satir, col=1)


def _iz(fig, x, y, ad, renk, satir, kalin=1.8, kes=None, grup=None,
        goster=True, opacity=1.0, dolgu=None, dolgu_renk=None):
    fig.add_trace(go.Scatter(
        x=x, y=y, name=ad, mode="lines", legendgroup=grup or ad,
        showlegend=goster, opacity=opacity, connectgaps=False,
        line=dict(color=renk, width=kalin, dash=kes),
        fill=dolgu, fillcolor=dolgu_renk),
        row=satir, col=1)


def _cubuk(fig, x, y, ad, renk, satir, grup=None, goster=True, opacity=0.85):
    fig.add_trace(go.Bar(x=x, y=y, name=ad, marker_color=renk,
                         marker_line_width=0, opacity=opacity,
                         legendgroup=grup or ad, showlegend=goster),
                  row=satir, col=1)


# ===========================================================================
# YIĞIN DENETİMİ — bu sınıf hata YALNIZ burada yakalanır
# ===========================================================================
# Yığılmış çubuk + toplam çizgisi olan her panelde, çubukların toplamı çizgiye
# eşit OLMAK ZORUNDADIR. Metrik katmanının kimlik denetimleri bunu göremez:
# orada iki taraf da AYNI seriden türer, oysa grafikte çubuk bir kolonu,
# çizgi başka bir kolonu okur. İkisi farklı NaN işlemi kullanıyorsa (biri ham
# NaN, diğeri fillna(0)) yığın sessizce kısalır.
#
# GERÇEK OLAY (2026-08 denetimi): Şekil 11'in üst panelinde eurobond bacağı
# `eb_odeme_uv12` (ham NaN, min_periods=12) ile çiziliyordu, toplam çizgisi
# ise aynı bacağı `fillna(0)` ile topluyordu. 66 çubuğun 36'sı eksikti; fark
# 2023-04'te 18,2 MİLYAR USD. Okur eksik çubuğu "o dönem eurobond ödemesi
# yoktu" diye okuyordu. Aşağıdaki denetim tam bu sapmayı ölçer.
#
# PLOTLY DAVRANIŞI: NaN bir çubuk ÇİZİLMEZ, yani yığında sıfır gibi durur.
# Denetim bu yüzden `fillna(0)` ile toplar — ekranda görünen yığın budur.
YIGIN_ESIK_MN_USD = 1.0
_YIGIN: list[dict] = []


def _yigin_denetimi(ad: str, cubuklar: list[pd.Series], cizgi: pd.Series,
                    esik: float = YIGIN_ESIK_MN_USD) -> None:
    """Yığılmış çubukların toplamı ile toplam çizgisini KARŞILAŞTIRIR.

    `cubuklar` ve `cizgi` GRAFİKTE ÇİZİLEN serilerin ta kendisi olmalıdır
    (aynı pencere, aynı örnekleme) — yeniden hesaplanan bir kopya, aradaki
    farkı gizler.
    """
    if cizgi is None or not len(cizgi) or not cubuklar:
        return
    # ÇUBUKLARIN indeksi esas alınır: yığılmış paneller okunabilirlik için
    # SEYRELTİLİYOR (bkz. _ornekle), çizgi ise aylık kalıyor. Çizginin
    # indeksine göre toplamak, örneklenmemiş ayları "çubuk sıfır" sayar ve
    # denetimi sahte sapmayla doldururdu.
    idx = cubuklar[0].index
    toplam = sum(s.reindex(idx).fillna(0.0) for s in cubuklar)
    fark = (cizgi.reindex(idx) - toplam).abs().dropna()
    if fark.empty:
        return
    gecti = bool(fark.max() <= esik)
    _YIGIN.append({"panel": ad, "n": int(len(fark)),
                   "maks_fark": round(float(fark.max()), 3),
                   "maks_tarih": str(fark.idxmax().date()),
                   "esik": esik, "gecti": gecti})
    isaret = "✓" if gecti else "✗"
    print(f"    yığın {isaret} {ad}: n={len(fark)}, maks "
          f"{fark.max():,.2f} mn USD ({fark.idxmax():%m.%Y})")


def _pencere(df: pd.DataFrame, bas: str, son=None) -> pd.DataFrame:
    """Pencere sabitleri SUNUM tercihidir, ölçüm değil — ama serinin gerçek
    başlangıcının gerisine düşmemeleri gerekir; düşerlerse eksen boş bir
    kuyruk çizer ve okur 'veri var ama sıfır' sanır."""
    if df.empty:
        return df
    bas_t = max(pd.Timestamp(bas), df.index[0])
    d = df.loc[df.index >= bas_t]
    if son is not None:
        d = d.loc[d.index <= pd.Timestamp(son)]
    return d


def _ornekle(d: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Yığılmış çubuk panelleri için SEYRELTME (yalnız sunum kararı).

    12 aylık BİRİKİMLİ bir seriyi her ay çubukla çizmek bilgi eklemez: ardışık
    iki çubuk 11 ayı ortak taşır. 16 yıllık pencerede 198 çubuk yan yana
    gelince renkler birbirine karışıyor ve yığın okunamıyor (ölçüldü). Çubuklar
    bu yüzden N ayda bir örneklenir; ÇİZGİLER aylık kalır, yani hiçbir tepe
    noktası kaybolmaz. Örnekleme SON gözleme çapalıdır — en taze çubuk her
    zaman görünür.
    """
    if d.empty:
        return d, 1
    yil = (d.index[-1] - d.index[0]).days / 365.25
    n = 6 if yil > 20 else 3 if yil > 8 else 1
    if n == 1:
        return d, 1
    return d.iloc[::-1].iloc[::n].iloc[::-1], n


def _ornek_notu(n: int) -> list[str]:
    if n <= 1:
        return []
    return [f"Yığılmış çubuklar okunabilirlik için {n} AYDA BİR örneklendi "
            "(12 aylık birikimli seride ardışık iki çubuk 11 ayı ortak taşır); "
            "çizgiler aylık, hiçbir tepe noktası atlanmıyor."]


def _kaynak(damga: str, ek: str = "") -> str:
    return (f"Veri: TCMB EVDS3 · ödemeler dengesi aylık, milyon USD "
            f"(grafikte milyar USD) · Çıpa: {damga}." + (" " + ek if ek else ""))


# ===========================================================================
# ŞEKİL 01 — Manşet ve çekirdek cari denge
# ===========================================================================
def sekil_01(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Aylık cari denge (çubuk) ile 12 aylık birikimli manşet ve "
            "çekirdek cari denge (çizgi)",
            "b) Manşet − çekirdek makası: altın ve enerjinin cari dengeye "
            "toplam katkısı (12 aylık birikimli)"))
    d = _pencere(M, CEKIRDEK_BAS)
    _cubuk(fig, d.index, _mia(d["cari"]), "Aylık cari denge", GRI, 1, opacity=0.55)
    _iz(fig, d.index, _mia(d["cari12"]), "Manşet cari denge (12 aylık)",
        CLARET, 1, kalin=2.2)
    _iz(fig, d.index, _mia(d["cekirdek12"]),
        "Çekirdek cari denge — altın ve enerji hariç (12 aylık)", TEAL, 1,
        kalin=2.2)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    _iz(fig, d.index, _mia(d["makas12"]), "Manşet − çekirdek", GOLD, 2, kalin=2.0,
        dolgu="tozeroy", dolgu_renk="rgba(154,115,39,0.13)")
    _iz(fig, d.index, _mia(d["altin_net12"]), "Altın net (12 aylık)", MOR, 2,
        kalin=1.3, kes="dash")
    _iz(fig, d.index, _mia(d["enerji_net12"]), "Enerji net (12 aylık)", LACI, 2,
        kalin=1.3, kes="dot")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)

    s = d["cari12"].dropna()
    c = d["cekirdek12"].dropna()
    _son_isaret(fig, 1, s.index[-1], _mia(s.iloc[-1]),
                f"manşet {_sayi(_mia(s.iloc[-1]), 1)} mia USD", CLARET)
    _son_isaret(fig, 1, c.index[-1], _mia(c.iloc[-1]),
                f"çekirdek {_sayi(_mia(c.iloc[-1]), 1)} mia USD", TEAL, ay=34)
    mk = d["makas12"].dropna()
    _son_isaret(fig, 2, mk.index[-1], _mia(mk.iloc[-1]),
                f"{_sayi(_mia(mk.iloc[-1]), 1)} mia USD", GOLD)

    alt = [
        _kaynak(damga, "Manşet cari denge TP.ODANA6.Q01; çekirdek "
                       "TP.HARICCARIACIK.K10 (TCMB'nin altın ve enerji hariç "
                       "tanımı)."),
        f"Ölçülen (12 aylık, {damga}): manşet {_sayi(_mia(s.iloc[-1]), 1)} "
        f"mia USD, çekirdek {_sayi(_mia(c.iloc[-1]), 1)} mia USD, makas "
        f"{_sayi(_mia(mk.iloc[-1]), 1)} mia USD.",
        "Makas kimliği sınandı: manşet = çekirdek + altın net + enerji net "
        f"(n={o['dogrulama'].get('manşet CA(12a) = çekirdek + altın net + enerji net', {}).get('n', '—')}, "
        f"en büyük sapma "
        f"{_sayi(o['dogrulama'].get('manşet CA(12a) = çekirdek + altın net + enerji net', {}).get('maks_fark'), 2)} "
        "mn USD).",
        "Çekirdek seri TÜİK dış ticaret istatistiklerinden beslenir; TÜİK "
        "revizyonu buraya da yansır. 12 aylık toplam, eksik ay varsa "
        "hesaplanmaz (kısmi toplam yayımlanmaz).",
    ]
    _duzen(fig, "Cari denge: manşet ve çekirdek", alt, 2,
           y_baslik="milyar USD")
    _eksen_tr(fig, [1, 2], d.index[0], d.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 02 — Altın ve enerji ayrıştırması (köprü)
# ===========================================================================
def sekil_02(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Köprü: çekirdek cari denge + altın net + enerji net = manşet "
            "cari denge (12 aylık birikimli)",
            "b) Aylık altın ve enerji dengesi — ayrıştırmanın kaynağı"))
    d = _pencere(M, CEKIRDEK_BAS)
    y1, n_ornek = _ornekle(d)
    _cubuk(fig, y1.index, _mia(y1["cekirdek12"]), "Çekirdek cari denge", TEAL, 1)
    _cubuk(fig, y1.index, _mia(y1["altin_net12"]), "Altın net (parasal olmayan)",
           GOLD, 1)
    _cubuk(fig, y1.index, _mia(y1["enerji_net12"]), "Enerji net (27. fasıl)",
           LACI, 1)
    _iz(fig, d.index, _mia(d["cari12"]), "Manşet cari denge (yığının toplamı)",
        CLARET, 1, kalin=2.2)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    y = _pencere(M, YAKIN_BAS)
    _cubuk(fig, y.index, _mia(y["altin_net"]), "Altın net (aylık)", GOLD, 2)
    _cubuk(fig, y.index, _mia(y["enerji_net"]), "Enerji net (aylık)", LACI, 2)
    _iz(fig, y.index, _mia(y["cari"]), "Manşet cari denge (aylık)", CLARET, 2,
        kalin=1.4)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)

    a12 = d["altin_net12"].dropna()
    e12 = d["enerji_net12"].dropna()
    _son_isaret(fig, 1, a12.index[-1], _mia(a12.iloc[-1]),
                f"altın {_sayi(_mia(a12.iloc[-1]), 1)}", GOLD, ay=-30)
    _son_isaret(fig, 1, e12.index[-1], _mia(e12.iloc[-1]),
                f"enerji {_sayi(_mia(e12.iloc[-1]), 1)}", LACI, ay=34)
    ay_e = y["enerji_net"].dropna()
    _son_isaret(fig, 2, ay_e.index[-1], _mia(ay_e.iloc[-1]),
                f"{ay_ad(ay_e.index[-1])}: {_sayi(_mia(ay_e.iloc[-1]), 1)} mia USD",
                LACI)

    alt = [
        _kaynak(damga, "Altın net TP.HARICCARIACIK.K4 (= K2 ihracat − K3 "
                       "ithalat); enerji net K7 (= K5 − K6)."),
        "Üstteki yığın bir AYRIŞTIRMADIR, üç ayrı seri değil: çekirdek + altın "
        "+ enerji toplamı manşet cari dengeye BİREBİR eşittir (kimlik "
        "sınandı). Kırmızı çizgi yığının toplamıdır.",
        f"Ölçülen (12 aylık, {damga}): altın net {_sayi(_mia(a12.iloc[-1]), 1)} "
        f"mia USD, enerji net {_sayi(_mia(e12.iloc[-1]), 1)} mia USD.",
        "Alt panel neden gerekli: 12 aylık toplam altın ithalatındaki tek aylık "
        "sıçramaları yumuşatır; ayrıştırmanın kaynağı olan aylık oynaklık "
        "ancak burada görünür.",
    ]
    alt += _ornek_notu(n_ornek)
    _duzen(fig, "Cari dengenin ayrıştırılması: altın ve enerji", alt, 2,
           y_baslik="milyar USD")
    _eksen_tr(fig, [1], d.index[0], d.index[-1])
    _eksen_tr(fig, [2], y.index[0], y.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 03 — Cari dengenin alt kalemleri
# ===========================================================================
def sekil_03(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Cari dengenin alt kalemleri (12 aylık birikimli, yığılmış)",
            "b) Mal dengesinin bacakları: ihracat ve ithalat (12 aylık "
            "birikimli)"))
    d = _pencere(M, TAM_BAS)
    y1, n_ornek = _ornekle(d)
    _cubuk(fig, y1.index, _mia(y1["mal_denge12"]), "Mal dengesi", CLARET, 1)
    _cubuk(fig, y1.index, _mia(y1["hizmet_denge12"]), "Hizmet dengesi", TEAL, 1)
    _cubuk(fig, y1.index, _mia(y1["birincil_denge12"]),
           "Birincil gelir dengesi (faiz, kâr, ücret)", LACI, 1)
    _cubuk(fig, y1.index, _mia(y1["ikincil_denge12"]),
           "İkincil gelir dengesi (transferler)", MOR, 1)
    _iz(fig, d.index, _mia(d["cari12"]), "Cari denge (yığının toplamı)", INK, 1,
        kalin=2.0)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    _iz(fig, d.index, _mia(d["ihracat12"]), "İhracat", TEAL, 2, kalin=1.9)
    _iz(fig, d.index, _mia(d["ithalat12"]), "İthalat", CLARET, 2, kalin=1.9)
    _iz(fig, d.index, _mia(d["hizmet_denge12"]),
        "Hizmet dengesi (karşılaştırma için)", GOLD, 2, kalin=1.4, kes="dash")

    for kol, renk, ay_ in (("mal_denge12", CLARET, -34),
                           ("hizmet_denge12", TEAL, 34)):
        s = d[kol].dropna()
        _son_isaret(fig, 1, s.index[-1], _mia(s.iloc[-1]),
                    f"{_sayi(_mia(s.iloc[-1]), 1)}", renk, ay=ay_)
    ih = d["ihracat12"].dropna()
    _son_isaret(fig, 2, ih.index[-1], _mia(ih.iloc[-1]),
                f"ihracat {_sayi(_mia(ih.iloc[-1]), 0)} mia USD", TEAL)

    alt = [
        _kaynak(damga, "Mal dengesi Q04; hizmet dengesi Q05−Q06; birincil "
                       "gelir Q08−Q09; ikincil gelir Q11."),
        "Yığın bir ayrıştırmadır: dört kalemin toplamı cari dengeye BİREBİR "
        "eşittir (kimlik sınandı, "
        f"n={o['dogrulama'].get('CA(12a) = mal + hizmet + birincil + ikincil', {}).get('n', '—')}).",
        "Hizmet dengesi Türkiye'de büyük ölçüde TURİZM kalemidir ve mal "
        "açığını kısmen karşılar; birincil gelir dengesi ise dış borcun ve "
        "doğrudan yatırım stokunun FAİZ/KÂR faturasıdır — ikisi farklı "
        "sürücülere bağlıdır, aynı grafikte olmaları kıyas içindir.",
    ]
    alt += _ornek_notu(n_ornek)
    _duzen(fig, "Cari dengenin alt kalemleri", alt, 2, y_baslik="milyar USD")
    _eksen_tr(fig, [1, 2], d.index[0], d.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 04 — Cari denge / GSYH
# ===========================================================================
def sekil_04(M, G, o, damga, damga_c):
    if G is None or G.empty:
        return None
    g = G.dropna(subset=["cari_gsyh"])
    if g.empty:
        return None
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Cari denge / GSYH (%) — 12 aylık birikimli cari denge ÷ 4 "
            "çeyreklik GSYH, ikisi de USD",
            "b) Paydanın kendisi: 4 çeyreklik GSYH (USD) — birim dönüşümü "
            "görünür olsun diye"))
    _cubuk(fig, g.index, g["cari_gsyh"], "Manşet cari denge / GSYH", CLARET, 1)
    _iz(fig, g.index, g["cekirdek_gsyh"], "Çekirdek cari denge / GSYH", TEAL, 1,
        kalin=2.0)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    g4 = G.dropna(subset=["gsyh4_mn_usd"])
    _iz(fig, g4.index, _mia(g4["gsyh4_mn_usd"]),
        "4 çeyreklik GSYH — çeyrek ORTALAMA kurla", LACI, 2, kalin=2.2)
    _iz(fig, g4.index, _mia(g4["gsyh4_mn_usd_nokta"]),
        "Aynı GSYH — çeyrek SONU (nokta) kurla: tercih edilmedi", GRI, 2,
        kalin=1.3, kes="dash")

    s = g["cari_gsyh"]
    _son_isaret(fig, 1, s.index[-1], s.iloc[-1],
                f"{ceyrek_ad(s.index[-1])}: %{_sayi(s.iloc[-1], 2)}", CLARET)
    v = g4["gsyh4_mn_usd"]
    _son_isaret(fig, 2, v.index[-1], _mia(v.iloc[-1]),
                f"{_sayi(_mia(v.iloc[-1]), 0)} mia USD", LACI)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="milyar USD", row=2, col=1)

    gs = o.get("gsyh", {})
    alt = [
        f"Veri: cari denge TCMB EVDS3 (aylık, mn USD) · GSYH TÜİK "
        f"TP.GSYIH20.BY.B1GQ (üç aylık, BİN TL) · kur TP.DK.USD.A.YTL "
        f"(günlük). Cari denge çıpası {damga}; ORANIN çıpası {damga_c}.",
        "BİRİM ZİNCİRİ: bin TL → /1000 → milyon TL → /çeyrek ORTALAMA USDTRY → "
        "milyon USD. Çeyrek ortalaması kullanılır; nokta kur bir AKIM "
        "büyüklüğünü çeyrek içi kur hareketi kadar yanıltır — iki sürüm alt "
        f"panelde yan yana, aradaki fark %{_sayi(gs.get('nokta_kur_farki_yuzde'), 2)}.",
        f"DÖNEM UYUMSUZLUĞU: ödemeler dengesi {damga}'e kadar dolu, GSYH ise "
        f"{damga_c}'e kadar. Oran GSYH'nin son çeyreğinde DURUR ve grafikte "
        "kendi dönemiyle etiketlenir; 'bu ayın oranı' diye sunmak sessiz "
        "bayatlama olurdu.",
        f"Ölçülen: %{_sayi(gs.get('cari_gsyh_son'), 2)} ({gs.get('cari_gsyh_donem')}); "
        f"tarihçe %{_sayi(gs.get('cari_gsyh_min'), 2)} … "
        f"%{_sayi(gs.get('cari_gsyh_maks'), 2)}. 4 çeyreklik GSYH "
        f"{_sayi(gs.get('gsyh4_trilyon_usd'), 3)} trilyon USD — mertebe "
        f"denetimi bandı {gs.get('mertebe_bant_trn')} trilyon USD ve denetim "
        f"{'GEÇTİ' if gs.get('mertebe_gecti') else 'DÜŞTÜ'}.",
    ]
    _duzen(fig, "Cari denge / GSYH ve paydanın kendisi", alt, 2)
    _eksen_tr(fig, [1], g.index[0], g.index[-1])
    _eksen_tr(fig, [2], g4.index[0], g4.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 05 — Finans hesabı kırılımı (giriş işaretiyle)
# ===========================================================================
def _finans_yigin(fig, d, satir, goster=True):
    kalemler = [
        ("yuk_dyy", "Doğrudan yatırım (yabancı girişi)", TEAL),
        ("yuk_port_hisse", "Portföy — hisse senedi", GOLD),
        ("yuk_port_borc", "Portföy — borç senedi", TURUNCU),
        ("yuk_port_artik", "Portföy — diğer (fon payları vb.)", PEMBE),
        ("yuk_mevduat", "Mevduat (yurt dışından)", LACI),
        ("yuk_kredi", "Krediler", CLARET),
        ("yuk_diger_artik", "Ticari kredi ve diğer yükümlülükler", MOR),
        ("yuk_turev", "Finansal türevler", YESIL),
    ]
    for kol, ad, renk in kalemler:
        _cubuk(fig, d.index, _mia(d[kol]), ad, renk, satir, goster=goster)
    _cubuk(fig, d.index, -_mia(d["yerlesik_varlik"]),
           "Yerleşiklerin dış varlık edinimi (−)", GRI, satir, goster=goster)


def sekil_05(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Finans hesabı kırılımı — 12 aylık birikimli, GİRİŞ işaretiyle "
            "(rezerv HARİÇ)",
            "b) Aynı kırılımın aylık hâli"))
    d = _pencere(M, ANA_BAS).copy()
    for k in ("yuk_dyy", "yuk_port_hisse", "yuk_port_borc", "yuk_port_artik",
              "yuk_mevduat", "yuk_kredi", "yuk_diger_artik", "yuk_turev",
              "yerlesik_varlik"):
        d[k] = d[k + "12"]
    y1, n_ornek = _ornekle(d)
    _finans_yigin(fig, y1, 1)
    _iz(fig, d.index, _mia(d["fin_giris12"]),
        "Net finansman girişi (yığının toplamı)", INK, 1, kalin=2.2)
    _yigin_denetimi("05a finans hesabı kırılımı",
                    [y1[k] for k in ("yuk_dyy", "yuk_port_hisse",
                                     "yuk_port_borc", "yuk_port_artik",
                                     "yuk_mevduat", "yuk_kredi",
                                     "yuk_diger_artik", "yuk_turev")]
                    + [-y1["yerlesik_varlik"]], d["fin_giris12"])
    _iz(fig, d.index, _mia(d["rezerv_akim12"]),
        "Rezerv değişimi (+ = rezerv artışı) — bu kırılıma DAHİL DEĞİL", GRI, 1,
        kalin=1.6, kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    y = _pencere(M, YAKIN_BAS)
    _finans_yigin(fig, y, 2, goster=False)
    _iz(fig, y.index, _mia(y["fin_giris"]), "Net finansman girişi (yığının toplamı)",
        INK, 2, kalin=1.4, goster=False,
        grup="Net finansman girişi (yığının toplamı)")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)

    s = d["fin_giris12"].dropna()
    _son_isaret(fig, 1, s.index[-1], _mia(s.iloc[-1]),
                f"net giriş {_sayi(_mia(s.iloc[-1]), 1)} mia USD", INK)
    ay_s = y["fin_giris"].dropna()
    _son_isaret(fig, 2, ay_s.index[-1], _mia(ay_s.iloc[-1]),
                f"{ay_ad(ay_s.index[-1])}: {_sayi(_mia(ay_s.iloc[-1]), 1)} mia USD",
                INK)

    b = o["basrol"]
    alt = [
        _kaynak(damga, "Finans hesabı ANALİTİK sunumun REZERV HARİÇ kalemidir "
                       "(TP.ODANA6.Q13)."),
        "İŞARET: BPM6'da finans hesabı = net varlık edinimi − net yükümlülük "
        "oluşumu ve POZİTİF değer sermaye ÇIKIŞI demektir. Burada okuma "
        "kolaylığı için GİRİŞ işareti kullanıldı; çevirme metrik katmanında "
        "TEK YERDE yapılır.",
        "Yığın kimliktir: yabancının net yükümlülük oluşumu eksi "
        "yerleşiklerin dış varlık edinimi = net finansman girişi (sınandı, "
        f"en büyük sapma {_sayi(o['dogrulama'].get('fin_giris = brüt yükümlülük − yerleşik varlık edinimi', {}).get('maks_fark'), 2)} mn USD).",
        "ADLANDIRMA: BPM6'da bu kalemlerin hepsi NET yükümlülük oluşumudur "
        "(Q38'in EVDS'teki adı bile '3.6.Finansal Türevler: NET Yükümlülük "
        "Oluşumu') ve negatif olabilirler. 'Brüt' demek yalnız girişlerin "
        "sayıldığı izlenimini verirdi — vermez.",
        f"Ölçülen (12 aylık, {damga}): yükümlülük oluşumu (net, türevler dâhil) "
        f"{_sayi(_mia(b['brut_yukumluluk12_mn_usd']), 1)} mia USD — türev "
        f"bacağı {_sayi(_mia(b.get('yuk_turev12_mn_usd')), 1)} mia USD olduğu "
        f"için türevsiz sürüm {_sayi(_mia(b.get('yukumluluk_turevsiz12_mn_usd')), 1)} "
        f"mia USD. Yerleşik varlık edinimi "
        f"{_sayi(_mia(b['yerlesik_varlik12_mn_usd']), 1)} mia USD, net giriş "
        f"{_sayi(_mia(b['fin_giris12_mn_usd']), 1)} mia USD.",
        "YIĞININ TOPLAMI ÇİZGİYE EŞİTTİR — HER KOŞUDA ÖLÇÜLÜR. Çubukların "
        "toplamı ile toplam çizgisi arasındaki en büyük fark grafik "
        "katmanında ayrıca sınanır (cikti/yigin_denetimi.json); ayrışma "
        "olursa hat durur ve siteye kopyalama yapılmaz.",
        "REZERV NEDEN AYRI: analitik sunumda rezerv varlıklar finans hesabının "
        "İÇİNDE DEĞİLDİR (ayrıntılı sunumun Q101'i içerir; köprü "
        "Q101 = Q13 + Q33). İkisini aynı etiketle yan yana koymak 2026-03'te "
        "43,4 milyar USD'lik sahte bir sapma üretiyordu.",
        f"Finansal türevler kalemi {_yil(TUREV_BAS)}-01'de BAŞLIYOR; öncesinde "
        "kalem YOK (sıfır değil) ve yığında görünmez.",
    ]
    alt += _ornek_notu(n_ornek)
    _duzen(fig, "Finans hesabı: parayı kim, hangi kapıdan getiriyor", alt, 2,
           y_baslik="milyar USD")
    _eksen_tr(fig, [1], d.index[0], d.index[-1])
    _eksen_tr(fig, [2], y.index[0], y.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 06 — Kaliteli finansman, sıcak para ve kalite payı
# ===========================================================================
def sekil_06(M, o, damga):
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.075,
        subplot_titles=(
            "a) Kaliteli finansman: net doğrudan yatırım + özel sektör net "
            "uzun vadeli kredisi (12 aylık)",
            "b) Sıcak para: portföy + kısa vadeli kredi + mevduat "
            "yükümlülüğü (12 aylık)",
            "c) Kalite payı (%) — payda mutlak eşiğin altındayken BOŞ bırakılır"))
    d = _pencere(M, ANA_BAS).copy()
    d["bnk_uv_net12"] = d["kredi_bnk_uv_kul12"] - d["kredi_bnk_uv_ode12"]
    d["dgr_uv_net12"] = d["kredi_dgr_uv_kul12"] - d["kredi_dgr_uv_ode12"]
    y1, n_ornek = _ornekle(d)
    _cubuk(fig, y1.index, _mia(y1["dyy_giris12"]), "Net doğrudan yatırım girişi",
           TEAL, 1)
    _cubuk(fig, y1.index, _mia(y1["bnk_uv_net12"]),
           "Bankalar — net uzun vadeli kredi", LACI, 1)
    _cubuk(fig, y1.index, _mia(y1["dgr_uv_net12"]),
           "Reel sektör — net uzun vadeli kredi", GOLD, 1)
    _iz(fig, d.index, _mia(d["kaliteli12"]), "Kaliteli finansman (toplam)",
        CLARET, 1, kalin=2.2)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    _cubuk(fig, y1.index, _mia(y1["yuk_port_hisse12"] + y1["yuk_port_borc12"]
                               + y1["yuk_port_artik12"]),
           "Portföy yükümlülüğü", MOR, 2)
    _cubuk(fig, y1.index, _mia(y1["kredi_bnk_kv12"] + y1["kredi_dgr_kv12"]),
           "Kısa vadeli kredi", TURUNCU, 2)
    _cubuk(fig, y1.index, _mia(y1["yuk_mevduat12"]), "Mevduat", LACI, 2)
    _iz(fig, d.index, _mia(d["sicak_para12"]), "Sıcak para (toplam)", CLARET, 2,
        kalin=2.0)
    _iz(fig, d.index, _mia(d["kaliteli12"]),
        "Kaliteli finansman (karşılaştırma için)", TEAL, 2, kalin=1.5, kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)

    _iz(fig, d.index, d["kalite_pay_brut"],
        "Kaliteli / yükümlülük oluşumu (net, türevler dâhil)", TEAL, 3,
        kalin=2.0)
    _iz(fig, d.index, d["kalite_pay_turevsiz"],
        "Kaliteli / yükümlülük oluşumu (türevler HARİÇ)", LACI, 3, kalin=1.5,
        kes="dot")
    _iz(fig, d.index, d["kalite_pay_acik"], "Kaliteli / cari açık", CLARET, 3,
        kalin=2.0)
    fig.add_hline(y=100, line=dict(color=GOLD, width=1.1, dash="dot"), row=3,
                  col=1)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=3, col=1)

    kl = d["kaliteli12"].dropna()
    _son_isaret(fig, 1, kl.index[-1], _mia(kl.iloc[-1]),
                f"{_sayi(_mia(kl.iloc[-1]), 1)} mia USD", CLARET)
    sp = d["sicak_para12"].dropna()
    _son_isaret(fig, 2, sp.index[-1], _mia(sp.iloc[-1]),
                f"{_sayi(_mia(sp.iloc[-1]), 1)} mia USD", CLARET)
    pb = d["kalite_pay_brut"].dropna()
    if len(pb):
        _son_isaret(fig, 3, pb.index[-1], pb.iloc[-1],
                    f"%{_sayi(pb.iloc[-1], 0)}", TEAL)
    pa = d["kalite_pay_acik"].dropna()
    if len(pa):
        _son_isaret(fig, 3, pa.index[-1], pa.iloc[-1],
                    f"%{_sayi(pa.iloc[-1], 0)}", CLARET, ay=34)
    fig.update_yaxes(title_text="milyar USD", row=1, col=1)
    fig.update_yaxes(title_text="milyar USD", row=2, col=1)
    fig.update_yaxes(title_text="%", row=3, col=1)

    k = o["kalite"]
    esik = o["esik"]["oran_payda_mn_usd"]
    alt = [
        _kaynak(damga, "Net DYY = Q15 − Q14; özel sektör net UV kredi = "
                       "(Q169−Q170) + (Q182−Q183); sıcak para yükümlülük "
                       "bacağından (Q17, Q167+Q180, Q143)."),
        "'KALİTE' BİR DEĞER YARGISI DEĞİL VADE ÖLÇÜSÜDÜR: doğrudan yatırım ve "
        "uzun vadeli kredi, portföy ve mevduattan yavaş çıkar. Tanıma "
        "katılmayan okur bileşenleri üstteki iki panelde ayrı ayrı görür.",
        f"Ölçülen (12 aylık, {damga}): kaliteli finansman "
        f"{_sayi(_mia(k.get('kaliteli_12ay')), 1)} mia USD — bunun "
        f"{_sayi(_mia(k.get('ozel_uv_kredi_12ay')), 1)} mia USD'si uzun vadeli "
        f"kredi, yalnız {_sayi(_mia(k.get('dyy_12ay')), 1)} mia USD'si net "
        f"doğrudan yatırım. Sıcak para {_sayi(_mia(k.get('sicak_para_12ay')), 1)} "
        "mia USD.",
        f"ORAN NEDEN İKİNCİL: her iki payda da tek başına kırılgan. Payda "
        f"mutlak {_sayi(esik / 1000, 0)} milyar USD'nin altına düştüğünde oran "
        "çizilmez (grafikte boşluk); ölçülen boş ay sayısı brüt paydada "
        f"{k.get('pay_brut_bos_ay')}, cari açık paydasında "
        f"{k.get('pay_acik_bos_ay')}. Sebep veri hatası değil, paydanın sıfıra "
        "yaklaşması ve işaret değiştirmesidir.",
        f"Son değerler: yükümlülük oluşumuna oran %{_sayi(k.get('pay_brut_son'), 0)} "
        f"({_yil(TUREV_BAS)} sonrası medyan %{_sayi(k.get('pay_brut_medyan_2014'), 0)}); "
        f"cari açığı karşılama oranı %{_sayi(k.get('pay_acik_son'), 0)} "
        f"({_yil(ANA_BAS)} sonrası medyan %{_sayi(k.get('pay_acik_medyan_2010'), 0)}). "
        "Kesikli altın çizgi %100 çizgisidir.",
        f"PAYDA TANIMI VE {_yil(TUREV_BAS)} KIRILMASI: ana payda BPM6'nın NET "
        "yükümlülük oluşumudur ve finansal türevleri İÇERİR. Türev bacağı "
        f"({_sayi(_mia(k.get('turev_bacagi_12ay')), 1)} mia USD, 12 aylık) "
        "negatif olduğunda paydayı küçültür ve oranı yukarı savurur: türevsiz "
        f"payda {_sayi(_mia(k.get('payda_turevsiz_12ay')), 1)} mia USD ile oran "
        f"%{_sayi(k.get('pay_turevsiz_son'), 0)}, yani "
        f"{_sayi(abs((k.get('pay_brut_son') or 0) - (k.get('pay_turevsiz_son') or 0)), 1)} "
        "puan aşağıda (noktalı lacivert çizgi). Kalem "
        f"{_yil(TUREV_BAS)}-01'de BAŞLADIĞI için payda tanımı orada KIRILIYOR; "
        f"medyan bu yüzden {_yil(TUREV_BAS)} sonrası pencereden verilir "
        f"({_yil(ANA_BAS)} sonrası medyan %"
        f"{_sayi(k.get('pay_brut_medyan_2010'), 0)} iki tanımın karışımıdır).",
    ]
    alt += _ornek_notu(n_ornek)
    _duzen(fig, "Finansmanın kalitesi: vadeye göre ayrıştırma", alt, 3)
    _eksen_tr(fig, [1, 2, 3], d.index[0], d.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 07 — Dış borç çevirme oranları
# ===========================================================================
def sekil_07(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Bankalar: uzun vadeli çevirme oranı (bu çalışmanın türetmesi) "
            "ile TCMB'nin kendi oranı",
            "b) Reel sektör (diğer sektörler): aynı iki oran"))
    d = _pencere(M, ROLL_BAS)
    _iz(fig, d.index, d["roll_uv_bnk"],
        "Bankalar — YALNIZ uzun vadeli kredi (12 aylık kullanım ÷ geri ödeme)",
        CLARET, 1, kalin=2.2)
    _iz(fig, d.index, d["roll_tcmb_bnk"],
        "TCMB — bankalar, kısa+uzun vade (tahvil hariç)", LACI, 1, kalin=1.6)
    _iz(fig, d.index, d["roll_tcmb_bnk_tahvil"],
        "TCMB — bankalar, kısa+uzun vade (tahvil dahil)", GRI, 1, kalin=1.3,
        kes="dash")
    _iz(fig, d.index, d["roll_uv_dgr"],
        "Reel sektör — YALNIZ uzun vadeli kredi (12 aylık)", CLARET, 2,
        kalin=2.2, grup="reel_uv")
    _iz(fig, d.index, d["roll_tcmb_dgr"],
        "TCMB — diğer sektörler, kısa+uzun vade (tahvil hariç)", TEAL, 2,
        kalin=1.6)
    _iz(fig, d.index, d["roll_tcmb_dgr_tahvil"],
        "TCMB — diğer sektörler (tahvil dahil)", GRI, 2, kalin=1.3, kes="dash",
        grup="tcmb_dgr_tahvil")
    for s in (1, 2):
        fig.add_hline(y=100, line=dict(color=GOLD, width=1.3, dash="dot"),
                      row=s, col=1)

    r = o["rollover"]
    for satir, kol, renk in ((1, "roll_uv_bnk", CLARET), (2, "roll_uv_dgr", CLARET)):
        s = d[kol].dropna()
        if len(s):
            _son_isaret(fig, satir, s.index[-1], s.iloc[-1],
                        f"%{_sayi(s.iloc[-1], 0)}", renk)
    for satir, kol, renk in ((1, "roll_tcmb_bnk", LACI), (2, "roll_tcmb_dgr", TEAL)):
        s = d[kol].dropna()
        if len(s):
            _son_isaret(fig, satir, s.index[-1], s.iloc[-1],
                        f"TCMB %{_sayi(s.iloc[-1], 0)}", renk, ay=36)

    alt = [
        _kaynak(damga, "Türetilen oran: 12 aylık kullanım toplamı ÷ 12 aylık "
                       "geri ödeme toplamı (banka Q169/Q170, reel sektör "
                       "Q182/Q183). TCMB'nin oranı bie_oderoll."),
        "İKİ TANIM AYNI SERİ DEĞİLDİR: TCMB'nin oranı KISA+UZUN vadeyi (kesikli "
        "gri çizgide ayrıca tahvili) kapsar; buradaki oran YALNIZ uzun vadeli "
        f"krediyi ölçer. Ölçülen ortalama mutlak fark bankada "
        f"{_sayi(r.get('roll_bnk_kapsam_farki_ort_puan'), 1)} puan, reel "
        f"sektörde {_sayi(r.get('roll_dgr_kapsam_farki_ort_puan'), 1)} puan — "
        "bu KAPSAM farkıdır, veri hatası değil.",
        f"Ölçülen ({damga}): banka uzun vade %{_sayi(r.get('roll_bnk_son'), 1)} "
        f"(TCMB %{_sayi(r.get('roll_bnk_tcmb_son'), 1)}); reel sektör "
        f"%{_sayi(r.get('roll_dgr_son'), 1)} (TCMB "
        f"%{_sayi(r.get('roll_dgr_tcmb_son'), 1)}). {_yil(ANA_BAS)} sonrası "
        f"bant: banka %{_sayi(r.get('roll_bnk_min_2010'), 0)}–"
        f"%{_sayi(r.get('roll_bnk_maks_2010'), 0)}, reel sektör "
        f"%{_sayi(r.get('roll_dgr_min_2010'), 0)}–"
        f"%{_sayi(r.get('roll_dgr_maks_2010'), 0)}.",
        "ORAN NEDEN 12 AYLIK TOPLAMLARDAN: aylık geri ödeme bacağı bazı aylarda "
        "çok küçük olabiliyor ve oran tavana fırlıyor. Pay ve payda ayrı ayrı "
        "12 aya toplanır, sonra bölünür (aylık oranların ortalaması DEĞİL); "
        f"payda {_sayi(o['esik']['roll_payda_mn_usd'], 0)} mn USD'nin altındaysa "
        "oran boş bırakılır.",
        "Altın kesikli çizgi %100'dür: üstü borcun tamamının çevrilip üstüne "
        "yeni borçlanıldığı, altı net geri ödeme yapıldığı anlamına gelir.",
    ]
    _duzen(fig, "Uzun vadeli dış borç çevirme oranı: iki tanım yan yana", alt, 2,
           y_baslik="%")
    _eksen_tr(fig, [1, 2], d.index[0], d.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 08 — Çevirme oranının bacakları
# ===========================================================================
def sekil_08(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Bankalar: uzun vadeli kredi KULLANIMI ve GERİ ÖDEMESİ "
            "(12 aylık toplam)",
            "b) Reel sektör: aynı iki bacak"))
    d = _pencere(M, ANA_BAS)
    _iz(fig, d.index, _mia(d["kredi_bnk_uv_kul12"]),
        "Bankalar — kullanım (oranın PAYI)", TEAL, 1, kalin=2.2)
    _iz(fig, d.index, _mia(d["kredi_bnk_uv_ode12"]),
        "Bankalar — geri ödeme (oranın PAYDASI)", CLARET, 1, kalin=2.2)
    _cubuk(fig, d.index, _mia(d["kredi_bnk_uv_kul12"] - d["kredi_bnk_uv_ode12"]),
           "Net (kullanım − geri ödeme)", GOLD, 1, opacity=0.45)
    _iz(fig, d.index, _mia(d["kredi_dgr_uv_kul12"]),
        "Reel sektör — kullanım", TEAL, 2, kalin=2.2, grup="reel_kul")
    _iz(fig, d.index, _mia(d["kredi_dgr_uv_ode12"]),
        "Reel sektör — geri ödeme", CLARET, 2, kalin=2.2, grup="reel_ode")
    _cubuk(fig, d.index, _mia(d["kredi_dgr_uv_kul12"] - d["kredi_dgr_uv_ode12"]),
           "Net (reel sektör)", GOLD, 2, opacity=0.45, grup="reel_net")
    for s in (1, 2):
        fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=s, col=1)

    for satir, kul, ode in ((1, "kredi_bnk_uv_kul12", "kredi_bnk_uv_ode12"),
                            (2, "kredi_dgr_uv_kul12", "kredi_dgr_uv_ode12")):
        k = d[kul].dropna()
        p = d[ode].dropna()
        _son_isaret(fig, satir, k.index[-1], _mia(k.iloc[-1]),
                    f"kullanım {_sayi(_mia(k.iloc[-1]), 1)}", TEAL)
        _son_isaret(fig, satir, p.index[-1], _mia(p.iloc[-1]),
                    f"ödeme {_sayi(_mia(p.iloc[-1]), 1)}", CLARET, ay=36)

    r = o["rollover"]
    alt = [
        _kaynak(damga, "Banka bacakları Q169 (kullanım) ve Q170 (geri ödeme); "
                       "reel sektör Q182 ve Q183. 12 aylık toplamlar."),
        "BU ŞEKİL OLMADAN ÇEVİRME ORANI OKUNAMAZ: oran yükselirken KULLANIMIN "
        "mı arttığı yoksa GERİ ÖDEMENİN mi düştüğü ancak bacaklar ayrı "
        "çizilince görülür. İkisi çok farklı hikâyelerdir — biri iştah, öteki "
        "vade yapısı.",
        f"Ölçülen ({damga}): banka oranı %{_sayi(r.get('roll_bnk_son'), 1)}, "
        f"reel sektör %{_sayi(r.get('roll_dgr_son'), 1)}. Altın çubuklar net "
        "bakiyedir: pozitif = sektör net borçlanıyor, negatif = net geri ödüyor.",
        "Kimlik sınandı: net uzun vadeli kredi kalemi (Q168/Q181) kullanım "
        "eksi geri ödemeye birebir eşit — bacaklar aynı tablodan geliyor.",
    ]
    _duzen(fig, "Çevirme oranının bacakları: kullanım mı arttı, ödeme mi düştü",
           alt, 2, y_baslik="milyar USD")
    _eksen_tr(fig, [1, 2], d.index[0], d.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 09 — Net hata ve noksan
# ===========================================================================
def sekil_09(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Net hata ve noksan: aylık (çubuk) ve 12 aylık birikimli (çizgi)",
            "b) Büyüklük ölçüsü: |NHN| ÷ |cari denge| (12 aylık) ve 36 aylık "
            "yüzdelik dilim"))
    d = _pencere(M, ANA_BAS)
    _cubuk(fig, d.index, _mia(d["nhn"]), "Aylık net hata ve noksan", GRI, 1,
           opacity=0.6)
    _iz(fig, d.index, _mia(d["nhn12"]), "12 aylık birikimli", CLARET, 1,
        kalin=2.2)
    _iz(fig, d.index, _mia(d["nhn_std12"]),
        "Aylık NHN'nin 12 aylık standart sapması", LACI, 1, kalin=1.3, kes="dot")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    _iz(fig, d.index, d["nhn_oran"], "|NHN(12a)| ÷ |cari denge(12a)| (%)", TEAL,
        2, kalin=2.0)
    _iz(fig, d.index, d["nhn_yuzdelik36"],
        "Aylık |NHN|'nin 36 aylık yüzdelik dilimi (%)", GOLD, 2, kalin=1.5)
    fig.add_hline(y=100, line=dict(color=GRI, width=1.0, dash="dot"), row=2,
                  col=1)

    n = d["nhn12"].dropna()
    _son_isaret(fig, 1, n.index[-1], _mia(n.iloc[-1]),
                f"{_sayi(_mia(n.iloc[-1]), 1)} mia USD", CLARET)
    ora = d["nhn_oran"].dropna()
    if len(ora):
        _son_isaret(fig, 2, ora.index[-1], ora.iloc[-1],
                    f"%{_sayi(ora.iloc[-1], 0)}", TEAL)
    fig.update_yaxes(title_text="milyar USD", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)

    nh = o["nhn"]
    alt = [
        _kaynak(damga, "Net hata ve noksan TP.ODANA6.Q31 (ayrıntılı sunumdaki "
                       "Q210 ile birebir aynı; kimlik sınandı)."),
        "NHN, ödemeler dengesi kimliğinin kapanması için gereken artıktır: "
        "kaydedilmemiş akımları, ölçüm hatalarını ve zamanlama farklarını "
        "birlikte taşır. BURADA YALNIZ ÖLÇÜLÜR — kaynağı hakkında bu grafikten "
        "çıkarım yapılamaz.",
        f"Ölçülen ({damga}): 12 aylık NHN {_sayi(_mia(nh.get('nhn12_son')), 1)} "
        f"mia USD; tarihçe {_sayi(_mia(nh.get('nhn12_min')), 1)} … "
        f"{_sayi(_mia(nh.get('nhn12_maks')), 1)} mia USD. Mevcut değer tüm "
        f"tarihçenin %{_sayi(nh.get('nhn12_yuzdelik_tam_tarihce'), 0)} "
        f"yüzdelik diliminde. |NHN|/|cari denge| = "
        f"%{_sayi(nh.get('nhn_oran_son'), 1)}.",
        "Yüzdelik dilim neden var: 'bu ay olağandışı mı' sorusuna sabit bir "
        "eşik uydurmadan, tarihçenin kendisiyle cevap verir. %100'e yakın "
        "değer, son 36 ayın en büyük mutlak sapması demektir.",
    ]
    _duzen(fig, "Net hata ve noksan: büyüklüğün ölçümü", alt, 2)
    _eksen_tr(fig, [1, 2], d.index[0], d.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 10 — Ödemeler dengesi kimliği (şelale)
# ===========================================================================
def _selale(fig, satir, etiketler, degerler, ad):
    fig.add_trace(go.Waterfall(
        name=ad, orientation="v",
        measure=["relative"] * len(degerler) + ["total"],
        x=etiketler + ["Toplam<br>(sıfır olmalı)"],
        y=[float(v) for v in degerler] + [0.0],
        text=[_sayi(v, 1) for v in degerler] + [_sayi(sum(degerler), 2)],
        textposition="outside", textfont=dict(size=11),
        connector=dict(line=dict(color=GRI, width=1)),
        increasing=dict(marker=dict(color=TEAL)),
        decreasing=dict(marker=dict(color=CLARET)),
        totals=dict(marker=dict(color=INK)), showlegend=False),
        row=satir, col=1)


def sekil_10(M, o, damga):
    d = M.dropna(subset=["cari12", "fin_giris12", "rezerv_akim12",
                         "sermaye_hesabi12", "nhn12"])
    if len(d) < 13:
        return None
    son = d.index[-1]
    onceki = son - pd.DateOffset(months=12)
    if onceki not in d.index:
        onceki = d.index[max(0, len(d) - 13)]
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.13,
        subplot_titles=(
            f"a) Son 12 ay ({ay_ad(son - pd.DateOffset(months=11))} – "
            f"{ay_ad(son)})",
            f"b) Bir önceki 12 ay ({ay_ad(onceki - pd.DateOffset(months=11))} – "
            f"{ay_ad(onceki)})"))
    # Etiketler İKİ SATIRA bölünür: tek satırda yan yana gelen uzun adlar
    # dar iframe'de birbirine giriyor (ölçüldü).
    etiket = ["Cari<br>denge", "Sermaye<br>hesabı", "Net hata<br>ve noksan",
              "Net finansman<br>girişi<br>(rezerv hariç)",
              "Rezerv<br>değişimi (−)"]
    for satir, t in ((1, son), (2, onceki)):
        v = [_mia(d.loc[t, "cari12"]), _mia(d.loc[t, "sermaye_hesabi12"]),
             _mia(d.loc[t, "nhn12"]), _mia(d.loc[t, "fin_giris12"]),
             -_mia(d.loc[t, "rezerv_akim12"])]
        _selale(fig, satir, etiket, v, ay_ad(t))
        fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=satir, col=1)

    kim = o["dogrulama"].get("−CA = fin_giris + KA + NHN − Rezerv (aylık)", {})
    alt = [
        _kaynak(damga, "Kimlik: cari denge + sermaye hesabı + net hata noksan "
                       "= finans hesabı (rezerv hariç) + rezerv varlıklar."),
        "Şelale bu kimliğin GİRİŞ işaretiyle yazılmış hâlidir: cari denge + "
        "sermaye hesabı + net hata noksan + net finansman girişi − rezerv "
        "değişimi = 0. Toplam çubuğunun sıfır olmaması bir hesap hatası olurdu.",
        f"Kimlik sınandı: n={kim.get('n', '—')} ayda en büyük sapma "
        f"{_sayi(kim.get('maks_fark'), 2)} mn USD (eşik "
        f"{_sayi(kim.get('esik'), 0)} mn USD).",
        "REZERV NEDEN EKSİ İŞARETLE: rezerv ARTIŞI bir finansman kaynağı "
        "değildir; gelen kaynağın rezervde biriken kısmıdır. Bu yüzden "
        "kimlikte diğer kalemlerden düşülür.",
        "Alt panel bir önceki 12 aydır: iki dönemi yan yana koymak, kalem "
        "büyüklüklerinin hangi yönde değiştiğini tek bakışta gösterir.",
    ]
    _duzen(fig, "Ödemeler dengesi kimliği: son 12 ay ve bir önceki 12 ay", alt,
           2, y_baslik="milyar USD", ek_yukseklik=60)
    fig.update_xaxes(tickangle=0)
    return fig


# ===========================================================================
# ŞEKİL 11 — Brüt dış finansman ihtiyacı ve karşılanması
# ===========================================================================
def sekil_11(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        subplot_titles=(
            "a) Brüt dış finansman ihtiyacı: cari açık + uzun vadeli anapara "
            "geri ödemeleri (12 aylık)",
            "b) Karşılanması — ödemeler dengesi kimliğinden türetilen, birebir "
            "kapanan bileşenler"))
    d = _pencere(M, ANA_BAS).copy()
    y1, n_ornek = _ornekle(d)
    _cubuk(fig, y1.index, _mia(y1["cari_acik12"]), "Cari açık", CLARET, 1)
    _cubuk(fig, y1.index, _mia(y1["kredi_bnk_uv_ode12"]),
           "Anapara — bankalar (UV kredi)", LACI, 1)
    _cubuk(fig, y1.index, _mia(y1["kredi_dgr_uv_ode12"]),
           "Anapara — reel sektör (UV kredi)", GOLD, 1)
    _cubuk(fig, y1.index, _mia(y1["kredi_gh_uv_ode12"]),
           "Anapara — genel hükümet (UV kredi)", MOR, 1)
    _cubuk(fig, y1.index, _mia(y1["eb_odeme_uv12"]),
           "Anapara — uzun vadeli tahvil (eurobond, A21)", TURUNCU, 1)
    _iz(fig, d.index, _mia(d["ihtiyac12"]), "Brüt dış finansman ihtiyacı", INK,
        1, kalin=2.2)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)
    _yigin_denetimi("11a finansman ihtiyacı",
                    [y1[k] for k in ("cari_acik12", "kredi_bnk_uv_ode12",
                                     "kredi_dgr_uv_ode12", "kredi_gh_uv_ode12",
                                     "eb_odeme_uv12")], d["ihtiyac12"])

    _cubuk(fig, y1.index, _mia(y1["uv_kullanim12"]),
           "Uzun vadeli brüt kullanım (kredi + tahvil)", TEAL, 2)
    _cubuk(fig, y1.index, _mia(y1["diger_net_giris12"]),
           "Diğer net finansman girişi (portföy, mevduat, KV kredi, DYY…)",
           LACI, 2)
    _cubuk(fig, y1.index, _mia(y1["sermaye_hesabi12"]), "Sermaye hesabı", PEMBE, 2)
    _cubuk(fig, y1.index, _mia(y1["nhn12"]), "Net hata ve noksan", GRI, 2)
    _cubuk(fig, y1.index, -_mia(y1["rezerv_akim12"]),
           "Rezerv değişimi (−): artış kaynağı emer", GOLD, 2)
    _iz(fig, d.index, _mia(d["kaynak_kimlik12"]),
        "Kaynak toplamı (= ihtiyaç, kimlik sürümü)", INK, 2, kalin=2.2)
    _iz(fig, d.index, _mia(d["ihtiyac_kimlik12"]),
        "İhtiyaç (kimlik sürümü: −cari denge + anapara)", CLARET, 2, kalin=1.4,
        kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)
    _yigin_denetimi("11b kaynak tablosu",
                    [y1["uv_kullanim12"], y1["diger_net_giris12"],
                     y1["sermaye_hesabi12"], y1["nhn12"], -y1["rezerv_akim12"]],
                    d["kaynak_kimlik12"])

    ih = d["ihtiyac12"].dropna()
    _son_isaret(fig, 1, ih.index[-1], _mia(ih.iloc[-1]),
                f"{_sayi(_mia(ih.iloc[-1]), 1)} mia USD", INK)
    kk = d["kaynak_kimlik12"].dropna()
    _son_isaret(fig, 2, kk.index[-1], _mia(kk.iloc[-1]),
                f"{_sayi(_mia(kk.iloc[-1]), 1)} mia USD", INK)

    t = o["ihtiyac"]
    mert = o["dogrulama"].get(
        "mertebe: UV anapara(12a) ÷ haftalık dış borç ödemesi(52h)", {})
    alt = [
        _kaynak(damga, "Anapara geri ödemeleri Q170 + Q183 + Q178 + A21 "
                       "(YALNIZ uzun vadeli tahvil); brüt kullanım Q169 + "
                       "Q182 + Q177 + A11."),
        f"Ölçülen ({damga}): brüt dış finansman ihtiyacı "
        f"{_sayi(_mia(t.get('ihtiyac12_son')), 1)} mia USD — bunun "
        f"{_sayi(_mia(t.get('cari_acik_12ay')), 1)} mia USD'si cari açık "
        f"(%{_sayi(t.get('ihtiyacta_cari_acik_payi_yuzde'), 0)}), "
        f"{_sayi(_mia(t.get('uv_anapara_12ay')), 1)} mia USD'si uzun vadeli "
        f"anapara geri ödemesi (bankalar "
        f"{_sayi(_mia(t.get('anapara_bnk_12ay')), 1)} + reel sektör "
        f"{_sayi(_mia(t.get('anapara_dgr_12ay')), 1)} + genel hükümet "
        f"{_sayi(_mia(t.get('anapara_gh_12ay')), 1)} + eurobond "
        f"{_sayi(_mia(t.get('eb_odeme_uv_12ay')), 1)} mia USD).",
        "ALT PANEL BİR TAUTOLOJİDİR, DENETİM DEĞİL: 'diğer net finansman "
        "girişi' bizzat (net giriş − uzun vadeli net) diye tanımlandığı için "
        "kaynak tarafında uzun vadeli kullanım ve anapara sadeleşir ve geriye "
        "ödemeler dengesi kimliğinin kendisi kalır. İki tarafın kapanması "
        "anapara bacaklarının doğruluğu hakkında HİÇBİR ŞEY söylemez — "
        "bacaklar bozulduğunda da sapma 0,00 çıkıyor (ölçüldü).",
        "ANAPARANIN GERÇEK DENETİMİ BAĞIMSIZ BİR KAYNAKLA YAPILIR: uzun vadeli "
        "anaparanın 12 aylık toplamı, TCMB'nin HAFTALIK dış borç ödeme "
        f"takviminin 52 haftalık toplamına oranlanır. Ölçülen "
        f"{_sayi(mert.get('son_oran'), 2)}; bant {mert.get('bant', '—')} "
        f"(tarihçe {_sayi(mert.get('min_oran'), 2)}–"
        f"{_sayi(mert.get('maks_oran'), 2)}, n={mert.get('n', '—')}). "
        "Kapsamlar farklı olduğu için eşitlik değil MERTEBE sınanır.",
        "Eurobond neden hem ihtiyaçta hem kaynakta: tahvil bir KREDİ değil "
        "portföy yükümlülüğüdür; anapara ödemesini ihtiyaca yazıp ihracını "
        "kaynağa yazmamak tabloyu bir bacak kadar şişirirdi.",
        "EUROBOND KAPSAMI — ŞEKİL 12'DEN FARKLI: buraya YALNIZ uzun vadeli "
        f"bacak girer (A11 ihraç {_sayi(_mia(t.get('eb_kullanim_uv_12ay')), 1)}, "
        f"A21 anapara {_sayi(_mia(t.get('eb_odeme_uv_12ay')), 1)} mia USD). "
        f"Şekil 12 kısa vadeyi DE içeren A1/A2 toplamını çizer "
        f"({_sayi(_mia(t.get('eb_kullanim_12ay')), 1)} / "
        f"{_sayi(_mia(t.get('eb_odeme_12ay')), 1)} mia USD). Fark bir sapma "
        "değil, kapsam farkıdır.",
        "A21 İHRAÇ/İTFA OLMAYAN AYDA BOŞ GELİR, SIFIR SAYILDI: bu bacağın "
        "12 aylık toplamı boş ayları sıfır kabul ederek kurulur — toplam "
        "çizgisi de aynı işlemi kullanır, yığın bu yüzden çizgiye birebir "
        "oturur (her koşuda ölçülür: cikti/yigin_denetimi.json).",
        "Üst paneldeki ihtiyaç tanımı cari FAZLA dönemlerinde cari kalemi "
        "sıfırlar (fazla bir ihtiyaç değildir); alt paneldeki kimlik sürümü "
        "fazlayı eksi işaretle taşır, bu yüzden iki çizgi fazla dönemlerinde "
        "ayrışır.",
    ]
    alt += _ornek_notu(n_ornek)
    _duzen(fig, "Brüt dış finansman ihtiyacı ve nasıl karşılandığı", alt, 2,
           y_baslik="milyar USD")
    _eksen_tr(fig, [1, 2], d.index[0], d.index[-1])
    return fig


# ===========================================================================
# ŞEKİL 12 — Eurobond akımı ve haftalık dış borç ödeme takvimi
# ===========================================================================
def sekil_12(M, H, o, damga, damga_h):
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.085,
        subplot_titles=(
            "a) Eurobond: aylık ihraç (sektör kırılımlı) ve anapara ödemesi",
            "b) Aynı akım 12 aylık birikimli: ihraç, ödeme ve net erişim",
            "c) Haftalık dış borç ödemeleri — 4 haftalık toplam (EN TAZE veri)"))
    d = _pencere(M, ANA_BAS)
    _cubuk(fig, d.index, _mia(d["eb_kullanim_gh"]), "İhraç — genel hükümet",
           LACI, 1)
    _cubuk(fig, d.index, _mia(d["eb_kullanim_bnk"]), "İhraç — bankalar", TEAL, 1)
    _cubuk(fig, d.index, _mia(d["eb_kullanim_dgr"]), "İhraç — diğer sektörler",
           GOLD, 1)
    _cubuk(fig, d.index, -_mia(d["eb_odeme"]), "Geri ödeme (anapara, −)",
           CLARET, 1)
    _iz(fig, d.index, _mia(d["eb_kullanim"] - d["eb_odeme"]),
        "Aylık net (ihraç − ödeme)", INK, 1, kalin=1.2)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    # 12 aylık birikimli seri KENDİ panelinde: aylık çubuklarla aynı eksene
    # konduğunda büyüklük farkı aylık kalemi görünmez ediyordu (ölçüldü).
    _iz(fig, d.index, _mia(d["eb_kullanim12"]), "İhraç (12 aylık)", TEAL, 2,
        kalin=2.0)
    _iz(fig, d.index, _mia(d["eb_odeme12"]), "Geri ödeme (12 aylık)", CLARET, 2,
        kalin=2.0)
    _iz(fig, d.index, _mia(d["eb_net12"]), "Net piyasa erişimi (12 aylık)", INK,
        2, kalin=2.2)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)

    if H is not None and not H.empty:
        h = _pencere(H, HAFTA_BAS)
        _cubuk(fig, h.index, h["borc_odeme_haz_4h"], "Hazine", CLARET, 3)
        _cubuk(fig, h.index, h["borc_odeme_dgr_4h"], "Diğer", LACI, 3)
        _cubuk(fig, h.index, h["borc_odeme_tcmb_4h"], "TCMB", GOLD, 3)
        _iz(fig, h.index, h["borc_odeme_top_4h"], "Toplam (4 haftalık)", INK, 3,
            kalin=1.6)
        t = h["borc_odeme_top_4h"].dropna()
        _son_isaret(fig, 3, t.index[-1], t.iloc[-1],
                    f"{gun_ad(t.index[-1])}: {_sayi(t.iloc[-1], 0)} mn USD", INK)
        _eksen_tr(fig, [3], h.index[0], h.index[-1], gunluk=True)

    eb = d["eb_net12"].dropna()
    if len(eb):
        _son_isaret(fig, 2, eb.index[-1], _mia(eb.iloc[-1]),
                    f"net {_sayi(_mia(eb.iloc[-1]), 1)} mia USD", INK)
    fig.update_yaxes(title_text="milyar USD", row=1, col=1)
    fig.update_yaxes(title_text="milyar USD", row=2, col=1)
    fig.update_yaxes(title_text="milyon USD", row=3, col=1)

    t = o["ihtiyac"]
    hf = o.get("haftalik", {})
    alt = [
        f"Veri: TCMB EVDS3 · eurobond akımı bie_odeydiebs (aylık, ödemeler "
        f"dengesi çıpası {damga}) · haftalık ödemeler bie_dbafod (çarşamba, "
        f"kendi çıpası {damga_h}).",
        "PANELLERİN DÖNEMİ FARKLIDIR ve bilerek öyle bırakıldı: aylık "
        "ödemeler dengesi ~2 ay gecikmeli, haftalık borç ödeme takvimi ~5 gün. "
        "Aynı eksene zorlamak taze veriyi bayat verinin hızına düşürürdü.",
        f"Ölçülen ({damga}, 12 aylık): tahvil ihracı "
        f"{_sayi(_mia(t.get('eb_kullanim_12ay')), 1)} mia USD, geri ödeme "
        f"{_sayi(_mia(t.get('eb_odeme_12ay')), 1)} mia USD, net "
        f"{_sayi(_mia(t.get('eb_net_12ay')), 1)} mia USD.",
        "KAPSAM — ŞEKİL 11 İLE AYNI ETİKET, FARKLI KÜME: buradaki sayılar "
        "A1/A2 TOPLAMIDIR, yani KISA VADE DÂHİL. Şekil 11'in anapara ve brüt "
        "kullanım bacağına yalnız uzun vadeli sürüm (A11/A21) girer: ihraç "
        f"{_sayi(_mia(t.get('eb_kullanim_uv_12ay')), 1)}, geri ödeme "
        f"{_sayi(_mia(t.get('eb_odeme_uv_12ay')), 1)} mia USD. İki sayıyı "
        "birbirinin yerine koyan okur, Şekil 11'deki anapara toplamını "
        "tutturamaz; fark bir sapma değil KAPSAM farkıdır.",
        f"Haftalık ({damga_h}): son hafta {_sayi(hf.get('son_hafta_mn_usd'), 0)} "
        f"mn USD, son 4 hafta {_sayi(hf.get('son_4hafta_mn_usd'), 0)} mn USD, "
        f"son 52 hafta {_sayi(hf.get('son_52hafta_mn_usd'), 0)} mn USD.",
        "SEYREK SERİ UYARISI: eurobond serileri (hem toplam hem sektör "
        "kırılımı) ihraç/itfa OLMAYAN ayda boş gelir — sıfır değil, hücre "
        "yok. AYLIK panelde o aylarda çubuk yoktur (boş bırakmak dürüsttür); "
        "12 AYLIK birikimli panelde ise boş ay SIFIR AKIM sayılır, yoksa tek "
        "bir boş ay bütün pencereyi silerdi. Toplam ve net hesabı "
        "kırılımlardan değil toplam serilerden (A1/A2) kurulmuştur.",
    ]
    _duzen(fig, "Piyasa erişimi ve ödeme takvimi", alt, 3)
    _eksen_tr(fig, [1, 2], d.index[0], d.index[-1])
    return fig


# ===========================================================================
SEKILLER = [
    "01_cari_manset_cekirdek.html",
    "02_altin_enerji_ayristirma.html",
    "03_cari_alt_kalemler.html",
    "04_cari_gsyh.html",
    "05_finans_hesabi_kirilim.html",
    "06_kaliteli_finansman.html",
    "07_rollover.html",
    "08_rollover_bacaklar.html",
    "09_net_hata_noksan.html",
    "10_odemeler_dengesi_kimligi.html",
    "11_finansman_ihtiyaci.html",
    "12_eurobond_ve_odeme_takvimi.html",
]


def _yukle():
    M = pd.read_csv(VERI / "metrik.csv", index_col=0, parse_dates=True)
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    gyol, hyol = VERI / "ceyrek_metrik.csv", VERI / "haftalik_metrik.csv"
    G = pd.read_csv(gyol, index_col=0, parse_dates=True) if gyol.exists() else None
    H = pd.read_csv(hyol, index_col=0, parse_dates=True) if hyol.exists() else None
    return M, G, H, o


def kos() -> None:
    M, G, H, o = _yukle()
    s_ay = pd.Timestamp(o["son_ay"])
    s_ceyrek = pd.Timestamp(o["son_ceyrek"])
    s_hafta = pd.Timestamp(o["son_hafta"])
    damga, damga_c, damga_h = ay_ad(s_ay), ceyrek_ad(s_ceyrek), gun_ad(s_hafta)
    print(f"Ödemeler dengesi — grafikler · veri {damga} · GSYH {damga_c} · "
          f"haftalık {damga_h}")

    ciktilar = [
        (sekil_01(M, o, damga), SEKILLER[0]),
        (sekil_02(M, o, damga), SEKILLER[1]),
        (sekil_03(M, o, damga), SEKILLER[2]),
        (sekil_04(M, G, o, damga, damga_c), SEKILLER[3]),
        (sekil_05(M, o, damga), SEKILLER[4]),
        (sekil_06(M, o, damga), SEKILLER[5]),
        (sekil_07(M, o, damga), SEKILLER[6]),
        (sekil_08(M, o, damga), SEKILLER[7]),
        (sekil_09(M, o, damga), SEKILLER[8]),
        (sekil_10(M, o, damga), SEKILLER[9]),
        (sekil_11(M, o, damga), SEKILLER[10]),
        (sekil_12(M, H, o, damga, damga_h), SEKILLER[11]),
    ]
    n = 0
    for fig, ad in ciktilar:
        if fig is None:
            print(f"  ATLANDI: {ad} — girdisi üretilemedi (uyarilar.json'a bakın)")
            continue
        _yaz(fig, ad)
        n += 1
    (CIKTI / "yukseklikler.json").write_text(json.dumps(
        {ad: int(fig.layout.height) for fig, ad in ciktilar if fig is not None},
        ensure_ascii=False, indent=1), encoding="utf-8")
    # YIĞIN DENETİMİ HER KOŞUDA YAZILIR (sessiz bayatlama yasak): dosya
    # koşuda üretilmezse eski ölçüm yerinde kalır ve "kapanıyor" der.
    (CIKTI / "yigin_denetimi.json").write_text(json.dumps(
        {"kosum": pd.Timestamp.today().strftime("%Y-%m-%d"),
         "esik_mn_usd": YIGIN_ESIK_MN_USD, "paneller": _YIGIN},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {n}/{len(ciktilar)} grafik yazıldı → {CIKTI}")
    # YIĞIN SAPMASI DURDURUCUDUR. Yığılmış bir çubuk kendi toplam çizgisinden
    # ayrışıyorsa panel YANLIŞ okunur ("o dönem bu kalem yoktu" sanılır) ve
    # bu sınıf hata metrik katmanının kimlik denetimlerine hiç görünmez.
    bozuk = [y for y in _YIGIN if not y["gecti"]]
    if bozuk:
        for y in bozuk:
            print(f"  ✗ YIĞIN AYRIŞMASI {y['panel']}: en büyük "
                  f"{y['maks_fark']:,.2f} mn USD ({y['maks_tarih']}), eşik "
                  f"{y['esik']} mn USD")
        raise SystemExit(
            f"DUR: {len(bozuk)} yığılmış panelde çubuk toplamı kendi toplam "
            "çizgisiyle örtüşmüyor. Genellikle sebebi, aynı bacağın çubukta ve "
            "çizgide FARKLI NaN işlemiyle üretilmesidir. Siteye kopyalama "
            "YAPILMAZ. Ayrıntı: cikti/yigin_denetimi.json")
    # SESSİZ BAYATLAMA YASAK: bir figür üretilemezse eskisi site/public'te
    # yerinde kalır ve sayfanın geri kalanı tazelenir — grafik bayat, metin
    # taze. Bu yüzden eksikte hat DURUR ve siteye kopyalama yapılmaz.
    if n < len(ciktilar):
        eksik = [ad for fig, ad in ciktilar if fig is None]
        raise SystemExit(
            f"DUR: {len(eksik)} figür üretilemedi ({', '.join(eksik)}). "
            "Siteye kopyalama YAPILMAZ — eski grafikle taze metin yayımlanmasın. "
            "Nedeni için uyarilar.json'a bakın.")


if __name__ == "__main__":
    kos()
