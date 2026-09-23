#!/usr/bin/env python3
"""BIST TLREF tarihsel dosyası ile EVDS birebir mi — ölçüm, hüküm değil.

İkinci keşif (kesif_tlref_bist2.py, 23.09.2026 06:56 UTC) şunu ölçtü:
  · /datum/tlreforani.csv (günlük, Last-Modified 22.09 13:00 GMT) 22/09/2026
    için TLREF 36,5477 veriyor; /datum/bisttlrefendeksi.csv aynı gün endeks
    6789,09772. EVDS'in son gözlemi o saatte hâlâ 21.09.
  · Tarihsel zip'lerin içindeki CSV'ler UTF-16 (BOM ÿþ) — ikinci betik
    onları latin-1 okuyup ayrıştıramadı, yani birebirlik ÖLÇÜLEMEDİ.
Bir kaynak ancak mevcut kaynakla örtüşen günlerde birebir aynıysa yedek
olabilir. Bu betik tarihsel dosyaları doğru kodlamayla okur ve EVDS ile
örtüşen her günü kıyaslar (oran ve endeks ayrı). Ağa çıkar, depoya YAZMAZ.
"""
from __future__ import annotations

import io
import sys
import zipfile
import datetime as dt
from pathlib import Path

import requests

SIMDI = dt.datetime.now(dt.timezone.utc)
print(f"şimdi {SIMDI:%Y-%m-%d %H:%M} UTC")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})
KOK = "https://www.borsaistanbul.com"

kok = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(kok / "Aktarılacak Projeler" / "Fonlama"))
import veri as F  # noqa: E402


def evds(kod: str, bas: dt.date) -> dict[dt.date, float]:
    out: dict[dt.date, float] = {}
    g = bas
    while g <= SIMDI.date():
        son = min(g + dt.timedelta(days=360), SIMDI.date())
        j = F._cek(f"{F.BASE}/series={kod}&startDate={g:%d-%m-%Y}&endDate={son:%d-%m-%Y}&type=json")
        alan = kod.replace(".", "_")
        for s in j.get("items") or []:
            v = s.get(alan)
            if v not in (None, ""):
                out[dt.datetime.strptime(s["Tarih"], "%d-%m-%Y").date()] = float(v)
        g = son + dt.timedelta(days=1)
    return out


def csv_metni(ham: bytes) -> str:
    for kod in ("utf-16", "utf-8-sig", "cp1254", "latin-1"):
        try:
            m = ham.decode(kod)
            if m.count("\x00") == 0 and ("/" in m or "." in m):
                return m
        except UnicodeDecodeError:
            continue
    return ham.decode("latin-1", "ignore")


def tarih(s: str):
    s = s.strip().strip('"')
    for f in ("%d/%m/%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s[:10], f).date()
        except ValueError:
            continue
    return None


def sayi(s: str):
    s = s.strip().strip('"')
    if not s:
        return None
    # "1.234,56" ve "1234.56" iki yazımı da
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def tarihsel(yol: str) -> tuple[list[str], list[list[str]]]:
    r = S.get(KOK + yol, timeout=40)
    print(f"\nGET {yol} → {r.status_code} {len(r.content)} bayt · Last-Modified {r.headers.get('last-modified')}")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    ad = z.namelist()[0]
    metin = csv_metni(z.read(ad))
    satirlar = [s for s in metin.splitlines() if s.strip()]
    ayrac = ";" if satirlar[0].count(";") >= satirlar[0].count(",") else ","
    if satirlar[0].count("\t") > satirlar[0].count(ayrac):
        ayrac = "\t"
    tablo = [s.split(ayrac) for s in satirlar]
    print(f"  {ad}: {len(tablo)} satır · ayraç {ayrac!r}")
    for s in tablo[:3] + tablo[-3:]:
        print("   ", [x.strip()[:24] for x in s[:9]])
    return tablo[0], tablo[1:]


def kiyasla(ad: str, tablo, evds_seri: dict, tarih_i: int, deger_i: int, tol: float) -> None:
    ortak = esit = 0
    farklar = []
    son_bist = None
    for s in tablo:
        if len(s) <= max(tarih_i, deger_i):
            continue
        g, v = tarih(s[tarih_i]), sayi(s[deger_i])
        if g is None or v is None:
            continue
        son_bist = g if son_bist is None or g > son_bist else son_bist
        if g in evds_seri:
            ortak += 1
            f = abs(v - evds_seri[g])
            farklar.append((f, g, v, evds_seri[g]))
            esit += f < tol
    farklar.sort(reverse=True)
    print(f"  {ad}: BIST son gün {son_bist} · EVDS son gün {max(evds_seri) if evds_seri else '—'} · "
          f"örtüşen {ortak} gün · birebir (<{tol}) {esit} · en büyük farklar: "
          + "; ".join(f"{g} bist {v} evds {e} (|Δ| {f:.6f})" for f, g, v, e in farklar[:5]))
    eksik_evds = sorted(g for g in evds_seri if g >= min((tarih(s[tarih_i]) for s in tablo
                                                           if len(s) > tarih_i and tarih(s[tarih_i])),
                                                          default=SIMDI.date()))
    bist_gunler = {tarih(s[tarih_i]) for s in tablo if len(s) > tarih_i}
    yalniz_evds = [g for g in eksik_evds if g not in bist_gunler]
    print(f"  {ad}: EVDS'te olup BIST dosyasında olmayan gün {len(yalniz_evds)} "
          f"{[str(g) for g in yalniz_evds[:6]]}")


bas = dt.date(2019, 1, 1)
e_oran = evds("TP.BISTTLREF.ORAN", bas)
e_end = evds("TP.BISTTLREF.KAPANIS", dt.date(2019, 6, 14))
print(f"EVDS oran {len(e_oran)} gözlem ({min(e_oran)} → {max(e_oran)}) · "
      f"endeks {len(e_end)} gözlem ({min(e_end)} → {max(e_end)})")

bas_o, t_o = tarihsel("/datum/TLREFORANI_D.zip")
print("  başlık:", [x.strip() for x in bas_o])
bas_e, t_e = tarihsel("/datum/BISTTLREFENDEKSI_D.zip")
print("  başlık:", [x.strip() for x in bas_e])


def sutun(baslik, *adaylar):
    for i, b in enumerate(baslik):
        bb = b.lower()
        if any(a in bb for a in adaylar):
            return i
    return None


ti = sutun(bas_o, "tarih", "date")
di = sutun(bas_o, "değer", "deger", "value", "oran", "rate", "tlref")
print(f"  oran dosyası sütunları: tarih {ti}, değer {di}")
if ti is not None and di is not None:
    kiyasla("oran", t_o, e_oran, ti, di, 5e-5)
else:
    # sütun adı tutmazsa her sayısal sütunu dene
    for d in range(len(bas_o)):
        if d != (ti or 0):
            kiyasla(f"oran/sütun{d}", t_o, e_oran, ti or 0, d, 5e-5)

ti = sutun(bas_e, "tarih", "date")
di = sutun(bas_e, "kapan", "closing", "close")
print(f"  endeks dosyası sütunları: tarih {ti}, kapanış {di}")
if ti is not None and di is not None:
    kiyasla("endeks", t_e, e_end, ti, di, 5e-4)

print("\nbitti", dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "UTC")
