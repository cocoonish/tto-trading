# -*- coding: utf-8 -*-
"""Orta Vadeli Program ve ima edilen kur — veri katmanı.

HATTIN SORUSU
-------------
Program GSYH'yi hem TL hem dolar cinsinden yayımlıyor. İkisinin ORANI,
programın ima ettiği ORTALAMA KURDUR. Program bir kur patikası yayımlamaz —
ama bu oran onu ele verir. Ve gerçekleşen kur her gün değiştiği için
"programın tutması için yıl sonunda kur kaç olmalı" sorusunun cevabı HER GÜN
DEĞİŞİR. Hattın işi o cevabı canlı tutmaktır.

İKİ KATMAN, İKİ AYRI RİTİM
--------------------------
1. PROGRAM TABLOLARI STATİKTİR. Yayımlanmış bir belgenin sayıları bir daha
   değişmez; ağdan çekilmez, `programlar.json`da kaynak künyesiyle durur
   (hangi belge, hangi tablo, hangi sayfa). Bu dosya ELLE tutulur —
   Makroihtiyati hattındaki düzenleme defteriyle aynı sözleşme.
2. GERÇEKLEŞEN KUR CANLIDIR. Yahoo Finance'ten günlük kapanış çekilir
   (ortak/usdtry — kapsam ölçümlü, TTL'li önbellekle; KARAR 09.09.2026).

Üçüncü ve dördüncü bacak DEPODAN gelir, ağdan değil: TL gecelik faiz
(Fonlama hattının `data/gunluk.csv`si) ve gerçekleşen TÜFE (Enflasyon
hattının `data/metrik.csv`si). Bu yüzden hat `guncelle.py` kütüğünde
`bagimli=("fonlama", "enflasyon")` ile kayıtlıdır: üst hat tazelenmeden bu
hat koşarsa taşıma ve enflasyon bacakları dünkü seriden hesaplanmış kalır.
İKİSİ DE ZORUNLU DEĞİLDİR — düşerlerse kendi figürleri üretilmez ve bacağın
YAŞI sayfada yazılır; hattın manşeti (ima edilen kur) yalnız kur bacağına ve
program tablosuna dayanır.

EVDS3 tuzakları (bu depoda ölçüldü, kalıp Kredi hattından)
----------------------------------------------------------
· `evds2.tcmb.gov.tr/service/evds` ÖLÜ. Çalışan uç `evds3/igmevdsms-dis`;
  sorgu `?` ile BAŞLAMAZ, anahtar URL'de DEĞİL `key:` BAŞLIĞINDA gider.
· Tek istek ~1000 satır döndürür, gerisini UYARI VERMEDEN kırpar ve aralığın
  SONUNDAN geriye doldurur — yani kesilen şey TARİHÇENİN BAŞIDIR. Bugün tek
  parça yetse bile parçalama döngüsü KALDIRILMAZ.
· Bitiş İLERİ atılır (ILERI_GUN): TCMB ertesi iş gününün gösterge kurunu bir
  gün önce ilan ediyor; bitişi bugüne kesmek o gözlemi sessizce düşürür.

Koşum:  python3 veri.py  [--yenile] [--yardim]
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.request

import pandas as pd

# --------------------------------------------------------------------------- yollar
PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parent.parent                      # …/TTO Trading
VERI = PROJE / "data"
CACHE = VERI / "cache"
CIKTI = PROJE / "cikti"
for _p in (VERI, CACHE, CIKTI):
    _p.mkdir(parents=True, exist_ok=True)

# Depodan okunan iki bacak. Kardeş hatların ÜRETTİĞİ dosyalar; bu hat onlara
# yazmaz. Yolu tek yerde tutmanın sebebi, dosya taşındığında iki katmanın
# (veri.py ve duman.py) birlikte kaymasıdır.
FAIZ_DOSYA = KOK / "Aktarılacak Projeler" / "Fonlama" / "data" / "gunluk.csv"
TUFE_DOSYA = KOK / "Aktarılacak Projeler" / "Enflasyon" / "data" / "metrik.csv"
PROGRAM_DOSYA = PROJE / "programlar.json"


def _bicim():
    """ortak/bicim — okura giden her sayı ve tarih buradan yazılır.

    Alt süreçte `PYTHONPATH` ortak/'ı taşıyor; taşımadığı bir kabuktan
    koşulduğunda da bulunsun diye yol elle ekleniyor. Aynı yardımcı
    metrik.py, grafik.py, ozet_uret.py ve duman.py içinde de var: sınayanla
    sınanan aynı yoldan modül bulmalı.
    """
    try:
        import bicim
    except ImportError:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


# --------------------------------------------------------------------------- anahtar
# EVDS anahtarı kaynak koda GÖMÜLMEZ. Arama sırası bütün hatlarda aynıdır.
_ADAYLAR = [
    PROJE / ".evds_key",
    KOK / ".evds_key",
    KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key",
]
_ANAHTAR: str | None = None

BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
CACHE_TTL_SAAT = 12

# EVDS'in sessiz kırpmasına karşı parça uzunluğu. İş günü serisinde 366 gün
# ~250 satır demek; sınırın çok altında kalır ve tarihçe uzadıkça da kalır.
PARCA_GUN = 366
# Bitiş ileri atılır — gerekçe modül başlığında.
ILERI_GUN = 10
# Çekimin alt sınırı. Hattın ÖLÇÜMÜ için gereken en eski gün, en eski
# programın ilk sütun yılından bir önceki yılın kapanışıdır (2023 sonu);
# buradan on yıl geriden sormanın sebebi başka: "kalan iş günü" tahmininin
# tatil payı, serinin KENDİ geçmişinden ölçülüyor ve o ölçüm kaç yıl varsa o
# kadar sağlam.
KUR_BAS = "2015-01-01"

# KARAR (09.09.2026, kullanıcı): gerçekleşen kur Yahoo Finance'ten (ortak/usdtry,
# kapsam ölçümlü, kapanmamış bar düşürülür). Ad kod değil kaynak etiketi.
KUR_SERI = {"usdtry": "USDTRY=X"}

# --------------------------------------------------------------------------- uyarı
# İKİ AİLE, İKİ AYRI HÜKÜM.
# SAG_UC_IZI: serinin SAĞ UCUNA dair kusurlar — bunlar sayfayı BAYAT ilan
#   eder, çünkü hepsi "bugünkü sayı ilerlemedi" demenin bir biçimidir.
# TARIHCE_IZI: tarihçenin ORTASINA dair kusurlar — okura gösterilir ama
#   sayfayı bayat İLAN ETMEZ. On yıllık günlük bir seride bir boşluk bulunması
#   neredeyse kesindir; aileye konsaydı sayfa sonsuza kadar bayat olurdu.
SAG_UC_IZI = ("TAZELİK", "ESKİ ÖNBELLEK", "SERİ YOK", "BAYAT", "ÖLÇÜM EKSİK")
TARIHCE_IZI = ("KAPSAM", "TARİHÇEDE BOŞLUK", "BACAK GERİDE")
_UYARI: list[str] = []

# Bacakların okur adları. Olay cümlesi ve koşu kaydı dosya adı basmasın diye
# TEK yerde durur; ozet_uret.py ve grafik.py buradan okur.
BLOK_OKUR = {
    "kur": "gerçekleşen kur",
    "faiz": "TL gecelik faiz",
    "tufe": "gerçekleşen TÜFE",
    "program": "program tabloları",
}

# Tazelik toleransları (gün). Kur her iş günü yayımlanır; TL gecelik faiz de
# öyle. TÜFE aylık ve ayın ilk iş günlerinde gelir. Program tabloları YILDA
# BİR yayımlanır — onun toleransı bir yılı aşan bir sessizliktir ve o zaten
# "yeni program çıktı, deftere girmedi" demektir.
TOLERANS_GUN = {"kur": 6, "faiz": 6, "tufe": 45, "program": 400}

# Ritmi AYLIK olan bacaklar: yaşları ayın SON gününden ölçülür (bkz.
# tazelik_olc). Ayrı bir küme, çünkü tolerans tablosu ritmi söylemez.
AYLIK_BACAK = frozenset({"tufe"})

# Şekil dosyaları TEK KAYNAK: grafik.py koşu sırasını buna karşı denetler,
# duman panel künyesi ve zorunlu listeyle örtüşmesini sınar.
SEKIL_DOSYALARI = (
    "01_ima_kur.html",
    "02_bu_yil.html",
    "03_yil_sonu.html",
    "04_tufe_deflator.html",
    "05_reel_tl.html",
    "06_carry.html",
    "07_revizyon.html",
)
# ZORUNLU figürler hattın SORUSUNU anlatanlardır: biri üretilemiyorsa siteye
# kopyalama olmaz (eski grafikle taze metin yayımlanmasın). Carry ve TÜFE
# figürleri depodan gelen bacaklara dayanıyor ve o bacaklar hattın manşetini
# taşımıyor; onların eksikliği hattı DURDURMAZ, adıyla görünür.
ZORUNLU_SEKIL = ("01_ima_kur.html", "02_bu_yil.html", "03_yil_sonu.html",
                 "07_revizyon.html")

# Yöntem sınamasının eşiği. OVP dipnotu milli gelir hesabında ihracat-ithalat
# AĞIRLIKLI kur kullanıldığını söylüyor, düz USD/TRY değil. "İhmal edilebilir"
# bir HÜKÜMDÜR ve her koşuda yeniden ölçülür; bu eşik onun sınırıdır.
YONTEM_ESIK_YUZDE = 1.0
# İç tutarlılık eşiği (puan): nominal GSYH artışı ile (1+büyüme)x(1+deflatör)
# arasındaki sapma. Kaynağın kendi yuvarlaması bu mertebede fark üretir.
TUTARLILIK_ESIK_PUAN = 0.10


def uyar(mesaj: str) -> None:
    """Görünür uyarı: ekrana basılır ve uyarilar.json'a taşınır."""
    if mesaj not in _UYARI:
        _UYARI.append(mesaj)
    print("  ! " + mesaj, flush=True)


