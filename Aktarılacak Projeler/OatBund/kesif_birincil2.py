#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND ANALİZİ — BİRİNCİL KAYNAK YOKLAMASI, İKİNCİ TUR (kesif.yml).

Birinci tur (keşif #33) 61 hedefin 39'unu açtı; açılamayanların bir kısmı
iddianın tek kaynağıydı (not takvimi, AFT ihale sonucu, Nagel'in sözü). Bu tur
iki şey yapar: (1) aynı iddialar için BAŞKA yayıncıların adreslerini dener,
(2) adresi bilinmeyen iddialar için bir arama motorunun sonuç sayfasını
indirir ve sonuçların başlık, adres ve özetini basar — özet bir kaynak
değildir; yalnız bir sonraki turda indirilecek adresi bulmaya yarar.

Hüküm kurmaz; çıktı ham girdidir. `python3 -u` ile koşar.
"""
from __future__ import annotations

import html
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from kesif_birincil import ARANAN_BAGLAM, UA, al, metne, baslik  # noqa: E402

HEDEFLER: list[tuple[str, str, list[str]]] = [
    ("jdn_not", "https://www.journaldunet.com/business/1545557-notation-de-la-france-moody-s-face-a-la-pression-apres-fitch-et-standard-poor-s/",
     [r"23\s*octobre", r"27\s*novembre", r"Moody", r"S&P|Standard"]),
    ("bourso_ihale", "https://www.boursorama.com/bourse/actualites/details-de-l-adjudication-d-oat-5ca591a04af26b9ddba86acd70d04637",
     [r"4[,.]93", r"2036", r"11[,.]999|12\s*milliards", r"5[,.]40"]),
    ("rte_bardella", "https://www.rte.ie/news/2026/0928/1593261-bardella-antisemitic-comments/",
     [r"Mediapart", r"2013", r"forger|fake|fabricat"]),
    ("euronext_cds", "https://live.euronext.com/en/financial-news/five-french-market-hot-spots-investors-radars-amid-debt-jitters",
     [r"52", r"2017", r"Barclays", r"basis points"]),
    ("hellenic_barclays", "https://www.hellenicshippingnews.com/barclays-flags-french-election-as-a-potential-risk-for-euro/",
     [r"beta", r"periphery|peripheral", r"generous", r"election"]),
    ("usn_nagel", "https://money.usnews.com/investing/news/articles/2026-10-01/ecb-focuses-on-inflation-not-bond-spreads-nagel-says",
     [r"spread", r"price stability", r"TPI|Transmission"]),
    ("cnews_anket", "https://www.cnews.fr/france/2026-09-28/presidentielle-2027-marine-le-pen-arriverait-largement-en-tete-face-edouard",
     [r"57\s*%", r"43\s*%", r"34\s*%", r"OpinionWay"]),
    ("cnbc_0831", "https://www.cnbc.com/2026/08/31/france-debt-bond-yields-budget.html",
     [r"4\.2", r"spread", r"basis points"]),
    ("cnbc_0924", "https://www.cnbc.com/2026/09/24/france-budget-debt-deficit-government.html",
     [r"spread", r"basis points", r"Lescure", r"54"]),
    ("aft_not_ua2", "https://www.aft.gouv.fr/en/frances-credit-ratings",
     [r"Moody", r"next", r"October", r"November"]),
]

SORGULAR = [
    "Moody's France sovereign rating calendar 2026 October 23",
    "calendrier agences de notation France 2026 Moody's 23 octobre S&P 27 novembre",
    "S&P Global Ratings France calendar 27 November 2026",
    "AFT adjudication 1er octobre 2026 OAT 2036 4,93",
    "Nagel spreads price stability France bonds 1 October 2026",
    "Fitch affirms France A+ 28 August 2026 deficit 5.5% 2027",
    "PLF 2027 dette publique 121,7 % 2027 119,3 %",
    "OAT Bund 100 points de base 18 septembre 2026 première fois depuis 2012",
    "Bardella Mediapart 2013 messages plainte diffamation",
    "Lagarde commission ECON 28 septembre 2026 hausse mesurée",
    "France 10-year yield highest since 2002 1 October 2026 spread 2012",
    "euro OAT Bund spread EUR/USD 1 October 2026 afternoon Italy two-year spread",
]


def ara(sorgu: str) -> list[tuple[str, str, str]]:
    """DuckDuckGo HTML sonuç sayfası; olmazsa Bing. (başlık, adres, özet)."""
    out: list[tuple[str, str, str]] = []
    adres = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": sorgu, "kl": "fr-fr"})
    kod, govde, _ = al(adres, sn=20)
    if kod == 200 and govde:
        t = govde.decode("utf-8", "replace")
        for m in re.finditer(r'(?s)class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', t):
            u = m.group(1)
            q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get("uddg")
            u = q[0] if q else u
            out.append((_duz(m.group(2)), u, _duz(m.group(3))))
    if not out:
        adres = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": sorgu, "setlang": "fr"})
        kod, govde, _ = al(adres, sn=20)
        if kod == 200 and govde:
            t = govde.decode("utf-8", "replace")
            for m in re.finditer(r'(?s)<li class="b_algo".*?<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?<p[^>]*>(.*?)</p>', t):
                out.append((_duz(m.group(2)), html.unescape(m.group(1)), _duz(m.group(3))))
        out.insert(0, ("[bing]", f"HTTP {kod}", ""))
    return out[:6]


def _duz(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"(?s)<[^>]+>", " ", s))).strip()[:300]


def yokla(hedef):
    kimlik, url, ifadeler = hedef
    kod, govde, tur = al(url, sn=45)
    if kod != 200 or not govde:
        return kimlik, url, kod, None, []
    metin = metne(govde, tur, url)
    bul = []
    for ifade in ifadeler:
        es = list(re.finditer(ifade.replace(" ", r"\s*"), metin, re.I))
        bul.append((ifade, len(es), " ⟂ ".join(metin[max(0, m.start() - ARANAN_BAGLAM):m.end() + ARANAN_BAGLAM]
                                                for m in es[:2])))
    return kimlik, url, kod, (len(metin), baslik(govde)), bul


def main() -> int:
    print(f"# {len(HEDEFLER)} hedef · {len(SORGULAR)} sorgu · {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC")
    with ThreadPoolExecutor(max_workers=6) as h:
        sonuc = list(h.map(yokla, HEDEFLER))
    for kimlik, url, kod, bilgi, bul in sonuc:
        print(f"\n=== {kimlik} · HTTP {kod} · {url}")
        if bilgi is None:
            print("    AÇILAMADI")
            continue
        print(f"    başlık: {bilgi[1]} · metin {bilgi[0]} karakter")
        for ifade, n, b in bul:
            print(f"    [{n or 'YOK'}] {ifade}" + (f" :: {b}" if n else ""))
    for s in SORGULAR:
        print(f"\n### ARAMA: {s}")
        try:
            for bas, u, oz in ara(s):
                print(f"    - {bas} | {u} | {oz}")
        except Exception as e:  # noqa: BLE001
            print(f"    arama düştü: {e}")
        time.sleep(1.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
