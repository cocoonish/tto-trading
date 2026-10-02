#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 10 (Ticaret hadleri ve emtia) ölçüm katmanı.

Pratikler
  p10a  Emtia paraları: AUD–metal ve CAD–enerji (CNBC New York 17:00,
        Dünya Bankası Pink Sheet), NOK–enerji (ECB referans kuru çaprazı,
        14:15 Orta Avrupa): aylık log değişim korelasyonu, tam örneklem
        2000–2026 ve 36 aylık kayan; Newey–West eğimi ve örneklem dışı kıyas;
        öncü/gecikmeli korelasyon tablosu; 2014-06 → 2016-01 petrol düşüşü.
  p10b  2022 dolar şoku: 03.01.2022 → 31.10.2022 EUR, CAD, JPY (dolara
        karşı) ve enerji fiyatı; Türkiye: aylık Δlog enerji → ΔUSD/TRY,
        Δ2 yıllık DİBS, ve 12 aylık net enerji faturası 2013–2026.
        Yönetilen kur dönemi (2021-12 … 2023-06) kur ve faiz tepkisinde
        AYRI dönemdir, havuzlanmaz.
  sekil_17  aylık AUD–metal, CAD–enerji, NOK–enerji seviyeleri (2000=100)
            ve 36 aylık kayan korelasyonlar.
  p10c  Kur sürücüleri haritası (şartname 02.10.2026): 40 para–sürücü çifti
        (biri kaynakta yok; faiz farkı, emtia, risk, Çin, Türkiye), perşembeden perşembeye
        haftalık değişim 2010-01 → 2026-09; Pearson ve sıra korelasyonu,
        Newey–West eğimi, dört dönem, son 52 hafta, 52 haftalık kayan
        korelasyon, günlük gecikme (t, t−1, t+1), vade devri haftaları
        dışarıda ve plasebo, hüküm etiketi (istikrarlı · dönemsel · zayıf),
        para başına sürücü sıralaması, yerel getirilerin saat sınaması ve
        veri denetimi (kapsam, boşluk, bayat kotasyon, temizlik, devir).
  sekil_surucu_harita  para × sürücü grubu, 2015–2026 haftalık korelasyon.
  sekil_surucu_kayan   başlıca sekiz çiftin 52 haftalık kayan korelasyonu.
  sekil_usdjpy         USD/JPY ve ABD − Japonya 2/10 yıllık farkı: seviye
                       (iki ayrı panel), kayan korelasyon ve eğim.