def uyarilar() -> list[str]:
    return list(_UYARI)


def anahtar() -> str:
    """EVDS anahtarı — TEMBEL okunur (künye basmak ağa çıkmaz, anahtar istemez)."""
    global _ANAHTAR
    if _ANAHTAR is None:
        a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
        if not a:
            for yol in _ADAYLAR:
                if yol.exists():
                    try:
                        a = yol.read_text(encoding="utf-8").strip()
                    except OSError as ex:
                        print(f"UYARI: {yol} okunamadı ({type(ex).__name__}).")
                        a = ""
                    if a:
                        break
        if not a:
            raise RuntimeError(
                "EVDS anahtarı bulunamadı. export TTO_EVDS_KEY=<anahtar> ya da şu "
                "dosyalardan birine yazın (.gitignore'da): "
                + " / ".join(str(y) for y in _ADAYLAR))
        _ANAHTAR = a
    return _ANAHTAR


# ===========================================================================
#  PROGRAM TABLOLARI — statik kayıt, ama okunurken DENETLENİR
# ===========================================================================
def programlar() -> dict:
    """programlar.json'u okur ve YAPISINI denetler.

    Denetim ağa çıkmaz ve saniyeler sürer; sebebi şu: bu dosya ELLE tutuluyor
    ve elle tutulan bir tabloda bir sütunun kayması ya da bir yılın atlanması
    hiçbir yerde hata vermez — yalnız sayfada yanlış bir sayı görünür.
    """
    kayit = json.loads(PROGRAM_DOSYA.read_text(encoding="utf-8"))
    satir = kayit["satir"]
    for p in kayit["programlar"]:
        yillar = list(p["sutun"])
        for ad, hucre in p["deger"].items():
            if ad not in satir:
                raise RuntimeError(
                    f"{p['kod']}: '{ad}' satırının tanımı yok — birim ve okur adı "
                    "bilinmeden sayfaya sayı basılamaz.")
            if list(hucre) != yillar:
                raise RuntimeError(
                    f"{p['kod']}/{ad}: yıl sütunları tabloyla tutmuyor "
                    f"({list(hucre)} ≠ {yillar}). Bir sütun kaymış olabilir.")
    return kayit


