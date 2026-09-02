"""TCMB rezerv hattı — piyasa tanımı (birincil) + Stand-By 2A (karşılaştırma).

Bu dosya İKİ ayrı rezerv ölçüsü üretir ve ikisini yan yana tutar. Sebebi
basit: "net rezerv" tek bir şey değildir, tanım seçimine göre milyar dolarlar
oynar. Hangi tanımın ne olduğu aşağıda açıkça yazılıdır.

===========================================================================
A. PİYASA TANIMI  (birincil seri — bütün grafiklerin ve güncel okumanın serisi)
===========================================================================
Kaynağı tamamen analitik bilanço (HER İŞ GÜNÜ yayımlanır) olduğu için günlük
çözünürlüklüdür; haftalık çapaya, ara değere, taşımaya ihtiyaç duymaz.

  Net dış varlık (t) = [ A02 − A11 − A14 ](t) / USDTRY_alış(t)

    A02  TP.AB.A02  A.1 Dış Varlıklar
    A11  TP.AB.A11  P.1a Dış Yükümlülükler
    A14  TP.AB.A14  P.1bb Bankalar Döviz Mevduatı
    kur  TP.DK.USD.A.YTL (alış, AYNI GÜN)

  Özdeşlik: A10 = A11 + A13 + A14 olduğundan formül (A02 − A10 + A13)/kur'a
  eşittir. Yani A13 (P.1ba Kamu ve Diğer Döviz Mevduatı) yükümlülükten
  DÜŞÜLMEZ — kamunun TCMB'deki döviz mevduatı "dış" yükümlülük sayılmaz.
  Ham (A02 − A10)/kur kullanmak seriyi sistematik olarak 6,6 milyar USD
  aşağı kaydırır. Kamu hareketleri seviyeden değil, AKIMDAN düşülür (bkz. D).

  Brüt rezerv (t) = TOPLAM(F)/1000 + [ A02(t)/kur(t) − A02(F)/kur(F) ]/1e6
    TOPLAM  TP.AB.TOPLAM (haftalık Cuma, MİLYON USD — zaten USD, çapraz kur
            dönüşümü yok)
    F       son Cuma ≤ t − GECIKME_GUN  (bkz. GECIKME_GUN gerekçesi)

  Neden çapa: A02 (Dış Varlıklar) resmi rezerv varlıklarından sistematik
  olarak 2,4–2,9 milyar USD fazladır — rezerv tanımına girmeyen diğer döviz
  alacaklarını da içerir. Bu boşluk bir SABİTLE değil, her hafta tazelenen
  gerçek çapayla düşülür; hafta içi hareket analitik bilançodan gelir.

  Toplam swap stoku (t) = C(G) + [ S(t) − S(G) ]
    S(t) = [ TOTALSTOKALIMYONLU − TOTALSTOKSATIMYONLU ](t)/1000
           TCMB'nin YURT İÇİ bankalarla swap stoku, her iş günü yayımlanır
    C(G) = −[ II.2 + II.3 ](G)/1000    IRFCL toplam (yabancı MB dahil)
    G    = son IRFCL gözlemi ≤ t − GECIKME_GUN

    yerli_banka(t)  = S(t)              ← bağımsız, günlük, GÖZLENEN seri
    yabanci_mb(t)   = C(G) − S(G)       ← artık; ancak IRFCL frekansında
                                          tazelenir, ay içi hareketi
                                          gözlenemez (basamak fonksiyonu)

    Artık gözlemlenemeyen bacağa yazılır, gözlemlenene değil. İşaret
    konvansiyonu: stok POZİTİF yazılır ("alım yönlü" = TCMB vadede döviz
    satıyor) ve seviyeden ÇIKARILIR.

  Swap hariç net rezerv (t) = net dış varlık (t) − toplam swap stoku (t)

  Brüt rezervin kırılımı:
    Altın (t) = TP.AB.C1(F)/1000 × P(t)/P(F)      P = altın fiyatı, aynı gün
    Döviz (t) = Brüt (t) − Altın (t)

    Oransal biçim (miktar × fiyat değil) kasıtlıdır: fiyat serisinin TCMB
    değerleme fiyatına göre sistematik iskontosu P(t)/P(F) oranında
    sadeleşir. "Döviz" satırı saf döviz DEĞİLDİR: IRFCL'in (1) döviz
    varlıkları + (2) IMF rezerv pozisyonu + (3) SDR toplamıdır.

===========================================================================
B. STAND-BY 2A  (karşılaştırma serisi — kaldırılmadı, rolü değişti)
===========================================================================
  Eski net rezerv (T) = [ N06(son Cuma) + Δ(A02 − A14)(son Cuma→T) ] / kur(T)
    N06  TP.AB.N06  Stand-By Cari "2A Net Uluslararası Rezervler" (Bin TL)

  Bu TCMB'nin kendi haftalık yayınıdır ve Bloomberg/Reuters manşetlerinde
  çıkan sayı odur; bu yüzden sayfadan kaldırılmaz. Piyasa tanımından
  ORTALAMA 2,2 milyar USD (bant 1,9–2,5) düşüktür ve fark TAMAMEN VARLIK
  BACAĞINDADIR: N06 varlık tarafında daha dar bir tanım olan brüt döviz
  rezervini kullanır. Yükümlülük bacakları 0,4 milyar USD içinde örtüşür
  (A14 ile |N09| Cuma günleri BİREBİR aynıdır).

  İki ölçü de doğrudur; tanımları farklıdır. Fark SABİT DEĞİLDİR: Cuma
  ortalaması 2023'te ≈ +1,2, 2026'da ≈ +1,8 milyar USD'dir ve tek tek
  haftalarda −2 ile +2,5 arasında salınır. Bu yüzden denetim sabit bir banda
  değil, farkın kendi bir yıllık dağılımına bakar (TANIM_FARKI_*): sürüklenme
  uyarı üretmez, SIÇRAMA üretir.

===========================================================================
C. GECIKME_GUN = 5 (üç kalemin ortak çapa kuralı)
===========================================================================
Bir Cuma F'nin haftalık istatistiği F+6'da (Perşembe 14:30) yayımlanır.
Analitik bilançonun referans dönemi bir önceki iş günü olduğu için t
verisiyle derlenen tablo t+1'de çıkar; o tablo ancak F+6 ≤ t+1, yani
F ≤ t−5 koşulunu sağlayan Cuma'yı kullanabilir. Pencere sınırı Çarşamba'ya
düşer.

Seçim ölçütü yayın takvimidir. 4, 5 ve 6 günlük gecikmeler ortalama hata
bakımından ölçüm gürültüsü içinde ayrışmaz; ayrıştıran şey artığın YAPISIDIR
(5 günde artık yuvarlama zeminine çöker, komşularında basamak kalır). "Üç
kalemde ayrı ayrı sınandı" bağımsız kanıt değildir — üçü de aynı haftalık
yayın takvimine bağlıdır. Ayrıntılı gerekçe GECIKME_GUN yorumunda.

===========================================================================
D. AKIM — altın fiyat etkisinden arındırılmış net döviz alımı/satımı
===========================================================================
altin_etkisi.py'de. Kimlik:

  Δ(swap hariç net) = net döviz alımı + altın fiyat etkisi + Δ(kamu döviz
                      mevduatı)

Akım serisi L ile etiketlenir ve L → L+1 değişimini taşır; bu yüzden rezerv
serisinden bir iş günü geride biter.

===========================================================================
Bilinen sınırlar (kapatılmadı, yazıldı)
===========================================================================
1. Altın, TCMB'nin haftalık Londra kotasyonuyla değil günlük piyasa
   fiyatıyla ölçülüyor → altın/döviz kırılımında günlük yarım milyar dolar
   mertebesinde artık kalır. Brüt ve net seviye bundan ETKİLENMEZ.
2. Hafta içi altın MİKTAR değişimi hiçbir günlük resmi kaynakta yayımlanmaz;
   ancak Cuma'da yakalanır.
3. Yabancı merkez bankası swap stoku yalnız IRFCL frekansında tazelenir.
   Haftalık IRFCL gözlemi olan haftalarda swap kalemi kesin, yalnız aylık
   çapa olan haftalarda hassasiyet belirgin düşer → `swap_capa_tipi`
   sütunu ve ozet.json'daki `p_swap_capa_tipi` bunu görünür kılar.
4. Parite (USD dışı kur) etkisi arındırılmamıştır — kompozisyon
   yayımlanmıyor (altin_etkisi.py modül notu).
5. ROM/zorunlu karşılık bloke hesabı yükümlülükten düşülmemiştir; bazı
   "net rezerv" tanımları düşer.
6. Analitik bilançonun referans dönemi bir önceki iş günüdür: bizim serimiz
   VERİ tarihiyle etiketlenir, tablo tarihiyle değil.
7. Net dış varlık BAŞTAN SONA TL kaynaklıdır (USD çapası yoktur; brüt
   rezervin aksine). 8,9 trilyon TL'lik bir kalemde binde birlik kur
   uyumsuzluğu ~190 milyon USD sahte akım üretir. Kur olarak TCMB'nin
   bilanço değerleme kuralına uyan ALIŞ kuru kullanılır; satış kuru
   seviyeyi ~0,1 milyar USD kaydırırdı. Bu, kapatılmamış bir tanım
   farkıdır. Dönüşümün kayıp kaymadığı `capa_boslugu()` tanısıyla izlenir.
8. Yabancı merkez bankası swap bacağı gözlenemediği için basamak
   fonksiyonudur; yeni bir IRFCL gözlemi geldiğinde SIÇRAR. Bu sıçrama o
   günün işlemi değil, geç gelen bilgidir — akımdan `swap_capa_revizyon`
   sütunuyla ayrıştırılır (silinmez, ayrı gösterilir).

DOĞRULAMA PENCERESİ: bu hattın seviye ve kırılım hataları yalnız yerel bir
doğrulama kümesiyle, Haziran–Ağustos 2026 aralığında ölçülmüştür. Oynaklığın
yüksek olduğu rejimlerde (ör. Mart 2026 altın hareketi) hata bandı ÖLÇÜLMÜŞ
DEĞİLDİR; o dönemlerin sayıları bu bantlarla değil, yöntemin kendisiyle
savunulur.

Kalan farklar bir kalibrasyon sabitiyle KAPATILMAZ; bu dosyada hiçbir
uydurma katsayı, ofset ya da düzeltme faktörü yoktur.

Kullanım:
  python net_rezerv.py                  # haftalık + günlük seri, CSV yazar
  python net_rezerv.py --kontrol-dogrula # yerel kontrol dosyasıyla hata tablosu
  python net_rezerv.py --swap-dogrula   # ara değer/basamak hatası (eski seri)
  python net_rezerv.py --gunluk-dogrula # eski günlük proxy'nin geri-testi
  python net_rezerv.py --validate       # 24.04.2026 referans karşılaştırması
  python net_rezerv.py --capa 2026-02-27  # birikimli akım çıpasını değiştir
  python net_rezerv.py --daily-only --daily-start 01-04-2026

Yan dosyalar:
  altin_etkisi.py  altın fiyat etkisinden arındırma sistemi (bu dosya onu
                   içe alır; kendi başına da koşar)
  grafik.py        altı Plotly HTML
  ozet_uret.py     ozet.json — sayfadaki oynak sayılar
  irfcl_arsiv.py   haftalık IRFCL gözlem arşivi (Wayback backfill)
"""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re

import pandas as pd
import pdfplumber
import requests
import tcmb

import altin_etkisi

# EVDS anahtari kaynak koda GOMULMEZ: once TTO_EVDS_KEY ortam degiskeni
# (CI'da depo secret'i), sonra bu klasordeki .evds_key dosyasi (.gitignore'da).
_ANAHTAR_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".evds_key")


def _anahtar_adaylari(base_dir):
    """Anahtar dosyası adayları — sıra tüm hatlarda AYNI (bkz. README, guncelle.py).

    <proje>/.evds_key → depo kökü/.evds_key → kardeş TCMBNetRezerv/.evds_key.
    Kök adayı olmadan, temiz bir klonda köke tek dosya koyan kullanıcının bu hattı
    düşüyordu; hatların yarısı kökü okurken yarısı okumuyordu.
    """
    p = os.path.abspath(base_dir)
    kok = os.path.dirname(os.path.dirname(p))          # …/TTO Trading
    return [os.path.join(p, ".evds_key"),
            os.path.join(kok, ".evds_key"),
            os.path.join(kok, "Aktarılacak Projeler", "TCMBNetRezerv", ".evds_key")]


def _dosyadan_anahtar(adaylar, uyar=None):
    """İlk okunabilir ve boş olmayan adaydaki anahtar; hiçbiri yoksa ''."""
    for yol in adaylar:
        if not os.path.exists(yol):
            continue
        try:
            with open(yol, encoding="utf-8") as f:
                a = f.read().strip()
        except OSError as e:
            if uyar:
                uyar(f"UYARI: {yol} okunamadı ({type(e).__name__}).")
            continue
        if a:
            return a
    return ""


_ANAHTAR_ADAYLARI = _anahtar_adaylari(os.path.dirname(os.path.abspath(__file__)))


def _evds_anahtari() -> str:
    anahtar = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if anahtar:
        return anahtar
    anahtar = _dosyadan_anahtar(_ANAHTAR_ADAYLARI, print)
    if anahtar:
        return anahtar
    raise RuntimeError(
        "EVDS anahtari bulunamadi. export TTO_EVDS_KEY=<anahtar> ya da su "
        "dosyalardan BIRINE yazin (.gitignore'da):\n"
        + "".join(f"    {y}\n" for y in _ANAHTAR_ADAYLARI)
    )


API_KEY = _evds_anahtari()

SERIES = {
    # Stand-by Cari (haftalık - Cuma)
    "net_uluslararasi_rezerv_TL": "TP.AB.N06",
    "brut_doviz_rezerv_TL":       "TP.AB.N07",
    "brut_doviz_yukumluluk_TL":   "TP.AB.N08",
    "bankalar_doviz_mev_TL":      "TP.AB.N09",
    "imf_TL":                     "TP.AB.N10",
    "diger_yukumluluk_TL":        "TP.AB.N11",
    "diger_net_TL":               "TP.AB.N12",   # N06 = N07+N08+N12 kimliği için
    # Analitik bilanço (iş günü) — günlük delta için
    "dis_varliklar_TL":           "TP.AB.A02",   # A.1 Dış Varlıklar
    "bankalar_doviz_mev_gunluk_TL": "TP.AB.A14", # P.1bb Bankalar Döviz Mevduatı
    # A17 = Emisyon (Rezerv Para bileşeni). Eskiden yanlışlıkla "döviz
    # yükümlülüğü" diye buradaydı; günlük tahmin hatasının ana kaynağıydı.
    "emisyon_TL":                 "TP.AB.A17",
    # --- Piyasa tanımı (yeni birincil hat) ---
    "dis_yukumlulukler_TL":       "TP.AB.A11",   # P.1a Dış Yükümlülükler
    "toplam_doviz_yuk_TL":        "TP.AB.A10",   # P.1 Toplam (kimlik denetimi)
    "kamu_doviz_mev_TL":          "TP.AB.A13",   # P.1ba Kamu ve Diğer (akım arındırması)
    # --- Yalnız YAPISAL KİMLİK denetimi için (formüle girmezler) ---
    # Maliyeti düşük, getirisi yüksek: TCMB analitik bilanço tablosunun satır
    # düzenini değiştirdiğinde bu kimlikler bozulur ve hat ERKEN uyarı verir.
    # Seviye formülü A02/A11/A14'e dayandığı için o satırların yerinden
    # oynaması aksi hâlde sessizce yanlış bir seri üretirdi.
    "toplam_varlik_TL":           "TP.AB.A01",   # A  Toplam Varlıklar
    "ic_varliklar_TL":            "TP.AB.A03",   # A.2 İç Varlıklar
    "degerleme_hesabi_TL":        "TP.AB.A08",   # A.3 Değerleme Hesabı
    "toplam_yukumluluk_TL":       "TP.AB.A09",   # P  Toplam Yükümlülükler
    "doviz_mevduati_TL":          "TP.AB.A12",   # P.1b Döviz Mevduatı (=A13+A14)
    "mb_parasi_TL":               "TP.AB.A15",   # P.2 Merkez Bankası Parası
    # USD/TRY alış (günlük) — SERİNİN KULLANDIĞI KUR BUDUR
    "usdtry":                     "TP.DK.USD.A.YTL",
    # USD/TRY satış — formüle GİRMEZ, yalnız kur varyantı tanısı için
    # (bkz. kur_varyanti_farki): alış/satış tercihinin seviyeye etkisi
    # iddia edilmez, ÖLÇÜLÜR.
    "usdtry_satis":               "TP.DK.USD.S.YTL",
}

