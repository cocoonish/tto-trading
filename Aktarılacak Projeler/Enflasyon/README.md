# Enflasyon panosu — veri hattı

Panonun merkezinde **yıllık enflasyon değil, momentum** var: mevsimsellikten
arındırılmış aylık değişimin **3 ve 6 aylık yıllıklandırılmış** hâli (SAAR),
12 aylık oranın yanında. Yıllık oran, momentumun 12 aylık hareketli
ortalamasıdır; bugünkü fiyatlama davranışını bir yıl geriye yayar ve dönüşleri
geç gösterir.

Kaynak: **TCMB EVDS3** (`evds3.tcmb.gov.tr/igmevdsms-dis`). Tek dış bağımlılık
budur; başka portal, PDF ya da elle bakımlı tablo yoktur.

## Koşma sırası

```bash
python3 veri.py          # EVDS → data/aylik.csv, data/gunluk.csv, data/agac.csv
python3 metrik.py        # hesaplar → data/*.csv, data/*.json, uyarilar.json
python3 grafik.py        # 9 şekil → cikti/NN_*.html + cikti/yukseklikler.json
python3 ozet_uret.py     # ozet.json (sayfa metnindeki oynak sayılar)
```

Kök dizinden tek komutla: `python3 guncelle.py enflasyon`
(ev stili — `site/tools/plotly_stil.py` — koşunun sonunda kendiliğinden uygulanır).

`python3 veri.py --yenile` önbelleği yok sayıp EVDS'e gider.

## EVDS anahtarı

Kaynak koda **gömülmez**. Arama sırası:

1. `TTO_EVDS_KEY` ortam değişkeni (CI'da depo secret'ı)
2. `<proje>/.evds_key`
3. `<kök>/.evds_key`
4. `<kök>/Aktarılacak Projeler/TCMBNetRezerv/.evds_key` (kardeş proje)

Bu projeye `.evds_key` **kopyalanmaz**; kardeş projedeki dosya okunur.

## Ne hesaplanıyor

| Konu | Nerede | Not |
|---|---|---|
| 3a / 6a SAAR (zincir) | `metrik.saar` | `(P_t/P_{t−n})^(12/n) − 1`; üs `12/n`, `n/12` değil |
| Aritmetik ve basit yıllıklandırma | `metrik.saar_aritmetik`, `saar_basit` | yalnız karşılaştırma; **basit ölçekleme ana seri olarak kullanılmaz** |
| ECB tipi 3a/3a momentum | `metrik.ecb_momentum` | üç aylık hareketli ORTALAMALARIN oranı — daha az oynak, ~1,5 ay daha gecikmeli |
| Mevsimsellikten arındırma | `metrik.arindir` | hareketli tatil ön-arındırması → `STL(log, period=12, seasonal=13, robust)` |
| Hareketli dinî tatil regresörü | `metrik.tatil_regresorleri` | aritmetik Hicri takvim; uzun dönem ay ortalamasıyla merkezlenir (Census `genhol` mantığı) |
| Ağırlık tahmini | `metrik.agirlik_tahmini` | zincir-Laspeyres kimliğinden kısıtlı EKK (EVDS ağırlık yayımlamıyor) |
| Etkin ağırlık ω | `metrik.etkin_agirlik` | `w_i·(P_{i,t−1}/P_{i,Ara})` normalize; yıl başı ağırlığı **kullanılmaz** |
| Katkı ayrıştırma | `metrik.katki_hesapla` | aylık tam (`Σ C = π`), yıllık ileriye bileşiklenmiş |
| Kırpılmış ortalama / medyan | `metrik.kirpilmis`, `agirlikli_medyan` | α ∈ {0,05; 0,08; 0,10}; 43–45 üç haneli COICOP grubu |
| Difüzyon | `metrik.difuzyon` | üç eşik: %0, hedefle uyumlu tempo, manşetin kendisi |
| Baz etkisi patikası | `metrik.baz_patikasi` | üç senaryo; "geçen yıl tekrar" senaryosu yıllığı sabit bırakır (kendini doğrulama) |
| Beklenti isabeti | `metrik.beklenti_isabeti` | MAE / yanlılık / RMSE, h = 0,1,2 ay, 36 ve 60 aylık pencere |
| Reel faiz | `metrik.reel` | **tam Fisher**; `i − π` yaklaşımı kullanılmaz |
| Hizmet ataleti | `metrik.atalet_olc` | 36 aylık yuvarlanan AR(1) katsayısı ρ |
| İTO nowcast | `metrik.ito_nowcast` | katsayı her koşuda yeniden tahmin edilir, koda gömülmez |

