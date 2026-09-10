# -*- coding: utf-8 -*-
"""Merkezi Yönetim Bütçesi & Borç Stoku — grafik katmanı (Plotly, ev stili).

Kurallar (site sözleşmesi):
  · Çok panelli figürlerde paneller ALT ALTA (rows=N, cols=1). YAN YANA PANEL YOK.
  · Panel başına ~340 px; buradaki `height` MDX'teki `yukseklik={}` ile AYNI
    olmak zorunda — cikti/yukseklikler.json tek kaynak.
  · Başlık solda, iki satır: "<b>Başlık</b><br><sup>alt başlık</sup>".
  · Lejant altta yatay, beyaz zemin, include_plotlyjs="cdn",
    config: responsive=True, displaylogo=False.
  · Tarih ekseni TÜRKÇE ay adlarıyla etiketlenir (Plotly'nin kendi biçimi
    İngilizce; tickvals/ticktext elle verilir).
  · Her figürde SON GÖZLEM anotasyonla işaretlenir ve başlıkta veri tarihi
    yazar — bayat grafik gözle görülür.
  · Şekil numarası BELGE SIRASINI izler; dosya adı = şekil no (NN_ad.html).
  · Bir figür üretilemezse hat DURUR — eski grafik + taze metin yayımlanmasın.

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
PEMBE, TURUNCU = "#a05195", "#c4703a"

PANEL_PX = 340
KAYNAK = "Kaynak: TCMB EVDS3 (HMB, TÜİK, TCMB derlemeleri)"

# Pencereler. Sabitler burada; panel başlıklarındaki yıllar bu sabitlerden
# TÜRETİLİR — sabit değişince başlık da değişsin, sessizce yanlışa dönmesin.
TAM_BAS = "2007-01-01"       # 12 aylık birikimli seriler burada başlar
AYLIK_BAS = "2019-01-01"     # aylık bar panelleri (240 ay bar okunmaz)
CEYREK_BAS = "2004-12-31"
HAFTA_BAS = "2020-09-11"     # menkul kıymet istatistiklerinin başlangıcı
STOK_BAS = "2020-09-01"      # ARAÇ tabanlı bileşik stok burada başlar: eurobond
                             # sahiplik kırılımı (yurt içi / yurt dışı) daha
                             # geriye gitmiyor. Daha uzun ama yanlış tanımlı bir
                             # seri çizilmez; uzun tarihli okuma alt panelde
                             # finansal hesaplar (F.3+F.4) çizgisiyle verilir.
FIN_BAS = "2010-12-31"       # finansal hesaplar


def _yil(t: str) -> int:
    return int(str(t)[:4])


# --------------------------------------------------------------------------- düzen
SATIR_SINIR = 150     # başlık bloğunda bir <sup> satırına sığan yaklaşık karakter


def _sayi(x, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi: binlik nokta, ondalık virgül, eksi U+2212.

    Metin içinde f"{x:,.1f}".replace(",", ".") yazmak cümlenin KENDİ
    noktalarını da bozuyordu; dönüşüm tek yerde ve yalnız sayıya uygulanır.
    """
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = f"{x:,.{ondalik}f}"
    return (s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
             .replace("-", "−"))


