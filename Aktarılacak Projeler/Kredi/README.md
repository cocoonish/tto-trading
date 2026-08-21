# Kredi & Parasal Büyüklükler — veri hattı

Bankacılık sektörü kredi hacmi, kur etkisinden arındırılmış kredi büyümesi, parasal
büyüklükler (M1/M2/M3), para çarpanı, mevduat kompozisyonu ve dolarizasyon, KKM,
kredi faizleri ve makaslar, takipteki alacaklar ve Banka Kredileri Eğilim Anketi.

Site sayfası: `site/src/content/projeler/kredi-parasal.mdx`
Web çıktısı:  `site/public/projeler/kredi-parasal/`
Tek dış bağımlılık: **TCMB EVDS3**.

```
veri.py  →  metrik.py  →  grafik.py  →  ozet_uret.py
 data/*.csv   data/metrik_*.csv   cikti/*.html      ozet.json
              uyarilar.json       yukseklikler.json
```

Sıra bağlayıcıdır: her adım bir öncekinin yazdığı dosyayı okur.

---

## 1. Erişim — EVDS3 ve tuzakları

```
BASE = https://evds3.tcmb.gov.tr/igmevdsms-dis
GET {BASE}/series={KOD}&startDate=DD-MM-YYYY&endDate=DD-MM-YYYY&type=json
GET {BASE}/serieList/type=json&code={VERI_GRUBU}
Başlık: key: <ANAHTAR>          ← anahtar URL'de DEĞİL
```

* `evds2.tcmb.gov.tr/service/evds` **ölüdür** (HTML SPA kabuğu döndürür).
* Anahtar arama sırası (bu projeye anahtar **kopyalanmaz**):
  `TTO_EVDS_KEY` → `<proje>/.evds_key` → `TTO Trading/.evds_key` →
  kardeş `Aktarılacak Projeler/TCMBNetRezerv/.evds_key`.
* **Satır sınırı:** tek istek ~1000 satır döndürüyor ve aralığın **sonundan geriye**
  dolduruyor, gerisini uyarı vermeden kırpıyor. `veri.py` frekansa göre parçalıyor:
  iş günü **366 gün**, haftalık **900 hafta**; aylık ve üç aylık seriler tek istekte
  tam geliyor.
* **Dört tarih biçimi, üç ayrıştırıcı:** iş günü ve haftalık `DD-MM-YYYY`, aylık
  `YYYY-M`, üç aylık `YYYY-Qn`. BKEA'yı aylık ayrıştırıcıya vermek `int('Q2')` ile düşer.
* Yanıt kolonu = seri kodunun noktaları alt çizgiye çevrilmiş hâli
  (`TP.HPBITABLO6.1` → `TP_HPBITABLO6_1`).
* EVDS'in `LAST_UPDATED` alanı **tazelik ölçüsü değildir** (metaveri kaydının
  güncellenme tarihi). Tazelik yalnız **son dolu gözlemden** okunur.
* Önbellek: `data/cache/*.csv`, TTL 12 saat (katalog 168 saat). Ağ düşerse eski
  önbelleğe düşülür ama **sessiz kalınmaz**: uyarı basılır ve `uyarilar.json`'a girer.

## 2. Birimler — bu hattın en sinsi hata kaynağı

| Seri ailesi | EVDS birimi |
|---|---|
| `TP.HPBITABLO1/2/3/6/7.*` (haftalık para ve banka) | **bin TL** |
| `TP.HPBITABLO4.*` (YP mevduat) | milyon USD |
| `TP.AB.A*` (analitik bilanço) | bin TL |
| `TP.APIFON*` | milyon TL |
| `TP.TLDTHVADE.*` | bin TL |
| `TP.ZORUNDTH.KB7 / KB8` | milyon USD / **milyon TL** |
| `TP.KKM.K1 / K4` | milyar USD / milyar TL |
| `TP.KAVRAMSAL.*` | endeks (30.12.2005 = 100) |

Bin TL ile milyon TL arasındaki bin katlık fark trilyonlarda gözle yakalanmaz.
Bu yüzden hat iki **kimlik denetimi** taşıyor:

* `TP.AB.A24` (bin TL) ile `−TP.APIFON3` (milyon TL) aynı günde aynı sayı olmalı.
  Denetim **medyana** bakar, maksimuma değil: kimlik ay/çeyrek kapanışlarında
  değerleme farkıyla birkaç günde sapıyor ve tabanı küçük bir günde bu oran %3'e
  çıkabiliyor. Aranan hata sınıfı başka — birim bozulursa sapma **her gün** olur.
