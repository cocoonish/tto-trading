# -*- coding: utf-8 -*-
"""OVP hattı — ozet.json üretimi (sayfanın canlı sayı kaynağı).

Sayfa metnindeki OYNAK her sayı buradan beslenir:
`<Deger proje="ovp" anahtar="…" ondalik={n}>statik yedek</Deger>`.

NE BURAYA GİRER
---------------
İki aile. Birincisi TÜREYEN ölçümler: ima edilen kur, gerçekleşenle arası,
kalan günlerin tutturması gereken ortalama, yıl sonu iması, taşıma, revizyon —
program sabit dursa bile bunlar her yeni kotasyonla değişir.

İkincisi PROGRAM TABLOSUNUN KENDİ SATIRLARI (`p_…` ve `pe_…`). Yayımlanmış bir
belgenin sayıları bir daha değişmez, yani sayfada statik de yazılabilirlerdi.
Yazılmıyorlar, çünkü sayının KAYNAĞI sayfa değil hat kaydıdır: oradaki bir
aktarım düzeltmesi sayfaya kendiliğinden ulaşmalı ve sayfada duran ikinci bir
kopya bir gün sessizce ayrışır. Anahtarlar yıl ADINI değil OFSETİ taşır
(y0 = programın ilk sütunu), yoksa yeni program geldiği gün sayfa kırılırdı.

SAAT — hangi sayının hangi güne ait olduğu
------------------------------------------
Üç CANLI bacak var (kur · lira gecelik faiz · gerçekleşen enflasyon) ve
dördüncüsü canlı değil: program tablosu. Hattın ana saati (`_tarih`) canlı
bacakların EN YENİSİDİR — çıpa değil: çıpayı hattın saati yapmak ilerlemiş
bir bacağı donmuş gösterir. Bayatlık hükmü ise EN GERİDE kalan bacaktan
kurulur; en tazesine bakmak bayat bir bacağı taze göstermek olurdu. Üç ölçü,
üç ayrı soru.

Program tablosundan TÜREYEN ölçümler bir GÜNE ait değildir (bir belgeye
aittir) ve kendi `_tarih` anahtarlarını taşımazlar; saatsiz denetimi bu
aileleri önek listesinden tanır. Belgenin sürümü sayfada ayrıca yazılır.

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys

import pandas as pd

import veri
from veri import PROJE, VERI, BLOK_OKUR, SAG_UC_IZI, TOLERANS_GUN

O: dict = {}
_ATLANAN: list[str] = []
# Blok saatleri MODÜL DÜZEYİNDE durur: saat, değeri yazan çağrının ARGÜMANI
# olmasın diye. Argüman olsaydı bir çağrı yerinde unutulur ve o sayı sessizce
# başka bir güne damgalanırdı.
_SAAT: dict[str, dt.date] = {}


def _bicim():
    try:
        import bicim
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


def _okur_dili():
    try:
        import okur_dili
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
        import okur_dili
    return okur_dili


def uyar(m: str) -> None:
    print(f"UYARI: {m}", file=sys.stderr)


# Anahtar → blok. Saat bu kuraldan fanlanır: `<anahtar>_tarih`.
BLOK_KURAL = (
    (re.compile(r"^(son_kur|ger_ort|sapma|gereken|yil_sonu|ytd|onceki_kapanis"
                r"|yil_basi|patika_farki|kalan_hareket|n_gerceklesen)"), "kur"),
    (re.compile(r"^carry_(tl|kur|net|yillik|ort_gecelik|gun|bas)"), "carry"),
    (re.compile(r"^tufe_(son|gecen)"), "tufe"),
    (re.compile(r"^politika_faizi"), "faiz"),
)

# SAATSİZ AİLELER — bir GÜNE ait olmayan ölçümler.
# Program tablosundan türeyen her şey buraya girer: bunlar yayımlanmış bir
# belgenin aritmetiğidir, bir günün gözlemi değil. Sayfada belgenin SÜRÜMÜ
# ayrıca yazılır, yani okur hangi programdan söz edildiğini görür.
SAATSIZ_ONEK = ("ima_", "rev_", "makas_", "tutarlilik_", "faiz_artis",
                "p_", "pe_",
                "nominal_artis", "program_", "kumule_", "eski_", "zincir_",
                "carry_ileri_", "carry_faiz", "yontem_", "kalan_", "bayat_",
                "gecikme_", "veri_gecikme_", "uyari_", "bu_yil", "yil_gun",
                "atlanan_", "beklenen_")
SAATSIZ = {"kosum_tarihi", "hat_saati_blok"}

# İSTEĞE BAĞLI AİLELER — bir koşuda hiç yazılmayabilecek anahtarlar.
# Sayfa sınavının 1. ölçütünde "isteğe bağlı anahtar" diye bir şey YOKTUR:
# MDX'in çağırdığı bir anahtar özette yoksa yayın DURUR. Bu yüzden bu
# ailelere düşen anahtarlar ölçülemediklerinde `null` yazılır — null,
# "ölçülmedi" demenin ta kendisidir — ve listesi sayfaya konur ki sayfayı
# yazan oturum "hangi anahtar güvenli" sorusunu tahminle cevaplamasın.
ISTEGE_BAGLI = (
    re.compile(r"^carry_"),          # lira gecelik faiz bacağı düşebilir
    re.compile(r"^tufe_(son|gecen)"),  # gerçekleşen enflasyon bacağı düşebilir
    re.compile(r"^zincir_y[0-9]_"),  # zincirin uzunluğu programın süresine bağlı
    re.compile(r"^eski_zincir_y[0-9]_"),
    # Ortak yıl sayısı programa göre değişir. Kalem adı ALT ÇİZGİ taşıyabilir
    # (cari_gsyh); `[a-z]+` yazımı onları aileye almıyordu ve satır bir gün
    # tablodan düştüğünde anahtar sessizce kaybolur, yayın durururdu.
    re.compile(r"^rev_[a-z_]+_y[0-9](_(yeni|eski))?$"),
    re.compile(r"^makas_y[0-9]$"),
    re.compile(r"^ima_y[0-9]$"),
    re.compile(r"^eski_ima_y[0-9]$"),
    re.compile(r"^yontem_r[0-9]_"),
    # Bütçe faiz gideri satırı her programda bulunmayabilir.
    re.compile(r"^(faiz_artis|nominal_artis)"),
    # Program tablosunun satırları: bir sonraki programda bir satır kalkabilir
    # ya da bir sütun eksik gelebilir. Anahtarın KAYBOLMASI sayfa sınavının
    # 1. ölçütünde yayını durdururdu; null "ölçülmedi" demenin kendisidir.
    re.compile(r"^pe?_[a-z_]+_y[0-9]$"),
)


def istege_bagli(anahtar: str) -> bool:
    return any(k.match(anahtar) for k in ISTEGE_BAGLI)


def blok_ad(anahtar: str) -> str | None:
    for kalip, ad in BLOK_KURAL:
        if kalip.match(anahtar):
            return ad
    return None


def _yaz(anahtar: str, deger, ondalik: int | None):
    if ondalik is None:
        O[anahtar] = deger
    elif ondalik == 0:
        O[anahtar] = int(round(float(deger)))
    else:
        O[anahtar] = round(float(deger), ondalik)


def koy(anahtar: str, deger, ondalik: int | None = 2) -> None:
    """Ölçülemeyeni ATLAR; isteğe bağlı aileye düşüyorsa `null` yazar.

    Atlamak ile null yazmak aynı şey değildir: atlanan anahtarın yerine
    sayfada MDX'teki statik yedek görünür ve o sabit güncel görünür ama
    değildir — bu yüzden atlanan sayısı bayatlık hükmüne girer. Null ise
    "ölçülmedi" demenin kendisidir ve sayfa onu boş basar.
    """
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        if istege_bagli(anahtar):
            O[anahtar] = None
            return
        _ATLANAN.append(anahtar)
        uyar(f"'{anahtar}' kaynakta yok — anahtar atlandı.")
        return
    _yaz(anahtar, deger, ondalik)


def olc(anahtar: str, deger, ondalik: int | None = 2) -> None:
    """koy + saatini KENDİ anahtarına fanlar (`<anahtar>_tarih`)."""
    koy(anahtar, deger, ondalik)
    if anahtar not in O or O[anahtar] is None:
        return
    ad = blok_ad(anahtar)
    if ad and _SAAT.get(ad):
        O[f"{anahtar}_tarih"] = _SAAT[ad].strftime("%d.%m.%Y")


def yil_yaz(anahtar: str, deger) -> None:
    """Bir YIL, sayı değil ETİKETTİR ve METİN olarak yazılır.

    Sayı olarak yazılsaydı sayfa onu biçim sözleşmesinden geçirir ve binlik
    ayracıyla "2.026" diye basardı — okur bunu bir yıl olarak okumaz. Aynı
    sebeple yıl anahtarları hiçbir ölçüme, sapma taramasına ya da bayatlık
    hükmüne girmez: adlandırdıkları şey bir gözlem değil, bir sütun.
    """
    O[anahtar] = None if deger is None else str(int(deger))


def konusuz(anahtar: str, deger, ondalik: int | None = 2) -> None:
    """Ölçülecek KONUSU olmayanı `null` yazar, ATLANAN saymaz.

    "Ölçemedik" ile "ölçülecek bir şey yoktu" aynı görünür ama aynı değildir:
    ayrım olmasaydı sınıfın boş olduğu her koşuda sayfa kendini bayat ilan
    ederdi — yani en sağlıklı hâlinde alarm çalardı.
    """
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        O[anahtar] = None
        return
    _yaz(anahtar, deger, ondalik)


def _saatler(m: dict) -> dict[str, dt.date]:
    """Blok saatleri — ölçüm katmanının yazdığı uçlardan."""
    b = _bicim()
    out: dict[str, dt.date] = {}
    for blok, anahtar in (("kur", "kur_tarih"), ("faiz", "faiz_tarih"),
                          ("tufe", "tufe_tarih"), ("carry", "carry_tarih")):
        g = b.tarihe_cevir(m.get(anahtar))
        if g:
            out[blok] = g
    return out


def _saatsiz_denetimi() -> list[str]:
    """Saati olmayan SAYI anahtarları — kapı değil, kayıt (kapı sayfa sınavında)."""
    eksik = []
    for a, v in O.items():
        if a.startswith("_") or a in SAATSIZ or a.startswith(SAATSIZ_ONEK):
            continue
        if a.endswith("_tarih") or a.endswith("_gun") or a.endswith("_yil"):
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if f"{a}_tarih" not in O:
            eksik.append(a)
    return sorted(eksik)


CUMLE_TAVAN, SAYI_TAVAN = 2, 1
# MUAF ALANLAR — ölçüt CÜMLEYİ sınar, her metni değil.
#   uyari_metni   : bir BİRLEŞTİRMEDİR; satırların kendisi ayrıca sınanıyor.
#   program_kaynak: KÜNYEDİR (belge adı, yılı, yayımcısı). İçindeki sayılar
#                   ölçüm değil kaynağın kendi adıdır ve sayı yoğunluğu ölçütü
#                   orada tanım gereği yanlış alarm verir.
#   damga_*       : şekil damgasıdır, cümle değil ("program 09.2025 · kur
#                   03.09.2026"). İki tarih taşır ve taşımak zorundadır.
CUMLE_OLCUSU_MUAF = {"uyari_metni", "program_kaynak"}
CUMLE_OLCUSU_MUAF_ONEK = ("damga_",)


def _cumle_denetimi() -> list[str]:
    """Okura basılan CÜMLE alanlarında kod ve yapım dili.

    Bu alanlar koşu kutusunda ve `<Deger>` içinde sayfaya OLDUĞU GİBİ basılır;
    hattın Python'u onları operatör için yazarsa okur dosya adı ve anahtar
    okur. Kapı sayfa sınavında, burada yalnız görünür kayıt.
    """
    od = _okur_dili()
    bulgu: list[str] = []
    for alan, metin in od.ozet_cumleleri(O):
        for aile, parca, _n in od.tara(metin):
            bulgu.append(f"{alan} — {aile}: {parca}")
    # KOŞU KAYDINDA MUAFİYET YOKTUR: backtick orada kod göstermez, dizge
    # sayfaya olduğu gibi basılır. `uyari_metni` birleştirmedir; satırların
    # kendisi tek tek sınanır.
    for _n, aile, parca in od.kosu_kaydi_tara(
            (O.get("uyari_metni") or "").split(" · ")):
        bulgu.append(f"{aile}: {parca}")
    return bulgu


def _cumle_olcusu_denetimi() -> list[str]:
    """Bir cümle en çok bir ölçüm taşır ve bir alan en çok iki cümle.

    Bir cümle altı ölçümü birleştirdiğinde altı bağımsız yanlışlaşma yolu
    açılır ve her düzeltme turu birini kapatıp başkasını açar — bir hata
    dizisi değil, bir TASARIM sorunu. `uyari_metni` birleştirmedir ve muaftır.
    """
    od = _okur_dili()
    bulgu = []
    for anahtar, deger in O.items():
        if (anahtar in CUMLE_OLCUSU_MUAF
                or anahtar.startswith(CUMLE_OLCUSU_MUAF_ONEK)
                or not isinstance(deger, str)):
            continue
        if " " not in deger or len(deger) < od.CUMLE_ESIK:
            continue
        cumle = len(re.findall(r"\.\s", deger)) + 1
        sayi = len(re.findall(r"\d", deger)) and len(
            re.findall(r"(?<![\w.])[−+]?\d+[.,]?\d*", deger))
        if cumle > CUMLE_TAVAN:
            bulgu.append(f"{anahtar}: {cumle} cümle (tavan {CUMLE_TAVAN})")
        if sayi > SAYI_TAVAN * cumle:
            bulgu.append(f"{anahtar}: {sayi} sayı / {cumle} cümle "
                         f"(tavan cümle başına {SAYI_TAVAN})")
    return bulgu


def main() -> int:
    global _SAAT
    b = _bicim()
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    try:
        uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))
    except Exception as ex:                                        # noqa: BLE001
        uyar(f"koşu kaydı okunamadı ({type(ex).__name__}).")
        uy = {}
    try:
        vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    except Exception as ex:                                        # noqa: BLE001
        uyar(f"veri katmanının kaydı okunamadı ({type(ex).__name__}) — "
             "o katmanın uyarıları sayıma girmiyor.")
        vd = {}

    _SAAT = _saatler(m)
    if not _SAAT:
        # TARİHSİZ BİR ÖZET YAYINA GİREMEZ: sayfadaki her sayı bir güne aittir
        # ve o gün ölçülemiyorsa sayı da yayımlanamaz.
        raise SystemExit("DURDU — hiçbir blok saati kurulamadı.")

    canli = {k: v for k, v in _SAAT.items() if k in ("kur", "faiz", "tufe")}
    ana_blok = max(canli, key=lambda k: canli[k])
    O["_tarih"] = canli[ana_blok].strftime("%d.%m.%Y")
    O["hat_saati_blok"] = BLOK_OKUR[ana_blok]
    for blok, g in _SAAT.items():
        if blok == "tufe":
            # AYLIK bir gözlem GÜN gibi yazılamaz: "01.08.2026" okura o GÜNÜN
            # ölçümü gibi görünür. ortak/bicim iki yazımı da çözer.
            O["tufe_tarih"] = g.strftime("%m.%Y")
            O["tufe_ay"] = f"{b.AYLAR_TR[g.month - 1]} {g.year}"
        else:
            O[f"{blok}_tarih"] = g.strftime("%d.%m.%Y")
            O[f"{blok}_gun"] = b.tarih_uzun(g)
    O["kosum_tarihi"] = dt.date.today().strftime("%d.%m.%Y")
    bugun = dt.date.today()
    geride = max(canli, key=lambda k: (bugun - canli[k]).days)
    for blok, g in canli.items():
        O[f"gecikme_{blok}_gun"] = (bugun - g).days
    O["veri_gecikme_gun"] = (bugun - canli[geride]).days
    O["veri_gecikme_blok"] = BLOK_OKUR[geride]

    # ---------------------------------------------------------------- program
    yeni, eski = m["program_yeni"], m["program_eski"]
    O["program_yeni_ad"] = yeni["ad"]
    O["program_yeni_kisa"] = yeni["kisa"]
    O["program_yeni_yayin"] = yeni["yayin_yazi"]
    O["program_eski_ad"] = eski["ad"]
    O["program_eski_kisa"] = eski["kisa"]
    O["program_eski_yayin"] = eski["yayin_yazi"]
    O["program_kaynak"] = f"{yeni['kaynak']} · {eski['kaynak']}"
    yil_yaz("bu_yil", m["bu_yil"])
    O["yil_gun_ortancasi"] = m.get("yil_gun_ortancasi")

    # PROGRAM TABLOSUNUN KENDİ SATIRLARI DA BURADAN GEÇER.
    # Yayımlanmış bir belgenin sayıları bir daha değişmez, yani sayfada statik
    # yazılabilirlerdi. Yazılmıyorlar, çünkü sayının KAYNAĞI sayfa değil hat
    # kaydıdır (`programlar.json`): oradaki bir aktarım düzeltmesi sayfaya
    # kendiliğinden ulaşmalı, ve sayfada duran bir ikinci kopya bir gün sessizce
    # ayrışır. Yıl SÜTUNU değil OFSET taşırlar (y0 = programın ilk sütunu):
    # yıl adına bağlı bir anahtar, yeni program geldiği gün sayfayı kırardı.
    PANO_SATIR = ("gsyh_tl", "gsyh_usd", "kisi_basi_gelir", "buyume", "deflator",
                  "tufe", "cari", "cari_gsyh", "altin_haric_cari", "ihracat",
                  "ithalat", "dis_ticaret_dengesi", "brent", "enerji_ithalati",
                  "turizm_geliri", "issizlik", "faiz_gideri", "faiz_gideri_gsyh")
    kayit_tam = veri.programlar()
    for onek, blok in (("p", yeni), ("pe", eski)):
        p = veri.program(kayit_tam, blok["kod"])
        yillar = sorted(int(y) for y in p["sutun"])
        for i, y in enumerate(yillar):
            yil_yaz(f"{onek}_y{i}_yil", y)
            O[f"{onek}_y{i}_tur"] = {"gerceklesme": "gerçekleşme",
                                     "tahmin": "gerçekleşme tahmini",
                                     "program": "program"}[veri.sutun_turu(p, y)]
        for ad in PANO_SATIR:
            seri = veri.satir_serisi(p, ad)
            ond = kayit_tam["satir"][ad]["ondalik"]
            for i, y in enumerate(yillar):
                koy(f"{onek}_{ad}_y{i}", seri.get(y), ond)

    ima_y = m["ima"].get(yeni["kod"]) or {}
    ima_e = m["ima"].get(eski["kod"]) or {}
    bu_yil = int(m["bu_yil"])
    for i in range(4):
        y = bu_yil + i
        yil_yaz(f"ima_y{i}_yil", y)
        koy(f"ima_y{i}", ima_y.get(str(y)), 3)
        koy(f"eski_ima_y{i}", ima_e.get(str(y)), 3)

    # ------------------------------------------------------- yöntem sınaması
    ys = sorted(m.get("yontem") or [], key=lambda r: r["yil"], reverse=True)
    O["yontem_n"] = len(ys)
    O["yontem_esik"] = m.get("yontem_esik_yuzde")
    for i in range(2):
        r = ys[i] if i < len(ys) else {}
        yil_yaz(f"yontem_r{i + 1}_yil", r.get("yil"))
        O[f"yontem_r{i + 1}_program"] = r.get("program_kisa")
        koy(f"yontem_r{i + 1}_ima", r.get("ima"), 3)
        koy(f"yontem_r{i + 1}_ger", r.get("gerceklesen"), 3)
        koy(f"yontem_r{i + 1}_fark", r.get("fark_yuzde"), 3)
    if ys:
        en = max(ys, key=lambda r: abs(r["fark_yuzde"]))
        koy("yontem_maks_fark", abs(en["fark_yuzde"]), 3)
        yil_yaz("yontem_maks_yil", en["yil"])
        # İKİ CÜMLE, İKİ SAYI. Tek cümlede üç ölçüm birleştirilseydi üç
        # bağımsız yanlışlaşma yolu açılırdı; yıl kendi anahtarında duruyor.
        O["yontem_cumlesi"] = (
            f"Yöntem sınaması {O['yontem_n']} kapanmış yılda kuruldu. "
            f"En büyük sapma {b.yuzde(abs(en['fark_yuzde']), 2)}.")
    else:
        konusuz("yontem_maks_fark", None, 3)
        yil_yaz("yontem_maks_yil", None)
        O["yontem_cumlesi"] = ("Sınama bu koşuda kurulamadı: kapanmış ve "
                               "gerçekleşme olarak yayımlanmış yıl yok.")

    # -------------------------------------------------- içinde bulunulan yıl
    bu = (m.get("bu_yil_olcum") or {}).get(yeni["kod"]) or {}
    bu_e = (m.get("bu_yil_olcum") or {}).get(eski["kod"]) or {}
    olc("son_kur", bu.get("son_kur"), 4)
    olc("ger_ort_bu_yil", bu.get("gerceklesen_ortalama"), 3)
    olc("sapma_bu_yil", bu.get("sapma_yuzde"), 2)
    olc("ytd_yuzde", bu.get("ytd_yuzde"), 2)
    olc("yil_basi_kur", bu.get("yil_basi"), 4)
    olc("onceki_kapanis", bu.get("onceki_kapanis"), 4)
    olc("gereken_ort", bu.get("gereken_ortalama"), 3)
    olc("gereken_bugune_gore", bu.get("gereken_bugune_gore_yuzde"), 2)
    olc("yil_sonu_dogrusal", bu.get("yil_sonu_dogrusal"), 2)
    olc("yil_sonu_ustel", bu.get("yil_sonu_ustel"), 2)
    olc("patika_farki", bu.get("patika_farki_yuzde"), 3)
    olc("kalan_hareket", bu.get("yil_sonu_kalan_hareket_yuzde"), 2)
    koy("kalan_gun", bu.get("kalan_gun"), 0)
    koy("kalan_tatil_payi", bu.get("kalan_tatil_payi"), 0)
    koy("kalan_tatil_ornek_yil", bu.get("kalan_tatil_ornek_yil"), 0)
    koy("kalan_gun_tatilsiz", bu.get("kalan_gun_tatilsiz"), 0)
    olc("gereken_ort_tatilsiz", bu.get("gereken_ortalama_tatilsiz"), 3)
    olc("n_gerceklesen", bu.get("n_gerceklesen"), 0)
    olc("eski_gereken_ort", bu_e.get("gereken_ortalama"), 3)
    olc("eski_sapma_bu_yil", bu_e.get("sapma_yuzde"), 2)

    # ---------------------------------------------------------------- zincir
    for onek, kod in (("zincir", yeni["kod"]), ("eski_zincir", eski["kod"])):
        z = (m.get("zincir") or {}).get(kod) or []
        for i in range(4):
            r = z[i] if i < len(z) else {}
            yil_yaz(f"{onek}_y{i}_yil", r.get("yil"))
            koy(f"{onek}_y{i}_giris", r.get("giris"), 2)
            koy(f"{onek}_y{i}_ort", r.get("ovp_ortalama"), 2)
            koy(f"{onek}_y{i}_cikis", r.get("cikis"), 2)
            koy(f"{onek}_y{i}_deval", r.get("deval_yuzde"), 1)
            koy(f"{onek}_y{i}_tufe", r.get("tufe_yuzde"), 1)
            koy(f"{onek}_y{i}_reel", r.get("reel_tl_yuzde"), 1)
            koy(f"{onek}_y{i}_makas", r.get("makas_puan"), 1)

    for onek, kod in (("kumule", yeni["kod"]), ("eski_kumule", eski["kod"])):
        k = (m.get("kumule") or {}).get(kod) or {}
        yil_yaz(f"{onek}_bas_yil", k.get("bas_yil"))
        yil_yaz(f"{onek}_son_yil", k.get("son_yil"))
        koy(f"{onek}_kur", k.get("kur_yuzde"), 1)
        koy(f"{onek}_tufe", k.get("tufe_yuzde"), 1)
        koy(f"{onek}_reel", k.get("reel_tl_yuzde"), 1)

    # ---------------------------------------------------------------- taşıma
    c = m.get("carry") or {}
    ger = c.get("gerceklesen") or {}
    olc("carry_tl", ger.get("tl_yuzde"), 2)
    olc("carry_ort_gecelik", ger.get("ortalama_gecelik"), 2)
    olc("carry_kur", ger.get("kur_yuzde"), 2)
    olc("carry_net", ger.get("net_yuzde"), 2)
    olc("carry_yillik", ger.get("yillik_yuzde"), 2)
    koy("carry_gun", ger.get("gun"), 0)
    koy("carry_faiz", c.get("faiz_varsayimi"), 2)
    ileri = c.get("ileri") or []
    for i in range(4):
        r = ileri[i] if i < len(ileri) else {}
        yil_yaz(f"carry_ileri_y{i}_yil", r.get("yil"))
        koy(f"carry_ileri_y{i}_basit", r.get("basit_yuzde"), 1)
        koy(f"carry_ileri_y{i}_bilesik", r.get("bilesik_yuzde"), 1)
        koy(f"carry_ileri_y{i}_reel_faiz", r.get("reel_faiz_yuzde"), 1)
    O["carry_varsayim_cumlesi"] = (
        f"İleriye dönük taşıma, lira faizinin bugünkü "
        f"{b.yuzde(c.get('faiz_varsayimi'), 2)} seviyesinde sabit kalması "
        "varsayımıyla hesaplandı."
        if c.get("faiz_varsayimi") is not None else
        "İleriye dönük taşıma bu koşuda hesaplanmadı: lira gecelik faiz "
        "serisi elde yok.")

    # -------------------------------------------------------------- revizyon
    rev = m.get("revizyon") or []
    for kalem in ("ima_kur", "tufe", "buyume", "cari_gsyh", "deflator"):
        kayit = {r["yil"]: r for r in rev if r["kalem"] == kalem}
        kisa = "ima" if kalem == "ima_kur" else kalem
        for i in range(3):
            y = bu_yil + i
            yil_yaz(f"rev_{kisa}_y{i}_yil", y)
            r = kayit.get(y) or {}
            koy(f"rev_{kisa}_y{i}", r.get("fark"), 2)
            # Farkın yanında İKİ UÇ da yazılır: okur "yüzde 12,4 puan yukarı"
            # cümlesini tek başına okuduğunda neyin neye göre değiştiğini
            # göremez; sayfadaki tablo üç sütunludur.
            koy(f"rev_{kisa}_y{i}_yeni", r.get("yeni"), 2)
            koy(f"rev_{kisa}_y{i}_eski", r.get("eski"), 2)
    ima_rev = [r for r in rev if r["kalem"] == "ima_kur"]
    if ima_rev:
        en = max(ima_rev, key=lambda r: abs(r["fark"]))
        yil_yaz("rev_ima_maks_yil", en["yil"])
        koy("rev_ima_maks", en["fark"], 1)
        koy("rev_ima_maks_eski", en["eski"], 2)
        koy("rev_ima_maks_yeni", en["yeni"], 2)
    O["rev_hucre_sayisi"] = len(rev)
    O["rev_ortak_yil"] = len({r["yil"] for r in rev})

    # ------------------------------------------------- deflatör ve faiz gideri
    fg = (m.get("faiz_gideri") or {}).get(yeni["kod"]) or []
    kayit = {r["yil"]: r for r in fg}
    for i in range(4):
        y = bu_yil + i
        yil_yaz(f"makas_y{i}_yil", y)
        koy(f"makas_y{i}", (kayit.get(y) or {}).get("deflator_tufe_makasi_puan"), 1)
    # Faiz gideri manşeti, programın İLK program yılıdır (gerçekleşme tahmini
    # değil): sayfa "program yılında faiz gideri nominal gelirden şu kadar
    # hızlı artıyor" cümlesini oradan kurar.
    prog_yil = [y for y in sorted(kayit)
                if veri.sutun_turu(veri.program(veri.programlar(), yeni["kod"]), y)
                == "program"]
    r = kayit[prog_yil[0]] if prog_yil else {}
    yil_yaz("faiz_artis_yil", r.get("yil"))
    koy("faiz_artis", r.get("faiz_gideri_yuzde"), 1)
    koy("nominal_artis", r.get("nominal_gsyh_yuzde"), 1)
    koy("faiz_artis_fark", r.get("fark_puan"), 1)

    # ---------------------------------------------------------- iç tutarlılık
    tut = m.get("tutarlilik") or []
    esik = m.get("tutarlilik_esik_puan") or 0.1
    sapan = [r for r in tut
             if abs(r["sapma"]) > (esik if r["birim"] == "puan" else 0.06)]
    O["tutarlilik_n"] = len(tut)
    O["tutarlilik_sapan"] = len(sapan)
    koy("tutarlilik_esik", esik, 2)
    if tut:
        koy("tutarlilik_maks", max(abs(r["sapma"]) for r in tut
                                   if r["birim"] == "puan"), 3)
    O["tutarlilik_cumlesi"] = (
        f"Programların kendi içindeki {O['tutarlilik_n']} özdeşlik sınandı ve "
        "hepsi tuttu." if not sapan else
        f"Programların kendi içindeki {O['tutarlilik_n']} özdeşlikten "
        f"{len(sapan)} tanesi tutmuyor.")

    # ------------------------------------------------------ gerçekleşen TÜFE
    olc("tufe_son", m.get("tufe_son"), 2)
    tg = m.get("tufe_gerceklesen") or {}
    olc("tufe_gecen_yil", tg.get(str(bu_yil - 1)), 2)
    yil_yaz("tufe_gecen_yil_yil", bu_yil - 1)

    # ------------------------------------------------------------- koşu kaydı
    uyarilar = list(uy.get("uyarilar", []))
    for u in (vd.get("uyarilar") or []):
        if u not in uyarilar:
            uyarilar.append(u)

    # BAYATLIK ÜÇ SEBEPTEN KURULUR ve EN GERİDE kalan bacaktan ölçülür.
    tol = TOLERANS_GUN[geride]
    sebep: list[str] = []
    if O["veri_gecikme_gun"] > tol:
        sebep.append(f"{BLOK_OKUR[geride]} bacağı {O['veri_gecikme_gun']} gün "
                     f"geride (tolerans {tol} gün)")
    izler = [u for u in uyarilar if u.startswith(SAG_UC_IZI)]
    if izler:
        sebep.append(f"{len(izler)} tazelik uyarısı düştü")
    if _ATLANAN:
        sebep.append(f"{len(_ATLANAN)} ölçüm bu koşuda yapılamadı")
    O["bayat"] = bool(sebep)
    O["bayat_tolerans_gun"] = tol
    O["bayat_sebep_sayisi"] = len(sebep)
    O["atlanan_olcum_sayisi"] = len(_ATLANAN)
    O["bayat_cumlesi"] = (
        "Veri bayat: " + "; ".join(sebep) + "." if sebep else
        "Veri taze: bütün bacaklar tolerans içinde.")
    O["uyari_sayisi"] = len(uyarilar)
    O["uyari_metni"] = (" · ".join(uyarilar) if uyarilar
                        else "Bu koşuda uyarı yok.")
    O["uyari_cumlesi"] = (
        "Bu koşuda uyarı düşmedi." if not uyarilar else
        "Bu koşuda düşen tek uyarı budur:" if len(uyarilar) == 1 else
        f"Bu koşuda {len(uyarilar)} uyarı düştü:")

    # ------------------------------------------- şekil saat defteri ve damga
    # İKİ TÜKETİCİ, TEK DEFTER: aynı fonksiyonu grafik.py figürün KENDİ alt
    # başlığı için okuyor. Birleşik damga defterde duramaz (sayfa sınavı tek
    # bir tarih ister ve çözemediğini engel sayar); ayrım MEKANİK yapılır.
    defter, birlesik = veri.defter_ayir(veri.sekil_saatleri(m))
    O["_sekil_tarih"] = defter
    O.update(birlesik)

    O["_istege_bagli"] = sorted(a for a in O if istege_bagli(a))

    saatsiz = _saatsiz_denetimi()
    if saatsiz:
        uyar(f"saati olmayan {len(saatsiz)} sayı anahtarı: "
             + ", ".join(saatsiz[:8]))
    for satir in _cumle_denetimi():
        uyar(f"okur dili — {satir}")
    for satir in _cumle_olcusu_denetimi():
        uyar(f"cümle ölçüsü — {satir}")

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · hat saati {O['_tarih']} "
          f"({O['hat_saati_blok']}) · en geride {O['veri_gecikme_blok']} "
          f"({O['veri_gecikme_gun']} gün) · atlanan {len(_ATLANAN)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
