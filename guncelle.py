#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — tüm veri hatlarını tek yerden güncelle.

Kullanım:
  python guncelle.py                    # etkileşimli menü: hangileri, hafif/tam, commit?
  python guncelle.py --hepsi            # 8 hattın hepsi (hafif mod)
  python guncelle.py tcmb reer          # yalnız bunlar
  python guncelle.py --hepsi --tam      # ağır adımlar dahil (FX GDELT+FinBERT, Hazine scraper)
  python guncelle.py --hepsi --commit   # bitince siteye kopyalanan çıktıları commit'le + push
  python guncelle.py --liste            # hatları göster, hiçbir şey koşturma
  python guncelle.py --denetle --hepsi  # KOŞMADAN denetle: eksik paket/anahtar/araç var mı
  python guncelle.py --denetle --hepsi --duzelt   # bulunan eksikleri kur
  python guncelle.py --kur tcmb hazine  # seçilen hatların .venv'ini kur/yenile (requirements)
  python guncelle.py --kur --hepsi      # hepsini kur — yeni bilgisayarda İLK adım
  python guncelle.py --panel hazine     # hattın canlı panelini aç (Dash/Streamlit), Ctrl+C ile kapat

Kip:
  hafif  = cron'un yaptığı: depodaki veriden grafik + ozet.json (dakikalar)
  tam    = hattın kendisi veriyi de çeker (FX: 52 hafta GDELT + FinBERT skorlaması,
           Hazine: scraper). Yerelde tazeleme için bu; cron ağır adımları bilinçli atlar.

Sözleşme:
  · Her hat kendi klasöründe koşar; bir adım düşerse o hat DURUR, siteye kopyalama yapılmaz.
  · Diğer hatlar etkilenmez; sonda özet tablo ve çıkış kodu (biri düştüyse 1).
  · Kopyalama tablosu HATLAR içinde — cron (.github/workflows/veri-guncelle.yml) ile aynı
    kaynak→hedef eşlemesi. Yeni çıktı eklerken ikisini birden güncelle.
  · Yorumlayıcı: her hat, klasöründe .venv varsa ONUN python'uyla koşar (bat/kur.bat ya da
    --kur bunu kurar); yoksa guncelle.py'yi çalıştıran python. Eskiden hep ikincisiydi → bat
    ile venv kurulan Windows'ta sistem python'u tcmb/pdfplumber'ı bulamıyor, ilk hat düşüyordu.
  · EVDS anahtarı — sıra ARTIK HER HATTA AYNI: TTO_EVDS_KEY ortam değişkeni →
    <proje>/.evds_key → kök/.evds_key → kardeş Aktarılacak Projeler/TCMBNetRezerv/.evds_key.
    (2026-08'e kadar dört eski hat yalnız kendi klasörüne bakıyordu; temiz bir klonda
    köke tek dosya koyan kullanıcının o hatları düşüyordu — dördü de bu sıraya çevrildi.)
    Burada yalnız erken uyarı verilir; ortam değişkeni ATANMAZ (atansaydı projeye özel
    anahtar hiç okunmaz, fiilî öncelik hatların ilan ettiği sırayla çelişirdi).
  · Ev stili (site/tools/plotly_stil.py) her koşunun sonunda TEK KEZ uygulanır.
"""
from __future__ import annotations
import argparse, os, re, shutil, subprocess, sys, time
from collections import deque
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

KOK = Path(__file__).resolve().parent
SITE = KOK / "site" / "public" / "projeler"
PY = sys.executable
# Windows'ta yönlendirilmiş/çağrılmış çıktıda cp1254 "→ ✓ Δ" karakterlerinde düşmesin
for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
_COCUK_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


_ANSI = re.compile(r"\033\[[0-9;]*m")
GUNLUK_KLASOR = KOK / "gunlukler"
_GUNLUK = None          # açık dosya tanıtıcısı (yoksa None)


class _Tee:
    """Ekrana basılan her şeyi günlüğe de yaz (renk kodları ayıklanarak).

    Neden: "bazı hatalar aldım" diyen kullanıcının elinde gösterecek bir metin
    kalmıyordu; konsol kapanınca kanıt da gidiyordu. Artık her koşu dosyaya düşer.
    """

    def __init__(self, akis, dosya):
        self.akis, self.dosya = akis, dosya

    def write(self, m):
        self.akis.write(m)
        try:
            self.dosya.write(_ANSI.sub("", m))
        except Exception:
            pass
        return len(m)

    def flush(self):
        self.akis.flush()
        try:
            self.dosya.flush()
        except Exception:
            pass

    def isatty(self):
        return self.akis.isatty()


def gunluk_ac(tut: int = 20) -> Path | None:
    """gunlukler/guncelle-<tarih>.log aç; eskileri buda. Yazılamazsa sessizce geç."""
    global _GUNLUK
    try:
        GUNLUK_KLASOR.mkdir(exist_ok=True)
        yol = GUNLUK_KLASOR / f"guncelle-{datetime.now():%Y%m%d-%H%M%S}.log"
        _GUNLUK = open(yol, "w", encoding="utf-8", errors="replace")
    except OSError:
        return None
    sys.stdout = _Tee(sys.stdout, _GUNLUK)
    sys.stderr = _Tee(sys.stderr, _GUNLUK)
    eskiler = sorted(GUNLUK_KLASOR.glob("guncelle-*.log"))[:-tut]
    for e in eskiler:
        try:
            e.unlink()
        except OSError:
            pass
    return yol


def gunluge_yaz(metin: str):
    """Çocuk sürecin çıktısı: ekrana zaten gitti, dosyaya da düşsün."""
    if _GUNLUK:
        try:
            _GUNLUK.write(_ANSI.sub("", metin) + "\n")
        except Exception:
            pass


def hat_python(h: "Hat") -> str:
    """Hattın yorumlayıcısı: klasöründe .venv varsa onun python'u, yoksa bu python."""
    d = KOK / h.klasor
    for aday in (d / ".venv" / "Scripts" / "python.exe", d / ".venv" / "bin" / "python"):
        if aday.exists():
            return str(aday)
    return PY