def _yuzde(x, ondalik: int = 1) -> str:
    """Türkçe yüzde yazımı: işaret yüzde iminin ÖNÜNE gelir — "−%8,2".
    f"%{x}" biçimi "%−8,2" üretiyordu."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return ("−" if x < 0 else "") + "%" + _sayi(abs(x), ondalik)


def _bol(metin: str, sinir: int = SATIR_SINIR) -> list[str]:
    """Uzun alt başlık satırını KELİME sınırından böler. Plotly başlık satırını
    sarmaz; sınırı aşan satır figürün sağından taşar."""
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


def _yigin_hizala(fig) -> None:
    """Her yığının izleri ORTAK ucunda biter — eksik bacak SIFIR çizilmez.

    ARIZA (ölçülen 10.09.2026, YAYIMLANMIŞ figürde): Şekil 07'nin üç bacağı
    ayrı ritimde bitiyor (iç borç 07.2026 · eurobond 08.2026 · dış kredi
    06.2026, çeyreklik ve çeyrek içinde basamak). Her iz KENDİ indeksiyle
    çiziliyor ve plotly yığında eksik x'i SIFIR sayıyor (`stackgaps` öntanımlı
    "infer zero"), yani yığının tepesi son iki ayda kendiliğinden çöküyordu:
    borç stoku okura 14,93 → 13,89 → 4,73 trilyon TL diye çıktı. Sayfanın
    damgası DOĞRUYDU ("aylık 06.2026"); yalan söyleyen çizimdi.

    ÇÖZÜM YIĞININ KENDİ ÜYELERİNDEN TÜRETİLİR: grubun ortak ucu, üyelerinin
    son dolu gözlemlerinin EN ESKİSİDİR — bir kompozisyon ancak bütün
    kalemlerinin ölçüldüğü güne kadar kurulabilir. Elle tutulan bir kolon
    listesi olsaydı yeni bir yığın eklendiğinde sessizce dışarıda kalırdı.

    KAPI BURADA DURUR, ÇAĞRI YERİNDE DEĞİL: `_duzen` her figürün ZORUNLU son
    adımı (on üç şeklin on üçü çağırıyor), yani yarın eklenecek bir yığın da
    kendiliğinden bu kuraldan geçer.
    """
    gruplar: dict[str, list] = {}
    for tr in fig.data:
        g = getattr(tr, "stackgroup", None)
        if g:
            gruplar.setdefault(g, []).append(tr)
    for izler in gruplar.values():
        uclar = []
        for tr in izler:
            x, y = getattr(tr, "x", None), getattr(tr, "y", None)
            if x is None or y is None:
                continue
            ya = np.asarray(y, dtype="float64")
            xa = np.asarray(x)
            n = min(len(xa), len(ya))
            dolu = np.flatnonzero(np.isfinite(ya[:n]))
            if len(dolu):
                uclar.append(pd.Timestamp(str(xa[dolu[-1]])))
        if len(uclar) < 2:
            continue
        uc = min(uclar)
        if uc == max(uclar):
            continue                      # bacaklar zaten aynı günde bitiyor
        for tr in izler:
            xa = np.asarray(tr.x)
            tut = np.array([pd.Timestamp(str(v)) <= uc for v in xa])
            tr.x = xa[tut]
            tr.y = np.asarray(tr.y, dtype="float64")[:len(tut)][tut]


def _duzen(fig, baslik: str, alt: list[str], n_panel: int,
           ek_yukseklik: int = 0, barmode: str = "group") -> go.Figure:
    """Ev stili düzeni.

    DİPNOT NEDEN GRAFİĞİN İÇİNDE DEĞİL: site/tools/plotly_stil.py her HTML'e
    çalışma zamanında legend.y = −0,1 ve margin.b = 110 dayatıyor; sabit
    konumlu bir dipnot uzun figürlerde lejantın üstüne biner. Açıklama
    satırları bu yüzden BAŞLIK bloğunda (<sup>) taşınır — ev stili başlıktaki
    her <br> için üst marjı büyütür, çakışma imkânsızdır.
    """
    _yigin_hizala(fig)
    alt = [parca for satir in alt for parca in _bol(satir)]
    l_satir = _lejant_satir(fig)
    # ÜST MARJ İNCE AYARI: plotly_stil.py margin.t'yi önce koşulsuz 92'ye çeker,
    # sonra YALNIZCA mevcut değer gerekenden küçükse yükseltir. Doğru değeri
    # buraya yazmak ters teper; bir eksik yazılır, ev stili kendi hesabına
    # tamamlar.
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
        hoverlabel=dict(bgcolor="white", bordercolor=GRID),
        # BARMODE FİGÜR BAZINDA. Varsayılan "group": karşılaştırılan iki seri
        # YAN YANA çizilir. "relative" (yığma) YALNIZCA kalemler bir toplamın
        # bileşeniyse kullanılır — aksi hâlde okur, iki serinin toplamını tek
        # serinin değeri sanır (ölçüldü: aylık denge ile faiz dışı denge
        # yığılınca −1,6 trilyon TL'lik olmayan bir ay görünüyordu).
        barmode=barmode)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=GRID,
                     automargin=True)
    for ann in fig.layout.annotations:
        if ann.text and ann.font and ann.font.size is None:
            ann.font.size = 12
    return fig


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


# --------------------------------------------------------------------------- eksen
def _etiket(t: pd.Timestamp, tip: str) -> str:
    if tip == "ceyrek":
        return ceyrek_ad(t)
    if tip == "gun":
        return f"{t.day} {AY_KISA[t.month]} {str(t.year)[2:]}"
    return f"{AY_KISA[t.month]}-{str(t.year)[2:]}"


def _tarih_ekseni(fig, satir: int, idx, tip: str = "ay") -> None:
    """TÜRKÇE tarih ekseni.

    Plotly'nin yerleşik tarih biçimleyicisi İngilizce ay adı basıyor ve locale
    ayarı figüre gömülmüyor; tickvals/ticktext elle verilir. Etiket sıklığı
    aralığın uzunluğundan türetilir — sabit bir dtick, kısa pencerede tek
    etiket, uzun pencerede üst üste binen etiket üretirdi.
    """
    idx = pd.DatetimeIndex(pd.Series(idx).dropna()).sort_values()
    if len(idx) == 0:
        return
    bas, son = idx[0], idx[-1]
    yil = max((son - bas).days / 365.25, 0.01)
    if yil > 12:
        tv = pd.date_range(pd.Timestamp(bas.year, 1, 1), son, freq="3YS")
        tt = [str(t.year) for t in tv]
    elif yil > 6:
        tv = pd.date_range(pd.Timestamp(bas.year, 1, 1), son, freq="2YS")
        tt = [str(t.year) for t in tv]
    elif yil > 3:
        tv = pd.date_range(pd.Timestamp(bas.year, 1, 1), son, freq="YS")
        tt = [str(t.year) for t in tv]
    elif yil > 1.2:
        tv = pd.date_range(bas, son, freq="QS")
        tt = [_etiket(t, "ceyrek" if tip == "ceyrek" else "ay") for t in tv]
    else:
        tv = pd.date_range(bas, son, freq="MS")
        tt = [_etiket(t, "ay") for t in tv]
    tv = [t for t in tv if bas <= t <= son]
    tt = tt[:len(tv)]
    # SON GÖZLEM her zaman etiketlenir: grafiğin nerede bittiği, okurun bayat
    # veriyi gözle yakalamasının tek yolu.
    if not tv or (son - tv[-1]).days > 20:
        tv = list(tv) + [son]
        tt = list(tt) + [_etiket(son, tip)]
    # tickvals ISO METİN olarak verilir: pandas.Timestamp nesnesi düzen
    # sözlüğünde kalırsa Plotly'nin HTML yazıcısı halleder ama statik görüntü
    # üreticisi (kaleido/orjson) serileştiremeyip düşer.
    fig.update_xaxes(tickmode="array",
                     tickvals=[pd.Timestamp(t).isoformat() for t in tv],
                     ticktext=list(tt), row=satir, col=1)


def _son_nokta(fig, s: pd.Series, satir: int, renk: str, tip: str = "ay",
               ondalik: int = 1, birim: str = "", ay: int = -34,
               ax: int = -46) -> None:
    """Son gözlemi işaretler ve DEĞERİYLE + TARİHİYLE etiketler."""
    s = pd.Series(s).dropna()
    if s.empty:
        return
    t, v = s.index[-1], float(s.iloc[-1])
    ts = pd.Timestamp(t).isoformat()          # bkz. _tarih_ekseni: ISO metin
    fig.add_trace(go.Scatter(x=[ts], y=[v], mode="markers", showlegend=False,
                             hoverinfo="skip",
                             marker=dict(size=7, color=renk,
                                         line=dict(width=1.2, color="white"))),
                  row=satir, col=1)
    fig.add_annotation(
        x=ts, y=v, row=satir, col=1, xanchor="right",
        text=f"<b>{_sayi(v, ondalik)}{birim}</b><br><sup>{_etiket(t, tip)}</sup>",
        showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=renk,
        ax=ax, ay=ay, align="right", bgcolor="rgba(255,255,255,0.82)",
        bordercolor=renk, borderwidth=0.8, borderpad=2,
        font=dict(size=10, color=INK))


# --------------------------------------------------------------------------- izler
def _pen(s: pd.Series, bas: str) -> pd.Series:
    """Pencere SUNUM tercihidir, ölçüm değil — ama serinin gerçek başlangıcının
    gerisine düşmemeli; düşerse eksen boş bir kuyruk çizer ve okur 'veri var
    ama sıfır' sanır."""
    s = pd.Series(s).dropna()
    if s.empty:
        return s
    return s.loc[s.index >= max(pd.Timestamp(bas), s.index[0])]


def _cizgi(fig, s, ad, renk, satir, kalin=1.9, kes=None, goster=True,
           grup=None, opak=1.0):
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, name=ad, mode="lines", legendgroup=grup or ad,
        showlegend=goster, opacity=opak,
        line=dict(color=renk, width=kalin, dash=kes)), row=satir, col=1)


def _bar(fig, s, ad, renk, satir, goster=True, grup=None, opak=0.85):
    fig.add_trace(go.Bar(x=s.index, y=s.values, name=ad, marker_color=renk,
                         legendgroup=grup or ad, showlegend=goster,
                         opacity=opak, marker_line_width=0), row=satir, col=1)


def _yigin(fig, s, ad, renk, satir, grup="yigin", goster=True):
    """Yığılmış alan. stackgroup satır BAZINDA ayrılır; aynı grup adı iki
    panelde kullanılırsa Plotly ikisini tek yığına toplar."""
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, name=ad, mode="lines", line=dict(width=0.6, color=renk),
        stackgroup=f"{grup}{satir}", fillcolor=renk, showlegend=goster,
        legendgroup=ad), row=satir, col=1)


def _sifir(fig, satir):
    fig.add_hline(y=0, line=dict(color=GRI, width=1), row=satir, col=1)


