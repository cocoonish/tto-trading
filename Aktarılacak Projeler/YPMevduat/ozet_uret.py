# -*- coding: utf-8 -*-
"""Yurt içi yerleşiklerin YP mevduatı — ozet.json üretimi.

Sayfa metnindeki OYNAK her sayı buradan beslenir (CLAUDE.md kural 5):
MDX'te <Deger proje="yp-mevduat" anahtar="…" ondalik={1}>statik yedek</Deger>.
Tarihsel ve yöntemsel sabitler (kimliğin türetimi, kaynak künyesi, doğrulama
örnekleri) sayfada STATİK kalır — onlar veri tazelendikçe değişmez.

Bütün değerler ölçüm katmanının ÜRETTİĞİ dosyalardan okunur; bu dosyada elle
yazılmış tek bir sayı yoktur. Bir değer kaynakta yoksa anahtar ATLANIR ve
gerekçesi hata akışına basılır: eksik bir sayının yerine sayfadaki statik yedek
görünür, uydurulmuş bir değer değil.

DÖRT SÖZLEŞME — dördü de bir gün gerçekten yanlış yayımlanmış bir sayıdan doğdu:

1. `_tarih` HATTIN EN YENİ CANLI BACAĞIDIR, çıpası değil. Ölçüm katmanı dört
   blok saati yazıyor (stok · akım · kimlik · dolarizasyon) ve bunlar aynı
   cumada bitmeyebiliyor. Çıpa (`son_hafta`) çekirdeğin TAMAMININ dolu olduğu
   haftadır, yani blokların EN ESKİSİ; onu hattın saati yapmak, ilerlemiş bir
   bloğu donmuş göstermek olurdu. Sayfa sınavının özet saati ölçütü tam bunu
   arıyor: `_tarih`, canlı bacakların en yenisinden geride kalırsa hattın saati
   geride kalmış sayılır.

2. HER DEĞERİN KENDİ SAATİ VAR. Bir özet tek bir yayım ritmi taşımaz; bu hatta
   stok tabloları ile resmî ayrıştırma tablosu ayrı yayımlanıyor. Sayfa
   bileşeni sırayla `<anahtar>_tarih` → `_tarih` diyor, yani saat anahtarı
   DEĞERİN anahtarına birebir eklenmelidir. Yanlış adla yazılan bir saat
   sessizce hattın ana saatine düşer ve okura HİÇ ulaşmaz. Bu yüzden saat
   burada elle değil, `blok_ad()` kuralıyla otomatik fanlanıyor ve dosyanın
   sonunda "saati olmayan sayı" denetimi koşuyor: kapsam bir listeden değil
   kuralın kendisinden türer, yoksa yarın eklenen bir anahtar sessizce
   saatsiz kalır ve bakılmayan yer geçen sınavla aynı görünür.

3. ŞEKİL SAAT DEFTERİ BURADA KURULMAZ, OKUNUR. Defter veri katmanında tek
   yerde duruyor; çizim katmanı figürün KENDİ alt yazısı için, bu dosya sayfa
   damgası için AYNI fonksiyonu çağırır. İki liste tutulsaydı bir gün sessizce
   ayrışır ve okur aynı figürün İÇİNDE ve ALTINDA iki farklı tarih görürdü.
   Dürüstçe tek gün seçilemeyen figürün değeri None kalır — sayfa o şeklin
   altına tarih HİÇ basmaz, çünkü yanlış bir tarih tarihsizlikten kötüdür.

4. MANŞET YURT İÇİ YERLEŞİKLERDİR: `stok_toplam_mia` (kaynağın TP.HPBITABLO2.10
   kalemi, milyar dolar), saati `stok_toplam_mia_tarih`. Kaynağın geniş toplamı
   (TP.HPBITABLO4.1) yurt dışı yerleşik bankaları da kapsar ve manşet olarak
   KULLANILMAZ; bu sayfada yalnız adıyla ve farkıyla geçer (`genis_toplam_mia`,
   `genis_fark_mia`, `genis_fark_pay`, `genis_fark_cumlesi`). İki toplamı aynı
   şeymiş gibi yan yana koymak bu hattın en pahalı hatası olurdu — biri
   ötekinden yaklaşık kırk milyar dolar büyük. Anahtar adları FARKI adlandırır,
   farkın İÇİNDEKİNİ değil: künyenin kalem numaralandırmasına göre fark üç
   bölümü birden kapsıyor ve yurt dışı yerleşik bankalar yalnız biri. Adı
   `yurtdisi_mia` olsaydı sayfayı yazan bir sonraki oturum ölçülmemiş bir
   cümle kurardı.

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import datetime as dt
import json
import re
import sys

import pandas as pd

import veri
from veri import PROJE, VERI, ad_gun, sekil_saatleri, tazelik_tolerans

O: dict = {}
_ATLANAN: list[str] = []
# Blok saatleri: {blok adı → o bloğun ortak cuması}. Ana akış dolduruyor,
# `olc()` her değerin saatini buradan fanlıyor. Modül düzeyinde duruyor ki
# saat, değeri yazan çağrının ARGÜMANI olmasın: bir çağrı yerinde unutulan
# argüman, sessizce saatsiz kalan bir sayı demektir.
_SAAT: dict[str, pd.Timestamp] = {}


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı.

    Ondalık virgül, binlik nokta, eksi U+2212, yüzde işareti sayıdan ÖNCE.
    Kardeş hatların özet üreticileri bu işi yapan YEREL bir yardımcı taşıyor;
    o bir borçtur ve kopyalanmadı: aynı sözleşmenin iki tanımı bir gün sessizce
    ayrışır ve hangisinin neyi yazdığı kimsenin aklında kalmaz.

    Yedek yol, hattın klasöründen ELLE koşulduğu hâl içindir: koşu kütüğü
    çocuk sürecin arama yoluna ortak dizini ekliyor, ama elle koşan bir kabuk
    eklemiyor.
    """
    try:
        import bicim
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


def _okur_dili():
    """ortak/okur_dili — koşu kaydının ve özet cümlelerinin süzgeci.

    Bulunamazsa None döner ve denetim ATLANIR: bu dosya bir yayın kapısı
    değildir, kapı sayfa sınavındadır. Ama kusuru burada, hat koşarken görmek
    yayının önünde bulmaktan ucuzdur.
    """
    try:
        import okur_dili
    except ImportError:
        try:
            import pathlib as _pl
            import sys as _sys
            _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
            import okur_dili
        except ImportError:
            return None
    return okur_dili


def uyar(m: str) -> None:
    """OPERATÖR uyarısı — hata akışına. Okura giden metin değildir.

    Ayrım bilerek keskin: bu satırlar koşu çıktısında kalır, okur kaydına
    (uyarilar.json) girmez. Okura giden uyarılar ölçüm katmanında yazılıyor ve
    oradan devrediliyor; burada yalnız "şu anahtar kaynakta yok" gibi yapım
    bilgisi var ve o bilgi sayfada işe yaramaz.
    """
    print(f"UYARI: {m}", file=sys.stderr)


def koy(anahtar: str, deger, ondalik: int | None = 2) -> None:
    """Bir değeri özete yazar; ölçülemeyeni ATLAR.

    None ya da NaN gelirse anahtar hiç yazılmaz: sayfadaki statik yedek
    görünür. Sıfır yazmak ya da "—" yazmak İKİSİ DE yanlış olurdu — sıfır bir
    ölçüm sonucudur ve ölçülemeyen bir şeyi sıfır diye yayımlamak okura
    "ölçtük, sonuç sıfır" demektir.
    """
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        _ATLANAN.append(anahtar)
        # YAPISAL OLARAK EKSİK KALABİLEN ANAHTAR SİLİNMEZ, BOŞ YAZILIR.
        # Sayfa bileşeni `null`ı "ölçülmedi" diye okuyup statik yedeği yerinde
        # bırakıyor — yani okur açısından atlamakla aynı — ama sayfa sınavının
        # birinci ölçütü için anahtar VARDIR. O ölçüt "ozet.json'da olmayan
        # anahtar" bulduğunda ENGEL üretir ve HER hatta kapıdır: kaynağın bir
        # bacağı yayımlamadığı bir koşuda SİTENİN TAMAMININ yayını dururdu.
        # Ölçüldü: lira bacakları yüklenemediğinde özetten yirmi anahtar birden
        # düşüyor. Sınavda "isteğe bağlı anahtar" kavramı yok, öyleyse sözleşme
        # burada sabitlenir — ve sabitlenmesi bir sayı uydurmak DEĞİLDİR:
        # `null` "ölçülmedi" demenin ta kendisi.
        if istege_bagli(anahtar):
            O[anahtar] = None
        uyar(f"'{anahtar}' kaynakta yok — değer boş bırakıldı.")
        return
    if ondalik is None:
        O[anahtar] = deger
    elif ondalik == 0:
        O[anahtar] = int(round(float(deger)))
    else:
        O[anahtar] = round(float(deger), ondalik)


