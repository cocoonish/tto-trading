#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haftalık teknik analiz bülteni — ÖLÇÜM katmanı (çok zaman dilimli).

Altı enstrüman (ABD 2Y, ABD 10Y, DXY, EUR/USD, USD/CHF, XU100) için teknik
analizin SAYISAL zeminini ÜÇ zaman diliminde kurar: 1 saatlik, 4 saatlik ve
günlük. Her dilimde aynı gösterge seti ölçülür (SMA'lar, RSI, MACD, ATR,
Bollinger, pivot destek/direnç kümeleri, regresyon kanalı) + YAPI ölçümü:
son salınım tepeleri/dipleri, yönleri (yükselen/alçalan/yatay), çift tepe/dip
ve sıkışma bayrakları — formasyon adlandırması yazı katmanının işidir ama
dayanacağı noktalar burada ölçülür. Çıktı:

    site/src/data/teknik/<tarih>.json    ölçülen katman (yorum alanları boş)
    site/public/teknik/<slug>-s1.html    1 saatlik mum + RSI + MACD
    site/public/teknik/<slug>-s4.html    4 saatlik mum + RSI + MACD
    site/public/teknik/<slug>-gunluk.html günlük mum + RSI + MACD

YORUM BURADAN ÇIKMAZ (bkz. bulten/YAZIM.md, "Haftalık teknik analiz"); yazı
katmanı teknik/yaz.py kapısından geçer ve andığı her sayı burada ölçülmüş
olmak zorundadır — uydurma yok.

Bar disiplini (CLAUDE.md: "bir ölçüm ancak KAPANMIŞ bir seansı ölçebilir"):
· Günlükte bugünün (UTC) barı düşürülür.
· Saatlikte kapanmamış saat düşürülür (bar başlangıcı + 1 saat > şimdi).
· 4 saatlik barlar kapanmış 1 saatliklerden kurulur (UTC 00/04/08… çıpalı);
  süresi dolmamış son kova düşürülür, kova etiketi içindeki son GERÇEK bar.
· Haftalık seri (yalnız gösterge bağlamı: h10/h40, haftalık RSI) günlükten,
  yalnız cuması geçmiş haftalardan türetilir.
