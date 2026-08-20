#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — tek seferde KURULUM (bağımlılıklar).

Yeni bir bilgisayarda depoyu klonladıktan sonra çalıştırılacak İLK şey.
Windows'ta: kur.bat (çift tıklama yeter).

  python kur.py                    # her şey: 7 veri hattı + site + Playwright
  python kur.py --hat tcmb hazine  # yalnız bu hatlar
  python kur.py --site-yok         # siteyi (npm install) atla
  python kur.py --playwright-yok   # MEDAS tarayıcısını atla (marj hattı)
  python kur.py --liste            # ne kurulacak, göster

Ne yapar:
  1. Ön koşul denetimi: Python sürümü, Node/npm, EVDS anahtarı.
  2. Her veri hattı için proje klasöründe `.venv` + `requirements.txt`
     (guncelle.py'deki kur() ile AYNI kod — iki yerde tutulmuyor).
  3. site/ için `npm install`.
  4. Yiyecek marjı hattı için Playwright Chromium (yalnız MEDAS ham dosyaları
     yoksa gerekir; varsa atlanır).
  5. Sonda özet tablo + sıradaki adımlar.

Tekrar çalıştırmak güvenlidir: var olan sanal ortam yeniden kurulmaz, yalnız
bağımlılıklar tazelenir.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent
PY = sys.executable

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}


def _renk(m, k):
    return f"\033[{k}m{m}\033[0m" if sys.stdout.isatty() else m


def guncelle_modulu():
    """guncelle.py'yi modül olarak yükle — HATLAR ve kur() oradan gelir."""
    yol = KOK / "guncelle.py"
    if not yol.exists():
        print(_renk(f"✗ guncelle.py bulunamadı: {yol}", 31))
        sys.exit(1)
    spec = importlib.util.spec_from_file_location("guncelle", yol)
    mod = importlib.util.module_from_spec(spec)
    # sys.modules'e ÖNCE yazılmalı: guncelle.py'deki @dataclass, sınıfın modülünü
    # sys.modules'te arıyor; kayıtlı değilse AttributeError ile düşüyor.
    sys.modules["guncelle"] = mod
    spec.loader.exec_module(mod)
    return mod


def npm_yolu() -> str | None:
    for ad in ("npm.cmd", "npm") if os.name == "nt" else ("npm",):
        y = shutil.which(ad)
        if y:
            return y
    return None


def on_kosullar() -> list[str]:
    """Eksik/riskli ön koşulları döndürür (boş liste = temiz)."""
    sorun = []
    print(f"  Python  {sys.version.split()[0]}  ({sys.executable})")
    if sys.version_info < (3, 10):
        sorun.append("Python 3.10+ gerekir (mevcut: %d.%d)" % sys.version_info[:2])

    npm = npm_yolu()
    if npm:
        try:
            nv = subprocess.run(["node", "--version"], capture_output=True, text=True,
                                timeout=30).stdout.strip()
        except Exception:
            nv = "?"
        print(f"  Node    {nv}  ·  npm {subprocess.run([npm, '--version'], capture_output=True, text=True).stdout.strip()}")
    else:
        print(_renk("  Node    bulunamadı — site kurulumu atlanacak "
                    "(kurmak için: https://nodejs.org, LTS)", 33))

    # Anahtar üç yerde olabilir: ortam değişkeni → kök → proje klasörü. Hatlar da
    # aynı sırayla arar; yalnız köke bakmak "anahtar yok" diye yanlış uyarı veriyordu.
    nerede = anahtar_nerede()
    if nerede:
        print(f"  EVDS    anahtar bulundu ({nerede})")
    else:
        print(_renk("  EVDS    anahtar YOK — kurulum yine de yapılır ama veri hatları "
                    "koşmaz.\n          Kökte '.evds_key' dosyası oluşturup içine yalnız "
                    "anahtarı yazın (tek satır, boşluksuz).", 33))
    return sorun


def anahtar_nerede() -> str | None:
    """EVDS anahtarı nerede bulundu? (ortam / kök / proje) — yoksa None."""
    if os.environ.get("TTO_EVDS_KEY"):
        return "TTO_EVDS_KEY ortam değişkeni"
    if (KOK / ".evds_key").exists():
        return "kök .evds_key"
    proje = sorted(p.parent.name for p in KOK.glob("*/*/.evds_key"))
    if proje:
        ek = "" if len(proje) < 4 else f" (+{len(proje) - 3})"
        return "proje klasörleri: " + ", ".join(proje[:3]) + ek
    return None


def playwright_gerekli_mi(marj_klasor: Path) -> bool:
    """MEDAS ham dosyaları depoyla geldiyse tarayıcıya gerek yok."""
    ham = marj_klasor / "data" / "raw"
    return not ((ham / "medas_madde_fiyatlari.xls").exists()
                and (ham / "medas_tarim_ufe.xls").exists())