# ===========================================================================
# ŞEKİL 01 — Bütçe dengesi: aylık ve 12 aylık birikimli
# ===========================================================================
def sekil_01(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"a) Aylık gerçekleşme ({_yil(AYLIK_BAS)}→): bütçe dengesi ve "
            "faiz dışı denge (milyar TL)",
            f"b) 12 aylık birikimli ({_yil(TAM_BAS)}→): aynı iki denge "
            "(trilyon TL) — mevsimsellikten arınmış okuma"))
    _bar(fig, _pen(M["denge_ay"], AYLIK_BAS), "Bütçe dengesi (aylık)", CLARET, 1)
    _bar(fig, _pen(M["fdd_ay"], AYLIK_BAS), "Faiz dışı denge (aylık)", TEAL, 1)
    _sifir(fig, 1)
    _cizgi(fig, _pen(M["denge_12a"], TAM_BAS), "Bütçe dengesi (12 aylık)", CLARET, 2, 2.4)
    _cizgi(fig, _pen(M["fdd_12a"], TAM_BAS), "Faiz dışı denge (12 aylık)", TEAL, 2, 2.4)
    _cizgi(fig, _pen(M["gb_denge_12a"], TAM_BAS),
           "Genel bütçe dengesi (12 aylık, kapsam kontrolü)", GRI, 2, 1.3, "dot")
    _sifir(fig, 2)
    _son_nokta(fig, _pen(M["denge_ay"], AYLIK_BAS), 1, CLARET, "ay", 0, " mlr")
    _son_nokta(fig, _pen(M["denge_12a"], TAM_BAS), 2, CLARET, "ay", 2, " trl")
    _son_nokta(fig, _pen(M["fdd_12a"], TAM_BAS), 2, TEAL, "ay", 2, " trl", ay=30)
    fig.update_yaxes(title_text="milyar TL", row=1, col=1)
    fig.update_yaxes(title_text="trilyon TL", row=2, col=1)
    _tarih_ekseni(fig, 1, _pen(M["denge_ay"], AYLIK_BAS).index)
    _tarih_ekseni(fig, 2, _pen(M["denge_12a"], TAM_BAS).index)
    return _duzen(fig, f"Merkezi yönetim bütçe dengesi · veri {damga}", [
        "Merkezi yönetim dengesi EVDS'te HAZIR YOK; GEL001 − GID001 ile türetilir. "
        "Faiz dışı denge = GEL001 − GID002.",
        "Kesikli gri seri GENEL BÜTÇE dengesidir (GEN35) ve kapsam kontrolü içindir: "
        "12 aylık birikimli iki denge son 24 ayda ortalama "
        f"%{_sayi((o['butce'].get('kapsam_farki_24ay') or 0)*100, 1)} ayrışır — özel bütçeli "
        "idareler + düzenleyici kurumlar farkı. Sıfır BEKLENMEZ.",
        "Bütçe serileri AKIMDIR (aylık gerçekleşme), yıl içi kümülatif DEĞİL; "
        "EVDS kataloğundaki 'KÜMÜLATİF' etiketi düşük frekansa çevirme yöntemidir.",
        KAYNAK + " · bie_kbmgel, bie_kbmgid, bie_kbgen."], n_panel=2)


# ===========================================================================
# ŞEKİL 02 — Denge / GSYH
# ===========================================================================
def sekil_02(C, o, damga_c):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            "a) 12 aylık birikimli denge ve faiz dışı denge, 4 çeyreklik GSYH'ye oran (%)",
            "b) Faiz gideri / GSYH (%) — borç servisinin milli gelire yükü"))
    _cizgi(fig, _pen(C["denge_gsyh"], CEYREK_BAS), "Bütçe dengesi / GSYH", CLARET, 1, 2.3)
    _cizgi(fig, _pen(C["fdd_gsyh"], CEYREK_BAS), "Faiz dışı denge / GSYH", TEAL, 1, 2.3)
    _sifir(fig, 1)
    _cizgi(fig, _pen(C["faiz_gsyh"], CEYREK_BAS), "Faiz gideri / GSYH", GOLD, 2, 2.3)
    _son_nokta(fig, _pen(C["denge_gsyh"], CEYREK_BAS), 1, CLARET, "ceyrek", 2, "%")
    _son_nokta(fig, _pen(C["fdd_gsyh"], CEYREK_BAS), 1, TEAL, "ceyrek", 2, "%", ay=30)
    _son_nokta(fig, _pen(C["faiz_gsyh"], CEYREK_BAS), 2, GOLD, "ceyrek", 2, "%")
    for r in (1, 2):
        fig.update_yaxes(title_text="% GSYH", row=r, col=1)
        _tarih_ekseni(fig, r, _pen(C["faiz_gsyh"], CEYREK_BAS).index, "ceyrek")
    return _duzen(fig, f"Bütçe dengesi ve faiz yükü, GSYH'ye oran · GSYH {damga_c}", [
        "Pay: 12 aylık birikimli akım (çeyrek sonu ayından okunur). Payda: 4 çeyrek "
        "toplamı cari fiyatlarla GSYH — tek çeyreği dörtle çarpmak mevsimselliği orana taşırdı.",
        "SERİ BURADA BİTER, aylık serilerden ERKEN. GSYH yaklaşık iki çeyrek gecikmeli "
        "yayımlanıyor; GSYH'yi ileri taşıyıp (ffill) daha yeni bir oran üretmek sessiz bayatlamadır.",
        KAYNAK + " · bie_kbmgel, bie_kbmgid, bie_gsyhhrccar."], n_panel=2)


# ===========================================================================
# ŞEKİL 03 — Reel gelir ve harcama (hattın asıl hikâyesi)
# ===========================================================================
def sekil_03(M, o, damga):
    taban = o["butce"]["deflator_taban_ay"]
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"a) TÜFE ile deflate edilmiş 12 aylık birikimli gelir ve faiz dışı harcama "
            f"({taban} fiyatlarıyla, trilyon TL)",
            "b) Reel yıllık değişim (çubuk) ile nominal yıllık değişim (çizgi) — "
            "makasın hikâyesi bu panelde"))
    _cizgi(fig, _pen(M["reel_gelir_12a"], TAM_BAS), "Reel gelir", TEAL, 1, 2.4)
    _cizgi(fig, _pen(M["reel_fdg_12a"], TAM_BAS), "Reel faiz dışı harcama", CLARET, 1, 2.4)
    _cizgi(fig, _pen(M["reel_faiz_12a"], TAM_BAS), "Reel faiz gideri", GOLD, 1, 1.7)
    _bar(fig, _pen(M["gelir_reel_yy"], TAM_BAS), "Reel gelir, y/y", TEAL, 2)
    _bar(fig, _pen(M["fdg_reel_yy"], TAM_BAS), "Reel faiz dışı harcama, y/y", CLARET, 2)
    _cizgi(fig, _pen(M["gelir_nom_yy"], TAM_BAS), "Nominal gelir, y/y", LACI, 2, 1.7, "dash")
    _cizgi(fig, _pen(M["tufe_yy"], TAM_BAS), "TÜFE, y/y", GRI, 2, 1.4, "dot")
    _sifir(fig, 2)
    _son_nokta(fig, _pen(M["reel_gelir_12a"], TAM_BAS), 1, TEAL, "ay", 2, " trl")
    _son_nokta(fig, _pen(M["reel_fdg_12a"], TAM_BAS), 1, CLARET, "ay", 2, " trl", ay=32)
    _son_nokta(fig, _pen(M["gelir_reel_yy"], TAM_BAS), 2, TEAL, "ay", 1, "%")
    _son_nokta(fig, _pen(M["gelir_nom_yy"], TAM_BAS), 2, LACI, "ay", 1, "%",
               ay=-40, ax=-104)
    fig.update_yaxes(title_text=f"trilyon TL ({taban} fiyatları)", row=1, col=1)
    fig.update_yaxes(title_text="%, yıllık", row=2, col=1)
    for r in (1, 2):
        _tarih_ekseni(fig, r, _pen(M["reel_gelir_12a"], TAM_BAS).index)
    fark = o["butce"]["fisher"].get("basit_cikarma_farki_son_pp")
    return _duzen(fig, f"Reel bütçe: gelir ve harcama · veri {damga}", [
        f"Deflatör: TÜFE genel endeks, taban {taban} (son BÜTÇE ayı — son TÜFE ayı değil). "
        "Sıra bağlayıcı: önce AYLIK deflate, sonra 12 aylık toplam; önce toplayıp tek "
        "deflatörle bölmek yıl içi fiyat hareketini yok sayar.",
        "Reel değişim ÇARPIMSAL (Fisher) konvansiyonla: (1+nominal)/(1+deflatör) − 1. "
        "Basit çıkarma (nominal − enflasyon) bu depoda kullanılmaz; son gözlemde iki tanım "
        f"{_sayi(abs(fark or 0), 1)} puan ayrışıyor.",
        "Nominal seri tek başına yanıltıcıdır: gelirin nominal artışının büyük kısmı "
        "fiyat artışıdır.",
        KAYNAK + " · bie_kbmgel, bie_kbmgid, bie_tukfiy2025."], n_panel=2)


