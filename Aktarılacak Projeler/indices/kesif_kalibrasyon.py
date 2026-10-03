#!/usr/bin/env python3
"""Keşif: FX haber endeksi kalibrasyonunun ölçüsü — yeniden kalibrasyondan ÖNCE.

Bulutta koşar (fx.yml `kalibrasyon: olcum`): haber arşivi (`data/gdelt_cache.json`)
yalnız o iş akışının önbelleğinde, Yahoo yalnız koşucudan açık. Hiçbir parametre
dosyasına YAZMAZ; çıktısı `data/kalibrasyon_kesif.json` (ölçümün arşivi) ve kayıt.

M1  Kapanış saati. Her sembolün GÜNLÜK bar kapanışı hangi SAATLİK barın kapanışıyla
    eşleşiyor? (D ve D−1, UTC saat saat medyan |fark|, bp). Dövizde beklenen D−1'in
    Londra gece yarısı; vadeli ve endekslerde kapanışın ölçülen saati
    `fiyat.KAPANIS` tablosuna yazılır.
M2  Aynı arşivle dört ölçü, kayıtlı (22.07.2026) parametrelerde ve ızgara boyunca:
    (a) BUGÜNKÜ KOD — Yahoo günlük kapanışı, geriye dönük getiri (pct_change),
        gün D = D 00:00 UTC referansı, amaç yuvarlanan ortalama (lag'i SORMAYAN —
        kodun kendisi böyle; bkz. not);
    (b) GERİYE dönük tepki B_h ↔ S(D) — düzeltilmiş kapanış, kapanış anı referansı;
    (c) İLERİ F_5 ↔ S(D−lag); (d) İLERİ F_1 ↔ S(D−lag).
    (b)–(d) için: IS (ilk %70, son h gün ambargo) ızgara maksimumu, en iyi setin OOS
    değeri, plasebo (hedef dairesel kaydırılarak aynı ızgaranın maksimumu) p'si.
R   Rejim özeti: gün etiketi D 00:00 (eski) ve D+1 00:00 (yeni) referansla.

NOT (a): `grid_search` amaç olarak `rolling_correlation(idx_s, ret_series)` kullanıyor
ve lag'i oraya UYGULAMIYOR (lag yalnız Pearson/Spearman'a giriyordu). Yani lag 0 ile
1 aynı amacı veriyor ve kayıtlı `lag_days` sıralamanın kararsız eşitlik bozmasından
geliyor. (a) bunu birebir yeniden üretir.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import sys
import time
import warnings
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import config            # noqa: E402
import index_builder     # noqa: E402
import fiyat             # noqa: E402

CIKTI = os.path.join(BASE, "data", "kalibrasyon_kesif.json")
PENCERE = 20
IS_PAY = 0.7
T0 = time.time()
warnings.filterwarnings("ignore", category=RuntimeWarning)


def log(*a):
    print(f"[{time.time() - T0:7.1f}s]", *a, flush=True)


# ─────────────────────────────────────────── arşiv
def arsiv(onbellek: dict, anahtar: str, hafta: int = 52):
    """Önbellekten son `hafta` kapanmış hafta; skorlu; tahvilde skor terslenmiş KOPYA.
    Sıra eski optimizasyonla aynı: en yeni hafta önce, hafta içi kayıtlı sırayla."""
    kay = onbellek.get(anahtar) or {}
    simdi = datetime.now(timezone.utc)
    haftalar = sorted((k for k in kay if datetime.fromisoformat(k).replace(tzinfo=timezone.utc)
                       + timedelta(hours=23, minutes=59, seconds=59) < simdi), reverse=True)[:hafta]
    ters = config.ASSETS[anahtar].get("invert_sentiment", False)
    makaleler = []
    for h in haftalar:
        for a in kay[h].get("articles", []):
            if "score" not in a:
                continue
            makaleler.append(dict(a, score=-a["score"]) if ters else a)
    if not haftalar:
        return makaleler, None, None
    bas = datetime.fromisoformat(min(haftalar)).replace(tzinfo=timezone.utc) - timedelta(days=6)
    son = datetime.fromisoformat(max(haftalar)).replace(hour=23, minute=59, second=59,
                                                        tzinfo=timezone.utc)
    return makaleler, bas, son


# ─────────────────────────────────────────── bugünkü kodun dondurulmuş kopyası
def eski_fiyat(ticker):
    """price_fetcher.fetch_prices (period 1y) — DONDURULMUŞ kopya."""
    import yfinance as yf
    df = yf.download(ticker, period="1y", auto_adjust=True, progress=False)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Close"]].copy().ffill()
    for d in [1, 2, 3, 5]:
        df[f"Return_{d}d"] = df["Close"].pct_change(d)
    df.dropna(subset=["Return_1d"], inplace=True)
    return df


def eski_gunluk_seri(makaleler, params, bas, son):
    """build_daily_index_series'in ESKİ gün referansıyla (D 00:00) kopyası."""
    dizi = index_builder.MakaleDizisi(makaleler)
    seri = {}
    bugun = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    t = bas
    while t <= son:
        k = t.strftime("%Y-%m-%d")
        if k >= bugun:
            break
        v, _ = index_builder._compute_index_value(makaleler, params, reference_time=t, dizi=dizi)
        seri[k] = round(v, 4)
        t += timedelta(days=1)
    return index_builder.smooth_series(index_builder.normalize_index_series(seri), span=3)


