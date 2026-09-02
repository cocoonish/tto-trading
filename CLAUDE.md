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
├── tweet/                       # X gönderileri: uret.py bülten/teknik, analiz.py analiz
│                                #   yazısını yönetici özetinden kurar; denetim.py KALİTE
│                                #   KAPISI; gonder.py defterli/bayat-korumalı gönderir,
│                                #   metni arsiv/'e, defteri site/src/data/tweet/'e aynalar
├── analiz/                      # Analiz yazım rehberi (YAZIM.md) + şablon (sablon.mdx);
│                                #   kapısı site/tools/analiz_sinavi.py
└── Research/                    # Ham araştırma dosyaları (Excel vb.)
```

Site kabuğunun tek kaynakları: `site/src/lib/bolumler.ts` (bölüm numaraları,
adresler, RSS beslemeleri — başlık, alt bilgi ve kicker'lar buradan okur),
`site/src/lib/bicim.ts` (sayı/tarih/İstanbul saati yazımı — başka yerde sayı
biçimlenmez; Python eşi `ortak/bicim.py`, ikisi aynı sözleşmeyi taşır: eksi
U+2212, ondalık virgül, yüzde önde, bp arkada — bülten ölçüm katmanı, olay
cümleleri ve rejim metinleri sayıyı oradan yazar, `bulten/denetim.py`nin
`bicim` ölçütü sızıntıyı uyarı olarak listeler), `site/src/lib/yayinlar.ts` (bülten ve teknik sayılarının yayın
kapısı, sayı numarası ve önizleme özeti — dört sayfa ve dört RSS beslemesi
buradan okur). Bağlantı önizleme kartları `site/tools/og_kart.py` ile çizilir
(`site/public/og/`); site simgesinin PNG türevleri (32 · 180 apple-touch)
`site/tools/favicon_uret.py` ile SVG'den üretilir — SVG tek kaynaktır, PNG elle
çizilmez; sayfa kimliği (kanonik adres, og/twitter meta, JSON-LD)
`Base.astro`'da kurulur. Hakkında sayfasındaki yayın takvimi
`site/src/data/yayin_takvimi.json`dan okunur; her adımın saati ilgili iş akışının
cron'undan türetilir ve `bulten/duman.py` ikisini karşılaştırır — cron kayarsa
sınama düşer, sayfa eski saati anlatmaya devam edemez.

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
   TEKRARLAMAZ; onu soğurur. **Tam standart `analiz/YAZIM.md`de, şablon
   `analiz/sablon.mdx`te; kapı `site/tools/analiz_sinavi.py`** (sayfa sınavının
   10. ölçütü): 1 Eylül 2026'dan sonra yayımlanan yazılarda tarihli slug/başlık,
   zorunlu ön bilgi, yönetici özeti ve kapanış bölümü ("Ne ölçmedik") ENGEL;
   eski yazılar değiştirilmez, yalnız bilgi olarak raporlanır. Slug'ın tarihsiz
   kökü SERİ anahtarıdır: aynı kökten yazılar sayfada "bu serinin diğer yazıları"
   kutusuyla birbirine bağlanır — konu kökü yazıdan yazıya aynı yazılır.
   **X gönderisi kendiliğinden çıkar:** `tweet/analiz.py` yayın günü `pubDate`i
   bugün olan yazının yönetici özetini (tez, tablo satırları, rakamlar; `<Deger>`
   canlı çözülür) gönderiye çevirir; defter aynı yazıyı ikinci kez göndermez.

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
| `yaz.py` | yazı katmanının yazma kapısı: `yorum`, `ozet`, `gundem` ve **`duzeltmeler`** (yayımlanmış sayının yapısal düzeltme kaydı — sayfa "Düzeltmeler" bölümü ve `/duzeltmeler/` listesi buradan) |

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

**Kurucu ilke — ikna edici bir tablo, sınanmamış bir kuraldır; ve sınama
ÖRNEKLEM DIŞI olur.** İTO ile TÜFE arasındaki farkın takvim ayı profili son
derece düzgün duruyordu: Mayıs tek eksi ay (−0,44 puan), Nisan/Ekim/Kasım
belirgin artı, ve her birinin makul bir açıklaması vardı (İstanbul'un kira ve
hizmet ağırlığı, okul dönemi, turizm sezonu). Kural olarak koda girmesi
kaçınılmaz görünüyordu. Örneklem DIŞI sınandı: altı kuralın yarıştığı
genişleyen pencerede takvim ayı düzeltmesi İKİ pencerede de SONUNCU, hatayı
0,125 puan BÜYÜTÜYOR. Sebep çubukların üstünde yazıyordu — ay başına 2–3 gözlem
var, yani her ay için tahmin edilen parametre, onu tahmin edecek gözlemden
fazla. Konsaydı sitedeki her aylık tahmin sistematik olarak daha kötü olacaktı
ve hiçbir yeşil koşu bunu söylemeyecekti. Bir örüntü ne kadar iyi bir hikâye
anlatıyorsa onu sınamadan kabul etme eğilimi o kadar güçlüdür; üç gözlemden
kurulmuş her örüntü için bir açıklama bulunabilir. Örneklem İÇİ uyum (R²)
bu soruyu cevaplamaz — sorulacak soru "geçmişe ne kadar uydu" değil, "yarın
hangisini kullanayım"dır.

İkinci yarısı: SIRALAMA DA BİR SONUÇTUR. Aynı yarışta başlangıç penceresi 12
aydan 18 aya çekilince kazanan değişti. Bunun karşılığı "o hâlde 12 ayı
seçeyim" değil, "hiçbir kural için 'en iyisi budur' denemez"dir — ve bu hüküm
metne değil KODA yazılır (`itp_siralama_metin`), çünkü örneklem büyüdüğünde
hükmün kendisi de değişmelidir. Doğru kıyas noktası da naif kural değil
PİYASADIR: aynı pencerede PKA anketi 0,481, İTO kuralı 0,388 verdi ama eşli
farkın p'si 0,414 — yani "İTO piyasadan iyi tahmin ediyor" cümlesi bu veriyle
KURULAMAZ ve kurulmadı.

**Kurucu ilke — "bulamadım" ile "yok" aynı şey değildir; kaynağın kataloğu
TAHMİN EDİLMEZ, İSTENİR.** İTO–TÜFE karşılaştırmasını 2023'e uzatmak için
EVDS'te daha uzun bir İTO serisi arandı. İlk keşif yedi grup kodu TAHMİN etti
(`bie_fgist`, `bie_ito`, `bie_gecinme`…) ve yedisi de boş döndü. Bu sonucun
anlamı "İTO grubu yok" değil, "tahminlerim tutmadı"dır — ve ikisi birbirine
tıpatıp benzer. Doğrusu grup listesini istemekti: `categories/type=json` ucu
açıldı, 154 grup geldi ve adında İTO/İstanbul/geçinme geçen grup gerçekten
YOK. Kod uzayı da ölçüldü: yalnız iki seri veri döndürüyor (`TP.FG.IST1.23`,
`TP.FG.IST2.23`) ve ikisi de 2024-01'de başlıyor; kalan kırk kod HTTP 400.
Ancak bu iki ölçümden sonra "örneklem geriye götürülemez" cümlesi kurulabilir.

Keşif koşusunun kendisi de araca bağlandı: `veri.yml`'in `kesif` girdisi
depodaki bir `kesif*.py`yi `contents: read` ile koşturur, tazeleme hiç
çalışmaz. Önceden bu iş, iş akışı dosyasını bir dalda geçici olarak "keşif
kipine alarak" yapılıyordu; elle yapılan her adım bir gün atlanır ve geri
alma unutulursa main bozulur. İki de tuzak ölçüldü: Python stdout'u tty
olmayan yere TAMPONLUYOR (ilk koşu 20 dakikada tek satır yazmadan iptal
edildi, tamponla birlikte her şey gitti — `python3 -u` şart), ve ıskalanan
her kod istemcinin yeniden deneme bütçesini harcadığı için kod uzayı DAR
tutulmalı. Uzun bir keşifte ilerlemenin görünmesi, keşfin kendisi kadar
önemli.

**Kurucu ilke — bir DIŞLAMA kuralı, dışlayacak veri yokken de kurulur; ve
dışlama silmek değil İŞARETLEMEKTİR.** "2023 outlier, karşılaştırmaya
katmayalım" isteği geldi ama EVDS'te 2023 İTO'su yok. Kural yine de koda
kondu (`DISLANAN_YIL`), çünkü veri geldiği gün kendiliğinden devreye girmesi,
o gün birinin hatırlamasına bel bağlamaktan güvenli. Kuralın üç davranışı
"bir gözlemi atmak veriye müdahaledir; müdahalenin sonucu görünmezse okurun
elinde yalnız bizim sözümüz kalır" ilkesinden türüyor: dışlanan aylar
tablodan ve grafikten SİLİNMEZ (gri sütun, gölgeli aralık, ayrı sembol);
dışlanan dönemin kendi istatistikleri ayrıca yazılır ve iki dönemin farkı
Welch t ile sınanır; bütün kestirim AYNI kodla iki örneklemde birden koşup
sonuç yan yana basılır. Kıyas edilemeyecek sayı da kıyasa SOKULMAZ — tam
örneklemde kural yarışı dışlanan ayları da puanlıyor, yani iki MAE farklı ay
kümesinde ölçülüyor; karşılaştırmaya yalnız katsayılar giriyor. Ve hüküm
metni üç hâlli: dışlanan ay yokken "ayrışmıyor" yazmak, koşmamış bir
sınamanın sonucunu bildirmek olurdu.

**Kurucu ilke — bir denetimin KAPSAMI denetimin parçasıdır.** Sayfa sınavının
1. kuralı doğruydu, koşuyordu, yeşil bitiyordu — ve `<Deger>` kullanımlarının
546'sından yalnız 180'ine bakıyordu. Çünkü yalnız `site/src/content/projeler/`
altını tarıyordu; `<Deger>` sözleşmesi ise koleksiyondan bağımsız (bileşen
`ozet.json`'u `/projeler/<proje>/` genel yolundan çeker). Büyüme yazısı
projeler'den analiz'e taşındığı gün sınavın görüş alanından da çıkmıştı ve
kimse fark etmemişti; borçlanma ve El Niño yazıları hiç girmemişti. Aynı kusur
bu dosyada bir kez daha kayıtlı: hat listesi elle tutulduğu için sınav
hazine-ihrac sayfasına hiç bakmıyordu. İki olayın ortak noktası ölçütün yanlış
olması değil, ölçütün BAKMADIĞI yerin olması — ve bakılmayan yer, geçen
sınavla aynı görünür. Bir denetim eklenirken "bu ölçüt doğru mu" kadar "bu
ölçüt neyi HİÇ görmüyor" da sorulur; kapsam bir listeden değil, sözleşmenin
kendi tanımından türetilir.

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
- `astro.config.mjs` içindeki `site:` alanı yayın adresidir (`https://cocoonish.github.io`);
  kanonik bağlantı, site haritası, RSS ve önizleme kartları bu kökten kurulur.
  Kendi alan adı alınırsa yalnız burası değişir: `robots.txt` bir uç noktadır
  (`site/src/pages/robots.txt.ts`) ve Base/RSS'te yedek adres yoktur — `site`
  tanımsızsa derleme DÜŞER, yanlış kanonik adres basılmaz. Python tarafında
  `yayinla.py` adresi astro.config ile karşılaştırır.
