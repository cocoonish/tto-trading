# TTO Trading

Türkiye makro & piyasa araştırmaları: veri hatları (Python) → statik site (Astro).
On üç veri hattı EVDS/TÜİK/Hazine/haber kaynaklarından çekip Plotly grafikleri üretir,
site bunları gömer; sayfa metnindeki güncel sayılar `ozet.json`'dan **canlı** okunur.

> **Bu depo private.** Veri hatları, `Research/` altındaki masa dokümanları ve commit
> geçmişi burada kalır. **Yayınlanan tek şey `site/`**: ayrı bir public depoya
> (`cocoonish/cocoonish.github.io`) kopyalanır ve GitHub Pages'te yayına girer —
> **https://cocoonish.github.io/** · gönderim: `yayinla.bat`

---

## Yeni bilgisayarda 3 adım

```bash
git clone https://github.com/cocoonish/tto-trading.git
cd tto-trading
```

1. **EVDS anahtarı** — repoyla gelmez. Kökte `.evds_key` adlı dosya oluşturup içine
   yalnız anahtarı yazın (ya da `TTO_EVDS_KEY` ortam değişkeni). Tüm hatlar aynı sırayla
   arar: ortam değişkeni → `<proje>/.evds_key` → kök `.evds_key` → `TCMBNetRezerv/.evds_key`;
   köke koyulan tek dosya hepsine yeter.
2. **Kurulum** — **`kur.bat`** (çift tıklama yeter). Yedi veri hattının her biri için
   `.venv` + `requirements.txt`, site için `npm install`, marj hattı için Playwright.
   Tekrar çalıştırmak güvenlidir. macOS/Linux: `python3 kur.py`
3. **Siteyi aç** — `site.bat` → tarayıcı `http://localhost:4321` adresinde açılır.

4. **Denetle** — `guncelle.bat --denetle` (macOS/Linux: `python3 guncelle.py --denetle`):
   hiçbir şey koşturmadan Python/git/Node, EVDS anahtarı ve her hattın bağımlılıklarını
   yoklar; eksik varsa tek satırlık çözümü yazar. `--duzelt` eklerseniz kendisi kurar.
   Yayın tarafının eşleniği: `yayinla.bat --denetle` (git kimliği, uzak depo erişimi).

Ayrıntılı anlatım: **[KURULUM.md](KURULUM.md)** · çalışma rehberi: [CLAUDE.md](CLAUDE.md)

## Günlük kullanım

