# -*- coding: utf-8 -*-
"""Altın fiyat kaynağı yoklaması — LBMA fiksingi ve uluslararası gün içi fiyat.

NİYE VAR (05.10.2026). Hattın altın fiyatı BİST Kıymetli Madenler ağırlıklı
ortalaması (AGORT03). İnceleme ölçtü: analitik bilançonun dış varlıkları altını
aynı gün SABAH uluslararası fiyatla yeniden değerliyor (Yahoo GC=F saatlik ile
R² 09–11 UTC'de zirve); uluslararası fiyat modele girince AGORT03'ün katsayısı
sıfıra iniyor, AGORT03'ün yerel primi ise %5–9'a kadar oynuyor ve günlük akıma
milyar dolarlık sahte hareket yazıyor. Aday referans LBMA sabah (AM) fiksingi
(Londra 10:30). Kurucu sıra: önce KAYNAK yoklanır (her aday birkaç saniye),
sonra serisi ölçülür, sonra hat kurulur. Bu betik yalnız yoklar ve döker.

İlk koşu (#327): LBMA genel JSON ucu 403 (dört istek), Yahoo ham chart ucu 429.
429 bir ölçüm değildir; yfinance önce çerez alır, üretim de onu kullanır.
Bu koşunun adayları — katalog TAHMİN EDİLMEZ, İSTENİR:
  1. EVDS: bütün veri gruplarının listesi (datagroups mode=0) içinde adında
     altın / gold / kıymetli maden geçen gruplar ve serileri; adında Londra /
     London / LBMA / ons geçen her serinin 2022-12 → bugün değerleri.
  2. Bundesbank SDMX: BBEX3 akışında D.XAU.* (joker) — hangi altın serileri
     var, adları, son değerleri; LBMA sabah fiksingi bulunursa tam seri.
  3. LBMA genel JSON — tarayıcının gönderdiği Referer/Origin başlıklarıyla.
  4. yfinance saatlik: GC=F (vadeli, ön ay), XAUUSD=X, MGC=F — kapsam ve son
     iki haftanın 07–16 UTC barları (yerel ölçüm arşivi 21.09'da bitiyor).

Koşum (yalnız iş akışından):
    veri.yml → kesif: Aktarılacak Projeler/TCMBNetRezerv/kesif_altin_fiyat.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import time
import urllib.request

PROJE = pathlib.Path(__file__).resolve().parent
EVDS = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
BBK = "https://api.statistiken.bundesbank.de/rest"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
BAS = "2022-12-01"


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
                govde = ex.read()[:300]
            except Exception:                                # noqa: BLE001
                pass
        return f"{type(ex).__name__}: {str(ex)[:120]}", govde, time.time() - t0


def anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    y = PROJE / ".evds_key"
    return y.read_text(encoding="utf-8").strip() if y.exists() else ""


# --------------------------------------------------------------------------- 1
def evds() -> None:
    print("\n▶ EVDS — veri grubu kataloğu", flush=True)
    k = anahtar()
    if not k:
        print("  anahtar yok, atlandı", flush=True)
        return
    st, g, sure = al(f"{EVDS}/datagroups/mode=0&type=json", 90, {"key": k})
    print(f"  datagroups mode=0 → {st} ({len(g)} bayt, {sure:.1f} sn)", flush=True)
    if st != 200:
        return
    gruplar = json.loads(g.decode("utf-8"))
    print(f"  grup sayısı {len(gruplar)}", flush=True)
    anah = ("altın", "altin", "gold", "kıymetli", "kiymetli", "maden", "precious")
    aday = [x for x in gruplar
            if any(a in (str(x.get("DATAGROUP_NAME", "")) + " "
                         + str(x.get("DATAGROUP_NAME_ENG", ""))).lower() for a in anah)]
    for x in aday:
        print(f"  · {x.get('DATAGROUP_CODE')} | {x.get('DATAGROUP_NAME')} | "
              f"{x.get('DATAGROUP_NAME_ENG')} | {x.get('FREQUENCY_STR')}", flush=True)
    seri_aday = []
    for x in aday:
        kod = x.get("DATAGROUP_CODE")
        st, g, _ = al(f"{EVDS}/serieList/type=json&code={kod}", 60, {"key": k})
        if st != 200:
            print(f"    serieList {kod} → {st}", flush=True)
            continue
        for s in json.loads(g.decode("utf-8")):
            ad = f"{s.get('SERIE_NAME')} | {s.get('SERIE_NAME_ENG')}"
            print(f"    {s.get('SERIE_CODE'):28s} {s.get('FREQUENCY_STR', ''):8s} "
                  f"{s.get('START_DATE', '')} | {ad}", flush=True)
            if any(a in ad.lower() for a in ("londra", "london", "lbma", " ons", "ounce", "fixing")):
                seri_aday.append(s.get("SERIE_CODE"))
    bugun = dt.date.today().strftime("%d-%m-%Y")
    for kod in seri_aday[:12]:
        st, g, _ = al(f"{EVDS}/series={kod}&startDate=01-12-2022&endDate={bugun}&type=json",
                      90, {"key": k})
        if st != 200:
            print(f"  ✗ {kod} → {st}", flush=True)
            continue
        kolon = kod.replace(".", "_")
        items = [i for i in json.loads(g.decode("utf-8")).get("items", [])
                 if i.get(kolon) not in (None, "", "null")]
        print(f"\nEVDS_CSV_BAS {kod} n={len(items)}", flush=True)
        for i in items:
            print(f"{i.get('Tarih')};{i.get(kolon)}")
        print(f"EVDS_CSV_SON {kod}", flush=True)


# --------------------------------------------------------------------------- 2
def bundesbank() -> None:
    print("\n▶ Bundesbank SDMX — BBEX3 D.XAU.*", flush=True)
    denemeler = [
        f"{BBK}/data/BBEX3/D.XAU....?format=sdmx_csv&startPeriod=2026-09-20",
        f"{BBK}/data/BBEX3/D.XAU....?startPeriod=2026-09-20",
        f"{BBK}/download/BBEX3/D.XAU.USD.EA.AC.C04?format=csv&lang=en",
        f"{BBK}/metadata/codelist/BBK/CL_BBK_ERX_RATE_TYPE",
    ]
    for u in denemeler:
        st, g, sure = al(u, 40, {"Accept": "text/csv, application/xml, */*"})
        print(f"  {u[len(BBK):][:90]:90s} → {st} ({len(g)} bayt, {sure:.1f} sn)", flush=True)
        if g:
            metin = g.decode("utf-8", "replace")
            print("    " + "\n    ".join(metin.splitlines()[:30]), flush=True)
    # Tam seri: sabah fiksingi adayı bulunursa yerel ölçüm için dökülür.
    for anahtar_ in ("D.XAU.USD.EA.AC.C04", "D.XAU.USD.EA.AC.C05"):
        u = f"{BBK}/data/BBEX3/{anahtar_}?format=sdmx_csv&startPeriod={BAS}"
        st, g, _ = al(u, 60, {"Accept": "text/csv"})
        print(f"  tam seri {anahtar_} → {st} ({len(g)} bayt)", flush=True)
        if st == 200 and g:
            print(f"BBK_CSV_BAS {anahtar_}")
            print(g.decode("utf-8", "replace"))
            print(f"BBK_CSV_SON {anahtar_}", flush=True)


# --------------------------------------------------------------------------- 3
def lbma() -> None:
    print("\n▶ LBMA — tarayıcı başlıklarıyla", flush=True)
    b = {"Referer": "https://www.lbma.org.uk/prices-and-data/precious-metal-prices",
         "Origin": "https://www.lbma.org.uk", "Accept": "application/json, text/plain, */*",
         "Accept-Language": "en-GB,en;q=0.9"}
    for ad in ("gold_am", "gold_pm"):
        st, g, sure = al(f"https://prices.lbma.org.uk/json/{ad}.json", 30, b)
        print(f"  {ad} → {st} ({len(g)} bayt, {sure:.1f} sn)", flush=True)
        if st != 200:
            if g:
                print(f"    gövde: {g[:200]!r}", flush=True)
            continue
        d = json.loads(g.decode("utf-8"))
        print(f"    kayıt {len(d)}; son {d[-1] if d else None}", flush=True)
        print(f"LBMA_CSV_BAS {ad}")
        for k in d:
            if isinstance(k, dict) and str(k.get("d", "")) >= BAS and k.get("v"):
                print(f"{k['d']};{k['v'][0]}")
        print(f"LBMA_CSV_SON {ad}", flush=True)


# --------------------------------------------------------------------------- 4
def yahoo() -> None:
    print("\n▶ yfinance saatlik", flush=True)
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError as ex:
        print(f"  yfinance yok: {ex}", flush=True)
        return
    for s in ("GC=F", "XAUUSD=X", "MGC=F"):
        try:
            h = yf.download(s, period="730d", interval="60m", progress=False,
                            auto_adjust=False, threads=False)
        except Exception as ex:                              # noqa: BLE001
            print(f"  {s}: {type(ex).__name__}: {ex}", flush=True)
            continue
        if h is None or len(h) == 0:
            print(f"  {s}: boş", flush=True)
            continue
        c = h["Close"]
        if hasattr(c, "columns"):
            c = c.iloc[:, 0]
        c = c.dropna()
        idx = pd.DatetimeIndex(c.index)
        c.index = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
        print(f"  {s}: {len(c)} bar · {c.index[0]} → {c.index[-1]}", flush=True)
        son = c[c.index >= pd.Timestamp("2026-09-14", tz="UTC")]
        son = son[(son.index.hour >= 6) & (son.index.hour <= 17)]
        print(f"YF_CSV_BAS {s}")
        for t, v in son.items():
            print(f"{t:%Y-%m-%d %H:%M};{v:.2f}")
        print(f"YF_CSV_SON {s}", flush=True)


def main() -> int:
    print("=" * 74)
    print("  ALTIN FİYAT KAYNAĞI YOKLAMASI (ikinci koşu)")
    print("=" * 74, flush=True)
    for f in (evds, bundesbank, lbma, yahoo):
        try:
            f()
        except Exception as ex:                              # noqa: BLE001
            print(f"  ! {f.__name__} düştü: {type(ex).__name__}: {ex}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
