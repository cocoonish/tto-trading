#!/usr/bin/env python3
"""FX haber endeksi — duman sinamasi (guncelle.py her kosudan ONCE koşturur).

Ag yok, canli dosya yok (her madde kendi fiksturunu kurar), saat acik
verilir; 30 saniyeyi asarsa kendisi duser. Her madde gercekten yapilmis ya da
yapilmasi kolay bir kusurun sinifini kapatir:

  1  hizli pencere eski pencereyle BIT BIT ayni (192 kombinasyon; mikrosaniye,
     saat dilimsiz ve bozuk damga, kopya makale, −0,0 skor, uca denk referans)
  2  cekirdekte numpy'nin vektor exp/tanh/sqrt/pow'u ve .timestamp() YOK (cikti
     makineye gore degisirdi; esdegerlik o zaman kosucuya bagli kalirdi)
  3  saat dilimsiz referans iki yolda da HATA (eskisi sessizce 0,0 donuyordu)
  4  kapanis hizasi: kapanistan bir saniye sonraki haber o gunun degerine girmez
  5  fiyat: dovizde gunluk bara dusulmez; hafta sonu ve kapanmamis gun duser;
     doviz disi her sembolun kapanis ani tanimli
  6  ileri getiri ileri, geri getiri geri
  7  arsiv: haftasinin disina dusen damga atilir ve sayilir; tahvil tersleme
     onbellegi degistirmez; kapanmamis hafta girmez
  8  plasebo p asla sifir degil: (1+b)/(1+K)
  9  kalibrasyon: izgarada gecikme yok, varsayilan izgarada; egitimin son h gunu
     atilir; gurultu → "öngörmüyor" ve varsayilan; ekilmis sinyal → aile gecer;
     rakibin altinda kalan varlik kendi parametresini ALAMAZ
 10  parametre dosyasi: 15 varlik, her biri izgaranin butun anahtarlarini tasir
 11  kalibrasyon kimligi saniye cozunurlugunde: ayni kalibrasyonun mikrosaniye
     farkli damgalari tek kimliktir; ayni gune dusen iki kimlik saatiyle yazilir
 12  ozet: ayni kalibrasyonda hareket sayisaldir; kalibrasyon degistiyse hareket
     bos ve sebebi yazili; sayfanin cagirdigi HER anahtar ozette (MDX'ten)
 13  kalibrasyon girisi haber cekmez, FinBERT yuklemez, eski fiyati okumaz
"""

from __future__ import annotations

import ast
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import warnings
from datetime import datetime, timedelta, timezone

warnings.filterwarnings("ignore", category=RuntimeWarning)
BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(os.path.dirname(BURASI))
sys.path.insert(0, BURASI)
sys.path.insert(0, os.path.join(KOK, "ortak"))

import numpy as np            # noqa: E402
import pandas as pd           # noqa: E402

import config                 # noqa: E402
import correlation_optimizer as co  # noqa: E402
import fiyat                  # noqa: E402
import hizali                 # noqa: E402
import index_builder as ib    # noqa: E402
import kalibrasyon_damga as kd  # noqa: E402

T0 = time.time()
SURE = 90.0
SIMDI = datetime(2026, 10, 3, 15, 0, tzinfo=timezone.utc)
dusen: list[str] = []
gecen = 0


def sina(ad: str, kosul, ayrinti: str = "") -> None:
    global gecen
    try:
        ok = bool(kosul() if callable(kosul) else kosul)
    except Exception as exc:  # noqa: BLE001
        ok, ayrinti = False, f"{type(exc).__name__}: {exc}"
    if ok:
        gecen += 1
    else:
        dusen.append(f"{ad}" + (f" — {ayrinti}" if ayrinti else ""))


def bit(v: float) -> bytes:
    return struct.pack("<d", float(v))


