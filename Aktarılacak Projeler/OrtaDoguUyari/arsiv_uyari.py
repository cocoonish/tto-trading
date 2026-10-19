#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABD'NİN ORTA DOĞU UYARISI (19.10.2026) — analizin girdi arşivi, bulutta.

Neden gerekli: araştırma ajanları bu oturumdan hiçbir sayfayı açamadı; elçilik uyarılarının metni, tarihsel emsaller
ve tahmin piyasası fiyatları yalnız arama motoru özetlerinden okunabildi. Kural (CLAUDE.md, Brent analizi): bir alıntı
ya da sayı, kaynağın kendi metninde görülmeden yayımlanmaz. Bu betik kaynakları bulutta İNDİRİR ve olduğu gibi saklar;
sorgu yerelde (`kaynak_metin.py`, `dogrula.py`) yapılır.

Parçalar (arastirma-veri.yml `parcalar`; her parça yalnız kendi dosyalarına yazar, künyesi `kunye_<parça>.json`):
  sayfalar  `kaynak_url.json` listesi (haber, resmî arşiv, araştırma notu)
  elcilik   12 elçiliğin uyarı listesi; Ekim 2026 ve Şubat–Mart 2026 uyarıları listeden ÇÖZÜLÜR (adres tahmin edilmez)
  piyasa    Polymarket (arama → İran ile ilgili piyasalar → fiyat geçmişi), Kalshi, Metaculus
  veri      CNBC günlük kapanışlar (Eylül 2026 → bugün), jeopolitik risk endeksi (GPR), Wikipedia olay sayfaları

Yardımcılar (`al`, `yaz`, `kaynak`, `kaydet`) Brent analizinin arşiv modülünden; ham dizin buraya çevrilir.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI.parent / "BrentSenaryo"))
import arsiv_brent as ab  # noqa: E402

ab.HAM = BURASI / "veri" / "ham"
LISTE = BURASI / "kaynak_url.json"
SIMDI = datetime.now(timezone.utc)

ELCILIK = {"sa": "Suudi Arabistan", "ae": "BAE", "kw": "Kuveyt", "jo": "Ürdün", "bh": "Bahreyn", "om": "Umman",
           "ir": "İran", "qa": "Katar", "iq": "Irak", "lb": "Lübnan", "ye": "Yemen", "il": "İsrail"}
#: Listeden izlenecek uyarıların adres kalıbı: Ekim 2026 ve 2026 savaşının başlangıcı (Şubat–Mart).
ELCILIK_DESEN = re.compile(r"(october|september|march|february)-\d{1,2}-2026", re.I)


def _ad(url: str) -> str:
    import hashlib
    oz = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    alan = urllib.parse.urlparse(url).netloc.replace("www.", "")
    return f"{ab._dosya_adi(alan)[:30]}_{oz}"


def _uzanti(govde: bytes) -> str:
    if govde[:5] == b"%PDF-":
        return "pdf"
    s = govde[:200].lstrip()
    if s[:1] in (b"{", b"["):
        return "json"
    return "html"


def _indir(url: str, klasor: str, not_: str, sn: int = 40) -> dict:
    try:
        d, gv = ab.al(url, sn=sn, baslik={"Accept": "text/html,application/pdf,application/json,*/*;q=0.8",
                                          "Accept-Language": "en,tr;q=0.8"})
    except RuntimeError as e:
        print(f"   ! {url[:100]}: {e}"[:200], flush=True)
        return {"hata": str(e)[:160]}
    kayit = {"durum": d, "bayt": len(gv)}
    if d == 200 and gv:
        yol = f"{klasor}/{_ad(url)}.{_uzanti(gv)}.gz"
        ab.yaz(yol, gv, url, d, not_=not_)
        kayit["dosya"] = yol
    print(f"   {d} {len(gv):>8} {url[:110]}", flush=True)
    return kayit


# ─────────────────────────────────────────────────────────────── sayfalar
@ab.kaynak("Kaynak sayfaları")
def sayfalar() -> dict:
    sonuc = {}
    for url in json.loads(LISTE.read_text(encoding="utf-8")):
        if ab.kalan() < 60:
            sonuc[url] = "bütçe doldu"
            continue
        sonuc[url] = _indir(url, "kaynak", "atıf kaynağı")
        time.sleep(0.4)
    return sonuc


