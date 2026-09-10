# -*- coding: utf-8 -*-
"""TCMB fonlama & likidite — grafik katmanı (Plotly, site ev stili).

Kurallar (site sözleşmesi):
  · Çok panelli figürlerde paneller ALT ALTA (rows=N, cols=1). YAN YANA PANEL YOK.
  · Panel başına ~340 px + başlık/lejant payı; buradaki `height` MDX'teki
    `yukseklik={}` ile AYNI olmak zorunda (cikti/yukseklikler.json tek kaynak).
  · Başlık solda, iki satır: "<b>Başlık</b><br><sup>alt başlık</sup>".
  · Lejant altta yatay, beyaz zemin, include_plotlyjs="cdn",
    config: responsive=True, displaylogo=False.
  · Şekil numarası BELGE SIRASINI izler; dosya adı = şekil no (NN_ad.html).
  · Her figürün başlığında VERİ TARİHİ vardır (bayat grafik gözle görülür).
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
# Pencere sabitleri ve ŞEKİL SAATLERİ veri.py'de, tek yerde durur: figürün
# alt yazısındaki tarihi burası, sayfadaki damgayı ozet_uret.py aynı
# fonksiyondan okur.
from veri import (VERI, GEC_BAS, SWAP_BAS, TAM_BAS, YAKIN_BAS, ZK_BAS, gun_ad)

CIKTI = veri.PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)

# Ev stili jetonları — site/tools/plotly_stil.py ve diğer hatlarla aynı
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
LACI, MOR, YESIL, GRI = "#2f4b7c", "#665191", "#7a9e7e", "#8a8a8a"
PALET = [TEAL, CLARET, GOLD, LACI, MOR, "#a05195", YESIL, GRI]
BANT = "rgba(154,115,39,0.13)"        # faiz koridoru dolgusu
OLAY = "rgba(142,31,47,0.10)"          # örtük sıkılaştırma dönemi gölgesi

PANEL_PX = 340
LEJANT_SATIR_PX = 22

# Pencereler veri.py'den gelir; panel başlıklarındaki yıllar o sabitlerden
# TÜRETİLİR — sabit değişince başlık da değişsin, sessizce yanlışa dönmesin.


def _yil(t: str) -> int:
    return int(str(t)[:4])


# --------------------------------------------------------------------------- düzen
SATIR_SINIR = 150     # başlık bloğunda bir <sup> satırına sığan yaklaşık karakter


def _sayi(x, ondalik: int = 0) -> str:
    """Türkçe sayı biçimi: binlik ayracı nokta, ondalık ayracı virgül.

    Metin içinde `f"{x:,.0f}".replace(",", ".")` yazmak cümlenin KENDİ
    noktalarını da bozuyordu; dönüşüm tek yerde ve yalnız sayıya uygulanır.
    """
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _bol(metin: str, sinir: int = SATIR_SINIR) -> list[str]:
    """Uzun alt başlık satırını KELİME sınırından böler.

    Plotly başlık satırını sarmaz; sınırı aşan satır figürün sağından taşar.
    Elle saymak yerine burada bölünür — metin düzenlendiğinde taşma sessizce
    geri gelmesin.
    """
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
    çalışma zamanında `legend.y = −0,1` ve `margin.b = 110` dayatıyor; Plotly
    figürden taşacak lejantı figürün ALT KENARINA yapıştırıyor. Sabit konumlu
    bir dipnot uzun figürlerde lejantın üstüne biner. Bu yüzden açıklama
    satırları BAŞLIK bloğunda (<sup>) taşınır — ev stili başlıktaki her <br>
    için üst marjı 26 px büyütür, çakışma imkânsızdır.
    """
    # Satırlar burada bölünür; figür yüksekliği bölünmüş satır SAYISINDAN
    # hesaplanır ve cikti/yukseklikler.json'a o değer yazılır — MDX'teki
    # yukseklik={} ile aynı kaynaktan beslenir.
    alt = [parca for satir in alt for parca in _bol(satir)]
    l_satir = _lejant_satir(fig)
    # ÜST MARJ İNCE AYARI: plotly_stil.py margin.t'yi önce koşulsuz 92'ye çeker,
    # sonra YALNIZCA mevcut değer gerekenden KÜÇÜKSE yükseltir. Doğru değeri
    # buraya yazmak ters teper; bir eksik yazılır, ev stili kendi hesabına
    # tamamlar.
    ust = 92 + 26 * len(alt) + 25
    b = 110 + max(0, l_satir - 1) * 24
    h = PANEL_PX * n_panel + ust + b + ek_yukseklik
    metin = f"<b>{baslik}</b>" + "".join(f"<br><sup>{x}</sup>" for x in alt)
    # Üste çivilenmiş başlık, ev stilinin dayattığı üst marjın (gerekenT)
    # tepesine yapışınca altında büyük bir boşluk kalıyor. Blok, ölçülmüş
    # satır yüksekliğine göre marjın İÇİNE ortalanır: üstten dolgu =
    # (marj − blok yüksekliği) / 2. Ortalama, çakışmayı geri getirmez çünkü
    # blok yüksekliği marjın yarısından küçük.
    gereken_t = 92 + 26 * len(alt) + 26          # plotly_stil.py'nin hesabı
    blok_px = 22 + 19 * len(alt)                 # ölçüldü: satır ~18,5 px
    dolgu_t = int(max(12, (gereken_t - blok_px) / 2))
    fig.update_layout(
        # BAŞLIK ÜSTE ÇİVİLENİR. Plotly'nin varsayılanı başlık bloğunu üst
        # marjın İÇİNDE DİKEY ORTALAR; alt başlık 7–8 satıra çıktığında blok
        # aşağı kayıp ilk panelin başlığına biniyor (ölçüldü: 4 panelli ZK
        # figüründe başlık 149–315 px, panel başlığı 310 px). y=1 + yanchor
        # "top" ile blok kabın tepesinden başlar; üst marjın fazlası boşluk
        # olarak altta kalır, çakışma imkânsızdır.
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


def _cipa(damga: str | None) -> str:
    """Alt yazıdaki " · Çıpa: <gün>" eki — damga ÖLÇÜLEMEMİŞSE hiç yazılmaz.

    Bir figürün panelleri farklı günlerde bitiyorsa tek bir çıpa hangi bacağı
    seçse öbürü hakkında yalan olur; o zaman tarih figürün alt yazısında
    ÇIKMAZ, her panel kendi gününü kendi başlığında taşır.
    """
    return f" · Çıpa: {damga}" if damga else ""


def _panel_veri(damga: str | None, etiket: str = "veri") -> str:
    """Panel başlığındaki " — veri <gün>" eki; ölçülemeyen panelde hiç yazılmaz.

    Figürün panelleri farklı günlerde bitiyorsa okurun hangi panele hangi güne
    kadar baktığı panelin ÜSTÜNDE yazar; tek bir figür çıpası bunu anlatamaz.
    """
    return f" · {etiket} {damga}" if damga else ""


def _kuyruk_kes(df: pd.DataFrame, uc) -> pd.DataFrame:
    """Kareyi kendi ucunda bitir — SAĞ uçtaki ölçülemeyen kuyruk çizilmez.

    `_pencere` yalnız SOL sınır koyar; kare her zaman M'nin indeksi kadar
    uzundur ve o indeks en hızlı bacağın (kur) günlerini taşır. Yavaş bir
    bacağın kuyruğu bu yüzden boş kalır: çizgi izinde zararsız (boşluk
    çizilmez) ama YIĞILI alanda ölümcül — plotly boşluğu sıfır sayar ve okur
    kalemin gerçekten sıfırlandığını sanır.
    """
    if uc is None or df.empty:
        return df
    return df.loc[df.index <= pd.Timestamp(uc)]


def _panel_gun(uc, damga: str | None) -> str:
    """Panel başlığına " · veri <gün>" — YALNIZ panel figürün damgasından
    ayrıldığında.

    Sağlıklı günde üç panel de aynı günde biter ve başlıklar bugünkü hâliyle
    kalır; bir bacak geride kaldığında okur hangi panelin nereye kadar
    çizildiğini panelin ÜSTÜNDE görür. Tek figür çıpası bunu anlatamaz: çıpa
    en eski bacaktır ve ondan ileri giden paneli olduğundan eski gösterir.
    """
    if uc is None:
        return ""
    ad = gun_ad(pd.Timestamp(uc))
    return "" if (damga and ad == damga) else _panel_veri(ad)


def _cizili_uc(fig) -> pd.Timestamp | None:
    """Figürün gerçekten ÇİZDİĞİ uç: her izin son dolu gözlemi, en eskisi.

    veri.sekil_saatleri kolon ADIYLA ölçüyor, bu fonksiyon FİGÜRÜN KENDİSİNİ
    ölçüyor; ikisi ayrışırsa figüre bir iz eklenmiş ve saat listesi
    güncellenmemiş demektir. Kusur göze çarpmaz — damga bir gün kayar ve
    koşu yeşil biter — bu yüzden kos() ayrışmada DURUR.
    """
    uclar = []
    for tr in fig.data:
        x, y = getattr(tr, "x", None), getattr(tr, "y", None)
        if x is None or y is None:
            continue
        try:
            xa = np.asarray(x)
            ya = np.asarray(y, dtype="float64")
        except (TypeError, ValueError):
            continue
        n = min(len(xa), len(ya))
        if n == 0:
            continue
        dolu = np.flatnonzero(np.isfinite(ya[:n]))
        if not len(dolu):
            continue
        try:
            uclar.append(pd.Timestamp(xa[dolu[-1]]))
        except (TypeError, ValueError):
            continue
    return min(uclar) if uclar else None


def _uc_denetimi(ad: str, beyan_t, beyan: str | None, fig) -> None:
    """İlan edilen uç ile figürün çizdiği uç TEK YÖNLÜ karşılaştırılır.

    DAMGANIN TAŞIDIĞI GÜVENCE: bir damga BAYAT BACAĞI TAZE GÖSTEREMEZ. Yani
    ilan edilen uç, figürün en eski izinin ucundan İLERİ olamaz; olursa okur
    ölçülmemiş bir günü ölçülmüş sanır ve hat DURUR — bir figüre iz eklenip
    saat listesi güncellenmediğinde tam olarak bu olur, ve kapı bunun için
    yazılmıştı.

    TERS YÖN KUSUR DEĞİLDİR: ilan edilen uç çizilenden GERİDE ise damga
    tutucudur — okura yalan söylemez, yalnız kendini olduğundan eski gösterir.
    Eskiden burada EŞİTLİK aranıyordu ve ölçüt kuralın kendi MEŞRU çıktısını
    kusur sayıyordu: bir APİ alt kalemi bir gün geride kalınca `_uc` damgayı
    doğru biçimde geri çekiyor, `fillna(0)` ile çizilen iz ise geri gitmiyor,
    kapı farkı "kolon listesi ayrışmış" diye okuyup HATTIN TAMAMINI
    durduruyordu (ölçüldü 10.09.2026: on kalemin ALTISI tek başına düşürüyor;
    Şekil 03-08 hiç yazılmıyor, siteye kopyalama olmuyor). Yayının önünde
    duran bir denetimin yanlış alarmı arızanın kendisidir — üstelik ekrandaki
    teşhis de yanlış olduğu için sonraki oturum kolon listesi arardı.

    AYRI FONKSİYON, çünkü ağa çıkan `kos()`un İÇİNDE duran bir kapı hiçbir
    sınama tarafından koşturulamaz: duman bunu kuralın ilan ettiği dört hâlle
    doğrudan çağırır.
    """
    cizili = _cizili_uc(fig)
    if beyan_t is None or cizili is None:
        return
    beyan_t = pd.Timestamp(beyan_t)
    if beyan_t > cizili:
        raise SystemExit(
            f"DUR: {ad} için ilan edilen uç ({beyan}) figürün en eski izinin "
            f"ucundan ({gun_ad(cizili)}) İLERİDE. Damga, o figürde ölçülmemiş "
            "bir günü ilan eder — saat listesi figürün izleriyle ayrışmış.")
    if beyan_t < cizili:
        print(f"    not: {ad} — damga {beyan}, figürün en eski izi "
              f"{gun_ad(cizili)} tarihinde bitiyor; damga tutucu "
              "(ilan, çizilenden geride).")


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


def _iz(fig, x, y, ad, renk, satir, kalin=1.8, kes=None, dolgu=None,
        grup=None, goster=True, opacity=1.0):
    fig.add_trace(go.Scatter(
        x=x, y=y, name=ad, mode="lines", legendgroup=grup or ad,
        showlegend=goster, opacity=opacity,
        line=dict(color=renk, width=kalin, dash=kes),
        fill=dolgu, fillcolor=BANT if dolgu else None),
        row=satir, col=1)


def _olay_gomle(fig, donemler: list[dict], satir: int, n_panel: int):
    """Örtük sıkılaştırma dönemlerini panel arkasına gölge olarak yaz."""
    for d in donemler:
        fig.add_vrect(x0=d["bas"], x1=d["son"], fillcolor=OLAY,
                      line_width=0, layer="below", row=satir, col=1)


def _pencere(df: pd.DataFrame, bas: str) -> pd.DataFrame:
    """Pencere sabitleri SUNUM tercihidir, ölçüm değil — ama serinin gerçek
    başlangıcının gerisine düşmemeleri gerekir; düşerlerse eksen boş bir
    kuyruk çizer ve okur 'veri var ama sıfır' sanır."""
    if df.empty:
        return df
    bas_t = max(pd.Timestamp(bas), df.index[0])
    return df.loc[df.index >= bas_t]


# ===========================================================================
# ŞEKİL 01 — Politika faizi · AOFM · TLREF üçlüsü ve koridor bandı (ANA)
# ===========================================================================
def sekil_01(M, o, damga):
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.11,
        subplot_titles=(
            f"a) Yakın dönem ({_yil(YAKIN_BAS)}–bugün): koridor, politika faizi, "
            "fiilî TCMB faizi ve TLREF",
            f"b) Tam tarihçe ({_yil(TAM_BAS)}–bugün): koridor, AOFM ve geç "
            "likidite penceresi"))

    y = _pencere(M, YAKIN_BAS)
    # Koridor bandı: alt bandı görünmez iz, üst bandı ona doldurulur.
    _iz(fig, y.index, y["koridor_alt"], "Koridor alt bandı (O/N borç alma)",
        GOLD, 1, kalin=1.0, kes="dot", grup="koridor")
    fig.add_trace(go.Scatter(
        x=y.index, y=y["koridor_ust"], name="Faiz koridoru",
        mode="lines", line=dict(color=GOLD, width=1.0, dash="dot"),
        fill="tonexty", fillcolor=BANT, legendgroup="koridor",
        showlegend=True), row=1, col=1)
    _iz(fig, y.index, y["politika"], "Politika faizi (1 hafta repo kotasyonu)",
        INK, 1, kalin=2.2)
    _iz(fig, y.index, y["aofm"], "AOFM — ağırlıklı ort. fonlama maliyeti",
        CLARET, 1, kalin=2.0)
    _iz(fig, y.index, y["aosm"], "AOSM — ağırlıklı ort. sterilizasyon maliyeti "
        "(türetme)", TEAL, 1, kalin=1.6, kes="dash")
    _iz(fig, y.index, y["tlref"], "TLREF (piyasa gecelik)", LACI, 1, kalin=1.6)

    t = _pencere(M, TAM_BAS)
    _iz(fig, t.index, t["koridor_alt"], "Koridor alt bandı (O/N borç alma)",
        GOLD, 2, kalin=1.0, kes="dot", grup="koridor", goster=False)
    fig.add_trace(go.Scatter(
        x=t.index, y=t["koridor_ust"], name="Faiz koridoru", mode="lines",
        line=dict(color=GOLD, width=1.0, dash="dot"), fill="tonexty",
        fillcolor=BANT, legendgroup="koridor", showlegend=False), row=2, col=1)
    _iz(fig, t.index, t["glp_satis"], "Geç likidite penceresi (borç verme)",
        MOR, 2, kalin=1.2, kes="dashdot")
    _iz(fig, t.index, t["aofm_ham"], "AOFM (ham, tabansız günler dahil)",
        GRI, 2, kalin=1.0, opacity=0.55)
    _iz(fig, t.index, t["aofm"], "AOFM — ağırlıklı ort. fonlama maliyeti",
        CLARET, 2, kalin=1.8, goster=False, grup="AOFM — ağırlıklı ort. fonlama maliyeti")
    _iz(fig, t.index, t["politika"], "Politika faizi (1 hafta repo kotasyonu)",
        INK, 2, kalin=1.8, goster=False,
        grup="Politika faizi (1 hafta repo kotasyonu)")
    _olay_gomle(fig, o.get("donemler", []), 2, 2)

    pol_bas = M["politika"].dropna()
    pol_bas = pol_bas.index[0] if len(pol_bas) else None
    alt = [
        f"Veri: TCMB EVDS3 · iş günü{_cipa(damga)}. Politika faizi = 1 hafta "
        "vadeli repo SATIŞ kotasyonu (TP.PY.P02.1H); koridor = O/N borç alma "
        "(TP.PY.P01.ON) – O/N borç verme (TP.PY.P02.ON).",
        "AOFM (TP.APIFON4) fonlama bacağının tutar-ağırlıklı faizidir; fonlama "
        f"tabanı {_sayi(o['rejim']['taban_esik_mn_tl'])} mn TL'nin altına düşen "
        "günlerde tanımsızdır ve çizilmez.",
        "AOSM bu çalışmanın türetmesidir, TCMB serisi değildir. Alt paneldeki "
        "kırmızı gölgeler AOFM'nin koridorun üstüne çıktığı dönemlerdir.",
        ("AOFM bir STOK ortalamasıdır: faiz KARARI haftalarında eski, ucuz "
         "fonlama stokta durduğu için AOFM koridorun TABANININ altına da "
         "düşebilir. Bu mekanik gecikmedir, 'örtük gevşeme' değildir; "
         + (f"ölçülen: {len(o.get('donemler_alti') or [])} ayrı dönem, "
            f"toplam {sum(d['gun'] for d in (o.get('donemler_alti') or []))} "
            "iş günü."
            if (o.get("donemler_alti") or []) else
            "bu tarihçede böyle bir dönem ölçülmedi.")),
    ]
    if pol_bas is not None:
        alt.append(f"Politika faizi kotasyonu EVDS'te {pol_bas:%d.%m.%Y} "
                   "tarihinde başlıyor; öncesinde haftalık repo ihaleyle "
                   "fonlanıyordu ve bu vadede kotasyon yayımlanmıyordu.")
    _duzen(fig, "Faiz koridoru, politika faizi ve fiilî TCMB faizi", alt, 2,
           y_baslik="%")
    return fig