def eski_yuvarlanan(idx: pd.Series, ret: pd.Series, w=PENCERE) -> float:
    c = pd.DataFrame({"index": idx, "returns": ret}).dropna()
    if len(c) < w:
        return 0.0
    r = c["index"].rolling(w).corr(c["returns"]).dropna()
    return round(float(r.mean()), 4) if len(r) else 0.0


def eski_amac(makaleler, params, fiyatlar, sutun):
    """optimize_asset'in IS amacı (yuvarlanan ort.), kayıtlı parametrede."""
    n = len(fiyatlar)
    isp = fiyatlar.iloc[:int(n * IS_PAY)]
    bas = isp.index[0].to_pydatetime().replace(tzinfo=timezone.utc)
    son = isp.index[-1].to_pydatetime().replace(tzinfo=timezone.utc)
    s = pd.Series(eski_gunluk_seri(makaleler, params, bas, son))
    s.index = pd.to_datetime(s.index)
    return eski_yuvarlanan(s, isp[sutun])


# ─────────────────────────────────────────── yeni ölçü
def yuvarlanan_ort(x: np.ndarray, y: np.ndarray, w=PENCERE) -> float:
    """20'lik pencere Pearson'larının ortalaması (çiftler eksiksiz; sıfır varyanslı pencere düşer)."""
    n = len(x)
    if n < w:
        return float("nan")
    cx = np.concatenate([[0.0], np.cumsum(x)])
    cy = np.concatenate([[0.0], np.cumsum(y)])
    cxx = np.concatenate([[0.0], np.cumsum(x * x)])
    cyy = np.concatenate([[0.0], np.cumsum(y * y)])
    cxy = np.concatenate([[0.0], np.cumsum(x * y)])
    sx, sy = cx[w:] - cx[:-w], cy[w:] - cy[:-w]
    sxx, syy, sxy = cxx[w:] - cxx[:-w], cyy[w:] - cyy[:-w], cxy[w:] - cxy[:-w]
    vx, vy = sxx - sx * sx / w, syy - sy * sy / w
    ok = (vx > 1e-12) & (vy > 1e-18)
    if not ok.any():
        return float("nan")
    r = (sxy[ok] - sx[ok] * sy[ok] / w) / np.sqrt(vx[ok] * vy[ok])
    return float(r.mean())


def hizala(s: pd.Series, hedef: pd.Series, lag: int):
    d = pd.DataFrame({"x": s.shift(lag), "y": hedef}).dropna()
    return d["x"].to_numpy(float), d["y"].to_numpy(float), d.index


def izgara():
    keys = [k for k in config.PARAM_GRID if k != "lag_days"]
    return [dict(zip(keys, c)) for c in itertools.product(*(config.PARAM_GRID[k] for k in keys))]


def ad(p):
    return f"{p['aggregation']}·hl{p['time_decay_halflife']}·{p['score_transform']}" \
           f"·nf{p['neutral_filter']}·mw{p['momentum_weight']}"


def m1(ticker, saatlik, gunluk_kapanis):
    """Günlük kapanış ↔ saatlik barın kapanışı: (gün kayması, UTC saat) başına medyan |fark| bp."""
    s = saatlik.copy()
    s.index = s.index + pd.Timedelta(hours=1)          # barın kapanış anı
    g = gunluk_kapanis.dropna()
    g = g[g.index >= s.index.min().tz_convert(None).normalize() + pd.Timedelta(days=2)].iloc[-220:]
    sonuc = []
    for kay in (0, -1):
        for saat in range(24):
            fark = []
            for gun, v in g.items():
                t = pd.Timestamp(gun + pd.Timedelta(days=kay) + pd.Timedelta(hours=saat), tz="UTC")
                pen = s[(s.index <= t) & (s.index > t - pd.Timedelta(minutes=61))]
                if len(pen):
                    fark.append(abs(math.log(float(pen.iloc[-1]) / v)) * 1e4)
            if len(fark) >= 0.6 * len(g):
                sonuc.append((round(float(np.median(fark)), 2), kay, saat, len(fark)))
    sonuc.sort()
    return [{"medyan_bp": a, "gun_kaymasi": b, "utc_saat": c, "n": d} for a, b, c, d in sonuc[:4]]