- Bülten dosyalarında otomatik koşu ile yazı katmanı aynı gün dosyasına dokunur;
  bu çakışma **elle çözülmez**. `.gitattributes` + `bulten/birlestir.py` sürücüsü
  yazılı sürümü seçer, önbellekte anahtarları birleştirir. Sürücü `.git/config`'de
  durduğu ve depoyla taşınmadığı için `bulten.py` her koşuda kendini kurar.
  Sürücü komutu kabuktan geçtiğinden **yollar tırnaklanmalı** (depo yolunda boşluk var).

**Kurucu ilke — bir dosyanın SONU, kodun sonu değildir.** `uge_profil`
metrik.py'ye eklendi ve dosyanın sonuna yazıldı — yani `if __name__` kapısının
ALTINA. Python tanımı çalıştırmadan `kos()` koşmaya başladı ve hat NameError
ile düştü; sözdizimi doğruydu, `py_compile` temiz geçti, modül olarak içe
aktarıldığında fonksiyon ÇALIŞIYORDU (yerel sınama bu yüzden yeşil verdi).
Hata yalnız betik olarak koşarken görünüyor ve hattın bütün adımlarını birden
düşürüyor. Derlenmesi, içe aktarılması ve koşması ÜÇ AYRI sınamadır; ilk ikisi
geçti diye üçüncüsü geçmez. Sigorta araca kondu: `guncelle.py`nin ön denetimi
artık her adım betiğini ayrıştırıp kapıdan sonra `def`/`class` arıyor ve
bulursa ENGEL üretiyor — statik, saniyeler sürüyor, koşturmadan soruyor.