# ===========================================================================
# ŞEKİL 02 — Spreadler
# ===========================================================================
def sekil_02(M, o, damga):
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "a) TLREF − politika faizi (puan)",
                            "b) Fiilî TCMB faizi − politika faizi (puan)",
                            "c) TLREF − AOFM: piyasa TCMB'den pahalıya mı "
                            "borçlanıyor? (puan)"))
    y = _pencere(M, YAKIN_BAS)
    for satir, (kol, ad, renk) in enumerate(
            [("spread_tlref_politika", "TLREF − politika faizi", LACI)], start=1):
        _iz(fig, y.index, y[kol], ad, renk, satir)
    _iz(fig, y.index, y["spread_aofm_politika"], "AOFM − politika faizi",
        CLARET, 2)
    _iz(fig, y.index, y["spread_marjinal_politika"],
        "Marjinal TCMB faizi − politika faizi", TEAL, 2, kes="dash")
    _iz(fig, y.index, y["spread_tlref_aofm"], "TLREF − AOFM", MOR, 3)
    for s in (1, 2, 3):
        fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=s, col=1)

    r = o["rejim"]
    ort_neg = M.loc[M["net_fonlama"] < 0, "spread_tlref_aofm"].dropna()
    ort_poz = M.loc[M["net_fonlama"] > 0, "spread_tlref_aofm"].dropna()
    alt = [
        f"Veri: TCMB EVDS3 · iş günü{_cipa(damga)}. Pencere "
        f"{_yil(YAKIN_BAS)}–bugün.",
        "Marjinal TCMB faizi: sistem net BORÇLUYSA fonlamanın fiyatı (AOFM), "
        "net ALACAKLIYSA sterilizasyonun fiyatı (AOSM). Son bir yılda "
        f"{r['net_negatif_gun']}/{r['pencere_gun']} iş gününde sistem net "
        "alacaklıydı.",
        ("TLREF − AOFM: tüm tarihçede net fonlama pozitifken ortalama "
         f"{ort_poz.mean():+.3f} puan (n={len(ort_poz)}), negatifken "
         f"{ort_neg.mean():+.3f} puan (n={len(ort_neg)}). Belirgin pozitif "
         "sıçramalar tekil OLAYDIR, rejim değil."),
        ("Üç makasın son dolu günü AYNI OLMAYABİLİR: AOFM tabansız günlerde "
         "tanımsız olduğu için AOFM'li makaslar TLREF'li makastan geride "
         "kalabilir. Bu yüzden makaslar birbirinden çıkarılarak okunmaz; "
         "her makasın kendi tarihi ve son ORTAK güne çıpalı sürümleri sayfa "
         "metninde ayrıca verilir."),
    ]
    _duzen(fig, "Politika faizi ile piyasa ve fiilî fonlama faizi arasındaki "
                "makaslar", alt, 3, y_baslik="puan")
    return fig