# Haftalık rezerv tablosu, MİLYON USD (grup bie_abres2, Cuma). Stand-By
# tablosundan (N*) farkı: bunlar zaten USD saklanır. N07'yi TP.DK.USD.A.YTL
# ile çevirmek TCMB'nin kendi çapraz kurlarıyla derlediği tabloya karşı
# sistematik bir sapma bırakıyordu; TOPLAM kullanınca o hata sınıfı kalkar.
REZERV_USD_SERIES = {
    "altin_M":  "TP.AB.C1",       # Altın
    "doviz_M":  "TP.AB.C2",       # Döviz + IMF rezerv pozisyonu + SDR
    "toplam_M": "TP.AB.TOPLAM",   # Toplam rezerv varlıkları
}

# TCMB'nin yurt içi bankalarla swap stoku — İŞ GÜNÜ, MİLYON USD, T−1 güncel.
# Yabancı merkez bankası bacağı BU SERİDE YOKTUR (yalnız IRFCL'de görünür);
# swap_stoku() ikisini birleştirir.
SWAP_SERIES = {
    "swap_alim_M":  "TP.SWAPTEKTAR.TOTALSTOKALIMYONLU",
    "swap_satim_M": "TP.SWAPTEKTAR.TOTALSTOKSATIMYONLU",
}

# Altın fiyatı, USD/ons, İŞ GÜNÜ (BİST Kıymetli Madenler Piyasası).
# AGORT03 = ağırlıklı ortalama (birincil), KAP03 = kapanış (yedek + tanı).
ALTIN_FIYAT_SERIES = {
    "altin_agort": "TP.ALTINPIYASA.AGORT03",
    "altin_kapanis": "TP.ALTINPIYASA.KAP03",
}

# Aylık IRFCL'nin altın MİKTARI (milyon troy ons) — yalnız haftalık arşiv
# öncesi geri doldurma için (altin_etkisi.ons_capalari kademe 3).
IRFCL_ONS_SERIES = {"ons_M": "TP.REZVARPD.K11"}

# --- Adlandırılmış sabitler (çıplak sayı bırakılmaz) -----------------------

# Haftalık çapa gecikmesi, TAKVİM GÜNÜ. Bir Cuma F'nin haftalık istatistiği
# F+6'da (Perşembe 14:30, TCMB Haftalık Para ve Banka İstatistikleri yayın
# takvimi) yayımlanır; t verisiyle derlenen tablo t+1'de çıktığı için ancak
# F+6 ≤ t+1 ⇔ F ≤ t−5 koşulunu sağlayan Cuma kullanılabilir.
#
# Seçim ölçütü YAYIN TAKVİMİDİR, hata istatistiği değil. Dürüstlük payı:
#   · 4, 5 ve 6 günlük gecikmeler bir yerel doğrulama kümesinde ölçüldüğünde
#     ortalama hata bakımından birbirinden AYRIŞMIYOR (üçü de yuvarlama
#     yarı-adımı mertebesinde). Yani bu ölçüm tek başına ayırt edici değildir.
#   · Ayrıştıran şey artığın YAPISI: 5 günde artık, aynı kümenin tamamında
#     yuvarlama zeminine (≤ 0,05 mlr USD) çökerken 4 ve 6 günde basamak
#     şeklinde artık bırakıyor. Bu yapısal bir gözlemdir, uydurulmuş bir
#     katsayı değil — GECIKME_GUN kesikli bir takvim parametresidir.
#   · "Brüt, altın ve swap kalemlerinde ayrı ayrı sınandı" ifadesi BAĞIMSIZ
#     kanıt değildir: üç kalem de aynı haftalık Cuma yayın takvimine bağlıdır,
#     yani aynı kanıtın üç kopyasıdır.
#   · Yayın saati 14:30 olduğu için F+6 ≤ t+1 koşulu sabah derlenen bir tablo
#     için sınırda kalır; o durumda 6 gerekebilir.
GECIKME_GUN = 5

# Yapısal kimlik denetimi toleransı, BİN TL. EVDS analitik bilançoyu bin TL'ye
# yuvarlayarak yayımlar; A01 = A02+A03+A08 gibi kimlikler bu yüzden tam sıfır
# değil ±1 bin TL sapar. Sıfır tolerans kullanmak her koşuda sahte hata verir.
KIMLIK_TOLERANS_BIN_TL = 10.0

# Çapraz kaynak denetimi toleransı, MİLYON USD (EVDS haftalık tablo ↔ IRFCL
# PDF). İki yayın aynı sayıyı farklı yuvarlamayla basıyor.
CAPRAZ_TOLERANS_M = 5.0

# Piyasa tanımı ile Stand-By 2A arasındaki farkın denetimi.
#
# DİKKAT: burada eskiden SABİT bir bant vardı — (1,5 – 3,0) milyar USD. O bant
# yalnız birkaç aylık bir pencereye bakılarak seçilmişti ve serinin kendisinde
# geçerli değildi: fark 2023'ten bu yana yukarı sürükleniyor (Cuma ortalaması
# 2023'te ≈ +1,2, 2026'da ≈ +1,8) ve tek tek haftalarda −2 ile +2,5 arasında
# salınıyor; tüm tarihteki Cuma'ların yaklaşık beşte biri o sabit bandın
# dışında kalıyordu. Yani dedektör pencereye uydurulmuştu.
#
# Yerine YUVARLANAN dağılım kullanılıyor: son TANIM_FARKI_PENCERE Cuma'nın
# medyanı ± TANIM_FARKI_MAD_KAT × MAD. Ölçüt "fark şu sabit aralıkta mı"
# değil, "fark kendi yakın geçmişinin dağılımının dışına çıktı mı" olur —
# sürüklenme uyarı üretmez, SIÇRAMA üretir.
TANIM_FARKI_PENCERE = 52          # ~bir yıllık Cuma sayısı
TANIM_FARKI_MAD_KAT = 4.0         # medyan ± 4·MAD; normal dağılımda ≈ ±2,7σ
TANIM_FARKI_TABAN = 0.30          # MAD çok küçükken bant kapanmasın (mlr USD)
TANIM_FARKI_SON_N = 8             # son kaç Cuma sınanır

# Günlük serinin en az bu kadarı HAFTALIK IRFCL çapasına dayanmalı. Altındaysa
# uyarı basılır. Gerekçe ölçüme dayanır, kalibrasyona değil: haftalık çapaya
# oturan günlerde swap hariç serinin bağımsız bir referansa karşı sapması
# gürültü düzeyinde (±0,02 mlr USD) kalırken, aylık çapaya oturan günlerde on
# katına (±0,20) çıkıyor ve çapa yaşıyla birlikte büyüyor. Hedef bir kalite
# eşiğidir; hesaba GİRMEZ, yalnız kapsamı görünür kılar.
SWAP_HAFTALIK_CAPA_HEDEF = 0.50

# Kur varyantı tanısı (bkz. kur_varyanti_farki): alış yerine satış kuru
# kullanılsaydı seviye ne kadar kayardı. Bu bir KALİBRASYON DEĞİL, ilan edilen
# bir tanım farkının ölçüsüdür. Eşik, normal alış/satış makasının ürettiği
# kaymanın (mertebe: 0,1 mlr USD) belirgin üstünde tutulur: makas açıldığında
# kur seçimi maddi bir tercih hâline gelir ve bu görünür olmalıdır.
KUR_VARYANT_UYARI_MLR = 0.30

# Çapa boşluğu tanısı (bkz. capa_boslugu). Aynı dayanıklılık mantığı: sabit
# bir bant değil, serinin kendi yakın geçmişinin dağılımı.
CAPA_BOSLUK_PENCERE = 52
CAPA_BOSLUK_MAD_KAT = 6.0
CAPA_BOSLUK_TABAN = 0.50   # mlr USD; boşluk zaten oynak, taban geniş tutulur
CAPA_BOSLUK_SON_N = 4

# Tazelik toleransları — İKİ AYRI ÖLÇÜ, ikisi de DUVAR SAATİNE göre.
#
# DİKKAT (düzeltilmiş hata): bu denetim eskiden `bugun=son_veri` ile
# çağrılıyordu; son_veri'yi de analitik bilançonun son gözlemi belirlediği
# için "analitik bilanço" kaleminin yaşı YAPISAL OLARAK her zaman 0 çıkıyor,
# denetim hiçbir koşulda ateşlenemiyordu. Daha kötüsü: EVDS toptan düşüp bütün
# seriler aynı eski tarihte donsa son_veri de donacağı için TÜM yaşlar
# toleransın içinde kalıyor ve hat "uyarı yok" basıyordu. Yani projenin adını
# koyduğu "sessiz bayatlama" hatasının tam kendisi denetim mekanizmasının
# içindeydi. Referans artık gerçek takvim günüdür.
#
# (a) CEPHE kaynakları — her iş günü yayımlanan birincil beslemeler. Yaş İŞ
#     GÜNÜ cinsinden ölçülür; hafta sonunu kendiliğinden hesaba katar.
#     Eşik, resmi tatil payı bırakacak kadar geniş tutulmuştur: Türkiye'de
#     bayram tatilleri köprü günleriyle birlikte bir haftayı bulabildiği için
#     4 iş günlük "doğru" eşik her bayramda sahte uyarı verirdi. 7 iş günü,
#     gerçekten donmuş bir beslemeyi (20+ iş günü) yine de yakalar.
# (b) DÜŞÜK FREKANSLI kaynaklar — haftalık/aylık yayınlar; TAKVİM günü.
TAZELIK_TOLERANS_ISGUNU = {
    "analitik bilanço (TP.AB.A*)": 7,
    "USD/TRY (TP.DK.USD.A.YTL)": 7,
    "altın fiyatı (TP.ALTINPIYASA.*)": 7,
    "swap stoku (TP.SWAPTEKTAR.*)": 7,
}
TAZELIK_TOLERANS_GUN = {
    "haftalık rezerv (TP.AB.C*/TOPLAM)": 12,
    "Stand-By 2A (TP.AB.N*)": 12,
    "haftalık IRFCL gözlemi": 14,
    "aylık IRFCL (TP.DOVVARNC.*)": 60,
}

# Bütün cephe kaynakları AYNI tarihte bitiyorsa bu normaldir (hepsi aynı iş
# günü takvimini paylaşır). Ama o ortak tarih bu kadar iş gününden eskiyse
# tek bir seri değil BESLEMENİN KENDİSİ düşmüş demektir — ayrı uyarı basılır,
# çünkü tek tek kaynak uyarıları bu durumda yanıltıcı biçimde "hepsi bozuk"
# gibi okunur.
CEPHE_ORTAK_DURUS_ISGUNU = 3

# Cephe kaynağı ile düşük frekanslı kaynak arasındaki GÖRECELİ yaş farkı için
# eşik (takvim günü). Duvar saati denetimini tamamlar: haftalık tablo hâlâ
# tolerans içinde ama günlük bilançodan alışılmadık ölçüde gerideyse yayın
# takvimi kaymış olabilir.
GORELI_YAS_TOLERANS_GUN = 20

# IRFCL (Uluslararası Rezervler ve Döviz Likiditesi) — AYLIK, ay sonu.
# Haftalık PDF'teki II.2 / II.3 kalemlerinin resmi seri karşılığı; ay sonu
# tarihlerinde PDF ile milyon USD hassasiyetinde AYNI (bkz. irfcl_arsiv.py
# --dogrula). Swap hariç net rezervin tarihsel omurgası bu iki seri.
IRFCL_SERIES = {
    "ii2_M": "TP.DOVVARNC.K14",   # II.2 Yurt içi para karşılığı döviz forward/future (toplam)
    "ii3_M": "TP.DOVVARNC.K23",   # II.3 Diğer (repo/ticari/diğer borç-alacak, toplam)
}

WEEKLY_TABLES_PAGE = (
    "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Istatistikler/"
    "Odemeler+Dengesi+ve+Ilgili+Istatistikler/Uluslararasi+Rezervler+ve+Doviz+Likiditesi/"
    "Veri+(Tablolar)+-+Haftalik"
)

# Haftalık IRFCL gözlem arşivi (irfcl_arsiv.py doldurur, her koşuda canlı PDF
# noktası eklenir). Ay içi gerçek haftalık gözlemler burada birikiyor.
GOZLEM_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "irfcl_gozlem.csv")

# EVDS tek istekte yaklaşık 700 satırdan sonrasını sessizce kırpıyor (uzun
# aralık istendiğinde aralığın SONUNDAN geriye doğru dolduruyor). Bu yüzden
# istek yıllık parçalara bölünüyor — aksi halde --start geriye çekildiğinde
# tarihsel derinlik alınmıyor.
EVDS_PARCA_GUN = 366


# ----------------------------------------------------------------------------
# EVDS
# ----------------------------------------------------------------------------
def _read_evds_seri(client: "tcmb.Client", code: str, start: str,
                    end: str) -> pd.Series:
    """Tek seriyi yıllık parçalar hâlinde çekip birleştirir (satır sınırı için)."""
    t0 = pd.to_datetime(start, dayfirst=True)
    t1 = pd.to_datetime(end, dayfirst=True)
    parcalar: list[pd.Series] = []
    imlec = t0
    while imlec <= t1:
        son = min(imlec + pd.Timedelta(days=EVDS_PARCA_GUN - 1), t1)
        try:
            df = client.read(
                code,
                start=imlec.strftime("%d-%m-%Y"),
                end=son.strftime("%d-%m-%Y"),
            )
        except KeyError:
            # tcmb istemcisi BOŞ yanıtı (o parçada hiç gözlem yok) KeyError
            # olarak fırlatıyor. Bu bir hata değil, seri o yıllarda henüz
            # başlamamış demektir; başlangıç tarihi geriye çekildiğinde tüm
            # hattı düşürüyordu. Parça atlanır — BÜTÜN parçalar boşsa aşağıda
            # boş seri döner ve tazelik denetimi bunu zaten yakalar.
            df = pd.DataFrame()
        if len(df):
            parcalar.append(df.iloc[:, 0])
        imlec = son + pd.Timedelta(days=1)
    if not parcalar:
        return pd.Series(dtype=float)
    s = pd.concat(parcalar)
    return s[~s.index.duplicated(keep="last")].sort_index()


# Analitik bilanço kalemleri yalnız GÜNLÜK pencerede gerekli; haftalık
# Stand-By serisi ise tüm tarihsel derinliği tutar. İkisini aynı başlangıçtan
# çekmek EVDS'e gereksiz yüzlerce istek attırıyordu.
GUNLUK_AB_ETIKETLERI = {
    "dis_varliklar_TL", "bankalar_doviz_mev_gunluk_TL", "emisyon_TL",
    "dis_yukumlulukler_TL", "toplam_doviz_yuk_TL", "kamu_doviz_mev_TL",
    "toplam_varlik_TL", "ic_varliklar_TL", "degerleme_hesabi_TL",
    "toplam_yukumluluk_TL", "doviz_mevduati_TL", "mb_parasi_TL",
    "usdtry_satis",
}


