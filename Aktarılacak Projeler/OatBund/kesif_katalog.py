#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND — İKİNCİ YOKLAMA: kataloglar İSTENİR, seri kodu tahmin edilmez.

İlk yoklama (01.10.2026, keşif #27) ölçtü: ECB'de ülke düzeyinde GÜNLÜK getiri
yok (FM günlük kataloğu 404, aylık yalnız euro alanı), Eurostat günlük uç 404,
Stooq tarayıcı sınaması istiyor; Bundesbank, Banque de France Webstat, ABD
Hazinesi ve Yahoo açık. Bu koşu Fransa'nın günlük getirisini (TEC10) Webstat
kataloğundan ARAR ve Eurostat'ın kendi içindekiler tablosunu okur.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

UA = {"User-Agent": "Mozilla/5.0 (compatible; tto-arastirma/1.0)", "Accept": "*/*"}
WS = "https://webstat.banque-france.fr/api/explore/v2.1"


def al(url: str, sn: int = 15, sinir: int = 3_000_000) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=sn) as r:
            return r.status, r.read(sinir).decode("utf-8", "replace")
    except HTTPError as e:
        try:
            g = e.read(2000).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            g = ""
        return e.code, g
    except (URLError, TimeoutError, OSError) as e:
        return None, repr(e)


def webstat_ara(ifade: str) -> None:
    q = urllib.parse.urlencode({"where": f'search("{ifade}")', "limit": 40,
                                "select": "dataset_id,metas.default.title"})
    d, m = al(f"{WS}/catalog/datasets?{q}")
    print(f"--- webstat ara '{ifade}': durum={d}")
    if d != 200:
        print("   ", m[:400])
        return
    js = json.loads(m)
    print(f"    toplam {js.get('total_count')}")
    for r in js.get("results", []):
        t = r.get("metas", {}).get("default", {}).get("title") if "metas" in r else r.get("title")
        print(f"    {r.get('dataset_id')} | {t}")


def main() -> int:
    # 1) Webstat kataloğu — Fransa devlet tahvili getirileri
    for ifade in ("TEC 10", "TEC10", "échéance constante", "emprunts d'Etat",
                  "OAT", "obligations d'Etat 10 ans", "taux des emprunts",
                  "rendement", "FR10YT"):
        webstat_ara(ifade)
    # Webstat'ın birleşik gözlem uçları (sürüme göre adı değişir)
    for ds in ("observations", "series", "webstat-observations"):
        d, m = al(f"{WS}/catalog/datasets/{ds}?select=dataset_id")
        print(f"--- webstat veri kümesi '{ds}': durum={d} {m[:300]}")
    # 2) Eurostat içindekiler — faiz kümeleri
    d, m = al("https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt?lang=EN", sn=30,
              sinir=40_000_000)
    print(f"--- eurostat toc: durum={d} bayt={len(m)}")
    if d == 200:
        for s in m.splitlines():
            if "irt_" in s.lower() or "bond yield" in s.lower():
                print("   ", s[:240])
    for kod in ("irt_lt_mcby_d", "IRT_LT_MCBY_D", "irt_lt_mcby_m"):
        d, m = al("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
                  f"{kod}?format=JSON&lang=EN&geo=FR&lastTimePeriod=3")
        print(f"--- eurostat {kod}: durum={d} {m[:400]}")
    # 3) Bundesbank — kalan vade getirileri bir sözcük: hangi tür seri?
    d, m = al("https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
              "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=sdmx_csv"
              "&startPeriod=2026-09-20")
    print(f"--- bbk 10y son günler: durum={d}")
    for s in m.splitlines()[1:]:
        p = s.split(";")
        if len(p) > 17:
            print("   ", p[16], p[17])
    # Umlaufsrendite / gösterge getiri adayları — katalog adıyla
    for anahtar in ("D.I.UMR.RD.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A",
                    "D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A"):
        d, m = al(f"https://api.statistiken.bundesbank.de/rest/data/BBSIS/{anahtar}"
                  "?format=sdmx_csv&lastNObservations=2")
        print(f"--- bbk {anahtar}: durum={d} {m.splitlines()[1][:300] if d == 200 and len(m.splitlines()) > 1 else m[:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