# ── fikstur: makaleler ─────────────────────────────────────────────────────────
def makaleler(n=900, tohum=3, bas=datetime(2026, 8, 1, tzinfo=timezone.utc), gun=40):
    r = random.Random(tohum)
    out = []
    for _ in range(n):
        t = bas + timedelta(seconds=r.randint(0, gun * 86400), microseconds=r.randint(0, 999999))
        u = r.random()
        pub = t.isoformat() if u > 0.03 else (t.replace(tzinfo=None).isoformat() if u > 0.01 else "bozuk")
        a = {"published": pub, "score": r.choice([round(r.uniform(-1, 1), 4), -0.0, 0.0, 0.31, -0.3])}
        if r.random() < 0.3:
            a["source_weight"] = r.choice([0.7, 0.9, 1.0])
        out.append(a)
    out += out[:15]                       # haftalar arasi kopya
    out.append({"score": 0.5})            # damgasiz
    return out


# 1 ─ hizli pencere = eski pencere, bit bit
def m1():
    arts = makaleler()
    dizi = ib.MakaleDizisi(arts)
    refs = [datetime(2026, 8, 1, tzinfo=timezone.utc) + timedelta(days=d, hours=h)
            for d in (0, 6, 7, 15, 33, 41) for h in (0, 21)]
    ozel = [datetime.fromisoformat(a["published"]) for a in arts[:6]
            if isinstance(a.get("published"), str) and a["published"][:2] == "20" and "+" in a["published"]]
    refs += ozel + [t + timedelta(days=7) for t in ozel]
    fark = n = 0
    for p in co.izgara():
        for r in refs:
            a = ib._compute_index_value(arts, p, r)
            b = ib._compute_index_value(arts, p, r, dizi=dizi)
            n += 1
            if bit(a[0]) != bit(b[0]) or a[1] != b[1]:
                fark += 1
    return fark == 0 and n > 1000, f"{fark}/{n} fark"


# 2 ─ cekirdekte vektor matematik yok
YASAK_CAGRI = {("np", "exp"), ("np", "tanh"), ("np", "sqrt"), ("np", "power"), ("np", "round")}
CEKIRDEK = {"apply_transform", "compute_time_weights", "aggregate_weighted_mean",
            "aggregate_bull_bear_ratio", "aggregate_intensity_ratio",
            "aggregate_directional_strength", "compute_momentum", "_compute_index_value",
            "_pencere", "pencere", "_mikro"}


def m2():
    agac = ast.parse(open(os.path.join(BURASI, "index_builder.py"), encoding="utf-8").read())
    bulgu = []
    for f in ast.walk(agac):
        if isinstance(f, ast.FunctionDef) and f.name in CEKIRDEK:
            for d in ast.walk(f):
                if isinstance(d, ast.Attribute) and isinstance(d.value, ast.Name):
                    if (d.value.id, d.attr) in YASAK_CAGRI:
                        bulgu.append(f"{f.name}: {d.value.id}.{d.attr}")
                if isinstance(d, ast.Attribute) and d.attr == "timestamp":
                    bulgu.append(f"{f.name}: .timestamp()")
    return not bulgu, "; ".join(bulgu)


# 3 ─ saat dilimsiz referans iki yolda da hata
def m3():
    arts = makaleler(50)
    dizi = ib.MakaleDizisi(arts)
    hata = 0
    for d in (None, dizi):
        try:
            ib._compute_index_value(arts, dict(config.DEFAULT_PARAMS), datetime(2026, 8, 10), dizi=d)
        except ValueError:
            hata += 1
    return hata == 2, f"{hata}/2 yol hata verdi"


# 4 ─ kapanis hizasi
def m4():
    kap = pd.Timestamp("2026-09-30 21:00", tz="UTC")
    arts = [{"published": (kap - pd.Timedelta(hours=3)).isoformat(), "score": -0.8},
            {"published": kap.isoformat(), "score": 0.6},
            {"published": (kap + pd.Timedelta(seconds=1)).isoformat(), "score": 1.0}]
    S = hizali.ham_seri(ib.MakaleDizisi(arts), dict(config.DEFAULT_PARAMS),
                        pd.Series([kap], index=[pd.Timestamp("2026-09-30")]))
    v, n = ib._compute_index_value(arts[:2], dict(config.DEFAULT_PARAMS), kap.to_pydatetime())
    return abs(S.iloc[0] - v) < 1e-15 and n == 2, f"S {S.iloc[0]} · iki makaleyle {v}"


