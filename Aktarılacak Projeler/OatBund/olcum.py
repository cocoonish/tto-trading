#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND ANALİZİ — ölçüm katmanı. Yazının ve figürlerin BÜTÜN sayıları buradan.

Bu bir hat değil, tek bir analizin ölçümü. Analiz yayımlandığı günün metnidir
(karar 08.09.2026); girdi `veri/` altındaki dondurulmuş arşivdir
(`arsiv_veri.py`, bulutta) ve bu modül AĞA ÇIKMAZ. Her dosyanın özü künyedeki
sha256'ya karşı her okumada yeniden sınanır: arşiv sessizce değişirse ölçüm
düşer.

SÖZLEŞMELER (her biri ölçülerek kondu, gerekçesi yanında):

* SPREAD = ülkenin 10 yıllık gösterge getirisi − Almanya 10 yıllık gösterge
  getirisi, AYNI kaynaktan ve AYNI zaman damgasından (CNBC/Tullett Prebon).
  İki bacağı ayrı kaynaktan almak farkın içine iki kaynağın yöntem ve saat
  farkını koyar. Sabit vadeli Fransa serisi (Banque de France TEC10) anahtarsız
  erişilemedi. Kaynak SINANDI: aylık ortalaması ECB'nin resmî Maastricht
  serisiyle (IRS) 315 ayda korelasyon 0,996, ortalama fark −3,5 bp
  (`kaynak_sinamasi`).
* GÜNÜN SAATİ: hafta içi bar Avrupa kapanışıdır — ECB AAA eğrisiyle aynı gün
  korelasyonu 0,87–0,90, ertesi günle 0,08–0,10. HAFTA SONU barı ATILIR ama
  sebebi "cumanın kopyası" değildir: 564 cuma–cumartesi çiftinin 550'sinde
  cumartesi farklı, yani cuma New York'taki son kotasyon. Başka saatin
  kotasyonu bir Avrupa seansı değildir.
* TAŞINMIŞ İŞ GÜNÜ: Fransa ve Almanya bacaklarının İKİSİ DE bir önceki iş
  gününün değerini birebir taşıyorsa o gün piyasa kapalıdır (tatil) ve atılır.
  Tek bacağın aynı kalması bir ölçümdür.
* EUR/USD: ECB referans kuru (14:15 CET) — resmî, sabit saatli, 1999'dan.
  Kaynakların günü farklı etiketlediği ölçüldü (Yahoo'nun D barı CNBC'nin D−1
  barıyla eşleşiyor, seviye farkı medyanı 0,0008); bu yüzden kur–spread ilişkisi
  HAFTALIK (çarşamba–çarşamba) ölçülür, birkaç saatlik fark beş günlük pencerede
  küçük kalır. Çarşamba: cuma ve pazartesi tatillerinden en az etkilenen gün.
* Değişimler baz puan (bp); seviyeler yüzde; kur değişimi log-yüzde.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"

# Yazının veri günü: arşivin son kapanmış Avrupa seansı.
SON_GUN = "2026-10-01"
# 2026 epizodunun başlangıcı: yılın dibi (ölçülür, `seviye_ozeti` sınar).
EPIZOT_BAS = "2026-02-25"
ULKE_AD = {"fr": "Fransa", "de": "Almanya", "it": "İtalya", "es": "İspanya", "be": "Belçika",
           "nl": "Hollanda", "at": "Avusturya", "pt": "Portekiz", "gr": "Yunanistan"}


class ArsivHatasi(RuntimeError):
    pass


# ── arşiv ─────────────────────────────────────────────────────────────────
@lru_cache(maxsize=None)
def kunye() -> dict:
    return json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def oku(ad: str) -> pd.DataFrame:
    """Arşiv dosyasını okur; özü künyeyle KARŞILAŞTIRIR."""
    k = kunye()["dosyalar"].get(ad)
    if k is None:
        raise ArsivHatasi(f"{ad} künyede yok")
    ham = gzip.decompress((VERI / ad).read_bytes())
    oz = hashlib.sha256(ham).hexdigest()
    if oz != k["sha256"]:
        raise ArsivHatasi(f"{ad} özü künyeyle tutmuyor: {oz[:12]} ≠ {k['sha256'][:12]}")
    df = pd.read_csv(io.BytesIO(ham), index_col=0, parse_dates=True)
    return df.sort_index()


