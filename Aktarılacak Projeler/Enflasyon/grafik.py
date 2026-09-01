# -*- coding: utf-8 -*-
"""Enflasyon panosu — grafik katmanı (Plotly, site ev stili).

Kurallar (site sözleşmesi):
  · Çok panelli figürlerde paneller ALT ALTA (rows=N, cols=1). Yan yana panel YOK.
  · Panel başına ~340 px + başlık/lejant payı; buradaki `height` MDX'teki
    `yukseklik={}` ile AYNI olmak zorunda (aşağıdaki SEKILLER tablosu tek kaynak).
  · Başlık solda, iki satır: "<b>Başlık</b><br><sup>alt başlık</sup>".
  · Lejant altta yatay, beyaz zemin, include_plotlyjs="cdn",
    config: responsive=True, displaylogo=False.
  · Şekil numarası BELGE SIRASINI izler; dosya adı = şekil no (NN_ad.html).
  · Her grafiğin başlığında VERİ TARİHİ vardır (bayat grafik gözle görülür).

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
from veri import VERI, ad_uzun

CIKTI = veri.PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

# Ev stili jetonları — site/tools/plotly_stil.py ve diğer hatlarla aynı
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
LACI, MOR, YESIL, GRI = "#2f4b7c", "#665191", "#7a9e7e", "#8a8a8a"
PALET = [TEAL, CLARET, GOLD, LACI, MOR, "#a05195", YESIL]

PANEL_PX = 340          # panel başına tasarım yüksekliği
UST_PAY = 96            # iki satırlık başlık payı
LEJANT_SATIR_PX = 22    # lejant satır yüksekliği
DIPNOT_SATIR_PX = 15
SATIR_KARAKTER = 118    # 10–11 px yazıda bir satıra sığan yaklaşık karakter

# Momentum panellerinin varsayılan penceresi. 2022–23 sıçramalarında 3 aylık
# SAAR %200'e çıkıyor; tüm tarihçeyi tek eksene koymak bugünkü 30 civarını
# okunamaz hâle getiriyordu. Tam tarihçe Şekil 01'in ikinci panelinde duruyor.
MOM_BAS = "2024-01-01"
TAM_BAS = "2013-01-01"
DIFUZYON_BAS = "2019-01-01"
REEL_BAS = "2018-01-01"


_AY_KISA_TR = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
               7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}


def _ay_tr(t) -> str:
    """'Feb 2022' değil 'Şub 2022' — strftime('%b') C yereliyle İngilizce basıyor."""
    return f"{_AY_KISA_TR[t.month]} {t.year}"


def _yil(tarih: str) -> int:
    """Pencere sabitinden yıl — panel başlıklarına DÜZ METİN yıl gömülmez.
    Sabit değişirse başlık da değişsin (sessizce yanlışa dönmesin)."""
    return int(str(tarih)[:4])


def _lejant_satir(fig) -> int:
    """Lejant kaç satır kaplayacak? Yatay lejantta etiketler yan yana dizilir."""
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
    çalışma zamanında `legend.y = −0,1` ve `margin.b = 110` dayatıyor; Plotly
    de figürden taşacak lejantı figürün ALT KENARINA yapıştırıyor (2300 px'lik
    REER figüründe ölçüldü: lejant 2259–2288 px arasına kenetleniyor). Bu
    yüzden sabit konumlu bir dipnot ek açıklaması, uzun figürlerde lejantın
    üstüne biniyor. Çözüm: açıklama satırları BAŞLIK bloğunda (<sup>) taşınıyor
    — ev stili başlıktaki her <br> için üst marjı 26 px büyütüyor, çakışma
    imkânsız. Uzun metodoloji notları sayfa metnine (MDX) ve README'ye ait.
    """
    for satir in alt:
        # Plotly başlık satırını sarmaz; uzun satır figürün sağından taşar.
        if len(re.sub("<[^>]+>", "", satir)) > 155:
            print(f"    UYARI: alt başlık satırı {len(satir)} karakter, taşabilir: "
                  f"{satir[:60]}…")
    l_satir = _lejant_satir(fig)
    # ÜST MARJ İNCE AYARI: plotly_stil.py önce margin.t'yi koşulsuz 92'ye çeker,
    # sonra YALNIZCA mevcut değer gerekenT'den KÜÇÜKSE gerekenT'ye yükseltir
    # (gerekenT = 92 + 26·<br> sayısı + 26, üst başlıklı subplot varsa). Yani
    # doğru değeri buraya yazmak ters teper: 196 yazarsak "küçük değil" deyip
    # 92'de bırakıyor ve alt başlık satırları panel başlığının üstüne biniyor.
    # Bir eksik yazıyoruz; ev stili kendi hesabına yükseltiyor.
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
    if y_baslik:
        fig.update_yaxes(title_text=y_baslik)
    return fig


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


def _cizgi(fig, s: pd.Series, ad: str, renk: str, row=1, kalin=2.0,
           kesik=None, grup=None, gizle=False):
    s = s.dropna()
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, name=ad, mode="lines",
        line=dict(color=renk, width=kalin, dash=kesik),
        legendgroup=grup or ad, showlegend=not gizle,
        hovertemplate="%{y:.2f}<extra>" + ad + "</extra>"), row=row, col=1)


# ---------------------------------------------------------------------------
def _yukle():
    a = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    M = pd.read_csv(VERI / "metrik.csv", index_col=0, parse_dates=True)
    SA = pd.read_csv(VERI / "sa.csv", index_col=0, parse_dates=True)
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    K = (pd.read_csv(VERI / "katki.csv", index_col=0, parse_dates=True)
         if (VERI / "katki.csv").exists() else pd.DataFrame())
    D = (pd.read_csv(VERI / "dagilim.csv", index_col=0, parse_dates=True)
         if (VERI / "dagilim.csv").exists() else pd.DataFrame())
    B = pd.read_csv(VERI / "baz_senaryo.csv", index_col=0, parse_dates=True)
    R = (pd.read_csv(VERI / "reel_faiz.csv", index_col=0, parse_dates=True)
         if (VERI / "reel_faiz.csv").exists() else pd.DataFrame())
    tani = json.loads((VERI / "sa_tani.json").read_text(encoding="utf-8"))
    return a, M, SA, K, D, B, R, o, tani


def ser(M: pd.DataFrame, seri: str, kol: str, bas=MOM_BAS) -> pd.Series:
    d = M[M["seri"] == seri]
    if d.empty or kol not in d.columns:
        return pd.Series(dtype=float)
    return d[kol].loc[d.index >= bas].dropna()


