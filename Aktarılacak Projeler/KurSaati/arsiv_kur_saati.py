#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KUR SAATİ — Yahoo'nun günlük döviz barı HANGİ ANIN fiyatını taşıyor?

NEDEN. 02.10.2026 sabah bülteninin piyasa tablosu EUR/USD'yi 1,1327 ile
"01.10.2026 kapanışı" diye bastı; CNBC'nin (Tullett Prebon) New York 17:00
kapanışı 01.10'da 1,1241, 30.09'da 1,1328. OAT–Bund arşivinde 2010–2026
ölçüldü: Yahoo'nun D tarihli EUR/USD barı CNBC'nin D−1 kapanışından medyanda
4,6 bp, D kapanışından 27,1 bp sapıyor. Aynı arşivde 01.10 barı, gün içinde
indirildiğinde canlı fiyatı (1,1246) taşıyordu; ertesi sabah aynı bar 1,1327.
Yani bar kapandığında kapanışı günün BAŞINDAKİ fiyata dönüyor görünüyor.
Bülten ve kur hatları (ortak/usdtry.py) bu barları olduğu gibi kullanıyor.

Bu betik ağa çıkar ve HAM yanıtları arşivler; hüküm kurmaz. Ölçüm yerelde,
arşive karşı yapılır (CLAUDE.md — dış kaynak önce yoklanır; sezgi ölçülmeden
koda girmez). Arşivlenen:

  * Yahoo chart ucu: günlük (2 yıl, OHLC + meta), saatlik (60 gün),
    beş dakikalık (5 gün) — yedi sembol
  * yfinance: bültenin piyasa katmanıyla AYNI çağrı (çoklu sembol, period=1y,
    interval=1d, auto_adjust=False, group_by=ticker) ve tek sembol çağrısı
    (ortak/usdtry.py'nin çağrısı)
  * CNBC: günlük bar (2024 → bugün) ve 5 günlük beş dakikalık grafik —
    New York 17:00 kapanışı kıyas noktası

Yalnız `arastirma-veri.yml` ile bulutta koşar (paketler: yfinance).
"""
from __future__ import annotations

import gzip
import io
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0 Safari/537.36"), "Accept": "application/json"}
YAHOO = ["USDTRY=X", "EURUSD=X", "EURTRY=X", "GBPUSD=X", "USDJPY=X", "GBPTRY=X", "TRY=X"]
CNBC = ["TRY=", "EUR=", "EURTRY=", "GBP=", "JPY="]
KUNYE: dict = {"dosyalar": {}, "uyarilar": []}


def al(url: str, sn: int = 40, deneme: int = 4) -> bytes:
    son = None
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=sn) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            son = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"indirilemedi: {url[:140]} — {son!r}")


def yaz(ad: str, ham: bytes, kaynak: str) -> None:
    tampon = io.BytesIO()
    with gzip.GzipFile(fileobj=tampon, mode="wb", mtime=0) as g:
        g.write(ham)
    (VERI / ad).write_bytes(tampon.getvalue())
    KUNYE["dosyalar"][ad] = {"kaynak": kaynak, "indirme_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "bayt": len(ham)}
    print(f"  ✓ {ad} ({len(ham):,} bayt)", flush=True)


def yahoo_chart() -> None:
    for sem in YAHOO:
        for ad, q in (("1d", {"range": "2y", "interval": "1d"}), ("60m", {"range": "60d", "interval": "60m"}),
                      ("5m", {"range": "5d", "interval": "5m"})):
            q = {**q, "includePrePost": "false", "events": "history"}
            u = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sem)}?" + urllib.parse.urlencode(q)
            try:
                yaz(f"yahoo_{sem.replace('=', '').lower()}_{ad}.json.gz", al(u), f"Yahoo chart {sem} {q}")
            except Exception as e:  # noqa: BLE001
                KUNYE["uyarilar"].append(f"Yahoo {sem} {ad}: {e!r}")
                print(f"  ✗ Yahoo {sem} {ad}: {e!r}", flush=True)
            time.sleep(1.5)


def yfin() -> None:
    try:
        import yfinance as yf
    except Exception as e:  # noqa: BLE001
        KUNYE["uyarilar"].append(f"yfinance yok: {e!r}")
        return
    try:
        ham = yf.download(YAHOO[:6], period="1y", interval="1d", progress=False, auto_adjust=False,
                          group_by="ticker", threads=True)
        yaz("yfinance_coklu_1d.csv.gz", ham.to_csv().encode("utf-8"), "yfinance.download çoklu, bültenin çağrısı")
    except Exception as e:  # noqa: BLE001
        KUNYE["uyarilar"].append(f"yfinance çoklu: {e!r}")
    for sem in ("USDTRY=X", "EURUSD=X"):
        try:
            ham = yf.download(sem, start=(datetime.now(timezone.utc) - timedelta(days=400)).date().isoformat(),
                              end=(datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(), interval="1d",
                              progress=False, auto_adjust=False, threads=False)
            yaz(f"yfinance_{sem.replace('=', '').lower()}_1d.csv.gz", ham.to_csv().encode("utf-8"),
                "yfinance.download tek sembol, ortak/usdtry.py'nin çağrısı")
        except Exception as e:  # noqa: BLE001
            KUNYE["uyarilar"].append(f"yfinance {sem}: {e!r}")
        time.sleep(1.5)


def cnbc() -> None:
    yarin = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%d")
    for sem in CNBC:
        u = (f"https://ts-api.cnbc.com/harmony/app/bars/{urllib.parse.quote(sem)}/1D/20240101000000/"
             f"{yarin}000000/adjusted/EST5EDT.json")
        try:
            yaz(f"cnbc_{sem.rstrip('=').lower()}_1d.json.gz", al(u, sn=30), f"CNBC bars {sem} 1D")
        except Exception as e:  # noqa: BLE001
            KUNYE["uyarilar"].append(f"CNBC {sem} 1D: {e!r}")
        u = f"https://ts-api.cnbc.com/harmony/app/charts/5D.json?symbol={urllib.parse.quote(sem)}"
        try:
            yaz(f"cnbc_{sem.rstrip('=').lower()}_5d.json.gz", al(u, sn=30), f"CNBC charts 5D {sem}")
        except Exception as e:  # noqa: BLE001
            KUNYE["uyarilar"].append(f"CNBC {sem} 5D: {e!r}")
        time.sleep(1)


def main() -> int:
    VERI.mkdir(exist_ok=True)
    KUNYE["baslangic_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for ad, f in (("Yahoo chart", yahoo_chart), ("yfinance", yfin), ("CNBC", cnbc)):
        print(f"── {ad}", flush=True)
        f()
    KUNYE["bitis_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (VERI / f"kunye_{KUNYE['baslangic_utc'][:16].replace(':', '')}.json").write_text(
        json.dumps(KUNYE, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── bitti · {len(KUNYE['dosyalar'])} dosya · {len(KUNYE['uyarilar'])} uyarı")
    for u in KUNYE["uyarilar"]:
        print("  ! " + u)
    return 0 if KUNYE["dosyalar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