**Kurucu ilke — yayın kapısı DERLEMEDEN ve SINAVDAN geçer.** `yayin.yml`
public depoya kopyalamadan önce siteyi derler ve `sayfa_sinavi.py`yi koşturur;
düşerse yayın durur ve iş akışı e-posta gönderir. Yerelde aynı şey `cd site &&
npm run yayin-kontrol`. Sınavın kapsamı büyüdü: (11) her proje sayfasının
HAT_MANSET girdisi ve anahtarı ozet.json'da var mı (eksik pano ana sayfa
tablosundan SESSİZCE düşüyordu), (12) her ozet.json'un `_tarih`i çözülüyor ve
yarından ileri değil (TÜFEX metin karşılaştırmasıyla en ESKİ bacağı hattın
saati yapmıştı, sayfa "81 gün önce" diyordu), (13) lib/bicim dışında yerel
biçimleyici (uyarı), (9b) okur dili derlenmiş çıktıda da (uyarı — bileşen
dizgeleri yalnız orada görünür). KaTeX kapısı aracı ya da node'u bulamazsa
artık yeşil geçmez, düşer. Eskiden ham kaynak
kopyalanıyor, derleme yalnız public depoda yapılıyordu: derleme düşerse site
sessizce eski sürümde kalıyordu (30.08.2026). Aynı ilke tweette:
`tweet/denetim.py` her gönderiyi (bülten, teknik, analiz, özel) gönderimden
önce sınar — tavsiye dili, link (**tweetlerde HİÇ link kullanılmaz** —
kullanıcı kararı; açık adres, www, çıplak alan adı ve X adresi dahil, tanım
`tweet/denetim.LINK`, gönderim katmanı `gonder._gonder_zincir` ikinci kez
kilitler), emoji, HTML kalıntısı, site atfı, sayı
ortasında kesik cümle, boş bölüm etiketi, sorumluluk notu, okur dili — ve engel
varsa gönderim durur. Sorumluluk notu her gönderinin son satırıdır ve kırpmadan
muaftır (`uret._kapat`).