# ===========================================================================
# ŞEKİL 04 — Vergi kompozisyonu
# ===========================================================================
KALEM_VERGI = [
    ("v_gelir", "Gelir vergisi", TEAL),
    ("v_kurumlar", "Kurumlar vergisi", CLARET),
    ("v_kdv_dahil", "Dahilde alınan KDV", GOLD),
    ("v_kdv_ithal", "İthalde alınan KDV", LACI),
    ("v_otv", "ÖTV", MOR),
    ("v_damga", "Damga vergisi", YESIL),
]


def _kesit_bar(fig, M, kalemler, satir, s_ay):
    """Kalem bazında reel y/y — KESİT (son ay) + bir yıl öncesi referansı.

    Zaman serisi yerine kesit: altı kalemin ayrı ayrı zaman serisi tek panelde
    okunmuyordu. Bir yıl önceki değer gölge çubuk olarak konur ki "yüksek mi
    düşük mü" sorusunun bir çıpası olsun.
    """
    ad, simdi, once = [], [], []
    for kol, etiket, _renk in kalemler:
        s = M[f"{kol}_reel_yy"].dropna()
        if s.empty:
            continue
        ad.append(etiket)
        simdi.append(float(s.iloc[-1]))
        once.append(float(s.iloc[-13]) if len(s) > 13 else np.nan)
    fig.add_trace(go.Bar(x=ad, y=once, name="Bir yıl önce (aynı ay)",
                         marker_color=GRI, opacity=0.45, marker_line_width=0),
                  row=satir, col=1)
    # Kesit çubuğu NÖTR renkte: yığın panelindeki kalem renkleriyle aynı rengi
    # kullanmak, iki panelde farklı anlam taşıyan aynı rengi doğuruyordu.
    fig.add_trace(go.Bar(x=ad, y=simdi, name=f"{ay_ad(s_ay)} (12 aylık birikimli)",
                         marker_color=INK, marker_line_width=0), row=satir, col=1)
    _sifir(fig, satir)


def sekil_04(M, o, damga, s_ay):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.14,
        subplot_titles=(
            f"a) Vergi gelirlerinin kalem kompozisyonu ({_yil(TAM_BAS)}→), "
            "12 aylık birikimli paylar (%)",
            "b) Kalem bazında REEL yıllık değişim (%) — kesit karşılaştırması"))
    for kol, etiket, renk in KALEM_VERGI:
        _yigin(fig, _pen(M[f"pay_{kol}"], TAM_BAS), etiket, renk, 1)
    _yigin(fig, _pen(M["pay_v_diger"], TAM_BAS), "Diğer vergiler (artık)", GRI, 1)
    _kesit_bar(fig, M, KALEM_VERGI, 2, s_ay)
    fig.update_yaxes(title_text="% vergi gelirleri", row=1, col=1, range=[0, 100])
    fig.update_yaxes(title_text="%, reel yıllık", row=2, col=1)
    _tarih_ekseni(fig, 1, _pen(M["pay_v_gelir"], TAM_BAS).index)
    return _duzen(fig, f"Vergi kompozisyonu ve reel seyri · veri {damga}", [
        "Paylar 12 AYLIK BİRİKİMLİDEN alınır: aylık paylar mevsimsellikten okunamaz "
        "(kurumlar vergisi Şubat/Nisan/Ağustos'ta yığılır).",
        "'Diğer vergiler' bir ARTIK kalemdir (toplam eksi altı kalem), gizlenmiş bir "
        "kalem değil; motorlu taşıtlar, harçlar, BSMV ve tahsilattan reddiyeler buradadır.",
        "Reel değişim çarpımsal konvansiyonla; deflatör TÜFE genel endeks.",
        KAYNAK + " · bie_kbmgel, bie_tukfiy2025."], n_panel=2)


# ===========================================================================
# ŞEKİL 05 — Harcama kompozisyonu
# ===========================================================================
KALEM_GIDER = [
    ("personel", "Personel", TEAL),
    ("sgk_primi", "SGK devlet primi", YESIL),
    ("mal_hizmet", "Mal ve hizmet alımı", GOLD),
    ("cari_transfer", "Cari transferler", LACI),
    ("sermaye_gider", "Sermaye gideri (yatırım)", MOR),
    ("sermaye_transfer", "Sermaye transferi", PEMBE),
    ("borc_verme", "Borç verme", TURUNCU),
    ("faiz", "Faiz gideri", CLARET),
]


def sekil_05(M, o, damga, s_ay):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.14,
        subplot_titles=(
            f"a) Bütçe giderlerinin kalem kompozisyonu ({_yil(TAM_BAS)}→), "
            "12 aylık birikimli paylar (%)",
            "b) Kalem bazında REEL yıllık değişim (%) — kesit karşılaştırması"))
    for kol, etiket, renk in KALEM_GIDER:
        _yigin(fig, _pen(M[f"pay_{kol}"], TAM_BAS), etiket, renk, 1)
    _yigin(fig, _pen(M["pay_gider_diger"], TAM_BAS), "Diğer giderler (artık)", GRI, 1)
    _kesit_bar(fig, M, KALEM_GIDER, 2, s_ay)
    fig.update_yaxes(title_text="% toplam gider", row=1, col=1, range=[0, 100])
    fig.update_yaxes(title_text="%, reel yıllık", row=2, col=1)
    _tarih_ekseni(fig, 1, _pen(M["pay_personel"], TAM_BAS).index)
    return _duzen(fig, f"Harcama kompozisyonu ve reel seyri · veri {damga}", [
        "YALNIZ ÜST DÜZEY KALEMLER çizilir. EVDS'in gider tablosundaki pek çok alt kalem "
        "Kasım 2023'te kesiliyor ve alt kırılımların toplamı üst kalemi TUTMUYOR; "
        "alt kırılım kullanılsaydı yığın sessizce eksik kalırdı.",
        "'Diğer giderler' artık kalemdir (yedek ödenekler, hazine yardımlarının bu sekiz "
        "başlığa girmeyen kısmı vb.).",
        "Faiz gideri yığının içinde tutulur: faiz dışı harcama okuması için Şekil 03'e bakın.",
        KAYNAK + " · bie_kbmgid, bie_tukfiy2025."], n_panel=2)


# ===========================================================================
# ŞEKİL 06 — Faiz yükü
# ===========================================================================
def sekil_06(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            "a) Faiz gideri / vergi geliri ve faiz gideri / toplam gelir "
            "(12 aylık birikimli, %)",
            "b) Faiz giderinin ayrışması — iç borç, dış borç, kira sertifikası, "
            "iskonto (reel, 12 aylık birikimli, trilyon TL)"))
    _cizgi(fig, _pen(M["faiz_vergi"], TAM_BAS), "Faiz gideri / vergi geliri", CLARET, 1, 2.4)
    _cizgi(fig, _pen(M["faiz_gelir"], TAM_BAS), "Faiz gideri / toplam gelir", LACI, 1, 1.8)
    for kol, etiket, renk in (("faiz_ic", "İç borç faizi", TEAL),
                              ("faiz_dis", "Dış borç faizi", CLARET),
                              ("faiz_kira", "Kira sertifikası", GOLD),
                              ("faiz_iskonto", "İskonto ve KV nakit işlem", LACI)):
        _yigin(fig, _pen(M[f"reel_{kol}_12a"], TAM_BAS), etiket, renk, 2)
    _son_nokta(fig, _pen(M["faiz_vergi"], TAM_BAS), 1, CLARET, "ay", 1, "%")
    _son_nokta(fig, _pen(M["reel_faiz_ic_12a"], TAM_BAS), 2, TEAL, "ay", 2, " trl")
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="trilyon TL (son ay fiyatları)", row=2, col=1)
    for r in (1, 2):
        _tarih_ekseni(fig, r, _pen(M["faiz_vergi"], TAM_BAS).index)
    return _duzen(fig, f"Faiz yükü ve faiz giderinin ayrışması · veri {damga}", [
        "Faiz gideri / vergi geliri, borç servisinin vergi tabanını ne kadar yediğini "
        "ölçer; iki büyüklük de 12 aylık birikimlidir.",
        "Dış borç faizi KUR HAREKETİNE duyarlıdır ve bu yüzden ayrı gösterilir: "
        "aynı döviz kupon ödemesi, TL değer kaybettiğinde bütçede büyür.",
        "Kira sertifikası kalemi 2013'te, türev ürün gideri 2008'de başlıyor; öncesinde "
        "yığında yer almaması veri eksikliği değil, kalemin var olmamasıdır.",
        KAYNAK + " · bie_kbmgid (GID152/153/160/161/163), bie_tukfiy2025."], n_panel=2)


