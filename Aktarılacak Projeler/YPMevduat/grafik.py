# -*- coding: utf-8 -*-
"""Yurt içi yerleşiklerin YP mevduatı — grafik katmanı (Plotly, site ev stili).

HATTIN SORUSU, FİGÜRLERİN DİLİNDE
---------------------------------
"Yabancı para mevduatı ne kadar arttı" değil, "artışın ne kadarı GERÇEK PARA
GİRİŞİ, ne kadarı DEĞERLEME". Seri milyon ABD doları cinsinden yayımlanıyor ve
sepette euro, sterlin ve kıymetli maden var: euro dolara karşı değer
kazandığında USD karşılığı hiçbir yeni hesap açılmadan yükselir. Kaynak bu
ayrıştırmayı RESMÎ olarak yayımlıyor; bu katmanın işi onu okunur kılmak,
yeniden türetmek değil. Bu yüzden hiçbir figürde "bizim arındırmamız" diye
ikinci bir seri yok: okur için iki rakip gerçek üretmek, tek bir gerçeği
göstermemekten kötüdür.

FİGÜR KÜMESİ — NEDEN ALTI, NEDEN BU BÖLÜNME
-------------------------------------------
Yedi konu var (stok · haftalık ayrıştırma · kümüle akım · kıymetli maden ·
dolarizasyon · gerçek–tüzel ayrışması · kimlik artığı) ve altı figür. Kümenin
sınırını konu sayısı değil DAMGA belirledi, ve gerekçesi şu:

  · Şekil saat defteri (veri.sekil_saatleri) her figürü ÖLÇÜM KATMANININ bir
    bloğuna bağlıyor: stok bloğu, akım bloğu, dolarizasyon bloğu. Bir figür
    iki bloktan birden beslenirse damgası bağlayıcı (EN ESKİ) bacağa düşer.
  · Kıymetli maden bacağının STOKU stok bloğunda, AKIMI akım bloğunda. İkisini
    tek figürde birleştirmek o figürü karma yapardı: akım tarafı taze olduğu
    haftalarda bile damga stok bacağına düşer ve TAZE bir panel BAYAT görünür.
    Kusur iki yönde birden yalan söyler — bu depoda bir kez tam olarak böyle
    oldu ve okur taze bir endeksi bayat sandı. Bu yüzden maden STOKU birinci
    figürün ikinci panelinde, maden AKIMI dördüncü figürün üçüncü panelinde.
  · Gerçek–tüzel ayrışması AYRI bir figür değil, kümüle akım figürünün üçüncü
    panelidir: ayrışma kümüle akımın kendisinden okunuyor ve iki figüre
    bölmek aynı seriyi iki damgayla iki kez yayımlamak olurdu.
  · Kimlik artığı KENDİ figüründe kaldı, çünkü tek karma figür odur (stok
    değişimi ile resmî ayrıştırma yan yana) ve damgası yapısal olarak
    min(stok, akım). Onu haftalık ayrıştırma figürüne katmak, yalnız akım
    tablosundan beslenen o figürü de karma yapardı.

Dosya adlarının ve saat defteri anahtarlarının KAYNAĞI veri.py'dir
(veri.SEKIL_DOSYALARI). Bu dosyada aynı adlar üç yerde daha geçiyor (panel
künyesi, zorunlu figür listesi ve koşu sırası) ve "bu dosya kendi listesini
tutmaz" diye yazılıydı — yazılmış olması onu doğru yapmıyordu. Dört liste bir
gün sessizce ayrışabilir, o yüzden ayrışma artık ÖLÇÜLÜYOR: duman sınaması
panel künyesinin ve zorunlu listenin kaynak listeyle örtüştüğünü sınıyor, koşu
sırası da aşağıda kaynak listeye karşı denetleniyor. Bir iddia ancak bir ölçüt
onu sınıyorsa yazılabilir.

EV STİLİ SÖZLEŞMESİ
-------------------
  · Paneller ALT ALTA (rows=N, cols=1). YAN YANA PANEL YOK — sayfa sınavı
    gömülü HTML'de x ekseni domain sol uçlarını sayıyor.
  · Panel başına ~340 px; buradaki `height` MDX'teki yükseklik değeriyle AYNI
    olmak zorunda ve tek kaynak cikti/yukseklikler.json. Alt başlığa BİR
    satır eklemek figürü 26 px büyütür, yani metni düzenleyen her değişiklik
    yüksekliği de değiştirir.
  · Başlık solda, açıklama satırları başlık bloğunda <sup> ile. Figür içi
    sabit konumlu dipnot KONMAZ: ev stili çalışma zamanında lejantı figürün
    alt kenarına yapıştırıyor ve dipnot uzun figürlerde onun üstüne biner.
  · Üst marj GEREKENDEN BİR EKSİK yazılır; ev stili kendi hesabıyla tamamlar.
    Doğru değeri yazmak o düzeltmeyi devre dışı bırakır ve ters teper.
  · Her figürün başlığında KENDİ veri ucu vardır — hattın ana saati değil.
    Ölçülemeyen uçta tarih HİÇ yazılmaz: yanlış bir tarih, tarihsizlikten
    kötüdür ve "veri None" ikisinden de.
  · Figür metni OKURA basılır (yayın kapısı gömülü HTML'in başlık, alt yazı,
    lejant ve ipucu metinlerini tarıyor): dosya adı, sütun adı, grup kodu ve
    kendi sürüm tarihçemiz oraya GİRMEZ. Sayı ortak/bicim ile yazılır.
    Kaynağın büyük harfli seri kodu (TP.HPBITABLO5.2) künyedir ve girebilir.

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
# ŞEKİL SAATLERİ veri.py'de, tek yerde durur: figürün alt yazısındaki tarihi
# burası, sayfadaki damgayı ozet_uret.py AYNI fonksiyondan okur.
from veri import VERI, ad_gun, sekil_saatleri

CIKTI = veri.PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı.

    Ondalık virgül, binlik nokta, eksi U+2212, yüzde işareti sayıdan ÖNCE.
    Figürün başlığı ve alt yazısı sayfada şeklin tam üstünde duruyor, yani
    okur metnidir: `f"{x:,.1f}"` kalıbı hem ondalık nokta hem ASCII tire
    taşır ve o kalıp kardeş hatların alt yazılarında hâlâ duruyor —
    kopyalanmaz.

    Koşuda `ortak/` alt süreç ortamında PYTHONPATH'tedir; hat elle kendi
    klasöründen koşturulursa olmayabilir, o yüzden depo kökünden bulunur.
    """
    try:
        import bicim
    except ImportError:
        import sys as _sys
        _sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


# --------------------------------------------------------------------------- jetonlar
# Ev stili jetonları — site/tools/plotly_stil.py ve kardeş hatlarla aynı.
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
LACI, MOR, YESIL, GRI = "#2f4b7c", "#665191", "#7a9e7e", "#8a8a8a"

# RENK BİR SÖZLÜKTÜR, süs değil: aynı kavram bütün figürlerde aynı renkte.
# Üç ayrı boyut var ve üçü de aynı sayfada dolaşıyor; boyutlar arasında renk
# ödünç alınmaz, yoksa okur ikinci figürde birinci figürün anlamını arar.
#   (1) KİŞİ boyutu — kimin mevduatı
KISI = {"toplam": INK, "gercek": CLARET, "tuzel": LACI}
#   (2) AYRIŞTIRMA boyutu — değişimin hangi parçası
AR, PE, ARTIK, DELTA = TEAL, GOLD, MOR, INK
#   (3) PARA CİNSİ boyutu — hangi döviz ya da maden
CINS = {"usd": TEAL, "eur": LACI, "diger": GRI, "maden": GOLD}

PANEL_PX = 340
SATIR_SINIR = 150     # başlık bloğunda bir <sup> satırına sığan yaklaşık karakter