**Kurucu ilke — okur dili HER YAYINDA geçerlidir, tek yerden tanımlanır.**
Kural yalnız site yazıları için değil: bülten, teknik bülten, tweetler ve
proje panoları — okura giden ne varsa. İki aile yasak. **Kod dili**: dosya,
anahtar ve boru hattı adları (`ozet.json`, `metrik.py`, `itp_b_sabit`, MDX,
cron, iş akışı) — okurun elinde bu şeylerin hiçbiri yok. **Yapım dili**: kendi
sürüm tarihçemizin anlatısı ("bu yazının ilk sürümünde şu hata vardı",
"önceki sürümde şöyle yazıyordu", "kod hatasıydı, düzeltildi"). Kalıplar
`ortak/okur_dili.py`de TEK yerde durur ve dört kapı da onu içe aktarır:
`sayfa_sinavi.py` (9. ölçüt), `bulten/denetim.py` (ENGEL), `tweet/ozel.py` +
`tweet/gonder.py` (gönderim durur), `teknik/yaz.py` (yazma reddedilir). Üç ayrı
liste tutulsaydı bir gün sessizce ayrışır ve hangisinin neyi gördüğü kimsenin
aklında kalmazdı. Muafiyetler de tanımın parçası: etiket içi, kod bloğu,
backtick, markdown bağlantı hedefi ve kaynağın kendi BÜYÜK harfli alan adları
(`YLD_YTM_MID`, `TP.PY.P06.ON`) taranmaz — kaynak künyesi okura verilen bir
bilgidir, bizim değişken adımız değil. Alan sözlüğü de yasaklanmaz: "repo" ve
"push" piyasa terimidir. Ölçüt bir kez fazla geniş koşturuldu ve 951 bulgunun
tamamı etiket içiydi; bir denetim yanlış alarm ürettiğinde kimse ona bakmaz,
yani kapsam kadar HASSASİYET de denetimin parçasıdır.

**Kurucu ilke — sayfa okura yazılır, kendi yapımına değil.** Yazılarda ve
tweetlerde "bu kodda şöyle yapılmıştı ama böyle oldu", "yazının ilk sürümünde
şu hata vardı", "ozet.json'dan okunur", "MDX'e dokunulmadan tazelenir" gibi
cümlelerin yeri yok: hiçbiri okurun kararını değiştirmiyor ve metnin
güvenilirliğini de artırmıyor — bulguyu taşıyan cümle kalır, süreç anlatısı
gider. Yapım kararları, ölçüm kusurları ve düzeltme gerekçeleri **sohbette**
konuşulur, commit mesajına ve koda yazılır. Ayrım ince ama nettir: "günlük
hizalama bu olayı −4,8σ, haftalık +0,4σ verir, doğrusu haftalıktır" OKURA bir
şey söyler; "ilk hesabımız günlüktü ve yanlıştı" söylemez. Yayımlanmış bir
SAYININ düzeltilmesi ayrı iştir ve kalır (okur eski sayıya göre karar vermiş
olabilir): tarihli, eski/yeni değerleri yazan kısa bir düzeltme notu — ama
sürüm tarihçesi anlatmadan. Sigorta araca kondu: `sayfa_sinavi.py`'nin 9.
ölçütü bütün içerik dosyalarını tarar ve bu dili bulursa sınav DÜŞER.
