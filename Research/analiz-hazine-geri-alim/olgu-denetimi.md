# Olgu denetimi — hazine-geri-alim.mdx (çekişmeli)

Denetim tarihi: 24.08.2026. Yöntem: her sayı birincil kaynağa geri götürüldü
(Hazine basın bültenleri, geçici takvim PDF'i, Treasury Fiscal Data API, Treasury
günlük CMT/reel CMT CSV'leri 2000–2026, NY Fed ACM Excel, NY Fed SOMA API,
Fed H.4.1, MSPD, MTS, TIC Tablo 5, ODM/TBAC sunumu, Liberty Street Economics).
İkincil kaynaklar (Bloomberg/Yahoo sendikasyonu, CNBC, AP/HuffPost, Reuters,
Robeco, OFR) ayrıca açıldı ve alıntılar tek tek eşleştirildi.

Sonuç özeti: **yazının sayısal omurgası büyük ölçüde sağlam.** 60'ın üzerinde
birincil sayı birebir doğrulandı. Buna karşılık 7 sert hata, 8 zayıf/kırılgan nokta
bulundu. Hatalardan biri (§2.4 "doluluk istisnasız %100") yazının izleme listesindeki
bir eşiği de geçersiz kılıyor.

---

## A. SERT HATALAR

### A1. "Doluluk istisnasız %100'dü" — YANLIŞ (§2.4, ayrıca §9 eşik tablosu)

**İddia:** "2026'nın ilk sekiz buçuk ayında ... doluluk **istisnasız %100**'dü."

**Neden yanlış:** 19 Mart 2026 tarihli 20–30 yıl likidite desteği operasyonunda
Hazine 2,000 milyar dolarlık tavana karşılık yalnızca **0,205 milyar dolar** aldı —
**doluluk %10,2**. Teklif o gün 36,003 milyar dolardı (teklif/azami 18,00× — yazının
"18,2×" üst sınırına yakın; yani yazı bu operasyonun teklif verisini kullanmış ama
kabul verisini görmemiş).

**Doğrusu:** 22 uzun uç operasyonundan 21'inde doluluk %100, 1'inde %10,2.

**Kaynak:** Treasury Fiscal Data, `buybacks_operations` veri seti (çekim 24.08.2026),
operation_date 2026-03-19, maturity_bucket "20Y to 30Y":
max_par_amt_redeemed 2.000.000.000 / total_par_amt_accepted 205.000.000.
Ayrıca Hazine'nin kendi ODM sunumu (TreasuryPresentationToTBACQ32026.pdf, s.54)
"continues to **generally** buy back the maximum par amount" diyor — "always" değil.
10–20 yıl kovası için aynı slaytta (s.53) "continues to buy back the maximum" deniyor;
istisna yalnız 20–30 yılda.

**İkinci etki:** §9 izleme tablosundaki "Doluluk oranı %100'ün altına inerse →
Hazine fiyata duyarlı davranıp kapasiteyi kullanmıyor; 'likidite desteği' anlatısı
zayıflar" eşiği **zaten beş ay önce tetiklenmiş** durumda. Eşik olarak kullanılamaz;
ya kaldırılmalı ya da "ikinci kez" diye yeniden kurulmalı.

---

### A2. 2000–02 programının yıl bazında operasyon sayıları — YANLIŞ (§5.1)

**İddia:** "2000'de **16 operasyonda** 30,0 milyar, 2001'de **26 operasyonda**
33,5 milyar, 2002'de 3 operasyonda 4,0 milyar."

**Doğrusu:** 2000'de **20 operasyon** (30,005 milyar dolar), 2001'de **22 operasyon**
(33,502 milyar dolar), 2002'de 3 operasyon (4,000 milyar dolar).

**Kaynak:** Treasury Fiscal Data `buybacks_operations`, 2000-03-09 – 2002-04-25 arası
45 kayıt. Toplam 67,507 milyar dolar.

Not: toplam (45 op / 67,5 milyar dolar), ortalama operasyon büyüklüğü (1,5 milyar dolar)
ve karşılama oranı istatistikleri (min 2,14× / maks 8,98× / ortalama 4,39×) **doğru**.
Yalnız yıllara dağılım yanlış. 16+26 = 42 ve 20+22 = 42 olduğu için toplam tutuyor —
hata bu yüzden gözden kaçmış.

---

### A3. 30 yıllık başabaş bandı çok dar — YANLIŞ (§4.1, ayrıca §9 eşik tablosu)

**İddia:** "30 yıllık başabaş enflasyon bir yıldır **2,18–2,27** bandında hareketsiz."
§9: "30 yıllık başabaş | 2,18–2,27 bandını yukarı kırarsa | ..."

**Neden yanlış:** Yazının kendi tarif ettiği yöntemle (nominal par CMT − reel par CMT,
30 yıl), 2026 yılbaşından 21 Ağustos'a kadar 161 gözlemin aralığı **2,15 – 2,34**:
- Zirve **2,34** — 19.05.2026
- Dip **2,15** — 24.06.2026
Yani band hem yukarı hem aşağı kırılmış; §9 eşiği Mayıs'ta zaten tetiklenmiş.

