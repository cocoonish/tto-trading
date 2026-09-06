#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yurt içi yerleşiklerin YP mevduatı — duman sınaması. Ağa çıkmaz, saniyeler sürer.

`guncelle.py` bu dosyayı hattın ADIMLARINDAN ÖNCE koşturur ve düşerse hat hiç
koşmaz, siteye kopyalama olmaz. Sınama `--denetle` yazan birinin eline
bırakılmaz: zamanlanmış koşu `--denetle` demez ve bozuk bir ölçüm katmanı
çıktısını siteye kopyalamış olurdu.

BURADAKİ HER MADDE BİR ARIZAYA KARŞILIK GELİR. Süsleme yok: bir iddia ya bu
depoda gerçekten yanlış yayımlanmış bir sayıyı, ya yayını durdurmuş bir yanlış
alarmı, ya da bu hattın kurulurken adı konmuş bir tuzağını kapatır. Bir
sigortanın hangi arızaya karşı çalıştığı konduğu gün yazılmazsa, sonraki oturum
onu her arızaya karşı sanır — bu yüzden her bloğun başında gerekçe yazılı.

SENTETİK ÇERÇEVE SEVİYEDEN VE AKIMDAN BİRLİKTE KURULUR: akımlar çekilir, stok
onların birikimi olur. Ölçüm katmanına doğrudan "artık sıfır" verilseydi sınama
hattın gerçekte koştuğu yoldan ayrılırdı — Δ stoku ölçüm katmanı kendisi
hesaplıyor ve sınanması gereken tam olarak o hesap. Çerçevenin takvimi de
uydurma değil: keşifte ÖLÇÜLEN pencereler birebir kurulur (değişim tablosu
653 hafta, stok tabloları 114 hafta), çünkü sınanan şeylerin yarısı tam bu
asimetriden doğuyor — ve asimetri küçükken görünmeyen bir kusur, on yıla
çıkınca sayfanın yarısını yanlış anlatır.

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import ast
import contextlib
import inspect
import io
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import metrik
import ozet_uret
import veri

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}"
          + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def _ortak(ad: str):
    """`ortak/` modülünü içe aktarır.

    `guncelle.py` çocuk sürece PYTHONPATH'i ekliyor, ama hat elle klasöründen
    koşturulduğunda eklemiyor. Hat modüllerinin `_bicim()` yardımcısı da aynı
    yedek yolu taşıyor; sınamanın onlardan farklı bir yoldan modül bulması,
    sınananla sınayanın ayrışması demek olurdu.
    """
    try:
        return __import__(ad)
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ortak"))
        return __import__(ad)


okur_dili = _ortak("okur_dili")
# Sınama, sınananla AYNI biçim sözleşmesinden okur: beklenen metni burada
# elle biçimlendirmek, ikinci bir biçim tanımı olurdu.
_bicim = _ortak("bicim")

# Keşifte ölçülen pencereler. Değişim tablosu stok tablolarından ON YIL önce
# başlıyor ve bu asimetri hattın yarısını belirliyor: kümüle akım stoktan
# geriye uzatılamaz, kimlik yalnız ortak pencerede kurulabilir, kapsam
# denetimi her seriyi KENDİ beklenen başlangıcına karşı sormak zorunda, şekil
# damgaları da iki ayrı bacağa bağlanıyor.
#
# SENTETİK ÇERÇEVE ÖLÇÜLEN PENCEREYİ TAŞIR, KOLAY OLANI DEĞİL. Değişim tablosu
# uzun süre 05.01.2024'te başlıyor sanıldı ve sınama da o pencereyi kuruyordu:
# 139 hafta. Gerçek pencere 653 — beş kat. Sınama kısa pencerede koştuğu sürece
# "139'a göre yazılmış bir varsayım" hiçbir yerde patlamazdı; ölçüldüğü gün
# ölçülen pencereye geçmesi bu yüzden sınamanın kendi kapsamının parçası.
AKIM_BAS, STOK_BAS, SON_HAFTA = "2014-02-28", "2024-06-28", "2026-08-28"
AKIM_HAFTA, STOK_HAFTA = 653, 114
KIRILIM = ("usd", "eur", "diger", "maden")
AKIM_KOLON = ([f"{o}_{e}" for o in ("ar", "pe") for e in ("toplam", "gercek", "tuzel")]
              + [f"{o}_{e}_{k}" for o in ("ar", "pe")
                 for e in ("gercek", "tuzel") for k in KIRILIM])
# Stok tablolarından gelen her sütun: bunlar yarım yıl SONRA başlıyor.
STOK_KOLON = ("stok_toplam", "stok_gercek", "stok_tuzel", "k_gercek", "k_tuzel",
              "maden_gercek", "maden_tuzel", "maden_diger", "genis_toplam",
              "mevduat_toplam", "mevduat_yi", "mevduat_tl", "mevduat_yp_tl")

# Okura giden metinlerin biriktiği torba. Sınamanın SONUNDA tek seferde
# taranır: kapsam elle tutulan bir listeden değil, hattın GERÇEKTEN ÜRETTİĞİ
# metinden türetilir. Elle tutulan bir liste bir gün bir cümleyi kaçırır ve o
# cümle okur dili kapısına ilk kez yayın gününde çarpar.
OKUR_METIN: list[str] = []


def _topla(*metinler) -> None:
    for m in metinler:
        if isinstance(m, str) and m.strip():
            OKUR_METIN.append(m)


def _iz_kaynak(ad: str) -> str:
    """Bir veri katmanı fonksiyonunun KAYNAK METNİ.

    Bazı sigortaları davranışla sınamak mümkün değil, çünkü sigorta
    kaldırıldığında çıktı DEĞİŞMEZ: yoklama payı kalkarsa "tarihçe uzamış"
    dalı hiç ateşlenmez ve ölü bir dalın çıktısı (boş) hiç ateşlenmeyen doğru
    bir dalınkiyle aynı görünür. Böyle bir sigorta ancak yerinde durduğu
    sorularak sınanır; ölçüt buraya, hattın kendi kapısına konur.
    """
    import inspect
    return inspect.getsource(getattr(veri, ad))


def _uyari_sifirla() -> None:
    """İki katmanın uyarı listesi de MODÜL DÜZEYİNDE ve tekilleştirmeli.

    Ard arda koşan iki sentetik senaryodan ilkinin uyarısı ikincisinde
    duruyor olsaydı, "bozuk çerçevede uyarı düştü" iddiası temiz çerçevenin
    uyarısıyla da geçerdi — yani sınama hep yeşil verirdi.
    """
    metrik._UYARI.clear()
    veri._UYARI.clear()


def _uyari_al() -> list[str]:
    u = list(metrik._UYARI)
    _topla(*u)
    return u


# ===========================================================================
# SENTETİK ÇERÇEVELER
# ===========================================================================
def _cerceve(bas: str = AKIM_BAS, son: str = SON_HAFTA,
             stok_bas: str | None = STOK_BAS, tohum: int = 20260905) -> pd.DataFrame:
    """Kaynağın yayımladığı biçimde bir haftalık çerçeve (`data/haftalik.csv`).

    Kurgu kimliğin kendisinden doğar: her hafta için arındırılmış değişim ve
    parite etkisi çekilir, stok bunların birikimi olarak kurulur. Böylece
    Δ stok = arındırılmış + parite kimliği YAPICA tutar ve sınama, kimliğin
    tutmadığı hâli ayrıca kurgulayarak ölçer.

    SEVİYELER BİR ONDALIĞA YUVARLANIR — kaynak da öyle yayımlıyor. Yuvarlama
    kimliğe hafta başına en çok 0,1 milyon dolarlık bir artık bırakır ve ölçüm
    katmanının eşiği (25,0 milyon dolar) tam bu payı taşımak için var:
    yuvarlamasız bir sentetik çerçeve, eşiğin gereksiz olduğu izlenimini
    verirdi.

    `stok_bas` verilirse stok tablolarından gelen sütunlar o tarihten ÖNCE boş
    bırakılır — kaynağın gerçek tarihçesi böyle.
    """
    rng = np.random.default_rng(tohum)
    idx = pd.date_range(bas, son, freq="W-FRI")
    n = len(idx)
    H = pd.DataFrame(index=idx)
    H.index.name = "tarih"

    for etiket, olcek in (("gercek", 1.0), ("tuzel", 0.55)):
        for kir, sigma in (("usd", 260.0), ("eur", 180.0),
                           ("diger", 40.0), ("maden", 220.0)):
            H[f"ar_{etiket}_{kir}"] = rng.normal(0.0, sigma * olcek, n).round(1)
            # TANIM GEREĞİ SIFIR OLAN BACAK ÇERÇEVEDE DE SIFIRDIR. Kaynak
            # dolar bacaklarının parite etkisini gerçekten sıfır yayımlıyor
            # ve künye bunu gerekçesiyle kayda geçiriyor; sentetik çerçeve
            # onlara değer yazsaydı ölçüm katmanının "kayda geçmiş gerekçe
            # çelişiyor" uyarısı her koşuda düşerdi — yani sınama, gerçekte
            # olmayan bir arızayı sürekli görürdü. Liste elle yazılmıyor,
            # künyeden okunuyor: iki yerde ayrı yazılsaydı bir gün ayrışırdı.
            _cek = rng.normal(0.0, sigma * olcek * 0.4, n).round(1)
            H[f"pe_{etiket}_{kir}"] = (
                0.0 if f"pe_{etiket}_{kir}" in veri.TANIM_SIFIRI else _cek)
        H[f"ar_{etiket}"] = H[[f"ar_{etiket}_{k}" for k in KIRILIM]].sum(axis=1)
        H[f"pe_{etiket}"] = H[[f"pe_{etiket}_{k}" for k in KIRILIM]].sum(axis=1)
    H["ar_toplam"] = H["ar_gercek"] + H["ar_tuzel"]
    H["pe_toplam"] = H["pe_gercek"] + H["pe_tuzel"]

    # Stok: ilk haftanın Δ'sı YOKTUR (bir öncesi ölçülmemiş), seviye tabandan
    # başlar. Kaynağın keşifte ölçülen son değerleri taban alındı ki büyüklük
    # mertebesi gerçek veriyle aynı olsun — eşikler mertebeye göre konmuş.
    for etiket, taban in (("gercek", 148_848.7), ("tuzel", 82_508.3)):
        akim = (H[f"ar_{etiket}"] + H[f"pe_{etiket}"]).copy()
        akim.iloc[0] = 0.0
        H[f"stok_{etiket}"] = (taban + akim.cumsum()).round(1)
    H["stok_toplam"] = H["stok_gercek"] + H["stok_tuzel"]

    # Kırılım tablosunun iki kalemi ana tablonunkiyle BİREBİR aynı (keşifte
    # ölçüldü); veri katmanının sıkı eşikli kimliği bunu sınıyor.
    H["k_gercek"] = H["stok_gercek"]
    H["k_tuzel"] = H["stok_tuzel"]
    H["maden_gercek"] = (H["stok_gercek"] * 0.602).round(1)
    H["maden_tuzel"] = (H["stok_tuzel"] * 0.108).round(1)
    H["maden_diger"] = 3_263.5

    # GENİŞ TOPLAM yurt dışı yerleşikleri de içerir ve HATTIN KONUSU DEĞİLDİR.
    # Fark, keşifte ölçülen büyüklükte tutuldu (39.714,9 milyon dolar).
    H["genis_toplam"] = (H["stok_toplam"] + 39_714.9
                         + rng.normal(0.0, 400.0, n)).round(1)

    # Lira karşılıkları BİN TL. Aynı tabloda milyon dolarlık kalemlerle yan
    # yana duruyorlar ve trilyon ölçeğinde bir birim hatası gözle yakalanmaz.
    kur = 33.0 + np.linspace(0.0, 11.5, n)
    H["mevduat_yp_tl"] = (H["stok_toplam"] * kur * 1e3).round(0)
    H["mevduat_tl"] = (9.4e9 + np.linspace(0.0, 6.0e8, n)).round(0)
    H["mevduat_yi"] = H["mevduat_tl"] + H["mevduat_yp_tl"]
    H["mevduat_toplam"] = (H["mevduat_yi"] * 1.03).round(0)

    if stok_bas is not None:
        H.loc[H.index < pd.Timestamp(stok_bas), list(STOK_KOLON)] = np.nan
    return H


def _kimligi_boz(H: pd.DataFrame, kac: int = 6, buyukluk: float = 900.0) -> pd.DataFrame:
    """Stok kımıldamadan ayrıştırma kayar: kalem numaralandırması kaymış hâl.

    Yalnız gerçek kişi bacağı (ve onu içeren toplam) bozulur; tüzel bacağı
    temiz kalır. Kusurun HANGİ bacakta olduğunu söylemeyen bir tanı, kusurun
    nerede aranacağını da söylemez.
    """
    B = H.copy()
    for kol in ("ar_gercek", "ar_toplam"):
        B.iloc[-kac:, B.columns.get_loc(kol)] += buyukluk
    return B


def _kapsami_boz(H: pd.DataFrame, buyukluk: float = 500.0) -> pd.DataFrame:
    """gerçek + tüzel ≠ toplam. Bozulursa sayfadaki HER sayı yanlıştır."""
    B = H.copy()
    B.iloc[-3:, B.columns.get_loc("stok_toplam")] += buyukluk
    return B


def _yuvarlama_ayrismasi(H: pd.DataFrame, eski_esik: float = 1e-6,
                         tavan: float = 0.09) -> pd.DataFrame:
    """İki tablo AYNI kalemi ayrı ayrı yuvarlamış olsun — GERÇEKTE ölçülen hâl.

    `_cerceve` kırılım tablosunu ana tablonun BİREBİR kopyası yapıyor, yani
    ayrışma tam sıfır ve sıkı bir eşik orada hiç sınanmıyor. Gerçek veri öyle
    değil: ana tablo bir ondalıkla (ızgara 0,1), kırılım tablosu üç ondalıkla
    (0,001) yayımlanıyor ve 114 haftada en büyük ayrışma 0,063 milyon dolar —
    ızgaranın altında, ama 61.383 milyon dolarlık stokta bağıl olarak
    1,03e-06, yani eski bağıl eşiğin ÜSTÜNDE. Yanlış alarm tam bu aralıktan
    çıktı.

    BÜYÜKLÜK SABİT YAZILMAZ, ÖLÇÜLEREK SEÇİLİR: sentetik çerçevenin seviyeleri
    gerçek veriyle aynı mertebede ama aynı sayı değil, sabit bir 0,063 burada
    bağıl olarak eşiğin ALTINDA kalır ve sınama sessizce anlamsızlaşırdı —
    "yanlış alarm yok" iddiası, yanlış alarmın hiç mümkün olmadığı bir
    çerçevede geçerdi. Büyüklük bu yüzden çerçevenin kendi seviyesinden
    türetiliyor: eski bağıl kuralı aşacak kadar büyük, ölçülen ızgaranın
    (0,1 + 0,001) altında kalacak kadar küçük.

    En kötü hâl en KÜÇÜK seviyeye konuyor, çünkü bağıl ölçü orada patlar —
    gerçek veride de kırılan bacak iki stokun küçüğüydü.
    """
    rng = np.random.default_rng(7702)
    B = H.copy()
    for kol in ("k_gercek", "k_tuzel"):
        seviye = B[kol].abs()
        b = min(1.05 * eski_esik * float(seviye.min()), tavan)
        gur = rng.uniform(-b, b, len(B))
        gur[int(seviye.fillna(np.inf).to_numpy().argmin())] = b
        B[kol] = (B[kol] + gur).round(3)
    return B


def _kalem_kaydir(H: pd.DataFrame) -> pd.DataFrame:
    """Kaynağın kalem numaralandırması kaymış olsun: kırılım tablosundaki tüzel
    kişi stokunun yerine AYNI TABLODAKİ EN YAKIN komşu kalem gelsin.

    Yuvarlama tabanının tespit payını yemediğini gösteren senaryo budur: en
    yakın komşuyla bile artık on binlerce milyon dolar olur, tabanın beş
    büyüklük basamağı üstünde.
    """
    B = H.copy()
    B["k_tuzel"] = B["maden_gercek"]
    return B


def _hafta_kaydir(H: pd.DataFrame) -> pd.DataFrame:
    """Kaynak, bir haftanın hareketini BİR SONRAKİ cumaya damgalamış olsun.

    Bu hâl ÖLÇÜLMEDİ ve varsayılmıyor; ölçüm katmanı hizalamayı ölçüp karar
    veriyor. Sınananın kendisi o karar: ÖLÇÜLEN kaydırma ile UYGULANAN
    kaydırma aynı şeyi söylemezse ikisi de doğru görünür ve kimlik artığı
    gerçek bir kusur gibi yayımlanır.
    """
    B = H.copy()
    B[AKIM_KOLON] = B[AKIM_KOLON].shift(1)
    return B


def _hafta_atla(H: pd.DataFrame, konum: int = -6) -> pd.DataFrame:
    """Bir haftanın gözlemi hiç gelmemiş olsun (yayım atlanmış)."""
    return H.drop(H.index[konum])


def _sifir_blok(H: pd.DataFrame, kol: str, kac: int, sag_uc: bool) -> pd.DataFrame:
    B = H.copy()
    j = B.columns.get_loc(kol)
    if sag_uc:
        B.iloc[-kac:, j] = 0.0
    else:
        B.iloc[-kac - 10:-10, j] = 0.0
    return B


def _bugune_cipala(H: pd.DataFrame) -> pd.DataFrame:
    """Aynı çerçeveyi BUGÜNE demirler (son gözlem en yakın cuma).

    Tazelik denetiminin referansı DUVAR SAATİDİR, verinin kendi son günü
    değil; öyleyse tazelik ancak bugüne göre kurulmuş bir çerçeveyle
    sınanabilir. Sabit takvimli çerçeve zamanla kaçınılmaz olarak bayatlar —
    ona "taze" dedirtmek, sınamayı bir gün kendiliğinden kırmızıya çeviren bir
    saatli bomba olurdu.
    """
    bugun = pd.Timestamp.today().normalize()
    cuma = bugun - pd.Timedelta(days=(bugun.weekday() - 4) % 7)
    B = H.copy()
    B.index = pd.date_range(end=cuma, periods=len(B), freq="W-FRI")
    B.index.name = "tarih"
    return B


H0 = _cerceve()
b = veri._bicim()


# ===========================================================================
# 1. KİMLİK — Δ stok = arındırılmış değişim + parite etkisi
# ===========================================================================
# Hattın merkezî iddiası bu kimliktir ve iki AYRI TABLO arasında kurulur:
# stok tablosu ile değişim tablosu. Aradaki artık yuvarlama ve revizyon
# vintajı taşır, yani kusur olmayabilir — bu yüzden kimlik hattı DURDURMAZ,
# artık ölçülür ve yayımlanır (kardeş hattaki Laspeyres artığının aynısı).
# Onu yayının önüne koymak, ölçmeye çalıştığımız şeyi görünmez kılardı.
# Kapsam kimliği (gerçek + tüzel = toplam) ise DURDURUR: keşifte birebir
# ölçüldü ve bozulması kalem eşlemesinin kaydığı anlamına gelir.
print("\n▶ Kimlik: ayrıştırma stok değişimini kapatıyor mu")

_uyari_sifirla()
A0, t0 = metrik.ayristir(H0, 0)
u0 = _uyari_al()
_topla(t0.get("cumle"))

_artik = A0["artik_toplam"].dropna().abs()
sina("temiz çerçevede artık yuvarlama payının içinde",
     float(_artik.max()) <= 0.5,
     f"en büyük artık {b.sayi(float(_artik.max()), 3)} milyon dolar")
sina("temiz çerçevede kimlik TUTUYOR", t0.get("tutuyor") is True,
     str(t0.get("tutuyor")))
sina("temiz çerçevede açık bacak yok", not t0.get("asan_bacak"),
     str(t0.get("asan_bacak")))
# Yayının önünde durmayan bir denetim bile gereksiz kırmızı yakmamalı: bir
# denetim yanlış alarm ürettiğinde kimse ona bakmaz, kapsam kadar HASSASİYET
# de denetimin parçasıdır.
sina("temiz çerçevede kimlik uyarısı DÜŞMÜYOR",
     not [x for x in u0 if x.startswith("KİMLİK")], "; ".join(u0)[:120])

_uyari_sifirla()
A1, t1 = metrik.ayristir(_kimligi_boz(H0), 0)
u1 = _uyari_al()
_topla(t1.get("cumle"))

sina("bozuk çerçevede kimlik TUTMUYOR", t1.get("tutuyor") is False,
     str(t1.get("tutuyor")))
sina("bozuk çerçevede kimlik uyarısı DÜŞÜYOR",
     any(x.startswith("KİMLİK") for x in u1), "; ".join(u1)[:120])
# Hat DURMUYOR: çağrı istisna atmadan döndü ve artığı taşıyan çerçeveyi
# üretti. Ölçülmemiş bir şeyi ölçülmüş gibi göstermektense fark yazılır.
sina("kimlik tutmayınca hat DURMUYOR, artık YAYIMLANIYOR",
     isinstance(A1, pd.DataFrame) and not A1["artik_gercek"].dropna().empty
     and bool(t1.get("cumle")),
     f"cümle {'var' if t1.get('cumle') else 'yok'}")
sina("kusur bacağıyla adlandırılıyor, temiz bacak temiz kalıyor",
     set(t1.get("asan_bacak") or []) == {"gercek", "toplam"}
     and (t1["bacak"]["tuzel"]["tutuyor"] is True),
     f"açık bacaklar {t1.get('asan_bacak')}")

# İki denetim ailesi AYNI çerçevede karışmıyor: ayrıştırma kimliği açıkken
# kapsam kimliği hâlâ temiz, yani hat durmuyor.
_uyari_sifirla()
dur_temiz, kap_temiz = metrik.kapsam_kimligi(H0)
dur_bozuk_ayr, _ = metrik.kapsam_kimligi(_kimligi_boz(H0))
dur_kapsam, kap_bozuk = metrik.kapsam_kimligi(_kapsami_boz(H0))
_topla(*dur_kapsam)
_uyari_al()

sina("kapsam kimliği temiz çerçevede DUR üretmiyor", not dur_temiz,
     "; ".join(dur_temiz)[:120])
sina("ayrıştırma kimliği açıkken kapsam kimliği hattı DURDURMUYOR",
     not dur_bozuk_ayr, "; ".join(dur_bozuk_ayr)[:120])
sina("kapsam kimliği bozulunca hat DURUYOR",
     bool(dur_kapsam) and kap_bozuk["kapsam"]["gecti"] is False,
     f"dur {len(dur_kapsam)} · geçti {kap_bozuk.get('kapsam', {}).get('gecti')}")
sina("kapsam kimliği geçtiğinde de ÖLÇÜLÜP kayda geçiyor",
     kap_temiz["kapsam"]["gecti"] is True
     and kap_temiz["kapsam"]["n"] == int(H0["stok_toplam"].notna().sum()),
     str(kap_temiz.get("kapsam")))
# DURDURUCU METİN, UYGULANAN EŞİĞİ YAZMALI. Metin sabit tabanı ("tolerans
# 2,0 milyon dolar") tolerans diye yazıyordu, oysa eşik ÜÇ KOLUN BÜYÜĞÜ ve
# bağıl kol bugünkü stokta 2,31 milyon dolara denk geliyor — haftaların
# yarısında okura söylenen tolerans, uygulanandan küçüktü. Bir kapının okura
# yanlış eşik bildirmesi, eşiğin kendisinin yanlış olmasından ayırt edilemez:
# ikisi de "bu fark neden geçti" sorusunu cevapsız bırakır.
_kb = kap_bozuk["kapsam"]
_uyg = _kb["uygulanan_esik_maks_fark_haftasi_mn"]
sina("kapsam uyarısı SABİTİ değil UYGULANAN eşiği yazıyor",
     bool(dur_kapsam) and f"{_bicim.sayi(_uyg, 2)} milyon dolar" in dur_kapsam[0]
     and "tolerans 2,0 milyon dolar" not in dur_kapsam[0],
     f"uygulanan {_uyg} · " + (dur_kapsam[0] if dur_kapsam else "")[:220])
sina("bağıl kol sabit tabanı GERÇEKTEN devralıyor (iddia boş değil)",
     _uyg > metrik.ESIK_KAPSAM_MN, f"{_uyg} > {metrik.ESIK_KAPSAM_MN}")
sina("uyarı üç kolun HANGİLERİ olduğunu da yazıyor",
     bool(dur_kapsam) and "sabit taban" in dur_kapsam[0]
     and "ölçülen yayım yuvarlaması" in dur_kapsam[0]
     and "en büyüğü" in dur_kapsam[0],
     (dur_kapsam[0] if dur_kapsam else "")[:260])

# Lira tabanı kimliği (dolarizasyon payının PAYDA tarafı) keşifte ÖLÇÜLMEDİ:
# ölçülmemiş bir seviyeye eşik konmaz. Artık hesaplanır ve kayda geçer, ama
# hüküm verilmez — "sınanmadı" ile "tutmuyor" aynı şey değildir.
sina("ölçülmemiş lira tabanı kimliğine EŞİK konmuyor, yalnız ölçülüyor",
     kap_temiz["lira_tabani"]["gecti"] is None
     and kap_temiz["lira_tabani"]["esik_bagil"] is None
     and kap_temiz["lira_tabani"]["n"] > 0,
     str(kap_temiz.get("lira_tabani", {}).get("gecti")))

# Kritik argümanın VARSAYILANI OLMAZ. Bir çağrı yerinde unutulursa Python
# hemen hata versin: varsayılan sıfır konsaydı, hizalama ölçümü başka bir
# hafta söylerken çerçeve sessizce kaynağın damgasıyla kurulur ve kimlik
# artığı gerçek bir kusur gibi görünürdü. Aynı sigorta bu depoda bir kez daha
# kondu (taşınan fiyattan sahte sıfır üreten çağrıda).
try:
    metrik.ayristir(H0)          # type: ignore[call-arg]
    _kaydirma_varsayilani = True
except TypeError:
    _kaydirma_varsayilani = False
sina("hafta kaydırmasının VARSAYILANI yok (unutulursa hata verir)",
     not _kaydirma_varsayilani)

# ÖLÇÜLEN hizalama ile UYGULANAN hizalama aynı şeyi söylemeli. Ayrışsalardı
# ikisi de doğru görünür ve artık gerçek bir kusur gibi yayımlanırdı.
_uyari_sifirla()
Hk = _hafta_kaydir(H0)
k_sec, k_tani = metrik.hizalama_sec(Hk)
u_k = _uyari_al()
_topla(k_tani.get("gerekce"))
_, t_kaydirmasiz = metrik.ayristir(Hk, 0)
_, t_kaydirmali = metrik.ayristir(Hk, k_sec)

sina("kayık damgalı kaynakta kaydırma ÖLÇÜLÜP seçiliyor", k_sec == -1,
     f"seçilen kaydırma {k_sec}")
sina("kaydırma seçilince okur görsün diye uyarı düşüyor",
     any(x.startswith("HAFTA HİZALAMASI") for x in u_k), "; ".join(u_k)[:120])
sina("seçilen kaydırma artığı kapatıyor, kaydırmasız hâli kapatmıyor",
     t_kaydirmali.get("tutuyor") is True and t_kaydirmasiz.get("tutuyor") is False,
     f"kaydırmalı {t_kaydirmali.get('tutuyor')} · "
     f"kaydırmasız {t_kaydirmasiz.get('tutuyor')}")

_uyari_sifirla()
k0, k0_tani = metrik.hizalama_sec(H0)
u_k0 = _uyari_al()
_topla(k0_tani.get("gerekce"))
sina("kayıklık yokken doğal okuma korunuyor ve uyarı düşmüyor",
     k0 == 0 and not u_k0, f"kaydırma {k0} · uyarı {len(u_k0)}")

# ATLANAN HAFTA: iki gözlem arasındaki fark İKİ haftalık değişimdir ve bir
# haftalık akımla karşılaştırılamaz. Sıfır sayılırsa artık, atlanan haftanın
# akımı kadar çıkar ve gerçek bir kusur gibi görünür.
_uyari_sifirla()
Ha = _hafta_atla(H0)
Aa, ta = metrik.ayristir(Ha, 0)
_uyari_al()
_bosluk_sonrasi = Ha.index[-5]
sina("atlanan haftadan sonraki Δ ÖLÇÜLMEMİŞ sayılıyor (sıfır değil)",
     bool(pd.isna(Aa.loc[_bosluk_sonrasi, "delta_gercek"]))
     and bool(pd.isna(Aa.loc[_bosluk_sonrasi, "artik_gercek"])),
     f"Δ {Aa.loc[_bosluk_sonrasi, 'delta_gercek']}")
sina("atlanan hafta SAHTE artık üretmiyor (kimlik hâlâ tutuyor)",
     ta.get("tutuyor") is True, str(ta.get("tutuyor")))


# ===========================================================================
# 2. KÜMÜLE AKIM — bu hattın asıl katkısı
# ===========================================================================
# Sayfanın anlattığı seyir bu: bir hafta artı, ertesi hafta eksi, ay toplamı
# neredeyse sıfır. Pencerenin nerede başlayıp bittiği yanlışsa anlatının
# tamamı yanlış olur; işaret yanlışsa çıkış giriş diye okunur. Ve ay başında
# sıfıra yakın bir kümüle "akım olmadı" da olabilir "ölçüm gelmedi" de —
# ikisini ayıran, kaç haftanın toplandığıdır.
print("\n▶ Kümüle akım: pencere, işaret ve ölçülmemiş hafta")