def fetch_evds(start: str, end: str,
               gunluk_start: str | None = None) -> pd.DataFrame:
    """SERIES sözlüğünü çeker. `gunluk_start` verilirse analitik bilanço
    kalemleri o tarihten itibaren istenir (haftalık seriler `start`'tan)."""
    client = tcmb.Client(api_key=API_KEY)
    out: dict[str, pd.Series] = {}
    for label, code in SERIES.items():
        s = (gunluk_start if (gunluk_start and label in GUNLUK_AB_ETIKETLERI)
             else start)
        out[label] = _read_evds_seri(client, code, s, end)
    # sort=False: pandas'ın varsayılanı değişiyor, davranış sabitlensin diye
    # açıkça veriliyor (hemen ardından zaten sort_index çağrılıyor).
    df = pd.concat(out, axis=1, sort=False).sort_index()
    df["usdtry"] = df["usdtry"].ffill()
    if "usdtry_satis" in df.columns:
        df["usdtry_satis"] = df["usdtry_satis"].ffill()
    return df


def fetch_irfcl_aylik(start: str, end: str) -> pd.DataFrame:
    """EVDS aylık IRFCL: II.2 ve II.3 (Milyon USD), ay SONU tarihine indekslenir.

    EVDS aylık serileri ayın 1'i etiketiyle döner; IRFCL'de değer ayın SON
    gününe aittir. Haftalık PDF ile hizalamak için indeks ay sonuna kaydırılır.
    """
    client = tcmb.Client(api_key=API_KEY)
    out: dict[str, pd.Series] = {}
    for label, code in IRFCL_SERIES.items():
        out[label] = _read_evds_seri(client, code, start, end)
    df = pd.concat(out, axis=1, sort=False).sort_index().dropna(how="all")
    df.index = df.index + pd.offsets.MonthEnd(0)
    df["toplam_M"] = df["ii2_M"].fillna(0.0) + df["ii3_M"].fillna(0.0)
    df.index.name = "tarih"
    return df


def fetch_grup(seriler: dict[str, str], start: str, end: str,
               ay_sonuna_kaydir: bool = False) -> pd.DataFrame:
    """Verilen kod sözlüğünü tek DataFrame olarak çeker (etiket = sütun adı).

    `ay_sonuna_kaydir`: EVDS aylık serileri ayın 1'i etiketiyle döner ama
    değer ayın SON gününe aittir; haftalık/günlük takvimle hizalamak için
    indeks ay sonuna taşınır.
    """
    client = tcmb.Client(api_key=API_KEY)
    out: dict[str, pd.Series] = {}
    for label, code in seriler.items():
        out[label] = _read_evds_seri(client, code, start, end)
    df = pd.concat(out, axis=1, sort=False).sort_index().dropna(how="all")
    if ay_sonuna_kaydir and len(df):
        df.index = df.index + pd.offsets.MonthEnd(0)
    df.index.name = "tarih"
    return df


# ----------------------------------------------------------------------------
# Piyasa tanımı — çapa kuralı ve seviye formülleri
# ----------------------------------------------------------------------------
def capa_serisi(index: pd.DatetimeIndex, capa_index: pd.DatetimeIndex,
                gecikme: int = GECIKME_GUN) -> pd.Series:
    """Her t için kullanılabilir en son çapa tarihi: son F ≤ t − gecikme.

    Brüt rezerv, altın kırılımı ve swap stoku bu tek kuralı paylaşır
    (gerekçesi modül açıklamasının C bölümünde). Çapa yoksa NaT — geriye
    doğru uydurma YAPILMAZ.
    """
    if len(capa_index) == 0 or len(index) == 0:
        return pd.Series(pd.NaT, index=index)
    sol = pd.DataFrame({"t": pd.DatetimeIndex(index)})
    sol["arama"] = sol["t"] - pd.Timedelta(days=gecikme)
    sag = pd.DataFrame({"capa": pd.DatetimeIndex(capa_index).sort_values()})
    b = pd.merge_asof(sol.sort_values("arama"), sag, left_on="arama",
                      right_on="capa", direction="backward")
    return pd.Series(b["capa"].values, index=b["t"].values).reindex(index)


def _capadan(seri: pd.Series, capalar: pd.Series) -> pd.Series:
    """Çapa tarihlerindeki değerleri günlük takvime taşır (hizalama yardımcısı).

    Çapa günü (Cuma / ay sonu) tatile denk gelip günlük seride karşılığı
    yoksa en yakın ÖNCEKİ iş günü alınır — bu bir tarih hizalamasıdır,
    veri uydurma değildir.
    """
    kaynak = seri.dropna()
    if kaynak.empty:
        return pd.Series(float("nan"), index=capalar.index)
    hizali = kaynak.reindex(
        kaynak.index.union(capalar.dropna().unique())).sort_index().ffill()
    return pd.Series(hizali.reindex(capalar.values).values,
                     index=capalar.index)


def piyasa_net_dis_varlik(ab: pd.DataFrame) -> pd.Series:
    """(A02 − A11 − A14)/kur_alış — milyar USD, aynı gün, çapa yok.

    KUR SEÇİMİ (a priori gerekçe, hata istatistiği değil): TCMB analitik
    bilançoyu kendi GÖSTERGE NİTELİĞİNDEKİ ALIŞ kurlarıyla TL'ye çevirerek
    yayımlar; ters çevirmede aynı kuru kullanmak dönüşümü kapatır. Satış kuru
    kullanmak dönüşümü kapatmaz ve seviyeyi sistematik olarak ~0,1 milyar USD
    kaydırır — bu, KAPATILMAMIŞ bir tanım farkıdır ve sayfada da böyle yazılır.

    KAPATILMAMIŞ İKİNCİ FARK (bilinen sınır): bu seri baştan sona TL kaynaklı
    hesaplanır, USD çapası yoktur. 8,9 trilyon TL'lik bir dış varlık
    kaleminde binde birlik bir kur uyumsuzluğu ~190 milyon USD'lik sahte akım
    üretir. Brüt rezerv (piyasa_brut) bu yüzden USD çapasına oturtulmuştur;
    net dış varlık için eşdeğer bir USD kaynağı YOK (IRFCL yükümlülük bacağını
    bu kırılımda yayımlamıyor), dolayısıyla brütteki gibi bir USD çapası
    kurulamıyor. Kurulabilen İKİ tanı var ve ikisi de koşuluyor:
      · `capa_boslugu()` — TL kaynak ile USD kaynak arasındaki boşluk kayıyor
        mu (yani dönüşüm TCMB'nin değerleme kurundan ayrışıyor mu);
      · `kur_varyanti_farki()` — alış yerine satış kuru kullanılsaydı seviye
        ne kadar kayardı. Bu, yukarıdaki "~0,1 milyar USD" iddiasını her
        koşuda ÖLÇÜLEN bir sayıya çevirir.
    Sessizce varyanta geçilmez; fark ilan edilir.
    """
    tl = (ab["dis_varliklar_TL"] - ab["dis_yukumlulukler_TL"]
          - ab["bankalar_doviz_mev_gunluk_TL"])
    return tl / ab["usdtry"] / 1e6


def kur_varyanti_farki(ab: pd.DataFrame) -> pd.Series:
    """Alış yerine satış kuru kullanılsaydı seviye ne kadar kayardı (mlr USD).

        fark(t) = ND_alış(t) − ND_satış(t) = TL(t)·[1/alış(t) − 1/satış(t)]

    Yayımlanan seri ALIŞ kuruyla kurulur (gerekçe: piyasa_net_dis_varlik
    docstring'i). Bu fonksiyon kararı değiştirmez; kararın BEDELİNİ ölçer.
    Sayfada "kapatılmamış tanım farkı" diye yazılan sayı buradan gelir —
    kaynak koda gömülü bir tahmin değil, her koşuda EVDS'ten türetilen bir
    büyüklük. Satış kuru serisi yoksa boş seri döner (tanı atlanır, hat
    durmaz).
    """
    if "usdtry_satis" not in ab.columns:
        return pd.Series(dtype=float)
    tl = (ab["dis_varliklar_TL"] - ab["dis_yukumlulukler_TL"]
          - ab["bankalar_doviz_mev_gunluk_TL"])
    satis = ab["usdtry_satis"]
    return ((tl / ab["usdtry"] - tl / satis) / 1e6).dropna()


def capa_boslugu(ab: pd.DataFrame, rez_usd: pd.DataFrame) -> pd.Series:
    """TL kaynak ile USD kaynak arasındaki boşluk — Cuma'larda, milyar USD.

        boşluk(F) = TOPLAM(F)/1000 − A02(F)/kur(F)

    Bu, "USD cinsinden yayımlanan resmi rezerv varlıkları" ile "TL bilanço
    kaleminin bizim kurumuzla USD'ye çevrilmiş hâli" arasındaki farktır. İki
    bileşeni var: (i) A02'nin rezerv tanımına girmeyen diğer döviz alacakları
    — YAPISAL, 2–3 milyar USD; (ii) kur bacağındaki uyumsuzluk — OLMAMASI
    gereken. Boşluk büyük ölçüde sabit kaldığı sürece (i) baskındır; ANİ ya da
    sürekli kayması TL→USD dönüşümünün TCMB'nin kendi değerleme kurundan
    ayrıştığını gösterir. Seviye formülüne GİRMEZ, yalnız izlenir.
    """
    toplam = rez_usd["toplam_M"].dropna()
    a02_usd = (ab["dis_varliklar_TL"] / ab["usdtry"] / 1e6).dropna()
    ortak = toplam.index.intersection(a02_usd.index)
    return (toplam.reindex(ortak) / 1000.0 - a02_usd.reindex(ortak)).sort_index()


def piyasa_brut(ab: pd.DataFrame, rez_usd: pd.DataFrame) -> pd.DataFrame:
    """Brüt rezerv: haftalık USD çapası + analitik bilanço hafta içi hareketi.

    Dönen sütunlar: brut_usd, brut_capa_tarih.
    """
    toplam = rez_usd["toplam_M"].dropna()
    capalar = capa_serisi(ab.index, toplam.index)
    a02_usd = ab["dis_varliklar_TL"] / ab["usdtry"] / 1e6
    brut = (_capadan(toplam, capalar) / 1000.0
            + a02_usd - _capadan(a02_usd, capalar))
    return pd.DataFrame({"brut_usd": brut, "brut_capa_tarih": capalar})


def altin_doviz_kirilimi(rez_usd: pd.DataFrame, fiyat: pd.Series,
                         brut: pd.Series,
                         index: pd.DatetimeIndex) -> pd.DataFrame:
    """Brüt rezervin altın/döviz kırılımı — oransal altın biçimi.

    altin(t) = C1(F)/1000 × P(t)/P(F)   ve   doviz(t) = brut(t) − altin(t)

    Oransal biçim, fiyat serisinin TCMB değerleme fiyatına göre sistematik
    iskontosunu P(t)/P(F) oranında sadeleştirir; miktar × fiyat biçiminde o
    iskonto doğrudan seviyeye geçerdi.
    """
    c1 = rez_usd["altin_M"].dropna()
    capalar = capa_serisi(index, c1.index)
    altin = (_capadan(c1, capalar) / 1000.0
             * fiyat.reindex(index) / _capadan(fiyat, capalar))
    return pd.DataFrame({"altin_usd": altin, "doviz_usd": brut - altin,
                         "altin_capa_tarih": capalar})


def irfcl_capalari(gozlem: pd.DataFrame | None,
                   aylik: pd.DataFrame | None) -> pd.DataFrame:
    """IRFCL swap çapaları — index tarih, sütun [c_usd, tip].

    c_usd = −(II.2 + II.3)/1000, yani POZİTİF stok konvansiyonu.
    tip   = "haftalık" (PDF gözlemi) ya da "aylık" (EVDS ay sonu serisi).
    Aynı tarihte ikisi de varsa haftalık kazanır — tam o güne aittir.
    """
    parcalar: list[pd.DataFrame] = []
    if aylik is not None and len(aylik):
        s = -(aylik["ii2_M"].fillna(0.0) + aylik["ii3_M"].fillna(0.0)) / 1000.0
        parcalar.append(pd.DataFrame({"c_usd": s, "tip": "aylık",
                                      "oncelik": 1}))
    if gozlem is not None and len(gozlem):
        s = -(pd.to_numeric(gozlem["ii2_M"], errors="coerce").fillna(0.0)
              + pd.to_numeric(gozlem["ii3_M"], errors="coerce").fillna(0.0)) / 1000.0
        parcalar.append(pd.DataFrame({"c_usd": s, "tip": "haftalık",
                                      "oncelik": 2}))
    if not parcalar:
        return pd.DataFrame(columns=["c_usd", "tip"],
                            index=pd.DatetimeIndex([], name="tarih"))
    tum = pd.concat(parcalar).sort_values("oncelik")
    tum = tum[~tum.index.duplicated(keep="last")].sort_index()
    tum.index.name = "tarih"
    return tum[["c_usd", "tip"]]


def swap_stoku(swap_gunluk: pd.DataFrame, capalar: pd.DataFrame,
               index: pd.DatetimeIndex) -> pd.DataFrame:
    """Toplam swap stoku ve yerli/yabancı kırılımı — milyar USD, POZİTİF stok.

      S(t)            = (alım yönlü − satım yönlü)/1000   ← günlük, gözlenen
      swap_toplam(t)  = C(G) + [S(t) − S(G)]
      swap_yerli(t)   = S(t)
      swap_yabanci(t) = C(G) − S(G)   ← artık; IRFCL frekansında tazelenir

    Artığın YABANCI bacağa yazılması kasıtlıdır: yerli bacak bağımsız ve
    günlük gözlenen bir seridir, yabancı bacak ise ancak IRFCL frekansında
    bilinir. Gözlenemeyene artık yazmak doğru olandır.

    Dönen sütunlar: swap_toplam_usd, swap_yerli_usd, swap_yabanci_usd,
    swap_capa_tarih, swap_capa_tipi.
    """
    bos = pd.Series(float("nan"), index=index)
    if swap_gunluk.empty or capalar.empty:
        return pd.DataFrame({"swap_toplam_usd": bos, "swap_yerli_usd": bos,
                             "swap_yabanci_usd": bos,
                             "swap_capa_tarih": pd.Series(pd.NaT, index=index),
                             "swap_capa_tipi": pd.Series(pd.NA, index=index,
                                                         dtype="object")})
    s = ((swap_gunluk["swap_alim_M"].fillna(0.0)
          - swap_gunluk["swap_satim_M"].fillna(0.0)) / 1000.0).sort_index()
    # Çapa yalnız S'nin de bilindiği tarihlerden seçilir: S(G) olmadan
    # [S(t) − S(G)] kurulamaz, yarım hesapla devam edilmez.
    uygun = pd.DatetimeIndex([g for g in capalar.index if len(s.loc[:g])])
    capa_t = capa_serisi(index, uygun)
    c_g = pd.Series(capalar["c_usd"].reindex(capa_t.values).values,
                    index=index)
    tip = pd.Series(capalar["tip"].reindex(capa_t.values).values, index=index)
    s_t = s.reindex(index)
    s_g = _capadan(s, capa_t)
    return pd.DataFrame({
        "swap_toplam_usd": c_g + (s_t - s_g),
        "swap_yerli_usd": s_t,
        "swap_yabanci_usd": c_g - s_g,
        "swap_capa_tarih": capa_t,
        "swap_capa_tipi": tip,
    })


def calculate_weekly_net_reserves(
    df: pd.DataFrame, swap_duzeltme_usd: pd.Series | None = None
) -> pd.DataFrame:
    """Haftalık (Cuma) net rezerv ve alt kalemler -- milyar USD."""
    weekly = df.dropna(subset=["net_uluslararasi_rezerv_TL"]).copy()
    for col, target in [
        ("net_uluslararasi_rezerv_TL", "net_rezerv_usd"),
        ("brut_doviz_rezerv_TL", "brut_rezerv_usd"),
        ("brut_doviz_yukumluluk_TL", "brut_yukumluluk_usd"),
        ("bankalar_doviz_mev_TL", "bankalar_doviz_mev_usd"),
        ("imf_TL", "imf_usd"),
        ("diger_yukumluluk_TL", "diger_yukumluluk_usd"),
    ]:
        weekly[target] = weekly[col] * 1_000.0 / weekly["usdtry"] / 1e9
    if swap_duzeltme_usd is not None:
        weekly["swap_duzeltme_usd"] = swap_duzeltme_usd.reindex(weekly.index)
        weekly["swap_haric_net_rezerv_usd"] = (
            weekly["net_rezerv_usd"] + weekly["swap_duzeltme_usd"]
        )
    return weekly


