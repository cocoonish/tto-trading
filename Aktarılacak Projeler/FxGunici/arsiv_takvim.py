#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber takviminin RESMİ kaynaklarını ham hâliyle dondurur (bulut koşucusu).

Neden ham sayfa: takvim bir kez ayrıştırılıp CSV'ye yazılsaydı, ayrıştırıcının
bir kusuru kaynağa geri dönmeden düzeltilemezdi ve yayımlanan saatin hangi
belgeden okunduğu kanıtlanamazdı. Bu betik yalnız İNDİRİR: her adresin yanıtı
`veri/takvim/ham/` altına yazılır, durumu `veri/takvim/ham/manifest.json`a.
Ayrıştırma yerelde, ağsız: `takvim.py`.

Kaynaklar (yalnız resmi):
  · BLS — Employment Situation ve CPI yayım arşivi dizinleri; her yayımın
    arşivlenmiş metninin BAŞI (ambargo saati "8:30 a.m. (ET)" orada yazar).
  · Federal Reserve — FOMC takvim sayfaları (güncel + yıl yıl tarihsel) ve her
    toplantının karar metni basın bülteni ("For release at 2:00 p.m.").
  · ECB — para politikası kararı ve basın toplantısı dizinleri (yıl yıl).
  · Bank of England — Para Politikası Özeti ve tutanak dizinleri.