# ===========================================================================
# ŞEKİL 03 — Net APİ fonlaması (stok) ve kompozisyonu
# ===========================================================================
def sekil_03(M, o, damga):
    # ÜÇ PANEL, ÜÇ UÇ. Yığılı bir kompozisyon ancak BÜTÜN kalemlerinin
    # ölçüldüğü güne kadar çizilebilir: eksik kalemi sıfır basmak okura "bu
    # kanal bugün hiç kullanılmadı" der ve toplamı olduğundan küçük gösterir.
    # Uçlar veri katmanının TEK fonksiyonundan gelir (`api_panel_uclari`);
    # figürün damgası da onların en eskisi, yani kesim ile damga ayrışamaz.
    uc = veri.api_panel_uclari(M)
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "a) TCMB net fonlaması (A − B): işaret rejimi "
                            "belirler" + _panel_gun(uc["net"], damga),
                            "b) Fonlama bacağı (A) — yığılı, milyar TL"
                            + _panel_gun(uc["fon"], damga),
                            "c) Sterilizasyon bacağı (B) — yığılı, milyar TL"
                            + _panel_gun(uc["ste"], damga)))
    y = _pencere(M, YAKIN_BAS)
    net = _kuyruk_kes(y, uc["net"])["net_fonlama"] / 1000.0   # mn TL → mlr TL
    fig.add_trace(go.Scatter(
        x=net.index, y=net, name="Net fonlama (A − B)", mode="lines",
        line=dict(color=CLARET, width=1.8), fill="tozeroy",
        fillcolor="rgba(142,31,47,0.10)"), row=1, col=1)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    fon = [("fon_ihale", "A1 · ihale yoluyla fonlama", TEAL),
           ("fon_kot_repo", "A2a · BİST O/N, kotasyon ve PY repo", LACI),
           ("fon_kot_depo", "A2b · TL depo", GOLD),
           ("fon_glp", "A2c · geç likidite penceresi", MOR),
           ("fon_kot_diger", "A · diğer/artık", GRI)]
    yf = _kuyruk_kes(y, uc["fon"])
    for kol, ad, renk in fon:
        if kol not in yf.columns:
            continue
        # fillna(0) yalnız İÇERİDEKİ boşluk için: yığılı alanda ortada bir
        # boşluk yığını kırar. KUYRUK yukarıda kesildi — sağ uçtaki boşluk
        # "kanal kullanılmadı" değil "ölçülemedi" demektir.
        s = (yf[kol].fillna(0) / 1000.0)
        if s.abs().max() < 1e-9:
            continue
        fig.add_trace(go.Scatter(
            x=yf.index, y=s, name=ad, mode="lines", stackgroup="fon",
            line=dict(color=renk, width=0.6), fillcolor=renk, opacity=0.75),
            row=2, col=1)
    ste = [("ste_ihale", "B1 · ihale yoluyla sterilizasyon", TEAL),
           ("ste_kot", "B2 · kotasyon yoluyla sterilizasyon", GOLD),
           ("ste_liksen", "B3 · likidite senedi", MOR),
           ("ste_diger", "B · diğer/artık", GRI)]
    ys = _kuyruk_kes(y, uc["ste"])
    for kol, ad, renk in ste:
        if kol not in ys.columns:
            continue
        s = (ys[kol].fillna(0) / 1000.0)
        if s.abs().max() < 1e-9:
            continue
        fig.add_trace(go.Scatter(
            x=ys.index, y=s, name=ad, mode="lines", stackgroup="ste",
            line=dict(color=renk, width=0.6), fillcolor=renk, opacity=0.75),
            row=3, col=1)

    r = o["rejim"]
    liksen = M["ste_liksen"].dropna()
    lik_bas = f"{liksen.index[0]:%d.%m.%Y}" if len(liksen) else "—"
    alt = [
        f"Veri: TCMB EVDS3 · bie_apifon · iş günü{_cipa(damga)}. EVDS birimi "
        "milyon TL; grafikte milyar TL'ye çevrildi. Pencere "
        f"{_yil(YAKIN_BAS)}–bugün.",
        "Net fonlama POZİTİF: sistem TCMB'ye net borçlu, TL likiditesi açık. "
        "NEGATİF: sistem net alacaklı, TL likiditesi fazla ve marjinal fiyatı "
        "sterilizasyon belirliyor.",
        (f"Son bir yılda {r['net_negatif_gun']}/{r['pencere_gun']} iş günü "
         f"negatif, {r['fonlama_sifir_gun']} iş gününde fonlama tam sıfır. "
         f"Likidite senedi kalemi {lik_bas} tarihinde doğdu — rejim "
         "değişikliğinin çıpası."),
    ]
    _duzen(fig, "TCMB net açık piyasa fonlaması ve kompozisyonu", alt, 3,
           y_baslik="milyar TL")
    return fig