YÖN. Para birimi serileri "yerel paranın dolar karşısındaki DEĞERİ" olarak
kurulur (artış değer kazancı): CNBC'de AUD XXX/USD olduğu için log(AUD/USD),
CAD USD/XXX olduğu için −log(USD/CAD); NOK, JPY ve EUR aynı kuralla. Türkiye
satırında ise ders sözleşmesi geçerlidir: s = log(USD/TRY), artış TL'nin
DEĞER KAYBI.

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. PINK SHEET AYLIK ORTALAMADIR, CNBC AY SONU DEĞERİ DEĞİL. Ay sonu kurun
     değişimi ile ay ortalaması emtia değişimini eşleştirmek iki şey yapar:
     eşzamanlı korelasyonu düşürür (AUD–metal 0,35; aynı iki seri ay
     ortalamasıyla 0,61) ve kurun bir AY ÖNCEKİ değişimini emtianın bu ayki
     değişimiyle aritmetik olarak ilişkilendirir (ortalamanın değişimi önceki
     ayın günlerini de taşır). Aritmetiğin BÜYÜKLÜĞÜ ölçüldü (denetim): kurun
     kendi ay ortalaması emtianın yerine konunca (aynı gün, öncülük yok) öncü
     korelasyon eşzamanlının 0,76 (AUD) – 0,84 (CAD) katı çıkıyor, yani
     aritmetik öncü korelasyonu eşzamanlının ALTINDA tutar. AUD–metalde öncü
     (0,48) eşzamanlıyı (0,35) aşıyor: aritmetiğin vereceği ≈0,27'nin üstünde
     ≈0,21'lik fazla aritmetik DEĞİLDİR. Ama ortalama penceresiyle örtüşmeyen
     iki ay öncü sınamada ilişki yok (AUD 0,10, t 0,8): fazla ortalama
     penceresinin dışına taşmıyor, "kur emtiayı öngörüyor" kuralı bu veriyle
     kurulamaz. CAD ve NOK'ta öncü korelasyon aritmetiğin verdiği düzeyde.
     Ana tanım ders planının istediği ay sonu kurudur; ay ortalaması hizası
     yanında durur ve öncü/gecikmeli tablo iki hizayı, plaseboyu ve
     örtüşmesiz sınamayı birlikte verir.
  2. CNBC kur dosyası hafta sonu barı da taşır (479 pazar, 6 cumartesi) ve 01–03.01.2020'de bozuk
     EUR/USD kotasyonu vardır. İkisi de ortak tanımda ayıklanır
     (`ortak_olc.cnbc_kur`: hafta içi, bozuk kotasyon günleri çıkarılmış); ay
     sonu değeri ve ay ortalaması oradan okunur.
  3. NOK New York kapanışı değil ECB 14:15 Orta Avrupa sabitlemesidir (euro
     çaprazından USD/NOK); ay sonu değeri ayın son sabitlemesidir. CAD ile
     NOK aynı satırda kıyaslanırken saat farkı adıyla yazılır.
  4. 2022 PENCERESİNDE ENERJİ AYLIK ORTALAMADIR: kur 03.01 → 31.10 günlük
     kapanışlarla, enerji Ocak → Ekim ay ortalamalarıyla ölçülür.
  5. DİBS HİZASI "gun_sonu" (`ortak_olc.DIBS_KAYMA`, k = 2): L etiketli DİBS
     değeri L−1'in sabah sabitlemesidir; ay sonu kur (Yahoo, CNBC) ve DXY gün
     sonu kapanışı olduğu için aylık Δ2 yıllık, D gününe D'den iki Türkiye iş
     günü sonraki etiket yazılarak kurulur (aynı günün gün sonu bilgisi).
     CUMA: 18.12.2023 öncesi Yahoo USD/TRY serisinde cumartesi barı yok; cuma
     biten ayın son değeri pazartesi barının başından (hafta sonu açılışından
     sonra) gelir. `usdtry(cuma_dus=True)` KULLANILMAZ: aylık değişim
     pencereleri bitişik kalır (her hafta sonu tek bir aya yazılır, hiçbiri iki
     kez ya da hiç sayılmaz); perşembeye çekmek o ayın cuma seansını ertesi
     aya taşırdı. Ölçüldü: yönetilen dönem dışı enerji eğimi ay sonu kurla
     −0,0656 (t −2,37), cuma boşaltılınca −0,0691 (t −2,37); hüküm değişmiyor
     (`p10b.turkiye.tepki.usdtry.cuma_duyarliligi`).
  6. ENERJİ FATURASI ile FİYAT: 12 aylık net enerji ithalatı ile 12 aylık
     ortalama enerji endeksi seviyede birlikte eğilimlidir; seviye
     regresyonu sahte ilişki riski taşır. Ana ölçü iki serinin 12 aylık log
     değişimidir; gecikme profili sözleşmelerin fiyata bağlanma gecikmesini
     (boru gazı fiyatı petrole birkaç ay gecikmeyle bağlanır) gösterir.
  7. USD/TRY'NİN EĞİLİMİ SIFIR KIYASINI BOZAR: Türkiye'de aylık kur
     değişiminin ortalaması sıfırdan belirgin büyüktür (kontrollü değer
     kaybı). Rastgele yürüyüş kıyası (değişim sıfır) bu yüzden modelin
     yalnız SABİT TERİMİNİ ödüllendirir: 2023-07 … 2026-08'de enerji eğimi
     sıfırken örneklem dışı oran sıfır kıyasına göre 0,14, koşulsuz ortalama
     kıyasına göre 1,10. Hüküm iki kıyasın da geçmesini ister (p10a'da da).
  8. TÜRKİYE'NİN ENERJİ–KUR EĞİMİ HİZAYA DUYARLI: yönetilen dönem dışında
     ay sonu kurla −0,07 (t −2,4; enerji pahalılaşınca TL değer kazanıyor;
     dolar endeksi kontrol edilince eğim −0,055'e iniyor, yani ortak etkenin
     bir kısmı dolardır — risk iştahı ayrıca ölçülmedi), aynı ilişki kur ay
     ortalamasıyla −0,03 (t −0,8). Mekanik hüküm "ölçülü" der; satır
     `hizaya_duyarli` bayrağını taşır ve metin onu kural olarak kuramaz.
  9. "%10'LUK FİYAT ARTIŞI" BASİT YÜZDEDİR (denetimde düzeltildi): esneklik
     log cinsindendir, %10'luk artışın etkisi 1,1^b − 1'dir; exp(0,1·b) − 1
     10 log puanlık (%10,5) artışı verir ve faturaya etkiyi ≈%5 büyütürdü
     (5,40'a karşı 5,13 milyar dolar).
  10. ÖRTÜŞEN 12 AYLIK DEĞİŞİMDE DM t'si: enerji faturası eşzamanlı ilişkisinin
     hataları 23 ay örtüşür; sözleşme fonksiyonunun varsayılan DM gecikmesi
     (3) t'yi şişirir. DM ayrıca 24 gecikmeyle verilir; hüküm sıfır ve
     koşulsuz ortalama kıyasının ikisini de ister.

  11. ORTAK GÜN (p10c). İki seri tek tek perşembeye kadarki son günüyle
     örneklense bazı haftalarda farklı günden okunur: Japonya 2 yıllık farkı
     ile yende haftaların %9,6'sı (80 hafta; Japonya tatilleri). Haftanın
     değeri bu yüzden iki serinin BİRLİKTE bulunduğu perşembeye kadarki son
     gündür; örneklenen gün ve perşembe payı satırda yazılı.
  12. ABD BACAĞI (p10c). ABD getirileri ABD Hazinesi par eğrisinden (resmî
     kaynak, altının reel faiz sürücüsüyle aynı yayım). Bedeli 1 bp çözünürlük
     (Hazine 2 yıllıkta sıfır değişimli günler 2012'de %46; CNBC 2 yıllık üç
     ondalıkla yazılır ve Hazine sıfırken günlerin %86'sında oynar). İLK
     GEREKÇE YANLIŞTI ve ölçüyle düzeltildi: "CNBC 10 yıllıkta değişimi sıfır
     görünen günlerin %59'unda Hazine oynuyor, demek ki CNBC bayat" tek yönlü
     bir çıkarımdı. Simetrik sınamada Hazine sıfırken CNBC de %56 oynuyor ve
     CNBC 10 yıllığın %98'i zaten 1 bp çözünürlükte: iki ayrı anlık görüntünün
     yuvarlaması, bayat kotasyon değil (alanlar `abd_bacagi`). CNBC'nin 2014
     boşlukları (Ocak–Mart, Ekim–Aralık) yerel getirilerde de var, fark
     satırına kazanç getirmez. Faiz farkı satırlarında ABD bacağı CNBC'den
     kurulunca korelasyon aynı günlerde ikinci ondalıkta aynı (yen 2 yıllık
     0,4647 ile 0,4643).
  13. GERİ DÖNEN SIÇRAMA (p10c). Avustralya 2 yıllık 21.04.2025'te 0,020
     yazıyor (önce 3,299, sonra 3,233: −328 ve +321 bp); COP 28.12.2010'da
     2033 (önce 1938, sonra 1936). Kural tek tanımda
     (`ortak_olc.geri_donen_sicrama`); getiride 100 bp (en büyük meşru günlük
     hareket İsviçre 2 yıllıkta 63,9 bp, 21.03.2023), kurda EM eşiği (%3,5).
     Emtia TEMİZLENMEZ: aynı kural 2015'te Brent'in gerçek oynak günlerini de
     yakalıyor.
  14. VADE DEVRİ (p10c). CNBC'nin yakın vadesi sözleşmeyi son işlem gününe
     kadar tutar (keşifte ham hacimle görüldü: WTI 21.04.2020'de 10,01 ve
     hacim 18 bin, ertesi gün yeni sözleşme 13,78 ve hacim 1,2 milyon).
     Devir günü borsa kuralından tahmin edilir; kural ham hacim sıçramasına
     karşı keşifte sınandı (modül hacmi okumaz): hacim adaylarının Brent'te
     %92'si, WTI'de %81'i kural gününün ±1 iş günü içinde; metallerde aday
     kümesi gürültülü (%51–57), pencere −1 … +3. Devir gününde günlük
     oynaklık fazlası ölçülür (Brent sd %3,08 · öbür günler %2,27; demir
     cevheri %9,27 · %1,44). Haftalık korelasyon devir haftaları dışarıda
     bırakılınca Brent ve WTI çiftlerinde +0,01 … +0,05 artıyor, aynı sayıda
     rastgele haftayla kurulan plasebonun %90 bandının içinde ya da
     kıyısında; demir cevherinde BRL 0,10 → 0,17, bandın dışında.
  15. SAAT (p10c). Asya-Pasifik kapanışlı getiri bir önceki New York gününü
     taşır: Avustralya 2 yıllığın günlük değişiminin ABD 2 yıllığın aynı
     günüyle korelasyonu 0,07, bir önceki günüyle 0,43 (Japonya 10 yıllık
     0,13 · 0,34); Almanya aynı gün (0,49 · 0,10). Yen yerel bacakla EKSİ
     (haftalık 2 yıllık −0,08, 10 yıllık −0,23): Japonya getirisi ABD'yi
     izliyor; farkın korelasyonunu ABD bacağı taşıyor (−0,48).
  16. SEVİYE (sekil_usdjpy). USD/JPY ile ABD − Japonya 2 yıllık farkı
     seviyede 0,79, dönemlerde −0,40 (2015–2019) ile +0,96 (2020–2022)
     arasında; haftalık değişimde 0,46 ve dört dönemde artı. Seviye yalnız
     figür ve uyarıdır.
  17. KAPSAM (p10c). Yeni Zelanda 2 yıllık getirisi kaynakta yok: çift
     kurulmadı, 10 yıllık fark ikame satırdır. Kanada 2 yıllık 2020-04'te
     başlar: dört dönemin ikisinde ölçülebildiği için 'istikrarlı' olamaz,
     10 yıllık fark uzun örneklemi verir. Japonya 2 yıllıkta ardışık aynı
     değer payı 2012'de %53: sıfıra yakın faizde bayat kotasyon ile gerçek
     durgunluk veriyle ayrılamaz, payı yıl yıl yazılı.
  18. TÜRKİYE (p10c). USD/TRY Yahoo'dan; yönetilen kur dönemi (2021-12 …
     2023-06) dışarıda ve ayrı dönem. TRY–Brent ARTI (0,08, t 2,5; beklenen
     eksi), 'dönemsel': 2010–2014'te +0,31, sonraki dönemlerde sıfır
     civarı — p10b'deki aylık bulgunun haftalık eşi.
  19. KIYAS SÜTUNU ÖRNEKLEMİ BELİRLEYEMEZ (p10c, doğrulama turu). İlk yazımda
     faiz farkı satırlarının ortak günü, yalnız kaynak kıyası için okunan
     CNBC ABD bacağını da istiyordu: CNBC'nin eksik ya da ayrı günü olan
     haftalarda ana ölçü başka günden örnekleniyordu (çift başına 24–66
     hafta; yen 2 yıllık 0,4610 yerine 0,4643, sterlin 0,2344 yerine
     0,2358). Ana ölçünün ortak günü artık yalnız para ve farkın kendisidir;
     kaynak kıyası iki tanımın birlikte bulunduğu günlerde ayrı kurulur ve
     Hazine tanımı da AYNI günlerde yan yana yazılır. Bağımsız yeniden
     hesapla (modülün fonksiyonları kullanılmadan) altı çift — yen–2y,
     NOK–Brent, CAD–WTI, AUD–bakır, altın–reel faiz, TRY–Brent — n, korelasyon
     ve eğimde dört ondalığa kadar tutuyor.
  20. TRY'NİN GÜNLÜK ÖLÇÜSÜNDE CUMA (p10c). 18.12.2023 öncesi USD/TRY'nin cuma
     değeri pazartesi barının başıdır ve hafta sonunu taşır
     (`ortak_olc.usdtry`); günlük gecikme ölçüsü o cumaları kullanıyordu.
     Artık `cuma_dus=True` serisinden: cuma ve pazartesi değişimi düşer
     (TRY–VIX gecikme-0 −0,181 → −0,195, TRY–Brent 0,089 → 0,095). Haftalık
     ölçü perşembeyi örneklediği için etkilenmez (örneklenen günlerin
     869'u perşembe, 11'i çarşamba, 2'si salı; cuma yok).
  21. KAPSAM KIYASI (p10c, sıralama ve harita). Kanada 2 yıllık 2020-04'te
     başlıyor ve 2015–2026 penceresinin %55'ini taşıyor; ilk yazımda yine de
     CAD'nin "en güçlü sürücüsü" sayılıyordu (0,399; aynı pencerede WTI
     0,392, 10 yıllık fark 0,388 — farklı örneklemlerin korelasyonu). Demir
     cevheri (2016-11 → 2020-09 boş) %64, İsviçre 2 yıllık 2010–2014'te %41.
     Kural: hafta sayısı paranın en geniş kapsamlı sürücüsününkinin
     `SRC_KAPSAM_ORAN`ından azsa listede adıyla durur, "en güçlü" sayılmaz.
     Eşik iki ölçülmüş kümenin arasında (%41–64 ile CNBC'nin ortak 2014
     boşluklarının %83–91'i); %90 seçilseydi Japonya 10 yıllık 2010–2014'te
     %89,6 ile yalnız ortak boşluk yüzünden dışlanırdı.
  22. BAYAT YEREL BACAK ÖLÇÜLDÜ (p10c). Japonya 2 yıllıkta ardışık aynı değer
     payı 2000 sonrası %18, 2010 sonrası %14, 2012'de %53. Yerel bacağın
     haftalık değişimi tam sıfır olan haftalar (yen 2 yıllıkta 826'nın 76'sı)
     dışarıda bırakılınca korelasyon 0,461 → 0,466, aynı sayıda rastgele
     hafta dışarıda bırakan plaseboyla aynı band içinde; 2010–2014'te ise
     0,325 → 0,274 (bayat haftalarda fark tamamen ABD bacağıdır ve yen
     ABD bacağını izliyor). Farkın haftalık varyansının ABD bacağından gelen
     payı yen 2 yıllıkta %98 (dönemlerde %93–101). Bütün faiz farkı
     satırlarında `bacaklar_haftalik.bayat_yerel_hafta`.
  23. İŞARET HÜKMÜ |t| İSTER (p10c). CHF–VIX korelasyonu 0,001 (t 0,03) iken
     "beklenen işaret tutuyor: evet" yazılıyordu. |t| < 2'de alan boştur ve
     sebebi yazılıdır.
  24. SAAT İZİNİN KONTROLÜ (p10c). Haftalık eksi günlük gecikme-0 korelasyonu
     yalnız saatten gelmez; iki serisi de New York 17:00 kapanışı olan
     AUD–yuan çiftinde fark 0,006 (kontrol), emtia vadelisi çiftlerinde
     mutlak değerce 0,04–0,16 (eksi korelasyonlu çiftte fark eksidir: altın–
     reel faiz −0,15; vadeli barının kapanış saati kaynakta yazılı değil).
     Kontrol `saat_kontrolu`nda.
     Vade devri takvimi vadelinin kendi işlem günlerinde sayılır: her hafta
     içi gününü iş günü sayan takvim WTI'de 29 ayda (Şükran Günü, Noel, Kutsal
     Cuma, Anma Günü) son işlem gününü bir gün kaydırırdı; kendi takvim ise
     Brent'te 3 ayda veri boşluğunu tatil sayıyor (15.01.2016 barı yok), ±1
     günlük pencere bunu kapsıyor.

ÖLÇÜLEN BULGU (tuzak değil): CAD–enerji ve NOK–enerji 36 aylık kayan
korelasyonu 2024 sonundan itibaren eksiye döndü (ikisi de 2024-11'den beri,
22 ay; CAD'de en düşük −0,44, 2025-09; 2022 ortasında +0,54'tü);
2014–2016 petrol düşüşünde enerji ithalatçısı EUR da CAD'ye yakın değer
kaybetti (−22 ile −27 log puan) ve dolar endeksi aynı pencerede +21 log puan
yükseldi: o dönemin baskın terimi doların kendisiydi.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo
import olcum_b08 as b08

warnings.filterwarnings("ignore", message="Could not infer format")   # ovp_programlar ilk sütunu tarih değil
warnings.filterwarnings("ignore", category=FutureWarning)

# ───────────────────────────────────────────────────────── sabitler (adlı)
BAS = "2000-02-01"            # CNBC 2000-01-03'te başlar: ilk aylık değişim Şubat 2000
SON = str(oo.CIPA_AY.to_timestamp().date())    # Pink Sheet çıpası (2026-08)
KAYAN_AY = 36
KAYAN_ASGARI = 30
OOS_ILK_AY = 120
PETROL = ("2014-06-01", "2016-01-01", "2014-06 → 2016-01 petrol düşüşü")
SOK_2022 = ("2022-01-03", "2022-10-31")
TR_BAS = "2013-02-01"         # DİBS eğrisi 2013-01'de başlar: ilk aylık değişim Şubat 2013
YON_BAS, YON_SON = oo.YONETILEN
DIBS_HIZA = "gun_sonu"        # ay sonu kur ve DXY gün sonu kapanışı (tuzak 5)
TR_DONEMLER = (("oncesi", TR_BAS, oo.YON_ONCESI_SON_AY, f"2013-02 … {oo.YON_ONCESI_AY}"),
               ("yonetilen", oo.YON_ILK, oo.YON_SON_AY, f"yönetilen kur {oo.YON_AY[0]} … {oo.YON_AY[1]} (ayrı dönem)"),
               ("sonrasi", f"{oo.YON_SONRASI_AY}-01", SON, f"{oo.YON_SONRASI_AY} … 2026-08"))
FATURA_BAS = "2013-01-01"
FATURA_AZAMI_GECIKME = 12


_iso, kurulmadi, hukum = oo._iso, oo.kurulmadi, oo.hukum      # tek tanımlar ortak_olc'de
_reg = oo.reg


def _oos_iki(y: pd.Series, x: pd.Series, ilk: int) -> tuple[dict, dict, str | None]:
    """İki saf kıyas (`ortak_olc.oos_takimi`, ufuk 1): (sıfır, koşulsuz ortalama, hüküm için oranlar)."""
    tk = oo.oos_takimi(y, x, ilk)
    return tk["sifir"], tk["ortalama"], oo.takim_oranlari(tk)


# ───────────────────────────────────────────────────────── seriler
def _cnbc() -> pd.DataFrame:
    """CNBC kurları, ortak tanım (tuzak 2)."""
    return oo.cnbc_kur()


def _deger(seri: pd.Series, ters: bool) -> pd.Series:
    """Yerel paranın dolar karşısındaki değeri, log×100 (artış değer kazancı)."""
    x = np.log(seri.dropna()) * 100
    return -x if ters else x


@lru_cache(maxsize=2)
def _aylik_kurlar(hiza: str) -> pd.DataFrame:
    """hiza: 'son' ay sonu (son hafta içi kapanış), 'ort' ay ortalaması."""
    c = _cnbc()
    a = c.resample("MS").last() if hiza == "son" else c.resample("MS").mean()
    out = pd.DataFrame({"aud": _deger(a["aud"], False), "cad": _deger(a["cad"], True),
                        "eur": _deger(a["eur"], False), "jpy": _deger(a["jpy"], True)})
    try:
        nok = _usd_nok()
        out["nok"] = _deger(nok.resample("MS").last() if hiza == "son" else nok.resample("MS").mean(), True)
    except bulut.VeriYok:
        pass
    return out


@lru_cache(maxsize=1)
def _usd_nok() -> pd.Series:
    """USD/NOK = (EUR/NOK)/(EUR/USD), ECB 14:15 Orta Avrupa; hafta içi."""
    x = (bulut.ecb_kur("NOK") / bulut.ecb_kur("USD")).dropna()
    x = x[(x.index.dayofweek < 5) & (x.index <= oo.CIPA_GUN)]
    x.name = "usdnok"
    return x


@lru_cache(maxsize=1)
def _emtia() -> pd.DataFrame:
    k = oo.oku("kuresel_aylik")
    return pd.DataFrame({"metal": np.log(k["emtia_metal"]) * 100,
                         "enerji": np.log(k["emtia_enerji"]) * 100}).dropna()


def _cift(fx: str, emtia: str, hiza: str) -> pd.DataFrame:
    a = _aylik_kurlar(hiza)
    if fx not in a.columns:
        raise bulut.VeriYok("ECB referans kurları: NOK elde yok")
    d = pd.concat([a[fx].diff().rename("fx"), _emtia()[emtia].diff().rename("em")], axis=1)
    return d.loc[BAS:SON].dropna()


# ───────────────────────────────────────────────────────── p10a
def _kayan(d: pd.DataFrame) -> pd.Series:
    return d["fx"].rolling(KAYAN_AY, min_periods=KAYAN_ASGARI).corr(d["em"]).dropna()


def _kor_tablosu(a: pd.Series, e: pd.Series) -> dict:
    out = {}
    for ad, k in (("kur_bir_ay_onde", 1), ("es_zamanli", 0), ("emtia_bir_ay_onde", -1)):
        # kur_bir_ay_onde: kurun t−1 ayındaki değişimi ile emtianın t ayındaki değişimi
        d = pd.concat([a.shift(k).rename("fx"), e.rename("em")], axis=1).loc[BAS:SON].dropna()
        out[ad] = {"kor": float(d["fx"].corr(d["em"])), "n": int(len(d))}
    return out


def _oncu_gecikmeli(fx: str, emtia: str, hiza: str) -> dict:
    a = _aylik_kurlar(hiza)[fx].diff()
    e = _emtia()[emtia].diff()
    out = _kor_tablosu(a, e)
    if hiza != "son":
        return out
    # Ay sonu kur ~ ay ortalaması emtia hizasında aritmetiğin payı: emtianın yerine kurun KENDİ
    # ay ortalaması konur (aynı günler, öncülük yok). Bu plasebonun öncü/eşzamanlı oranı,
    # ortalama almanın tek başına üreteceği öncü korelasyonu verir.
    oz = _kor_tablosu(a, _aylik_kurlar("ort")[fx].diff())
    oran = oz["kur_bir_ay_onde"]["kor"] / oz["es_zamanli"]["kor"]
    beklenen = oran * out["es_zamanli"]["kor"]
    # Örtüşmesiz öncülük: kurun t−2 ayındaki değişimi, emtianın t ayı ortalama değişimiyle (ortalamanın
    # kapsadığı t−1 ve t aylarıyla örtüşmez). Öngörü iddiası ancak burada kurulabilir.
    d = pd.concat([a.shift(2).rename("x"), e.rename("y")], axis=1).loc[BAS:SON].dropna()
    r = _reg(d["y"], d["x"], gecikme=None)
    out.update({
        "plasebo_kurun_kendi_ortalamasi": {"kur_bir_ay_onde": oz["kur_bir_ay_onde"]["kor"],
                                           "es_zamanli": oz["es_zamanli"]["kor"], "oncu_es_orani": oran},
        "aritmetik_beklenen_oncu_kor": beklenen,
        "aritmetik_disi_fazla": out["kur_bir_ay_onde"]["kor"] - beklenen,
        "kur_iki_ay_onde_ortusmesiz": {"kor": float(d["x"].corr(d["y"])), "egim": r["b"][0], "t": r["t"][0],
                                       "n": r["n"], "gecikme": r["gecikme"]},
    })
    return out


def _cift_olc(fx: str, emtia: str, ad: str) -> dict:
    try:
        d = _cift(fx, emtia, "son")
        d_ort = _cift(fx, emtia, "ort")
    except bulut.VeriYok as hata:
        return kurulmadi(str(hata))
    r = _reg(d["fx"], d["em"], gecikme=None)
    oos, oos_ort, oranlar = _oos_iki(d["fx"], d["em"], OOS_ILK_AY)
    kay = _kayan(d)
    kay_ort = _kayan(d_ort)
    son = kay.index.max()
    out = {
        "yontem": (f"{ad}: yerel paranın dolar karşısındaki değerinin aylık log değişimi ile emtia endeksinin "
                   "aylık log değişimi arasındaki korelasyon ve Newey–West eğimi; kur ay sonu kapanışı, "
                   "emtia Pink Sheet ay ortalaması; örneklem dışı kıyas hem rastgele yürüyüş (değişim sıfır) hem "
                   "koşulsuz ortalama."),
        "n": int(len(d)), "ilk": _iso(d.index.min()), "son": _iso(d.index.max()),
        "kor_ay_sonu": float(d["fx"].corr(d["em"])),
        "kor_ay_ortalamasi": float(d_ort["fx"].corr(d_ort["em"])),
        "n_ay_ortalamasi": int(len(d_ort)),
        "egim_yuzde_yuzde": r["b"][0], "se": r["se"][0], "t": r["t"][0], "r2": r["r2"], "gecikme": r["gecikme"],
        "oos": oos, "oos_ortalama": oos_ort,
        "hukum": hukum(r["t"][0], oranlar),
        "kayan_36ay": {"son_tarih": _iso(son), "son": float(kay.loc[son]),
                       "en_dusuk": float(kay.min()), "en_dusuk_tarih": _iso(kay.idxmin()),
                       "en_yuksek": float(kay.max()), "en_yuksek_tarih": _iso(kay.idxmax()),
                       "medyan": float(kay.median()), "eksi_ay_payi_yuzde": float((kay < 0).mean() * 100),
                       "n_pencere": int(len(kay)),
                       "son_eksi_dizi_baslangic": _eksi_dizi(kay)[0], "son_eksi_dizi_ay": _eksi_dizi(kay)[1],
                       "ay_ortalamasi_son": float(kay_ort.iloc[-1]), "ay_ortalamasi_medyan": float(kay_ort.median())},
        "oncu_gecikmeli": {"ay_sonu": _oncu_gecikmeli(fx, emtia, "son"),
                           "ay_ortalamasi": _oncu_gecikmeli(fx, emtia, "ort"),
                           "not": ("Kur bir ay önde: kurun önceki ayki değişimi ile emtianın bu ayki değişimi. "
                                   "Ay sonu hizasında bu korelasyonun bir kısmı ortalama alma aritmetiğidir; "
                                   "aritmetiğin payı kurun kendi ay ortalamasıyla kurulan plasebodan ölçülür ve "
                                   "eşzamanlı korelasyonun altında kalır. Öngörü iddiası yalnız ortalama "
                                   "penceresiyle örtüşmeyen iki ay öncü sınamada kurulabilir.")},
    }
    return out


def _eksi_dizi(kay: pd.Series) -> tuple:
    """Kayan korelasyonun sondaki kesintisiz eksi dizisi: (başlangıç ayı, uzunluk); son değer eksi değilse (None, 0)."""
    if kay.empty or kay.iloc[-1] >= 0:
        return None, 0
    arti = kay[kay >= 0]
    dizi = kay[kay.index > arti.index.max()] if len(arti) else kay
    return _iso(dizi.index.min()), int(len(dizi))


def _bolum(a: pd.DataFrame, e: pd.DataFrame, fx: str, emtia: str, bas: str, son: str) -> dict:
    if fx not in a.columns:
        return kurulmadi("ECB referans kurları: NOK elde yok")
    dfx = float(a.loc[son, fx] - a.loc[bas, fx])
    dem = float(e.loc[son, emtia] - e.loc[bas, emtia])
    return {"kur_degisim_log_yuzde": dfx, "kur_degisim_yuzde": float(100 * (math.exp(dfx / 100) - 1)),
            "emtia_degisim_log_yuzde": dem, "emtia_degisim_yuzde": float(100 * (math.exp(dem / 100) - 1)),
            "oran_kur_emtia": dfx / dem if dem else None}


def _petrol_dusus() -> dict:
    bas, son, ad = PETROL
    e = _emtia()
    son_ = _aylik_kurlar("son")
    ort_ = _aylik_kurlar("ort")
    out = {"ad": ad, "ilk": bas, "son": son,
           "yontem": ("Haziran 2014'ten Ocak 2016'ya emtia endeksinin ay ortalaması ve paranın dolar karşısındaki "
                      "değeri (ay ortalaması; ay sonu kapanışı sağlamlık) log değişimi."),
           "enerji_degisim_log_yuzde": float(e.loc[son, "enerji"] - e.loc[bas, "enerji"]),
           "metal_degisim_log_yuzde": float(e.loc[son, "metal"] - e.loc[bas, "metal"])}
    out["enerji_degisim_yuzde"] = float(100 * (math.exp(out["enerji_degisim_log_yuzde"] / 100) - 1))
    for fx, em in (("cad", "enerji"), ("nok", "enerji"), ("aud", "metal")):
        out[fx] = {"ay_ortalamasi": _bolum(ort_, e, fx, em, bas, son),
                   "ay_sonu": _bolum(son_, e, fx, em, bas, son)}
    out["eur_kiyas"] = {"ay_ortalamasi": _bolum(ort_, e, "eur", "enerji", bas, son)}
    # doların kendi hareketi (ay ortalaması, aynı pencere): "baskın terim dolar" cümlesinin ölçüsü
    dx = oo.oku("yahoo_dxy_vix_gunluk")["dxy"].dropna()
    dx = np.log(dx[dx.index.dayofweek < 5].resample("MS").mean()) * 100
    out["dxy_degisim_log_yuzde"] = float(dx.loc[son] - dx.loc[bas])
    out["n"] = sum(1 for k in ("cad", "nok", "aud") if out[k]["ay_ortalamasi"].get("durum") is None) + 1  # + EUR kıyası
    out["vaka_tablosu"] = True
    out["saat_notu"] = "CAD ve AUD New York 17:00, NOK ECB 14:15 Orta Avrupa sabitlemesinden, dolar endeksi New York kapanışı."
    return out


def p10a() -> dict:
    aud = _cift_olc("aud", "metal", "AUD–metal")
    return {
        "yontem": ("Emtia ihracatçısı paraların (AUD, CAD, NOK) dolar karşısındaki aylık değeri ile ilgili emtia "
                   "endeksinin aylık log değişimleri arasındaki eşzamanlı, öncü ve kayan korelasyon; 2014–2016 "
                   "petrol düşüşünde kur ve emtia değişimi."),
        "n": aud.get("n"), "ilk": aud.get("ilk"), "son": aud.get("son"),
        "kaynak": ["cnbc_kur_gunluk (AUD/USD, USD/CAD, EUR/USD; New York 17:00)",
                   "kuresel_aylik (Pink Sheet metal ve enerji endeksleri, nominal dolar, ay ortalaması)",
                   "bulut: ECB referans kurları (USD/NOK çaprazı, 14:15 Orta Avrupa)",
                   "yahoo_dxy_vix_gunluk (dolar endeksi, petrol penceresi)"],
        "aud_metal": aud,
        "cad_enerji": _cift_olc("cad", "enerji", "CAD–enerji"),
        "nok_enerji": _cift_olc("nok", "enerji", "NOK–enerji"),
        "petrol_2014_2016": _petrol_dusus(),
    }


# ───────────────────────────────────────────────────────── p10b
def _sok_2022() -> dict:
    c = _cnbc()
    b, s = pd.Timestamp(SOK_2022[0]), pd.Timestamp(SOK_2022[1])
    paralar = {}
    for kod, ters in (("eur", False), ("cad", True), ("jpy", True), ("gbp", False), ("aud", False), ("chf", True)):
        x0, x1 = float(c.loc[b, kod]), float(c.loc[s, kod])
        dlog = 100 * math.log(x1 / x0) * (-1 if ters else 1)
        paralar[kod] = {"degisim_log_yuzde": dlog, "degisim_yuzde": float(100 * (math.exp(dlog / 100) - 1)),
                        "baz": x0, "son": x1, "kote": "USD/XXX" if ters else "XXX/USD",
                        "rol": {"eur": "enerji ithalatçısı", "jpy": "enerji ithalatçısı",
                                "cad": "enerji ihracatçısı"}.get(kod, "kıyas")}
    dx = oo.oku("yahoo_dxy_vix_gunluk")["dxy"].dropna()
    ab = oo.oku("abd_hazine_gunluk")["us2"].dropna()
    e = oo.oku("kuresel_aylik")["emtia_enerji"]
    e0, e1 = float(e.loc["2022-01-01"]), float(e.loc["2022-10-01"])
    out = {
        "yontem": ("3 Ocak 2022 ile 31 Ekim 2022 kapanışları arasında paranın dolar karşısındaki değerinin log "
                   "değişimi (eksi değer kaybı); enerji Ocak ve Ekim ay ortalamaları arasında."),
        "kaynak": ["cnbc_kur_gunluk (New York 17:00)", "kuresel_aylik (Pink Sheet enerji, ay ortalaması)",
                   "yahoo_dxy_vix_gunluk (DXY)", "abd_hazine_gunluk (2 yıllık par getiri)"],
        "ilk": SOK_2022[0], "son": SOK_2022[1], "n": len(paralar),
        "paralar": paralar,
        "dxy_degisim_log_yuzde": float(100 * math.log(dx.loc[s] / dx.loc[b])),
        "abd_2y_degisim_bp": float((ab.loc[s] - ab.loc[b]) * 100),
        "abd_2y_baz_yuzde": float(ab.loc[b]), "abd_2y_son_yuzde": float(ab.loc[s]),
        "enerji_degisim_log_yuzde": float(100 * math.log(e1 / e0)),
        "enerji_degisim_yuzde": float(100 * (e1 / e0 - 1)),
        "enerji_zirve_ay": _iso(e.loc["2022-01-01":"2022-10-01"].idxmax()),
        "enerji_zirveye_log_yuzde": float(100 * math.log(e.loc["2022-01-01":"2022-10-01"].max() / e0)),
        "cad_eksi_eur_puan": paralar["cad"]["degisim_log_yuzde"] - paralar["eur"]["degisim_log_yuzde"],
        "cad_eksi_jpy_puan": paralar["cad"]["degisim_log_yuzde"] - paralar["jpy"]["degisim_log_yuzde"],
        "saat_notu": "Kurlar New York 17:00, ABD 2 yıllık getiri New York kapanışı, enerji aylık ortalama.",
        "vaka_tablosu": True,
    }
    return out


@lru_cache(maxsize=2)
def _tr_aylik(cuma_dus: bool = False) -> pd.DataFrame:
    s, _ = oo.usdtry(cuma_dus=cuma_dus)
    s = s.dropna()
    d = oo.dibs(DIBS_HIZA, ("n2y",))["n2y"].dropna()      # Türkiye iş günü takviminde, gün sonu hizası
    dx = oo.oku("yahoo_dxy_vix_gunluk")["dxy"].dropna()
    dx = dx[dx.index.dayofweek < 5]
    ls = np.log(s) * 100
    df = pd.DataFrame({
        "denerji": _emtia()["enerji"].diff(),
        "dkur": ls.resample("MS").last().diff(),
        "dkur_ort": (np.log(s.resample("MS").mean()) * 100).diff(),
        "dn2y_bp": (d.resample("MS").last() * 100).diff(),
        "ddxy": (np.log(dx.resample("MS").last()) * 100).diff(),
    })
    return df.loc[TR_BAS:SON]


def _donem_reg(z: pd.DataFrame, yad: str) -> dict:
    d = z[[yad, "denerji", "ddxy"]].dropna()
    if len(d) < 12:
        return kurulmadi("dönemde gözlem yetersiz")
    r = _reg(d[yad], d["denerji"], gecikme=None)
    rk = _reg(d[yad], d[["denerji", "ddxy"]], gecikme=None)
    out = {"n": r["n"], "ilk": r["ilk"], "son": r["son"], "egim": r["b"][0], "se": r["se"][0], "t": r["t"][0],
           "r2": r["r2"], "gecikme": r["gecikme"], "kor": float(d[yad].corr(d["denerji"])),
           "dolar_kontrollu": {"egim": rk["b"][0], "se": rk["se"][0], "t": rk["t"][0],
                               "dxy_egim": rk["b"][1], "dxy_t": rk["t"][1], "r2": rk["r2"]}}
    ilk = max(24, len(d) // 2)
    if len(d) - ilk >= 10:
        oos, oos_ort, oranlar = _oos_iki(d[yad], d["denerji"], ilk)
        out["oos"] = oos
        out["oos_ortalama"] = oos_ort
        out["hukum"] = hukum(r["t"][0], oranlar)
    else:
        out["oos"] = kurulmadi("örneklem dışı sınama için en az on tahmin gerekir")
        out["oos_ortalama"] = kurulmadi("örneklem dışı sınama için en az on tahmin gerekir")
        out["hukum"] = "tarif edici"
    return out


def _tr_tepki() -> dict:
    df = _tr_aylik()
    yon = (df.index >= YON_BAS) & (df.index <= YON_SON)
    out = {}
    for yad, ad in (("dkur", "usdtry"), ("dn2y_bp", "dibs_2y")):
        bl = {}
        for anahtar, bas, son, etiket in TR_DONEMLER:
            bl[anahtar] = {"etiket": etiket, **_donem_reg(df.loc[bas:son], yad)}
        bl["yonetilen_haric"] = {"etiket": "2013-02 … 2021-11 ve 2023-07 … 2026-08 (yönetilen dönem dışarıda)",
                                 **_donem_reg(df[~yon], yad)}
        out[ad] = bl
    dc = _tr_aylik(cuma_dus=True)
    yc = (dc.index >= YON_BAS) & (dc.index <= YON_SON)
    rc = _donem_reg(dc[~yc], "dkur")
    out["usdtry"]["cuma_duyarliligi"] = {
        "etiket": "yönetilen dönem dışı, 18.12.2023 öncesi cuma kur değeri boşaltılmış (ay perşembe kapanışıyla biter)",
        "n": rc.get("n"), "egim": rc.get("egim"), "t": rc.get("t"), "hukum": rc.get("hukum"),
        "not": "Ana tanım cuma değerini tutar: aylık pencereler bitişik kalır (tuzak 5)."}
    out["usdtry"]["ay_ortalamasi_yonetilen_haric"] = {
        "etiket": "aynı ilişki, kur ay ortalamasıyla (emtia ile aynı hiza)", **_donem_reg(df[~yon], "dkur_ort")}
    out["birim"] = {"usdtry": "USD/TRY'nin aylık log değişimi (%) / enerji endeksinin aylık log değişimi (%)",
                    "dibs_2y": "2 yıllık DİBS getirisinin aylık değişimi (bp) / enerji endeksinin aylık log değişimi (%)"}
    out["isaret"] = "USD/TRY'de artı eğim: enerji pahalılaştığında TL değer kaybeder."
    out["kiyas_notu"] = ("USD/TRY'nin aylık değişiminde belirgin bir eğilim (sürekli değer kaybı) var: sıfır kıyası "
                         "yalnız sabit terimi ödüllendirir, bu yüzden hüküm koşulsuz ortalama kıyasını da ister.")
    hk = out["usdtry"]["yonetilen_haric"]
    ho = out["usdtry"]["ay_ortalamasi_yonetilen_haric"]
    hk["hizaya_duyarli"] = bool(np.sign(hk.get("egim") or 0) != np.sign(ho.get("egim") or 0)
                                or (abs(hk.get("t") or 0) >= 2) != (abs(ho.get("t") or 0) >= 2))
    out["hiza_notu"] = ("Ay sonu kurla kurulan eğim ve aynı ilişkinin kur ay ortalamasıyla (enerjiyle aynı hiza) "
                        "kurulan eğimi yan yana: ikisi ayrışıyorsa sonuç hizaya duyarlıdır.")
    out["hiza_duyarliligi"] = {"ay_sonu_egim": hk.get("egim"), "ay_sonu_t": hk.get("t"),
                               "ay_ortalamasi_egim": ho.get("egim"), "ay_ortalamasi_t": ho.get("t"),
                               "isaret_ayni": bool(hk.get("egim") is not None and ho.get("egim") is not None
                                                   and np.sign(hk["egim"]) == np.sign(ho["egim"])),
                               "ikisi_de_anlamli": bool(abs(hk.get("t") or 0) >= 2 and abs(ho.get("t") or 0) >= 2)}
    return out


def _fatura() -> dict:
    o = oo.oku("odemeler_aylik")
    fatura = -o["hc_enerji_net"].rolling(12, min_periods=12).sum() / 1e3       # milyar USD, artı = net ithalat
    fiyat = oo.oku("kuresel_aylik")["emtia_enerji"].rolling(12, min_periods=12).mean()
    G = b08.aylik_gsyh_usd()
    df = pd.DataFrame({"lf": np.log(fatura) * 100, "lp": np.log(fiyat) * 100}).loc[FATURA_BAS:].dropna()
    d12 = df.diff(12)
    profil = {"gecikme_ay": [], "esneklik": [], "se": [], "t": [], "r2": []}
    for k in range(FATURA_AZAMI_GECIKME + 1):
        r = _reg(d12["lf"], d12["lp"].shift(k), gecikme=b08.HAC_GECIKME)
        profil["gecikme_ay"].append(k); profil["esneklik"].append(r["b"][0]); profil["se"].append(r["se"][0])
        profil["t"].append(r["t"][0]); profil["r2"].append(r["r2"])
    j = int(np.argmax(profil["r2"]))
    r0 = _reg(d12["lf"], d12["lp"], gecikme=b08.HAC_GECIKME)
    dd = d12.dropna()
    # eşzamanlı ilişki: ambargo 1; hatalar 23 ay örtüştüğü için DM t'si 24 gecikmeyle (tuzak 10)
    oos = b08.oos_takim(dd["lf"], dd["lp"], min(60, len(dd) // 2), 1, b08.HAC_GECIKME)
    sev = _reg(df["lf"], df["lp"], gecikme=b08.HAC_GECIKME)
    son = fatura.dropna().index.max()
    oran = (fatura * 1e3 / G * 100).dropna().loc[FATURA_BAS:]
    son_fatura = float(fatura.loc[son])
    on_yuzde = 1.1 ** r0["b"][0] - 1          # %10'luk (basit) fiyat artışının faturaya oranı (tuzak 9)
    return {
        "yontem": ("12 aylık net enerji ithalatının (milyar dolar) 12 aylık log değişimi, Pink Sheet enerji "
                   "endeksinin 12 aylık ortalamasının k ay önceki 12 aylık log değişimine regrese edildi (esneklik); "
                   "standart hata Newey–West (gecikme 24), örneklem dışı kıyas koşulsuz ortalama ve değişimin "
                   "sıfır olması."),
        "kaynak": ["odemeler_aylik (hc_enerji_net, milyon USD)", "kuresel_aylik (emtia_enerji)",
                   "gsyh_ceyreklik ve usdtry_tcmb_gunluk (GSYH oranı için)"],
        "n": r0["n"], "ilk": r0["ilk"], "son": r0["son"],
        "esneklik_es_zamanli": r0["b"][0], "se": r0["se"][0], "t": r0["t"][0], "r2": r0["r2"],
        "gecikme": r0["gecikme"], "oos": oos, "hukum": hukum(r0["t"][0], b08.oranlar(oos)),
        "gecikme_profili": profil,
        "en_iyi_uyum_gecikme_ay": int(profil["gecikme_ay"][j]), "en_iyi_uyum_esneklik": float(profil["esneklik"][j]),
        "en_iyi_uyum_r2": float(profil["r2"][j]),
        "seviye_esnekligi_saglamlik": {"esneklik": sev["b"][0], "t": sev["t"][0], "r2": sev["r2"], "n": sev["n"],
                                       "not": "iki seri seviyede eğilimli; sahte ilişki riski, ana ölçü değil"},
        "son_deger": {"tarih": _iso(son), "fatura_12ay_mlr_usd": son_fatura,
                "fatura_gsyh_yuzde": float(oran.iloc[-1]), "gsyh_oran_tarihi": _iso(oran.index.max()),
                "on_yuzde_fiyat_artisi_mlr_usd": float(son_fatura * on_yuzde),
                "on_yuzde_fiyat_artisi_gsyh_puan": float(oran.iloc[-1] * on_yuzde),
                "on_yuzde_fiyat_artisi_fatura_yuzde": float(100 * on_yuzde)},
        "fatura_gsyh_araligi": {"en_dusuk_yuzde": float(oran.min()), "en_dusuk_tarih": _iso(oran.idxmin()),
                                "en_yuksek_yuzde": float(oran.max()), "en_yuksek_tarih": _iso(oran.idxmax())},
        "donem_notu": ("Enerji faturasının fiyata esnekliği kur tepkisi değildir; yönetilen kur dönemi bu ölçüde "
                       "ayrılmaz."),
    }


def p10b() -> dict:
    tr = _tr_aylik()[["denerji", "dkur"]].dropna()
    return {"yontem": ("2022 dolar şokunun euro, Kanada doları ve yen üzerindeki izi (vaka) ve Türkiye'de aylık "
                       "enerji fiyatı değişiminin kura, 2 yıllık faize ve enerji faturasına yansıması."),
            "n": int(len(tr)), "ilk": _iso(tr.index.min()), "son": _iso(tr.index.max()),
            "kaynak": ["cnbc_kur_gunluk", "kuresel_aylik", "usdtry_yahoo_gunluk", "dibs_egri_gunluk",
                       "yahoo_dxy_vix_gunluk", "abd_hazine_gunluk", "odemeler_aylik"],
            "sok_2022": _sok_2022(),
            "turkiye": {
                "yontem": ("Aylık: Pink Sheet enerji endeksinin (ay ortalaması) log değişimi ile USD/TRY'nin ay sonu "
                           "log değişimi ve 2 yıllık DİBS getirisinin ay sonu değişimi; Newey–West eğimi, dolar "
                           "endeksi kontrollü ikinci tanım, örneklem dışı kıyas rastgele yürüyüş ve koşulsuz "
                           "ortalama; yönetilen kur dönemi ayrı."),
                "kaynak": ["kuresel_aylik (emtia_enerji)", "usdtry_yahoo_gunluk", "dibs_egri_gunluk (n2y)",
                           "yahoo_dxy_vix_gunluk (DXY)", "fonlama_gunluk (yalnız iş günü takvimi)"],
                "tepki": _tr_tepki(),
                "enerji_faturasi": _fatura()}}


# ───────────────────────────────────────────────────────── sekil_17
def sekil_17() -> dict:
    a = _aylik_kurlar("son")
    e = _emtia()
    df = pd.concat([a, e], axis=1).loc["2000-01-01":SON]

    def endeks(s: pd.Series):
        if s.dropna().empty:
            return None
        taban = s.loc["2000-01-01":"2000-12-01"].mean()
        return [None if pd.isna(v) else float(100 * math.exp((v - taban) / 100)) for v in s]
    kor = {}
    for fx, em, ad in (("aud", "metal", "aud_metal"), ("cad", "enerji", "cad_enerji"), ("nok", "enerji", "nok_enerji")):
        try:
            k = _kayan(_cift(fx, em, "son")).reindex(df.index)
            kor[ad] = [None if pd.isna(v) else float(v) for v in k]
        except bulut.VeriYok:
            kor[ad] = None
    return {"baslik": "Emtia paraları: AUD–metal, CAD–enerji, NOK–enerji", "n": int(len(df)),
            "yontem": "Paranın dolar karşısındaki değeri (ay sonu) ve Pink Sheet emtia endeksi, 2000 ortalaması = 100; "
                      "36 aylık kayan korelasyon aylık log değişimlerden.",
            "kaynak": ["cnbc_kur_gunluk", "kuresel_aylik", "bulut: ECB referans kurları (NOK)"],
            "tarih": [_iso(t) for t in df.index],
            "aud_deger_2000_100": endeks(df["aud"]), "metal_2000_100": endeks(df["metal"]),
            "cad_deger_2000_100": endeks(df["cad"]), "enerji_2000_100": endeks(df["enerji"]),
            "nok_deger_2000_100": endeks(df["nok"]) if "nok" in df.columns else None,
            "kor36_aud_metal": kor["aud_metal"], "kor36_cad_enerji": kor["cad_enerji"],
            "kor36_nok_enerji": kor["nok_enerji"],
            "ilk": _iso(df.index.min()), "son": _iso(df.index.max()),
            "not": ("Paranın değeri dolar karşısında (artış değer kazancı), ay sonu kapanışı; emtia Pink Sheet ay "
                    "ortalaması; kayan korelasyon 36 aylık pencerede aylık log değişimlerden.")}


# ───────────────────────────────────────────────────────── p10c: kur sürücüleri haritası
# Örneklem, dönemler ve eşikler (şartname 02.10.2026; adlı sabitler, metin buradan okur).
SRC_BAS = pd.Timestamp("2010-01-01")          # ilk haftalık değişim 2010'un ilk haftası
SRC_ONCE = pd.Timestamp("2009-11-02")         # ilk değişimin tabanı için önceki haftalar okunur
SRC_DONEMLER = (("2010_2014", "2010-01-01", "2014-12-31", "2010–2014"),
                ("2015_2019", "2015-01-01", "2019-12-31", "2015–2019"),
                ("2020_2022", "2020-01-01", "2022-12-31", "2020–2022"),
                ("2023_2026", "2023-01-01", str(oo.CIPA_GUN.date()), "2023–2026"))
SRC_SIRALAMA = ("2015-01-01", str(oo.CIPA_GUN.date()), "2015–2026")
SRC_ORNEK_GUN = 3               # haftanın son örnek günü: perşembe (0 pazartesi … 3 perşembe)
SRC_KAYAN = 52                  # kayan pencere (hafta)
SRC_KAYAN_ASGARI = 40           # pencerede asgari ortak hafta
SRC_DONEM_ASGARI = 26           # dönem regresyonu için asgari hafta
SRC_SON_HAFTA = 52
SRC_ISTIKRAR_T = 2.0            # tam örneklem |t| eşiği
SRC_ISTIKRAR_DONEM = 3          # "iki dönemden fazlasında aynı işaret"
SRC_GETIRI_SICRAMA_BP = 100.0   # getiri barında geri dönen sıçrama eşiği (tuzak 13)
SRC_KUR_SICRAMA = oo.EM_SICRAMA_ESIK      # kur barında aynı eşik (ortak tanım)
SRC_PLASEBO = 200               # devir haftası dışlamasının plasebosu: aynı sayıda rastgele hafta
SRC_TOHUM = 20261002
SRC_TOHUM_BAYAT = 1000          # bayat yerel hafta plasebosunun tohumu devirinkinden ayrı: 20261002 + 1000 + çift sırası
SRC_KAPSAM_ORAN = 0.75          # sıralama ve haritada kıyas: aynı paranın en geniş kapsamlı sürücüsünün haftalarının en az
                                # %75'i (kısa örneklemli korelasyon tam pencereninkiyle kıyaslanmaz; tuzak 21). Eşik iki
                                # ölçülmüş kümenin arasında: geç başlayan ya da yıllarca boş seri pencerenin %41–64'ünü,
                                # CNBC'nin bütün yerel getirilerde ortak 2014 boşlukları ise %83–91'ini taşıyor.
SRC_SAAT_KONTROL = "aud_cnh"    # iki serisi de New York 17:00 kapanışı olan çift: saat farkı yokken haftalık − günlük farkı

# Paralar: kod → (okur adı, kotasyon, kaynak). Değer DOLARA KARŞI: USD/XXX'te işaret çevrilir.
SRC_PARA = {
    "jpy": ("Japon yeni", "USD/XXX", "g10"), "chf": ("İsviçre frangı", "USD/XXX", "g10"),
    "eur": ("Euro", "XXX/USD", "g10"), "gbp": ("Sterlin", "XXX/USD", "g10"),
    "aud": ("Avustralya doları", "XXX/USD", "g10"), "nzd": ("Yeni Zelanda doları", "XXX/USD", "cnbc"),
    "cad": ("Kanada doları", "USD/XXX", "g10"), "nok": ("Norveç kronu", "USD/XXX", "cnbc"),
    "cop": ("Kolombiya pesosu", "USD/XXX", "cnbc"), "mxn": ("Meksika pesosu", "USD/XXX", "cnbc"),
    "clp": ("Şili pesosu", "USD/XXX", "cnbc"), "brl": ("Brezilya reali", "USD/XXX", "cnbc"),
    "zar": ("Güney Afrika randı", "USD/XXX", "cnbc"), "krw": ("Kore wonu", "USD/XXX", "cnbc"),
    "cnh": ("Çin yuanı (kıyı dışı)", "USD/XXX", "cnbc"), "try": ("Türk lirası", "USD/XXX", "yahoo"),
    "altin": ("Altın ($/ons)", "fiyat", "vadeli"),
}
SRC_HARITA_SATIR = ("jpy", "chf", "eur", "gbp", "aud", "nzd", "cad", "nok", "cop", "mxn", "clp", "brl", "zar",
                    "krw", "try", "altin")
SRC_GRUPLAR = (("faiz", "Faiz farkı (yerel − ABD; altında ABD reel faizi)"), ("emtia", "Emtia fiyatı"),
               ("vix", "Risk: VIX"), ("hisse", "Risk iştahı: S&P 500"), ("cin", "Çin: yuan"),
               ("dolar", "G10 dolar sepeti"))
SRC_EMTIA = ("brent", "wti", "bakir", "demir_cevheri", "altin", "platin", "soya")
# Yerel getiriler CNBC'den (kendi piyasasının kapanışı); ABD bacağı ABD Hazinesi par eğrisinden (tuzak 12).
SRC_GETIRI = ("jp2y", "jp10y", "de2y", "gb2y", "au2y", "nz2y", "nz10y", "ca2y", "ca10y", "ch2y")

# Sürücüler: ad → tanım. "fark" yerel − ABD getiri farkı (bp), "emtia" log fiyat (%), "reel" ABD
# reel faizi (bp), "vix" puan, "hisse" log endeks (%), "para" yuanın değeri (%), "sepet" doların değeri (%).
SRC_SURUCU = {
    "jp_us_2y": {"tur": "fark", "yerel": "jp2y", "abd": "us2", "grup": "faiz", "ad": "Japonya − ABD 2 yıllık getiri farkı",
                 "saat": "Japonya bacağı Tokyo kapanışı, ABD bacağı New York öğleden sonra"},
    "jp_us_10y": {"tur": "fark", "yerel": "jp10y", "abd": "us10", "grup": "faiz", "ad": "Japonya − ABD 10 yıllık getiri farkı",
                  "saat": "Japonya bacağı Tokyo kapanışı, ABD bacağı New York öğleden sonra"},
    "de_us_2y": {"tur": "fark", "yerel": "de2y", "abd": "us2", "grup": "faiz", "ad": "Almanya − ABD 2 yıllık getiri farkı",
                 "saat": "Almanya bacağı Avrupa kapanışı, ABD bacağı New York öğleden sonra"},
    "gb_us_2y": {"tur": "fark", "yerel": "gb2y", "abd": "us2", "grup": "faiz", "ad": "İngiltere − ABD 2 yıllık getiri farkı",
                 "saat": "İngiltere bacağı Londra kapanışı, ABD bacağı New York öğleden sonra"},
    "au_us_2y": {"tur": "fark", "yerel": "au2y", "abd": "us2", "grup": "faiz", "ad": "Avustralya − ABD 2 yıllık getiri farkı",
                 "saat": "Avustralya bacağı Sydney kapanışı, ABD bacağı New York öğleden sonra"},
    "nz_us_2y": {"tur": "fark", "yerel": "nz2y", "abd": "us2", "grup": "faiz", "ad": "Yeni Zelanda − ABD 2 yıllık getiri farkı",
                 "saat": "Yeni Zelanda bacağı Wellington kapanışı, ABD bacağı New York öğleden sonra"},
    "nz_us_10y": {"tur": "fark", "yerel": "nz10y", "abd": "us10", "grup": "faiz",
                  "ad": "Yeni Zelanda − ABD 10 yıllık getiri farkı",
                  "saat": "Yeni Zelanda bacağı Wellington kapanışı, ABD bacağı New York öğleden sonra"},
    "ca_us_2y": {"tur": "fark", "yerel": "ca2y", "abd": "us2", "grup": "faiz", "ad": "Kanada − ABD 2 yıllık getiri farkı",
                 "saat": "iki bacak da Kuzey Amerika kapanışı"},
    "ca_us_10y": {"tur": "fark", "yerel": "ca10y", "abd": "us10", "grup": "faiz", "ad": "Kanada − ABD 10 yıllık getiri farkı",
                  "saat": "iki bacak da Kuzey Amerika kapanışı"},
    "ch_us_2y": {"tur": "fark", "yerel": "ch2y", "abd": "us2", "grup": "faiz", "ad": "İsviçre − ABD 2 yıllık getiri farkı",
                 "saat": "İsviçre bacağı Zürih kapanışı, ABD bacağı New York öğleden sonra"},
    "abd_reel_10y": {"tur": "reel", "grup": "faiz", "ad": "ABD 10 yıllık reel getiri (enflasyona endeksli tahvil)",
                     "saat": "New York öğleden sonra"},
    "brent": {"tur": "emtia", "grup": "emtia", "ad": "Brent petrol (yakın vade)", "saat": "Londra borsa seansı"},
    "wti": {"tur": "emtia", "grup": "emtia", "ad": "WTI petrol (yakın vade)", "saat": "New York borsa seansı"},
    "bakir": {"tur": "emtia", "grup": "emtia", "ad": "Bakır (yakın vade)", "saat": "New York borsa seansı"},
    "demir_cevheri": {"tur": "emtia", "grup": "emtia", "ad": "Demir cevheri (yakın vade)", "saat": "borsa seansı"},
    "altin": {"tur": "emtia", "grup": "emtia", "ad": "Altın (yakın vade)", "saat": "New York borsa seansı"},
    "platin": {"tur": "emtia", "grup": "emtia", "ad": "Platin (yakın vade)", "saat": "New York borsa seansı"},
    "soya": {"tur": "emtia", "grup": "emtia", "ad": "Soya fasulyesi (yakın vade)", "saat": "Chicago borsa seansı"},
    "vix": {"tur": "vix", "grup": "vix", "ad": "VIX (S&P 500 opsiyon oynaklığı)", "saat": "New York 16:15"},
    "spx": {"tur": "hisse", "grup": "hisse", "ad": "S&P 500 endeksi", "saat": "New York 16:00"},
    "cnh": {"tur": "para", "grup": "cin", "ad": "Yuanın dolar karşısındaki değeri (kıyı dışı)", "saat": "New York 17:00"},
    "dolar_sepeti": {"tur": "sepet", "grup": "dolar", "ad": "Doların altı G10 paraya karşı değeri (eşit ağırlık)",
                     "saat": "New York 17:00"},
}
SRC_BIRIM = {"fark": ("bp", "paranın %'si / farkın 1 baz puanı", "yuzde_bp"),
             "reel": ("bp", "altının %'si / reel getirinin 1 baz puanı", "yuzde_bp"),
             "emtia": ("%", "paranın %'si / emtia fiyatının %'si", "yuzde_yuzde"),
             "vix": ("puan", "paranın %'si / VIX'in 1 puanı", "yuzde_puan"),
             "hisse": ("%", "paranın %'si / endeksin %'si", "yuzde_yuzde"),
             "para": ("%", "paranın %'si / yuanın %'si", "yuzde_yuzde"),
             "sepet": ("%", "paranın %'si / dolar sepetinin %'si", "yuzde_yuzde")}

_G_FAIZ = ("Yerel getiri ABD'ninkine göre yükselince (yerel − ABD farkı artınca) o parada tutulan kısa vadeli varlığın "
           "getirisi ve beklenen politika faizi farkı para lehine döner: faiz paritesi ve taşıma kanalı.")
_G_RISKLI = ("Yüksek faizli ya da küresel büyüme döngüsüne bağlı para: riskten kaçışta taşıma pozisyonları kapanır ve "
             "para satılır.")
_G_HISSE = ("Hisse fiyatlarının yükselişi risk iştahının göstergesidir; döngüsel ve taşıma paraları birlikte değer kazanır.")
# (anahtar, para, sürücü, beklenen işaret, gerekçe)
SRC_CIFTLER = (
    ("jpy_jp_us_2y", "jpy", "jp_us_2y", 1, "Japonya − ABD farkı düşünce (ABD getirisi Japonya'nınkinden hızlı yükselince) "
     "doları tutmanın getirisi artar ve yen değer kaybeder: dolar–yen taşıma işleminin ve faiz paritesinin kanalı."),
    ("jpy_jp_us_10y", "jpy", "jp_us_10y", 1, "Uzun vade farkı aynı kanaldan işler; Japonya'nın getiri eğrisi kontrolü "
     "döneminde (Eylül 2016 – Mart 2024) Japonya 10 yıllığı dar bantta tutuldu: farkın oynaklığının ne kadarının ABD "
     "bacağından geldiği satırda dönem dönem ölçülüdür."),
    ("eur_de_us_2y", "eur", "de_us_2y", 1, _G_FAIZ),
    ("gbp_gb_us_2y", "gbp", "gb_us_2y", 1, _G_FAIZ),
    ("aud_au_us_2y", "aud", "au_us_2y", 1, _G_FAIZ),
    ("nzd_nz_us_2y", "nzd", "nz_us_2y", 1, _G_FAIZ),
    ("nzd_nz_us_10y", "nzd", "nz_us_10y", 1, _G_FAIZ),
    ("cad_ca_us_2y", "cad", "ca_us_2y", 1, _G_FAIZ),
    ("cad_ca_us_10y", "cad", "ca_us_10y", 1, _G_FAIZ),
    ("chf_ch_us_2y", "chf", "ch_us_2y", 1, _G_FAIZ),
    ("nok_brent", "nok", "brent", 1, "Norveç ihracatının büyük kısmı ham petrol ve doğal gazdır: petrol pahalılaşınca "
     "ticaret hadleri ve ihracat geliri artar, kron değer kazanır."),
    ("cad_wti", "cad", "wti", 1, "Kanada ham petrol ihracatçısıdır (büyük kısmı ABD'ye, Kuzey Amerika fiyatıyla): petrol "
     "fiyatı ticaret hadlerini taşır."),
    ("cop_brent", "cop", "brent", 1, "Kolombiya'nın en büyük ihracat kalemi petroldür."),
    ("mxn_wti", "mxn", "wti", 1, "Meksika petrol üreticisidir; ama yakıt ithalatı yüzünden enerji dengesi zayıftır, "
     "beklenen artı işaret zayıf olabilir."),
    ("aud_bakir", "aud", "bakir", 1, "Avustralya metal ihracatçısıdır; bakır küresel sanayi talebinin göstergesidir."),
    ("aud_demir_cevheri", "aud", "demir_cevheri", 1, "Demir cevheri Avustralya'nın en büyük ihracat kalemidir (alıcısı "
     "ağırlıkla Çin)."),
    ("clp_bakir", "clp", "bakir", 1, "Şili dünyanın en büyük bakır üreticisidir; bakır ihracatının en büyük kalemidir."),
    ("zar_altin", "zar", "altin", 1, "Güney Afrika altın üreticisidir; altın fiyatı ihracat gelirini taşır."),
    ("zar_platin", "zar", "platin", 1, "Güney Afrika dünyanın en büyük platin üreticisidir."),
    ("brl_soya", "brl", "soya", 1, "Brezilya dünyanın en büyük soya ihracatçısıdır."),
    ("brl_demir_cevheri", "brl", "demir_cevheri", 1, "Brezilya dünyanın en büyük demir cevheri ihracatçılarındandır."),
    ("altin_abd_reel_10y", "altin", "abd_reel_10y", -1, "Altın faiz getirmez: ABD reel faizi yükselince altını tutmanın "
     "fırsat maliyeti artar ve fiyat düşer (beklenen eksi)."),
    ("jpy_vix", "jpy", "vix", 1, "Riskten kaçışta (VIX yükselince) yenle fonlanmış taşıma pozisyonları kapanır ve Japon "
     "yatırımcının dış varlıktan dönüşü yen talebi yaratır: yen değer kazanır."),
    ("chf_vix", "chf", "vix", 1, "İsviçre frangı güvenli liman parasıdır: riskten kaçışta talep görür."),
    ("aud_vix", "aud", "vix", -1, _G_RISKLI),
    ("nzd_vix", "nzd", "vix", -1, _G_RISKLI),
    ("mxn_vix", "mxn", "vix", -1, _G_RISKLI),
    ("zar_vix", "zar", "vix", -1, _G_RISKLI),
    ("brl_vix", "brl", "vix", -1, _G_RISKLI),
    ("krw_vix", "krw", "vix", -1, "Kore ekonomisi küresel ticaret döngüsüne ve yarı iletken ihracatına bağlıdır: "
     "riskten kaçışta won satılır."),
    ("aud_spx", "aud", "spx", 1, _G_HISSE),
    ("nzd_spx", "nzd", "spx", 1, _G_HISSE),
    ("mxn_spx", "mxn", "spx", 1, _G_HISSE),
    ("zar_spx", "zar", "spx", 1, _G_HISSE),
    ("brl_spx", "brl", "spx", 1, _G_HISSE),
    ("krw_spx", "krw", "spx", 1, _G_HISSE),
    ("aud_cnh", "aud", "cnh", 1, "Çin Avustralya'nın en büyük ihracat pazarıdır; yuanın değeri Çin talebinin ve politika "
     "duruşunun vekilidir."),
    ("try_brent", "try", "brent", -1, "Türkiye net enerji ithalatçısıdır: petrol pahalılaşınca dış açık ve döviz talebi "
     "büyür, TL değer kaybeder (beklenen eksi)."),
    ("try_vix", "try", "vix", -1, "Riskten kaçışta gelişen ülke paralarından çıkış olur (beklenen eksi)."),
    ("try_dolar_sepeti", "try", "dolar_sepeti", -1, "Doların G10 paralarına karşı genel değer kazancı TL'ye de yansır "
     "(beklenen eksi: sepet yükselince TL değer kaybeder)."),
)
SRC_KAYAN_CIFTLER = ("jpy_jp_us_2y", "eur_de_us_2y", "nok_brent", "cad_wti", "aud_bakir", "clp_bakir", "zar_altin",
                     "altin_abd_reel_10y")

# Vade devri takvimi (tuzak 14): kural, sözleşme ayları (None = her ay), işaretlenen pencere (devir gününe göre
# işlem günü). "brent": ICE son işlem günü (Şubat 2016 sözleşmesine kadar teslim ayının ilk gününden 15 gün önceki
# iş gününden bir önceki iş günü, sonra teslim ayından iki önceki ayın son iş günü); "wti": NYMEX son işlem günü
# (teslimden önceki ayın 25'inden üç iş günü önce); "ay_sonu": sözleşme ayından önceki ayın son iş günü (ilk
# bildirim günü; metallerde ve soyada yakın vade o gün devreder). Devir günü son işlem gününden sonraki ilk gündür.
SRC_DEVIR = {
    "brent": ("brent", None, (-1, 1)),
    "wti": ("wti", None, (-1, 1)),
    "altin": ("ay_sonu", (2, 4, 6, 8, 10, 12), (-1, 3)),
    "bakir": ("ay_sonu", (3, 5, 7, 9, 12), (-1, 3)),
    "platin": ("ay_sonu", (1, 4, 7, 10), (-1, 3)),
    "soya": ("ay_sonu", (1, 3, 5, 7, 8, 9, 11), (-1, 3)),
    "demir_cevheri": ("ay_sonu", None, (-1, 1)),
}
SRC_DEVIR_AD = {
    "brent": ("ICE Brent son işlem günü: Şubat 2016 sözleşmesine kadar teslim ayının ilk gününden 15 gün önceki "
              "iş gününden bir önceki iş günü, sonra teslim ayından iki önceki ayın son iş günü"),
    "wti": "NYMEX WTI son işlem günü: teslimden önceki ayın 25'inden üç iş günü önce (25'i iş günü değilse dört)",
    "ay_sonu": "ilk bildirim günü: sözleşme ayından önceki ayın son iş günü; yakın vade o gün devreder",
    "ay_sonu_aylik": "aylık ortalamayla kapanan sözleşme: yakın vade her ayın son iş gününde biter",
}
SRC_KAYNAK = ["bulut: surucu_gunluk (CNBC günlük barları: emtia vadelileri, yerel getiriler, G10 dışı paralar, "
              "S&P 500; döviz New York 17:00)",
              "cnbc_kur_gunluk (G10 kurları, New York 17:00, bozuk kotasyon günleri çıkarılmış)",
              "abd_hazine_gunluk (ABD Hazinesi 2 ve 10 yıllık par getirisi)",
              "bulut: abd_reel_getiri (ABD Hazinesi 10 yıllık reel par getirisi)",
              "yahoo_dxy_vix_gunluk (VIX)", "usdtry_yahoo_gunluk (USD/TRY)"]


def _src_kolon_para(kod: str) -> str:
    return "e_altin" if kod == "altin" else f"p_{kod}"


def _src_kolon_surucu(ad: str) -> tuple[str, float]:
    """(günlük çerçevedeki sütun, değişimin ölçeği): getiride ×100 (bp), log değerlerde 1 (zaten %)."""
    t = SRC_SURUCU[ad]["tur"]
    if t == "fark":
        return f"f_{ad}", 100.0
    if t == "reel":
        return "y_reel10", 100.0
    if t == "emtia":
        return f"e_{ad}", 1.0
    return {"vix": "vix", "hisse": "spx", "para": "p_cnh", "sepet": "sepet"}[t], 1.0


_SRC_GETIRI_AD = {"jp2y": "Japonya 2 yıllık", "jp10y": "Japonya 10 yıllık", "de2y": "Almanya 2 yıllık",
                  "gb2y": "İngiltere 2 yıllık", "au2y": "Avustralya 2 yıllık", "nz2y": "Yeni Zelanda 2 yıllık",
                  "nz10y": "Yeni Zelanda 10 yıllık", "ca2y": "Kanada 2 yıllık", "ca10y": "Kanada 10 yıllık",
                  "ch2y": "İsviçre 2 yıllık", "us2": "ABD 2 yıllık (ABD Hazinesi)", "us10": "ABD 10 yıllık (ABD Hazinesi)",
                  "us2_cnbc": "ABD 2 yıllık (CNBC)", "us10_cnbc": "ABD 10 yıllık (CNBC)",
                  "reel10": "ABD 10 yıllık reel (ABD Hazinesi)"}


def _src_kolon_ad(c: str) -> str:
    """Günlük çerçeve sütununun okur adı."""
    if "_" not in c:
        return {"vix": "VIX", "spx": "S&P 500", "sepet": "G10 dolar sepeti"}.get(c, c)
    on, ad = c.split("_", 1)
    if c == "p_try_cnbc":
        return "Türk lirası (CNBC, kıyas)"
    if on == "p":
        return SRC_PARA[ad][0]
    if on == "e":
        return SRC_SURUCU[ad]["ad"]
    if on == "y":
        return _SRC_GETIRI_AD.get(ad, ad)
    if on == "f":
        return SRC_SURUCU[ad]["ad"]
    return c


@lru_cache(maxsize=1)
def _src_gunluk() -> tuple[pd.DataFrame, dict]:
    """Bütün para ve sürücü serileri, hafta içi takviminde, DOLDURMA YOK (eksik gün boş kalır, değişim köprü
    kurmaz). Paralar ve emtia log×100, getiriler %, VIX puan, dolar sepeti log×100 (dolar yönünde).
    İkinci değer temizlik raporudur."""
    takvim = pd.bdate_range(SRC_ONCE, oo.CIPA_GUN)
    s = bulut.surucu_gunluk()
    s = s[s.index.dayofweek < 5]
    g10 = oo.cnbc_kur()
    D = pd.DataFrame(index=takvim)
    rapor = {"kur_temizlik": {}, "getiri_temizlik": {}, "kurulmayan": {}}
    for kod, (_, kote, kaynak) in SRC_PARA.items():
        if kaynak == "g10":
            x = g10[kod].dropna()
        elif kaynak == "yahoo":
            x = oo.usdtry()[0].dropna()
        elif kod in s.columns:
            x = s[kod].dropna().loc[SRC_ONCE - pd.Timedelta(days=10):]
            if kaynak == "cnbc":
                m = oo.geri_donen_sicrama(np.log(x).diff(), SRC_KUR_SICRAMA)
                rapor["kur_temizlik"][kod] = [_iso(t) for t in x.index[m]]
                x = x[~m]
        else:
            rapor["kurulmayan"][kod] = "kaynak sembolü yanıt vermedi"
            continue
        v = np.log(x) * 100
        D[_src_kolon_para(kod)] = (-v if kote == "USD/XXX" else v).reindex(takvim)
    D["p_try_cnbc"] = (-np.log(s["try"].dropna()) * 100).reindex(takvim)
    # günlük ölçü için: geçiş öncesi cuma değeri pazartesi barının başıdır (hafta sonunu taşır; ortak_olc.usdtry)
    D["p_try_cumasiz"] = (-np.log(oo.usdtry(cuma_dus=True)[0].dropna()) * 100).reindex(takvim)
    for ad in SRC_EMTIA:
        if ad != "altin":
            D[f"e_{ad}"] = (np.log(s[ad].dropna()) * 100).reindex(takvim)
    for ad in SRC_GETIRI:
        if ad not in s.columns:
            rapor["kurulmayan"][ad] = "kaynak sembolü yanıt vermedi"
            continue
        y = s[ad].dropna().loc[SRC_ONCE - pd.Timedelta(days=10):]
        m = oo.geri_donen_sicrama(y.diff() * 100, SRC_GETIRI_SICRAMA_BP)
        rapor["getiri_temizlik"][ad] = [_iso(t) for t in y.index[m]]
        D[f"y_{ad}"] = y[~m].reindex(takvim)
    a = oo.oku("abd_hazine_gunluk")
    D["y_us2"] = a["us2"].reindex(takvim)
    D["y_us10"] = a["us10"].reindex(takvim)
    D["y_us2_cnbc"] = s["us2y"].reindex(takvim)
    D["y_us10_cnbc"] = s["us10y"].reindex(takvim)
    D["y_reel10"] = bulut.abd_reel_getiri()["reel10y"].reindex(takvim)
    D["vix"] = oo.oku("yahoo_dxy_vix_gunluk")["vix"].reindex(takvim)
    D["spx"] = (np.log(s["spx"].dropna()) * 100).reindex(takvim)
    D["sepet"] = (oo.dolar_sepeti()["sepet"] * 100).reindex(takvim)
    for ad, tn in SRC_SURUCU.items():
        if tn["tur"] == "fark" and f"y_{tn['yerel']}" in D.columns:
            D[f"f_{ad}"] = D[f"y_{tn['yerel']}"] - D[f"y_{tn['abd']}"]
    return D, rapor


def _src_takvim_ici(T: pd.DatetimeIndex, ay: pd.Period) -> pd.DatetimeIndex:
    return T[(T.year == ay.year) & (T.month == ay.month)]


@lru_cache(maxsize=16)
def _src_devir_gunleri(ad: str) -> pd.DatetimeIndex:
    """Yakın vade vadelisinin tahmini devir günleri (yeni sözleşmenin ilk günü), vadelinin KENDİ işlem günleri
    takviminde (tatiller kaynakta bar olmadığı için takvimin dışındadır)."""
    return pd.DatetimeIndex(sorted(set(_src_devir_tahmini(ad, "kendi").values())))


@lru_cache(maxsize=32)
def _src_devir_tahmini(ad: str, takvim: str) -> dict:
    """Sözleşme ayı → tahmini devir günü. takvim 'kendi': iş günleri vadelinin kendi barlarıdır (tatiller doğru
    düşer, ama kaynaktaki veri boşluğu da tatil sayılır); 'hafta_ici': her hafta içi günü iş günüdür (veri boşluğu
    kaymaz, tatil iş günü sayılır), sonuç vadelinin bir sonraki barına taşınır. İkisinin farkı takvim
    duyarlılığıdır (veri denetimi)."""
    kural, aylar, _ = SRC_DEVIR[ad]
    Tk = pd.DatetimeIndex(bulut.surucu_gunluk()[ad].dropna().index)
    Tk = Tk[Tk.dayofweek < 5]
    T = Tk if takvim == "kendi" else pd.bdate_range(Tk.min(), Tk.max())
    out = {}
    for p in pd.period_range(SRC_ONCE.to_period("M") - 2, oo.CIPA_GUN.to_period("M") + 3, freq="M"):
        if aylar and p.month not in aylar:
            continue
        if kural == "wti":
            onceki = p - 1
            g25 = pd.Timestamp(onceki.year, onceki.month, 25)
            if g25 in T:
                taban = g25
            else:
                k = T.searchsorted(g25) - 1
                if k < 0:
                    continue
                taban = T[k]
            i = T.get_loc(taban) - 3
        elif kural == "brent":
            if p <= pd.Period("2016-02", "M"):
                g15 = p.to_timestamp() - pd.Timedelta(days=15)
                if g15 in T:
                    x = g15
                else:
                    k = T.searchsorted(g15) - 1
                    if k < 0:
                        continue
                    x = T[k]
                i = T.get_loc(x) - 1
            else:
                m = _src_takvim_ici(T, p - 2)
                if not len(m):
                    continue
                i = T.get_loc(m[-1])
        else:                                       # ay_sonu
            m = _src_takvim_ici(T, p - 1)
            if not len(m):
                continue
            i = T.get_loc(m[-1])
        if 0 <= i < len(T) - 1:
            g = T[i + 1]
            if takvim != "kendi":
                j = Tk.searchsorted(g)
                if j >= len(Tk):
                    continue
                g = Tk[j]
            out[p] = g
    return out


@lru_cache(maxsize=16)
def _src_devir_penceresi(ad: str) -> np.ndarray:
    """Devir gününün çevresindeki işaretli işlem günleri (pencere SRC_DEVIR), sıralı ns dizisi."""
    _, _, (a, b) = SRC_DEVIR[ad]
    T = pd.DatetimeIndex(bulut.surucu_gunluk()[ad].dropna().index)
    T = T[T.dayofweek < 5]
    poz = T.searchsorted(_src_devir_gunleri(ad))
    gunler = set()
    for p in poz:
        for k in range(a, b + 1):
            if 0 <= p + k < len(T):
                gunler.add(T[p + k])
    return np.array(sorted(gunler), dtype="datetime64[ns]")


def _src_devir_isaret(d: pd.DataFrame, ad: str) -> pd.Series:
    """Haftalık değişim penceresi (önceki örnek günü, örnek günü] devir penceresinden bir gün içeriyor mu."""
    w = _src_devir_penceresi(ad)
    g = d["gun"].values.astype("datetime64[ns]")
    o = d["onceki"].values.astype("datetime64[ns]")
    ok = ~(np.isnat(g) | np.isnat(o))
    say = np.zeros(len(d), dtype=bool)
    say[ok] = (np.searchsorted(w, g[ok], side="right") - np.searchsorted(w, o[ok], side="right")) > 0
    return pd.Series(say, index=d.index)


@lru_cache(maxsize=128)
def _src_haftalik(kolonlar: tuple) -> pd.DataFrame:
    """Haftalık seviye: haftanın PERŞEMBE'ye kadarki SON ORTAK günü (bütün sütunların birlikte bulunduğu gün;
    perşembe bir seride tatilse o hafta hepsi aynı önceki güne çekilir). Hafta tarihi o haftanın perşembesidir;
    `gun` örneklenen gerçek gün. Çıpa haftası (perşembesi çıpanın ilerisinde) kısmidir ve düşer."""
    D, _ = _src_gunluk()
    f = D[list(kolonlar)].dropna()
    f = f[f.index.dayofweek <= SRC_ORNEK_GUN]
    w = f.resample("W-FRI").last()
    w["gun"] = f.index.to_series().resample("W-FRI").last()
    w.index = w.index - pd.Timedelta(days=1)          # hafta tarihi perşembe
    return w[w.index <= oo.CIPA_GUN]


def _src_tek_gun(kolon: str) -> pd.Series:
    """Tek bir serinin kendi başına örneklenen günü (haftanın perşembeye kadarki son günü)."""
    D, _ = _src_gunluk()
    x = D[kolon].dropna()
    x = x[x.index <= oo.CIPA_GUN]
    x = x[x.index.dayofweek <= SRC_ORNEK_GUN]
    g = x.index.to_series().resample("W-FRI").last()
    g.index = g.index - pd.Timedelta(days=1)
    return g[g.index <= oo.CIPA_GUN]


def _persembe(t) -> str | None:
    """Hafta tarihi (perşembe) ISO yazımı."""
    return None if t is None or pd.isna(t) else _iso(t)


def _src_yonetilen(d: pd.DataFrame) -> pd.Series:
    """Haftalık değişim penceresi (önceki, gün] yönetilen kur dönemiyle kesişiyor mu."""
    return (d["gun"] >= oo.YONETILEN[0]) & (d["onceki"] < oo.YONETILEN[1])


def _src_ozet(y: pd.Series, x: pd.Series, gun: pd.Series | None = None, asgari: int = SRC_DONEM_ASGARI) -> dict:
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1, sort=True).dropna()
    if len(d) < asgari:
        return kurulmadi(f"ortak hafta {len(d)}; en az {asgari} gerekir", n=int(len(d)))
    r = _reg(d["y"], d["x"])
    g = gun.reindex(d.index) if gun is not None else pd.Series(d.index, index=d.index)
    return {"n": int(len(d)), "ilk": _iso(g.min()), "son": _iso(g.max()),
            "kor": float(d["y"].corr(d["x"])), "spearman": float(d["y"].corr(d["x"], method="spearman")),
            "beta": r["b"][0], "se": r["se"][0], "t": r["t"][0], "r2": r["r2"], "gecikme": r["gecikme"]}


def _src_kayan(d: pd.DataFrame) -> pd.Series:
    return d["dp"].rolling(SRC_KAYAN, min_periods=SRC_KAYAN_ASGARI).corr(d["dx"])


@lru_cache(maxsize=64)
def _src_cift_veri(anahtar: str) -> tuple[pd.DataFrame, dict]:
    """Bir çiftin haftalık değişim çerçevesi (dp para %, dx sürücü kendi biriminde, gun, onceki; faiz farkında
    bacaklar) ve tanımı. Yönetilen kur döneminde TRY değişimleri boştur."""
    c = {a: (p, s, b, g) for a, p, s, b, g in SRC_CIFTLER}[anahtar]
    para, sur, bek, ger = c
    tn = SRC_SURUCU[sur]
    pk = _src_kolon_para(para)
    sk, olcek = _src_kolon_surucu(sur)
    D, _ = _src_gunluk()
    if pk not in D.columns or sk not in D.columns:
        eksik = tn["ad"] if sk not in D.columns else SRC_PARA[para][0]
        return pd.DataFrame(), {"durum": "kurulmadi", "sebep": f"{eksik} kurulmadı: kaynak sembolü yanıt vermedi"}
    # Ortak gün yalnız ÖLÇÜNÜN kendi sütunlarından kurulur (para, sürücü; faiz farkında iki bacağı farkın kendisi
    # taşır). Kaynak kıyası için okunan CNBC ABD bacağı ana örneklemi belirleyemez (tuzak 19): ayrı çerçevede ölçülür.
    kol = [pk, sk] + ([f"y_{tn['yerel']}", f"y_{tn['abd']}"] if tn["tur"] == "fark" else [])
    w = _src_haftalik(tuple(kol))
    d = pd.DataFrame({"dp": w[pk].diff(), "dx": w[sk].diff() * olcek, "gun": w["gun"], "onceki": w["gun"].shift(1)})
    if tn["tur"] == "fark":
        d["d_yerel"] = w[f"y_{tn['yerel']}"].diff() * 100
        d["d_abd"] = w[f"y_{tn['abd']}"].diff() * 100
    d = d[d.index >= SRC_BAS]                     # ilk değişimin bittiği perşembe 2010'da
    kiyas = (f"y_{tn['abd']}_cnbc",) if tn["tur"] == "fark" else ()
    bilgi = {"para": para, "surucu": sur, "beklenen": bek, "gerekce": ger, "pk": pk, "sk": sk, "olcek": olcek,
             "kolonlar": tuple(kol), "kiyas_kolonlar": kiyas}
    if para == "try":
        yon = _src_yonetilen(d).fillna(False)
        bilgi["yonetilen"] = d[yon].copy()
        d.loc[yon, [c for c in d.columns if c.startswith("d")]] = np.nan
    return d, bilgi


def _src_gunluk_gecikme(bilgi: dict) -> dict:
    """Günlük değişimde eşzamanlılık: paranın t günü ile sürücünün t günü (gecikme 0), t−1 günü (sürücü bir gün
    önde) ve t+1 günü (sürücünün tarihli değişimi paranın gününden sonra biter). Değişim köprü kurmaz (önceki
    hafta içi günü boşsa o günün değişimi boştur)."""
    D, _ = _src_gunluk()
    # TRY: geçiş öncesi cuma değeri hafta sonunu taşır (pazartesi barının başı); günlük ölçüde o cumalar boştur, yani
    # cuma ve pazartesi değişimi düşer (tuzak 20). Haftalık ölçü perşembeyi örneklediği için etkilenmez.
    dp = D["p_try_cumasiz" if bilgi["para"] == "try" else bilgi["pk"]].diff()
    dx = D[bilgi["sk"]].diff() * bilgi["olcek"]
    if bilgi["para"] == "try":
        y = oo.yonetilen_mi(D.index)
        dp = dp.where(~y)
    out = {}
    for ad, k in (("para_t_surucu_t", 0), ("para_t_surucu_t_eksi_1", 1), ("para_t_surucu_t_arti_1", -1)):
        z = pd.concat([dp.rename("p"), dx.shift(k).rename("x")], axis=1).loc[SRC_BAS:].dropna()
        out[ad] = {"kor": float(z["p"].corr(z["x"])), "n": int(len(z))}
    tn = SRC_SURUCU[bilgi["surucu"]]
    if tn["tur"] == "fark":
        dy = D[f"y_{tn['yerel']}"].diff() * 100
        da = D[f"y_{tn['abd']}"].diff() * 100
        bac = {}
        for ad, x, k in (("yerel_t", dy, 0), ("yerel_t_eksi_1", dy, 1), ("yerel_t_arti_1", dy, -1),
                         ("abd_t", da, 0), ("abd_t_eksi_1", da, 1)):
            z = pd.concat([dp.rename("p"), x.shift(k).rename("x")], axis=1).loc[SRC_BAS:].dropna()
            bac[ad] = {"kor": float(z["p"].corr(z["x"])), "n": int(len(z))}
        out["bacaklar"] = bac
        out["bacak_notu"] = ("Paranın t günü New York 17:00'de biter. Yerel bacak kendi piyasasının kapanışıdır; "
                             "Asya-Pasifik kapanışlı getirinin (Japonya, Avustralya, Yeni Zelanda) t+1 günkü değişimi "
                             "paranın t günündeki New York seansını içerir. ABD bacağı New York öğleden sonradır. "
                             "Paranın beklenen işareti yerel bacakla artı, ABD bacağıyla eksidir.")
    if bilgi["para"] == "try":
        out["cuma_notu"] = (f"{oo.GECIS_YAHOO_CUMA.strftime('%d.%m.%Y')} öncesinde USD/TRY'nin cuma değeri pazartesi "
                            "barının başındaki fiyattır ve hafta sonunu taşır; günlük ölçüde o cumalar boş bırakılır, "
                            "cuma ve pazartesi değişimi düşer. Haftalık ölçü perşembeyi örneklediği için etkilenmez.")
    return out


def _src_devir_olc(d: pd.DataFrame, bilgi: dict, k: int) -> dict | None:
    """Çiftteki vadeli(ler) için devir haftaları dışarıda bırakılınca korelasyon; aynı sayıda rastgele hafta
    dışarıda bırakılan plaseboyla."""
    vadeliler = [a for a in (bilgi["surucu"], bilgi["para"]) if a in SRC_DEVIR]
    if not vadeliler:
        return None
    dd = d.dropna(subset=["dp", "dx"])
    isaret = pd.Series(False, index=dd.index)
    for a in vadeliler:
        isaret |= _src_devir_isaret(dd, a)
    r = _src_dislama(dd, isaret, SRC_TOHUM + k)
    return {"vadeli": vadeliler, "n_devir_haftasi": r["m"], "devir_haftasi_payi_yuzde": r["pay_yuzde"],
            "kor_tam": r["kor_tam"], "kor_devir_haric": r["kor_haric"], "fark": r["fark"],
            "plasebo_fark_p05": r["p05"], "plasebo_fark_p95": r["p95"], "plasebo_disinda": r["disinda"],
            "n_plasebo": SRC_PLASEBO}


def _src_dislama(dd: pd.DataFrame, maske: pd.Series, tohum: int) -> dict:
    """İşaretli haftalar dışarıda bırakılınca korelasyonun değişimi ve aynı sayıda RASTGELE hafta dışarıda
    bırakılan plasebonun %90 bandı (devir haftası ve bayat yerel getiri haftası aynı kuralla)."""
    kalan = dd[~maske]
    tam = float(dd["dp"].corr(dd["dx"]))
    haric = float(kalan["dp"].corr(kalan["dx"]))
    m = int(maske.sum())
    rng = np.random.default_rng(tohum)
    yv, xv = dd["dp"].to_numpy(float), dd["dx"].to_numpy(float)
    fark_p = np.empty(SRC_PLASEBO)
    for i in range(SRC_PLASEBO):
        sec = np.ones(len(dd), dtype=bool)
        sec[rng.choice(len(dd), size=m, replace=False)] = False
        fark_p[i] = np.corrcoef(yv[sec], xv[sec])[0, 1] - tam
    lo, hi = float(np.quantile(fark_p, 0.05)), float(np.quantile(fark_p, 0.95))
    return {"m": m, "pay_yuzde": 100.0 * m / len(dd), "kor_tam": tam, "kor_haric": haric, "fark": haric - tam,
            "p05": lo, "p95": hi, "disinda": bool((haric - tam) < lo or (haric - tam) > hi)}


def _src_bacak_olc(dd: pd.DataFrame, bilgi: dict, k: int) -> dict:
    """Faiz farkı satırında iki bacak: bacak başına korelasyon, farkın haftalık varyansının ABD bacağından gelen
    payı (dx = d_yerel − d_abd olduğundan var(dx) = cov(dx, d_yerel) − cov(dx, d_abd); ABD payı −cov(dx, d_abd)/var(dx)),
    yerel bacağın haftalık değişimi TAM SIFIR olan haftaların (bayat kotasyon ya da gerçek durgunluk; veriyle
    ayrılamaz) dışlanması plaseboyla, ve ABD bacağı CNBC kapanışıyla kurulunca korelasyon (kaynak sağlamlığı; ana
    örneklemi değiştirmeden, iki tanımın birlikte bulunduğu ORTAK günlerde yan yana)."""
    def pay(z):
        v = float(z["dx"].var())
        return 100.0 * float(-z["dx"].cov(z["d_abd"])) / v if v > 0 else None
    out = {"yerel_kor": float(dd["dp"].corr(dd["d_yerel"])), "abd_kor": float(dd["dp"].corr(dd["d_abd"])),
           "fark_varyansinda_abd_payi_yuzde": pay(dd),
           "fark_varyansinda_abd_payi_donem_yuzde": {ad: (pay(z) if len(z := dd.loc[b:s]) >= SRC_DONEM_ASGARI else None)
                                                     for ad, b, s, _ in SRC_DONEMLER}}
    sifir = dd["d_yerel"] == 0
    r = _src_dislama(dd, sifir, SRC_TOHUM + SRC_TOHUM_BAYAT + k)
    donem = {}
    for ad, b, s, _ in SRC_DONEMLER:
        z, zs = dd.loc[b:s], sifir.loc[b:s]
        donem[ad] = ({"n": int(len(z)), "n_sifir_hafta": int(zs.sum()), "kor": float(z["dp"].corr(z["dx"])),
                      "kor_haric": float(z.loc[~zs, "dp"].corr(z.loc[~zs, "dx"]))}
                     if len(z) - int(zs.sum()) >= SRC_DONEM_ASGARI else None)
    out["bayat_yerel_hafta"] = {"n_sifir_hafta": r["m"], "pay_yuzde": r["pay_yuzde"], "kor_tam": r["kor_tam"],
                                "kor_haric": r["kor_haric"], "fark": r["fark"], "plasebo_fark_p05": r["p05"],
                                "plasebo_fark_p95": r["p95"], "plasebo_disinda": r["disinda"],
                                "n_plasebo": SRC_PLASEBO, "donemler": donem,
                                "not": ("Yerel getirinin haftalık değişimi tam sıfır olan haftalar dışarıda bırakılınca "
                                        "korelasyon; aynı sayıda rastgele hafta dışarıda bırakılan plaseboyla. Sıfıra "
                                        "yakın faizde bayat kotasyon ile gerçek durgunluk veriyle ayrılamaz.")}
    tn = SRC_SURUCU[bilgi["surucu"]]
    yk, ak = f"y_{tn['yerel']}", f"y_{tn['abd']}"
    wk = _src_haftalik(bilgi["kolonlar"] + bilgi["kiyas_kolonlar"])
    q = pd.DataFrame({"dp": wk[bilgi["pk"]].diff(), "dx": wk[bilgi["sk"]].diff() * 100,
                      "dx_cnbc": (wk[yk] - wk[f"{ak}_cnbc"]).diff() * 100}).loc[SRC_BAS:].dropna()
    out["abd_bacagi_cnbc_kor"] = float(q["dp"].corr(q["dx_cnbc"]))
    out["abd_bacagi_hazine_kor_ayni_gunler"] = float(q["dp"].corr(q["dx"]))
    out["n_kiyas"] = int(len(q))
    out["not"] = ("Yerel bacakla artı, ABD bacağıyla eksi beklenir. Farkın varyansındaki ABD payı %100'ü aşabilir: "
                  "yerel getiri ABD'ninkiyle aynı yönde oynadığında yerel bacağın katkısı eksidir. Kaynak kıyası "
                  "(ABD bacağı CNBC kapanışıyla) iki tanımın birlikte bulunduğu günlerde, Hazine tanımıyla yan yana; "
                  "ana ölçünün örneklemi bu kıyastan bağımsızdır.")
    return out


def _src_hukum(tam: dict, donemler: dict) -> tuple[str, int, int]:
    if tam.get("durum") == "kurulmadi":
        return "kurulmadı", 0, 0
    isaret = np.sign(tam["beta"])
    say = [v for v in donemler.values() if v.get("durum") != "kurulmadi"]
    ayni = sum(1 for v in say if np.sign(v["beta"]) == isaret)
    if abs(tam["t"]) < SRC_ISTIKRAR_T:
        return "zayıf", ayni, len(say)
    return ("istikrarlı" if ayni >= SRC_ISTIKRAR_DONEM else "dönemsel"), ayni, len(say)


@lru_cache(maxsize=64)
def _src_satir(anahtar: str) -> dict:
    d, bilgi = _src_cift_veri(anahtar)
    if bilgi.get("durum") == "kurulmadi":
        c = {a: (p, s, b, g) for a, p, s, b, g in SRC_CIFTLER}[anahtar]
        return {"para": c[0], "surucu": c[1], "beklenen_isaret": c[2], "gerekce": c[3],
                "grup": SRC_SURUCU[c[1]]["grup"], **bilgi}
    k = [a for a, *_ in SRC_CIFTLER].index(anahtar)
    tn = SRC_SURUCU[bilgi["surucu"]]
    birim, birim_okur, birim_kod = SRC_BIRIM[tn["tur"]]
    dd = d.dropna(subset=["dp", "dx"])
    tam = _src_ozet(dd["dp"], dd["dx"], dd["gun"])
    donem = {}
    for ad, b, s, etiket in SRC_DONEMLER:
        z = dd.loc[b:s]
        donem[ad] = {"etiket": etiket, **_src_ozet(z["dp"], z["dx"], z["gun"])}
    hk, ayni, say = _src_hukum(tam, donem)
    b, s, et = SRC_SIRALAMA
    z = dd.loc[b:s]
    sira = _src_ozet(z["dp"], z["dx"], z["gun"])
    son_lbl = dd.index.max()
    z = dd[dd.index > son_lbl - pd.Timedelta(weeks=SRC_SON_HAFTA)]
    son52 = _src_ozet(z["dp"], z["dx"], z["gun"], asgari=SRC_DONEM_ASGARI)
    kay = _src_kayan(d).dropna()
    bek = bilgi["beklenen"]
    out = {
        "para": bilgi["para"], "para_ad": SRC_PARA[bilgi["para"]][0], "surucu": bilgi["surucu"], "surucu_ad": tn["ad"],
        "grup": tn["grup"], "beklenen_isaret": bek, "gerekce": bilgi["gerekce"],
        "birim": birim, "beta_birim": birim_kod, "beta_okur": birim_okur, "saat": tn["saat"],
        "n": tam.get("n"), "ilk": tam.get("ilk"), "son": tam.get("son"),
        "tam": tam, "donemler": donem,
        "donem_ayni_isaret": ayni, "donem_sayisi": say,
        "hukum": hk,
        "hukum_notu": (None if say >= SRC_ISTIKRAR_DONEM else
                       f"seri dört dönemin yalnız {say} tanesinde ölçülebiliyor; 'istikrarlı' en az "
                       f"{SRC_ISTIKRAR_DONEM} dönem ister"),
        # |t| < 2 iken korelasyonun işareti sıfırdan ayırt edilemez: hüküm kurulmaz (CHF–VIX 0,001, t 0,03)
        "beklenen_isaret_tutuyor": (None if tam.get("kor") is None or abs(tam["t"]) < SRC_ISTIKRAR_T
                                    else bool(np.sign(tam["kor"]) == bek)),
        "beklenen_isaret_notu": (f"tam örneklemde |t| < {SRC_ISTIKRAR_T:.0f}: işaret sıfırdan ayırt edilemiyor"
                                 if tam.get("kor") is not None and abs(tam["t"]) < SRC_ISTIKRAR_T else None),
        "siralama_" + b[:4] + "_" + s[:4]: {"etiket": et, **sira},
        "son_52_hafta": son52,
        "kayan_52": ({"n_pencere": int(len(kay)), "beklenen_isarette_pay_yuzde": float((np.sign(kay) == bek).mean() * 100),
                      "en_dusuk": float(kay.min()), "en_dusuk_tarih": _persembe(kay.idxmin()),
                      "en_yuksek": float(kay.max()), "en_yuksek_tarih": _persembe(kay.idxmax()),
                      "medyan": float(kay.median()), "son": float(kay.iloc[-1]), "son_tarih": _persembe(kay.index[-1])}
                     if len(kay) else kurulmadi("kayan pencere için yeterli hafta yok")),
        "gunluk": _src_gunluk_gecikme(bilgi),
        "persembe_payi_yuzde": float((pd.DatetimeIndex(dd["gun"]).dayofweek == SRC_ORNEK_GUN).mean() * 100),
    }
    out["saat_izi_haftalik_eksi_gunluk0"] = (tam["kor"] - out["gunluk"]["para_t_surucu_t"]["kor"]
                                              if tam.get("kor") is not None else None)
    # tek tek örneklense iki seri kaç haftada farklı günden okunurdu (ortak gün kuralı bunu kapatır)
    gp, gx = _src_tek_gun(bilgi["pk"]), _src_tek_gun(bilgi["sk"])
    j = pd.concat([gp.rename("p"), gx.rename("x")], axis=1).loc[SRC_BAS:].dropna()
    out["ayri_gun_haftasi"] = int((j["p"] != j["x"]).sum())
    out["ayri_gun_payi_yuzde"] = float((j["p"] != j["x"]).mean() * 100) if len(j) else None
    dv = _src_devir_olc(d, bilgi, k)
    if dv is not None:
        out["devir"] = dv
    if tn["tur"] == "fark":
        out["bacaklar_haftalik"] = _src_bacak_olc(dd, bilgi, k)
    if bilgi["para"] == "try":
        y = bilgi["yonetilen"].dropna(subset=["dp", "dx"])
        out["yonetilen_donem"] = {"etiket": f"yönetilen kur {oo.YON_AY[0]} … {oo.YON_AY[1]} (ayrı dönem, havuzlanmaz)",
                                  **_src_ozet(y["dp"], y["dx"], y["gun"], asgari=SRC_DONEM_ASGARI)}
        # CNBC TRY (New York 17:00) ile aynı ölçü: kaynak kıyası
        sk, olcek = bilgi["sk"], bilgi["olcek"]
        w = _src_haftalik(("p_try_cnbc", "p_try", sk))
        q = pd.DataFrame({"dp": w["p_try_cnbc"].diff(), "dy": w["p_try"].diff(), "dx": w[sk].diff() * olcek,
                          "gun": w["gun"], "onceki": w["gun"].shift(1)}).loc[SRC_BAS:]
        q = q[~_src_yonetilen(q).fillna(False)].dropna()
        out["cnbc_kiyas"] = {"kor_cnbc_try": float(q["dp"].corr(q["dx"])), "kor_yahoo_try_ayni_gunler": float(q["dy"].corr(q["dx"])),
                             "iki_kaynak_haftalik_kor": float(q["dp"].corr(q["dy"])), "n": int(len(q)),
                             "not": "CNBC New York 17:00, Yahoo 18.12.2023'ten İstanbul 18:00 (öncesi gün sonu); yalnız kıyas."}
    return out


def _src_veri_denetimi() -> dict:
    """Her sütunun kapsamı, boşlukları, bayat kotasyon payı, perşembe örneklemesi, temizlik ve vade devri."""
    D, rapor = _src_gunluk()
    s = bulut.surucu_gunluk()
    hafta_sonu = int((s.index.dayofweek >= 5).sum())
    kullanilan = sorted({c for a, *_ in SRC_CIFTLER for c in (_src_cift_veri(a)[1].get("kolonlar", ())
                                                              + _src_cift_veri(a)[1].get("kiyas_kolonlar", ()))}
                        | {"p_try_cnbc"})
    seriler = {}
    for c in kullanilan:
        x = D[c].loc[SRC_BAS:].dropna()
        if x.empty:
            continue
        idx = x.index
        bosluk = pd.Series(idx[1:] - idx[:-1], index=idx[1:])
        bosluk = bosluk[bosluk > pd.Timedelta(days=7)].sort_values(ascending=False)
        ayni = x.diff().dropna() == 0
        dizi = (x != x.shift()).cumsum()
        g = _src_tek_gun(c).loc[SRC_BAS:].dropna()
        w = x[x.index.dayofweek <= SRC_ORNEK_GUN].resample("W-FRI").last()
        w = w[w.index - pd.Timedelta(days=1) <= oo.CIPA_GUN].diff().dropna()
        seriler[c] = {"ad": _src_kolon_ad(c), "n": int(len(x)), "ilk": _iso(idx.min()), "son": _iso(idx.max()),
                      "bosluk_sayisi_7_gunden_uzun": int(len(bosluk)),
                      "en_uzun_bosluklar": [{"ilk": _iso(t - b), "son": _iso(t), "gun": int(b.days)}
                                            for t, b in bosluk.head(3).items()],
                      "bayat_gun_payi_yuzde": float(ayni.mean() * 100),
                      "en_uzun_ayni_deger_gun": int(x.groupby(dizi).size().max()),
                      "haftalik_sifir_degisim_payi_yuzde": float((w == 0).mean() * 100),
                      "persembe_payi_yuzde": float((pd.DatetimeIndex(g.values).dayofweek == SRC_ORNEK_GUN).mean() * 100)}
    # bayat kotasyonun yıllara dağılımı (Japonya 2 yıllık; sıfıra yakın faizde ayrım veriyle yapılamaz)
    jp = (D["y_jp2y"].loc[SRC_BAS:].dropna().diff().dropna() == 0)
    jp_yil = jp.groupby(jp.index.year).mean() * 100
    # ABD bacağı kaynak seçimi (tuzak 12)
    abd = {}
    for v, c in (("2y", "us2"), ("10y", "us10")):
        z = D[[f"y_{c}", f"y_{c}_cnbc"]].loc[SRC_BAS:].dropna()
        dz = z.diff().dropna() * 100
        w = z[z.index.dayofweek <= SRC_ORNEK_GUN].resample("W-FRI").last().diff().dropna() * 100
        sifir = dz[dz[f"y_{c}_cnbc"] == 0]
        oynayan = float((sifir[f"y_{c}"].abs() > 0).mean() * 100) if len(sifir) else None
        hsifir = dz[dz[f"y_{c}"] == 0]
        # simetrik sınama: sıfır değişim günlerinde öbür kaynak iki yönde benzer payla oynuyorsa bu bayat kotasyon
        # değil, iki ayrı anlık görüntünün yuvarlamasıdır (tuzak 12)
        h_oynayan = float((hsifir[f"y_{c}_cnbc"].abs() > 0).mean() * 100) if len(hsifir) else None
        cn = z[f"y_{c}_cnbc"] * 100
        abd[v] = {"ortak_gun": int(len(z)), "gunluk_degisim_kor": float(dz.corr().iloc[0, 1]),
                  "haftalik_degisim_kor": float(w.corr().iloc[0, 1]), "n_hafta": int(len(w)),
                  "cnbc_sifir_degisim_payi_yuzde": float((dz[f"y_{c}_cnbc"] == 0).mean() * 100),
                  "hazine_sifir_degisim_payi_yuzde": float((dz[f"y_{c}"] == 0).mean() * 100),
                  "cnbc_sifir_gunlerinde_hazine_mutlak_degisim_medyan_bp": float(sifir[f"y_{c}"].abs().median()),
                  "cnbc_sifir_gunlerinde_hazine_oynayan_pay_yuzde": oynayan,
                  "hazine_sifir_gunlerinde_cnbc_oynayan_pay_yuzde": h_oynayan,
                  "cnbc_kotasyonu_bp_cozunurlukte_pay_yuzde": float(((cn - cn.round()).abs() < 1e-6).mean() * 100),
                  "duzey_fark_medyan_bp": float((z[f"y_{c}_cnbc"] - z[f"y_{c}"]).median() * 100)}
    # vade devri: tahmini devir günündeki günlük değişim öbür günlerle (ortalama kare farkı devir sıçramasının ölçüsü)
    devir = {}
    for a, (kural, aylar, pen) in SRC_DEVIR.items():
        x = np.log(s[a].dropna()) * 100
        x = x[x.index.dayofweek < 5]
        dx = x.diff().loc[SRC_BAS:].dropna()
        R = _src_devir_gunleri(a)
        m = dx.index.isin(R)
        sd_r, sd_o = float(dx[m].std()), float(dx[~m].std())
        tk, th = _src_devir_tahmini(a, "kendi"), _src_devir_tahmini(a, "hafta_ici")
        aylar_ic = [p for p in tk if SRC_BAS <= tk[p] <= oo.CIPA_GUN]
        devir[a] = {"kural": kural, "kural_ad": SRC_DEVIR_AD[kural] if not (kural == "ay_sonu" and aylar is None)
                    else SRC_DEVIR_AD["ay_sonu_aylik"],
                    "sozlesme_aylari": list(aylar) if aylar else "her ay",
                    "n_sozlesme_ayi": len(aylar_ic),
                    "hafta_ici_takvimle_farkli_sozlesme_ayi": int(sum(1 for p in aylar_ic if th.get(p) != tk[p])),
                    "pencere_is_gunu": list(pen), "n_devir_gunu": int(m.sum()),
                    "devir_gunu_sd_yuzde": sd_r, "obur_gunler_sd_yuzde": sd_o,
                    "devir_sicramasi_sd_yuzde": float(math.sqrt(max(sd_r ** 2 - sd_o ** 2, 0.0))),
                    "devir_gunu_mutlak_medyan_yuzde": float(dx[m].abs().median()),
                    "obur_gunler_mutlak_medyan_yuzde": float(dx[~m].abs().median())}
    # CNBC G10 kurlarının sürücü arşivindeki kopyası depodaki seriyle aynı mı (bozuk günler dışında)
    g10 = oo.cnbc_kur()
    ic = {}
    for kod in oo.SEPET:
        z = pd.concat([s[kod].rename("a"), g10[kod].rename("b")], axis=1, sort=True).dropna()
        ic[kod] = {"ortak_gun": int(len(z)), "azami_fark_bp": float((np.log(z["a"] / z["b"]).abs() * 1e4).max())}
    return {
        "yontem": ("Her serinin 2010 sonrası kapsamı, 7 günden uzun boşlukları, ardışık iki işlem gününde aynı değeri "
                   "taşıyan gün payı (bayat kotasyon), haftalık değişimi sıfır olan hafta payı, kendi başına örneklense "
                   "perşembe gününün payı; geri dönen tek günlük sıçramalar; yakın vade vadelilerinde tahmini devir "
                   "günündeki günlük değişimin oynaklığı."),
        "hafta_sonu_bar": hafta_sonu,
        "hafta_sonu_notu": "Sürücü arşivinde hafta sonu barı yok (hazırlıkta ayıklandı: kaynakta cumanın kopyasıydı).",
        "seriler": seriler,
        "japonya_2y_bayat_yillik_yuzde": {str(k): float(v) for k, v in jp_yil.items()},
        "kur_temizlik": rapor["kur_temizlik"], "getiri_temizlik": rapor["getiri_temizlik"],
        "temizlik_kurali": (f"Bir günün değişimi ve ertesi günün değişimi ikisi de eşiği aşıyor, işaretleri ters ve "
                            f"iki günlük net hareket küçüğünün yarısından az: kurda %{SRC_KUR_SICRAMA * 100:.1f} (log), "
                            f"getiride {SRC_GETIRI_SICRAMA_BP:.0f} bp. Emtia temizlenmez: aynı kural petrolün gerçek "
                            "oynak günlerini de yakalıyor."),
        "kurulmayan": rapor["kurulmayan"],
        "abd_bacagi": abd,
        "abd_bacagi_secimi": ("ABD bacağı ABD Hazinesi par eğrisinden: resmî kaynak ve altının reel faiz sürücüsüyle "
                              "aynı yayım. Bedeli çözünürlüktür: Hazine iki ondalıkla (1 bp) yayımlar ve 2 yıllıkta "
                              "değişimi sıfır günlerin payı sıfır faiz yıllarında yükselir; CNBC 2 yıllığı daha ince "
                              "yazar. 10 yıllıkta iki kaynak da çoğunlukla 1 bp çözünürlüklüdür ve bir kaynağın sıfır "
                              "değişim günlerinde öbürü iki yönde de benzer payla oynar (paylar alanda): bu bayat "
                              "kotasyonun değil, iki ayrı anlık görüntünün yuvarlamasının izidir; iki kaynaktan "
                              "hiçbiri bu ölçüyle bayat sayılamaz. CNBC'nin 2014 boşlukları yerel bacaklarda da olduğu "
                              "için fark satırlarında kazanç getirmez. İki kaynağın haftalık değişimi neredeyse aynıdır "
                              "ve seçim sonucu değiştirmez: faiz farkı satırlarında ABD bacağı CNBC'den kurulunca "
                              "korelasyon, iki tanımın birlikte bulunduğu günlerde Hazine tanımıyla yan yana yazılı."),
        "abd_2y_hazine_sifir_degisim_yillik_yuzde": {
            str(k): float(v) for k, v in
            ((D["y_us2"].loc[SRC_BAS:].dropna().diff().dropna() == 0)
             .pipe(lambda z: z.groupby(z.index.year).mean() * 100)).items()},
        "devir": devir,
        "devir_notu": ("Devir günü borsanın son işlem günü kuralından tahmin edilir; işaretlenen pencere tahmindeki bir "
                       "iki günlük kaymayı kapsar. Haftalık ölçüde devir haftası, perşembeden perşembeye penceresi bu "
                       "günlerden birini içeren haftadır. Kural vadelinin kendi işlem günü takviminde sayılır: "
                       "borsa tatilleri doğru düşer (her hafta içi gününü iş günü sayan takvim, WTI'de Şükran Günü "
                       "gibi tatillerde son işlem gününü bir gün kaydırırdı), ama kaynaktaki veri boşluğu da tatil "
                       "sayılır. İki takvimin farklı tahmin verdiği sözleşme ayı sayısı satırda."),
        "g10_ic_sinama": ic,
    }


def _src_saat_sinamasi() -> dict:
    """Yerel getirinin kapanış saati ölçüyle: yerel getirinin t günkü değişimi ABD getirisinin t ve t−1 günkü
    değişimiyle. Kapanışı New York'tan önce olan piyasada (Asya-Pasifik) yerel değişim bir önceki New York
    gününün ABD hareketini taşır (t−1 korelasyonu t'ninkini geçer)."""
    D, _ = _src_gunluk()
    out = {}
    for ad, tn in SRC_SURUCU.items():
        if tn["tur"] != "fark" or f"y_{tn['yerel']}" not in D.columns:
            continue
        y = D[f"y_{tn['yerel']}"].diff().loc[SRC_BAS:]
        a = D[f"y_{tn['abd']}"].diff().loc[SRC_BAS:]
        r = {}
        for k, ka in (("abd_t", 0), ("abd_t_eksi_1", 1), ("abd_t_arti_1", -1)):
            z = pd.concat([y.rename("y"), a.shift(ka).rename("a")], axis=1).dropna()
            r[k] = {"kor": float(z["y"].corr(z["a"])), "n": int(len(z))}
        r["kapanis"] = ("New York'tan önce (önceki New York gününü taşır)"
                        if r["abd_t_eksi_1"]["kor"] > r["abd_t"]["kor"] else "New York ile aynı gün")
        out[tn["yerel"]] = {"ad": _SRC_GETIRI_AD.get(tn["yerel"], tn["yerel"]), **r}
    return {"yontem": ("Yerel 2 ve 10 yıllık getirinin günlük değişimi ile ABD getirisinin aynı gün, bir önceki gün ve "
                       "bir sonraki gün değişimi arasındaki korelasyon (2010 sonrası)."),
            "getiriler": out}


def _src_kapsam_notlari(satirlar: dict) -> None:
    """Faiz farkı satırlarına kaynak kapsamının notu, VERİDEN (elle yazılmış tarih yok): yerel getirinin kaynaktaki
    ilk gözlemi örneklemin başından bir yıldan geçse; aynı paranın başka bir faiz farkı satırı kurulamadıysa (ikame)
    ya da kısa örneklemliyse (bu satır uzun örneklemi verir)."""
    D, _ = _src_gunluk()

    def ilk(v):
        c = f"y_{SRC_SURUCU[v['surucu']]['yerel']}"
        return D[c].dropna().index.min() if c in D.columns else None

    def kisa(v):
        t = ilk(v)
        return t is not None and t > SRC_BAS + pd.DateOffset(years=1)
    for a, v in satirlar.items():
        if v.get("durum") == "kurulmadi" or SRC_SURUCU[v["surucu"]]["tur"] != "fark":
            continue
        notlar = []
        if kisa(v):
            notlar.append(f"{_SRC_GETIRI_AD[SRC_SURUCU[v['surucu']]['yerel']]} getirisi kaynakta "
                          f"{ilk(v).strftime('%m.%Y')} ayında başlıyor")
        for b, u in satirlar.items():
            if b == a or u.get("para") != v["para"] or SRC_SURUCU[u["surucu"]]["tur"] != "fark":
                continue
            if u.get("durum") == "kurulmadi":
                notlar.append(f"{SRC_SURUCU[u['surucu']]['ad']} kurulamadığı için ikame satır")
            elif kisa(u) and not kisa(v):
                notlar.append(f"kısa örneklemli kardeş satırın ({SRC_SURUCU[u['surucu']]['ad']}) yanında uzun "
                              "örneklemi verir")
        v["kapsam_notu"] = ("; ".join(notlar) + ".") if notlar else None


def _src_siralama(satirlar: dict) -> dict:
    """Her para için sürücülerin |haftalık korelasyon| sırası (2015–2026) ve dönem dönem en güçlü sürücü. Kıyas
    aynı pencerede ölçülen sürücüler arasında kurulur: paranın en geniş kapsamlı sürücüsünün haftalarının
    `SRC_KAPSAM_ORAN`ından azını taşıyan sürücü listede durur ama 'en güçlü' sayılamaz (tuzak 21)."""
    b, s, _ = SRC_SIRALAMA
    sk = "siralama_" + b[:4] + "_" + s[:4]
    out = {}
    for para in SRC_HARITA_SATIR:
        r = [(a, v) for a, v in satirlar.items() if v.get("para") == para and v.get("durum") != "kurulmadi"]
        if not r:
            continue
        olc = [(a, v[sk]["kor"], v["surucu"], v[sk]["n"]) for a, v in r if v[sk].get("kor") is not None]
        nmax = max((z[3] for z in olc), default=0)
        sira = sorted(olc, key=lambda z: -abs(z[1]))
        kiyas = [z for z in sira if z[3] >= SRC_KAPSAM_ORAN * nmax]
        donem = {}
        for ad, *_rest in SRC_DONEMLER:
            dz = [(v["surucu"], v["donemler"][ad]["kor"], v["donemler"][ad]["n"]) for _, v in r
                  if v["donemler"][ad].get("kor") is not None]
            nm = max((z[2] for z in dz), default=0)
            dk = sorted((z for z in dz if z[2] >= SRC_KAPSAM_ORAN * nm), key=lambda z: -abs(z[1]))
            donem[ad] = ({"en_guclu": dk[0][0], "kor": dk[0][1], "n_surucu": len(dk),
                          "kisa_kapsamli": [z[0] for z in dz if z[2] < SRC_KAPSAM_ORAN * nm]} if dk else None)
        tepe = [v["en_guclu"] for v in donem.values() if v and v["n_surucu"] >= 2]
        out[para] = {"sira": [{"cift": a, "surucu": su, "kor": k, "n": n, "kapsam_payi_yuzde": 100.0 * n / nmax,
                               "kiyaslanabilir": bool(n >= SRC_KAPSAM_ORAN * nmax)} for a, k, su, n in sira],
                     "en_guclu": kiyas[0][2] if kiyas else None, "en_guclu_kor": kiyas[0][1] if kiyas else None,
                     "donemler": donem,
                     "donemden_doneme_degisiyor": (len(set(tepe)) > 1) if len(tepe) >= 2 else None,
                     "n_surucu": len(kiyas), "n_surucu_kisa_kapsamli": len(sira) - len(kiyas)}
    return out


@lru_cache(maxsize=1)
def _p10c_ic() -> dict:
    satirlar = {a: dict(_src_satir(a)) for a, *_ in SRC_CIFTLER}
    _src_kapsam_notlari(satirlar)
    ok = [v for v in satirlar.values() if v.get("durum") != "kurulmadi"]
    say = {h: sum(1 for v in ok if v["hukum"] == h) for h in ("istikrarlı", "dönemsel", "zayıf")}
    kon = satirlar[SRC_SAAT_KONTROL]
    return {
        "yontem": ("Her para dolara karşı değeriyle (artış değer kazancı; altın $/ons fiyatıyla) girer. Perşembe "
                   "kapanışından perşembe kapanışına haftalık değişim: iki serinin birlikte bulunduğu haftanın "
                   "perşembeye kadarki son günü (biri tatilse ikisi aynı önceki güne çekilir). Korelasyon (Pearson "
                   "ve sıra), Newey–West standart hatalı eğim (paranın %'si / sürücünün birimi), dört dönem, son 52 "
                   "hafta ve 52 haftalık kayan korelasyon; günlük değişimde gecikme 0 ve ±1 gün. Hüküm: tam "
                   "örneklemde |t| ≥ 2 ve dört dönemin en az üçünde aynı işaret 'istikrarlı', |t| ≥ 2 ama daha az "
                   "dönemde 'dönemsel', |t| < 2 'zayıf'. Hepsi eşzamanlı tariftir: haftalık sürücü değişimi önceden "
                   "bilinmez, öngörü iddiası kurulmaz."),
        "kaynak": SRC_KAYNAK,
        "n": int(sum(v["n"] for v in ok)), "n_cift": len(ok), "n_cift_kurulmayan": len(satirlar) - len(ok),
        "ilk": min(v["ilk"] for v in ok), "son": max(v["son"] for v in ok),
        "hukum_sayimi": say,
        "yon_sozlesmesi": ("Paranın değeri dolara karşı: EUR, GBP, AUD, NZD kotasyonu doğrudan, öbür paralarda (USD/XXX) "
                           "işaret çevrilir. Faiz farkı 'yerel − ABD' yönünde: fark artarsa (yerel getiri ABD'ninkine "
                           "göre yükselirse; fark eksiyse sıfıra yaklaşırsa) yerel para lehine. "
                           "Sürücüler: emtia log fiyat değişimi (%), getiri farkı ve ABD reel faizi (bp), VIX (puan), "
                           "S&P 500 log değişimi (%), yuan değeri (%), doların sepete karşı değeri (%)."),
        "saat_notu": ("Döviz New York 17:00 (CNBC), USD/TRY Yahoo (18.12.2023'ten İstanbul 18:00, öncesi gün sonu), "
                      "vadeliler borsa seansı, yerel getiriler kendi piyasasının kapanışı (Tokyo, Sydney, Avrupa), "
                      "ABD getirileri New York öğleden sonra, VIX 16:15. Haftalık ölçüde saat farkı haftanın küçük bir "
                      "parçasıdır; günlük ölçüde Tokyo ve Sydney kapanışlı getiri bir gün öne kayar. Haftalık ile "
                      "günlük gecikme-0 korelasyonu arasındaki fark yalnız saatten gelmez; iki serisi de New York "
                      "17:00 kapanışı olan kontrol çiftindeki fark ölçünün kendi payıdır (saat kontrolü)."),
        "saat_kontrolu": {"cift": SRC_SAAT_KONTROL, "ad": f"{kon['para_ad']} – {kon['surucu_ad']}",
                          "saat_izi_haftalik_eksi_gunluk0": kon["saat_izi_haftalik_eksi_gunluk0"],
                          "not": ("İki serisi de New York 17:00 kapanışı olan çiftte haftalık korelasyon eksi günlük "
                                  "gecikme-0 korelasyonu: saat farkı yokken fark sıfıra yakın çıkar. Öbür satırlarda "
                                  "bu kontrolün üstünde kalan fark saat farkının izidir.")},
        "donemler": [{"anahtar": a, "ilk": b, "son": s, "etiket": e} for a, b, s, e in SRC_DONEMLER],
        "turkiye_notu": (f"USD/TRY Yahoo'dan (karar 09.09.2026; CNBC TRY yalnız kıyas). Yönetilen kur dönemi "
                         f"({oo.YON_AY[0]} … {oo.YON_AY[1]}) TRY ölçülerinde dışarıdadır ve ayrı dönem olarak "
                         "yazılır; perşembeden perşembeye penceresi o dönemle kesişen hafta düşer."),
        "ciftler": satirlar,
        "siralama": _src_siralama(satirlar),
        "saat_sinamasi": _src_saat_sinamasi(),
        "veri_denetimi": _src_veri_denetimi(),
    }


def p10c() -> dict:
    return _p10c_ic()


# ───────────────────────────────────────────────────────── sürücü figürleri
def sekil_surucu_harita() -> dict:
    p = _p10c_ic()
    b, s, et = SRC_SIRALAMA
    sk = "siralama_" + b[:4] + "_" + s[:4]
    hucre = []
    for para in SRC_HARITA_SATIR:
        tum = [v for v in p["ciftler"].values() if v.get("para") == para and v.get("durum") != "kurulmadi"
               and v[sk].get("kor") is not None]
        nmax = max((v[sk]["n"] for v in tum), default=0)
        satir = []
        for g, _ in SRC_GRUPLAR:
            r = [v for v in tum if v.get("grup") == g]
            if not r:
                satir.append(None)
                continue
            kiyas = [z for z in r if z[sk]["n"] >= SRC_KAPSAM_ORAN * nmax]
            v = max(kiyas or r, key=lambda z: abs(z[sk]["kor"]))
            satir.append({"surucu": v["surucu"], "surucu_ad": v["surucu_ad"], "kor": v[sk]["kor"], "n": v[sk]["n"],
                          "ilk": v[sk]["ilk"], "kapsam_payi_yuzde": 100.0 * v[sk]["n"] / nmax,
                          "kisa_kapsam": bool(v[sk]["n"] < SRC_KAPSAM_ORAN * nmax),
                          "beklenen_isaret": v["beklenen_isaret"],
                          "ters": bool(np.sign(v[sk]["kor"]) != v["beklenen_isaret"]),
                          "etiket": v["hukum"], "alternatif": [z["surucu"] for z in r if z is not v],
                          "kisa_kapsamli": [z["surucu"] for z in r if z[sk]["n"] < SRC_KAPSAM_ORAN * nmax]})
        hucre.append(satir)
    dolu = [c for r in hucre for c in r if c]
    return {"baslik": "Kur sürücüleri haritası: haftalık korelasyon, 2015–2026",
            "yontem": ("Satır para (dolara karşı değeri; altın $/ons), sütun sürücü grubu; hücre 2015–2026 haftalık "
                       "(perşembeden perşembeye) değişim korelasyonu. Grupta birden çok sürücü varsa |korelasyonu| en "
                       "yüksek olanı, ama yalnız pencereyi kapsayanlar arasından: hafta sayısının paranın en geniş "
                       f"kapsamlı sürücüsününkine oranı %{SRC_KAPSAM_ORAN * 100:.0f} eşiğinin altında kalan sürücü "
                       "(kaynakta geç başlayan ya da yıllarca boş seri) seçilmez, hücrede adıyla durur. İşareti "
                       "beklenene ters olan hücre işaretli; etiket tam örneklem hükmü."),
            "kaynak": SRC_KAYNAK, "n": len(dolu), "ilk": b, "son": s,
            "satirlar": list(SRC_HARITA_SATIR), "satir_ad": [SRC_PARA[k][0] for k in SRC_HARITA_SATIR],
            "sutunlar": [g for g, _ in SRC_GRUPLAR], "sutun_ad": [a for _, a in SRC_GRUPLAR],
            "hucre": hucre,
            "not": "Eşzamanlı tarif; öngörü değildir. Boş hücre: o para için o grupta çift ölçülmedi."}


def sekil_surucu_kayan() -> dict:
    p = _p10c_ic()
    seriler, ad, ozet = {}, {}, {}
    for a in SRC_KAYAN_CIFTLER:
        d, _ = _src_cift_veri(a)
        k = _src_kayan(d)
        seriler[a] = k
        v = p["ciftler"][a]
        ad[a] = f"{v['para_ad']} – {v['surucu_ad']}"
        ozet[a] = {"beklenen_isaret": v["beklenen_isaret"], "kor_tam": v["tam"]["kor"], "hukum": v["hukum"],
                   "beklenen_isarette_pay_yuzde": v["kayan_52"].get("beklenen_isarette_pay_yuzde")}
    df = pd.DataFrame(seriler).sort_index()
    df = df.loc[df.notna().any(axis=1).idxmax():] if len(df) else df
    return {"baslik": "Başlıca sekiz çiftin 52 haftalık kayan korelasyonu",
            "yontem": ("Perşembeden perşembeye haftalık değişimlerin 52 haftalık kayan korelasyonu (pencerede en az "
                       f"{SRC_KAYAN_ASGARI} ortak hafta); hafta tarihi perşembedir."),
            "kaynak": SRC_KAYNAK, "n": int(df.notna().sum().sum()),
            "ilk": _persembe(df.index.min()), "son": _persembe(df.index.max()),
            "tarih": [_persembe(t) for t in df.index],
            "seriler": {a: [None if pd.isna(x) else float(x) for x in df[a]] for a in SRC_KAYAN_CIFTLER},
            "ad": ad, "ozet": ozet, "ciftler": list(SRC_KAYAN_CIFTLER)}


def sekil_usdjpy() -> dict:
    """USD/JPY ile (ABD − Japonya) 2 ve 10 yıllık getiri farkı: seviye (iki ayrı panel) ve 52 haftalık kayan
    korelasyon ve eğim (değişimden). Seviye korelasyonu yalnız figür ve uyarı içindir."""
    D, _ = _src_gunluk()
    out_lv = {}
    for v in ("2y", "10y"):
        w = _src_haftalik(("p_jpy", f"f_jp_us_{v}"))
        out_lv[v] = pd.DataFrame({"usdjpy": np.exp(-w["p_jpy"] / 100), "fark": -w[f"f_jp_us_{v}"]}).loc[SRC_BAS:]
    eksen = out_lv["2y"].index.union(out_lv["10y"].index)
    wj = D["p_jpy"].dropna()
    wj = wj[wj.index.dayofweek <= SRC_ORNEK_GUN].resample("W-FRI").last()
    wj.index = wj.index - pd.Timedelta(days=1)
    wj = np.exp(-wj[(wj.index <= oo.CIPA_GUN) & (wj.index >= SRC_BAS)] / 100)
    eksen = eksen.union(wj.index)
    kay, beta, sev = {}, {}, {}
    for v in ("2y", "10y"):
        d, _ = _src_cift_veri(f"jpy_jp_us_{v}")
        kay[v] = _src_kayan(d).reindex(eksen)
        cov = d["dp"].rolling(SRC_KAYAN, min_periods=SRC_KAYAN_ASGARI).cov(d["dx"])
        var = d["dx"].where(d["dp"].notna()).rolling(SRC_KAYAN, min_periods=SRC_KAYAN_ASGARI).var()
        beta[v] = (cov / var).reindex(eksen)          # yenin değeri / (JP − US) = USD/JPY % / (US − JP) bp
        z = out_lv[v].dropna()
        lz = pd.DataFrame({"l": np.log(z["usdjpy"]) * 100, "f": z["fark"]})
        sev[v] = {"tam": {"kor": float(lz["l"].corr(lz["f"])), "n": int(len(lz)),
                          "ilk": _persembe(lz.index.min()), "son": _persembe(lz.index.max())},
                  "donemler": {ad: ({"kor": float(q["l"].corr(q["f"])), "n": int(len(q))}
                                    if len(q := lz.loc[bb:ss]) >= SRC_DONEM_ASGARI else kurulmadi("dönemde gözlem az"))
                               for ad, bb, ss, _ in SRC_DONEMLER},
                  "degisim_kor_tam": _p10c_ic()["ciftler"][f"jpy_jp_us_{v}"]["tam"]["kor"]}

    def liste(x):
        return [None if pd.isna(t) else float(t) for t in x]
    return {"baslik": "USD/JPY ve ABD − Japonya getiri farkı",
            "yontem": ("Haftalık (perşembe) USD/JPY seviyesi ve ABD − Japonya 2 ve 10 yıllık getiri farkı (%, ABD "
                       "Hazinesi par getirisi eksi CNBC Japonya getirisi); 52 haftalık kayan korelasyon ve eğim haftalık "
                       "değişimlerden (USD/JPY'nin %'si / farkın 1 bp'si). Seviye korelasyonu iki eğilimli serinin "
                       "ortak eğiliminden şişebilir; hüküm değişimden kurulur."),
            "kaynak": SRC_KAYNAK[:3], "n": int(len(eksen)), "ilk": _persembe(eksen.min()), "son": _persembe(eksen.max()),
            "tarih": [_persembe(t) for t in eksen],
            "usdjpy": liste(wj.reindex(eksen)),
            "abd_eksi_japonya_2y_yuzde": liste(out_lv["2y"]["fark"].reindex(eksen)),
            "abd_eksi_japonya_10y_yuzde": liste(out_lv["10y"]["fark"].reindex(eksen)),
            "kor52_2y": liste(kay["2y"]), "kor52_10y": liste(kay["10y"]),
            "beta52_2y_yuzde_bp": liste(beta["2y"]), "beta52_10y_yuzde_bp": liste(beta["10y"]),
            "seviye_korelasyonu": sev,
            "uyari": ("Seviye korelasyonu ölçü değildir: iki seri yıllarca birlikte eğilim gösterdiğinde seviyeler "
                      "ilişkisiz değişimlerle de yüksek korelasyon verir. Ders hükmü haftalık değişimden kurar."),
            "panel_notu": "Seviye iki ayrı panelde (USD/JPY; getiri farkları), çift eksen yok."}


# ───────────────────────────────────────────────────────── giriş
def olc() -> dict:
    out = {"p10a": p10a(), "p10b": p10b(), "sekil_17": sekil_17(),
           "p10c": p10c(), "sekil_surucu_harita": sekil_surucu_harita(),
           "sekil_surucu_kayan": sekil_surucu_kayan(), "sekil_usdjpy": sekil_usdjpy()}
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"\n{time.monotonic() - t0:.1f} sn")
