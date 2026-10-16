#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber takviminin İKİNCİ geçişi: ilk geçişin ulaşamadığı resmi listeler (bulut koşucusu).

İlk geçiş (16.10.2026 08:51) ölçtü:
  · BLS — bls.gov otomatik istekleri reddediyor (403; makro dersinin üç geçişi de
    aynısını ölçmüştü). Bu geçiş bls.gov'a HİÇ istek atmaz. Yayım tarihleri Internet
    Archive'ın anlık görüntü dizininden (CDX) okunur: BLS'nin arşiv dosyaları yayım
    tarihiyle adlandırılır (`news.release/archives/empsit_AAGGYYYY.htm`) ve dizin
    arşivlenmiş her dosyanın adını tek yanıtta verir. Ayrıca her seriden birkaç
    arşiv dosyasının kendisi indirilir: ambargo satırı ("8:30 a.m. (ET)") oradadır.
  · ECB — dizin sayfaları listeyi JavaScript'le yıllık `index_include.en.html`
    dosyalarından yükler; ilk geçiş sayfanın kabuğunu indirdi, listeyi indiremedi.
    Bu geçiş karar, basın toplantısı ve basın bülteni include dosyalarını ister;
    bülten başlığında yayım SAATİNDEN söz eden sayfaları ayrıca indirir.
  · BoE — "Bank Rate" tablosu yalnız DEĞİŞİKLİK tarihlerini verir. Bu geçiş her
    yılın her ayı için MPC özet sayfasını (`monetary-policy-summary-and-minutes/
    YYYY/<ay>-YYYY`) ister; toplantı olmayan ay 404 döner ve öyle kaydedilir.
  · Fed — basın toplantısı sayfalarından örnekler (saati yazıyor mu).

Internet Archive istek sınırı ölçülmüştü (makro dersi: hızlı ardışık isteklerde 429):
istekler arası 10 sn, 429'da artan bekleme. Bütçe 18 dakika; var olan dosya yeniden
indirilmez. Yalnız indirir; ayrıştırma yerelde (`takvim_kur.py`).
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import urllib3

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "takvim" / "ham"
BASLIK = {"User-Agent": "tto-trading-arastirma/1.0 (+https://cocoonish.github.io)",
          "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
BUTCE_SN = 18 * 60
T0 = time.monotonic()
YILLAR = list(range(2018, 2027))
AYLAR = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
         "november", "december"]
HAVUZ = urllib3.PoolManager(num_pools=8, maxsize=2, block=True, headers=BASLIK, retries=False)


def ad(url: str) -> str:
    sade = re.sub(r"^https?://", "", url)
    sade = re.sub(r"[^A-Za-z0-9._-]+", "_", sade)[:150]
    return f"{sade}_{hashlib.sha1(url.encode()).hexdigest()[:8]}.html"


def kalan() -> float:
    return BUTCE_SN - (time.monotonic() - T0)


