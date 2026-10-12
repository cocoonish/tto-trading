#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — dış kaynakların YOKLAMASI ve HAM arşivi.

Yalnız bulutta koşar (`arastirma-veri.yml`; bu oturumların koşucusu veri
kaynaklarına çıkamıyor). Depoda zaten duranlar YENİDEN İNDİRİLMEZ: 2026 rejimi
için bültenin piyasa fotoğrafı (51 enstrüman, kapanış saatleri düzeltilmiş),
makro dersinin donmuş girdileri (ABD Hazinesi 1990+, DXY/VIX 1971+, USD/TRY
TCMB 1990+, ödemeler dengesi enerji kalemleri 1996+, TÜFE enerji 2005+),
TCMB rezerv ve fonlama hatları. Bu betik yalnız EKSİK olanı çeker:

  CNBC     günlük bar (5 yıllık parçalar): vadeli emtia, paralar (New York
           17:00), getiriler, hisse endeksleri — TEK kaynak, TEK kapanış; uzun
           emsal penceresi (1990 Körfez) için 1985'ten yoklanır
  Yahoo    hisse ve fon kapanışları (yfinance; düzeltilmiş kapanış dahil):
           ABD sektör fonları, havayolları, kredi, gelişmekte olan piyasa
           fonları, BIST endeksleri ve petrole duyarlı BIST hisseleri,
           1985 öncesine uzanan ABD endeksleri
  EIA      Brent ve WTI spot fiyatı (günlük, 1986/1987+), ABD benzin ve
           motorin pompa fiyatı (haftalık)
  EVDS     TÜFE enerji ve akaryakıt kalemleri (aylık)
  Dünya Bankası Pink Sheet (aylık, 1960+; reel fiyat ve petrol yükü için)
  ABD Hazinesi 2026 nominal ve reel getiri eğrisi (depodaki arşiv 30.09'da bitiyor)
  NY Fed   petrol fiyatı dinamikleri raporu (talep/arz ayrıştırması) — yoklama
  Caldara–Iacoviello jeopolitik risk endeksi (günlük) — yoklama

İlke sırası CLAUDE.md'den: dış kaynak önce YOKLANIR, sonra kurulur; sembol
adları tahmin edilmez SORULUR (her araç için aday listesi, bar döndüren ilk
aday seçilir, hiçbiri tutmazsa durum kodlarıyla "kapalı" yazılır); adres
sabitlenmez sayfadan çözülür (Pink Sheet, NY Fed).

Yanıtlar OLDUĞU GİBİ (gzip'li ham bayt, mtime 0) `veri/ham/<kaynak>/` altına
yazılır; ayrıştırma yerelde (`hazirla.py`). Künye `veri/ham/kunye.json`
(adres, durum, bayt, sha256, an), rapor `veri/ham/rapor.json` (kaynak başına
sonuç, süre, hata — "bulamadım" ile "yok" aynı şey değildir).

BÜTÇE: iş akışı adımı 21 dakikada keser; betik kendi saatini 19 dakikada
kapatır ve kalan kaynakları "bütçe doldu" diye rapora yazar.

EVDS anahtarı yalnız `key:` istek başlığına konur, hiçbir dosyaya yazılmaz.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "ham"
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
    """(durum, gövde). 4xx yeniden denenmez; ağ hatası istisnayla yükselir."""
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
    p = HAM / yol
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as g:
            g.write(govde)
    KUNYE[yol] = {"url": url, "durum": durum, "bayt": len(govde),
                  "sha256": hashlib.sha256(govde).hexdigest(),
                  "an": datetime.now(timezone.utc).isoformat(timespec="seconds"), "not": not_}


def kaynak(ad: str):
    def sar(f):
        def ic():
            if kalan() < 30:
                RAPOR[ad] = {"durum": "bütçe doldu", "sure_sn": 0}
                print(f"── {ad}: bütçe doldu, koşmadı", flush=True)
                return
            t = time.monotonic()
            print(f"── {ad}", flush=True)
            try:
                RAPOR[ad] = {"durum": "tamam", **(f() or {})}
            except Exception as e:  # noqa: BLE001 — bir kaynağın düşmesi öbürlerini götürmesin
                RAPOR[ad] = {"durum": "hata", "hata": f"{type(e).__name__}: {e}"[:600]}
                print(f"   ! {ad}: {e!r}"[:400], flush=True)
            RAPOR[ad]["sure_sn"] = round(time.monotonic() - t, 1)
        ic.__name__ = f.__name__
        return ic
    return sar


# ─────────────────────────────────────────────────────────────── CNBC
# Araç → aday semboller (sırayla denenir). Uzun emsal listesi (UZUN) 1985'ten,
# öbürleri 2000'den istenir; kaynağın o yıllarda bar vermemesi ölçümün sonucudur.
CNBC = {
    # vadeli emtia (yakın vade)
    "brent": ["@LCO.1", "@BRN.1"], "wti": ["@CL.1"], "kalorifer": ["@HO.1"],
    "benzin": ["@RB.1"], "gazyagi_gasoil": ["@LGO.1", "@GO.1", "@QS.1"],
    "dogalgaz": ["@NG.1"], "ttf": ["@TFM.1", "@TTF.1", "@TG.1"],
    "altin": ["@GC.1"], "gumus": ["@SI.1"], "bakir": ["@HG.1"],
    "bugday": ["@W.1", "@ZW.1"], "misir": ["@C.1", "@ZC.1"],
    # paralar (CNBC kotasyonu, New York 17:00)
    "eur": ["EUR="], "jpy": ["JPY="], "gbp": ["GBP="], "chf": ["CHF="],
    "cad": ["CAD="], "aud": ["AUD="], "nzd": ["NZD="], "nok": ["NOK="],
    "sek": ["SEK="], "krw": ["KRW="], "zar": ["ZAR="], "mxn": ["MXN="],
    "brl": ["BRL="], "clp": ["CLP="], "cop": ["COP="], "try": ["TRY="],
    "inr": ["INR="], "idr": ["IDR="], "php": ["PHP="], "thb": ["THB="],
    "pln": ["PLN="], "huf": ["HUF="], "czk": ["CZK="], "ils": ["ILS="],
    "egp": ["EGP="], "cnh": ["CNH="], "dem": ["DEM="],
    # getiriler
    "us3m": ["US3M"], "us2y": ["US2Y"], "us5y": ["US5Y"], "us10y": ["US10Y"],
    "us30y": ["US30Y"], "de2y": ["DE2Y-DE"], "de10y": ["DE10Y-DE"],
    "gb2y": ["GB2Y-GB"], "gb10y": ["GB10Y-GB"], "jp2y": ["JP2Y-JP"],
    "jp10y": ["JP10Y-JP"], "it10y": ["IT10Y-IT"],
    "tr2y": ["TR2Y-TR", "TR2YT=RR", "TR2Y"], "tr10y": ["TR10Y-TR", "TR10YT=RR", "TR10Y"],
    # hisse endeksleri ve oynaklık
    "spx": [".SPX"], "ndx": [".NDX"], "rut": [".RUT"], "vix": [".VIX"],
    "dxy": [".DXY"], "sx5e": [".STOXX50E", ".SX5E"], "dax": [".GDAXI"],
    "ftse": [".FTSE"], "cac": [".FCHI"], "n225": [".N225"], "hsi": [".HSI"],
    "kospi": [".KS11"], "sensex": [".BSESN"], "shcomp": [".SSEC"],
    "bist100": [".XU100", "XU100"],
}
UZUN = {"brent", "wti", "altin", "jpy", "dem", "gbp", "chf", "try", "us2y", "us10y",
        "spx", "vix", "dxy", "n225", "dax", "ftse"}
CNBC_ILK_UZUN = 1985
CNBC_ILK = 2000


def _cnbc_url(sem: str, bas: str, son: str) -> str:
    return (f"https://ts-api.cnbc.com/harmony/app/bars/{urllib.parse.quote(sem)}/1D/"
            f"{bas}000000/{son}/adjusted/EST5EDT.json")


def _bar_sayisi(gv: bytes) -> int:
    try:
        j = json.loads(gv)
    except Exception:  # noqa: BLE001
        return 0
    return len(((j.get("barData") or {}).get("priceBars")) or [])


def _dosya_adi(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


@kaynak("CNBC")
def cnbc() -> dict:
    sonuc = {}
    yarin = (SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    iki_yil = (SIMDI - timedelta(days=730)).strftime("%Y%m%d")
    for arac, adaylar in CNBC.items():
        if kalan() < 300:
            sonuc[arac] = {"durum": "bütçe doldu"}
            continue
        yoklama, secilen = {}, None
        for sem in adaylar:
            try:
                d, gv = al(_cnbc_url(sem, iki_yil, f"{yarin}000000"), sn=20, deneme=1)
            except RuntimeError as e:
                yoklama[sem] = f"hata {e}"[:80]
                continue
            n = _bar_sayisi(gv) if d == 200 else 0
            yoklama[sem] = {"durum": d, "bar": n}
            if n > 20:
                secilen = sem
                break
            time.sleep(0.3)
        if not secilen:
            sonuc[arac] = {"durum": "kapalı", "yoklama": yoklama}
            print(f"   {arac}: kapalı {yoklama}", flush=True)
            continue
        ilk = CNBC_ILK_UZUN if arac in UZUN else CNBC_ILK
        parcalar = {}
        for bas in range(ilk, SIMDI.year + 1, 5):
            if kalan() < 240:
                parcalar[bas] = "bütçe doldu"
                break
            son = f"{bas + 4}1231235959" if bas + 4 < SIMDI.year else f"{yarin}000000"
            u = _cnbc_url(secilen, f"{bas}0101", son)
            try:
                d, gv = al(u, sn=40)
            except RuntimeError as e:
                parcalar[bas] = f"hata {e}"[:80]
                continue
            n = _bar_sayisi(gv) if d == 200 else 0
            if n:
                yaz(f"cnbc/{arac}__{_dosya_adi(secilen)}_{bas}.json.gz", gv, u, d,
                    not_=f"{arac} · {secilen}")
            parcalar[bas] = {"durum": d, "bar": n}
            time.sleep(0.25)
        sonuc[arac] = {"durum": "tamam", "sembol": secilen, "yoklama": yoklama, "parcalar": parcalar}
        print(f"   {arac}: {secilen} · " + ", ".join(
            f"{k}:{v.get('bar') if isinstance(v, dict) else v}" for k, v in parcalar.items()), flush=True)
    return sonuc


# ─────────────────────────────────────────────────────────────── Yahoo
# Hisse ve fon kapanışları. Döviz BİLEREK yok: Yahoo'nun günlük döviz barının
# kapanışı günün BAŞIDIR (ölçüldü, 02.10.2026); paralar CNBC'den.
YAHOO = [
    # ABD endeksleri (1990 emsali için uzun) ve ima edilen oynaklık: ^OVX ham
    # petrol (USO opsiyonları), ^GVZ altın, ^MOVE ABD tahvili — piyasanın bir
    # aylık hareketi ne kadar olası saydığının tek doğrudan ölçüsü
    "^GSPC", "^IXIC", "^DJI", "^RUT", "^VIX", "^TNX", "^IRX", "^FVX", "^TYX",
    "^OVX", "^GVZ", "^MOVE", "BZ=F", "CL=F",
    # ABD sektör fonları ve temalar
    "XLE", "XOP", "XLB", "XLI", "XLY", "XLP", "XLU", "XLF", "XLK", "XLV", "XLRE",
    "JETS", "ITA", "XAR", "IYT",
    # havayolları ve petrol şirketleri (uzun tarihçe)
    "DAL", "UAL", "LUV", "XOM", "CVX",
    # kredi, tahvil ve enflasyon korumalı tahvil fonları
    "HYG", "JNK", "LQD", "TLT", "IEF", "SHY", "TIP",
    # gelişmekte olan ve ülke fonları
    "EEM", "EMB", "TUR", "EWZ", "EWW", "INDA", "EWY", "EWJ", "FXI", "EZU", "EWG", "EWU",
    "KSA", "UAE", "QAT", "EWT",
    # BIST endeksleri ve petrole duyarlı hisseler
    "XU100.IS", "XU030.IS", "XBANK.IS", "XUSIN.IS", "XULAS.IS", "XKMYA.IS", "XUTEK.IS",
    "XHOLD.IS", "XUHIZ.IS", "XUMAL.IS",
    "TUPRS.IS", "THYAO.IS", "PGSUS.IS", "PETKM.IS", "AYGAZ.IS", "FROTO.IS", "TOASO.IS",
    "BIMAS.IS", "EREGL.IS", "SISE.IS", "AKBNK.IS", "GARAN.IS", "KCHOL.IS", "ASELS.IS",
    "TAVHL.IS", "CLEBI.IS", "ENJSA.IS", "AKSEN.IS", "ULKER.IS", "MGROS.IS",
]


@kaynak("Yahoo")
def yahoo() -> dict:
    try:
        import yfinance as yf
    except ImportError as e:
        raise RuntimeError(f"yfinance yok: {e!r}") from e
    sonuc = {}
    for kod in YAHOO:
        if kalan() < 200:
            sonuc[kod] = "bütçe doldu"
            continue
        h = None
        for deneme in range(3):
            try:
                h = yf.Ticker(kod).history(period="max", interval="1d", auto_adjust=False, actions=True)
                break
            except Exception as e:  # noqa: BLE001 — 429 bir ölçüm değildir: bekle, yeniden dene
                sonuc[kod] = f"hata {type(e).__name__}: {e}"[:120]
                time.sleep(5 * (deneme + 1))
        if h is None or h.empty:
            sonuc.setdefault(kod, "boş")
            print(f"   {kod}: {sonuc[kod]}", flush=True)
            time.sleep(1.0)
            continue
        h = h.copy()
        # Tarih: borsanın yerel işlem günü (saat dilimi düşürülür, gün korunur).
        h.index = [t.strftime("%Y-%m-%d") for t in h.index]
        kolon = [c for c in ("Open", "High", "Low", "Close", "Adj Close", "Volume",
                             "Dividends", "Stock Splits") if c in h.columns]
        metin = h[kolon].to_csv(index_label="tarih", float_format="%.6f", lineterminator="\n").encode("utf-8")
        yaz(f"yahoo/{_dosya_adi(kod)}.csv.gz", metin, f"yfinance:{kod}:period=max", 200, not_=kod)
        sonuc[kod] = {"satir": int(len(h)), "ilk": h.index[0], "son": h.index[-1]}
        print(f"   {kod}: {len(h)} satır {h.index[0]}→{h.index[-1]}", flush=True)
        time.sleep(0.8)
    return sonuc


# ─────────────────────────────────────────────────────────────── EIA
EIA = {
    "brent_spot_gunluk": "https://www.eia.gov/dnav/pet/hist_xls/RBRTEd.xls",
    "wti_spot_gunluk": "https://www.eia.gov/dnav/pet/hist_xls/RWTCd.xls",
    "abd_benzin_pompa_haftalik": "https://www.eia.gov/dnav/pet/hist_xls/EMM_EPMR_PTE_NUS_DPGw.xls",
    "abd_motorin_pompa_haftalik": "https://www.eia.gov/dnav/pet/hist_xls/EMD_EPD2D_PTE_NUS_DPGw.xls",
}


@kaynak("EIA")
def eia() -> dict:
    sonuc = {}
    for ad, u in EIA.items():
        try:
            d, gv = al(u, sn=60)
        except RuntimeError as e:
            sonuc[ad] = f"hata {e}"[:120]
            continue
        if d == 200 and len(gv) > 1000:
            yaz(f"eia/{ad}.xls.gz", gv, u, d)
        sonuc[ad] = {"durum": d, "bayt": len(gv)}
        print(f"   {ad}: {d} · {len(gv)} bayt", flush=True)
    return sonuc


# ─────────────────────────────────────────────────────────────── EVDS
EVDS = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
EVDS_SERI = {
    "enerji": "TP.FE25.OKTG09", "tufe": "TP.TUKFIY2025.GENEL",
    "akaryakit": "TP.TUKFIY2025.0722", "motorin": "TP.TUKFIY2025.07221",
    "benzin": "TP.TUKFIY2025.07222", "otogaz": "TP.TUKFIY2025.07223",
    "elektrik": "TP.TUKFIY2025.04510", "dogalgaz": "TP.TUKFIY2025.04521",
    "tupgaz": "TP.TUKFIY2025.04522", "yolcu_tasima": "TP.TUKFIY2025.073",
    "ulastirma": "TP.TUKFIY2025.07",
}


def _evds(yol: str, sn: int = 60) -> tuple[int, bytes]:
    anahtar = os.environ.get("TTO_EVDS_KEY", "").strip()
    if not anahtar:
        raise RuntimeError("TTO_EVDS_KEY yok")
    return al(f"{EVDS}/{yol}", sn=sn, baslik={"key": anahtar, "Accept": "application/json"})


@kaynak("EVDS")
def evds() -> dict:
    sonuc = {}
    bitis = SIMDI.strftime("%d-%m-%Y")
    kodlar = list(EVDS_SERI.values())
    # Demet geçersiz bir kod yüzünden düşerse kodlar tek tek istenir.
    for i in range(0, len(kodlar), 6):
        demet = kodlar[i:i + 6]
        yol = f"series={'-'.join(demet)}&startDate=01-01-2004&endDate={bitis}&type=json"
        try:
            d, gv = _evds(yol)
        except RuntimeError as e:
            d, gv = 0, str(e).encode()
        if d == 200:
            yaz(f"evds/tufe_{i // 6:02d}.json.gz", gv, f"{EVDS}/{yol}", d, not_=",".join(demet))
            sonuc[",".join(demet)] = d
            continue
        for kod in demet:
            yol = f"series={kod}&startDate=01-01-2004&endDate={bitis}&type=json"
            try:
                d1, g1 = _evds(yol)
            except RuntimeError as e:
                sonuc[kod] = f"hata {e}"[:120]
                continue
            if d1 == 200:
                yaz(f"evds/{_dosya_adi(kod)}.json.gz", g1, f"{EVDS}/{yol}", d1, not_=kod)
            sonuc[kod] = d1
    # Seri adları katalogdan (kod tahmin edilmez, adı sorulur).
    for grup in ("bie_tukfiy2025", "bie_fe25"):
        try:
            d, sl = _evds(f"serieList/type=json&code={grup}", sn=40)
            if d == 200:
                yaz(f"evds/serielist_{grup}.json.gz", sl, f"{EVDS}/serieList/type=json&code={grup}", d)
            sonuc[f"serieList:{grup}"] = d
        except RuntimeError as e:
            sonuc[f"serieList:{grup}"] = f"hata {e}"[:120]
    return sonuc


# ─────────────────────────────────────────────────────────────── Dünya Bankası
CMO_SAYFA = "https://www.worldbank.org/en/research/commodity-markets"
CMO_KALIP = re.compile(r"https://thedocs\.worldbank\.org/[^\"'\s>]*CMO-Historical-Data-Monthly\.xlsx")
CMO_YEDEK = [
    "https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/related/CMO-Historical-Data-Monthly.xlsx",
]


@kaynak("Pink Sheet")
def pink() -> dict:
    adresler = []
    try:
        d, sayfa = al(CMO_SAYFA, sn=40)
        if d == 200:
            adresler += list(dict.fromkeys(CMO_KALIP.findall(sayfa.decode("utf-8", "ignore"))))
    except RuntimeError as e:
        print(f"   CMO sayfası okunamadı: {e}", flush=True)
    adresler += CMO_YEDEK
    for u in adresler:
        try:
            d, gv = al(u, sn=90)
        except RuntimeError as e:
            print(f"   {u[-60:]}: {e}", flush=True)
            continue
        if d == 200 and len(gv) > 100_000:
            yaz("worldbank/CMO-Historical-Data-Monthly.xlsx.gz", gv, u, d)
            return {"adres": u, "bayt": len(gv), "sayfadan": u not in CMO_YEDEK}
    raise RuntimeError("Pink Sheet hiçbir adresten alınamadı")


# ─────────────────────────────────────────────────────────────── ABD Hazinesi
@kaynak("ABD Hazinesi")
def hazine() -> dict:
    sonuc = {}
    for tur in ("daily_treasury_yield_curve", "daily_treasury_real_yield_curve"):
        for yil in (2025, 2026):
            u = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                 f"daily-treasury-rates.csv/{yil}/all?type={tur}&field_tdr_date_value={yil}&page&_format=csv")
            try:
                d, gv = al(u, sn=40)
            except RuntimeError as e:
                sonuc[f"{tur}:{yil}"] = f"hata {e}"[:120]
                continue
            if d == 200:
                yaz(f"hazine/{tur}_{yil}.csv.gz", gv, u, d)
            sonuc[f"{tur}:{yil}"] = {"durum": d, "bayt": len(gv)}
    return sonuc


# ─────────────────────────────────────────────────────────────── NY Fed
NYF_SAYFA = "https://www.newyorkfed.org/research/policy/oil_price_dynamics_report"


@kaynak("NY Fed petrol")
def nyfed() -> dict:
    d, sayfa = al(NYF_SAYFA, sn=40)
    yaz("nyfed/sayfa.html.gz", sayfa, NYF_SAYFA, d)
    metin = sayfa.decode("utf-8", "ignore")
    baglar = sorted(set(re.findall(r"href=\"([^\"]+\.(?:xlsx|xls|csv))\"", metin, flags=re.I)))
    alinan = {}
    for b in baglar[:6]:
        u = urllib.parse.urljoin(NYF_SAYFA, b)
        try:
            d1, gv = al(u, sn=60)
        except RuntimeError as e:
            alinan[u] = f"hata {e}"[:100]
            continue
        if d1 == 200:
            yaz(f"nyfed/{_dosya_adi(Path(b).name)}.gz", gv, u, d1)
        alinan[u] = {"durum": d1, "bayt": len(gv)}
    return {"sayfa": d, "baglar": baglar[:20], "alinan": alinan}


# ─────────────────────────────────────────────────────────────── GPR
GPR = ["https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls",
       "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"]


@kaynak("GPR")
def gpr() -> dict:
    sonuc = {}
    for u in GPR:
        try:
            d, gv = al(u, sn=60)
        except RuntimeError as e:
            sonuc[u] = f"hata {e}"[:100]
            continue
        if d == 200 and len(gv) > 1000:
            yaz(f"gpr/{_dosya_adi(Path(u).name)}.gz", gv, u, d)
        sonuc[u] = {"durum": d, "bayt": len(gv)}
    return sonuc


def kaydet(ek: str) -> None:
    """Künye ve rapor betiğe özgü dosyaya yazılır (iki arşiv betiği ayrı koşar,
    aynı dosyayı paylaşmaz); var olan kayıtlar korunur."""
    kp = HAM / f"kunye_{ek}.json"
    eski = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
    eski.update(KUNYE)
    kp.write_text(json.dumps(dict(sorted(eski.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rp = HAM / f"rapor_{ek}.json"
    rapor = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    rapor[SIMDI.strftime("%Y-%m-%dT%H:%M:%SZ")] = RAPOR
    rp.write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── bitti {round(time.monotonic() - T0, 1)} sn · {len(KUNYE)} ham dosya")
    for ad, r in RAPOR.items():
        print(f"   {ad}: {r.get('durum')} ({r.get('sure_sn')} sn){' — ' + r['hata'] if r.get('hata') else ''}")


def main() -> int:
    """Bu betik yalnız CNBC'yi çeker (en uzun kaynak); öbürleri `arsiv_brent_ek.py`."""
    HAM.mkdir(parents=True, exist_ok=True)
    cnbc()
    kaydet("cnbc")
    return 0 if KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