# ----------------------------------------------------------------------------
# Swap düzeltmesi (II.2 + II.3) — GERÇEK gözlemlerden
# ----------------------------------------------------------------------------
def swap_gozlemleri(start: str, end: str,
                    canli_pdf: dict | None = None) -> pd.DataFrame:
    """(II.2 + II.3) gerçek gözlem tablosu — milyar USD, tarih indeksli.

    Üç kaynak birleştirilir (çakışmada haftalık gözlem kazanır, çünkü tam o
    güne ait):
      1. EVDS aylık IRFCL (ay sonu)          → kaynak = "evds_aylik"
      2. irfcl_gozlem.csv (haftalık PDF arşivi) → kaynak = "irfcl_pdf"
      3. o anki canlı haftalık PDF              → kaynak = "irfcl_pdf"

    Uydurma/genişletme YOK: her satır yayımlanmış bir IRFCL gözlemidir.
    """
    aylik = fetch_irfcl_aylik(start, end)
    kayit = pd.DataFrame({
        "swap_duzeltme_usd": aylik["toplam_M"] / 1_000.0,
        "kaynak": "evds_aylik",
    })

    if os.path.exists(GOZLEM_CSV):
        ark = pd.read_csv(GOZLEM_CSV, index_col=0, parse_dates=True)
        haftalik = pd.DataFrame({
            "swap_duzeltme_usd": (ark["ii2_M"] + ark["ii3_M"]) / 1_000.0,
            "kaynak": "irfcl_pdf",
        })
        kayit = pd.concat([kayit, haftalik])

    if canli_pdf and "tarih" in canli_pdf:
        # 0.0 VARSAYILANI YOK: eksik bir bacağı sıfır saymak çapayı sessizce
        # milyarlarca dolar kaydırır (II.3 tek başına ~4 mlr USD). parse_weekly_pdf
        # zaten eksik bacakta hata veriyor; burası ikinci savunma — doğrudan
        # indeksleme, eksikse KeyError.
        ii2 = canli_pdf["II_2_acik_M"] + canli_pdf["II_2_fazla_M"]
        ii3 = canli_pdf["II_3_toplam_M"]
        kayit.loc[canli_pdf["tarih"]] = [(ii2 + ii3) / 1_000.0, "irfcl_pdf"]

    # Aynı tarihte hem aylık hem haftalık varsa haftalığı tut
    kayit = kayit.sort_values("kaynak")           # evds_aylik < irfcl_pdf
    kayit = kayit[~kayit.index.duplicated(keep="last")].sort_index()
    kayit.index.name = "tarih"
    return kayit


def swap_duzeltme_serisi(gozlem: pd.DataFrame, index: pd.DatetimeIndex,
                         ileri_tasima_gun: int = 21) -> pd.Series:
    """Gözlemleri istenen takvime taşır — zaman ağırlıklı doğrusal ara değer.

    Kurallar (kasıtlı olarak muhafazakâr):
      • İlk gözlemden ÖNCE  → NaN (geriye doğru uzatma YOK).
      • Gözlemler ARASINDA  → iki gerçek gözlem arasında zamana göre doğrusal
        ara değer. IRFCL swap pozisyonu vade defterinin doğal akışıyla değişir;
        iki yayım arasını doğrusal bağlamak, ay sonu değerini bir ay boyunca
        sabit tutmaktan (basamak) daha isabetli: elde 7 ay-içi gerçek haftalık
        gözlem varken ortalama |hata| ara değerde 0,41 / basamakta 0,91 milyar
        USD (%55 daha az). Ölçüm: `python net_rezerv.py --swap-dogrula`.
      • Son gözlemden SONRA → en fazla `ileri_tasima_gun` gün sabit taşınır
        (haftalık IRFCL ~1 hafta gecikmeli yayımlanır), sonrası NaN.

    Dönen seri milyar USD; NaN kalan yerlerde "swap hariç net rezerv" de
    hesaplanmaz — sahte doluluk üretilmez.
    """
    g = gozlem["swap_duzeltme_usd"].dropna().sort_index()
    g = g[~g.index.duplicated(keep="last")]   # union/interpolate tekrar kaldırmaz
    if g.empty:
        return pd.Series(index=index, dtype=float)

    birlesik = g.reindex(g.index.union(index)).sort_index()
    ara = birlesik.interpolate(method="time", limit_area="inside")
    ara = ara.reindex(index)

    # Son gözlemden sonrası: sınırlı ileri taşıma
    son_t, son_v = g.index[-1], g.iloc[-1]
    kuyruk = (index > son_t) & (index <= son_t + pd.Timedelta(days=ileri_tasima_gun))
    ara[kuyruk] = son_v
    ara[index > son_t + pd.Timedelta(days=ileri_tasima_gun)] = float("nan")
    ara[index < g.index[0]] = float("nan")
    return ara


def swap_gozlem_maskesi(gozlem: pd.DataFrame,
                        index: pd.DatetimeIndex) -> pd.Series:
    """İlgili tarih gerçek bir IRFCL gözlemi mi? (grafikte işaretlemek için)"""
    return pd.Series(index.isin(gozlem.index), index=index)


def calculate_daily_net_reserves(
    df: pd.DataFrame, swap_duzeltme_usd: pd.Series | None = None,
    swap_gozlem: pd.Series | None = None,
) -> pd.DataFrame:
    """Cuma anchor + analitik bilanço delta ile günlük net rezerv tahmini.

    Net Rezerv (T) = (N06_son_Cuma_TL + ΔAnalitik_TL(son_Cuma→T)) / USDTRY(T)
    ΔAnalitik = Δ(A02 Dış Varlıklar − A14 Bankaların Döviz Mevduatı)

    Cuma günlerinde delta = 0 ⇒ resmi haftalık değerle eşleşir.

    Parameters
    ----------
    df : EVDS dataframe (fetch_evds çıktısı)
    swap_duzeltme_usd : Optional. Tarihe göre (II.2 + II.3), milyar USD —
        `swap_duzeltme_serisi` çıktısı. Verilirse
        Swap Hariç Net Rezerv (T) = Net Rezerv (T) + swap_duzeltme(T).
        Düzeltmenin NaN olduğu tarihlerde swap hariç seri de NaN kalır.
    """
    out = df[["dis_varliklar_TL", "bankalar_doviz_mev_gunluk_TL",
              "usdtry"]].copy()
    # Dış Varlıklar - Bankaların Döviz Mevduatı (A02 - A14). N06'nın hafta
    # içinde gerçekten oynayan iki bacağı bunlar; IMF ve "diğer" yükümlülük
    # hafta içinde sabit kabul edilir (bkz. modül açıklaması + --gunluk-dogrula).
    out["analitik_net_TL"] = (
        out["dis_varliklar_TL"] - out["bankalar_doviz_mev_gunluk_TL"]
    )

    # Cuma anchor: TP.AB.N06 (TL) ve aynı Cumadaki analitik net (TL)
    # NOT: Cuma günü analitik bilanço yayımlanmamış olabilir (yayım gecikmesi).
    # Bu durumda anchor için en yakın ÖNCEKİ iş günü değeri kullanılır.
    n06 = df["net_uluslararasi_rezerv_TL"]
    out["anchor_n06_TL"] = n06.ffill()
    # Analitik veriyi önce ffill et (eksik günleri doldur), sonra anchor seç
    analitik_filled = out["analitik_net_TL"].ffill()
    out["anchor_analitik_TL"] = analitik_filled.where(n06.notna()).ffill()
    out["anchor_date"] = pd.Series(out.index, index=out.index).where(
        n06.notna()
    ).ffill()

    out["delta_analitik_TL"] = out["analitik_net_TL"] - out["anchor_analitik_TL"]
    out["net_rezerv_usd"] = (
        (out["anchor_n06_TL"] + out["delta_analitik_TL"])
        * 1_000.0 / out["usdtry"] / 1e9
    )

    # Brüt rezerv günlük (sadece dış varlıklardan):
    # Stand-by cari Brüt rezerv günlük olarak yok; analitik Dış Varlıklar
    # altın+döviz toplamı olduğu için yaklaşık brüt rezerv değeri verir.
    out["analitik_dis_varlik_usd"] = (
        out["dis_varliklar_TL"] * 1_000.0 / out["usdtry"] / 1e9
    )

    if swap_duzeltme_usd is not None:
        # Swap Hariç = Net Rezerv + (II.2 + II.3). Düzeltme artık TARİHE GÖRE
        # değişen gerçek IRFCL verisi; eskiden son PDF'in tek sabiti tüm geçmişe
        # yayılıyordu (2007'den bugüne aynı offset) — o davranış kaldırıldı.
        out["swap_duzeltme_usd"] = swap_duzeltme_usd.reindex(out.index)
        out["swap_haric_net_rezerv_usd"] = (
            out["net_rezerv_usd"] + out["swap_duzeltme_usd"]
        )
        # O tarihte IRFCL gözlemi var mı (yayımlanmış) yoksa ara değer mi?
        out["swap_gozlem"] = (
            False if swap_gozlem is None
            else swap_gozlem.reindex(out.index).fillna(False)
        )

    cols = [
        "usdtry", "analitik_dis_varlik_usd", "net_rezerv_usd",
        "delta_analitik_TL"
    ]
    if "swap_haric_net_rezerv_usd" in out.columns:
        cols += ["swap_duzeltme_usd", "swap_haric_net_rezerv_usd", "swap_gozlem"]
    return out[cols].dropna(subset=["net_rezerv_usd"])


# ----------------------------------------------------------------------------
# Haftalık IRFCL PDF parser
# ----------------------------------------------------------------------------
def _parse_number(s: str) -> float:
    s = s.strip().replace(".", "").replace(",", ".")
    return float(s) if s and s != "-" else 0.0


def _satir_toplami(ln: str) -> float | None:
    """II. bölüm satırından 'Toplam' sütununu çıkarır.

    Satır düzeni: <etiket> [dipnot no] Toplam  1-aya-kadar  2-3-ay  4ay-1yıl
    Dipnot numarası bazı sürümlerde var bazılarında yok (ör. 2021 PDF'lerinde
    '3. Diğer -5.486 ...' iken 2026'da '3. Diğer 3 3.736 ...'). Ayırt etmek için
    kimlik kullanılıyor: Toplam = üç vade kovasının toplamı. Son dört sayı bu
    kimliği sağlıyorsa ilki Toplam'dır; sağlamıyorsa satırdaki ilk sayı alınır.
    """
    sayilar = [_parse_number(x) for x in re.findall(r"-?[\d\.]+", ln)]
    if not sayilar:
        return None
    if len(sayilar) >= 4:
        d = sayilar[-4:]
        if abs(d[0] - (d[1] + d[2] + d[3])) < 1.0:
            return d[0]
    return sayilar[0]


def _son_sayi(ln: str) -> float | None:
    """Bölüm I satırlarının değeri satırın SON sayısıdır.

    Bölüm II/III'ün aksine burada tek sütun var; ama bazı satırlarda etiketten
    sonra bir DİPNOT NUMARASI geliyor ("A. Resmi rezerv varlıkları 1 178.366").
    İlk sayıyı almak dipnotu değer sanmak olurdu; son sayı alınır.
    """
    sayilar = re.findall(r"-?\d[\d\.]*", ln)
    return _parse_number(sayilar[-1]) if sayilar else None


def _ons_miktari(ln: str) -> float | None:
    """'—(saf) milyon troy ons 24,953' satırı.

    Bu satırda virgül ONDALIK ayraçtır (gövdedeki '107.345'te nokta binlik
    ayraçtır), bu yüzden _parse_number() DEĞİL ayrı bir kural kullanılır.
    """
    m = re.search(r"milyon\s+troy\s+ons\s+([\d.,]+)\s*$", ln, re.IGNORECASE)
    if not m:
        return None
    return float(m.group(1).replace(".", "").replace(",", "."))


# Bölüm I.A alt kalemleri: satır başı deseni → çıktı anahtarı
_IA_KALEMLERI = [
    (r"\(1\)\s*D[öo]viz\s*varl[ıi]klar[ıi]", "I_A1_doviz_M"),
    (r"\(2\)\s*IMF\s*rezerv\s*pozisyonu", "I_A2_imf_poz_M"),
    (r"\(3\)\s*SDR", "I_A3_sdr_M"),
    (r"\(4\)\s*alt[ıi]n", "I_A4_altin_M"),
    (r"\(5\)\s*di[ğg]er\s*rezerv\s*varl[ıi]klar[ıi]", "I_A5_diger_M"),
]


