#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO · Yapı ve Momentum — OLASILIK ÖLÇÜMÜ ve KURULUM BACKTEST'İ.

İki katman, ikisi de `yapi_referans` kurallarından ve depodaki OHLC
arşivinden (`veri.py`) beslenir; ağa çıkmaz.

(A) OLAY OLASILIKLARI — indikatörün "kırılım olasılığı" satırlarının kaynağı.
    Her olay ailesi için ölçülen soru ADIYLA:
      bos        : BOS'tan sonra ±0,618·aralık hedefi (kullanıcı Pine'ının
                   Target 1'i), kırılan seviyenin gövdeyle geri alınmasından
                   ÖNCE görülüyor mu (ufuk 50 bar)?  T2 = ±1,0·aralık.
      choch/mss  : yön değişiminden sonra yeni yönde BOS, geri CHoCH'tan
                   önce geliyor mu?
      sweep      : süpürmeden sonra 1 ATR ters hareket, 1 ATR devamdan önce
                   geliyor mu? Ve ≤3 barda displacement geliyor mu?
      fvg        : CE'ye dokunma · tam dolum · ters dönme (50 bar); CE'den
                   1 ATR tepki, tam dolumdan önce mi?
      ob         : taze OB'nin ilk dokunuşunda 1 ATR tepki, gövdeyle
                   kırılmadan önce mi?
      esit       : EQH/EQL süpürüldü mü, koşuldu mu, hiç test edilmedi mi?
      prz        : PRZ'ye giriş → teyit → T1 stoptan önce mi?
      div        : kullanıcı tablosunun 25 satırı, satırın kendi SL/TP ATR
                   çarpanıyla — kaynağın yüzdesiyle yan yana, N ile.
    Her satır N taşır; N < 30 satır yorumsuz basılır (örneklem aritmetiği,
    SMC 15.4: n=30 ±9 puan).

(B) KURULUM PAKETLERİ — emir mekaniğiyle R çarpanı.
      sweep_mss_fvg : sweep → MSS → bacaktaki ilk FVG CE'sine limit; stop
                      sweep ucu − tampon; hedef 2R (ve 3R).
      ob_retest     : BOS/MSS bacağının taze OB'sine (MT) limit; stop fitil
                      ötesi − tampon; 2R.
      prz           : teyit kapanışında piyasa; stop kalıp geçersizliği −
                      tampon; T1/T2 (0,382/0,618 AD).
      diverjans     : onay kapanışında piyasa; SL/TP tablo çarpanları × ATR.
      bos_devam     : BOS kapanışında piyasa (kırılım); stop korunan swing;
                      hedef 0,618·aralık.
    Her satırda: n, isabet, ort R, bootstrap %95 aralığı, kâr faktörü,
    RASTGELE GİRİŞ TABANI (aynı seri, aynı sayıda emir, aynı yön dağılımı,
    aynı stop/hedef mesafesi, giriş b+1 açılışı; 30 koşu → gerçek sonucun
    yüzdeliği; yalnız süzgeçsiz satırda — süzgeçli satırlar onunla kıyaslanır),
    risk < 0,3 ATR emirler 'dar' sayılır ve ölçüye girmez (spread riski yutar),
    iki yarı, maliyet (gidiş-dönüş spread VARSAYIMI, `SPREAD`; ölçülmedi).
    Doluş kuralı: sinyal barı KAPANMIŞ bardır, emir i+1'den itibaren; aynı
    barda stop ve hedef → stop (tutucu; sayısı 'belirsiz' olarak yazılır).