def program_kodlari(kayit: dict) -> list[str]:
    """Programlar YENİDEN ESKİYE sıralı; ilki 'yeni program'dır.

    Sıra dosyadaki yazım sırasından DEĞİL yayım ayından türetilir: dosyaya
    üçüncü bir program eklenirken sıraya dikkat edilmesi gerekmesin.
    """
    return [p["kod"] for p in sorted(kayit["programlar"],
                                     key=lambda p: p["yayin_ay"], reverse=True)]


def program(kayit: dict, kod: str) -> dict:
    for p in kayit["programlar"]:
        if p["kod"] == kod:
            return p
    raise KeyError(kod)


def satir_serisi(p: dict, ad: str) -> dict[int, float]:
    """Bir programın bir satırı: {yıl: değer}; ölçülemeyen hücre DÜŞER.

    None'ı sıfıra çevirmek ya da taşımak yerine düşürmenin sebebi tek cümle:
    ölçülemeyen boş bırakılır, sıfır bir ölçüm sonucudur.
    """
    h = p["deger"].get(ad) or {}
    return {int(y): float(v) for y, v in h.items() if v is not None}


def sutun_turu(p: dict, yil: int) -> str:
    """'gerceklesme' | 'tahmin' | 'program' — YÖNTEM SINAMASININ KAPISI.

    Sınama yalnız GERÇEKLEŞME sütunlarında kurulabilir: 'gerçekleşme tahmini'
    (GT) sütunundaki fark yöntem farkı değil TAHMİN hatasıdır, program (P)
    sütunu ise henüz olmamış bir yıldır. İkisini karıştırmak, ölçtüğümüz şeyi
    değiştirir — ve tam olarak bu ayrım olmadan geçen yılın 2025 sütunu
    (+%0,39) yöntem sapması sanılırdı.
    """
    return p["sutun"][str(yil)]


def yayin_gunu(p: dict):
    """Programın YAYIN GÜNÜ — ölçülemiyorsa None.

    Belgenin kapağı yalnız ayı yazıyor. Bir ay damgası, ortak/bicim
    sözleşmesinde ayın SON gününe demirlenir; ay henüz kapanmadıysa o gün
    YARINA düşer ve yayına giden bir damga ölçülmemiş bir günü ilan etmiş
    olur. Bu yüzden ay kapanmadan gün yazılmaz: figürün damgası o gün için
    None kalır, program sürümü figürün KENDİ alt başlığında ("Eylül 2026")
    okura yine görünür. Ay kapandığı gün damga kendiliğinden gelir.
    """
    b = _bicim()
    g = b.tarihe_cevir(pd.Timestamp(p["yayin_ay"] + "-01").strftime("%m.%Y"))
    if g is None or g > dt.date.today():
        return None
    return g


def program_ay_yazi(p: dict) -> str:
    """Program sürümünün okur yazımı: 'Eylül 2026'. Figürün alt başlığına girer."""
    b = _bicim()
    t = pd.Timestamp(p["yayin_ay"] + "-01")
    return f"{b.AYLAR_TR[t.month - 1]} {t.year}"


# ===========================================================================
#  ÇEKİM
# ===========================================================================
def _cek(url: str, deneme: int = 3):
    son_hata: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:                                    # noqa: BLE001
            son_hata = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü: {son_hata}") from son_hata


def _tazelik():
    """ortak/tazelik — önbellek tazeliğinin TEK tanımı; TTO_YENILE orada okunur.
    Hat kendi klasöründen elle koşturulursa ortak/ PYTHONPATH'te olmayabilir;
    depo kökünden bulunur (kalıp: metrik.py'nin _bicim yardımcısı)."""
    try:
        import tazelik
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import tazelik
    return tazelik


def _taze(yol: pathlib.Path, ttl_saat: float) -> bool:
    """Önbellek hâlâ kullanılabilir mi — karar ortak/tazelik'te (TTO_YENILE)."""
    return _tazelik().taze(yol, ttl_saat)


def _yas_gun(yol: pathlib.Path) -> float:
    return _tazelik().yas_gun(yol)


def _ayristir(items, kolon: str) -> pd.Series:
    """İŞ GÜNÜ serisinin biçimi: 'DD-MM-YYYY'. Kolon adı = kodun nokta yerine
    alt çizgi taşıyan hâli."""
    df = pd.DataFrame(items)
    if kolon not in df.columns or "Tarih" not in df.columns:
        return pd.Series(dtype=float)
    s = pd.to_numeric(df[kolon].replace("", None), errors="coerce")
    s.index = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    return s.dropna().sort_index()


def _cache_yolu(kod: str, alt_sinir: str) -> pathlib.Path:
    """Önbellek anahtarı SORGU PENCERESİNİ taşır.

    Bu depoda ölçülmüş bir kusur: anahtar yalnız seri kodundan kuruluyken
    katalog başlangıcı geriye çekildiğinde önbellekteki KISA dosya hâlâ taze
    görünüyor (TTL dolmamış, ad değişmemiş) ve hat kısa tarihçeyle koşuyordu.
    ÜST SINIR ADA GİRMEZ: her gün değişir, girseydi hiç önbellek olmazdı.
    """
    return CACHE / f"gun_{kod.replace('.', '_')}_{alt_sinir}.csv"