## Yöntem kararları ve gerekçeleri

**Zincir yıllıklandırma.** Basit ölçekleme (12 × ortalama aylık) Temmuz 2026'da
3 aylıkta 1,5, 6 aylıkta 3,6 puan sapıtıyor; kullanılmıyor. Zincir ile
aritmetik-ortalama-sonra-bileşikle fark 0,01–0,08 puan — zincir seçildi çünkü
doğrudan endeks düzeyinden gelir ve "bu tempo 12 ay sürerse" ifadesinin tam
karşılığıdır.

**Arındırma pazarlık konusu değil.** Temmuz 2026'da ham 3 aylık SAAR %19,49,
arındırılmış %30,62 — 11,1 puan fark. Ham 3 aylık SAAR yalnızca "hangi üç ay
pencereye düştü" sorusunu ölçer.

**Neden STL, neden X-13 değil.** TÜİK'in resmî arındırılmış TÜFE'si EVDS'te
**yok** (52.694 seri tarandı; arındırılmış olarak yayımlananlar yalnız GSYH,
sanayi üretimi, işgücü, KKO, güven endeksleri). X-13ARIMA-SEATS ise `x13as`
ikili dosyasına bağımlı; cron/CI ortamında sessiz kırılma riski taşıyor.
Sayfada "TCMB'nin arındırılmış serisi" **denmez**, "bu çalışmanın STL
arındırması" denir. `ozet.json`'da `sa_yontem` alanı bunu taşır.

**Mevsimsellik anlamlılık sınaması.** Δln P üzerinde 11 ay kuklasının F testi,
**önce trend alınarak** (13 aylık ortalanmış hareketli ortalama çıkarılarak)
koşuluyor. Ham Δln P ile test gücü çöküyordu: aylık enflasyonun ortalaması
2005–2026 boyunca %0,5 ile %5 arasında gezindiği için ay kuklaları bu
sürüklenmeyle yarışıyordu (çekirdek B: ham p = 0,15 → trendden arındırılmış
p = 0,002). Anlamsız çıkan seri **arındırılmadan** geçirilir ve tanıya
işaretlenir — bu koşuda işlenmiş gıda (p = 0,29) ve Yİ-ÜFE (p = 0,52) öyle;
TCMB de Aralık 2024 notunda işlenmiş gıda için aynı notu düşmüştü.

**Ağırlıklar tahmin ediliyor — ve bağımsız olarak doğrulanıyor.** EVDS ağırlık
yayımlamıyor. TÜFE yıl içinde bir önceki yılın Aralık'ını temel alan zincir
Laspeyres olduğu için

```
P_t / P_Ara,y−1 = Σ_i w_i^y · (P_it / P_i,Ara,y−1)
```

kimliği w üzerinde tam doğrusaldır: yıl içindeki her ay bir denklem, Σw = 1 bir
kısıt. Aşırı belirlenmişse EKK; cari yılda ay sayısı yetmezse kimlikler tam
sağlanacak biçimde önceki yılın ağırlıklarından en az sapan çözüm seçilir.
Yöntemin bağımsız sınavı: 2026 için hizmet ağırlığında **+7,5**, enerjide
**−3,2**, temel malda **−2,9** puanlık değişim buluyor — TCMB Blog'un
yayımladığı **+7,4 / −3,2 / −3,0** ile örtüşüyor. Kimlik artığı eşiği
(0,05 puan) aşarsa hat **DURUR** (`metrik.py` `SystemExit`) — sessizce yanlış
ağırlıkla katkı yayımlanmaz.

**Doğrudan mı dolaylı mı arındırma.** Genel endeks **doğrudan** arındırılır;
katkı ve dağılım hesabındaki alt kalemler **kendi içlerinde** arındırılır.
Bu bir tutarsızlıktır ve bilerek yazılmıştır (dolaylı toplam, doğrudan
arındırılmış manşetle birebir örtüşmez).

## Sessiz bayatlamaya karşı denetimler