# ===========================================================================
def sekil_01(M, o, damga):
    """ANA GRAFİK: manşet momentum üçlüsü — yakın plan + tam tarihçe."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10,
                        subplot_titles=(
                            f"Yakın plan — dezenflasyon dönemi ({_yil(MOM_BAS)}'ten bu yana)",
                            f"Tam tarihçe ({_yil(TAM_BAS)}'ten bu yana): sıçramalar ölçeği bastırır"))
    for r, bas in ((1, MOM_BAS), (2, TAM_BAS)):
        gizle = r > 1
        _cizgi(fig, ser(M, "tufe", "yillik", bas), "12 aylık (manşet)", GRI,
               row=r, kalin=1.6, grup="y12", gizle=gizle)
        _cizgi(fig, ser(M, "tufe", "saar6_sa", bas),
               "6 aylık SAAR (mevsimsellikten arındırılmış)", TEAL,
               row=r, kalin=2.4, grup="s6", gizle=gizle)
        _cizgi(fig, ser(M, "tufe", "saar3_sa", bas),
               "3 aylık SAAR (mevsimsellikten arındırılmış)", CLARET,
               row=r, kalin=2.6, grup="s3", gizle=gizle)
        _cizgi(fig, ser(M, "tufe", "ecb3", bas), "ECB tipi 3a/3a momentum", GOLD,
               row=r, kalin=1.4, kesik="dot", grup="ecb", gizle=gizle)
        # HAM (arındırılmamış) yıllıklandırılmışlar: model varsayımı taşımayan,
        # yayımlanmış endeksten doğrudan çıkan karşılıklar. Arındırılmışla aradaki
        # açıklık mevsimselliğin o ay ne kadar iş yaptığını gösterir.
        _cizgi(fig, ser(M, "tufe", "saar3_ham", bas), "3 aylık — ham (arındırılmamış)",
               CLARET, row=r, kalin=1.3, kesik="dash", grup="h3", gizle=gizle)
        _cizgi(fig, ser(M, "tufe", "saar6_ham", bas), "6 aylık — ham (arındırılmamış)",
               TEAL, row=r, kalin=1.3, kesik="dash", grup="h6", gizle=gizle)
    son = ser(M, "tufe", "saar3_sa", MOM_BAS)
    fig.add_trace(go.Scatter(
        x=son.index[-3:], y=son.values[-3:], mode="markers",
        name="son 3 ay: uç henüz oturmadı",
        marker=dict(color="white", size=8, line=dict(color=CLARET, width=1.8)),
        hovertemplate="%{y:.2f}<extra>son 3 ay — revizyona açık</extra>"),
        row=1, col=1)
    fig.update_yaxes(title_text="yıllık %")

    # ALT PANEL: tam tarihçede 3a SAAR Şubat 2022'de %200'e çıkıyor. Bu bir aykırı
    # değer DEĞİL, ölçünün varlık sebebi: kur şokunun geçişkenliği aylık fiyatlamada
    # patlarken 12 aylık oran onu aylara yayıp geç gösteriyor. Bu yüzden eksen
    # KIRPILMAZ (kırpmak 2022'yi, yani dersin en öğretici epizodunu gizler);
    # bunun yerine panel yükseltilir ve zirve etiketlenir.
    tam3 = ser(M, "tufe", "saar3_sa", TAM_BAS)
    tam12 = ser(M, "tufe", "yillik", TAM_BAS)
    if len(tam3):
        zirve_t = tam3.idxmax()
        zirve_v = float(tam3.max())
        y12_o_an = float(tam12.reindex([zirve_t]).iloc[0]) if zirve_t in tam12.index else float("nan")
        fig.add_annotation(
            x=zirve_t, y=zirve_v, row=2, col=1,
            text=(f"3a SAAR zirvesi %{zirve_v:.0f} ({_ay_tr(zirve_t)})"
                  + (f"<br>12 aylık o an %{y12_o_an:.0f} — gecikme burada görünür"
                     if y12_o_an == y12_o_an else "")),
            showarrow=True, arrowhead=2, arrowsize=0.8, arrowwidth=1.2,
            arrowcolor=CLARET, ax=70, ay=-30,
            font=dict(size=11, color=CLARET), align="left",
            bgcolor="rgba(255,255,255,0.86)", bordercolor=CLARET, borderwidth=1)
        fig.update_yaxes(range=[min(0.0, float(tam3.min()) * 1.1), zirve_v * 1.14],
                         row=2, col=1)

    for an in fig.layout.annotations:
        if an.yanchor == "bottom" and str(an.xref).endswith(("paper", "domain")):
            an.font.size = 12
            an.font.color = INK
    return _duzen(
        fig,
        "Manşet enflasyon momentumu: 3 ve 6 aylık yıllıklandırılmış",
        [f"TÜFE (2025=100), zincir yıllıklandırma (P_t/P_t−n)^(12/n)−1 · veri: {damga}",
         "SAAR: bugünkü fiyatlama temposu 12 ay sürerse yıllık enflasyon ne olurdu — "
         "12 aylık oran bu temponun hareketli ortalamasıdır, dönüşleri geç gösterir",
         "Son 3 nokta içi boş: arındırma filtresi serinin ucunda tek taraflıdır, "
         "bu değerler sonraki koşularda revize olur",
         "Alt panelin ekseni kırpılmadı: 2022'deki sıçrama aykırı değer değil, "
         "momentum ölçüsünün varlık sebebidir",
         "Kesikli çizgiler HAM (arındırılmamış) yıllıklandırılmış karşılıklar — "
         "arındırılmışla aradaki açıklık, mevsimselliğin o ay ne kadar iş yaptığıdır"],
        n_panel=2, y_baslik="yıllık %", ek_yukseklik=180)


def sekil_02(M, damga):
    """Çekirdek B ve C, aynı momentum üçlüsüyle."""
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.09,
                        subplot_titles=("Çekirdek B — işlenmemiş gıda, enerji, alkol-tütün ve altın hariç",
                                        "Çekirdek C — enerji, gıda, alkol-tütün ve altın hariç"))
    for i, ad in enumerate(("cekirdek_b", "cekirdek_c"), start=1):
        _cizgi(fig, ser(M, ad, "yillik"), "12 aylık", GRI, row=i, kalin=1.6,
               grup="y12", gizle=i > 1)
        _cizgi(fig, ser(M, ad, "saar6_sa"), "6 aylık SAAR", TEAL, row=i, kalin=2.2,
               grup="s6", gizle=i > 1)
        _cizgi(fig, ser(M, ad, "saar3_sa"), "3 aylık SAAR", CLARET, row=i, kalin=2.4,
               grup="s3", gizle=i > 1)
    fig.update_yaxes(title_text="yıllık %")
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    return _duzen(
        fig, "Çekirdek göstergelerde momentum",
        [f"ÖKTG-B ve ÖKTG-C (2025=100), TCMB tanımları · veri: {damga}",
         "B ile C arasındaki tek fark işlenmiş gıdadır; Türkiye'de bu kalem emtia ve "
         "kur geçişkenliği taşıdığı için ikisi sistematik ayrışır"],
        n_panel=2)


def sekil_03(a, M, SA, tani, damga):
    """Arındırmanın ne yaptığı: ham vs SA."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=("Aylık değişim: ham ve mevsimsellikten arındırılmış",
                                        "3 aylık yıllıklandırılmış: ham veriyle hesaplamanın bedeli"))
    h = ser(M, "tufe", "aylik_ham", bas=MOM_BAS)
    s = ser(M, "tufe", "aylik_sa", bas=MOM_BAS)
    fig.add_trace(go.Bar(x=h.index, y=h.values, name="ham aylık", marker_color=GRID,
                         marker_line_color=GRI, marker_line_width=0.4,
                         hovertemplate="%{y:.2f}<extra>ham aylık</extra>"), row=1, col=1)
    _cizgi(fig, s, "arındırılmış aylık", CLARET, row=1, kalin=2.2)
    _cizgi(fig, ser(M, "tufe", "saar3_ham", bas=MOM_BAS),
           "3a SAAR — ham veriyle (yanıltıcı)", GRI, row=2, kalin=1.8, kesik="dash")
    _cizgi(fig, ser(M, "tufe", "saar3_sa", bas=MOM_BAS),
           "3a SAAR — arındırılmış", CLARET, row=2, kalin=2.4)
    fig.update_yaxes(title_text="aylık %", row=1, col=1)
    fig.update_yaxes(title_text="yıllık %", row=2, col=1)
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    p = tani.get("seriler", {}).get("tufe", {})
    kat = p.get("tatil_katsayi", {})
    tat = ", ".join(f"{k}: {v:+.2f} pp" for k, v in kat.items() if abs(v) > 1e-9) or "hiçbiri anlamlı değil"
    return _duzen(
        fig, "Mevsimsellikten arındırma ne yapıyor?",
        [f"{tani.get('yontem', '')} · veri: {damga}",
         f"Ön aşamada hareketli dinî tatil regresörleri çıkarılır — bu koşuda anlamlı "
         f"bulunanlar: {tat}",
         "Alt paneldeki fark yöntem tercihi değil ölçüm hatasıdır: ham 3 aylık SAAR "
         "yalnızca \"hangi üç ay pencereye düştü\" sorusunu ölçer"],
        n_panel=2)


