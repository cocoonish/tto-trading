# ABD Hazinesi Tahvil Geri Alımları — MEKANİZMA

Araştırma notu · derleme tarihi 23–24 Ağustos 2026
Kapsam: geri alımın hukuki temeli, ters ihale mekaniği, iki program türü, finansman
aritmetiği, QE/Twist karşılaştırması, off-the-run likidite primi, 2024–2026 operasyon
tarihçesi.

Kaynak etiketleri: **[B]** birincil (Hazine/Fed/Federal Register/TBAC), **[İ]** ikincil.
Bu notta işaretlenmemiş her şey **[B]**'dir. Kendi hesaplarım **[HESAP]** ile işaretli.

---

## 0. TETİKLEYİCİ OLAYIN BİRİNCİL KAYNAK METNİ

**Bulgu 0.1 — 19 Ağustos 2026 duyurusunun tam içeriği**

Başlık: "Treasury Announces Increased Sizes of Nominal Long-End Liquidity Support
Buybacks Beginning September 9".

Gövde metninin özeti (kendi cümlemle): Hazine, uzun vadeli nominal kuponlu menkul
kıymetlerde (10 yıl–20 yıl ve 20 yıl–30 yıl sektörleri) likidite desteği geri alım
operasyonlarının büyüklüğünü "en az iki katına" çıkarıyor. Operasyon başına mevcut azami
tutar **2 milyar dolar**dan **en az 4 milyar dolar**a çıkıyor. Değişiklik **9 Eylül 2026**
itibarıyla yürürlükte ve bu refinansman çeyreğinin kalanı boyunca (**4 Kasım 2026**'ya
kadar) geçerli. Gerekçe olarak, uzun vadeli sektörlerde piyasa katılımcılarından gelen
"tutarlı güçlü sponsorluk" ve Hazine'nin uzun vadeli geri alım operasyonlarında rutin
olarak aldığı "yüksek kaliteli tekliflerin önemli hacmi" gösterildi. Gelecekteki geri
alım büyüklükleri hakkında bilgi 4 Kasım 2026'daki üç aylık refinansmanda verilecek.
Güncellenmiş geçici geri alım takvimi "daha sonra" yayımlanacak.

- SAYI/TARİH: 2 mia $ → en az 4 mia $ / operasyon; yürürlük 09.09.2026; bitiş 04.11.2026;
  sektörler 10Y–20Y ve 20Y–30Y nominal kupon.
- Kaynak: U.S. Department of the Treasury, basın bülteni sb0607, 19.08.2026.
  https://home.treasury.gov/news/press-releases/sb0607

**Dikkat — yazarın kullanacağı nüans:** metin "en az 4 milyar dolar" diyor. Yani 4 mia $
bir tavan değil, yeni taban. Hazine üst sınırı serbest bırakmış durumda.

**Bulgu 0.2 — Değişiklikten önce açıklanmış çeyrek büyüklükleri**

5 Ağustos 2026 tarihli üç aylık refinansman bildirisinin "BUYBACKS" başlığı: Hazine,
Ağustos–Ekim 2026 çeyreğinde likidite desteği için kovalar genelinde **38 milyar dolara
kadar** off-the-run menkul kıymet, nakit yönetimi için 1 ay–2 yıl kovasında **25 milyar
dolara kadar** alım öngörüyor.

- Kaynak: Treasury, Quarterly Refunding Statement (Brian Smith), basın bülteni sb0590,
  05.08.2026. https://home.treasury.gov/news/press-releases/sb0590

---

## 1. GERİ ALIM NEDİR — HUKUKİ TEMEL VE TANIM

**Bulgu 1.1 — Yasal yetki: 31 U.S.C. 3111**

Geri alımın resmî adı "redemption operation" (itfa operasyonu). 31 U.S.C. §3111, Hazine
Bakanı'na vadesinden önce veya vadesinde tahvil, bono, borçlanma sertifikası, Hazine
bonosu veya tasarruf sertifikalarını **satın alma, itfa etme veya refinanse etme** yetkisi
veriyor. Kritik cümle — finansman kaynağı doğrudan kanunda tanımlı: Bakan bu alımlarda
**"bir yükümlülüğün satışından elde edilen parayı ve Hazine'nin genel fonundaki diğer
parayı"** kullanabilir.

Yani yasa metninin kendisi söylüyor: geri alımın parası ya **yeni borçlanmadan** ya da
**mevcut nakit bakiyesinden** gelir. Para basılmaz, yaratılmaz.

- Kaynak: 31 CFR 375.0, "Marketable Treasury Securities Redemption Operations", Final
  Rule, Federal Register 91 FR 15540, yayım 30.03.2026, yürürlük 30.03.2026.
  Belge no 2026-06070. Yetki dayanağı 31 U.S.C. 3111.
  https://www.federalregister.gov/documents/2026/03/30/2026-06070/marketable-treasury-securities-redemption-operations

**Bulgu 1.2 — Geri alınan kâğıt yok edilir (retire), portföye alınmaz**

Geri alım, bir CUSIP'in dolaşımdaki nominal (par) tutarını satın alınan miktar kadar,
tam olarak azaltan bir **itfa** olarak yapılandırılmıştır. Satın alınan kâğıtlar takas
anında **iptal edilir** (retired upon settlement). Hazine bunları elinde tutmaz, ödünç
vermez, repoya koymaz.

Bu, geri alımı Fed'in SOMA alımından ayıran birinci yapısal fark: Fed alırsa kâğıt
Fed'in bilançosunda VARLIK olarak durur ve karşılığında rezerv (yükümlülük) yaratılır;
Hazine alırsa kâğıt yok olur ve karşılığında başka bir Hazine kâğıdı ihraç edilir.

- Kaynak: Treasury Office of Debt Management (ODM), "Regular Treasury Buyback Program
  Details", Nisan 2024, s. 8.
  https://home.treasury.gov/system/files/221/TreasurySupplementalQ22024.pdf
- Kaynak: TreasuryDirect, "FAQs about Treasury Securities Buybacks" (erişim 23.08.2026).
  https://www.treasurydirect.gov/help-center/faqs/buyback-faqs/

---

## 2. TERS İHALE (REVERSE AUCTION) MEKANİĞİ — ADIM ADIM

**Bulgu 2.1 — Format: çoklu fiyat (multiple-price) ters ihale, FedTrade üzerinden**

Likidite desteği geri alımları, **New York Fed'in FedTrade** platformu üzerinden
yürütülen **çoklu fiyat** ters ihaleleridir. "Çoklu fiyat" = kabul edilen her teklif,
teklif sahibinin kendi verdiği fiyattan takas edilir (tek fiyat/Hollanda usulü DEĞİL).
Hazine'nin normal ihaleleri tek fiyat usulüyken geri alımların çoklu fiyat olması
tarihsel bir tercihtir: 2000'de NY Fed'in mevcut açık piyasa işlemleri elektronik
sisteminden hemen yararlanabilmek için seçilmiştir.

- Kaynak: TreasuryDirect Buyback FAQs; ODM Nisan 2024 s. 2.
- Tarihsel gerekçe: Federal Register, "Marketable Treasury Securities Redemption
  Operations; Final Rule", 19.01.2000, s. 3115 — Garbade & Rutherford (2007) içinde
  aktarılmış, dipnot 19.

**Bulgu 2.2 — Kim teklif verebilir (2026 itibarıyla genişletildi)**

31 CFR 375.11(a) uyarınca "submitter" (doğrudan teklif veren) olabilmek için:
1. NY Fed tarafından **birincil satıcı (primary dealer)** olarak atanmış bir kurum olmak,
   VEYA
2. Hazine tarafından geri alım operasyonlarına **doğrudan katılması onaylanmış** bir
   kuruluş olmak.

Diğer herkes ancak bir submitter aracılığıyla teklif verdirebilir (375.11(b)).

Genişleme kronolojisi:
- Nisan 2024 (program başlangıcı): **yalnızca birincil satıcılar**. "Diğer piyasa
  katılımcıları bir birincil satıcı aracılığıyla erişebilir."
- **30 Temmuz 2025**: Hazine, ihale katılımına dayalı olarak sınırlı sayıda ek
  karşı tarafa doğrudan teklif verme yetkisi tanıma planını duyurdu (Temmuz 2025
  refinansman bildirisi, sb0212). Amaç: "geri alım sürecinde daha fazla rekabeti
  teşvik etmek ve likidite desteğine erişimi genişletmek."
- **19 Eylül 2025**: uygunluk kriterleri yayımlandı.
- Kriter: altı aylık gözlem döneminde **35 milyar doları aşan** toplam nominal kupon +
  TIPS ihale tahsisi (10 yıl eşdeğerine süre-ayarlı). Altı ayda bir gözden geçiriliyor.
  Eşik operasyonel kısıtlara göre belirlendi ve ileride değişebilir.
- İlk ek karşı taraf listesi, 2025'in ilk yarısında 35 mia $ üzeri tahsis almış,
  birincil satıcı OLMAYAN ihale katılımcılarından oluşuyor. Erişim yine FedTrade
  (veya halefi platform) üzerinden.
- **30 Mart 2026**: bu genişleme 31 CFR 375.11(a) değişikliğiyle yönetmeliğe işlendi.

- SAYI/TARİH: 35 mia $ eşik; 30.07.2025 duyuru; 19.09.2025 kriterler; 30.03.2026 nihai
  kural.
- Kaynak: Federal Register 91 FR 15540 (30.03.2026), giriş bölümü ve §375.11;
  TreasuryDirect Buyback FAQs; Treasury QRS sb0212 (Temmuz 2025).

**Bulgu 2.3 — Teklif formatı ve limitleri**

- Teklifler yalnızca **rekabetçi** olabilir (fiyat belirtmek zorunlu). Rekabetçi olmayan
  teklif yok. (31 CFR 375.13(a))
- Her teklif: menkul kıymet tanımı + nominal tutar + fiyat. (375.13(a))
- **Fiyat formatı: 100 dolar nominal başına fiyat.** (375.13(b), 30.03.2026'da
  netleştirildi.) Uygulamada 32'de bir ve 32'de birin sekizde biri kesirleriyle
  yazılıyor; FAQ'daki örnek gösterim `102-17 2`. 2026 sonuç dosyalarında ağırlıklı
  ortalama kabul fiyatı ondalık olarak yayımlanıyor (ör. 71.469).
- **Asgari teklif tutarı: 1 milyon dolar nominal**, artış katı da 1 milyon dolar.
  (Operasyon duyurusunda belirtilir; 2026 operasyonlarında `minOfferAmountAndMultiples =
  1.000.000`.)
