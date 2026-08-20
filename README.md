# TTO Trading

Türkiye makro & piyasa araştırmaları: veri hatları (Python) → statik site (Astro).
Yedi veri hattı EVDS/TÜİK/Hazine/haber kaynaklarından çekip Plotly grafikleri üretir,
site bunları gömer; sayfa metnindeki güncel sayılar `ozet.json`'dan **canlı** okunur.

> **Depo private.** Site henüz yayında değil; yerelde `site.bat` ile açılır (aşağıda).

---

## Yeni bilgisayarda 3 adım

```bash
git clone https://github.com/cocoonish/tto-trading.git
cd tto-trading
```

1. **EVDS anahtarı** — repoyla gelmez. Kökte `.evds_key` adlı dosya oluşturup içine
   yalnız anahtarı yazın (ya da `TTO_EVDS_KEY` ortam değişkeni).
2. **Kurulum** — **`kur.bat`** (çift tıklama yeter). Yedi veri hattının her biri için
   `.venv` + `requirements.txt`, site için `npm install`, marj hattı için Playwright.
   Tekrar çalıştırmak güvenlidir. macOS/Linux: `python3 kur.py`
3. **Siteyi aç** — `site.bat` → tarayıcı `http://localhost:4321` adresinde açılır.

Ayrıntılı anlatım: **[KURULUM.md](KURULUM.md)** · çalışma rehberi: [CLAUDE.md](CLAUDE.md)

## Günlük kullanım

| Komut | İş |
|---|---|
| `kur.bat` | **kurulum**: tüm bağımlılıklar (`--hat tcmb hazine`, `--site-yok`, `--liste`) |
| `site.bat` | siteyi yerelde aç (`--port`, `--derle`, `--onizle`) |
| `guncelle.bat` | menü: hangi hatlar güncellensin, hafif/tam, commit? |
| `guncelle.bat --hepsi --tam` | yedi hattın tamamı, ağır adımlar dahil |
| `guncelle.bat --kur <hat>` | tek hattın `.venv` + bağımlılıkları (kur.bat'ın alt kümesi) |
| `panel.bat hazine` \| `fx` | canlı pano (Dash 8050 / Streamlit 8501) |

Windows dışında `.bat` yerine aynı adlı `.py`: `python3 kur.py`, `python3 site_baslat.py`,
`python3 guncelle.py`, `python3 panel.py`.

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
kur.py · guncelle.py · panel.py · site_baslat.py   kök araçlar (her birinin .bat'ı var)
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

Siteye girmeyen ek araç: [try-asw](https://github.com/cocoonish/try-asw) — Bloomberg TRY OIS
eğrisiyle ASW hesaplayıcı (BBG terminali gerektirir, o yüzden sitede yok).

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
| **Smart Money Concepts (SMC)** | yapı, likidite, OB/FVG, 15 setup, backtest protokolü — 57 grafik |
| **Harmonik Patternler** | Fibonacci, XABCD kataloğu, PRZ, işlem yönetimi — 48 grafik |

## Otomatik güncelleme

`.github/workflows/veri-guncelle.yml` her Cuma 06:00 UTC'de hafif hatları koşturur ve
çıktıları commit'ler. **Depo secret'ı gerekir:** Settings → Secrets and variables → Actions
→ `TTO_EVDS_KEY`. Ağır adımlar (FinBERT, Hazine scraper) bilinçli olarak cron dışıdır;
onlar yerelde `guncelle.bat --tam` ile koşturulup push edilir.

## Güvenlik notları

- **Anahtarlar kaynak koda gömülmez.** Sıra: `TTO_EVDS_KEY` → `<proje>/.evds_key` → kök
  `.evds_key`. `.evds_key` `.gitignore`'da. `push.bat` ve `guncelle.py --commit`, commit
  öncesi eklenen satırlarda `KEY/TOKEN/SECRET/PASSWORD = "..."` kalıbını tarar ve bulursa durur.
- **Bu depo public YAPILMAMALIDIR:** geçmiş commit'lerde (a) rotasyona girmemiş eski bir
  EVDS anahtarı ve (b) yalnız yerel doğrulama için kullanılan özel görseller bulunuyor.
  Yayınlanması istenirse önce `git-filter-repo` ile geçmiş temizlenmeli.