def sekil_04(K, o, damga):
    """Katkı ayrıştırma — yıllık ve aylık."""
    if K.empty:
        return None
    grup = {f"oktg{v[1][-2:]}": v[0] for v in veri.KATKI_GRUP.values()}
    renk = {"oktg10": GOLD, "oktg09": LACI, "oktg18": TEAL,
            "oktg22": MOR, "oktg23": CLARET}
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=("Yıllık enflasyona katkı (puan) — ileriye bileşiklenmiş aylık katkılar",
                                        "Aylık enflasyona katkı (puan) — son 36 ay"))
    y = K[K.index >= "2016-01-01"]
    for k, ad in grup.items():
        if f"y_{k}" not in y.columns:
            continue
        fig.add_trace(go.Bar(x=y.index, y=y[f"y_{k}"] * 100, name=ad,
                             marker_color=renk[k], legendgroup=k,
                             hovertemplate="%{y:.2f} puan<extra>" + ad + "</extra>"),
                      row=1, col=1)
    fig.add_trace(go.Scatter(x=y.index, y=y["pi_12"] * 100, name="12 aylık enflasyon",
                             mode="lines", line=dict(color=INK, width=1.6),
                             legendgroup="mansettoplam",
                             hovertemplate="%{y:.2f}%<extra>manşet</extra>"), row=1, col=1)
    m = K.tail(36)
    for k, ad in grup.items():
        if f"c_{k}" not in m.columns:
            continue
        fig.add_trace(go.Bar(x=m.index, y=m[f"c_{k}"] * 100, name=ad,
                             marker_color=renk[k], legendgroup=k, showlegend=False,
                             hovertemplate="%{y:.2f} puan<extra>" + ad + "</extra>"),
                      row=2, col=1)
    fig.add_trace(go.Scatter(x=m.index, y=m["pi"] * 100, name="aylık enflasyon",
                             mode="lines+markers", line=dict(color=INK, width=1.4),
                             marker=dict(size=4), legendgroup="mansettoplam",
                             showlegend=False,
                             hovertemplate="%{y:.2f}%<extra>aylık manşet</extra>"),
                  row=2, col=1)
    fig.update_layout(barmode="relative")
    fig.update_yaxes(title_text="puan", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    ag = o.get("agirlik_son_yil", {})
    kay = o.get("agirlik_kayma_pp", {})
    kisa = {"oktg10": "gıda", "oktg09": "enerji", "oktg18": "temel mal",
            "oktg22": "alkol-tütün-altın", "oktg23": "hizmet"}
    kayma = (" · ".join(f"{kisa.get(k, k)} {v:+.1f}"
                        for k, v in sorted(kay.items(), key=lambda x: -abs(x[1])))
             if kay else "—")
    return _duzen(
        fig, "Enflasyon nereden geliyor? Katkı ayrıştırması",
        [f"TCMB'nin beşli gruplaması, ÖKTG ağacı · veri: {damga}",
         f"Yıllık katkı = aylık katkıların İLERİYE BİLEŞİKLENMİŞ toplamı; artık son 24 ayda "
         f"en çok {o.get('katki_yil_artik_pp', 0):.4f} puan",
         f"EVDS ağırlık yayımlamaz — ağırlıklar zincir-Laspeyres kimliğinden tahmin "
         f"edildi; {ag.get('yil', '')} kimlik artığı {ag.get('artik_pp', 0)} puan",
         f"{ag.get('yil', '')} ağırlık kayması (puan): {kayma}"],
        n_panel=2)


def sekil_05(D, M, o, damga):
    """Difüzyon + kırpılmış ortalama/medyan."""
    if D.empty:
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=(
                            f"Kırpılmış ortalama ve medyan — 3 aylık ortalamanın "
                            f"yıllıklandırılmışı ({_yil(MOM_BAS)}'ten bu yana)",
                            f"Difüzyon: fiyat artışı ne kadar yaygın? "
                            f"({_yil(DIFUZYON_BAS)}'dan bu yana, 3 aylık ortalama, ağırlıklı %)"))
    d = D[D.index >= MOM_BAS]
    ust = d["kirpma_10_saar3"].combine(d["kirpma_05_saar3"], max)
    alt = d["kirpma_10_saar3"].combine(d["kirpma_05_saar3"], min)
    fig.add_trace(go.Scatter(x=d.index, y=ust, mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=d.index, y=alt, mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(29,92,92,0.13)",
                             name="kırpma bandı (α=0,05–0,10)",
                             hoverinfo="skip"), row=1, col=1)
    _cizgi(fig, d["kirpma_08_saar3"], "kırpılmış ortalama (α=0,08 · Cleveland Fed standardı)",
           TEAL, row=1, kalin=2.2)
    _cizgi(fig, d["medyan_saar3"], "ağırlıklı medyan", GOLD, row=1, kalin=2.0)
    _cizgi(fig, ser(M, "tufe", "saar3_sa", bas=MOM_BAS), "TÜFE 3a SAAR",
           CLARET, row=1, kalin=1.6, kesik="dash")
    # Difüzyon 0–100 arasında sınırlı bir ölçü; momentum panelinden daha uzun
    # bir pencere taşıyabilir ve yaygınlığın rejim değişimi ancak öyle görünür.
    # Aylık difüzyon 60–100 arasında sert salınıyor ve okunmuyor; TCMB'nin ana
    # eğilim sunumundaki gibi 3 AYLIK ORTALAMA çiziliyor (ham aylık seri
    # dagilim.csv'de duruyor).
    d2 = D[D.index >= DIFUZYON_BAS].rolling(3).mean()
    _cizgi(fig, d2["difuzyon_0"], "fiyatı ARTAN kalemlerin ağırlıklı payı (eşik %0)",
           CLARET, row=2, kalin=2.2)
    _cizgi(fig, d2["difuzyon_hedef"],
           f"hedefle uyumlu tempoyu AŞAN payı (eşik aylık %{metrik.HEDEF_AYLIK:.2f})",
           TEAL, row=2, kalin=2.0)
    _cizgi(fig, d2["difuzyon_mansete_gore"], "manşetten hızlı artan payı (değişken eşik)",
           GOLD, row=2, kalin=1.6, kesik="dot")
    fig.update_yaxes(title_text="yıllık %", row=1, col=1)
    fig.update_yaxes(title_text="ağırlıklı %", row=2, col=1, range=[0, 100])
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    n = int(D["kesit_n"].iloc[-1])
    kt = (o or {}).get("kesit_tani") or {}
    ham_n = kt.get("arindirilmayan_n")
    ham_w = kt.get("arindirilmayan_agirlik")
    yog = kt.get("yogunlasma") or {}
    # KESİT NİTELENDİRMESİ: "arındırılmış aylık değişimler" cümlesi kesitin
    # dörtte biri HAM geçtiği için tek başına yanıltıcı; yoğunlaşma da öyle
    # (43 grup var ama eşdeğer bağımsız kalem sayısı ~13). İkisi de dipnota girer.
    alt_satir = [f"{n} adet üç haneli COICOP grubunun aylık değişimleri, etkin "
                 f"ağırlıklarla · veri: {damga}"]
    if ham_n:
        alt_satir.append(
            f"Kesitin {ham_n}'i (ağırlıkça %{ham_w:.1f}) mevsimsellik testinden "
            f"geçemedi ve HAM geçti — ölçüler karma bir kesit üzerindedir")
    if yog.get("esdeger_kalem"):
        alt_satir.append(
            f"Kesit yoğun: en büyük kalem ağırlığın %{yog['en_buyuk_pay']}'ini taşıyor, "
            f"eşdeğer bağımsız kalem sayısı {yog['esdeger_kalem']}")
    return _duzen(
        fig, "Dağılım ölçüleri: kırpılmış ortalama, medyan ve yaygınlık",
        alt_satir + [
         "Kırpma seviyesi keyfîdir: α=0,05–0,10 bandı taralı verildi, bandın genişliği "
         "ölçü belirsizliğinin kendisidir (medyan α→0,5 limitidir)",
         "Difüzyon bir seviye değil YAYGINLIK ölçüsüdür — enflasyon düşerken yüksek "
         "kalıyorsa düşüş birkaç kalemden geliyordur ve kırılgandır"],
        n_panel=2)


