#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel tatillerin resmî listeleri (bulut koşucusu): İngiltere ve ABD.

Stratejilerin tatil takvimi yalnız 25 Aralık ve 1 Ocak'ı işlem günü saymaz (gunluk.TATIL_TAKVIM); Londra ya da New
York kapalıyken de kurallar sıradan gün gibi işlem açar. Ders bunu adıyla söyler ve o günlerin işlemlerini betimler
(ön kayıt dışı; ders_olcum.tatil_betimi). Listeler tahmin edilmez, resmî kaynaktan okunur:

  İngiltere  gov.uk'un banka tatilleri dosyası (England and Wales; ikame günler ve tek seferlik tatiller dahil)
  ABD        OPM'nin federal tatil takvimi (Federal Reserve Bankaları da federal tatillerde kapalıdır, yani dolar
             takası yapılmaz) ve Fed'in kendi tatil sayfası (yalnız yakın yıllar)
  Sınama     `holidays` kütüphanesinin aynı iki takvimi: resmî listeyle ayrıştığı gün adıyla raporlanır

Yalnız indirir; ayrıştırma yerelde (tatil.py). Var olan dosya yeniden indirilmez.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "tatil" / "ham"
BASLIK = {"User-Agent": "tto-trading-arastirma/1.0 (+https://cocoonish.github.io)",
          "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
KAYNAK = {
    "gov_uk": "https://www.gov.uk/bank-holidays.json",
    "opm": "https://www.opm.gov/policy-data-oversight/pay-leave/federal-holidays/",
    "fed_k8": "https://www.federalreserve.gov/aboutthefed/k8.htm",
}
YILLAR = range(2018, 2027)


def _ad(url: str, uzanti: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", url.split("://", 1)[-1]).strip("_")[:120] + uzanti


def getir(url: str, uzanti: str = ".html") -> dict:
    yol = HAM / _ad(url, uzanti)
    if yol.exists():
        return {"url": url, "durum": "var", "dosya": yol.name, "sha256": hashlib.sha256(yol.read_bytes()).hexdigest()}
    son = ""
    for bekle in (0, 5, 15):
        if bekle:
            time.sleep(bekle)
        try:
            r = requests.get(url, headers=BASLIK, timeout=(15, 60))
        except requests.RequestException as e:
            son = type(e).__name__
            continue
        if r.status_code == 200:
            yol.write_bytes(r.content)
            return {"url": url, "durum": 200, "dosya": yol.name, "bayt": len(r.content),
                    "sha256": hashlib.sha256(r.content).hexdigest(), "tur": r.headers.get("content-type")}
        son = f"HTTP {r.status_code}"
        if r.status_code in (403, 404, 410):
            break
    return {"url": url, "durum": son}


def kutuphane() -> dict:
    """`holidays` kütüphanesinin İngiltere (England) ve ABD federal takvimleri: yalnız sınama içindir."""
    try:
        import holidays
    except ImportError:
        return {"durum": "kütüphane yok"}
    out = {"surum": getattr(holidays, "__version__", None), "ingiltere": {}, "abd": {}}
    for y in YILLAR:
        for ad, tk in (("ingiltere", holidays.country_holidays("GB", subdiv="ENG", years=y)),
                       ("abd", holidays.country_holidays("US", years=y))):
            for g, n in sorted(tk.items()):
                out[ad][g.isoformat()] = str(n)
    return out


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    kunye = {"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kaynak": {}}
    for ad, url in KAYNAK.items():
        s = getir(url, ".json" if url.endswith(".json") else ".html")
        kunye["kaynak"][ad] = s
        print(ad, s.get("durum"), s.get("bayt"), s.get("dosya"), flush=True)
    # OPM sayfası yılları ayrı adreslerde tutuyorsa adlar sayfanın kendisinden okunur (adres tahmin edilmez).
    opm = kunye["kaynak"]["opm"]
    if opm.get("dosya"):
        metin = (HAM / opm["dosya"]).read_text(encoding="utf-8", errors="replace")
        yil_var = {y: (str(y) in metin) for y in YILLAR}
        kunye["kaynak"]["opm"]["yil_gecen"] = yil_var
        bag = sorted({b for b in re.findall(r'href="([^"]+)"', metin) if re.search(r"holiday", b, re.I)})
        kunye["kaynak"]["opm"]["tatil_baglari"] = bag[:80]
        print("opm yıllar:", yil_var, "· bağ:", len(bag), flush=True)
    k = kutuphane()
    (HAM / "holidays_kutuphanesi.json").write_text(json.dumps(k, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                                   encoding="utf-8")
    kunye["kutuphane"] = {"surum": k.get("surum"), "durum": k.get("durum"),
                          "ingiltere": len(k.get("ingiltere") or {}), "abd": len(k.get("abd") or {})}
    (HAM / "kunye.json").write_text(json.dumps(kunye, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                    encoding="utf-8")
    print(json.dumps(kunye, ensure_ascii=False, indent=1)[:4000], flush=True)
    return 0 if all(isinstance(v, dict) and v.get("dosya") for v in kunye["kaynak"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
