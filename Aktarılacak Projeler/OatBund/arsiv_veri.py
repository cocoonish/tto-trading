#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND ANALİZİ — GİRDİ ARŞİVİ (bulutta koşar, `veri/` altına yazar).

Analizin sayıları SABİTTİR (karar 08.09.2026); yayımlanan her sayının arşivi
depoda durur ve ölçüm ağa çıkmadan yeniden üretilir. Bu betik yalnız
`arastirma-veri.yml` ile bulutta koşar (bu oturumların koşucusu kaynaklara
çıkamıyor) ve yalnız ÖLÇÜLEREK açık bulunmuş uçları kullanır — yoklama
koşuları keşif #27–#31 (01.10.2026):

  Bundesbank  BBSIS, Bund getirileri GÜNLÜK — kupon ödemeli (par) getiri
              (`ZAR`) ve sıfır kuponlu Svensson getirisi (`ZST`), 2 ve 10 yıl
  ABD Hazinesi günlük getiri eğrisi CSV'si, yıl başına bir istek
  ECB        EXR (EUR/USD referans kuru, 14:15 CET), IRS (Maastricht uzun
              vadeli faiz, AYLIK, bütün AB ülkeleri), YC (euro alanı AAA eğrisi)
  Eurostat   irt_lt_mcby_m (aynı aylık ölçüt, ECB'yle çapraz sınama için) —
              GÜNLÜK küme `irt_lt_mcby_d` yayımdan KALDIRILMIŞ (404, ölçüldü)
  Yahoo      EUR/USD=X günlük kapanış (yfinance)
  CNBC       gösterge getirileri (FR/DE/IT/ES/BE/NL/AT/PT/GR 10y; FR/DE/IT/ES 2y;
              FR/DE 5y ve 30y; ABD 2y/10y) ve EUR/USD — günlük bar ucu, 2000'den;
              Banque de France'ın sabit vadeli TEC10'u anahtarsız sorguda boş
              (Webstat kayıtları anahtar istiyor), Stooq tarayıcı sınaması istiyor

KAPSAM ÖLÇÜLÜR, VARSAYILMAZ ("veri geldi" ile "veri TAM geldi" aynı şey
değildir): her serinin ilk ve son günü, gözlem sayısı ve hafta içi doluluğu
künyeye yazılır; beklenen kapsamı tutturmayan seri ADIYLA uyarı alır.

Dosyalar deterministik yazılır (sabit ondalık, gzip zaman damgası 0) ve her
birinin özü (sha256, sıkıştırılmamış metin) künyede durur; `olcum.py` okurken
özü yeniden hesaplar.

`requests` değil `urllib`: ortak emniyet `requests`i üç denemeli sarar; burada
yeniden deneme bilinçli ve kaynağa özgü yazılıyor.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0 Safari/537.36"), "Accept": "*/*"}
BASLANGIC = "1999-01-01"
UYARILAR: list[str] = []
KAYNAKLAR: dict[str, dict] = {}


def al(url: str, sn: int = 40, deneme: int = 3) -> bytes:
    son = None
    for i in range(deneme):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=sn) as r:
                return r.read()
        except HTTPError as e:
            son = e
            if e.code in (400, 401, 403, 404):
                break
        except (URLError, TimeoutError, OSError) as e:
            son = e
        time.sleep(2 * (i + 1))
    raise RuntimeError(f"indirilemedi: {url[:140]} — {son!r}")


def gz_yaz(df: pd.DataFrame, ad: str, kaynak: str, aciklama: str, beklenen_ilk: str | None = None,
           gunluk: bool = True) -> None:
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    metin = df.to_csv(float_format="%.6f", lineterminator="\n", index_label="tarih")
    ham = metin.encode("utf-8")
    tampon = io.BytesIO()
    with gzip.GzipFile(fileobj=tampon, mode="wb", mtime=0) as g:
        g.write(ham)
    (VERI / ad).write_bytes(tampon.getvalue())
    kapsam = {}
    for k in df.columns:
        s = df[k].dropna()
        if s.empty:
            UYARILAR.append(f"{ad}:{k} BOŞ")
            kapsam[k] = {"n": 0}
            continue
        k_ = {"n": int(len(s)), "ilk": str(s.index.min().date()), "son": str(s.index.max().date())}
        if gunluk:
            is_gunu = pd.bdate_range(s.index.min(), s.index.max())
            k_["is_gunu_dolulugu"] = round(float(len(s.index.intersection(is_gunu)) / max(1, len(is_gunu))), 4)
        kapsam[k] = k_
        if beklenen_ilk and k_["ilk"] > beklenen_ilk:
            UYARILAR.append(f"{ad}:{k} beklenenden geç başlıyor ({k_['ilk']} > {beklenen_ilk})")
    KAYNAKLAR[ad] = {"sha256": hashlib.sha256(ham).hexdigest(), "satir": int(len(df)),
                     "kaynak": kaynak, "aciklama": aciklama, "kapsam": kapsam}
    print(f"  ✓ {ad}: {len(df)} satır · " + ", ".join(
        f"{k} {v.get('ilk')}→{v.get('son')} n={v.get('n')}" for k, v in kapsam.items()), flush=True)


# ── Bundesbank ────────────────────────────────────────────────────────────
BBK = "https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
BBK_SERI = {
    "de10_par": "D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A",
    "de2_par": "D.I.ZAR.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A",
    "de30_par": "D.I.ZAR.ZI.EUR.S1311.B.A604.R30XX.R.A.A._Z._Z.A",
    "de10_sifir": "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A",
}


def bundesbank() -> None:
    sutun = {}
    for ad, anahtar in BBK_SERI.items():
        try:
            m = al(f"{BBK}{anahtar}?format=sdmx_csv&startPeriod={BASLANGIC}").decode("utf-8-sig")
        except RuntimeError as e:
            UYARILAR.append(f"bundesbank {ad}: {e}")
            continue
        satir = [s.split(";") for s in m.splitlines()]
        bas = satir[0]
        it, iv = bas.index("TIME_PERIOD"), bas.index("OBS_VALUE")
        d = {}
        for p in satir[1:]:
            if len(p) > iv and p[iv] not in ("", "."):
                d[pd.Timestamp(p[it])] = float(p[iv])
        sutun[ad] = pd.Series(d)
    if sutun:
        gz_yaz(pd.DataFrame(sutun), "bund_gunluk.csv.gz", "Deutsche Bundesbank, BBSIS",
               "Bund getirileri, %; _par = kupon ödemeli (yıllık kupon) getiri, _sifir = sıfır kuponlu Svensson; kalan vade 2/10/30 yıl",
               beklenen_ilk="1999-02-01")


# ── ABD Hazinesi ──────────────────────────────────────────────────────────
def hazine() -> None:
    parca = []
    for yil in range(1999, datetime.now(timezone.utc).year + 1):
        u = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
             f"daily-treasury-rates.csv/{yil}/all?type=daily_treasury_yield_curve"
             f"&field_tdr_date_value={yil}&page&_format=csv")
        try:
            df = pd.read_csv(io.BytesIO(al(u)))
        except Exception as e:  # noqa: BLE001
            UYARILAR.append(f"ABD Hazinesi {yil}: {e!r}")
            continue
        df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        parca.append(df.set_index("Date")[["2 Yr", "10 Yr"]].rename(columns={"2 Yr": "us2", "10 Yr": "us10"}))
    if parca:
        gz_yaz(pd.concat(parca), "abd_gunluk.csv.gz", "ABD Hazinesi, Daily Treasury Par Yield Curve",
               "ABD Hazine par getirisi, %; 2 ve 10 yıl", beklenen_ilk="1999-01-05")


# ── ECB ───────────────────────────────────────────────────────────────────
ECB = "https://data-api.ecb.europa.eu/service/data/"


def ecb_csv(akis_anahtar: str) -> pd.DataFrame:
    m = al(f"{ECB}{akis_anahtar}?format=csvdata&startPeriod={BASLANGIC[:7]}", sn=90)
    return pd.read_csv(io.BytesIO(m), usecols=["KEY", "REF_AREA", "TIME_PERIOD", "OBS_VALUE"]
                       if b"REF_AREA" in m[:2000] else ["KEY", "TIME_PERIOD", "OBS_VALUE"])


def ecb() -> None:
    try:
        df = ecb_csv("EXR/D.USD.EUR.SP00.A")
        s = df.assign(t=pd.to_datetime(df["TIME_PERIOD"])).set_index("t")["OBS_VALUE"]
        gz_yaz(pd.DataFrame({"eurusd_ecb": s}), "eurusd_ecb.csv.gz", "ECB, EXR.D.USD.EUR.SP00.A",
               "EUR/USD referans kuru (14:15 CET)", beklenen_ilk="1999-01-05")
    except Exception as e:  # noqa: BLE001
        UYARILAR.append(f"ECB EXR: {e!r}")
    try:
        df = ecb_csv("IRS/M..L.L40.CI.0000.EUR.N.Z")
        df["t"] = pd.PeriodIndex(df["TIME_PERIOD"], freq="M").to_timestamp(how="end").normalize()
        tablo = df.pivot_table(index="t", columns="REF_AREA", values="OBS_VALUE", aggfunc="last")
        gz_yaz(tablo, "irs_aylik.csv.gz", "ECB, IRS.M.<ülke>.L.L40.CI.0000.EUR.N.Z",
               "Maastricht ölçütü uzun vadeli (10 yıl) devlet tahvili getirisi, aylık ortalama, %; tarih ayın son günü",
               gunluk=False)
    except Exception as e:  # noqa: BLE001
        UYARILAR.append(f"ECB IRS: {e!r}")
    try:
        parca = {}
        for v in ("SR_2Y", "SR_10Y"):
            for egri in ("G_N_A", "G_N_C"):
                df = ecb_csv(f"YC/B.U2.EUR.4F.{egri}.SV_C_YM.{v}")
                parca[f"{'aaa' if egri == 'G_N_A' else 'tum'}_{v[3:].lower()}"] = (
                    df.assign(t=pd.to_datetime(df["TIME_PERIOD"])).set_index("t")["OBS_VALUE"])
        gz_yaz(pd.DataFrame(parca), "ecb_egri.csv.gz", "ECB, YC.B.U2.EUR.4F.<G_N_A|G_N_C>.SV_C_YM.SR_<2Y|10Y>",
               "Euro alanı devlet tahvili spot (sıfır kuponlu) getirisi, %; aaa = AAA notlu ihraççılar, tum = bütün ihraççılar",
               beklenen_ilk="2004-09-07")
    except Exception as e:  # noqa: BLE001
        UYARILAR.append(f"ECB YC: {e!r}")


# ── Eurostat ──────────────────────────────────────────────────────────────
def eurostat() -> None:
    try:
        m = al("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/irt_lt_mcby_m"
               "?format=JSON&lang=EN&sinceTimePeriod=1999-01", sn=90)
        js = json.loads(m)
        ids, size = js["id"], js["size"]
        dim = js["dimension"]
        konum = {d: {v: k for k, v in dim[d]["category"]["index"].items()} for d in ids}
        degerler = js["value"]
        kayit = {}
        carpan = [1] * len(size)
        for i in range(len(size) - 2, -1, -1):
            carpan[i] = carpan[i + 1] * size[i + 1]
        for k, v in degerler.items():
            k = int(k)
            ind = []
            for i in range(len(size)):
                ind.append(k // carpan[i])
                k %= carpan[i]
            boyut = {ids[i]: konum[ids[i]][ind[i]] for i in range(len(size))}
            t = pd.Period(boyut["time"].replace("M", "-"), freq="M").to_timestamp(how="end").normalize()
            kayit.setdefault(boyut["geo"], {})[t] = float(v)
        gz_yaz(pd.DataFrame(kayit), "eurostat_aylik.csv.gz", "Eurostat, irt_lt_mcby_m",
               "AB yakınsama ölçütü uzun vadeli faiz, aylık, %; tarih ayın son günü", gunluk=False)
    except Exception as e:  # noqa: BLE001
        UYARILAR.append(f"Eurostat aylık: {e!r}")


# ── Yahoo ─────────────────────────────────────────────────────────────────
def yahoo() -> None:
    try:
        import yfinance as yf
    except ImportError as e:
        UYARILAR.append(f"yfinance yok: {e!r}")
        return
    parca = {}
    # Ortak risk iştahını ayırmak için kontroller (VIX, hisse endeksleri), Avrupa
    # içi güvenli liman (EUR/CHF), bölgesel ayrışma (CAC 40 − DAX) ve egemen–banka
    # bağı (Fransız bankaları). Vadeli emtia BİLEREK yok: ön vade devri seviyeyi
    # bozar (CLAUDE.md — geriye ölçeklenmiş seriden aritmetik kurulmaz).
    for kod, ad in (("EURUSD=X", "eurusd"), ("DX-Y.NYB", "dxy"), ("EURCHF=X", "eurchf"),
                    ("EURGBP=X", "eurgbp"), ("EURJPY=X", "eurjpy"), ("^VIX", "vix"),
                    ("^STOXX50E", "sx5e"), ("^FCHI", "cac"), ("^GDAXI", "dax"),
                    ("BNP.PA", "bnp"), ("GLE.PA", "socgen"), ("ACA.PA", "cagri")):
        h = yf.Ticker(kod).history(period="max", interval="1d", auto_adjust=False)
        if h.empty:
            UYARILAR.append(f"Yahoo {kod} boş")
            continue
        s = h["Close"].copy()
        s.index = pd.DatetimeIndex([pd.Timestamp(t.date()) for t in s.index])
        parca[ad] = s
    if parca:
        gz_yaz(pd.DataFrame(parca), "yahoo_gunluk.csv.gz", "Yahoo Finance (yfinance), günlük kapanış",
               "Kapanış (tarih: Yahoo işlem günü; döviz barı ölçüldü: Yahoo D ≈ CNBC D−1)", beklenen_ilk="2004-01-01")


# ── CNBC ──────────────────────────────────────────────────────────────────
# Yoklama (keşif #31, 01.10.2026) ölçtü: tarih aralıklı bar ucu 2000'den bugüne
# GÜNLÜK bar veriyor (FR10Y 7.248, DE10Y 7.387 bar tek istekte). Hafta içi barı
# AVRUPA kapanışıdır (ECB AAA eğrisiyle aynı gün korelasyonu 0,87–0,90, ertesi
# günle 0,08–0,10); hafta sonu barları cumanın KOPYASI DEĞİL — 564 cuma–cumartesi
# çiftinin 550'sinde cumartesi farklı, yani cuma New York'taki son kotasyon.
# Arşiv kaynağın döndürdüğünü OLDUĞU GİBİ saklar; hafta sonu ve tatil ayıklaması
# ölçüm katmanında, kuralıyla ve sayımıyla yapılır.
# Uzun aralık tek istekte kırpılabilir (CLAUDE.md — EVDS 2000–2026'yı sessizce
# kırpıyordu): seri beş yıllık PARÇALARLA istenir, parçaların örtüşmesi yok.
CNBC_SEM = ["FR10Y-FR", "DE10Y-DE", "IT10Y-IT", "ES10Y-ES", "BE10Y-BE", "NL10Y-NL",
            "AT10Y-AT", "PT10Y-PT", "GR10Y-GR", "FR2Y-FR", "DE2Y-DE", "IT2Y-IT", "ES2Y-ES",
            "FR5Y-FR", "DE5Y-DE", "FR30Y-FR", "DE30Y-DE", "US2Y", "US10Y", "EUR="]


def _cnbc_bar(govde: bytes) -> pd.Series:
    js = json.loads(govde)
    ps = js.get("barData", {}).get("priceBars", []) or []
    d = {}
    for p in ps:
        try:
            d[pd.Timestamp(p["tradeTime"][:8])] = float(p["close"])
        except (KeyError, ValueError, TypeError):
            continue
    return pd.Series(d, dtype=float)


def _ad(sem: str) -> str:
    return {"EUR=": "eurusd"}.get(sem, sem.split("-")[0].lower())


def cnbc() -> None:
    gunluk, aylik = {}, {}
    bugun = datetime.now(timezone.utc)
    yarin = (bugun + pd.Timedelta(days=1)).strftime("%Y%m%d")
    for sem in CNBC_SEM:
        ad = _ad(sem)
        parca = []
        for bas in range(2000, bugun.year + 1, 5):
            son = f"{bas + 4}1231235959" if bas + 4 < bugun.year else f"{yarin}000000"
            u = (f"https://ts-api.cnbc.com/harmony/app/bars/{urllib.request.quote(sem)}/1D/"
                 f"{bas}0101000000/{son}/adjusted/EST5EDT.json")
            try:
                s = _cnbc_bar(al(u, sn=30, deneme=3))
                if not s.empty:
                    parca.append(s)
            except Exception as e:  # noqa: BLE001
                UYARILAR.append(f"CNBC günlük {sem} {bas}: {e!r}")
        if parca:
            gunluk[ad] = pd.concat(parca)
        try:
            aylik[ad] = _cnbc_bar(al("https://ts-api.cnbc.com/harmony/app/charts/ALL.json?symbol="
                                     + urllib.request.quote(sem), sn=30, deneme=2))
        except Exception as e:  # noqa: BLE001
            UYARILAR.append(f"CNBC aylık {sem}: {e!r}")
        print(f"  · CNBC {sem}: günlük {len(gunluk.get(ad, []))} · aylık {len(aylik.get(ad, []))}", flush=True)
    if gunluk:
        gz_yaz(pd.DataFrame(gunluk), "cnbc_gunluk.csv.gz", "CNBC (Tullett Prebon), günlük bar ucu",
               "Gösterge (benchmark) devlet tahvili getirisi, %; eurusd = EUR/USD; günlük kapanış, "
               "tarih CNBC işlem günü (New York saati); hafta sonu barları kaynakta cumanın kopyası",
               beklenen_ilk="2000-01-10")
    if aylik:
        gz_yaz(pd.DataFrame(aylik), "cnbc_aylik.csv.gz", "CNBC (Tullett Prebon), ALL grafik ucu",
               "Gösterge devlet tahvili getirisi, aylık kapanış, %", gunluk=False)


# ── ECB politika faizi ─────────────────────────────────────────────────────
def ecb_faiz() -> None:
    try:
        df = ecb_csv("FM/D.U2.EUR.4F.KR.DFR.LEV")
        s = df.assign(t=pd.to_datetime(df["TIME_PERIOD"])).set_index("t")["OBS_VALUE"]
        gz_yaz(pd.DataFrame({"dfr": s}), "ecb_dfr.csv.gz", "ECB, FM.D.U2.EUR.4F.KR.DFR.LEV",
               "ECB mevduat imkânı faizi, %, günlük (takvim günü)")
    except Exception as e:  # noqa: BLE001
        UYARILAR.append(f"ECB DFR: {e!r}")


def main() -> int:
    VERI.mkdir(exist_ok=True)
    t0 = time.monotonic()
    for ad, f in (("Bundesbank", bundesbank), ("ABD Hazinesi", hazine), ("ECB", ecb),
                  ("ECB faiz", ecb_faiz), ("Eurostat", eurostat), ("Yahoo", yahoo),
                  ("CNBC", cnbc)):
        print(f"── {ad}", flush=True)
        try:
            f()
        except Exception as e:  # noqa: BLE001 — bir kaynağın düşmesi öbürlerini götürmesin
            UYARILAR.append(f"{ad} DÜŞTÜ: {e!r}")
            print(f"  ✗ {ad}: {e!r}", flush=True)
    kunye = {"olusturma": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "sure_sn": round(time.monotonic() - t0, 1), "dosyalar": KAYNAKLAR, "uyarilar": UYARILAR}
    (VERI / "kunye.json").write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── bitti {kunye['sure_sn']} sn · {len(KAYNAKLAR)} dosya · {len(UYARILAR)} uyarı")
    for u in UYARILAR:
        print("  ! " + u)
    return 0 if KAYNAKLAR else 1


if __name__ == "__main__":
    sys.exit(main())
