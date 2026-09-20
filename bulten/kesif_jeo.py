#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JEOPOLİTİK/ENERJİ KEŞFİ — hangi birincil kaynak AÇIK, ardında ne var.

Bu oturumlar `raw.githubusercontent.com` dışında hiçbir yere çıkamıyor
(ölçüldü: altı adresin beşi bağlantı hatası). Bulut koşucusu çıkabiliyor —
PPK arşivinde ölçülmüş hâli var. Bu betik o asimetriyi kullanır.

SIRA CLAUDE.md'DEN: önce KAYNAK yoklanır (her aday 8 saniye, bir dakikada
biter), sonra AÇIK kapının ardındaki seriler ölçülür. Ters sırada bir keşif
koşusu 20 dakikalık bütçeyi tek satır öğrenmeden doldurabiliyor.

Aranan dört şey:
  1. Hürmüz Boğazı GEÇİŞ SAYISI — IMF PortWatch günlük darboğaz sayımı
     yayımlıyor; başka hiçbir ücretsiz kaynakta günlük geçiş yok.
  2. Rafineri/enerji arz kesintisi — EIA haftalık ürün stoku ve rafineri
     kullanım oranı.
  3. OLAY YOĞUNLUĞU — GDELT (depo bunu FX haber hattında zaten kullanıyor).
  4. HABER — deponun kendi yayıncı akışları, jeopolitik süzgeçle.

Depoya YAZMAZ; çıktı koşu kaydında kalır (`veri.yml` keşif işi
`contents: read`).

Koşum:  veri.yml → kesif = bulten/kesif_jeo.py
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

ZAMAN_ASIMI = 8            # yoklama başına; bir dakikada biter
BASLIK = {"User-Agent": "Mozilla/5.0 (compatible; tto-arastirma/1.0)"}


# ── 1. YOKLAMA ────────────────────────────────────────────────────────────
# Her aday ADIYLA ve NE İÇİN sorulduğuyla yazılır: "bulunamadı" demek ama
# neyin aranmış olduğunu söylememek, her düzeltme için yeni bir koşu demek.
ADAYLAR = [
    # (ad, url, ne için)
    ("PortWatch darboğaz (ArcGIS)",
     "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
     "Daily_Chokepoints_Data/FeatureServer/0?f=json", "Hürmüz günlük geçiş"),
    ("PortWatch katalog",
     "https://portwatch.imf.org/datasets.json", "darboğaz veri kümeleri"),
    ("EIA v2 kök", "https://api.eia.gov/v2/", "ürün stoku · rafineri kullanımı"),
    ("EIA açık seri", "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
     "?frequency=weekly&data[0]=value&length=5", "haftalık stok"),
    ("GDELT doc api",
     "https://api.gdeltproject.org/api/v2/doc/doc?query=hormuz&mode=artlist"
     "&maxrecords=5&format=json", "olay yoğunluğu"),
    ("GDELT tone timeline",
     "https://api.gdeltproject.org/api/v2/doc/doc?query=%22strait%20of%20hormuz%22"
     "&mode=timelinevolinfo&timespan=6m&format=json", "geçiş haberi zaman serisi"),
    ("Dünya Bankası Pink Sheet",
     "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-"
     "0050012025/related/CMO-Historical-Data-Monthly.xlsx", "aylık emtia"),
    ("Yahoo chart BZ=F",
     "https://query1.finance.yahoo.com/v8/finance/chart/BZ=F?range=2y&interval=1d",
     "Brent tarihçe"),
    ("Reuters RSS", "https://www.reuters.com/arc/outboundfeeds/rss/", "haber"),
    ("BBC World RSS", "https://feeds.bbci.co.uk/news/world/rss.xml", "haber"),
    ("AA Politika RSS", "https://www.aa.com.tr/tr/rss/default?cat=politika", "haber"),
    ("AL Monitor RSS", "https://www.al-monitor.com/rss.xml", "bölge haberi"),
    ("UN Comtrade", "https://comtradeapi.un.org/public/v1/", "ticaret akımı"),
    ("Baltic/Clarksons", "https://www.clarksons.net/", "navlun"),
    ("ACLED", "https://api.acleddata.com/acled/read", "çatışma olayı"),
    ("TCMB duyuru", "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/"
     "Main+Menu/Duyurular/Basin", "resmî metin"),
]


