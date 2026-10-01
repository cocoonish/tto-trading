#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND — DÖRDÜNCÜ YOKLAMA: Fransa'nın (ve akranların) GÜNLÜK 10 yıllığı.

Üçüncü yoklama (keşif #29) ölçtü: Webstat kataloğu günlük TEC eğrisini
(`fm-d-fr-eur-fr2-bb-frmoytec10-hsta`) ve aylık gösterge getirilerini (FR, DE,
IT, ES) ADIYLA listeliyor ama `records` ucu 0 kayıt döndürüyor — katalog
kayıtları yalnız üst veri. Bu koşu iki şeyi sorar: (1) Webstat'ta verinin
asıl durduğu yer (küme üst verisi, dışa aktarma ucu, kayıt taşıyan kümeler),
(2) günlük tarihçe veren başka uçlar. Her aday tek atış, 12 saniye.
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0 Safari/537.36"), "Accept": "*/*",
      "Accept-Language": "en-US,en;q=0.8"}
WS = "https://webstat.banque-france.fr/api/explore/v2.1"
TEC = "fm-d-fr-eur-fr2-bb-frmoytec10-hsta"


def al(url: str, sn: int = 12, sinir: int = 600_000) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=sn) as r:
            return r.status, r.read(sinir).decode("utf-8", "replace")
    except HTTPError as e:
        try:
            return e.code, e.read(1500).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return e.code, ""
    except (URLError, TimeoutError, OSError) as e:
        return None, repr(e)


def bas(ad: str, d, m: str, n: int = 700) -> None:
    print(f"--- {ad}: durum={d} bayt={len(m)}")
    print("    " + m[:n].replace("\n", "\n    "))


def main() -> int:
    # 1) Webstat: kümenin kendi üst verisi (nerede durduğunu söyleyen alanlar)
    d, m = al(f"{WS}/catalog/datasets/{TEC}")
    print(f"--- webstat üst veri {TEC}: durum={d}")
    if d == 200:
        js = json.loads(m)
        for k in ("has_records", "visibility", "features", "attachments", "alternative_exports",
                  "data_visible", "fields"):
            print(f"    {k}: {json.dumps(js.get(k), ensure_ascii=False)[:500]}")
        md = (js.get("metas") or {})
        for k, v in md.items():
            print(f"    metas.{k}: {json.dumps(v, ensure_ascii=False)[:900]}")
    for uc in (f"{WS}/catalog/datasets/{TEC}/exports/csv?limit=5",
               f"{WS}/catalog/datasets/{TEC}/exports/json?limit=5"):
        bas("webstat dışa aktarma " + uc.rsplit("/", 1)[-1], *al(uc), n=500)
    q = urllib.parse.urlencode({"where": "has_records", "limit": 20})
    d, m = al(f"{WS}/catalog/datasets?{q}")
    print(f"--- webstat kayıt taşıyan kümeler: durum={d}")
    if d == 200:
        js = json.loads(m)
        print(f"    toplam {js.get('total_count')}")
        for r in js.get("results", []):
            t = ((r.get("metas") or {}).get("default") or {}).get("title")
            print(f"    {r.get('dataset_id')} | {str(t)[:120]}")
    else:
        print("    " + m[:300])
    # 2) CNBC grafik ucu — günlük tarihçe
    for sem in ("FR10Y-FR", "DE10Y-DE", "IT10Y-IT", "ES10Y-ES", "FR2Y-FR", "DE2Y-DE"):
        for aralik in ("5Y", "ALL"):
            d, m = al(f"https://ts-api.cnbc.com/harmony/app/charts/{aralik}.json?symbol={sem}")
            ozet = m[:260]
            if d == 200:
                try:
                    js = json.loads(m)
                    ps = js.get("barData", {}).get("priceBars", [])
                    ozet = (f"bar={len(ps)} ilk={ps[0] if ps else None} son={ps[-1] if ps else None}")
                except Exception as e:  # noqa: BLE001
                    ozet = "JSON değil " + repr(e)[:80] + " " + m[:200]
            print(f"--- cnbc {sem} {aralik}: durum={d} {ozet[:600]}")
    # 3) MarketWatch indirme ucu
    for sem in ("TMBMKFR-10Y", "TMBMKDE-10Y"):
        u = (f"https://www.marketwatch.com/investing/bond/{sem.lower()}/downloaddatapartial?"
             "startdate=09/01/2026%2000:00:00&enddate=10/01/2026%2000:00:00&daterange=d30"
             "&frequency=p1d&csvdownload=true&downloadpartial=false&newdates=false&countrycode=bx")
        bas(f"marketwatch {sem}", *al(u), n=300)
    # 4) Banque de France sayfası (TEC indirme bağlantısı aranır)
    d, m = al("https://www.banque-france.fr/fr/statistiques/taux-et-cours/"
              "taux-indicatifs-des-bons-du-tresor-et-oat")
    print(f"--- bdf tec sayfası: durum={d} bayt={len(m)}")
    for satir in m.split('"'):
        if any(x in satir.lower() for x in (".csv", ".xls", "download", "telecharg")):
            print("    bağ:", satir[:200])
    # 5) Banco de España — günlük faiz tabloları
    for u in ("https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/ti_1_7.csv",
              "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/ti_1_8.csv"):
        bas("bde " + u.rsplit("/", 1)[-1], *al(u), n=500)
    return 0


if __name__ == "__main__":
    sys.exit(main())
