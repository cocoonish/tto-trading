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

AKIMDA Q NET ALTINDIR: brüt miktar (IRFCL) eksi TCMB'nin altın cinsinden
yükümlülükleri (haftalık bilanço, safi gram; bkz. YUKUMLULUK_KALEMLERI). Akım
NET pozisyondan kurulur ve o yükümlülükler de yeniden değerlenir.

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
(T, son akım etiketinin ERTESİ iş günüdür: Γ(L) fiyatı L+1'e yürütür.)
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
Birincil (05.10.2026'dan beri): LONDRA SABAH FİYATI — TCMB'nin altını
yeniden değerlediği saatin (fiksing, Londra 10:30) uluslararası fiyatı. İki
fiziki altın ETC'sinin (IGLN.L, SGLD.L) Londra 10:00 ve 11:00'de biten saatlik
barlarından kurulur, USD/ons'a TCMB'nin KENDİ değerleme fiyatıyla (IRFCL: altın
değeri / ons, son 12 çapanın medyanı) ölçeklenir; günlük değerler depoda
biriken bir arşivde durur (`altin_londra.csv`, arşiv kazanır). Ayrıntı ve
ölçümler `LONDRA_ETC` üstündeki notta.

Londra serisinin ilk gününden ÖNCE: TP.ALTINPIYASA.AGORT03 (BİST Kıymetli
Madenler ağırlıklı ortalama, USD/ons), yedeği TP.ALTINPIYASA.KAP03 (kapanış);
seviye ilk Londra gününde Londra'ya ölçeklenir, günlük değişimler BİST'indir.
Londra serisinden SONRA eksik gün BİST'le doldurulmaz, taşınır ("ffill").
Hangi günün hangi kaynaktan geldiği `altin_fiyat_kaynak` sütununda ve
`ozet.json`'da görünür.

TANI (sessiz bayatlama dedektörü): her IRFCL gözleminde ima edilen değerleme
fiyatı P_ima = altın_değeri / ons hesaplanır ve P_ima/P − 1 izlenir; eşik %3.

--------------------------------------------------------------------------
6. BİLİNEN SINIR (kapatılmadı, yazıldı)
--------------------------------------------------------------------------
TCMB altını günlük bilançoda HER GÜN yeniden değerler (ölçüldü, 05.10.2026,
Londra fiyatıyla: dış varlıkların günlük değişimi BRÜT altının fiyat
etkisine Q·ΔP 17.11.2023'ten bu yana 1,15 ile (t 22, 681 gün), yıl yıl
2024'te 1,12, 2025'te 1,29, 2026'da 1,11 ile tepki veriyor; eskiden burada
"haftanın son iş günü Londra kotasyonuyla değerler" yazıyordu ve bu ölçümle
çelişiyor). BİST fiyatıyla aynı ölçü 2024'te 0,16 veriyordu: fiyatın
gürültüsü katsayıyı sıfıra çekiyordu, yani düşük katsayı TCMB'nin değil
ölçünün kusuruydu. Değerleme fiyatının KENDİSİ elimizde değil: Londra sabah
fiyatı onu IRFCL çapalarında medyan %0,09, en kötü %0,31 sapmayla izliyor
(BİST ortalaması %0,57 / %4,4 idi). Kalan sapma bir kalibrasyon sabitiyle
KAPATILMAZ — kapatmak, ölçüm hatasını modele gömmek olur.

LONDRA SERİSİNDEN ÖNCESİ ARINMIŞ DEĞİLDİR. 17.11.2023 öncesinde fiyat BİST
ortalamasıdır ve o dönemin günlük akımı net Γ'ya −0,84 (t −4,9) eğimle
tepki veriyor: fiyat etkisi akıma sızıyor. Bir birikim o dönemden
başlatılırsa `cipa_tanisi` uyarı basar; yayımlanan çıpa (27.02.2026) bu
dönemin çok sonrasındadır.

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


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı (ondalık virgül, eksi U+2212,
    yüzde önde). Hat kendi klasöründen elle koşturulursa ortak/ PYTHONPATH'te
    olmayabilir; depo kökünden bulunur."""
    try:
        import bicim
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim


# Çapa kaynağının okur adı: koşu kaydı sayfaya olduğu gibi basılır, 'irfcl_pdf' okura gitmez.
KAYNAK_ADI = {"irfcl_pdf": "IRFCL PDF", "ima": "ima", "evds_aylik": "EVDS aylık"}

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

# Son çapadan sonra miktar serisinin taşınabileceği azami gün. ÖLÇÜ ÇAPANIN
# TARİHİNE göre: çapa CUMA tarihlidir ve izleyen hafta (~+6 gün, Perşembe)
# yayımlanır; yani sağlıklı bir haftada bile çapanın yaşı bir sonraki yayım
# günü 13 güne çıkar (Cuma 28.08 → Perşembe 10.09'da 28.08 hâlâ son çapa).
# Eşik 8 iken bu uyarı her hafta Pazar–Çarşamba yanlış alarm veriyordu ve
# okura basılıyordu (09.09.2026'da ölçüldü). Bir yayının ATLANMASI çapayı
# 20 güne taşır; 16, sağlıklı haftanın 13'ünü sahte uyarıya çevirmeyecek,
# atlanan tek yayımı yakalayacak kadar dar.
ONS_TASIMA_UYARI_GUN = 16

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
# Günlük bant 05.10.2026'dan beri bütçe aralığının (±0,2–0,4; net altın,
# Londra sabah fiyatı) ÜST UCUNDA tutuluyor: bağımsız referansa karşı ölçülen
# hata (0,45) brüt altın ve BİST fiyatıyla kurulan tanıma aitti, yeni tanımın
# karşılığı ölçülmedi. Ölçülmeden daraltılan bir bant, iddiayı büyütür.
AKIM_BANT_GUNLUK = 0.40        # mlr USD
AKIM_BANT_HAFTALIK = 0.50      # mlr USD
AKIM_BANT_AYLIK = 1.00         # mlr USD
AKIM_BANT_BIRIKIMLI_6AY = 2.00 # mlr USD; notun ±1,5–2,5 aralığının ortası

# Faiz geliri (ρ) yanlılığının mertebesi — ARINDIRILMIYOR, İLAN EDİLİYOR.
# Yıllık 2,1–2,5 milyar USD'lik rezerv getirisi, işareti POZİTİF ve
# sistematik. Kimlikten düşülmediği için yayımlanan birikimli net alım bu
# kadar YUKARI yanlıdır. Hesaba GİRMEZ; yalnız ozet.json'a ve sayfaya taşınır.
FAIZ_GELIRI_YILLIK_MLR = 2.30

# --- Altın cinsinden YÜKÜMLÜLÜKLER (05.10.2026) ----------------------------
# Akım NET pozisyondan kuruluyor (dış varlıklar eksi döviz yükümlülükleri), ve
# TCMB'nin yükümlülüklerinin bir kısmı ALTIN cinsinden: bankaların zorunlu
# karşılık altını, bankaların TCMB'deki altın ve teminat altını, yurt dışı
# bankaların altın mevduatı, Hazine'nin altın mevduatı. Fiyat değişince
# onlar da yeniden değerlenir; net pozisyondaki fiyat etkisi BRÜT altının
# değil NET altının (brüt − yükümlülük) etkisidir. Brüt miktarla kurulan Γ
# net pozisyondan fazla düşüyordu. Ölçüldü (05.10.2026, Londra fiyatıyla,
# 2026'nın 176 iş günü, birleşik akım blokları hariç): brüt Γ ile kurulan
# akımın Γ'ya eğimi −0,27 (t −3,5) — altın yükseldiğinde sahte satış,
# düştüğünde sahte alım; yükümlülük tarafı (A11 + A14) bu kalemlerin kendi
# fiyat etkisine 0,88 ile (t 7,2) tepki veriyor. Net altınla eğim +0,15
# (t 1,3); Londra fiyatının bütün döneminde (17.11.2023'ten, 681 gün) brüt
# −0,26 (t −5,2), net +0,14 (t 1,8). Kaynak bir kalibrasyon sabiti DEĞİL,
# TCMB'nin haftalık bilançosunda yayımladığı safi gram kalemleri.
ONS_GRAM = 31.1034768          # bir troy ons, gram
# Sütun → bilanço kalemi. Analitik bilançodaki yeri: Hazine kalemi kamu döviz
# mevduatına (P.1ba), yurt içi banka kalemleri bankalar döviz mevduatına
# (P.1bb), yurt dışı banka kalemi dış yükümlülüklere (P.1a) düşer; üçü de net
# pozisyonun düştüğü yükümlülüklerdir. Standart dışı Hazine altını (diğer
# pasifler) bu kümede değil: karşılığı rezerv varlığı değil.
YUKUMLULUK_KALEMLERI = {
    "hazine_g": "Hazine altın mevduatı",
    "banka_teminat_g": "yurt içi bankaların teminat altını",
    "banka_g": "yurt içi bankaların altın mevduatı",
    "zk_g": "zorunlu karşılık altını",
    "yd_banka_g": "yurt dışı bankaların altın mevduatı",
}

# Fiyat etkisinin akıma SIZIP SIZMADIĞI (tanı): son SIZINTI_PENCERE iş gününde
# net alımın Γ'ya eğimi (birleşik akım blokları hariç). Brüt altınla kurulan
# akım 2026'da −0,27 / t −3,5 veriyor; net altın ve Londra fiyatıyla +0,15 /
# t 1,3. Eşik ikili: eğim büyük VE istatistiksel olarak ayırt edilebilir
# olmalı — yalnız eğim, gürültülü bir pencerede sahte alarm üretir. Kayan
# pencereyle ölçüldü (Haziran 2024'ten 585 pencere): iki pencere ateşliyor,
# ikisi de Mart 2026'nın %10'luk altın düşüşü haftasında.
SIZINTI_PENCERE = 120
SIZINTI_ESIK_EGIM = 0.15
SIZINTI_ESIK_T = 3.0


# ---------------------------------------------------------------------------
# Fiyat serisi
# ---------------------------------------------------------------------------
def fiyat_serisi(agort: pd.Series, kap: pd.Series,
                 index: pd.DatetimeIndex,
                 londra: pd.Series | None) -> pd.DataFrame:
    """Günlük altın fiyatı (USD/ons) + hangi kaynaktan geldiği.

    `londra` (bkz. londra_fiyat) ZORUNLUDUR; `None` yalnız sınamada ya da
    Londra serisi hiç kurulamadığında bilinçli olarak verilir — varsayılanı
    olsaydı bir çağrı yeri onu unutup ölçülmüş gürültüyü sessizce geri
    getirirdi.

    Londra serisinin ilk gününden (S) itibaren fiyat YALNIZ odur: eksik gün BİST
    fiyatıyla doldurulmaz, taşınır ("ffill") — iki kaynak arasındaki yerel prim
    farkı (ölçüldü: medyan %0,57, en kötü gün %4,4) tek günlük bir fiyat
    hareketi gibi okunurdu. S'den önce BİST serisi (AGORT03 → KAP03) kullanılır
    ve S günündeki iki fiyatın oranıyla ölçeklenir: o oran yalnız seviyeyi
    taşır, S'den önceki günlük DEĞİŞİMLER BİST'in değişimidir ve S'deki dikiş
    sahte bir hareket üretmez.
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
    londra_bas = None
    geri_olcek = None
    if londra is not None:
        lo = londra.reindex(index)
        if lo.notna().any():
            londra_bas = lo.first_valid_index()
            bist_s = fiyat.ffill().get(londra_bas)
            onceki = index < londra_bas
            if bist_s is not None and pd.notna(bist_s) and bist_s:
                geri_olcek = float(lo[londra_bas] / bist_s)
                fiyat = fiyat.where(~onceki, fiyat * geri_olcek)
            else:
                # S'de BİST fiyatı yoksa öncesi ölçeklenemez; dikiş sahte bir
                # hareket yazmasın diye S'den önceki fiyat ölçülemez sayılır.
                fiyat = fiyat.where(~onceki)
                kaynak = kaynak.where(~onceki)
            sonrasi = ~onceki
            fiyat = fiyat.where(~sonrasi, lo)
            kaynak = kaynak.where(~sonrasi, pd.Series("londra", index=index)
                                  .where(lo.notna()))
    tasima = fiyat.isna() & fiyat.ffill().notna()
    fiyat = fiyat.ffill()
    kaynak = kaynak.where(~tasima, "ffill")
    out = pd.DataFrame({"altin_fiyat": fiyat, "altin_fiyat_kaynak": kaynak})
    out.attrs["londra_bas"] = londra_bas
    out.attrs["geri_olcek"] = geri_olcek
    return out


# ---------------------------------------------------------------------------
# Londra fiyatı — TCMB'nin değerleme saatindeki uluslararası fiyat
# ---------------------------------------------------------------------------
# NİYE (05.10.2026, ölçüldü). Analitik bilanço altını her gün Londra sabah
# fiksingi saatindeki (10:30) uluslararası fiyatla yeniden değerliyor. Akımın
# kuruluşunda (Δswap hariç − Δkamu) bu saatin fiyatıyla kurulan net Γ'nin
# katsayısı 1,09 (t 9,2, 679 gün), BİST ağırlıklı ortalamasınınki 0,06 (t 0,6):
# BİST serisi değerlemeyi açıklamıyor, akıma yalnız gürültü yazıyordu — günde
# ~0,63 milyar USD (akımın standart sapması 1,857 → 1,748). Değerleme saati
# ayrıca TCMB'nin KENDİ yayımladığı değerleme fiyatıyla (IRFCL: altın değeri /
# ons) doğrulandı: aşağıdaki seri onu medyan %0,09, en kötü %0,31 sapmayla
# izliyor; BİST ortalaması %0,57 / %4,4, vadeli GC=F %0,5 (kontrat devri).
# KAYNAK: LBMA'nın kendi ucu buluttan 403, Bundesbank'ta seri yok, Dukascopy
# 503, Stooq JavaScript doğrulaması istiyor (keşif 05.10.2026). Erişilen ve
# devirsiz olan: Londra borsasındaki iki FİZİKİ altın ETC'si, USD cinsinden.
# Pay başına sabit altın hakkı taşırlar (yıllık ücret kadar yavaş erir: ölçülen
# eğim %0,11/yıl), vadeleri yoktur.
LONDRA_ETC = ("IGLN.L", "SGLD.L")
# Londra YEREL saatinde biten iki saatlik barın kapanışlarının ortalaması
# (10:00 ve 11:00) ≈ fiksing saati 10:30. Tek bar varsa o alınır.
LONDRA_BAR_BITIS = (10, 11)
# Ölçek: ETC fiyatı → USD/ons. TCMB'nin kendi değerleme fiyatından (IRFCL PDF:
# altın değeri / ons) son N çapanın medyanı. Ücret erimesi N çapada ihmal
# edilebilir (%0,11/yıl).
LONDRA_OLCEK_CAPA = 12
LONDRA_OLCEK_ASGARI = 3
LONDRA_ARSIV = os.path.join(BURASI, "altin_londra.csv")
# Arşivdeki bir günün değeri yeni indirmeyle bu oranın üstünde ayrışırsa tanı
# satırı basılır (arşiv kazanır: yayımlanmış bir sayının girdisi değişmez).
LONDRA_ARSIV_FARK = 0.001


def londra_gunluk(saatlik: dict[str, pd.Series],
                  simdi: pd.Timestamp) -> pd.DataFrame:
    """Saatlik barlardan gün başına Londra ~10:30 fiyatı (ETC'nin kendi birimi).

    `saatlik[sembol]`: indeksi barın BAŞLANGICI (UTC), değeri kapanış. Bar
    kapanışı başlangıç + 1 saattir ve `simdi`den sonra kapanan bar
    KULLANILMAZ (kapanmamış bar ölçüm değildir). İndeks: Londra takvim günü.
    """
    simdi = pd.Timestamp(simdi)
    simdi = simdi.tz_localize("UTC") if simdi.tzinfo is None else simdi.tz_convert("UTC")
    sutunlar = {}
    for sembol, s in saatlik.items():
        if s is None or len(s) == 0:
            continue
        s = s.dropna().astype(float)
        bas = pd.DatetimeIndex(s.index)
        bas = bas.tz_localize("UTC") if bas.tz is None else bas.tz_convert("UTC")
        bitis = bas + pd.Timedelta(hours=1)
        kapali = bitis <= simdi
        yerel = bitis.tz_convert("Europe/London")
        df = pd.DataFrame({"v": s.values, "saat": yerel.hour, "dk": yerel.minute,
                           "gun": yerel.tz_localize(None).normalize()})[kapali]
        df = df[(df["dk"] == 0) & df["saat"].isin(LONDRA_BAR_BITIS)]
        if df.empty:
            continue
        sutunlar[sembol] = df.groupby("gun")["v"].mean()
    if not sutunlar:
        return pd.DataFrame(columns=list(LONDRA_ETC), dtype=float)
    out = pd.DataFrame(sutunlar).sort_index()
    out.index.name = "tarih"
    return out


def londra_arsiv_birlestir(arsiv: pd.DataFrame | None,
                           yeni: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Arşiv + yeni indirme. ARŞİV KAZANIR: kaydedilmiş bir günün değeri
    değiştirilmez (o gün üzerine kurulmuş akım yayımlanmıştır); yalnız boş
    hücreler ve yeni günler doldurulur. Dönen sayı: arşivle yeni indirmenin
    LONDRA_ARSIV_FARK'tan fazla ayrıştığı hücre sayısı (tanı)."""
    if arsiv is None or arsiv.empty:
        return yeni.sort_index(), 0
    ortak_g = arsiv.index.intersection(yeni.index)
    ortak_s = arsiv.columns.intersection(yeni.columns)
    fark = 0
    if len(ortak_g) and len(ortak_s):
        a = arsiv.loc[ortak_g, ortak_s]
        y = yeni.loc[ortak_g, ortak_s]
        fark = int(((a / y - 1).abs() > LONDRA_ARSIV_FARK).sum().sum())
    birlesik = arsiv.combine_first(yeni).sort_index()
    birlesik.index.name = "tarih"
    return birlesik, fark


def londra_olcek(etc: pd.Series, deger_fiyati: pd.Series) -> tuple[float | None, int]:
    """ETC birimi → USD/ons ölçeği: TCMB değerleme fiyatı / ETC, son
    LONDRA_OLCEK_CAPA çapanın medyanı. Çapa yetmezse (None, n) — ölçeksiz bir
    seri seviye uydurmaz."""
    oran = (deger_fiyati / etc.reindex(deger_fiyati.index)).dropna()
    oran = oran[oran > 0].sort_index().tail(LONDRA_OLCEK_CAPA)
    if len(oran) < LONDRA_OLCEK_ASGARI:
        return None, int(len(oran))
    return float(oran.median()), int(len(oran))


def londra_fiyat(arsiv: pd.DataFrame,
                 deger_fiyati: pd.Series) -> tuple[pd.Series | None, dict]:
    """Arşivden USD/ons Londra fiyatı: ölçeklenmiş ETC'lerin gün başına ortalaması.

    `deger_fiyati`: TCMB'nin değerleme fiyatı (IRFCL PDF çapalarında altın
    değeri / ons). Hiçbir ETC ölçeklenemezse (None, künye) döner ve çağıran
    taraf BİST serisine kalır — sebebi künyede adıyla durur.
    """
    kunye: dict = {}
    parca = []
    for sembol in arsiv.columns:
        k, n = londra_olcek(arsiv[sembol], deger_fiyati)
        kunye[sembol] = {"olcek": k, "capa": n}
        if k is not None:
            parca.append(arsiv[sembol] * k)
    if not parca:
        return None, kunye
    p = pd.concat(parca, axis=1).mean(axis=1, skipna=True).dropna()
    p.name = "londra"
    return p, kunye


def deger_fiyati_capalari(gozlem: pd.DataFrame | None) -> pd.Series:
    """TCMB'nin değerleme fiyatı (USD/ons): IRFCL PDF'inde altın değeri / ons.
    İki sayı da AYNI tablodan, yani TCMB'nin o Cuma kullandığı fiyattır."""
    if gozlem is None or not {"altin_M", "mn_ons"} <= set(gozlem.columns):
        return pd.Series(dtype=float)
    g = gozlem.dropna(subset=["altin_M", "mn_ons"])
    g = g[g["mn_ons"] > 0]
    return (g["altin_M"] / g["mn_ons"]).astype(float).sort_index()


def londra_arsiv_oku(yol: str = LONDRA_ARSIV) -> pd.DataFrame | None:
    if not os.path.exists(yol):
        return None
    a = pd.read_csv(yol, index_col=0, parse_dates=True)
    a.index.name = "tarih"
    return a.astype(float)


def londra_hazirla(saatlik: dict[str, pd.Series] | None,
                   simdi: pd.Timestamp,
                   deger_fiyati: pd.Series,
                   arsiv: pd.DataFrame | None,
                   indirme_hatasi: str | None = None
                   ) -> tuple[pd.Series | None, pd.DataFrame | None, list[str], dict]:
    """Ağa ÇIKMAYAN yarı: indirilen saatlik barlar + arşiv → USD/ons Londra serisi.

    Dönüş: (fiyat serisi ya da None, yazılacak arşiv, uyarılar, künye).
    Ağdan gelen tek girdi `saatlik`tir (indirilemediyse None ve sebebi
    `indirme_hatasi`); duman bu fonksiyonu gerçek biçimdeki sahte barlarla
    koşturur. Arşiv yazımı çağıranın işidir (dosya yolu sınamada değişir).
    """
    b = _bicim()
    uyarilar: list[str] = []
    if saatlik:
        yeni = londra_gunluk(saatlik, simdi)
        birlesik, fark = londra_arsiv_birlestir(arsiv, yeni)
        if fark:
            uyarilar.append(
                f"LONDRA ALTIN FİYATI ARŞİVİ: kaydedilmiş {fark} değerle yeni "
                f"indirme arasında {b.yuzde(LONDRA_ARSIV_FARK * 100, 1)}'i aşan "
                "fark var; arşivdeki değer korundu (o günlerin akımı "
                "yayımlandı).")
    else:
        birlesik = arsiv
        son = (f"{arsiv.index.max():%d.%m.%Y}" if arsiv is not None and len(arsiv)
               else "yok")
        uyarilar.append(
            "LONDRA ALTIN FİYATI ALINAMADI: bu koşuda saatlik kotasyonlar "
            f"indirilemedi ({indirme_hatasi or 'boş yanıt'}). Arşivin son günü "
            f"{son}; sonraki günlerin fiyat etkisi ölçülemedi ve akımları boş "
            "kaldı.")
    if birlesik is None or birlesik.empty:
        uyarilar.append(
            "LONDRA ALTIN FİYATI KURULAMADI: arşiv boş; fiyat etkisi bütün "
            "dönemde BİST ağırlıklı ortalamasıyla hesaplandı (değerleme saatinde "
            "değil, günlük gürültüsü yüksek).")
        return None, birlesik, uyarilar, {}
    p, kunye = londra_fiyat(birlesik, deger_fiyati)
    if p is None:
        uyarilar.append(
            "LONDRA ALTIN FİYATI ÖLÇEKLENEMEDİ: TCMB'nin değerleme fiyatıyla "
            f"eşleşen yeterli haftalık çapa yok (en az {LONDRA_OLCEK_ASGARI}); "
            "fiyat etkisi bu koşuda BİST ağırlıklı ortalamasıyla hesaplandı.")
    kunye = {"etc": kunye, "son_gun": f"{birlesik.index.max():%Y-%m-%d}",
             "gun": int(len(birlesik))}
    return p, birlesik, uyarilar, kunye


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
                f"taşındı (eşik {FIYAT_TASIMA_UYARI_GUN}). Fiyat kaynağı "
                "durmuş olabilir; o günlerin fiyat etkisi güvenilmez."
            )
    if t.iloc[-1]:
        son_gercek = kaynak[kaynak != "ffill"]
        if len(son_gercek):
            bos = olculemeyen_fiyat_gunleri(kaynak)
            gunler = bos[bos].index
            araligi = (f"{gunler[0]:%d.%m.%Y} ve sonrası"
                       if len(gunler) > 1 else f"{gunler[0]:%d.%m.%Y}")
            uyarilar.append(
                f"ALTIN FİYATI SERİNİN UCUNDA TAŞINIYOR: son gerçek kotasyon "
                f"{son_gercek.index[-1]:%d.%m.%Y}. Fiyatın kımıldayıp "
                "kımıldamadığı bilinmediği için fiyat etkisi ve net döviz "
                f"alımı {araligi} için boş bırakıldı; sıfır yazılmadı."
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
                _b = _bicim()
                red.append(
                    f"ONS ÇAPASI REDDEDİLDİ ({t:%d.%m.%Y}): IRFCL PDF'i "
                    f"{_b.sayi(s.loc[t], 3)} mn ons diyor; bu, ima edilen değerleme "
                    f"fiyatını {_b.sayi(deg_fiyat.loc[t], 0)} USD/ons yapıyor, oysa "
                    f"piyasa {_b.sayi(p.loc[t], 0)} ({_b.yuzde(oran.loc[t] * 100, 1, isaret=True)}, eşik "
                    f"{_b.yuzde(ONS_CAPA_RED_ORAN * 100, 0)}). Fiyat farkıyla "
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
def olculemeyen_fiyat_gunleri(kaynak: pd.Series) -> pd.Series:
    """Fiyat farkının ÖLÇÜLEMEDİĞİ günler (Γ burada boş bırakılır).

    Γ(L) = Q(L)·[P(L+1) − P(L)]; iki ucundan biri TAŞINMIŞSA fark ölçülmüş
    değildir. Taşımanın iki sebebi olabilir ve ikisi aynı görünür:

      · ORTADAKİ taşıma — BİST kapalıydı (çoğu bayram arifesi yarım günü),
        ama TCMB bilançosunu yine yayımladı ve altını uluslararası fiyatla
        yeniden değerledi. Burada maskelenmez: iki günün TOPLAMI doğrudur,
        günlere dağılımı ölçülemez — `arife_bloklari` ile birleştirilir.
      · SONDAKİ taşıma — besleme durmuş olabilir. Fiyatın kımıldayıp
        kımıldamadığını BİLMİYORUZ; Γ = 0 yazmak ölçmediğimiz bir şeyi
        ölçmüş gibi göstermektir.

    İkisini ayıran şey, taşınan günden SONRA gerçek bir kotasyon gelip
    gelmediğidir: geldiyse tatil, gelmediyse kesinti. Bu yüzden yalnız serinin
    SAĞ UCUNDAKİ taşıma bloğu maskelenir; ortadaki bloklar dokunulmadan kalır.

    Ölçüldü (02.09.2026, 918 iş günü): fiyat 14 günde taşınmış ve Γ'nın
    SIFIR çıktığı günlerin TAMAMI (14/14) bu taşımalardan doğuyor — gerçek
    kotasyonla ölçülmüş tek bir sıfır yok. Yani sayfadaki her sıfır, ölçüm
    değil taşımanın izidir. O gün ortadaki sıfırın "tatil, fiyat kımıldamadı"
    diye doğru olduğu varsayıldı; 05.10.2026'da yanlış çıktı (bkz.
    `arife_bloklari`).
    """
    tasindi = (kaynak == "ffill")
    if not tasindi.any():
        return pd.Series(False, index=kaynak.index)
    gercek = ~tasindi
    if not gercek.any():                       # hiç gerçek kotasyon yok
        return pd.Series(True, index=kaynak.index)
    son_gercek = kaynak.index[gercek][-1]
    uctaki_tasima = tasindi & (kaynak.index > son_gercek)
    # Γ(L) iki ucu da ister: L ya da L+1 uçtaki taşımadaysa fark ölçülemez.
    return uctaki_tasima | uctaki_tasima.shift(-1, fill_value=False)


def arife_bloklari(kaynak: pd.Series) -> list[tuple[list[pd.Timestamp], pd.Timestamp]]:
    """ORTADAKİ taşıma blokları: (boşaltılacak etiketler, birleşik akımın etiketi).

    Fiyat kaynağının kapalı olduğu ama TCMB'nin bilançosunu yayımladığı günler
    (Londra serisinde İngiltere resmî tatilleri; ondan önceki BİST döneminde
    çoğu bayram arifesi yarım günü) fiyat serisinde taşınır: P(L) = P(L−1). Γ(L−1)
    sıfır çıkar, Γ(L) iki günün fiyat hareketini birden taşır. Bilanço ise
    altını O GÜN de uluslararası fiyatla yeniden değerler; düşülmeyen yeniden
    değerleme L−1'in akımına, fazladan düşülen L'ninkine yazılır. Ölçüldü
    (05.10.2026, 11 arife): L−1'in akımı iki günlük fiyat etkisiyle 0,89
    korelasyonlu, sıradan günlerde ardışık akım korelasyonu 0,11; en büyük
    vakada akım bir gün −1,91, ertesi gün +7,45 milyar dolar yazılmıştı.

    İki günün TOPLAMI doğrudur (fiyat hareketinin tamamı bir kez düşülür);
    dağılımı ölçülemez. Kural: blok [L1..Lk] için L1−1..Lk−1 etiketleri boş,
    toplam Lk etiketine yazılır — birikimli akım değişmez, günlük seri sahte
    bir zıt çift basmaz. Serinin SAĞ UCUNDAKİ taşıma bu kümede değildir
    (`olculemeyen_fiyat_gunleri` onu boş bırakır).
    """
    k = kaynak.reindex(kaynak.index)
    tasindi = (k == "ffill").to_numpy()
    gercek = ~tasindi
    if not tasindi.any() or not gercek.any():
        return []
    son_gercek = int(gercek.nonzero()[0][-1])
    bloklar: list[tuple[list[pd.Timestamp], pd.Timestamp]] = []
    i = 0
    n = len(tasindi)
    while i < n:
        if not tasindi[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and tasindi[j + 1]:
            j += 1
        if i >= 1 and j < son_gercek:
            bos = list(k.index[i - 1:j])          # L1−1 .. Lk−1
            bloklar.append((bos, k.index[j]))     # toplam Lk'ye
        i = j + 1
    return bloklar


def birlesik_akim(df: pd.DataFrame, kaynak: pd.Series,
                  kolonlar: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    """`arife_bloklari`nın kuralını uygular; ikinci dönüş birleşik etiketlerdir.

    Bloktaki değerlerden biri boşsa birleşik değer de BOŞTUR — boş bir günü
    sıfır sayıp toplamak, ölçülmemiş bir şeyi ölçülmüş gibi gösterirdi.
    """
    out = df.copy()
    isaret = pd.Series(False, index=df.index)
    for bos, hedef in arife_bloklari(kaynak.reindex(df.index)):
        etiketler = bos + [hedef]
        for c in kolonlar:
            if c not in out.columns:
                continue
            blok = out.loc[etiketler, c]
            out.loc[hedef, c] = blok.sum() if blok.notna().all() else float("nan")
            out.loc[bos, c] = float("nan")
        isaret.loc[hedef] = True
    return out, isaret


def yukumluluk_ons_serisi(gram: pd.DataFrame | None,
                          index: pd.DatetimeIndex) -> pd.DataFrame:
    """Altın cinsinden yükümlülükler, milyon troy ons, günlük takvimde.

    Kaynak TCMB haftalık bilançosu (Cuma, safi gram). Çapalar arasında zamana
    göre doğrusal ara değer, son çapadan sonra taşıma — brüt miktar serisiyle
    (`ons_serisi`) AYNI kural, aynı fonksiyon.

    Bir kalem bilançoda ilk göründüğü haftadan önce YOKTU (yurt dışı bankaların
    altın mevduatı 05.04.2024'te açıldı): o haftalar sıfırdır. İlk görünüşten
    SONRA boş gelen hafta ise çapa olmaz — boşu sıfır saymak, yükümlülüğü
    o hafta için silmek demek olurdu.

    Veri hiç yoksa ya da bir kalem hiç yoksa HATA verir: net altın kurulamazsa
    Γ brüt altınla kurulur ve ölçülmüş bir kusuru geri getirir; sessizce brüte
    düşmek yerine hat görünür biçimde durur.
    """
    if gram is None or gram.empty:
        raise RuntimeError(
            "ALTIN YÜKÜMLÜLÜĞÜ YOK: TCMB haftalık bilançosunun altın kalemleri "
            "alınamadı; net altın kurulamıyor, fiyat etkisi hesaplanmadı.")
    eksik = [c for c in YUKUMLULUK_KALEMLERI if c not in gram.columns]
    if eksik:
        raise RuntimeError(
            "ALTIN YÜKÜMLÜLÜĞÜ EKSİK: " + ", ".join(YUKUMLULUK_KALEMLERI[c] for c in eksik)
            + " alınamadı; net altın kurulamıyor.")
    g = gram[list(YUKUMLULUK_KALEMLERI)].astype(float).sort_index()
    for c in g.columns:
        ilk = g[c].first_valid_index()
        if ilk is None:
            raise RuntimeError(
                f"ALTIN YÜKÜMLÜLÜĞÜ BOŞ: {YUKUMLULUK_KALEMLERI[c]} hiç gözlem taşımıyor.")
        g.loc[g.index < ilk, c] = 0.0
    capa = g.dropna(how="any").sum(axis=1) / ONS_GRAM / 1e6
    capalar = pd.DataFrame({"ons": capa, "kaynak": "haftalik_bilanco"})
    q = ons_serisi(capalar, index)
    out = pd.DataFrame({"ons_yukumluluk": q["ons"],
                        "ons_yukumluluk_kaynak": q["ons_kaynak"]})
    out.attrs["son_capa"] = capa.index[-1] if len(capa) else None
    return out


def sizinti_tanisi(akim: pd.Series, gamma: pd.Series,
                   haric: pd.Series | None,
                   pencere: int = SIZINTI_PENCERE) -> list[str]:
    """Fiyat etkisi akıma sızıyor mu: son `pencere` günde akımın Γ'ya eğimi.

    Doğru arındırılmış bir akım altın fiyatından bağımsız olmalıdır. Eğim
    belirgin biçimde sıfırdan ayrışırsa fiyat etkisi ya fazla ya eksik
    düşülüyor demektir — altın yükümlülüklerinin değerlemesi, miktar serisi ya
    da fiyat kaynağı kaymış olabilir.

    `haric` (birleşik akım etiketleri, `akim_birlesik`) regresyondan DÜŞÜLÜR
    ve argümanın varsayılanı yoktur. Birleşik bir etiket birden çok seansın
    toplamıdır; hem akımı hem Γ'yı birlikte büyütür ve tek başına eğimi
    taşır. Ölçüldü (05.10.2026, BİST fiyatlı seri): 19.03.2026 birleşik
    noktasının kaldıracı (n·h) 50, öbür noktaların en büyüğü 5; o tek nokta
    02.03–28.08 penceresini +0,64 / t +3,15 ile sahte bir uyarıya taşıyordu,
    çıkarılınca +0,04 / t 0,15. Düşme pencereden ÖNCE yapılır: pencere yine
    `pencere` gözlem tutar.
    """
    if haric is not None:
        maske = haric.reindex(akim.index)
        maske = maske.astype(str).str.lower().isin(["true", "1"])
        akim = akim[~maske]
    d = pd.concat([akim, gamma], axis=1).dropna().tail(pencere)
    if len(d) < pencere // 2:
        return []
    y = d.iloc[:, 0].to_numpy()
    x = d.iloc[:, 1].to_numpy()
    xm = x - x.mean()
    sxx = float((xm ** 2).sum())
    if sxx <= 0:
        return []
    b = float((xm * (y - y.mean())).sum() / sxx)
    e = y - y.mean() - b * xm
    se = (float((e ** 2).sum()) / (len(d) - 2) / sxx) ** 0.5
    t = b / se if se > 0 else 0.0
    if abs(b) >= SIZINTI_ESIK_EGIM and abs(t) >= SIZINTI_ESIK_T:
        _b = _bicim()
        yon = "ters" if b < 0 else "aynı"
        return [
            f"ALTIN ETKİSİ SIZINTISI: son {len(d)} iş gününde günlük net alım, altın "
            f"fiyat etkisiyle {yon} yönde hareket ediyor (eğim {_b.sayi(b, 2, isaret=True)}, "
            f"t {_b.sayi(t, 1, isaret=True)}). Fiyat etkisi akımdan doğru ölçüde "
            "düşülmüyor olabilir."
        ]
    return []


def yukumluluk_tazelik_tanisi(son: pd.Timestamp | None,
                              bugun: pd.Timestamp | None = None) -> list[str]:
    """Yükümlülük çapası ne kadar eskidi — brüt miktar çapasıyla aynı eşik.

    Referans DUVAR SAATİDİR (bkz. altin_tanilari (4)); `bugun` yalnız sınama için.
    """
    if son is None:
        return []
    ref = bugun if bugun is not None else pd.Timestamp.today().normalize()
    yas = (ref - son).days
    if yas > ONS_TASIMA_UYARI_GUN:
        return [
            f"ALTIN YÜKÜMLÜLÜĞÜ TAZELİĞİ: TCMB'nin altın cinsinden yükümlülükleri en "
            f"son {son:%d.%m.%Y} tarihli haftalık bilançodan okundu ({yas} gün önce, "
            f"eşik {ONS_TASIMA_UYARI_GUN}). O günden beri taşınıyor; haftalık "
            "bilanço yayımı kesilmiş olabilir."
        ]
    return []


def altin_fiyat_etkisi(ons: pd.Series, fiyat: pd.Series,
                       fiyat_kaynak: pd.Series | None) -> pd.DataFrame:
    """Laspeyres fiyat/miktar ayrıştırması. Etiket L, değer L→L+1 (mlr USD).

    Dönen sütunlar:
      altin_fiyat_etkisi   Γ(L) = Q(L)·ΔP
      altin_miktar_etkisi  Λ(L) = P(L+1)·ΔQ
      altin_deger_ima      V(L) = Q(L)·P(L)   (tanı; rezervdeki altın kalemi
                           bundan biraz farklıdır, oradaki değerleme fiyatı
                           TCMB'nin haftalık kotasyonudur)
      bennet_fark          |Γ_Laspeyres − Γ_Bennet|  (tanı)

    `fiyat_kaynak` ZORUNLUDUR ve `None` verilmesi bilinçli bir tercihtir
    (yalnız sınamada). Varsayılanı olsaydı bir çağrı yerinde unutulur ve o
    hat sessizce taşınmış fiyattan sıfır üretirdi — bu bir kez oldu. Verilirse
    fiyat FARKININ ölçülemediği günlerde Γ boş
    bırakılır (bkz. olculemeyen_fiyat_gunleri). Sıfır bir ölçüm sonucudur;
    taşınan fiyat ölçüm değildir. Λ ve Bennet farkı yalnız ΔQ ≠ 0 iken
    fiyata bağlıdır; miktar kımıldamadıysa ikisi de TAM OLARAK sıfırdır ve
    maskelenmez — ölçülebilen bir sıfırı boşaltmak da bir kusurdur. Seviye
    tanısı V(L) = Q(L)·P(L) bir FARK değildir, dokunulmaz; fiyatının taşındığı
    `altin_fiyat_kaynak` alanında zaten görünür.
    """
    q = ons.astype(float)
    p = fiyat.astype(float)
    dp = p.shift(-1) - p
    dq = q.shift(-1) - q
    gamma = q * dp / 1000.0
    lam = p.shift(-1) * dq / 1000.0
    bennet = (q + q.shift(-1)) / 2.0 * dp / 1000.0
    fark = (gamma - bennet).abs()               # = ½·|ΔQ·ΔP|
    if fiyat_kaynak is not None:
        olcusuz = olculemeyen_fiyat_gunleri(fiyat_kaynak.reindex(q.index))
        miktar_olcusuz = olcusuz & dq.ne(0.0)   # ΔQ = 0 ise ΔP'den bağımsız
        gamma = gamma.mask(olcusuz)
        lam = lam.mask(miktar_olcusuz)
        fark = fark.mask(miktar_olcusuz)
    return pd.DataFrame({
        "altin_fiyat_etkisi": gamma,
        "altin_miktar_etkisi": lam,
        "altin_deger_ima": q * p / 1000.0,
        "bennet_fark": fark,
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


def birikimli_akim(akim: pd.Series, cipa: str = CIPA_TARIHI,
                   bloklar: list[tuple[list[pd.Timestamp], pd.Timestamp]] | None = None
                   ) -> pd.Series:
    """Çıpadan itibaren zincirlenmiş birikim. Etiket akım serisiyle aynı (L).

    birikimli(L) = Σ akim(s),  çıpa ≤ s ≤ L
    yani "çıpa gününden L+1 iş gününe kadar biriken net döviz alımı".

    Çıpa günü seride yoksa SESSİZCE en yakın güne kaydırılmaz: görünür hata
    verilir. Kaydırma, birikimli serinin sessizce yeniden tabanlanması demek
    olurdu.

    `bloklar` (`arife_bloklari`): çıpa bir birleşik akımın HEDEF etiketine ya
    da bloğun ilk boş etiketinden SONRAKİ bir boş etikete düşerse birikim,
    çıpadan ÖNCEKİ etiketlerin akımını da sayardı (ölçüldü: çıpa 19.03.2026
    verilince birikim çıpa 18.03 ile birebir aynı çıkıyordu). O da görünür
    hatadır; bloğun ilk boş etiketi geçerli bir çıpadır.
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
    for bos, hedef in (bloklar or []):
        icerde = [hedef] + list(bos[1:])
        if t0 in icerde:
            raise RuntimeError(
                f"Çıpa tarihi {t0:%d.%m.%Y} birleşik bir akım bloğunun içinde "
                f"({bos[0]:%d.%m.%Y} kapanışından {hedef:%d.%m.%Y} etiketine). "
                "Bu blokta günlere dağılım ölçülemez; birikim çıpadan önceki "
                f"etiketleri de sayardı. Çıpa {bos[0]:%d.%m.%Y} ya da "
                "bloktan sonraki bir gün olabilir.")
    pencere = akim.copy()
    pencere[pencere.index < t0] = float("nan")
    return pencere.cumsum()


def cipa_tanisi(cipa: str, londra_bas: pd.Timestamp | None) -> list[str]:
    """Çıpa Londra fiyatının başladığı günden önceyse görünür uyarı.

    Londra serisinden ÖNCEKİ günlerde fiyat BİST ağırlıklı ortalamasıdır ve
    TCMB'nin değerleme saatinde değildir; o dönemin günlük akımı fiyat
    etkisinden arınmış DEĞİLDİR (ölçüldü 05.10.2026: 2023 başı–16.11.2023
    akımın net Γ'ya eğimi −0,84, t −4,9; Londra fiyatıyla 17.11.2023–
    01.10.2026 +0,14, t 1,8). Oradan başlatılan bir birikim fiyat hareketini
    de taşır."""
    t0 = pd.Timestamp(cipa)
    if londra_bas is None:
        return []          # Londra serisi yok: kaynak uyarısı zaten basıldı
    if t0 < pd.Timestamp(londra_bas):
        return [
            f"ÇIPA LONDRA FİYATINDAN ÖNCE: {t0:%d.%m.%Y}. Altın fiyatı "
            f"{pd.Timestamp(londra_bas):%d.%m.%Y} öncesinde TCMB'nin değerleme "
            "saatinde değil; o dönemin günlük akımı fiyat etkisinden arınmış "
            "değildir ve bu çıpadan kurulan birikim fiyat hareketini de taşır."]
    return []


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
                f"{en_kotu[0]:%d.%m.%Y}, {_bicim().sayi(abs(en_kotu[1]), 2)} mlr USD. "
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
            _b = _bicim()
            kalem_ons.append((t, sapma_usd, (
                f"ALTIN MİKTAR TANISI ({t:%d.%m.%Y}): yayımlanan ons "
                f"{_b.sayi(q_pdf, 3)} ile ima edilen ons {_b.sayi(q_ima, 3)} arasındaki fark "
                f"{_b.yuzde(sapma_oran * 100, 1)}, yani {_b.sayi(sapma_usd, 2)} mlr USD'lik "
                f"sahte miktar etkisi (eşikler {_b.yuzde(ONS_TANI_ESIK_ORAN * 100, 0)} "
                f"ve {_b.sayi(ONS_TANI_ESIK_USD, 2)} mlr USD). Fiyat kaynağı kaymış ya "
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
                _b = _bicim()
                kaynak_ad = str(capalar.loc[t, "kaynak"])
                kalem_sic.append((t, sicrama, (
                    f"ALTIN MİKTAR SIÇRAMASI ({t:%d.%m.%Y}): iki çapa arasında "
                    f"miktar {_b.sayi(dq, 3, isaret=True)} mn ons değişti ({_b.yuzde(oran * 100, 1)}, "
                    f"{_b.sayi(sicrama, 2)} mlr USD; eşikler "
                    f"{_b.yuzde(ONS_SICRAMA_ESIK_ORAN * 100, 0)} ve "
                    f"{_b.sayi(ONS_SICRAMA_ESIK_USD, 2)} mlr USD, kaynak "
                    f"{KAYNAK_ADI.get(kaynak_ad, kaynak_ad.replace('_', ' '))}). Bu gerçek bir altın "
                    "alım/satımı mı, yoksa fiyat kaynağının kayması mı — "
                    "miktar etkisi (Λ) buna göre okunmalı.")))
    _yayimla("ALTIN MİKTAR SIÇRAMASI", kalem_sic)

    # (2) İma edilen değerleme fiyatı piyasa fiyatından ne kadar sapıyor?
    # "ima" çapasında miktar zaten V/P'den kuruludur, yani V/Q = P ve sapma
    # CEBİRSEL OLARAK sıfırdır — o çapa bu tanıya hiçbir şey söylemez. Tanı
    # yalnız miktarı bağımsız yayımlanan çapalarda (IRFCL PDF, EVDS aylık)
    # sorulur; son sekiz çapanın hiçbiri öyle değilse tanının KÖR olduğu koşu
    # çıktısına adıyla yazılır (sessizlik "sorun yok" diye okunmasın).
    bagimsiz = [t for t in capalar.index[-8:]
                if str(capalar.loc[t, "kaynak"]) != "ima"]
    if not bagimsiz and not capalar.empty:
        print("  [tanı] ALTIN FİYAT TANISI ölçülemedi: son sekiz çapanın "
              "hepsi ima edilen miktar (V/P), değerleme fiyatı sapması "
              "cebirsel olarak sıfır.")
    for t in bagimsiz:
        v = altin_deger_M.reindex([t]).iloc[0]
        q = capalar.loc[t, "ons"]
        p = fiyat.reindex([t]).iloc[0] if t in fiyat.index else None
        if pd.isna(v) or pd.isna(q) or not q or p is None or pd.isna(p):
            continue
        p_ima = v / q
        sapma = abs(p_ima / p - 1.0)
        if sapma > FIYAT_TANI_ESIK:
            _b = _bicim()
            uyarilar.append(
                f"ALTIN FİYAT TANISI ({t:%d.%m.%Y}): ima edilen değerleme "
                f"fiyatı {_b.sayi(p_ima, 0)} USD/ons, piyasa serisi "
                f"{_b.sayi(p, 0)} ({_b.yuzde(sapma * 100, 1)} sapma, eşik "
                f"{_b.yuzde(FIYAT_TANI_ESIK * 100, 0)}). Fiyat beslemesi donmuş ya da "
                "TCMB değerleme referansını değiştirmiş olabilir."
            )

    # (3) Laspeyres ile Bennet ayrışıyor mu? (oransal — bkz. BENNET_TANI_ESIK)
    if {"bennet_fark", "altin_fiyat_etkisi"} <= set(etki.columns):
        g = etki["altin_fiyat_etkisi"].abs()
        oran = (etki["bennet_fark"] / g).where(g > BENNET_TABAN).dropna()
        if len(oran) and oran.max() > BENNET_TANI_ESIK:
            t = oran.idxmax()
            _b = _bicim()
            uyarilar.append(
                f"AYRIŞTIRMA TANISI ({t:%d.%m.%Y}): Laspeyres ile Bennet "
                f"fiyat etkisi {_b.yuzde(oran.max() * 100, 1)} ayrışıyor (eşik "
                f"{_b.yuzde(BENNET_TANI_ESIK * 100, 0)}). Miktar serisinde sıçrama var."
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

    T, son akım etiketinin ertesi iş günüdür (Γ(L) fiyatı L+1'e yürütür).

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
    # Γ(L) L→L+1 değişimini taşır; Σ Γ(çıpa…son) fiyatı P(çıpa)'dan
    # P(son+1)'e kadar yürütür. Doğrudan etki de AYNI uca kadar ölçülür —
    # P(son) bir günü eksik sayar ve D_T'ye son günün fiyat etkisini ekler.
    konum = fiyat.index.get_indexer([son])[0]
    if konum < 0 or konum + 1 >= len(fiyat.index):
        return None, []
    uc = fiyat.index[konum + 1]
    p0, q0 = fiyat.get(t0), ons.get(t0)
    p_t = fiyat.iloc[konum + 1]
    if pd.isna(p0) or pd.isna(q0) or pd.isna(p_t):
        return None, []
    dogrudan = q0 * (p_t - p0) / 1000.0
    d_t = float(g.sum() - dogrudan)
    uyarilar: list[str] = []
    # Ölçek referansı: aynı pencerede biriken fiyat etkisinin büyüklüğü.
    olcek = abs(float(g.sum()))
    if olcek > 0 and abs(d_t) > ZINCIRLEME_TANI_ORAN * olcek:
        _b = _bicim()
        uyarilar.append(
            f"ZİNCİRLEME TANISI: günlük fiyat etkilerinin toplamı "
            f"({_b.sayi(float(g.sum()), 2, isaret=True)}) ile çıpa miktarıyla "
            f"hesaplanan doğrudan fiyat etkisi ({_b.sayi(dogrudan, 2, isaret=True)}) "
            f"arasında {_b.sayi(d_t, 2, isaret=True)} mlr USD sapma var (pencere "
            f"{t0:%d.%m.%Y}–{uc:%d.%m.%Y}). Miktar ile fiyat birlikte hareket "
            "ediyor ya da miktarın ara değeri bozulmuş olabilir."
        )
    return d_t, uyarilar


# ---------------------------------------------------------------------------
# Tek çağrılık boru hattı (net_rezerv.py bunu kullanır)
# ---------------------------------------------------------------------------
def akim_ayristir(ons: pd.Series, ons_yukumluluk: pd.Series, fiyat: pd.Series,
                  fiyat_kaynak: pd.Series, swap_haric: pd.Series,
                  kamu_doviz_usd: pd.Series) -> pd.DataFrame:
    """Net altın + ayrıştırma + akım + arife birleştirmesi — TEK tanım.

    Hem canlı hat (`arindirma_hatti`) hem çevrimdışı yeniden üretim
    (`_gunlukten_uret`) bunu çağırır; iki ayrı kopya bir gün sessizce ayrışırdı.
    Γ ve Λ NET altınla (brüt − yükümlülük) kurulur; `altin_deger_ima` BRÜT
    altının değeri olarak kalır (rezervdeki altın kaleminin tanısı).
    """
    q_net = ons - ons_yukumluluk
    etki = altin_fiyat_etkisi(q_net, fiyat, fiyat_kaynak)
    etki["altin_deger_ima"] = ons * fiyat / 1000.0
    akim = net_doviz_alimi(swap_haric, kamu_doviz_usd,
                           etki["altin_fiyat_etkisi"],
                           etki["altin_miktar_etkisi"])
    out = pd.concat([etki, akim], axis=1)
    out, birlesik = birlesik_akim(
        out, fiyat_kaynak,
        ["altin_fiyat_etkisi", "altin_miktar_etkisi", "net_doviz_alimi",
         "net_doviz_alimi_altin_haric"])
    for _bos, _hedef in arife_bloklari(fiyat_kaynak.reindex(out.index)):
        out.loc[_bos, "bennet_fark"] = float("nan")
    out["ons_net"] = q_net
    out["akim_birlesik"] = birlesik
    return out


def arindirma_hatti(index: pd.DatetimeIndex, agort: pd.Series, kap: pd.Series,
                    altin_deger_M: pd.Series, aylik_ons: pd.Series | None,
                    gozlem: pd.DataFrame | None, swap_haric: pd.Series,
                    kamu_doviz_usd: pd.Series, yukumluluk_gram: pd.DataFrame | None,
                    londra_fiyati: pd.Series | None,
                    cipa: str = CIPA_TARIHI) -> tuple[pd.DataFrame, list[str]]:
    """Fiyat + miktar + ayrıştırma + akım + birikim — tek çağrıda.

    `yukumluluk_gram` ZORUNLUDUR (varsayılanı yok): unutulan bir çağrı yeri
    Γ'yı brüt altınla kurup ölçülmüş kusuru geri getirirdi. `londra_fiyati`
    de öyle (bkz. `fiyat_serisi`): unutulan çağrı yeri değerleme saatinde
    olmayan BİST fiyatına sessizce dönerdi.

    Dönen DataFrame sütunları:
      altin_fiyat, altin_fiyat_kaynak, ons, ons_kaynak, ons_yukumluluk,
      ons_yukumluluk_kaynak, ons_net, altin_fiyat_etkisi, altin_miktar_etkisi,
      altin_deger_ima, bennet_fark, net_doviz_alimi, net_doviz_alimi_altin_haric,
      akim_birlesik, net_doviz_alimi_birikimli, altin_fiyat_etkisi_birikimli
    """
    f = fiyat_serisi(agort, kap, index, londra_fiyati)
    capalar = ons_capalari(gozlem, altin_deger_M, f["altin_fiyat"], aylik_ons)
    q = ons_serisi(capalar, index)
    qy = yukumluluk_ons_serisi(yukumluluk_gram, index)
    ayr = akim_ayristir(q["ons"], qy["ons_yukumluluk"], f["altin_fiyat"],
                        f["altin_fiyat_kaynak"], swap_haric, kamu_doviz_usd)
    etki = ayr

    out = pd.concat([f, q, qy, ayr], axis=1)
    bloklar = arife_bloklari(f["altin_fiyat_kaynak"].reindex(index))
    try:
        out["net_doviz_alimi_birikimli"] = birikimli_akim(
            out["net_doviz_alimi"], cipa, bloklar)
        out["altin_fiyat_etkisi_birikimli"] = birikimli_akim(
            out["altin_fiyat_etkisi"], cipa, bloklar)
        uyari_cipa: list[str] = cipa_tanisi(cipa, f.attrs.get("londra_bas"))
    except RuntimeError as e:
        out["net_doviz_alimi_birikimli"] = float("nan")
        out["altin_fiyat_etkisi_birikimli"] = float("nan")
        uyari_cipa = [f"BİRİKİMLİ AKIM ÜRETİLEMEDİ: {e}"]

    # Akımın hangi günlerinin GEÇİCİ olduğu (son çapadan sonrası) — grafikler
    # ve sayfa bunu görünür kılar; revizyon politikası modül notunda.
    # Net altın İKİ çapadan kurulur (brüt miktar ve yükümlülük); hangisi daha
    # eskiyse akım ondan sonra geçicidir.
    son_capa = capalar.index[-1] if not capalar.empty else None
    son_yuk = qy.attrs.get("son_capa")
    if son_capa is not None and son_yuk is not None:
        son_capa = min(son_capa, son_yuk)
    out["akim_gecici"] = (pd.Series(index > son_capa, index=index)
                          if son_capa is not None
                          else pd.Series(False, index=index))

    # DİKKAT: tazelik/taşıma tanılarında referans DUVAR SAATİDİR; verinin son
    # gününü referans almak denetimi kendi kendine referanslı hâle getirirdi.
    uyarilar = altin_tanilari(capalar, altin_deger_M, f["altin_fiyat"], etki)
    uyarilar += fiyat_tasima_tanisi(f["altin_fiyat_kaynak"])
    uyarilar += uyari_cipa
    uyarilar += yukumluluk_tazelik_tanisi(qy.attrs.get("son_capa"))
    uyarilar += sizinti_tanisi(out["net_doviz_alimi"], out["altin_fiyat_etkisi"],
                               out["akim_birlesik"])

    # Zincirleme tanısı (yayımlanmaz, denetlenir) — bkz. zincirleme_tanisi.
    # Γ net altınla kurulduğu için doğrudan etki de net miktarla ölçülür.
    d_t, uyari_zincir = zincirleme_tanisi(etki["altin_fiyat_etkisi"],
                                          out["ons_net"], f["altin_fiyat"], cipa)
    uyarilar += uyari_zincir
    out.attrs["zincirleme_dt"] = d_t
    out.attrs["son_ons_capa"] = son_capa
    out.attrs["londra_bas"] = f.attrs.get("londra_bas")
    out.attrs["geri_olcek"] = f.attrs.get("geri_olcek")
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
               "ons_yukumluluk", "swap_haric_usd", "kamu_doviz_mev_usd",
               "altin_usd", "doviz_usd"]
    eksik = [c for c in gerekli if c not in gunluk.columns]
    if eksik:
        raise RuntimeError(
            "gunluk.csv beklenen sütunları taşımıyor: " + ", ".join(eksik) +
            ". Önce `python net_rezerv.py` koşturun."
        )
    etki = akim_ayristir(gunluk["ons"], gunluk["ons_yukumluluk"],
                         gunluk["altin_fiyat"], gunluk["altin_fiyat_kaynak"],
                         gunluk["swap_haric_usd"], gunluk["kamu_doviz_mev_usd"])
    akim = etki
    out = pd.DataFrame(index=gunluk.index)
    out["altin_ons_mn"] = gunluk["ons"]
    out["altin_ons_yukumluluk_mn"] = gunluk["ons_yukumluluk"]
    out["altin_ons_net_mn"] = etki["ons_net"]
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
    out["akim_birlesik"] = akim["akim_birlesik"]
    out["kumulatif"] = birikimli_akim(
        out["net_alim_satim"], cipa,
        arife_bloklari(gunluk["altin_fiyat_kaynak"].reindex(out.index)))
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
    uyarilar += sizinti_tanisi(out["net_alim_satim"], out["altin_fiyat_etkisi"],
                               out["akim_birlesik"])
    _ld = gunluk["altin_fiyat_kaynak"].astype(str)
    _ld = _ld[_ld == "londra"]
    uyarilar += cipa_tanisi(args.capa, _ld.index[0] if len(_ld) else None)
    d_t, uyari_zincir = zincirleme_tanisi(out["altin_fiyat_etkisi"],
                                          out["altin_ons_net_mn"],
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