"""
from __future__ import annotations

import argparse
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

KANAL_BAR = 250             # regresyon kanalı penceresi (her dilimde bar sayısı)
HAFTALIK_YIL = 5            # günlük çekimin derinliği
SAATLIK_DONEM = "6mo"       # 1 saatlik çekimin derinliği (Yahoo sınırı 730 gün)


@dataclass(frozen=True)
class Enstruman:
    kod: str
    slug: str
    ad: str
    tip: str                # fiyat | getiri
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

# (kod, ad, grafikte gösterilen bar, pivot kanadı)
DILIMLER = (
    ("s1", "1 saatlik", 420, 5),
    ("s4", "4 saatlik", 360, 4),
    ("gun", "günlük", 260, 3),
)


# ── gösterge matematiği (saf, ağsız — duman sınaması bunları çağırır) ────────

def sma(dizi: list[float], n: int) -> float | None:
    if len(dizi) < n:
        return None
    return sum(dizi[-n:]) / n


def rsi_wilder(kapanis: list[float], n: int = 14) -> float | None:
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
    return 100.0 - 100.0 / (1.0 + kazanc / kayip)


def _ema_seri(dizi: list[float], n: int) -> list[float]:
    alpha = 2.0 / (n + 1)
    out = [dizi[0]]
    for x in dizi[1:]:
        out.append(out[-1] + alpha * (x - out[-1]))
    return out


def macd(kapanis: list[float]) -> tuple[float, float, float] | None:
    if len(kapanis) < 35:
        return None
    hat = [a - b for a, b in zip(_ema_seri(kapanis, 12), _ema_seri(kapanis, 26))]
    sinyal = _ema_seri(hat[25:], 9)
    return hat[-1], sinyal[-1], hat[-1] - sinyal[-1]


def atr_wilder(yuksek, dusuk, kapanis, n: int = 14) -> float | None:
    if len(kapanis) < n + 1:
        return None
    tr = [max(yuksek[i] - dusuk[i],
              abs(yuksek[i] - kapanis[i - 1]),
              abs(dusuk[i] - kapanis[i - 1])) for i in range(1, len(kapanis))]
    a = sum(tr[:n]) / n
    for x in tr[n:]:
        a = (a * (n - 1) + x) / n
    return a


def bollinger(kapanis, n: int = 20, k: float = 2.0):
    if len(kapanis) < n:
        return None
    p = kapanis[-n:]
    orta = sum(p) / n
    ss = math.sqrt(sum((x - orta) ** 2 for x in p) / n)
    return orta + k * ss, orta, orta - k * ss


def pivotlar(yuksek, dusuk, zaman, kanat: int = 3):
    """Fraktal salınım uçları: iki yanındaki `kanat` bardan yüksek tepe /
    alçak dip → (seviye, zaman) listeleri, kronolojik."""
    tepeler, dipler = [], []
    for i in range(kanat, len(yuksek) - kanat):
        if yuksek[i] == max(yuksek[i - kanat:i + kanat + 1]):
            tepeler.append((yuksek[i], zaman[i]))
        if dusuk[i] == min(dusuk[i - kanat:i + kanat + 1]):
            dipler.append((dusuk[i], zaman[i]))
    return tepeler, dipler


def kumele(uclar, tolerans: float):
    if not uclar:
        return []
    sirali = sorted(uclar)
    bolgeler = [[sirali[0]]]
    for s, t in sirali[1:]:
        if s - bolgeler[-1][-1][0] <= tolerans:
            bolgeler[-1].append((s, t))
        else:
            bolgeler.append([(s, t)])
    return [{"seviye": sum(x for x, _ in b) / len(b),
             "dokunus": len(b),
             "son_dokunus": max(t for _, t in b)} for b in bolgeler]


def kanal(kapanis: list[float], pencere: int = KANAL_BAR) -> dict | None:
    p = kapanis[-pencere:]
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
    konum = None if ss == 0 else (p[-1] - (orta - 2 * ss)) / (4 * ss)
    return {"pencere": n, "egim_bar": egim, "orta": orta,
            "ust": orta + 2 * ss, "alt": orta - 2 * ss,
            "konum": konum, "sigma": ss}


# ── YAPI ölçümü: formasyonların sayısal zemini ───────────────────────────────

def _yon(a: float, b: float, esik: float) -> str:
    """b, a'ya göre: yükselen / alçalan / yatay (eşik = 0,25×ATR)."""
    if b - a > esik:
        return "yukselen"
    if a - b > esik:
        return "alcalan"
    return "yatay"


def yapi_olc(tepeler, dipler, atr: float | None) -> dict:
    """Son salınım uçlarından piyasa yapısı. Formasyon ADI vermez — çift
    tepe/dip ve sıkışma gibi sayısal olarak tanımlı bayrakları ölçer, yazı
    katmanı adlandırmayı bu noktalara dayanarak yapar."""
    esik = (atr or 0.0) * 0.25
    yakin = (atr or 0.0) * 0.35
    son_t = tepeler[-3:]
    son_d = dipler[-3:]
    out: dict = {
        "tepeler": [{"seviye": s, "zaman": z} for s, z in son_t],
        "dipler": [{"seviye": s, "zaman": z} for s, z in son_d],
        "tepe_yonu": None, "dip_yonu": None, "karakter": None,
        "cift_tepe": None, "cift_dip": None, "sikisma": False,
    }
    if len(son_t) >= 2:
        out["tepe_yonu"] = _yon(son_t[-2][0], son_t[-1][0], esik)
        if abs(son_t[-1][0] - son_t[-2][0]) <= yakin:
            out["cift_tepe"] = {"seviye": (son_t[-1][0] + son_t[-2][0]) / 2,
                                "zamanlar": [son_t[-2][1], son_t[-1][1]]}
    if len(son_d) >= 2:
        out["dip_yonu"] = _yon(son_d[-2][0], son_d[-1][0], esik)
        if abs(son_d[-1][0] - son_d[-2][0]) <= yakin:
            out["cift_dip"] = {"seviye": (son_d[-1][0] + son_d[-2][0]) / 2,
                               "zamanlar": [son_d[-2][1], son_d[-1][1]]}
    ty, dy = out["tepe_yonu"], out["dip_yonu"]
    if ty and dy:
        out["karakter"] = {
            ("yukselen", "yukselen"): "yükseliş yapısı (tepeler ve dipler yükseliyor)",
            ("alcalan", "alcalan"): "düşüş yapısı (tepeler ve dipler alçalıyor)",
            ("alcalan", "yukselen"): "sıkışma (alçalan tepeler, yükselen dipler)",
            ("yukselen", "alcalan"): "genişleme (yükselen tepeler, alçalan dipler)",
        }.get((ty, dy), f"karışık (tepeler {ty}, dipler {dy})".replace(
            "yukselen", "yükseliyor").replace("alcalan", "alçalıyor").replace(
            "yatay", "yatay"))
        out["sikisma"] = (ty, dy) == ("alcalan", "yukselen")
    return out


