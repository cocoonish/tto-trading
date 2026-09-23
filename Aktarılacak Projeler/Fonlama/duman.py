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


# ─────────────────────────────────────────────── 6. Şekil 03: yığın kuyruğu ve damga
# ARIZA (ölçülen 10.09.2026, İKİ KUSUR BİR ARADA):
#
# (a) SAHTE SIFIR — okura giden hâli. M'nin indeksi en HIZLI bacağın (kur)
#     günlerini taşır; APİ kalemleri 09.09'da bitmişken indeks 10.09'a
#     uzuyordu ve yığın döngüsü `fillna(0)` ile o günü ÇİZİYORDU: A1 202.000 →
#     0, B1 1.040.741 → 0, B2 16.321 → 0. Okur bunu "TCMB bugün ihaleyle hiç
#     fonlama yapmadı" diye okur. Deponun kendi ilkesi bunu yasaklıyor: SIFIR
#     bir ölçüm sonucudur, ölçülemeyen boş bırakılır. Ölçüldü: düzeltmeden
#     önce 3 sahte sıfır, sonra 0.
#
# (b) YANLIŞ ALARM — hattı durduran hâli. Kapı (grafik.kos) ilan edilen uç ile
#     figürün çizdiği ucun EŞİT olmasını istiyordu. Kural (`_uc`) ise bir alt
#     kalem geride kalınca damgayı DOĞRU biçimde geri çeker ("kıyas ancak
#     hepsinin ölçüldüğü güne kadar kurulabilir"), oysa `fillna(0)`lı iz
#     geriye gitmediği için kapı farkı "kolon listesi ayrışmış" diye okuyup
#     İSTİSNA fırlatıyordu. Ölçüldü: on kalemin ALTISI tek başına DUR
#     üretiyordu (fon_ihale · fon_kot_repo · fon_kot_depo · ste_ihale ·
#     ste_kot · ste_liksen) ve düşen adım hattın TAMAMINI durduruyor —
#     Şekil 03-08 hiç yazılmıyor, siteye kopyalama olmuyor. Üstelik ekrandaki
#     teşhis yanlış olduğu için sonraki oturum kolon listesi arardı.
#
# ÖLÇÜT KURALIN İLAN ETTİĞİ HÂLLERE KOŞTURULUR — bir kuralı sınamak ile o
# kuralı ÖLÇEN kapıyı sınamak iki ayrı iştir. Aşağıdaki dört hâl kuralın kendi
# ilanıdır: bacaklar aynı gün · bir kalem bir gün geride · bir kalem üç gün
# geride · net bacak geride.
def _api_cerceve(son: str, geri: dict[str, int] | None = None) -> pd.DataFrame:
    """Sahte APİ karesi: kalemler `son` gününde biter, `geri` verilen kalemi
    o kadar iş günü geriye çeker. M'nin indeksi HER ZAMAN `son`a kadar uzar
    (kur bacağı gibi hızlı bir bacak yüzünden) — arızanın çekirdeği budur."""
    ix = pd.bdate_range(pd.Timestamp(son) - pd.Timedelta(days=200),
                        pd.Timestamp(son))
    kol = ["net_fonlama", "fon_ihale", "fon_kot_repo", "fon_kot_depo",
           "fon_glp", "fon_kot_diger", "ste_ihale", "ste_kot", "ste_liksen",
           "ste_diger"]
    df = pd.DataFrame(100.0, index=ix, columns=kol)
    df["net_fonlama"] = -50.0
    for k, n in (geri or {}).items():
        if n:
            df.loc[ix[-n:], k] = float("nan")
    return df


