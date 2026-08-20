"""Altın fiyat etkisinden arındırma sistemi.

Rezervdeki günlük değişimin ne kadarı gerçek bir döviz alım/satımı, ne kadarı
yalnızca elde duran altının yeniden değerlenmesi? Bu modül o ayrımı yapar.

--------------------------------------------------------------------------
1. AYRIŞTIRMA (Laspeyres)
--------------------------------------------------------------------------
Altın değeri V(t) = Q(t) · P(t)   (Q = miktar, milyon troy ons; P = USD/ons)

    Γ(L) = Q(L)   · [P(L+1) − P(L)]      ← FİYAT etkisi (milyar USD)
    Λ(L) = P(L+1) · [Q(L+1) − Q(L)]      ← MİKTAR etkisi (milyar USD)
    Γ + Λ = V(L+1) − V(L)                ← kimlik, artık yok

Laspeyres, taban ağırlıklı standart ayrıştırmadır; ECB'nin rezerv değerleme
kutusundaki formül tam olarak budur. (Eskiden burada "ECB ve IMF COFER'in
resmi uygulaması" yazıyordu — COFER atfı YANLIŞTI: COFER resmi döviz
rezervlerinin PARA KOMPOZİSYONU istatistiğidir ve altını kapsamaz.)
Simetrik (Bennet) varyant tanı olarak da hesaplanır:
    Γ_B(L) = ½·[Q(L) + Q(L+1)] · [P(L+1) − P(L)]
İkisinin farkı tam olarak −½·ΔQ·ΔP'dir ve günlük 0,01 milyar USD altındadır;
eşiği aşarsa miktar serisinde bozulma var demektir → görünür uyarı.

ZİNCİRLEME TANISI. Laspeyres zinciri "gezinir": günlük fiyat etkilerinin
toplamı, çıpa miktarıyla hesaplanan doğrudan fiyat etkisine eşit değildir.
    D_T = Σ Γ(t) − Q(çıpa)·[P(T) − P(çıpa)]
D_T, miktar ile fiyatın BİRLİKTE hareket ettiği ölçüde büyür. Yayımlanmaz ama
denetlenir: birikimli akımın yanında büyük kalırsa Q ara değerinin bozulduğu
ya da altın stokunun fiyatla ilişkili biçimde değiştiği anlamına gelir.

--------------------------------------------------------------------------
2. ETİKET KONVANSİYONU (ÖNEMLİ)
--------------------------------------------------------------------------
Bütün AKIM serileri `L` ile etiketlenir ve `L → L+1` (bir sonraki iş günü)
değişimini taşır. Seviye serileri `t` ile etiketlenir ve o günün seviyesidir.
Sonuç: rezerv serisi son veri gününe kadar gelirken akım serisi bir iş günü
geride biter. (İleri hiza ile geri hiza arasındaki fark ölçüldü; ileri hiza
belirgin şekilde doğru.) Bu yüzden `ozet.json`'da `ak_tarih` ile `p_tarih`
birbirinden farklıdır ve bu bir hata değildir.

--------------------------------------------------------------------------
3. NET DÖVİZ ALIMI — İKİ TANIM BİRDEN
--------------------------------------------------------------------------
    N_fp(L) = Δswap_haric(L→L+1) − Δ[kamu döviz mevduatı](L→L+1) − Γ(L)
    N(L)    = N_fp(L) − Λ(L)

`N_fp` = "altın FİYAT etkisi hariç". Piyasa tablolarının standart tanımıdır:
altının yeniden değerlenmesini dışlar ama TCMB'nin altın ALIMLARINI akımda
bırakır (altın da bir rezerv varlığıdır). Başrolde bu durur.

`N`    = "altın tamamen hariç". Yalnız döviz bacağının akımı.

Kamu ve diğer döviz mevduatı (analitik bilanço P.1ba) akımdan düşülür:
Hazine'nin TCMB'deki hesabına giren/çıkan döviz TCMB'nin piyasa işlemi
değildir. Seviye tanımından ise düşülmez (bkz. net_rezerv.py).

--------------------------------------------------------------------------
4. MİKTAR SERİSİ Q — üç kademeli, hepsi resmi
--------------------------------------------------------------------------
  1) Haftalık IRFCL tablosunun "—(saf) milyon troy ons" satırı
     (irfcl_gozlem.csv, `mn_ons` sütunu)            → kaynak "irfcl_pdf"
  2) İma edilen miktar  Q_ima(F) = TP.AB.C1(F) / P(F)
     (haftalık altın değeri ÷ aynı gün fiyat)       → kaynak "ima"
  3) Aylık IRFCL TP.REZVARPD.K11 (geri doldurma)    → kaynak "evds_aylik"

Çapalar arasında zamana göre doğrusal ara değer, son çapadan sonra taşıma.
(2) kademesinin yapısal bir üstünlüğü var: fiyat serisinin TCMB değerleme
fiyatına göre sistematik iskontosu Q_ima = V/P oranında sadeleşir, yani
Γ hesabında fiyat kaynağının seviye kayması kendiliğinden düşer.

SÜZGEÇ VE TANI. Kademe 1 çapası önce MAKULLÜK süzgecinden geçer: kabul
edilirse ima ettiği değerleme fiyatı P_deg = V/Q_pdf olur ve bunun piyasa
serisinden yüzde sekizden fazla ayrışması fiyat farkıyla açıklanamaz — o çapa
REDDEDİLİR, o hafta kademe 2'ye düşer, uyarı basılır (ölçüldü: Mart 2023
enstantanelerinde Q_pdf 30–32 mn ons okunuyor, komşu haftalarda 23; sebep
büyük olasılıkla o vintage'ın PDF düzeni).

Süzgeci geçen çapalarda |Q_pdf − Q_ima| izlenir. Eşik İKİLİDİR ve ikisi de
gereklidir: (a) ORANSAL — %2; (b) USD — 0,20 milyar. Tek başına yüzde eşik
yanıltıcıydı (25 mn ons × ~4.300 USD tabanında %2 ≈ 2,1 mlr USD'lik sahte
miktar etkisi, sistemin günlük gürültü tabanının dört katı); tek başına USD
eşiği ise ters yönde yanıltıcı — 100+ milyar dolarlık bir altın stokunda
BEKLENEN kotasyon farkı (yüzde bir buçuk) bile 1,5 milyar doları geçtiği için
her hafta "tanı" üretiyordu. İki ölçüt birlikte, beklenen farkı sessiz,
beklenmeyeni görünür bırakır. Aynı ikili mantık ardışık çapalar arasındaki
|ΔQ| sıçraması için de geçerlidir (çapa dizisi heterojendir; kaynak geçişi
tek başına milyar dolarlık bir sıçrama gibi görünür).

Tarihsel tanılar tek tek değil ÖZETLENEREK yayımlanır (son TANI_YAKIN_CAPA
çapa satır satır, öncesi sayı + en kötü örnek); ayrıntının tamamı koşu
çıktısındadır. Sebep: uyarı listesi sayfada görünen bir denetim satırıdır,
doksan satırlık bir liste hiç uyarı olmamasıyla aynı işi görür.

REVİZYON POLİTİKASI (önemli): Q ara değerle bağlandığı için son çapadan
SONRAKİ günlerin akımı GEÇİCİDİR. Yeni bir haftalık çapa geldiğinde o günler
"taşıma"dan "ara_deger"e döner, Q(t) değişir, dolayısıyla Γ(t) ve zaten
yayımlanmış olan net_doviz_alimi(t) de revize olur. Bu, tarihsel seri için
doğru davranıştır (t günü için t'den sonra yayımlanan bilgi kullanılır) ama
serinin SAĞ UCUNDAKİ değerler kesin değildir; `ons_kaynak` sütunu hangi
günlerin geçici olduğunu gösterir ve grafiklerde o günler ayrı işaretlenir.

--------------------------------------------------------------------------
5. FİYAT SERİSİ P
--------------------------------------------------------------------------
Birincil: TP.ALTINPIYASA.AGORT03 (BİST Kıymetli Madenler ağırlıklı ortalama,
USD/ons, iş günü). Yedek: TP.ALTINPIYASA.KAP03 (kapanış). Hangi günün hangi
kaynaktan geldiği `altin_fiyat_kaynak` sütununda ve `ozet.json`'da görünür.
Tatil günlerinde son iş gününün fiyatı taşınır ("ffill" olarak işaretlenir).

TANI (sessiz bayatlama dedektörü): her IRFCL gözleminde ima edilen değerleme
fiyatı P_ima = altın_değeri / ons hesaplanır ve P_ima/P_AGORT − 1 izlenir.
TCMB altını haftanın son iş günü Londra kotasyonuyla değerlediği için küçük
(yüzde bir buçuk mertebesinde) bir sistematik fark BEKLENİR; eşik %3.

--------------------------------------------------------------------------
6. BİLİNEN SINIR (kapatılmadı, yazıldı)
--------------------------------------------------------------------------
TCMB altını günlük piyasa fiyatıyla değil, haftanın/ayın son iş günü Londra
kotasyonuyla değerler. Elimizdeki günlük fiyat serisi bu referansın birebir
aynısı değildir; günlük getiri sapması yüzde yarım mertebesindedir ve 25
milyon ons tabanında günde yarım milyar dolar mertebesinde sahte akım
üretir. Bu fark bir kalibrasyon sabitiyle KAPATILMAZ — kapatmak, ölçüm
hatasını modele gömmek olur. Aylık ve daha uzun ufuklarda büyük ölçüde
birbirini götürür.

Parite (USD dışı kur) etkisi bu sürümde arındırılmaz: TCMB rezervinin para
kompozisyonu yayımlanmadığı için tahmin edilebilir ama hesaplanamaz;
mertebesi altın fiyat etkisinin kırkta biridir. Türetilemeyen bir sayıyı
koda sokmamak için tahmini bir ağırlıkla arındırma yapılmaz. Aynı gerekçe
SDR parite bacağı (Π^S) için de geçerlidir.

FAİZ GELİRİ (ρ) — ARINDIRILMIYOR, YUKARI YANLILIK BIRAKIYOR.
Tam kimlik şudur:
    N = ΔB − Γ − Λ − Π^S − s·Δq^S − Π − ρ
Uygulama Π ve Π^S'yi yukarıdaki gerekçeyle düşürüyor. ρ (rezerv portföyünün
faiz geliri + piyasa değeri değişimi) de düşürülüyor, AMA bu ihmal edilebilir
bir kalem DEĞİLDİR ve bu yüzden burada işaretiyle ve mertebesiyle yazılıyor:
  · Mertebesi yıllık 2,1–2,5 milyar USD, yani günlük ~6–7 milyon USD.
  · İŞARETİ POZİTİFTİR ve SİSTEMATİKTİR: faiz geliri rezervi büyütür ve bizim
    hesabımızda "TCMB döviz aldı" gibi görünür.
  · Çıpadan altı aylık bir pencerede bu ~1,0–1,3 milyar USD'lik YUKARI
    yanlılık demektir. Yayımlanan birikimli net alım rakamı bu kadar
    yukarıdadır; okur bunu bilerek okumalıdır.
Neden hesaplanmıyor: rezerv portföyünün vade ve enstrüman kırılımı
yayımlanmıyor; ortalama getiri ancak bir varsayımla (SOFR/SDR faiz karışımı)
kurulabilir. Kalibrasyonla kapatmak yerine YAZILDI — bu, hattın bilinen ve
kapatılmamış en büyük sistematik yanlılığıdır.

--------------------------------------------------------------------------
Kullanım
--------------------------------------------------------------------------
  python altin_etkisi.py                       # gunluk.csv'den (çevrimdışı)
  python altin_etkisi.py --capa 2026-02-27     # birikimli çıpasını değiştir
  python altin_etkisi.py --online              # EVDS + IRFCL'den taze çek
  python altin_etkisi.py --csv yol.csv         # çıktı yolu
"""