# Kaynak künyesi. Seri kodları BÜYÜK harfli yazılır ve okura verilen künye
# bilgisidir; kaynağın İÇ GRUP adı (küçük harfli tablo kodu) okurun elinde
# hiçbir şey ifade etmez ve figür metnine girmez.
KAYNAK = ("Kaynak: TCMB EVDS3, haftalık para ve banka istatistikleri · "
          "TP.HPBITABLO2, TP.HPBITABLO4 ve TP.HPBITABLO5 tabloları")


# --------------------------------------------------------------------------- metin
def _sy(o: dict, anahtar: str, ondalik: int = 1, isaret: bool = False) -> str:
    """Özetten bir sayı — okur yazımıyla. Ölçülmemişse uzun tire.

    Alt başlıklardaki her sayı ÖLÇÜMDEN gelir ve tek bir yerden biçimlenir:
    figürün içindeki sayı ile sayfadaki sayı ayrı yerlerde yazılsaydı bir gün
    sessizce ayrışırlardı ve okur aynı büyüklüğü iki türlü görürdü.
    """
    v = o.get(anahtar)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return "—"
    return _bicim().sayi(v, ondalik, isaret)


def _yz(o: dict, anahtar: str, ondalik: int = 1, isaret: bool = False) -> str:
    """Özetten bir yüzde — işaret ve yüzde imi sayıdan ÖNCE (biçim sözleşmesi)."""
    v = o.get(anahtar)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return "—"
    return _bicim().yuzde(v, ondalik, isaret)


def _gun(o: dict, anahtar: str) -> str:
    """Özetteki bir blok saatinin okur yazımı; çözülemezse uzun tire."""
    d = _bicim().tarihe_cevir(o.get(anahtar))
    return ad_gun(pd.Timestamp(d)) if d is not None else "—"


def _bol(metin: str, sinir: int = SATIR_SINIR) -> list[str]:
    """Uzun alt başlık satırını KELİME sınırından böler.

    Plotly başlık satırını sarmaz; sınırı aşan satır figürün sağından taşar.
    Elle saymak yerine burada bölünür, çünkü metin her düzenlendiğinde taşma
    sessizce geri gelir ve bunu hiçbir sınama yakalamaz.
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
    """Lejantın kaç satır süreceği — alt marj bu sayıdan büyür."""
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


def _veri(damga: str | None) -> str:
    """Başlıktaki " · veri <gün>" eki — damga ÖLÇÜLEMEMİŞSE hiç yazılmaz.

    Defter bir figürün ucunu ölçemediğinde None döndürür (ör. bacaklardan biri
    hiç yüklenememişse): o zaman başlıkta tarih ÇIKMAZ. Yanlış bir tarih
    tarihsizlikten kötüdür, "veri None" ikisinden de.
    """
    return f" · veri {damga}" if damga else ""


# --------------------------------------------------------------------------- düzen
def _duzen(fig, baslik: str, alt: list[str], n_panel: int,
           y_baslik: str = "", barmode: str | None = None,
           ek_yukseklik: int = 0) -> go.Figure:
    """Ev stili düzeni ve YÜKSEKLİK — MDX ile tek kaynak.

    Açıklama satırları BAŞLIK bloğunda (<sup>) taşınır, figür içi sabit konumlu
    açıklama olarak DEĞİL: ev stili çalışma zamanında lejantı figürün alt
    kenarına yapıştırıyor ve sabit dipnot uzun figürlerde onun üstüne biner.
    Başlık bloğu her <br> için üst marjı büyütüyor, çakışma olmuyor.

    ÜST MARJ BİR EKSİK YAZILIR. Ev stili üst marjı önce koşulsuz 92'ye çeker,
    sonra YALNIZCA mevcut değer gerekenden KÜÇÜKSE yükseltir; doğru değeri
    buraya yazmak o düzeltmeyi devre dışı bırakır ve başlık panele biner.

    BAŞLIK ÜSTE ÇİVİLENİR. Plotly'nin varsayılanı başlık bloğunu üst marjın
    içinde dikey ortalar; alt başlık altı-yedi satıra çıktığında blok aşağı
    kayıp ilk panelin başlığına biniyor. y=1 ve yanchor "top" ile blok kabın
    tepesinden başlar, fazlası altta boşluk olarak kalır.
    """
    alt = [parca for satir in alt for parca in _bol(satir)]
    l_satir = _lejant_satir(fig)
    ust = 92 + 26 * len(alt) + 25
    b = 110 + max(0, l_satir - 1) * 24
    h = PANEL_PX * n_panel + ust + b + ek_yukseklik
    metin = f"<b>{baslik}</b>" + "".join(f"<br><sup>{x}</sup>" for x in alt)
    gereken_t = 92 + 26 * len(alt) + 26        # ev stilinin kendi hesabı
    blok_px = 22 + 19 * len(alt)               # ölçülmüş satır yüksekliği ~18,5 px
    dolgu_t = int(max(12, (gereken_t - blok_px) / 2))
    fig.update_layout(
        title=dict(text=metin, x=0, xanchor="left", y=1.0, yanchor="top",
                   yref="container", pad=dict(t=dolgu_t, l=0),
                   font=dict(size=15, color=INK, family="Georgia, serif")),
        height=h, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Georgia, serif", size=12, color=INK),
        # SAYI YAZIMI FİGÜRÜN İÇİNDE DE TÜRKÇE. Eksen etiketleri ve ipucu
        # kutuları Plotly'nin varsayılanıyla "231,357.0" diye çıkıyordu; sayfa
        # metni aynı sayıyı "231.357,0" diye yazıyor ve okur iki yazımı yan
        # yana görüyordu. Ondalık virgül, binlik nokta — ortak biçim
        # sözleşmesinin figür içindeki karşılığı.
        separators=",.",
        legend=dict(orientation="h", yanchor="top", y=-0.1, x=0,
                    font=dict(size=11), tracegroupgap=2,
                    bgcolor="rgba(255,255,255,0)"),
        margin=dict(l=64, r=64, t=ust, b=b),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", bordercolor=GRID))
    if barmode:
        fig.update_layout(barmode=barmode)
    fig.update_xaxes(gridcolor=GRID, zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor=GRID,
                     automargin=True)
    if y_baslik:
        fig.update_yaxes(title_text=y_baslik)
    return fig


def _sablon(ad: str, birim: str, ondalik: int) -> str:
    """İpucu kutusunun metni — okur yazımıyla.

    YÜZDE İŞARETİ SAYIDAN ÖNCE GELİR (biçim sözleşmesi) ve ipucu kutusu da
    okur metnidir: kardeş hatlar yüzdeyi sayının ARKASINA koyuyor ve o kalıp
    kopyalanmadı. İşaretin yeri okunuşu belirler; "yüzde 14,7" ile "14,7%"
    aynı sayfada yan yana durursa okur iki ayrı yazım görür. Binlik ve
    ondalık ayraçları ise düzenin kendi ayarından geliyor (bkz. _duzen).
    """
    if birim == "%":
        govde = f"yüzde %{{y:,.{ondalik}f}}"
    else:
        govde = f"%{{y:,.{ondalik}f}}{birim}"
    return f"{govde}<extra>{ad}</extra>"


def _cizgi(fig, s, ad: str, renk: str, satir: int = 1, kalin: float = 2.0,
           kes: str | None = None, ikincil: bool | None = None,
           birim: str = " milyon dolar", ondalik: int = 0,
           gorunur: bool = True) -> None:
    """Bir çizgi izi. Boş seri hiç çizilmez — boş bir iz lejantı kirletir ve
    figürün çizdiği ucu ölçen denetimi de yanıltır."""
    if s is None:
        return
    s = pd.Series(s).dropna()
    if s.empty:
        return
    ek = {} if ikincil is None else {"secondary_y": ikincil}
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, name=ad, mode="lines", showlegend=gorunur,
        line=dict(color=renk, width=kalin, dash=kes),
        hovertemplate=_sablon(ad, birim, ondalik)),
        row=satir, col=1, **ek)


def _cubuk(fig, s, ad: str, renk: str, satir: int = 1,
           birim: str = " milyon dolar", ondalik: int = 0,
           opaklik: float = 0.85, gorunur: bool = True) -> None:
    """Bir çubuk izi (yığılmış ayrıştırma panelleri için)."""
    if s is None:
        return
    s = pd.Series(s).dropna()
    if s.empty:
        return
    fig.add_trace(go.Bar(
        x=s.index, y=s.values, name=ad, marker_color=renk, opacity=opaklik,
        showlegend=gorunur, hovertemplate=_sablon(ad, birim, ondalik)),
        row=satir, col=1)


def _sifir(fig, satir: int = 1) -> None:
    """Sıfır çizgisi. Akım panellerinde işaretin kendisi haberdir: giriş mi
    çıkış mı sorusu, eksenin hangi tarafında durduğuyla okunur."""
    fig.add_hline(y=0, line=dict(color=GRI, width=1), row=satir, col=1)


def _kol(df: pd.DataFrame, ad: str):
    """Bir sütun ya da None — eksik sütun figürü düşürmez, izi çizilmez."""
    if df is None or df.empty or ad not in df.columns:
        return None
    s = df[ad]
    return s if s.notna().any() else None


def _cizili_uc(fig) -> pd.Timestamp | None:
    """Figürün gerçekten ÇİZDİĞİ uç: her izin son dolu gözlemi, EN ESKİSİ.

    Saat defteri sütun adıyla ölçüyor, bu fonksiyon FİGÜRÜN KENDİSİNİ; ikisi
    ayrışırsa figüre bir iz eklenmiş ve defter güncellenmemiş demektir. Kusur
    göze çarpmaz — damga bir gün kayar ve koşu yeşil biter.
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


