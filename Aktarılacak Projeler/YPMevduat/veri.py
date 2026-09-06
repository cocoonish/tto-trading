# -*- coding: utf-8 -*-
"""Yurt içi yerleşiklerin YP mevduatı — veri katmanı (EVDS3).

HATTIN SORUSU
-------------
"Döviz mevduatı ne kadar arttı" değil, "artışın ne kadarı gerçek para girişi,
ne kadarı değerleme". Seri milyon ABD doları cinsinden yayımlanıyor ve sepette
euro, sterlin ve kıymetli maden var: euro dolara karşı değer kazandığında USD
karşılığı hiçbir yeni para girmeden yükselir.

AYRIŞTIRMAYI BİZ TÜRETMİYORUZ — TCMB resmî olarak yayımlıyor:

    Δ stok  =  Parite etkisinden arındırılmış değişim  +  Parite etkisi
    (2.11 · 2.12)          (5.1 … 5.11)                    (5.12 … 5.22)

Bu katmanın işi ayrıştırmayı UYDURMAK değil, resmî ayrıştırmayı TAM ve
ÖLÇÜLMÜŞ biçimde indirmek: kapsam ölçülür, kimlik denetlenir, her serinin
kendi başlangıcı ve kendi son günü kayda geçer.

EN PAHALI OLASI HATA — İKİ FARKLI "TOPLAM"
------------------------------------------
TP.HPBITABLO4.1 (271.071,9) yurt DIŞI yerleşik bankaları da içeren GENİŞ
toplamdır; TP.HPBITABLO2.10 (231.357,0) yalnız yurt İÇİ yerleşiklerdir ve
hattın konusu budur. İkisi manşette yan yana konmaz; geniş toplam kullanılırsa
ADIYLA ve FARKIYLA geçer. Ayrım burada SÜTUN ADIYLA görünür kılınır
(`genis_toplam` ↔ `stok_toplam`) ve fark her koşuda ölçülüp künyeye yazılır —
bir sonraki oturum ikisini karıştıramasın.

FARK "YURT DIŞI BACAK" DEĞİLDİR — ve bu ayrım ölçümden geliyor. Künyenin kalem
numaralandırmasına göre 4.1 = "1. TOPLAM", 4.3 = "1.1.1", 4.8 = "1.1.2"
(ikisinin toplamı 1.1 = 2.10) ve 4.21 = "1.4. Yurt Dışı Yerleşik Bankalar".
Yani 4.1 − 2.10 = 1.2 + 1.3 + 1.4'tür; yalnız 1.4 yurt dışı yerleşik
bankalardır ve 4.21 BU HATTA ÇEKİLMİYOR. Üstelik farkın içindeki 1.3.4 kalemi
(TP.HPBITABLO4.20) tek başına 3.263,5 milyon dolar, yani farkın yüzde sekizi.
Ölçülen büyüklük İKİ TOPLAM ARASINDAKİ KAPSAM FARKIDIR ve adı da öyle konur
(`genis_fark_*`); "yurt dışı yerleşikler şu kadar tutuyor" cümlesi kurulmak
istenirse önce 4.21 kataloğa alınıp ÖLÇÜLMELİDİR. Hattın kendi kodu 1.3'ün ne
olduğunun ölçülmediğini bir yerde yazıp aynı büyüklüğü başka bir yerde okura
"yurt dışı bacak" diye basıyordu; bir düzeltme genelleştirilmeden tamamlanmaz.

BİRİM KARIŞIMI AYNI TABLODA
---------------------------
bie_hpbitablo2'de .10/.11/.12 MİLYON USD, .1/.2/.3/.6 BİN TL. "Trilyon"
ölçeğinde bir birim hatası gözle yakalanmaz. Bu yüzden birim yorumda değil
KATALOGDA durur (`Seri.birim`) ve tek kaynaktan okunur: metrik katmanı
dönüşümü oradan alır, üç ayrı liste tutulsaydı bir gün sessizce ayrışırdı.

TARİHÇE ASİMETRİK — KUSUR DEĞİL, AMA ÖLÇÜLMESİ GEREKEN BİR ASİMETRİ
-------------------------------------------------------------------
Değişim tablosu (hpbitablo5) 28-02-2014'ten, stok tabloları (2 ve 4)
28-06-2024'ten başlıyor: on yılı aşan bir fark. Bu bir hizalama kusuru
DEĞİLDİR ve hizalanmaya çalışılmaz; ama HANGİ ÖLÇÜM HANGİ PENCEREDEN geliyor
sorusu, asimetri büyüdükçe sayfanın yarısını belirler:

  · Yalnız değişim tablosundan türeyen her şey (haftalık arındırılmış akım,
    parite etkisi, kümüle toplamlar, iki bacağın ayrışması) o tablonun KENDİ
    penceresine sahiptir — stok tablosunun geç başlaması onları bağlamaz.
  · Stokun haftalık değişimini ve kimliği (Δ stok ≟ arındırılmış + parite)
    isteyen her şey İKİ tabloyu birden ister, yani yalnız ORTAK pencerede
    kurulabilir; kümüle akım da stoktan geriye uzatılmaz.

Ayrım yalnız cümlede değil KODDA duruyor: kimlik ayrı bir bloğa çıpalanıyor,
kümüle akım stok tablosunun ucuna hiç bakmıyor, ve okur cümlesi iki pencereyi
ayrı sayılarla yazıyor. Tek bir "ölçüm şu kadar haftayı kapsıyor" cümlesi
asimetri 25 haftayken küçük bir kusurdu; 539 haftaya çıkınca okura sayfanın
yarısını beş kat kısa gösterir hâle geldi.

BAŞLANGIÇ ELLE YAZILMAZ, ÖLÇÜLÜR
--------------------------------
28-02-2014 bir ölçümdür ve künyede kanıtıyla durur (`Seri.bas_kanit`: hangi
alt sınırdan sorulduğunda çıktı). Önceki değer (05-01-2024) ölçüm değildi —
ilk keşif koşusunun kendi sorgu alt sınırının iziydi, üstelik çekim de aynı
sabitten başlıyordu ve kapsam denetimi de onu ölçüt alıyordu: üç yer
birbirini doğruluyor görünürken hiçbiri ölçmüyordu. Üç sigorta birlikte
gider ve tek başına hiçbiri yetmez: (i) künye başlangıcın ölçülüp
ölçülmediğini TAŞIR ve ölçülmemiş başlangıç üzerine hüküm kurulmaz —
dayanağı "serinin öncesi yok" olan hükümler, yani DAYANAKSIZ sıfır sınıfı;
tanım gereği sıfır o dayanağı hiç kullanmaz ve kapıya girmez. (ii) Çekim
katalogdaki başlangıçtan bir yıl GERİDEN
sorar, böylece tarihçe uzarsa cevabın kendisi söyler; (iii) kapsam denetimi
iki yöne birden bakar — geç başlayan seri kırpma izidir, erken başlayan seri
kataloğun geride kaldığının.

UÇ NOKTA NOTU (ölçülmüş)
------------------------
`evds2.tcmb.gov.tr/service/evds` ÖLÜ. Çalışan uç:

    https://evds3.tcmb.gov.tr/igmevdsms-dis/{param}={deger}&...

Sorgu dizesi `?` ile BAŞLAMAZ; anahtar URL'de DEĞİL `key:` HTTP başlığında
gider. Tek istek ~1000 SATIRLA sınırlı ve aralığın SONUNDAN geriye dolduruyor,
gerisini uyarı vermeden kırpıyor — HTTP 200 döner, seri kısa gelir, koşu yeşil
biter. Bu hattın serileri 2024'te başladığı için bugün tek parça yeter; buna
rağmen parçalama döngüsü KALDIRILMAZ, çünkü tarihçe uzayınca ya da başlangıç
geriye çekilince kırpma SESSİZCE geri gelir.

Satır sınırı TARİH sayısına bağlıdır, SERİ sayısına değil: `series=A-B-C`
biçiminde birden çok seri tek istekte gelir. Bu yüzden seriler demet hâlinde
çekilir (35 istek yerine 6). Ama bir kod geçersizse EVDS BÜTÜN isteği
reddediyor; demet düşünce seriler tek tek denenir, yoksa bir bozuk kod diğer
beşini götürür.

Koşum:  python3 veri.py [--yenile]      · ağa çıkar
        python3 veri.py --yardim        · yalnız künyeyi basar, ağa ÇIKMAZ
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.request
from typing import NamedTuple

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- yollar
PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parent.parent                      # …/tto-trading
VERI = PROJE / "data"
CACHE = VERI / "cache"
for _p in (VERI, CACHE):
    _p.mkdir(parents=True, exist_ok=True)


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı (ondalık virgül, eksi
    U+2212, yüzde önde, tarih GG.AA.YYYY).

    Bu katmanın uyarı satırları `uyarilar.json` üzerinden sayfadaki koşu
    kutusuna OLDUĞU GİBİ basılıyor; oradaki her sayı bu sözleşmeyle yazılır.
    `f"{x:.1f}"` kalıbı hem ondalık nokta hem ASCII tire taşır ve yayın
    kapısında "biçim" bulgusu üretir.

    Koşuda `ortak/` PYTHONPATH'tedir (alt süreç ortamı); hat elle kendi
    klasöründen koşturulursa olmayabilir, o yüzden depo kökünden bulunur.
    """
    try:
        import bicim
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


# --------------------------------------------------------------------------- anahtar
# EVDS anahtarı kaynak koda GÖMÜLMEZ ve bu projeye .evds_key KOPYALANMAZ.
# Arama sırası: ortam değişkeni (CI'da depo secret'ı) → proje → kök → kardeş.
_ADAYLAR = [
    PROJE / ".evds_key",
    KOK / ".evds_key",
    KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key",
]

BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

CACHE_TTL_SAAT = 12
DEMET = 6                 # tek istekte kaç seri (satır sınırı seri sayısına bağlı DEĞİL)

# YAYIM RİTMİ — TEK TANIM, üç tüketici.
# Bu hattın bütün serileri aynı yayımdan gelir (Haftalık Para ve Banka
# İstatistikleri; Perşembe yayımı, Cuma damgalı, yedi günde bir). Üç ayrı ölçü
# bu tek sayıdan türer: parça uzunluğu (tek istekte kaç gün), tazelik toleransı
# (kaç günlük gecikme olağan) ve KAPSAM toleransı (beklenen başlangıç ile gelen
# başlangıç arasındaki kaç günlük fark kırpma sayılmaz). Üçü ayrı ayrı
# yazılsaydı bir gün sessizce ayrışır ve hangisinin neyi söylediği kimsenin
# aklında kalmazdı — bu depoda tam olarak bu sınıf kusur ölçüldü.
AILE_RITIM_GUN = {"haftalik": 7}

# EVDS'İN SESSİZ KIRPMASI — depo genelinde ölçülmüş davranış: tek istek
# ~1000 satır döndürüyor, gerisini UYARI VERMEDEN kırpıyor ve aralığın
# SONUNDAN geriye dolduruyor, yani kesilen şey tarihçenin BAŞIDIR. HTTP 200
# döner, "items" doludur, koşu yeşil biter.
SATIR_SINIRI = 1000
# Parça, sınırın onda dokuzu. Yüzde onluk pay bir güvenlik payı değil ölçüm
# payıdır: sınır "~1000" diye ölçüldü, tam 1000 diye değil.
PARCA_PAYI = 0.9
PARCA_HAFTA_GUN = int(SATIR_SINIRI * PARCA_PAYI) * AILE_RITIM_GUN["haftalik"]

# YOKLAMA PAYI — ÇEKİM, KATALOGDAKİ BAŞLANGIÇTAN GERİDEN SORAR.
#
# Bu payın gerekçesi bu hattın en pahalı kusurudur ve kusur yanlış bir tarih
# DEĞİLDİ: ölçüt ile ölçülen AYNI sabitten geliyordu. Katalogdaki başlangıç
# çekimin alt sınırıydı, kapsam denetimi de gelen başlangıcı aynı sabite karşı
# soruyordu — yani seri o sabitten daha eski bir gözlem taşısa bile denetim onu
# GÖREMEZDİ, çünkü hiç sorulmuyordu. Elle yazılmış bir sabit, kendi kendini
# doğrulayan bir ölçüm gibi görünüyordu ve on iki buçuk yıllık tarihçenin iki
# buçuk yılı yayımlanıyordu.
#
# Alt sınır bu yüzden bir yıl (53 hafta) GERİDEN sorulur: kaynak katalogdakinden
# eski bir gözlem yayımlıyorsa cevabın kendisi bunu söyler. 371 gün tam elli üç
# haftadır, yani sorgu alt sınırı da bir CUMAYA düşer ve haftalık ızgara kaymaz.
# Bedeli sıfıra yakın: yoklama payıyla birlikte pencere hâlâ tek parçaya sığıyor
# (aşağıdaki aritmetik `duman.py`de ENGEL olarak sınanıyor).
#
# YOKLAMA, HÜKÜM İÇİN YETMEZ. Bir yıllık pay "bu serinin başlangıcı ölçüldü"
# demek için değil, "başlangıç kaydığında görelim" demek içindir; serinin
# GERÇEKTEN nerede başladığı ancak kaynağın verebileceğinden kesinlikle daha
# eski bir alt sınırla (bkz. KESIF_ALT_SINIR) ölçülür. İkisi karıştırılırsa
# yoklama, kapatmak için konduğu kusurun kendisine dönüşür.
YOKLAMA_GUN = 53 * AILE_RITIM_GUN["haftalik"]

ILERI_GUN = 10            # bitiş tarihi ileri atılır (aşağıda gerekçesi)

_UYARI: list[str] = []
_ANAHTAR: str | None = None


# UYARI AİLELERİ — hangi önekin "bu koşuda bir ölçüm eksik ya da geride" dediği
# TEK yerde. Özet üreticisi bayatlık hükmünü buradan kuruyor ve önek listesini
# kendi tutuyordu: listede yalnız üç önek vardı ("TAZELİK", "ESKİ ÖNBELLEK",
# "BAYAT") ve bir seri HİÇ yüklenemediğinde basılan "SERİ YOK" cümlesi o listede
# yoktu. Sonuç ölçüldü: dört ölçüm anahtarı özetten düştü, sayfada onların
# yerine MDX'e elle yazılmış statik yedekler göründü ve hemen üstlerinde "Veri
# taze: bütün bacaklar tolerans içinde" yazıyordu — donmuş bir sayı, taze
# damgasının altında, üstelik aynı kutuda "SERİ YOK: …" cümlesi dururken.
# Sayfa kendisiyle çelişiyordu. Aile tanımı burada durur ki kapsam bir listeden
# değil sözleşmeden türesin.
#
# AİLE İKİYE AYRILDI: BAYATLIK SAĞ UCA DAİR BİR HÜKÜMDÜR.
# Tek aile vardı ve içinde tarihçeye dair iki önek duruyordu ("HAFTA ATLANDI",
# "ARALIK KISALDI", "KAPSAM"). Bunlar SERİNİN TAMAMINI tarıyor: 2015'teki tek
# bir eksik hafta, verisi bugüne kadar gelmiş bir sayfayı HER KOŞUDA bayat
# ilan ediyordu. On iki yıllık haftalık bir seride bir boşluk bulunması
# neredeyse kesin olduğu için hüküm kalıcı olurdu — yani ölçü, ölçtüğü şeyi
# ayırt edemez hâle gelirdi: gerçekten donmuş bir besleme ile on yıl önceki
# bir tatil kayması aynı cümleyi basardı.
#
# AYRIM: "bugünkü sayılar ilerlemedi mi" ile "tarihçenin şeklinde bir kusur
# var mı" AYRI sorulardır. Birincisi sayfadaki sayıya dokunur (bayatlık),
# ikincisi pencereye dokunur ve okura yine bildirilir — ama sayfayı bayat
# ilan etmez. Boşluk uyarıları bu yüzden kendi tarihine göre iki önekten
# birini alıyor (bkz. `bosluk_uyarilari`), KAPSAM ise tanımı gereği
# tarihçenin BAŞINA dair bir bulgudur ve sağ uçla ilgisi yoktur.
SAG_UC_IZI = ("TAZELİK", "ESKİ ÖNBELLEK", "SERİ YOK", "HAFTA ATLANDI",
              "ARALIK KISALDI", "ÖLÇÜM EKSİK", "BAYAT")
TARIHCE_IZI = ("KAPSAM", "TARİHÇEDE BOŞLUK", "TARİHÇEDE KISA ARALIK")

# Bayatlık hükmünü kuran aile SAĞ UÇ ailesidir; ad bunu söylesin diye
# `SAG_UC_IZI` yazılıyor. Eski ad ATIF olarak duruyor (iki liste değil, tek
# tanımın iki adı): ayrı ayrı yazılsalardı bir gün sessizce ayrışırdı.
TAZELIK_IZI = SAG_UC_IZI


def uyar(mesaj: str) -> None:
    """Görünür uyarı: ekrana basılır ve uyarilar.json üzerinden sayfaya gider.

    Bu satırlar OPERATÖRE değil OKURA yazılır: sütun adı, dosya adı, grup kodu
    ve komut anahtarı metne girmez; sayı ortak/bicim ile yazılır. Serinin adı
    her zaman katalogdaki okur adıdır (`okur_adi`), sütun adı değil.
    """
    if mesaj not in _UYARI:
        _UYARI.append(mesaj)
    print("  ! " + mesaj, flush=True)


def uyarilar() -> list[str]:
    """Bu koşuda basılan görünür uyarılar.

    metrik.py bunu KENDİ listesine katar; katmadığında tazelik ve kapsam
    uyarıları uyarilar.json'a hiç girmez ve sayfada görünmez — düzenin
    yasakladığı sessiz bayatlamanın tam kendisi.
    """
    return list(_UYARI)


def _evds_anahtari() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    for yol in _ADAYLAR:
        if yol.exists():
            try:
                a = yol.read_text(encoding="utf-8").strip()
            except OSError as ex:
                print(f"UYARI: {yol} okunamadı ({type(ex).__name__}).")
                a = ""
            if a:
                return a
    raise RuntimeError(
        "EVDS anahtarı bulunamadı. TTO_EVDS_KEY ortam değişkenini tanımlayın "
        "ya da şu dosyalardan birine yazın (hepsi .gitignore'da): "
        + " / ".join(str(y) for y in _ADAYLAR))


def anahtar() -> str:
    """Tembel okuma: künye basmak gibi ağa çıkmayan yollar anahtar istemesin."""
    global _ANAHTAR
    if _ANAHTAR is None:
        _ANAHTAR = _evds_anahtari()
    return _ANAHTAR


