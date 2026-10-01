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
* GÜNÜN SAATİ: hafta içi bar PARİS 17:30 kotasyonudur — gün içi dakikalık
  barlarla ölçüldü (keşif #32: Almanya 2y 01.10 gün içi 17:30 = 3,0535 = günlük
  kapanış; Almanya 10y 3,5203 ↔ 3,5191; Fransa 10y 4,9256 ↔ 4,9282) ve ECB AAA
  eğrisiyle aynı gün korelasyonu 0,87–0,90. HAFTA SONU barı ATILIR: 564
  cuma–cumartesi çiftinin 550'sinde cumartesi farklı, yani cuma 17:30'dan
  sonraki kotasyonlar cumartesiye yazılıyor; bir Avrupa seansı değildir.
* TAŞINMIŞ İŞ GÜNÜ: Fransa ve Almanya bacaklarının İKİSİ DE bir önceki iş
  gününün değerini birebir taşıyorsa o gün piyasa kapalıdır (tatil) ve atılır.
  Tek bacağın aynı kalması bir ölçümdür.
* EUR/USD: ECB referans kuru (14:15 CET) — resmî, sabit saatli, 1999'dan;
  getirilerin Paris 17:30 kapanışına en yakın resmî kur. CNBC'nin döviz barı New
  York 17:00 kapanışıdır, Yahoo'nun D barı ise CNBC'nin D−1 barıyla eşleşiyor
  (seviye farkı medyanı 0,0008) — üç kaynak günü üç ayrı saatte etiketliyor. Bu
  yüzden kur–spread ilişkisi HAFTALIK (çarşamba–çarşamba) ölçülür; birkaç
  saatlik fark beş günlük pencerede küçük kalır ve New York kapanışıyla
  kurulan model sağlamlık sınaması olarak ayrıca koşulur. Çarşamba: cuma ve
  pazartesi tatillerinden en az etkilenen gün.
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
    # Yarım son hafta atılır: kova çarşambada kapanmamışsa (veri günü perşembe)
    # o "hafta" bir günlük değişimdir ve haftalık örnekleme girmez.
    if t.index[-1] < w.index[-1]:
        w = w.iloc[:-1]
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
    """Epizotta kurun hareketi: ölçülen ve modelin iki kanala atfettiği.

    Katsayılar epizottan ÖNCE (egitim_bas–kesim) haftalık örnekte tahmin edilir;
    aksi hâlde epizot kendi açıklamasını kendisi kurardı. Atıf SEVİYELERDEN
    kurulur (başlangıç günü → veri günü): haftalık kovaların sınırına bağlı
    kalmaz ve veri gününün kendisini de içerir. Sabit terim haftalık olduğu için
    hafta sayısıyla ölçeklenir."""
    d = haftalik()
    o = ols(d[(d.index >= egitim_bas) & (d.index <= kesim)], "fx", ["rd", "spr"])
    df = gunluk()
    fx = oku("eurusd_ecb.csv.gz")["eurusd_ecb"].dropna()
    rd = ((df["us2y"] - df["de2y"]) * 100).dropna()
    s = spread()
    t0, son = bas, SON_GUN
    hafta = _isgunu(t0, son) / 5
    kur = float(100 * (np.log(_once(fx, son)[1]) - np.log(_once(fx, t0)[1])))
    drd = _once(rd, son)[1] - _once(rd, t0)[1]
    dsp = _once(s, son)[1] - _once(s, t0)[1]
    return {"bas": _once(s, t0)[0], "son": _once(s, son)[0], "hafta": hafta, "kur_gercek": kur,
            "faiz_payi": o["b"]["rd"] * drd, "spread_payi": o["b"]["spr"] * dsp,
            "sabit_payi": o["sabit"] * hafta, "rd_toplam": drd, "spr_toplam": dsp,
            "artik": kur - (o["b"]["rd"] * drd + o["b"]["spr"] * dsp + o["sabit"] * hafta),
            "katsayi": o}