def _uc_denetimi(ad: str, beyan: str | None, fig) -> None:
    """İlan edilen uç ile figürün çizdiği uç TEK YÖNLÜ karşılaştırılır.

    NEDEN EŞİTLİK DEĞİL — ve bu, kardeş hattan bilinçli bir sapmadır. Orada
    saat defteri figürün ÇİZDİĞİ sütunlardan ölçülüyor, yani eşitlik doğal.
    Burada defter ÖLÇÜM BLOĞUNUN ortak tarihini taşıyor: blok, içindeki
    BÜTÜN serilerin dolu olduğu haftaya çıpalı ve bir figür o bloğun yalnız
    bir alt kümesini çiziyor olabilir. Çizilmeyen tek bir bacak geride
    kaldığında eşitlik ölçütü düşer ve YAYININ ÖNÜNDE DURAN BİR DENETİMİN
    YANLIŞ ALARMI, ARIZANIN KENDİSİDİR: bu depoda bir kez yayın altı koşu
    üst üste düştü ve site on iki saat dondu.

    Bu yüzden yalnız ZARARLI yön durdurur:
      · çizilen uç ilan edilenden ESKİYSE → figür göstermediği bir haftayı
        ilan ediyor demektir; bu düpedüz yanlış bir tarihtir, hat DURUR.
      · çizilen uç ilan edilenden YENİYSE → blok saati tutucudur, figür
        gerçekte daha ileriye kadar çiziyor. Yalan değil ama sessiz de
        kalınmaz: koşu kaydına operatör notu düşer.
    """
    if not beyan:
        return
    d = _bicim().tarihe_cevir(beyan)
    cizili = _cizili_uc(fig)
    if d is None or cizili is None:
        return
    beyan_t = pd.Timestamp(d)
    if cizili < beyan_t:
        raise SystemExit(
            f"DUR: {ad} için ilan edilen uç ({beyan}) figürün çizdiği uçtan "
            f"({ad_gun(cizili)}) YENİ. Şekil saat defteri figürün izleriyle "
            "ayrışmış; damga, figürde olmayan bir haftayı ilan eder.")
    if cizili > beyan_t:
        print(f"    not: {ad} — blok saati {beyan}, figürün kendi ucu "
              f"{ad_gun(cizili)}; damga tutucu (bloğun bir bacağı geride).")


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


# --------------------------------------------------------------------------- veri
def _yukle():
    """Ölçüm katmanının çerçeveleri. Okunan her dosyanın bir YAZICISI var ve o
    yazıcı hattın adım listesinde görünüyor — bu depoda bir kez kimsenin
    yazmadığı bir dosya okunuyordu: dosya vardı, hata vermiyordu, yalnızca
    yaşlanıyordu. Ölü bağımlılık kırık olandan tehlikelidir.
    """
    def oku(ad):
        yol = VERI / ad
        if not yol.exists():
            return pd.DataFrame()
        return pd.read_csv(yol, index_col=0, parse_dates=True).sort_index()

    M = oku("metrik_haftalik.csv")      # metrik.py: stok, kırılım, paylar
    A = oku("ayristirma.csv")           # metrik.py: Δ stok · arındırılmış · parite · artık
    K = oku("kumule.csv")               # metrik.py: ay · yıl · 4 ve 13 haftalık kümüle
    D = oku("dolarizasyon.csv")         # metrik.py: ham ve arındırılmış pay
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    return M, A, K, D, o


def _olculdu(o: dict, blok_saati: str) -> bool:
    """Bu figürün beslendiği ÖLÇÜM BLOĞU bu koşuda ölçüldü mü?

    NEDEN VAR — ölçüm katmanı bazı çerçeveleri yalnız DOLU olduklarında
    yazıyor (kümüle akım ve dolarizasyon). Bir bacak yüklenemediğinde o
    çerçeve yazılmaz ama diskteki ÖNCEKİ koşudan kalan dosya yerinde durur:
    çizim katmanı onu okur, figür üretilir, koşu yeşil biter ve sayfaya
    BAYAT bir figür gider. Üstelik bloğun saati de yazılmadığı için figürün
    altına tarih hiç basılmaz — yani bayatlık okura görünmez bile. Dosyanın
    varlığı ölçümün kanıtı değildir; kanıt, ölçüm katmanının o bloğa BU
    KOŞUDA bir saat yazmış olmasıdır. Ölü bağımlılık kırık olandan
    tehlikelidir: dosya vardır, okunur, hata vermez, yalnızca yaşlanır.
    """
    return _bicim().tarihe_cevir(o.get(blok_saati)) is not None


