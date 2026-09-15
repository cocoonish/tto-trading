#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörü v2 — 5 ve 15 dakikalık FX'te BACKTEST (keşif; hüküm değil).

Üçüncü koşu (15.09.2026). İlk iki koşu ölçtü ve kayda geçti
(scratchpad/bulut_5dk_ozet.md): dersin mutlak rejim eşikleri enstrümana göre
%3–%100 arasında açık kalıyor; beş ölçünün de, göreli hükmün de ileriye dönük
öngörü gücü yok; ve maliyetsiz "kenar" tamamen medyanı 2,6 pip olan en küçük
riskli işlemlerden geliyor — yarım pip gidiş-dönüş maliyet on yapılandırmanın
onunu da eksiye çeviriyor.

Bu koşu YENİ kural katmanını ölçer: dersin tick'li emir paketi, altı tick
kuralı, sıkılaştırma/başabaş yönetimi, beş kurulum ailesi (dönüş barı ·
ikinci giriş H2/L2 · kırılım modu · başarısız dönüş · bant kenarı) ve göreli
rejim süzgeci — brooks_backtest.YAPILANDIRMA'nın tamamı, R∈{1,2}, iki yönetim.
Her satır için pip maliyetiyle net R (0 · 0,5 · 1 · 2 pip gidiş-dönüş) ve
risk dilimleri basılır. Veri Yahoo'dan, depoya yazılmaz; yalnız özet.

