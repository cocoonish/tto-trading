#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE DERSİ — dış kaynakların YOKLAMASI ve HAM arşivi.

Yalnız bulutta koşar (`arastirma-veri.yml`; bu oturumların koşucusu
kaynaklara çıkamıyor). İlke sırası CLAUDE.md'den: dış kaynak önce YOKLANIR,
sonra kurulur; katalog tahmin edilmez İSTENİR; adres sabitlenmez çözülür.

NE YAPAR. Her kaynak için önce tek bir küçük istek (yoklama, kısa zaman aşımı)
atar; açık çıkarsa asıl indirmeyi yapar. Yanıtlar OLDUĞU GİBİ (gzip'li ham
bayt) `veri/ham/<kaynak>/` altına yazılır; AYRIŞTIRMA BURADA YAPILMAZ, yerelde
(`hazirla_bulut.py`) yapılır. Sebep: bir ayrıştırma kusuru yeniden indirme
gerektirmesin — kaynak bir kez çekilir, ayrıştırıcı istenildiği kadar
düzeltilir ("YAYIMLANAN BİR SAYININ ARŞİVİ DEPODA DURUR").

KÜNYE. `veri/ham/kunye_bulut.json`: her ham dosyanın adresi, durum kodu,
boyutu, sıkıştırılmamış baytların sha256'sı ve indirme anı. Ayrıca
`veri/ham/rapor.json`: kaynak başına yoklama sonucu (açık · kapalı · hata),
süre ve hata metni — "bulamadım" ile "yok" aynı şey değildir, kapalı çıkan
kaynağın sebebi adıyla durur.

BÜTÇE. İş akışının adımı 21 dakikada keser; betik kendi saatini 19 dakikada
kapatır ve kalan kaynakları "bütçe doldu" diye rapora yazar (sessiz kesilme
yok). Kaynaklar önem sırasıyla koşar: EVDS → TÜİK takvimi → BLS → FOMC →
BIS → ECB → Eurostat → Dünya Bankası → ABD Hazinesi → NY Fed ACM → BoE →
CNBC gilt → HMB.

EVDS anahtarı yalnız `key:` istek başlığına konur, hiçbir dosyaya ve kayda
yazılmaz.

`requests` değil `urllib`: yeniden deneme kaynağa özgü ve bilinçli yazılıyor.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

BURASI = Path(__file__).resolve().parent
HAM = Path(os.environ["MAKRO_HAM"]) if os.environ.get("MAKRO_HAM") else BURASI / "veri" / "ham"  # sınama için
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")
T0 = time.monotonic()
BUTCE_SN = 19 * 60
KUNYE: dict[str, dict] = {}
RAPOR: dict[str, dict] = {}
SIMDI = datetime.now(timezone.utc)


def kalan() -> float:
    return BUTCE_SN - (time.monotonic() - T0)


def al(url: str, sn: int = 40, deneme: int = 2, baslik: dict | None = None) -> tuple[int, bytes]:
    """(durum, gövde). 4xx yeniden denenmez; hata metni istisnayla yükselir."""
    son = None
    h = {"User-Agent": UA, "Accept": "*/*"}
    h.update(baslik or {})
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=sn) as r:
                return r.status, r.read()
        except HTTPError as e:
            son = e
            if e.code in (400, 401, 403, 404, 410):
                try:
                    govde = e.read()
                except Exception:  # noqa: BLE001
                    govde = b""
                return e.code, govde
        except (URLError, TimeoutError, OSError) as e:
            son = e
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"indirilemedi: {url[:160]} — {son!r}")


def yaz(yol: str, govde: bytes, url: str, durum: int, not_: str = "") -> None:
    """Ham yanıtı gzip'li (mtime 0) yazar; künyeye özü koyar. Anahtar URL'de yok."""
    p = HAM / yol
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as g:
            g.write(govde)
    KUNYE[yol] = {"url": url, "durum": durum, "bayt": len(govde),
                  "sha256": hashlib.sha256(govde).hexdigest(),
                  "an": datetime.now(timezone.utc).isoformat(timespec="seconds"), "not": not_}