Dahası olay penceresinin içinde: 17.08 = 2,25 · 18.08 = 2,25 · 19.08 = 2,25 ·
**20.08 = 2,28** · 21.08 = 2,27. 20 Ağustos zaten bandın üstünde.

**Kaynak:** home.treasury.gov, Daily Treasury Par Yield Curve Rates 2026 ve
Daily Treasury Par Real Yield Curve Rates 2026 (CSV, çekim 24.08.2026).

---

### A4. 18 Ağustos operasyonunun vade aralığı — YANLIŞ (§2.4 tablosu)

**İddia:** "Vade aralığı | 15.11.2046 – 15.05.2056"

**Doğrusu:** İki farklı doğru sayı var, ikisi de bu değil:
- Geçici takvimin ilan ettiği pencere: **19.08.2046 – 18.08.2056**
- Fiilen uygun 36 CUSIP'in kapsadığı gerçek vade aralığı: **15.02.2047 – 15.02.2056**

**Kaynak:** Tentative-Buyback-ScheduleQ32026.pdf (05.08.2026), 8/18/2026 satırı;
Fiscal Data `buybacks_security_details`, operation_date 2026-08-18 (36 kayıt).

---

### A5. CBO revizyonu yanlış belgeye atfedilmiş (§4.2 ve §10/9)

**İddia:** "CBO, FY2026 açık tahminini ... 2,1 trilyon dolara yükseltti; gerekçe
Yüksek Mahkeme'nin IEEPA tarifelerini iptali sonucu ~250 milyar dolar düşük gümrük
geliri. (Bu revizyon CBO'nun **Temmuz 2026 aylık bütçe incelemesine** dayanıyor;
belgenin PDF'ine doğrudan erişilemedi, içerik ikincil aktarımla alındı — bu yazının
en zayıf sayılarından biri.)"

**Neden şüpheli:** İçeriğin kendisi doğru (1,9 → 2,1 trilyon dolar; ~250 milyar dolar
gümrük geliri açığı; Yüksek Mahkeme'nin 20 Şubat IEEPA kararı). Ama kaynak yanlış:
Aylık Bütçe İncelemesi (yayın no. 61983) tam yıl projeksiyon revizyonu içermez.
Revizyonun yeri ayrı bir CBO yayınıdır:
**"CBO's Updated Budgetary Projections of Tariffs as of July 31, 2026",
yayın no. 62704** (~10.08.2026), cbo.gov/publication/62704.

**Sonuç:** Yazı gereksiz yere bir "erişilemedi / ikincil aktarım" uyarısı taşıyor.
Doğru belge kamuya açık ve birincil. Hem atıf hem de öz-eleştiri notu düzeltilmeli.
(Denetimde cbo.gov 403 döndürdü — bot engeli; içerik Fortune ve CBO yayın listesi
üzerinden teyit edildi.)

---

### A6. "Planlanan 1.367 milyar dolarlık ihracın %0,15'i" — kaynaksız ve tutarsız (§6.3a)

**İddia:** "Bir bağımsız analiz, geri alımın iki çeyrekte planlanan **1.367 milyar
dolarlık ihracın** yalnızca **%0,15'ine** denk geldiğini hesapladı."

**Üç ayrı sorun:**
1. **Kaynaksız.** "Bir bağımsız analiz" — kurum, yazar, tarih yok. Yazının kendi
   kuralını (her iddia kaynağa dayanır) ihlal eden tek yer.
2. **Payda yanlış etiketlenmiş.** 1.367 = 739 + 628, yani Temmuz–Eylül ve Ekim–Aralık
   çeyreklerinin **özel elde tutulan net pazarlanabilir borçlanma** tahmini
   (Hazine sb0584, 28.07.2026). Bu "planlanan ihraç" değil, net borçlanma.
   Brüt ihraç aynı iki çeyrekte kupon tarafında 1.088 + 1.109 = 2.197 milyar dolar,
   bono tarafında ayrıca ~13 trilyon dolar (ODM s.18 ve s.65).
3. **Pay tutmuyor.** 1.367'nin %0,15'i = **2,05 milyar dolar** — tek bir operasyon.
   Yazının kendi sayılarıyla oran: 28 / 1.367 = **%2,0**; ilave kapasiteyle
   14 / 1.367 = **%1,0**. %0,15 hiçbir anlamlı büyüklüğe karşılık gelmiyor.

**Öneri:** Ya çıkarılmalı ya da kaynağı bulunup payı/paydası açık yazılmalı.

---

### A7. §8.1 kendi girdisini yanlış etiketliyor

**İddia:** "10 yıllık **vade primi** ilk gün ~**6 baz puan** düştüyse, BIS
elastikiyetiyle GOP yerel getirilerinde beklenen etki ≈−7 baz puan."

**Neden yanlış:** 6 baz puan, 10 yıllık **getirinin** (CMT 4,71 → 4,65) hareketi.
10 yıllık **vade primi** aynı gün **9,9 baz puan** düştü — bunu yazının kendisi
§7.1'de doğru veriyor (ACM 0,8707 → 0,7721). BIS elastikiyeti (ABD vade primi
+100 bp → GOP yerel getirisi +115 bp) vade primine uygulanır, getiriye değil.