Bütçe: keşif işi 20 dk; 14 dk dolunca kalan satırlar ADIYLA atlanır."""
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
from brooks_referans import Seri                                 # noqa: E402

BASLANGIC = time.time()
BUTCE_SN = 14 * 60
ISLER = [("EURUSD=X", "5m", 59, "eurusd-5dk"), ("EURUSD=X", "15m", 59, "eurusd-15dk"),
         ("USDCHF=X", "5m", 59, "usdchf-5dk"), ("USDJPY=X", "15m", 59, "usdjpy-15dk"),
         ("GBPUSD=X", "5m", 59, "gbpusd-5dk")]
RASTGELE = 60
PIP = {"eurusd": 0.0001, "gbpusd": 0.0001, "usdchf": 0.0001, "usdjpy": 0.01}
MALIYET_PIP = (0.0, 0.5, 1.0, 2.0)


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
    d = d.iloc[:-1]                                   # kapanmamış son bar düşer
    z = [pd.Timestamp(t).strftime("%Y-%m-%dT%H:%M") for t in d.index]
    return Seri([float(x) for x in d["Open"]], [float(x) for x in d["High"]],
                [float(x) for x in d["Low"]], [float(x) for x in d["Close"]], z)


def maliyet_ve_risk(y: dict, rng: random.Random) -> None:
    islemler = y["islemler"]
    if not islemler:
        return
    for t in islemler:
        pip = PIP[t["seri"].split("-")[0]]
        t["_risk_pip"] = t["risk_tick"] * TICK[t["seri"]] / pip
    riskler = sorted(t["_risk_pip"] for t in islemler)
    q1, q2, q3 = riskler[len(riskler) // 4], riskler[len(riskler) // 2], riskler[3 * len(riskler) // 4]
    satir = []
    for m in MALIYET_PIP:
        net = [t["R"] - m / t["_risk_pip"] for t in islemler if t["_risk_pip"] > 0]
        ca = BT.bootstrap_ca(net, rng, 300)
        satir.append(f"{m:.1f}p {sum(net) / len(net):+.3f} [{ca[0]:+.2f},{ca[1]:+.2f}]" if ca else f"{m:.1f}p —")
    print(f"      risk pip p25/p50/p75 {q1:.1f}/{q2:.1f}/{q3:.1f} · net R: " + " · ".join(satir))
    dilim = []
    for ad, alt, ust in (("küçük", 0, q1), ("orta", q1, q3), ("büyük", q3, 1e9)):
        sec = [t for t in islemler if alt <= t["_risk_pip"] < ust and t["_risk_pip"] > 0]
        if sec:
            brut = sum(t["R"] for t in sec) / len(sec)
            net = sum(t["R"] - 1.0 / t["_risk_pip"] for t in sec) / len(sec)
            dilim.append(f"{ad} n={len(sec)} brüt {brut:+.2f} / 1p {net:+.2f}")
    kd = " · ".join(f"{k} {v}" for k, v in y["kurulum_dagilimi"].items() if v)
    print(f"      risk dilimi · " + " · ".join(dilim) + f" · kurulum: {kd}")


TICK: dict[str, float] = {}


def main() -> int:
    print(f"Brooks v2 · 5/15 dk backtest · yapılandırma {len(BT.YAPILANDIRMA)} × R{BT.HEDEFLER} × 2 yönetim · rastgele {RASTGELE}")
    seriler: list[BT.SeriOlcum] = []
    for sembol, aralik, gun, ad in ISLER:
        d = cek(sembol, aralik, gun)
        if d is None:
            print(f"  {ad}: ÇEKİLEMEDİ")
            continue
        s = seriye(d)
        g = O.govde_kunyesi(s)
        tick = R.tick_tahmini(s)
        TICK[ad] = tick
        print(f"\n=== {ad} · {len(s)} bar · {s.zaman[0]} → {s.zaman[-1]} · tick {tick:g} · gövde {g}")
        if not g["gecti"]:
            print(f"  {ad}: GÖVDE KAPISINDAN GEÇMEDİ — dışarıda")
            continue
        t0 = time.time()
        so = BT.SeriOlcum(ad, s, tick=tick, maliyet=0.0)
        n = len(s) - BT.BAS
        say = {k: sum(1 for i in range(BT.BAS, len(s)) if so.paket[k][i]) for k in so.paket}
        print("  paket sıklığı /100 bar: " + " · ".join(f"{k} {100 * v / n:.1f}" for k, v in say.items()))
        gr = [so.rejim_goreli[i] for i in range(BT.BAS, len(s)) if so.rejim_goreli[i]]
        print(f"  göreli rejim payı: BANT %{100 * gr.count('BANT') / max(1, len(gr)):.1f} · ara %{100 * gr.count('ara') / max(1, len(gr)):.1f} · trend %{100 * gr.count('trend') / max(1, len(gr)):.1f} (n={len(gr)})")
        seriler.append(so)
        print(f"  ({ad} ölçüm {time.time() - t0:.0f} s · toplam {gecen():.0f} s)")
        time.sleep(2)
    if not seriler:
        print("hiç seri ölçülemedi")
        return 1

    print(f"\n=== BACKTEST · {len(seriler)} seri · ortak başlangıç {BT.BAS}")
    print("  yapılandırma                        R yön.    N  kazanma  ort_R   CA95           KF   rast%  ilk/ikinci")
    rng = random.Random(BT.TOHUM)
    for ad, ayar in BT.YAPILANDIRMA:
        for hr in BT.HEDEFLER:
            for yon in (BT.YONETIM_SABIT, BT.YONETIM_DERS):
                yad = "ders" if yon["basabas"] else "sabit"
                if gecen() > BUTCE_SN:
                    print(f"  ATLANDI (bütçe {BUTCE_SN} s doldu): {ad} · R={hr} · {yad}")
                    continue
                t0 = time.time()
                y = BT.yapilandirma_olc(ad, ayar, hr, seriler, rng, tekrar=RASTGELE, yonetim=yon)
                ca = f"[{y['ca_alt']:+.2f},{y['ca_ust']:+.2f}]" if y["ca_alt"] is not None else "—"
                kf = f"{y['kar_faktoru']:.2f}" if y["kar_faktoru"] is not None else "—"
                yz = f"{y['rastgele']['yuzdelik']:.0f}" if y["rastgele"]["yuzdelik"] is not None else "—"
                ilk, iki = y["ilk_yari"]["ort_R"], y["ikinci_yari"]["ort_R"]
                print(f"  {ad:36s} {hr} {yad:5s} {y['n']:5d}  {(y['kazanma'] or 0):.3f}  {(y['ort_R'] or 0):+.3f}  {ca:14s} {kf:5s} {yz:>4s}  "
                      f"{(ilk if ilk is not None else 0):+.2f}/{(iki if iki is not None else 0):+.2f}  "
                      f"(emir {y['emir']}, dolum {y['dolum_orani']}, çift {y['cift_vurus']}, belirsiz {y['belirsiz']}+{y['cift_belirsiz']}, {time.time() - t0:.0f} s)")
                seri_satir = " · ".join(f"{k} n={v['n']} {(v['ort_R'] if v['ort_R'] is not None else 0):+.2f}" for k, v in y["seri"].items())
                print(f"      seri: {seri_satir}")
                maliyet_ve_risk(y, rng)
    print(f"\nbitti · {gecen():.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