# ── temiz günlük çerçeve ─────────────────────────────────────────────────
@lru_cache(maxsize=None)
def _gunluk_sayimli() -> tuple[pd.DataFrame, dict]:
    ham = oku("cnbc_gunluk.csv.gz")
    ham = ham[ham.index <= SON_GUN]
    hs = ham.index.dayofweek >= 5
    df = ham[~hs].copy()
    tas = (df["fr10y"].diff() == 0) & (df["de10y"].diff() == 0)
    sayim = {"ham_bar": int(len(ham)), "hafta_sonu_atilan": int(hs.sum()),
             "tasinmis_atilan": int(tas.sum()),
             "tasinmis_son": [str(t.date()) for t in df.index[tas]][-6:]}
    df = df[~tas]
    sayim["temiz_gun"] = int(len(df))
    return df, sayim


def gunluk() -> pd.DataFrame:
    return _gunluk_sayimli()[0]


def temizlik_sayimi() -> dict:
    return dict(_gunluk_sayimli()[1])


def spread(ulke: str = "fr", vade: int = 10, karsi: str = "de") -> pd.Series:
    """Ülke − karşı ülke gösterge getirisi farkı, baz puan. İki bacak aynı
    gün ölçülmemişse fark kurulmaz."""
    df = gunluk()
    return ((df[f"{ulke}{vade}y"] - df[f"{karsi}{vade}y"]) * 100).dropna()


def _once(s: pd.Series, gun: str) -> tuple[str, float]:
    """`gun` ya da ondan önceki son gözlem."""
    s = s[s.index <= gun].dropna()
    return str(s.index[-1].date()), float(s.iloc[-1])


def _son_gorulme(s: pd.Series) -> str | None:
    """Bugünkü seviyeye ya da üstüne en son ne zaman çıkıldı (bugünden önce)."""
    once = s[s.index < s.index[-1]]
    ust = once[once >= s.iloc[-1]]
    return str(ust.index[-1].date()) if len(ust) else None


# ── 1. seviye ve konum ────────────────────────────────────────────────────
def seviye_ozeti() -> dict:
    s = spread()
    df = gunluk()
    son = float(s.iloc[-1])
    out = {"gun": str(s.index[-1].date()), "spread": son,
           "fr10": float(df["fr10y"].dropna().iloc[-1]),
           "de10": float(df["de10y"].dropna().iloc[-1])}
    for ad, i in (("1g", -2), ("1h", -6), ("1a", -22)):
        out[f"degisim_{ad}"] = son - float(s.iloc[i])
        out[f"tarih_{ad}"] = str(s.index[i].date())
    for ad, gun in (("yb", "2025-12-31"), ("haziran", "2026-06-30"), ("agustos", "2026-08-31")):
        t, v = _once(s, gun)
        out[f"seviye_{ad}"], out[f"tarih_{ad}"], out[f"degisim_{ad}"] = v, t, son - v
    out["son_gorulme"] = _son_gorulme(s)
    out["yuzdelik_2000"] = float((s < son).mean() * 100)
    out["tarihi_zirve"], out["tarihi_zirve_gun"] = float(s.max()), str(s.idxmax().date())
    yil = s[s.index >= "2026-01-01"]
    out["yil_dibi"], out["yil_dibi_gun"] = float(yil.min()), str(yil.idxmin().date())
    out["epizot_degisim"] = son - out["yil_dibi"]
    # Yılın dibi epizodun tanımıdır; sabit yazılan EPIZOT_BAS ölçüyle tutmalı.
    out["epizot_bas_tutarli"] = out["yil_dibi_gun"] == EPIZOT_BAS
    # Bacakların payı: Haziran sonundan bu yana spread artışının ne kadarı OAT'tan.
    t0 = out["tarih_haziran"]
    a, b = df.loc[:t0].dropna(subset=["fr10y", "de10y"]).iloc[-1], df.dropna(subset=["fr10y", "de10y"]).iloc[-1]
    out["haziran_fr_bp"] = float((b["fr10y"] - a["fr10y"]) * 100)
    out["haziran_de_bp"] = float((b["de10y"] - a["de10y"]) * 100)
    # Eylül günleri: en büyük tek günlük açılmalar
    eyl = s[s.index > "2026-08-31"].diff().dropna()
    out["eylul_en_buyuk"] = [(str(t.date()), float(v)) for t, v in eyl.sort_values(ascending=False).head(5).items()]
    out["gunluk_seri_son"] = [(str(t.date()), float(v)) for t, v in s[s.index > "2026-08-27"].items()]
    return out


