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