def _cek(url: str, deneme: int = 3):
    """EVDS3'ten JSON. Anahtar `key:` BAŞLIĞINDA gider, URL'de değil.

    Zaman aşımı AÇIKÇA yazılır: ortak/sitecustomize.py'nin ağ emniyeti
    `requests`'i sarıyor, bu hat ise urllib kullanıyor — o koruma buraya
    ULAŞMAZ. Zaman aşımısız bir istek, hattın bütün adımlarını asılı bırakır.
    """
    son_hata: Exception | None = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(
                url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:            # ağ, zaman aşımı, 5xx…
            son_hata = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü: {son_hata}") from son_hata


def _taze(yol: pathlib.Path, ttl_saat: float) -> bool:
    if not yol.exists():
        return False
    return (dt.datetime.now().timestamp() - yol.stat().st_mtime) / 3600 < ttl_saat


def _yas_gun(yol: pathlib.Path) -> float:
    return (dt.datetime.now().timestamp() - yol.stat().st_mtime) / 86400


# --------------------------------------------------------------------------- ayrıştırıcı
def _ayristir(items, kolonlar: list[str], bicim_ad: str) -> pd.DataFrame:
    """EVDS yanıtını çerçeveye çevirir. Kolon adı = kodun noktaları alt çizgi.

    `bicim_ad` ZORUNLU ve açıkça verilir, çünkü EVDS'in tarih biçimleri
    karıştırılınca seri SESSİZCE boşalır (hata değil, boş çerçeve). Bu hattın
    bütün serileri HAFTALIK(Cuma) ve haftalık damga iş günü serileriyle AYNI
    "DD-MM-YYYY" biçimindedir — ayrı bir "hafta" ayrıştırıcısı yazmak, olmayan
    bir biçim uydurmak olurdu.
    """
    if not items:
        return pd.DataFrame()
    df = pd.DataFrame(items)
    if "Tarih" not in df.columns:
        return pd.DataFrame()
    if bicim_ad == "gun":
        t = pd.to_datetime(df["Tarih"], format="%d-%m-%Y", errors="coerce")
    else:
        raise ValueError(f"bu hatta tanımlı olmayan tarih biçimi: {bicim_ad}")
    # Boş dize None'a çevrilmeden to_numeric'e verilirse gözlem NaN yerine
    # sessizce başka bir şeye dönüşebilir; eksik gözlem NaN kalmalı.
    out = {}
    for k in kolonlar:
        if k in df.columns:
            out[k] = pd.to_numeric(df[k].replace("", None), errors="coerce")
    if not out:
        return pd.DataFrame()
    d = pd.DataFrame(out)
    d.index = t
    d = d[~d.index.isna()].sort_index()
    d.index.name = "tarih"
    return d


def _url(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp) -> str:
    return (f"{BASE}/series={'-'.join(kodlar)}"
            f"&startDate={bas:%d-%m-%Y}&endDate={son:%d-%m-%Y}&type=json")


def _demet_cek(kodlar: list[str], bas: pd.Timestamp, son: pd.Timestamp,
               parca_gun: int, bicim_ad: str) -> pd.DataFrame:
    """Bir seri demetini tarih parçaları hâlinde çeker.

    Demetin tamamı düşerse (bir kod geçersizse EVDS bütün isteği reddediyor)
    seriler tek tek denenir; böylece bir bozuk kod diğer beşini götürmez.
    """
    guvenli = [k.replace(".", "_") for k in kodlar]
    parcalar: list[pd.DataFrame] = []
    imlec = bas
    while imlec <= son:
        sonu = min(imlec + pd.Timedelta(days=parca_gun - 1), son)
        try:
            items = _cek(_url(kodlar, imlec, sonu)).get("items", [])
            p = _ayristir(items, guvenli, bicim_ad)
        except Exception as ex:
            # TARİH ortak/bicim'den yazılır, `%m.%Y` ile DEĞİL. İki sebep ve
            # ikisi de bağımsız: (i) bu satır uyarı kaydı üzerinden sayfaya
            # olduğu gibi basılıyor ve yayın kapısının koşu kaydı ölçütü
            # `01.2024` yazımını "biçim" bulgusu sayıyor; (ii) burada
            # ayrıştırılan şey AYLIK bir gözlem değil, HAFTALIK bir serinin
            # gün hassasiyetli istek penceresidir — ay yazımı gün bilgisini
            # sessizce atar ve okur pencerenin nerede başladığını göremez.
            b_ = _bicim()
            uyar("Kaynak bir seri demetini vermedi "
                 f"({b_.tarih_kisa(imlec)}–{b_.tarih_kisa(sonu)}): "
                 "seriler tek tek deneniyor.")
            print(f"    (ayrıntı: {', '.join(kodlar)} — {ex})", flush=True)
            tekler = []
            for k, g in zip(kodlar, guvenli):
                try:
                    it = _cek(_url([k], imlec, sonu)).get("items", [])
                    d = _ayristir(it, [g], bicim_ad)
                    if len(d):
                        tekler.append(d)
                except Exception as ex2:
                    uyar(f"SERİ ALINAMADI: {k} "
                         f"({b_.tarih_kisa(imlec)}–{b_.tarih_kisa(sonu)}).")
                    print(f"    (ayrıntı: {ex2})", flush=True)
                time.sleep(0.2)
            p = pd.concat(tekler, axis=1) if tekler else pd.DataFrame()
        if len(p):
            parcalar.append(p)
        imlec = sonu + pd.Timedelta(days=1)
        time.sleep(0.2)
    if not parcalar:
        return pd.DataFrame()
    d = pd.concat(parcalar)
    return d[~d.index.duplicated(keep="last")].sort_index()


def sorgu_alt_siniri(s: Seri) -> pd.Timestamp:
    """Bu serinin çekimde SORULACAĞI alt sınır — TEK TANIM, ÜÇ TÜKETİCİ.

    Aritmetik üç yerde birden lazım: çekim (isteğin başlangıcı), kapsam kaydı
    (`sorulan_bas` — gelen başlangıcın anlamı ona bağlı) ve ÖNBELLEK ANAHTARI
    (aşağıdaki gerekçe). Üçü ayrı ayrı yazılsaydı biri güncellenip öteki
    unutulurdu; bu depoda tam bu sınıf kusur defalarca ölçüldü.
    """
    return pd.Timestamp(s.bas) - pd.Timedelta(days=YOKLAMA_GUN)


def _cache_yolu(kod: str, bicim_ad: str, alt_sinir) -> pathlib.Path:
    """Önbellek dosyası — ADI, DOSYAYI ÜRETEN SORGUYU DA TAŞIR.

    Önbellek SERİ BAZINDA tutulur: demet bileşimi değişince (bir seri eklenip
    çıkınca) önbelleğin tamamı geçersizleşmesin.

    ANAHTAR NEDEN ALT SINIRI TAŞIYOR — ÖLÇÜLMÜŞ BİR ARIZA. Anahtar bir süre
    yalnız biçim ve seri kodundan kuruluydu, yani AYNI dosya adı iki farklı
    sorgunun cevabını taşıyabiliyordu. Katalogdaki başlangıç 2024'ten 2014'e
    çekildiğinde (beş kat tarihçe) önbellekteki 139 haftalık dosya hâlâ TAZE
    görünüyordu: TTL dolmamıştı, ad değişmemişti, dosya olduğu gibi okunuyordu.
    Sonuç sessiz ve iki katlıydı — hat kısa tarihçeyle koşuyor, KAPSAM denetimi
    de gelen başlangıcı yeni katalogla kıyaslayıp kırpma görüyor ve kusuru
    KAYNAĞA yıkan bir uyarı basıyordu ("tarihçenin başı kesilmiş olabilir").
    Koşu yeşil bitiyordu. Koşucu önbelleği CI'da da geri yüklendiği için arıza
    yerelde kalmıyordu.

    KURAL (sınıf kusur): ÖNBELLEKLENEN BİR ÇIKTI, ONU ÜRETEN GİRDİYİ DE
    TAŞIMALIDIR. Girdi burada sorgunun alt sınırıdır ve o da katalogdaki
    başlangıç ile yoklama payından türer: ikisinden biri değişince ad değişir,
    eski dosya bir daha okunmaz.

    ÜST SINIR ADA GİRMEZ, ÇÜNKÜ HER GÜN DEĞİŞİR: istek hep "bugün + pay"a
    kadar sorulur ve o ucun tazeliğini TTL ölçer. Ada konsaydı önbellek her
    gün baştan kurulur, yani hiç önbellek olmazdı.
    """
    d = pd.Timestamp(alt_sinir)
    return CACHE / f"evds_{bicim_ad}_{kod.replace('.', '_')}_{d:%Y%m%d}.csv"


def _cache_eskisini_sil(kod: str, bicim_ad: str, tut: pathlib.Path) -> None:
    """Aynı serinin BAŞKA bir sorgu penceresinden kalmış önbellek dosyaları.

    Anahtar pencereyi taşıdığı için eski dosya artık OKUNMUYOR; ama silinmezse
    koşucu önbelleğinde sonsuza kadar birikir ve — daha kötüsü — katalogdaki
    başlangıç bir gün geri alınırsa yeniden CANLANIR. Bir daha okunmayacak
    dosyayı bırakmak, kapatılan kusura geri dönüş yolu bırakmaktır.
    """
    guvenli = kod.replace(".", "_")
    # ÖNEK SONDAKİ ALT ÇİZGİYİ TAŞIR VE BU BİLİNÇLİDİR: "…TABLO5_1" yazımı
    # "…TABLO5_10" ile başlıyor, yani çizgisiz bir önek bir serinin
    # temizliğinde BAŞKA bir serinin önbelleğini silerdi.
    adaylar = list(CACHE.glob(f"evds_{bicim_ad}_{guvenli}_*.csv"))
    # PENCERESİZ ESKİ YAZIM da temizlenir. Koşucu önbelleği bu dosyaları
    # taşımaya devam ediyor ve artık hiçbir yerden okunmuyorlar; bırakılırsa
    # sonsuza kadar birikirler. Ad TAM eşleşmeyle silinir, jokerle değil.
    eski_yazim = CACHE / f"evds_{bicim_ad}_{guvenli}.csv"
    if eski_yazim.exists():
        adaylar.append(eski_yazim)
    for y in adaylar:
        if y != tut:
            with contextlib.suppress(OSError):
                y.unlink()


# ===========================================================================
# SERİ KATALOĞU
# ===========================================================================
# BAŞLANGICIN ÖLÇÜLDÜĞÜ KEŞFİN ALT SINIRI.
# "Kaynağın verebileceğinden kesinlikle daha eski" olması ŞART: bir başlangıcı
# ölçmek, ondan ÖNCESİNİ sorup boş cevap almaktır. Alt sınır serinin gerçek
# başlangıcına yakınsa gelen cevap serinin değil SORGUNUN alt sınırıdır ve ikisi
# tıpatıp aynı görünür.
KESIF_ALT_SINIR = "2005-01-01"


class Seri(NamedTuple):
    """Bir serinin TEK künyesi: kod · başlangıç · başlangıcın kanıtı · birim · ad.

    Alanları ayrı sözlüklerde tutmak bu depoda ölçülmüş bir arıza sınıfıdır:
    listeler bir gün sessizce ayrışır ve hangisinin neyi söylediği kimsenin
    aklında kalmaz. Buradaki tek satır beş tüketiciyi birden besler — çekim
    (kod), kapsam denetimi (bas), HÜKÜM KAPISI (bas_kanit), ölçüm katmanının
    birim dönüşümü (birim) ve okura basılan her uyarı satırı (okur_adi).

    NEDEN BAŞLANGICIN AYRI BİR KANIT ALANI VAR. Başlangıç bu hatta bir kez
    ELLE yazıldı ve ölçüm sanıldı: ilk keşif koşusu 2024 başından sormuştu,
    dönen ilk cuma katalogda "kaynağın yayımladığı ilk gözlem" diye durdu ve
    çekim de aynı sabitten başladı. Ölçüt ile ölçülen aynı sabitten geliyordu,
    yani kapsam denetimi bu kusuru YAPISAL OLARAK göremezdi — daha eski bir
    gözlem hiç sorulmadığı için hiç görünmedi. Kusur elli iki hafta değil BEŞ
    KAT tarihçe kaybettirdi (653 hafta yerine 139).

    Bir sabitin ölçüm sanılmasını engelleyen tek şey, ölçülüp ölçülmediğinin
    KÜNYEDE yazılı olmasıdır. `bas_kanit` bunu tek bir soruya indirir: bu
    başlangıç HANGİ alt sınırdan sorulduğunda çıktı? Boşsa hiç sorulmamıştır.

    VARSAYILAN BOŞTUR VE BU BİLİNÇLİDİR. Yarın kataloğa eklenen bir seri kanıt
    alanı yazılmadan gelirse "ölçülmemiş" sayılır ve üzerine hüküm kurulmaz —
    yani unutmanın bedeli sessiz bir yanlış değil, eksik bir cümledir. Ters
    varsayılan (ölçülmüş saymak) tam olarak kapatmaya çalıştığımız kusuru
    yeniden üretirdi.
    """
    kod: str
    bas: str          # kaynağın yayımladığı İLK gözlem (kapsam denetiminin ölçütü)
    birim: str        # "mn USD" | "bin TL"
    okur_adi: str     # okura basılacak ad; parantezde kaynağın KENDİ seri kodu
    bas_kanit: str = ""   # `bas`ın ölçüldüğü sorgunun ALT SINIRI; boş = ölçülmedi


def kapsam_tolerans(aile: str = "haftalik") -> int:
    """Beklenen başlangıç ile gelen başlangıç arasında kırpma saymadığımız fark.

    Tolerans YAYIM RİTMİNDEN türer, elle yazılmaz: bir yayım aralığı kadar
    kayma kırpma değil, kaynağın kendi damgalama kararıdır (tatil kayması ilk
    haftayı birkaç gün öteleyebilir). İki aralık ise artık kaymadır — ve bu
    hatta gerçek bir kırpmanın ilk işareti de tam bir hafta olur: seri satır
    sınırını aştığı gün kaynak tarihçenin başından BİR hafta keser, yüz hafta
    değil. Dar tolerans o ilk haftayı yakalar, geniş tolerans kaçırırdı.
    """
    return int(AILE_RITIM_GUN[aile])


def bas_olculdu(ad: str) -> bool:
    """KATALOG YARISI: bu serinin başlangıcı ÖLÇÜLDÜ mü — yoksa elle mi yazıldı?

    DİKKAT — BU FONKSİYON TEK BAŞINA HÜKÜM KAPISI DEĞİLDİR. Yalnız kataloğu
    sorar; elimizdeki çerçevenin o başlangıca gerçekten uzanıp uzanmadığını
    SORMAZ. Hüküm kapısı `bas_olculen(H)`dir ve iki yarıyı birlikte ister
    (gerekçesi orada).

    Ölçüt bir bayrak değil ARİTMETİKTİR ve sebebi budur: bayrak elle konur,
    aritmetik konamaz. Bir başlangıç ancak ONDAN ÖNCESİ sorulup boş dönmüşse
    ölçülmüştür; sorgunun alt sınırı `bas`ın kendisiyse (bu hattın kusuru tam
    buydu) cevap zaten `bas`tan erken OLAMAZ ve ölçüm yapılmamıştır. Kanıt
    alanına yanlışlıkla `bas` yazan bir sonraki oturum bu yüzden sessizce
    "ölçüldü" damgası alamaz: aritmetik onu eler.

    Yayım ritmi kadar pay bırakılır — alt sınır ile başlangıç arasında yalnız
    birkaç günlük fark, kaynağın ilk haftasını sormamış olmakla aynı şeydir.
    """
    s = HAFTALIK.get(ad)
    if s is None or not s.bas_kanit:
        return False
    return (pd.Timestamp(s.bas) - pd.Timestamp(s.bas_kanit)).days > kapsam_tolerans()


def bas_cerceveye_ulasti(H: pd.DataFrame, ad: str) -> bool:
    """VERİ YARISI: ELİMİZDEKİ çerçeve, katalogdaki başlangıca kadar uzanıyor mu?

    Katalog "kaynak bu seriyi 28.02.2014'te yayımlamaya başladı" der; bu
    fonksiyon "peki bu koşuda çektiğimiz seri oraya kadar geliyor mu" diye
    sorar. İkisi AYRI sorulardır ve ayrıştıkları hâl sessizdir: kırpılmış ya da
    bayat önbellekten okunmuş bir çerçevede katalog hâlâ 2014 der, elimizdeki
    seri 2024'te başlar ve fark hiçbir yerde hükme girmez.

    Tolerans kapsam denetimiyle AYNI: bir yayım aralığı kadar kayma kırpma
    değil, kaynağın damgalama kararıdır. İki eşik ayrı yazılsaydı biri
    güncellenip öteki unutulurdu.
    """
    s = HAFTALIK.get(ad)
    if s is None or ad not in H.columns:
        return False
    d = H[ad].dropna()
    if d.empty:
        return False
    return (d.index[0] - pd.Timestamp(s.bas)).days <= kapsam_tolerans()


def bas_olculen(H: pd.DataFrame) -> tuple[str, ...]:
    """HÜKÜM KAPISI — "bu serinin ÖNCESİ YOK" diyebileceğimiz seriler.

    KAPI NEDEN İKİ YARILI. Dayanağı "serinin öncesi yok" olan her hüküm iki
    ayrı şeyin birden doğru olmasını ister:

      (i)  KAYNAĞIN ilk gözlemi ölçülmüş olmalı — yoksa katalogdaki başlangıç
           bir sorgu sınırının izi olabilir (`bas_olculdu`);
      (ii) ELİMİZDEKİ çerçeve o başlangıca kadar uzanmalı — yoksa gördüğümüz
           ilk gözlem serinin değil ÇEKİMİN başlangıcıdır.

    Kapı uzun süre yalnız (i)'yi soruyordu ve (ii) hiç sorulmuyordu. Sonuç
    yapısal olarak sessizdi: katalog 2014 derken elde 2024'te başlayan 139
    haftalık bir çerçeve varken "bu bacak serinin ilk gözleminden beri sıfır,
    üzerine hüküm kurulabilir" cümlesi kuruluyordu — 514 hafta hiç görülmeden.
    Kırpılmış bir tarihçe ile tam bir tarihçe, katalog tarafından bakıldığında
    TIPATIP AYNI görünür; farkı yalnız veriye sorarak görebilirsiniz.

    KURAL (sınıf kusur): BİR HÜKÜM, ELDE OLAN VERİDEN KURULUR. Kataloğu sorup
    veriyi sormayan bir kapı, kapatmak için konduğu kusurun kendisine döner.
    """
    return tuple(a for a in HAFTALIK
                 if bas_olculdu(a) and bas_cerceveye_ulasti(H, a))


# Okur adında parantez içi TP kodu bilinçlidir: okurun EVDS'te arayabileceği
# bir künyedir ve yayın kapısı onu (BÜYÜK harfli kaynak kodu) muaf tutar.
# Sütun adı ("stok_gercek") ise okura HİÇBİR şey söylemez ve okur dili
# ölçütünde "anahtar adı" bulgusu üretir — bir başka hatta tam bu yüzden
# tırnak içinde sütun adı basan bir tazelik uyarısı vardı.
HAFTALIK: dict[str, Seri] = {
    # ---- bie_hpbitablo2 · STOK · MİLYON USD · yalnız YURT İÇİ yerleşikler ----
    "stok_toplam": Seri(
        "TP.HPBITABLO2.10", "2024-06-28", "mn USD",
        "Yurt içi yerleşiklerin toplam YP mevduatı (TP.HPBITABLO2.10)",
        bas_kanit=KESIF_ALT_SINIR),
    "stok_gercek": Seri(
        "TP.HPBITABLO2.11", "2024-06-28", "mn USD",
        "Gerçek kişilerin YP mevduatı (TP.HPBITABLO2.11)"),
    "stok_tuzel": Seri(
        "TP.HPBITABLO2.12", "2024-06-28", "mn USD",
        "Tüzel kişilerin YP mevduatı (TP.HPBITABLO2.12)"),
    # ---- bie_hpbitablo2 · TL KARŞILIKLARI · BİN TL ----
    # Dolarizasyon payının bacakları BURADAN gelir ve İKİSİ DE bin TL'dir;
    # milyon dolar cinsindeki stok serisiyle aynı orana sokulamaz.
    # TP.HPBITABLO2.1 (toplam mevduat) BİLEREK ÇEKİLMİYOR — künyesi aşağıda.
    "mevduat_yi": Seri(
        "TP.HPBITABLO2.2", "2024-06-28", "bin TL",
        "Yurt içi yerleşiklerin mevduatı, TL karşılığı (TP.HPBITABLO2.2)"),
    "mevduat_tl": Seri(
        "TP.HPBITABLO2.3", "2024-06-28", "bin TL",
        "Türk lirası mevduat (TP.HPBITABLO2.3)"),
    "mevduat_yp_tl": Seri(
        "TP.HPBITABLO2.6", "2024-06-28", "bin TL",
        "YP mevduatın TL karşılığı (TP.HPBITABLO2.6)"),
    # ---- bie_hpbitablo4 · STOK KIRILIMI · MİLYON USD ----
    # DİKKAT: genis_toplam YURT DIŞI yerleşikleri de içerir; manşet DEĞİLDİR.
    "genis_toplam": Seri(
        "TP.HPBITABLO4.1", "2024-06-28", "mn USD",
        "Toplam YP mevduat, yurt dışı yerleşikler dahil (TP.HPBITABLO4.1)",
        bas_kanit=KESIF_ALT_SINIR),
    "k_gercek": Seri(
        "TP.HPBITABLO4.3", "2024-06-28", "mn USD",
        "Gerçek kişiler, kırılım tablosu (TP.HPBITABLO4.3)"),
    "maden_gercek": Seri(
        "TP.HPBITABLO4.7", "2024-06-28", "mn USD",
        "Gerçek kişilerin kıymetli maden depo hesapları (TP.HPBITABLO4.7)"),
    "k_tuzel": Seri(
        "TP.HPBITABLO4.8", "2024-06-28", "mn USD",
        "Tüzel kişiler, kırılım tablosu (TP.HPBITABLO4.8)"),
    "maden_tuzel": Seri(
        "TP.HPBITABLO4.12", "2024-06-28", "mn USD",
        "Tüzel kişilerin kıymetli maden depo hesapları (TP.HPBITABLO4.12)"),
    # 4.20 kırılım tablosunun 1.3 başlığı altında duruyor ve o başlığın NE
    # olduğu ölçülmedi. "Yurt dışı yerleşik" saymak bir VARSAYIM olurdu —
    # 1.4 ölçülmüş biçimde yurt dışı yerleşik bankalardır, 1.3 değil. Bu yüzden
    # seri tarafsız adla taşınır ve başlık ölçülmeden sayfaya çıkmaz.
    # NEDEN YİNE DE ÇEKİLİYOR: iki toplam arasındaki kapsam farkının İÇİNDEN
    # ölçülmüş tek kalem budur (3.263,5 milyon dolar, farkın yaklaşık yüzde
    # sekizi) ve farkın tamamını "yurt dışı bacak" saymanın neden yanlış
    # olduğunu ölçüyle gösteren şey odur. Yayımlanan bir değeri beslemediği
    # için tazelik ve sıfır denetimlerinin dışında (bkz. DENETIM_DISI);
    # 1.3 başlığı ölçüldüğü gün sayfaya çıkabilir.
    "maden_diger": Seri(
        "TP.HPBITABLO4.20", "2024-06-28", "mn USD",
        "Kıymetli maden depo hesapları, diğer bölüm (TP.HPBITABLO4.20)"),
    # ---- bie_hpbitablo5 · RESMÎ AYRIŞTIRMA · HAFTALIK DEĞİŞİM · MİLYON USD ----
    #
    # BAŞLANGIÇ: 28.02.2014 — ÖLÇÜLDÜ, yazılmadı. Bu ailenin başlangıcı bir
    # süre 05.01.2024 diye durdu ve o tarih bir ölçüm DEĞİLDİ: ilk keşif koşusu
    # 01.01.2024'ten sormuştu ve 05.01.2024 ondan sonraki ilk cumadır — yani
    # sorgunun kendi alt sınırının izi. Yirmi iki serinin HEPSİNİN aynı güne
    # yapışması kırpılmış bir tarihçenin imzasıydı; 2005'ten sorulduğunda
    # tablonun 28.02.2014'te başladığı ve 653 hafta taşıdığı görüldü — beş kat.
    #
    # KANIT ALANI ONU TAŞIYAN SERİDE DURUR. Aile başına tek bir not yazılsaydı
    # kanıt seriden seriye devredilirdi; oysa ölçülen şey SERİNİN kendi
    # cevabıdır. Bu ailede on seri doğrudan soruldu (1 · 2 · 3 · 6 · 13 · 14 ·
    # 15 · 16 · 17 · 21) ve onu da aynı güne cevap verdi. Kalan on ikisi için
    # "aynı tablo, aynı yayım" makul bir ÇIKARIMDIR ama ölçüm değildir ve bu
    # hattın bütün kusuru tam olarak bir çıkarımı ölçüm saymaktan doğdu; kanıt
    # alanları boş kalır, hüküm kapısı onları eler ve keşif koşusu bir sonraki
    # ağ turunda kapatır.
    #
    # 1. Parite etkisinden ARINDIRILMIŞ değişim (yurt içi yerleşikler)
    "ar_toplam": Seri(
        "TP.HPBITABLO5.1", "2014-02-28", "mn USD",
        "Arındırılmış değişim, toplam (TP.HPBITABLO5.1)",
        bas_kanit=KESIF_ALT_SINIR),
    "ar_gercek": Seri(
        "TP.HPBITABLO5.2", "2014-02-28", "mn USD",
        "Arındırılmış değişim, gerçek kişiler (TP.HPBITABLO5.2)",
        bas_kanit=KESIF_ALT_SINIR),
    "ar_gercek_usd": Seri(
        "TP.HPBITABLO5.3", "2014-02-28", "mn USD",
        "Arındırılmış değişim, gerçek kişiler, dolar (TP.HPBITABLO5.3)",
        bas_kanit=KESIF_ALT_SINIR),
    "ar_gercek_eur": Seri(
        "TP.HPBITABLO5.4", "2014-02-28", "mn USD",
        "Arındırılmış değişim, gerçek kişiler, euro (TP.HPBITABLO5.4)"),
    "ar_gercek_diger": Seri(
        "TP.HPBITABLO5.5", "2014-02-28", "mn USD",
        "Arındırılmış değişim, gerçek kişiler, diğer para birimleri (TP.HPBITABLO5.5)"),
    "ar_gercek_maden": Seri(
        "TP.HPBITABLO5.6", "2014-02-28", "mn USD",
        "Arındırılmış değişim, gerçek kişiler, kıymetli maden (TP.HPBITABLO5.6)",
        bas_kanit=KESIF_ALT_SINIR),
    "ar_tuzel": Seri(
        "TP.HPBITABLO5.7", "2014-02-28", "mn USD",
        "Arındırılmış değişim, tüzel kişiler (TP.HPBITABLO5.7)"),
    "ar_tuzel_usd": Seri(
        "TP.HPBITABLO5.8", "2014-02-28", "mn USD",
        "Arındırılmış değişim, tüzel kişiler, dolar (TP.HPBITABLO5.8)"),
    "ar_tuzel_eur": Seri(
        "TP.HPBITABLO5.9", "2014-02-28", "mn USD",
        "Arındırılmış değişim, tüzel kişiler, euro (TP.HPBITABLO5.9)"),
    "ar_tuzel_diger": Seri(
        "TP.HPBITABLO5.10", "2014-02-28", "mn USD",
        "Arındırılmış değişim, tüzel kişiler, diğer para birimleri (TP.HPBITABLO5.10)"),
    "ar_tuzel_maden": Seri(
        "TP.HPBITABLO5.11", "2014-02-28", "mn USD",
        "Arındırılmış değişim, tüzel kişiler, kıymetli maden (TP.HPBITABLO5.11)"),
    # 2. PARİTE ETKİSİ (yurt içi yerleşikler)
    "pe_toplam": Seri(
        "TP.HPBITABLO5.12", "2014-02-28", "mn USD",
        "Parite etkisi, toplam (TP.HPBITABLO5.12)"),
    "pe_gercek": Seri(
        "TP.HPBITABLO5.13", "2014-02-28", "mn USD",
        "Parite etkisi, gerçek kişiler (TP.HPBITABLO5.13)",
        bas_kanit=KESIF_ALT_SINIR),
    "pe_gercek_usd": Seri(
        "TP.HPBITABLO5.14", "2014-02-28", "mn USD",
        "Parite etkisi, gerçek kişiler, dolar (TP.HPBITABLO5.14)",
        bas_kanit=KESIF_ALT_SINIR),
    "pe_gercek_eur": Seri(
        "TP.HPBITABLO5.15", "2014-02-28", "mn USD",
        "Parite etkisi, gerçek kişiler, euro (TP.HPBITABLO5.15)",
        bas_kanit=KESIF_ALT_SINIR),
    "pe_gercek_diger": Seri(
        "TP.HPBITABLO5.16", "2014-02-28", "mn USD",
        "Parite etkisi, gerçek kişiler, diğer para birimleri (TP.HPBITABLO5.16)",
        bas_kanit=KESIF_ALT_SINIR),
    "pe_gercek_maden": Seri(
        "TP.HPBITABLO5.17", "2014-02-28", "mn USD",
        "Parite etkisi, gerçek kişiler, kıymetli maden (TP.HPBITABLO5.17)",
        bas_kanit=KESIF_ALT_SINIR),
    "pe_tuzel": Seri(
        "TP.HPBITABLO5.18", "2014-02-28", "mn USD",
        "Parite etkisi, tüzel kişiler (TP.HPBITABLO5.18)"),
    "pe_tuzel_usd": Seri(
        "TP.HPBITABLO5.19", "2014-02-28", "mn USD",
        "Parite etkisi, tüzel kişiler, dolar (TP.HPBITABLO5.19)"),
    "pe_tuzel_eur": Seri(
        "TP.HPBITABLO5.20", "2014-02-28", "mn USD",
        "Parite etkisi, tüzel kişiler, euro (TP.HPBITABLO5.20)"),
    "pe_tuzel_diger": Seri(
        "TP.HPBITABLO5.21", "2014-02-28", "mn USD",
        "Parite etkisi, tüzel kişiler, diğer para birimleri (TP.HPBITABLO5.21)",
        bas_kanit=KESIF_ALT_SINIR),
    "pe_tuzel_maden": Seri(
        "TP.HPBITABLO5.22", "2014-02-28", "mn USD",
        "Parite etkisi, tüzel kişiler, kıymetli maden (TP.HPBITABLO5.22)"),
}

# SEPET BİLEŞİMİ — BİLEREK ÇEKİLMİYOR, künye kayıt için burada duruyor.
#
# Üç ayrı sebep ve üçü de bağımsız:
#   (i)   BİR HAFTA GERİDE bitiyor (ölçüldü: 21-08-2026, ötekiler 28-08-2026).
#         Çekirdeğe alınsaydı hattın saati her hafta bir hafta geriye düşerdi.
#   (ii)  AYRI POPÜLASYON: bu tablo "zorunlu karşılığa tabi döviz tevdiat
#         hesapları"dır, hpbitablo2 ise "yurt içi yerleşiklerin YP mevduatı".
#         İkisini aynı toplam saymak, geniş/dar toplam hatasının bir başka
#         biçimidir.
#   (iii) BİRİMİ ÖLÇÜLMEDİ — ve hangi kalemin ölçüldüğü de künyeye göre
#         yazılır, hatırlanarak değil. Künyede DEĞER taşıyan dört kalem
#         KB3–KB6'dır: kıymetli maden 85.507,5 · diğer 8.824,6 · bir aya kadar
#         vadeli 175.179,0 · bir aydan uzun 52.617,1. KB1 ve KB2 (dolar ve euro
#         bacakları) için ölçülmüş DEĞER YOK. Ölçülen dördü yüzde değil SEVİYE
#         gibi duruyor; bir kardeş hat aynı grubu "pay" adıyla taşıdığı için
#         ad sözleşmesi ile ölçüm çelişiyor ve çelişki çözülmeden bir seri
#         grafiğe giremez. Yanlış eşleştirilmiş bir not, bir sonraki oturumu
#         "KB1 bir seviyedir" sanarak yola çıkarır — tam olarak önlemek için
#         var olduğu şeyi yapar.
#
# Kural: bu kodlar ancak birimleri ÖLÇÜLDÜKTEN sonra kataloğa taşınır —
# "paylar toplamı 100'e mi yakın, seviyeler toplamı DTH'a mı" sorusu bir
# koşuyla cevaplanır. O güne kadar hiçbir yerden okunmuyorlar; bu liste
# yalnız bir sonraki oturumun kodları yeniden TAHMİN etmesini önlemek için
# duruyor ("bulamadım" ile "yok" aynı şey değildir).
#
# KOD YAZIMI TÜRETİLMİŞTİR, ÖLÇÜLMÜŞ DEĞİL: künye grup adını (küçük harfli
# tablo kodu) ve KB1–KB6 eklerini kaydediyor, aşağıdaki tam kod yazımı ise
# kardeş hatların kalıbından türetildi. Kullanılacağı gün bir keşif koşusuyla
# DOĞRULANIR — "bulamadım" ile "yok" aynı şey değildir ve tahmin edilmiş bir
# kod uzayı, boş dönünce "bu seri yok" diye okunur.
SEPET_KUNYE = {
    "TP.ZORUNDTH.KB1": "USD bacağı (değeri ölçülmedi)",
    "TP.ZORUNDTH.KB2": "EUR bacağı (değeri ölçülmedi)",
    "TP.ZORUNDTH.KB3": "kıymetli maden bacağı (85.507,5)",
    "TP.ZORUNDTH.KB4": "diğer para birimleri bacağı (8.824,6)",
    "TP.ZORUNDTH.KB5": "1 aya kadar vadeli (175.179,0)",
    "TP.ZORUNDTH.KB6": "1 aydan uzun vadeli (52.617,1)",
}

# ÇEKİLMEYEN KÜNYE — toplam mevduat.
# TP.HPBITABLO2.1 kataloğa alınmıştı ve HİÇBİR TÜKETİCİSİ YOKTU: her koşuda
# indiriliyor, önbelleğe yazılıyor, kapsam kaydında yer kaplıyordu; bir gün
# donsaydı okur sayfada hiç görmediği bir seri için uyarı okuyacaktı. Daha
# tehlikelisi tersi: "çekiliyorsa kullanılıyordur" sanan bir sonraki oturum onu
# dolarizasyon payının paydasına koyabilirdi — oysa 2.1 yurt dışı yerleşikleri
# de içerir ve payın paydası 2.2'dir (yurt içi yerleşikler). Ölü bir bağımlılık
# kırık olandan tehlikelidir: dosya vardır, okunur, hata vermez, yalnızca
# yaşlanır. Kod burada duruyor ki bir sonraki oturum onu yeniden TAHMİN etmesin.
CEKILMEYEN_KUNYE = {
    "TP.HPBITABLO2.1": "Toplam mevduat, TL karşılığı — yurt dışı yerleşikler dahil",
}

# ÇEKİRDEK — hattın saatini belirleyen seriler.
# Seçim BİR KARARDIR: sayfanın merkezî iddiası KİMLİĞİN kendisidir
# (Δ stok = arındırılmış değişim + parite etkisi), öyleyse hattın çıpası
# kimliğin HESAPLANABİLDİĞİ son haftadır. Bir hafta geriden gelen hiçbir
# bacak (sepet bileşimi) çekirdeğe alınmaz — alınsaydı hattın saati her
# hafta bir hafta geriye düşerdi.
CEKIRDEK = ("stok_gercek", "stok_tuzel", "ar_gercek", "ar_tuzel",
            "pe_gercek", "pe_tuzel")

# BAŞLANGICI KATALOGDA ÖLÇÜLMÜŞ SERİLER — KÜNYENİN SAYIMI, HÜKÜM KAPISI DEĞİL.
#
# Liste elle tutulmuyor, künyeden TÜRETİLİYOR; elle tutulan bir "bunlar
# ölçüldü" listesi kataloğun kendisinden ayrışabilir ve o gün ikisi de doğru
# görünür. Kapsam sözleşmenin kendisinden gelir: ölçülmüş başlangıç =
# kanıt alanı `bas`tan yayım ritmi kadar önce duran seri.
#
# BU SABİT BİR HÜKÜM KAPISI DEĞİLDİR VE ÖYLE KULLANILMAZ. Modül düzeyinde
# durduğu için elinde ÇERÇEVE YOKTUR: kataloğun ne dediğini bilir, o koşuda
# gerçekten ne çekildiğini bilemez. Hüküm kapısı `bas_olculen(H)`dir ve
# ikisini birden sorar; ayrımın gerekçesi o fonksiyonda yazılı. Buradaki
# sayım yalnız KÜNYEYE basılır ("kaç serinin başlangıcı ölçülmüş"), yani
# kataloğun kendi hakkındaki ifadesidir ve öyle adlandırılmıştır.
BAS_OLCULEN = tuple(a for a in HAFTALIK if bas_olculdu(a))

# Kapsam kapısı: çekirdeğin TAM olduğu hafta sayısı bunun altına düşerse
# çıktı ÜRETİLMEZ. Bu bir analiz penceresi eşiği DEĞİL, KIRPMA/ÇÖKME
# dedektörüdür: kaynağın yayımladığı tarihçe ölçüldü (stok tabloları 114,
# değişim tablosu 653 hafta), yarım yılın altına düşen bir çekirdek yarım
# kalmış bir çekimdir. Eşik ORTAK pencereye bakar (çekirdek hem stok hem
# değişim bacağı taşıyor), yani tarihçe asimetrisi onu 114'ün üstüne
# çıkarmaz — ve çıkarmamalı: kapı kırpmayı arıyor, uzunluğu değil.
# Her ölçümün kendi pencere yeterliliği ölçüm katmanının işidir.
ASGARI_HAFTA = 26

# Tazelik: bu hatta TEK yayım ritmi var (Haftalık Para ve Banka İstatistikleri,
# Perşembe yayımı, Cuma damgalı, 6 gün gecikme). Tolerans bir yayım aralığı
# artı bir tatil payıdır ve ARALIK ELLE YAZILMAZ: ritim tek yerde tanımlı
# (AILE_RITIM_GUN) ve tazelik toleransı da kapsam toleransı da oradan türüyor.
# Tek eşik ancak ritim gerçekten tekse doğrudur; sepet bileşimi eklenirse
# KENDİ ritmiyle eklenmelidir.
TATIL_PAYI_GUN = 5
AILE_TOLERANS = {a: r + TATIL_PAYI_GUN for a, r in AILE_RITIM_GUN.items()}

# TAZELİK KAPSAMI BİR LİSTEDEN DEĞİL SÖZLEŞMEDEN TÜRER. Elle tutulan bir
# "bakılacaklar" listesi otuz beş serinin onunu kapsıyordu ve kalan yirmi beşi
# donduğunda hiçbir cümle kurulmuyordu: ölçüm katmanı sütunu bulamayınca ilgili
# anahtarı atlıyor, sayfa o anahtarın yerine MDX'teki statik yedeği gösteriyor
# ve tazelik satırı "bütün bacaklar tolerans içinde" diyordu — donmuş bir sayı,
# taze damgasının altında. Bakılmayan yer geçen sınavla aynı görünür. Kapsam bu
# yüzden kataloğun KENDİSİ: özete değer besleyen her seri denetime girer.
#
# Tek istisna GEREKÇELİDİR ve adıyla duruyor: `maden_diger` hiçbir yayımlanan
# değeri beslemiyor (aşağıdaki not), yani donması okurun gördüğü hiçbir sayıyı
# etkilemez; onun için uyarı basmak okura görmediği bir seriyi anlatmak olurdu.
#
# İSTİSNA TEK ADLA DURUYOR ÇÜNKÜ TEK GEREKÇESİ VAR: "okurun gördüğü hiçbir
# sayıyı beslemiyor". O gerekçe tazeliğe olduğu kadar sıfır denetimine de
# aynen uyar — iki denetim iki ayrı istisna listesi tutsaydı bir gün sessizce
# ayrışır ve hangisinin neyi görmediği kimsenin aklında kalmazdı. Ad bu yüzden
# ailenin değil GEREKÇENİN adıdır.
DENETIM_DISI = ("maden_diger",)
TAZELIK_SERI = {
    "haftalik": tuple(a for a in HAFTALIK if a not in DENETIM_DISI),
}

# SIFIR BLOĞU EŞİĞİ — TEK TANIM. Ölçüm katmanı bu sabiti içe aktarır
# (`metrik.ESIK_SIFIR_BLOK`). İki yerde ayrı yazılıydı (52 ve 26) ve aynı dört
# seri için okura iki farklı hafta sayısı basılıyordu; bir gün biri güncellenip
# öteki unutulurdu. Yarım yıl, "bir hafta sıfır çıktı" ile "bu bacak artık
# yayımlanmıyor" arasını ayırmaya yeten en kısa penceredir.
SIFIR_BLOK_HAFTA = 26

# SIFIR DENETİMİNİN KAPSAMI — ELLE TUTULAN LİSTEDEN DEĞİL, KATALOĞUN KENDİSİ.
#
# Burada on bir seri adı elle yazılıydı ("ölü seri adayları") ve o listede
# dolar bacakları YOKTU. Gerçek veriyle ölçüldüğünde dört bacak serinin
# tamamında tam sıfır çıktı — `pe_*_diger` ve `pe_*_usd` — ama denetim yalnız
# ikisini gördü, çünkü öteki ikisi listede değildi. Bakılmayan yer geçen
# sınavla aynı görünür: kapsam hiç uyarı üretmediği için hiç sorgulanmadı.
#
# Doğru kapsam bir yargıdan ("hangi seri sıfır OLABİLİR") değil sözleşmeden
# türer: özete değer besleyen HER seri. Hangi sıfırın ölçüm, hangisinin
# ölçümün yokluğu olduğu sorusu kapsamda değil SINIFLANDIRMADA cevaplanır
# (bkz. `metrik.sifir_olc` beş hâli) — orada cevap veriden gelir, listeden
# değil. Kapsamı dar tutmanın hiçbir kazancı yok: sıfır olmayan bir seri
# zaten hiçbir cümle üretmez.
SIFIR_KAPSAMI = tuple(a for a in HAFTALIK if a not in DENETIM_DISI)

# KIRILIM SÖZLEŞMESİ — üst kalem ↔ onu oluşturan bacaklar, TEK TANIM.
#
# İki tüketicisi var ve ikisi de aynı ağacı soruyor: kaynak kimliği denetimi
# ("bacakların toplamı üst kaleme eşit mi") ve sıfır denetiminin dayanaksız
# sıfır cümlesi ("bu bacak hep sıfırsa, aynı kırılımın ÖTEKİ bacakları ne
# yapıyor" — ve aynı kesenin arındırılmış akımı ne yapıyor).
# Ağaç iki yerde ayrı yazılsaydı bir gün sessizce ayrışırdı.
#
# Kalem numaraları burada YAZILMIYOR, katalogdan türetiliyor (`kirilim_adi`):
# okur adının içine elle yazılmış bir kod aralığı, katalog değiştiği gün
# yalan söylemeye başlar ve hiçbir denetim bunu görmez.
class Kirilim(NamedTuple):
    ust: str
    parcalar: tuple[str, ...]
    etiket: str        # okura basılacak kırılım adı (kod aralığı EKLENİR)


KIRILIMLAR: tuple[Kirilim, ...] = (
    Kirilim("ar_gercek",
            ("ar_gercek_usd", "ar_gercek_eur", "ar_gercek_diger",
             "ar_gercek_maden"),
            "Gerçek kişilerin arındırılmış değişiminde para birimi kırılımı"),
    Kirilim("ar_tuzel",
            ("ar_tuzel_usd", "ar_tuzel_eur", "ar_tuzel_diger",
             "ar_tuzel_maden"),
            "Tüzel kişilerin arındırılmış değişiminde para birimi kırılımı"),
    Kirilim("pe_gercek",
            ("pe_gercek_usd", "pe_gercek_eur", "pe_gercek_diger",
             "pe_gercek_maden"),
            "Gerçek kişilerin parite etkisinde para birimi kırılımı"),
    Kirilim("pe_tuzel",
            ("pe_tuzel_usd", "pe_tuzel_eur", "pe_tuzel_diger",
             "pe_tuzel_maden"),
            "Tüzel kişilerin parite etkisinde para birimi kırılımı"),
    Kirilim("ar_toplam", ("ar_gercek", "ar_tuzel"),
            "Arındırılmış değişimde gerçek ve tüzel kişi"),
    Kirilim("pe_toplam", ("pe_gercek", "pe_tuzel"),
            "Parite etkisinde gerçek ve tüzel kişi"),
)

# TANIM GEREĞİ SIFIR — sıfırın ÖLÇÜMDEN ÖNCE bilindiği bacaklar, gerekçesiyle.
#
# Bu bir KAPSAM listesi DEĞİLDİR ve öyle olmadığı için elle tutulabilir:
# denetimin neye baktığını belirlemiyor (kapsam kataloğun kendisi), yalnızca
# ölçülen bir sıfırı TANIM sınıfına taşıyor ve gerekçesini yazıyor; buraya
# yazılmayan bir bacağın sıfırı dayanaksız sayılır. Bir gün yeni bir bacak
# eklenip buraya yazılmazsa kaybedilen şey bir açıklama cümlesidir, bir kör
# nokta değil — kusurun bedeli sınırlı olduğu için liste elle tutulabilir.
#
# Gerekçe ilk ilkelerden: dolar cinsi bir mevduatın DOLAR olarak ölçülen
# parite etkisi olamaz, çünkü ortada çapraz kur yoktur. Bu, kaynağın yöntem
# belgesinden okunmuş bir iddia değil aritmetiktir; "kaynak şöyle hesaplıyor"
# cümlesi kurulmaz, kurulamaz da — yöntem belgesi okunmadı.
TANIM_SIFIRI: dict[str, str] = {
    "pe_gercek_usd": "dolar cinsi bir mevduatın dolar olarak ölçülen parite "
                     "etkisi olamaz, çünkü ortada çapraz kur yoktur",
    "pe_tuzel_usd": "dolar cinsi bir mevduatın dolar olarak ölçülen parite "
                    "etkisi olamaz, çünkü ortada çapraz kur yoktur",
}

# PARİTE ETKİSİ ↔ ARINDIRILMIŞ AKIM EŞİ — TEK TANIM, AĞAÇTAN TÜRETİLİYOR.
#
# NEDEN VAR. Bir bacağın parite etkisi hiç yayımlanmıyorsa, AYNI KESENİN
# arındırılmış akımı da parite etkisinden arındırılmamış olabilir — ve o akım
# manşetin içindedir. Sınırın büyüklüğünü yazabilmek için "bu parite bacağının
# arındırılmış eşi hangisi" sorusunun tek bir cevabı olmalı.
#
# EŞLEME ADDAN DEĞİL AĞAÇTAN ÇIKIYOR. "pe_" önekini "ar_" ile değiştiren bir
# dize ameliyatı bugün doğru sonucu verirdi ve yarın bir ad değiştiğinde
# sessizce yanlış bacağı eşlerdi. Burada eşleme KIRILIMLAR sözleşmesindeki
# konumdan geliyor: iki üst kalemin bacak listeleri aynı sırada aynı para
# birimlerini taşıyor. Sıralar bir gün ayrışırsa eşleme None döner ve o cümle
# HİÇ KURULMAZ — yanlış bir eş, hiç eş olmamasından kötüdür.
AYRISTIRMA_ESI: tuple[tuple[str, str], ...] = (
    ("pe_gercek", "ar_gercek"),
    ("pe_tuzel", "ar_tuzel"),
)


def arindirilmis_esi(ad: str) -> str | None:
    """Bir parite etkisi bacağının AYNI KESEDEKİ arındırılmış akım bacağı."""
    for pe_ust, ar_ust in AYRISTIRMA_ESI:
        pe = next((k for k in KIRILIMLAR if k.ust == pe_ust), None)
        ar = next((k for k in KIRILIMLAR if k.ust == ar_ust), None)
        if pe is None or ar is None or len(pe.parcalar) != len(ar.parcalar):
            continue
        if ad in pe.parcalar:
            return ar.parcalar[pe.parcalar.index(ad)]
    return None


# ÖLÇÜM BLOKLARININ OKUR ADLARI — TEK TANIM.
# İki modül aynı kutuya yazıyor (ölçüm katmanının ortak hafta uyarısı ve özet
# üreticisinin bayatlık cümlesi) ve iki AYRI ad tablosu tutuluyordu: biri
# "akım" diyordu, öteki "resmî ayrıştırma tablosu". Okur aynı kutuda aynı şeyin
# iki adını görüyor ve ikisinin aynı şey olduğunu bilemiyordu. Üstelik ilk
# tablodaki üç ad hattın KENDİ İÇ ANAHTARIYDI ("stok", "akım", "kimlik") —
# okurun elinde o anahtarların karşılığı yok.
BLOK_OKUR = {
    "stok": "stok tabloları",
    "akim": "resmî ayrıştırma tablosu",
    "kimlik": "stok ile ayrıştırmanın kıyası",
    "dol": "mevduatın lira karşılığı",
}


def blok_okur(ad: str) -> str:
    """Bir ölçüm bloğunun OKUR adı. Bilinmeyen bloğun iç anahtarı BASILMAZ.

    Ham anahtar yedeği bilerek yok: yedek olsaydı yarın eklenen bir blok
    sessizce kendi kod adıyla okura giderdi ve hiçbir denetim bunu görmezdi.
    """
    return BLOK_OKUR.get(ad, "bir ölçüm ailesi")


AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
         7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım",
         12: "Aralık"}
AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
           7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}

# Şekil dosyaları: ad = çıktı dosyası = kopya hedefi = saat defteri anahtarı.
# Üçü AYNI dizedir; ad ay/tarih taşımaz (bir ay sonra yalan söyleyen adres).
SEKIL_DOSYALARI = (
    "01_stok_kirilim.html",
    "02_kumule_akim.html",
    "03_ayristirma.html",
    "04_para_cinsi.html",
    "05_kimlik.html",
    "06_dolarizasyon.html",
)


def okur_adi(ad: str) -> str:
    """Bir sütunun OKUR adı. Katalogda yoksa kodun kendisi döner — sütun adı
    ASLA okura basılmaz."""
    s = HAFTALIK.get(ad)
    return s.okur_adi if s is not None else ad.upper()


def birim(ad: str) -> str:
    """Bir sütunun birimi ("mn USD" | "bin TL"). Ölçüm katmanı dönüşümü
    buradan okur; birim ikinci bir yerde yazılmaz."""
    s = HAFTALIK.get(ad)
    return s.birim if s is not None else ""


# BİRİMİN OKUR YAZIMI — TEK TANIM. Katalogdaki "mn USD" bir künye kısaltması;
# okura giden cümlede birim açık yazılır ("milyon dolar"), çünkü okurun elinde
# bizim kısaltma sözleşmemiz yok. Kapsam kimliğinin uyarısı bunu zaten açık
# yazıyordu, kırılım kimliğininki katalog kısaltmasını basıyordu — aynı kutuda
# aynı birimin iki yazımı.
BIRIM_OKUR = {"mn USD": "milyon dolar", "bin TL": "bin lira"}