def sekil_06(M, o, damga):
    """Hizmet vs temel mal + atalet."""
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.065,
                        subplot_titles=("12 aylık enflasyon: hizmet ve temel mal",
                                        "3 aylık yıllıklandırılmış momentum",
                                        "Kalıcılık: 36 aylık yuvarlanan AR(1) katsayısı (ρ)"))
    hs = ser(M, "hizmet", "yillik", bas=MOM_BAS)
    tm = ser(M, "temel_mal", "yillik", bas=MOM_BAS)
    _cizgi(fig, hs, "Hizmet", CLARET, row=1, kalin=2.4)
    _cizgi(fig, tm, "Temel mallar", TEAL, row=1, kalin=2.4)
    mak = (hs - tm).dropna()
    fig.add_trace(go.Scatter(x=mak.index, y=mak.values, name="makas (hizmet − temel mal)",
                             mode="lines", line=dict(color=GOLD, width=1.4, dash="dot"),
                             hovertemplate="%{y:.1f} puan<extra>makas</extra>"),
                  row=1, col=1)
    _cizgi(fig, ser(M, "hizmet", "saar3_sa", bas=MOM_BAS), "Hizmet 3a SAAR",
           CLARET, row=2, kalin=2.2, grup="hs3")
    _cizgi(fig, ser(M, "temel_mal", "saar3_sa", bas=MOM_BAS), "Temel mal 3a SAAR",
           TEAL, row=2, kalin=2.2, grup="tm3")
    at = o.get("atalet_seri", {})
    for ad, renk, etiket in (("hizmet", CLARET, "Hizmet ρ"),
                             ("temel_mal", TEAL, "Temel mal ρ"),
                             ("tufe", GRI, "TÜFE ρ")):
        s = at.get(ad)
        if not s:
            continue
        ss = pd.Series({pd.Timestamp(k): v for k, v in s.items()}).sort_index()
        ss = ss[ss.index >= "2016-01-01"]
        _cizgi(fig, ss, etiket, renk, row=3, kalin=2.0 if ad != "tufe" else 1.4,
               kesik="dot" if ad == "tufe" else None)
    fig.update_yaxes(title_text="yıllık % / puan", row=1, col=1)
    fig.update_yaxes(title_text="yıllık %", row=2, col=1)
    fig.update_yaxes(title_text="ρ", row=3, col=1)
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    return _duzen(
        fig, "Hizmet mi mal mı? Dezenflasyonun en yapışkan bileşeni",
        [f"ÖKTG hizmet (OKTG23) ve temel mallar (OKTG18) · veri: {damga}",
         "Makas, dezenflasyonun tamamlanıp tamamlanmadığının en okunaklı tek sayısıdır",
         "ρ: arındırılmış aylık değişimin kendi gecikmesine 36 aylık yuvarlanan "
         "regresyonu — 1'e yaklaştıkça fiyatlama geçmişe bağlıdır"],
        n_panel=3)


def sekil_07(a, M, o, damga):
    """Beklentiler ve isabet."""
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.065,
                        subplot_titles=("12 ay sonrası enflasyon beklentisi — üç kesim",
                                        "PKA ufukları ve gerçekleşme",
                                        "Anket isabeti: ufka göre ortalama mutlak hata ve yanlılık"))
    ge = ser(M, "tufe", "yillik", bas="2015-01-01")
    _cizgi(fig, ge, "Gerçekleşen 12 aylık", INK, row=1, kalin=1.6)
    for ad, renk, etiket in (("pka_12a", TEAL, "Piyasa katılımcıları (PKA)"),
                             ("reel_kesim_12a", GOLD, "Reel sektör (İYA)"),
                             ("hanehalki_12a", CLARET, "Hanehalkı")):
        if ad in a.columns:
            s = a[ad].dropna()
            _cizgi(fig, s[s.index >= "2015-01-01"], etiket, renk, row=1, kalin=2.0)
    _cizgi(fig, ge, "Gerçekleşen 12 aylık", INK, row=2, kalin=1.6, grup="ger",
           gizle=True)
    for ad, renk, etiket, kesik in (
            ("pka_yilsonu", LACI, "PKA · cari yıl sonu", None),
            ("pka_12a", TEAL, "PKA · 12 ay sonrası", None),
            ("pka_24a", MOR, "PKA · 24 ay sonrası", "dash"),
            ("pka_5y", YESIL, "PKA · 5 yıl sonrası", "dot")):
        if ad in a.columns:
            s = a[ad].dropna()
            _cizgi(fig, s[s.index >= "2015-01-01"], etiket, renk, row=2,
                   kalin=1.8, kesik=kesik)
    bek = o.get("beklenti_isabet", {})
    ufuklar = ["h0", "h1", "h2"]
    etiket = {"h0": "cari ay (nowcast)", "h1": "1 ay ileri", "h2": "2 ay ileri"}
    for pen, renk, ad in (("p36", CLARET, "son 36 ay"), ("p60", GRI, "son 60 ay")):
        x = [etiket[h] for h in ufuklar if h in bek]
        y = [bek[h][pen]["mae"] for h in ufuklar if h in bek]
        fig.add_trace(go.Bar(x=x, y=y, name=f"MAE · {ad}", marker_color=renk,
                             hovertemplate="%{y:.2f} puan<extra>MAE " + ad + "</extra>"),
                      row=3, col=1)
    for pen, renk, ad in (("p36", TEAL, "son 36 ay"), ("p60", GOLD, "son 60 ay")):
        x = [etiket[h] for h in ufuklar if h in bek]
        y = [bek[h][pen]["yanlilik"] for h in ufuklar if h in bek]
        fig.add_trace(go.Scatter(x=x, y=y, name=f"Yanlılık · {ad}", mode="markers+lines",
                                 marker=dict(color=renk, size=10, symbol="diamond"),
                                 line=dict(color=renk, width=1, dash="dot"),
                                 hovertemplate="%{y:+.2f} puan<extra>yanlılık " + ad + "</extra>"),
                      row=3, col=1)
    fig.update_yaxes(title_text="yıllık %", row=1, col=1)
    fig.update_yaxes(title_text="yıllık %", row=2, col=1)
    fig.update_yaxes(title_text="puan", row=3, col=1)
    fig.update_layout(barmode="group")
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    n = o.get("bek__pka_12a_n")
    kat = (f"PKA'nın bu koşudaki katılımcı sayısı {n:.0f}. " if n else "")
    return _duzen(
        fig, "Beklentiler ve gerçekleşme",
        [f"TCMB Piyasa Katılımcıları Anketi (uygun ortalama), İYA ve hanehalkı özetleri · "
         f"veri: {damga}",
         "Üç kesimin ölçeği aynı değildir; hanehalkı sistematik olarak yukarıda okur"
         + (f" · PKA katılımcı sayısı {n:.0f}" if n else ""),
         "Alt panel: e = gerçekleşme − beklenti; yanlılık pozitifse anket enflasyonu "
         "EKSİK tahmin etmiştir"],
        n_panel=3)


def sekil_08(R, M, o, damga):
    """Reel faiz."""
    if R.empty:
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=(
                            f"Reel faiz — tam Fisher: (1+i)/(1+π)−1 ({_yil(REEL_BAS)}'den bu yana)",
                            f"Nominal faiz ve enflasyon ölçüleri ({_yil(MOM_BAS)}'ten bu yana)"))
    d = R[R.index >= REEL_BAS]
    _cizgi(fig, d["ex_post"], "ex-post (gerçekleşen 12 aylık enflasyonla)", GRI,
           row=1, kalin=1.8)
    _cizgi(fig, d["ex_ante"], "ex-ante (PKA 12 ay beklentisiyle)", TEAL, row=1, kalin=2.2)
    _cizgi(fig, d["egilime_gore"], "ana eğilime göre (3 aylık SAAR ile)", CLARET,
           row=1, kalin=2.4)
    _cizgi(fig, d["ileri_ex_ante"], "ileriye dönük (12 ay sonraki faiz / 24 ay sonraki enflasyon)",
           GOLD, row=1, kalin=1.6, kesik="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=1), row=1, col=1)
    # Alt panel dar pencerede: 3 aylık SAAR 2022'de %200'e çıkıyor ve tüm
    # tarihçe tek eksene konursa bugünkü 30 civarı okunmaz hâle geliyor.
    d2 = R[R.index >= MOM_BAS]
    _cizgi(fig, d2["faiz"], "TCMB ağırlıklı ortalama fonlama maliyeti", INK, row=2, kalin=2.2)
    _cizgi(fig, d2["pi12"], "12 aylık enflasyon", GRI, row=2, kalin=1.6)
    _cizgi(fig, d2["egilim3"], "3 aylık SAAR", CLARET, row=2, kalin=2.0)
    _cizgi(fig, d2["bek12"], "PKA 12 ay beklentisi", TEAL, row=2, kalin=1.6, kesik="dot")
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="%", row=2, col=1)
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    return _duzen(
        fig, "Reel faiz: hangi enflasyonla ölçüyorsunuz?",
        [f"Faiz: TP.APIFON4 — EVDS'te \"politika faizi\" adlı bir seri yoktur · veri: {damga}",
         "Yaklaşık Fisher (r ≈ i − π) yüksek enflasyonda kullanılamaz: i=%40, π=%32 iken "
         "tam formül %6,06, yaklaşık %8,00 verir",
         "Yıllık enflasyonla hesaplanan reel faiz, dezenflasyonda politikanın sıkılığını "
         "sistematik olarak EKSİK gösterir"],
        n_panel=2)


