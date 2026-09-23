#!/usr/bin/env python3
"""TLREF'in aynı gün yayımlandığı bir kaynak var mı — ölçüm, hüküm değil.

Neden: sabah bülteni TLREF'i fonlama hattından, o da EVDS'in TP.BISTTLREF.ORAN
serisinden okuyor. Depodaki koşu tarihçesi EVDS'in T gününün TLREF'ini T+1
günü öğlene doğru verdiğini gösteriyor (22.09 17:08 koşusunda hâlâ 21.09;
21.09'un değeri 22.09 13:57 koşusunda geldi). 04:20 UTC'deki bülten bu yüzden
bir önceki seansın TLREF'ini hiçbir gün taşıyamıyor. TLREF'in yöneticisi Borsa
İstanbul; kural setinin T günü 15:50'de ilan edip 16:00'dan sonra "Veri /
TLREF Verileri" altında yayımladığı söyleniyor — bu oturumdan borsaistanbul.com
engelli, yani ölçüm buluttan yapılır.

Bu betik ağa çıkar, depoya YAZMAZ, HÜKÜM KURMAZ:
  (1) EVDS'te şu an TLREF'in son gözlemleri (gecikmenin bugünkü hâli)
  (2) BIST'in TLREF sayfalarındaki bağlar — adres TAHMİN EDİLMEZ, sayfadan
      çözülür; tlref/veri geçen her bağ adıyla basılır
  (3) indirilebilir veri dosyası bulunursa: biçimi, ilk/son satırları, son
      tarihi — ve EVDS ile örtüşen günlerde değerler birebir aynı mı
  (4) kural setinin ilan/yayım saatini söyleyen satırlar (PDF akışlarından)
"""
from __future__ import annotations

import io
import re
import sys
import zlib
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
S.headers.update({"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"})

# ─────────────────────────── (1) EVDS
print("\n(1) EVDS — TP.BISTTLREF.ORAN · TP.BISTTLREF.KAPANIS son gözlemler")
EVDS = {}
try:
    kok = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(kok / "Aktarılacak Projeler" / "Fonlama"))
    import veri as F  # noqa: E402
    bas = SIMDI.date() - dt.timedelta(days=20)
    url = (f"{F.BASE}/series=TP.BISTTLREF.ORAN-TP.BISTTLREF.KAPANIS"
           f"&startDate={bas:%d-%m-%Y}&endDate={SIMDI.date():%d-%m-%Y}&type=json")
    j = F._cek(url)
    for s in (j.get("items") or [])[-8:]:
        print(f"  {s.get('Tarih')}  oran {s.get('TP_BISTTLREF_ORAN')}  endeks {s.get('TP_BISTTLREF_KAPANIS')}")
    for s in j.get("items") or []:
        if s.get("TP_BISTTLREF_ORAN") not in (None, ""):
            EVDS[s["Tarih"]] = float(s["TP_BISTTLREF_ORAN"])
except Exception as e:  # noqa: BLE001
    print(f"  ! EVDS ölçülemedi: {type(e).__name__}: {str(e)[:160]}")


# ─────────────────────────── (2) BIST sayfaları ve bağlar
def al(url: str, **kw):
    try:
        r = S.get(url, timeout=25, allow_redirects=True, **kw)
        print(f"  GET {url} → {r.status_code} {r.headers.get('content-type', '')[:40]} "
              f"{len(r.content)} bayt" + (f" (son adres {r.url})" if r.url != url else ""))
        return r
    except Exception as e:  # noqa: BLE001
        print(f"  GET {url} → {type(e).__name__}: {str(e)[:120]}")
        return None


print("\n(2) BIST TLREF SAYFALARI — bağlar sayfadan çözülür")
SAYFALAR = ["https://www.borsaistanbul.com/en/indices/tlref",
            "https://www.borsaistanbul.com/tr/endeksler/tlref",
            "https://www.borsaistanbul.com/en/indices/tlrefk"]
