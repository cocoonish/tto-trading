# TCMB Fonlama & Likidite — veri hattı

Site sayfası: `site/src/content/projeler/fonlama-likidite.mdx`
Web çıktısı: `site/public/projeler/fonlama-likidite/`
Kök hat adı (`guncelle.py`): **`fonlama`**

Bu hat, TCMB'nin TL likiditesini **hangi fiyattan** ve **hangi kanaldan**
yönettiğini ölçer: faiz koridoru ve politika faizi, fiilî fonlama maliyeti
(AOFM), fazla likidite rejiminde onun aynası olan sterilizasyon maliyeti
(AOSM — bu çalışmanın türetmesi), TLREF, net açık piyasa fonlaması ve
kompozisyonu, swap stoku, zorunlu karşılık tesisi ve bunların kredi/mevduat
faizine geçişkenliği.

---

## Koşum

```bash
python3 veri.py        # EVDS3 → data/gunluk.csv, haftalik.csv, aylik.csv
python3 metrik.py      # → data/metrik.csv, zk.csv, haftalik_metrik.csv, uyarilar.json
python3 grafik.py      # → cikti/NN_*.html + cikti/yukseklikler.json
python3 ozet_uret.py   # → ozet.json
```

Sıra **bağlayıcıdır**: sonraki adım öncekinin CSV'sini okur. Kök dizinden tek
komutla: `python3 guncelle.py fonlama`.

Ev stili (grafikler siteye kopyalandıktan sonra):

```bash
cd site && python3 tools/plotly_stil.py public/projeler/fonlama-likidite/*.html
```

### Bağımlılıklar

`requirements.txt`: pandas, numpy, plotly. **statsmodels gerekmez** —
yuvarlanan regresyon `numpy.linalg.lstsq` ile kuruluyor.

### EVDS anahtarı

Kaynak koda **gömülmez**. Arama sırası (`veri.py` bu sırayı uygular):

1. `TTO_EVDS_KEY` ortam değişkeni (CI'da depo secret'ı)
2. `Aktarılacak Projeler/Fonlama/.evds_key`
3. `TTO Trading/.evds_key`
4. kardeş `Aktarılacak Projeler/TCMBNetRezerv/.evds_key`

Bu projeye anahtar **kopyalanmaz**; kardeş dosyadan okunur.

---

## EVDS3 erişimi — tuzaklar

`evds2.tcmb.gov.tr/service/evds` **ölüdür**. Çalışan uç nokta:

```
https://evds3.tcmb.gov.tr/igmevdsms-dis/series={KOD}&startDate=DD-MM-YYYY&endDate=DD-MM-YYYY&type=json
Başlık:  key: <ANAHTAR>          ← anahtar URL'de DEĞİL
```

| Tuzak | Ne oluyor | Hattın çözümü |
|---|---|---|
| **1000 satır sınırı** | EVDS aralığın **sonundan geriye** dolduruyor, gerisini uyarı vermeden kırpıyor | iş günü serileri 366 günlük, haftalık seriler 900 haftalık parçalar hâlinde çekiliyor |
| Satır sınırı **seri sayısına bağlı değil** | `series=A-B-C` tek istekte üç seri getiriyor, satır sayısı değişmiyor | seriler 6'lı demetler hâlinde çekiliyor (720 istek yerine ~110) |
| Bir demette bozuk kod | EVDS bütün isteği reddediyor | demet düşerse seriler tek tek deneniyor, düşen seri adıyla raporlanıyor |
| Üç ayrı tarih biçimi | İŞ GÜNÜ/HAFTALIK `20-08-2026`, AYLIK `2026-6`, ÜÇ AYLIK `2026-Q2` | ayrı ayrıştırıcılar; üç aylık biçim bu hatta kullanılmıyor ama tuzak `veri.py`'de yazılı |
| `LAST_UPDATED` | metaveri kaydının güncellenme tarihi, **tazelik ölçüsü değil** | tazelik yalnız **son dolu gözlemden** okunuyor |
| Kur serisinin gecikmesi **−1 gün** | TCMB ertesi günün kurunu bir gün önce ilan ediyor | tazelik denetiminde negatif gecikme muaf; `son_gun()` çekirdeğine kur alınmıyor |

---

## Birimler — bu hattın en pahalı hata sınıfı