from __future__ import annotations

import argparse
import os

import pandas as pd

BURASI = os.path.dirname(os.path.abspath(__file__))
CIKTI_CSV = os.path.join(BURASI, "altin_etkisi.csv")

# --- Adlandırılmış sabitler (çıplak sayı bırakılmaz) ---------------------

# Birikimli net döviz alımının çıpası. 2026 kur şokunun hemen öncesindeki
# rezerv zirvesi; piyasa tabloları da birikimi bu tarihten sayar. --capa ile
# ezilir. DİKKAT: çıpa değişirse birikimli seri baştan hesaplanır, kaydırılmaz
# (kaydırma = sessiz bayatlama).
CIPA_TARIHI = "2026-02-27"

# |Q_pdf − Q_ima|·P eşiği — MİLYAR USD cinsinden, yüzde değil.
#
# Eskiden bu eşik %2 idi ve bu yanlış ölçekteydi: 25 milyon ons × ~4.300 USD
# tabanında %2 ≈ 2,1 milyar USD'lik sahte miktar etkisi (Λ) demektir, yani
# yakalaması gereken hatanın dört katı büyüklüğünde bir eşik. Ölçü artık
# doğrudan hatanın etkilediği büyüklükte: miktar farkının USD karşılığı
# sistemin günlük gürültü tabanının (~0,5 mlr USD) yarısını aşarsa uyarılır.
ONS_TANI_ESIK_USD = 0.20

