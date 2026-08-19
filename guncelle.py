#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — tüm veri hatlarını tek yerden güncelle.

Kullanım:
  python guncelle.py                    # etkileşimli menü: hangileri, hafif/tam, commit?
  python guncelle.py --hepsi            # 7 hattın hepsi (hafif mod)
  python guncelle.py tcmb reer          # yalnız bunlar
  python guncelle.py --hepsi --tam      # ağır adımlar dahil (FX GDELT+FinBERT, Hazine scraper)
  python guncelle.py --hepsi --commit   # bitince siteye kopyalanan çıktıları commit'le + push
  python guncelle.py --liste            # hatları göster, hiçbir şey koşturma
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
  · EVDS anahtarı: TTO_EVDS_KEY ortam değişkeni → kök .evds_key → <proje>/.evds_key. Hatlar
    kendi içinde de aynı sırayla arar; burada yalnız erken uyarı verilir.
  · Ev stili (site/tools/plotly_stil.py) her koşunun sonunda TEK KEZ uygulanır.
"""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys, time
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
    tarih_anahtari: str = "_tarih" # ozet.json'da veri tarihini taşıyan alan (tazelik denetimi)
    panel: list[str] = field(default_factory=list)  # canlı panel komutu (python'dan sonraki argümanlar)

    def adimlar(self, tam: bool) -> list[str]:
        return (self.tam or self.hafif) if tam else self.hafif


P = Path("Aktarılacak Projeler")
HATLAR: list[Hat] = [
    Hat("tcmb", "TCMB Net Rezerv", P / "TCMBNetRezerv", "tcmb-net-rezerv",
        ["net_rezerv.py", "grafik.py", "ozet_uret.py"], [],
        {"tcmb_rezerv_grafik.html": "grafik.html"}, tarih_anahtari="g_tarih"),
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
    Hat("marj", "Yiyecek Hizmetleri Marjı", Path("Research/marj"), "yiyecek-hizmetleri-marj",
        ["src/web_cikti.py", "src/ozet_uret.py"],
        ["src/run_all.py", "src/web_cikti.py", "src/ozet_uret.py"],
        {"output/web/*.html": "*", "output/ozet.json": "ozet.json"},
        "tam kip: EVDS/TÜİK'ten yeniden çeker; MEDAS için Playwright"),
]
HAT = {h.ad: h for h in HATLAR}


def _renk(m, k):  # k: 32 yeşil, 31 kırmızı, 33 sarı, 36 camgöbeği
    return f"\033[{k}m{m}\033[0m" if sys.stdout.isatty() else m


EVDS_HATLAR = {"tcmb", "usdtry", "reer", "yabanci", "marj"}


def anahtar_uyar(secilen: list["Hat"]):
    if os.environ.get("TTO_EVDS_KEY"): return
    if (KOK / ".evds_key").exists():
        os.environ["TTO_EVDS_KEY"] = (KOK / ".evds_key").read_text(encoding="utf-8").strip(); return
    eksik = [h.ad for h in secilen if h.ad in EVDS_HATLAR and not (KOK / h.klasor / ".evds_key").exists()]
    if eksik:
        print(_renk(f"  [UYARI] EVDS anahtarı yok: {', '.join(eksik)} hatları düşecek. "
                    "Çözüm: kök klasöre .evds_key dosyası (tek satır anahtar) ya da TTO_EVDS_KEY ortam değişkeni.", 33))


def _ozet_tarih(h: Hat) -> str | None:
    """Sitedeki ozet.json'daki veri tarihi — koşu öncesi/sonrası kıyas için."""
    import json
    y = SITE / h.slug / "ozet.json"
    try:
        return str(json.load(open(y, encoding="utf-8")).get(h.tarih_anahtari))
    except Exception:
        return None


def kos(h: Hat, tam: bool) -> tuple[bool, str, float]:
    d = KOK / h.klasor
    t0 = time.time()
    eski_tarih = _ozet_tarih(h)
    py = hat_python(h)
    if py != PY:
        print(f"    (yorumlayıcı: {Path(py).relative_to(KOK) if py.startswith(str(KOK)) else py})")
    for i, adim in enumerate(h.adimlar(tam), 1):
        print(f"    [{i}] {adim}")
        r = subprocess.run([py, *adim.split()], cwd=d, env=_COCUK_ENV)
        if r.returncode != 0:
            ipucu = ""
            if py == PY and not (d / ".venv").exists():
                ipucu = f" — bağımlılık eksikse: python guncelle.py --kur {h.ad}  (ya da bat\\{h.slug}\\kur.bat)"
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
    yeni_tarih = _ozet_tarih(h)
    if yeni_tarih and yeni_tarih == eski_tarih:
        return True, f"{n} dosya kopyalandı — {_renk('veri tarihi DEĞİŞMEDİ: ' + yeni_tarih, 33)}", time.time() - t0
    return True, f"{n} dosya kopyalandı · veri {eski_tarih or '?'} → {yeni_tarih}", time.time() - t0


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
    subprocess.run(["git", "commit", "-q", "-m", f"veri: {adlar} güncellendi (guncelle.py)"], cwd=KOK)
    r = subprocess.run(["git", "push"], cwd=KOK)
    return r.returncode == 0


def menu() -> tuple[list[Hat], bool, bool]:
    print("\nHatlar:")
    for i, h in enumerate(HATLAR, 1):
        print(f"  {i}. {h.ad:8s} {h.baslik:26s} {_renk(h.not_, 36) if h.not_ else ''}")
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
    a = ap.parse_args()

    if a.liste:
        for h in HATLAR:
            print(f"{h.ad:8s} {h.baslik:26s} hafif: {' → '.join(h.hafif)}")
            if h.tam: print(f"{'':8s} {'':26s} tam  : {' → '.join(h.tam)}   ({h.not_})")
        return 0

    if a.hepsi: secilen, tam, cm = list(HATLAR), a.tam, a.commit
    elif a.hatlar:
        yanlis = [x for x in a.hatlar if x not in HAT]
        if yanlis: print(f"tanınmayan hat: {yanlis} — geçerli: {list(HAT)}"); return 2
        secilen, tam, cm = [HAT[x] for x in a.hatlar], a.tam, a.commit
    else:
        secilen, tam, cm = menu()
    if not secilen: print("hat seçilmedi"); return 2

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
        print(f"  {_renk('✓', 32) if ok else _renk('✗', 31)} {h.baslik:26s} {mesaj:34s} {sn:5.0f}s")
    dusen = [h for h, ok, _, _ in sonuc if not ok]
    if cm:
        if dusen:
            print(_renk(f"\n  {len(dusen)} hat düştü — commit yine de yapılıyor (başarılı çıktılar için).", 33))
        commit_push([h for h, ok, _, _ in sonuc if ok])
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