def cek_kume(kodlar: dict[str, str], yenile: bool = False) -> pd.DataFrame:
    """AĞA ÇIKAN TEK ÇAĞRI. Seri bazında TTL'li önbellek, parçalı istek.

    Duman sınaması bu fonksiyonu bir lambda ile değiştirip `kos()`un TAMAMINI
    ağsız koşturur; ağa çıkan iş bu yüzden tek bir yerde toplanmıştır.
    """
    t0 = pd.to_datetime(KUR_BAS)
    t1 = pd.Timestamp.today().normalize() + pd.Timedelta(days=ILERI_GUN)
    out: dict[str, pd.Series] = {}
    for ad, kod in kodlar.items():
        if kod == "USDTRY=X":
            # Yahoo Finance — tek tanım ortak/usdtry; kapsam yetmezse eski önbellek.
            try:
                import usdtry as _u
            except ImportError:
                import sys as _s
                _s.path.insert(0, str(PROJE.parent.parent / "ortak"))
                import usdtry as _u
            k = _u.seri(bas=KUR_BAS, onbellek=VERI / "cache" / "usdtry_yahoo.csv",
                        ttl_saat=0 if yenile else CACHE_TTL_SAAT)
            for m in k.uyarilar:
                uyar("BAYAT: kur — " + m)
            out[ad] = k.seri
            continue
        cyol = _cache_yolu(kod, KUR_BAS)
        if _taze(cyol, CACHE_TTL_SAAT) and not yenile:
            s = pd.read_csv(cyol, index_col=0, parse_dates=True).iloc[:, 0]
            out[ad] = s
            continue
        guvenli = kod.replace(".", "_")
        try:
            parcalar: list[pd.Series] = []
            imlec = t0
            while imlec <= t1:
                sonu = min(imlec + pd.Timedelta(days=PARCA_GUN - 1), t1)
                url = (f"{BASE}/series={kod}&startDate={imlec:%d-%m-%Y}"
                       f"&endDate={sonu:%d-%m-%Y}&type=json")
                p = _ayristir(_cek(url).get("items", []), guvenli)
                if len(p):
                    parcalar.append(p)
                imlec = sonu + pd.Timedelta(days=1)
                time.sleep(0.15)
            if not parcalar:
                raise RuntimeError("boş yanıt")
            s = pd.concat(parcalar)
            s = s[~s.index.duplicated(keep="last")].sort_index()
        except Exception as ex:                                    # noqa: BLE001
            if cyol.exists():
                uyar(f"ESKİ ÖNBELLEK: kur serisi kaynaktan alınamadı, "
                     f"{_yas_gun(cyol):.0f} gün önce indirilen kopya kullanılıyor. "
                     "Bu bacak bayat olabilir.")
                s = pd.read_csv(cyol, index_col=0, parse_dates=True).iloc[:, 0]
            else:
                uyar("SERİ YOK: gerçekleşen kur serisi kaynaktan alınamadı ve "
                     "elde kopya da yok.")
                raise RuntimeError(f"kur serisi düştü ve önbellek yok: {ex}") from ex
        else:
            s.to_csv(cyol)
        out[ad] = s
    df = pd.DataFrame(out)
    df.index.name = "tarih"
    return df.sort_index()


def faiz_bacagi() -> pd.DataFrame:
    """TL gecelik faiz — Fonlama hattının depoya yazdığı seriden.

    Ağa çıkmaz. Dosya yoksa BOŞ çerçeve döner ve uyarı düşer: taşıma figürü
    üretilmez, hat durmaz. Bir kardeş hattın düşmesi bu hattın manşetini
    (ima edilen kur) götürmemeli.
    """
    if not FAIZ_DOSYA.exists():
        uyar("SERİ YOK: TL gecelik faiz serisi elde yok; taşıma ölçümü bu "
             "koşuda yapılmadı.")
        return pd.DataFrame()
    d = pd.read_csv(FAIZ_DOSYA, index_col=0, parse_dates=True)
    # ENDEKS DE ALINIR. Gecelik faizin BİLEŞİK getirisini kotasyonlardan
    # yeniden kurmak gün sayımı sorar ve bu seride yanlış cevap on puanı aşan
    # bir hata veriyor (bkz. metrik.carry_gerceklesen). Kaynağın kendi endeksi
    # (BİST TLREF Endeksi) o hesabı zaten yapmış ve aynı dosyada duruyor;
    # ölçünün resmî karşılığı varken onu yeniden türetmek, türetmenin
    # doğruluğunu da ölçmeyi gerektirir.
    var = [k for k in ("tlref", "tlref_endeks", "politika") if k in d.columns]
    if not var:
        uyar("SERİ YOK: TL gecelik faiz dosyasında beklenen sütunlar yok; "
             "taşıma ölçümü bu koşuda yapılmadı.")
        return pd.DataFrame()
    return d[var].sort_index()


def tufe_bacagi() -> pd.DataFrame:
    """Gerçekleşen TÜFE (yıllık, aylık damgalı) — Enflasyon hattının ölçümünden.

    Ağa çıkmaz. Yıl sonu TÜFE'si ARALIK gözlemidir; program tablosundaki
    "TÜFE yıl sonu" satırıyla ancak o gözlem karşılaştırılabilir.
    """
    if not TUFE_DOSYA.exists():
        uyar("SERİ YOK: gerçekleşen TÜFE serisi elde yok; enflasyon "
             "karşılaştırması bu koşuda yapılmadı.")
        return pd.DataFrame()
    d = pd.read_csv(TUFE_DOSYA, parse_dates=["tarih"])
    if not {"seri", "yillik", "tarih"} <= set(d.columns):
        uyar("SERİ YOK: gerçekleşen TÜFE dosyasında beklenen sütunlar yok; "
             "enflasyon karşılaştırması bu koşuda yapılmadı.")
        return pd.DataFrame()
    t = d[d["seri"] == "tufe"].set_index("tarih")[["yillik"]].dropna()
    t = t.rename(columns={"yillik": "tufe_12a"}).sort_index()
    return t


# ===========================================================================
#  ÖLÇÜM — hepsi çerçevenin fonksiyonu, hiçbiri ağa çıkmaz
# ===========================================================================
def cerceve_imza(K: pd.DataFrame) -> str:
    """Kaydın ANLATTIĞI çerçeveyi adıyla taşır: satır·sütun·ilk·son.

    Ölçüm katmanı veri katmanının kaydından uyarı devralırken bu künyeyi
    karşılaştırır; tutmuyorsa devralmaz ve "ÖLÇÜM EKSİK" der. Kayıttaki uyarı
    listesinin BOŞ durup ölçülen çerçevenin uyarı gerektirdiği bir hâl bu
    depoda gerçekten yaşandı.
    """
    if K is None or K.empty:
        return "0x0"
    return (f"{K.shape[0]}x{K.shape[1]}·{K.index[0]:%Y-%m-%d}·"
            f"{K.index[-1]:%Y-%m-%d}")


def son_gun(K: pd.DataFrame) -> pd.Timestamp:
    """Kur bacağının çıpası: SABİT TARİH YASAK, veriden okunur."""
    s = K["usdtry"].dropna()
    if s.empty:
        raise RuntimeError("kur serisi boş: dönem okunamadı")
    return s.index[-1]