# Kademe 1 (IRFCL PDF) miktar çapasının MAKULLÜK süzgeci ve tanı eşiği.
#
# Çapa kabul edilince ima edilen değerleme fiyatı P_deg = C1/Q_pdf olur. Bu,
# günlük piyasa serisinden sistematik olarak biraz farklı olmalıdır (farklı
# kotasyon saati; mertebe yüzde bir buçuk). AMA yüzde sekizi aşan bir fark
# fiyat farkıyla açıklanamaz: haftalık altın hareketinin kendisi bile nadiren
# o kadardır ve değerleme gecikmesi birkaç günlüktür. Böyle bir çapa, PDF
# düzeni değiştiğinde yanlış satırdan okunmuş bir miktar demektir — ölçüldü:
# Mart 2023 enstantanelerinde Q_pdf 30–32 mn ons okunuyor, komşu haftalarda
# 23; ima edilen değerleme fiyatı 1.643 USD/ons çıkıyor, o tarihte piyasa
# 1.838. Böyle bir çapa KABUL EDİLİRSE sahte bir miktar etkisi (Λ) doğurur ve
# doğrudan "net döviz alımı" barına yazılır.
#
# Süzgeç sessiz DEĞİLDİR: reddedilen her çapa uyarı üretir ve o hafta kademe 2
# (ima) çapasına düşer — yani seri kaybolmaz, yalnız güvenilir kaynağa iner.
ONS_CAPA_RED_ORAN = 0.08
# Tanı (reddetmez, yalnız uyarır): ima edilen değerleme fiyatı piyasa
# serisinden bu orandan fazla ayrışıyorsa görünür kılınır.
ONS_TANI_ESIK_ORAN = 0.02

# İki ARDIŞIK çapa arasındaki miktar sıçraması. İKİ ölçüt birlikte aranır:
#   · USD karşılığı — sıçramanın Λ'ya yazacağı etki maddi olmalı;
#   · ORANSAL büyüklük — çapa dizisi HETEROJENDİR (kademe 1/2/3 birbirini
#     izler) ve iki komşu çapa farklı kademelerdense aralarındaki fark büyük
#     ölçüde değerleme/piyasa fiyatı farkından gelir (yüzde bir buçuk mertebe
#     = 25 mn ons tabanında ~0,4 mn ons ≈ 1,6 milyar USD). Tek başına USD
#     eşiği bu KAYNAK GEÇİŞİ artefaktını "miktar sıçraması" diye raporluyordu:
#     arşiv 10'dan 47 gözleme çıkınca 60'tan fazla uyarı üretti ve denetim
#     satırı okunamaz hâle geldi. Oransal eşik artefaktın üstünde durur.
ONS_SICRAMA_ESIK_USD = 1.00
ONS_SICRAMA_ESIK_ORAN = 0.04

# Tarihsel çapa tanıları tek tek DEĞİL, özetlenerek yayımlanır: son
# TANI_YAKIN_CAPA çapa için satır satır, öncesi için tek bir özet satırı
# (sayı + en kötü örnek). Ayrıntının tamamı koşu çıktısına basılır. Gerekçe:
# uyarı listesi sayfada görünür bir denetim satırıdır; 90 satırlık bir liste
# hiç uyarı olmamasıyla aynı işi görür (alarm körlüğü).
TANI_YAKIN_CAPA = 8

# |P_ima / P_AGORT − 1| eşiği. TCMB'nin haftalık değerleme fiyatı ile günlük
# piyasa ortalaması arasında yüzde bir buçuk mertebesinde sistematik fark
# BEKLENİR (farklı kotasyon saati); %3 aşımı beslemenin donduğunu gösterir.
FIYAT_TANI_ESIK = 0.03

# |Laspeyres − Bennet| / |Laspeyres| eşiği — ORANSAL. Mutlak eşik kullanmak
# yanlış olurdu: iki ardışık iş günü arasında tatil varsa hem ΔQ hem ΔP birkaç
# güne birikir, fark da doğal olarak büyür (ör. dört günlük bir bayram
# arasında fiyat %10 oynadığında mutlak fark yarım milyar doları bulur ama
# ayrıştırma gayet sağlamdır). Oransal ölçü bu ölçek etkisinden bağımsızdır.
BENNET_TANI_ESIK = 0.10
# Oran hesabına girmesi için gereken asgari fiyat etkisi (mlr USD): Γ sıfıra
# yakınken oran anlamsız büyür.
BENNET_TABAN = 0.05

# Son çapadan sonra miktar serisinin taşınabileceği azami gün. Haftalık altın
# değeri ~6 gün gecikmeli yayımlanır; eşik 14 günken en hatalı girdiye (miktar
# serisi) İKİ HAFTA sessiz taşıma izni veriyordu. Yayın ritmi 6 gün olduğuna
# göre 8 gün, bir yayının atlanmasını yakalayacak kadar dar, tek bir gecikmeyi
# sahte uyarıya çevirmeyecek kadar geniştir.
ONS_TASIMA_UYARI_GUN = 8

# Fiyat serisinin ARDIŞIK kaç iş günü taşınabileceği (ffill). Ons tarafında
# ONS_TASIMA_UYARI_GUN vardı, fiyat tarafında karşılığı YOKTU: AGORT03 ve
# KAP03 birlikte dursa ama takvim ilerlese fiyat sessizce süresiz taşınırdı.
# net_rezerv.py'nin tazelik denetimi bunu ham seride yakalar, ama bu modül tek
# başına (gunluk.csv'den) koştuğunda o denetim devrede değildir; koruma tek
# noktaya bağlı kalmasın diye burada da bir eşik var.
FIYAT_TASIMA_UYARI_GUN = 3

# Zincirleme tanısı D_T = ΣΓ − Q(çıpa)·ΔP için eşik: birikimli akımın bu
# katından büyükse uyarı. Oransal ölçü kasıtlı — D_T'nin "büyük" olması,
# mutlak değerinden çok yayımlanan birikimli rakama göre büyüklüğüyle
# anlamlıdır (aynı D_T, üç aylık bir pencerede ciddi, üç yıllıkta önemsizdir).
ZINCIRLEME_TANI_ORAN = 0.50

# --- Hata bütçesi (raporlama kuralı) --------------------------------------
# Araştırma notunun raporlama kuralı: "sayfada tek bir nokta tahmin verilmez".
# Aşağıdaki bantlar notun hata bütçesinden gelir — bir kontrol setine
# BAKILARAK ölçülmüş sayılar DEĞİLDİR, ölçüm hatası kalemlerinin (altın
# değerleme fiyatı farkı, swap çapası, parite, faiz geliri) mertebelerinden
# türetilmiş 1σ mertebe tahminleridir. Yayımlanan her akım rakamının yanında
# görünür.
AKIM_BANT_GUNLUK = 0.40        # mlr USD; günlük ±0,3–0,5 aralığının ortası
AKIM_BANT_HAFTALIK = 0.50      # mlr USD
AKIM_BANT_AYLIK = 1.00         # mlr USD
AKIM_BANT_BIRIKIMLI_6AY = 2.00 # mlr USD; notun ±1,5–2,5 aralığının ortası

# Faiz geliri (ρ) yanlılığının mertebesi — ARINDIRILMIYOR, İLAN EDİLİYOR.
# Yıllık 2,1–2,5 milyar USD'lik rezerv getirisi, işareti POZİTİF ve
# sistematik. Kimlikten düşülmediği için yayımlanan birikimli net alım bu
# kadar YUKARI yanlıdır. Hesaba GİRMEZ; yalnız ozet.json'a ve sayfaya taşınır.
FAIZ_GELIRI_YILLIK_MLR = 2.30