def kaynak_sinamasi() -> dict:
    """CNBC'den kurulan aylık ortalama farklar ECB'nin resmî serisine karşı."""
    irs = oku("irs_aylik.csv.gz")
    out = {}
    for u in ("fr", "it", "es", "be"):
        cn = spread(u).resample("ME").mean()
        resmi = (irs[u.upper()] - irs["DE"]) * 100
        j = pd.concat([cn.rename("c"), resmi.rename("r")], axis=1, sort=True).dropna()
        f = j["c"] - j["r"]
        out[u] = {"ay": int(len(j)), "korelasyon": float(j.corr().iloc[0, 1]),
                  "ort_fark": float(f.mean()), "mutlak_medyan": float(f.abs().median()),
                  "son_ay": str(j.index[-1].date()), "son_ay_resmi": float(j["r"].iloc[-1]),
                  "son_ay_cnbc": float(j["c"].iloc[-1])}
    return out


# ── 2. akranlar ───────────────────────────────────────────────────────────
AKRAN = ("fr", "it", "gr", "be", "es", "pt", "at", "nl")


def akranlar() -> list[dict]:
    out = []
    for u in AKRAN:
        s = spread(u)
        t_h, v_h = _once(s, "2026-06-30")
        out.append({"ulke": u, "ad": ULKE_AD[u], "gun": str(s.index[-1].date()), "spread": float(s.iloc[-1]),
                    "haziran": v_h, "degisim_haziran": float(s.iloc[-1]) - v_h,
                    "getiri": float(gunluk()[f"{u}10y"].dropna().iloc[-1])})
    return sorted(out, key=lambda r: -r["spread"])


def fransa_italya() -> dict:
    """Fransa'nın 10 yıllığı İtalya'nınkinin üstünde mi, ne zamandan beri."""
    f = spread("fr", 10, "it")
    son_neg = f[f <= 0].index[-1]
    sonra = f[f.index > son_neg]
    fe = spread("fr", 10, "es")
    son_neg_es = fe[fe <= 0].index[-1]
    return {"fr_eksi_it": float(f.iloc[-1]), "kesintisiz_bas": str(sonra.index[0].date()) if len(sonra) else None,
            "gun_sayisi": int(len(sonra)), "tarihce_zirve": float(f.max()), "tarihce_zirve_gun": str(f.idxmax().date()),
            "2000_sonrasi_pozitif_gun": int((f > 0).sum()), "toplam_gun": int(len(f)),
            "ilk_pozitif": str(f[f > 0].index[0].date()) if (f > 0).any() else None,
            "fr_eksi_es": float(fe.iloc[-1]), "es_kesintisiz_bas": str(fe[fe.index > son_neg_es].index[0].date())}


# ── 3. eğri ───────────────────────────────────────────────────────────────
def egri() -> dict:
    out = {}
    for v in (2, 5, 10, 30):
        s = spread("fr", v)
        out[v] = {"spread": float(s.iloc[-1]), "gun": str(s.index[-1].date()),
                  "degisim_1g": float(s.iloc[-1] - s.iloc[-2]),
                  "degisim_haziran": float(s.iloc[-1]) - _once(s, "2026-06-30")[1],
                  "son_gorulme": _son_gorulme(s), "zirve": float(s.max()), "zirve_gun": str(s.idxmax().date()),
                  "en_buyuk_tek_gun_once": None}
        d = s.diff().dropna()
        ust = d[(d.index < d.index[-1]) & (d >= d.iloc[-1])]
        out[v]["tek_gun_son_gorulme"] = str(ust.index[-1].date()) if len(ust) else None
    i2 = spread("it", 2)
    out["it2"] = {"spread": float(i2.iloc[-1]), "degisim_1g": float(i2.iloc[-1] - i2.iloc[-2])}
    df = gunluk()
    for k in ("de2y", "fr2y", "de10y", "fr10y", "us2y"):
        s = df[k].dropna()
        out[f"{k}_1g_bp"] = float((s.iloc[-1] - s.iloc[-2]) * 100)
    return out