# ===========================================================================
# 01 — STOK VE KIRILIM   (yalnız stok bloğu; damga stok saatinden)
# ===========================================================================
def sekil_01(M: pd.DataFrame, o: dict, damga: str | None):
    """Yurt içi yerleşiklerin stoku, kişi kırılımı ve kıymetli maden bacağı.

    GENİŞ TOPLAM ADIYLA VE FARKIYLA GEÇER. Kaynağın dört numaralı tablosundaki
    toplam (TP.HPBITABLO4.1) yurt dışı yerleşik bankaları da içeriyor ve
    hattın konusu yurt içi yerleşiklerdir; iki toplamı aynı şeymiş gibi yan
    yana koymak bu hattın en pahalı hatası olurdu. Bu yüzden geniş toplam ince
    kesikli ve gri çiziliyor (manşet değil), adı "yurt dışı yerleşikler dahil"
    diye geçiyor ve farkı alt yazıda sayıyla duruyor.

    AMA FARKIN TAMAMI YURT DIŞI BACAK DEĞİLDİR ve alt yazı bunu söylemez.
    Künyenin kalem numaralandırmasına göre geniş toplam dört bölümlü ve yurt
    içi toplam yalnız birincisi; fark üç bölümü birden kapsıyor. Yurt dışı
    yerleşik bankalar bunların yalnız biri (TP.HPBITABLO4.21) ve o seri bu
    hatta çekilmiyor, farkın içindeki bir başka kalem ise (TP.HPBITABLO4.20)
    tek başına farkın yüzde sekizi kadar. Alt yazı bir zamanlar farkın
    TAMAMINI "yurt dışı bacağın payı" diye ilan ediyordu; hattın veri katmanı
    aynı varsayımı başka bir yerde açıkça yasaklarken. Bir düzeltme
    genelleştirilmeden tamamlanmaz: ölçülen şey KAPSAM FARKIDIR ve öyle yazılır.

    MADEN BACAĞI BURADA YALNIZ SEVİYE. Aynı bacağın akımı dördüncü figürde:
    seviye stok bloğundan, akım değişim tablosundan geliyor ve ikisini tek
    figürde birleştirmek damgayı bağlayıcı (en eski) bacağa düşürürdü.
    """
    if not _olculdu(o, "stok_tarih") or _kol(M, "stok_toplam_mia") is None:
        return None
    b = _bicim()
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.10,
        specs=[[{"secondary_y": False}], [{"secondary_y": True}]],
        subplot_titles=(
            "Toplam stok ve kişi kırılımı",
            "Kıymetli maden depo hesapları: seviye ve toplam içindeki payı"))

    _cizgi(fig, _kol(M, "stok_toplam_mia"), "Yurt içi yerleşikler, toplam",
           KISI["toplam"], 1, kalin=2.6, birim=" milyar dolar", ondalik=1)
    _cizgi(fig, _kol(M, "stok_gercek_mia"), "Gerçek kişiler", KISI["gercek"], 1,
           kalin=2.0, birim=" milyar dolar", ondalik=1)
    _cizgi(fig, _kol(M, "stok_tuzel_mia"), "Tüzel kişiler", KISI["tuzel"], 1,
           kalin=2.0, birim=" milyar dolar", ondalik=1)
    _cizgi(fig, _kol(M, "genis_toplam_mia"),
           "Yurt dışı yerleşikler dahil geniş toplam", GRI, 1, kalin=1.2,
           kes="dot", birim=" milyar dolar", ondalik=1)

    _cizgi(fig, _kol(M, "maden_gercek_mia"), "Gerçek kişilerin maden hesapları",
           GOLD, 2, kalin=2.0, birim=" milyar dolar", ondalik=1)
    _cizgi(fig, _kol(M, "maden_tuzel_mia"), "Tüzel kişilerin maden hesapları",
           MOR, 2, kalin=2.0, birim=" milyar dolar", ondalik=1)
    _cizgi(fig, _kol(M, "maden_pay_toplam"),
           "Maden hesaplarının toplam içindeki payı (sağ eksen)", TEAL, 2,
           kalin=1.6, kes="dash", ikincil=True, birim="%", ondalik=1)

    fig.update_yaxes(title_text="milyar dolar", row=1, col=1)
    fig.update_yaxes(title_text="milyar dolar", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="%", row=2, col=1, secondary_y=True,
                     showgrid=False)

    ilk = M.dropna(how="all").index
    alt = [
        "Manşet, yurt içi yerleşiklerin toplam yabancı para mevduatıdır "
        "(TP.HPBITABLO2.10). Kesikli gri iz, yurt dışı yerleşik bankaları da "
        "kapsayan geniş toplamdır (TP.HPBITABLO4.1) ve manşet değildir: son "
        f"haftada iki toplam arasındaki kapsam farkı "
        f"{_sy(o, 'genis_fark_mia', 1)} milyar dolar, geniş toplam içindeki "
        f"payı {_yz(o, 'genis_fark_pay', 1)}. Bu fark yalnız yurt dışı "
        "yerleşik bankaları değil, kaynağın kırılım tablosunda onların dışında "
        "kalan bölümleri de kapsıyor; bileşimi bu sayfada ölçülmedi.",
        f"Son hafta: toplam {_sy(o, 'stok_toplam_mia', 1)} milyar dolar; "
        f"gerçek kişiler {_sy(o, 'stok_gercek_mia', 1)} "
        f"({_yz(o, 'gercek_pay', 1)}), tüzel kişiler "
        f"{_sy(o, 'stok_tuzel_mia', 1)} ({_yz(o, 'tuzel_pay', 1)}).",
        "Kıymetli maden depo hesapları dolar karşılığıyla yayımlanır: altın "
        "fiyatı yükseldiğinde bu bacak tek bir gram bile yatırılmadan büyür. "
        f"Son haftada gerçek kişilerde {_sy(o, 'maden_gercek_mia', 1)}, tüzel "
        f"kişilerde {_sy(o, 'maden_tuzel_mia', 1)} milyar dolar; ikisinin "
        f"toplam içindeki payı {_yz(o, 'maden_pay_toplam', 1)}.",
        "Bu şekildeki seriler stok tablolarından geliyor ve "
        f"{b.tarih_uzun(ilk[0]) if len(ilk) else '—'} tarihinde başlıyor; "
        "haftalık değişim tablosu daha geriye gidiyor ve o tarihçe akım "
        "şekillerinde görünür.",
        KAYNAK,
    ]
    return _duzen(fig, f"Yurt içi yerleşiklerin yabancı para mevduatı{_veri(damga)}",
                  alt, n_panel=2)


# ===========================================================================
# 02 — KÜMÜLE ARINDIRILMIŞ AKIM VE AYRIŞMA   (yalnız akım bloğu)
# ===========================================================================
def sekil_02(K: pd.DataFrame, o: dict, damga: str | None):
    """Hattın asıl katkısı: haftalık fiili akımın ay içinde ve yıl içinde toplamı.

    ÜÇÜNCÜ PANEL AYRI BİR FİGÜR DEĞİL. Gerçek ve tüzel kişilerin ayrışması
    tam olarak bu serilerden okunuyor; ayrı bir figüre bölmek aynı seriyi iki
    damgayla iki kez yayımlamak olurdu. Kayan on üç haftalık toplam, ay ve yıl
    pencerelerinin başlangıç gününe bağımlı olmayan tek görünümdür: "aynı
    seri, farklı pencere, farklı sayı" bir iddia değil, yan yana duran bir
    ölçüdür.

    ETİKET UYARISI ALT YAZIDA DURUYOR: haftalık gözlem cumaya damgalı ve bir
    önceki cumadan bu yana olan değişimi taşıyor, yani ayın ilk haftası bir
    önceki ayın son günlerini de kapsıyor. Ölçü doğru olsa da etiket yanlışsa
    kusur sürer — okur bugünün hareketi sanar.
    """
    if not _olculdu(o, "akim_tarih") or _kol(K, "kum_yil_ar_toplam_mn") is None:
        return None
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.08,
        subplot_titles=(
            "Yıl içi kümüle: takvim yılına damgalı haftaların toplamı",
            "Ay içi kümüle: takvim ayına damgalı haftaların toplamı",
            "On üç haftalık kayan toplam: gerçek ve tüzel kişiler karşı karşıya"))

    for satir, onek in ((1, "kum_yil_"), (2, "kum_ay_")):
        goster = satir == 1
        _cizgi(fig, _kol(K, f"{onek}ar_toplam_mn"), "Toplam", KISI["toplam"],
               satir, kalin=2.6, gorunur=goster)
        _cizgi(fig, _kol(K, f"{onek}ar_gercek_mn"), "Gerçek kişiler",
               KISI["gercek"], satir, kalin=2.0, gorunur=goster)
        _cizgi(fig, _kol(K, f"{onek}ar_tuzel_mn"), "Tüzel kişiler",
               KISI["tuzel"], satir, kalin=2.0, gorunur=goster)
        _sifir(fig, satir)

    _cizgi(fig, _kol(K, "kum_13h_ar_gercek_mn"),
           "Gerçek kişiler, on üç haftalık toplam", KISI["gercek"], 3, kalin=2.2)
    _cizgi(fig, _kol(K, "kum_13h_ar_tuzel_mn"),
           "Tüzel kişiler, on üç haftalık toplam", KISI["tuzel"], 3, kalin=2.2)
    _sifir(fig, 3)
    for satir in (1, 2, 3):
        fig.update_yaxes(title_text="milyon dolar", row=satir, col=1)

    ters = o.get("ayrisma_ters_oran")
    ayrisma_satiri = (
        f"Ölçülen {_sy(o, 'ayrisma_n_hafta', 0)} haftada gerçek ve tüzel "
        "kişilerin haftalık fiili akımlarının ters işaret taşıma oranı "
        f"{_bicim().yuzde(ters * 100, 1) if isinstance(ters, float) else '—'}; "
        f"iki akımın korelasyonu {_sy(o, 'ayrisma_korel', 2)}. Bu bir "
        "ölçümdür, kural değildir."
        if isinstance(ters, float) else
        "Gerçek ve tüzel kişilerin ayrışması bu koşuda ölçülmedi: örneklem "
        "bir yıllık haftalık gözlemin altında kaldı.")

    alt = [
        "Buradaki akım, kaynağın PARİTE ETKİSİNDEN ARINDIRILMIŞ değişimidir: "
        "hesaplara giren ve çıkan tutar. Sepetin dolar karşısında "
        "değerlenmesinden ve kıymetli maden fiyatından gelen büyüme bu "
        "serinin dışındadır ve haftalık ayrıştırma şeklinde ayrıca duruyor.",
        f"Yıl içi toplam {_gun(o, 'kum_yil_bas')} tarihinden bu yana "
        f"{_sy(o, 'kum_yil_hafta', 0)} haftayı, ay içi toplam "
        f"{_gun(o, 'kum_ay_bas')} tarihinden bu yana "
        f"{_sy(o, 'kum_ay_hafta', 0)} haftayı topluyor. Son haftada yıl içi "
        f"{_sy(o, 'kum_yil_ar_toplam_mn', 0)}, ay içi "
        f"{_sy(o, 'kum_ay_ar_toplam_mn', 0)} milyon dolar.",
        "Haftalık gözlem cumaya damgalıdır ve bir önceki cumadan bu yana olan "
        "değişimi taşır: ayın ilk haftası bir önceki ayın son günlerini de "
        "kapsar. Ay içi toplam bu yüzden takvim ayının akımı değil, o aya "
        "damgalı haftaların toplamıdır.",
        ayrisma_satiri,
        "Toplama boş hafta doldurmaz: ölçülmemiş bir hafta sıfır sayılmaz. "
        "Ay başında kümülenin sıfıra yakın olması bir ölçümdür, ama besleme "
        "durduğunda da aynı görünür; ikisini toplanan hafta sayısı ayırır.",
        KAYNAK,
    ]
    return _duzen(fig, f"Parite etkisinden arındırılmış kümüle akım{_veri(damga)}",
                  alt, n_panel=3)