- **Menkul kıymet başına azami teklif sayısı: 9.** (Operasyon duyurusunda belirtilir;
  375.13(c) 2026'da bu üst sınırı yönetmeliğe bağladı.) Teklif verilebilecek menkul
  kıymet sayısında sınır yok.

- Kaynak: 31 CFR 375.13 (91 FR 15540, 30.03.2026); TreasuryDirect Buyback FAQs;
  TreasuryDirect operasyon sonuç XML'i BBR_20260818174000.xml.

**Bulgu 2.4 — Operasyon zaman çizelgesi (tipik gün)**

| Aşama | Zaman | İçerik |
|---|---|---|
| Geçici çeyrek takvimi | Her üç aylık refinansmanda | Tarihler, tip, kova, azami tutar, vade aralığı, takas tarihi |
| **Ön duyuru** (Preliminary Announcement) | Operasyondan **1 iş günü önce, 11:00 ET** | Muhtemel uygun CUSIP listesi, geçici büyüklük/zamanlama, teslimat talimatları |
| **Nihai duyuru** (Final Announcement) | Operasyon günü **11:00 ET** | Nihai uygun CUSIP listesi. Ön duyuruyu geçersiz kılar. Bu andan sonra liste değişmez |
| **Operasyon penceresi** | **13:40–14:00 ET** (20 dakika) | FedTrade üzerinden teklif toplama; katılımcılara başlangıç/bitiş bildirimi |
| Değerlendirme + sonuçlar | Operasyon biter bitmez | Toplam teklif, toplam kabul, CUSIP bazında kabul ve ağırlıklı ortalama kabul fiyatı |
| **Takas** | Genellikle **T+1** | Nominal tutar × kabul fiyatı + birikmiş faiz |

Ön duyuru ile nihai duyuru arasında CUSIP listesi yalnızca piyasa koşullarının bir
dışlama kuralını tetiklemesi hâlinde değişir.

- SAYI/TARİH: 11:00 ET ön ve nihai duyuru; 13:40–14:00 ET operasyon; T+1 takas.
- Kaynak: ODM Nisan 2024, s. 4 ve s. 7; TreasuryDirect Buyback FAQs; Treasury,
  "Tentative Schedule of Treasury Buyback Operations — August 2026 Quarterly Refunding",
  yayım 05.08.2026, dipnot 1–2.
  https://home.treasury.gov/system/files/221/Tentative-Buyback-ScheduleQ32026.pdf

**Bulgu 2.5 — Teklifler nasıl değerlendirilir (fiyatlama kriteri)**

Teklifler iki ölçüte göre değerlendirilir:
1. **Operasyon kapanışındaki cari piyasa fiyatlarına yakınlık**, ve
2. **Göreli değer (relative value) ölçütleri**.

Hazine kendini "fiyata duyarlı alıcı" (price-sensitive buyer) olarak tanımlıyor. Fiilî
alım tutarı operasyon sırasında, tekliflerin kalitesine göre belirleniyor. Hazine
duyurulan azami tutardan **daha azını** alabilir; hiç almamaya da karar verebilir
(31 CFR 375.30(a)(1)-(2)). Hazine hangi teklifi neden kabul ettiğinin kriterlerini
kamuya açmıyor.

**Yeni (30.03.2026): pro-rata tahsis.** 31 CFR 375.24 eklendi — belirli bir menkul
kıymette **en yüksek kabul edilen fiyattaki teklifler oransal (prorated) olarak kabul
edilebilir**. (Normal ihaledeki "stop-out"ta oransal tahsis mantığının ters ihaledeki
karşılığı.)

**Yeni (30.03.2026): FedTrade bilgisinin kullanımı.** 375.14(b) — katılımcılar yalnızca
FedTrade'de görünen operasyon bilgisini, ancak (i) bilgi başka bir kaynaktan da
edinilebiliyorsa veya (ii) işlem yalnızca operasyondaki tekliflerinin kabul/reddinden
doğan **belirli, tanımlanabilir riskleri hedge etmek** (veya bu hedge'leri kapatmak)
amaçlıysa bir işleme dayanak yapabilir. Bu bilgiyi başkasına aktarmak da aynı istisna
dışında yasak.

- Kaynak: TreasuryDirect Buyback FAQs; ODM Nisan 2024 s. 8; 31 CFR 375.14, 375.24,
  375.30 (91 FR 15540, 30.03.2026).

**Bulgu 2.6 — Takas, ödeme tutarı ve temerrüt cezası**

- **"Settlement amount" = itfa edilen nominal tutar × kabul edilen fiyat + birikmiş
  faiz.** (31 CFR 375.2 tanımı.) Yani Hazine kirli fiyat öder.
- Takas genellikle operasyondan **bir iş günü sonra** (T+1). Hazine aynı gün takas
  hakkını saklı tutuyor.
- Teslim edilen kâğıtlar "her türlü rehin, yük, talep ve kısıtlamadan ari" olmalı
  (375.15).
- Zamanında teslim edilmezse: TMPG (Treasury Market Practices Group) fails charge
  metodolojisine göre ceza; ayrıca 375.31(b) uyarınca **öngörülen takas tutarının
  %1'ine kadar** tasfiye edilmiş zarar (liquidated damages) talep edilebilir; gelecekteki
  geri alımlardan ve 31 CFR 356 ihalelerinden men dâhil başka yaptırımlar da mümkün.
- NY Fed'in fiskal ajan rolü (375.3): teklifleri kabul ve inceleme, sonuçları hesaplama,
  itfa bildirimlerini yayınlama, takasta kâğıtları teslim alma, ödemeyi işleme.
- Teslimat hesabı 2026 operasyonlarında: `ABA 021089482 US TREAS BUYBACK/6000`.

- Kaynak: 31 CFR 375.2, 375.3, 375.15, 375.23, 375.31 (91 FR 15540); TreasuryDirect
  Buyback FAQs; BBR_20260818174000.xml.

**Bulgu 2.7 — Sonuçlarda ne açıklanır**

Operasyon bittikten sonra Hazine web sitesinde: toplam teklif edilen nominal tutar,
toplam kabul edilen nominal tutar ve **menkul kıymet bazında ağırlıklı ortalama kabul
fiyatı**. 30.03.2026 kuralı, sonuçların basın bülteni yerine web sitesi üzerinden
yayımlandığını ve bilginin genel olarak operasyon bazında verildiğini yönetmeliğe
işledi. Reddedilen teklifler için teyit gönderilmiyor (375.22(a), 2026'da eklendi).

Not: 2026 kuralı "privately held amount" terimini 375.2 ve 375.21'den çıkardı, çünkü
Hazine bu bilgiyi sonuçlarda yayımlamıyor.

- Kaynak: 31 CFR 375.21, 375.22 (91 FR 15540); ODM Ağustos 2023 s. 8.

---

## 3. UYGUNLUK: HANGİ TAHVİLLER, HANGİ VADELER

**Bulgu 3.1 — Dokuz vade kovası**

Hazine geri alımları **9 kova** üzerinden yürütür; bir operasyonda **yalnızca bir kova**
işlem görür.

| Ürün | Amaç | Vade sektörü |
|---|---|---|
| Nominal kupon | Nakit yönetimi **ve** likidite desteği | 1 ay – 2 yıl |
| Nominal kupon | Likidite desteği | 2Y – 3Y |
| Nominal kupon | Likidite desteği | 3Y – 5Y |
| Nominal kupon | Likidite desteği | 5Y – 7Y |
| Nominal kupon | Likidite desteği | 7Y – 10Y |
| Nominal kupon | Likidite desteği | 10Y – 20Y |
| Nominal kupon | Likidite desteği | 20Y – 30Y |
| TIPS | Likidite desteği | 1Y – 7.5Y → **Ağustos 2025'ten itibaren 1Y – 10Y** |
| TIPS | Likidite desteği | 7.5Y – 30Y → **Ağustos 2025'ten itibaren 10Y – 30Y** |

TIPS kovalarının sınırı Ağustos 2025'te değiştirildi (7,5 yıl kırılımı 10 yıla taşındı).

- Kaynak: ODM Nisan 2024 s. 3; ODM "Fiscal Year 2026 Q3 Report" (TBAC'a sunum),
  Temmuz 2026, s. 46 dipnot 3.
  https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ32026.pdf

**Bulgu 3.2 — Kapsam dışı ürünler**

Hazine **bono (bills), değişken faizli tahvil (FRN) ve STRIPS geri almayı planlamıyor.**
Yalnızca off-the-run nominal kuponlu kâğıtlar ve TIPS.

- Kaynak: TreasuryDirect Buyback FAQs; TBAC 1Ç2025 sunumu s. 5.

**Bulgu 3.3 — Dışlama kuralları (tam liste)**

Her iki operasyon türü için geçerli:
1. **On-the-run ve on-the-run'a yakın**: ilk kupon ödeme tarihini geçmemiş yeni ihraçlar.
2. **Kupon ödeme tarihine yakın kâğıtlar**: kupon ödemesi, takas tarihinden önceki iki
   iş günü içinde veya takas tarihinde olanlar.
3. **CTD ve CTD'ye yakın**: bir vadeli işlem sözleşmesi için makul olarak teslime en ucuz
   olma ihtimali olan kâğıtlar.
4. **Repo special'lar**: repo piyasasında belirgin şekilde special işlem gören veya
   benzer ihraçlara kıyasla olağanüstü talep gören kâğıtlar.
5. **Satın alma limiti**: hesaplanan limiti 10 milyon dolardan az olan kâğıtlar.
6. **İstisnai durumlar**: Hazine yüksek talep gören kâğıtları almayı reddedebilir.

Yalnızca **nakit yönetimi** için ek olarak:
7. **Bonoya göre pahalı (rich to bills)**: benzer vadeli Hazine bonolarından belirgin
   şekilde düşük getiriyle işlem gören kuponlu kâğıtlar.
8. **Vergi ödeme tarihlerine yakın vadeli**: üç aylık vergi tarihleri veya nisan vergi
   sezonu civarında vadesi dolan kuponlu kâğıtlar. (Aksi hâlde geri alım, nakit
   dengesizliğini hafifletmek yerine büyütürdü.)

TBAC'a göre bu çerçeve, Fed'in kalıcı açık piyasa işlemlerinde (POMO) kullandığı
çerçevenin rafine bir versiyonudur ve prim taşıyan ya da takas riski doğuran kâğıtları
dışlar. TIPS için ayrıca: takas tarihinden itibaren bir yıl içinde vadesi dolan TIPS
dışlanır.

- Kaynak: ODM Nisan 2024 s. 6; TBAC "Treasury Buyback Program Enhancements", 29.07.2025,
  s. 13; TBAC 1Ç2025 s. 5.
  https://home.treasury.gov/system/files/221/TBACCharge1Q32025.pdf
  https://home.treasury.gov/system/files/221/TBACCharge1Q12025.pdf

**Bulgu 3.4 — CUSIP başına satın alma limiti: TAM FORMÜL**

Bu, yazının teknik gücünü artıracak birinci sınıf materyal. Hazine, tek bir CUSIP'te
özel elde kalan arzı aşırı azaltmanın likiditeyi destekleyeceğine değil zedeleyeceğine
inandığı için iki kısıt uygular:

| Adım | Formül | Açıklama |
|---|---|---|
| A | Dolaşımdaki nominal (Par Outstanding) | |
| B | SOMA (Fed) elindeki tutar | |
| C | STRIPS'e ayrıştırılmış tutar | |
| D | Serbest dolaşım tabanı | **Nominal kupon: 10 mia $ · TIPS: 5 mia $** |
| E | `MAX{ A − (B + C + D) , 0 }` | Serbest dolaşım dolar limiti |
| F | `A − (10/7)·B` | SOMA payı limiti; öyle ki `B / (A − F) = %70` |
| G | `MIN{ E , F }` | İki limitin küçüğü |
| H | `FLOOR{ G , 1 mn $ }` | 1 milyon dolarlık lotlara yuvarlama |
| I | `EĞER H ≥ 10 mn $ İSE H, DEĞİLSE 0` | Nihai satın alma limiti |

İki kısıtın sözel hâli:
- Operasyon takas olduktan sonra **serbest dolaşım** (dolaşımdaki nominal eksi SOMA
  eksi STRIPS) nominal kuponlarda **10 milyar doların**, TIPS'te **5 milyar doların**
  üstünde kalmalı.
- Takas sonrası **SOMA'nın payı dolaşımdaki nominalin %70'ini aşmamalı**. (Geri alım
  dolaşımdaki nominali azalttığı için SOMA payı mekanik olarak yükselir — kısıt bunu
  dizginler.)
- Herhangi bir tek kâğıtta asgari alım **10 milyon dolar nominal**; altında kalan
  CUSIP tamamen dışlanır.

Hazine'nin 22.04.2024 tarihli dört örneği (mn $):

| | 912810FH6 (TIPS) | 912810QA9 | 912810QX9 | 9128282A7 |
|---|---|---|---|---|
| A Par outstanding | 19.497 | 25.909 | 41.995 | 65.349 |
| B SOMA | 9.598 | 18.072 | 26.598 | 10.765 |
| C STRIPS (31.03.2024) | 6 | 101 | 1.079 | 10 |
| D Taban | 5.000 | 10.000 | 10.000 | 10.000 |
| E | 4.893 | **0** | 4.318 | 44.574 |
| F | 5.786 | 92 | 3.998 | 49.970 |
| G = MIN(E,F) | 4.893 | 0 | 3.998 | 44.574 |
| I Nihai limit | **4.893** | **0** | **3.997** | **44.574** |

912810QA9 örneği öğretici: SOMA 25,9 mia $'lık ihracın 18,1 mia $'ını tutuyor; serbest
dolaşım zaten 10 mia $ tabanının altında, dolayısıyla limit sıfır — bu kâğıt geri alıma
hiç giremez.

- SAYI/TARİH: 10 mia $ / 5 mia $ serbest dolaşım tabanı; %70 SOMA tavanı; 10 mn $ asgari;
  1 mn $ lot.
- Kaynak: ODM "Regular Treasury Buyback Program Details", Nisan 2024, s. 5.

**Bulgu 3.5 — Kaldırılmış kısıt: 20 CUSIP tavanı**

Program Mayıs 2024'te başlarken Hazine, takas raporlama sistemindeki geçici operasyonel
kısıt nedeniyle her operasyonda en fazla **20 CUSIP** için teklif topluyordu. Bu tavan
**Ağustos 2024'te** kaldırıldı. Bugün tipik bir operasyonda uygun CUSIP sayısı 10 ile 61
arasında değişiyor (ör. 06.08.2026 1Ay–2Y operasyonunda 61 uygun kâğıt; 16.06.2026
7Y–10Y operasyonunda yalnızca 10).

- Kaynak: ODM Nisan 2024 s. 2 ve s. 8; ODM "Review of Treasury Buyback Results",
  29.10.2024, s. 7 ("Prior to August 2024, Treasury limited the buyback eligible
  population to at most 20 CUSIPs").
  https://home.treasury.gov/system/files/221/TreasurySupplementalQ42024.pdf
- CUSIP sayıları: Treasury Fiscal Data API, `buybacks_operations` veri seti, çekim
  24.08.2026. https://fiscaldata.treasury.gov/datasets/treasury-securities-buybacks/

---

## 4. İKİ PROGRAM TÜRÜ: LİKİDİTE DESTEĞİ vs NAKİT YÖNETİMİ

**Bulgu 4.1 — Amaç farkı (Hazine'nin kendi tanımları)**

| | **Likidite Desteği** | **Nakit Yönetimi** |
|---|---|---|
| Amaç | Piyasa katılımcılarına off-the-run kâğıtlarını satmak için **düzenli ve öngörülebilir bir fırsat** yaratarak piyasa likiditesini desteklemek | Hazine'nin **nakit bakiyesindeki ve bono ihracındaki oynaklığı azaltmak**, bono arzı kesintilerini asgariye indirmek, zaman içinde borçlanma maliyetini düşürmek |
| Vade | Nominal ve TIPS eğrisinin tamamı (7 nominal + 2 TIPS kovası) | Ağırlıklı olarak **1 ay – 2 yıl** nominal kupon; kısa vadeli TIPS de değerlendirilebilir |
| Sıklık | Genellikle haftada bir (bazen iki), her kova çeyrekte en az bir kez | **Mevsimsel**: büyük vergi ödeme tarihlerinin (15 Nisan, 15 Haziran, 15 Eylül, 15 Aralık) hemen çevresindeki haftalar |
| Kullanılmayan kapasite | **Devredilmez** | Sonraki operasyonlara **devredilebilir** |
| Tipik operasyon büyüklüğü (Ağu 2026) | 4 mia $ (kısa/orta nominal), 2 mia $ (10Y–20Y, 20Y–30Y), 750 mn $ (kısa TIPS), 500 mn $ (uzun TIPS) | 12,5 mia $ (Eylül 2026 planı) |
| Piyasa stresine müdahale | **Hayır.** Hazine "akut piyasa stresi epizotlarını hafifletmek için geri alım kullanmayı amaçlamıyor" | Hayır |

- Kaynak: TreasuryDirect Buyback FAQs; ODM Nisan 2024 s. 2; ODM Ağustos 2023 s. 3–4;
  TBAC 1Ç2025 s. 5 (devredilebilirlik kuralı); Treasury geçici takvim (05.08.2026).

**Bulgu 4.2 — "Akut stresle mücadele aracı değildir" — programın en önemli sınırı**

Hazine hem FAQ'da hem 1Ç2025 TBAC sunumunda açıkça yazıyor: geri alımlar düzenli ve
öngörülebilirdir ve **akut piyasa stresi epizotlarını hafifletmeye yönelik değildir.**
TBAC 3Ç2022 sunumu bu sınırın nedenini de veriyor: Fed alımlarından farklı olarak
Hazine programı kapsam olarak sınırlıdır ve piyasa işleyişini stres dönemlerinde
desteklemek üzere tasarlanmamıştır.

Yazar için: 19 Ağustos hamlesi bir "piyasa kurtarma" değil, kalibrasyon değişikliğidir.
Hazine gerekçe olarak stresi değil, "güçlü sponsorluk" ve "yüksek kaliteli tekliflerin
hacmini" gösterdi — yani aşırı talebi.

- Kaynak: TreasuryDirect Buyback FAQs; TBAC 1Ç2025 s. 3; TBAC 3Ç2022 "Revisiting
  Treasury Buybacks", s. 20; Treasury sb0607 (19.08.2026).

**Bulgu 4.3 — Nakit yönetimi geri alımının ekonomik farkı (Garbade & Rutherford)**

NY Fed'in klasik çalışması ayrımı en net şekilde koyuyor (kendi özetim):
- **Borç yönetimi geri alımı**, Hazine'nin borçluluğunun **biçimini** değiştirir —
  off-the-run borçtan on-the-run borca — ama toplam borçluluğu ve nakit bakiyesini
  **sabit tutar**.
- **Nakit yönetimi geri alımı** ise hem Hazine borçluluğunu hem nakit bakiyesini
  **azaltmanın** bir yoludur. Ancak bütçe fazlası yokken Hazine bu nakdi ileride yeniden
  edinmek zorundadır; yani söndürülen borç yeniden ihdas edilir. Geri alım ile sonraki
  refinansman arasındaki zaman aralığı, Hazine'ye aksi hâlde taşımayacağı bir risk yükler
  (ikame kâğıtlar daha yüksek getiriyle satılırsa ekonomik zarar doğar).

- Kaynak: Kenneth D. Garbade & Matthew Rutherford, "Buybacks in Treasury Cash and Debt
  Management", Federal Reserve Bank of New York Staff Report no. 304, Ekim 2007,
  Bölüm 5. https://www.newyorkfed.org/research/staff_reports/sr304.html

---

## 5. FİNANSMAN — YAZININ EN KRİTİK TEKNİK BÖLÜMÜ

**Bulgu 5.1 — Hazine'nin resmî ilkesi: geri alım borçlanma ihtiyacıdır**

ODM'nin Nisan 2024 program dokümanındaki iki cümle belirleyici:

> Geri alım için harcanan tutarlar, borç yönetimi açısından **diğer herhangi bir
> borçlanma ihtiyacı kaynağı gibi** işlem görür. Hazine, ek ihracı geri alınan kâğıtlarla
> belirli bir vadede **doğrudan eşleştirmeye çalışmayacaktır.**

Ve:

> Geri alımların, dolaşımdaki borcun genel vade profilini **değiştirmesi amaçlanmıyor.**

Yani: (i) geri alımın parası yeni ihraçtan gelir, (ii) ama Hazine "20 yıllık aldım,
20 yıllık ihraç edeyim" gibi bir vade eşleştirmesi taahhüdü vermez. Vade kompozisyonu
ihraç kararlarıyla yönetilir, geri alımla değil.

- Kaynak: ODM Nisan 2024 s. 8.

**Bulgu 5.2 — Aritmetiği kapatan tablo: ODM'nin finansman denklemi**

Hazine'nin TBAC'a sunumundaki "Sources of Privately-Held Financing" tablosu geri alımı
açıkça bir **finansman ihtiyacı kalemi** olarak gösteriyor ve artığı bonoya bırakıyor
(mia $):

**FY26 Ç4 (Temmuz–Eylül 2026):**
| Kalem | Tutar |
|---|---|
| Duyurulan net pazarlanabilir borçlanma | 739 |
| Net kupon ihracı | 375 |
| **Varsayılan geri alımlar** | **45** |
| **İma edilen bono değişimi** | **409** |

**FY27 Ç1 (Ekim–Aralık 2026):**
| Kalem | Tutar |
|---|---|
| Duyurulan net pazarlanabilir borçlanma | 628 |
| Net kupon ihracı | 361 |
| **Varsayılan geri alımlar** | **50** |
| **İma edilen bono değişimi** | **317** |

**[HESAP] Denklemi kapatın:** `Bono = Borçlanma − Net kupon + Geri alım`.
- 739 − 375 + 45 = **409** ✓
- 628 − 361 + 50 = **317** ✓

Bu, geri alımın finansmanının tek satırlık ispatıdır: **geri alım, bono ihracını birebir
artırır.** Duyurulan net borçlanma ihtiyacı değişmez; değişen, o ihtiyacın nasıl
karşılandığıdır. Kupon eğrisinden çekilen nominal, bono eğrisine yüklenir.

Hazine'nin borçlanma projeksiyonlarındaki metodolojik not da bunu doğruluyor: "geri
alımların, özel elde tutulan net pazarlanabilir borçlanmayı önemli ölçüde etkilemesi
beklenmiyor, çünkü **yeni ihraç, geri alınan kâğıtların yerini alıyor**."

Ayrıca varsayım kuralı: likidite desteği geri alımları bir önceki takvim çeyreğinin
fiilî alımlarına eşit varsayılıyor; nakit yönetimi geri alımları en son karşılaştırılabilir
takvim çeyreğine göre (mevsimsellik nedeniyle) alınıyor.

- SAYI/TARİH: FY26Ç4 varsayılan geri alım 45 mia $; FY27Ç1 50 mia $; nakit bakiyesi
  varsayımı 30.09.2026 için 950 mia $, 31.12.2026 için 850 mia $ (30.06.2026: 919 mia $).
- Kaynak: ODM "Fiscal Year 2026 Q3 Report", Temmuz 2026, s. 15–17.

**Bulgu 5.3 — Nominal ≠ nakit: iskontolu tahvil etkisi**

Geri alım **nominal (par) üzerinden borcu söndürür** ama **piyasa fiyatı üzerinden nakit
öder.** Uzun uçtaki düşük kuponlu 2020–2021 ihraçları derin iskontoda işlem gördüğü için
aradaki fark büyüktür.

İşlenmiş örnek — **18 Ağustos 2026, 20Y–30Y likidite desteği operasyonu** (duyurudan bir
gün önce):

| CUSIP | Kupon | Vade | Kabul edilen nominal | Ağırlıklı ort. kabul fiyatı |
|---|---|---|---|---|
| 912810SC3 | %3,125 | 15.05.2048 | 1.000 mn $ | 71,469 |
| 912810SU3 | %1,875 | 15.02.2051 | 175 mn $ | 52,375 |
| 912810SX7 | %2,375 | 15.05.2051 | 825 mn $ | 59,070 |
| **Toplam** | | | **2.000 mn $** | **64,684** (ağırlıklı) |

Operasyon istatistikleri: 36 uygun CUSIP, **3'ü** kabul edildi; teklif 19.868 mn $;
azami 2.000 mn $; **teklif/azami = 9,93×**; %100 doldu. Operasyon 13:40–14:00 ET;
takas 19.08.2026; vade aralığı 15.11.2046–15.05.2056.

**[HESAP]** 2,000 mia $ nominal borç söndürüldü, karşılığında **≈1,294 mia $** temiz
nakit (+ birikmiş faiz) ödendi. Yani:
- Dolaşımdaki nominal borç 2,0 mia $ azalır;
- Finanse edilmesi gereken nakit yalnızca ~1,29 mia $'dır;
- Fark ~0,71 mia $, iskontonun muhasebeleşmemiş "kazancı"dır (ekonomik olarak bir kazanç
  değildir — nominal borç zaten piyasa değerinden fazlaydı, ama borç tavanı ve nominal
  stok istatistikleri açısından önemlidir).

**[HESAP] Duration etkisi.** Aynı üç kâğıdın fiyatlarından çözülen getiriler ve düzeltilmiş
durasyonlar: %5,380 / D=14,20 · %5,405 / D=16,99 · %5,410 / D=16,15. Portföy DV01'i
≈ **1,96 mn $/bp**. 10 yıllık eşdeğeri (10Y modD ≈ 7,7, fiyat ≈ 100 varsayımıyla)
≈ **2,5 mia $ 10 yıllık nominal eşdeğeri**. Yani tek bir 2 mia $ nominal uzun uç
operasyonu, özel sektörün elinden yaklaşık 2,5 mia $ 10 yıllık eşdeğeri duration çeker.
(Bu hesap benimdir; getiri çözümü yarı yıllık kupon tarihi yaklaşımıyla yapılmıştır,
birikmiş faiz ihmal edilmiştir.)

- Kaynak (veri): TreasuryDirect operasyon sonuçları, BBR_20260818174000.xml, 18.08.2026.
  https://www.treasurydirect.gov/instit/annceresult/press/preanre/2026/BBR_20260818174000.pdf
- Kaynak (TBAC'ın aynı yöntemi kullanması): TBAC 29.07.2025, s. 6 dipnot — ortalama geri
  alım fiyatları 72 aylık geri alım WAM'ında 91, 216 aylık WAM'ında 76 varsayılmış;
  "daha uzun vadeli operasyonlar muhtemelen daha fazla iskontolu tahvil alımı içerir ve
  bu nedenle satın alınan milyar nominal başına daha az bono ihracı gerektirir."

**Bulgu 5.4 — WAM (ağırlıklı ortalama vade) etkisi: sayısallaştırılmış**

TBAC'ın Temmuz 2025 senaryo analizi, geri alımın WAM üzerindeki etkisini doğrudan
ölçüyor. Varsayımlar: geri alımların piyasa değeri **3 aylık bono** ile finanse ediliyor;
30.06.2025 itibarıyla 28,6 trilyon $ pazarlanabilir borç, WAM 72 ay.

Yıllık WAM değişimi (ay), çeyreklik geri alım büyüklüğü × geri alım WAM'ı matrisi:

| Geri alım WAM (ay) / ort. fiyat | 30 mia$/çeyrek | 60 | 90 | 120 | 150 |
|---|---|---|---|---|---|
| 72 ay (px 91) | −0,3 | −0,5 | −0,8 | −1,1 | −1,3 |
| 108 ay (px 87) | −0,4 | −0,8 | −1,2 | −1,6 | −2,0 |
| 144 ay (px 82) | −0,5 | −1,1 | −1,6 | −2,2 | −2,7 |
| 180 ay (px 79) | −0,7 | −1,4 | −2,0 | −2,7 | −3,4 |
| 216 ay (px 76) | −0,8 | −1,6 | −2,5 | −3,3 | −4,1 |

Kritik kıyas: **WAM'ın yıllık değişiminin standart sapması 2 ay**. Mevcut program azami
büyüklükte yapılsa (30 mia $/çeyrek, ~9 yıl geri alım WAM'ı) WAM'ı **yılda 0,4 ay**
kısaltır — tipik bir yıllık değişimin çok içinde.

TBAC'ın 10Y–20Y'yi 4→8 mia $, 20Y–30Y'yi 4→6 mia $'a çıkarma önerisinin etkisi: program
azamisi 36 mia $/çeyreğe (≈10,5 yıl WAM) çıkar ve mevcut 30 mia $'lık programa kıyasla
WAM'ı yılda **ilave 0,2 ay** kısaltır.

TBAC'ın ilkesel duruşu (yazının tezini destekleyecek cümle, kendi özetim): likidite
desteği amacı verildiğinde, WAM gibi geniş metrikler **ihraç kararlarıyla** yönetilmeli,
likidite desteği geri alım programıyla değil. Hazine geri alım büyüklüklerini, borcun
genel vade kompozisyonunu maddi olarak değiştirmeden artırabilir.

TBAC 1Ç2023 sunumundaki tamamlayıcı ölçüm: 6–12 aylık "short coup" geri alımları bono
eğrisinin herhangi bir kombinasyonuyla finanse edilirse WAM etkisi **0,05 aydan az**.

- SAYI/TARİH: WAM yıllık değişim std sapması 2 ay; 30 mia$/çeyrek → −0,4 ay/yıl;
  36 mia$/çeyrek → ilave −0,2 ay/yıl; 28,6 tn $ pazarlanabilir borç, WAM 72 ay (30.06.2025).
- Kaynak: TBAC "Treasury Buyback Program Enhancements", 29.07.2025, s. 2, 6, 9;
  TBAC "Considerations for Designing a Regular and Predictable Treasury Buyback Program",
  1Ç2023, s. 10, 21, 27, 28.
  https://home.treasury.gov/system/files/221/TBACCharge1Q12023.pdf

**Bulgu 5.5 — Term premium argümanı**

TBAC 1Ç2023: off-the-run alıp uzun vadeli on-the-run ihraç etmenin term premium maliyeti
endişesi **küçüktür**, çünkü Hazine süreçte benzer vadede term premium'u hem **öder hem
alır**. Ayrıca geri alım ile finansman arasındaki gün içi getiri dalgalanmaları zamanla
birbirini götürür. Bu nedenle TBAC, geri alım ile finansmanın **ayrı ayrı** yürütülmesini
(switch/takas yerine) öneriyor.

- Kaynak: TBAC 1Ç2023, s. 27–28.

**Bulgu 5.6 — Doğrudan tasarruf kanalı (arbitraj)**

TBAC 3Ç2022'nin iki kanal ayrımı:
1. **Dolaylı**: geri alım piyasa likiditesini artırır → likidite primi düşer → Hazine'nin
   fonlama maliyeti düşer.
2. **Doğrudan**: Hazine **daha yüksek getirili (ucuz) off-the-run** kâğıt alıp **daha
   düşük getirili (pahalı) on-the-run ve bono** ihraç ederse vergi mükellefi doğrudan
   kazanır. Bonolar likidite + "moneyness/güvenlik" primi taşıdığından bono ile
   finansman bu farkı büyütebilir.

Uyarı: ihraç büyüklükleri fazla artarsa on-the-run likidite primi erir ve doğrudan kazanç
kaybolur. TBAC bunu programın temel belirsizliği olarak işaretliyor.

- Kaynak: TBAC "Revisiting Treasury Buybacks", 3Ç2022, s. 12, 16–17, 19, 24.
  https://home.treasury.gov/system/files/221/TBACCharge2Q32022.pdf

---

## 6. QE, OPERATION TWIST ve GERİ ALIM: NET KARŞILAŞTIRMA

**Bulgu 6.1 — Üç aracın yapısal karşılaştırması**

| | **QE (LSAP)** | **Operation Twist (MEP)** | **Hazine geri alımı** |
|---|---|---|---|
| Kim yapar | Federal Reserve (para otoritesi) | Federal Reserve | ABD Hazinesi (maliye/borç idaresi) |
| Kâğıda ne olur | Fed bilançosunda **varlık** olarak durur (SOMA) | SOMA içinde **kompozisyon değişir** | **İtfa edilir, yok edilir** |
| Karşılığında ne yaratılır | **Banka rezervi** (Fed yükümlülüğü) — para tabanı büyür | Hiçbir şey; kısa kâğıt satılır/itfa edilir | **Yeni Hazine kâğıdı** (esasen bono) |
| Fed bilanço büyüklüğü | **Büyür** | **Değişmez** | **Değişmez** |
| Özel sektörün elindeki net Hazine arzı (nominal) | **Azalır** (Fed emer) | Değişmez; sadece vade kayar | **Değişmez** (yeni ihraç yerini alır) |
| Özel sektörün taşıdığı duration | **Azalır** | **Azalır** (uzun al, kısa sat) | **Azalır** (uzun al, bono ihraç et) — ama çok daha küçük ölçekte |
| Para politikası sinyali | Güçlü, kasıtlı | Güçlü, kasıtlı | **Yok** (Hazine bunu bir politika sinyali olarak sunmuyor) |
| Stres dönemi müdahalesi | Evet (piyasa işleyişi QE'si) | — | **Hayır, açıkça amaçlanmıyor** |
| Ölçek | QE1 1,25 tn $ MBS + 175 mia $ ajans + 300 mia $ UST; QE2 600 mia $ UST; QE3 aylık 40 mia $ MBS + 45 mia $ UST | **667 mia $** | **450,4 mia $ nominal / 27 ayda** (bkz. Bulgu 8.1) — ve bunun **karşılığı ihraç edilir** |

- QE rakamları kaynağı: Federal Reserve Board, "Timeline: Balance Sheet Policies" ve
  "Recent balance sheet trends".
  https://www.federalreserve.gov/monetarypolicy/timeline-balance-sheet-policies.htm
- MEP kaynağı: Federal Reserve Board, "Maturity Extension Program and Reinvestment
  Policy" — 21.09.2011 duyurusu: Haziran 2012 sonuna kadar kalan vadesi **6–30 yıl** olan
  **400 mia $** Hazine kâğıdı alımı ve kalan vadesi **3 yıl veya daha az** olan eşit
  tutarda satış; 20.06.2012'de **267 mia $** uzatma; program **31.12.2012**'de bitti;
  toplam **667 mia $**.
  https://www.federalreserve.gov/monetarypolicy/maturityextensionprogram.htm
  https://www.federalreserve.gov/newsevents/pressreleases/monetary20110921a.htm

**Bulgu 6.2 — "Geri alım QE değildir" — üç maddede kesin gerekçe**

1. **Bilanço**: Fed'in bilançosu değişmez; rezerv yaratılmaz. Geri alım yalnızca
   Hazine'nin borç kompozisyonunu değiştirir. Yasal dayanak (31 U.S.C. 3111) parayı
   "bir yükümlülüğün satışından elde edilen para" olarak tanımlar — yani borçla.
2. **Net arz**: Hazine'nin kendi projeksiyon metodolojisi, geri alımların özel elde
   tutulan net pazarlanabilir borçlanmayı önemli ölçüde etkilemediğini, çünkü yeni
   ihracın geri alınanın yerini aldığını söylüyor. Net arz sabit; kompozisyon değişiyor.
3. **Amaç ve sinyal**: Hazine bunu bir para politikası aracı olarak sunmuyor ve akut
   piyasa stresine müdahale aracı olmadığını açıkça yazıyor.

**Ancak yazının dürüst olması gereken nokta:** geri alım **duration açısından nötr
değildir.** Uzun kuponlu kâğıt alıp bono ihraç etmek, özel sektörün taşıdığı faiz riskini
azaltır — mekanizma olarak Operation Twist'in maliye politikası tarafındaki küçük
kardeşidir. Fark ölçekte ve niyette:
- **[HESAP]** 18.08.2026 operasyonu ≈ 1,96 mn $/bp DV01 ≈ 2,5 mia $ 10Y eşdeğeri.
- **[HESAP]** 9 Eylül değişikliğinin çeyrek sonuna kadar yarattığı ilave 14 mia $
  nominal uzun uç kapasitesi (bkz. Bulgu 9.2), ~%65 ortalama fiyat ve ~15 düzeltilmiş
  durasyon varsayımıyla ≈ **13,7 mn $/bp ilave DV01 ≈ 17,8 mia $ 10Y eşdeğeri**.
- Karşılaştırma: MEP 667 mia $ (15 ayda) — iki büyüklük mertebesi fark.

**Bulgu 6.3 — 2026'da eş zamanlı üçüncü aktör: Fed'in rezerv yönetimi alımları (RMP)**

Yazının karıştırmaması gereken bir nokta: 2026'da Fed de Hazine kâğıdı alıyor — ama bu
ne QE ne de geri alımdır.
- Aralık 2025 FOMC toplantısında Komite, rezerv bakiyelerinin "bol" (ample) seviyeye
  indiğine hükmetti ve rezerv arzını sürdürmek için kısa vadeli Hazine kâğıdı alımlarına
  başladı. Bu, 2017'den beri süren niceliksel sıkılaştırma (QT) döneminin sonu oldu.
- FOMC, NY Fed Masası'nı SOMA'yı **Hazine bonoları** ve gerekirse kalan vadesi **3 yıl
  veya daha az** olan diğer Hazine kâğıtları ile artırmaya yönlendirdi (RMP).
- Ocak 2026 başından itibaren SOMA yaklaşık **250 mia $** Hazine bonosu aldı; bunun
  ~160 mia $'ı RMP, ~90 mia $'ı ajans MBS anapara geri dönüşlerinin yeniden yatırımı.
- Rezerv bakiyeleri ~3,1 tn $ seviyesine yükseldi (bol aralık içinde). Aylık RMP tutarı
  önceden belirlenmiş bir patikada değil.

**Fed bilançosu, 20 Ağustos 2026 H.4.1 (mn $):**
| Kalem | Tutar |
|---|---|
| Reserve Bank credit | 6.705.727 |
| Doğrudan tutulan menkul kıymetler | 6.471.814 |
| — ABD Hazine kâğıtları | 4.538.703 |
| — — Bonolar | 534.115 |
| — — Nominal tahvil/bono | 3.621.850 |
| — — Enflasyona endeksli | 276.076 |
| — MBS | 1.930.764 |
| Rezerv bakiyeleri | 2.935.287 |

Kritik ayrım: **Fed kısa uçtan alıyor (bono, ≤3Y), Hazine uzun uçtan alıyor.** İkisi
zıt yönde duration etkisi yaratmıyor — Fed'in RMP'si duration nötrdür (bono), Hazine'nin
geri alımı ise duration çeker ve bono ihraç eder. Net etki: özel sektör hem Fed'e hem
Hazine'ye bono kaynağı sağlıyor, uzun kâğıt stoğu azalıyor.

- Kaynak: NY Fed, "Statement Regarding Reserve Management Purchases Operations",
  10.12.2025; NY Fed, "FAQs: Reserve Management Purchases and Reinvestment Purchases";
  NY Fed, Perli konuşması "Reflections on the Early Days of Reserve Management Purchases
  and the Maintenance of Ample Reserves", 26.03.2026.
  https://www.newyorkfed.org/markets/opolicy/operating_policy_251210a
  https://www.newyorkfed.org/markets/reserve-management-reinvestment-purchases-faq
  https://www.newyorkfed.org/newsevents/speeches/2026/per260326
- Kaynak (bilanço): Federal Reserve Board, H.4.1, yayım 20.08.2026 (hafta sonu 19.08.2026).
  https://www.federalreserve.gov/releases/h41/current/

**Bulgu 6.4 — SOMA kısıtı: iki aracın kesişim noktası**

Geri alımın CUSIP limiti formülünde SOMA doğrudan yer alıyor (Bulgu 3.4): serbest
dolaşım = dolaşımdaki nominal − SOMA − STRIPS, ve takas sonrası SOMA payı %70'i
aşamaz. Yani **Fed'in geçmişteki QE alımları, bugün Hazine'nin hangi CUSIP'i ne kadar
geri alabileceğini fiilen sınırlıyor.** 912810QA9 örneğinde SOMA'nın %70'e yakın payı
kâğıdı programdan tamamen dışlıyor.

- Kaynak: ODM Nisan 2024 s. 5.

---

## 7. OFF-THE-RUN / ON-THE-RUN LİKİDİTE PRİMİ

**Bulgu 7.1 — Neden off-the-run hedefleniyor**

On-the-run tahviller iki nedenle daha düşük getiriyle işlem görür:
1. **Likidite**: işlem hacmi ve derinliği yüksektir.
2. **Repo değeri**: sahibi bunları açığa satanlara ödünç verip ek gelir elde edebilir.

Off-the-run kâğıtlar bu primden yoksundur; likidite primi doğrudan **daha yüksek getiri**
olarak vergi mükellefine maliyet yazar. Geri alımın mantığı: Hazine primsiz (ucuz) kâğıdı
alır, primli (pahalı) kâğıdı ihraç eder.

Off-the-run kâğıtlar geri alıma girer ÇÜNKÜ: (i) satıcı bulmakta zorlanan gerçek bir
envanter vardır, (ii) on-the-run/CTD/repo special kâğıtlar zaten dışlanmıştır — Hazine
piyasanın en likit kâğıdını çekip likiditeyi bozmak istemez.

- Kaynak: TBAC 3Ç2022, s. 16 (Duffie 1996; Garbade & Rutherford 2007 atıflarıyla);
  ayrıca Amihud & Mendelson 1991, Warga 1992, Krishnamurthy 2002, Krishnamurthy &
  Vissing-Jorgensen 2012 (TBAC üzerinden aktarım).

**Bulgu 7.2 — Primin büyüklüğü: ölçülmüş rakamlar**

- **10 yıllık on-the-run primi**, Fed'in off-the-run getiri eğrisiyle ölçüldüğünde:
  1998–2007 ortalaması **19,4 bp**; 2013–2022 ortalaması **3,8 bp**. Aynı dönemde
  ortalama çeyreklik 10 yıllık ihraç büyüklüğü 18 mia $'dan 77 mia $'a çıktı. Yani
  ihraç büyüdükçe on-the-run primi eridi.
- **1 yıl altı "short coup"lar** (rolldown ile 1 yıl altına inmiş kupon kâğıtları):
  6 ay–1 yıl bandında benzer vadeli bonolara karşı **10–20 bp** getiri farkı nadir değil;
  1 yıl altında asset-swap spread dağılımı belirgin şekilde genişliyor — kötü likiditenin
  işareti.
- **Kabul edilen tekliflerin ucuzluğu (1Ç2025 TBAC ölçümü)**: satın alınan kâğıtların,
  sunumu yapan üyenin Z-spread spline'ına göre nominal-ağırlıklı ortalama ucuzluğu:

| Kova | 1Ay–2Y | 2Y–3Y | 3Y–5Y | 5Y–7Y | 7Y–10Y | 10Y–20Y | 20Y–30Y |
|---|---|---|---|---|---|---|---|
| Ort. ucuzluk (bp) | 1,79 | 0,88 | 0,52 | 0,26 | 0,37 | 0,58 | 0,18 |

  Yani Hazine genel olarak ucuz kâğıt alıyor, ama uzun uçta marj çok ince (0,18–0,58 bp)
  — likidite sağlama ile göreli değer arasında denge kuruluyor.

- Kaynak: TBAC 3Ç2022 s. 14; TBAC 1Ç2023 s. 21; TBAC 1Ç2025 s. 9.

**Bulgu 7.3 — Program başladıktan sonra off-the-run işleyişi iyileşti mi?**

TBAC Temmuz 2025 bulgusu (kendi özetim): Hazine piyasası işleyişi 2023'ten beri
iyileşiyor ve bu eğilim geri alım programının Mayıs 2024'te başlamasından sonra da
sürdü. Uydurulmuş Hazine eğrisine göre off-the-run dağılımı (RMSE) 2023 sıkılaştırma
döngüsünde zirve yaptıktan sonra düşüş trendine girdi ve program başladıktan sonra
düşmeye devam etti.

Ama aynı sunum karşıt bir gözlem de veriyor: **birincil satıcı Hazine envanteri artmaya
devam ediyor.** Son bir yılda toplam Hazine envanteri **93 mia $ (%31)** arttı
(2Ç25 ort. / 2Ç24 ort.). Pazarlanabilir borç stoğuna normalize edildiğinde envanter
2019'daki tüm zamanların zirvesine yakın. En büyük yüzde artışlar <2Y, 7Y–11Y ve
11Y–21Y sektörlerinde.

Birincil satıcı Hazine envanteri (çeyreklik ortalama, mia $):
| Çeyrek | Toplam |
|---|---|
| 2Ç24 | 299 |
| 3Ç24 | 329 |
| 4Ç24 | 310 |
| 1Ç25 | 400 |
| 2Ç25 | 392 |

- Kaynak: TBAC 29.07.2025, s. 3–4 (kaynak: NY Fed birincil satıcı istatistikleri,
  sunum yapan üyenin hesaplamaları).

**Bulgu 7.4 — Geri alım piyasada ne kadar büyük? Bağlam rakamları**

1Ç2025 TBAC ölçümleri (29.05.2024–22.01.2025 dönemi):
- Kabul edilen nominal kupon hacmi, operasyon tarihleri çevresinde **3 günlük hareketli
  ortalama off-the-run hacminin ortalama %10'u**. Tüm operasyonlar tam dolsaydı %13
  olurdu.
- Ancak dönem boyunca **günlük ortalama off-the-run hacmi 183 mia $** olduğu için, geri
  alımlar toplam piyasa hacmine göre görece küçük bir katılım oranı.
- **Birincil satıcı bakiyelerine göre**: kabul edilen nominal kupon hacmi (0,3] yıl
  sektöründe dealer bakiyelerinin ortalama **%19'u**, (3,30] yıl sektöründe **%4'ü**.
- **Uzun TIPS'te** operasyonlar tek günlük sektör hacminin tamamına eşit olabiliyor
  (10–30Y TIPS'te azami/hacim oranı %63–%125 arasında ölçüldü).

Sonuç (TBAC): operasyon günü tek tek sektörlerde geri alım **önemli** büyüklükte, ama
kümülatif piyasa hacmi bağlamında etki **ılımlı**.

- Kaynak: TBAC 1Ç2025, s. 10–13 (kaynak: TreasuryDirect, FINRA günlük Hazine hacim
  verileri, NY Fed birincil satıcı istatistikleri).

**Bulgu 7.5 — Yoğunlaşma: birkaç CUSIP toplamın yarısını oluşturuyor**

1Ç2025 TBAC: 319 ihraç geri alıma uygun oldu, 205'i kabul edildi. Toplam 92,052 mia $
nominal kabul edildi (potansiyel 115 mia $ üzerinden). **Kabul edilen ihraçların en üst
%10'u, geri alınan nominalin 48,422 mia $'ını (toplamın %52,6'sı)** oluşturdu — medyan
4 kümülatif operasyonda. Yani piyasada belirli envanterleri tüketmeye yönelik güçlü,
sürekli "axe"ler var.

En çok alınan beş CUSIP (kümülatif, dönem sonu):
| CUSIP | Kupon | Vade | Kümülatif kabul | Dolan operasyon sayısı |
|---|---|---|---|---|
| 91282CHN4 | %4,75 | 31.07.2025 | 6,164 mia $ | 7 |
| 91282CFE6 | %3,13 | 15.08.2025 | 4,906 mia $ | 4 |
| 91282CAB7 | %0,25 | 31.07.2025 | 4,656 mia $ | 3 |
| 912828K74 | %2,00 | 15.08.2025 | 4,565 mia $ | 5 |
| 91282CBQ3 | %0,50 | 28.02.2026 | 3,672 mia $ | 6 |

- Kaynak: TBAC 1Ç2025, s. 7.

---

## 8. OPERASYON TAKVİMİ VE BÜYÜKLÜKLERİ: 2024 → 2026

**Bulgu 8.1 — Kümülatif tablo (birincil veriden kendi derlemem)**

Treasury Fiscal Data API `buybacks_operations` veri setinden derlenmiştir; dönem
**29.05.2024 – 20.08.2026**, **155 operasyon**. **[HESAP]** (toplama benim, satır verisi
birincil).

| Tip | Kova | Op. | Teklif (mia$) | Azami (mia$) | Alınan (mia$) | Teklif/Azami | Doluluk |
|---|---|---|---|---|---|---|---|
| Nakit Yön. | 1Ay–2Y | 25 | 673,1 | 247,0 | 236,9 | 2,73× | %96 |
| Likidite | 1Ay–2Y | 10 | 320,3 | 34,0 | 34,0 | 9,41× | %100 |
| Likidite | 2Y–3Y | 9 | 77,0 | 34,0 | 19,4 | 2,27× | %57 |
| Likidite | 3Y–5Y | 11 | 113,4 | 40,0 | 29,4 | 2,83× | %74 |
| Likidite | 5Y–7Y | 9 | 56,0 | 35,0 | 14,9 | 1,60× | %43 |
| Likidite | **7Y–10Y** | 9 | 43,9 | 34,0 | **3,7** | 1,29× | **%11** |
| Likidite | **10Y–20Y** | 25 | **481,5** | 50,0 | **50,0** | **9,63×** | **%100** |
| Likidite | **20Y–30Y** | 26 | **529,2** | 52,0 | **49,0** | **10,18×** | **%94** |
| Likidite | TIPS 1Y–7.5Y | 10 | 24,2 | 5,0 | 3,8 | 4,84× | %75 |
| Likidite | TIPS 1Y–10Y | 8 | 32,9 | 6,0 | 5,6 | 5,49× | %94 |
| Likidite | TIPS 7.5Y–30Y | 9 | 12,2 | 4,5 | 3,1 | 2,72× | %69 |
| Likidite | TIPS 10Y–30Y | 4 | 4,1 | 2,0 | 0,5 | 2,06× | %23 |
| **TOPLAM** | | **155** | **2.367,9** | **543,5** | **450,4** | | |

Karşılaştırma için Hazine'nin kendi yayımladığı kesit (28.07.2026'ya kadar, 148 operasyon):
teklif 2.292,1 mia $, azami 528,0 mia $, alınan 440,5 mia $. Aradaki fark 28.07–20.08
arasındaki 7 operasyondan geliyor — rakamlarım tutarlı.

Hazine'nin kendi vurgusu: **Temmuz 2026 sonu itibarıyla en çok alım yapılan iki sektör
1 Ay–2 Yıl nominal kuponlarda 266,9 mia $ ve uzun uç nominal kuponlarda 95,0 mia $.**

- Kaynak (satır verisi): Treasury Fiscal Data, `buybacks_operations` veri seti, çekim
  24.08.2026. https://fiscaldata.treasury.gov/datasets/treasury-securities-buybacks/
- Kaynak (Hazine kesiti): ODM "Fiscal Year 2026 Q3 Report", Temmuz 2026, s. 46.

**Bulgu 8.2 — Operasyon başına azami tutarların evrimi**

| Dönem | Kaynak/olay | Nominal kupon LS | 10Y–20Y ve 20Y–30Y | TIPS LS | Nakit yönetimi |
|---|---|---|---|---|---|
| Mayıs 2024 (başlangıç) | Mayıs 2024 duyurusu | **2 mia $** / op | 2 mia $ | **500 mn $** / op | — |
| Ağu–Eki 2024 | Temmuz 2024 duyurusu | **4 mia $** / op | **2 mia $** (kova başına 2 op) | 500 mn $ (her TIPS kovası 2 op) | 4 op × **5 mia $** = 20 mia $ (Eylül 2024) |
| Ara 2024 | | | | | 7,5 mia $ / op |
| Mar–Nis 2025 | | | | | 8,5 mia $ / op |
| Haz 2025 | | | | | 10 mia $ / op |
| Nis 2026 | | | | | **15 mia $** / op |
| Haz 2026 | | | | | 12,5 mia $ / op |
| Ağu–Eki 2026 (plan) | QRS 05.08.2026 | 4 mia $ | **2 mia $** | 750 mn $ (kısa), 500 mn $ (uzun) | **12,5 mia $** / op |
| **9 Eyl 2026'dan** | **sb0607, 19.08.2026** | 4 mia $ | **en az 4 mia $** | değişmedi | değişmedi |

Çeyreklik program azamileri:
- Ağustos 2023'te açıklanan başlangıç tasarımı: likidite desteği **çeyrek başına 30 mia $**
  (kova başına nominalde 4 mia $, TIPS'te 1 mia $); nakit yönetimi ilk yılda **en fazla
  120 mia $**.
- Ağustos 2026 çeyreği: likidite desteği **38 mia $**, nakit yönetimi **25 mia $**.

- Kaynak: ODM Ağustos 2023 s. 4; ODM "Review of Treasury Buyback Results", 29.10.2024,
  s. 2; Treasury geçici takvim 05.08.2026; Treasury QRS sb0590 (05.08.2026);
  Treasury sb0607 (19.08.2026); Fiscal Data operasyon verisi.

**Bulgu 8.3 — Ağustos 2026 çeyreği geçici takvimi (tam liste)**

Yayım 05.08.2026. Tüm operasyonlar 13:40–14:00 ET; takas T+1. (*) işaretliler Mayıs 2026
refinansman çeyreğine ait.

| Duyuru | Operasyon | Tip | Kâğıt / vade | Azami |
|---|---|---|---|---|
| 05.08 | 06.08 * | Likidite | Nominal 1Ay–2Y | 4 mia $ |
| 10.08 | 11.08 * | Likidite | Nominal 10Y–20Y | 2 mia $ |
| 17.08 | 18.08 | Likidite | Nominal 20Y–30Y | 2 mia $ |
| 19.08 | 20.08 | Likidite | Nominal 3Y–5Y | 4 mia $ |
| 24.08 | 25.08 | Likidite | Nominal 5Y–7Y | 4 mia $ |
| 02.09 | 03.09 | **Nakit Yön.** | Nominal 1Ay–2Y | **12,5 mia $** |
| 08.09 | **09.09** | **Nakit Yön.** | Nominal 1Ay–2Y | **12,5 mia $** |
| 09.09 | **10.09** | Likidite | Nominal 10Y–20Y | 2 → **≥4 mia $** |
| 14.09 | 15.09 | Likidite | TIPS 10Y–30Y | 500 mn $ |
| 16.09 | 17.09 | Likidite | Nominal 7Y–10Y | 4 mia $ |
| 23.09 | 24.09 | Likidite | Nominal 20Y–30Y | 2 → **≥4 mia $** |
| 28.09 | 29.09 | Likidite | TIPS 1Y–10Y | 750 mn $ |
| 30.09 | 01.10 | Likidite | Nominal 10Y–20Y | 2 → **≥4 mia $** |
| 05.10 | 06.10 | Likidite | Nominal 2Y–3Y | 4 mia $ |
| 07.10 | 08.10 | Likidite | Nominal 20Y–30Y | 2 → **≥4 mia $** |
| 14.10 | 15.10 | Likidite | Nominal 10Y–20Y | 2 → **≥4 mia $** |
| 20.10 | 21.10 | Likidite | TIPS 1Y–10Y | 750 mn $ |
| 26.10 | 27.10 | Likidite | Nominal 20Y–30Y | 2 → **≥4 mia $** |
| 03.11 | 04.11 | Likidite | Nominal 10Y–20Y | 2 → **≥4 mia $** |
| 04.11 | 05.11 | Likidite | Nominal 1Ay–2Y | 4 mia $ |

**[HESAP]** Takvimdeki likidite desteği azamileri (Mayıs çeyreğine ait iki operasyon hariç)
toplamı **tam olarak 38,0 mia $** — QRS'teki rakamla birebir uyuşuyor. Nakit yönetimi:
2 × 12,5 = **25,0 mia $** — QRS ile birebir.

Not: 19.08 duyurusunun "9 Eylül'den itibaren" ifadesindeki 9 Eylül operasyonu bir **nakit
yönetimi** operasyonudur; değişiklikten fiilen etkilenen **ilk uzun uç operasyonu
10 Eylül 2026 (10Y–20Y)**'dir.

Ayrıca Hazine "genel olarak" tüm kovaları çeyrekte en az bir kez kapsamaya ve tatilleri,
büyük veri açıklamalarını ve FOMC duyurularını atlamaya çalışıyor.

- Kaynak: Treasury, "Tentative Schedule of Treasury Buyback Operations — August 2026
  Quarterly Refunding", yayım 05.08.2026; ODM Nisan 2024 s. 4.
  https://home.treasury.gov/system/files/221/Tentative-Buyback-ScheduleQ32026.pdf

**Bulgu 8.4 — 2026 operasyonları (Ocak–Ağustos), operasyon bazında**

Teklif/azami oranı ve doluluk (mia $; kaynak: Fiscal Data API, 24.08.2026 çekimi):

| Tarih | Tip | Kova | Uygun/Kabul CUSIP | Teklif | Azami | Alınan |
|---|---|---|---|---|---|---|
| 20.08.2026 | LS | 3Y–5Y | 48 / 3 | 10,159 | 4,0 | 1,860 |
| 18.08.2026 | LS | 20Y–30Y | 36 / 3 | 19,868 | 2,0 | 2,000 |
| 11.08.2026 | LS | 10Y–20Y | 37 / 2 | 7,399 | 2,0 | 2,000 |
| 06.08.2026 | LS | 1Ay–2Y | 61 / 15 | 35,786 | 4,0 | 4,000 |
| 28.07.2026 | LS | 20Y–30Y | 35 / 3 | 21,935 | 2,0 | 2,000 |
| 23.07.2026 | LS | 10Y–20Y | 38 / 2 | 16,304 | 2,0 | 2,000 |
| 22.07.2026 | LS | TIPS 1Y–10Y | 27 / 6 | 3,194 | 0,750 | 0,405 |
| 16.07.2026 | LS | 20Y–30Y | 36 / 3 | 30,542 | 2,0 | 2,000 |
| 09.07.2026 | LS | 2Y–3Y | 32 / 11 | 12,464 | 4,0 | 2,295 |
| 01.07.2026 | LS | 10Y–20Y | 38 / 2 | 15,724 | 2,0 | 2,000 |
| 25.06.2026 | LS | 20Y–30Y | 35 / 3 | 21,320 | 2,0 | 2,000 |
| 24.06.2026 | LS | TIPS 1Y–10Y | 28 / 6 | 4,545 | 0,750 | 0,750 |
| 16.06.2026 | LS | 7Y–10Y | 10 / 2 | 5,068 | 4,0 | 0,570 |
| 11.06.2026 | **CM** | 1Ay–2Y | 50 / 18 | 27,896 | 12,5 | 12,078 |
| 09.06.2026 | LS | 10Y–20Y | 37 / 4 | 18,390 | 2,0 | 2,000 |
| 04.06.2026 | **CM** | 1Ay–2Y | 49 / 21 | 41,662 | 12,5 | 12,500 |
| 03.06.2026 | LS | 20Y–30Y | 36 / 14 | 21,260 | 2,0 | 2,000 |
| 28.05.2026 | LS | TIPS 10Y–30Y | 16 / 5 | 0,784 | 0,500 | 0,091 |
| 21.05.2026 | LS | 5Y–7Y | 26 / 1 | 3,751 | 4,0 | 0,300 |
| 19.05.2026 | LS | 3Y–5Y | 48 / 8 | 9,191 | 4,0 | 1,674 |
| 13.05.2026 | LS | TIPS 1Y–10Y | 28 / 8 | 2,339 | 0,750 | 0,735 |
| 07.05.2026 | LS | 1Ay–2Y | 61 / 14 | 43,878 | 4,0 | 4,000 |
| 06.05.2026 | LS | 10Y–20Y | 36 / 2 | 19,689 | 2,0 | 2,000 |
| 28.04.2026 | LS | 20Y–30Y | 35 / 6 | 35,562 | 2,0 | 2,000 |
| 23.04.2026 | LS | 2Y–3Y | 32 / 2 | 4,747 | 4,0 | 0,358 |
| 22.04.2026 | **CM** | 1Ay–2Y | 49 / 26 | 37,841 | 15,0 | 15,000 |
| 16.04.2026 | **CM** | 1Ay–2Y | 46 / 18 | 40,033 | 15,0 | 15,000 |
| 15.04.2026 | LS | 10Y–20Y | 37 / 2 | 18,055 | 2,0 | 2,000 |
| 09.04.2026 | LS | 20Y–30Y | 35 / 3 | 36,472 | 2,0 | 2,000 |
| 01.04.2026 | **CM** | 1Ay–2Y | 53 / 20 | 43,113 | 15,0 | 15,000 |

Dikkat çeken yapı: uzun uç operasyonlarında **36 uygun CUSIP'ten yalnızca 2–3'ü** kabul
ediliyor. Yani talep muazzam ama Hazine fiyata duyarlı davranıp yalnızca en ucuz birkaç
kâğıdı alıyor. Belly'de (5Y–7Y, 7Y–10Y) tam tersi: teklif zayıf, doluluk düşük.

- Kaynak: Treasury Fiscal Data, `buybacks_operations`, çekim 24.08.2026.

---

## 9. 19 AĞUSTOS 2026 DEĞİŞİKLİĞİNİN NİCEL KARŞILIĞI

**Bulgu 9.1 — Değişikliği hazırlayan kanıt: teklif/azami oranları**

Hazine'nin gerekçesi ("uzun vadeli operasyonlarda rutin olarak alınan yüksek kaliteli
tekliflerin önemli hacmi") verilerle birebir örtüşüyor.

**[HESAP]** 2026 yılbaşından 20 Ağustos'a kadar, operasyon bazında teklif/azami oranları:

- **20Y–30Y** (11 operasyon): 12,6× · 12,8× · 12,5× · 18,0× · 18,2× · 17,8× · 10,6× ·
  10,7× · 15,3× · 11,0× · 9,9×
  → Toplam 298,6 mia $ teklif / 22,0 mia $ azami = **13,57× ortalama**; alınan 20,2 mia $.
- **10Y–20Y** (11 operasyon): 14,3× · 11,4× · 10,4× · 8,9× · 18,0× · 9,0× · 9,8× · 9,2× ·
  7,9× · 8,2× · 3,7×
  → Toplam 221,8 mia $ teklif / 22,0 mia $ azami = **10,08× ortalama**; alınan 22,0 mia $
  (%100 doluluk).

Karşılaştırma: aynı 2026 döneminde 5Y–7Y'de teklif/azami 0,94×, 7Y–10Y'de 1,27×.

Uzun uç operasyonlarının fiilen tamamı **%100 doluyor** — yani azami tutar bağlayıcı bir
kısıt. Bu, "kapasiteyi artır" sinyalinin kendisidir.

- Kaynak: Treasury Fiscal Data, `buybacks_operations`, çekim 24.08.2026 (satır verisi
  birincil, oran hesapları benim).

**Bulgu 9.2 — Değişikliğin yarattığı ilave kapasite**

**[HESAP]** 9 Eylül 2026'dan 4 Kasım 2026'ya kadar geçici takvimde **7 uzun uç likidite
desteği operasyonu** var: 10.09 (10–20Y), 24.09 (20–30Y), 01.10 (10–20Y), 08.10 (20–30Y),
15.10 (10–20Y), 27.10 (20–30Y), 04.11 (10–20Y). Yani 4 adet 10Y–20Y + 3 adet 20Y–30Y.

| | Operasyon başına 2 mia $ | Operasyon başına 4 mia $ |
|---|---|---|
| 7 operasyonun toplam azamisi | **14,0 mia $** | **28,0 mia $** |
| Çeyrek likidite desteği azamisi | 38,0 mia $ | **52,0 mia $** |

→ Uzun uç kapasitesi **iki katına**, çeyreklik likidite desteği tavanı **%37 artışla
38 → 52 mia $**'a çıkıyor (Hazine takvimi başka yerde kısmadığı varsayımıyla).

**Uyarı — bu bir varsayımdır.** Hazine "güncellenmiş geçici geri alım takvimi daha sonra
yayımlanacak" dedi; operasyon sayısını veya diğer kovaları değiştirebilir. Ayrıca "en az
4 milyar dolar" ifadesi üst sınır koymuyor. 4 Kasım QRS'e kadar kesinlik yok.

**[HESAP] Duration karşılığı**: ilave 14 mia $ nominal uzun uç kapasitesi, 18.08.2026
operasyonundaki gibi ~%65 ortalama fiyat ve ~15 düzeltilmiş durasyon varsayımıyla
≈ 9,1 mia $ piyasa değeri, **≈13,7 mn $/bp DV01**, **≈17,8 mia $ 10 yıllık nominal
eşdeğeri**. Bir çeyrek için. Kıyas: MEP 667 mia $ (15 ay); 30 yıllık ihale büyüklüğü
Ağustos–Ekim 2026 planında ayda 25/22/22 mia $ (Ağu/Eyl/Eki).

- Kaynak: Treasury sb0607 (19.08.2026); geçici takvim (05.08.2026); QRS sb0590
  (05.08.2026, ihale büyüklükleri tablosu); duration hesapları benim.

**Bulgu 9.3 — TBAC bunu bir yıl önce önerdi**

Temmuz 2025 TBAC sunumu (29.07.2025), üç bileşenli bir "buyback score" (teklif/azami
oranı, eğri RMSE'si, off-the-run iskontosu — her birinin 1 yıllık z-skorunun eşit
ağırlıklı ortalaması) geliştirip şu tavsiyeyi verdi:

- **10Y–20Y alımlarını 4 mia $'dan 8 mia $'a çıkar** (yükselen teklif/azami oranları ve
  off-the-run'ların son dönemde ucuzlaması nedeniyle).
- **20Y–30Y alımlarını 4 mia $'dan 6 mia $'a çıkar** (sektörün genel olarak yüksek
  teklif/azami oranları nedeniyle).

Buyback score tablosu (Temmuz 2025):
| Tenor | Teklif/azami (cari) | z | RMSE (bp) | z | Off-the-run iskontosu (bp) | z | **Skor** |
|---|---|---|---|---|---|---|---|
| 1Ay–2Y | 7,5 | −0,5 | 1,1 | −1,2 | −2,0 | −2,4 | −1,4 |
| 2Y–3Y | 1,9 | −0,7 | 0,7 | −2,3 | −2,3 | −1,8 | −1,6 |
| 3Y–5Y | 3,5 | 0,8 | 0,9 | −0,6 | −0,6 | −1,3 | −0,4 |
| 5Y–7Y | 1,8 | −0,2 | 1,3 | −0,6 | −0,5 | −1,5 | −0,8 |
| 7Y–10Y | 1,0 | −0,3 | 1,2 | −1,5 | −2,3 | −2,3 | −1,4 |
| **10Y–20Y** | **11,4** | 1,2 | 1,2 | −0,4 | 0,4 | 1,3 | **+0,7** |
| **20Y–30Y** | **9,4** | 1,6 | 1,3 | 0,3 | 0,8 | 0,1 | **+0,6** |
| TIPS 1Y–7.5Y | 5,8 | 0,2 | 2,1 | −1,0 | −3,0 | −0,1 | −0,3 |
| TIPS 7.5Y–30Y | 4,0 | 1,3 | 2,7 | 0,0 | −0,6 | 1,9 | **+1,0** |

Hazine 19 Ağustos 2026'da bu tavsiyenin yönünü uyguladı ama biçimini değiştirdi: kova
başına çeyreklik tutar yerine **operasyon başına** tutarı ikiye katladı.

Aynı sunumun izlenmesi gereken sektör uyarıları: TIPS 7.5Y–30Y skoru yüksek ama
operasyonlar dolmuyor; 2Y–3Y ve 7Y–10Y azaltma için izlenmeli.

- Kaynak: TBAC "Treasury Buyback Program Enhancements", 29.07.2025, s. 7–9.

**Bulgu 9.4 — TBAC'ın tartıştığı ama uygulanmayan mekanik değişiklikler**

Yazının "ne yapılmadı" bölümü için:
1. **Yield-spread bidding**: katılımcılar en yakın on-the-run'a göre bir getiri spread'i
   kilitleyerek teklif verir. Dealer'lar için süreci basitleştirir (kapanışa doğru onlarca
   CUSIP'in fiyatını güncellemek yerine yalnızca referans on-the-run güncellenir). Ama
   Hazine'nin ima edilen tüm-dahil off-the-run fiyatını hesaplamasını karmaşıklaştırır.
2. **Switch / duration-nötr takas modeli**: off-the-run alıp aynı anda on-the-run vermek.
   Geniş vade dağılımlı kovalarda ciddi **eğri riski** doğurur; son kullanıcı futures ya
   da swap ile hedge etmeyi tercih edebilir. Bir seçenek: katılımcıya outright ya da
   switch teklif verme esnekliği tanımak.
3. **Karşı taraf tabanını daha da genişletmek**: ihalelerdekine benzer açık erişim
   çerçevesi teklif sayısını ve sonuçları iyileştirebilir, son kullanıcıya anonimlik ve
   doğrudan icra sağlar; ama FedTrade erişimi/ek platform, takas ve mutabakat karmaşıklığı
   getirir. Hazine takas (Treasury clearing) reformu bu dengeyi değiştirebilir.
4. **Takvim değişikliği**: TBAC mevcut takvimi "düşünülmüş ve uygun" buldu ama ay içi
   döngüselliğe dikkat çekti — 0–2Y, 3–5Y, 5–7Y, 10–20Y sektörlerinde hacim **ay sonunda**
   yoğunlaşıyor; 2–3Y, 7–10Y, 20–30Y'de ay ortası ya da ay sonu. TIPS 0–5Y'de hacim ayrıca
   **TÜFE açıklaması** çevresinde yükseliyor.

Risk uyarısı (yazı için önemli): **daha büyük operasyon = operasyon başına daha fazla
duration riski**, dolayısıyla oynaklık arttığında sonuçlarda daha fazla değişkenlik.
TBAC'ın hatırlattığı somut örnek: **Temmuz 2024'teki 7Y–10Y operasyonu, kapanış öncesi
getirilerin sert yükselmesi nedeniyle karşılıksız kaldı** (24.07.2024: 2 mia $ azami,
3,706 mia $ teklif, **0 alım**).

- Kaynak: TBAC 29.07.2025, s. 11–12; Fiscal Data (24.07.2024 operasyonu).

---

## 10. TARİHSEL ÖNCEL: 2000–2002 GERİ ALIM PROGRAMI

**Bulgu 10.1 — Rakamlar**

- Hazine, **Mart 2000 – Nisan 2002** arasında **45 ters ihalede toplam 67,5 milyar $**
  tahvil geri aldı.
- İlk **42 operasyon** (2000–2001) bütçe fazlası döneminde tahvil itfalarını kısa/orta
  vadeli itfalarla dengelemek içindi; bu 42 operasyonda **63,5 milyar $** alındı.
- Son **3 operasyon** Nisan 2002'nin ikinci yarısında, mevsimsel güçlü vergi tahsilatı
  döneminde yapıldı ve Hazine'nin nakit bakiyesini **4 milyar $** azalttı — yani ilk
  gerçek "nakit yönetimi geri alımı".
- **Ortalama operasyon büyüklüğü 1,5 milyar $.** Operasyonlar ayda iki kez, genellikle
  ayın ikinci yarısında (Hazine nakit akışının güçlü olduğu dönem).
- Dördüncü operasyon (3 mia $ hedef, 26 farklı tahvil) hantal kalınca Hazine operasyon
  büyüklüğünü **2 milyar $'ı geçmeyecek** ve uygun tahvil setini **10–12 ihraç** olacak
  şekilde sistematik olarak sınırladı.
- 28.09.2000'den itibaren uygun tahvil listesi dört panel arasında sırayla döndürüldü:
  (i) Şubat 2010–Kasım 2014 vadeli çağrılabilir tahviller, (ii) Şubat 2015–2019 vadeli
  çağrılamaz, (iii) 2019–2022/2023, (iv) 2022/2023–Kasım 2027.
- **Karşılama (coverage) oranı** 2,14 ile 8,98 arasında değişti, ortalama **4,39**.
  Hazine hiçbir operasyonda yeterli teklif alamama durumu yaşamadı.
- Ortalama olarak, bir tahvilin 1999 sonu itibarıyla halka açık tutarının **%14'ü** geri
  alındı — ama dağılım çok geniş: 10⅝ Ağustos 2015'in 6 mia $'lık stoğunun yarısından
  fazlası alınırken, 7¼ Mayıs 2016'nın 17¾ mia $'ından hiç alınmadı.

- Kaynak: Garbade & Rutherford, NY Fed Staff Report 304, Ekim 2007, s. 3, 7–12.

**Bulgu 10.2 — 2000 mekaniğinin bugünkünden farkları**

| | 2000–2002 | 2024–2026 |
|---|---|---|
| İhale kapanışı | 11:00 ET | 14:00 ET |
| Sonuç bildirimi | ~11:05 ET bireysel, ~11:15 ET basın bülteni | Operasyon sonrası web sitesi |
| Takas | **T+2** | **T+1** |
| Fiyat formatı | Nominalin yüzdesi, birikmiş faiz hariç, 32'de bir ve 32'de birin sekizde biri | 100 $ nominal başına fiyat |
| Teklif sayısı sınırı | **Yok** | Menkul kıymet başına 9 |
| Asgari teklif | 100.000 $ katları | 1.000.000 $ ve katları |
| Sonuçlarda yayımlanan | Tahvil bazında teklif, kabul, **en yüksek kabul fiyatı**, ağırlıklı ortalama fiyat | Operasyon bazında teklif/kabul + CUSIP bazında ağırlıklı ortalama fiyat (en yüksek kabul fiyatı artık yayımlanmıyor) |
| Katılımcı | **Yalnızca birincil satıcılar** | Birincil satıcılar + Hazine onaylı ek karşı taraflar |
| Amaç | Bütçe fazlası döneminde vade yapısını dengelemek | Likidite desteği + nakit yönetimi |
| Format | Çoklu fiyat | Çoklu fiyat (aynı) |

- Kaynak: Garbade & Rutherford (2007), s. 8–9 ve dipnot 17–21 (31 CFR 375.13, 375.11
  o dönem hâli); 31 CFR 375 (91 FR 15540, 30.03.2026); TreasuryDirect Buyback FAQs.

**Bulgu 10.3 — 2000'deki piyasa etkisi: yazının en çarpıcı tarihsel paraleli**

Programın en önemli etkisi, 2000 başında eğrinin uzun ucunda **olağandışı ve olağandışı
ölçüde dik bir tersine dönme** yaratmasıydı.
- **12 Ocak 2000** — Bakan Summers'ın programı duyurmasından bir gün önce — eğri pozitif
  eğimliydi.
- Duyurudan sonraki günlerde piyasa, programın uzun vadeli getirileri kısa vadelilerin
  altına iteceğini fark etti ve önden alım başladı.
- **18 Ocak – 3 Şubat 2000** arasında 30 yıllık getiri **58 baz puan** düştü (%6,75 →
  %6,17); 5 yıllık yalnızca 9 bp düştü; 2 yıllık **9 bp yükseldi**.
- 16 Mart 2000'deki ikinci geri alım ihalesine gelindiğinde eğri 2 yıl ötesinde tersine
  dönmüştü. 2 yıla kadar olan kısım pozitif eğimli kaldı.
- Basında dönem "kaotik" olarak tarif edildi; uzun tahvilde short squeeze yaşandı.
- Eğri, Fed'in zayıflayan ekonomiye karşı faiz indirmeye başladığı 2001'de yeniden
  pozitif eğime döndü.

Gary Gensler'in (Hazine Müsteşarı, Kasım 2000) değerlendirmesi (kendi özetim): geri
alımlar borcun vade yapısını yönetmeye yardımcı oldu; program olmasaydı ödemelerin
tamamı kısa vadeli borçtan gelirdi ve dolaşımdaki borcun ortalama ömrü **2 ay daha
uzamış** olurdu. İkincisi, geri alımlar benchmark ihraçların likiditesine katkı yaptı;
hatta aksi hâlde ihraç edilemeyecek kâğıtların ihracını mümkün kıldı.

Summers'ın Ocak 2000'deki gerekçesi: geri alımlar benchmark likiditesini artırır ve
zamanla devletin faiz maliyetini düşürür; ayrıca vadesine hatırı sayılır süre kalmış
borcu ödeyerek, borcun ortalama vadesinin (1997'de 5¼ yıl, 1999'da 5¾ yıl, 2004'e kadar
neredeyse 8 yıla çıkması öngörülen) maliyetli ve gereksiz bir şekilde uzamasını önler.

**Yazar için köprü:** 2000'deki 58 bp'lik ralli, arz beklentisinin şok değişimine
verilen tepkiydi (30 yıllık ihracın kıtlaşacağı algısı). 19 Ağustos 2026'daki 9 bp'lik
30 yıllık rallisi ve iki gün içinde sönmesi, aynı mekanizmanın çok daha küçük ve çok
daha hızlı fiyatlanmış bir versiyonudur — çünkü bu kez arz kıtlaşmıyor, yalnızca
kompozisyon kayıyor ve piyasa bunu biliyor.

- Kaynak: Garbade & Rutherford (2007), s. 10–12 ve dipnot 14, 24–26.

**Bulgu 10.4 — 2003–2013 arası boşluk ve test operasyonları**

TreasuryDirect'in kendi kaydına göre **2003–2013 arasında hiç geri alım operasyonu
yapılmadı.** Sonraki yıllarda Hazine operasyonel kapasiteyi korumak için düzenli
**"test" (small-value) geri alım operasyonları** yürüttü. Mart 2024'te küçük tutarlı
geri alım takvimi yayımlandı, Nisan 2024'te küçük tutarlı operasyonlar yapıldı, ilk
gerçek operasyon **29 Mayıs 2024**'te gerçekleşti.

- Kaynak: TreasuryDirect Buyback Announcements & Results sayfası; TBAC 3Ç2022 charge
  metni ("Treasury has conducted regular test buyback operations to maintain operational
  capabilities"); ODM Nisan 2024 s. 4; Fiscal Data (ilk operasyon 29.05.2024).

---

## 11. ULUSLARARASI KARŞILAŞTIRMA (bağlam için)

**Bulgu 11.1 — OECD ülkelerinde geri alım standarttır**

2012 tarihli bir OECD çalışma kâğıdına dayanan TBAC derlemesi: çoğu egemen ihraççının
bir geri alım programı var ve birçoğu bunu düzenli yapıyor. Başlıca gerekçeler sırasıyla
**itfa profilini düzleştirmek**, ardından likidite artırımı ve nakit yönetimi. Alımlar
ağırlıkla kısa vadeli (<2Y) kâğıtlara odaklanıyor: 27 borç idaresinin **25'i (%93)**
itfaya yaklaşan tahvilleri hedeflediğini, **12'si (%44)** bir illikidite ölçütü
kullandığını bildiriyor.

Dört temsilci ihraççı — Kanada, Fransa, Belçika, Avustralya — **brüt ihracın %20–30'unu
veya daha fazlasını** düzenli olarak geri alıyor. Geri alımların WAM'ı ağırlıkla
**1,5 yılın altında.**

Örnek yıl (2018): Kanada brüt ihracın %45'i, Avustralya %41'i, Belçika %20'si,
Fransa %15'i.

**Kanada üç ayrı geri alım türü işletiyor:**
| Tür | Amaç | Uygunluk | Uygulama |
|---|---|---|---|
| Cash management bond buyback (CMBB) | Nakit bakiyesi yönetimi, bono ihracındaki oynaklığı düzleştirmek | <18 ay vadeli CGB; dolaşım >12 mia $; serbest dolaşım (BoC hariç) >8 mia $ | Haftalık |
| Outright (nakit bazlı) | Likidite artırımı | İlliquid yüksek kuponlu tahviller, büyük off-the-run'lar, 1–25 yıl (OTR benchmark hariç) | Genellikle nominal tahvil ihalesini izleyen çarşamba |
| **Switch** | Likidite + on-the-run benchmark ihracını sürdürmek | Aynı | **Duration-nötr** takas: illiquid tahvil ↔ benchmark tahvil |

**Fransa (AFT)**: 2000'den beri geri alım yapıyor; başlangıçta benchmark likiditesi,
zamanla itfa profilini düzleştirme amacına kaydı; **2 yıl ve altı** vadelerle sınırlı;
tersine ihale ya da OTC — son yıllarda yalnızca OTC.

ABD'nin bu tabloda özgün yanı: ABD, likidite desteğini eğrinin **tamamına**, 30 yıla
kadar yayan ender ihraççılardan biri; çoğu ülke kısa uçla sınırlı kalıyor. Ve ABD switch
kullanmıyor — geri alım ile finansmanı ayrı yürütüyor.

- Kaynak: TBAC "Considerations for Designing a Regular and Predictable Treasury Buyback
  Program", 1Ç2023, s. 12–15 (kaynak: OECD 2012 çalışma kâğıdı, Refinitiv, sunum yapan
  üyenin hesaplamaları).

---

## 12. PROGRAMIN ETKİNLİĞİ: TBAC'IN RESMÎ DEĞERLENDİRMESİ

**Bulgu 12.1 — 1Ç2025 değerlendirmesinin sonucu**

29.05.2024–22.01.2025 dönemi için TBAC'ın hükmü (kendi özetim): mevcut geri alım programı
belirtilen hedeflerini geniş ölçüde gerçekleştiriyor ve programı mevcut ayarından
değiştirmek için acil bir ihtiyaç kanıtı çok az.

Alt bulgular:
- **Nominal kuponlar**: uygun ihraçların ortalama **%37'si** bir miktar dolduruldu;
  operasyonların **%68'inde** azami tutarın tamamı alındı.
- **TIPS**: uygun ihraçların ortalama **%39'u** dolduruldu; operasyonların yalnızca
  **%33'ünde** azami tutar alındı.
- Doluluk oranı, teklif edilen tutarın azamiye oranıyla **artıyor** — yüksek hacimli
  katılımın yüksek dolulukla karşılanması, likidite sağlama hedefinin tuttuğunun makul
  bir göstergesi.
- Satın alınan tahviller göreli değer çerçevesinde genel olarak **ucuz** görünüyor.
- Dealer geri bildirimi: program iyi işliyor, off-the-run envanteri için çıkış sağlıyor,
  off-the-run piyasa likiditesini **ılımlı** ölçüde destekliyor.
- Model Z-spread ölçümleri, dönem boyunca piyasanın off-the-run göreli değer iştahının
  **istikrarlı** olduğunu gösteriyor.

- Kaynak: TBAC "Treasury Buyback Program Effectiveness Assessment", 04.02.2025, s. 4,
  6, 18.

**Bulgu 12.2 — Çeyreklik WAM tabloları (fiilî alımlar)**

Likidite desteği (kaynak: TBAC 29.07.2025, s. 15):
| Çeyrek | Nominal (mia $) | Piyasa değeri (mia $) | WAM (ay) |
|---|---|---|---|
| 2Ç24 | 8,4 | 7,5 | 102 |
| 3Ç24 | 16,1 | 13,9 | 136 |
| 4Ç24 | 20,2 | 17,9 | 100 |
| 1Ç25 | 25,1 | 21,8 | 107 |
| 2Ç25 | 20,7 | 17,7 | 120 |
| 3Ç25 (22.07.25'e kadar) | 3,8 | 3,1 | 173 |
| **Toplam** | **94,2** | **81,9** | |

Nakit yönetimi (aynı kaynak, s. 14):
| Çeyrek | Nominal (mia $) | Piyasa değeri (mia $) | WAM (ay) |
|---|---|---|---|
| 3Ç24 | 20,0 | 19,7 | 12 |
| 4Ç24 | 18,7 | 18,3 | 12 |
| 1Ç25 | 25,5 | 25,2 | 12 |
| 2Ç25 | 48,4 | 47,8 | 13 |
| **Toplam** | **112,7** | **110,9** | |

Bu iki tablo Bulgu 5.3'ün genel geçerliliğini gösteriyor: **likidite desteğinde nominal
ile piyasa değeri arasındaki fark %11–19'a çıkıyor** (94,2 → 81,9 mia $, %13 iskonto);
nakit yönetiminde ise kâğıtlar kısa olduğu için fark neredeyse yok (112,7 → 110,9,
%1,6). Yani uzun uç geri alımı, her 100 $ nominal borç için yalnızca ~65–87 $ nakit
gerektiriyor.

---

## 13. YAZI İÇİN İŞLENMİŞ ÖRNEK — "BİR OPERASYONUN ANATOMİSİ"

**18 Ağustos 2026, 20Y–30Y likidite desteği** (19 Ağustos duyurusundan bir gün önce):

| Adım | Veri |
|---|---|
| Duyuru (ön) | 17.08.2026, 11:00 ET — muhtemel uygun CUSIP listesi |
| Duyuru (nihai) | 18.08.2026, 11:00 ET — 36 uygun CUSIP |
| Vade aralığı | 15.11.2046 – 15.05.2056 |
| Operasyon penceresi | 18.08.2026, 13:40–14:00 ET, FedTrade |
| Asgari teklif / kat | 1.000.000 $ |
| Menkul kıymet başına azami teklif | 9 |
| Fiyat formatı | 100 $ nominal başına fiyat |
| Azami itfa tutarı | 2.000.000.000 $ |
| **Toplam teklif** | **19.868.000.000 $** → teklif/azami **9,93×** |
| **Kabul edilen** | **2.000.000.000 $** (%100 doluluk), **3 CUSIP** |
| Kabul edilenler | 912810SC3 %3,125 05/2048 → 1.000 mn $ @ 71,469 · 912810SU3 %1,875 02/2051 → 175 mn $ @ 52,375 · 912810SX7 %2,375 05/2051 → 825 mn $ @ 59,070 |
| **[HESAP]** Ağırlıklı ortalama fiyat | **64,684** |
| **[HESAP]** Ödenen temiz nakit | **≈1,294 mia $** (+ birikmiş faiz) |
| **[HESAP]** Söndürülen nominal borç | **2,000 mia $** |
| **[HESAP]** Çekilen DV01 | **≈1,96 mn $/bp** ≈ 2,5 mia $ 10Y eşdeğeri |
| Takas | 19.08.2026 (T+1), ABA 021089482 US TREAS BUYBACK/6000 |

Anlatı: Hazine 20 milyar dolarlık teklif aldı, 2 milyar dolarlık kapasitesini doldurdu,
36 uygun kâğıdın yalnızca 3'ünü — en derin iskontolu, en düşük kuponlu, en uzun
duration'lı olanları — aldı. Nominalde 2 milyar dolar borç söndü, kasadan 1,3 milyar
dolar çıktı. Aradaki 0,7 milyar dolar, 2020–2021'in %1,875 kuponlu tahvillerini bugünkü
%5,4 getiri ortamında geri almanın aritmetiğidir. Ertesi gün Hazine, bu operasyonun
büyüklüğünü ikiye katlayacağını duyurdu.

- Kaynak: TreasuryDirect, BBR_20260818174000.xml / .pdf, 18.08.2026; hesaplar benim.

---

## 14. YAZAR İÇİN KRİTİK NÜANSLAR (kaynaklı)

1. **"Geri alım QE değildir" doğru ama yarım doğrudur.** Bilanço ve rezerv yaratma
   açısından kesinlikle QE değil. Ama duration açısından mini-Twist'tir. Yazı bunu
   söylemezse teknik okuyucu yakalar. Ölçek farkı iki büyüklük mertebesi.
2. **"En az 4 milyar dolar" bir taban, tavan değil.** Hazine üst sınırı belirtmedi.
3. **9 Eylül bir nakit yönetimi operasyonu günüdür**; ilk etkilenen uzun uç operasyonu
   **10 Eylül**'dür.
4. **Uzun uç operasyonlarında 36 uygun kâğıttan 2–3'ü alınıyor.** Bu, "Hazine uzun ucu
   destekliyor" anlatısını ciddi biçimde niteler: Hazine yalnızca en ucuz birkaç
   iskontolu kâğıdı alıyor, eğriyi geniş biçimde desteklemiyor.
5. **Net arz değişmiyor, kompozisyon değişiyor.** ODM'nin kendi finansman tablosu
   (Bulgu 5.2) bunu birebir gösteriyor: geri alım = ilave bono ihracı.
6. **Nominal ≠ nakit.** 100 $ nominal uzun tahvil ≈ 65 $ nakit. Bu, borç tavanı,
   nominal borç istatistikleri ve bono ihraç ihtiyacı hesapları için önemli.
7. **Program stres aracı değil.** Hazine bunu iki ayrı belgede açıkça yazıyor.
8. **SOMA, geri alımı kısıtlıyor** (%70 tavan, 10 mia $ serbest dolaşım tabanı) — QE'nin
   mirası bugünkü geri alım kapasitesini biçimlendiriyor.
9. **Büyük operasyon = büyük duration riski.** Temmuz 2024'te 7Y–10Y operasyonu getiri
   şoku nedeniyle sıfır alımla kapandı. 4 milyar dolarlık uzun uç operasyonları bu riski
   iki katına çıkarır.
10. **Belly ölü.** 7Y–10Y'de 9 operasyonda 34 mia $ kapasiteden yalnızca 3,7 mia $
    (%11) kullanıldı. Program eğri boyunca homojen değil.

---

## BULUNAMAYAN

1. **19 Ağustos 2026 sonrası güncellenmiş geçici geri alım takvimi.** Hazine "daha sonra
   yayımlanacak" dedi; 24.08.2026 itibarıyla yayımlanmış bir güncel takvim bulamadım.
   Dolayısıyla operasyon sayısının değişip değişmeyeceği, diğer kovaların kısılıp
   kısılmayacağı ve çeyreklik likidite desteği tavanının resmî yeni değeri (38 mia $
   mı kalacak, 52 mia $'a mı çıkacak) **bilinmiyor**. Bulgu 9.2'deki 52 mia $ benim
   varsayımsal hesabımdır.
2. **10Y–20Y ve 20Y–30Y için yeni operasyon başına azami tutarın üst sınırı.** "En az
   4 milyar dolar" deniyor; fiilî tavan açıklanmadı.
3. **9 Eylül 2026 sonrası fiilî operasyon sonuçları.** Derleme tarihinde henüz
   gerçekleşmemiş.
4. **Hazine'nin teklif kabul kriterlerinin resmî formülü.** Hazine hiçbir zaman hangi
   teklifi neden kabul ettiğinin kriterlerini kamuya açmadı; 2000 döneminde de açmamıştı
   (Garbade & Rutherford 2007, dipnot 23). "Cari piyasa fiyatlarına yakınlık ve göreli
   değer ölçütleri" ifadesinden ötesi yok. Merrick (2005), Hazine'nin göreli pahalı
   tahvilleri almaktan genel olarak kaçındığı ama alımlarını göreli ucuz tahvillerle
   sınırlamayı başaramadığı sonucuna varmış (birincil kaynağı okumadım, TBAC/NY Fed
   üzerinden aktarım).
5. **Genişletilmiş karşı taraf listesindeki kurumların isimleri ve sayısı.** Kriter
   (35 mia $ eşiği) yayımlanmış, liste kamuya açık değil.
6. **2026 operasyonlarının piyasa değeri (market value) toplamları.** TBAC 3Ç2025 bu
   veriyi 22.07.2025'e kadar veriyor; sonraki dönem için CUSIP bazında ağırlıklı ortalama
   fiyatlardan tek tek hesaplanabilir ama toplu bir birincil tablo bulamadım. 18.08.2026
   operasyonu için kendim hesapladım (Bulgu 5.3).
7. **Hazine'nin 4 Kasım 2026 refinansmanına dair herhangi bir ön işaret.** Yalnızca
   "daha fazla bilgi orada verilecek" deniyor.
8. **Geri alımın on-the-run/off-the-run spread'i üzerindeki nedensel etkisinin
   ekonometrik ölçümü.** TBAC korelasyonel gözlemler sunuyor (RMSE düşüşü, ASW
   diferansiyeli), ama nedensellik tahmini yapan bir Fed çalışma kâğıdı bulamadım.
9. **20.08.2026 itibarıyla ABD pazarlanabilir borcunun WAM'ı.** ODM 3Ç2026 raporunda
   grafik olarak var, metinde sayı olarak çıkarılamadı. Elimdeki en yakın birincil
   çıpalar: 30.06.2025 itibarıyla 28,6 tn $ pazarlanabilir borç ve **72 ay WAM**
   (TBAC 29.07.2025, s. 6 dipnot); 31.07.2026 itibarıyla bono stoğu ~7,0 tn $ ve bono
   payı **%22,2** (ODM 3Ç2026, s. 22) — buradan pazarlanabilir borç **[HESAP]** ≈ 31,5 tn $.
10. **NY Fed'in "Treasury Debt Auctions and Buybacks as Fiscal Agent" sayfası.**
    HTTP 403 döndü, erişilemedi. İçeriğinin büyük kısmı 31 CFR 375 ve TreasuryDirect
    FAQ'tan zaten karşılandı.

---

## KAYNAK LİSTESİ (tam)

**Birincil — Hazine**
1. Treasury, "Treasury Announces Increased Sizes of Nominal Long-End Liquidity Support
   Buybacks Beginning September 9", sb0607, 19.08.2026.
   https://home.treasury.gov/news/press-releases/sb0607
2. Treasury, "Quarterly Refunding Statement of Deputy Assistant Secretary for Federal
   Finance Brian Smith", sb0590, 05.08.2026.
   https://home.treasury.gov/news/press-releases/sb0590
3. Treasury QRS, sb0212, Temmuz 2025 (karşı taraf genişletme duyurusu).
   https://home.treasury.gov/news/press-releases/sb0212
4. Treasury, "Tentative Schedule of Treasury Buyback Operations — August 2026 Quarterly
   Refunding", 05.08.2026.
   https://home.treasury.gov/system/files/221/Tentative-Buyback-ScheduleQ32026.pdf
5. ODM, "Regular Treasury Buyback Program Details", Nisan 2024.
   https://home.treasury.gov/system/files/221/TreasurySupplementalQ22024.pdf
6. ODM, "Treasury's Current Views on the Operational Design of a Regular Buyback
   Program", Ağustos 2023.
   https://home.treasury.gov/system/files/221/TreasurySupplementalQRQ32023.pdf
7. ODM, "Review of Treasury Buyback Results", 29.10.2024.
   https://home.treasury.gov/system/files/221/TreasurySupplementalQ42024.pdf
8. ODM, "Treasury Presentation to TBAC — Fiscal Year 2026 Q3 Report", Temmuz 2026.
   https://home.treasury.gov/system/files/221/TreasuryPresentationToTBACQ32026.pdf
9. TreasuryDirect, "FAQs about Treasury Securities Buybacks" (erişim 23–24.08.2026).
   https://www.treasurydirect.gov/help-center/faqs/buyback-faqs/
10. TreasuryDirect, "Treasury Buyback Announcements & Results".
    https://www.treasurydirect.gov/auctions/announcements-data-results/buy-backs/
11. TreasuryDirect, operasyon sonuçları BBR_20260818174000.xml / .pdf, 18.08.2026.
12. Treasury Fiscal Data, `buybacks_operations` veri seti (API), çekim 24.08.2026.
    https://fiscaldata.treasury.gov/datasets/treasury-securities-buybacks/

**Birincil — TBAC**
13. TBAC, "Treasury Buyback Program Enhancements", 29.07.2025.
    https://home.treasury.gov/system/files/221/TBACCharge1Q32025.pdf
14. TBAC, "Treasury Buyback Program Effectiveness Assessment", 04.02.2025.
    https://home.treasury.gov/system/files/221/TBACCharge1Q12025.pdf
15. TBAC, "Considerations for Designing a Regular and Predictable Treasury Buyback
    Program", 1Ç2023.
    https://home.treasury.gov/system/files/221/TBACCharge1Q12023.pdf
16. TBAC, "Revisiting Treasury Buybacks", 3Ç2022.
    https://home.treasury.gov/system/files/221/TBACCharge2Q32022.pdf

**Birincil — Federal Register / mevzuat**
17. Treasury/Fiscal Service, "Marketable Treasury Securities Redemption Operations",
    Final Rule, 91 FR 15540, yayım ve yürürlük 30.03.2026, belge 2026-06070, 31 CFR 375.
    https://www.federalregister.gov/documents/2026/03/30/2026-06070/marketable-treasury-securities-redemption-operations
18. 31 U.S.C. §3111 (yasal yetki; 31 CFR 375.0 içinde aktarılmış).
19. Federal Register, "Marketable Treasury Securities Redemption Operations; Final Rule",
    19.01.2000 (çoklu fiyat formatının gerekçesi; Garbade & Rutherford üzerinden).

**Birincil — Federal Reserve / NY Fed**
20. Kenneth D. Garbade & Matthew Rutherford, "Buybacks in Treasury Cash and Debt
    Management", FRBNY Staff Report no. 304, Ekim 2007.
    https://www.newyorkfed.org/research/staff_reports/sr304.html
21. Federal Reserve Board, "Maturity Extension Program and Reinvestment Policy".
    https://www.federalreserve.gov/monetarypolicy/maturityextensionprogram.htm
22. Federal Reserve Board, FOMC basın bülteni 21.09.2011 (MEP duyurusu).
    https://www.federalreserve.gov/newsevents/pressreleases/monetary20110921a.htm
23. Federal Reserve Board, "Timeline: Balance Sheet Policies".
    https://www.federalreserve.gov/monetarypolicy/timeline-balance-sheet-policies.htm
24. Federal Reserve Board, H.4.1 "Factors Affecting Reserve Balances", 20.08.2026.
    https://www.federalreserve.gov/releases/h41/current/
25. NY Fed, "Statement Regarding Reserve Management Purchases Operations", 10.12.2025.
    https://www.newyorkfed.org/markets/opolicy/operating_policy_251210a
26. NY Fed, "FAQs: Reserve Management Purchases and Reinvestment Purchases".
    https://www.newyorkfed.org/markets/reserve-management-reinvestment-purchases-faq
27. NY Fed, Roberto Perli, "Reflections on the Early Days of Reserve Management Purchases
    and the Maintenance of Ample Reserves", 26.03.2026.
    https://www.newyorkfed.org/newsevents/speeches/2026/per260326

**Erişilemeyen**
28. NY Fed, "Treasury Debt Auctions and Buybacks as Fiscal Agent" — HTTP 403.
    https://www.newyorkfed.org/markets/treasury-debt-auctions-and-buybacks-as-fiscal-agent
