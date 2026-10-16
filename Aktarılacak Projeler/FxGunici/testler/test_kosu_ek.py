# -*- coding: utf-8 -*-
"""Ön kaydın aileye özgü iki ölçüsü: fiksingde ay sonu ayrımı, momentumda HAC regresyonu.

Regresyon elle kurulan bir örneğe karşı sınanır (standart hata formülü kodun kendisinden
türetilmez); ay sonu ayrımı sentetik bir işlem tablosunda kümeleri ve farkı doğru ayırmalı."""
from __future__ import annotations

import pytest
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kosu  # noqa: E402


def test_nw_ols_gecikme_sifirda_beyaz_standart_hata():
    # L = 0: HAC, White'ın varyansıdır. Elle: V = (X'X)^-1 (Σ u² x x') (X'X)^-1.
    rng = np.random.default_rng(3)
    x = rng.normal(size=400)
    y = 0.2 + 0.5 * x + rng.normal(size=400) * (1 + 0.5 * np.abs(x))
    r = kosu.nw_ols(x, y, lag=0)
    X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    u = y - X @ b
    A = np.linalg.inv(X.T @ X)
    V = A @ (X.T * u ** 2) @ X @ A
    assert math.isclose(r["beta"], b[1], rel_tol=1e-10)
    assert math.isclose(r["se_beta"], math.sqrt(V[1, 1]), rel_tol=1e-10)
    assert r["lag"] == 0


def test_nw_ols_gecikme_ilintili_hatada_standart_hatayi_buyutur():
    # Pozitif ilintili x ve hata: Bartlett gecikmeleri standart hatayı büyütmeli.
    rng = np.random.default_rng(5)
    n = 2000
    e, v = rng.normal(size=n), rng.normal(size=n)
    x, u = np.zeros(n), np.zeros(n)
    for t in range(1, n):
        x[t] = 0.7 * x[t - 1] + v[t]
        u[t] = 0.7 * u[t - 1] + e[t]
    y = 0.1 * x + u
    beyaz = kosu.nw_ols(x, y, lag=0)["se_beta"]
    hac = kosu.nw_ols(x, y)["se_beta"]
    assert hac > 1.3 * beyaz
    assert kosu.nw_ols(x, y)["lag"] == int(np.floor(4 * (n / 100) ** (2 / 9)))


def test_ay_sonu_ayrimi_kumeler_ve_fark():
    gun = pd.date_range("2019-01-01", periods=200, freq="B").to_numpy().astype("datetime64[D]")
    ay_sonu = np.zeros(200, bool)
    ay_sonu[::20] = True
    r = np.where(ay_sonu, 1.0, -0.1) + np.linspace(-0.01, 0.01, 200)
    a = pd.DataFrame({"gun": gun, "ay_sonu": ay_sonu, "r": r, "pnl_pip": r * 10})
    icm = np.arange(200) < 120
    o = kosu.ay_sonu_ayrimi(a, icm)
    assert o["ay_sonu"]["tum"]["n"] == 10 and o["diger"]["tum"]["n"] == 190
    assert o["ay_sonu"]["is"]["n"] == 6 and o["ay_sonu"]["oos"]["n"] == 4
    assert o["fark"]["tum"]["fark_r"] > 1.0 and o["fark"]["tum"]["p"] < 1e-6
    assert o["ay_sonu"]["tum"]["ga_alt"] <= o["ay_sonu"]["tum"]["beklenti_r"] <= o["ay_sonu"]["tum"]["ga_ust"]


def test_basabas_kesisimi():
    """Başabaş kayma: net R'nin ızgarada sıfırı kestiği nokta (doğrusal), sıfırda bile eksi → 0, sonda bile artı → None."""
    import kosu
    assert kosu._sifir_kesisim([0.0, 0.5, 1.0, 2.0], [0.053, 0.011, -0.028, -0.1]) == pytest.approx(
        0.5 + 0.5 * 0.011 / (0.011 + 0.028))
    assert kosu._sifir_kesisim([0.0, 0.5], [-0.01, -0.05]) == 0.0
    assert kosu._sifir_kesisim([0.0, 0.5], [0.2, 0.1]) is None