# ===========================================================================
# ŞEKİL 07 — Borç stoku
# ===========================================================================
def sekil_07(M, C, o, damga, damga_c):
    b = (o["stok"].get("stok_bilesen") or {})
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"a) Merkezi yönetim borç stoku, ARAÇ tabanında ({_yil(STOK_BAS)}→, "
            "trilyon TL, yığılmış)",
            "b) Stok / GSYH — bileşik stok ve uzun tarihli referans olarak "
            "finansal hesaplar (F.3+F.4) (%)"))
    _yigin(fig, _pen(M["ic_borc_trl"], STOK_BAS),
           "İç borç: yurt içinde ihraç, tüm sahipler (A09)", TEAL, 1)
    _yigin(fig, _pen(M["dis_senet_trl"], STOK_BAS),
           "Yurt dışında ihraç senet: eurobond, tüm sahipler (ST − S1311)", CLARET, 1)
    _yigin(fig, _pen(M["dis_kredi_trl"], STOK_BAS),
           "Dış krediler (G4 − yurt dışının senetleri)", GOLD, 1)
    _cizgi(fig, _pen(C["stok_gsyh"], CEYREK_BAS), "Brüt stok / GSYH", TEAL, 2, 2.3)
    if "net_stok_gsyh" in C.columns:
        _cizgi(fig, _pen(C["net_stok_gsyh"], CEYREK_BAS),
               "Net stok / GSYH (nakit varlık düşülmüş)", CLARET, 2, 2.0, "dash")
    if "fh_borc_gsyh" in C.columns:
        _cizgi(fig, _pen(C["fh_borc_gsyh"], FIN_BAS),
               "Referans: finansal hesaplar F.3+F.4 / GSYH (piyasa değerli)",
               GRI, 2, 1.5, "dot")
    _son_nokta(fig, _pen(M["toplam_borc_trl"], STOK_BAS), 1, INK, "ay", 2, " trl")
    _son_nokta(fig, _pen(C["stok_gsyh"], CEYREK_BAS), 2, TEAL, "ceyrek", 1, "%")
    fig.update_yaxes(title_text="trilyon TL", row=1, col=1)
    fig.update_yaxes(title_text="% GSYH", row=2, col=1)
    _tarih_ekseni(fig, 1, _pen(M["ic_borc_trl"], STOK_BAS).index)
    _tarih_ekseni(fig, 2, _pen(C["fh_borc_gsyh"] if "fh_borc_gsyh" in C.columns
                               else C["stok_gsyh"], FIN_BAS).index, "ceyrek")
    return _duzen(fig, f"Merkezi yönetim borç stoku · veri {damga}", [
        "Stok ARAÇ (ihraç) tabanında TÜRETİLMİŞTİR. İç borç (A09) ihraç tabanlı, brüt dış "
        "borç (G4) YERLEŞİKLİK tabanlıdır; ikisi doğrudan toplanamaz — yurt dışı "
        "yerleşiklerin elindeki DİBS iki kez sayılır, yurt içi yerleşiklerin elindeki "
        "eurobond hiç sayılmazdı.",
        f"Bu koşuda düzeltmenin büyüklüğü: iki tabanı toplayan tanım "
        f"{_sayi(b.get('eski_tanim_trl'), 2)} trilyon TL verirdi; çift sayılan DİBS "
        f"{_sayi(b.get('cift_sayilan_dibs_trl'), 2)} düşülüp eksik kalan eurobond "
        f"{_sayi(b.get('eksik_eurobond_trl'), 2)} eklendiğinde "
        f"{_sayi(b.get('toplam_trl'), 2)} trilyon TL çıkıyor "
        f"({_yuzde(b.get('duzeltme_yuzde'), 1)}).",
        f"Üst panel {_yil(STOK_BAS)}'de başlar: eurobondun sahiplik kırılımı (yurt içi / "
        "yurt dışı) haftalık menkul kıymet istatistikleriyle o tarihte başlıyor. Daha uzun "
        "ama yanlış tanımlı bir seri çizilmedi; uzun tarihli okuma alt panelde finansal "
        "hesaplar çizgisiyle verilir (piyasa değerli, bu yüzden sistematik olarak yukarıda).",
        "Dış kredi bacağı üç aylıktır ve çeyrek içinde BASAMAK olarak taşınır; son "
        f"yayımlanan çeyreğin ({o['stok']['son_dis_ceyrek']}) ötesine uzatılmaz — bileşik "
        "seri o ayda biter.",
        f"Alt panelde bileşik stok GSYH ile aynı çeyrekte biter ({damga_c}); üst panel "
        "aylıktır. İki panelin farklı yerde bitmesi hata değil, yayım gecikmesidir.",
        KAYNAK + " · bie_kbicborc, bie_ebondyazdeg, bie_dibsyazdeg, bie_brutdbborclu, "
        "bie_finhestnks7101311, bie_gsyhhrccar, bie_dkdovytl."], n_panel=2)


# ===========================================================================
# ŞEKİL 08 — TL / döviz kompozisyonu
# ===========================================================================
def sekil_08(M, H, o, damga, damga_h):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"a) Stokun para cinsi bacakları ({_yil(STOK_BAS)}→, pay %) — döviz payı "
            "ALT SINIR, yurt dışı payı AYRI bir olgu",
            f"b) Eurobond stokunun para birimi kırılımı ({_yil(HAFTA_BAS)}→, "
            "piyasa değeri payları, %)"))
    tl_pay = (100 - M["doviz_pay"]).dropna()
    _yigin(fig, _pen(tl_pay, STOK_BAS),
           "İç borç bacağı — TL + AYRIŞTIRILAMAYAN döviz cinsi yurt içi ihraç", TEAL, 1)
    _yigin(fig, _pen(M["doviz_pay"], STOK_BAS),
           "Döviz cinsi bacak: yurt dışında ihraç senet + dış kredi", CLARET, 1)
    _cizgi(fig, _pen(M["yurt_disi_pay"], STOK_BAS),
           "Karşılaştırma: YERLEŞİKLİK payı (brüt dış borç / stok)", LACI, 1, 1.8, "dash")
    if "pay_ic_satis_doviz" in M.columns:
        _cizgi(fig, _pen(M["pay_ic_satis_doviz"], STOK_BAS),
               "Kanıt: iç borçlanma SATIŞININ döviz cinsi payı (12 aylık, akım)",
               GOLD, 1, 1.5, "dot")
    for kol, etiket, renk in (("pay_eb_usd", "ABD doları", TEAL),
                              ("pay_eb_eur", "Euro", CLARET),
                              ("pay_eb_jpy", "Japon yeni", GOLD)):
        _yigin(fig, _pen(H[kol], HAFTA_BAS), etiket, renk, 2)
    _son_nokta(fig, _pen(M["doviz_pay"], STOK_BAS), 1, CLARET, "ay", 1, "%")
    _son_nokta(fig, _pen(H["pay_eb_eur"], HAFTA_BAS), 2, CLARET, "gun", 1, "%")
    fig.update_yaxes(title_text="% toplam stok", row=1, col=1, range=[0, 100])
    fig.update_yaxes(title_text="% eurobond stoku", row=2, col=1, range=[0, 100])
    _tarih_ekseni(fig, 1, _pen(M["doviz_pay"], STOK_BAS).index)
    _tarih_ekseni(fig, 2, _pen(H["pay_eb_usd"], HAFTA_BAS).index)
    return _duzen(fig, f"Borç stokunun para kompozisyonu · veri {damga}", [
        "DÖVİZ PAYI ile YURT DIŞI PAYI aynı şey değildir ve bu panel ikisini ayırır. Döviz "
        "payı gerçekten döviz cinsi iki bacaktır (yurt dışında ihraç senet + dış kredi); "
        "yerleşiklik payı ise alacaklısı yurt dışında olan tutardır ve içinde yurt dışı "
        "yerleşiklerin elindeki TL cinsi DİBS de vardır.",
        "DÖVİZ PAYI ALT SINIRDIR: iç borç stokunun içindeki DÖVİZ CİNSİ yurt içi ihraçlar "
        "EVDS'te stok olarak ayrıştırılamıyor. Küçük değiller — noktalı çizgi, iç borçlanma "
        "SATIŞININ döviz cinsi payını (12 aylık birikimli akım) gösterir; son gözlemde "
        f"{_yuzde(float(M['pay_ic_satis_doviz'].dropna().iloc[-1]), 1)}.",
        "Finansman akımlarını (GEN53/54) kümüle ederek döviz cinsi iç STOK tahmin etmek "
        "DENENDİ ve REDDEDİLDİ: kur farkı revalüasyonunu yok saydığı için iç borcun yalnız "
        "~%1'ini veriyor. Akım payı bir kanıttır, stok tahmini değildir.",
        f"Alt panel haftalık menkul kıymet istatistiklerinden gelir (son {damga_h}) ve "
        "PİYASA değeri üzerindendir; yazılı değer toplamıyla karıştırılamaz.",
        KAYNAK + " · bie_kbicborc, bie_kbgen, bie_ebondyazdeg, bie_dibsyazdeg, "
        "bie_brutdbborclu, bie_ebondvade."], n_panel=2)


