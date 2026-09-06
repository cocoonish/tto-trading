# -*- coding: utf-8 -*-
"""Yurt içi yerleşiklerin YP mevduatı — ölçüm katmanı.

Girdi   data/haftalik.csv · data/veri_durum.json          (veri.py üretir)
Çıktı   data/metrik_haftalik.csv   stok, kırılım, paylar
        data/ayristirma.csv        Δ stok · arındırılmış değişim · parite etkisi · ARTIK
        data/kumule.csv            ay içi · yıl içi · 4 ve 13 haftalık kümüle akım
        data/dolarizasyon.csv      ham ve parite etkisinden arındırılmış pay
        data/metrik_ozet.json      son hafta değerleri + tanı blokları
        uyarilar.json              veri ve ölçüm katmanının uyarıları (SAYFAYA çıkar)

HATTIN SORUSU
-------------
"YP mevduatı ne kadar arttı" değil, "artışın ne kadarı GERÇEK PARA GİRİŞİ, ne
kadarı DEĞERLEME". Seri milyon ABD doları cinsinden yayımlanıyor ve sepette
euro, sterlin ve kıymetli maden var: euro dolara karşı değer kazandığında USD
karşılığı hiçbir yeni para girmeden yükselir.

AYRIŞTIRMAYI BİZ TÜRETMİYORUZ. TCMB resmî olarak yayımlıyor:

    Δ stok  =  Parite etkisinden arındırılmış değişim  +  Parite etkisi
    (2.11 · 2.12)          (5.1 … 5.11)                    (5.12 … 5.22)

Bu katmanın işi ayrıştırmayı UYDURMAK değil, onu OKUNUR kılmak: kümüle akım,
kırılım, ayrışma ve KİMLİK DENETİMİ. Kendi kur sepetimizden ikinci bir "parite
etkisi" hesaplayıp resmî olanın yanına koymak okur için iki rakip gerçek
üretirdi; yapılmaz.

ÜÇ DENETİM AİLESİ, ÜÇ AYRI AĞIRLIK — KARIŞTIRILMAZ
--------------------------------------------------
(1) KAPSAM KİMLİĞİ (gerçek + tüzel = toplam) **DURDURUR**. Keşifte birebir
    ölçüldü; bozulması kalem numaralandırmasının ya da birimin kaydığı
    anlamına gelir ve o zaman sayfadaki HER sayı yanlıştır.
(2) AYRIŞTIRMA KİMLİĞİ (Δ stok ≟ arındırılmış + parite) **DURDURMAZ**. Artık
    ölçülür, yayımlanır ve sayfada görünür — kardeş hattaki Laspeyres
    artığının aynısı. Sebebi: bu kimlik TCMB'nin İKİ AYRI TABLOSU arasında
    kuruluyor, yani yuvarlama ve revizyon vintajı farkı taşıyor; onu yayının
    önüne koymak, ölçmeye çalıştığımız şeyi görünmez kılardı.
(3) ÖLÇÜM, denetim değil: yurt dışı bacak, ölü seri, hafta hizalaması. Eşik
    konmaz, ölçülür ve kayda geçer.

BU KATMANIN VERİ KATMANINA BORÇLARI
-----------------------------------
· veri.py'nin uyarıları BURADA devralınır (bellekteki liste + koşu kaydı).
  Devralınmazsa tazelik ve önbellek uyarıları sayfaya HİÇ çıkmaz: düzenin
  yasakladığı sessiz bayatlama tam olarak budur.
· Uyarı kaydı uyarı YOKKEN DE yazılır. Kopya sözleşmesinde düz yol olarak
  duruyor ve dosya yoksa kopyalama TAM ORADA kesilir — sözlükte ondan sonra
  gelen hiçbir çıktı siteye gitmez, üstelik koşu yeşil biter.
· Şekil saat defteri (veri.sekil_saatleri) `stok_tarih`, `akim_tarih` ve
  `dol_tarih` anahtarlarını BURADAN okur. Bu üçü yazılmazsa defterin tamamı
  boş döner ve hiçbir şeklin altına tarih basılmaz.

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd

import veri
from veri import PROJE, VERI, ad_gun, ad_uzun


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı (ondalık virgül, eksi
    U+2212, yüzde önde, tarih GG.AA.YYYY).

    Bu katmanın uyarı satırları ve özetteki cümle alanları sayfaya OLDUĞU GİBİ
    basılıyor. `f"{x:.1f}"` kalıbı hem ondalık nokta hem ASCII tire taşır ve
    yayın kapısında "biçim" bulgusu üretir; kardeş hatlarda o kalıp hâlâ
    duruyor ve kopyalanmaz.

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


_UYARI: list[str] = []


def uyar(m: str) -> None:
    """Görünür uyarı: ekrana basılır ve uyarilar.json üzerinden SAYFAYA çıkar.

    Bu yüzden OPERATÖRE değil OKURA yazılır: sütun adı, dosya adı, grup kodu
    ve komut anahtarı metne girmez; sayı ortak/bicim'den yazılır. Kaynağın
    BÜYÜK harfli seri kodu (TP.HPBITABLO5.2) künyedir ve girebilir.
    """
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def uyarilar() -> list[str]:
    return list(_UYARI)


# ===========================================================================
# EŞİKLER — her biri AYRI ad, AYRI ağırlık, AYRI gerekçe
# ===========================================================================
# (1) KAPSAM KİMLİĞİ — DURDURUR.  gerçek (2.11) + tüzel (2.12) = toplam (2.10)
#
# Eşiğin büyüklüğü verinin ÖLÇEĞİNDEN türetildi, uydurulmadı:
#   · Kaynak bu üç seriyi bir ondalık basamakla yayımlıyor (148.848,7 ·
#     82.508,3 · 231.357,0). Üç bağımsız yuvarlamanın en kötü hâli
#     0,05 + 0,05 + 0,05 = 0,15 milyon dolarlık bir artıktır.
#   · 2,0 milyon dolar bu tabanın 13 katıdır, yani yuvarlamadan doğan bir
#     artık bu kapıyı ASLA çalamaz. Yayının önünde duran bir denetimin yanlış
#     alarmı arızanın kendisidir; buraya dar bir eşik koymak (bağıl 1e-6 gibi)
#     yuvarlama tabanına yalnız 1,5 kat pay bırakırdı.
#   · Yakalaması gereken arıza ise ÇOK BÜYÜK: bir kalem numaralandırması
#     kayarsa toplama giren bacak değişir ve artık on binlerce milyon dolar
#     olur (yalnız gerçek kişilerin maden hesapları 89.585,1). Tespit payı
#     dört basamak.
# Bağıl kol, ölçek büyüdüğünde eşiğin sabit kalmamasını sağlar: etkin eşik
# ikisinin BÜYÜĞÜDÜR. Bugünkü stokta bağıl kol 2,3 milyon dolara denk gelir.
ESIK_KAPSAM_MN = 2.0
ESIK_KAPSAM_BAGIL = 1e-5

# (2) AYRIŞTIRMA KİMLİĞİ — DURDURMAZ, yalnız uyarır.  Δ stok ≟ arındırılmış + parite
#
# Bu kimlik (1)'den yapısal olarak farklıdır: iki AYRI TABLO karşılaştırılıyor.
# Aynı yayımın aynı satırları değil, biri stok biri değişim tablosu. Aradaki
# artık üç kaynaktan beslenir ve üçü de kusur DEĞİLDİR: yuvarlama (en kötü
# 0,2 milyon dolar — Δ stok iki yuvarlanmış seviyenin farkı, arındırılmış ve
# parite ayrı ayrı yuvarlanmış), revizyon vintajı farkı, ve kaynağın kendi
# hesabındaki iç yuvarlama.
#   · 25,0 milyon dolar, yuvarlama tabanının 125 katı ve 231 milyar dolarlık
#     stokun on binde 1,1'i (yüzde 0,011) — sayfanın konuştuğu milyar
#     ölçeğinde görünmez. Kıyas yorumda ON KAT yanlış yazılmıştı ("on binde
#     0,1") ve eşiği gözden geçiren bir sonraki oturum ona güvenip eşiği on kat
#     büyütmeyi makul sanabilirdi; o hâlde son haftanın brüt hareketinin onda
#     birine kadar olan bir kimlik kırılması sessizce geçerdi. Kıyas artık
#     koşuda türetiliyor da (`esik.kimlik_son_stok_payi`), yani yaşlanmıyor.
#   · Yakalaması gereken arıza yine çok büyük: yanlış hafta hizalaması ya da
#     kalem kayması artığı haftalık akımın kendi büyüklüğüne çıkarır (ölçülen
#     son hafta brüt 2.714,8 milyon dolar). Tespit payı iki basamak.
# Bağıl kol (brüt hareketin yüzde biri) olağandışı büyük bir haftanın mutlak
# tabanla haksız yere işaretlenmesini önler; etkin eşik ikisinin BÜYÜĞÜDÜR.
ESIK_KIMLIK_MN = 25.0
ESIK_KIMLIK_BAGIL = 0.01

# Uyarı SON PENCEREYE bakar, tam tarihçeye değil: iki yıl önceki bir revizyon
# bugünün kusuru değildir ve maksimuma bakan bir ölçüt o hafta yüzünden
# sonsuza kadar kırmızı kalır. Kalıcı bir kırılma zaten bu pencerede de
# görünür. Tam tarihçenin maksimumu TANI olarak ayrıca kaydedilir.
KIMLIK_PENCERE = 52

# (3) HAFTA HİZALAMASI — hüküm değil, KARAR eşiği.
# Değişim tablosunun hangi haftanın hareketini hangi cumaya damgaladığı
# ÖLÇÜLMEDİ. Doğal okuma aynı cumadır (kaydırma sıfır) ve VARSAYILAN odur;
# başka bir kaydırma ancak KARARLI bir farkla daha iyiyse benimsenir. On kat
# istenmesinin sebebi: kaydırma seçimini artığa bakarak yapmak örneklem içi
# bir uydurmadır ve marjinal bir iyileşme buna yetmez. Gerçek bir yanlış
# hizalamada fark on kat değil yüz kattır — yani bu eşik gerçek olayı
# kaçırmaz, gürültüyü ise içeri almaz.
ESIK_HIZALAMA_ORAN = 0.10

# (4) ÖRNEKLEM YETERLİLİĞİ — ayrışma istatistikleri için.
# Bir yıllık haftalık gözlemin altında korelasyon ve işaret oranı yazmak, üç
# gözlemden kural kurmakla aynı şeydir. Yetmiyorsa ölçüm YAPILMAZ ve sebebi
# yazılır; boş bırakmak uydurmaktan iyidir.
ESIK_TARIHCE_HAFTA = 52

# (4b) DOLARİZASYON ÇIPASININ ASGARİ PENCERESİ.
# Çıpa takvim yılının ilk gözlemidir; ocak ayının ilk haftalarında bu pencere
# birkaç gözlemden ibaret olur ve çıpa son haftanın kendisine kadar
# yaklaşabilir. O hâlde arındırılmış pay tanım gereği ham paya eşittir ve
# "iki ölçünün farkı" YAPISAL bir sıfır olur — ölçüm gibi görünen, ölçüm
# olmayan bir sayı. Dört hafta, bir pencere ölçüsünün en az isteyeceği şey.
ESIK_CIPA_HAFTA = 4

# (5) SIFIR BLOĞU — ölçüm mü, ölçümün yokluğu mu?
# Bir haftanın arındırılmış değişimi gerçekten sıfır olabilir; o bir ÖLÇÜMDÜR
# ve boşaltılmaz. Ama serinin SAĞ UCUNDA yarım yıl boyunca tam sıfır varsa
# ikisi ayırt edilemez. Eşik yalnız RAPORLAMAYI tetikler (aşağıda sifir_olc'un
# gerekçesine bakın: burada maskeleme YAPILMIYOR).
# Tanım VERİ KATMANINDA (veri.SIFIR_BLOK_HAFTA): aynı olay için iki katmanda
# iki ayrı eşik (52 ve 26) duruyordu ve okur aynı dört seri için aynı kutuda
# iki farklı hafta sayısı görüyordu.
ESIK_SIFIR_BLOK = veri.SIFIR_BLOK_HAFTA

# Kümüle akımın hareketli pencereleri. Ay ve yıl içi kümüle TAKVİME bağlıdır
# ve pencere uzunluğu haftadan haftaya değişir; sabit uzunluklu iki pencere
# yanına konur ki "sonuç pencereye bağlı" cümlesi okura ÖLÇÜLMÜŞ olarak
# görünsün, iddia olarak değil.
PENCERE_KISA = 4
PENCERE_UZUN = 13

# BLOK OKUR ADLARI BURADA TUTULMAZ. İki modül aynı kutuya yazıyor ve iki ayrı
# ad tablosu tutuluyordu; ikisi daha ilk günden ayrışmıştı ("akım" ile "resmî
# ayrıştırma tablosu" aynı şeydi ve okur bunu bilemezdi). Tek tanım veri
# katmanında (`veri.blok_okur`); üstelik oradaki sürümün ham anahtar yedeği de
# yok, yani yarın eklenen bir blok kendi kod adıyla okura gidemez.

# Ayrıştırma çerçevesinin üç bacağı: (etiket, stok serisi, arındırılmış, parite)
BACAKLAR = (
    ("gercek", "stok_gercek", "ar_gercek", "pe_gercek"),
    ("tuzel", "stok_tuzel", "ar_tuzel", "pe_tuzel"),
    ("toplam", "stok_toplam", "ar_toplam", "pe_toplam"),
)

# Para birimi kırılımları da ayrıştırma çerçevesine girer: aynı tablodan
# gelirler ve seçilen hafta hizalamasını AYNI şekilde taşımaları gerekir.
# Ayrı bir yerde kaydırılsalardı bir gün biri kaydırılır öteki unutulurdu.
KIRILIM = ("usd", "eur", "diger", "maden")

# ozet.json anahtarları — birim ADIN İÇİNDE: _mn milyon dolar, _mia milyar
# dolar, _mlr milyar lira, _pay yüzde. Aynı özette üç ayrı taban dolaşıyor
# (yurt içi toplam · geniş toplam · lira karşılığı) ve birimi adında
# taşımayan bir anahtar bir gün yanlış tabana bağlanır.
#
# İKİ AYRI EŞLEME, ÇÜNKÜ İKİ AYRI SAAT: `AKIM_OZET` yalnız değişim tablosundan
# gelen serileri taşır; stok değişimi ve kimlik artığı İKİ TABLOYU birden
# kullandığı için ayrı bir bloğa (`KIMLIK_OZET`) gider. Hepsi tek blokta
# olsaydı stok tablosu bir hafta geciktiğinde akım figürlerinin damgası da
# geriye düşerdi — oysa o figürler stok serisini hiç çizmiyor ve taze bir
# paneli bayat göstermek, bayatı taze göstermek kadar yanlıştır.
AKIM_OZET: dict[str, str] = {}
for _e in ("toplam", "gercek", "tuzel"):
    AKIM_OZET[f"ar_{_e}"] = f"ar_{_e}_mn"
    AKIM_OZET[f"pe_{_e}"] = f"pe_{_e}_mn"
for _e in ("gercek", "tuzel"):
    for _k in KIRILIM:
        AKIM_OZET[f"ar_{_e}_{_k}"] = f"ar_{_e}_{_k}_mn"
        AKIM_OZET[f"pe_{_e}_{_k}"] = f"pe_{_e}_{_k}_mn"

KIMLIK_OZET: dict[str, str] = {}
for _e in ("toplam", "gercek", "tuzel"):
    KIMLIK_OZET[f"delta_{_e}"] = f"delta_{_e}_mn"
    KIMLIK_OZET[f"artik_{_e}"] = f"kimlik_artik_{_e}_mn"

# Kümüle akımın özete çıkan bacakları. Çerçevede HER akım serisinin dört
# penceresi var; özete yalnız sayfanın konuştuğu bacaklar taşınır, çünkü
# ozet.json'un her anahtarı bir sözleşmedir ve kullanılmayan anahtar bir gün
# yanlış yere bağlanır.
KUM_OZET = (
    "kum_ay_ar_toplam_mn", "kum_ay_ar_gercek_mn", "kum_ay_ar_tuzel_mn",
    "kum_ay_pe_toplam_mn", "kum_ay_pe_gercek_mn", "kum_ay_pe_tuzel_mn",
    "kum_ay_ar_gercek_maden_mn", "kum_ay_ar_tuzel_maden_mn",
    "kum_yil_ar_toplam_mn", "kum_yil_ar_gercek_mn", "kum_yil_ar_tuzel_mn",
    "kum_yil_pe_toplam_mn", "kum_yil_ar_gercek_maden_mn",
    f"kum_{PENCERE_KISA}h_ar_toplam_mn", f"kum_{PENCERE_KISA}h_pe_toplam_mn",
    f"kum_{PENCERE_UZUN}h_ar_toplam_mn", f"kum_{PENCERE_UZUN}h_pe_toplam_mn",
)


# ===========================================================================
# yardımcılar
# ===========================================================================
def _oku(ad: str) -> pd.DataFrame:
    d = pd.read_csv(VERI / ad, index_col=0, parse_dates=True)
    return d.sort_index()


def _son_deger(df: pd.DataFrame, kol: str):
    if kol not in df.columns:
        return None
    s = df[kol].dropna()
    if not len(s):
        return None
    v = float(s.iloc[-1])
    return None if not np.isfinite(v) else v


def _f(v):
    """Sonlu bir sayı ya da None. NaN ve sonsuz DEĞER DEĞİLDİR.

    Ölçülemeyen bir büyüklük özete None olarak girer; özet üreticisi None'ı
    ATLAR ve sayfada statik yedek görünür. NaN yazmak iki ayrı kusur olurdu:
    okura sayı gibi görünen bir şey basılır, ve JSON'un NaN'ı standart dışı
    olduğu için sayfa tarafındaki okuyucu sessizce düşer.
    """
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def _json_temiz(x):
    """Ölçülemeyen her sayıyı None'a çevirir — özet ve uyarı kaydı yazılmadan önce.

    NEDEN SON KAPI: NaN, Python'un json yazıcısında sessizce `NaN` diye çıkar
    ve bu geçerli JSON değildir; sayfa tarafındaki çözümleyici o dosyayı
    OKUYAMAZ ve pano hiç görünmez. Tek tek her hesabın sonuna bakmak yerine
    yazımın hemen öncesine tek bir süzgeç kondu; ardından yazıcı katı kipte
    çağrılır, yani süzgeçten kaçan bir değer sessizce geçmez, hata verir.
    """
    if isinstance(x, dict):
        return {k: _json_temiz(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json_temiz(v) for v in x]
    if isinstance(x, (bool, str)) or x is None:
        return x
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        return _f(x)
    return x


def _yaz_json(yol, veri_) -> None:
    """Katı kipte yazım: süzgeçten kaçan bir NaN sessizce geçmesin, hata versin."""
    yol.write_text(json.dumps(_json_temiz(veri_), ensure_ascii=False, indent=1,
                              allow_nan=False), encoding="utf-8")


def _blok(df: pd.DataFrame, kolonlar: list[str], ad: str,
          cipa_kolonlari: list[str] | None = None) -> dict:
    """Bir BLOĞUN tüm anahtarlarını TEK ORTAK tarihten okur.

    Sütunların son dolu gözlemleri farklı tarihlere düşebilir: bu hatta stok
    tabloları (bie kaynağının iki ve dört numaralı tabloları) ile değişim
    tablosu ayrı yayımlanıyor ve aynı cumada bitmeyebiliyorlar. Her sütunu
    bağımsız okumak özette iki tarihi tek blokta karıştırır ve sayfa hepsini
    hattın çıpa tarihliymiş gibi yan yana basar — "aynı haftanın
    karşılaştırması" diye sunulan fark, bir haftalık tarih kaymasının kendisi
    olur. Kardeş bir hatta sayfanın METNİ bir tarihi, ŞEKLİN damgası başka
    bir tarihi söyleyecek kadar ilerlemişti.

    DEĞER ORTAK HAFTANIN KENDİSİNDEN OKUNUR — `asof` İLE DEĞİL, ve bu bir
    düzeltmedir. `asof`, ortak haftada gözlem yoksa SESSİZCE ondan önceki son
    gözlemi döndürüyordu: satır içinde deliği olan bir sütunun bir hafta
    önceki değeri, ortak haftanın damgasıyla yayımlanıyordu. Ölçüldü — iki
    sütunlu bir çerçevede ikincisinin ortak haftadaki gözlemi yokken basılan
    sayı onun bir önceki haftasınındı ve uyarı hâlâ "tümünün dolu olduğu ortak
    hafta" diyordu. Seri başına delikli indeks bu hatta YAPISALDIR: önbellek
    her seriyi kendi boş gözlemleri atılmış hâliyle saklıyor ve demet düştüğünde
    seriler tek tek çekiliyor. Ortak haftada gözlemi olmayan anahtar artık
    ÖZETE HİÇ YAZILMAZ (sayfada statik yedek görünür) ve adı `<blok>_delikli`
    alanında ayrıca durur — "kayan" ile "delikli" AYRI kusurlardır: biri geç
    biten seriyi, öteki ortasında gözlemi eksik olanı adlandırır.

    `cipa_kolonlari` verilirse ortak hafta YALNIZ o sütunlardan hesaplanır,
    ama okuma bütün sütunlar için yapılır. Gerekçesi ölçülmüş: sabit uzunluklu
    kayan pencere sütunları (dört ve on üç haftalık toplamlar) tanım gereği
    kaynak serinin ucundan geride bitebilir — tek bir boş hafta on üç hafta
    boyunca NaN üretiyor — ve bloğun tamamını bir çeyrek geriye çekiyordu.
    Pencerenin ucu bloğun saatini belirlememeli; kendisi o hafta ölçülemiyorsa
    zaten yazılmaz.

    Kayan sütunların adı özete LİSTE olarak yazılır, birleştirilmiş bir dize
    olarak değil: dize olsaydı okur diline "anahtar adı" bulgusu olarak
    sızardı (okura basılan cümle alanları yalnız metinlerdir, listeler değil).
    """
    var = [k for k in kolonlar if k in df.columns and df[k].notna().any()]
    if not var:
        return {}
    cipa_var = [k for k in (cipa_kolonlari or kolonlar) if k in var] or var
    sonlar = {k: df[k].dropna().index[-1] for k in cipa_var}
    ortak = min(sonlar.values())          # çıpa sütunlarının hepsinin dolduğu tarih
    cikti: dict = {}
    delikli: list[str] = []
    for k in var:
        v = df[k].reindex([ortak]).iloc[0]
        if pd.notna(v) and np.isfinite(float(v)):
            cikti[k] = float(v)
        else:
            delikli.append(k)
    cikti[f"{ad}_tarih"] = ortak.strftime("%Y-%m-%d")
    b = _bicim()
    if len(set(sonlar.values())) > 1:
        en_yeni = max(sonlar.values())
        kayan = [k for k, t in sonlar.items() if t != ortak]
        uyar(f"ORTAK HAFTA: {veri.blok_okur(ad)} farklı haftalarda bitiyor "
             f"({b.tarih_kisa(ortak)} ile {b.tarih_kisa(en_yeni)}); "
             f"{b.sayi(len(kayan), 0)} seri daha yeni. Ölçüm, hepsinin dolu "
             f"olduğu ortak haftaya ({b.tarih_kisa(ortak)}) çıpalandı ve "
             "sayfada bu tarih görünür.")
        cikti[f"{ad}_kayan"] = kayan
        cikti[f"{ad}_en_yeni_tarih"] = en_yeni.strftime("%Y-%m-%d")
    if delikli:
        uyar(f"ÖLÇÜM EKSİK: {veri.blok_okur(ad)} içinde "
             f"{b.sayi(len(delikli), 0)} serinin ortak haftada "
             f"({b.tarih_kisa(ortak)}) gözlemi yok; o serilerin bu koşudaki "
             "değeri yayımlanmadı ve sayfada önceki metin görünür.")
        cikti[f"{ad}_delikli"] = delikli
    return cikti


def _kaydir(s: pd.Series, k: int) -> pd.Series:
    """Bir seriyi GÖZLEM konumuyla kaydırır, takvim günüyle değil.

    Hizalama ölçümü (veri.hizalama_olc) kaydırmayı boş gözlemleri atılmış seri
    üzerinde yapıyor; buradaki kaydırmanın onunla AYNI şeyi söylemesi gerekir,
    yoksa "en iyi kaydırma" ile "uygulanan kaydırma" sessizce ayrışır ve
    ikisinin de doğru göründüğü bir kusur çıkar.
    """
    if k == 0:
        return s
    d = s.dropna()
    return d.shift(k).reindex(s.index)


def _ardisik_fark(s: pd.Series) -> pd.Series:
    """Haftalık değişim — yalnız ARDIŞIK cumalar arasında.

    Bir hafta atlanmışsa iki gözlem arasındaki fark İKİ haftalık değişimdir ve
    bir haftalık akımla karşılaştırılamaz: kimlik artığı o hafta atlanan
    haftanın akımı kadar çıkar ve gerçek bir kusur gibi görünür. Atlanan hafta
    veri katmanında zaten uyarı olarak görünüyor; burada o haftanın değişimi
    ÖLÇÜLMEMİŞ sayılır, sıfır sayılmaz.
    """
    d = s.dropna()
    if len(d) < 2:
        return pd.Series(index=s.index, dtype=float)
    fark = d.diff()
    gun = d.index.to_series().diff().dt.days
    return fark.where(gun == 7).reindex(s.index)


def _yil_basi(idx: pd.DatetimeIndex) -> pd.Timestamp | None:
    """İçinde bulunulan takvim yılının ilk gözlemi; pencere kısaysa son 53'ün ilki.

    Yıl dönünce çıpa da döner ve sayfadaki tarih özetten gelir, elle yazılmaz.

    YEDEK ÇIPANIN KOŞULU GÖZLEM SAYISIDIR — ve bu bir düzeltmedir. Önceki
    sürüm "yıl içi pencere BOŞSA" diye soruyordu; oysa son gözlem her zaman
    kendi takvim yılının içindedir, yani o küme hiç boşalmaz ve yedek dal HİÇ
    KOŞMAZDI. Korumanın var olduğu iddia edilen tek durum, korumanın
    çalışmadığı durumdu: ocak ayının ilk cumasında çıpa son haftanın KENDİSİ
    oluyor, arındırılmış pay tanım gereği ham paya eşit çıkıyor ve sayfa
    "iki ölçünün farkı 0,00 puan" diye YAPISAL bir sıfırı ölçüm gibi
    yayımlıyordu. Ölçüldü: çerçeve 1 Ocak 2027'de bitince fark tam sıfır ve
    figürün ikinci paneli tek noktadan ibaret kalıyordu.

    Eşik dört haftadır: bir pencere ölçüsünün en az bir aylık gözlem istemesi,
    "çıpadan bu yana" cümlesinin bir şey söylemesi için gereken en az şey.
    Tarihçe yedek çıpayı da taşımıyorsa (ilk koşu) elde olan ilk gözleme
    düşülür — uydurulmuş bir çıpa yerine kısa bir pencere yeğdir ve pencerenin
    kaç hafta olduğu zaten yayımlanıyor.
    """
    if idx is None or not len(idx):
        return None
    son = idx[-1]
    yil_ici = idx[idx >= pd.Timestamp(son.year, 1, 1)]
    if len(yil_ici) >= ESIK_CIPA_HAFTA:
        return yil_ici[0]
    return idx[max(0, len(idx) - 53)]


# ===========================================================================
# 1. KAPSAM KİMLİĞİ — bu katmanın TEK durdurucu denetimi
# ===========================================================================
def kapsam_kimligi(H: pd.DataFrame) -> tuple[list[str], dict]:
    """gerçek + tüzel = toplam. Bozulursa sayfadaki HER sayı yanlıştır.

    Keşifte birebir ölçüldü (148.848,7 + 82.508,3 = 231.357,0), yani bu
    "ölçülmüş kimlik" ailesindendir ve eşik konabilir. Eşiğin gerekçesi
    ESIK_KAPSAM_MN'in yanında yazılı.

    Aynı fonksiyon lira tarafındaki kardeş kimliği de ÖLÇER ama EŞİK KOYMAZ:
    lira mevduatı ile lira karşılığı YP mevduatının toplamının yurt içi
    yerleşik mevduatına eşit olup olmadığı keşifte ölçülmedi. Ölçülmemiş bir
    seviyeye eşik konmaz; artık hesaplanır, kayda geçer ve ilk gerçek koşudan
    sonra karar verilir. Bu kimlik önemsiz değil: dolarizasyon payının payda
    tarafı ona dayanıyor, yani iki bacağın aynı nüfusu anlatıp anlatmadığı
    sorusunun cevabı orada.
    """
    b = _bicim()
    dur: list[str] = []
    rapor: dict = {}
    K = set(H.columns)

    if {"stok_gercek", "stok_tuzel", "stok_toplam"} <= K:
        d = pd.DataFrame({"a": H["stok_gercek"] + H["stok_tuzel"],
                          "b": H["stok_toplam"]}).dropna()
        if len(d):
            fark = (d["a"] - d["b"]).abs()
            # YAYIM HASSASİYETİ TABANI — ölçülür, varsayılmaz. Sabit 2,0'ın
            # gerekçesi "kaynak bir ondalıkla yayımlıyor" ölçümüydü ve o ölçüm
            # 2026'da doğru; kaynak yarın hassasiyetini değiştirirse gerekçe
            # yalan olur ama sabit yerinde kalır. Ölçülen taban bu yüzden
            # yanına konuyor: etkin eşik ÜÇÜNÜN büyüğü. Bugün hiçbir şeyi
            # değiştirmiyor (ölçülen taban 0,2 · sabit 2,0) — değiştirmemesi
            # de doğrulanmış olsun diye kayda yazılıyor.
            (adim_a, hal_a) = veri.yayim_adimi_olc(d["a"])
            (adim_b, hal_b) = veri.yayim_adimi_olc(d["b"])
            taban = float(adim_a + adim_b)
            esik = np.maximum(max(ESIK_KAPSAM_MN, taban),
                              ESIK_KAPSAM_BAGIL * d["b"].abs())
            asim = fark > esik
            rapor["kapsam"] = {
                "kimlik": "TP.HPBITABLO2.11 + TP.HPBITABLO2.12 = TP.HPBITABLO2.10",
                "n": int(len(d)),
                "maks_fark_mn": float(fark.max()),
                "maks_tarih": str(fark.idxmax().date()),
                "son_fark_mn": float(fark.iloc[-1]),
                "esik_mn": ESIK_KAPSAM_MN, "esik_bagil": ESIK_KAPSAM_BAGIL,
                "yayim_taban_mn": taban,
                "yayim_adimi_hal_sol": hal_a, "yayim_adimi_hal_sag": hal_b,
                # UYGULANAN eşik de kayda girer, yalnız sabitleri değil: üç
                # kollu bir eşikte hangisinin devraldığı haftadan haftaya
                # değişir ve sabitleri okuyan biri eşiği yanlış bilir.
                "uygulanan_esik_maks_mn": float(esik.max()),
                "uygulanan_esik_son_mn": float(esik.iloc[-1]),
                # OKURA YAZILAN SAYI DA KAYDA GİRER: uyarı en büyük farkın
                # HAFTASINDAKİ eşiği yazıyor ve künyedeki en büyük eşik
                # başka bir hafta olabilir. İki sayı kayda ayrı girmezse
                # "metindeki eşik doğru mu" sorusu kayıttan cevaplanamaz.
                "uygulanan_esik_maks_fark_haftasi_mn": float(
                    esik.loc[fark.idxmax()]),
                "asim_hafta": int(asim.sum()),
                "birim": "mn USD",
                "gecti": bool(not asim.any()),
            }
            if asim.any():
                # TOLERANS DİYE YAZILAN SAYI, UYGULANAN SAYI OLMALI. Metin
                # sabit tabanı ("2,0 milyon dolar") tolerans diye yazıyordu,
                # oysa eşik ÜÇ KOLUN BÜYÜĞÜ ve bağıl kol bugünkü stokta 2,31
                # milyon dolara denk geliyor — yani haftaların yarısında
                # okura söylenen tolerans, uygulanandan küçüktü. Bir kapının
                # okura yanlış eşik bildirmesi, eşiğin kendisinin yanlış
                # olmasından ayırt edilemez: ikisi de "bu fark neden geçti"
                # sorusunu cevapsız bırakır.
                gun = fark.idxmax()
                dur.append(
                    "KAPSAM KİMLİĞİ: gerçek ve tüzel kişilerin YP mevduatı "
                    "toplamı, yurt içi yerleşiklerin toplam YP mevduatını "
                    f"vermiyor — en büyük fark {b.sayi(float(fark.max()), 1)} "
                    f"milyon dolar ({b.tarih_kisa(gun)}); o haftada uygulanan "
                    f"tolerans {b.sayi(float(esik.loc[gun]), 2)} milyon dolar "
                    f"(sabit taban {b.sayi(ESIK_KAPSAM_MN, 1)} milyon dolar, "
                    f"ölçülen yayım yuvarlaması {b.sayi(taban, 3)} milyon "
                    "dolar ve toplamın yüz binde biri arasından en büyüğü). "
                    "Kalem numaralandırması ya da birim değişmiş olabilir.")
    else:
        uyar("KAPSAM KİMLİĞİ SINANAMADI: gerçek kişi, tüzel kişi ve toplam YP "
             "mevduat serilerinin üçü birden yüklenemedi; stok kırılımının "
             "kendi içinde tutarlı olup olmadığı bu koşuda ölçülemiyor.")

    if {"mevduat_tl", "mevduat_yp_tl", "mevduat_yi"} <= K:
        d2 = pd.DataFrame({"a": H["mevduat_tl"] + H["mevduat_yp_tl"],
                           "b": H["mevduat_yi"]}).dropna()
        if len(d2):
            f2 = (d2["a"] - d2["b"]).abs()
            bagil = f2 / d2["b"].abs().clip(lower=1e-9)
            rapor["lira_tabani"] = {
                "kimlik": "TP.HPBITABLO2.3 + TP.HPBITABLO2.6 = TP.HPBITABLO2.2",
                "n": int(len(d2)),
                "maks_fark_bin_tl": float(f2.max()),
                "maks_bagil": float(bagil.max()),
                "maks_tarih": str(bagil.idxmax().date()),
                "son_fark_bin_tl": float(f2.iloc[-1]),
                "son_bagil": float(bagil.iloc[-1]),
                "birim": "bin TL",
                "esik_bagil": None,      # ÖLÇÜLMEDİ: eşik ilk gerçek koşudan sonra
                "gecti": None,
            }
    return dur, rapor


# ===========================================================================
# 2. HAFTA HİZALAMASI — ölçüm katmanının vermesi gereken TEK karar
# ===========================================================================
def hizalama_sec(H: pd.DataFrame) -> tuple[int, dict]:
    """Değişim tablosu stok tablosuyla aynı cumaya mı damgalı? Ölç ve KARAR VER.

    Varsayılan SIFIRDIR (doğal okuma: aynı cuma). Başka bir kaydırma yalnız
    şu iki koşul birden sağlanırsa benimsenir:
      · her iki bacakta da (gerçek ve tüzel) AYNI kaydırma en küçük artığı
        veriyorsa — gerçek bir damgalama farkı bacağa göre değişmez;
      · ve o kaydırmanın medyan artığı sıfır kaydırmanınkinin onda birinden
        küçükse (bkz. ESIK_HIZALAMA_ORAN).
    Marjinal bir iyileşmeye bakarak kaydırma seçmek, örneklem içi uyuma
    bakarak kural kurmaktır; bu depoda bir kez ölçüldü ve ikna edici tablonun
    örneklem dışında en kötü kural olduğu görüldü.

    Karar özete YAZILIR: kaydırma sıfır değilse okur bunu görmeli, çünkü o
    durumda yayımlanan haftalık akımlar kaynağın damgasından farklı bir
    haftaya bağlanmış olur.
    """
    b = _bicim()
    olcum = veri.hizalama_olc(H)
    tani: dict = {"aday": olcum, "secilen": 0, "esik_oran": ESIK_HIZALAMA_ORAN}
    if not olcum:
        tani["gerekce"] = ("Hizalama ölçülemedi: stok ve değişim serileri "
                           "kesişmiyor. Doğal okuma korundu.")
        return 0, tani

    def _medyan(bacak: str, k: int):
        r = (olcum.get(bacak) or {}).get("kaydirmalar", {}).get(str(k))
        return None if r is None else float(r["medyan_mutlak_artik"])

    bacaklar = [x for x in ("gercek", "tuzel") if x in olcum]
    enler = {x: olcum[x]["en_kucuk_artik_kaydirma"] for x in bacaklar}
    aday = set(enler.values())
    if len(aday) == 1:
        k = int(aday.pop())
    else:
        k = 0
        tani["gerekce"] = ("İki bacak farklı kaydırmalarda en küçük artığı "
                           "veriyor; bir damgalama farkı bacağa göre "
                           "değişmeyeceği için doğal okuma korundu.")
        if any((_medyan(x, 0) or 0.0) > ESIK_KIMLIK_MN for x in bacaklar):
            uyar("HAFTA HİZALAMASI: resmî ayrıştırmanın hangi haftaya "
                 "damgalandığı gerçek ve tüzel kişi bacaklarında farklı "
                 "çıkıyor. Ölçüm, kaynağın kendi damgasıyla yapıldı ve iki "
                 "tablo arasındaki fark olduğu gibi yayımlanıyor.")
        return k, tani

    if k == 0:
        tani["gerekce"] = ("Kaynağın kendi damgası en küçük artığı veriyor; "
                           "kaydırma uygulanmadı.")
        return 0, tani

    kararli = True
    for x in bacaklar:
        m0, mk = _medyan(x, 0), _medyan(x, k)
        if m0 is None or mk is None or mk > ESIK_HIZALAMA_ORAN * m0:
            kararli = False
    if not kararli:
        tani["gerekce"] = ("Başka bir kaydırma az farkla daha iyi görünüyor "
                           "ama fark kararlı değil; doğal okuma korundu.")
        return 0, tani

    tani["secilen"] = k
    tani["gerekce"] = ("Resmî ayrıştırma stok tablosundan farklı bir haftaya "
                       "damgalanıyor; ölçüm bu kaydırmayla yapıldı.")
    m0 = _medyan(bacaklar[0], 0)
    mk = _medyan(bacaklar[0], k)
    uyar("HAFTA HİZALAMASI: resmî ayrıştırma tablosu stok tablosuyla aynı "
         f"haftaya damgalanmıyor; {b.sayi(abs(k), 0)} haftalık kaydırmayla "
         f"ölçüldü. Kaydırmasız artığın ortancası {b.sayi(m0, 1)} milyon "
         f"dolar, kaydırmalı ölçümde {b.sayi(mk, 1)} milyon dolar.")
    return k, tani


# ===========================================================================
# 3. AYRIŞTIRMA — Δ stok ≟ arındırılmış değişim + parite etkisi
# ===========================================================================
def ayristir(H: pd.DataFrame, kaydirma: int) -> tuple[pd.DataFrame, dict]:
    """Resmî ayrıştırmayı stok değişimiyle yan yana koyar ve ARTIĞI ölçer.

    `kaydirma`nın VARSAYILANI YOKTUR ve bu bilinçlidir. Bir çağrı yerinde
    unutulursa Python hemen hata verir; varsayılan sıfır konsaydı, hizalama
    ölçümü başka bir hafta söylerken çerçeve sessizce kaynağın damgasıyla
    kurulur ve kimlik artığı gerçek bir kusur gibi görünürdü. Bu depoda aynı
    sigorta bir kez daha kondu: taşınan fiyattan sahte sıfır üreten çağrıda
    da kritik argümanın varsayılanı kaldırılmıştı.

    Kırılım bacakları (dolar · euro · diğer · maden) da buraya girer, çünkü
    aynı tablodan geliyorlar ve SEÇİLEN KAYDIRMAYI aynı biçimde taşımaları
    gerekir. Ayrı bir yerde kaydırılsalardı bir gün biri kaydırılır, öteki
    unutulurdu.

    ARTIK YAYIMLANIR. Kimlik tutmazsa hat DURMAZ: bu kimlik iki ayrı tablo
    arasında kuruluyor ve artığın kendisi okura bir şey söylüyor. Ölçülmemiş
    bir şeyi ölçülmüş gibi göstermektense fark yazılır.
    """
    b = _bicim()
    A = pd.DataFrame(index=H.index)
    K = set(H.columns)

    for etiket, stok, ar, pe in BACAKLAR:
        if stok in K:
            A[f"delta_{etiket}"] = _ardisik_fark(H[stok])
        if ar in K:
            A[f"ar_{etiket}"] = _kaydir(H[ar], kaydirma)
        if pe in K:
            A[f"pe_{etiket}"] = _kaydir(H[pe], kaydirma)
    for etiket in ("gercek", "tuzel"):
        for kir in KIRILIM:
            for onek in ("ar", "pe"):
                ad = f"{onek}_{etiket}_{kir}"
                if ad in K:
                    A[ad] = _kaydir(H[ad], kaydirma)

    bacak: dict = {}
    asan: list[str] = []
    for etiket, _stok, _ar, _pe in BACAKLAR:
        d_, a_, p_ = f"delta_{etiket}", f"ar_{etiket}", f"pe_{etiket}"
        if not {d_, a_, p_} <= set(A.columns):
            continue
        artik = A[d_] - A[a_] - A[p_]
        brut = A[a_].abs() + A[p_].abs()
        # Mutlak kol, ÖLÇÜLEN yayım hassasiyetinin altına düşemez. Δ stok iki
        # yuvarlanmış seviyenin farkı, arındırılmış ve parite de ayrı ayrı
        # yuvarlanmış: üç bağımsız ızgara. Bugün taban 25,0'ın çok altında
        # (kaynak ondalıklı yayımlıyor) ve sabit devrede kalıyor; kaynak bir
        # gün tam sayıya geçerse eşik kendiliğinden yukarı kayar. Aynı sınıf
        # kusur kırılım kimliğinde ölçüldü ve orada yanlış alarma dönüştü.
        taban_k = float(veri.yayim_adimi(A[d_]) + veri.yayim_adimi(A[a_])
                        + veri.yayim_adimi(A[p_]))
        esik = np.maximum(max(ESIK_KIMLIK_MN, taban_k),
                          ESIK_KIMLIK_BAGIL * brut)
        A[f"artik_{etiket}"] = artik
        A[f"esik_{etiket}"] = esik
        gecerli = artik.dropna()
        if gecerli.empty:
            continue
        pencere = gecerli.iloc[-KIMLIK_PENCERE:]
        p_esik = esik.reindex(pencere.index)
        asim = pencere.abs() > p_esik
        # Bağıl artık: brüt hareketin bir tabanla korunmuş payı. Taban, sıfıra
        # bölmeyi değil, hareketsiz bir haftada bağıl ölçünün patlamasını
        # önler — hareketin olmadığı yerde "yüzde kaç saptı" sorusu anlamsız.
        bagil = (gecerli.abs() / brut.reindex(gecerli.index).clip(lower=1.0))
        # BAĞIL ARTIK DA PENCERE İÇİNDEN — mutlak ölçüyle aynı pencereden.
        # Mutlak maksimum son elli iki haftadan, bağıl maksimum TAM TARİHÇEDEN
        # alınıyordu ve ikisi sayfada yan yana yayımlanıyordu: iki yıl önceki
        # tek haftalık bir revizyon "artık %455,3" diye, üstelik bu haftanın
        # tarihiyle damgalanmış olarak görünürken hemen yanında "kimlik
        # tutuyor, son elli iki haftada en büyük fark 0,0 milyon dolar"
        # yazıyordu. Ölçüldü. Bir uyarı SON PENCEREYE bakıyorsa, o uyarının
        # yanında yayımlanan her ölçü de aynı pencereden gelmelidir.
        p_bagil = bagil.reindex(pencere.index).dropna()
        bacak[etiket] = {
            "n_hafta": int(len(gecerli)),
            "pencere_hafta": int(len(pencere)),
            "artik_son_mn": float(gecerli.iloc[-1]),
            "artik_maks_mn": float(gecerli.abs().max()),
            "artik_maks_tarih": str(gecerli.abs().idxmax().date()),
            "artik_pencere_maks_mn": float(pencere.abs().max()),
            "artik_bagil_maks": float(bagil.max()),
            "artik_bagil_maks_tarih": str(bagil.idxmax().date()),
            "artik_bagil_pencere_maks": (float(p_bagil.max())
                                         if len(p_bagil) else None),
            "artik_bagil_son": float(bagil.iloc[-1]),
            "asim_hafta": int(asim.sum()),
            "birim": "mn USD",
            "yayim_taban_mn": taban_k,
            "tutuyor": bool(not asim.any()),
        }
        if asim.any():
            asan.append(etiket)

    # SINANMAMIŞ ile TUTMUYOR aynı şey değildir. Ortak haftası olmayan bir
    # kimlik için False yazmak, yapılmamış bir sınavın sonucunu bildirmek
    # olurdu; özet üreticisi None'ı atlar ve sayfada iddia görünmez.
    tutuyor = None if not bacak else all(r["tutuyor"] for r in bacak.values())
    maks_pencere = max((r["artik_pencere_maks_mn"] for r in bacak.values()),
                       default=None)
    tani = {
        "kaydirma": int(kaydirma),
        "esik_mn": ESIK_KIMLIK_MN,
        "esik_bagil": ESIK_KIMLIK_BAGIL,
        "pencere_hafta": KIMLIK_PENCERE,
        "bacak": bacak,
        "tutuyor": tutuyor,
        # Hangi bacağın açık kaldığı TANIDIR: uyarı cümlesi tek satırda
        # toplanıyor (otuz beş satırlık bir duvar kimseye okunmaz), ama
        # "gerçek kişilerde tutuyor, tüzelde tutmuyor" bilgisi kusurun nerede
        # aranacağını söyler ve koşu kaydında durur.
        "asan_bacak": asan,
        "artik_pencere_maks_mn": _f(maks_pencere),
        "artik_maks_mn": None if not bacak else _f(
            max(r["artik_maks_mn"] for r in bacak.values())),
        # TAM TARİHÇENİN maksimumu TANIDIR ve özete çıkmaz; okura giden ölçü
        # pencere içindekidir (bkz. yukarıdaki gerekçe).
        "artik_bagil_maks": None if not bacak else _f(
            max(r["artik_bagil_maks"] for r in bacak.values())),
        "artik_bagil_pencere_maks": _f(max(
            (r["artik_bagil_pencere_maks"] for r in bacak.values()
             if r["artik_bagil_pencere_maks"] is not None), default=None)),
        "n_hafta": None if not bacak else int(
            max(r["n_hafta"] for r in bacak.values())),
    }
    if not bacak:
        tani["cumle"] = ("Resmî ayrıştırma ile stok değişimi bu koşuda "
                         "karşılaştırılamadı: iki tablonun ortak haftası yok.")
        uyar("KİMLİK SINANAMADI: resmî ayrıştırma ile stok değişiminin ortak "
             "haftası yok; iki tablonun birbirini kapatıp kapatmadığı bu "
             "koşuda ölçülemiyor.")
        return A, tani

    if maks_pencere is None:
        return A, tani
    if tutuyor:
        tani["cumle"] = (
            "Resmî ayrıştırma stok değişimini kapatıyor: son "
            f"{b.sayi(KIMLIK_PENCERE, 0)} haftada en büyük fark "
            f"{b.sayi(maks_pencere, 1)} milyon dolar. Tolerans, o haftanın "
            f"brüt hareketinin {b.yuzde(ESIK_KIMLIK_BAGIL * 100, 0)}'i ya da "
            f"{b.sayi(ESIK_KIMLIK_MN, 1)} milyon dolar — hangisi büyükse.")
    else:
        tani["cumle"] = (
            "Resmî ayrıştırma ile stok değişimi arasındaki fark son "
            f"{b.sayi(KIMLIK_PENCERE, 0)} haftada en çok "
            f"{b.sayi(maks_pencere, 1)} milyon dolara çıktı ve toleransı aştı; "
            f"tolerans o haftanın brüt hareketinin "
            f"{b.yuzde(ESIK_KIMLIK_BAGIL * 100, 0)}'i ya da "
            f"{b.sayi(ESIK_KIMLIK_MN, 1)} milyon dolar. Fark ölçülüyor ve "
            "burada yayımlanıyor.")
        uyar("KİMLİK: resmî ayrıştırmanın toplamı ile stok değişimi son "
             f"{b.sayi(KIMLIK_PENCERE, 0)} haftada birbirini kapatmıyor — en "
             f"büyük fark {b.sayi(maks_pencere, 1)} milyon dolar, tolerans "
             f"{b.sayi(ESIK_KIMLIK_MN, 1)} milyon dolar. Ölçüm durdurulmadı; "
             "fark sayfada yayımlanıyor.")
    return A, tani


# ===========================================================================
# 4. KÜMÜLE AKIM — bu hattın asıl katkısı
# ===========================================================================
def kumule(A: pd.DataFrame) -> pd.DataFrame:
    """Haftalık akımları ay içinde, yıl içinde ve sabit pencerelerde toplar.

    BAŞLANGIÇ NOKTASI AÇIKÇA TANIMLIDIR ve özete yazılır (bkz. `kumule_tanisi`):
    ay içi toplam, o takvim ayına damgalı ilk cumadan başlar; yıl içi toplam, o
    takvim yılına damgalı ilk cumadan. Pencere değiştiğinde sonucun değiştiği
    okura GÖRÜNSÜN diye sabit uzunluklu iki pencere (dört ve on üç hafta) da
    hesaplanır: "aynı seri, farklı pencere, farklı sayı" bir iddia değil,
    yan yana duran bir ölçüm olur.

    ETİKET UYARISI — ölçü doğru olsa da etiket yanlışsa kusur devam eder.
    Haftalık gözlem cumaya damgalıdır ve ÖNCEKİ cumadan bu yana olan değişimi
    taşır; yani ayın ilk cuması bir önceki ayın son günlerini de kapsar. Ay
    içi toplam bu yüzden "takvim ayının akımı" DEĞİL, "o aya damgalı
    haftaların toplamı"dır. Fark küçük ama adı doğru konmazsa okur bugünün
    hareketi sanar; bu ayrım özet cümlesinde yazılı.

    ÖLÇÜLMEMİŞ BİR HAFTADAN SONRASI DA ÖLÇÜLEMEZ — ve bu bir düzeltmedir.
    `groupby().cumsum()` boş gözlemi ATLIYOR: yalnız o haftanın hücresi boş
    kalıyor, SONRAKİ her hücre o haftayı sıfır sayarak birikiyordu. Ölçüldü:
    [100 · boş · 50 · 25] dizisinin ay içi kümülesi [100 · boş · 150 · 175]
    veriyor, yani boş hafta "hareket olmadı" diye toplanıyor. Bir akım
    serisinin tek haftası eksik geldiğinde sayfa "o aya damgalı dört haftada X"
    yazıyordu ve dört haftanın biri hiç ölçülmemişti; üstelik hafta sayacı
    satır bazlı olduğu için eksilmiyordu bile. Sıfır bir ölçüm sonucudur ve
    ölçülemeyen boş bırakılır: bir grubun İLK boşluğundan sonrası SÜTUN BAZINDA
    geçersiz kılınır. Aynı mantık dolarizasyondaki birikmiş parite etkisinde
    zaten uygulanıyordu (`cumsum(skipna=False)`); iki yerde iki ayrı davranış
    olamaz.

    Kayan pencereler (`rolling`) bu maskeyi istemez: `min_periods` zaten
    penceredeki tek bir boş gözlemde NaN üretiyor, yani ölçülmemiş hafta oraya
    sızmıyor.
    """
    akim = [c for c in A.columns if c.startswith(("ar_", "pe_"))]
    K = pd.DataFrame(index=A.index)
    if not akim or not len(A.index):
        return K
    ay = A.index.to_period("M")
    yil = A.index.year
    for c in akim:
        bos = A[c].isna()
        for onek, grup in (("ay", ay), ("yil", yil)):
            # Grup içinde İLK boşluktan itibaren birikim geçersiz: o haftadan
            # sonrası "eksik haftayı sıfır sayan" bir toplam olurdu.
            gecersiz = bos.groupby(grup).cummax()
            K[f"kum_{onek}_{c}_mn"] = A[c].groupby(grup).cumsum().where(~gecersiz)
        for n in (PENCERE_KISA, PENCERE_UZUN):
            K[f"kum_{n}h_{c}_mn"] = A[c].rolling(n, min_periods=n).sum()
    return K


def pencere_kapsami(idx: pd.DatetimeIndex, n: int, cipa) -> int | None:
    """Bir sabit pencerenin GERÇEKTEN kapsadığı takvim günü sayısı.

    `rolling` GÖZLEM sayar, takvim haftası değil. Kaynak bir cumayı hiç
    yayımlamazsa "dört haftalık toplam" diye yayımlanan sayı yirmi sekiz günü
    kapsar (ölçüldü: 31.07 · 07.08 · 21.08 · 28.08 → 28 gün, oysa dört hafta
    21 gündür) ve okur onu dört haftalık bir pencerenin sonucu sanar. Ölçü
    yanlış değil, ETİKET yanlış — ve bu depoda bir kusur bir kez tam olarak
    orada durdu: sayı doğruydu, hangi seansa ait olduğunu söyleyen alan yoktu.

    NEDEN MASKELEME DEĞİL ÖLÇÜM. Sapan pencereyi boşaltmak denendi ve ölçüldü:
    on üç haftalık pencerede tek bir atlanan hafta sağ uçtaki on iki gözlemi
    birden siliyor, kümüle akım figürünün üçüncü paneli üç ay geriye düşüyor ve
    çizim katmanının uç denetimi — figürün çizdiği ucu ilan edilenden eski
    bulup — hattın TAMAMINI durduruyor. Yani kaynağın bir haftayı atlaması yine
    bütün panoyu düşürürdü; oysa bu tam olarak kaldırmaya çalıştığımız kusurun
    kendisi. Kapsam bu yüzden ÖLÇÜLÜR ve sapması okura yazılır: takvimle
    kurulmuş bir pencere (91 günlük) de aynı silmeyi yapardı.

    Δ stok tarafında aynı soruya `_ardisik_fark` yedi günlük kapıyla cevap
    veriyor; orada maskeleme doğru, çünkü bir haftalık değişim iki haftalık
    aralıkta TANIMSIZDIR — burada ise toplam tanımlı, yalnız adı eksik.
    """
    z = _bicim().tarihe_cevir(cipa) if not isinstance(cipa, pd.Timestamp) else cipa
    if z is None or idx is None or not len(idx):
        return None
    onceki = idx[idx <= pd.Timestamp(z)]
    if len(onceki) < n:
        return None
    return int((onceki[-1] - onceki[-n]).days)


def kumule_tanisi(A: pd.DataFrame, cipa) -> dict:
    """Kümüle akımın PENCERE ETİKETİ — çerçevenin ucundan değil, ÇIPADAN.

    `cipa`nın VARSAYILANI YOKTUR ve bu bilinçlidir: etiketin hangi haftaya ait
    olduğu bu ölçünün anlamıdır ve bir çağrı yerinde unutulursa Python hemen
    hata versin.

    NEDEN AYRI FONKSİYON — ölçüldü ve bir ay adı yanlış yayımlandı. Etiket
    (ay adı, başlangıç günü, toplanan hafta sayısı) çerçevenin EN YENİ dolu
    haftasından kuruluyordu; SAYI ise akım bloğunun ortak haftasından okunuyor.
    İkisi ayrıştığı an okur bir ayın sayısını başka bir ayın adıyla görür.
    Ayrışmanın en kolay tetiği on üç haftalık pencere sütunlarıydı: tek bir boş
    hafta o sütunları on üç hafta boyunca NaN yapıyor, blok o kadar geriye
    çıpalanıyordu. Ölçüldü — sayfa "Ağustos 2026 içinde, o aya damgalı dört
    haftada 302,8 milyon dolar" yazdı; 302,8 MAYIS ayının kümülesiydi ve
    Ağustos'un gerçek toplamı 1.196,0 idi. Etiket artık sayının okunduğu
    haftadan türüyor; ölçü ile etiket aynı yerden gelmezse ikisi de doğru
    görünür.
    """
    akim = [c for c in A.columns if c.startswith(("ar_", "pe_"))]
    if not akim or not len(A.index):
        return {}
    dolu = A[akim].dropna(how="all").index
    z = _bicim().tarihe_cevir(cipa) if not isinstance(cipa, pd.Timestamp) else cipa
    if z is None or not len(dolu):
        return {}
    son = pd.Timestamp(z)
    # Çıpadan SONRAKİ haftalar pencereye girmez: sayı o haftaya kadar okundu.
    dolu = dolu[dolu <= son]
    if not len(dolu):
        return {}
    ay_ici = dolu[(dolu.year == son.year) & (dolu.month == son.month)]
    yil_ici = dolu[dolu.year == son.year]
    return {
        "son_hafta": son.strftime("%Y-%m-%d"),
        "ay_bas": ay_ici[0].strftime("%Y-%m-%d") if len(ay_ici) else None,
        "ay_hafta": int(len(ay_ici)),
        "ay_etiket": ad_uzun(son),
        "yil_bas": yil_ici[0].strftime("%Y-%m-%d") if len(yil_ici) else None,
        "yil_hafta": int(len(yil_ici)),
        "yil_etiket": str(son.year),
        "pencere_kisa_hafta": PENCERE_KISA,
        "pencere_uzun_hafta": PENCERE_UZUN,
        # Pencerenin GERÇEKTEN kapsadığı takvim günü: atlanan bir hafta
        # "dört haftalık" etiketli toplamı yirmi sekiz güne uzatır.
        "pencere_kisa_kapsam_gun": pencere_kapsami(dolu, PENCERE_KISA, son),
        "pencere_uzun_kapsam_gun": pencere_kapsami(dolu, PENCERE_UZUN, son),
    }


# ===========================================================================
# 5. STOK, KIRILIM VE PAYLAR
# ===========================================================================
def stok_metrikleri(H: pd.DataFrame) -> pd.DataFrame:
    """Seviyeler milyar dolara, kırılımlar paya çevrilir.

    GENİŞ TOPLAM AYRI TUTULUR. Yurt dışı yerleşikleri de içeren toplam ile
    yalnız yurt içi yerleşikleri kapsayan toplam ayrı sütunlardır ve farkları
    ÖLÇÜLÜP yazılır. İkisini aynı şeymiş gibi yan yana koymak bu hattın en
    pahalı hatası olurdu; sayfada geçerse adıyla ve farkıyla geçmesi
    gerektiği için fark burada hesaplanır.
    """
    M = pd.DataFrame(index=H.index)
    K = set(H.columns)
    # milyon dolar → milyar dolar
    for hedef, kaynak in (("stok_toplam_mia", "stok_toplam"),
                          ("stok_gercek_mia", "stok_gercek"),
                          ("stok_tuzel_mia", "stok_tuzel"),
                          ("maden_gercek_mia", "maden_gercek"),
                          ("maden_tuzel_mia", "maden_tuzel"),
                          ("genis_toplam_mia", "genis_toplam")):
        if kaynak in K:
            M[hedef] = H[kaynak] / 1e3
    if {"maden_gercek", "maden_tuzel"} <= K:
        M["maden_toplam_mia"] = (H["maden_gercek"] + H["maden_tuzel"]) / 1e3
    if {"maden_gercek", "stok_gercek"} <= K:
        M["maden_pay_gercek"] = H["maden_gercek"] / H["stok_gercek"] * 100.0
    if {"maden_tuzel", "stok_tuzel"} <= K:
        M["maden_pay_tuzel"] = H["maden_tuzel"] / H["stok_tuzel"] * 100.0
    if {"maden_gercek", "maden_tuzel", "stok_toplam"} <= K:
        M["maden_pay_toplam"] = ((H["maden_gercek"] + H["maden_tuzel"])
                                 / H["stok_toplam"] * 100.0)
    if {"stok_gercek", "stok_toplam"} <= K:
        M["gercek_pay"] = H["stok_gercek"] / H["stok_toplam"] * 100.0
    if {"stok_tuzel", "stok_toplam"} <= K:
        M["tuzel_pay"] = H["stok_tuzel"] / H["stok_toplam"] * 100.0
    if {"genis_toplam", "stok_toplam"} <= K:
        # ADI "YURT DIŞI" DEĞİL "KAPSAM FARKI": künyenin kalem
        # numaralandırmasına göre bu fark üç bölümü birden kapsıyor
        # (1.2 + 1.3 + 1.4) ve yurt dışı yerleşik bankalar yalnız sonuncusu.
        # Anahtar adı bir SÖZLEŞMEDİR: `yurtdisi_mia` diye yazılan bir sayı,
        # sayfayı yazan bir sonraki oturuma "yurt dışı yerleşikler kırk milyar
        # dolar tutuyor" cümlesini kurdurur ve o cümle ölçülmemiştir.
        M["genis_fark_mia"] = (H["genis_toplam"] - H["stok_toplam"]) / 1e3
        M["genis_fark_pay"] = ((H["genis_toplam"] - H["stok_toplam"])
                               / H["genis_toplam"] * 100.0)
    return M


# ===========================================================================
# 6. DOLARİZASYON — ham pay ile parite etkisinden arındırılmış pay
# ===========================================================================
def dolarizasyon(H: pd.DataFrame, A: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """YP / (TL + YP). Ham pay parite hareketiyle de oynar; arındırılmışı oynamaz.

    İKİ BACAK DA LİRA CİNSİNDEN (kaynağın iki numaralı tablosunun lira
    karşılığı kalemleri). Aynı tabloda milyon dolarlık kalemler de var ve
    ikisi karıştırılırsa trilyon ölçeğinde bir birim hatası gözle
    yakalanmaz — bu yüzden birim, seri kataloğunda tek yerde duruyor ve
    dönüşüm buradan okunuyor.

    ARINDIRMANIN KURULUŞU (ve neden ima edilen kur KULLANILMIYOR):
    Payın lira bacağını sabit kurla yeniden değerlemek bir kur serisi ister;
    künyede referans bir dolar kuru YOK ve lira karşılığını dolar stokuna
    bölerek elde edilen ima edilen kur DENETLENEMEZ, dolayısıyla ne
    yayımlanır ne de bir yayımlanan sayının içine gizlenir. Bunun yerine
    payın YP bacağı, resmî parite etkisinden arındırılmış stokun ORANIYLA
    ölçeklenir:

        YP_ar(t) = YP_lira(t) · [ S(t) − Σ parite etkisi ] / S(t)

    Bu oran birimsizdir ve kuru SADELEŞTİRİR: hiçbir yerde kur hesaplanmaz.
    Ölçü şunu söyler — dolarizasyon payının çıpadan bu yana değişiminin ne
    kadarı, sepetin dolar karşısındaki değerlenmesi ve kıymetli maden fiyatı
    yüzünden. Liranın dolar karşısındaki hareketi BU ÖLÇÜNÜN DIŞINDADIR ve
    olması gereken de budur: kaynağın arındırdığı şey paritedir.

    Parite etkisi stokun kendisinden ÇIKARILIR (stoka arındırılmış akımlar
    EKLENMEZ). İki yol kimlik tam kapansaydı aynı olurdu; kapanmadığında
    ekleme yolu kimlik artığını da biriktirir ve arındırılmış stok gerçek
    stoktan artık kadar uzaklaşır. Çıkarma yolu, sapmayı tam olarak
    ölçtüğümüz şeyle (birikmiş parite etkisi) sınırlı tutar.

    ÇIPADAN ÖNCESİ BOŞ BIRAKILIR. Arındırılmış pay ÇIPAYA GÖRE tanımlıdır;
    seriyi çıpanın gerisine uzatmak arındırmanın anlamını sessizce tersine
    çevirir. Çıpa her takvim yılında döner, böylece birikmiş artık da bir yılla
    sınırlı kalır.
    """
    b = _bicim()
    D = pd.DataFrame(index=H.index)
    K = set(H.columns)
    if not {"mevduat_tl", "mevduat_yp_tl"} <= K:
        uyar("DOLARİZASYON ÖLÇÜLEMEDİ: mevduatın lira ve yabancı para "
             "bacakları bu koşuda yüklenemedi; pay hesaplanmadı.")
        return D, {}

    tl, yp = H["mevduat_tl"], H["mevduat_yp_tl"]
    D["mevduat_tl_mlr"] = tl / 1e6          # bin TL → milyar TL
    D["mevduat_yp_mlr"] = yp / 1e6
    D["dol_pay_ham"] = yp / (tl + yp) * 100.0

    if "stok_toplam" not in K or "pe_toplam" not in A.columns:
        tani = {"cipa": None, "yontem": "yalnız ham pay",
                "not": ("Parite etkisinden arındırılmış pay bu koşuda "
                        "kurulamadı: arındırma için gereken seriler eksik.")}
        uyar("DOLARİZASYON: parite etkisinden arındırılmış pay bu koşuda "
             "hesaplanamadı; sayfada yalnız ham pay görünür.")
        return D, tani

    ortak = D[["dol_pay_ham"]].dropna().index.intersection(
        H["stok_toplam"].dropna().index).intersection(A["pe_toplam"].dropna().index)
    cipa = _yil_basi(ortak)
    if cipa is None:
        return D, {"cipa": None, "yontem": "yalnız ham pay"}

    pe = A["pe_toplam"].reindex(H.index)
    # Çıpadan SONRAKİ haftaların parite etkisi birikir; çıpa haftasının kendisi
    # toplama girmez (çıpada arındırılmış pay ham paya eşittir, tanım gereği).
    seg = pe.where(pe.index > cipa, 0.0)
    # skipna=False BİLİNÇLİ: bir haftanın parite etkisi ölçülmemişse o
    # haftadan sonrası için birikmiş parite de bilinmiyordur. Boş gözlemi sıfır
    # saymak, ölçülmemiş bir şeyi "parite etkisi olmadı" diye yayımlamak olurdu.
    kum = seg.cumsum(skipna=False)
    S = H["stok_toplam"]
    oran = (S - kum) / S
    yp_ar = yp * oran
    D["mevduat_yp_ar_mlr"] = yp_ar / 1e6
    D["dol_pay_ar"] = yp_ar / (tl + yp_ar) * 100.0
    D["pe_kum_cipa_mn"] = kum
    D.loc[D.index < cipa, ["dol_pay_ar", "mevduat_yp_ar_mlr", "pe_kum_cipa_mn"]] = np.nan
    D["dol_pay_fark"] = D["dol_pay_ham"] - D["dol_pay_ar"]

    ham = D["dol_pay_ham"].dropna()
    ar = D["dol_pay_ar"].dropna()
    son = ham.index[-1] if len(ham) else None
    tani = {
        "cipa": cipa.strftime("%Y-%m-%d"),
        "cipa_etiket": ad_gun(cipa),
        # Her sayı _f'den geçer: ölçülemeyen değer NaN olarak değil None
        # olarak kayda girer. NaN okura "nan" diye basılabilir ve özet
        # dosyasını geçerli JSON olmaktan çıkarır.
        # ÇIPADAKİ pay ÇIPANIN KENDİ haftasından okunur. `asof` burada da
        # doğru sonucu verirdi (çıpa üç serinin ortak indeksinden seçiliyor,
        # yani o hafta doluluğu garanti), ama geriye doldurma bu dosyada bir
        # kez gerçek bir kusur üretti ve kalıp kopyalanmasın diye burada da
        # yazılmadı: ölçülemeyen bir hafta boş kalır, taşınmaz.
        "ham_cipa": _f(ham.reindex([cipa]).iloc[0]) if len(ham) else None,
        "ham_son": _f(ham.iloc[-1]) if len(ham) else None,
        "ar_son": _f(ar.iloc[-1]) if len(ar) else None,
        "fark_son": (_f(ham.iloc[-1] - ar.iloc[-1])
                     if len(ham) and len(ar) and ham.index[-1] == ar.index[-1]
                     else None),
        "pe_kum_son_mn": _f(D["pe_kum_cipa_mn"].dropna().iloc[-1])
        if D["pe_kum_cipa_mn"].notna().any() else None,
        "son_hafta": son.strftime("%Y-%m-%d") if son is not None else None,
        "yontem": ("arındırılmış pay, resmî parite etkisinin çıpadan bu yana "
                   "birikmiş toplamı stoktan düşülerek kuruldu; kur serisi "
                   "kullanılmadı"),
    }
    # Cümle yalnız DÖRT ölçünün de var olduğu koşuda kurulur; biri eksikken
    # kurmak sayfaya "iki ölçünün farkı — puan" gibi bir cümle basardı.
    if None not in (tani["ham_cipa"], tani["ham_son"], tani["ar_son"],
                    tani["fark_son"]):
        tani["cumle"] = (
            f"Dolarizasyon payı {b.tarih_uzun(cipa)} çıpasında "
            f"{b.yuzde(tani['ham_cipa'], 1)}, son haftada "
            f"{b.yuzde(tani['ham_son'], 1)}. Resmî parite etkisinden "
            f"arındırıldığında son haftadaki pay {b.yuzde(tani['ar_son'], 1)}; "
            f"iki ölçünün farkı {b.sayi(tani['fark_son'], 2)} puan.")
    return D, tani


# ===========================================================================
# 7. AYRIŞMA — gerçek kişi ile tüzel kişi ters yönde mi?
# ===========================================================================
def ayrisma_olc(A: pd.DataFrame, M: pd.DataFrame) -> dict:
    """Gerçek ve tüzel kişilerin akımları ve payları ölçülür — KURAL KURULMAZ.

    Burada yalnız ÖLÇÜM var: kaç haftada işaretler ters, iki akımın
    korelasyonu ne, paylar nerede. Bir düzenlilik görülse bile koda kural
    olarak girmez ve sayfada "şu grup şöyle davranır" diye yazılmaz; bu
    depoda ikna edici bir aylık örüntü tam olarak böyle sınandı ve örneklem
    dışında en kötü kural olduğu görüldü.

    Örneklem İKİYE bölünüp oran ayrı ayrı yazılır. Sebebi doğrudan bu: bir
    oranın örneklemin iki yarısında birbirini tutup tutmadığı, tek bir
    ortalamanın söylemediği şeyi söyler — okur örüntünün ne kadar kararlı
    olduğunu kendisi görür.

    Örneklem yetmiyorsa hiçbir sayı yazılmaz ve sebebi kaydedilir.
    """
    if not {"ar_gercek", "ar_tuzel"} <= set(A.columns):
        return {"yeterli": False, "sebep": "iki bacak birden ölçülemedi"}
    d = A[["ar_gercek", "ar_tuzel"]].dropna()
    n = int(len(d))
    if n < ESIK_TARIHCE_HAFTA:
        return {"n_hafta": n, "asgari_hafta": ESIK_TARIHCE_HAFTA,
                "yeterli": False,
                "sebep": ("örneklem bir yıllık haftalık gözlemin altında; "
                          "işaret oranı ve korelasyon yazılmadı")}

    isaret = np.sign(d["ar_gercek"]) * np.sign(d["ar_tuzel"])
    ters = int((isaret < 0).sum())
    ayni = int((isaret > 0).sum())
    sifir = int((isaret == 0).sum())
    oran = (ters / (ters + ayni)) if (ters + ayni) else None

    def _oran(pay: pd.DataFrame):
        i = np.sign(pay["ar_gercek"]) * np.sign(pay["ar_tuzel"])
        t, a = int((i < 0).sum()), int((i > 0).sum())
        return (t / (t + a)) if (t + a) else None

    yari = n // 2
    o1, o2 = _oran(d.iloc[:yari]), _oran(d.iloc[yari:])
    # Korelasyon, bir bacak sabitse TANIMSIZDIR; tanımsızı sayı diye yazmayız.
    korel = _f(d["ar_gercek"].corr(d["ar_tuzel"]))
    son = d.tail(min(ESIK_TARIHCE_HAFTA, n))
    korel_son = _f(son["ar_gercek"].corr(son["ar_tuzel"]))
    return {
        "n_hafta": n, "yeterli": True,
        "ters_hafta": ters, "ayni_hafta": ayni, "sifir_hafta": sifir,
        "ters_oran": oran, "ters_oran_ilk_yari": o1, "ters_oran_ikinci_yari": o2,
        "korel": korel, "korel_son_pencere": korel_son,
        "pencere_hafta": int(len(son)),
        "gercek_pay_son": _son_deger(M, "gercek_pay"),
        "tuzel_pay_son": _son_deger(M, "tuzel_pay"),
        "hukum": ("Bu bir ölçümdür, kural değildir: örneklem dışı sınanmadan "
                  "bir davranış kuralına dönüştürülmez."),
    }


# ===========================================================================
# 8. SIFIR — ölçüm mü, ölçümün yokluğu mu?
# ===========================================================================
def _sag_uc_sifir(s: pd.Series) -> int:
    """Serinin SAĞ UCUNDAKİ kesintisiz tam sıfır bloğunun uzunluğu (hafta)."""
    d = s.dropna()
    if d.empty or float(d.iloc[-1]) != 0.0:
        return 0
    n = 0
    for v in d.to_numpy()[::-1]:
        if float(v) != 0.0:
            break
        n += 1
    return int(n)


def _hukumsuz_cumle(hukumsuz: list[str], H: pd.DataFrame,
                    olculen_seri: int) -> str:
    """Baştan sona sıfır ÇIKAN ama üzerine hüküm KURULAMAYAN seriler.

    NEDEN AYRI BİR CÜMLE. "Bu bacak serinin ilk gözleminden beri sıfır"
    demek, elimizdeki ilk gözlemin SERİNİN ilk gözlemi olduğunu varsayar.
    Başlangıcı ölçülmemiş bir seride bu varsayım tutmaz: elimizdeki ilk
    gözlem, kaynağın ilk gözlemi değil SORGUNUN alt sınırı olabilir — ve
    ikisi tıpatıp aynı görünür. Bu hatta tam olarak bu oldu: yirmi iki seri
    yıllarca 2024 başında başlıyor sanıldı, oysa 2014'te başlıyorlardı.

    Sıfırın kendisi ÖLÇÜLDÜ ve yazılır; ölçülmeyen şey onun ne anlama
    geldiğidir. "Yapısal" demek de "donmuş" demek de aynı ölçülmemiş adımı
    atlar, bu yüzden ikisi de denmez ve eksik olan ADIYLA yazılır — okur
    bunun bir belirsizlik değil, bizim henüz sormadığımız bir soru olduğunu
    görsün.
    """
    b = _bicim()
    if not olculen_seri:
        return ("Başlangıcı ölçülmediği için hüküm kurulamayan bir sıfır var "
                "mı, bu koşuda ölçülemedi: gözlem yüklenemedi.")
    if not hukumsuz:
        return ("Başlangıcı ölçülmediği için hüküm kurulamayan bir sıfır bu "
                f"koşuda yok: ölçülen {b.sayi(olculen_seri, 0)} serinin "
                "baştan sona sıfır olanlarının hepsinde ya sıfırın kayda "
                "geçmiş bir gerekçesi var ya da kaynağın ilk gözlemi "
                "ölçülmüş.")
    n = min(int(H[a].dropna().shape[0]) for a in hukumsuz)
    return (f"{veri._adlar(hukumsuz, en_fazla=min(len(hukumsuz), 6))} serisi "
            f"elimizdeki {b.sayi(n, 0)} haftanın tamamında tam sıfır. Bu "
            "sıfırın serinin başından beri sürüp sürmediği SÖYLENEMEZ: "
            "kaynağın bu seriyi ne zaman yayımlamaya başladığı ölçülmedi, "
            "yani elimizdeki ilk gözlem serinin ilk gözlemi olmayabilir. "
            "Ölçülen sıfır yazıldı, üzerine hüküm kurulmadı.")


# MANŞET AKIM — sınırın büyüklüğü NEYE göre yazılacak.
# Hattın okura verdiği asıl ürün parite etkisinden arındırılmış akımdır ve
# kırılım bacakları onun İÇİNDEDİR. Bir bacağın parite etkisi hiç
# yayımlanmıyorsa sınır o bacakta kalmaz, manşete taşınır; büyüklüğü de ancak
# manşetin yanında anlam taşır ("98,5 milyon dolar" tek başına büyük mü küçük
# mü olduğunu söylemez).
MANSET_AKIM = "ar_toplam"


def _tanim_cumle(tanim: list[str], olculen_bas, olculen_seri: int) -> str:
    """TANIM GEREĞİ SIFIR — dayanağı veride değil ARİTMETİKTE olan sıfır.

    NEDEN AYRI BİR SINIF VE AYRI BİR CÜMLE. Baştan sona sıfır çıkan bütün
    bacaklar tek bir cümlede toplanıyordu ve o cümle hepsi için birden "bu bir
    ölçümdür, donmuş besleme değil" diyordu. Ölçüm DONMAYI eliyor; üçüncü bir
    hâli — kaynağın o bacağı hiç hesaplamıyor olması — elemiyor. Dolar
    bacaklarında üçüncü hâlin sorulmasına gerek yok: dolar cinsi bir mevduatın
    dolar olarak ölçülen parite etkisi zaten olamaz. Öteki bacaklarda ise
    dayanak YOK ve onlar kendi cümlelerinde anılır. İkisini aynı kutuda aynı
    ağırlıkta anmak, dayanaksız olana dayanağı olanın gücünü ödünç verirdi.

    HAFTA SAYILMIYOR ve bu bilinçli: hüküm veriden gelmiyor. Kaç hafta
    ölçüldüğünü yazmak, sıfırın dayanağı gözlem sayısıymış gibi görünürdü —
    oysa bir hafta ölçülseydi de, bin hafta ölçülseydi de aynı şey doğru
    olurdu. Bu yüzden bu sınıf, başlangıcı ölçülmemiş bir seride de kurulur:
    hüküm kapısının koruduğu dayanak ("serinin öncesi yok") burada hiç
    kullanılmıyor. Ölçülmemiş başlangıç yine de ADIYLA anılır, çünkü okurun
    bilmesi gereken şey hükmün neye dayandığı kadar neye dayanmadığıdır.
    """
    b = _bicim()
    if not olculen_seri:
        return ("Tanım gereği sıfır olması beklenen bacaklar bu koşuda "
                "ölçülemedi: gözlem yüklenemedi.")
    if not tanim:
        return ("Tanım gereği sıfır olan bir bacak bu koşuda bulunmadı: "
                f"ölçülen {b.sayi(olculen_seri, 0)} serinin hiçbirinde "
                "sıfırın kayda geçmiş bir gerekçesi yok.")
    # Gerekçe TEKİLLEŞTİRİLİR: iki dolar bacağı aynı aritmetiği taşıyor ve
    # aynı cümleyi iki kez yazmak okura iki ayrı dayanak varmış gibi görünür.
    gerekce = list(dict.fromkeys(veri.TANIM_SIFIRI[a] for a in tanim))
    parca = [f"{veri._adlar(tanim, en_fazla=min(len(tanim), 6))} serisinde "
             f"sıfır TANIM GEREĞİDİR: {'; '.join(gerekce)}. Bu hüküm gözlem "
             "sayısına dayanmıyor — ortada ölçülecek bir büyüklük yok."]
    eksik = [a for a in tanim if a not in set(olculen_bas)]
    if eksik:
        parca.append(
            f"Bunlardan {veri._adlar(eksik, en_fazla=min(len(eksik), 4))} "
            "serisinin kaynakta ne zaman yayımlanmaya başladığı ölçülmedi; "
            "tanım gereği sıfır hükmü buna dayanmıyor, elimizdeki haftaların "
            "tamamı da onunla uyumlu.")
    return " ".join(parca)


def _dayanaksiz_cumle(dayanaksiz: list[str], H: pd.DataFrame,
                      tanim: list[str], hukumsuz: list[str],
                      olculen_seri: int) -> tuple[str, dict]:
    """DAYANAĞI OLMAYAN SIFIR — ölçüleni yaz, ötesine geçme.

    NE ÖLÇÜLDÜ. (a) Elimizdeki haftaların tamamında sıfır ve bir kez bile
    sıfırdan farklı değer yayımlanmamış — bu DONMAYI eler, çünkü yayımı duran
    bir seri önce sıfırdan farklı değerler gösterir, sonra sıfıra düşer.
    (b) Aynı kırılımın öteki bacakları aynı dönemde hareket ediyor. (c) Aynı
    kesenin ARINDIRILMIŞ akımı hareketli, yani kese ölü değil.

    NE ÖLÇÜLMEDİ. Kaynağın bu bacağı nasıl hesapladığı. Yöntem belgesi
    okunmadı ve okunmadan "kaynak bunu hesaplamıyor" cümlesi kurulamaz.
    Kurulabilecek en güçlü cümle şudur: sıfır, hareketin yokluğu değil
    ÖLÇÜNÜN yokluğu olabilir ve ikisi elimizdeki gözlemle ayırt edilemez.

    VE BUNUN MANŞETE DOKUNAN BİR SONUCU VAR. Parite etkisi hiç yayımlanmayan
    bir bacakta, arındırılmış akım da parite etkisinden arındırılmamış
    olabilir; o bacak manşet akımın içindedir. Arındırmanın ne kadar eksik
    kaldığı ölçülemez — ölçülemeyen şeyin kendisi odur. Ölçülebilen şey
    ETKİLENEN DİLİMİN büyüklüğüdür ve o yazılır: ne abartılır, ne gizlenir.

    ADLANDIRMA İLE ÖLÇÜM AYNI SERİ KÜMESİNDEN TÜRER. Kıyas cümlesi kısa
    adlarla kuruluyor ("euro ve kıymetli maden") ama sayılar seri seri
    ölçülüyordu ve iki küme AYRI süzülüyordu: adı anılmayan bir bacağın gözlem
    sayısı, anılan bacaklara yakıştırılıyordu. Yapısal bir bacak bir gün
    sıfırdan farklı bir değer yayımlarsa (kapının izlediği olayın ta kendisi)
    kısa adı hem sıfır hem hareketli kümede birden geçer; o hâlde kısa ad
    AYIRT EDİCİ DEĞİLDİR ve parça HİÇ YAZILMAZ. Bir cümle parçasının kendi
    ölçüm koşulu tutmuyorsa o parça yazılmaz — ölçülmemiş bir parça,
    ölçülmüşlerin yanında onlardan ayırt edilemez.
    """
    b = _bicim()
    tani: dict = {}
    if not olculen_seri:
        return ("Dayanağı olmayan bir sıfır var mı, bu koşuda ölçülemedi: "
                "gözlem yüklenemedi.", tani)
    if not dayanaksiz:
        return ("Gerekçesi kayıtlı olmayan, baştan sona sıfır bir bacak bu "
                f"koşuda yok: ölçülen {b.sayi(olculen_seri, 0)} serinin "
                "hiçbiri elimizdeki haftaların tamamında sıfır değil.", tani)

    # HAFTA SAYISI EN KISA SERİDEN: seriler farklı uzunlukta olabilir ve en
    # uzununu yazmak, kısa olan hakkında ölçülmemiş bir şey söylemek olurdu.
    n = min(int(H[a].dropna().shape[0]) for a in dayanaksiz)
    tani["hafta"] = int(n)
    tani["seri"] = list(dayanaksiz)
    parca = [f"{veri._adlar(dayanaksiz, en_fazla=min(len(dayanaksiz), 6))} "
             f"serisi elimizdeki {b.sayi(n, 0)} haftanın tamamında tam sıfır "
             "ve bir kez bile sıfırdan farklı bir değer yayımlanmamış. Donmuş "
             "besleme bunu açıklamıyor: yayımı duran bir seri önce sıfırdan "
             "farklı değerler gösterir, sonra sıfıra düşer — burada öncesi yok."]

    # (a) AYNI KIRILIMIN ÖTEKİ BACAKLARI. Kıyas yalnız dokunulan kırılımların
    # içinde kurulur: bütün kırılımlara bakılsaydı cümle, parite etkisi
    # hakkında başka bir tablonun gözlemiyle kurulmuş olurdu.
    tam_sifir = set(dayanaksiz) | set(tanim) | set(hukumsuz)
    dokunan = [k for k in veri.KIRILIMLAR
               if any(a in dayanaksiz for a in k.parcalar)]
    sifir_ad: list[str] = []
    oteki: list[str] = []
    for kir in dokunan:
        for a in kir.parcalar:
            if a in dayanaksiz:
                sifir_ad.append(a)
            elif a in tam_sifir:
                # BAŞKA BİR SINIFIN SIFIRI. O da baştan sona sıfır; "öteki
                # bacaklar hareket gösteriyor" kıyasında anmak cümleyi kendi
                # ölçümüne aykırı yapardı.
                continue
            else:
                oteki.append(a)
    kisa_sifir = list(dict.fromkeys(veri.bacak_kisa_adi(a) for a in sifir_ad))
    kisa_oteki = list(dict.fromkeys(veri.bacak_kisa_adi(a) for a in oteki))
    belirsiz = sorted(set(kisa_sifir) & set(kisa_oteki))
    dolu = [int((H[a].dropna() != 0).sum()) for a in oteki if a in H.columns]
    kapsam = [int(H[a].dropna().shape[0]) for a in oteki if a in H.columns]
    tani["kiyas_belirsiz_kisa_ad"] = belirsiz
    tani["kiyas_oteki_seri"] = list(oteki)
    if kisa_sifir and kisa_oteki and not belirsiz and dolu and min(dolu) > 0:
        # Öteki bacaklar SAYIYLA anlatılır, sıfatla değil: "aynı haftalarda
        # sıfırdan farklı" demek onların hiç sıfır çıkmadığını İDDİA etmektir.
        # En SEYREK olanı yazılır — cümlenin taşıdığı en zayıf gözlem hangisi
        # ise okur onu görür.
        # Aynı sayıyı iki kez okutmak okura ikincisini bir alt küme
        # sandırır; tam kapsama TAMAMI diye yazılır.
        say = (f"ölçülen {b.sayi(min(kapsam), 0)} haftanın tamamında sıfırdan "
               "farklı" if min(dolu) == min(kapsam)
               else "en seyreğinde bile sıfırdan farklı gözlem sayısı "
                    f"{b.sayi(min(dolu), 0)} hafta, ölçülen toplam "
                    f"{b.sayi(min(kapsam), 0)} hafta")
        parca.append(
            f"Aynı kırılımların öteki bacakları ({' ve '.join(kisa_oteki)}) "
            f"aynı dönemde hareket gösteriyor: {say}.")

    # (b) KESENİN KENDİSİ ÖLÜ MÜ? Parite etkisi sıfır olan bacağın AYNI
    # kesedeki arındırılmış akımı. Hareketliyse "o kesede hiçbir şey olmuyor"
    # açıklaması da elenir; hareketsizse böyle bir cümle KURULMAZ.
    es = [veri.arindirilmis_esi(a) for a in dayanaksiz]
    ar_kol = [a for a in es if a and a in H.columns]
    kese = (H[ar_kol].sum(axis=1, min_count=len(ar_kol)).dropna()
            if ar_kol else pd.Series(dtype=float))
    dolu_ar = int((kese != 0).sum()) if len(kese) else 0
    tani["kese_seri"] = list(ar_kol)
    tani["kese_hafta"] = int(len(kese))
    tani["kese_sifirdisi_hafta"] = dolu_ar
    if len(kese) and dolu_ar:
        tani["kese_medyan_mn"] = float(kese.abs().median())
        tani["kese_maks_mn"] = float(kese.abs().max())
        # "139 haftanın 139 haftasında" diye yazmak sayıyı iki kez okutur ve
        # okur ikincisini bir alt küme sanar; tam kapsama TAMAMI diye yazılır.
        kac = ("tamamında" if dolu_ar == len(kese)
               else f"{b.sayi(dolu_ar, 0)} haftasında")
        # "toplamı" ancak toplanacak birden çok bacak varsa yazılır: tek
        # bacakta okur, olmayan bir toplama işlemi arar.
        govde = (f"{veri._adlar(ar_kol, en_fazla=min(len(ar_kol), 4))}"
                 + (" toplamı" if len(ar_kol) > 1 else ""))
        parca.append(
            f"Aynı kesenin arındırılmış akımı ise hareketli: {govde} ölçülen "
            f"{b.sayi(len(kese), 0)} haftanın {kac} sıfırdan farklı.")

    # (c) HÜKÜM — ölçümün kapsadığı yere kadar, bir adım ötesine değil.
    # HÜKÜM CÜMLESİ KAÇ GÖZLEME DAYANDIĞINI SAYMAZ: yukarıdaki parçaların
    # her birinin kendi ölçüm koşulu var ve tutmayan parça hiç yazılmıyor.
    # "Bu üç gözlem" diye başlayan bir cümle, iki parçanın yazıldığı bir
    # koşuda olmayan bir gözleme dayanıyormuş gibi görünürdü.
    parca.append(
        "Ölçülenler birlikte şunu söylüyor: sıfır, hareketin yokluğu değil "
        "ÖLÇÜNÜN yokluğu olabilir ve ikisi elimizdeki gözlemle ayırt "
        "edilemez. Kaynağın bu bacağı nasıl hesapladığı ölçülmedi; yöntem "
        "belgesi okunmadı ve okunmadan kaynak adına bir cümle kurulmaz.")

    # (d) SONUÇ VE BÜYÜKLÜĞÜ.
    manset = (H[MANSET_AKIM].dropna() if MANSET_AKIM in H.columns
              else pd.Series(dtype=float))
    ortak = kese.index.intersection(manset.index) if len(kese) else []
    if len(ortak) and dolu_ar:
        k2 = kese.loc[ortak].abs()
        m2 = manset.loc[ortak].abs()
        oran = float((k2 / m2.clip(lower=1e-9)).median() * 100.0)
        tani["manset_medyan_mn"] = float(m2.median())
        tani["kese_manset_oran_medyan_pay"] = oran
        parca.append(
            "Bunun manşete dokunan bir sonucu var: parite etkisi hiç "
            "yayımlanmayan bir bacakta arındırılmış akım da parite "
            "etkisinden gerçekte arındırılmamış olabilir ve o bacak manşet "
            "akımın içindedir. Arındırmanın ne kadar eksik kaldığı "
            "ölçülemez — ölçülemeyen şeyin kendisi odur; ölçülebilen şey "
            "etkilenen dilimin büyüklüğüdür. Bu kesenin haftalık akımının "
            f"mutlak medyanı {b.sayi(float(k2.median()), 1)} milyon dolar, "
            f"manşet akımınki {b.sayi(float(m2.median()), 1)} milyon dolar; "
            f"haftalık oranın medyanı {b.yuzde(oran, 1)}, kesenin en büyük "
            f"haftası {b.sayi(float(k2.max()), 1)} milyon dolar. Manşet bu "
            "yüzden geçersiz olmuyor, ama bu dilim kadar bir belirsizlik "
            "taşıdığı bilinerek okunur.")
    return " ".join(parca), tani


def sifir_olc(H: pd.DataFrame, kolonlar, esik_hafta: int,
              olculen_bas) -> tuple[list[str], dict]:
    """Sıfırları ÖLÇER ve raporlar; MASKELEMEZ. Gerekçesi aşağıda.

    Argümanların VARSAYILANI YOKTUR: hangi bacaklara bakıldığı, eşiğin ne
    olduğu ve hangi serilerin BAŞLANGICININ ÖLÇÜLDÜĞÜ bu ölçünün anlamını
    belirliyor; unutulursa Python hemen hata versin. Sessizce yanlış kapsamla
    koşan bir sıfır denetimi, hiç koşmayandan kötüdür.

    BEŞ HÂL. Üçüncüsü hattın ilk gerçek koşusunda, dördüncüsü tarihçenin
    ölçülen başa çekildiği gün, beşincisi de "ölçüm donmayı eler ama
    ölçülmemişliği elemez" kusuru görüldüğünde eklendi.

      (i)   blok = bütün seri VE sıfırın kayda geçmiş bir GEREKÇESİ var →
            TANIM SIFIRI. Hüküm veriden değil aritmetikten gelir; hafta
            sayılmaz, başlangıcın ölçülmüş olması da gerekmez.
      (ii)  blok = bütün seri, gerekçe YOK, başlangıç ölçülmüş → DAYANAKSIZ
            SIFIR. Ölçülen yazılır (donma elenir), hüküm kurulmaz; manşete
            dokunan sonucu büyüklüğüyle birlikte yazılır.
      (iii) blok = bütün seri, gerekçe yok, başlangıç ÖLÇÜLMEMİŞ → HÜKÜM
            KURULMAZ. Sıfır ölçüldü, anlamı ölçülmedi.
      (iv)  blok sağ uçta ama öncesinde sıfırdan farklı gözlem var → gerçekten
            AYIRT EDİLEMEZ; uyarı düşer.
      (v)   blok serinin ortasında → ölçüm; arkasından gerçek bir gözlem
            gelmiştir, uyarı yok.

    (i) ile (ii) NEDEN AYRILDI. İkisi bir zamanlar tek sınıftı ve tek cümle
    hepsi için birden "bu bir ölçümdür, donmuş besleme değil" diyordu. Ölçüm
    donmayı eliyor; ÜÇÜNCÜ bir hâli — kaynağın o bacağı hiç hesaplamıyor
    olmasını — elemiyor. Ve veri o üçüncü hâle işaret ediyordu: dolar dışı
    kese canlı (arındırılmış akımı haftadan haftaya hareket ediyor) ama parite
    etkisi tam sıfır; oysa dolar dışı bir kesenin dolara karşı parite etkisi,
    çapraz kur kımıldadığı sürece sıfır olamaz. Dolar bacaklarında ise sıfır
    tanım gereğidir ve orada "bu bir ölçümdür" DOĞRU. Ayırt edilebilene "ayırt
    edilemiyor" demek yanlıştı; ayırt edilemeyene "ölçümdür" demek de yanlış.

    (iii) NEDEN VAR. Yapısal hükmün dayanağı "serinin öncesi yok" cümlesidir
    ve o cümle ancak elimizdeki ilk gözlem SERİNİN ilk gözlemiyse doğrudur.
    Bu hatta öyle değildi: katalogdaki başlangıç elle yazılmış bir sabitti,
    çekimin alt sınırıydı ve kapsam denetiminin ölçütüydü — üç yer birbirini
    doğruluyor görünürken hiçbiri ölçmüyordu. 2005'ten sorulduğunda tarihçenin
    139 değil 653 hafta olduğu çıktı; hüküm bu kez GÜÇLENDİ ama bu bir şans
    meselesiydi. Kapı hükmün sonucunu değil DAYANAĞINI sorar — ve yalnız o
    dayanağı KULLANAN sınıfa uygulanır: tanım sıfırı onu hiç kullanmaz.

    TANIM SIFIRININ ÇELİŞMESİ DE ÖLÇÜLÜR. Kayda geçmiş bir gerekçe, sıfırın
    ölçülmeden önce bilindiğini söyler; o bacakta sıfırdan farklı bir değer
    çıkarsa yanlış olan gerekçe ya da kalem eşleşmesidir ve bu bir uyarıdır.
    Bir iddianın YANLIŞLANABİLİR olması onun ölçülebilir olmasıdır; hiçbir
    denetimin bakmadığı bir iddia, sınanmamış bir kural olarak kalır.

    NEDEN MASKELEME YOK — ve bu bir eksiklik değil, ölçülmüş bir karar:
    Bu depoda taşınan bir fiyattan doğan sahte sıfırlar maskelendi, ama orada
    KANIT vardı: sıfırların tamamının taşımadan doğduğu 918 iş gününde
    ölçülmüştü. Burada öyle bir kanıt YOK. Bu hattın serileri taşınmıyor:
    yayım dursa gözlem gelmez, boş kalır — sıfır GÖRÜNMEZ. Maskelemek "bu bir
    ölçüm değildir" demektir; bu da ölçülmemiş bir iddiadır.
    """
    b = _bicim()
    olculen = set(olculen_bas)
    rapor: dict = {"esik_hafta": int(esik_hafta),
                   "bas_olculen_seri": len(olculen), "seri": {}}
    uzun: list[str] = []
    tanim: list[str] = []
    dayanaksiz: list[str] = []
    hukumsuz: list[str] = []
    celiski: list[str] = []
    en_uzun = 0
    for ad in kolonlar:
        if ad not in H.columns:
            continue
        d = H[ad].dropna()
        if d.empty:
            continue
        sag = _sag_uc_sifir(H[ad])
        ic = int((d.iloc[:len(d) - sag] == 0).sum()) if sag < len(d) else 0
        # Serinin TAMAMI sıfırsa eşik hiç sorulmaz — "yarım yıl mı geçti"
        # sorusunun cevabı hükmü değiştirmiyor. Sorulan şey BAŞKA: sıfırın
        # kayda geçmiş bir gerekçesi var mı, yoksa elimizdeki ilk gözlem
        # serinin ilk gözlemi mi?
        tam = bool(sag == len(d))
        bas_var = ad in olculen
        gerekceli = ad in veri.TANIM_SIFIRI
        if tam:
            hal = ("tanim" if gerekceli
                   else ("dayanaksiz" if bas_var else "bas_olculmedi"))
        else:
            hal = "ayirt_edilemez" if sag >= esik_hafta else "olcum"
        rapor["seri"][ad] = {
            "n_gozlem": int(len(d)),
            "sifirdisi_hafta": int((d != 0).sum()),
            "sag_uc_sifir_hafta": sag,
            "ic_sifir_hafta": ic,
            "hal": hal,
            "tanim_gerekcesi": bool(gerekceli),
            "bas_olculdu": bool(bas_var),
            "asildi": bool(sag >= esik_hafta),
        }
        if tam:
            (tanim if gerekceli
             else (dayanaksiz if bas_var else hukumsuz)).append(ad)
        else:
            if gerekceli:
                celiski.append(ad)
            if sag >= esik_hafta:
                uzun.append(ad)
                en_uzun = max(en_uzun, sag)
    olculen_seri = len(rapor["seri"])
    rapor["olculen_seri"] = olculen_seri
    rapor["asan_seri"] = len(uzun)
    rapor["tanim_seri"] = len(tanim)
    rapor["dayanaksiz_seri"] = len(dayanaksiz)
    rapor["hukumsuz_seri"] = len(hukumsuz)
    rapor["celiskili_seri"] = len(celiski)
    uy: list[str] = []

    # DÖRT CÜMLE HER KOŞUDA YAZILIR, BULGU OLMASA DA. Bulgu varken yazılıp
    # yokken hiç yazılmayan bir anahtar, sayfada statik yedeğe düşer: hüküm
    # tam yanlışlaştığı anda okur eski cümleyi okumaya devam eder. Kardeş okur
    # cümleleri (tazelik, kapsam) bulgu yokken de "yok" metniyle yazılıyor;
    # sıfır cümleleri de artık öyle.
    rapor["tanim_cumle"] = _tanim_cumle(tanim, olculen, olculen_seri)
    rapor["dayanaksiz_cumle"], rapor["dayanaksiz"] = _dayanaksiz_cumle(
        dayanaksiz, H, tanim, hukumsuz, olculen_seri)
    rapor["hukumsuz_cumle"] = _hukumsuz_cumle(hukumsuz, H, olculen_seri)

    if celiski:
        # KAYDA GEÇMİŞ GEREKÇE ÇELİŞİYOR. Uyarı: sıfır beklenen bir bacakta
        # değer çıktı, yani ya gerekçe ya kalem eşleşmesi yanlış. İkisi de
        # okurun gördüğü sayıları etkiler.
        uy.append(
            f"TANIM SIFIRI ÇELİŞİYOR: {veri._adlar(celiski)} — sıfır olması "
            "kayda geçmiş bir gerekçeye dayanıyordu, ama ölçülen haftalarda "
            "sıfırdan farklı değerler var (en çok "
            f"{b.sayi(max(rapor['seri'][a]['sifirdisi_hafta'] for a in celiski), 0)}"
            " hafta). Gerekçe ya da kalemin karşılığı yanlış; bu bacaktan "
            "beslenen sayılar sınanana kadar temkinle okunmalı.")

    if uzun:
        # Cümle RAPORDA taşınır. Uyarı metnini sonradan ikiye bölüp özete
        # koymak, bir seri adının içinde iki nokta geçtiği gün cümleyi ortadan
        # keserdi; aynı metin iki yerde ayrı ayrı kurulsaydı da bir gün
        # sessizce ayrışırdı.
        rapor["cumle"] = (
            f"{veri._adlar(uzun)} son {b.sayi(en_uzun, 0)} haftanın tamamında "
            "tam sıfır; öncesinde sıfırdan farklı gözlemler var. O haftalarda "
            "gerçekten hiç hareket olmamış olabilir; kaynağın bu bacağı "
            "yayımlamayı bırakmış olması da aynı görünür ve elimizdeki "
            "gözlemle ikisi ayırt edilemiyor. Sıfırlar olduğu gibi bırakıldı.")
        uy.append(
            f"AYIRT EDİLEMİYOR: {veri._adlar(uzun)} son "
            f"{b.sayi(en_uzun, 0)} haftanın tamamında tam sıfır; öncesinde "
            "sıfırdan farklı gözlemler var. O haftalarda gerçekten hiç "
            "hareket olmamış olabilir; kaynağın bu bacağı yayımlamayı "
            "bırakmış olması da aynı görünür ve elimizdeki gözlemle ikisi "
            "ayırt edilemiyor. Sıfırlar olduğu gibi bırakıldı.")
    elif not olculen_seri:
        rapor["cumle"] = ("Yayımı durmuş görünen bir sıfır bloğu var mı, bu "
                          "koşuda ölçülemedi: gözlem yüklenemedi.")
    else:
        rapor["cumle"] = (
            f"Sağ ucunda {b.sayi(esik_hafta, 0)} haftadan uzun kesintisiz "
            "sıfır taşıyan bir bacak bu koşuda yok: ölçülen "
            f"{b.sayi(olculen_seri, 0)} serinin hiçbirinde yayımın durmuş "
            "olabileceğini düşündüren bir blok bulunmadı.")
    return uy, rapor


# ===========================================================================
# ana akış
# ===========================================================================
def kos() -> int:
    b = _bicim()
    H = _oku("haftalik.csv")

    # VERİ KATMANININ UYARILARI BURADA DEVRALINIR. Tazelik alarmları, eski
    # önbellek, kapsam ve boşluk uyarıları veri katmanında basılıp koşu
    # kaydına yazılıyor; devralınmazsa uyarı kaydına hiç girmez ve SAYFADA
    # GÖRÜNMEZ. İki kaynak birleştirilir (bellekteki liste + dosyadaki kayıt)
    # çünkü veri katmanı ayrı bir alt süreçte koşmuş olabilir ve o durumda
    # bellekteki liste boştur.
    devir: list[str] = list(veri.uyarilar())
    try:
        durum = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
        devir += list(durum.get("uyarilar") or [])
    except (OSError, ValueError, AttributeError) as ex:
        durum = {}
        uyar(f"VERİ KATMANI KAYDI OKUNAMADI ({type(ex).__name__}): veri "
             "katmanının uyarıları devralınamadı; tazelik uyarıları bu koşuda "
             "GÖRÜNMEYEBİLİR.")
    for u in devir:
        if u not in _UYARI:
            _UYARI.append(u)
            print("  ! (veri) " + u, flush=True)

    s_h = veri.son_hafta(H)
    print("Yurt içi yerleşiklerin YP mevduatı — ölçüm katmanı")
    print(f"  çıpa: {ad_gun(s_h)} (cuma)")

    dur, kapsam_rapor = kapsam_kimligi(H)
    kaydirma, hiz_tani = hizalama_sec(H)
    A, ayr_tani = ayristir(H, kaydirma)
    K = kumule(A)
    M = stok_metrikleri(H)
    D, dol_tani = dolarizasyon(H, A)
    ayrisma = ayrisma_olc(A, M)
    sifir_uy, sifir_rapor = sifir_olc(H, veri.SIFIR_KAPSAMI, ESIK_SIFIR_BLOK,
                                      veri.BAS_OLCULEN)
    for u in sifir_uy:
        uyar(u)

    # --- özet -------------------------------------------------------------
    o: dict = {"son_hafta": s_h.strftime("%Y-%m-%d")}

    # STOK BLOĞU — bloğun tümünün dolu olduğu ortak haftaya çıpalanır ve
    # `stok_tarih` yazar. Şekil saat defteri bu anahtarı okuyor: yazılmazsa
    # stok figürlerinin altına tarih HİÇ basılmaz.
    o.update(_blok(M, list(M.columns), "stok"))

    # AKIM BLOĞU — yalnız değişim tablosundan gelenler: haftalık arındırılmış
    # değişim, parite etkisi ve bunların kümülesi. İkisi TEK blokta ve TEK
    # tarihte, çünkü kümüle akım haftalık akımın toplamıdır; ayrı okunsalardı
    # kümüle bir haftayı, haftalık akım başka bir haftayı gösterebilirdi.
    # BİLİNÇLİ TUTUCULUK: para birimi kırılımları da bu blokta. Bir kırılım
    # bacağı ötekilerden geride biterse blok o haftaya çıpalanır ve manşet
    # akımların damgası bir hafta geriye düşer. Bunu daha da bölmek cazip
    # görünür ama şekil defterinde para birimi figürü de akım saatine bağlı:
    # bölünseydi o figür kendi bacağından YENİ bir tarihle damgalanır ve bayat
    # panel taze görünürdü. Karma bir figürde bağlayıcı bacak en eskisidir.
    # Bacaklar ayrıştığında blok zaten uyarı düşürüyor, yani sessiz kalmıyor.
    akim_gorunum = A[[c for c in AKIM_OZET if c in A.columns]].rename(
        columns={k: v for k, v in AKIM_OZET.items() if k in A.columns})
    kum_gorunum = K[[c for c in KUM_OZET if c in K.columns]]
    AK = pd.concat([akim_gorunum, kum_gorunum], axis=1)
    # ÇIPA YALNIZ HAFTALIK AKIMLARDAN. Kümüle sütunları (takvim içi ve sabit
    # pencere) haftalık akımın TÜREVİDİR ve uçları tanım gereği kaynağın
    # ucundan geride olabilir: on üç haftalık pencerede tek bir boş hafta on üç
    # hafta boyunca NaN üretiyor, yıl içi kümüle ise bir boşluktan sonra yıl
    # sonuna kadar ölçülemez hâle geliyor. Türev bir sütun, türediği sütunun
    # saatini KAYDIRMAMALI: ölçüldü, tek bir haftalık boşluk akım bloğunun
    # tamamını 28.08'den 29.05'e çekiyordu ve o hafta gerçekten ölçülmüş olan
    # haftalık akımlar da üç ay geride yayımlanıyordu. Kümüle değerin kendisi o
    # haftada ölçülemiyorsa zaten yazılmaz (bloğun delik denetimi) ve koşu
    # kaydında adıyla görünür — bu, bayat bir sayı yayımlamaktan iyidir.
    cipa_kol = list(akim_gorunum.columns)
    o.update(_blok(AK, list(AK.columns), "akim", cipa_kolonlari=cipa_kol))

    # KİMLİK BLOĞU — stok değişimi ve artık İKİ TABLODAN birden geliyor,
    # öyleyse kendi saatleri var ve o saat ikisinin EN ESKİSİDİR. Şekil
    # defteri kimlik figürü için zaten aynı hesabı yapıyor (stok ile akım
    # saatinin en eskisi); burada aynı büyüklüğün ölçülmüş hâli duruyor ki
    # sayfadaki sayı ile şeklin damgası aynı haftayı söylesin.
    kimlik_gorunum = A[[c for c in KIMLIK_OZET if c in A.columns]].rename(
        columns={k: v for k, v in KIMLIK_OZET.items() if k in A.columns})
    o.update(_blok(kimlik_gorunum, list(kimlik_gorunum.columns), "kimlik"))

    # DOLARİZASYON BLOĞU — `dol_tarih` yazar (şekil defterinin üçüncü anahtarı).
    o.update(_blok(D, ["dol_pay_ham", "dol_pay_ar", "dol_pay_fark",
                       "mevduat_tl_mlr", "mevduat_yp_mlr",
                       "mevduat_yp_ar_mlr"], "dol"))

    o["kimlik_kaydirma"] = int(kaydirma)
    o["kimlik_esik"] = ESIK_KIMLIK_MN
    o["kimlik_esik_bagil"] = ESIK_KIMLIK_BAGIL
    o["kimlik_pencere_hafta"] = KIMLIK_PENCERE
    # PENCERE İÇİNDEKİ bağıl maksimum: yanında yayımlanan mutlak ölçü de,
    # hüküm de, cümle de aynı pencereden geliyor.
    o["kimlik_artik_bagil"] = ayr_tani.get("artik_bagil_pencere_maks")
    o["kimlik_tutuyor"] = ayr_tani.get("tutuyor")
    if ayr_tani.get("cumle"):
        o["kimlik_cumlesi"] = ayr_tani["cumle"]

    # KÜMÜLENİN ETİKETİ, SAYININ OKUNDUĞU HAFTADAN. Çerçevenin ucundan
    # kurulduğunda bir ayın sayısı başka bir ayın adıyla yayımlanıyordu.
    kum_tani = kumule_tanisi(A, o.get("akim_tarih"))
    for anahtar in ("ay_bas", "ay_hafta", "ay_etiket", "yil_bas", "yil_hafta",
                    "yil_etiket"):
        if anahtar in kum_tani:
            o[f"kum_{anahtar}"] = kum_tani[anahtar]
    # SABİT PENCERENİN ADI İLE KAPSAMI AYRIŞABİLİR. Kaynak bir cumayı hiç
    # yayımlamazsa "dört haftalık" etiketli toplam yirmi sekiz günü kapsar;
    # takvime bağlı kümüleler o haftayı hiç saymaz, sabit pencereler ise
    # pencereyi geriye UZATIR — ikisi aynı cümleyle anlatılamaz. Ölçülür ve
    # sapması adıyla yazılır; boşaltmak, tek bir atlanan hafta yüzünden sağ
    # uçtaki on iki gözlemi silip figürü üç ay geriye düşürürdü.
    for n, anahtar in ((PENCERE_KISA, "pencere_kisa_kapsam_gun"),
                       (PENCERE_UZUN, "pencere_uzun_kapsam_gun")):
        kapsam = kum_tani.get(anahtar)
        if kapsam is not None:
            o[f"kum_{n}h_kapsam_gun"] = kapsam
        if kapsam is not None and kapsam != 7 * (n - 1):
            uyar(f"PENCERE KAPSAMI: {b.sayi(n, 0)} haftalık kayan toplam son "
                 f"haftada {b.sayi(kapsam, 0)} takvim gününü kapsıyor "
                 f"({b.sayi(7 * (n - 1), 0)} gün olmalıydı); aradaki haftalardan "
                 "biri yayımlanmamış ve pencere geriye uzamış.")
    o["kum_pencere_kisa_hafta"] = PENCERE_KISA
    o["kum_pencere_uzun_hafta"] = PENCERE_UZUN

    if dol_tani.get("cipa"):
        o["dol_cipa"] = dol_tani["cipa"]
        o["dol_cipa_etiket"] = dol_tani.get("cipa_etiket")
        o["dol_pay_cipa"] = dol_tani.get("ham_cipa")
    if dol_tani.get("cumle"):
        o["dol_cumlesi"] = dol_tani["cumle"]

    for anahtar in ("n_hafta", "ters_hafta", "ters_oran", "ters_oran_ilk_yari",
                    "ters_oran_ikinci_yari", "korel", "korel_son_pencere"):
        if anahtar in ayrisma:
            o[f"ayrisma_{anahtar}"] = ayrisma[anahtar]
    # Cümle, İKİ YARININ DA ölçüldüğü ve korelasyonun sonlu olduğu koşulda
    # kurulur. Ölçülmemiş bir yarıyı sıfır diye yazmak, uydurulmuş bir
    # kararlılık raporu olurdu.
    if (ayrisma.get("yeterli") and ayrisma.get("ters_oran") is not None
            and ayrisma.get("ters_oran_ilk_yari") is not None
            and ayrisma.get("ters_oran_ikinci_yari") is not None
            and _f(ayrisma.get("korel")) is not None):
        o["ayrisma_cumlesi"] = (
            "Gerçek ve tüzel kişilerin arındırılmış haftalık akımları ölçülen "
            f"{b.sayi(ayrisma['n_hafta'], 0)} haftada "
            f"{b.yuzde(ayrisma['ters_oran'] * 100, 1)} oranında ters yönde "
            f"hareket etti; örneklemin ilk yarısında "
            f"{b.yuzde(ayrisma['ters_oran_ilk_yari'] * 100, 1)}, ikinci "
            f"yarısında {b.yuzde(ayrisma['ters_oran_ikinci_yari'] * 100, 1)}. "
            f"İki akımın korelasyonu {b.sayi(ayrisma['korel'], 2)}.")

    # KÜMÜLENİN ETİKETİ — ölçü doğru olsa da etiket yanlışsa kusur sürer.
    o["kum_yontem_cumlesi"] = (
        "Haftalık gözlemler cumaya damgalıdır ve bir önceki cumadan bu yana "
        "olan değişimi taşır. Ay içi toplam, o aya damgalı haftaların "
        "toplamıdır: ayın ilk haftası bir önceki ayın son günlerini de kapsar.")

    # ÜÇ TABAN — sayfada hangi sayının hangi tabandan geldiği tek yerde yazılı.
    o["taban_sozlugu"] = (
        "Sayfada üç ayrı taban var: yurt içi yerleşiklerin toplam yabancı para "
        "mevduatı (TP.HPBITABLO2.10), yurt dışı yerleşikleri de içeren geniş "
        "toplam (TP.HPBITABLO4.1) ve aynı mevduatın Türk lirası karşılığı "
        "(TP.HPBITABLO2.6). Manşet birincisidir; ikincisi yalnız farkıyla "
        "birlikte anılır, dolarizasyon payı ise yalnız üçüncüsünden hesaplanır.")

    cek = [c for c in veri.CEKIRDEK if c in H.columns]
    tam = H[cek].dropna(how="any") if cek else H.iloc[0:0]
    # İKİ TABLONUN BAŞLANGICI ÖLÇÜLÜR, VARSAYILMAZ. Tarihçenin asimetrik
    # olduğunu biliyoruz ama cümle onu ölçtüğü için söyler: kaynak bir gün
    # eski tarihçeyi geriye doldurursa cümle kendiliğinden düzelir.
    def _ilk(kol):
        return (H[kol].dropna().index[0]
                if kol in H.columns and H[kol].notna().any() else None)
    ar_ilk, stok_ilk = _ilk("ar_toplam"), _ilk("stok_toplam")
    ar_seri = H["ar_toplam"].dropna() if ar_ilk is not None else None
    if len(tam) and ar_ilk is not None and stok_ilk is not None:
        # İKİ PENCERE, İKİ CÜMLE PARÇASI — ve bu bir düzeltmedir.
        #
        # Cümle "ölçüm şu kadar haftayı kapsıyor" diye TEK bir sayı yazıyordu
        # ve o sayı ORTAK pencereydi (iki tablonun kesişimi). Tarihçe simetriye
        # yakınken kusur küçüktü; ölçülen başa çekildiğinde asimetri 25 haftadan
        # beş yüz haftanın üstüne çıktı ve tek sayı okura sayfanın YARISINI
        # olduğundan kısa gösterir hâle geldi: kümüle akım figürleri on iki
        # yılı çiziyor, metin "yüz on dört haftayı kapsıyor" diyordu.
        #
        # Hangi ölçüm hangi pencereden geliyor, ayrımı ŞUDUR ve yapısaldır:
        #   · Yalnız değişim tablosundan türeyen her şey (haftalık arındırılmış
        #     akım, parite etkisi, kümüle toplamlar, iki bacağın ayrışması)
        #     değişim tablosunun KENDİ penceresine sahiptir — stok tablosunun
        #     geç başlaması onları hiç bağlamaz.
        #   · Stokun haftalık değişimini ve kimliği (Δ stok ≟ arındırılmış +
        #     parite) isteyen her şey İKİ tabloyu birden ister, yani yalnız
        #     ORTAK pencerede kurulabilir.
        # Ayrım koda da böyle geçti: kimlik bloğu ayrı çıpalanıyor, kümüle
        # akım stok tablosunun ucuna hiç bakmıyor.
        fark_hafta = int(round((stok_ilk - ar_ilk).days / 7))
        # CÜMLE ÖLÇTÜĞÜ ŞEYİ SÖYLER: "tablo şu tarihte başlıyor" bir KAYNAK
        # iddiasıdır, oysa burada ölçülen şey ELİMİZDEKİ haftalardır. İkisi
        # ayrıştığında — çekim kırpıldığında ya da katalog geride kaldığında —
        # cümle kaynak hakkında yanlış bir şey söyler ve aynı kutudaki kapsam
        # uyarısıyla çelişir. Kaynağın kendi başlangıcı ayrı bir ölçümdür
        # (künyede durur, kapsam denetimi onu ayrıca sorar); bu cümle yalnız
        # hangi ölçümün hangi pencereden geldiğini anlatır.
        # ASİMETRİ SIFIRSA BOŞLUK CÜMLESİ YAZILMAZ. Kaynak stok tarihçesini
        # geriye doldurursa (ya da bir gün iki tablo aynı haftada başlarsa)
        # sabit metin "aradaki sıfır hafta için stok gözlemi yok" der ve
        # olmayan bir boşluğu anlatır — ölçülmemiş bir şeyi ölçülmüş gibi
        # göstermenin küçük ama aynı sınıftan bir biçimi. Ölçüldü: simetrik
        # pencerede cümle tam bunu yazıyordu.
        if fark_hafta:
            o["kapsam_cumlesi"] = (
                f"Bu sayfada iki ayrı pencere var. Resmî ayrıştırma "
                f"tablosundan ölçülen haftalar {b.tarih_uzun(ar_ilk)} "
                "tarihinde başlıyor: haftalık arındırılmış akım, parite "
                "etkisi ve kümüle toplamlar "
                f"{b.sayi(int(len(ar_seri)), 0)} haftayı kapsıyor. Stok "
                f"tablolarından ölçülen haftalar {b.tarih_uzun(stok_ilk)} "
                "tarihinde başlıyor; stokun haftalık değişimi ve ikisinin "
                "birbirini kapatıp kapatmadığı ancak her iki tablonun birden "
                f"ölçüldüğü {b.sayi(len(tam), 0)} haftada kurulabiliyor. "
                f"Aradaki {b.sayi(abs(fark_hafta), 0)} hafta için stok "
                "gözlemi yok: o haftalarda akım ölçülüyor, stok değişimi "
                "ölçülmüyor ve stok akımdan geriye uzatılmıyor.")
        else:
            o["kapsam_cumlesi"] = (
                f"Resmî ayrıştırma tablosu ile stok tablolarından ölçülen "
                f"haftalar aynı tarihte başlıyor ({b.tarih_uzun(ar_ilk)}): "
                "haftalık akım, kümüle toplamlar, stokun haftalık değişimi ve "
                "ikisinin birbirini kapatıp kapatmadığı aynı "
                f"{b.sayi(len(tam), 0)} haftalık pencerede ölçülüyor.")
        # Ayrımın MAKİNE kaydı: cümle okura, sayılar koşu kaydına. İkisi aynı
        # ölçümden geldiği için bir gün ayrışamazlar.
        dog_kapsam = {
            "akim_bas": ar_ilk.strftime("%Y-%m-%d"),
            "akim_hafta": int(len(ar_seri)),
            "stok_bas": stok_ilk.strftime("%Y-%m-%d"),
            "ortak_bas": tam.index[0].strftime("%Y-%m-%d"),
            "ortak_hafta": int(len(tam)),
            "asimetri_hafta": int(abs(fark_hafta)),
        }
    else:
        dog_kapsam = {}
    # DÖRT AYRI ANAHTAR, çünkü dört ayrı hâl — ve dördü sayfada AYNI KUTUDA
    # AYNI AĞIRLIKTA anılmamalı:
    #   · tanım gereği sıfır — dayanağı aritmetik, veriye hiç bakmıyor;
    #   · dayanağı olmayan sıfır — donma elendi, ama sıfırın hareketin mi
    #     ölçünün mü yokluğu olduğu ayırt EDİLEMİYOR (ve manşete dokunuyor);
    #   · yayımı durmuş olabilecek blok — kaynak tarafındaki belirsizlik;
    #   · başlangıcı ölçülmemiş seri — bizim henüz sormadığımız soru.
    # Tek anahtarda toplansalardı okur, dayanağı olmayan bir sıfırı da,
    # bizim sormadığımız bir soruyu da ölçüm sanırdı.
    #
    # DÖRDÜ DE HER KOŞUDA YAZILIR, BULGU OLMASA DA. Bulgu varken yazılıp
    # yokken düşen bir anahtar sayfada statik yedeğe düşer: hüküm tam
    # yanlışlaştığı anda okur eski cümleyi okumaya devam eder — yani anahtar,
    # en çok gerektiği gün DONAR. Kardeş okur cümleleri (tazelik, kapsam)
    # zaten bulgu yokken de "yok" metniyle yazılıyor.
    o["sifir_tanim_cumlesi"] = sifir_rapor["tanim_cumle"]
    o["sifir_dayanaksiz_cumlesi"] = sifir_rapor["dayanaksiz_cumle"]
    o["sifir_hukumsuz_cumlesi"] = sifir_rapor["hukumsuz_cumle"]
    o["sifir_cumlesi"] = sifir_rapor["cumle"]

    dog = {"kapsam": kapsam_rapor, "kimlik": ayr_tani, "hizalama": hiz_tani,
           "sifir": sifir_rapor, "ayrisma": ayrisma, "pencere": dog_kapsam}
    o["ayristirma"] = ayr_tani
    o["kumule"] = kum_tani
    o["dolarizasyon"] = dol_tani
    o["ayrisma"] = ayrisma
    o["hizalama"] = hiz_tani
    o["sifir"] = sifir_rapor
    o["dogrulama"] = dog
    # EŞİĞİN BÜYÜKLÜK KIYASI KOŞUDA TÜRETİLİR, yorumda yazılmaz: yorumdaki
    # sayı bir kez on kat yanlış yazıldı ve eşiği gözden geçiren bir sonraki
    # oturumu on kat büyütmeye ikna edebilirdi. Türetilen kıyas yaşlanmaz.
    _son_stok = _son_deger(M, "stok_toplam_mia")
    o["esik"] = {
        "kimlik_son_stok_payi": (None if not _son_stok else
                                 _f(ESIK_KIMLIK_MN / (_son_stok * 1e3))),
        "kapsam_mn_usd": ESIK_KAPSAM_MN, "kapsam_bagil": ESIK_KAPSAM_BAGIL,
        "kimlik_mn_usd": ESIK_KIMLIK_MN, "kimlik_bagil": ESIK_KIMLIK_BAGIL,
        "kimlik_pencere_hafta": KIMLIK_PENCERE,
        "hizalama_oran": ESIK_HIZALAMA_ORAN,
        "tarihce_hafta": ESIK_TARIHCE_HAFTA, "sifir_blok_hafta": ESIK_SIFIR_BLOK,
    }
    o["uyarilar"] = list(_UYARI)

    # --- yazım ------------------------------------------------------------
    # SIRA BAĞLAYICI: uyarı kaydı HER HÂLDE ve ÖNCE yazılır. Kopya
    # sözleşmesinde düz yol olarak duruyor; yoksa kopyalama tam orada kesilir
    # ve sözlükte ondan sonra gelen hiçbir çıktı siteye gitmez, üstelik koşu
    # yeşil biter. Uyarı listesi boş olsa bile dosya yazılır.
    _yaz_json(PROJE / "uyarilar.json",
              {"hafta": s_h.strftime("%Y-%m-%d"),
               "kosum": dt.date.today().isoformat(),
               "uyarilar": list(_UYARI), "dogrulama": dog})

    if dur:
        for x in dur:
            print("  ✗ " + x)
        # ÖLÇÜM ÇERÇEVELERİ YAZILMAZ. Uyarı kaydı yukarıda yazıldı (kaybolmasın
        # diye), ama kendi kapsam kimliğini geçemeyen bir çerçeveyi ölçümmüş
        # gibi depoya bırakmak doğru olmaz: izlenen dosyaların doğru sürümü
        # depodakidir ve koşucunun otomatik kaydı yanlış sürümü sahiplenir.
        # Sonraki adımlar (grafik ve özet) hiç koşmaz, siteye kopyalama olmaz.
        raise SystemExit(
            "DUR: stok kırılımının kapsam kimliği tutmuyor. Ölçüm çerçeveleri "
            "yazılmadı ve siteye kopyalama YAPILMAZ; kalem eşlemesi kaymışken "
            "üretilen bir pano, hiç pano olmamasından kötüdür.")

    M.to_csv(VERI / "metrik_haftalik.csv")
    A.to_csv(VERI / "ayristirma.csv")
    if not K.empty:
        K.to_csv(VERI / "kumule.csv")
    if not D.empty:
        D.to_csv(VERI / "dolarizasyon.csv")
    _yaz_json(VERI / "metrik_ozet.json", o)

    print(f"  yazıldı: stok {M.shape} · ayrıştırma {A.shape} · "
          f"kümüle {K.shape} · dolarizasyon {D.shape}")
    # Aşağıdaki döküm OPERATÖR tanısıdır ve okura hiçbir yerden basılmaz; bu
    # yüzden sabit genişlikli hizalamayla yazılıyor. Okura giden her satır
    # (uyarı şablonları ve özetin cümle alanları) sayıyı ortak/bicim'den
    # yazar. Ayrım burada yazılı ki bir sonraki oturum bu kalıbı bir uyarı
    # şablonuna kopyalamasın.
    for etiket, r in (ayr_tani.get("bacak") or {}).items():
        print(f"    kimlik {'✓' if r['tutuyor'] else '✗'} {etiket:<7} "
              f"n={r['n_hafta']:>4}  son {r['artik_son_mn']:>10,.2f}  "
              f"pencere maks {r['artik_pencere_maks_mn']:>10,.2f} mn USD")
    if kapsam_rapor.get("kapsam"):
        r = kapsam_rapor["kapsam"]
        print(f"    kapsam {'✓' if r['gecti'] else '✗'} n={r['n']}  "
              f"maks {r['maks_fark_mn']:,.3f} mn USD  eşik {ESIK_KAPSAM_MN}")
    if kum_tani:
        print(f"    kümüle: ay {kum_tani['ay_bas']} ({kum_tani['ay_hafta']} hafta) · "
              f"yıl {kum_tani['yil_bas']} ({kum_tani['yil_hafta']} hafta)")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return 0


if __name__ == "__main__":
    raise SystemExit(kos())
