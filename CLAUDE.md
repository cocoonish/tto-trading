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
│   ├── OVP/                     # Orta Vadeli Program: ima edilen kur (GSYH_TL/GSYH_USD),
│   │                            #   program tabloları programlar.json'da ELLE tutulur
│   └── indices/                 # FX haber-duyarlılık endeksi (üç kip: hafif/günlük/tam)
├── teknik/                      # Haftalık teknik analiz bülteni (olc.py ölçer,
│                                #   yaz.py yorum kapısı — her sayı ölçümden; pazar koşusu)
├── tweet/                       # X gönderileri: uret.py bülten/teknik, analiz.py analiz
│                                #   yazısını yönetici özetinden kurar; denetim.py KALİTE
│                                #   KAPISI; gonder.py defterli/bayat-korumalı gönderir,
│                                #   metni arsiv/'e yazar; siteye HİÇBİR ŞEY yazmaz
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
cron'undan türetilir ve `ortak/yayin_takvimi.karsilastir` ikisini karşılaştırır —
`bulten/duman.py` ile sayfa sınavının 16. ölçütü aynı fonksiyonu çağırır; cron
kayarsa sınama da yayın kapısı da düşer, sayfa eski saati anlatmaya devam edemez.
Aynı fonksiyon kapsamı da sınar (sitede çıkan her zamanlanmış yayının X adımı);
`okura: false` adımlar kayıtta durur, sayfaya basılmaz.

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
   ölçüm. **Analizin sayıları SABİTTİR (karar 08.09.2026): yalnız panolar
   canlıdır**; `<Deger>` analizde kullanılmaz, eski yazılardaki etiketler yedek
   metniyle sabit basılır (Yazi.astro `data-deger="sabit"` kabı, sayfa sınavı
   24). Özet, gövdedeki bir kutuyu TEKRARLAMAZ; onu soğurur. **Tam standart `analiz/YAZIM.md`de, şablon
   `analiz/sablon.mdx`te; kapı `site/tools/analiz_sinavi.py`** (sayfa sınavının
   10. ölçütü): 1 Eylül 2026'dan sonra yayımlanan yazılarda tarihli slug/başlık,
   zorunlu ön bilgi, yönetici özeti ve kapanış bölümü ("Ne ölçmedik") ENGEL;
   eski yazılar değiştirilmez, yalnız bilgi olarak raporlanır. Slug'ın tarihsiz
   kökü SERİ anahtarıdır: aynı kökten yazılar sayfada "bu serinin diğer yazıları"
   kutusuyla birbirine bağlanır — konu kökü yazıdan yazıya aynı yazılır.
   **X gönderisi kendiliğinden çıkar:** `tweet/analiz.py` yayın günü `pubDate`i
   bugün olan yazının yönetici özetini (tez, tablo satırları, rakamlar; sayılar
   sayfadaki gibi sabit) gönderiye çevirir; defter aynı yazıyı ikinci kez göndermez.

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