# ===========================================================================
# ŞEKİL 09 — Kur duyarlılığı (panel + tablo)
# ===========================================================================
def sekil_09(o, damga):
    s = o.get("senaryo") or {}
    if not s.get("satirlar"):
        return None
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12, row_heights=[0.58, 0.42],
        specs=[[{"type": "xy"}], [{"type": "table"}]],
        subplot_titles=(
            f"a) USD/TRY şoku altında borç stoku (çıpa {s['cipa_ay']}, trilyon TL) — "
            "şok yalnız döviz cinsi bacağa",
            "b) Senaryo tablosu"))
    kur = [r["kur"] for r in s["satirlar"]]
    fig.add_trace(go.Scatter(
        x=kur, y=[r["stok_paralel_trl"] for r in s["satirlar"]],
        name="Paralel şok (TL bütün dövizlere karşı)", mode="lines+markers",
        line=dict(color=CLARET, width=2.4), marker=dict(size=7)), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=kur, y=[r["stok_yalniz_usd_trl"] for r in s["satirlar"]],
        name=f"Yalnız USD bacağı (ağırlık %{_sayi(s['agirlik']['usd']*100, 1)})",
        mode="lines+markers", line=dict(color=TEAL, width=2.0, dash="dash"),
        marker=dict(size=6)), row=1, col=1)
    fig.add_vline(x=s["kur"], line=dict(color=GRI, width=1.4, dash="dot"),
                  row=1, col=1)
    fig.add_annotation(x=s["kur"], y=s["toplam_trl"], row=1, col=1,
                       text=f"<b>mevcut kur {_sayi(s['kur'], 2)}</b><br>"
                            f"<sup>stok {_sayi(s['toplam_trl'], 2)} trl TL</sup>",
                       showarrow=True, arrowhead=0, arrowcolor=GRI, ax=-58, ay=-40,
                       bgcolor="rgba(255,255,255,0.85)", bordercolor=GRI,
                       borderwidth=0.8, borderpad=2, font=dict(size=10, color=INK))
    fig.update_xaxes(title_text="USD/TRY", row=1, col=1)
    fig.update_yaxes(title_text="trilyon TL", row=1, col=1)

    basliklar = ["Şok", "USD/TRY", "Stok · paralel<br>(trl TL)",
                 "Değişim<br>(%)", "Stok · yalnız USD<br>(trl TL)",
                 "Stok/GSYH · paralel<br>(%)"]
    hucre = [
        # Türkçe yazımda işaret yüzde imininin ÖNÜNE gelir: "−%10", "%−10" değil.
        [("0" if not r["sok"] else
          ("−" if r["sok"] < 0 else "+") + "%" + _sayi(abs(r["sok"]) * 100, 0))
         for r in s["satirlar"]],
        [_sayi(r["kur"], 2) for r in s["satirlar"]],
        [_sayi(r["stok_paralel_trl"], 2) for r in s["satirlar"]],
        [_sayi(r["degisim_paralel_yuzde"], 1) for r in s["satirlar"]],
        [_sayi(r["stok_yalniz_usd_trl"], 2) for r in s["satirlar"]],
        [_sayi(r.get("stok_gsyh_paralel"), 1) for r in s["satirlar"]],
    ]
    fig.add_trace(go.Table(
        header=dict(values=basliklar, fill_color="#f5f2ec", align="right",
                    font=dict(size=11, color=INK, family="Georgia, serif"),
                    line_color=GRID, height=42),
        cells=dict(values=hucre, fill_color="white", align="right",
                   font=dict(size=11, color=INK, family="Georgia, serif"),
                   line_color=GRID, height=24)), row=2, col=1)
    return _duzen(fig, f"Kur duyarlılığı: borç stoku şok altında · veri {damga}", [
        "Şok yalnız GERÇEKTEN DÖVİZ CİNSİ bacağa uygulanır: yurt dışında ihraç edilen senet "
        f"+ dış krediler (stokun %{_sayi(s.get('doviz_pay'), 1)}'i). Brüt dış borcun "
        "tamamına uygulanamaz — içinde yurt dışı yerleşiklerin elindeki TL cinsi DİBS de "
        "vardır ve o tutar kur şokunda TL cinsinden DEĞİŞMEZ.",
        "TL TUTARI SÜTUNU ALT SINIRDIR: iç borç stokunun içindeki DÖVİZ CİNSİ yurt içi "
        "ihraçlar EVDS'te ayrıştırılamadığı için şok dışında kaldı; gerçek etki "
        "tablodakinden BÜYÜKTÜR.",
        "PARALEL senaryoda TL bütün dövizlere karşı aynı oranda değer kaybeder. YALNIZ USD "
        "senaryosunda EUR/TRY ve JPY/TRY sabit kalır; şok dolar ağırlığı kadar geçer.",
        f"Para birimi ağırlıkları eurobond tablosundan (USD %{_sayi(s['agirlik']['usd']*100,1)} · "
        f"EUR %{_sayi(s['agirlik']['eur']*100,1)} · JPY %{_sayi(s['agirlik']['jpy']*100,1)}) alınıp "
        "döviz bacağının tamamına VEKİL olarak uygulanmıştır — dış kredilerin para "
        "kompozisyonu EVDS'te yayımlanmıyor.",
        f"STOK/GSYH SÜTUNU ise ÜST SINIRDIR: çıpası {s.get('cipa_ceyrek')} çeyreğidir ve "
        "GSYH SABİT varsayılmıştır; gerçek bir şokta nominal GSYH de büyür.",
        KAYNAK + " · bie_kbicborc, bie_ebondyazdeg, bie_dibsyazdeg, bie_brutdbborclu, "
        "bie_ebondvade, bie_gsyhhrccar."],
        n_panel=2, ek_yukseklik=60)


