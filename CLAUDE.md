# TTO Trading — Çalışma Rehberi

Türkiye makro & piyasa araştırmaları blogu. Yapı: **Markdown → Astro → statik site**
(GitHub'a push → otomatik deploy hedefleniyor).

## Klasör yapısı

```
TTO Trading/
├── site/                        # Astro sitesi (Türkçe, editorial dergi tasarımı)
│   ├── src/content/projeler/    # Proje sayfaları (.mdx) — 1 dosya = 1 proje
│   ├── src/content/arastirma/   # Araştırma notları (.mdx) — 1 dosya = 1 not
│   ├── src/components/          # GrafikEmbed, TahvilHesaplayici, KayitKarti…
│   └── public/projeler/<slug>/  # Python'un ürettiği Plotly HTML çıktıları
├── Aktarılacak Projeler/        # Kaynak Python projeleri (siteye beslenen hatlar)
│   ├── TCMBNetRezerv/           # EVDS + IRFCL → net & swap hariç net rezerv
│   ├── TRYREER/                 # TÜFE/Yi-ÜFE ağırlıklı REDK analizi
│   ├── hazineihrac/             # Hazine ihale scraper + analiz (kendi .git'i var!)
│   ├── USDTRYDeval/             # USD/TRY trend kanalları
│   └── indices/                 # FX haber-duyarlılık endeksi (üç kip: hafif/günlük/tam)
├── teknik/                      # Haftalık teknik analiz bülteni (olc.py ölçer,
│                                #   yaz.py yorum kapısı — her sayı ölçümden; pazar koşusu)
├── tweet/                       # Bültenlerin X zincirleri (uret.py kurar, gonder.py
│                                #   defterli/bayat-korumalı gönderir; TW_* secret'sız KURU)
└── Research/                    # Ham araştırma dosyaları (Excel vb.)
```

## Komutlar (site/ içinde)

- `npm run dev` — geliştirme sunucusu
- `npm run build` — üretim derlemesi (`dist/`)

## İçerik kuralları (kullanıcının koyduğu standart — her içerikte geçerli)

1. **Hiçbir şey atlanmaz.** Bir Excel/Python modeli siteye aktarılırken içindeki her
   metodoloji bölümü, her formül, her sayısal örnek derse taşınır. Özet geçmek yok.
2. **Ders formatı.** Her konu önce teori (türetim, KaTeX), sonra pratik (gerçek
   verilerle adım adım sayısal hesap) olarak anlatılır. Hedef kitle: profesyonel
   trader — jargon açıklanır ama seviye düşürülmez.
3. **Her grafiğin hesabı anlatılır.** Proje sayfalarında her şekil için "bu seri
   nasıl hesaplanıyor" bölümü olur: veri kaynağı, formül, dönüşümler, varsayımlar.
4. **Hesap araçları birbirine bağlanır.** Aynı sayfadaki araçlar ortak durumu paylaşır
   (ör. bootstrap eğrisi → ASW/forward araçlarına akar; `window` üzerinden custom
   event ile: `egri-guncellendi`).
5. **Sayfa metnindeki güncel sayılar dinamiktir.** Her proje pipeline'ı bir
   `ozet_uret.py` ile `ozet.json` üretir (→ `site/public/projeler/<slug>/`);
   MDX'te oynak sayılar `<Deger proje anahtar>statik yedek</Deger>` ile yazılır —
   JSON güncellenince sayfa metni MDX'e dokunmadan tazelenir. Tarihsel/metodolojik
   sabitler (doğrulama örnekleri, bant istatistikleri) statik kalır.
6. **Grafik ev stili.** Python'dan gelen Plotly HTML'leri siteye kopyalanınca
   `site/tools/plotly_stil.py` ile ev stiline geçirilir (başlık solda, lejant altta,
   responsive, beyaz zemin). Bu adım grafik güncelleme akışının parçasıdır.

## İçerik ekleme akışı

1. **Yeni araştırma**: `site/src/content/arastirma/<slug>.mdx` oluştur.
   Frontmatter şeması: `title`, `description`, `pubDate`, `updatedDate?`, `tags[]`,
   `durum` (aktif | taslak | arsiv), `kaynak?`, `guncelleme?`.
   Formüller KaTeX ile yazılır (`$...$`, `$$...$$`).
2. **Yeni proje**: aynı şema ile `site/src/content/projeler/<slug>.mdx`;
   grafik gömmek için `<GrafikEmbed src="/projeler/<slug>/x.html" baslik="…" no="01" />`.
3. **Hesap aracı**: `TahvilHesaplayici.astro` kalıbını kopyala — saf istemci tarafı
   vanilla JS, kütüphane yok.
4. **Yeni analiz**: `site/src/content/analiz/<konu>-<YYYY-AA-GG>.mdx`. Analiz, tek bir
   piyasa gelişmesini mekanizmasına kadar açan yazıdır (pano değil — pano `projeler/`).
   **Dosya adı ve başlık TARİH taşır**, çünkü aynı konu tekrar tekrar analiz edilir:
   her çeyrek bir büyüme verisi, her ay bir enflasyon, her ihale bir söküm gelir ve
   tarihsiz slug ikinci yazıda çakışır. Başlık kalıbı: `<GG Ay YYYY> <Konu> — <alt
   başlık>`. Kart ayrıca `pubDate`i kendisi basar (`KayitKarti`), yani tarih iki yerde
   birden görünür ve listede hangi yazının hangi güne ait olduğu okunur.
   **Uzun analizler (~20 KB üzeri) `<div class="yonetici">` ile bir YÖNETİCİ
   ÖZETİ ile açılır**: tek cümlelik tez, soru–cevap tablosu (gelir mi · ne zaman ·
   ne kadar · faize etkisi · kanıtın gücü) ve `.rakamlar` şeridinde altı anahtar
   ölçüm. Özetteki her sayı da `<Deger>` ile bağlanır — özet donarsa yazının geri
   kalanı tazelenirken okur yanlış sonucu okur. Özet, gövdedeki bir kutuyu
   TEKRARLAMAZ; onu soğurur.

## Grafik güncelleme akışı

Python projesi HTML üretir → dosya `site/public/projeler/<slug>/` altına kopyalanır →
push ile yayına girer. Şablon: `.github/workflows/veri-guncelle.yml` (cron'lu, henüz
taslak; repo GitHub'a bağlanınca aktifleştirilecek).

## Bülten katmanları (`bulten/`)

Ölçülen katman otomatik koşudan gelir, yazı katmanı ona dokunmaz (bkz.
`bulten/YAZIM.md`). Modüller:

| dosya | ne yapar |
|---|---|
| `uret.py` | bülteni kurar, `site/src/data/bulten/<tarih>.json` yazar |
| `gozlem.py` | hatların `ozet.json` anlık görüntü deposu; **anahtar başına saat** |
| `olay.py` | eşikleri uygular, olay cümlesini kurar; **haber tonundaki olağandışı hareketi sıralar** |
| `piyasa.py` | 51 enstrüman, TL faiz seti, türev makaslar, **σ-normalize hareket** |
| `takvim.py` | resmî yayım takvimi; `surpriz.py` geçmişi arşivler ve sonucu ölçer |
| `soz.py` | söz defterini (`izleme.json`) okura açar |
| `rejim.py` | reel faiz, taşıma, reel kredi, REDK sapması, eğri, rezerv kalitesi, **enflasyon risk primi, makroihtiyati ayrışma** |
| `grafik_veri.py` | satır içi SVG grafiklerin verisi (Plotly bültene girmez) |
| `denetim.py` | 40 ölçüt; engel varsa bülten yayına gitmez. `karanlik`: donan seri · `yerlesmemis`: kapanmamış seansın barı · `revizyon`: yayımlanan sayı sonradan değişti mi · `haber_tonu`: haber endeksinin olağandışı hareketi anılmış mı |
| `tazeleme.py` | hangi hattın koşacağına resmî yayım takvimi karar verir |
| `zincir.py` | veri→ölçüm→yazı zincirinin durumu; eksik halkayı ve çıkış koduyla ne yapılacağını söyler |

**Kurucu ilke — saat.** Bir `ozet.json` tek bir yayım ritmi taşımaz: aynı dosyada
günlük ve haftalık seriler yan yana durur. Bir anahtarın saati, önce açıkça
tanımlanan alan, yoksa `<anahtar>_tarih` geleneği, o da yoksa `_tarih`tir. Panodaki
tarih, farkın kıyas noktası ve gecikme denetimi bu saatten okunur.

**Kurucu ilke — emniyet kütüphanenin altına serilir.** Ağa çıkan bir hattın
kusuru çoğu zaman hattın kendi dosyasında değildir: `tcmb` istemcisi isteği
zaman aşımısız atıyordu ve argümanı çağrı yerinden geçirmenin YOLU YOKTU
(kwargs sorgu dizesine gidiyor). Ortak korumalar bu yüzden `ortak/sitecustomize.py`
içinde durur; `PYTHONPATH`e eklendiği için her hat alt süreci — kendi `.venv`iyle
koşan da, yarın eklenecek olan da — onunla açılır. Hatların dosyalarına tek satır
girmez.

**Kurucu ilke — zinciri saat değil rutin sürükler.** Bülten üç halkalı:
veri tazeleme → ölçüm → yazı. İlk ikisi GitHub'ın zamanlanmış tetikleyicisine
bağlı ve o tetikleyici ölçülebilir biçimde güvenilmez — kayda geçen zamanlanmış
koşuların TAMAMI 30–60 dk gecikmeli başladı, sabah penceresindekiler (26.08
ölçüm, 27.08 hem veri hem ölçüm) hiç başlamadı. Zincirin gerçekten güvenilir
halkası yazı katmanını ateşleyen bulut rutinidir. Bu yüzden yazı katmanı önce
`bulten/zincir.py` ile duruma bakar, eksik halkayı kendi tetikler, sonra yazar.
Üç savunma katmanı var ve üçü de depodaki araçlarda durur: yedek cron'lar
(düşen tetikleyiciye ikinci şans), `bulten.py`nin **yazılmış bülteni ezmeme**
kapısı (geç düşen bir ölçüm koşusu yayımlanmış metnin altındaki sayıları
değiştiremez), ve `nobetci.yml` (hafta içi 06:37 UTC — bülten yazılmamışsa iş
akışı DÜŞER, düşen iş akışı e-posta gönderir). Arızanın görüntüsü ile sağlığın
görüntüsü aynıydı: yayın iş akışı "değişiklik yok" deyip yeşil bitiyor, site
dünkü bülteni göstermeye devam ediyordu. Nöbetçi o sessizliği kapatıyor.

**Kurucu ilke — sigorta metne değil araca konur.** Yazı katmanını ateşleyen
rutinin metni depoda değil, claude.ai hesabının rutin ayarlarında durur ve bir
aracı onu DEĞİŞTİREMEZ. 27.08.2026'da iki ayrı sınamayla ölçüldü.
(1) Rutinler listelenebiliyor ve metinleri OKUNABİLİYOR — bu sayede rehberle
çeliştikleri yerler bulundu — ama güncelleme REDDEDİLİYOR: bir aracı yalnız
kendi kurduğu rutini değiştirebilir. (2) "Öyleyse silip yenisini kurayım" da
işlemiyor: aracının kurduğu rutine kaynak depo BAĞLANMIYOR. Sınama rutini
kuruldu, ateşlendi ve 24 saniyede depoya hiç dokunamadan bitti (oturum etiketi
`routine-lineage-none`); mevcut rutinlerin taşıdığı `sources` alanının
karşılığı `create_trigger`'da yok. Yani rutin metnindeki bir kusur ancak İNSAN
eliyle, claude.ai arayüzünden düzeltilir. Üstelik o metin
depoyla birlikte sürümlenmez, gözden geçirilmez ve kimse ona bakmaz. Bu yüzden
bir kural "rutin metnine yazıldı" diye tamam sayılmaz: araç onu kendi başına
dayatabilmelidir. `yaz.py`nin damga sigortası açık argüman
verilmese de yama dosyasının zamanıyla sürer, denetim eşikleri koddadır, duman
sınaması iş akışını durdurur. Rutin metni yalnız
`bulten/YAZIM.md`ye işaret eder; kural rehbere yazılır.

**Kurucu ilke — uydurma yok.** Sürpriz yalnız sayısal beklenti varsa hesaplanır;
söz karnesi yalnız notlanmış kayıtlardan oran verir; kıyas eğrisi elde ne kadar
tarihçe varsa o kadar geriye gider ve kendi tarihiyle etiketlenir. Ölçülmemiş bir
şeyi ölçülmüş gibi göstermektense boş bırakılır, sebebi yazılır.

**Kurucu ilke — önbellek depoyu ezmez.** Bir koşucu önbelleği yalnız
**izlenmeyen** ham veriyi taşır. `veri.yml` `Aktarılacak Projeler/*/data`yı
önbelleğe alıyordu; o dizinlerde izlenen dosyalar da var ve `restore-keys`
önek eşleşmesiyle gelen eski önbellek, başka bir iş akışının (fx) ürettiği
dosyaların ESKİ hâlini checkout'un üzerine yazıyordu. 27.08 koşusu böylece
26.08 Pazar tam kipinin ürettiği FX snapshot'ını sildi ve `git add` silmeyi
sahiplendi — koşu yeşil bitti, tarihçe 7 kayıttan 6'ya düştü. Kural: izlenen
bir dosyanın doğru sürümü depodakidir; restore'dan sonra `git checkout --`
ile depo sürümü geri konur (izlenmeyen önbellek dosyalarına dokunmaz).

**Kurucu ilke — bir ölçüm ancak KAPANMIŞ bir seansı ölçebilir.** Günün barı
piyasa kapanmadan alınırsa "günlük değişim" dünkü seansı değil geceliği ölçer
ve işareti dünküyle ters olabilir. 27.08.2026 sabahı 51 enstrümanın 21'i böyle
yayımlandı; altın dünkü seansı −%0,86 kapatmışken bülten +%1,78 yazdı ve günün
bütün anlatısı o sahte harekete kuruldu. Üç katmanlı sigorta kondu: ölçüm
katmanı grup grup kapanış saatine göre kapanmamış barı düşürür
(`piyasa.KAPANIS_UTC`), denetim aynı soruyu yayının SON kapısında bağımsız
sorar ve ENGEL üretir, duman sınaması ikisini de sahte saatle çağırır. Tek
katmanlı sigorta yetmez: bu koruma bir zamanlar vardı ama yalnız beş enerji
vadelisini kapsıyordu ve kimse fark etmedi.

**Kurucu ilke — bir düzeltme genelleştirilmeden tamamlanmaz.** Aynı sabahki
metin enerjideki ölçü hatasını buldu, doğru teşhis etti, düzgün bir geri alma
yazdı — ve aynı paragrafın devamında aynı hatayı taşıyan metal rakamlarını
düzeltmeden yayımladı. Bir kusur bulunduğunda sorulacak soru "bu seriyi
düzelttim mi" değil, "bu kusur başka nerede olabilir"dir. Denetimin
`revizyon` ölçütü bunu artık ölçüyor: daha önce yayımladığımız bir sayı
sonradan değiştiyse adıyla listelenir, yani kusur göze çarpmasa da görünür.

**Kurucu ilke — dış kaynak önce YOKLANIR, sonra kurulur; adresi sabitlenmez,
çözülür.** El Niño hattının küresel kanadı FRED üzerine kurulacaktı. İlk keşif
koşusu 29 seriyi 60 saniyelik zaman aşımıyla denedi ve 20 dakikalık iş bütçesi
tek satır öğrenmeden doldu: FRED bu koşuculardan ERİŞİLEMİYOR (üç ucu da zaman
aşımı), IMF SDMX'in DNS'i çözülmüyor, IMF datamapper 403 veriyor. Doğru sıra
şudur: önce KAYNAK yoklanır (her aday 8 saniye, bir dakikada biter), sonra açık
kapının ardındaki SERİLER ölçülür, sonra hat kurulur. Ölçüm hattı zayıflatmadı,
güçlendirdi: açık çıkan kapılar (Dünya Bankası Pink Sheet, BLS, BIS, ECB)
FRED'in vereceğinden fazlasını verdi — örneklem 1980 yerine 1960'ta başlıyor ve
karşılaştırmaya iki ekonomi giriyor.

İkinci yarısı daha sinsi: Pink Sheet'in adresi her güncellemede değişen bir
sağlama taşıyor. Sabit adres yazıldığında koşu YEŞİL bitti, dosya indi,
ayrıştırıldı — ve emtia serisi yedi ay geride kaldı. Bir dış dosyanın adresi
sabitlenmez, yayımcının sayfasından çözülür; sabit adresler yalnız yedektir. Ve
her serinin KENDİ yaşı ölçülüp yazılır: birleşik tablonun son ayı başka bir
kaynaktan gelebiliyor ve donmuş seriyi taze gösteriyor.

Üçüncüsü: bir dosyanın başlık düzeni sayfadan sayfaya değişebilir (Pink
Sheet'te bir sayfada üstte kategori altta alt kalem, diğerinde üstte ad altta
BİRİM). "En doğru başlık satırını seç" sezgisi sırayla iki tarafı da ısırdı.
Doğrusu satır SEÇMEMEK: her sütunun bütün başlık hücreleri aday olarak saklanır,
eşleme herhangi biriyle tutar. Ve eşleme tutmazsa dosyanın GERÇEK sütun adları
künyeye yazılır — "bulunamadı" demek ama neyin bulunabileceğini söylememek, her
düzeltme için ayrı bir keşif koşusu demekti.

**Kurucu ilke — "veri geldi" ile "veri TAM geldi" aynı şey değildir.** Bir
kaynak kırpmayı söylemez. yfinance `USDTRY=X` bu koşuculardan altı aylık ve
seviyesi yıllar geride bir seri döndürüyordu; grafik çizildi, koşu yeşil bitti,
dolar bazlı ihraç hacmi aylarca yanlış bir kurla bölündü. Kaynak EVDS'e
çevrilince aynı kusur biçim değiştirip geri geldi: 2000–2026 tek istekte
sorulunca EVDS yanıtı sessizce kırpıyor — 200 dönüyor, seri kısa geliyor. Kural:
uzun aralık PARÇALI sorulur, gelen serinin KAPSAMI ölçülür ve kapsam çıktının
ihtiyacına yetmiyorsa çıktı üretilmez, üstelik bayat dosyası SİLİNİR.

Aynı sabahın üçüncü kusuru daha sinsiydi: `ozet_uret.py`, `grafik_ozet.json`'u
okuyordu ve o dosyayı **yazan kimse yoktu** — depodaki sürüm elle koşulmuş bir
günden kalmıştı. Ölü bir bağımlılık kırık olandan tehlikelidir: dosya vardır,
okunur, hata vermez, yalnızca yaşlanır. Bir dosya okunuyorsa onu üreten adım
hattın adım listesinde GÖRÜNMELİDİR.

**Kurucu ilke — sezgi ölçülmeden koda girmez; ÖLÇÜ ile ETİKET ayrı kusurlardır.**
"Pazartesi kapanışı Cuma'ya göre ÜÇ takvim günü kapsar, öyleyse günlük σ ile
kıyaslamak hareketi olduğundan olağandışı gösterir." Sezgi ikna edici ve
YANLIŞ. 49 enstrümanda bir yıllık seride ölçüldü: üç takvim günlük (hafta sonu)
değişimlerin σ'sının bir günlüğe oranı **medyan 1,00** — rastgele yürüyüşün
beklediği √3 = 1,73 değil; 1,30'u aşan yalnız üç enstrüman (hafta sonu seansı
olan enerji vadelileri ve JPY). Üç günden uzun boşluklarda da (bayram) oran
1,02. Sebep basit: bunlar KAPANIŞTAN KAPANIŞA fiyatlar, hafta sonunda seans
yoktur, yani "üç takvim günü" hâlâ TEK seanslık risktir. USD/TRY'de hafta sonu
değişimlerinin ortalaması (+0,029%) hafta içinin (+0,068%) altında — taşıma
bile birikmiyor. Ölçekleme uygulansaydı gerçek hareketler sistematik olarak
gizlenirdi.

Ama aynı gözlemin ardında GERÇEK bir kusur vardı ve o ölçüde değil ETİKETTE:
31.08.2026 pazartesi bülteninde elli piyasa satırının ELLİSİ 28.08 Cuma
kapanışını taşıyordu ve "günlük değişim" diye yayımlandı; hangi seansa ait
olduğunu söyleyen tek bir alan yoktu. Pazartesi okuyan biri hareketi bugüne
ait sanar. Bir gözlem "sayı yanlış" diye geldiğinde önce sayı ölçülür; sayı
doğruysa soru biter değil, YER DEĞİŞTİRİR — okurun gördüğü etikete geçer.
Anlık görüntü artık seansını yazıyor (`piyasa.kapanis_seansi`), denetim
kaçırılan SEANS sayısını ölçüyor (takvim günü değil: tek tatil uyarı, iki
seans engel) ve duman sınaması ölçeklemenin geri konmasını yakalıyor.

**Kurucu ilke — kopya sözleşmesi bir bütündür; SIRA kusuru gizler.** Hattın
siteye kopyalanacak çıktı listesi bir sözleşmedir ve eksik bir dosya kopyalamayı
yarıda keser. Hazine hattının iki grafiği yalnız tam kipte üretiliyor ve
`.gitignore`'da: hafif kip onları göremeyince kopyalama tam o noktada duruyordu.
Kusuru görünmez yapan şey sözlük sırasıydı — o dosyadan ÖNCE gelen on bir HTML
siteye gidiyor, SONRA gelen `tablolar.json` ile `ozet.json` gitmiyordu. Yani
grafikler tazeleniyor, sayfa metnindeki sayılar donuyordu ve ikisi de aynı yeşil
koşunun içinde oluyordu. Bir kipin üretemediği çıktı, o kipin kopya
sözleşmesinde bulunmamalı ya da o kip onu üretmelidir.

**Kurucu ilke — bir hattın kipi, ölçüsünün ritmine göre bölünür.** FX hattı
tek bir "tazele" düğmesi değildi: anlık endeks canlı haber akışından gelir ve
HER GÜN ilerleyebilir, rejim/korelasyon panelleri GDELT haftalık arşivinden
gelir ve yalnız hafta kapanınca ilerler. Hafif kip haber akışını hiç toplamadığı
için hat günlük listede sahte tazelik damgası atıyordu; çözüm olarak haftalığa
çekilince bu sefer günlük ilerleyebilecek yarı da donduruldu. Doğrusu üçüncü bir
kip: `--gunluk` canlı akışı çeker, `web_cikti.py --anlik` yalnız anlık
grafikleri çizer, GDELT tabanlı paneller ve onların "veri sonu" damgası
haftalık koşuya bırakılır. Bir hattın çıktıları farklı ritimlerdeyse kipleri de
o ritimlere bölünür — tek kip, en yavaş ritme mahkûm eder.

## Dikkat

- `hazineihrac/` içinde gömülü bir `.git` var — kök repo'ya eklerken submodule
  sorununa yol açar; aktarım sırasında `.git`'i kaldır veya taşı.
- Plotly HTML'leri plotly.js'i gömülü içerdiğinde ~4,6 MB oluyor; ileride
  `include_plotlyjs='cdn'` ile üretilirse ~%98 küçülür.
- Site dili Türkçe; tasarım jetonları `site/src/styles/global.css` başında
  (`--paper`, `--ink`, `--claret`; Fraunces / Newsreader / IBM Plex Mono).
- `astro.config.mjs` içindeki `site:` alanı gerçek domain alınınca güncellenecek.
- Bülten dosyalarında otomatik koşu ile yazı katmanı aynı gün dosyasına dokunur;
  bu çakışma **elle çözülmez**. `.gitattributes` + `bulten/birlestir.py` sürücüsü
  yazılı sürümü seçer, önbellekte anahtarları birleştirir. Sürücü `.git/config`'de
  durduğu ve depoyla taşınmadığı için `bulten.py` her koşuda kendini kurar.
  Sürücü komutu kabuktan geçtiğinden **yollar tırnaklanmalı** (depo yolunda boşluk var).