Bin TL ile milyon TL arasındaki bin katlık fark, trilyon TL ölçeğinde gözle
yakalanmaz. Dönüşüm **tek yerde** (`metrik.py`) yapılır.

| Seri ailesi | EVDS birimi | Grafikte |
|---|---|---|
| `TP.APIFON*` (fonlama, sterilizasyon, net) | **milyon TL** | milyar TL |
| `TP.AB.A*` (analitik bilanço) | **bin TL** | milyar TL |
| `TP.PPIBSM`, `TP.PPIGBTL` (sistem likiditesi) | **milyon TL** | milyar TL |
| `TP.PY.P07.*` (ihale kabul tutarları) | **bin TL** | milyon TL (AOSM ağırlığı) |
| `TP.SWAPTEKTAR.*` | **milyon USD** | milyar USD / milyar TL |
| `TP.TLDTHVADE.*`, `TP.ZORUNDTH.KB8` (ZK tabanı) | **bin TL** | milyar TL |
| `TP.PY.P0*` faizler, `TP.APIFON4`, `TP.BISTTLREF.ORAN` | **yüzde** | yüzde / puan |

---

## Seriler

### İş günü (gecikme 0–1 gün)

| Ad | Kod | İçerik |
|---|---|---|
| `fon_top` / `fon_ihale` / `fon_kot_repo` / `fon_kot_depo` / `fon_glp` | `TP.APIFON1.TOP` · `.IHA` · `.KOT.A` · `.KOT.B` · `.KOT.C` | fonlama bacağı (A) |
| `ste_top` / `ste_ihale` / `ste_kot` / `ste_liksen` | `TP.APIFON2.TOP` · `.IHA` · `.KOT` · `.LIK` | sterilizasyon bacağı (B); likidite senedi **14.03.2025**'te doğdu |
| `net_fonlama` / `aofm` | `TP.APIFON3` · `TP.APIFON4` | net fonlama (A−B) ve ağırlıklı ortalama fonlama maliyeti |
| `politika` | `TP.PY.P02.1H` | politika faizi = 1 hafta vadeli repo **satış** kotasyonu |
| `koridor_alt` / `koridor_ust` / `glp_satis` | `TP.PY.P01.ON` · `TP.PY.P02.ON` · `TP.PY.P02.LON` | koridor tabanı, tavanı, geç likidite penceresi |
| `tlref` / `bist_on` | `TP.BISTTLREF.ORAN` · `TP.AOFOBAP` | piyasa gecelik faizi ve bağımsız kontrolü |
| `sto_oni_*` / `sto_1hi_*` | `TP.PY.P06/P07.ONI` · `.1HI` | sterilizasyon ihalelerinin faizi ve kabul tutarı (AOSM girdisi) |
| `serbest_mevduat` / `gun_basi_likidite` | `TP.PPIBSM` · `TP.PPIGBTL` | sistem likiditesi |
| `ab_*` | `TP.AB.A02`–`A25` | analitik bilanço (rezerv para, emisyon, ZK bloke, APİ, kamu mevduatı) |
| `swap_*` | `TP.SWAPTEKTAR.*` | TCMB taraflı swap stokları, kanal kırılımı |
| `usdtry` | `TP.DK.USD.A.YTL` | swap stokunun TL karşılığı için |

### Haftalık (Cuma; faiz ailesi 6 gün, ZK tabanı 13 gün gecikmeli)

`TP.KTF17` ticari TL kredi · `TP.KTFTUK` tüketici · `TP.KTF10` ihtiyaç ·
`TP.KTF12` konut · `TP.TRY.MT06` TL mevduat · `TP.TRY.MT02` 3 aya kadar ·
`TP.TLDTHVADE.KB6/KB12/KB18` ve `TP.ZORUNDTH.KB7/KB8` ZK tabanı ·
`TP.KYBKATFON.KB1/KB6` katılım fonları.

Haftalık seriler **2013**'ten çekilir: 2005'ten çekilirse 1080 satır olur ve
EVDS 1000'de **serinin başını** sessizce kırpar.

### Aylık — yalnız doğrulama için

`TP.BISPOLFAIZ.TUR` (BIS derlemesi politika faizi) ·
`TP.API.REP.ORT.G1` / `TP.API.TREP.ORT.G1` (aylık APİ repo/ters repo faizi).
Bunlar **grafiğe girmez**.

---

## Metrikler ve formüller

