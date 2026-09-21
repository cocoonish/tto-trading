#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İki panelli indikatör — OHLC ARŞİVİ için keşif indirmesi (depoya yazmaz).

Bu oturumların koşucusu Yahoo'ya çıkamıyor; bulut keşif işi çıkabiliyor
(veri.yml `kesif`, yfinance yalnız o işte kurulu). Yayımlanacak her backtest
sayısının arşivi depoda durmak zorunda (CLAUDE.md, 20.09.2026) — o yüzden
ham OHLC burada sıkıştırılıp base64 olarak koşu kaydına basılır, oturum onu
ayrıştırıp `Aktarılacak Projeler/Indikator/veri/` altına yazar.

Biçim: her seri için `=== SERI <ad> <satir> <sha256> ===` başlığı, ardından
76 karakterlik base64 satırları (gzip'li CSV: t,o,h,l,c,v — t epoch saniye,
UTC), `=== SON <ad> ===` kapanışı. Kapanmamış son bar düşürülür (bir ölçüm
ancak kapanmış seansı ölçebilir). Yahoo aralık tavanları: 5m/15m 60 gün,
1h 730 gün, 1d sınırsız."""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import sys
import time

import pandas as pd

BASLANGIC = time.time()
SEMBOLLER = [
    ("EURUSD=X", "eurusd"), ("GBPUSD=X", "gbpusd"), ("USDJPY=X", "usdjpy"),
    ("USDCHF=X", "usdchf"), ("AUDUSD=X", "audusd"), ("USDTRY=X", "usdtry"),
    ("GC=F", "altin"), ("BTC-USD", "btcusd"), ("DX-Y.NYB", "dxy"),
    ("ES=F", "sp500"), ("XU100.IS", "bist100"), ("CL=F", "wti"),
]
ARALIKLAR = [("1d", "max"), ("1h", "730d"), ("15m", "60d"), ("5m", "60d")]


def cek(sembol, aralik, donem):
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
    d = d.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]].dropna(subset=["open", "high", "low", "close"])
    idx = d.index
    if idx.tz is None:
        idx = idx.tz_localize("UTC")
    else:
        idx = idx.tz_convert("UTC")
    d.index = idx
    return d


def kapanmamis_dusur(d: pd.DataFrame, aralik: str) -> pd.DataFrame:
    """Son bar, kendi aralığı kadar süre geçmemişse kapanmamıştır → düşer."""
    simdi = pd.Timestamp.now(tz="UTC")
    sure = {"1d": pd.Timedelta(days=1), "1h": pd.Timedelta(hours=1),
            "15m": pd.Timedelta(minutes=15), "5m": pd.Timedelta(minutes=5)}[aralik]
    if len(d) and d.index[-1] + sure > simdi:
        return d.iloc[:-1]
    return d


def bas(ad: str, d: pd.DataFrame) -> None:
    buf = io.StringIO()
    out = pd.DataFrame({"t": (d.index.view("int64") // 10**9),
                        "o": d["open"].values, "h": d["high"].values,
                        "l": d["low"].values, "c": d["close"].values,
                        "v": d["volume"].fillna(0).astype("int64").values})
    out.to_csv(buf, index=False, float_format="%.6f", lineterminator="\n")
    ham = buf.getvalue().encode()
    sik = gzip.compress(ham, 9)
    b64 = base64.b64encode(sik).decode()
    print(f"=== SERI {ad} {len(out)} {hashlib.sha256(ham).hexdigest()} ===", flush=True)
    for i in range(0, len(b64), 76):
        print(b64[i:i + 76])
    print(f"=== SON {ad} ===", flush=True)
    print(f"  {ad}: {len(out)} bar · {d.index[0]:%Y-%m-%d %H:%M} → {d.index[-1]:%Y-%m-%d %H:%M} · "
          f"gzip {len(sik)/1024:.0f} KB", flush=True)


def main() -> int:
    toplam = 0
    for sembol, ad in SEMBOLLER:
        for aralik, donem in ARALIKLAR:
            if time.time() - BASLANGIC > 16 * 60:
                print(f"BÜTÇE doldu; {ad}-{aralik} ve sonrası ATLANDI", flush=True)
                return 0
            d = cek(sembol, aralik, donem)
            if d is None:
                print(f"  {ad}-{aralik}: İNDİRİLEMEDİ", flush=True)
                continue
            d = kapanmamis_dusur(duzle(d), aralik)
            if d.empty:
                print(f"  {ad}-{aralik}: boş", flush=True)
                continue
            bas(f"{ad}-{aralik}", d)
            toplam += len(d)
            time.sleep(1.0)
    print(f"TOPLAM {toplam} bar · {time.time() - BASLANGIC:.0f} sn", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
