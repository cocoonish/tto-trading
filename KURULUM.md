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

## 5. Bir projeyi kur ve çalıştır

`bat\<proje>\` klasörüne gidin, sırayla çift tıklayın:

1. **`kur.bat`** — sanal ortam + bağımlılıklar (ilk seferde birkaç dakika)
2. **`calistir.bat`** — hattı koşturur
3. **`push.bat`** — çıktıyı GitHub'a gönderir

Sonraki günlerde: **`guncelle.bat`** (pull) → `calistir.bat` → `push.bat`.

**İlk deneme için `bat\tcmb-net-rezerv\`** — en basit ve en hızlı hat.

## 6. Proje başına özel notlar

- **`fx-haber-endeksi`** — GDELT/haber önbelleği (`indices/data/*_cache.json`) repoya
  girmez, çünkü ~35 MB ve her koşuda büyür. Yeni bilgisayarda **ilk `calistir.bat`
  52 haftalık geçmişi sıfırdan çeker ve FinBERT ile skorlar: 2-4 saat sürebilir.**
  Sonraki koşular yalnız yeni haftaları çeker (dakikalar). Ayrıca `kur.bat` torch +
  transformers indirir (~2 GB). Sabır isteyen tek hat bu.
- **`yiyecek-marj`** — `kur.bat` sonrası **bir kez** şu komut (MEDAS hasadı için tarayıcı):
  ```
  Research\marj\.venv\Scripts\python.exe -m playwright install chromium
  ```
  `Research\marj\data\raw\medas_*.xls` dosyaları repoyla geliyorsa hasat atlanır ve bu
  adım gerekmez.
- **`hazine-ihrac`** — `calistir.bat` scraper'ı da koşturur (Hazine sitesini tarar);
  ilk koşu 10-20 dakika, sonrakiler kısa (işlenen URL'ler önbelleklenir).
- Diğer dördü (`tcmb-net-rezerv`, `usdtry-deval`, `try-reer`, `yabanci-pozisyon`) yalnız
  EVDS'e gider, dakikalar içinde biter.

## 7. Site (isteğe bağlı — sadece sayfaları yerelde görmek isterseniz)

Node.js (nodejs.org, LTS) kurun, sonra:

```
cd site
npm install
npm run dev
```

Tarayıcıda `http://localhost:4321`. Bat'lar siteyi **build etmez**; site GitHub'a push
edilince yayına giren tarafta derlenir. Yerelde bakmak istemiyorsanız bu adımı atlayın.

## Windows dışı (macOS/Linux)

Bat'lar çalışmaz ama mantık aynıdır; her komut proje klasöründe:

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
- **`[HATA] Sanal ortam yok`** → o projenin `kur.bat`'ı çalıştırılmamış.
- **`[UYARI] EVDS anahtari bulunamadi`** → adım 4 eksik.
- **`[DURDU] gomulu anahtar`** → bir dosyaya `KEY = "..."` biçiminde anahtar yazılmış;
  push kasıtlı olarak reddedildi. Anahtarı `.evds_key`'e taşıyın.
