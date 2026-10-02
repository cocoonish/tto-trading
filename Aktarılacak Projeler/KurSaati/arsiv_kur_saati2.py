#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KUR SAATİ (2) — Yahoo'nun SAATLİK döviz barı gün sonunu doğru taşıyor mu?

İlk arşiv (arsiv_kur_saati.py) ölçtü: Yahoo'nun kapanmış GÜNLÜK döviz barında
yüksek ve düşük günün gerçek aralığı, ama "kapanış" alanı günün BAŞINDAKİ
fiyat (EUR/USD 01.10: kapanış 1,13272 ≈ açılış 1,13268, en düşük 1,12194;
CNBC gün sonu 1,1241). Ham chart ucu bulut koşucusuna 429 verdi; yfinance
çerezle geçti. Bu betik bültenin piyasa tablosundaki on iki döviz sembolünün
yfinance saatlik (60 gün) ve beş dakikalık (5 gün) barlarını ve aynı anda
günlük barlarını arşivler. Hüküm kurmaz; ölçüm yerelde.

Yalnız `arastirma-veri.yml` ile bulutta koşar (paketler: yfinance).
"""
from __future__ import annotations

import gzip
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
FX = ["USDTRY=X", "EURTRY=X", "GBPTRY=X", "EURUSD=X", "USDJPY=X", "GBPUSD=X", "USDCHF=X",
      "AUDUSD=X", "NZDUSD=X", "USDCAD=X", "USDSEK=X", "USDNOK=X"]
KUNYE: dict = {"dosyalar": {}, "uyarilar": []}


def yaz(ad: str, df, kaynak: str) -> None:
    ham = df.to_csv().encode("utf-8")
    t = io.BytesIO()
    with gzip.GzipFile(fileobj=t, mode="wb", mtime=0) as g:
        g.write(ham)
    (VERI / ad).write_bytes(t.getvalue())
    KUNYE["dosyalar"][ad] = {"kaynak": kaynak, "indirme_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                             "satir": int(len(df))}
    print(f"  ✓ {ad} ({len(df)} satır)", flush=True)


def main() -> int:
    import yfinance as yf
    VERI.mkdir(exist_ok=True)
    KUNYE["baslangic_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for aralik, donem in (("60m", "60d"), ("5m", "5d"), ("1d", "3mo")):
        for deneme in range(4):
            try:
                ham = yf.download(FX, period=donem, interval=aralik, progress=False, auto_adjust=False,
                                  group_by="ticker", threads=False)
                if ham is None or len(ham) == 0:
                    raise RuntimeError("boş çerçeve")
                yaz(f"yf_fx_{aralik}.csv.gz", ham, f"yfinance.download {len(FX)} sembol period={donem} interval={aralik}")
                break
            except Exception as e:  # noqa: BLE001
                KUNYE["uyarilar"].append(f"{aralik} deneme {deneme + 1}: {e!r}")
                time.sleep(20 * (deneme + 1))
        time.sleep(3)
    KUNYE["bitis_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (VERI / f"kunye2_{KUNYE['baslangic_utc'][:16].replace(':', '')}.json").write_text(
        json.dumps(KUNYE, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── bitti · {len(KUNYE['dosyalar'])} dosya · uyarılar: {KUNYE['uyarilar']}")
    return 0 if KUNYE["dosyalar"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