* İma edilen sepet kuru (`KB8/KB7`) USD kurunun 0,5–2 katı bandında olmalı; dışına
  çıkarsa birim varsayımı bozulmuştur, hat USD'ye düşer ve uyarır.

## 3. Tazelik — aile bazlı, tek eşik yok

Bu hatta beş ayrı yayım ritmi var; tek eşik her koşuda ya yanlış alarm ya sessiz
kabul üretir. Referans **duvar saatidir**.

| Aile | Gecikme | Tolerans | Ölçüm |
|---|---|---|---|
| APİ fonlaması / AOFM | aynı gün | 3 iş günü | son gözlemden |
| Analitik bilanço | 1 iş günü | 4 iş günü | son gözlemden |
| Döviz kuru | **−1 gün** (bir gün önceden ilan) | 4 iş günü | negatif gecikme alarm üretmez |
| Haftalık para ve banka | 6 gün (Perşembe) | 12 gün | son gözlemden |
| ZK tabanı | 13 gün | 20 gün | son gözlemden |
| Aylık para ve banka | 51 gün | 70 gün | **dönem sonundan** |
| BKEA (üç aylık) | 51 gün | 110 gün | **dönem sonundan** |

Aylık ve üç aylık gözlemler dönemin **ilk** gününe damgalanır (`2026-6` →
`01.06.2026`) ama TCMB gecikmeyi dönemin **sonundan** sayar. Damgadan ölçmek her ay
bir aylık sahte gecikme ekler; `veri.py` bu yüzden bu iki aile için ölçümü dönem
sonuna çeviriyor.

## 4. Yöntem

### 4.1 Kur etkisinden arındırma — zincirleme

Haftalık büyüme oranı, YP bacağı **önceki haftanın kuruyla** değerlenerek kurulur:

```
g_s = [K^TL_s + K^YP_s · (e_{s−1}/e_s)] / [K^TL_{s−1} + K^YP_{s−1}] − 1
```

13 haftalık yıllıklandırma **bileşik**tir: `(∏(1+g))^(52/13) − 1`, üs **4**.
Basit ölçekleme (`4 × G13`) bileşiklenmeyi ihmal eder ve bu ölçekte iki puandan
fazla sapar; **kullanılmaz**.

**Sıra bağlayıcıdır:** önce arındır → sonra zincirle → sonra yıllıklandır. Ters
sırada kur etkisi de yıllıklandırılır ve hata dört katına çıkar.

Girdi serileri: `TP.HPBITABLO2.24` (yurt içi TL kredi) ve `TP.HPBITABLO2.28`
(yurt içi YP kredi, TL karşılığı).

### 4.2 Hangi kur

YP kredinin **döviz cinsinden** miktarı EVDS'te yayımlanmıyor; yalnız TL karşılığı
var. Kredi tarafının para cinsi bileşimi de yayımlanmıyor. Bu yüzden ana seride
**mevduat tarafından ima edilen sepet kuru** kullanılıyor:

```
e_sepet = TP.ZORUNDTH.KB8 (milyon TL) / TP.ZORUNDTH.KB7 (milyon USD)
```

Bu bir **yaklaşımdır** ve sayfada açıkça yazılır: sepet **mevduat** sepetidir,
kredi sepeti değildir, ve kıymetli maden depo hesaplarını içerir. USD kuruyla
(`TP.DK.USD.A.YTL`) hesap **tanı** olarak tutulur; ikisi arasındaki fark eşiği
aşarsa uyarı düşer.

ZK tabanı 13 gün gecikmeli olduğu için sepet kuru son 1–2 haftada boştur. O kuyruk
USD ve EUR üzerinden (sabitsiz EKK, son 104 hafta) **tahmin edilir** ve
`sepet_kaynak` alanında işaretlenir; kuyruk dört haftayı aşarsa uyarı düşer.

Haftalık gözlemler Cuma itibarıyladır; kur da aynı Cuma alınır. Cuma tatilse **en
yakın önceki** iş gününe düşülür ve gözlem `geri_tasima` diye işaretlenir. **İleri
taşıma yapılmaz** — gelecekteki bir kurla geçmiş bir stoğu değerlemek, ölçüm
gününde bilinmeyen bilgiyi kullanmaktır.