def getir(url: str, bekleme: tuple = (0, 4, 10), arsiv: bool = False) -> dict:
    yol = HAM / ad(url)
    if yol.exists():
        return {"url": url, "durum": "var", "dosya": yol.name}
    son = ""
    for b in bekleme:
        if kalan() < 30:
            return {"url": url, "durum": "butce"}
        if b:
            time.sleep(b)
        try:
            r = HAVUZ.request("GET", url, timeout=urllib3.Timeout(connect=15.0, read=60.0),
                              retries=urllib3.Retry(total=None, connect=0, read=0, status=0, other=0, redirect=5),
                              preload_content=True)
            if r.status == 200:
                yol.write_bytes(r.data)
                return {"url": url, "durum": 200, "dosya": yol.name, "bayt": len(r.data)}
            son = f"HTTP {r.status}"
            if r.status in (403, 404, 410):
                break
        except urllib3.exceptions.HTTPError as e:
            son = type(e).__name__
    return {"url": url, "durum": son}


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    mp = HAM / "manifest2.json"
    manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}

    def kaydet(s: dict) -> dict:
        manifest[s["url"]] = {k: v for k, v in s.items() if k != "url"}
        print(f"{s.get('durum')}\t{s['url']}", flush=True)
        return s

    # 1) BLS — Internet Archive CDX (bls.gov'a istek yok)
    ia_bekle = (0, 30, 75, 150)
    cdx = ("https://web.archive.org/cdx/search/cdx?url=bls.gov/news.release/archives/{seri}_"
           "&matchType=prefix&output=json&fl=original,timestamp,statuscode,mimetype&collapse=urlkey&limit=20000")
    ornek = {}
    for seri in ("empsit", "cpi"):
        s = kaydet(getir(cdx.format(seri=seri), ia_bekle))
        time.sleep(10)
        if s.get("dosya"):
            try:
                satir = json.loads((HAM / s["dosya"]).read_text(encoding="utf-8"))[1:]
            except ValueError:
                satir = []
            # Her yıldan en eski ve en yeni 200'lü htm kopyası: ambargo satırını sınamak için örnek.
            yillik: dict[str, list] = {}
            for orij, ts, durum, mime in satir:
                m = re.search(rf"{seri}_(\d{{2}})(\d{{2}})(\d{{4}})\.htm$", orij)
                if m and durum == "200" and int(m.group(3)) >= 2018:
                    yillik.setdefault(m.group(3), []).append((orij, ts))
            ornek[seri] = [(v[0], v[-1]) for _, v in sorted(yillik.items())]
    for seri, ciftler in ornek.items():
        for (ilk, son) in ciftler:
            for orij, ts in {ilk, son}:
                if kalan() < 120:
                    break
                kaydet(getir(f"https://web.archive.org/web/{ts}id_/{orij}", ia_bekle))
                time.sleep(10)

    # 2) ECB — yıllık include dosyaları
    ecb = []
    for y in YILLAR:
        ecb += [f"https://www.ecb.europa.eu/press/govcdec/mopo/{y}/html/index_include.en.html",
                f"https://www.ecb.europa.eu/press/pressconf/{y}/html/index_include.en.html",
                f"https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/{y}/html/index_include.en.html",
                f"https://www.ecb.europa.eu/press/pr/date/{y}/html/index_include.en.html"]
    for u in ecb:
        kaydet(getir(u))
        time.sleep(0.5)
    # bülten başlığında yayım saati geçenler (ör. karar ve basın toplantısı saatinin değişmesi)
    saat_kalip = re.compile(r'<a[^>]+href="([^"]+\.en\.html)"[^>]*>([^<]*(?:timing|time of|publication time|'
                            r'press conference|14:15|13:45)[^<]*)</a>', re.I)
    for u, m in list(manifest.items()):
        if "/press/pr/date/" in u and m.get("dosya") and (HAM / m["dosya"]).exists():
            metin = (HAM / m["dosya"]).read_text(encoding="utf-8", errors="replace")
            for href, baslik in saat_kalip.findall(metin):
                if kalan() < 60:
                    break
                kaydet(getir(urljoin(u, href)))
                time.sleep(0.5)

    # 3) BoE — MPC özet sayfaları, yıl × ay
    for y in YILLAR:
        for a in AYLAR:
            if kalan() < 60:
                break
            kaydet(getir(f"https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/{y}/{a}-{y}",
                         bekleme=(0, 3)))
            time.sleep(0.5)

    # 4) Fed — basın toplantısı sayfası örnekleri
    for t in ("20180321", "20190130", "20200303", "20200315", "20230322", "20260916"):
        kaydet(getir(f"https://www.federalreserve.gov/monetarypolicy/fomcpresconf{t}.htm"))
        time.sleep(0.5)

    manifest["_koşu"] = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "sure_sn": round(time.monotonic() - T0, 1)}
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    durumlar: dict[str, int] = {}
    for k, v in manifest.items():
        if not k.startswith("_"):
            durumlar[str(v.get("durum"))] = durumlar.get(str(v.get("durum")), 0) + 1
    print("durumlar:", durumlar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