Çıktı: site/src/data/yapi_backtest.json — sayfa bileşeni yalnız buradan okur.
Zaman dilimleri: 5m · 15m · 1h (arşiv) · 4h ve günlük (saatlikten kurulur;
Yahoo FX günlük barında gövde yok). Örneklem DIŞI: her satır iki yarı taşır;
ayrıca 5/15 dk yalnız 12 haftadır ve bu yazılır."""
from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

KOK = Path(__file__).resolve().parent
DEPO = KOK.parents[1]
sys.path.insert(0, str(KOK))
import veri                                  # noqa: E402
import yapi_referans as Y                    # noqa: E402
from brooks_referans import Seri             # noqa: E402

CIKTI = DEPO / "site" / "src" / "data" / "yapi_backtest.json"

# Gidiş-dönüş spread VARSAYIMI (fiyat birimi). Ölçülmedi; tipik perakende
# değerler. Sayfa bunu "varsayım" diye yazar.
SPREAD = {"eurusd": 0.00012, "gbpusd": 0.00015, "usdjpy": 0.012, "usdchf": 0.00015, "audusd": 0.00014,
          "usdcad": 0.00016, "nzdusd": 0.00018, "eurgbp": 0.00015, "eurchf": 0.00018, "dxy": 0.02,
          "xu100": 3.0, "spx": 0.5, "ndx": 1.5, "wti": 0.04, "xau": 0.35}
UFUK = 50
TAMPON_ATR = 0.25
RASTGELE = 30
ZAMAN_DILIMLERI = ("5m", "15m", "1h", "4h", "1d")


def seriler_tf() -> dict[str, dict[str, Seri]]:
    """{tf: {enstrüman: Seri}} — 4h ve günlük saatlikten; FX günlük Yahoo'dan alınmaz."""
    out: dict[str, dict[str, Seri]] = defaultdict(dict)
    for ad in veri.seriler():
        ens, tf = veri.enstruman(ad), veri.aralik(ad)
        if tf in ("5m", "15m", "1h"):
            out[tf][ens] = veri.oku(ad)
    for ens, s in list(out["1h"].items()):
        out["4h"][ens] = veri.yeniden_ornekle(s, 240)
        out["1d"][ens] = veri.yeniden_ornekle(s, 1440)
    return out


# ── sonuç tarayıcı ───────────────────────────────────────────────────────────
def islem(s: Seri, bas: int, yon: int, giris: float, stop: float, hedef: float,
          limit: bool, ufuk: int) -> dict | None:
    """bas: sinyal barı (kapanmış). Emir bas+1'den itibaren. Limit emirde doluş
    fiyatın seviyeye gelmesiyle (ufuk içinde gelmezse None). Döner: R (hedef
    → +hedefR, stop → −1), 'belirsiz' bayrağı (aynı barda ikisi), doluş barı."""
    risk = abs(giris - stop)
    if risk <= 0:
        return None
    n = len(s)
    i = bas + 1
    dolus = None
    if limit:
        while i < n and i <= bas + ufuk:
            if (yon > 0 and s.l[i] <= giris) or (yon < 0 and s.h[i] >= giris):
                dolus = i
                # doluş barında açılış boşlukla seviyeyi geçtiyse daha iyi fiyattan dolar
                if (yon > 0 and s.o[i] < giris) or (yon < 0 and s.o[i] > giris):
                    giris = s.o[i]
                    risk = abs(giris - stop)
                    if risk <= 0:
                        return None
                break
            i += 1
        if dolus is None:
            return None
    else:
        if i >= n:
            return None
        dolus = i
        giris = s.o[i]                      # piyasa emri: sonraki barın açılışı
        risk = abs(giris - stop)
        if risk <= 0:
            return None
    hedef_r = abs(hedef - giris) / risk
    j = dolus
    while j < n and j <= dolus + ufuk:
        stop_vur = s.l[j] <= stop if yon > 0 else s.h[j] >= stop
        hedef_vur = s.h[j] >= hedef if yon > 0 else s.l[j] <= hedef
        if stop_vur and hedef_vur:
            return {"R": -1.0, "belirsiz": True, "dolus": dolus, "cikis": j, "risk": risk, "giris": giris}
        if stop_vur:
            return {"R": -1.0, "belirsiz": False, "dolus": dolus, "cikis": j, "risk": risk, "giris": giris}
        if hedef_vur:
            return {"R": hedef_r, "belirsiz": False, "dolus": dolus, "cikis": j, "risk": risk, "giris": giris}
        j += 1
    # ufuk doldu: kapanıştan çık
    k = min(j, n - 1)
    r = (s.c[k] - giris) / risk * yon
    return {"R": r, "belirsiz": False, "dolus": dolus, "cikis": k, "risk": risk, "giris": giris, "zaman": True}