# ===========================================================================
# ŞEKİL 04 — Swap stokunun fonlamadaki payı
# ===========================================================================
def sekil_04(M, o, damga):
    if "swap_alim_usd" not in M.columns:
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11,
                        subplot_titles=(
                            "a) TCMB taraflı swap stoku — kanal kırılımı "
                            "(milyar ABD doları)",
                            "b) Swap ile sağlanan TL ve APİ fonlaması "
                            "(milyar TL)"))
    y = _pencere(M, SWAP_BAS)
    kanal = [("swap_tcmb_piy", "TCMB döviz karşılığı TL swap piyasası", TEAL),
             ("swap_bist", "BİST swap piyasası", LACI),
             ("swap_gelenek", "Geleneksel swap ihaleleri (alım yönlü)", GOLD),
             ("swap_miktar", "Miktar ihaleleri", MOR),
             ("swap_altin_piy", "Altın swap piyasası", YESIL)]
    for kol, ad, renk in kanal:
        if kol in y.columns and y[kol].abs().max() > 1e-9:
            _iz(fig, y.index, y[kol] / 1000.0, ad, renk, 1, kalin=1.2)
    _iz(fig, y.index, y["swap_alim_usd"] / 1000.0,
        "Toplam stok — alım yönlü", CLARET, 1, kalin=2.2)
    _iz(fig, y.index, y["swap_satim_usd"] / 1000.0,
        "Toplam stok — satım yönlü", INK, 1, kalin=1.6, kes="dash")

    _iz(fig, y.index, y["swap_alim_tl"] / 1000.0,
        "Swap ile SAĞLANAN TL (alım yönlü stok × kur)", TEAL, 2, kalin=1.8)
    if "swap_satim_tl" in y.columns and y["swap_satim_tl"].abs().max() > 1e-9:
        _iz(fig, y.index, -y["swap_satim_tl"] / 1000.0,
            "Swap ile ÇEKİLEN TL (satım yönlü stok × kur, eksi)", MOR, 2,
            kalin=1.4, kes="dot")
    _iz(fig, y.index, y["fon_top"] / 1000.0, "APİ fonlaması (A)", CLARET, 2,
        kalin=1.6)
    _iz(fig, y.index, y["tcmb_tl_saglama"] / 1000.0,
        "Net APİ + swap (alım − satım) = TCMB kaynaklı net TL", LACI, 2,
        kalin=1.6, kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)

    b = o["bayrak"]
    son_alim = float(M["swap_alim_usd"].dropna().iloc[-1])
    son_satim = float(M["swap_satim_usd"].dropna().iloc[-1])
    alt = [
        f"Veri: TCMB EVDS3 · bie_swaptektarf · iş günü{_cipa(damga)}. EVDS "
        "birimi milyon ABD doları; TL karşılığı için TP.DK.USD.A.YTL "
        f"kullanıldı. Pencere {_yil(SWAP_BAS)}–bugün.",
        "Swap, fonlamanın bilanço DIŞI bacağıdır ve İKİ YÖNLÜDÜR: alım yönlü "
        "swapta TCMB döviz alıp TL verir, satım yönlüsünde döviz satıp TL "
        "çeker. Toplam ölçü (b panelindeki kesikli çizgi) iki bacağın "
        "FARKIDIR; tek bacak alınırsa satım stoku büyürken sağlanan TL sabit "
        "görünür.",
        (f"Çıpa günü alım yönlü stok {_sayi(son_alim)} mn USD, satım yönlü "
         f"{_sayi(son_satim)} mn USD "
         f"(≈ {_sayi(float(M['swap_satim_tl'].dropna().iloc[-1]) / 1000.0)} "
         "milyar TL'lik TL çekilmesi)."
         + ("  Alım yönlü kanal KAPALI: 'swap ile TL sağlanıyor' cümlesi bu "
            "koşuda kurulmuyor — seri taze, olgu yok."
            if not b["swap_alim_aktif"] else "")),
    ]
    _duzen(fig, "Swap stokunun TCMB fonlamasındaki yeri", alt, 2)
    fig.update_yaxes(title_text="milyar USD", row=1, col=1)
    fig.update_yaxes(title_text="milyar TL", row=2, col=1)
    return fig