### AOFM — ve tabanı yokken neden yayımlanmadığı

$$\text{AOFM}_t=\frac{\sum_{k\in\mathcal{A}}F_{k,t}\,i_{k,t}}{\sum_{k\in\mathcal{A}}F_{k,t}}$$

$\mathcal{A}$ **yalnız fonlama bacağıdır**; sterilizasyon paydaya girmez.
Fonlama sıfıra düşerse AOFM tanımsızdır — **ama EVDS o gün de bir sayı basar.**
Hat, fonlama tabanı 5 milyar TL'nin altındaki günleri `aofm_gecerli = false`
işaretler, temiz seriyi NaN yapar, grafikte çizmez ve sayfa metninde "fonlama
maliyeti" cümlesi kurulmaz. Bu, sessiz bayatlamanın **veri kaynağı tarafından
üretilen** biçimidir: seri taze, değer geçersiz.

### AOSM — bu çalışmanın türetmesi (TCMB serisi DEĞİL)

Fazla likidite rejiminde marjinal fiyatı sterilizasyon belirler:

$$\text{AOSM}_t=\frac{S^{\text{ONI}}_t\,i^{\text{ONI}}_t+\big(S^{\text{ihale}}_t-S^{\text{ONI}}_t\big)\,\bar{i}^{\text{1HI}}_{t,5}}{S^{\text{ihale}}_t}$$

Gecelik depo alım ihalesinin (ONI) vadesi bir gün olduğu için o günkü kabul
tutarı aynı zamanda o günkü **stoktur**; ihale yoluyla sterilizasyon stokunun
kalanı haftalık depo alım ihalesinden (1HI) gelir ve stokta ~5 iş günü kalır.
Kalan bacak bu yüzden son 5 iş gününün tutar-ağırlıklı 1HI faiziyle değerlenir.

**Varsayım ve ölçümü:** kalan bacağın tamamının 1HI olduğu varsayılıyor.
Denetim, `kalan ÷ günlük 1HI tutarı` oranını hesaplar; 5 civarında olmalıdır.
Oran 3–7 aralığının dışına çıkarsa **görünür uyarı** düşer.

### Marjinal TCMB faizi

| Rejim | Marjinal fiyat |
|---|---|
| `net_fonlama > 0` — sistem net **borçlu** | AOFM |
| `net_fonlama < 0` — sistem net **alacaklı** | AOSM |
| AOSM yok (09.05.2024 öncesi fazla likidite günleri) | TLREF, **vekil** olarak işaretli |

Vekil payı `metrik_ozet.json → rejim.marjinal_kaynak` altında sayılır; pay
yükselirse "TCMB'nin marjinal fiyatı" cümlesi zayıflar ve bu gizlenmez.

### Koridor konumu ve örtük sıkılaştırma

$$\text{konum}_t=\frac{i^{\text{gecelik}}_t-i^{\text{alt}}_t}{i^{\text{üst}}_t-i^{\text{alt}}_t}$$

0 = taban, 1 = tavan. **Kırpılmaz**: bandın dışına çıkması asıl anlatılacak
olgudur. Bir "örtük sıkılaştırma dönemi", AOFM'nin koridor tavanını en az
0,05 puan aşarak en az 5 iş günü sürmesidir.

### İma edilen efektif ZK oranı

$$\hat r_t=\frac{\texttt{TP.AB.A19}}{\texttt{TP.TLDTHVADE.KB6}+\texttt{TP.ZORUNDTH.KB8}}$$

**ZK oranları EVDS'te yayımlanmıyor.** Bu, tebliğdeki herhangi bir tek orana
eşit değildir: vade dilimlerine ve para cinsine göre farklı oranlar uygulanır
ve YP karşılıklar döviz olarak tutulabilir. Sayfada "gerçekleşmiş **tesis**
oranı" diye etiketlenir; "ZK oranı %X'e indirildi" cümlesi bu seriden
**türetilmez**, tebliğden okunur.

Ayrıca bloke hesap bir **basamak fonksiyonudur** (tesis dönemi iki hafta;
ölçülen medyan adım aralığı 14 gün): günlük farkını "günlük likidite etkisi"
saymak yanlıştır. Taban 13 gün gecikmeli geldiği için ileriye taşınır; taşıma
21 günü aşarsa oran **hesaplanmaz** (bayat paydayla oran basılmaz).

### Geçişkenlik