# ── 4. epizotlar ──────────────────────────────────────────────────────────
# Başlangıç günü OLAYIN kendisidir (araştırma defteriyle doğrulanır); bitiş
# penceresi zirvenin aranacağı sınırdır. Seviyeler bu tablodan değil veriden.
EPIZOTLAR = [
    ("2008 küresel finans krizi", "2008-09-12", "2009-03-31", "Lehman Brothers'ın çöküşü (15.09.2008)"),
    ("2010 Yunanistan", "2010-04-22", "2010-06-30", "Yunanistan açık revizyonu, ilk kurtarma paketi"),
    ("2011 euro bölgesi borç krizi", "2011-07-01", "2011-12-31", "İtalya ve İspanya'ya bulaşma; Fransa notu tartışması"),
    ("2016–17 cumhurbaşkanlığı seçimi", "2016-11-09", "2017-04-21", "anketlerde Le Pen yükselişi"),
    ("2020 salgın", "2020-02-21", "2020-04-30", "salgın şoku"),
    ("2024 meclisin feshi", "2024-06-07", "2024-07-31", "9 Haziran 2024 fesih kararı (son iş günü 7 Haziran)"),
    ("2024 Barnier hükümetinin düşüşü", "2024-11-29", "2024-12-31", "4 Aralık 2024 gensoru"),
    ("2025 Bayrou güven oylaması", "2025-08-22", "2025-10-31", "25 Ağustos 2025 güven oylaması duyurusu"),
    ("2026", EPIZOT_BAS, SON_GUN, "yılın dibinden bugüne"),
]


def _isgunu(a: str, b: str) -> int:
    return int(np.busday_count(pd.Timestamp(a).date(), pd.Timestamp(b).date()))


def epizotlar() -> list[dict]:
    s, it = spread("fr"), spread("it")
    fx = oku("eurusd_ecb.csv.gz")["eurusd_ecb"].dropna()
    df = gunluk()
    rd = ((df["us2y"] - df["de2y"]) * 100).dropna()
    out = []
    for ad, a, b, olay in EPIZOTLAR:
        p = s[(s.index >= a) & (s.index <= b)]
        tz = p.idxmax()
        t0, v0 = _once(s, a)
        z = float(p.max())
        r = {"ad": ad, "olay": olay, "bas": t0, "bas_seviye": v0, "zirve": z, "zirve_gun": str(tz.date()),
             "acilma": z - v0, "is_gunu": _isgunu(t0, str(tz.date())),
             "eurusd_yuzde": float(100 * (np.log(_once(fx, str(tz.date()))[1]) - np.log(_once(fx, t0)[1]))),
             "rd_bp": _once(rd, str(tz.date()))[1] - _once(rd, t0)[1],
             "it_bp": _once(it, str(tz.date()))[1] - _once(it, t0)[1]}
        for m in (1, 3, 6):
            t = tz + pd.DateOffset(months=m)
            r[f"sonra_{m}a"] = (_once(s, str(t.date()))[1] - z) if t <= s.index[-1] else None
        out.append(r)
    return out


# ── 5. EUR/USD duyarlılığı ────────────────────────────────────────────────
@lru_cache(maxsize=None)
def haftalik() -> pd.DataFrame:
    """Çarşamba–çarşamba haftalık değişimler. fx: 100·Δln(EUR/USD, ECB 14:15);
    rd: Δ(ABD 2y − Almanya 2y), bp; spr: ΔOAT–Bund 10y, bp; ispr: ΔBTP–Bund 10y."""
    df = gunluk()
    fx = oku("eurusd_ecb.csv.gz")["eurusd_ecb"]
    t = pd.DataFrame({"spr": (df["fr10y"] - df["de10y"]) * 100, "ispr": (df["it10y"] - df["de10y"]) * 100,
                      "rd": (df["us2y"] - df["de2y"]) * 100, "de2": df["de2y"] * 100,
                      "de10": df["de10y"] * 100}).join(fx.rename("fx"), how="inner")
    y = oku("yahoo_gunluk.csv.gz")
    if "vix" in y:
        t = t.join(y["vix"].rename("vix"), how="left")
    if "eurchf" in y:
        t = t.join(y["eurchf"].rename("eurchf"), how="left")
    t = t.dropna(subset=["spr", "ispr", "rd", "fx"])
    w = t.resample("W-WED").last()
    d = pd.DataFrame({"fx": np.log(w["fx"]).diff() * 100, "spr": w["spr"].diff(), "ispr": w["ispr"].diff(),
                      "rd": w["rd"].diff(), "de2": w["de2"].diff(), "de10": w["de10"].diff()})
    if "vix" in w:
        d["vix"] = np.log(w["vix"]).diff() * 100
    if "eurchf" in w:
        d["eurchf"] = np.log(w["eurchf"]).diff() * 100
    return d[d.index >= "2004-01-01"].dropna(subset=["fx", "spr", "ispr", "rd"])


