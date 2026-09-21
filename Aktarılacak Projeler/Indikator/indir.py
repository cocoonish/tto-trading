#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İki panelli indikatörün OHLC ARŞİVİNİ indirir ve `veri/` altına yazar.

Bulutta koşar (`.github/workflows/indikator-veri.yml`; yfinance yalnız orada
kurulu — bu oturumların koşucusu Yahoo'ya çıkamıyor). Çıktı deponun kendi
kalıbıyla dala COMMIT edilir: yayımlanan her backtest sayısının arşivi depoda
durur (CLAUDE.md, 20.09.2026) ve ölçüm ağa çıkmadan yeniden üretilebilir.

Sözleşme (`veri.py` okur): `veri/<ad>-<aralik>.csv.gz` — t (epoch sn, UTC,
barın AÇILIŞI), o, h, l, c (%.6f), v; `veri/kunye.json` her serinin bar
sayısını, kapsamını, ham CSV'nin sha256'sını ve koşu künyesini taşır.
Kapanmamış son bar düşürülür (bir ölçüm ancak kapanmış seansı ölçebilir).
Yahoo aralık tavanları: 5m/15m 60 gün, 1h 730 gün, 1d sınırsız — kısa
aralıklar her koşuda yalnız son 60 günü verir; arşiv bu yüzden ÜST ÜSTE
BİRİKTİRİR: eldeki seriyle birleştirilir, aynı açılış anı yeni indirmeden
alınır, hiçbir eski bar silinmez."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parent
VERI = KOK / "veri"
BASLANGIC = time.time()
# Kullanıcının işlem evreni (21.09.2026): FX majörleri, EUR/GBP, EUR/CHF, DXY,
# XU100, SPX, NDX, WTI, XAU. USD/TRY bilerek YOK. Ana zaman dilimi 5 dk;
# 1 sa, 4 sa ve günlük bağlam için.
SEMBOLLER = [
    ("EURUSD=X", "eurusd"), ("GBPUSD=X", "gbpusd"), ("USDJPY=X", "usdjpy"),
    ("USDCHF=X", "usdchf"), ("AUDUSD=X", "audusd"), ("USDCAD=X", "usdcad"),
    ("NZDUSD=X", "nzdusd"), ("EURGBP=X", "eurgbp"), ("EURCHF=X", "eurchf"),
    ("DX-Y.NYB", "dxy"), ("XU100.IS", "xu100"), ("^GSPC", "spx"),
    ("^NDX", "ndx"), ("CL=F", "wti"), ("GC=F", "xau"),
]
ARALIKLAR = [("1d", "max"), ("1h", "730d"), ("15m", "60d"), ("5m", "60d")]
SURE = {"1d": pd.Timedelta(days=1), "1h": pd.Timedelta(hours=1),
        "15m": pd.Timedelta(minutes=15), "5m": pd.Timedelta(minutes=5)}


def cek(sembol: str, aralik: str, donem: str):
    import yfinance as yf
    for deneme in range(4):
        try:
            d = yf.download(sembol, interval=aralik, period=donem, progress=False,
                            auto_adjust=False, threads=False)
            if d is not None and len(d):
                return d
            print(f"  {sembol} {aralik}: boş (deneme {deneme + 1})", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  {sembol} {aralik}: {type(e).__name__}: {str(e)[:120]} (deneme {deneme + 1})", flush=True)
        time.sleep(3 * (deneme + 1))
    return None


def duzle(d: pd.DataFrame) -> pd.DataFrame:
    if isinstance(d.columns, pd.MultiIndex):
        d = d.copy()
        d.columns = [c[0] for c in d.columns]
    d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    d = d.dropna(subset=["open", "high", "low", "close"])
    idx = d.index
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    d.index = idx
    return d[~d.index.duplicated(keep="last")].sort_index()


def kapanmamis_dusur(d: pd.DataFrame, aralik: str) -> pd.DataFrame:
    """Son bar, kendi aralığı kadar süre geçmemişse kapanmamıştır → düşer."""
    simdi = pd.Timestamp.now(tz="UTC")
    if len(d) and d.index[-1] + SURE[aralik] > simdi:
        return d.iloc[:-1]
    return d


def tablo(d: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({"t": (d.index.view("int64") // 10**9).astype("int64"),
                         "o": d["open"].values, "h": d["high"].values,
                         "l": d["low"].values, "c": d["close"].values,
                         "v": d["volume"].fillna(0).astype("int64").values})


def eski_oku(yol: Path) -> pd.DataFrame | None:
    if not yol.exists():
        return None
    return pd.read_csv(io.BytesIO(gzip.decompress(yol.read_bytes())))


def birlestir(eski: pd.DataFrame | None, yeni: pd.DataFrame) -> pd.DataFrame:
    if eski is None or eski.empty:
        return yeni
    b = pd.concat([eski, yeni]).drop_duplicates(subset="t", keep="last").sort_values("t")
    return b.reset_index(drop=True)


def yaz(ad: str, t: pd.DataFrame, kunye: dict) -> None:
    buf = io.StringIO()
    t.to_csv(buf, index=False, float_format="%.6f", lineterminator="\n")
    ham = buf.getvalue().encode()
    (VERI / f"{ad}.csv.gz").write_bytes(gzip.compress(ham, 9))
    kosu = os.environ.get("GITHUB_RUN_NUMBER", "yerel")
    sha = os.environ.get("GITHUB_SHA", "")[:8]
    kunye[ad] = {
        "bar": int(len(t)), "sha256": hashlib.sha256(ham).hexdigest(),
        "bas": pd.Timestamp(int(t["t"].iloc[0]), unit="s", tz="UTC").strftime("%Y-%m-%d %H:%M"),
        "son": pd.Timestamp(int(t["t"].iloc[-1]), unit="s", tz="UTC").strftime("%Y-%m-%d %H:%M"),
        "kaynak": "Yahoo Finance (yfinance), kapanmamış son bar düşürüldü, koşular üst üste biriktirilir",
        "son_kosu": f"indikator-veri.yml #{kosu}, commit {sha}, {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC",
    }
    print(f"  {ad:16s} {len(t):7d} bar · {kunye[ad]['bas']} → {kunye[ad]['son']}", flush=True)


def main() -> int:
    VERI.mkdir(exist_ok=True)
    kunye_yol = VERI / "kunye.json"
    kunye = json.loads(kunye_yol.read_text(encoding="utf-8")) if kunye_yol.exists() else {}
    toplam, eksik = 0, []
    for sembol, ad in SEMBOLLER:
        for aralik, donem in ARALIKLAR:
            if time.time() - BASLANGIC > 22 * 60:
                print(f"::warning::bütçe doldu; {ad}-{aralik} ve sonrası ATLANDI", flush=True)
                eksik.append(f"{ad}-{aralik}")
                continue
            d = cek(sembol, aralik, donem)
            if d is None:
                print(f"::warning::{ad}-{aralik} İNDİRİLEMEDİ", flush=True)
                eksik.append(f"{ad}-{aralik}")
                continue
            d = kapanmamis_dusur(duzle(d), aralik)
            if d.empty:
                eksik.append(f"{ad}-{aralik}")
                continue
            seri = f"{ad}-{aralik}"
            t = birlestir(eski_oku(VERI / f"{seri}.csv.gz"), tablo(d))
            yaz(seri, t, kunye)
            toplam += len(t)
            time.sleep(1.0)
    kunye["_kosu"] = {"eksik": eksik, "toplam_bar": toplam,
                      "zaman": f"{pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC"}
    kunye_yol.write_text(json.dumps(dict(sorted(kunye.items())), ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
    print(f"TOPLAM {toplam} bar · eksik {len(eksik)} · {time.time() - BASLANGIC:.0f} sn", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