# 5 ─ fiyat
def m5():
    fiyat._BELLEK.clear()
    out = []
    g = pd.Series([1.0, 1.1, 1.2, 1.3], index=pd.to_datetime(["2026-09-25", "2026-09-26",
                                                              "2026-09-28", "2026-09-29"]))
    f = fiyat.gunluk_kapanislar("^GSPC", gunluk=g, simdi=datetime(2026, 9, 29, 19, 0, tzinfo=timezone.utc),
                                gun=None)
    out.append(list(f.seri.index.strftime("%d")) == ["25", "28"])          # cumartesi ve kapanmamis gun
    try:
        import fx_kapanis
        es = fx_kapanis.yfinance_saatlik
        fx_kapanis.yfinance_saatlik = lambda *a, **k: {}
        try:
            fiyat.doviz_kapanislari("EURUSD=X", simdi=SIMDI)
            out.append(False)                                               # gunluk bara dusmus olurdu
        except RuntimeError:
            out.append(True)
        finally:
            fx_kapanis.yfinance_saatlik = es
    except ImportError:
        out.append(False)
    eksik = [c["ticker"] for c in config.ASSETS.values()
             if not fiyat.doviz_mu(c["ticker"]) and c["ticker"] not in fiyat.KAPANIS]
    out.append(not eksik)
    idx = pd.date_range("2026-09-28 00:00", "2026-09-30 23:00", freq="h", tz="UTC")
    fx = fiyat.doviz_kapanislari("EURUSD=X", saatlik=pd.Series(np.arange(len(idx), dtype=float), index=idx),
                                 simdi=datetime(2026, 9, 30, 22, 0, tzinfo=timezone.utc), gun=None)
    out.append(fx.kaynak == "saatlik" and float(fx.seri.iloc[0]) == 20.0          # 21:00 UTC kapanisi
               and str(fx.an.iloc[0]) == "2026-09-28 21:00:00+00:00")
    return all(out), f"{out} eksik tablo: {eksik}"


# 6 ─ getiri yonu
def m6():
    s = pd.Series([1.0, 2.0, 4.0, 8.0])
    return (fiyat.ileri_getiri(s, 1).tolist()[:3] == [1.0, 1.0, 1.0]
            and math.isnan(fiyat.ileri_getiri(s, 1).iloc[-1])
            and math.isnan(fiyat.geri_getiri(s, 1).iloc[0])), ""


# 7 ─ arsiv
def m7():
    hafta = "2026-09-27"                      # pazar
    kay = {"UST2Y": {hafta: {"articles": [
        {"published": "2026-09-23T10:00:00+00:00", "score": 0.4},
        {"published": "2026-10-01T10:00:00+00:00", "score": 0.9},     # cekim ani: haftasinin disi
        {"published": "2026-09-21T00:00:00+00:00", "score": -0.2},
        {"published": "2026-09-22T09:00:00+00:00"}]},                 # skorsuz
        "2026-10-04": {"articles": [{"published": "2026-10-02T10:00:00+00:00", "score": 0.1}]}}}
    mk, abas, ason, den = hizali.arsiv(kay, "UST2Y", simdi=SIMDI)
    return (len(mk) == 2 and mk[0]["score"] == -0.4 and kay["UST2Y"][hafta]["articles"][0]["score"] == 0.4
            and den["hafta_disi_atilan"] == 1 and den["skorsuz"] == 1 and den["hafta"] == 1
            and ason.date().isoformat() == hafta), f"{len(mk)} {den}"


# 8 ─ plasebo p
def m8():
    return (hizali.p_degeri(0.9, np.array([0.1, 0.2, 0.3])) == 0.25
            and hizali.p_degeri(0.15, np.array([0.1, 0.2, 0.3])) == 0.75), ""