def ilk_hangisi(s: Seri, bas: int, ust: float, alt: float, ufuk: int, govde_ust=False, govde_alt=False) -> str:
    """bas+1'den itibaren fiyat önce `ust`e mi `alt`a mı dokunur (govde_*: kapanışla)."""
    for j in range(bas + 1, min(len(s), bas + 1 + ufuk)):
        u = (s.c[j] >= ust) if govde_ust else (s.h[j] >= ust)
        a = (s.c[j] <= alt) if govde_alt else (s.l[j] <= alt)
        if u and a:
            return "belirsiz"
        if u:
            return "ust"
        if a:
            return "alt"
    return "hic"


# ── istatistik ───────────────────────────────────────────────────────────────
def bootstrap_ort(x: list[float], k: int = 400, tohum: int = 7) -> tuple[float, float]:
    if not x:
        return (math.nan, math.nan)
    rng = random.Random(tohum)
    n = len(x)
    ort = sorted(sum(rng.choice(x) for _ in range(n)) / n for _ in range(k))
    return (ort[int(0.025 * k)], ort[int(0.975 * k) - 1])


def ozet_r(R: list[float]) -> dict:
    if not R:
        return {"n": 0}
    kaz = [r for r in R if r > 0]
    kay = [r for r in R if r <= 0]
    ca = bootstrap_ort(R)
    yarim = len(R) // 2
    return {"n": len(R), "kazanma": round(len(kaz) / len(R), 3), "ort_R": round(st.mean(R), 3),
            "ca_alt": round(ca[0], 3), "ca_ust": round(ca[1], 3),
            "kar_faktoru": round(sum(kaz) / abs(sum(kay)), 2) if kay and sum(kay) != 0 else None,
            "ilk_yari_ort_R": round(st.mean(R[:yarim]), 3) if yarim else None,
            "ikinci_yari_ort_R": round(st.mean(R[yarim:]), 3) if yarim else None}


def oran(k: int, n: int) -> dict:
    if n == 0:
        return {"n": 0, "oran": None}
    p = k / n
    se = math.sqrt(p * (1 - p) / n)
    return {"n": n, "oran": round(p, 3), "ca_alt": round(max(0, p - 1.96 * se), 3), "ca_ust": round(min(1, p + 1.96 * se), 3)}