# ─────────────────────────────────────────────────────────────── elçilikler
@ab.kaynak("Elçilik uyarıları")
def elcilik() -> dict:
    sonuc = {}
    for cc, ad in ELCILIK.items():
        kok = f"https://{cc}.usembassy.gov"
        bulunan: set[str] = set()
        listeler = [f"{kok}/category/alert/", f"{kok}/category/alert/page/2/", f"{kok}/category/alert/page/3/",
                    f"{kok}/u-s-citizen-services/security-and-travel-information/", f"{kok}/news-events/"]
        kayit = {"liste": {}, "uyari": {}}
        for lu in listeler:
            if ab.kalan() < 90:
                break
            r = _indir(lu, f"elcilik/{cc}", f"{ad} uyarı listesi")
            kayit["liste"][lu] = r
            if r.get("dosya"):
                metin = ab.gzip.decompress((ab.HAM / r["dosya"]).read_bytes()).decode("utf-8", errors="replace")
                for m in re.finditer(r'href="(https?://' + re.escape(f"{cc}.usembassy.gov") + r'/[^"#?]+)"', metin):
                    u = m.group(1)
                    if ELCILIK_DESEN.search(u) and ("alert" in u or "advisory" in u or "message" in u):
                        bulunan.add(u.rstrip("/") + "/")
            time.sleep(0.3)
        for u in sorted(bulunan):
            if ab.kalan() < 60:
                break
            kayit["uyari"][u] = _indir(u, f"elcilik/{cc}", f"{ad} uyarısı")
            time.sleep(0.3)
        sonuc[cc] = {"liste_n": len(kayit["liste"]), "uyari_n": len(kayit["uyari"]), **kayit}
        print(f"   {cc}: {len(bulunan)} uyarı adresi", flush=True)
    return sonuc


# ─────────────────────────────────────────────────────────────── tahmin piyasaları
PM_ARAMA = ["US strike Iran", "US military action against Iran", "Iran ceasefire", "US Iran ceasefire",
            "invade Iran", "Israel strike Iran", "Iran war", "US Iran deal", "Fordow", "Iran Gulf state",
            "Iran attack", "Khamenei", "Hormuz"]
PM_SORU = re.compile(r"\bIran", re.I)
PM_KONU = re.compile(r"strike|military action|attack|ceasefire|invade|invasion|war\b|Fordow|Hormuz|deal|"
                     r"bomb|target|Gulf state|escalat", re.I)
PM_AZAMI = 90


def _json(url: str, sn: int = 30):
    try:
        d, gv = ab.al(url, sn=sn, baslik={"Accept": "application/json"})
    except RuntimeError as e:
        return None, None, str(e)[:120]
    if d != 200:
        return d, gv, None
    try:
        return d, gv, json.loads(gv)
    except Exception:  # noqa: BLE001
        return d, gv, None


@ab.kaynak("Polymarket")
def polymarket() -> dict:
    piyasa: dict[str, dict] = {}
    rapor = {"arama": {}}
    for q in PM_ARAMA:
        for durum in ("active", "closed"):
            url = ("https://gamma-api.polymarket.com/public-search?" +
                   urllib.parse.urlencode({"q": q, "events_status": durum, "limit_per_type": 50,
                                           "keep_closed_markets": 1}))
            d, gv, j = _json(url)
            rapor["arama"][f"{q}|{durum}"] = d
            if d == 200 and gv:
                ab.yaz(f"polymarket/arama_{ab._dosya_adi(q)}_{durum}.json.gz", gv, url, d, not_="Polymarket arama")
            if not isinstance(j, dict):
                continue
            for ev in j.get("events") or []:
                for m in ev.get("markets") or []:
                    soru = m.get("question") or ""
                    if PM_SORU.search(soru) and PM_KONU.search(soru):
                        piyasa.setdefault(str(m.get("id")), {"soru": soru, "slug": m.get("slug"),
                                                             "olay": ev.get("title"), "olay_slug": ev.get("slug"),
                                                             "hacim": float(m.get("volume") or 0)})
            time.sleep(0.3)
    print(f"   Polymarket: {len(piyasa)} aday piyasa", flush=True)
    secilen = sorted(piyasa.items(), key=lambda kv: -kv[1]["hacim"])[:PM_AZAMI]
    rapor["piyasa"] = {}
    for mid, p in secilen:
        if ab.kalan() < 120:
            rapor["piyasa"][mid] = "bütçe doldu"
            continue
        url = f"https://gamma-api.polymarket.com/markets/{mid}"
        d, gv, m = _json(url)
        if d == 200 and gv:
            ab.yaz(f"polymarket/piyasa_{mid}.json.gz", gv, url, d, not_=p["soru"][:160])
        r = {"soru": p["soru"], "durum": d, "gecmis": {}}
        tok = []
        try:
            tok = json.loads((m or {}).get("clobTokenIds") or "[]")
        except Exception:  # noqa: BLE001
            tok = []
        if tok:
            t0 = tok[0]   # ilk sonuç ("Yes")
            for ad_, sorgu in (("gunluk", {"market": t0, "interval": "max", "fidelity": 1440}),
                               ("saatlik", {"market": t0, "interval": "max", "fidelity": 60})):
                hu = "https://clob.polymarket.com/prices-history?" + urllib.parse.urlencode(sorgu)
                d2, g2, j2 = _json(hu)
                n = len((j2 or {}).get("history") or []) if isinstance(j2, dict) else 0
                if d2 == 200 and g2 and n == 0 and isinstance(m, dict) and m.get("startDate") and m.get("endDate"):
                    # Kapanmış piyasada "max" boş dönebiliyor: açık aralıkla yeniden sor.
                    try:
                        bas = int(datetime.fromisoformat(m["startDate"].replace("Z", "+00:00")).timestamp())
                        son = int(datetime.fromisoformat(m["endDate"].replace("Z", "+00:00")).timestamp()) + 86400
                        q2 = {"market": t0, "startTs": bas, "endTs": son, "fidelity": sorgu["fidelity"]}
                        hu = "https://clob.polymarket.com/prices-history?" + urllib.parse.urlencode(q2)
                        d2, g2, j2 = _json(hu)
                        n = len((j2 or {}).get("history") or []) if isinstance(j2, dict) else 0
                    except Exception:  # noqa: BLE001
                        pass
                if d2 == 200 and g2:
                    ab.yaz(f"polymarket/gecmis_{mid}_{ad_}.json.gz", g2, hu, d2, not_=p["soru"][:160])
                r["gecmis"][ad_] = {"durum": d2, "nokta": n}
                time.sleep(0.25)
        rapor["piyasa"][mid] = r
        print(f"   {mid} {r['gecmis']} {p['soru'][:80]}", flush=True)
    return rapor