# ===========================================================================
# ŞEKİL 10 — Vade yapısı
# ===========================================================================
def sekil_10(H, o, damga_h):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            "a) DİBS — kalan vadesi 1 yıldan kısa olanın payı (%), piyasa değeri "
            "tablosu üzerinden",
            "b) Eurobond — kalan vadesi 1 yıldan kısa olanın payı (%)"))
    _cizgi(fig, _pen(H["pay_dibs_kv_kisa"], HAFTA_BAS),
           "Kalan vade < 1 yıl (DİBS)", CLARET, 1, 2.3)
    _cizgi(fig, _pen(H["pay_dibs_ov_kisa"], HAFTA_BAS),
           "Orijinal vade kısa (referans)", GRI, 1, 1.4, "dot")
    _cizgi(fig, _pen(H["pay_eb_kv_kisa"], HAFTA_BAS),
           "Kalan vade < 1 yıl (eurobond)", TEAL, 2, 2.3)
    _son_nokta(fig, _pen(H["pay_dibs_kv_kisa"], HAFTA_BAS), 1, CLARET, "gun", 1, "%")
    _son_nokta(fig, _pen(H["pay_eb_kv_kisa"], HAFTA_BAS), 2, TEAL, "gun", 1, "%")
    for r in (1, 2):
        fig.update_yaxes(title_text="%", row=r, col=1)
        _tarih_ekseni(fig, r, _pen(H["pay_dibs_kv_kisa"], HAFTA_BAS).index)
    oran = o["haftalik"].get("eb_toplam_farki", {})
    return _duzen(fig, f"Vade yapısı: kısa vade payı · veri {damga_h}", [
        "ORTALAMA VADE EVDS'TE YOK. Kısa vade payı bir VEKİL göstergedir ve öyle "
        "etiketlenir: vadesi bir yıldan kısa kalan stokun toplam içindeki oranı.",
        "BİRİM NOTU: vade tabloları YAZILI (nominal) değil PİYASA değeri üzerindendir "
        f"(DİBS'te piyasa/yazılı oranı {_sayi(float((H['dibs_piyasa_yazili_oran'].dropna().iloc[-1])), 2)}×). "
        "Pay, HER ZAMAN kendi tablosunun toplamına bölünerek alınır; yazılı stoka "
        "uygulanırsa yaklaşık %20'lik sessiz hata doğar.",
        f"Eurobond tarafında yazılı değer {_sayi(oran.get('yazili_mlrusd'), 1)} mlr USD, piyasa "
        f"değeri {_sayi(oran.get('piyasa_mlrusd'), 1)} mlr USD — iki toplam birbirinin yerine "
        "kullanılamaz.",
        KAYNAK + " · bie_dibsvade, bie_ebondvade."], n_panel=2)


# ===========================================================================
# ŞEKİL 11 — DİBS sahiplik kompozisyonu
# ===========================================================================
def sekil_11(H, o, damga_h):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"a) DİBS stokunu ELİNDE TUTAN sektörler ({_yil(HAFTA_BAS)}→), "
            "yazılı değer payları (%)",
            "b) Yurt dışı yerleşiklerin payı (%)"))
    for kol, etiket, renk in (
            ("pay_dibs_bankalar", "Bankalar", TEAL),
            ("pay_dibs_diger_yurtici", "Diğer yurt içi yerleşikler", LACI),
            ("pay_dibs_fonlar", "Yatırım fonları", GOLD),
            ("pay_dibs_tcmb", "TCMB", MOR),
            ("pay_dibs_yurtdisi", "Yurt dışı yerleşikler", CLARET)):
        _yigin(fig, _pen(H[kol], HAFTA_BAS), etiket, renk, 1)
    _cizgi(fig, _pen(H["pay_dibs_yurtdisi"], HAFTA_BAS),
           "Yurt dışı yerleşik payı", CLARET, 2, 2.4)
    _son_nokta(fig, _pen(H["pay_dibs_bankalar"], HAFTA_BAS), 1, TEAL, "gun", 1, "%")
    _son_nokta(fig, _pen(H["pay_dibs_yurtdisi"], HAFTA_BAS), 2, CLARET, "gun", 1, "%")
    fig.update_yaxes(title_text="% DİBS stoku", row=1, col=1, range=[0, 100])
    fig.update_yaxes(title_text="%", row=2, col=1)
    for r in (1, 2):
        _tarih_ekseni(fig, r, _pen(H["pay_dibs_yurtdisi"], HAFTA_BAS).index)
    return _duzen(fig, f"DİBS sahiplik kompozisyonu · veri {damga_h}", [
        "Sektör kırılımı İHRAÇÇI değil senedi ELİNDE TUTAN taraftır; ihraççı zaten genel "
        "yönetimdir. 'Diğer yurt içi yerleşikler' artık kalemdir (S.1 eksi TCMB, bankalar "
        "ve yatırım fonları).",
        "Paylar YAZILI (nominal) değer tablosunun kendi toplamına bölünerek alınır — vade "
        "tablosunun piyasa değerli toplamıyla karıştırılmaz.",
        "Yurt dışı yerleşik payı ForeignHoldings hattıyla ÇAKIŞIR; burada yalnız borç stoku "
        "bağlamında verilir, portföy akımı okuması o hattadır.",
        KAYNAK + " · bie_dibsyazdeg."], n_panel=2)


# ===========================================================================
# ŞEKİL 12 — İç borç çevirme oranı
# ===========================================================================
def sekil_12(M, o, damga):
    c = o["stok"].get("cevirme") or {}
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            "a) İç borç çevirme oranı, 12 aylık birikimli (%) — anapara ve "
            "anapara + iç borç faizi",
            f"b) Net borçlanma, aylık ({_yil(AYLIK_BAS)}→, milyar TL): iç ve dış bacak"))
    _cizgi(fig, _pen(M["cevirme"], TAM_BAS),
           "Çevirme oranı — anapara (satış ÷ itfa)", CLARET, 1, 2.4)
    _cizgi(fig, _pen(M["cevirme_faiz"], TAM_BAS),
           "Çevirme oranı — anapara + iç borç faizi", LACI, 1, 1.9, "dash")
    fig.add_hline(y=100, line=dict(color=GRI, width=1, dash="dot"), row=1, col=1)
    _bar(fig, _pen(M["ic_borclanma_net_ay"], AYLIK_BAS), "Net iç borçlanma", TEAL, 2)
    _bar(fig, _pen(M["dis_borclanma_net_ay"], AYLIK_BAS), "Net dış borçlanma", CLARET, 2)
    _sifir(fig, 2)
    _son_nokta(fig, _pen(M["cevirme"], TAM_BAS), 1, CLARET, "ay", 0, "%")
    _son_nokta(fig, _pen(M["cevirme_faiz"], TAM_BAS), 1, LACI, "ay", 0, "%", ay=32)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="milyar TL", row=2, col=1)
    _tarih_ekseni(fig, 1, _pen(M["cevirme"], TAM_BAS).index)
    _tarih_ekseni(fig, 2, _pen(M["ic_borclanma_net_ay"], AYLIK_BAS).index)
    return _duzen(fig, f"İç borç çevirme oranı ve net borçlanma · veri {damga}", [
        "Bu oran FİNANSMAN TABLOSUNDAN hesaplanır (satış ÷ itfa) ve Hazine İhraç hattındaki "
        "İHALE bazlı karşılama oranıyla AYNI ŞEY DEĞİLDİR — ihale tarafı için o sayfaya bakın.",
        "12 AYLIK BİRİKİMLİ ZORUNLUDUR: itfasız aylarda payda sıfıra yaklaşır ve aylık oran "
        f"patlar. Ölçülen son 5 yıl bandı %{_sayi(c.get('bant_5y_min'), 0)}–"
        f"%{_sayi(c.get('bant_5y_max'), 0)}.",
        "Faiz dahil varyantta paydaya İÇ BORÇ FAİZ ÖDEMELERİ (GID153) eklenir; iki tanım "
        "aynı grafikte ayrı çizilir çünkü 'çevirme oranı' terimi ikisi için de kullanılıyor.",
        "Satış kalemleri: TL/döviz bono ve tahvil satışları (GEN47+50+53+63). İtfa: aynı "
        "kalemlerin ödeme bacağı. Döviz cinsi bono kalemi 2019'da başlar.",
        "Alt panelde iki bar YIĞILIDIR: net iç ve net dış borçlanma toplandığında "
        "toplam net borçlanmayı (GEN41) verir — bu iki kalem bir toplamın bileşenidir.",
        KAYNAK + " · bie_kbgen, bie_kbmgid."], n_panel=2, barmode="relative")


