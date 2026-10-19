#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTA DOĞU UYARISI — ikinci arşiv geçişi: ilk geçişin bulamadıkları.

  1. Polymarket: bugünkü "ateşkes … tarihine kadar sürer mi" dizisinin öbür vadeleri (aynı olaydaki bütün piyasalar)
     ve İran etiketli açık olaylar; fiyat geçmişleriyle.
  2. Wikipedia: emsal olayların sayfaları BAŞLIĞIYLA (arama motoru ilk geçişte hız sınırına takıldı); her istek
     arasında bekleme.
Yardımcılar ilk geçişten (`arsiv_uyari`); künye `kunye_ek.json`.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse

import arsiv_uyari as au

ab = au.ab

WIKI_BASLIK = [
    "Twelve-Day War", "United States strikes on Iranian nuclear sites", "Killing of Qasem Soleimani",
    "Operation Martyr Soleimani", "2019–2021 Persian Gulf crisis", "Operation Infinite Reach", "Operation Desert Fox",
    "1998 United States embassy bombings", "2003 invasion of Iraq", "Gulf War", "Operation Desert Storm",
    "2012 Benghazi attack", "2013 Ghouta chemical attack", "Timeline of the Syrian civil war (May–August 2013)",
    "October 2026 Houthi attacks on Saudi Arabian airports", "Houthi blockade of Saudi Arabia",
    "September 2026 United States strikes on Iran", "Islamabad Memorandum", "2026 Iran war ceasefire",
    "Operation Epic Fury", "2026 Iran war ceasefire", "Islamabad Talks", "Reactions to the 2026 Iran war",
    "2024 Iran–Israel conflict", "April 2024 Iranian strikes on Israel", "October 2024 Iranian strikes on Israel",
    "2023 Hamas-led attack on Israel", "Attacks on United States bases during the Gaza war",
]
PM_EK_ARAMA = ["ceasefire continues through", "US x Iran ceasefire continues", "US x Iran", "Iran strike November",
               "Iran midterms", "US strike Iran November", "US strike Iran December"]


@ab.kaynak("Polymarket ek")
def polymarket_ek() -> dict:
    rapor = {"olay": {}, "piyasa": {}}
    adaylar: dict[str, dict] = {}
    adresler = [("events_iran", "https://gamma-api.polymarket.com/events?" + urllib.parse.urlencode(
        {"tag_slug": "iran", "closed": "false", "limit": 200}))]
    for q in PM_EK_ARAMA:
        adresler.append((f"arama_{ab._dosya_adi(q)}", "https://gamma-api.polymarket.com/public-search?" +
                         urllib.parse.urlencode({"q": q, "events_status": "active", "limit_per_type": 50})))
    # Bugünkü piyasanın olayı: slug'ından olay listesi
    adresler.append(("olay_31ekim", "https://gamma-api.polymarket.com/markets?slug=us-x-iran-ceasefire-continues-through-october-31-20260917"))
    for ad, url in adresler:
        d, gv, j = au._json(url)
        rapor["olay"][ad] = d
        if d == 200 and gv:
            ab.yaz(f"polymarket/ek_{ad}.json.gz", gv, url, d, not_="Polymarket ek liste")
        olaylar = []
        if isinstance(j, dict):
            olaylar = j.get("events") or []
        elif isinstance(j, list):
            olaylar = j
        for ev in olaylar:
            for m in (ev.get("markets") or [ev]) if isinstance(ev, dict) else []:
                soru = m.get("question") or ""
                if au.PM_SORU.search(soru) and au.PM_KONU.search(soru):
                    adaylar.setdefault(str(m.get("id")), {"soru": soru})
            for e2 in (ev.get("events") or []) if isinstance(ev, dict) else []:
                es = e2.get("slug")
                if es:
                    u2 = "https://gamma-api.polymarket.com/events?slug=" + urllib.parse.quote(es)
                    d2, g2, j2 = au._json(u2)
                    if d2 == 200 and g2:
                        ab.yaz(f"polymarket/ek_olay_{ab._dosya_adi(es)[:60]}.json.gz", g2, u2, d2, not_="Polymarket olay")
                        for e3 in (j2 or []):
                            for m in e3.get("markets") or []:
                                adaylar.setdefault(str(m.get("id")), {"soru": m.get("question") or ""})
        time.sleep(0.3)
    print(f"   Polymarket ek: {len(adaylar)} aday", flush=True)
    for mid, p in list(adaylar.items())[:80]:
        if ab.kalan() < 120:
            break
        if (ab.HAM / f"polymarket/piyasa_{mid}.json.gz").exists():
            continue
        url = f"https://gamma-api.polymarket.com/markets/{mid}"
        d, gv, m = au._json(url)
        if d == 200 and gv:
            ab.yaz(f"polymarket/piyasa_{mid}.json.gz", gv, url, d, not_=p["soru"][:160])
        tok = []
        try:
            tok = json.loads((m or {}).get("clobTokenIds") or "[]")
        except Exception:  # noqa: BLE001
            tok = []
        r = {"soru": p["soru"], "gecmis": {}}
        if tok:
            for ad_, fid in (("gunluk", 1440), ("saatlik", 60)):
                hu = "https://clob.polymarket.com/prices-history?" + urllib.parse.urlencode(
                    {"market": tok[0], "interval": "max", "fidelity": fid})
                d2, g2, j2 = au._json(hu)
                if d2 == 200 and g2:
                    ab.yaz(f"polymarket/gecmis_{mid}_{ad_}.json.gz", g2, hu, d2, not_=p["soru"][:160])
                r["gecmis"][ad_] = d2
                time.sleep(0.25)
        rapor["piyasa"][mid] = r
        print(f"   {mid} {p['soru'][:90]}", flush=True)
    return rapor


@ab.kaynak("Wikipedia başlıkla")
def wiki_baslik() -> dict:
    sonuc = {}
    for b in dict.fromkeys(WIKI_BASLIK):
        hu = "https://en.wikipedia.org/api/rest_v1/page/html/" + urllib.parse.quote(b.replace(" ", "_"), safe="")
        sonuc[b] = au._indir(hu, "wiki", f"Wikipedia: {b}", sn=45)
        time.sleep(1.5)
    return sonuc


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    polymarket_ek()
    wiki_baslik()
    ab.kaydet("ek")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