# ===========================================================================
# BLOK SAATLERİ — hangi anahtar hangi bloğun haftasına ait?
# ===========================================================================
# Ölçüm katmanı dört blok saati yazıyor. Aşağıdaki kural, bir anahtarın hangi
# bloğa ait olduğunu ADINDAN türetir; elle tutulan bir eşleme listesi
# tutulmadı, çünkü bu depoda elle tutulan her liste bir gün eksik kaldı ve
# eksik kalan yer geçen sınavla aynı göründü. Kural tutmazsa dosyanın sonundaki
# denetim o anahtarı ADIYLA basar.
BLOK_KURAL = (
    # Stok değişimi ve kimlik artığı İKİ TABLODAN birden geliyor (stok tablosu
    # ile ayrıştırma tablosu), yani kendi saatleri var ve o saat ikisinin en
    # eskisidir. Ölçüm katmanı bunu ayrı bir blok olarak ölçüyor.
    (re.compile(r"^(delta_|kimlik_artik_)"), "kimlik"),
    # Haftalık akım, kümüle akım ve gerçek–tüzel ayrışması yalnız resmî
    # ayrıştırma tablosundan geliyor. Pencere adı sayıyla yazılıyor (dört ve
    # on üç haftalık) ve pencere değişirse kural onu da tanısın diye kalıp
    # sayıyı serbest bırakıyor.
    (re.compile(r"^(ar_|pe_|ayrisma_)"), "akim"),
    (re.compile(r"^kum_(ay|yil|\d+h)_"), "akim"),
    # BÜTÜN ÖRNEKLEM toplamları da yalnız ayrıştırma tablosundan geliyor ve
    # `sifir_` gibi SAATSİZ değiller: bir toplamın son haftası, toplandığı
    # pencerenin sağ ucudur ve her hafta ilerler. Saati akım bloğunun saatidir.
    # (`tum_bas` ve `tum_son` pencerenin kendi uçları, sayı değil — onlar
    # zaten `koy` yolundan tarih olarak yazılıyor.)
    (re.compile(r"^tum_"), "akim"),
    # Dolarizasyon payı mevduatın LİRA karşılığından hesaplanıyor; ölçüm
    # katmanı onu kendi ortak haftasına çıpalıyor.
    (re.compile(r"^(dol_|mevduat_)"), "dol"),
    # Stok, kırılım ve paylar.
    (re.compile(r"^(stok_|maden_|genis_|gercek_pay|tuzel_pay)"), "stok"),
)

# SAATİ OLMAYAN SAYILAR — bilinçli ve gerekçeli liste.
# Bunlar bir haftaya ait ÖLÇÜM değil; ya koddan gelen yöntem sabitleri ya da
# koşunun kendi kaydı. Bir saat eklemek okura "bu eşik o hafta ölçüldü"
# demek olurdu.
SAATSIZ = {
    "kimlik_esik_mn", "kimlik_esik_pay", "kimlik_pencere_hafta",
    "kimlik_kaydirma", "kum_pencere_kisa_hafta", "kum_pencere_uzun_hafta",
    "uyari_sayisi", "bayat_tolerans_gun", "beklenen_yayim_gecikme_gun",
    "veri_gecikme_gun", "atlanan_olcum_sayisi",
}
# ÖNEKLER — bir HAFTAYA değil, ÇERÇEVENİN TAMAMINA ait ölçümler.
#   · `sifir_`  — sıfır sınıflaması bütün tarihçe üzerinde yapılıyor: kaç seri
#     hangi sınıfa düştü, etkilenen dilimin haftalık medyanı… Bunlara son
#     haftanın damgasını vurmak okura "bu sınıflandırma o hafta ölçüldü"
#     demektir; oysa ölçünün penceresi serinin tamamı.
#   · `kapsam_` — iki tablonun başlangıcı ve pencere uzunlukları; tanımı gereği
#     tarihçenin BAŞINA dair, sağ ucun haftasıyla ilgisi yok.
#   · `bayat_`  — koşunun kendi kaydı (tolerans, sebep sayısı), ölçüm değil.
SAATSIZ_ONEK = ("gecikme_", "sifir_", "kapsam_", "bayat_")

# Blokların OKUR adları VERİ KATMANINDA, tek yerde. Burada ikinci bir tablo
# tutuluyordu ve ölçüm katmanınınkiyle daha ilk günden ayrışmıştı: aynı sayfada
# aynı kutuya biri "akım" yazıyordu, öteki "resmî ayrıştırma tablosu" — okur
# ikisinin aynı şey olduğunu bilemezdi ve "blok" zaten bu hattın ölçüm
# mimarisine ait, okurun elinde karşılığı olmayan bir kavramdı.
BLOK_OKUR = veri.BLOK_OKUR

# Kaynak, referans cumayı izleyen PERŞEMBE yayımlıyor (Haftalık Para ve Banka
# İstatistikleri). Yayım günü buradan türetilir; tolerans ise veri katmanından
# okunur (`tazelik_tolerans`) — eşik iki yerde ayrı yazılsaydı biri güncellenir,
# öteki unutulurdu.
#
# BURADAN ÇIKAN GÜN BEKLENENDİR, ÖLÇÜLMÜŞ DEĞİL — ve anahtar adları da öyle
# yazılır (`beklenen_yayim_*`). Hesap yalnız takvim aritmetiğidir: referans
# cuma artı altı gün, hafta sonuna düşerse izleyen ilk iş gününe kayar. Resmî
# tatili GÖRMEZ; kaynak bayram arifesi yüzünden bir gün geç yayımlarsa sayfa
# hiç gerçekleşmemiş bir yayım günü ilan eder ve hiçbir denetim bunu yakalayamaz,
# çünkü ölçülen değil ilan edilen bir şeydir. Anahtarları "yayim_tarihi" diye
# yazmak, okura ölçülmüş bir gün gibi görünürdü. Kaynağın resmî yayım takvimine
# bağlanana kadar sayfada karar bu ölçüye dayandırılmaz; bayatlık hükmü ÖLÇÜLEN
# `veri_gecikme_gun`den kurulur.
YAYIM_GUN = 6


