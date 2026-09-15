#!/usr/bin/env python3
"""5 ve 15 dakikalık FX barları — backtest için ham girdi, HÜKÜM DEĞİL.

Neden: Brooks indikatörünün eşikleri derste 5 dakikalık barda kalibre; sitedeki
ölçüm 1 saat ve üstünde. Kullanıcı 5 dakikalık EUR/USD'de "örtüşme çizgisi hep
eşiğin üstünde" dedi ve 1 saatlikte ölçüldü: 13 serinin 9'unda %100. Dersin
kendi ölçeğinde de böyle mi — ancak o ölçekte veriyle cevaplanır.

Yahoo bu oturumlardan kapalı; bulut koşucusu açık. Çıktı depoya YAZILMAZ
(keşif işi contents: read): gzip+base64 olarak log'a dökülür, iki işaret
arasından okunur. 60 gün 5 dakikalık FX ≈ 12.000 bar/parite."""
import base64, gzip, io, sys, time

def cek(sembol, aralik, gun):
    import yfinance as yf
    for deneme in range(4):
        try:
            d = yf.download(sembol, interval=aralik, period=f"{gun}d",
                            progress=False, auto_adjust=False, threads=False)
            if d is not None and len(d):
                return d
            print(f"  {sembol} {aralik}: boş çerçeve (deneme {deneme+1})")
        except Exception as e:  # noqa: BLE001
            print(f"  {sembol} {aralik}: {type(e).__name__}: {str(e)[:100]} (deneme {deneme+1})")
        time.sleep(15 * (deneme + 1))
    return None

def dok(ad, d):
    import pandas as pd
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d[["Open", "High", "Low", "Close"]].dropna()
    buf = io.StringIO()
    for t, r in d.iterrows():
        buf.write(f"{int(pd.Timestamp(t).timestamp())},{r['Open']:.6f},{r['High']:.6f},{r['Low']:.6f},{r['Close']:.6f}\n")
    ham = buf.getvalue().encode()
    b64 = base64.b64encode(gzip.compress(ham, 9)).decode()
    print(f"\n=== {ad} · {len(d)} bar · {d.index[0]} → {d.index[-1]} · {len(ham)//1024} KB ham · {len(b64)//1024} KB b64 ===")
    print(f"<<<{ad}>>>")
    for i in range(0, len(b64), 76):
        print(b64[i:i+76])
    print(f"<<</{ad}>>>")

def main():
    print("5/15 dakikalık FX keşfi")
    isler = [("EURUSD=X", "5m", 59, "eurusd-5dk"), ("EURUSD=X", "15m", 59, "eurusd-15dk"),
             ("USDCHF=X", "15m", 59, "usdchf-15dk"), ("USDJPY=X", "15m", 59, "usdjpy-15dk"),
             ("USDCHF=X", "5m", 59, "usdchf-5dk")]
    ok = 0
    for sembol, aralik, gun, ad in isler:
        d = cek(sembol, aralik, gun)
        if d is None:
            print(f"  {ad}: ÇEKİLEMEDİ"); continue
        dok(ad, d); ok += 1
        time.sleep(3)
    print(f"\n{ok}/{len(isler)} seri döküldü")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