# ---------------------------------------------------------------------------
# Fiyat serisi
# ---------------------------------------------------------------------------
def fiyat_serisi(agort: pd.Series, kap: pd.Series,
                 index: pd.DatetimeIndex) -> pd.DataFrame:
    """Günlük altın fiyatı (USD/ons) + hangi kaynaktan geldiği.

    Öncelik: AGORT03 (ağırlıklı ortalama) → KAP03 (kapanış) → son iş gününün
    taşınması. Taşınan günler "ffill" diye işaretlenir ki tatil mi yoksa
    besleme kesintisi mi olduğu `ozet.json`'dan görülebilsin.
    """
    a = agort.reindex(index)
    k = kap.reindex(index)
    fiyat = a.copy()
    kaynak = pd.Series(
        pd.NA, index=index, dtype="object"
    ).mask(a.notna(), "agort03")
    yedek = fiyat.isna() & k.notna()
    fiyat = fiyat.where(~yedek, k)
    kaynak = kaynak.where(~yedek, "kap03")
    tasima = fiyat.isna() & fiyat.ffill().notna()
    fiyat = fiyat.ffill()
    kaynak = kaynak.where(~tasima, "ffill")
    return pd.DataFrame({"altin_fiyat": fiyat, "altin_fiyat_kaynak": kaynak})


def fiyat_tasima_tanisi(kaynak: pd.Series) -> list[str]:
    """Fiyat serisi arka arkaya kaç iş günü taşındı? Eşiği aşarsa uyarı.

    Ons tarafındaki taşıma denetiminin fiyat karşılığı. Serinin SONUNDAKİ
    taşıma ayrıca vurgulanır: ortadaki bir taşıma tatildir, sondaki taşıma
    beslemenin durması olabilir.
    """
    uyarilar: list[str] = []
    t = (kaynak == "ffill")
    if not t.any():
        return uyarilar
    # Ardışık "ffill" blokları
    blok = (t != t.shift()).cumsum()[t]
    for _, grup in t[t].groupby(blok):
        n = len(grup)
        if n > FIYAT_TASIMA_UYARI_GUN:
            uyarilar.append(
                f"ALTIN FİYATI TAŞINDI: {grup.index[0]:%d.%m.%Y}–"
                f"{grup.index[-1]:%d.%m.%Y} arası {n} iş günü fiyat serisi "
                f"taşındı (eşik {FIYAT_TASIMA_UYARI_GUN}). AGORT03 ve KAP03 "
                "birlikte durmuş olabilir; o günlerin fiyat etkisi güvenilmez."
            )
    if t.iloc[-1]:
        son_gercek = kaynak[kaynak != "ffill"]
        if len(son_gercek):
            uyarilar.append(
                f"ALTIN FİYATI SERİNİN UCUNDA TAŞINIYOR: son gerçek kotasyon "
                f"{son_gercek.index[-1]:%d.%m.%Y}. Sağ uçtaki fiyat etkisi ve "
                "akım rakamları bu taşımaya dayanıyor."
            )
    return uyarilar


# ---------------------------------------------------------------------------
# Miktar serisi (ons)
# ---------------------------------------------------------------------------
def ons_capalari(gozlem: pd.DataFrame | None, altin_deger_M: pd.Series,
                 fiyat: pd.Series, aylik_ons: pd.Series | None
                 ) -> pd.DataFrame:
    """Üç kademeli miktar çapası tablosu — index tarih, sütun [ons, kaynak].

    Kademe 1 kademe 2'yi, kademe 2 kademe 3'ü ezer (aynı tarihte çakışırlarsa).

    Parameters
    ----------
    gozlem : irfcl_gozlem.csv (mn_ons sütunu varsa kademe 1)
    altin_deger_M : TP.AB.C1, haftalık Cuma, MİLYON USD
    fiyat : günlük altın fiyatı (USD/ons)
    aylik_ons : TP.REZVARPD.K11, aylık, milyon troy ons
    """
    kayitlar: list[pd.DataFrame] = []

    # Kademe 3 (en zayıf): aylık IRFCL
    if aylik_ons is not None and len(aylik_ons.dropna()):
        s = aylik_ons.dropna()
        kayitlar.append(pd.DataFrame({"ons": s, "kaynak": "evds_aylik",
                                      "oncelik": 1}))

    # Kademe 2: ima edilen miktar = haftalık altın değeri / aynı gün fiyat.
    # Fiyat kaynağının seviye kayması bu bölmede sadeleşir (bkz. modül notu).
    if len(altin_deger_M.dropna()):
        v = altin_deger_M.dropna()
        p = fiyat.reindex(v.index)
        ima = (v / p).dropna()
        if len(ima):
            kayitlar.append(pd.DataFrame({"ons": ima, "kaynak": "ima",
                                          "oncelik": 2}))

    # Kademe 1 (tercih): haftalık IRFCL PDF'inin yayımladığı miktar.
    # MAKULLÜK SÜZGECİ: çapa, ima ettiği değerleme fiyatı piyasa serisinden
    # ONS_CAPA_RED_ORAN'dan fazla ayrışıyorsa REDDEDİLİR (bkz. sabit yorumu).
    # Reddedilen hafta kademe 2'ye düşer; sessizce değil, uyarıyla.
    red: list[str] = []
    if gozlem is not None and "mn_ons" in gozlem.columns:
        s = pd.to_numeric(gozlem["mn_ons"], errors="coerce").dropna()
        if len(s) and len(altin_deger_M.dropna()):
            v = altin_deger_M.dropna().reindex(s.index)
            p = fiyat.reindex(s.index)
            deg_fiyat = v / s
            oran = (deg_fiyat / p - 1.0)
            kotu = oran.abs() > ONS_CAPA_RED_ORAN
            for t in s.index[kotu.fillna(False)]:
                red.append(
                    f"ONS ÇAPASI REDDEDİLDİ ({t:%d.%m.%Y}): IRFCL PDF'i "
                    f"{s.loc[t]:.3f} mn ons diyor; bu, ima edilen değerleme "
                    f"fiyatını {deg_fiyat.loc[t]:,.0f} USD/ons yapıyor, oysa "
                    f"piyasa {p.loc[t]:,.0f} (%{oran.loc[t] * 100:+.1f}, eşik "
                    f"%{ONS_CAPA_RED_ORAN * 100:.0f}). Fiyat farkıyla "
                    "açıklanamaz — PDF düzeni değişmiş olabilir. O hafta "
                    "kademe 2 (ima) çapası kullanılıyor."
                )
            s = s[~kotu.fillna(False)]
        if len(s):
            kayitlar.append(pd.DataFrame({"ons": s, "kaynak": "irfcl_pdf",
                                          "oncelik": 3}))

    if not kayitlar:
        bos = pd.DataFrame(columns=["ons", "kaynak"],
                           index=pd.DatetimeIndex([], name="tarih"))
        bos.attrs["red_uyarilari"] = red
        return bos

    tum = pd.concat(kayitlar).sort_values("oncelik")
    tum = tum[~tum.index.duplicated(keep="last")].sort_index()
    tum.index.name = "tarih"
    out = tum[["ons", "kaynak"]]
    out.attrs["red_uyarilari"] = red
    return out