# ===========================================================================
# ŞEKİL 05 — Zorunlu karşılıklar ve sistem likiditesi
# ===========================================================================
def sekil_05(M, Z, o, panel_saat: dict):
    """Bu figürün TEK saati yok: dört panel, dört gün.

    Bloke hesap ile ima edilen oran analitik bilançonun gününde, tesis adımları
    son ADIM gününde, sistem likiditesi gün başı likidite tablosunun gününde
    biter — ve o tablo daha erken yayımlandığı için ötekilerin İLERİSİNDE
    durur. Tek çıpa hangi bacağı seçse öbürü hakkında yalan olurdu; alt yazıda
    tarih ÇIKMAZ, her panel kendi gününü kendi başlığında taşır.
    """
    if Z is None or Z.empty:
        return None
    # Panel (a)'da iki büyüklük ~14 kat farklı (bloke hesap ~1,1 trilyon TL,
    # taban ~16 trilyon TL). Tek eksende bloke hesap sıfır çizgisine yapışıyor
    # ve "ZK yok" gibi okunuyordu; taban İKİNCİ eksende çizilir ve ikisinin
    # oranı zaten (b) panelinde ayrıca duruyor.
    fig = make_subplots(rows=4, cols=1, vertical_spacing=0.065,
                        specs=[[{"secondary_y": True}], [{}], [{}], [{}]],
                        subplot_titles=(
                            "a) ZK bloke hesabı ve ZK'ya tabi taban "
                            f"(milyar TL){_panel_veri(panel_saat['bloke'])}",
                            "b) İma edilen efektif tesis oranı (%) — TCMB'nin "
                            "ilan ettiği oran DEĞİLDİR"
                            f"{_panel_veri(panel_saat['oran'])}",
                            "c) Tesis dönemi adımları (milyar TL) — seri bir "
                            "basamak fonksiyonudur"
                            f"{_panel_veri(panel_saat['adim'], 'son adım')}",
                            "d) Bankalar serbest mevduatı ve gün başı toplam "
                            "likidite (milyar TL)"
                            f"{_panel_veri(panel_saat['likidite'])}"))
    # ZK panelinin başlangıcı SABİT DEĞİL: bloke hesap ayrı kalem olarak
    # yayımlanmaya başladığı günden birkaç ay önce başlar. Sabit tarih yazmak,
    # kalem tarihi değiştiğinde paneli sessizce boş bir yıla açardı.
    bloke_bas = (o.get("zk") or {}).get("bloke_bas")
    zk_bas = (max(pd.Timestamp(ZK_BAS), pd.Timestamp(bloke_bas)
                  - pd.Timedelta(days=90)) if bloke_bas
              else pd.Timestamp(ZK_BAS))
    z = _pencere(Z, zk_bas)
    _iz(fig, z.index, z["zk_bloke"] / 1000.0, "ZK bloke hesabı (TP.AB.A19)",
        CLARET, 1, kalin=1.8)
    if "zk_taban" in z.columns:
        fig.add_trace(go.Scatter(
            x=z.index, y=z["zk_taban"] / 1000.0, mode="lines",
            name="ZK'ya tabi taban (TL mevduat + DTH'nin TL karşılığı) — sağ eksen",
            line=dict(color=TEAL, width=1.4, dash="dash")),
            row=1, col=1, secondary_y=True)
        _iz(fig, z.index, z["zk_oran"], "İma edilen efektif tesis oranı", GOLD,
            2, kalin=1.8)

    d = z["zk_bloke"].diff()
    adim = d[d.abs() > 1e-6]
    fig.add_trace(go.Bar(
        x=adim.index, y=adim / 1000.0, name="Tesis dönemi değişimi",
        marker=dict(color=[CLARET if v < 0 else TEAL for v in adim],
                    line=dict(width=0)), opacity=0.85), row=3, col=1)
    fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=3, col=1)

    m = _pencere(M, zk_bas)
    _iz(fig, m.index, m["serbest_mevduat"] / 1000.0,
        "Bankalar serbest mevduatı (TP.PPIBSM)", LACI, 4, kalin=1.6)
    _iz(fig, m.index, m["gun_basi_likidite"] / 1000.0,
        "Gün başı toplam likidite (TP.PPIGBTL)", MOR, 4, kalin=1.4, kes="dash")

    zk = o.get("zk", {})
    ort_gun = zk.get("adim_ortalama_gun")
    alt = [
        f"Veri: TCMB EVDS3 · iş günü (bloke hesap, likidite) + haftalık "
        f"(taban). Pencere {zk_bas:%m.%Y}–bugün.",
        ("DÖRT PANELİN DÖRT AYRI GÜNÜ VAR: her panelin son gözlem günü kendi "
         "başlığında yazılıdır. Gün başı likidite tablosu (d) daha erken "
         "yayımlandığı için İLERİDE, tesis adımları (c) basamak fonksiyonu "
         "olduğu için GERİDE durur — (c)'nin durması eksiklik değil, veridir."),
        (f"ZK bloke hesabı (TP.AB.A19) analitik bilançoda AYRI KALEM olarak "
         f"{pd.Timestamp(bloke_bas):%d.%m.%Y} tarihinde doğdu; öncesinde "
         "bankalar mevduatı bloke/serbest diye ayrılmıyordu ve seri tam sıfır "
         "basıyordu. O sıfırlar veri sayılmadı." if bloke_bas else
         "ZK bloke hesabının başlangıç tarihi okunamadı."),
        ("ZK ORANLARI EVDS'te YAYIMLANMIYOR; yayımlanan yalnız sonuçtur. "
         "b panelindeki oran = bloke hesap ÷ ZK'ya tabi taban, yani "
         "gerçekleşmiş TESİS oranı — vade dilimlerine ve para cinsine göre "
         "farklı oranların bileşimidir, tebliğdeki tek bir orana eşit değildir."),
        (f"Bloke hesap tesis dönemi sınırlarında güncellenir: ölçülen medyan "
         f"adım aralığı {ort_gun:.0f} gün ({zk.get('adim_sayisi', 0)} adım). "
         "Günlük farkını 'günlük likidite etkisi' saymak yanlıştır."
         if ort_gun else
         "Bloke hesap tesis dönemi sınırlarında güncellenir; günlük farkı "
         "likidite etkisi değildir."),
        ("Taban 13 gün gecikmeli yayımlanır ve ileriye TAŞINIR; taşıma 21 günü "
         "aşarsa oran hesaplanmaz (bayat paydayla oran basılmaz)."),
        ("Taban, EVDS'in yayımladığı TOPLAM seriden okunur "
         "(TP.TLDTHVADE.KB18, bin TL). İki bacak iki AYRI veri grubundan gelir "
         "ve ölçekleri farklıdır (bie_tldthvade bin TL, bie_zorundth milyon "
         "TL); elde toplamak isteyen birim çevirmek zorundadır. Hat bunu her "
         "koşuda denetler: elde kurulan toplam EVDS toplamından %1'den fazla "
         "ayrışırsa oran üretilmez ve hat durur."),
    ]
    _duzen(fig, "Zorunlu karşılıklar, tesis ve sistem likiditesi", alt, 4)
    fig.update_yaxes(title_text="bloke hesap · milyar TL", row=1, col=1,
                     secondary_y=False)
    fig.update_yaxes(title_text="taban · milyar TL", row=1, col=1,
                     secondary_y=True, showgrid=False)
    fig.update_yaxes(title_text="%", row=2, col=1)
    fig.update_yaxes(title_text="milyar TL", row=3, col=1)
    fig.update_yaxes(title_text="milyar TL", row=4, col=1)
    return fig


