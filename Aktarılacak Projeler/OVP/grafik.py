# -*- coding: utf-8 -*-
"""OVP hattı — grafik katmanı (Plotly, site ev stili).

HATTIN SORUSU, FİGÜRLERİN DİLİNDE
---------------------------------
Program bir kur patikası yayımlamıyor; iki GSYH satırının oranı onu ele
veriyor. Figürler bu ima edilen patikayı, onun gerçekleşenle olan mesafesini
ve "programın tutması için bundan sonra ne olmalı" sorusunun bugünkü cevabını
anlatır. Hiçbiri seri dökümü değildir: her figür bir SORUYA cevap verir.

  01  İma edilen ortalama kur — iki program ve gerçekleşen yıllık ortalamalar.
      İkinci panel YÖNTEM SINAMASIDIR: kapanmış yıllarda ima ile gerçekleşenin
      farkı. Bu panel olmadan birinci panel bir VARSAYIM üzerine kurulu olurdu
      ("ima edilen kur, USD/TRY ortalamasıdır"); onunla birlikte bir ÖLÇÜM.
  02  İçinde bulunulan yıl — cevabı her gün değişen soru. Kalan günlerin
      tutturması gereken ortalama ve iki patika varsayımı.
  03  Yıl sonu imaları ve devalüasyon — zincirlenmiş patika, iki program.
  04  Enflasyon tarafı: TÜFE patikası, deflatör−TÜFE makası ve faiz giderinin
      nominal gelire göre artışı. Üçü aynı figürde, çünkü üçü de nominal
      GSYH'nin — yani ima edilen kurun paydasının — bileşenleri.
  05  Reel TL: devalüasyon ile enflasyonun farkı, yıl yıl ve kümüle.
  06  Taşıma: gerçekleşen kümüle iz ve ileriye dönük yıllık getiri.
  07  Revizyon: iki programın ortak yıllarında satır satır fark. İki panel,
      çünkü İKİ AYRI BİRİM var — seviye satırları yüzde, oran satırları puan
      revize olur ve ikisini aynı eksende çizmek birini görünmez yapardı.

EV STİLİ SÖZLEŞMESİ
-------------------
  · Paneller ALT ALTA (rows=N, cols=1). YAN YANA PANEL YOK.
  · Panel başına ~340 px; yükseklik tek kaynak cikti/yukseklikler.json.
  · Başlık solda, açıklama satırları başlık bloğunda <sup> ile. Figür içi
    sabit konumlu dipnot KONMAZ (ev stili lejantı alt kenara yapıştırıyor).
  · Üst marj GEREKENDEN BİR EKSİK yazılır; ev stili kendi hesabıyla tamamlar.
  · Her figürün başlığında KENDİ veri ucu vardır — hattın ana saati değil.
    Ölçülemeyen uçta tarih HİÇ yazılmaz.
  · Figür metni OKURA basılır: dosya adı, sütun adı ve kendi sürüm tarihçemiz
    oraya girmez; sayı ortak/bicim ile yazılır.

Koşum:  python3 grafik.py   (önce veri.py → metrik.py)
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import veri
from veri import VERI, SEKIL_DOSYALARI, ZORUNLU_SEKIL, sekil_saatleri

CIKTI = veri.PROJE / "cikti"
CIKTI.mkdir(exist_ok=True)


def _bicim():
    try:
        import bicim
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


# --------------------------------------------------------------------------- jetonlar
TEAL, CLARET, GOLD, INK, GRID = "#1d5c5c", "#8e1f2f", "#9a7327", "#1a1a1a", "#e8e4dc"
LACI, MOR, YESIL, GRI = "#2f4b7c", "#665191", "#7a9e7e", "#8a8a8a"

# RENK BİR SÖZLÜKTÜR: aynı kavram bütün figürlerde aynı renkte. İki boyut var
# ve aralarında renk ödünç alınmaz — yoksa okur ikinci figürde birinci figürün
# anlamını arar.
#   (1) KAYNAK boyutu — sayı hangi programdan ya da gerçekleşmeden geliyor
PROG = {"yeni": CLARET, "eski": LACI, "gerceklesen": INK}
#   (2) BÜYÜKLÜK boyutu — hangi ölçü
OLCU = {"kur": CLARET, "tufe": TEAL, "reel": MOR, "faiz": GOLD, "nominal": GRI}

PANEL_PX = 340
SATIR_SINIR = 150

KAYNAK_EK = ("Gerçekleşen kur: TCMB gösterge niteliğindeki alış kuru "
             "(TP.DK.USD.A.YTL), günlük.")


# --------------------------------------------------------------------------- metin
def _sy(v, ondalik: int = 1, isaret: bool = False) -> str:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return "—"
    return _bicim().sayi(v, ondalik, isaret)


def _yz(v, ondalik: int = 1, isaret: bool = False) -> str:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return "—"
    return _bicim().yuzde(v, ondalik, isaret)


def _bol(metin: str, sinir: int = SATIR_SINIR) -> list[str]:
    """Uzun alt başlık satırını KELİME sınırından böler; Plotly sarmıyor."""
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


def _veri_eki(damga: str | None) -> str:
    """Başlıktaki " · veri <damga>" eki — ölçülemeyen damgada HİÇ yazılmaz.

    Damga birleşik olabilir ("program 09.2025 · gerçekleşen 03.09.2026"):
    program tablosu ile canlı kur arasında bir yıla varan mesafe var ve tek
    bir uçla dürüst anlatılamaz. Bileşen tanımadığı dizgeyi olduğu gibi basar.
    """
    return f" · veri {damga}" if damga else ""


def _duzen(fig, baslik: str, alt: list[str], n_panel: int,
           y_baslik: str = "", barmode: str | None = None,
           ek_yukseklik: int = 0) -> go.Figure:
    """Ev stili düzeni ve YÜKSEKLİK — MDX ile tek kaynak.

    ÜST MARJ BİR EKSİK YAZILIR: ev stili üst marjı önce koşulsuz 92'ye çeker,
    sonra YALNIZCA mevcut değer gerekenden küçükse yükseltir; doğru değeri
    buraya yazmak o düzeltmeyi devre dışı bırakır ve başlık panele biner.
    """
    alt = [parca for satir in alt for parca in _bol(satir)]
    l_satir = _lejant_satir(fig)
    ust = 92 + 26 * len(alt) + 25
    b = 110 + max(0, l_satir - 1) * 24
    h = PANEL_PX * n_panel + ust + b + ek_yukseklik
    metin = f"<b>{baslik}</b>" + "".join(f"<br><sup>{x}</sup>" for x in alt)
    gereken_t = 92 + 26 * len(alt) + 26
    blok_px = 22 + 19 * len(alt)
    dolgu_t = int(max(12, (gereken_t - blok_px) / 2))
    fig.update_layout(
        title=dict(text=metin, x=0, xanchor="left", y=1.0, yanchor="top",
                   yref="container", pad=dict(t=dolgu_t, l=0),
                   font=dict(size=15, color=INK, family="Georgia, serif")),
        height=h, plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Georgia, serif", size=12, color=INK),
        # Figürün İÇİNDEKİ sayı da Türkçe yazılır: ondalık virgül, binlik
        # nokta. Sayfa metni aynı sayıyı böyle yazıyor; iki yazımı yan yana
        # görmek okuru iki ayrı büyüklük var sanmaya iter.
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
    """İpucu metni — YÜZDE İŞARETİ SAYIDAN ÖNCE (biçim sözleşmesi)."""
    if birim == "%":
        govde = f"yüzde %{{y:,.{ondalik}f}}"
    else:
        govde = f"%{{y:,.{ondalik}f}}{birim}"
    return f"{govde}<extra>{ad}</extra>"


def _cizgi(fig, x, y, ad: str, renk: str, satir: int = 1, kalin: float = 2.0,
           kes: str | None = None, birim: str = "", ondalik: int = 2,
           mod: str = "lines", gorunur: bool = True, sembol: str = "circle") -> None:
    if x is None or y is None or len(x) == 0:
        return
    fig.add_trace(go.Scatter(
        x=list(x), y=list(y), name=ad, mode=mod, showlegend=gorunur,
        line=dict(color=renk, width=kalin, dash=kes),
        marker=dict(color=renk, size=7, symbol=sembol),
        hovertemplate=_sablon(ad, birim, ondalik)),
        row=satir, col=1)


def _cubuk(fig, x, y, ad: str, renk: str, satir: int = 1, birim: str = "",
           ondalik: int = 2, opaklik: float = 0.85, gorunur: bool = True) -> None:
    if x is None or y is None or len(x) == 0:
        return
    fig.add_trace(go.Bar(
        x=list(x), y=list(y), name=ad, marker_color=renk, opacity=opaklik,
        showlegend=gorunur, hovertemplate=_sablon(ad, birim, ondalik)),
        row=satir, col=1)


def _sifir(fig, satir: int = 1) -> None:
    fig.add_hline(y=0, line=dict(color=GRI, width=1), row=satir, col=1)


def _yaz(fig, ad: str) -> pathlib.Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", full_html=True,
                   config={"responsive": True, "displaylogo": False})
    print(f"  yazıldı: cikti/{ad}  (yükseklik {fig.layout.height})")
    return yol


# --------------------------------------------------------------------------- veri
def _yukle():
    """Girdi, ölçüm katmanının ÜRETTİĞİ dosyalardan gelir.

    Bir dosya okunuyorsa onu üreten adım hattın adım listesinde GÖRÜNMELİDİR;
    burada okunan her şeyi metrik.py yazıyor (guncelle.py kütüğündeki sıra:
    veri.py → metrik.py → grafik.py → ozet_uret.py). Ölü bir bağımlılık kırık
    olandan tehlikelidir: dosya vardır, okunur, hata vermez, yalnız yaşlanır.
    """
    o = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    K = pd.read_csv(VERI / "kur.csv", index_col=0, parse_dates=True)
    C = (pd.read_csv(VERI / "metrik_carry.csv", index_col=0, parse_dates=True)
         if (VERI / "metrik_carry.csv").exists() else pd.DataFrame())
    return o, K, C


def _olculdu(o: dict, *anahtarlar: str) -> bool:
    """Bu KOŞUDA ölçüldü mü — dosyanın varlığı ölçümün kanıtı değildir."""
    return all(o.get(a) for a in anahtarlar)


def _yil_dizi(d: dict) -> tuple[list[int], list[float]]:
    """{"2026": 46.8} → ([2026], [46.8]); yıl sırasıyla."""
    yillar = sorted(int(y) for y in d)
    return yillar, [d[str(y)] for y in yillar]


# ===========================================================================
#  01 — İMA EDİLEN ORTALAMA KUR + YÖNTEM SINAMASI
# ===========================================================================
def sekil_01(o: dict, damga: str | None):
    ima = o.get("ima") or {}
    yeni, eski = o["program_yeni"], o["program_eski"]
    if yeni["kod"] not in ima:
        return None
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False,
                        vertical_spacing=0.13,
                        subplot_titles=(
                            "İma edilen ortalama kur ve gerçekleşen yıllık ortalama",
                            "Yöntem sınaması: kapanmış yıllarda ima ile gerçekleşenin farkı"))
    for tur, kod in (("yeni", yeni["kod"]), ("eski", eski["kod"])):
        if kod not in ima:
            continue
        x, y = _yil_dizi(ima[kod])
        ad = (yeni if tur == "yeni" else eski)["kisa"]
        _cizgi(fig, x, y, f"{ad} iması", PROG[tur], 1, mod="lines+markers",
               birim=" lira", ondalik=2,
               kes=None if tur == "yeni" else "dash")
    ger = [g for g in (o.get("gerceklesen_yil") or []) if g["n"] >= 200]
    if ger:
        _cizgi(fig, [g["yil"] for g in ger], [g["ortalama"] for g in ger],
               "Gerçekleşen yıllık ortalama", PROG["gerceklesen"], 1,
               mod="markers", birim=" lira", ondalik=2, sembol="diamond")
    # Yılın TAMAMI dolmadan hesaplanan ortalama yıl ortalaması DEĞİLDİR; ayrı
    # sembol ve ayrı adla çizilir, yoksa okur onu kapanmış bir yılın
    # ortalamasıyla aynı kefeye koyar.
    kismi = [g for g in (o.get("gerceklesen_yil") or []) if g["n"] < 200]
    if kismi:
        _cizgi(fig, [g["yil"] for g in kismi], [g["ortalama"] for g in kismi],
               "Yıl içi ortalama (yıl kapanmadı)", GRI, 1, mod="markers",
               birim=" lira", ondalik=2, sembol="x")
    ys = o.get("yontem") or []
    if ys:
        _cubuk(fig, [f"{r['program_kisa']} · {r['yil']}" for r in ys],
               [r["fark_yuzde"] for r in ys], "İma − gerçekleşen", TEAL, 2,
               birim="%", ondalik=3)
        esik = o.get("yontem_esik_yuzde")
        if esik:
            for isaret in (esik, -esik):
                fig.add_hline(y=isaret, line=dict(color=CLARET, width=1,
                                                  dash="dot"), row=2, col=1)
    _sifir(fig, 2)
    fig.update_yaxes(title_text="lira", row=1, col=1)
    fig.update_yaxes(title_text="yüzde fark", row=2, col=1)
    fig.update_xaxes(title_text="yıl", row=1, col=1, dtick=1)
    alt = [
        "İma edilen ortalama kur, programın TL cinsinden gayrisafi yurt içi "
        "hasılasının dolar cinsinden hasılasına bölünmesidir. Program bir kur "
        "patikası yayımlamaz; bu oran onu ele verir.",
        "Alt panel, hükmün kendisini sınar. Programın dipnotu milli gelir "
        "hesabında ihracat-ithalat ağırlıklı kur kullanıldığını söylüyor, düz "
        "dolar-lira kuru değil. Sınamaya yalnız KAPANMIŞ ve gerçekleşme olarak "
        "yayımlanmış yıllar girer: gerçekleşme tahmini sütunundaki fark yöntem "
        "farkı değil tahmin hatasıdır.",
        KAYNAK_EK,
        f"Kaynak: {yeni['kaynak']} · {eski['kaynak']}",
    ]
    return _duzen(fig, f"Programın ima ettiği ortalama kur{_veri_eki(damga)}",
                  alt, n_panel=2)


# ===========================================================================
#  02 — İÇİNDE BULUNULAN YIL
# ===========================================================================
def sekil_02(o: dict, K: pd.DataFrame, damga: str | None):
    yeni = o["program_yeni"]
    bu = (o.get("bu_yil_olcum") or {}).get(yeni["kod"])
    if not bu or "usdtry" not in K.columns:
        return None
    b = _bicim()
    yil = bu["yil"]
    s = K["usdtry"].dropna()
    s = s[s.index.year == yil]
    if s.empty:
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13,
                        subplot_titles=(
                            f"{yil} kuru ve programın tutması için gereken patika",
                            "Yıl içi ortalama, programın ortalamasına doğru"))
    _cizgi(fig, s.index, s.values, "Gerçekleşen kur", PROG["gerceklesen"], 1,
           birim=" lira", ondalik=4)
    fig.add_hline(y=bu["ovp_ortalama"], line=dict(color=PROG["yeni"], width=1.5,
                                                  dash="dash"), row=1, col=1)
    if bu.get("gereken_ortalama"):
        fig.add_hline(y=bu["gereken_ortalama"],
                      line=dict(color=GOLD, width=1.5, dash="dot"), row=1, col=1)
        # KALAN GÜNLERİN İKİ PATİKASI. İkisi de AYNI ortalamayı tutturuyor;
        # aralarındaki fark yalnız patikanın bükümünden geliyor ve o farkın
        # küçük çıkması bir SONUÇTUR — yıl sonu iması patika varsayımına
        # duyarlı değil. Okur bunu ancak iki iz birden çizilirse görebilir.
        son_g = pd.Timestamp(bu["son_gun"])
        n = int(bu["kalan_gun"])
        gunler = pd.bdate_range(son_g + pd.Timedelta(days=1), periods=n)
        for ad, uc, renk, kes in (
                ("Doğrusal patika", bu.get("yil_sonu_dogrusal"), TEAL, "dash"),
                ("Üstel patika", bu.get("yil_sonu_ustel"), MOR, "dot")):
            if not uc:
                continue
            if ad.startswith("Doğrusal"):
                yol = np.linspace(bu["son_kur"], uc, n + 1)[1:]
            else:
                g = (uc / bu["son_kur"]) ** (1 / n)
                yol = bu["son_kur"] * g ** np.arange(1, n + 1)
            _cizgi(fig, gunler, yol, ad, renk, 1, kalin=1.6, kes=kes,
                   birim=" lira", ondalik=2)
    # Yıl içi kümülatif ortalama: her günün soluna kadar gerçekleşenin
    # ortalaması. Yıl sonuna doğru programın ortalamasına yakınsıyorsa
    # program tutuyor demektir; ayrışma büyüyorsa tutmuyor.
    kum = s.expanding().mean()
    _cizgi(fig, kum.index, kum.values, "Yıl içi ortalama (birikimli)", TEAL, 2,
           birim=" lira", ondalik=3)
    fig.add_hline(y=bu["ovp_ortalama"], line=dict(color=PROG["yeni"], width=1.5,
                                                  dash="dash"), row=2, col=1)
    fig.update_yaxes(title_text="lira", row=1, col=1)
    fig.update_yaxes(title_text="lira", row=2, col=1)
    alt = [
        f"{yeni['kisa']} {yil} için ortalama kuru {_sy(bu['ovp_ortalama'], 3)} "
        f"lira ima ediyor (kesikli koyu çizgi). Yılın ilk "
        f"{_sy(bu['n_gerceklesen'], 0)} işlem gününde gerçekleşen ortalama "
        f"{_sy(bu['gerceklesen_ortalama'], 3)} lira, yani imanın "
        f"{_yz(bu['sapma_yuzde'], 1, True)} uzağında.",
        (f"Programın tutması için kalan {_sy(bu['kalan_gun'], 0)} işlem gününün "
         f"ortalaması {_sy(bu.get('gereken_ortalama'), 3)} lira olmalı (noktalı "
         f"çizgi) — bugünkü {_sy(bu['son_kur'], 4)} liranın "
         f"{_yz(bu.get('gereken_bugune_gore_yuzde'), 1, True)} üstü."
         if bu.get("gereken_ortalama") else
         "Yıl kapandığı için kalan gün yok; gereken ortalama sorusu bu koşuda "
         "sorulmuyor."),
        (f"Kalan günlerin ortalaması bilindiğinde yıl sonu seviyesi hâlâ "
         f"patika varsayımına bağlı. Doğrusal patika {_sy(bu.get('yil_sonu_dogrusal'), 2)}, "
         f"üstel patika {_sy(bu.get('yil_sonu_ustel'), 2)} lira veriyor; aradaki "
         f"fark {_yz(bu.get('patika_farki_yuzde'), 3)}. İkisinin bu kadar yakın "
         "çıkması bir sonuçtur: yıl sonu iması, patikanın biçimine değil "
         "ortalamaya bağlı."
         if bu.get("yil_sonu_ustel") else ""),
        (f"Kalan gün sayısı hafta içi günlerdir; resmî tatiller düşülmedi, "
         f"çünkü gelecekteki tatilleri saymak bir varsayım olurdu. Geçmiş "
         f"{_sy(bu.get('kalan_tatil_ornek_yil'), 0)} yılda aynı takvim "
         f"penceresinde ortanca {_sy(bu.get('kalan_tatil_payi'), 0)} hafta içi "
         f"gün gözlemsiz kalmış; o kadar gün düşülseydi gereken ortalama "
         f"{_sy(bu.get('gereken_ortalama_tatilsiz'), 3)} lira olurdu."
         if bu.get("kalan_tatil_payi") is not None else ""),
        KAYNAK_EK,
    ]
    return _duzen(fig, f"İçinde bulunulan yıl: gerçekleşen ile programın "
                       f"arası{_veri_eki(damga)}",
                  [a for a in alt if a], n_panel=2)


# ===========================================================================
#  03 — YIL SONU İMALARI VE DEVALÜASYON
# ===========================================================================
def sekil_03(o: dict, damga: str | None):
    z = o.get("zincir") or {}
    yeni, eski = o["program_yeni"], o["program_eski"]
    if not z.get(yeni["kod"]):
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13,
                        subplot_titles=("Zincirlenmiş yıl sonu seviyeleri",
                                        "Yıl sonundan yıl sonuna devalüasyon"))
    for tur, kod in (("yeni", yeni["kod"]), ("eski", eski["kod"])):
        satirlar = z.get(kod) or []
        if not satirlar:
            continue
        ad = (yeni if tur == "yeni" else eski)["kisa"]
        # Zincirin GİRİŞİ, ilk yılın başındaki gerçek kapanıştır: patika
        # oradan başlar ve okur nereden başladığını görmeli.
        x = [satirlar[0]["yil"] - 1] + [r["yil"] for r in satirlar]
        y = [satirlar[0]["giris"]] + [r["cikis"] for r in satirlar]
        _cizgi(fig, x, y, f"{ad} yıl sonu iması", PROG[tur], 1,
               mod="lines+markers", birim=" lira", ondalik=2,
               kes=None if tur == "yeni" else "dash")
        _cubuk(fig, [r["yil"] for r in satirlar],
               [r["deval_yuzde"] for r in satirlar], f"{ad}", PROG[tur], 2,
               birim="%", ondalik=1)
    _sifir(fig, 2)
    fig.update_yaxes(title_text="lira", row=1, col=1)
    fig.update_yaxes(title_text="yüzde", row=2, col=1)
    fig.update_xaxes(title_text="yıl", row=1, col=1, dtick=1)
    ilk = (z.get(yeni["kod"]) or [{}])[0]
    alt = [
        "Zincir, her yılın çıkışını sonraki yılın girişi yapar. İçinde "
        "bulunulan yılın çıkışı, kalan günlerin tutturması gereken ortalamadan "
        "üstel patika varsayımıyla çözülür; sonraki yıllarda giriş bellidir ve "
        "yıl sonu, programın ima ettiği ortalamayı tutturan patikadan gelir.",
        (f"Zincirin başlangıcı {_sy(ilk.get('giris'), 4)} lira — "
         f"{ilk.get('yil', 0) - 1} yılının kapanışı, ölçülmüş bir gözlem."
         if ilk.get("giris") else ""),
        "Devalüasyon paneli yıl sonundan yıl sonuna değişimdir; yıl "
        "ortalamasındaki değişim değil. İkisi aynı şey değildir ve program "
        "yalnız ortalamayı ima ettiği için yıl sonu bir çıkarımdır.",
        f"Kaynak: {yeni['kaynak']} · {eski['kaynak']}",
    ]
    return _duzen(fig, f"Yıl sonu imaları ve devalüasyon{_veri_eki(damga)}",
                  [a for a in alt if a], n_panel=2, barmode="group")


# ===========================================================================
#  04 — ENFLASYON TARAFI
# ===========================================================================
def sekil_04(o: dict, damga: str | None):
    yeni, eski = o["program_yeni"], o["program_eski"]
    fg = (o.get("faiz_gideri") or {}).get(yeni["kod"]) or []
    if not fg:
        return None
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.09,
                        subplot_titles=(
                            "Yıl sonu tüketici enflasyonu: iki program ve gerçekleşen",
                            "Deflatör ile tüketici enflasyonu arasındaki makas",
                            "Faiz gideri ile nominal gelirin artışı"))
    kayit = veri.programlar()
    for tur, blok in (("yeni", yeni), ("eski", eski)):
        p = veri.program(kayit, blok["kod"])
        tufe = veri.satir_serisi(p, "tufe")
        _cizgi(fig, sorted(tufe), [tufe[y] for y in sorted(tufe)],
               f"{blok['kisa']} tüketici enflasyonu", PROG[tur], 1,
               mod="lines+markers", birim="%", ondalik=1,
               kes=None if tur == "yeni" else "dash")
        de = veri.satir_serisi(p, "deflator")
        ortak = sorted(set(de) & set(tufe))
        _cubuk(fig, ortak, [de[y] - tufe[y] for y in ortak],
               f"{blok['kisa']} makası", PROG[tur], 2, birim=" puan", ondalik=1)
    ger = o.get("tufe_gerceklesen") or {}
    if ger:
        x, y = _yil_dizi(ger)
        _cizgi(fig, x, y, "Gerçekleşen yıl sonu enflasyonu", PROG["gerceklesen"],
               1, mod="markers", birim="%", ondalik=2, sembol="diamond")
    _cubuk(fig, [r["yil"] for r in fg if "faiz_gideri_yuzde" in r],
           [r["faiz_gideri_yuzde"] for r in fg if "faiz_gideri_yuzde" in r],
           "Faiz gideri artışı", OLCU["faiz"], 3, birim="%", ondalik=1)
    _cizgi(fig, [r["yil"] for r in fg if "nominal_gsyh_yuzde" in r],
           [r["nominal_gsyh_yuzde"] for r in fg if "nominal_gsyh_yuzde" in r],
           "Nominal gelir artışı", OLCU["nominal"], 3, mod="lines+markers",
           birim="%", ondalik=1)
    _sifir(fig, 2)
    fig.update_yaxes(title_text="yüzde", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    fig.update_yaxes(title_text="yüzde", row=3, col=1)
    alt = [
        "Üç panel de nominal gelirin bileşenleri: deflatör ile tüketici "
        "enflasyonu arasındaki makas nominal geliri büyütür, nominal gelir de "
        "dolar hedefi sabitken ima edilen kuru yukarı çeker.",
        "Deflatör bütün yurt içi üretimin fiyatını, tüketici enflasyonu "
        "hanenin sepetini ölçer; ikisi arasındaki farkın işareti tesadüf "
        "değildir ve programın bütün yıllarında aynı yöndedir.",
        "Üçüncü panel bir faiz patikası DEĞİLDİR: program sayısal bir politika "
        "faizi yayımlamıyor. Ölçülen şey iki yayımlanmış bütçe satırının "
        "büyüme farkı — faiz gideri nominal gelirden hızlı artıyorsa borcun "
        "ortalama maliyeti nominal büyümenin üstünde kalıyor demektir.",
        f"Kaynak: {yeni['kaynak']} · {eski['kaynak']} · gerçekleşen enflasyon "
        "Türkiye İstatistik Kurumu tüketici fiyat endeksi.",
    ]
    return _duzen(fig, f"Enflasyon, deflatör ve faiz gideri{_veri_eki(damga)}",
                  alt, n_panel=3)


# ===========================================================================
#  05 — REEL TL
# ===========================================================================
def sekil_05(o: dict, damga: str | None):
    z = o.get("zincir") or {}
    km = o.get("kumule") or {}
    yeni, eski = o["program_yeni"], o["program_eski"]
    if not z.get(yeni["kod"]):
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13,
                        subplot_titles=(
                            "Yıl yıl reel lira değişimi (enflasyon ve devalüasyon)",
                            "Zincirin toplamı: kur, enflasyon ve reel lira"))
    for tur, blok in (("yeni", yeni), ("eski", eski)):
        satirlar = [r for r in (z.get(blok["kod"]) or []) if "reel_tl_yuzde" in r]
        if not satirlar:
            continue
        _cubuk(fig, [r["yil"] for r in satirlar],
               [r["reel_tl_yuzde"] for r in satirlar], f"{blok['kisa']}",
               PROG[tur], 1, birim="%", ondalik=1)
    etiket, deger, renk = [], [], []
    for tur, blok in (("yeni", yeni), ("eski", eski)):
        k = km.get(blok["kod"]) or {}
        if not k.get("kur_yuzde"):
            continue
        for ad, anahtar, r in (("kur", "kur_yuzde", OLCU["kur"]),
                               ("enflasyon", "tufe_yuzde", OLCU["tufe"]),
                               ("reel lira", "reel_tl_yuzde", OLCU["reel"])):
            if k.get(anahtar) is None:
                continue
            etiket.append(f"{blok['kisa']}<br>{k['bas_yil'] - 1}→{k['son_yil']} · {ad}")
            deger.append(k[anahtar])
            renk.append(r)
    if etiket:
        fig.add_trace(go.Bar(x=etiket, y=deger, marker_color=renk,
                             showlegend=False, name="",
                             hovertemplate="yüzde %{y:,.1f}<extra></extra>"),
                      row=2, col=1)
    _sifir(fig, 1)
    _sifir(fig, 2)
    fig.update_yaxes(title_text="yüzde", row=1, col=1)
    fig.update_yaxes(title_text="yüzde", row=2, col=1)
    fig.update_xaxes(title_text="yıl", row=1, col=1, dtick=1)
    alt = [
        "Reel lira değişimi ÇARPIMSAL ölçülür: bir artı enflasyonun bir artı "
        "devalüasyona bölümü, eksi bir. Yüzde otuzların üstündeki oranlarda "
        "\"enflasyon eksi devalüasyon\" çıkarması puanlarca sapar.",
        "Artı değer, liranın dolar karşısında reel olarak değer kazandığını "
        "söyler: iç fiyatlar kurdan hızlı artıyor demektir. Bu bir reel efektif "
        "kur ölçüsü DEĞİLDİR — tek para birimine karşı, tek fiyat endeksiyle.",
        f"Kaynak: {yeni['kaynak']} · {eski['kaynak']}",
    ]
    return _duzen(fig, f"Programın ima ettiği reel lira{_veri_eki(damga)}",
                  alt, n_panel=2, barmode="group")


# ===========================================================================
#  06 — TAŞIMA
# ===========================================================================
def sekil_06(o: dict, C: pd.DataFrame, damga: str | None):
    c = o.get("carry") or {}
    ger = c.get("gerceklesen")
    ileri = c.get("ileri") or []
    if not ger and not ileri:
        return None
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13,
                        subplot_titles=(
                            "Gerçekleşen taşıma: lira faizi, kur ve net getiri",
                            "Programın ima ettiği devalüasyona karşı ileriye dönük taşıma"))
    if not C.empty:
        for kol, ad, renk in (("tl_yuzde", "Lira gecelik bileşik getiri", OLCU["faiz"]),
                              ("kur_yuzde", "Kur değişimi", OLCU["kur"]),
                              ("net_yuzde", "Net (dolar bazında)", OLCU["reel"])):
            if kol in C.columns:
                _cizgi(fig, C.index, C[kol].values, ad, renk, 1, birim="%",
                       ondalik=2)
    if ileri:
        _cubuk(fig, [r["yil"] for r in ileri], [r["basit_yuzde"] for r in ileri],
               "Basit yıllık (faiz ÷ devalüasyon)", TEAL, 2, birim="%", ondalik=1)
        _cubuk(fig, [r["yil"] for r in ileri], [r["bilesik_yuzde"] for r in ileri],
               "Gecelikte dönerek (bileşik)", MOR, 2, birim="%", ondalik=1)
    _sifir(fig, 1)
    _sifir(fig, 2)
    fig.update_yaxes(title_text="yüzde", row=1, col=1)
    fig.update_yaxes(title_text="yüzde", row=2, col=1)
    faiz = c.get("faiz_varsayimi")
    alt = [
        (f"Yılbaşından bu yana lira gecelikte {_yz(ger.get('tl_yuzde'), 2)} "
         f"getirdi (ortalama gecelik oran {_yz(ger.get('ortalama_gecelik'), 2)}), "
         f"kur {_yz(ger.get('kur_yuzde'), 2)} yükseldi; dolar bazında net "
         f"{_yz(ger.get('net_yuzde'), 2, True)}, yıllığa çevrilince "
         f"{_yz(ger.get('yillik_yuzde'), 2, True)}."
         if ger else
         "Gerçekleşen taşıma bu koşuda ölçülemedi: lira gecelik faiz serisi "
         "elde yok."),
        "Lira bacağı gözlem günleri üzerinden bileşiklenir: her kotasyon bir "
        "günlük faiz taşır, hafta sonu ayrıca eklenmez.",
        (f"Alt panel BİR VARSAYIM taşır ve varsayım şudur: lira faizi bugünkü "
         f"{_yz(faiz, 2)} seviyesinde SABİT kalır. Program bir faiz patikası "
         f"yayımlamıyor, biz de uydurmuyoruz — sonuç, faiz sabitken programın "
         f"kendi devalüasyon imasına karşı ne kazanılacağıdır."
         if faiz is not None else
         "İleriye dönük taşıma bu koşuda hesaplanmadı: lira faizi elde yok."),
        "İki çubuk iki konvansiyondur. Basit olan yıllık faiz kotasyonunun "
        "yıllık devalüasyona bölünmesi — sayfadaki ex-ante reel faizle aynı "
        "konvansiyon. Bileşik olan gecelikte dönen bir pozisyonun gerçekten "
        "biriktirdiği getiri — üst paneldeki gerçekleşen bacakla aynı "
        "konvansiyon. Tek konvansiyon yazılsaydı iki sayıdan biri öbürüyle "
        "kıyaslanamaz olurdu.",
        KAYNAK_EK + " Lira gecelik faiz: Türk Lirası gecelik referans faiz oranı.",
    ]
    return _duzen(fig, f"Taşıma: gerçekleşen ve ileriye dönük{_veri_eki(damga)}",
                  [a for a in alt if a], n_panel=2, barmode="group")


# ===========================================================================
#  07 — REVİZYON
# ===========================================================================
# Revizyon haritasında GÖSTERİLECEK kalemler. Bütün satırlar ölçülür ve
# çerçeveye yazılır (metrik_revizyon.csv); figüre yalnız hattın sorusunu
# ilgilendirenler girer, çünkü otuz beş satırlık bir ısı haritası okunmaz.
# Liste İKİYE bölünür ve bölünme zorunludur: seviye satırları YÜZDE, oran
# satırları PUAN revize olur; ikisini aynı eksende çizmek birini görünmez,
# ötekini devasa gösterirdi.
REV_YUZDE = ("ima_kur", "gsyh_tl", "gsyh_usd", "ihracat", "ithalat",
             "faiz_gideri", "cari")
REV_PUAN = ("tufe", "deflator", "buyume", "cari_gsyh", "faiz_gideri_gsyh",
            "issizlik")
# Kalem renkleri AÇIKÇA verilir. Plotly'nin kendi döngüsüne bırakılsaydı aynı
# kalem iki panelde iki ayrı renk alırdı ve renk bu sayfada bir sözlük.
# İma edilen kur ilk sırada ve claret: hattın sorusu odur.
REV_RENK = (CLARET, LACI, TEAL, GOLD, MOR, YESIL, GRI)


def sekil_07(o: dict, damga: str | None):
    rev = o.get("revizyon") or []
    if not rev:
        return None
    yeni, eski = o["program_yeni"], o["program_eski"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13,
                        subplot_titles=(
                            "Seviye satırlarının revizyonu (yüzde)",
                            "Oran satırlarının revizyonu (puan)"))
    for satir, kalemler in ((1, REV_YUZDE), (2, REV_PUAN)):
        yillar = sorted({r["yil"] for r in rev if r["kalem"] in kalemler})
        for i, kalem in enumerate(kalemler):
            kayitlar = {r["yil"]: r for r in rev if r["kalem"] == kalem}
            if not kayitlar:
                continue
            ad = next(iter(kayitlar.values()))["ad"]
            _cubuk(fig, yillar,
                   [kayitlar[y]["fark"] if y in kayitlar else None for y in yillar],
                   ad, REV_RENK[i % len(REV_RENK)], satir,
                   birim="%" if satir == 1 else " puan", ondalik=1)
    _sifir(fig, 1)
    _sifir(fig, 2)
    fig.update_yaxes(title_text="yüzde", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    fig.update_xaxes(title_text="yıl", row=1, col=1, dtick=1)
    fig.update_xaxes(title_text="yıl", row=2, col=1, dtick=1)
    ima = [r for r in rev if r["kalem"] == "ima_kur"]
    en = max(ima, key=lambda r: abs(r["fark"])) if ima else None
    alt = [
        f"İki programın ORTAK yıllarında satır satır fark: {yeni['kisa']} eksi "
        f"{eski['kisa']}. Artı değer yukarı revizyondur.",
        (f"En büyük kur revizyonu {en['yil']} yılında: ima edilen ortalama kur "
         f"{_sy(en['eski'], 3)} liradan {_sy(en['yeni'], 3)} liraya, "
         f"{_yz(en['fark'], 1, True)}."
         if en else ""),
        "Birim satıra göre seçilir ve bu bir tercih değil zorunluluktur: yüzde "
        "otuz ile yüzde yirmi sekiz arasındaki fark PUANDIR, iki milli gelir "
        "rakamı arasındaki fark YÜZDEDİR. Aynı eksene konsalardı biri "
        "görünmezdi.",
        f"Kaynak: {yeni['kaynak']} · {eski['kaynak']}",
    ]
    return _duzen(fig, f"İki program arasındaki revizyon{_veri_eki(damga)}",
                  [a for a in alt if a], n_panel=2, barmode="group")


# ===========================================================================
#  koşu
# ===========================================================================
# Panel sayıları KÜNYEDİR ve ÖLÇÜLÜR: yükseklik doğrudan bu sayıdan
# hesaplanıyor, yani bir figüre panel eklenip burası güncellenmezse figür kendi
# ilan ettiği yükseklikten uzun olur ve gömme onu ALTTAN KIRPAR. Dosya adları
# burada TEKRARLANMAZ; tek kaynak veri.SEKIL_DOSYALARI.
PANEL_SAYISI = {
    "01_ima_kur.html": 2,
    "02_bu_yil.html": 2,
    "03_yil_sonu.html": 2,
    "04_tufe_deflator.html": 3,
    "05_reel_tl.html": 2,
    "06_carry.html": 2,
    "07_revizyon.html": 2,
}


def _panel_denetimi(ad: str, fig) -> None:
    """Figürün gerçekten kaç paneli var — künyedeki sayıyla aynı mı?

    Ölçü figürün KENDİSİNDEN alınır (x eksenlerinin sayısı); çağrı yerindeki
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