def ons_serisi(capalar: pd.DataFrame,
               index: pd.DatetimeIndex) -> pd.DataFrame:
    """Çapaları günlük takvime taşır — aralarda doğrusal, sonrasında taşıma.

    Miktar, fiyattan farklı olarak yavaş değişen bir stoktur; iki yayım
    arasını doğrusal bağlamak basamak fonksiyonundan biraz daha isabetlidir
    (fark ölçüldü: ihmal edilebilir) ve çapa gününde tam kapanır.
    İlk çapadan ÖNCE geriye uzatma YOK — NaN bırakılır.
    """
    if capalar.empty:
        return pd.DataFrame({"ons": pd.Series(index=index, dtype=float),
                             "ons_kaynak": pd.Series(index=index,
                                                     dtype="object")})
    q = capalar["ons"].astype(float)
    birlesik = q.reindex(q.index.union(index)).sort_index()
    ara = birlesik.interpolate(method="time", limit_area="inside")
    ara = ara.reindex(index)
    son_t = q.index[-1]
    ara[index > son_t] = q.iloc[-1]          # taşıma (basamak)
    ara[index < q.index[0]] = float("nan")   # geriye uzatma yok

    kaynak = pd.Series("ara_deger", index=index, dtype="object")
    kaynak[ara.isna()] = pd.NA
    kaynak[index > son_t] = "tasima"
    ortak = capalar.index.intersection(index)
    kaynak.loc[ortak] = capalar.loc[ortak, "kaynak"].values
    return pd.DataFrame({"ons": ara, "ons_kaynak": kaynak})


# ---------------------------------------------------------------------------
# Ayrıştırma
# ---------------------------------------------------------------------------
def altin_fiyat_etkisi(ons: pd.Series, fiyat: pd.Series) -> pd.DataFrame:
    """Laspeyres fiyat/miktar ayrıştırması. Etiket L, değer L→L+1 (mlr USD).

    Dönen sütunlar:
      altin_fiyat_etkisi   Γ(L) = Q(L)·ΔP
      altin_miktar_etkisi  Λ(L) = P(L+1)·ΔQ
      altin_deger_ima      V(L) = Q(L)·P(L)   (tanı; rezervdeki altın kalemi
                           bundan biraz farklıdır, oradaki değerleme fiyatı
                           TCMB'nin haftalık kotasyonudur)
      bennet_fark          |Γ_Laspeyres − Γ_Bennet|  (tanı)
    """
    q = ons.astype(float)
    p = fiyat.astype(float)
    dp = p.shift(-1) - p
    dq = q.shift(-1) - q
    gamma = q * dp / 1000.0
    lam = p.shift(-1) * dq / 1000.0
    bennet = (q + q.shift(-1)) / 2.0 * dp / 1000.0
    return pd.DataFrame({
        "altin_fiyat_etkisi": gamma,
        "altin_miktar_etkisi": lam,
        "altin_deger_ima": q * p / 1000.0,
        "bennet_fark": (gamma - bennet).abs(),
    })


def net_doviz_alimi(swap_haric: pd.Series, kamu_doviz_usd: pd.Series,
                    gamma: pd.Series, lam: pd.Series) -> pd.DataFrame:
    """Günlük net döviz alımı/satımı — iki tanım. Etiket L, değer L→L+1.

    net_doviz_alimi              N_fp = Δswap_haric − Δkamu − Γ
    net_doviz_alimi_altin_haric  N    = N_fp − Λ
    """
    d_seviye = swap_haric.shift(-1) - swap_haric
    d_kamu = kamu_doviz_usd.shift(-1) - kamu_doviz_usd
    n_fp = d_seviye - d_kamu - gamma
    return pd.DataFrame({
        "net_doviz_alimi": n_fp,
        "net_doviz_alimi_altin_haric": n_fp - lam,
    })


def birikimli_akim(akim: pd.Series, cipa: str = CIPA_TARIHI) -> pd.Series:
    """Çıpadan itibaren zincirlenmiş birikim. Etiket akım serisiyle aynı (L).

    birikimli(L) = Σ akim(s),  çıpa ≤ s ≤ L
    yani "çıpa gününden L+1 iş gününe kadar biriken net döviz alımı".

    Çıpa günü seride yoksa SESSİZCE en yakın güne kaydırılmaz: görünür hata
    verilir. Kaydırma, birikimli serinin sessizce yeniden tabanlanması demek
    olurdu.
    """
    t0 = pd.Timestamp(cipa)
    gecerli = akim.dropna()
    if gecerli.empty:
        raise RuntimeError("Akım serisi boş; birikimli hesaplanamaz.")
    if t0 < gecerli.index[0] or t0 > gecerli.index[-1]:
        raise RuntimeError(
            f"Çıpa tarihi {t0:%d.%m.%Y} akım serisinin dışında "
            f"({gecerli.index[0]:%d.%m.%Y}–{gecerli.index[-1]:%d.%m.%Y}). "
            "Seriyi geriye uzatın (--daily-start) ya da --capa değiştirin."
        )
    if t0 not in akim.index:
        raise RuntimeError(
            f"Çıpa tarihi {t0:%d.%m.%Y} bir iş günü değil ya da o gün veri "
            "yok. En yakın güne kaydırma yapılmaz; geçerli bir iş günü verin."
        )
    pencere = akim.copy()
    pencere[pencere.index < t0] = float("nan")
    return pencere.cumsum()