def hiz(vadeler=(10, 2)) -> dict:
    """Pencereli açılma (5 · 22 · 66 iş günü) ve bu büyüklüğün en son ne zaman
    görüldüğü. Pencereli ölçü tek günlük gösterge kaydırmalarına dayanıklıdır
    (CNBC serisinde gösterge tahvil değişimi tek günlük sıçrama üretebiliyor:
    28.11.2022 +16,2 bp, iki gün sonra −15,6 bp, ECB eğrisinde karşılığı yok);
    aynı epizodun kendi günleri sayılmaz (pencerenin 1,5 katı kadar geri gidilir)."""
    out = {}
    for v in vadeler:
        s = spread("fr", v)
        for n in (1, 5, 22, 66):
            g = s.diff(n).dropna()
            son = float(g.iloc[-1])
            once = g[g.index < g.index[-1] - pd.Timedelta(days=max(3, int(n * 1.5)))]
            ust = once[once >= son]
            out[f"{v}y_{n}"] = {"degisim": son, "son_gorulme": str(ust.index[-1].date()) if len(ust) else None}
    df = gunluk()
    rd = ((df["us2y"] - df["de2y"]) * 100).dropna()
    out["rd_son"] = float(rd.iloc[-1])
    out["rd_agustos26"] = _once(rd, "2026-08-26")[1]
    return out


# ── 6. ne kadar gidebilir: ölçülmüş dağılımlar ───────────────────────────
def ileri_dagilim(esik: float = 30.0, pencere: int = 22, ufuk: int = 22) -> dict:
    """Spread son `pencere` iş gününde ≥ `esik` bp açıldığında, sonraki `ufuk`
    iş gününde ne oldu? Örtüşen gözlemler bağımsız değildir: gözlemler arasında
    40 takvim gününden uzun boşluk yeni bir KÜME açar ve kümeler adıyla yazılır
    — dağılımın hangi dönemden geldiği görünmezse tek bir epizot bütün oranı
    taşıyabilir."""
    s = spread()
    g = s.diff(pencere)
    ileri = s.shift(-ufuk) - s
    k = pd.DataFrame({"g": g, "i": ileri}).dropna()
    sec = k[k["g"] >= esik]
    kumeler, onceki = [], None
    for t, r in sec.iterrows():
        if onceki is None or (t - onceki).days > 40:
            kumeler.append([])
        kumeler[-1].append((t, r["g"], r["i"]))
        onceki = t
    kume = [{"bas": str(c[0][0].date()), "son": str(c[-1][0].date()), "n": len(c),
             "azami_acilma": float(max(x[1] for x in c)),
             "ileri_min": float(min(x[2] for x in c)), "ileri_maks": float(max(x[2] for x in c)),
             "daha_acilan": int(sum(1 for x in c if x[2] > 0))} for c in kumeler]
    return {"esik": esik, "pencere": pencere, "ufuk": ufuk, "gozlem": int(len(sec)), "epizot": len(kume),
            "kumeler": kume,
            "daha_acildi_payi": float((sec["i"] > 0).mean() * 100) if len(sec) else None,
            "daha_acilan_kume": int(sum(1 for c in kume if c["daha_acilan"] > 0)),
            "medyan": float(sec["i"].median()) if len(sec) else None,
            "p10": float(sec["i"].quantile(0.1)) if len(sec) else None,
            "p90": float(sec["i"].quantile(0.9)) if len(sec) else None,
            "bugunku_acilma": float(g.iloc[-1])}


def oynaklik_bandi(gun: int = 20, ufuk: int = 22) -> dict:
    """Son `gun` iş gününün gerçekleşen günlük spread oynaklığı ve onun ±1,96σ√ufuk
    bandı. Tahmin değil, ölçek: bugünkü hızla bir ayda ne kadar yer değiştirir."""
    d = spread().diff().dropna()
    sig = float(d.iloc[-gun:].std(ddof=1))
    sig_uzun = float(d[d.index >= "2013-01-01"].std(ddof=1))
    return {"sigma_gunluk": sig, "sigma_2013_sonrasi": sig_uzun, "oran": sig / sig_uzun,
            "bant_1a": 1.96 * sig * np.sqrt(ufuk), "spread": float(spread().iloc[-1])}


# ── 7. gün içi: 1 Ekim ────────────────────────────────────────────────────
PARIS = "Europe/Paris"


@lru_cache(maxsize=None)
def gun_ici() -> pd.DataFrame:
    """Dakikalık son kotasyonlar, Paris saatine çevrilmiş; her bacak kendi son
    kotasyonunu taşır (ileri doldurma yalnız AYNI GÜN içinde)."""
    g = oku("cnbc_gun_ici.csv.gz").copy()
    g.index = g.index.tz_localize("UTC").tz_convert(PARIS)
    g = g.sort_index()
    gun = g.index.date
    g = g.groupby(gun).ffill()
    g["spr"] = (g["fr10y"] - g["de10y"]) * 100
    g["ispr"] = (g["it10y"] - g["de10y"]) * 100
    g["spr2"] = (g["fr2y"] - g["de2y"]) * 100
    g["ispr2"] = (g["it2y"] - g["de2y"]) * 100
    g["rd"] = (g["us2y"] - g["de2y"]) * 100
    return g