**Kurucu ilke — bir İŞİN bütçesi, adımlarının toplamının ÜSTÜNDE durmalıdır;
ve `if: always()` İŞ zaman aşımına karşı ÇALIŞMAZ.** 04.09.2026 sabahı 45
dakikalık tazeleme çöpe gitti ve bu bir kaza değil, `veri.yml`in kendi
GARANTİSİYDİ: kurulum 5 + tazele 45 + türev 5 = 55 > iş sınırı 50, üstelik
"Hazine ihaleleri" adımının HİÇ zaman aşımı yoktu. 04:22–05:07 tazeleme kendi
sınırını doldurdu, 05:07'de Hazine başladı, 05:12'de İŞ sınırı doldu ve
`if: always()` taşıyan Koşu nabzı ile Commit adımlarının İKİSİ DE pending
kaldı — GitHub iş sınırında `always()` adımlarını da öldürüyor. Elli dakika
yandı, tazeleme damgası hiç ilerlemedi ve bir sonraki koşu aynı elli dakikayı
baştan yakacaktı. Sigorta 27.08'de tam bu kaybı önlemek için konmuştu ve ADIM
zaman aşımına karşı çalışıyordu; kimse İŞ zaman aşımını sormamıştı — bir
sigortanın hangi arızaya karşı çalıştığı konduğu gün yazılmazsa, sonraki
oturum onu her arızaya karşı sanır. Üç düzeltme birlikte gider: işi kesip
DEFTER TUTMAYA yer bırakmak (tazele 45→40, iş 50→65, Hazine'ye tavan), asılan
adımı duvar saatiyle kesip DÖNGÜYÜ SÜRDÜRMEK, ve aritmetiği
`bulten/duman.py`ye ENGEL olarak koymak. O ölçüt bir eşik değil ÖZDEŞLİKTİR —
adım sınırlarının toplamı artı sınırsız adımların ölçülmüş payı, iş sınırını
aşamaz — ve 04.09'un dosyasına karşı koşulduğunda düşüyor, bugünküne karşı
geçiyor. Kural: sınırsız bir adım, kendisinden SONRA gelen bütün adımların
sigortasını yakar.

Kesmenin kendisi de genelleştirildi. `_adim_kos` yalnız doğrudan çocuğu
öldürseydi torunlar (hattın `.venv`i, kazıyıcı, asılı istek) ayakta kalırdı;
süreç AĞACI öldürülüyor ve döngü SÜRÜYOR — bir hattın asılması, tazelenmiş
öbür hatların commit'ini götürmemeli. Çıktı ayrı bir iş parçacığından
pompalanıyor, çünkü hiç çıktı üretmeden asılan bir süreçte okuma döngüsünün
kendisi bloklanır ve zaman aşımı satırına hiç gelinmez; asılmanın en yaygın
biçimi tam olarak budur. Tavan yalnız HAFİF kipte: TAM ve GÜNLÜK kipler
ölçülerek uzun (FX tam kipi 1 sa 45 dk) ve kendi iş akışlarında koşuyor,
onlara hafif kipin tavanını dayatmak haftalık FX koşusunu her hafta öldüren
bir yanlış alarm olurdu.

İkinci yarısı ölçünün kendisiyle ilgili ve "bir denetimin KAPSAMI denetimin
parçasıdır" kusurunun bir eşi: `kosu_nabzi.json` her koşuda ÜZERİNE yazıyordu,
yani "bu sabahki veri penceresi ateşlendi mi" sorusu geriye dönük CEVAPSIZDI —
o sabah altı cron'un hiçbiri ateşlenmemişti ve depoda bunun izi yoktu. Dosya
var, okunuyor, hata vermiyor, yalnızca sorulan soruyu göremiyor. Artık son
altmış koşu birikiyor (tetik ve hangi cron penceresi olduğu dahil); üst düzey
alanlar en son kaydın kopyası olarak KALIYOR ki `denetim.nabiz` ve
`zincir.durum` kırılmasın — biçim değişikliğinin sessizce kırdığı bir okuyucu,
ölçülemeyen yeni bir arıza demektir. Ölçülmeyen bir seviyeye eşik de
KONULMAZ: pencere ateşlenme oranı önce birikir, alarm hakkı sonra verilir.

**Kurucu ilke — bir ALARM, izlediği zamanlayıcıya BAĞLANAMAZ; ve YOKLUK ile
GECİKME ayrı ölçülerdir.** 04.09.2026'da bülten çıktı — 65 dakika geç, ve
kimse haber almadı. İki bağımsız sebepten: (1) `nobetci.yml` YOKLUK soruyor
("bülten yazılmış mı"), oysa o gün bülten 05:50'de yazılmıştı; nöbetçi
06:37'de baksaydı YEŞİL geçerdi, yani arıza onun sorduğu soruya göre HİÇ
OLMAMIŞ sayılır. (2) Nöbetçi zaten hiç koşmadı: kendisi de düşen zamanlayıcıda
ve o sabah pencerenin TAMAMI (veri 02:13/02:41, ölçüm 03:23/03:51, nöbetçi
06:37) ateşlenmedi. Bir alarmın izlediği arıza ile alarmın kendi hata kaynağı
AYNI olduğunda, alarm tam ihtiyaç duyulan günde susar. Depodaki on iş
akışından yalnız `yayin.yml` ve `tweet.yml` cron'suz (push · workflow_run)
ateşleniyordu; alarm oraya, olay akışına taşındı (`gecikme.yml`, CRON YOK) ve
`workflow_run: requested` sayesinde rutinin 04:17'deki tetiklemesiyle uyanır —
koşunun bitmesini beklemeden. Nöbetçi silinmedi, YEDEĞE döndü: tek fonksiyon,
iki taşıyıcı — biri olay tetikli, biri cron'lu.

Kanalın kendisi de ÖLÇÜLDÜ, çünkü "düşen iş akışı e-posta gönderir" cümlesi bu
depoda yalnız ZAMANLANMIŞ koşu için yazılıydı ve yeni taşıyıcı cron'suz. İlk
gerçek alarm ölçümü yaptı: dosya main'e girdiği anda push ile uyandı, bugünün
gecikmesini (39,5 dk, pay 24 dk, darboğaz yazı) ölçtü, sekiz saniyede kırmızı
bitti ve e-posta geldi. Mükerrerlik kaydını da yazdı; aynı gün ikinci kez
sorulduğunda "zaten bildirilmiş" deyip susuyor. Bir yan bulgu kayda değer:
alarmın kendi commit'i ikinci bir koşu TETİKLEMEDİ — GitHub, `GITHUB_TOKEN`
ile atılan push'lardan iş akışı ateşlemiyor, yani alarm yapısal olarak kendini
besleyen bir döngüye giremez. `workflow_run` yolu da aynı gün ölçüldü: iki
koşu o tetikleyiciyle uyandı ve ikisi de yeşil bitti, yani hem taşıyıcı hem
mükerrerlik bastırması gerçek olayda çalışıyor. Geriye tek bileşim kaldı —
`workflow_run` + DÜŞME; ölçülen düşme push kaynaklıydı ve üç koşunun aktörü de
aynı, ama "aynı mekanizma" bir çıkarımdır, ölçüm değil.

Ölçünün tanımı da tek yerde (`bulten/gecikme.py`) ve söz KODA YAZILMADI,
`site/src/data/yayin_takvimi.json`dan çözülüyor: sitenin okura ilan ettiği saat
neyse gecikme ona göre ölçülür, cron kayarsa `karsilastir()` ikisini birlikte
kaydırır. Ve bir YAPISAL KİLİT: o modülde yayını durduran bir sınıf HİÇ
TANIMLI DEĞİL (`SINIFLAR = zamaninda · uyari · alarm`), duman sınaması hem
sabiti hem kaynak metnini sınıyor. Sebebi 02.09'da ölçüldü: yayının önünde
duran bir denetimin yanlış alarmı siteyi on iki saat durdurmuştu. Geç kalmış
bir bülteni DURDURAN kapı, gecikmeyi yokluğa çevirir — yani ölçtüğü şeyi
büyütür.

**KARAR (04.09.2026, kullanıcıya açıkça soruldu).** Kurtarma yolunu kısaltmak
için bir "sabah bütçesi" tasarlanmıştı: araç kalan zamanı hesaplayıp sığmayan
hattı dünkü sürümde bırakacaktı. REDDEDİLDİ — "veri tam olsun, geç çıksın".
Gerekçe kayda geçsin ki bir sonraki oturum aynı şeyi yeniden önermesin:
"zamanında ama bir hattı bayat" ile "geç ama tam" arasındaki tercih EDİTORYAL
bir karardır ve bir araca devredilmez; enflasyon günü kredi hattının bir gün
eski kalması, yirmi dakikalık gecikmeden pahalı olabilir. Bütçe yerine
gecikmenin ÖLÇÜLMESİ ve ALARM VERMESİ seçildi: bülten gerektiği kadar geç
çıkar, ama artık sessizce geç çıkmaz.

**AÇIK SORU — bu planın kapatmadığı tek nokta arızası.** Cron'lar düştüğünde
zinciri başlatan ilk uyanma hâlâ claude.ai rutinidir ve bir aracı depo dışı
zamanlayıcı KURAMAZ (27.08'de ölçüldü). Depo dışı ikinci bir tetikleyici
(cron-job.org vb.) soruldu ve şimdilik istenmedi; gerekçe, rutinin bugüne
kadar hiç düşmemiş olması — düşen hep GitHub cron'ları oldu. Rutin düşerse bu
plan onu YAKALAYAMAZ; yakaladığı şey cron'ların düşmesidir.

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

**Kurucu ilke — AĞA ÇIKAN bir giriş noktası, ağa çıkmayan hiçbir işi içinde
tutmamalı.** Duman sınamaları ağa çıkmaz; öyleyse ağa çıkan bir `kos()`un
İÇİNDE duran her ölçüm, döküm ve kayıt kurulumu hiçbir kapı tarafından
KOŞTURULMAZ. YPMevduat'ta ölçüldü (05.09.2026): duman koşarken ölçüm katmanının
giriş noktasının 195, özetinkinin 189, çizimninkinin 34 satırı çalışıyordu —
veri katmanınınki SIFIR. Bulunan kusur da tam oradaydı: künye döngüsü kimlik
kayıtlarının TAMAMINDAN `maks_fark` okuyordu, oysa denetim üç ayrı biçimde
kayıt yazıyor (eşitlik · kapsanma · sınanamadı) ve ikinci tür eklendiği gün
hattın BİRİNCİ adımı her koşuda KeyError ile ölürdü; ölçüm, çizim, özet hiç
koşmazdı. Derlenmesi, içe aktarılması ve koşması üç ayrı sınamadır ve üçüncüsü
kimsenin bakmadığı yerdeydi. Düzeltme iki parçalı ve ikisi de genelleştirilir:
(1) ağa çıkmayan iş AYRI fonksiyonlara çıkar (`durum_kaydi` · `kosu_dokumu`) ve
duman onları GERÇEK çerçeveyle çağırır; ayrıca ağa çıkan tek çağrı (`cek_kume`)
sarmalanıp giriş noktasının KENDİSİ de koşturulur — kapsam kapısı ve dosya
yazımı dahil. (2) Bir döküm kaydın alanlarını SORAR, varsaymaz: tanımadığı
kaydı düşmeden, ADIYLA basar — sessizce atlamak, ölçülmemiş bir şeyi ölçülmüş
gibi göstermenin en sessiz biçimidir. Yapısal kilit de kapıya kondu: `kos()`
gövdesinde ölçüm çağrısı kalırsa duman DÜŞER, yoksa bir sonraki oturum onları
geri taşır ve kapsam sessizce sıfıra döner.

**Kurucu ilke — yayın kapısı DERLEMEDEN ve SINAVDAN geçer.** `yayin.yml`
public depoya kopyalamadan önce siteyi derler ve `sayfa_sinavi.py`yi koşturur;
düşerse yayın durur ve iş akışı e-posta gönderir. Yerelde aynı şey `cd site &&
npm run yayin-kontrol`. Sınavın kapsamı büyüdü: (11) her proje sayfasının
HAT_MANSET girdisi ve anahtarı ozet.json'da var mı (eksik pano ana sayfa
tablosundan SESSİZCE düşüyordu), (12) her ozet.json'un `_tarih`i çözülüyor ve
yarından ileri değil (TÜFEX metin karşılaştırmasıyla en ESKİ bacağı hattın
saati yapmıştı, sayfa "81 gün önce" diyordu), (13) lib/bicim dışında yerel
biçimleyici (uyarı), (9b) okur dili derlenmiş çıktıda da (uyarı — bileşen
dizgeleri yalnız orada görünür), (17) koşu kaydının okur dili — hatların
`uyarilar.json` satırları ve `ozet.json`un CÜMLE olan her metin alanı sayfaya
olduğu gibi basılır — kod ve yapım dili ENGEL, anahtar adı ve biçim UYARI.
Tam ve bağlayıcı liste `sayfa_sinavi.py` başlığındadır (2c, 11b–11d, 14, 15,
16 dahil); bu paragraf onu ÖZETLER, kapsamı o dosya tanımlar. KaTeX kapısı
aracı ya da node'u bulamazsa
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
proje panoları — okura giden ne varsa. Hatların KOŞU KAYDI da öyle:
`uyarilar.json` satırları ve `ozet.json`un cümle olan her metin alanı sayfaya
olduğu gibi basılır (koşu kutusu, `<Deger>`), ve hatların Python'u onları OPERATÖR için
yazıyordu — `kkm_aktif` bayrağı, `bie_pydibsarsiv` grubu, '5.2%', "`python
irfcl_arsiv.py` ile doldurun" okura gitti, dokuzuncu ölçüt yeşildi (kaynak MDX
değil, veri dosyası). `okur_dili.kosu_kaydi_tara` bu satırları MUAFİYETSİZ
tarar (backtick orada kod göstermez), iki parçalı anahtar adı, `bie_` kodu,
anahtar:tarih çifti ve biçim sözleşmesini (ondalık nokta, ISO tarih, ASCII
eksi) de sorar; `guncelle.py` hat koştuğu anda uyarır, sayfa sınavı (17) iki
ağırlıkla kapı olur: şablondan başka yerden gelemeyecek kusur (backtick, dosya
adı, `bie_` kodu, komut anahtarı, yapım dili) ENGEL; bir yer tutucudan
sızabilecek anahtar adı ve biçim UYARI — veri kaynaklı bir sızıntı günün
bültenini durdurmaz, ama adıyla görünür. Hattın uyarı şablonu sayıyı
`ortak/bicim`den yazar. İki aile yasak. **Kod dili**: dosya,
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

**Kurucu ilke — SIFIR bir ölçüm sonucudur; ölçülemeyen boş bırakılır.**
Altın fiyat etkisi Γ(L) = Q(L)·[P(L+1) − P(L)] iki uçtaki fiyatı ister. Fiyat
serisi tatilde son değerini taşır (`ffill`) ve bu doğrudur: piyasa kapalıysa
fiyat gerçekten kımıldamamıştır, Γ = 0 bir ölçümdür. Ama besleme DURDUĞUNDA
seri aynı görünür ve Γ yine 0 çıkar — bu kez ölçüm değil, ölçememenin izidir.
Ölçüldü (02.09.2026, 918 iş günü): fiyat 14 günde taşınmış ve Γ'nın sıfır
çıktığı günlerin TAMAMI (14/14) taşımadan doğuyor; gerçek kotasyonla ölçülmüş
tek bir sıfır yok. Yani sayfada yayımlanan her "günün fiyat etkisi 0,00" sahte
ve okur onu "TCMB bugün altında hiçbir şey yapmadı" diye okuyor. İkisini ayıran
şey taşınan günden SONRA gerçek kotasyon gelip gelmediğidir: geldiyse tatil,
gelmediyse kesinti — bu yüzden yalnız serinin SAĞ UCUNDAKİ taşıma bloğu
maskelenir, ortadaki bloklar dokunulmadan kalır. Maske Λ'ya ancak ΔQ ≠ 0 iken
uygulanır: miktar kımıldamadıysa Λ fiyattan bağımsız olarak TAM sıfırdır ve
ölçülebilen bir sıfırı boşaltmak da bir kusurdur. Sigorta imzaya kondu:
`fiyat_kaynak` argümanının VARSAYILANI YOK — bir çağrı yerinde unutulursa
TypeError verir, sessizce sahte sıfır üretmez (bir çağrı yeri gerçekten
unutulmuştu). Ve ölçülemeyen bir seans sayfada görünür: akım serisinin
seviyeden kaç seans geride kaldığı ve SEBEBİ tek cümleyle yazılır, besleme
yetiştiğinde cümle kendiliğinden döner.

**Kurucu ilke — bir ŞEKLİN tarihi, HATTIN tarihi değildir.** FX haber endeksi
sayfasında on figürün hepsi "veri 03.09.2026" diye damgalanıyordu; oysa dördü
GDELT haftalık arşivinden geliyor ve 30.08'de bitiyordu, biri temmuzdaki
kalibrasyona aitti, biri de yapısal olarak bir hafta geride. Sebep basit:
`GrafikEmbed`, `tarihAnahtari` verilmemişse hattın TEK ana saatini basıyor.
Kusur okura iki yönde birden yalan söylüyor — bayat panel taze görünüyor, ve
okur tek damgayı sayfanın tamamına yorup TAZE endeksi bayat sanıyor.
Kullanıcının ilk cümlesi buydu: "aşağıda haberlerin geldiğini görüyorum ama
endeks yenilenmemiş gibi duruyor." Endeks yenilenmişti; yenilenmeyen şey
etiketti. Çözüm `<Deger>`de zaten olan sözleşmenin şekle taşınması: hat her
figürün ucunu KENDİ çizen kodundan ilan eder (`ozet.json` → `_sekil_tarih`),
bileşen sırayla açık anahtar → defter → ana saat der, ölçülemeyen uç `null`
kalır ve o şeklin altına tarih HİÇ basılmaz. Kapı da kondu
(sayfa sınavı 18): defter açan hatta yarından ileri tarih ENGEL, girdi eksiği
UYARI — bir figürün unutulması yayını durdurmaz ama adıyla görünür.

**Kurucu ilke — bir figürün damgası BAĞLAYICI bacaktır; ve bazı figürler tek
bir günle dürüst anlatılamaz.** Kural bütün hatlara yayılırken asıl soru
"hangi tarih" değil, "iki bacaklı bir figürde HANGİSİ" oldu. Cevap en eskisi:
figürün sözü serilerin KIYASIDIR ve kıyas ancak hepsinin ölçüldüğü güne kadar
kurulabilir; en tazesini yazmak öbür bacağı olduğundan yeni gösterir. TL taşıma
Şekil 01 ve 03'te nakit bacağı TLREF'e, tahvil bacağı DİBS'e bağlı ve ayrı
düşebiliyor — `min()` bu yüzden yapısal yazılır, bugünkü sıralamaya bakmaz.
Ama bacaklar birbirinden çok uzaksa en eskisi de yalan söyler: ödemeler dengesi
Şekil 12'de eurobond akımı aylık (30.06), ödeme takvimi haftalık (26.08) biter
ve aradaki 57 günde hangi bacak seçilse öbürü hakkında yanıltıcı olur. Üçüncü
yol damgayı İKİ PARÇALI yazmaktır ("aylık 30.06.2026 · haftalık 26.08.2026");
bileşen tanımadığı dizgeyi olduğu gibi basar. Dördüncü hâl de var: Kredi Şekil
03'ün dört paneli üç ritimde ve tek damga hangisi olursa olsun bir grubu
yanıltır — defterde `None`, sayfada tarih YOK, her panel kendi saatini kendi
başlığında taşır.

Bu genişleme yeni bir kusur sınıfını da açtı: figürün İÇİNDEKİ alt yazı
("Çıpa: 2 Eylül 2026") okura sayfa damgası kadar görünür ve iki taraf ayrı
kaynaktan besleniyordu. Fonlama Şekil 05'in hiçbir paneli 02.09'da bitmiyor;
o tarih hattın ana saatiydi ve figürün içine basılıyordu. Kural: hat figür
saatlerini TEK bir fonksiyonda tutar ve hem çizim koduna hem özet üreticisine
oradan verir (`Kredi/veri.py` → `sekil_saatleri`). İki ayrı liste bir gün
sessizce ayrışır ve hangisinin neyi söylediği kimsenin aklında kalmaz.

Yayılmanın ölçüsü tekrarlanabilir tutuldu, çünkü "kaç figür yanlış" sorusunun
cevabı ölçme yöntemine bağlı. Sitedeki 411 gömülü figürün 237'si derslere ait
statik dosyalar (özetleri yok, zaten tarih basılmıyor); damga sözleşmesi kalan
174'ü bağlıyor. Bunların 92'si TEK SAATLİ, yani çizilen bütün izler aynı günde
bitiyor. O 92 figürde tarama 12 aday verdi, 10'u gerçek çıktı ve onu da
kapandı. Kalan 82 figür karma; onlarda "doğru tarih" tek bir ölçüyle
tanımlanamadığı için hat hat, bacak bacak ölçüldü — 28 figürün damgası değişti.

Kalan iki aday TARAMANIN kendi yanlış pozitifiydi ve ikisi de aynı dersi
veriyor: **bir figürün son x değeri, verisinin ucu DEĞİLDİR.** Hazine
`vade_talep` çeyreklik kovalarla çiziliyor ve son kova 2026-07-01 diye
etiketli — ama o kova AÇIK çeyrektir ve içindeki en yeni ihale 18.08'dir, yani
damga zaten doğruydu. Enflasyon `13_ito_bulut`ta on izin dokuzu tarihsiz saçılım;
tek tarihli iz "farkın EKSİ olduğu aylar" filtresi ve son eksi ay 2026-05 —
serinin ucu değil, alt kümenin ucu. İkisinde de ölçüt "yanlış tarih" diye
bağırıyordu ve sayfa doğruydu. Otomatik tarama kusuru BULUR, hükmü figürün ne
çizdiğine bakan biri verir.

En büyük ayrışmayı tarama DEĞİL, hat hat ölçüm buldu: enflasyon Şekil 05'in
sekiz izinden YEDİSİ 2025-12'de bitiyor (`dagilim.csv` orada donmuş) ve sayfa
onu 08.2026 diye damgalıyordu — 245 gün. Tek bir iz (TÜFE 3a SAAR referansı)
bugüne kadar geldiği için figür "karma" sayılıyor ve tek-saatli tarama ona
BAKAMIYOR. Otomatik ölçüt tartışmasız olanı bulur; tartışmalı olanı gözle
ölçmek gerekir.

Aynı hattın kuyruğunda ikinci bir kusur çıktı ve o damgayla değil BİLEŞENLE
ilgili: `Deger.astro`nun KENDİ tarih ayrıştırıcısı vardı ve `AA.YYYY` yazımını
tanımıyordu. Aylık bir saat gün gibi yazılamayacağı için (`01.07.2026` okura o
GÜNÜN ölçümü gibi görünür) o yazım her yerde kullanılıyor — sonuç: on beş
`*_tarih` anahtarının, aralarında bütçe ve enflasyon hatlarının ANA saatinin,
bayatlık denetimi sessizce KAPALIYDI. Ayrıştıramayan bir denetim hep "sorun
yok" der. Ayrıştırma `lib/bicim`e devredildi; ölçüm katmanındaki eşiyle
(`ortak/bicim.py`) aynı sözleşme, tek tanım.

Kapıya iki basamak daha kondu: 18b açık `tarihAnahtari`nin gerçekten çözülüp
çözülmediğini sorar (anahtar yok/dizge değil → UYARI, yarından ileri → ENGEL,
birleşik damganın İÇİNDEKİ her tarih ayrı ayrı), 18c ise aynı figüre konmuş iki
ilanın (açık anahtar + defter) ÇELİŞMEDİĞİNİ. İkisi de `site/tools/duman_sinav.py`
ile sınanıyor — çünkü bu ölçüt yayının önünde duruyor ve yanlış alarmı siteyi
durdurur; birleşik damgayı kusur sayan bir sürüm tam olarak bunu yapardı.

**Kurucu ilke — okur dili kapıları FİGÜRÜN İÇİNE de bakar; ve bir sınav
bakmadığı hattı geçmiş sayar.** Yayılma iki kör nokta daha açtı, ikisi de
"bakılmayan yer, geçen sınavla aynı görünür" sınıfından. Birincisi: okur dili
ölçütleri MDX'i (9), derlenmiş sayfayı (9b) ve koşu kaydını (17) tarıyordu ama
gömülü Plotly HTML'inin BAŞLIK ve ALT YAZI metnini hiçbiri taramıyordu — oysa o
metin şeklin tam üstünde, okurun gözünün ilk gittiği yerde duruyor. Ölçüldü:
164 figürde 76 kod/yapım dili sızıntısı, aralarında okura kendi sürüm
tarihçemizi anlatan bir alt yazı ("bu halka yazının ilk sürümünde
ölçülmemişti"). Yeni ölçüt (19) yapım dilini ENGEL sayıyor (taban sıfıra
indirildi), kod dilini TEK satırda toplanan UYARI (taban yetmiş altı; hepsini
engel yapmak yayını mevcut kusurla durdururdu, ve `bie_` grup kodunun kaynak
künyesi mi kod dili mi olduğu ayrıca karar ister). İkincisi: sayfa sınavı
özeti HATTIN KLASÖRÜNDE arıyordu ve yiyecek-hizmetleri-marj hattı özetini
başka bir dizine yazdığı için BÜTÜNÜYLE atlanıyordu — on yedi figürlü, doksan
`<Deger>` çağıran bir sayfa aylarca hiçbir ölçüte girmedi. Kapsam listeden
değil SÖZLEŞMEDEN türetilir: sayfanın okuduğu dosya
`site/public/projeler/<slug>/ozet.json`dur, sınav da artık onu okuyor.

**Kurucu ilke — YAYININ ÖNÜNDE DURAN denetimin yanlış alarmı, arızanın
kendisidir; ve bir ÇAKIŞMA araması tesadüf üretir.** 02.09.2026 16:46'dan
03.09 04:31'e kadar yayın iş akışı arka arkaya ALTI KEZ düştü, site on iki
saat dondu ve günün bülteni yayına hiç çıkmadı. Depoda tek bir dosya
değişmemişti: DİBS hattının verisi tazelendi, `kimlik_cok_kaynakli` 52'den
51'e ve `spot_3a` 37,06'dan 36,79'a indi, ikisi de sayfadaki UYDURMA aritmetik
örneğinin sabitleriyle ("gösterge fiyatı 51,00 TL olsun", "yıllık kupon oranı
%36,8") tesadüfen çakıştı ve çıplak oynak sayı ölçütü bunu ihlal saydı. Ölçüt
doğruydu, sayfa doğruydu, kusur ÖLÇÜTÜN HASSASİYETİNDEYDİ. Aynı kutu bir kez
daha çarpışmıştı (40,03 ile `forward_1y1y`) ve o zaman anahtar bazlı bir
muafiyet konmuştu — yanlış araç: anahtarı sayfanın TAMAMINDA kör eder, yani
gerçek bir donmuş sayıyı da kaçırır, ve bir sonraki tesadüf için hiçbir şey
yapmaz. Doğrusu sebebi adlandırmak: o kutudaki sayılar veri değil VARSAYIM,
öyleyse kutu işaretlenir (`sinav-ornek`). Üç hassasiyet kuralı ölçülerek
kondu: uydurma kutuları tarama dışı, TAM SAYI yalnız kendi yazımıyla aranır ve
bulgusu UYARI (sayımların çoğu yöntemsel sabittir — 250 iş günlük pencere, 100
günlük tolerans), eksi işareti sayının parçasıdır ("−22,1" pozitif 22,1 ile
eşleşmez). Örneklem dışı sınandı: 63 geçmiş veri sürümü bugünkü sayfalara
karşı koşuldu, düzeltmeden önce 1 sürüm yayını durduruyordu, sonra 0. Ve
sınavın kendisi artık sınanıyor (`site/tools/duman_sinav.py`, yayın kapısının
İLK adımı): bir denetim yayının önünde duruyorsa, onun yanlış alarmı da bir
arızadır ve regresyon sınaması ister.

**Kurucu ilke — hattın duman sınaması, hattın koşusunun içindedir.** Bir hat
klasöründe `duman.py` varsa `guncelle.py` onu adımlardan ÖNCE koşturur ve
düşerse hat koşmaz; `--denetle` de aynı yardımcıyı çağırır. Sınama yalnız
`--denetle` yazan birinin eline bağlı kalsaydı zamanlanmış koşu onu hiç
sormazdı — ve bozuk bir ölçüm katmanı çıktısını siteye kopyalamış olurdu.
Sınamada duran her madde bir gün gerçekten yanlış yayımlanmış bir sayıdır;
ağa çıkmaz, saniyeler sürer.

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

**Kurucu ilke — YAYIMLANMIŞ BİR BELGE de bir veri kaynağıdır, ama CANLI
DEĞİLDİR; ve iki cins bacağı tek damgayla anlatmak iki yönde birden yalan
söyler.** Orta Vadeli Program hattının iki bacağı var: yılda bir yayımlanan,
bir daha değişmeyecek bir tablo ve her iş günü ilerleyen bir kur serisi.
Aralarındaki mesafe bir yıla varıyor. "Karma figürde damga EN ESKİ bacaktır"
kuralı burada düz uygulansaydı TAZE kur bacağı bir yıl bayat görünürdü — kuralın
önlemek için yazıldığı iki kusurdan İKİNCİSİ. Kural belgeye değil CANLI seriye
konur; belge bacağı damgada ADIYLA durur ("program 09.2025 · kur 03.09.2026").
Bunun bir uzantısı da ölçüldü: belgenin kapağı yalnız AYI yazıyor, gün belgede
geçmiyor. Bir ay damgası ortak/bicim sözleşmesinde ayın SON gününe demirlenir
ve ay henüz kapanmadıysa o gün YARINA düşer, yani yayına giden bir damga
ölçülmemiş bir günü ilan eder. Ay kapanmadan gün yazılmıyor: o figürün damgası
o gün için yalnız canlı bacağı taşır, program sürümü figürün KENDİ alt
başlığında okura yine görünür, ve ay kapandığı gün damga kendiliğinden gelir.
Birleşik damganın nereye yazılacağı da sözleşmenin parçası: şekil saat defteri
(`_sekil_tarih`) çözülebilir TEK bir tarih ya da `null` ister ve çözemediğini
ENGEL sayar, o yüzden birleşik damga MDX'in açık `tarihAnahtari`sine düşer.
İkisi de AYNI fonksiyondan mekanik olarak ayrılıyor (`veri.defter_ayir`), çünkü
elle tutulan iki liste bir gün sessizce ayrışır.

**Kurucu ilke — bir TAHMİN TABLOSUNUN sütunu üç türlüdür ve ölçüt hangisine
baktığını bilmelidir.** Program tablosunda gerçekleşme, gerçekleşme tahmini ve
program sütunları yan yana durur. Hattın yöntem sınaması (ima edilen kur ile
gerçekleşen günlük ortalamanın farkı) yalnız KAPANMIŞ ve GERÇEKLEŞME olarak
yayımlanmış sütunlarda kurulur: tahmin sütunundaki fark yöntem farkı değil
TAHMİN hatasıdır, program sütunu henüz olmamış bir yıldır, açık bir yılın yarım
ortalaması da yıl ortalaması değildir. Ayrım yapılmasaydı geçen yılın kendi
tahmin hatası (+%0,39) ölçünün güvenilmezliği gibi görünürdü; ayrımla birlikte
sınama iki kapanmış yılda +%0,12 ve %0,00 veriyor, yani "ima edilen kur pratikte
USD/TRY ortalamasıdır" cümlesi bir varsayım değil bir ÖLÇÜM. Sınama her koşuda
yeniden yapılıyor ve sonucu yayımlanıyor — bir kez doğrulanıp bırakılan hüküm,
kaynak yöntemini değiştirdiği gün sessizce yanlışa döner. Aynı sebeple elle
tutulan tablonun KENDİ özdeşlikleri de her koşuda sınanıyor (nominal gelir
artışı = (1+büyüme)(1+deflatör); cari denge oranı; faiz gideri oranı; dış
ticaret dengesi = ihracat − ithalat): elle aktarılan bir tabloda kayan bir hücre
hiçbir yerde hata vermez, yalnız sayfada yanlış bir sayı görünür.

**Kurucu ilke — İKİ VARSAYIMIN AYNI SONUCU VERMESİ ancak ikisi AYNI KISITI
tutturuyorsa bir sonuçtur.** Yıl ortalaması bilindiğinde yıl sonu seviyesi hâlâ
patikanın biçimine bağlı; hat iki uç varsayımı (doğrusal ve üstel) ayrı ayrı
çözüp ikisini de yayımlıyor ve yakın çıkmalarını sayfada bir SAĞLAMLIK sonucu
olarak sunuyor. O cümle ilk yazımda geçersizdi: doğrusal çözüm "ortalama uçların
ortasıdır" kestirmesiyle yazılmıştı ve bugünü bir kez daha sayıyordu, yani
kısıtı SAĞLAMIYORDU — üstel çözüm bugünü saymıyor. İki patika farklı kısıtları
tutturunca "yakınlık" bir tesadüfe döner ve sayfadaki hüküm dayanaksız kalır.
Duman sınaması bu yüzden yakınlığı değil KISITI ölçüyor: her iki patikanın da
hedef ortalamayı tutturduğu ayrı ayrı sınanıyor. Kusur ancak o ölçüt yazıldıktan
sonra görüldü — yakınlığı sınayan bir ölçüt (fark < %1) her iki hâlde de yeşil
geçerdi.

**Kurucu ilke — bir KONVANSİYON ölçünün parçasıdır; ve bir ölçünün RESMÎ
karşılığı varken onu yeniden türetmek, türetmenin doğruluğunu da ölçmeyi
gerektirir.** Gerçekleşen taşımada lira bacağı önce GÖZLEM GÜNLERİ üzerinden
bileşiklendi — her kotasyon bir günlük faiz taşıyor sanıldı. Yanlıştı ve
yanlışlığı ölçünün kendisi kadar büyüktü: gecelik bir faiz TAKVİM günü taşır,
cuma kotasyonu pazartesiye kadar üç gün işler. 2026 yılı başı → 03.09 arasında
resmî ölçü (BİST TLREF Endeksi) %+29,61, gözlem günüyle %+19,58 — 10,03 puan,
yani taşımanın kendisiyle aynı mertebede. Kusuru pahalı yapan şey de buydu:
sayfanın manşet sorularından biri "ne kadar taşıma getirisi verdi" ve cevap
neredeyse yarı yarıya eksik çıkıyordu.
İki ders birden çıktı. Birincisi: RESMÎ ÖLÇÜ VARSA O KULLANILIR. Endeks
hattın zaten okuduğu dosyada, YAN SÜTUNDA duruyordu; gün sayımı, tatil ve
yuvarlama onun sözleşmesinde çözülmüş. Kendi türetmemiz ancak endeks yokken
devreye giriyor ve hangi yolun kullanıldığı kayda geçiyor (`tl_yol`).
İkincisi ve daha sinsisi: DUMAN SINAMASI YANLIŞ KONVANSİYONU KİLİTLİYORDU —
"lira bacağı gözlem günleri üzerinden bileşikleniyor" diye bir iddia yazılmıştı
ve yeşil geçiyordu. Bir kusuru sınamaya yazmak onu kalıcı yapar; sınama artık
gözlem günü konvansiyonunun KULLANILMADIĞINI, endeks varsa ondan gelindiğini
ve figürle özetin aynı konvansiyondan beslendiğini sınıyor.
İleriye dönük taşımada ise iki konvansiyon BİRDEN yayımlanıyor: basit olan
yıllık faiz kotasyonunun yıllık devalüasyona bölünmesi (sayfadaki ex-ante reel
faizle aynı konvansiyon, yani onunla kıyaslanabilir), bileşik olan gecelikte
dönen bir pozisyonun gerçekten biriktirdiği getiri (gerçekleşen bacakla aynı
konvansiyon). Tek konvansiyon yazılsaydı sayfadaki iki sayıdan biri öbürüyle
kıyaslanamaz olurdu ve okur bunu göremezdi. Ve ileriye dönük bacağın taşıdığı
varsayım (lira faizinin sabit kalması) okura AYRI bir cümlede yazılıyor: bir
projeksiyonun varsayımı gizlenirse okur onu ölçüm sanır.

**Kurucu ilke — bir YIL sayı değil ETİKETTİR.** Özet üreticisi yıl sütunlarını
sayı olarak yazıyordu ve sayfa onları biçim sözleşmesinden geçirip binlik
ayracıyla "2.026" diye basıyordu. Kusur hiçbir hesabı bozmuyor, hiçbir kapıyı
düşürmüyor ve yalnızca okurun gözünde bir yılı bir miktara çeviriyordu; sayfa
sınavının "statik yedek sapması" bilgisi onu ancak yan etkiyle gösterdi.
Adlandırdığı şey bir gözlem değil bir SÜTUN olan her anahtar metin yazılır ve
hiçbir ölçüme, sapma taramasına ya da bayatlık hükmüne girmez.

**Kurucu ilke — bir SAYFA silindiğinde ona bağlanan bağ hiçbir yerde hata
vermez; ve o bağı çoğu zaman kaynak değil bir BİLEŞEN kurar.** OVP panosu
kaldırıldı — ölçüm hattı ve analiz yazısı kaldı, ikisi aynı şeyi anlatıyordu ve
pano gereksizdi. Silme işlemi hiçbir yerde hata vermedi, vermezdi de: bültenin
kaynak notu hattın slug'ını `/projeler/<slug>/` adresine BİLEŞENDE çeviriyordu
ve o adres kaynakta hiç yazmıyor. Aynı satır hattın ADINI da panonun
başlığından okuyordu, yani sayfa gidince okura slug basacaktı. İkisi de tek bir
sessiz varsayımdan doğuyor: HER HATTIN BİR PANOSU VAR. Varsayım kırıldığı gün
404 ile kod dili birlikte gelir ve koşu yeşil biter. Sözleşme yeniden yazıldı:
bir hattın sayfası, o hattın `ozet.json`unu OKUYAN sayfadır — panosu varsa
pano, yoksa `<Deger proje="<slug>">` çağıran en yeni analiz, hiçbiri yoksa bağ
HİÇ KURULMAZ (`site/src/lib/hatSayfa.ts`); ad ise ölçüm katmanının kayda
yazdığı `hat_ad`dan gelir (tek tanım `bulten/ayar.HAT_ADI`), pano başlığından
değil. İki kapı kondu ve ikisi de arızaya karşı koşturularak sınandı: sayfa
sınavının 20. ölçütü derlenmiş çıktıdaki her `href="/…"` hedefini sorar —
kaynağa değil ÇIKTIYA bakar, çünkü bağı bileşen kurar — ve `bulten/duman.py`
izlenen her hattın adının tanımlı olduğunu, kaydın da onu taşıdığını sınar.

**KARAR (07.09.2026, kullanıcı) — site X gönderisini OKURA GÖSTERMEZ; hesap
hiçbir yere yazılmaz.** Bülten, teknik ve analiz künyelerinde "Paylaşım ·
X gönderisi ↗" satırı vardı ve hakkında sayfası her yayının X'te de çıktığını
söylüyordu. Kaldırıldı. Tweet ATILMAYA devam ediyor — değişen, sitenin
gönderiye bağ vermesi ve X'ten söz etmesi. Kaldırma yalnız metni silmekle
bitmiyor, çünkü bağı METİN DEĞİL BİLEŞEN kuruyordu: künye satırı `lib/x.ts`
üzerinden tweet defterinin site aynasını (`site/src/data/tweet/defter.json`)
okuyordu ve o ayna gönderim katmanınca her gönderide yazılıyordu. Zincirin
tamamı gitti: künye satırları, `lib/x.ts`, ayna dosyası, `gonder.py`nin ayna
yazımı, iki tweet iş akışının `git add` yolu. Sonuncusunda gizli bir tuzak
vardı ve tam da bu depoda bir kez ölçülmüştü: `tweet-ozel.yml` dört yolu TEK
`git add` satırında veriyordu ve git, listedeki tek bir yol bile yoksa komutun
TAMAMINI reddeder — ayna kalkınca defter ile arşiv sessizce sahnelenmez,
mükerrer gönderi riski doğardı. Bir yolu kaldırırken o yolun geçtiği HER
komutun hata davranışı sorulur.
Yayın takviminin "X gönderisi" adımları SİLİNMEDİ, `okura: false` oldu: adım
kayıtta durur ve `tweet.yml`in cron kayması ölçülmeye devam eder, sayfaya
basılmaz. Bir denetimi, ölçtüğü şeyin okura görünmemesi gerekçesiyle
kaldırmak, ölçümü de kaldırmaktır.
Kapı sayfa sınavının 21. ölçütü: derlenmiş çıktıda x.com/twitter.com adresi ve
"X gönderisi" yazısı ENGEL. Hassasiyeti ölçülerek kondu — `twitter:card`
meta'sı (hesap adı taşımaz) ve Türkçe "paylaşım" sözcüğü (bir araştırma
yazısında iktisadi anlamıyla geçiyor) taranmaz; altı regresyon maddesi
`site/tools/duman_sinav.py`de.

İzin kaldırılması iki kör noktayı daha açtı ve ikisi de bu dosyada adı konmuş
kusur sınıflarının eşi. Birincisi ÇALIŞMIYORDU ve yeşil bitiyordu: gecikme
ölçüsünün X bacağı site aynasından gerçek deftere (`tweet/defter.json`)
taşındı, ama alarmı taşıyan `gecikme.yml` SPARSE-CHECKOUT ile koşuyor ve
listesinde `tweet` yoktu — koşucuda dosya hiç bulunmuyor, `_json` istisnayı
yutuyor, bacak her gün ölçülemiyor ve iş akışı YEŞİL bitiyor. Sparse ağaç
birebir kurulup ölçüldü: "gönderim defteri okunamadı", çıkış kodu 0. Bir
ölçüm aracının okuduğu dosya, o aracı koşturan iş akışının CHECKOUT
KAPSAMINDA yoksa ölçü sessizce kapanır; kapsam artık kaynaktan türetilip
sınanıyor (`gecikme.py`nin `kok / "..."` okumaları ⊆ `gecikme.yml` listesi) ve
`tweet` listeden çıkarılarak düşürüldüğü doğrulandı. İkincisi KAPININ KENDİ
YANLIŞ ALARMIYDI: `analiz/sablon.mdx`in `ozet` yer tutucusu "X gönderisinin
yedeğidir" diyordu ve o alan kartta okura basılıyor — şablondan kopyalanan
ilk yazı 21. ölçüte takılıp YAYINI DURDURACAKTI. Kaldırmanın kendisi bir yayın
arızasına dönüşürdü. Aynı sebeple 20 ve 21 artık `dist/` yokken SESSİZCE
atlanmıyor: `npm run sinav` derlemiyor ve koşmamış bir ölçüt "GEÇTİ" hükmünün
içinde görünmez kalıyordu.

Kalıbın HASSASİYETİ de ölçülerek genişletildi (hesap anışı, "Twitter'da",
"X'ten paylaşıldı"). Sol harf sınırı ve LOKATİF şart zorunlu: sitede "VIX'te",
"TÜFEX'te", "FX'te", "MDX'te" geçiyor ve bir istatistik yazısında "Y'den X'e
çıkarım" var — sonuncusu yönelme hâli dışarıda bırakılmasaydı yayını
durdururdu ve bugün yalnız MDX'in kıvrık kesme işareti sayesinde
kurtuluyordu, yani TESADÜFEN. Yirmi iki referans cümlesi duman sınavında.

**AÇIK KALAN — PUBLIC DEPONUN GEÇMİŞİ.** Kaldırma HEAD'i temizler, GEÇMİŞİ
değil: `cocoonish.github.io` public ve `src/lib/x.ts` ile
`src/data/tweet/defter.json` eski commit'lerde (ör. 5643dc70) hâlâ
indirilebiliyor. İçerik gerçek gönderi kimlikleri — zaten herkese açık
tweetler, hesap adı yok — ama iz orada. Silmek için public deponun geçmişini
YENİDEN YAZMAK gerekir; geri alınamaz bir işlem ve mevcut klonları bozar, o
yüzden kullanıcı açıkça istemeden yapılmadı.

**Kurucu ilke — bir METİN ALANININ dili sözleşmedir; bir alanı dışarıda
bırakmak yazarın bilemeyeceği bir ayrım yaratır.** Yazı katmanının bütün metin
alanları HTML taşıyor ve `yorum` ile `gundem.*` `set:html` ile basılıyordu;
`ozet` ise METİN olarak basılıyordu. Yazar farkı bilemez — aynı kapıdan
(`yaz.py`) aynı dille yazar — ve yazdı: dört bülten sayısında okur cümlenin
başında "<p>" YAZISINI gördü, yirmi kaçış. Hiçbir kapı bunu sormuyordu, çünkü
kaynak da veri de DOĞRUYDU; kusur yalnız iki tarafın farklı sözleşme
konuşmasındaydı ve bu ancak ÇIKTIDA görünür. Alan artık aynı yoldan basılıyor
ve sözleşme iki yönde de bozulmuyor: etiketle açılmayan bir değer `<p>` ile
sarılır, yani düz metin de kabul. Kapı sayfa sınavının 22. ölçütü — dist'te
kaçmış HER etiket (yalnız `<p>` değil) ENGEL, `<code>`/`<pre>` içi muaf:
HTML anlatan bir ders etiketi GÖSTERMEK zorundadır ve muafiyet olmasaydı
ölçüt bir gün yayını tam da o yazı yüzünden durdururdu. Dört regresyon
maddesi `site/tools/duman_sinav.py`de; ölçüt arızanın kendisine karşı
koşturularak sınandı (20 kaçış → 0).

**Kurucu ilke — BİR TETİK, VERİ İLERLEMEDİYSE TÜKETİLMEZ; ve bir önlem,
KAÇ YERDE karşılığı olduğu ölçülmeden konmuş sayılmaz.** Kullanıcı "kredi
datası güncellenmemiş gibi görünüyor" dedi ve haklıydı: site 17 gün eski
haftayı gösteriyordu (21.08), oysa aynı yayımdan beslenen YP mevduatı hattı
28.08'i çoktan bulmuştu. Kaynakta veri VARDI; kimse bir daha sormamıştı.
Zincir şöyle koptu: Haftalık Para ve Banka İstatistikleri perşembe 14:30'da
duyuruldu, tazeleme takvimi krediyi tetikledi, hat 03.09'da koştu, EVDS o anda
hâlâ 21.08 haftasını veriyordu, hat eli boş döndü — ve DAMGAYI ALDI. Karar
"son koşumdan sonra yayım oldu mu" diye sorduğu için tetik tüketilmiş sayıldı;
bir sonraki tetik 10.09 perşembeydi ve emniyet ağı (11 gün) haftalık döngüden
UZUN, yani hiç ateşlenmeyecekti. Kusurun görüntüsü sağlığın görüntüsüyle
aynıydı: koşu yeşil, damga taze, sayfa bayat. Üstelik ölçü VARDI — hattın
kendi `uyarilar.json`u "13 gün geride (tolerans 12)" yazmıştı ve onu okuyan
hiçbir kapı yoktu. `guncelle.py`nin damga satırındaki yorum bu tuzağı zaten
adıyla reddediyordu ("'koştu sayıldı ama veri gelmedi' durumu oluşmasın") ama
yalnız DÜŞEN koşu için: başarıyla biten ama eli boş dönen koşu muaftı. Bir
yorumun neyi kapsamadığı yazılmazsa, sonraki oturum onu her şeyi kapsıyor
sanır.
Defter artık koşunun NE GETİRDİĞİNİ de yazıyor (`son_surum`, `deneme`) ve
sürümü ilerletmeyen koşu tetiği tüketmiyor: hat bir sonraki pencerede yeniden
deneniyor, dört hakla ve iki saat arayla. Sayı ölçülmüş değil TAVAN, ve öyle
yazıldı — kaynağın veriyi hiç düşürmediği hâlde hattın her pencerede koşup
durmasını engelliyor; hak dolunca da SUSMUYOR, gerekçe adıyla yazılıyor, çünkü
"yeni yayım yok" satırı sağlıklı bir bekleyişle birebir aynı görünür.
Sürüm ölçüsünün TANIMI ayrı bir tuzaktı ve ilk yazımda tam ona düşülmüştü:
imza hattın bütün tarih alanlarından kurulunca, kredinin GÜNLÜK bacağı her iş
günü ilerlediği için imza her koşuda değişiyor, sayaç hiç artmıyor ve yeniden
deneme yazıldığı arıza için HİÇ ateşlenmiyordu. En eskisini almak da işlemiyor
(aylık bacak bir ay meşru olarak durur, sağlıklı haftalarda dört deneme
yakardı). Ölçü hattın ANA SAATİ — `RITIM`in zaten denetlediği saat. Ana saati
ilerlerken içindeki bir alanın donması bu ölçüye görünmez; o `RITIM_ALAN`ın
işi ve dışarıda kaldığı adıyla yazıldı.
İkinci yarısı önlemin KAPSAMIYLA ilgili. Yeniden deneme, önbellekten okuduğu
sürece hiçbir şeyi yeniden denemez: önbellekte duran şey tam da eli boş dönen
koşunun cevabıdır. Depoda bunun için bir düğme zaten vardı — `veri.yml`
zorlanmış koşuda `TTO_YENILE=1` export ediyor ve yanındaki yorum kusuru TÜİK
için birebir tarif ediyordu. Ölçüldü: TTL'li önbellek tutan DOKUZ dosyanın
yalnız BİRİ (Enflasyon) o değişkeni okuyordu. Yani "takvimi dinleme, koşulsuz
tazele" düğmesi sekiz hat için hiçbir şey yapmıyordu ve hiçbir koşu bunu
söylemiyordu. Kural `ortak/tazelik.py`ye tek tanım olarak taşındı, dokuz hattın
`_taze`si oraya devretti, ve kapsam bir listeden değil SÖZLEŞMEDEN türetildi:
dosyada TTL'li bir önbellek varsa tazelik kararı oradan geçmelidir. Üç ölçüt de
arızanın kendisine karşı koşturularak sınandı (yeniden deneme kaldırılınca,
imza ana saat yerine bütün alanlardan kurulunca, bir hat devretmeyince ayrı
ayrı DÜŞÜYOR; bugünkü ağaca karşı geçiyor).

**Kurucu ilke — BİR ÖLÇÜ, TÜKETİCİSİ YOKSA ÖLÇÜLMEMİŞTİR; ve bir hattın KİPİ,
ana saatini üreten adımı içermek zorundadır.** Kullanıcı "bütün projeler sürekli
en güncel hâlinde olmalı" dedi. Kredi arızası bir örnekti; soru zincirin
TAMAMINA soruldu ve altı kollu bir denetim koşuldu (36 ham bulgu → 10 doğrulama
turuna girdi → 4 ayakta kaldı, 6 ÇÜRÜTÜLDÜ). Çürütülenler kayda değer, çünkü
ikisi bu oturumun kendi hipotezleriydi: "haftalık hatların emniyet ağı (11 gün)
yayım döngüsünden (7 gün) uzun, yapısal olarak hiç ateşlenemez" iddiası yanlış
dosyadan ölçülmüştü, "FX günlük kipi bültenden sonra iniyor" iddiasının ham
sayıları doğru ama çıkarımı yanlıştı. İkna edici bir teşhis, sınanmamış bir
teşhistir.

Ayakta kalan dördü ve ortak dersleri:

(1) MARJ HATTININ HAFİF KİPİ DERLEME ZİNCİRİNİ HİÇ KOŞTURMUYORDU. Adım listesi
`web_cikti.py` + `ozet_uret.py` idi ve İKİSİ DE yalnız OKUR; hattın ana saati
`output/seriler.xlsx`ten türüyor ve o dosyayı yazan `rapor.py` yalnız TAM kipten
çağrılıyor — tam kip ise cron'la ateşlenemiyor. Xlsx 26.08'den beri yeniden
yazılmamıştı: 03.09'da Ağustos TÜFE'si yayımlandı, tetik ateşledi, hat KOŞTU,
tetiği tüketti ve ana saatini ilerletemedi. Sayfada aynı anda üç figür Ağustos,
on üçü Temmuz gösteriyordu. Ölü bağımlılık ilkesi bu depoda zaten yazılıydı
("bir dosya okunuyorsa onu üreten adım adım listesinde GÖRÜNMELİDİR") — kural
vardı, o hatta uygulanmamıştı. Hasat kapısı da ayrı bir adıma çıkarıldı
(`Research/marj/src/hasat.py`), çünkü `rapor.py`yi tek başına eklemek İKİNCİ bir
ölü bağımlılık kurardı.

(2) ÖLÇÜNÜN TÜKETİCİSİ SIFIRDI. Aynı gün konan yeniden deneme defteri arızayı
artık ölçüyordu, ama tek aday tüketici (`denetim.tazeleme_atlandi`)
`[k for k in kararlar if k.kossun]` süzgeciyle TAM DA ARIZA HÂLİNİ atıyordu:
hakkı dolan hat `kossun=False` döner. Ölçülen ama okunmayan bir sinyal,
ölçülmemiş sinyaldir. `bulten/bayatlik.py` ölçünün tek tanımı oldu ve iki
tüketicisi var: denetim satırı (süzgecin ÖNÜNDE) ve `gecikme.yml`in cron'suz
alarm adımı. Ölçü DAR ve bilerek: alarm yalnız "kaynak yayımladı + hat koştu +
ana saat ilerlemedi + hak doldu" bileşiminden doğar. Ham veri yaşı eşik OLAMAZ —
ölçüldü, o gün üç hatta ateşlerdi ve İKİSİ MEŞRUDU (ödemeler dengesi 11.09'da
yayımlanacaktı, hazinenin sıradaki ihalesi 14.09'daydı): ≥%67 yanlış pozitif.
Ve `gecikme.py`nin eşi bir YAPISAL KİLİT: `SINIFLAR`da yayını durduran sınıf
HİÇ TANIMLI DEĞİL.

(3) KAPSAM ÜÇ AYRI YERDE SÖZLEŞMEDEN KOPMUŞTU. `ayar.RITIM` 21 hattın 18'ini
taşıyordu; eksik üçü (yp-mevduat, buyume, el-nino) RITIM'i dolaşan SEKİZ çağrı
yerinin hepsinden birden düşüyordu — panoları üretiliyor, bayatlıklarını soran
kimse yok; en görünür sonucu üç aylık GSYH yayımının bültende HİÇ
duyurulamamasıydı. `ayar.RITIM_ALAN` kütüğün İLAN ETTİĞİ 21 ikincil saatin
1'ini denetliyordu. Ve `denetim._tarihe`nin KENDİ ayrıştırıcısı `AA.YYYY`
yazımını tanımıyordu, yani beş hattın karanlık denetimi SESSİZCE KAPALIYDI
(aynı kusur `Deger.astro`da bir kez daha ölçülmüştü — ayrıştıramayan bir
denetim hep "sorun yok" der). Üçü de sözleşmeden türetildi ve `duman.py` her
ilanın karşılığını ENGEL olarak sınıyor. EŞİKLER kopyalanmadı: RITIM "bu sürüme
geçileli kaç gün", `Tetik.en_gec` "son KOŞUMDAN kaç gün" ölçer ve depo ikisini
bilerek ayırmış (fx 5↔9, reelfx 75↔30); mekanik kopya reelfx'te her ay yanlış
alarm üretirdi. Genişlemenin yanlış alarm maliyeti ölçüldü: SIFIR.

(4) BİR TAVAN KENDİNİ KİLİTLEYEBİLİR. Hazine adımının 8 dakikalık sınırı hattın
bulutta ölçülmüş süresinin (10–20 dk soğuk tarama) ALTINDAYDI: her tam kip
kesiliyor, kesilen koşu `finally` koşmadığı için süre defterine hiçbir şey
yazmıyor, defter boş olduğu için tavan hiç ölçüye bağlanamıyordu. Üç düzeltme
birlikte gider: tavan üç parçadan kurulup parçalar YAZILDI (ön adım 2 + kazıma
19 + geri alma 1 = 22, iş sınırı 80), ön adımın kendi sınırı kondu (sınırsızdı
ve kabuk `timeout`unun DIŞINDAydı), ve `guncelle.py`ye SIGTERM tutucusu eklendi
— artık kesilen koşu da `finally` zincirini koşturuyor, yani tamamlanan
hatların süresi ve damgası korunuyor. Kapının kendi kör noktası da kapandı:
bütçe ölçütü yalnız `timeout-minutes`e bakıyordu ve adımın İÇİNDEKİ sınırsız
komutu göremiyordu; yeni ölçüt kabuk içi `timeout` TAŞIYAN adımlarda korumasız
python çağrısı arıyor (kapsam dar ve adıyla yazılı, bugünkü ağaçta yanlış
pozitif sıfır).

Küçük ama aynı sınıftan üç kalan: `_ihale_gunleri` "adında tarih geçen her
sütun" diyordu ve 20 günün 12'si ihale günü değildi (itfa tarihleri 2028'den
itibaren GERÇEK tetiğe dönecekti) — sütun artık ADIYLA sorulyor, bulunamazsa
dosyanın gerçek sütun adları yazılıyor. `olu_kaliplar()` 27.08'den beri ölçü
üretiyordu ve beş çağrı yerinin hiçbiri kapı değildi; üstelik belgesi kodun
TERSİNİ anlatıyordu ("hat emniyet ağına düşer" — oysa kod `kossun=True` veriyor,
hat HER pencerede koşuyor, ölçülü maliyeti ~87 dk/gün). Ve kör koşunun izi
nabız defterine kondu (EŞİK YOK, bilerek: ölçülmeyen bir seviyeye eşik konmaz).

On üç arıza enjeksiyonunun on üçü de yakalandı; dördü ilk turda geçti ve sebep
ölçütün körlüğü değil MUTASYONUN arızayı üretmemesiydi — bir regresyon
sınamasının kendisi de yanlış olabilir, ve "ölçüt düşmedi" ile "arıza yok"
birbirine tıpatıp benzer.

**Kurucu ilke — YAZI KATMANI, ÖLÇÜLEN KATMANIN BİLMEDİĞİ BİR OLAYI ANLATAMAZ;
ve YILLIKLANDIRILMIŞ BİR HIZ TEK GÜNLE OKUNMAZ.** İki bulgu aynı sayıdan çıktı
ve ikisi de "sayı doğru, bağlam eksik" sınıfından.

Birincisi ağır. 08.09.2026 bülteni okura iki kez OLMAMIŞ bir olay anlattı:
"Bugün Hazine iki yıl vadeli kira sertifikasını doğrudan satışla ihraç ediyor"
ve "Dün yapılan sekiz ay vadeli hazine bonosu ihalesinin sonuçları henüz hatta
düşmedi — modelin beklentisi 130,4 milyar TL". İkisi de AĞUSTOS–EKİM
stratejisinde vardı ve Hazine 31.08'de yayımladığı EYLÜL–KASIM stratejisinde
ikisini de takvimden çıkardı. HAT DOĞRU DAVRANDI: planı 31.08'de yeniledi,
canlı dosyasında o iki ihale YOK, `kritik_takvim` yalnız 14–15 Eylül'ü
gösteriyor. Yazı katmanı ise iki hafta boyunca eski stratejiden yazmayı
sürdürdü — ölçüldü, aynı iddia 31.08'den 08.09'a SEKİZ sayıda geçti ve söz
defterinde bir de TAAHHÜT olarak durdu ("Model 7 Eylül bono ihalesi için
130,4 mlr TL gerçekleşme"). Ölçülen katman ile yazı katmanı çeliştiğinde hakem
ölçülen katmandır ve bunu soran hiçbir kapı yoktu.
Kaynak seçimi hükmün kendisi kadar önemli: canlı plan dosyası yalnız bugünden
İLERİYİ tutar, oysa iddia dünle de ilgili olabilir. Hakem YÜRÜRLÜKTEKİ
STRATEJİDİR — üç ayı kapsar, arşivde sürümleriyle durur ve pencerenin İÇİNDE
bir gün için kaydı yoksa o gün ihale YOKTUR. Pencerenin dışında depo bir şey
bilmez ve ölçüt SUSAR. Pencere, günleri veren belgenin KENDİSİNDEN türetilir:
ilk yazımda arşiv dosyasının adındaki tarihten (+1 ay) kurulmuştu ve yanlış
çıktı — o tarih belgenin yayım günü değil hattın onu TARADIĞI gündür, aynı
strateji üç kez arşivlenmişti ve asıl sorulacak gün pencerenin dışında
kalıyordu.
Hassasiyet ölçülerek kuruldu: ilk kalıp "aynı cümledeki her tarih" diyordu ve
13 sayıda 49 bulgu verdi, çoğu aynı cümlede geçen alakasız bir yayımdı
("4 Eylül'de ABD tarım dışı istihdamı, 7 Eylül'de … bono ihalesi" → 4 Eylül
yanlış yakalanıyordu). İki daraltma: çıpa ile iddia arasında en çok ~70
karakter olabilir ve ARADA BAŞKA TARİH BULUNAMAZ. Tarihçeye karşı koşuldu ve
sınır tam yerinde çıktı: 30.08 ve öncesi TEMİZ (o gün yürürlükte olan
stratejide ihale gerçekten vardı, yazı DOĞRUYDU), kusur 31.08'de başlıyor.
Bir ölçüt geçmişi geriye dönük suçlamamalı.
Kapı kurulurken kendi kör noktası da ölçüldü: sınama `ihale_takvimi`yi
DOĞRUDAN çağırıyordu, yani ölçütün `denetim.kos()` listesinde olup olmadığını
sormuyordu — ölçüt yazılıp listeye konmasa hiç koşmazdı. Bu, aynı gün üç kez
karşılaşılan "ölçü var, tüketici yok" kusurunun bir eşi.

Yan bulgu, ölçütün KENDİ süzgecinde: düzeltilmiş metin USD/SEK hareketini
açıkça anlattığı hâlde haber tonu ölçütü "ANILMAMIŞ" deyip ENGEL üretti.
Sebep `_sade`de: NFKD'nin ayırdığı birleştirici işaretler BOŞLUĞA çevriliyordu
ve Türkçe büyük İ bunu asimetrik yapıyordu — `"İsveç".lower()` "i" + nokta
üretir, yani metin "i svec  kronu", anahtar "isvec  kron" oluyor ve ikisi ASLA
eşleşmiyordu. Aynı kusur sınıfı bu dosyada bir kez daha kayıtlı ve orada
anahtarlar metinle aynı süzgeçten geçirilerek onarılmıştı; bu kez süzgecin
KENDİSİ onarıldı (işaret boşluğa çevrilmez, SİLİNİR). Etkisi ölçüldü: 13 sayı
üzerinde ENGEL 6'dan 5'e indi — kaldırılan tek bulgu yanlış alarmın kendisi.
Kapanamayan bir uyarı, yazarı bütün uyarıları görmezden gelmeye alıştırır.

İkincisi ölçünün okunuşuyla ilgili ve kullanıcı adıyla koydu: "valör farkı vs.
olduğunda hız çok artmış veya azalmış görünebiliyor". Yıllıklandırma bir GÜNLÜK
fiyat farkını 365'e ölçekler; valör farkı, tatil ya da TCMB'nin ertesi gün
kurunu bir gün önce ilan etmesi oranı tek günde sıçratır. 08.09 bülteninde bir
aylık hız tek günde 4,5 puan "arttı" (%19,6 → %24,1). Ölçüldü: düzgün bir %20
patikada son güne konan %0,5'lik sahte bir kotasyon sıçraması tek günlük oranı
7,8 puan, AYNI ÖLÇÜNÜN beş günlük ortalamasını yalnız 1,6 puan oynatıyor —
4,9× söndürme. Ortalama artık cümlenin İÇİNDE, dipnotta değil: sıçramayı okuyan
biri ortalamayı aynı satırda görmeli.
Bağlam AYNI ÖLÇÜNÜN penceresi olmak zorunda. Hattın zaten yazdığı
`hafta_son_ort` buraya GİRMEDİ: o 1 HAFTALIK oranın haftalık ortalamasıdır ve
bir AYLIK hızın yanına yazmak iki farklı pencereyi aynı cümlede kıyaslamak
olurdu. Hat bu yüzden aynı `deval()` tanımını kaydırarak yeni bir ortalama
üretiyor (`d1a_ort`, `d3a_ort`); iki ayrı formül bir gün sessizce ayrışır.
Kapsam elle tutulmuyor: `ayar.Izlem.baglam` taşıyan her anahtar hem olay
cümlesine hem gösterge şeridine kendiliğinden giriyor.

**Kurucu ilke — TEKRARIN İKİ EKSENİ VARDIR ve biri hiç ölçülmüyordu.**
Kullanıcı "tekrarlı olmasın, her gün aynı şeyleri söylemeyelim" dedi. Depoda
bir tekrar ölçeri zaten vardı (`bulten/tekrar.py`) ama yalnız bir SAYININ
KENDİ içine bakıyordu; "günler arası" ekseni hiç sorulmamıştı. Ölçüldü
(07.09.2026, 13 sayı): ardışık iki sayı arasında birebir 7-sözcük öbeği
örtüşmesi 26.08'den 06.09'a DÜZENLİ tırmanmış — %0,5 → %19,1 → %25,8 → %33,2
→ %37,5 → %46,2.
Kaynağı ayrıştırmak hükmü tersine çevirdi ve bu kayda değer: kusur YAZARDA
DEĞİLDİ. Her sabah yazılan düzyazı gerçekten yeni — gündem %0,6 · yorum %0,3
· özet %2,7. Tekrarın TAMAMI tek bir yerden geliyordu: söz defteri %91,4
örtüşüyordu, çünkü 4.816 sözcüklük bölüm her sabah kelimesi kelimesine
yeniden basılıyordu. Bir şikâyet "yazı tekrarlı" diye geldiğinde önce yazı
ÖLÇÜLÜR; yazı temizse soru bitmez, YER DEĞİŞTİRİR — sayfanın kendi basım
biçimine geçer.
Düzeltme defteri SİLMİYOR, basım biçimini değiştiriyor: ölçüm katmanı her
kaydı `degisti`/`duran` diye işaretler (üç ölçüt veriden türer — bugün açıldı,
bugün kapandı, vadesi geldi; dördüncüsü önceki sayının metniyle kıyastır),
sayfa değişeni TAM metniyle, duranı tek satırlık künyesiyle basar. Ölçüldü:
defter 4.816 → 1.801 sözcük, sayfa düzyazısının günler arası örtüşmesi
%47,3 → %21,1, haftalık sayı 18.456 → 15.644 sözcük.
Üç tuzak kayda geçsin. (1) İlk kural KAPANMIŞ kayıt için de "vade yakın"
soruyordu; kapanan 17 kaydın 16'sı "değişen" çıkıyor ve tekrar yerinde
kalıyordu — kapanmış bir kayıt için vade ANLAMSIZDIR. (2) Ölçünün kapsamı
elle tutulan bir listeydi (gündem + yorum = düzyazının %27'si); sözleşmeden
türetilince — okura düzyazı olarak basılan her alan — asıl biriktiği yerler
göründü. (3) Kapsam genişleyince İÇ tekrar ölçüsü yapısal olarak şişti ve 13
sayının 3'ünü ENGELLEYECEKTİ; sebep gerçek kusur değil, söz defterinin ve
özetin gövdeye DEĞMESİNİN tanımı gereği meşru olmasıydı — `kilit`/`yorum`
zaten aynı gerekçeyle muaftı. Muafiyet İÇ ölçüye özgü: GÜNLER ARASI ölçüde
söz defteri tam tersine asıl bakılacak yerdir.
Eşikler iki ÖLÇÜLEN hâlden türetildi, sezgiden değil (toplam: bozuk %47,3 ·
düzeltilmiş %21,1 → eşik 30; bölüm: bozuk %91,5–100 · düzeltilmiş %71,4 →
eşik 80) ve ölçü ENGEL DEĞİL UYARI: sakin bir haftada iki sayının benzemesi
meşrudur, vadesi gelen bir söz yeniden anılmalıdır. Yayının önünde duran bir
denetimin yanlış alarmı, ölçtüğü kusurdan pahalıdır.
Yan bulgu, eski kapının göremediği: 24–25.08'de `ozet` önceki sayıdan
%97–100 aynen kopyalanmış. Bakılmayan yer, geçen sınavla aynı görünür.

**Kurucu ilke — bir KURAL yalnız YORUMA yazıldığında dayatılmaz; ve bir
FARKIN birimi, SEVİYENİN birimi değildir.** İki kusur aynı turda çıktı ve
ikisi de "kural var, kapı yok" sınıfından.
Birincisi renk: `global.css` jetonun yanına kendi kuralını yazmıştı —
"`--ink-30` yalnız çizgi ve kenarlıkta; metinde kullanılmaz". Kural doğruydu
ve hiçbir yerde SORULMUYORDU: ölçüldü, sekiz dosyada on beş yerde metin rengi
olarak kullanılıyordu. Kontrast 1,90:1; WCAG AA gövde 4,5 · büyük 3,0 · metin
dışı öğe 3,0 — üçünü de geçmiyor. Üstelik en yoğun sayı sütunları (σ, 52
hafta aralığı, tema sütunu) tam bu renkteydi, yani sayfanın en çok bakılan
yeri en zor okunan yerdi. Hepsi `--ink-60`a (4,59:1) çekildi — jetonun kendi
yorumunun "metinde kullanılabilir en soluk mürekkep" dediği değer. Kapı sayfa
sınavının 23. ölçütü; `text-decoration-color` kapsam dışı, çünkü o alt çizgi
rengidir, metin değil.
İkincisi ölçü: olay cümlesi "Tüketici kredisi büyümesi 12,8 % azaldı: 43,0 →
30,2 %." diye çıkıyordu. İki kusur birden. (a) Birim sayının ARKASINDAYDI;
sözleşme yüzdeyi öne alır (derlenmiş sayfada 40 yer). (b) Daha ağırı:
%43,0'dan %30,2'ye inen bir oranın farkı 12,8 PUANDIR, %12,8 değil — %12,8'lik
bir düşüş 43,0'ı 37,5'e indirirdi. Cümle yalnız çirkin değil YANLIŞTI ve
`ayar.IZLEMLER`in 56 kaydından 30'u bu daldan geçiyordu. Seviye ile farkın
yazımı artık iki ayrı fonksiyonda (`olay._sev` · `olay._fark_yaz`) ve fark
birimi tablodan türüyor (`FARK_BIRIMI = {"%": "puan"}`).
Kapının kendi kalıbı da ölçülerek daraltıldı: ilk yazımda `\d\s+%` kullanıldı
ve `\s` satır sonunu da eşlediği için alanlar "\n" ile birleştirilince 20
bulgunun 20'si YANLIŞ POZİTİF çıktı (bir alanın sonundaki tarih + öbürünün
başındaki yüzde). Kusurun gerçek biçimi aynı satırda ve boşlukla: `\d[ \t]+%`.

**Kurucu ilke — `ch` bir KARAKTER genişliği değildir.** Satır uzunluğu
`--olcu: 70ch` ve `.bulten { max-width: 74ch }` ile yazılıyordu ve ikisi de
doğru görünüyordu (ideal bant 60–80). Ölçüldü: `ch` birimi '0' RAKAMININ
genişliğidir ve Newsreader'da 0,5665em; bültenin kendi metninde ortalama
karakter 0,4199em (57.651 karakter üzerinden). Oran 1,349 — yani 74ch bu
fontta 74 değil ~100 KARAKTER. Sınırı yazan da okuyan da bandın içinde
sanıyordu. En kötüsü haber özetleriydi: 13,1 px ve genişlik sınırı YOK →
satır başına 129 karakter, 44 özet. Düzyazı ölçüsü artık `rem` cinsinden tek
bir jetonda (`--olcu-metin: 32rem` ≈ 72 karakter) ve sınır SÜTUNA değil METNE
konuyor — sütun 74ch'te kalmak zorunda, çünkü tablolar ve gösterge ızgarası o
genişliği kullanıyor. Metnin %55,8'i 14 px altındaydı; en ağır iki blok
(haber özeti, söz defteri) gövdenin bir kademe altına çıkarıldı.

**Kurucu ilke — TEKİLLEŞTİRME KALIBI BİR KEZ YAZILIR, HER YERE UYGULANIR.**
"Kritik takvim" ile "Takvim" bir zamanlar aynı olayı iki kez basıyordu ve
çözüm bu dosyada zaten yazılıydı: anahtar kümesi kur, tam listeden çıkar.
Aynı kusur olaylarda duruyordu ve kimse bakmamıştı — ölçüldü (13 sayı):
"Öne çıkanlar" ve "Notlar" bölümlerindeki 115 maddenin 115'i de "Hat hat
değişim"de BİREBİR tekrar ediyordu. Aynı kalıp hat+anahtar çiftiyle
uygulandı; ölçüldü, 8/8 → 0. Bir kusur çözüldüğünde sorulacak soru "bu bölümü
düzelttim mi" değil, "bu kalıbın uygulanmadığı başka yer var mı"dır.

**Kurucu ilke — BİR SAYAÇ NEYİ SAYDIĞINI BİLMELİDİR; ve bir alarmın yanlış
pozitifi tek bir e-posta değil, bir ZİNCİRDİR.** 08.09.2026 akşamı kullanıcıya
on dört "Gecikme alarmı", üç "Siteyi yayınla" ve üç "Veri tazeleme" arıza
e-postası gitti. İki bağımsız kök vardı.
Birincisi kendi elimizden çıktı. Aynı gün konan "kaynak yayımladı, veri
gelmedi" sayacı HER başarılı koşuda artıyordu; oysa sayaç yalnız kaynağın
yayımladığı BİLİNEN bir koşuda anlam taşır. Türev hatlar (makro · carry ·
tufex) tazeleme takviminde tarifsizdir — üst hat koşunca koşar, saatleri üst
hattan gelir — ve günde altı pencerede koşup haftalık saatlerini
ilerletemedikleri için aynı gün "hak doldu"ya vardılar. Zincir şöyle yürüdü:
sahte alarm cron'suz alarm kanalını her uyanmada (on dört koşu) kırmızı
bitirdi ve kayıt olmadığı için her seferinde e-posta gitti; bülten denetimi
aynı alarmı UYARI olarak bastı; duman sınaması CANLI defteri okuduğu için o
uyarıyla düştü; duman düştüğü için veri tazeleme üç pencere boyunca HİÇ koşmadı.
Bir ölçünün yanlış pozitifi, o ölçüyü okuyan her kapıya yayılır. Dört düzeltme
birlikte gider ve dördü de arızanın kendisine karşı koşturularak sınandı:
(1) sayaç yalnız yayım tetikli koşuda ve onun yeniden denemesinde artar
(`Karar.sayilir` → `durum_yaz(sayilan=…)`); emniyet ağı, elle koşu, ölü kalıp,
kör koşu ve tarifsiz hat sayılmaz, tarifsiz hat defterden SİLİNİR.
(2) Sürüm imzası ana saat ARTI tarifin ek kaynaklarının ilan ettiği yan saat
(`izlenen_saatler`): butce'de haftalık TCMB yayımı `_tarih2`yi ilerletir, ana
saat aylık kalır — yan saat imzada olmasaydı haftalık tetik her hafta "veri
gelmedi" sayardı; her ek kaynak ilerlettiği saati ADIYLA ilan eder.
(3) Alarm kanalı MÜKERRERLİK KAYDI taşır (`bayatlik_alarm_kaydi.json`,
anahtar hat|sürüm): aynı hat aynı sürümde takılıyken bir kez bildirilir. Kanal
günde 40–70 kez uyanıyor; kayıtsız alarm iki günde okunmaz olur.
(4) Duman sınaması deponun o günkü defterini DEĞİL kendi kurduğu çerçeveyi
okur. Ve kapının kendi tuzağı adıyla yazıldı: canlı defterde eski koddan kalmış
bir tarifsiz sayaç ENGEL yapılmadı — yapılsaydı veri iş akışı duman kapısında
kilitlenir ve temizliği yapacak koşu hiç başlamazdı.
İkinci kök hattaydı ve "ölçülemeyen boş bırakılır" ilkesinin eksik yarısı:
DİBS dokuz yıl düğümünü kuramadığı gün `kiyas_*_9y_degisim_bp` çıpa gününün
değerini istedi, NaN çıktı ve `koy()` anahtarı ATLADI. Sayfa anahtarı adıyla
çağırıyor; yayın kapısı eksik anahtarı ENGEL saydı (doğru: yedekteki donmuş
sayı yayımlanmamalı) ve yayın üç kez düştü — günün bülteni saatlerce çıkmadı.
Kural: sayfanın adıyla çağırdığı anahtar HER koşuda yazılır — ölçülebiliyorsa
toleransın içindeki son dolu günden ve KENDİ tarihiyle (`_degisim_bp_tarih`),
ölçülemiyorsa boş ("—"); atlanmaz. Kusur hattın koşusunda doğdu ve o koşu
yeşil bitti; `guncelle.py` artık kopyaladığı anda sayfanın çağırdığı eksik
anahtarı adıyla uyarır, hattın kendi `duman.py`si döngüyü sınar.

Yedi sayının düzeltmesi yazılırken aynı sınıftan üç kusur daha çıktı ve üçü de
"arşiv sayısı bugünün ölçüsüyle ölçülüyordu" başlığında toplanıyor. (1) Yazma
kapısı (`yaz.py`) denetimi koşturur; tema görüntüsü ve haber tonu ölçütleri
bugünün DEFTERİNİ okuyup eski sayıyla kıyaslıyordu ve yedi düzeltmenin yedisini
sahte ENGEL ile reddetti — `tazeleme_atlandi`nin baştan beri taşıdığı "yalnız
bugünün sayısı" kapısı ikisine de kondu (`_arsiv_sayisi`). (2) Yayımlanmış bir
düzeltme kaydı, düzelttiği iddianın çelişkisini KAPATIR (`ihale_takvimi`,
etiket `alan`da geçiyorsa): eski metni silmek tarihçeyi yeniden yazmak olurdu,
okur eski sayıya göre karar vermiş olabilir. (3) `yaz.py` yayımlanmış sayıya
yazılan düzeltmede `ilk_yazi_zamani`ni O ANIN damgasıyla dolduruyordu; gecikme
ölçüsü üç günü 12.390 dakika geç gösterdi. 04.09'da fikstür bu tuzağı adıyla
yazmış ve kendi girdisini dondurmuştu — kaynağı düzeltmemişti; fikstür geçti,
tarihçe bozuldu. Damga artık yalnız İLK yazımda atılır (ölçü takvim günü değil
"yazılmış mı": geç kalan sayı ertesi gün ilk kez yazılıyorsa gerçek gecikmeyi
taşımalı). Bir fikstürün kendini bir tuzaktan koruması, tuzağı kapatmaz.

**KARAR (08.09.2026, kullanıcı) — YALNIZ PANOLAR CANLIDIR; analiz ve ders
yazıları yayımlandığı günün metnidir.** "Analiz olarak yayımladıklarımızın canlı
olmasına gerek yok, sadece projeler canlı olacak. Analizlerdeki canlı işaretini
de silelim." Analizlerde 1.293, bir derste 10 `<Deger>` çağrısı vardı ve hepsi
sayfa açılınca hattın bugünkü dosyasından tazeleniyordu — tarihli bir yazının
altındaki sayı kayıyor, "3 Eylül" başlıklı bir analiz eylül ortasının verisini
anlatıyordu. MDX'e dokunulmadı (yayımlanmış yazı değiştirilmez): düzen
(`Yazi.astro`) pano dışı gövdeyi `data-deger="sabit"` kabına alır, `Deger`
betiği kabın içine dokunmaz, stil alt çizgiyi ve yardım imlecini kaldırır;
yedek metin — yazının yazıldığı günkü sayı — olduğu gibi kalır. Künyedeki
"Ritim" satırı da yalnız panoda. Kapı sayfa sınavının 24. ölçütü: derlenmiş
çıktıda kapsız canlı alan taşıyan analiz/ders ENGEL, kaplı pano ENGEL (kabı
bileşen kurar, düzen değişikliği onu sessizce düşürebilir). Ölçüt 7 bilgi
satırına indi: analizdeki eksik anahtar okuru etkilemez — 08.09'da tam bu
sınıftan bir eksik (DİBS kıyas anahtarı, bir analiz yazısında) yayını üç kez
durdurmuştu. Tweet üretici de sayfayla aynı sözleşmeye çekildi: gönderi
sayfanın gösterdiği sabit sayıyı taşır, canlı çözmez. Kapsam dışı ve ADIYLA
yazılı: analizlere gömülü figürler (`GrafikEmbed`) hattın dosyasıdır ve hat
koştukça yenilenmeye DEVAM EDER — metin sabit, figür canlı; bir analiz figürün
o günkü değerini anlatıyorsa tarihiyle anlatmalı. Figürleri de dondurmak
(yayım günü kopyası) istenirse ayrı karar.

**Kurucu ilke — bir SAYACIN TABANI koşudan ÖNCE ölçülür; "koşulsuz tazele"
koşu başına söylenir, adım başına değil; ve KALIPTAKİ HER YAYIM hattın bir
saatini ilerletmelidir.** 09.09.2026'da bütün hatların güncellik denetimi
(21 hat, hat hat inceleme, ulusal takvim keşfi, defter ölçümü) üç mekanizma
kusuru çıkardı ve üçü de "sağlıklı görünen arıza" sınıfından.

(1) SOĞUK BAŞLANGIÇ. Sürüm defterinde 18 tarifli hattın 11'inin tabanı yoktu.
Tabansız hat ilk sayılan koşusunda eli boş dönerse koşu SONRASI sürüm tabana
yazılıp "ilerledi" sayılıyor, sayaç 0 kalıyor ve yeniden deneme hiç
açılmıyordu — 03.09 kredi arızasının sigortasız tekrarı, 10.09 Perşembe için
kredi · ypmevduat · yabanci hatlarında hazır bekliyordu. Kıyas noktası koşu
ÖNCESİ sürümdür (`guncelle.py` ölçer, `durum_yaz(onceki=…)`); defter
`tazeleme.py --tohumla` ile bir kerede dolduruldu ve duman tabansız tarifli
hattı ENGEL sayıyor. Bir sayaç, ilk ölçümünü hangi noktadan aldığını
bilmiyorsa ilk arızayı sağlık sanır.

(2) YİRMİ KEZ İNDİRME. `TTO_YENILE=1` her ADIMDA önbelleği atlatıyordu; marj
hattı beş adımdır ve `rapor.py` aynı 39 seriyi bir koşuda yirmi kez ister
(her hesap fonksiyonu tabloyu baştan kurar). Zorlanmış koşuda 757 EVDS
indirmesi, 15 dakikalık adım tavanı doldu, hat düştü, kullanıcıya arıza
e-postası gitti (bulut #138). Yerel sınama bunu GÖRMEDİ: devre kesici açık
olduğundan yirmi geçişin her biri anında önbelleğe düşüyor ve zincir "temiz"
bitiyordu — ağa çıkamayan bir sınama, ağ maliyetini ölçemez. Kural
`ortak/tazelik`te: koşunun başlangıç anından (`TTO_KOSU_BASLANGIC`, hat
başında yazılır) SONRA yazılmış önbellek bu koşunun indirmesidir ve tazedir;
marj ayrıca süreç içi bellek tutar. Aynı koşu düzeltmeyle 1.290 s → 70 s.
Tavanı büyütmek (kullanıcının sorduğu "15 dk az mı?") çare değildi: sorun
adımın uzunluğu değil, aynı işin yirmi kez yapılmasıydı.

(3) TÜKETİLMEYEN YAYIM KALIPTA. Sürüm sayacı yayım tetikli koşuda artar; hattın
OKUMADIĞI bir yayım kalıptaysa tetikli koşu eli boş döner, üç yeniden deneme
önbelleği atlayarak koşar ve ertesi gün "kaynak yayımladı, veri gelmedi"
alarmı doğar — `kararlar()` ile ölçüldü (28.09 15:23 → 18:37 · 05:13 · 11:47
→ 29.09 alarm). Enflasyon ve marj'da Hizmet ÜFE, bütçede Finansman ve İç
Borç, ödemeler dengesinde KVDB ve UYP böyleydi: her ay bir sahte alarm ve üç
boş tam çekim. Kural: ana kalıp yalnız ANA saati ilerleten yayımı tutar;
başka bir saati ilerleten yayım EK KAYNAK olarak, ilerlettiği saat ADIYLA
girer (bütçede Denge Tablosu → `akim_tarih`), hiçbir saati ilerletmeyen
yayım tarifte durmaz. Takvim hangi yayımın hangi seriyi ilerlettiğini
söylemez; hat söyler, duman sorar.

Eşikler de KOŞU RİTMİNE göre yeniden ölçüldü, veri ritmine göre değil:
günlük bir bacak haftalık koşuda yenileniyorsa (kredi `gun_tarih`) eşik
haftalıktır, haftalık bir bacak aylık koşuda yenileniyorsa (reelfx rezerv)
aylıktır; çeyreklik GSYH bacağı aylık ana saatin 123 gün gerisine meşru
düşebilir (bütçe karanlık 75 → 140). Aksi her hafta okura basılan sahte
"gecikti" satırıdır — hazine RITIM 12, ihaleler arası üç haftada altı sayıda
bastı; TCMB altın çapası eşiği 8 gün, Cuma tarihli + altı gün yayımlanan bir
çapa için her hafta Paz–Çar öttü.

**KARAR (09.09.2026, kullanıcı) — USD/TRY her hatta Yahoo Finance'ten gelir;
TCMB gösterge kuru yalnız DÖNÜŞÜM kurudur.** "usdtry evdsden çekiliyor gibi,
bu her yerden yahoo finance olmalı." Kurun KONU olduğu her hat — devalüasyon
panosu, taşıma (fonlama → carry), OVP'nin gerçekleşen kuru, REDK'nin USD/TRY
bacağı, hazinenin dolar bazlı ihraç grafiği; bülten ve teknik zaten öyleydi —
tek yükleyiciden okur: `ortak/usdtry.py`. Tek tanım, çünkü aynı seriyi ayrı
ayrı çeken iki hattan biri kırpık seriyi bir gün fark etmez; bu dosyada
ölçülmüş hâli yazılı (yfinance altı aylık, seviyesi yıllar geride bir seri
döndürmüştü ve koşu yeşil bitmişti). Yükleyici üç şeyi SÖZLEŞME olarak sınar:
KAPSAM (istenen başlangıçtan 45 günden geç başlayan, bugünden 5 günden eski
biten ya da hafta içi günlerin %90'ından azını taşıyan seri), SEVİYE (eldeki
önbellekle ortak son günde %20'den fazla ayrışan seri) ve KAPANMAMIŞ BAR
(günün UTC barı düşürülür — bir ölçüm ancak kapanmış seansı ölçebilir).
Geçmeyen seri eldeki önbelleğe düşer ve sebebi künyeye yazılır (`kur_uyari`,
hattın uyarı listesi); önbellek de yoksa hata — kırpık seri ASLA grafiğe
girmez, koşu yeşil bitip yanlış kurla bölmez. Damga artık İŞLEM GÜNÜDÜR:
EVDS'in ertesi günün kurunu bir gün önce ilan etmesi (valör) ve tatil öncesi
ileri tarih sorunu yapısal olarak yok; bültenin `usdtry` saati bu yüzden bir
gün geri adım attı ve bu bir gerileme değil, doğru etikettir.
Kapsam dışı ve ADIYLA yazılı: resmî bir istatistiğin TL karşılığını kuran
DÖNÜŞÜM kuru — TCMB net rezervde swap ve altın stoku, kredide kur etkisi
arındırması, bütçede borç stoku, ödemeler dengesinde stok bacağı — TCMB
gösterge kurunda kaldı: o tablolar TCMB'nin kendi kuruyla yayımlanır ve
Yahoo kapanışıyla çevrilirse resmî rakamla ayrışır. İki küme
`bulten/duman.py`de KAYNAK METNİNDEN sınanıyor (`_usdtry_tek_kaynak`): konu
hatlarında EVDS kur kodu kalırsa DÜŞER, dönüşüm hatlarından biri Yahoo'ya
geçerse de düşer — kural yoruma değil kapıya yazıldı. Dönüşüm hatlarının da
Yahoo'ya çekilmesi istenirse ayrı karar; bu paragraf o gün güncellenir.

**Kurucu ilke — SAYFANIN ÇAĞIRDIĞI ANAHTAR, ÖZETİYLE BİRLİKTE YAYINA GİRER;
bir KAPI kopyadan ÖNCE sorulmalıdır; ve BİÇİMLENMİŞ BİR DİZGE YENİDEN
AYRIŞTIRILMAZ.** 09.09.2026'da altı hattın saat düzeltmesi tek dalda toplandı
ve yayın kapısı MERGE'DEN ÖNCE koşturuldu. Üç kusur çıktı; üçü de kapı
olmasa main'e sessizce girecekti.

(1) Kod yeni anahtar üretiyor, YAYIMLANMIŞ ÖZET onu taşımıyor. Üç sayfa
(dibs · butce · tufex) `ozet.json`da olmayan 18 anahtarı adıyla çağırıyordu:
MDX ile kod aynı commit'te, ama okurun gördüğü dosya hattın BİR SONRAKİ
koşusundan geliyor. Yayın kapısı eksik anahtarı ENGEL sayar (doğru: donmuş
yedek yayımlanmamalı) ve site donardı — 08.09'da tam bu sınıftan bir eksik
yayını üç kez durdurmuştu. Kural: bir sayfa yeni bir anahtar çağırıyorsa o
anahtarın ÖZETİ de aynı commit'te gider; özet üreticisi depodaki veriyle
koşturulur, hem hat klasöründeki hem site kopyası commit edilir, ve yeni
özetin eskisine göre farkı YAZILIR (yeni 85 · düşen 0 · değişen 36).
DÜŞEN anahtar olmamalı; açıklanamayan bir değişiklik bir kusurdur.

(2) Tam o farkta bir kusur yakalandı: bütçe özeti ay ADINI biçimlenmiş
dizgeden yeniden ayrıştırıyordu — `_ay_yaz` çıktısı `08.2026`, ve
`pd.Timestamp("08.2026")` Ağustos değil OCAK veriyor. Sayfa TÜFE ayını
yanlış basıyordu ve hiçbir kapı bunu görmezdi: değer de tarih de "geçerli"
görünüyor. Ad artık HAM değerden türüyor. Bir dizgeyi kendi biçimleyicimizden
geçirdikten sonra geri okumak, sözleşmeyi iki kez uygulamaktır.

(3) GERİLEME KAPISI KOPYADAN SONRA DURUYORDU. 25.08'de Hazine 448 ihaleyi
16'ya düşürdüğünde konan kapı "tarihi geri giden hat düşmüş sayılır,
commit adımı onu dışarıda bırakır" diyordu; o cümle yalnız TAM kip için
doğruydu (`veri.yml` düşen tam kipi `git checkout` ile geri alır). HAFİF
kipte kapı ateşleniyor, hat "düştü" görünüyor, ama gerilemiş `ozet.json`
siteye ÇOKTAN kopyalanmış ve `if: always()` taşıyan commit adımı onu
yayımlamış oluyordu — 09.09 koşu #143'te ölçüldü (24 dosya commit'lendi).
Kapı hattın KENDİ ürettiği özeti okuyup kopyadan ÖNCE soruyor. Kaynak
sözleşmesi bilerek değiştiğinde (USD/TRY'nin valörden işlem gününe geçmesi)
elle `--gerileme-kabul`; iş akışı o ucu kullanmaz ve duman sınaması
`veri.yml`de geçmediğini de sınar. Bir sigortanın hangi kipte çalıştığı
konduğu gün yazılmazsa, sonraki oturum onu her kipte sanır.

Aynı turda dördüncü bir kusur ETİKETTE değil SINIRDA bulundu: yayın
kapısının "ileri tarih" ölçütü hafta sonunu atlıyor ama RESMÎ TATİLİ
bilmiyordu. 31.12.2026 perşembe tam iş günü; TCMB o gün ertesi iş gününün
kurunu ilan eder ve 1 Ocak tatil olduğu için o gün 04.01.2027'dir — tatil
bilmeyen sınır 01.01.2027 der ve YAYIMLANAN DOĞRU TARİHİ "ileri" sayıp
siteyi durdurur (04.09'da aynı sınıftan bir yanlış alarm yirmi bir saat
dondurmuştu). Sabit tarihli yedi tatil tabloya girdi; HAREKETLİ bayramlar
resmî takvimden OKUNMADAN YAZILMADI — uydurma bir tatil, olmayan bir günde
sınırı gevşetir ve gerçek bir ileri tarihi kaçırır. Girilmemiş yılda
davranış bugünküyle birebir aynı, yani tablo hiçbir koşulda YENİ bir yanlış
alarm üretemez: eklenen her gün sınırı yalnız İLERİ taşır. AÇIK KALAN:
Ramazan ve Kurban günleri girilmedi; girilene kadar o haftalarda sınır
yalnız hafta sonunu bilir.

**Kurucu ilke — ZORLANMIŞ KOŞU BEDAVA BİR DOĞRULAMA ARACI DEĞİLDİR; ve bir
KAYNAK SÖZLEŞMESİ değişimi hat başına BİR günlük engel demektir.** 09.09.2026
akşamı on altı hattın yeni kodu buluta zorlanmış koşuyla (`zorla=true`) tek
tek doğrulandı ve iki şey ölçüldü.

(1) KREDİ ZORLANMIŞ KOŞUDA SIĞMIYOR. Hattın ÖNBELLEKLİ hafif koşusu ölçülü
843 saniye; hafif kip adım tavanı 900. Yani sağlıklı hâlde bile pay %6 ve
`TTO_YENILE=1` ile veri adımı 900 saniyeyi aşıp süreç ağacıyla birlikte
kesildi. Tavanın yorumu "hafif kip dakikalarda biter, 15 dakikayı aşan adım
ASILMIŞTIR" diyor — bu hat için o cümle DOĞRU DEĞİL. Tavanı ölçmeden
büyütmek çare değil: dıştaki iş akışı adımı zaten 40 dakikada kesiyor ve o
sınır bütün hatların toplamı için. Kural: kredi (ve ölçülen süresi tavana
yaklaşan her hat) TAKVİMLE, yani önbellekli koşar; zorlanmış koşu bir
doğrulama aracı olarak yalnız süresi tavanın yarısının altında ölçülmüş
hatlarda kullanılır. Zamanlanmış koşu bu değişiklikten etkilenmiyor —
ölçülen 843 saniye tavanın altında.

(2) SÖZLEŞME DEĞİŞİNCE GERİLEME KAPISI BİR KEZ ÖTER VE BU DOĞRUDUR. USD/TRY
valörden işlem gününe geçince OVP panosunun saati 09.09'dan 08.09'a
"geriledi"; kapı siteye kopyalamayı durdurdu ve yayın bir koşu boyunca
donmuş kaldı. Gerileme gerçek değildi — hattın kendi çıktısındaki
`gecikme_kur_gun` ESKİ sürümde −1'di, yani yayımlanan damga KAPANMAMIŞ bir
günü ilan ediyordu. Doğru çözüm hattın O KOŞUDA ürettiği özeti kabul
etmektir (elle düzeltilmiş değer değil): 113 alanın hepsi hattın çıktısı,
yeni ve düşen anahtar sıfır. Bir kaynak sözleşmesi değiştirilirken bu bir
gün baştan hesaba katılır; kapı gevşetilmez.

Yan ölçüm, aynı akşam üçüncü kez görülen bir sınıf: fonlama Şekil 07'nin
alt yazısı kısaldı, figür 26 piksel alçaldı, sayfa eski yüksekliği ilan
etmeye devam etti ve YAYIN DÜŞTÜ — kusur hattın yeşil biten koşusunda değil
saatler sonra sitenin donmasında göründü. `guncelle.py` artık kopyalama
anında sapmayı adıyla uyarıyor. DİBS'te aynı sınıfın bir sonraki hâli
ölçülerek kapatıldı: alt yazıya veriden gelen ay adı girdiği için satır
sayısı ay adının uzunluğuna bağlı olabilirdi; 12×12 = 144 ay bileşiminin
hepsinde satır sayısı 3 çıktı ve bu ölçüm hattın duman sınamasına kilitlendi.

**KARAR (14.09.2026, kullanıcı istedi, ÖLÇÜM cevapladı) — ROT AYRI TAHMİN
EDİLMİYOR.** Hazine Şekil 11'in ipucu sorulurken ikinci bir soru daha geldi
("rot tahmini yapıyor muyuz burada") ve ayrı tahmin istendi. Ölçüldü; cevap
HAYIR ve gerekçe iki katmanlı.

Birincisi CEBİR, ölçüm değil: kestirici kıyasların ORTALAMASI ve ortalama
DOĞRUSALDIR, yani ort(Toplam) ≡ ort(İhale) + ort(ROT). "İki bacağı ayrı tahmin
edip toplayalım" önerisinin en düz biçimi mevcut yöntemle AYNI SAYIYI üretiyor
— 449 ihalenin 449'unda birebir, azami fark 1,5e−11 mn TL. Bir öneri ölçülmeden
önce, önerinin mevcut hâlden CEBİRSEL OLARAK farklı olup olmadığı sorulur;
burada değildi ve bu tek başına yarışın yarısını bitirdi.

İkincisi ÖLÇÜM: ayrı tahmini anlamlı kılmak için ROT'u bir PAY olarak
modelleyip ihale bacağını ona bölen üç kestirici (kıyas payı · kısaltılmış lag
payı · sabit yarı yarıya) örneklem DIŞI yarıştırıldı (yürüyen pencere, N=457).
En iyisi MAE'yi 6.953'ten 6.814'e indiriyor (%2,0) ama eşli fark ANLAMSIZ
(t p=0,384 · Wilcoxon p=0,314), bootstrap %95 güven aralığı sıfırı kapsıyor,
ihalelerin yalnız %47,3'ünde kazanıyor ve MEDYAN eşli fark mevcut yöntemin
LEHİNE. Üç saf kıyas ölçütü (genel medyan · tip medyanı · rastgele yürüyüş)
mevcut yöntemden KESİN olarak kötü (p<1e−12) — yani ölçülen isabet ROT
ayrıştırmasından değil KIYAS KURALINDAN geliyor.

Kararı asıl veren şey ZİNCİRİN TAMAMINDA ölçülmesiydi. Ham tahmin adımında
küçük ve anlamsız bir iyileşme gibi görünen kestiriciler, üretimdeki aylık
hedefe ölçekleme adımıyla BİRLİKTE koşulduğunda ANLAMLI BİÇİMDE KÖTÜLEŞİYOR
(+168 · Wilcoxon p=0,0069 ve +182 · p=0,0036). Bir adımı tek başına ölçüp
"biraz daha iyi" demek, o adımın zincirin geri kalanıyla nasıl çarpıştığını
sormamaktır — burada işaret tam tersine döndü.

Okura düşen kısım YAPILDI, çünkü asıl kusur tahminde değil GÖRÜNÜRLÜKTEYDİ:
ROT sayfada yalnız bir sütun listesinde geçiyordu, oysa 463 ihalenin medyanında
toplamın %49,5'i ve SIFIR olduğu tek bir ihale yok. Sözlüğe girdi, tahmin
bölümüne ölçülmüş payıyla yazıldı, Şekil 11'in ipucu B/C'nin tabanını "ihale +
ROT" diye söylüyor. Bir büyüklüğü ayrı TAHMİN etmekle ayrı GÖSTERMEK farklı
şeylerdir; ölçüm birincisini reddetti, ikincisi zaten eksikti.

AÇIK KALAN, adıyla: yarış yalnız Toplam(Gerçekleşme) üzerinde kuruldu —
zincirin tek doğrusal olmayan adımı olan bid-to-cover tahmini bu ölçüye girmedi
ve ayrı ölçüm ister. MAE seviyeye bağlı ve seviye altı yılda 12 kat büyüdü;
deflate edilmiş bir ölçüde sıralama değişebilir, ölçülmedi. En güncel rejimde
örneklem dar (2026'da N=47) ve o pencerede hiçbir eşli fark anlamlı değil.


**Kurucu ilke — BİR KURAL BİR GÜNÜ DEĞİL BİR SEANSI SORMALIDIR; ve bir
FİKSTÜRÜN girdisi CANLIYSA beklentisi SAYIYA değil SÖZLEŞMEYE bağlanır.**
14.09.2026'da kullanıcıya gün boyu "veri tazeleme" arıza e-postası gitti ve
zincir söküldüğünde iki ayrı kusur çıktı; ikisi de "sağlıklı görünen arıza"
sınıfından ve ikincisi yayımlanmış bir sayıydı.

(1) DONMUŞ BEKLENTİ, CANLI GİRDİ. `veri.yml` dört kez kırmızı bitti çünkü
`duman.py`nin ihale ölçütü donmuş bir çıpa gününe (07.09) bakıp CANLI plan
dosyasında "ihale günü sayısı 8" diyordu. O gün 14.09 ihalesi yapıldı,
takvimden düştü, sayı 7'ye indi ve ölçüt DÜŞTÜ. Bedeli tek bir e-postadan
büyük: duman adımlardan ÖNCE koşar, düştüğü için EVDS anahtarı, tazeleme
takvimi ve "Gereken hatları tazele" adımları ATLANDI — veri beş saat hiç
tazelenmedi ve e-postalar o sessizliğin yan etkisiydi. Aynı kusur 10.09'da
YPMevduat fikstüründe adıyla ölçülmüştü; kural vardı, bu ölçüte
uygulanmamıştı. Ölçüt ikiye ayrıldı: sentetik plan dosyası (girdi ve
beklenti BİRLİKTE donmuş) sözleşmenin dört maddesini sınar — sütun ADIYLA
sorulur, itfa tarihleri sızmaz, aynı günün iki ihalesi tekilleşir, ufkun
ötesi düşer — canlı dosyada ise yalnız kaymayan nitelik sorulur ve o yarının
çıpası BUGÜNDÜR: donmuş çıpa 2027'de meşru bir ihale gününü "itfa sızıntısı"
sayar, yani kaldırılan kusurun takvime bağlı biçimini geri koyardı.

(2) BİR GÜN, BİR SEANS DEĞİLDİR. Düzeltme zinciri açınca altından ikinci bir
arıza çıktı: usdtry ve ovp hatları "VERİ GERİLEDİ" (12.09 → 11.09) ile
durdu. 12.09 bir CUMARTESİ. 13.09 PAZAR koşusu (6d086e1c) seriye 12.09
cumartesi barını almıştı — `kur_gozlem` 675 → 678, `kur_son` 09.09 → 12.09,
`kur` 48,46 → 48,55 — ve cuma kapanışı 48,5921 olduğuna göre bu bayat bir
tekrar DEĞİL, cumanın %0,086 altında ayrı bir değerdi. `kapanmamis_bari_dusur`
onu göremez, çünkü o kural bir SEANSI değil bir GÜNÜ soruyor: cumartesi barı
PAZAR çekildiğinde artık "bugün" değildir. Yayımlanan dosya kendi içinde
çelişiyordu ve kimse bakmamıştı — hattın saati cumartesi, figür damgası
"kur ve TLREF 11.09.2026", çünkü TLREF iş günü serisi ve birleşik damga en
eski bacağı alır. Pazartesi Yahoo o barı hiç vermedi (678 → 677), gerileme
kapısı öttü ve iki pano siteye kopyalanamadı. Kapı DOĞRU davrandı; gerileyen
şey veri değil, kirli barın kendisiydi.

ÖLÇÜM HİPOTEZİ ÇÜRÜTMEDİ AMA KAPSAMI DÜZELTTİ, ve bu ayrı bir ders. İlk
keşif koşusu yfinance yolunu ölçtü ("2015 → bugün 3.045 gözlemde hafta sonu
barı SIFIR, hafta içi doluluk %99,7") — oysa ÜRETİM yfinance kullanmıyor:
`veri.yml`in hiçbir işi onu kurmuyor, hat chart ucundan besleniyor. Yani
ölçüm, kusurun doğduğu yola hiç bakmamıştı; "bir denetimin KAPSAMI denetimin
parçasıdır" kusurunun eşi, üstelik ölçümü yapan tarafta. Yan kanıt aynı
çıktıdaydı: yayımlanan 48,55 ne 11.09'un 48,5921'ine ne 14.09'un 48,6128'ine
yuvarlanıyor, yani cumartesi barı ayrı bir gözlem. Hükmü veren şey serinin
kendisi oldu: 21:01'deki üretim koşusu 3.044 gözlem (→ 11.09) demişti,
yfinance bugün 3.045 verip kapanmamış barı düşünce BİREBİR aynı — iki uç
ayrışmıyor ve 12.09 barı bugün hiçbir uçta YOK. Kaynak o barı GERİ ÇEKTİ.
Kaynağın geri çektiği bir bar hiçbir zaman yerleşmiş bir gözlem değildi.

Süzgeç bu yüzden kondu ve maliyeti ölçüldü: bugünkü seride düşen gözlem 0,
yıllıklandırılmış hıza etki +0,00 puan. SESSİZ SİLMİYOR — düşen gün ADIYLA
`kur_uyari`ya yazılıyor, çünkü kaynak bir gün damgalarını kaydırırsa (meşru
bir cuma seansı cumartesiye düşerse) sessiz bir süzgeç gerçek veriyi yok
eder, uyarı ise onu adıyla gösterir. SIRA da sözleşmenin parçası: süzgeç
kapsam denetiminden ÖNCE koşar, çünkü doluluk ölçütü `len(s)`i İŞ GÜNÜ
sayısıyla kıyaslıyor ve hafta sonu barı paydayı şişirip eksik bir hafta içi
gününü maskeleyebiliyordu — tek düzeltme iki kusuru birden kapatıyor. Yedi
ölçüt hattın duman sınamasında, çerçeve o günün birebir kendisi, ve BİRİNCİ
madde kapanmamış bar kuralının bu hâli DÜŞÜREMEDİĞİNİ sabitliyor: ikinci
süzgecin neden gerektiği yoruma değil ölçüte yazılı. Beş arıza
enjeksiyonunun beşi de yakalanıyor.

Üç yan bulgu kayda değer. Birincisi: `429 BİR ÖLÇÜM DEĞİLDİR` — keşif
betiği tek denemede "Too Many Requests" alıp pes etti ve iki koşu boyunca
ölçüm HİÇ yapılamadı; bir hız sınırı kaynağın ne döndürdüğü hakkında hiçbir
şey söylemez. İkincisi: yükleyicinin ilan ettiği sözleşme ("asıl yol
yfinance, yedek chart ucu") bulutta TERSİNE işliyor, çünkü `veri.yml` hiçbir
işte yfinance kurmuyor — yani üretimdeki USD/TRY tamamen çerezsiz ve hız
sınırlı ham uca bağlı. Keşif işine eklendi; TAZELEME işine bilerek
EKLENMEDİ, çünkü üretimde kur yolunu değiştirmek bir kaynak sözleşmesi
değişimidir ve gerileme kapısını bir gün öttürür (AÇIK KARAR). Üçüncüsü
tıkanmanın kendisi: bu arıza her hafta tekrar eder (pazar koşusu kirli damga
yazar, pazartesi "geriler") ama KENDİLİĞİNDEN AÇILIR — salı sabahı seri
14.09'u taşıyınca damga 12.09'un ilerisine geçer ve kapı susar; yani
`--gerileme-kabul` gerekmedi ve kapı gevşetilmedi.

**Kurucu ilke — BİR ÖLÇÜNÜN CETVELİ ÖLÇÜNÜN PARÇASIDIR; ve bir kuralın
uygulanmadığı yer, kuralın yazıldığı yerle aynı görünür.** 09.09.2026'da
denetimin görmediği dört hat (odemeler · fx · marj · ovp) aynı yöntemle
incelendi: 26 ham bulgu, 4 ÇÜRÜTÜLDÜ, 4 oylanamadan kaldı.

Turun ilk bulgusu oturumun KENDİ ölçümüydü ve yanlıştı. "Beş hattın yaşı
toleransını aşıyor" diye ölçüldü — kredi · makroihtiyati · yabanci ·
ypmevduat 12 gün (eşik 11), odemeler 71 (eşik 45) — ve haftalık dörtlünün
tarihçesi bunu doğruluyordu (sağlıklı çevrimde azami 13 gün). Eşikleri
gevşetmek kaçınılmaz görünüyordu. Tüketici okununca hüküm TERSİNE döndü:
`denetim.tazelik` VERİ TARİHİNİN YAŞINI değil `gozlem.son_gorulme` ile
"bu SÜRÜME geçileli kaç gün"ü ölçüyor; aynı hatlar o cetvelle 1, 1, 5, 0
gün ve 21 hattın HİÇBİRİ eşiğini aşmıyor. Depo bu ayrımı `RITIM` ile
`Tetik.en_gec` arasında zaten adıyla yazmıştı; ölçen taraf onu okumadan
ölçtü. Bir eşiği tartışmadan önce onu OKUYAN kodun hangi büyüklüğü
ölçtüğü sorulur — iki cetvel aynı birimi (gün) verir ve birbirine tıpatıp
benzer.

Ayakta kalanların en pahalısı OVP'deydi ve bir GÜN sonrası için kuruluydu.
TÜFE serisi ayın İLK gününde indeksli; hat üç ayrı yerde bu ham indeksi
saat olarak kullanıyordu. Kural dosyada ZATEN YAZILIYDI ("aylık bir gözlem
GÜN gibi yazılamaz") ama yalnız `tufe_tarih`e uygulanmıştı: aynı bloktan
fanlanan iki anahtar "01.08.2026" çıkıyor, `gecikme_tufe_gun` 39 yazıyor
(doğrusu 9), ve asıl bedel 15.09.2026'da geliyordu — yaş 45 günlük
toleransı aşıyor ve sıradaki TÜFE yayımına (03.10) kadar 18 gün okura
SAHTE "bacak gecikti" satırı basılacaktı. Çıpa TEK yere (`_saatler`),
yazım TEK fonksiyona (`blok_damga`) alındı: damga, yaş ve "en geride olan
blok" seçimi aynı günden okur. Bir kural bir kez yazılır, HER YERE
uygulanır; yazıldığı yerde doğru göründüğü için uygulanmadığı yer
görünmez.

Düzeltme kendi kuyruğunu da açtı: `KARANLIK_GUN['ovp']=75` tam o şişmeye
göre konmuştu. Çıpa düzelince ölçülen iç boşluk 38 → 8 güne indi ve eşik
ölçüden yeniden türetildi (yapısal azami 32 gün → eşik 50, yanlış alarm 0).
Bir kusura göre konmuş eşik, kusur düzeltilince yeniden ölçülmezse
gerekçesiz bir körlük olarak kalır.

Aynı sınıfın iki eşi daha kapandı. (1) `Deger` bir anahtarın kendi saati
yoksa hattın ANA saatini basar; FX'in optimizasyon karnesinin on anahtarı
ızgara aramasından geliyor ve arama haftalarca yenilenmiyordu —
kalibrasyon 22.07, ana saat 09.09, okur 49 gün önceki ölçümü bugünün
ölçümü sanıyordu. "Bir ŞEKLİN tarihi HATTIN tarihi değildir" kuralının
DEĞER tarafı. (2) Ödemeler dengesi ana saatini "30.06.2026" yazıyordu;
aynı anahtarı (`ay_kisa`) yazan kardeş hat butce-borc "06.2026" yazıyor —
tek anahtar adı, iki sözleşme, sayfa ikisini yan yana basıyor.

Kapsam kapısının öbür yarısı da kondu. Ölçüt "kütükteki her ilanın eşiği
var mı" diye soruyordu; "her eşiğin ALANI var mı" diye sormuyordu.
`denetim.tazelik` bir alanın kaydını bulamazsa `continue` der, yani adı
kayan bir ikincil saat eşiğini alır, sınavı geçer ve SONSUZA KADAR sessiz
kalır. Bugünkü ağaçta 29 kaydın 29'u karşılığını buluyor (yanlış alarm 0);
bir alan adı tek harf kaydırıldığında duman DÜŞÜYOR.

ÇÜRÜTÜLENLER de kayda değer, çünkü ikisi ikna ediciydi. "OVP kur bacağı
hâlâ EVDS valör damgalı" — hat Yahoo'ya geçtikten sonra koşmuş ve saatini
ilerletmişti. "Tarifteki TCMB kur yayımı artık hattın hiçbir saatini
ilerletmiyor, her gün sahte alarm doğacak" — mekanizma doğru, sonuç yanlış:
Yahoo'nun işlem günleri TCMB'nin yayım günleriyle örtüşüyor, yani tetikli
koşu saati yine ilerletiyor. Ölçüldü: 18 hattın 18'inde yeniden deneme
sayacı 0. Bir tarifin GEREKÇESİ eskiyebilir; ürettiği DAVRANIŞ eskimemiş
olabilir.

**Kurucu ilke — BİR ÇİZİM KÜTÜPHANESİ DE VERİYİ DOLDURUR; ve bir kapının
YANLIŞ ALARMI ile ÖLÇTÜĞÜ KUSUR aynı düzeltmeyi istemez.** 10.09.2026'da
"figürün çizdiği uç ile ilan edilen uç ayrışıyor" diye görünen tek bir bulgu
söküldü ve altından iki ayrı kusur çıktı; ikincisi YAYIMLANMIŞ bir sayıydı.

(1) ÇİZİM KATMANI SESSİZCE SIFIR ÜRETİYOR. Yığılı alan grafiğinde eksik bir
gözlem plotly'de öntanımlı olarak SIFIR sayılır (`stackgaps: "infer zero"`) —
yani kusur veri dosyasına hiç yazılmadan okura gider ve hiçbir veri denetimi
onu göremez. İki hatta ölçüldü. Fonlama Şekil 03'te `fillna(0)` bunu açıkça
yapıyordu: M'nin indeksi en HIZLI bacağın (kur) günlerini taşıyor, APİ
kalemleri bir gün geride bitiyor ve figür o gün A1'i 202.000 → 0, B1'i
1.040.741 → 0 çiziyordu. Bütçe Şekil 07'de `fillna` YOKTU ve kusur daha
büyüktü: üç bacak üç ayrı ritimde bitiyor (dış kredi 06.2026 · iç borç 07.2026
· eurobond 08.2026), her iz KENDİ indeksiyle çiziliyor ve plotly eksik ayları
sıfırlıyordu — merkezi yönetim borç stoku okura **14,93 → 13,89 → 4,73 trilyon
TL** diye çıktı, iki ayda 10 trilyon TL'lik sahte bir çöküş, ve o figür
haftalardır yayındaydı. Sayfanın damgası her iki hatta da DOĞRUYDU (bütçede
"aylık 06.2026"); yalan söyleyen ÇİZİMDİ. Kural: bir yığılı kompozisyon ancak
BÜTÜN kalemlerinin ölçüldüğü güne kadar çizilir; sağ uçtaki boşluk "bu kanal
kullanılmadı" değil "ölçülemedi" demektir. Kapı bütçede çağrı yerine değil her
figürün ZORUNLU son adımına kondu (`_duzen` → `_yigin_hizala`) ve ortak uç
yığının KENDİ üyelerinden ölçülüyor: elle tutulan bir kolon listesi olsaydı
yarın eklenecek yığın sessizce dışarıda kalırdı. Yayılma ölçüldü — sitedeki
177 figürün 9'u yığınlı, 7 çağrı yerinin 6'sı zaten aynı uçta bitiyordu ve
dokunulmadı.

Ölçünün CETVELİ de bir kez daha kusuru gizledi: ilk tarama "izin son değeri 0
iken bir öncekinin sıfırdan farklı olması" diye yazıldı ve Bütçe'yi HİÇ
göremedi, çünkü orada sıfır veride yok, plotly'nin yığılmasında doğuyor. Aynı
soruyu "yığındaki izlerin uçları aynı mı" diye sormak onu ilk denemede buldu.

(2) KAPININ YANLIŞ ALARMI AYRI BİR ARIZADIR. Fonlama'nın kapısı ilan edilen uç
ile çizilen ucun EŞİT olmasını istiyordu. Kural (`_uc`) bir alt kalem geride
kalınca damgayı DOĞRU biçimde geri çeker; `fillna(0)`lı iz geri gitmediği için
kapı bu MEŞRU çıktıyı "kolon listesi ayrışmış" diye okuyup istisna
fırlatıyordu — ölçüldü, on kalemin ALTISI tek başına hattın TAMAMINI
durduruyordu (Şekil 03-08 hiç yazılmaz, siteye kopyalama olmaz, iş akışı
kırmızı biter) ve ekrandaki teşhis de yanlış olduğu için sonraki oturum kolon
listesi arardı. Bir kapının yönü, ölçtüğü GÜVENCEDEN türer: damganın taşıdığı
söz "bayat bacağı taze gösterme"dir, öyleyse ilan çizilenden İLERİ olamaz;
GERİDE olması tutuculuktur ve nottur, engel değil. Kardeş hat YPMevduat aynı
kapıdan bir kez yanmış ve tek yönlüye geçmişti — kural depoda yazılıydı,
Fonlama'ya uygulanmamıştı ve muafiyetin gerekçesi ("orada defter figürün
çizdiği sütunlardan ölçülüyor, eşitlik doğal") ölçülmeden kabul edilmişti.

Kapı ağa çıkan `kos()`un İÇİNDEN ayrı bir fonksiyona çıkarıldı, çünkü orada
duran bir kapıyı hiçbir sınama koşturamaz; duman artık kuralın ilan ettiği
DÖRT hâle birden koşuyor ve karşılaştırmayı yeniden yazmıyor, KAPININ
KENDİSİNİ çağırıyor — yeniden yazsaydı kapı geri bozulduğunda da yeşil
geçerdi. İlk yazımda tam bu tuzağa düşülmüştü: üç maddenin ikisi aynı şeyi
ölçüyordu ve biri tanımı gereği hiç düşemezdi.


**Kurucu ilke — HATTIN KENDİ KAPISI, KURALIN MEŞRU ÇIKTISINI KUSUR SAYAMAZ; ve
BİR FİKSTÜRÜN GİRDİSİ DONMUŞSA ÖLÇÜSÜ DE DONMALIDIR.** 10.09.2026'da TÜFEX
arızasının aynı sınıftan eşleri altı hatta arandı. Beşi aynı kalıptaydı ve
hepsi "hattın duman sınaması, hattın kendi kuralının ürettiği çıktıyı ENGEL
sayıyor" diye okunuyor — duman adımlardan ÖNCE koştuğu için sonuç her seferinde
aynı: hat komple atlanır, panosu donar, iş akışı kırmızı biter, ve ekrandaki
teşhis yanlış olduğu için sonraki oturum kusuru yanlış yerde arar.

DİBS'te ölçüt kuralı YENİDEN YAZMIŞTI: sayfanın çağırdığı kıyas anahtarları
elle yazılmış bir düzenli ifadeyle sınanıyordu ve o kalıp `_degisim_bp_tarih`
sonekini hiç tanımıyordu — oysa döngü onu her koşuda üretiyor. Kural bir kez
tanımlanır, ölçüt onu SORAR: kapsam artık döngünün kendi sabitlerinden türüyor
ve iki yönlü sınanıyor (üretilen her anahtar ilan edilen kümenin içinde mi).

Kredi'de iki kusur birdeydi. Ölçülemeyen bir saat anahtarı ATLANIYORDU ve
sayfanın adıyla çağırdığı bir anahtar düştüğünde yayın kapısı ENGEL verir —
08.09'un kuralı ("sayfanın çağırdığı anahtar HER koşuda yazılır; ölçülemiyorsa
boş") bu hatta uygulanmamıştı. İkincisi daha sinsi: madde deponun O ANKİ
`ozet.json`una bakıyordu, oysa duman adımlardan ÖNCE koşar ve okuduğu dosya BİR
ÖNCEKİ koşunun çıktısıdır. Kaynak bir gün düşseydi ertesi koşuda madde düşer,
hat atlanır ve anahtarı geri getirecek koşu HİÇ BAŞLAMAZDI — onarımın tek yolu
kapanırdı. Bir sınama, düzeltmesi gereken arızayı kendi eliyle kalıcı
yapmamalı; doğru soru veride değil SÖZLEŞMEDEDİR ve sahte çerçeveyle sorulur.

Enflasyon'da garanti YARIMDI: "iki tüketici, tek tablo" maddesi iki dosyada
fonksiyon ADININ geçmesini soruyordu, aynı tabloya aynı GİRDİNİN verildiğini
değil. Çizim kanatları kabul koşulundan geçiriyor, özet üreticisi süzgeçsiz
veriyordu; yetersiz bir profilde çizim figürü hiç üretmiyor, özet o figüre
defterde TARİH yazıyordu — sayfa, üretilmemiş BAYAT bir figürün altına TAZE
damga basıyordu. Süzgeç tablonun İÇİNE alındı: artık ham kanat veren tüketici
ile süzülmüş kanat veren aynı defteri alır, ayrışma yapısal olarak imkânsız.

USD/TRY'de ölçüt kuralın ilan ettiği hâli tanımıyordu ve UYARI METNİ DE
YANLIŞTI ("açık anahtar çözülemezse damga ana saate düşer" — oysa defter
figürün girdisini `None` olarak taşır ve bileşen zinciri orada keser). Soru
üçe bölündü: ad kuralın ürettiği adlardan biri mi, figürün defter girdisi var
mı (ana saate düşüşü engelleyen tek şey bu), ve ölçülebilen bacak varken
anahtar yazılıyor mu. Anahtarın yokluğu artık ENGEL değil, adıyla NOT.

YPMevduat'ta kusur ölçütün İÇERİĞİNDE değil ZAMANINDAYDI ve o gün hattı
GERÇEKTEN durdurmuştu: TEMİZ fikstür son haftasını sabit bir güne demirliyor,
tazelik ölçüsü duvar saatine bakıyordu. Takvim ilerledikçe fikstür
kendiliğinden bayatladı — 09.09'da yaş tam toleransta, 10.09'da bir gün
fazlaydı ve üç madde birden çöktü; hattın panosu 09.09'da dondu ve haftalık
yayım günü olan 10.09 sabahı hiç koşamayacaktı. Duvar saati tek kapıdan
okunuyor artık (`veri.bugun_ts`) ve fikstür kendi gününü ÇERÇEVEDEN türetiyor;
üretim yolunda hiçbir şey değişmiyor, "referans duvar saatidir" ilkesi duruyor
ve çerçeveyi bugüne çıpalayan maddeler bilerek kapının DIŞINDA.

O düzeltmenin kuyruğu ayrıca kayda değer, çünkü ÖLÇÜNÜN KENDİSİNİ ölçtü: saat
dondurulunca gecikme dalının yalnız TESADÜFEN kapsandığı görüldü — ölçüt
"tolerans aşımı bayat sayılır mı" diye sormuyor, arızayı takvimin getirmesini
bekliyordu. Arıza enjeksiyonuyla ölçüldü: dal koddan tamamen çıkarıldığında
sınama YEŞİL geçiyordu. Bir tesadüfün kapattığı boşluk, tesadüf ortadan
kalkınca görünür — ve o ana kadar "ölçüt düşmedi" ile "arıza yok" birbirine
tıpatıp benzer.


**Kurucu ilke — BİR ÖLÇÜT, KURALIN İLAN ETTİĞİ HÂLLERE KOŞTURULMADIYSA
SINANMAMIŞTIR.** 10.09.2026 sabahı veri tazeleme 19,5 dakikada kırmızı bitti
ve kullanıcıya arıza e-postası gitti. Kusur veride değil KAPIDAYDI.

TÜFEX'in duman sınamasındaki genel madde "her bacağın tarihi damganın İÇİNDE
geçsin" diyordu. Hattın kendi kuralı ise: bacaklar aynı ritimdeyse ve
DAMGA_AYRIM_GUN'den (7) yakınsa damga TEK tarihtir — EN ESKİ bacak, çünkü
kıyas ancak hepsinin ölçüldüğü güne kadar kurulur. İki hüküm aynı dosyada,
birkaç satır arayla duruyordu ve "1-7 gün ayrık" hâlinde ZIT sonuç veriyordu:
dosyanın kendi sentetik maddesi (bacaklar 08.09 / 05.09 / 08.09 → damga 05.09)
genel maddeden geçirildiğinde DÜŞÜYOR. Çelişki iddia değil, ölçüm.

Görünmesi için bacakların ayrılması gerekti ve o gün ayrıldı: 10.09 DİBS
eğrisinin 3y ve 7y düğümleri kurulamadı, reel bacaklarının 1y ve 2y'si 10.09'a
geçerken 7y 09.09'da kaldı — bir gün. Son 400 iş gününde ilk kez. Öbür üç
figür geçti, çünkü onların bacakları yedi günden UZAK ayrık (3y düğümü
12.06'dan beri yok) ve iki parçalı damga her bacağı adıyla yazıyor. Kusur tam
da eşiğin ALTINDAKİ dar pencerede doğuyor.

Bedeli kapının yerinden geliyor: duman sınaması adımlardan ÖNCE koşar, o
yüzden hat komple atlandı ve panosu 09.09'da dondu; iki adım çıkış kodu 1
verdi, iş akışı kırmızı bitti. Geri kalan her şey normal işledi — commit
`if: always()` taşıdığı için 73 dosya yayına gitti. Arızanın görüntüsü ile
sağlığın görüntüsü yine birbirine benziyordu: koşu kırmızı ama site taze.

Yerine konan sözleşme kuralın DÖRT hâlinde de geçerli ve TEK tanımda:
damganın EN ESKİ tarihi bacakların en eskisidir (bir damga bayat bacağı taze
gösteremez — ölçünün taşıdığı asıl güvence bu), bacaklar eşikten uzak ayrıksa
her bacak adıyla geçer (eski maddenin DOĞRU olan yarısı), ve damga özetin
kendi bacaklarından kuralın ürettiği dizgenin ta kendisidir.

Asıl ders ölçütün içeriğinde değil KOŞTURULDUĞU YERDE: çelişki aylarca
görünmedi çünkü ölçüt, kuralın kendi ilan ettiği hâllere HİÇ uygulanmamıştı.
Kuralı sınayan dört sentetik madde vardı ve ölçütü sınayan tek madde yoktu.
Artık sözleşme o dört hâle de koşuyor; eski madde geri konduğunda nadir bir
veri hizalanmasını beklemeden, kuralın kendi hâlinde anında düşüyor (ölçüldü:
iki maddede birden). Bir kuralı sınamak ile o kuralı ÖLÇEN ölçütü sınamak iki
ayrı iştir; ikincisi yazılmazsa çelişki, ancak veri onu ortaya çıkardığı gün
ve yayının önünde durarak görünür.

**Kurucu ilke — BİR SÜZGECİN DAYANDIĞI VARSAYIM ÖLÇÜLMEZSE SÜZGEÇ KENDİ
GEREKÇESİNDEN BAĞIMSIZ YAŞAR; ve BİR EŞİK, ÖLÇÜNÜN RİTMİNE GÖRE ANLAM
DEĞİŞTİRİR.** Kullanıcı "projelerdeki veriler güncellendikçe önemli görülenler
bültene de gelmeli, okuyucularımızı hep güncel tutmalıyız" dedi. Ölçüm katmanı
onları ZATEN üretiyordu; kaybeden sayfaydı ve kusur üç katmanda birden çıktı.

(1) OKURA HİÇ ULAŞMAYAN KOVA. 07.09.2026'da konan tekilleştirme süzgeci
kümesini `one_cikanlar` ARTI `notlar`dan kuruyor ve üstündeki yorum "notlar
YUKARIDA duruyor" diyordu. `BultenGovde.astro`da `id="notlar"` diye bir bölüm
HİÇ OLMAMIŞTI; `b.notlar` dosyaya ilk kez o commit'le, yalnız süzgecin İÇİNDE
girdi. Sonuç iki yönlü ve sessiz: `dikkat` seviyesindeki olaylar hiçbir yerde
basılmıyor, üstelik basıldıkları VARSAYILARAK hat hat listesinden de
süzülüyordu. Ölçüldü (derlenmiş 17 sayı): 108 dikkat olayının 108'i sayfada
yok, kontrol olarak 37 önemli olayın 37'si var. 08.09'dan beri `one_cikanlar`
boş olduğu için okura ölçüm cümlesi HİÇ ulaşmıyordu — 10.09 sayısı sekiz olay
ölçmüştü ve "Hat hat değişim" tekilleştirmeden sonra SIFIR madde bırakıyordu;
okurun elinde yalnız "veri sürümü ilerledi" satırları kalıyordu, yani hangi
hattın yenilendiği yazılıyor, NE değiştiği hiç yazılmıyordu. Kural: bir süzgeç
yalnız GERÇEKTEN BASILAN bölümden kurulur ve kapı ÇIKTIYA bakar (sayfa sınavı
25) — olayı basan da süzen de bir BİLEŞENDİR, ikisi de kaynakta olay kovası
olarak görünmez. Ölçütün kendi yanlış alarmı da ölçülüp kapatıldı: kaçış
çözülmeden aranan beş cümle sayfada DURDUĞU HÂLDE kayıp sayılıyordu (`&#39;`,
`&amp;`); yayın kapısında duran bir ölçüt için beş yanlış alarm siteyi
durdurmak demektir, kıyasın iki tarafı da aynı süzgeçten geçer.

