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
│   └── indices/                 # FX haber-duyarlılık endeksi (henüz web çıktısı yok)
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
| `olay.py` | eşikleri uygular, olay cümlesini kurar |
| `piyasa.py` | 51 enstrüman, TL faiz seti, türev makaslar, **σ-normalize hareket** |
| `takvim.py` | resmî yayım takvimi; `surpriz.py` geçmişi arşivler ve sonucu ölçer |
| `soz.py` | söz defterini (`izleme.json`) okura açar |
| `rejim.py` | reel faiz, taşıma, reel kredi, REDK sapması, eğri, rezerv kalitesi, **enflasyon risk primi, makroihtiyati ayrışma** |
| `grafik_veri.py` | satır içi SVG grafiklerin verisi (Plotly bültene girmez) |
| `denetim.py` | 30 ölçüt; engel varsa bülten yayına gitmez. `karanlik`: hattın saati ilerlerken donan seriyi yakalar |
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
aracı onu değiştiremez (arayüzden kurulmuş rutinler agent'a kapalı; agent'ın
kurduğu rutin ise özel depoyu klonlayamaz, çünkü yeni oturuma kaynak depo
bağlanmaz). Bu yüzden bir kural "rutin metnine yazıldı" diye tamam sayılmaz:
araç onu kendi başına dayatabilmelidir. `yaz.py`nin damga sigortası açık argüman
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
