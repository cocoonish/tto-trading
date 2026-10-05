# -*- coding: utf-8 -*-
"""Altın SPOT fiyat kaynağı yoklaması — üçüncü koşu.

NİYE VAR (05.10.2026). Ölçüldü: TCMB analitik bilançosu altını Londra sabah
fiksingi saatindeki (10:30) uluslararası fiyatla yeniden değerliyor — saatlik
GC=F ile ortak regresyonda o saatin katsayısı 1,07 (t 8), BİST ağırlıklı
ortalamasınınki 0,13 (t 0,9). İki yoklama sonucu:
  · LBMA genel JSON ucu buluttan 403 (başlıklı ve başlıksız); Bundesbank
    BBEX3 akışında XAU yok; EVDS'te Londra fiyatı yalnız AYLIK (TP.MK.LON.YTL).
  · Erişilebilen tek saatlik kaynak yfinance GC=F — VADELİ, ön ay; kontrat
    devrinde ~%0,5 sıçrar ve geçmiş kontratlar Yahoo'dan silindiği için eski
    devirler eşleştirilemez.
Bu koşu SPOT adaylarını yoklar, hiçbir şey kurmaz:
  1. Bundesbank BBK01 akışında eski Londra fiksingi kodları (WT5500–WT5530):
     her kodun adı ve son değerleri.
  2. Dukascopy açık veri ucu: XAU/USD dakika mumları (bir günlük dosya,
     LZMA sıkıştırılmış ikili). Biçim çözülür, Londra 10:30 fiyatı basılır.
  3. Stooq: XAU/USD günlük ve saatlik CSV.

Koşum (yalnız iş akışından):
    veri.yml → kesif: Aktarılacak Projeler/TCMBNetRezerv/kesif_altin_spot.py
"""
from __future__ import annotations

import datetime as dt
import lzma
import struct
import time
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
BBK = "https://api.statistiken.bundesbank.de/rest"


def al(url: str, zaman: int = 30, basliklar: dict | None = None):
    t0 = time.time()
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(basliklar or {})
    try:
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=zaman) as r:
            return r.status, r.read(), time.time() - t0
    except Exception as ex:                                  # noqa: BLE001
        govde = b""
        if hasattr(ex, "read"):
            try:
                govde = ex.read()[:200]
            except Exception:                                # noqa: BLE001
                pass
        return f"{type(ex).__name__}: {str(ex)[:100]}", govde, time.time() - t0


def bundesbank() -> None:
    print("\n▶ Bundesbank BBK01 WT55xx", flush=True)
    for n in range(5500, 5531):
        kod = f"WT{n}"
        st, g, sure = al(f"{BBK}/data/BBK01/{kod}?format=sdmx_csv&startPeriod=2026-09-25",
                         20, {"Accept": "text/csv"})
        if st != 200 or len(g) < 40:
            print(f"  {kod}: {st} ({len(g)} bayt)", flush=True)
            continue
        satirlar = g.decode("utf-8", "replace").splitlines()
        print(f"  {kod}: 200 · {len(satirlar)} satır", flush=True)
        for s in satirlar[:2] + satirlar[-3:]:
            print("    " + s[:240], flush=True)
    # Ad/başlık: SDMX yapısı yerine bir yıllık seri — kod bulunursa ayrıca dökülür.
    for kod in ("WT5511", "WT5512", "WT5513"):
        st, g, _ = al(f"{BBK}/data/BBK01/{kod}?format=sdmx_csv&startPeriod=2022-12-01",
                      40, {"Accept": "text/csv"})
        if st == 200 and len(g) > 40:
            print(f"BBK_CSV_BAS {kod}")
            print(g.decode("utf-8", "replace"))
            print(f"BBK_CSV_SON {kod}", flush=True)


def dukascopy() -> None:
    print("\n▶ Dukascopy XAU/USD dakika mumları", flush=True)
    # Ay indeksi SIFIRDAN başlar (Ocak = 00). Birim: fiyat × 1000 (XAU/USD).
    for gun in (dt.date(2026, 10, 2), dt.date(2026, 9, 30), dt.date(2024, 3, 4)):
        for taraf in ("BID", "ASK"):
            url = (f"https://datafeed.dukascopy.com/datafeed/XAUUSD/{gun.year}/"
                   f"{gun.month - 1:02d}/{gun.day:02d}/{taraf}_candles_min_1.bi5")
            st, g, sure = al(url, 30)
            print(f"  {gun} {taraf}: {st} ({len(g)} bayt, {sure:.1f} sn)", flush=True)
            if st != 200 or not g:
                continue
            try:
                ham = lzma.decompress(g)
            except Exception as ex:                          # noqa: BLE001
                print(f"    lzma: {ex}", flush=True)
                continue
            n = len(ham) // 24
            print(f"    {len(ham)} bayt, {n} mum", flush=True)
            # Kayıt: >IIIIIf  saniye(gün başından), açılış, kapanış, düşük, yüksek, hacim
            for i in (0, 1, 9 * 60, 9 * 60 + 30, 10 * 60, 10 * 60 + 30, n - 1):
                if 0 <= i < n:
                    s, a, k, d, y, v = struct.unpack(">IIIIIf", ham[i * 24:(i + 1) * 24])
                    print(f"    [{i:4d}] t+{s:5d}s  a={a} k={k} d={d} y={y} v={v:.2f}", flush=True)
    # Saatlik tik dosyası (yedek biçim)
    url = "https://datafeed.dukascopy.com/datafeed/XAUUSD/2026/09/02/09h_ticks.bi5"
    st, g, sure = al(url, 30)
    print(f"  tik 2026-10-02 09h: {st} ({len(g)} bayt)", flush=True)


def stooq() -> None:
    print("\n▶ Stooq", flush=True)
    for url in ("https://stooq.com/q/d/l/?s=xauusd&i=d",
                "https://stooq.com/q/d/l/?s=xauusd&i=60",
                "https://stooq.com/q/l/?s=xauusd&f=sd2t2ohlc&h&e=csv"):
        st, g, sure = al(url, 30)
        print(f"  {url} → {st} ({len(g)} bayt, {sure:.1f} sn)", flush=True)
        if g:
            sat = g.decode("utf-8", "replace").splitlines()
            for s in sat[:3] + sat[-3:]:
                print("    " + s[:200], flush=True)


def main() -> int:
    print("=" * 74)
    print("  ALTIN SPOT KAYNAĞI YOKLAMASI")
    print("=" * 74, flush=True)
    for f in (bundesbank, dukascopy, stooq):
        try:
            f()
        except Exception as ex:                              # noqa: BLE001
            print(f"  ! {f.__name__} düştü: {type(ex).__name__}: {ex}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