**Doğrusu:** 9,9 × 1,15 ≈ **−11,4 baz puan**, ≈−7 değil. Yazının vardığı sonuç
("ölçülemeyecek kadar küçük") değişmez ama sayı ve etiket düzeltilmeli.

**Kaynak:** NY Fed ACM Daily (ACMTP10): 2026-08-18 = 0,870722 · 2026-08-19 = 0,772103.

---

## B. ZAYIF / KIRILGAN NOKTALAR

### B1. §7.1'in "yerel arz kanıtı" 2 baz puanlık bir CMT yuvarlamasına dayanıyor

Yazının en güçlü iddialarından biri: "20 yıllığın 30 yıllıktan fazla hareket etmesi,
etkinin ... **yerel arz** etkisi olduğunun kanıtıdır."

Bu, CMT'de 20Y −11 bp / 30Y −9 bp farkından geliyor. İki uyarı:
- 18.08.2026 CMT'de 20Y ve 30Y **tam olarak eşit** (ikisi de 5,28) — par eğrisinde
  olağandışı bir düzlük. Baz nokta buradan alınınca 20Y hareketi mekanik olarak şişiyor.
- Piyasa getirileriyle çalışan kaynaklar aynı günü farklı raporluyor: Bloomberg
  aktarımı 20 yıllık için −9 bp / 5,18, 30 yıllık için −9…−10 bp veriyor. Yani
  "20Y > 30Y" bulgusu veri kaynağına duyarlı.

Öneri: bulgu korunabilir ama "CMT par eğrisinde" kaydıyla ve 2 bp'nin gürültü
sınırında olduğu notuyla. "Kanıtıdır" yerine "ile tutarlıdır".

### B2. TD Securities / Goldberg — bir alıntı doğrulandı, ikisi doğrulanamadı

- ✅ "sözlü müdahalenin eşdeğeri": doğru. AP (20.08.2026): "effectively the equivalent
  of verbal intervention from the U.S. Treasury"; devamı "Treasury firing a warning
  shot across the market's bow rather than doing something just yet". Goldberg ayrıca
  "this is not QE ... their own little version of 'Operation Twist'" demiş.
- ❓ "Bu, Hazine'nin uzun ucu desteklemek için atabileceği muhtemel birçok adımın ilki":
  hiçbir kaynakta bulunamadı.
- ❗ §6.4: "TD Securities (Goldberg): 'Daha kalıcı bir önlem, uzun uç **ihale
  büyüklüklerini düşürmek** olurdu.'" — bulunamadı ve **muhtemelen yanlış kişiye
  atfedilmiş**. Uzun uç ihale büyüklüklerinin kısılması beklentisini Bloomberg
  (20.08.2026, Ruth Carson) açıkça **JPMorgan**'a atfediyor: "The move raises the
  chances Treasury could cut long-end auction sizes if yields keep climbing."
  Goldberg'in kayıtlı sözü ise ters yönde: "It's just a few billion ... won't change
  their auction size reduction plans materially" (Bloomberg, 19.08.2026, Alexandra Harris).

**Etki:** §6.4'ün tüm kurgusu ("TD ihale küçültmesi bekliyor ↔ TBAC/satıcılar artış
bekliyor; ikisi aynı anda doğru olamaz") bu atıf üzerine kurulu. Atıf düşerse başlık
yeniden yazılmalı — karşıtlık JPMorgan ile TBAC arasında kurulabilir, ki JPMorgan
zaten aynı notta "FY2027–28'de 3,5 trilyon dolardan fazla finansman açığı" görüp
"daha az değil daha çok uzun vadeli arz gerekecek" diyor.

### B3. Han, Longstaff & Merrill'in 6,20 sentlik yayılımı doğrulanamadı (§5.1)