def kur(h: "Hat") -> bool:
    """bat/<proje>/kur.bat'ın eşleniği: .venv oluştur + requirements.txt yükle."""
    d = KOK / h.klasor
    venv = d / ".venv"
    vpy = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not vpy.exists():
        print(f"    [1/2] sanal ortam oluşturuluyor: {venv}")
        if subprocess.run([PY, "-m", "venv", str(venv)]).returncode != 0:
            print(_renk("    ✗ venv oluşturulamadı", 31)); return False
    else:
        print("    [1/2] sanal ortam mevcut")
    req = d / "requirements.txt"
    if not req.exists():
        print(_renk("    [UYARI] requirements.txt yok, bağımlılık yüklenmedi", 33)); return True
    print("    [2/2] bağımlılıklar yükleniyor (requirements.txt)")
    subprocess.run([str(vpy), "-m", "pip", "install", "--upgrade", "pip", "-q"], env=_COCUK_ENV)
    r = subprocess.run([str(vpy), "-m", "pip", "install", "-r", str(req)], env=_COCUK_ENV)
    if r.returncode != 0:
        print(_renk("    ✗ pip install başarısız", 31)); return False
    print(_renk("    ✓ kurulum tamam", 32)); return True


@dataclass
class Hat:
    ad: str                        # kısa ad (komut satırında)
    baslik: str
    klasor: Path                   # kökten göreli
    slug: str                      # site/public/projeler/<slug>
    hafif: list[str]               # cron ile aynı adımlar
    tam: list[str]                 # ağır hat (boşsa hafif ile aynı)
    kopya: dict[str, str]          # kaynak (klasöre göreli) → hedef dosya adı
    not_: str = ""
    # ozet.json'da veri tarihini taşıyan alan(lar) — tazelik denetimi.
    # LİSTE olmasının sebebi: bir hattın farklı frekanslı birden çok çıktısı
    # olabiliyor ve biri ilerlerken diğeri sessizce donabiliyor (TCMB'de rezerv
    # serisi ilerlerken altın/akım tarafı taşımaya girebilir). Tek anahtara
    # bakmak o durumda "veri tazelendi" der.
    tarih_anahtarlari: tuple[str, ...] = ("_tarih",)
    panel: list[str] = field(default_factory=list)  # canlı panel komutu (python'dan sonraki argümanlar)

    def adimlar(self, tam: bool) -> list[str]:
        return (self.tam or self.hafif) if tam else self.hafif