def parse_weekly_pdf(pdf_bytes: bytes) -> dict:
    """RT*.pdf'inden referans tarih, brüt rezerv, I.A kırılımı, ons, II.2, II.3.

    Bölüm I.A'nın beş alt kalemi ve altın MİKTARI (milyon troy ons) da okunur;
    ons, altın fiyat etkisi hesabının birinci kademe miktar kaynağıdır
    (altin_etkisi.ons_capalari). Kimlik I.A = (1)+(2)+(3)+(4)+(5) sağlanmazsa
    ayrıştırıcı bozulmuş demektir → sessizce yanlış sayı döndürmek yerine
    görünür hata verilir.

    NOT: Tarih PDF'in İÇİNDEN okunur, dosya adından değil. TCMB sunucusu
    RT<tarih>TR.pdf yoluna hangi tarih verilirse verilsin GÜNCEL PDF'i
    döndürüyor; dosya adına güvenmek yanlış tarihli kayda yol açar.
    """
    out: dict = {}
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(p.extract_text() or "" for p in pdf.pages)
    lines = [ln.strip() for ln in text.split("\n")]

    # Referans tarih: I. bölüm başlığının hemen altındaki gg.aa.yyyy
    for ln in lines[:20]:
        m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", ln)
        if m:
            out["tarih"] = pd.Timestamp(int(m.group(3)), int(m.group(2)),
                                        int(m.group(1)))
            break

    # --- Bölüm I.A: toplam + beş alt kalem + altın miktarı --------------
    icerde = False
    for ln in lines:
        if re.match(r"A\.\s*Resmi\s*rezerv\s*varl[ıi]klar[ıi]", ln):
            deger = _son_sayi(ln)
            if deger is not None:
                out["resmi_rezerv_varliklari_M"] = deger
            icerde = True
            continue
        if icerde and re.match(r"B\.\s*Di[ğg]er\s*d[öo]viz\s*varl[ıi]klar[ıi]", ln):
            icerde = False
            continue
        if not icerde:
            continue
        ons = _ons_miktari(ln)
        if ons is not None and "mn_ons" not in out:
            out["mn_ons"] = ons
            continue
        for desen, anahtar in _IA_KALEMLERI:
            if anahtar not in out and re.match(desen, ln):
                deger = _son_sayi(ln)
                if deger is not None:
                    out[anahtar] = deger
                break

    # Kimlik denetimi: yanlış hizalanmış bir sütun sessizce geçmesin.
    #
    # DİKKAT — denetim TERSİNE kurulmuştur: eskiden "beş alt kalemin hepsi
    # bulunduysa kimliği sına" deniyordu, yani ayrıştırıcı KISMEN bozulduğunda
    # (bir satır yakalanmadığında) denetim tamamen atlanıyor ve eksik alan
    # arşive sessizce NaN olarak yazılıyordu. "Ayrıştırıcı bozulursa çıktı
    # üretme" güvencesinin devre dışı kaldığı yer tam da orasıydı. Şimdi:
    # beklenen alanlardan HERHANGİ BİRİ eksikse hata verilir.
    if "resmi_rezerv_varliklari_M" not in out:
        raise RuntimeError(
            "IRFCL PDF ayrıştırılamadı: 'A. Resmi rezerv varlıkları' satırı "
            "okunamadı. Tablo düzeni değişmiş olabilir; çıktı üretilmedi."
        )
    eksik_ia = [a for _, a in _IA_KALEMLERI if out.get(a) is None]
    if eksik_ia:
        raise RuntimeError(
            "IRFCL PDF ayrıştırılamadı: I.A alt kalemleri eksik ("
            + ", ".join(eksik_ia) + "). Kısmi ayrıştırma BAŞARI SAYILMAZ; "
            "çıktı üretilmedi."
        )
    alt = [out[a] for _, a in _IA_KALEMLERI]
    fark = abs(out["resmi_rezerv_varliklari_M"] - sum(alt))
    if fark > CAPRAZ_TOLERANS_M:
        raise RuntimeError(
            f"IRFCL PDF kimliği bozuk: I.A "
            f"{out['resmi_rezerv_varliklari_M']:,.0f} ≠ "
            f"(1)+(2)+(3)+(4)+(5) {sum(alt):,.0f} "
            f"(fark {fark:,.0f} mn USD). Ayrıştırıcı tablo düzenine "
            "uymuyor; çıktı üretilmedi."
        )
    # II. bölüm kalemleri de zorunludur: swap çapasının TAMAMI bu üç satırdan
    # gelir. Biri kaçırılırsa 0.0 varsayılanı çapayı milyarlarca dolar kaydırır
    # (II.3 tek başına ~4 mlr USD) ve bu kalıcı olarak arşive yazılır.

    for ln in lines:
        if re.match(r"\(a\)\s*A[çc][ıi]k\s*pozisyonlar\s*\(-\)", ln):
            if "II_2_acik_M" not in out:
                deger = _satir_toplami(re.sub(r"^\(a\).*?\(-\)", "", ln))
                if deger is not None:
                    out["II_2_acik_M"] = deger
            continue
        if re.match(r"\(b\)\s*Fazla\s*pozisyonlar\s*\(\+\)", ln):
            if "II_2_fazla_M" not in out:
                deger = _satir_toplami(re.sub(r"^\(b\).*?\(\+\)", "", ln))
                if deger is not None:
                    out["II_2_fazla_M"] = deger
    for ln in lines:
        if re.match(r"3\.?\s*Di[ğg]er\b", ln):
            deger = _satir_toplami(re.sub(r"^3\.?\s*Di[ğg]er", "", ln))
            if deger is not None:
                out["II_3_toplam_M"] = deger
            break

    eksik_ii = [a for a in ("II_2_acik_M", "II_2_fazla_M", "II_3_toplam_M")
                if out.get(a) is None]
    if eksik_ii:
        raise RuntimeError(
            "IRFCL PDF ayrıştırılamadı: II. bölüm kalemleri eksik ("
            + ", ".join(eksik_ii) + "). Swap çapası bu üç satırdan kurulur; "
            "eksik bacağı sıfır saymak çapayı milyarlarca dolar kaydırır. "
            "Çıktı üretilmedi."
        )
    return out


def fetch_latest_weekly_pdf() -> bytes:
    """Sitedeki EN SON haftalık IRFCL PDF'ini indirir (tek hafta; arşiv yok).

    Referans tarih dosya adından DEĞİL PDF içinden okunur → parse_weekly_pdf.
    """
    page = requests.get(WEEKLY_TABLES_PAGE, timeout=30).text
    m = re.search(r"href=\"([^\"]*RT(\d{8})TR\.pdf[^\"]*)\"", page)
    if not m:
        raise RuntimeError("RT*.pdf linki bulunamadı")
    rel = m.group(1).replace("&amp;", "&")
    url = "https://www.tcmb.gov.tr" + rel
    return requests.get(url, timeout=60).content


def gozlem_arsivine_ekle(kalem: dict) -> None:
    """Canlı PDF gözlemini irfcl_gozlem.csv'ye ekler (gerçek haftalık birikim).

    TCMB geçmiş haftaları yayında tutmadığı için her koşu, o haftanın gerçek
    II.2/II.3 değerini kalıcılaştırır; zamanla ay içi gözlem yoğunluğu artar.
    """
    if not kalem or "tarih" not in kalem:
        return
    # Zorunlu bacaklar: 0.0 VARSAYILANI YOK. Eskiden .get(..., 0.0) vardı ve
    # PDF düzeni değişip satırlardan biri yakalanmadığında çapa sessizce 0'a
    # kayıp kalıcı olarak arşive yazılıyordu (II.3 tek başına ~4 mlr USD).
    # parse_weekly_pdf artık eksik bacakta hata veriyor; burası ikinci savunma.
    eksik = [a for a in ("II_2_acik_M", "II_2_fazla_M", "II_3_toplam_M")
             if kalem.get(a) is None]
    if eksik:
        raise RuntimeError(
            f"IRFCL gözlemi arşive YAZILMADI ({kalem['tarih']:%d.%m.%Y}): "
            + ", ".join(eksik) + " okunamadı. Eksik bacağı sıfır sayan bir "
            "çapa milyarlarca dolarlık sahte swap hareketi üretir."
        )
    # Şema geriye uyumlu olarak büyüdü: eski satırlarda yeni sütunlar NaN
    # kalır (ör. mn_ons yalnız bu sürümden sonra toplanan haftalarda dolu).
    cols = ["ii2_M", "ii3_M", "resmi_rez_M", "doviz_M", "imf_poz_M", "sdr_M",
            "altin_M", "mn_ons", "kaynak"]
    if os.path.exists(GOZLEM_CSV):
        ark = pd.read_csv(GOZLEM_CSV, index_col=0, parse_dates=True)
        for c in cols:
            if c not in ark.columns:
                ark[c] = pd.NA
    else:
        ark = pd.DataFrame(columns=cols,
                           index=pd.DatetimeIndex([], name="tarih"))
    ark.loc[kalem["tarih"], cols] = [
        kalem["II_2_acik_M"] + kalem["II_2_fazla_M"],
        kalem["II_3_toplam_M"],
        kalem.get("resmi_rezerv_varliklari_M"),
        kalem.get("I_A1_doviz_M"),
        kalem.get("I_A2_imf_poz_M"),
        kalem.get("I_A3_sdr_M"),
        kalem.get("I_A4_altin_M"),
        kalem.get("mn_ons"),
        "irfcl_pdf",
    ]
    ark = ark[~ark.index.duplicated(keep="last")].sort_index()
    ark.index.name = "tarih"
    ark.to_csv(GOZLEM_CSV)


# ----------------------------------------------------------------------------
# Sessiz bayatlama denetimleri
# ----------------------------------------------------------------------------
def _son_gozlem(veri) -> pd.Timestamp | None:
    """Bir seri/indeksin son GEÇERLİ gözlem tarihi; yoksa None."""
    if veri is None:
        return None
    idx = veri.dropna().index if isinstance(veri, pd.Series) else pd.Index(veri)
    return pd.Timestamp(max(idx)) if len(idx) else None


def _isgunu_yasi(son: pd.Timestamp, ref: pd.Timestamp) -> int:
    """İki tarih arasındaki İŞ GÜNÜ sayısı (Pzt–Cum). Negatifse 0.

    Resmi tatiller bu takvimde yoktur; bu yüzden ölçü tatil haftalarında
    gerçek yaştan BÜYÜK çıkar — eşikler o payı bırakacak şekilde seçilmiştir
    (bkz. TAZELIK_TOLERANS_ISGUNU).
    """
    if son >= ref:
        return 0
    return max(len(pd.bdate_range(son, ref)) - 1, 0)


def tazelik_denetimi(veriler: dict[str, pd.Index | pd.Series],
                     bugun: pd.Timestamp | None = None) -> list[str]:
    """Her kaynağın son gözlemi GERÇEK BUGÜNE göre ne kadar eski?

    "Koştu ama ilerlemedi" sınıfı hatalar bu denetimle görünür olur: kaynak
    düştüğünde hat sessizce eski değerle devam etmez, uyarı basar.

    `bugun` YALNIZ testler için parametreliktir. Üretimde verilmez: referans
    duvar saatidir. Referansı verinin kendisinden almak (ör. `son_veri`)
    denetimi kendi kendine referanslı ve dolayısıyla işlevsiz hâle getirir.
    """
    ref = bugun if bugun is not None else pd.Timestamp.today().normalize()
    uyarilar: list[str] = []

    def _yoklama(ad: str) -> pd.Timestamp | None:
        if ad not in veriler:
            uyarilar.append(f"TAZELİK: '{ad}' kaynağı hiç yüklenmedi.")
            return None
        son = _son_gozlem(veriler.get(ad))
        if son is None:
            uyarilar.append(f"TAZELİK: '{ad}' kaynağı BOŞ döndü.")
        return son

    # --- (a) Cephe kaynakları: iş günü cinsinden, duvar saatine göre --------
    cephe_son: dict[str, pd.Timestamp] = {}
    for ad, tolerans in TAZELIK_TOLERANS_ISGUNU.items():
        son = _yoklama(ad)
        if son is None:
            continue
        cephe_son[ad] = son
        yas = _isgunu_yasi(son, ref)
        if yas > tolerans:
            uyarilar.append(
                f"TAZELİK: '{ad}' son gözlemi {son:%d.%m.%Y} ({yas} iş günü "
                f"önce, tolerans {tolerans}; bugün {ref:%d.%m.%Y}). Kaynak "
                "durmuş olabilir."
            )

    # --- (b) Düşük frekanslı kaynaklar: takvim günü ------------------------
    for ad, tolerans in TAZELIK_TOLERANS_GUN.items():
        son = _yoklama(ad)
        if son is None:
            continue
        yas = (ref - son).days
        if yas > tolerans:
            uyarilar.append(
                f"TAZELİK: '{ad}' son gözlemi {son:%d.%m.%Y} ({yas} gün önce, "
                f"tolerans {tolerans}; bugün {ref:%d.%m.%Y}). Kaynak durmuş "
                "olabilir."
            )

    # --- (c) Toptan durma: bütün cephe kaynakları aynı eski tarihte bitiyor -
    # Aynı tarihte bitmeleri normaldir (ortak iş günü takvimi); anormal olan o
    # ortak tarihin eskimesidir. Tek tek uyarı basmak bu durumda "her kaynak
    # ayrı ayrı bozuldu" gibi okunur; asıl teşhis "besleme düştü"dür.
    if len(cephe_son) >= 2 and len(set(cephe_son.values())) == 1:
        ortak = next(iter(cephe_son.values()))
        yas = _isgunu_yasi(ortak, ref)
        if yas > CEPHE_ORTAK_DURUS_ISGUNU:
            uyarilar.append(
                f"BESLEME DURMUŞ OLABİLİR: {len(cephe_son)} cephe kaynağının "
                f"HEPSİ aynı tarihte ({ortak:%d.%m.%Y}, {yas} iş günü önce) "
                f"bitiyor. Tek bir seri değil EVDS beslemesinin tamamı durmuş "
                "olabilir; sayfadaki bütün güncel sayılar o tarihe aittir."
            )

    # --- (d) Göreli yaş: kaynaklar birbirine göre nerede? ------------------
    # Duvar saati denetimini tamamlar. Cephe hâlâ tazeyken haftalık tablo
    # alışılmadık ölçüde geride kalıyorsa yayın takvimi kaymış olabilir.
    en_taze = max(cephe_son.values()) if cephe_son else None
    if en_taze is not None:
        for ad in TAZELIK_TOLERANS_GUN:
            son = _son_gozlem(veriler.get(ad))
            if son is None:
                continue
            geri = (en_taze - son).days
            if geri > TAZELIK_TOLERANS_GUN[ad] + GORELI_YAS_TOLERANS_GUN:
                uyarilar.append(
                    f"GÖRECELİ TAZELİK: '{ad}' ({son:%d.%m.%Y}) cephe "
                    f"kaynaklarından {geri} gün geride ({en_taze:%d.%m.%Y}). "
                    "Yayın takvimi kaymış ya da bu tek kaynak durmuş olabilir."
                )
    return uyarilar


