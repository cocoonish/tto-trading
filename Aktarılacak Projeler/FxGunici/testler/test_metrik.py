# -*- coding: utf-8 -*-
"""Sıfıra yakın bootstrap ucunun bilgi alanı: yalnız uç sıfıra yakınken kurulur; tohum duyarlılığı önceden kayıtlı
yordamın kendisiyle ölçülür."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import metrik as mk  # noqa: E402


def test_sinir_bilgisi_uzak_ucta_yok():
    rng = np.random.default_rng(2)
    x = rng.normal(0.5, 1.0, 400)               # ortalama ~10 SE: alt uç sıfırdan çok uzak
    alt, _ = mk.bootstrap_ort(x)
    assert mk.sinir_bilgisi(x, alt, "alt") is None


def test_sinir_bilgisi_sifira_yakin_ucta_kurulur():
    rng = np.random.default_rng(4)
    x = rng.normal(0.0, 1.0, 300)
    x = x - x.mean() + 1.96 * x.std(ddof=1) / np.sqrt(len(x))   # alt uç ≈ 0
    alt, _ = mk.bootstrap_ort(x)
    s = mk.sinir_bilgisi(x, alt, "alt")
    assert s is not None and abs(s["uzaklik_se"]) < mk.SINIR_SE
    assert 0.0 <= s["pozitif_pay"] <= 1.0 and s["kesin_mc_se"] > 0
    # tohum duyarlılığı önceden kayıtlı yordamla: aynı tohumla aynı uç
    assert mk.bootstrap_ort(x, 2000, mk.SINIR_TOHUM_TABAN)[0] == mk.bootstrap_ort(x, 2000, mk.SINIR_TOHUM_TABAN)[0]


def test_ortalama_se_kume():
    x = np.array([1.0, 1.0, -1.0, -1.0, 2.0, 0.0])
    kume = np.array([0, 0, 1, 1, 2, 2])
    # küme toplamları 2, −2, 2; n 2,2,2; oran ort 1/3
    S = np.array([2.0, -2.0, 2.0]); N = np.array([2.0, 2.0, 2.0]); m = S.sum() / N.sum()
    beklenen = np.sqrt(3 / 2 * ((S - m * N) ** 2).sum()) / N.sum()
    assert np.isclose(mk.ortalama_se(x, kume), beklenen)
