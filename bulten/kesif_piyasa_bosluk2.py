#!/usr/bin/env python3
"""Boş gelen bir önceki seansın kapanışı meta alanlarından doğru okunur mu — ölçüm.

İlk keşif (kesif_piyasa_bosluk.py, 23.09.2026 06:47 UTC) gösterdi ki:
  · Yahoo 22.09 için satır AÇIYOR ama kapanışı BOŞ (null) veriyor — hisse
    endeksleri, ETF'ler, DXY, MOVE, BTC; 04:20'de dolu olan ^TNX ve ^VIX
    06:47'de boşalmış. Üretimdeki dropna() o satırı atıyor.
  · Piyasa KAPALIYKEN meta.regularMarketPrice, regularMarketTime gününün
    kapanışıdır (XU100 13198,84 = haberdeki kapanış; günlük satırı dolu olan
    altı sembolde fark 0,00 bp). Gün içi son bar yedek OLAMAZ (BIST medyan
    9 bp, azami 63 bp).
Açık kalan: piyasa ŞU AN AÇIKKEN (BTC 7/24, Hang Seng, Şanghay, DXY) meta
fiyatı bugünün canlı fiyatıdır; dünün kapanışı ancak "önceki kapanış"
alanlarından gelebilir. Bu betik o alanları, dünün günlük kapanışı DOLU olan
sembollerde birebir kıyaslar — alan doğruysa boş gün için yedek olabilir.

Ağa çıkar, depoya YAZMAZ, HÜKÜM KURMAZ.
"""
from __future__ import annotations

import sys
import time
import datetime as dt

sys.path.insert(0, ".")
from yfinance.data import YfData  # noqa: E402

import piyasa as P  # noqa: E402

SIMDI = dt.datetime.now(dt.timezone.utc)
print(f"şimdi {SIMDI:%Y-%m-%d %H:%M} UTC")
URL = "https://query2.finance.yahoo.com/v8/finance/chart/{}"
VERI = YfData()


def ham(sym: str, **params) -> dict | None:
    for bekle in (0, 5, 15, 45):
        if bekle:
            time.sleep(bekle)
        try:
            r = VERI.get(URL.format(sym), params=params, timeout=30)
            if r.status_code == 429:
                continue
            res = ((r.json().get("chart") or {}).get("result") or [])
            return res[0] if res else None
        except Exception as e:  # noqa: BLE001
            print(f"    ! {sym}: {type(e).__name__}: {str(e)[:100]}")
    return None


def gunluk(r: dict) -> list[tuple[dt.date, float | None]]:
    off = (r.get("meta") or {}).get("gmtoffset") or 0
    ts = r.get("timestamp") or []
    kap = (((r.get("indicators") or {}).get("quote") or [{}])[0].get("close")) or [None] * len(ts)
    return [((dt.datetime.fromtimestamp(t, dt.timezone.utc) + dt.timedelta(seconds=off)).date(), c)
            for t, c in zip(ts, kap)]


def bp(a, b):
    return "—" if a is None or b in (None, 0) else f"{(a / b - 1) * 1e4:+.2f}"


ilk = True
print("\nsembol       bugün(yerel) · son DOLU günlük (gün=kapanış) · range=1d: chartPrev / previousClose / "
      "regularMarketPreviousClose · fark(bp, son dolu günlüğe)")
for v in P.VARLIKLAR:
    k = v.kod
    r5 = ham(k, range="5d", interval="1d", includePrePost="false")
    r1 = ham(k, range="1d", interval="1d", includePrePost="false")
    if not r5 or not r1:
        print(f"  {k:12s} ölçülemedi")
        continue
    m1 = r1.get("meta") or {}
    if ilk:
        print("  meta alanları (range=1d):", sorted(m1.keys()))
        ilk = False
    off = m1.get("gmtoffset") or 0
    bugun = (SIMDI + dt.timedelta(seconds=off)).date()
    satir = gunluk(r5)
    once = [(g, c) for g, c in satir if g < bugun]
    dolu = [(g, c) for g, c in once if c is not None]
    bos = [g for g, c in once if c is None]
    son_dolu = dolu[-1] if dolu else (None, None)
    cp, pc, rpc = m1.get("chartPreviousClose"), m1.get("previousClose"), m1.get("regularMarketPreviousClose")
    # Kıyas yalnız dünün (bugünden önceki son satırın) DOLU olduğu sembolde anlamlı
    son_satir = once[-1] if once else (None, None)
    kiyas = son_satir[1]
    print(f"  {k:12s} {bugun} · {son_dolu[0]}={son_dolu[1] if son_dolu[1] is None else round(son_dolu[1], 4)}"
          f" · boş: {','.join(str(g)[5:] for g in bos) or '—'}"
          f" · cp {cp} / pc {pc} / rpc {rpc}"
          f" · fark cp {bp(cp, kiyas)} pc {bp(pc, kiyas)} rpc {bp(rpc, kiyas)}"
          f"{'' if kiyas is not None else '  (dünkü satır BOŞ — kıyas yok)'}")
    time.sleep(0.25)

print("\nbitti", dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "UTC")
