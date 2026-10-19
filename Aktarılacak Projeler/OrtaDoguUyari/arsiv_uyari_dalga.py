#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTA DOĞU UYARISI — üçüncü arşiv geçişi: uyarı DALGALARININ tam metni.

İlk geçiş elçilik listelerinden yalnız Şubat–Mart ve Eylül–Ekim 2026 uyarılarını indirdi. Listenin kendisi daha geniş:
on iki elçiliğin aynı gün yayımladığı uyarılar (dalga) Temmuz ve Ağustos'ta da var ve yazının en önemli sorusu —
"bu kadar çok ülkeye uyarı verildiğinde ne oldu" — o günlerin METNİNİ ister. Bu geçiş:

  1. listelerin 4.–8. sayfalarını indirir (Suudi Arabistan, İsrail ve Ürdün listeleri 3. sayfada Mart'tan sonra
     başlıyordu; kapsam elçilikten elçiliğe değişmesin),
  2. eldeki ve yeni listelerden 2026 tarihli bütün uyarı adreslerini çözer (adres tahmin edilmez),
  3. henüz indirilmemiş olanları indirir.

Yardımcılar ilk geçişten (`arsiv_uyari`); künye `kunye_dalga.json`.
"""
from __future__ import annotations

import re
import sys
import time

import arsiv_uyari as au

ab = au.ab
DESEN = re.compile(r"(january|february|march|april|may|june|july|august|september|october)-\d{1,2}-2026", re.I)


def _listedeki(cc: str, metin: str) -> set[str]:
    out = set()
    for m in re.finditer(r'href="(https?://' + re.escape(f"{cc}.usembassy.gov") + r'/[^"#?]+)"', metin):
        u = m.group(1)
        if DESEN.search(u) and ("alert" in u or "advisory" in u or "message" in u):
            out.add(u.rstrip("/") + "/")
    return out


@ab.kaynak("Elçilik uyarı dalgaları")
def dalga() -> dict:
    import json
    eldeki_url = set()
    for p in sorted(ab.HAM.glob("kunye_*.json")):
        for yol, k in json.loads(p.read_text(encoding="utf-8")).items():
            if yol.startswith("elcilik/") and k.get("durum") == 200:
                eldeki_url.add(k["url"].rstrip("/") + "/")
    sonuc = {}
    for cc, ad in au.ELCILIK.items():
        kok = f"https://{cc}.usembassy.gov"
        bulunan: set[str] = set()
        # eldeki listeler
        for p in (ab.HAM / "elcilik" / cc).glob("*.gz"):
            try:
                bulunan |= _listedeki(cc, ab.gzip.decompress(p.read_bytes()).decode("utf-8", errors="replace"))
            except Exception:  # noqa: BLE001
                pass
        kayit = {"liste": {}, "uyari": {}}
        for sayfa in range(4, 9):
            if ab.kalan() < 120:
                break
            lu = f"{kok}/category/alert/page/{sayfa}/"
            r = au._indir(lu, f"elcilik/{cc}", f"{ad} uyarı listesi")
            kayit["liste"][lu] = r
            if not r.get("dosya"):
                break
            bulunan |= _listedeki(cc, ab.gzip.decompress((ab.HAM / r["dosya"]).read_bytes()).decode("utf-8", errors="replace"))
            time.sleep(0.3)
        for u in sorted(bulunan - eldeki_url):
            if ab.kalan() < 60:
                break
            kayit["uyari"][u] = au._indir(u, f"elcilik/{cc}", f"{ad} uyarısı")
            time.sleep(0.3)
        sonuc[cc] = {"bulunan": len(bulunan), "yeni": len(kayit["uyari"]), **kayit}
        print(f"   {cc}: {len(bulunan)} uyarı adresi, {len(kayit['uyari'])} yeni", flush=True)
    return sonuc


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    dalga()
    ab.kaydet("dalga")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