1. **`son_ay()` veriden okunur.** Hiçbir modülde sabit tarih yok.
2. **Aile bazlı tazelik.** TÜFE/ÖKTG/Yİ-ÜFE ayın 3'ünde, PKA cari ay ikinci
   yarısında, YKKE ay ortası, İTO ayın ilk günleri, faiz iş günü. Tek eşik her
   ay yanlış alarm üretirdi (`veri.TAZELIK`).
3. **EVDS `LAST_UPDATED` alanı tazelik ölçüsü DEĞİLDİR** — tuzaktır. Ölçüldü:
   `bie_tukfiy2025` verisi 07.2026'da biterken alan 22.04.2026 diyor. Tazelik
   yalnız son dolu gözlemden okunur.
4. **Çapraz doğrulama (formül/kolon hizalaması), hattı DURDURUR.** Endeksten
   hesapladığımız 12 aylık değişim, EVDS'in kendi `formulas=3` çıktısıyla
   0,05 puan içinde tutmalı; tutmazsa `metrik.py` `SystemExit` ile düşer.
   Aylık için eşik 0,01 puan (uyarı). Bu koşuda iki ölçüde de fark
   **0,000 puan** (36 aylık örtüşme).
   **NE ÖLÇMEZ:** bayatlık. EVDS'in formül çıktısı bizim serimizin sunucu
   tarafındaki dönüşümüdür ve kıyas yalnız kesişen tarihlerde yapılır; endeks
   3 ve 6 ay bayatlatılarak sınandı, maks fark yine 0,000000 puan. Tazelik
   denetimi `veri.tazelik_denetimi`'dir (madde 2). Tek tazelik katkısı:
   pencere KOŞUM GÜNÜNDEN türetilir ve EVDS bizden ileri bir ay döndürürse
   görünür uyarı düşer.
5. **Yapısal denetimler.** `TP.FE25.OKTG01` ile `TP.TUKFIY2025.GENEL` birebir
   aynı olmalı; PKA katılımcı sayısı 12 aylık ortalamanın %75'inin altına
   düşerse uyarı; katkı toplamı manşetten 0,02 puandan fazla sapamaz.
6. **Ölü alt kalem denetimi.** Üç haneli grupların son gözlem ayı genel
   endeksle karşılaştırılır. Bu koşuda `095` (Kültürel mallar) ve `105`
   (Seviyeye göre tanımlanamayan eğitim) 12.2025'te bitiyor — sınıflama
   değişiminde düşen kalemler. Güncel kesitten çıkarılır, yaşadıkları
   yılların ağırlık tahmininde korunur, ω yeniden ölçeklenir.