# ── bar disiplini ────────────────────────────────────────────────────────────

def kapanmis_gunler(tarih, *diziler):
    bugun = datetime.now(timezone.utc).date().isoformat()
    kes = len(tarih)
    while kes > 0 and tarih[kes - 1] >= bugun:
        kes -= 1
    return tarih[:kes], [d[:kes] for d in diziler]


def kapanmis_saatler(zaman, *diziler, saat: int = 1):
    """ISO (UTC) saat damgalı barlardan kapanmamış olanı düşürür:
    bar başlangıcı + `saat` > şimdi ise bar hâlâ oluşuyordur."""
    simdi = datetime.now(timezone.utc)
    kes = len(zaman)
    while kes > 0:
        t = datetime.fromisoformat(zaman[kes - 1]).replace(tzinfo=timezone.utc)
        if t + timedelta(hours=saat) <= simdi:
            break
        kes -= 1
    return zaman[:kes], [d[:kes] for d in diziler]


def s4_kur(zaman, acilis, yuksek, dusuk, kapanis) -> dict[str, list]:
    """Kapanmış 1 saatlik barlardan 4 saatlik bar (UTC 00/04/08… çıpalı).
    Süresi dolmamış son kova düşürülür; kova etiketi içindeki son GERÇEK bar."""
    simdi = datetime.now(timezone.utc)
    kovalar: dict[tuple, list[int]] = {}
    for i, z in enumerate(zaman):
        t = datetime.fromisoformat(z)
        kovalar.setdefault((t.date(), t.hour // 4), []).append(i)
    out = {"zaman": [], "acilis": [], "yuksek": [], "dusuk": [], "kapanis": []}
    for (gun, blok), idx in sorted(kovalar.items()):
        bitis = datetime(gun.year, gun.month, gun.day, blok * 4,
                         tzinfo=timezone.utc) + timedelta(hours=4)
        if bitis > simdi:                # kova süresi dolmadı → ölçülmez
            continue
        out["zaman"].append(zaman[idx[-1]])
        out["acilis"].append(acilis[idx[0]])
        out["yuksek"].append(max(yuksek[i] for i in idx))
        out["dusuk"].append(min(dusuk[i] for i in idx))
        out["kapanis"].append(kapanis[idx[-1]])
    return out


def haftalik_kur(tarih, acilis, yuksek, dusuk, kapanis) -> dict[str, list]:
    bugun = datetime.now(timezone.utc).date()
    haftalar: dict[tuple[int, int], list[int]] = {}
    for i, t in enumerate(tarih):
        iso = date.fromisoformat(t).isocalendar()
        haftalar.setdefault((iso[0], iso[1]), []).append(i)
    out = {"tarih": [], "kapanis": []}
    for (yil, hafta), idx in sorted(haftalar.items()):
        if date.fromisocalendar(yil, hafta, 5) >= bugun:
            continue
        out["tarih"].append(tarih[idx[-1]])
        out["kapanis"].append(kapanis[idx[-1]])
    return out


# ── veri çekimi ──────────────────────────────────────────────────────────────

def cek() -> dict[str, dict]:
    """Enstrüman başına {gunluk: OHLC(5y), saatlik: OHLC(6mo) | None}.
    Saatlik veri kaynak tarafında eksikse dürüstçe None taşınır."""
    import pandas as pd
    import yfinance as yf
    kodlar = [e.kod for e in ENSTRUMANLAR]

    def coz(ham, kod, saatlik: bool):
        try:
            blok = ham[kod] if isinstance(ham.columns, pd.MultiIndex) else ham
            blok = blok.dropna(subset=["Close"])
        except Exception:
            return None
        if len(blok) < (120 if saatlik else 60):
            return None
        if saatlik:
            idx = blok.index.tz_convert("UTC") if blok.index.tz is not None \
                else blok.index.tz_localize("UTC")
            zaman = [t.strftime("%Y-%m-%dT%H:%M") for t in idx]
        else:
            zaman = [str(x.date()) for x in blok.index]
        return {"zaman": zaman,
                "acilis": [float(x) for x in blok["Open"]],
                "yuksek": [float(x) for x in blok["High"]],
                "dusuk": [float(x) for x in blok["Low"]],
                "kapanis": [float(x) for x in blok["Close"]]}

    g = yf.download(kodlar, period=f"{HAFTALIK_YIL}y", interval="1d",
                    progress=False, auto_adjust=False, group_by="ticker",
                    threads=True)
    s = yf.download(kodlar, period=SAATLIK_DONEM, interval="1h",
                    progress=False, auto_adjust=False, group_by="ticker",
                    threads=True)
    return {kod: {"gunluk": coz(g, kod, False), "saatlik": coz(s, kod, True)}
            for kod in kodlar}


# ── dilim ölçümü ─────────────────────────────────────────────────────────────

def _sma_seri(dizi, n):
    out, toplam = [], 0.0
    for i, x in enumerate(dizi):
        toplam += x
        if i >= n:
            toplam -= dizi[i - n]
        out.append(toplam / n if i >= n - 1 else None)
    return out


def olc_dilim(e: Enstruman, zaman, acilis, yuksek, dusuk, kapanis,
              kanat: int) -> tuple[dict, dict]:
    """Bir zaman diliminin ölçümü. (json_dilim, cizim_ham) döner."""
    son = kapanis[-1]
    a = atr_wilder(yuksek, dusuk, kapanis)
    tepe, dip = pivotlar(yuksek[-KANAL_BAR:], dusuk[-KANAL_BAR:],
                         zaman[-KANAL_BAR:], kanat)
    tol = (a * 0.75) if a else (max(yuksek) - min(dusuk)) * 0.01
    direnc = sorted([b for b in kumele(tepe, tol) if b["seviye"] > son],
                    key=lambda b: b["seviye"])
    destek = sorted([b for b in kumele(dip, tol) if b["seviye"] < son],
                    key=lambda b: -b["seviye"])
    bb = bollinger(kapanis)
    md = macd(kapanis)
    kn = kanal(kapanis)
    yp = yapi_olc(tepe, dip, a)

    r = lambda x, n=e.ondalik: (None if x is None else round(x, max(n, 2)))
    js = {
        "son": r(son),
        "bar_zamani": zaman[-1],
        "pencere": {"bar": len(kapanis), "baslangic": zaman[0]},
        "hareketli": {f"g{n}": r(sma(kapanis, n)) for n in (20, 50, 100, 200)},
        "momentum": {"rsi14": r(rsi_wilder(kapanis)),
                     "macd": r(md[0], e.ondalik + 1) if md else None,
                     "macd_sinyal": r(md[1], e.ondalik + 1) if md else None,
                     "macd_hist": r(md[2], e.ondalik + 1) if md else None},
        "oynaklik": {"atr14": r(a),
                     "atr14_pct": r(a / son * 100.0) if a and son else None},
        "bant": ({"ust": r(bb[0]), "orta": r(bb[1]), "alt": r(bb[2])}
                 if bb else None),
        "kanal": ({"pencere_bar": kn["pencere"],
                   "orta": r(kn["orta"]), "ust": r(kn["ust"]),
                   "alt": r(kn["alt"]),
                   "konum_pct": r(kn["konum"] * 100.0)
                   if kn["konum"] is not None else None} if kn else None),
        "seviyeler": {
            "direnc": [{"seviye": r(b["seviye"]), "dokunus": b["dokunus"],
                        "son_dokunus": b["son_dokunus"]} for b in direnc[:3]],
            "destek": [{"seviye": r(b["seviye"]), "dokunus": b["dokunus"],
                        "son_dokunus": b["son_dokunus"]} for b in destek[:3]],
        },
        "yapi": {
            "tepeler": [{"seviye": r(t["seviye"]), "zaman": t["zaman"]}
                        for t in yp["tepeler"]],
            "dipler": [{"seviye": r(t["seviye"]), "zaman": t["zaman"]}
                       for t in yp["dipler"]],
            "karakter": yp["karakter"],
            "cift_tepe": ({"seviye": r(yp["cift_tepe"]["seviye"]),
                           "zamanlar": yp["cift_tepe"]["zamanlar"]}
                          if yp["cift_tepe"] else None),
            "cift_dip": ({"seviye": r(yp["cift_dip"]["seviye"]),
                          "zamanlar": yp["cift_dip"]["zamanlar"]}
                         if yp["cift_dip"] else None),
            "sikisma": yp["sikisma"],
        },
    }
    ham = {"zaman": zaman, "acilis": acilis, "yuksek": yuksek,
           "dusuk": dusuk, "kapanis": kapanis, "kanal": kn,
           "seviyeler": js["seviyeler"]}
    return js, ham


def olc_enstruman(e: Enstruman, s: dict) -> tuple[dict, dict]:
    """Üç dilimli ölçüm. (json_enstruman, {dilim: cizim_ham}) döner."""
    g = s["gunluk"]
    if not g:
        raise SystemExit(f"{e.kod}: günlük seri yok — teknik bülten kurulmaz")
    tarih, (ga, gy, gd, gk) = kapanmis_gunler(
        g["zaman"], g["acilis"], g["yuksek"], g["dusuk"], g["kapanis"])
    if len(gk) < 60:
        raise SystemExit(f"{e.kod}: günlük seri çok kısa ({len(gk)} bar)")
    if e.tip == "getiri" and not (0.0 < gk[-1] < 25.0):
        raise SystemExit(f"{e.kod}: getiri {gk[-1]} — kotasyon ölçeği "
                         "beklenenden farklı, seri güvenilmez")
    son, getiri = gk[-1], e.tip == "getiri"

    def deg(geri):
        if len(gk) <= geri:
            return None
        once = gk[-1 - geri]
        return (son - once) * 100.0 if getiri else \
            ((son / once - 1.0) * 100.0 if once else None)

    ybb = None
    for i, t in enumerate(tarih):
        if t >= f"{tarih[-1][:4]}-01-01" and i > 0:
            once = gk[i - 1]
            ybb = (son - once) * 100.0 if getiri else (son / once - 1.0) * 100.0
            break

    yh, yl = max(gy[-252:]), min(gd[-252:])
    hft = haftalik_kur(tarih, ga, gy, gd, gk)
    r = lambda x, n=e.ondalik: (None if x is None else round(x, max(n, 2)))

    dilimler: dict[str, dict] = {}
    hamlar: dict[str, dict] = {}
    js_gun, ham_gun = olc_dilim(e, tarih, ga, gy, gd, gk, kanat=3)
    dilimler["gun"], hamlar["gun"] = js_gun, ham_gun

    st = s.get("saatlik")
    if st:
        z1, (a1, y1, d1, k1) = kapanmis_saatler(
            st["zaman"], st["acilis"], st["yuksek"], st["dusuk"], st["kapanis"])
        if len(k1) >= 120:
            js1, ham1 = olc_dilim(e, z1, a1, y1, d1, k1, kanat=5)
            dilimler["s1"], hamlar["s1"] = js1, ham1
            k4 = s4_kur(z1, a1, y1, d1, k1)
            if len(k4["kapanis"]) >= 60:
                js4, ham4 = olc_dilim(e, k4["zaman"], k4["acilis"],
                                      k4["yuksek"], k4["dusuk"],
                                      k4["kapanis"], kanat=4)
                dilimler["s4"], hamlar["s4"] = js4, ham4
    for kod, _, _, _ in DILIMLER:
        if kod not in dilimler:
            dilimler[kod] = {"eksik": "kaynakta bu dilim için yeterli veri yok"}

    js = {
        "kod": e.kod, "slug": e.slug, "ad": e.ad, "tip": e.tip,
        "birim": e.birim, "ondalik": e.ondalik,
        "bar_tarihi": tarih[-1],
        "son": r(son),
        "degisim": {"g1": r(deg(1)), "h1": r(deg(5)), "a1": r(deg(21)),
                    "a3": r(deg(63)), "ybb": r(ybb)},
        "aralik52": {"yuksek": r(yh), "dusuk": r(yl),
                     "konum_pct": r((son - yl) / (yh - yl) * 100.0)
                     if yh != yl else None},
        "fib": {**{k: r(yh - (yh - yl) * o) for k, o in
                   (("s382", 0.382), ("s500", 0.5), ("s618", 0.618))},
                "aciklama": "52 haftalık aralığın %38,2 / %50 / %61,8 düzeltmeleri"},
        "haftalik": {"h10": r(sma(hft["kapanis"], 10)),
                     "h40": r(sma(hft["kapanis"], 40)),
                     "rsi14": r(rsi_wilder(hft["kapanis"])),
                     "hafta_tarihi": hft["tarih"][-1] if hft["tarih"] else None},
        "dilimler": dilimler,
        "grafikler": {kod: f"/teknik/{e.slug}-{'gunluk' if kod == 'gun' else kod}.html"
                      for kod, _, _, _ in DILIMLER if "eksik" not in dilimler[kod]},
        "yorum": None,
    }
    return js, hamlar


# ── grafikler ────────────────────────────────────────────────────────────────

def ciz_dilim(e: Enstruman, dilim_kod: str, dilim_ad: str, ham: dict,
              gosterim_bar: int) -> None:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    n = min(gosterim_bar, len(ham["kapanis"]))
    z = ham["zaman"][-n:]
    a, y, d, k = (ham["acilis"][-n:], ham["yuksek"][-n:],
                  ham["dusuk"][-n:], ham["kapanis"][-n:])
    tam_k = ham["kapanis"]
    sma50 = _sma_seri(tam_k, 50)[-n:]
    sma200 = _sma_seri(tam_k, 200)[-n:]
    rsi = _rsi_seri(tam_k)[-n:]
    mac = _macd_seriler(tam_k)
    saatlik = dilim_kod != "gun"

    fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                        row_heights=[0.62, 0.19, 0.19], vertical_spacing=0.03,
                        subplot_titles=("", "RSI(14)", "MACD(12,26,9)"))
    fig.add_trace(go.Candlestick(
        x=z, open=a, high=y, low=d, close=k, name=e.ad,
        increasing_line_color="#2d6a4f", decreasing_line_color="#9d2235",
        showlegend=False), row=1, col=1)
    for ad_, seri, renk in (("SMA50", sma50, "#b8860b"),
                            ("SMA200", sma200, "#365f91")):
        fig.add_trace(go.Scatter(x=z, y=seri, name=ad_,
                                 line=dict(width=1.4, color=renk)), row=1, col=1)
    kn = ham["kanal"]
    if kn:
        kb = min(kn["pencere"], n)
        xs = z[-kb:]
        taban = kn["orta"] - kn["egim_bar"] * (kn["pencere"] - 1)
        for etiket, kes in (("kanal üst", 2), ("kanal orta", 0), ("kanal alt", -2)):
            bas = kn["pencere"] - kb
            ys = [taban + kn["egim_bar"] * (bas + i) + kes * kn["sigma"]
                  for i in range(kb)]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, name=etiket,
                line=dict(width=1, dash="dot" if kes else "dash",
                          color="#8a8a8a"),
                showlegend=(kes == 2)), row=1, col=1)
    for yon, renk in (("direnc", "#9d2235"), ("destek", "#2d6a4f")):
        for b in ham["seviyeler"][yon]:
            fig.add_hline(y=b["seviye"], line_width=1, line_dash="dash",
                          line_color=renk, opacity=0.55, row=1, col=1,
                          annotation_text=f"{b['seviye']} ({b['dokunus']}x)",
                          annotation_font_size=10)
    fig.add_trace(go.Scatter(x=z, y=rsi, name="RSI",
                             line=dict(width=1.2, color="#5f4b8b"),
                             showlegend=False), row=2, col=1)
    for esik in (30, 70):
        fig.add_hline(y=esik, line_width=0.8, line_dash="dot",
                      line_color="#999", row=2, col=1)
    fig.add_trace(go.Bar(x=z, y=mac["hist"][-n:], name="hist",
                         marker_color="#b0b0b0", showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=z, y=mac["macd"][-n:], name="MACD",
                             line=dict(width=1.1, color="#365f91"),
                             showlegend=False), row=3, col=1)
    fig.add_trace(go.Scatter(x=z, y=mac["sinyal"][-n:], name="sinyal",
                             line=dict(width=1.1, color="#b8860b"),
                             showlegend=False), row=3, col=1)
    aralik = f"{z[0]} → {z[-1]}" + (" (UTC)" if saatlik else "")
    fig.update_layout(title=f"{e.ad} — {dilim_ad} ({aralik})",
                      xaxis_rangeslider_visible=False, height=760,
                      legend=dict(orientation="h"))
    if saatlik:
        # Kategori ekseni: seans boşlukları (gece, hafta sonu) grafikte delik
        # açmasın. Etiket sayısı sınırlı tutulur.
        fig.update_xaxes(type="category", nticks=8)
    else:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    GRAFIK.mkdir(parents=True, exist_ok=True)
    ek = "gunluk" if dilim_kod == "gun" else dilim_kod
    fig.write_html(GRAFIK / f"{e.slug}-{ek}.html",
                   include_plotlyjs="cdn", full_html=True)


