#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND — ALTINCI YOKLAMA: CNBC günlük barı günün HANGİ SAATİNİ taşıyor?

Ölçülen çelişki (01.10.2026): CNBC'nin 1 Ekim barında Bund 10y −6,0 bp (3,5191),
oysa Bundesbank'ın günlük par getirisi +2 bp (3,60 → 3,62) ve ajans haberleri
Bund'un o gün yükseldiğini yazıyor; CNBC'den kurulan fark 140,9 bp, haberlerde
127–133 bp. Hipotez: hafta içi barı Avrupa kapanışı değil, New York'taki son
kotasyon. Sınama: gün içi barlar çekilir, her günün Paris 17:30 kotasyonu ile
günlük barın kapanışı karşılaştırılır; günlük kapanışa hangi saat eşitse bar o
saattir.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0 Safari/537.36"), "Accept": "*/*"}
NY = ZoneInfo("America/New_York")
PARIS = ZoneInfo("Europe/Paris")


def al(url: str):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, None
    except (URLError, TimeoutError, OSError, ValueError) as e:
        return None, repr(e)


def barlar(js) -> list[tuple[datetime, float]]:
    out = []
    for p in (js or {}).get("barData", {}).get("priceBars", []) or []:
        try:
            t = datetime.fromtimestamp(int(p["tradeTimeinMills"]) / 1000, tz=timezone.utc)
            out.append((t, float(p["close"])))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def main() -> int:
    for sem in ("FR10Y-FR", "DE10Y-DE", "FR2Y-FR", "DE2Y-DE", "IT10Y-IT", "EUR="):
        print(f"=== {sem}")
        d, js = al(f"https://ts-api.cnbc.com/harmony/app/bars/{urllib.request.quote(sem)}/1D/"
                   "20260921000000/20261003000000/adjusted/EST5EDT.json")
        gunluk = barlar(js) if d == 200 else []
        print("  günlük:", [(t.astimezone(NY).strftime("%a %d.%m %H:%M NY"), v) for t, v in gunluk])
        ici = []
        for uc in ("5D", "1D"):
            d2, js2 = al(f"https://ts-api.cnbc.com/harmony/app/charts/{uc}.json?symbol={urllib.request.quote(sem)}")
            b = barlar(js2) if d2 == 200 else []
            print(f"  gün içi {uc}: durum={d2} bar={len(b)} ilk={b[0][0].isoformat() if b else None} "
                  f"son={b[-1][0].isoformat() if b else None}")
            if len(b) > len(ici):
                ici = b
        if not ici:
            continue
        adim = sorted({int((b2[0] - b1[0]).total_seconds() // 60) for b1, b2 in zip(ici, ici[1:])})[:4]
        print(f"  gün içi adım (dk): {adim}")
        gunler = sorted({t.astimezone(PARIS).date() for t, _ in ici})
        for g in gunler:
            gun_ici = [(t, v) for t, v in ici if t.astimezone(PARIS).date() == g]
            p1730 = [(t, v) for t, v in gun_ici if t.astimezone(PARIS).time() <= datetime.strptime("17:30", "%H:%M").time()]
            ny17 = [(t, v) for t, v in ici if t.astimezone(NY).date() == g and t.astimezone(NY).hour < 17]
            son = gun_ici[-1] if gun_ici else None
            print(f"   {g}: Paris 17:30 → {p1730[-1][1] if p1730 else None} "
                  f"({p1730[-1][0].astimezone(PARIS).strftime('%H:%M') if p1730 else '-'}) · "
                  f"NY 17:00 öncesi son → {ny17[-1][1] if ny17 else None} "
                  f"({ny17[-1][0].astimezone(NY).strftime('%H:%M NY') if ny17 else '-'}) · "
                  f"Paris günü son → {son[1] if son else None} ({son[0].astimezone(PARIS).strftime('%H:%M') if son else '-'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