# ── (A) olay olasılıkları ───────────────────────────────────────────────────
def olay_olasiliklari(s: Seri, y: Y.Yapi, m: Y.Momentum) -> dict:
    n = len(s)
    out: dict = {}
    # BOS: T1 (0,618·aralık) seviyenin gövdeyle geri alınmasından önce mi
    say = Counter()
    for o in y.olaylar:
        if o.tur != "BOS":
            continue
        ar = y.aralik[o.bar]
        if ar is None:
            continue
        r = ar[1] - ar[0]
        t1 = o.seviye + o.yon * 0.618 * r
        t2 = o.seviye + o.yon * 1.0 * r
        geri = o.seviye
        if o.yon > 0:
            h1 = ilk_hangisi(s, o.bar, t1, geri, UFUK, govde_alt=True)
            h2 = ilk_hangisi(s, o.bar, t2, geri, UFUK, govde_alt=True)
            say["t1_" + ("evet" if h1 == "ust" else "hayir" if h1 in ("alt", "belirsiz") else "hic")] += 1
            say["t2_" + ("evet" if h2 == "ust" else "hayir" if h2 in ("alt", "belirsiz") else "hic")] += 1
        else:
            h1 = ilk_hangisi(s, o.bar, geri, t1, UFUK, govde_ust=True)
            h2 = ilk_hangisi(s, o.bar, geri, t2, UFUK, govde_ust=True)
            say["t1_" + ("evet" if h1 == "alt" else "hayir" if h1 in ("ust", "belirsiz") else "hic")] += 1
            say["t2_" + ("evet" if h2 == "alt" else "hayir" if h2 in ("ust", "belirsiz") else "hic")] += 1
    nb = say["t1_evet"] + say["t1_hayir"] + say["t1_hic"]
    out["bos_t1"] = oran(say["t1_evet"], nb) | {"geri_alindi": say["t1_hayir"], "kararsiz": say["t1_hic"]}
    out["bos_t2"] = oran(say["t2_evet"], nb) | {"geri_alindi": say["t2_hayir"], "kararsiz": say["t2_hic"]}
    # CHoCH / MSS: yeni yönde BOS, geri CHoCH'tan önce mi
    for tur in ("CHOCH", "MSS"):
        e = h = 0
        idx = [k for k, o in enumerate(y.olaylar) if o.tur == tur]
        for k in idx:
            o = y.olaylar[k]
            sonraki = next((q for q in y.olaylar[k + 1:] if q.tur in ("BOS", "CHOCH", "MSS")), None)
            if sonraki is None:
                continue
            if sonraki.tur == "BOS" and sonraki.yon == o.yon:
                e += 1
            else:
                h += 1
        out[tur.lower() + "_devam"] = oran(e, e + h)
    # Sweep: 1 ATR ters, 1 ATR devamdan önce; ≤3 barda displacement
    e = h = disp = tot = 0
    for bar, ad, sev, yon in y.sweepler:
        a = y.atr[bar]
        if not a:
            continue
        tot += 1
        if yon > 0:    # üst havuz süpürüldü → beklenen tepki aşağı
            r = ilk_hangisi(s, bar, s.c[bar] + a, s.c[bar] - a, UFUK)
            e += r == "alt"; h += r in ("ust", "belirsiz")
        else:
            r = ilk_hangisi(s, bar, s.c[bar] + a, s.c[bar] - a, UFUK)
            e += r == "ust"; h += r in ("alt", "belirsiz")
        disp += any(y.displacement(j) and ((s.c[j] < s.o[j]) if yon > 0 else (s.c[j] > s.o[j])) for j in range(bar + 1, min(n, bar + 4)))
    out["sweep_tepki"] = oran(e, e + h)
    out["sweep_displacement3"] = oran(disp, tot)
    # Sweep havuz türüne göre tepki
    tur_say: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for bar, ad, sev, yon in y.sweepler:
        a = y.atr[bar]
        if not a:
            continue
        r = ilk_hangisi(s, bar, s.c[bar] + a, s.c[bar] - a, UFUK)
        ok = (r == "alt") if yon > 0 else (r == "ust")
        kot = (r in ("ust", "belirsiz")) if yon > 0 else (r in ("alt", "belirsiz"))
        if ok or kot:
            tur_say[ad][0] += ok; tur_say[ad][1] += 1
    out["sweep_havuz"] = {ad: oran(k, t) for ad, (k, t) in tur_say.items()}
    # FVG
    ce = dolu = ters = tot = tepki_e = tepki_h = 0
    for f in y.fvgler:
        if f.bar + UFUK >= n:
            continue
        tot += 1
        ce += f.ce_bar is not None and f.ce_bar <= f.bar + UFUK or (f.dolu_bar is not None and f.dolu_bar <= f.bar + UFUK)
        dolu += f.dolu_bar is not None and f.dolu_bar <= f.bar + UFUK
        ters += f.ters_bar is not None and f.ters_bar <= f.bar + UFUK
        if f.ce_bar is not None and f.ce_bar <= f.bar + UFUK:
            a = y.atr[f.ce_bar] or 0
            if a > 0:
                if f.yon > 0:
                    r = ilk_hangisi(s, f.ce_bar, f.ce + a, f.alt, UFUK)
                    tepki_e += r == "ust"; tepki_h += r in ("alt", "belirsiz")
                else:
                    r = ilk_hangisi(s, f.ce_bar, f.ust, f.ce - a, UFUK)
                    tepki_e += r == "alt"; tepki_h += r in ("ust", "belirsiz")
    out["fvg_ce50"] = oran(ce, tot); out["fvg_dolu50"] = oran(dolu, tot); out["fvg_ters50"] = oran(ters, tot)
    out["fvg_ce_tepki"] = oran(tepki_e, tepki_e + tepki_h)
    # OB ilk dokunuş tepkisi
    e = h = 0
    for ob in y.oblar:
        if ob.taze_bar is None:
            continue
        a = y.atr[ob.taze_bar] or 0
        if a <= 0:
            continue
        if ob.yon > 0:
            r = ilk_hangisi(s, ob.taze_bar, ob.ust + a, ob.alt, UFUK, govde_alt=True)
            e += r == "ust"; h += r in ("alt", "belirsiz")
        else:
            r = ilk_hangisi(s, ob.taze_bar, ob.ust, ob.alt - a, UFUK, govde_ust=True)
            e += r == "alt"; h += r in ("ust", "belirsiz")
    out["ob_tepki"] = oran(e, e + h)
    # EQH/EQL: sweep / run / test yok (50 bar)
    say = Counter()
    for hv in y.havuzlar:
        if hv.ad not in ("EQH", "EQL") or hv.bar + UFUK >= n:
            continue
        if hv.durum in ("sweep", "run") and hv.durum_bar is not None and hv.durum_bar <= hv.bar + UFUK:
            say[hv.durum] += 1
        else:
            say["test_yok"] += 1
    t = sum(say.values())
    out["esit_sweep"] = oran(say["sweep"], t); out["esit_run"] = oran(say["run"], t); out["esit_testyok"] = oran(say["test_yok"], t)
    # PRZ
    bitmis = [p for p in y.przler if p.durum != "bekliyor"]
    giren = [p for p in bitmis if p.tamam_bar is not None]
    out["prz_tamamlanma"] = oran(len(giren), len(bitmis))            # PRZ'ye fiyat geldi mi
    out["prz_gecersiz_once"] = oran(sum(1 for p in bitmis if p.tamam_bar is None and p.durum == "gecersiz"), len(bitmis))
    out["prz_teyit"] = oran(sum(1 for p in giren if p.durum == "teyit"), len(giren))   # girenlerin kaçı dönüş mumu verdi
    e = h = 0
    for p in y.przler:
        if p.durum != "teyit" or p.durum_bar is None:
            continue
        r = ilk_hangisi(s, p.durum_bar, *(p.t1, p.stop) if p.yon > 0 else (p.stop, p.t1), UFUK * 2)
        ok = (r == "ust") if p.yon > 0 else (r == "alt")
        kot = (r in ("alt", "belirsiz")) if p.yon > 0 else (r in ("ust", "belirsiz"))
        e += ok; h += kot
    out["prz_t1"] = oran(e, e + h)
    return out