# ===========================================================================
# ŞEKİL 13 — Net borç ve Hazine nakit varlığı
# ===========================================================================
def sekil_13(C, o, damga_fh):
    """damga_fh: finansal hesaplar bacağının KENDİ çeyreği (GSYH'ninki değil)."""
    if "net_fin_deger_trl" not in C.columns:
        return None
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"a) Merkezi yönetimin finansal yükümlülükleri, varlıkları ve NET FİNANSAL "
            f"DEĞERİ ({_yil(FIN_BAS)}→, trilyon TL)",
            "b) Hazine nakit varlığı ile brüt ve net borç stoku (trilyon TL)"))
    _cizgi(fig, _pen(C["yukum_toplam_trl"], FIN_BAS),
           "Toplam yükümlülük (F.0)", CLARET, 1, 2.2)
    _cizgi(fig, _pen(C["varlik_toplam_trl"], FIN_BAS),
           "Toplam finansal varlık (VF.0)", TEAL, 1, 2.2)
    _cizgi(fig, _pen(C["net_fin_deger_trl"], FIN_BAS),
           "Net finansal değer (BF.9)", LACI, 1, 2.4)
    _cizgi(fig, _pen(C["borc_senedi_trl"], FIN_BAS),
           "Borçlanma senetleri (F.3)", GOLD, 1, 1.5, "dot")
    _sifir(fig, 1)
    # "Brüt − net farkı" TANIM GEREĞİ nakit varlığa eşittir; ayrı bir seri
    # olarak çizilirse iki çizgi birebir üst üste biner ve panel bilgi taşımaz.
    # Onun yerine iki STOK DÜZEYİ ile nakit varlık birlikte gösterilir.
    if "net_stok_trl" in C.columns:
        _cizgi(fig, _pen(C["stok_trl"], FIN_BAS), "Brüt borç stoku", GRI, 2, 1.6, "dot")
        _cizgi(fig, _pen(C["net_stok_trl"], FIN_BAS),
               "Net borç stoku (nakit varlık düşülmüş)", CLARET, 2, 2.0, "dash")
    _cizgi(fig, _pen(C["nakit_trl"], FIN_BAS),
           "Hazine nakit varlığı (VF.2 para ve mevduat)", TEAL, 2, 2.3)
    _son_nokta(fig, _pen(C["net_fin_deger_trl"], FIN_BAS), 1, LACI, "ceyrek", 2, " trl")
    _son_nokta(fig, _pen(C["nakit_trl"], FIN_BAS), 2, TEAL, "ceyrek", 2, " trl")
    for r in (1, 2):
        fig.update_yaxes(title_text="trilyon TL", row=r, col=1)
        _tarih_ekseni(fig, r, _pen(C["net_fin_deger_trl"], FIN_BAS).index, "ceyrek")
    d = (o.get("dogrulama") or {}).get("DİBS+eurobond ↔ finansal hesaplar F.3", {})
    return _duzen(fig, f"Net borç göstergeleri (finansal hesaplar) · veri {damga_fh}", [
        "Finansal hesaplar ÜÇ AYLIKTIR ve bu hattın en gecikmeli ailesidir (yaklaşık iki "
        "çeyrek). Panel bu yüzden aylık serilerden erken biter.",
        "Net finansal değer (BF.9) = finansal varlıklar − yükümlülükler. Negatif olması "
        "beklenir; 'net borç' kavramının finansal hesaplar karşılığıdır.",
        "BAĞIMSIZ DOĞRULAMA: DİBS + eurobond yazılı değer toplamı ile F.3 kalemi ÖZDEŞ "
        f"DEĞİLDİR, bantlıdır — son çeyrekte fark {_yuzde((d.get('son_fark') or 0)*100, 1)} "
        f"(son altı çeyrek bandı {_yuzde((d.get('son6_min') or 0)*100, 1)}…"
        f"{_yuzde((d.get('son6_max') or 0)*100, 1)}). Finansal hesaplar piyasa değerlidir ve "
        "kapsamı biraz geniştir; farkı sıfıra zorlayan düzeltme YAPILMAZ.",
        KAYNAK + " · bie_finhestnks7101311, bie_dibsyazdeg, bie_ebondyazdeg."], n_panel=2)


# ===========================================================================
def _yukle():
    M = pd.read_csv(VERI / "aylik_metrik.csv", index_col=0, parse_dates=True)
    C = pd.read_csv(VERI / "ceyreklik_metrik.csv", index_col=0, parse_dates=True)
    H = pd.read_csv(VERI / "haftalik_metrik.csv", index_col=0, parse_dates=True)
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    return M, C, H, o


def kos() -> None:
    M, C, H, o = _yukle()
    s_ay = pd.Timestamp(o["son_ay"])
    s_ceyrek = pd.Timestamp(o["son_ceyrek"])
    s_hafta = pd.Timestamp(o["son_hafta"])
    damga, damga_c, damga_h = ay_ad(s_ay), ceyrek_ad(s_ceyrek), gun_ad(s_hafta)
    # ŞEKİL 13'ÜN DAMGASI GSYH'NİN DEĞİL, FİNANSAL HESAPLARIN ÇEYREĞİDİR. Figür
    # "veri 2026-Ç2" diyordu, çizdiği her seri 2026-Ç1'de bitiyordu (09.09.2026'da
    # ölçüldü): iki kurum aynı çeyreklik dosyada durur ama ayrı takvimle yayımlar.
    # Uç, çizilen sütunlardan ölçülür (veri.bacak_ucu) — özetin `finhesap_tarih`i
    # ile aynı listeden, yani sayfadaki damga ile figürün içindeki alt yazı aynı
    # çeyreği söyler.
    s_fh = veri.bacak_ucu(C, veri.FH_KOLONLAR)
    damga_fh = ceyrek_ad(s_fh) if s_fh is not None else "—"
    print(f"Merkezi yönetim bütçesi & borç stoku — grafikler · bütçe {damga}")

    ciktilar = [
        (sekil_01(M, o, damga), "01_denge_aylik.html"),
        (sekil_02(C, o, damga_c), "02_denge_gsyh.html"),
        (sekil_03(M, o, damga), "03_reel_gelir_harcama.html"),
        (sekil_04(M, o, damga, s_ay), "04_vergi_kompozisyon.html"),
        (sekil_05(M, o, damga, s_ay), "05_harcama_kompozisyon.html"),
        (sekil_06(M, o, damga), "06_faiz_yuku.html"),
        (sekil_07(M, C, o, damga, damga_c), "07_borc_stoku.html"),
        (sekil_08(M, H, o, damga, damga_h), "08_tl_doviz.html"),
        (sekil_09(o, damga), "09_kur_duyarlilik.html"),
        (sekil_10(H, o, damga_h), "10_vade_yapisi.html"),
        (sekil_11(H, o, damga_h), "11_dibs_sahiplik.html"),
        (sekil_12(M, o, damga), "12_cevirme_orani.html"),
        (sekil_13(C, o, damga_fh), "13_net_borc.html"),
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
    print(f"  {n}/{len(ciktilar)} grafik yazıldı → {CIKTI}")
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