def main():
    import fx_kapanis
    import news_fetcher
    import yfinance as yf
    import correlation_optimizer as co

    cikti = {"olcum_ani": datetime.now(timezone.utc).isoformat(), "m1": {}, "m2": {}, "r": {}}
    kayitli = co.load_optimized_params()
    onbellek = news_fetcher._load_historical_cache()
    log("önbellek varlıkları:", sorted(onbellek))
    combos = izgara()

    for anahtar, cfg in config.ASSETS.items():
        ticker = cfg["ticker"]
        try:
            saat = fx_kapanis.yfinance_saatlik([ticker]).get(ticker)
            gdf = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
            if isinstance(gdf.columns, pd.MultiIndex):
                gdf.columns = gdf.columns.get_level_values(0)
            gk = gdf["Close"]
            gk.index = pd.DatetimeIndex(gk.index).tz_localize(None) if gk.index.tz else gk.index
            cikti["m1"][anahtar] = {"ticker": ticker, "en_iyi": m1(ticker, saat, gk)}
            log("M1", anahtar, cikti["m1"][anahtar]["en_iyi"][:2])
        except Exception as e:  # noqa: BLE001
            cikti["m1"][anahtar] = {"ticker": ticker, "hata": repr(e)}
            log("M1 HATA", anahtar, e)
            saat = None

        makaleler, abas, ason = arsiv(onbellek, anahtar)
        kay = {"makale": len(makaleler), "arsiv": [abas.isoformat() if abas else None,
                                                   ason.isoformat() if ason else None]}
        cikti["m2"][anahtar] = kay
        if len(makaleler) < 50:
            kay["hata"] = "arşiv yetersiz"
            log("M2 atlandı", anahtar, len(makaleler))
            continue
        p0 = dict(kayitli.get(anahtar, config.DEFAULT_PARAMS))
        try:
            eski = eski_fiyat(ticker)
            kay["a_bugunku_kod"] = {"5d": eski_amac(makaleler, p0, eski, "Return_5d"),
                                    "1d": eski_amac(makaleler, p0, eski, "Return_1d")}
        except Exception as e:  # noqa: BLE001
            kay["a_hata"] = repr(e)

        try:
            if fiyat.doviz_mu(ticker):
                fy = fiyat.doviz_kapanislari(ticker, saatlik=saat, gun=400)
            else:
                fy = fiyat.gunluk_kapanislar(ticker, gun=400)
        except Exception as e:  # noqa: BLE001
            kay["fiyat_hata"] = repr(e)
            log("fiyat HATA", anahtar, e)
            continue
        kay["fiyat_tanim"] = fy.tanim
        if fiyat.doviz_mu(ticker) and len(fy.seri):
            # Dövizde kaymanın kendisi: Yahoo günlük Close(D+1) ≈ NY17(D) mi?
            ny = fy.seri
            g = eski["Close"] if len(eski) else pd.Series(dtype=float)
            ort = ny.index.intersection(g.index)
            ort1 = ny.index.intersection(g.index - pd.Timedelta(days=1))
            if len(ort) > 20:
                kay["kayma_bp"] = {
                    "ayni_gun": round(float(np.median(np.abs(np.log(g.reindex(ort) / ny.reindex(ort))))) * 1e4, 2),
                    "ertesi_gun_bari": round(float(np.median(np.abs(np.log(
                        g.reindex(ort1 + pd.Timedelta(days=1)).to_numpy() / ny.reindex(ort1).to_numpy())))) * 1e4, 2)}
        # Kapanış anı arşivin içinde ve 7 günlük pencere tam olan işlem günleri
        an = fy.an.dropna()
        gecerli = an[(an - pd.Timedelta(days=config.LOOKBACK_DAYS) >= pd.Timestamp(abas))
                     & (an <= pd.Timestamp(ason))]
        gunler = list(gecerli.index)
        if len(gunler) < 80:
            kay["hata"] = f"hizalı gün yetersiz ({len(gunler)})"
            continue
        kesim = int(len(gunler) * IS_PAY)
        is_g, oos_g = gunler[:kesim], gunler[kesim:]
        kay["gun"] = {"is": [str(is_g[0].date()), str(is_g[-1].date()), len(is_g)],
                      "oos": [str(oos_g[0].date()), str(oos_g[-1].date()), len(oos_g)]}
        dizi = index_builder.MakaleDizisi(makaleler)

        def seri(params, gl):
            d = index_builder.seri_anlarda(dizi, params, {str(g.date()): gecerli[g].to_pydatetime()
                                                          for g in gl})
            s = pd.Series(d)
            s.index = pd.to_datetime(s.index)
            return s

        hedefler = {"ileri_5": fiyat.ileri_getiri(fy.seri, 5), "ileri_1": fiyat.ileri_getiri(fy.seri, 1),
                    "geri_5": fiyat.geri_getiri(fy.seri, 5), "geri_1": fiyat.geri_getiri(fy.seri, 1)}
        ambargo = {"ileri_5": 5, "ileri_1": 1, "geri_5": 0, "geri_1": 0}

        # kayıtlı parametrede
        s_is0 = seri(p0, is_g)
        kay["kayitli"] = {"params": p0}
        for hk, hy in hedefler.items():
            for lag in (0, 1):
                x, y, _ = hizala(s_is0, hy.reindex(is_g[:len(is_g) - ambargo[hk]]), lag)
                kay["kayitli"][f"{hk}_lag{lag}"] = round(yuvarlanan_ort(x, y), 4)

        # ızgara
        t1 = time.time()
        is_seri = {i: seri(p, is_g) for i, p in enumerate(combos)}
        log("M2", anahtar, f"{len(combos)} seri {time.time() - t1:.1f}s", len(makaleler), "makale")
        rng_k = list(range(PENCERE, max(PENCERE + 1, len(is_g) - PENCERE)))
        kay["izgara"] = {}
        for hk, hy in hedefler.items():
            for lag in (0, 1):
                hd = hy.reindex(is_g[:len(is_g) - ambargo[hk]])
                xs = {i: hizala(s, hd, lag) for i, s in is_seri.items()}
                deg = {i: yuvarlanan_ort(x, y) for i, (x, y, _) in xs.items()}
                en = max(deg, key=lambda i: (-math.inf if math.isnan(deg[i]) else deg[i]))
                plasebo = []
                for k in rng_k:
                    m = -math.inf
                    for i, (x, y, _) in xs.items():
                        v = yuvarlanan_ort(x, np.roll(y, k))
                        if not math.isnan(v) and v > m:
                            m = v
                    plasebo.append(m)
                plasebo = np.array(plasebo)
                # OOS: en iyi set, OOS günlerinde ayrı kurulan seriyle
                s_oos = seri(combos[en], oos_g)
                xo, yo, _ = hizala(s_oos, hy.reindex(oos_g), lag)
                kay["izgara"][f"{hk}_lag{lag}"] = {
                    "is_max": round(deg[en], 4), "params": ad(combos[en]),
                    "is_medyan": round(float(np.nanmedian(list(deg.values()))), 4),
                    "oos": round(yuvarlanan_ort(xo, yo), 4),
                    "plasebo_p": round(float((plasebo >= deg[en]).mean()), 4),
                    "plasebo_95": round(float(np.quantile(plasebo, 0.95)), 4),
                    "plasebo_n": int(len(plasebo))}
        log("M2", anahtar, {k: (v["is_max"], v["oos"], v["plasebo_p"]) for k, v in kay["izgara"].items()})
        json.dump(cikti, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # R — rejim özeti, iki gün etiketiyle
    try:
        import web_cikti
        yeni = web_cikti.duyarlilik_matrisi()
        cikti["r"]["yeni"] = web_cikti.rejim_ozeti(seriler=yeni)
        eski_s = {}
        opt = web_cikti._optimize_paramlar()
        for anahtar in config.ASSETS:
            hafta = web_cikti._gdelt_haftalik(anahtar, onbellek)
            if not hafta:
                continue
            mk = [a for arts in hafta.values() for a in arts]
            hs = sorted(hafta)
            bas = datetime.fromisoformat(hs[0]).replace(tzinfo=timezone.utc) - timedelta(days=6)
            son = datetime.fromisoformat(hs[-1]).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            s = pd.Series(eski_gunluk_seri(mk, web_cikti._varlik_parametresi(opt, anahtar), bas, son))
            s.index = pd.to_datetime(s.index)
            eski_s[anahtar] = s.sort_index()
        cikti["r"]["eski"] = web_cikti.rejim_ozeti(seriler=eski_s)
        log("R", cikti["r"])
    except Exception as e:  # noqa: BLE001
        cikti["r"]["hata"] = repr(e)
        log("R HATA", e)

    json.dump(cikti, open(CIKTI, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("yazıldı", CIKTI)


if __name__ == "__main__":
    main()
