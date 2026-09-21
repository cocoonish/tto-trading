#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İki panelli indikatör — OHLC ARŞİVİ için keşif indirmesi (depoya yazmaz).

Bu oturumların koşucusu Yahoo'ya çıkamıyor; bulut keşif işi çıkabiliyor
(veri.yml `kesif`, yfinance yalnız o işte kurulu). Yayımlanacak her backtest
sayısının arşivi depoda durmak zorunda (CLAUDE.md, 20.09.2026) — o yüzden
ham OHLC burada sıkıştırılıp base64 olarak koşu kaydına basılır, oturum onu
ayrıştırıp `Aktarılacak Projeler/Indikator/veri/` altına yazar.

Biçim: her seri için `=== SERI <ad> <satir> <olcek> <sha256> ===` başlığı,
ardından 2000 karakterlik base64 satırları, `=== SON <ad> ===` kapanışı.
Yük: xz ile sıkıştırılmış FARK tablosu (dt, do, h−o, o−l, c−o, v; fiyatlar
ölçek·fiyat tam sayısı, do bir önceki kapanışa göre). Koşu kaydı aracı yalnız
son 5.000 satırı veriyor (#230'da 95 bin satırın 5 bini geldi, 500 bin bar
kayboldu; kaydın tam indirmesi de koşucu depolamasına çıkamıyor), o yüzden
satır az ve yoğun. sha256 HAM CSV'nin (t,o,h,l,c,v · %.6f) sağlamasıdır;
ayrıştırıcı farkları açıp CSV'yi kurar ve ona karşı sınar — kodlama katmanı
da kapının içinde. Kapanmamış son bar düşürülür (bir ölçüm ancak kapanmış
seansı ölçebilir). Yahoo aralık tavanları: 5m/15m 60 gün, 1h 730 gün, 1d
sınırsız."""
from __future__ import annotations

import base64
import hashlib
import io
import lzma
import sys
import time

import numpy as np
import pandas as pd

BASLANGIC = time.time()
SEMBOLLER = [
    ("EURUSD=X", "eurusd"), ("GBPUSD=X", "gbpusd"), ("USDJPY=X", "usdjpy"),
    ("USDCHF=X", "usdchf"), ("AUDUSD=X", "audusd"), ("USDTRY=X", "usdtry"),
    ("GC=F", "altin"), ("BTC-USD", "btcusd"), ("DX-Y.NYB", "dxy"),
    ("ES=F", "sp500"), ("XU100.IS", "bist100"), ("CL=F", "wti"),
]
ARALIKLAR = [("1d", "max"), ("1h", "730d"), ("15m", "60d"), ("5m", "60d")]
SATIR = 2000


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
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
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


def olcek_bul(d: pd.DataFrame) -> int:
    """Fiyatların ondalık basamağı (en çok 6) → 10^k. Tam sayıya çevirince fark
    tablosu kayıpsız kalır; 6 basamak %.6f yazımıyla aynı sözleşme."""
    for k in range(0, 7):
        olc = 10 ** k
        if all(np.allclose(d[c].values * olc, np.round(d[c].values * olc), atol=1e-6)
               for c in ("open", "high", "low", "close")):
            return olc
    return 10 ** 6


def ham_csv(d: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    out = pd.DataFrame({"t": (d.index.view("int64") // 10**9),
                        "o": d["open"].values, "h": d["high"].values,
                        "l": d["low"].values, "c": d["close"].values,
                        "v": d["volume"].fillna(0).astype("int64").values})
    out.to_csv(buf, index=False, float_format="%.6f", lineterminator="\n")
    return buf.getvalue().encode()


def fark_tablosu(d: pd.DataFrame, olcek: int) -> bytes:
    t = (d.index.view("int64") // 10**9).astype("int64")
    o, h, l, c = (np.round(d[k].values * olcek).astype("int64") for k in ("open", "high", "low", "close"))
    v = d["volume"].fillna(0).astype("int64").values
    dt = np.diff(t, prepend=t[0])
    do = o - np.concatenate(([o[0]], c[:-1]))
    tab = np.column_stack([dt, do, h - o, o - l, c - o, v])
    ilk = f"{t[0]} {o[0]}\n".encode()
    satirlar = "\n".join(" ".join(map(str, r)) for r in tab).encode()
    return lzma.compress(ilk + satirlar, preset=9 | lzma.PRESET_EXTREME)


def bas(ad: str, d: pd.DataFrame) -> None:
    ham = ham_csv(d)
    olcek = olcek_bul(d)
    yuk = fark_tablosu(d, olcek)
    b64 = base64.b64encode(yuk).decode()
    print(f"=== SERI {ad} {len(d)} {olcek} {hashlib.sha256(ham).hexdigest()} ===", flush=True)
    for i in range(0, len(b64), SATIR):
        print(b64[i:i + SATIR])
    print(f"=== SON {ad} ===", flush=True)
    print(f"  {ad}: {len(d)} bar · {d.index[0]:%Y-%m-%d %H:%M} → {d.index[-1]:%Y-%m-%d %H:%M} · "
          f"xz {len(yuk)/1024:.0f} KB · {len(b64)//SATIR + 1} satır", flush=True)


def main() -> int:
    toplam, satir = 0, 0
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
