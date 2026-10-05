# -*- coding: utf-8 -*-
"""Altın fiyatı — fiziki altın ETC'lerinin saatlik barları (dördüncü koşu).

NİYE VAR (05.10.2026). TCMB analitik bilançosu altını Londra sabah fiksingi
saatindeki (10:30) uluslararası fiyatla yeniden değerliyor (ölçüldü: saatlik
GC=F ile katsayı 1,07, t 8; BİST ağırlıklı ortalaması 0,13, t 0,9). Spot
kaynakların hepsi buluttan kapalı çıktı: LBMA 403, Bundesbank'ta seri yok,
Dukascopy 503, Stooq JavaScript doğrulaması istiyor. Erişilen tek saatlik seri
vadeli GC=F; kontrat devrinde ~%0,5 sıçrıyor ve eski devirler eşleştirilemiyor.

Aday: Londra ve Frankfurt'ta Londra saatinde işlem gören FİZİKİ altın
ETC'leri. Pay başına sabit altın hakkı taşırlar (yıllık ücret kadar yavaş
erir), vadeleri yoktur, yani devir sıçraması yapısal olarak olamaz. Yalnız
YOKLANIR: kapsam, saat kapsaması ve her iş günü Londra 10:00 ile 11:00'de
biten barların kapanışı dökülür (yerel ölçüm için). GC=F aynı biçimde yanına
yazılır — ETC ile oranı devir günlerini GÖSTERİR.

Adaylar: IGLN.L (iShares, USD) · SGLD.L (Invesco, USD) · PHAU.L (WisdomTree,
USD) · 4GLD.DE (Xetra-Gold, EUR; EURUSD=X ile çevrilir) · GC=F (kıyas).

Koşum (yalnız iş akışından):
    veri.yml → kesif: Aktarılacak Projeler/TCMBNetRezerv/kesif_altin_etc.py
"""
from __future__ import annotations

import pandas as pd

SEMBOLLER = ["IGLN.L", "SGLD.L", "PHAU.L", "4GLD.DE", "EURUSD=X", "GC=F"]


def saatlik(sembol: str) -> pd.DataFrame | None:
    import yfinance as yf
    h = yf.download(sembol, period="730d", interval="60m", progress=False,
                    auto_adjust=False, threads=False)
    if h is None or len(h) == 0:
        return None
    if isinstance(h.columns, pd.MultiIndex):
        h.columns = h.columns.get_level_values(0)
    h = h[["Open", "Close", "Volume"]].dropna(subset=["Close"])
    idx = pd.DatetimeIndex(h.index)
    h.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    return h


def main() -> int:
    print("=" * 74)
    print("  ALTIN ETC SAATLİK YOKLAMASI")
    print("=" * 74, flush=True)
    veri: dict[str, pd.DataFrame] = {}
    for s in SEMBOLLER:
        try:
            h = saatlik(s)
        except Exception as ex:                              # noqa: BLE001
            print(f"  {s}: {type(ex).__name__}: {ex}", flush=True)
            continue
        if h is None:
            print(f"  {s}: boş", flush=True)
            continue
        lon = h.index.tz_convert("Europe/London")
        saat = pd.Series(lon.hour).value_counts().sort_index()
        print(f"  {s}: {len(h)} bar · {h.index[0]} → {h.index[-1]} · "
              f"Londra saat kapsaması {dict(saat)}", flush=True)
        print(f"    son 3: {[(str(t), round(float(v), 4)) for t, v in h['Close'].tail(3).items()]}",
              flush=True)
        veri[s] = h
    # Gün başına iki değer: Londra 09:00–10:00 ve 10:00–11:00 barlarının kapanışı.
    print("\nCSV_BAS")
    print("tarih;sembol;k10;k11;hacim10;hacim11")
    for s, h in veri.items():
        lon = h.index.tz_convert("Europe/London")
        df = h.copy()
        df["gun"] = lon.date
        df["saat"] = lon.hour
        for gun, g in df.groupby("gun"):
            r9 = g[g["saat"] == 9]
            r10 = g[g["saat"] == 10]
            k10 = float(r9["Close"].iloc[-1]) if len(r9) else float("nan")
            k11 = float(r10["Close"].iloc[-1]) if len(r10) else float("nan")
            v10 = float(r9["Volume"].iloc[-1]) if len(r9) else float("nan")
            v11 = float(r10["Volume"].iloc[-1]) if len(r10) else float("nan")
            if k10 == k10 or k11 == k11:
                print(f"{gun};{s};{k10:.5f};{k11:.5f};{v10:.0f};{v11:.0f}")
    print("CSV_SON", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