@ab.kaynak("Kalshi ve Metaculus")
def kalshi_metaculus() -> dict:
    sonuc = {}
    adresler = [
        "https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXUSAIRANAGREEMENT&limit=100",
        "https://api.elections.kalshi.com/trade-api/v2/events?series_ticker=KXUSAIRANAGREEMENT&limit=100",
        "https://api.elections.kalshi.com/trade-api/v2/markets?limit=200&status=open&series_ticker=KXIRANSTRIKE",
        "https://www.metaculus.com/api2/questions/41594/",
        "https://www.metaculus.com/api/posts/41594/",
        "https://www.metaculus.com/api2/questions/?search=Iran%20attack&limit=50",
        "https://www.metaculus.com/api/posts/?search=Iran&limit=50",
    ]
    for u in adresler:
        sonuc[u] = _indir(u, "tahmin", "tahmin platformu")
        time.sleep(0.3)
    return sonuc


# ─────────────────────────────────────────────────────────────── piyasa verisi + olay sayfaları
CNBC_SON = {"brent": "@LCO.1", "wti": "@CL.1", "altin": "@GC.1", "spx": ".SPX", "vix": ".VIX", "dxy": ".DXY",
            "us10y": "US10Y", "try": "TRY=", "bist100": ".XU100"}
WIKI = ["2026 Iran war", "2026 Iran–United States war", "7 May 2026 United States strikes on Iran",
        "Twelve-Day War", "June 2025 United States strikes on Iranian nuclear sites", "Killing of Qasem Soleimani",
        "2013 United States embassy closures", "Worldwide Caution", "2026 Strait of Hormuz crisis",
        "2026 Houthi attacks on Saudi Arabia", "Operation Desert Fox", "Operation Infinite Reach"]


@ab.kaynak("CNBC son dönem")
def cnbc_son() -> dict:
    sonuc = {}
    bas = "20250501"
    yarin = (SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    for ad_, sem in CNBC_SON.items():
        u = ab._cnbc_url(sem, bas, f"{yarin}000000")
        try:
            d, gv = ab.al(u, sn=25, deneme=2)
        except RuntimeError as e:
            sonuc[ad_] = f"hata {e}"[:120]
            continue
        n = ab._bar_sayisi(gv) if d == 200 else 0
        if n:
            ab.yaz(f"cnbc/{ad_}.json.gz", gv, u, d, not_=f"{sem} günlük")
        sonuc[ad_] = {"durum": d, "bar": n}
        print(f"   {ad_}: {d} {n} bar", flush=True)
        time.sleep(0.3)
    return sonuc


@ab.kaynak("Wikipedia")
def wikipedia() -> dict:
    sonuc = {}
    for q in WIKI:
        su = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "query", "list": "search", "srsearch": q, "srlimit": 3, "format": "json"})
        d, gv, j = _json(su)
        basliklar = [x["title"] for x in ((j or {}).get("query") or {}).get("search", [])][:2] if isinstance(j, dict) else []
        sonuc[q] = {"arama": d, "baslik": basliklar}
        for b in basliklar:
            hu = "https://en.wikipedia.org/api/rest_v1/page/html/" + urllib.parse.quote(b.replace(" ", "_"), safe="")
            sonuc[q][b] = _indir(hu, "wiki", f"Wikipedia: {b}", sn=45)
            time.sleep(0.3)
    return sonuc


def main() -> int:
    parca = os.environ.get("TTO_PARCA", "").strip() or "hepsi"
    ab.HAM.mkdir(parents=True, exist_ok=True)
    adimlar = {"sayfalar": [sayfalar], "elcilik": [elcilik], "piyasa": [polymarket, kalshi_metaculus],
               "veri": [cnbc_son, ab.gpr, wikipedia]}
    secim = adimlar.get(parca) or [f for L in adimlar.values() for f in L]
    for f in secim:
        f()
    ab.kaydet(parca)
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
