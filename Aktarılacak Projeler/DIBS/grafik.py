# -*- coding: utf-8 -*-
"""DİBS verim eğrisi & reel faiz — grafik katmanı (Plotly, site ev stili).

Kurallar (site sözleşmesi):
  · Çok panelli figürlerde paneller ALT ALTA (rows=N, cols=1). YAN YANA PANEL YOK.
  · Panel başına ~340 px + başlık/lejant payı; buradaki `height` MDX'teki
    `yukseklik={}` ile AYNI olmak zorunda (cikti/yukseklikler.json tek kaynak).
  · Başlık solda, iki satır: "<b>Başlık</b><br><sup>alt başlık</sup>".
  · Lejant altta yatay, beyaz zemin, include_plotlyjs="cdn",
    config: responsive=True, displaylogo=False.
  · Tarih ekseninde TÜRKÇE ay adları (Plotly varsayılanı İngilizce basar).
  · Son gözlem her zaman ANOTASYONLA işaretlenir — bayat grafik gözle görünür.
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

import metrik
import veri
from veri import VERI, AY_KISA, gun_ad

CIKTI = veri.PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

# Ev stili jetonları — site/tools/plotly_stil.py ve diğer hatlarla aynı
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
LACI, MOR, YESIL, GRI = "#2f4b7c", "#665191", "#7a9e7e", "#8a8a8a"
PALET = [TEAL, CLARET, GOLD, LACI, MOR, "#a05195", YESIL, GRI]
TARAMA = "rgba(142,31,47,0.10)"        # ters eğri / makas dolgusu
TARAMA2 = "rgba(29,92,92,0.10)"
# Seviye ısı haritası için ev renk ölçeği (açık kâğıt → teal → altın → bordo)
ISI = [[0.0, "#f6f2ea"], [0.25, "#bcd4d0"], [0.5, "#1d5c5c"],
       [0.75, "#9a7327"], [1.0, "#8e1f2f"]]

PANEL_PX = 340

# Pencereler. Sabitler burada; panel başlıklarındaki yıllar bu sabitlerden
# TÜRETİLİR — sabit değişince başlık da değişsin, sessizce yanlışa dönmesin.
YAKIN_BAS = "2023-01-01"
TAM_BAS = "2013-01-01"
TLREF_BAS = "2019-01-02"


def _yil(t: str) -> int:
    return int(str(t)[:4])


_ETIKET = {"n3a": "3 ay", "n6a": "6 ay", "n1y": "1 yıl", "n2y": "2 yıl",
           "n3y": "3 yıl", "n5y": "5 yıl", "n7y": "7 yıl", "n9y": "9 yıl"}


def _dugum_etiket(k: str) -> str:
    return _ETIKET.get(k, k)


# --------------------------------------------------------------------------- düzen
# Başlık bloğunda bir <sup> satırına sığan yaklaşık karakter. Fonlama hattı
# 150 kullanıyor; BURADA 130: bu hattın alt başlıkları formül ve büyük harfli
# uyarı içerdiği için ortalama karakter genişliği daha büyük ve 150'de satır
# figürün sağından TAŞIYORDU (ölçüldü, 1100 px genişlikte kırpıldı).
SATIR_SINIR = 130


def _sayi(x, ondalik: int = 0) -> str:
    """Türkçe sayı biçimi: binlik ayracı nokta, ondalık ayracı virgül."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _bol(metin: str, sinir: int = SATIR_SINIR) -> list[str]:
    """Uzun alt başlık satırını KELİME sınırından böler (Plotly sarmıyor)."""
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
    konumlu bir dipnot uzun figürlerde lejantın üstüne binerdi. Açıklama
    satırları bu yüzden BAŞLIK bloğunda (<sup>) taşınır.
    """
    alt = [parca for satir in alt for parca in _bol(satir)]
    l_satir = _lejant_satir(fig)
    # ÜST MARJ İNCE AYARI: plotly_stil.py margin.t'yi önce koşulsuz 92'ye çeker,
    # sonra YALNIZCA mevcut değer gerekenden küçükse yükseltir; doğru değeri
    # buraya yazmak ters teper, bir eksik yazılır.
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
        hoverlabel=dict(bgcolor="white", bordercolor=GRID))
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=GRID,
                     automargin=True)
    if y_baslik:
        fig.update_yaxes(title_text=y_baslik)
    return fig


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


def _iz(fig, x, y, ad, renk, satir, kalin=1.8, kes=None, dolgu=None,
        dolgu_renk=None, grup=None, goster=True, opacity=1.0, mod="lines"):
    fig.add_trace(go.Scatter(
        x=x, y=y, name=ad, mode=mod, legendgroup=grup or ad,
        showlegend=goster, opacity=opacity,
        line=dict(color=renk, width=kalin, dash=kes),
        marker=dict(color=renk, size=5),
        fill=dolgu, fillcolor=dolgu_renk),
        row=satir, col=1)


def _tarih_ekseni(fig, x, satir: int) -> None:
    """Tarih ekseninde TÜRKÇE ay adları.

    Plotly ay kısaltmalarını İngilizce basar ve yerel ayar seçeneği yok;
    tick'ler burada elle üretilir. Adım pencerenin uzunluğundan seçilir:
    uzun tarihçede yıl, orta pencerede altı ay, kısa pencerede üç ay.
    """
    x = pd.DatetimeIndex(x)
    if len(x) == 0:
        return
    bas, son = x.min(), x.max()
    yil_span = (son - bas).days / 365.25
    if yil_span > 7:
        vals = pd.date_range(bas.normalize().replace(month=1, day=1), son,
                             freq="YS")
        text = [str(t.year) for t in vals]
    elif yil_span > 2.5:
        vals = pd.date_range(bas.normalize().replace(day=1), son, freq="6MS")
        text = [f"{AY_KISA[t.month]}-{str(t.year)[2:]}" for t in vals]
    else:
        vals = pd.date_range(bas.normalize().replace(day=1), son, freq="3MS")
        text = [f"{AY_KISA[t.month]}-{str(t.year)[2:]}" for t in vals]
    fig.update_xaxes(tickmode="array", tickvals=list(vals), ticktext=text,
                     row=satir, col=1)


def _son_isaret(fig, s: pd.Series, satir: int, renk: str, ondalik: int = 2,
                birim: str = "%", kaydir: int = -46) -> None:
    """Son gözlemi noktayla ve etiketle işaretle (bayatlık gözle görünsün)."""
    s = s.dropna()
    if s.empty:
        return
    t, v = s.index[-1], float(s.iloc[-1])
    fig.add_trace(go.Scatter(
        x=[t], y=[v], mode="markers", marker=dict(color=renk, size=7),
        showlegend=False, hoverinfo="skip"), row=satir, col=1)
    fig.add_annotation(
        x=t, y=v, text=f"<b>{_sayi(v, ondalik)}{birim}</b>", showarrow=False,
        xanchor="left", xshift=8, yshift=0, font=dict(size=11, color=renk),
        bgcolor="rgba(255,255,255,0.75)", row=satir, col=1)


def _pencere(df: pd.DataFrame, bas: str) -> pd.DataFrame:
    """Pencere sabitleri SUNUM tercihidir, ölçüm değil — ama serinin gerçek
    başlangıcının gerisine düşmemeleri gerekir; düşerlerse eksen boş bir
    kuyruk çizer ve okur 'veri var ama sıfır' sanır."""
    if df.empty:
        return df
    bas_t = max(pd.Timestamp(bas), df.index[0])
    return df.loc[df.index >= bas_t]


def _egri_ciz(t: np.ndarray, y: np.ndarray, adim: float = 0.02):
    """Ham noktalardan 'uydurulan eğri' — tekilleştirilmiş vadeler arasında
    doğrusal ara değer. Uydurmanın verinin üstüne ne kadar bindiği görünsün
    diye noktalar AYRICA çizilir."""
    tekil = np.unique(np.round(t, 6))
    y_tekil = np.array([np.median(y[np.isclose(t, v)]) for v in tekil])
    if len(tekil) < 2:
        return tekil, y_tekil
    izgara = np.arange(tekil[0], tekil[-1] + adim, adim)
    return izgara, metrik._ara_deger(tekil, y_tekil, izgara)


# ===========================================================================
# ŞEKİL 01 — Bugünün spot eğrisi ve nereden geldiği
# ===========================================================================
KIYAS_ETIKET = {"bugun": ("Bugün", CLARET, 2.4),
                "1ay": ("1 ay önce", TEAL, 1.6),
                "3ay": ("3 ay önce", GOLD, 1.4),
                "1yil": ("1 yıl önce", GRI, 1.3)}


def sekil_01(KE, M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            "a) Spot (sıfır kuponlu) eğri: bugün ve geçmiş kesitler — noktalar "
            "tek tek strip'ler, çizgi bunlardan uydurulan eğri",
            "b) Bugünkü eğrinin geçmiş kesitlere göre değişimi (baz puan, "
            "sabit vadeli düğümler)"))
    kesitler = {ad: g for ad, g in KE.groupby("kesit")}
    for ad in ("1yil", "3ay", "1ay", "bugun"):
        if ad not in kesitler:
            continue
        etiket, renk, kalin = KIYAS_ETIKET[ad]
        g = kesitler[ad].sort_values("vade_yil")
        tarih = str(g["tarih"].iloc[0])
        t = g["vade_yil"].to_numpy()
        y = g["getiri"].to_numpy()
        gx, gy = _egri_ciz(t, y)
        fig.add_trace(go.Scatter(
            x=gx, y=gy, mode="lines", name=f"{etiket} ({tarih})",
            legendgroup=ad, line=dict(color=renk, width=kalin)), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=t, y=y, mode="markers", name=f"{etiket} — ham strip",
            legendgroup=ad, showlegend=False,
            marker=dict(color=renk, size=4, opacity=0.55 if ad != "bugun" else 0.85,
                        symbol="circle")), row=1, col=1)
    # (b) düğüm bazında değişim
    dugumler = [(d, metrik.DUGUM_AD[d]) for d in metrik.DUGUM]
    kiyas_gun = o["kiyas_gunleri"]
    bugun_g = pd.Timestamp(kiyas_gun["bugun"])
    for ad, renk in (("1ay", TEAL), ("3ay", GOLD), ("1yil", GRI)):
        if ad not in kiyas_gun:
            continue
        g = pd.Timestamp(kiyas_gun[ad])
        fark = [(M.loc[bugun_g, k] - M.loc[g, k]) * 100.0 for _, k in dugumler]
        fig.add_trace(go.Bar(
            x=[f"{d:g} yıl" if d >= 1 else f"{int(d * 12)} ay" for d, _ in dugumler],
            y=fark, name=f"{KIYAS_ETIKET[ad][0]}sine göre", marker_color=renk,
            opacity=0.85), row=2, col=1)
    fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=2, col=1)
    fig.update_xaxes(title_text="vade (yıl)", row=1, col=1)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="baz puan", row=2, col=1)
    fig.update_layout(barmode="group")

    kim = o["kimlik"]
    ev = o.get("evren", {})
    n_son = int(o["kapsama"]["nokta_son"])
    alt = [
        f"Veri: TCMB EVDS3 · DİBS gösterge değerleri · Çıpa: {damga}. "
        f"Eğri {n_son} sıfır kuponlu strip'ten kuruluyor; vade aralığı "
        f"{_sayi(M.loc[bugun_g, 'vade_min'], 2)}–"
        f"{_sayi(M.loc[bugun_g, 'vade_maks'], 2)} yıl.",
        "BOOTSTRAP YOK: TCMB her sabit kuponlu DİBS'in anapara ve kupon "
        "strip'lerini ayrı yayımlıyor; strip sıfır kuponlu olduğu için spot "
        "getiri doğrudan okunuyor — y = (ödeme/fiyat)^(365/kalan gün) − 1, "
        "ACT/365 yıllık bileşik.",
        "Ödeme: anapara strip'inde 100 TL; kupon strip'inde o serinin kendi "
        "<i>.ORAN</i> değeri. <i>.ORAN</i> adı 'Kupon Faiz Oranı' olsa da "
        "içerik DÖNEMSEL KUPON TUTARIDIR, yıllık oran değildir.",
        ("Kimlik denetimi: aynı itfa gününe düşen bağımsız strip'ler aynı "
         f"getiriyi vermeli. Çıpa gününde {kim['cok_kaynakli_vade_son']} vadede "
         f"çoklu kaynak var, medyan sapma {_sayi(kim['medyan_son'], 4)} puan "
         f"(eşik {_sayi(kim['esik_medyan'], 2)})."),
        ("Ara değer doğrusaldır ve EKSTRAPOLASYON YAPMAZ; iki komşu nokta "
         "arasındaki boşluk vadeye göre belirlenen sınırı aşarsa o düğüm "
         "BOŞ bırakılır — grafikte çizgi de orada kesilir."),
        (f"Değişken faizli sızmasına karşı {_sayi(ev.get('degisken_kupon_atilan', 0))} "
         "kupon strip'i ödeme tutarı sabit olmadığı için eğriden çıkarıldı; "
         "sukuk (kira sertifikası) ve hazine bonoları zaten evren dışıdır."),
    ]
    _duzen(fig, "DİBS spot (sıfır kuponlu) verim eğrisi", alt, 2)
    return fig


# ===========================================================================
# ŞEKİL 02 — Eğrinin zaman içindeki hareketi
# ===========================================================================
def sekil_02(M, o, damga):
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.075,
        subplot_titles=(
            f"a) Sabit vadeli düğümler ({_yil(TAM_BAS)}–bugün)",
            "b) Eğrinin bütünü: düğüm × tarih ısı haritası (haftalık, %)",
            "c) Ana bileşenler: seviye, eğim, bükülme (puan cinsinden skor)"))
    t = _pencere(M, TAM_BAS)
    for kol, ad, renk in (("n3a", "3 ay", GOLD), ("n1y", "1 yıl", TEAL),
                          ("n2y", "2 yıl", CLARET), ("n5y", "5 yıl", LACI),
                          ("n9y", "9 yıl", MOR)):
        _iz(fig, t.index, t[kol], ad, renk, 1, kalin=1.4)
    _son_isaret(fig, t["n2y"], 1, CLARET)
    _tarih_ekseni(fig, t.index, 1)

    # (b) ısı haritası — haftalık örnekleme (günlük 3.500 sütun dosyayı şişirir)
    h = t[[metrik.DUGUM_AD[d] for d in metrik.DUGUM]].resample("W-FRI").last()
    fig.add_trace(go.Heatmap(
        z=h.to_numpy().T, x=h.index,
        y=[f"{d:g} yıl" if d >= 1 else f"{int(d * 12)} ay" for d in metrik.DUGUM],
        colorscale=ISI, colorbar=dict(title="%", len=0.28, y=0.5, thickness=12,
                                      outlinewidth=0),
        hovertemplate="%{y} · %{x|%d.%m.%Y}: %{z:.2f}%<extra></extra>"),
        row=2, col=1)
    _tarih_ekseni(fig, h.index, 2)

    # (c) ana bileşenler
    if {"pc1", "pc2", "pc3"} <= set(M.columns):
        p = _pencere(M, TAM_BAS)
        for kol, ad, renk in (("pc1", "PC1 — seviye", CLARET),
                              ("pc2", "PC2 — eğim", TEAL),
                              ("pc3", "PC3 — bükülme", GOLD)):
            _iz(fig, p.index, p[kol], ad, renk, 3, kalin=1.4)
        fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=3, col=1)
        _tarih_ekseni(fig, p.index, 3)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="vade", row=2, col=1)
    fig.update_yaxes(title_text="puan", row=3, col=1)

    pca = o.get("pca") or {}
    pay = pca.get("aciklanan_pay") or [None, None, None]
    kap = o["kapsama"]
    alt = [
        f"Veri: TCMB EVDS3 · iş günü · Çıpa: {damga}. Düğümler her gün o günün "
        "sıfır kuponlu noktalarından yeniden kurulur; sabit bir kıymete "
        "bağlanmaz (kıymet vadesi geldikçe eğri kendini yeniler).",
        (f"9 yıllık düğüm {kap['dugum_dolu']['n9y']} günde kurulabildi "
         f"({kap['gun_sayisi']} günün "
         f"%{kap['dugum_dolu']['n9y'] / kap['gun_sayisi'] * 100:.0f}'i); uzun uç "
         "her dönem yayımda değildi. Boş günlerde çizgi kesilir, uydurulmaz."),
        ("Ana bileşenler düğüm panelinin ("
         + ", ".join(_dugum_etiket(k) for k in (pca.get("dugum") or []))
         + ") ortalamadan sapmalarına uygulanır; 9 yıllık düğüm HER GÜN dolu "
         "olmadığı için PCA'ya alınmadı (alınsaydı skor serisi parçalanırdı). "
         "Açıklanan pay: "
         + " · ".join(f"PC{i + 1} %{p * 100:.1f}" for i, p in enumerate(pay) if p)
         + f" (toplam %{(pca.get('toplam_pay_3') or 0) * 100:.1f})."),
        ("İşaret konvansiyonu sabitlenmiştir: PC1 yukarı = eğrinin TAMAMI "
         "yükseliyor, PC2 yukarı = eğri DİKLEŞİYOR (uzun uç kısa uca göre "
         "artıyor), PC3 yukarı = ORTA vade uçlara göre yükseliyor. Aksi hâlde "
         "işaret koşumdan koşuma dönerdi."),
        ("Isı haritasında yatay bir renk şeridinin bütün olarak koyulaşması "
         "SEVİYE hareketidir; şeridin üstü ile altının ters yönde değişmesi "
         "EĞİM hareketidir. 2018 ve 2023 sonrası bantlar bu iki hareketin "
         "birlikte göründüğü dönemlerdir."),
    ]
    _duzen(fig, "Eğri zaman içinde nasıl hareket ediyor", alt, 3, ek_yukseklik=40)
    return fig


# ===========================================================================
# ŞEKİL 03 — Eğim ve bükülme
# ===========================================================================
def sekil_03(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            "a) Eğri eğimi: 2 yıl − 9 yıl ve 2 yıl − 5 yıl (puan; sıfırın "
            "altı = TERS eğri)",
            "b) Bükülme (kelebek): 2×2 yıl − 1 yıl − 5 yıl (puan; pozitif = "
            "orta vade uçlara göre yüksek)"))
    t = _pencere(M, TAM_BAS)
    _iz(fig, t.index, t["egim_2y9y"], "2 yıl − 9 yıl (10 yıl ucu YOK, vekil)",
        CLARET, 1, kalin=1.7)
    _iz(fig, t.index, t["egim_2y5y"], "2 yıl − 5 yıl", TEAL, 1, kalin=1.4)
    _iz(fig, t.index, t["egim_2y3a"], "2 yıl − 3 ay (kısa uç eğimi)", GOLD, 1,
        kalin=1.1, kes="dot")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)
    # TERS EĞRİ DÖNEMLERİ — taralı arka plan.
    # SIRA ÖNEMLİ: `add_vrect` varsayılan olarak `exclude_empty_subplots=True`
    # ile çalışır, yani HENÜZ İZ EKLENMEMİŞ bir panele hiçbir şey koymaz ve
    # HATA DA VERMEZ. Gölgeler izlerden ÖNCE eklendiğinde 55 dikdörtgenin
    # tamamı sessizce düşüyordu (ölçüldü: layout.shapes boş kalıyor).
    ters = (t["egim_2y9y"] < 0).fillna(False)
    bas = None
    for i, (g, v) in enumerate(ters.items()):
        if v and bas is None:
            bas = g
        if (not v or i == len(ters) - 1) and bas is not None:
            fig.add_vrect(x0=bas, x1=g, fillcolor=TARAMA, line_width=0,
                          layer="below", row=1, col=1)
            bas = None
    _son_isaret(fig, t["egim_2y9y"], 1, CLARET, birim=" puan")
    _tarih_ekseni(fig, t.index, 1)

    _iz(fig, t.index, t["kelebek_1_2_5"], "2×2y − 1y − 5y", MOR, 2, kalin=1.6)
    _iz(fig, t.index, t["kelebek_2_5_9"], "2×5y − 2y − 9y (uzun kelebek)",
        LACI, 2, kalin=1.2, kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)
    _son_isaret(fig, t["kelebek_1_2_5"], 2, MOR, birim=" puan")
    _tarih_ekseni(fig, t.index, 2)

    # Pay, eğimin ÖLÇÜLEBİLDİĞİ günlere göre hesaplanır (9 yıllık düğüm her
    # gün yok). Bütün pencereye bölmek oranı sessizce küçültürdü ve ozet.json
    # ile sayfa metni birbirini tutmazdı.
    olculen = int(t["egim_2y9y"].notna().sum())
    ters_gun = int(ters.sum())
    ters_son = t.index[ters][-1] if ters.any() else None
    alt = [
        f"Veri: TCMB EVDS3 · iş günü · Çıpa: {damga}. Eğim = uzun düğüm − kısa "
        "düğüm; iki nokta da AYNI GÜNÜN eğrisinden okunur.",
        ("EVDS'te 10 yıllık bir düğüm ÇOĞU GÜN YOKTUR: aktif sıfır kuponlu "
         "evrenin en uzun noktası ~9 yıl. Uluslararası kıyaslarda '2y−10y' "
         "denen ölçü burada 2y−9y ile VEKİL edilmiştir; vade farkı bir yıl "
         "kısadır ve eğim mutlak değerce biraz küçük çıkar."),
        (f"Taralı alanlar ters eğri dönemleridir: eğimin ölçülebildiği "
         f"{olculen} iş gününün {ters_gun} tanesi "
         f"(%{ters_gun / max(olculen, 1) * 100:.0f})"
         + (f", en son {ters_son:%d.%m.%Y}." if ters_son is not None else ".")),
        ("Kelebek, eğrinin ORTASININ uçlara göre konumudur: 2×2y − 1y − 5y "
         "pozitifse orta vade iki uca çizilen doğrunun ÜSTÜNDEDİR. Politika "
         "faizi beklentisinin tepe noktası orta vadeye oturduğunda bu ölçü "
         "yükselir."),
    ]
    _duzen(fig, "Eğri eğimi ve bükülmesi", alt, 2, y_baslik="puan")
    return fig


# ===========================================================================
# ŞEKİL 04 — Taşıma (carry): eğri ile fonlama maliyeti arasındaki makas
# ===========================================================================
def sekil_04(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            f"a) 2 yıllık spot getiri ile fonlama faizleri — fonlama faizleri "
            f"BİLEŞİĞE ÇEVRİLMİŞ ({_yil(TAM_BAS)}–bugün)",
            "b) Taşıma: 2 yıllık spot eksi BİLEŞİK fonlama faizi (puan)"))
    t = _pencere(M, TAM_BAS)
    _iz(fig, t.index, t["n2y"], "2 yıllık spot getiri (bileşik)", CLARET, 1,
        kalin=1.8)
    _iz(fig, t.index, t["aofm_bilesik"],
        "AOFM — bileşiğe çevrilmiş", TEAL, 1, kalin=1.3)
    _iz(fig, t.index, t["politika_bilesik_gercek"],
        "Politika faizi (1 hafta repo) — bileşiğe çevrilmiş", INK, 1,
        kalin=1.2, kes="dot")
    # TLREF için MOR: TEAL (#1d5c5c) ile LACİ (#2f4b7c) küçük lejant
    # kutucuğunda birbirinden ayırt edilemiyordu (ölçüldü) — AOFM ile TLREF
    # bu figürün ana karşıtlığı olduğu için iki rengin ayrışması şart.
    _iz(fig, t.index, t["tlref_bilesik"], "TLREF — bileşiğe çevrilmiş", MOR, 1,
        kalin=1.1)
    # HAM (BASİT) yayımlanan değer de gizlenmez: okur TCMB/BİST ekranında
    # gördüğü sayıyı grafikte bulamazsa grafiğe güvenmez.
    _iz(fig, t.index, t["tlref"], "TLREF — ham (BASİT, yayımlandığı hâliyle)",
        GRI, 1, kalin=0.9, kes="dash")
    _son_isaret(fig, t["n2y"], 1, CLARET)
    _tarih_ekseni(fig, t.index, 1)

    _iz(fig, t.index, t["carry_2y_tlref"], "2 yıl − TLREF (bileşik)", MOR, 2,
        kalin=1.5, dolgu="tozeroy", dolgu_renk=TARAMA2)
    _iz(fig, t.index, t["carry_2y_aofm"], "2 yıl − AOFM (bileşik)", TEAL, 2,
        kalin=1.2)
    _iz(fig, t.index, t["carry_3a_tlref"], "3 ay − TLREF (kısa uç, bileşik)",
        GOLD, 2, kalin=1.0, kes="dot")
    # KONVANSİYON DERSİ: aynı taşıma BASİT farkla nereye düşerdi?
    _iz(fig, t.index, t["carry_2y_tlref_basit"],
        "2 yıl − TLREF, BASİT farkla (yanlış konvansiyon)", GRI, 2, kalin=0.9,
        kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)
    _son_isaret(fig, t["carry_2y_tlref"], 2, MOR, birim=" puan")
    _tarih_ekseni(fig, t.index, 2)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)

    _c = t["carry_2y_tlref"].dropna()
    neg = int((_c < 0).sum())
    alt = [
        f"Veri: TCMB EVDS3 · iş günü · Çıpa: {damga}. Taşıma = 2 yıllık spot "
        "getiri eksi gecelik fonlama faizi; tahvili gecelikle fonlayan bir "
        "pozisyonun eğri SABİT KALIRSA kazanacağı taşımadır.",
        ("KONVANSİYON UYARISI: TLREF, AOFM ve 1 hafta repo faizi BASİT yıllık "
         "yayımlanır; strip getirisi ise YILLIK BİLEŞİKTİR. Karşılaştırma için "
         "fonlama faizleri bileşiğe çevrilmiştir — gecelik için "
         "(1+r/365)^365−1, 1 hafta için (1+r·7/365)^(365/7)−1. Ham (basit) "
         "TLREF ve basit farkla hesaplanan taşıma da gri kesikli çizgilerle "
         "gösteriliyor: iki konvansiyon arasındaki fark bugün "
         f"{_sayi(o['anlik'].get('konvansiyon_farki_tlref'), 2)} puandır ve "
         "taşımanın İŞARETİNİ değiştirecek büyüklüktedir."),
        ("Politika faizi kotasyonu (TP.PY.P02.1H) EVDS'te 14.09.2018'de "
         "başlıyor; öncesinde bu vadede kotasyon yayımlanmıyor ve haftalık "
         "repo İHALEYLE fonlanıyordu. O dönemde fiilî politika faizi AOFM'dir "
         "— grafikte kesintisiz olan çizgi odur."),
        ("TLREF 28.12.2018'de başlar. Üç faiz aynı günde farklı sayılar verir: "
         "AOFM TCMB'nin fiilen ödettiği ortalama, TLREF piyasanın teminatlı "
         "gecelik faizi, politika faizi ise kotasyondur."),
        (f"TLREF'in başladığı günden bu yana {len(_c)} iş gününün {neg}'inde "
         f"taşıma NEGATİFTİ (%{neg / max(len(_c), 1) * 100:.0f}); bu "
         "dönemlerde uzun pozisyon taşımak para kaybettirir ve pozisyon ancak "
         "faiz İNMESİ beklentisiyle tutulur."),
    ]
    _duzen(fig, "Taşıma: eğri ile fonlama maliyeti arasındaki makas", alt, 2)
    return fig


# ===========================================================================
# ŞEKİL 05 — Reel faiz: Fisher ileri ve geriye dönük
# ===========================================================================
def sekil_05(M, o, damga, anket_gun):
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.075,
        subplot_titles=(
            "a) 1 yıllık nominal spot getiri, PKA 12 ay enflasyon beklentisi "
            "ve gerçekleşen yıllık TÜFE",
            "b) FISHER reel faiz: ileri bakışlı ve geriye dönük (taralı alan "
            "= beklenti–gerçekleşme makası)",
            "c) Yöntem farkı: basit çıkarma (i − π) eksi Fisher (puan)"))
    t = _pencere(M, TAM_BAS)
    _iz(fig, t.index, t["n1y"], "1 yıllık nominal spot", CLARET, 1, kalin=1.7)
    _iz(fig, t.index, t["pka_12a"], "PKA 12 ay TÜFE beklentisi (basamak)",
        TEAL, 1, kalin=1.4)
    _iz(fig, t.index, t["tufe_yillik"], "Gerçekleşen yıllık TÜFE", GOLD, 1,
        kalin=1.2, kes="dash")
    _son_isaret(fig, t["n1y"], 1, CLARET)
    _tarih_ekseni(fig, t.index, 1)

    # (b) iki reel faiz ve aralarındaki taralı fark
    ort = t[["reel_ileri", "reel_geriye"]].dropna()
    if len(ort):
        fig.add_trace(go.Scatter(
            x=ort.index, y=ort["reel_geriye"], mode="lines", name="_alt",
            line=dict(width=0), showlegend=False, hoverinfo="skip"), row=2, col=1)
        fig.add_trace(go.Scatter(
            x=ort.index, y=ort["reel_ileri"], mode="lines",
            name="Beklenti–gerçekleşme makası", line=dict(width=0),
            fill="tonexty", fillcolor=TARAMA, showlegend=True), row=2, col=1)
    _iz(fig, t.index, t["reel_ileri"], "Fisher ileri reel faiz (PKA beklentisi)",
        CLARET, 2, kalin=1.7)
    _iz(fig, t.index, t["reel_geriye"], "Fisher geriye dönük reel faiz "
        "(gerçekleşen TÜFE)", TEAL, 2, kalin=1.5)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)
    _son_isaret(fig, t["reel_ileri"], 2, CLARET)
    _tarih_ekseni(fig, t.index, 2)

    _iz(fig, t.index, t["fisher_basit_fark"],
        "Basit çıkarma − Fisher", MOR, 3, kalin=1.4, dolgu="tozeroy",
        dolgu_renk="rgba(102,81,145,0.10)")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=3, col=1)
    _son_isaret(fig, t["fisher_basit_fark"], 3, MOR, birim=" puan")
    _tarih_ekseni(fig, t.index, 3)
    # Anket yayım günleri: reel faizdeki BASAMAK sıçramaları buradan gelir.
    # YALNIZ SON 12 AY çizilir — 13 yıllık eksende yüzlerce dikey çizgi
    # birbirine girip taralı bir blok gibi görünüyordu (ölçüldü).
    for g in anket_gun[-12:]:
        fig.add_vline(x=g, line=dict(color=GRI, width=0.6, dash="dot"),
                      opacity=0.5, row=2, col=1)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    fig.update_yaxes(title_text="puan", row=3, col=1)

    a = o["anlik"]
    e = o["esik"]
    alt = [
        f"Veri: TCMB EVDS3 · Çıpa: {damga}. Reel faiz FISHER kimliğiyle "
        "hesaplanır: r = (1+i)/(1+π) − 1. Bu depoda BAĞLAYICI karardır; basit "
        "çıkarma (i − π) yalnız yöntem farkını göstermek için hesaplanır.",
        (f"Çıpa gününde: nominal %{_sayi(a.get('n1y'), 2)}, beklenti "
         f"%{_sayi(a.get('pka_12a'), 2)} → Fisher ileri reel "
         f"%{_sayi(a.get('reel_ileri'), 2)}; basit çıkarma "
         f"%{_sayi(a.get('reel_ileri_basit'), 2)} derdi. Fark "
         f"{_sayi(a.get('fisher_basit_fark'), 2)} puan — enflasyon yükseldikçe "
         "iki yöntem arasındaki makas açılır (panel c)."),
        ("FREKANS UYUMSUZLUĞU: eğri GÜNLÜK, beklenti AYLIKTIR. PKA ayın "
         f"{e['pka_yayim_gun']}'sinde, TÜFE ertesi ayın "
         f"{e['tufe_yayim_gecikme']}'inde yayımlanmış sayılarak günlüğe "
         "basamak olarak yayılır — ay başından yaymak o gün piyasanın "
         "bilmediği bir sayıyı kullanmak, yani GELECEĞE BAKMAK olurdu."),
        ("Panel (b)'deki dikey noktalı çizgiler SON 12 anket yayım günüdür: "
         "reel faizdeki keskin basamaklar piyasa hareketi değil, beklenti "
         "serisinin yenilenmesidir."),
        ("İki reel faiz aynı nominal faizi FARKLI paydayla böler. Geriye dönük "
         "ölçü geçmiş enflasyonu, ileri ölçü beklenen enflasyonu kullanır; "
         "dezenflasyonda ileri ölçü YÜKSEK, enflasyon hızlanırken DÜŞÜK "
         "görünür. Taralı alan bu makastır."),
    ]
    _duzen(fig, "Reel faiz: Fisher ileri ve geriye dönük", alt, 3,
           ek_yukseklik=30)
    return fig


# ===========================================================================
# ŞEKİL 06 — TÜFEX reel eğrisi ve başabaş enflasyon
# ===========================================================================
def sekil_06(M, KR, KE, o, damga):
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.075,
        subplot_titles=(
            "a) TÜFEX (TÜFE'ye endeksli DİBS) reel spot eğrisi — noktalar tek "
            "tek kıymetler",
            "b) Vadeye göre başabaş enflasyon ve PKA beklentileri",
            "c) 1 · 2 · 5 yıllık başabaş enflasyonun zaman içindeki seyri"))
    if KR is None or KR.empty:
        return None
    r = KR.sort_values("vade_yil")
    t = r["vade_yil"].to_numpy()
    y = r["reel_getiri"].to_numpy()
    gx, gy = _egri_ciz(t, y)
    fig.add_trace(go.Scatter(x=gx, y=gy, mode="lines", name="Reel eğri (uydurma)",
                             line=dict(color=TEAL, width=2.0)), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=t, y=y, mode="markers", name="TÜFEX anapara strip'i",
        marker=dict(color=TEAL, size=7, symbol="circle-open", line=dict(width=1.6)),
        hovertemplate="%{x:.2f} yıl: %{y:.2f}%<extra></extra>"), row=1, col=1)
    fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=1, col=1)

    # (b) vadeye göre başabaş: her TÜFEX noktasının vadesinde nominal eğri okunur
    bugun = KE[KE["kesit"] == "bugun"].sort_values("vade_yil")
    nt = bugun["vade_yil"].to_numpy()
    ny = bugun["getiri"].to_numpy() / 100.0
    tekil = np.unique(np.round(nt, 6))
    ny_tekil = np.array([np.median(ny[np.isclose(nt, v)]) for v in tekil])
    nom = metrik._ara_deger(tekil, ny_tekil, t)
    be = ((1 + nom) / (1 + y / 100.0) - 1) * 100.0
    fig.add_trace(go.Scatter(
        x=t, y=be, mode="lines+markers", name="Başabaş enflasyon (nominal ÷ reel)",
        line=dict(color=CLARET, width=2.0), marker=dict(size=6)), row=2, col=1)
    a = o["anlik"]
    # ANKET BEKLENTİSİ İKİ BİÇİMDE ÇİZİLİR.
    # (1) ORTALAMAYA ÇEVRİLMİŞ (dolu baklava) — başabaşla AYNI ufku ölçer.
    #     Başabaş vadeye kadarki yıllık ORTALAMA enflasyondur; PKA serileri
    #     ise "X ay SONRASININ yıllık" NOKTA oranlarıdır. Nokta beklentiyi
    #     başabaşın yanına koymak risk primini sistematik olarak şişirir.
    # (2) HAM NOKTA beklenti (içi boş gri baklava) — TCMB'nin yayımladığı
    #     sayı gizlenmez, ama farklı bir şey ölçtüğü işaretle ayrılır.
    ort_ad = {1.0: "pka_ort_1y", 2.0: "pka_ort_2y", 5.0: "pka_ort_5y",
              7.0: "pka_ort_7y"}
    for ad, vade, renk in (("1 yıl", 1.0, GOLD), ("2 yıl", 2.0, LACI),
                           ("5 yıl", 5.0, MOR), ("7 yıl", 7.0, TEAL)):
        deger = a.get(ort_ad[vade])
        if deger is None:
            continue
        fig.add_trace(go.Scatter(
            x=[vade], y=[deger], mode="markers+text",
            name=f"Anket — {ad} ORTALAMASINA çevrilmiş",
            marker=dict(color=renk, size=11, symbol="diamond"),
            text=[f" {_sayi(deger, 1)}%"], textposition="middle right",
            textfont=dict(size=10, color=renk)), row=2, col=1)
    for i, (ad, vade, deger) in enumerate((
            ("PKA 12 ay (ham nokta)", 1.0, a.get("pka_12a")),
            ("PKA 24 ay (ham nokta)", 2.0, a.get("pka_24a")),
            ("PKA 5 yıl (ham nokta)", 5.0, a.get("pka_5y")))):
        if deger is None:
            continue
        fig.add_trace(go.Scatter(
            x=[vade], y=[deger], mode="markers",
            name="Anket — HAM nokta beklenti ('X ay sonrasının yıllık')",
            showlegend=i == 0,
            marker=dict(color=GRI, size=10, symbol="diamond-open",
                        line=dict(width=1.5)),
            hovertemplate=f"{ad}: {_sayi(deger, 2)}%<extra></extra>"),
            row=2, col=1)

    # (c) başabaş zaman serisi
    p = _pencere(M, "2021-01-01")
    for kol, ad, renk in (("be_1y", "1 yıllık başabaş", GOLD),
                          ("be_2y", "2 yıllık başabaş", CLARET),
                          ("be_5y", "5 yıllık başabaş", TEAL)):
        if kol in p.columns:
            _iz(fig, p.index, p[kol], ad, renk, 3, kalin=1.4)
    _iz(fig, p.index, p["pka_12a"], "PKA 12 ay beklentisi (anket, zaman serisi)",
        GRI, 3, kalin=1.2, kes="dot")
    _son_isaret(fig, p["be_2y"], 3, CLARET)
    _tarih_ekseni(fig, p.index, 3)
    fig.update_xaxes(title_text="vade (yıl)", row=1, col=1)
    fig.update_xaxes(title_text="vade (yıl)", row=2, col=1)
    for s in (1, 2, 3):
        fig.update_yaxes(title_text="%", row=s, col=1)

    kap = o["kapsama"]
    zin = o.get("tufe_zinciri") or {}
    alt = [
        f"Veri: TCMB EVDS3 · Çıpa: {damga}. Reel getiri = "
        "(100 × RefEndeks(t)/RefEndeks(ihraç) ÷ fiyat)^(365/gün) − 1. TÜFEX'in "
        "yayımlanan 'Değer'i ENDEKSLENMİŞ TL fiyatıdır, reel fiyat değildir.",
        ("Referans endeks EVDS'te YOK; Hazine'nin tanımı yeniden kuruluyor: "
         "RefEndeks(t) = TÜFE(m−3) + (gün−1)/D × [TÜFE(m−2) − TÜFE(m−3)]. Taban "
         "2003=100 zinciridir; TÜİK 2025 baz değişikliği sonrası zincir "
         f"katsayısı örtüşme ayından ({zin.get('ortusme_ay', '—')}) her koşuda "
         f"okunur: {_sayi(zin.get('kat'), 4)} — sabit yazılmaz."),
        ("BAŞABAŞ ≠ BEKLENTİ. Panel (b)'de DOLU baklavalar anketin söylediği, "
         "kırmızı çizgi piyasanın fiyatladığı enflasyondur. Aradaki fark "
         "enflasyon risk primi, likidite primi ve TÜFE ölçümüne güvensizliğin "
         f"karışımıdır: 1 yılda {_sayi(a.get('prim_1y'), 1)} puan, 5 yılda "
         f"{_sayi(a.get('prim_5y'), 1)} puan."),
        ("UFUK DÜZELTMESİ: PKA serileri 'X AY SONRASININ yıllık TÜFE' "
         "oranlarıdır — 24 ay serisi İKİNCİ YILIN tek yıllık oranıdır, iki "
         "yıllık ortalama DEĞİL. Başabaş ise tanımı gereği vadeye kadarki "
         "yıllık ORTALAMA'dır. Dolu baklavalar bu yüzden 12 ay, 24 ay ve 5 "
         "yıl çıpalarından kurulan bir yıllık enflasyon patikasının "
         "vadeye kadarki GEOMETRİK ORTALAMASIDIR; içi boş gri baklavalar ham "
         "nokta beklentilerdir. Ara yıllar (3, 4) log-doğrusal ara değerle "
         "doldurulur ve son çıpanın ötesi (6, 7) sabit tutulur — patika bir "
         "VARSAYIMDIR, anket o yılları sormaz."),
        ("Reel eğri nominal eğri kadar sık değildir: " + str(kap.get("reel_notu", ""))),
        ("Kısa uçta kıymetler arası saçılma geniştir (Şekil 08c); tek bir "
         "'reel faiz' çizgisine indirgemek yanlış kesinlik üretir. Uzun uçta "
         "saçılma daralır."),
    ]
    _duzen(fig, "TÜFEX reel eğrisi ve başabaş enflasyon", alt, 3, ek_yukseklik=30)
    return fig


# ===========================================================================
# ŞEKİL 07 — İleri (forward) oranlar ve ima edilen faiz patikası
# ===========================================================================
def sekil_07(M, KE, o, damga):
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.12,
        subplot_titles=(
            "a) İleri oranlar: 1y1y, 2y1y ve 2y3y (bugünkü eğrinin ima ettiği "
            "gelecek faizler)",
            "b) Bugünkü eğrinin ima ettiği bir yıllık faiz patikası ile PKA "
            "politika faizi beklentileri"))
    t = _pencere(M, TAM_BAS)
    _iz(fig, t.index, t["f_1y1y"], "1y1y — bir yıl sonrasının 1 yıllık faizi",
        CLARET, 1, kalin=1.6)
    _iz(fig, t.index, t["f_2y1y"], "2y1y — iki yıl sonrasının 1 yıllık faizi",
        TEAL, 1, kalin=1.4)
    _iz(fig, t.index, t["f_2y3y"], "2y3y — iki yıl sonrasının 3 yıllık faizi",
        GOLD, 1, kalin=1.2, kes="dash")
    _iz(fig, t.index, t["n1y"], "1 yıllık spot (kıyas)", GRI, 1, kalin=1.0,
        kes="dot")
    _son_isaret(fig, t["f_1y1y"], 1, CLARET)
    _tarih_ekseni(fig, t.index, 1)

    # (b) bugünkü kesitten ima edilen bir yıllık ileri faiz patikası
    bugun = KE[KE["kesit"] == "bugun"].sort_values("vade_yil")
    nt = bugun["vade_yil"].to_numpy()
    ny = bugun["getiri"].to_numpy() / 100.0
    tekil = np.unique(np.round(nt, 6))
    ny_tekil = np.array([np.median(ny[np.isclose(nt, v)]) for v in tekil])
    yillar = np.arange(1.0, 10.0)
    s = metrik._ara_deger(tekil, ny_tekil, yillar)
    patika_x, patika_y = [], []
    for k in range(len(yillar)):
        if not np.isfinite(s[k]):
            continue
        if k == 0:
            f = s[0]
        else:
            if not np.isfinite(s[k - 1]):
                continue
            f = ((1 + s[k]) ** yillar[k] / (1 + s[k - 1]) ** yillar[k - 1]) - 1
        patika_x.append(k)
        patika_y.append(f * 100.0)
    fig.add_trace(go.Scatter(
        x=patika_x, y=patika_y, mode="lines+markers",
        name="Eğrinin ima ettiği 1 yıllık faiz (yıl yıl)",
        line=dict(color=CLARET, width=2.0, shape="hv"),
        marker=dict(size=7)), row=2, col=1)
    a = o["anlik"]
    # KONVANSİYON: ima edilen patika BİLEŞİKTİR (spot getirilerden türer).
    # Politika faizi ve PKA politika faizi beklentileri BASİT yayımlanır;
    # yan yana koymadan önce bileşiğe çevrilir. Çevrilmezse aradaki fark
    # "vade primi" diye okunur ama bir kısmı yalnız konvansiyon farkıdır —
    # bugünkü sayılarda prim İŞARET DEĞİŞTİRİYOR.
    def _hafta_bilesik(v):
        if v is None:
            return None
        return ((1 + v / 100.0 * metrik.POLITIKA_VADE_GUN / metrik.GUN_SAYISI)
                ** (metrik.GUN_SAYISI / metrik.POLITIKA_VADE_GUN) - 1) * 100.0

    for ad, x, deger, renk in (
            ("Bugünkü politika faizi (bileşiğe çevrilmiş)", 0,
             _hafta_bilesik(a.get("politika")), INK),
            ("PKA 12 ay sonrası politika faizi (bileşiğe çevrilmiş)", 1,
             _hafta_bilesik(a.get("pka_faiz_12a")), TEAL),
            ("PKA 24 ay sonrası politika faizi (bileşiğe çevrilmiş)", 2,
             _hafta_bilesik(a.get("pka_faiz_24a")), GOLD)):
        if deger is None:
            continue
        fig.add_trace(go.Scatter(
            x=[x], y=[deger], mode="markers+text", name=ad,
            marker=dict(color=renk, size=11, symbol="diamond"),
            text=[f" {_sayi(deger, 1)}%"], textposition="middle right",
            textfont=dict(size=10, color=renk)), row=2, col=1)
    # HAM (BASİT) değerler de gösterilir: okurun TCMB ekranında gördüğü sayı.
    for ad, x, deger in (
            ("Politika faizi / PKA beklentisi — ham (BASİT)", 0, a.get("politika")),
            (None, 1, a.get("pka_faiz_12a")),
            (None, 2, a.get("pka_faiz_24a"))):
        if deger is None:
            continue
        fig.add_trace(go.Scatter(
            x=[x], y=[deger], mode="markers", name=ad or "",
            showlegend=ad is not None,
            marker=dict(color=GRI, size=9, symbol="diamond-open",
                        line=dict(width=1.4)),
            hovertemplate=f"ham (basit): {_sayi(deger, 2)}%<extra></extra>"),
            row=2, col=1)
    fig.update_xaxes(title_text="bugünden itibaren geçen yıl", row=2, col=1,
                     tickmode="array", tickvals=list(range(0, 9)),
                     ticktext=[f"{k}–{k + 1}" for k in range(0, 9)])
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)

    alt = [
        f"Veri: TCMB EVDS3 · iş günü · Çıpa: {damga}. İleri oran spot "
        "getirilerden türetilir: f(t₁→t₂) = [(1+s₂)^t₂ / (1+s₁)^t₁]^(1/(t₂−t₁)) − 1. "
        "Yeni bir veri değil, eğrinin kendi içindeki bilginin başka yazılışıdır.",
        (f"Çıpa gününde 1y1y %{_sayi(a.get('f_1y1y'), 2)}, 2y1y "
         f"%{_sayi(a.get('f_2y1y'), 2)}; 1 yıllık spot "
         f"%{_sayi(a.get('n1y'), 2)}. İleri oran spotun ALTINDAYSA eğri kısa "
         "vadede faiz İNİŞİ fiyatlıyor demektir."),
        ("Panel (b) İMA EDİLEN patikadır, TAHMİN DEĞİLDİR: içinde vade primi "
         "vardır. Vade primi pozitifse ima edilen patika gerçek beklenen "
         "politika faizinin ÜSTÜNDE kalır — baklava işaretleriyle (PKA anketi) "
         "arasındaki fark bu primin kaba bir ölçüsüdür."),
        ("KONVANSİYON: ima edilen patika spot getirilerden türediği için "
         "BİLEŞİKTİR; politika faizi ve PKA politika faizi beklentileri ise "
         "BASİT yayımlanır. Dolu baklavalar bileşiğe çevrilmiş, içi boş gri "
         "baklavalar ham (basit) değerlerdir. Çevrilmeden kurulan bir "
         "karşılaştırmada 'vade primi' diye okunan farkın önemli bir kısmı "
         "yalnız konvansiyon farkıdır — bugünkü sayılarda işareti bile "
         "değiştiriyor."),
        ("Ayrıca patika DİBS getirisinden türer, politika faizinden değil: "
         "tahvil kredi riski taşımasa da likidite ve vade riski taşır; "
         "iki büyüklüğü birebir eşitlemek yanlış olur."),
    ]
    _duzen(fig, "İleri oranlar ve eğrinin ima ettiği faiz patikası", alt, 2)
    return fig


# ===========================================================================
# ŞEKİL 08 — Tanı paneli: veri sağlığı
# ===========================================================================
def sekil_08(M, RD, KR, o, damga):
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.075,
        subplot_titles=(
            "a) Günlük kullanılabilir sıfır kuponlu nokta sayısı ve vade "
            "kapsaması",
            "b) Kimlik denetimi: aynı itfa gününe düşen bağımsız strip'ler "
            "arasındaki getiri farkı (puan)",
            "c) TÜFEX kıymetleri arası reel getiri saçılması (son bir yıl)"))
    t = _pencere(M, TAM_BAS)
    for kol, ad, renk in (("nokta_kisa", "≤ 1 yıl", GOLD),
                          ("nokta_orta", "1–5 yıl", TEAL),
                          ("nokta_uzun", "> 5 yıl", CLARET)):
        fig.add_trace(go.Scatter(
            x=t.index, y=t[kol], name=ad, mode="lines", stackgroup="kapsama",
            line=dict(width=0.6, color=renk), fillcolor=renk, opacity=0.75),
            row=1, col=1)
    # Toplam ayrı çizgi olarak çizilmez: yığının tepesi ZATEN toplamdır,
    # üstüne bir çizgi daha koymak aynı sayıyı iki kez göstermek olurdu.
    _son_isaret(fig, t["nokta"], 1, INK, ondalik=0, birim="")
    _tarih_ekseni(fig, t.index, 1)

    # Günlük sapma serisi çok gürültülü (log eksende dolu bir bant gibi
    # görünüyordu). Ham seri soluk arka planda kalır, üstüne 21 günlük
    # yuvarlanan medyan çizilir — eğilim okunabilsin, aykırı gün kaybolmasın.
    _iz(fig, t.index, t["sapma_maks"], "En büyük sapma (ham, günlük)", CLARET, 2,
        kalin=0.6, opacity=0.30, goster=False, grup="maks")
    _iz(fig, t.index, t["sapma_maks"].rolling(21, min_periods=5).median(),
        "En büyük sapma (21 gün yuvarlanan medyan)", CLARET, 2, kalin=1.3,
        grup="maks")
    _iz(fig, t.index, t["sapma_medyan"], "Medyan sapma (ham, günlük)", TEAL, 2,
        kalin=0.6, opacity=0.30, goster=False, grup="medyan")
    _iz(fig, t.index, t["sapma_medyan"].rolling(21, min_periods=5).median(),
        "Medyan sapma (21 gün yuvarlanan medyan)", TEAL, 2, kalin=1.5,
        grup="medyan")
    kim = o["kimlik"]
    fig.add_hline(y=kim["esik_medyan"], line=dict(color=GOLD, width=1.0, dash="dash"),
                  row=2, col=1)
    fig.add_annotation(x=t.index[int(len(t) * 0.06)], y=kim["esik_medyan"],
                       text=("MEDYAN sapma uyarı eşiği "
                             f"{_sayi(kim['esik_medyan'], 2)} puan — kırmızı "
                             "seri EN BÜYÜK sapmadır, bu eşiğe tabi değildir"),
                       showarrow=False, yshift=10, font=dict(size=10, color=GOLD),
                       row=2, col=1)
    _son_isaret(fig, t["sapma_medyan"], 2, TEAL, ondalik=3, birim=" puan")
    _tarih_ekseni(fig, t.index, 2)
    fig.update_yaxes(type="log", row=2, col=1)

    if RD is not None and not RD.empty:
        fig.add_trace(go.Scatter(
            x=RD["vade_yil"], y=RD["reel_getiri"], mode="markers",
            name="Son bir yılın TÜFEX gözlemleri",
            marker=dict(color=GRI, size=3, opacity=0.30),
            hovertemplate="%{x:.2f} yıl: %{y:.2f}%<extra></extra>"), row=3, col=1)
    if KR is not None and not KR.empty:
        fig.add_trace(go.Scatter(
            x=KR["vade_yil"], y=KR["reel_getiri"], mode="markers",
            name="Çıpa günü", marker=dict(color=CLARET, size=8,
                                          symbol="circle-open",
                                          line=dict(width=1.8))), row=3, col=1)
    fig.update_xaxes(title_text="vade (yıl)", row=3, col=1)
    fig.update_yaxes(title_text="adet", row=1, col=1)
    fig.update_yaxes(title_text="puan (log)", row=2, col=1)
    fig.update_yaxes(title_text="reel %", row=3, col=1)

    kap = o["kapsama"]
    ytm = o.get("ytm_sinamasi") or {}
    ev = o.get("evren") or {}
    alt = [
        f"Veri: TCMB EVDS3 · iş günü · Çıpa: {damga}. Bu panel HATTIN KENDİ "
        "SAĞLIĞINI ölçer: eğri kaç noktadan kuruluyor, noktalar birbiriyle "
        "tutuyor mu, reel taraf ne kadar dağınık.",
        (f"Çıpa gününde {kap['nokta_son']} nokta (tarihçe medyanı "
         f"{kap['nokta_medyan']}). Vadesi dolan kıymet güncel veri grubundan "
         "düştüğü için tarihçe ARŞİV grubuyla birleştirilmiştir; birleştirilmese "
         "2013 yılı için elde beş nokta kalırdı."),
        (f"Kimlik denetimi (panel b): tarihçe boyunca medyan sapmanın medyanı "
         f"{_sayi(kim['medyan_medyan'], 4)} puan, en büyük tekil sapma "
         f"{_sayi(kim['maks_maks'], 3)} puan ({kim['maks_tarih']}). Eşik "
         f"{_sayi(kim['esik_maks'], 1)} puan aşılırsa hat DURUR: o noktada "
         "sınıflandırma bozulmuş, muhtemelen değişken faizli bir kıymet nominal "
         "eğriye sızmıştır."),
        (("İÇ TUTARLILIK ÖZDEŞLİĞİ (bağımsız doğrulama DEĞİL): tahvilin nakit "
          "akışı kendi strip'lerinden kurulup yine o strip'lerin kendi "
          "getirileriyle iskonto edildiği için model fiyatı zorunlu olarak "
          "strip fiyatlarının toplamına eşittir — TCMB'nin yayımladığı "
          f"kuponlu tahvil 'Değer'i de odur. {ytm.get('ozdeslik_n')} tahvilin "
          "hepsinde |Σ strip fiyatı − tahvil fiyatı| en çok "
          f"{ytm.get('ozdeslik_maks_tl')} TL (eşik "
          f"{ytm.get('ozdeslik_esik_tl')} TL); aşılsaydı hat DURURDU. "
          f"Kalan medyan YTM farkı {_sayi(ytm.get('medyan_fark_puan'), 4)} "
          "puan yalnız aynı vadede birden çok strip bulunduğunda alınan "
          "MEDYANDAN gelir. Bu bir BİRİM SINAMASIDIR: ödeme tanımı, etiket "
          "sınıflandırması ya da strip↔tahvil eşlemesi bozulursa buradan "
          "görünür; eğrinin dışarıdan doğrulandığı anlamına GELMEZ.") if ytm
         else "Özdeşlik birim sınaması bu koşuda yapılamadı."),
        ("Sapmanın bu kadar küçük olması kısmen GÖSTERGE FİYAT olmasındandır: "
         "işlem görmemiş kıymette TCMB model fiyatı basar, dolayısıyla noktalar "
         "tam bağımsız gözlem değildir. Denetim yine de değerlidir — bozulan "
         "şey birim/sınıflandırma olduğunda buradan görünür."),
        (f"Panel (c): TÜFEX evreni {ev.get('tufex_fiyati_gelen', '—')} anapara "
         "strip'i. Kısa uçta kıymetler arası reel getiri farkı birkaç puana "
         "çıkar (likidite + referans endeks yaklaşımının hata payı); ham "
         "dağılım bilinçli olarak korunuyor."),
    ]
    _duzen(fig, "Tanı paneli: eğri ne kadar sağlam", alt, 3, ek_yukseklik=30)
    return fig


# ===========================================================================
SEKILLER = [
    ("01_egri_bugun.html", 2),
    ("02_egri_hareketi.html", 3),
    ("03_egim_bukulme.html", 2),
    ("04_carry.html", 2),
    ("05_reel_faiz.html", 3),
    ("06_tufex_basabas.html", 3),
    ("07_forward.html", 2),
    ("08_tani_paneli.html", 3),
]


def _yukle():
    M = pd.read_csv(VERI / "metrik.csv", index_col=0, parse_dates=True)
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    KE = pd.read_csv(VERI / "kesit_egri.csv")
    yol_r = VERI / "kesit_reel.csv"
    KR = pd.read_csv(yol_r) if yol_r.exists() else None
    yol_d = VERI / "reel_dagilim.csv"
    RD = pd.read_csv(yol_d) if yol_d.exists() else None
    A = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    return M, o, KE, KR, RD, A


def kos() -> None:
    M, o, KE, KR, RD, A = _yukle()
    s_gun = pd.Timestamp(o["son_gun"])
    damga = gun_ad(s_gun)
    print(f"DİBS verim eğrisi & reel faiz — grafikler · veri {damga}")
    anket_gun = metrik.yayim_gunleri(A["pka_12a"], M.index, o["esik"]["pka_yayim_gun"])

    ciktilar = [
        (sekil_01(KE, M, o, damga), "01_egri_bugun.html"),
        (sekil_02(M, o, damga), "02_egri_hareketi.html"),
        (sekil_03(M, o, damga), "03_egim_bukulme.html"),
        (sekil_04(M, o, damga), "04_carry.html"),
        (sekil_05(M, o, damga, anket_gun), "05_reel_faiz.html"),
        (sekil_06(M, KR, KE, o, damga), "06_tufex_basabas.html"),
        (sekil_07(M, KE, o, damga), "07_forward.html"),
        (sekil_08(M, RD, KR, o, damga), "08_tani_paneli.html"),
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
