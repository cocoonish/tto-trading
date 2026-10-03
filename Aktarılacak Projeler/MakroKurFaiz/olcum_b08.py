#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 8 (Dış ticaret akımı ve cari denge) ölçüm katmanı.

Pratikler
  p8a   Türkiye sektörel dengeleri, çeyreklik 2006Ç4–2026Ç2: kamu (MERKEZİ
        YÖNETİM bütçesi, 12 aylık akım / GSYH; genel yönetim DEĞİL), dış
        denge (12 aylık cari denge / GSYH), özel kesim = dış − kamu (ARTIK).
        İkiz açık katsayısı (Δ4 dış denge ~ Δ4 kamu). OVP 2024–2025 kontrol
        noktası (tasarruf–yatırım farkı, cari/GSYH, genel devlet dengesi).
  p8b   J-eğrisi: REDK'nin (ARTIŞ = TL'nin REEL DEĞER KAZANCI) 0…24 ay
        gecikmeli 12 aylık log değişimine, altın ve enerji hariç mal
        dengesinin (mal dengesi − net parasal olmayan altın − net enerji)
        12 aylık toplamındaki 12 aylık değişimin (GSYH'ye oranla) tepkisi;
        gecikme başına ayrı Newey–West eğimi, gelir (GSYH büyümesi) kontrollü
        profil, yıllık kısıtsız dağıtılmış gecikme. Fiyat/miktar ayrımı
        bulut arşivindeki dış ticaret birim değer ve miktar endekslerinden.
  p8c   REDK sapması (log REDK'nin GENİŞLEYEN pencereli ortalamasından —
        ileriye bakmaz) → sonraki 12 ayda cari/GSYH ve çekirdek cari/GSYH
        değişimi; Newey–West (gecikme 24) ve örneklem dışı kıyas.
  p8d   Kırılgan Beşli vaka tablosu (TEST DEĞİL): 22.05.2013 → 30.08.2013
        BRL, INR, ZAR, TRY, IDR ve kontrol MXN; 2012 cari/GSYH (Dünya Bankası).
  vaka_brexit_2016  DM vakası (TEST DEĞİL; 8.3): 23.06.2016 AB referandumu.
        Pencere 23.06 kapanışı → 24.06 kapanışı (ilk tepki günü) ve alt
        pencere 23.06 → 04.08.2016 (BoE'nin referandum sonrası paketi):
        gilt 2/10/30 yıllık (bp), sterlin (CNBC New York 17:00, log %), faiz ×
        para kadranı; sterlinin avroya ve öbür beş G10 parasına karşı değişimi,
        Bund ve ABD 10 yıllık, ECB sabitlemesiyle sağlamlık, 2015 cari/GSYH
        (Dünya Bankası). Olay penceresinin kendisi Bölüm 5'in İngiltere olay
        satırıdır (`olcum_b05._olay_igb`): aynı ölçü iki modülde iki kodla
        kurulmaz.
  sekil_13  üç denge (çeyreklik)
  sekil_14  J-eğrisi gecikme profili
  sekil_15  REDK sapması × sonraki 12 aylık cari denge değişimi (aylık)

YÖN. s = log(USD/yerel): artış yerel paranın DEĞER KAYBI. TCMB REDK'nin
ARTIŞI TL'nin REEL DEĞER KAZANCI; Marshall–Lerner'in uzun dönem işareti bu
yüzden EKSİdir (reel değer kazancı mal dengesini bozar). Dengeler GSYH'nin
yüzdesidir; oranın farkı PUANDIR.

DÖNÜŞÜM KURU (karar 09.09.2026). Dolar cinsi resmî tablolar TCMB gösterge
kuruyla çevrilir (ortak_olc.usdtry_tcmb; Yahoo değil). Her ayın akımı O AYIN
ortalama kuruyla çevrilir; çeyreklik TL GSYH aylara eşit bölünür (üçte bir)
ve o ayın kuruyla dolara çevrilir. Seçim: sektörel denge TL cinsinden
kurulur (cari dengenin her ayı kendi ayının kuruyla TL'ye, 12 aylık toplam /
4 çeyreklik TL GSYH), çünkü bütçe dengesi de TL akımının TL GSYH'ye oranıdır
ve özdeşlik (S − I) TL milli hesaplarda kurulur. Resmî biçim (dolar cari /
dolar GSYH) yanında durur; fark kur hızla değer kaybederken büyür.

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. İKİ DÖNÜŞÜM KURALI HIZLI DEĞER KAYBINDA BİR PUANA YAKIN AYRIŞIR:
     2018Ç4'te TL oranı −%0,86, resmî dolar oranı −%1,84; 2022Ç2'de TL
     −%3,89, dolar −%2,88 (ortalama mutlak fark 0,13 puan). Sebep aritmetik:
     2018'in açık ayları düşük kurda, fazla ayları (Ağustos–Aralık) yüksek
     kurda; TL toplamı yüksek kurlu aylara daha çok ağırlık verir. Hangisinin "doğru"
     olduğu soruya bağlıdır; özdeşlik için TL, uluslararası kıyas için dolar.
  2. PAYDA ETKİSİ: dolar GSYH'si reel değer kaybıyla mekanik olarak küçülür,
     yani açık/GSYH oranı payı hiç değişmeden büyür (Δ(B/G) ≈ ΔB/G −
     (B/G)·Δln G). Çekirdek mal dengesi sıfıra yakın olduğu için p8b'de etki
     küçük; cari açıkta (−%3 civarı) %20'lik bir reel değer kaybı oranı tek
     başına ≈0,6 puan kötüleştirir. Ana ölçü bu yüzden SABİT PAYDALIDIR:
     dengedeki dolar değişimi, değişimin başındaki 12 aylık dolar GSYH'ye
     bölünür; oranın kendi değişimi sağlamlık olarak yanında.
     SABİT PAYDA DA MEKANİK BİR TERİM TAŞIR (denetimde ölçüldü): iki ölçünün
     farkı birebir (B/G)_son · (G_son/G_baş − 1), yani oran × dolar GSYH
     büyümesidir (özdeşlik 1e−15'te kapanıyor). Açık sürerken dolar GSYH'si
     büyüdükçe sabit paydalı ölçü kendiliğinden kötüleşir: p8c'nin cari
     hedefinin ortalaması bu yüzden −0,49 puandır (mekanik pay −0,34).
     Eğime etkisi küçük: p8b'de gecikme 8'de −0,0009 (eğim −0,075),
     p8c'de −0,004 (t −1,0). İki ölçü mekaniği iki ayrı yoldan taşır; ikisi
     yan yana basılır, hiçbiri "temiz" sayılmaz.
  3. ÖRTÜŞEN UFUKTA ÖRNEKLEM DIŞI SINAMA SIZAR: eğitim penceresine t'den
     önceki BÜTÜN satırlar alınırsa, hedef "sonraki 12 ayın değişimi"
     olduğunda o satırların son on biri t anında henüz gerçekleşmemiştir.
     Örneklem dışı sınama bu yüzden AMBARGOLUDUR (`ortak_olc.oos_takimi`,
     ambargo = ufuk: eğitim yalnız hedefi gerçekleşmiş satırlarla) ve
     Diebold–Mariano t'si ufka uygun Newey–West gecikmesiyle (24) kurulur.
     Ambargosuz eşleri ("…_ambargosuz") sızıntının büyüklüğü olarak yanında
     yazılır ve hükme GİRMEZ (tek hüküm kuralı, `ortak_olc.hukum`).
  4. GENİŞLEYEN ORTALAMA EĞİLİMİ SAPMA SANAR: TL 1994–2010 arasında reel
     değer kazandı, 2011–2022 arasında kaybetti; genişleyen ortalamadan
     sapma bu yüzden çoğunlukla eğilimdir (2007-12'de +31, 2021-12'de −63
     log puan; 2026-08'de genişleyen ortalamaya göre −17, kayan 10 yıllık
     ortalamaya göre +6 — aynı gün iki ters hüküm). Sağlamlık olarak kayan 10 yıllık ortalamadan sapma da sınanır.
  5. 2013 PENCERESİNİN UÇ GÜNLERİ İKİ SAATTEN: Yahoo kurları (BRL, INR,
     ZAR, MXN, TRY) düzeltilmiş günlük bardır, D değeri D'nin Londra gece
     yarısı kapanışıdır; 22.05.2013 Bernanke ifadesi 10:00 New York'ta
     (16:00 Orta Avrupa) başladığı için baz OLAY ÖNCESİ son kapanıştır
     (21.05). ECB referans kurları 14:15 Orta Avrupa'dadır, yani 22.05
     sabitlemesi ifadeden ÖNCEdir ve baz o gündür. Yahoo serisinde
     cumartesi barı olmadığı için 30.08.2013 CUMA değeri pazartesi barının
     başından gelir (hafta sonu açılışından sonraki fiyat); ECB sütunu bu
     kusuru taşımaz ve sağlamlık olarak yanında durur.
  6. ALTIN VE ENERJİ HARİÇ MAL DENGESİ ödemeler dengesi tanımıyla kurulur
     (mal dengesi − net parasal olmayan altın − net enerji); kalemler
     1996'dan başlar. Dış ticaret birim değer ve miktar endeksleri 2013'ten
     başlar, ithalat miktarında YAKIT HARİÇ endeks yoktur (değer ağırlığı
     olmadan çıkarılamaz): toplam ithalat miktarı ve yakıt ayrı verilir.
  7. SIZINTININ BÜYÜKLÜĞÜ ÖLÇÜLDÜ: p8c'de ambargosuz örneklem dışı oran
     0,99 (kıyasa denk görünür), ambargolu oran 1,20 (kıyastan KÖTÜ). Gerçekleşmemiş hedefleri gören eğitim modeli olduğundan iyi
     gösteriyordu.
  8. GELİR KONTROLÜ İHRACATTA TERS NEDENSELDİR: ihracat GSYH'nin bir
     bileşenidir; ihracat miktarının yurt içi büyümeye "esnekliği" (+1,5)
     talep etkisi değil muhasebedir. Gelir kontrollü ihracat esnekliği bu
     yüzden yalnız sağlamlıktır; ithalatta kontrol anlamlıdır.
  9. TCMB KURU TATİLİ BİLMELİ (denetimde ölçüldü): valör tarihini takvim iş
     günüyle geri almak resmî tatilin bir önceki günü yapılan ilanı TATİL
     gününe yazar ve asıl ilan günü seriden düşer. Tek tanım
     `ortak_olc.usdtry_tcmb` ilan gününü Türkiye iş günü takviminden kurar
     (valörden önceki son Türkiye iş günü; 2011 öncesinde valör dizisinin bir
     önceki günü). 30.08.2013 Zafer Bayramı'dır: o gün ilan yoktur, son ilan
     29.08 perşembedir ve p8d onu ADIYLA yazar. Aylık ve çeyreklik dönüşüm
     kuru da aynı seriden ortalanır.
  10. RASTGELE YÜRÜYÜŞ KIYASI (veri planı: Türkiye regresyonları rastgele
     yürüyüş kıyasıyla sınanır). Bağımlı değişken bir DEĞİŞİM olduğu için
     rastgele yürüyüş kıyası "değişim sıfır"dır. Hüküm koşulsuz ortalama ve
     sıfır kıyasının İKİSİNİ de ister; bugünkü ağaçta hiçbir hüküm bundan
     değişmiyor (p8b sıfıra göre ambargolu 0,93, ambargosuz 0,85).
  11. "%10'LUK" ETKİ LOG PUANLA YAZILMAZ (denetimde düzeltildi): eğimler log
     puan başınadır; 10·b 10 log puanlık (%10,5) hareketi verir. %10'luk reel
     değer kazancı 100·ln 1,1 = 9,53, kaybı 100·ln 0,9 = −10,54 log puandır ve
     ikisi simetrik değildir (8. ay eğimiyle −0,72 ve +0,79 puan; eski alan
     −0,75 yazıyordu).

  12. MXN'NİN YAHOO BARI NİSAN 2018 ÖNCESİNDE GÜN SONUDUR (`ortak_olc.em_kur`,
     `EM_GUN_SONU_GECIS`): öbür EM barlarındaki "günün başı" düzeltmesi MXN'ye
     2018-04-01'den önce uygulanmaz. p8d'nin MXN satırı bu yüzden ham bardır;
     21.05 ve 30.08 değerleri o günlerin gün sonu kapanışıdır (öbür Yahoo
     satırlarının 30.08 cuma değeri pazartesi barının başıdır, tuzak 5).
  13. CUMA UCU (p8d). Pencerenin son günü vakanın tanımıdır (30.08.2013 cuma);
     Yahoo düzeltilmiş barında cuma kapanışı YOKTUR, cuma değeri pazartesi
     barının başıdır ve öyle yazılır (`saat_notu`). Perşembe kapanışına
     çekmek (`usdtry(cuma_dus=True)`) vakadan bir seansı keserdi; aynı günün
     kusursuz sağlamlığı ECB'nin 30.08 sabitlemesidir ve her satırda yanında
     durur.
  14. BREXIT'TE İKİ KAPANIŞIN İKİSİ DE SONUÇTAN ÖNCE (vaka_brexit_2016).
     Sandıklar 23.06.2016 22:00 Londra'da (17:00 New York) kapandı, sonuçlar
     gece açıklandı. Gilt Londra kapanışı sandıklar kapanmadan, CNBC sterlin
     kapanışı (New York 17:00) sandıkların kapandığı anda alınır; ECB'nin
     23.06 sabitlemesi (14:15 Orta Avrupa) de öncedir. Baz bu yüzden üç
     kaynakta da 23.06, tepki 24.06'dır. Sterlinin dolara karşı hareketi
     dolar bacağını da taşır: öbür beş G10 parasına karşı değişim ve doların
     o beşe karşı değişimi ayrı yazılır (özdeşlik: sterlin/dolar = sterlin/beş
     − dolar/beş). Bu bir ayrıştırma değildir: Avrupa'yı ortak etkileyen bir
     şok o beşin içindeki avroya da düşer, avroya karşı değişim bu yüzden
     ayrıca yazılır.

ÖLÇÜLEN BULGULAR (tuzak değil): J-eğrisinin KISA kolu yok — gecikme 0'da
eğim sıfır, 4–13 ayda anlamlı eksi, en derin 8. ayda; dolar faturalı
ticarette (baskın para) değer kaybının ilk aylarda dolar cinsi dengeyi
bozması beklenmez. İkiz açık eğimi EKSİ (−0,77): Türkiye'de kamu dengesi
bozulduğunda cari denge iyileşiyor; özel kesim kamuyu fazlasıyla dengeliyor.
"İkisini aynı çevrim sürüklüyor" açıklaması ÖLÇÜLDÜ VE YETMİYOR: reel GSYH
büyümesi kontrol edilince eğim −0,63 (t −3,7) kalıyor, büyümenin kendi eğimi
−0,11 (t −1,6). Çevrim eğimin yalnız küçük bir kısmını taşıyor; kalanının
kaynağı bu ölçümle ayrıştırılamaz (metin onu nedensel bir hüküm olarak
kuramaz). Faiz dışı dengeyle eğim −0,68 (t −2,9), örneklem dışında tarif edici.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import olcum_b05 as b05          # İngiltere olay satırının tek tanımı (b05 bu modülü içe aktarmaz; döngü yok)
import ortak_olc as oo

warnings.filterwarnings("ignore", message="Could not infer format")   # ovp_programlar ilk sütunu tarih değil
warnings.filterwarnings("ignore", category=FutureWarning)

# ───────────────────────────────────────────────────────── sabitler (adlı)
HAC_GECIKME = 24              # 12 aylık toplamın 12 aylık değişimi ≈ 23 aylık örtüşme
HAC_GECIKME_CEYREK = 8        # çeyreklik Δ4 (4 çeyreklik toplamın 4 çeyreklik değişimi)
JEGRI_AZAMI_GECIKME = 24      # ay
SAPMA_ASGARI_AY = 60          # genişleyen ortalama için asgari geçmiş
SAPMA_KAYAN_AY = 120          # sağlamlık: kayan 10 yıllık ortalama
UFUK_AY = 12
ON_YUZDE_KAZANC_LOG = 100 * math.log(1.1)     # %10'luk (basit) artış, log puan
ON_YUZDE_KAYIP_LOG = 100 * math.log(0.9)      # %10'luk (basit) azalış, log puan
OOS_ILK_AY = 120              # örneklem dışı ilk eğitim penceresi (ay)
OOS_ILK_CEYREK = 40
ALT_DONEM_BAS = "2003-01-01"  # dalgalı kur ve enflasyon hedeflemesi dönemi
YONETILEN_ONCESI_SON = oo.YON_ONCESI_SON_AY   # yönetilen kur dönemi öncesi son ay (2021-11-01; tek tanım ortak_olc)
YON_ETIKET = f"{oo.YON_AY[0]} … {oo.YON_AY[1]}"
TAPER = {"olay": "2013-05-22", "baz_yahoo": "2013-05-21", "baz_ecb": "2013-05-22", "son": "2013-08-30"}
BESLI = [("BRL", "BRA", "Brezilya"), ("INR", "IND", "Hindistan"), ("ZAR", "ZAF", "Güney Afrika"),
         ("TRY", "TUR", "Türkiye"), ("IDR", "IDN", "Endonezya")]
KONTROL = [("MXN", "MEX", "Meksika")]
# Brexit vakası: pencere Bölüm 5'in İngiltere olay sözleşmesiyle ("baslangic" olay öncesi kapanış,
# "bitis" pencerenin son kapanışı; `olcum_b05._olay_igb`)
BREXIT_SAAT = ("Sandıklar 23.06.2016 22:00 Londra'da (17:00 New York) kapandı, sonuçlar gece açıklandı. Gilt "
               "Londra kapanışı sandıklar kapanmadan, CNBC sterlin kapanışı (New York 17:00) sandıkların "
               "kapandığı anda alınır: ikisi de sonuçtan öncedir, tepki 24.06 kapanışlarındadır.")
BREXIT = [
    {"kimlik": "brexit_2016_ilk_gun", "ad": "İngiltere 23.06.2016 AB referandumu → ilk tepki günü",
     "baslangic": "2016-06-23", "bitis": "2016-06-24", "saat_notu": BREXIT_SAAT},
    {"kimlik": "brexit_2016_boe", "alt": True,
     "ad": "İngiltere 23.06.2016 AB referandumu → BoE'nin 04.08.2016 paketi",
     "baslangic": "2016-06-23", "bitis": "2016-08-04",
     "saat_notu": BREXIT_SAAT[:BREXIT_SAAT.index(" Gilt")] + " Pencere BoE'nin referandum sonrası ilk faiz "
                  "indirimini ve varlık alımı paketini açıkladığı günün kapanışına uzatıldı (karar 12:00 Londra'da, "
                  "iki kapanıştan da önce); aradaki bütün haberleri taşır."},
]
BREXIT_CARI_YIL = "2015-12-31"   # olaydan önceki son tam yıl (p8d'de 2013 olayına 2012)
G10_OBUR = ["usd_eur", "usd_aud", "usd_chf", "usd_jpy", "usd_cad"]   # sterlin dışındaki beş G10 (dolar yönünde log)


# ───────────────────────────────────────────────────────── yardımcılar
_f, _iso, kurulmadi, hukum = oo._f, oo._iso, oo.kurulmadi, oo.hukum      # tek tanımlar ortak_olc'de
_reg = oo.reg


def oos_takim(y: pd.Series, x: pd.Series, ilk: int, ufuk: int, gecikme: int) -> dict:
    """İki saf kıyas (koşulsuz ortalama, sıfır = rastgele yürüyüşün değişimi),
    ambargo = ufuk, Diebold–Mariano gecikmesi `gecikme` (`ortak_olc.oos_takimi`).
    ufuk > 1 iken ambargosuz eşleri sızıntının büyüklüğü olarak yazılır; hükme
    girmez (tuzak 3)."""
    return oo.oos_takimi(y, x, ilk, ufuk=ufuk, dm_gecikme=gecikme, sizinti=True)


oranlar = oo.takim_oranlari


def tcmb_ilan() -> pd.Series:
    """TCMB gösterge kuru (TL/USD), İLAN gününe yazılmış; Türkiye iş günü
    takvimiyle geri alınmış valör serisi (`ortak_olc.usdtry_tcmb`, tuzak 9).
    Saat: 15:30 TSİ."""
    return oo.usdtry_tcmb()


# ───────────────────────────────────────────────────────── ortak seriler
@lru_cache(maxsize=1)
def aylik_kur_ort() -> pd.Series:
    """TCMB gösterge kuru (TL/USD), ay ortalaması; dönüşüm kuru."""
    t = oo.usdtry_tcmb()
    return t.resample("MS").mean()


def _ceyrekten_aya(s: pd.Series, bol: bool) -> pd.Series:
    """Çeyrek sonu tarihli seriyi o çeyreğin üç ayına yayar (bol: üçe böler)."""
    out = {}
    for q, v in s.dropna().items():
        p = pd.Period(q, "Q")
        bas = p.asfreq("M", "s")
        for m in range(3):
            out[(bas + m).to_timestamp()] = v / 3 if bol else v
    return pd.Series(out, dtype="float64").sort_index()


@lru_cache(maxsize=1)
def aylik_gsyh_usd() -> pd.Series:
    """12 aylık dolar GSYH'si (milyon USD), aylık: çeyreklik cari fiyatlı TL GSYH
    aylara eşit bölünür, her ay kendi ortalama TCMB kuruyla dolara çevrilir ve
    12 ay toplanır. Son ay, GSYH'nin bilinen son çeyreğinin son ayıdır."""
    g = oo.oku("gsyh_ceyreklik")["gsyh_cari_bin_tl"] / 1e3          # milyon TL, çeyrek
    ga = _ceyrekten_aya(g, bol=True)
    k = aylik_kur_ort().reindex(ga.index)
    usd = (ga / k).rolling(12, min_periods=12).sum()
    usd.name = "gsyh12_mn_usd"
    return usd.dropna()


@lru_cache(maxsize=1)
def _odemeler() -> pd.DataFrame:
    o = oo.oku("odemeler_aylik")
    o = o[o.index >= "1992-01-01"].copy()     # 1992 öncesi yalnız yıllık (Aralık) gözlem
    o["cekirdek_mal"] = o["mal_denge"] - o["hc_altin_net"] - o["hc_enerji_net"]
    return o


def oniki_toplam(ad: str) -> pd.Series:
    """Ödemeler dengesi kaleminin 12 aylık toplamı (milyon USD)."""
    return _odemeler()[ad].rolling(12, min_periods=12).sum()


def gsyh_orani(ad: str) -> pd.Series:
    """Kalemin 12 aylık toplamı / 12 aylık dolar GSYH, %."""
    return (oniki_toplam(ad) / aylik_gsyh_usd() * 100).dropna()


def _redk_log() -> pd.Series:
    return np.log(oo.oku("redk_aylik")["redk_tufe"].dropna()) * 100


def _gelir_buyume_aylik() -> pd.Series:
    """Mevsim ve takvim arındırılmış reel GSYH'nin yıllık log büyümesi (%), çeyreğin üç ayına."""
    h = np.log(oo.oku("gsyh_ceyreklik")["gsyh_mta_hacim"].dropna()) * 100
    return _ceyrekten_aya(h.diff(4), bol=False)


# ───────────────────────────────────────────────────────── p8a
@lru_cache(maxsize=1)
def _sektorel() -> pd.DataFrame:
    o = _odemeler()
    k = aylik_kur_ort().reindex(o.index)
    cari_tl12 = (o["cari"] * k).rolling(12, min_periods=12).sum()       # milyon TL
    ceyrek = cari_tl12[cari_tl12.index.month.isin([3, 6, 9, 12])].copy()
    ceyrek.index = ceyrek.index + pd.offsets.QuarterEnd(0)
    b = oo.oku("butce_ceyreklik")
    dis = ceyrek / (b["gsyh_yil_trl"] * 1e6) * 100                      # trilyon TL → milyon TL
    # resmî biçim: dolar cari / dolar GSYH (çeyreklik TL GSYH çeyrek ortalama kuruyla)
    g = oo.oku("gsyh_ceyreklik")["gsyh_cari_bin_tl"] / 1e3
    kq = oo.usdtry_tcmb().resample("QE").mean()
    gusd4 = (g / kq.reindex(g.index)).rolling(4, min_periods=4).sum()
    cu = o["cari"].rolling(12, min_periods=12).sum()
    cu = cu[cu.index.month.isin([3, 6, 9, 12])].copy()
    cu.index = cu.index + pd.offsets.QuarterEnd(0)
    dis_usd = cu / gusd4 * 100
    df = pd.DataFrame({"kamu": b["denge_gsyh"], "dis": dis, "dis_usd": dis_usd}).dropna()
    df = df[df.index <= oo.CIPA_CEYREK.end_time.normalize()]
    df["ozel"] = df["dis"] - df["kamu"]
    return df


def _q(t) -> str:
    p = pd.Period(t, "Q")
    return f"{p.year}Ç{p.quarter}"


def p8a() -> dict:
    df = _sektorel()
    son = df.index.max()
    uc = {}
    for c in ("kamu", "dis", "ozel"):
        uc[c] = {"en_dusuk_gsyh_yuzde": float(df[c].min()), "en_dusuk_ceyrek": _q(df[c].idxmin()),
                 "en_yuksek_gsyh_yuzde": float(df[c].max()), "en_yuksek_ceyrek": _q(df[c].idxmax()),
                 "ortalama_gsyh_yuzde": float(df[c].mean())}
    fark = (df["dis"] - df["dis_usd"])
    donusum = {"tl_eksi_usd_azami_mutlak_puan": float(fark.abs().max()),
               "azami_ceyrek": _q(fark.abs().idxmax()),
               "azami_ceyrek_tl_gsyh_yuzde": float(df.loc[fark.abs().idxmax(), "dis"]),
               "azami_ceyrek_usd_gsyh_yuzde": float(df.loc[fark.abs().idxmax(), "dis_usd"]),
               "ortalama_mutlak_puan": float(fark.abs().mean()),
               "bir_puani_asan_ceyrek": int((fark.abs() >= 1).sum())}

    # ikiz açık: 4 çeyreklik değişimler (örtüşen; gecikme 8). Eşzamanlı ilişki:
    # ambargo 1, DM t'si de 8 çeyreklik gecikmeyle (4 çeyreklik toplamın Δ4'ü 7 çeyrek örtüşür).
    d4 = df.diff(4).dropna()
    ikiz = _reg(d4["dis"], d4["kamu"], HAC_GECIKME_CEYREK)
    oos = oos_takim(d4["dis"], d4["kamu"], OOS_ILK_CEYREK, 1, HAC_GECIKME_CEYREK)
    # sağlamlık 1: çevrim (reel GSYH'nin yıllık büyümesi) kontrolü — "ikisini aynı çevrim sürüklüyor" açıklamasının sınaması
    h = np.log(oo.oku("gsyh_ceyreklik")["gsyh_mta_hacim"].dropna()) * 100
    cev = _reg(d4["dis"], pd.DataFrame({"kamu": d4["kamu"], "buyume": h.diff(4)}).reindex(d4.index),
               HAC_GECIKME_CEYREK)
    # sağlamlık 2: faiz dışı denge (veri planı: Türkiye regresyonları faiz dışı dengeyle de kurulur)
    fdd = oo.oku("butce_ceyreklik")["fdd_gsyh"].reindex(df.index).diff(4).reindex(d4.index)
    fd = _reg(d4["dis"], fdd.rename("fdd"), HAC_GECIKME_CEYREK)
    fd_oos = oos_takim(d4["dis"], fdd, OOS_ILK_CEYREK, 1, HAC_GECIKME_CEYREK)
    ikiz_out = {"n": ikiz["n"], "ilk": ikiz["ilk"], "son": ikiz["son"], "egim": ikiz["b"][0],
                "se": ikiz["se"][0], "t": ikiz["t"][0], "r2": ikiz["r2"], "gecikme": ikiz["gecikme"],
                "ozel_kesim_dengelemesi": 1 - ikiz["b"][0],
                "seviye_korelasyonu_kamu_ozel": float(df["kamu"].corr(df["ozel"])),
                "seviye_korelasyonu_kamu_dis": float(df["kamu"].corr(df["dis"])),
                "oos": oos, "hukum": hukum(ikiz["t"][0], oranlar(oos)),
                "cevrim_kontrollu": {"egim": cev["b"][0], "t": cev["t"][0], "buyume_egim": cev["b"][1],
                                     "buyume_t": cev["t"][1], "r2": cev["r2"], "n": cev["n"],
                                     "yontem": ("Aynı regresyona reel GSYH'nin yıllık büyümesi kontrol olarak eklendi; "
                                                "eğim yerinde kalıyorsa ortak çevrim ilişkiyi tek başına açıklamaz.")},
                "faiz_disi_denge": {"egim": fd["b"][0], "se": fd["se"][0], "t": fd["t"][0], "r2": fd["r2"],
                                    "n": fd["n"], "ilk": fd["ilk"], "son": fd["son"], "oos": fd_oos,
                                    "hukum": hukum(fd["t"][0], oranlar(fd_oos)),
                                    "yontem": "Kamu dengesi yerine faiz dışı dengenin dört çeyreklik değişimi."},
                "yontem": ("Dış dengenin dört çeyreklik değişimi kamu dengesinin dört çeyreklik değişimine "
                           "regrese edildi; eğim 1 tam ikiz açık, 0 özel kesimin kamuyu tamamen dengelemesi "
                           "demektir; standart hata Newey–West, örneklem dışı kıyas koşulsuz ortalama ve "
                           "değişimin sıfır olması.")}

    # OVP kontrol noktası: kendi yıl sonu ölçümüm (Ç4) ile programın satırı
    ovp = oo.oku("ovp_programlar").reset_index()
    kontrol = []
    for _, r in ovp.iterrows():
        yil = int(r["yil"])
        if yil not in (2024, 2025) or r["sutun"] not in ("gerceklesme", "tahmin"):
            continue
        q4 = pd.Timestamp(f"{yil}-12-31")
        if q4 not in df.index:
            continue
        z = df.loc[q4]
        ovp_ozel = float(r["tasarruf_yatirim_farki_gsyh"] - r["genel_devlet_dengesi_gsyh"])
        kontrol.append({
            "program": r["program"], "yayin_ay": r["yayin_ay"], "yil": yil, "sutun": r["sutun"],
            # gerçekleşme sütununda fark veri sürümü (ve kapsam) farkıdır; tahmin sütununda yıl kapanmadan
            # yayımlanmış bir tahminin hatasıdır — ikisi aynı kontrol noktası değildir
            "fark_turu": "sürüm ve kapsam farkı" if r["sutun"] == "gerceklesme" else "tahmin hatası",
            "kontrol_noktasi": r["sutun"] == "gerceklesme",
            "ovp_tasarruf_yatirim_farki_gsyh_yuzde": float(r["tasarruf_yatirim_farki_gsyh"]),
            "ovp_cari_gsyh_yuzde": float(r["cari_gsyh"]),
            "ovp_genel_devlet_dengesi_gsyh_yuzde": float(r["genel_devlet_dengesi_gsyh"]),
            "ovp_ozel_artik_gsyh_yuzde": ovp_ozel,
            "olcum_dis_tl_gsyh_yuzde": float(z["dis"]), "olcum_dis_usd_gsyh_yuzde": float(z["dis_usd"]),
            "olcum_kamu_merkezi_yonetim_gsyh_yuzde": float(z["kamu"]), "olcum_ozel_gsyh_yuzde": float(z["ozel"]),
            "fark_cari_usd_puan": float(z["dis_usd"] - r["cari_gsyh"]),
            "fark_cari_tl_puan": float(z["dis"] - r["cari_gsyh"]),
            "fark_dis_tasarruf_yatirim_puan": float(z["dis"] - r["tasarruf_yatirim_farki_gsyh"]),
            "fark_kamu_puan": float(z["kamu"] - r["genel_devlet_dengesi_gsyh"]),
            "fark_ozel_puan": float(z["ozel"] - ovp_ozel)})
    return {
        "yontem": ("Kamu dengesi merkezi yönetim bütçesinin 12 aylık dengesinin GSYH'ye oranı; dış denge 12 aylık "
                   "cari dengenin her ayı kendi ayının TCMB ortalama kuruyla liraya çevrilip toplanmış hâlinin "
                   "dört çeyreklik GSYH'ye oranı; özel kesim dengesi bu ikisinin farkı olarak kalan artık."),
        "kaynak": ["butce_ceyreklik (denge_gsyh, gsyh_yil_trl)", "odemeler_aylik (cari)",
                   "usdtry_tcmb_gunluk (dönüşüm kuru)", "gsyh_ceyreklik (cari fiyatlarla GSYH)",
                   "ovp_programlar (kontrol noktası)"],
        "kapsam_notu": ("Kamu MERKEZİ YÖNETİMDİR (genel yönetim değil: yerel yönetimler, sosyal güvenlik ve fonlar "
                        "dışarıda). Özel kesim ARTIKTIR: kapsam farkı, nakit–tahakkuk farkı, net hata ve noksan ile "
                        "dönüşüm kuru seçimi ona yazılır."),
        "donusum_secimi": ("TL oranı: aylık cari denge o ayın ortalama kuruyla liraya çevrilir; resmî dolar oranı "
                           "(çeyreklik TL GSYH çeyrek ortalama kuruyla dolara) karşılaştırma için yanında."),
        "n": int(len(df)), "ilk": _iso(df.index.min()), "son": _iso(son),
        "ilk_ceyrek": _q(df.index.min()), "son_ceyrek": _q(son),
        "son_deger": {"kamu_gsyh_yuzde": float(df.loc[son, "kamu"]), "dis_tl_gsyh_yuzde": float(df.loc[son, "dis"]),
                      "dis_usd_gsyh_yuzde": float(df.loc[son, "dis_usd"]), "ozel_gsyh_yuzde": float(df.loc[son, "ozel"])},
        "uc_degerler": uc, "donusum_farki": donusum, "ikiz_acik": ikiz_out, "ovp_kontrol": kontrol,
        "ovp_notu": ("OVP'nin gerçekleşme satırları belgenin yayımlandığı günün verisidir; ödemeler dengesi ve "
                     "GSYH sonradan düzeltildiyse fark ölçüm hatası değil sürüm farkıdır. Tahmin satırı yıl "
                     "kapanmadan yayımlanmıştır: oradaki fark programın tahmin hatasıdır ve kontrol noktası "
                     "sayılmaz. OVP özel kesim satırı burada tasarruf–yatırım farkından genel devlet dengesi "
                     "çıkarılarak kuruldu (artık)."),
    }


def sekil_13() -> dict:
    df = _sektorel()
    return {"baslik": "Türkiye sektörel dengeleri (% GSYH, 4 çeyreklik akım)", "n": int(len(df)),
            "yontem": "Kamu (merkezi yönetim), dış (cari, TL dönüşümlü ve resmî dolar biçimi) ve özel kesim (artık) "
                      "dengesi, dört çeyreklik akım / GSYH.",
            "kaynak": ["butce_ceyreklik", "odemeler_aylik", "usdtry_tcmb_gunluk", "gsyh_ceyreklik"],
            "tarih": [_iso(t) for t in df.index], "ceyrek": [_q(t) for t in df.index],
            "kamu": [float(v) for v in df["kamu"]], "dis": [float(v) for v in df["dis"]],
            "ozel": [float(v) for v in df["ozel"]], "dis_usd": [float(v) for v in df["dis_usd"]],
            "birim": "% GSYH", "ilk": _iso(df.index.min()), "son": _iso(df.index.max()),
            "ilk_ceyrek": _q(df.index.min()), "son_ceyrek": _q(df.index.max())}


# ───────────────────────────────────────────────────────── p8b
@lru_cache(maxsize=1)
def _jegri_cerceve() -> pd.DataFrame:
    B = oniki_toplam("cekirdek_mal")
    G = aylik_gsyh_usd()
    q = _redk_log()
    df = pd.DataFrame({
        "y_sabit": (B - B.shift(12)) / G.shift(12) * 100,          # puan, değişimin başındaki GSYH
        "y_oran": (B / G * 100).diff(12),                           # puan, oranın kendi değişimi
        "dq": q.diff(12),                                           # %, log×100
        "g": _gelir_buyume_aylik(),
    })
    df = df[df.index <= oo.CIPA_AY.to_timestamp()]
    return df


def _profil(df: pd.DataFrame, yad: str, kontrol: bool = False, bas: str | None = None,
            son: str | None = None) -> dict:
    """k = 0…24 için ayrı HAC eğimi; sütun dizileri (kompakt). Örneklem her gecikmede aynıdır
    (reel kur 1994'ten başlar, bağımlı değişken 1997 sonundan), n/ilk/son bir kez yazılır."""
    z = df if bas is None else df[df.index >= bas]
    z = z if son is None else z[z.index <= son]
    out = {"gecikme_ay": [], "egim": [], "se": [], "t": [], "r2": []}
    if kontrol:
        out.update({"gelir_egim": [], "gelir_t": []})
    nler = set()
    for k in range(JEGRI_AZAMI_GECIKME + 1):
        X = pd.DataFrame({"dq": df["dq"].shift(k)}).reindex(z.index)
        if kontrol:
            X["g"] = z["g"]
        r = _reg(z[yad], X, HAC_GECIKME)
        out["gecikme_ay"].append(k)
        out["egim"].append(r["b"][0]); out["se"].append(r["se"][0]); out["t"].append(r["t"][0])
        out["r2"].append(r["r2"])
        if kontrol:
            out["gelir_egim"].append(r["b"][1]); out["gelir_t"].append(r["t"][1])
        nler.add((r["n"], r["ilk"], r["son"]))
    n, ilk, son = sorted(nler)[0]
    out.update({"n": n, "ilk": ilk, "son": son, "ayni_orneklem": len(nler) == 1,
                "birim": "puan (% GSYH) / REDK'nin %1'lik (log) değişimi", "gecikme": HAC_GECIKME})
    return out


def _profil_ozeti(pr: dict) -> dict:
    b = np.array(pr["egim"])
    t = np.array(pr["t"])
    g = pr["gecikme_ay"]
    j = int(np.argmin(b))
    anlamli_eksi = [g[i] for i in range(len(g)) if t[i] <= -2]
    anlamli_arti = [g[i] for i in range(len(g)) if t[i] >= 2]
    return {"en_eksi_gecikme_ay": int(g[j]), "en_eksi_egim_puan_yuzde": float(b[j]),
            "en_eksi_t": float(t[j]),
            # eğim log puan başınadır: %10'luk kazanç 100·ln 1,1 = 9,53, %10'luk kayıp 100·ln 0,9 = −10,54 log puan
            "on_yuzde_reel_deger_kazanci_puan": float(ON_YUZDE_KAZANC_LOG * b[j]),
            "on_yuzde_reel_deger_kaybi_puan": float(ON_YUZDE_KAYIP_LOG * b[j]),
            "anlamli_eksi_gecikmeler_ay": anlamli_eksi, "anlamli_arti_gecikmeler_ay": anlamli_arti,
            "gecikme0_egim": float(b[0]), "gecikme0_t": float(t[0]),
            "gecikme24_egim": float(b[-1]), "gecikme24_t": float(t[-1]),
            # J-eğrisi: ilk altı ayda anlamlı ARTI eğim ve sonra anlamlı EKSİ eğim
            "j_isareti_kisa_arti_uzun_eksi": bool(any(t[i] >= 2 for i in range(7)) and len(anlamli_eksi) > 0)}


def _fiyat_miktar(df: pd.DataFrame) -> dict:
    try:
        e = bulut.dis_ticaret_endeks()
    except bulut.VeriYok as hata:
        return kurulmadi(f"{hata}; fiyat ve miktar ayrımı yapılamadı")
    seriler = {
        "ihracat_miktar": np.log(e["ihr_miktar"]) * 100,
        "ithalat_miktar": np.log(e["ith_miktar"]) * 100,
        "ithalat_yakit_miktar": np.log(e["ith_yakit_miktar"]) * 100,
        "ticaret_hadleri": np.log(e["ihr_birim_deger"] / e["ith_birim_deger"]) * 100,
        "ihracat_birim_deger": np.log(e["ihr_birim_deger"]) * 100,
        "ithalat_birim_deger": np.log(e["ith_birim_deger"]) * 100,
    }
    out = {"yontem": ("Dış ticaret miktar ve birim değer endekslerinin 12 aylık log değişimi, reel efektif kurun "
                      "aynı aydaki ve 12 ay önceki 12 aylık log değişimine ayrı ayrı regrese edildi; ikinci "
                      "tanımda yurt içi gelir büyümesi kontrol."),
           "kaynak": ["bulut: EVDS dış ticaret birim değer ve miktar endeksleri (2010=100)", "redk_aylik",
                      "gsyh_ceyreklik (hacim endeksi)"],
           "birim": "endeksin yüzde değişimi / REDK'nin yüzde değişimi (log×100)",
           "kalemler": {}}
    for ad, s in seriler.items():
        y = s.diff(12)
        kalem = {}
        for k in (0, 12):
            x = df["dq"].shift(k)
            r = _reg(y, x.rename("dq"), HAC_GECIKME)
            rg = _reg(y, pd.DataFrame({"dq": x, "g": df["g"]}), HAC_GECIKME)
            kalem[f"gecikme_{k}"] = {"esneklik": r["b"][0], "se": r["se"][0], "t": r["t"][0], "r2": r["r2"],
                                     "n": r["n"], "ilk": r["ilk"], "son": r["son"],
                                     "gelir_kontrollu_esneklik": rg["b"][0], "gelir_kontrollu_t": rg["t"][0],
                                     "gelir_kontrollu_n": rg["n"],
                                     "gelir_esneklik": rg["b"][1], "gelir_t": rg["t"][1]}
        d = pd.concat([y.rename("y"), df["dq"].shift(12).rename("x")], axis=1).dropna()
        ilk = min(60, len(d) // 2)
        oos = oo.oos_takimi(d["y"], d["x"], ilk, ufuk=UFUK_AY, dm_gecikme=HAC_GECIKME)
        kalem["oos_gecikme_12"] = oos
        kalem["hukum_gecikme_12"] = hukum(kalem["gecikme_12"]["t"], oranlar(oos))
        out["kalemler"][ad] = kalem
    out["sinir"] = ("İthalatta yakıt hariç miktar endeksi yok; değer ağırlıkları olmadan toplamdan çıkarılamaz. "
                    f"Endeksler 2013'te başlar ve yönetilen kur dönemini ({YON_ETIKET}) içerir. İhracat GSYH'nin "
                    "bileşeni olduğu için ihracatta gelir kontrolü ters nedenseldir, yalnız sağlamlıktır.")
    return out


def p8b() -> dict:
    df = _jegri_cerceve()
    ana = _profil(df, "y_sabit")
    gelir = _profil(df, "y_sabit", kontrol=True)
    oran = _profil(df, "y_oran")
    alt = _profil(df, "y_sabit", bas=ALT_DONEM_BAS)
    yon_once = _profil(df, "y_sabit", son=YONETILEN_ONCESI_SON)
    # yıllık kısıtsız dağıtılmış gecikme: örtüşmeyen üç yıllık değişim birlikte
    X = pd.DataFrame({"yil0": df["dq"], "yil1": df["dq"].shift(12), "yil2": df["dq"].shift(24)})
    dl = _reg(df["y_sabit"], X, HAC_GECIKME)
    Xg = X.assign(g=df["g"])
    dlg = _reg(df["y_sabit"], Xg, HAC_GECIKME)

    def _dl(r: dict, gelirli: bool) -> dict:
        b, se, t = r["b"], r["se"], r["t"]
        o = {f"yil{i}_egim": b[i] for i in range(3)} | {f"yil{i}_t": t[i] for i in range(3)} | \
            {f"yil{i}_se": se[i] for i in range(3)}
        o.update({"toplam_egim": float(sum(b[:3])), "r2": r["r2"], "n": r["n"], "ilk": r["ilk"], "son": r["son"],
                  "gecikme": r["gecikme"]})
        if gelirli:
            o.update({"gelir_egim": b[3], "gelir_t": t[3]})
        return o
    # örneklem dışı: 12 ay önceki reel kur değişimi → bu yılın değişimi (gerçek öngörü ufku)
    d = pd.concat([df["y_sabit"].rename("y"), df["dq"].shift(12).rename("x")], axis=1).dropna()
    oos12 = oos_takim(d["y"], d["x"], OOS_ILK_AY, UFUK_AY, HAC_GECIKME)
    return {
        "yontem": ("Altın ve enerji hariç mal dengesinin 12 aylık toplamındaki 12 aylık değişim (dolar; değişimin "
                   "başındaki 12 aylık dolar GSYH'ye oranla, puan), reel efektif kurun k ay önceki 12 aylık log "
                   "değişimine her k = 0…24 için ayrı regrese edildi; standart hata Newey–West (gecikme 24)."),
        "kaynak": ["odemeler_aylik (mal_denge, hc_altin_net, hc_enerji_net)", "redk_aylik (redk_tufe)",
                   "gsyh_ceyreklik", "usdtry_tcmb_gunluk (dönüşüm kuru)"],
        "isaret": ("REDK artışı TL'nin reel değer kazancıdır: eksi eğim, reel değer kazancının dengeyi bozduğu "
                   "(Marshall–Lerner yönü) demektir; J-eğrisi kısa gecikmede ARTI, uzun gecikmede EKSİ eğim ister."),
        "birim": "puan (% GSYH) / REDK'nin %1'lik (log) değişimi",
        "n": ana["n"], "ilk": ana["ilk"], "son": ana["son"],
        "profil": ana, "ozet": _profil_ozeti(ana),
        "gelir_kontrollu": {"profil": gelir, "ozet": _profil_ozeti(gelir),
                            "yontem": "Aynı regresyona yurt içi reel GSYH'nin yıllık büyümesi kontrol olarak eklendi."},
        "oran_degisimi": {"profil": oran, "ozet": _profil_ozeti(oran),
                          "yontem": "Bağımlı değişken dengenin GSYH'ye oranının kendi 12 aylık değişimi (payda etkisi dahil)."},
        "alt_donem_2003": {"profil": alt, "ozet": _profil_ozeti(alt),
                           "yontem": "Ana tanım, 2003 sonrası (dalgalı kur ve enflasyon hedeflemesi dönemi)."},
        "yonetilen_oncesi": {"ozet": _profil_ozeti(yon_once), "n": yon_once["n"], "ilk": yon_once["ilk"],
                             "son": yon_once["son"],
                             "gecikme_12": {"egim_puan_yuzde": yon_once["egim"][12], "t": yon_once["t"][12]},
                             "yontem": (f"Ana tanım, yönetilen kur dönemi ({YON_ETIKET}) başlamadan biten "
                                        "örneklem; bu bir kur tepkisi değil, dönem sağlamlık için ayrılır.")},
        "yillik_dagitilmis_gecikme": {"gelirsiz": _dl(dl, False), "gelir_kontrollu": _dl(dlg, True),
                                      "yontem": ("Reel kurun bu yılki, bir yıl önceki ve iki yıl önceki 12 aylık "
                                                 "değişimleri birlikte (örtüşmeyen pencereler).")},
        "oos_gecikme_12": oos12,
        "gecikme_12": {"egim_puan_yuzde": ana["egim"][12], "se": ana["se"][12], "t": ana["t"][12]},
        "hukum_gecikme_12": hukum(ana["t"][12], oranlar(oos12)),
        "fiyat_miktar": _fiyat_miktar(df),
    }


def sekil_14() -> dict:
    df = _jegri_cerceve()
    ana = _profil(df, "y_sabit")
    gelir = _profil(df, "y_sabit", kontrol=True)
    return {"baslik": "J-eğrisi: reel kur değişiminin çekirdek mal dengesine gecikmeli etkisi",
            "gecikme_ay": ana["gecikme_ay"], "egim": ana["egim"], "se": ana["se"],
            "egim_gelir_kontrollu": gelir["egim"], "se_gelir_kontrollu": gelir["se"],
            "birim": ana["birim"], "ilk": ana["ilk"], "son": ana["son"], "n": ana["n"],
            "yontem": "Her gecikme k = 0…24 için ayrı Newey–West eğimi (gecikme 24); gelir kontrollü profil yanında.",
            "kaynak": ["odemeler_aylik", "redk_aylik", "gsyh_ceyreklik", "usdtry_tcmb_gunluk"]}


# ───────────────────────────────────────────────────────── p8c
@lru_cache(maxsize=1)
def _sapma_cerceve() -> pd.DataFrame:
    q = _redk_log()
    gen = q.expanding(min_periods=SAPMA_ASGARI_AY).mean()
    kay = q.rolling(SAPMA_KAYAN_AY, min_periods=SAPMA_KAYAN_AY).mean()
    G = aylik_gsyh_usd()
    out = {"sapma": q - gen, "sapma_kayan": q - kay, "sapma_tam_ornek": q - q.mean()}
    for ad, kalem in (("cari", "cari"), ("cekirdek", "hc_cekirdek")):
        B = oniki_toplam(kalem)
        oran = B / G * 100
        out[f"{ad}_oran"] = oran
        out[f"{ad}_ileri_sabit"] = (B.shift(-UFUK_AY) - B) / G * 100       # payda başlangıçta sabit
        out[f"{ad}_ileri_oran"] = oran.shift(-UFUK_AY) - oran
    df = pd.DataFrame(out)
    return df[df.index <= oo.CIPA_AY.to_timestamp()]


def _sapma_regresyonu(df: pd.DataFrame, yad: str, xad: str, oos: bool = True) -> dict:
    d = df[[yad, xad]].dropna()
    r = _reg(d[yad], d[xad], HAC_GECIKME)
    out = {"n": r["n"], "ilk": r["ilk"], "son": r["son"], "egim_puan_yuzde": r["b"][0], "se": r["se"][0],
           "t": r["t"][0], "r2": r["r2"], "gecikme": r["gecikme"], "sabit": r["sabit"],
           "on_yuzde_sapma_puan": ON_YUZDE_KAZANC_LOG * r["b"][0]}     # REDK ortalamasının %10 üstü
    if oos:
        tk = oos_takim(d[yad], d[xad], OOS_ILK_AY, UFUK_AY, HAC_GECIKME)
        out.update({"oos": tk, "hukum": hukum(r["t"][0], oranlar(tk))})
    return out


def p8c() -> dict:
    df = _sapma_cerceve()
    son = df["sapma"].dropna().index.max()
    sonuc = {
        "yontem": ("Log reel efektif kurun o aya kadarki bütün geçmişin ortalamasından sapması (yüzde), sonraki "
                   "12 ayda 12 aylık cari dengenin dolar değişimine (değişimin başındaki 12 aylık dolar GSYH'ye "
                   "oranla, puan) regrese edildi; standart hata Newey–West (gecikme 24), örneklem dışı kıyas "
                   "koşulsuz ortalama ve değişimin sıfır olması, eğitim yalnız gerçekleşmiş hedeflerle."),
        "kaynak": ["redk_aylik (redk_tufe)", "odemeler_aylik (cari, hc_cekirdek)", "gsyh_ceyreklik",
                   "usdtry_tcmb_gunluk (dönüşüm kuru)"],
        "isaret": "Artı sapma ortalamaya göre pahalı TL'dir; eksi eğim pahalı liranın sonraki yıl cari dengeyi bozduğu demektir.",
        "sapma_son": {"tarih": _iso(son), "sapma_yuzde": float(df.loc[son, "sapma"]),
                      "sapma_kayan_yuzde": _f(df.loc[son, "sapma_kayan"])},
        "sapma_dagilimi": {"en_dusuk_yuzde": float(df["sapma"].min()), "en_dusuk_tarih": _iso(df["sapma"].idxmin()),
                           "en_yuksek_yuzde": float(df["sapma"].max()), "en_yuksek_tarih": _iso(df["sapma"].idxmax())},
    }
    for ad in ("cari", "cekirdek"):
        ana = _sapma_regresyonu(df, f"{ad}_ileri_sabit", "sapma")
        sonuc[ad] = {
            **ana,
            "oran_degisimi": _sapma_regresyonu(df, f"{ad}_ileri_oran", "sapma"),
            "kayan_10_yil_sapma": _sapma_regresyonu(df, f"{ad}_ileri_sabit", "sapma_kayan"),
            "alt_donem_2003": _sapma_regresyonu(df[df.index >= ALT_DONEM_BAS], f"{ad}_ileri_sabit", "sapma", oos=False),
            "ileriye_bakan_tam_ornek_ortalamasi": _sapma_regresyonu(df, f"{ad}_ileri_sabit", "sapma_tam_ornek", oos=False),
        }
    sonuc["cekirdek"]["tanim"] = "altın ve enerji hariç cari denge (TCMB tablosu)"
    sonuc["ileriye_bakan_notu"] = ("Tam örneklem ortalamasından sapma, o gün bilinmeyen gelecek gözlemleri kullanır; "
                                   "yalnız karşılaştırma için örneklem içi verilir.")
    return sonuc


def sekil_15() -> dict:
    df = _sapma_cerceve()
    d = df[["sapma", "cari_ileri_sabit", "cari_oran"]].dropna(subset=["sapma", "cari_oran"])
    return {"baslik": "REDK sapması ve sonraki 12 ayda cari denge değişimi", "n": int(len(d)),
            "n_ileri": int(d["cari_ileri_sabit"].notna().sum()),
            "yontem": "Log REDK'nin genişleyen ortalamadan sapması, 12 aylık cari denge / GSYH ve sonraki 12 ayın "
                      "sabit paydalı değişimi (aylık).",
            "kaynak": ["redk_aylik", "odemeler_aylik", "gsyh_ceyreklik", "usdtry_tcmb_gunluk"],
            "tarih": [_iso(t) for t in d.index],
            "redk_sapma_yuzde": [float(v) for v in d["sapma"]],
            "cari_gsyh_yuzde": [float(v) for v in d["cari_oran"]],
            "sonraki_12ay_cari_degisim_puan": [_f(v) for v in d["cari_ileri_sabit"]],
            "ilk": _iso(d.index.min()), "son": _iso(d.index.max()),
            "not": "Sonraki 12 ayın değişimi son 12 ayda henüz gerçekleşmediği için boştur."}


# ───────────────────────────────────────────────────────── p8d
def _yahoo_degisim(kod: str) -> dict:
    if kod == "TRY":
        s, kun = oo.usdtry()
        kaynak = "Yahoo USD/TRY (düzeltilmiş günlük bar, Londra gece yarısı)"
    else:
        s = oo.em_kur(kod)
        g = oo.EM_GUN_SONU_GECIS.get(kod.lower())
        kaynak = (f"Yahoo USD/{kod} (ham günlük bar: {g.strftime('%d.%m.%Y')} öncesinde gün sonu kapanışı)"
                  if g is not None and pd.Timestamp(TAPER["son"]) < g else
                  f"Yahoo USD/{kod} (düzeltilmiş günlük bar, Londra gece yarısı)")
    b, e = pd.Timestamp(TAPER["baz_yahoo"]), pd.Timestamp(TAPER["son"])
    if b not in s.index or e not in s.index:
        return kurulmadi(f"Yahoo USD/{kod} serisinde pencere uç günü yok")
    return {"baz_gun": _iso(b), "son_gun": _iso(e), "baz": float(s.loc[b]), "son": float(s.loc[e]),
            "degisim_log_yuzde": float(100 * math.log(s.loc[e] / s.loc[b])),
            "degisim_yuzde": float(100 * (s.loc[e] / s.loc[b] - 1)), "kaynak": kaynak}


def _ecb_degisim(kod: str) -> dict:
    try:
        x = bulut.ecb_kur(kod) / bulut.ecb_kur("USD")         # USD/XXX = (EUR/XXX)/(EUR/USD)
    except bulut.VeriYok as hata:
        return kurulmadi(str(hata))
    b, e = pd.Timestamp(TAPER["baz_ecb"]), pd.Timestamp(TAPER["son"])
    if b not in x.index or e not in x.index:
        return kurulmadi(f"ECB {kod} serisinde pencere uç günü yok")
    return {"baz_gun": _iso(b), "son_gun": _iso(e), "baz": float(x.loc[b]), "son": float(x.loc[e]),
            "degisim_log_yuzde": float(100 * math.log(x.loc[e] / x.loc[b])),
            "degisim_yuzde": float(100 * (x.loc[e] / x.loc[b] - 1)),
            "kaynak": f"ECB referans kuru çaprazı USD/{kod} (14:15 Orta Avrupa)"}


def p8d() -> dict:
    try:
        w = bulut.wdi("cari")
        wdi_hata = None
    except bulut.VeriYok as hata:
        w, wdi_hata = None, str(hata)
    satirlar = []
    for kod, iso3, ad in BESLI + KONTROL:
        if kod == "IDR":
            ana = _ecb_degisim("IDR")
            if ana.get("durum") is None:
                ana["kaynak"] = "ECB referans kuru çaprazı USD/IDR (14:15 Orta Avrupa; Yahoo serisi yok)"
        else:
            ana = _yahoo_degisim(kod)
        satir = {"para": kod, "ulke": ad, "grup": "kontrol" if (kod, iso3, ad) in KONTROL else "kırılgan beşli",
                 "kur": ana, "ecb_saglamlik": _ecb_degisim(kod),
                 "ana_kaynak_ecb": kod == "IDR"}
        if w is None:
            satir["cari_gsyh_2012"] = kurulmadi(wdi_hata)
        elif iso3 not in w.columns or pd.isna(w[iso3].get(pd.Timestamp("2012-12-31"))):
            satir["cari_gsyh_2012"] = kurulmadi("Dünya Bankası dosyasında 2012 değeri yok")
        else:
            satir["cari_gsyh_2012"] = {"deger_yuzde": float(w.loc[pd.Timestamp("2012-12-31"), iso3]),
                                       "kaynak": "Dünya Bankası WDI, cari denge (% GSYH)"}
        satirlar.append(satir)
    # Türkiye: TCMB gösterge kuru (15:30 TSİ ilanı; 22.05 ilanı ifadeden önce) ve kendi ölçümüm.
    # 30.08.2013 Türkiye'de resmî tatil (Zafer Bayramı): o gün ilan yok, son ilan 29.08 (tuzak 9).
    t = tcmb_ilan()
    b, e = pd.Timestamp(TAPER["baz_ecb"]), pd.Timestamp(TAPER["son"])
    e_ilan = t.index[t.index <= e].max() if (t.index <= e).any() else None
    if b in t.index and e_ilan is not None:
        tcmb = {"baz_gun": _iso(b), "son_gun": _iso(e_ilan),
                "degisim_log_yuzde": float(100 * math.log(t.loc[e_ilan] / t.loc[b])),
                "kaynak": "TCMB gösterge kuru (ilan günü; 15:30 TSİ)",
                "not": (None if e_ilan == e else
                        f"{_iso(e)} Türkiye'de resmî tatil, TCMB ilanı yok; son ilan {_iso(e_ilan)}")}
    else:
        tcmb = kurulmadi("TCMB kurunda uç gün yok")
    df = _sektorel()
    q = pd.Timestamp("2012-12-31")
    turkiye = {"tcmb_kuru_saglamlik": tcmb,
               "cari_gsyh_2012_olcum_usd_yuzde": float(df.loc[q, "dis_usd"]) if q in df.index else None,
               "cari_gsyh_2012_olcum_tl_yuzde": float(df.loc[q, "dis"]) if q in df.index else None}
    besli_deg = [s["kur"].get("degisim_log_yuzde") for s in satirlar if s["grup"] == "kırılgan beşli"]
    besli_deg = [v for v in besli_deg if v is not None]
    return {
        "yontem": ("22 Mayıs 2013 Bernanke ifadesinden önceki son kapanıştan 30 Ağustos 2013 kapanışına dolar "
                   "karşısında log kur değişimi (artı değer kaybı) ve 2012 cari denge/GSYH; bir vaka tablosudur, "
                   "istatistik sınaması yapılmaz."),
        "kaynak": ["em_kur_yahoo_gunluk (BRL, INR, ZAR, MXN)", "usdtry_yahoo_gunluk", "bulut: ECB referans kurları",
                   "bulut: Dünya Bankası WDI cari denge", "usdtry_tcmb_gunluk (sağlamlık)"],
        "vaka_tablosu": True, "test_degil": "n < 10: vaka tablosudur, t yazılmaz.",
        "olay": {"gun": TAPER["olay"], "saat": "10:00 New York (16:00 Orta Avrupa, 17:00 TSİ)",
                 "baz_yahoo": TAPER["baz_yahoo"], "baz_ecb": TAPER["baz_ecb"], "son": TAPER["son"]},
        "saat_notu": ("Yahoo kurları Londra gece yarısı kapanışıdır, baz olay öncesi 21.05; ECB 14:15 Orta Avrupa "
                      "sabitlemesidir, 22.05 sabitlemesi ifadeden öncedir. Yahoo serisinde cumartesi barı yok: 30.08 "
                      "cuma değeri pazartesi barının başından (hafta sonu açılışından sonra) gelir; MXN'nin o dönemki "
                      "ham barı ise gün sonu kapanışıdır. TCMB gösterge "
                      "kuru 15:30 TSİ ilanıdır; 30.08 Türkiye'de resmî tatil olduğu için son ilan 29.08'dir."),
        "n": len(satirlar), "ilk": TAPER["baz_yahoo"], "son": TAPER["son"],
        "satirlar": satirlar, "turkiye": turkiye,
        "besli_medyan_degisim_log_yuzde": float(np.median(besli_deg)) if len(besli_deg) == len(BESLI) else None,
        "besli_medyan_n": len(besli_deg),
        "besli_medyan_notu": (None if len(besli_deg) == len(BESLI) else
                              f"beşlinin yalnız {len(besli_deg)} parası ölçülebildi; medyan yazılmadı"),
    }


# ───────────────────────────────────────────────────────── Brexit 2016 (vaka)
def _brexit_ek(b: pd.Timestamp, s: pd.Timestamp) -> dict:
    """Olay satırının yanına: sterlinin avroya ve öbür beş G10 parasına karşı değişimi, doların o beşe karşı
    değişimi ve ABD kadranı (tuzak 14), Bund 10 yıllık, ECB sabitlemesiyle sterlin. Uç günler olay satırının
    günleridir (gilt ∩ CNBC sterlin); bir bacak o günü taşımıyorsa o bacak kurulmaz, öbürleri yazılır."""
    out: dict = {}
    sep = oo.dolar_sepeti()
    if b in sep.index and s in sep.index:
        d = (sep.loc[s] - sep.loc[b]) * 100                      # dolar yönünde log %, artış doların değer kazancı
        dolar_bes = float(d[G10_OBUR].mean())
        sterlin_dolar = float(-d["usd_gbp"])
        out["sterlin_ayrisimi"] = {
            "d_sterlin_dolar_yuzde": sterlin_dolar,
            "d_sterlin_bes_g10_yuzde": sterlin_dolar + dolar_bes,
            "d_dolar_bes_g10_yuzde": dolar_bes,
            "d_sterlin_avro_yuzde": sterlin_dolar + float(d["usd_eur"]),
            "d_yen_dolar_yuzde": float(-d["usd_jpy"]),
            "ozdeslik": "sterlin/dolar = sterlin/beş G10 − dolar/beş G10",
            "yontem": ("CNBC New York 17:00 kurlarının log değişimi (yüzde); beş G10: avro, Avustralya doları, "
                       "İsviçre frangı, yen, Kanada doları, eşit ağırlıklı. Eksi değer sterlinin değer kaybıdır."),
        }
        us10 = oo.oku("abd_hazine_gunluk")["us10"]
        if b in us10.index and s in us10.index:
            d_us10 = float((us10.loc[s] - us10.loc[b]) * 100)
            out["abd"] = {"d_us10_bp": d_us10, "d_dolar_bes_g10_yuzde": dolar_bes,
                          "kadran": oo.kadran(d_us10, dolar_bes, "guvenli_liman"),
                          "not": "ABD 10 yıllık New York öğleden sonra kotasyonu (≈15:30), dolar New York 17:00."}
        else:
            out["abd"] = kurulmadi("ABD 10 yıllık getirisi pencerenin uç günlerini taşımıyor")
    else:
        out["sterlin_ayrisimi"] = kurulmadi("CNBC G10 kurları pencerenin uç günlerini taşımıyor")
    av = oo.oku("cnbc_avrupa_getiri_gunluk")["de10y"].dropna()
    av = av[av.index.dayofweek < 5]
    if b in av.index and s in av.index:
        out["bund_10y"] = {"bas": float(av.loc[b]), "son": float(av.loc[s]),
                           "d_bp": float((av.loc[s] - av.loc[b]) * 100),
                           "kaynak": "CNBC Alman 10 yıllık gösterge"}
    else:
        out["bund_10y"] = kurulmadi("Alman 10 yıllık getirisi pencerenin uç günlerini taşımıyor")
    try:
        x = bulut.ecb_kur("USD") / bulut.ecb_kur("GBP")          # sterlin/dolar = (EUR/USD)/(EUR/GBP)
    except bulut.VeriYok as hata:
        out["ecb_saglamlik"] = kurulmadi(str(hata))
    else:
        if b in x.index and s in x.index:
            out["ecb_saglamlik"] = {"baz_gun": _iso(b), "son_gun": _iso(s), "baz": float(x.loc[b]),
                                    "son": float(x.loc[s]),
                                    "d_sterlin_dolar_yuzde": float(100 * math.log(x.loc[s] / x.loc[b])),
                                    "kaynak": "ECB referans kuru çaprazı sterlin/dolar (14:15 Orta Avrupa)"}
        else:
            out["ecb_saglamlik"] = kurulmadi("ECB sterlin ya da dolar kurunda pencere uç günü yok")
    return out


def vaka_brexit_2016() -> dict:
    satirlar = []
    for o in BREXIT:
        r = b05._olay_igb(o)
        if "kadran" in r:                                       # olay satırı kuruldu: gilt ve sterlin uç günleri var
            b, s = pd.Timestamp(r["ilk"]), pd.Timestamp(r["son"])
            g10, k = bulut.gilt()["gb10y"], oo.cnbc_kur()["gbp"]
            r["kadran_adi"] = oo.KADRAN_ADI_DM.get(r["kadran"], r["kadran"])
            r.update({"gilt_10y_bas": _f(g10.get(b)), "gilt_10y_son": _f(g10.get(s)),
                      "sterlin_bas": _f(k.get(b)), "sterlin_son": _f(k.get(s))})
            r.update(_brexit_ek(b, s))
            if r.get("bund_10y", {}).get("d_bp") is not None:
                r["d_gilt_bund_10y_bp"] = r["d_gb10y_bp"] - r["bund_10y"]["d_bp"]
        satirlar.append(r)
    try:
        w = bulut.wdi("cari")
    except bulut.VeriYok as hata:
        cari = kurulmadi(str(hata))
    else:
        v = w["GBR"].get(pd.Timestamp(BREXIT_CARI_YIL)) if "GBR" in w.columns else None
        cari = (kurulmadi(f"Dünya Bankası dosyasında İngiltere'nin {BREXIT_CARI_YIL[:4]} değeri yok") if v is None or pd.isna(v)
                else {"yil": int(BREXIT_CARI_YIL[:4]), "deger_yuzde": float(v),
                      "kaynak": "Dünya Bankası WDI, cari denge (% GSYH)"})
    ana = [r for r in satirlar if "kadran" in r and not r["alt_pencere"]]
    return {
        "yontem": ("23 Haziran 2016 AB referandumundan önceki kapanıştan pencerenin son kapanışına gilt 2, 10 ve 30 "
                   "yıllık getirisinin değişimi (baz puan) ve sterlinin dolar karşısında log değişimi (yüzde; eksi "
                   "değer kaybı); kadran uzun faizin ve paranın değerinin birlikte yönüdür (Bölüm 5'teki İngiltere "
                   "olay satırıyla aynı tanım). Bir vaka satırıdır, istatistik sınaması yapılmaz."),
        "kaynak": ["bulut: gilt (CNBC, Londra kapanışı)", "cnbc_kur_gunluk (New York 17:00)",
                   "cnbc_avrupa_getiri_gunluk (Bund)", "abd_hazine_gunluk", "yahoo_dxy_vix_gunluk (VIX)",
                   "bulut: ECB referans kurları (sağlamlık)", "bulut: Dünya Bankası WDI cari denge"],
        "vaka_tablosu": True, "test_degil": "tek olay: vaka satırıdır, t yazılmaz.",
        "olay": {"gun": "2016-06-23", "saat": "sandıklar 22:00 Londra (17:00 New York); sonuçlar gece",
                 "baz": BREXIT[0]["baslangic"], "tepki": BREXIT[0]["bitis"]},
        "saat_notu": BREXIT_SAAT,
        "kadran_adlari": oo.KADRAN_ADI_DM,
        "n": len(ana), "n_satir": len([r for r in satirlar if "kadran" in r]),
        "ilk": BREXIT[0]["baslangic"], "son": max(o["bitis"] for o in BREXIT),
        "satirlar": satirlar,
        "cari_gsyh_onceki_yil": cari,
    }


# ───────────────────────────────────────────────────────── giriş
def olc() -> dict:
    out = {"p8a": p8a(), "p8b": p8b(), "p8c": p8c(), "p8d": p8d(), "vaka_brexit_2016": vaka_brexit_2016(),
           "sekil_13": sekil_13(), "sekil_14": sekil_14(), "sekil_15": sekil_15()}
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"\n{time.monotonic() - t0:.1f} sn")