def _sekil03_olc(df: pd.DataFrame) -> dict:
    """Kuralın ürettiği damga ile figürün gerçekten çizdiği ucu YAN YANA ölçer."""
    import grafik
    uc = veri.api_panel_uclari(df)
    damga_t = min([t for t in uc.values() if t is not None], default=None)
    o = {"rejim": {"net_negatif_gun": 0, "net_pozitif_gun": 0,
                   "pencere_gun": 250, "fonlama_sifir_gun": 0},
         "son_gun": str(df.index[-1].date())}
    fig = grafik.sekil_03(df, o,
                          grafik.gun_ad(damga_t) if damga_t is not None else None)
    cizili = grafik._cizili_uc(fig)
    # KAPININ KENDİSİ koşturulur — karşılaştırma burada YENİDEN YAZILMAZ.
    # Yeniden yazılsaydı ölçüt, kapı geri bozulduğunda da yeşil geçerdi:
    # bir kuralı sınamak ile o kuralı ÖLÇEN kapıyı sınamak iki ayrı iştir.
    try:
        grafik._uc_denetimi("03_net_api_kompozisyon.html", damga_t,
                            grafik.gun_ad(damga_t) if damga_t is not None
                            else None, fig)
        dur = False
    except SystemExit:
        dur = True
    sahte = 0
    for tr in fig.data:
        ad = str(tr.name)
        if ad[:1] not in ("A", "B"):
            continue
        y = pd.Series(tr.y).astype(float)
        if len(y) >= 2 and abs(y.iloc[-1]) < 1e-9 and abs(y.iloc[-2]) > 1e-9:
            sahte += 1
    return {"damga": damga_t, "cizili": cizili, "sahte": sahte, "dur": dur}


_SON = "2026-09-09"
for _etiket, _geri in (("bacaklar aynı gün", {}),
                       ("bir kalem bir gün geride", {"fon_ihale": 1}),
                       ("bir kalem üç gün geride", {"ste_kot": 3}),
                       ("net bacak geride", {"net_fonlama": 1})):
    _o = _sekil03_olc(_api_cerceve(_SON, _geri))
    sina(f"Şekil 03 [{_etiket}]: ölçülemeyen gün SIFIR çizilmiyor",
         _o["sahte"] == 0, f"{_o['sahte']} sahte sıfır")
    sina(f"Şekil 03 [{_etiket}]: kuralın kendi damgası KAPIYI düşürmüyor",
         not _o["dur"],
         f"damga {_o['damga']} · çizili {_o['cizili']} — kapı DUR verdi")
    sina(f"Şekil 03 [{_etiket}]: damga bayat bacağı taze göstermiyor",
         _o["damga"] is None or _o["cizili"] is None
         or pd.Timestamp(_o["damga"]) <= _o["cizili"],
         f"damga {_o['damga']} > çizili {_o['cizili']}")

# Kuyruk kesme, damgayı ÜRETEN fonksiyondan okunur: iki ayrı liste bir gün
# sessizce ayrışır ve figür ile altındaki tarih farklı günü anlatır.
import grafik as _g
_kaynak = inspect.getsource(_g.sekil_03)
sina("Şekil 03 panel uçlarını veri katmanının TEK fonksiyonundan alıyor",
     "veri.api_panel_uclari(" in _kaynak)
sina("Şekil 03 yığın kareleri kuyruğunda kesiliyor (sağ uçtaki boşluk çizilmez)",
     _kaynak.count("_kuyruk_kes(") >= 3, _kaynak.count("_kuyruk_kes("))
sina("figür damgası panel uçlarının EN ESKİSİ (iki liste tutulmuyor)",
     "api_panel_uclari(M).values()" in inspect.getsource(veri.sekil_uclari))
# Kapı TEK YÖNLÜ: ilan çizilenden GERİDEYSE damga tutucudur, kusur değil.
_kapi = inspect.getsource(_g._uc_denetimi)
sina("kapı tek yönlü (yalnız ilan çizilenden İLERİDEYSE durur)",
     "beyan_t > cizili" in _kapi and "!= beyan" not in _kapi)