def beyan_gunu(damga: str | None):
    """Birleşik damganın CANLI bacağını çözer — uç denetiminin ölçütü.

    Damga iki parçalı olabilir ("program 09.2025 · gerçekleşen 03.09.2026") ve
    o dizgede iki tarih vardır: biri yayımlanmış bir belgenin ayı, öteki canlı
    serinin günü. Uç denetimi yalnız CANLI bacağı sorabilir — program bacağı
    bir zaman serisi değil, figürde çizili bir uç taşımıyor. Canlı bacak
    yazımda SONDA durur, o yüzden son tarih alınır.
    """
    if not damga:
        return None
    b = _bicim()
    tek = b.tarihe_cevir(damga)
    if tek is not None:
        return tek
    bulgu = re.findall(r"\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}|\b\d{2}\.\d{4}\b",
                       damga)
    for parca in reversed(bulgu):
        g = b.tarihe_cevir(parca)
        if g is not None:
            return g
    return None


def _uc_denetimi(ad: str, damga: str | None, fig) -> None:
    """İlan edilen canlı uç ile figürün çizdiği en yeni TARİHLİ iz — TEK YÖNLÜ.

    Yalnız x ekseni TARİH olan figürlerde sorulur; bu hattın figürlerinin çoğu
    YIL eksenlidir ve orada "veri ucu" diye bir şey yoktur. Ölçüt tek yönlü:
    figürün en yeni izi ilan edilenden ESKİYSE damga figürde olmayan bir günü
    ilan ediyor demektir ve hat DURUR. İleri gitmesi not düşülür, hattı
    durdurmaz — yayının önünde duran bir denetimin yanlış alarmı arızanın
    kendisidir.
    """
    d = beyan_gunu(damga)
    if d is None:
        return
    uclar = []
    for tr in fig.data:
        x = getattr(tr, "x", None)
        if x is None or len(x) == 0:
            continue
        # YIL ekseni ya da metin ekseni tarih SANILMAZ. Dizeyi tarihe
        # ÇEVİRMEYE ÇALIŞMAK yanlış araçtır: "2026" de çevrilir ve ocak birine
        # düşer, "OVP 2027–2029 · 2025" de bir tarih üretebilir. Sorulacak
        # soru "bu değer tarihe benziyor mu" değil, "bu eksen zaten tarih
        # mi"dir; cevabı değerin KENDİ tipindedir.
        ilk = list(x)[0]
        if not isinstance(ilk, (pd.Timestamp, np.datetime64)):
            continue
        t = pd.to_datetime(pd.Series(list(x)), errors="coerce").dropna()
        if t.empty:
            continue
        uclar.append(t.max())
    if not uclar:
        return
    yeni = max(uclar)
    if yeni < pd.Timestamp(d):
        raise SystemExit(
            f"DUR: {ad} için ilan edilen uç ({damga}) figürün çizdiği hiçbir "
            f"ize ulaşmıyor; en yeni tarihli iz {yeni:%d.%m.%Y} tarihinde "
            "bitiyor. Damga, figürde olmayan bir günü ilan eder.")