# ===========================================================================
# 03 — HAFTALIK AYRIŞTIRMA   (yalnız akım bloğu)
# ===========================================================================
def sekil_03(A: pd.DataFrame, o: dict, damga: str | None):
    """Haftalık değişimin iki parçası: fiili akım ve parite etkisi.

    AYRIŞTIRMAYI BİZ TÜRETMİYORUZ; kaynak iki bloğu da kendisi yayımlıyor. Bu
    figürde yalnız o iki blok var — stok değişimi burada ÇİZİLMİYOR, çünkü
    stok başka bir tablodan geliyor ve figürü karma yapardı: damga bağlayıcı
    (en eski) bacağa düşer, akım tarafı taze olduğu haftalarda bile bayat
    görünürdü. İkisinin toplamının stok değişimini kapatıp kapatmadığı kimlik
    şeklinde, kendi damgasıyla ölçülüyor.
    """
    if not _olculdu(o, "akim_tarih") or _kol(A, "ar_toplam") is None:
        return None
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.08,
        subplot_titles=("Toplam", "Gerçek kişiler", "Tüzel kişiler"))
    for satir, etiket in ((1, "toplam"), (2, "gercek"), (3, "tuzel")):
        goster = satir == 1
        _cubuk(fig, _kol(A, f"ar_{etiket}"),
               "Parite etkisinden arındırılmış değişim", AR, satir,
               gorunur=goster)
        _cubuk(fig, _kol(A, f"pe_{etiket}"), "Parite etkisi", PE, satir,
               gorunur=goster)
        _sifir(fig, satir)
        fig.update_yaxes(title_text="milyon dolar", row=satir, col=1)

    alt = [
        "Kaynak haftalık değişimi İKİ parçaya ayırıp ikisini de kendisi "
        "yayımlıyor: hesaplara giren ve çıkan tutar (arındırılmış değişim, "
        "TP.HPBITABLO5.1 … TP.HPBITABLO5.11) ve sepetin dolar karşısındaki "
        "hareketinden gelen değerleme (parite etkisi, TP.HPBITABLO5.12 … "
        "TP.HPBITABLO5.22). Çubuklar üst üste yığılıdır; ikisinin toplamı "
        "stok değişimidir.",
        f"Son haftada toplam fiili akım {_sy(o, 'ar_toplam_mn', 1)} milyon "
        f"dolar, parite etkisi {_sy(o, 'pe_toplam_mn', 1)} milyon dolar. "
        f"Gerçek kişilerde fiili akım {_sy(o, 'ar_gercek_mn', 1)}, tüzel "
        f"kişilerde {_sy(o, 'ar_tuzel_mn', 1)} milyon dolar.",
        "Eksi değer hesaplardan çıkış, artı değer giriş demektir. Parite "
        "etkisinin eksi olması bir çıkış değildir: sepetteki para birimleri "
        "dolara karşı değer kaybettiğinde aynı mevduatın dolar karşılığı "
        "düşer.",
        "İki bloğun toplamının yayımlanan stok değişimini kapatıp kapatmadığı "
        "ayrıca ölçülüyor ve kimlik şeklinde yayımlanıyor.",
        KAYNAK,
    ]
    return _duzen(fig, f"Haftalık değişimin ayrıştırılması{_veri(damga)}",
                  alt, n_panel=3, barmode="relative")