def sekil_09(a, B, damga):
    """Baz etkisi patikası."""
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.09,
                        subplot_titles=("Önümüzdeki 12 ayın yıllık enflasyon patikası — üç senaryo",
                                        "Hesabın dışına düşen aylar: baz elverişli mi?"))
    ger = ((a["tufe"] / a["tufe"].shift(12) - 1) * 100).dropna()
    ger = ger[ger.index >= "2024-01-01"]
    _cizgi(fig, ger, "Gerçekleşen 12 aylık", INK, row=1, kalin=2.0)
    kopru = pd.concat([ger.tail(1)])
    for ad, renk, etiket in (
            ("son3_sa", CLARET, f"arındırılmış son 3 ayın temposu sürerse (aylık %{B['son3_sa_aylik'].iloc[0]:.2f})"),
            ("son12_ort", TEAL, f"son 12 ayın ortalaması sürerse (aylık %{B['son12_ort_aylik'].iloc[0]:.2f})"),
            ("gecen_yil", GOLD, "geçen yılın aylık oranları tekrarlarsa (yıllık sabit kalır)")):
        s = pd.concat([kopru, B[ad]])
        _cizgi(fig, s, etiket, renk, row=1, kalin=2.2,
               kesik="dot" if ad == "gecen_yil" else "dash")
    d = B["dusen_aylik"]
    renkler = [TEAL if v < B["son3_sa_aylik"].iloc[0] else CLARET for v in d.values]
    fig.add_trace(go.Bar(x=d.index, y=d.values, name="hesaptan düşen aylık oran",
                         marker_color=renkler,
                         hovertemplate="%{y:.2f}%<extra>bir yıl önceki aylık</extra>"),
                  row=2, col=1)
    fig.add_hline(y=float(B["son3_sa_aylik"].iloc[0]), line=dict(color=INK, width=1, dash="dot"),
                  row=2, col=1)
    fig.update_yaxes(title_text="yıllık %", row=1, col=1)
    fig.update_yaxes(title_text="aylık %", row=2, col=1)
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    return _duzen(
        fig, "Baz etkisi: önümüzdeki 12 ayın mekaniği",
        [f"1+π₁₂(t+h) = (1+π₁₂(t))·Π(1+π ileri)/Π(1+π düşen) · veri: {damga}",
         "Baz etkisi bir öngörü değil muhasebe kimliğidir; her senaryonun aylık varsayımı "
         "lejantta yazılıdır",
         "Alt panelde çubuklar hesaptan DÜŞEN (bir yıl önceki) aylık oranlar, kesikli "
         "çizgi ileri varsayım",
         "Çubuk çizginin ÜSTÜNDEYSE o ay yıllık enflasyon mekanik olarak geriler — "
         "baz elverişlidir"],
        n_panel=2)


# ===========================================================================
SEKILLER = [
    ("01_manset_momentum.html", 1),
    ("02_cekirdek_momentum.html", 2),
    ("03_arindirma.html", 2),
    ("04_katki.html", 2),
    ("05_dagilim_difuzyon.html", 2),
    ("06_hizmet_mal.html", 3),
    ("07_beklenti.html", 3),
    ("08_reel_faiz.html", 2),
    ("09_baz_etkisi.html", 2),
]


# ===========================================================================
# İTO kanadı — şekil 10-12
#
# NEDEN AYRI ÜÇ FİGÜR: İTO okuması üç ayrı soruya cevap veriyor ve üçü aynı
# eksene sığmıyor. (10) İki seri ne kadar yakın ve fark ne? (11) Farkı bir
# KURALA çevirebilir miyiz, ve o kural piyasanın fiyatladığı ankete karşı ne
# yapıyor? (12) İlişki kararlı mı, takvim ayı bir şey söylüyor mu?
#
# İTO PROFİLİ YOKSA FİGÜR ÜRETİLMEZ ve kos() hattı DURDURUR — sessizce eski
# grafikle taze metin yayımlanmasın (bkz. kos() sonundaki kapı).
def _ito_yukle() -> dict | None:
    y = VERI / "ito_profil.json"
    if not y.exists():
        return None
    d = json.loads(y.read_text(encoding="utf-8"))
    return d if d.get("tablo") else None