def gerekli_bas(kayit: dict) -> pd.Timestamp:
    """Ölçüm için gereken en eski gün — KATALOGDAN türetilir, elle yazılmaz.

    En eski programın ilk sütun yılından bir ÖNCEKİ yılın son çeyreği: yıl
    sonu/yıl sonu devalüasyonu ölçmek için o yılın KAPANIŞI gerekir.
    """
    ilk = min(int(y) for p in kayit["programlar"] for y in p["sutun"])
    return pd.Timestamp(year=ilk - 1, month=10, day=1)


def kapsam_olc(K: pd.DataFrame, kayit: dict) -> dict:
    """Gelen serinin KAPSAMI: "veri geldi" ile "veri TAM geldi" aynı şey değil."""
    s = K["usdtry"].dropna() if "usdtry" in K.columns else pd.Series(dtype=float)
    ger = gerekli_bas(kayit)
    return {
        "n": int(len(s)),
        "bas": None if s.empty else s.index[0].strftime("%Y-%m-%d"),
        "son": None if s.empty else s.index[-1].strftime("%Y-%m-%d"),
        "gerekli_bas": ger.strftime("%Y-%m-%d"),
        "yeterli": bool(len(s) and s.index[0] <= ger),
        "sorulan_bas": KUR_BAS,
    }


def kapsam_yeterli(K: pd.DataFrame, kayit: dict) -> None:
    """DURDURUCU kapı: kapsam ölçümün ihtiyacına yetmiyorsa çıktı ÜRETİLMEZ.

    Yarım kalmış bir çekim kırpma ya da çökme demektir; o hâlde üretilen bir
    pano hiç panodan kötüdür, çünkü yeşil bir koşunun içinde yayımlanır.
    """
    k = kapsam_olc(K, kayit)
    if not k["yeterli"]:
        raise SystemExit(
            f"DURDU — kur serisinin kapsamı yetmiyor: {k['n']} gözlem, "
            f"başlangıç {k['bas']}, gereken {k['gerekli_bas']}. "
            "Kırpılmış bir tarihçeyle ima edilen kur ölçülemez.")


def bosluk_olc(K: pd.DataFrame) -> dict:
    """Tarihçenin ORTASINDAKİ boşluklar — bayatlık hükmüne GİRMEZ (TARİHÇE_İZİ)."""
    s = K["usdtry"].dropna()
    if len(s) < 3:
        return {"maks_gun": None, "maks_tarih": None, "uzun_bosluk": 0}
    fark = s.index.to_series().diff().dt.days.dropna()
    # 4 günden uzun boşluk = hafta sonu + bir tatilden fazlası.
    uzun = fark[fark > 4]
    i = int(fark.values.argmax())
    return {"maks_gun": int(fark.iloc[i]),
            "maks_tarih": fark.index[i].strftime("%Y-%m-%d"),
            "uzun_bosluk": int(len(uzun))}


def tazelik_olc(K: pd.DataFrame, F: pd.DataFrame, T: pd.DataFrame) -> dict:
    """Her bacağın YAŞI ayrı ölçülür: biri ilerlerken öteki sessizce donabilir.

    Kur bacağında NEGATİF gecikme normaldir (ertesi günün kuru bir gün önce
    ilan edilir); alarm üretilmez.
    """
    bugun = pd.Timestamp.today().normalize()
    out: dict[str, dict] = {}
    for ad, s in (("kur", K["usdtry"].dropna() if "usdtry" in K.columns else None),
                  ("faiz", F["tlref"].dropna() if "tlref" in F.columns else None),
                  ("tufe", T["tufe_12a"].dropna() if "tufe_12a" in T.columns else None)):
        if s is None or s.empty:
            out[ad] = {"son": None, "gecikme_gun": None, "tolerans": TOLERANS_GUN[ad]}
            continue
        # AYLIK bir bacağın YAŞI ayın SON gününden ölçülür. TÜFE serisi ayın
        # İLK gününde indeksli; ham indeksten ölçmek yaşı ayın uzunluğu kadar
        # (30 gün) BÜYÜTÜR ve tolerans daha veri gelmeden dolar. 09.09.2026'da
        # ölçüldü: Ağustos TÜFE'si 03.09'da yayımlandı, 01.08 çıpasıyla yaş
        # 15.09'da 45 günü aşıyor ve sıradaki yayıma (03.10) kadar 18 gün
        # SAHTE "bacak gecikti" satırı okura basılacaktı. Çıpa ortak/bicim
        # sözleşmesiyle aynı: bir ay damgası ayın son gününe demirlenir.
        son = s.index[-1]
        if ad in AYLIK_BACAK:
            son = son + pd.offsets.MonthEnd(0)
        out[ad] = {"son": son.strftime("%Y-%m-%d"),
                   "gecikme_gun": int((bugun - son).days),
                   "tolerans": TOLERANS_GUN[ad]}
    return out


def tazelik_denetimi(taz: dict) -> list[str]:
    uy: list[str] = []
    b = _bicim()
    for ad, k in taz.items():
        if k["son"] is None:
            continue
        if k["gecikme_gun"] > k["tolerans"]:
            uy.append(
                f"TAZELİK: {BLOK_OKUR[ad]} bacağının son gözlemi "
                f"{b.tarih_kisa(k['son'])}, bugün itibarıyla {k['gecikme_gun']} gün "
                f"geride (tolerans {k['tolerans']} gün).")
    return uy


def kapsam_uyarilari(K: pd.DataFrame, kayit: dict) -> list[str]:
    uy: list[str] = []
    k = kapsam_olc(K, kayit)
    b = _bicim()
    # Sorulan gün ile ilk gözlem arasında birkaç günlük fark TAKVİMDİR (yılbaşı,
    # hafta sonu), kırpma değil. Ölçüt bir zamanlar tam eşitlik arıyordu ve her
    # koşuda yanlış alarm veriyordu; bir denetim yanlış alarm ürettiğinde kimse
    # ona bakmaz, yani kapsam kadar HASSASİYET de denetimin parçasıdır.
    if k["bas"] and (pd.Timestamp(k["bas"])
                     - pd.Timestamp(k["sorulan_bas"])).days > 15:
        uy.append(f"KAPSAM: kur serisi {b.tarih_kisa(k['sorulan_bas'])} tarihinden "
                  f"soruldu, ilk gözlem {b.tarih_kisa(k['bas'])} — kaynak bu "
                  "tarihten öncesini vermiyor.")
    return uy


