#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TCMB fonlama ve likidite — duman sınaması. Ağa çıkmaz, saniyeler sürer.

`guncelle.py` bu dosyayı hattın ADIMLARINDAN ÖNCE koşturur ve düşerse hat hiç
koşmaz, siteye kopyalama olmaz. Sınama `--denetle` yazan birinin eline
bırakılmaz: zamanlanmış koşu `--denetle` demez ve bozuk bir ölçüm katmanı
çıktısını siteye kopyalamış olurdu.

NEDEN BU DOSYA VAR. Hattın bayatlık sınavı zaten yazılmıştı (`bayatlik_sinavi.py`)
ama ADI `duman.py` değildi, yani `guncelle.py` onu HİÇ görmüyordu ve depoda onu
çağıran tek bir satır yoktu (09.09.2026'da ölçüldü). Sessiz bayatlamayı
kilitlemek için yazılmış bir sınav, kendisi de sessizce koşmuyordu.

NEDEN `bayatlik_sinavi.main()` DOĞRUDAN ÇAĞRILMIYOR. O sınav deponun O GÜNKÜ
verisini ve DUVAR SAATİNİ okur: kopyayı olduğu gibi koşturup "taze veride
bayat=False" bekler. Bu dosya ise hattın ADIMLARINDAN ÖNCE, yani veri
tazelenmeden koşuyor — depodaki veri birkaç gün eskiyse "ters yön" maddesi
düşer, hat koşmaz ve veriyi tazeleyecek olan koşu tam da bu yüzden hiç
başlamaz. Yayının önünde duran bir denetimin yanlış alarmı arızanın kendisidir.
Bu yüzden sınama KENDİ ÇERÇEVESİNİ kurar (`ozet_uret.bayat_karari` ve
`veri.tazelik_denetimi` sahte saatle çağrılır); uçtan uca sürüm
`bayatlik_sinavi.py`de elle koşturulmaya devam eder.

BURADAKİ HER MADDE BİR ARIZAYA KARŞILIK GELİR. Bir iddia ya bu depoda gerçekten
yanlış yayımlanmış bir sayıyı, ya yayını durdurmuş bir yanlış alarmı, ya da bu
hattın adı konmuş bir tuzağını kapatır.

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import datetime as dt
import inspect
import sys

import pandas as pd

import ozet_uret
import veri

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def _gunluk(son: str, kolonlar=("net_fonlama", "aofm", "politika", "tlref",
                                "ab_api", "serbest_mevduat", "swap_alim",
                                "usdtry")) -> pd.DataFrame:
    """Sahte günlük çerçeve: `son` gününde biten, kesintisiz bir yayım serisi."""
    gunler = [g.date() for g in pd.date_range(pd.Timestamp(son) - pd.Timedelta(days=400),
                                              pd.Timestamp(son))]
    ix = [pd.Timestamp(g) for g in gunler if veri.yayim_gunu(g)]
    return pd.DataFrame(1.0, index=pd.DatetimeIndex(ix), columns=list(kolonlar))


def _haftalik(son: str) -> pd.DataFrame:
    ix = pd.date_range(end=pd.Timestamp(son), periods=60, freq="7D")
    return pd.DataFrame(1.0, index=ix,
                        columns=["f_ticari_tl", "f_mevduat_tl", "zk_taban_tl", "dth_tl"])


print("TCMB fonlama ve likidite — duman sınaması\n")

# ─────────────────────────────────────────────────────── 1. yayım takvimi
# ARIZA: tazelik ölçüsü TAKVİM GÜNÜ sayıyordu ve hafta sonu tek başına üç gün
# yiyordu. 2018-09-14 → 2026-09-07 tarihçesinde ölçüldü: takvim günü kuralı
# (tolerans 4) sekiz ayrı günde sahte "BAYAT VERİ" bastı, hepsi bayram
# haftasında. Aşağıdaki üç gün o sekizin içinden — bugünkü ölçütün onları
# kapalı sayması ŞART.
sina("bayram günü yayım günü SAYILMAZ (Kurban 2026)",
     not veri.yayim_gunu(dt.date(2026, 5, 27))
     and not veri.yayim_gunu(dt.date(2026, 5, 28))
     and not veri.yayim_gunu(dt.date(2026, 5, 29)))
sina("bayram günü yayım günü SAYILMAZ (Ramazan 2024)",
     not veri.yayim_gunu(dt.date(2024, 4, 10))
     and not veri.yayim_gunu(dt.date(2024, 4, 11))
     and not veri.yayim_gunu(dt.date(2024, 4, 12)))
# PENCERE PAYI OLMADAN BU ÜÇ GÜN KAÇARDI. Tablo hicri takvimi 2019–2026
# arasındaki 16 bayramın 10'unda bir gün ileri düşüyor; aşağıdaki üç gün APİ
# serisinde GÖZLEMLENMİŞ kapanma günleri ve hesabın kendisi onları bir gün
# sonraya koyuyor. Payı sıfırlayan bir sürüm bu maddede DÜŞER.
sina("hesabın bir gün kaydığı bayramlar da kapalı (pencere payı)",
     not veri.yayim_gunu(dt.date(2022, 5, 2))
     and not veri.yayim_gunu(dt.date(2023, 6, 28))
     and not veri.yayim_gunu(dt.date(2025, 6, 6)),
     f"pay={veri.BAYRAM_PAY_GUN}")
sina("sabit tatil yayım günü SAYILMAZ (29 Ekim 2026, perşembe)",
     not veri.yayim_gunu(dt.date(2026, 10, 29)))
sina("hafta sonu yayım günü SAYILMAZ",
     not veri.yayim_gunu(dt.date(2026, 9, 5)) and not veri.yayim_gunu(dt.date(2026, 9, 6)))
sina("sıradan iş günü yayım günüDÜR",
     veri.yayim_gunu(dt.date(2026, 9, 7)) and veri.yayim_gunu(dt.date(2026, 9, 9)))

# ARIZA (ölçülen): 26.05.2026 son gözlem, 01.06.2026 koşusu → takvim günü 6 > 4
# ile BAYAT basılırdı; oysa aradaki üç gün Kurban Bayramı ve kaynak kapalıydı.
sina("bayram haftası sahte BAYAT üretmiyor (26.05 → 01.06.2026)",
     veri.yayim_gun_gecikmesi(dt.date(2026, 5, 26), dt.date(2026, 6, 1)) == 1,
     str(veri.yayim_gun_gecikmesi(dt.date(2026, 5, 26), dt.date(2026, 6, 1))))
sina("hafta sonu tek başına gecikme üretmiyor (Cuma → Pazartesi)",
     veri.yayim_gun_gecikmesi(dt.date(2026, 9, 4), dt.date(2026, 9, 7)) == 1)
# KARŞI YÖN: kapıyı gevşetmek yasak. Gerçek bir duruş HÂLÂ yakalanmalı.
sina("gerçek duruş yakalanıyor (24.08 → 09.09.2026 = 12 yayım günü)",
     veri.yayim_gun_gecikmesi(dt.date(2026, 8, 24), dt.date(2026, 9, 9)) == 12,
     str(veri.yayim_gun_gecikmesi(dt.date(2026, 8, 24), dt.date(2026, 9, 9))))
sina("ileri tarihli gözlem negatif gecikme üretmiyor",
     veri.yayim_gun_gecikmesi(dt.date(2026, 9, 10), dt.date(2026, 9, 9)) == 0)

# YAPISAL KİLİT: birim geri TAKVİM GÜNÜNE döndürülürse bu ölçüt düşer. Ölçüt
# kaynağı okur, çünkü eşik tablosu doğru kalıp ölçünün birimi bozulabilir.
_kaynak = inspect.getsource(veri.tazelik_denetimi)
sina("günlük tazelik YAYIM GÜNÜ ile ölçülüyor (takvim günü farkı değil)",
     "yayim_gun_gecikmesi(son, bugun)" in _kaynak and "(bugun - son).days" not in _kaynak.split("TAZELIK_HAFTALIK")[0],
     _kaynak[:200])
sina("günlük tolerans yayım günü mertebesinde (ölçülen en kötü hâl 2)",
     veri.tazelik_tolerans("gunluk") == 2
     and max(t for _, t, _ in veri.TAZELIK_GUNLUK.values()) <= 3,
     str(veri.tazelik_tolerans("gunluk")))

# ─────────────────────────────────────────────────────── 2. tazelik denetimi
# Sahte çerçeve + sahte saat: ölçüt kendi arızasına karşı koşturuluyor.
_bayram_uy = veri.tazelik_denetimi(_gunluk("2026-05-26"), _haftalik("2026-05-22"),
                                   bugun="2026-06-01")
sina("bayram haftasında GÜNLÜK tazelik uyarısı DÜŞMÜYOR",
     not [u for u in _bayram_uy if "TAZELİK" in u and "gün" in u and "Haftalık" not in u
          and "ZK" not in u],
     " · ".join(_bayram_uy)[:200])
_duran_uy = veri.tazelik_denetimi(_gunluk("2026-08-24"), _haftalik("2026-08-21"),
                                  bugun="2026-09-09")
sina("gerçekten duran günlük yayın uyarı ÜRETİYOR",
     len([u for u in _duran_uy if u.startswith("TAZELİK")]) >= 6,
     " · ".join(_duran_uy)[:200])
_taze_uy = veri.tazelik_denetimi(_gunluk("2026-09-08"), _haftalik("2026-09-04"),
                                 bugun="2026-09-09")
sina("taze veride hiç tazelik uyarısı YOK", not _taze_uy, " · ".join(_taze_uy)[:200])

# ARIZA SINIFI: haftalık faiz bacağının eşiği 12 idi ve koşu anında ölçülen en
# büyük gecikme de 12 — payı SIFIRDI, tek gecikmiş yayım sahte alarm verirdi.
sina("haftalık eşikler ölçülen en kötü hâlin ÜSTÜNDE (faiz 12 → 13, ZK 19 → 20)",
     veri.TAZELIK_HAFTALIK["f_ticari_tl"][1] == 13
     and veri.TAZELIK_HAFTALIK["zk_taban_tl"][1] == 20)
_hafta_kotu = veri.tazelik_denetimi(_gunluk("2026-09-08"), _haftalik("2026-08-21"),
                                    bugun="2026-09-09")
sina("haftalık bacak 19 gün geride iken faiz uyarısı düşüyor, ZK düşmüyor",
     any("kredi faizi" in u for u in _hafta_kotu)
     and not any("ZK'ya tabi TL" in u for u in _hafta_kotu),
     " · ".join(_hafta_kotu)[:200])

# ─────────────────────────────────────────────────────── 3. bayat kararı
# `bayatlik_sinavi.py`nin iki iddiası, ağa çıkmadan ve duvar saatinden bağımsız:
# taze veride bayrak KAPALI, durmuş veride AÇIK ve cümle "BAYAT VERİ" ile başlar.
_taze = ozet_uret.bayat_karari(1, 6, [])
sina("taze veride bayat bayrağı KAPALI",
     _taze["bayat"] is False and not _taze["bayat_cumlesi"].startswith("BAYAT VERİ"),
     str(_taze))
_eski = ozet_uret.bayat_karari(42, 60, [])
sina("durmuş veride bayat bayrağı AÇIK ve cümle 'BAYAT VERİ' ile başlıyor",
     _eski["bayat"] is True and _eski["bayat_cumlesi"].startswith("BAYAT VERİ")
     and "yayım günü" in _eski["bayat_cumlesi"],
     str(_eski))
# Veri katmanının kendi tazelik uyarısı da bayatlık KANITIDIR: seri taze
# görünürken önbelleğe düşülmüş olabilir.
_enj = ozet_uret.bayat_karari(1, 6, ["TAZELİK: sınav enjeksiyonu — yayın durmuş olabilir."])
sina("veri katmanının tazelik uyarısı tek başına bayat bayrağını AÇIYOR",
     _enj["bayat"] is True and _enj["bayat_cumlesi"].startswith("BAYAT VERİ"),
     str(_enj))
sina("bayat kararı ozet_uret.main()'in İÇİNDE değil, ayrı fonksiyonda",
     "bayat_sebep" not in inspect.getsource(ozet_uret.main)
     and "bayat_karari(" in inspect.getsource(ozet_uret.main))

# ─────────────────────────────────────────────────────── 4. kimlik denetimi
# ARIZA SINIFI (bu depoda YPMevduat'ta ölçüldü): künye döngüsü kayıtların
# TAMAMINDAN aynı alanı okuyordu ve ikinci tür kayıt eklendiği gün hat KeyError
# ile ölüyordu. Burada üç kayıt türü de (geçti · düştü · sınanamadı) üretiliyor.
_k = pd.DataFrame({
    "ab_api": [-1000.0, -2000.0, -3000.0],
    "net_fonlama": [1.0, 2.0, 3.0],
    "fon_top": [1.0, 2.0, 3.0], "ste_top": [0.0, 0.0, 0.0],
    "ab_rezerv_para": [10.0, 10.0, 10.0], "ab_emisyon": [4.0, 4.0, 4.0],
    "ab_bankalar": [3.0, 3.0, 3.0], "ab_zk_bloke": [1.0, 1.0, 1.0],
    "ab_serbest": [2.0, 2.0, 2.0], "ab_fon": [2.0, 2.0, 2.0],
    "ab_bankadisi": [1.0, 1.0, 1.0], "ab_mbp": [15.0, 15.0, 15.0],
    "ab_kamu_mev": [1.0, 1.0, 1.0], "ab_diger_mbp": [0.0, 0.0, 0.0],
}, index=pd.date_range("2026-09-01", periods=3, freq="B"))
_uy, _rapor = veri.kimlik_denetimi(_k)
sina("kimlik denetimi sahte çerçevede koşuyor ve rapor üretiyor",
     isinstance(_rapor, dict) and len(_rapor) >= 1, f"{len(_rapor)} kayıt")
# KÜNYE DÖNGÜSÜ KAYDIN ALANLARINI SORAR, VARSAYMAZ.
_eksik = [ad for ad, r in _rapor.items() if "gecti" not in r]
sina("her kimlik kaydı 'gecti' alanını taşıyor (döküm alanı varsaymaz)",
     not _eksik, str(_eksik))

# ARIZA (ölçülen 09.09.2026): hattın ana saati her koşuda bir iş günü geride
# çıkıyor (04.09 16:08 TR → 03.09 · 07.09 17:41 → 04.09 · 08.09 16:19 → 07.09)
# ve "APİ tablosu aynı gün mü yayımlanıyor, yoksa koşu saatimiz mi erken"
# sorusu ancak koşunun ANI kayda geçerse cevaplanabilir. Gün çözünürlüğü bu
# soruyu göremez.
sina("koşu kaydı koşunun ANINI da yazıyor (yalnız gününü değil)",
     '"kosum_an"' in inspect.getsource(veri.kos))

# ─────────────────────────────────────────────────────── 5. sayfanın çağırdığı anahtar
# ARIZA (08.09.2026, DİBS): sayfanın adıyla çağırdığı bir anahtar bir koşuda
# yazılmadı, yayın kapısı ENGEL verdi ve site saatlerce dondu. Bayatlık
# anahtarları sayfanın ilk ekranında duruyor.
_ozet_anahtar = set(ozet_uret.bayat_karari(1, 6, [])) | {"yayim_gecikme_yayim_gun"}
sina("bayat kararı sayfanın çağırdığı dört anahtarı da yazıyor",
     {"bayat", "bayat_tolerans_gun", "bayat_tolerans_hafta",
      "bayat_cumlesi"} <= _ozet_anahtar)


# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