### 4.3 Laspeyres ayrıştırma (kur etkisinin büyüklüğü)

Rezerv hattındaki `TCMBNetRezerv/altin_etkisi.py` ile **aynı çerçeve**, sözlük
bilinçli olarak ortak:

```
Γ_s = K^{YP,fc}_{s−1} · Δe_s          (kur etkisi   — atılan bacak)
Λ_s = ΔK^TL_s + e_s · ΔK^{YP,fc}_s    (gerçek akım  — tutulan bacak)
Γ + Λ = ΔK                            (kimlik, artık yok)
```

Kimlik artığı ölçülür; makine hassasiyetinin dışına çıkarsa uyarı düşer. Simetrik
(Bennet) varyantı ve zincirleme sapması `D_T` **tanı** olarak hesaplanır,
yayımlanmaz.

### 4.4 Uzun tarihçe — seri kırılması

Eski haftalık tablolar (`bie_kredi`) **31.01.2025**'te kapandı, yeni tablolar
(`bie_hpbitablo*`) **28.06.2024**'te başladı: 32 haftalık örtüşme var.

* **Seviyede uç uca ekleme yasaktır.** Tanım farkı sabit değil, sürükleniyor.
* Birleştirme yalnız **büyüme oranı** düzeyinde yapılır; kırılma haftasında zincir
  **koparılır** (o haftanın "büyümesi" iki farklı tanımın farkıdır, büyüme değildir).
* Örtüşme oranının sürüklenmesi her koşuda ölçülür; ±0,001'i aşarsa uyarı düşer.
* Kırılma tarihi `ozet.json`'a `kredi_seri_kirilma` olarak yazılır ve grafikte
  dikey çizgiyle işaretlenir.