def bosluk_uyarilari(K: pd.DataFrame) -> list[str]:
    uy: list[str] = []
    b = _bicim()
    d = bosluk_olc(K)
    if d["maks_gun"] and d["maks_gun"] > 10:
        uy.append(f"TARİHÇEDE BOŞLUK: kur serisinde en uzun kesinti "
                  f"{b.sayi(d['maks_gun'], 0)} gün ({b.tarih_kisa(d['maks_tarih'])}).")
    return uy


def bacak_uyarilari(taz: dict) -> list[str]:
    """Depodan gelen bacakların kur bacağına göre GERİDE kalması.

    Bu bir tazelik kusuru değil BAĞIMLILIK kusurudur: kardeş hat henüz
    koşmamış olabilir. Bayatlık hükmüne girmez (TARİHÇE_İZİ), ama adıyla
    görünür — yoksa taşıma figürü dünkü faizle çizilir ve kimse fark etmez.
    """
    uy: list[str] = []
    b = _bicim()
    kur = taz.get("kur", {}).get("son")
    if not kur:
        return uy
    for ad in ("faiz",):
        son = taz.get(ad, {}).get("son")
        if son and son < kur:
            fark = (pd.Timestamp(kur) - pd.Timestamp(son)).days
            if fark > 3:
                uy.append(f"BACAK GERİDE: {BLOK_OKUR[ad]} serisi kur serisinden "
                          f"{b.sayi(fark, 0)} gün geride "
                          f"({b.tarih_kisa(son)} ↔ {b.tarih_kisa(kur)}).")
    return uy


def program_tutarlilik(kayit: dict) -> list[dict]:
    """Programın KENDİ içindeki üç özdeşlik — her koşuda yeniden ölçülür.

    Bir kez doğrulanıp bırakılmaz: `programlar.json` elle tutuluyor ve bir
    hücre düzeltilirken bir başkası kayabilir. Sınama saniyeler sürüyor.

    (1) nominal GSYH artışı = (1+büyüme)x(1+deflatör)
    (2) cari denge / GSYH   = cari denge ÷ dolar GSYH
    (3) faiz gideri / GSYH  = faiz gideri ÷ TL GSYH
    Dördüncüsü de var ve tam tutuyor: dış ticaret dengesi = ihracat − ithalat.
    """
    kayitlar: list[dict] = []
    for p in kayit["programlar"]:
        tl = satir_serisi(p, "gsyh_tl")
        usd = satir_serisi(p, "gsyh_usd")
        buy = satir_serisi(p, "buyume")
        de = satir_serisi(p, "deflator")
        cari = satir_serisi(p, "cari")
        cari_o = satir_serisi(p, "cari_gsyh")
        fz = satir_serisi(p, "faiz_gideri")
        fz_o = satir_serisi(p, "faiz_gideri_gsyh")
        ihr = satir_serisi(p, "ihracat")
        ith = satir_serisi(p, "ithalat")
        dtd = satir_serisi(p, "dis_ticaret_dengesi")
        yillar = sorted(tl)
        for y in yillar[1:]:
            if y - 1 not in tl or y not in buy or y not in de:
                continue
            olculen = (tl[y] / tl[y - 1] - 1) * 100
            beklenen = ((1 + buy[y] / 100) * (1 + de[y] / 100) - 1) * 100
            kayitlar.append({"program": p["kod"], "yil": y, "ad": "nominal_gsyh",
                             "olculen": olculen, "beklenen": beklenen,
                             "sapma": olculen - beklenen, "birim": "puan"})
        for y in yillar:
            if y in cari and y in usd and y in cari_o:
                o = cari[y] / usd[y] * 100
                kayitlar.append({"program": p["kod"], "yil": y, "ad": "cari_gsyh",
                                 "olculen": o, "beklenen": cari_o[y],
                                 "sapma": o - cari_o[y], "birim": "puan"})
            if y in fz and y in tl and y in fz_o:
                o = fz[y] / tl[y] * 100
                kayitlar.append({"program": p["kod"], "yil": y, "ad": "faiz_gsyh",
                                 "olculen": o, "beklenen": fz_o[y],
                                 "sapma": o - fz_o[y], "birim": "puan"})
            if y in ihr and y in ith and y in dtd:
                o = ihr[y] - ith[y]
                kayitlar.append({"program": p["kod"], "yil": y, "ad": "dis_ticaret",
                                 "olculen": o, "beklenen": dtd[y],
                                 "sapma": o - dtd[y], "birim": "milyar dolar"})
    return kayitlar


def tutarlilik_uyarilari(kayitlar: list[dict]) -> list[str]:
    b = _bicim()
    uy: list[str] = []
    AD = {"nominal_gsyh": "nominal gelir artışı", "cari_gsyh": "cari denge oranı",
          "faiz_gsyh": "faiz gideri oranı", "dis_ticaret": "dış ticaret dengesi"}
    for r in kayitlar:
        esik = TUTARLILIK_ESIK_PUAN if r["birim"] == "puan" else 0.06
        if abs(r["sapma"]) > esik:
            uy.append(
                f"TUTARLILIK: {r['program']} programının {r['yil']} yılında "
                f"{AD[r['ad']]} özdeşliği tutmuyor — tablodan hesaplanan "
                f"{b.sayi(r['olculen'], 2)}, tabloda yazan "
                f"{b.sayi(r['beklenen'], 2)}.")
    return uy


def cerceve_uyarilari(K: pd.DataFrame, F: pd.DataFrame, T: pd.DataFrame,
                      kayit: dict) -> list[str]:
    """TEK TANIM, İKİ KATMAN: veri.py ve metrik.py aynı fonksiyonu kendi
    çerçevesiyle çağırır.

    Çerçeveden TÜRETİLEBİLEN uyarı devralınmaz, YENİDEN ÖLÇÜLÜR. Devir yalnız
    çerçeveye bakarak bilinemeyen olaylar içindir: ağ düştü, seri hiç gelmedi,
    önbellekten okundu.
    """
    taz = tazelik_olc(K, F, T)
    return (kapsam_uyarilari(K, kayit) + bosluk_uyarilari(K)
            + tazelik_denetimi(taz) + bacak_uyarilari(taz)
            + tutarlilik_uyarilari(program_tutarlilik(kayit)))