def yokla() -> dict[str, dict]:
    print("=" * 78)
    print("1. YOKLAMA — hangi kapı açık (aday başına %d sn)" % ZAMAN_ASIMI)
    print("=" * 78)
    acik = {}
    for ad, url, nicin in ADAYLAR:
        t0 = time.time()
        try:
            r = requests.get(url, timeout=ZAMAN_ASIMI, headers=BASLIK)
            sn = time.time() - t0
            n = len(r.content)
            print(f"  {r.status_code:3d}  {n:>9,} bayt  {sn:5.2f}sn  {ad}  ({nicin})")
            if r.status_code == 200 and n > 0:
                acik[ad] = {"url": url, "bayt": n, "metin": r.text[:400]}
        except Exception as ex:                                  # noqa: BLE001
            print(f"  ---  {type(ex).__name__:>22}  {time.time()-t0:5.2f}sn  {ad}")
    print(f"\n  AÇIK: {len(acik)} / {len(ADAYLAR)}")
    return acik


# ── 2. HÜRMÜZ GEÇİŞLERİ ───────────────────────────────────────────────────
PW_SORGU = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
            "Daily_Chokepoints_Data/FeatureServer/0/query")


def hurmuz():
    print()
    print("=" * 78)
    print("2. HÜRMÜZ GEÇİŞLERİ — IMF PortWatch günlük darboğaz sayımı")
    print("=" * 78)
    # Önce ALAN ADLARINI sor: sütun adı tahmin edilmez, istenir.
    try:
        r = requests.get(PW_SORGU.replace("/query", "") + "?f=json",
                         timeout=20, headers=BASLIK)
        alanlar = [a["name"] for a in r.json().get("fields", [])]
        print("  alanlar:", ", ".join(alanlar[:30]))
    except Exception as ex:                                      # noqa: BLE001
        print(f"  alan listesi alınamadı: {ex!r}")
        alanlar = []

    for ad_alan in ("portname", "chokepoint", "CHOKEPOINT", "name"):
        if ad_alan in alanlar:
            break
    else:
        ad_alan = "portname"

    try:
        r = requests.get(PW_SORGU, timeout=45, headers=BASLIK, params={
            "where": f"{ad_alan} LIKE '%Hormuz%'",
            "outFields": "*", "f": "json",
            "orderByFields": "date DESC", "resultRecordCount": 400})
        js = r.json()
        ozl = js.get("features", [])
        print(f"  kayıt: {len(ozl)}")
        if ozl:
            print("  örnek kayıt:", json.dumps(ozl[0]["attributes"], ensure_ascii=False)[:500])
            satir = []
            for f in ozl:
                a = f["attributes"]
                t = a.get("date")
                if isinstance(t, (int, float)):
                    t = datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")
                satir.append((t, a))
            satir.sort()
            print(f"  aralık: {satir[0][0]} → {satir[-1][0]}")
            sayi_alan = [k for k in satir[-1][1]
                         if any(s in k.lower() for s in ("n_", "num", "count", "transit", "cargo", "capacity"))]
            print("  sayı alanları:", sayi_alan[:14])
            print("  --- son 25 gün ---")
            for t, a in satir[-25:]:
                print("   ", t, {k: a.get(k) for k in sayi_alan[:8]})
    except Exception as ex:                                      # noqa: BLE001
        print(f"  sorgu düştü: {ex!r}")