# ---------------------------------------------------------------------------
# Tanılar
# ---------------------------------------------------------------------------
def altin_tanilari(capalar: pd.DataFrame, altin_deger_M: pd.Series,
                   fiyat: pd.Series, etki: pd.DataFrame,
                   bugun: pd.Timestamp | None = None) -> list[str]:
    """Altın tarafının sessiz bayatlama denetimleri — uyarı metinleri döner."""
    uyarilar: list[str] = []

    # ons_capalari'nin reddettiği çapalar (makullük süzgeci) — her biri görünür.
    uyarilar += list(capalar.attrs.get("red_uyarilari", []))

    yakin = set(capalar.index[-TANI_YAKIN_CAPA:])

    def _yayimla(baslik: str, kalemler: list[tuple[pd.Timestamp, float, str]]
                 ) -> None:
        """Yakın çapaları satır satır, eskileri tek özet satırıyla yayımlar."""
        if not kalemler:
            return
        eski = [k for k in kalemler if k[0] not in yakin]
        for t, _, metin in kalemler:
            if t in yakin:
                uyarilar.append(metin)
            else:
                print("  [tarihsel tanı] " + metin)
        if eski:
            en_kotu = max(eski, key=lambda k: abs(k[1]))
            uyarilar.append(
                f"{baslik} — {len(eski)} TARİHSEL çapada (son "
                f"{TANI_YAKIN_CAPA} çapanın dışında); en büyüğü "
                f"{en_kotu[0]:%d.%m.%Y}, {abs(en_kotu[1]):.2f} mlr USD. "
                "Ayrıntı koşu çıktısında."
            )

    # (1) Yayımlanan ons ile ima edilen ons tutuyor mu? İKİ ölçüt birlikte:
    # (a) ima edilen DEĞERLEME fiyatı piyasa serisinden oransal olarak ne kadar
    # ayrışıyor — yüzde bir buçuk mertebesindeki fark BEKLENİR, çünkü TCMB
    # haftanın son iş günü kotasyonuyla değerler; (b) farkın Λ'ya yazacağı USD
    # etkisi maddi mi. Yalnız USD ölçütü kullanmak, 100+ milyar dolarlık bir
    # altın stokunda BEKLENEN fiyat farkını her hafta "tanı" diye raporlardı.
    pdf = capalar[capalar["kaynak"] == "irfcl_pdf"]["ons"]
    kalem_ons: list[tuple[pd.Timestamp, float, str]] = []
    for t, q_pdf in pdf.items():
        v = altin_deger_M.reindex([t]).iloc[0]
        p = fiyat.reindex([t]).ffill().iloc[0] if t in fiyat.index else None
        if pd.isna(v) or p is None or pd.isna(p) or not q_pdf:
            continue
        q_ima = v / p
        sapma_usd = abs(q_pdf - q_ima) * p / 1000.0     # milyar USD
        sapma_oran = abs(q_pdf / q_ima - 1.0) if q_ima else 0.0
        if sapma_usd > ONS_TANI_ESIK_USD and sapma_oran > ONS_TANI_ESIK_ORAN:
            kalem_ons.append((t, sapma_usd, (
                f"ALTIN MİKTAR TANISI ({t:%d.%m.%Y}): yayımlanan ons "
                f"{q_pdf:.3f} ile ima edilen ons {q_ima:.3f} arasındaki fark "
                f"%{sapma_oran * 100:.1f}, yani {sapma_usd:.2f} mlr USD'lik "
                f"sahte miktar etkisi (eşikler %{ONS_TANI_ESIK_ORAN * 100:.0f} "
                f"ve {ONS_TANI_ESIK_USD:.2f} mlr USD). Fiyat kaynağı kaymış ya "
                "da PDF ayrıştırıcısı bozulmuş olabilir.")))
    _yayimla("ALTIN MİKTAR TANISI", kalem_ons)

    # (1b) Ardışık çapalar arasındaki miktar SIÇRAMASI: gerçek altın alımı mı,
    # fiyat kaynağının kayması mı? İkisi ayırt edilmeden Λ'ya yazılmamalı.
    # Ölçüt yine ikili (bkz. ONS_SICRAMA_ESIK_ORAN): heterojen çapa dizisinde
    # kaynak geçişi tek başına milyar dolarlık bir "sıçrama" gibi görünür.
    q_capa = capalar["ons"].astype(float).dropna()
    kalem_sic: list[tuple[pd.Timestamp, float, str]] = []
    if len(q_capa) >= 2:
        onceki = q_capa.shift(1)
        for t, dq in q_capa.diff().dropna().items():
            p = fiyat.reindex([t]).ffill().iloc[0] if t in fiyat.index else None
            if p is None or pd.isna(p) or not onceki.loc[t]:
                continue
            sicrama = abs(dq) * p / 1000.0
            oran = abs(dq / onceki.loc[t])
            if sicrama > ONS_SICRAMA_ESIK_USD and oran > ONS_SICRAMA_ESIK_ORAN:
                kalem_sic.append((t, sicrama, (
                    f"ALTIN MİKTAR SIÇRAMASI ({t:%d.%m.%Y}): iki çapa arasında "
                    f"miktar {dq:+.3f} mn ons değişti (%{oran * 100:.1f}, "
                    f"{sicrama:.2f} mlr USD; eşikler "
                    f"%{ONS_SICRAMA_ESIK_ORAN * 100:.0f} ve "
                    f"{ONS_SICRAMA_ESIK_USD:.2f}, kaynak "
                    f"{capalar.loc[t, 'kaynak']}). Bu gerçek bir altın "
                    "alım/satımı mı, yoksa fiyat kaynağının kayması mı — "
                    "miktar etkisi (Λ) buna göre okunmalı.")))
    _yayimla("ALTIN MİKTAR SIÇRAMASI", kalem_sic)

    # (2) İma edilen değerleme fiyatı piyasa fiyatından ne kadar sapıyor?
    for t in capalar.index[-8:]:
        v = altin_deger_M.reindex([t]).iloc[0]
        q = capalar.loc[t, "ons"]
        p = fiyat.reindex([t]).iloc[0] if t in fiyat.index else None
        if pd.isna(v) or pd.isna(q) or not q or p is None or pd.isna(p):
            continue
        p_ima = v / q
        sapma = abs(p_ima / p - 1.0)
        if sapma > FIYAT_TANI_ESIK:
            uyarilar.append(
                f"ALTIN FİYAT TANISI ({t:%d.%m.%Y}): ima edilen değerleme "
                f"fiyatı {p_ima:,.0f} USD/ons, piyasa serisi {p:,.0f} "
                f"(%{sapma * 100:.1f} sapma, eşik "
                f"%{FIYAT_TANI_ESIK * 100:.0f}). Fiyat beslemesi donmuş ya da "
                "TCMB değerleme referansını değiştirmiş olabilir."
            )

    # (3) Laspeyres ile Bennet ayrışıyor mu? (oransal — bkz. BENNET_TANI_ESIK)
    if {"bennet_fark", "altin_fiyat_etkisi"} <= set(etki.columns):
        g = etki["altin_fiyat_etkisi"].abs()
        oran = (etki["bennet_fark"] / g).where(g > BENNET_TABAN).dropna()
        if len(oran) and oran.max() > BENNET_TANI_ESIK:
            t = oran.idxmax()
            uyarilar.append(
                f"AYRIŞTIRMA TANISI ({t:%d.%m.%Y}): Laspeyres ile Bennet "
                f"fiyat etkisi %{oran.max() * 100:.1f} ayrışıyor (eşik "
                f"%{BENNET_TANI_ESIK * 100:.0f}). Miktar serisinde sıçrama var."
            )

    # (4) Miktar çapası ne kadar eskidi?
    # DİKKAT: referans DUVAR SAATİDİR. Eskiden çağıran taraf `bugun=son_veri`
    # geçiyordu; son_veri'yi de aynı besleme belirlediği için yaş yapay olarak
    # küçülüyor, denetim körleşiyordu. `bugun` yalnız testler için parametrik.
    if not capalar.empty:
        son = capalar.index[-1]
        ref = bugun if bugun is not None else pd.Timestamp.today().normalize()
        yas = (ref - son).days
        if yas > ONS_TASIMA_UYARI_GUN:
            uyarilar.append(
                f"ALTIN MİKTAR TAZELİĞİ: son çapa {son:%d.%m.%Y} ({yas} gün "
                f"önce, eşik {ONS_TASIMA_UYARI_GUN}). Miktar o günden beri "
                "taşınıyor; haftalık altın değeri yayımı kesilmiş olabilir."
            )
    return uyarilar