# ===========================================================================
# ŞEKİL 06 — Fonlama maliyeti → mevduat/kredi faizi geçişkenliği
# ===========================================================================
def sekil_06(H, o, damga):
    if H is None or H.empty or "marjinal" not in H.columns:
        return None
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "a) Marjinal TCMB faizi, ticari TL kredi ve TL "
                            "mevduat faizi (%)",
                            "b) Aracılık marjları (puan)",
                            "c) 52 haftalık yuvarlanan geçişkenlik katsayısı "
                            "β — NEDENSELLİK DEĞİL, eşhareket"))
    h = _pencere(H, GEC_BAS)
    _iz(fig, h.index, h["marjinal"], "Marjinal TCMB faizi (AOFM / AOSM)",
        CLARET, 1, kalin=1.8)
    _iz(fig, h.index, h.get("politika_h"), "Politika faizi", INK, 1, kalin=1.4,
        kes="dot")
    _iz(fig, h.index, h.get("f_ticari_tl"), "Ticari kredi faizi (TL, akım)",
        TEAL, 1, kalin=1.6)
    _iz(fig, h.index, h.get("f_tuketici"), "Tüketici kredisi faizi (TL, akım)",
        MOR, 1, kalin=1.2, kes="dash")
    _iz(fig, h.index, h.get("f_mevduat_tl"), "TL mevduat faizi (akım)", LACI, 1,
        kalin=1.6)

    _iz(fig, h.index, h.get("makas"), "Ticari kredi − TL mevduat makası", GOLD,
        2, kalin=1.8)
    _iz(fig, h.index, h.get("kredi_marj"),
        "Ticari kredi − marjinal TCMB faizi", TEAL, 2, kalin=1.4, kes="dash")
    _iz(fig, h.index, h.get("mevduat_marj"),
        "Marjinal TCMB faizi − TL mevduat", LACI, 2, kalin=1.4, kes="dot")
    fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=2, col=1)

    for kol, ad, renk in (("beta_ticari_tl", "β · ticari TL kredi faizi", TEAL),
                          ("beta_mevduat_tl", "β · TL mevduat faizi", LACI)):
        if kol in h.columns:
            _iz(fig, h.index, h[kol], ad, renk, 3, kalin=1.8)
    fig.add_hline(y=1, line=dict(color=GOLD, width=1.0, dash="dot"), row=3, col=1)
    fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=3, col=1)

    g = (o.get("gecirgenlik") or {}).get("gecikme_taramasi", {})
    tic = g.get("ticari_tl", {})
    mev = g.get("mevduat_tl", {})
    alt = [
        f"Veri: TCMB EVDS3 · haftalık (Cuma) faiz akımları{_cipa(damga)}. "
        f"Pencere {_yil(GEC_BAS)}–bugün. Marjinal TCMB faizi günlük seriden "
        "gelir ama haftalık ortalamaya indirgenir; üç panel de aynı Cuma'da "
        "biter.",
        ("β, haftalık FARKLARIN 52 haftalık yuvarlanan EKK katsayısıdır "
         "(Δfaiz = α + β·Δmarjinal). β = 1 tam geçişkenlik demektir."),
        (f"Tam örneklem: ticari kredi β = {tic.get('tam_beta', float('nan')):.2f} "
         f"(en iyi gecikme {tic.get('en_iyi_gecikme_hafta', '?')} hafta, "
         f"n = {tic.get('n', '?')}), TL mevduat β = "
         f"{mev.get('tam_beta', float('nan')):.2f} "
         f"(gecikme {mev.get('en_iyi_gecikme_hafta', '?')} hafta)."),
        ("Bu bir NEDENSELLİK ölçüsü değildir: aynı pencerede her iki seriyi de "
         "kur, risk primi ya da PPK beklentisi besliyor olabilir."),
    ]
    _duzen(fig, "Fonlama maliyetinden kredi ve mevduat faizine geçişkenlik",
           alt, 3)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    fig.update_yaxes(title_text="β", row=3, col=1)
    return fig