# 9 ─ kalibrasyon
def _veri(anahtar, sinyal: float, tohum: int, n=200, grid_n=4, rakip_guclu=False):
    rng = np.random.default_rng(tohum)
    gun = pd.bdate_range("2025-10-01", periods=n)
    ton = np.zeros(n)
    for i in range(1, n):
        ton[i] = 0.8 * ton[i - 1] + rng.normal()
    ret = rng.normal(0, 1, n + 6)
    ret[1:n + 1] += sinyal * ton
    px = pd.Series(np.exp(np.cumsum(ret * 0.01)))
    F5 = (px.shift(-5) / px - 1).to_numpy()[:n]
    F1 = (px.shift(-1) / px - 1).to_numpy()[:n]
    M = np.vstack([ton + rng.normal(0, 0.3 + 0.3 * j, n) for j in range(grid_n)])
    # Guclu rakip hedefin KENDISINI tasir: kural "aday rakibi gecemezse ongormuyor"
    # bir sansa degil yapiya karsi sinansin (rakip = ton iken katlara gore z'lenen
    # gurultulu bir aday tesadufen ustte kalabiliyordu).
    rakip = np.vstack([np.nan_to_num(F5) + (rng.normal(0, 1e-4, n) if rakip_guclu else 0) if rakip_guclu
                       else rng.normal(size=n) for _ in range(2)])
    return {"anahtar": anahtar, "M": M, "gunler": gun, "hedef": {5: F5, 1: F1},
            "tepki": {5: (px / px.shift(5) - 1).to_numpy()[:n], 1: (px / px.shift(1) - 1).to_numpy()[:n]},
            "rakip": rakip, "denetim": {}, "fiyat_tanim": "test", "arsiv": ["a", "b"]}


def _veri_donus(anahtar, tohum, n=200, grid_n=4):
    """Fiyat GERI DONUYOR ve endeks yalniz gecmis fiyati ters isaretle tasiyor:
    adaylar rakibin DONUS adaylarinin ta kendisi. Devam adaylari egitimde eksi
    ρ verdigi icin rakip her katta adayla AYNI seriyi secer, ornek disi ρ'lar
    birebir esit cikar ve "rakibi gecti" (kesin buyuk) saglanamaz. Rakip yalniz
    devam isaretini tasisaydi ρ'su eksi kalir ve aday kurali gecerdi."""
    rng = np.random.default_rng(tohum)
    gun = pd.bdate_range("2025-10-01", periods=n)
    r = np.zeros(n + 6)
    for i in range(1, n + 6):
        r[i] = -0.45 * r[i - 1] + rng.normal(0, 0.01)
    px = pd.Series(np.exp(np.cumsum(r))[:n], index=gun)
    rakip = co.fiyat_rakibi(px, gun)
    lr = np.log(px).diff()                           # adaylari rakipten BAGIMSIZ kur
    M = np.vstack([-lr.ewm(halflife=hl, min_periods=hl).mean().to_numpy(float)
                   for hl in co.FIYAT_YARIOMUR[:grid_n]])
    F5 = (px.shift(-5) / px - 1).to_numpy()
    F1 = (px.shift(-1) / px - 1).to_numpy()
    return {"anahtar": anahtar, "M": M, "gunler": gun, "hedef": {5: F5, 1: F1},
            "tepki": {5: (px / px.shift(5) - 1).to_numpy(), 1: (px / px.shift(1) - 1).to_numpy()},
            "rakip": rakip, "denetim": {}, "fiyat_tanim": "test", "arsiv": ["a", "b"]}


def _grid4():
    g = co.izgara()
    dv = co.varsayilan_sira(g)
    return [g[dv]] + [p for i, p in enumerate(g) if i != dv][:3]