def gun_ici_pencere(gun: str = SON_GUN, bas: str = "15:30", son: str = "17:30") -> dict:
    """Bir gün içi pencerede farkların, faiz farkının ve kurun değişimi.

    Pencere VERİYE BAKILARAK seçildi (1 Ekim'de açılmanın başladığı saat →
    Avrupa kapanışı): bu bir sınama değil, bir olayın betimlemesidir. Faiz
    farkının kımıldamadığı bir pencerede kurun hareketi, faiz kanalına
    atfedilemeyecek kısmı GÖRÜNÜR kılar; büyüklüğü tek bir günden genellenmez."""
    g = gun_ici()
    gg = g[g.index.date == pd.Timestamp(gun).date()].between_time("08:00", "17:30")
    a = gg[gg.index.strftime("%H:%M") <= bas].iloc[-1]
    b = gg[gg.index.strftime("%H:%M") <= son].iloc[-1]
    out = {"gun": gun, "bas": bas, "son": son}
    for k in ("spr", "ispr", "spr2", "ispr2", "rd"):
        out[k] = {"bas": float(a[k]), "son": float(b[k]), "degisim": float(b[k] - a[k])}
    for k in ("de2y", "us2y", "de10y", "fr10y", "it2y"):
        out[k] = {"bas": float(a[k]), "son": float(b[k]), "degisim_bp": float((b[k] - a[k]) * 100)}
    out["eurusd"] = {"bas": float(a["eurusd"]), "son": float(b["eurusd"]),
                     "degisim_yuzde": float(100 * (np.log(b["eurusd"]) - np.log(a["eurusd"])))}
    return out


def gun_ici_ozet(gun: str = SON_GUN, saatler=("09:00", "14:15", "17:30")) -> dict:
    """Bir günün seçili saatlerindeki fark ve kur; 15 dakikalık değişimlerin
    eş hareketi. Avrupa seansı: 08:00–17:30 Paris."""
    g = gun_ici()
    gg = g[(g.index.date == pd.Timestamp(gun).date())]
    gg = gg.between_time("08:00", "17:30")
    out = {"gun": gun, "dakika": int(len(gg))}
    for s in saatler:
        r = gg[gg.index.strftime("%H:%M") <= s].iloc[-1]
        out[s] = {k: float(r[k]) for k in ("spr", "ispr", "spr2", "ispr2", "eurusd", "de10y", "fr10y", "de2y",
                                           "us2y", "rd")}
    zt = gg["spr"].idxmax()
    out["zirve"] = {"saat": zt.strftime("%H:%M"), "spr": float(gg["spr"].max())}
    on5 = gg.resample("15min").last().dropna(subset=["spr", "eurusd"])
    d = pd.DataFrame({"spr": on5["spr"].diff(), "fx": np.log(on5["eurusd"]).diff() * 100,
                      "ispr": on5["ispr"].diff()}).dropna()
    out["on5_n"] = int(len(d))
    out["on5_korelasyon"] = float(d["spr"].corr(d["fx"]))
    out["on5_egim"] = float(np.polyfit(d["spr"], d["fx"], 1)[0]) if len(d) > 3 else None
    return out


def gun_ici_bes_gun() -> dict:
    """Arşivdeki beş günün tamamında 15 dakikalık değişimlerin eş hareketi
    (Avrupa seansı); her gün ayrı ve birleşik."""
    g = gun_ici()
    parca, gunluk_k = [], {}
    for gun in sorted(set(g.index.date)):
        gg = g[g.index.date == gun].between_time("08:00", "17:30")
        on5 = gg.resample("15min").last().dropna(subset=["spr", "eurusd"])
        d = pd.DataFrame({"spr": on5["spr"].diff(), "fx": np.log(on5["eurusd"]).diff() * 100}).dropna()
        if len(d) >= 10:
            gunluk_k[str(gun)] = {"n": int(len(d)), "korelasyon": float(d["spr"].corr(d["fx"]))}
            parca.append(d)
    b = pd.concat(parca)
    return {"gunler": gunluk_k, "n": int(len(b)), "korelasyon": float(b["spr"].corr(b["fx"])),
            "egim": float(np.polyfit(b["spr"], b["fx"], 1)[0])}