def diverjans_tablosu(s: Seri, y: Y.Yapi, m: Y.Momentum) -> list[dict]:
    """Kullanıcı tablosunun 25 satırı, satırın kendi SL/TP çarpanıyla."""
    satirlar = []
    for n_satir, (dt, cb, cr, ct, sl_k, tp_k, iddia) in enumerate(Y.DIV_TABLO):
        R = []
        for d in m.diverjanslar:
            if d.tablo != n_satir:
                continue
            a = y.atr[d.bar]
            if not a or d.bar + 1 >= len(s):
                continue
            yon = +1 if dt in (1, 3) else -1
            giris = s.c[d.bar]
            r = islem(s, d.bar, yon, giris, giris - yon * sl_k * a, giris + yon * tp_k * a, False, UFUK * 4)
            if r is not None:
                R.append(1 if r["R"] > 0 else 0)
        satirlar.append({"satir": n_satir, "tip": dt, "bb": cb, "rsi": cr, "trend": ct, "sl": sl_k, "tp": tp_k,
                         "iddia": iddia, **oran(sum(R), len(R))})
    return satirlar


# ── (B) kurulum paketleri ────────────────────────────────────────────────────
def paket_emirleri(s: Seri, y: Y.Yapi, m: Y.Momentum, paket: str, hedef_R: float) -> list[dict]:
    """Her emir: {bar, yon, giris, stop, hedef, limit}."""
    E = []
    n = len(s)
    if paket == "sweep_mss_fvg":
        for o in y.olaylar:
            if o.tur != "MSS":
                continue
            fvg = next((f for f in y.fvgler if f.yon == o.yon and o.bar - 10 <= f.bar <= o.bar), None)
            sw = next((b for b, ad, sev, yon in reversed(y.sweepler) if b < o.bar and yon == -o.yon and b >= o.bar - int(Y.SABIT["sweep_pencere"])), None)
            if fvg is None or sw is None:
                continue
            a = y.atr[o.bar] or 0
            uc = min(s.l[sw:o.bar + 1]) if o.yon > 0 else max(s.h[sw:o.bar + 1])
            stop = uc - o.yon * TAMPON_ATR * a
            giris = fvg.ce
            risk = abs(giris - stop)
            if risk <= 0:
                continue
            E.append({"bar": o.bar, "yon": o.yon, "giris": giris, "stop": stop, "hedef": giris + o.yon * hedef_R * risk, "limit": True})
    elif paket == "ob_retest":
        for ob in y.oblar:
            if ob.olay_bar + 1 >= n:
                continue
            a = y.atr[ob.olay_bar] or 0
            stop = ob.fitil - ob.yon * TAMPON_ATR * a
            giris = ob.mt
            risk = abs(giris - stop)
            if risk <= 0:
                continue
            E.append({"bar": ob.olay_bar, "yon": ob.yon, "giris": giris, "stop": stop, "hedef": giris + ob.yon * hedef_R * risk, "limit": True})
    elif paket == "prz":
        for p in y.przler:
            if p.durum != "teyit" or p.durum_bar is None or p.durum_bar + 1 >= n:
                continue
            a = y.atr[p.durum_bar] or 0
            stop = p.stop - p.yon * TAMPON_ATR * a
            giris = s.c[p.durum_bar]
            risk = abs(giris - stop)
            if risk <= 0:
                continue
            hedef = p.t1 if hedef_R == 1 else p.t2
            if (hedef - giris) * p.yon <= 0:
                continue
            E.append({"bar": p.durum_bar, "yon": p.yon, "giris": giris, "stop": stop, "hedef": hedef, "limit": False})
    elif paket == "diverjans":
        for d in m.diverjanslar:
            if d.tablo is None or d.bar + 1 >= n:
                continue
            a = y.atr[d.bar] or 0
            yon = +1 if d.tip in (1, 3) else -1
            giris = s.c[d.bar]
            E.append({"bar": d.bar, "yon": yon, "giris": giris, "stop": giris - yon * d.sl_atr * a,
                      "hedef": giris + yon * d.tp_atr * a, "limit": False})
    elif paket == "bos_devam":
        for o in y.olaylar:
            if o.tur != "BOS" or o.bar + 1 >= n:
                continue
            ar = y.aralik[o.bar]
            pl = y.pL[o.bar] if o.yon > 0 else y.pH[o.bar]
            if ar is None or pl is None:
                continue
            r = ar[1] - ar[0]
            giris = s.c[o.bar]
            stop = pl
            if (giris - stop) * o.yon <= 0:
                continue
            E.append({"bar": o.bar, "yon": o.yon, "giris": giris, "stop": stop, "hedef": o.seviye + o.yon * 0.618 * r, "limit": False})
    return E