# ── 3. OLAY YOĞUNLUĞU ─────────────────────────────────────────────────────
def gdelt():
    print()
    print("=" * 78)
    print("3. OLAY YOĞUNLUĞU — GDELT haber hacmi zaman serisi")
    print("=" * 78)
    for etiket, q in (("Hürmüz", '"strait of hormuz"'),
                      ("İran savaşı", '"iran war"'),
                      ("rafineri saldırısı", '"refinery" ("strike" OR "attack" OR "drone")'),
                      ("Rusya rafineri", '"russian refinery"'),
                      ("enerji ateşkesi", '"energy ceasefire" OR "ceasefire" "energy"')):
        u = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
             + requests.utils.quote(q) + "&mode=timelinevol&timespan=9m&format=json")
        try:
            r = requests.get(u, timeout=30, headers=BASLIK)
            js = r.json()
            seri = js["timeline"][0]["data"]
            son = seri[-1]
            deger = [p["value"] for p in seri]
            zirve = max(range(len(deger)), key=lambda i: deger[i])
            print(f"  {etiket:<20} n={len(seri):4d}  son {son['date'][:10]} {son['value']:.4f}"
                  f"  · zirve {seri[zirve]['date'][:10]} {deger[zirve]:.4f}"
                  f"  · son/zirve {son['value']/deger[zirve]*100 if deger[zirve] else 0:.0f}%")
            # Son 12 haftanın seyri: tırmanıyor mu, sönüyor mu
            k = max(1, len(seri) // 40)
            print("      seyir: " + " ".join(f"{p['date'][4:8]}:{p['value']:.3f}"
                                             for p in seri[::k][-12:]))
        except Exception as ex:                                  # noqa: BLE001
            print(f"  {etiket:<20} düştü: {ex!r}")


# ── 4. HABER ──────────────────────────────────────────────────────────────
KALIP = re.compile(
    r"İran|Iran|Hürmüz|Hormuz|Tahran|Tehran|Basra|Husi|Houthi|Yemen|Riyad|Riyadh|"
    r"Rusya|Russia|Ukrayna|Ukraine|rafineri|refiner|Novorossiysk|Primorsk|Ust-Luga|"
    r"Druzhba|dizel|diesel|distilat|distillate|crack|tanker|OPEC|OPEC\+|ateşkes|"
    r"ceasefire|müzakere|talks|yaptırım|sanction|boğaz|strait|petrol|oil|Brent",
    re.I)


def haberler():
    print()
    print("=" * 78)
    print("4. HABER — deponun kendi yayıncı akışları, jeopolitik süzgeçle")
    print("=" * 78)
    sys.path.insert(0, "/home/runner/work/tto-trading/tto-trading/bulten")
    sys.path.insert(0, ".")
    try:
        import ayar
        kaynaklar = ayar.HABER_KAYNAKLARI
    except Exception as ex:                                      # noqa: BLE001
        print(f"  ayar okunamadı ({ex!r}) — gömülü liste")
        kaynaklar = [{"ad": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
                     {"ad": "AA Politika", "url": "https://www.aa.com.tr/tr/rss/default?cat=politika"}]
    import xml.etree.ElementTree as ET
    toplam = tut = 0
    for k in kaynaklar:
        try:
            r = requests.get(k["url"], timeout=15, headers=BASLIK)
            kok = ET.fromstring(r.content)
            ogeler = kok.iter("item")
            bulunan = []
            for o in ogeler:
                b = (o.findtext("title") or "").strip()
                tar = (o.findtext("pubDate") or "")[:22]
                toplam += 1
                if KALIP.search(b):
                    bulunan.append((tar, b))
            if bulunan:
                print(f"\n  ── {k['ad']} ({len(bulunan)} eşleşme)")
                for tar, b in bulunan[:14]:
                    print(f"     {tar[:17]:<18} {b[:135]}")
                tut += len(bulunan)
        except Exception as ex:                                  # noqa: BLE001
            print(f"  ── {k['ad']}: OKUNAMADI ({type(ex).__name__})")
    print(f"\n  taranan başlık {toplam} · eşleşen {tut}")


# ── 5. ENERJİ TARİHÇESİ ───────────────────────────────────────────────────
def enerji():
    print()
    print("=" * 78)
    print("5. ENERJİ — iki yıllık tarihçe (bültenin bir yıllık penceresinden uzun)")
    print("=" * 78)
    try:
        import yfinance as yf
        kodlar = ["BZ=F", "CL=F", "HO=F", "RB=F", "NG=F", "GC=F"]
        df = yf.download(kodlar, period="3y", interval="1d",
                         progress=False, auto_adjust=False)["Close"]
        df = df.dropna(how="all")
        print(f"  {df.index[0].date()} → {df.index[-1].date()}  n={len(df)}")
        d = df.dropna()
        crack = (2 * d["RB=F"] * 42 + d["HO=F"] * 42 - 3 * d["CL=F"]) / 3
        dist = d["HO=F"] * 42 - d["CL=F"]
        ben = d["RB=F"] * 42 - d["CL=F"]
        for ad, s in (("3:2:1", crack), ("distilat", dist), ("benzin", ben),
                      ("Brent", d["BZ=F"]), ("Brent−WTI", d["BZ=F"] - d["CL=F"])):
            srt = sorted(s.values)
            yp = 100.0 * sum(1 for y in srt if y <= s.iloc[-1]) / len(srt)
            print(f"  {ad:<10} son {s.iloc[-1]:8.2f}  3y-min {srt[0]:7.2f}  "
                  f"medyan {srt[len(srt)//2]:7.2f}  maks {srt[-1]:7.2f}  yüzdelik {yp:5.1f}%")
        print("\n  --- distilat crack, aylık ortalama (3 yıl) ---")
        ay = dist.resample("MS").mean()
        print("  " + " ".join(f"{t.strftime('%y-%m')}:{v:.0f}" for t, v in ay.items()))
    except Exception as ex:                                      # noqa: BLE001
        print(f"  düştü: {ex!r}")


def main() -> int:
    print(f"KEŞİF · {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n")
    acik = yokla()
    hurmuz()
    gdelt()
    enerji()
    haberler()
    print("\nBİTTİ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
