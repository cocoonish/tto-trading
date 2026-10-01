#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND — KAYNAK YOKLAMASI (seri ölçülmeden önce kapı ölçülür).

Her aday uç 8 saniyeyle bir kez denenir; koşu bir dakikada biter. Seri
çekilmez: yalnız kapının açık olup olmadığı, yanıtın biçimi ve kataloğun
ne sunduğu ölçülür (CLAUDE.md — "dış kaynak önce YOKLANIR, sonra kurulur";
"kaynağın kataloğu TAHMİN EDİLMEZ, İSTENİR").

`requests` değil `urllib`: ortak emniyet `requests`i üç denemeli sarar ve
yoklama tek atış olmalı.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from urllib.error import HTTPError, URLError

UA = {"User-Agent": "Mozilla/5.0 (compatible; tto-arastirma/1.0)",
      "Accept": "*/*"}

ADAYLAR = [
    # ECB Data Portal
    ("ecb_irs_fr_aylik",
     "https://data-api.ecb.europa.eu/service/data/IRS/M.FR.L.L40.CI.0000.EUR.N.Z"
     "?lastNObservations=3&format=csvdata"),
    ("ecb_fm_katalog_gunluk_getiri",
     "https://data-api.ecb.europa.eu/service/data/FM/D......YLD"
     "?detail=serieskeysonly&format=csvdata"),
    ("ecb_fm_katalog_aylik_getiri",
     "https://data-api.ecb.europa.eu/service/data/FM/M......YLD"
     "?detail=serieskeysonly&format=csvdata"),
    ("ecb_yc_aaa_2y",
     "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y"
     "?lastNObservations=3&format=csvdata"),
    ("ecb_exr_usd",
     "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
     "?lastNObservations=3&format=csvdata"),
    # Eurostat — Maastricht ölçütü uzun vadeli getiri, GÜNLÜK
    ("eurostat_irt_lt_mcby_d",
     "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
     "irt_lt_mcby_d?format=JSON&lang=EN&sinceTimePeriod=2026-09-20"),
    # Bundesbank — federal menkul kıymet getirileri, kalan vade 10 ve 2 yıl
    ("bbk_10y",
     "https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
     "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=sdmx_csv&lastNObservations=3"),
    ("bbk_2y",
     "https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
     "D.I.ZST.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A?format=sdmx_csv&lastNObservations=3"),
    # Banque de France Webstat
    ("bdf_webstat_katalog",
     "https://webstat.banque-france.fr/api/explore/v2.1/catalog/datasets?limit=3"),
    # Stooq — günlük tahvil getirileri
    ("stooq_10fry", "https://stooq.com/q/d/l/?s=10fry.b&i=d"),
    ("stooq_10dey", "https://stooq.com/q/d/l/?s=10dey.b&i=d"),
    ("stooq_2fry", "https://stooq.com/q/d/l/?s=2fry.b&i=d"),
    # ABD Hazinesi günlük getiri eğrisi
    ("ust_2026",
     "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
     "daily-treasury-rates.csv/2026/all?type=daily_treasury_yield_curve"
     "&field_tdr_date_value=2026&page&_format=csv"),
    # Yahoo ham uç (yfinance ayrıca aşağıda)
    ("yahoo_chart_eurusd",
     "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?range=5d&interval=1d"),
]


def yokla(ad: str, url: str) -> dict:
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=8) as r:
            govde = r.read(400_000)
            durum = r.status
    except HTTPError as e:
        return {"ad": ad, "durum": e.code, "sn": round(time.monotonic() - t0, 1),
                "hata": str(e)[:160]}
    except (URLError, TimeoutError, OSError) as e:
        return {"ad": ad, "durum": None, "sn": round(time.monotonic() - t0, 1),
                "hata": repr(e)[:160]}
    metin = govde.decode("utf-8", "replace")
    return {"ad": ad, "durum": durum, "sn": round(time.monotonic() - t0, 1),
            "bayt": len(govde), "metin": metin}


def ozet(k: dict) -> None:
    print(f"--- {k['ad']}: durum={k['durum']} süre={k['sn']} sn "
          f"bayt={k.get('bayt')} {k.get('hata', '')}")
    m = k.get("metin")
    if not m:
        return
    ad = k["ad"]
    if "katalog_gunluk" in ad or "katalog_aylik" in ad:
        satirlar = m.splitlines()
        print(f"    satır: {len(satirlar)}; başlık: {satirlar[0][:200] if satirlar else ''}")
        anahtar = [s.split(",")[0] for s in satirlar[1:]]
        # Ülke düzeyinde 10 ve 2 yıllık gösterge adayları — tamamı adıyla basılır.
        for s in satirlar[1:]:
            if any(x in s for x in ("10Y", "2Y", "_10", "_2")):
                print("    ", s[:220])
        print(f"    toplam anahtar: {len(anahtar)}")
        return
    if ad.startswith("eurostat"):
        try:
            js = json.loads(m)
            boy = js.get("dimension", {})
            for d in boy:
                kat = boy[d].get("category", {}).get("index", {})
                anahtarlar = list(kat)[:60] if isinstance(kat, dict) else kat
                print(f"    boyut {d}: {len(kat)} → {anahtarlar}")
            print(f"    değer sayısı: {len(js.get('value', {}))}; güncelleme: {js.get('updated')}")
        except Exception as e:  # noqa: BLE001
            print("    JSON değil:", repr(e)[:120], m[:300])
        return
    print("    " + m[:700].replace("\n", "\n    "))


def main() -> int:
    for ad, url in ADAYLAR:
        ozet(yokla(ad, url))
    print("--- yfinance")
    try:
        import yfinance as yf
        for kod in ("EURUSD=X", "^TNX", "DX-Y.NYB"):
            h = yf.Ticker(kod).history(period="max", interval="1d", auto_adjust=False)
            print(f"    {kod}: n={len(h)} ilk={h.index.min()} son={h.index.max()} "
                  f"son_kapanis={h['Close'].iloc[-1] if len(h) else None}")
    except Exception as e:  # noqa: BLE001
        print("    yfinance düştü:", repr(e)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
