# -*- coding: utf-8 -*-
"""KEŞİF — küresel emtia/ABD verisi için HANGİ KAYNAK koşucudan erişilebilir.

İlk keşif koşusu FRED'de asıldı: 29 seri × 60 sn zaman aşımı, iş bütçesi doldu
ve tek satır bile öğrenemedik. Ders: önce KAYNAK denenir, sonra seri. Bu betik
her adayı KISA zaman aşımıyla (8 sn) bir kez yoklar, cevabın ilk satırlarını
basar ve hepsini bir dakikada bitirir.

Aday kaynaklar aynı sayıyı farklı kapılardan verir; biri kapalıysa diğeri açık
olabilir. Aranan şey: 1980'e uzanan AYLIK birincil emtia fiyatları + ABD TÜFE.
"""
from __future__ import annotations

import socket
import sys
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
ZA = 8

# İKİNCİ TUR. Birinci tur 31.08.2026'da şunu ölçtü: FRED koşucudan ZAMAN AŞIMINA
# uğruyor (üç uç, üçü de), IMF SDMX'in DNS'i çözülmüyor, IMF datamapper 403,
# stooq JavaScript kapısı koyuyor. Açık çıkanlar: Dünya Bankası Pink Sheet
# (xlsx, aylık, 1960→), BLS API (anahtarsız, ABD TÜFE), FAO sayfası, NOAA.
# Eksik kalan iki şey aranıyor: politika faizi ve Türkiye dışı bir TÜFE karşılığı.
ADAYLAR = [
    ("BIS toplu — merkez bankası politika faizleri (aylık, uzun tarihçe)",
     "https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip"),
    ("BIS API — politika faizi (ABD)",
     "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.US?format=csv"),
    ("Fed DDP — H.15 (politika faizi)",
     "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&series=bf17364827e38702b42a58cf8eaa3f78&lastobs=&from=&to=&filetype=csv&label=include&layout=seriescolumn"),
    ("NY Fed — etkin federal fonlama oranı",
     "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/10.json"),
    ("Dünya Bankası API — dünya TÜFE (yıllık)",
     "https://api.worldbank.org/v2/country/WLD/indicator/FP.CPI.TOTL.ZG?format=json&per_page=100"),
    ("ECB SDW — Euro Bölgesi HICP manşet",
     "https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.000000.4.ANR?format=csvdata&startPeriod=2024-01"),
    ("ECB SDW — Euro Bölgesi HICP gıda",
     "https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.010000.4.ANR?format=csvdata&startPeriod=2024-01"),
    ("BLS — ABD TÜFE gıda (CUUR0000SAF1)",
     "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SAF1"),
    ("BLS — ABD çekirdek TÜFE (CUUR0000SA0L1E)",
     "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0L1E"),
]

ADAYLAR_TUR1 = [
    ("FRED csv (emtia gıda)",
     "https://fred.stlouisfed.org/graph/fredgraph.csv?id=PFOODINDEXM"),
    ("FRED csv (ABD TÜFE)",
     "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL"),
    ("FRED anasayfa",
     "https://fred.stlouisfed.org/"),
    ("Dünya Bankası Pink Sheet (aylık, 1960→)",
     "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx"),
    ("IMF SDMX — birincil emtia (PCPS)",
     "http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/PCPS/M.W00.PFOOD.IX?startPeriod=2020"),
    ("IMF datamapper",
     "https://www.imf.org/external/datamapper/api/v1/indicators"),
    ("FAO gıda fiyat endeksi sayfası",
     "https://www.fao.org/worldfoodsituation/foodpricesindex/en/"),
    ("BLS zaman serisi API (ABD TÜFE)",
     "https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0"),
    ("stooq (emtia vadelileri)",
     "https://stooq.com/q/d/l/?s=zw.f&i=m"),
    ("NOAA ONI (halihazırda çalışan uç — kontrol)",
     "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"),
]
# Argümansız koşuda iki tur da yoklanır; "tur1"/"tur2" ile daraltılır.


def dene(ad: str, url: str) -> None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=ZA) as r:
            ham = r.read(1400)
            kod, tur = r.status, r.headers.get("Content-Type", "?")
        try:
            bas = ham.decode("utf-8", errors="replace")
        except Exception:
            bas = repr(ham[:200])
        satir = [x for x in bas.splitlines() if x.strip()][:3]
        print(f"  ✓ {kod}  {ad}\n      tür: {tur}")
        for x in satir:
            print(f"      | {x[:150]}")
    except urllib.error.HTTPError as ex:
        print(f"  ✗ HTTP {ex.code}  {ad}  — {url[:70]}")
    except (socket.timeout, TimeoutError):
        print(f"  ✗ ZAMAN AŞIMI ({ZA} sn)  {ad}  — {url[:70]}")
    except Exception as ex:
        print(f"  ✗ {type(ex).__name__}  {ad}  — {str(ex)[:90]}")


def main() -> int:
    sec = [a for a in sys.argv[1:] if a.strip()]
    liste = list(ADAYLAR)
    if "tur2" not in sec:
        liste += ADAYLAR_TUR1
    sec = [a for a in sec if a not in ("tur1", "tur2")]
    if "tur1" in sys.argv[1:]:
        liste = list(ADAYLAR_TUR1)
    print(f"── kaynak yoklaması (zaman aşımı {ZA} sn) · {len(liste)} aday\n")
    for ad, url in liste:
        if sec and not any(x.lower() in ad.lower() for x in sec):
            continue
        dene(ad, url)
        print()
    print("── bitti. Açık kapılardan hangisi 1980'e uzanan AYLIK emtia + ABD TÜFE "
          "veriyorsa hat onun üstüne kurulur.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