# ===========================================================================
# 04 — PARA CİNSİ VE KIYMETLİ MADEN   (yalnız akım bloğu)
# ===========================================================================
def sekil_04(K: pd.DataFrame, o: dict, damga: str | None):
    """Fiili akımın para cinsi kırılımı ve kıymetli maden bacağının seyri.

    KIRILIM HAFTALIK DEĞİL, ON ÜÇ HAFTALIK KAYAN TOPLAM. Haftalık kırılım
    çubukları dört bacakta birden gürültülüdür ve okur yönü göremez; kayan
    toplam yönü gösterir ve pencere başlangıcına bağımlı değildir.

    ÜÇÜNCÜ PANEL, KIYMETLİ MADEN BACAĞININ İKİ YÜZÜ. Kaynak maden hesaplarını
    da aynı ayrıştırmayla yayımlıyor: hesaplardan gerçekten çıkan tutar
    arındırılmış blokta, değerleme kaynaklı büyüme parite etkisi bloğunda
    duruyor. İkisi yan yana çizilince "altın hesabı büyüdü" ile "altın hesabına
    para girdi" arasındaki fark gözle görülür.
    """
    if not _olculdu(o, "akim_tarih") or _kol(K, "kum_13h_ar_gercek_usd_mn") is None:
        return None
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.08,
        subplot_titles=(
            "Gerçek kişiler: fiili akımın para cinsi kırılımı, on üç haftalık toplam",
            "Tüzel kişiler: fiili akımın para cinsi kırılımı, on üç haftalık toplam",
            "Kıymetli maden bacağı: yıl içi fiili akım ve değerleme"))

    adlar = (("usd", "ABD doları"), ("eur", "Euro"),
             ("diger", "Diğer para cinsleri"), ("maden", "Kıymetli maden"))
    for satir, etiket in ((1, "gercek"), (2, "tuzel")):
        for kir, ad in adlar:
            _cubuk(fig, _kol(K, f"kum_13h_ar_{etiket}_{kir}_mn"), ad,
                   CINS[kir], satir, gorunur=satir == 1)
        _sifir(fig, satir)

    _cizgi(fig, _kol(K, "kum_yil_ar_gercek_maden_mn"),
           "Gerçek kişiler, maden hesaplarına fiili akım", GOLD, 3, kalin=2.4)
    _cizgi(fig, _kol(K, "kum_yil_ar_tuzel_maden_mn"),
           "Tüzel kişiler, maden hesaplarına fiili akım", MOR, 3, kalin=2.0)
    _cizgi(fig, _kol(K, "kum_yil_pe_gercek_maden_mn"),
           "Gerçek kişiler, maden hesaplarında değerleme", GOLD, 3, kalin=1.4,
           kes="dash")
    _cizgi(fig, _kol(K, "kum_yil_pe_tuzel_maden_mn"),
           "Tüzel kişiler, maden hesaplarında değerleme", MOR, 3, kalin=1.2,
           kes="dash")
    _sifir(fig, 3)
    for satir in (1, 2, 3):
        fig.update_yaxes(title_text="milyon dolar", row=satir, col=1)

    alt = [
        "İlk iki panelde çubuklar üst üste yığılıdır ve her biri o para "
        "cinsinden hesaplara giren ya da çıkan tutarı gösterir; parite etkisi "
        "bu panellerin dışındadır.",
        f"Son haftada gerçek kişilerin maden hesaplarına fiili akım "
        f"{_sy(o, 'ar_gercek_maden_mn', 1)} milyon dolar, aynı hesaplardaki "
        f"değerleme {_sy(o, 'pe_gercek_maden_mn', 1)} milyon dolar. Tüzel "
        f"kişilerde fiili akım {_sy(o, 'ar_tuzel_maden_mn', 1)}, değerleme "
        f"{_sy(o, 'pe_tuzel_maden_mn', 1)} milyon dolar.",
        "Üçüncü panelde düz izler fiili akımın, kesikli izler değerlemenin yıl "
        "içi toplamıdır. İkisi ters yöne gittiğinde stok büyürken hesaplardan "
        "para çıkıyor demektir; büyümenin kaynağı fiyattır.",
        "Diğer para cinsleri bacağı sterlin ve benzeri küçük kalemleri "
        "toplar; uzun süre tam sıfır kalan bir bacak, hareketin olmaması ile "
        "kaynağın o bacağı yayımlamayı bırakması arasında ayırt edilemez ve "
        "böyle bir durum koşu kaydında adıyla görünür.",
        KAYNAK,
    ]
    return _duzen(fig, f"Fiili akımın para cinsi ve kıymetli maden kırılımı{_veri(damga)}",
                  alt, n_panel=3, barmode="relative")


# ===========================================================================
# 05 — KİMLİK DENETİMİ   (KARMA: stok ve akım bloğu; damga en eski bacak)
# ===========================================================================
def sekil_05(A: pd.DataFrame, o: dict, damga: str | None):
    """Δ stok ≟ arındırılmış değişim + parite etkisi — ve ARTIK.

    BU FİGÜR YAYINI DURDURMAZ, GÖSTERİR. Kimlik kaynağın İKİ AYRI TABLOSU
    arasında kuruluyor (stok tablosu ile değişim tablosu), yani yuvarlama ve
    revizyon vintajı farkı taşıyor. Kimliği yayının önüne koymak, ölçmeye
    çalıştığımız şeyi görünmez kılardı; artık ölçülür, yayımlanır ve
    kapanmadığı hafta okurun gözüne çarpar.

    TOLERANS BANDI ÇİZİLİYOR, çünkü "artık sıfır değil" tek başına bir şey
    söylemez: brüt hareketin büyüklüğüne göre ölçülen bir eşik var ve okur
    artığın o eşiğin içinde mi dışında mı olduğunu görmeli.
    """
    if not _olculdu(o, "kimlik_tarih") or _kol(A, "artik_toplam") is None:
        return None

    # FİGÜR, KİMLİĞİN KURULABİLDİĞİ PENCEREYE KIRPILIR.
    #
    # Kimlik İKİ TABLODAN birden besleniyor ve tarihçe asimetrik: değişim
    # tablosu 2014'te, stok tabloları 2024'te başlıyor. Artık ancak ikisinin
    # ortak haftasında ölçülebilir; tolerans bandı ise yalnız arındırılmış
    # değişim ile parite etkisinin brüt hareketinden türediği için ÖLÇÜLEMEYEN
    # dönemde de hesaplanabiliyordu. Kırpılmadığında sonuç ölçüldü: alt panelin
    # ekseni 2014'e açılıyor, artık izleri panelin sağ yüzde on yedisine
    # sıkışıyor ve panelin geri kalanını tek başına tolerans bandı dolduruyor —
    # okur, kimliğin on iki yıl boyunca sınandığını ve hep tuttuğunu görür.
    # Oysa o dönemde kimlik HİÇ sınanmadı.
    #
    # Kural: bir figür, ÖLÇÜLEMEYEN bir dönemi çizmez. Kırpma pencereyi
    # artığın kendisinden alır (bugünkü sıralamaya bakmaz), üst panel de aynı
    # pencereye girer — üstteki kıyasın ("çubukların toplamı kesikli izi
    # kapatıyor mu") sorusu da ancak stok bacağı varken sorulabilir.
    _artik = A["artik_toplam"].dropna()
    A = A.loc[_artik.index[0]:_artik.index[-1]] if len(_artik) else A

    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.11,
        subplot_titles=(
            "Yayımlanan stok değişimi ile resmî ayrıştırmanın toplamı",
            "Artık: stok değişimi eksi (arındırılmış değişim artı parite etkisi)"))

    _cubuk(fig, _kol(A, "ar_toplam"), "Parite etkisinden arındırılmış değişim",
           AR, 1)
    _cubuk(fig, _kol(A, "pe_toplam"), "Parite etkisi", PE, 1)
    _cizgi(fig, _kol(A, "delta_toplam"), "Yayımlanan stok değişimi", DELTA, 1,
           kalin=1.6, kes="dot")
    _sifir(fig, 1)

    _cizgi(fig, _kol(A, "artik_toplam"), "Artık, toplam", ARTIK, 2, kalin=2.2,
           ondalik=1)
    _cizgi(fig, _kol(A, "artik_gercek"), "Artık, gerçek kişiler", KISI["gercek"],
           2, kalin=1.2, kes="dot", ondalik=1)
    _cizgi(fig, _kol(A, "artik_tuzel"), "Artık, tüzel kişiler", KISI["tuzel"],
           2, kalin=1.2, kes="dot", ondalik=1)
    esik = _kol(A, "esik_toplam")
    if esik is not None:
        _cizgi(fig, esik, "Tolerans", GRI, 2, kalin=1.0, kes="dash", ondalik=1)
        _cizgi(fig, -esik, "Tolerans", GRI, 2, kalin=1.0, kes="dash",
               ondalik=1, gorunur=False)
    _sifir(fig, 2)
    for satir in (1, 2):
        fig.update_yaxes(title_text="milyon dolar", row=satir, col=1)

    kaydirma = o.get("kimlik_kaydirma")
    alt = [
        "Kaynak hem stok seviyesini hem de haftalık değişimin iki parçasını "
        "yayımlıyor. Üstteki panelde yığılı çubukların toplamı, kesikli izle "
        "çizilen stok değişimini kapatmalıdır; alttaki panel aradaki farkı "
        "gösterir.",
        # HÜKÜM, ÖLÇÜM VE TOLERANS ARTIK ÜÇ AYRI KAYNAKTAN BİRLEŞİYOR.
        # Koşu kaydının cümlesi mekanikleşti (yalnız ölçümü bildiriyor); hüküm
        # kendi anahtarında, toleransın iki bacağı ve pencere uzunluğu da
        # öyle. Nüansı kuran yer BURASI — figürün gözden geçirilmiş alt
        # yazısı — ve sayıları ölçümden çekiyor: bir gün eşik değişirse alt
        # yazı kendiliğinden düzelir.
        (o.get("kimlik_hukum") or "Kimlik bu koşuda sınanamadı.") + " "
        + (o.get("kimlik_cumlesi") or
           "Ölçülmemiş bir sınavın sonucu bildirilmez.")
        + f" Ölçüm penceresi son {_sy(o, 'kimlik_pencere_hafta', 0)} hafta; "
          f"tolerans, o haftanın brüt hareketinin "
          f"{_yz(o, 'kimlik_esik_pay', 0)} kadarı ya da "
          f"{_sy(o, 'kimlik_esik_mn', 1)} milyon dolar — hangisi büyükse.",
        f"Artığın son haftadaki değeri toplamda "
        f"{_sy(o, 'kimlik_artik_toplam_mn', 1)}, gerçek kişilerde "
        f"{_sy(o, 'kimlik_artik_gercek_mn', 1)}, tüzel kişilerde "
        f"{_sy(o, 'kimlik_artik_tuzel_mn', 1)} milyon dolar. Gri kesikli "
        "izler toleransın iki yönünü gösteriyor.",
        "Bu şekil iki tablodan birden besleniyor ve tarihi, ikisinin en eski "
        "olanına bağlıdır: bir kıyas ancak her iki tarafın da ölçüldüğü güne "
        "kadar kurulabilir. Aynı sebeple şekil yalnız iki tablonun ORTAK "
        "haftalarını çiziyor; değişim tablosunun tek başına uzandığı daha "
        "eski dönemde kimlik sınanamaz ve o dönem burada gösterilmez.",
    ]
    if isinstance(kaydirma, int) and kaydirma != 0:
        alt.insert(3, "Değişim tablosunun haftası, stok tablosunun haftasıyla "
                      f"{_sy(o, 'kimlik_kaydirma', 0)} hafta kaydırılarak "
                      "eşleştirildi; kaydırma artığı belirgin biçimde "
                      "küçülttüğü için benimsendi.")
    alt.append(KAYNAK)
    return _duzen(fig, f"Kimlik denetimi: ayrıştırma stok değişimini kapatıyor mu{_veri(damga)}",
                  alt, n_panel=2, barmode="relative")