def birim_okur(birim_ad: str) -> str:
    """Bir birimin okur yazımı. Bilinmeyen birim OLDUĞU GİBİ döner — uydurma
    bir çeviri, yanlış birimle yayımlanmış bir sayıdan farksız olurdu."""
    return BIRIM_OKUR.get(birim_ad, birim_ad)


def bacak_kisa_adi(ad: str) -> str:
    """Bir kırılım bacağının KISA okur adı: "euro", "kıymetli maden", "dolar".

    Okur adının son virgülden sonraki parçası alınır ve kaynak kodu atılır.
    Kısa adlar AYRI bir sözlükte tutulsaydı katalogla bir gün ayrışırdı —
    burada tek kaynak yine `Seri.okur_adi`dır.
    """
    tam = okur_adi(ad).split(" (")[0]
    return tam.rsplit(", ", 1)[-1].strip()


def kirilim_adi(k: "Kirilim") -> str:
    """Bir kırılımın okur adı, KOD ARALIĞI KATALOGDAN TÜRETİLEREK.

    Kod aralığı ("TP.HPBITABLO5.3–5.6 = TP.HPBITABLO5.2") daha önce her
    kimliğin adına ELLE yazılıydı. Elle yazılmış bir kod, katalog değiştiği
    gün yalan söylemeye başlar ve hiçbir denetim bunu göremez: okur adı
    yalnızca okunur, sınanmaz. Şimdi tek kaynak katalog.

    İki yazım var ve seçim parça sayısından türüyor: ikiden çok bacakta
    aralık, iki bacakta toplama. Sebep okunurluk — dört kalemi tek tek yazmak
    adı okunmaz uzunluğa çıkarır, iki kalemi aralık diye yazmak ise aradaki
    kalemleri de kapsıyormuş gibi görünür.

    Aralığın İKİ UCU DA TAM KOD yazılır. Kısaltılmış bir uç ("5.3–6") okurun
    kaynakta arayabileceği bir künye değildir ve kısaltmanın nereden kesileceği
    kaynağın kod yazımına bağlıdır — bir gün başka bir tablo eklendiğinde
    sessizce yanlış yere keser.
    """
    kodlar = [HAFTALIK[a].kod for a in k.parcalar if a in HAFTALIK]
    ust_kod = HAFTALIK[k.ust].kod if k.ust in HAFTALIK else k.ust
    if not kodlar:
        return k.etiket
    sol = f"{kodlar[0]}–{kodlar[-1]}" if len(kodlar) > 2 else " + ".join(kodlar)
    return f"{k.etiket} toplamı ({sol} = {ust_kod})"


# YAYIM ADIMININ ÖLÇÜLEBİLİRLİK KOŞULLARI — iki ayrı sabit, iki ayrı gerekçe.
#
# (a) IZGARA ARALIĞI. Üs döngüsü sıfırdan başlıyordu, yani ölçülebilen en KABA
# ızgara 1,0 idi; üstüne bir de `tavan=1.0` konmuştu. İkisi birlikte "kaynak
# hassasiyetini kabalaştırırsa taban kendiliğinden kayar" sigortasını YAPISAL
# OLARAK ATIL bırakıyordu: kaynak yarın on milyon dolarlık yuvarlamaya geçse
# ölçülen adım yine 1,0 çıkar, taban on kat dar kalır ve iki tablonun MEŞRU
# yuvarlama farkı "KİMLİK BOZUK" diye yayımlanırdı — yayının önünde duran bir
# denetimin yanlış alarmı arızanın kendisidir. Aralık artık kaba tarafa da üç
# basamak açık ve tavan yok.
ADIM_US_KABA = -3
ADIM_US_INCE = 6

# (b) ÖRNEKLEM. Kaba tarafı açmak tek başına YENİ bir kusur üretir ve o kusur
# bugünkü veride ölçüldü: baştan sona sıfır olan dört seri tek bir değer
# taşıyor ve tek bir değer HER ızgaranın üstünde durur. Eski sürüm onlara 1,0
# (tavanın kendisi), tavansız sürüm 1.000,0 diyordu; ikisi de ölçüm değil
# TESADÜF — üstelik tavan bu tesadüfü ölçüm gibi gösteriyordu.
#
# Ayıran şey BENZERSİZ gözlem sayısıdır ve eşik aritmetikten gelir: gerçek
# ızgara bir basamak daha ince olsaydı, N benzersiz değerin hepsinin kaba
# ızgaraya düşme olasılığı 10⁻ᴺ olurdu. Altı benzersiz değer bunu milyonda
# bire indirir; altısının altında ölçüm YAPILMAZ ve sebebi adıyla döner.
# Bugünkü veride eşik yalnız o dört sıfır seriyi eliyor: kalan otuz serinin
# benzersiz gözlem sayısı 114 ile 139 arasında.
ADIM_ASGARI_BENZERSIZ = 6


def yayim_adimi_olc(s: pd.Series) -> tuple[float, str]:
    """Bir serinin YAYIM ADIMI ve ölçümün HÂLİ — kaynağın hangi ızgarada
    yayımladığı, ve ölçülemediyse NEDEN ölçülemediği.

    ÖLÇÜLÜR, VARSAYILMAZ. Bu hatta iki tablo iki ayrı hassasiyet taşıyor ve
    ikisi gerçek veriden ölçüldü: stok tabloları bir ondalıkla (adım 0,1
    milyon dolar), kırılım tablosu üç ondalıkla (adım 0,001) yayımlanıyor.
    Sabit bir taban yazılsaydı kaynak hassasiyetini değiştirdiği gün ya yanlış
    alarm ya da sessizce körelmiş bir kapı kalırdı.

    Ölçü, bütün gözlemlerin üzerinde durduğu en KABA ondalık ızgaradır:
    değerlerin hepsi 0,1'in katıysa adım 0,1'dir.

    NEDEN ONDALIK BASAMAK SAYMIYORUZ. İlk sürüm `repr` üzerinden basamak
    sayıyordu ve TOPLAM serilerde çöktü: 100.476,8 + 62.668,4 kayan noktada
    163.145,19999999998 eder, on dört basamak görünür ve ölçü "ızgara yok"
    der. Oysa iki tanesi de 0,1 ızgarasında olan sayıların toplamı da 0,1
    ızgarasındadır — üstelik kimlik denetiminin bir tarafı tam olarak böyle
    bir toplamdır, yani ölçü en çok ihtiyaç duyulan yerde susardı. Doğrusu
    bölünebilirliği kayan nokta payıyla SORMAK: pay büyüklükle birlikte büyür
    (v/g ne kadar büyükse gösterimin kendi hatası o kadar büyük), bu yüzden
    orantılı.

    AMA ORANTILI PAYIN BİR SINIRI VAR ve eski sürüm o sınırı sormuyordu: pay
    0,5'e ulaştığında HER gerçek sayı bir tam sayının payı içindedir, yani
    sınama ızgarayı değil hiçbir şeyi ölçer. Eski sürüm o hâlde de bir ızgara
    DÖNDÜRÜYORDU — ölçemediğini söylemek yerine yanlış bir ızgara vermek,
    eşiğin tabanını sessizce şişirir. Pay ızgara inceldikçe büyüdüğü için,
    bir ızgarada karar verilemiyorsa daha incesinde hiç verilemez; ölçüm o
    noktada durur ve hâl adıyla döner.

    DÖNEN SIFIR ÜÇ AYRI ŞEY OLABİLİR ve üçü ayrı adla döner: hiç gözlem yok ·
    örneklem bir ızgarayı tesadüften ayıramayacak kadar dar · seri
    yuvarlanmamış. Sıfırı tek başına döndüren eski imza bu üçünü aynı
    görüntüye indiriyordu; eşiğin tabanı olarak sıfır, tabanın KONULMADIĞI
    anlamına gelir ve okura hangi sebeple konulmadığı da söylenmelidir.
    """
    d = s.dropna()
    if d.empty:
        return 0.0, "gozlem_yok"
    if int(d.nunique()) < ADIM_ASGARI_BENZERSIZ:
        return 0.0, "ornek_yetersiz"
    v = d.to_numpy(dtype=float)
    for us in range(ADIM_US_KABA, ADIM_US_INCE + 1):
        g = 10.0 ** (-us)
        oran = v / g
        pay = np.maximum(1e-6, np.abs(oran) * 1e-12)
        if not bool(np.all(pay < 0.5)):
            return 0.0, "karar_verilemez"
        if bool(np.all(np.abs(oran - np.round(oran)) <= pay)):
            return float(g), "olculdu"
    # En ince ızgaradan sonrası ızgara değil: seri yuvarlanmamış demektir ve
    # yuvarlanmamış bir seriye yuvarlama tabanı çıkarmak anlamsız olurdu.
    return 0.0, "izgara_yok"