(2) TAKVİMLİ YAYIMDA HABER, YAYIMIN KENDİSİDİR. Eşik mantığı piyasa serisinde
doğrudur (her gün ilerleyen bir seride haber hareketin büyüklüğüdür) ama
takvimli bir istatistikte yanlış cevap verir. Ölçüldü: 04.09'da Ağustos TÜFE'si
yayımlandı, yıllık oran %31,75'ten %31,51'e indi ve bültendeki tek izi "veri
sürümü ilerledi" satırı oldu — motor kendi kuralınca DOĞRU sustu, çünkü 0,24
puanlık hareket 1,0 puanlık eşiğin altında. Okur ayın en çok beklenen verisinin
yayımlandığını bültenden öğrenemedi. `Izlem.yayim` bayrağı taşıyan anahtar,
kendi saati ilerlediğinde eşiğe bakılmadan duyurulur. Bayrak GÜNLÜK seriye
konmaz (her gün ateşler, bülteni boğar) ve bunun sınırı ölçüyle kondu: kütükteki
ritim eşikleri 4–6 ile 11+ diye iki kümede toplanıyor, sınır aradaki boşlukta.

(3) BİR ÖLÇÜMÜN KIYAS NOKTASI, KAYNAK SUSTUĞUNDA YERİNDE KALIR. Kıyas noktası
"o anahtarın saati bugünkünden FARKLI olan en son görüntü"ydü; kaynak yayımı
durdurduğunda bu nokta kımıldamıyor ve cümle her sabah yeniden kuruluyordu.
Ölçüldü (17 sayı): 145 ölçüm cümlesinin 84'ü (%57,9) daha önce AYNI veri
tarihiyle duyurulmuş cümlelerin tekrarı; tek başına Hazine hattının üç cümlesi
18.08 ihalesini 21.07 ile kıyaslayarak 48 kez basıldı ve 10 Eylül'de hâlâ 23
gün önceki veri "azaldı" diye okunuyordu. Kural: bir ölçüm, saati BİR ÖNCEKİ
SÜRÜME göre ilerlediyse duyurulur. Yazarken bir tuzağa düşülüp çıkıldı —
"sondan ikinci kayıt" yanlış kıyas noktasıdır, çünkü defter yalnız içerik
değiştiğinde satır yazar ve donmuş bir hatta son kayıt bugünkü görüntünün ta
kendisidir; ölçüt tam da düzeltmek istediği tekrarı üretirdi. Doğrusu "bugünkü
görüntüden FARKLI olan en son kayıt".

