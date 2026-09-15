#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörü — 5 ve 15 dakikalık FX'te ÖLÇÜM (keşif; hüküm değil).

Neden: dersin eşikleri 5 dakikalık barda kalibre, depodaki ölçüm 1 saat ve
üstünde (13 seri: üç bant işaretinin üçü sabit, backtest'te kenar yok).
Kullanıcı 5 dakikalık EUR/USD'de "örtüşme hep eşiğin üstünde" dedi. Soru:
dersin KENDİ ölçeğinde de böyle mi — ancak o ölçekte veriyle cevaplanır.

Veri Yahoo'dan (bu oturumlardan kapalı, koşucudan açık), depoya YAZILMAZ.
Kurallar brooks_referans'tan, emir mekaniği brooks_backtest'ten olduğu gibi
çağrılır; burada hiçbir kural yeniden yazılmaz. Yalnız ÖZET basılır:

  (1) beş rejim ölçüsünün seri başına p10/p50/p90'ı ve dersin eşiğiyle
      "bant tarafında" pencere payı; rejim hükmünün payları; UTC saat
      bloğuna göre BANT payı (seans etkisi)
  (2) sinyal barı sıklığı (K≥1/2/3, 100 barda) ve dolum oranı
  (3) backtest: ablasyon alt kümesi × R∈{1,2} + rastgele taban
  (4) öngörü: ölçü(i) ↔ sonraki 35 barın net/aralık oranı — örtüşmeyen
      pencereler, Spearman, permütasyon p (scipy yok)

Bütçe: keşif işi 20 dk. Her aşama ilerleme basar; 15 dk dolunca kalan
yapılandırmalar ADIYLA atlanır (sessiz kısaltma yok)."""
from __future__ import annotations

import random
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(KOK / "site" / "tools"))
sys.path.insert(0, str(KOK / "site" / "public" / "indikatorler"))
sys.path.insert(0, str(KOK))

import brooks_backtest as BT                                     # noqa: E402
import brooks_ornek as O                                         # noqa: E402
import brooks_referans as R                                      # noqa: E402
from brooks_referans import FiyatPaneli, RejimPanosu, Seri       # noqa: E402

BASLANGIC = time.time()
BUTCE_SN = 15 * 60
ISLER = [("EURUSD=X", "5m", 59, "eurusd-5dk"), ("EURUSD=X", "15m", 59, "eurusd-15dk"),
         ("USDCHF=X", "5m", 59, "usdchf-5dk"), ("USDJPY=X", "15m", 59, "usdjpy-15dk"),
         ("GBPUSD=X", "5m", 59, "gbpusd-5dk")]
YAPI = [y for y in BT.YAPILANDIRMA if y[0] in (
    "tam sistem · K≥3", "tam sistem · K≥2", "−rejim · K≥3", "süzgeçsiz · K≥1", "yalnız always-in · K≥1")]
RASTGELE = 200
UFUK_ONGORU = 35


def gecen() -> float:
    return time.time() - BASLANGIC


def cek(sembol, aralik, gun):
    import yfinance as yf
    for deneme in range(4):
        try:
            d = yf.download(sembol, interval=aralik, period=f"{gun}d",
                            progress=False, auto_adjust=False, threads=False)
            if d is not None and len(d):
                return d
            print(f"  {sembol} {aralik}: boş çerçeve (deneme {deneme + 1})")
        except Exception as e:  # noqa: BLE001
            print(f"  {sembol} {aralik}: {type(e).__name__}: {str(e)[:100]} (deneme {deneme + 1})")
        time.sleep(15 * (deneme + 1))
    return None


def seriye(d) -> Seri:
    import pandas as pd
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d[["Open", "High", "Low", "Close"]].dropna()
    # Kapanmamış son bar: koşu anındaki bar henüz kapanmadı — düşürülür.
    d = d.iloc[:-1]
    z = [pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M") for t in d.index]
    return Seri([float(x) for x in d["Open"]], [float(x) for x in d["High"]],
                [float(x) for x in d["Low"]], [float(x) for x in d["Close"]], z)


def yuzdelik(x: list[float], p: float) -> float:
    if not x:
        return float("nan")
    s = sorted(x)
    return s[min(len(s) - 1, int(p / 100 * len(s)))]


def _rank(x: list[float]) -> list[float]:
    sirali = sorted(range(len(x)), key=lambda i: x[i])
    r = [0.0] * len(x)
    i = 0
    while i < len(sirali):
        j = i
        while j + 1 < len(sirali) and x[sirali[j + 1]] == x[sirali[i]]:
            j += 1
        for k in range(i, j + 1):
            r[sirali[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 4:
        return float("nan")
    rx, ry = _rank(x), _rank(y)
    mx, my = sum(rx) / n, sum(ry) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    return sxy / (sxx * syy) ** 0.5 if sxx > 0 and syy > 0 else float("nan")


def perm_p(x: list[float], y: list[float], rho: float, rng: random.Random, tekrar: int = 500) -> float:
    if rho != rho:
        return float("nan")
    y2 = list(y)
    sayac = 0
    for _ in range(tekrar):
        rng.shuffle(y2)
        if abs(spearman(x, y2)) >= abs(rho):
            sayac += 1
    return (sayac + 1) / (tekrar + 1)


def dagilim(ad: str, s: Seri, rp: RejimPanosu) -> dict:
    """Beş ölçünün dağılımı + rejim payları + UTC blok BANT payı + öngörü."""
    olculer: dict[str, list[float]] = {k: [] for k in ("ortusme_oran", "doji_oran", "kesisme", "net_aralik", "azami_dizi")}
    isaret_acik = {k: 0 for k in ("ortusme", "doji", "kesisme", "net", "dizi")}
    rejim_pay = {"BANT": 0, "ara": 0, "trend": 0}
    blok = {b: [0, 0] for b in ("00-06", "06-12", "12-18", "18-24")}
    kayit: list[tuple[int, dict]] = []
    n = 0
    for i in range(BT.BAS, len(s)):
        o = rp.olcu(i)
        if o is None:
            continue
        n += 1
        for k in olculer:
            olculer[k].append(float(o[k]))
        for k in isaret_acik:
            isaret_acik[k] += int(o["isaret"][k])
        rejim_pay[o["rejim"]] += 1
        saat = int(s.zaman[i][11:13]) if s.zaman else 0
        b = ("00-06", "06-12", "12-18", "18-24")[min(3, saat // 6)]
        blok[b][0] += 1
        blok[b][1] += int(o["rejim"] == "BANT")
        kayit.append((i, o))
    w = int(R.SABIT_RP["pencere"])
    print(f"\n[{ad}] pencere {n} · rejim payı: " + " · ".join(f"{k} %{100 * v / n:.1f}" for k, v in rejim_pay.items()))
    print("  ölçü            p10     p50     p90   eşik   açık payı")
    esik = {"ortusme_oran": ("ortusme", "≥", R.SABIT_RP["ortusmePay"]), "doji_oran": ("doji", "≥", R.SABIT_RP["dojiPay"]),
            "kesisme": ("kesisme", "≥", R.SABIT_RP["kesismeEsik"]), "net_aralik": ("net", "≤", R.SABIT_RP["netEsik"]),
            "azami_dizi": ("dizi", "<", R.SABIT_RP["diziEsik"])}
    for k, x in olculer.items():
        ik, op, e = esik[k]
        print(f"  {k:14s} {yuzdelik(x, 10):7.3f} {yuzdelik(x, 50):7.3f} {yuzdelik(x, 90):7.3f}  {op}{e:<5} %{100 * isaret_acik[ik] / n:.1f}")
    print("  UTC blok BANT payı: " + " · ".join(f"{b} %{100 * v[1] / v[0]:.0f} (n={v[0]})" if v[0] else f"{b} —" for b, v in blok.items()))

    # Öngörü: ölçü(i) ↔ sonraki UFUK barın net/aralık'ı, örtüşmeyen pencereler (adım 70)
    rng = random.Random(BT.TOHUM)
    xs: dict[str, list[float]] = {k: [] for k in olculer}
    xs["n"] = []
    ys: list[float] = []
    for i, o in kayit[::w]:
        j = i + UFUK_ONGORU
        if j >= len(s):
            break
        aralik = max(s.h[i + 1:j + 1]) - min(s.l[i + 1:j + 1])
        ys.append(abs(s.c[j] - s.c[i]) / aralik if aralik > 0 else 0.0)
        for k in olculer:
            xs[k].append(float(o[k]))
        xs["n"].append(float(o["n"]))
    print(f"  öngörü (örtüşmeyen n={len(ys)}, hedef sonraki {UFUK_ONGORU} barın net/aralık'ı):")
    for k, x in xs.items():
        rho = spearman(x, ys)
        p = perm_p(x, ys, rho, rng)
        print(f"    {k:14s} ρ {rho:+.3f}  p {p:.3f}")
    return {"n": n, "rejim": rejim_pay}


def sinyal_sikligi(ad: str, so: BT.SeriOlcum) -> None:
    n = len(so.s) - BT.BAS
    for K in (1, 2, 3):
        sayi = sum(1 for i in range(BT.BAS, len(so.s)) for yon in (1, -1)
                   if so.donus[yon][i] and so.kalite[yon][i] >= K)
        print(f"  [{ad}] dönüş barı K≥{K}: {sayi} ({100 * sayi / n:.1f}/100 bar)")
    ai_donus = sum(1 for i in range(BT.BAS + 1, len(so.s)) if so.ai[i] != so.ai[i - 1] and so.ai[i] != 0)
    bw = sum(so.bw[BT.BAS:])
    print(f"  [{ad}] always-in dönüşü {ai_donus} ({100 * ai_donus / n:.2f}/100) · barbwire %{100 * bw / n:.1f}")


def main() -> int:
    print(f"Brooks 5/15 dk keşfi · yapılandırma {len(YAPI)} · rastgele {RASTGELE}")
    seriler: list[BT.SeriOlcum] = []
    for sembol, aralik, gun, ad in ISLER:
        d = cek(sembol, aralik, gun)
        if d is None:
            print(f"  {ad}: ÇEKİLEMEDİ")
            continue
        s = seriye(d)
        g = O.govde_kunyesi(s)
        print(f"\n=== {ad} · {len(s)} bar · {s.zaman[0]} → {s.zaman[-1]} · gövde {g}")
        if not g["gecti"]:
            print(f"  {ad}: GÖVDE KAPISINDAN GEÇMEDİ — dışarıda, sebebi yukarıda")
            continue
        t0 = time.time()
        rp = RejimPanosu(s)
        dagilim(ad, s, rp)
        so = BT.SeriOlcum(ad, s)
        sinyal_sikligi(ad, so)
        seriler.append(so)
        print(f"  ({ad} ölçüm {time.time() - t0:.0f} s · toplam {gecen():.0f} s)")
        time.sleep(2)
    if not seriler:
        print("hiç seri ölçülemedi")
        return 1

    print(f"\n=== BACKTEST · {len(seriler)} seri · ortak başlangıç {BT.BAS}")
    print("  yapılandırma                 R    N   kazanma   ort_R   CA95            KF    rastgele‰  ilk/ikinci")
    rng = random.Random(BT.TOHUM)
    for ad, ayar in YAPI:
        for hr in BT.HEDEFLER:
            if gecen() > BUTCE_SN:
                print(f"  ATLANDI (bütçe {BUTCE_SN} s doldu): {ad} · R={hr}")
                continue
            t0 = time.time()
            y = BT.yapilandirma_olc(ad, ayar, hr, seriler, rng, tekrar=RASTGELE)
            ca = f"[{y['ca_alt']:+.2f}, {y['ca_ust']:+.2f}]" if y["ca_alt"] is not None else "—"
            kf = f"{y['kar_faktoru']:.2f}" if y["kar_faktoru"] is not None else "—"
            yz = f"{y['rastgele']['yuzdelik']:.0f}" if y["rastgele"]["yuzdelik"] is not None else "—"
            ilk = y["ilk_yari"]["ort_R"]
            iki = y["ikinci_yari"]["ort_R"]
            print(f"  {ad:28s} {hr}  {y['n']:4d}   {(y['kazanma'] or 0):.3f}   {(y['ort_R'] or 0):+.3f}  {ca:16s} {kf:5s}  {yz:>6s}   "
                  f"{(ilk if ilk is not None else 0):+.2f}/{(iki if iki is not None else 0):+.2f}  "
                  f"(emir {y['emir']}, dolum {y['dolum_orani']}, çift {y['cift_vurus']}, {time.time() - t0:.0f} s)")
            seri_satir = " · ".join(f"{k} n={v['n']} {(v['ort_R'] if v['ort_R'] is not None else 0):+.2f}" for k, v in y["seri"].items())
            print(f"      seri: {seri_satir}")
    print(f"\nbitti · {gecen():.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