def kimlik_denetimi(raw: pd.DataFrame, gunluk: pd.DataFrame,
                    rez_usd: pd.DataFrame,
                    swap_pdf: dict | None = None) -> list[str]:
    """Yapısal kimlikler + çapraz kaynak denetimleri.

    EVDS analitik bilançoyu bin TL'ye yuvarlayarak yayımladığı için kimlikler
    tam sıfır değil ±1 bin TL sapar; bu yüzden sıfır değil
    KIMLIK_TOLERANS_BIN_TL kullanılır (aksi hâlde her koşuda sahte hata).
    """
    uyarilar: list[str] = []

    def _bin_tl(ad: str, fark: pd.Series) -> None:
        f = fark.dropna().abs()
        if len(f) and f.max() > KIMLIK_TOLERANS_BIN_TL:
            uyarilar.append(
                f"KİMLİK BOZULDU: {ad} — maks sapma {f.max():,.0f} bin TL "
                f"({f.idxmax():%d.%m.%Y}). TCMB tablo yapısını değiştirmiş "
                "olabilir; seviye formülü gözden geçirilmeli."
            )

    _bin_tl("A10 = A11 + A13 + A14",
            raw["toplam_doviz_yuk_TL"] - (raw["dis_yukumlulukler_TL"]
                                          + raw["kamu_doviz_mev_TL"]
                                          + raw["bankalar_doviz_mev_gunluk_TL"]))
    # Analitik bilançonun yapısal iskeleti. Seviye formülü A02/A11/A14'e
    # dayanıyor; bu satırların tabloda yer değiştirmesi aksi hâlde sessizce
    # yanlış bir seri üretirdi. Maliyeti sıfır, erken uyarı değeri yüksek.
    _bin_tl("A01 = A02 + A03 + A08",
            raw["toplam_varlik_TL"] - (raw["dis_varliklar_TL"]
                                       + raw["ic_varliklar_TL"]
                                       + raw["degerleme_hesabi_TL"]))
    _bin_tl("A09 = A10 + A15",
            raw["toplam_yukumluluk_TL"] - (raw["toplam_doviz_yuk_TL"]
                                           + raw["mb_parasi_TL"]))
    _bin_tl("A12 = A13 + A14",
            raw["doviz_mevduati_TL"] - (raw["kamu_doviz_mev_TL"]
                                        + raw["bankalar_doviz_mev_gunluk_TL"]))
    _bin_tl("A01 = A09 (bilanço denkliği)",
            raw["toplam_varlik_TL"] - raw["toplam_yukumluluk_TL"])
    _bin_tl("N06 = N07 + N08 + N12",
            raw["net_uluslararasi_rezerv_TL"]
            - (raw["brut_doviz_rezerv_TL"] + raw["brut_doviz_yukumluluk_TL"]
               + raw["diger_net_TL"].fillna(0.0)))
    _bin_tl("N08 = N09 + N10 + N11",
            raw["brut_doviz_yukumluluk_TL"]
            - (raw["bankalar_doviz_mev_TL"] + raw["imf_TL"]
               + raw["diger_yukumluluk_TL"]))
    # Cuma günleri analitik bilançonun A14'ü ile Stand-By tablosunun N09'u
    # BİREBİR aynı olmalı. Ayrışırlarsa iki tablodan biri kaymıştır.
    cuma = raw["bankalar_doviz_mev_TL"].dropna().index
    _bin_tl("A14(Cuma) = |N09|",
            raw["bankalar_doviz_mev_gunluk_TL"].reindex(cuma)
            - raw["bankalar_doviz_mev_TL"].reindex(cuma).abs())

    # Çapraz kaynak: EVDS haftalık USD tablosu ↔ haftalık IRFCL PDF.
    # Üç kalem de sınanır. ALTIN kalemi burada özellikle önemli: brüt rezervin
    # altın/döviz kırılımında döviz bacağı ARTIK olarak belirleniyor, yani
    # C1'deki bir kayma doğrudan "döviz rezervi" satırına yazılır — ve altın
    # zaman zaman brütün dörtte üçüne çıkıyor.
    if swap_pdf and "tarih" in swap_pdf and swap_pdf["tarih"] in rez_usd.index:
        t = swap_pdf["tarih"]

        def _capraz(ad: str, evds_kolon: str, pdf_deger: float | None) -> None:
            if pdf_deger is None or evds_kolon not in rez_usd.columns:
                return
            evds = rez_usd.loc[t, evds_kolon]
            if pd.isna(evds):
                return
            fark = abs(float(evds) - float(pdf_deger))
            if fark > CAPRAZ_TOLERANS_M:
                uyarilar.append(
                    f"ÇAPRAZ KAYNAK ({t:%d.%m.%Y}): {ad} — EVDS {evds:,.0f} ile "
                    f"IRFCL PDF {pdf_deger:,.0f} arasında {fark:,.0f} mn USD "
                    f"fark (tolerans {CAPRAZ_TOLERANS_M:.0f})."
                )

        _capraz("TP.AB.TOPLAM ↔ 'A. Resmi rezerv varlıkları'", "toplam_M",
                swap_pdf.get("resmi_rezerv_varliklari_M"))
        _capraz("TP.AB.C1 ↔ I.A(4) altın", "altin_M",
                swap_pdf.get("I_A4_altin_M"))
        # C2 = döviz + IMF rezerv pozisyonu + SDR, yani PDF'in (1)+(2)+(3)'ü.
        pdf_c2 = [swap_pdf.get(a) for a in ("I_A1_doviz_M", "I_A2_imf_poz_M",
                                            "I_A3_sdr_M")]
        if all(v is not None for v in pdf_c2):
            _capraz("TP.AB.C2 ↔ I.A (1)+(2)+(3)", "doviz_M", sum(pdf_c2))

    # Piyasa tanımı ile Stand-By 2A farkı kendi yakın geçmişinin dağılımı
    # içinde mi? (Sabit bant değil — gerekçesi TANIM_FARKI_* yorumunda.)
    if {"net_dis_varlik_usd", "eski_net_rezerv_usd"} <= set(gunluk.columns):
        fark = (gunluk["net_dis_varlik_usd"]
                - gunluk["eski_net_rezerv_usd"]).dropna()
        cuma_fark = fark.reindex(cuma).dropna()
        # Sınanan son N Cuma, bandı KURAN pencerenin dışında tutulur; aksi
        # hâlde sıçrama kendi eşiğini de yukarı çeker ve dedektör körleşir.
        sinanan = cuma_fark.tail(TANIM_FARKI_SON_N)
        taban = cuma_fark.iloc[:-TANIM_FARKI_SON_N].tail(TANIM_FARKI_PENCERE)
        if len(taban) >= 12 and len(sinanan):
            medyan = float(taban.median())
            mad = float((taban - medyan).abs().median())
            yari = max(TANIM_FARKI_MAD_KAT * mad, TANIM_FARKI_TABAN)
            alt, ust = medyan - yari, medyan + yari
            disari = sinanan[(sinanan < alt) | (sinanan > ust)]
            if len(disari):
                uyarilar.append(
                    f"TANIM FARKI SIÇRAMASI: piyasa tanımı − Stand-By 2A farkı "
                    f"son {TANIM_FARKI_SON_N} Cuma'nın {len(disari)}'inde son "
                    f"{len(taban)} Cuma'nın dağılımının dışında "
                    f"(bant {alt:+.2f}…{ust:+.2f}, son değer "
                    f"{sinanan.iloc[-1]:+.2f} mlr USD). İki seriden biri kaymış "
                    "ya da TCMB bir tanımı değiştirmiş olabilir."
                )
    return uyarilar


# ----------------------------------------------------------------------------
# Hat — tek çağrıda bütün seriler
# ----------------------------------------------------------------------------
def hat_kos(start: str = "01-01-2002", end: str | None = None,
            daily_start: str = "01-01-2023",
            cipa: str = altin_etkisi.CIPA_TARIHI,
            pdf_cek: bool = True) -> dict:
    """Bütün kaynakları çeker, iki tanımı da hesaplar, uyarıları toplar.

    Dönen sözlük: raw, haftalik, gunluk, gozlem, swap_pdf, pdf_tarih,
    uyarilar (list[str]).
    """
    end = end or dt.date.today().strftime("%d-%m-%Y")
    # Piyasa tanımının çapaları günlük pencereden biraz geriye bakar; 120 gün
    # tampon en uzak çapa (aylık IRFCL) için fazlasıyla yeterli.
    piyasa_start = (pd.to_datetime(daily_start, dayfirst=True)
                    - pd.Timedelta(days=120)).strftime("%d-%m-%Y")

    raw = fetch_evds(start, end, gunluk_start=piyasa_start)
    rez_usd = fetch_grup(REZERV_USD_SERIES, piyasa_start, end)
    swap_g = fetch_grup(SWAP_SERIES, piyasa_start, end)
    fiyat_ham = fetch_grup(ALTIN_FIYAT_SERIES, piyasa_start, end)
    ons_aylik = fetch_grup(IRFCL_ONS_SERIES, piyasa_start, end,
                           ay_sonuna_kaydir=True)
    aylik_irfcl = fetch_irfcl_aylik(start, end)

    swap_pdf, pdf_tarih = None, None
    if pdf_cek:
        try:
            swap_pdf = parse_weekly_pdf(fetch_latest_weekly_pdf())
            gozlem_arsivine_ekle(swap_pdf)
            if "tarih" in swap_pdf:
                pdf_tarih = f"{swap_pdf['tarih']:%d-%m-%Y}"
        except Exception as e:               # ağ/format hatası sessiz geçmez
            swap_pdf = None
            print(f"UYARI: haftalık IRFCL PDF alınamadı ({type(e).__name__}: {e}). "
                  "Swap çapası arşivdeki son gözlemle sınırlı kalacak.")

    gozlem = (pd.read_csv(GOZLEM_CSV, index_col=0, parse_dates=True)
              if os.path.exists(GOZLEM_CSV) else None)

    # --- Günlük takvim: analitik bilanço + kurun BİRLİKTE bulunduğu iş günleri
    idx = raw.index[raw["dis_varliklar_TL"].notna() & raw["usdtry"].notna()]
    idx = idx[idx >= pd.to_datetime(daily_start, dayfirst=True)]
    ab = raw.loc[idx]

    # --- A. Piyasa tanımı
    g = pd.DataFrame(index=idx)
    g.index.name = "Tarih"
    g["usdtry"] = ab["usdtry"]
    g["net_dis_varlik_usd"] = piyasa_net_dis_varlik(ab)
    g["kamu_doviz_mev_usd"] = ab["kamu_doviz_mev_TL"] / ab["usdtry"] / 1e6
    brut = piyasa_brut(ab, rez_usd)
    g["brut_usd"] = brut["brut_usd"]

    capalar = irfcl_capalari(gozlem, aylik_irfcl)
    sw = swap_stoku(swap_g, capalar, idx)
    for c in ("swap_toplam_usd", "swap_yerli_usd", "swap_yabanci_usd",
              "swap_capa_tarih", "swap_capa_tipi"):
        g[c] = sw[c]
    g["swap_haric_usd"] = g["net_dis_varlik_usd"] - g["swap_toplam_usd"]

    # Çapa yenileme revizyonu — akımdan AYRIŞTIRILIR, silinmez.
    # Yabancı MB bacağı gözlenemediği için basamak fonksiyonudur: yalnız yeni
    # bir IRFCL gözlemi geldiğinde sıçrar. O sıçrama TCMB'nin o gün yaptığı bir
    # işlem DEĞİL, önceki günlere ait bilginin geç gelmesidir. Ayrı bir bileşen
    # olarak yazılmazsa akımda "TCMB o gün yarım milyar dolar aldı" diye
    # okunur. Etiket L, değer L→L+1 (akım konvansiyonu).
    #   Δswap_haric = Δnet_dış − Δswap_yerli − Δswap_yabancı
    # olduğundan revizyonun akıma katkısı tam olarak −Δswap_yabancı'dır.
    g["swap_capa_revizyon"] = -(g["swap_yabanci_usd"].shift(-1)
                                - g["swap_yabanci_usd"])

    # --- B. Altın arındırma sistemi (fiyat, miktar, ayrıştırma, akım)
    arind, altin_uyari = altin_etkisi.arindirma_hatti(
        index=idx,
        agort=fiyat_ham.get("altin_agort", pd.Series(dtype=float)),
        kap=fiyat_ham.get("altin_kapanis", pd.Series(dtype=float)),
        altin_deger_M=rez_usd["altin_M"],
        aylik_ons=ons_aylik.get("ons_M"),
        gozlem=gozlem,
        swap_haric=g["swap_haric_usd"],
        kamu_doviz_usd=g["kamu_doviz_mev_usd"],
        cipa=cipa,
    )
    for c in arind.columns:
        g[c] = arind[c]

    kirilim = altin_doviz_kirilimi(rez_usd, g["altin_fiyat"], g["brut_usd"], idx)
    g["altin_usd"] = kirilim["altin_usd"]
    g["doviz_usd"] = kirilim["doviz_usd"]

    # --- C. Eski tanım (Stand-By 2A) — aynen korunuyor, rolü değişti
    swap_duz_eski = swap_duzeltme_serisi(
        swap_gozlemleri(start, end, swap_pdf), raw.index)
    swap_gzm = swap_gozlem_maskesi(
        swap_gozlemleri(start, end, swap_pdf), raw.index)
    eski = calculate_daily_net_reserves(raw, swap_duz_eski, swap_gzm)
    g["eski_net_rezerv_usd"] = eski["net_rezerv_usd"].reindex(idx)
    g["eski_swap_haric_usd"] = eski["swap_haric_net_rezerv_usd"].reindex(idx)
    g["analitik_dis_varlik_usd"] = eski["analitik_dis_varlik_usd"].reindex(idx)
    g["tanim_farki"] = g["net_dis_varlik_usd"] - g["eski_net_rezerv_usd"]

    # --- D. Geriye uyumluluk. Sayfadaki MDX, grafik.py ve ozet_uret.py bu üç
    # adı kullanıyor; adlar korunur ama İÇERİKLERİ YENİ TANIMA geçer (eski
    # tanım eski_* sütunlarında durmaya devam eder).
    g["net_rezerv_usd"] = g["net_dis_varlik_usd"]
    g["swap_haric_net_rezerv_usd"] = g["swap_haric_usd"]
    # Eski konvansiyon (negatif düzeltme) korunuyor: swap_haric = net + düzeltme
    g["swap_duzeltme_usd"] = -g["swap_toplam_usd"]
    g["swap_gozlem"] = pd.Series(idx.isin(capalar.index), index=idx)

    # --- E. Haftalık çerçeve (Stand-By tablosu) + piyasa tanımı kolonları
    haftalik = calculate_weekly_net_reserves(raw, swap_duz_eski)
    for kaynak, hedef in [("brut_usd", "p_brut_usd"),
                          ("altin_usd", "p_altin_usd"),
                          ("doviz_usd", "p_doviz_usd"),
                          ("net_dis_varlik_usd", "p_net_dis_usd"),
                          ("swap_toplam_usd", "p_swap_toplam_usd"),
                          ("swap_haric_usd", "p_swap_haric_usd"),
                          ("tanim_farki", "tanim_farki")]:
        haftalik[hedef] = g[kaynak].reindex(haftalik.index)

    # --- F. Denetimler
    # DİKKAT: tazelik_denetimi'ne `bugun` GEÇİLMEZ — referans duvar saatidir.
    # Eskiden `bugun=son_veri` geçiliyordu; son_veri'yi de bu serilerin kendisi
    # belirlediği için denetim kendi kendine referanslı ve işlevsizdi.
    uyarilar = tazelik_denetimi({
        "analitik bilanço (TP.AB.A*)": raw["dis_varliklar_TL"],
        "haftalık rezerv (TP.AB.C*/TOPLAM)": rez_usd["toplam_M"],
        "Stand-By 2A (TP.AB.N*)": raw["net_uluslararasi_rezerv_TL"],
        "swap stoku (TP.SWAPTEKTAR.*)": swap_g.get("swap_alim_M"),
        "altın fiyatı (TP.ALTINPIYASA.*)": fiyat_ham.get("altin_agort"),
        "USD/TRY (TP.DK.USD.A.YTL)": raw["usdtry"],
        "haftalık IRFCL gözlemi": (capalar[capalar["tip"] == "haftalık"]["c_usd"]
                                   if len(capalar) else None),
        "aylık IRFCL (TP.DOVVARNC.*)": aylik_irfcl["toplam_M"],
    })
    uyarilar += kimlik_denetimi(raw, g, rez_usd, swap_pdf)
    uyarilar += altin_uyari

    # Kur bacağı tanısı: TL kaynak ile USD kaynak arasındaki boşluk kayıyor mu?
    # (Seviye formülüne girmez; bkz. capa_boslugu.)
    bosluk = capa_boslugu(ab, rez_usd)
    if len(bosluk) >= 12:
        taban = bosluk.iloc[:-CAPA_BOSLUK_SON_N].tail(CAPA_BOSLUK_PENCERE)
        sinanan = bosluk.tail(CAPA_BOSLUK_SON_N)
        if len(taban) >= 8:
            medyan = float(taban.median())
            mad = float((taban - medyan).abs().median())
            yari = max(CAPA_BOSLUK_MAD_KAT * mad, CAPA_BOSLUK_TABAN)
            disari = sinanan[(sinanan - medyan).abs() > yari]
            if len(disari):
                uyarilar.append(
                    f"ÇAPA BOŞLUĞU KAYDI: TOPLAM(USD) − A02/kur farkı son "
                    f"{len(disari)} Cuma'da kendi bir yıllık dağılımının "
                    f"dışında (medyan {medyan:+.2f}, bant ±{yari:.2f}, son "
                    f"{sinanan.iloc[-1]:+.2f} mlr USD). TL→USD dönüşümü "
                    "TCMB'nin değerleme kurundan ayrışıyor olabilir."
                )

    # Kur varyantı tanısı: alış yerine satış kuru kullanılsaydı seviye ne kadar
    # kayardı. Seriyi DEĞİŞTİRMEZ; kararın bedelini ölçer ve sayfaya taşır.
    kur_varyant = kur_varyanti_farki(ab)
    if len(kur_varyant):
        g["kur_varyant_fark"] = kur_varyant.reindex(idx)
        son_varyant = float(kur_varyant.iloc[-1])
        if abs(son_varyant) > KUR_VARYANT_UYARI_MLR:
            uyarilar.append(
                f"KUR VARYANTI BÜYÜDÜ: alış yerine satış kuru kullanılsaydı "
                f"net dış varlık {son_varyant:+.2f} mlr USD kayardı (eşik "
                f"{KUR_VARYANT_UYARI_MLR:.2f}). Alış/satış makası açılmış; "
                "kur seçimi artık maddi bir tanım tercihidir."
            )
    else:
        uyarilar.append(
            "KUR VARYANTI ÖLÇÜLEMEDİ: TP.DK.USD.S.YTL (satış kuru) alınamadı; "
            "alış/satış tercihinin seviyeye etkisi bu koşuda ÖLÇÜLMEDİ."
        )

    # Swap çapasının hassasiyeti — SON GÜNE DEĞİL, PENCEREYE bakılır.
    # Eskiden yalnız son günün çapa tipine bakılıyordu; son gün haftalık çapaya
    # oturduğunda uyarı susuyor ve sayfa yüksek hassasiyet iddia ediyordu, oysa
    # grafik tarihçesinin büyük bölümü düşük hassasiyetli aylık çapaya
    # dayanabiliyordu. Ölçülmüş hata bandı: haftalık çapa ±0,02 · aylık çapa
    # ±0,20 milyar USD mertebesinde.
    tipler = g["swap_capa_tipi"].dropna()
    if len(tipler):
        haftalik_oran = float((tipler == "haftalık").mean())
        if tipler.iloc[-1] == "aylık":
            uyarilar.append(
                "SWAP ÇAPASI AYLIK: son günlerin swap kalemi ay sonu IRFCL "
                "gözlemine dayanıyor; haftalık gözlem gelene kadar hassasiyet "
                "düşük (aylık çapada hata bandı ±0,20 mlr USD mertebesinde)."
            )
        if haftalik_oran < SWAP_HAFTALIK_CAPA_HEDEF:
            uyarilar.append(
                f"SWAP ÇAPA KAPSAMI DÜŞÜK: günlük serinin yalnız "
                f"%{haftalik_oran * 100:.0f}'i haftalık IRFCL çapasına "
                f"dayanıyor (hedef %{SWAP_HAFTALIK_CAPA_HEDEF * 100:.0f}); "
                "geri kalanı ay sonu çapasından taşınıyor. Haftalık arşiv "
                "doldurulduğunda bu kalemin hatası belirgin şekilde küçülür."
            )

    # Yayımlanmayan ama denetlenen tanılar — uyarilar.json'a yazılır, sayfaya
    # (ozet.json) da taşınır. "Sessizce doğru varsayma" yerine görünür ölçü.
    tipler_son = g["swap_capa_tipi"].dropna()
    tani = {
        # Laspeyres zincirleme sapması (altin_etkisi.zincirleme_tanisi)
        "zincirleme_dt": (None if arind.attrs.get("zincirleme_dt") is None
                          else round(float(arind.attrs["zincirleme_dt"]), 3)),
        # Günlük serinin ne kadarı HAFTALIK IRFCL çapasına dayanıyor
        "swap_haftalik_capa_orani": (round(float((tipler_son == "haftalık").mean()), 3)
                                     if len(tipler_son) else None),
        # Miktar (ons) çapasının son tarihi — akımın hangi günden sonrası geçici
        "son_ons_capa": (f"{pd.Timestamp(arind.attrs['son_ons_capa']):%Y-%m-%d}"
                         if arind.attrs.get("son_ons_capa") is not None else None),
        # TL↔USD çapa boşluğunun son Cuma değeri (kur bacağı tanısı)
        "capa_boslugu": (round(float(bosluk.iloc[-1]), 3) if len(bosluk) else None),
        # Alış/satış kuru tercihinin seviyeye etkisi — ÖLÇÜLEN, iddia edilen
        # değil. Sayfadaki "kapatılmamış tanım farkı" cümlesi bunu kullanır.
        "kur_varyant_fark": (round(float(kur_varyant.iloc[-1]), 3)
                             if len(kur_varyant) else None),
    }

    return {"raw": raw, "haftalik": haftalik, "gunluk": g, "gozlem": capalar,
            "swap_pdf": swap_pdf, "pdf_tarih": pdf_tarih, "rez_usd": rez_usd,
            "uyarilar": uyarilar, "tani": tani}