# ===========================================================================
#  ŞEKİL SAAT DEFTERİ — bir figürün damgası, HATTIN saati değildir
# ===========================================================================
#  Bu hatta iki cins bacak var ve ritimleri kıyas kabul etmiyor:
#    · PROGRAM TABLOSU — yılda bir yayımlanan, bir daha değişmeyecek bir belge.
#      Saati, ait olduğu programın yayın ayıdır (gün belgede yok, uydurulmadı).
#    · GERÇEKLEŞEN KUR — her iş günü ilerleyen bir seri.
#  Aradaki mesafe bir yıla varıyor. Böyle bir figürde "en eski bacak" kuralını
#  düz uygulamak, TAZE olan kur bacağını bir yıl bayat gösterirdi; en yenisini
#  yazmak da program sürümünü bugünkü gibi gösterirdi. İkisi de bu depoda
#  adlandırılmış birer kusur. Üçüncü yol kullanılıyor: İKİ PARÇALI DAMGA
#  ("program 09.2025 · gerçekleşen 03.09.2026"). Bileşen tanımadığı dizgeyi
#  olduğu gibi basar ve sayfa sınavı birleşik damganın İÇİNDEKİ her tarihi
#  ayrı ayrı sınar.
#
#  Birleşik damga `_sekil_tarih` defterine YAZILAMAZ (o ölçüt tek bir tarih
#  ister ve çözemediğini ENGEL sayar): defterde değeri None kalır, MDX o
#  figüre `tarihAnahtari` ile birleşik anahtarı verir. İkisi de AYNI
#  fonksiyondan türetilir, yani bir gün sessizce ayrışamazlar.
def sekil_saatleri(o: dict, uzun: bool = False) -> dict[str, str | None]:
    """Figür başına veri ucu; `o` = data/metrik_ozet.json.

    Değerler ÖLÇÜMDEN gelir, türetilmez. Ölçüm yoksa değer None kalır ve o
    şeklin altına tarih basılmaz — uydurmaktan iyidir.

    `uzun=True` figürün KENDİ alt başlığının yazımını verir ("3 Eylül 2026" ·
    "Eylül 2025"); varsayılan site sözleşmesidir ("03.09.2026" · "09.2025").
    """
    b = _bicim()

    def gun(t):
        if not t:
            return None
        return b.tarih_uzun(str(t)) if uzun else b.tarih_kisa(str(t))

    def ay(t):
        # AY damgası GÜN gibi yazılamaz: "30.09.2025" okura o GÜNÜN ölçümü
        # gibi görünür. ortak/bicim iki yazımı da çözer.
        if not t:
            return None
        g = b.tarihe_cevir(str(t))
        if g is None:
            return None
        return (f"{b.AYLAR_TR[g.month - 1]} {g.year}" if uzun
                else f"{g.month:02d}.{g.year}")

    def karma(program_ay, canli_gun, etiket="kur", aylik=False):
        """İki parçalı damga; bir parça ölçülemiyorsa öteki TEK BAŞINA yazılır.

        Tek parça kaldığında damga ÇIPLAK TARİH olur ve şekil saat defterine
        girebilir; iki parçalıysa defter onu alamaz (o ölçüt tek bir tarih
        ister) ve MDX'in açık anahtarına düşer. Ayrımı `defter_ayir` mekanik
        yapıyor, burada karar verilmiyor.

        Yazım KISA tutulur (en uzun hâli otuz beş karakter): ozet.json'un
        cümle alanlarını tarayan kapılar kırk karakterden uzun her metin
        değerini OKUR CÜMLESİ sayıyor ve bir damga cümle değildir — sayı
        yoğunluğu ölçütü orada yanlış alarm verirdi.
        """
        # AYLIK bir canlı bacak GÜN gibi yazılmaz: "01.08.2026" okura o GÜNÜN
        # ölçümü gibi görünür, oysa gözlem bütün ağustos ayına ait.
        p, k = ay(program_ay), (ay(canli_gun) if aylik else gun(canli_gun))
        if p and k:
            return f"program {p} · {etiket} {k}"
        return p or k

    kur = o.get("kur_tarih")
    tufe = o.get("tufe_tarih")
    faiz = o.get("faiz_tarih")
    # Karma figürlerin program bacağı: figürde geçen programların EN ESKİSİ.
    # min() YAPISAL yazılır, bugünkü sıralamaya bakmaz.
    eski = o.get("program_eski_yayin")
    yeni = o.get("program_yeni_yayin")
    return {
        "01_ima_kur.html": karma(eski, kur),
        "02_bu_yil.html": karma(yeni, kur),
        "03_yil_sonu.html": karma(eski, kur),
        "04_tufe_deflator.html": karma(eski, tufe, "enflasyon", aylik=True),
        "05_reel_tl.html": karma(eski, kur),
        # Taşımanın canlı bacağı İKİ seridir (kur ve gecelik faiz) ve ölçüm
        # katmanı ikisinin EN ESKİSİNİ `carry_tarih` olarak yazıyor. Burada
        # yeniden min() almak iki saati ayrıştırırdı: ölçülmüş bir saat
        # yeniden türetilmez.
        "06_carry.html": karma(yeni, o.get("carry_tarih") or faiz or kur,
                               "taşıma"),
        # Yalnız iki programın tablolarından çizilir; canlı bacağı yok.
        "07_revizyon.html": ay(eski),
    }


def defter_ayir(saatler: dict[str, str | None]) -> tuple[dict, dict]:
    """Şekil saatlerini İKİ tüketiciye MEKANİK olarak dağıtır.

    (defter, birlesik):
      · defter  → ozet.json `_sekil_tarih`; TEK tarih ya da None. Birleşik
        damga buraya yazılamaz (sayfa sınavı 18 çözemediğini ENGEL sayar).
      · birlesik → `damga_<figür kökü>` anahtarları; MDX bunları
        `tarihAnahtari` ile çağırır ve sayfa sınavı 18b içlerindeki her
        tarihi ayrı ayrı sınar.
    Ayrım BURADA, tek yerde yapılır: iki liste elle tutulsaydı bir gün
    sessizce ayrışır ve figürün alt başlığı ile sayfadaki damga farklı gün
    söylerdi.
    """
    b = _bicim()
    defter: dict[str, str | None] = {}
    birlesik: dict[str, str] = {}
    for dosya, deger in saatler.items():
        if deger and b.tarihe_cevir(deger) is None:
            defter[dosya] = None
            birlesik["damga_" + dosya.split(".")[0]] = deger
        else:
            defter[dosya] = deger
    return defter, birlesik


