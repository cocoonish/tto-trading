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
139 hafta, stok tabloları 114 hafta), çünkü sınanan şeylerin yarısı tam bu
asimetriden doğuyor.

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import ast
import contextlib
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

# Keşifte ölçülen pencereler. Değişim tablosu stok tablolarından yarım yıl
# önce başlıyor ve bu asimetri hattın yarısını belirliyor: kümüle akım stoktan
# geriye uzatılamaz, kapsam denetimi her seriyi KENDİ beklenen başlangıcına
# karşı sormak zorunda, şekil damgaları da iki ayrı bacağa bağlanıyor.
AKIM_BAS, STOK_BAS, SON_HAFTA = "2024-01-05", "2024-06-28", "2026-08-28"
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
            H[f"pe_{etiket}_{kir}"] = rng.normal(0.0, sigma * olcek * 0.4, n).round(1)
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
     _kapsam["ar_toplam"]["n"] == 139 and _kapsam["stok_toplam"]["n"] == 114
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
sina("kapsam yetmeyince çıktı ÜRETİLMEZ kapısı kapanıyor",
     veri.kapsam_yeterli(H0)[0] is True
     and veri.kapsam_yeterli(H0.iloc[-10:])[0] is False,
     str(veri.kapsam_yeterli(H0.iloc[-10:])))
_topla(veri.kapsam_yeterli(H0.iloc[-10:])[1])

_uy_bosluk = veri.bosluk_uyarilari(_hafta_atla(H0))
_topla(*_uy_bosluk)
sina("atlanan hafta veri katmanında da görünüyor",
     len(_uy_bosluk) == 1 and _uy_bosluk[0].startswith("HAFTA ATLANDI"),
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
     len(_uy_kisa) == 1 and _uy_kisa[0].startswith("ARALIK KISALDI"),
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

# Kaynağın KENDİ içindeki tutarlılık: ölçülmüş kimliklere sıkı eşik konur,
# ölçülmemişlere KONMAZ. Ölçülmeyen bir seviyeye eşik koymak, ilk koşuda
# yanlış alarm üretip yayının önünde durmak demektir.
_uy_k, _rap_k = veri.kimlik_denetimi(H0)
_topla(*_uy_k)
_esiksiz = [r for r in _rap_k.values() if r.get("esik_bagil") is None]
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
uy_s, r_s = metrik.sifir_olc(Hs_sag, veri.OLU_ADAY, metrik.ESIK_SIFIR_BLOK)
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
uy_ic, r_ic = metrik.sifir_olc(Hs_ic, veri.OLU_ADAY, metrik.ESIK_SIFIR_BLOK)
sina("serinin ORTASINDAKİ sıfır bloğu sağ uç sayılmıyor",
     r_ic["seri"][_kol]["sag_uc_sifir_hafta"] == 0
     and r_ic["seri"][_kol]["ic_sifir_hafta"] >= 30,
     str(r_ic["seri"][_kol]))
sina("ortadaki blok için uyarı DÜŞMÜYOR (yanlış alarm yok)", not uy_ic,
     "; ".join(uy_ic)[:120])

Hs_kisa = _sifir_blok(H0, _kol, metrik.ESIK_SIFIR_BLOK - 1, sag_uc=True)
uy_kisa, _ = metrik.sifir_olc(Hs_kisa, veri.OLU_ADAY, metrik.ESIK_SIFIR_BLOK)
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
import ozet_uret         # noqa: E402

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


def _kutu(H: pd.DataFrame, sekil: bool = True) -> dict:
    """Ölçüm → çizim → özet zincirini GEÇİCİ dizinde uçtan uca koşturur."""
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
            json.dumps({"uyarilar": veri.uyarilar()}, ensure_ascii=False),
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
sina("ölçüm atlanınca sayfa kendini TAZE ilan etmiyor",
     bool(_L["atlanan"]) and _L["o"]["bayat"] is True
     and "taze" not in _L["o"]["bayat_cumlesi"],
     f"atlanan {len(_L['atlanan'])} · bayat {_L['o']['bayat']}")
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
