# -*- coding: utf-8 -*-
"""Günlük tablonun "önceki işlem günü" zinciri: tatil satırı tablodan çıkmaz ama zincire girmez."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gunluk as gl  # noqa: E402


def _seri(n=40, tatil_k=(20,)):
    rng = np.random.default_rng(3)
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    o = np.concatenate([[100.0], c[:-1]])
    h = np.maximum(o, c) + rng.uniform(0.5, 1.5, n)
    l = np.minimum(o, c) - rng.uniform(0.5, 1.5, n)
    tatil = np.zeros(n, bool)
    for k in tatil_k:
        # tatil satırı: ince kotasyon, dar aralık
        h[k], l[k] = c[k - 1] + 0.05, c[k - 1] - 0.05
        o[k] = c[k] = c[k - 1]
        tatil[k] = True
    return h, l, c, o, tatil


def test_tatil_ertesi_onceki_gun_tatilden_onceki_islem_gunu():
    h, l, c, o, tatil = _seri()
    oh, ol, oc, oo, atr, atr_y, nr4, nr7 = gl.onceki_zincir(h, l, c, o, tatil)
    # 21. gün (tatilin ertesi): önceki gün 19. gün
    assert oh[21] == h[19] and ol[21] == l[19] and oc[21] == c[19] and oo[21] == o[19]
    # tatilden öncesi ve sonrası olağan
    assert oh[19] == h[18] and oh[22] == h[21]
    assert np.isnan(oh[0])


def test_tatilsiz_seride_eski_tanimla_ayni():
    h, l, c, o, tatil = _seri(tatil_k=())
    oh, ol, oc, oo, atr, atr_y, nr4, nr7 = gl.onceki_zincir(h, l, c, o, tatil)
    assert np.array_equal(oh[1:], h[:-1]) and np.isnan(oh[0])
    tr = np.empty(len(h))
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])
    atr_eski = np.concatenate([[np.nan], gl._wilder(tr, 14)[:-1]])
    assert np.allclose(atr, atr_eski, equal_nan=True)
    aralik = h - l
    for i in range(7, len(h)):
        assert nr7[i] == (aralik[i - 1] <= aralik[i - 7:i].min() + 1e-9)


def test_tatil_satiri_atr_ve_nr_zincirine_girmez():
    h, l, c, o, tatil = _seri()
    oh, ol, oc, oo, atr, atr_y, nr4, nr7 = gl.onceki_zincir(h, l, c, o, tatil)
    # tatil satırını hiç içermeyen seriyle karşılaştır: tatil ertesi günün ATR ve NR bayrakları aynı olmalı
    m = ~tatil
    hh, ll, cc, oo2 = h[m], l[m], c[m], o[m]
    oh2, ol2, oc2, _, atr2, _, nr4_2, nr7_2 = gl.onceki_zincir(hh, ll, cc, oo2, np.zeros(m.sum(), bool))
    idx = np.flatnonzero(m)
    assert np.allclose(atr[idx], atr2, equal_nan=True)
    assert np.array_equal(nr4[idx], nr4_2) and np.array_equal(nr7[idx], nr7_2)


def test_eurusd_2019_01_02_onceki_gun_31_12_2018():
    """Gerçek veri: EUR/USD 02.01.2019'un önceki işlem günü 31.12.2018'dir (01.01.2019 tatil, tek dakika)."""
    import ayar as ay
    import veri as vr
    a = ay.oku()
    try:
        d = vr.oku("EURUSD", a)
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"veri yok: {e}")
    g = gl.gunluk_kur(d, orneklem=(a.baslangic, a.bitis))
    k = int(np.flatnonzero(g.gun == np.datetime64("2019-01-02"))[0])
    j = int(np.flatnonzero(g.gun == np.datetime64("2018-12-31"))[0])
    assert g.tatil[int(np.flatnonzero(g.gun == np.datetime64("2019-01-01"))[0])]
    assert g.onceki_h[k] == g.h[j] and g.onceki_l[k] == g.l[j] and g.onceki_c[k] == g.c[j]