Aynı düzeltme iki sahte bildirimi de kapattı ve ikisi de DİZGE kıyasından
doğuyordu: Büyüme hattı yalnız tarih YAZIMI değiştiği için (30.06.2026 →
06.2026, iki sayısı da birebir aynı) "veri sürümü ilerledi" diye
duyuruluyordu; OVP hattı ise 09.09.2026 → 08.09.2026 GERİLEMESİNİ "ilerledi"
diye basıyordu. Kıyas artık `ortak/bicim` çözücüsünden geçiyor ve SIKI
BÜYÜKTÜR; çözülemeyen tarihte eski davranış korunuyor, çünkü ayrıştıramayan bir
denetim hep "sorun yok" der.

(4) KAPSAM YİNE SÖZLEŞMEDEN TÜRETİLDİ. 21 hattın 9'unun izlemi HİÇ YOKTU ve
altısına bültenin hiçbir ölçüm kanalı dokunmuyordu — 501 sayısal ölçüm
yayımlanıyor, tek izleri "veri sürümü ilerledi" satırıydı. Beş takvimli hat
izleme alındı; kalan dördü GEREKÇESİYLE muaf ve gerekçe KODA yazıldı, çünkü
gerekçe yazılmazsa bir sonraki oturum unutulmuş bir hat ile bilinçli bir
muafiyeti ayırt edemez. Duman ölçütü her iki yönü de sorar (izlemsiz hat
gerekçeli mi, gerekçeli hat gerçekten izlemsiz mi) ve dört arıza enjeksiyonunun
dördünü de yakalıyor. Mevcut kapı (`_hat_adi_kapsami`) yeni hattın ADINI
soruyordu, izleminin olup olmadığını sormuyordu — bir denetim eklenirken "bu
ölçüt doğru mu" kadar "bu ölçüt neyi HİÇ görmüyor" da sorulur.

