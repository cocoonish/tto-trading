#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bağlantı önizleme kartları (Open Graph, 1200×630) — ev stilinde, kütüphanesiz.

Site bir bağlantı olarak paylaşıldığında (X, Telegram, LinkedIn, WhatsApp)
gösterilen kart. Dört sürüm: genel, bülten, teknik, analiz. Şablon
og_kart/kart.html; yazı tipleri sitenin kendi paketlerinden (node_modules)
okunur, yani kart ile sayfa aynı harflerle konuşur.

Çizim, Playwright'ın kurulu Chromium'uyla ekran görüntüsü alarak yapılır; ek
paket istemez. Çıktı site/public/og/<ad>.png — Base.astro og:image olarak
sayfanın bölümüne göre bunlardan birini verir.

    python3 site/tools/og_kart.py            # dört bölüm kartı + eksik analiz kartları
    python3 site/tools/og_kart.py --analiz   # yalnız analiz kartları (yeni/eskimiş yazılar)
    python3 site/tools/og_kart.py --chromium /yol/chrome
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parent
SABLON = BURASI / "og_kart" / "kart.html"
CIKTI = SITE / "public" / "og"
FONT = SITE / "node_modules"

KARTLAR = {
    "genel": ("Türkiye makro & piyasa araştırmaları",
              "Türkiye makrosunu ölçülmüş verilerle okumak.",
              "Günlük bülten · haftalık teknik analiz · analiz yazıları · veri panoları · dersler"),
    "bulten": ("Bülten",
               "Hafta içi her sabah günlük, pazar akşamı haftaya bakış.",
               "51 enstrüman · rejim panosu · takvim · günün okuması · her sayı kendi tarihiyle"),
    "teknik": ("Haftalık Teknik Analiz",
               "Altı enstrüman, üç zaman dilimi, ölçüme dayalı senaryolar.",
               "ABD 2Y/10Y · DXY · EUR/USD · USD/CHF · BIST 100"),
    "analiz": ("Analiz",
               "Tek bir gelişmeyi mekanizmasına kadar açan uzun yazılar.",
               "Yönetici özeti · ölçüm · tarihsel emsal · fiyat etkisi · izleme listesi"),
}


def chromium_bul(verilen: str | None) -> str | None:
    adaylar = [verilen] if verilen else []
    adaylar += [os.environ.get("TTO_CHROMIUM", "")]
    kok = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))
    if kok.exists():
        # headless_shell ÖNCE: eski başsız kipte pencere boyutu görüntü alanına
        # birebir eşittir. Yeni başsız kip (chrome --headless=new) pencere
        # çerçevesi payı bırakıyor ve 630 piksellik kartın alt şeridini kırpıyordu.
        adaylar += [str(p) for p in sorted(kok.glob("chromium_headless_shell-*/chrome-linux/headless_shell"))]
        adaylar += [str(p) for p in sorted(kok.glob("chromium-*/chrome-linux/chrome"))]
    adaylar += [shutil.which(a) or "" for a in ("chromium", "chromium-browser", "google-chrome", "chrome")]
    for a in adaylar:
        if a and Path(a).exists():
            return a
    return None