# ===========================================================================
# 06 — DOLARİZASYON PAYI   (yalnız dolarizasyon bloğu)
# ===========================================================================
def sekil_06(D: pd.DataFrame, o: dict, damga: str | None):
    """YP / (TL + YP): ham pay ve parite etkisinden arındırılmış pay.

    BU FİGÜR ZORUNLU DEĞİL. Payın iki bacağı da kaynağın lira karşılığı
    kalemlerinden geliyor ve o kalemler yüklenemediğinde ölçüm katmanı payı
    hiç hesaplamıyor, uyarı düşürüyor. Yapısal olarak üretilemeyebilen bir
    figürü "zorunlu" saymak, bir figür eksik diye ÇALIŞAN öbür figürlerin de
    siteye kopyalanmamasına yol açardı — bu depoda bir kez tam olarak böyle
    oldu ve on altı çalışan figür bir eksik yüzünden bir ay geride kaldı.

    ÜRETİLMEYEN FİGÜRÜN ESKİ DOSYASI SİLİNİR. Burada bir zamanlar "eksik figür
    atlandı diye görünür ve sayfa o şekli basmaz" yazıyordu; sayfadaki gömme
    STATİKTİR, yani sayfa o şekli basar. Kopya sözleşmesi de diskteki her
    HTML'i joker ile alıyor: üretilmeyen figürün ÖNCEKİ koşudan kalan dosyası
    siteye gider, üstelik ölçüm katmanı o bloğa saat yazmadığı için altına
    tarih hiç basılmaz — bayat figür, bayatlığını gösteren tek işaretten de
    yoksun kalır. Silme işi koşunun sonunda yapılıyor (bkz. kos).

    GERÇEK–TÜZEL AYRIŞMASI BURADA YOK, ÇÜNKÜ ÖLÇÜLEMİYOR. Kaynak lira
    mevduatının gerçek ve tüzel kişi kırılımını yayımlamıyor; payı ikiye
    bölmek için elimizde veri yok ve bölünmüş bir pay uydurulmaz. Bunun
    yazılması, boş bırakılan yerin sebebiyle birlikte durmasıdır.
    """
    if not _olculdu(o, "dol_tarih") or _kol(D, "dol_pay_ham") is None:
        return None
    fig = make_subplots(
        rows=2, cols=1, vertical_spacing=0.11,
        specs=[[{"secondary_y": False}], [{"secondary_y": True}]],
        subplot_titles=(
            "Yabancı para mevduatın toplam mevduat içindeki payı",
            "İki ölçünün farkı ve çıpadan bu yana birikmiş parite etkisi"))

    _cizgi(fig, _kol(D, "dol_pay_ham"), "Ham pay", KISI["gercek"], 1, kalin=2.4,
           birim="%", ondalik=2)
    _cizgi(fig, _kol(D, "dol_pay_ar"),
           "Parite etkisinden arındırılmış pay", AR, 1, kalin=2.4, birim="%",
           ondalik=2)

    _cizgi(fig, _kol(D, "dol_pay_fark"), "Ham eksi arındırılmış (puan)", ARTIK,
           2, kalin=2.0, birim=" puan", ondalik=2)
    _cizgi(fig, _kol(D, "pe_kum_cipa_mn"),
           "Çıpadan bu yana birikmiş parite etkisi (sağ eksen)", PE, 2,
           kalin=1.6, kes="dash", ikincil=True)
    _sifir(fig, 2)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1, secondary_y=False)
    fig.update_yaxes(title_text="milyon dolar", row=2, col=1, secondary_y=True,
                     showgrid=False)

    alt = [
        "Payın iki bacağı da lira cinsindendir (TP.HPBITABLO2.3 ve "
        "TP.HPBITABLO2.6). Ham pay, sepet dolara karşı değer kazandığında "
        "hiçbir hesap değişmeden yükselir; arındırılmış pay bu hareketten "
        "temizlenmiştir.",
        # ÜÇ PAY VE ÇIPA ARTIK ALT YAZIDA KURULUYOR. Koşu kaydının cümlesi
        # yalnız iki ölçünün FARKINI bildiriyor; çıpadaki pay, son haftadaki
        # ham pay ve arındırılmış pay kendi anahtarlarında duruyor — üstelik
        # çıpadaki pay KENDİ saatiyle. Okur üçünü de burada yan yana görür.
        # ÇIPANIN GÜNÜ OKUR YAZIMIYLA: ölçüm katmanının `dol_cipa` alanı ISO
        # yazımdadır (makine kaydı) ve okura basılamaz; okur yazımı ayrı bir
        # alanda duruyor ve biçim sözleşmesi tek yerden geliyor.
        (f"Dolarizasyon payı {o.get('dol_cipa_etiket', '—')} çıpasında "
         f"{_yz(o, 'dol_pay_cipa', 1)}, son haftada {_yz(o, 'dol_pay_ham', 1)}; "
         f"aynı haftada arındırılmış pay {_yz(o, 'dol_pay_ar', 1)}. "
         if o.get("dol_pay_ar") is not None else
         "Arındırılmış pay bu koşuda kurulamadı; şekilde yalnız ham pay "
         "görünüyor. ")
        + (o.get("dol_cumlesi") or ""),
        "Arındırma için kur serisi kullanılmadı: yabancı para bacağı, resmî "
        "parite etkisinin çıpadan bu yana birikmiş toplamı stoktan düşülerek "
        "ölçeklendi. Oran birimsizdir ve kuru sadeleştirir. Çıpa her takvim "
        "yılında döner, böylece birikmiş fark bir yılla sınırlı kalır.",
        "Liranın dolar karşısındaki hareketi bu ölçünün DIŞINDADIR: kaynağın "
        "arındırdığı şey paritedir, kur değil.",
        "Payın gerçek ve tüzel kişi ayrımı burada yok, çünkü ölçülemiyor: "
        "kaynak lira mevduatının kişi kırılımını yayımlamıyor ve bölünmüş bir "
        "pay uydurulmaz.",
        KAYNAK,
    ]
    return _duzen(fig, f"Dolarizasyon payı: ham ve arındırılmış{_veri(damga)}",
                  alt, n_panel=2)