def ols(d: pd.DataFrame, y: str, xs: list[str], nw: int = 4) -> dict:
    """En küçük kareler + Newey–West (Bartlett, `nw` gecikme) standart hata."""
    d = d.dropna(subset=[y] + xs)
    X = np.column_stack([np.ones(len(d))] + [d[x].values for x in xs])
    Y = d[y].values
    b, *_ = np.linalg.lstsq(X, Y, rcond=None)
    e = Y - X @ b
    XtXi = np.linalg.inv(X.T @ X)
    u = X * e[:, None]
    S = u.T @ u
    for L in range(1, nw + 1):
        G = u[L:].T @ u[:-L]
        S += (1 - L / (nw + 1)) * (G + G.T)
    se = np.sqrt(np.diag(XtXi @ S @ XtXi))
    return {"n": int(len(d)), "r2": float(1 - e.var() / Y.var()),
            "b": {x: float(b[i + 1]) for i, x in enumerate(xs)},
            "t": {x: float(b[i + 1] / se[i + 1]) for i, x in enumerate(xs)},
            "sabit": float(b[0]), "bas": str(d.index[0].date()), "son": str(d.index[-1].date())}


DONEMLER = [("2004–2026", "2004-01-01", "2026-12-31"), ("2004–2009", "2004-01-01", "2009-12-31"),
            ("2010–2012", "2010-01-01", "2012-12-31"), ("2013–2019", "2013-01-01", "2019-12-31"),
            ("2020–2023", "2020-01-01", "2023-12-31"), ("2024–2026", "2024-01-01", "2026-12-31")]
MODELLER = {"faiz": ["rd"], "faiz+fr": ["rd", "spr"], "faiz+fr+it": ["rd", "spr", "ispr"],
            "faiz+fr+vix": ["rd", "spr", "vix"]}


def duyarlilik() -> dict:
    d = haftalik()
    out = {}
    for ad, a, b in DONEMLER:
        dd = d[(d.index >= a) & (d.index <= b)]
        out[ad] = {m: ols(dd, "fx", xs) for m, xs in MODELLER.items()}
    return out


def kanallar() -> dict:
    """Spread açıldığında Bund ve EUR/CHF ne yapıyor — haftalık, 2024–2026."""
    d = haftalik()
    dd = d[d.index >= "2024-01-01"]
    out = {"de2": ols(dd, "de2", ["spr"]), "de10": ols(dd, "de10", ["spr"])}
    if "eurchf" in dd:
        out["eurchf"] = ols(dd, "eurchf", ["spr"])
    if "vix" in dd:
        out["vix_spr"] = ols(dd, "spr", ["vix"])
    return out


def orneklem_disi(kesim: str = "2023-12-31", egitim_bas: str = "2004-01-01") -> dict:
    """Katsayılar kesim öncesinde tahmin edilir, sonrasında haftalık kur
    değişimini açıklama gücü ölçülür. Kıyas: yalnız faiz farkı modeli ve sıfır."""
    d = haftalik()
    eg = d[(d.index > egitim_bas) & (d.index <= kesim)]
    te = d[d.index > kesim]
    out = {"egitim": f"{eg.index[0].date()}–{eg.index[-1].date()}", "test": f"{te.index[0].date()}–{te.index[-1].date()}",
           "test_n": int(len(te))}
    hata = {}
    for m, xs in (("sifir", []), ("faiz", ["rd"]), ("faiz+fr", ["rd", "spr"]), ("faiz+fr+it", ["rd", "spr", "ispr"])):
        if xs:
            o = ols(eg, "fx", xs)
            tah = o["sabit"] + sum(o["b"][x] * te[x] for x in xs)
        else:
            tah = pd.Series(0.0, index=te.index)
        e = te["fx"] - tah
        hata[m] = e
        out[m] = {"r2_dis": float(1 - (e ** 2).sum() / ((te["fx"] - te["fx"].mean()) ** 2).sum()),
                  "mae": float(e.abs().mean())}
    # Eşli fark: faiz+fr modeli, faiz modeline göre her hafta kare hatayı azaltıyor mu?
    fark = hata["faiz"] ** 2 - hata["faiz+fr"] ** 2
    t = float(fark.mean() / (fark.std(ddof=1) / np.sqrt(len(fark))))
    out["esli_t"] = t
    out["kazandigi_hafta_payi"] = float((fark > 0).mean() * 100)
    return out