Koşum: arastirma-veri.yml, betik = "Aktarılacak Projeler/FxGunici/arsiv_takvim.py".
Bütçe 18 dakika; tekrar koşulursa var olan dosyaları yeniden indirmez.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import urllib3

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "takvim" / "ham"
BASLIK = {
    # ASCII başlık ŞART (http.client latin-1). BLS betik ajanlarını reddedebiliyor;
    # yaygın bir tarayıcı ajanı ve tanıtım dizgesi birlikte gönderilir.
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/126.0 Safari/537.36 tto-trading-research/1.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
BUTCE_SN = 18 * 60
T0 = time.monotonic()
YILLAR = list(range(2018, 2027))


def ad(url: str) -> str:
    """Adresten güvenli ve tekil dosya adı."""
    sade = re.sub(r"^https?://", "", url)
    sade = re.sub(r"[^A-Za-z0-9._-]+", "_", sade)[:150]
    return f"{sade}_{hashlib.sha1(url.encode()).hexdigest()[:8]}.html"


# requests değil urllib3: deponun ortak HTTP korumasının devre kesicisi toplu
# indirmede geçici zaman aşımlarını bütün isteklere yayıyor (bkz. dukascopy.py).
HAVUZ = urllib3.PoolManager(num_pools=8, maxsize=4, block=True, headers=BASLIK, retries=False)


def getir(url: str, oturum=None, bas_bayt: int | None = None) -> dict:
    yol = HAM / ad(url)
    if yol.exists():
        return {"url": url, "durum": "var", "dosya": yol.name}
    son = ""
    for i in range(4):
        try:
            r = HAVUZ.request("GET", url, timeout=urllib3.Timeout(connect=10.0, read=30.0),
                              retries=urllib3.Retry(total=None, connect=0, read=0, status=0, other=0, redirect=5),
                              preload_content=True)
            if r.status == 200:
                icerik = r.data if bas_bayt is None else r.data[:bas_bayt]
                yol.write_bytes(icerik)
                return {"url": url, "durum": 200, "dosya": yol.name, "bayt": len(r.data),
                        "son_adres": r.geturl() or url}
            son = f"HTTP {r.status}"
            if r.status in (403, 404, 410):
                break
        except urllib3.exceptions.HTTPError as e:
            son = f"{type(e).__name__}"
        time.sleep(1.5 * 2 ** i)
    return {"url": url, "durum": son}


def bagla(dosya: Path, taban: str, kalip: str) -> list[str]:
    metin = dosya.read_text(encoding="utf-8", errors="replace")
    return sorted({urljoin(taban, m) for m in re.findall(kalip, metin)})


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    manifest_yol = HAM / "manifest.json"
    manifest = json.loads(manifest_yol.read_text()) if manifest_yol.exists() else {}
    s = None

    def kaydet(sonuc: dict) -> None:
        manifest[sonuc["url"]] = {k: v for k, v in sonuc.items() if k != "url"}

    # 1) Dizin sayfaları
    dizinler = [
        "https://www.bls.gov/bls/news-release/empsit.htm",
        "https://www.bls.gov/bls/news-release/cpi.htm",
        "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        *[f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm" for y in YILLAR],
        *[f"https://www.ecb.europa.eu/press/govcdec/mopo/{y}/html/index.en.html" for y in YILLAR],
        *[f"https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/{y}/html/index.en.html"
          for y in YILLAR],
        *[f"https://www.ecb.europa.eu/press/pr/date/{y}/html/index.en.html" for y in YILLAR],
        "https://www.ecb.europa.eu/press/govcdec/mopo/html/index.en.html",
        "https://www.ecb.europa.eu/press/press_conference/html/index.en.html",
        "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/monetary-policy-summary-and-minutes",
        "https://www.bankofengland.co.uk/monetary-policy/the-interest-rate-bank-rate",
        "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp",
        "https://www.bankofengland.co.uk/monetary-policy/upcoming-mpc-dates",
    ]
    for u in dizinler:
        kaydet(getir(u, s))
        print(f"{manifest[u].get('durum')}\t{u}", flush=True)

    # 2) BLS: dizindeki her arşivlenmiş yayım (yalnız ilk 6 KB: ambargo satırı başta)
    bls = []
    for kok, kalip in (("empsit", r'href="((?:https?://www\.bls\.gov)?/news\.release/archives/empsit_\d{8}\.htm)"'),
                       ("cpi", r'href="((?:https?://www\.bls\.gov)?/news\.release/archives/cpi_\d{8}\.htm)"')):
        u = f"https://www.bls.gov/bls/news-release/{kok}.htm"
        m = manifest.get(u, {})
        if m.get("dosya") and (HAM / m["dosya"]).exists():
            for link in bagla(HAM / m["dosya"], "https://www.bls.gov", kalip):
                tarih = re.search(r"_(\d{2})(\d{2})(\d{4})\.htm", link)
                if tarih and int(tarih.group(3)) >= 2017:
                    bls.append(link)
    # 3) Fed: takvim sayfalarındaki karar metni bültenleri
    fed = []
    for u, m in list(manifest.items()):
        if "federalreserve.gov/monetarypolicy/fomc" in u and m.get("dosya") and (HAM / m["dosya"]).exists():
            fed += bagla(HAM / m["dosya"], "https://www.federalreserve.gov",
                         r'href="((?:https?://www\.federalreserve\.gov)?/newsevents/pressreleases/monetary20\d{6}a\.htm)"')
    fed = sorted(set(fed))
    # 4) ECB: dizinlerdeki karar ve basın toplantısı sayfaları
    ecb = []
    for u, m in list(manifest.items()):
        if "ecb.europa.eu" in u and m.get("dosya") and (HAM / m["dosya"]).exists():
            ecb += bagla(HAM / m["dosya"], "https://www.ecb.europa.eu",
                         r'href="((?:https?://www\.ecb\.europa\.eu)?/press/(?:pr/date/\d{4}/html/ecb\.mp\d{6}[^"]*\.en\.html|'
                         r'press_conference/monetary-policy-statement/\d{4}/html/ecb\.is\d{6}[^"]*\.en\.html))"')
    ecb = sorted(set(ecb))

    isler = [(u, 6000) for u in bls] + [(u, None) for u in fed] + [(u, None) for u in ecb]
    print(f"alt sayfa: BLS {len(bls)} · Fed {len(fed)} · ECB {len(ecb)}", flush=True)
    with ThreadPoolExecutor(max_workers=4) as h:
        for sonuc in h.map(lambda ub: getir(ub[0], None, ub[1])
                           if time.monotonic() - T0 < BUTCE_SN else {"url": ub[0], "durum": "butce"}, isler):
            kaydet(sonuc)
    manifest["_koşu"] = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "sure_sn": round(time.monotonic() - T0, 1)}
    manifest_yol.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    durumlar: dict[str, int] = {}
    for k, v in manifest.items():
        if not k.startswith("_"):
            durumlar[str(v.get("durum"))] = durumlar.get(str(v.get("durum")), 0) + 1
    print("durumlar:", durumlar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