# YAPISAL OLARAK EKSİK KALABİLEN ANAHTARLAR — sayfaya <Deger> ile BAĞLANMAZ.
#
# `koy()` ölçülemeyen anahtarı bilinçli olarak ATLIYOR: sayfada statik yedek
# görünsün, uydurulmuş bir sayı değil. Ama sayfa sınavının birinci ölçütü
# "ozet.json'da olmayan anahtar" bulduğunda ENGEL üretir ve o kural HER hatta
# kapıdır — yani MDX bu anahtarlardan birini çağırırsa, kaynağın o bacağı
# yayımlamadığı bir koşuda SİTENİN TAMAMININ yayını durur. Sınavda "isteğe
# bağlı anahtar" kavramı yok, öyleyse sözleşme burada sabitlenir ve özete
# yazılır: aşağıdaki aileler bir koşuda ölçülüp öbüründe ölçülmeyebilir.
#
# Ölçüldü: lira bacakları yüklenemediğinde özet 217 anahtardan 197'ye düşüyor
# ve dolarizasyon ailesinin tamamı (yirmi anahtar) kayboluyor. Aynı risk
# "diğer para birimleri" bacaklarında var — kaynak o kalemi yayımlamayı
# bırakırsa üç anahtar birden düşer.
#
# Bu aileler sayfada CÜMLE ile anlatılır (`dol_cumlesi` gibi, kendisi de
# isteğe bağlı ve ölçülemediğinde hiç yazılmayan bir alan), sayı olarak
# <Deger>'e bağlanmaz.
ISTEGE_BAGLI = (
    re.compile(r"^(dol_|mevduat_)"),          # payın lira bacakları eksik olabilir
    re.compile(r"_diger_mn(_tarih)?$"),       # kaynak bu bacağı yayımlamayabilir
    re.compile(r"^gecikme_dol_"),             # bloğu yoksa gecikmesi de yok
    # Takvime bağlı kümüleler: bir akım serisinin TEK haftası boş geldiğinde o
    # grubun geri kalanı ölçülemez olur (ölçülmemiş bir haftadan sonrası da
    # ölçülemez) ve değer yazılmaz. Sabit pencereler aynı sebeple boş kalabilir.
    re.compile(r"^kum_(ay|yil|\d+h)_"),
    # SINIFI BOŞ OLAN ÖLÇÜM. Dayanaksız sıfır sınıfına hiçbir bacak
    # düşmediğinde o sınıfın kese ve dilim ölçüleri YOKTUR — ölçülemedikleri
    # için değil, ölçülecek bir konu olmadığı için. Anahtar `null` yazılır
    # (sayfa sınavının birinci ölçütü onu bulsun) ama ATLANAN ÖLÇÜM
    # SAYILMAZ: sayılsaydı sınıfın boş olduğu her koşuda sayfa kendini bayat
    # ilan ederdi. Ayrımı `konusuz()` taşıyor.
    re.compile(r"^sifir_dayanaksiz_(hafta|kiyas_(dolu|kapsam)|kese_zayif)"),
    # MANŞET SINIRI: sınıftan bağımsız ölçülür ama konusu olmayabilir —
    # parite etkisi hiç yayımlanmayan bacak yoksa dilim de yoktur.
    re.compile(r"^sifir_sinir_(dilim|manset)"),
    re.compile(r"^sifir_hukumsuz_hafta$"),
)


def istege_bagli(anahtar: str) -> bool:
    """Bu anahtar bir koşuda hiç yazılmayabilir mi?"""
    return any(k.search(anahtar) for k in ISTEGE_BAGLI)


def blok_ad(anahtar: str) -> str | None:
    """Bir özet anahtarının bağlı olduğu ölçüm bloğu; bilinmiyorsa None."""
    for kalip, blok in BLOK_KURAL:
        if kalip.match(anahtar):
            return blok
    return None


def _is_gunu(t: dt.date) -> dt.date:
    """Hafta sonuna düşen bir yayım günü, izleyen ilk iş gününe kayar."""
    while t.weekday() >= 5:
        t += dt.timedelta(days=1)
    return t


def beklenen_yayim_gunu(cuma: pd.Timestamp) -> dt.date:
    """Bir referans cumanın BEKLENEN yayım günü — takvim aritmetiğinden.

    Ölçüm değildir: resmî tatili görmez (bkz. YAYIM_GUN gerekçesi).
    """
    return _is_gunu((pd.Timestamp(cuma) + pd.Timedelta(days=YAYIM_GUN)).date())


def _saatler(m: dict) -> dict[str, pd.Timestamp]:
    """Ölçüm katmanının yazdığı blok saatleri → {blok: cuma}.

    Yazılmamış bir blok BURADA YOK sayılır (uydurulmaz): o bloğun anahtarları
    zaten özete girmemiştir ve şekil defteri de o figürü tarihsiz bırakır.
    """
    b = _bicim()
    out: dict[str, pd.Timestamp] = {}
    for blok in ("stok", "akim", "kimlik", "dol"):
        d = b.tarihe_cevir(m.get(f"{blok}_tarih"))
        if d is not None:
            out[blok] = pd.Timestamp(d)
    return out


def olc(anahtar: str, deger, ondalik: int | None = 2,
        saat: str | None = None) -> None:
    """Bir ÖLÇÜMÜ yazar ve saatini kendi anahtarına fanlar.

    `saat` verilmezse blok kuralından türetilir. Açık `saat` yalnız bloğundan
    farklı bir güne ait değerler içindir (çıpadaki pay gibi: onun saati bloğun
    haftası değil, çıpanın kendi günüdür).
    """
    koy(anahtar, deger, ondalik)
    # Boş yazılan (ölçülemeyen) bir anahtara SAAT konmaz: saat, o değerin hangi
    # haftaya ait olduğunu söyler ve ölçülmemiş bir değerin haftası yoktur.
    if O.get(anahtar) is None:
        return
    if saat is not None:
        O[f"{anahtar}_tarih"] = saat
        return
    blok = blok_ad(anahtar)
    if blok is None:
        return                      # dosyanın sonundaki denetim bunu basar
    t = _SAAT.get(blok)
    if t is not None:
        O[f"{anahtar}_tarih"] = t.strftime("%d.%m.%Y")


def konusuz(anahtar: str, deger, ondalik: int | None = 2) -> None:
    """ÖLÇÜLECEK KONUSU OLMAYAN bir değeri yazar — ATLANAN ölçüm saymadan.

    `koy()` ile arasındaki fark, bu depoda bir kez pahalıya mal olmuş bir
    ayrımdır: "ölçemedik" ile "ölçülecek bir şey yoktu" aynı görünür ama aynı
    şey değildir. Dayanaksız sıfır sınıfına hiçbir bacak düşmediğinde o
    sınıfın kese ve dilim ölçüleri boştur — kaynak bir şeyi yayımlamadığı
    için değil, sorunun konusu olmadığı için. `koy()` bunları atlanan ölçüm
    sayardı ve atlanan ölçüm sayısı BAYATLIK HÜKMÜNE giriyor: sınıfın boş
    olduğu her koşuda sayfa kendini bayat ilan ederdi — yani en sağlıklı
    hâlinde alarm çalardı.

    Anahtar yine de YAZILIR (`null`): sayfa sınavının birinci ölçütü onu
    bulmalı, ve `null` "ölçülmedi" demenin ta kendisidir.
    """
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        O[anahtar] = None
        return
    koy(anahtar, deger, ondalik)


def _saatsiz_denetimi() -> list[str]:
    """Saati olmayan SAYI anahtarları — kapsam denetiminin kendisi.

    Bu ölçüt doğru olduğu kadar NEYİ GÖRMEDİĞİ de sorulmuş olsun diye var:
    yarın eklenen bir anahtar blok kuralına uymazsa saatsiz kalır, sayfa onu
    hattın ana saatiyle etiketler ve donmuş bir sayı taze görünür. Kusur göze
    çarpmaz — ama burada adıyla görünür.
    """
    eksik = []
    for a, d in O.items():
        if a.startswith("_") or a.endswith("_tarih"):
            continue
        if not isinstance(d, (int, float)) or isinstance(d, bool):
            continue
        if a in SAATSIZ or a.startswith(SAATSIZ_ONEK):
            continue
        if f"{a}_tarih" not in O:
            eksik.append(a)
    return eksik


def _cumle_denetimi() -> list[str]:
    """Özetin CÜMLE alanlarını okur dili süzgecinden geçirir (bilgi amaçlı).

    Kapı burada DEĞİL, sayfa sınavındadır; burada yalnız görünür olur.
    Gerekçe: yayının önünde duran bir denetimin yanlış alarmı arızanın
    kendisidir — bu depoda bir kez bir kapı siteyi on iki saat durdurdu. Ama
    kusuru hat koşarken görmek, yayın kapısında görmekten ucuz.
    """
    od = _okur_dili()
    if od is None:
        return []
    cumleler = od.ozet_cumleleri(O)
    bulgu = []
    for alan, metin in cumleler:
        for _, aile, esl in od.kosu_kaydi_tara([metin]):
            if aile in od.KOSU_KAYDI_ENGEL:
                bulgu.append(f"{alan}: {aile} — {esl!r}")
    return bulgu