# Kapı ağa çıkan kos()'un İÇİNDE kalırsa hiçbir sınama onu koşturamaz.
_kos = inspect.getsource(_g.kos)
sina("kapı ayrı fonksiyonda (ağa çıkan kos()'un içinde değil)",
     "_uc_denetimi(" in _kos and "_cizili_uc(" not in _kos)
sina("kapı ham tarihi okuyor (biçimlenmiş damga geri ayrıştırılmıyor)",
     "uclar[ad]" in _kos and "veri.sekil_uclari(" in _kos)

# ---------------------------------------------------------------------------
# TLREF'İN AYNI GÜN UZANTISI (ortak/tlref.py). EVDS TLREF'i bir iş günü geriden
# veriyor; 23.09.2026 sabah bülteni bu yüzden "TLREF 21 Eylül itibarıyla" yazdı,
# oysa 22.09'un değeri Borsa İstanbul'da 22.09 13:00 GMT'den beri yayımlıydı.
# Uzantı yalnız EVDS'in son gününden SONRASINI ekler ve örtüşen her günde
# birebirliği yeniden sınar. Sahte dosya gerçek dosyanın biçimini taşır:
# UTF-16 + BOM, ';' ayraç, iki dilli başlık, dipnot satırları, binlik virgüllü
# hacim sütunu — 23.09 keşfinde ikinci betik tam bu biçimi okuyamamıştı.
print("\nTLREF aynı gün uzantısı")
import io as _io
import zipfile as _zip
try:
    import tlref as _tl
except ImportError:
    sys.path.insert(0, str(veri.KOK / "ortak"))
    import tlref as _tl


def _bist_zip(gunler: dict, endeks: bool = False) -> bytes:
    if endeks:
        bas = ("Tarih (GG.AA.YYYY) / Date (DD.MM.YYYY);Endeks Kodu / Index Code;"
               "Endeksler / Index Names In Turkish;Endekslerin İngilizce İsimleri;"
               "Kur Türü / Cur Code;Seans No / Session;Kapanış Değeri / Closing Value;"
               "En Düşük Değer / Lowest Value;En Yüksek Değer / Highest Value")
        # En düşük / en yüksek KASITLI olarak kapanıştan farklı: gerçek dosyada
        # üçü aynı gün aynı sayıdır (günde tek sabitleme), yani yanlış sütunu
        # seçen bir ayrıştırıcı bugün zararsız ama GÖRÜNMEZ olurdu — ilk arıza
        # enjeksiyonu tam bu yüzden kaçtı.
        sat = [f"{g:%d.%m.%Y};BISTTLREF;BIST TLREF ENDEKSI;BIST TLREF INDEX;TL;1;{v};{v - 1};{v + 1}"
               for g, v in gunler.items()]
    else:
        bas = ("TARIH/DATE;AD/NAME;INGILIZCE ADI/NAME IN ENGLISH;KOD/CODE;ISIN/ISIN;"
               "DEGER/VALUE;REPO AOF /VWAP REPO RATE;ISLEM HACMI/TRADED VOLUME")
        sat = [f"{g:%d/%m/%Y};TURK LIRASI GECELIK REFERANS;TURKISH LIRA OVERNIGHT;"
               f"TLREF;TRIXIST00015;{v};{v};15,145,000,000" for g, v in gunler.items()]
    sat += ["HESAPLAMAYA DAHIL  AKTIF;Kendinden kendine işlemler hariç",
            "ILK %15'LIK HACIME KARSI;Hesaplamaya Dahil işlemler"]
    b = _io.BytesIO()
    with _zip.ZipFile(b, "w") as z:
        z.writestr("TLREFORANI_D.csv", ("\n".join([bas] + sat)).encode("utf-16"))
    return b.getvalue()


