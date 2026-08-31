# -*- coding: utf-8 -*-
"""KEŞİF — HMB'nin duyuru akışında EN SON İç Borçlanma Stratejisi hangisi?

Neden ayrı bir betik: 31.08.2026'da yeni stratejiyi indirmek için hat iki kez
tam kipte koşturuldu, ikisi de düştü ve 1.400 satırlık koşu kaydından sebebi
okumak pahalı. Asıl soru ise çok daha ucuz cevaplanabilir ve ÖNCE sorulmalı:
HMB yeni stratejiyi yayımladı mı? Yayımlamadıysa hattaki hiçbir kusur bu işi
bugün bitirmez.

Hattın kendi API'sini kullanır (WordPress REST), hiçbir şey yazmaz, PDF
indirmez — yalnız duyuru başlıklarını ve tarihlerini basar.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request

API = "https://www.hmb.gov.tr/portal/v2/posts"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
KALIP = re.compile(r"i[çc]\s*bor[çc]lanma\s*stratejis", re.I)


def sayfa(n: int, adet: int = 20) -> list[dict]:
    url = f"{API}?page={n}&per_page={adet}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        veri = json.loads(r.read().decode("utf-8", "replace"))
    if isinstance(veri, dict):
        veri = veri.get("data") or veri.get("items") or veri.get("posts") or []
    return veri if isinstance(veri, list) else []


def alan(k: dict, *adlar: str) -> str:
    for a in adlar:
        v = k.get(a)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            for x in ("rendered", "tr", "title"):
                if isinstance(v.get(x), str) and v[x].strip():
                    return v[x].strip()
    return ""


def main() -> int:
    kac = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    print(f"── HMB duyuru akışı · ilk {kac} sayfa\n")
    bulunan, toplam = [], 0
    for n in range(1, kac + 1):
        try:
            kayitlar = sayfa(n)
        except Exception as ex:
            print(f"  sayfa {n} düştü: {type(ex).__name__}: {str(ex)[:90]}")
            break
        if not kayitlar:
            print(f"  sayfa {n}: boş — akış bitti")
            break
        toplam += len(kayitlar)
        for k in kayitlar:
            baslik = alan(k, "title", "baslik", "name")
            tarih = alan(k, "date", "publishDate", "created_at", "tarih")
            if KALIP.search(baslik):
                bulunan.append((tarih[:10], baslik))
    print(f"  taranan duyuru: {toplam}\n")
    print("── İÇ BORÇLANMA STRATEJİSİ duyuruları (en yeni önce)")
    if not bulunan:
        print("  HİÇ BULUNAMADI — kalıp tutmadı ya da akış farklı geliyor.")
    for t, b in bulunan[:12]:
        print(f"  {t}  {b[:110]}")
    print("\n── İlk 8 duyuru (kalıptan bağımsız, akışın gerçekten ne döndüğü)")
    try:
        for k in sayfa(1)[:8]:
            print(f"  {alan(k,'date','publishDate','tarih')[:10]}  "
                  f"{alan(k,'title','baslik','name')[:100]}")
    except Exception as ex:
        print(f"  düştü: {ex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
