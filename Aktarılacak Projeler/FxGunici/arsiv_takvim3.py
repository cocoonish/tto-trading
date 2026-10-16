#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber takviminin ÜÇÜNCÜ geçişi: her olayın SAATİNİ tarih tarih veren resmi belgeler (bulut koşucusu).

İkinci geçiş (16.10.2026 09:30) tarihleri verdi, saati her tarih için vermedi:
  · BLS — Internet Archive dizini dosya adlarını (yayım tarihi) veriyor; saat ise
    yayımın kendi ambargo satırında: "embargoed until 8:30 a.m. (ET) Friday, ...".
    Bu geçiş her yayımın arşivlenmiş kopyasını (yalnız 200 dönen kopya) ister ve
    sayfanın tamamını değil, sayfa başlığı ile ambargo satırını saklar (bir yayım
    ~1 MB; 230 sayfa depoyu 230 MB büyütürdü). Gövdenin sha256'sı da yazılır:
    kopya, Internet Archive adresi ve zaman damgasıyla yeniden indirilip sınanabilir.
    bls.gov'a HİÇ istek atılmaz (BLS otomatik istekleri reddediyor).
  · Fed — karar metni yayım saatini yazıyor ("For release at 2:00 p.m. EDT"), basın
    toplantısı sayfası yazmıyor (altı örnekte ölçüldü: sayfadaki tek saat kararın
    yayım saati). Fed'in AYLIK etkinlik takvimi her etkinliği saatiyle listeler; bu
    geçiş önce Internet Archive dizininden o sayfaların ADINI öğrenir (adres tahmin
    edilmez), sonra her ayın sayfasını Fed'den ister.
  · ECB — karar duyurusu basın toplantısının saatini yazıyor ("press conference
    starting at 14:45 CET today"); bu geçiş 2018'den bu yana her karar duyurusunu
    ister (liste ikinci geçişin include dosyalarından).

PARÇA (`TTO_PARCA`): `bls-empsit` · `bls-cpi` · `fed` · `ecb`; boşsa hepsi. Her parça
yalnız kendi künyesine (`ham/manifest3_<parça>.json`) ve kendi dosyalarına yazar.
Internet Archive istekleri arası 4 sn, 429'da artan bekleme. Bütçe 18 dakika; var
olan dosya yeniden indirilmez. Yalnız indirir; ayrıştırma yerelde (`takvim_kur.py`).
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import urllib3

import ayar as ay
import ozler

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "takvim" / "ham"
BASLIK = {"User-Agent": "tto-trading-arastirma/1.0 (+https://cocoonish.github.io)",
          "Accept": "text/html,application/json;q=0.9,*/*;q=0.8"}
BUTCE_SN = 18 * 60
T0 = time.monotonic()
# İndirme penceresi ayarın penceresinden: başlangıçtan bir ay önce (ilk olayın öncesi), bitişe kadar.
_AYAR = ay.oku()
BIT = _AYAR.bitis
BAS = (_AYAR.baslangic.replace(day=1) - timedelta(days=1)).replace(day=1)
AYLAR = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
         "november", "december"]
HAVUZ = urllib3.PoolManager(num_pools=8, maxsize=2, block=True, headers=BASLIK, retries=False)
IA_BEKLE = (0, 30, 75, 150)
IA_ARA = 4.0


def ad(url: str, uzanti: str = ".html") -> str:
    sade = re.sub(r"^https?://", "", url)
    sade = re.sub(r"[^A-Za-z0-9._-]+", "_", sade)[:150]
    return f"{sade}_{hashlib.sha1(url.encode()).hexdigest()[:8]}{uzanti}"


def kalan() -> float:
    return BUTCE_SN - (time.monotonic() - T0)


def iste(url: str, bekleme: tuple = (0, 4, 10)) -> tuple[int | str, bytes]:
    son: int | str = ""
    for b in bekleme:
        if kalan() < 30:
            return "butce", b""
        if b:
            time.sleep(b)
        try:
            r = HAVUZ.request("GET", url, timeout=urllib3.Timeout(connect=15.0, read=60.0),
                              retries=urllib3.Retry(total=None, connect=0, read=0, status=0, other=0, redirect=5),
                              preload_content=True)
            if r.status == 200:
                return 200, r.data
            son = f"HTTP {r.status}"
            if r.status in (403, 404, 410):
                break
        except urllib3.exceptions.HTTPError as e:
            son = type(e).__name__
    return son, b""