Yeni izlemlerin eşiği YOK ve bu bilerek: bu hatların tarihçesi bültenin kendi
defterinde henüz yok (yp-mevduat 2 kayıt), yani "kaç puanlık hareket dikkate
değer" sorusu ÖLÇÜLEMİYOR. Ölçülmemiş bir seviyeye eşik konmaz; yerine takvimli
yayımın kendisi olay sayılıyor, tarihçe birikince eşik ölçülüp eklenir.

**Kurucu ilke — BİR MERKEZ BANKASI METNİNİN TONU, DEĞİŞMEYEN PARAGRAFTA
ÖLÇÜLÜR; ve İKİNCİ ELDEN ÖZET, ÖLÇÜLMEDEN KAYNAK SAYILMAZ.** 10.09.2026 PPK
kararı üzerine analiz istendi ("sektör ne demiş, dovish mi hawkish mi").
Elimizdeki tek kanal arama motoruydu ve ÖLÇÜLEREK güvenilmez bulundu:
döndürdüğü piyasa tepkisi paragrafı USD/TRY'yi 34,85 yazıyordu, hattın kendi
ölçümü 48,46 — %28 sapma, üstelik aynı özette bozuk sayılar vardı. Bir kaynağın
güvenilirliği, kullanmadan ÖNCE elimizdeki bir ölçüme karşı sınanabilir; bu
sınama yapılmasaydı yazının bir paragrafı uydurma olurdu.

Doğru yol depoda zaten vardı: bu oturumlar `www.tcmb.gov.tr`ye çıkamıyor ama
BULUT KOŞUCUSU çıkabiliyor (dört adresin dördü de 200). `bulten/kesif_ppk.py`
duyuruları oradan indirip metni olduğu gibi döküyor; yorum yapmıyor, hüküm
kurmuyor — çıktısı ham girdidir. Duyuru numarası SABİTLENMİYOR, liste
sayfasından çözülüyor. İki tuzak ölçülerek kapandı: sıralama adrese göre
yapılınca "…-01" < "…-12" < "…-17" olduğu için yılın EN ESKİ kararları indi
(numara yıl içinde artar, sıralama numaraya göre olmalı), ve künye çıpası
yalnız İngilizceyi tanıdığı için ("No:" — Türkçesi "Sayı:") gereken metin tam
da kaybedildi.

Ton ölçümünün kendisi mekanik: altı duyurunun tam metni paragraflarına ayrılıp
karşılaştırıldı. 10 Eylül metninin yedi paragrafından ALTISI 23 Temmuz metniyle
birebir aynı; değişen tek paragraf teşhis. Yıla yayıldığında teşhis 5/5 geçişte
değişmiş, rehberliği taşıyan duruş paragrafı 11 Haziran'dan beri HİÇ
değişmemiş. Asıl bulgu KAYIP BİR CÜMLEDE: "Adımların büyüklüğü … gözden
geçirilmektedir" yılın altı metninde yalnız 22 Ocak'ta — indirimin yapıldığı
duyuruda — var; bir sonraki toplantıda kaldırıldı ve beş toplantıdır geri
gelmedi. "Bu metin güvercinleşti" hissi iki okurda iki sonuç verir; hangi
cümlenin eklendiği ve hangisinin çıkarıldığı tek sonuç verir. Ve bir ifadenin
"ilk kez geçiyor" hükmü, yılın TAMAMINA karşı taranmadan kurulmaz.