| Komut | İş |
|---|---|
| `kur.bat` | **kurulum**: tüm bağımlılıklar (`--hat tcmb hazine`, `--site-yok`, `--liste`) |
| `site.bat` | siteyi yerelde aç (`--port`, `--derle`, `--onizle`) |
| `guncelle.bat` | menü: hangi hatlar güncellensin, hafif/tam, commit? |
| `guncelle.bat --hepsi --tam` | yedi hattın tamamı, ağır adımlar dahil |
| `guncelle.bat --denetle` | **koşmadan denetle**: eksik paket/anahtar/araç var mı (`--duzelt` = kur) |
| `guncelle.bat --kur <hat>` | tek hattın `.venv` + bağımlılıkları (kur.bat'ın alt kümesi) |
| `panel.bat hazine` \| `fx` | canlı pano (Dash 8050 / Streamlit 8501) |
| `yayinla.bat` | siteyi yayına gönder (`-m "mesaj"`, `--kuru` = deneme, `--denetle`) |
| `bulten.bat` | **günlük bülten** üret (`--guncelle` = önce hatları tazele) |

Windows dışında `.bat` yerine aynı adlı `.py`: `python3 kur.py`, `python3 site_baslat.py`,
`python3 guncelle.py`, `python3 panel.py`, `python3 yayinla.py`.

## Klasörler

```
site/                     Astro sitesi
  src/content/projeler/     proje sayfaları (.mdx)
  src/content/arastirma/    ders/araştırma sayfaları (.mdx)
  public/projeler/<slug>/   hatların ürettiği grafikler + ozet.json
  public/arastirma/<slug>/  ders grafikleri
  tools/plotly_stil.py      grafiklere ev stili
  tools/ders_grafik/        ders grafiklerini üreten scriptler
Aktarılacak Projeler/     veri hatları (TCMBNetRezerv, TRYREER, hazineihrac, …)
Research/                 ham araştırma (marj hattı burada)
bat/                      proje başına Windows bat'ları
kur.py · guncelle.py · panel.py · site_baslat.py · yayinla.py   kök araçlar (.bat'ları var)
```

## Veri hatları

Her hattın ayrıca **tek başına çalışan** bir deposu var (yalnız o projeyi indirmek için).

| Hat | Sayfa | Kaynak | Tek başına depo |
|---|---|---|---|
| `tcmb` | TCMB Net Rezerv Takibi | EVDS analitik bilanço + IRFCL | [tcmb-net-rezerv](https://github.com/cocoonish/tcmb-net-rezerv) |
| `usdtry` | USD/TRY Devalüasyon Hızı | EVDS kur | [usdtry-deval](https://github.com/cocoonish/usdtry-deval) |
| `reer` | TL Reel Efektif Döviz Kuru | EVDS REDK | [try-reer](https://github.com/cocoonish/try-reer) |
| `yabanci` | Yabancı Pozisyonu (DİBS/hisse) | EVDS menkul kıymet ist. | [yabanci-pozisyon](https://github.com/cocoonish/yabanci-pozisyon) |
| `hazine` | Hazine İhraç Takvimi & İhale Analizi | Hazine sitesi (scraper) | [hazine-ihrac](https://github.com/cocoonish/hazine-ihrac) |
| `fx` | FX Haber-Duyarlılık Endeksi | GDELT + RSS + FinBERT | [fx-haber-endeksi](https://github.com/cocoonish/fx-haber-endeksi) |
| `marj` | Yiyecek Hizmetleri: Fiyat/Maliyet Marjı | EVDS + TÜİK MEDAS | [yiyecek-marj](https://github.com/cocoonish/yiyecek-marj) |
| `enflasyon` | Enflasyon Panosu | EVDS3 TÜFE ağacı + ÖKTG + anketler | — |
| `kredi` | Kredi ve Parasal Büyüklükler | EVDS3 haftalık para-banka + analitik bilanço | — |
| `fonlama` | TCMB Fonlama ve Likidite | EVDS3 APİ + kotasyon + TLREF + ZK | — |
| `dibs` | DİBS Verim Eğrisi ve Reel Faiz | EVDS3 DİBS fiyat/kupon + TÜFEX + anket | — |
| `odemeler` | Ödemeler Dengesi ve Dış Finansman | EVDS3 ödemeler dengesi + dış borç + GSYH | — |
| `butce` | Bütçe ve Borç Stoku | EVDS3 bütçe + dış borç + menkul kıymet sahipliği | — |

Siteye girmeyen ek araç: [try-asw](https://github.com/cocoonish/try-asw) — Bloomberg TRY OIS
eğrisiyle ASW hesaplayıcı (BBG terminali gerektirir, o yüzden sitede yok).

## Analiz

`site/src/content/analiz/` — tek bir piyasa gelişmesini mekanizmasına, tarihsel
emsaline ve fiyat etkisine kadar açan uzun yazılar. Bültenden farkı kapsam değil
**derinlik**: bülten günün tamamını özetler, analiz tek olayı sonuna kadar açar.
Sitede `/analiz/` adresinde.

Yazım standardı **[`analiz/YAZIM.md`](analiz/YAZIM.md)**, şablon
[`analiz/sablon.mdx`](analiz/sablon.mdx): tarihli slug ve başlık, yönetici
özeti (tez · soru–cevap · altı ölçüm), "Ne ölçmedik" kapanışı, her sayı
`<Deger>` ile canlı. Kapı `site/tools/analiz_sinavi.py` (sayfa sınavının 10.
ölçütü). Aynı konunun yazıları slug kökünden **seri** olur ve sayfada
birbirine bağlanır. Yayın günü X gönderisi yönetici özetinden kendiliğinden
kurulur (`tweet/analiz.py`).

## Dersler

`site/src/content/arastirma/` — teori + gerçek veriyle adım adım pratik:

| Ders | Kapsam |
|---|---|
| Faiz Teorisi ve Eğri İnşası | konvansiyonlar, bootstrap, TLREF patikası |
| Enstrüman Fiyatlama | tahvil, swap, forward swap, swaption, ASW |
| Risk ve Hedge | DV01 konvansiyonları, FX forward, OIS hedge |
| Trade Pratiği | asset swap ve TRY OIS pozisyonları |
| Opsiyon Book Yönetimi | FX vanilla, çapraz kur, egzotikler |
| Bloomberg HRA | korelasyon ve göreli değer analizi |
| **Al Brooks fiyat hareketi** | bar okuma, yapı, kırılım, geri çekilme, dönüşler, mıknatıslar, işlem matematiği, seans; 28 adım adım işlem — **160 bin kelime, 94 grafik** |
| **Smart Money Concepts (SMC)** | yapı, likidite, OB/FVG, 15 setup, backtest protokolü — 57 grafik |
| **Harmonik Patternler** | Fibonacci, XABCD kataloğu, PRZ, işlem yönetimi — 48 grafik |

## Otomatik güncelleme

`.github/workflows/veri-guncelle.yml` her Cuma 06:00 UTC'de hafif hatları koşturur ve
çıktıları commit'ler. **Depo secret'ı gerekir:** Settings → Secrets and variables → Actions
→ `TTO_EVDS_KEY`. Ağır adımlar (FinBERT, Hazine scraper) bilinçli olarak cron dışıdır;
onlar yerelde `guncelle.bat --tam` ile koşturulup push edilir.

## Günlük bülten

Her sabah otomatik derlenen makro bülteni: **https://cocoonish.github.io/bulten/**

Dört katman, üçü kural tabanlı (LLM yok), biri yorum:

| Katman | Ne yapar | Nerede |
|---|---|---|
| `bulten/olay.py` | Hatların `ozet.json`'unu bir önceki **veri sürümüyle** kıyaslar, `ayar.py`'deki eşikleri uygular, cümleyi kurar | çekirdek |
| `bulten/takvim.py` | TÜİK Ulusal Veri Yayımlama Takvimi (TÜİK+TCMB+HMB+BDDK+SPK), Fed ve ECB takvimleri, Hazine ihale programı (kendi hattımızdan, **model beklentisiyle**), TCMB PPK/rapor tarihleri | çekirdek |
| `bulten/haber.py` | TCMB Basın Duyuruları, Resmî Gazete, Bloomberg HT / AA / Investing / Google News; alaka süzgeci + öykü kümeleme | çekirdek |
| yorum | "Günün okuması" — sayılar çekirdekten, cümle LLM'den | Mac'te zamanlanmış görev |

Otomasyon çift bacaklı: **bulutta** `.github/workflows/bulten.yml` her sabah 07:23'te
(İstanbul) hatları tazeler ve bülteni üretir — bilgisayar kapalıyken de bülten çıkar;
**Mac'te** zamanlanmış Claude görevi 07:41'de üstüne yorum katmanını yazar ve yayınlar.
Yorum alanı deterministik koşularda **korunur**, silinmez.

Eşikler ve izlenen büyüklükler tek dosyada: [`bulten/ayar.py`](bulten/ayar.py) (37 izlem).
Bir eşik ayda birkaç kez tetikleniyorsa doğru yerdedir; her gün tetikleniyorsa bülten
okunmaz hâle gelir.

**Kıyas noktası neden "önceki veri sürümü":** aynı verinin iki anlık görüntüsü arasındaki
fark sıfırdır. Hat günde iki kez koşulursa bülten "değişiklik yok" derdi — haftalık bir
seri için bile. Bu yüzden kıyas, `_tarih`i farklı olan en son görüntüye göre yapılır:
"son veri yayımından bu yana ne değişti".

Depo secret'ları: `TTO_EVDS_KEY` (zorunlu), `TTO_YAYIN_TOKEN` (isteğe bağlı — bulut
doğrudan yayına gönderebilsin diye public depoya yazma yetkili PAT).

## X gönderileri

`tweet/` — bülten, haftaya bakış, teknik analiz ve analiz yazıları yayın günü
X'te tek uzun gönderi olarak çıkar (link yok, emoji yok, site atfı yok).
Metin yalnız yayımlanmış katmandan kurulur: bülten okuması ve gündem
(`uret.py`), analizin yönetici özeti (`analiz.py`). Her gönderi
**`tweet/denetim.py`** kapısından geçer — tavsiye dili, link, HTML kalıntısı,
site atfı, sayı ortasında kesik cümle, boş bölüm etiketi, sorumluluk notu, okur
dili; engel varsa gönderim durur. `gonder.py` defter tutar (aynı içerik bir kez),
bayat içeriği göndermez, gönderilen metni `tweet/arsiv/`e yazar ve defteri
`site/src/data/tweet/`e aynalar — sayfa künyesindeki "X gönderisi" bağı buradan.
Önizleme: `python3 tweet/gonder.py --kuru`.

## Yayın

Site iki depoda yaşar: **kaynak burada** (private), **yayın** ayrı bir public depoda
(`cocoonish/cocoonish.github.io`). `yayinla.bat` şunu yapar: yerelde derler (CI'da
patlamasın diye), `site/` klasörünü public depo klonuna kopyalar, gömülü kimlik bilgisi
taraması yapar, commit'ler ve push eder. Bulut iş akışı (`yayin.yml`) aynı işi
her içerik commit'inde yapar ve kopyalamadan ÖNCE siteyi derleyip
`site/tools/sayfa_sinavi.py`yi koşturur: derleme ya da sınav düşerse yayın durur.
Yerelde aynı kapı: `cd site && npm run yayin-kontrol` (derleme + KaTeX + sayfa sınavı).
Sayfa kimliği (kanonik adres, bağlantı önizleme kartı, RSS: `/rss.xml`,
`/bulten/rss.xml`, `/teknik/rss.xml`, `/analiz/rss.xml`) siteyle birlikte üretilir. Push'u gören GitHub Actions derleyip Pages'e
koyar (~2 dk) → https://cocoonish.github.io/

Public depoya **yalnız `site/` gider**: veri hatları, `Research/`, `bat/`, `CLAUDE.md`
ve bu deponun commit geçmişi oraya hiç kopyalanmaz.

## Güvenlik notları

- **Anahtarlar kaynak koda gömülmez.** Sıra: `TTO_EVDS_KEY` → `<proje>/.evds_key` → kök
  `.evds_key`. `.evds_key` `.gitignore`'da. `push.bat` ve `guncelle.py --commit`, commit
  öncesi eklenen satırlarda `KEY/TOKEN/SECRET/PASSWORD = "..."` kalıbını tarar ve bulursa durur.
- **Bu depo public YAPILMAMALIDIR:** geçmiş commit'lerde (a) rotasyona girmemiş eski bir
  EVDS anahtarı ve (b) yalnız yerel doğrulama için kullanılan özel görseller bulunuyor.
  Yayınlanması istenirse önce `git-filter-repo` ile geçmiş temizlenmeli.