# ===========================================================================
# koşu
# ===========================================================================
# Panel sayıları KÜNYEDİR ve ÖLÇÜLÜR (bkz. _panel_denetimi): yükseklik
# doğrudan bu sayıdan hesaplanıyor, yani bir figüre panel eklenip burası
# güncellenmezse figür kendi ilan ettiği yükseklikten uzun olur ve gömme onu
# ALTTAN KIRPAR — bu depoda bir kez on bir gömme böyleydi, en kötüsü 200 px, ve
# hiçbir şey ölçmüyordu. Dosya adları burada TEKRARLANMAZ; onların tek kaynağı
# veri.py'deki listedir.
PANEL_SAYISI = {
    "01_stok_kirilim.html": 2,
    "02_kumule_akim.html": 3,
    "03_ayristirma.html": 3,
    "04_para_cinsi.html": 3,
    "05_kimlik.html": 2,
    "06_dolarizasyon.html": 2,
}

# ZORUNLU FİGÜRLER — üretilemezse hat DURUR ve siteye kopyalama yapılmaz.
# Dolarizasyon şekli listede DEĞİL: payın lira bacakları yüklenemediğinde
# ölçüm katmanı çerçeveyi hiç kurmuyor ve bu YAPISAL bir eksiklik. Onu da
# zorunlu saymak, bir bacak eksik diye çalışan beş figürün de siteye
# gitmemesine yol açardı; eksik figür ATLANDI diye görünür ve sayfa o şekli
# basmaz.
ZORUNLU = ("01_stok_kirilim.html", "02_kumule_akim.html", "03_ayristirma.html",
           "04_para_cinsi.html", "05_kimlik.html")


def _panel_denetimi(ad: str, fig) -> None:
    """Figürün gerçekten kaç paneli var — künyedeki sayıyla aynı mı?

    Yükseklik künyedeki panel sayısından hesaplanıyor. Bir figüre panel eklenip
    künye güncellenmezse figür kendi ilan ettiği yükseklikten uzun olur ve
    gömme onu alttan kırpar; kusur göze çarpmaz, koşu yeşil biter. Ölçü
    figürün KENDİSİNDEN alınır (x eksenlerinin sayısı), çünkü çağrı yerindeki
    argümanı ikinci kez okumak aynı hatayı iki kez yapmak olurdu.
    """
    beklenen = PANEL_SAYISI.get(ad)
    if beklenen is None:
        return
    var = len([k for k in fig.layout if re.fullmatch(r"xaxis\d*", k)])
    if var != beklenen:
        raise SystemExit(
            f"DUR: {ad} künyede {beklenen} panelli, figürde {var} panel var. "
            "Yükseklik künyedeki sayıdan hesaplanıyor; ayrışma gömmeyi alttan "
            "kırpar ve bunu hiçbir şey ölçmez.")


def kos() -> None:
    M, A, K, D, o = _yukle()
    # DAMGA FİGÜR BAŞINA, TEK DEFTERDEN. Hattın iki ritmi var (stok tabloları
    # ile değişim tablosu ayrı yayımlanıyor) ve tek bir ana saatle damgalamak
    # iki yönde birden yalan söyler: bayat panel taze görünür, okur tek damgayı
    # sayfanın tamamına yorup taze paneli bayat sanır. Aynı defteri
    # ozet_uret.py sayfa altındaki damga için okur.
    saat = sekil_saatleri(o, uzun=True)
    kisa = sekil_saatleri(o)
    s_h = _bicim().tarihe_cevir(o.get("son_hafta"))
    print("Yurt içi yerleşiklerin YP mevduatı — grafikler"
          + (f" · çıpa {ad_gun(pd.Timestamp(s_h))}" if s_h else ""))
    print(f"  stok bloğu {_gun(o, 'stok_tarih')} · akım bloğu "
          f"{_gun(o, 'akim_tarih')} · dolarizasyon bloğu {_gun(o, 'dol_tarih')}")

    ciktilar = [
        (sekil_01(M, o, saat["01_stok_kirilim.html"]), "01_stok_kirilim.html"),
        (sekil_02(K, o, saat["02_kumule_akim.html"]), "02_kumule_akim.html"),
        (sekil_03(A, o, saat["03_ayristirma.html"]), "03_ayristirma.html"),
        (sekil_04(K, o, saat["04_para_cinsi.html"]), "04_para_cinsi.html"),
        (sekil_05(A, o, saat["05_kimlik.html"]), "05_kimlik.html"),
        (sekil_06(D, o, saat["06_dolarizasyon.html"]), "06_dolarizasyon.html"),
    ]

    # KOŞU SIRASI DA KAYNAK LİSTEYE KARŞI DENETLENİR: bu dosyada figür adı üç
    # yerde daha geçiyor ve "kendi listesini tutmaz" diye yazılı olması onları
    # kaynak listeyle örtüşür yapmıyordu.
    _adlar = [ad for _f, ad in ciktilar]
    if list(veri.SEKIL_DOSYALARI) != _adlar:
        raise SystemExit(
            "DUR: çizilen figür listesi künyedekiyle örtüşmüyor "
            f"({_adlar} ≠ {list(veri.SEKIL_DOSYALARI)}). Dosya adı, kopya "
            "hedefi ve saat defteri anahtarı AYNI dizedir; ayrıştıklarında "
            "sayfa bir figürü bulamaz ya da yanlış damgayla basar.")

    n = 0
    for fig, ad in ciktilar:
        if fig is None:
            print(f"  ATLANDI: {ad} — girdisi üretilemedi (koşu kaydına bakın)")
            # ESKİ DOSYA SİLİNİR. Kopya sözleşmesi diskteki her HTML'i joker
            # ile alıyor; üretilmeyen figürün önceki koşudan kalan dosyası
            # aksi hâlde siteye gider ve ölçüm katmanı o bloğa saat yazmadığı
            # için ALTINA TARİH HİÇ BASILMAZ — bayat bir figür, bayatlığını
            # gösteren tek işaretten de yoksun. Ölçüldü: lira bacakları
            # düşürüldüğünde beş figür tazelendi, altıncısı önceki koşunun
            # damgasıyla yerinde kaldı.
            eski = CIKTI / ad
            if eski.exists():
                eski.unlink()
                print(f"    (önceki koşudan kalan dosya silindi: {ad})")
            continue
        _panel_denetimi(ad, fig)
        _uc_denetimi(ad, kisa[ad], fig)
        _yaz(fig, ad)
        n += 1

    # YÜKSEKLİK TEK KAYNAK. Sayfadaki gömme yüksekliği bu dosyadan alınır;
    # alt başlığa bir satır eklemek figürü 26 px büyütür, yani metni düzenleyen
    # her değişiklik yüksekliği de değiştirir ve elle yazılmış bir sayı
    # sessizce eskir — gömme grafiği alttan kırpar ve bunu hiçbir şey ölçmez.
    (CIKTI / "yukseklikler.json").write_text(json.dumps(
        {ad: int(fig.layout.height) for fig, ad in ciktilar if fig is not None},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {n}/{len(ciktilar)} grafik yazıldı → {CIKTI}")

    eksik = [ad for fig, ad in ciktilar if fig is None and ad in ZORUNLU]
    if eksik:
        # SESSİZ BAYATLAMA YASAK: bir figür üretilemezse eskisi sitede yerinde
        # kalır ve sayfanın metni tazelenir — grafik bayat, metin taze, koşu
        # yeşil. Bu yüzden zorunlu bir figür eksikse hat DURUR.
        raise SystemExit(
            f"DUR: {len(eksik)} zorunlu figür üretilemedi "
            f"({', '.join(eksik)}). Siteye kopyalama YAPILMAZ — eski grafikle "
            "taze metin yayımlanmasın. Sebebi için koşu kaydına bakın.")


if __name__ == "__main__":
    kos()
