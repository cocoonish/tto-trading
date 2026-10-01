#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND — ÜÇÜNCÜ YOKLAMA: Banque de France Webstat kataloğu.

İkinci yoklama (keşif #28) `select=metas.default.title` ile 400 aldı — alan adı
tahmin edilmişti. Bu koşu alan seçmeden sorar, kaydın kendi alanlarını basar ve
bulunan aday kümelerin İLK kayıtlarını gösterir (biçim ölçülmeden çekme
yazılmaz).
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

UA = {"User-Agent": "Mozilla/5.0 (compatible; tto-arastirma/1.0)", "Accept": "*/*"}
WS = "https://webstat.banque-france.fr/api/explore/v2.1"


def al(url: str, sn: int = 20) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=sn) as r:
            return r.status, r.read(5_000_000).decode("utf-8", "replace")
    except HTTPError as e:
        try:
            return e.code, e.read(3000).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return e.code, ""
    except (URLError, TimeoutError, OSError) as e:
        return None, repr(e)


def baslik(r: dict) -> str:
    m = r.get("metas") or {}
    d = m.get("default") or {}
    return str(d.get("title") or r.get("title") or "")[:150]


ADAYLAR: list[str] = []


def ara(ifade: str, n: int = 30) -> None:
    q = urllib.parse.urlencode({"where": f'search("{ifade}")', "limit": n})
    d, m = al(f"{WS}/catalog/datasets?{q}")
    print(f"--- ara '{ifade}': durum={d}")
    if d != 200:
        print("   ", m[:300])
        return
    js = json.loads(m)
    print(f"    toplam {js.get('total_count')}")
    for r in js.get("results", []):
        ds = r.get("dataset_id")
        print(f"    {ds} | {baslik(r)}")
        ADAYLAR.append(ds)


def main() -> int:
    for ifade in ("FR10YT", "TEC10", "TEC 10", "échéance constante 10 ans",
                  "Taux de l'Echéance Constante", "rendement emprunt d'Etat 10 ans",
                  "DE10YT", "IT10YT", "ES10YT", "Bund", "FR2YT"):
        ara(ifade)
    goruldu = set()
    for ds in ADAYLAR:
        if ds in goruldu or len(goruldu) >= 12:
            continue
        goruldu.add(ds)
        d, m = al(f"{WS}/catalog/datasets/{ds}/records?limit=3")
        print(f"=== kayıtlar {ds}: durum={d}")
        print("   ", m[:1200].replace("\n", " "))
    # İlk aday kümenin uzunluğu ve uçları
    if ADAYLAR:
        ds = ADAYLAR[0]
        for sira in ("time_period_start", "time_period", "date"):
            q = urllib.parse.urlencode({"limit": 3, "order_by": f"{sira} desc"})
            d, m = al(f"{WS}/catalog/datasets/{ds}/records?{q}")
            print(f"--- {ds} order_by={sira}: durum={d} {m[:600]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