def m9():
    g = co.izgara()
    out = [all("lag_days" not in co.config.PARAM_GRID for _ in [0]), co.varsayilan_sira(g) >= 0,
           len(g) == np.prod([len(v) for v in config.PARAM_GRID.values()])]
    # egitimin son h gunu atilir
    uzun = []
    co.yuruyen(np.random.default_rng(1).normal(size=(2, 160)), np.random.default_rng(2).normal(size=160), 5,
               lambda x, y, asgari=20: (uzun.append(len(x)), 0.0)[1])
    out.append(uzun[0] == co.ILK_EGITIM - 5)
    g4 = _grid4()
    anahtarlar = list(config.ASSETS)[:4]
    p, k = co.kalibre_et([_veri(a, 0.0, 10 + i) for i, a in enumerate(anahtarlar)], g4)
    out.append(all(p[a]["hukum"] == "öngörmüyor" for a in anahtarlar)
               and all(p[a]["params"]["aggregation"] == config.DEFAULT_PARAMS["aggregation"] for a in anahtarlar))
    p, k = co.kalibre_et([_veri(a, 1.5, 20 + i) for i, a in enumerate(anahtarlar)], g4)
    out.append(k["aile"]["5"]["p"] <= co.ESIK_P and all(p[a]["hukum"] == "öngörüyor" for a in anahtarlar))
    p, k = co.kalibre_et([_veri(a, 1.5, 20 + i, rakip_guclu=True) for i, a in enumerate(anahtarlar)], g4)
    out.append(all(p[a]["hukum"] == "öngörmüyor" for a in anahtarlar))     # rakip ayni bilgiyi tasiyor
    # Rakip iki isareti tasir: devam ve donus (ters isaret) adaylari.
    px = pd.Series(np.exp(np.cumsum(np.random.default_rng(3).normal(0, 0.01, 60))),
                   index=pd.bdate_range("2026-01-01", periods=60))
    rk = co.fiyat_rakibi(px, px.index)
    m = len(co.FIYAT_YARIOMUR)
    out.append(rk.shape[0] == 2 * m and np.allclose(rk[m:], -rk[:m], equal_nan=True))
    # Fiyat donuyor ve endeks yalniz gecmis fiyati ters isaretle tasiyor: aday ileriyi
    # "ongorur" ama bilgisi haberden degil fiyatin kendi donusunden gelir → ongormuyor.
    dv = [_veri_donus(a, 50 + i) for i, a in enumerate(anahtarlar)]
    p, k = co.kalibre_et(dv, g4)
    out.append(all(p[a]["hukum"] == "öngörmüyor" for a in anahtarlar))
    # Karsi sinama: ayni veride rakip YALNIZ devam isaretini tasisaydi kural en az
    # bir varligi "ongoruyor" sayardi — madde iki isaretin farkini gercekten olcuyor.
    for v in dv:
        v["rakip"] = v["rakip"][:len(co.FIYAT_YARIOMUR)]
    p, _ = co.kalibre_et(dv, g4)
    out.append(any(p[a]["hukum"] == "öngörüyor" for a in anahtarlar))
    return all(out), str(out)


# 10 ─ parametre dosyasi
def m10():
    g4 = _grid4()
    p, _ = co.kalibre_et([_veri(a, 0.0, 30 + i) for i, a in enumerate(config.ASSETS)], g4)
    d = tempfile.mkdtemp()
    try:
        yol = os.path.join(d, "p.json")
        json.dump(p, open(yol, "w", encoding="utf-8"))
        es, config.OPTIMIZED_PARAMS = config.OPTIMIZED_PARAMS, yol
        try:
            lp = co.load_optimized_params()
        finally:
            config.OPTIMIZED_PARAMS = es
        anahtar = set(config.PARAM_GRID) | {"lag_days"}
        return (set(lp) == set(config.ASSETS) and all(anahtar <= set(v) for v in lp.values())
                and len({v["timestamp"] for v in p.values()}) == 1), f"{len(lp)} varlık"
    finally:
        shutil.rmtree(d, ignore_errors=True)


