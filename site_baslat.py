#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — siteyi yerelde başlat (Astro geliştirme sunucusu).

Çift tıklama için: site.bat  (Windows).  Terminalden:

  python site_baslat.py                # kur (gerekiyorsa) + başlat + tarayıcıyı aç
  python site_baslat.py --port 4400    # başka port
  python site_baslat.py --derle        # üretim derlemesi (npm run build) — sunucu açmaz
  python site_baslat.py --onizle       # dist/ klasörünü sun (npm run preview)
  python site_baslat.py --kur          # yalnız npm install
  python site_baslat.py --tarayici-yok

Ne yapar:
  1. Node.js/npm var mı denetler (yoksa nereden kurulacağını yazar).
  2. site/node_modules yoksa `npm install` çalıştırır (ilk sefer birkaç dakika).
  3. `npm run dev` ile sunucuyu ön planda başlatır; Ctrl+C kapatır.
  4. Sunucu ayağa kalkınca tarayıcıyı http://localhost:<port> adresinde açar.

Not: Site, veri hatlarının ürettiği grafikleri `site/public/` altından okur — sunucu
veri üretmez. Grafikleri tazelemek için: python guncelle.py <hat>   (ör. tcmb, hazine)
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

KOK = Path(__file__).resolve().parent
SITE = KOK / "site"
VARSAYILAN_PORT = 4321

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _renk(m, k):
    return f"\033[{k}m{m}\033[0m" if sys.stdout.isatty() else m


def npm_yolu() -> str | None:
    """npm çalıştırılabilirinin yolu. Windows'ta npm.cmd'dir; shutil.which ikisini de bulur."""
    for ad in ("npm.cmd", "npm") if os.name == "nt" else ("npm",):
        y = shutil.which(ad)
        if y:
            return y
    return None


def surum(komut: list[str]) -> str | None:
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=30)
        return r.stdout.strip() or None
    except Exception:
        return None


def on_kosul() -> str | None:
    """Node/npm denetimi. Sorun varsa mesaj döndürür, yoksa None."""
    if not SITE.exists():
        return f"site klasörü yok: {SITE}  (repo kökünden çalıştırın)"
    npm = npm_yolu()
    if not npm:
        return ("Node.js/npm bulunamadı.\n"
                "    Kurulum: https://nodejs.org  → LTS sürümü, varsayılan seçeneklerle.\n"
                "    Kurduktan sonra terminali KAPATIP açın (PATH yenilensin) ve tekrar deneyin.")
    nv = surum(["node", "--version"]) or "?"
    print(f"  Node {nv} · npm {surum([npm, '--version']) or '?'}")
    return None


def kur(npm: str) -> bool:
    print("\n▶ Bağımlılıklar kuruluyor (npm install) — ilk seferde birkaç dakika sürer")
    r = subprocess.run([npm, "install"], cwd=SITE)
    if r.returncode != 0:
        print(_renk("  ✗ npm install başarısız", 31))
        return False
    print(_renk("  ✓ kurulum tamam", 32))
    return True


def ayakta_mi(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/", timeout=1.5) as y:
            return y.status < 500
    except Exception:
        return False


def tarayici_ac(port: int, zaman_asimi: float = 90.0):
    """Sunucu gerçekten cevap verince tarayıcıyı aç (sabit gecikme yerine yoklama)."""
    def _bekle():
        t0 = time.time()
        while time.time() - t0 < zaman_asimi:
            if ayakta_mi(port):
                try:
                    webbrowser.open(f"http://localhost:{port}/")
                except Exception:
                    pass
                return
            time.sleep(0.7)
    threading.Thread(target=_bekle, daemon=True).start()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=VARSAYILAN_PORT)
    ap.add_argument("--kur", action="store_true", help="yalnız npm install, sunucu açma")
    ap.add_argument("--derle", action="store_true", help="üretim derlemesi (npm run build)")
    ap.add_argument("--onizle", action="store_true", help="derlenmiş siteyi sun (npm run preview)")
    ap.add_argument("--tarayici-yok", action="store_true")
    a = ap.parse_args()

    print(f"{'═' * 64}\n  TTO Trading — site\n{'═' * 64}")
    hata = on_kosul()
    if hata:
        print(_renk(f"  ✗ {hata}", 31))
        return 1
    npm = npm_yolu()

    if not (SITE / "node_modules").exists():
        if not kur(npm):
            return 1
    elif a.kur:
        if not kur(npm):
            return 1
    if a.kur:
        return 0

    if a.derle:
        print("\n▶ Üretim derlemesi (npm run build) → site/dist")
        r = subprocess.run([npm, "run", "build"], cwd=SITE)
        print(_renk("  ✓ derleme tamam" if r.returncode == 0 else "  ✗ derleme düştü",
                    32 if r.returncode == 0 else 31))
        return r.returncode

    if a.onizle:
        komut = [npm, "run", "preview", "--", "--port", str(a.port)]
        etiket = "önizleme (derlenmiş site)"
    else:
        komut = [npm, "run", "dev", "--", "--port", str(a.port)]
        etiket = "geliştirme sunucusu (kaydettiğiniz her değişiklik anında yansır)"

    print(f"\n▶ {etiket}")
    print(_renk(f"  adres : http://localhost:{a.port}/", 36))
    print("  (kapatmak için bu pencerede Ctrl+C)")
    print("  not   : grafikler site/public altından okunur; tazelemek için "
          "python guncelle.py <hat>\n")

    if not a.tarayici_yok:
        tarayici_ac(a.port)
    try:
        return subprocess.run(komut, cwd=SITE).returncode
    except KeyboardInterrupt:
        print("\n  sunucu kapatıldı")
        return 0


if __name__ == "__main__":
    sys.exit(main())
