#!/usr/bin/env python3
"""Piyasa fotoğrafında bir önceki seansın barı neden eksik — ölçüm, hüküm değil.

Neden: 23.09.2026 04:20 UTC bülten koşusunda 51 enstrümanın 23'ü (bütün nakit
hisse endeksleri, ETF'ler, DXY, MOVE ve Bitcoin) 22.09 Salı barını TAŞIMIYORDU;
seri 21.09'dan doğrudan 23.09'un canlı barına atlıyordu (canlı bar yerleşmemiş
kuralıyla düştü, geriye 21.09 kaldı). Döviz, vadeliler ve ABD getirileri 22.09'u
taşıyordu. Bitcoin'de aynı boşluk neredeyse HER sabah var (22.09 koşusunda
21.09 yok, 21.09 koşusunda 20.09 yok).

Bu betik ağa çıkar, HÜKÜM KURMAZ, yalnız ölçer:
  (A) üretim çağrısının birebir tekrarı: hangi sembol hangi son barı taşıyor
  (B) ham chart ucu (yfinance düzeltmeleri OLMADAN): son satırların zaman
      damgası (UTC ve borsa saati), kapanışı, ve meta alanları
      (regularMarketTime/Price, currentTradingPeriod) — boşluk kaynakta mı,
      yfinance'in "canlı satır birleştirme" düzeltmesinde mi
  (C) yedek yolların sadakati: (1) meta.regularMarketPrice, piyasa kapalıyken,
      o günün günlük kapanışına eşit mi; (2) gün içi (5 dk · 1 sa) SON barın
      kapanışı günlük kapanışa ne kadar yakın — son 60 günde, sembol sembol
Ölçüm olmadan onarım koda girmez (CLAUDE.md — sezgi ölçülmeden koda girmez).
"""
from __future__ import annotations

import sys
import time
import datetime as dt
import statistics as st

sys.path.insert(0, ".")
import pandas as pd  # noqa: E402
import yfinance as yf  # noqa: E402
from yfinance.data import YfData  # noqa: E402

import piyasa as P  # noqa: E402

SIMDI = dt.datetime.now(dt.timezone.utc)
print(f"yfinance {yf.__version__} · pandas {pd.__version__} · şimdi {SIMDI:%Y-%m-%d %H:%M} UTC")

ETKILENEN = ["XU100.IS", "XU030.IS", "XBANK.IS", "XUSIN.IS", "TUR", "^GSPC", "^NDX",
             "^DJI", "^RUT", "^STOXX", "^GDAXI", "^FCHI", "^FTSE", "FTSEMIB.MI",
             "^HSI", "000001.SS", "^MOVE", "DX-Y.NYB", "HYG", "LQD", "EMB", "EEM",
             "BTC-USD", "^N225"]
KONTROL = ["USDTRY=X", "EURUSD=X", "GC=F", "BZ=F", "^TNX", "^VIX"]
URL = "https://query2.finance.yahoo.com/v8/finance/chart/{}"
BEKLEME = (5, 15, 45)
VERI = YfData()


def ham(sym: str, **params) -> dict | None:
    """Ham chart ucu (yfinance'in çerez/crumb oturumuyla) — 429'a yeniden dener."""
    for bekle in (0,) + BEKLEME:
        if bekle:
            time.sleep(bekle)
        try:
            r = VERI.get(URL.format(sym), params=params, timeout=30)
            if r.status_code == 429:
                continue
            j = r.json()
            res = (j.get("chart") or {}).get("result") or []
            return res[0] if res else None
        except Exception as e:  # noqa: BLE001
            print(f"    ! {sym} {params}: {type(e).__name__}: {str(e)[:100]}")
    print(f"    ! {sym} {params}: 429 — ölçülemedi")
    return None


def satirlar(r: dict) -> list[tuple[dt.datetime, float | None]]:
    ts = r.get("timestamp") or []
    q = ((r.get("indicators") or {}).get("quote") or [{}])[0]
    kap = q.get("close") or [None] * len(ts)
    return [(dt.datetime.fromtimestamp(t, dt.timezone.utc), c) for t, c in zip(ts, kap)]


def yerel(t: dt.datetime, r: dict) -> dt.datetime:
    off = (r.get("meta") or {}).get("gmtoffset") or 0
    return t + dt.timedelta(seconds=off)


# ─────────────────────────── (A) üretim çağrısının tekrarı
print("\n(A) ÜRETİM ÇAĞRISI — yf.download(51 sembol, period=1y, group_by=ticker, threads=True)")
kodlar = [v.kod for v in P.VARLIKLAR]
b = yf.download(kodlar, period="1y", interval="1d", progress=False,
                auto_adjust=False, group_by="ticker", threads=True)
son = {}
for k in kodlar:
    try:
        s = b[k]["Close"].dropna()
        son[k] = [str(x.date()) for x in s.index[-3:]]
    except Exception as e:  # noqa: BLE001
        son[k] = [f"yok ({type(e).__name__})"]
enbuyuk = max((v[-1] for v in son.values() if v and v[-1][:2] == "20"), default="")
for k in kodlar:
    isaret = "  ←" if son[k] and son[k][-1] < enbuyuk else ""
    print(f"  {k:12s} {' '.join(son[k])}{isaret}")

