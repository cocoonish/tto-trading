#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haftalık teknik analiz bülteni — ÖLÇÜM katmanı.

Altı enstrüman (ABD 2Y, ABD 10Y, DXY, EUR/USD, USD/CHF, XU100) için grafik
tabanlı teknik analizin SAYISAL zeminini kurar: OHLC serileri, hareketli
ortalamalar, RSI/MACD, ATR, Bollinger, 52 haftalık aralık, pivot destek/direnç
kümeleri, regresyon kanalı ve Fibonacci düzeltme seviyeleri. Çıktı:

    site/src/data/teknik/<tarih>.json      ölçülen katman (yorum alanları boş)
    site/public/teknik/<slug>-gunluk.html  günlük mum grafiği + RSI + MACD
    site/public/teknik/<slug>-haftalik.html haftalık mum grafiği + RSI

YORUM BURADAN ÇIKMAZ. Trend okuması, seviye seçimi, senaryolar yazı katmanının
işidir (bkz. bulten/YAZIM.md, "Haftalık teknik analiz"); yazı katmanı yalnız
teknik/yaz.py üzerinden dokunabilir ve andığı her sayı burada ölçülmüş olmak
zorundadır. Ölçülmemiş bir seviye yorumda kullanılamaz — uydurma yok.

Bar disiplini (bkz. CLAUDE.md, "bir ölçüm ancak KAPANMIŞ bir seansı ölçebilir"):
· Günlük seride bugünün (UTC) barı düşürülür — kapanmamış seans ölçülmez.
· Haftalık barlar günlükten türetilir ve yalnız CUMASI GEÇMİŞ haftalar alınır;
  etiket haftanın son GERÇEK günüdür, gelecek tarihli kova üretilemez
  (net rezervin 27.08 "28 Aug" kovası dersi).
