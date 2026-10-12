#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — girdileri BİR KEZ dondurur.

Analiz yayımlandığı günün ölçümüdür (karar 08.09.2026): metindeki sayılar ve
figürler CANLI hatlardan okunamaz — hatların `data/` dosyaları her koşuda
yeniden yazılır ("BİR REHBERİN GİRDİSİ, KAYAN BİR PENCEREDEN OKUNAMAZ"). Bu
betik iki tür girdiyi `veri/` altına deterministik `csv.gz` olarak yazar:

  DEPO     bültenin piyasa fotoğrafı (51 enstrüman, 2025-10 → 2026-10; döviz
           kapanışları saatlik bardan, lira İstanbul 18:00, öbürleri New York
           17:00), DİBS eğrisi ve başabaşlar, TCMB fonlama ve rezerv hatları,
           ödemeler dengesinin enerji kalemleri, TÜFE (enerji dahil), makro
           dersinin donmuş arşivi (ABD Hazinesi 1990+, DXY/VIX, TCMB kuru 1990+,
           GSYH, ABD TÜFE)
  BULUT    `arsiv_brent.py` / `arsiv_brent_ek.py`'nin ham yanıtları
           (`veri/ham/`): CNBC günlük barları, Yahoo kapanışları, EIA spot ve
           pompa fiyatları, EVDS TÜFE kalemleri, ABD Hazinesi 2025–2026,
           Dünya Bankası Pink Sheet

ÇIPA. Günlük seriler 9 Ekim 2026 (cuma; yazının veri günü — 12 Ekim'in
kapanışı yazı kurulurken yerleşmemişti), aylık seriler kaynağın son ayı.
Künyede her depo kaynağının git blob özü ve HEAD commit'i durur.

KAYNAK OLDUĞU GİBİ. Arşiv kaynağın verdiğini saklar; ayıklama (vade devri,
hafta sonu barı, tatil) ölçüm katmanında kuralıyla yapılır. Tek istisna CNBC
hafta sonu barıdır: kaynakta cumanın kopyası olduğu ölçülmüştü (makro dersi,
`hazirla_bulut.py`) ve burada da atılır, sayısı künyeye yazılır.

DETERMİNİZM. Sabit ondalık, `\\n` satır sonu, gzip zaman damgası 0; künyedeki
sha256 SIKIŞTIRILMAMIŞ metnin özüdür ve künye duvar saati taşımaz.

ÜSTÜNE YAZMAZ: var olan bir arşiv dosyası `--yeniden` olmadan yenilenmez.

Koşum:  python3 hazirla.py [--yalniz depo|bulut] [--adim ad1,ad2] [--yeniden]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
AP = KOK / "Aktarılacak Projeler"
VERI = BURASI / "veri"
HAM = VERI / "ham"
KUNYE_YOL = VERI / "kunye.json"
CIPA = pd.Timestamp("2026-10-09")

KUNYE: dict[str, dict] = {}
UYARI: list[str] = []


