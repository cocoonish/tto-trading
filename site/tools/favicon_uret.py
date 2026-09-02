#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Favicon PNG türevleri — SVG'den, başsız Chromium ile.

Site simgesi yalnız SVG'ydi: iOS ana ekranı, Safari sekmesi ve bazı RSS
okuyucuları SVG'yi okumaz, boş kare gösterir. Bu araç site/public/favicon.svg'yi
üç boyutta PNG'ye çevirir; Base.astro bunları <link> ile ilan eder.

    python3 site/tools/favicon_uret.py            # 32 · 180 (apple-touch) · 512
    python3 site/tools/favicon_uret.py --chromium /yol/chrome

Tek kaynak SVG'dir: renk ya da harf değişirse SVG düzenlenir ve araç yeniden
koşturulur; PNG'ler elle çizilmez. Chromium yolu og_kart ile ortak (chromium_bul).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
from og_kart import chromium_bul  # noqa: E402

PUBLIC = BURASI.parent / "public"
SVG = PUBLIC / "favicon.svg"
BOYUTLAR = {32: "favicon-32.png", 180: "apple-touch-icon.png", 512: "favicon-512.png"}


def ciz(chromium: str, boyut: int, hedef: Path) -> None:
    svg = SVG.read_text(encoding="utf-8")
    html = ("<!doctype html><html><head><meta charset='utf-8'><style>"
            "html,body{margin:0;padding:0;background:#f5f0e6;overflow:hidden}"
            f"svg{{display:block;width:{boyut}px;height:{boyut}px}}</style></head><body>"
            + svg + "</body></html>")
    with tempfile.TemporaryDirectory() as td:
        h = Path(td) / "ikon.html"
        h.write_text(html, encoding="utf-8")
        basli = "headless_shell" in chromium
        cmd = [chromium, "--headless" if basli else "--headless=new",
               "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
               "--force-device-scale-factor=1", f"--window-size={boyut},{boyut}",
               f"--screenshot={hedef}", "--virtual-time-budget=1500", h.as_uri()]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not hedef.exists():
            raise SystemExit(f"{hedef.name}: çizim düştü ({r.returncode}): {r.stderr[-400:]}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chromium", help="Chromium/headless_shell yolu (verilmezse aranır)")
    a = ap.parse_args()
    ch = chromium_bul(a.chromium)
    if not ch:
        raise SystemExit("Chromium bulunamadı — --chromium ile yol ver")
    if not SVG.exists():
        raise SystemExit(f"{SVG} yok")
    for boyut, ad in BOYUTLAR.items():
        hedef = PUBLIC / ad
        ciz(ch, boyut, hedef)
        print(f"  {ad:22s} {boyut}×{boyut} · {hedef.stat().st_size} bayt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