# KOŞU KAYDI CÜMLESİNİN SÖZLEŞMESİ — ÖLÇÜLÜR, VARSAYILMAZ.
#
# Kural (bkz. metrik.SINIF_BOS'un üstündeki gerekçe): bir koşu kaydı cümlesi
# EN ÇOK İKİ cümle ve TEK bir ölçümden beslenir. Bir kural yalnız rehbere
# yazıldığında bir sonraki oturum onu bilmez; burada sayılıyor ve aşan anahtar
# ADIYLA basılıyor.
#
# ÖLÇÜNÜN TANIMI, YANLIŞ ALARM ÜRETMEYECEK BİÇİMDE:
#   · Cümle sınırı, ardından BOŞLUK ya da satır sonu gelen nokta/soru/ünlemdir.
#     Seri künyesi (TP.HPBITABLO5.14), ondalık virgül ve tarih yazımı
#     (28.02.2014) noktadan sonra boşluk taşımaz, yani sınır sayılmazlar.
#   · Sayı sayılırken PARANTEZ İÇİ atılır: parantez okurun kaynakta
#     arayabileceği künyeyi taşır, bizim ölçümümüzü değil.
#   · "ve N seri daha" da atılır: o bir ad listesinin kırpılma işareti,
#     ikinci bir ölçüm değil — `veri._adlar` uzun listeyi böyle kapatıyor.
CUMLE_SINIRI = re.compile(r"[.!?](?:\s|$)")
KUNYE_PARANTEZ = re.compile(r"\([^)]*\)")
AD_KIRPMA = re.compile(r"\bve \d+ seri daha\b")
SAYI_IZI = re.compile(r"\d[\d.,]*")
CUMLE_TAVAN = 2
SAYI_TAVAN = 1
# UYARI LİSTESİ BİR CÜMLE DEĞİL, BİRLEŞTİRMEDİR. `uyari_metni` bağımsız uyarı
# satırlarını " · " ile yan yana koyar; her satır kendi kaydıdır ve sözleşme
# satırların KENDİSİNE uygulanır (aşağıda ayrıca sayılıyor), birleşmiş hâline
# değil. Muafiyet olmasaydı iki uyarı düşen her koşu bu ölçütü düşürürdü.
CUMLE_OLCUSU_MUAF = {"uyari_metni"}


def cumle_olcusu(metin: str) -> tuple[int, int]:
    """Bir okur metninin (cümle sayısı, ölçüm sayısı) ölçüsü."""
    t = str(metin or "")
    cumle = len([x for x in CUMLE_SINIRI.split(t) if x.strip()])
    sade = AD_KIRPMA.sub(" ", KUNYE_PARANTEZ.sub(" ", t))
    return cumle, len(SAYI_IZI.findall(sade))


def _cumle_olcusu_denetimi(satirlar=()) -> list[str]:
    """Sözleşmeyi aşan okur metinleri → ["alan: 4 cümle · 5 ölçüm", …].

    Kapsam bir listeden değil SÖZLEŞMEDEN türer: özetin okura basılan cümle
    alanları `okur_dili.ozet_cumleleri` ile, koşu kaydının uyarı satırları da
    olduğu gibi. Elle tutulan bir alan listesi bir gün eksik kalır ve eksik
    kalan yer geçen sınavla aynı görünür.
    """
    bulgu: list[str] = []
    od = _okur_dili()
    alanlar = (od.ozet_cumleleri(O) if od is not None else
               [(a, d) for a, d in sorted(O.items())
                if isinstance(d, str) and " " in d and len(d) >= 40])
    for ad, metin in alanlar:
        if ad in CUMLE_OLCUSU_MUAF:
            continue
        c, n = cumle_olcusu(metin)
        if c > CUMLE_TAVAN or n > SAYI_TAVAN:
            bulgu.append(f"{ad}: {c} cümle · {n} ölçüm")
    for i, satir in enumerate(satirlar, 1):
        c, n = cumle_olcusu(satir)
        if c > CUMLE_TAVAN:
            bulgu.append(f"koşu kaydı {i}. satır: {c} cümle")
    return bulgu