def epizot_atfi(bas: str = "2026-08-26", kesim: str = "2026-06-30", egitim_bas: str = "2024-01-01") -> dict:
    """Eylül epizodunda kurun hareketi: ölçülen ve modelin iki kanala atfettiği.

    Katsayılar epizottan ÖNCE (egitim_bas–kesim) tahmin edilir; aksi hâlde
    epizot kendi açıklamasını kendisi kurardı."""
    d = haftalik()
    o = ols(d[(d.index >= egitim_bas) & (d.index <= kesim)], "fx", ["rd", "spr"])
    p = d[d.index > bas]
    return {"pencere": f"{p.index[0].date()}–{p.index[-1].date()}", "hafta": int(len(p)),
            "kur_gercek": float(p["fx"].sum()), "faiz_payi": float(o["b"]["rd"] * p["rd"].sum()),
            "spread_payi": float(o["b"]["spr"] * p["spr"].sum()), "sabit_payi": float(o["sabit"] * len(p)),
            "rd_toplam": float(p["rd"].sum()), "spr_toplam": float(p["spr"].sum()),
            "katsayi": o}


# ── 6. ne kadar gidebilir: ölçülmüş dağılımlar ───────────────────────────
def ileri_dagilim(esik: float = 30.0, pencere: int = 22, ufuk: int = 22) -> dict:
    """Spread son `pencere` iş gününde ≥ `esik` bp açıldığında, sonraki `ufuk`
    iş gününde ne oldu? Örtüşen gözlemler bağımsız değildir; epizot sayısı ayrıca
    yazılır."""
    s = spread()
    g = s.diff(pencere)
    ileri = s.shift(-ufuk) - s
    k = pd.DataFrame({"g": g, "i": ileri}).dropna()
    sec = k[k["g"] >= esik]
    # epizot: ardışık seçilmiş günler arasında 22 iş gününden büyük boşluk yeni epizot.
    gunler = sec.index
    epz = 0
    onceki = None
    for t in gunler:
        if onceki is None or (s.index.get_loc(t) - s.index.get_loc(onceki)) > pencere:
            epz += 1
        onceki = t
    bugun_g = float(g.iloc[-1])
    return {"esik": esik, "pencere": pencere, "ufuk": ufuk, "gozlem": int(len(sec)), "epizot": epz,
            "daha_acildi_payi": float((sec["i"] > 0).mean() * 100) if len(sec) else None,
            "medyan": float(sec["i"].median()) if len(sec) else None,
            "p10": float(sec["i"].quantile(0.1)) if len(sec) else None,
            "p90": float(sec["i"].quantile(0.9)) if len(sec) else None,
            "bugunku_acilma": bugun_g}


def oynaklik_bandi(gun: int = 20, ufuk: int = 22) -> dict:
    """Son `gun` iş gününün gerçekleşen günlük spread oynaklığı ve onun ±1,96σ√ufuk
    bandı. Tahmin değil, ölçek: bugünkü hızla bir ayda ne kadar yer değiştirir."""
    d = spread().diff().dropna()
    sig = float(d.iloc[-gun:].std(ddof=1))
    sig_uzun = float(d[d.index >= "2013-01-01"].std(ddof=1))
    return {"sigma_gunluk": sig, "sigma_2013_sonrasi": sig_uzun, "oran": sig / sig_uzun,
            "bant_1a": 1.96 * sig * np.sqrt(ufuk), "spread": float(spread().iloc[-1])}