baglar: dict[str, str] = {}
for u in SAYFALAR:
    r = al(u)
    if r is None or r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
        continue
    html = r.text
    for m in re.finditer(r'href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
        href, metin = m.group(1), re.sub(r"<[^>]+>|\s+", " ", m.group(2)).strip()
        tam = urljoin(r.url, href)
        if re.search(r"tlref|veri|data|datastore|\.xls|\.csv|\.zip", tam + " " + metin, re.I):
            baglar.setdefault(tam, metin[:70])
    for m in re.finditer(r".{0,120}(15[:.]50|16[:.]00|12[:.]35|12[:.]45).{0,120}", html):
        print("    saat geçen metin:", re.sub(r"<[^>]+>|\s+", " ", m.group(0))[:240])
print(f"\n  tlref/veri geçen {len(baglar)} bağ:")
for u, t in sorted(baglar.items()):
    print(f"    {t!r:72s} {u}")

# ─────────────────────────── (3) veri dosyaları
print("\n(3) VERİ DOSYALARI — derinlik 1, yalnız tlref geçen bağlar")
try:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "openpyxl", "xlrd"],
                   check=False, capture_output=True, timeout=120)
except Exception:  # noqa: BLE001
    pass
import pandas as pd  # noqa: E402

ikinci: dict[str, str] = {}
for u, t in sorted(baglar.items()):
    if "tlref" not in (u + t).lower():
        continue
    r = al(u)
    if r is None or r.status_code != 200:
        continue
    ct = r.headers.get("content-type", "")
    if "html" in ct:
        for m in re.finditer(r'href=["\']([^"\']+)["\']', r.text, re.I):
            tam = urljoin(r.url, m.group(1))
            if re.search(r"\.(xlsx?|csv|zip|txt)(\?|$)", tam, re.I) or "tlref" in tam.lower():
                ikinci.setdefault(tam, u)
        for m in re.finditer(r".{0,120}(15[:.]50|16[:.]00|12[:.]35|12[:.]45).{0,120}", r.text):
            print("    saat geçen metin:", re.sub(r"<[^>]+>|\s+", " ", m.group(0))[:240])
print(f"\n  ikinci düzey {len(ikinci)} aday:")
for u, kaynak in sorted(ikinci.items()):
    print(f"    {u}   (← {kaynak})")


def tablo_oku(r) -> pd.DataFrame | None:
    ad = r.url.lower()
    try:
        if ad.endswith(".csv") or "csv" in r.headers.get("content-type", ""):
            return pd.read_csv(io.BytesIO(r.content), sep=None, engine="python")
        if re.search(r"\.xlsx?(\?|$)", ad) or "excel" in r.headers.get("content-type", "") \
                or "spreadsheet" in r.headers.get("content-type", ""):
            return pd.read_excel(io.BytesIO(r.content))
    except Exception as e:  # noqa: BLE001
        print(f"      okunamadı: {type(e).__name__}: {str(e)[:120]}")
    return None


for u in sorted(ikinci)[:25]:
    if not re.search(r"\.(xlsx?|csv|zip|txt)(\?|$)", u, re.I):
        continue
    r = al(u)
    if r is None or r.status_code != 200:
        continue
    df = tablo_oku(r)
    if df is None:
        continue
    print(f"      sütunlar: {list(df.columns)[:12]}  satır {len(df)}")
    print("      ilk:", df.head(2).to_dict("records"))
    print("      son:", df.tail(4).to_dict("records"))

# ─────────────────────────── (4) kural seti PDF
print("\n(4) KURAL SETİ — ilan/yayım saatini söyleyen satırlar")
for pdf in ("https://www.borsaistanbul.com/files/tlref-kural-seti-tr-29012026.pdf",):
    r = al(pdf)
    if r is None or r.status_code != 200:
        continue
    ham = r.content
    metin = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", ham, re.S):
        try:
            metin.append(zlib.decompress(m.group(1)).decode("latin-1", "ignore"))
        except Exception:  # noqa: BLE001
            continue
    duz = " ".join(metin)
    parca = " ".join(re.findall(r"\(([^)]{1,200})\)", duz))
    for m in re.finditer(r".{0,160}(15[:.]\s?50|16[:.]\s?00|15[:.]\s?30|12[:.]\s?35).{0,160}", parca):
        print("    PDF:", m.group(0)[:330])
    if not parca.strip():
        print("    PDF metni akışlardan çözülemedi (yazı tipi eşlemesi) — saat bu yoldan ölçülemedi")

print("\nbitti", dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "UTC")