def getir(url: str, bekleme: tuple = (0, 4, 10)) -> dict:
    """Ham sayfayı saklar (var olan dosya yeniden indirilmez)."""
    yol = HAM / ad(url)
    if yol.exists():
        return {"url": url, "durum": "var", "dosya": yol.name}
    durum, veri = iste(url, bekleme)
    if durum == 200:
        yol.write_bytes(veri)
        return {"url": url, "durum": 200, "dosya": yol.name, "bayt": len(veri)}
    return {"url": url, "durum": durum}


def duz(b: bytes) -> str:
    t = b.decode("utf-8", errors="replace")
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).strip()


class Kunye:
    def __init__(self, parca: str):
        self.yol = HAM / f"manifest3_{parca}.json"
        self.v = json.loads(self.yol.read_text(encoding="utf-8")) if self.yol.exists() else {}

    def kaydet(self, s: dict) -> dict:
        self.v[s["url"]] = {k: v for k, v in s.items() if k != "url"}
        print(f"{s.get('durum')}\t{s['url']}", flush=True)
        return s

    def yaz(self) -> None:
        self.v["_koşu"] = {"zaman": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "sure_sn": round(time.monotonic() - T0, 1)}
        self.yol.write_text(json.dumps(self.v, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        d: dict[str, int] = {}
        for k, x in self.v.items():
            if not k.startswith("_"):
                d[str(x.get("durum"))] = d.get(str(x.get("durum")), 0) + 1
        print(f"{self.yol.name}: {d}", flush=True)


# ───────────────────────────────────────────── BLS
def bls(seri: str) -> None:
    k = Kunye(f"bls-{seri}")
    cdx = ("https://web.archive.org/cdx/search/cdx?url=bls.gov/news.release/archives/{seri}_"
           "&matchType=prefix&output=json&fl=original,timestamp,statuscode,mimetype&collapse=urlkey"
           "&filter=statuscode:200&limit=20000").format(seri=seri)
    s = k.kaydet(getir(cdx, IA_BEKLE))
    time.sleep(IA_ARA)
    if not s.get("dosya"):
        k.yaz()
        return
    try:
        satir = json.loads((HAM / s["dosya"]).read_text(encoding="utf-8"))[1:]
    except ValueError:
        satir = []
    aday: dict[str, tuple[str, str]] = {}
    for orij, ts, durum, mime in satir:
        m = re.search(rf"archives/{seri}_(\d{{2}})(\d{{2}})(\d{{4}})\.htm$", orij)
        if not m or durum != "200":
            continue
        try:
            g = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            continue
        if BAS <= g <= BIT and g.isoformat() not in aday:
            aday[g.isoformat()] = (orij, ts)
    hedef = HAM / f"bls_{seri}_ambargo.json"
    defter = json.loads(hedef.read_text(encoding="utf-8")) if hedef.exists() else {}
    for g in sorted(aday):
        if g in defter and defter[g].get("ambargo"):
            continue
        if kalan() < 60:
            break
        orij, ts = aday[g]
        url = f"https://web.archive.org/web/{ts}id_/{orij}"
        durum, veri = iste(url, IA_BEKLE)
        kayit = {"url": url, "orijinal": orij, "wayback": ts, "durum": durum}
        if durum == 200:
            metin = duz(veri)
            i = metin.find("Transmission of material")
            bas = re.search(r"(?is)<title>(.*?)</title>", veri.decode("utf-8", errors="replace"))
            kayit.update({"sha256": hashlib.sha256(veri).hexdigest(), "bayt": len(veri),
                          "baslik": html.unescape(bas.group(1).strip()) if bas else "",
                          "ambargo": metin[i:i + 400] if i >= 0 else ""})
        defter[g] = kayit
        print(f"{durum}\t{g}\t{kayit.get('ambargo', '')[:90]}", flush=True)
        time.sleep(IA_ARA)
    hedef.write_text(json.dumps(defter, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    k.v[f"bls:{seri}:ambargo"] = {"durum": 200, "dosya": hedef.name, "aday": len(aday),
                                  "okunan": sum(1 for x in defter.values() if x.get("ambargo"))}
    k.yaz()


# ───────────────────────────────────────────── Fed
def fed() -> None:
    k = Kunye("fed")
    # Önce Internet Archive dizininden Fed'in etkinlik sayfalarının ADLARI (adres tahmin edilmez).
    cdx = ("https://web.archive.org/cdx/search/cdx?url=federalreserve.gov/newsevents/20&matchType=prefix"
           "&output=json&fl=original,timestamp,statuscode&collapse=urlkey&filter=statuscode:200&limit=20000")
    s = k.kaydet(getir(cdx, IA_BEKLE))
    time.sleep(IA_ARA)
    adlar: set[str] = set()
    bicimler: dict[str, int] = {}
    if s.get("dosya"):
        try:
            for orij, ts, durum in json.loads((HAM / s["dosya"]).read_text(encoding="utf-8"))[1:]:
                m = re.search(r"/newsevents/(20\d{2})-([a-z]+)\.htm$", orij)
                if m and m.group(2) in AYLAR:
                    adlar.add(f"{m.group(1)}-{m.group(2)}")
                b = re.sub(r"\d", "9", orij.split("/newsevents/", 1)[-1].split("?")[0])
                bicimler[b] = bicimler.get(b, 0) + 1
        except ValueError:
            pass
    print(f"Fed aylık takvim sayfası adı dizinde: {len(adlar)}", flush=True)
    # Adres biçimleri (rakam → 9): kalıp tutmazsa bir sonraki geçiş doğru adı buradan seçer.
    for b, n in sorted(bicimler.items(), key=lambda x: -x[1])[:25]:
        print(f"    biçim {n:5d}  {b}", flush=True)
    # Kalıp dizinde varsa (YYYY-ay.htm) kapsamın bütün ayları Fed'in kendisinden istenir.
    if adlar:
        for y in range(2018, 2027):
            for i, a in enumerate(AYLAR):
                if date(y, i + 1, 1) > BIT or kalan() < 60:
                    continue
                k.kaydet(getir(f"https://www.federalreserve.gov/newsevents/{y}-{a}.htm"))
                time.sleep(1.0)
    # Güncel takvimin JSON beslemesi (yaklaşan etkinlikler) — biçimi sınamak için.
    k.kaydet(getir("https://www.federalreserve.gov/json/calendar.json"))
    k.yaz()


# ───────────────────────────────────────────── ECB
def ecb() -> None:
    k = Kunye("ecb")
    m2 = json.loads((HAM / "manifest2.json").read_text(encoding="utf-8"))
    sayfalar: list[str] = []
    for y in range(2018, 2027):
        u = f"https://www.ecb.europa.eu/press/govcdec/mopo/{y}/html/index_include.en.html"
        if not m2.get(u, {}).get("dosya"):
            print(f"include yok: {u}", flush=True)
            continue
        t = (HAM / m2[u]["dosya"]).read_text(encoding="utf-8", errors="replace")
        # Karar duyuruları (ecb.mp…) ve karar listesinde duran öbür bültenler (ecb.pr…, ör. 18.03.2020
        # olağanüstü PEPP duyurusu): adres include dosyasının KENDİSİNDEN okunur, tahmin edilmez.
        for href in re.findall(r'href="(/press/pr/date/\d{4}/html/ecb\.(?:mp|pr)\d{6}[^"]*\.en\.html)"', t):
            if href not in sayfalar:
                sayfalar.append(href)
    print(f"ECB karar duyurusu: {len(sayfalar)}", flush=True)
    for h in sayfalar:
        if kalan() < 60:
            break
        k.kaydet(getir("https://www.ecb.europa.eu" + h))
        time.sleep(1.0)
    k.yaz()


PARCALAR = {"bls-empsit": lambda: bls("empsit"), "bls-cpi": lambda: bls("cpi"), "fed": fed, "ecb": ecb}


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    istenen = os.environ.get("TTO_PARCA", "").split() or list(PARCALAR)
    bilinmeyen = [p for p in istenen if p not in PARCALAR]
    if bilinmeyen:
        raise SystemExit(f"bilinmeyen parça: {bilinmeyen} (tanınan: {list(PARCALAR)})")
    for p in istenen:
        print(f"── {p}", flush=True)
        PARCALAR[p]()
    print(f"bitti: {time.monotonic() - T0:.0f} sn")
    ozler.yaz(HAM)      # ham sayfaların SHA-256 sabitlemesi (takvim_kur okumadan önce sınar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