_ix = pd.bdate_range("2026-09-01", "2026-09-21")
_evds = pd.Series([36.0 + i / 100 for i in range(len(_ix))], index=_ix)
_bist = {g.date(): float(v) for g, v in _evds.items()}
_bist[dt.date(2026, 9, 22)] = 36.5477
_oku = _tl.ayristir(_bist_zip(_bist), "oran")
sina("UTF-16 + dipnotlu BIST dosyası ayrıştırılıyor (tarih/değer ADIYLA)",
     len(_oku) == len(_bist) and _oku[dt.date(2026, 9, 22)] == 36.5477,
     f"{len(_oku)} gün")
_s, _b = _tl.uzat(_evds, _oku, "oran", bugun=dt.date(2026, 9, 23))
sina("EVDS'in son gününden SONRAKİ gün eklendi (21.09 → 22.09)",
     _b["durum"] == "uzatildi" and _b["gunler"] == ["2026-09-22"]
     and float(_s.iloc[-1]) == 36.5477, str(_b))
sina("uzantı EVDS'in kendi günlerine DOKUNMUYOR",
     _s.loc[_ix].equals(_evds))
_bozuk = dict(_oku)
_bozuk[dt.date(2026, 9, 15)] += 0.01
_s2, _b2 = _tl.uzat(_evds, _bozuk, "oran", bugun=dt.date(2026, 9, 23))
sina("örtüşen bir günde ayrışma → uzantı YAPILMIYOR, seri dokunulmadan dönüyor",
     _b2["durum"] == "ayrisma" and _s2.equals(_evds), str(_b2))
_s3, _b3 = _tl.uzat(_evds.iloc[:3], _oku, "oran", bugun=dt.date(2026, 9, 23))
sina("örtüşme yetersizken sözleşme sınanmış SAYILMIYOR (uzantı yok)",
     _b3["durum"] == "ortusme_yetersiz" and _s3.equals(_evds.iloc[:3]), str(_b3))
_ileri = dict(_oku)
_ileri[dt.date(2026, 9, 26)] = 36.6          # cumartesi
_ileri[dt.date(2026, 9, 30)] = 36.7          # yarından ileri
_s4, _b4 = _tl.uzat(_evds, _ileri, "oran", bugun=dt.date(2026, 9, 23))
sina("hafta sonu ve yarından ileri tarih eklenmiyor",
     _b4["gunler"] == ["2026-09-22"], str(_b4))
_s5, _b5 = _tl.uzat(_evds, {g: v for g, v in _oku.items() if g <= dt.date(2026, 9, 21)},
                    "oran", bugun=dt.date(2026, 9, 23))
sina("BIST de aynı günde bitiyorsa uzantı 'gerek yok' der, seri aynı",
     _b5["durum"] == "gerek_yok" and _s5.equals(_evds), str(_b5))
_e = _tl.ayristir(_bist_zip({g: 6700 + i for i, g in enumerate(_bist)}, endeks=True), "endeks")
sina("endeks dosyası da ADIYLA ayrıştırılıyor (kapanış sütunu, en düşük/en yüksek değil)",
     len(_e) == len(_bist) and _e[dt.date(2026, 9, 22)] == 6700 + len(_bist) - 1)