def ciz(chromium: str, ad: str, baslik: str, alt: str, dip: str) -> Path:
    html = SABLON.read_text(encoding="utf-8")
    html = (html.replace("{{FONT}}", FONT.as_uri())
                .replace("{{BOLUM}}", ad if ad != "genel" else "cocoonish.github.io")
                .replace("{{BASLIK}}", baslik)
                .replace("{{ALT}}", alt)
                .replace("{{DIP}}", dip))
    CIKTI.mkdir(parents=True, exist_ok=True)
    hedef = CIKTI / f"{ad}.png"
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "kart.html"
        h.write_text(html, encoding="utf-8")
        basli = "headless_shell" in chromium
        cmd = [chromium, "--headless" if basli else "--headless=new",
               "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
               "--force-device-scale-factor=1", "--window-size=1200,630",
               f"--screenshot={hedef}", "--virtual-time-budget=3000", h.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not hedef.exists():
            raise SystemExit(f"{ad}: çizim düştü ({r.returncode}): {r.stderr[-400:]}")
    return hedef


def _kacis(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def analiz_kartlari(ch: str, yalniz_eksik: bool = True) -> int:
    """Her analiz yazısı için kendi kartı: /og/analiz/<slug>.png — başlık, tez, tarih.
    Ön bilgi ortak ayrıştırıcıdan (ortak/on_bilgi.py) okunur; sayfa dosya
    varsa bunu, yoksa bölüm kartını kullanır."""
    sys.path.insert(0, str(SITE.parent / "ortak"))
    import on_bilgi  # noqa: E402
    dizin = SITE / "src" / "content" / "analiz"
    hedef_dizin = CIKTI / "analiz"
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    n = 0
    for yol in sorted(dizin.glob("*.mdx")):
        hedef = hedef_dizin / f"{yol.stem}.png"
        if yalniz_eksik and hedef.exists() and hedef.stat().st_mtime >= yol.stat().st_mtime:
            continue
        fm = on_bilgi.ayristir(yol.read_text(encoding="utf-8"))
        baslik = str(fm.get("title") or yol.stem)
        # Tarih öneki ilk satırda ayrı yazılır; başlıkta yinelenmez.
        import re as _re
        m = _re.match(r"^\s*(\d{1,2}\s+\S+\s+\d{4})\s+(.*)$", baslik)
        tarih, govde = (m.group(1), m.group(2)) if m else (str(fm.get("pubDate") or ""), baslik)
        if len(govde) > 96:
            govde = govde[:93].rsplit(" ", 1)[0] + "…"
        tez = str(fm.get("ozet") or "")
        if len(tez) > 190:
            tez = tez[:187].rsplit(" ", 1)[0] + "…"
        html = (SABLON.read_text(encoding="utf-8")
                .replace("{{FONT}}", FONT.as_uri())
                .replace("{{BOLUM}}", _kacis(f"Analiz · {tarih}"))
                .replace("{{BASLIK}}", _kacis(govde))
                .replace("{{ALT}}", _kacis(tez))
                .replace("{{DIP}}", _kacis("Yönetici özeti · ölçüm · tarihsel emsal · fiyat etkisi")))
        with tempfile.TemporaryDirectory() as td:
            h = Path(td) / "kart.html"; h.write_text(html, encoding="utf-8")
            basli = "headless_shell" in ch
            cmd = [ch, "--headless" if basli else "--headless=new", "--no-sandbox", "--disable-gpu",
                   "--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=1200,630",
                   f"--screenshot={hedef}", "--virtual-time-budget=3000", h.as_uri()]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if r.returncode != 0 or not hedef.exists():
                raise SystemExit(f"{yol.stem}: kart çizilemedi: {r.stderr[-300:]}")
        n += 1
        print(f"  ✓ {hedef.relative_to(SITE)}")
    return n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chromium", help="Chromium/Chrome ikilisi")
    p.add_argument("--analiz", action="store_true", help="yalnız analiz kartlarını (eksik/eskimiş) çiz")
    p.add_argument("--hepsi", action="store_true", help="analiz kartlarını da yeniden çiz")
    a = p.parse_args()
    ch = chromium_bul(a.chromium)
    if not ch:
        print("Chromium bulunamadı — kartlar çizilmedi (mevcut PNG'ler kalır).", file=sys.stderr)
        return 1
    if not a.analiz:
        for ad, (baslik, alt, dip) in KARTLAR.items():
            y = ciz(ch, ad, baslik, alt, dip)
            print(f"  ✓ {y.relative_to(SITE)} ({y.stat().st_size // 1024} KB)")
    n = analiz_kartlari(ch, yalniz_eksik=not a.hepsi)
    print(f"  analiz kartı: {n} çizildi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