def sekil_10(ip, damga):
    """İTO ve TÜFE: aylık okuma, fark ve yıllık yakınsama.

    DIŞLANAN YIL GRAFİKTEN ÇIKARILMAZ, İŞARETLENİR. Kestirimden çıkarılan bir
    dönemi grafikten de silmek, okura "böyle bir dönem yoktu" demektir; oysa
    dışlamanın gerekçesi tam olarak o dönemin nasıl göründüğüdür."""
    if not ip:
        return None
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.075,
                        subplot_titles=("Aylık değişim: İTO (İstanbul) ve TÜFE (Türkiye)",
                                        "Fark = İTO − TÜFE, puan",
                                        "12 aylık değişim ve aradaki makas"))
    t = pd.DataFrame(ip["tablo"])
    if "dislandi" not in t.columns:
        t["dislandi"] = False
    x = pd.to_datetime(t["ay"] + "-01")
    fig.add_trace(go.Bar(x=x, y=t["ito"], name="İTO · aylık", marker_color=GOLD,
                         hovertemplate="%{y:.2f}%<extra>İTO</extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=x, y=t["tufe"], name="TÜFE · aylık", marker_color=TEAL,
                         hovertemplate="%{y:.2f}%<extra>TÜFE</extra>"), row=1, col=1)
    f = ip["fark"]
    ds = ip.get("dislama") or {}
    # Dışlanan aylar GRİ; kestirime giren aylar işaretine göre renkli.
    renk = [GRI if dis else (CLARET if v > 0 else LACI)
            for v, dis in zip(t["fark"], t["dislandi"])]
    fig.add_trace(go.Bar(x=x, y=t["fark"], name="Fark (İTO − TÜFE)",
                         marker_color=renk, customdata=t["dislandi"],
                         hovertemplate="%{y:+.2f} puan<extra>fark</extra>"),
                  row=2, col=1)
    # Dışlanan aralık her panelde gölgelendirilir — okur hangi dönemin
    # kestirime girmediğini bir bakışta görsün.
    if ds.get("n"):
        d0 = pd.Timestamp(ds["ilk_ay"] + "-01") - pd.Timedelta(days=15)
        d1 = pd.Timestamp(ds["son_ay"] + "-01") + pd.Timedelta(days=15)
        for r in (1, 2):
            fig.add_vrect(x0=d0, x1=d1, fillcolor=GRI, opacity=0.10,
                          line_width=0, row=r, col=1)
        fig.add_annotation(x=d0 + (d1 - d0) / 2, yref="y2 domain", y=1.0,
                           text=f"{', '.join(str(y) for y in ds['yillar'])} — "
                                "kestirim DIŞI (grafikte duruyor)",
                           showarrow=False, font=dict(size=10, color=GRI),
                           row=2, col=1)
    fig.add_hline(y=f["ort"], line=dict(color=INK, width=1.4, dash="dash"),
                  annotation_text=f"kestirim ortalaması {f['ort']:+.2f}".replace(".", ","),
                  annotation_position="top right",
                  annotation_font=dict(size=10, color=INK), row=2, col=1)
    for yon in (+1, -1):
        fig.add_hline(y=f["ort"] + yon * f["std"], line=dict(color=GRI, width=1, dash="dot"),
                      row=2, col=1)
    y = pd.DataFrame(ip["yillik"])
    xy = pd.to_datetime(y["ay"] + "-01")
    fig.add_trace(go.Scatter(x=xy, y=y["ito"], name="İTO · 12 aylık", mode="lines",
                             line=dict(color=GOLD, width=2.2),
                             hovertemplate="%{y:.2f}%<extra>İTO 12a</extra>"), row=3, col=1)
    fig.add_trace(go.Scatter(x=xy, y=y["tufe"], name="TÜFE · 12 aylık", mode="lines",
                             line=dict(color=TEAL, width=2.2),
                             hovertemplate="%{y:.2f}%<extra>TÜFE 12a</extra>"), row=3, col=1)
    fig.add_trace(go.Scatter(x=xy, y=y["fark"], name="Makas (puan)",
                             mode="lines", line=dict(color=CLARET, width=1.6, dash="dot"),
                             hovertemplate="%{y:+.2f} puan<extra>makas</extra>"),
                  row=3, col=1)
    fig.update_yaxes(title_text="aylık %", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    fig.update_yaxes(title_text="yıllık % / puan", row=3, col=1)
    fig.update_layout(barmode="group")
    for an in fig.layout.annotations:
        if an.text and "ortalama" not in an.text and "kestirim DIŞI" not in an.text:
            an.font.size = 12
            an.font.color = INK
    yo = ip.get("yillik_ozet", {})
    alt2 = (f"Fark ortalaması {f['ort']:+.2f} puan (medyan {f['medyan']:+.2f}), "
            f"İTO ayların %{f['ito_ustte_pay']:.0f}'inde yukarıda; "
            f"noktalı çizgiler ortalama ± 1 standart sapma").replace(".", ",")
    if ds.get("n"):
        alt2 += f" · gri sütunlar {', '.join(str(y) for y in ds['yillar'])}: kestirim dışı"
    return _duzen(
        fig, "İTO ile TÜFE: aynı ayın iki ölçümü",
        [f"İTO İstanbul endeksi (EVDS TP.FG.IST1.23) ve TÜFE Türkiye geneli · "
         f"tam örneklem {ip.get('tam_ilk_ay')}–{ip.get('tam_son_ay')} "
         f"(n={ip.get('n_tam')}), kestirim n={ip['n_toplam']} · veri: {damga}",
         alt2,
         f"Alt panel: 12 aylık makas {yo.get('maks', 0):.2f} puan zirvesinden "
         f"{yo.get('son', 0):.2f} puana indi".replace(".", ",")],
        n_panel=3)


def sekil_11(ip, damga):
    """İTO'dan TÜFE'ye: eşleme, kural yarışı, sürpriz."""
    if not ip or not ip.get("kural", {}).get("skor"):
        return None
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "Koşullu eşleme: İTO aylık okuması → TÜFE beklentisi",
                            "Kural yarışı: örneklem DIŞI ortalama mutlak hata",
                            "Sürpriz sürprizi öngörür mü? (ankete göre sapmalar)"))
    t = pd.DataFrame(ip["tablo"])
    if "dislandi" not in t.columns:
        t["dislandi"] = False
    es = pd.DataFrame(ip["esleme"])
    fig.add_trace(go.Scatter(x=es["ito"], y=es["ust"], mode="lines", name="%95 öngörü aralığı",
                             line=dict(color=GRID, width=0), showlegend=False,
                             hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=es["ito"], y=es["alt"], mode="lines", name="%95 öngörü aralığı",
                             line=dict(color=GRID, width=0), fill="tonexty",
                             fillcolor="rgba(29,92,92,0.10)",
                             hovertemplate="%{y:.2f}%<extra>alt sınır</extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=es["ito"], y=es["ito"], mode="lines", name="45° (TÜFE = İTO)",
                             line=dict(color=GRI, width=1.2, dash="dot"),
                             hovertemplate="%{y:.2f}%<extra>45°</extra>"), row=1, col=1)
    fig.add_trace(go.Scatter(x=es["ito"], y=es["tufe"], mode="lines",
                             name="Regresyon (kestirim örneklemi)",
                             line=dict(color=TEAL, width=2.4),
                             hovertemplate="%{y:.2f}%<extra>regresyon</extra>"), row=1, col=1)
    # DIŞLAMANIN ETKİSİ GÖRÜNÜR OLSUN: aynı kodla tam örneklemde kurulan
    # doğru da çizilir. İki doğru üst üste düşüyorsa dışlama sonucu
    # değiştirmiyor demektir ve okur bunu gözüyle görür.
    ka = (ip.get("karsilastirma") or {}).get("dahil") or {}
    if ka.get("egim") is not None:
        fig.add_trace(go.Scatter(
            x=es["ito"], y=ka["sabit"] + ka["egim"] * es["ito"], mode="lines",
            name="Regresyon (dışlanan yıllar DAHİL)",
            line=dict(color=MOR, width=1.8, dash="dash"),
            hovertemplate="%{y:.2f}%<extra>tam örneklem</extra>"), row=1, col=1)
    kal = t[~t["dislandi"]]
    dis = t[t["dislandi"]]
    fig.add_trace(go.Scatter(x=kal["ito"], y=kal["tufe"], mode="markers",
                             name="Aylık gözlem (kestirime giren)",
                             marker=dict(color=CLARET, size=7, opacity=0.8),
                             text=kal["ad"],
                             hovertemplate="%{text}<br>İTO %{x:.2f}% → TÜFE %{y:.2f}%"
                                           "<extra></extra>"), row=1, col=1)
    if len(dis):
        fig.add_trace(go.Scatter(x=dis["ito"], y=dis["tufe"], mode="markers",
                                 name="Dışlanan yıl (kestirime girmedi)",
                                 marker=dict(color=GRI, size=8, symbol="x",
                                             opacity=0.85),
                                 text=dis["ad"],
                                 hovertemplate="%{text}<br>İTO %{x:.2f}% → TÜFE %{y:.2f}%"
                                               "<extra>dışlandı</extra>"), row=1, col=1)
    ad = {"naif": "Naif: TÜFE = İTO", "sabit": "Sabit kaydırma",
          "medyan": "Medyan kaydırma", "oransal": "Oransal",
          "regresyon": "Regresyon", "takvimli": "Takvim ayı düzeltmeli"}
    sk = ip["kural"]["skor"]
    sira = sorted(sk, key=lambda c: sk[c]["mae"])
    kaz = ip["kural"]["kazanan"]
    anket = ip.get("anket") or {}
    etiket = [ad[c] for c in sira]
    deger = [sk[c]["mae"] for c in sira]
    renkler = [TEAL if c == kaz else (CLARET if c == "takvimli" else GRI) for c in sira]
    if anket.get("pka_mae") is not None:
        etiket.append("PKA anketi (piyasa)")
        deger.append(anket["pka_mae"])
        renkler.append(GOLD)
    fig.add_trace(go.Bar(x=etiket, y=deger, marker_color=renkler, name="MAE, puan",
                         hovertemplate="%{y:.3f} puan<extra>%{x}</extra>"), row=2, col=1)
    sp = ip.get("surpriz") or {}
    if sp:
        xs = np.linspace(-1.5, 1.5, 40)
        fig.add_trace(go.Scatter(x=xs, y=sp["sabit"] + sp["egim"] * xs, mode="lines",
                                 name=f"TÜFE sürprizi = {sp['sabit']:.2f} + "
                                      f"{sp['egim']:.2f} × İTO sürprizi",
                                 line=dict(color=CLARET, width=2.4),
                                 hovertemplate="%{y:+.2f} puan<extra></extra>"), row=3, col=1)
        fig.add_trace(go.Scatter(x=xs, y=xs, mode="lines", name="Birebir geçiş (45°)",
                                 line=dict(color=GRI, width=1.2, dash="dot"),
                                 hoverinfo="skip"), row=3, col=1)
        fig.add_hline(y=0, line=dict(color=GRID, width=1), row=3, col=1)
        fig.add_vline(x=0, line=dict(color=GRID, width=1), row=3, col=1)
    fig.update_xaxes(title_text="İTO aylık, %", row=1, col=1)
    fig.update_yaxes(title_text="TÜFE aylık, %", row=1, col=1)
    fig.update_yaxes(title_text="MAE, puan", row=2, col=1)
    fig.update_xaxes(title_text="İTO − anket, puan", row=3, col=1)
    fig.update_yaxes(title_text="TÜFE − anket, puan", row=3, col=1)
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    k = ip["kural"]
    r = ip["regresyon"]
    alt3 = ("Sürpriz regresyonu ölçülemedi (anket serisi eksik)" if not sp else
            f"İTO ankete göre 1 puan yukarıdaysa TÜFE ortalama "
            f"{sp['egim']:.2f} puan yukarıda geliyor (t={sp['t']:.2f}, "
            f"R²={sp['r2']:.2f}, işaret uyumu %{sp['isaret_uyumu']:.0f})".replace(".", ","))
    return _duzen(
        fig, "İTO okumasından TÜFE beklentisine",
        [f"Aralık %95 ÖNGÖRÜ aralığıdır (güven aralığı değil): tek bir ayın "
         f"nereye düşeceğini gösterir · kestirim n={r['n']} ay · veri: {damga}",
         f"Orta panel: her kural genişleyen pencereyle, KENDİ geleceğini görmeden "
         f"kuruldu · {k['n']} örneklem dışı ay ({k['ilk_ay']}–{k['son_ay']})",
         alt3],
        n_panel=3)