# ===========================================================================
# ŞEKİL 07 — Gecelik faizin koridordaki konumu, örtük sıkılaştırma dönemleri
# ===========================================================================
def sekil_07(M, o, damga):
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.085,
                        subplot_titles=(
                            "a) Gecelik piyasa faizinin koridordaki konumu "
                            "(0 = taban, 1 = tavan)",
                            "b) AOFM − koridor tavanı (puan): pozitif = örtük "
                            "sıkılaştırma",
                            "c) Koridor genişliği ve politika faizinin bant "
                            "içindeki yeri (puan)"))
    t = _pencere(M, TAM_BAS)
    _iz(fig, t.index, t["konum_tlref"], "TLREF'in koridordaki konumu", LACI, 1,
        kalin=1.5)
    _iz(fig, t.index, t["konum_aofm"], "AOFM'nin koridordaki konumu", CLARET, 1,
        kalin=1.3, kes="dash")
    for yy, ad in ((0.0, "taban"), (1.0, "tavan")):
        fig.add_hline(y=yy, line=dict(color=GOLD, width=1.0, dash="dot"),
                      row=1, col=1)

    _iz(fig, t.index, t["aofm_koridor_ustu"], "AOFM − koridor tavanı", CLARET,
        2, kalin=1.5)
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)
    _olay_gomle(fig, o.get("donemler", []), 1, 3)
    _olay_gomle(fig, o.get("donemler", []), 2, 3)

    _iz(fig, t.index, t["koridor_bant"], "Koridor genişliği (tavan − taban)",
        GOLD, 3, kalin=1.6)
    _iz(fig, t.index, t["politika"] - t["koridor_alt"],
        "Politika faizi − koridor tabanı", TEAL, 3, kalin=1.4)
    _iz(fig, t.index, t["koridor_ust"] - t["politika"],
        "Koridor tavanı − politika faizi", MOR, 3, kalin=1.4, kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.8), row=3, col=1)

    don = o.get("donemler", [])
    en_uzun = max(don, key=lambda d: d["gun"]) if don else None
    en_derin = max(don, key=lambda d: d["asim_maks_pp"]) if don else None
    alt = [
        f"Veri: TCMB EVDS3 · iş günü{_cipa(damga)}. Pencere "
        f"{_yil(TAM_BAS)}–bugün. Konum kırpılmaz: bandın DIŞINA çıkması asıl "
        "anlatılacak olgudur.",
        (f"Kırmızı gölgeler: AOFM'nin koridor tavanını en az "
         f"{o['esik']['koridor_ustu_pay_pp']:.2f} puan aşarak en az "
         f"{o['esik']['donem_min_gun']} iş günü sürdüğü dönemler — toplam "
         f"{len(don)} dönem."),
    ]
    if en_uzun:
        alt.append(
            f"En uzun dönem {en_uzun['bas'][8:10]}.{en_uzun['bas'][5:7]}."
            f"{en_uzun['bas'][:4]}–{en_uzun['son'][8:10]}.{en_uzun['son'][5:7]}."
            f"{en_uzun['son'][:4]} ({en_uzun['gun']} iş günü, ortalama aşım "
            f"{en_uzun['asim_ort_pp']:.2f} puan, AOFM ortalaması "
            f"%{en_uzun['aofm_ort']:.2f}, geç likidite penceresi ortalaması "
            f"%{en_uzun['glp_ort']:.2f}).")
    if en_derin and en_derin is not en_uzun:
        alt.append(
            f"En derin aşım {en_derin['bas'][:4]} yılında: tavanın "
            f"{en_derin['asim_maks_pp']:.2f} puan üstü.")
    _duzen(fig, "Gecelik faizin koridordaki konumu ve örtük sıkılaştırma "
                "dönemleri", alt, 3)
    fig.update_yaxes(title_text="konum (0–1)", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    fig.update_yaxes(title_text="puan", row=3, col=1)
    return fig


# ===========================================================================
# ŞEKİL 08 — Rezerv hattıyla çapraz: swap stoku ve net rezerv
# ===========================================================================
def sekil_08(M, R, o, damga):
    if R is None or R.empty:
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.11,
                        subplot_titles=(
                            "a) TCMB taraflı swap stoku (bu hat) ile rezerv "
                            "hattının yerleşik swap düzeltmesi (milyar USD)",
                            "b) Net rezerv, swap hariç net rezerv ve swap "
                            "düzeltmesi (milyar USD)"))
    ort = M.index.intersection(R.index)
    m, r = M.loc[ort], R.loc[ort]
    _iz(fig, m.index, m["swap_alim_usd"] / 1000.0,
        "Swap stoku — alım yönlü (bu hat)", TEAL, 1, kalin=1.8)
    _iz(fig, m.index, m["swap_satim_usd"] / 1000.0,
        "Swap stoku — satım yönlü (bu hat)", CLARET, 1, kalin=1.8)
    _iz(fig, r.index, r["swap_yerli_usd"],
        "Rezerv hattı · yerleşiklerle swap (alım − satım)", INK, 1, kalin=1.2,
        kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=1, col=1)

    _iz(fig, r.index, r["net_rezerv_usd"], "Net rezerv", LACI, 2, kalin=1.8)
    _iz(fig, r.index, r["swap_haric_net_rezerv_usd"],
        "Swap hariç net rezerv", CLARET, 2, kalin=1.8)
    _iz(fig, r.index, r["swap_toplam_usd"],
        "Swap düzeltmesi (yerleşik + yurt dışı)", GOLD, 2, kalin=1.4, kes="dash")
    fig.add_hline(y=0, line=dict(color=INK, width=0.9), row=2, col=1)

    d = (o.get("dogrulama") or {}).get("hatlar_arasi_swap") or {}
    alt = [
        f"Veri: bu hat TCMB EVDS3 bie_swaptektarf; rezerv verisi TTO Trading "
        "rezerv hattının kendi boru hattından. İki seri yalnız ORTAK iş "
        f"günlerinde çizilir{_cipa(damga)}; rezerv hattının kendi son gözlemi "
        f"{gun_ad(R.index[-1])}.",
        ("İki hat aynı seriyi FARKLI soru için kullanıyor: burada 'TL "
         "likiditesine ne kadar katkı', rezerv hattında 'rezervin ne kadarı "
         "ödünç'. Kimlik: yerleşik swap düzeltmesi = alım yönlü − satım yönlü "
         "stok."),
    ]
    if d:
        alt.append(
            f"Kimlik sınandı: {d['n']} ortak iş gününde en büyük fark "
            f"{d['maks_fark_mlr_usd']:.2e} milyar USD — iki boru hattı aynı "
            "sayıyı üretiyor.")
    alt.append("Swap düzeltmesi yurt dışı merkez bankalarıyla yapılan swapları "
               "da içerir; bu hattın TCMB taraflı swap stoku yalnız yurt içi "
               "piyasa bacağıdır. İkisi aynı büyüklük değildir.")
    _duzen(fig, "Swap stoku ile net rezerv: iki hattın kesişimi", alt, 2,
           y_baslik="milyar USD")
    return fig