$$\Delta i^{\text{kredi}}_s=\alpha+\beta\,\Delta i^{\text{marjinal}}_{s-k}+\varepsilon_s$$

Haftalık farklar üzerinde 52 haftalık yuvarlanan EKK. Gecikme $k$, tam
örneklemde çapraz korelasyon taramasıyla seçilir (0–8 hafta).
**Nedensellik iddiası değildir**: aynı pencerede her iki seriyi de kur, risk
primi ya da PPK beklentisi besliyor olabilir.

---

## Denetimler — hangisi durdurur, hangisi uyarır

### Hattı DURDURANLAR (`metrik.py`, çıkış 1)

| Sınav | Eşik | Ölçülen |
|---|---|---|
| `TP.APIFON1.TOP − TP.APIFON2.TOP = TP.APIFON3` | 1e-6 mn TL | 1,2e-10 (n=3.928) |
| Günlük politika kotasyonunun ay sonu değeri ↔ EVDS'in **ayrı** yayımladığı aylık BIS serisi | 0,01 puan | **0,000 puan** (n=94 ay) |
| TLREF ↔ BİST gecelik repo ağırlıklı ortalama faizi | 1,00 puan | ort. 0,024 · maks 0,536 (n=1.889) |
| Bir figür üretilemezse (`grafik.py`) | — | siteye kopyalama yapılmaz |

### GÖRÜNÜR UYARI düşürenler (`uyarilar.json`)

- **Tazelik**, aile bazlı: APİ/kotasyon/likidite 4 gün · TLREF ve analitik
  bilanço 5 gün · haftalık faiz 12 gün · ZK tabanı 20 gün · kur muaf.
  Referans **duvar saatidir**; verinin kendi son gününü referans almak denetimi
  kendi kendine referanslı hâle getirirdi.
- **Kimlik**: `TP.AB.A24 / 1000 = −TP.APIFON3`. Son 250 iş gününde tipik APİ
  büyüklüğünün %1'ini aşarsa uyarı. Tam tarihçede kalıcı bir artık var ve bu
  **kapsam farkıdır** (bilançonun APİ kalemi işlemiş faizi de taşır) — hattı
  durdurmak yanlış alarm olurdu, o yüzden yalnız tanı olarak raporlanır.
- **Analitik bilanço kimlikleri**: `A16 = A17+A18+A21+A22`, `A18 = A19+A20`,
  `A15 = A16+A24+A25`. Üçü de yuvarlama hassasiyetinde kapanıyor.
- **Ölü seri**: `TP.PY.P01.LON` (GLP alış kotasyonu) son 252 iş gününün
  tamamında 0 basıyor. **Sıfır bir faiz oranı değildir**; "bu yönde kotasyon
  verilmiyor" demektir ve grafiğe basılırsa koridor bandını tabana çeker.
  Kotasyon serilerinde 0 → NaN.
- **AOFM tabansız**: fonlama eşiğin altındayken EVDS'in AOFM basması.
- **AOSM varsayımı zayıf**: kalan/1HI oranı 3–7 dışına çıkarsa.
- **Hatlar arası tutarlılık**: rezerv hattının yerleşik swap düzeltmesi,
  `(alım yönlü − satım yönlü) / 1000` ile birebir aynı olmalı. Ölçülen fark
  909 ortak iş gününde 7,1e-15 milyar USD — iki bağımsız boru hattı aynı sayıyı
  üretiyor. Ayrışırsa iki sayfada iki farklı "swap stoku" dolaşıyor demektir.

---

## Şekiller

| Dosya | Panel | İçerik |
|---|---|---|
| `01_koridor_faizler.html` | 2 | **Ana grafik.** Koridor bandı, politika faizi, AOFM, AOSM, TLREF (yakın dönem) + tam tarihçe, örtük sıkılaştırma dönemleri gölgeli |
| `02_spreadler.html` | 3 | TLREF−politika · AOFM/marjinal−politika · TLREF−AOFM (rejime göre ortalamalar) |
| `03_net_api_kompozisyon.html` | 3 | Net APİ fonlaması (stok) · fonlama bacağı yığılı · sterilizasyon bacağı yığılı |
| `04_swap_fonlama.html` | 2 | Swap stoku kanal kırılımı · swap ile sağlanan TL ve APİ fonlaması |
| `05_zk_likidite.html` | 4 | ZK bloke + taban · ima edilen tesis oranı · tesis dönemi adımları · serbest mevduat ve gün başı likidite |
| `06_gecirgenlik.html` | 3 | Marjinal faiz vs kredi/mevduat faizi · aracılık marjları · yuvarlanan β |
| `07_koridor_konumu.html` | 3 | Gecelik faizin koridordaki konumu · AOFM−tavan · koridor genişliği ve asimetri |
| `08_rezerv_capraz.html` | 2 | Swap stoku ↔ rezerv hattının swap düzeltmesi · net rezerv, swap hariç net rezerv |

