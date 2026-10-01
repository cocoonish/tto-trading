#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND — BEŞİNCİ YOKLAMA: günlük tarihçenin derinliği.

Dördüncü yoklama (keşif #30) ölçtü: CNBC grafik ucu açık ama `5Y` HAFTALIK
(523 bar, 2016'dan), `ALL` AYLIK (1990/1994'ten) bar veriyor; Banco de España
`ti_1_7.csv` açık (600 KB'ta kesildi, sütun açıklamaları görülmedi); Webstat
kayıtları anahtarsız boş, BdF sayfası 403, MarketWatch 401.
Bu koşu: (1) CNBC'nin tarih aralıklı GÜNLÜK bar ucunu ve `1Y` aralığını,
(2) BdE tablosunun sütun AÇIKLAMALARINI ve ilk/son veri satırlarını,
(3) Webstat seri sayfasındaki dışa aktarma bağlarını sorar.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from urllib.error import HTTPError, URLError

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0 Safari/537.36"), "Accept": "*/*"}


def al(url: str, sn: int = 20, sinir: int = 30_000_000) -> tuple[int | None, bytes]:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=sn) as r:
            return r.status, r.read(sinir)
    except HTTPError as e:
        try:
            return e.code, e.read(1500)
        except Exception:  # noqa: BLE001
            return e.code, b""
    except (URLError, TimeoutError, OSError) as e:
        return None, repr(e).encode()


def cnbc_ozet(ad: str, d, govde: bytes) -> None:
    if d != 200:
        print(f"--- {ad}: durum={d} {govde[:240]!r}")
        return
    try:
        js = json.loads(govde)
        ps = js.get("barData", {}).get("priceBars", [])
        tt = [p.get("tradeTime", "")[:8] for p in ps]
        aralik = sorted({(int(b) - int(a)) for a, b in zip(tt[:-1], tt[1:]) if a.isdigit() and b.isdigit()})[:5]
        print(f"--- {ad}: bar={len(ps)} ilk={tt[0] if tt else None} son={tt[-1] if tt else None} "
              f"adım(gg)={aralik} son5={[(p['tradeTime'][:8], p['close']) for p in ps[-5:]]}")
    except Exception as e:  # noqa: BLE001
        print(f"--- {ad}: JSON değil {e!r} {govde[:200]!r}")


def main() -> int:
    # 1) CNBC
    for aralik in ("1Y", "YTD", "3Y"):
        cnbc_ozet(f"cnbc FR10Y-FR {aralik}", *al(f"https://ts-api.cnbc.com/harmony/app/charts/{aralik}.json?symbol=FR10Y-FR"))
    for bas, son in (("20000101000000", "20261001000000"), ("20160101000000", "20261001000000"),
                     ("20240101000000", "20261001000000")):
        for sem in ("FR10Y-FR", "DE10Y-DE"):
            u = f"https://ts-api.cnbc.com/harmony/app/bars/{sem}/1D/{bas}/{son}/adjusted/EST5EDT.json"
            cnbc_ozet(f"cnbc bars {sem} {bas[:8]}→{son[:8]}", *al(u))
    # 2) BdE ti_1_7 — açıklama satırları ve uçlar
    d, g = al("https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/ti_1_7.csv")
    print(f"--- bde ti_1_7: durum={d} bayt={len(g)}")
    if d == 200:
        m = g.decode("latin-1")
        satirlar = m.splitlines()
        for s in satirlar[:7]:
            print("    ", s[:1500])
        veri = [s for s in satirlar if re.match(r'^"?\d{1,2} [A-Z]{3} \d{4}', s)]
        print(f"    veri satırı: {len(veri)}")
        for s in veri[:2] + veri[-4:]:
            print("    ", s[:400])
    # 2b) BdE tablo dizini — öbür faiz tabloları
    for kod in ("ti_1_1", "ti_1_2", "ti_1_3", "ti_1_4", "ti_1_5", "ti_1_6", "ti_1_9", "be1905", "be1904"):
        d, g = al(f"https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/{kod}.csv", sinir=6000)
        if d == 200:
            m = g.decode("latin-1").splitlines()
            print(f"--- bde {kod}: açıklama: {m[3][:700] if len(m) > 3 else m[:2]}")
        else:
            print(f"--- bde {kod}: durum={d}")
    # 3) Webstat seri sayfası
    d, g = al("https://webstat.banque-france.fr/fr/catalogue/FM/FM.D.FR.EUR.FR2.BB.FRMOYTEC10.HSTA",
              sinir=2_000_000)
    print(f"--- webstat seri sayfası: durum={d} bayt={len(g)}")
    if d == 200:
        m = g.decode("utf-8", "replace")
        for b in sorted(set(re.findall(r'(?:href|src)="([^"]+)"', m))):
            if any(x in b.lower() for x in ("export", "download", "csv", "api", "xls", "sdmx")):
                print("    bağ:", b[:200])
        for b in sorted(set(re.findall(r'https?://[^"\'\s<>]+', m))):
            if any(x in b.lower() for x in ("export", "download", "csv", "/api/")):
                print("    adres:", b[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