def paket_kos(s: Seri, y: Y.Yapi, m: Y.Momentum, paket: str, hedef_R: float, spread: float,
              suzgec: str = "yok") -> dict:
    emirler = paket_emirleri(s, y, m, paket, hedef_R)
    if suzgec == "konum":   # discount'ta alış, premium'da satış
        emirler = [e for e in emirler if y.konum[e["bar"]] is not None and ((e["yon"] > 0 and y.konum[e["bar"]] < 50) or (e["yon"] < 0 and y.konum[e["bar"]] > 50))]
    elif suzgec == "trend":  # yapı yönüyle hizalı
        emirler = [e for e in emirler if y.trend[e["bar"]] == e["yon"]]
    elif suzgec == "itki":   # sinyal barının itkisi göreli üst yarıda
        emirler = [e for e in emirler if m.itki_sira[e["bar"]] is not None and m.itki_sira[e["bar"]] >= 50]
    R, R_net, belirsiz, dolmayan, dar = [], [], 0, 0, 0
    riskler, yonler = [], []
    asgari = 0.3
    for e in emirler:
        a = y.atr[e["bar"]] or 0
        if a <= 0 or abs(e["giris"] - e["stop"]) < asgari * a:
            dar += 1
            continue
        r = islem(s, e["bar"], e["yon"], e["giris"], e["stop"], e["hedef"], e["limit"], UFUK)
        if r is None:
            dolmayan += 1
            continue
        R.append(r["R"]); R_net.append(r["R"] - spread / r["risk"])
        belirsiz += r["belirsiz"]; riskler.append(r["risk"]); yonler.append(e["yon"])
    oz = ozet_r(R)
    oz["net_ort_R"] = round(st.mean(R_net), 3) if R_net else None
    oz["emir"] = len(emirler); oz["dolmayan"] = dolmayan; oz["belirsiz"] = belirsiz; oz["dar"] = dar
    # rastgele giriş tabanı: aynı sayıda emir, aynı yön, aynı risk (ATR oranı), aynı hedef R
    oz["risk_atr_p50"] = round(st.median(r / (y.atr[e["bar"]] or 1) for r, e in zip(riskler, emirler) if y.atr[e["bar"]]), 2) if riskler else None
    if R and riskler and suzgec == "yok":
        rng = random.Random(11)
        hedef_r_ort = st.mean(abs(e["hedef"] - e["giris"]) / abs(e["giris"] - e["stop"]) for e in emirler if abs(e["giris"] - e["stop"]) > 0)
        rast = []
        adaylar = list(range(300, len(s) - UFUK - 2))
        for _ in range(RASTGELE):
            rr = []
            for risk, yon in zip(riskler, yonler):
                b = rng.choice(adaylar)
                g = s.o[b + 1]      # piyasa emri b+1 açılışında dolar; stop/hedef DOLUŞ fiyatından
                x = islem(s, b, yon, g, g - yon * risk, g + yon * hedef_r_ort * risk, False, UFUK)
                if x is not None:
                    rr.append(x["R"])
            if rr:
                rast.append(st.mean(rr))
        if rast:
            oz["rastgele_ort_R"] = round(st.mean(rast), 3)
            oz["rastgele_yuzdelik"] = round(100 * sum(1 for v in rast if v < oz["ort_R"]) / len(rast), 1)
    return oz