def kos() -> None:
    o, K, C = _yukle()
    # DAMGA FİGÜR BAŞINA, TEK DEFTERDEN: aynı defteri ozet_uret.py sayfa
    # altındaki damga için okuyor. İki liste tutulsaydı figürün alt başlığı
    # ile sayfadaki damga bir gün farklı gün söylerdi.
    saat = sekil_saatleri(o, uzun=True)
    kisa = sekil_saatleri(o)
    print("OVP hattı — grafikler")
    print(f"  kur ucu {o.get('kur_tarih')} · faiz ucu {o.get('faiz_tarih')} · "
          f"TÜFE ucu {o.get('tufe_tarih')}")

    ciktilar = [
        (sekil_01(o, saat["01_ima_kur.html"]), "01_ima_kur.html"),
        (sekil_02(o, K, saat["02_bu_yil.html"]), "02_bu_yil.html"),
        (sekil_03(o, saat["03_yil_sonu.html"]), "03_yil_sonu.html"),
        (sekil_04(o, saat["04_tufe_deflator.html"]), "04_tufe_deflator.html"),
        (sekil_05(o, saat["05_reel_tl.html"]), "05_reel_tl.html"),
        (sekil_06(o, C, saat["06_carry.html"]), "06_carry.html"),
        (sekil_07(o, saat["07_revizyon.html"]), "07_revizyon.html"),
    ]

    # KOŞU SIRASI KAYNAK LİSTEYE KARŞI DENETLENİR: dosya adı, kopya hedefi ve
    # saat defteri anahtarı AYNI dizedir; ayrıştıklarında sayfa bir figürü
    # bulamaz ya da yanlış damgayla basar.
    _adlar = [ad for _f, ad in ciktilar]
    if list(SEKIL_DOSYALARI) != _adlar:
        raise SystemExit(
            f"DUR: çizilen figür listesi künyedekiyle örtüşmüyor "
            f"({_adlar} ≠ {list(SEKIL_DOSYALARI)}).")

    n = 0
    for fig, ad in ciktilar:
        if fig is None:
            print(f"  ATLANDI: {ad} — girdisi üretilemedi (koşu kaydına bakın)")
            # ÜRETİLEMEYEN FİGÜRÜN ESKİ DOSYASI SİLİNİR: kopya sözleşmesi
            # diskteki her HTML'i joker ile alıyor ve o dosya siteye giderdi;
            # üstelik bloğun saati yazılmadığı için altına tarih hiç
            # basılmazdı — bayat bir figür, bayatlığını gösteren tek işaretten
            # de yoksun.
            eski = CIKTI / ad
            if eski.exists():
                eski.unlink()
                print(f"    (önceki koşudan kalan dosya silindi: {ad})")
            continue
        _panel_denetimi(ad, fig)
        _uc_denetimi(ad, kisa[ad], fig)
        _yaz(fig, ad)
        n += 1

    # YÜKSEKLİK TEK KAYNAK: alt başlığa bir satır eklemek figürü 26 px büyütür,
    # yani metni düzenleyen her değişiklik yüksekliği de değiştirir ve MDX'te
    # elle yazılmış bir sayı sessizce eskir.
    (CIKTI / "yukseklikler.json").write_text(json.dumps(
        {ad: int(fig.layout.height) for fig, ad in ciktilar if fig is not None},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {n}/{len(ciktilar)} grafik yazıldı → {CIKTI}")

    eksik = [ad for fig, ad in ciktilar if fig is None and ad in ZORUNLU_SEKIL]
    if eksik:
        raise SystemExit(
            f"DUR: {len(eksik)} zorunlu figür üretilemedi ({', '.join(eksik)}). "
            "Siteye kopyalama YAPILMAZ — eski grafikle taze metin "
            "yayımlanmasın.")


if __name__ == "__main__":
    kos()