def playwright_kur(marj_klasor: Path, hat_python) -> tuple[bool, str]:
    vpy = hat_python
    if not playwright_gerekli_mi(marj_klasor):
        return True, "gerekmiyor (MEDAS ham dosyaları mevcut)"
    print("    Playwright Chromium indiriliyor (~150 MB)…")
    r = subprocess.run([vpy, "-m", "playwright", "install", "chromium"],
                       cwd=str(marj_klasor), env=_ENV)
    return (r.returncode == 0,
            "kuruldu" if r.returncode == 0 else "BAŞARISIZ (MEDAS hasadı çalışmaz)")


def site_kur() -> tuple[bool, str]:
    npm = npm_yolu()
    if not npm:
        return False, "Node/npm yok — atlandı"
    site = KOK / "site"
    if not site.exists():
        return False, "site/ klasörü yok"
    print("    npm install (ilk seferde birkaç dakika)…")
    r = subprocess.run([npm, "install"], cwd=str(site), env=_ENV)
    return (r.returncode == 0, "kuruldu" if r.returncode == 0 else "npm install BAŞARISIZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hat", nargs="*", help="yalnız bu hatlar (boş = hepsi)")
    ap.add_argument("--site-yok", action="store_true", help="npm install yapma")
    ap.add_argument("--playwright-yok", action="store_true", help="MEDAS tarayıcısını kurma")
    ap.add_argument("--liste", action="store_true", help="ne kurulacak, göster ve çık")
    a = ap.parse_args()

    g = guncelle_modulu()
    hatlar = list(g.HATLAR)
    if a.hat:
        yanlis = [x for x in a.hat if x not in g.HAT]
        if yanlis:
            print(f"tanınmayan hat: {yanlis} — geçerli: {list(g.HAT)}")
            return 2
        hatlar = [g.HAT[x] for x in a.hat]

    print(f"{'═' * 66}\n  TTO Trading — kurulum\n{'═' * 66}")
    if a.liste:
        for h in hatlar:
            req = KOK / h.klasor / "requirements.txt"
            print(f"  {h.ad:8s} {h.baslik:26s} {h.klasor}"
                  f"{'' if req.exists() else '   (requirements.txt YOK)'}")
        if not a.site_yok:
            print(f"  {'site':8s} {'Astro sitesi (npm install)':26s} site/")
        return 0

    print("\n▶ Ön koşullar")
    sorun = on_kosullar()
    if sorun:
        for s in sorun:
            print(_renk(f"  ✗ {s}", 31))
        return 1

    sonuc: list[tuple[str, bool, str, float]] = []

    for h in hatlar:
        print(f"\n▶ {h.baslik}  ({h.klasor})")
        t0 = time.time()
        ok = g.kur(h)
        mesaj = "kuruldu" if ok else "BAŞARISIZ"
        # marj hattı: MEDAS hasadı için tarayıcı
        if ok and h.ad == "marj" and not a.playwright_yok:
            pw_ok, pw_mesaj = playwright_kur(KOK / h.klasor, g.hat_python(h))
            mesaj += f" · Playwright: {pw_mesaj}"
            ok = ok and pw_ok
        sonuc.append((h.baslik, ok, mesaj, time.time() - t0))

    if not a.site_yok:
        print("\n▶ Site (Astro)")
        t0 = time.time()
        ok, mesaj = site_kur()
        sonuc.append(("Site (npm)", ok, mesaj, time.time() - t0))

    print(f"\n{'═' * 66}\n  ÖZET\n{'═' * 66}")
    for ad, ok, mesaj, sn in sonuc:
        isaret = _renk("✓", 32) if ok else _renk("✗", 31)
        print(f"  {isaret} {ad:30s} {mesaj:48s} {sn:5.0f}s")

    dusen = [ad for ad, ok, _, _ in sonuc if not ok]
    print()
    if dusen:
        print(_renk(f"  {len(dusen)} adım düştü: {', '.join(dusen)}", 31))
        print("  Tekrar çalıştırmak güvenlidir; yalnız düşenler için:"
              "  python kur.py --hat <ad>")
    else:
        print(_renk("  Kurulum tamam.", 32))
    print("\n  Sıradaki adımlar:")
    print("    site.bat                     siteyi aç (http://localhost:4321)")
    print("    guncelle.bat                 veri hatlarını güncelle (menü)")
    print("    guncelle.bat --hepsi --tam   hepsini, ağır adımlar dahil")
    print("    panel.bat hazine | fx        canlı pano")
    if not anahtar_nerede():
        print(_renk("\n  UYARI: EVDS anahtarı yok — veri hatları koşmaz. "
                    "Kökte .evds_key dosyası oluşturun.", 33))
    return 1 if dusen else 0


if __name__ == "__main__":
    sys.exit(main())