def _rsi_seri(kapanis, n: int = 14):
    out = [None] * len(kapanis)
    for i in range(n, len(kapanis)):
        out[i] = rsi_wilder(kapanis[:i + 1], n)
    return out


def _macd_seriler(kapanis):
    if len(kapanis) < 35:
        b = [None] * len(kapanis)
        return {"macd": b, "sinyal": b, "hist": b}
    hat = [a - b for a, b in zip(_ema_seri(kapanis, 12), _ema_seri(kapanis, 26))]
    sinyal = [None] * 25 + _ema_seri(hat[25:], 9)
    hist = [None if s is None else m - s for m, s in zip(hat, sinyal)]
    return {"macd": hat, "sinyal": sinyal, "hist": hist}


# ── ana akış ─────────────────────────────────────────────────────────────────

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--yeniden-olc", action="store_true",
                   help="yazılmış bülteni bilerek yeniden ölç (yorumlar sıfırlanır; "
                        "metnin yeni ölçüye göre yeniden yazılması ŞART)")
    arg = p.parse_args()

    bugun = datetime.now(timezone.utc).date()
    hedef = VERI / f"{bugun.isoformat()}.json"
    if hedef.exists() and not arg.yeniden_olc:
        eski = json.loads(hedef.read_text(encoding="utf-8"))
        if eski.get("yazili"):
            print(f"{hedef.name} yazılmış — ölçüm onu ezmez "
                  "(bilerek: --yeniden-olc), çıkılıyor")
            return 0

    seriler = cek()
    kayit = {
        "tarih": bugun.isoformat(),
        "tr_tarih": f"{bugun.day} {AYLAR[bugun.month]} {bugun.year}",
        "olcum_zamani": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "yazili": False,
        "giris": None,
        "enstrumanlar": [],
    }
    for e in ENSTRUMANLAR:
        js, hamlar = olc_enstruman(e, seriler[e.kod])
        for kod, ad, bar, _ in DILIMLER:
            if kod in hamlar:
                ciz_dilim(e, kod, ad, hamlar[kod], bar)
        kayit["enstrumanlar"].append(js)
        dolu = [k for k in ("s1", "s4", "gun") if "eksik" not in js["dilimler"][k]]
        print(f"  {e.ad:26s} son={js['son']}  bar={js['bar_tarihi']}  "
              f"dilimler={','.join(dolu)}")
    kayit["veri_ucu"] = min(m["bar_tarihi"] for m in kayit["enstrumanlar"])
    VERI.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    print(f"yazıldı: {hedef}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