def main() -> int:
    b = _bicim()
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))

    # Koşu kaydı ve veri katmanı durumu. İkisi de okunamazsa hat yine yazılır
    # ama uyarı sayısı EKSİK olur; sessizce sıfır yazmak yerine hata akışına
    # sebebiyle birlikte basılıyor.
    try:
        uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        uyar(f"koşu kaydı okunamadı ({type(ex).__name__}) — uyarı listesi eksik.")
        uy = {}
    try:
        vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        uyar(f"veri katmanının kaydı okunamadı ({type(ex).__name__}) — "
             "onun uyarıları sayıma girmiyor.")
        vd = {}

    # ------------------------------------------------------------ saatler
    global _SAAT
    _SAAT = _saatler(m)
    cipa = b.tarihe_cevir(m.get("son_hafta"))

    # HATTIN SAATİ: canlı bacakların EN YENİSİ. Çıpa (kimliğin hesaplanabildiği
    # hafta) blokların en eskisidir ve onu hattın saati yapmak ilerlemiş bir
    # bloğu donmuş gösterirdi.
    if _SAAT:
        ana = max(_SAAT.values())
    elif cipa is not None:
        ana = pd.Timestamp(cipa)
        uyar("blok saati hiç yazılmamış; hattın saati çıpadan alındı.")
    else:
        # Saatsiz bir özet, sayfa sınavının özet saati ölçütünü DÜŞÜRÜR ve
        # yayını durdurur. Yanlış bir tarih uydurmaktansa adım burada düşer:
        # bozuk bir özet, hiç özet olmamasından kötüdür.
        raise SystemExit(
            "DUR: ölçüm katmanı ne blok saati ne çıpa yazmış; hattın saati "
            "kurulamıyor ve tarihsiz bir özet yayına giremez.")

    O["_tarih"] = ana.strftime("%d.%m.%Y")
    O["hat_saati_blok"] = BLOK_OKUR.get(
        next((k for k, v in _SAAT.items() if v == ana), ""), "")

    # ------------------------------------------------------------ dönem
    if cipa is not None:
        c = pd.Timestamp(cipa)
        O["hafta"] = ad_gun(c)
        O["hafta_kisa"] = c.strftime("%d.%m.%Y")
        O["onceki_hafta"] = ad_gun(c - pd.Timedelta(weeks=1))
    for blok, t in _SAAT.items():
        # İki yazım, iki iş: kısa yazım SAATTİR (sayfa damgası, şekil
        # bağlantısı, bayatlık denetimi), uzun yazım okur cümlesinin içine
        # girer. Aynı günü iki biçimde yazmak tekrar değil; tek biçim yazsaydık
        # ya cümlede tarih rakamlaşırdı ya da denetim ayrıştıramazdı.
        O[f"{blok}_tarih"] = t.strftime("%d.%m.%Y")
        O[f"{blok}_hafta"] = ad_gun(t)
    O["kosum_tarihi"] = dt.date.today().strftime("%d.%m.%Y")

    # ------------------------------------------------------------ gecikme
    # Gecikme, veri katmanının tazelik denetimiyle AYNI tanımdan ölçülür:
    # DUVAR SAATİ eksi son gözlem. Verinin kendi ucunu referans almak denetimi
    # kendi kendine referanslı yapar ("son gözlem bugün, demek ki taze") ve
    # donmuş bir seri sonsuza kadar taze görünür.
    bugun = pd.Timestamp.today().normalize()
    gecikme: dict[str, int] = {}
    for blok, t in _SAAT.items():
        g = int((bugun - t).days)
        gecikme[blok] = g
        koy(f"gecikme_{blok}_gun", g, 0)
    if gecikme:
        # HÜKÜM EN GERİDE KALANA GÖRE. Sayfa, bloklarının en yavaşı kadar
        # tazedir; en tazesine bakmak bayat bir paneli taze göstermek olurdu.
        en_geride = max(gecikme, key=lambda k: gecikme[k])
        koy("veri_gecikme_gun", gecikme[en_geride], 0)
        O["veri_gecikme_blok"] = BLOK_OKUR.get(en_geride, "")
        # İKİ GECİKME, İKİ SORU — adları benzediği için ayrımı burada yazıyorum.
        # `veri_gecikme_gun` "son gözlemin üstünden kaç gün geçti" der ve
        # bayatlık hükmü ondan kurulur (tolerans aynı tanımla ölçülmüş).
        # `beklenen_yayim_gecikme_gun` "verinin BEKLENEN yayım gününden beri
        # kaç gün geçti" der ve ölçüm değil TAKVİM ARİTMETİĞİDİR: kaynağın
        # yayım ritmi araya altı gün koyuyor, yani ikisi hiçbir zaman eşit
        # olmaz ve birini ötekinin yerine kullanmak bayatlık eşiğini altı gün
        # kaydırır. Adındaki "beklenen" bilinçli: resmî tatilde kayan bir yayım
        # bu hesabı yanıltır ve okur ilan edilen günü ölçülmüş sanmamalı.
        yt = beklenen_yayim_gunu(_SAAT[en_geride])
        O["beklenen_yayim_tarihi"] = yt.strftime("%d.%m.%Y")
        koy("beklenen_yayim_gecikme_gun", (dt.date.today() - yt).days, 0)

    # ------------------------------------------------------------ stok
    # Manşet BURADA: yurt içi yerleşiklerin toplam yabancı para mevduatı.
    for a in ("stok_toplam_mia", "stok_gercek_mia", "stok_tuzel_mia",
              "maden_gercek_mia", "maden_tuzel_mia", "maden_toplam_mia",
              "genis_toplam_mia", "genis_fark_mia"):
        olc(a, m.get(a), 1)
    for a in ("gercek_pay", "tuzel_pay", "maden_pay_gercek", "maden_pay_tuzel",
              "maden_pay_toplam", "genis_fark_pay"):
        olc(a, m.get(a), 2)

    # ------------------------------------------------------------ akım
    # Haftalık akım milyon dolar cinsinden ölçülüyor; manşet cümleleri milyar
    # dolar konuşuyor. Dönüşüm BURADA yapılır, sayfada değil: sayfa bileşeni
    # sayıyı olduğu gibi basar, yani bölmenin yeri yoktur ve MDX'e yazılmış bir
    # bölme bir gün ölçüm katmanının biriminden ayrışırdı.
    for e in ("toplam", "gercek", "tuzel"):
        olc(f"ar_{e}_mn", m.get(f"ar_{e}_mn"), 1)
        olc(f"pe_{e}_mn", m.get(f"pe_{e}_mn"), 1)
    for e in ("gercek", "tuzel"):
        for k in ("usd", "eur", "diger", "maden"):
            olc(f"ar_{e}_{k}_mn", m.get(f"ar_{e}_{k}_mn"), 1)
            olc(f"pe_{e}_{k}_mn", m.get(f"pe_{e}_{k}_mn"), 1)
    if m.get("ar_toplam_mn") is not None:
        olc("ar_toplam_mia", m["ar_toplam_mn"] / 1e3, 2)
    if m.get("pe_toplam_mn") is not None:
        olc("pe_toplam_mia", m["pe_toplam_mn"] / 1e3, 2)
    # KIYMETLİ MADEN İKİ BACAKLI. Gerçek kişi bacağı tek başına anılırsa tüzel
    # bacağı görünmez kalır; bir düzeltme genelleştirilmeden tamamlanmaz, bir
    # ölçüm de öyle. Toplam yalnız İKİ bacak da ölçülmüşse yazılır.
    for onek in ("ar", "pe"):
        g, t = m.get(f"{onek}_gercek_maden_mn"), m.get(f"{onek}_tuzel_maden_mn")
        if g is not None and t is not None:
            olc(f"{onek}_maden_toplam_mn", g + t, 1)

    # ------------------------------------------------------------ kümüle akım
    for a in ("kum_ay_ar_toplam_mn", "kum_ay_ar_gercek_mn", "kum_ay_ar_tuzel_mn",
              "kum_ay_pe_toplam_mn", "kum_ay_pe_gercek_mn", "kum_ay_pe_tuzel_mn",
              "kum_ay_ar_gercek_maden_mn", "kum_ay_ar_tuzel_maden_mn",
              "kum_yil_ar_toplam_mn", "kum_yil_ar_gercek_mn",
              "kum_yil_ar_tuzel_mn", "kum_yil_pe_toplam_mn",
              "kum_yil_ar_gercek_maden_mn", "kum_yil_ar_tuzel_maden_mn"):
        olc(a, m.get(a), 1)
    # BÜTÜN ÖRNEKLEMİN TOPLAMLARI. Sayfanın manşet iddiası bunlara dayanıyor;
    # anahtarı olmayan bir iddia, sayfada donmuş bir sayı demektir. Pencere de
    # birlikte yazılır (`tum_bas` · `tum_son` · `tum_hafta`): bir toplamın
    # anlamı, hangi pencereden toplandığından ayrılamaz ve o pencere her hafta
    # bir hafta uzuyor.
    for a in ("tum_ar_toplam_mia", "tum_ar_maden_mia", "tum_ar_maden_disi_mia",
              "tum_pe_toplam_mia",
              "tum_ar_gercek_mia", "tum_ar_gercek_maden_mia",
              "tum_ar_gercek_maden_disi_mia",
              "tum_ar_tuzel_mia", "tum_ar_tuzel_maden_mia",
              "tum_ar_tuzel_maden_disi_mia"):
        olc(a, m.get(a), 1)
    olc("tum_hafta", m.get("tum_hafta"), 0)
    # Pencerenin uçları TARİH; `koy` sayıya çevirir. Kümüle başlangıçlarında
    # kullanılan yol burada da geçerli: tarih biçimi tek yerden (`lib/bicim`in
    # Python eşi) çözülür ve okur yazımıyla basılır.
    for a in ("tum_bas", "tum_son"):
        d = b.tarihe_cevir(m.get(a))
        if d is not None:
            O[a] = pd.Timestamp(d).strftime("%d.%m.%Y")
            O[f"{a}_gun"] = ad_gun(pd.Timestamp(d))
    # Sabit pencereler: pencere uzunluğu ölçüm katmanının sabiti, anahtar adı
    # da onu taşıyor. Uzunluk değişirse anahtar adı da değişir ve sayfa
    # "on üç haftalık" derken dört haftalık bir sayı basmaz.
    for p in (m.get("kum_pencere_kisa_hafta"), m.get("kum_pencere_uzun_hafta")):
        if p is None:
            continue
        for a in (f"kum_{int(p)}h_ar_toplam_mn", f"kum_{int(p)}h_pe_toplam_mn"):
            olc(a, m.get(a), 1)
    for a in ("kum_ay_ar_toplam_mn", "kum_yil_ar_toplam_mn"):
        if m.get(a) is not None:
            olc(a.replace("_mn", "_mia"), m[a] / 1e3, 2)
    # YIL İÇİ KIRILIM, MİLYAR CİNSİNDEN VE MADEN/MADEN DIŞI AYRI. Sayfanın
    # ayrışma anlatısı bu altı sayıya dayanıyor ve maden dışı bacak hiçbir
    # anahtarda yoktu: sayfa iki büyük sayının farkını KENDİ alıp yazmak
    # zorunda kalırdı, yani her tazelemede donan bir üçüncü sayı üretirdi.
    # Fark burada alınıyor, çünkü ölçüm katmanının işi budur; ve yuvarlama tek
    # yerde yapılıyor, yani sayfadaki üç sayı birbirini tutuyor.
    for kesim, tam, maden in (("gercek", "kum_yil_ar_gercek_mn",
                               "kum_yil_ar_gercek_maden_mn"),
                              ("tuzel", "kum_yil_ar_tuzel_mn",
                               "kum_yil_ar_tuzel_maden_mn"),
                              ("toplam", "kum_yil_ar_toplam_mn", None)):
        t, md = m.get(tam), m.get(maden) if maden else None
        if maden is None and (m.get("kum_yil_ar_gercek_maden_mn") is not None
                              and m.get("kum_yil_ar_tuzel_maden_mn") is not None):
            md = (m["kum_yil_ar_gercek_maden_mn"]
                  + m["kum_yil_ar_tuzel_maden_mn"])
        if t is None:
            continue
        olc(f"kum_yil_ar_{kesim}_mia", t / 1e3, 1)
        if md is not None:
            olc(f"kum_yil_ar_{kesim}_maden_mia", md / 1e3, 1)
            olc(f"kum_yil_ar_{kesim}_maden_disi_mia", (t - md) / 1e3, 1)
    # TOPLANAN HAFTA SAYISI DA BİR ÖLÇÜMDÜR ve akım bloğuna aittir: ay başında
    # sıfıra yakın bir kümüle ile beslemesi durmuş bir kümüle aynı görünür,
    # ikisini ayıran şey budur. Yöntem sabitleri (pencere uzunlukları) ise
    # koddan geliyor ve bir haftaya ait değil — onlar saatsiz yazılır.
    olc("kum_ay_hafta", m.get("kum_ay_hafta"), 0)
    olc("kum_yil_hafta", m.get("kum_yil_hafta"), 0)
    koy("kum_pencere_kisa_hafta", m.get("kum_pencere_kisa_hafta"), 0)
    koy("kum_pencere_uzun_hafta", m.get("kum_pencere_uzun_hafta"), 0)
    # PENCERENİN ADI İLE KAPSAMI AYRIŞABİLİR ve fark okurun görmesi gereken bir
    # ölçümdür: kaynak bir cumayı hiç yayımlamazsa "dört haftalık" etiketli
    # toplam yirmi sekiz günü kapsar. Kapsam bir yöntem sabiti değil, o haftaya
    # ait bir ÖLÇÜM — o yüzden kendi saatiyle yazılır.
    for p_ in (m.get("kum_pencere_kisa_hafta"), m.get("kum_pencere_uzun_hafta")):
        if p_ is not None:
            olc(f"kum_{int(p_)}h_kapsam_gun", m.get(f"kum_{int(p_)}h_kapsam_gun"), 0)
    # Kümülenin BAŞLANGICI okura yazılır. Ay başında kümülenin sıfıra yakın
    # olması bir ÖLÇÜMDÜR, ama besleme durduğunda da aynı görünür; ikisini
    # ayıran şey toplanan hafta sayısı ile başlangıç günüdür.
    for a in ("kum_ay_bas", "kum_yil_bas"):
        d = b.tarihe_cevir(m.get(a))
        if d is not None:
            O[a] = pd.Timestamp(d).strftime("%d.%m.%Y")
            O[f"{a}_gun"] = ad_gun(pd.Timestamp(d))
    for a in ("kum_ay_etiket", "kum_yil_etiket"):
        if m.get(a):
            O[a] = str(m[a])

    # ------------------------------------------------------------ kimlik
    for e in ("toplam", "gercek", "tuzel"):
        olc(f"delta_{e}_mn", m.get(f"delta_{e}_mn"), 1)
        olc(f"kimlik_artik_{e}_mn", m.get(f"kimlik_artik_{e}_mn"), 1)
    # Bağıl artık kaynakta oran olarak duruyor; okura yüzde olarak gider ve
    # anahtar adı birimi taşır. Aynı büyüklüğü hem oran hem yüzde diye iki
    # anahtara yazmak, bir gün birinin yanlış yere bağlanması demektir.
    if m.get("kimlik_artik_bagil") is not None:
        olc("kimlik_artik_pay", m["kimlik_artik_bagil"] * 100.0, 3)
    # EŞİĞİN OKUR BİRİMİ ÖLÇÜM KATMANINDA KURULUYOR, burada DÖNÜŞTÜRÜLMÜYOR:
    # aynı eşiği figürün alt yazısı da basıyor ve iki ayrı dönüşüm bir gün
    # sessizce ayrışırdı (biri oranı yüzdeye çevirir, öteki unutur).
    koy("kimlik_esik_mn", m.get("kimlik_esik_mn"), 1)
    koy("kimlik_esik_pay", m.get("kimlik_esik_pay"), 2)
    koy("kimlik_pencere_hafta", m.get("kimlik_pencere_hafta"), 0)
    koy("kimlik_kaydirma", m.get("kimlik_kaydirma"), 0)
    # ÜÇ HÂLLİ: tutuyor · tutmuyor · SINANMADI. Sınanmamış bir kimliğe "False"
    # yazmak, yapılmamış bir sınavın sonucunu bildirmek olurdu; ölçüm katmanı
    # bu yüzden None döndürüyor ve None burada da atlanıyor. HÜKÜM METNİ de
    # ölçüm katmanında kuruluyor — figürün alt yazısı aynı metni basıyor ve
    # iki yerde ayrı ayrı yazılsaydı bir gün sessizce ayrışırlardı.
    if m.get("kimlik_tutuyor") is not None:
        O["kimlik_tutuyor"] = bool(m["kimlik_tutuyor"])
    if m.get("kimlik_hukum"):
        O["kimlik_hukum"] = str(m["kimlik_hukum"])

    # ------------------------------------------------------------ dolarizasyon
    for a in ("dol_pay_ham", "dol_pay_ar", "dol_pay_fark"):
        olc(a, m.get(a), 2)
    for a in ("mevduat_tl_mlr", "mevduat_yp_mlr", "mevduat_yp_ar_mlr"):
        olc(a, m.get(a), 0)
    # ÇIPADAKİ PAYIN SAATİ BLOĞUN HAFTASI DEĞİL, ÇIPANIN KENDİ GÜNÜDÜR.
    # Bloğun saatini yazsaydık okur, çıpadaki ölçümü son haftanın ölçümü
    # sanardı; sayfa bileşeni her değerin saatini o değerin anahtarından okuyor
    # ve bu, sözleşmenin tam olarak işe yaradığı yer.
    d_cipa = b.tarihe_cevir(m.get("dol_cipa"))
    if d_cipa is not None:
        O["dol_cipa"] = ad_gun(pd.Timestamp(d_cipa))
        O["dol_cipa_kisa"] = pd.Timestamp(d_cipa).strftime("%d.%m.%Y")
        olc("dol_pay_cipa", m.get("dol_pay_cipa"), 2,
            saat=O["dol_cipa_kisa"])
    else:
        koy("dol_pay_cipa", m.get("dol_pay_cipa"), 2)

    # ------------------------------------------------------------ ayrışma
    for a in ("ayrisma_n_hafta", "ayrisma_ters_hafta", "ayrisma_korel",
              "ayrisma_korel_son_pencere"):
        olc(a, m.get(a), 0 if a.endswith("_hafta") else 3)
    for a in ("ayrisma_ters_oran", "ayrisma_ters_oran_ilk_yari",
              "ayrisma_ters_oran_ikinci_yari"):
        if m.get(a) is not None:
            olc(a.replace("_oran", "_pay"), m[a] * 100.0, 1)

    # ------------------------------------------------------------ cümleler
    # Ölçüm katmanının kurduğu cümleler OLDUĞU GİBİ taşınır: içlerindeki her
    # sayı orada biçim sözleşmesinden yazıldı ve burada yeniden kurmak aynı
    # metnin ikinci bir tanımı olurdu.
    # SIFIRIN DÖRT CÜMLESİ DÖRT AYRI ANAHTARDA taşınır ve sayfa onları aynı
    # kutuda aynı ağırlıkta toplamamalıdır: tanım gereği sıfır (dayanağı
    # aritmetik), dayanağı olmayan sıfır (ayırt edilemeyen ve manşete dokunan
    # sınır), yayımı durmuş olabilecek blok (kaynaktaki belirsizlik) ve
    # başlangıcı ölçülmemiş seri (bizim sormadığımız soru).
    for a in ("kimlik_cumlesi", "dol_cumlesi", "ayrisma_cumlesi",
              "kapsam_cumlesi", "sifir_cumlesi", "sifir_tanim_cumlesi",
              "sifir_dayanaksiz_cumlesi", "sifir_hukumsuz_cumlesi"):
        if m.get(a):
            O[a] = str(m[a])

    # ÜÇ TABANIN KAYNAK KODU — sözlüğün yerine geçen makine bilgisi.
    # Sayfada üç ayrı taban geçiyor ve hangisinin manşet olduğu okura
    # anlatılmalı; o anlatı SAYFANIN nesridir. Koşu kaydına düşen, üç kalemin
    # katalogdan çözülmüş kodu — elle yazılmış bir kod, katalog değiştiği gün
    # sessizce yalan söylerdi.
    for a in ("taban_manset_kod", "taban_genis_kod", "taban_lira_kod"):
        if m.get(a):
            O[a] = str(m[a])

    # İKİ PENCERE — sayılar burada, ayrımın anlatısı sayfada.
    # Tarihçe asimetrik: yalnız değişim tablosundan türeyen ölçümler uzun
    # pencereden, Δ stok ve kimlik ancak ORTAK pencereden geliyor. Hangi
    # ölçümün hangi pencereden geldiğini anlatan cümle sayfanın işi; burada
    # o cümlenin dayandığı beş sayı duruyor.
    for a in ("kapsam_akim_hafta", "kapsam_ortak_hafta",
              "kapsam_asimetri_hafta"):
        koy(a, m.get(a), 0)
    for a in ("kapsam_akim_bas", "kapsam_stok_bas", "kapsam_ortak_bas"):
        d = b.tarihe_cevir(m.get(a))
        if d is not None:
            O[a] = pd.Timestamp(d).strftime("%d.%m.%Y")

    # SIFIR SINIFLAMASININ SAYILARI. Dört metin artık mekanik (sınıfa giren
    # seriler + tek ölçüm + sınıfın adı); cümlelerden çıkan her sayı burada
    # kendi anahtarını buluyor ve sayfa hangisini hangi metnin yanına
    # koyacağını kendi seçiyor. Sayımlar HER koşuda yazılır (sıfır bir ölçüm
    # sonucudur), sınıfa bağlı ölçümler yalnız sınıf doluyken.
    for a in ("sifir_olculen_seri", "sifir_esik_hafta", "sifir_tanim_seri",
              "sifir_dayanaksiz_seri", "sifir_hukumsuz_seri",
              "sifir_ayirt_edilemez_seri", "sifir_celiskili_seri",
              "sifir_tam_sifir_seri", "sifir_ayirt_edilemez_maks_hafta",
              "sifir_tanim_bas_kanitsiz_seri", "sifir_tanim_bas_kirpik_seri",
              "sifir_hukumsuz_bas_kanitsiz_seri",
              "sifir_hukumsuz_bas_kirpik_seri",
              "sifir_dayanaksiz_kiyas_oteki_seri",
              "sifir_dayanaksiz_kese_seri",
              "sifir_dayanaksiz_kese_hareketli_seri",
              "sifir_dayanaksiz_kese_durgun_seri",
              # MANŞET SINIRI SINIFTAN BAĞIMSIZ: parite etkisi hiç
              # yayımlanmayan her bacak sayılır, sıfırın sebebi ölçülmüş olsun
              # ya da olmasın. Sınıfa bağlı yazıldığında bacak sınıf
              # değiştirdiğinde sınır sayfadan büsbütün kayboluyordu.
              "sifir_sinir_seri", "sifir_sinir_kese_seri",
              "sifir_sinir_kese_hareketli_seri",
              "sifir_sinir_kese_durgun_seri"):
        koy(a, m.get(a), 0)
    for a in ("sifir_hukumsuz_hafta", "sifir_dayanaksiz_hafta",
              "sifir_dayanaksiz_kiyas_dolu_min_hafta",
              "sifir_dayanaksiz_kiyas_kapsam_min_hafta",
              "sifir_dayanaksiz_kese_zayif_hafta",
              "sifir_dayanaksiz_kese_zayif_sifirdisi_hafta",
              "sifir_sinir_dilim_hafta"):
        konusuz(a, m.get(a), 0)
    for a in ("sifir_dayanaksiz_kese_zayif_pay",
              "sifir_sinir_dilim_manset_pay"):
        konusuz(a, m.get(a), 1)
    for a in ("sifir_sinir_dilim_medyan_mn", "sifir_sinir_dilim_maks_mn",
              "sifir_sinir_manset_medyan_mn"):
        konusuz(a, m.get(a), 1)

    # GENİŞ TOPLAM ADIYLA VE FARKIYLA. Bu cümle sayfanın en pahalı hatasına
    # karşı konmuş bir sigortadır: kaynağın geniş toplamı yurt dışı yerleşik
    # bankaları da içeriyor ve manşetle yan yana konursa okur kırk milyar
    # dolarlık bir farkı görmeden iki sayıyı aynı şey sanır. Cümle ölçümden
    # kuruluyor, yani fark değiştiğinde kendiliğinden düzeliyor.
    if all(O.get(a) is not None for a in ("genis_toplam_mia", "stok_toplam_mia",
                                          "genis_fark_mia", "genis_fark_pay")):
        # Yüzdeye Türkçe iyelik eki EKLENMİYOR ("geniş toplamın %14,7'si"):
        # ekin ünlüsü sayının OKUNUŞUNA göre değişir ve biçimlenmiş bir sayının
        # ardına sabit bir ek yazmak, sayı değiştiği gün yanlış eke düşer.
        # Cümle bu yüzden eksiz kuruluyor.
        # TEK ÖLÇÜM: KAPSAM FARKININ BÜYÜKLÜĞÜ. Cümle dört ölçüm ve dört
        # cümle taşıyordu; dördü de zaten kendi anahtarında duruyor
        # (`genis_toplam_mia` · `stok_toplam_mia` · `genis_fark_mia` ·
        # `genis_fark_pay`). Farkın NEDEN olduğu — geniş toplamın yurt dışı
        # yerleşik bankaları da kapsaması, ve farkın yalnız onlardan ibaret
        # OLMAMASI — sayfanın anlatacağı bir nüans; bu hattın en pahalı
        # hatasına karşı konmuş sigorta o anlatının kendisidir, cümlenin
        # koşu kaydında durması değil.
        O["genis_fark_cumlesi"] = (
            "Kaynağın geniş toplamı ile bu sayfanın manşeti arasındaki kapsam "
            f"farkı {b.sayi(O['genis_fark_mia'], 1)} milyar dolar.")

    # KÜMÜLE AKIM — hattın asıl katkısı. Cümle yalnız İKİ pencere de ölçülmüşse
    # kurulur; toplanan hafta sayısı cümlenin içindedir, çünkü ay başında
    # sıfıra yakın bir kümüle ile beslemesi durmuş bir kümüle aynı görünür.
    if (O.get("kum_ay_ar_toplam_mn") is not None
            and O.get("kum_yil_ar_toplam_mn") is not None
            and O.get("kum_ay_hafta") and O.get("kum_yil_hafta")):
        # TEK ÖLÇÜM: AY İÇİ TOPLAM. Cümle dört ölçüm taşıyordu (ay toplamı,
        # ay hafta sayısı, yıl toplamı, yıl hafta sayısı) artı ayın adı ve bir
        # işaret açıklaması. Dördü de kendi anahtarında duruyor
        # (`kum_ay_ar_toplam_mn` · `kum_ay_hafta` · `kum_yil_ar_toplam_mn` ·
        # `kum_yil_hafta`), ayın adı da (`kum_ay_etiket`). İşaretin ne
        # anlattığı bir yöntem notudur ve sayfaya aittir — her koşuda aynı
        # kalan bir cümle, bir koşunun kaydı olamaz.
        #
        # AY ADI CÜMLEDEN ÇIKTI ama ÖLÇÜM olarak duruyor: etiket, sayının
        # okunduğu haftadan türetiliyor (çerçevenin ucundan kurulduğunda bir
        # ayın sayısı başka bir ayın adıyla yayımlanmıştı) ve sayfa onu
        # ölçümün yanına kendi koyar.
        O["kum_cumlesi"] = (
            "Parite etkisinden arındırılmış akımın ay içi toplamı "
            f"{b.sayi(O['kum_ay_ar_toplam_mn'], 1)} milyon dolar.")

    # ------------------------------------------------------------ koşu kaydı
    uyarilar = [str(x) for x in (uy.get("uyarilar") or [])]
    # SON SAVUNMA: ölçüm katmanı devralmayı atlarsa uyarı burada yakalanır.
    # Devir zinciri kırıldığında hiçbir şey hata vermez, uyarı yalnızca
    # SAYFADA GÖRÜNMEZ — ve görünmeyen bir uyarı, olmayan bir uyarıdır.
    #
    # AMA YALNIZ AYNI PENCEREYİ ANLATIYORSA. İki kayıt da anlattığı çerçeveyi
    # künyesiyle taşıyor; künyeler ayrıştığında veri katmanının satırları
    # BAŞKA bir koşuya aittir ve onları sayfaya taşımak, geçmiş bir günün
    # alarmını bugün çalmaktır. Bir savunma hattı, savunduğu şeyin doğru
    # olduğunu da sormalıdır.
    vd_imza, m_imza = vd.get("cerceve_imza"), m.get("cerceve_imza")
    if vd_imza is None or m_imza is None or vd_imza == m_imza:
        for u in (vd.get("uyarilar") or []):
            if str(u) not in uyarilar:
                uyarilar.append(str(u))

    tol = tazelik_tolerans("haftalik")
    # SEBEPLER SAYILIR, CÜMLEYE DİZİLMEZ. Bayatlık cümlesi üç bağımsız ölçümü
    # (gecikme günü, düşen tazelik uyarısı sayısı, atlanan ölçüm sayısı)
    # noktalı virgülle yan yana diziyordu; üçü de kendi anahtarında duruyor
    # ya da artık duruyor. Cümleye kalan tek şey HÜKÜM: sayfadaki sayılar bu
    # koşuda ilerledi mi, ilerlemedi mi. Sebep dizisi burada yalnız hükmü
    # kurmak için toplanıyor.
    sebep: list[str] = []
    if O.get("veri_gecikme_gun") is not None and O["veri_gecikme_gun"] > tol:
        sebep.append("gecikme")
    # ÖNEK LİSTESİ BURADA TUTULMAZ: aile tanımı veri katmanında (bkz.
    # veri.SAG_UC_IZI). Elle tutulan liste üç önek taşıyordu ve "SERİ YOK"
    # onda yoktu; hiç yüklenemeyen bir seri bayatlık hükmünü hiç tetiklemiyordu.
    #
    # AİLE SAĞ UÇ AİLESİDİR, "bütün uyarılar" DEĞİL. Bayatlık, sayfadaki
    # sayının bu koşuda ilerleyip ilerlemediğine dair bir hükümdür; tarihçenin
    # ŞEKLİNE dair bulgular (eski bir boşluk, tarihçenin başındaki eksik)
    # okura ayrıca gösterilir ama sayfayı bayat ilan etmez. Ayrım olmadan
    # 2015'te atlanmış tek bir hafta bu sayfayı sonsuza kadar bayat yapardı.
    izler = [u for u in uyarilar if u.startswith(veri.SAG_UC_IZI)]
    if izler:
        # KATMAN ADI YAZILMAZ. Bu satırlar artık iki yerden de gelebiliyor
        # (veri katmanı çekim sırasında, ölçüm katmanı çerçeveden yeniden
        # ölçerek) ve hangisinin bastığı okurun kararını değiştirmiyor —
        # üstelik yanlış katmanı adlandıran bir cümle, kusuru yanlış yerde
        # aratır.
        sebep.append("tazelik uyarısı")
    # DÜŞEN HER ANAHTAR SAYFADA BİR STATİK YEDEK DEMEKTİR. Ölçülemeyen bir
    # anahtar özete hiç yazılmıyor ve sayfa onun yerine MDX'e elle yazılmış
    # sabiti gösteriyor; o sabit güncel görünür ama değildir. Bu yüzden atlanan
    # anahtar sayısı bayatlık hükmüne KENDİ BAŞINA girer: uyarı satırı
    # basılmamış olsa bile (ölçüm katmanı sütunu hiç görmemiş olabilir) sayfa
    # bir donmuş sayı gösteriyordur.
    if _ATLANAN:
        sebep.append("atlanan ölçüm")
    O["bayat"] = bool(sebep)
    koy("atlanan_olcum_sayisi", len(_ATLANAN), 0)
    # ÜÇ SEBEP, ÜÇ SAYI — sayfa hangisini anacağını kendi seçer.
    koy("bayat_sebep_sayisi", len(sebep), 0)
    koy("bayat_tazelik_uyarisi_sayisi", len(izler), 0)
    # Toleransın birimi GÜNDÜR, ailenin adı "haftalık" olsa da. Birimi adında
    # taşımayan bir eşik bir gün yanlış okunur: on iki gün ile on iki hafta
    # arasındaki fark, donmuş bir seriyi üç ay boyunca taze göstermektir.
    koy("bayat_tolerans_gun", tol, 0)
    # İKİ BAYRAK, SIFIR ÖLÇÜM. Hüküm burada; gecikmenin kaç gün olduğu
    # (`veri_gecikme_gun`), toleransın kaç gün olduğu (`bayat_tolerans_gun`),
    # kaç tazelik uyarısı düştüğü ve kaç ölçümün atlandığı kendi
    # anahtarlarında. "Tazelik uyarısı yok" ifadesi de cümleden çıktı: o bir
    # VERİ iddiasıydı ve hükmün koşulu değil, koşullarından yalnız biriydi —
    # gecikme yüzünden bayat sayılan bir koşuda cümle onu yine de yazardı.
    O["bayat_cumlesi"] = (
        "BAYAT VERİ: sayfadaki sayılar bu koşuda ilerlememiş olabilir."
        if sebep else "Veri taze: bütün bacaklar tolerans içinde.")
    koy("uyari_sayisi", len(uyarilar), 0)
    O["uyari_metni"] = ((O["bayat_cumlesi"] + " · " if O["bayat"] else "")
                        + (" · ".join(uyarilar) if uyarilar
                           else "Bu koşuda uyarı yok."))
    # Sayıyı ÇERÇEVELEYEN cümle de sayıdan türetilir: "tek uyarı budur" derken
    # üç madde listeleyen bir metin, kendisiyle çelişir.
    O["uyari_cumlesi"] = (
        "Bu koşuda uyarı düşmedi." if not uyarilar else
        "Bu koşuda düşen tek uyarı budur:" if len(uyarilar) == 1 else
        f"Bu koşuda {b.sayi(len(uyarilar), 0)} uyarı düştü:")

    # ------------------------------------------------- şekil saat defteri
    # Defter veri katmanında TEK yerde duruyor; burada yalnız okunuyor. Çizim
    # katmanı figürün kendi alt yazısı için aynı fonksiyonu çağırıyor: iki
    # liste tutulsaydı okur aynı figürün içinde ve altında iki farklı tarih
    # görürdü. Değeri None olan figürün altına sayfa tarih BASMAZ.
    O["_sekil_tarih"] = sekil_saatleri(m)

    # SÖZLEŞME SAYFAYA YAZILI OLARAK GİDER. Bu anahtarlar bir koşuda ölçülüp
    # öbüründe hiç yazılmayabilir; MDX onları <Deger> ile çağırırsa o koşuda
    # sayfa sınavının birinci ölçütü ENGEL üretir ve sitenin TAMAMININ yayını
    # durur. Listeyi burada üretmek, sayfayı yazan oturumun "hangi anahtar
    # güvenli" sorusunu tahminle cevaplamasını önler. Alt çizgiyle başlıyor:
    # saatsiz sayı denetimi ve okur dili taraması onu atlar, çünkü bir ölçüm
    # değil bir makine kaydıdır.
    O["_istege_bagli"] = sorted(a for a in O if istege_bagli(a))

    # ------------------------------------------------------------ denetimler
    saatsiz = _saatsiz_denetimi()
    for a in saatsiz:
        uyar(f"'{a}' bir sayı ama saati yok — blok kuralına takılmıyor; "
             "sayfa onu hattın ana saatiyle etiketler.")
    for x in _cumle_denetimi():
        uyar(f"okur dili: {x}")
    # CÜMLE SÖZLEŞMESİ — kapı burada DEĞİL, hattın duman sınamasındadır.
    # Gerekçe kardeş denetimle aynı: yayının önünde duran bir denetimin yanlış
    # alarmı arızanın kendisidir. Ama kusuru hat koşarken görmek ucuz, ve
    # sözleşmeyi aşan anahtar adıyla görünsün — sayılan şey ölçü, hüküm değil.
    olcu = _cumle_olcusu_denetimi(uyarilar)
    for x in olcu:
        uyar(f"cümle sözleşmesi: {x}")

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    manset = O.get("stok_toplam_mia")
    print(f"ozet.json yazıldı: {len(O)} anahtar · hat saati {O['_tarih']} "
          f"({O.get('hat_saati_blok', '—')})")
    print(f"  manşet stok_toplam_mia = "
          f"{b.sayi(manset, 1) if manset is not None else '—'} milyar dolar "
          f"· saat {O.get('stok_toplam_mia_tarih', '—')}")
    bloklar = " · ".join(f"{k} {v.strftime('%d.%m.%Y')}"
                         for k, v in sorted(_SAAT.items()))
    print(f"  blok saatleri: {bloklar or 'yok'}")
    print(f"  atlanan anahtar {len(_ATLANAN)} · saatsiz sayı {len(saatsiz)} · "
          f"uyarı {O.get('uyari_sayisi', 0)} · cümle sözleşmesi "
          f"{'temiz' if not olcu else f'{len(olcu)} aşım'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