# 11 ─ kalibrasyon kimligi
def m11():
    d = tempfile.mkdtemp()
    try:
        yol = os.path.join(d, "p.json")
        json.dump({"A": {"params": {}, "timestamp": "2026-07-22T19:23:33.628199+00:00"},
                   "B": {"params": {}, "timestamp": "2026-07-22T19:23:33.628227+00:00"}}, open(yol, "w"))
        g = kd.guncel(yol)
        eski = {"timestamp": "2026-08-04T20:05:21.640171+00:00"}
        yeni = {"timestamp": "2026-10-02T17:58:45+00:00", "kalibrasyon": g}
        ayni_gun = kd.degisim_metni("2026-10-03T09:00:00", "2026-10-03T17:30:00")
        return (kd.kimlik(eski) == kd.kimlik(yeni) == g and "09:00" in ayni_gun
                and kd.kimlik({"timestamp": "2026-07-15T18:32:02+00:00"}) == kd.GECMIS[0]), f"{g} · {ayni_gun}"
    finally:
        shutil.rmtree(d, ignore_errors=True)


# 12 ─ ozet: kara kutu, gecici dizinde
def _ozet_kos(tarihce, karne, sekil_ozet=True):
    d = tempfile.mkdtemp()
    try:
        for f in ("ozet_uret.py", "kalibrasyon_damga.py", "config.py"):
            shutil.copy(os.path.join(BURASI, f), d)
        os.makedirs(os.path.join(d, "data"))
        os.makedirs(os.path.join(d, "cikti"))
        json.dump(tarihce, open(os.path.join(d, "data", "index_history.json"), "w"))
        json.dump({k: {"articles": [{"published": "2026-10-02T10:00:00+00:00", "score": 0.1}] * 30}
                   for k in config.ASSETS}, open(os.path.join(d, "data", "sentiment_scores.json"), "w"))
        json.dump(karne, open(os.path.join(d, "data", "kalibrasyon_karne.json"), "w"))
        json.dump({k: {"params": dict(config.DEFAULT_PARAMS), "timestamp": karne["olcum_ani"]}
                   for k in config.ASSETS}, open(os.path.join(d, "data", "optimized_params.json"), "w"))
        json.dump({"as_of": "2026-09-27", "n_assets": 15}, open(os.path.join(d, "cikti", "rejim_ozet.json"), "w"))
        if sekil_ozet:
            json.dump({"sekil04": {"varlik": {k: {"rho": 0.1 * (i % 3 - 1), "n": 50, "p": 0.3}
                                              for i, k in enumerate(config.ASSETS)}, "uc": "2026-09-25"},
                       "sekil05": {"ort": {k: {"1g": 0.01, "5g": -0.02, "bant_disi_5g": 0.05}
                                           for k in config.ASSETS}, "uc": "2026-09-24"}},
                      open(os.path.join(d, "cikti", "sekil_ozet.json"), "w"))
        env = dict(os.environ, PYTHONPATH=os.path.join(KOK, "ortak"))
        r = subprocess.run([sys.executable, "-B", "ozet_uret.py"], cwd=d, capture_output=True,
                           text=True, timeout=60, env=env)
        if r.returncode:
            raise RuntimeError(r.stderr[-400:])
        return json.load(open(os.path.join(d, "ozet.json"), encoding="utf-8"))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _karne_fikstur():
    _, k = co.kalibre_et([_veri(a, 0.0, 40 + i) for i, a in enumerate(config.ASSETS)], _grid4())
    return json.loads(json.dumps(k, default=co._json))


def _anlik(i, kal=None):
    s = {"timestamp": f"2026-09-{10 + i:02d}T17:00:00+00:00",
         "indices": {k: {"value": round(0.3 * math.sin(i + j), 4), "category": "Neutral"}
                     for j, k in enumerate(config.ASSETS)},
         "regime": {"label": "Transitioning", "basket_spread": 0.01, "avg_correlation": 0.02,
                    "pc1_share": 0.2, "as_of": "2026-09-27"}}
    if kal:
        s["kalibrasyon"] = kal
    return s


