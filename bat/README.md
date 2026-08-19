# Proje bat'ları (Windows)

Her proje için dört bat: **kur → çalıştır → push**, ara sıra **güncelle**.
Panosu olan iki projede beşinci bat: **panel** (canlı dashboard).
Hepsi `_ortak/ortak.bat`'a (panel: kökteki `panel.py`'ye) delege eder — bir düzeltme
yedi yere değil bir yere gider.

Kök klasörde ayrıca iki sarmalayıcı var, hepsini tek yerden yönetmek için:
`guncelle.bat` (tüm hatlar, kurulum `--kur` dahil) ve `panel.bat` (paneller).

| Klasör | Proje | Kaynak |
|---|---|---|
| `tcmb-net-rezerv/` | TCMB Net Rezerv | `Aktarılacak Projeler/TCMBNetRezerv` |
| `usdtry-deval/` | USDTRY Devalüasyon | `Aktarılacak Projeler/USDTRYDeval` |
| `try-reer/` | TRY REER | `Aktarılacak Projeler/TRYREER` |
| `yabanci-pozisyon/` | Yabancı Pozisyonu | `Aktarılacak Projeler/ForeignHoldings` |
| `hazine-ihrac/` | Hazine İhraç | `Aktarılacak Projeler/hazineihrac` |
| `fx-haber-endeksi/` | FX Haber Endeksi | `Aktarılacak Projeler/indices` |
| `yiyecek-marj/` | Yiyecek Hizmetleri Marjı | `Research/marj` |

## Dört işlem

- **`kur.bat`** — projeye özel `.venv` oluşturur, `requirements.txt`'i yükler. Tekrar çalıştırmak
  güvenlidir (var olanı atlar). Her projenin ayrı ortamı var: `indices` torch/transformers ister,
  paylaşılan ortam diğerlerini şişirir ve sürüm çakıştırırdı.
- **`guncelle.bat`** — `git pull --rebase --autostash` + requirements'ı yeniden yükler.
- **`calistir.bat`** — hattı **baştan sona** koşturur (yerel TAM hat; cron'daki hafif "depodaki
  veriden grafik" adımı değil). Örn. FX'te `run.py --fetch-history` (GDELT + FinBERT), Hazine'de
  scraper dahil. Adımlar sırayla; **biri düşerse zincir durur** — yarım çıktı üretilmez.
- **`panel.bat`** *(yalnız `hazine-ihrac` ve `fx-haber-endeksi`)* — canlı panoyu açar
  (Hazine: Dash → `http://127.0.0.1:8050`, FX: Streamlit → `http://localhost:8501`).
  Kökteki `panel.py`'ye delege eder; **açmadan önce** paket (dash/streamlit) ve panonun
  okuduğu CSV/JSON var mı denetler, eksikse ne yapılacağını yazar. Pano veri ÜRETMEZ,
  üretilmiş veriyi okur — önce `calistir.bat`.
- **`push.bat`** — yalnız o projenin klasörünü + `site/public/projeler/<slug>` çıktısını commit'ler
  ve GitHub'a gönderir. **Commit öncesi gömülü kimlik bilgisi taraması** yapar
  (`*KEY/TOKEN/SECRET/PASSWORD = "..."`) — bulursa stage'i geri alıp durur.

## Kök sarmalayıcılar (tüm projeler)

| Komut | İş |
|---|---|
| `guncelle.bat` | menü: hangi hatlar, hafif/tam, commit? |
| `guncelle.bat --hepsi --tam` | 7 hattın tamamı, ağır adımlar dahil |
| `guncelle.bat --kur --hepsi` | her projeye `.venv` + `requirements.txt` (yeni bilgisayarda İLK adım) |
| `guncelle.bat --kur tcmb fx` | yalnız seçilenleri kur |
| `panel.bat` | menü: hangi pano? |
| `panel.bat hazine` / `panel.bat fx` / `panel.bat site` | panoyu/siteyi aç (Ctrl+C kapatır) |
| `panel.bat hazine --port 8060` | portu değiştir |

`guncelle.py` her hattı, proje klasöründe `.venv` varsa **onun** python'uyla koşturur;
yoksa sistem python'uyla. (Eskiden hep sistem python'uydu: `kur.bat` ile venv kurulmuş
Windows'ta `tcmb`/`pdfplumber` bulunamıyor, ilk hat düşüyordu.)

## EVDS anahtarı

Sırayla aranır: `TTO_EVDS_KEY` ortam değişkeni → `<proje>/.evds_key` → repo kökündeki
`.evds_key`. Anahtar **kaynak koda gömülmez** ve `.evds_key` `.gitignore`'dadır. Bulunamazsa
`calistir.bat` uyarır; EVDS'e giden adımlar hata verir.

## Notlar

- Klasör adları Türkçe harf içerir (`Aktarılacak Projeler`); `ortak.bat` bu yüzden `chcp 65001`
  ile UTF-8'e geçer. Bat'lar başka yere kopyalanırsa `%~dp0` göreli yolları bozulur — yerinde
  çalıştırın.
- `yiyecek-marj/calistir.bat` içindeki `src\run_all.py` MEDAS hasadı için Playwright ister:
  ilk kurulumdan sonra bir kez `python -m playwright install chromium`. `data/raw/medas_*.xls`
  mevcutsa hasat atlanır, Playwright gerekmez.
- Cron (`.github/workflows/veri-guncelle.yml`) aynı hatları Cuma 06:00 UTC'de koşturur ama
  ağır adımları (FinBERT, scraper) bilinçli olarak dışarıda bırakır; onlar bu bat'larla yerelde
  koşulup push edilir.
