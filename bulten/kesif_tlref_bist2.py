#!/usr/bin/env python3
"""BIST TLREF veri dosyaları: adres, biçim, son gün ve EVDS ile birebirlik — ölçüm.

İlk keşif (kesif_tlref_bist.py, 23.09.2026 06:52 UTC) iki şey ölçtü:
  · EVDS'te TLREF'in son gözlemi 21.09 — 22.09 bülten saatinden SONRA da yok.
  · BIST'in TLREF sayfası "Günlük — 16:00'dan sonra (yarım günde 12:45)"
    satırında bir indirme düğmesi taşıyor; dosyanın yolu bir `href`te değil
    düğmenin `dosya-yolu` niteliğinde. İlk betik yalnız bağları okuduğu için
    dosyaya ulaşamadı.
Bu betik o nitelikleri sayfadan ÇÖZER (adres tahmin edilmez), her dosyayı
indirir, biçimini ve son satırlarını basar, ve EVDS ile örtüşen günlerde
oranın birebir aynı olup olmadığını sayar. Ağa çıkar, depoya YAZMAZ.
"""
from __future__ import annotations

import io
import re
import sys
import zipfile
import datetime as dt
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import requests

SIMDI = dt.datetime.now(dt.timezone.utc)
print(f"şimdi {SIMDI:%Y-%m-%d %H:%M} UTC")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9"})
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "openpyxl", "xlrd"],
               check=False, capture_output=True, timeout=180)
import pandas as pd  # noqa: E402

# EVDS
EVDS: dict[dt.date, float] = {}
try:
    kok = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(kok / "Aktarılacak Projeler" / "Fonlama"))
    import veri as F  # noqa: E402
    bas = SIMDI.date() - dt.timedelta(days=120)
    j = F._cek(f"{F.BASE}/series=TP.BISTTLREF.ORAN&startDate={bas:%d-%m-%Y}"
               f"&endDate={SIMDI.date():%d-%m-%Y}&type=json")
    for s in j.get("items") or []:
        v = s.get("TP_BISTTLREF_ORAN")
        if v not in (None, ""):
            EVDS[dt.datetime.strptime(s["Tarih"], "%d-%m-%Y").date()] = float(v)
    print(f"EVDS: {len(EVDS)} gözlem, son {max(EVDS) if EVDS else '—'}")
except Exception as e:  # noqa: BLE001
    print(f"! EVDS ölçülemedi: {type(e).__name__}: {str(e)[:160]}")

SAYFA = "https://www.borsaistanbul.com/endeksler/tlref"
r = S.get(SAYFA, timeout=25)
print(f"\nGET {SAYFA} → {r.status_code} {len(r.content)} bayt")
html = r.text
dugmeler = []
for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I):
    satir = m.group(1)
    for d in re.finditer(r'dosya-yolu=["\']([^"\']+)["\']', satir):
        etiket = re.sub(r"<[^>]+>|&nbsp;|\s+", " ", satir)
        dugmeler.append((re.sub(r"\s+", " ", etiket).strip()[:140], d.group(1)))
# satır dışında kalan düğmeler de sayılsın
for d in re.finditer(r'dosya-yolu=["\']([^"\']+)["\']', html):
    if d.group(1) not in {y for _, y in dugmeler}:
        dugmeler.append(("(satır dışı)", d.group(1)))
print(f"{len(dugmeler)} indirme düğmesi:")
for et, yol in dugmeler:
    print(f"  {et!r}\n      dosya-yolu = {yol}")


def tarih_coz(x):
    if isinstance(x, (dt.date, dt.datetime, pd.Timestamp)):
        return pd.Timestamp(x).date()
    s = str(x).strip()
    for f in ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y%m%d"):
        try:
            return dt.datetime.strptime(s[:10], f).date()
        except ValueError:
            continue
    return None


def tablo_incele(ad: str, veri: bytes) -> None:
    kucuk = ad.lower()
    df = None
    try:
        if kucuk.endswith((".xlsx", ".xls")):
            df = pd.read_excel(io.BytesIO(veri), header=None)
        elif kucuk.endswith((".csv", ".txt")):
            df = pd.read_csv(io.BytesIO(veri), sep=None, engine="python", header=None,
                             encoding="latin-1")
    except Exception as e:  # noqa: BLE001
        print(f"      okunamadı: {type(e).__name__}: {str(e)[:120]}")
        return
    if df is None:
        print(f"      biçim tanınmadı: {ad}")
        return
    print(f"      {ad}: {df.shape[0]} satır × {df.shape[1]} sütun")
    for _, row in df.head(6).iterrows():
        print("        başı:", [str(v)[:22] for v in row.tolist()[:8]])
    for _, row in df.tail(4).iterrows():
        print("        sonu:", [str(v)[:22] for v in row.tolist()[:8]])
    # tarih sütunu + oran sütunu ara; EVDS ile birebir kıyas
    en_iyi = None
    for ti in range(df.shape[1]):
        gunler = df.iloc[:, ti].map(tarih_coz)
        if gunler.notna().sum() < 5:
            continue
        for oi in range(df.shape[1]):
            if oi == ti:
                continue
            say = esit = 0
            fark = []
            for g, v in zip(gunler, df.iloc[:, oi]):
                try:
                    v = float(str(v).replace(",", "."))
                except ValueError:
                    continue
                if g in EVDS:
                    say += 1
                    fark.append(abs(v - EVDS[g]))
                    esit += abs(v - EVDS[g]) < 5e-5
            if say >= 5 and (en_iyi is None or esit > en_iyi[0]):
                son = max((g for g in gunler if g), default=None)
                en_iyi = (esit, say, ti, oi, max(fark), son)
    if en_iyi:
        esit, say, ti, oi, azami, son = en_iyi
        print(f"      EVDS kıyası: tarih sütunu {ti}, oran sütunu {oi} · örtüşen {say} gün, "
              f"birebir (<0,00005) {esit} · azami fark {azami:.6f} · dosyanın son günü {son}")
    else:
        print("      EVDS ile örtüşen tarih/oran sütunu bulunamadı")


for et, yol in dugmeler[:12]:
    url = urljoin(SAYFA, yol)
    try:
        d = S.get(url, timeout=40)
    except Exception as e:  # noqa: BLE001
        print(f"\n  GET {url} → {type(e).__name__}")
        continue
    ct = d.headers.get("content-type", "")
    print(f"\n  GET {url} → {d.status_code} {ct[:50]} {len(d.content)} bayt "
          f"· Last-Modified {d.headers.get('last-modified')}")
    if d.status_code != 200:
        continue
    if url.lower().endswith(".zip") or "zip" in ct:
        try:
            z = zipfile.ZipFile(io.BytesIO(d.content))
            adlar = z.namelist()
            print(f"      zip: {len(adlar)} dosya · ilk {adlar[:3]} · son {adlar[-3:]}")
            for ad in sorted(adlar)[-2:]:
                tablo_incele(ad, z.read(ad))
        except Exception as e:  # noqa: BLE001
            print(f"      zip açılamadı: {type(e).__name__}")
    else:
        tablo_incele(url.split("?")[0], d.content)

print("\nbitti", dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "UTC")
