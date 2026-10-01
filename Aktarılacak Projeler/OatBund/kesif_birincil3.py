#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND ANALİZİ — BİRİNCİL KAYNAK YOKLAMASI, ÜÇÜNCÜ TUR (kesif.yml).

İkinci tur (keşif #34) not takvimini açamadı: AFT bütün yollarda 403, arama
motorunun yedeği sorguyu tanımadı. Bu tur (1) adayı ikinci turda bulunan
sayfaları GENİŞ bağlamla indirir (ihale sonucunun bütün satırları, bir ay
önceki fark tahmininin sahibi), (2) arama sorgularını aralıklı ve az sayıda
yollar (birinci arama motoru hızlı ardışık sorguda kesiliyor — ölçüldü).

Hüküm kurmaz. `python3 -u` ile koşar.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kesif_birincil import al, metne, baslik  # noqa: E402
from kesif_birincil2 import ara  # noqa: E402

BAGLAM = 420
HEDEFLER: list[tuple[str, str, list[str]]] = [
    ("bourso_ihale", "https://www.boursorama.com/bourse/actualites/details-de-l-adjudication-d-oat-5ca591a04af26b9ddba86acd70d04637",
     [r"MATURITE", r"TOTAL"]),
    ("emprunt_not", "https://empruntpatriotique.fr/notation-france-agences-standard-poor-fitch-moodys-2026/",
     [r"calendrier", r"octobre", r"novembre", r"Moody", r"Fitch", r"Scope"]),
    ("ethifinance", "https://www.ethifinance.com/wp-content/uploads/2025/12/Sovereign-Ratings-Calendar_EN_2026.pdf",
     [r"France"]),
    ("cnbc_0831", "https://www.cnbc.com/2026/08/31/france-debt-bond-yields-budget.html",
     [r"fair value", r"year-end forecast", r"2024/2025"]),
    ("guardian_bardella", "https://www.theguardian.com/world/2026/sep/29/jordan-bardella-national-rally-antisemitism-claims-france",
     [r"Mediapart", r"lawsuit|legal"]),
    ("aft_takvim", "https://www.aft.gouv.fr/fr/calendrier-notations-france", [r"Moody", r"octobre", r"novembre"]),
]
SORGULAR = [
    "Moody's France rating review 23 October 2026",
    "S&P France notation 27 novembre 2026",
    "Nagel spreads price stability ECB tools 1 October 2026 France",
    "Fitch France prochaine revue notation 2027 calendrier",
]


def main() -> int:
    print(f"# {len(HEDEFLER)} hedef · {len(SORGULAR)} sorgu · {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC")
    for kimlik, url, ifadeler in HEDEFLER:
        kod, govde, tur = al(url, sn=45)
        print(f"\n=== {kimlik} · HTTP {kod} · {url}")
        if kod != 200 or not govde:
            print("    AÇILAMADI")
            continue
        metin = metne(govde, tur, url)
        print(f"    başlık: {baslik(govde)} · metin {len(metin)} karakter")
        for ifade in ifadeler:
            es = list(re.finditer(ifade, metin, re.I))
            print(f"    [{len(es) or 'YOK'}] {ifade}")
            for m in es[:6]:
                print("       › " + metin[max(0, m.start() - BAGLAM):m.end() + BAGLAM])
    for s in SORGULAR:
        time.sleep(9)
        print(f"\n### ARAMA: {s}")
        try:
            for bas, u, oz in ara(s):
                print(f"    - {bas} | {u} | {oz}")
        except Exception as e:  # noqa: BLE001
            print(f"    arama düştü: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