K0 = metrik.kumule(A0)
kt0 = metrik.kumule_tanisi(A0, A0.index[-1])
_ay = [t for t in A0.index if (t.year, t.month) == (2025, 3)]
_yil = [t for t in A0.index if t.year == 2026]

sina("ay içi kümüle, ayın ilk cumasında o haftanın akımına eşit",
     abs(float(K0.loc[_ay[0], "kum_ay_ar_toplam_mn"])
         - float(A0.loc[_ay[0], "ar_toplam"])) < 1e-9)
sina("ay içi kümüle, ayın son cumasında o ayın haftalarının toplamı",
     abs(float(K0.loc[_ay[-1], "kum_ay_ar_toplam_mn"])
         - float(A0.loc[_ay, "ar_toplam"].sum())) < 1e-9 and len(_ay) > 1)
# Ay dönünce pencere SIFIRLANMALI: önceki ayın birikimi taşınsaydı "ay içi
# fiili akım" diye yayımlanan sayı iki ayın toplamı olurdu.
_onceki_ay_son = [t for t in A0.index if (t.year, t.month) == (2025, 2)][-1]
sina("ay dönünce pencere SIFIRLANIYOR (önceki ayın birikimi taşınmıyor)",
     abs(float(K0.loc[_ay[0], "kum_ay_ar_toplam_mn"])) < 1e6
     and not np.isclose(float(K0.loc[_ay[0], "kum_ay_ar_toplam_mn"]),
                        float(K0.loc[_onceki_ay_son, "kum_ay_ar_toplam_mn"])
                        + float(A0.loc[_ay[0], "ar_toplam"])))
sina("yıl içi kümüle, yılın ilk cumasında o haftanın akımına eşit",
     abs(float(K0.loc[_yil[0], "kum_yil_ar_toplam_mn"])
         - float(A0.loc[_yil[0], "ar_toplam"])) < 1e-9)
sina("yıl içi kümüle, yılın haftalarının toplamı",
     abs(float(K0.loc[_yil[-1], "kum_yil_ar_toplam_mn"])
         - float(A0.loc[_yil, "ar_toplam"].sum())) < 1e-9)
sina("pencere başı, hafta sayısı ve etiketi kayda geçiyor",
     kt0.get("ay_bas") is not None and (kt0.get("ay_hafta") or 0) > 0
     and kt0.get("yil_bas") == _yil[0].strftime("%Y-%m-%d")
     and kt0.get("yil_hafta") == len(_yil),
     str({k: kt0.get(k) for k in ("ay_bas", "ay_hafta", "yil_bas", "yil_hafta")}))

# İŞARET: çıkış eksi. Bir ayın akımlarının tamamı eksiyken kümüle de eksi
# olmalı ve toplamla birebir tutmalı — işaretin ters dönmesi, aylık iki
# milyar dolarlık bir çıkışı giriş diye yayımlamak demektir.
Ae = A0.copy()
_eksi_ay = [t for t in Ae.index if (t.year, t.month) == (2025, 9)]
_akim_kol = [c for c in Ae.columns if c.startswith(("ar_", "pe_"))]
Ae.loc[_eksi_ay, _akim_kol] = -Ae.loc[_eksi_ay, _akim_kol].abs()
Ke = metrik.kumule(Ae)
sina("hepsi çıkış olan ayda kümüle EKSİ ve toplamla birebir",
     float(Ke.loc[_eksi_ay[-1], "kum_ay_ar_toplam_mn"]) < 0
     and abs(float(Ke.loc[_eksi_ay[-1], "kum_ay_ar_toplam_mn"])
             - float(Ae.loc[_eksi_ay, "ar_toplam"].sum())) < 1e-9,
     b.sayi(float(Ke.loc[_eksi_ay[-1], "kum_ay_ar_toplam_mn"]), 1))

# ÖLÇÜLMEMİŞ HAFTA SIFIR SAYILMAZ. O haftanın kendi hücresi boş kalır ve
# toplam yalnız ölçülen haftaları taşır; sıfırla doldurulsaydı "o hafta hiç
# hareket olmadı" diye yayımlanmış olurdu.
Ab = A0.copy()
_bos = _ay[2]
Ab.loc[_bos, _akim_kol] = np.nan
Kb = metrik.kumule(Ab)
ktb = metrik.kumule_tanisi(Ab, Ab.index[-1])
_onceki = [t for t in _ay if t < _bos]
sina("ölçülmemiş haftanın kümülesi BOŞ (sıfır değil)",
     bool(pd.isna(Kb.loc[_bos, "kum_ay_ar_toplam_mn"])))
# ÖLÇÜLMEMİŞ BİR HAFTADAN SONRASI DA ÖLÇÜLEMEZ. `groupby().cumsum()` boş
# gözlemi ATLIYORDU: yalnız o haftanın hücresi boş kalıyor, SONRAKİ her hücre
# o haftayı sıfır sayarak birikiyordu — yani "o aya damgalı dört haftada X"
# cümlesindeki dört haftanın biri hiç ölçülmemiş oluyordu ve hafta sayacı da
# eksilmiyordu. Ölçüldü: [100 · boş · 50 · 25] → [100 · boş · 150 · 175].
sina("boşluktan SONRAKİ haftaların kümülesi de BOŞ (eksik hafta sıfır sayılmaz)",
     bool(Kb.loc[[t for t in _ay if t > _bos], "kum_ay_ar_toplam_mn"].isna().all())
     and len([t for t in _ay if t > _bos]) > 0,
     str(list(Kb.loc[_ay, "kum_ay_ar_toplam_mn"].round(1))))
sina("boşluktan ÖNCEKİ haftalar dokunulmadan doğru toplanıyor",
     abs(float(Kb.loc[_onceki[-1], "kum_ay_ar_toplam_mn"])
         - float(Ab.loc[_onceki, "ar_toplam"].sum())) < 1e-9 and len(_onceki) > 1)
# Aynı maske her SÜTUN için bağımsız: bir kırılım bacağının boşluğu manşet
# akımın kümülesini düşürmemeli, yoksa sayfanın manşeti bir bacak yüzünden
# aylarca kaybolur.
Ac = A0.copy()
Ac.loc[_bos, "ar_gercek_diger"] = np.nan
Kc = metrik.kumule(Ac)
sina("maske SÜTUN BAZINDA: bir bacağın boşluğu manşet kümüleyi düşürmüyor",
     bool(pd.notna(Kc.loc[_ay[-1], "kum_ay_ar_toplam_mn"]))
     and bool(pd.isna(Kc.loc[_ay[-1], "kum_ay_ar_gercek_diger_mn"])))
sina("kaç haftanın toplandığı kayda geçiyor (sıfır akım ≠ ölçüm yok)",
     (ktb.get("ay_hafta") or 0) > 0 and (kt0.get("ay_hafta") or 0) > 0,
     f"ay_hafta {ktb.get('ay_hafta')}")

# ETİKET, SAYININ OKUNDUĞU HAFTADAN. Tanı çerçevenin EN YENİ dolu haftasından
# kuruluyordu, sayı ise akım bloğunun ORTAK haftasından okunuyor; ikisi
# ayrıştığında sayfa bir ayın sayısını başka bir ayın adıyla yayımlıyordu
# (ölçüldü: "Ağustos 2026 içinde … 302,8", oysa 302,8 Mayıs'ın kümülesiydi).
_gec = A0.index[-14]
_tani_gec = metrik.kumule_tanisi(A0, _gec)
sina("kümülenin etiketi ÇIPADAN türüyor, çerçevenin ucundan değil",
     _tani_gec["son_hafta"] == _gec.strftime("%Y-%m-%d")
     and _tani_gec["ay_etiket"] == veri.ad_uzun(_gec)
     and pd.Timestamp(_tani_gec["ay_bas"]) <= _gec,
     str({k: _tani_gec.get(k) for k in ("son_hafta", "ay_etiket", "ay_bas")}))
sina("çıpadan SONRAKİ haftalar pencereye girmiyor",
     _tani_gec["ay_hafta"] == len([t for t in A0.index
                                   if (t.year, t.month) == (_gec.year, _gec.month)
                                   and t <= _gec]),
     f"ay_hafta {_tani_gec['ay_hafta']}")
try:
    metrik.kumule_tanisi(A0)          # type: ignore[call-arg]
    _tani_varsayilani = True
except TypeError:
    _tani_varsayilani = False
sina("kümüle etiketinin ÇIPA argümanının VARSAYILANI yok", not _tani_varsayilani)

# KÜMÜLE AKIM STOKTAN GERİYE UZATILMAZ. Değişim tablosu yarım yıl önce
# başlıyor; o aralıkta Δ stok YOKTUR ve kimlik sınanamaz. Sınanamayan bir
# haftayı sıfır artıkla doldurmak, yapılmamış bir sınavın sonucunu bildirmek
# olurdu.
_erken = A0.index[A0.index < pd.Timestamp(STOK_BAS)]
sina("stok tablosu başlamadan önce Δ ve artık BOŞ, akım DOLU",
     bool(A0.loc[_erken, "delta_gercek"].isna().all())
     and bool(A0.loc[_erken, "artik_gercek"].isna().all())
     and bool(A0.loc[_erken, "ar_gercek"].notna().all()),
     f"{len(_erken)} hafta")

# Tek haftalık ve boş veri ÇÖKMEZ: hattın ilk koşusunda ya da kaynak yeni bir
# bacak açtığında elde tek gözlem olabilir; kümüle adımının orada düşmesi
# hattın tamamını düşürürdü.
try:
    K1 = metrik.kumule(A0.iloc[:1])
    kt1 = metrik.kumule_tanisi(A0.iloc[:1], A0.index[0])
    Kz = metrik.kumule(A0.iloc[:0])
    ktz = metrik.kumule_tanisi(A0.iloc[:0], A0.index[0])
    _cokme = None
except Exception as ex:                                   # noqa: BLE001
    K1 = kt1 = Kz = ktz = None
    _cokme = f"{type(ex).__name__}: {ex}"
sina("tek haftalık veri kümüleyi ÇÖKERTMİYOR",
     _cokme is None and kt1 is not None and kt1.get("ay_hafta") == 1,
     _cokme or str(kt1))
sina("boş çerçeve kümüleyi ÇÖKERTMİYOR",
     _cokme is None and ktz == {}, _cokme or str(ktz))
sina("sabit pencere dolmadan sayı üretmiyor",
     K1 is not None
     and bool(pd.isna(K1[f"kum_{metrik.PENCERE_KISA}h_ar_toplam_mn"].iloc[0])))

# SABİT PENCERE GÖZLEM DEĞİL TAKVİM SAYAR. `rolling` gözlem sayıyor: kaynak bir
# cumayı hiç yayımlamazsa "dört haftalık toplam" diye yayımlanan sayı yirmi
# sekiz günü kapsar (ölçüldü: 31.07 · 07.08 · 21.08 · 28.08 → 28 gün) ve okur
# onu üç haftalık bir pencerenin sonucu sanar. Ölçü yanlış değil, ETİKET
# yanlış. Δ stok tarafında aynı kapı zaten vardı, kayan pencerelerde eşi yoktu.
_Hp = _hafta_atla(H0, konum=-3)
_Ap, _ = metrik.ayristir(_Hp, 0)
_kap = metrik.pencere_kapsami(_Ap.index, metrik.PENCERE_KISA, _Ap.index[-1])
sina("sabit pencerenin GERÇEK takvim kapsamı ölçülüyor",
     _kap == 28 and metrik.pencere_kapsami(A0.index, metrik.PENCERE_KISA,
                                           A0.index[-1]) == 21,
     f"atlanan haftada {_kap} gün")
# Maskeleme YERİNE ölçüm: sapan pencereyi boşaltmak denendi ve on üç haftalık
# pencerede tek bir atlanan hafta sağ uçtaki on iki gözlemi birden siliyor,
# figürün üçüncü paneli üç ay geriye düşüyor ve uç denetimi hattın TAMAMINI
# durduruyordu — kaldırmaya çalıştığımız kusurun ta kendisi.
sina("sapan pencere BOŞALTILMIYOR (yayını durduran bir yan etki üretmez)",
     bool(pd.notna(metrik.kumule(_Ap)[
         f"kum_{metrik.PENCERE_KISA}h_ar_toplam_mn"].iloc[-1])))


# ===========================================================================
# 3. YURT DIŞI BACAK — bu hattın EN PAHALI olası hatası
# ===========================================================================
# TP.HPBITABLO4.1 (keşifte 271.071,9) YURT DIŞI YERLEŞİKLERİ DE İÇERİR;
# TP.HPBITABLO2.10 (231.357,0) yalnız yurt içi yerleşiklerdir ve HATTIN
# KONUSU BUDUR. Aradaki 39.714,9 bir kusur değil, kapsamın kendisi. Bir gün
# biri "toplam" diye 4.1'i yazacak ve iki toplam yan yana durduğu için hiçbir
# denetim bunu göremeyecek — sayı da tarih de kendi içinde tutarlı olacak.
# Sigorta bu yüzden ADA değil DAVRANIŞA konuyor: geniş toplam kımıldatılır ve
# değişen sütunlar sayılır. Manşete giden hiçbir anahtar kımıldamamalı.
print("\n▶ Yurt dışı bacak: geniş toplam manşete giremez")

M0 = metrik.stok_metrikleri(H0)
_gp = H0.copy()
_gp["genis_toplam"] = _gp["genis_toplam"] + 25_000.0
Mg = metrik.stok_metrikleri(_gp)

_degisen = {c for c in M0.columns
            if not np.isclose(float(M0[c].iloc[-1]), float(Mg[c].iloc[-1]),
                              rtol=0, atol=1e-9)}
sina("geniş toplam yalnız KENDİ anahtarlarını besliyor",
     _degisen == {"genis_toplam_mia", "genis_fark_mia", "genis_fark_pay"},
     f"değişen sütunlar {sorted(_degisen)}")
# FARKIN ADI "YURT DIŞI" OLAMAZ. Künyenin kalem numaralandırmasına göre geniş
# toplam dört bölümlü, yurt içi toplam yalnız birincisi; fark 1.2 + 1.3 + 1.4.
# Yurt dışı yerleşik bankalar (TP.HPBITABLO4.21) bunların yalnız BİRİ ve o
# seri bu hatta ÇEKİLMİYOR. Alt yazı farkın tamamını "yurt dışı bacağın payı"
# diye ilan ediyordu — üstelik hattın veri katmanı aynı varsayımı başka bir
# yerde açıkça yasaklarken. Ad bir sözleşmedir: `yurtdisi_mia` diye yazılan
# bir sayı, sayfayı yazan oturuma ölçülmemiş bir cümle kurdurur.
_yd_ad = [c for c in M0.columns if "yurtdisi" in c]
sina("ölçülmemiş bir kapsam iddiasını taşıyan anahtar adı YOK",
     not _yd_ad and "genis_fark_mia" in M0.columns, f"kalan {_yd_ad}")
sina("kaynak künyesinde yurt dışı yerleşik bankalar serisi ÇEKİLMİYOR",
     not any(s_.kod.endswith("HPBITABLO4.21") for s_ in veri.HAFTALIK.values()))
sina("manşet stoku YURT İÇİ tabandan geliyor",
     abs(float(M0["stok_toplam_mia"].iloc[-1])
         - float(H0["stok_toplam"].iloc[-1]) / 1e3) < 1e-9
     and "stok_toplam_mia" not in _degisen)
# Aynı soru ÖZET anahtarı düzeyinde: sayfanın `<Deger>` ile okuduğu şey bu
# sözlük ve manşet anahtarı da oradan seçilecek.
_o0 = metrik._blok(M0, list(M0.columns), "stok")
_og = metrik._blok(Mg, list(Mg.columns), "stok")
_oz_degisen = {k for k in _o0
               if isinstance(_o0[k], float) and not np.isclose(_o0[k], _og[k])}
sina("geniş tabandan beslenen her ÖZET anahtarı adında geniş/yurt dışı taşıyor",
     bool(_oz_degisen)
     and all(("genis" in k) or ("yurtdisi" in k) for k in _oz_degisen),
     f"değişen anahtarlar {sorted(_oz_degisen)}")

# Fark bir kusur değil, YAYIMLANACAK bir büyüklük: sayfada geniş toplam
# geçecekse adıyla ve FARKIYLA geçmeli, yani fark ölçülmüş olmalı.
uy_yd, r_yd = veri.genis_fark_olc(H0)
_topla(*uy_yd)
sina("kapsam farkı ÖLÇÜLÜP künyeye yazılıyor",
     r_yd.get("son_fark_mn_usd", 0) > 0
     and r_yd.get("n") == int(H0["genis_toplam"].notna().sum()),
     str({k: r_yd.get(k) for k in ("n", "son_fark_mn_usd", "son_pay")}))
sina("geniş toplam temizken kapsam uyarısı DÜŞMÜYOR", not uy_yd,
     "; ".join(uy_yd)[:120])

_ters = H0.copy()
_ters["genis_toplam"] = _ters["stok_toplam"] - 1_000.0
uy_ters, _ = veri.genis_fark_olc(_ters)
_topla(*uy_ters)
sina("geniş toplam dar toplamın ALTINA düşerse kapsam çelişkisi uyarılıyor",
     any(x.startswith("KAPSAM ÇELİŞKİSİ") for x in uy_ters),
     "; ".join(uy_ters)[:120])


# ===========================================================================
# 4. TARİHÇE ASİMETRİSİ VE ŞEKİL SAAT DEFTERİ
# ===========================================================================
# Bu hattın iki ritmi var: stok tabloları ile değişim tablosu ayrı yayımlanıyor
# ve aynı cumada bitmeyebiliyor. Kardeş bir hatta on figürün hepsi tek ana
# saatle damgalanmıştı; dördü dört gün, biri iki ay geriydi. Kusur okura İKİ
# YÖNDE birden yalan söyler: bayat panel taze görünür, ve okur tek damgayı
# sayfanın tamamına yorup TAZE olanı bayat sanır.
print("\n▶ Şekil saat defteri: bağlayıcı bacak ve ölçülemeyen uç")

_ES, _YE = "2026-08-21", "2026-08-28"
_d1 = veri.sekil_saatleri({"stok_tarih": _YE, "akim_tarih": _ES, "dol_tarih": _YE})
_d2 = veri.sekil_saatleri({"stok_tarih": _ES, "akim_tarih": _YE, "dol_tarih": _YE})

sina("karma figürde bağlayıcı bacak EN ESKİ olan",
     _d1["05_kimlik.html"] == "21.08.2026", str(_d1["05_kimlik.html"]))
# min() YAPISAL yazılır: bugün hangi bacağın önde olduğuna bakmaz. Sıralama
# tersine döndüğünde de kazanan en eski bacaktır — figürün sözü serilerin
# KIYASIDIR ve kıyas ancak hepsinin ölçüldüğü güne kadar kurulabilir.
sina("sıralama tersine dönünce de bağlayıcı bacak EN ESKİ",
     _d2["05_kimlik.html"] == "21.08.2026", str(_d2["05_kimlik.html"]))
sina("her figür KENDİ bacağına bağlı (stok figürü stok, akım figürü akım)",
     _d1["01_stok_kirilim.html"] == "28.08.2026"
     and _d1["03_ayristirma.html"] == "21.08.2026",
     f"01 {_d1['01_stok_kirilim.html']} · 03 {_d1['03_ayristirma.html']}")

# Akım figürleri stok serisini HİÇ çizmiyor; stok saati onları bağlamamalı.
# Bağlasaydı bayat bir akım paneli taze stok tarihiyle damgalanırdı.
_yalniz_stok = veri.sekil_saatleri({"stok_tarih": _YE})
sina("akım figürü stok saatine DÜŞMÜYOR",
     _yalniz_stok["03_ayristirma.html"] is None
     and _yalniz_stok["01_stok_kirilim.html"] == "28.08.2026",
     str(_yalniz_stok["03_ayristirma.html"]))
# Ölçülmeyen bir ucun öbüründen yeni olduğu KANITLANAMAZ: seçilecek bir "en
# eski" yoktur. Yanlış bir tarih, tarihsizlikten kötüdür.
sina("bacaklardan biri ölçülmemişse karma figürün damgası YOK",
     _yalniz_stok["05_kimlik.html"] is None)
# KİMLİK FİGÜRÜNÜN SAATİ ÖLÇÜLMÜŞ OLANDIR, YENİDEN TÜRETİLEN DEĞİL.
# Defter `min(stok, akım)` diye kendi hesabını yapıyordu; ölçüm katmanı ise
# aynı bloğun ortak haftasını zaten ölçüp `kimlik_tarih` diye yazıyor. İkisi
# ayrıştığında (kaynak bir haftayı atladığında ya da son gözlemi altı gün
# arayla damgaladığında Δ stok ölçülmemiş sayılır ve kimlik saati geriye
# düşer) çizim katmanının uç denetimi doğru davranıp hattın TAMAMINI
# durduruyordu — çalışan beş figür ve özet de siteye gitmiyordu. Yayının
# önünde duran bir denetimin yanlış alarmı arızanın kendisidir.
_kt = veri.sekil_saatleri({"stok_tarih": _YE, "akim_tarih": _YE,
                           "kimlik_tarih": _ES})
sina("kimlik figürünün damgası ÖLÇÜLMÜŞ kimlik saatinden geliyor",
     _kt["05_kimlik.html"] == "21.08.2026", str(_kt["05_kimlik.html"]))
sina("kimlik saati ölçülmemişse yedek yol (en eski bacak) çalışıyor",
     _d1["05_kimlik.html"] == "21.08.2026")
_bos_defter = veri.sekil_saatleri({})
sina("hiç ölçüm yoksa defterin TAMAMI boş (uydurma yok)",
     all(v is None for v in _bos_defter.values()),
     str({k: v for k, v in _bos_defter.items() if v is not None}))
