#!/usr/bin/env python3
"""BIST TLREF GÜNLÜK dosyalarının biçimi ve yayım saati — ölçüm, hüküm değil.

İnceleme bulgusu (23.09.2026): uzantı yalnız TARİHSEL zip'leri okuyor ve o
dosyalar ~16:30 UTC'de güncelleniyor; Fonlama'nın o günkü son koşusu çoğu gün
daha erken bitiyor (14.09 15:32 · 17.09 14:21 · 18.09 13:25 · 21.09 15:35), yani
uzantı o günlerde "gerek yok" deyip hiçbir şey eklemiyor. Günlük dosyalar
(/datum/tlreforani.csv · /datum/bisttlrefendeksi.csv) 13:00 GMT'de yayımlanıyor
ama ayrıştırıcı onların BİÇİMİNİ bilmiyor. Bu betik iki günlük ve iki tarihsel
dosyanın başlıklarını (Last-Modified), ilk baytlarını ve çözülmüş satırlarını
olduğu gibi basar. Ağa çıkar, depoya YAZMAZ.
"""
from __future__ import annotations

import io
import zipfile
import datetime as dt

import requests

print(f"şimdi {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
KOK = "https://www.borsaistanbul.com"


def coz(ham: bytes) -> str:
    if ham[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return ham.decode("utf-16")
    for k in ("utf-8-sig", "cp1254", "latin-1"):
        try:
            return ham.decode(k)
        except UnicodeDecodeError:
            pass
    return ham.decode("latin-1", "ignore")


for yol in ("/datum/tlreforani.csv", "/datum/bisttlrefendeksi.csv",
            "/datum/TLREFORANI_D.zip", "/datum/BISTTLREFENDEKSI_D.zip"):
    print(f"\n=== {yol}")
    try:
        r = requests.get(KOK + yol, timeout=30, headers={"User-Agent": UA})
    except Exception as ex:
        print("  indirilemedi:", type(ex).__name__, ex)
        continue
    print("  durum", r.status_code, "· tür", r.headers.get("content-type"),
          "· Last-Modified", r.headers.get("last-modified"), "· bayt", len(r.content))
    ham = r.content
    if ham[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(ham))
        print("  zip içi:", z.namelist())
        ham = z.read(z.namelist()[0])
    print("  ilk 16 bayt:", ham[:16])
    satir = [s for s in coz(ham).splitlines() if s.strip()]
    print(f"  {len(satir)} satır; ilk 4:")
    for s in satir[:4]:
        print("   ", repr(s))
    print("  son 4:")
    for s in satir[-4:]:
        print("   ", repr(s))
print("\nbitti", dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "UTC")