Paneller **alt alta** (cols=1). Yükseklikler `cikti/yukseklikler.json`'a yazılır
ve MDX'teki `yukseklik={}` ile aynı kaynaktan beslenir; `guncelle.py` ikisi
ayrıştığında uyarır.

Şekil 08, kardeş hattın `Aktarılacak Projeler/TCMBNetRezerv/gunluk.csv`
dosyasını okur. Dosya yoksa figür üretilmez ve hat **durur** — eksik panelli
bir sayfa yayımlanmaz.

---

## Bilinen sınırlar

1. **Politika faizi kotasyonu 14.09.2018'de başlıyor.** Öncesinde haftalık repo
   ihaleyle fonlanıyordu ve TCMB bu vadede kotasyon yayımlamıyordu. Tam tarihçe
   panelinde 2018 öncesi için politika faizi çizgisi **yoktur**; koridor, AOFM
   ve geç likidite penceresi çizilir. Gerçekleşen 1 haftalık işlem faizi
   (`TP.PY.P06.1H`) da aynı tarihte başlıyor, dolayısıyla günlük vekil de yok.
   Ölçüldü: iki seri örtüşme penceresinde 1.526 iş gününün 1.503'ünde birebir
   aynı; ayrıştıkları 23 gün PPK karar günleridir (kotasyon aynı gün güncellenir,
   gerçekleşen işlem o gün hâlâ eski faizdedir).
2. **AOSM bir TCMB serisi değildir.** Kalan sterilizasyon bacağının tamamının
   haftalık depo alım ihalesi olduğu varsayılıyor. Kırık vade ve 4 haftalık
   ihaleler açıldığı dönemlerde varsayım zayıflar; denetim bunu ölçer ve uyarır.
3. **ZK oranları EVDS'te yok.** Yayımlanan yalnız sonuçtur; buradaki oran
   gerçekleşmiş tesis oranıdır, tebliğdeki oran değildir. Bir tesis dönemindeki
   düşüş "oran indirimi mi, taban daralması mı" sorusunu ZK serisinden ayırt
   ETMEZ; ayırmak için taban ile birlikte okumak gerekir ve grafik ikisini de
   çizer.
4. **Geçişkenlik katsayısı nedensellik değildir.** Ayrıca marjinal faiz serisi
   rejime göre kaynak değiştiriyor (AOFM/AOSM/TLREF); rejim geçişleri
   katsayıda kırılma üretebilir.
5. **Swap kapsam farkı.** Bu hattın `TP.SWAPTEKTAR.*` stoku yurt içi piyasa
   bacağıdır; rezerv hattının swap düzeltmesi yurt dışı merkez bankalarıyla
   yapılan swapları da içerir. İkisi aynı büyüklük değildir ve Şekil 08'in alt
   notunda böyle yazılır.
6. **Alım yönlü swap stoku ve GLP fonlaması bu ölçüm gününde sıfırdır.**
   Seri taze, olgu yok. `ozet.json`'daki `swap_alim_aktif` / `glp_aktif` /
   `likidite_senedi_aktif` bayrakları sayfa metnini kapatır; bağlanmazsa
   "swap ile TL sağlanıyor" cümlesi olgu bittikten sonra da yayında kalır —
   bu, hiç güncellenmeyen bir sayıdan kötüdür, çünkü yanlış bir **mekanizma**
   anlatır.
7. **Politika faizi ile fiilî faiz aynı şey değildir.** Bu, bu hattın kurucu
   gözlemidir: 2018'in ilk çeyreğinde AOFM tam olarak geç likidite penceresi
   faizine (%12,75) eşitti — ilan edilen politika faizinin 475 baz puan
   üzerinde ve koridorun tavanının da dışında. Faiz grafiğinde politika faizi
   **tek başına çizilmez**.