4,38 sent ✅ doğru (JF 62(6), Aralık 2007 özeti: "an average of only 4.38 cents per
$100 notional amount more than the prevailing market ask price"). Ama özet karşılaştırmayı
oran olarak veriyor: maliyet "**about two-thirds** the size of the usual bid-ask spread"
— bu 6,57 sent ima eder, 6,20 değil. 6,20 özetin içinde yok; tam metinden geliyorsa
sayfa numarasıyla verilmeli, yoksa "yayılımın yaklaşık üçte ikisi" biçiminde yazılmalı.

### B4. Connolly & Struby'nin işareti: yayınlanmış özet yazının tercih ettiği okumaya karşı

Yayınlanmış JBF özeti iki yerde de açıkça "yield" diyor: "contributed an average of
**95 basis points to the yields** of bonds bought back and bonds of similar maturity"
ve "each $10 billion of purchases corresponded with an average **yield increase** of
7,8 basis points". Yazı bunu "iktisadi olarak doğru okuma fiyat getirisidir" diyerek
çeviriyor. Uyarı dürüstçe konmuş ama çerçeve, kaynağın desteklemediği yöne eğik.
En temiz çözüm: özetin lafzını aktar, yorumu ayrı cümlede ver.

### B5. H.4.1 parantezi toplamıyor (§3.1)

534.115 + 3.621.850 + 276.076 = **4.432.041**, yazının verdiği toplam ise 4.538.703.
Fark **106.661** = H.4.1'in ayrı satırı olan "Inflation compensation". Dört sayının
dördü de doğru (Fed H.4.1, 20.08.2026); eksik olan beşinci kalem. Parantezde
"+ enflasyon telafisi 106.661" eklenmeli.

### B6. "Ocak 2026'dan bu yana SOMA ~250 milyar dolar bono aldı (~160'ı RMP)" (§3.1)

SOMA bono **stoku** 07.01.2026'da 241,8 milyar dolar, 19.08.2026'da 537,8 milyar dolar
— stok değişimi **+296,0 milyar dolar**. Alım ≠ stok değişimi (bonolar itfa oluyor),
dolayısıyla ~250 rakamı yanlış olmayabilir; ama hangi seriden geldiği belirtilmemiş ve
~160 milyar dolarlık RMP ayrıştırması için hiçbir kaynak verilmemiş.
Doğrulanabilir ve doğrulanmış olan: 20.08.2025 → 19.08.2026 bono stoku
195,5 → 537,8 milyar dolar (+342,3; +%175,1). Bu ikisi yeterli; ara rakam ya
kaynaklandırılmalı ya çıkarılmalı.

### B7. §10/7 kendi kendine yarattığı bir veri boşluğu

"18–21 Ağustos penceresinde ABD başabaş enflasyon oranlarının **birincil kaynaktan**
hareketi ... terminal verisi gerektiriyor."

Gerekmiyor. Yazı §4.1'de başabaşı zaten "nominal ve reel par CMT eğrilerinin farkı"
olarak hesaplıyor ve iki CSV de kamuya açık. 30 yıllık başabaş:
17.08 **2,25** · 18.08 **2,25** · 19.08 **2,25** · 20.08 **2,28** · 21.08 **2,27**.
10 yıllık için de aynı yöntemle hesaplanabilir. Yani "iyi ralli mi kötü ralli mi"
testinin ayırt edici verisi elde var: **duyuru günü 30 yıllık başabaş hiç oynamadı
(2,25 → 2,25)**, ertesi iki günde +2/+3 bp yükseldi. Bu, §7.4'ün mali baskınlık
okumasını zayıf ama yönü doğru biçimde destekleyen gerçek bir bulgu — kullanılmalı.

### B8. Morgan Stanley'nin "+100 bp 7s30s hedefi" tek kaynaklı kaldı (§6.2)

Doğrulanan: 20.08.2026 tarihli Global Macro Strategy raporunda "sinyal geri alımın
kendisinden önemli", eğri dikleşme ve dolar zayıflığı tezinin korunduğu.
Doğrulanamayan: 7 yıl–30 yıl için **+100 bp hedef**. Yazının kendi uyarısı yerinde.
Not: "rapor tarihinde ~+71" çıpası doğru — CMT 19.08.2026'da 7s30s = 5,19 − 4,48 = 71 bp.

---

## C. DOĞRULANANLAR (hata bulunamadı)

Aşağıdakiler birincil kaynaktan birebir teyit edildi.

**Duyuru (sb0607, 19.08.2026)** — tam metin çekildi. "increasing, by at least double,
the size of liquidity support buyback operations for longer-dated nominal coupon
securities (the 10-year to 20-year sector and the 20-year to 30-year sector).
The current maximum size of $2 billion per operation will be at least $4 billion per
operation. This change is effective September 9, 2026 and will be in effect for the
remainder of this refunding quarter (through November 4, 2026)." Gerekçe cümlesi
("consistent strong sponsorship ... significant volume of high-quality offers") ve
"An updated tentative Treasury buyback schedule will be released at a later date"
de aynen var. **Yazının §1'i kelime kelime doğru.**

**Takvim okuması (§1)** — Tentative-Buyback-ScheduleQ32026.pdf (05.08.2026):
- 9 Eylül gerçekten bir **nakit yönetimi** günü (1Mo–2Y, 12,5 milyar dolar). ✓
- Değişiklikten etkilenen ilk operasyon **10 Eylül, 10–20 yıl**. ✓
- 9 Eylül – 4 Kasım arası tam **7** uzun uç LS operasyonu, yazının verdiği tarihlerle
  birebir: 10–20 yıl 10 Eyl / 1 Eki / 15 Eki / 4 Kas; 20–30 yıl 24 Eyl / 8 Eki / 27 Eki. ✓
- Çeyreklik LS azamileri toplamı **tam 38,0 milyar dolar**, nakit yönetimi **tam
  25,0 milyar dolar** — sb0590'daki "up to $38 billion" ve "up to $25 billion" ile
  birebir. Yazının kendi doğrulama testi geçiyor. ✓
- 14 → 28 milyar dolar ve 38 → ~52 milyar dolar (+%36,8) aritmetiği doğru. ✓

**231 milyar dolar 10 yıl+ brüt kupon ihracı (§1)** — iki bağımsız yoldan doğrulandı:
sb0590 ihale büyüklükleri (10Y 42+39+39 = 120; 20Y 16+13+13 = 42; 30Y 25+22+22 = 69)
ve ODM sunumu s.18 (Temmuz–Eylül 2026 gross: 10Y 120, 20Y 42, 30Y 69). ✓
%6,1 ve %12,1 oranları doğru. ✓

**Finansman tablosu (§3.2)** — ODM sunumu s.18'den birebir:
FY26 Ç4: 739 / 375 / 45 / 409. FY27 Ç1: 628 / 361 / 50 / 317. ✓
sb0584'te 739 ve 628 doğrulandı; ayrıca sb0584 dipnotu yazının alıntıladığı cümleyi
aynen içeriyor: "buybacks are not expected to significantly affect privately-held net
marketable borrowing as new issuance replaces securities that are bought back". ✓

**CUSIP limit formülü ve örnek (§2.3)** — ODM Nisan 2024 supplemental s.5:
E = MAX{A−(B+C+D),0}; F = A − (10/7)B; G = MIN{E,F}; H = FLOOR{G, $1MM};
I = IF H ≥ $10MM THEN H ELSE $0. 912810QA9: A = 25.909, B = 18.072, C = 101,
D = 10.000, E = 0, F = 92, limit **0**. ✓ Dışlama kuralları listesi de s.6 ile birebir. ✓

**18 Ağustos operasyonu (§2.4)** — Fiscal Data:
36 uygun CUSIP ✓ · teklif 19,868 milyar dolar ✓ · teklif/azami 9,93× ✓ ·
kabul 2,000 milyar dolar, %100 ✓ · 3 CUSIP ✓ ·
912810SC3 %3,125 05/2048, 1.000 mn, 71,469 ✓ ·
912810SU3 %1,875 02/2051, 175 mn, 52,375 ✓ ·
912810SX7 %2,375 05/2051, 825 mn, 59,070 ✓ ·
ağırlıklı ortalama fiyat 64,684 ✓ · temiz nakit 1,2937 milyar dolar ✓ ·
takas 19.08.2026 ✓. (Tek hata vade aralığı — A4.)

**Teklif/azami istatistikleri (§2.4)** — 20–30 yıl 11 op: 9,93× – 18,24×, ortalama
**13,57×** ✓. 10–20 yıl 11 op: 3,70× – 18,02×, ortalama **10,08×** ✓.
(Yazının "18,2×" ve "18,0×" üst sınırları doğru.)

**24 Temmuz 2024, 7–10 yıl, sıfır alım (§2.4)** — 2 milyar dolar tavan,
3,706 milyar dolar teklif, **0,00 kabul**, 10 uygun CUSIP. Programın tarihindeki
tek sıfır-kabul operasyonu. ✓

**Program büyüklüğü (§3.4)** — 2024'ten bu yana toplam kabul: likidite desteği
213,4 + nakit yönetimi 236,9 = **450,3 milyar dolar** (+ 0,6 milyar dolar küçük
değerli test operasyonları). Yazının "450,4 milyar dolar / 27 ay" rakamı doğru. ✓

**Olay günü eğrisi (§7.1)** — Treasury CMT, 18.08 → 19.08.2026:
2Y 4,19→4,19 (0) ✓ · 3Y 4,26→4,25 (−1) ✓ · 5Y 4,37→4,35 (−2) ✓ · 7Y 4,53→4,48 (−5) ✓ ·
10Y 4,71→4,65 (−6) ✓ · 20Y 5,28→5,17 (−11) ✓ · 30Y 5,28→5,19 (−9) ✓.
21.08: 2Y 4,24 · 5Y 4,43 · 10Y **4,74** · 20Y 5,25 · 30Y 5,27 ✓.
§7.2'deki beş eğim satırının **on beş hücresi de** bu verilerden birebir çıkıyor. ✓

**19 yılın zirvesi (§4.1)** — 30Y CMT 17.08.2026 = **5,31**. 2007–2026 arasındaki
tüm günlük gözlemler tarandı: 5,31 ve üzerini gören tek gün **12.06.2007 = 5,35**.
Yazının iddiası tam olarak doğru. ✓
Şubat dibi 27.02.2026 = 4,64 (2026'nın en düşüğü) → +67 bp ✓.
Temmuz: 30.06 4,91 → 31.07 5,27 = +36 bp ✓.
30 yıllık reel getiri 17.08.2026 = **3,06** ✓.

**ACM vade primi** — NY Fed ACM Excel (son gözlem 20.08.2026):
Aylık: 30.06 0,512276 → 31.07 0,837552 (+32,5 bp); risk-nötr 3,964858 → 3,985446
(+2,1 bp) ✓ — "Temmuz satışının ~%94'ü vade primi" doğru.
Günlük: 17.08 **0,894756** (2026 zirvesi ✓) · 18.08 0,870722 · 19.08 0,772103
(−9,9 bp ✓); risk-nötr 3,908013 → 3,938556 (+3,1 bp ✓).

**31 Ekim 2001 (§5.2)** — Treasury CMT 2001, üç satır da birebir:
30.10: 10y 4,44 / 20y 5,21 / 30y 5,22 (20s30s +1) ✓
31.10: 10y 4,30 / 20y 5,05 / 30y 4,89 (20s30s −16) ✓
01.11: 10y 4,24 / 20y 5,00 / 30y 4,79 (20s30s −21) ✓
30 yıllık tek günde −33, iki günde −43, 10 yıllık aynı gün −14 ✓.
19.11.2001 30y = **5,22** (duyuru öncesi seviyeye dönüş) ✓ ·
10.12.2001 30y = **5,58** = +36 bp ✓.
20s30s Aralık 2001 en yassı **−32** (24 ve 26 Aralık) ✓ — ama ayın tipik değeri
−26…−30; "Aralık'ta −32" ayın uç değeri, ortalaması değil (küçük seçicilik).
Şubat 2002 −22 ✓ (aralık −21…−25).

**Ocak–Şubat 2000 (§5.1)** — Treasury CMT 2000:
18.01.2000: 2y 6,47 / 5y 6,65 / 10y 6,75 / 30y 6,75 (10s30s 0) ✓
03.02.2000: 2y 6,56 / 5y 6,56 / 10y 6,49 / 30y 6,17 (10s30s −32) ✓
30 yıllık −58 bp ✓ · 5 yıllık −9 bp ✓ · 2 yıllık **+9 bp** ✓ ·
zirve terslik 08.02.2000 = **−37 bp** ✓ (2000'in en ters günü).

**Borç ve bütçe (§4.2)** — Debt to the Penny: 17.08 39,9867 → **18.08 40,0474
trilyon dolar** (40 trilyonu ilk aşan gün, duyurudan bir gün önce ✓);
20.08 halkın elindeki borç **32,279 trilyon dolar** ✓.
MTS (31.07.2026, FY26 ilk 10 ay): açık **1.798,8 milyar dolar** ✓;
toplam harcama 6.284,2 milyar dolar → net faiz 962,9 / 6.284,2 = **%15,3** ✓.

**Bono payı (§3.2)** — MSPD 31.07.2026: bonolar 6.988,9 / toplam pazarlanabilir
31.455,1 = **%22,2** ✓. (ODM sunumu s.23 aynı tarihte "T-bills share ... 22.2%"
diyor — birebir.)

**Fed bilançosu (§3.1)** — H.4.1, 20.08.2026: doğrudan tutulanlar 6.471.814 ✓ ·
ABD Hazine kâğıdı 4.538.703 ✓ · bonolar 534.115 ✓ · nominal kupon 3.621.850 ✓ ·
enflasyona endeksli 276.076 ✓ · rezerv bakiyeleri 2.935.287 ✓. (Bkz. B5.)

**SOMA (§3.1)** — markets.newyorkfed.org SOMA API:
20.08.2025 bono 195,493 milyar dolar → 19.08.2026 bono **537,752 milyar dolar**;
+342,3 milyar, **+%175,1** ✓.

**TIC (§4.4)** — Tablo 5, Haziran 2026 verisi:
Yabancı resmî 2026-02 **4.011,0** → 2026-06 **3.778,1** = −232,9 (−%5,81) ✓
Japonya 1.239,3 → 1.116,7 = −122,6 ✓
Toplam yabancı 2025-06 9.093,6 → 2026-06 9.299,0 = +%2,26 ✓ ("yalnız %2,3 arttı")

**OFR (§4.4)** — OFR Blog, 19.08.2026 (duyuruyla aynı gün ✓): hedge fon nakit
Hazine pozisyonu 2025 sonunda **2 trilyon dolar**, beş yıl öncesinin neredeyse üç katı;
pazarlanabilir borç aynı dönemde %29 artışla 28,9 trilyon dolar; hedge fon payı
**rekor %7** ✓. (1,4 trilyon dolarlık kısa vadeli işlem pozisyonu ayrıca teyit edilmedi.)

**Likidite verileri (§7.3)** — Liberty Street Economics, "Liquidity Fades as
Treasuries Age" (30.06.2026), Chaboud–Correia Golay–Fleming–Huh–Keane–Shachar:
30 trilyon dolar üzeri stok, **%4'ünden azı** on-the-run, günlük hacmin **%65'i** ✓ ·
off-the-run müşteri işlemlerinin **%18'i** aynı kâğıtta 15 dakika içinde eşleşiyor ✓ ·
2 yıl etkin yayılım 0,66 / 1,22 / 2,23 bp ✓ · Mart 2020: 1,38 / 4,23 / 7,45 bp ✓ ·
CTD etkisi 5 yılda +1,31, 10 yılda +0,75, 2 yılda +0,51 milyar dolar ✓.
**Altısı da birebir.** (Küçük not: "%82'de aracı envantere almak zorunda" yazının
çıkarımı; kaynak yalnız %18'in eşleştiğini söylüyor.)

**Mart 2020 çıpası (§5.4)** — Garbade & Keane, LSE 20.08.2020: "Cumulative purchases
between March 13 and July 31 amounted to **$1.77 trillion** of Treasuries"; bazı
günlerde 100 milyar doların üzerinde ✓.

**Han, Longstaff & Merrill (§5.1)** — JF 62(6), Aralık 2007; 4,38 sent ✓;
2000–02'de 67,5 milyar dolar illikit borç ✓. (Bkz. B3.)

**Connolly & Struby (§5.1)** — JBF cilt 168 (2024), 107286; 95 bp ve 10 milyar dolar
başına 7,8 bp ✓ (işaret için B4).

### Alıntı ve atıf denetimi — hepsi sahibine ait

| Kişi/kurum | Yazıdaki iddia | Durum |
|---|---|---|
| Bessent | "İhraç başına 4 milyar dolardan fazla olabilir"; "Koşulların ne olduğunu göreceğiz"; 30 yıllığın likiditesi "çok zayıf" | ✅ CNBC 20.08.2026, birebir |
| Bessent | "Bunun bir kısmı sinyal vermek… getirilerin temel dinamikleri yansıtmadığına inandığımızı göstermek" | ✅ Reuters/CNBC 20.08.2026 |
| Barclays | ~16 milyar dolar/çeyrek, ~64 milyar dolar/yıl, ~%15 | ✅ Bloomberg 19.08.2026 (Ye Xie) |
| Robeco (Hoogeveen & Scholten) | ~66 milyar dolar/yıl, ~%15 brüt 20–30 yıl arzı | ✅ robeco.com, 21.08.2026 |
| Wells Fargo (Manolatos) | 32 milyar dolar/çeyrek; 5 Kasım'a kadar +12; sonra +16/çeyrek | ✅ Bloomberg 19.08.2026 (Alexandra Harris), birebir |
| JPMorgan (Jay Barry ve ekibi) | Kredibilite eksikliği, vade primini yukarı iter | ✅ Bloomberg 20.08.2026: "strategists including **Jay Barry** wrote" |
| JPMorgan (Maia Crook) | "regular and predictable"tan sapma, risk primi | ✅ gerçek kişi, JPM kıdemli araştırma analisti |
| Jefferies (Thomas Simons) | "regular and predictable" doktrininden sapma, kredibilite | ✅ CNBC 20.08.2026, birebir; ayrıca Bloomberg |
| Jefferies | 32 trilyon dolarlık piyasada çok küçük | ✅ |
| Evercore ISI (Guha & Casiraghi) | "çok küçük ölçekli bir Operation Twist", geri tepebilir | ✅ Bloomberg 19.08.2026, birebir |
| Deutsche Bank (Saravelos) | "Operation Twist burada"; "yumuşak mali baskı" | ✅ Bloomberg 19.08.2026: "Operation Twist is here"; CNBC: "soft-form" financial repression |
| Citi | 20 yıllıkta AL | ✅ Bloomberg 20.08.2026 |
| BofA (Mark Cabana) | "Yüksek borçlanma maliyetlerinin başlıca nedeni ... Fed'in enflasyonu nasıl kontrol edeceğine dair belirsizlik" | ✅ AP 20.08.2026, birebir |
| JPMorgan (Michael Feroli) | "Fed'in kısa vadeli faizleri kontrol etme yeteneği üzerinde herhangi bir etki görmüyorum" | ✅ Reuters 20.08.2026, birebir |
| El-Erian | "hem mutlak olarak hem net ihraca oranla küçük ... YCC'nin daha geniş devreye alınması" | ✅ kendi X/Substack notu, 19–20.08.2026 |
| Rebecca Patterson (CFR) | "özden çok sinyal" | ✅ CFR, 20.08.2026 12:30 |
| TD (Goldberg) | üç alıntıdan biri | ⚠️ bkz. B2 |
| Morgan Stanley | sinyal > büyüklük; dikleşme tezi korunuyor | ✅ (20.08.2026 Global Macro Strategy) |
| Morgan Stanley | 7s30s hedef +100 bp | ⚠️ bkz. B8 |

**Şirket tahvili arzı (§4.5)** — Ağustos IG arzı 17.08 itibarıyla **145,2 milyar dolar**,
2020'nin Ağustos rekoru **136 milyar dolar** ✓ (Bloomberg 17.08.2026). Hyperscaler
yılbaşından bu yana ~**225 milyar dolar** ✓ — yazının verdiği 132–225 aralığının üst ucu.
Yazının "kaynaklar birbirini tutmuyor, tek rakam vermek dürüst olmaz" yaklaşımı yerinde.

**"Kayda değer sessizlik" (§6.3)** — Goldman Sachs, PIMCO, BlackRock, Vanguard için
bu denetimde de isimli, doğrudan bir değerlendirme bulunamadı. ✅ İddia ayakta.

---

## D. DOĞRULANAMAYANLAR (hata değil — kapsam dışı)

- **Türkiye tarafının tamamı** (§8.2–8.4): TL sıfır kuponlu eğri, eurobond getirileri,
  CDS, yabancı DİBS akımı. Kaynak TCMB EVDS ve bir aracı kurum bülteni; EVDS anahtarı
  olmadan bağımsız doğrulanamadı. **Ancak iç tutarlılık testleri geçiyor:**
  - Spread aritmetiği: 5,91−4,20 = 171 ✓ · 7,04−4,63 = 241 ✓ · 7,77−5,20 = 257 ✓ ·
    257−171 = 86 bp dikleşme ✓
  - Kullanılan ABD ölçütleri (3Y 4,20 / 10Y 4,63 / 20Y 5,20) **tam olarak
    13.08.2026 CMT değerleri** — yazının "13–14 Ağustos kesiti" ifadesiyle tutarlı ✓
  - Beta çıpası: 30Y CMT 13.07.2026 5,10 → 13.08.2026 5,21 = **+11 bp** ✓ (yazının
    "aynı ayda ABD 30 yıllık +11 bp" ifadesi doğrulandı)
  - Küçük tutarsızlık: beta 30 yıllığa göre ölçülüyor ama spread tablosunda 2047
    için ölçüt 20 yıllık. İkisi de açıklanmış; yine de not düşülmeli.
- **MOVE 73,18** (§7.5) — yazı zaten "ikincil, güven düzeyi orta" diyor.
- **DXY 98,80 / haftalık −%0,9; Brent 94,39 (+%6,6)** — doğrulanamadı.
  **Altın 4.680,60 ✅ doğrulandı** (piyasa kotasyonu).
- **SOFR swap spread'leri** (§7.5) — yazının bilinçli boşluğu; ayakta.
- **IMF WP 2025/088 katsayıları** (§7.3) — yazının bilinçli boşluğu; ayakta.
- **BoE 2022 sayıları** (§5.4: 130 bp / 5 milyar £ gün / 13 iş günü / 65 milyar £
  kapasite / 19,3 = 12,1 + 7,2 milyar £ fiilî / 29.11.2022–12.01.2023, 12 operasyon)
  — bu turda yeniden doğrulanmadı; BoE Quarterly Bulletin 2023 ile örtüşür görünüyor.
- **Operation Twist 1961 (~15 bp) ve 2011 MEP (400 + 267 = 667 milyar dolar,
  ex-ante 15–20 bp)** — bu turda yeniden doğrulanmadı; standart ve iyi belgelenmiş.
- **BIS WP 1081 elastikiyetleri** (+115 bp / −%6 / −%5 / %8) — bu turda doğrulanmadı.
- **Miran & Roubini (Temmuz 2024): 800 milyar dolar ikame, ~1 puanlık teşvik** —
  bu turda doğrulanmadı.
- **TBAC nominal–piyasa değeri tablosu** (§3.4: 94,2 / 81,9 ve 112,7 / 110,9) —
  Q3 2026 ODM sunumunda bulunamadı; muhtemelen TBAC 29.07.2025 sunumunda.
  Sayfa numarasıyla atıf verilmeli.
- **Perli konuşması (§7.5)** — 09.07.2026, Mayıs 2026 ortasında repo faizlerinin
  tavanın 15 bp altına inmesi; bu turda doğrulanmadı.
- **31 CFR 375 nihai kural detayları** (§2.2: oransal tahsis, FedTrade bilgi kısıtı,
  35 milyar dolarlık karşı taraf eşiği) — bu turda doğrulanmadı. Operasyon saati
  (13:40–14:00 ET) ve asgari 1 milyon dolar lot ✓ takvimden ve ODM'den teyitli.

---

## E. ÖNCELİKLİ DÜZELTME LİSTESİ

1. §2.4 ve §9: "doluluk istisnasız %100" → "22 operasyonun 21'inde %100; istisna
   19.03.2026, 20–30 yıl, %10,2". §9 eşiği yeniden kurgula.
2. §5.1: 16/26 → **20/22** operasyon.
3. §4.1 ve §9: başabaş bandı 2,18–2,27 → **2,15–2,34** (2026 YTD, aynı yöntem).
4. §2.4: vade aralığını düzelt (takvim penceresi 19.08.2046–18.08.2056; fiilî
   uygun CUSIP aralığı 15.02.2047–15.02.2056).
5. §4.2 ve §10/9: CBO atfını **yayın 62704**'e çevir, "erişilemedi" notunu kaldır.
6. §6.3a: "%0,15 / 1.367 milyar dolar" cümlesini kaynaklandır ya da çıkar.
7. §8.1: "vade primi ~6 bp" → **9,9 bp**; sonuç ≈−11 bp.
8. §6.4: TD/Goldberg atfını doğrula; doğrulanmazsa karşıtlığı **JPMorgan** ↔ TBAC
   ekseninde yeniden kur.
9. §3.1: H.4.1 parantezine enflasyon telafisi (106.661) ekle.
10. §10/7: başabaş boşluğunu kaldır, hesaplanmış seriyi (17–21.08: 2,25 / 2,25 /
    2,25 / 2,28 / 2,27) yazıya koy — duyuru günü başabaşın **hiç oynamaması**
    §7.4 için gerçek bir bulgu.
11. §7.1: "kanıtıdır" → "ile tutarlıdır"; 20Y−30Y farkının 2 bp olduğunu ve CMT par
    eğrisine özgü olabileceğini not düş.
12. §5.1: 6,20 sentlik yayılımı ya sayfa numarasıyla ver ya "yayılımın yaklaşık
    üçte ikisi" biçiminde yaz.