# ── 8. kayan katsayı ──────────────────────────────────────────────────────
def kayan_katsayi(pencere: int = 104) -> pd.DataFrame:
    """`pencere` haftalık kayan pencerede EUR/USD'nin faiz farkı ve OAT–Bund
    farkına duyarlılığı (10 bp başına %), Newey–West ±2 s.h. bandıyla."""
    d = haftalik()
    sat = []
    for i in range(pencere, len(d) + 1):
        dd = d.iloc[i - pencere:i]
        o = ols(dd, "fx", ["rd", "spr"])
        b, t = o["b"]["spr"] * 10, o["t"]["spr"]
        se = abs(b / t) if t else float("nan")
        sat.append({"tarih": dd.index[-1], "spr": b, "alt": b - 2 * se, "ust": b + 2 * se,
                    "rd": o["b"]["rd"] * 10})
    return pd.DataFrame(sat).set_index("tarih")


def epizot_yollari(gun: int = 160) -> dict:
    """Her epizotta başlangıçtan itibaren iş günü ekseninde farkın yolu."""
    s = spread()
    out = {}
    for ad, a, b, _ in EPIZOTLAR:
        p = s[s.index >= a].iloc[:gun + 1]
        out[ad] = (p - p.iloc[0]).tolist()
    return out


# ── 10. öbür piyasalar ────────────────────────────────────────────────────
PIYASA = [("eurchf", "EUR/CHF"), ("eurjpy", "EUR/JPY"), ("eurgbp", "EUR/GBP"), ("dxy", "Dolar endeksi (DXY)"),
          ("vix", "VIX"), ("sx5e", "Euro Stoxx 50"), ("cac", "CAC 40"), ("dax", "DAX"),
          ("bnp", "BNP Paribas"), ("socgen", "Société Générale"), ("cagri", "Crédit Agricole")]


def piyasalar(bas: str = "2026-08-26") -> list[dict]:
    """Epizot penceresinde öbür piyasaların yüzde değişimi (Yahoo kapanışı).

    Döviz çaprazlarında Yahoo'nun günlük etiketi bir gün kayık (ölçüldü); bu
    yüzden yalnız ÇOK HAFTALIK değişim yazılır, günlük değişim yazılmaz."""
    y = oku("yahoo_gunluk.csv.gz")
    out = []
    for k, ad in PIYASA:
        if k not in y:
            continue
        s = y[k].dropna()
        s = s[s.index <= SON_GUN]
        out.append({"kod": k, "ad": ad, "son": float(s.iloc[-1]), "son_gun": str(s.index[-1].date()),
                    "degisim": float(100 * (s.iloc[-1] / _once(s, bas)[1] - 1)),
                    "degisim_haziran": float(100 * (s.iloc[-1] / _once(s, "2026-06-30")[1] - 1))})
    return out


def kur_ozeti() -> dict:
    fx = oku("eurusd_ecb.csv.gz")["eurusd_ecb"].dropna()
    fx = fx[fx.index <= SON_GUN]
    y26 = fx[fx.index >= "2026-01-01"]
    once = fx[fx.index < fx.index[-1]]
    alt = once[once <= fx.iloc[-1]]
    return {"son": float(fx.iloc[-1]), "gun": str(fx.index[-1].date()),
            "yil_zirve": float(y26.max()), "yil_zirve_gun": str(y26.idxmax().date()),
            "yil_dip": float(y26.min()), "yil_dip_gun": str(y26.idxmin().date()),
            "son_gorulme": str(alt.index[-1].date()) if len(alt) else None,
            "agustos26": _once(fx, "2026-08-26")[1], "haziran": _once(fx, "2026-06-30")[1],
            "yb": _once(fx, "2025-12-31")[1], "onceki_gun": float(fx.iloc[-2]),
            "zirveden": float(100 * (np.log(fx.iloc[-1]) - np.log(y26.max())))}


def ecb_faiz() -> list[dict]:
    d = oku("ecb_dfr.csv.gz")["dfr"]
    d = d[d.index <= SON_GUN]
    ch = d[d.diff() != 0]
    return [{"gun": str(t.date()), "dfr": float(v)} for t, v in ch[ch.index >= "2024-01-01"].items()]


# ── 9. ölçüm dosyası ──────────────────────────────────────────────────────
def _yuvarla(x, b: int = 6):
    if isinstance(x, float):
        return None if (x != x) else round(x, b)
    if isinstance(x, (np.floating,)):
        return _yuvarla(float(x), b)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, dict):
        return {str(k): _yuvarla(v, b) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_yuvarla(v, b) for v in x]
    return x


def _seri(s: pd.Series, b: int = 4) -> dict:
    s = s.dropna()
    return {"t": [str(t.date()) for t in s.index], "v": [round(float(v), b) for v in s.values]}