# ===========================================================================
SEKILLER = [
    ("01_koridor_faizler.html", 2),
    ("02_spreadler.html", 3),
    ("03_net_api_kompozisyon.html", 3),
    ("04_swap_fonlama.html", 2),
    ("05_zk_likidite.html", 4),
    ("06_gecirgenlik.html", 3),
    ("07_koridor_konumu.html", 3),
    ("08_rezerv_capraz.html", 2),
]


def _yukle():
    M, Z, H, R = veri.cerceveler()
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    if R is None:
        print("  ! rezerv hattının günlük çıktısı yok — Şekil 08 üretilemeyecek.")
    return M, Z, H, R, o


def kos() -> None:
    M, Z, H, R, o = _yukle()
    # DAMGA FİGÜR BAŞINA. Eskiden sekiz şeklin sekizi de hattın günlük APİ
    # saatiyle damgalanıyordu; bu hat beş ritim taşıyor ve damga iki figürde
    # yalan söylüyordu — haftalık geçişkenlik figürü on iki gün eskiyken
    # "bugün" diye, ZK figürü de dört ayrı günde biten dört paneline tek gün
    # yazarak. Aynı defteri ozet_uret.py sayfa altındaki damga için okur:
    # figürün İÇİNDEKİ ile ALTINDAKİ tarih tek kaynaktan gelsin.
    uclar = veri.sekil_uclari(M, Z, H, R)          # HAM tarih — kapı bunu okur
    saat = veri.sekil_saatleri(M, Z, H, R, uzun=True)   # yazılmış hâli
    zk_saat = veri.zk_panel_saatleri(M, Z, uzun=True)
    print(f"TCMB fonlama & likidite — grafikler · günlük bacak "
          f"{gun_ad(pd.Timestamp(o['son_gun']))}")

    ciktilar = [
        (sekil_01(M, o, saat["01_koridor_faizler.html"]), "01_koridor_faizler.html"),
        (sekil_02(M, o, saat["02_spreadler.html"]), "02_spreadler.html"),
        (sekil_03(M, o, saat["03_net_api_kompozisyon.html"]), "03_net_api_kompozisyon.html"),
        (sekil_04(M, o, saat["04_swap_fonlama.html"]), "04_swap_fonlama.html"),
        (sekil_05(M, Z, o, zk_saat), "05_zk_likidite.html"),
        (sekil_06(H, o, saat["06_gecirgenlik.html"]), "06_gecirgenlik.html"),
        (sekil_07(M, o, saat["07_koridor_konumu.html"]), "07_koridor_konumu.html"),
        (sekil_08(M, R, o, saat["08_rezerv_capraz.html"]), "08_rezerv_capraz.html"),
    ]
    n = 0
    for fig, ad in ciktilar:
        if fig is None:
            print(f"  ATLANDI: {ad} — girdisi üretilemedi (uyarilar.json'a bakın)")
            continue
        _uc_denetimi(ad, uclar[ad], saat[ad], fig)
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