def sekil_12(ip, damga):
    """Takvim ayı profili, ilişkinin kararlılığı ve dışlanan dönem."""
    if not ip or not ip.get("kayan"):
        return None
    ds = ip.get("dislama") or {}
    # ÜÇÜNCÜ PANEL HER ZAMAN ÇİZİLİR. Yalnız dışlama varken çizilseydi, hiçbir
    # şey dışlanmadığında okur "örneklem hangi enflasyon rejimini kapsıyor"
    # sorusunu soramazdı — oysa bir eşleme kuralının en önemli sınırı budur:
    # kural, ancak gördüğü rejimde geçerlidir.
    n_panel = 3
    basliklar = ["Takvim ayına göre ortalama fark (İTO − TÜFE) — kestirim örneklemi",
                 "İlişki kararlı mı? 12 aylık kayan korelasyon, eğim ve ortalama fark",
                 ("Örneklem hangi rejimi kapsıyor? Aylık TÜFE — dışlanan dönem gri"
                  if ds.get("n") else
                  "Örneklem hangi rejimi kapsıyor? Aylık TÜFE'nin salınımı")]
    fig = make_subplots(rows=n_panel, cols=1, vertical_spacing=0.09,
                        subplot_titles=tuple(basliklar))
    tk = pd.DataFrame(ip["takvim"])
    fig.add_trace(go.Bar(x=tk["ad"], y=tk["ort_fark"],
                         marker_color=[CLARET if v > 0 else LACI for v in tk["ort_fark"]],
                         name="Ortalama fark", text=[f"n={n}" for n in tk["n"]],
                         textposition="outside", textfont=dict(size=10, color=GRI),
                         hovertemplate="%{y:+.2f} puan · %{text}<extra>%{x}</extra>"),
                  row=1, col=1)
    fig.add_hline(y=ip["fark"]["ort"], line=dict(color=INK, width=1.4, dash="dash"),
                  row=1, col=1)
    ky = pd.DataFrame(ip["kayan"])
    xk = pd.to_datetime(ky["ay"] + "-01")
    fig.add_trace(go.Scatter(x=xk, y=ky["r"], name="Korelasyon (r)", mode="lines",
                             line=dict(color=TEAL, width=2.2),
                             hovertemplate="%{y:.3f}<extra>r</extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=xk, y=ky["egim"], name="Regresyon eğimi", mode="lines",
                             line=dict(color=GOLD, width=2.0),
                             hovertemplate="%{y:.3f}<extra>eğim</extra>"), row=2, col=1)
    fig.add_trace(go.Scatter(x=xk, y=ky["ort_fark"], name="Ortalama fark, puan",
                             mode="lines", line=dict(color=CLARET, width=1.8, dash="dot"),
                             hovertemplate="%{y:+.3f} puan<extra>ortalama fark</extra>"),
                  row=2, col=1)
    fig.add_hline(y=1.0, line=dict(color=GRI, width=1, dash="dot"), row=2, col=1)
    # ÜÇÜNCÜ PANEL: dışlama gerekçesinin KENDİSİ. "Outlier" demek yetmez;
    # dışlanan dönemin aylık TÜFE'sinin nasıl salındığı gösterilir ve kalan
    # örneklemin bandıyla yan yana konur.
    t = pd.DataFrame(ip["tablo"])
    if "dislandi" not in t.columns:
        t["dislandi"] = False
    x = pd.to_datetime(t["ay"] + "-01")
    fig.add_trace(go.Bar(
        x=x, y=t["tufe"],
        marker_color=[GRI if dis else TEAL for dis in t["dislandi"]],
        name=("Aylık TÜFE (gri: dışlanan)" if ds.get("n") else "Aylık TÜFE"),
        hovertemplate="%{y:.2f}%<extra>aylık TÜFE</extra>"), row=3, col=1)
    kal = t[~t["dislandi"]]["tufe"]
    if len(kal):
        for v in (float(kal.min()), float(kal.max())):
            fig.add_hline(y=v, line=dict(color=LACI, width=1.2, dash="dash"),
                          row=3, col=1)
    fig.update_yaxes(title_text="aylık %", row=3, col=1)
    fig.update_yaxes(title_text="puan", row=1, col=1)
    fig.update_yaxes(title_text="r / eğim / puan", row=2, col=1)
    for an in fig.layout.annotations:
        an.font.size = 12
        an.font.color = INK
    k = ip["kural"]
    zarar = k.get("takvimli_zarar")
    alt2 = ("Takvim düzeltmesinin örneklem dışı etkisi ölçülemedi" if zarar is None else
            f"Takvim ayı düzeltmesi örneklem DIŞI hatayı {zarar:+.3f} puan "
            f"DEĞİŞTİRİYOR — tablo ikna edici, kural değil".replace(".", ","))
    kal_t = t[~t["dislandi"]]["tufe"]
    if ds.get("n"):
        alt3 = (f"En alt panel: dışlanan dönemde aylık TÜFE "
                f"%{ds.get('tufe_min', 0):.2f}–%{ds.get('tufe_maks', 0):.2f} "
                f"arasında salındı; kestirim örnekleminde "
                f"%{ds.get('kalan_tufe_min', 0):.2f}–%{ds.get('kalan_tufe_maks', 0):.2f} "
                f"(kesikli çizgiler)").replace(".", ",")
    else:
        alt3 = (f"En alt panel: örneklemde aylık TÜFE %{float(kal_t.min()):.2f} ile "
                f"%{float(kal_t.max()):.2f} arasında salındı (kesikli çizgiler) — "
                f"kural ancak bu bantta sınanmıştır").replace(".", ",")
    return _duzen(
        fig, "Takvim ayı, kararlılık ve dışlama kararı",
        [f"Üst panel kestirim örnekleminden; her çubuğun üstündeki n o takvim "
         f"ayındaki gözlem sayısıdır · veri: {damga}",
         alt2, alt3],
        n_panel=n_panel)