def hepsi() -> dict:
    """Yazının ve figürlerin bütün sayıları. `veri/olcum.json` olarak yazılır;
    yayın kapısı (dogrula.py) ve çizim (sekil.py) yalnız bunu okur."""
    s = spread()
    df = gunluk()
    D = duyarlilik()
    kk = kayan_katsayi()
    gi = gun_ici()
    gg = gi[gi.index.date == pd.Timestamp(SON_GUN).date()].between_time("07:30", "19:00")
    gg15 = gg.resample("15min").last()
    out = {
        "son_gun": SON_GUN,
        "arsiv": {ad: v["sha256"] for ad, v in kunye()["dosyalar"].items()},
        "arsiv_olusturma": kunye()["olusturma"],
        "temizlik": temizlik_sayimi(),
        "seviye": seviye_ozeti(),
        "kaynak": kaynak_sinamasi(),
        "akranlar": akranlar(),
        "fransa_italya": fransa_italya(),
        "egri": egri(),
        "hiz": hiz(),
        "epizotlar": epizotlar(),
        "duyarlilik": D,
        "kanallar": kanallar(),
        "orneklem_disi": {"2004_2023": orneklem_disi("2023-12-31", "2004-01-01"),
                          "2013_2023": orneklem_disi("2023-12-31", "2013-01-01"),
                          "2004_2019": orneklem_disi("2019-12-31", "2004-01-01")},
        "atif": {b: {k: v for k, v in epizot_atfi(bas=b).items()}
                 for b in ("2026-08-26", "2026-06-30", EPIZOT_BAS)},
        "ileri": [ileri_dagilim(30, 22, 22), ileri_dagilim(30, 22, 66), ileri_dagilim(40, 22, 22),
                  ileri_dagilim(50, 22, 22)],
        "oynaklik": oynaklik_bandi(),
        "gun_ici": gun_ici_ozet(),
        "gun_ici_pencere": gun_ici_pencere(),
        "gun_ici_bes_gun": gun_ici_bes_gun(),
        "piyasalar": piyasalar(),
        "kur": kur_ozeti(),
        "ecb_faiz": ecb_faiz(),
        "kayan": {"son": float(kk["spr"].iloc[-1]), "son_alt": float(kk["alt"].iloc[-1]),
                  "son_ust": float(kk["ust"].iloc[-1]), "son_tarih": str(kk.index[-1].date()),
                  "ort_2013_2019": float(kk.loc["2013":"2019", "spr"].mean()),
                  "ort_2024_sonra": float(kk.loc["2024":, "spr"].mean())},
        "seriler": {
            "spread": _seri(s, 2),
            "spread_it": _seri(spread("it"), 2),
            "fr10": _seri(df["fr10y"], 4), "de10": _seri(df["de10y"], 4),
            "kayan": {"t": [str(t.date()) for t in kk.index], "spr": [round(float(v), 4) for v in kk["spr"]],
                      "alt": [round(float(v), 4) for v in kk["alt"]], "ust": [round(float(v), 4) for v in kk["ust"]]},
            "epizot_yollari": epizot_yollari(),
            "gun_ici": {"t": [t.strftime("%H:%M") for t in gg15.index],
                        "spr": [None if v != v else round(float(v), 2) for v in gg15["spr"]],
                        "ispr2": [None if v != v else round(float(v), 2) for v in gg15["ispr2"]],
                        "spr2": [None if v != v else round(float(v), 2) for v in gg15["spr2"]],
                        "eurusd": [None if v != v else round(float(v), 5) for v in gg15["eurusd"]]},
            "ileri_noktalar": _ileri_noktalar(),
        },
    }
    return _yuvarla(out)


def _ileri_noktalar(esik: float = 30.0, pencere: int = 22, ufuk: int = 22) -> dict:
    s = spread()
    k = pd.DataFrame({"g": s.diff(pencere), "i": s.shift(-ufuk) - s}).dropna()
    sec = k[k["g"] >= esik]
    return {"t": [str(t.date()) for t in sec.index], "g": [round(float(v), 2) for v in sec["g"]],
            "i": [round(float(v), 2) for v in sec["i"]]}


def main() -> int:
    o = hepsi()
    (VERI / "olcum.json").write_text(json.dumps(o, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                     encoding="utf-8")
    sv = o["seviye"]
    print(f"olcum.json yazıldı · veri günü {o['son_gun']} · fark {sv['spread']:.1f} bp · "
          f"{len(o['seriler']['spread']['t'])} gün")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