sina("defterdeki her damga GG.AA.YYYY yazımında",
     all(re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", v) for v in _d1.values() if v),
     str(sorted({v for v in _d1.values() if v})))
# Figürün İÇİNDEKİ alt yazı okura sayfa damgası kadar görünür; iki taraf ayrı
# kaynaktan beslenirse bir gün sessizce ayrışır ve okur aynı figürün içinde ve
# altında iki farklı tarih görür.
sina("figür alt başlığı aynı defterden, uzun yazımla",
     veri.sekil_saatleri({"stok_tarih": _YE, "akim_tarih": _ES},
                         uzun=True)["05_kimlik.html"] == "21 Ağustos 2026")
# Kapsam bir listeden değil SÖZLEŞMEDEN türetilir: defterde girdisi olmayan
# bir figür sayfa sınavında uyarı üretir ve hattın ana saatine düşer.
sina("defter, üretilen bütün figürleri kapsıyor",
     set(_d1) == set(veri.SEKIL_DOSYALARI),
     f"defterde olmayan {sorted(set(veri.SEKIL_DOSYALARI) - set(_d1))}")

# ÖLÜ BAĞIMLILIK KIRIK OLANDAN TEHLİKELİDİR: defter üç anahtar okuyor ve o
# anahtarları ölçüm katmanı yazıyor. Yazan adım kaybolursa defter sessizce
# boşalır — dosya vardır, okunur, hata vermez, yalnızca tarih basılmaz olur.
_metrik_agac = ast.parse(Path(metrik.__file__).read_text(encoding="utf-8"))
_yazilan = {f"{d.args[2].value}_tarih" for d in ast.walk(_metrik_agac)
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
            and d.func.id == "_blok" and len(d.args) == 3
            and isinstance(d.args[2], ast.Constant)}
_veri_agac = ast.parse(Path(veri.__file__).read_text(encoding="utf-8"))
_defter_govde = next(d for d in ast.walk(_veri_agac)
                     if isinstance(d, ast.FunctionDef) and d.name == "sekil_saatleri")
_okunan = {d.args[0].value for d in ast.walk(_defter_govde)
           if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
           and d.func.attr == "get" and d.args
           and isinstance(d.args[0], ast.Constant)}
sina("defterin okuduğu her saat anahtarını ölçüm katmanı YAZIYOR",
     bool(_okunan) and _okunan <= _yazilan,
     f"yazan yok: {sorted(_okunan - _yazilan)}")

# BLOK TARİHİ: farklı haftalarda biten serileri yan yana basmak, "aynı
# haftanın karşılaştırması" diye sunulan farkı bir haftalık tarih kaymasının
# kendisi yapar. Blok, tümünün dolu olduğu ortak haftaya çıpalanır.
_uyari_sifirla()
Mk = M0.copy()
Mk.iloc[-1, Mk.columns.get_loc("maden_pay_gercek")] = np.nan
_bk = metrik._blok(Mk, list(Mk.columns), "stok")
_ub = _uyari_al()
sina("blok, tümünün dolu olduğu ORTAK haftaya çıpalanıyor",
     _bk["stok_tarih"] == M0.index[-2].strftime("%Y-%m-%d"),
     f"{_bk['stok_tarih']} · beklenen {M0.index[-2].date()}")
sina("kayan seriler adlandırılıyor ve uyarı düşüyor",
     bool(_bk.get("stok_kayan"))
     and "maden_pay_gercek" not in _bk["stok_kayan"]
     and any(x.startswith("ORTAK HAFTA") for x in _ub),
     f"kayan {_bk.get('stok_kayan')} · uyarı {len(_ub)}")
sina("bloğun bütün serileri aynı haftada bitiyorsa uyarı DÜŞMÜYOR",
     "stok_kayan" not in metrik._blok(M0, list(M0.columns), "stok"))
# Uyarı metni okura HATTIN İÇ ANAHTARINI basmaz. İki modül aynı kutuya
# yazıyordu ve iki ayrı ad tablosu tutuyordu: biri "akım" diyordu, öteki
# "resmî ayrıştırma tablosu"; okur ikisinin aynı şey olduğunu bilemezdi.
sina("ortak hafta uyarısı BLOK sözcüğünü ve iç anahtarı taşımıyor",
     all(" bloğ" not in x and "blok" not in x.lower() for x in _ub)
     and any(veri.blok_okur("stok") in x for x in _ub),
     "; ".join(_ub)[:140])
sina("blok okur adları TEK yerde (özet üreticisi kendi tablosunu tutmuyor)",
     __import__("ozet_uret").BLOK_OKUR is veri.BLOK_OKUR)

# ORTAK HAFTADA GÖZLEMİ OLMAYAN SÜTUN TAŞINMAZ. `asof` sessizce bir önceki
# haftanın değerini döndürüyordu ve o değer ortak haftanın damgasıyla
# yayımlanıyordu: ölçüldü, basılan sayı serinin bir hafta önceki değeriydi ve
# uyarı hâlâ "tümünün dolu olduğu ortak hafta" diyordu. Seri başına delikli
# indeks bu hatta yapısal (önbellek her seriyi kendi dolu gözlemleriyle
# saklıyor, demet düşünce seriler tek tek çekiliyor).
_uyari_sifirla()
Mh = M0.copy()
Mh.iloc[-1, Mh.columns.get_loc("maden_pay_gercek")] = np.nan   # blok -2'ye çıpalanır
Mh.iloc[-2, Mh.columns.get_loc("maden_pay_tuzel")] = np.nan    # ortak haftada DELİK
_bh = metrik._blok(Mh, list(Mh.columns), "stok")
_uh = _uyari_al()
sina("ortak haftada gözlemi olmayan anahtar ÖZETE YAZILMIYOR (taşınmıyor)",
     "maden_pay_tuzel" not in _bh and _bh.get("stok_delikli") == ["maden_pay_tuzel"],
     f"delikli {_bh.get('stok_delikli')} · yazıldı {'maden_pay_tuzel' in _bh}")
# "KAYAN" ile "DELİKLİ" AYRI kusurlardır ve ayrı alanlarda adlandırılır: biri
# geç biten seriyi, öteki ortasında gözlemi eksik olanı söyler. Bir seri
# ikisi birden olabilir (geç bitiyor VE ortak haftada boş) — o yüzden ölçüt
# dışlama değil, ayrı alanın VARLIĞI ve ayrı uyarı ailesidir.
sina("deliği olan seri KENDİ alanında adlandırılıyor ve ayrı uyarı düşüyor",
     _bh.get("stok_delikli") == ["maden_pay_tuzel"]
     and any(x.startswith("ÖLÇÜM EKSİK") for x in _uh)
     and any(x.startswith("ORTAK HAFTA") for x in _uh),
     f"delikli {_bh.get('stok_delikli')} · uyarı {[x[:24] for x in _uh]}")
sina("delik yokken ÖLÇÜM EKSİK uyarısı DÜŞMÜYOR (yanlış alarm yok)",
     "stok_delikli" not in metrik._blok(M0, list(M0.columns), "stok"))

# ÇIPA SÜTUNLARI DARALTILABİLİR: sabit uzunluklu pencerelerin ucu tanım gereği
# geride olabilir ve bloğun TAMAMINI bir çeyrek geriye çekiyordu.
_cp = M0.copy()
_cp["kum_13h_sinav_mn"] = np.nan
_cp.iloc[:-13, _cp.columns.get_loc("kum_13h_sinav_mn")] = 1.0
_b_dar = metrik._blok(_cp, list(_cp.columns), "stok",
                      cipa_kolonlari=[c for c in _cp.columns
                                      if not c.startswith("kum_")])
sina("çıpa sütunları daraltılınca pencere sütunu bloğun saatini çekmiyor",
     _b_dar["stok_tarih"] == M0.index[-1].strftime("%Y-%m-%d")
     and "kum_13h_sinav_mn" not in _b_dar,
     f"{_b_dar['stok_tarih']}")

# HATTIN SAATİ: bir hafta geriden gelen bir bacak çekirdeğe alınsaydı hattın
# saati her hafta bir hafta geriye düşerdi. Çekirdek, kimliğin
# HESAPLANABİLDİĞİ haftayı verir.
veri._SON.pop("hafta", None)
Hs = H0.copy()
Hs.iloc[-2:, Hs.columns.get_loc("ar_gercek")] = np.nan
_cipa = veri.son_hafta(Hs)
veri._SON.pop("hafta", None)
Hd = H0.copy()
Hd.iloc[-2:, Hd.columns.get_loc("maden_diger")] = np.nan   # çekirdek DIŞI
_cipa_dis = veri.son_hafta(Hd)
veri._SON.pop("hafta", None)
sina("çıpa, çekirdeğin TAMAMININ dolu olduğu son cuma",
     _cipa == H0.index[-3], f"{_cipa.date()} · beklenen {H0.index[-3].date()}")
sina("çekirdek DIŞI bir bacağın gecikmesi hattın saatini geriye çekmiyor",
     _cipa_dis == H0.index[-1], f"{_cipa_dis.date()}")


# ===========================================================================
# 5. VERİ KATMANININ KAPILARI — kırpma, boşluk, tazelik, kaynak kimliği
# ===========================================================================
# "Veri geldi" ile "veri TAM geldi" aynı şey değildir: kaynak bin satırdan
# sonrasını UYARI VERMEDEN kırpar, HTTP 200 döner ve koşu yeşil biter — eksik
# olan yalnız tarihçedir. Ölçüt bu yüzden her seriyi KENDİ beklenen
# başlangıcına karşı sorar; tek bir genel başlangıç, tarihçesi zaten asimetrik
# olan yirmi beş seriyi birden yanlış işaretlerdi.
print("\n▶ Veri katmanı: kırpma izi, atlanan hafta ve tazelik")

_kapsam = veri.kapsam_olc(H0)
sina("kapsam, keşifte ölçülen iki pencereyi birebir görüyor",
     _kapsam["ar_toplam"]["n"] == AKIM_HAFTA
     and _kapsam["stok_toplam"]["n"] == STOK_HAFTA
     and _kapsam["ar_toplam"]["bas"] == AKIM_BAS
     and _kapsam["stok_toplam"]["bas"] == STOK_BAS,
     f"akım {_kapsam['ar_toplam']['n']} · stok {_kapsam['stok_toplam']['n']}")
_uy_kapsam = veri.kapsam_uyarilari(_kapsam)
_topla(*_uy_kapsam)
sina("tarihçe asimetrik diye kırpma alarmı ÇALMIYOR", not _uy_kapsam,
     "; ".join(_uy_kapsam)[:140])

_kirpik = _cerceve(bas="2025-01-03")
_uy_kirpik = veri.kapsam_uyarilari(veri.kapsam_olc(_kirpik))
_topla(*_uy_kirpik)
# Kırpma bir İSTEK düzeyinde olur ve aynı demetteki bütün serileri birden
# vurur: otuz beş satır tek bir olayı anlatır ve okunmaz.
sina("tarihçenin başı kesilince uyarı düşüyor, TEK cümlede",
     len(_uy_kirpik) == 1 and _uy_kirpik[0].startswith("KAPSAM"),
     f"{len(_uy_kirpik)} satır")

# --- KAPSAM TOLERANSI: YAYIM RİTMİNDEN TÜRÜYOR ------------------------------
# Tolerans elle yazılmış bir yedi değil, tek yerde duran yayım ritminin
# kendisi. İki ölçü (tazelik ve kapsam) aynı ritimden türüyor; ayrı ayrı
# yazılsalardı biri güncellenip öteki unutulurdu ve bu depoda tam bu sınıf
# kusur ölçüldü (aynı olay için iki katmanda iki ayrı hafta sayısı).
sina("kapsam toleransı yayım ritminden türüyor, elle yazılmıyor",
     veri.kapsam_tolerans("haftalik") == veri.AILE_RITIM_GUN["haftalik"]
     and veri.tazelik_tolerans("haftalik")
     == veri.AILE_RITIM_GUN["haftalik"] + veri.TATIL_PAYI_GUN,
     f"kapsam {veri.kapsam_tolerans('haftalik')} · "
     f"tazelik {veri.tazelik_tolerans('haftalik')}")
# GERÇEK BİR KIRPMANIN İLK İŞARETİ TEK HAFTADIR: seri satır sınırını aştığı
# gün kaynak tarihçenin başından bir hafta keser, yüz hafta değil. Tolerans
# bir yayım aralığını geçerse o ilk hafta görünmez ve kırpma ancak birikince
# fark edilir — yani ölçüt geç kalır.
_bir_hafta = _cerceve(bas=(pd.Timestamp(AKIM_BAS)
                           + pd.Timedelta(days=14)).strftime("%Y-%m-%d"))
sina("iki haftalık kırpma bile YAKALANIYOR (tolerans bir yayım aralığı)",
     any(x.startswith("KAPSAM")
         for x in veri.kapsam_uyarilari(veri.kapsam_olc(_bir_hafta))),
     str(veri.kapsam_uyarilari(veri.kapsam_olc(_bir_hafta)))[:140])
# Tam bir yayım aralığı kadar kayma KIRPMA DEĞİL: kaynak ilk haftayı tatil
# kaymasıyla öteleyebilir ve her hafta alarm veren bir denetime kimse bakmaz.
_tam_bir = _cerceve(bas=(pd.Timestamp(AKIM_BAS)
                         + pd.Timedelta(days=7)).strftime("%Y-%m-%d"))
sina("tek yayım aralığı kadar kayma kırpma SAYILMIYOR (yanlış alarm yok)",
     not veri.kapsam_uyarilari(veri.kapsam_olc(_tam_bir)),
     str(veri.kapsam_uyarilari(veri.kapsam_olc(_tam_bir)))[:140])

# --- TARİHÇE UZARSA: "ERKEN BAŞLIYOR" DALI ÖLÜ KOD DEĞİL --------------------
# BU HATTIN EN PAHALI KUSURU BURADA KAPANIYOR. Çekim alt sınırı ile kapsam
# denetiminin ölçütü aynı sabitti: gelen başlangıç beklenenden ERKEN
# olamazdı, çünkü daha eskisi hiç sorulmuyordu. Denetim doğruydu, koşuyordu,
# yeşil bitiyordu — ve on iki buçuk yıllık tarihçenin on yılını göremiyordu.
# Sınama iki şeyi birden ölçer: cevabın erken gelmesi UYARI üretiyor mu, ve
# çekim gerçekten katalogdakinden geriden mi soruyor. İkincisi olmadan
# birincisi hiç ateşlenmez, yani ölü koddur.
_uzun = _cerceve(bas=(pd.Timestamp(AKIM_BAS)
                      - pd.Timedelta(days=veri.YOKLAMA_GUN)).strftime("%Y-%m-%d"))
_uy_uzun = veri.kapsam_uyarilari(veri.kapsam_olc(_uzun))
_topla(*_uy_uzun)
sina("kaynak katalogdakinden ESKİ gözlem yayımlarsa uyarı düşüyor",
     len(_uy_uzun) == 1 and _uy_uzun[0].startswith("KAPSAM")
     and "daha eski" in _uy_uzun[0],
     "; ".join(_uy_uzun)[:180])
sina("erken bulgusu ALT SINIR olarak yazılıyor (yoklama payı kadar bakılıyor)",
     bool(_uy_uzun) and "en az" in _uy_uzun[0], "; ".join(_uy_uzun)[:180])
sina("çekim, katalogdaki başlangıçtan GERİDEN soruyor (dal ölü kod değil)",
     veri.YOKLAMA_GUN > veri.kapsam_tolerans("haftalik")
     and pd.Timestamp(_kapsam["ar_toplam"]["sorulan_bas"])
     < pd.Timestamp(_kapsam["ar_toplam"]["beklenen_bas"]),
     f"yoklama {veri.YOKLAMA_GUN} gün · "
     f"sorulan {_kapsam['ar_toplam']['sorulan_bas']}")
# Yoklama payı KAYNAK METNİNDEN de sınanır: `cek_kume` payı uygulamayı
# bırakırsa yukarıdaki dal sessizce ölü koda döner ve hiçbir ölçüt düşmez —
# çünkü ölü bir dalın çıktısı, hiç ateşlenmeyen doğru bir dalın çıktısıyla
# aynı görünür (boş).
# Pay artık TEK bir fonksiyonda (`sorgu_alt_siniri`) ve üç tüketici onu
# oradan çağırıyor: çekim, kapsam kaydı ve ÖNBELLEK ANAHTARI. Ölçüt bu yüzden
# iki halkayı birden soruyor — payın tanımda durması ve çekimin onu ÇAĞIRMASI.
# Yalnız biri sorulsaydı, tanım yerinde dururken çağrı yerinin payı atlaması
# görünmezdi.
sina("yoklama payı çekim kodunda GERÇEKTEN uygulanıyor",
     "sorgu_alt_siniri" in _iz_kaynak("cek_kume")
     and "YOKLAMA_GUN" in _iz_kaynak("sorgu_alt_siniri"),
     "cek_kume yoklama payını uygulamıyor")

# --- ÇEKİM PENCERESİNİN ARİTMETİĞİ: 653 HAFTA TEK İSTEĞE SIĞIYOR MU --------
# Soru bir hüküm değil ARİTMETİK, öyleyse yorumda değil kodda durur ve her
# koşuda yeniden ölçülür. Kaynak ~1000 satırdan sonrasını UYARI VERMEDEN
# kırpıyor ve aralığın SONUNDAN geriye doldurduğu için kesilen şey tarihçenin
# BAŞI oluyor — yani sığmayan bir istek, tam olarak bu hattın kurtarmaya
# çalıştığı yılları yeniden kaybettirir.
_ar = veri.parca_aritmetigi()
sina("653 haftalık pencere, yoklama payıyla birlikte TEK isteğe sığıyor",
     _ar["tek_parca"] and not _ar["siniri_asiyor"]
     and _ar["istek_satir"] < veri.SATIR_SINIRI,
     f"{_ar['istek_satir']} satır · {_ar['parca_sayisi']} parça")
# ASIL BAĞLAYICI ÖZDEŞLİK BU: bugün sığması bir ölçüm, yarın da kesilmemesi
# bir GARANTİ. Tarihçe uzadığında istek bölünür; bölünen her parçanın kendi
# başına sınırın altında kalması parçalama uzunluğunun tanımından gelmeli,
# bugünkü tarihten değil.
sina("parça uzunluğu satır sınırının ALTINDA (tarihçe uzasa da kesilmez)",
     _ar["parca_satir"] < veri.SATIR_SINIRI
     and veri.PARCA_HAFTA_GUN == int(veri.SATIR_SINIRI * veri.PARCA_PAYI)
     * veri.AILE_RITIM_GUN["haftalik"],
     f"parça {_ar['parca_satir']} satır · sınır {veri.SATIR_SINIRI}")
# Bir sınıra ne kadar yaklaşıldığı, aşılıp aşılmadığı kadar önemli: pay
# ölçülmezse parçalamanın ilk kez devreye girdiği gün de görünmez.
sina("tek parçanın dolmasına kalan pay ÖLÇÜLÜYOR ve pozitif",
     _ar["kalan_hafta"] > 0, f"{_ar['kalan_hafta']} hafta")
sina("kapsam yetmeyince çıktı ÜRETİLMEZ kapısı kapanıyor",
     veri.kapsam_yeterli(H0)[0] is True
     and veri.kapsam_yeterli(H0.iloc[-10:])[0] is False,
     str(veri.kapsam_yeterli(H0.iloc[-10:])))
_topla(veri.kapsam_yeterli(H0.iloc[-10:])[1])

# --- ÖNBELLEK ANAHTARI SORGU PENCERESİNİ TAŞIR -----------------------------
# ARIZANIN KENDİSİ: anahtar bir süre yalnız biçim ve seri kodundan kuruluydu,
# yani AYNI dosya adı iki farklı sorgunun cevabını taşıyabiliyordu.
# Katalogdaki başlangıç 2024'ten 2014'e çekildiğinde önbellekteki 139 haftalık
# dosya hâlâ TAZE görünüyordu (TTL dolmamış, ad değişmemiş) ve olduğu gibi
# okunuyordu. Sonuç sessiz ve iki katlıydı: hat kısa tarihçeyle koşuyor, kapsam
# denetimi de gelen başlangıcı YENİ katalogla kıyaslayıp kırpma görüyor ve
# kusuru KAYNAĞA yıkan bir uyarı basıyordu. Koşucu önbelleği CI'da da geri
# yüklendiği için arıza yerelde kalmıyordu.
#
# SINIF KURALI: önbelleklenen bir çıktı, onu üreten GİRDİYİ de taşımalıdır.
_s_eski = veri.Seri("TP.HPBITABLO5.1", "2024-01-05", "mn USD",
                    "Arındırılmış değişim, toplam (TP.HPBITABLO5.1)")
_s_yeni = veri.HAFTALIK["ar_toplam"]
_y_eski = veri._cache_yolu(_s_eski.kod, "gun", veri.sorgu_alt_siniri(_s_eski))
_y_yeni = veri._cache_yolu(_s_yeni.kod, "gun", veri.sorgu_alt_siniri(_s_yeni))
sina("katalogdaki başlangıç değişince ÖNBELLEK GEÇERSİZLEŞİYOR",
     _s_eski.kod == _s_yeni.kod and _y_eski != _y_yeni,
     f"{_y_eski.name} ↔ {_y_yeni.name}")
# Anahtarın değişmesi yetmez, DEĞİŞMEMESİ de gerekir: pencere aynıyken ad da
# aynı kalmazsa önbellek her koşuda baştan kurulur, yani hiç önbellek olmaz.
sina("aynı sorgu penceresi AYNI önbellek dosyasına düşüyor",
     veri._cache_yolu(_s_yeni.kod, "gun",
                      veri.sorgu_alt_siniri(_s_yeni)) == _y_yeni, _y_yeni.name)
# ÜST SINIR ADA GİRMEZ: istek hep "bugün + pay"a kadar sorulur ve o ucun
# tazeliğini TTL ölçer. Ada girseydi ad her gün değişir ve önbellek ölürdü.
sina("önbellek anahtarı yalnız ALT sınırı taşıyor (üst sınır TTL'in işi)",
     veri.CACHE_TTL_SAAT > 0
     and pd.Timestamp.today().strftime("%Y%m%d") not in _y_yeni.name,
     _y_yeni.name)
# BİR DAHA OKUNMAYACAK DOSYA BIRAKILMAZ: koşucu önbelleğinde birikir ve
# katalog bir gün geri alınırsa YENİDEN CANLANIR — kapatılan kusura geri
# dönüş yolu bırakmak, kusuru kapatmamaktır.
_cache_eski = veri.CACHE
_tmp_cache = Path(tempfile.mkdtemp(prefix="ypmevduat-onbellek-"))
try:
    veri.CACHE = _tmp_cache
    _a = veri._cache_yolu("TP.HPBITABLO5.1", "gun", "2013-02-22")
    _c = veri._cache_yolu("TP.HPBITABLO5.1", "gun", "2023-01-06")
    # PENCERESİZ ESKİ YAZIM: koşucu önbelleği bunları taşımaya devam ediyor.
    _e = _tmp_cache / "evds_gun_TP_HPBITABLO5_1.csv"
    # ADI BU SERİNİN ADIYLA BAŞLAYAN BAŞKA BİR SERİ: "…5_1" yazımı "…5_10"
    # ile başlıyor ve çizgisiz bir önekle temizlik onu da silerdi.
    _d = veri._cache_yolu("TP.HPBITABLO5.10", "gun", "2013-02-22")
    for _q in (_a, _c, _d, _e):
        _q.write_text("tarih,x\n", encoding="utf-8")
    veri._cache_eskisini_sil("TP.HPBITABLO5.1", "gun", _a)
    _kalan = sorted(q.name for q in _tmp_cache.glob("*.csv"))
finally:
    veri.CACHE = _cache_eski
    shutil.rmtree(_tmp_cache, ignore_errors=True)
# ASIL ARIZANIN KENDİSİ, DAVRANIŞLA: eski pencerenin dosyası TAZE dururken
# (TTL dolmamış) çekim onu kullanmaya devam ediyordu. Ölçüt tam o hâli kurar —
# eski dosya taze, yeni anahtar YOK, öyleyse seri kaynaktan yeniden çekilir.
_cache_eski2 = veri.CACHE
_tmp2 = Path(tempfile.mkdtemp(prefix="ypmevduat-onbellek2-"))
try:
    veri.CACHE = _tmp2
    _eski_pencere = veri._cache_yolu(_s_eski.kod, "gun",
                                     veri.sorgu_alt_siniri(_s_eski))
    _eski_pencere.write_text("tarih,x\n", encoding="utf-8")
    _eski_taze = veri._taze(_eski_pencere, veri.CACHE_TTL_SAAT)
    _yeni_taze = veri._taze(
        veri._cache_yolu(_s_yeni.kod, "gun", veri.sorgu_alt_siniri(_s_yeni)),
        veri.CACHE_TTL_SAAT)
finally:
    veri.CACHE = _cache_eski2
    shutil.rmtree(_tmp2, ignore_errors=True)
sina("eski pencerenin TAZE kopyası yeni sorguyu KARŞILAMIYOR (yeniden çekilir)",
     _eski_taze and not _yeni_taze,
     f"eski taze {_eski_taze} · yeni taze {_yeni_taze}")
sina("eski pencere ve penceresiz eski yazım siliniyor",
     _c.name not in _kalan and _e.name not in _kalan, str(_kalan))
sina("adı önek olan BAŞKA serinin önbelleği silinmiyor",
     sorted(_kalan) == sorted([_a.name, _d.name]), str(_kalan))

# BOŞLUK BULGUSU İKİ ÖNEKTEN BİRİNİ ALIR VE ÖLÇÜT TARİHTİR (bkz. E3 bloğu
# aşağıda): sağ uçtaki boşluk bu koşuda yayımlanan sayıya dokunur, eski
# boşluk tarihçenin bir özelliğidir. Sentetik çerçeve SABİT takvimli olduğu
# için `_hafta_atla` her zaman ESKİ bir boşluk üretir; sağ uç hâli aşağıda
# bugüne demirlenmiş çerçeveyle ayrıca kurulur.
_uy_bosluk = veri.bosluk_uyarilari(_hafta_atla(H0))
_topla(*_uy_bosluk)
sina("atlanan hafta veri katmanında da görünüyor",
     len(_uy_bosluk) == 1
     and _uy_bosluk[0].startswith(("HAFTA ATLANDI", "TARİHÇEDE BOŞLUK")),
     "; ".join(_uy_bosluk)[:140])
sina("boşluk yokken uyarı DÜŞMÜYOR", not veri.bosluk_uyarilari(H0))

# KISALAN ARALIK DA BİR ÖLÇÜMÜ DÜŞÜRÜR. Ölçüt yalnız "yedi günden uzun" diye
# soruyordu; kaynak son gözlemi tatil kayması yüzünden altı gün arayla
# damgaladığında hiçbir uyarı düşmüyordu — oysa ölçüm katmanı haftalık değişimi
# yalnız TAM YEDİ GÜNLÜK aralıklarda hesaplıyor, yani o haftanın Δ stoku
# ölçülmemiş sayılıyor ve koşu kaydında hiç iz kalmıyordu.
_Hk6 = H0.copy()
_ix = list(_Hk6.index)
_ix[-1] = _ix[-1] - pd.Timedelta(days=1)
_Hk6.index = pd.DatetimeIndex(_ix, name="tarih")
_uy_kisa = veri.bosluk_uyarilari(_Hk6)
_topla(*_uy_kisa)
sina("altı günlük aralık koşu kaydında GÖRÜNÜYOR",
     len(_uy_kisa) == 1
     and _uy_kisa[0].startswith(("ARALIK KISALDI", "TARİHÇEDE KISA ARALIK")),
     "; ".join(_uy_kisa)[:140])
sina("iki aile AYRI cümlelerde (atlanan hafta ile kısalan aralık)",
     len(veri.bosluk_uyarilari(_hafta_atla(_Hk6))) == 2,
     str(veri.bosluk_uyarilari(_hafta_atla(_Hk6))))

# TAZELİK referansı DUVAR SAATİDİR, verinin kendi son günü değil: verinin
# ucunu referans almak denetimi kendi kendine referanslı yapar ("son gözlem
# bugün, demek ki taze") ve donmuş bir seri sonsuza kadar taze görünür.
Ht = _bugune_cipala(H0)
_uy_taze = veri.tazelik_denetimi(Ht)
sina("bugüne kadar gelen çerçevede tazelik uyarısı DÜŞMÜYOR", not _uy_taze,
     "; ".join(_uy_taze)[:140])
_uy_bayat = veri.tazelik_denetimi(
    Ht.iloc[:-max(2, veri.tazelik_tolerans("haftalik") // 7 + 1)])
_topla(*_uy_bayat)
sina("yayım durunca tazelik uyarısı DÜŞÜYOR",
     any(x.startswith("TAZELİK") for x in _uy_bayat),
     "; ".join(_uy_bayat)[:140])
# "Hiç yüklenemedi" ile "geç" AYRI cümlelerdir: birincisi çekimin, ikincisi
# kaynağın kusurudur ve aynı cümlede toplanırlarsa hangisi olduğu okurun
# elinde kalmaz.
_uy_yok = veri.tazelik_denetimi(Ht.drop(columns=["maden_gercek"]))
_topla(*_uy_yok)
sina("hiç yüklenemeyen seri, gecikmiş seriden AYRI cümlede",
     len(_uy_yok) == 1 and "hiç yüklenemedi" in _uy_yok[0],
     "; ".join(_uy_yok)[:140])

# --- ESKİ BOŞLUK BAYATLIK DEĞİL, TARİHÇE ÖZELLİĞİDİR -----------------------
# ARIZANIN KENDİSİ: boşluk ölçümü tarihçenin TAMAMINI tarıyor ama ürettiği
# cümlenin öneki bayatlık ailesindeydi. 2015'te atlanmış tek bir hafta, verisi
# bugüne kadar gelmiş bir sayfayı HER KOŞUDA bayat ilan ediyordu — ve on iki
# yıllık haftalık bir seride boşluk bulunmaması neredeyse imkânsız olduğu için
# hüküm KALICI olurdu. Ölçü, ölçtüğü şeyi ayırt edemez hâle gelir: gerçekten
# donmuş bir besleme ile on yıl önceki bir tatil kayması aynı cümleyi basar.
#
# AYRIM: bayatlık SAĞ UCA dair bir hükümdür; eski boşluk pencereye dokunur,
# okura bildirilir ama bu koşuda yayımlanan sayı hakkında bir şey söylemez.
# İki yön de sınanır — yalnız biri sınansaydı ölçüt ya körleşir ya sağırlaşır.
_Ht_sag = Ht.drop(Ht.index[-2])            # son aralık on dört gün: SAĞ UÇ
_uy_sag = veri.bosluk_uyarilari(_Ht_sag)
_topla(*_uy_sag)
sina("SAĞ UÇTAKİ boşluk bayatlık ailesine giriyor",
     len(_uy_sag) == 1 and _uy_sag[0].startswith(veri.SAG_UC_IZI)
     and not _uy_sag[0].startswith(veri.TARIHCE_IZI),
     "; ".join(_uy_sag)[:160])
_Ht_eski = _hafta_atla(Ht, konum=-60)      # bir yıldan eski: TARİHÇE
_uy_eskib = veri.bosluk_uyarilari(_Ht_eski)
_topla(*_uy_eskib)
sina("ESKİ boşluk bayatlık ailesine GİRMİYOR (tarihçe özelliği)",
     len(_uy_eskib) == 1 and _uy_eskib[0].startswith(veri.TARIHCE_IZI)
     and not _uy_eskib[0].startswith(veri.SAG_UC_IZI),
     "; ".join(_uy_eskib)[:160])
# BULGU KAYBOLMUYOR — kaybolan yalnız yanlış hüküm. Eski boşluk okura yine
# gösteriliyor ve dokunmadığı şey adıyla yazılıyor.
sina("eski boşluk okura GÖSTERİLİYOR ve dokunmadığı şey yazılıyor",
     bool(_uy_eskib)
     and "bu koşuda yayımlanan sayılara dokunmuyorlar" in _uy_eskib[0],
     "; ".join(_uy_eskib)[:200])
# İKİ AİLE ÇAKIŞMAZ: bir önek iki ailede birden olsaydı hüküm hangi ailenin
# üyesi olduğuna göre değil, listelerin sırasına göre kurulurdu.
sina("sağ uç ve tarihçe aileleri AYRIK, ikisi de boş değil",
     not (set(veri.SAG_UC_IZI) & set(veri.TARIHCE_IZI))
     and veri.TAZELIK_IZI is veri.SAG_UC_IZI and bool(veri.TARIHCE_IZI),
     f"{veri.SAG_UC_IZI} ↔ {veri.TARIHCE_IZI}")
# ÖLÇÜT YENİ BİR SABİT DEĞİL: "sağ uç" penceresi tazelik toleransının kendisi.
sina("sağ uç ölçütü tazelik toleransından türüyor, elle yazılmıyor",
     veri.bosluk_sag_ucta(pd.Timestamp.today().normalize())
     and not veri.bosluk_sag_ucta(
         pd.Timestamp.today().normalize()
         - pd.Timedelta(days=veri.tazelik_tolerans() + 1)),
     f"tolerans {veri.tazelik_tolerans()} gün")

# Kaynağın KENDİ içindeki tutarlılık: ölçülmüş kimliklere sıkı eşik konur,
# ölçülmemişlere KONMAZ. Ölçülmeyen bir seviyeye eşik koymak, ilk koşuda
# yanlış alarm üretip yayının önünde durmak demektir.
_uy_k, _rap_k = veri.kimlik_denetimi(H0)
_topla(*_uy_k)
# EŞİKSİZ KİMLİK = eşik alanı VAR ve None. Filtre `.get(...) is None` diye
# yazılıydı ve o yazım, eşik alanı hiç OLMAYAN kayıtları (kapsanma denetimi,
# sınanamayan kimlik) da eşiksiz sayardı — sayım bir gün sessizce başka bir
# aileyi içeri alır ve iddia neyi saydığını bilmez.
_esiksiz = [r for r in _rap_k.values()
            if "esik_bagil" in r and r["esik_bagil"] is None]
sina("kaynak kimlikleri temiz çerçevede uyarı üretmiyor", not _uy_k,
     "; ".join(_uy_k)[:140])
sina("ölçülmemiş kimlikler EŞİKSİZ ölçülüp raporlanıyor",
     len(_esiksiz) >= 6 and all(r["gecti"] is None for r in _esiksiz),
     f"{len(_esiksiz)} eşiksiz kimlik")
_uy_kb, _ = veri.kimlik_denetimi(_kapsami_boz(H0))
_topla(*_uy_kb)
sina("ölçülmüş kimlik bozulunca kaynak kimliği uyarısı düşüyor",
     any(x.startswith("KİMLİK BOZUK") for x in _uy_kb),
     "; ".join(_uy_kb)[:140])

# --- YAYIM HASSASİYETİ TABANI ------------------------------------------------
# İLK GERÇEK KOŞUDA YANLIŞ ALARM VERDİ. Kimlik eşiği yalnız BAĞILDI (1e-6) ve
# kırılım tablosuyla ana tablo arasındaki 0,063 milyon dolarlık ayrışma —
# 61.383 milyon dolarlık bir stokta 1e-6 tam olarak 0,061'e denk geliyordu —
# ihlal sayıldı. Okur "kalem numaralandırması değişmiş olabilir" diye olmayan
# bir arızayı okudu. Yayının önünde duran bir denetimin yanlış alarmı arızanın
# kendisidir; kapsam kadar HASSASİYET de denetimin parçasıdır.
print("\n▶ Yayım hassasiyeti: yuvarlama tabanı ve tespit payı")

sina("yayım adımı ÖLÇÜLÜYOR: bir ondalıkla yayımlanan seride 0,1",
     veri.yayim_adimi(H0["stok_gercek"]) == 0.1,
     str(veri.yayim_adimi(H0["stok_gercek"])))
_ince = (H0["stok_gercek"] + 0.037).round(3)
sina("yayım adımı ÖLÇÜLÜYOR: üç ondalıkla yayımlanan seride 0,001",
     veri.yayim_adimi(_ince) == 0.001, str(veri.yayim_adimi(_ince)))
# İLK SÜRÜM BURADA ÇÖKTÜ: ondalık basamak sayan bir ölçü, iki yuvarlanmış
# sayının TOPLAMINDA (100.476,8 + 62.668,4 = 163.145,19999999998) on dört
# basamak görür ve "ızgara yok" der. Oysa kimlik denetiminin bir tarafı tam
# olarak böyle bir toplamdır — ölçü en çok gerektiği yerde susardı.
sina("iki yuvarlanmış serinin TOPLAMINDA da ızgara ölçülüyor (0,1)",
     veri.yayim_adimi(H0["stok_gercek"] + H0["stok_tuzel"]) == 0.1,
     str(veri.yayim_adimi(H0["stok_gercek"] + H0["stok_tuzel"])))
sina("yuvarlanmamış seride ızgara YOK diyor (taban uydurmuyor)",
     veri.yayim_adimi(H0["stok_gercek"] * np.pi) == 0.0,
     str(veri.yayim_adimi(H0["stok_gercek"] * np.pi)))
# ADIM TAVANI KALDIRILDI VE SEBEBİ ÖLÇÜLDÜ. Üs döngüsü sıfırdan başlıyor,
# tavan da 1,0'dı: ikisi birlikte "kaynak hassasiyetini kabalaştırırsa taban
# kendiliğinden kayar" sigortasını YAPISAL OLARAK ATIL bırakıyordu — ölçülen
# adım 1,0'ı geçemiyordu, yani sigorta hiçbir koşulda çalışamazdı. Bir
# sigortanın hangi arızaya karşı çalıştığı yazılmazsa sonraki oturum onu her
# arızaya karşı sanar; burada yazılmıştı ve YİNE DE çalışmıyordu.
_kaba = (H0["stok_gercek"] / 10.0).round(0) * 10.0
sina("kaynak kabalaşırsa adım da kabalaşıyor (tavan yok)",
     veri.yayim_adimi(_kaba) == 10.0,
     str(veri.yayim_adimi(_kaba)))
sina("adım imzasında TAVAN argümanı yok",
     "tavan" not in inspect.signature(veri.yayim_adimi).parameters,
     str(inspect.signature(veri.yayim_adimi)))
# KABA TARAFI AÇMAK TEK BAŞINA YENİ BİR KUSUR ÜRETİR: tek değer taşıyan bir
# seri HER ızgaranın üstünde durur. Eski sürüm ona tavanın kendisini (1,0),
# tavansız sürüm 1.000,0 diyordu; ikisi de ölçüm değil TESADÜF. Bu hattın
# baştan sona sıfır dört serisi tam olarak böyle.
_tek = pd.Series([0.0] * 200, index=H0.index[:200])
sina("tek değerli seride ızgara ÖLÇÜLEMEZ diyor (tesadüf ölçüm sayılmıyor)",
     veri.yayim_adimi_olc(_tek) == (0.0, "ornek_yetersiz"),
     str(veri.yayim_adimi_olc(_tek)))
sina("örneklem eşiği ARİTMETİKTEN geliyor, elle konmuş bir sayı değil",
     veri.ADIM_ASGARI_BENZERSIZ >= 6
     and 10.0 ** (-veri.ADIM_ASGARI_BENZERSIZ) <= 1e-6,
     str(veri.ADIM_ASGARI_BENZERSIZ))
# ORANTILI PAYIN SINIRI SORULUYOR. Pay 0,5'e ulaştığında her gerçek sayı bir
# tam sayının payı içindedir: sınama ızgarayı değil HİÇBİR ŞEYİ ölçer. Eski
# sürüm o hâlde de bir ızgara döndürüyordu — ölçemediğini söylemek yerine
# yanlış bir ızgara vermek, eşiğin tabanını sessizce şişirir.
_dev = H0["stok_gercek"] * 1e12
sina("pay ızgarayı ayırt edemeyecek kadar büyükse KARAR VERİLEMEZ deniyor",
     veri.yayim_adimi_olc(_dev) == (0.0, "karar_verilemez"),
     str(veri.yayim_adimi_olc(_dev)))
sina("ölçülemeyen ızgara TABAN olarak sıfır döner (uydurma taban yok)",
     veri.yayim_adimi(_dev) == 0.0 and veri.yayim_adimi(_tek) == 0.0)
# SIFIRIN ÜÇ SEBEBİ AYRI ADLA DÖNER: eşiğe etkisi aynı olsa da tanısı değil.
sina("dönen sıfırın SEBEBİ adıyla ayrılıyor",
     len({veri.yayim_adimi_olc(_tek)[1], veri.yayim_adimi_olc(_dev)[1],
          veri.yayim_adimi_olc(H0["stok_gercek"] * np.pi)[1],
          veri.yayim_adimi_olc(H0["stok_gercek"].iloc[0:0])[1]}) >= 3,
     str([veri.yayim_adimi_olc(x)[1] for x in
          (_tek, _dev, H0["stok_gercek"] * np.pi,
           H0["stok_gercek"].iloc[0:0])]))

_uyari_sifirla()
_Hy = _yuvarlama_ayrismasi(H0)
_uy_y, _rap_y = veri.kimlik_denetimi(_Hy)
_topla(*_uy_y)
_capraz = [r for a, r in _rap_y.items()
           if r.get("esik_bagil") is not None and "TP.HPBITABLO4" in a]
sina("ölçülen yayım ayrışması YANLIŞ ALARM üretmiyor",
     not any(x.startswith("KİMLİK BOZUK") for x in _uy_y),
     "; ".join(_uy_y)[:200])
# Bu iddia sınamayı bir REGRESYON sınamasına çeviriyor: eski kural (yalnız
# bağıl 1e-6) bu çerçevede GERÇEKTEN düşerdi. Düşmeseydi yukarıdaki "yanlış
# alarm yok" iddiası boş bir iddia olurdu.
sina("eski kural (yalnız bağıl eşik) bu çerçevede DÜŞERDİ",
     any(r["maks_bagil"] > 1e-6 for r in _capraz),
     str([round(r["maks_bagil"], 9) for r in _capraz]))
sina("taban ÖLÇÜLEN iki ızgaranın toplamı (0,1 + 0,001)",
     bool(_capraz) and all(abs(r["esik_taban"] - 0.101) < 1e-9 for r in _capraz),
     str([r.get("esik_taban") for r in _capraz]))

# TESPİT PAYI DARALMIYOR. Taban yanlış alarmı susturmak için değil, ölçülen
# yayım hassasiyetinden kondu; yakalaması gereken arıza beş büyüklük basamağı
# daha büyük.
_uyari_sifirla()
_uy_kk, _rap_kk = veri.kimlik_denetimi(_kalem_kaydir(H0))
_topla(*_uy_kk)
_kk = [x for x in _uy_kk if x.startswith("KİMLİK BOZUK")]
sina("yuvarlama tabanı GERÇEK kalem kaymasını hâlâ yakalıyor", bool(_kk),
     "; ".join(_uy_kk)[:140])
sina("kalem kayması artığı tabanın en az bin katı",
     any(r["maks_fark"] > 1000 * r["esik_taban"]
         for a, r in _rap_kk.items()
         if r.get("esik_bagil") is not None and r.get("gecti") is False),
     str([(round(r["maks_fark"], 1), r["esik_taban"])
          for r in _rap_kk.values() if r.get("gecti") is False]))
# Uyarı METNİ de okura ne olduğunu söylemeli: kaç kat olduğunu yazmayan bir
# cümle, "0,3 milyon dolar" büyük mü küçük mü sorusunu okurun elinde bırakır.
sina("uyarı, farkın yuvarlama payının kaç KATI olduğunu yazıyor",
     bool(_kk) and "katı" in _kk[0] and "yuvarlamadan doğamaz" in _kk[0],
     (_kk[0] if _kk else "")[:180])
# Birim OKUR yazımıyla basılır: katalogdaki kısaltma bizim künyemiz, okurun
# elinde onun karşılığı yok. Aynı kutudaki kapsam uyarısı zaten açık yazıyordu.
sina("uyarı birimi okur diliyle yazıyor (künye kısaltması değil)",
     bool(_kk) and "milyon dolar" in _kk[0] and "mn USD" not in _kk[0],
     (_kk[0] if _kk else "")[:180])

# KIYAS NOKTASININ ADI, ÖLÇÜLEN ŞEYİN ADI OLMALI. Metin bölenini "yuvarlamanın
# bırakabileceği pay" diye adlandırıyordu; oysa bölen TAM adımların toplamı
# (0,1 + 0,001) ve yuvarlamanın bırakabileceği pay onun YARISIDIR (0,0505) —
# bu dosyanın kendi belgesi de o payı öyle ölçüyor. İki ad aynı sayıya
# konunca okura verilen kat sayısı iki kat küçük görünüyordu: "kaç kat" diye
# soran biri yanlış bir ölçekle bakıyordu.
_kk_kayit = [r for r in _rap_kk.values() if r.get("gecti") is False]
_kat_bekle = max(r["maks_fark"] / r["esik_taban"] for r in _kk_kayit)
sina("uyarı kıyas noktasını ÖLÇÜLEN ADIMLARIN TOPLAMI diye adlandırıyor",
     bool(_kk) and "yayım adımları toplamının" in _kk[0]
     and "yuvarlamanın bırakabileceği payın" not in _kk[0],
     (_kk[0] if _kk else "")[:220])
sina("yazılan kat sayısı TAM adımlar toplamına göre (yarım adıma göre değil)",
     bool(_kk) and f"{_bicim.sayi(_kat_bekle, 1)} katı" in _kk[0],
     f"beklenen {_bicim.sayi(_kat_bekle, 1)} · " + (_kk[0] if _kk else "")[:220])
# TABAN ÖLÇÜLEMEDİĞİNDE KIYAS DA YAZILMAZ: ölçülmemiş bir bölenle kurulan
# "şu kadar kat" cümlesi, kaç kat olduğunu ölçmüş gibi görünürdü.
_uyari_sifirla()
_Hb = _kalem_kaydir(H0).copy()
for _c in ("k_tuzel", "stok_tuzel"):
    _Hb[_c] = _Hb[_c] * np.pi * 1e12
_uy_tb, _ = veri.kimlik_denetimi(_Hb)
_topla(*_uy_tb)
_tb = [x for x in _uy_tb if x.startswith("KİMLİK BOZUK")]
sina("taban ölçülemeyince 'kaç kat' yazılmıyor, sebebi yazılıyor",
     bool(_tb) and any("ölçülemedi" in x and "katı" not in x for x in _tb),
     "; ".join(_tb)[:240])

# EKSİK SÜTUNDA KİMLİK SESSİZCE ATLANMIYOR. Atlanan bir kimlik, geçen bir
# kimlikle tıpatıp aynı görünür: ne uyarı vardır ne künye satırı. Kardeşi
# (kapsam kimliği) aynı durumda "SINANAMADI" diyordu; aynı olayın iki
# katmanda iki farklı görüntüsü olması, hangisinin neyi görmediğini kimsenin
# aklında tutamaması demek.
_uyari_sifirla()
_uy_eks, _rap_eks = veri.kimlik_denetimi(H0.drop(columns=["k_tuzel"]))
_topla(*_uy_eks)
sina("eksik sütunda kimlik SESSİZCE atlanmıyor, SINANAMADI diyor",
     any(x.startswith("KİMLİK SINANAMADI") for x in _uy_eks),
     "; ".join(_uy_eks)[:200])
sina("sınanamayan kimlik künyede de ADIYLA duruyor",
     any(r.get("sinandi") is False and r.get("gecti") is None
         for r in _rap_eks.values()),
     str([a[:40] for a, r in _rap_eks.items() if r.get("sinandi") is False]))
sina("iki katman aynı olayı AYNI dille anlatıyor",
     any("SINANAMADI" in x for x in _uy_eks)
     and "SINANAMADI" in inspect.getsource(metrik.kapsam_kimligi))
sina("sınanamayan kimlik hangi serinin eksik olduğunu OKUR ADIYLA yazıyor",
     any(veri.okur_adi("k_tuzel") in x for x in _uy_eks),
     "; ".join(_uy_eks)[:200])

# MADEN SERİLERİ HİÇBİR KİMLİĞE GİRMİYORDU — oysa altı yayımlanan sayıyı
# besliyorlar (iki seviye, toplamları ve üç pay). Eşitlik kurulamıyor, çünkü
# aradaki para birimi kalemleri (4.4–4.6) bu hatta çekilmiyor; sorulabilen
# soru daha zayıf ama boş değil: alt kalem üst kalemin İÇİNDE mi? Payın
# anlamlı olması buna bağlı.
_maden_kod = {veri.HAFTALIK[a].kod for a in ("maden_gercek", "maden_tuzel")}
_kimlik_metni = " | ".join(_rap_k.keys())
sina("maden serileri artık BİR kimliğe giriyor",
     all(k in _kimlik_metni for k in _maden_kod), str(sorted(_maden_kod)))
_kapsanmalar = [r for r in _rap_k.values() if "maks_pay" in r]
sina("kapsanma temiz çerçevede ölçülüp GEÇİYOR",
     len(_kapsanmalar) == 2 and all(r["gecti"] is True for r in _kapsanmalar)
     and all(0.0 < r["maks_pay"] < 100.0 for r in _kapsanmalar),
     str([round(r["maks_pay"], 1) for r in _kapsanmalar]))
_uyari_sifirla()
_Hm = H0.copy()
_Hm["maden_gercek"] = _Hm["k_gercek"] * 1.04
_uy_m, _rap_m = veri.kimlik_denetimi(_Hm)
_topla(*_uy_m)
sina("alt kalem üst kalemi aşınca KAPSANMA uyarısı düşüyor",
     any(x.startswith("KAPSANMA BOZUK") for x in _uy_m),
     "; ".join(_uy_m)[:200])
sina("kapsanma eşiği UYDURULMUYOR, yayım adımından geliyor",
     all(r["tolerans"] >= 0.0 for r in _kapsanmalar)
     and "yayim_adimi_hal_ic" in _kapsanmalar[0],
     str([r["tolerans"] for r in _kapsanmalar]))
# YAYIMLANAN HER SAYININ BESLENDİĞİ SERİ BİR DENETİME GİRMELİ. Kapsam bir
# listeden değil sözleşmeden türer: kırılım ağacındaki bacaklar kimlikte,
# maden serileri kapsanmada, geniş toplam kapsam ölçümünde.
_kimlikte = {a for k in veri.KIRILIMLAR for a in (k.ust,) + tuple(k.parcalar)}
_kimlikte |= {"stok_gercek", "stok_tuzel", "stok_toplam", "k_gercek",
              "k_tuzel", "maden_gercek", "maden_tuzel"}
_denetimsiz = (set(veri.SIFIR_KAPSAMI) - _kimlikte
               - {"mevduat_yi", "mevduat_tl", "mevduat_yp_tl", "genis_toplam"})
sina("kaynak denetimi dışında kalan seri YOK (lira tabanı ve geniş toplam ayrı)",
     not _denetimsiz, str(sorted(_denetimsiz)))

# KAPSAM SÖZLEŞMEDEN TÜRER. Kırılım ağacına elle bir bacak eklenmeyi unutursa
# o bacağın toplamı hiç sınanmaz ve bakılmayan yer geçen sınavla aynı görünür.
_agac = {a for k in veri.KIRILIMLAR for a in (k.ust,) + tuple(k.parcalar)}
_ayristirma_serileri = {a for a in veri.HAFTALIK
                        if a.startswith(("ar_", "pe_"))}
sina("ayrıştırma tablosunun HER serisi kırılım ağacında (kimlik kapsamı tam)",
     _ayristirma_serileri <= _agac,
     str(sorted(_ayristirma_serileri - _agac)))
sina("kırılım adındaki kalem numaraları KATALOGDAN türetiliyor",
     all(veri.HAFTALIK[k.ust].kod in veri.kirilim_adi(k)
         and veri.HAFTALIK[k.parcalar[0]].kod in veri.kirilim_adi(k)
         for k in veri.KIRILIMLAR))


# ===========================================================================
# 6. DOLARİZASYON — neyin arındırıldığı ETİKETİN kendisidir
# ===========================================================================
# Ölçü YALNIZ PARİTEYİ (çapraz kur ve kıymetli maden fiyatı) arındırır;
# liranın dolar karşısındaki hareketini ARINDIRMAZ. Sayfada "kur etkisinden
# arındırılmış" diye yazılırsa okur yanlış şeyi okur. Ölçü doğru olsa da
# etiket yanlışsa kusur sürer.
print("\n▶ Dolarizasyon: çıpa ve arındırmanın kapsamı")

_uyari_sifirla()
D0, dt0 = metrik.dolarizasyon(H0, A0)
_topla(dt0.get("cumle"), dt0.get("yontem"))
_uyari_al()

_cipa_t = pd.Timestamp(dt0["cipa"])
sina("arındırılmış pay ÇIPADAN ÖNCE boş bırakılıyor",
     bool(D0.loc[D0.index < _cipa_t, "dol_pay_ar"].isna().all())
     and bool(D0.loc[D0.index >= _cipa_t, "dol_pay_ar"].notna().any()),
     f"çıpa {dt0.get('cipa')}")

# İMA EDİLEN KUR SADELEŞİYOR: iki lira bacağı da aynı çarpanla ölçeklenince
# pay kımıldamamalı. Kımıldasaydı ölçünün içinde denetlenemeyen bir kur
# saklanıyor olurdu; künyede referans bir dolar kuru YOK ve ölçülemeyen bir
# şey bir yayımlanan sayının içine gizlenmez.
_esol = H0.copy()
for kol in ("mevduat_tl", "mevduat_yp_tl"):
    _esol[kol] = _esol[kol] * 1.35
De, _ = metrik.dolarizasyon(_esol, A0)
sina("iki lira bacağı birlikte ölçeklenince pay DEĞİŞMİYOR (kur sadeleşiyor)",
     np.isclose(float(D0["dol_pay_ar"].dropna().iloc[-1]),
                float(De["dol_pay_ar"].dropna().iloc[-1]), rtol=1e-12)
     and np.isclose(float(D0["dol_pay_ham"].dropna().iloc[-1]),
                    float(De["dol_pay_ham"].dropna().iloc[-1]), rtol=1e-12))

# Ama YALNIZ yabancı para bacağı hareket ettiğinde pay DEĞİŞMELİ: liranın
# dolar karşısındaki hareketi bu ölçünün DIŞINDADIR ve olması gereken de
# budur. Onu da arındıran bir "iyileştirme" ölçüyü sessizce başka bir şeye
# çevirir ve sayfadaki etiketi yalan yapar.
_tek = H0.copy()
_tek["mevduat_yp_tl"] = _tek["mevduat_yp_tl"] * 1.35
Dt, _ = metrik.dolarizasyon(_tek, A0)
sina("yalnız yabancı para bacağı oynayınca pay DEĞİŞİYOR "
     "(parite arındırılır, liranın hareketi değil)",
     not np.isclose(float(D0["dol_pay_ar"].dropna().iloc[-1]),
                    float(Dt["dol_pay_ar"].dropna().iloc[-1]), rtol=1e-6))

# ÇIPA, OCAK AYININ İLK HAFTASINDA SON HAFTANIN KENDİSİ OLAMAZ.
# `_yil_basi`nin yedek çıpası "yıl içi pencere BOŞSA" diye soruyordu; oysa son
# gözlem her zaman kendi takvim yılının içindedir, yani o küme hiç boşalmaz ve
# yedek dal HİÇ KOŞMAZDI — korumanın var olduğu iddia edilen tek durum,
# korumanın çalışmadığı durumdu. Ölçüldü: çerçeve 1 Ocak 2027'de bitince çıpa
# o haftanın kendisi oluyor, arındırılmış pay tanım gereği ham paya eşit
# çıkıyor ve sayfa "iki ölçünün farkı 0,00 puan" diye YAPISAL bir sıfırı ölçüm
# gibi yayımlıyordu. Sıfır bir ölçüm sonucudur; tanımdan gelen bir sıfır değil.
_idx_ocak = pd.DatetimeIndex(["2026-12-25", "2027-01-01"])
sina("yıl başı çıpası asgari pencereyi sağlamıyorsa YEDEK çıpaya düşüyor",
     metrik._yil_basi(_idx_ocak) == pd.Timestamp("2026-12-25"),
     str(metrik._yil_basi(_idx_ocak)))
sina("yedek çıpa dalı ERİŞİLEBİLİR (asgari pencere eşiği var)",
     metrik.ESIK_CIPA_HAFTA >= 2)

_uyari_sifirla()
Hy = _cerceve(son="2027-01-01")
Dy, dty = metrik.dolarizasyon(Hy, metrik.ayristir(Hy, 0)[0])
_uyari_al()
_topla(dty.get("cumle"))
sina("ocak ayının ilk cumasında çıpa son haftanın KENDİSİ olmuyor",
     dty.get("cipa") is not None
     and pd.Timestamp(dty["cipa"]) < Hy.index[-1],
     f"çıpa {dty.get('cipa')} · son hafta {Hy.index[-1].date()}")
sina("arındırılmış pay ile ham pay farkı YAPISAL sıfır değil",
     dty.get("fark_son") is not None and abs(float(dty["fark_son"])) > 1e-9,
     f"fark {dty.get('fark_son')}")

_uyari_sifirla()
_eksik = H0.drop(columns=["mevduat_tl", "mevduat_yp_tl"])
Dx, dtx = metrik.dolarizasyon(_eksik, A0)
_ux = _uyari_al()
sina("bacaklar yoksa pay UYDURULMUYOR, sebebi yazılıyor",
     Dx.empty and dtx == {} and any("DOLARİZASYON" in x for x in _ux),
     "; ".join(_ux)[:120])


# ===========================================================================
# 7. SIFIR — ölçüm mü, ölçümün yokluğu mu?
# ===========================================================================
# Bir haftanın arındırılmış değişimi gerçekten sıfır olabilir; o bir ÖLÇÜMDÜR
# ve boşaltılmaz. Kardeş bir hatta taşınan fiyattan doğan sahte sıfırlar
# maskelendi, ama orada KANIT vardı (918 iş gününde sıfırların tamamı
# taşımadan doğuyordu). Burada öyle bir kanıt yok: bu hattın serileri
# taşınmıyor, yayım dursa gözlem gelmez ve sıfır GÖRÜNMEZ. Ölçüm katmanının
# kararı bu yüzden ÖLÇ VE YAZ, maskeleme; sınanan da o karar.
print("\n▶ Sıfır ile donma: ölç, maskeleme")

_kol = "ar_gercek_diger"
Hs_sag = _sifir_blok(H0, _kol, 30, sag_uc=True)
_once = Hs_sag[_kol].copy()
uy_s, r_s = metrik.sifir_olc(Hs_sag, veri.SIFIR_KAPSAMI,
                            metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(*uy_s, r_s.get("cumle"))

sina("sağ uçtaki sıfır bloğunun uzunluğu doğru ölçülüyor",
     r_s["seri"][_kol]["sag_uc_sifir_hafta"] == 30,
     str(r_s["seri"][_kol]["sag_uc_sifir_hafta"]))
sina("eşiği aşan sağ uç bloğu uyarı üretiyor",
     r_s["seri"][_kol]["asildi"] is True and bool(uy_s))
sina("uyarı, ikisinin AYIRT EDİLEMEDİĞİNİ söylüyor (hüküm vermiyor)",
     all("ayırt edilemiyor" in x for x in uy_s)
     and "ayırt edilemiyor" in (r_s.get("cumle") or ""),
     "; ".join(uy_s)[:140])
# MASKELEME YOK: değerler sıfır kalır, boşaltılmaz. Boşaltmak "bu bir ölçüm
# değildir" demektir ve bu, ölçülmemiş bir iddia olurdu.
sina("sıfırlar MASKELENMİYOR (çerçeve değişmiyor)",
     Hs_sag[_kol].equals(_once) and bool((Hs_sag[_kol].tail(30) == 0.0).all()))

# Serinin ORTASINDAKİ sıfır bloğu ölçümdür: arkasından gerçek bir gözlem
# gelmiştir. Onu da işaretleyen bir denetim yanlış alarm üretir.
Hs_ic = _sifir_blok(H0, _kol, 30, sag_uc=False)
uy_ic, r_ic = metrik.sifir_olc(Hs_ic, veri.SIFIR_KAPSAMI,
                              metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
sina("serinin ORTASINDAKİ sıfır bloğu sağ uç sayılmıyor",
     r_ic["seri"][_kol]["sag_uc_sifir_hafta"] == 0
     and r_ic["seri"][_kol]["ic_sifir_hafta"] >= 30,
     str(r_ic["seri"][_kol]))
sina("ortadaki blok için uyarı DÜŞMÜYOR (yanlış alarm yok)", not uy_ic,
     "; ".join(uy_ic)[:120])

Hs_kisa = _sifir_blok(H0, _kol, metrik.ESIK_SIFIR_BLOK - 1, sag_uc=True)
uy_kisa, _ = metrik.sifir_olc(Hs_kisa, veri.SIFIR_KAPSAMI,
                             metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
sina("eşiğin altındaki sağ uç bloğu uyarı üretmiyor", not uy_kisa,
     "; ".join(uy_kisa)[:120])

# Hangi bacaklara bakıldığı ve eşiğin ne olduğu bu ölçünün ANLAMINI
# belirliyor; sessizce yanlış kapsamla koşan bir sıfır denetimi hiç
# koşmayandan kötüdür.
try:
    metrik.sifir_olc(H0)          # type: ignore[call-arg]
    _sifir_varsayilani = True
except TypeError:
    _sifir_varsayilani = False
sina("sıfır denetiminin kapsam ve eşik argümanlarının VARSAYILANI yok",
     not _sifir_varsayilani)
# Başlangıcı ölçülmüş serilerin kümesi de aynı sınıftan bir argümandır:
# unutulursa hüküm kapısı sessizce açılır ve ölçülmemiş bir başlangıç üzerine
# yapısal hüküm kurulur — yani kapının hiç konmadığı hâle dönülür.
try:
    metrik.sifir_olc(H0, veri.SIFIR_KAPSAMI,        # type: ignore[call-arg]
                     metrik.ESIK_SIFIR_BLOK)
    _bas_varsayilani = True
except TypeError:
    _bas_varsayilani = False
sina("ölçülmüş başlangıç kümesi argümanının da VARSAYILANI yok",
     not _bas_varsayilani)

# AYNI OLAY İÇİN OKURA TEK CÜMLE. İki katman da uyarı basıyordu ve ikisi
# ÇELİŞİYORDU: veri katmanı "bilgi taşımıyor" diye HÜKÜM veriyor, ölçüm
# katmanı tam da o hükmün verilemeyeceğini söylüyordu; üstelik pencereler
# ayrıydı (52 ve 26) ve okur aynı dört seri için aynı kutuda iki farklı hafta
# sayısı görüyordu. Hüküm vermeyen sürüm doğru olandır; veri katmanı artık
# yalnız makine kaydı yazar.
_olu = veri.olu_seri_olc(Hs_sag)
sina("veri katmanı ölü seriyi MAKİNE kaydına yazıyor, okura cümle KURMUYOR",
     isinstance(_olu, dict) and _kol in _olu["seri"]
     and _olu["pencere_hafta"] == metrik.ESIK_SIFIR_BLOK,
     str({k: _olu.get(k) for k in ("pencere_hafta", "olculen_hafta")}))
sina("sıfır bloğu eşiği TEK tanımdan geliyor",
     metrik.ESIK_SIFIR_BLOK is veri.SIFIR_BLOK_HAFTA)

# --- ÜÇÜNCÜ VE DÖRDÜNCÜ HÂL: SIFIRIN İKİ AYRI SINIFI ------------------------
# İLK GERÇEK KOŞUDA ÖLÇÜLDÜ. Baştan sona sıfır çıkan bacaklar tek bir sınıfta
# toplanıyordu ve tek cümle hepsi için birden "bu bir ölçümdür, donmuş besleme
# değil" diyordu. Ölçüm DONMAYI eliyor — donan bir seri önce sıfırdan farklı
# değerler gösterir, sonra sıfıra düşer; serinin tamamı sıfırsa öncesi yoktur.
# Ama ölçüm ÜÇÜNCÜ bir hâli elemiyor: kaynağın o bacağı hiç hesaplamıyor
# olması. Ve veri o üçüncü hâle işaret ediyordu: dolar DIŞI kese canlı
# (arındırılmış akımının mutlak medyanı 98,5 milyon dolar, 139 haftanın
# 139'unda sıfırdan farklı) ama parite etkisi tam sıfır — oysa dolar dışı bir
# kesenin dolara karşı parite etkisi, çapraz kur kımıldadığı sürece sıfır
# olamaz. Dolar bacaklarında ise sıfır TANIM GEREĞİDİR ve orada "bu bir
# ölçümdür" doğru. Ayırt edilebilene "ayırt edilemiyor" demek yanlıştı;
# ayırt edilemeyene "ölçümdür" demek de yanlış.
print("\n▶ Sıfırın beş hâli: tanım · dayanaksız · hükümsüz · ayırt edilemez · ölçüm")

_uyari_sifirla()
# TANIM SIFIRI ÇERÇEVEDE ZATEN SIFIR (bkz. `_cerceve`), yani bu hâl için
# kurgu gerekmiyor — kaynak gerçekten öyle yayımlıyor.
_TAN = "pe_gercek_usd"
_DAY = "pe_tuzel_diger"
Hy_tam = _sifir_blok(H0, _DAY, len(H0), sag_uc=True)
uy_y, r_y = metrik.sifir_olc(Hy_tam, veri.SIFIR_KAPSAMI,
                             metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(*uy_y, r_y.get("tanim_cumle"), r_y.get("dayanaksiz_cumle"),
       r_y.get("hukumsuz_cumle"), r_y.get("cumle"))

sina("gerekçesi kayıtlı bacakta hâl TANIM SIFIRI",
     r_y["seri"][_TAN]["hal"] == "tanim"
     and r_y["seri"][_TAN]["tanim_gerekcesi"] is True,
     str(r_y["seri"][_TAN]))
sina("gerekçesi olmayan tam sıfırda hâl DAYANAKSIZ",
     r_y["seri"][_DAY]["hal"] == "dayanaksiz"
     and r_y["seri"][_DAY]["sag_uc_sifir_hafta"] == r_y["seri"][_DAY]["n_gozlem"],
     str(r_y["seri"][_DAY]))
sina("iki sınıf AYRI cümlelerde, aynı kutuda toplanmıyor",
     bool(r_y.get("tanim_cumle")) and bool(r_y.get("dayanaksiz_cumle"))
     and r_y["tanim_seri"] >= 1 and r_y["dayanaksiz_seri"] >= 1,
     f"tanım {r_y.get('tanim_seri')} · dayanaksız {r_y.get('dayanaksiz_seri')}")
sina("hiçbiri UYARI üretmiyor (ölçümdür, alarm değil)", not uy_y,
     "; ".join(uy_y)[:160])

# TANIM CÜMLESİ HAFTA SAYMAZ VE SAYMAMALI: hüküm veriden değil aritmetikten
# geliyor. Hafta sayısı yazsaydı okur, sıfırın dayanağını gözlem sayısı
# sanardı — bir hafta ölçülseydi de aynı şey doğru olurdu.
sina("tanım cümlesi dayanağı ARİTMETİK diyor, hafta saymıyor",
     "TANIM GEREĞİDİR" in (r_y.get("tanim_cumle") or "")
     and "çapraz kur" in (r_y.get("tanim_cumle") or "")
     and str(len(H0)) not in (r_y.get("tanim_cumle") or ""),
     (r_y.get("tanim_cumle") or "")[:200])

# --- CÜMLE MEKANİK, SAYI KAYITTA: TASARIM KARARININ SINAMASI --------------
# Bu blok bir zamanlar CÜMLENİN İÇİNDEKİ ifadeleri arıyordu ("Donmuş besleme
# bunu açıklamıyor", "manşet akımın içindedir", "keselerin arındırılmış akımı
# ise hareketli"). Kusurların ezici çoğunluğu tam orada, çok cümleli çok
# kaynaklı metinlerde çıktı: bir cümle altı ölçümü birleştirdiğinde altı
# bağımsız yanlışlaşma yolu açılıyordu. Argüman sayfaya taşındı; koşu kaydı
# ölçümü bildiriyor. Ölçüt de o yüzden metni değil ÖLÇÜMÜ sınıyor — ve
# cümlenin argümanı GERİ GELMEDİĞİNİ ayrıca sınıyor, çünkü bir düzeltmenin en
# kolay geri alınma biçimi cümleye bir cümle daha eklemektir.
_day = r_y.get("dayanaksiz_cumle") or ""
_dy = r_y["dayanaksiz"]
sina("dayanaksız cümlesi ÖLÇÜLEN gözlem sayısını yazıyor",
     (str(len(H0)) in _day or f"{len(H0):,}".replace(",", ".") in _day)
     and _dy["hafta"] == len(H0), _day[:200])
# DONMA ÖLÇÜYLE ELENİYOR — cümlede iddia edilerek değil. Yayımı duran bir
# seri önce sıfırdan farklı değerler gösterir, sonra sıfıra düşer; sınıfın
# koşulu tam olarak budur ve ölçüsü seri kaydında duruyor.
sina("donma cümleyle değil ÖLÇÜYLE eleniyor",
     r_y["seri"][_DAY]["sifirdisi_hafta"] == 0
     and r_y["seri"][_DAY]["sag_uc_sifir_hafta"] == r_y["seri"][_DAY]["n_gozlem"]
     and "Donmuş besleme" not in _day,
     str(r_y["seri"][_DAY]))
sina("dayanaksız cümlesi 'kaynak şöyle hesaplıyor' DEMİYOR",
     "ölçünün yokluğu" in _day and "kaynak" not in _day.lower(), _day[-400:])
# ÖTEKİ BACAKLAR KIYASI ARTIK SAYIDIR. Kıyas kırılımın KENDİ bacaklarından
# kurulur ve başka bir sınıfın sıfırı ona girmez; ikisi de burada ölçülüyor.
# BAŞKA BİR SINIFIN SIFIRI KIYASA GİRMEZ: dolar bacağı da baştan sona sıfır
# (tanım gereği) ve "öteki bacaklar hareket gösteriyor" ölçüsünde sayılsaydı
# ölçü kendi sonucuna aykırı olurdu. Kıyas yalnız DOKUNULAN kırılımın
# içinde kurulur; bütün kırılımlara bakılsaydı ölçü, parite etkisi hakkında
# başka bir tablonun gözlemiyle kurulmuş olurdu.
sina("öteki bacaklar kıyası kırılımın KENDİ bacaklarından ölçülüyor",
     set(_dy["kiyas_oteki_seri"]) == {"pe_tuzel_eur", "pe_tuzel_maden"}
     and "pe_tuzel_usd" not in _dy["kiyas_oteki_seri"]
     and _dy["kiyas_dolu_min_hafta"] > 0,
     str(_dy["kiyas_oteki_seri"]))
# MANŞETE DOKUNAN SONUCUN SAYILARI KAYITTA. Parite etkisi hiç yayımlanmayan
# bir bacakta arındırılmış akım da arındırılmamış olabilir ve o bacak
# manşetin içindedir; o CÜMLE sayfanındır, buradaki SAYI koşu kaydınındır.
sina("dayanaksız sıfırın dokunduğu dilim BÜYÜKLÜĞÜYLE ölçülüyor",
     _dy["dilim_medyan_mn"] > 0 and _dy["manset_medyan_mn"] > 0
     and _dy["dilim_manset_oran_medyan_pay"] > 0
     and _dy["dilim_maks_mn"] >= _dy["dilim_medyan_mn"],
     str({k: _dy[k] for k in ("dilim_medyan_mn", "manset_medyan_mn",
                              "dilim_manset_oran_medyan_pay")}))
# --- E7: ÖLÇÜLEN İLE İDDİA EDİLEN AYNI ŞEY DEĞİL --------------------------
# Cümle "…ama bu dilim kadar bir belirsizlik taşıdığı bilinerek okunur" diye
# bitiyordu: ÖLÇÜLEN şey kesenin AKIMI, İDDİA edilen şey eksik ARINDIRMANIN
# büyüklüğü. İkisi farklı büyüklükler ve cümle onları eşitliyordu. Cümle ile
# sayı ayrıldığında bu eşitlemenin kurulacağı yer de kalmıyor — ölçüt bunu
# YAPISAL olarak sorar: cümlede dilime dair TEK BİR SAYI bile yok.
sina("ölçülen akım, ölçülmemiş arındırma açığına EŞİTLENMİYOR",
     "belirsizlik" not in _day and "dilim" not in _day
     and ozet_uret.cumle_olcusu(_day)[1] <= 1, _day[-360:])
# --- E6: KESE KESE ÖLÇÜLÜR, TOPLANARAK DEĞİL ------------------------------
# Cümle iki AYRI keseyi (gerçek ve tüzel kişilerin diğer para birimleri
# hesapları) toplayıp tekil bir özneyle "aynı kesenin akımı hareketli"
# diyordu. Toplam iki yönde birden yanıltır ve ikisi de burada sınanıyor:
# (i) baştan sona sıfır bir bacak, hareketli bir bacakla toplandığında
# toplam sıfırdan farklı çıkar ve ölü bacak ADIYLA "hareketli" diye geçer;
# (ii) zıt işaretle kımıldayan iki bacak toplamda sıfır verir ve ikisi
# birden hareketsiz görünür. Ölçü bacak bacak yapılıyor ve CÜMLEYE hiç
# girmiyor: bir kese cümlede anılmıyorsa yanlış anılamaz da.
sina("keseler TEK TEK ölçülüyor ve cümlede hiç anılmıyorlar",
     len(_dy["kese_hareketli"]) == 1 and not _dy["kese_durgun"]
     and _dy["kese_olcum"][_dy["kese_hareketli"][0]]["sifirdisi_hafta"] > 0
     and "kese" not in _day, _day[:900])

# İKİ KESELİ ÇERÇEVE: kusurun kendisi iki keseyi TOPLAMAKTAN doğuyordu,
# öyleyse senaryo da iki keseli olmalı. Tek keseli bir çerçevede toplam ile
# bacak ölçüsü aynı sayıyı verir ve sınama, kapattığı kusuru hiç göremezdi.
Hy_ikikese = _sifir_blok(Hy_tam, "pe_gercek_diger", len(H0), sag_uc=True)
_, r_iki = metrik.sifir_olc(Hy_ikikese, veri.SIFIR_KAPSAMI,
                            metrik.ESIK_SIFIR_BLOK,
                            veri.bas_olculen(Hy_ikikese))
_iki = r_iki.get("dayanaksiz_cumle") or ""
_topla(_iki)
sina("iki ayrı kese TEKİL bir özneyle 'aynı kese' diye anılmıyor",
     r_iki["dayanaksiz_seri"] == 2
     and len(r_iki["dayanaksiz"]["kese_hareketli"]) == 2
     and "kese" not in _iki, _iki[:900])

_Hy_yari = Hy_ikikese.copy()
_Hy_yari["ar_gercek_diger"] = 0.0          # bir kese ölü, öteki canlı
_, r_yari = metrik.sifir_olc(_Hy_yari, veri.SIFIR_KAPSAMI,
                             metrik.ESIK_SIFIR_BLOK,
                             veri.bas_olculen(_Hy_yari))
_yari = r_yari.get("dayanaksiz_cumle") or ""
_topla(_yari)
sina("baştan sona sıfır bir kese 'hareketli' diye ANILMIYOR",
     r_yari["dayanaksiz"]["kese_durgun"] == ["ar_gercek_diger"]
     and r_yari["dayanaksiz"]["kese_hareketli"] == ["ar_tuzel_diger"]
     and veri.okur_adi("ar_gercek_diger") not in _yari,
     _yari[:900])
# ÖLÇÜMÜ TUTMAYAN KESE GİZLENMİYOR: kendi ölçüsüyle kayda giriyor ve özete
# sayıyla çıkıyor. Cümleden düşmek görünmezlik değil; görünmezlik, hiçbir
# yerde ölçülmemiş olmaktır.
sina("ölçümü tutmayan kese ÖLÇÜYLE kayda geçiyor",
     r_yari["dayanaksiz"]["kese_olcum"]["ar_gercek_diger"]["sifirdisi_hafta"] == 0
     and r_yari["dayanaksiz"]["kese_olcum"]["ar_gercek_diger"]["hafta"] > 0,
     str(r_yari["dayanaksiz"]["kese_olcum"]["ar_gercek_diger"]))

# (ii) MAHSUP: iki kese zıt işaretle kımıldarsa TOPLAM sıfır olur. Toplanan
# ölçüde bu "iki kese de hareketsiz" demektir; bacak bacak ölçüde ikisi de
# hareketlidir ve dilimin büyüklüğü MUTLAK değerlerden toplanır.
_Hy_mahsup = Hy_ikikese.copy()
_Hy_mahsup["ar_tuzel_diger"] = -_Hy_mahsup["ar_gercek_diger"]
_, r_mah = metrik.sifir_olc(_Hy_mahsup, veri.SIFIR_KAPSAMI,
                            metrik.ESIK_SIFIR_BLOK,
                            veri.bas_olculen(_Hy_mahsup))
_mah = r_mah.get("dayanaksiz_cumle") or ""
_topla(_mah)
_isaretli = float((_Hy_mahsup["ar_gercek_diger"]
                   + _Hy_mahsup["ar_tuzel_diger"]).abs().median())
sina("zıt işaretli iki kese MAHSUP EDİLMİYOR (dilim mutlak toplanıyor)",
     len(r_mah["dayanaksiz"]["kese_hareketli"]) == 2
     and _isaretli == 0.0
     and r_mah["dayanaksiz"]["dilim_medyan_mn"] > 0,
     f"işaretli medyan {_isaretli} · dilim "
     f"{r_mah['dayanaksiz'].get('dilim_medyan_mn')}")

_Hy_olu = Hy_ikikese.copy()
for _c in ("ar_gercek_diger", "ar_tuzel_diger"):
    _Hy_olu[_c] = 0.0
_, r_olu = metrik.sifir_olc(_Hy_olu, veri.SIFIR_KAPSAMI,
                            metrik.ESIK_SIFIR_BLOK,
                            veri.bas_olculen(_Hy_olu))
sina("kese de ölüyse 'hareketli' kümesi BOŞ kalıyor",
     not r_olu["dayanaksiz"]["kese_hareketli"]
     and len(r_olu["dayanaksiz"]["kese_durgun"]) == 2,
     str(r_olu["dayanaksiz"]["kese_durgun"]))
# EŞLEME AĞAÇTAN TÜRETİLİYOR: dize ameliyatıyla kurulan bir eş, bir ad
# değiştiği gün sessizce yanlış bacağı gösterirdi.
sina("parite bacağının arındırılmış eşi KIRILIM AĞACINDAN çözülüyor",
     veri.arindirilmis_esi("pe_tuzel_diger") == "ar_tuzel_diger"
     and veri.arindirilmis_esi("ar_tuzel_diger") is None,
     str(veri.arindirilmis_esi("pe_tuzel_diger")))

# ÖTEKİ BACAKLAR SIFATLA DEĞİL SAYIYLA ANLATILIR: bir bacak otuz hafta
# sustuğunda cümle bunu göstermeli, yoksa okur ölçülmemiş bir kesinlik okur.
_uyari_sifirla()
_Hy_seyrek = _sifir_blok(Hy_tam, "pe_tuzel_eur", 30, sag_uc=True)
_, r_yb = metrik.sifir_olc(_Hy_seyrek, veri.SIFIR_KAPSAMI,
                           metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(r_yb.get("dayanaksiz_cumle"), r_yb.get("cumle"))
# BEKLENEN SAYI ÇERÇEVEDEN ÖLÇÜLÜR, elle yazılmaz: susturulan haftaların
# yanında yuvarlamadan doğan sıfırlar da var ve elle yazılmış bir sayı
# ("653 − 30") sınamayı gerçek ölçüden ayırırdı.
_bekle = min(int((_Hy_seyrek[c].dropna() != 0).sum())
             for c in ("pe_tuzel_eur", "pe_tuzel_maden"))
sina("öteki bacak arada sustuğunda ÖLÇÜLEN hafta sayısı kayda giriyor",
     _bekle < len(H0) - 20
     and r_yb["dayanaksiz"]["kiyas_dolu_min_hafta"] == _bekle
     and r_yb["dayanaksiz"]["kiyas_kapsam_min_hafta"] >= _bekle,
     f"beklenen {_bekle} · ölçülen "
     f"{r_yb['dayanaksiz'].get('kiyas_dolu_min_hafta')}")

# --- ADLANDIRMA İLE ÖLÇÜM AYNI SERİ KÜMESİNDEN TÜRER ------------------------
# BU CÜMLE KENDİ İZLEDİĞİ OLAYDA KIRILIYORDU. Kıyas kısa adlarla kuruluyor
# ("euro ve kıymetli maden") ama sayılar seri seri ölçülüyordu ve iki küme
# AYRI süzülüyordu: adı anılmayan bir bacağın gözlem sayısı, anılan bacaklara
# yakıştırılıyordu. Yapısal bir bacak bir gün sıfırdan farklı bir değer
# yayımlarsa — kapının izlediği olayın ta kendisi — kısa adı hem sıfır hem
# hareketli kümede birden geçer; ölçülen sayı 1 hafta olur ve cümle onu
# 653 haftalık bacaklara yakıştırır. Doğrusu: kısa ad ayırt edici değilse
# parça HİÇ YAZILMAZ.
# (a) İZLENEN OLAYIN KENDİSİ: yapısal bir bacak bir hafta değer yayımlıyor.
_uyari_sifirla()
_Hy_iki_day = _sifir_blok(Hy_tam, "pe_gercek_diger", len(Hy_tam), sag_uc=True)
_Hy_uyanan = _Hy_iki_day.copy()
_Hy_uyanan.iloc[-1, _Hy_uyanan.columns.get_loc("pe_gercek_diger")] = 12.5
_, r_uy = metrik.sifir_olc(_Hy_uyanan, veri.SIFIR_KAPSAMI,
                           metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(r_uy.get("dayanaksiz_cumle"))
_d_uy = r_uy.get("dayanaksiz_cumle") or ""
sina("uyanan bacağın 1 haftası öteki bacaklara YAKIŞTIRILMIYOR",
     re.search(r"(?<!\d)1 hafta", _d_uy) is None, _d_uy[:600])
sina("uyanan bacak 'baştan sona sıfır' listesinde ANILMIYOR",
     veri.okur_adi("pe_gercek_diger") not in _d_uy, _d_uy[:400])
sina("uyanan bacak hakkında 'hiç yayımlanmadı' hükmü KURULMUYOR",
     r_uy["seri"]["pe_gercek_diger"]["hal"] != "dayanaksiz"
     and r_uy["dayanaksiz_seri"] == 1,
     str(r_uy["seri"]["pe_gercek_diger"]["hal"]))

# (b) KISA AD AYIRT EDİCİ OLMADIĞINDA PARÇA HİÇ YAZILMAZ. İki ayrı kırılımda
# iki ayrı para birimi bacağı dayanaksız sıfır olursa, birinin kısa adı
# ötekinin "hareketli" kümesinde geçer: aynı ad hem sıfır hem hareketli
# tarafta durur ve cümle hangisini anlattığını söyleyemez.
_uyari_sifirla()
# İKİ BACAK DA KÜNYEDEN SEÇİLİR: dayanaksız sınıfına girmek için başlangıcı
# ÖLÇÜLMÜŞ ve tanım gerekçesi OLMAYAN bacak gerek. Elle seçilen bir çift, bir
# gün kanıt alanı doldukça sessizce başka bir sınıfa kayar ve senaryo hiç
# kurulmadan geçerdi.
_cak_aday = [a for k in veri.KIRILIMLAR for a in k.parcalar
             if a.startswith("pe_") and a in veri.BAS_OLCULEN
             and a not in veri.TANIM_SIFIRI]
_cak_cift = ["pe_gercek_eur", "pe_tuzel_diger"]
assert set(_cak_cift) <= set(_cak_aday), _cak_aday
_Hy_cak = H0.copy()
for _c in _cak_cift:
    _Hy_cak = _sifir_blok(_Hy_cak, _c, len(H0), sag_uc=True)
_, r_cak = metrik.sifir_olc(_Hy_cak, veri.SIFIR_KAPSAMI,
                            metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(r_cak.get("dayanaksiz_cumle"))
_d_cak = r_cak.get("dayanaksiz_cumle") or ""
sina("kısa ad iki kümede birden geçince ÇAKIŞMA kayda geçiyor",
     set(r_cak["dayanaksiz"]["kiyas_belirsiz_kisa_ad"])
     == {"euro", "diğer para birimleri"} and r_cak["dayanaksiz_seri"] == 2,
     str(r_cak["dayanaksiz"]["kiyas_belirsiz_kisa_ad"]))
# ÇAKIŞMA CÜMLEYİ DEĞİL SAYFAYI BAĞLAR. Kısa ad kıyası cümleden çıktı; ama
# ölçü kaldı, çünkü sayfayı yazan oturumun bu tuzağı görmesi gerekiyor —
# ayırt edici olmayan bir kısa adla kurulmuş bir nesir, aynı kusuru sayfada
# yeniden üretirdi. Ölçülen bir şeyi ölçmeyi bırakmak, kusuru
# görünmezleştirmenin en sessiz biçimidir.
# ÇAKIŞMA ARTIK CÜMLEYİ DÜŞÜREMEZ, ÇÜNKÜ KIYAS CÜMLEDE YOK. Kısa ad yalnız
# seri KÜNYESİNİN içinde geçiyor ("… gerçek kişiler, euro (TP.HPBITABLO5.15)")
# ve künye okura verilen bir adrestir, bizim kurduğumuz bir kıyas değil.
# Ölçüt bu yüzden kıyas KURULMADIĞINI sorar, kısa adın hiç geçmediğini değil —
# ikincisi yanlış alarm üretirdi ve yanlış alarm veren bir ölçüte kimse bakmaz.
sina("çakışan kısa ad ölçülüyor ama cümlede KIYAS kurulmuyor",
     len(r_cak["dayanaksiz"]["kiyas_belirsiz_kisa_ad"]) == 2
     and "öteki bacak" not in _d_cak and "hareket" not in _d_cak,
     _d_cak[:600])
sina("çakışmada bile ölçülen sıfırın kendisi YAZILMAYA devam ediyor",
     "tamamında tam sıfır" in _d_cak and "ölçünün yokluğu" in _d_cak,
     _d_cak[:240])

# İKİNCİ HÂL KORUNUYOR: sıfırdan farklı gözlemlerin ARDINDAN gelen sağ uç
# bloğu gerçekten ayırt edilemez ve uyarısı DURUYOR. Yeni sınıfları tanıyan
# bir düzeltmenin en kolay kaza biçimi, bu hâli de sessizce yutmasıdır.
sina("sıfırdan farklı gözlemden SONRA gelen blok hâlâ AYIRT EDİLEMEZ",
     r_s["seri"][_kol]["hal"] == "ayirt_edilemez", str(r_s["seri"][_kol]))
sina("ortadaki blok ÖLÇÜM olarak sınıflanıyor",
     r_ic["seri"][_kol]["hal"] == "olcum", str(r_ic["seri"][_kol]))

# İKİSİ AYNI KOŞUDA BİRLİKTE OLABİLİR ve AYRI cümlelerdir.
_uyari_sifirla()
Hy_iki = _sifir_blok(Hy_tam, _kol, 30, sag_uc=True)
uy_i, r_i = metrik.sifir_olc(Hy_iki, veri.SIFIR_KAPSAMI,
                             metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(*uy_i, r_i.get("dayanaksiz_cumle"), r_i.get("cumle"))
sina("dayanaksız sıfır ile donma aynı koşuda AYRI cümlelerde",
     bool(r_i.get("dayanaksiz_cumle")) and bool(r_i.get("cumle"))
     and r_i["dayanaksiz_seri"] == 1 and r_i["asan_seri"] == 1,
     f"dayanaksız {r_i.get('dayanaksiz_seri')} · aşan {r_i.get('asan_seri')}")
sina("donma uyarısı dayanaksız seriyi ADIYLA ANMIYOR",
     bool(uy_i) and veri.okur_adi(_DAY) not in uy_i[0],
     "; ".join(uy_i)[:160])

# --- DÖRT CÜMLE HER KOŞUDA YAZILIR -----------------------------------------
# Bulgu varken yazılıp yokken düşen bir anahtar sayfada STATİK YEDEĞE düşer:
# hüküm tam yanlışlaştığı anda okur eski cümleyi okumaya devam eder — yani
# anahtar, en çok gerektiği gün donar. Kardeş okur cümleleri (tazelik,
# kapsam) bulgu yokken de "yok" metniyle yazılıyor.
_uyari_sifirla()
_, r_bos = metrik.sifir_olc(H0, veri.SIFIR_KAPSAMI, metrik.ESIK_SIFIR_BLOK,
                            veri.BAS_OLCULEN)
_topla(r_bos.get("tanim_cumle"), r_bos.get("dayanaksiz_cumle"),
       r_bos.get("hukumsuz_cumle"), r_bos.get("cumle"))
sina("bulgu yokken de DÖRT cümlenin dördü yazılıyor",
     all(bool(r_bos.get(a)) for a in ("tanim_cumle", "dayanaksiz_cumle",
                                      "hukumsuz_cumle", "cumle")),
     str({a: bool(r_bos.get(a)) for a in ("tanim_cumle", "dayanaksiz_cumle",
                                          "hukumsuz_cumle", "cumle")}))
# BOŞ SINIF BAYRAK TAŞIR, CÜMLE DEĞİL (E8'in genelleştirmesi). Boş bir
# sınıfın metni sınıflandırmanın sonucunu bildirir, verinin özelliğini değil:
# "hiçbiri baştan sona sıfır değil" bir VERİ iddiasıdır ve baştan sona sıfır
# bacaklar başka bir sınıfa düşmüşse aynı koşuda ölçülmüş bir gerçeği yalanlar.
sina("bulgu yokken metin BAYRAK, boş da kalmıyor",
     r_bos.get("dayanaksiz_cumle") == metrik.SINIF_BOS
     and r_bos.get("cumle") == metrik.SINIF_BOS,
     (r_bos.get("dayanaksiz_cumle") or "")[:160])
sina("boş sınıf bayrağı hiçbir SAYI ve hiçbir veri iddiası taşımıyor",
     ozet_uret.cumle_olcusu(metrik.SINIF_BOS) == (1, 0)
     and "sıfır" not in metrik.SINIF_BOS, metrik.SINIF_BOS)
_bos_H = H0.iloc[0:0]
_, r_hic = metrik.sifir_olc(_bos_H, veri.SIFIR_KAPSAMI,
                            metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(r_hic.get("tanim_cumle"), r_hic.get("dayanaksiz_cumle"),
       r_hic.get("hukumsuz_cumle"), r_hic.get("cumle"))
# ÖLÇÜLEMEDİ İLE BOŞ SINIF AYRI ŞEYLERDİR ve ikisi aynı bayrağa düşmemeli:
# biri "ölçtük, sınıf boş", öteki "hiç ölçemedik". Aynı metni yazsalardı okur
# bir arızayı sağlıklı bir koşu sanardı.
sina("hiç gözlem yokken boş sınıf bayrağı DEĞİL, sebebi yazılıyor",
     all("gözlem yüklenemedi" in (r_hic.get(a) or "")
         and r_hic.get(a) != metrik.SINIF_BOS
         for a in ("tanim_cumle", "dayanaksiz_cumle", "hukumsuz_cumle",
                   "cumle")),
     (r_hic.get("cumle") or "")[:160])

# --- TANIM SIFIRININ ÇELİŞMESİ ÖLÇÜLÜYOR -----------------------------------
# Kayda geçmiş bir gerekçe, sıfırın ölçülmeden önce bilindiğini söyler. O
# bacakta sıfırdan farklı bir değer çıkarsa yanlış olan gerekçe ya da kalem
# eşleşmesidir. Hiçbir denetimin bakmadığı bir iddia, sınanmamış bir kural
# olarak kalır — bir iddianın yanlışlanabilir olması onun ölçülebilir
# olmasıdır.
_uyari_sifirla()
_Hy_celiski = Hy_tam.copy()
_Hy_celiski.iloc[-3:, _Hy_celiski.columns.get_loc(_TAN)] = 41.0
uy_c, r_c = metrik.sifir_olc(_Hy_celiski, veri.SIFIR_KAPSAMI,
                             metrik.ESIK_SIFIR_BLOK, veri.BAS_OLCULEN)
_topla(*uy_c)
sina("tanım gereği sıfır bacakta değer çıkarsa ÇELİŞKİ uyarısı düşüyor",
     r_c["celiskili_seri"] == 1
     and any(x.startswith("TANIM SIFIRI ÇELİŞİYOR") for x in uy_c),
     "; ".join(uy_c)[:200])
sina("çelişen bacak TANIM sınıfına da girmiyor",
     r_c["seri"][_TAN]["hal"] != "tanim"
     and veri.okur_adi(_TAN) not in (r_c.get("tanim_cumle") or ""),
     r_c["seri"][_TAN]["hal"])

# --- BEŞİNCİ HÂL: ÖLÇÜLMEMİŞ BAŞLANGIÇ ÜZERİNE HÜKÜM KURULMAZ --------------
# DAYANAKSIZ SIFIR HÜKMÜNÜN TEK DAYANAĞI "serinin öncesi yok" cümlesidir ve o
# cümle ancak elimizdeki ilk gözlem SERİNİN ilk gözlemiyse doğrudur. Bu hatta
# öyle değildi: katalogdaki başlangıç elle yazılmış bir sabitti, çekimin alt
# sınırıydı ve kapsam denetiminin ölçütüydü — üç yer birbirini doğruluyor
# görünürken hiçbiri ölçmüyordu. Kapı hükmün SONUCUNU değil DAYANAĞINI sorar.
print("\n▶ Hüküm kapısı: ölçülmemiş başlangıç hüküm taşımaz")

_uyari_sifirla()
uy_hs, r_hs = metrik.sifir_olc(Hy_tam, veri.SIFIR_KAPSAMI,
                               metrik.ESIK_SIFIR_BLOK,
                               tuple(a for a in veri.BAS_OLCULEN if a != _DAY))
_topla(*uy_hs, r_hs.get("hukumsuz_cumle"), r_hs.get("dayanaksiz_cumle"))
sina("başlangıcı ölçülmemiş seri DAYANAKSIZ sayılmıyor",
     r_hs["seri"][_DAY]["hal"] == "bas_olculmedi"
     and r_hs["dayanaksiz_seri"] == 0 and r_hs["hukumsuz_seri"] == 1,
     str(r_hs["seri"][_DAY]))
sina("hükümsüz seri için dayanaksız sıfır cümlesi KURULMUYOR",
     r_hs.get("dayanaksiz_cumle") == metrik.SINIF_BOS,
     (r_hs.get("dayanaksiz_cumle") or "")[:120])
# Sıfırın kendisi ÖLÇÜLDÜ ve yazılır; ölçülmeyen şey onun ne anlama geldiği.
sina("ölçülen sıfır YİNE DE yazılıyor, eksik olan cümlede anılıyor",
     "tam sıfır" in (r_hs.get("hukumsuz_cumle") or "")
     and "ölçülmedi" in (r_hs.get("hukumsuz_cumle") or "")
     and r_hs["hukumsuz_tani"]["hafta"] == len(Hy_tam),
     (r_hs.get("hukumsuz_cumle") or "")[:200])
# "Ayırt edilemiyor" BAŞKA bir hâldir: orada kaynak belirsiz, burada eksik
# olan bizim ölçümümüz.
sina("hükümsüz hâl 'ayırt edilemiyor' DİYE anlatılmıyor",
     "ayırt edilemiyor" not in (r_hs.get("hukumsuz_cumle") or "")
     and not uy_hs, (r_hs.get("hukumsuz_cumle") or "")[:160])
# Başlangıç ölçüldüğü an hüküm KENDİLİĞİNDEN kurulur: kapı bir yasak değil,
# eksik bir ölçümün adıdır.
sina("başlangıç ölçülünce aynı veri DAYANAKSIZ hükmünü taşıyor",
     r_y["seri"][_DAY]["hal"] == "dayanaksiz" and r_y["dayanaksiz_seri"] >= 1
     and r_y.get("hukumsuz_cumle") == metrik.SINIF_BOS,
     f"{r_y['seri'][_DAY]['hal']} · hükümsüz {r_y.get('hukumsuz_seri')}")
# --- KAPININ İKİNCİ YARISI: KIRPILMIŞ ÇERÇEVEDE HÜKÜM KURULMAZ ------------
# ARIZANIN KENDİSİ: kapı yalnız KATALOĞU soruyordu ("kaynağın ilk gözlemi
# ölçüldü mü") ve elimizdeki çerçevenin o başlangıca uzanıp uzanmadığını HİÇ
# sormuyordu. Kırpılmış bir tarihçe ile tam bir tarihçe, katalog tarafından
# bakıldığında TIPATIP AYNI görünür: katalog 2014 derken elde 2024'te başlayan
# 139 haftalık bir çerçeve varken "bu bacağın öncesi yok, üzerine hüküm
# kurulabilir" cümlesi kuruluyordu — 514 hafta hiç görülmeden.
_kirpik_c = Hy_ikikese.loc[pd.Timestamp("2024-01-05"):]
_, r_kirp = metrik.sifir_olc(_kirpik_c, veri.SIFIR_KAPSAMI,
                             metrik.ESIK_SIFIR_BLOK,
                             veri.bas_olculen(_kirpik_c))
_kirp_c = r_kirp.get("hukumsuz_cumle") or ""
_topla(_kirp_c, r_kirp.get("dayanaksiz_cumle"), r_kirp.get("cumle"))
sina("kırpılmış çerçevede yapısal hüküm KURULMUYOR",
     r_kirp["dayanaksiz_seri"] == 0 and r_kirp["hukumsuz_seri"] == 2
     and r_iki["dayanaksiz_seri"] == 2,
     f"kırpık dayanaksız {r_kirp['dayanaksiz_seri']} hükümsüz "
     f"{r_kirp['hukumsuz_seri']} · tam dayanaksız {r_iki['dayanaksiz_seri']}")
# Kapının HANGİ yarısının düştüğü okura yazılır: kaynağın başlangıcı ölçülü
# olabilir ve eksik olan bizim çekimimiz olabilir. Tek bir "ölçülmedi"
# cümlesi bu hâlde okuru eksiği kaynakta aramaya gönderirdi.
# KAPININ HANGİ YARISI DÜŞTÜ — ARTIK SAYIYLA. Cümlede üç şerh vardı ve biri
# bir turda YANLIŞ da yazdı; iki yarı ayrı sayılara indi, cümle tarafsız
# açılışta kaldı ("bu koşuda ölçülmedi" ikisini de kapsar; "kaynakta ne zaman
# yayımlanmaya başladığı ölçülmedi" ikinci yarıda okuru eksiği KAYNAKTA
# aramaya gönderirdi).
sina("düşen yarı SAYIYLA kayda geçiyor, cümle tarafsız açılıyor",
     r_kirp["hukumsuz_tani"]["bas_kirpik_seri"] == 2
     and r_kirp["hukumsuz_tani"]["bas_kanitsiz_seri"] == 0
     and "bu koşuda ölçülmedi" in _kirp_c
     and "kaynak" not in _kirp_c.lower(), _kirp_c[:300])
# KATALOG SABİTİ İLE ÇERÇEVE KAPISI GERÇEKTEN AYRIŞIYOR: ayrışmasaydı bu
# sınama, kapattığı kusuru hiç göremezdi (vakumda geçen bir ölçüt).
sina("katalog sayımı ile çerçeve kapısı kırpılmış veride AYRIŞIYOR",
     set(veri.bas_olculen(_kirpik_c)) < set(veri.BAS_OLCULEN)
     and set(veri.bas_olculen(Hy_ikikese)) == set(veri.BAS_OLCULEN),
     f"kırpık {len(veri.bas_olculen(_kirpik_c))} · "
     f"tam {len(veri.bas_olculen(Hy_ikikese))} · katalog {len(veri.BAS_OLCULEN)}")
# ÖLÇÜM KATMANI KAPIYA ÇERÇEVEYİ VERİYOR MU — davranışla sınanamaz, çünkü
# katalog sabitine geri dönüldüğünde ÇIKTI temiz çerçevede DEĞİŞMEZ; kusur
# yalnız kırpılmış bir koşuda görünür ve o koşu burada kurulmuyor.
# --- "YOK" CÜMLESİ SINIFLANDIRMAYI ANLATIR, VERİYİ DEĞİL -------------------
# ARIZANIN KENDİSİ: iki cümle, bir SINIFIN boş olmasını VERİNİN bir özelliği
# gibi yazıyordu. (1) "Sağ ucunda eşikten uzun kesintisiz sıfır taşıyan bir
# bacak bu koşuda yok" — oysa koşul yalnız AYIRT EDİLEMEZ sınıfının boş
# olmasıydı; baştan sona sıfır bacaklar o sınıfa hiç girmiyor (öncesinde
# sıfırdan farklı gözlem aranıyor), yani sağ ucunda yüz otuz dokuz haftalık
# kesintisiz sıfır taşıyan dört bacak dururken cümle "yok" diyordu.
# (2) "Ölçülen serilerin hiçbiri elimizdeki haftaların tamamında sıfır değil"
# — oysa koşul DAYANAKSIZ sınıfının boş olmasıydı ve o bacaklar başka bir
# sınıfa düşmüş olabilir. İkisi de aynı koşuda ölçülmüş bir gerçeği yalanlar.
_tam0 = [a for a in veri.SIFIR_KAPSAMI
         if a in _kirpik_c.columns and not _kirpik_c[a].dropna().empty
         and bool((_kirpik_c[a].dropna() == 0).all())]
_c_kirp, _d_kirp = r_kirp["cumle"], r_kirp["dayanaksiz_cumle"]
_topla(_c_kirp, _d_kirp)
# İKİNCİ DENEME DE YETMEDİ, KUSUR SINIFI CÜMLENİN KENDİSİNDEYDİ. İlk sürüm
# "yok" diyordu ve yanlıştı; ikincisi kapsamı cümlenin içine yazdı (üç ölçüm,
# iki cümle) ve doğruydu ama aynı tuzağı taşıyordu — bir sonraki sınıf
# eklendiğinde yine elle güncellenmesi gereken bir metin. Üçüncüsü cümleyi
# BAYRAĞA indirdi ve sayıyı kendi anahtarına koydu: sınıfların sayımları
# ayrı ayrı ölçülüyor, hangisinin hangisiyle birlikte anılacağına sayfa
# karar veriyor.
sina("baştan sona sıfır bacaklar VARKEN sayımı kayda geçiyor",
     len(_tam0) == 4 and r_kirp["tam_sifir_seri"] == 4
     and (r_kirp["tanim_seri"] + r_kirp["dayanaksiz_seri"]
          + r_kirp["hukumsuz_seri"]) == 4,
     f"ölçülen tam sıfır {len(_tam0)} · kayıt {r_kirp['tam_sifir_seri']}")
sina("boş sınıfın bayrağı BAŞKA sınıfın sayısını anmıyor",
     _d_kirp == metrik.SINIF_BOS and _c_kirp == metrik.SINIF_BOS
     and b.sayi(len(_tam0), 0) not in _d_kirp, _d_kirp[:240])
sina("sağ uç sınıfının kendi ölçüsü kayda geçiyor",
     r_kirp["ayirt_edilemez_maks_hafta"] == 0
     and r_kirp["asan_seri"] == 0,
     f"{r_kirp['ayirt_edilemez_maks_hafta']} hafta")
# TERS HÂL: gerçekten hiçbir bacak baştan sona sıfır değilse cümleler DÜZ
# hâllerini alır. Yalnız biri sınansaydı ölçüt, eklediği ekin her koşuda
# basıldığı bir sürümü de geçerdi.
_Hy_sifirsiz = H0.copy()
_rng8 = np.random.default_rng(4242)
for _c8 in veri.TANIM_SIFIRI:
    _Hy_sifirsiz[_c8] = _rng8.normal(0.0, 50.0, len(_Hy_sifirsiz)).round(1)
_uy8, r_t8 = metrik.sifir_olc(_Hy_sifirsiz, veri.SIFIR_KAPSAMI,
                              metrik.ESIK_SIFIR_BLOK,
                              veri.bas_olculen(_Hy_sifirsiz))
_topla(*_uy8, r_t8["cumle"], r_t8["dayanaksiz_cumle"])
sina("hiç tam sıfır yokken de AYNI bayrak yazılıyor (metin dallanmıyor)",
     (r_t8["tanim_seri"] + r_t8["dayanaksiz_seri"] + r_t8["hukumsuz_seri"]) == 0
     and r_t8["tam_sifir_seri"] == 0
     and r_t8["cumle"] == r_t8["dayanaksiz_cumle"] == metrik.SINIF_BOS,
     f"{r_t8['dayanaksiz_cumle'][:120]}")

# ÖLÇÜT YORUMLARI SAYMAZ: gerekçe yorumunda geçen bir sabit adı, kodun o
# sabiti KULLANDIĞI anlamına gelmez. Yorumu da sayan ilk sürüm tam bu yüzden
# yanlış alarm verdi — ve yayının önünde duran bir ölçütün yanlış alarmı,
# arızanın kendisidir.
_kos_kod = "\n".join(
    s for s in inspect.getsource(metrik.kos).splitlines()
    if not s.lstrip().startswith("#"))
sina("ölçüm katmanı hüküm kapısına ÇERÇEVEYİ veriyor (sabiti değil)",
     "veri.bas_olculen(H)" in _kos_kod
     and "veri.BAS_OLCULEN" not in _kos_kod,
     "metrik.kos katalog sabitini kullanıyor")

# KAPI YALNIZ DAYANAĞI KULLANAN SINIFA UYGULANIR. Tanım sıfırı "serinin
# öncesi yok" cümlesini hiç kullanmıyor; ona da uygulansaydı, aritmetikle
# bilinen bir şey ölçülmediği için söylenmemiş olurdu — ve aynı kutuda iki
# özdeş bacak (iki dolar bacağı) iki ayrı hikâye anlatırdı.
sina("tanım sıfırı, başlangıcı ölçülmemiş olsa da hükmünü taşıyor",
     not veri.bas_olculdu("pe_tuzel_usd")
     and r_y["seri"]["pe_tuzel_usd"]["hal"] == "tanim",
     str(r_y["seri"]["pe_tuzel_usd"]))
# ÖLÇÜLMEMİŞ BAŞLANGIÇ TANIM SINIFINDA DA KAYDA GEÇER — ama cümlede değil.
# Tanım hükmü o ölçüme HİÇ dayanmıyor; cümlede anılması okura hükmün ona
# dayandığını düşündürüyordu ve şerh bir turda yanlış da yazdı. Sayı duruyor,
# hükmün neye dayanmadığını sayfa anlatıyor.
sina("ölçülmemiş başlangıç tanım SINIFINDA sayıyla kayda geçiyor",
     not veri.bas_olculdu("pe_tuzel_usd")
     and r_y["tanim_tani"]["bas_kanitsiz_seri"] == 1
     and "pe_tuzel_usd" in r_y["tanim_tani"]["bas_kanitsiz"]
     and "ölçülmedi" not in (r_y.get("tanim_cumle") or ""),
     str(r_y["tanim_tani"]))
# --- AYNI KUSUR TANIM CÜMLESİNDE DE VARDI (genelleştirme) ------------------
# Bir kusur bulunduğunda sorulacak soru "bu cümleyi düzelttim mi" değil, "bu
# kusur başka nerede olabilir"dir. Hüküm kapısı çerçeveyi de sormaya
# başlayınca tanım cümlesinin tek gerekçesi ("kaynakta ne zaman yayımlanmaya
# başladığı ölçülmedi") kırpılmış bir koşuda YANLIŞLAŞTI: kaynağın ilk
# gözlemi ölçülü olabiliyor ve eksik olan bizim çekimimiz oluyor — cümle ise
# okuru eksiği KAYNAKTA aramaya gönderiyordu. Ölçüldü: kırpılmış çerçevede
# kanıtı OLAN bir bacak (dolar bacağının parite etkisi) o cümleyle anılıyordu.
_tc_kirp = r_kirp["tanim_cumle"]
_tt_kirp = r_kirp["tanim_tani"]
_topla(_tc_kirp)
sina("kırpılmış çerçevede iki sebep AYRI AYRI sayılıyor",
     veri.bas_olculdu("pe_gercek_usd")
     and _tt_kirp["bas_kirpik"] == ["pe_gercek_usd"]
     and _tt_kirp["bas_kanitsiz"] == ["pe_tuzel_usd"]
     and not veri.bas_olculdu("pe_tuzel_usd"),
     str(_tt_kirp))
# CÜMLE HİÇBİR SEBEBİ ANLATMIYOR — ve anlatmaması bir kayıp değil: tek bir
# "ölçülmedi" cümlesi ikinci hâlde okuru eksiği KAYNAKTA aramaya gönderirdi,
# iki cümle ise sınıfın dayanmadığı bir ölçümü hükmün yanına koyardı.
sina("tanım cümlesi başlangıç şerhi TAŞIMIYOR (iki cümlelik risk kalktı)",
     "uzanmıyor" not in _tc_kirp and "ölçülmedi" not in _tc_kirp
     and ozet_uret.cumle_olcusu(_tc_kirp)[0] == 1, _tc_kirp[-300:])
# EN KOLAY KAZA BİÇİMİ: bir seriyi bir kümeden çıkarıp öbürüne düşmesini
# unutmak. Hükümsüz bacak da TAM SIFIR; "aynı kırılımın öteki bacakları
# hareket gösteriyor" kıyasında anılırsa cümle kendi ölçümüne aykırı olur.
_uyari_sifirla()
_Hy_iki_sifir = _sifir_blok(Hy_tam, "pe_tuzel_eur", len(Hy_tam), sag_uc=True)
_, r_hk = metrik.sifir_olc(
    _Hy_iki_sifir, veri.SIFIR_KAPSAMI, metrik.ESIK_SIFIR_BLOK,
    tuple(a for a in veri.BAS_OLCULEN if a != "pe_tuzel_eur"))
_topla(r_hk.get("dayanaksiz_cumle"), r_hk.get("hukumsuz_cumle"))
sina("hükümsüz bacak 'hareket gösteren öteki bacaklar' ölçüsüne GİRMİYOR",
     "pe_tuzel_eur" not in r_hk["dayanaksiz"]["kiyas_oteki_seri"]
     and r_hk["hukumsuz_seri"] == 1,
     str(r_hk["dayanaksiz"]["kiyas_oteki_seri"]))
# Kapının KAPSAMI da künyeden türer, elle tutulan bir listeden değil.
sina("ölçülmüş başlangıç kümesi KÜNYEDEN türetiliyor",
     set(veri.BAS_OLCULEN)
     == {a for a in veri.HAFTALIK if veri.bas_olculdu(a)}
     and set(veri.BAS_OLCULEN) < set(veri.HAFTALIK),
     f"{len(veri.BAS_OLCULEN)}/{len(veri.HAFTALIK)} seri")
# ÖLÇÜT BİR BAYRAK DEĞİL ARİTMETİK: bayrak elle konur, aritmetik konamaz.
# Kanıt alanına serinin KENDİ başlangıcını yazan bir sonraki oturum, tam bu
# hattın kusurunu (sorgunun alt sınırını ölçüm sanmak) yeniden üretirdi ve
# bayrakla sınayan bir kapı onu geçirirdi.
_kendi = veri.Seri("TP.SINAV.1", "2014-02-28", "mn USD", "sınav (TP.SINAV.1)",
                   bas_kanit="2014-02-28")
_gercek = veri.HAFTALIK["ar_toplam"]
veri.HAFTALIK["_sinav_kendi"] = _kendi
try:
    _kendi_olculdu = veri.bas_olculdu("_sinav_kendi")
finally:
    veri.HAFTALIK.pop("_sinav_kendi", None)
sina("kanıt alanı başlangıcın KENDİSİYSE ölçüm sayılmıyor",
     not _kendi_olculdu)
sina("kanıt alanı yoksa ölçüm sayılmıyor (varsayılan fail-closed)",
     not veri.bas_olculdu("pe_tuzel_usd")
     and veri.HAFTALIK["pe_tuzel_usd"].bas_kanit == "",
     veri.HAFTALIK["pe_tuzel_usd"].bas_kanit)
sina("keşifte sorulan seride kanıt alanı DURUYOR",
     veri.bas_olculdu("ar_toplam") and _gercek.bas_kanit == veri.KESIF_ALT_SINIR,
     _gercek.bas_kanit)

# KAPSAM: denetim, dolar bacaklarına HİÇ BAKMIYORDU. Elle tutulan listede
# yoklardı ve dördünden ikisi (dolar bacakları) yapısal sıfırdı — bakılmayan
# yer geçen sınavla aynı görünür. Kapsam artık kataloğun kendisi.
_bacaklar = {a for k in veri.KIRILIMLAR for a in k.parcalar}
sina("sıfır denetimi kırılımların HER bacağını görüyor (dolar dahil)",
     _bacaklar <= set(veri.SIFIR_KAPSAMI),
     str(sorted(_bacaklar - set(veri.SIFIR_KAPSAMI))))
sina("sıfır kapsamı KATALOGDAN türetiliyor, elle tutulan listeden değil",
     set(veri.SIFIR_KAPSAMI) == set(veri.HAFTALIK) - set(veri.DENETIM_DISI),
     f"{len(veri.SIFIR_KAPSAMI)} seri")
sina("tazelik ile sıfır denetimi AYNI istisnayı taşıyor (tek gerekçe)",
     set(veri.TAZELIK_SERI["haftalik"]) == set(veri.SIFIR_KAPSAMI))


# ===========================================================================
# 8. OKUR DİLİ VE BİÇİM — koşu kaydı da bir yayındır
# ===========================================================================
# Hatların koşu kaydı okura OLDUĞU GİBİ basılır: uyarı satırları ve özetin
# cümle olan her metin alanı. Bu depoda bir grup kodu, iki dosya adı ve bir
# komut satırı ("… ile doldurun") tam bu yoldan okura gitti ve dokuzuncu ölçüt
# yeşildi, çünkü kaynak MDX değil veri dosyasıydı. Tarama MUAFİYETSİZ koşar —
# backtick orada kod göstermez.
#
# Kapsam elle tutulan bir listeden değil, hattın GERÇEKTEN ÜRETTİĞİ metinden
# geliyor; ölçüt de sayfa sınavının kullandığı fonksiyonun ta kendisi. İki
# ayrı liste bir gün sessizce ayrışır.
print("\n▶ Okur dili ve biçim: koşu kaydının kendisi")

# MUAFİYET YOK — ve muafiyetin kaldırılması bir düzeltmedir. Burada bir
# "AA.YYYY yazımı biçim bulgusu sayılmaz" süzgeci vardı ve tam iki satırı
# gizliyordu: demet çekimi düşünce basılan uyarılar tarih penceresini
# `%m.%Y` ile yazıyordu. Hattın kendi kapısı "temiz" derken yayın kapısı aynı
# iki satır için altı uyarı üretiyordu; bir muafiyet, hat kapısı ile yayın
# kapısını ayrıştırdığı anda kendisi bir arızadır. Şablonlar artık tarihi
# ortak/bicim'den yazıyor (gün bilgisi de korunuyor), yani gizlenecek bulgu
# kalmadı ve süzgeç kaldırıldı. Bir gün ay yazımı gerçekten gerekirse
# istisna BURAYA değil ortak tanıma konur.
def _bulgular(metinler):
    return okur_dili.kosu_kaydi_tara(metinler)


# Elde ne birikti — vakumda geçen bir sınama, geçen bir sınamadan ayırt
# edilemez: taranan metin boşsa ölçüt hep yeşil verir.
_sayili = [m for m in OKUR_METIN if re.search(r"\d", m)]
sina("taranacak gerçek metin birikti (boş kümede sınama geçmez)",
     len(OKUR_METIN) >= 20 and len(_sayili) >= 12,
     f"{len(OKUR_METIN)} metin · {len(_sayili)} tanesi sayı taşıyor")

_bulgu = _bulgular(OKUR_METIN)
_engel = [x for x in _bulgu if x[1] in okur_dili.KOSU_KAYDI_ENGEL]
_uyari_ailesi = [x for x in _bulgu if x[1] in okur_dili.KOSU_KAYDI_UYARI]
sina("üretilen metinlerde KOD ve YAPIM dili yok", not _engel,
     "; ".join(f"{a}: {e}" for _i, a, e in _engel[:5]))
# Anahtar adı ve biçim ailesi yayın kapısında UYARI ağırlığında; hattın KENDİ
# şablonlarını tam denetimimizde tuttuğumuz için burada da sıfır olmalı.
# f"{x:+.2f}" kalıbı hem ondalık nokta hem ASCII tire taşır ve okur metnine
# girmez; sayı ortak/bicim'den yazılır.
sina("üretilen metinlerde anahtar adı ve biçim sızıntısı yok",
     not _uyari_ailesi,
     "; ".join(f"{a}: {e}" for _i, a, e in _uyari_ailesi[:5]))
sina("üretilen metinlerde ondalık VİRGÜL kullanılmış",
     any(re.search(r"\d,\d", m) for m in OKUR_METIN))

# Serinin OKUR ADI da yayındır: her uyarı satırı seriyi onunla anıyor. Sütun
# adı okura hiçbir şey söylemez; kaynağın BÜYÜK harfli kodu ise okurun
# arayabileceği bir künyedir ve muaftır.
_ad_bulgu = _bulgular([s.okur_adi for s in veri.HAFTALIK.values()])
sina("seri okur adlarında kod dili ve biçim sızıntısı yok", not _ad_bulgu,
     "; ".join(f"{a}: {e}" for _i, a, e in _ad_bulgu[:5]))

# Sayının TEK yazımı ortak/bicim'dedir ("başka yerde sayı biçimlenmez").
# İki katman ayrı bir biçimleyiciye bağlansaydı bir gün sessizce ayrışırdı.
sina("ölçüm ve veri katmanı AYNI biçimleyiciyi kullanıyor",
     metrik._bicim() is veri._bicim(),
     f"{metrik._bicim().__name__} · {veri._bicim().__name__}")
sina("biçim sözleşmesi: eksi U+2212, binlik nokta, ondalık virgül",
     b.sayi(-1234.5, 1) == "−1.234,5" and b.yuzde(-1.884, 2) == "−%1,88"
     and b.sayi(None) == "—",
     f"{b.sayi(-1234.5, 1)!r} · {b.yuzde(-1.884, 2)!r}")

# ŞABLONUN KENDİSİ de taranır: bugünkü sentetik koşu her uyarı yolunu
# tetiklemiyor olabilir ve tetiklenmemiş bir şablon, ilk kez GERÇEK koşuda
# okura çarpar. Sayı alanlarının yerine ortak/bicim yazımında bir sayı, tarih
# alanlarının yerine kendi biçimiyle bir tarih konur ki tarama metnin gerçek
# hâlini görsün.
_ORNEK_GUN = pd.Timestamp("2026-08-28")
_STRFTIME = re.compile(r"%[a-zA-Z]")


def _metin(dugum) -> str | None:
    if isinstance(dugum, ast.Constant) and isinstance(dugum.value, str):
        return dugum.value
    if isinstance(dugum, ast.JoinedStr):
        return "".join(_metin(d) or "" for d in dugum.values)
    if isinstance(dugum, ast.FormattedValue):
        spec = _metin(dugum.format_spec) if dugum.format_spec is not None else ""
        return (_ORNEK_GUN.strftime(spec) if spec and _STRFTIME.search(spec)
                else "1.234,5")
    if isinstance(dugum, ast.BinOp) and isinstance(dugum.op, ast.Add):
        sol, sag = _metin(dugum.left), _metin(dugum.right)
        return None if sol is None or sag is None else sol + sag
    return None


def _sayi_belirteci(dugum) -> list[str]:
    """Okur metninde KENDİ biçim belirtecini taşıyan SAYI alanları.

    `f"{x:+.2f}"` hem ondalık noktayı hem ASCII tireyi geri getirir ve okur
    metnine girmez; sayı ortak/bicim'den yazılır. Tarih belirteçleri (%m.%Y)
    muaf: onlar ay yazımını kuruyor ve kendi sözleşmeleri var.
    """
    out = []
    for d in ast.walk(dugum):
        if not (isinstance(d, ast.FormattedValue) and d.format_spec is not None):
            continue
        spec = _metin(d.format_spec) or ""
        if not _STRFTIME.search(spec):
            out.append(f"{ast.unparse(d.value)}:{spec}")
    return out


# Taranacak yüzey SÖZLEŞMEDEN türetilir: okura olduğu gibi basılan şey uyarı
# satırlarıdır ve özetin CÜMLE olan metin alanlarıdır. Cümlenin tanımı da
# bizim değil, yayın kapısının tanımı.
_sablon: list[str] = []
_belirtec: list[str] = []
_CUMLE_ANAHTAR = re.compile(r"(_cumlesi|_sozlugu|^cumle$|^hukum$|^gerekce$"
                            r"|^sebep$|^yontem$|^not$|^kimlik$)")
for _agac in (_veri_agac, _metrik_agac):
    for _d in ast.walk(_agac):
        if (isinstance(_d, ast.Call) and isinstance(_d.func, ast.Name)
                and _d.func.id == "uyar" and _d.args):
            _m = _metin(_d.args[0])
            if _m:
                _sablon.append(_m)
            _belirtec += _sayi_belirteci(_d.args[0])
        elif isinstance(_d, ast.Assign) and len(_d.targets) == 1 \
                and isinstance(_d.targets[0], ast.Subscript) \
                and isinstance(_d.targets[0].slice, ast.Constant) \
                and isinstance(_d.targets[0].slice.value, str) \
                and _CUMLE_ANAHTAR.search(_d.targets[0].slice.value):
            _m = _metin(_d.value)
            if _m:
                _sablon.append(_m)
                _belirtec += _sayi_belirteci(_d.value)
        elif isinstance(_d, ast.Dict):
            for _a, _v in zip(_d.keys, _d.values):
                if (isinstance(_a, ast.Constant) and isinstance(_a.value, str)
                        and _CUMLE_ANAHTAR.search(_a.value)):
                    _m = _metin(_v)
                    if _m and " " in _m and len(_m) >= okur_dili.CUMLE_ESIK:
                        _sablon.append(_m)
                        _belirtec += _sayi_belirteci(_v)

_sablon_bulgu = _bulgular(_sablon)
sina("uyarı ve cümle ŞABLONLARININ tamamı okur dili taramasından geçiyor",
     len(_sablon) >= 25 and not _sablon_bulgu,
     f"{len(_sablon)} şablon · "
     + "; ".join(f"{a}: {e}" for _i, a, e in _sablon_bulgu[:5]))
sina("okur metninde kendi biçim belirtecini taşıyan SAYI alanı yok",
     not _belirtec, "; ".join(_belirtec[:3]))


# ===========================================================================
# 9. YAPI — derlenmesi, içe aktarılması ve koşması ÜÇ AYRI SINAMADIR
# ===========================================================================
# `if __name__` kapısının ALTINA yazılan bir tanım py_compile'dan geçer, modül
# olarak içe aktarınca ÇALIŞIR ve yalnız betik olarak koşarken NameError verip
# hattın bütün adımlarını düşürür. `guncelle.py`nin ön denetimi bunu arıyor ama
# YALNIZ adım listesindeki betiklere bakıyor — bu dosya o listede değil, yani
# kendi kuralına karşı denetlenmiyor. Buradaki tarama klasörün TAMAMINI görür:
# bakılmayan yer, geçen sınavla aynı görünür.
print("\n▶ Yapı: kapıdan sonra tanım ve saat defterinin tüketicileri")

_kapi_kusuru: list[str] = []
_betikler = sorted(p for p in veri.PROJE.glob("*.py"))
for _p in _betikler:
    _agac = ast.parse(_p.read_text(encoding="utf-8"))
    _kapi = [i for i, d in enumerate(_agac.body)
             if isinstance(d, ast.If) and "__name__" in ast.dump(d.test)]
    if not _kapi:
        continue
    for _d in _agac.body[_kapi[0] + 1:]:
        if isinstance(_d, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            _kapi_kusuru.append(f"{_p.name}:{_d.name}")
sina("hiçbir hat betiğinde kapıdan SONRA üst düzey tanım yok",
     not _kapi_kusuru and len(_betikler) >= 3,
     f"{len(_betikler)} betik · {_kapi_kusuru}")

# İKİ TÜKETİCİ, TEK DEFTER: çizim katmanı figürün alt yazısı için, özet
# üreticisi sayfa damgası için AYNI fonksiyonu çağırmalı. Ayrı iki liste
# tutulsaydı biri güncellenir, öbürü kalırdı ve okur aynı figürün İÇİNDE ve
# ALTINDA iki farklı tarih görürdü. Henüz yazılmamış bir tüketicinin YOKLUĞUNU
# bu ölçüt yakalamaz — onu adım listesi yakalar, çünkü dosyası olmayan bir
# adım koşuyu düşürür; ama dosya YAZILDIĞI AN bu ölçüt onu bağlar.
_tuketici = [ad for ad in ("grafik.py", "ozet_uret.py")
             if (veri.PROJE / ad).exists()]
_ayrisan = [ad for ad in _tuketici
            if "sekil_saatleri" not in (veri.PROJE / ad).read_text(encoding="utf-8")]
sina("saat defterinin her tüketicisi saati AYNI fonksiyondan alıyor",
     not _ayrisan, f"kendi listesini tutan: {_ayrisan}")
print(f"    (bulunan tüketici: {', '.join(_tuketici) if _tuketici else 'yok'})")


# ===========================================================================
# 10. ÇİZİM VE ÖZET KATMANLARI — kapılar SINANMADAN kapı sayılmaz
# ===========================================================================
# Bu sınama uzun süre yalnız `import metrik, veri` yapıyordu; çizim ve özet
# katmanlarına tek teması kaynak METNİNDE bir dizge aramaktı. Yani hattın iki
# DURDURUCU kapısı (figürün çizdiği uç ile ilan edilen damganın kıyası, ve
# panel künyesi denetimi) sınamanın görüş alanı DIŞINDAYDI: ölçüldü — uç
# denetimi devre dışı bırakılıp panel künyesi bozulduğunda sınama yine
# "geçti" verdi. `guncelle.py` bu dosyayı hattın adımlarından ÖNCE koşturuyor,
# yani "ağa çıkmadan saniyeler içinde" korunduğu söylenen yüzey aslında
# ölçümün yarısını hiç görmüyordu. Geçmeyen bir sınama, geçen bir sınamadan
# ayırt edilemez.
#
# Buradaki senaryolar hattın GERÇEKTEN koştuğu yolu koşturur (ölçüm → çizim →
# özet), ama çıktıları GEÇİCİ bir dizine yazar: bir sınama çerçevesinin yayın
# çıktısıyla aynı dosyaya yazması, bu depoda ayrıca ölçülmüş bir kusur
# sınıfıdır (hattın çalışma ağacı bir kez sentetik sayılarla dolmuştu).
print("\n▶ Çizim ve özet: durdurucu kapılar ve saat sözleşmesi")

import grafik            # noqa: E402  (geçici dizin kurulmadan içe aktarılır)
# `ozet_uret` YUKARIDA içe aktarıldı: cümle sözleşmesinin ölçüsü
# (`cumle_olcusu`) sıfır sınıflarının sınamalarında da kullanılıyor ve o blok
# bu satırdan önce koşuyor. Modülün içe aktarılması yan etkisiz — özet sözlüğü
# boş kuruluyor, yazma yalnız `main()` içinde.

# FİGÜRÜN İÇİNDEKİ METİN DE OKURA GÖRÜNÜR — ve çıkarıcısı yayın kapısıyla AYNI
# olmalı. Gömülü Plotly HTML'inin başlık ve alt yazısı sayfada şeklin tam
# üstünde, okurun gözünün ilk gittiği yerde duruyor; bu depoda bir figürün alt
# yazısı okura kendi sürüm tarihçemizi anlatıyordu ve bütün yeşil koşulardan
# geçmişti. İki ayrı çıkarıcı yazsaydık biri bir alanı görür öteki görmezdi.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "site" / "tools"))
try:
    from sayfa_sinavi import sekil_metinleri as _sekil_metinleri
except ImportError:                                            # site yoksa
    _sekil_metinleri = None                                    # type: ignore


def _kutu(H: pd.DataFrame, sekil: bool = True, durum: dict | None = None) -> dict:
    """Ölçüm → çizim → özet zincirini GEÇİCİ dizinde uçtan uca koşturur.

    `durum` verilirse veri katmanının koşu kaydı ONUNLA kurulur: kaydın bayat
    ya da başka bir pencereye ait olduğu hâller ancak böyle sınanabilir.
    """
    kutu = Path(tempfile.mkdtemp(prefix="ypmevduat-duman-"))
    (kutu / "data").mkdir()
    (kutu / "cikti").mkdir()
    eski = (veri.PROJE, veri.VERI, metrik.PROJE, metrik.VERI,
            grafik.CIKTI, grafik.VERI, ozet_uret.PROJE, ozet_uret.VERI)
    try:
        veri.PROJE = metrik.PROJE = ozet_uret.PROJE = kutu
        veri.VERI = metrik.VERI = grafik.VERI = ozet_uret.VERI = kutu / "data"
        grafik.CIKTI = kutu / "cikti"
        veri._SON.pop("hafta", None)
        _uyari_sifirla()
        H.to_csv(kutu / "data" / "haftalik.csv")
        (kutu / "data" / "veri_durum.json").write_text(
            json.dumps(durum if durum is not None
                       else {"uyarilar": veri.uyarilar(),
                             "cerceve_imza": veri.cerceve_imza(H)},
                       ensure_ascii=False),
            encoding="utf-8")
        out: dict = {}
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            metrik.kos()
            out["m"] = json.loads(
                (kutu / "data" / "metrik_ozet.json").read_text(encoding="utf-8"))
            if sekil:
                try:
                    grafik.kos()
                    out["dur"] = None
                except SystemExit as ex:
                    out["dur"] = str(ex)
            ozet_uret.O.clear()
            ozet_uret._ATLANAN.clear()
            ozet_uret.main()
            out["o"] = json.loads((kutu / "ozet.json").read_text(encoding="utf-8"))
            out["saatsiz"] = ozet_uret._saatsiz_denetimi()
            out["atlanan"] = list(ozet_uret._ATLANAN)
        out["html"] = sorted(p_.name for p_ in (kutu / "cikti").glob("*.html"))
        # Çıkarıcı bulunamazsa (site ağacı yoksa) liste BOŞ kalır ve ölçüt
        # "boş kümede sınama geçmez" kuralıyla düşer: vakumda geçen bir sınama,
        # geçen bir sınamadan ayırt edilemez.
        out["sekil_metin"] = [] if _sekil_metinleri is None else [
            (p_.name, t) for p_ in sorted((kutu / "cikti").glob("*.html"))
            for t in _sekil_metinleri(p_.read_text(encoding="utf-8"))]
        out["uyari"] = _uyari_al()
        # KOŞU KAYDININ UYARI SATIRLARI — okura OLDUĞU GİBİ basılan metin.
        # Cümle sözleşmesi bu satırları da bağlıyor: `uyari_metni` onları yan
        # yana koyan bir BİRLEŞTİRMEDİR ve muaf, ama satırların kendisi
        # sayılmalı. Kayıt okunamazsa BOŞ liste değil, ölçütü düşürecek bir
        # eksiklik olarak görünsün diye anahtar hiç yazılmıyor.
        _kayit = kutu / "uyarilar.json"
        if _kayit.exists():
            out["kosu_uyarilari"] = [
                str(x) for x in (json.loads(_kayit.read_text(encoding="utf-8"))
                                 .get("uyarilar") or [])]
        return out
    finally:
        (veri.PROJE, veri.VERI, metrik.PROJE, metrik.VERI,
         grafik.CIKTI, grafik.VERI, ozet_uret.PROJE, ozet_uret.VERI) = eski
        veri._SON.pop("hafta", None)
        shutil.rmtree(kutu, ignore_errors=True)


_T = _kutu(H0)
# ÜRETİLEN ÖZETİN KENDİSİ DE TARANIR — ve kapsam bizim listemizden değil, YAYIN
# KAPISININ tanımından geliyor (`okur_dili.ozet_cumleleri`). Yukarıdaki okur
# dili bölümü yalnız uyarı satırlarını ve ŞABLONLARI görüyor; sayfaya asıl
# basılan şey ise özetin cümle alanlarıdır ve onlar ancak zincir uçtan uca
# koştuktan sonra var olur. İki ayrı liste tutulsaydı bir gün sessizce ayrışır
# ve hangisinin neyi gördüğü kimsenin aklında kalmazdı.
_oz_cumle = okur_dili.ozet_cumleleri(_T["o"])
_oz_bulgu = [(a_, aile, esl) for a_, metin in _oz_cumle
             for _i, aile, esl in _bulgular([metin])]
# Figürün BAŞLIĞI ve ALT YAZISI da okur metnidir ve yayın kapısı (sayfa
# sınavının on dokuzuncu ölçütü) onu tarıyor: yapım dili ENGEL, kod dili
# uyarı. Hattın kendi kapısı burada ikisini de sıfırda tutar — figür metnini
# tam denetimimizde yazıyoruz, taban sıfır olabilir.
_fig_bulgu = [(ad, aile, esl) for ad, metin in _T["sekil_metin"]
              for _i, aile, esl in _bulgular([metin])
              if aile in okur_dili.KOSU_KAYDI_ENGEL]
sina("figür başlık ve alt yazılarında KOD ve YAPIM dili yok",
     len(_T["sekil_metin"]) >= 40 and not _fig_bulgu,
     f"{len(_T['sekil_metin'])} metin · "
     + "; ".join(f"{ad}: {aile} {esl!r}" for ad, aile, esl in _fig_bulgu[:4]))
sina("üretilen özetin cümle alanlarında kod, yapım dili ve biçim sızıntısı yok",
     len(_oz_cumle) >= 6 and not _oz_bulgu,
     f"{len(_oz_cumle)} cümle · "
     + "; ".join(f"{a_}: {aile} {esl!r}" for a_, aile, esl in _oz_bulgu[:4]))
sina("temiz çerçevede zincirin tamamı koşuyor ve altı figür yazılıyor",
     _T["dur"] is None and _T["html"] == list(veri.SEKIL_DOSYALARI),
     f"{_T['dur']} · {_T['html']}")
# Bir sayı anahtarı blok kuralına takılmazsa saatsiz kalır ve sayfa onu hattın
# ANA saatiyle (blokların en yenisi) etiketler: bayat bir sayı taze damga alır.
sina("özetteki her sayı bir ölçüm bloğuna bağlı (saatsiz sayı yok)",
     not _T["saatsiz"], str(_T["saatsiz"]))
sina("temiz koşuda hiçbir ölçüm atlanmıyor ve bayat hükmü düşmüyor",
     not _T["atlanan"] and _T["o"]["bayat"] is False,
     f"atlanan {_T['atlanan']}")

# ===========================================================================
# CÜMLE SÖZLEŞMESİ — koşu kaydı MEKANİK, nüans SAYFAYA ait
# ===========================================================================
# NEDEN BİR SÖZLEŞME VAR. Bu hattın okur metinleri üç düzeltme turu boyunca
# kusur üretti ve kusurların ezici çoğunluğu tek bir yerdeydi: çok cümleli,
# çok kaynaklı metinler. Bir cümle altı ölçümü birleştirdiğinde altı bağımsız
# yanlışlaşma yolu açılıyor ve her tur birini kapatıp başkasını açıyordu —
# bir hata dizisi değil, bir TASARIM sorunu. Kural: bir koşu kaydı cümlesi EN
# ÇOK İKİ cümle ve TEK bir ölçümden beslenir; ikinci ölçüm AYRI bir anahtara
# yazılır ve sayfa ikisini yan yana koymayı seçer.
#
# ÖLÇÜT ÜRETİLEN ÖZETE KARŞI KOŞAR, ŞABLONA KARŞI DEĞİL: bir cümle şablonda
# tek, veriyle dolduğunda üç cümle olabilir (bir seri adının içinde nokta
# geçtiği gün). Kapsam yine sözleşmeden türüyor (`okur_dili.ozet_cumleleri`).
print("\n▶ Cümle sözleşmesi: en çok iki cümle, tek ölçüm")

_soz_asan = ozet_uret._cumle_olcusu_denetimi(_T["kosu_uyarilari"])
sina("üretilen özetin HER okur cümlesi sözleşmeye uyuyor",
     not _soz_asan and len(_oz_cumle) >= 8,
     f"{len(_oz_cumle)} cümle · " + "; ".join(_soz_asan[:4]))
# ÖLÇÜNÜN KENDİSİ DE SINANIR. Yayının önünde durmayan bir ölçüt bile yanlış
# alarm verirse kimse ona bakmaz; doğru saymadığı sürece de hiçbir şey
# korumaz. İki yönde birden sınanıyor.
_dort = ("Bir ölçüm 12,3 milyon dolar. İkinci ölçüm 4,5 puan. Üçüncüsü 6 "
         "hafta. Dördüncüsü yok.")
sina("ölçü çok cümleli çok ölçümlü bir metni YAKALIYOR",
     ozet_uret.cumle_olcusu(_dort) == (4, 3),
     str(ozet_uret.cumle_olcusu(_dort)))
# YANLIŞ ALARM YOK: seri künyesi (TP.HPBITABLO5.14) parantez içinde, ondalık
# virgül nokta taşımaz ve ad listesinin kırpılma işareti ("ve 3 seri daha")
# bir ölçüm değil, uzun listenin kapanışıdır — üçü de sayıma girmez.
_kunyeli = ("Parite etkisi, gerçek kişiler, dolar (TP.HPBITABLO5.14) ve 3 "
            "seri daha elimizdeki 653 haftanın tamamında tam sıfır.")
sina("künye, ondalık ve ad kırpması ölçüye YANLIŞ ALARM vermiyor",
     ozet_uret.cumle_olcusu(_kunyeli) == (1, 1),
     str(ozet_uret.cumle_olcusu(_kunyeli)))
# TARİH BİR ÖLÇÜMDÜR ve sayılır — bu bilinçli. "Kaynağın ilk gözlemi
# 28.02.2014" ölçülmüş bir gündür; sayılmasaydı bir cümle iki ölçümü tarih
# kılığında taşıyabilirdi. Cümlelerden çıkan tarihler kendi anahtarlarına
# gitti (`kapsam_akim_bas` · `kapsam_stok_bas` · `dol_cipa`).
sina("tarih de bir ÖLÇÜM sayılıyor (kılık değiştirmiş ikinci ölçüm yok)",
     ozet_uret.cumle_olcusu(
         "Tarihçe 28.02.2014 tarihinde başlıyor ve 653 hafta sürüyor.")
     == (1, 2),
     str(ozet_uret.cumle_olcusu(
         "Tarihçe 28.02.2014 tarihinde başlıyor ve 653 hafta sürüyor.")))
# UYARI SATIRLARI DA KOŞU KAYDIDIR ve aynı sözleşmeye tabidir. `uyari_metni`
# muaf, çünkü o bir CÜMLE değil BİRLEŞTİRMEDİR: bağımsız uyarı satırlarını
# yan yana koyar ve satırların kendisi ayrıca sayılıyor.
sina("koşu kaydı uyarı satırları da sözleşmeye uyuyor",
     not [x for x in _soz_asan if x.startswith("koşu kaydı")]
     and "uyari_metni" in ozet_uret.CUMLE_OLCUSU_MUAF,
     str(_T["kosu_uyarilari"])[:200])

# --- CÜMLEDEN ÇIKAN HER SAYI KENDİ ANAHTARINDA -----------------------------
# BU BİR SİLME DEĞİL. Ölçülen hiçbir şey kaybolmadı: cümlelerden çıkan sayılar
# özete kendi anahtarlarıyla girdi ve makine kaydı (doğrulama bloğu) olduğu
# gibi duruyor. Ölçüt bunu sayar — bir "kısaltma" turu, ölçümü sessizce
# düşürerek de geçebilirdi ve o, düzeltilen kusurdan kötü olurdu.
_tasinan = [
    # kimlik cümlesinden: pencere ve toleransın iki bacağı
    "kimlik_pencere_hafta", "kimlik_esik_mn", "kimlik_esik_pay",
    # dolarizasyon cümlesinden: çıpa, çıpadaki pay, iki pay
    "dol_cipa", "dol_pay_cipa", "dol_pay_ham", "dol_pay_ar",
    # ayrışma cümlesinden: hafta sayısı, iki yarı, korelasyon
    "ayrisma_n_hafta", "ayrisma_ters_pay_ilk_yari",
    "ayrisma_ters_pay_ikinci_yari", "ayrisma_korel",
    # kapsam cümlesinden: iki başlangıç, iki pencere, asimetri
    "kapsam_akim_bas", "kapsam_stok_bas", "kapsam_akim_hafta",
    "kapsam_ortak_hafta", "kapsam_asimetri_hafta",
    # kümüle cümlesinden: ay etiketi, iki hafta sayısı, yıl toplamı
    "kum_ay_etiket", "kum_ay_hafta", "kum_yil_hafta", "kum_yil_ar_toplam_mn",
    # geniş fark cümlesinden: iki toplam ve pay
    "genis_toplam_mia", "stok_toplam_mia", "genis_fark_pay",
    # bayatlık cümlesinden: gecikme, tolerans, sebep ve uyarı sayıları
    "veri_gecikme_gun", "bayat_tolerans_gun", "bayat_sebep_sayisi",
    "bayat_tazelik_uyarisi_sayisi", "atlanan_olcum_sayisi",
    # taban sözlüğünden: üç kalemin KATALOGDAN çözülmüş kodu
    "taban_manset_kod", "taban_genis_kod", "taban_lira_kod",
    # sıfır sınıflarından: sayımlar ve kapının iki yarısı
    "sifir_olculen_seri", "sifir_esik_hafta", "sifir_tam_sifir_seri",
    "sifir_tanim_seri", "sifir_dayanaksiz_seri", "sifir_hukumsuz_seri",
    "sifir_ayirt_edilemez_seri", "sifir_ayirt_edilemez_maks_hafta",
    "sifir_tanim_bas_kanitsiz_seri", "sifir_tanim_bas_kirpik_seri",
    "sifir_hukumsuz_bas_kanitsiz_seri", "sifir_hukumsuz_bas_kirpik_seri",
    # dayanaksız sıfırın manşete dokunan sonucundan: dilim ve kese ölçüleri
    "sifir_dayanaksiz_dilim_medyan_mn", "sifir_dayanaksiz_dilim_maks_mn",
    "sifir_dayanaksiz_manset_medyan_mn", "sifir_dayanaksiz_dilim_manset_pay",
    "sifir_dayanaksiz_kese_seri", "sifir_dayanaksiz_kese_hareketli_seri",
    "sifir_dayanaksiz_kese_durgun_seri", "sifir_dayanaksiz_kiyas_oteki_seri",
]
_eksik_tasinan = [a for a in _tasinan if a not in _T["o"]]
sina("cümleden çıkan her sayı özette KENDİ anahtarını buluyor",
     not _eksik_tasinan, str(_eksik_tasinan))
# TABAN KODLARI KATALOGDAN ÇÖZÜLÜYOR — sözlükte elle yazılıydı ve katalog
# değişse sessizce yalan söylerdi.
sina("üç tabanın kodu KATALOGDAN çözülüyor (elle yazılmıyor)",
     _T["o"]["taban_manset_kod"] == veri.HAFTALIK["stok_toplam"].kod
     and _T["o"]["taban_genis_kod"] == veri.HAFTALIK["genis_toplam"].kod
     and _T["o"]["taban_lira_kod"] == veri.HAFTALIK["mevduat_yp_tl"].kod,
     f"{_T['o'].get('taban_manset_kod')} · {_T['o'].get('taban_genis_kod')}")
# ÖLÇÜM TAŞIMAYAN YÖNTEM NESRİ KOŞU KAYDINDA DURMAZ: hiçbir koşuda
# değişmiyorsa bir koşunun kaydı olamaz, ve sayfada gözden geçirilmiş nesir
# olarak durması daha iyidir.
sina("ölçüm taşımayan yöntem nesri koşu kaydından çıktı",
     "kum_yontem_cumlesi" not in _T["o"] and "taban_sozlugu" not in _T["o"],
     str([a for a in ("kum_yontem_cumlesi", "taban_sozlugu") if a in _T["o"]]))

# --- SINIFI BOŞ OLAN ÖLÇÜM, ATLANAN ÖLÇÜM DEĞİLDİR -------------------------
# EN KOLAY KAZA BİÇİMİ: yeni anahtarları `koy()` ile yazmak. `koy()`
# ölçülemeyeni ATLANAN sayar ve atlanan ölçüm sayısı BAYATLIK HÜKMÜNE girer —
# dayanaksız sıfır sınıfının boş olduğu her koşuda (yani bugünkü koşuda)
# sayfa kendini bayat ilan ederdi. "Ölçemedik" ile "ölçülecek bir şey yoktu"
# aynı görünür ama aynı şey değildir; ayrımı `konusuz()` taşıyor.
sina("boş sınıfın ölçüsü null yazılıyor ama ATLANAN sayılmıyor",
     _T["o"]["sifir_dayanaksiz_seri"] == 0
     and "sifir_dayanaksiz_dilim_medyan_mn" in _T["o"]
     and _T["o"]["sifir_dayanaksiz_dilim_medyan_mn"] is None
     and not _T["atlanan"] and _T["o"]["bayat"] is False,
     f"atlanan {_T['atlanan']}")
# DOLU SINIFTA AYNI ANAHTAR SAYIYI TAŞIR: null'ın "ölçülmedi" demesi, ölçümün
# hiç yapılmadığı anlamına gelmemeli.
_TD = _kutu(_sifir_blok(H0, "pe_tuzel_diger", len(H0), sag_uc=True),
            sekil=False)
sina("sınıf dolunca aynı anahtarlar SAYIYLA doluyor",
     _TD["o"]["sifir_dayanaksiz_seri"] == 1
     and _TD["o"]["sifir_dayanaksiz_dilim_medyan_mn"] > 0
     and _TD["o"]["sifir_dayanaksiz_manset_medyan_mn"] > 0
     and _TD["o"]["sifir_dayanaksiz_kese_hareketli_seri"] == 1,
     f"dilim {_TD['o'].get('sifir_dayanaksiz_dilim_medyan_mn')}")
sina("sınıf dolduğunda da cümle sözleşmesi tutuyor",
     not ozet_uret._cumle_olcusu_denetimi(_TD["kosu_uyarilari"]),
     "; ".join(ozet_uret._cumle_olcusu_denetimi(_TD["kosu_uyarilari"])[:3]))

# --- CÜMLEDEN ÇIKAN NÜANS FİGÜRÜN ALT YAZISINDA GERÇEKTEN ÇÖZÜLÜYOR MU -----
# ÖLÇÜLDÜ VE KIRILDI: nüans figürün alt yazısına taşınırken oradaki anahtarlar
# ÖZET adlarıyla yazıldı — oysa çizim katmanı ÖLÇÜM katmanının dosyasını
# okuyor. Sonuç sessizdi: hüküm "Kimlik bu koşuda sınanamadı" yedeğine düştü,
# eşik "—" basıldı ve çıpanın günü okura ISO yazımla gitti. Hiçbir kapı
# düşmedi, çünkü metin GEÇERLİYDİ — yalnız yanlıştı. Bu yüzden ölçüt metnin
# varlığını değil ÇÖZÜLDÜĞÜNÜ sorar.
_alt = {ad: t for ad, t in _T["sekil_metin"] if len(t) > 200}
_a05 = next((t for ad, t in _alt.items() if ad.startswith("05")), "")
_a06 = next((t for ad, t in _alt.items() if ad.startswith("06")), "")
sina("kimlik figürünün alt yazısı hükmü ve eşiği ÇÖZÜYOR (yedeğe düşmüyor)",
     _T["m"]["kimlik_hukum"] in _a05
     and "sınanamadı" not in _a05
     and f"{b.sayi(_T['m']['kimlik_esik_mn'], 1)} milyon dolar" in _a05
     and f"{b.sayi(_T['m']['kimlik_pencere_hafta'], 0)} hafta" in _a05
     and "—" not in _a05.split("tolerans")[1][:60],
     _a05[:400])
sina("dolarizasyon figürü çıpanın gününü OKUR yazımıyla basıyor",
     _T["m"]["dol_cipa_etiket"] in _a06
     and _T["m"]["dol_cipa"] not in _a06,
     _a06[:400])
# HÜKÜM VE OKUR BİRİMLİ EŞİK ÖLÇÜM KATMANINDA TEK YERDE KURULUYOR: iki
# tüketici (özet üreticisi ve çizim katmanı) aynı dizgeyi okuyor. İki ayrı
# dönüşüm yazılsaydı okur aynı eşiği figürde ve sayfada iki türlü görürdü.
sina("hüküm ve okur birimli eşik TEK yerde (ölçüm katmanında) kuruluyor",
     _T["o"]["kimlik_hukum"] == _T["m"]["kimlik_hukum"]
     and _T["o"]["kimlik_esik_pay"] == _T["m"]["kimlik_esik_pay"]
     and _T["o"]["kimlik_esik_mn"] == _T["m"]["kimlik_esik_mn"],
     f"{_T['o'].get('kimlik_esik_pay')} · {_T['m'].get('kimlik_esik_pay')}")

# --- ÖLÇÜLEN PENCERE ZİNCİRİ UÇTAN UCA KOŞUYOR ----------------------------
# Yukarıdaki `_kutu(H0)` artık ÖLÇÜLEN pencerede koşuyor: değişim tablosu 653
# hafta, stok tabloları 114. Sınama uzun süre 139 haftalık bir çerçevede
# koştu ve o çerçevede "139'a göre yazılmış" bir varsayım hiçbir yerde
# patlamazdı — kısa pencerede geçen bir sınama, uzun pencerede geçen bir
# sınamadan ayırt edilemez. İddia açıkça yazılır ki çerçeve bir gün sessizce
# kısalırsa (birinin `_cerceve` varsayılanını değiştirmesi yeter) ölçüt düşsün.
sina("zincir ÖLÇÜLEN pencerede uçtan uca koşuyor (653 hafta akım · 114 stok)",
     len(H0) == AKIM_HAFTA
     and int(H0["stok_toplam"].notna().sum()) == STOK_HAFTA
     and _T["dur"] is None,
     f"çerçeve {len(H0)} hafta · stok "
     f"{int(H0['stok_toplam'].notna().sum())} · {_T['dur']}")
# TARİHÇE ASİMETRİSİ OKUR CÜMLESİNE DOĞRU GEÇİYOR MU. Cümle uzun süre TEK bir
# sayı yazıyordu ("ölçüm şu kadar haftayı kapsıyor") ve o sayı ORTAK
# pencereydi; asimetri 25 haftayken kusur küçüktü, 539 haftaya çıkınca cümle
# okura sayfanın yarısını olduğundan beş kat kısa gösterir hâle geldi.
# Kümüle akım figürleri on iki yılı çizerken metin "yüz on dört hafta" der.
_kap_c = _T["o"].get("kapsam_cumlesi") or ""
_pen = _T["m"]["dogrulama"]["pencere"]
# İKİ PENCERE ARTIK DÜZ ANAHTARLARDA. Cümle uzun süre TEK bir sayı yazıyordu
# ("ölçüm şu kadar haftayı kapsıyor") ve o sayı ORTAK pencereydi; asimetri 25
# haftayken kusur küçüktü, 539 haftaya çıkınca cümle okura sayfanın yarısını
# beş kat kısa gösterdi. İkinci sürüm ikisini de cümleye yazdı — dört cümle,
# beş ölçüm. Üçüncüsü sayıları anahtarlara verdi: sayfa hangi ölçümün hangi
# pencereden geldiğini kendi anlatır, cümle tek farkı bildirir.
sina("iki pencere de DÜZ anahtarlarda, sayfa <Deger> ile çağırabiliyor",
     _T["o"]["kapsam_akim_hafta"] == AKIM_HAFTA
     and _T["o"]["kapsam_ortak_hafta"] == STOK_HAFTA
     and _pen["akim_hafta"] == AKIM_HAFTA
     and _pen["ortak_hafta"] == STOK_HAFTA,
     f"{_pen} · {_kap_c[:120]}")
sina("asimetri ÖLÇÜLÜP yazılıyor, varsayılmıyor",
     _pen["asimetri_hafta"] == AKIM_HAFTA - STOK_HAFTA
     and _T["o"]["kapsam_asimetri_hafta"] == AKIM_HAFTA - STOK_HAFTA
     and f"{AKIM_HAFTA - STOK_HAFTA}" in _kap_c,
     f"{_pen['asimetri_hafta']} hafta")
# CÜMLE TEK ÖLÇÜM TAŞIR ve kaynak hakkında iddia kurmaz. "Tablo şu tarihte
# başlıyor" bir kaynak iddiasıdır ve çekim kırpıldığında yanlış olur —
# üstelik aynı kutudaki kapsam uyarısıyla çelişir.
sina("kapsam cümlesi tek ölçüm taşıyor ve kaynak hakkında konuşmuyor",
     ozet_uret.cumle_olcusu(_kap_c) == (1, 1)
     and "tablosu 2" not in _kap_c, _kap_c[:160])
# ŞEKİL SAATLERİ TARİHÇENİN BAŞINDAN ETKİLENMEZ — ve bu bir ölçümdür, umut
# değil. Damga blokların ORTAK SON haftasından geliyor; tarihçenin başını
# geriye çekmek son haftayı kımıldatamaz. Bir gün damga çerçevenin uzunluğuna
# bağlanırsa (ör. "ilk gözlemden bu yana" diye bir hesapla) figürler sessizce
# yanlış tarih basar ve hiçbir ölçüt düşmez.
# Kısa çerçeve, ölçülen pencerenin son iki yılı: aynı SON hafta, farklı BAŞ.
# Sabit bir tarih yazmak, ölçülen pencere bir gün yeniden ölçüldüğünde
# ikisinin sessizce üst üste binmesine yol açardı.
_kisa = _cerceve(bas=(pd.Timestamp(SON_HAFTA)
                      - pd.Timedelta(weeks=104)).strftime("%Y-%m-%d"))
_TK = _kutu(_kisa, sekil=False)
sina("figür damgaları tarihçenin BAŞINDAN etkilenmiyor (son hafta aynı)",
     veri.sekil_saatleri(_T["m"]) == veri.sekil_saatleri(_TK["m"]),
     f"uzun {veri.sekil_saatleri(_T['m'])} · kısa {veri.sekil_saatleri(_TK['m'])}")
sina("uzun tarihçe akım bloğunun saatini kaydırmıyor",
     _T["m"]["akim_tarih"] == _TK["m"]["akim_tarih"] == SON_HAFTA,
     f"{_T['m']['akim_tarih']} · {_TK['m']['akim_tarih']}")
# KÜMÜLE AKIM ON İKİ YILA GİDER, KİMLİK GİTMEZ: ikisi ayrı pencerelerden ve
# ayrım koda geçmeli, yalnız cümleye değil. Kimlik artığı stok bacağını
# istediği için ortak pencerede kalır; kümüle akım stok tablosunun ucuna hiç
# bakmaz. Ölçüt ikisinin GERÇEKTEN ayrıştığını sorar.
_A0_uzun = _T["m"]["ayristirma"]
sina("kimlik ortak pencerede, kümüle akım kendi penceresinde ölçülüyor",
     _A0_uzun["bacak"]["toplam"]["n_hafta"] <= STOK_HAFTA
     and _T["m"]["ayrisma_n_hafta"] > STOK_HAFTA,
     f"kimlik {_A0_uzun['bacak']['toplam']['n_hafta']} hafta · "
     f"ayrışma {_T['m']['ayrisma_n_hafta']} hafta")
# ASİMETRİ SIFIRSA OLMAYAN BİR BOŞLUK ANLATILMAZ. Kaynak stok tarihçesini
# geriye doldurursa iki pencere çakışır; sabit metin o hâlde "aradaki sıfır
# hafta için stok gözlemi yok" der. Ölçüldü — cümle tam bunu yazıyordu ve
# hiçbir ölçüt düşmüyordu, çünkü bugünkü veride asimetri sıfır değil.
# Bugün gerçekleşmeyen bir hâl, sınanmadığı sürece yarın sessizce yayımlanır.
_TS = _kutu(_cerceve(stok_bas=None), sekil=False)
_kap_s = _TS["o"].get("kapsam_cumlesi") or ""
sina("iki pencere çakışınca olmayan boşluk ANLATILMIYOR",
     "aynı haftada başlıyor" in _kap_s
     and ozet_uret.cumle_olcusu(_kap_s) == (1, 0)
     and _TS["m"]["dogrulama"]["pencere"]["asimetri_hafta"] == 0,
     _kap_s[:180])

# --- KAYNAK BİR HAFTAYI ATLARSA hat DURMAMALI -----------------------------
# Ölçüldü: kimlik bloğunun saati bir hafta geriye düşüyor, defter ise SON
# cumayı ilan ediyordu ve `_uc_denetimi` doğru davranıp hattı durduruyordu.
# Sonuç: 01–04 yazılmış, 05–06 hiç yazılmamış, yükseklik künyesi hiç
# üretilmemiş, siteye kopyalama yok — çalışan beş figür de gitmiyor. Kaynağın
# bir haftayı atlaması hattın tasarımında AÇIKÇA hayatta kalınabilir sayılan
# bir olay; bütün panoyu durdurması yanlış alarmın kendisidir.
_A = _kutu(_hafta_atla(H0, konum=-2))
sina("kaynak bir haftayı atlayınca hat DURMUYOR, altı figür de yazılıyor",
     _A["dur"] is None and _A["html"] == list(veri.SEKIL_DOSYALARI),
     f"{_A['dur']}")
# "Dört haftalık" etiketli bir toplam yirmi sekiz günü kapsıyorsa okur onu
# dört haftalık bir pencerenin sonucu sanar; ölçü doğru, ETİKET yanlış. Kapsam
# ölçülür ve sapması okura yazılır (boşaltmak, sağ uçtaki on iki gözlemi silip
# figürü üç ay geriye düşürür ve yayını durdururdu).
sina("atlanan haftada pencere kapsamı ÖLÇÜLÜP okura yazılıyor",
     _A["o"].get(f"kum_{metrik.PENCERE_KISA}h_kapsam_gun") == 28
     and any(x.startswith("PENCERE KAPSAMI") for x in _A["uyari"]),
     f"kapsam {_A['o'].get(f'kum_{metrik.PENCERE_KISA}h_kapsam_gun')} · "
     f"uyarı {[x[:20] for x in _A['uyari']]}")
sina("kapsam sapmıyorken PENCERE KAPSAMI uyarısı DÜŞMÜYOR",
     _T["o"].get(f"kum_{metrik.PENCERE_KISA}h_kapsam_gun") == 21
     and not any(x.startswith("PENCERE KAPSAMI") for x in _T["uyari"]))
sina("atlanan haftada kimlik figürünün damgası ÖLÇÜLEN kimlik haftası",
     veri.sekil_saatleri(_A["m"])["05_kimlik.html"]
     == pd.Timestamp(_A["m"]["kimlik_tarih"]).strftime("%d.%m.%Y")
     and _A["m"]["kimlik_tarih"] != _A["m"]["akim_tarih"],
     f"defter {veri.sekil_saatleri(_A['m'])['05_kimlik.html']} · "
     f"kimlik {_A['m']['kimlik_tarih']}")

# --- SON GÖZLEM ALTI GÜN ARAYLA (tatil kayması) ---------------------------
# İkinci tetikleyici ve daha sinsisi: veri katmanı tek bir uyarı bile
# basmıyordu, çünkü boşluk ölçütü yalnız "yedi günden uzun" diye soruyordu.
_H6 = H0.copy()
_ix6 = list(_H6.index)
_ix6[-1] = _ix6[-1] - pd.Timedelta(days=1)
_H6.index = pd.DatetimeIndex(_ix6, name="tarih")
_B = _kutu(_H6)
sina("altı günlük aralıkta hat DURMUYOR",
     _B["dur"] is None and _B["html"] == list(veri.SEKIL_DOSYALARI),
     f"{_B['dur']}")

# --- KAPILAR GERÇEKTEN KAPI MI --------------------------------------------
# Yukarıdaki iki senaryo kapının YANLIŞ ALARM vermediğini gösteriyor; bu ikisi
# kapının hâlâ ÇALIŞTIĞINI. İkisi birden sorulmazsa "düzeltme" sessizce
# denetimi kaldırmak olabilirdi.
def _iz(uc: str):
    f = go.Figure()
    f.add_trace(go.Scatter(x=pd.date_range("2026-01-02", uc, freq="W-FRI"),
                           y=[1.0] * len(pd.date_range("2026-01-02", uc,
                                                       freq="W-FRI"))))
    return f


_f_eski = _iz("2026-08-14")
try:
    grafik._uc_denetimi("sinav.html", "28.08.2026", _f_eski)
    _uc_kapisi = False
except SystemExit:
    _uc_kapisi = True
sina("ilan edilen uç figürün çizdiğinden YENİYSE çizim katmanı DURUYOR",
     _uc_kapisi)
try:
    with contextlib.redirect_stdout(io.StringIO()):
        grafik._uc_denetimi("sinav.html", "07.08.2026", _f_eski)
    _uc_tutucu = True
except SystemExit:
    _uc_tutucu = False
sina("ilan edilen uç ESKİYSE durmuyor (tutucu damga yanlış alarm değil)",
     _uc_tutucu)
sina("figürün çizdiği uç izlerin EN ESKİSİNDEN ölçülüyor",
     grafik._cizili_uc(_f_eski) == pd.Timestamp("2026-08-14"),
     str(grafik._cizili_uc(_f_eski)))

_f_panel = make_subplots(rows=3, cols=1)
try:
    grafik._panel_denetimi("02_kumule_akim.html", _f_panel)
    _panel_kapisi = "geçti"
except SystemExit as ex:
    _panel_kapisi = str(ex)
_f_panel2 = make_subplots(rows=2, cols=1)
try:
    grafik._panel_denetimi("02_kumule_akim.html", _f_panel2)
    _panel_bozuk = False
except SystemExit:
    _panel_bozuk = True
sina("panel künyesi figürle örtüşünce geçiyor, ayrışınca DURUYOR",
     _panel_kapisi == "geçti" and _panel_bozuk, str(_panel_kapisi)[:80])

# DÖRT LİSTE, TEK KAYNAK. Figür adı bu hatta dört yerde geçiyor (veri
# katmanının künyesi, panel künyesi, zorunlu liste ve koşu sırası) ve çizim
# katmanı "kendi listesini tutmaz" diye YAZILIYDI — yazılmış olması onu doğru
# yapmıyordu. Yedinci bir figür eklendiğinde dördü sessizce ayrışabilirdi.
sina("panel künyesi kaynak figür listesiyle birebir örtüşüyor",
     set(grafik.PANEL_SAYISI) == set(veri.SEKIL_DOSYALARI),
     f"fark {set(grafik.PANEL_SAYISI) ^ set(veri.SEKIL_DOSYALARI)}")
sina("zorunlu figürlerin hepsi kaynak listede",
     set(grafik.ZORUNLU) <= set(veri.SEKIL_DOSYALARI),
     f"listede olmayan {set(grafik.ZORUNLU) - set(veri.SEKIL_DOSYALARI)}")

# --- BİR FİGÜR, ÖLÇÜLEMEYEN BİR DÖNEMİ ÇİZMEZ ------------------------------
# ARIZANIN KENDİSİ: kimlik figürü İKİ tablodan besleniyor (değişim tablosu
# 2014'te, stok tabloları 2024'te başlıyor) ve artık ancak ortak haftada
# ölçülebiliyor. Tolerans bandı ise yalnız arındırılmış değişim ile parite
# etkisinin brüt hareketinden türediği için ÖLÇÜLEMEYEN dönemde de
# hesaplanabiliyordu: alt panelin ekseni 2014'e açılıyor, artık izleri sağ
# dilime sıkışıyor ve panelin geri kalanını tek başına tolerans bandı
# dolduruyordu. Okur, kimliğin on iki yıl boyunca sınandığını ve hep
# tuttuğunu görüyordu — oysa o dönemde kimlik HİÇ sınanmadı.
_A5, _ = metrik.ayristir(H0, 0)
_damga5 = b.tarih_kisa(SON_HAFTA)
_f5 = grafik.sekil_05(_A5, {"kimlik_tarih": _damga5, "kimlik_kaydirma": 0},
                      _damga5)
_x5 = [pd.Timestamp(min(_tr.x)) for _tr in _f5.data
       if getattr(_tr, "x", None) is not None and len(_tr.x)]
_artik_bas = _A5["artik_toplam"].dropna().index[0]
_esik_bas = _A5["esik_toplam"].dropna().index[0]
# TUZAK GERÇEKTEN VAR MI: eşik artıktan önce başlamıyorsa bu ölçüt vakumda
# geçer ve kapattığı kusuru hiç göremez.
_pay5 = len(_A5["artik_toplam"].dropna()) / len(_A5["esik_toplam"].dropna())
sina("tolerans bandı artıktan ÖNCE de hesaplanabiliyor (tuzak gerçek)",
     _esik_bas < _artik_bas and _pay5 < 0.25,
     f"eşik {_esik_bas.date()} · artık {_artik_bas.date()} · "
     f"artığın payı {_pay5:.2f}")
sina("kimlik figürü ÖLÇÜLEMEYEN dönemi ÇİZMİYOR",
     bool(_x5) and min(_x5) >= _artik_bas,
     f"figürün başı {min(_x5).date() if _x5 else '—'} · "
     f"artık {_artik_bas.date()}")
# Kırpma yalnız SOLDAN: sağ uç figürün ilan ettiği damgayı belirliyor ve
# oradan bir hafta kısalmak, çizim katmanının uç denetimini yanlış tarafa
# çevirirdi.
sina("kırpma figürün SAĞ ucuna dokunmuyor (damga korunuyor)",
     max(pd.Timestamp(max(_tr.x)) for _tr in _f5.data
         if getattr(_tr, "x", None) is not None and len(_tr.x))
     == _A5["artik_toplam"].dropna().index[-1],
     str(_A5["artik_toplam"].dropna().index[-1].date()))

# --- ÇERÇEVEDEN TÜRETİLEN UYARI DEVRALINMAZ, YENİDEN ÖLÇÜLÜR ---------------
# ARIZANIN KENDİSİ: ölçüm katmanı kapsam, boşluk, tazelik ve kaynak kimliği
# uyarılarını veri katmanının bıraktığı koşu kaydından DEVRALIYORDU ve
# kendisi hiç ölçmüyordu. Kayıt bir önceki koşudan kalmış, başka bir
# pencereyle yazılmış ya da veri katmanı hiç koşmamış olabilir — dosya
# yerinde durur, okunur, hata vermez, yalnızca BAŞKA bir çerçeveyi anlatır.
# Ölçüldü: kayıttaki uyarı listesi BOŞ dururken ölçülen çerçeve kapsam
# uyarısı gerektiriyordu ve sayfa "bu koşuda uyarı yok" diyordu.
sina("çerçeveden türeyen uyarı ÇERÇEVEDEN ölçülüyor, temizde susuyor",
     any(u.startswith("KAPSAM") for u in veri.cerceve_uyarilari(_kirpik_c))
     and not veri.cerceve_uyarilari(H0),
     "; ".join(veri.cerceve_uyarilari(_kirpik_c))[:160])
sina("iki katman AYNI fonksiyonu çağırıyor (iki uyarı listesi yok)",
     "veri.cerceve_uyarilari(H)" in _kos_kod
     and "cerceve_uyarilari(H)" in _iz_kaynak("kos"),
     "katmanlardan biri kendi listesini kuruyor")
# KAYIT ANLATTIĞI ÇERÇEVEYİ ADIYLA TAŞIR — `_cache_yolu` ile aynı sınıf kural.
sina("çerçeve künyesi pencereyi ayırt ediyor (kırpma · uzunluk · uç)",
     veri.cerceve_imza(H0) != veri.cerceve_imza(_kirpik_c)
     and veri.cerceve_imza(H0) != veri.cerceve_imza(H0.iloc[:-1])
     and veri.cerceve_imza(H0) == veri.cerceve_imza(H0.copy()),
     str(veri.cerceve_imza(_kirpik_c)))
# KATMANLAR ARASI HER KAYIT KÜNYESİNİ TAŞIR — sınıf kuralının KAPSAMI.
# Bu hatta katmandan katmana taşınan üç türetilmiş çıktı var: EVDS önbelleği
# (adında sorgu penceresini taşır), veri katmanının koşu kaydı ve ölçüm
# katmanının özeti. Üçünden biri künyesiz kalırsa onu okuyan katman yanlış
# olduğunu ÖLÇEMEZ; çizim katmanının eşdeğer kapısı ise damga denetimidir
# (ilan edilen uç ile figürün çizdiği uç kıyaslanır ve ayrışırsa hat DURUR).
sina("katmanlar arası koşu kayıtlarının hepsi künyesini taşıyor",
     "cerceve_imza" in _T["m"]
     and "cerceve_imza" in inspect.getsource(veri.kos)
     and "cerceve_imza" in (veri.PROJE / "ozet_uret.py").read_text(
         encoding="utf-8"),
     f"özette {'var' if 'cerceve_imza' in _T['m'] else 'YOK'}")

_YOK = ("SERİ YOK: Gerçek kişilerin YP mevduatı (TP.HPBITABLO2.11) ne "
        "kaynaktan geldi ne de önbellekte var; bu seriye dayanan ölçüm bu "
        "koşuda yapılamıyor.")
_S = _kutu(H0, sekil=False,
           durum={"uyarilar": [_YOK],
                  "cerceve_imza": {"satir": 1, "sutun": 1,
                                   "ilk": "2020-01-03", "son": "2020-01-03"}})
sina("başka pencereyi anlatan kayıttan olay satırı DEVRALINMIYOR",
     _YOK not in _S["o"]["uyari_metni"], _S["o"]["uyari_metni"][:200])
sina("devralınamayan kayıt SESSİZ geçmiyor, eksik ADIYLA yazılıyor",
     "ÖLÇÜM EKSİK" in _S["o"]["uyari_metni"]
     and "başka bir gözlem penceresi" in _S["o"]["uyari_metni"],
     _S["o"]["uyari_metni"][:240])
_topla(_S["o"]["uyari_metni"])
# KÜNYE UYUŞUYORSA DEVİR SÜRÜYOR: yanlış alarm üreten bir kapı, kapattığı
# kusurdan pahalıya mal olur — gerçek bir "seri yüklenemedi" satırı bu
# yüzden sayfaya ulaşmaya devam etmeli.
_S2 = _kutu(H0, sekil=False,
            durum={"uyarilar": [_YOK], "cerceve_imza": veri.cerceve_imza(H0)})
sina("künye uyuşurken olay satırı sayfaya ULAŞIYOR (yanlış alarm yok)",
     _YOK in _S2["o"]["uyari_metni"]
     and "ÖLÇÜM EKSİK: veri katmanının" not in _S2["o"]["uyari_metni"],
     _S2["o"]["uyari_metni"][:200])

# --- İSTEĞE BAĞLI FİGÜRÜN ESKİ DOSYASI SİTEYE GİTMEZ ----------------------
# Kopya sözleşmesi diskteki her HTML'i joker ile alıyor: üretilmeyen figürün
# önceki koşudan kalan dosyası siteye gidiyordu ve ölçüm katmanı o bloğa saat
# yazmadığı için ALTINA TARİH HİÇ BASILMIYORDU — bayat figür, bayatlığını
# gösteren tek işaretten de yoksun.
_L = _kutu(H0.drop(columns=["mevduat_tl", "mevduat_yp_tl"]))
sina("lira bacakları yokken beş figür yazılıyor, hat DURMUYOR",
     _L["dur"] is None and "06_dolarizasyon.html" not in _L["html"]
     and len(_L["html"]) == 5, f"{_L['dur']} · {_L['html']}")
sina("üretilemeyen figürün damgası YOK (yanlış tarih basılmıyor)",
     veri.sekil_saatleri(_L["m"])["06_dolarizasyon.html"] is None)
# DÜŞEN HER ANAHTAR SAYFADA BİR STATİK YEDEK DEMEKTİR: sayfa "veri taze" derken
# yirmi anahtarın yerinde donmuş sayılar görünüyordu ve hüküm bunu görmüyordu.
# ÖLÇÜT "Veri taze" HÜKMÜNÜ arar, "taze" HECESİNİ değil: bayatlık gerekçesi
# "tazelik uyarısı düştü" diyebilir ve o cümle hükmün TERSİDİR. Gevşek bir
# dize araması burada yanlış alarm üretti; bir ölçütün neye baktığı, ne kadar
# baktığı kadar önemli.
sina("ölçüm atlanınca sayfa kendini TAZE ilan etmiyor",
     bool(_L["atlanan"]) and _L["o"]["bayat"] is True
     and "Veri taze" not in _L["o"]["bayat_cumlesi"],
     f"atlanan {len(_L['atlanan'])} · bayat {_L['o']['bayat']} · "
     + _L["o"]["bayat_cumlesi"][:120])
# Sözleşme özete YAZILI olarak gider: sayfa sınavının birinci ölçütünde
# "isteğe bağlı anahtar" kavramı yok, yani bu anahtarlardan biri <Deger> ile
# çağrılırsa kaynağın o bacağı yayımlamadığı koşuda SİTENİN TAMAMI durur.
sina("yapısal olarak eksik kalabilen anahtarlar özette adıyla ilan ediliyor",
     set(_L["atlanan"]) <= set(_T["o"]["_istege_bagli"])
     and all(ozet_uret.istege_bagli(a) for a in _T["o"]["_istege_bagli"]),
     f"ilansız {sorted(set(_L['atlanan']) - set(_T['o']['_istege_bagli']))}")
# Bütün dolarizasyon ailesi ölçülemediğinde bile anahtarları özette DURUYOR:
# yoksa o koşuda sayfa sınavının birinci ölçütü ENGEL üretir ve yayın durur.
sina("ölçülemeyen dolarizasyon anahtarları özette BOŞ olarak duruyor",
     all(a in _L["o"] and _L["o"][a] is None for a in _L["atlanan"]),
     f"silinen {[a for a in _L['atlanan'] if a not in _L['o']]}")

# --- HİÇ YÜKLENEMEYEN SERİ DE BAYATLIK İZİDİR ------------------------------
# "SERİ YOK" öneki bayat hükmünün baktığı listede yoktu: dört ölçüm anahtarı
# düşerken sayfa "Veri taze: bütün bacaklar tolerans içinde" diyordu, üstelik
# aynı kutuda "SERİ YOK: …" cümlesi dururken. Sayfa kendisiyle çelişiyordu.
sina("bayatlık izi ailesi TEK yerde tanımlı ve SERİ YOK da ailede",
     "SERİ YOK" in veri.TAZELIK_IZI and "HAFTA ATLANDI" in veri.TAZELIK_IZI)
_S = _kutu(H0.drop(columns=["maden_tuzel"]), sekil=False)
sina("hiç yüklenemeyen seri bayat hükmünü TETİKLİYOR",
     _S["o"]["bayat"] is True and bool(_S["atlanan"]),
     f"bayat {_S['o']['bayat']} · atlanan {_S['atlanan']}")

# --- KİMLİK ARTIĞININ İKİ ÖLÇÜSÜ AYNI PENCEREDEN --------------------------
# Mutlak ölçü son elli iki haftadan, bağıl ölçü TAM TARİHÇEDEN geliyordu ve
# ikisi sayfada yan yana yayımlanıyordu: iki yıl önceki tek haftalık bir
# revizyon "artık %455,3" diye, bu haftanın tarihiyle damgalanmış olarak
# görünürken hemen yanında "kimlik tutuyor, en büyük fark 0,0" yazıyordu.
_Hr = H0.copy()
_Hr.loc[pd.Timestamp("2025-02-21"):, "stok_gercek"] += 3_000.0
_Hr["stok_toplam"] = _Hr["stok_gercek"] + _Hr["stok_tuzel"]
_Hr["k_gercek"] = _Hr["stok_gercek"]
_R = _kutu(_Hr, sekil=False)
sina("pencere dışındaki bir revizyon bağıl artığı ŞİŞİRMİYOR",
     _R["o"]["kimlik_tutuyor"] is True
     and _R["o"]["kimlik_artik_pay"] <= _R["o"]["kimlik_esik_pay"],
     f"artık payı {_R['o'].get('kimlik_artik_pay')} · "
     f"eşik {_R['o'].get('kimlik_esik_pay')}")
sina("tam tarihçenin maksimumu TANIDA duruyor ve kendi tarihini taşıyor",
     _R["m"]["ayristirma"]["bacak"]["gercek"]["artik_bagil_maks"] > 1.0
     and _R["m"]["ayristirma"]["bacak"]["gercek"]["artik_bagil_maks_tarih"]
     == "2025-02-21")

# --- YAYIM GÜNÜ ÖLÇÜLMÜŞ DEĞİL, BEKLENEN ----------------------------------
# Hesap yalnız takvim aritmetiğidir (cuma artı altı gün, hafta sonunda kayar)
# ve resmî tatili GÖRMEZ; adı "yayim_tarihi" olsaydı okur onu ölçülmüş bir gün
# sanardı ve hiçbir denetim bunu yakalayamazdı — ölçülen değil ilan edilen bir
# şeydir.
sina("beklenen yayım günü adında BEKLENEN taşıyor, ölçülmüş gibi durmuyor",
     "beklenen_yayim_tarihi" in _T["o"] and "yayim_tarihi" not in _T["o"]
     and "beklenen_yayim_gecikme_gun" in _T["o"],
     str([a for a in _T["o"] if "yayim" in a]))
# EŞİĞİN BÜYÜKLÜK KIYASI KOŞUDA TÜRETİLİR. Yorumda elle yazılmış kıyas ON KAT
# yanlıştı ("231 milyar dolarlık stokun on binde 0,1'i"; doğrusu on binde 1,1)
# ve eşiği gözden geçiren bir sonraki oturumu on kat büyütmeye ikna edebilirdi.
# Türetilen kıyas yaşlanmaz ve yanlış yazılamaz.
_kiyas = _T["m"]["esik"]["kimlik_son_stok_payi"]
sina("kimlik eşiğinin stoka oranı ölçümden türetiliyor (yorumda donmuyor)",
     _kiyas is not None
     and np.isclose(_kiyas, metrik.ESIK_KIMLIK_MN
                    / (_T["o"]["stok_toplam_mia"] * 1e3), rtol=1e-3)
     and 5e-5 < _kiyas < 5e-4,
     f"oran {_kiyas}")
sina("bayatlık hükmü ÖLÇÜLEN gecikmeden kuruluyor",
     _T["o"]["veri_gecikme_gun"] is not None
     and _T["o"]["bayat_tolerans_gun"] == veri.tazelik_tolerans("haftalik"))

# --- KÜMÜLENİN ETİKETİ İLE SAYISI AYNI HAFTADAN ---------------------------
# Ölçüldü: on üç haftalık pencere sütunundaki tek bir boşluk akım bloğunu
# 28.08'den 29.05'e çekiyor, sayfa ise "Ağustos 2026 içinde … 302,8 milyon
# dolar" yazıyordu — 302,8 Mayıs'ın kümülesiydi ve Ağustos'un gerçek toplamı
# 1.196,0. Sayı ile etiket ayrı yerlerden gelirse ikisi de doğru görünür.
_Hg = H0.copy()
_Hg.loc[pd.Timestamp("2026-06-05"), "ar_toplam"] = np.nan
_G = _kutu(_Hg, sekil=False)
_g_ay = pd.Timestamp(_G["o"]["kum_ay_bas"].split(".")[::-1][0]
                     + "-" + _G["o"]["kum_ay_bas"].split(".")[1]
                     + "-" + _G["o"]["kum_ay_bas"].split(".")[0])
sina("kümülenin ay etiketi ile sayısının haftası AYNI aya düşüyor",
     veri.ad_uzun(pd.Timestamp(_G["m"]["akim_tarih"])) == _G["o"]["kum_ay_etiket"]
     and _g_ay.month == pd.Timestamp(_G["m"]["akim_tarih"]).month,
     f"etiket {_G['o'].get('kum_ay_etiket')} · "
     f"akım saati {_G['m'].get('akim_tarih')}")
# Pencere sütunları bloğun saatini çekmemeli: bir haftalık boşluk yüzünden
# bütün akım panelinin bir çeyrek geriye düşmesi bu ayrışmayı tetikleyen şeydi.
# Kümüle sütunları haftalık akımın TÜREVİDİR ve uçları tanım gereği geride
# olabilir; türev bir sütun türediği sütunun saatini kaydırmamalı. Ölçüldü:
# tek bir haftalık boşluk akım bloğunun tamamını 28.08'den 29.05'e çekiyor ve
# o hafta gerçekten ölçülmüş haftalık akımlar da üç ay geride yayımlanıyordu.
sina("kümüle sütunundaki boşluk akım bloğunu geriye ÇEKMİYOR",
     _G["m"]["akim_tarih"] == _T["m"]["akim_tarih"],
     f"{_G['m']['akim_tarih']} · temiz {_T['m']['akim_tarih']}")
# Ama ölçülemeyen kümüle DE YAYIMLANMAZ: bir boşluktan sonra "yıl başından bu
# yana" toplanamaz ve o anahtar özete hiç girmez, koşu kaydında adıyla görünür.
# Değer YAZILMAZ ama ANAHTAR KALIR (boş olarak): sayfa bileşeni `null`ı
# "ölçülmedi" diye okuyup statik yedeği yerinde bırakıyor, sayfa sınavının
# birinci ölçütü ise anahtarı BULUYOR. Anahtarı büsbütün silmek, kaynağın bir
# haftayı eksik yayımladığı bir koşuda SİTENİN TAMAMININ yayınını durdururdu.
sina("boşluktan sonra yıl içi kümülenin DEĞERİ yazılmıyor",
     _G["o"]["kum_yil_ar_toplam_mn"] is None
     and isinstance(_T["o"]["kum_yil_ar_toplam_mn"], float)
     and any(x.startswith("ÖLÇÜM EKSİK") for x in _G["uyari"]),
     f"değer {_G['o'].get('kum_yil_ar_toplam_mn')!r}")
sina("ölçülemeyen anahtar ÖZETTEN SİLİNMİYOR (yayın kapısı onu bulmalı)",
     "kum_yil_ar_toplam_mn" in _G["o"]
     and "kum_yil_ar_toplam_mn_tarih" not in _G["o"],
     "boş değere saat konmuş" if "kum_yil_ar_toplam_mn_tarih" in _G["o"] else "")
sina("boş yazılan anahtar yine de ATLANAN sayılıyor (bayatlık hükmü düşer)",
     "kum_yil_ar_toplam_mn" in _G["atlanan"] and _G["o"]["bayat"] is True)


# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
