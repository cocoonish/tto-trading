#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — tüm veri hatlarını tek yerden güncelle.

Kullanım:
  python guncelle.py                    # etkileşimli menü: hangileri, hafif/tam, commit?
  python guncelle.py --hepsi            # kütükteki bütün hatlar (hafif mod)
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
  · Kopyalama tablosu HATLAR içinde — cron (.github/workflows/veri.yml) aynı kütükten
    koşar; siteye giden her çıktı burada listelenir, YAML'de kopya tutulmaz.
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
import argparse, json, os, re, shutil, signal, subprocess, sys, threading, time
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
# Hat alt süreçleri ortak HTTP emniyetiyle açılır: ortak/sitecustomize.py
# PYTHONPATH'te olunca Python onu açılışta kendiliğinden import eder ve
# zaman aşımısız kalan her isteğe varsayılan zaman aşımı + yeniden deneme koyar.
# Hat KENDİ .venv'iyle koşsa da geçerli — PYTHONPATH yorumlayıcıdan bağımsız.
# (2026-08-27: tcmb istemcisi timeout'suz istek atıyor, EVDS 21 dk astı.)
_ORTAK = str(KOK / "ortak")
_COCUK_ENV = {
    **os.environ,
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONPATH": os.pathsep.join(
        [_ORTAK] + ([p] if (p := os.environ.get("PYTHONPATH")) else [])),
}


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
    # Bu hat şu hatların ÇIKTISINDAN hesaplanır (türev hat). Komut satırında
    # bir üst hat seçilince türevleri de listenin SONUNA eklenir: üst hat elle
    # tazelenip türevi dünkü seriden hesaplanmış kalmasın.
    bagimli: tuple[str, ...] = ()
    # ozet.json'da veri tarihini taşıyan alan(lar) — tazelik denetimi.
    # LİSTE olmasının sebebi: bir hattın farklı frekanslı birden çok çıktısı
    # olabiliyor ve biri ilerlerken diğeri sessizce donabiliyor (TCMB'de rezerv
    # serisi ilerlerken altın/akım tarafı taşımaya girebilir). Tek anahtara
    # bakmak o durumda "veri tazelendi" der.
    tarih_anahtarlari: tuple[str, ...] = ("_tarih",)
    panel: list[str] = field(default_factory=list)  # canlı panel komutu (python'dan sonraki argümanlar)
    # GÜNLÜK kip — hafif ile tam arasında üçüncü bir basamak.
    #
    # Sebebi FX hattı: hafif kipi mevcut veriden grafik çiziyor, haber akışını
    # HİÇ toplamıyordu. Günlük listede durduğu sürece her koşuda "tazelendi"
    # damgası atıp veriyi ilerletmiyordu (bkz. 63fbf6e). Hattı listeden çıkarmak
    # sahte tazeliği bitirdi ama günlük ilerleyebilecek yarısını da dondurdu:
    # anlık endeks canlı haber akışından gelir ve HER GÜN ilerleyebilir; yalnız
    # GDELT haftalık arşivi haftalık ritimdedir.
    #
    # Bu alan o ikisini ayırır: `gunluk` gerçekten veri toplayan ama arşive
    # dokunmayan adımları taşır. Tanımlanmamışsa kip hafife düşer.
    gunluk: list[str] = field(default_factory=list)

    def adimlar(self, tam: bool, gunluk: bool = False) -> list[str]:
        if gunluk and not tam:
            return self.gunluk or self.hafif
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
        # grafik_yenile.py HAFİF listede olmak ZORUNDA: hedef_gerceklesme.html ve
        # vade_analizi.html yalnız main.py (tam kip) tarafından üretiliyor ve ikisi
        # de .gitignore'da. Yani taze bir checkout'ta hafif kip o iki dosyayı hiç
        # görmüyor, siteye kopyalama "çıktı yok" diye YARIDA kesiliyor ve dict
        # sırasında onlardan SONRA gelen tablolar.json ile ozet.json siteye hiç
        # gitmiyordu. HTML'ler kopyalandığı için hat çalışmış görünüyor, sayfanın
        # sayıları ise bir önceki tam kipte donuyordu. grafik_yenile.py aynı iki
        # grafiği depodaki CSV'lerden ağa çıkmadan üretir.
        ["grafik_yenile.py", "web_cikti_tahmin.py", "tablo_uret.py",
         "vade_proj.py", "ozet_uret.py"],
        ["main.py", "web_cikti_tahmin.py", "tablo_uret.py",
         "vade_proj.py", "ozet_uret.py"],
        {f"{f}.html": f"{f}.html" for f in ["planlanan_ihraclar", "tahmin_dogrulama", "tahmin_aylik",
         "strateji_revizyon", "faiz_gelisimi", "fiyat_araligi", "ihrac_hacmi", "ihrac_tempo", "ihrac_usd",
         "talep_analizi", "vade_dagilimi", "hedef_gerceklesme", "vade_analizi",
         "vade_patika", "vade_kompozisyon", "vade_maliyet", "vade_talep",
         "vade_itfa", "vade_reprice"]}       # analiz sayfasında gömülü — sözleşme bir bütündür
        | {"tablolar.json": "tablolar.json"},
        "tam kip: Hazine sitesini tarar (scraper), ilk koşu 10-20 dk",
        panel=["dashboard.py"]),            # Dash → http://127.0.0.1:8050
    Hat("fx", "FX Haber Endeksi", P / "indices", "fx-haber-endeksi",
        ["web_cikti.py", "ozet_uret.py"],
        ["run.py --fetch-history", "ozet_uret.py"],
        {"cikti/*.html": "*"},
        "tam kip: GDELT + FinBERT — ilk koşu saatler, sonrası dakikalar",
        # Günlük kip: canlı haber akışı (Google RSS, 7 günlük pencere) çekilir,
        # FinBERT ile puanlanır ve tarihçeye yeni bir snapshot yazılır; sonra
        # YALNIZ anlık endeks grafikleri çizilir (`--anlik`). GDELT tabanlı
        # paneller bilerek atlanır: o arşiv gün içinde ilerlemez, her gün
        # yeniden çizmek dakikalar süren günlük duyarlılık matrisini boşuna
        # koşturur ve haftalık "veri sonu" damgasını değişmeyen içerikle ezer.
        gunluk=["run.py", "web_cikti.py --anlik", "ozet_uret.py"],
        panel=["-m", "streamlit", "run", "dashboard.py"]),  # Streamlit → http://localhost:8501
    Hat("enflasyon", "Enflasyon Panosu", P / "Enflasyon", "enflasyon",
        # veri.py EVDS'ten çeker (TTL'li önbellek), metrik.py momentum/çekirdek/
        # katkı/dağılım/baz/reel faiz hesaplarını yapar ve EVDS'in kendi y/y
        # serisiyle ÇAPRAZ DOĞRULAR (0,05 puan eşiği aşılırsa hat DURUR),
        # grafik.py dokuz şekil üretir. Sıra bağlayıcıdır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        tarih_anahtarlari=("_tarih", "faiz_gun")),
    Hat("kredi", "Kredi ve Parasal Büyüklükler", P / "Kredi", "kredi-parasal",
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
    Hat("fonlama", "TCMB Fonlama ve Likidite", P / "Fonlama", "fonlama-likidite",
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
    Hat("ypmevduat", "Yurt içi yerleşiklerin YP mevduatı", P / "YPMevduat",
        "yp-mevduat",
        # Hattın sorusu "mevduat ne kadar arttı" değil, "artışın ne kadarı
        # fiili para akımı, ne kadarı değerleme": seri milyon dolar cinsinden
        # yayımlanıyor ve sepette euro, diğer para birimleri ve KIYMETLİ MADEN
        # var; euro dolara karşı değer kazandığında hiç yeni para girmeden
        # stok yükseliyor.
        # AYRIŞTIRMAYI BU HAT TÜRETMİYOR — TCMB parite etkisini ve ondan
        # arındırılmış değişimi RESMÎ olarak yayımlıyor; hattın işi o
        # ayrıştırmayı okunur kılmak ve KİMLİĞİ denetlemektir. Kendi kur
        # sepetimizden ikinci bir "parite etkisi" hesaplamak okura iki rakip
        # gerçek üretirdi.
        #
        # veri.py haftalık üç tabloyu (stok, stok kırılımı, resmî ayrıştırma)
        # 12 saat TTL'li ve SERİ BAZINDA önbellekle çeker; uzun aralık parçalı
        # istenir çünkü EVDS 1000 satırdan sonrasını SESSİZCE kırpıyor ("veri
        # geldi" ile "veri TAM geldi" aynı şey değildir). Gelen serinin KAPSAMI
        # ölçülür: çekirdeğin tam olduğu hafta sayısı 26'nın altına düşerse
        # çıktı ÜRETİLMEZ ve hat DURUR — yarım kalmış bir çekim, kırpma ya da
        # çökme demektir. metrik.py Δ stok = arındırılmış değişim + parite
        # etkisi kimliğini ölçer; ARTIK yayına engel DEĞİLDİR (Kredi'deki
        # Laspeyres artığının aynısı: ölçülür, yazılır, sayfada görünür),
        # çünkü kimlik TCMB'nin İKİ AYRI TABLOSU arasında kuruluyor ve
        # yuvarlama farkı taşır — sıkı bir eşik her koşuda yanlış alarm
        # üretirdi. DURDURAN tek ölçüm KAPSAM KİMLİĞİDİR (gerçek kişi + tüzel
        # kişi = toplam, aynı tablodan, ölçülmüş): tutmuyorsa kalem
        # numaralandırması kaymıştır ve o hâlde üretilen bir pano hiç
        # panodan kötüdür; ölçüm çerçeveleri yazılmadan hat düşer, siteye
        # kopyalama olmaz. grafik.py altı şekil üretir; ilan edilen veri ucu
        # figürün gerçekten çizdiği uçtan YENİ ise hat DURUR (bayat panelin
        # taze damgalanması bu hattın en olası kusuru). ozet_uret.py blok
        # saatlerini ve şekil saat defterini yazar; hiçbir saat kurulamıyorsa
        # DURUR — tarihsiz bir özet yayına giremez.
        #
        # DİKKAT: geniş toplam (yurt dışı yerleşik bankalar dahil) bu hattın
        # manşeti DEĞİLDİR; sayfada yalnız adıyla ve farkıyla geçer. İki
        # toplamı aynı şeymiş gibi yan yana koymak bu hattın en pahalı hatası
        # olurdu. Sıra bağlayıcıdır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        # Hattın ana saati (blokların EN YENİSİ) artı ÜÇ blok saati, yani üç
        # ayrı donma riski — hepsi aynı haftalık yayımdan
        # gelse de ayrı EVDS tablolarından okunuyor ve biri ilerlerken öbürü
        # sessizce durabilir: stok tabloları, resmî ayrıştırma tablosu, ve
        # dolarizasyonun beslendiği TL karşılıkları. Tek anahtara bakmak o
        # durumda "veri tazelendi" derdi. `kimlik_tarih` bilerek YOK ama
        # gerekçesi "türetilmiş olması" DEĞİL: o saat kendi başına ölçülüyor ve
        # stok ile akım saatinin en eskisinden GERİDE de olabiliyor (ardışık
        # iki gözlem tam yedi gün değilse haftalık değişim ölçülemez, blok bir
        # hafta geriye çıpalanır). Listeye girmemesinin sebebi, kimliğin
        # kendisinin hattı DURDURMAMASI: geride kalması bir donma değil,
        # ölçülemeyen bir haftadır ve koşu kaydında adıyla görünür. Şekil
        # damgası da o ölçülmüş saatten okunuyor. Sepet bileşimi tablosu (bir hafta
        # geriden gelen ayrı popülasyon) hat tarafından BİLEREK çekilmiyor;
        # çekildiği gün DÖRDÜNCÜ bir anahtar gerekir.
        tarih_anahtarlari=("_tarih", "stok_tarih", "akim_tarih", "dol_tarih")),
    Hat("odemeler", "Ödemeler Dengesi ve Dış Finansman", P / "OdemelerDengesi",
        "odemeler-dengesi",
        # veri.py EVDS3'ten dört frekansta çeker (aylık ödemeler dengesi,
        # haftalık dış borç ödeme takvimi, üç aylık GSYH, günlük kur) ve
        # 16 kimlik denetimi koşturur. metrik.py işaret çevirmesini TEK YERDE
        # yapar, çekirdek cari dengeyi ve brüt dış finansman ihtiyacını kurar;
        # tautolojik olmayan denetimleri (artık bandı, mertebe kıyası, bacak
        # yoklaması) koşturur ve biri düşerse hat DURUR. grafik.py on iki şekil
        # üretir ve her yığılmış panelde çubuk toplamı ile toplam çizgisini
        # KARŞILAŞTIRIR — ayrışma varsa figür yayımlanmaz. Sıra bağlayıcıdır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        # Dört ayrı yayım ritmi, dört ayrı donma riski: aylık ödemeler dengesi
        # ~2 ay gecikmeli, haftalık takvim ~5 gün, GSYH ~145 gün. Tek anahtara
        # bakmak "veri tazelendi" derdi.
        tarih_anahtarlari=("_tarih", "_tarih2", "_tarih3")),
    Hat("dibs", "DİBS Verim Eğrisi ve Reel Faiz", P / "DIBS", "dibs-verim-egrisi",
        # veri.py EVDS3'ten DİBS strip evrenini (güncel + arşiv) ve referans
        # faizleri çeker; önbellek seri bazında TTL'lidir ve çekim istisnayla
        # düşerse DOLU önbelleğe DOKUNMAZ (boş önbellek "EVDS doğruladı"
        # imzası taşır; planın %2'sinden fazlası veri taşımıyorsa hat DURUR).
        # metrik.py spot eğriyi bootstrapsız kurar (strip sıfır kuponludur),
        # fonlama faizlerini eğriyle aynı konvansiyona (BİLEŞİK) çevirip
        # taşımayı hesaplar, AOFM'yi tabanı yokken geçersiz işaretler, PKA
        # nokta beklentilerini vadeye kadarki ORTALAMAYA çevirir ve strip
        # toplamı özdeşliğini birim sınaması olarak koşturur — sapması varsa
        # hat DURUR. grafik.py sekiz şekil üretir. Sıra bağlayıcıdır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        # İki frekans, iki donma riski: eğri ve referans faizler günlük, anket
        # ile TÜFE aylık. Tek anahtara bakmak "veri tazelendi" derdi.
        tarih_anahtarlari=("_tarih", "_tarih2")),
    Hat("butce", "Bütçe ve Borç Stoku", P / "Butce", "butce-borc",
        # veri.py EVDS3'ten aylık bütçe, üç aylık dış borç ve GSYH, haftalık
        # menkul kıymet sahipliği ve günlük kur çeker. metrik.py'nin kritik işi
        # STOK TANIMI: iç borç (ihraç tabanlı) ile brüt dış borç (yerleşiklik
        # tabanlı) doğrudan toplanamaz — yurt dışının tuttuğu DİBS iki kez
        # sayılır, yerleşiklerin tuttuğu eurobond hiç sayılmaz. Stok bu yüzden
        # ARAÇ tabanında kurulur: iç borç + yurt dışında ihraç edilen senet
        # (devletin kendi tuttuğu düşülerek) + dış krediler. Dış kredi artığı
        # mertebe bandının dışına çıkarsa hat DURUR: sahiplik serilerinin
        # eşlemesi bozulmuş demektir ve yanlış stok yayına gitmemelidir.
        # grafik.py on üç şekil üretir.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*", "uyarilar.json": "uyarilar.json"},
        # Üç frekans ayrı ayrı donabiliyor: bütçe aylık, dış borç ve GSYH üç
        # aylık, sahiplik haftalık. Tek anahtara bakmak yanıltırdı.
        tarih_anahtarlari=("_tarih", "_tarih2", "_tarih3")),
    Hat("buyume", "Büyüme (GSYH)", P / "Buyume", "buyume",
        # veri.py seri kodlarını GÖMMEZ: her EVDS grubunun içeriğini serieList'ten
        # okur, o listeyi çeker (uydurma kod giremez, TÜİK seri eklerse gelir).
        # metrik.py katkıyı w(t−4)×g(t) ile kurar — zincirlenmiş hacim endeksleri
        # toplanmadığı için ağırlık CARİ fiyatlı paydan gelir — ve üç kimlik
        # koşturur: harcama tarafı GSYH'si üretim tarafıyla aynı mı, cari
        # fiyatlarla sektörel toplam + vergi GSYH'ye eşit mi, artık makul bantta
        # mı. Biri düşerse hat DURUR. Artık bileşenlere dağıtılmaz, ayrı yazılır.
        ["veri.py", "metrik.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*"},
        not_="Üç aylık; TÜİK yayımı ~60 gün gecikmeli."),
    Hat("elnino", "El Niño ve Gıda Enflasyonu", P / "ElNino", "el-nino",
        # veri.py ONI'yi NOAA'nın üç ayrı genel ucundan sırayla dener (hiçbiri
        # çalışmazsa hat DURUR) ve TÜFE alt endekslerini Enflasyon hattıyla AYNI
        # kodlardan çeker. metrik.py'nin kurucu kararı: ham gıda enflasyonu ile
        # ONI'yi korele etmek sahte ilişki üretir (ikisinin de kendi trendi var),
        # bu yüzden ölçüm GÖRECELİ gıda enflasyonu (gıda − manşet) üzerinden
        # yapılır. İki bağımsız ölçüt: çapraz korelasyon (kalıcılık yanlısı,
        # yalnız gecikme profili için) ve epizot çalışması (yanlılıktan geçmez,
        # tez buna dayanır). Geçiş katsayısı senaryo hesabı için ölçülür.
        #
        # kuresel.py KÜRESEL KANADI ölçer ve sırası metrik.py'den SONRADIR:
        # epizot tanımını metrik.py'den içe aktarır (iki yerde iki tanım bir gün
        # sessizce ayrışırdı) ve Türkiye ölçümünü karşılaştırmaya alır. Türkiye
        # örneklemi iki epizotta tıkanıyor; şokun GELDİĞİ yerin verisi 1980'de
        # başlıyor ve orada aynı ölçüt hüküm verebiliyor. FRED düşerse bu katman
        # hiçbir şey yazmaz, eskiyi de siler ve hat DURMAZ — Türkiye ölçümü
        # kendi başına ayakta.
        ["veri.py", "metrik.py", "kuresel.py", "grafik.py", "ozet_uret.py"], [],
        {"cikti/*.html": "*"},
        not_="ONI aylık, TÜFE aylık; ENSO tahminleri üç ayda bir belirginleşir."),
    Hat("marj", "Yiyecek Hizmetleri Marjı", Path("Research/marj"), "yiyecek-hizmetleri-marj",
        ["src/web_cikti.py", "src/ozet_uret.py"],
        ["src/run_all.py", "src/web_cikti.py", "src/ozet_uret.py"],
        {"output/web/*.html": "*", "output/ozet.json": "ozet.json"},
        "tam kip: EVDS/TÜİK'ten yeniden çeker; MEDAS için Playwright"),
    # ── TÜREV HATLAR — kendi kaynağına gitmez, üstteki hatların depoya yazdığı
    # CSV'lerden hesaplanır. SIRA BAĞLAYICIDIR: kos() hatları komut satırı /
    # kütük sırasıyla koşturur; bunlar Fonlama, DİBS, Kredi ve Enflasyon'dan
    # SONRA durmalı, yoksa aynı koşuda dünkü CSV'den hesaplanırlar. Tazeleme
    # takviminde tarifleri YOK: kararlar() onları "tarifi yok — koşuluyor" ile
    # her koşuda koşturur (saniyeler); üst hattın tetiğine bağlanmaları, üst
    # hat düşüp bir sonraki koşuda kurtulduğunda bunları bir gün bayat bırakırdı.
    # Eskiden veri.yml içinde elle `cd … && python hesap.py && cp …` adımıyla
    # koşuyorlardı: kopya sözleşmesi YAML'de kopya olarak duruyor, tazelik ve
    # geriye-gitme kapısı, ön denetim ve --liste onları hiç görmüyordu.
    # ozet.json kopya sözlüğüne yazılmaz: kos() proje kökündekini kendisi kopyalar.
    Hat("carry", "TL Taşıma Defteri", P / "Carry", "tl-tasima",
        ["hesap.py", "grafik.py"], [],
        {"makas.html": "makas.html", "endeks.html": "endeks.html",
         "nakit_tahvil.html": "nakit_tahvil.html", "konvansiyon.html": "konvansiyon.html"},
        "türev hat: Fonlama + DİBS depo serilerinden; her koşuda, saniyeler",
        # Üç saat: _tarih kurun günü (en taze seri), endeks_tarih TLREF'e kapılı
        # endeksin günü, nakit_tahvil_tarih ise Şekil 03'ün iki bacağının
        # ESKİSİ — yani DİBS taşıma kolonu donarsa donan tek anahtar odur.
        # İlk ikisi DİBS bacağını hiç görmüyordu.
        tarih_anahtarlari=("_tarih", "endeks_tarih", "nakit_tahvil_tarih"),
        bagimli=("fonlama", "dibs")),
    Hat("tufex", "TÜFEX ve Başabaş Enflasyon", P / "Tufex", "tufex-basabas",
        ["hesap.py", "grafik.py"], [],
        {"basabas_anket.html": "basabas_anket.html", "prim_kesit.html": "prim_kesit.html",
         "prim_tarihce.html": "prim_tarihce.html", "reel_tarihce.html": "reel_tarihce.html",
         "mevsim.html": "mevsim.html"},
        "türev hat: DİBS + Enflasyon depo serilerinden; her koşuda, saniyeler",
        tarih_anahtarlari=("_tarih", "basabas_2y_tarih"), bagimli=("dibs", "enflasyon")),
    Hat("makro", "Makroihtiyatinin İzi", P / "Makroihtiyati", "makroihtiyati",
        ["hesap.py", "grafik.py"], [],
        {"ayrisma.html": "ayrisma.html", "kacak.html": "kacak.html", "makas.html": "makas.html",
         "bkea.html": "bkea.html", "duzenlemeler.json": "duzenlemeler.json"},
        "türev hat: Kredi + Fonlama depo serilerinden; düzenleme defteri elle tutulur",
        # _tarih haftalık kredi bacağı; ikinci saat ÇEYREKLİK Banka Kredileri
        # Eğilim Anketi. Tek anahtarla bayatlık denetimi çeyreklik bacağa HİÇ
        # bakmıyordu: 03.09.2026'da anket 2026-04-01'de duruyordu (142 gün) ve
        # hiçbir koşu bunu söylemiyordu. İki yayım arasında bu anahtar tabiatı
        # gereği DONUK görünür — mesaj hangi bacağın kımıldamadığını adıyla
        # yazar; aranan şey bacağın büsbütün ölmesi ve geriye gitmesidir.
        tarih_anahtarlari=("_tarih", "bkea_std_isletme_tarih"),
        bagimli=("kredi", "fonlama")),
    # Reel sektör FX ağa çıkar (EVDS bie_fdvy, aylık, ~2 ay gecikmeli). Çekim
    # düşerse hat DURUR ve siteye hiçbir şey kopyalanmaz: sitedeki son iyi
    # çıktı kalır, koşu ✗ ile görünür. Eski YAML yolu "düşerse uyar, yer
    # tutucularla devam" diyordu — o yol depodaki gerçek veriyi yer tutucuyla
    # ezme riski taşıyordu.
    Hat("reelfx", "Reel Sektörün Döviz Pozisyonu", P / "ReelSektorFX", "reel-sektor-fx",
        ["veri_cek.py", "hesap.py", "grafik.py"], [],
        {"pozisyon.html": "pozisyon.html", "bilesim.html": "bilesim.html", "kisa_vade.html": "kisa_vade.html"},
        "EVDS bie_fdvy; takvim tetiği aylık — çekim düşerse hat durur, site korunur",
        # _tarih zaten net pozisyonun ayı; ikinci saat tcmb hattından gelen
        # haftalık rezerv bacağı — donarsa tazelik denetimi görsün.
        tarih_anahtarlari=("_tarih", "acik_rezerv_tarih"), bagimli=("tcmb",)),
]
HAT = {h.ad: h for h in HATLAR}


def _renk(m, k):  # k: 32 yeşil, 31 kırmızı, 33 sarı, 36 camgöbeği
    return f"\033[{k}m{m}\033[0m" if sys.stdout.isatty() else m


EVDS_HATLAR = {"tcmb", "usdtry", "reer", "yabanci", "marj", "enflasyon",
               "kredi", "fonlama", "ypmevduat", "odemeler", "dibs", "butce",
               "buyume", "elnino", "reelfx"}
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


def turevleri_ekle(secilen: list["Hat"], atlanan_adlar: set[str] | frozenset = frozenset()) -> list["Hat"]:
    """Seçilen bir üst hattın TÜREVLERİ de koşar (kütük sırasıyla, sonda): elle
    "fonlama" tazelenince taşıma defteri dünkü seriden hesaplanmış kalmazdı.

    Takvimin bilinçle ATLADIĞI hat geri eklenmez. reelfx tcmb'ye bağımlı ama
    kendi 30 günlük EVDS ritmi var (tazeleme.py emniyet ağı); tcmb her iş günü
    seçildiği için genişletme onu her gün ağa çıkarıyor, "30 günde bir EVDS"
    sözleşmesi kâğıt üstünde kalıyordu (02.09.2026). --gerekli yokken (elle
    koşu) davranış aynı: atlanan küme boştur."""
    secili = {h.ad for h in secilen}
    eklenen: list[Hat] = []
    for h in HATLAR:
        if h.bagimli and h.ad not in secili and set(h.bagimli) & secili:
            if h.ad in atlanan_adlar:
                print(f"  · {h.ad}: takvim atladı (yeni yayım yok) — türev genişletmesi geri eklemedi")
                continue
            eklenen.append(h); secili.add(h.ad)
            print(f"  + {h.ad}: {', '.join(x for x in h.bagimli if x in secili)} seçildiği için türev hat da koşacak")
    return list(secilen) + eklenen


def okur_dili_bulgulari(hedef: Path) -> list[str]:
    """Siteye kopyalanan koşu kaydının okur dili: uyarilar.json `uyarilar` ve
    ozet.json'un CÜMLE olan her metin alanı sayfaya OLDUĞU GİBİ basılır (koşu
    kutusu, veri durumu şeridi, `<Deger>` ile gömülen açıklama cümleleri). Operatör için yazılmış bir satır — `kkm_aktif`
    bayrağı, bie_ grup kodu, '5.2%' — hat koştuğu anda burada görünür; yayın
    kapısı (sayfa sınavı 17) aynı soruyu ENGEL olarak sorar. Tanım tek yerde:
    ortak/okur_dili.kosu_kaydi_tara."""
    if _ORTAK not in sys.path:
        sys.path.insert(0, _ORTAK)
    import okur_dili
    satirlar: list[tuple[str, str]] = []
    try:
        u = json.loads((hedef / "uyarilar.json").read_text(encoding="utf-8"))
        satirlar += [("uyarilar.json", str(x)) for x in (u.get("uyarilar") or [])]
    except (OSError, ValueError, AttributeError):
        pass
    try:
        d = json.loads((hedef / "ozet.json").read_text(encoding="utf-8"))
        satirlar += [(f"ozet.json {a}", m)
                     for a, m in okur_dili.ozet_cumleleri(d)]
    except (OSError, ValueError, AttributeError):
        pass
    return [f"{k}: {esl!r} ({aile})"
            for k, m in satirlar for _i, aile, esl in okur_dili.kosu_kaydi_tara([m])]


def duman_kos(h: "Hat") -> str | None:
    """Hattın klasöründeki `duman.py` — ağa çıkmadan, saniyeler içinde, hattın
    kendi ölçüm sözleşmelerini sorar. Geçerse None, düşerse tek satırlık sebep.

    NEDEN KOŞU'NUN İÇİNDE: sınama yalnız `--denetle` yazan birinin eline
    bağlıysa bir gün koşulmaz — zamanlanmış koşu `--denetle` demiyor. Ölçüm
    katmanı sözleşmesini bozmuş bir hat, bozuk çıktıyı siteye kopyalamadan
    ÖNCE durmalı. Maliyeti saniyeler; yalnız `duman.py`si olan hat için koşar.
    """
    yol = KOK / h.klasor / "duman.py"
    if not yol.exists():
        return None
    try:
        r = subprocess.run([hat_python(h), "-u", "duman.py"],
                           cwd=str(KOK / h.klasor), env=_COCUK_ENV,
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
    except Exception as e:                                  # zaman aşımı dahil
        return f"duman sınaması koşmadı ({type(e).__name__})"
    if r.returncode == 0:
        return None
    dusen = [x.strip() for x in (r.stdout + r.stderr).splitlines()
             if x.strip().startswith("✗")]
    return ("duman sınaması DÜŞTÜ: "
            + ("; ".join(dusen[:3]) if dusen else "ayrıntı koşu çıktısında")
            + f' — çözüm: cd "{h.klasor}" && python duman.py')


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


def _tarih_degeri(m: str) -> "datetime.date | None":
    """ozet.json'daki tarih metnini kıyaslanabilir bir güne çevir.

    Hatlar tarihi kendi doğal biriminde yazar: gün (18.08.2026), ay (07.2026,
    2026-08), çeyrek (2026-Ç1) veya damga (2026-08-18 18:54 UTC). Çözülemeyen
    biçim None döner ve kıyas yapılmaz — uydurma kıyas, kıyas yapmamaktan kötüdür.
    """
    import datetime as _dt
    m = (m or "").strip()
    if not m or m in ("None", "?"):
        return None
    ceyrek = re.match(r"^(\d{4})[-\s]*[ÇQq](\d)$", m)
    if ceyrek:
        yil, c = int(ceyrek.group(1)), int(ceyrek.group(2))
        return _dt.date(yil, min(3 * c, 12), 1)
    for kalip in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y", "%m.%Y", "%Y-%m", "%Y"):
        try:
            return _dt.datetime.strptime(m[:len("2026-08-18") if "%d" in kalip else 7
                                           if "%m" in kalip else 4], kalip).date()
        except ValueError:
            continue
    try:                                   # "2026-08-18 18:54 UTC" gibi damgalar
        return _dt.datetime.strptime(m[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


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


# Yalnız TAM kipte veya canlı panelde gereken paketler. Hafif kip bunlara
# dokunmaz; buna rağmen requirements.txt'te durdukları için ön denetim onları
# "eksik" sayıp hattı komple atlıyordu — 2026-08-25 bulut koşusunda rezerv,
# USDTRY, REER ve Hazine hatlarının dördü de tam bu yüzden hiç koşmadı.
# Bulutta bunları kurmak da anlamsız: torch tek başına ~2 GB.
AGIR_PAKET = {
    "torch", "transformers", "scikit-learn",   # fx: FinBERT (yalnız --tam)
    "praw", "ntscraper", "deep-translator", "vaderSentiment",  # fx: kaynak hasadı
    "playwright",                          # marj: MEDAS hasadı (ham dosya varsa gereksiz)
}

# CANLI PANEL paketleri. AGIR_PAKET'ten AYRI tutulmaları şart: ağır paketler
# TAM kipte gerçekten gerekir (fx'in FinBERT'i tam kipte koşar), panel
# paketleri ise HİÇBİR veri koşusunda gerekmez — panel yerelde elle açılan
# bir kolaylıktır. İkisi aynı kümedeyken "tam kip ağırları da kursun" kuralı
# panelinkileri de kuruyordu: 31.08.2026'da Hazine hattının tam kip koşusu
# dash kurmaya çalışırken düştü ve yeni İç Borçlanma Stratejisi inmedi.
# Bunlar yalnız --panel ve --kur yollarında kurulur.
# TORCH: KOŞUCUDA GPU YOK, CUDA DA OLMAMALI. Ölçüldü (03.09.2026, pip
# --dry-run): `torch>=2.0.0` Linux'ta 27 paket çözüyor ve 19'u
# nvidia-*/cuda-*/triton — cuda-toolkit, cudnn, nccl, cusparselt, nvshmem…
# Hepsi GPU içindir; FinBERT bu koşucularda CPU'da çıkarım yapar. O gün FX
# hattı tam bu yüzden düştü: koşucunun diski "No space left on device" ile
# doldu ve kurulum adımı bitmeden öldü — hat koşamadı, endeks o akşam
# ilerlemedi. Torch bu yüzden ÖNCE resmî CPU kanalından kurulur; kanal
# açılmazsa uyarı basılır ve normal kurulum kendi yolunu dener (yoklanmamış
# bir kaynağa hattı mahkûm etmeyiz).
TORCH_CPU_INDEKS = "https://download.pytorch.org/whl/cpu"
TORCH_AILESI = {"torch", "torchvision", "torchaudio"}

PANEL_PAKET = {
    "dash", "dash-bootstrap-components",   # hazine canlı panosu
    "streamlit",                           # fx canlı panosu
}


def _req_paketler(d: Path, agir_dahil: bool = True,
                  panel_dahil: bool = False) -> list[str]:
    """requirements.txt → dağıtım adları (sürüm, ekstra, koşul, yorum ayıklanmış).

    panel_dahil YALNIZ --panel/--kur yollarında açılır: canlı pano paketleri
    hiçbir veri koşusunun gereği değildir ve "eksik" sayılırlarsa hattı komple
    atlatırlar.
    """
    req = d / "requirements.txt"
    if not req.exists():
        return []
    adlar = []
    for satir in req.read_text(encoding="utf-8").splitlines():
        s = satir.split("#")[0].strip()
        if not s or s.startswith("-"):        # -r include, --index-url …
            continue
        s = re.split(r"[<>=!~;\[ ]", s, 1)[0].strip()
        if s in PANEL_PAKET and not panel_dahil:
            continue
        if s and (agir_dahil or s not in AGIR_PAKET):
            adlar.append(s)
    return adlar


def eksik_paketler(h: "Hat", tam: bool = True, gunluk: bool = False) -> list[str] | None:
    """Hattı koşacak yorumlayıcıda requirements'tan eksik olanlar.

    None = denetlenemedi (yorumlayıcı çalışmadı) — bu da bir bulgudur.
    Hafif kipte ağır paketler sorulmaz: o adımlar zaten koşmayacak.
    GÜNLÜK kip bağımlılıkta TAM sayılır: fx'in günlük kipi de run.py koşturur
    ve FinBERT skorlaması çalışma anında torch/transformers ister. İlk günlük
    koşu (28.08.2026, elle) tam bu yüzden 15 saniyede düştü: ön kontrol hafif
    listeye baktı ve geçti, import çalışma anında patladı.
    """
    paketler = _req_paketler(KOK / h.klasor, agir_dahil=tam or gunluk)
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


def tazeleme_modulu():
    """bulten/tazeleme.py'yi yükle (yoksa/çalışmazsa None).

    Paket değil, kardeş klasördeki bir betik olduğu için elle yüklenir.
    Bulunamaması guncelle.py'yi durdurmaz: takvim bir kolaylık, zorunluluk değil.
    """
    if "_TAZELEME" in globals():
        return globals()["_TAZELEME"]
    mod = None
    try:
        import importlib.util as _iu
        yol = KOK / "bulten" / "tazeleme.py"
        if yol.exists():
            sys.path.insert(0, str(KOK / "bulten"))
            sp = _iu.spec_from_file_location("tazeleme", yol)
            mod = _iu.module_from_spec(sp)
            # exec_module'dan ÖNCE kaydedilmeli: @dataclass alanları çözerken
            # sys.modules[cls.__module__]'e bakar, kayıtsız modülde None bulur.
            sys.modules["tazeleme"] = mod
            sp.loader.exec_module(mod)
    except Exception as e:
        print(_renk(f"  (tazeleme takvimi yüklenemedi: {e})", 33))
        mod = None
    globals()["_TAZELEME"] = mod
    return mod


def sistem_kur(secilen: list["Hat"], tam: bool, gunluk: bool = False) -> bool:
    """Seçilen hatların gereksinimlerini KOŞAN yorumlayıcıya kurar.

    Bulut koşucusu için: orada her hatta bir .venv kurmak hem yavaş hem gereksiz
    (koşucu zaten tek kullanımlık). Yalnız o koşuda gerçekten koşacak hatların
    paketleri kurulur — hafif kipte ağır paketler (torch, playwright, dash)
    listeye girmez.
    """
    paketler: set[str] = set()
    for h in secilen:
        req = KOK / h.klasor / "requirements.txt"
        if not req.exists():
            continue
        for satir in req.read_text(encoding="utf-8").splitlines():
            x = satir.split("#")[0].strip()
            if not x or x.startswith("-"):
                continue
            ad = re.split(r"[<>=!~;\[ ]", x, 1)[0].strip()
            # Günlük kip de ağır paketleri ister (bkz. eksik_paketler).
            # Panel paketleri hiçbir veri koşusunda gerekmez.
            if ad in PANEL_PAKET:
                continue
            if ad and (tam or gunluk or ad not in AGIR_PAKET):
                paketler.add(x)
    if not paketler:
        print("  kurulacak paket yok")
        return True
    sirali = sorted(paketler)
    print(f"  {len(sirali)} gereksinim kuruluyor: "
          + ", ".join(re.split(r"[<>=!~;\[ ]", x, 1)[0] for x in sirali))

    def _ad(x: str) -> str:
        return re.split(r"[<>=!~;\[ ]", x, 1)[0].strip().lower()

    torchlar = [x for x in sirali if _ad(x) in TORCH_AILESI]
    if torchlar:
        print(f"  torch CPU kanalından kuruluyor ({TORCH_CPU_INDEKS})")
        rt = _pip_kos([*torchlar, "--index-url", TORCH_CPU_INDEKS])
        if rt is not True:
            print(_renk("  [uyarı] CPU kanalı açılmadı; torch varsayılan "
                        "kanaldan kurulacak (CUDA paketleri diski doldurabilir)", 33))
        else:
            sirali = [x for x in sirali if _ad(x) not in TORCH_AILESI]
    if sirali and _pip_kos(sirali) is not True:
        return False
    return True


def _pip_kos(arglar: list[str]) -> bool:
    """pip install — düşerse SEBEBİ yazar, yalnız 'düştü' demez.

    03.09.2026'da FX hattı bu adımda öldü ve koşu kaydında görünen tek şey
    '✗ kurulum düştü' idi; gerçek sebep ("No space left on device") yedi yüz
    satırlık günlüğün ortasında duruyordu. Bir arıza mesajı, arızayı arayan
    kişiye ne yapacağını söylemelidir."""
    r = subprocess.run([PY, "-m", "pip", "install", "--quiet", *arglar],
                       env=_COCUK_ENV, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if not r.returncode:
        return True
    cikti = (r.stdout or "") + (r.stderr or "")
    for satir in cikti.splitlines()[-12:]:
        print(f"    {satir}")
    if "No space left on device" in cikti or "Errno 28" in cikti:
        print(_renk("  ✗ kurulum düştü: KOŞUCUNUN DİSKİ DOLDU. Ağır paketler "
                    "(torch/CUDA) sığmıyor — iş akışında diski boşaltan adım "
                    "koşuyor mu, torch CPU kanalından mı kuruluyor?", 31))
    else:
        print(_renk("  ✗ kurulum düştü", 31))
    return False


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


def _eksik_scriptler(h: "Hat", tam: bool, gunluk: bool = False) -> list[str]:
    """Adım satırlarının ilk parçası bir .py ise, dosya gerçekten duruyor mu?"""
    d = KOK / h.klasor
    yok = []
    for adim in h.adimlar(tam, gunluk):
        ilk = adim.split()[0]
        if ilk.endswith(".py") and not (d / ilk).exists():
            yok.append(ilk)
    return yok


def _kapidan_sonra_tanim(yol: Path) -> list[str]:
    """`if __name__ == "__main__":` kapısından SONRA tanımlanan üst düzey
    ad var mı?

    NEDEN VAR: bir hattın ölçüm katmanına yeni bir fonksiyon eklendi ve
    dosyanın SONUNA yazıldı — yani modül kapısından sonrasına. Python tanımı
    çalıştırmadan kos() koşmaya başladı ve hat NameError ile düştü. Sözdizimi
    doğru, içe aktarma doğru, derleme temiz; hata yalnız KOŞARKEN görünüyor ve
    hattın bütün adımlarını birden düşürüyor.

    Ölçüt statiktir ve saniyeler sürer: kapıdan sonra `def` ya da `class`
    görürse o adı döndürür. Bir dosyayı koşturmadan önce sorulacak en ucuz
    soru bu."""
    try:
        import ast
        agac = ast.parse(yol.read_text(encoding="utf-8"))
    except Exception:
        return []                       # derlenmiyorsa başka ölçüt söyler
    kapi = None
    for d in agac.body:
        if (isinstance(d, ast.If) and ast.dump(d.test).count("__name__")
                and ast.dump(d.test).count("__main__")):
            kapi = d.lineno
    if kapi is None:
        return []
    return [f"{g.name} (satır {g.lineno})" for g in agac.body
            if isinstance(g, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and g.lineno > kapi]


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
        eksik = eksik_paketler(h, tam)
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
        # KAPI ÖLÇÜTÜ: modül kapısından sonra tanım kalmışsa hat koşarken
        # NameError ile düşer. Statik, saniyeler sürer, ENGEL üretir —
        # koşturup öğrenmek yerine önce sorulur.
        for adim in h.adimlar(tam):
            ilk = adim.split()[0]
            if not ilk.endswith(".py"):
                continue
            gec = _kapidan_sonra_tanim(KOK / h.klasor / ilk)
            if gec:
                engel.append(
                    f"{h.ad}: {ilk} — `if __name__` kapısından SONRA tanım var "
                    f"({', '.join(gec)}). Python bu tanımları çalıştırmadan "
                    f"koşuya başlar; hat NameError ile düşer. Tanımı kapının "
                    f"üstüne taşıyın.")
        if yok:
            engel.append(f"{h.ad}: script yok — {', '.join(yok)}")
        print(f"  {h.ad:{_AD_G}s} {yorum:12s} {anahtar_m:8s} {paket_m:22s} {script_m}")
        if duzelt and (eksik or eksik is None):
            print(f"    → kuruluyor ({h.ad})")
            if kur(h):
                kalan = eksik_paketler(h, tam)
                if not kalan:
                    engel = [x for x in engel if not x.startswith(f"{h.ad}:")]
                    print(_renk("    ✓ giderildi", 32))

    # DUMAN SINAMASI: klasöründe `duman.py` olan hat, ağa çıkmadan kendi
    # ölçüm sözleşmelerini sorar. Buraya bağlanmasının sebebi kapsam: bir
    # sınama yalnız elle koşulduğu sürece bir gün koşulmaz. Ön denetim zaten
    # her güncellemenin önünde duruyor ve saniyeler sürüyor; sınama da orada
    # durur. Paketleri eksik olan hat atlanır (ayrı bir ENGEL zaten var).
    dumanli = [h for h in secilen if (KOK / h.klasor / "duman.py").exists()]
    if dumanli:
        print("\n▶ Duman sınamaları")
        for h in dumanli:
            if eksik_paketler(h, tam):
                print(f"  {h.ad:{_AD_G}s} {_renk('atlandı — paket eksik', 33)}")
                continue
            sebep = duman_kos(h)
            print(f"  {h.ad:{_AD_G}s} "
                  + (_renk("✓ temiz", 32) if sebep is None else _renk("DÜŞTÜ", 31)))
            if sebep:
                engel.append(f"{h.ad}: {sebep}")

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


# ADIM TAVANI — TOHUM, ölçüm değil.
#
# 900 saniye, ölçülen en yavaş hafif-kip HATTININ (kredi 869 sn, 27.08) üstünde
# duruyor ve o hat DÖRT adıma bölünüyor, yani tek bir adım bu tavana yaklaşmıyor.
# İşi bir hattı hızlandırmak değil, ASILMIŞ bir adımı bütün bütçeyi yemeden
# kesmek: 27.08'de EVDS 21 dakika astı ve dört hattın üçünün tamamlanmış işi
# çöpe gitti. `bulten/hat_suresi.json` biriktiğinde p90×2'ye geçilecek; okuyucu
# bu yüzden tek yerde (`adim_tavani`) duruyor.
ADIM_TAVAN_SN = 900

# ZAMAN AŞIMI İMZASI — TEK TANIM.
# `kos()` asılan bir adımı bu dizgeyle başlayan bir cümleyle bildiriyor ve
# `sure_kaydet()` süre defterine "zaman aşımı mı, düştü mü" diye onu okuyor.
# İki yere ayrı ayrı yazılmış aynı dizge bir gün sessizce ayrışır — nitekim
# ayrışmıştı: defter küçük harfle arıyordu, mesaj BÜYÜK harfle geliyordu ve
# asılan her hat deftere "düştü" diye geçiyordu. Süre defterinin var oluş
# sebebi tam da "hangi hat astı" sorusuydu (04.09.2026: 45 dakikayı hangi hat
# yedi, bilinmiyor); o soruyu cevaplayamayan bir kayıt işe yaramaz.
ZAMAN_ASIMI_IMZASI = "ZAMAN AŞIMI"


def adim_tavani(h: "Hat", tam: bool, gunluk: bool) -> float | None:
    """Bir adımın duvar saati tavanı (saniye). None = tavan yok.

    TAM ve GÜNLÜK kiplerde TAVAN YOK — bilerek. Bu kipler ölçülerek uzun:
    FX'in tam kipi 26.08'de 1 saat 45 dakikada bitti ve kendi iş akışında
    (fx.yml, 300 dakikalık bütçe) koşuyor. Onlara hafif kipin tavanını
    dayatmak, yayının önünde duran bir denetimin yanlış alarmı olurdu —
    haftalık FX koşusunu her hafta öldürürdü. Hafif kip ise "depodaki veriden
    grafik + ozet.json (dakikalar)" diye tanımlı; orada 15 dakikayı aşan bir
    adım çalışmıyor, ASILMIŞTIR.
    """
    if tam or gunluk:
        return None
    return ADIM_TAVAN_SN


def _agaci_oldur(p: subprocess.Popen):
    """Süreç AĞACINI öldür — yalnız çocuğu değil.

    Hatlar alt süreç açıyor (kendi .venv'i, pip, kazıyıcı). Yalnız doğrudan
    çocuğu öldürmek torunları ayakta bırakır: koşucu boş yere dolu kalır ve
    asılı istek hâlâ ağda durur. POSIX'te çocuk kendi oturumunda açıldığı için
    süreç GRUBU sinyallenebiliyor; Windows'ta taskkill /T ağacı geziyor.
    """
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                           capture_output=True)
            return
        gid = os.getpgid(p.pid)
        os.killpg(gid, signal.SIGTERM)
        try:
            p.wait(timeout=5)                    # düzgün kapanmaya şans
            return
        except subprocess.TimeoutExpired:
            os.killpg(gid, signal.SIGKILL)
    except Exception:                            # noqa: BLE001
        try:
            p.kill()
        except Exception:                        # noqa: BLE001
            pass


def _adim_kos(komut: list[str], cwd: Path,
              sinir_sn: float | None = None) -> tuple[int, list[str], bool]:
    """Adımı koştur; çıktıyı ekrana AKTARIRKEN günlüğe yaz ve son 40 satırı tut.

    subprocess.run(...) ile çocuğun çıktısı doğrudan terminale gidiyordu: canlı
    görünüyordu ama hiçbir yere kaydedilmiyor, hata mesajı özete de taşınamıyordu.

    DUVAR SAATİ ZAMAN AŞIMI (`sinir_sn`). 04.09.2026'ya kadar burada hiçbir
    zaman aşımı yoktu: `ortak/sitecustomize.py` yalnız HTTP İSTEĞİNE sınır
    takıyor, adımın toplam süresine değil. Bir hat asıldığında tazeleme adımının
    bütün bütçesini yiyor ve ONDAN SONRAKİ hatların tamamlanmış işi commit
    edilmeden gidiyordu (27.08: EVDS 21 dakika astı, dört hattın üçünün işi
    çöpe gitti). Sınır dolduğunda süreç AĞACI öldürülür, adım "zaman aşımı"
    diye raporlanır ve DÖNGÜ SÜRER — bir hattın asılması, tazelenmiş öbür
    hatların kaderini paylaşmaz.

    Çıktı ayrı bir iş parçacığından pompalanıyor: `for satir in p.stdout`
    doğrudan koşsaydı, hiç çıktı üretmeden asılan bir süreçte O DÖNGÜ
    bloklanırdı ve `wait(timeout=…)` satırına hiç gelinmezdi. Asılmanın en
    yaygın biçimi tam olarak budur.

    Döner: (çıkış kodu, son satırlar, zaman aşımına uğradı mı).
    """
    # Çocuk KENDİ süreç grubunda açılır ki ağacı tek sinyalle öldürülebilsin.
    ek = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
          else {"start_new_session": True})
    p = subprocess.Popen(komut, cwd=str(cwd), env=_COCUK_ENV,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1, encoding="utf-8", errors="replace",
                         **ek)
    son: deque[str] = deque(maxlen=40)

    def _pompala():
        try:
            for satir in p.stdout:               # satır satır: canlılık korunur
                satir = satir.rstrip("\n")
                # print() değil: sys.stdout zaten Tee ise iki kez yazılırdı.
                sys.__stdout__.write(satir + "\n")
                sys.__stdout__.flush()
                gunluge_yaz(satir)
                son.append(satir)
        except Exception:                        # noqa: BLE001
            pass                                 # boru kapandı (süreç öldürüldü)

    okuyucu = threading.Thread(target=_pompala, daemon=True)
    okuyucu.start()
    asti = False
    try:
        p.wait(timeout=sinir_sn)
    except subprocess.TimeoutExpired:
        asti = True
        _agaci_oldur(p)
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        son.append(f"[zaman aşımı] adım {sinir_sn:.0f} saniyede bitmedi; "
                   f"süreç ağacı öldürüldü")
    except KeyboardInterrupt:
        # Çocuk kendi oturumunda olduğu için terminalin Ctrl+C'sini ARTIK
        # almıyor; elle öldürülmezse guncelle.py kapandıktan sonra ayakta kalırdı.
        _agaci_oldur(p)
        raise
    okuyucu.join(timeout=5)
    return p.returncode, list(son), asti


def kos(h: Hat, tam: bool, gunluk: bool = False,
        adim_tavan_sn: float | None = None) -> tuple[bool, str, float]:
    # adim_tavan_sn: çağıran bir tavan dayatabilir (sabah bütçesi bu ucu
    # kullanacak); verilmezse kipe göre varsayılan tavan uygulanır.
    d = KOK / h.klasor
    t0 = time.time()
    eski_tarih = _ozet_tarih(h)
    py = hat_python(h)
    if py != PY:
        print(f"    (yorumlayıcı: {Path(py).relative_to(KOK) if py.startswith(str(KOK)) else py})")
    # Koşmadan önce yorumlayıcıyı yokla: eksik paket, sayfalarca traceback yerine
    # tek satırlık çözüm olarak görünsün. (Ekstra maliyet ~0,1 sn/hat.)
    eksik = eksik_paketler(h, tam, gunluk)
    if eksik is None:
        return False, (f"yorumlayıcı çalışmıyor ({py}) — çözüm: python guncelle.py "
                       f"--kur {h.ad}"), time.time() - t0
    if eksik:
        nerede = ".venv" if py != PY else "sistem python'u"
        return False, (f"eksik paket [{nerede}]: {', '.join(eksik[:4])}"
                       + (f" +{len(eksik) - 4}" if len(eksik) > 4 else "")
                       + f" — çözüm: python guncelle.py --kur {h.ad}"), time.time() - t0
    sebep = duman_kos(h)
    if sebep:
        return False, sebep, time.time() - t0
    tavan = adim_tavan_sn if adim_tavan_sn is not None else adim_tavani(h, tam, gunluk)
    for i, adim in enumerate(h.adimlar(tam, gunluk), 1):
        print(f"    [{i}] {adim}")
        kod, son, asti = _adim_kos([py, *adim.split()], d, tavan)
        if asti:
            # Zaman aşımı DÜŞMEDİR ama sebebi ayrı: hat damgalanmaz, bir
            # sonraki koşuda yeniden denenir, öbür hatlar koşmaya devam eder.
            return False, (f"{ZAMAN_ASIMI_IMZASI} — adım {i} ({adim}) {tavan:.0f} saniyede "
                           f"bitmedi; süreç ağacı öldürüldü. Kaynak asılmış olabilir. "
                           f"Öbür hatlar etkilenmedi."), time.time() - t0
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
    # OKUR DİLİ — koşu kaydı ve özet cümleleri sayfaya olduğu gibi basılır;
    # operatör dili burada görünsün, yayın kapısında (sayfa sınavı 17) ENGEL olur.
    for dil in okur_dili_bulgulari(hedef):
        print(_renk(f"    [UYARI] okur dili — {dil}", 33))

    yeni_tarih = _ozet_tarih(h)
    y, e = _tarih_ozeti(yeni_tarih), _tarih_ozeti(eski_tarih)

    # Veri GERİYE gidemez. 2026-08-25 bulut koşusunda Hazine hattı boş bir
    # klasörde kazıyıp 448 ihale yerine 16 buldu ve ozet.json'u 18.08.2026'dan
    # 04.06.2024'e çekti — koşu "başarılı" göründüğü için gerileme commit'lendi.
    # Tarihi geri giden hat DÜŞMÜŞ sayılır: damgalanmaz, sonraki koşuda tekrar
    # denenir ve commit adımı onu dışarıda bırakır.
    if yeni_tarih and eski_tarih:
        gerileyen = []
        for a in h.tarih_anahtarlari:
            yd, ed = _tarih_degeri(yeni_tarih.get(a, "")), _tarih_degeri(eski_tarih.get(a, ""))
            if yd and ed and yd < ed:
                gerileyen.append(f"{a}: {eski_tarih[a]} → {yeni_tarih[a]}")
        if gerileyen:
            return False, (f"VERİ GERİLEDİ — çıktı eskisinden geriye gitti "
                           f"({'; '.join(gerileyen)}). Kaynak eksik veri döndürmüş "
                           f"olabilir; hattın birikmiş veri dosyaları yerinde mi?"), time.time() - t0

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


# ── HAT SÜRESİ DEFTERİ ───────────────────────────────────────────────────────
# `kos()` her hattın süresini ZATEN ölçüyordu (dördüncü dönüş değeri) ve o sayı
# hiçbir yere yazılmıyordu. 04.09.2026'da tazeleme adımı 45 dakikalık sınırını
# doldurdu ve HANGİ HATTIN yediğini bugün hâlâ bilmiyoruz: iptal edilen koşunun
# günlükleri 404, `gunlukler/` de .gitignore'da. Ölçülmeyen bir süreden bütçe de
# sıralama da türetilemez; "sezgi ölçülmeden koda girmez" bu yüzden önce ÖLÇÜYÜ
# makine okuyabilir hâle getirmeyi gerektiriyor.
#
# Commit edilmeyen bir ölçüm, ölçülmemiş bir ölçümdür: yazma `finally` bloğunda
# (adım zaman aşımına çarpsa da koşar) ve dosya veri.yml'in `git add` listesinde.
HAT_SURESI = KOK / "bulten" / "hat_suresi.json"
SURE_KAYIT = 10                    # hat başına saklanan son koşu sayısı


def _kip_adi(tam: bool, gunluk: bool) -> str:
    return "tam" if tam else ("gunluk" if gunluk else "hafif")


def sure_oku(yol: Path | None = None) -> dict[str, list[dict]]:
    """Defteri oku. Dosya yok ya da BOZUKSA boş sözlük — istisna fırlatmaz.

    Bu defteri okuyan taraf (bütçe, sıralama, adım tavanı) onsuz da çalışmak
    zorunda: bir kayıt dosyasının bozulması hattı düşüremez."""
    y = Path(yol) if yol else HAT_SURESI
    try:
        d = json.loads(y.read_text(encoding="utf-8"))
        h = d.get("hatlar")
        return h if isinstance(h, dict) else {}
    except Exception:                                          # noqa: BLE001
        return {}


def sure_kaydet(sonuc, tam: bool, gunluk: bool = False,
                yol: Path | None = None, simdi: datetime | None = None) -> bool:
    """Koşan hatların sürelerini deftere ekle; hat başına son SURE_KAYIT koşu.

    `sonuc`: `main()`in biriktirdiği (hat, ok, mesaj, saniye) dörtlüleri.
    Döner: yazıldı mı (yazılamaması koşuyu DÜŞÜRMEZ — çağıran zaten sarmalıyor).
    """
    from datetime import timezone       # modül başındaki ortak satıra dokunmadan
    y = Path(yol) if yol else HAT_SURESI
    an = (simdi or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    kip = _kip_adi(tam, gunluk)
    defter = sure_oku(y)
    for h, ok, mesaj, sn in sonuc:
        ad = getattr(h, "ad", str(h))
        kayit = defter.get(ad)
        if not isinstance(kayit, list):
            kayit = []
        kayit.append({"an": an, "sn": round(float(sn), 1), "kip": kip,
                      # Büyük/küçük harfe DUYARSIZ: imza tek yerde tanımlı
                      # ama mesaj cümle içinde geçiyor ve bir gün yazımı değişir.
                      "sonuc": "ok" if ok else (
                          "zaman aşımı"
                          if ZAMAN_ASIMI_IMZASI.lower() in str(mesaj).lower()
                          else "düştü")})
        defter[ad] = kayit[-SURE_KAYIT:]
    y.parent.mkdir(parents=True, exist_ok=True)
    y.write_text(json.dumps(
        {"_aciklama": "Her veri hattının son koşularının süresi (saniye). Bütçe, "
                      "sıralama ve adım tavanı buradan türetilir; ölçüm birikene "
                      "kadar tohum değerler kullanılır.",
         "_kayit": SURE_KAYIT,
         "hatlar": {k: defter[k] for k in sorted(defter)}},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return True


def _sureler(hat: str, kip: str | None, yol: Path | None,
             yalniz_basarili: bool) -> list[float]:
    kayit = sure_oku(yol).get(hat) or []
    out = []
    for k in kayit:
        if not isinstance(k, dict):
            continue
        if kip and k.get("kip") != kip:
            continue
        if yalniz_basarili and k.get("sonuc") != "ok":
            continue
        try:
            out.append(float(k["sn"]))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out)


def medyan(hat: str, kip: str | None = None, yol: Path | None = None,
           yalniz_basarili: bool = True) -> float | None:
    """Hattın ölçülmüş medyan süresi (sn). Kayıt yoksa None — çağıran TOHUMA düşer."""
    v = _sureler(hat, kip, yol, yalniz_basarili)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else round((v[n // 2 - 1] + v[n // 2]) / 2, 1)


def p90(hat: str, kip: str | None = None, yol: Path | None = None,
        yalniz_basarili: bool = True) -> float | None:
    """Hattın 90. yüzdeliği (en yakın sıra). Kayıt yoksa None."""
    v = _sureler(hat, kip, yol, yalniz_basarili)
    if not v:
        return None
    import math
    return v[max(0, math.ceil(0.9 * len(v)) - 1)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("hatlar", nargs="*", help="kısa adlar: " + " ".join(HAT))
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--tam", action="store_true", help="ağır adımlar dahil")
    ap.add_argument("--gunluk", action="store_true",
                    help="günlük kip: veriyi gerçekten tazeler ama ağır arşive dokunmaz "
                         "(yalnız tanımlı hatlarda; yoksa hafife düşer)")
    ap.add_argument("--commit", action="store_true", help="bitince commit + push")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--kur", action="store_true", help="seçilen hatların .venv + requirements kurulumu (hat koşturmaz)")
    ap.add_argument("--panel", action="store_true", help="seçilen tek hattın canlı panelini aç (hazine: Dash, fx: Streamlit)")
    ap.add_argument("--denetle", action="store_true",
                    help="hiçbir şey koşturmadan ortamı denetle: python, git/node, EVDS anahtarı, "
                         "her hattın yorumlayıcısı ve paketleri")
    ap.add_argument("--gerekli", action="store_true",
                    help="yalnız resmî yayım takvimine göre TAZELENMESİ GEREKEN hatları koş "
                         "(bulten/tazeleme.py); kaynağı yayımlanmamış hat atlanır")
    ap.add_argument("--sistem-kur", action="store_true", dest="sistem_kur",
                    help="seçilen hatların gereksinimlerini .venv kurmadan bu yorumlayıcıya kur "
                         "(bulut koşucusu için)")
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
    atlanan_adlar: set[str] = set()      # --gerekli'nin bilinçle atladığı hatlar

    # Resmî yayım takvimi süzgeci: kaynağı son tazelemeden bu yana yayımlanmamış
    # hattı koşturmak, aynı veriyi ikinci kez indirmektir. 2026-08-25 bulut
    # koşusunda yedi hat 37 dakika koştu ve YEDİSİ de "veri tarihi DEĞİŞMEDİ"
    # dedi — o koşunun tamamı boşa gitti.
    if a.gerekli:
        _tz = tazeleme_modulu()
        if _tz is None:
            print(_renk("\n  --gerekli istendi ama tazeleme takvimi yüklenemedi.\n"
                        "  Süzgeçsiz devam etmek seçilen hatların HEPSİNİ koşmak olurdu;\n"
                        "  bu, --gerekli ile kaçınılmak istenen şeyin ta kendisi.\n"
                        "  Takvimsiz koşmak istiyorsanız --gerekli'yi kaldırın.", 31))
            return 3
    if a.gerekli:
        print(f"\n{'═'*64}\n  TAZELEME TAKVİMİ — hangi hat neden koşacak\n{'═'*64}")
        print(_tz.rapor([h.ad for h in secilen]))
        gerek = set(_tz.gerekli([h.ad for h in secilen]))
        atlanan = [h for h in secilen if h.ad not in gerek]
        atlanan_adlar = {h.ad for h in atlanan}
        secilen = [h for h in secilen if h.ad in gerek]
        if atlanan:
            print(f"\n  {len(atlanan)} hat atlandı (yeni yayım yok): "
                  + " ".join(h.ad for h in atlanan))
        if not secilen:
            print(_renk("\n  Tazelenmesi gereken hat yok — veri zaten güncel.", 32))
            return 0

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
    if a.sistem_kur:
        print(f"\n▶ Gereksinimler ({'tam' if tam else 'hafif'} kip) — "
              + " ".join(h.ad for h in secilen))
        if not sistem_kur(secilen, tam, a.gunluk):
            return 1

    sorunlu = []
    for h in secilen:
        e = eksik_paketler(h, tam, a.gunluk)
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
    secilen = turevleri_ekle(secilen, atlanan_adlar)

    try:
        for h in secilen:
            print(f"\n▶ {h.baslik}  ({h.klasor})")
            ok, mesaj, sn = kos(h, tam, a.gunluk)
            sonuc.append((h, ok, mesaj, sn))
            print(_renk(f"    {'✓' if ok else '✗'} {mesaj}  [{sn:.0f}s]", 32 if ok else 31))
    finally:
        # HAT SÜRESİ ÖNCE YAZILIR. Ölçünün kendisi en ucuz iş (tek küçük dosya)
        # ve ondan sonraki her adım (ev stili, damga) düşebilir; ölçü düşerse
        # bir sonraki koşu yine körlemesine bütçe yapar.
        try:
            if sonuc:
                sure_kaydet(sonuc, tam, a.gunluk)
                print(f"\n  Hat süresi deftere yazıldı: "
                      f"{HAT_SURESI.relative_to(KOK)} ({len(sonuc)} kayıt)")
        except Exception as _ex:                               # noqa: BLE001
            print(_renk(f"  [uyarı] hat süresi yazılamadı: {_ex}", 33))
        # Döngü bir istisnayla kesilse de: kopyalanmış grafikler ev stilinden
        # geçer ve BAŞARILI hatların damgası yazılır — yoksa commit adımı ham
        # Plotly HTML'ini yayınlar ve tamamlanan hat bir sonraki koşuda yeniden
        # koşar (ölçüldü: veri.yml adım sınırı gerçekten doluyor).
        ev_stili()
        # Tazeleme damgası yalnız BAŞARILI hatlara vurulur: düşen hat bir sonraki
        # koşuda yeniden denensin, "koştu sayıldı ama veri gelmedi" durumu oluşmasın.
        # --gerekli verilmese de damgalanır: hat gerçekten koştuysa takvim bunu
        # bilmeli, yoksa elle zorlanan tazeleme bir sonraki koşuda tekrar edilir.
        _tz = tazeleme_modulu()
        if _tz is not None:
            basarili = [h.ad for h, ok, _, _ in sonuc if ok]
            if basarili:
                _tz.durum_yaz(basarili)
                print(f"\n  Tazeleme damgası güncellendi: {' '.join(basarili)}")

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