def sekil_13(ip, damga):
    """TAHMİN BULUTU — bekleyen ayın TÜFE dağılımı.

    Nokta tahmin okura yanlış bir kesinlik veriyor ve en çok merak edilen
    soruyu hiç cevaplamıyor: TÜFE İTO'nun ÜSTÜNDE gelebilir mi? Bu figür
    dağılımı çizer ve o olasılığı yazar."""
    bk = (ip or {}).get("bekleyen") or {}
    b = bk.get("bulut")
    if not b:
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13,
                        subplot_titles=(
                            f"{bk.get('ad','')} TÜFE tahmin bulutu — İTO %"
                            + f"{b['ito']:.2f}".replace(".", ","),
                            "Geçmişte TÜFE, İTO'nun üstünde geldiği aylar"))
    ad = {"parametrik": "A · regresyon + t (simetri VARSAYAR)",
          "ampirik": "B · regresyon merkezi + ampirik artık",
          "tarihsel": "C · sabit kaydırma + tarihsel farklar"}
    renk = {"parametrik": GRI, "ampirik": TEAL, "tarihsel": GOLD}
    q = b["yuzdelikler"]
    for k in ("parametrik", "ampirik", "tarihsel"):
        v = b[f"y_{k}"]
        # Kutu-benzeri: 5–95 ince çizgi, 25–75 kalın, medyan işaret.
        fig.add_trace(go.Scatter(
            x=[v[0], v[-1]], y=[ad[k], ad[k]], mode="lines",
            line=dict(color=renk[k], width=2), name=f"{ad[k]} · %5–%95",
            hovertemplate="%{x:.2f}%<extra>%5–%95</extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=[v[2], v[4]], y=[ad[k], ad[k]], mode="lines",
            line=dict(color=renk[k], width=9), showlegend=False,
            hovertemplate="%{x:.2f}%<extra>%25–%75</extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=[v[3]], y=[ad[k]], mode="markers", showlegend=False,
            marker=dict(color="white", size=9, line=dict(color=INK, width=2)),
            hovertemplate="medyan %{x:.2f}%<extra></extra>"), row=1, col=1)
    # İTO çizgisi: bulutun sağında kalan kısım "TÜFE İTO'nun üstünde" demek.
    fig.add_vline(x=b["ito"], line=dict(color=CLARET, width=2, dash="dash"),
                  row=1, col=1)
    pu = b.get("p_ustunde") or {}
    fig.add_annotation(
        x=b["ito"], y=1.06, yref="y domain", showarrow=False,
        text=(f"İTO %{b['ito']:.2f} — sağı: TÜFE İTO'nun ÜSTÜNDE "
              f"(P ≈ %{pu.get('ampirik', 0):.0f})").replace(".", ","),
        font=dict(size=10, color=CLARET), xanchor="left", row=1, col=1)
    ua = pd.DataFrame(b.get("ustunde_aylar") or [])
    if len(ua):
        x2 = pd.to_datetime(ua["ay"] + "-01")
        fig.add_trace(go.Bar(x=x2, y=ua["fark"], marker_color=LACI,
                             name="Fark (İTO − TÜFE), eksi aylar",
                             hovertemplate="%{y:+.2f} puan<extra>%{x|%Y-%m}</extra>"),
                      row=2, col=1)
        fig.add_hline(y=0, line=dict(color=GRID, width=1), row=2, col=1)
    fig.update_xaxes(title_text="aylık TÜFE, %", row=1, col=1)
    fig.update_yaxes(title_text="", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    for an in fig.layout.annotations:
        if an.text and "İTO %" not in an.text:
            an.font.size = 12
            an.font.color = INK
    return _duzen(
        fig, "Nokta tahmin değil, bulut",
        [f"Üç kuruluş yan yana: tek kuruluş modelini gizler · n={b['n']} ay · "
         f"veri: {damga}",
         f"P(TÜFE > İTO): parametrik %{pu.get('parametrik', 0):.0f} · "
         f"ampirik %{pu.get('ampirik', 0):.0f} · tarihsel %{pu.get('tarihsel', 0):.0f} — "
         f"parametrik yüksek çıkıyor çünkü simetri varsayıyor, artıklar ise "
         f"sağa çarpık (çarpıklık {b.get('carpiklik', 0):.2f})".replace(".", ","),
         f"Alt panel: örneklemde TÜFE'nin İTO'yu aştığı {b.get('ustunde_n', 0)} ay"],
        n_panel=2)


def kos() -> None:
    a, M, SA, K, D, B, R, o, tani = _yukle()
    # atalet serisini metrik'ten yeniden üret (ozet yalnız son değeri taşır)
    o["atalet_seri"] = {k: v["seri"] for k, v in metrik.atalet_olc(SA).items()}
    damga = o["son_ay_ad"]
    ip = _ito_yukle()
    print(f"Enflasyon — grafikler · veri {damga}")
    ciktilar = [
        (sekil_01(M, o, damga), "01_manset_momentum.html"),
        (sekil_02(M, damga), "02_cekirdek_momentum.html"),
        (sekil_03(a, M, SA, tani, damga), "03_arindirma.html"),
        (sekil_04(K, o, damga), "04_katki.html"),
        (sekil_05(D, M, o, damga), "05_dagilim_difuzyon.html"),
        (sekil_06(M, o, damga), "06_hizmet_mal.html"),
        (sekil_07(a, M, o, damga), "07_beklenti.html"),
        (sekil_08(R, M, o, damga), "08_reel_faiz.html"),
        (sekil_09(a, B, damga), "09_baz_etkisi.html"),
    ]
    # İTO KANADI KOŞULLU: İTO serisi EVDS'te Ocak 2024'te başlıyor ve tek bir
    # dış seriye bağlı. Onu zorunlu figür saymak, seri bir gün gelmediğinde
    # çalışan dokuz figürü de birlikte düşürürdü — orantısız bir sigorta.
    # Ama "atla ve geç" de olmaz: eski HTML yerinde kalır, sayfa taze metinle
    # bayat grafiği yan yana basar. Doğrusu üçüncü yol: profil yoksa figürler
    # üretilmez VE eski kopyaları SİLİNİR, uyarı düşer, hat devam eder.
    ITO_CIKTI = ["10_ito_tufe.html", "11_ito_kural.html", "12_ito_takvim.html",
                 "13_ito_bulut.html"]
    if ip:
        ciktilar += [
            (sekil_10(ip, damga), ITO_CIKTI[0]),
            (sekil_11(ip, damga), ITO_CIKTI[1]),
            (sekil_12(ip, damga), ITO_CIKTI[2]),
            (sekil_13(ip, damga), ITO_CIKTI[3]),
        ]
    else:
        print("  ! İTO profili yok (data/ito_profil.json) — İTO figürleri "
              "üretilmedi ve eski kopyaları SİLİNİYOR (bayat grafik yayımlanmasın).")
        # Üretim klasörü VE sitedeki kopya: kopyalama adımı yalnız yazar,
        # silmez. Yalnız birini temizlemek bayat dosyayı sitede bırakırdı.
        for ad in ITO_CIKTI:
            (CIKTI / ad).unlink(missing_ok=True)
            (veri.KOK / "site/public/projeler/enflasyon" / ad).unlink(missing_ok=True)
    n = 0
    for fig, ad in ciktilar:
        if fig is None:
            print(f"  ATLANDI: {ad} — girdisi üretilemedi (uyarilar.json'a bakın)")
            continue
        _yaz(fig, ad)
        n += 1
    # MDX'teki yukseklik={} ile bu dosya AYNI kaynaktan beslenir: figürün
    # gerçek tasarım yüksekliği burada kayıt altına alınır.
    (CIKTI / "yukseklikler.json").write_text(json.dumps(
        {ad: int(fig.layout.height) for fig, ad in ciktilar if fig is not None},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {n}/{len(ciktilar)} grafik yazıldı → {CIKTI}")
    # SESSİZ BAYATLAMA YASAK: bir figür üretilemediyse eskisi site/public'te
    # yerinde kalır ve sayfanın geri kalanı tazelenir — grafik bayat, metin taze.
    # Bu yüzden eksikte hat DURUR (guncelle.py kopyalamaya geçmez, cron kırmızı).
    if n < len(ciktilar):
        eksik = [ad for fig, ad in ciktilar if fig is None]
        raise SystemExit(
            f"DUR: {len(eksik)} figür üretilemedi ({', '.join(eksik)}). "
            "Siteye kopyalama YAPILMAZ — eski grafikle taze metin yayımlanmasın. "
            "Nedeni için uyarilar.json'a bakın.")


if __name__ == "__main__":
    kos()