P = Path("Aktarılacak Projeler")
HATLAR: list[Hat] = [
    Hat("tcmb", "TCMB Net Rezerv", P / "TCMBNetRezerv", "tcmb-net-rezerv",
        # altin_etkisi.py, net_rezerv.py'nin yazdığı gunluk.csv'den
        # altin_etkisi.csv üretir (arındırma sisteminin bağımsız çıktısı);
        # grafik.py altı HTML üretir. Sıra bağlayıcıdır.
        ["net_rezerv.py", "altin_etkisi.py", "grafik.py --no-open",
         "ozet_uret.py"], [],
        {"tcmb_rezerv_grafik.html": "grafik.html",
         "brut_kirilim.html": "brut_kirilim.html",
         "altin_ayristirma.html": "altin_ayristirma.html",
         "akim.html": "akim.html",
         "swap.html": "swap.html",
         "tanim_farki.html": "tanim_farki.html"},
        tarih_anahtarlari=("g_tarih", "ak_tarih")),
    Hat("usdtry", "USDTRY Devalüasyon", P / "USDTRYDeval", "usdtry-deval",
        ["usdtry_deval_plotly.py", "usdtry_weekly_trends.py", "usdtry_monthly_trends.py", "ozet_uret.py"], [],
        {"usdtry_deval.html": "usdtry_deval.html", "usdtry_deval_3m.html": "usdtry_deval_3m.html",
         "usdtry_deval_6m.html": "usdtry_deval_6m.html", "usdtry_deval_seg.html": "usdtry_deval_seg.html",
         "usdtry_weekly_trends.html": "usdtry_weekly.html", "usdtry_monthly_trends.html": "usdtry_monthly.html"}),
    Hat("reer", "TRY REER", P / "TRYREER", "try-reer",
        ["main.py", "usdtry_reer_analysis.py", "ozet_uret.py"], [],
        {"reer_analysis.html": "reer_analysis.html", "usdtry_regression_10y.html": "redk_degisim_regresyon.html",
         "usdtry_regression_5y.html": "redk_degisim_regresyon_5y.html", "usdtry_regression_3m.html": "redk_degisim_regresyon_3m.html",
         "usdtry_reer_analysis_10y.html": "redk_usdtry_analiz_10y.html", "usdtry_reer_analysis_5y.html": "redk_usdtry_analiz_5y.html"}),
    Hat("yabanci", "Yabancı Pozisyonu", P / "ForeignHoldings", "yabanci-pozisyon",
        ["main.py", "ozet_uret.py"], [],
        {"charts/cumulative_chart.html": "kumulatif.html", "charts/ytd_dibs.html": "ytd_dibs.html",
         "charts/ytd_hisse.html": "ytd_hisse.html", "charts/ytd_toplam.html": "ytd_toplam.html"}),
    Hat("hazine", "Hazine İhraç", P / "hazineihrac", "hazine-ihrac",
        ["web_cikti_tahmin.py", "tablo_uret.py", "ozet_uret.py"],
        ["main.py", "web_cikti_tahmin.py", "tablo_uret.py", "ozet_uret.py"],
        {f"{f}.html": f"{f}.html" for f in ["planlanan_ihraclar", "tahmin_dogrulama", "tahmin_aylik",
         "strateji_revizyon", "faiz_gelisimi", "fiyat_araligi", "ihrac_hacmi", "ihrac_tempo", "ihrac_usd",
         "talep_analizi", "vade_dagilimi", "hedef_gerceklesme", "vade_analizi"]}
        | {"tablolar.json": "tablolar.json"},
        "tam kip: Hazine sitesini tarar (scraper), ilk koşu 10-20 dk",
        panel=["dashboard.py"]),            # Dash → http://127.0.0.1:8050
    Hat("fx", "FX Haber Endeksi", P / "indices", "fx-haber-endeksi",
        ["web_cikti.py", "ozet_uret.py"],
        ["run.py --fetch-history", "ozet_uret.py"],
        {"cikti/*.html": "*"},
        "tam kip: GDELT + FinBERT — ilk koşu saatler, sonrası dakikalar",
        panel=["-m", "streamlit", "run", "dashboard.py"]),  # Streamlit → http://localhost:8501
    Hat("enflasyon", "Enflasyon Panosu", P / "Enflasyon", "enflasyon",
        # veri.py EVDS'ten çeker (TTL'li önbellek), metrik.py momentum/çekirdek/
        # katkı/dağılım/baz/reel faiz hesaplarını yapar ve EVDS'in kendi y/y
        # serisiyle ÇAPRAZ DOĞRULAR (0,05 puan eşiği aşılırsa hat DURUR),
        # grafik.py dokuz şekil üretir. Sıra bağlayıcıdır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        tarih_anahtarlari=("_tarih", "faiz_gun")),
    Hat("kredi", "Kredi & Parasal Büyüklükler", P / "Kredi", "kredi-parasal",
        # veri.py EVDS3'ten dört frekansta çeker (haftalık para ve banka, iş günü
        # kur/bilanço/APİ, aylık KKM ve banka türü, üç aylık BKEA) ve aile bazlı
        # tazelik + kimlik denetimlerini yapar. metrik.py kur etkisinden
        # arındırılmış kredi büyümesini ZİNCİRLEME kurar, Laspeyres ayrıştırmasını
        # kimlik denetiminden geçirir ve üç bağımsız doğrulama koşturur; ham para
        # arzı sınavı (seviye tablosu ↔ TCMB'nin kendi endeksi) tutmazsa hat DURUR.
        # grafik.py dokuz şekil üretir. Sıra bağlayıcıdır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        # Üç ayrı frekans, üç ayrı donma riski: haftalık kredi ilerlerken aylık
        # KKM/banka türü tarafı sessizce durabiliyor. Tek anahtara bakmak yetmez.
        tarih_anahtarlari=("_tarih", "gun_tarih", "ay_tarih")),
    Hat("fonlama", "TCMB Fonlama & Likidite", P / "Fonlama", "fonlama-likidite",
        # veri.py EVDS3'ten çeker (12 saat TTL'li önbellek; iş günü serileri
        # 366 günlük, haftalık seriler 900 haftalık parçalar hâlinde — EVDS
        # 1000 satırdan sonrasını SESSİZCE kırpıyor). metrik.py AOFM'yi tabanı
        # yokken geçersiz işaretler, AOSM'yi (bu çalışmanın türetmesi) kurar,
        # koridor konumunu ve örtük sıkılaştırma dönemlerini çıkarır ve dört
        # BAĞIMSIZ DOĞRULAMA yapar (net fonlama kimliği · günlük politika
        # kotasyonu ↔ EVDS'in aylık BIS serisi · TLREF ↔ BİST gecelik repo AOF ·
        # rezerv hattıyla swap tutarlılığı) — biri düşerse hat DURUR.
        # grafik.py sekiz şekil üretir. Sıra bağlayıcıdır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        # Üç ayrı frekans var ve biri ilerlerken diğeri donabilir: APİ günlük,
        # haftalık faiz Cuma, ZK tabanı bir hafta daha geriden. Tek anahtara
        # bakmak "veri tazelendi" derdi.
        tarih_anahtarlari=("_tarih", "hafta_kisa", "zk_taban_tarih")),
    Hat("marj", "Yiyecek Hizmetleri Marjı", Path("Research/marj"), "yiyecek-hizmetleri-marj",
        ["src/web_cikti.py", "src/ozet_uret.py"],
        ["src/run_all.py", "src/web_cikti.py", "src/ozet_uret.py"],
        {"output/web/*.html": "*", "output/ozet.json": "ozet.json"},
        "tam kip: EVDS/TÜİK'ten yeniden çeker; MEDAS için Playwright"),
]
HAT = {h.ad: h for h in HATLAR}


def _renk(m, k):  # k: 32 yeşil, 31 kırmızı, 33 sarı, 36 camgöbeği
    return f"\033[{k}m{m}\033[0m" if sys.stdout.isatty() else m


EVDS_HATLAR = {"tcmb", "usdtry", "reer", "yabanci", "marj", "enflasyon",
               "kredi", "fonlama"}
# Liste sütun genişliği hat adlarından türetilir — yeni bir uzun ad eklendiğinde
# hizalama sessizce bozulmasın ("enflasyon" 9 karakter, eski sabit 8'di).
_AD_G = max(len(h.ad) for h in HATLAR) + 1
# Başlık sütunu da hat listesinden türetilir; sabit 26 karakterdi ve
# "Kredi & Parasal Büyüklükler" eklenince hizalama sessizce bozuluyordu.
_BASLIK_G = max(len(h.baslik) for h in HATLAR) + 1


def anahtar_uyar(secilen: list["Hat"]):
    if os.environ.get("TTO_EVDS_KEY"): return
    # DİKKAT: burada TTO_EVDS_KEY ATANMAZ. Atansaydı kökteki dosya <proje>/.evds_key'i
    # ezer ve hatların ilan ettiği arama sırası sessizce tersine dönerdi.
    if (KOK / ".evds_key").exists():
        return
    # Arama sırası artık HER hatta aynı (proje → kök → kardeş TCMBNetRezerv);
    # tek doğru yer hat_anahtari(), burada da o kullanılır. Eskiden bu liste
    # elle tutulan bir istisna kümesine bakıyordu ve yanlış alarm veriyordu.
    eksik = [h.ad for h in secilen if h.ad in EVDS_HATLAR and not hat_anahtari(h)]
    if eksik:
        print(_renk(f"  [UYARI] EVDS anahtarı yok: {', '.join(eksik)} hatları düşecek. "
                    "Çözüm: kök klasöre .evds_key dosyası (tek satır anahtar) ya da TTO_EVDS_KEY ortam değişkeni.", 33))


def yukseklik_denetimi(h: "Hat") -> str | None:
    """cikti/yukseklikler.json ↔ MDX'teki GrafikEmbed yukseklik={} uyuşuyor mu?

    Grafik yüksekliği panel sayısı, alt başlık satırı ve lejant satırından
    türetiliyor; dipnot bir satır uzayınca figür yükselir ama MDX'teki sayı elle
    yazıldığı için sessizce ayrışır ve iframe içinde grafik kırpılır. Bu denetim
    o ayrışmayı GÖRÜNÜR yapar.
    """
    import json, re
    y = KOK / h.klasor / "cikti" / "yukseklikler.json"
    mdx = KOK / "site" / "src" / "content" / "projeler" / f"{h.slug}.mdx"
    if not y.exists() or not mdx.exists():
        return None
    try:
        bek = json.loads(y.read_text(encoding="utf-8"))
        met = mdx.read_text(encoding="utf-8")
    except Exception:
        return None
    sapan, yok = [], []
    for blok in re.findall(r"<GrafikEmbed[^>]*?/>", met, re.S):
        m_src = re.search(r'src="/projeler/[^/]+/([^"]+)"', blok)
        m_yuk = re.search(r"yukseklik=\{(\d+)\}", blok)
        if not m_src or not m_yuk:
            continue
        dosya, gercek = m_src.group(1), int(m_yuk.group(1))
        if dosya not in bek:
            yok.append(dosya)
        elif int(bek[dosya]) != gercek:
            sapan.append(f"{dosya}: MDX {gercek} ≠ üretim {int(bek[dosya])}")
    if sapan or yok:
        p = []
        if sapan:
            p.append("yükseklik SAPMASI — " + "; ".join(sapan))
        if yok:
            p.append("MDX'te var, üretimde yok: " + ", ".join(yok))
        return " · ".join(p)
    return None


def _ozet_tarih(h: Hat) -> dict[str, str] | None:
    """Sitedeki ozet.json'daki veri tarih(ler)i — koşu öncesi/sonrası kıyas."""
    import json
    y = SITE / h.slug / "ozet.json"
    try:
        d = json.load(open(y, encoding="utf-8"))
    except Exception:
        return None
    return {a: str(d.get(a)) for a in h.tarih_anahtarlari}


def _tarih_ozeti(d: dict[str, str] | None) -> str:
    if not d:
        return "?"
    return " / ".join(d.values()) if len(d) > 1 else next(iter(d.values()))


# ─────────────────────────────── ÖN DENETİM ───────────────────────────────
# "Bende çalışıyor, sende çalışmıyor"un neredeyse tamamı tek bir eksik pakettir:
# hattın klasöründe .venv yoksa sistem python'uyla koşulur ve o python'da örneğin
# statsmodels yoksa ekran traceback'le dolar. Aşağısı hattı BAŞLATMADAN önce
# yorumlayıcıyı yoklar ve tek satırlık çözümü yazar.

_PAKET_KODU = (
    "import sys\n"
    "from importlib.metadata import distribution, PackageNotFoundError\n"
    "for a in sys.argv[1:]:\n"
    "    try: distribution(a)\n"
    "    except PackageNotFoundError: print(a)\n"
)
# Dağıtım adı ↔ import adı ayrışması (python-dateutil→dateutil, bs4 vb.) bizi
# ilgilendirmiyor: importlib.metadata DAĞITIM adına bakar, requirements.txt de
# dağıtım adı yazar. İkisi aynı sözlükten konuşur.


def _req_paketler(d: Path) -> list[str]:
    """requirements.txt → dağıtım adları (sürüm, ekstra, koşul, yorum ayıklanmış)."""
    req = d / "requirements.txt"
    if not req.exists():
        return []
    adlar = []
    for satir in req.read_text(encoding="utf-8").splitlines():
        s = satir.split("#")[0].strip()
        if not s or s.startswith("-"):        # -r include, --index-url …
            continue
        s = re.split(r"[<>=!~;\[ ]", s, 1)[0].strip()
        if s:
            adlar.append(s)
    return adlar


def eksik_paketler(h: "Hat") -> list[str] | None:
    """Hattı koşacak yorumlayıcıda requirements'tan eksik olanlar.

    None = denetlenemedi (yorumlayıcı çalışmadı) — bu da bir bulgudur.
    """
    paketler = _req_paketler(KOK / h.klasor)
    if not paketler:
        return []
    try:
        r = subprocess.run([hat_python(h), "-c", _PAKET_KODU, *paketler],
                           capture_output=True, text=True, env=_COCUK_ENV, timeout=120)
    except Exception:
        return None
    if r.returncode != 0:
        return None
    return [x for x in r.stdout.split() if x]


def hat_anahtari(h: "Hat") -> str | None:
    """Bu hattın anahtarı nereden gelecek? Sıra HER hatta aynı (2026-08 itibarıyla
    dört eski hat da bu sıraya çevrildi): ortam → proje → kök → kardeş TCMBNetRezerv.
    """
    if os.environ.get("TTO_EVDS_KEY"):
        return "ortam"
    for etiket, yol in (("proje", KOK / h.klasor / ".evds_key"),
                        ("kök", KOK / ".evds_key"),
                        ("kardeş", KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key")):
        try:
            if yol.exists() and yol.read_text(encoding="utf-8").strip():
                return etiket
        except OSError:
            continue
    return None


def anahtar_nerede() -> str | None:
    """EVDS anahtarı nerede bulundu? Arama sırası veri.py ile aynı."""
    if os.environ.get("TTO_EVDS_KEY"):
        return "TTO_EVDS_KEY ortam değişkeni"
    if (KOK / ".evds_key").exists():
        return "kök .evds_key"
    proje = sorted(p.parent.name for p in KOK.glob("*/*/.evds_key"))
    if proje:
        ek = "" if len(proje) < 4 else f" (+{len(proje) - 3})"
        return "proje: " + ", ".join(proje[:3]) + ek
    return None


def _eksik_scriptler(h: "Hat", tam: bool) -> list[str]:
    """Adım satırlarının ilk parçası bir .py ise, dosya gerçekten duruyor mu?"""
    d = KOK / h.klasor
    yok = []
    for adim in h.adimlar(tam):
        ilk = adim.split()[0]
        if ilk.endswith(".py") and not (d / ilk).exists():
            yok.append(ilk)
    return yok


def denetle(secilen: list["Hat"], tam: bool, duzelt: bool) -> int:
    """Hiçbir şey koşturmadan 'bu makinede güncelleme + yayın patlar mı?' der."""
    print(f"{'═' * 78}\n  ÖN DENETİM · {len(secilen)} hat · kip: "
          f"{'TAM' if tam else 'hafif'}\n{'═' * 78}")

    engel: list[str] = []          # güncellemeyi düşürecekler
    uyari: list[str] = []          # düşürmez ama bilinmeli

    print("\n▶ Ortam")
    print(f"  Python   {sys.version.split()[0]}  ({PY})")
    if sys.version_info < (3, 10):
        engel.append(f"Python 3.10+ gerekir (mevcut {sys.version_info[0]}.{sys.version_info[1]})")
    for arac, ne in (("git", "commit/push"), ("node", "site derlemesi"), ("npm", "site derlemesi")):
        yol = shutil.which(arac + ".cmd" if os.name == "nt" and arac == "npm" else arac) or shutil.which(arac)
        print(f"  {arac:8s} {'✓ ' + yol if yol else _renk('YOK — ' + ne + ' yapılamaz', 33)}")
        if not yol and arac == "git":
            uyari.append("git yok: --commit ve yayinla.py çalışmaz")
        if not yol and arac in ("node", "npm"):
            uyari.append(f"{arac} yok: yayinla.py yerel derlemeyi atlar")
    nerede = anahtar_nerede()
    print(f"  EVDS     {'✓ anahtar (' + nerede + ')' if nerede else _renk('anahtar YOK', 31)}")

    print(f"\n▶ Hatlar\n  {'hat':{_AD_G}s} {'yorumlayıcı':12s} {'anahtar':8s} "
          f"{'paket':22s} script")
    for h in secilen:
        d = KOK / h.klasor
        if not d.exists():
            print(_renk(f"  {h.ad:{_AD_G}s} klasör YOK: {h.klasor}", 31))
            engel.append(f"{h.ad}: klasör yok ({h.klasor})")
            continue
        yorum = ".venv" if hat_python(h) != PY else "sistem"
        if h.ad in EVDS_HATLAR:
            k = hat_anahtari(h)
            anahtar_m = k if k else _renk("YOK", 31)
            if not k:
                engel.append(f"{h.ad}: EVDS anahtarı yok — köke .evds_key koyun "
                             "ya da TTO_EVDS_KEY atayın")
        else:
            anahtar_m = "—"
        eksik = eksik_paketler(h)
        yok = _eksik_scriptler(h, tam)
        if eksik is None:
            paket_m, kotu = _renk("yorumlayıcı çalışmadı", 31), True
            engel.append(f"{h.ad}: yorumlayıcı çalışmıyor — python guncelle.py --kur {h.ad}")
        elif eksik:
            paket_m, kotu = _renk(f"EKSİK: {', '.join(eksik[:3])}"
                                  + (f" +{len(eksik) - 3}" if len(eksik) > 3 else ""), 31), True
            engel.append(f"{h.ad}: eksik paket ({len(eksik)}) — python guncelle.py --kur {h.ad}")
        else:
            paket_m, kotu = _renk("tam", 32), False
        script_m = _renk("EKSİK: " + ", ".join(yok), 31) if yok else "✓"
        if yok:
            engel.append(f"{h.ad}: script yok — {', '.join(yok)}")
        print(f"  {h.ad:{_AD_G}s} {yorum:12s} {anahtar_m:8s} {paket_m:22s} {script_m}")
        if duzelt and (eksik or eksik is None):
            print(f"    → kuruluyor ({h.ad})")
            if kur(h):
                kalan = eksik_paketler(h)
                if not kalan:
                    engel = [x for x in engel if not x.startswith(f"{h.ad}:")]
                    print(_renk("    ✓ giderildi", 32))

    print("\n▶ Site")
    site = KOK / "site"
    nm = site / "node_modules"
    print(f"  node_modules  {'✓' if nm.exists() else _renk('yok — ilk yayında npm install koşar (dakikalar)', 33)}")
    if not nm.exists():
        uyari.append("site/node_modules yok: ilk yayın uzun sürer")
    klon = KOK.parent / "TTO Trading Yayin"
    print(f"  yayın klonu   {'✓ ' + str(klon) if (klon / '.git').exists() else 'yok — yayinla.py klonlayacak'}")

    print(f"\n{'═' * 78}")
    for u in uyari:
        print(_renk(f"  [uyarı]  {u}", 33))
    if engel:
        print(_renk(f"  {len(engel)} ENGEL — güncelleme bu haliyle hata verir:", 31))
        for e in engel:
            print(_renk(f"    · {e}", 31))
        print("\n  Hepsini birden gidermek için:  python guncelle.py --denetle --hepsi --duzelt")
        return 1
    print(_renk("  Temiz — güncelleme ve yayın hatasız koşmalı.", 32))
    return 0


def _adim_kos(komut: list[str], cwd: Path) -> tuple[int, list[str]]:
    """Adımı koştur; çıktıyı ekrana AKTARIRKEN günlüğe yaz ve son 40 satırı tut.

    subprocess.run(...) ile çocuğun çıktısı doğrudan terminale gidiyordu: canlı
    görünüyordu ama hiçbir yere kaydedilmiyor, hata mesajı özete de taşınamıyordu.
    """
    p = subprocess.Popen(komut, cwd=str(cwd), env=_COCUK_ENV,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, encoding="utf-8", errors="replace")
    son: deque[str] = deque(maxlen=40)
    for satir in p.stdout:                       # satır satır: canlılık korunur
        satir = satir.rstrip("\n")
        # print() değil: sys.stdout zaten Tee ise iki kez yazılırdı.
        sys.__stdout__.write(satir + "\n")
        sys.__stdout__.flush()
        gunluge_yaz(satir)
        son.append(satir)
    p.wait()
    return p.returncode, list(son)


def kos(h: Hat, tam: bool) -> tuple[bool, str, float]:
    d = KOK / h.klasor
    t0 = time.time()
    eski_tarih = _ozet_tarih(h)
    py = hat_python(h)
    if py != PY:
        print(f"    (yorumlayıcı: {Path(py).relative_to(KOK) if py.startswith(str(KOK)) else py})")
    # Koşmadan önce yorumlayıcıyı yokla: eksik paket, sayfalarca traceback yerine
    # tek satırlık çözüm olarak görünsün. (Ekstra maliyet ~0,1 sn/hat.)
    eksik = eksik_paketler(h)
    if eksik is None:
        return False, (f"yorumlayıcı çalışmıyor ({py}) — çözüm: python guncelle.py "
                       f"--kur {h.ad}"), time.time() - t0
    if eksik:
        nerede = ".venv" if py != PY else "sistem python'u"
        return False, (f"eksik paket [{nerede}]: {', '.join(eksik[:4])}"
                       + (f" +{len(eksik) - 4}" if len(eksik) > 4 else "")
                       + f" — çözüm: python guncelle.py --kur {h.ad}"), time.time() - t0
    for i, adim in enumerate(h.adimlar(tam), 1):
        print(f"    [{i}] {adim}")
        kod, son = _adim_kos([py, *adim.split()], d)
        if kod != 0:
            ipucu = ""
            if py == PY and not (d / ".venv").exists():
                ipucu = f" — bağımlılık eksikse: python guncelle.py --kur {h.ad}  (ya da bat\\{h.slug}\\kur.bat)"
            # Hatanın SON satırı özete taşınır: kullanıcı yüzlerce satır yukarı
            # kaydırmadan sebebi görsün ("adım 2 düştü" tek başına teşhis değil).
            oz = next((x for x in reversed(son) if x.strip()), "")
            if oz:
                ipucu += f"  ⟨{oz.strip()[:110]}⟩"
            return False, f"adım {i} düştü: {adim}{ipucu}", time.time() - t0
    # siteye kopyala
    hedef = SITE / h.slug
    hedef.mkdir(parents=True, exist_ok=True)
    n = 0
    for kaynak, ad in h.kopya.items():
        if "*" in kaynak:
            for f in sorted(d.glob(kaynak)):
                shutil.copy2(f, hedef / (f.name if ad == "*" else ad)); n += 1
        else:
            src = d / kaynak
            if not src.exists():
                return False, f"çıktı yok: {kaynak}", time.time() - t0
            shutil.copy2(src, hedef / ad); n += 1
    # ozet.json (marj'da kopya tablosunda; diğerlerinde klasör kökünde)
    oz = d / "ozet.json"
    if oz.exists() and "output/ozet.json" not in h.kopya:
        shutil.copy2(oz, hedef / "ozet.json"); n += 1

    # TAZELİK DENETİMİ — "koştu ve kopyaladı" yetmez, veri tarihi ilerlemiş mi?
    # Aynıysa hata DEĞİL (kaynak yeni veri yayımlamamış olabilir: REER aylık, TCMB
    # haftalık) ama görünür uyarı: TCMB'de net_rezerv.py CSV yazmadığı için hat
    # 3 hafta "✓" göründü, veri 03.08'de kaldı. Bu satır o hatayı yakalar.
    # Anahtarlardan HERHANGİ BİRİ ilerlemediyse uyarılır: bir hattın farklı
    # frekanslı çıktılarından biri donarken diğeri ilerleyebiliyor.
    yuk = yukseklik_denetimi(h)
    if yuk:
        print(_renk(f"    [UYARI] {yuk}", 33))

    yeni_tarih = _ozet_tarih(h)
    y, e = _tarih_ozeti(yeni_tarih), _tarih_ozeti(eski_tarih)
    if yeni_tarih and eski_tarih:
        donan = [a for a in h.tarih_anahtarlari
                 if yeni_tarih.get(a) == eski_tarih.get(a)]
        if donan:
            etiket = ("hepsi" if len(donan) == len(h.tarih_anahtarlari)
                      else ", ".join(donan))
            return True, (f"{n} dosya kopyalandı — "
                          + _renk(f"veri tarihi DEĞİŞMEDİ ({etiket}): {y}", 33)), time.time() - t0
    return True, f"{n} dosya kopyalandı · veri {e} → {y}", time.time() - t0


def panel(h: Hat) -> int:
    """Hattın canlı panelini (Dash/Streamlit) aç; Ctrl+C kapatır."""
    if not h.panel:
        print(f"  {h.baslik} için panel tanımlı değil (paneli olanlar: "
              f"{', '.join(x.ad for x in HATLAR if x.panel)})"); return 2
    d = KOK / h.klasor
    py = hat_python(h)
    print(f"\n▶ {h.baslik} — panel: {' '.join(h.panel)}  (durdurmak için Ctrl+C)")
    try:
        return subprocess.run([py, *h.panel], cwd=d, env=_COCUK_ENV).returncode
    except KeyboardInterrupt:
        print("\n  panel kapatıldı"); return 0


def ev_stili():
    print("\n▶ Ev stili (plotly_stil.py --hepsi)")
    r = subprocess.run([PY, str(KOK / "site" / "tools" / "plotly_stil.py"), "--hepsi"],
                       cwd=KOK, capture_output=True, text=True)
    n = r.stdout.count("güncellendi")
    print(f"    {n} grafik ev stiline geçirildi")


def commit_push(secilen: list[Hat]):
    print("\n▶ Commit + push")
    yollar = [str(SITE / h.slug) for h in secilen] + [str(KOK / h.klasor) for h in secilen]
    subprocess.run(["git", "add", "-A", *yollar], cwd=KOK)
    # anahtar taraması — eklenen satırlarda gömülü kimlik bilgisi
    d = subprocess.run(["git", "diff", "--cached"], cwd=KOK, capture_output=True, text=True).stdout
    import re
    if re.search(r'^\+.*(?:KEY|TOKEN|SECRET|PASSWORD)\s*=\s*["\'][A-Za-z0-9]{6}', d, re.M | re.I):
        print(_renk("  [DURDU] stage'de gömülü kimlik bilgisine benzeyen satır var; commit yapılmadı.", 31))
        subprocess.run(["git", "reset", "-q"], cwd=KOK); return False
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=KOK).returncode == 0:
        print("    değişiklik yok"); return True
    adlar = ", ".join(h.ad for h in secilen)
    c = subprocess.run(["git", "commit", "-q", "-m", f"veri: {adlar} güncellendi (guncelle.py)"],
                       cwd=KOK, capture_output=True, text=True)
    if c.returncode != 0:
        print(_renk("  ✗ commit düştü", 31))
        print((c.stderr or c.stdout or "").strip()[-400:])
        ad = subprocess.run(["git", "config", "user.name"], cwd=KOK,
                            capture_output=True, text=True).stdout.strip()
        posta = subprocess.run(["git", "config", "user.email"], cwd=KOK,
                               capture_output=True, text=True).stdout.strip()
        if not ad or not posta:
            print(_renk('  Sebep: git kimliği ayarlı değil. Çözüm:\n'
                        '    git config --global user.name "Adınız"\n'
                        '    git config --global user.email "eposta@ornek.com"', 33))
        return False
    r = subprocess.run(["git", "push"], cwd=KOK)
    if r.returncode != 0:
        # Eskiden bu dönüş değeri main()'de yok sayılıyordu: push düşse bile
        # çıkış kodu 0 kalıyor, kullanıcı "gitti" sanıyordu.
        print(_renk("  ✗ push başarısız — commit YEREL kaldı. "
                    "Elle: git push  (ya da git pull --rebase && git push)", 31))
        return False
    return True


def menu() -> tuple[list[Hat], bool, bool]:
    print("\nHatlar:")
    for i, h in enumerate(HATLAR, 1):
        print(f"  {i}. {h.ad:{_AD_G}s} {h.baslik:{_BASLIK_G}s} {_renk(h.not_, 36) if h.not_ else ''}")
    print("  0. hepsi")
    print("  (kurulum: --kur · canlı panel: --panel hazine|fx · yardım: --help)")
    sec = input("\nHangileri? (numara/ad, virgülle; boş = hepsi): ").strip()
    if not sec or sec == "0":
        secilen = list(HATLAR)
    else:
        secilen = []
        for p in sec.replace(" ", "").split(","):
            if p.isdigit() and 1 <= int(p) <= len(HATLAR): secilen.append(HATLAR[int(p) - 1])
            elif p in HAT: secilen.append(HAT[p])
            else: print(f"  ? {p} tanınmadı, atlandı")
    tam = input("Kip — [h]afif (dakikalar) / [t]am (veri de çekilir, FX saatler): ").strip().lower().startswith("t")
    cm = input("Bitince commit + push? [e/H]: ").strip().lower().startswith("e")
    return secilen, tam, cm


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hatlar", nargs="*", help="kısa adlar: " + " ".join(HAT))
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--tam", action="store_true", help="ağır adımlar dahil")
    ap.add_argument("--commit", action="store_true", help="bitince commit + push")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--kur", action="store_true", help="seçilen hatların .venv + requirements kurulumu (hat koşturmaz)")
    ap.add_argument("--panel", action="store_true", help="seçilen tek hattın canlı panelini aç (hazine: Dash, fx: Streamlit)")
    ap.add_argument("--denetle", action="store_true",
                    help="hiçbir şey koşturmadan ortamı denetle: python, git/node, EVDS anahtarı, "
                         "her hattın yorumlayıcısı ve paketleri")
    ap.add_argument("--duzelt", action="store_true",
                    help="--denetle ile: eksik bulunan hatların kurulumunu yap")
    a = ap.parse_args()
    gunluk = gunluk_ac()

    if a.liste:
        for h in HATLAR:
            print(f"{h.ad:{_AD_G}s} {h.baslik:{_BASLIK_G}s} hafif: {' → '.join(h.hafif)}")
            # Sütun genişliği hat listesinden TÜRETİLİR; sabit yazılırsa uzun
            # başlıklı bir hat eklendiğinde hizalama sessizce bozulur.
            if h.tam: print(f"{'':{_AD_G}s} {'':{_BASLIK_G}s} tam  : {' → '.join(h.tam)}   ({h.not_})")
        return 0

    # --denetle tek başına yazıldığında menüye düşmesin: denetim zaten koşturmuyor,
    # doğal kapsamı "hepsi".
    if a.denetle and not a.hepsi and not a.hatlar:
        return denetle(list(HATLAR), a.tam, a.duzelt)

    if a.hepsi: secilen, tam, cm = list(HATLAR), a.tam, a.commit
    elif a.hatlar:
        yanlis = [x for x in a.hatlar if x not in HAT]
        if yanlis: print(f"tanınmayan hat: {yanlis} — geçerli: {list(HAT)}"); return 2
        secilen, tam, cm = [HAT[x] for x in a.hatlar], a.tam, a.commit
    else:
        secilen, tam, cm = menu()
    if not secilen: print("hat seçilmedi"); return 2

    if a.denetle:
        return denetle(secilen, a.tam, a.duzelt)

    if a.kur:
        print(f"\n{'═'*64}\n  KURULUM · {len(secilen)} hat\n{'═'*64}")
        hata = 0
        for h in secilen:
            print(f"\n▶ {h.baslik}  ({h.klasor})")
            if not kur(h): hata += 1
        return 1 if hata else 0
    if a.panel:
        if len(secilen) != 1:
            print("panel için tek hat seçin, ör: python guncelle.py --panel hazine"); return 2
        return panel(secilen[0])

    # Koşmadan önce hızlı yoklama (~0,1 sn/hat): kullanıcı on dakika bekleyip
    # sonunda "ModuleNotFoundError" görmesin. Windows'ta bat çift tıklamayla
    # sistem python'una düşüyor ve eksik paket en sık hata sebebi.
    sorunlu = []
    for h in secilen:
        e = eksik_paketler(h)
        if e is None or e:
            sorunlu.append(h)
    if sorunlu:
        print(_renk(f"\n  [ÖN DENETİM] bağımlılık eksik: "
                    + ", ".join(h.ad for h in sorunlu), 33))
        cevap = ""
        if sys.stdin.isatty():
            try:
                cevap = input("  Şimdi kurulsun mu? [E/h]: ").strip().lower()
            except EOFError:
                cevap = "h"
        if sys.stdin.isatty() and not cevap.startswith(("h", "n")):
            for h in sorunlu:
                print(f"\n▶ {h.baslik} — kurulum")
                kur(h)
        else:
            print("  Kurulmadan devam ediliyor: bu hatlar tek satırlık hatayla atlanacak "
                  "(kurmak için: python guncelle.py --kur " + " ".join(h.ad for h in sorunlu) + ")")

    anahtar_uyar(secilen)
    print(f"\n{'═'*64}\n  {len(secilen)} hat · kip: {'TAM' if tam else 'hafif'} · commit: {'evet' if cm else 'hayır'}\n{'═'*64}")
    sonuc = []
    for h in secilen:
        print(f"\n▶ {h.baslik}  ({h.klasor})")
        ok, mesaj, sn = kos(h, tam)
        sonuc.append((h, ok, mesaj, sn))
        print(_renk(f"    {'✓' if ok else '✗'} {mesaj}  [{sn:.0f}s]", 32 if ok else 31))

    ev_stili()

    print(f"\n{'═'*64}\n  ÖZET\n{'═'*64}")
    for h, ok, mesaj, sn in sonuc:
        print(f"  {_renk('✓', 32) if ok else _renk('✗', 31)} {h.baslik:{_BASLIK_G}s} {mesaj:34s} {sn:5.0f}s")
    dusen = [h for h, ok, _, _ in sonuc if not ok]
    if gunluk:
        print(f"\n  Kayıt: {gunluk.relative_to(KOK)}"
              + (_renk("   ← hata aldıysanız bu dosyayı paylaşın", 33) if dusen else ""))
    if cm:
        if dusen:
            print(_renk(f"\n  {len(dusen)} hat düştü — commit yine de yapılıyor (başarılı çıktılar için).", 33))
        if not commit_push([h for h, ok, _, _ in sonuc if ok]):
            return 1
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