Ölçülemeyen yazılmadı: sektörün YORUMU birincil kaynaktan doğrulanamadığı için
yazıya hiç girmedi, sektörün duruşu yalnız ölçülebilir iki biçimde verildi
(TCMB'nin kendi katılımcı anketi ve piyasanın fiyatlaması); sürpriz de karar
öncesi sayısal beklenti medyanı elde olmadığı için hesaplanmadı. Aynı disiplin
eğri hükmünde: 1 yıl ile politika faizi arasındaki 207 baz puanın ne kadarının
beklenti ne kadarının vade primi olduğu ayrıştırılmadığı için hüküm "piyasa
artış bekliyor" değil "eğri bir yıla yayılan indirim döngüsü fiyatlamıyor" ile
sınırlı tutuldu.

**Kurucu ilke — BİR ENDEKSİN ÖRNEKLEM İÇİ İSABETİ, ÇOĞU ZAMAN SIZINTININ
BÜYÜKLÜĞÜDÜR; ve BİR SÜZGECİN NEYİ SORDUĞUNU BİLMEMESİ, YANLIŞ SORMASINDAN
DAHA SESSİZDİR.** 10.09.2026'da kullanıcı önceki PPK metinlerinin incelenmesini
ve bir şahin/güvercin endeksi istedi. Arşiv kuruldu, endeks kuruldu, endeks
DÜŞTÜ — ve düşmesi kayda değer bir sonuç.

ARŞİV ÖNCE YOKLANDI. On bir yılın on birinde de üç liste sayfası açık ve ~131
tekil faiz kararı var; hat ancak bu ölçümden sonra kuruldu. Arşiv DEPODA duruyor,
çünkü yayımlanmış bir duyuru bir daha değişmez ve her ölçümde yeniden indirilen
bir girdi ölçümü kaynağın o günkü hâline bağımlı kılar. Ham PARAGRAFLARIN
saklanması ayrıca kendini ödedi: ayrıştırıcı iki kez düzeltildi ve ikisinde de
kaynak yeniden yüklenmedi.

SÜZGEÇ NEYİ SORDUĞUNU BİLMELİ. Sınıflandırıcı başlıkta "faiz oran" alt dizesini
arıyordu ve kırk bir "Kredi Kartı İşlemlerinde Uygulanacak AZAMİ FAİZ
ORANLARINA İlişkin Basın Duyurusu" PPK kararı sayıldı. Belgeler gerçek,
tarihleri gerçek, yalnızca SORU yanlıştı — endekse girselerdi kredi kartı
duyuruları PPK metni gibi puanlanacaktı ve hiçbir sayı bunu söylemeyecekti.
Düzeltmenin KENDİSİ ikinci bir kusur üretti (sıkı kalıp 2019 ve öncesinin
"PRESS RELEASE ON Summary…" başlıklı İngilizce özetlerini düşürdü); kapsam
kadar HASSASİYET de denetimin parçası ve son hâlde düşen kırk bir belgenin
kırk biri de gerçekten kredi kartı duyurusu.

ÇIPA İKİ REJİMİ BİRDEN TUTMALI. "politika faizi" ifadesini aramak 2016–2017'nin
TAMAMINI kaçırıyordu: o yıllarda oranlar maddeler hâlinde sayılıyordu. İki
dönemde de bulunan ifade "bir hafta vadeli repo ihale faiz oranı". Çıpanın
ardındaki pencere de CÜMLEYLE sınırlanmalı — sabit uzunlukta pencere koridor
cümlesine taşıyor ve "son oran" gecelik borçlanma faizi oluyordu (2026-01 %37
yerine %35,5). Sekiz bilinen dönüm noktasına karşı sınandı.

ENDEKSİN ÜÇ SIZINTISI VE HER BİRİNİN İŞARETİ AYNI YÖNE BAKIYORDU.
(1) Tek eşikli bir kural yapısal olarak hiç "sabit" diyemez; 111 kararın 67'si
sabit olduğu için ölçüt endeksin sinyalini değil KENDİ KUSURUNU ölçüyordu
(eğitim isabeti %30,6, saf kuralın yarısı). (2) En güçlü "güvercin" kalıp bir
KURUL ÜYESİ İSİM LİSTESİ çıktı: endeks tonu değil BAŞKAN SABİT ETKİSİNİ
öğrenmişti — doğru bir gözlem, ama metnin tonu değil ve yeni bir metin hakkında
hiçbir şey söylemez. (3) Kararın kendi cümlesi girdideydi, yani cevap soruya
konmuştu; ağırlığı küçüktü (−0,02) ama sızıntı ölçülünce kaldırılır, etkisi
küçük diye bırakılmaz. Üçü temizlenmeden ÖNCE eğitim isabeti %88,9'du; sonra
sinyal kalmadı. Aradaki fark endeksin gücü değil, ölçüm kusurunun büyüklüğü.

SAF KIYAS ÖLÇÜTÜ OLMADAN İSABET SAYISI ANLAMSIZDIR. 111 kararın 67'si sabit;
her toplantıda hiçbir şey demeden "sabit" diyen kural %50–67 isabet tutturur.
Endeks örneklem dışında bunu geçemedi (eşzamanlı −7,9 puan, öncü −5,4 puan) ve
yayına GİRMEDİ. Sebep de ölçülebilir: 2016–2022 ile 2023–2026 aynı rejim değil.

YAYINA GİREN, ÖRNEKLEM İÇİ OLDUĞU YAZILARAK GİRDİ. "Adımların büyüklüğü"
cümlesi 111 kararın beşinde geçiyor ve BEŞİ DE indirim; on bir yılda hiçbir
sabit kararda ve hiçbir artırımda yok. Ama 21 indirim bu cümle olmadan yapıldı
(yokluğu indirimi dışlamıyor) ve kalıp 2026 metinlerine BAKILARAK seçildi, yani
ilişki örneklem içi. İkisi de yazıya kondu ve sınanabilir hâli ileriye dönük
olarak izleme listesine girdi. Bir gözlem yayımlanabilir; yayımlanamayacak olan,
onu ölçülmüş bir öngörü gibi sunmaktır.

**Kurucu ilke — 7/24 İŞLEM GÖREN BİR SERİDE "KAPANMIŞ SEANS" BİR SEÇİMDİR ve
seçimin bedeli ÖLÇÜLEBİLİR.** Kullanıcı "48,46 dünün kuru değil mi, bugün 48,49
gibi" dedi. Sayı yanlış değildi — analiz "9 Eylül kapanışında" diye yazıyordu ve
48,4631 o günün kapanışı. Ama gözlem gerçek bir mekanizmayı işaret ediyordu:
`ortak/usdtry.kapanmamis_bari_dusur` bugüne ait barı gün UTC'de kapanmadan
seriye almıyor ve FX 7/24 işlediği için UTC günü 00:00'da kapanıyor. İstanbul
seansı 15:00 UTC'de kapandıktan sonra DOKUZ SAAT daha dünkü kur yayımlanıyor.
Maliyet ölçüldü (250 iş günü): medyan 0,028 TL (%0,062), p90 0,092 TL, azami
0,253 TL — ve RASTGELE DEĞİL, 250 günün 201'i artı yönlü, yani bir gün eski kur
sistematik olarak DÜŞÜK gösteriyor. Sabah bülteni penceresinde iki konvansiyon
da aynı barı verir; ayrışma yalnız akşam yayımlarında.

KARAR (10.09.2026, kullanıcı): UTC günü KALIYOR, etiket güçleniyor. Gerekçe
kayda geçsin ki bir sonraki oturum yeniden önermesin — İstanbul kapanışına
geçmek 14-15 saat tazelik kazandırırdı ama 15:00'te alınan bar FİNAL DEĞİL ve
bir aylık yıllıklandırılmış hız son gözleme aşırı duyarlı (son değer %0,1
oynarsa oran 1,5 puan kayar), yani akşam yayımlanan sayı ertesi sabah REVİZE
olurdu. Yayımlanmış bir sayının revize olmaması, dokuz saatlik tazelikten
değerli bulundu. Ölçülemeyen de yazıldı: 15:00–24:00 UTC hareketinin gerçek
dağılımı bu oturumdan ölçülemedi.

Bir yapısal kusur kayda değer ve KALIYOR: kural İKİ yerde yazılı
(`ortak/usdtry` ve `bulten/piyasa.KAPANIS_UTC`) ve duman fikstürü 12:00 UTC'de
koştuğu için iki konvansiyonu AYIRT EDEMİYOR — yani bu kural bir gün
değiştirilirse hiçbir kapı görmez.

**Kurucu ilke — BİR BAŞLIK KIRPILMAZ, TAŞAR; ve bir HÜKÜM, GEREKÇESİNİN
ÜSTÜNE yazılır.** Brooks indikatörüne rehber figürleri eklenirken iki kusur
çıktı ve ikisi de "kaynak doğru, okur eksik görüyor" sınıfından.

Birincisi ölçülebilir ve genel: plotly başlık metnini figür genişliğine
SIĞDIRMAZ, dışarı taşırır. Alt yazının sağ ucu çizim alanının dışında kalıyor
ve orada hiçbir şey yokmuş gibi görünüyor — yani cümlenin yarısı okura hiç
ulaşmıyor, üstelik eksik olduğu da anlaşılmıyor. Yedi figürün ikisinde
ölçüldü. Sayfa sınavının 19. ölçütü figür alt yazısını okur diliyle tarıyor
ama UZUNLUĞUNU sormuyor; kural bu yüzden çizim katmanına kondu
(`brooks_sekil._sar`, 104 karakter) ve üst boşluk satır sayısından türüyor —
sabit bir üst boşluk, sarılan başlığı çizim alanının içine iterdi.
Aynı figürlerde iki biçim kusuru daha vardı ve ikisi de sözleşmenin zaten
yazılı olduğu yerdeydi: sayılar `.2f` ile ondalık NOKTALI, binlik ayraç
ASCII virgüllü basılıyordu ve yatay eksende okura BAR SIRA NUMARASI
yazılıyordu ("360") — o sayı bir gözlem değil bizim dizinimiz. Üçü de
`ortak/bicim` sözleşmesine çekildi. Bir figür ürettiğinizde sayıyı yazan
kodun hangi sözleşmeden okuduğu sorulur; grafik kütüphanesinin varsayılanı
bizim sözleşmemiz değildir.

İkincisi TradingView tarafında ve kullanıcı adıyla koydu ("indikatörün
okunması biraz zor"). Her iki panelin durum kutusu da UYGULAMA sırasına göre
dizilmişti: fiyat panelinde on dört satır düz akıyordu, alt panelde rejim
HÜKMÜ (`BANT` · `ara` · `trend`) sekiz satırlık tablonun alttan ikincisindeydi
ve beş ham ölçü onun ÜSTÜNDEydi. Oysa okuma sırası dersin dayattığı sıradır ve
alt panel o sıranın BİRİNCİ adımı: cevabı tek sözcük. Ölçüler hükmün
gerekçesidir, gerekçe hükmün altına yazılır. İki kutu da yeniden dizildi
(① rejim → ② yön → ③ yasak → ④ kurulum; ayrıntı ayrı bölümde, `Özet`
kipinde gizli) ve kurulum satırı BİLEREK en sonda: gözü ilk oraya giden okur
kararı çoktan vermiş olur. `asgariKalite` varsayılanı da 0'dan 2'ye çekildi —
sıfırda her dönüş barı etiketleniyor ve ölçüldüğüne göre barların yarıdan
fazlası o koşulu sağlıyor, yani varsayılan ayar grafiği okunmaz yapıyordu.

Kutuların fonksiyonlara bölünmesi YENİ bir Pine hata sınıfı açtı: betik
yukarıdan aşağı derlenir, bir kullanıcı fonksiyonu çağrıldığı satırdan önce
tanımlanmış olmalıdır. O güne kadar dosyalarda tek bir kullanıcı fonksiyonu
yoktu; risk kodla birlikte doğdu ve `pine_denetle`ye yedinci ölçüt olarak
kondu. Ölçüt arızanın kendisine karşı koşturuldu ve İLK enjeksiyon YANLIŞTI:
tanım birkaç satır aşağı kaydırıldı ama çağrısının hâlâ ÜSTÜNDE kaldı, yani
arıza hiç üretilmedi ve "ölçüt kör" hükmü verilecekti. Tanım dosyanın SONUNA
alınınca ölçüt iki dosyada da düştü. Bu depoda bir kez daha kayıtlı olan
kusurun eşi: bir regresyon sınamasının kendisi de yanlış olabilir ve "ölçüt
düşmedi" ile "arıza yok" birbirine tıpatıp benzer.

Aynı turda üçüncü bir kusur, figürleri üretmek için replikasyonu İLK
BARDAN çağırınca çıktı: `en_dusuk`/`en_yuksek` boş pencerede istisna
fırlatıyordu. Pine orada `na` döner ve `na` ile yapılan her karşılaştırma
`false`'tur; Python'da birebir karşılığı `nan`. Üretim yolu ısınma payıyla
koştuğu için bu hâl hiçbir kapıda görünmüyordu — ama dosyayı kendi indirip
koşturan okur onu ilk satırda görürdü. BİR REPLİKASYONUN SADAKATİ, ÜRETİM
YOLUNUN HİÇ UĞRAMADIĞI BARLARDA DA ÖLÇÜLÜR. Ölçütün kendi teşhisi de
düzeltildi: ilk yazımda arıza enjekte edilince sınama ÇÖKÜYORDU, yani
ekrandaki hata sınamanın kendi kusuru gibi görünüyordu; artık adıyla
bildiriyor.

AÇIK KALAN — bu Pine hiç DERLENMEDİ. `pine_denetle`nin yedi ölçütü bu
oturumda gerçekten yapılmış yedi hatanın sınıfını kapatıyor; kapatmadığı her
şey açık. TradingView'e yapıştırılana kadar "derleniyor" cümlesi bir ÖLÇÜM
değil bir beklentidir.

**KARAR (15.09.2026, kullanıcı) — İNDİKATÖR v2: GÖRELİ EŞİK, BEŞ EMİR PAKETİ,
YAYIMLANMIŞ BACKTEST; SAYFA REHBER OLARAK YENİDEN YAZILDI.** Kullanıcı EUR/USD
5 dakikalık ekran görüntüsüyle geldi: "burada kırmızı hep eşik üstünde değil mi?
hep bant diyecek bu şekilde. ayrıca barlar boyandığı için algılaması biraz zor.
… daha fazla trade edilebilecek ve aynı zamanda backtesti yapılmış bir
indikatör kurmamız gerekiyor. yazıyı da aynı temelle tekrar yaz." Gözlem
ÖLÇÜLDÜ ve doğruydu: dersin Şekil 30 eşikleri tek seride tek günde ölçülmüş
SEVİYELERDİR ve enstrümana göre kayıyor — örtüşme işareti 13 serinin (1 sa · 4 sa ·
günlük) 7'sinde pencerelerin %100'ünde, 9'unda %99'un üstünde açık, ABD 10 yıllık
getirinin 4 saatliğinde %0; Yahoo 5 dk EUR/USD'de %3, USD/CHF'de %100, GBP/USD'de
%9; doji işareti 13 serinin 13'ünde %0. Sabit bir eşik bir enstrümanda hep
"bant", öbüründe hiç "bant" der ve ikisi de rejim ölçmez. Öntanımlı kip GÖRELİ
oldu: her ölçü son 280 bardaki kendi değerlerine göre `ta.percentrank`
sözleşmesiyle sıralanır, sıra ≥ 0,60 işaret (`RejimPanosu.olcu_goreli`,
`BANT_YONU`); ders (mutlak) kipi seçenek. Ölçülmüş sınır ADIYLA sayfada:
göreli hüküm de ileriye dönük bir şey söylemiyor (5 seri × 2 tarihçe, BANT ile
trend pencerelerinin ileri 35 barlık net/aralık'ı ayrışmıyor, permütasyon p
0,19–0,94; 30 Spearman sınamasında p<0,05 yalnız 2 ≈ şans) — pano TARİF eder,
tahmin etmez.

"Daha fazla trade" dersin KENDİ paketleriyle karşılandı, eşik gevşetilerek
değil: dönüş barı · ikinci giriş (H2/L2) · kırılım modu · başarısız dönüş ·
bant kenarı (`Kurulumlar`), her biri dersin sayısıyla (uç ± tick stop emri,
bir bar ömür, karşı uç ± tick koruyucu stop, 1R/2R, altı tick kuralı,
sıkılaştırma/başabaş). Pine ④ satırı paket adıyla konuşuyor, altında "Emir"
satırı ve son barın dört çizgisi. Öntanımlılar ölçülerek sadeleşti: bar
boyama yalnız güçlü trend barı (beş kademe 100 barda 72 renk değişimi),
`asgariKalite` 2, sayım ve kalıp etiketleri kapalı.

BACKTEST YAYIMLANDI ve HÜKMÜ "KENAR YOK". `site/tools/brooks_backtest.py`
(1 sa/4 sa/günlük 13 seri, 4.574 bar) ve `bulten/kesif_brooks_5dk.py` (Yahoo
5/15 dk beş FX serisi, 61.150 bar, 59 gün; bulut #187–#193) 11 bileşim × 2
hedef × 2 yönetim = 44 satır; her satırda rastgele giriş tabanı (60 koşu, aynı
emir sayısı, aynı mekanik), bootstrap %95 aralığı, iki yarı, 5 dk'da maliyet
(0/0,5/1/2 pip) ve risk dilimi. Üç bulgu kayda değer. (1) Brüt artı ortalama
EN KÜÇÜK RİSKLİ işlemlerden geliyor (küçük dilim brüt +0,24, 1 pip'te −0,51;
medyan risk 2–3 pip; Yahoo EUR/USD 5 dk barlarının %38'i sıfır gövdeli) —
bid-ask sıçraması ve kırpık besleme artefaktı; 0,5 pip gidiş-dönüşte
başarısız dönüş (+0,10, N=867, bir pipte −0,12) dışındaki her satır eksi. (2) Kırılım modu 1 saatlik ve
üstünde brüt artı (N≈85–97, aralık sıfırın üstünde, rastgele 96–100) ama
ÖRNEKLEM DIŞI sınandığında 5 dakikalığa TAŞINMADI ve 13 serideki artı iki
seriden geliyor — tek ölçekte birkaç seride görülen bir kenar kural
değildir. (3) Kalite ve rejim süzgeçleri isabeti DEĞİŞTİRMİYOR (K≥3 5 dk'da
−0,01; göreli rejim ile rejimsiz +0,10 / +0,11): süzgeç paket ailesini seçer,
sonucu ayırmaz. Sayfa bunu manşette söylüyor; tablo bileşeni (`BrooksBacktest`)
sayıyı dosyadan basar, prose'a elle sayı yazılmadı. Rastgele yüzdelik 100 olan
satır çok, kenar yok — "rastgeleden iyi" ile "maliyetten iyi" aynı şey değil.

Yol boyunca beş kusur ölçülerek kapandı ve her biri bu dosyada adı olan bir
sınıfın eşi. (a) BAR SAYACI dersin tanımını taşımıyordu: zirvesi öncekini
aşan HER barı sayıyor, iki ardışık yükselen bar H1 ve H2 oluyordu — 1.297
etiketin %88'i tavan H4'tü. Ders bacakla sayar (aşamayan bir bar araya
girmeden H2 yok); `_sayim_makinesi` o tanımı taşır, eski sayaç yalnız ölçüm
için duruyor. (b) BANT KENARI paketi yön filtresi serbest değilken trendde
fade işareti basıyordu (BIST 100 1 sa'da pencerenin dokuz barı "bant"); şart
Python ve Pine'da birlikte kondu. (c) Pine'da `if` bloğunun İÇİNE yazılan
fonksiyon derlenmez ve yedinci ölçüt onu görmüyordu (tanım çağrıdan
öncedeydi) — `pine_denetle` 8. ölçüt, arıza enjeksiyonuyla sınandı.
(d) Durum kutusunun çıpaları ELLE yazılmıştı ve göreli kip 280 bar tarihçe
isteyince hikâyeleri artık anlatmıyordu; `brooks_kutu.py --ara` adayları
ARAR, çıpa damgayla çözülür ve hikâye çizim anında yeniden sınanır. Kutu
Pine'ın paket önceliğini birebir taşır (`paket_sec`), `asgariKalite` bir
görünüm girdisi olduğu için eşik tablosunda değil Pine dosyasından okunur.
(f) İKİNCİ GİRİŞ paketi yön yasağına bakmıyordu — dönüş barı ve başarısız dönüş
bakıyordu, sayfa "kapalı yönde paket basılmaz" diyordu; doğrulama merceği yakaladı,
Pine · kutu · figür hizalandı (backtest'in tam indikatörü yasağı zaten her pakete
uyguluyordu, sayılar değişmedi). Aynı mercek alt panel not metinlerinin sayfada
Pine'dakinden farklı yazıldığını, alarm sayısının 13 olduğunu (10 + 3), kırılım
modunda 1R/2R çizgisi çizilmediğini ve gövde boşluğunun hesaplanıp hiç
basılmadığını buldu — hepsi kaynağa karşı satır satır okumadan görünmezdi.
(e) Yazarken kendi kapılarımıza takıldık ve ikisi kayda değer:
`brooks_ornek.py`nin duman kapısı dist↔public md5 ister, yani her figür
yenilemesi derleme ister — ara adımda `cp` ile dist'e kopyalamak meşru (derleme
public'i olduğu gibi kopyalar); ve `python3 -c "import brooks_referans"`
public altına `__pycache__` bırakıp yayın kapısını düşürüyor. Bir de iş akışı
tuzağı: keşif koşusu tazelemeyle AYNI `veri` concurrency grubunda ve
`cancel-in-progress: false`; zamanlanmış tazeleme sürerken tetiklenen keşif 18
dakika "pending" bekledi. Keşif ve tazeleme aynı deponun aynı dalına yazmıyor,
grup ayrılabilir — bu oturumda değiştirilmedi.

(g) İKİNCİ DOĞRULAMA TURU sayfayı KAYNAĞA karşı okudu (ders metni · ölçüm
dosyaları · Pine · replikasyon): 34 ham bulgu, 17'si ilk turda çoktan
kapanmış çıktı, 17'si ayakta kaldı ve hepsi düzeltildi. Üç sınıf kayda değer.
Birincisi DERSLE ÇELİŞEN İDDİA: sayfa "kırılım modunda hedef yoktur" diyordu,
ders kalıbın boyu kadar ölçülmüş hareket verir (4.11 · 5.14) — kalıbın boyu
risk olduğu için 1R'ye denk düşer; "iki sayım arasında en az bir aşamayan bar"
şartı DERSİN değil SAYACIN seçimi (Şekil 46 notu ardışık H1·H2'yi olası
sayar) ve sayfa onu dersin tanımı gibi yazıyordu; ders 18 değil on yedi bölüm
(0–16, 8A/8B). İkincisi ÖLÇÜM DOSYASINDAN DOĞRULANAMAYAN SAYI: "örtüşme en sık
bağlayan niteliktir" cümlesinin arkasında yalnız örtüşmenin sayısı vardı,
öbür üç niteliğin düşme sayısı hiç ölçülmemişti — ölçüldü (`_nitelik_dusme_k2`
· `_k3`), en sık bağlayan KUYRUK çıktı (2.316 barın 2.101'i), örtüşme
DÖRDÜNCÜ (268, yalnız 15'i 3/4); "%99,7" orta nokta payı koda yorum olarak
yazılmış, sayılmamıştı; örtüşme işaretinin "1 saatlik 13 serinin 9'unda %100"
cümlesi dört yerde (sayfa · Pine · Python · bu dosya) aynı yanlış kapsamı
taşıyordu — seriler 1 sa/4 sa/günlük, %100 olan 7, %99 üstü 9, biri %0. Bir
cümle dört yere KOPYALANDIĞINDA dört yerde birden yanlıştır. Üçüncüsü
KAPININ KENDİ KAPSAMI: ⑩ maddesinin "dar bant" hâli KONUMU da geçmiyordu, yani
yükseklik şartını hiç sınamıyordu; üç şart (yükseklik · HO süzgeci · yön
süzgeci) artık öbürleri geçerken TEK BAŞINA bağlanıyor ve üç arıza
enjeksiyonunun üçü de kendi maddesinde düşüyor; SIĞMA tek başına
SINANAMAZ (konum ve yükseklik geçerken cebirsel olarak sağlanır) ve öyle
yazıldı. Yapım dili de iki yerde figürün İÇİNDEYDİ ("eski sayacın
yanılgısı") — 19. ölçüt onu ENGEL saymıyor, çünkü "eski" tek başına kalıp
değil; okurun bilmediği bir "eski"yi anlatmak yine yapım dilidir.

**Kurucu ilke — `barstate.islast` KAPANMIŞLIK DEĞİL, SON OLMA hâlidir; ve bir
ölçüm aracının GÖSTERDİĞİ karar anı ile ÖLÇTÜĞÜ karar anı aynı olmalıdır.**
16.09.2026'da kullanıcı sordu: "indikatörde hep kapanan bara göre düşünmemiz
gerekmez miydi? açık barda baktıkça çok repaint ediyor." Ölçüldü; haklıydı ve
kusur göründüğünden derindi. İki Pine dosyasında `barstate.isconfirmed` HİÇ
geçmiyordu — yalnız `barstate.islast` vardı ve o "grafikteki son bar" demek,
"kapanmış bar" demek DEĞİL. Sonuç: giriş seviyesi canlı barın yürüyen ucundan
(`girisBoga = high + tick`), dönüş barı ölçütü canlı kapanıştan kuruluyordu;
on iki etiket, iki üçgen, bar boyaması ve zemin hiçbir onay kapısı taşımıyordu.

KLASİK REPAINT ARANDI VE BULUNAMADI, bu da bir sonuç: `request.security`,
`lookahead`, negatif `offset` iki dosyada da YOK, yani kapanmış bir barın
çıktısı sonradan değişmiyor. Yani kusur "geçmişi yeniden boyamak" değil, iki
ayrı şey: canlı barda hüküm yalpalaması, ve YAYIMLANAN BACKTEST'LE SÖZLEŞME
AYRIŞMASI. İkincisi asıl olan: `brooks_backtest.py`nin kendi başlığı "sinyal
barı i KAPANMIŞ bardır, emir i+1'de dolar" diyor ve `Seri`nin docstring'i
"Kapanmış barlar" — yani ölçülen her sayı kapanmış bar kararıdır. İndikatör
ise paketi bar hâlâ AÇIKKEN basıyordu. Ekranda dalgalanan seviyeler,
tablodaki sayıların ölçtüğü seviyeler değildi.

EN PAHALI HÂLİ ÇİZİM KAPISINDAYDI ve tek satırdı: `if barstate.islast`
çizgileri her barda SİLİP yeniden kuruyordu. Sinyal barı kapandığı an — yani
emrin ilk kez konulabildiği an — bir sonraki barın ilk tick'i çizgileri
siliyordu. Emir seviyeleri, emrin geçerli olduğu TEK barda ekranda yoktu.

DÜZELTME VERİYİ DEĞİL ÇİZİM ANINI KAYDIRIR. İlk tasarım bütün kutuyu `[1]`
ile indekslemekti; yirmi beş değer, iki de seri STRING demekti ve bu dosya
hiç derlenmediği için her yeni Pine yapısı ölçülmemiş bir risk. Doğrusu çok
daha küçük çıktı: `cizimBari = bar_index >= last_bar_index - 1 and kapanmis`.
Kutu ve çizgiler son KAPANMIŞ barda kurulur, canlı barda hiçbir şey yeniden
yazılmaz, eskisi yerinde durur — ve silme kusuru da kendiliğinden kapanır.
Bir tasarım, dokunduğu satır sayısıyla da ölçülür.

ALARMLAR GİRDİDEN BAĞIMSIZ OLARAK KAPALI. Disiplin bir girdiyle kapatılabilir
(`yalnizKapali`, öntanımlı AÇIK) ama on üç alarmın on üçü her koşulda
`barstate.isconfirmed` ister: gönderilmiş bir alarm geri alınamaz. Kırılım
modu kalıbı barın ilk tick'inde YAPISAL olarak doğrudur ve gap eşiği bir
EŞİTLİK sınamasıdır; ikisi de tam olarak "canlı barda doğup kapanışta yok
olan" biçimdir. Bir girdinin neyi kapsamadığı, kapsadığı kadar yazılır.

KURAL YORUMA YAZILMIŞTI. Alarm bloğunun tam üstünde "Uyarılar — hepsi
KAPANMIŞ bar üzerinden" diye bir YORUM duruyordu ve altındaki on koşulun
hiçbirinde kapı yoktu; sayfa da aynı cümleyi okura GEREKÇE diye yazıyordu.
Bu dosyada adı konmuş kusur sınıfının bir eşi daha: kural yalnız yoruma
yazıldığında dayatılmaz. `pine_denetle`ye iki ölçüt kondu — ⑨ her
`alertcondition` kapanış kapısı taşımalı, ⑩ disiplini İLAN EDEN dosyada bar
başına çizen her çağrı (`label.new` · `plotshape` · `barcolor` · `bgcolor`)
o kapıdan geçmeli. Kapı adları elle listelenmedi, SÖZLEŞMEDEN türetildi:
`kapanmis` ve ondan türeyen her ad (`cizimBari`) kapı sayılır, çünkü elle
tutulan bir ad listesi yeni bir sarmalayıcı eklendiği gün yanlış alarm
üretirdi. Altı arıza enjeksiyonunun altısı da yakalandı.

VE KAPIYI KOYAN YAMA, KAPATTIĞI KUSURU KENDİ ELİYLE ÜRETTİ. On alarma
`barstate.isconfirmed and ` öneki MEKANİK olarak eklendi; üçünün koşulu
`A or B` biçimindeydi ve `and` `or`'dan SIKI bağladığı için sonuç
`(isconfirmed and A) or B` oldu — ayı tarafı kapının DIŞINDA kaldı. Ölçütün
ilk hâli bunu GEÇİRDİ, çünkü satırda `barstate.isconfirmed` gerçekten
geçiyordu: ölçüt varlığı soruyordu, KAPSAMI değil. Kusur kodun kendi gözden
geçirmesinde çıktı ve iki yere birden yazıldı — Pine'da parantez, ölçütte
üst düzey `or` araması (`_ilk_arguman`, parantez içi üst düzey sayılmaz).
Bir kapı, kendi yanlış GEÇİŞİNE karşı da sınanmalıdır; "ölçüt düşmedi" ile
"arıza yok" bir kez daha birbirine tıpatıp benzedi.

KAPININ KENDİ KAPSAMI DA KUSURLUYDU: `yayin.yml` yalnız iki sınav koşuyordu,
yani Pine'ın statik denetimi ve replikasyonun kendini sınaması yayına giden
yolda HİÇ sorulmuyordu — `.pine` dosyaları public depoya hiçbir kapıdan
geçmeden kopyalanıyordu. Ölçü vardı, tüketicisi yoktu; adım eklendi.

AYNI TUR CANLI BARDAN BAĞIMSIZ İKİ AYRIŞMA DA BULDU. (1) Ortalama kesişmesi:
Pine önceki kapanışı BUGÜNKÜ ema ile kıyaslıyordu (`close[1] <= ema`),
replikasyon önceki ema ile — ortalama yürürken Pine sahte kesişme üretiyor ve
③ ölçüsü, dolayısıyla rejim hükmü ayrışıyordu. Bar kapandıktan sonra da
duruyordu, yani eşik paritesi kapısının göremediği bir ayrışma: o kapı
SABİTLERİ karşılaştırır, TANIMLARI değil. (2) Isınma: `hazir` kapısı
`not goreli or …` diye yazıldığı için ders kipinde bar 0'dan beri KOŞULSUZ
açıktı; Pine hüküm basarken replikasyon bar 88'e kadar `None` dönüyordu.
Bir de zemin ile kutu iki ayrı sınır kullanıyordu (zemin 3 işarette de
boyuyor, kutu "ara" diyor); zemin hükmün sınırına çekildi.

ÇÜRÜTÜLEN BİR BULGU KAYDA DEĞER, çünkü çürütmesi asıl kusuru buldu. "Isınma
kapısı beş ölçüden yalnız BİRİNE bakıyor ve seçtiği ölçü EMA'ya bağlı olmayan
TEK ölçü" diye bir bulgu geldi; ölçüldü ve cebirsel olarak TERS çıktı — EMA'ya
bağlı olan tek ölçü ③'tür, ve beş ölçünün beşi aynı barda non-na olduğu için
birine bakmak beşine bakmakla ÖZDEŞ. Ama aynı çürütme, aranan boşluğun
gerçekte nerede olduğunu gösterdi: mutlak kipteki koşulsuz `true`. İkna edici
bir teşhis sınanmamış bir teşhistir; sınanınca yerini daha iyisine bırakır.

BİR DOĞRULAMA TURU, ÖLÇTÜĞÜ AĞAÇ DEĞİŞİRKEN KOŞTURULAMAZ. Ölçüm iş akışı
2 saat 18 dakika sürdü (86 ajan); düzeltmeler o sürenin ortasında dosyalara
indi. Sonuç: 80 doğrulamanın 49'u "ÇÜRÜTÜLDÜ" dedi ve gerekçelerinde
"kaynağın bugünkü hâlinde birebir TERSİ", "KODDA ZATEN YAPILMIŞ" yazıyordu.
Yani o 49'un çoğu bulguyu çürütmüyor, DÜZELTİLMİŞ OLDUĞUNU doğruluyor —
ikisi bir rapor tablosunda birbirine tıpatıp benzer ve ayıran tek şey
okuyucunun dosyayı NE ZAMAN açtığıdır. Kural: uzun bir doğrulama turu
koşarken kaynak DONDURULUR (ya da doğrulayıcı bir kopyaya/commit'e
bağlanır); aksi hâlde tur, kendi düzeltmesini ölçer. Bu oturumda hüküm
ajanların sayımından değil, kendi bağımsız okumamdan kuruldu; yoksa
düzeltilmiş kusurlar "yanlış bulgu" diye kayda geçecekti.

AÇIK KALAN, ÖLÇÜLDÜ VE KARAR İSTİYOR — BERABERLİK. Bir bar aynı anda geçerli
bir boğa ve geçerli bir ayı dönüş barıysa ve kaliteleri EŞİTSE, Pine boğa
paketini basıyor (`kaliteBoga >= kaliteAyi`), backtest ise işlem AÇMIYOR
(`if len(aday) == 2 and aday[0]["kalite"] == aday[1]["kalite"]: return None,
True`). Ölçüldü: 1 sa/4 sa/günlük sette 7.973 emirde 171 kez (%2,1),
5 dakikalık sette 225.795 emirde 5.893 kez (%2,6); tamamı yön ve always-in
süzgeci KAPALI satırlarda toplanıyor, çünkü süzgeç açıkken iki aday aynı
anda uygun olamaz. Ders bu hâl için bir şey söylemiyor: backtest'in tercihi
(işlem yok) tutucu, Pine'ınki (boğa) keyfî. Hangisinin doğru olduğu ÖLÇÜM
değil EDİTORYAL bir karardır ve kullanıcıya sorulmadan kapatılmadı —
kapatılırsa ya yayımlanmış backtest sayıları ya indikatörün davranışı
değişir.

AÇIK KALAN, adıyla: Pine hiç DERLENMEDİ (sekiz statik ölçüt, derleyici yok);
yfinance üretim tazeleme işinde kurulu değil, yalnız keşifte; 5 dk örneklemi
tek bir yaz dönemi ve 59 gün; 1 sa+ göreli satırlarda N 16–23; bant kenarı ve
ikinci giriş 1 sa+ setinde N<10 (ölçülemedi, tabloda gri); tick veriden
tahmin ediliyor (`tick_tahmini`), TradingView'in `syminfo.mintick`i değil;
spread ve kayma sabit pip maliyetinin ötesinde modellenmedi.

**Kurucu ilke — BİR KURAL GENELLEŞTİRİLDİĞİNDE TÜKETİCİLERİ DE GENELLEŞİR; ve
`"x" in O` bir ÖLÇÜM kapısı değildir.** 15.09.2026'dan 16.09'a veri tazeleme
yedi koşu üst üste kırmızı bitti (#194–#200, son yeşil #193) ve DİBS panosu iki
gün 14.09'da dondu. Kök 09.09'da atılmıştı: o gün `anlik()` genelleştirildi —
sayfanın adıyla çağırdığı anahtar ölçülemese de yazılır (OLCULEMEDI), çünkü
ATLANAN anahtar yayın kapısında ENGEL olur. Kural doğruydu; uygulanmadığı yer
onu OKUYAN koddu. O günden sonra `"x" in O` tanımı gereği HEP doğrudur ve altı
türetilmiş anahtarın kapısı sessizce açık kaldı. 15.09'da dokuz yıl düğümünün
son dolu günü (07.09) yedi günlük toleransı aşınca `abs("—")` hattın DÖRDÜNCÜ
adımını düşürdü; duman ve ilk üç adım geçtiği için veri çekildi, ölçüldü,
çizildi — ve siteye hiç kopyalanmadı.

Arızanın görüntüsü yine sağlığın görüntüsüne benziyordu: commit adımı
`if: always()` taşıdığı için her koşuda 73 dosya yayına gitti, site ayakta
kaldı, öbür yirmi hat tazelendi; yalnız bir pano dondu. Kırmızı biten iş akışı
e-posta gönderdi ve kullanıcı onu gördü — yani bu kez alarm çalıştı, ölçüyü
okuyan yoktu.

Düzeltme üç katmanlı ve üçü de "yer tutucu" sözleşmesinin eksik yarısını
kapatıyor. (1) Kapı VARLIĞI değil DEĞERİ sorar (`olculdu`). (2) `koy()`
yer tutucu GİRDİSİNİ yer tutucu ÇIKTISINA çevirir — ölçülemeyen bir bacaktan
türeyen anahtarın doğru cevabı "—"dir, çökme değil; ama YALNIZ yer tutucu
böyle geçer, başka bir dizge ADIYLA patlar, sessizce boşa çevrilmez.
(3) Ölçüm BİÇİMİNDEKİ cümle sayısız kurulmaz: "9 yıllıktan — puan yüksek" ya da
"Fisher ileri reel faiz %—, geriye dönük %—; makas — puan" bir ölçüm değil,
ölçüm kılığında bir boşluktur; sayı yoksa cümle sebebini yazar.

TARAMA İKİNCİ BİR HÂLİ BULDU ve o hâl statik kapının GÖREMEYECEĞİ biçimdeydi:
manşet taşıma anahtarı bir DEĞİŞKENDEN okunuyor (`O[manset_kol]`), yani ad
kaynakta hiç geçmiyor. Kapısız hâli iki yönde birden kusurluydu — `koy()`'u
düşürür ya da cümleye `O.get('carry_manset', 0)` üzerinden SAHTE BİR SIFIR
yazardı ("fonlama maliyetinin 0,00 puan üstünde"), ölçülemeyen bir şeyi
ölçülmüş göstermenin en sessiz biçimi.

Dört kapı `duman.py`ye kondu ve kapsamı SÖZLEŞMEDEN türüyor: `anlik()`in
yazdığı anahtarlar kaynaktan çıkarılıyor, elle tutulan bir listeden değil.
Aritmetik kapısının ilk yazımı GİRİNTİYLE kuruluydu ve kuralın KENDİ ilan
ettiği iki hâlini göremiyordu — koşulu iki satıra yayılan `if` ile
`if not olculdu(…): … else:` tersi; ikisinde de DOĞRU kodu kusur sayıyordu.
Yayının önünde duran bir ölçütün yanlış alarmı arızanın kendisidir; ölçüt
AĞACA çevrildi (`ast`), dal dal sorar. Dört arıza enjeksiyonunun dördü de
yakalandı — ama biri dürüstçe kayda geçsin: aritmetik okumayı kapının dışına
çıkarmak O GÜN çökme üretmedi (iki bacak da ölçülmüştü), YATKIN bir kusur
ekti. Statik kapının işi tam olarak budur ve "ölçüt düştü" ile "bugün çöktü"
aynı şey değildir.

EN KÖTÜ HÂL FİKSTÜRÜ DE ANCAK EZDİĞİ TOLERANS KADAR GENİŞ: bütün anlık
anahtarları ölçülemez saymak (`ANLIK_TOLERANS_GUN = -1`) manşet taşıma dalına
HİÇ uğramıyor, çünkü AOFM bacağı kendi 400 günlük toleransını taşıyor ve genel
çıpayı dinlemiyor. O dal ancak kendi toleransı da ezilerek ölçülebildi. Bir
fikstür "hepsini boş yaptım" dediğinde, kendi istisnalarını da ezip ezmediği
sorulur.

Aynı sınıfın bir eşi TUFEX'te bulundu ve düzeltildi, üstelik kapının KENDİ
içinde: hattın duman sınaması `float(o["pka_12a"])` diyordu ve ifade `sina`nın
ARGÜMANINDA durduğu için istisna ölçütün içinde kalmıyor, `duman.py`yi
düşürüyordu — duman adımlardan ÖNCE koştuğu için hat komple atlanır ve panosu
donardı. Hat o anahtarı ölçemediğinde "—" yazıyor (sözleşmenin kendisi), yani
kapı hattın MEŞRU çıktısını çökmeye çeviriyordu. Arıza enjeksiyonuyla ölçüldü
(`ValueError: could not convert string to float: '—'`). Boş bacakta sorulacak
soru KIYAS değil TUTARLILIKTIR: aylık kaynak o ayı DOLU verirken günlük bacak
boşsa kusur vardır, ikisi birlikte boşsa yoktur. İlk enjeksiyon dosyanın
`ozet.json`unu düzenleyerek yapıldı ve HİÇBİR ŞEY üretmedi — sınama özeti
diskten değil hattan yeniden hesaplıyor; arıza ancak ÜRETİCİYE enjekte
edilince göründü. Bir enjeksiyonun yanlış yere yapılması, ölçütün kör
olduğuyla birebir aynı görünür.

ÜÇÜNCÜ EŞ BÜYÜME'DE ÇIKTI ve YER TUTUCUSU "—" DEĞİL `None`: ölçüm katmanı
NaN'ı None'a çeviriyor (doğru — ölçülemeyen sayı uydurulmaz), ama etiketi yazan
f-string None'ı biçimleyemiyor ve ÇİZİM ADIMI ölüyor; hattın kalan adımları
atlanır, panosu donar. Aynı sınıf, başka sentinel, aynı sonuç. Kapsam
SEZİLMEDİ, ÖLÇÜLDÜ: dört figürün her biri tek tek bozuk bir bacakla koşturuldu
ve BEŞ çağrı yeri düştü (son çeyreğin yıllık oranı · bir bileşenin katkısı ·
stok+zincirleme artığı · ayrıştırma tabanı · bir dayanıklılık kalemi), ikisi
düşmedi. "Hepsini boş yap" sledgehammer'ı üç figürü birden düşürüyordu ama
hangi çağrı yerinin kusurlu olduğunu SÖYLEMİYORDU — bir ölçünün kaç şey
kırdığını saymak, hangilerinin kırıldığını söylemez.

Etiket yazımı da sözleşmeye çekildi (ondalık virgül, eksi U+2212): kütüphanenin
varsayılanı bizim sözleşmemiz değil ve hat negatif bir katkıyı ASCII tire ile
basıyordu. Duman maddesi altı hâli AYRI AYRI soruyor — tek maddeyle sorulsaydı
ilk düşme kalanları maskelerdi. Altıdan biri (sektör büyümesi) enjeksiyonda
DÜŞMÜYOR ve düşmemesi doğru: o değer hiçbir yerde biçimlenmiyor. Madde
listede KAPSAM olarak duruyor ve bunun bir güvence olmadığı ADIYLA yazıldı —
yarın oraya bir etiket eklendiğinde kendiliğinden kapıya döner.

Bir de kapının KENDİ kusuru tekrar etti: ilk yazımda `sina(..., grafik._sayi(None, 1) == "—")`
denmişti ve enjeksiyon altında ifade `sina`nın ARGÜMANINDA patlayıp duman.py'yi
düşürdü, yani ekrandaki teşhis sınamanın kendi kusuru gibi göründü. Aynı kusur
aynı gün TÜFEX'te ölçülmüştü; kural bir yerde yazılıp öbür yerde
uygulanmamıştı — bu dosyanın en sık tekrar eden cümlesi.

TARAMANIN BIRAKTIĞI İKİ İZ DE ÖLÇÜLDÜ, İKİSİ DE BUGÜN CANLI DEĞİL — ve
ölçülmeselerdi ikisi de düzeltilecekti.

(1) Enflasyon Şekil'inde kapısız bir `f"{v:.3f}"` etiketi. Aynı kalıp, ama
ÜRETİCİ oraya None yazmıyor: `mae` `round(float(...), 3)` ile kuruluyor, en
kötü hâli `nan` — bir FLOAT, yani biçimlenir, çökme üretmez. Kusur sınıfı
farklı: çökme değil, okura ölçüm gibi görünen "nan". Yayılma tek tek çağrı
yeri okunarak değil ÇIKTIDAN ölçüldü — sitedeki 177 gömülü figürün etiket ve
açıklama metinleri tarandı, `nan`·`None`·`undefined` sızıntısı SIFIR. Bir
biçim kusurunun yayılmasını sormanın en ucuz yolu, okurun gördüğü dosyaya
bakmaktır.

(2) Büyüme ölçüm katmanındaki ASİMETRİ: dayanıklılık döngüsü ölçülemeyen
bacak için anahtarı yer tutucuyla yazıyor, on iki satır yukarıdaki katkı
döngüsü `continue` ile HİÇ yazmıyor. İkisi de savunulabilir, ama hangisinin
sözleşme olduğu yazılı değil ve 08.09 kuralı ("sayfanın çağırdığı anahtar
her koşuda yazılır") yer tutucudan yana — yani uyumsuz olan KATKI döngüsü.
Bedeli ölçüldü ve BUGÜN SIFIR: Büyüme'nin PANOSU YOK (`site/src/content/
projeler/` altında dosyası yok), tek tüketicisi 08.09 kararıyla DONDURULMUŞ
bir analiz yazısı — orada eksik anahtar yayını durdurmaz, bilgi satırıdır —
ve bültenin izlemi yalnız `buyume_yillik` ile `buyume_ceyreklik`i sorar,
ikisi de o döngünün dışında. AÇIK KALAN ve kullanıcıya SORULACAK: hangi
davranışın sözleşme olduğu bir KARARDIR, mekanik bir düzeltme değil; bir
gün Büyüme'ye pano açılırsa bu iz sessiz bir yayın engeline döner.

**Kurucu ilke — BİR KAPI ANCAK KOŞTURULDUĞU GÜNDE ÖLÇÜLMÜŞTÜR; ve ölçümün
kendisi de kör olabilir.** 17.09.2026 sabahı yayın iş akışı dört kez düştü ve
kusur yayın kapısının İLK basamağındaydı: `duman_sinav.py`nin 18b regresyon
maddesi girdiyi DONMUŞ (`acik("18.09.2026")`), ölçüyü CANLI (yarın sınırı)
tutuyordu. Madde 04.09'da yazıldığında 18.09 iki hafta ileriydi; 17.09 sabahı
YARIN oldu, sınır onu meşru saydı, engel listesi boşaldı ve madde düştü. Kusur
takvim ilerlediği için kendiliğinden doğdu ve kendiliğinden GEÇMEYECEKTİ.
Sınıf bu dosyada iki kez adıyla yazılı (YPMevduat 10.09 · ihale ölçütü 14.09);
kural vardı, bu maddeye uygulanmamıştı.

ASIL DERS DÜZELTMEDE DEĞİL, ARAMADA. "Başka nerede var" sorusu kaynağı okuyarak
cevaplanamaz: bu kusurların hepsi BUGÜN yeşil geçer. Kapılar İLERİ TARİHLERDE
koşturuldu (`freezegun` + pandas saatinin yamalanması; pandas kendi C saatini
okuduğu için yalnız freezegun dört hat kapısını kör bırakıyordu) ve harness
önce GERÇEK arızaya karşı doğrulandı — düzeltme öncesi sürüm 16.09'da geçiyor,
17.09'da düşüyor. Doğrulanmamış bir zaman yolculuğu, hiç koşmamakla aynı.

TARAMA BİR BOMBA BULDU: OVP hattı 15.10'a kadar geçiyor, 16.10'dan itibaren
düşüyor. Fikstürün TÜFE serisi `2026-08-01`'de donmuş, ölçü canlı; o gün
gerçekleşen bacak 45 günlük toleransı aşıyor ve bayatlık cümlesi üç sayılı bir
yan cümle kazanıyor ("gerçekleşen TÜFE bacağı 46 gün geride (tolerans 45 gün);
3 tazelik uyarısı düştü"). Cümle DOĞRU; kapı onu kusur sayıyor — "hattın kendi
kapısı, kuralın meşru çıktısını kusur sayamaz"ın bir eşi daha. Duman adımlardan
önce koştuğu için bedeli hattın komple atlanması, panonun donması ve veri
tazelemenin her koşuda kırmızı bitmesiydi.

YANLIŞ DÜZELTME ÖNCE DENENDİ VE ÖLÇÜM REDDETTİ: fikstürü duvar saatine bağlamak
bombayı söndürüyor ama YERİNE İKİ YENİSİNİ koyuyor (31.12'de konvansiyon
ayrışma maddesi düşüyor, 2027'de koşu çöküyor). Fikstürün çoğu bilerek donmuş —
kapalı çözümü bilinen sentetik patikalar, elle tutulan program tabloları. Kusur
"fikstür donmuş" değil, DONMUŞ GİRDİYİ CANLI SAATLE ÖLÇEN ALAN. Doğru düzeltme
o alanı ölçünün dışına almak: `bayat_cumlesi`nin sayı sayısı VERİDEN gelir,
yazardan değil — bir bacağı ADIYLA, YAŞIYLA ve TOLERANSIYLA anmak ölçünün
kendisidir ve tek sayıyla kurulamaz. Kardeşi `uyari_metni` aynı gerekçeyle
baştan muaftı.

MUAFİYET VARSAYILARAK DEĞİL ÖLÇÜLEREK KONDU: canlı sitede makroihtiyati panosu
bu cümleyi ZATEN 2 cümle / 3 sayı olarak basıyor ve okunuşu düzgün. Kapı onu
göremiyordu, çünkü her hat yalnız KENDİ fikstürünü ölçüyor — tavanın tutulamaz
olduğu üretimde çoktan görünmüştü, hiçbir ölçüt oraya bakmıyordu.

VE ÖLÇÜMÜN KENDİ KÖRLÜĞÜ ÜÇ KEZ TEKRARLADI, üçü de "sahte temiz" üretti.
(1) İlk tarama betiği `"Aktarılacak Projeler"` içindeki BOŞLUK yüzünden hiçbir
dizine giremedi ve 19 kapı için ✓ bastı. (2) `datetime.date`i Python alt
sınıfıyla değiştiren shim, pandas içe aktarılınca SEGFAULT veriyor; o yüzden
pandas'a dokunan kapılar hiç ölçülemedi ve çıkış 139 "sabit" sayıldı.
(3) `runpy.run_path` betiğin DİZİNİNİ `sys.path`e koymuyor; dokuz kapı
`ModuleNotFoundError` ile — HER tarihte aynı şekilde — düştü ve tam bu yüzden
"sabit" göründü. Üçünde de ölçülmemiş bir kapsam, ölçülmüş ve temiz çıkmışla
BİREBİR AYNI göründü. Bir tarama yazıldığında sorulacak ilk soru bulguları
değil, taramanın gerçekten O DOSYAYA dokunup dokunmadığıdır.

AÇIK KALAN ve KULLANICIYA SORULACAK: bu bombayı yalnız ileri tarihli koşu
buldu ve depoda bunu yapan hiçbir kapı yok. `duman_sinav.py` normalde 77 ms,
ileri tarihle 465 ms — yayın kapısına eklemek bedava; ama bomba HAT kapısında
çıktı ve 22 hattın tam taraması ~30 dk sürüyor, yani her koşuya konamaz.
Haftalık zamanlanmış bir tarama bu bombayı 29 gün önceden yakalardı; yeni bir
iş akışı ve yeni bir bağımlılık (`freezegun`) demek, o yüzden tek taraflı
kurulmadı.

YPMEVDUAT "BOMBASI" ÇÜRÜTÜLDÜ ve çürütmesi harness'ın kör noktasını buldu.
Tarama YPMevduat'ı YARIN patlayacak diye işaretledi; düşen madde önbellek
tazeliğiydi ("eski taze False · yeni taze False"). Ölçüldü: `tazelik.taze`
dosyanın MTIME'ını `datetime.now()` ile kıyaslıyor; freezegun saati ileri
alıyor ama dosyayı yazan OS saati GERÇEK. Yani ŞİMDİ yazılan bir fikstür
dosyası +1 günlük sahte saatte 16 saatlik görünüyor ve 12 saatlik TTL'i
aşıyor. Kusur depoda değil ÖLÇÜMDE. Kör nokta iki yönlü ve tehlikeli yarısı
ikincisi: o gürültünün arkasında GERÇEK bir bomba da saklanabilirdi. Koşucu
dosya saatini de kaydıracak biçimde onarıldı (`os.stat` sarmalanıp mtime aynı
farkla ötelenir), önce bilinen gerçek arızaya karşı yeniden doğrulandı
(16.09 geçer · 17.09 düşer), sonra YPMevduat beş ileri tarihte 341/0 çıktı —
arkasında bir şey yokmuş. İkna edici bir teşhis sınanmamış bir teşhistir;
burada teşhis ölçümün KENDİSİNİ suçlayarak doğrulandı.

Üç kapının "bugün de düşüyor" görüntüsü de ölçüm kusuruydu: Enflasyon yerelde
`ortak/` PYTHONPATH'te olmadığı için hiç koşamıyor (üretimde kurulu),
Makroihtiyati (41/0) ve bülten (72/0) doğrudan koşturulunca geçiyor. Bir kapı
"düştü" dediğinde önce KOŞUP koşmadığı sorulur.

**Kurucu ilke — BİR KAPIYI YALNIZ İLERİ BİR GÜNDE KOŞTURARAK ÖLÇEBİLİRSİN; ve
ÖLÇÜM ARACININ KENDİSİ DE ÖLÇÜLMEK ZORUNDADIR.** 17.09.2026'nın iki arızası
(yayın kapısının ilk basamağı · OVP'nin 16.10'a kurulu bombası) aynı sınıftan
ve ikisi de KAYNAK OKUNARAK BULUNAMAZ: hepsi BUGÜN yeşil geçer. Bu yüzden
kalıcı çözüm bir ölçüt değil bir ARAÇ oldu.

ARAÇ ÜÇ PARÇA. `ortak/zaman_yolculugu.py` duvar saatini kaydırır ve ÜÇ SAATİ
birden kaydırmak zorundadır — üçü de ölçülerek öğrenildi: (1) SIRA — freezegun
pandas'tan ÖNCE başlatılırsa yorumlayıcı SEGFAULT verir (datetime'ı Python alt
sınıfıyla değiştiriyor, pandas'ın C uzantısı kabul etmiyor); (2) PANDAS'IN
KENDİ SAATİ — `pd.Timestamp.today()` C tarafından okunur, freezegun ona
dokunmaz ve dört hat kapısı saatini oradan alır; (3) DOSYA SAATİ — `tazelik.taze`
mtime'a bakar, saati ileri alıp mtime'ı bırakmak ŞİMDİ yazılan fikstür
dosyasını bayat gösterir. Modül `ortak/sitecustomize.py`ye bağlandı (yeni
mekanizma YOK: guncelle.py zaten her hat alt sürecinde ortak/'ı PYTHONPATH'e
koyuyor) ve `TTO_SAHTE_GUN` yoksa tek satır çalışmaz.

`site/tools/zaman_sinav.py` kapıları ileri tarihlerde koşturur. ORTAM
UYDURULMAZ, `guncelle.py`DEN TÜRETİLİR — alt süreç, hattın kendi klasörü,
üretim PYTHONPATH'i; kendi `runpy` kurulumumuz hatların modüllerini gölgeleyip
üç kapıda sahte bulgu üretmişti. `.github/workflows/zaman.yml` haftalık koşar,
ONARMAZ HABER VERİR (nöbetçiyle aynı rol) ve ayrı bir concurrency grubunda —
tazelemenin arkasında kuyrukta beklemesin.

VE ARAÇ ÖNCE KENDİNİ SINAR, ayrı bir adım olarak. Sebep ölçüldü: bu tarama
yazılırken ÖLÇÜMÜN KENDİSİ BEŞ KEZ YANILDI ve beşi de gerçek bir hükümle
tıpatıp aynı göründü. (a) Betik `"Aktarılacak Projeler"` içindeki BOŞLUK
yüzünden hiçbir dizine giremedi, 19 kapı için ✓ bastı. (b) Elle yazılan
datetime shim'i pandas'ta segfault verdi, çıkış 139 "sabit" sayıldı.
(c) `runpy.run_path` betiğin dizinini `sys.path`e koymadı, dokuz kapı
`ModuleNotFoundError` ile HER tarihte aynı düşüp "sabit" göründü. (d) Dosya
mtime'ı kaydırılmayınca YPMevduat SAHTE BOMBA verdi. (e) `ortak/`u
PYTHONPATH'e elle eklemek üç hattın kendi modüllerini gölgeledi. Ayrıca
`os.stat` sarmalayıcısı NANOSANİYE alanlarını düşürünce `shutil.copystat`
patladı ve araç, ölçmek istediği kapıyı KENDİ ELİYLE düşürüp her tarihte
"bomba" dedi. Bir tarama yazıldığında sorulacak ilk soru bulguları değil,
taramanın gerçekten O DOSYAYA DOKUNUP DOKUNMADIĞIDIR — bu yüzden
`kendini_sina()` sentetik bir "donmuş girdi, canlı ölçü" bombası kurar ve
yakalayamazsa araç bütün "temiz" hükümlerini GEÇERSİZ ilan edip düşer.

Yan bulgu, aynı sınıfın bir eşi: Enflasyon `metrik.py` çıplak `import bicim`
yapıyordu ve hattın duman sınaması KENDİ KLASÖRÜNDEN hiç koşturulamıyordu
(üretimde PYTHONPATH'te olduğu için görünmüyordu). Elle koşturulamayan bir
kapı, kimsenin koşturmadığı kapıdır; deponun kendi kalıbı (YPMevduat'ın
`_bicim` yardımcısı) uygulandı.

VE ARAÇ İLK KOŞUSUNDA KENDİ YANLIŞ ALARMINI ÜRETTİ — altıncı ölçüm kusuru,
en öğreticisi. `bulten/duman.py` "yarın patlıyor" diye raporlandı; kapı sahte
saatle BUGÜN de aynı iki maddeyle düşüyordu, yani tarih bombası olamazdı.
Sebep: freezegun varsayılanda saati DONDURUR, ilerletmez (`time.sleep(0.05)`
sonrası geçen süre 0,0000 sn) ve düşen iki madde SÜRE ÖLÇÜYOR — devre kesici
ile "asılan adımı duvar saatiyle kes". Biz saati KAYDIRMAK istiyoruz,
DURDURMAK değil; `tick=True` kondu. Kural aracın kendisine de uygulandı
("yayının önünde duran denetimin yanlış alarmı arızanın kendisidir"): haftalık
bir alarmın yanlış pozitifi kaçırdığı bombadan ucuz değildir — iki kez boş
öterse üçüncüde kimse bakmaz. `kendini_sina()` artık saatin gerçekten
İŞLEDİĞİNİ de sınıyor ve arıza enjeksiyonuyla doğrulandı: tick geri
kaldırılınca araç çıkış 2 ile düşüp bütün "temiz" hükümlerini geçersiz ilan
ediyor.

**Kurucu ilke — KIRPILMIŞ BİR METNİN UZUNLUĞU, KISALTMA KARARININ ÖLÇÜSÜ
OLAMAZ; ve İLAN EDİLEN FAİZ, GERÇEKLEŞEN FAİZ DEĞİLDİR.** 17.09.2026'da PPK
toplantı özeti (2026-42) üzerine analiz yazıldı ve iki şey birden çıktı.

Birincisi ÖLÇÜNÜN kendisiyle ilgili ve bu dosyada adı konmuş bir sınıfın eşi.
`tweet/analiz.analiz_zinciri` tavanı aşan bir özette "tablo satırları SONDAN
düşer, rakam şeridi ve tez KALIR" diye yazılmış bir kısaltma taşıyordu. Kural
YORUMDA doğruydu, KODDA hiç çalışmıyordu: döngünün ölçüsü `uret._kapat`ın
çıktısıydı ve o fonksiyon gövdeyi tavana KIRPAR — yani çıktısı tanımı gereği
tavanı AŞAMAZ, döngünün koşulu hiçbir zaman sağlanmaz ve kod ÖLÜDÜR. Kırpma
sondan yediği için tam da korunmak istenen blok gidiyordu. Ölçüldü: ham gövde
4.132 karakter, tavan 3.800, rakam şeridi çıktıda YOK, tez de son üç cümlesi
kesilmiş hâlde. Gönderi kusursuz görünüyor, yalnız en alıntılanabilir bloğu
yok ve hiçbir kapı bunu sormuyordu — arızanın görüntüsü ile sağlığın görüntüsü
bir kez daha aynı. Ölçü KIRPILMAMIŞ gövdeden alınıyor (`_ham()`), pay tek yerde
hesaplanıyor (`kapasite`), ve duman sınamasına tavanı AŞAN sentetik bir özet
kondu: şerit kalmalı, ilk satır durmalı, son satır düşmeli. Arıza enjeksiyonuyla
doğrulandı (ölçü geri kırpılmış metne bağlanınca madde DÜŞÜYOR). Bir kısaltma
kuralı, kısaltmayı YAPAN fonksiyonun çıktısıyla ölçülemez.

İkincisi yazının kendi bulgusu ve kayda değer. Politika faizi 22.01.2026'dan
beri %37,0'de sabit; aynı yıl içinde piyasanın lirayı gecelik fonladığı oran
%36,67 ile %40,00 arasında, 3,33 puanlık bir bantta dolaştı. Rejim EŞİKSİZ
tanımlandı — her gün TLREF'in EN YAKIN durduğu İLAN EDİLMİŞ orana (politika ·
koridor üstü · koridor altı) göre sınıflandı, yani eşik seçilmedi, çıpalar
verili — ve 2026 tek bir kısa blok bile çıkmadan üç bloğa ayrıldı: politika
faizinde 41 gün, koridor tavanında 117 gün, yine politika faizinde 17 gün. İki
geçiş, yılın en büyük iki tek seanslık hareketi (+297 bp 02.03, −292 bp 24.08);
üçüncü en büyük hareket yalnız −88 bp, yani ayrım ölçünün kendisinden geliyor.
Ölçü `bulten/fonlama_rejim.py`de duruyor ve tüketicisi yazı katmanıdır. Ders:
bir para politikası duruşunun oynak bileşeni İLAN EDİLEN faiz olmak zorunda
değil; "faiz sabit" cümlesi, fonlamanın fiyatı sorulmadan kurulamaz.

Yan not, aynı turda ölçüldü ve KAPATILMADI: DİBS hattı anket anahtarlarının
okur etiketini (`<anahtar>_ay_ad`) ham aylık serinin SON ayından yazıyor, oysa
değerin kendisi `PKA_YAYIM_GUN = 20` varsayımı yüzünden bir ay geriden geliyor.
Sonuç: pano %23,69'u "Eylül 2026" diye etiketliyor, oysa o Ağustos anketidir ve
TCMB'nin kendi özet metni (2026-42 ¶24) bunu birebir doğruluyor. Kardeş hat
Tufex aynı sayıyı doğru etiketliyor (`pka_ay_ad` = "Ağustos 2026",
`pka_gecerli_baslangic` = 20.08.2026). Doğru düzeltmenin hangi tarafta olduğu
ÖLÇÜLEMEDİ: etiket mi bir ay ileri, yoksa varsayım mı bir kaç gün geç —
EVDS eylül satırını 16.09'da çoktan taşıyordu, yani anket 20'sinden ÖNCE
yayımlanmış görünüyor. Yayım gününün kendisi bu oturumdan ölçülemediği için
tek taraflı değiştirilmedi; ölçülmeden yapılan düzeltme, düzelttiğini sandığı
kusuru yer değiştirir.

**Kurucu ilke — YAYIMLANAN BİR SAYININ ARŞİVİ DEPODA DURUR; GERİYE ÖLÇEKLENMİŞ
BİR SERİDEN CRACK SPREAD HESAPLANMAZ; ve VADE DEVRİ GÜNÜ, AYNI SERİNİN İKİ
İNDİRMESİNİN AYRIŞTIĞI TEK GÜNDÜR.** 20.09.2026'da Hürmüz ve Rusya-Ukrayna
analizi yazıldı; yayın öncesi doğrulama turu yazının SEKİZ ayrı sayı ailesini
birden düzeltti ve dördü aynı sınıftan.

(1) ÜÇ YILLIK DAĞILIM YALNIZ KOŞU KAYDINDAYDI. Medyan, zirve, yüzdelik ve
uçlara mesafe bulut keşif koşusunun ekran çıktısından alınmıştı; depoda
karşılığı YOKTU, yani hiçbir kapı onları bir daha soramazdı ve yerel doğrulama
"kaynak bulunamadı" diyordu. Analizler canlı değer taşımaz (karar 08.09.2026),
yani sayıları MDX'e ELLE yazılır — bu, arşivin depoda durmasını tercih değil
ZORUNLULUK yapar. Üç parça kondu: `veri/defter.json` (keşif koşusunun tam
hassasiyetli arşivi — 754 günlük ham enerji serisi, 28 darboğazın yuvarlanmamış
ortalamaları, kapsam), `olcum.py` (sayıyı üreten TEK yer; figür de metin de
oradan), `dogrula.py` (yayımlanan metni ölçüme karşı sınayan kapı). Kapı
beklenen değerleri KENDİ İÇİNE yazmıyor, yayımlanan MDX tablolarını AYRIŞTIRIP
okuyor: iki liste bir gün sessizce ayrışır. 240 ölçüt, dört arıza
enjeksiyonunun dördü de yakalandı.

(2) CRACK SPREAD GERİYE ÖLÇEKLENMİŞ SERİDEN HESAPLANAMAZ. Bültenin serisi vade
devrini geriye ölçekleyerek arındırıyor ve bu bir getiri serisi için DOĞRU.
Ama ölçekleme üç bacağı FARKLI oranla çarpıyor — 18.09 devrinde HO 0,956 ·
CL 0,954 · RB 0,926 — ve 42×HO − CL aritmetiği o farkı spread'in kendisi kadar
büyütüyor. Ölçüldü: 02.02.2026 distilat crack düzeltilmiş seride 35,47, kote
edilmiş fiyatlarla 36,97; Brent 63,21 yerine 66,30. Yazının "14 Eylül'de Brent
100,75" cümlesi aynı paragraftaki "Brent 108 doları gördü" haberiyle
ÇELİŞİYORDU ve çelişkinin sebebi haber değil bizim serimizdi (gerçek kapanış
105,68). Bir crack, aynı gün gerçekten kote edilmiş üç fiyatın aritmetiğidir;
bir seviye cümlesi de kote edilmiş fiyattır. Yan bulgu: yazının üç yıllık
dağılımı HAM seriden, gün tablosu DÜZELTİLMİŞ seriden geliyordu — aynı
büyüklüğün iki ayrı bacağı iki ayrı sözleşmedeydi ve "1 yıllık zirve 112,94 ·
3 yıllık zirve 117,92" ikisi de AYNI günün (16.09) zirvesiydi.

(3) DEVİR GÜNÜ BİR YAYIN GÜNÜ DEĞİLDİR. Aynı serinin iki bağımsız indirmesi
250 örtüşen günün 249'unda dört ondalığa kadar BİREBİR aynı; ayrıştıkları tek
gün 18.09 — devir günü (Brent 99,29 ↔ 103,87, %4,6). Hangisinin "o günün ön
vadesi" olduğu bu oturumdan çözülemedi ve çözülmesi de gerekmedi: yazının veri
günü 17 Eylül'e çekildi, yani iki kaynağın birebir örtüştüğü son güne. Bir
sayının doğruluğu tek bir indirmeyle değil, iki bağımsız indirmenin
örtüşmesiyle de kurulabilir; örtüşmediği gün yayına girmez.

(4) BİR KONTROL GRUBUNUN TABANI MEVSİMİ DE KONTROL ETMELİDİR. Taban yedi yılın
tamamıydı (2019-01 → 2026-03), "şimdi" ise üç haftalık bir dilim — ve bu fark
mevsimi değişime yazıyordu. Ölçüldü: Bering Boğazı ham kıyasla +%328, aynı
TAKVİM penceresinin yıl yıl ortalamasıyla +%56,7 (yaz rotası). Savaş
bölgelerinde iki ölçü birbirine çok yakın (Hürmüz −%94,8 ↔ −%95,3), yani
oradaki düşüş mevsimden gelmiyor — ama bunu SÖYLEYEBİLMEK için mevsimin
ölçülmüş olması gerekiyordu. Kapsam da düzeldi: kaynak 28 darboğaz sayıyor,
yazı on ikisini ELLE saymıştı ve ikisinin adı kaynaktakiyle tutmuyordu
("Bosphorus"/"Bosporus", "Strait of Gibraltar"/"Gibraltar Strait") — İstanbul
Boğazı ile Cebelitarık sessizce DÜŞTÜ, kontrol grubu altı yerine beş
darboğazla ölçüldü ve yazı yine de "on kontrol darboğazı" diyordu. Kontrol
grubu artık ÇIKARMA ile kuruluyor (savaş rotasında olmayan her darboğaz: 22) ve
hüküm ortalamayla değil MEDYANLA veriliyor, çünkü tek bir mevsimsel uç
ortalamayı +%2,8'den +%17,7'ye taşıyor.

(5) ÖLÇÜT YAZILDI VE KAPIYA KONDU. `sayfa_sinavi.py` 26. ölçüt: "Aktarılacak
Projeler/*/dogrula.py" deseniyle bulunan her yazı doğrulayıcısı koşturulur,
düşerse yayın DURUR. Kapsam elle tutulan bir listeden değil desenden geliyor —
yeni bir yazı kendi doğrulayıcısını yazdığı gün kendiliğinden kapıya girer.
Ölçüt ağa çıkmaz, duvar saati okumaz (girdisi depodaki arşiv), saniyeler sürer
ve tarih bombası taşıyamaz.

İki yan bulgu kayda değer. Birincisi bu dosyanın en sık tekrar eden cümlesinin
bir eşi: ölçüt 26'nın ilk arıza enjeksiyonu HİÇBİR ŞEY üretmedi ve "ölçüt kör"
hükmü verilecekti — `sed` kalıbı tabloda KALIN yazılmış satıra uymamıştı, yani
arıza hiç enjekte edilmemişti. Enjeksiyon hedefi artık `assert` ile sınanıyor;
bir enjeksiyonun yanlış yere yapılması, ölçütün kör olduğuyla birebir aynı
görünür. İkincisi ağ tarafında: beş vadeli kodu PARALEL istemek yfinance'in
SQLite önbelleğini kilitliyor ("database is locked") ve düşen kod BOŞ SERİ
olarak dönüyor — bir bacağın sessizce kaybolması crack aritmetiğini eksik
bırakır; kodlar sırayla isteniyor ve boş dönen kod üç denemeden sonra ADIYLA
hata veriyor.

**KARAR (21.09.2026, kullanıcı) — İKİ PANELLİ "TTO · YAPI VE MOMENTUM": SMC +
HARMONİK + KULLANICI DİVERJANS TABLOSU; ARŞİV DEPOYA COMMIT EDİLİR; KENAR YOK.**
Kullanıcı Brooks indikatörünü yetersiz buldu ve kendi "TTO All-in-1" Pine'ını
verdi (RTF'te iki kez yapıştırılmış, ikinci kopya tam; `Aktarılacak
Projeler/Indikator/gelen/`): SMC ve harmonik dersleriyle harmanlanmış, alt ve
üst panelli, olasılık yazan, backtest'li bir indikatör istedi; evren yedi FX
majörü, EUR/GBP, EUR/CHF, DXY, XU100, SPX, NDX, WTI, XAU (USD/TRY YOK); ana
dilim 5 dk, bağlam 1 sa/4 sa/günlük. Nihai ürün iki Pine v6 dosyası
(`site/public/indikatorler/tto-yapi.pine`, `tto-momentum.pine`), Python
replikasyonu (`Aktarılacak Projeler/Indikator/yapi_referans.py`), backtest
(`backtest.py` → `site/src/data/yapi_backtest.json`), on figür (`sekil.py`),
sayfa (`site/src/content/indikatorler/tto-yapi-momentum.mdx`, bileşen
`YapiBacktest.astro`) ve kapı (`dogrula.py` → sayfa sınavı 26 kendiliğinden
koşturur; `duman.py` on bir madde: geleceğe bakma bar bar, dersin Gartley
örneği 40,43–40,51, Pine input ↔ SABIT, tablo ↔ Pine dizileri, harmonik
bantlar ↔ f_klasik, olasılık bloğu ↔ JSON, pine_denetle, emir mekaniği altı
hâl, BOS yalnız onaylı swing'e, künye, ve kapının KENDİ bağımlılığı).

KAPININ BAĞIMLILIĞI KOŞUCUDA ÖLÇÜLÜR. İlk yayın koşusu (#600) sayfa sınavı
26'da düştü: `dogrula.py` figür sırasını sormak için `sekil`i içe aktarıyor,
`sekil` en tepede plotly istiyor ve yayın koşucusunda plotly KURULU DEĞİL.
Yerel `npm run sinav` geçmişti — yerelde plotly var. Bir yayın kapısının
okuduğu modül, koşucuda olmayan bir kütüphaneyi tepeden isteyemez; çizim
kütüphanesi çizim yolunun bağımlılığıdır, kapı yolunun değil. `sekil` plotly
yoksa `None`a düşer (çizim `main` adıyla reddeder), `duman` ⑪ kapı yolunu
plotly ENGELLENMİŞ alt süreçte koşturur (kos() çağrılmaz — madde kendini
çağırırdı). Arıza enjeksiyonuyla sınandı. Yan tuzak: düzeltme yalnız
`Aktarılacak Projeler/` altına dokunduğu için `yayin.yml`in `site/**` yol
süzgeci ateşlemedi; yayın elle dispatch edildi (#601 yeşil). Bir kapıyı
düzelten commit siteye çıkmayan bir dizindeyse, yayını kendisi tetiklemez.

VERİ YOLU. Bu koşucu Yahoo'ya çıkamıyor; bulut çıkıyor. İlk yol (koşu
kaydına base64 basıp ayrıştırmak) İKİ kez tıkalı çıktı: kayıt aracı 95 bin
satırın SON 5 binini veriyor ve kaydın tam indirmesi koşucu depolamasına
(Azure blob) çıkamıyor — kurum politikası, retry yok. Doğru yol deponun kendi
kalıbı: `indikator-veri.yml` (workflow_dispatch, `contents: write`, veri
concurrency grubu) `indir.py`yi koşturup arşivi DALA COMMIT eder; 15 enstrüman
× 4 aralık = 60 csv.gz + `kunye.json` (sha256; `veri.py` okurken sınar).
Kısa aralıklar (5/15 dk) Yahoo'da 60 günle sınırlı ve koşular ÜST ÜSTE
BİRİKTİRİLİR; cron bilerek yok. Yeni iş akışı dalda dispatch EDİLEMİYOR
(404): dosya önce main'e girmeli, sonra ref olarak dal verilebilir. İki
tuzak ölçüldü: (1) pandas 3'te `DatetimeIndex.view('int64') // 10**9`
çözünürlüğe bağlı — bulutta indeks SANİYE çözünürlüğünde geldi, 617 bin
barın hepsine t=1 yazıldı; `as_unit("s").asi8` ile sabitlendi. (2) Yahoo'nun
FX GÜNLÜK barında gövde yok (gövde/menzil medyanı 0,02); günlük ve 4 sa
saatlikten kurulur (`veri.yeniden_ornekle`, UTC gece yarısı kova, son kova
düşer). Yahoo 5 dk EUR/USD, AUD/USD, NZD/USD barlarının üçte biri gövdesiz
(kaba kotasyon) — yapı/havuz ölçüleri sağlam, bar anatomisi zayıf.

ÖLÇÜM (560 bin kapanmış bar, 75 seri, 5 dilim). Taban oranlar okumayı
değiştiriyor: BOS'tan sonra ±0,618·aralık hedefi kırılım geri alınmadan
%28–37; CHoCH/MSS sonrası yeni yönde BOS %46–53; sweep sonrası 1 ATR dönüş
%47–50 (yazı tura); FVG 50 barda CE %79–83, tam dolum %70–76, ters %33–39;
OB ilk dokunuşta 1 ATR tepki %52–57; eşit tepe/dip 50 barda sweep %31–33 ·
run %38–52 · test yok %23–30; PRZ'ye gelme %31–42, gelenin teyidi %61–72,
teyitten T1 %57–72. PAKETLER: beş paketin hiçbiri maliyet sonrası
yayımlanabilir kenar vermedi. OB retest her dilimde rastgele GİRİŞİ yeniyor
(brüt +0,20…+0,27 R, iki yarı tutarlı) ama aynı derinlikteki rastgele LİMİT
(eşleştirilmiş rastgele seviye, SMC 15.4) aynı sayıyı veriyor — kenar yerin
değil geri çekilmeyi limitle almanın; risk medyanı 0,6 ATR, spread 5/15
dk'da eksiye çeviriyor. Diverjans tablosunun en iyi satırı (iddia %63,6)
%26–28 ölçüldü; satırların çoğu %50 civarı, iddia sırasıyla ölçülen sıra
ilişkisiz. Konum/trend/itki süzgeçleri paket ortalamasını değiştirmiyor.

ÜÇ ÖLÇÜM TUZAĞI KAYDA DEĞER. (1) R'nin paydası PLANLANAN risktir: boşlukla
dolan limitte payda doluştan kurulunca hafta sonu boşluğu riski sıfıra
yaklaştırıp tek işlemde onlarca R üretti (1 sa OB tabanı +2,9 R — artefakt).
(2) Rastgele tabanın girişi de sinyal kapanışından değil DOLUŞ fiyatından
kurulur; aksi 34 emirde +0,79 R sahte taban verdi. (3) BOS yalnız ONAYLI
swing'e karşı sorulur; koşan uca karşı sorulunca 823 sahte BOS çıktı.
Harmonik PRZ bant UÇLARINDAN değil İDEAL üç sayıdan kurulur: uçlar bölgeyi
şişirip Gartley'nin B bandını paylaşan Crab'i aynı C'de sahte aday yaptı.

PARİTE KAPISININ GÖREMEDİĞİ İKİ FARK ADIYLA: Pine `ta.pivothigh`in eşitlik
davranışı derlenmeden doğrulanamaz (replikasyon kesin eşitsizlik); PDH/PDL
Pine'da borsa günü, Python'da UTC gün. Pine hiç derlenmedi (on statik ölçüt).
AÇIK: kill zone/seans süzgeci ölçülmedi (arşiv saat damgalı, ölçülebilir);
5-0 · Three Drives · Nen Star tanınmıyor; SMT/COT yok; sayfa sınavı 19
indikatorler/ HTML figürlerini taramıyor (yalnız projeler/).

**Kurucu ilke — BİR ALT DİZE ARAMASI SÖZCÜK SINIRINI SORMUYORSA ER GEÇ BAŞKA
BİR SÖZCÜĞÜN İÇİNE DÜŞER; ve bir MUAFİYET, DERLENMİŞ ÇIKTIYA karşı
koşturulmadıysa konmuş sayılmaz.** 22.09.2026 sabahı aynı kusur sınıfı ÜÇ ayrı
yerde çıktı ve üçü de "kapsam kadar HASSASİYET de denetimin parçasıdır"
ailesinden. (1) Tweet kapısı gönderiye giden cümleleri site atfı taşıyorlarsa
düşürüyor; arama ham alt dizeydi ve `"sitede"` izi **"kapasitede"** sözcüğünün
İÇİNDE geçiyor — kapasite kullanım oranını anlatan meşru bir cümle sessizce
gönderiden düştü. Kapasite bu bültende her ay geçen bir makro terim, yani kusur
tek seferlik değil YAPISAL; aynı çift `"sitemiz"` ↔ "kapasitemiz" ve
`"sitede"` ↔ "üniversitede" için de var. (2) Aynı gün Tufex'e yazılan yeni bir
ölçüt `"09.2026"` alt dizesini aradı ve o dizge `"09.09.2026"` GÜN damgasının
içinde de geçtiği için ölçüt DOĞRU çıktıyı kusur saydı. (3) Sayfa sınavının
21. ölçütü `X hesab` arıyor ve bulduğu şey bizim cümlemiz değil, TARANAN HABER
LİSTESİNDEKİ bir özetti — bir partinin ekonomi başkanlığının X hesabından
paylaşım yaptığını söyleyen bir haber. Kararın (07.09.2026) koruduğu şey KENDİ
hesabımız ve KENDİ gönderimizdir; bir haberin içindeki üçüncü tarafın hesabı
değil. Bedeli en ağır olan buydu: bülten yazılmış, denetimden 0 engelle geçmiş,
main'e girmişti — ve yayın kapısı düştüğü için site dondu, günün bülteni okura
çıkmadı. Sol sözcük sınırı şartı çözümün tamamı değil, yalnız (1) için
geçerli; (3) sınırla çözülmez, çünkü sorun eşleşmenin biçimi değil METNİN
KİMİN OLDUĞU. Haber listesi tümüyle dış kaynaktan gelir ve makine doldurur,
o yüzden YAZI ailesi o bloğa bakmaz; BAĞ ailesi daraltılmaz — listedeki bir
x.com ADRESİ hâlâ engeldir, çünkü orası okura tıklanacak bir bağ verir.
Muafiyetin kuralı boşaltmadığı ayrıca sınanıyor: listenin DIŞINDA geçen bir
öz-atıf yakalanmaya devam ediyor.

İkinci yarısı daha pahalıya mal oldu ve asıl ders o. Muafiyet ilk yazımda
`<ul class="haber-liste">` diye SABİT yazıldı; Astro her etikete kendi kapsam
niteliğini ekliyor (`data-astro-cid-…`), yani kalıp DERLENMİŞ çıktıda HİÇ
tutmadı. Duman sınaması yeşil geçti — çünkü fikstür ideal biçimi taşıyordu —
ve sayfa sınavı düşmeye DEVAM ETTİ. İki yeşil arasında site hâlâ donuktu.
Bir muafiyetin çalıştığı, onu fikstüre karşı değil GERÇEK ÇIKTIYA karşı
koşturarak bilinir: site derlenip ölçüt canlı `dist/`e karşı koşuldu ve ancak
ondan sonra "geçti" denebildi. Fikstür artık derlenmiş biçimin kendisini
taşıyor (nitelikleriyle birlikte). "Ölçüt geçti" ile "arıza yok" bu depoda
bir kez daha birbirine tıpatıp benzedi — bu sefer benzeten şey fikstürün
gerçeği taşımamasıydı.

**Kurucu ilke — HATTIN KAPISI DÜŞTÜĞÜNDE PANO DONAR VE BU SESSİZDİR.**
18.09–22.09 arası Butce ile Tufex'in duman sınamaları düşüyordu; duman
adımlardan ÖNCE koştuğu için iki hat komple atlandı, panoları dört gün
18.09'da dondu ve veri tazeleme her koşuda kırmızı bitti (#229, #231–#234).
Arızanın görüntüsü sağlığın görüntüsüne benziyordu: commit `if: always()`
taşıdığı için öbür hatlar yayına gidiyor, site ayakta kalıyor, yalnız iki pano
donuyordu. İkisi de bu dosyanın en sık tekrar eden cümlesinin eşi — kural bir
yerde yazılıp öbür yerde uygulanmamıştı. Butce'de "eksi bir yaş yayımlanmaz"
kuralı `veri.gecikme_gun`da adıyla yazılı ama yalnız "butce" ailesine
uygulanmıştı; haftalık menkul kıymet bacağı çıpanın üç gün ilerisinde
tarihlenince okur cümlesi "son gözlemden bu yana -3 gün" oldu (hem anlamsız,
hem ASCII tire). Negatif yaş ATILMADI, ÇEVRİLDİ — ölçü olduğu gibi kalıyor
(`negatif_muaf` tam bu hâl için var), değişen yalnız cümlenin yazımı.
Tufex'te "kapanmamış ay damgaya girmez" kuralı OVP'de yazılı, DİBS'te
`ay_kapandi` yardımcısına kadar götürülmüş — Tufex ise AYNI anketi okuyan
ÜÇÜNCÜ tüketici ve kural ona uygulanmamıştı. Arıza TAKVİME BAĞLI VE TEKRAR
EDER: anket her ay yayımlandığı günden ayın sonuna kadar aynı hâli üretir,
yani ayda bir hafta hattı kapatırdı. Kapsam sezilmedi ÖLÇÜLDÜ: sekiz hattın
damgasında ay biçimli bacak var ve ayrımı yapan şey KAYNAĞIN RİTMİ — TÜFE,
kredi, GSYH gibi yayımlar ay kapandıktan SONRA geldiği için bacakları yapısal
olarak kapalı; anket dateli olduğu ayın İÇİNDE yayımlanıyor, bu yüzden açık
olan iki hat onu okuyan DİBS ile Tufex'ti ve DİBS zaten korunuyordu.