def yayim_adimi(s: pd.Series) -> float:
    """`yayim_adimi_olc`un yalnız adımı — hâli önemsemeyen çağrı yerleri için.

    `tavan` argümanı KALDIRILDI, eklenmedi: ölçülemeyen bir ızgarayı bir
    tavanla sınırlamak, ölçülmemiş bir sayıyı ölçülmüş gibi göstermenin başka
    bir biçimiydi. Ölçülemeyen ızgara artık sıfır döner ve taban KONULMAZ.
    """
    return yayim_adimi_olc(s)[0]

def _adlar(adlar, en_fazla: int = 3) -> str:
    """Bir uyarı cümlesine sığacak kadar okur adı; gerisi sayıyla.

    NEDEN VAR — bir denetim yanlış alarm ürettiğinde kimse ona bakmaz, ve
    "otuz beş satır" ile "yanlış alarm" okurun gözünde aynı şeydir. Bu hattın
    bütün uyarıları SERİ BAŞINA döngülerden çıkıyor ve kaynak tarafındaki bir
    kesinti otuz beş serinin HEPSİNİ birden vurur: koşu kutusu tek bir olayı
    otuz beş kez anlatan bir duvara döner ve içindeki gerçek tekil kusur
    (bir bacağın donması) o duvarda kaybolur. Bu yüzden her uyarı ailesi TEK
    cümlede toplanır; seri seri ayrıntı kaybolmaz, makine kaydında (koşu
    durumu) tam olarak durur.
    """
    b = _bicim()
    liste = list(adlar)
    gorunen = [okur_adi(a) for a in liste[:en_fazla]]
    kalan = len(liste) - len(gorunen)
    # Ayraç orta nokta, virgül DEĞİL: okur adlarının kendisi virgül taşıyor
    # ("Arındırılmış değişim, gerçek kişiler, kıymetli maden") ve virgülle
    # birleştirilmiş bir liste okunduğunda nerede bir serinin bitip
    # ötekinin başladığı seçilemez.
    metin = " · ".join(gorunen)
    if kalan > 0:
        metin += f" ve {b.sayi(kalan, 0)} seri daha"
    return metin


def ad_uzun(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_TR[t.month]} {t.year}"


def ad_gun(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day} {AY_TR[t.month]} {t.year}"


def ad_kisa(t) -> str:
    t = pd.Timestamp(t)
    return f"{AY_KISA[t.month]}-{str(t.year)[2:]}"


# --------------------------------------------------------------------------- toplama
def cek_kume(kodlar: dict[str, Seri], bicim_ad: str, parca_gun: int,
             yenile: bool = False, etiket: str = "") -> pd.DataFrame:
    """Bir seri kümesini çeker ve tek çerçeve verir; kolon adı = sözlük anahtarı.

    Ağ düşerse ve önbellek varsa eski önbellekle DEVAM EDİLİR ama SESSİZ
    kalınmaz: çevrimdışı bir koşunun sağlıklı bir koşuyla aynı görünmesi, bu
    depoda ölçülmüş bir arıza sınıfıdır.
    """
    # ÖNBELLEK ANAHTARI SORGU PENCERESİNİ TAŞIR (bkz. `_cache_yolu`): kataloğun
    # başlangıcı değişince ad da değişir, yani eski pencerenin cevabı bir daha
    # okunmaz. Bunun tazelikle ilgisi yok — 139 haftalık bir dosya TTL dolmadan
    # da yanlış cevaptır, çünkü sorulan soru artık başkadır.
    eksik = [ad for ad, s in kodlar.items()
             if yenile or not _taze(_cache_yolu(s.kod, bicim_ad,
                                                sorgu_alt_siniri(s)),
                                    CACHE_TTL_SAAT)]
    if eksik:
        print(f"  {etiket}: {len(eksik)}/{len(kodlar)} seri kaynaktan çekiliyor "
              f"({-(-len(eksik) // DEMET)} demet)", flush=True)
        # Aynı başlangıcı paylaşanlar bir arada tutulur: demetin başlangıcı
        # min() olduğu için karışık bir demet, geç başlayan seriyi de erken
        # tarihten sorar ve parça sayısını gereksiz büyütür.
        eksik = sorted(eksik, key=lambda a: kodlar[a].bas)
        # Bitiş İLERİ atılır: EVDS aralığın SONUNDAN geriye doldurur, yani
        # bitişi bugüne kesmek — bir gözlem ileri tarihli damgalanmışsa ya da
        # koşucunun saati kayıksa — en yeni gözlemi sessizce düşürür.
        son = pd.Timestamp.today().normalize() + pd.Timedelta(days=ILERI_GUN)
        for i in range(0, len(eksik), DEMET):
            grup = eksik[i:i + DEMET]
            # YOKLAMA PAYI: katalogdaki başlangıçtan BİR YIL GERİDEN sorulur.
            # Çekim alt sınırı ile kapsam denetiminin ölçütü aynı sabit
            # olduğunda denetim yapısal olarak kördür — daha eski bir gözlem
            # hiç sorulmadığı için hiç görünmez. Payı ekleyen tek satır,
            # `kapsam_uyarilari`nin "tarihçe uzamış" dalını ölçülebilir
            # kılan şeydir; kaldırılırsa o dal ölü koda döner ve sessizce
            # hep temiz görünür.
            bas = min(sorgu_alt_siniri(kodlar[a]) for a in grup)
            d = _demet_cek([kodlar[a].kod for a in grup], bas, son,
                           parca_gun, bicim_ad)
            for a in grup:
                g = kodlar[a].kod.replace(".", "_")
                if g in d.columns and d[g].notna().any():
                    s = d[g].dropna()
                    s.name = kodlar[a].kod
                    yeni = _cache_yolu(kodlar[a].kod, bicim_ad,
                                       sorgu_alt_siniri(kodlar[a]))
                    s.to_csv(yeni)
                    _cache_eskisini_sil(kodlar[a].kod, bicim_ad, yeni)
    out: dict[str, pd.Series] = {}
    yok: list[str] = []
    bayat: list[tuple[str, float]] = []
    for ad, s in kodlar.items():
        yol = _cache_yolu(s.kod, bicim_ad, sorgu_alt_siniri(s))
        if not yol.exists():
            yok.append(ad)
            continue
        if not _taze(yol, CACHE_TTL_SAAT):
            bayat.append((ad, _yas_gun(yol)))
        out[ad] = pd.read_csv(yol, index_col=0, parse_dates=True).iloc[:, 0]
    # Kesinti SERİ BAŞINA değil AİLE BAŞINA anlatılır: kaynak düştüğünde otuz
    # beş serinin hepsi birden düşer ve otuz beş satır tek bir olayı anlatır.
    b = _bicim()
    if len(yok) == 1:
        uyar(f"SERİ YOK: {okur_adi(yok[0])} ne kaynaktan geldi ne de önbellekte "
             "var; bu seriye dayanan ölçüm bu koşuda yapılamıyor.")
    elif yok:
        uyar(f"SERİ YOK: {b.sayi(len(yok), 0)} seri ne kaynaktan geldi ne de "
             f"önbellekte var ({_adlar(yok)}); bunlara dayanan ölçümler bu "
             "koşuda yapılamıyor.")
    if len(bayat) == 1:
        ad, yas = bayat[0]
        uyar(f"ESKİ ÖNBELLEK: {okur_adi(ad)} {b.sayi(yas, 0)} gün önce alınmış — "
             "bu koşuda tazelenemedi, seri bayat olabilir.")
    elif bayat:
        ad, yas = max(bayat, key=lambda x: x[1])
        uyar(f"ESKİ ÖNBELLEK: {b.sayi(len(bayat), 0)} seri bu koşuda tazelenemedi "
             f"ve önbellekten okundu; en eskisi {okur_adi(ad)}, "
             f"{b.sayi(yas, 0)} gün önce alınmış.")
    df = pd.DataFrame(out).sort_index()
    df.index.name = "tarih"
    return df


# --------------------------------------------------------------------------- kapsam
def cerceve_imza(H: pd.DataFrame) -> dict:
    """Bir çerçevenin KÜNYESİ: türetilmiş bir kayıt, HANGİ çerçeveyi anlattığını
    söylemelidir.

    `_cache_yolu` ile AYNI SINIF kusura karşı. Ölçüm katmanı, veri katmanının
    bıraktığı koşu kaydından uyarıları devralıyor ve o kaydın anlattığı
    çerçevenin ELİNDEKİ çerçeve olduğunu varsayıyordu. Varsayım sessizce
    düşer: veri katmanı düştüğü, atlandığı ya da başka bir pencereyle koştuğu
    her koşuda kayıt yerinde durur, okunur, hata vermez — yalnızca başka bir
    çerçeveyi anlatır. Bir kayıt kendi girdisini taşımıyorsa, onu okuyan
    katman yanlış olduğunu ölçemez.

    Künye ne kadar dar olursa o kadar iyi: satır ve sütun sayısı ile iki uç,
    pencerenin uzaması (653 hafta), kısalması (kırpma) ve ilerlemesi (yeni
    hafta) hâllerinin üçünü de birden ayırt eder.
    """
    idx = H.index
    return {
        "satir": int(H.shape[0]),
        "sutun": int(H.shape[1]),
        "ilk": None if not len(idx) else pd.Timestamp(idx[0]).strftime("%Y-%m-%d"),
        "son": None if not len(idx) else pd.Timestamp(idx[-1]).strftime("%Y-%m-%d"),
    }


def kapsam_olc(H: pd.DataFrame) -> dict:
    """Her serinin KENDİ ilk gözlemi, KENDİ son gözlemi ve gözlem sayısı.

    "Veri geldi" ile "veri TAM geldi" aynı şey değildir: kaynak kırpmayı
    SÖYLEMEZ, HTTP 200 döner ve seri kısa gelir. Tarihçe bu hatta ASİMETRİK
    olduğu için tek bir hat saati bu soruyu cevaplayamaz — her serinin kapsamı
    AYRI ölçülür ve kayda geçer.
    """
    kapsam: dict[str, dict] = {}
    for ad, s in HAFTALIK.items():
        # SORULAN alt sınır kayda GİRER, çünkü gelen başlangıcın anlamı ona
        # bağlı: sorgu alt sınırı ile cevap AYNI güne düşüyorsa o cevap
        # serinin başlangıcı değil sorgunun sınırıdır ve ikisi tıpatıp aynı
        # görünür. Bu hattın en pahalı kusuru tam olarak buydu ve kayıtta
        # sorulanın izi olmadığı için geriye dönük de görülemiyordu.
        # HÜKÜM KAPISI KAYDA ÜÇ ALANLA GİRER, BİRLE DEĞİL. Kayıt bir süre
        # yalnız `bas_olculdu` taşıyordu ve o alan KATALOĞUN ifadesidir;
        # kırpılmış bir çerçevede de aynen "ölçüldü" der. Kapının iki yarısı
        # ayrı ayrı yazılır ki geriye dönük bakan biri hangi yarının düştüğünü
        # görebilsin — ikisi tek bayrakta toplanırsa fark ölçülemez hâle gelir.
        ortak = {"kod": s.kod, "birim": s.birim, "beklenen_bas": s.bas,
                 "bas_kanit": s.bas_kanit,
                 "bas_kanit_var": bas_olculdu(ad),
                 "sorulan_bas": sorgu_alt_siniri(s).strftime("%Y-%m-%d")}
        if ad not in H.columns:
            kapsam[ad] = {**ortak, "bas": None, "son": None, "n": 0,
                          "cerceve_basa_uzaniyor": False, "bas_olculdu": False}
            continue
        d = H[ad].dropna()
        uzaniyor = bas_cerceveye_ulasti(H, ad)
        kapsam[ad] = {
            **ortak,
            "bas": None if d.empty else d.index[0].strftime("%Y-%m-%d"),
            "son": None if d.empty else d.index[-1].strftime("%Y-%m-%d"),
            "n": int(len(d)),
            "cerceve_basa_uzaniyor": bool(uzaniyor),
            "bas_olculdu": bool(ortak["bas_kanit_var"] and uzaniyor),
        }
    return kapsam


def kapsam_uyarilari(kapsam: dict) -> list[str]:
    """Beklenen başlangıç ile gelen başlangıç AYRIŞTI mı — iki yöne birden?

    İKİ AYRI ARIZA, İKİ AYRI CÜMLE. Ölçüt uzun süre yalnız birini sorabiliyordu
    ve öteki YAPISAL OLARAK görünmezdi.

      (a) GEÇ BAŞLIYOR — kırpma izi. Kaynak tek istekte ~1000 satır döndürüp
          gerisini uyarı vermeden kesiyor ve aralığın SONUNDAN geriye
          doldurduğu için kesilen şey tarihçenin BAŞIDIR. HTTP 200 döner,
          gövde doludur, koşu yeşil biter; eksik olan yalnız tarihçedir.

      (b) ERKEN BAŞLIYOR — tarihçe uzamış, biz kısa soruyoruz. Bu dal ancak
          çekim katalogdaki başlangıçtan GERİDEN sorduğu için ölçülebilir
          (bkz. YOKLAMA_GUN). Alt sınır ile ölçüt aynı sabit olsaydı cevap
          hiçbir zaman beklenenden erken OLAMAZDI ve denetim sonsuza kadar
          "temiz" derdi — bu hattın on iki buçuk yıllık tarihçesinin iki buçuk
          yılı tam olarak böyle kayboldu. Bulgu bir ALT SINIRDIR: yoklama payı
          kadar geriye bakabiliyoruz, kaynak daha da eskiye gidiyor olabilir.

    Tolerans yayım ritminden türer (`kapsam_tolerans`): bir yayım aralığı
    kadar kayma kırpma değil, kaynağın damgalama kararıdır.

    Bulgu ailesi başına TEK cümlede toplanır. İki arıza da istek düzeyinde
    olur, yani aynı demetteki bütün serileri birden vurur; seri seri yazmak
    bir olayı otuz beş kez anlatmak olurdu. Seri bazlı ayrıntı kaybolmuyor —
    koşu kaydında her serinin sorulan alt sınırı, gelen başlangıcı, son günü
    ve gözlem sayısı ayrı ayrı duruyor.
    """
    b = _bicim()
    tol = kapsam_tolerans()
    gec: list[tuple[str, pd.Timestamp, pd.Timestamp, int]] = []
    erken: list[tuple[str, pd.Timestamp, pd.Timestamp, int]] = []
    for ad, k in kapsam.items():
        if not k["bas"]:
            continue
        bek = pd.Timestamp(k["beklenen_bas"])
        bas = pd.Timestamp(k["bas"])
        fark = (bas - bek).days
        if fark > tol:
            gec.append((ad, bas, bek, fark))
        elif -fark > tol:
            erken.append((ad, bas, bek, -fark))

    uy: list[str] = []
    if gec:
        ad, bas, bek, _ = max(gec, key=lambda x: x[3])
        if len(gec) == 1:
            # CÜMLE KUSURU KAYNAĞA YIKMAZ. "Kaynak tarihçeyi kesti" bir
            # ÇIKARIMDIR ve bu hatta yanlış çıktı: aynı görüntü, sorgu
            # penceresi değişmişken eski cevabı taşımaya devam eden bir
            # önbellekten de doğuyordu. Ölçülen şey elimizdeki serinin nerede
            # BAŞLADIĞIDIR; nerede kesildiği ölçülmedi ve yazılmaz.
            uy.append(
                f"KAPSAM: {okur_adi(ad)} bu koşuda {b.tarih_kisa(bas)} "
                f"tarihinde başlıyor; kaynağın yayımladığı ilk gözlem "
                f"{b.tarih_kisa(bek)}. Tarihçenin başı bu koşuda alınamadı.")
        else:
            uy.append(
                f"KAPSAM: {b.sayi(len(gec), 0)} seri bu koşuda kaynağın "
                f"yayımladığı ilk gözlemden geride başlıyor; en uzun eksik "
                f"{okur_adi(ad)} serisinde ({b.tarih_kisa(bek)} yerine "
                f"{b.tarih_kisa(bas)}). Tarihçenin başı bu koşuda alınamadı.")
    if erken:
        ad, bas, bek, gun = max(erken, key=lambda x: x[3])
        # "EN AZ" bilinçli: yoklama payı kadar geriye bakılıyor, dolayısıyla
        # ölçülen fark gerçek farkın alt sınırıdır. "Tam şu kadar" yazmak,
        # ölçülmemiş bir kesinlik bildirmek olurdu.
        kac = f"{b.sayi(gun / AILE_RITIM_GUN['haftalik'], 0)} hafta"
        if len(erken) == 1:
            uy.append(
                f"KAPSAM: {okur_adi(ad)} {b.tarih_kisa(bas)} tarihinde "
                f"başlıyor; bu sayfa onu {b.tarih_kisa(bek)} tarihinden "
                f"itibaren ölçüyordu. Kaynak en az {kac} daha eski gözlem "
                "yayımlıyor ve ölçüm o kadar geriye uzatılmadı.")
        else:
            uy.append(
                f"KAPSAM: {b.sayi(len(erken), 0)} seri, bu sayfanın ölçmeye "
                f"başladığı tarihten daha eski gözlem taşıyor; en uzunu "
                f"{okur_adi(ad)} serisinde ({b.tarih_kisa(bek)} yerine "
                f"{b.tarih_kisa(bas)}). Kaynak en az {kac} daha eski gözlem "
                "yayımlıyor ve ölçüm o kadar geriye uzatılmadı.")
    return uy