# ===========================================================================
#  GİRİŞ NOKTALARI
# ===========================================================================
def kunye_yaz() -> None:
    """`--yardim`: AĞA ÇIKMAZ. Katalog, tolerans ve şekil saat defterinin
    ANAHTARLARI basılır (defter boş sözlükle çağrılabilir olmalı)."""
    kayit = programlar()
    print("OVP hattı — künye")
    print(f"  program kaydı: {PROGRAM_DOSYA.name}")
    for kod in program_kodlari(kayit):
        p = program(kayit, kod)
        g = yayin_gunu(p)
        print(f"    {p['kisa']:<16} yayım {program_ay_yazi(p)} "
              f"(damga: {g.strftime('%m.%Y') if g else 'ay kapanmadı'}) "
              f"· {len(p['deger'])} satır · sütun {','.join(p['sutun'])}")
    print(f"  kur serisi: Yahoo Finance {KUR_SERI['usdtry']} · {KUR_BAS} tarihinden, "
          f"günlük kapanış (kapanmamış bar düşürülür)")
    print(f"  depodan gelen bacaklar: {FAIZ_DOSYA.name} (TL gecelik faiz) · "
          f"{TUFE_DOSYA.name} (gerçekleşen TÜFE)")
    print("  tolerans (gün): "
          + " · ".join(f"{BLOK_OKUR[k]} {v}" for k, v in TOLERANS_GUN.items()))
    print(f"  yöntem sınaması eşiği: %{YONTEM_ESIK_YUZDE} · "
          f"iç tutarlılık eşiği: {TUTARLILIK_ESIK_PUAN} puan")
    d, bl = defter_ayir(sekil_saatleri({}))
    print(f"  şekil saat defteri: {len(d)} figür ({', '.join(sorted(d))})")
    print(f"  birleşik damga anahtarları: {', '.join(sorted(bl)) or '—'}")
    print(f"  zorunlu figür: {', '.join(ZORUNLU_SEKIL)}")


def durum_kaydi(K: pd.DataFrame, F: pd.DataFrame, T: pd.DataFrame,
                kayit: dict) -> dict:
    """AĞSIZ. `kos()`un ÖLÇEN yarısı — duman sınaması bunu GERÇEK çerçeveyle
    çağırır.

    Ağa çıkan bir giriş noktasının İÇİNDE duran ölçüm hiçbir kapı tarafından
    koşturulmaz; bu depoda tam olarak o kusur ölçüldü ve hattın birinci adımı
    her koşuda ölecek durumdaydı.
    """
    for u in cerceve_uyarilari(K, F, T, kayit):
        uyar(u)
    taz = tazelik_olc(K, F, T)
    return {
        "kosum": dt.date.today().isoformat(),
        "son_gun": son_gun(K).strftime("%Y-%m-%d"),
        "kapsam": kapsam_olc(K, kayit),
        "bosluk": bosluk_olc(K),
        "tazelik": taz,
        "tutarlilik": program_tutarlilik(kayit),
        "programlar": {p["kod"]: {"yayin_ay": p["yayin_ay"],
                                  "satir": len(p["deger"]),
                                  "sutun": list(p["sutun"])}
                       for p in kayit["programlar"]},
        "kur": [int(K.shape[0]), int(K.shape[1])],
        "faiz": [int(F.shape[0]), int(F.shape[1])],
        "tufe": [int(T.shape[0]), int(T.shape[1])],
        "cerceve_imza": cerceve_imza(K),
        "uyarilar": list(_UYARI),
    }


def kosu_dokumu(durum: dict) -> list[str]:
    """AĞSIZ operatör dökümü. OKURA BASILMAZ — sabit genişlikli hizalama ve
    ISO tarih taşır; bu ayrım koda yazılıdır ki bir sonraki oturum bu kalıbı
    bir uyarı şablonuna kopyalamasın."""
    s = [f"  SON KUR GÜNÜ: {durum['son_gun']} · kapsam "
         f"{durum['kapsam']['n']} gözlem ({durum['kapsam']['bas']} → "
         f"{durum['kapsam']['son']})"]
    for ad, k in durum["tazelik"].items():
        s.append(f"  {ad:<8} son={k['son'] or '—':<12} "
                 f"gecikme={k['gecikme_gun'] if k['gecikme_gun'] is not None else '—':>5} "
                 f"tolerans={k['tolerans']}")
    kotu = [r for r in durum["tutarlilik"]
            if abs(r["sapma"]) > (TUTARLILIK_ESIK_PUAN if r["birim"] == "puan" else 0.06)]
    s.append(f"  program özdeşliği: {len(durum['tutarlilik'])} kayıt, "
             f"{len(kotu)} sapma")
    for kod, p in durum["programlar"].items():
        s.append(f"  {kod:<10} {p['yayin_ay']} · {p['satir']} satır · "
                 f"{len(p['sutun'])} sütun")
    return s


def kos(yenile: bool = False) -> dict:
    """İNCE gövde: çek → kapsam kapısı → ölç → iki dosya yaz → döküm bas."""
    print("EVDS3 + program kaydı → OVP hattı veri katmanı")
    kayit = programlar()
    K = cek_kume(KUR_SERI, yenile=yenile)
    kapsam_yeterli(K, kayit)
    F = faiz_bacagi()
    T = tufe_bacagi()

    durum = durum_kaydi(K, F, T, kayit)

    K.to_csv(VERI / "kur.csv")
    if not F.empty:
        F.to_csv(VERI / "faiz.csv")
    if not T.empty:
        T.to_csv(VERI / "tufe.csv")
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")

    for satir in kosu_dokumu(durum):
        print(satir)
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return durum


if __name__ == "__main__":
    if "--yardim" in sys.argv:
        kunye_yaz()
    else:
        kos(yenile="--yenile" in sys.argv)