# ─────────────────────────────────────────────────────────────── yardımcılar
def git_blob(yol: Path) -> str | None:
    try:
        return subprocess.run(["git", "hash-object", str(yol)], cwd=KOK, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def head() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=KOK, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def yaz(df: pd.DataFrame, ad: str, aciklama: str, kaynak: str, sutun: dict | None = None,
        kaynak_yol: list | None = None, ondalik: int = 6, gunluk: bool = True, ek: dict | None = None,
        yeniden: bool = False) -> None:
    yol = VERI / f"{ad}.csv.gz"
    if yol.exists() and not yeniden:
        raise SystemExit(f"{yol.name} var — yenilemek için --yeniden (yeni pencere metnin sayılarını değiştirir)")
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df.index = pd.DatetimeIndex(df.index).normalize()
    df.index.name = "tarih"
    metin = df.to_csv(float_format=f"%.{ondalik}f", lineterminator="\n", date_format="%Y-%m-%d")
    ham = metin.encode("utf-8")
    tampon = io.BytesIO()
    with gzip.GzipFile(fileobj=tampon, mode="wb", mtime=0) as g:
        g.write(ham)
    yol.write_bytes(tampon.getvalue())
    kapsam = {}
    for c in df.columns:
        s = df[c].dropna()
        kapsam[c] = {"n": int(len(s)), "ilk": s.index.min().strftime("%Y-%m-%d") if len(s) else None,
                     "son": s.index.max().strftime("%Y-%m-%d") if len(s) else None}
        if not len(s):
            UYARI.append(f"{ad}:{c} BOŞ")
    KUNYE[yol.name] = {"sha256": hashlib.sha256(ham).hexdigest(), "satir": int(len(df)), "aciklama": aciklama,
                       "kaynak": kaynak, "sutun_aciklama": sutun or {}, "kapsam": kapsam,
                       "kaynak_dosyalar": [{"yol": str(p.relative_to(KOK)) if isinstance(p, Path) else str(p),
                                            "git_blob": git_blob(p) if isinstance(p, Path) else None}
                                           for p in (kaynak_yol or [])],
                       **(ek or {})}
    print(f"  ✓ {yol.name}: {len(df)} satır · {len(df.columns)} sütun", flush=True)


def kes(df: pd.DataFrame) -> pd.DataFrame:
    """Çıpada keser. Sıralamadan `.loc[:CIPA]` YAZILMAZ: sırasız bir dizinde dilim konumsaldır —
    ABD Hazinesi'nin iki yıllık dosyası azalan sırayla birleşince 2026'nın 194 günü sessizce düşmüştü."""
    df = df.sort_index()
    return df[df.index <= CIPA]


def ham_oku(yol: str) -> bytes:
    return gzip.decompress((HAM / yol).read_bytes())


def ham_kunye() -> dict:
    out = {}
    for p in sorted(HAM.glob("kunye_*.json")):
        out.update(json.loads(p.read_text(encoding="utf-8")))
    return out


# ─────────────────────────────────────────────────────────────── depo
PIYASA_ADI = {
    "XU100.IS": "BIST 100", "XU030.IS": "BIST 30", "XBANK.IS": "BIST Bankacılık", "XUSIN.IS": "BIST Sınai",
    "USDTRY=X": "USD/TRY", "EURTRY=X": "EUR/TRY", "GBPTRY=X": "GBP/TRY", "TUR": "Türkiye hisse fonu (TUR)",
    "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^DJI": "Dow Jones", "^RUT": "Russell 2000", "^VIX": "VIX",
    "^STOXX": "STOXX Europe 600", "^GDAXI": "DAX", "^FCHI": "CAC 40", "^FTSE": "FTSE 100",
    "FTSEMIB.MI": "FTSE MIB", "^N225": "Nikkei 225", "^HSI": "Hang Seng", "000001.SS": "Şanghay Bileşik",
    "^IRX": "ABD 13 haftalık bono", "2YY=F": "ABD 2 yıllık (vadeli)", "^FVX": "ABD 5 yıllık", "^TNX": "ABD 10 yıllık",
    "^TYX": "ABD 30 yıllık", "^MOVE": "MOVE", "DX-Y.NYB": "Dolar endeksi (DXY)", "EURUSD=X": "EUR/USD",
    "USDJPY=X": "USD/JPY", "GBPUSD=X": "GBP/USD", "USDCHF=X": "USD/CHF", "AUDUSD=X": "AUD/USD",
    "NZDUSD=X": "NZD/USD", "USDCAD=X": "USD/CAD", "USDSEK=X": "USD/SEK", "USDNOK=X": "USD/NOK",
    "GC=F": "altın", "SI=F": "gümüş", "PL=F": "platin", "HG=F": "bakır", "BZ=F": "Brent", "CL=F": "WTI",
    "RB=F": "RBOB benzin", "HO=F": "kalorifer yakıtı (ULSD)", "NG=F": "doğal gaz (Henry Hub)",
    "HYG": "ABD yüksek getirili kredi fonu (HYG)", "LQD": "ABD yatırım yapılabilir kredi fonu (LQD)",
    "EMB": "gelişmekte olan ülke dolar tahvili fonu (EMB)", "EEM": "gelişmekte olan piyasa hisse fonu (EEM)",
    "BTC-USD": "Bitcoin",
}


def depo_piyasa(yeniden: bool) -> None:
    kaynak = KOK / "bulten/onbellek/piyasa_ham.json"
    d = json.loads(kaynak.read_text(encoding="utf-8"))
    seri, tanim = {}, {}
    for k, v in d["seri"].items():
        s = pd.Series(v["kapanis"], index=pd.to_datetime(v["tarih"]), dtype="float64")
        seri[k] = s[s.index <= CIPA]
        if v.get("kapanis_tanimi"):
            tanim[k] = v["kapanis_tanimi"]
    df = pd.DataFrame(seri)
    yaz(df, "piyasa_2026", "Bültenin piyasa fotoğrafı: 51 enstrümanın günlük kapanışı (2025-10 → 2026-10-09)",
        "Yahoo Finance (bülten ölçüm katmanı); döviz kapanışı saatlik bardan (`ortak/fx_kapanis`)",
        {k: PIYASA_ADI.get(k, k) for k in df.columns}, [kaynak], ondalik=6, yeniden=yeniden,
        ek={"doviz_kapanis_surumu": d.get("doviz_kapanis"), "kapanis_tanimi": tanim,
            "piyasa_zamani": d.get("zaman"),
            "not": ("Vadeli seriler (BZ=F, CL=F, RB=F, HO=F, NG=F) ham ön vade kapanışıdır; vade devri "
                    "günleri ölçüm katmanında ayıklanır. Getiri satırları (^IRX, ^FVX, ^TNX, ^TYX, 2YY=F) % "
                    "cinsinden seviye; 2YY=F bayat vadeli kotasyon taşır (bülten kaydı) ve kullanılmaz.")})


def depo_tr(yeniden: bool) -> None:
    m_yol = AP / "DIBS/data/metrik.csv"
    m = pd.read_csv(m_yol, parse_dates=["tarih"], index_col="tarih")
    kol = ["n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y", "n9y", "be_1y", "be_2y", "be_3y", "be_5y",
           "r1y", "r2y", "r3y", "r5y", "pka_12a", "pka_24a", "tlref", "politika", "aofm"]
    m = m[[c for c in kol if c in m.columns]]
    yaz(m[m.index <= CIPA], "dibs_gunluk", "DİBS sıfır kuponlu nominal ve reel (TÜFE'ye endeksli) getiri eğrisi, başabaş, beklenti",
        "TCMB EVDS (DİBS kotasyonları) — DİBS hattının eğri kurulumu",
        {"n3a": "nominal 3 ay, %", "n2y": "nominal 2 yıl, %", "n5y": "nominal 5 yıl, %", "be_2y": "2 yıllık başabaş, %",
         "r2y": "2 yıllık reel getiri, %", "pka_12a": "12 ay sonrası TÜFE beklentisi (Piyasa Katılımcıları Anketi), %"},
        [m_yol], yeniden=yeniden)

    f_yol = AP / "Fonlama/data/gunluk.csv"
    f = pd.read_csv(f_yol, parse_dates=["tarih"], index_col="tarih")
    f = f[["tlref", "aofm", "politika", "koridor_alt", "koridor_ust", "fon_ihale", "fon_top", "net_fonlama"]]
    yaz(f[f.index <= CIPA], "fonlama_gunluk", "TCMB fonlaması: TLREF, ağırlıklı ortalama fonlama maliyeti, politika faizi, koridor, repo ihalesi",
        "TCMB EVDS, BIST TLREF — Fonlama hattı",
        {"tlref": "TLREF, %", "aofm": "TCMB ağırlıklı ortalama fonlama maliyeti, %", "politika": "politika faizi, %",
         "koridor_ust": "gecelik borç verme faizi, %", "fon_ihale": "bir hafta vadeli repo ihalesi tutarı, mn TL"},
        [f_yol], yeniden=yeniden)

    r_yol = AP / "TCMBNetRezerv/gunluk.csv"
    r = pd.read_csv(r_yol, parse_dates=["Tarih"], index_col="Tarih")
    r = r[["net_rezerv_usd", "swap_haric_net_rezerv_usd", "brut_usd", "net_doviz_alimi", "altin_usd", "doviz_usd",
           "altin_fiyat_etkisi"]]
    yaz(r[r.index <= CIPA], "rezerv_gunluk", "TCMB net rezerv, swap hariç net rezerv, brüt rezerv ve altın fiyat etkisinden arındırılmış net döviz alımı",
        "TCMB analitik bilanço (EVDS) ve uluslararası rezervler — TCMB net rezerv hattı",
        {"net_rezerv_usd": "milyar USD", "swap_haric_net_rezerv_usd": "milyar USD", "brut_usd": "milyar USD",
         "net_doviz_alimi": "günlük, milyar USD (+ alım, − satış)"}, [r_yol], yeniden=yeniden)

    o_yol = AP / "OdemelerDengesi/data/aylik.csv"
    o = pd.read_csv(o_yol, parse_dates=["tarih"], index_col="tarih")
    o = o[["cari", "hc_enerji_ith", "hc_enerji_ihr", "hc_enerji_net", "hc_altin_net", "hc_cekirdek"]]
    yaz(o, "odemeler_aylik", "Ödemeler dengesi: cari denge ve enerji kalemleri, aylık, milyon USD",
        "TCMB ödemeler dengesi istatistikleri (EVDS) — Ödemeler dengesi hattı",
        {"hc_enerji_ith": "enerji ithalatı (+), mn USD", "hc_enerji_ihr": "enerji ihracatı, mn USD",
         "hc_enerji_net": "net enerji (− açık), mn USD"}, [o_yol], gunluk=False, yeniden=yeniden)

    e_yol = AP / "Enflasyon/data/aylik.csv"
    e = pd.read_csv(e_yol, parse_dates=["tarih"], index_col="tarih")
    e = e[["tufe", "enerji", "cekirdek_c", "gida", "hizmet", "pka_12a"]]
    yaz(e, "tufe_aylik", "TÜFE (2025=100), enerji ve çekirdek C göstergeleri, aylık",
        "TÜİK TÜFE (EVDS) — Enflasyon hattı", {"enerji": "TÜİK özel kapsamlı enerji göstergesi"},
        [e_yol], gunluk=False, yeniden=yeniden)


def depo_makro(yeniden: bool) -> None:
    mk = AP / "MakroKurFaiz/veri"
    for ad, yol, aciklama, kaynak in (
        ("abd_hazine_1990", mk / "bulut/abd_hazine_1y.csv.gz", "ABD Hazinesi par getiri eğrisi (3 ay–30 yıl), 1990+",
         "ABD Hazinesi Daily Treasury Par Yield Curve (makro dersi arşivi)"),
        ("abd_reel_2003", mk / "bulut/abd_reel_getiri.csv.gz", "ABD Hazinesi reel (TIPS) par getiri eğrisi, 2003+",
         "ABD Hazinesi Daily Treasury Real Yield Curve (makro dersi arşivi)"),
        ("dxy_vix_1971", mk / "yahoo_dxy_vix_gunluk.csv.gz", "Dolar endeksi (1971+) ve VIX (1990+)",
         "Yahoo Finance (makro dersi arşivi)"),
        ("usdtry_tcmb_1990", mk / "usdtry_tcmb_gunluk.csv.gz", "TCMB gösterge kuru (döviz alış), valör tarihli, 1990+",
         "TCMB EVDS (makro dersi arşivi)"),
        ("gecelik_1990", mk / "gecelik_gunluk.csv.gz", "TCMB gecelik ağırlıklı ortalama faiz, 1990+",
         "TCMB EVDS (makro dersi arşivi)"),
        ("gsyh_ceyreklik", mk / "gsyh_ceyreklik.csv.gz", "GSYH, çeyreklik (cari fiyatlarla, bin TL)",
         "TÜİK (makro dersi arşivi)"),
        ("kuresel_aylik", mk / "kuresel_aylik.csv.gz", "Pink Sheet enerji endeksi, ABD TÜFE ve çekirdek TÜFE, politika faizleri",
         "Dünya Bankası Pink Sheet, BLS (makro dersi arşivi)"),
    ):
        df = pd.read_csv(yol, index_col=0, parse_dates=True)
        dk = 8 if ad == "usdtry_tcmb_1990" else 6
        yaz(df, ad, aciklama, kaynak, None, [yol], ondalik=dk, gunluk=not ad.endswith(("aylik", "ceyreklik")),
            yeniden=yeniden)


def depo_surucu(yeniden: bool) -> None:
    """Makro dersinin CNBC sürücü arşivi (aynı uç, 2000 → 30.09.2026, 41 araç): Brent arşivinin ilk
    geçişinde CNBC'nin boş döndürdüğü sembollerin (Brent, altın, EUR/USD, USD/JPY, ABD 2 yıllık …)
    ve boş beş yıllık parçaların YEDEĞİ. Ölçüm katmanı iki geçişi birleştirir; ikisinin örtüştüğü
    günlerde birebirliği sınar ve sayısını yazar."""
    yol = AP / "MakroKurFaiz/veri/bulut/surucu_gunluk.csv.gz"
    df = pd.read_csv(yol, index_col=0, parse_dates=True)
    yaz(df, "cnbc_surucu_2000", "CNBC günlük kapanışları, 2000 → 30.09.2026 (makro dersinin sürücü arşivi)",
        "CNBC (ts-api.cnbc.com, günlük bar ucu; makro dersi arşivi)", None, [yol], yeniden=yeniden)


def depo_yabanci(yeniden: bool) -> None:
    """Yurt dışı yerleşiklerin haftalık hisse senedi ve DİBS kesin alım-satımı (TCMB menkul kıymet
    istatistikleri, milyon USD; hafta cuma günüyle tarihli) — bir petrol şokunda taşıma pozisyonunun
    ne kadar hızlı çözüldüğünün ölçüsü."""
    yol = AP / "ForeignHoldings/foreign_holdings_data.csv"
    df = pd.read_csv(yol, parse_dates=["Tarih"]).set_index("Tarih")[["Hisse", "DIBS", "Toplam"]]
    df.columns = ["hisse", "dibs", "toplam"]
    yaz(kes(df), "yabanci_haftalik", "Yurt dışı yerleşiklerin haftalık hisse senedi ve DİBS net alımı, milyon USD",
        "TCMB haftalık menkul kıymet istatistikleri (EVDS) — yabancı portföy hattı",
        {"hisse": "hisse senedi net alımı, mn USD (+ alım)", "dibs": "DİBS net alımı, mn USD (+ alım)"}, [yol],
        ondalik=2, yeniden=yeniden)


def depo_dis_ticaret(yeniden: bool) -> None:
    """Dış ticaret birim değer ve miktar endeksleri (TÜİK, 2013=100): yakıt ithalatının birim değeri
    Türkiye'nin enerji faturasının FİYAT bacağıdır — vadeli Brent mi fiziki Brent mi, bu seri söyler."""
    yol = AP / "MakroKurFaiz/veri/bulut/evds_dis_ticaret_endeks.csv.gz"
    df = pd.read_csv(yol, index_col=0, parse_dates=True)
    yaz(df, "dis_ticaret_endeks", "Dış ticaret birim değer ve miktar endeksleri, aylık (yakıt ithalatı dahil)",
        "TÜİK dış ticaret endeksleri (TCMB EVDS; makro dersi arşivi)",
        {"ith_yakit_birim_deger": "yakıt ithalatı birim değer endeksi (USD bazlı)",
         "ith_yakit_miktar": "yakıt ithalatı miktar endeksi"}, [yol], gunluk=False, yeniden=yeniden)


# ─────────────────────────────────────────────────────────────── bulut
def bulut_cnbc(yeniden: bool) -> None:
    hk = ham_kunye()
    sutun, yollar, sembol, haftasonu = {}, [], {}, {}
    for p in sorted((HAM / "cnbc").glob("*.json.gz")):
        arac = p.name.split("__")[0]
        y = str(p.relative_to(HAM))
        bars = (json.loads(ham_oku(y)).get("barData") or {}).get("priceBars") or []
        s = pd.Series({pd.Timestamp(b["tradeTime"][:8]): float(b["close"]) for b in bars
                       if b.get("close") not in (None, "", "UNCH")}, dtype="float64")
        if not len(s):
            continue
        sutun.setdefault(arac, []).append(s)
        yollar.append(HAM / y)
        sembol[arac] = hk.get(y, {}).get("not", "").split(" · ")[-1]
    if not sutun:
        UYARI.append("CNBC ham barı yok")
        return
    seri = {}
    for a, parca in sutun.items():
        x = pd.concat(parca).sort_index()
        x = x[~x.index.duplicated(keep="last")]
        haftasonu[a] = int((x.index.dayofweek >= 5).sum())
        x = x[x.index.dayofweek < 5]
        seri[a] = x[x.index <= CIPA]
    df = pd.DataFrame(seri).sort_index()
    yaz(df, "cnbc_gunluk", "CNBC günlük kapanış barları: vadeli emtia, paralar (New York 17:00), getiriler, hisse endeksleri",
        "CNBC (ts-api.cnbc.com, günlük bar ucu)", {a: sembol.get(a, "") for a in df.columns}, yollar,
        ek={"sembol": sembol, "atilan_hafta_sonu_bari": haftasonu,
            "not": "Yakın vade vadeli serileri vade devrinde sıçrar (ham); döviz barı New York 17:00, vadeli barı borsa seansı."},
        yeniden=yeniden)


def bulut_yahoo(yeniden: bool) -> None:
    kapanis, duz, yollar = {}, {}, []
    for p in sorted((HAM / "yahoo").glob("*.csv.gz")):
        y = str(p.relative_to(HAM))
        df = pd.read_csv(io.BytesIO(ham_oku(y)), index_col=0, parse_dates=True)
        ad = p.name[:-len(".csv.gz")]
        if "Close" not in df:
            continue
        kapanis[ad] = df["Close"]
        if "Adj Close" in df:
            duz[ad] = df["Adj Close"]
        yollar.append(HAM / y)
    if not kapanis:
        UYARI.append("Yahoo ham dosyası yok")
        return
    yaz(kes(pd.DataFrame(kapanis)), "yahoo_kapanis", "Yahoo günlük kapanış (borsanın işlem günü)",
        "Yahoo Finance (yfinance)", None, yollar, yeniden=yeniden)
    yaz(kes(pd.DataFrame(duz)), "yahoo_duzeltilmis", "Yahoo düzeltilmiş kapanış (temettü ve bölünme)",
        "Yahoo Finance (yfinance)", None, yollar, yeniden=yeniden)


def _eia_xls(y: str) -> pd.Series:
    x = pd.read_excel(io.BytesIO(ham_oku(y)), sheet_name="Data 1", header=2)
    x = x.dropna()
    s = pd.Series(pd.to_numeric(x.iloc[:, 1], errors="coerce").values, index=pd.to_datetime(x.iloc[:, 0]))
    return s.dropna()


def bulut_eia(yeniden: bool) -> None:
    seri, yollar = {}, []
    for ad in ("brent_spot_gunluk", "wti_spot_gunluk", "abd_benzin_pompa_haftalik", "abd_motorin_pompa_haftalik"):
        y = f"eia/{ad}.xls.gz"
        if not (HAM / y).exists():
            UYARI.append(f"EIA {ad} yok")
            continue
        seri[ad] = _eia_xls(y)
        yollar.append(HAM / y)
    if "brent_spot_gunluk" in seri:
        yaz(kes(pd.DataFrame({k: seri[k] for k in ("brent_spot_gunluk", "wti_spot_gunluk") if k in seri})),
            "eia_spot_gunluk", "EIA spot fiyatı: Europe Brent (RBRTE) ve WTI Cushing (RWTC), USD/varil",
            "U.S. Energy Information Administration", None, [p for p in yollar if "spot" in p.name], yeniden=yeniden)
    pompa = {k: seri[k] for k in ("abd_benzin_pompa_haftalik", "abd_motorin_pompa_haftalik") if k in seri}
    if pompa:
        yaz(kes(pd.DataFrame(pompa)), "eia_pompa_haftalik", "ABD perakende benzin ve motorin fiyatı, USD/galon, haftalık",
            "U.S. Energy Information Administration", None, [p for p in yollar if "pompa" in p.name], yeniden=yeniden)


def _evds_tarih(t: str) -> pd.Timestamp:
    m = re.fullmatch(r"(\d{4})-(\d{1,2})", str(t))
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", str(t))
    if m:
        return pd.Timestamp(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    raise ValueError(f"EVDS tarih biçimi tanınmadı: {t}")


def bulut_evds(yeniden: bool) -> None:
    import arsiv_brent as ab
    ad_kod = ab.EVDS_SERI
    parca, yollar = [], []
    for p in sorted((HAM / "evds").glob("*.json.gz")):
        if p.name.startswith("serielist"):
            continue
        y = str(p.relative_to(HAM))
        j = json.loads(ham_oku(y))
        df = pd.DataFrame(j.get("items") or [])
        if df.empty:
            continue
        df = df.drop(columns=[c for c in ("UNIXTIME", "YEARWEEK") if c in df.columns])
        df["tarih"] = [_evds_tarih(t) for t in df.pop("Tarih")]
        parca.append(df.set_index("tarih"))
        yollar.append(HAM / y)
    if not parca:
        UYARI.append("EVDS TÜFE kalemi yok")
        return
    df = pd.concat(parca, axis=1)
    df = df.loc[:, ~df.columns.duplicated()].apply(pd.to_numeric, errors="coerce")
    df.columns = [c.replace("_", ".") for c in df.columns]
    ters = {v: k for k, v in ad_kod.items()}
    df = df.rename(columns={c: ters.get(c, c) for c in df.columns})
    yaz(df, "tufe_kalem_aylik", "TÜFE enerji ve akaryakıt kalemleri (2025=100), aylık",
        "TÜİK TÜFE (TCMB EVDS)", {k: v for k, v in ad_kod.items()}, yollar, gunluk=False, yeniden=yeniden)


def bulut_hazine(yeniden: bool) -> None:
    nom, reel, yollar = [], [], []
    for p in sorted((HAM / "hazine").glob("*.csv.gz")):
        y = str(p.relative_to(HAM))
        df = pd.read_csv(io.BytesIO(ham_oku(y)))
        if "Date" not in df.columns:
            continue
        df["tarih"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
        df = df.set_index("tarih").drop(columns=["Date"])
        (reel if "real" in p.name else nom).append(df)
        yollar.append(HAM / y)
    if nom:
        n = pd.concat(nom).apply(pd.to_numeric, errors="coerce")
        yaz(kes(n), "hazine_nominal_2025", "ABD Hazinesi par getiri eğrisi, 2025–2026, %", "ABD Hazinesi",
            None, [p for p in yollar if "real" not in p.name], yeniden=yeniden)
    if reel:
        r = pd.concat(reel).apply(pd.to_numeric, errors="coerce")
        yaz(kes(r), "hazine_reel_2025", "ABD Hazinesi reel (TIPS) par getiri eğrisi, 2025–2026, %", "ABD Hazinesi",
            None, [p for p in yollar if "real" in p.name], yeniden=yeniden)


def bulut_pink(yeniden: bool) -> None:
    y = "worldbank/CMO-Historical-Data-Monthly.xlsx.gz"
    if not (HAM / y).exists():
        UYARI.append("Pink Sheet yok")
        return
    xl = pd.ExcelFile(io.BytesIO(ham_oku(y)))
    sayfa = next(s for s in xl.sheet_names if "Monthly Prices" in s)
    ham_df = xl.parse(sayfa, header=None)
    # Başlık satırı BULUNUR (sayfa düzeni sürümden sürüme değişebilir — El Niño hattında ölçüldü):
    # ilk sütunu "1960M01" biçiminde olan ilk satırdan önceki satırlar başlıktır.
    ilk = next(i for i in range(len(ham_df)) if re.fullmatch(r"\d{4}M\d{2}", str(ham_df.iat[i, 0]).strip()))
    basliklar = [" ".join(str(ham_df.iat[j, c]) for j in range(max(0, ilk - 6), ilk)
                          if str(ham_df.iat[j, c]) not in ("nan", "")) for c in range(ham_df.shape[1])]
    aranan = {"brent": "Crude oil, Brent", "ham_ort": "Crude oil, average", "dubai": "Crude oil, Dubai",
              "wti": "Crude oil, WTI", "avrupa_gaz": "Natural gas, Europe", "lng_japonya": "Liquefied natural gas, Japan"}
    sec = {}
    for ad, k in aranan.items():
        aday = [c for c, b in enumerate(basliklar) if k.lower() in b.lower()]
        if aday:
            sec[ad] = aday[0]
        else:
            UYARI.append(f"Pink Sheet sütunu yok: {k} (başlıklar: {[b for b in basliklar if 'rude' in b][:6]})")
    veri = ham_df.iloc[ilk:]
    tarih = [pd.Timestamp(int(str(t)[:4]), int(str(t)[5:7]), 1) for t in veri.iloc[:, 0]]
    df = pd.DataFrame({ad: pd.to_numeric(veri.iloc[:, c], errors="coerce").values for ad, c in sec.items()}, index=tarih)
    yaz(df, "pink_aylik", "Dünya Bankası Pink Sheet aylık ortalama fiyatlar: ham petrol (Brent, Dubai, WTI, ortalama), Avrupa gazı, LNG",
        "Dünya Bankası, Commodity Markets (Pink Sheet)", {ad: aranan[ad] for ad in sec}, [HAM / y], gunluk=False,
        yeniden=yeniden)


def bulut_egri(yeniden: bool) -> None:
    """Vade eğrisi: Yahoo'da listeli tek tek kontratların kapanışı (sütun = kontrat) ve CNBC sürekli
    ikinci ve sonraki vadeler. Ham CNBC barı burada da hafta sonu süzgecinden geçer (ön vadeyle aynı)."""
    kap, yollar = {}, []
    for p in sorted((HAM / "yahoo_egri").glob("*.csv.gz")):
        y = str(p.relative_to(HAM))
        df = pd.read_csv(io.BytesIO(ham_oku(y)), index_col=0, parse_dates=True)
        if "Close" in df and len(df):
            kap[p.name[:-len(".csv.gz")]] = df["Close"]
            yollar.append(HAM / y)
    if kap:
        yaz(kes(pd.DataFrame(kap)), "egri_kontrat", "Brent, WTI ve ULSD vadeli kontratlarının günlük kapanışı (Yahoo'da listeli olanlar)",
            "Yahoo Finance (NYMEX BZ, CL, HO kontratları; yfinance)", None, yollar,
            ek={"not": "Sütun adı kontrat kodudur: BZF27_NYM = Ocak 2027 teslimli Brent. Vadesi dolan kontrat "
                       "Yahoo'dan silinir; eğri yalnız arşiv günü listeli olanlarla kurulur."}, yeniden=yeniden)
    else:
        UYARI.append("Yahoo kontrat eğrisi yok")
    hk = ham_kunye()
    sutun, yollar, sembol, haftasonu = {}, [], {}, {}
    for p in sorted((HAM / "cnbc_egri").glob("*.json.gz")):
        arac = p.name.split("__")[0]
        y = str(p.relative_to(HAM))
        bars = (json.loads(ham_oku(y)).get("barData") or {}).get("priceBars") or []
        s = pd.Series({pd.Timestamp(b["tradeTime"][:8]): float(b["close"]) for b in bars
                       if b.get("close") not in (None, "", "UNCH")}, dtype="float64")
        if len(s):
            sutun.setdefault(arac, []).append(s)
            yollar.append(HAM / y)
            sembol[arac] = hk.get(y, {}).get("not", "").split(" · ")[-1]
    if sutun:
        seri = {}
        for a, parca in sutun.items():
            x = pd.concat(parca).sort_index()
            x = x[~x.index.duplicated(keep="last")]
            haftasonu[a] = int((x.index.dayofweek >= 5).sum())
            seri[a] = x[x.index.dayofweek < 5]
        yaz(kes(pd.DataFrame(seri)), "cnbc_egri", "CNBC sürekli vadeli serileri: Brent ikinci, üçüncü, altıncı, on ikinci vade; WTI ve ULSD ikinci vade",
            "CNBC (ts-api.cnbc.com, günlük bar ucu)", {a: sembol.get(a, "") for a in seri}, yollar,
            ek={"sembol": sembol, "atilan_hafta_sonu_bari": haftasonu}, yeniden=yeniden)
    else:
        UYARI.append("CNBC sürekli vade yok")


def bulut_nyfed(yeniden: bool) -> None:
    """NY Fed Oil Price Dynamics Report: Brent'in HAFTALIK log değişiminin talep, arz ve artık
    payına ayrışması (1986-01-24 → 2023-11-03; rapor 2023'te durdu). Sayfa düzeni BULUNUR:
    başlık satırı "Date" hücresidir, sabit satır numarası varsayılmaz."""
    y = "nyfed/oil_oil_price_dynamics_data_xls.gz"
    if not (HAM / y).exists():
        UYARI.append("NY Fed petrol ayrışması yok")
        return
    xl = pd.ExcelFile(io.BytesIO(ham_oku(y)))
    sayfa = next((s for s in xl.sheet_names if s.startswith("3_")), None)
    if sayfa is None:
        UYARI.append(f"NY Fed: 1986 sayfası yok ({xl.sheet_names})")
        return
    h = xl.parse(sayfa, header=None)
    bas = next(i for i in range(len(h)) if str(h.iat[i, 0]).strip() == "Date")
    basliklar = [str(h.iat[bas, c]).strip() for c in range(h.shape[1])]
    esle = {"Price Brent": "brent", "Demand": "talep", "Supply": "arz", "Residual": "artik"}
    eksik = [k for k in esle if k not in basliklar]
    if eksik:
        UYARI.append(f"NY Fed sütunu yok: {eksik} (başlıklar: {basliklar})")
        return
    v = h.iloc[bas + 1:]
    tarih = pd.to_datetime(v.iloc[:, 0], errors="coerce")
    df = pd.DataFrame({ad: pd.to_numeric(v.iloc[:, basliklar.index(k)], errors="coerce").values
                       for k, ad in esle.items()}, index=tarih.values)
    df = df[df.index.notna()].dropna(how="all")
    fark = float((df["brent"] - df["talep"] - df["arz"] - df["artik"]).abs().max())
    yaz(df, "nyfed_haftalik", "NY Fed petrol fiyatı dinamikleri: Brent'in haftalık log değişimi ve talep / arz / artık payları",
        "Federal Reserve Bank of New York, Oil Price Dynamics Report (son güncelleme 06.11.2023)",
        {"brent": "Brent haftalık log değişimi", "talep": "talep payı", "arz": "arz payı", "artik": "artık"},
        [HAM / y], ondalik=8, ek={"sayfa": sayfa, "ozdeslik_azami_fark": fark,
                                 "not": "Haftalık değerler; kümülatif sayfa (2_2010-today) bu serinin birikimiyle birebir."},
        yeniden=yeniden)


def bulut_gpr(yeniden: bool) -> None:
    """Caldara–Iacoviello jeopolitik risk endeksi: günlük (1985+) ve aylık Türkiye endeksi."""
    y = "gpr/data_gpr_daily_recent_xls.gz"
    if (HAM / y).exists():
        g = pd.read_excel(io.BytesIO(ham_oku(y)))
        g["tarih"] = pd.to_datetime(g["DAY"].astype(int).astype(str), format="%Y%m%d")
        g = g.set_index("tarih")[["GPRD", "GPRD_ACT", "GPRD_THREAT"]].apply(pd.to_numeric, errors="coerce")
        yaz(kes(g), "gpr_gunluk", "Jeopolitik risk endeksi, günlük (Caldara–Iacoviello)",
            "Caldara, D. ve Iacoviello, M. (2022), Measuring Geopolitical Risk — matteoiacoviello.com",
            {"GPRD": "genel", "GPRD_ACT": "eylem", "GPRD_THREAT": "tehdit"}, [HAM / y], yeniden=yeniden)
    else:
        UYARI.append("GPR günlük yok")
    y = "gpr/data_gpr_export_xls.gz"
    if (HAM / y).exists():
        a = pd.read_excel(io.BytesIO(ham_oku(y)))
        a["tarih"] = pd.to_datetime(a["month"])
        kol = [c for c in ("GPR", "GPRT", "GPRA", "GPRC_TUR", "GPRC_SAU", "GPRC_RUS", "GPRC_UKR", "GPRC_ISR")
               if c in a.columns]
        yaz(a.set_index("tarih")[kol].apply(pd.to_numeric, errors="coerce"), "gpr_aylik",
            "Jeopolitik risk endeksi, aylık: genel, tehdit, eylem ve ülke endeksleri",
            "Caldara, D. ve Iacoviello, M. (2022), Measuring Geopolitical Risk — matteoiacoviello.com",
            {"GPRC_TUR": "Türkiye"}, [HAM / y], gunluk=False, yeniden=yeniden)
    else:
        UYARI.append("GPR aylık yok")


ADIMLAR = {
    "depo": ("piyasa", "tr", "makro", "dis_ticaret", "surucu", "yabanci"),
    "bulut": ("cnbc", "yahoo", "eia", "evds", "hazine", "pink", "nyfed", "gpr", "egri"),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yeniden", action="store_true")
    ap.add_argument("--yalniz", choices=sorted(ADIMLAR), default=None)
    ap.add_argument("--adim", default=None,
                    help="virgülle adım adları: " + " · ".join(f"{k}: {','.join(v)}" for k, v in ADIMLAR.items()))
    a = ap.parse_args(argv)
    VERI.mkdir(exist_ok=True)
    eski = json.loads(KUNYE_YOL.read_text(encoding="utf-8")) if KUNYE_YOL.exists() else {}
    KUNYE.update(eski.get("dosyalar", {}))
    sys.path.insert(0, str(BURASI))
    secili = set(a.adim.split(",")) if a.adim else None
    bilinmeyen = (secili or set()) - {x for v in ADIMLAR.values() for x in v}
    if bilinmeyen:
        raise SystemExit(f"bilinmeyen adım: {sorted(bilinmeyen)}")
    for tur, adlar in ADIMLAR.items():
        if a.yalniz not in (None, tur):
            continue
        print(f"── {tur}", flush=True)
        for ad in adlar:
            if secili is None or ad in secili:
                globals()[f"{tur}_{ad}"](a.yeniden)
    kunye = {"cipa": CIPA.strftime("%Y-%m-%d"), "head": head(),
             "not": "sha256 sıkıştırılmamış CSV metninin özüdür; git_blob kaynak dosyanın `git hash-object` özü.",
             "uyarilar": UYARI, "dosyalar": dict(sorted(KUNYE.items()))}
    KUNYE_YOL.write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── künye: {len(KUNYE)} dosya · {len(UYARI)} uyarı")
    for u in UYARI:
        print("  ! " + u)
    return 0


if __name__ == "__main__":
    sys.exit(main())