# Aynı semboller TEK TEK (threads=False, tek sembol) — toplu çağrı farkı var mı
print("\n(A2) AYNI SEMBOLLER TEK TEK — yf.download(sembol, period=1y) · Ticker.history(period=5d)")
for k in ETKILENEN + KONTROL:
    try:
        s1 = yf.download(k, period="1y", interval="1d", progress=False, auto_adjust=False)
        c1 = s1["Close"].dropna()
        if isinstance(c1, pd.DataFrame):
            c1 = c1.iloc[:, 0]
        d1 = [str(x.date()) for x in c1.index[-3:]]
    except Exception as e:  # noqa: BLE001
        d1 = [f"hata {type(e).__name__}"]
    try:
        h = yf.Ticker(k).history(period="5d", interval="1d", auto_adjust=False)
        d2 = [str(x.date()) for x in h["Close"].dropna().index[-3:]]
    except Exception as e:  # noqa: BLE001
        d2 = [f"hata {type(e).__name__}"]
    print(f"  {k:12s} download: {' '.join(d1):34s} history(5d): {' '.join(d2)}")
    time.sleep(0.3)

# ─────────────────────────── (B) ham chart ucu
print("\n(B) HAM CHART UCU — range=5d interval=1d (yfinance düzeltmesi YOK)")
META = {}
for k in ETKILENEN + KONTROL:
    r = ham(k, range="5d", interval="1d", includePrePost="false", events="div,splits")
    if not r:
        continue
    m = r.get("meta") or {}
    META[k] = (r, m)
    rs = satirlar(r)
    rmt = m.get("regularMarketTime")
    rmt_s = dt.datetime.fromtimestamp(rmt, dt.timezone.utc).strftime("%m-%d %H:%M") if rmt else "—"
    ctp = ((m.get("currentTradingPeriod") or {}).get("regular") or {})
    ctp_s = ""
    if ctp.get("start"):
        ctp_s = (dt.datetime.fromtimestamp(ctp["start"], dt.timezone.utc).strftime("%m-%d %H:%M") + "→" +
                 dt.datetime.fromtimestamp(ctp["end"], dt.timezone.utc).strftime("%H:%M"))
    print(f"  {k:12s} tz={m.get('exchangeTimezoneName')} tip={m.get('instrumentType')} "
          f"rmTime={rmt_s}Z rmPrice={m.get('regularMarketPrice')} "
          f"prevClose={m.get('previousClose')} chartPrev={m.get('chartPreviousClose')} seans={ctp_s}Z")
    for t, c in rs[-4:]:
        print(f"       {t:%Y-%m-%d %H:%M}Z  yerel {yerel(t, r):%Y-%m-%d %H:%M}  kapanış {c}")
    time.sleep(0.3)

print("\n(B2) HAM CHART UCU — range=1y interval=1d, SON dört satır (üretimin aralığı)")
for k in ETKILENEN + KONTROL:
    r = ham(k, range="1y", interval="1d", includePrePost="false", events="div,splits")
    if not r:
        continue
    rs = satirlar(r)
    print(f"  {k:12s} " + " · ".join(f"{t:%m-%d %H:%M}Z={c if c is None else round(c, 4)}" for t, c in rs[-4:]))
    time.sleep(0.3)

# ─────────────────────────── (C) yedek yolların sadakati
print("\n(C1) META — piyasa şu an KAPALIYSA regularMarketPrice o günün günlük kapanışına eşit mi")
for k, (r, m) in META.items():
    rmt = m.get("regularMarketTime")
    fiyat = m.get("regularMarketPrice")
    if not rmt or fiyat is None:
        continue
    ctp = ((m.get("currentTradingPeriod") or {}).get("regular") or {})
    acik = bool(ctp.get("start") and ctp["start"] <= SIMDI.timestamp() < ctp["end"])
    gun = yerel(dt.datetime.fromtimestamp(rmt, dt.timezone.utc), r).date()
    gunluk = {yerel(t, r).date(): c for t, c in satirlar(r) if c is not None}
    g = gunluk.get(gun)
    fark = "—" if g is None else f"{(fiyat / g - 1) * 1e4:+.2f} bp"
    print(f"  {k:12s} açık={acik!s:5s} son işlem günü {gun} fiyat {fiyat} · günlük satır {g} · fark {fark}")

print("\n(C2) GÜN İÇİ SON BAR — günlük kapanışa uzaklık (bp), son ~60 gün")
print("     sembol       aralık  n   tam(≤0,1bp)  medyan  p90     azami")


def sadakat(k: str, aralik: str, gun_say: str) -> None:
    g = ham(k, range="3mo", interval="1d", includePrePost="false")
    i = ham(k, range=gun_say, interval=aralik, includePrePost="false")
    if not g or not i:
        print(f"  {k:12s} {aralik:5s}  ölçülemedi")
        return
    gunluk = {yerel(t, g).date(): c for t, c in satirlar(g) if c is not None}
    sonbar: dict[dt.date, float] = {}
    for t, c in satirlar(i):
        if c is not None:
            sonbar[yerel(t, i).date()] = c          # sıralı: son yazılan son bar
    farklar = [abs(sonbar[d] / gunluk[d] - 1) * 1e4 for d in sonbar if d in gunluk and gunluk[d]]
    if not farklar:
        print(f"  {k:12s} {aralik:5s}  ortak gün yok")
        return
    farklar.sort()
    tam = sum(f <= 0.1 for f in farklar) / len(farklar)
    p90 = farklar[int(0.9 * (len(farklar) - 1))]
    print(f"  {k:12s} {aralik:5s} {len(farklar):3d}  %{100 * tam:5.1f}       "
          f"{st.median(farklar):6.2f}  {p90:6.2f}  {max(farklar):7.2f}")


for k in ETKILENEN:
    for aralik, gun_say in (("5m", "60d"), ("1h", "60d")):
        sadakat(k, aralik, gun_say)
        time.sleep(0.3)

print("\nbitti", dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "UTC")