# ----------------------------------------------------------------------------
# Çıktılar
# ----------------------------------------------------------------------------
def latest_summary(weekly: pd.DataFrame, swap_pdf: dict | None,
                   pdf_date: str | None) -> str:
    last = weekly.iloc[-1]
    lines = [
        f"=== TCMB Net Uluslararası Rezerv  ({last.name:%d-%m-%Y}, Cuma) ===",
        f"  Brüt Döviz Rezervi    : {last['brut_rezerv_usd']:>8.2f} milyar USD",
        f"  Brüt Yükümlülükler    : {last['brut_yukumluluk_usd']:>8.2f} milyar USD",
        f"     - Bankalar Döviz   : {last['bankalar_doviz_mev_usd']:>8.2f} milyar USD",
        f"     - IMF              : {last['imf_usd']:>8.2f} milyar USD",
        f"     - Diğer            : {last['diger_yukumluluk_usd']:>8.2f} milyar USD",
        f"  Net Rezerv (TP.AB.N06): {last['net_rezerv_usd']:>8.2f} milyar USD",
        f"  USD/TRY (alış)        : {last['usdtry']:>8.4f}",
    ]
    if swap_pdf and "resmi_rezerv_varliklari_M" in swap_pdf:
        rrv = swap_pdf["resmi_rezerv_varliklari_M"] / 1000.0
        lines.insert(
            1,
            f"  I.A Resmi Rez. Varl.  : {rrv:>8.2f} milyar USD  (haftalık IRFCL)",
        )
    if swap_pdf and all(a in swap_pdf for a in
                        ("II_2_acik_M", "II_2_fazla_M", "II_3_toplam_M")):
        # Yalnız ÜÇ bacak da varsa basılır; eksik bacağı sıfır sayıp "swap
        # hariç" diye bir sayı göstermek, yanlış bir rakamı doğru gibi sunardı.
        ii2 = (swap_pdf["II_2_acik_M"] + swap_pdf["II_2_fazla_M"]) / 1000.0
        ii3 = swap_pdf["II_3_toplam_M"] / 1000.0
        swap_haric = last["net_rezerv_usd"] + ii2 + ii3
        lines += [
            "",
            f"=== Haftalık IRFCL Tablosu  ({pdf_date}) ===",
            f"  II.2 Açık Pozisyon (-)  : {ii2:>8.2f} milyar USD",
            f"  II.3 Diğer (net)        : {ii3:>8.2f} milyar USD",
            f"  Net Swap Pozisyonu     : {ii2 + ii3:>8.2f} milyar USD",
            "",
            f"  Swap Hariç Net Rezerv  : {swap_haric:>8.2f} milyar USD",
        ]
    return "\n".join(lines)


def gunluk_dogrulama_raporu(raw: pd.DataFrame) -> str:
    """Günlük tahminin çekirdeği olan Δproxy'nin Cuma→Cuma geri-testi.

    Her resmi Cuma F için: hata = [N06(F) − N06(F−7)] − Δproxy(F−7→F), USD'ye
    F kuru ile çevrilir. Aday proxy'ler yan yana basılır ki seçim gerekçesi
    (A02−A14) her koşuda veriyle yeniden görülsün. Elle ayar yok: yalnız EVDS.
    """
    adaylar = {
        "A02-A14 (kullanılan)": raw["dis_varliklar_TL"]
                                - raw["bankalar_doviz_mev_gunluk_TL"],
        "A02      (yalnız dış varlık)": raw["dis_varliklar_TL"],
        "A02-A17 (eski; A17=emisyon)": raw["dis_varliklar_TL"] - raw["emisyon_TL"],
    }
    cuma = raw[raw["net_uluslararasi_rezerv_TL"].notna()]
    usd = raw["usdtry"].ffill().reindex(cuma.index)
    dN = cuma["net_uluslararasi_rezerv_TL"].diff()
    satirlar = ["=== Günlük tahmin geri-testi (Cuma→Cuma, milyar USD) ==="]
    for ad, p in adaylar.items():
        dP = p.ffill().reindex(cuma.index).diff()
        e = ((dN - dP) * 1000.0 / usd / 1e9).dropna()
        e26 = e[e.index.year == e.index.year.max()]
        satirlar.append(
            f"  {ad:<30} n={len(e):>3}  RMSE {float((e**2).mean())**0.5:5.2f}  "
            f"MAE {e.abs().mean():5.2f}  maks {e.abs().max():5.2f}   | "
            f"{e.index.year.max()}: RMSE {float((e26**2).mean())**0.5:5.2f}  "
            f"maks {e26.abs().max():5.2f}"
        )
    return "\n".join(satirlar)


def swap_dogrulama_raporu(gozlem: pd.DataFrame) -> str:
    """Ay içi haftalık gözlemlerle ara değer / basamak hatasını ölçer.

    Test kümesi: kaynak="irfcl_pdf" olan ve ay sonuna denk GELMEYEN gerçek
    haftalık gözlemler. Bu noktalar yalnızca EVDS aylık (ay sonu) gözlemlerden
    tahmin edilir; gerçek değerle farkı iki yöntem için raporlanır.
    """
    aylik = gozlem[gozlem["kaynak"] == "evds_aylik"]["swap_duzeltme_usd"]
    test = gozlem[gozlem["kaynak"] == "irfcl_pdf"]["swap_duzeltme_usd"]
    test = test[[t != t + pd.offsets.MonthEnd(0) for t in test.index]]
    test = test[(test.index >= aylik.index.min()) & (test.index <= aylik.index.max())]
    if test.empty:
        return "\n=== Swap düzeltmesi doğrulama ===\n  (ay içi gözlem yok)"

    birlesik = aylik.reindex(aylik.index.union(test.index)).sort_index()
    ara = birlesik.interpolate(method="time", limit_area="inside")
    basamak = birlesik.ffill()

    lines = ["", "=== Swap düzeltmesi doğrulama (ay içi gerçek IRFCL haftaları) ===",
             "Tarih      |  gerçek |  aradeğer(hata) | basamak(hata)"]
    h_ara, h_bas = [], []
    for t, v in test.items():
        e1, e2 = ara.loc[t] - v, basamak.loc[t] - v
        h_ara.append(abs(e1))
        h_bas.append(abs(e2))
        lines.append(f"{t:%Y-%m-%d} | {v:>7.2f} | {ara.loc[t]:>7.2f}"
                     f" ({e1:+5.2f}) | {basamak.loc[t]:>7.2f} ({e2:+5.2f})")
    n = len(h_ara)
    lines += [
        f"  n = {n} hafta | ortalama |hata|: "
        f"ara değer {sum(h_ara) / n:.2f} mlr USD, "
        f"basamak {sum(h_bas) / n:.2f} mlr USD",
    ]
    return "\n".join(lines)


def piyasa_ozeti(gunluk: pd.DataFrame, uyarilar: list[str]) -> str:
    """Piyasa tanımının son gününü ve akım serisinin son gününü basar."""
    gecerli = gunluk.dropna(subset=["swap_haric_usd"])
    if gecerli.empty:
        return "=== Piyasa tanımı === (seri boş — swap çapası bulunamadı)"
    s = gecerli.iloc[-1]
    capa = s.get("swap_capa_tarih")
    capa_s = f"{pd.Timestamp(capa):%d.%m.%Y}" if pd.notna(capa) else "-"
    satirlar = [
        f"=== Piyasa tanımı — rezerv ({s.name:%d.%m.%Y}) ===",
        f"  Brüt rezerv           : {s['brut_usd']:>8.2f} milyar USD",
        f"     - Altın             : {s['altin_usd']:>8.2f} milyar USD"
        f"   (fiyat {s['altin_fiyat']:,.0f} USD/ons, "
        f"{s['altin_fiyat_kaynak']})",
        f"     - Döviz + IMF + SDR : {s['doviz_usd']:>8.2f} milyar USD",
        f"  Net dış varlık        : {s['net_dis_varlik_usd']:>8.2f} milyar USD",
        f"  Toplam swap stoku     : {s['swap_toplam_usd']:>8.2f} milyar USD"
        f"   (çapa {capa_s}, {s['swap_capa_tipi']})",
        f"     - Yerli banka       : {s['swap_yerli_usd']:>8.2f} milyar USD",
        f"     - Yabancı MB        : {s['swap_yabanci_usd']:>8.2f} milyar USD",
        f"  Swap hariç net rezerv : {s['swap_haric_usd']:>8.2f} milyar USD",
        f"  Stand-By 2A (eski)    : {s['eski_net_rezerv_usd']:>8.2f} milyar USD"
        f"   (tanım farkı {s['tanim_farki']:+.2f})",
    ]
    akim = gunluk.dropna(subset=["net_doviz_alimi"])
    if len(akim):
        a = akim.iloc[-1]
        satirlar += [
            "",
            f"=== Altın fiyat etkisinden arındırılmış akım "
            f"(etiket {a.name:%d.%m.%Y} → bir sonraki iş günü) ===",
            f"  Altın fiyat etkisi     : {a['altin_fiyat_etkisi']:+8.2f} milyar USD",
            f"  Net döviz alımı/satımı : {a['net_doviz_alimi']:+8.2f} milyar USD",
            f"     (altın tamamen hariç: {a['net_doviz_alimi_altin_haric']:+.2f})",
            f"  Çıpadan birikimli      : "
            f"{a['net_doviz_alimi_birikimli']:+8.2f} milyar USD",
            f"  Altın miktarı          : {a['ons']:>8.2f} milyon ons "
            f"({a['ons_kaynak']})",
        ]
    if uyarilar:
        satirlar += ["", f"=== UYARILAR ({len(uyarilar)}) ==="]
        satirlar += [f"  ! {u}" for u in uyarilar]
    else:
        satirlar += ["", "=== Denetim: uyarı yok ==="]
    return "\n".join(satirlar)


# Yerel doğrulama dosyası. ÜRETİM AKIŞI BU DOSYAYA BAĞIMLI DEĞİLDİR: yoksa
# --kontrol-dogrula nazikçe atlar, diğer her şey normal koşar. İçindeki hiçbir
# sayı formüle girmez; yalnız hata ölçümü için okunur.
KONTROL_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "kontrol_seti.csv")

# Kontrol dosyasındaki sütun → bizim ürettiğimiz sütun.
#
# SEVİYE kalemleri her zaman kıyaslanır. AKIM kalemleri (net_alim_altin_haric,
# altin_fiyat_etkisi) yalnız dosyada varsa kıyaslanır — hattın en yeni ve en
# iddialı çıktısı odur, ama seviye kalemlerinden bağımsız bir doğrulama ister.
# Dosyada yoksa rapor bunu AÇIKÇA yazar; sessizce "her şey doğrulandı" demez.
KONTROL_ESLEME = {
    "brut": "brut_usd",
    "altin": "altin_usd",
    "doviz": "doviz_usd",
    "swap_toplam": "swap_toplam_usd",
    "yerli_banka": "swap_yerli_usd",
    "yabanci_mb": "swap_yabanci_usd",
    "swap_haric": "swap_haric_usd",
}

# Akım kalemleri AYRI tutulur. Bizim akım serimiz L ile etiketlenir ve
# L → L+1 hareketini taşır; referans tablonun hangi ucu etiketlediği ise BİZE
# BAĞLI DEĞİL, ölçülecek bir şeydir. Bu yüzden kıyas tek bir hizada değil,
# −1 / 0 / +1 iş günü kaydırmalarının HEPSİNDE yapılır ve rapor üçünü de
# basar: doğru hiza, hatanın bir mertebe çöktüğü hizadır (seviye kalemlerinde
# aynı tarama shift=0'ı seçiyor ve komşuları yüz kat kötü çıkıyor). Hizayı
# varsaymak, yanlış hizada ölçülmüş bir hatayı "yöntem hatası" sanmaya yol
# açardı.
#
# net_alim_birikimli DİKKAT: referansın birikimli satırı YAYIMLANDIĞI ANIN
# değeridir (vintage). Günlük akımlar sonradan revize olduğu için bu sütun,
# bizim bugünkü (revize) serimize karşı yapısal olarak bir revizyon farkı
# taşır; kıyas o yüzden yöntem hatası değil, revizyon büyüklüğü ölçer.
KONTROL_AKIM_ESLEME = {
    "net_alim_altin_haric": "net_doviz_alimi",
    "net_alim_birikimli": "net_doviz_alimi_birikimli",
    "altin_fiyat_etkisi_birikimli": "altin_fiyat_etkisi_birikimli",
}

# Akım hizası taraması: bizim seriyi kaç İŞ GÜNÜ kaydırıp kıyaslayalım.
KONTROL_AKIM_KAYMALARI = (-1, 0, 1)


