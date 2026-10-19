#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABD'NİN ORTA DOĞU UYARISI (19.10.2026) — yazının bütün sayıları buradan.

Girdiler (hepsi depoda, donmuş):
  veri/olaylar.json           emsal tablosu: tarih, tür, kapsam, sonuç; her satır kaynak kimliği taşır (dogrula.py
                              kaynağın kendi metninde arar)
  veri/ham/polymarket/        tahmin piyasası fiyat geçmişi (bulut arşivi)
  veri/ham/cnbc/              son dönem kapanışları (bulut arşivi, Mayıs 2025 →)
  ../BrentSenaryo/veri/       uzun tarihçe: CNBC günlük kapanışlar (1985 →), jeopolitik risk endeksi (GPR, 1985 →)

Çıktı: veri/olcum.json. Ölçüler:
  1. taban oranı: geniş (çok ülkeli) uyarıların ardından 7 / 30 / 90 gün içinde ABD saldırısı ve savaşın yeni ülkelere
     yayılması; türüne göre (eylem öncesi tahliye · tehdit uyarısı · olay sonrası), Jeffreys aralığıyla
  2. piyasa: her emsal gününden 5 / 20 / 60 iş günü sonra Brent, altın, S&P 500, VIX, ABD 10 yıllık, USD/TRY
  3. GPR: bugünkü 30 günlük düzeyin tarihteki yeri ve aynı düzeyin aşıldığı geçmiş dönemler
  4. tahmin piyasaları: şimdiki fiyatlar ve emsal günlerdeki fiyatlar, piyasanın kendi çözümüyle
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
HAM = VERI / "ham"
BRENT = BURASI.parent / "BrentSenaryo" / "veri"
CIKTI = VERI / "olcum.json"
#: Yazının adresi (tek tanım: figürler ve kapı buradan okur).
SLUG = "abd-orta-dogu-uyarisi-2026-10-19"

#: Piyasa tepkisinin ufukları (iş günü) ve araçları (CNBC uzun tarihçe sütun adı → okur adı, birim).
UFUK = (5, 20, 60)
ARAC = {"brent": ("Brent", "yuzde"), "altin": ("Altın", "yuzde"), "spx": ("S&P 500", "yuzde"),
        "vix": ("VIX", "puan"), "us10y": ("ABD 10 yıllık", "bp"), "try": ("USD/TRY", "yuzde")}
#: Taban oranının ufukları (takvim günü).
GUN = (7, 30, 90)


def _oz(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def jeffreys(k: int, n: int, a: float = 0.05) -> tuple[float, float]:
    """Binom oranı için Jeffreys aralığı (Beta(k+½, n−k+½) yüzdelikleri)."""
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(a / 2, k + 0.5, n - k + 0.5))
    hi = 1.0 if k == n else float(beta.ppf(1 - a / 2, k + 0.5, n - k + 0.5))
    return lo, hi


# ─────────────────────────────────────────────────────────────── uzun tarihçe
def uzun_seri() -> pd.DataFrame:
    d = pd.read_csv(BRENT / "cnbc_gunluk.csv.gz", parse_dates=["tarih"]).set_index("tarih").sort_index()
    return d[[c for c in ARAC if c in d]]


def tepki(seri: pd.DataFrame, gun: str) -> dict:
    """Emsal gününün kapanışından (o gün ya da önceki ilk işlem günü) h iş günü sonrasına değişim."""
    t = pd.Timestamp(gun)
    out = {}
    for c, (_, birim) in ARAC.items():
        s = seri[c].dropna()
        i = s.index.searchsorted(t, side="right") - 1
        if i < 0:
            continue
        r = {"baz_tarih": s.index[i].date().isoformat(), "baz": float(s.iloc[i])}
        for h in UFUK:
            if i + h >= len(s):
                continue
            v = float(s.iloc[i + h])
            r[f"d{h}"] = (v / r["baz"] - 1) if birim == "yuzde" else ((v - r["baz"]) * (100 if birim == "bp" else 1))
            r[f"t{h}"] = s.index[i + h].date().isoformat()
        out[c] = r
    return out


# ─────────────────────────────────────────────────────────────── GPR
def gpr() -> dict:
    """Jeopolitik risk endeksi (Caldara–Iacoviello, günlük). Kaynak bulutun bugün indirdiği dosyadır; endeks geriye
    dönük yeniden hesaplanabildiği için eski bir indirmeyle EKLENMEZ — eski indirme yalnız revizyonun büyüklüğünü ölçer."""
    p = next(iter(sorted((HAM / "gpr").glob("*recent*.gz"))))
    ek = pd.read_excel(gzip.open(p))
    ek["tarih"] = pd.to_datetime(ek["date"])
    g = ek.set_index("tarih")[["GPRD", "GPRD_ACT", "GPRD_THREAT"]].dropna().sort_index()
    eski = pd.read_csv(BRENT / "gpr_gunluk.csv.gz", parse_dates=["tarih"]).set_index("tarih").sort_index()
    ortak = g.index.intersection(eski.index)
    fark = (g.loc[ortak, "GPRD"] - eski.loc[ortak, "GPRD"]).abs()
    fark = {"gun": int(len(ortak)), "azami": float(fark.max()), "ayni_pay": float((fark < 1e-6).mean())}
    r = g.rolling(30, min_periods=30).mean()
    son = r.dropna().iloc[-1]
    gun = r.dropna().index[-1]
    tum = r["GPRD"].dropna()
    ay = r.resample("ME").max()
    return {"son_gun": gun.date().isoformat(), "revizyon": fark, "dosya_ozu": _oz(p),
            "gpr30": float(son["GPRD"]), "tehdit30": float(son["GPRD_THREAT"]), "eylem30": float(son["GPRD_ACT"]),
            "yuzdelik": float((tum < son["GPRD"]).mean()),
            "ortalama_tum": float(g["GPRD"].mean()),
            "ay": {d.strftime("%Y-%m"): {"gpr30": float(v["GPRD"]), "tehdit30": float(v["GPRD_THREAT"]),
                                        "eylem30": float(v["GPRD_ACT"])} for d, v in ay.dropna().iterrows()},
            "seri": [[d.date().isoformat(), round(float(v), 1)] for d, v in r["GPRD"].dropna().resample("W").last().items()]}


def main() -> int:
    seri = uzun_seri()
    olcum = {"kunye": {"cnbc_gunluk": _oz(BRENT / "cnbc_gunluk.csv.gz"), "gpr_gunluk": _oz(BRENT / "gpr_gunluk.csv.gz"),
                       "olcum_py": _oz(Path(__file__))},
             "gpr": gpr()}
    olaylar_yol = VERI / "olaylar.json"
    if olaylar_yol.exists():
        olcum["kunye"]["olaylar"] = _oz(olaylar_yol)
        olaylar = json.loads(olaylar_yol.read_text(encoding="utf-8"))
        olcum["tepki"] = {o["id"]: tepki(seri, o["tarih"]) for o in olaylar["olay"]}
    CIKTI.write_text(json.dumps(olcum, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    print(f"✓ {CIKTI.relative_to(BURASI)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
