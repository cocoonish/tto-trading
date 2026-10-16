#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber takvimi: resmi kaynakların dondurulmuş ham sayfalarından olay listesi.

Şema (`veri/takvim/olaylar.csv`, ve kullanıcının ek dosyası `veri/takvim/ek.csv`):
  olay        NFP · CPI · FOMC_karar · FOMC_basin · ECB_karar · ECB_basin · BoE_karar · (ek olaylar)
  tarih       yerel tarih (YYYY-AA-GG)
  yerel_saat  yerel duvar saati (SS:DD) — saat TARİH BAZINDA, kaynağın kendi metninden
  bolge       IANA saat dilimi (America/New_York, Europe/Berlin, Europe/London)
  kaynak      saati ve tarihi veren resmi belgenin adresi
  not         (isteğe bağlı) olağanüstü toplantı, ertelenmiş yayım vb.
  ciftler     (yalnız ek dosyada, isteğe bağlı) boşlukla ayrık parite listesi; boşsa
              olay tipinin öntanımlı eşlemesi (onkayit.toml [haber])

UTC karşılığı her satır için `zoneinfo` ile o günün kuralından hesaplanır;
dosyada UTC saklanmaz (iki kaynak bir gün ayrışırdı).
"""
from __future__ import annotations

import tomllib
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
DIZIN = BURASI / "veri" / "takvim"
ANA = DIZIN / "olaylar.csv"
EK = DIZIN / "ek.csv"
ONKAYIT = tomllib.loads((BURASI / "onkayit.toml").read_text(encoding="utf-8"))
SUTUN = ["olay", "tarih", "yerel_saat", "bolge", "kaynak", "not"]


def olay_ciftleri(olay: str) -> list[str]:
    h = ONKAYIT["haber"]
    if olay.startswith("ECB"):
        return list(h["ecb"])
    if olay.startswith("BoE"):
        return list(h["boe"])
    return list(h["abd"])


def _utc_sn(df: pd.DataFrame) -> np.ndarray:
    out = np.empty(len(df), dtype=np.int64)
    for i, (t, s, b) in enumerate(zip(df["tarih"], df["yerel_saat"], df["bolge"])):
        yerel = pd.Timestamp(f"{t} {s}").tz_localize(ZoneInfo(b), ambiguous="raise", nonexistent="raise")
        out[i] = int(yerel.tz_convert("UTC").timestamp())
    return out


def tumu() -> pd.DataFrame:
    parcalar = []
    for yol, ad in ((ANA, "resmi"), (EK, "ek")):
        if yol.exists():
            df = pd.read_csv(yol, dtype=str, keep_default_na=False)
            eksik = [c for c in SUTUN[:5] if c not in df.columns]
            if eksik:
                raise SystemExit(f"{yol.name}: eksik sütun {eksik}")
            df["kume"] = ad
            parcalar.append(df)
    if not parcalar:
        return pd.DataFrame(columns=SUTUN + ["kume", "utc_sn", "ciftler"])
    df = pd.concat(parcalar, ignore_index=True)
    if "ciftler" not in df.columns:
        df["ciftler"] = ""
    df["ciftler"] = [c if c else " ".join(olay_ciftleri(o)) for o, c in zip(df["olay"], df["ciftler"].fillna(""))]
    df["utc_sn"] = _utc_sn(df)
    # Aynı olay aynı anda iki kez (resmi + ek) yazıldıysa resmi kalır.
    df = df.sort_values(["utc_sn", "olay", "kume"]).drop_duplicates(["olay", "utc_sn"], keep="first")
    return df.reset_index(drop=True)


def olaylar_oku(cift: str) -> pd.DataFrame:
    df = tumu()
    if len(df) == 0:
        return df
    return df[df["ciftler"].str.split().apply(lambda x: cift in x)].reset_index(drop=True)