"""
from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
VERI = KOK / "site" / "src" / "data" / "teknik"
GRAFIK = KOK / "site" / "public" / "teknik"

GUNLUK_PENCERE = 260        # grafikte gösterilen günlük bar (≈ 1 yıl)
KANAL_GUN = 250             # regresyon kanalı penceresi
HAFTALIK_YIL = 5            # haftalık grafiğin derinliği


@dataclass(frozen=True)
class Enstruman:
    kod: str
    slug: str
    ad: str
    tip: str                # fiyat | getiri  (getiri → değişimler baz puan)
    ondalik: int
    birim: str = ""


ENSTRUMANLAR: tuple[Enstruman, ...] = (
    Enstruman("2YY=F", "us2y", "ABD 2 yıllık getiri", "getiri", 3, "%"),
    Enstruman("^TNX", "us10y", "ABD 10 yıllık getiri", "getiri", 3, "%"),
    Enstruman("DX-Y.NYB", "dxy", "Dolar endeksi (DXY)", "fiyat", 3),
    Enstruman("EURUSD=X", "eurusd", "EUR/USD", "fiyat", 4),
    Enstruman("USDCHF=X", "usdchf", "USD/CHF", "fiyat", 4),
    Enstruman("XU100.IS", "xu100", "BIST 100", "fiyat", 0, "puan"),
)


# ── gösterge matematiği (saf, ağsız — duman sınaması bunları çağırır) ────────

def sma(dizi: list[float], n: int) -> float | None:
    if len(dizi) < n:
        return None
    return sum(dizi[-n:]) / n


def rsi_wilder(kapanis: list[float], n: int = 14) -> float | None:
    """Wilder RSI: ilk ortalama basit, sonrası üstel (alpha = 1/n)."""
    if len(kapanis) < n + 1:
        return None
    farklar = [kapanis[i] - kapanis[i - 1] for i in range(1, len(kapanis))]
    kazanc = sum(max(f, 0.0) for f in farklar[:n]) / n
    kayip = sum(max(-f, 0.0) for f in farklar[:n]) / n
    for f in farklar[n:]:
        kazanc = (kazanc * (n - 1) + max(f, 0.0)) / n
        kayip = (kayip * (n - 1) + max(-f, 0.0)) / n
    if kayip == 0:
        return 100.0
    rs = kazanc / kayip
    return 100.0 - 100.0 / (1.0 + rs)


def _ema_seri(dizi: list[float], n: int) -> list[float]:
    alpha = 2.0 / (n + 1)
    out = [dizi[0]]
    for x in dizi[1:]:
        out.append(out[-1] + alpha * (x - out[-1]))
    return out


def macd(kapanis: list[float]) -> tuple[float, float, float] | None:
    """(macd, sinyal, histogram) — 12/26/9 EMA."""
    if len(kapanis) < 35:
        return None
    hat = [a - b for a, b in zip(_ema_seri(kapanis, 12), _ema_seri(kapanis, 26))]
    sinyal = _ema_seri(hat[25:], 9)      # 26. bardan itibaren anlamlı
    return hat[-1], sinyal[-1], hat[-1] - sinyal[-1]


def atr_wilder(yuksek: list[float], dusuk: list[float], kapanis: list[float],
               n: int = 14) -> float | None:
    if len(kapanis) < n + 1:
        return None
    tr = []
    for i in range(1, len(kapanis)):
        tr.append(max(yuksek[i] - dusuk[i],
                      abs(yuksek[i] - kapanis[i - 1]),
                      abs(dusuk[i] - kapanis[i - 1])))
    a = sum(tr[:n]) / n
    for x in tr[n:]:
        a = (a * (n - 1) + x) / n
    return a


def bollinger(kapanis: list[float], n: int = 20, k: float = 2.0
              ) -> tuple[float, float, float] | None:
    if len(kapanis) < n:
        return None
    p = kapanis[-n:]
    orta = sum(p) / n
    ss = math.sqrt(sum((x - orta) ** 2 for x in p) / n)
    return orta + k * ss, orta, orta - k * ss


def pivotlar(yuksek: list[float], dusuk: list[float], tarih: list[str],
             kanat: int = 3) -> tuple[list[tuple[float, str]], list[tuple[float, str]]]:
    """Fraktal salınım uçları: her iki yanındaki `kanat` bardan yüksek tepe /
    alçak dip. (seviye, tarih) listeleri döner — tepe ve dip ayrı."""
    tepeler, dipler = [], []
    for i in range(kanat, len(yuksek) - kanat):
        if yuksek[i] == max(yuksek[i - kanat:i + kanat + 1]):
            tepeler.append((yuksek[i], tarih[i]))
        if dusuk[i] == min(dusuk[i - kanat:i + kanat + 1]):
            dipler.append((dusuk[i], tarih[i]))
    return tepeler, dipler


def kumele(uclar: list[tuple[float, str]], tolerans: float
           ) -> list[dict]:
    """Yakın salınım uçlarını bölgelere toplar. Bölge seviyesi üye ortalaması;
    dokunuş sayısı ve son dokunuş tarihi ölçülür — 'iki kez test edilen seviye'
    yorumu buradan gelir, tahminden değil."""
    if not uclar:
        return []
    sirali = sorted(uclar)
    bolgeler: list[list[tuple[float, str]]] = [[sirali[0]]]
    for s, t in sirali[1:]:
        if s - bolgeler[-1][-1][0] <= tolerans:
            bolgeler[-1].append((s, t))
        else:
            bolgeler.append([(s, t)])
    out = []
    for b in bolgeler:
        out.append({"seviye": sum(x for x, _ in b) / len(b),
                    "dokunus": len(b),
                    "son_dokunus": max(t for _, t in b)})
    return out


def kanal(kapanis: list[float]) -> dict | None:
    """Son KANAL_GUN bara doğrusal regresyon; bant ±2σ artık. Eğim yıllık
    (%/yıl fiyatta, bp/yıl getiride değil — ham birim/yıl; okuma yazıda)."""
    p = kapanis[-KANAL_GUN:]
    n = len(p)
    if n < 60:
        return None
    xler = list(range(n))
    ox, oy = (n - 1) / 2.0, sum(p) / n
    pay = sum((x - ox) * (y - oy) for x, y in zip(xler, p))
    payda = sum((x - ox) ** 2 for x in xler)
    egim = pay / payda
    kesen = oy - egim * ox
    artik = [y - (egim * x + kesen) for x, y in zip(xler, p)]
    ss = math.sqrt(sum(a * a for a in artik) / n)
    orta = egim * (n - 1) + kesen
    ust, alt = orta + 2 * ss, orta - 2 * ss
    konum = None if ust == alt else (p[-1] - alt) / (ust - alt)
    return {"pencere_gun": n, "egim_gunluk": egim, "egim_yillik": egim * 252,
            "orta": orta, "ust": ust, "alt": alt,
            "konum": konum, "sigma": ss}


# ── bar disiplini ────────────────────────────────────────────────────────────

def kapanmis_gunler(tarih: list[str], *diziler: list[float]
                    ) -> tuple[list[str], list[list[float]]]:
    """Bugünün (UTC) barını düşürür: kapanmamış seans ölçülmez."""
    bugun = datetime.now(timezone.utc).date().isoformat()
    kes = len(tarih)
    while kes > 0 and tarih[kes - 1] >= bugun:
        kes -= 1
    return tarih[:kes], [d[:kes] for d in diziler]


def haftalik_kur(tarih: list[str], acilis, yuksek, dusuk, kapanis
                 ) -> dict[str, list]:
    """Günlükten haftalık bar türetir. Yalnız CUMASI GEÇMİŞ (tamamlanmış)
    haftalar; etiket haftanın son GERÇEK günü — gelecek tarih üretilemez."""
    bugun = datetime.now(timezone.utc).date()
    haftalar: dict[tuple[int, int], list[int]] = {}
    for i, t in enumerate(tarih):
        g = date.fromisoformat(t)
        iso = g.isocalendar()
        haftalar.setdefault((iso[0], iso[1]), []).append(i)
    out = {"tarih": [], "acilis": [], "yuksek": [], "dusuk": [], "kapanis": []}
    for (yil, hafta), idx in sorted(haftalar.items()):
        cuma = date.fromisocalendar(yil, hafta, 5)
        if cuma >= bugun:               # hafta kapanmadı → ölçülmez
            continue
        out["tarih"].append(tarih[idx[-1]])
        out["acilis"].append(acilis[idx[0]])
        out["yuksek"].append(max(yuksek[i] for i in idx))
        out["dusuk"].append(min(dusuk[i] for i in idx))
        out["kapanis"].append(kapanis[idx[-1]])
    return out


# ── veri çekimi ──────────────────────────────────────────────────────────────

def cek() -> dict[str, dict[str, list]]:
    """5 yıllık günlük OHLC, enstrüman başına. Ağa yalnız burada çıkılır."""
    import pandas as pd
    import yfinance as yf
    kodlar = [e.kod for e in ENSTRUMANLAR]
    ham = yf.download(kodlar, period=f"{HAFTALIK_YIL}y", interval="1d",
                      progress=False, auto_adjust=False, group_by="ticker",
                      threads=True)
    seriler: dict[str, dict[str, list]] = {}
    for kod in kodlar:
        try:
            blok = ham[kod] if isinstance(ham.columns, pd.MultiIndex) else ham
            blok = blok.dropna(subset=["Close"])
        except Exception:
            continue
        if len(blok) < 60:
            continue
        seriler[kod] = {
            "tarih": [str(x.date()) for x in blok.index],
            "acilis": [float(x) for x in blok["Open"]],
            "yuksek": [float(x) for x in blok["High"]],
            "dusuk": [float(x) for x in blok["Low"]],
            "kapanis": [float(x) for x in blok["Close"]],
        }
    return seriler


# ── enstrüman ölçümü ─────────────────────────────────────────────────────────

def _degisim(kapanis: list[float], geri: int, getiri: bool) -> float | None:
    if len(kapanis) <= geri:
        return None
    once, simdi = kapanis[-1 - geri], kapanis[-1]
    if getiri:
        return (simdi - once) * 100.0          # baz puan
    return (simdi / once - 1.0) * 100.0 if once else None


def olc_enstruman(e: Enstruman, s: dict[str, list]) -> dict | None:
    tarih, (acilis, yuksek, dusuk, kapanis) = kapanmis_gunler(
        s["tarih"], s["acilis"], s["yuksek"], s["dusuk"], s["kapanis"])
    if len(kapanis) < 60:
        return None
    if e.tip == "getiri" and not (0.0 < kapanis[-1] < 25.0):
        raise SystemExit(f"{e.kod}: getiri {kapanis[-1]} — kotasyon ölçeği "
                         "beklenenden farklı, seri güvenilmez")
    son = kapanis[-1]
    getiri = e.tip == "getiri"

    y252 = kapanis[-252:]
    yh, yl = max(yuksek[-252:]), min(dusuk[-252:])
    konum52 = None if yh == yl else (son - yl) / (yh - yl) * 100.0

    # yılbaşından bu yana
    ybb = None
    for i, t in enumerate(tarih):
        if t >= f"{tarih[-1][:4]}-01-01":
            ybb = ((son - kapanis[i - 1]) * 100.0 if getiri else
                   (son / kapanis[i - 1] - 1.0) * 100.0) if i > 0 else None
            break

    a = atr_wilder(yuksek, dusuk, kapanis)
    tepe, dip = pivotlar(yuksek[-KANAL_GUN:], dusuk[-KANAL_GUN:],
                         tarih[-KANAL_GUN:])
    tol = (a * 0.75) if a else (yh - yl) * 0.01
    direnc = [b for b in kumele(tepe, tol) if b["seviye"] > son]
    destek = [b for b in kumele(dip, tol) if b["seviye"] < son]
    direnc.sort(key=lambda b: b["seviye"])
    destek.sort(key=lambda b: -b["seviye"])

    bb = bollinger(kapanis)
    md = macd(kapanis)

    hft = haftalik_kur(tarih, acilis, yuksek, dusuk, kapanis)
    hkap = hft["kapanis"]

    fib_taban, fib_tavan = yl, yh
    fib = {f"s{int(o*1000)}": fib_tavan - (fib_tavan - fib_taban) * o
           for o in (0.382, 0.5, 0.618)}

    kn = kanal(kapanis)
    r = lambda x, n=e.ondalik: (None if x is None else round(x, max(n, 2)))
    return {
        "kod": e.kod, "slug": e.slug, "ad": e.ad, "tip": e.tip,
        "birim": e.birim, "ondalik": e.ondalik,
        "bar_tarihi": tarih[-1],
        "hafta_tarihi": hft["tarih"][-1] if hft["tarih"] else None,
        "son": r(son, e.ondalik),
        "degisim": {           # getiri: baz puan · fiyat: yüzde
            "g1": r(_degisim(kapanis, 1, getiri)),
            "h1": r(_degisim(kapanis, 5, getiri)),
            "a1": r(_degisim(kapanis, 21, getiri)),
            "a3": r(_degisim(kapanis, 63, getiri)),
            "ybb": r(ybb),
        },
        "aralik52": {"yuksek": r(yh, e.ondalik), "dusuk": r(yl, e.ondalik),
                     "konum_pct": r(konum52)},
        "hareketli": {"g20": r(sma(kapanis, 20), e.ondalik),
                      "g50": r(sma(kapanis, 50), e.ondalik),
                      "g100": r(sma(kapanis, 100), e.ondalik),
                      "g200": r(sma(kapanis, 200), e.ondalik),
                      "h10": r(sma(hkap, 10), e.ondalik),
                      "h40": r(sma(hkap, 40), e.ondalik)},
        "momentum": {"rsi14_g": r(rsi_wilder(kapanis)),
                     "rsi14_h": r(rsi_wilder(hkap)),
                     "macd": r(md[0], e.ondalik + 1) if md else None,
                     "macd_sinyal": r(md[1], e.ondalik + 1) if md else None,
                     "macd_hist": r(md[2], e.ondalik + 1) if md else None},
        "oynaklik": {"atr14": r(a, e.ondalik),
                     "atr14_pct": r(a / son * 100.0) if a and son else None},
        "bant": ({"ust": r(bb[0], e.ondalik), "orta": r(bb[1], e.ondalik),
                  "alt": r(bb[2], e.ondalik)} if bb else None),
        "kanal": (kn and {
            "pencere_gun": kn["pencere_gun"],
            "egim_yillik": r(kn["egim_yillik"], e.ondalik),
            "orta": r(kn["orta"], e.ondalik), "ust": r(kn["ust"], e.ondalik),
            "alt": r(kn["alt"], e.ondalik),
            "konum_pct": r(kn["konum"] * 100.0) if kn["konum"] is not None else None,
        }) or None,
        "seviyeler": {
            "direnc": [{"seviye": r(b["seviye"], e.ondalik),
                        "dokunus": b["dokunus"],
                        "son_dokunus": b["son_dokunus"]} for b in direnc[:4]],
            "destek": [{"seviye": r(b["seviye"], e.ondalik),
                        "dokunus": b["dokunus"],
                        "son_dokunus": b["son_dokunus"]} for b in destek[:4]],
            "fib": {k: r(v, e.ondalik) for k, v in fib.items()},
            "fib_aciklama": "52 haftalık aralığın (yüksekten alçağa) "
                            "%38,2 / %50 / %61,8 düzeltmeleri",
        },
        "grafikler": {"gunluk": f"/teknik/{e.slug}-gunluk.html",
                      "haftalik": f"/teknik/{e.slug}-haftalik.html"},
        "yorum": None,
        "_gunluk": {"tarih": tarih[-GUNLUK_PENCERE:],
                    "acilis": acilis[-GUNLUK_PENCERE:],
                    "yuksek": yuksek[-GUNLUK_PENCERE:],
                    "dusuk": dusuk[-GUNLUK_PENCERE:],
                    "kapanis": kapanis[-GUNLUK_PENCERE:]},
        "_haftalik": hft,
        "_kanal_ham": kn,
        "_sma_serileri": {
            "g50": _sma_seri(kapanis, 50)[-GUNLUK_PENCERE:],
            "g200": _sma_seri(kapanis, 200)[-GUNLUK_PENCERE:],
        },
    }


def _sma_seri(dizi: list[float], n: int) -> list:
    out: list = []
    toplam = 0.0
    for i, x in enumerate(dizi):
        toplam += x
        if i >= n:
            toplam -= dizi[i - n]
        out.append(toplam / n if i >= n - 1 else None)
    return out


# ── grafikler ────────────────────────────────────────────────────────────────

def ciz(e: Enstruman, m: dict) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    g = m["_gunluk"]
    rsi_seri = _rsi_seri(g["kapanis"])
    macd_seri = _macd_seriler(g["kapanis"])

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.62, 0.19, 0.19], vertical_spacing=0.03,
                        subplot_titles=("", "RSI(14)", "MACD(12,26,9)"))
    fig.add_trace(go.Candlestick(
        x=g["tarih"], open=g["acilis"], high=g["yuksek"],
        low=g["dusuk"], close=g["kapanis"], name=e.ad,
        increasing_line_color="#2d6a4f", decreasing_line_color="#9d2235",
        showlegend=False), row=1, col=1)
    for ad, seri, renk in (("SMA50", m["_sma_serileri"]["g50"], "#b8860b"),
                           ("SMA200", m["_sma_serileri"]["g200"], "#365f91")):
        fig.add_trace(go.Scatter(x=g["tarih"], y=seri, name=ad,
                                 line=dict(width=1.4, color=renk)), row=1, col=1)
    k = m["_kanal_ham"]
    if k:
        n = k["pencere_gun"]
        xs = g["tarih"][-n:]
        for etiket, kes in (("kanal üst", 2), ("kanal orta", 0), ("kanal alt", -2)):
            ys = [k["egim_gunluk"] * i + (k["orta"] - k["egim_gunluk"] * (n - 1))
                  + kes * k["sigma"] for i in range(n)]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, name=etiket, line=dict(
                    width=1, dash="dot" if kes else "dash", color="#8a8a8a"),
                showlegend=(kes == 2)), row=1, col=1)
    for yon, isaret in (("direnc", "#9d2235"), ("destek", "#2d6a4f")):
        for b in m["seviyeler"][yon]:
            fig.add_hline(y=b["seviye"], line_width=1, line_dash="dash",
                          line_color=isaret, opacity=0.55, row=1, col=1,
                          annotation_text=f"{b['seviye']} ({b['dokunus']}x)",
                          annotation_font_size=10)
    fig.add_trace(go.Scatter(x=g["tarih"], y=rsi_seri, name="RSI",
                             line=dict(width=1.2, color="#5f4b8b"),
                             showlegend=False), row=2, col=1)
    for esik in (30, 70):
        fig.add_hline(y=esik, line_width=0.8, line_dash="dot",
                      line_color="#999", row=2, col=1)
    fig.add_trace(go.Bar(x=g["tarih"], y=macd_seri["hist"], name="hist",
                         marker_color="#b0b0b0", showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=g["tarih"], y=macd_seri["macd"], name="MACD",
                             line=dict(width=1.1, color="#365f91"),
                             showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=g["tarih"], y=macd_seri["sinyal"], name="sinyal",
                             line=dict(width=1.1, color="#b8860b"),
                             showlegend=False), row=3, col=1)
    fig.update_layout(
        title=f"{e.ad} — günlük ({g['tarih'][0]} → {g['tarih'][-1]})",
        xaxis_rangeslider_visible=False, height=760,
        legend=dict(orientation="h"))
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    GRAFIK.mkdir(parents=True, exist_ok=True)
    fig.write_html(GRAFIK / f"{e.slug}-gunluk.html",
                   include_plotlyjs="cdn", full_html=True)

    h = m["_haftalik"]
    rsi_h = _rsi_seri(h["kapanis"])
    fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                         row_heights=[0.75, 0.25], vertical_spacing=0.04,
                         subplot_titles=("", "RSI(14) haftalık"))
    fig2.add_trace(go.Candlestick(
        x=h["tarih"], open=h["acilis"], high=h["yuksek"],
        low=h["dusuk"], close=h["kapanis"], name=e.ad,
        increasing_line_color="#2d6a4f", decreasing_line_color="#9d2235",
        showlegend=False), row=1, col=1)
    for ad, n, renk in (("SMA10h", 10, "#b8860b"), ("SMA40h", 40, "#365f91")):
        fig2.add_trace(go.Scatter(x=h["tarih"], y=_sma_seri(h["kapanis"], n),
                                  name=ad, line=dict(width=1.4, color=renk)),
                       row=1, col=1)
    fig2.add_trace(go.Scatter(x=h["tarih"], y=rsi_h, name="RSI",
                              line=dict(width=1.2, color="#5f4b8b"),
                              showlegend=False), row=2, col=1)
    for esik in (30, 70):
        fig2.add_hline(y=esik, line_width=0.8, line_dash="dot",
                       line_color="#999", row=2, col=1)
    fig2.update_layout(
        title=f"{e.ad} — haftalık ({h['tarih'][0]} → {h['tarih'][-1]})",
        xaxis_rangeslider_visible=False, height=620,
        legend=dict(orientation="h"))
    fig2.write_html(GRAFIK / f"{e.slug}-haftalik.html",
                    include_plotlyjs="cdn", full_html=True)


def _rsi_seri(kapanis: list[float], n: int = 14) -> list:
    out: list = [None] * len(kapanis)
    for i in range(n, len(kapanis)):
        out[i] = rsi_wilder(kapanis[:i + 1], n)
    return out


def _macd_seriler(kapanis: list[float]) -> dict[str, list]:
    if len(kapanis) < 35:
        b = [None] * len(kapanis)
        return {"macd": b, "sinyal": b, "hist": b}
    hat = [a - b for a, b in zip(_ema_seri(kapanis, 12), _ema_seri(kapanis, 26))]
    sinyal_kuyruk = _ema_seri(hat[25:], 9)
    sinyal = [None] * 25 + sinyal_kuyruk
    hist = [None if s is None else m - s for m, s in zip(hat, sinyal)]
    return {"macd": hat, "sinyal": sinyal, "hist": hist}


# ── ana akış ─────────────────────────────────────────────────────────────────

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def main() -> int:
    seriler = cek()
    eksik = [e.kod for e in ENSTRUMANLAR if e.kod not in seriler]
    if eksik:
        raise SystemExit(f"veri çekilemedi: {', '.join(eksik)} — "
                         "eksik enstrümanla teknik bülten kurulmaz")
    bugun = datetime.now(timezone.utc).date()
    kayit = {
        "tarih": bugun.isoformat(),
        "tr_tarih": f"{bugun.day} {AYLAR[bugun.month]} {bugun.year}",
        "olcum_zamani": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "yazili": False,
        "giris": None,
        "enstrumanlar": [],
    }
    for e in ENSTRUMANLAR:
        m = olc_enstruman(e, seriler[e.kod])
        if m is None:
            raise SystemExit(f"{e.kod}: seri çok kısa, ölçüm kurulamadı")
        ciz(e, m)
        for gecici in ("_gunluk", "_haftalik", "_kanal_ham", "_sma_serileri"):
            m.pop(gecici, None)
        kayit["enstrumanlar"].append(m)
        print(f"  {e.ad:26s} son={m['son']}  bar={m['bar_tarihi']}  "
              f"RSI={m['momentum']['rsi14_g']}")
    kayit["veri_ucu"] = min(m["bar_tarihi"] for m in kayit["enstrumanlar"])
    VERI.mkdir(parents=True, exist_ok=True)
    hedef = VERI / f"{kayit['tarih']}.json"
    # Yazılmış teknik bülten ezilmez — bülten katmanıyla aynı kapı.
    if hedef.exists():
        eski = json.loads(hedef.read_text(encoding="utf-8"))
        if eski.get("yazili"):
            print(f"{hedef.name} yazılmış — ölçüm onu ezmez, çıkılıyor")
            return 0
    hedef.write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    print(f"yazıldı: {hedef}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