def zincirleme_tanisi(gamma: pd.Series, ons: pd.Series, fiyat: pd.Series,
                      cipa: str) -> tuple[float | None, list[str]]:
    """D_T = Σ Γ(t) − Q(çıpa)·[P(T) − P(çıpa)] — zincirleme sapması.

    Laspeyres zinciri "gezinir": günlük fiyat etkilerinin toplamı, çıpa
    miktarıyla hesaplanan doğrudan fiyat etkisine eşit değildir. Aradaki fark
    miktar ile fiyatın BİRLİKTE hareket ettiği ölçüde büyür — yani D_T,
    Q ara değerinin bozulup bozulmadığını sınayan doğrudan bir göstergedir.

    Yayımlanmaz; büyüdüğünde uyarı olarak görünür. (Bunun bir hata olduğu
    iddiası YOK: zincirleme sapması Laspeyres'in bilinen bir özelliğidir.
    İzlenmesinin sebebi, aynı büyüklüğün Q serisindeki bir bozulmayla da
    şişmesidir.)
    """
    t0 = pd.Timestamp(cipa)
    g = gamma.dropna()
    g = g[g.index >= t0]
    if g.empty or t0 not in ons.index:
        return None, []
    son = g.index[-1]
    p0, q0 = fiyat.get(t0), ons.get(t0)
    p_t = fiyat.get(son)
    if pd.isna(p0) or pd.isna(q0) or pd.isna(p_t):
        return None, []
    d_t = float(g.sum() - q0 * (p_t - p0) / 1000.0)
    uyarilar: list[str] = []
    # Ölçek referansı: aynı pencerede biriken fiyat etkisinin büyüklüğü.
    olcek = abs(float(g.sum()))
    if olcek > 0 and abs(d_t) > ZINCIRLEME_TANI_ORAN * olcek:
        uyarilar.append(
            f"ZİNCİRLEME TANISI: Σ Γ ({g.sum():+.2f}) ile çıpa miktarıyla "
            f"hesaplanan doğrudan fiyat etkisi ({q0 * (p_t - p0) / 1000.0:+.2f}) "
            f"arasında D_T = {d_t:+.2f} mlr USD sapma var (pencere "
            f"{t0:%d.%m.%Y}–{son:%d.%m.%Y}). Miktar ile fiyat birlikte hareket "
            "ediyor ya da Q ara değeri bozulmuş olabilir."
        )
    return d_t, uyarilar