def parca_aritmetigi(bugun: pd.Timestamp | None = None) -> dict:
    """"653 haftalık seri tek isteğe sığar mı?" — ÖLÇÜLÜR, varsayılmaz.

    Soru kaynağın sessiz kırpmasıyla ilgili ve cevabı bir HÜKÜM değil bir
    ARİTMETİKTİR; aritmetik olduğu için yaşlanmaz ve `duman.py` onu ENGEL
    olarak sınayabilir. Yorumda "sığıyor" yazmak, tarihçe uzadıkça bir gün
    sessizce yalan olurdu.

    Üç büyüklük ölçülür ve üçü de aynı sınıra (SATIR_SINIRI) karşı durur:

      · EN GENİŞ İSTEK — katalogdaki en eski başlangıç, yoklama payıyla
        birlikte, bugüne kadar: kaç haftalık satır ister? Bugün 2014'ün
        başından bugüne yaklaşık yedi yüz hafta, sınırın altında, yani
        çekim TEK parçaya sığıyor ve tarihçenin başı kesilmiyor.
      · PARÇA TAVANI — parçalama devreye girdiğinde bir parça kaç satır
        döndürür? Tarihçe uzadığında istek bölünür ve her parça kendi başına
        sınırın altında kalır; yani cevap "bugün sığıyor" değil, "yarın da
        kesilmez"dir.
      · KALAN PAY — tek parçanın dolmasına kaç hafta var? Bir sınıra ne kadar
        yaklaşıldığı, sınırın aşılıp aşılmadığı kadar önemli: pay ölçülmezse
        parçalamanın ilk kez devreye girdiği gün de görünmez.
    """
    bugun = pd.Timestamp.today().normalize() if bugun is None else bugun
    en_eski = min(pd.Timestamp(s.bas) for s in HAFTALIK.values())
    sorulan = min(sorgu_alt_siniri(s) for s in HAFTALIK.values())
    ritim = AILE_RITIM_GUN["haftalik"]
    gun = int((bugun + pd.Timedelta(days=ILERI_GUN) - sorulan).days)
    return {
        "en_eski_bas": en_eski.strftime("%Y-%m-%d"),
        "sorulan_bas": sorulan.strftime("%Y-%m-%d"),
        "istek_gun": gun,
        "istek_satir": gun // ritim + 1,
        "parca_gun": PARCA_HAFTA_GUN,
        "parca_satir": PARCA_HAFTA_GUN // ritim,
        "parca_sayisi": -(-gun // PARCA_HAFTA_GUN),
        "satir_siniri": SATIR_SINIRI,
        "kalan_hafta": (PARCA_HAFTA_GUN - gun) // ritim,
        "tek_parca": gun <= PARCA_HAFTA_GUN,
        "siniri_asiyor": (gun // ritim + 1) > SATIR_SINIRI,
    }


def bosluk_olc(H: pd.DataFrame) -> dict:
    """Çekirdek serilerde ardışık iki gözlem arası YEDİ GÜN DEĞİLSE.

    ÖLÇÜT "uzun" DEĞİL "yedi değil"dir ve bu bir düzeltmedir. Eskiden yalnız
    `g > 7` soruluyordu, yani atlanan hafta görünüyor ama KISALAN aralık
    görünmüyordu — kaynak son gözlemi tatil kayması yüzünden altı gün arayla
    damgaladığında hiçbir uyarı düşmüyordu. Oysa ölçüm katmanı haftalık
    değişimi yalnız TAM YEDİ GÜNLÜK aralıklarda hesaplıyor (bkz. metrik
    `_ardisik_fark`): altı günlük bir aralık da o haftanın Δ stokunu
    ÖLÇÜLMEMİŞ yapar, kimlik bloğunun saatini geriye çeker ve koşu kaydında
    hiç iz bırakmazdı. Bir ölçümü düşüren her aralık görünür olmalı.

    Ölçüm ile uyarı ayrı tutulur (aynı hesabı iki kez yazmamak için): burası
    seri bazlı ham kaydı verir ve koşu durumuna girer, uyarı cümlesini
    `bosluk_uyarilari` kurar. Yalnız çekirdekte aranır: bir kırılım bacağının
    tek haftalık boşluğu kümüle akımı bozmaz, çekirdeğinki bozar.
    """
    out: dict[str, dict[str, list[str]]] = {}
    for ad in CEKIRDEK:
        if ad not in H.columns:
            continue
        d = H[ad].dropna()
        if len(d) < 2:
            continue
        fark = d.index.to_series().diff().dt.days
        uzun = [t.strftime("%Y-%m-%d") for t, g in fark.items()
                if pd.notna(g) and g > 7]
        kisa = [t.strftime("%Y-%m-%d") for t, g in fark.items()
                if pd.notna(g) and g < 7]
        if uzun or kisa:
            out[ad] = {"atlanan": uzun, "kisalan": kisa}
    return out


def bosluk_sag_ucta(tarih, bugun=None) -> bool:
    """Bu boşluk SAĞ UÇTA mı — yani bu koşuda yayımlanan sayılara dokunuyor mu?

    ÖLÇÜT TAZELİK TOLERANSIDIR, YENİ BİR SABİT DEĞİL. "Sayfadaki sayı ilerledi
    mi" sorusunun penceresi zaten tanımlı (`tazelik_tolerans`); boşluğun aynı
    pencereye düşüp düşmediği de aynı tanımdan sorulur. İkinci bir eşik
    yazılsaydı biri güncellenip öteki unutulurdu.
    """
    bugun = pd.Timestamp.today().normalize() if bugun is None else pd.Timestamp(bugun)
    return int((bugun - pd.Timestamp(tarih)).days) <= tazelik_tolerans()


def bosluk_uyarilari(H: pd.DataFrame, bugun=None) -> list[str]:
    """Beklenmeyen aralık TEK cümlede — ama DÖRT AİLE ayrı cümlelerde.

    İKİ EKSEN VAR VE İKİSİ DE BAĞIMSIZ.

    (1) NE OLDU. "Hafta atlandı" ile "aralık kısaldı" aynı cümlede
        anlatılamaz, çünkü sonuçları farklı: atlanan haftayı takvime bağlı
        kümüleler hiç saymaz, kısalan aralık ise o haftanın stok değişimini
        ölçülemez kılar. Bir cümlede toplansalardı okur hangisinin olduğunu
        bilemezdi ve ikisinin de doğru göründüğü bir kusur çıkardı.

    (2) NEREDE OLDU — VE BU BİR DÜZELTMEDİR. Boşluk ölçümü tarihçenin
        TAMAMINI tarıyor, ama ürettiği cümlenin öneki bayatlık ailesindeydi:
        2015'te atlanmış tek bir hafta, verisi bugüne kadar gelmiş bir sayfayı
        HER KOŞUDA "bayat" ilan ediyordu. On iki yıllık haftalık bir seride
        boşluk bulunmaması neredeyse imkânsız olduğu için hüküm KALICI olurdu
        ve gerçekten donmuş bir beslemeden ayırt edilemezdi.

        Eski bir boşluk bir TARİHÇE özelliğidir: pencereye dokunur, okura
        bildirilir, ama bu koşuda yayımlanan sayı hakkında hiçbir şey
        söylemez. Bayatlık SAĞ UCA dair bir hükümdür. İkisi ayrı önek alır
        (bkz. `SAG_UC_IZI` · `TARIHCE_IZI`) ve yalnız sağ uçtaki bayatlığı
        tetikler. Bulgunun kendisi hiçbir hâlde kaybolmaz — kaybolan yalnız
        yanlış hüküm.
    """
    b = _bicim()
    bosluk = bosluk_olc(H)
    if not bosluk:
        return []
    uy: list[str] = []
    atlanan = sorted({t for r in bosluk.values() for t in r["atlanan"]})
    kisalan = sorted({t for r in bosluk.values() for t in r["kisalan"]})
    for tarihler, sag_onek, tar_onek, govde in (
        (atlanan, "HAFTA ATLANDI", "TARİHÇEDE BOŞLUK",
         "çekirdek serilerde {n} hafta eksik; en yenisi {t}. Takvime bağlı "
         "kümüle toplamlar o haftaları hiç saymaz, sabit uzunluklu pencereler "
         "ise pencereyi geriye uzatır."),
        (kisalan, "ARALIK KISALDI", "TARİHÇEDE KISA ARALIK",
         "{n} gözlem bir öncekinden yedi günden az sonra damgalanmış; en "
         "yenisi {t}. O haftaların stok değişimi ölçülmemiş sayılıyor."),
    ):
        if not tarihler:
            continue
        sag = [x for x in tarihler if bosluk_sag_ucta(x, bugun)]
        eski = [x for x in tarihler if not bosluk_sag_ucta(x, bugun)]
        # Sağ uçtaki bulgu ile eski bulgu AYRI cümlelerde ve ayrı sayılarla
        # yazılır: tek cümlede toplansalardı sayının hangi kümeyi saydığı
        # okunmaz olurdu ve önek de ikisinden birini yanlış temsil ederdi.
        if sag:
            uy.append(f"{sag_onek}: " + govde.format(
                n=b.sayi(len(sag), 0), t=b.tarih_kisa(sag[-1])))
        if eski:
            uy.append(f"{tar_onek}: " + govde.format(
                n=b.sayi(len(eski), 0), t=b.tarih_kisa(eski[-1]))
                + " Bu boşluklar tarihçenin içinde kaldı; bu koşuda yayımlanan "
                  "sayılara dokunmuyorlar.")
    return uy


def cerceve_uyarilari(H: pd.DataFrame) -> list[str]:
    """ÇERÇEVEDEN TÜRETİLEBİLEN bütün uyarılar — TEK TANIM, İKİ KATMAN.

    NEDEN VAR. Ölçüm katmanı bu uyarıları veri katmanının bıraktığı koşu
    kaydından DEVRALIYORDU ve kendisi hiç ölçmüyordu. Devralma sessizce
    yanlış olabilir: kayıt bir önceki koşudan kalmış, başka bir pencereyle
    yazılmış ya da veri katmanı hiç koşmamış olabilir. Ölçüldü — kayıttaki
    uyarı listesi BOŞ dururken ölçülen çerçeve kapsam uyarısı gerektiriyordu;
    yani sayfa "bu koşuda uyarı yok" diyordu ve o cümle kaydın yaşı kadar
    eskiydi.

    KURAL: bir uyarı ÇERÇEVEDEN türetilebiliyorsa, ÖLÇEN katman onu kendi
    çerçevesinden türetir; devralınan kayıt yalnız çerçeveden türetilemeyen
    olayları taşır (ağ düştü, seri hiç gelmedi, önbellekten okundu).

    Liste burada tek yerde duruyor ki iki katman aynı soruyu aynı sırayla
    sorsun; iki ayrı çağrı listesi bir gün sessizce ayrışırdı.
    """
    uy = list(kapsam_uyarilari(kapsam_olc(H)))
    uy += bosluk_uyarilari(H)
    uy += tazelik_denetimi(H)
    uy += kimlik_denetimi(H)[0]
    uy += genis_fark_olc(H)[0]
    # Tekilleştirme SIRAYI korur: aynı cümle iki kaynaktan gelse de okur onu
    # bir kez görür ve ilk göründüğü yerde görür.
    return list(dict.fromkeys(uy))


def kapsam_yeterli(H: pd.DataFrame) -> tuple[bool, str]:
    """Çıktı üretilebilir mi? (yeterli mi, değilse sebebi)

    Bu kapı DURDURUR. Sebebi: kapsamı yetmeyen bir çekimden üretilen grafik ve
    sayfa metni, yeşil bir koşunun içinde yanlış yayımlanır ve hiçbir denetim
    bunu göremez. Durunca hattın SONRAKİ adımları hiç koşmaz.

    Yarım kalmış çerçeve YAZILMAZ; ama depodaki (doğru) sürüm de SİLİNMEZ.
    Silmek burada zarar verirdi: izlenen bir dosyanın doğru sürümü depodakidir
    ve koşucunun otomatik commit'i silmeyi sahiplenir — bir kardeş hattın
    tarihçesi tam böyle kısalmıştı.
    """
    b = _bicim()
    eksik = [ad for ad in CEKIRDEK
             if ad not in H.columns or H[ad].dropna().empty]
    if eksik:
        return False, ("çekirdek seriler eksik — "
                       + "; ".join(okur_adi(a) for a in eksik))
    tam = H[list(CEKIRDEK)].dropna(how="any")
    if len(tam) < ASGARI_HAFTA:
        return False, (f"çekirdeğin tamamının dolu olduğu hafta sayısı "
                       f"{b.sayi(len(tam), 0)}; asgari "
                       f"{b.sayi(ASGARI_HAFTA, 0)} hafta bekleniyor")
    return True, ""


# --------------------------------------------------------------------------- tazelik
def tazelik_tolerans(aile: str = "haftalik") -> int:
    """Bir tazelik ailesinin toleransı — denetimle AYNI kaynaktan.

    ozet_uret.py bayat bayrağını buradan okur; eşik iki yerde ayrı yazılırsa
    biri güncellenip öteki unutulur ve bayatlık sessizce kaçar.
    """
    return int(AILE_TOLERANS[aile])


def tazelik_olc(H: pd.DataFrame) -> dict:
    """Seri başına yayım gecikmesi (takvim günü). Ölçüm; hüküm bir sonraki
    fonksiyonda.

    Referans DUVAR SAATİDİR, verinin kendi son günü DEĞİL — verinin ucunu
    referans almak denetimi kendi kendine referanslı yapar ("son gözlem bugün,
    demek ki taze") ve donmuş bir seri sonsuza kadar taze görünür.
    """
    bugun = pd.Timestamp.today().normalize()
    out: dict[str, dict] = {}
    for aile, seriler in TAZELIK_SERI.items():
        tol = AILE_TOLERANS[aile]
        for ad in seriler:
            if ad not in H.columns or H[ad].dropna().empty:
                out[ad] = {"aile": aile, "tolerans": tol, "son": None,
                           "gecikme": None, "yok": True, "gec": False}
                continue
            sonu = H[ad].dropna().index[-1]
            gecikme = int((bugun - sonu).days)
            out[ad] = {"aile": aile, "tolerans": tol,
                       "son": sonu.strftime("%Y-%m-%d"), "gecikme": gecikme,
                       "yok": False, "gec": bool(gecikme > tol)}
    return out


def tazelik_denetimi(H: pd.DataFrame) -> list[str]:
    """Yayım durmuş mu? UYARI üretir, ASLA durdurmaz.

    Geç kalmış bir yayını DURDURAN bir kapı, gecikmeyi yokluğa çevirir — yani
    ölçtüğü şeyi büyütür. Bu yüzden burada eşik aşımı yalnız görünür olur.

    İki hâl AYRI cümlelerdir ve karıştırılmaz: "hiç yüklenemedi" (seri elimizde
    yok) ile "geç" (seri var, yayımı gecikmiş). Birincisi çekimin, ikincisi
    kaynağın kusurudur; aynı cümlede toplanırlarsa hangisinin olduğu okurun
    elinde kalmaz.

    Her hâl kendi içinde TEK cümleye toplanır: yayım durduğunda ailenin bütün
    serileri birden gecikir. Ama tek bir bacak donduğunda o bacak ADIYLA
    görünür — asıl aranan olay budur ve on satırlık bir duvarda kaybolmamalı.
    """
    b = _bicim()
    olcum = tazelik_olc(H)
    yok = [a for a, r in olcum.items() if r["yok"]]
    gec = [a for a, r in olcum.items() if r["gec"]]
    uy: list[str] = []
    if len(yok) == 1:
        uy.append(f"TAZELİK: {okur_adi(yok[0])} bu koşuda hiç yüklenemedi.")
    elif yok:
        uy.append(f"TAZELİK: {b.sayi(len(yok), 0)} seri bu koşuda hiç "
                  f"yüklenemedi ({_adlar(yok)}).")
    if gec:
        # En ESKİ bacak yazılır: gecikmenin büyüklüğü ailenin en geride
        # kalanıyla ölçülür, en tazesiyle değil.
        ad = max(gec, key=lambda a: olcum[a]["gecikme"])
        r = olcum[ad]
        if len(gec) == 1:
            uy.append(f"TAZELİK: {okur_adi(ad)} son gözlemi "
                      f"{b.tarih_kisa(r['son'])} ({b.sayi(r['gecikme'], 0)} gün "
                      f"önce, tolerans {b.sayi(r['tolerans'], 0)} gün). "
                      "Yayım durmuş olabilir.")
        else:
            uy.append(f"TAZELİK: {b.sayi(len(gec), 0)} serinin yayımı gecikmiş; "
                      f"en geride kalanı {okur_adi(ad)}, son gözlemi "
                      f"{b.tarih_kisa(r['son'])} ({b.sayi(r['gecikme'], 0)} gün "
                      f"önce, tolerans {b.sayi(r['tolerans'], 0)} gün). "
                      "Yayım durmuş olabilir.")
    return uy


# --------------------------------------------------------------------------- kimlik
def _kimlik(rapor: dict, uy: list[str], ad: str, sol: pd.Series, sag: pd.Series,
            olcek: pd.Series, esik_bagil: float | None, birim_ad: str) -> None:
    """Bir kimliği ölçer, rapora yazar; eşik VERİLMİŞSE aşımda uyarı düşürür.

    `esik_bagil=None` = "ölçülmemiş kimlik": artık hesaplanır ve yayımlanır ama
    eşik KONMAZ. Ölçülmeyen bir seviyeye eşik koymak, ilk koşuda yanlış alarm
    üretip yayının önünde durmak demektir — ve yayının önünde duran bir
    denetimin yanlış alarmı arızanın kendisidir.

    EŞİĞİN MUTLAK TABANI YAYIM HASSASİYETİNDEN GELİR — ve bu bir düzeltmedir.
    Bağıl eşik TEK BAŞINA konmuştu (1e-6) ve ilk gerçek koşuda YANLIŞ ALARM
    verdi: kırılım tablosundaki tüzel kişi stoku ile ana tablodaki aynı kalem
    en fazla 0,063 milyon dolar ayrışıyor, oysa 61.383 milyon dolarlık bir
    stokta 1e-6 yalnız 0,061 milyon dolara denk geliyordu. Okur, olmayan bir
    arızayı ("kalem numaralandırması değişmiş olabilir") okudu.

    Ölçülen fark ARIZA DEĞİL, iki tablonun ayrı ayrı yuvarlanmasıdır ve
    büyüklüğü de bunu söylüyor: ana tablo bir ondalıkla (adım 0,1), kırılım
    tablosu üç ondalıkla (adım 0,001) yayımlanıyor; 114 haftanın 113'ünde fark
    zaten 0,05'in — yani kaba ızgaranın YARISININ — altında.

    Taban neden YARIM adım değil TAM adım: 05.07.2024'te ana tablo 61.382,7
    yazarken kırılım tablosu 61.382,763 yazıyor, yani 61.382,8'e yuvarlanması
    gereken bir sayı aşağı yuvarlanmış. İki tablo aynı anlık değerin iki
    yuvarlaması DEĞİL: en az biri kendisi de yuvarlanmış parçaların toplamı ya
    da başka bir revizyon vintajı. Yarım adım (0,0505) bu gözlemi ÖLÇÜLMÜŞ
    biçimde kaçırıyor; taban bu yüzden her iki tablonun TAM adımı toplanarak
    kurulur (0,1 + 0,001 = 0,101) ve ölçülen en büyük farka 1,6 kat pay bırakır.

    TESPİT PAYI DARALMIYOR ve bu da ölçüldü. Bu kapının yakalaması gereken
    arıza kalem kaymasıdır: karşılaştırmaya giren bacak değişir. Tüzel kişi
    stokunun yerine aynı tablodaki EN YAKIN komşu kalem (gerçek kişilerin
    kıymetli maden hesabı) konursa artık 32.436 milyon dolara, gerçek kişi
    stoku konursa 83.557'ye, geniş toplam konursa 199.915'e çıkıyor. Taban
    (0,101) ile en küçük gerçek arıza arasında BEŞ büyüklük basamağı var; eşik
    yanlış alarmı susturmak için değil, ÖLÇÜLEN yayım hassasiyetinden
    türetildi.

    Etkin eşik ikisinin BÜYÜĞÜDÜR: ölçek büyüdüğünde bağıl kol devralır.
    """
    b = _bicim()
    d = pd.DataFrame({"s": sol, "r": sag, "o": olcek}).dropna()
    if d.empty:
        uy.append(f"KİMLİK: {ad} sınanamadı — girdi serileri kesişmiyor.")
        return
    fark = (d["s"] - d["r"]).abs()
    bagil = fark / d["o"].abs().clip(lower=1e-9)
    # Taban iki tarafın ÖLÇÜLEN adımından kuruluyor; taraflar aynı ızgaradaysa
    # toplam yine iki tam adımdır — iki bağımsız yuvarlama var demektir.
    (adim_sol, hal_sol) = yayim_adimi_olc(d["s"])
    (adim_sag, hal_sag) = yayim_adimi_olc(d["r"])
    taban = float(adim_sol + adim_sag)
    rapor[ad] = {
        "n": int(len(d)),
        "maks_fark": float(fark.max()),
        "maks_bagil": float(bagil.max()),
        "maks_tarih": str(bagil.idxmax().date()),
        "son_fark": float(fark.iloc[-1]),
        "birim": birim_ad,
        "esik_bagil": esik_bagil,
        "yayim_adimi_sol": float(adim_sol),
        "yayim_adimi_sag": float(adim_sag),
        # ADIMIN HÂLİ DE KAYDA GİRER. Sıfır bir adım üç ayrı sebepten gelir
        # (gözlem yok · örneklem dar · seri yuvarlanmamış) ve üçünün eşiğe
        # etkisi aynı olsa da tanısı aynı değil: sıfır tabanla koşan bir
        # kimlik, tabanı ölçülmüş sanılan bir kimlikle tıpatıp aynı görünür.
        "yayim_adimi_hal_sol": hal_sol,
        "yayim_adimi_hal_sag": hal_sag,
        "esik_taban": taban,
        "gecti": None,
    }
    if esik_bagil is None:
        return
    esik = (esik_bagil * d["o"].abs()).clip(lower=taban)
    asim = fark > esik
    rapor[ad]["asim_hafta"] = int(asim.sum())
    rapor[ad]["gecti"] = bool(not asim.any())
    if asim.any():
        # OKURA NE SÖYLER: iki tablo aynı kalemi aynı hafta farklı yazmış ve
        # fark yuvarlamayla açıklanamayacak kadar büyük. Kaç KAT olduğu
        # cümlenin içinde, çünkü "0,3 milyon dolar" tek başına büyük mü küçük
        # mü olduğunu söylemez — kıyas noktası yayım hassasiyetidir.
        en = float(fark.max())
        gun = fark.idxmax()
        # Ondalık, sayının BÜYÜKLÜĞÜNE göre: eşiğin hemen üstündeki bir sapma
        # ancak üç haneyle anlaşılır (0,105 ile 0,15 farklı şeyler), on binler
        # mertebesindeki bir kalem kaymasında aynı üç hane gürültüdür ve
        # sayıyı okunmaz yapar.
        bas = (f"KİMLİK BOZUK: {ad} — kaynağın iki tablosu aynı haftada farklı "
               f"değer veriyor. En büyük fark "
               f"{b.sayi(en, 3 if en < 10 else 1)} {birim_okur(birim_ad)} "
               f"({b.tarih_kisa(gun)})")
        # KIYAS NOKTASININ ADI, ÖLÇÜLEN ŞEYİN ADI OLMALI. Burada "yayım
        # yuvarlamasının bırakabileceği pay" yazıyordu, oysa bölen TAM
        # adımların toplamıdır (0,1 + 0,001) ve yuvarlamanın bırakabileceği
        # pay onun YARISIDIR (0,0505) — bu dosyanın kendi belgesi de o payı
        # öyle ölçüyor. İki ad aynı sayıya konunca okura verilen kat sayısı
        # iki kat küçük görünüyordu: gerçek bir kalem kaymasının kaç kat
        # olduğunu soran biri yanlış bir ölçekle bakıyordu.
        if taban > 0:
            bas += (f", iki tablonun ölçülen yayım adımları toplamının "
                    f"{b.sayi(en / taban, 1)} katı")
        else:
            # TABAN ÖLÇÜLEMEDİĞİNDE KIYAS DA YAZILMAZ. Ölçülmemiş bir bölenle
            # kurulan "şu kadar kat" cümlesi, kaç kat olduğunu ölçmüş gibi
            # görünürdü; eksik olan şey adıyla anılır.
            bas += (", yayım yuvarlamasının bırakabileceği pay bu koşuda "
                    "ölçülemedi ve karşılaştırma yalnız oransal eşikle "
                    "yapıldı")
        uy.append(
            bas + f"; toplam {b.sayi(int(asim.sum()), 0)} haftada aşılıyor. "
            "Bu kadarı yuvarlamadan doğamaz: kaynağın kalem numaralandırması "
            "ya da birimi değişmiş olabilir ve bu iki kalemden beslenen "
            "sayılar sınanana kadar temkinle okunmalı.")


def kimlik_denetimi(H: pd.DataFrame) -> tuple[list[str], dict]:
    """Kaynağın kendi içindeki tutarlılık. Tazelik değil, FORMÜL denetimi.

    Üç aile, üç ayrı ağırlık — aynı eşikle ölçülemezler:

    (1) ÖLÇÜLMÜŞ KİMLİKLER, sıkı eşik. Keşifte birebir doğrulandı:
        148.848,7 + 82.508,3 = 231.357,0 ve kırılım tablosunun iki kalemi ana
        tablonunkiyle rakamı rakamına aynı. Bunlar aynı yayımın aynı
        satırlarıdır; bağıl 1e-6 (yuvarlama payı) uygundur ve bozulması kalem
        numaralandırmasının kaydığı anlamına gelir.

    (2) ÖLÇÜLMEMİŞ KİMLİKLER, eşiksiz. Alt kırılımların toplamı üst kaleme
        eşit mi (dolar + euro + diğer + maden = toplam) keşifte ölçülmedi.
        Artık hesaplanır ve künyeye yazılır, ama eşik ilk gerçek koşudan sonra
        konur.

    (3) ÖLÇÜM, denetim değil. Geniş toplam ile yurt içi toplam arasındaki fark
        yurt dışı yerleşik bacaktır; bu bir kusur değil, yayımlanacak bir
        büyüklüktür. Eşik konmaz — yalnız işareti dönerse (geniş toplam dar
        toplamın ALTINA düşerse) kapsam varsayımı bozulmuş demektir ve uyarılır.

    AYRIŞTIRMA KİMLİĞİ (Δ stok = arındırılmış + parite) burada DENETLENMEZ:
    artığı ölçüp yayımlamak ölçüm katmanının işidir ve o kimlik tutmasa da hat
    DURMAZ. Bu katmanın oraya katkısı `hizalama_olc` ile hangi hafta
    hizalamasının artığı kapattığını ÖLÇMEKTİR.
    """
    uy: list[str] = []
    rapor: dict = {}
    K = set(H.columns)

    def _var(ad: str, gerekli) -> bool:
        """Kimliğin girdileri yüklendi mi — YOKSA SUSMAK YOK.

        Eksik sütunda kimlik SESSİZCE atlanıyordu ve kardeşi (kapsam kimliği)
        aynı durumda "SINANAMADI" diyordu: aynı olayın iki katmanda iki farklı
        görüntüsü. Atlanan bir kimlik, geçen bir kimlikle tıpatıp aynı görünür
        — koşu kaydında ne uyarı vardır ne künye satırı, yani bakılmayan yer
        geçen sınavla aynıdır. Sessiz atlama, ölçmediğini ölçmüş gibi
        göstermenin en ucuz biçimidir.
        """
        eksik = [a for a in gerekli if a not in K]
        if not eksik:
            return True
        rapor[ad] = {"gecti": None, "sinandi": False,
                     "yuklenemeyen": sorted(eksik)}
        uy.append(f"KİMLİK SINANAMADI: {ad} — "
                  f"{_adlar(eksik, en_fazla=min(len(eksik), 4))} bu koşuda "
                  "yüklenemedi; kaynağın kendi kalemleri arasındaki bu "
                  "bağıntı ölçülemiyor.")
        return False

    _ad_kapsam = ("Gerçek ve tüzel kişi stoklarının toplamı yurt içi toplama "
                  "eşit (TP.HPBITABLO2.11 + TP.HPBITABLO2.12 = "
                  "TP.HPBITABLO2.10)")
    if _var(_ad_kapsam, ("stok_gercek", "stok_tuzel", "stok_toplam")):
        _kimlik(rapor, uy, _ad_kapsam,
                H["stok_gercek"] + H["stok_tuzel"], H["stok_toplam"],
                H["stok_toplam"], 1e-6, "mn USD")
    _ad_kg = ("Kırılım tablosundaki gerçek kişi stoku ana tablodakiyle aynı "
              "(TP.HPBITABLO4.3 = TP.HPBITABLO2.11)")
    if _var(_ad_kg, ("k_gercek", "stok_gercek")):
        _kimlik(rapor, uy, _ad_kg,
                H["k_gercek"], H["stok_gercek"], H["stok_gercek"], 1e-6, "mn USD")
    _ad_kt = ("Kırılım tablosundaki tüzel kişi stoku ana tablodakiyle aynı "
              "(TP.HPBITABLO4.8 = TP.HPBITABLO2.12)")
    if _var(_ad_kt, ("k_tuzel", "stok_tuzel")):
        _kimlik(rapor, uy, _ad_kt,
                H["k_tuzel"], H["stok_tuzel"], H["stok_tuzel"], 1e-6, "mn USD")

    # (2) ÖLÇÜLMEMİŞ — bacakların toplamı üst kaleme eşit mi.
    # Ağaç KIRILIMLAR sözleşmesinden okunuyor: aynı ağaç sıfır denetiminin
    # cümlelerini de besliyor ve iki yerde ayrı yazılsaydı bir gün sessizce
    # ayrışırdı. Kalem numaraları da elle değil katalogdan.
    for kir in KIRILIMLAR:
        parcalar = list(kir.parcalar)
        if _var(kirilim_adi(kir), parcalar + [kir.ust]):
            _kimlik(rapor, uy, kirilim_adi(kir),
                    H[parcalar].sum(axis=1, min_count=len(parcalar)),
                    H[kir.ust], H[kir.ust].abs().clip(lower=1.0), None, "mn USD")

    # (4) KAPSANMA — eşitlik değil, İÇİNDE OLMA. İki seri hiçbir kimliğe
    # girmiyordu ve altı yayımlanan sayıyı besliyorlar.
    #
    # NEDEN EŞİTLİK KURULAMIYOR: kırılım tablosunun gerçek kişi bloğu 4.3'ten
    # 4.7'ye kadar sürüyor ve arasındaki para birimi kalemleri (4.4–4.6) bu
    # hatta ÇEKİLMİYOR, yani "bacakların toplamı üst kaleme eşit" sorusu
    # sorulamıyor. Sorulabilen soru daha zayıf ama boş değil: maden hesabı
    # üst kalemin İÇİNDE mi?
    #
    # NEDEN ÖNEMLİ: sayfa bu iki seriden bir PAY yazıyor (maden hesaplarının
    # stok içindeki oranı) ve o payın anlamlı olması kalemin gerçekten üst
    # kalemin bir parçası olmasına bağlı. Kalem numaralandırması kayar da
    # 4.7'nin yerine bloğun dışından bir kalem gelirse, pay sessizce yüzü
    # aşabilir ya da daha kötüsü aşmadan yanlış olur. Kıyas AYNI TABLONUN
    # kalemiyle kurulur (4.3 · 4.8), çünkü payda olarak kullanılan ana tablo
    # kalemine köprü zaten yukarıdaki iki sıkı kimlikle kurulu.
    for ic, dis, ad in (
            ("maden_gercek", "k_gercek",
             "Gerçek kişilerin kıymetli maden hesapları kırılım tablosundaki "
             "gerçek kişi stokunun içinde (TP.HPBITABLO4.7 ≤ TP.HPBITABLO4.3)"),
            ("maden_tuzel", "k_tuzel",
             "Tüzel kişilerin kıymetli maden hesapları kırılım tablosundaki "
             "tüzel kişi stokunun içinde (TP.HPBITABLO4.12 ≤ TP.HPBITABLO4.8)")):
        if _var(ad, (ic, dis)):
            _kapsanma(rapor, uy, ad, H[ic], H[dis], "mn USD")
    return uy, rapor


def _kapsanma(rapor: dict, uy: list[str], ad: str, ic: pd.Series,
              dis: pd.Series, birim_ad: str) -> None:
    """Bir kalem ötekinin İÇİNDE mi — kapsanma denetimi, eşitlik değil.

    EŞİK UYDURULMUYOR, TANIMDAN GELİYOR: bir alt kalem üst kalemi aşamaz.
    Tolerans yalnız yayım yuvarlamasıdır (iki tarafın ölçülen adımı), çünkü
    aşımın kendisi bir yorum değil aritmetik bir imkânsızlıktır. Adım
    ölçülemezse tolerans SIFIR olur ve bu doğru taraftır: ölçemediğimiz bir
    payı cömertçe vermek, kapıyı sessizce körelmiş bırakır.

    Ölçüm her hâlde künyeye yazılır — en büyük pay, o payın haftası, aşım
    sayısı. Bugün pay gerçek kişilerde en çok yüzde 61,5, tüzel kişilerde
    yüzde 13,2: kapsanma rahatça tutuyor ve o rahatlık ölçülmüş olarak
    duruyor, "herhâlde tutuyordur" olarak değil.
    """
    b = _bicim()
    d = pd.DataFrame({"i": ic, "d": dis}).dropna()
    if d.empty:
        rapor[ad] = {"gecti": None, "sinandi": False, "n": 0}
        uy.append(f"KİMLİK SINANAMADI: {ad} — girdi serileri kesişmiyor.")
        return
    (adim_ic, hal_ic) = yayim_adimi_olc(d["i"])
    (adim_dis, hal_dis) = yayim_adimi_olc(d["d"])
    tolerans = float(adim_ic + adim_dis)
    asim_mn = d["i"] - d["d"] - tolerans
    pay = d["i"] / d["d"].abs().clip(lower=1e-9) * 100.0
    asim = asim_mn > 0
    rapor[ad] = {
        "n": int(len(d)), "sinandi": True,
        "maks_pay": float(pay.max()),
        "maks_pay_tarih": str(pay.idxmax().date()),
        "son_pay": float(pay.iloc[-1]),
        "tolerans": tolerans,
        "yayim_adimi_hal_ic": hal_ic, "yayim_adimi_hal_dis": hal_dis,
        "asim_hafta": int(asim.sum()),
        "birim": birim_ad,
        "gecti": bool(not asim.any()),
    }
    if asim.any():
        # İKİ CÜMLE. Burada üç vardı ve ortadaki cümle ölçüyü, sonuncusu
        # gerekçeyi anlatıyordu; ölçü ile gerekçe tek cümlede birleştirildi ve
        # kaydın geri kalanı (aşımın haftası, payı, toplam hafta sayısı) zaten
        # rapor bloğunda duruyor. Koşu kaydı satırı mekanik olmalı: olayı ve
        # büyüklüğünü söyler, argümanı sayfaya bırakır.
        uy.append(
            f"KAPSANMA BOZUK: {ad} — alt kalem üst kalemi aşıyor; en büyük "
            f"aşım {b.sayi(float(asim_mn.max()), 1)} {birim_okur(birim_ad)}, "
            f"toplam {b.sayi(int(asim.sum()), 0)} hafta. Bir alt kalem üst "
            "kalemi aşamaz: bu iki kalemden hesaplanan paylar sınanana kadar "
            "temkinle okunmalı.")


def genis_fark_olc(H: pd.DataFrame) -> tuple[list[str], dict]:
    """Geniş toplam ile yurt içi toplamın FARKI — bir KAPSAM farkı.

    Bu bir DENETİM değil ÖLÇÜMDÜR ve eşiği yoktur: keşifte 39.714,9 mn USD
    ölçüldü ve bu bir kusur değil, kapsamın kendisidir. Ölçülüp künyeye
    yazılmasının sebebi, geniş toplamın sayfada geçmesi hâlinde ADIYLA ve
    FARKIYLA geçmesi zorunluluğudur.

    FARKIN TAMAMI "YURT DIŞI BACAK" DEĞİLDİR ve fonksiyonun adı da onu
    söylemez. Künyenin kalem numaralandırmasına göre geniş toplam (1.) dört
    bölümden oluşuyor ve yurt içi toplam yalnız birincisidir (1.1); fark
    1.2 + 1.3 + 1.4'tür. Yurt dışı yerleşik bankalar YALNIZCA 1.4'tür
    (TP.HPBITABLO4.21) ve o seri bu hatta çekilmiyor; farkın içindeki 1.3.4
    kalemi (TP.HPBITABLO4.20) tek başına 3.263,5 milyon dolar. Farkı okura
    "yurt dışı yerleşikler şu kadar tutuyor" diye basmak, ölçülmemiş bir şeyi
    ölçülmüş gibi göstermek olurdu — üstelik hattın kendi kodu 1.3'ün ne
    olduğunun ölçülmediğini başka bir yerde açıkça yazarken.

    Tek uyarı hâli: fark EKSİYE dönerse geniş toplam dar toplamın altına düşmüş
    demektir; o zaman kapsam varsayımı ("4.1 yurt içi toplamdan geniştir")
    bozulmuş ya da kalem numaralandırması kaymıştır.
    """
    b = _bicim()
    uy: list[str] = []
    if not {"genis_toplam", "stok_toplam"} <= set(H.columns):
        return uy, {}
    d = pd.DataFrame({"g": H["genis_toplam"], "i": H["stok_toplam"]}).dropna()
    if d.empty:
        return uy, {}
    fark = d["g"] - d["i"]
    pay = fark / d["g"].abs().clip(lower=1e-9)
    rapor = {
        "n": int(len(d)),
        "son_tarih": str(d.index[-1].date()),
        "son_fark_mn_usd": float(fark.iloc[-1]),
        "son_pay": float(pay.iloc[-1]),
        "en_kucuk_fark": float(fark.min()),
        "birim": "mn USD",
    }
    if float(fark.min()) < 0:
        uy.append(
            "KAPSAM ÇELİŞKİSİ: yurt dışı yerleşikleri de kapsayan geniş "
            "toplam (TP.HPBITABLO4.1), yalnız yurt içi yerleşikleri kapsayan "
            f"toplamın (TP.HPBITABLO2.10) altına düşüyor; en büyük eksi fark "
            f"{b.sayi(float(fark.min()), 1)} milyon dolar. İki toplamın kapsamı "
            "değişmiş olabilir.")
    return uy, rapor


def hizalama_olc(H: pd.DataFrame, kaydirmalar=(-1, 0, 1)) -> dict:
    """Ayrıştırma kimliğinin HAFTA HİZALAMASINI ölçer — hüküm vermez.

    Kimlik şu: Δ stok(t) = arındırılmış değişim + parite etkisi. Ama 5.x'in
    hangi haftanın değişimini hangi Cuma'ya damgaladığı (aynı hafta mı, bir
    önceki mi) keşifte ÖLÇÜLMEDİ ve VARSAYILMAZ. Burada birkaç hizalama
    denenir ve hangisinin artığı kapattığı RAPORLANIR; hangisinin kullanılacağı
    ölçüm katmanının kararıdır ve o karar ancak ilk gerçek koşudan sonra
    verilebilir.

    Kaydırma k: Δ stok(t) ile (arındırılmış + parite)(t) karşılaştırılırken
    ayrıştırma serileri k hafta kaydırılır. k = 0 doğal okumadır (aynı Cuma).
    Ölçü, artığın MEDYAN mutlak değeridir: tek bir haftanın aykırı değeri
    hizalama seçimini belirlememeli.
    """
    out: dict = {}
    for etiket, (stok, ar, pe) in {
            "gercek": ("stok_gercek", "ar_gercek", "pe_gercek"),
            "tuzel": ("stok_tuzel", "ar_tuzel", "pe_tuzel")}.items():
        if not {stok, ar, pe} <= set(H.columns):
            continue
        dstok = H[stok].dropna().diff()
        top = (H[ar] + H[pe]).dropna()
        sonuc: dict = {}
        for k in kaydirmalar:
            d = pd.DataFrame({"a": dstok, "b": top.shift(k)}).dropna()
            if d.empty:
                continue
            artik = (d["a"] - d["b"]).abs()
            sonuc[str(k)] = {
                "n": int(len(d)),
                "medyan_mutlak_artik": float(artik.median()),
                "maks_artik": float(artik.max()),
                "birim": "mn USD",
            }
        if sonuc:
            en_iyi = min(sonuc, key=lambda k: sonuc[k]["medyan_mutlak_artik"])
            out[etiket] = {"kaydirmalar": sonuc, "en_kucuk_artik_kaydirma": en_iyi}
    return out


def olu_seri_olc(H: pd.DataFrame, pencere: int = SIFIR_BLOK_HAFTA) -> dict:
    """Sağ uçtaki tam sıfır bloğunun MAKİNE kaydı — okura cümle KURMAZ.

    Bir haftada parite etkisinin ya da bir para biriminin akımının sıfır
    çıkması GERÇEK bir ölçümdür ve boşaltılmaz — sıfırı silmek, ölçülebilen
    bir sıfırı yok saymak olurdu. İkisini ayıran şey sağ uçtaki sıfır bloğunun
    UZUNLUĞUDUR: pencerenin tamamı sıfırsa seri dolu görünüp bilgi taşımıyordur.

    NEDEN BURADA OKUR CÜMLESİ YOK — ve bu bir düzeltmedir. Aynı olay için
    burada da, ölçüm katmanında da uyarı basılıyordu ve ikisi ÇELİŞİYORDU:
    biri "bilgi taşımıyor" diye HÜKÜM veriyor, öteki tam da o hükmün
    verilemeyeceğini ("ikisi ayırt edilemiyor") söylüyordu. Üstelik pencereler
    ayrıydı (52 ve 26), yani okur aynı dört seri için aynı kutuda iki farklı
    hafta sayısı ve iki farklı hüküm görüyordu. Hüküm vermeyen sürüm doğru
    olandır ve ölçüm katmanında durur; burası yalnız makine kaydını yazar.
    Eşik de artık tek yerde: SIFIR_BLOK_HAFTA.

    Sıfırı NaN'a çevirmek gerekiyorsa ölçüm katmanında, TEK yerde yapılır.
    """
    olu: list[str] = []
    n_pencere = 0
    for ad in SIFIR_KAPSAMI:
        if ad not in H.columns:
            continue
        s_ = H[ad].dropna()
        if s_.empty:
            continue
        sonu = s_.iloc[-pencere:]
        if len(sonu) >= pencere and (sonu == 0).all():
            olu.append(ad)
            n_pencere = len(sonu)
    return {"pencere_hafta": int(pencere), "seri": olu,
            "olculen_hafta": int(n_pencere)}


# --------------------------------------------------------------------------- dönem
_SON: dict[str, str] = {}


def son_hafta(H: pd.DataFrame | None = None) -> pd.Timestamp:
    """Analizin çıpası: ÇEKİRDEĞİN TAMAMININ dolu olduğu son Cuma.

    Sabit tarih YASAK. Çekirdek seçimi kimliğin hesaplanabildiği haftayı
    verir (bkz. CEKIRDEK); bir hafta geriden gelen hiçbir bacak çekirdekte
    değildir, yoksa hattın saati her hafta bir hafta geriye düşerdi.
    """
    if "hafta" in _SON:
        return pd.Timestamp(_SON["hafta"])
    if H is None:
        H = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    cekirdek = [c for c in CEKIRDEK if c in H.columns]
    if not cekirdek:
        raise RuntimeError("son_hafta: çekirdek seriler hiç yüklenmemiş.")
    tam = H[cekirdek].dropna(how="any")
    if tam.empty:
        raise RuntimeError("son_hafta: çekirdek serilerin ortak dolu haftası yok.")
    _SON["hafta"] = tam.index[-1].strftime("%Y-%m-%d")
    return tam.index[-1]


# --------------------------------------------------------------------------- şekil saatleri
def _zaman(t) -> pd.Timestamp | None:
    """Defterin okuduğu her yazımı çözer: GG.AA.YYYY · AA.YYYY · ISO · Timestamp.

    Çözüm ortak/bicim'e devredilir. Kendi ayrıştırıcısını yazan bir bileşen bu
    depoda bir kez `AA.YYYY` yazımını tanımadı ve on beş anahtarın bayatlık
    denetimi SESSİZCE kapandı: ayrıştıramayan bir denetim hep "sorun yok" der.
    """
    if t is None or t == "":
        return None
    if isinstance(t, pd.Timestamp):
        return None if pd.isna(t) else t
    d = _bicim().tarihe_cevir(t)
    if d is not None:
        return pd.Timestamp(d)
    try:
        z = pd.Timestamp(t)
    except (ValueError, TypeError):
        return None
    return None if pd.isna(z) else z


def _en_eski(*adaylar) -> pd.Timestamp | None:
    """Karma figürün BAĞLAYICI bacağı: en eski uç.

    `min()` YAPISAL yazılır — bugün hangi bacağın önde olduğuna bakmaz.
    Gerekçe: figürün sözü serilerin KIYASIDIR ve kıyas ancak hepsinin ölçüldüğü
    güne kadar kurulabilir; en tazesini yazmak öbür bacağı olduğundan yeni
    gösterir.

    Bacaklardan biri HİÇ ölçülmemişse sonuç None'dır: ölçülmeyen bir ucun
    öbüründen yeni olduğu KANITLANAMAZ, yani seçilecek bir "en eski" yoktur.
    Yanlış bir tarih, tarihsizlikten kötüdür.
    """
    z = [_zaman(a) for a in adaylar]
    if not z or any(x is None for x in z):
        return None
    return min(z)


def sekil_saatleri(o: dict, uzun: bool = False) -> dict[str, str | None]:
    """Figür başına VERİ UCU — hattın tek ana saati değil.

    `o` = data/metrik_ozet.json sözlüğü. Değerler ÖLÇÜMDEN gelir, türetilmez:
    ölçüm katmanı her bloğun ortak tarihini oraya yazar, burası yalnız hangi
    figürün hangi bloğa bağlı olduğunu bilir.

    Neden burada: İKİ tüketicisi var — grafik.py figürün KENDİ alt başlığına
    yazar (uzun=True), ozet_uret.py sayfa damgası için deftere koyar. İki ayrı
    liste bir gün sessizce ayrışır ve okur aynı figürün İÇİNDE ve ALTINDA iki
    farklı tarih görür.

    Bu hatta iki ritim var ve ikisi de haftalık ama AYNI hafta bitmeyebilir:
    stok tabloları (bie_hpbitablo2 ve 4) ile değişim tablosu (bie_hpbitablo5)
    ayrı yayımlanıyor. Stok ile akımı BİRLİKTE çizen kimlik figürünün damgası
    bu yüzden ikisinin EN ESKİSİDİR.

    Ölçüm yoksa değer None kalır ve o şeklin altına tarih HİÇ basılmaz.
    """
    def yaz(t):
        z = _zaman(t)
        if z is None:
            return None
        return ad_gun(z) if uzun else z.strftime("%d.%m.%Y")

    stok = o.get("stok_tarih")
    akim = o.get("akim_tarih")
    dol = o.get("dol_tarih")
    return {
        # Stok ve kırılım: yalnız bie_hpbitablo2/4 bacağı çizilir.
        "01_stok_kirilim.html": yaz(stok),
        # Kümüle akım, ayrıştırma ve para birimi kırılımı: yalnız
        # bie_hpbitablo5. Stok bacağı bu figürlere hiç girmiyor, öyleyse onun
        # saati bu figürleri bağlamaz.
        "02_kumule_akim.html": yaz(akim),
        "03_ayristirma.html": yaz(akim),
        "04_para_cinsi.html": yaz(akim),
        # Kimlik figürü KARMA: Δ stok ile arındırılmış + parite yan yana.
        # SAAT YENİDEN TÜRETİLMEZ, ÖLÇÜLMÜŞ OLANI OKUNUR. Ölçüm katmanı bu
        # bloğun ortak haftasını zaten ölçüp `kimlik_tarih` diye yazıyor ve
        # çizim katmanı aynı anahtarı figürün KAPISI olarak kullanıyor. Burada
        # `min(stok, akım)` diye yeniden hesaplamak iki saati ayrıştırıyordu:
        # kaynak bir haftayı atladığında (ya da son gözlemi altı gün arayla
        # damgaladığında) Δ stok ölçülmemiş sayılıyor, figür bir hafta geriye
        # kadar çiziliyor, ama defter SON cumayı ilan ediyordu — ve çizim
        # katmanının uç denetimi doğru davranıp hattın TAMAMINI durduruyordu.
        # Çalışan beş figür ve özet de siteye gitmiyordu; yani kaynağın bir
        # haftayı atlaması, tasarımda açıkça hayatta kalınabilir sayılan bir
        # olay, bütün panoyu donduruyordu. Yayının önünde duran bir denetimin
        # yanlış alarmı arızanın kendisidir. Yedek yol (`_en_eski`) duruyor:
        # ölçüm katmanı bu bloğu hiç yazmamışsa figür tarihsiz kalmasın.
        "05_kimlik.html": yaz(o.get("kimlik_tarih")) or yaz(_en_eski(stok, akim)),
        # Dolarizasyon bloğu kendi ortak tarihine çıpalanır (TL ve YP bacakları
        # aynı tabloda ama ölçüm katmanı bloğu ortak tarihe demirler).
        "06_dolarizasyon.html": yaz(dol),
    }


# --------------------------------------------------------------------------- künye
def kunye_yaz() -> None:
    """Ağa ÇIKMADAN kataloğu basar (--yardim).

    Bir hattın ne çektiğini görmek için onu koşturmak gerekmemeli: ağa çıkan
    tek yol, ağa çıkmayan hiçbir sorunun cevabını vermemeli. Bu yol aynı
    zamanda modülün BETİK OLARAK koştuğunun sınamasıdır — derlenmesi, içe
    aktarılması ve koşması üç ayrı sınamadır ve ilk ikisi geçti diye üçüncüsü
    geçmez.
    """
    print("Yurt içi yerleşiklerin YP mevduatı — veri katmanı künyesi")
    print(f"  kaynak    : EVDS3 · {BASE}")
    print(f"  seri sayısı: {len(HAFTALIK)} (hepsi haftalık, Cuma damgalı)")
    print(f"  çekirdek  : {len(CEKIRDEK)} seri · asgari kapsam {ASGARI_HAFTA} hafta")
    print(f"  tolerans  : tazelik {tazelik_tolerans('haftalik')} · "
          f"kapsam {kapsam_tolerans('haftalik')} takvim günü "
          f"(ritim {AILE_RITIM_GUN['haftalik']} gün)")
    a = parca_aritmetigi()
    print(f"  çekim     : {a['sorulan_bas']} → bugün · {a['istek_satir']} satır "
          f"· {a['parca_sayisi']} parça · satır sınırı {a['satir_siniri']} "
          f"(tek parçanın dolmasına {a['kalan_hafta']} hafta)")
    print(f"  yoklama   : katalogdaki başlangıçtan {YOKLAMA_GUN} gün geriden "
          "sorulur; tarihçe uzarsa cevabın kendisi söyler")
    print("\n  KOD                  BAŞLANGIÇ   KANIT       BİRİM     AD")
    for ad, s in HAFTALIK.items():
        yildiz = "*" if ad in CEKIRDEK else " "
        # Başlangıcın ölçülüp ölçülmediği künyenin GÖRÜNEN parçasıdır: bir
        # sabitin ölçüm sanılması bu hatta beş kat tarihçe kaybettirdi ve
        # kaybın tek görünür işareti, kimsenin bakmadığı bir sabitti.
        kanit = s.bas_kanit if bas_olculdu(ad) else "ÖLÇÜLMEDİ"
        print(f"  {yildiz}{s.kod:<20} {s.bas}  {kanit:<10}  {s.birim:<8}  "
              f"{s.okur_adi}")
    print("\n  (* çekirdek: hattın saatini bu serilerin ortak dolu haftası verir)")
    print(f"  (KANIT: başlangıcın ölçüldüğü sorgunun alt sınırı — "
          f"{len(BAS_OLCULEN)}/{len(HAFTALIK)} seri ölçülmüş. Ölçülmemiş "
          "başlangıç taşıyan seri üzerine hüküm kurulmaz.)")
    print("\n  ŞEKİL SAAT DEFTERİ (anahtarlar; değerleri ölçüm katmanı doldurur)")
    for dosya, deger in sekil_saatleri({}).items():
        print(f"    {dosya:<26} {deger}")
    print("\n  ÇEKİLMEYEN KÜNYE — sepet bileşimi (birimi ölçülmeden kullanılmaz)")
    for kod, ne in SEPET_KUNYE.items():
        print(f"    {kod:<22} {ne}")
    print("\n  ÇEKİLMEYEN KÜNYE — tüketicisi olmadığı için kataloğa alınmayan")
    for kod, ne in CEKILMEYEN_KUNYE.items():
        print(f"    {kod:<22} {ne}")


# --------------------------------------------------------------------------- ana akış
def kimlik_dokumu(kim_rapor: dict) -> list[str]:
    """Kimlik kayıtlarının operatör dökümü — AĞSIZ, bu yüzden SINANABİLİR.

    Bu fonksiyon `kos()`un içinden ÇIKARILDI ve sebebi kayda değer: döngü
    `kim_rapor`ın TAMAMINI dolaşıp her kayıttan `n` ve `maks_fark` okuyordu,
    oysa `kimlik_denetimi` üç ayrı şekilde kayıt yazıyor — eşitlik kimliği
    (`maks_fark`), KAPSANMA kimliği (`maks_pay`, `maks_fark` YOK) ve
    sınanamadı dalları. İkinci tür kayıt eklendiği gün `kos()` her koşuda
    KeyError ile düşer, yani hattın BİRİNCİ adımı ölür ve ölçüm, çizim, özet
    hiç koşmaz.

    Kusuru bu kadar uzun yaşatan şey ölçümün kendisi değil, ÖLÇÜLEBİLİRLİĞİYDİ:
    `kos()` ağa çıkıyor, duman sınaması ağa çıkamıyor, dolayısıyla hattın giriş
    noktası HİÇ koşturulmuyordu. Derlenmesi, içe aktarılması ve KOŞMASI üç ayrı
    sınamadır (CLAUDE.md) ve burada üçüncüsü kimsenin bakmadığı yerdeydi.
    Ağ gerektirmeyen her parça, ağ gerektiren adımdan AYRILIR ki sınanabilsin.

    Kayıt türünü ALANLARINDAN tanır, adından değil: yeni bir kimlik türü
    eklendiğinde bu döngü düşmez, tanımadığı ölçüyü adıyla basar.
    """
    satirlar: list[str] = []
    for ad, r in kim_rapor.items():
        isaret = "?" if r.get("gecti") is None else ("✓" if r["gecti"] else "✗")
        n = r.get("n")
        n_yazi = f"n={n:>4}" if isinstance(n, int) else "n=   ?"
        if "maks_fark" in r:
            olcu = f"maks {r['maks_fark']:>12,.3f} {r.get('birim', '')}"
        elif "maks_pay" in r:
            # `maks_pay` ZATEN yüzde cinsindendir (61,5 = %61,5). İlk yazımda
            # yüzle çarpılıp %6.150 basıldı; birimi tahmin etmek yerine kaydın
            # kendi değerine bakmak gerekiyordu.
            olcu = f"maks pay {r['maks_pay']:>9,.3f}%"
        else:
            # Tanınmayan kayıt SESSİZCE ATLANMAZ: hangi ölçüyü taşıdığı yazılır.
            # Atlamak, bir kimliğin sınanmadığını sınanmış gibi göstermektir.
            bilinen = ", ".join(k for k in sorted(r) if k not in ("gecti", "n"))
            olcu = f"ölçü tanınmadı ({bilinen})"
        satirlar.append(f"    kimlik {isaret} {n_yazi}  {olcu}  ·  {ad}")
    return satirlar


def kos(yenile: bool = False) -> dict:
    print("EVDS3 → yurt içi yerleşiklerin YP mevduatı, veri katmanı")
    print(f"  anahtar: {'ortam değişkeni' if os.environ.get('TTO_EVDS_KEY') else 'dosya'}")

    H = cek_kume(HAFTALIK, "gun", PARCA_HAFTA_GUN, yenile, etiket="haftalık")

    # SIRA BAĞLAYICI: kapsam kapısı her şeyden ÖNCE. Yarım kalmış bir çekimden
    # ölçüm yapmak, yeşil bir koşunun içinde yanlış sayı yayımlamaktır.
    yeter, sebep = kapsam_yeterli(H)
    if not yeter:
        raise SystemExit(
            f"DUR: kapsam yetersiz — {sebep}. Haftalık çerçeve YAZILMADI ve "
            "depodaki sürüme dokunulmadı; hattın sonraki adımları koşmaz. "
            "Eksik kapsamla üretilen bir pano, hiç pano olmamasından kötüdür.")

    kapsam = kapsam_olc(H)
    s_hafta = son_hafta(H)
    print(f"  SON HAFTA: {ad_gun(s_hafta)} (Cuma)")

    # ÇERÇEVEDEN TÜRETİLEN UYARILAR TEK ÇAĞRIDA. Ölçüm katmanı da AYNI
    # fonksiyonu kendi okuduğu çerçeveyle çağırıyor; iki katman aynı soruyu
    # aynı sırayla soruyor ve devralınan bayat bir kayıt onların yerini
    # alamıyor (bkz. `cerceve_uyarilari`).
    for u in cerceve_uyarilari(H):
        uyar(u)
    # Raporlar AYRICA alınır: koşu kaydına giren ayrıntı uyarı cümlesinden
    # zengin (bacak bacak artık, kapsam farkının payı ve tarihi). Cümleler
    # yukarıda zaten basıldı; `uyar` tekilleştirdiği için ikinci kez düşmez.
    _, kim_rapor = kimlik_denetimi(H)
    _, yd_rapor = genis_fark_olc(H)
    # ÖLÜ SERİ yalnız MAKİNE kaydına yazılır: okura giden cümle ölçüm
    # katmanında, tek yerde kuruluyor (bkz. olu_seri_olc gerekçesi).
    olu = olu_seri_olc(H)
    hizalama = hizalama_olc(H)

    H.to_csv(VERI / "haftalik.csv")
    # Uyarı cümleleri okur için TOPLANIYOR; ölçümün kendisi burada SERİ SERİ
    # duruyor. Toplamak bilgiyi atmak değil, okura tek olay olarak göstermek —
    # ayrıntıyı arayan koşu kaydında bulur.
    durum = {
        "kosum": dt.date.today().isoformat(),
        "son_hafta": s_hafta.strftime("%Y-%m-%d"),
        "haftalik": [int(H.shape[0]), int(H.shape[1])],
        # KAYIT, ANLATTIĞI ÇERÇEVEYİ ADIYLA TAŞIR. Ölçüm katmanı bu künyeyi
        # kendi okuduğu çerçeveyle karşılaştırıyor; tutmuyorsa kaydın
        # uyarılarını devralmıyor ve bunu görünür kılıyor.
        "cerceve_imza": cerceve_imza(H),
        # Çekim penceresinin aritmetiği kayda GİRER: "sığdı mı" sorusunun
        # cevabı bir yorum satırında yaşlanmasın, her koşuda yeniden ölçülsün.
        "parca": parca_aritmetigi(),
        "kapsam": kapsam,
        "bosluk": bosluk_olc(H),
        "tazelik": tazelik_olc(H),
        "kimlik": kim_rapor,
        "genis_fark": yd_rapor,
        "hizalama": hizalama,
        "olu_seri": olu,
        "uyarilar": list(_UYARI),
    }
    (VERI / "veri_durum.json").write_text(
        json.dumps(durum, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazıldı: data/haftalik.csv ({H.shape[0]}x{H.shape[1]})")

    # Aşağıdaki dökümdeki sayılar BİLEREK ortak/bicim'den geçmiyor: bu satırlar
    # koşu kütüğüne düşen OPERATÖR tanısıdır, okura hiçbir yerden basılmaz, ve
    # sabit genişlikli hizalama dokuz kimlik satırının büyüklüklerini yan yana
    # okunur kılıyor. Okura giden her satır (uyar() şablonları) biçimi
    # ortak/bicim'den yazar; ayrım burada yazılı ki bir sonraki oturum bu
    # kalıbı bir uyarı şablonuna kopyalamasın.
    for satir in kimlik_dokumu(kim_rapor):
        print(satir)
    if yd_rapor:
        print(f"    kapsam farkı (geniş toplam − yurt içi toplam): "
              f"{yd_rapor['son_fark_mn_usd']:,.1f} mn USD "
              f"({yd_rapor['son_pay'] * 100:.1f}% pay, {yd_rapor['son_tarih']})")
    for etiket, r in hizalama.items():
        print(f"    hizalama [{etiket}] artığı en küçük kaydırma: "
              f"{r['en_kucuk_artik_kaydirma']} hafta")
        for k, v in r["kaydirmalar"].items():
            print(f"      k={k:>2}: n={v['n']:>4}  medyan artık "
                  f"{v['medyan_mutlak_artik']:>10,.2f} mn USD")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return durum


if __name__ == "__main__":
    if "--yardim" in sys.argv:
        kunye_yaz()
    else:
        kos(yenile="--yenile" in sys.argv)
