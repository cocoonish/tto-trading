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

Adaylar:
  1. LBMA genel JSON uçları (gold_am / gold_pm) — tam tarihçe tek istekte.
  2. Yahoo saatlik XAUUSD=X ve GC=F (chart ucu, 730 gün) — 10 UTC barı.
Çıktı: her adayın erişim durumu, kapsam, son değer; LBMA AM'nin 2022-12 →
bugün USD serisi CSV_BAS/CSV_SON arasında (yerel ölçüm için).

Koşum (yalnız iş akışından):
    veri.yml → kesif: Aktarılacak Projeler/TCMBNetRezerv/kesif_altin_fiyat.py
"""
from __future__ import annotations

import json
import time
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")


def al(url: str, zaman: int = 20):
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json,*/*"})
        with urllib.request.urlopen(req, timeout=zaman) as r:
            govde = r.read()
            return r.status, govde, time.time() - t0
    except Exception as ex:                                  # noqa: BLE001
        return f"{type(ex).__name__}: {str(ex)[:120]}", b"", time.time() - t0


def lbma() -> dict:
    out = {}
    for ad in ("gold_am", "gold_pm"):
        for url in (f"https://prices.lbma.org.uk/json/{ad}.json",
                    f"https://prices.lbma.org.uk/json/{ad}.json?r=1"):
            st, g, sure = al(url)
            print(f"  {ad:8s} {url[:60]:60s} → {st} ({len(g)} bayt, {sure:.1f} sn)", flush=True)
            if st == 200 and g:
                try:
                    d = json.loads(g.decode("utf-8"))
                except ValueError as ex:
                    print(f"    JSON değil: {ex}; ilk 200 bayt: {g[:200]!r}", flush=True)
                    continue
                print(f"    kayıt {len(d)}; ilk {d[0] if d else None}; son {d[-1] if d else None}", flush=True)
                out[ad] = d
                break
    return out


def yahoo_saatlik(sembol: str) -> None:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{sembol}"
           "?interval=60m&range=730d")
    st, g, sure = al(url, 30)
    print(f"  {sembol:10s} saatlik → {st} ({len(g)} bayt, {sure:.1f} sn)", flush=True)
    if st != 200:
        return
    try:
        d = json.loads(g.decode("utf-8"))["chart"]["result"][0]
        ts = d.get("timestamp") or []
        print(f"    bar {len(ts)}; ilk {ts[0] if ts else None}; son {ts[-1] if ts else None}", flush=True)
    except Exception as ex:                                  # noqa: BLE001
        print(f"    ayrıştırılamadı: {ex}", flush=True)


def main() -> int:
    print("=" * 74)
    print("  ALTIN FİYAT KAYNAĞI YOKLAMASI")
    print("=" * 74, flush=True)
    print("\n▶ LBMA", flush=True)
    l = lbma()
    print("\n▶ Yahoo saatlik", flush=True)
    for s in ("XAUUSD=X", "GC=F"):
        yahoo_saatlik(s)
    am = l.get("gold_am")
    if am:
        # Biçim: [{"d": "YYYY-MM-DD", "v": [USD, GBP, EUR]}, ...] (yoklanınca doğrulanır)
        print("\nCSV_BAS")
        print("tarih;usd_am")
        for k in am:
            d = k.get("d") if isinstance(k, dict) else None
            v = k.get("v") if isinstance(k, dict) else None
            if d and d >= "2022-12-01" and isinstance(v, list) and v:
                print(f"{d};{v[0]}")
        print("CSV_SON", flush=True)
    pm = l.get("gold_pm")
    if pm:
        print("\nCSV_PM_BAS")
        print("tarih;usd_pm")
        for k in pm:
            d = k.get("d") if isinstance(k, dict) else None
            v = k.get("v") if isinstance(k, dict) else None
            if d and d >= "2022-12-01" and isinstance(v, list) and v:
                print(f"{d};{v[0]}")
        print("CSV_PM_SON", flush=True)
    print(f"\nÖZET: LBMA AM {'VAR' if am else 'YOK'} · PM {'VAR' if pm else 'YOK'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