Aynı kırılma **para arzı seviye tablosunda** da var (M3, 28.06.2024'te %2,4).
Tarih koda gömülmez: seviyeden hesaplanan haftalık büyüme, TCMB'nin kendi ham
endeksinden hesaplanan büyümeyle karşılaştırılır ve %0,5'ten fazla ayrışan hafta
**veriden bulunarak** koparılır.

### 4.5 Dolarizasyon

Ham pay DTH'ın TL karşılığı üzerinden hesaplandığı için kur yükselirken
**kendiliğinden** yükselir. Arındırılmış pay DTH'ı **çıpa haftasının** kuruyla
yeniden değerler:

```
δ̃_t = [D^YP_t · (e*/e_t)] / [D^TL_t + D^YP_t · (e*/e_t)]
```

Çıpa, içinde bulunulan takvim yılının ilk gözlemidir ve yıl dönünce kendiliğinden
ilerler. Sayfada **ham ve arındırılmış birlikte** verilir; ham pay tek başına
yayımlanmaz.

### 4.6 Reel faiz

**Tam Fisher**: `(1+i)/(1+π^e) − 1`. `i − π` yaklaşımı **yasaktır** — bu düzeyde
puanlarla sapıyor. Beklenti girdisi PKA 12 aylık TÜFE beklentisi
(`TP.PKAUO.S01.E.U`, aylık); haftalık eksene son yayımlanan değer taşınır.
Yaklaşık tanım grafikte yalnızca **tanı** izi olarak, kesikli çizilir.

### 4.7 Yayımlamadığımız şeyler

* **TCMB'nin makro ihtiyati kredi büyüme sınırı** grafiğe çizilmez. Sınırın referans
  kuru, oranı ve kapsam dışı kalemleri tebliğ ve basın duyurularında belirlenir,
  dönemler arasında değişir ve EVDS'te makine-okunur biçimde **yoktur**. Yayımladığımız
  seri TCMB'nin düzenleme serisi **değildir**; `ozet.json`'daki `arindirma_yontem`
  alanı (`zincirleme_sepet`) bunu taşır.
* **Zorunlu karşılık oranları** EVDS'te yoktur. Türetilen `zk_ima_oran`
  (`TP.AB.A19` / ZK'ya tabi taban) **ima edilen bileşik orandır**, tebliğdeki
  herhangi bir tek orana eşit değildir ve öyle etiketlenir.

## 5. Doğrulama

Üç bağımsız sınav, üç ayrı soru:

| # | Sınav | Soru | Sonuç |
|---|---|---|---|
| A | Seviyelerden hesaplanan **ham** M1/M2/M3 büyümesi ↔ TCMB'nin ayrı ürünü olan ham endeks (`bie_kavramsal` HAMM\*) | **kimlik** — aynı büyüklüğü mü anlatıyorlar? | eşitlik beklenir; 2 puanı aşarsa **hat durur** |
| B | Bu çalışmanın arındırdığı M2 ↔ TCMB'nin ARIM2 endeksi | **yöntem** — arındırma makul mü? | eşitlik **beklenmez** (TCMB'nin yöntemi yayımlanmıyor); yanlılık, RMSE ve korelasyon ölçülür |
| C | Haftalık kredi serisi (`bie_hpbitablo6`) ↔ aylık kredi serisi (`bie_krehacbs`) | **seviye** — iki ayrı ürün aynı şeyi mi ölçüyor? | seviye oranı 1'e yakın, 12 aylık büyümeler puan mertebesinde uyumlu |

Ayrıca her koşuda kimlik denetimleri: toplam kredi = yurt içi + yurt dışı ·
yurt içi kredi = TL + YP · M1/M2/M3 kimlikleri · A24 ↔ APIFON3 · Laspeyres Γ+Λ=ΔK ·
arşiv/yeni örtüşme oranı.

## 6. Bilinen sınırlar

1. **Kredi sepeti ölçülemiyor.** Ana seri mevduat sepetini vekil alıyor; bu bir
   yaklaşımdır ve bir kalibrasyon sabitiyle kapatılamaz. USD ile hesap tanı olarak
   yayımlanıyor, aradaki fark izleniyor.
2. **Haftalık kredi kırılımı 28.06.2024'te başlıyor.** Tüketici/ticari/KOBİ
   büyümeleri o tarihten öncesi için haftalık frekansta yok. Uzun tarihçe yalnız
   birleştirilmiş **toplam** seride var.
3. **Tüketici kalemleri TL+YP birleşik** yayımlanıyor; ayrıştırılamadığı için o
   seriler ham'dır ve arındırılmış serilerle aynı cümlede okunmaz.
4. **Aylık banka türü serilerinde** (`bie_krehacbs`) TL/YP kırılımı yok: katılım
   bankaları dahil/hariç kıyası ham büyüme üzerinden yapılır.
5. **Arındırma yöntemimiz TCMB'ninkiyle birebir aynı değil** (bkz. sınav B).
   M1'de fark büyüktür çünkü M1'in YP payı üçte ikiye yakındır ve arındırma seçimi
   sonucu domine eder.
6. **KKM** yalnız aylık stok olarak var; haftalık KKM serisi EVDS'te yoktur.
   Program fiilen kapandığı için `kkm_aktif` bayrağı `false`; sayfa metni bu bayrağa
   bağlıdır ve "KKM çıkışı" gerekçesi güncel dolarizasyon yorumunda kullanılmaz.
7. **Kredi ↔ enflasyon ilişkisi gecikmeli korelasyondur, nedensellik değildir.**
   Aynı pencerede her iki seriyi de kur hareketi besliyor olabilir.

## 7. Dosyalar

| Dosya | Ne yapar |
|---|---|
| `veri.py` | EVDS3 çekimi, önbellek, dört frekans, tazelik + kimlik denetimleri |
| `metrik.py` | arındırma, ayrıştırma, uzun tarihçe, para, dolarizasyon, faiz, çapraz doğrulama |
| `grafik.py` | dokuz Plotly şekli (paneller alt alta), `yukseklikler.json` |
| `ozet_uret.py` | `ozet.json` — sayfadaki her oynak sayının kaynağı |
| `uyarilar.json` | veri + hesap katmanının görünür uyarıları, doğrulama sonucu |
| `data/` | çekilen ve türetilen CSV'ler, `cache/` |
| `cikti/` | siteye kopyalanan HTML'ler |

## 8. Koşum

```bash
python3 veri.py            # --yenile ile önbelleği yok say
python3 metrik.py
python3 grafik.py
python3 ozet_uret.py
```

Tümü birden ve siteye kopyalama:

```bash
python3 guncelle.py kredi
cd site && python3 tools/plotly_stil.py public/projeler/kredi-parasal/*.html
```

Bir figür üretilemezse `grafik.py` çıkış kodu 1 verir ve **siteye kopyalama
yapılmaz** — eski grafikle taze metin yayımlanmasın.