# Çerçeve yolu: ağ yerine sahte `indir`. Ana saat (APİ çekirdeği) KAYMAMALI.
_gercek_indir = _tl.indir
try:
    _bist_end = {g: v + 6000 for g, v in _bist.items()}
    _tl.indir = lambda tur, zaman_asimi=30: (_bist_zip(_bist_end, endeks=True) if tur == "endeks"
                                             else _bist_zip(_bist))
    _G = pd.DataFrame({"net_fonlama": 1.0, "fon_top": 1.0, "ste_top": 1.0, "politika": 37.0,
                       "koridor_alt": 35.5, "koridor_ust": 40.0, "tlref": _evds,
                       "tlref_endeks": _evds + 6000}, index=_ix)
    veri._SON.pop("gun", None)
    _G2 = veri.tlref_uzantisi(_G)
    sina("hat çerçevesinde TLREF oranı ve endeksi ilerliyor (22.09)",
         _G2["tlref"].dropna().index[-1] == pd.Timestamp("2026-09-22")
         and _G2["tlref_endeks"].dropna().index[-1] == pd.Timestamp("2026-09-22"),
         str(veri._TLREF_BILGI))
    veri._SON.pop("gun", None)
    sina("ana saat (APİ çekirdeği) uzantıyla KAYMIYOR",
         veri.son_gun(_G2) == pd.Timestamp("2026-09-21"))
    veri._SON.pop("gun", None)

    def _dusen(tur, zaman_asimi=30):
        raise TimeoutError("ağ yok")
    _tl.indir = _dusen
    _once = len(veri._UYARI)
    _G3 = veri.tlref_uzantisi(_G)
    sina("kaynağa ulaşılamazsa hat DÜŞMÜYOR, çerçeve aynı, uyarı okur dilinde",
         _G3["tlref"].equals(_G["tlref"]) and len(veri._UYARI) > _once
         and "Borsa İstanbul" in veri._UYARI[-1] and ".zip" not in veri._UYARI[-1])
    _, _uy2, _bi2 = _tl.cerceveye_ekle(_G, {"tlref": "oran", "tlref_endeks": "endeks"})
    sina("iki dosya birden düşünce okura TEK cümle gider, hangisinin düştüğü bilgide adıyla",
         len(_uy2) == 1 and set(_bi2) == {"tlref", "tlref_endeks"}
         and all(b["durum"] == "indirilemedi" for b in _bi2.values()), str(_uy2))
finally:
    _tl.indir = _gercek_indir
    veri._SON.pop("gun", None)

# Yukarıdaki maddeler `indir`i SAHTEYLE değiştiriyor, yani ağ yolunun kendisini
# hiç koşturmuyor. 23.09.2026 uçtan uca koşusu tam orada düştü: istek başlığında
# Türkçe bir harf vardı ve http.client başlığı latin-1 ile kodlarken istek AĞA
# ÇIKMADAN UnicodeEncodeError verdi. GERÇEK `indir` bu yüzden yerel bir sunucuya
# karşı koşturulur — ağa çıkmaz, ama istek kurulumu, başlık kodlaması ve yanıtın
# okunması üretimle aynı yoldan geçer.
import http.server as _hs  # noqa: E402
import threading as _th  # noqa: E402

_GELEN: dict = {}


class _Sunucu(_hs.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        _GELEN["ua"] = self.headers.get("User-Agent")
        govde = _bist_zip(_bist, endeks=self.path.endswith("endeks.zip"))
        self.send_response(200)
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def log_message(self, *a):  # koşu kaydını kirletmesin
        pass


_srv = _hs.HTTPServer(("127.0.0.1", 0), _Sunucu)
_th.Thread(target=_srv.serve_forever, daemon=True).start()
_gercek_adres = dict(_tl.ADRES)
try:
    _tl.ADRES["oran"] = f"http://127.0.0.1:{_srv.server_port}/oran.zip"
    _tl.ADRES["endeks"] = f"http://127.0.0.1:{_srv.server_port}/endeks.zip"
    try:
        _yerel = _tl.ayristir(_tl.indir("oran", zaman_asimi=10), "oran")
        _hata = ""
    except Exception as ex:  # maddenin kendisi düşmesin; hata adıyla yazılsın
        _yerel, _hata = {}, f"{type(ex).__name__}: {ex}"
    sina("GERÇEK indir (yerel sunucu): başlık kodlanıyor, istek gidiyor, dosya ayrışıyor",
         _yerel == _oku and bool(_GELEN.get("ua")), _hata or str(_GELEN))
finally:
    _tl.ADRES.update(_gercek_adres)
    _srv.shutdown()
sina("uzantı kos()'ta EVDS çekiminin hemen ardında (tüketicisi var)",
     "tlref_uzantisi(g)" in inspect.getsource(veri.kos))

# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