def kaynak(ad: str):
    """Kaynak sarmalayıcı: süre, sonuç ve hata rapora; bütçe dolduysa koşmaz."""
    def sar(f):
        def ic():
            if kalan() < 30:
                RAPOR[ad] = {"durum": "bütçe doldu", "sure_sn": 0}
                print(f"── {ad}: bütçe doldu, koşmadı", flush=True)
                return
            t = time.monotonic()
            print(f"── {ad}", flush=True)
            try:
                ayrinti = f() or {}
                RAPOR[ad] = {"durum": "tamam", **ayrinti}
            except Exception as e:  # noqa: BLE001
                RAPOR[ad] = {"durum": "hata", "hata": f"{type(e).__name__}: {e}"[:600]}
                print(f"   ! {ad}: {e!r}"[:400], flush=True)
            RAPOR[ad]["sure_sn"] = round(time.monotonic() - t, 1)
        ic.__name__ = f.__name__
        return ic
    return sar


def sade(s: str) -> str:
    """Türkçe büyük harf tuzağına karşı: casefold → NFKD → birleştirici SİL → ı→i."""
    s = unicodedata.normalize("NFKD", str(s).casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("ı", "i").strip()


# ─────────────────────────────────────────────────────────────── EVDS
EVDS = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
EVDS_ARANAN = {
    # ad → (kategori/grup başlığında aranan sade dizgeler, hepsi değil BİRİ yeter)
    "pka": ("piyasa katilimcilari", "market participants"),
    "uyp": ("yatirim pozisyon", "investment position"),
    "kisa_vade_borc": ("kisa vadeli dis borc", "short term external debt", "kalan vade",
                       "remaining maturity"),
    "dis_ticaret_endeks": ("dis ticaret endeks", "foreign trade ind", "birim deger", "unit value",
                           "miktar endeks", "volume ind"),
}
EVDS_AZAMI_SERI = 900


def _evds(yol: str, sn: int = 60) -> tuple[int, bytes]:
    anahtar = os.environ.get("TTO_EVDS_KEY", "").strip()
    if not anahtar:
        raise RuntimeError("TTO_EVDS_KEY yok")
    return al(f"{EVDS}/{yol}", sn=sn, baslik={"key": anahtar, "Accept": "application/json"})


@kaynak("EVDS")
def evds() -> dict:
    d, kat = _evds("categories/type=json")
    yaz("evds/categories.json.gz", kat, f"{EVDS}/categories/type=json", d)
    if d != 200:
        raise RuntimeError(f"categories {d}")
    kategoriler = json.loads(kat)
    d, grp = _evds("datagroups/mode=0&type=json", sn=90)
    yaz("evds/datagroups.json.gz", grp, f"{EVDS}/datagroups/mode=0&type=json", d)
    gruplar = json.loads(grp)
    # Kategori başlığından (asıl yol) ve grup adından (ikinci yol) seçim.
    kat_sec: dict[str, set] = {k: set() for k in EVDS_ARANAN}
    for k in kategoriler:
        baslik = sade(" ".join(str(k.get(a) or "") for a in ("TOPIC_TITLE_TR", "TOPIC_TITLE_ENG")))
        for ad, kaliplar in EVDS_ARANAN.items():
            if any(x in baslik for x in kaliplar):
                try:
                    kat_sec[ad].add(int(float(k.get("CATEGORY_ID"))))
                except (TypeError, ValueError):
                    pass
    secim: dict[str, list[str]] = {k: [] for k in EVDS_ARANAN}
    for g in gruplar:
        kod = g.get("DATAGROUP_CODE")
        if not kod:
            continue
        try:
            cid = int(float(g.get("CATEGORY_ID")))
        except (TypeError, ValueError):
            cid = None
        ad_g = sade(" ".join(str(g.get(a) or "") for a in ("DATAGROUP_NAME", "DATAGROUP_NAME_ENG")))
        for ad, kaliplar in EVDS_ARANAN.items():
            if cid in kat_sec[ad] or any(x in ad_g for x in kaliplar):
                if kod not in secim[ad]:
                    secim[ad].append(kod)
    print("   seçilen gruplar: " + json.dumps(secim, ensure_ascii=False), flush=True)
    # serieList → seri kodları (yalnız katalogdan; elle kod yazılmaz).
    seriler: dict[str, list[dict]] = {}
    for ad, kodlar in secim.items():
        for kod in kodlar:
            if kalan() < 120:
                break
            d, sl = _evds(f"serieList/type=json&code={kod}", sn=40)
            yaz(f"evds/serielist/{kod}.json.gz", sl, f"{EVDS}/serieList/type=json&code={kod}", d, not_=ad)
            if d == 200:
                try:
                    seriler[kod] = [s for s in json.loads(sl) if s.get("SERIE_CODE")]
                except ValueError:
                    pass
    # Seri verisi: grup grup, demet en çok 6 kod; geçersiz kod demeti düşürürse tek tek.
    bitis = SIMDI.strftime("%d-%m-%Y")
    toplam = 0
    for kod, sl in seriler.items():
        kodlar = [s["SERIE_CODE"] for s in sl]
        for i in range(0, len(kodlar), 6):
            if toplam >= EVDS_AZAMI_SERI or kalan() < 300:
                break
            demet = kodlar[i:i + 6]
            yol = f"series={'-'.join(demet)}&startDate=01-01-1990&endDate={bitis}&type=json"
            try:
                d, gv = _evds(yol, sn=60)
            except RuntimeError as e:
                RAPOR.setdefault("EVDS_demet_hata", {"durum": "uyari", "liste": []})["liste"].append(f"{kod}:{i}: {e}"[:200])
                continue
            yaz(f"evds/seri/{kod}_{i // 6:03d}.json.gz", gv, f"{EVDS}/{yol}", d, not_=",".join(demet))
            toplam += len(demet)
    return {"secim": secim, "seri_listesi": {k: len(v) for k, v in seriler.items()}, "cekilen_seri": toplam}


# ───────────────────────────────────────────── TÜİK ulusal veri yayımlama takvimi
TUIK_UC = "https://www.tuik.gov.tr/Kurumsal/GetYillikHaberBulteniListesi?yil={yil}"


@kaynak("TÜİK takvim")
def tuik() -> dict:
    sonuc = {}
    for yil in range(SIMDI.year, 2008, -1):
        if kalan() < 60:
            break
        u = TUIK_UC.format(yil=yil)
        try:
            d, gv = al(u, sn=40, baslik={"Accept": "application/json, text/plain, */*",
                                          "Referer": "https://www.tuik.gov.tr/Kurumsal/Veri_Takvimi"})
        except RuntimeError as e:
            sonuc[yil] = f"hata: {e}"[:160]
            continue
        yaz(f"tuik/takvim_{yil}.json.gz", gv, u, d)
        try:
            j = json.loads(gv)
            sonuc[yil] = {"yayinda": len(j.get("yayindaOlanlarList") or []),
                          "bekleyen": len(j.get("yayindaOlmayanlarList") or [])}
        except ValueError:
            sonuc[yil] = f"json değil (durum {d}, {len(gv)} bayt)"
    return {"yillar": sonuc}


# ─────────────────────────────────────────────────────────── BLS arşiv dizinleri
@kaynak("BLS")
def bls() -> dict:
    sonuc = {}
    for ad in ("empsit", "cpi"):
        u = f"https://www.bls.gov/bls/news-release/{ad}.htm"
        d, gv = al(u, sn=40, baslik={"Accept": "text/html,application/xhtml+xml",
                                      "Accept-Language": "en-US,en;q=0.9"})
        yaz(f"bls/{ad}.htm.gz", gv, u, d)
        sonuc[ad] = {"durum": d, "bayt": len(gv),
                     "arsiv_baglanti": len(re.findall(rb"/news\.release/archives/" + ad.encode() + rb"_\d{8}", gv))}
    return sonuc


# ─────────────────────────────────────────────────────────── FOMC takvimleri
@kaynak("FOMC")
def fomc() -> dict:
    sonuc = {}
    adresler = [("fomccalendars", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm")]
    adresler += [(f"fomchistorical{y}", f"https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm")
                 for y in range(2008, 2021)]
    for ad, u in adresler:
        if kalan() < 60:
            break
        try:
            d, gv = al(u, sn=30)
        except RuntimeError as e:
            sonuc[ad] = f"hata: {e}"[:160]
            continue
        yaz(f"fomc/{ad}.htm.gz", gv, u, d)
        sonuc[ad] = d
    return sonuc


# ─────────────────────────────────────────────────────────────────── BIS
BIS = "https://stats.bis.org/api/v2/data/dataflow/BIS/{akim}/1.0/{anahtar}?format=csv&startPeriod={bas}"
BIS_ULKE = ["TR", "US", "XM", "JP", "GB", "CH", "AU", "CA", "NO", "SE", "BR", "MX", "ZA", "IN", "ID",
            "PL", "HU", "CL", "KR"]


@kaynak("BIS")
def bis() -> dict:
    sonuc = {}
    for akim, onek, bas in (("WS_EER", "M.R.B.", "1994-01"), ("WS_EER", "M.N.B.", "1994-01"),
                            ("WS_CBPOL", "M.", "1990-01")):
        u = BIS.format(akim=akim, anahtar=onek + "+".join(BIS_ULKE), bas=bas)
        d, gv = al(u, sn=90)
        ad = f"{akim}_{onek.replace('.', '')}"
        if d == 200 and gv.count(b"\n") > 50:
            yaz(f"bis/{ad}.csv.gz", gv, u, d)
            sonuc[ad] = {"durum": d, "satir": gv.count(b"\n")}
            continue
        # Çok ülkeli istek açılmadıysa ülke başına (depoda bulutta çalışan kalıp).
        sonuc[ad] = {"durum": d, "tekli": {}}
        for ulke in BIS_ULKE:
            if kalan() < 90:
                break
            u1 = BIS.format(akim=akim, anahtar=onek + ulke, bas=bas)
            try:
                d1, g1 = al(u1, sn=60)
            except RuntimeError as e:
                sonuc[ad]["tekli"][ulke] = f"hata {e}"[:120]
                continue
            yaz(f"bis/{ad}_{ulke}.csv.gz", g1, u1, d1)
            sonuc[ad]["tekli"][ulke] = d1
    return sonuc


# ─────────────────────────────────────────────────────────────────── ECB EXR
ECB_PARA = ["USD", "JPY", "GBP", "CHF", "CAD", "AUD", "SEK", "NOK", "BRL", "ZAR", "INR", "IDR", "MXN",
            "PLN", "HUF", "KRW", "TRY"]


@kaynak("ECB EXR")
def ecb() -> dict:
    sonuc = {}
    for kod in ECB_PARA:
        if kalan() < 60:
            break
        u = f"https://data-api.ecb.europa.eu/service/data/EXR/D.{kod}.EUR.SP00.A?format=csvdata&startPeriod=1999-01-01"
        try:
            d, gv = al(u, sn=90)
        except RuntimeError as e:
            sonuc[kod] = f"hata {e}"[:120]
            continue
        yaz(f"ecb/exr_{kod}.csv.gz", gv, u, d)
        sonuc[kod] = {"durum": d, "satir": gv.count(b"\n")}
    return sonuc


# ─────────────────────────────────────────────────────────────────── Eurostat
EUROSTAT = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{ds}?format=JSON&lang=EN&{q}"
EUROSTAT_GEO = ["DE", "FR", "IT", "ES", "PT", "EL", "IE", "NL", "BE", "AT", "FI", "EA20", "EU27_2020",
                "HU", "PL", "CZ", "RO"]


@kaynak("Eurostat")
def eurostat() -> dict:
    sonuc = {}
    geo = "&".join(f"geo={g}" for g in EUROSTAT_GEO)
    istekler = {
        "gov_10dd_edpt1": f"freq=A&unit=PC_GDP&sector=S13&na_item=B9&na_item=GD&{geo}",
        "gov_10q_ggdebt": f"freq=Q&unit=PC_GDP&sector=S13&na_item=GD&{geo}",
    }
    for ds, q in istekler.items():
        u = EUROSTAT.format(ds=ds, q=q)
        d, gv = al(u, sn=120)
        yaz(f"eurostat/{ds}.json.gz", gv, u, d)
        sonuc[ds] = {"durum": d, "bayt": len(gv)}
    return sonuc


# ─────────────────────────────────────────────────────────────── Dünya Bankası
WDI_ULKE = "TUR;USA;EMU;JPN;GBR;CHE;AUS;CAN;NOR;SWE;BRA;MEX;ZAF;IND;IDN;POL;HUN;CHL;KOR;ARG;RUS;CHN"


@kaynak("Dünya Bankası WDI")
def wdi() -> dict:
    sonuc = {}
    for gost in ("BN.CAB.XOKA.GD.ZS", "GC.DOD.TOTL.GD.ZS", "NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG"):
        u = (f"https://api.worldbank.org/v2/country/{WDI_ULKE}/indicator/{gost}"
             f"?format=json&per_page=20000&date=1980:{SIMDI.year}")
        d, gv = al(u, sn=90)
        yaz(f"wdi/{gost}.json.gz", gv, u, d)
        sonuc[gost] = {"durum": d, "bayt": len(gv)}
    return sonuc


# ─────────────────────────────────────────────────── ABD Hazinesi par getiri eğrisi
@kaynak("ABD Hazinesi")
def hazine() -> dict:
    sonuc = {}
    for yil in range(1990, SIMDI.year + 1):
        if kalan() < 60:
            break
        u = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
             f"daily-treasury-rates.csv/{yil}/all?type=daily_treasury_yield_curve"
             f"&field_tdr_date_value={yil}&page&_format=csv")
        try:
            d, gv = al(u, sn=60)
        except RuntimeError as e:
            sonuc[yil] = f"hata {e}"[:100]
            continue
        yaz(f"hazine/par_{yil}.csv.gz", gv, u, d)
        sonuc[yil] = d
    return sonuc


# ─────────────────────────────────────────────────────── NY Fed ACM vade primi
@kaynak("NY Fed ACM")
def acm() -> dict:
    u = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls"
    d, gv = al(u, sn=120)
    yaz("acm/ACMTermPremium.xls.gz", gv, u, d)
    return {"durum": d, "bayt": len(gv), "xls_imza": gv[:8].hex()}


# ─────────────────────────────────────────────── Bank of England IADB (gilt)
@kaynak("BoE IADB")
def boe() -> dict:
    sonuc = {}
    # IUDSNPY 5y · IUDMNPY 10y · IUDLNPY 20y nominal par getiri (günlük). 2022 dahil geniş pencere.
    u = ("https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes"
         "&Datefrom=01/Jan/2020&Dateto=now&SeriesCodes=IUDSNPY,IUDMNPY,IUDLNPY"
         "&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N")
    d, gv = al(u, sn=90, baslik={"Accept": "text/csv,text/plain,*/*"})
    yaz("boe/iadb_par.csv.gz", gv, u, d)
    sonuc["iadb"] = {"durum": d, "bayt": len(gv), "bas": gv[:200].decode("latin-1", "replace")}
    return sonuc


# ─────────────────────────────────────────────── CNBC (gilt ve dolar/sterlin)
@kaynak("CNBC gilt")
def cnbc() -> dict:
    sonuc = {}
    yarin = (SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    for sem in ("GB2Y-GB", "GB10Y-GB", "GB30Y-GB", "GBP=", "US1Y"):
        for bas in range(2010, SIMDI.year + 1, 5):
            if kalan() < 45:
                break
            son = f"{bas + 4}1231235959" if bas + 4 < SIMDI.year else f"{yarin}000000"
            u = (f"https://ts-api.cnbc.com/harmony/app/bars/{urllib.parse.quote(sem)}/1D/"
                 f"{bas}0101000000/{son}/adjusted/EST5EDT.json")
            try:
                d, gv = al(u, sn=30)
            except RuntimeError as e:
                sonuc[f"{sem}_{bas}"] = f"hata {e}"[:100]
                continue
            yaz(f"cnbc/{sem.replace('=', '').replace('-', '_')}_{bas}.json.gz", gv, u, d)
            sonuc[f"{sem}_{bas}"] = d
    return sonuc


# ─────────────────────────────────────────────────── HMB kredi notu sayfaları
@kaynak("HMB not")
def hmb() -> dict:
    sonuc = {}
    for ad, u in (("en", "https://en.hmb.gov.tr/credit-ratings"),
                  ("tr", "https://www.hmb.gov.tr/kredi-derecelendirme-notlari")):
        try:
            d, gv = al(u, sn=30)
        except RuntimeError as e:
            sonuc[ad] = f"hata {e}"[:120]
            continue
        yaz(f"hmb/kredi_notu_{ad}.htm.gz", gv, u, d)
        sonuc[ad] = {"durum": d, "bayt": len(gv)}
    return sonuc


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    for f in (evds, tuik, bls, fomc, bis, ecb, eurostat, wdi, hazine, acm, boe, cnbc, hmb):
        f()
    # Künye ve rapor var olanla BİRLEŞİR (ikinci koşu öncekini silmez).
    kp = HAM / "kunye_bulut.json"
    eski = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
    eski.update(KUNYE)
    kp.write_text(json.dumps(dict(sorted(eski.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rp = HAM / "rapor.json"
    rapor = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    rapor[SIMDI.strftime("%Y-%m-%dT%H%M")] = RAPOR
    rp.write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n══ ÖZET")
    for ad, r in RAPOR.items():
        print(f"  {ad:20s} {r.get('durum')}  {r.get('sure_sn', '')} sn  {str(r.get('hata', ''))[:160]}")
    print(f"  toplam {round(time.monotonic() - T0)} sn · {len(KUNYE)} ham dosya")
    return 0


if __name__ == "__main__":
    sys.exit(main())
