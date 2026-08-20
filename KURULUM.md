# Yeni bilgisayarda kurulum

Repo private: klonlamak için GitHub hesabınızla giriş gerekir. Bir kez yapılır.

## 1. Ön koşullar (bir kez)

| Ne | Nereden | Not |
|---|---|---|
| **Git** | git-scm.com | Kurulumda varsayılanlar yeterli |
| **Python 3.11+** | python.org | Kurulumda **"Add python.exe to PATH"** kutusunu işaretleyin |
| **GitHub CLI** (`gh`) | cli.github.com | Private repo için en kolay giriş yolu |

Kurulumdan sonra terminali (Windows: PowerShell veya cmd) açıp doğrulayın:

```
git --version
py -3 --version
gh --version
```

## 2. GitHub'a giriş (bir kez)

```
gh auth login
```

Sorulara: **GitHub.com → HTTPS → Yes (git için kimlik doğrulama) → Login with a web browser**.
Tarayıcı açılır, kodu girersiniz. Bundan sonra `git pull`/`git push` şifre sormaz.

## 3. Repoyu çekin

Klasörü nereye koymak istiyorsanız orada:

```
git clone https://github.com/cocoonish/tto-trading.git
cd tto-trading
```

Klasör adında Türkçe harf var (`Aktarılacak Projeler`) — sorun değil, bat'lar UTF-8'e geçiyor.

## 4. EVDS anahtarı — repoyla GELMEZ, elle koymanız gerekir

`.evds_key` bilinçli olarak `.gitignore`'da; yeni bilgisayarda yok. Repo **köküne**
`.evds_key` adlı bir dosya oluşturup içine yalnız anahtarı yazın (satır sonu/boşluk olmasın):

```
echo ANAHTARINIZ> .evds_key
```

Bat'lar sırayla `TTO_EVDS_KEY` ortam değişkeni → `<proje>\.evds_key` → kök `.evds_key`
arar. Kökteki tek dosya bütün projelere yeter.

## 5. Kurulum ve ilk koşu

İki yol var; ikisi de aynı şeyi yapar.

**A) Kökten, hepsi bir arada (önerilen).** Repo kökündeki bat'lar:

```
kur.bat                        REM KURULUM: 7 hattin .venv + requirements + site npm install
guncelle.bat                   REM menu: hangi hatlar, hafif/tam, commit?
site.bat                       REM siteyi ac (http://localhost:4321)
panel.bat                      REM menu: hangi canli pano (dashboard)?
```

`kur.bat` ne yapar: ön koşulları denetler (Python sürümü, Node/npm, EVDS anahtarı — anahtarı
kökte ve proje klasörlerinde arar), her veri hattı için sanal ortam + `requirements.txt`,
`site/` için `npm install`, marj hattı için Playwright Chromium (MEDAS ham dosyaları
depoyla geldiyse atlar). Sonunda özet tablo basar; **tekrar çalıştırmak güvenlidir**
(var olan ortam yeniden kurulmaz, bağımlılıklar tazelenir).

Seçmeli kurulum: `kur.bat --hat tcmb hazine` · siteyi atla: `kur.bat --site-yok` ·
ne kurulacağını gör: `kur.bat --liste`. Tek hat için `guncelle.bat --kur tcmb` de aynı işi
yapar. Kurulum yapılmamış bir hat koşturulursa hata mesajı hangi komutu çalıştıracağınızı yazar.