# ---------------------------------------------------------------------------
# Tek çağrılık boru hattı (net_rezerv.py bunu kullanır)
# ---------------------------------------------------------------------------
def arindirma_hatti(index: pd.DatetimeIndex, agort: pd.Series, kap: pd.Series,
                    altin_deger_M: pd.Series, aylik_ons: pd.Series | None,
                    gozlem: pd.DataFrame | None, swap_haric: pd.Series,
                    kamu_doviz_usd: pd.Series,
                    cipa: str = CIPA_TARIHI) -> tuple[pd.DataFrame, list[str]]:
    """Fiyat + miktar + ayrıştırma + akım + birikim — tek çağrıda.

    Dönen DataFrame sütunları:
      altin_fiyat, altin_fiyat_kaynak, ons, ons_kaynak,
      altin_fiyat_etkisi, altin_miktar_etkisi, altin_deger_ima, bennet_fark,
      net_doviz_alimi, net_doviz_alimi_altin_haric, net_doviz_alimi_birikimli,
      altin_fiyat_etkisi_birikimli
    """
    f = fiyat_serisi(agort, kap, index)
    capalar = ons_capalari(gozlem, altin_deger_M, f["altin_fiyat"], aylik_ons)
    q = ons_serisi(capalar, index)
    etki = altin_fiyat_etkisi(q["ons"], f["altin_fiyat"])
    akim = net_doviz_alimi(swap_haric, kamu_doviz_usd,
                           etki["altin_fiyat_etkisi"],
                           etki["altin_miktar_etkisi"])

    out = pd.concat([f, q, etki, akim], axis=1)
    try:
        out["net_doviz_alimi_birikimli"] = birikimli_akim(
            out["net_doviz_alimi"], cipa)
        out["altin_fiyat_etkisi_birikimli"] = birikimli_akim(
            out["altin_fiyat_etkisi"], cipa)
        uyari_cipa: list[str] = []
    except RuntimeError as e:
        out["net_doviz_alimi_birikimli"] = float("nan")
        out["altin_fiyat_etkisi_birikimli"] = float("nan")
        uyari_cipa = [f"BİRİKİMLİ AKIM ÜRETİLEMEDİ: {e}"]

    # Akımın hangi günlerinin GEÇİCİ olduğu (son çapadan sonrası) — grafikler
    # ve sayfa bunu görünür kılar; revizyon politikası modül notunda.
    son_capa = capalar.index[-1] if not capalar.empty else None
    out["akim_gecici"] = (pd.Series(index > son_capa, index=index)
                          if son_capa is not None
                          else pd.Series(False, index=index))

    # DİKKAT: tazelik/taşıma tanılarında referans DUVAR SAATİDİR; verinin son
    # gününü referans almak denetimi kendi kendine referanslı hâle getirirdi.
    uyarilar = altin_tanilari(capalar, altin_deger_M, f["altin_fiyat"], etki)
    uyarilar += fiyat_tasima_tanisi(f["altin_fiyat_kaynak"])
    uyarilar += uyari_cipa

    # Zincirleme tanısı (yayımlanmaz, denetlenir) — bkz. zincirleme_tanisi.
    d_t, uyari_zincir = zincirleme_tanisi(etki["altin_fiyat_etkisi"],
                                          q["ons"], f["altin_fiyat"], cipa)
    uyarilar += uyari_zincir
    out.attrs["zincirleme_dt"] = d_t
    out.attrs["son_ons_capa"] = son_capa
    return out, uyarilar


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _gunlukten_uret(gunluk: pd.DataFrame, cipa: str) -> pd.DataFrame:
    """gunluk.csv'deki girdilerden ayrıştırmayı YENİDEN hesaplar.

    Sadece net_rezerv.py'nin yazdığı sütunları kopyalamaz; Γ, Λ ve akımı
    burada yeniden kurar. Böylece bu modül tek başına çalıştığında (ör. farklı
    bir --capa ile) gerçekten kendi hesabını yapar.
    """
    gerekli = ["altin_fiyat", "altin_fiyat_kaynak", "ons", "ons_kaynak",
               "swap_haric_usd", "kamu_doviz_mev_usd", "altin_usd",
               "doviz_usd"]
    eksik = [c for c in gerekli if c not in gunluk.columns]
    if eksik:
        raise RuntimeError(
            "gunluk.csv beklenen sütunları taşımıyor: " + ", ".join(eksik) +
            ". Önce `python net_rezerv.py` koşturun."
        )
    etki = altin_fiyat_etkisi(gunluk["ons"], gunluk["altin_fiyat"])
    akim = net_doviz_alimi(gunluk["swap_haric_usd"],
                           gunluk["kamu_doviz_mev_usd"],
                           etki["altin_fiyat_etkisi"],
                           etki["altin_miktar_etkisi"])
    out = pd.DataFrame(index=gunluk.index)
    out["altin_ons_mn"] = gunluk["ons"]
    out["altin_fiyat"] = gunluk["altin_fiyat"]
    out["altin_fiyat_kaynak"] = gunluk["altin_fiyat_kaynak"]
    out["ons_kaynak"] = gunluk["ons_kaynak"]
    # İKİ FARKLI ALTIN DEĞERİ KAVRAMI — adları bunu söylüyor (eskiden tek bir
    # `altin_deger` sütunu vardı ve hangisi olduğu yazmıyordu):
    #   altin_deger_seviye : TCMB'nin haftalık değerleme ÇAPASINA oturan
    #                        oransal seri, C1(F)·P(t)/P(F). Rezerv tablosundaki
    #                        altın kaleminin günlük izidir.
    #   altin_deger_ima    : Q(t)·P(t), yani miktar × piyasa fiyatı. Γ ve Λ
    #                        AYRIŞTIRMASI BU SERİ ÜZERİNDEN yapılır.
    # Kimlik Γ + Λ = ΔV yalnız `altin_deger_ima` için makine hassasiyetinde
    # kapanır; `altin_deger_seviye` ile denenirse milyar dolarlık artık verir.
    # İkisi arasındaki fark, günlük piyasa fiyatı ile TCMB'nin haftalık
    # değerleme kotasyonu arasındaki iskontodur — kasıtlı olarak ayrı
    # tutulmuştur, çünkü çapa yenileme sıçraması akıma sızmasın istiyoruz.
    out["altin_deger_seviye"] = gunluk["altin_usd"]
    out["altin_deger_ima"] = etki["altin_deger_ima"]
    out["altin_fiyat_etkisi"] = etki["altin_fiyat_etkisi"]
    out["altin_miktar_etkisi"] = etki["altin_miktar_etkisi"]
    out["doviz_rezerv"] = gunluk["doviz_usd"]
    if "swap_capa_revizyon" in gunluk.columns:
        # Swap çapası yenilendiğinde akıma giren revizyon — TCMB işlemi DEĞİL.
        out["swap_capa_revizyon"] = gunluk["swap_capa_revizyon"]
    out["net_alim_satim"] = akim["net_doviz_alimi"]
    out["net_alim_satim_altin_haric"] = akim["net_doviz_alimi_altin_haric"]
    out["kumulatif"] = birikimli_akim(out["net_alim_satim"], cipa)
    out.index.name = "tarih"
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capa", "--cipa", dest="capa", default=CIPA_TARIHI,
                    help=f"birikimli akım çıpası, YYYY-AA-GG "
                         f"(varsayılan {CIPA_TARIHI})")
    ap.add_argument("--online", action="store_true",
                    help="gunluk.csv yerine EVDS + IRFCL'den taze çek")
    ap.add_argument("--start", default="01-01-2023",
                    help="--online için seri başlangıcı (gg-aa-yyyy)")
    ap.add_argument("--gunluk-csv", default=os.path.join(BURASI, "gunluk.csv"))
    ap.add_argument("--csv", default=CIKTI_CSV, help="çıktı CSV yolu")
    ap.add_argument("--pencere", type=int, default=15,
                    help="ekrana basılacak son gün sayısı")
    args = ap.parse_args()

    if args.online:
        # Gecikmeli içe alma: net_rezerv.py bu modülü içe aldığı için üst
        # düzeyde import edilirse döngü olur.
        import net_rezerv as nr
        gunluk = nr.hat_kos(args.start, cipa=args.capa)["gunluk"]
    else:
        if not os.path.exists(args.gunluk_csv):
            raise RuntimeError(
                f"{args.gunluk_csv} yok. Önce `python net_rezerv.py` koşturun "
                "ya da --online verin."
            )
        gunluk = pd.read_csv(args.gunluk_csv, index_col=0, parse_dates=True)

    out = _gunlukten_uret(gunluk, args.capa)

    gecerli = out["net_alim_satim"].dropna()
    print(f"=== Altın fiyat etkisinden arındırılmış net döviz alımı/satımı ===")
    print(f"  Çıpa: {pd.Timestamp(args.capa):%d.%m.%Y}   "
          f"Akım serisi: {gecerli.index[0]:%d.%m.%Y} → "
          f"{gecerli.index[-1]:%d.%m.%Y} ({len(gecerli)} gün)")
    print(f"  Çıpadan birikimli: {out['kumulatif'].dropna().iloc[-1]:+.2f} "
          f"± {AKIM_BANT_BIRIKIMLI_6AY:.1f} milyar USD  "
          f"(bant ölçüm hatası bütçesinden; birikimli rakam kendi belirsizlik "
          f"bandı kadar büyüktür)")
    print(f"  NOT: faiz geliri (ρ, yıllık ~{FAIZ_GELIRI_YILLIK_MLR:.1f} mlr USD) "
          "arındırılmamıştır → birikimli rakam bu kadar YUKARI yanlıdır.")
    print()
    print("Tarih      |    ons |   fiyat | altın(çapa) | altın(ima) |"
          "  fiyat etk |  net alım | birikimli")
    print("-" * 104)
    for t, r in out.dropna(subset=["net_alim_satim"]).tail(args.pencere).iterrows():
        print(f"{t:%Y-%m-%d} | {r['altin_ons_mn']:6.2f} | "
              f"{r['altin_fiyat']:7.0f} | {r['altin_deger_seviye']:11.2f} | "
              f"{r['altin_deger_ima']:10.2f} | "
              f"{r['altin_fiyat_etkisi']:+10.2f} | "
              f"{r['net_alim_satim']:+9.2f} | {r['kumulatif']:+9.2f}")

    # Çevrimdışı koşuda da tanılar basılır ve dosyaya yazılır: bu modül tek
    # başına çalıştığında net_rezerv.py'nin denetimi DEVREDE DEĞİLDİR, koruma
    # tek noktaya bağlı kalmasın.
    uyarilar = fiyat_tasima_tanisi(out["altin_fiyat_kaynak"])
    d_t, uyari_zincir = zincirleme_tanisi(out["altin_fiyat_etkisi"],
                                          out["altin_ons_mn"],
                                          out["altin_fiyat"], args.capa)
    uyarilar += uyari_zincir
    print()
    if uyarilar:
        print(f"=== UYARILAR ({len(uyarilar)}) ===")
        for u in uyarilar:
            print(f"  ! {u}")
    else:
        print("=== Altın tarafı denetimi: uyarı yok ===")
    if d_t is not None:
        print(f"  Zincirleme sapması D_T = {d_t:+.2f} mlr USD (tanı, "
              "yayımlanmaz)")

    out.to_csv(args.csv)
    print(f"\nCSV kaydedildi: {args.csv}")
    print("  Sütun sözlüğü: altin_deger_seviye = TCMB haftalık değerleme "
          "çapasına oturan seri;")
    print("                 altin_deger_ima    = Q·P; Γ ve Λ BU seri üzerinden "
          "ayrıştırılmıştır.")


if __name__ == "__main__":
    main()