PAKETLER = ["sweep_mss_fvg", "ob_retest", "prz", "diverjans", "bos_devam"]
SUZGECLER = ["yok", "konum", "trend", "itki"]


def birlestir_oran(satirlar: list[dict]) -> dict:
    k = sum(int(round((r.get("oran") or 0) * r["n"])) for r in satirlar if r.get("n"))
    n = sum(r["n"] for r in satirlar if r.get("n"))
    return oran(k, n)


def main() -> int:
    t0 = time.time()
    S = seriler_tf()
    kunye = {"olcum_tarihi": time.strftime("%Y-%m-%d"), "kaynak": "Aktarılacak Projeler/Indikator/veri (Yahoo Finance arşivi, kapanmış barlar)",
             "kural_kaynagi": "Aktarılacak Projeler/Indikator/yapi_referans.py", "ufuk_bar": UFUK, "tampon_atr": TAMPON_ATR,
             "rastgele_kosu": RASTGELE, "spread_varsayimi": SPREAD, "seriler": {}}
    olasilik: dict = {}
    div_tf: dict = {}
    paketler: list[dict] = []
    for tf in ZAMAN_DILIMLERI:
        satir_ens: dict[str, dict] = {}
        div_ens: dict[str, list[dict]] = {}
        R_paket: dict[tuple, list] = defaultdict(list)
        for ens, s in sorted(S[tf].items()):
            if len(s) < 600:
                continue
            y = Y.Yapi(s); m = Y.Momentum(s)
            kunye["seriler"][f"{ens}-{tf}"] = {"bar": len(s), "olay": len(y.olaylar), "fvg": len(y.fvgler), "ob": len(y.oblar),
                                                "prz": len(y.przler), "div": len(m.diverjanslar), "sweep": len(y.sweepler)}
            satir_ens[ens] = olay_olasiliklari(s, y, m)
            div_ens[ens] = diverjans_tablosu(s, y, m)
            for paket in PAKETLER:
                for hedef_R in (1.0, 2.0):
                    if paket == "diverjans" and hedef_R == 2.0:
                        continue      # hedef tablodan gelir
                    for sz in SUZGECLER:
                        oz = paket_kos(s, y, m, paket, hedef_R, SPREAD.get(ens, 0.0), sz)
                        oz.update({"tf": tf, "enstruman": ens, "paket": paket, "hedef_R": hedef_R, "suzgec": sz})
                        paketler.append(oz)
            print(f"  {ens}-{tf}: {len(s)} bar · olay {len(y.olaylar)} · prz {len(y.przler)} · {time.time()-t0:.0f} sn", flush=True)
        # TF toplamı: oranlar N ağırlıklı birleştirilir
        toplam: dict = {}
        anahtarlar = set(k for v in satir_ens.values() for k in v.keys())
        for k in anahtarlar:
            if k == "sweep_havuz":
                alt: dict[str, list] = defaultdict(list)
                for v in satir_ens.values():
                    for ad, o in v.get(k, {}).items():
                        alt[ad].append(o)
                toplam[k] = {ad: birlestir_oran(l) for ad, l in alt.items()}
            else:
                toplam[k] = birlestir_oran([v[k] for v in satir_ens.values() if k in v])
        olasilik[tf] = {"toplam": toplam, "enstruman": satir_ens}
        # diverjans tablosu TF toplamı
        div_tf[tf] = []
        for n_satir in range(len(Y.DIV_TABLO)):
            sat = [d[n_satir] for d in div_ens.values()]
            base = dict(sat[0]) if sat else {}
            base.update(birlestir_oran(sat))
            div_tf[tf].append(base)
    # paket toplamı (TF × paket × hedef × süzgeç): R listeleri yeniden kurulmaz; N ağırlıklı ortalama
    toplam_paket = []
    for tf in ZAMAN_DILIMLERI:
        for paket in PAKETLER:
            for hedef_R in (1.0, 2.0):
                for sz in SUZGECLER:
                    sat = [p for p in paketler if p["tf"] == tf and p["paket"] == paket and p["hedef_R"] == hedef_R and p["suzgec"] == sz and p.get("n")]
                    if not sat:
                        continue
                    n = sum(p["n"] for p in sat)
                    toplam_paket.append({"tf": tf, "paket": paket, "hedef_R": hedef_R, "suzgec": sz, "n": n, "seri": len(sat),
                                         "kazanma": round(sum(p["kazanma"] * p["n"] for p in sat) / n, 3),
                                         "ort_R": round(sum(p["ort_R"] * p["n"] for p in sat) / n, 3),
                                         "net_ort_R": round(sum((p["net_ort_R"] or 0) * p["n"] for p in sat) / n, 3),
                                         "rastgele_ort_R": round(sum((p.get("rastgele_ort_R") or 0) * p["n"] for p in sat) / n, 3),
                                         "ilk_yari_ort_R": round(sum((p["ilk_yari_ort_R"] or 0) * p["n"] for p in sat) / n, 3),
                                         "ikinci_yari_ort_R": round(sum((p["ikinci_yari_ort_R"] or 0) * p["n"] for p in sat) / n, 3),
                                         "seri_ustu_rastgele": sum(1 for p in sat if (p.get("rastgele_yuzdelik") or 0) >= 95)})
    kunye["sure_sn"] = round(time.time() - t0)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps({"kunye": kunye, "olasilik": olasilik, "diverjans": div_tf,
                                 "paket_toplam": toplam_paket, "paket": paketler}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"→ {CIKTI} ({kunye['sure_sn']} sn)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