**B) Proje proje.** `bat\<proje>\` klasörüne gidip sırayla çift tıklayın:

1. **`kur.bat`** — sanal ortam + bağımlılıklar (ilk seferde birkaç dakika)
2. **`calistir.bat`** — hattı koşturur
3. **`push.bat`** — çıktıyı GitHub'a gönderir

Sonraki günlerde: **`guncelle.bat`** (pull) → `calistir.bat` → `push.bat`.

**İlk deneme için `bat\tcmb-net-rezerv\`** — en basit ve en hızlı hat.

## 5a. Siteyi yerelde açmak (en sık kullanacağınız)

Kök klasördeki **`site.bat`** — çift tıklayın. Node/npm denetler, gerekiyorsa `npm install`
çalıştırır, geliştirme sunucusunu başlatır ve tarayıcıyı **http://localhost:4321** adresinde
açar. Kapatmak: pencerede **Ctrl+C**.

```
site.bat                 REM siteyi ac (varsayilan port 4321)
site.bat --port 4400     REM port mesgulse
site.bat --derle         REM uretim derlemesi (npm run build), sunucu acmaz
site.bat --onizle        REM derlenmis siteyi sun
site.bat --kur           REM yalniz npm install
```

macOS/Linux: `python3 site_baslat.py` (aynı seçenekler).
Site **veri üretmez**; grafikleri `site/public/` altından okur. Yeni veri için önce
`guncelle.bat`.

## 5b. Canlı panolar (dashboard)

İki projenin interaktif panosu var. Panolar **veri üretmez**, üretilmiş veriyi okur —
önce ilgili hattı koşturun.

| Komut | Pano | Adres |
|---|---|---|
| `panel.bat hazine` | Hazine İhraç (Dash) — ihaleler, tahminler, filtreler | http://127.0.0.1:8050 |
| `panel.bat fx` | FX Haber Endeksi (Streamlit) — endeks, manşetler, rejim | http://localhost:8501 |
| `panel.bat site` | Sitenin kendisi (Astro dev) — `site.bat` ile aynı | http://localhost:4321 |

`bat\hazine-ihrac\panel.bat` ve `bat\fx-haber-endeksi\panel.bat` da aynı işi yapar.
Port meşgulse: `panel.bat hazine --port 8060`. Kapatmak: pencerede **Ctrl+C**.
Pano açılmadan önce gerekli paket ve veri dosyaları denetlenir; eksikse hangi komutu
çalıştıracağınız yazılır (ör. `guncelle.bat --kur hazine` ya da `guncelle.bat hazine --tam`).
macOS/Linux'ta: `python3 panel.py hazine`.

## 6. Proje başına özel notlar

- **`fx-haber-endeksi`** — GDELT/haber önbelleği (`indices/data/*_cache.json`) repoya
  girmez, çünkü ~35 MB ve her koşuda büyür. Yeni bilgisayarda **ilk `calistir.bat`
  52 haftalık geçmişi sıfırdan çeker ve FinBERT ile skorlar: 2-4 saat sürebilir.**
  Sonraki koşular yalnız yeni haftaları çeker (dakikalar). Ayrıca `kur.bat` torch +
  transformers indirir (~2 GB). Sabır isteyen tek hat bu.
- **`yiyecek-marj`** — MEDAS hasadı için Playwright Chromium gerekir; kökteki `kur.bat`
  bunu **kendisi kurar** (yalnız `Research\marj\data\raw\medas_*.xls` yoksa; varsa atlar).
  Elle kurmak isterseniz:
  ```
  Research\marj\.venv\Scripts\python.exe -m playwright install chromium
  ```
- **`hazine-ihrac`** — `calistir.bat` scraper'ı da koşturur (Hazine sitesini tarar);
  ilk koşu 10-20 dakika, sonrakiler kısa (işlenen URL'ler önbelleklenir).
- Diğer dördü (`tcmb-net-rezerv`, `usdtry-deval`, `try-reer`, `yabanci-pozisyon`) yalnız
  EVDS'e gider, dakikalar içinde biter.

## 7. Site (isteğe bağlı — sadece sayfaları yerelde görmek isterseniz)

Node.js (nodejs.org, LTS) kurun, sonra:

```
cd site
npm install
```

Sonrasında `panel.bat site` (ya da `cd site && npm run dev`) —
tarayıcıda `http://localhost:4321`. Bat'lar siteyi **build etmez**; site GitHub'a push
edilince yayına giren tarafta derlenir. Yerelde bakmak istemiyorsanız bu adımı atlayın.

## Windows dışı (macOS/Linux)

Bat'lar çalışmaz ama mantık aynıdır; her komut proje klasöründe:

```
python3 guncelle.py --kur --hepsi     # kurulum (her projeye .venv + requirements)
python3 guncelle.py                   # menu; ya da: python3 guncelle.py tcmb hazine --tam
python3 guncelle.py --hepsi --commit  # koştur + commit + push
python3 panel.py hazine               # canli pano (fx / site de var)
```

Elle yapmak isterseniz her komut proje klasöründe:

```
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # kur
git pull --rebase --autostash                                         # guncelle
.venv/bin/python <hattın adımları, bat\<proje>\calistir.bat içinde>   # calistir
git add "<proje klasörü>" site/public/projeler/<slug> && git commit && git push
```

`.evds_key` yine kökte; hatlar `TTO_EVDS_KEY` ortam değişkenini de kabul eder:
`export TTO_EVDS_KEY=...`

## Sorun çıkarsa

- **`git push` "rejected"** → önce `guncelle.bat` (pull), sonra tekrar push. Cron botu
  (veri-bot) Cuma sabahları commit atar; siz de o gün push ederseniz çakışır.
- **`[HATA] Sanal ortam yok`** → o projenin `kur.bat`'ı (ya da `guncelle.bat --kur <hat>`)
  çalıştırılmamış.
- **`ModuleNotFoundError` / `adım 1 düştü`** → aynı sebep: `guncelle.bat --kur <hat>`.
  `guncelle.py` proje klasöründeki `.venv`'i kendiliğinden kullanır; venv yoksa sistem
  python'una düşer ve paketler orada olmayabilir.
- **Pano açılmıyor, "eksik paket" diyor** → `guncelle.bat --kur hazine` (ya da `fx`).
- **Pano açılıyor ama veri eski** → panolar veri üretmez: `guncelle.bat hazine --tam`.
- **Port meşgul** → `panel.bat hazine --port 8060`.
- **`[UYARI] EVDS anahtari bulunamadi`** → adım 4 eksik.
- **`[DURDU] gomulu anahtar`** → bir dosyaya `KEY = "..."` biçiminde anahtar yazılmış;
  push kasıtlı olarak reddedildi. Anahtarı `.evds_key`'e taşıyın.