def m12():
    import re
    karne = _karne_fikstur()
    kal = kd._saniye(karne["olcum_ani"])
    ayni = [_anlik(i, kal) for i in range(13)]
    o = _ozet_kos(ayni, karne)
    out = [bool(o["hareket"]) and all(isinstance(m["onceki"], float) and isinstance(m["deger"], float)
                                      and isinstance(m["fark"], float) for m in o["hareket"]),
           "hareket_kesinti" not in o, o.get("hareket_sigma_var") is True]
    farkli = ayni[:-1] + [_anlik(12, "2026-12-01T00:00:00")]
    o2 = _ozet_kos(farkli, karne)
    out += [o2["hareket"] == [], "kalibrasyon değişti" in o2.get("hareket_kesinti", ""),
            "kıyaslanamaz" in o2.get("alt1_donus_cumle", "")]
    mdx = open(os.path.join(KOK, "site", "src", "content", "projeler", "fx-haber-endeksi.mdx"),
               encoding="utf-8").read()
    cagri = set(re.findall(r'<Deger proje="fx-haber-endeksi" anahtar="([^"]+)"', mdx))
    # KAPSAM: sayfanın çağırdığı anahtar YALNIZ aynı kalibrasyon hâlinde değil,
    # kalibrasyonun DEĞİŞTİĞİ gün (yeniden kalibrasyonun ertesi koşusu — bu hâl
    # tanımı gereği bir kez yaşanır), tek okumalık tarihçede ve figür defteri
    # yokken de yazılmalı; yoksa yayın kapısı siteyi tam o gün durdurur.
    tek = _ozet_kos(ayni[-1:], karne)
    defsiz = _ozet_kos(ayni, karne, sekil_ozet=False)
    eksik = {ad: sorted(cagri - set(x)) for ad, x in
             (("aynı kalibrasyon", o), ("kalibrasyon değişti", o2), ("tek okuma", tek),
              ("figür defteri yok", defsiz))}
    eksik = {ad: e for ad, e in eksik.items() if e}
    out.append(not eksik)
    return all(out), f"{out} eksik: {eksik}"


# 13 ─ kalibrasyon girisi agdan haber cekmez
def m13():
    agac = ast.parse(open(os.path.join(BURASI, "correlation_optimizer.py"), encoding="utf-8").read())
    yasak = {"fetch_historical_news", "fetch_weekly_news", "load_model", "fetch_prices",
             "fetch_all_news_cached", "_score_all_articles"}
    bulgu = sorted({d.attr if isinstance(d, ast.Attribute) else d.id for d in ast.walk(agac)
                    if (isinstance(d, ast.Attribute) and d.attr in yasak)
                    or (isinstance(d, ast.Name) and d.id in yasak)})
    return not bulgu, ", ".join(bulgu)


for ad, fn in [("1 hızlı pencere bit bit eski pencere", m1), ("2 çekirdekte vektör matematik yok", m2),
               ("3 saat dilimsiz referans hata", m3), ("4 kapanıştan sonraki haber girmez", m4),
               ("5 fiyat sözleşmesi", m5), ("6 getiri yönü", m6), ("7 arşiv", m7), ("8 plasebo p", m8),
               ("9 kalibrasyon kuralı", m9), ("10 parametre dosyası", m10),
               ("11 kalibrasyon kimliği", m11), ("12 özet ve sayfa anahtarları", m12),
               ("13 kalibrasyon ağdan haber çekmez", m13)]:
    def _kos(fn=fn):
        ok, ayr = fn()
        if not ok:
            raise AssertionError(ayr)
        return True
    sina(ad, _kos)

sure = time.time() - T0
sina(f"süre ({sure:.1f} sn ≤ {SURE:.0f})", sure <= SURE)
if dusen:
    print(f"FX endeksi duman: {len(dusen)} madde DÜŞTÜ, {gecen} geçti")
    for d in dusen:
        print("  ✗", d)
    sys.exit(1)
print(f"✓ FX endeksi duman: {gecen} madde geçti ({sure:.1f} sn)")