7. **Arındırma revizyonu VINTAGE testiyle ölçülür.** `vintage_revizyon()`
   her seri için k = 1…6 ay keser, `arindir()`'i YENİDEN koşar ve o ay "son ay"
   iken hesaplanmış olacak SA m/m ile 3a SAAR'ı bugünküyle karşılaştırır.
   Manşette maks 0,12 pp, hizmette 4,33 pp (3a SAAR'da 17,05 pp) — mertebe
   farkı serilere göre değişiyor, tek sayıyla geçilmiyor. Manşet 0,30 puanı
   aşarsa uyarı düşer.
   `kosular_arasi_izi()` ayrıca önceki koşunun SA serisini `data/sa_onceki.csv`
   ile kıyaslar; bu bir REVİZYON ÖLÇÜSÜ DEĞİLDİR: aynı veriyle koşulduğunda
   yapısal olarak 0 çıkar. O yüzden içerik bayt-bayt aynıysa `var=False`
   işaretlenir ve `ozet.json`'a sayı YAZILMAZ (0,00 basmak sahte güvenceydi).
8. **TTL'li önbellek.** Seri verisi 12 saat, seri kataloğu 168 saat. Ağ
   düşerse eski önbelleğe düşülür ama **sessiz kalınmaz**: uyarı basılır ve
   `uyarilar.json`'a yazılır.
9. **Eksik figür hattı DURDURUR.** `grafik.py` dokuz şekilden biri üretilemezse
   çıkış kodu 1 verir. Bu olmadan `cp cikti/*.html` var olan (eski) dosyaları
   kopyalayıp başarıyla biterdi: grafik bayat, metin taze. Cron'da ikinci
   savunma olarak dosya sayısı da denetlenir.
10. **Yükseklik denetimi.** `guncelle.py:yukseklik_denetimi()` `yukseklikler.json`
   ile MDX'teki `yukseklik={}` değerlerini kıyaslar; sapmada görünür uyarı.

## Çıktılar

```
data/aylik.csv          70 aylık seri (TÜFE ağacı, ÖKTG, beklentiler, YKKE, İTO)
data/gunluk.csv         AOFM, TLREF (iş günü, yıllık parçalarla çekilir)
data/agac.csv           bie_tukfiy2025 kataloğu (349 seri, SEVIYE/UST_SERIE_CODE)
data/metrik.csv         seri × ay × (m/m, SA m/m, 3a/6a SAAR ham & SA, 12a, ECB)
data/sa.csv             arındırılmış endeks düzeyleri
data/sa_tani.json       arındırma tanıları: ana seriler + `alt_kalemler` (45 grubun
                        mevsimsellik p'si, tatil t/katsayıları, kesit yoğunlaşması,
                        medyan kalemi sıklığı) + `vintage` + `kosular_arasi`
data/alt_kalem.csv      kesitin 45 üç haneli grup endeksi (dağılım ölçüleri
                        önbelleğe bağlı kalmadan denetlenebilsin)
data/agirlik.json       tahmin edilen ağırlıklar (katkı grupları, ana gruplar, alt kesit)
data/katki.csv          aylık ve yıllık katkılar + artıklar
data/dagilim.csv        kırpılmış ortalama, medyan, difüzyon
data/baz_senaryo.csv    12 aylık üç senaryo patikası
data/reel_faiz.csv      dört reel faiz ölçüsü
data/beklenti.json      PKA isabet ölçüleri
data/ito_profil.json    İTO–TÜFE farkı: ay ay tablo, t sınaması, eğim=1 sınaması,
                        koşullu eşleme (öngörü aralığı), altı kurallık örneklem
                        DIŞI yarış + dayanıklılık, PKA anketiyle eşli kıyas,
                        sürpriz regresyonu, kayan kararlılık, yıllık makas
cikti/NN_*.html         12 şekil (ev stili, plotly.js CDN'den); 10–12 İTO kanadı
                        ve KOŞULLU: ito_profil.json yoksa üretilmez, eski
                        kopyaları hem cikti'den hem siteden silinir, hat durmaz
cikti/yukseklikler.json şekil yükseklikleri — MDX'teki yukseklik={} ile aynı kaynak
ozet.json               sayfa metnindeki oynak sayılar (~405 anahtar; 109'u itp_*)
uyarilar.json           tazelik/kaynak/denetim uyarıları + çapraz doğrulama sonucu
```

## Şekiller

| # | Dosya | Panel | Yükseklik |
|---|---|---|---|
| 01 | `01_manset_momentum.html` | 2 (yakın plan + tam tarihçe) | 1009 |
| 02 | `02_cekirdek_momentum.html` | 2 (B, C) | 959 |
| 03 | `03_arindirma.html` | 2 (aylık ham/SA, 3a ham/SA) | 1009 |
| 04 | `04_katki.html` | 2 (yıllık, aylık) | 1035 |
| 05 | `05_dagilim_difuzyon.html` | 2 (kırpma-medyan, difüzyon) | 1033 |
| 06 | `06_hizmet_mal.html` | 3 (12a, momentum, ρ) | 1349 |
| 07 | `07_beklenti.html` | 3 (üç kesim, PKA ufukları, isabet) | 1373 |
| 08 | `08_reel_faiz.html` | 2 (reel, nominal) | 1057 |
| 09 | `09_baz_etkisi.html` | 2 (patika, düşen aylar) | 1059 |
| 10 | `10_ito_tufe.html` | 3 (aylık okuma, fark, yıllık makas) | 1349 |
| 11 | `11_ito_kural.html` | 3 (eşleme, kural yarışı, sürpriz) | 1349 |
| 12 | `12_ito_takvim.html` | 2 (takvim ayı, kayan kararlılık) | 985 |

Yükseklikler `cikti/yukseklikler.json`'dan okunmalı; tablo koşum başına
değişebilir (alt başlık satırı ve lejant satırı sayısına bağlı).

**Neden dipnot grafiğin içinde değil:** `site/tools/plotly_stil.py` her HTML'e
çalışma zamanında `legend.y = −0,1` ve `margin.b = 110` dayatıyor, Plotly de
taşan lejantı figürün alt kenarına kenetliyor. Sabit konumlu dipnot ek
açıklaması uzun figürlerde lejantın üstüne biniyordu. Açıklama satırları bu
yüzden **başlık bloğunda** (`<sup>`) taşınıyor: ev stili başlıktaki her `<br>`
için üst marjı 26 px büyütüyor, çakışma imkânsız. (Aynı sebeple `margin.t`
bilerek gerekenden 1 px eksik yazılıyor — ev stili yalnız "mevcut değer
gerekenden küçükse" yükseltiyor.)

## Bilinen sınırlar

1. **Ağırlıklar TAHMİNDİR, TÜİK'in yayımladığı sayılar değildir.** Kimlik
   artığı 0,002 puan mertebesinde ve TCMB'nin duyurduğu 2026 kayması birebir
   yeniden üretiliyor; yine de bunlar bir çıkarımdır. Ana grup düğümü bir tam
   yılda **tam belirlenmiştir** (12 denklem + Σw = 1, 13 bilinmeyen) — artığı
   sıfır çıkar, bu bir doğrulama değildir. Alt düğümler aşırı belirlenmiştir
   ve artıkları anlamlıdır.
2. **X-13ARIMA-SEATS kurulu değil.** STL ile X-13 arasındaki 3 aylık SAAR farkı
   ölçülmedi. TCMB kendi yayınlarında X-13 kullanıyor; bizim sayımız TCMB'nin
   yayımladığı arındırılmış sayıyla birebir tutmayabilir.
3. **Arındırma geçmişi değiştirir.** Yeni ay eklendiğinde filtre yeniden koşar,
   son 6–12 gözlemin SA aylık değişimleri revize olur (uç nokta sorunu).
   Grafiklerde son 3 nokta içi boş çizilir. Bu bizim ürettiğimiz bir
   revizyondur — TÜFE endeksinin kendisi revize edilmez.
4. **Hareketli tatil düzeltmesi ön aşamadadır, RegARIMA değildir.** Hicri takvim
   aritmetik (tabular) yaklaşımla üretiliyor; Diyanet'in rasat tabanlı
   ilanından ±1 gün sapabilir. Genel endekste hiçbir tatil regresörü
   |t| > 1,96 eşiğini geçmedi (ters yönlü kalemler birbirini götürüyor);
   alt kalemlerde geçenler tanıya yazılıyor.
5. **Kırpma seviyesi keyfîdir.** α = 0,05 / 0,08 / 0,10 birlikte verilir;
   aradaki bant ölçü belirsizliğinin görsel ifadesidir. Kırpılmış ortalamanın
   sağa çarpık dağılımdan gelen negatif yanlılığı **düzeltilmez**, ayrı
   gösterge olarak raporlanır.
6. **Alt kesit üç haneli düzeydedir** (43–45 grup), beş haneli 188 temel başlık
   değil. Sebep: TÜİK'in kendi duyurusu 2026 sınıflama değişiminde "bazı alt
   endekslerde farklılık görülebilir" diyor; 4–5 haneli düzeyde geriye dönük
   kıyas güvenli değil.
7. **İTO regresyonu n = 30.** 2024 öncesi İstanbul TÜFE (2023=100) yok. İTO
   aynı ayın nowcast'idir, **gelecek ayın öncüsü değildir** (bir ay önceden
   korelasyon ≈ 0); zamanda kaydırılmış "öncü gösterge" çizimi yanlış olur.
8. **Yapışkan/esnek fiyat ayrımı yapılmadı.** TÜİK madde düzeyinde fiyat
   değiştirme sıklığı mikro verisi yayımlamıyor; Bils–Klenow tipi sınıflama
   replike edilemez.
9. **Asgari ücret EVDS'te yok** ve bu hatta kapsam dışıdır.
10. **PKA faiz beklentisi serilerinin bir kısmı durmuş görünüyor**
    (`TP.PKAUO.S04.A.U` son gözlem 05.2025). Kullanılan `TP.PKAUO.S04.D.U`
    (12 ay sonrası) canlı; tazelik denetimi bunu izliyor.