def kontrol_dogrulama_raporu(gunluk: pd.DataFrame,
                             yol: str = KONTROL_CSV) -> str:
    """Yerel doğrulama dosyasıyla gün gün ve kalem kalem hata tablosu.

    Dosya yoksa görünür ama zararsız bir not basılır; hat durmaz.
    """
    if not os.path.exists(yol):
        return ("\n=== Kontrol doğrulaması ===\n"
                f"  {os.path.basename(yol)} bulunamadı — atlandı. "
                "(Üretim akışı bu dosyaya bağımlı değildir.)")
    k = pd.read_csv(yol, parse_dates=["tarih"]).set_index("tarih").sort_index()
    var = [c for c in KONTROL_ESLEME if c in k.columns
           and KONTROL_ESLEME[c] in gunluk.columns]
    if not var:
        return "\n=== Kontrol doğrulaması ===\n  Karşılaştırılabilir sütun yok."

    ortak = k.index.intersection(gunluk.index)
    if len(ortak) == 0:
        return ("\n=== Kontrol doğrulaması ===\n"
                "  Ortak tarih yok (günlük seri penceresi dışında).")

    satirlar = ["", "=== Kontrol doğrulaması — gün gün (milyar USD) ===",
                "Tarih      | çapa    | " +
                " | ".join(f"{c:>12}" for c in var)]
    satirlar.append("-" * (22 + 15 * len(var)))
    for t in ortak:
        tip = gunluk.loc[t, "swap_capa_tipi"]
        hucre = []
        for c in var:
            e = gunluk.loc[t, KONTROL_ESLEME[c]] - k.loc[t, c]
            hucre.append("           -" if pd.isna(e) else f"{e:>+12.3f}")
        satirlar.append(f"{t:%Y-%m-%d} | {str(tip)[:7]:<7} | "
                        + " | ".join(hucre))

    satirlar += ["", "=== Kalem özeti ===",
                 f"{'kalem':<14}{'n':>4}{'ort':>9}{'|ort|':>9}{'std':>9}{'maks':>9}"]
    for c in var:
        e = (gunluk[KONTROL_ESLEME[c]].reindex(ortak) - k[c].reindex(ortak)).dropna()
        if e.empty:
            continue
        satirlar.append(f"{c:<14}{len(e):>4}{e.mean():>+9.3f}"
                        f"{e.abs().mean():>9.3f}{e.std():>9.3f}"
                        f"{e.abs().max():>9.3f}")
    # Net dış varlık kontrol setinde doğrudan yok; swap hariç + swap toplamı.
    if {"swap_haric", "swap_toplam"} <= set(k.columns):
        hedef = (k["swap_haric"] + k["swap_toplam"]).reindex(ortak)
        e = (gunluk["net_dis_varlik_usd"].reindex(ortak) - hedef).dropna()
        if len(e):
            satirlar.append(f"{'net_dis_varlik':<14}{len(e):>4}{e.mean():>+9.3f}"
                            f"{e.abs().mean():>9.3f}{e.std():>9.3f}"
                            f"{e.abs().max():>9.3f}")

    # Swap kaleminin hassasiyeti çapa tipine göre belirgin ayrışır; ayrı bas.
    satirlar += ["", "=== Swap çapası tipine göre (swap_haric) ==="]
    for tip in ("haftalık", "aylık"):
        alt = gunluk.loc[ortak]
        alt = alt[alt["swap_capa_tipi"] == tip]
        if alt.empty or "swap_haric" not in k.columns:
            continue
        e = (alt["swap_haric_usd"] - k["swap_haric"].reindex(alt.index)).dropna()
        if len(e):
            satirlar.append(f"  çapa={tip:<9} n={len(e):>3}  ort={e.mean():+7.3f}"
                            f"  |ort|={e.abs().mean():6.3f}"
                            f"  maks={e.abs().max():6.3f}")

    # --- AKIM doğrulaması (varsa) ------------------------------------------
    # Hattın en yeni ve en iddialı çıktısı budur (kullanıcının asıl istediği
    # "altın fiyat etkisinden arındırma"). Etiket hizası VARSAYILMAZ, ölçülür:
    # bkz. KONTROL_AKIM_ESLEME yorumu.
    satirlar += ["", "=== Akım doğrulaması (etiket hizası taranıyor) ==="]
    akim_var = [c for c in KONTROL_AKIM_ESLEME if c in k.columns
                and KONTROL_AKIM_ESLEME[c] in gunluk.columns
                and k[c].notna().any()]
    if not akim_var:
        satirlar.append(
            "  Kontrol dosyasında akım sütunu YOK ("
            + " / ".join(KONTROL_AKIM_ESLEME) + "). Hattın en yeni çıktısı "
            "olan 'altın fiyat etkisinden arındırılmış net döviz alımı' "
            "bağımsız bir referansa karşı SINANMAMIŞ durumdadır."
        )
    else:
        satirlar.append(f"  {'kalem':<30}{'kayma':>6}{'n':>5}{'ort':>9}"
                        f"{'|ort|':>9}{'maks':>9}")
        for c in akim_var:
            bizim = gunluk[KONTROL_AKIM_ESLEME[c]].dropna()
            en_iyi, en_iyi_mae = None, None
            olcum: list[tuple[int, pd.Series]] = []
            for kayma in KONTROL_AKIM_KAYMALARI:
                # Kaydırma İŞ GÜNÜ cinsinden: seride hafta sonu ve resmi tatil
                # yok, takvim günü kaydırmak tatillerde hizayı bozardı.
                konum = gunluk.index.get_indexer(bizim.index) + kayma
                gecerli = (konum >= 0) & (konum < len(gunluk.index))
                hizali = pd.Series(bizim.values[gecerli],
                                   index=gunluk.index[konum[gecerli]]).sort_index()
                e = (hizali.reindex(k.index) - k[c]).dropna()
                if e.empty:
                    continue
                olcum.append((kayma, e))
                if en_iyi_mae is None or e.abs().mean() < en_iyi_mae:
                    en_iyi, en_iyi_mae = kayma, e.abs().mean()
            for kayma, e in olcum:
                isaret = " ←" if kayma == en_iyi else ""
                satirlar.append(
                    f"  {c:<30}{kayma:>+6}{len(e):>5}{e.mean():>+9.3f}"
                    f"{e.abs().mean():>9.3f}{e.abs().max():>9.3f}{isaret}")
        satirlar.append(
            "  '←' hatanın en küçük olduğu hiza. Doğru hizada hata bir mertebe "
            "çökmeli;")
        satirlar.append(
            "  üç kayma birbirine yakınsa hiza ölçümü AYIRT EDİCİ DEĞİLDİR.")
        if "net_alim_birikimli" in akim_var:
            satirlar.append(
                "  NOT: net_alim_birikimli referansı YAYIM ANININ değeridir; "
                "farkın bir kısmı")
            satirlar.append(
                "  yöntem değil REVİZYON (günlük akımlar sonradan tazeleniyor).")
    satirlar += [
        "",
        "  NOT: doğrulama penceresi kontrol dosyasının kapsadığı aralıktır. "
        "Oynaklığın",
        "  yüksek olduğu rejimlerde (ör. Mart 2026) hata bandı ölçülmemiştir.",
    ]
    return "\n".join(satirlar)


def daily_summary(daily: pd.DataFrame, n: int = 30) -> str:
    """Son N iş günü — piyasa tanımı, kırılımıyla ve akımıyla birlikte.

    Son sütun akım serisidir ve L → L+1 değişimini taşır; bu yüzden son
    satırda BOŞTUR (bir sonraki iş gününün verisi henüz yok). Bu bir eksik
    değil, etiket konvansiyonunun sonucudur.
    """
    show = daily.tail(n).copy()
    cols = ["usdtry", "brut_usd", "altin_usd", "doviz_usd",
            "net_rezerv_usd", "swap_haric_net_rezerv_usd"]
    headers = ["USD/TRY", "Brüt", "Altın", "Döviz", "Net dış varlık",
               "Swap hariç"]
    cols = [c for c in cols if c in show.columns]
    headers = headers[:len(cols)]

    lines = ["", f"=== Günlük seri — piyasa tanımı (son {len(show)} iş günü, "
                 "milyar USD) ==="]
    lines.append("Tarih      | " + " | ".join(f"{h:>14}" for h in headers)
                 + " |  Δ swap hariç |  net döviz alımı")
    lines.append("-" * (13 + 17 * len(headers) + 34))

    onceki = None
    for d, row in show.iterrows():
        hucre = [f"{row[c]:>14.2f}" for c in cols]
        sh = row.get("swap_haric_net_rezerv_usd")
        delta = "             -" if (onceki is None or pd.isna(sh)
                                     or pd.isna(onceki)) else f"{sh - onceki:>+14.2f}"
        akim = row.get("net_doviz_alimi")
        akim_s = "                -" if pd.isna(akim) else f"{akim:>+17.2f}"
        lines.append(f"{d:%Y-%m-%d} | " + " | ".join(hucre)
                     + f" | {delta} | {akim_s}")
        onceki = sh
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # NOT: --start haftalık Stand-By serisinin derinliğidir. Analitik bilanço
    # kalemleri --daily-start penceresinden çekilir (EVDS'e gereksiz yüzlerce
    # istek atılmasın diye); ikisi bilerek ayrı.
    ap.add_argument("--start", default="01-01-2002")
    ap.add_argument("--end", default=dt.date.today().strftime("%d-%m-%Y"))
    ap.add_argument("--daily-start", default="01-01-2023",
                    help="günlük seri başlangıcı (gg-aa-yyyy); haftalık seriyi "
                         "kırpmaz")
    ap.add_argument("--capa", "--cipa", dest="capa",
                    default=altin_etkisi.CIPA_TARIHI,
                    help=f"birikimli net döviz alımı çıpası, YYYY-AA-GG "
                         f"(varsayılan {altin_etkisi.CIPA_TARIHI})")
    # CSV yolları VARSAYILAN olarak proje klasöründeki dosyalar. Eskiden None'dı ve
    # yalnız açıkça verilirse yazılıyordu; cron/bat/guncelle.py hepsi parametresiz
    # çağırdığı için hat hesabı yapıp DOSYAYA YAZMIYORDU — grafik.py ve ozet_uret.py
    # eski CSV'yi okuyor, sayfa 3 hafta 03.08'de kaldı ve "✓" görünüyordu.
    # Yazmamak istenirse --no-csv.
    _burasi = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--csv", default=os.path.join(_burasi, "haftalik_rezerv.csv"),
                    help="haftalık seri CSV yolu (varsayılan: proje klasörü)")
    ap.add_argument("--daily-csv", default=os.path.join(_burasi, "gunluk.csv"),
                    help="günlük seri CSV yolu (varsayılan: proje klasörü)")
    ap.add_argument("--no-csv", action="store_true",
                    help="CSV yazma (yalnız ekrana bas)")
    ap.add_argument("--daily-window", type=int, default=20,
                    help="özette gösterilecek son iş günü sayısı")
    ap.add_argument("--validate", action="store_true",
                    help="24.04.2026 referans değerleriyle karşılaştır")
    ap.add_argument("--no-pdf", action="store_true",
                    help="Haftalık PDF'i indirme (sadece EVDS)")
    ap.add_argument("--daily-only", action="store_true",
                    help="haftalık özet basma, sadece günlük tablo")
    ap.add_argument("--swap-dogrula", action="store_true",
                    help="ay içi gerçek IRFCL gözlemleriyle ara değer/basamak "
                         "yönteminin hatasını ölç (eski seri)")
    ap.add_argument("--gunluk-dogrula", action="store_true",
                    help="eski günlük tahmin proxy'sinin (A02-A14) Cuma→Cuma "
                         "geri-testi")
    ap.add_argument("--kontrol-dogrula", action="store_true",
                    help="varsa yerel kontrol dosyasıyla gün gün hata tablosu "
                         "bas (dosya yoksa atlanır; üretim buna bağımlı değil)")
    ap.add_argument("--kontrol-csv", default=KONTROL_CSV,
                    help="yerel doğrulama dosyasının yolu. Seviye sütunları: "
                         "tarih + brut/altin/doviz/swap_toplam/yerli_banka/"
                         "yabanci_mb/swap_haric. Akım sütunları (isteğe bağlı, "
                         "varsa ayrıca ölçülür): net_alim_altin_haric, "
                         "altin_fiyat_etkisi. Hepsi milyar USD.")
    args = ap.parse_args()

    h = hat_kos(args.start, args.end, daily_start=args.daily_start,
                cipa=args.capa, pdf_cek=not args.no_pdf)
    raw, weekly, daily = h["raw"], h["haftalik"], h["gunluk"]

    if not args.daily_only:
        print(latest_summary(weekly, h["swap_pdf"], h["pdf_tarih"]))
        print()
    print(piyasa_ozeti(daily, h["uyarilar"]))
    print(daily_summary(daily, n=args.daily_window))

    if args.swap_dogrula:
        print(swap_dogrulama_raporu(
            swap_gozlemleri(args.start, args.end, h["swap_pdf"])))
    if args.gunluk_dogrula:
        print(gunluk_dogrulama_raporu(raw))
    if args.kontrol_dogrula:
        print(kontrol_dogrulama_raporu(daily, args.kontrol_csv))

    if args.validate:
        ref = {"brut": 171.1, "net": 54.2, "swap_haric": 36.4}
        if "2026-04-24" in weekly.index.strftime("%Y-%m-%d").to_list():
            row = weekly.loc["2026-04-24"]
            print("\n=== Doğrulama (24.04.2026, Stand-By 2A tanımı) ===")
            print(f"  Brüt    -> hesap: {row['brut_rezerv_usd']:.2f} | "
                  f"resmi: {ref['brut']}")
            print(f"  Net     -> hesap: {row['net_rezerv_usd']:.2f} | "
                  f"resmi: {ref['net']}")
            # Swap hariç, 24.04.2026'ya AİT swap düzeltmesiyle hesaplanıyor
            # (eskiden son PDF'in sabiti kullanılıyordu — tarih uyumsuzdu).
            if "swap_haric_net_rezerv_usd" in weekly.columns:
                sh = row["swap_haric_net_rezerv_usd"]
                print(f"  S.Har. -> hesap: {sh:.2f} | resmi: {ref['swap_haric']}"
                      f"  (swap düzeltmesi: {row['swap_duzeltme_usd']:+.2f})")
            print("  NOT: bu üç referans ESKİ (Stand-By 2A) tanıma aittir; "
                  "piyasa tanımı bunlardan ~2,2 mlr USD yukarıdadır.")

    if not args.no_csv:
        weekly.to_csv(args.csv)
        daily.to_csv(args.daily_csv)
        # Uyarılar dosyaya da yazılır: ozet_uret.py çevrimdışı koştuğu için
        # denetim sonucunu buradan okur ve sayfaya taşır. Uyarı yoksa dosya
        # BOŞ LİSTE ile üzerine yazılır — eski uyarı asılı kalmasın.
        with open(os.path.join(os.path.dirname(args.daily_csv) or ".",
                               "uyarilar.json"), "w", encoding="utf-8") as f:
            json.dump({"tarih": f"{daily.index[-1]:%Y-%m-%d}",
                       # Denetimin KOŞTUĞU an (veri tarihi değil): ozet_uret.py
                       # bu iki tarihi karşılaştırıp denetim çıktısının kendisi
                       # bayatladıysa sayfada "0 uyarı" yazmıyor.
                       "kosum": f"{dt.date.today():%Y-%m-%d}",
                       "uyarilar": h["uyarilar"],
                       "tani": h.get("tani", {})}, f, ensure_ascii=False,
                      indent=1)
        print(f"\nCSV kaydedildi: {args.csv}")
        print(f"Günlük CSV kaydedildi: {args.daily_csv}  (son: {daily.index[-1]:%d.%m.%Y})")

    # Uyarı varsa çıkış kodunu DEĞİŞTİRMİYORUZ (hat yeşil bitmeli, veri yazıldı)
    # ama sona bir kez daha basıyoruz ki cron çıktısının kuyruğunda görünsün.
    if h["uyarilar"]:
        print(f"\n[{len(h['uyarilar'])} uyarı — ayrıntı yukarıda]")


if __name__ == "__main__":
    main()
