# -*- coding: utf-8 -*-
"""Figür yardımcıları (sekil.py), ikinci tur: örnek günün gösterge çizgisi ve patikaya girmeyen olayların alt yazısı.

Gösterge kuralın KENDİ tanımından gelir ve mumlarla aynı sırada durur: boyu tutmayan bir bant çizilmez, figür düşer.
Patikanın dışında kalan olaylar tarih ve sebebiyle yazılır; günlük ATR'si olmadığı için devam tablosundan da düşen
olayın sebebi ölçülmüş sebebidir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sekil = pytest.importorskip("sekil")
from plotly.subplots import make_subplots  # noqa: E402

K2 = {"ciftler": ["EURUSD", "GBPUSD"], "nokta": {"EURUSD": 1e-5, "GBPUSD": 1e-5},
      "pip": {"EURUSD": 1e-4, "GBPUSD": 1e-4}}


def test_patika_disinda_kalanlar_tarih_ve_sebepleriyle():
    sekil.parite_kur(K2)
    o = {"kunye": {"haber_sabit": {"patika_yon_sn": 300}},
         "haber": {"cift": {"EURUSD": {"patika": {"NFP": {"dislanan": [
                                {"tarih": "2024-03-08", "neden": "ilk_bes_dakikada_yon_yok"},
                                {"tarih": "2024-01-05", "neden": "tatil_ya_da_atr_yok"}]}}},
                            "GBPUSD": {"patika": {"NFP": {"dislanan": [
                                {"tarih": "2024-03-08", "neden": "ilk_bes_dakikada_yon_yok"}]}}}},
                   "olcu_disi": {"devam_atr": [{"olay": "NFP", "tarih": "2024-01-05",
                                                "parite": {"EURUSD": "gunluk_atr_yok"}}]}}}
    s = sekil._patika_dislanan(o, "NFP", ["EURUSD", "GBPUSD"])
    assert s == ("Çizilmeyen: 05.01.2024 (EUR/USD: günlük ATR yok) · "
                 "08.03.2024 (iki parite: ilk beş dakikada fiyat değişmedi, yön yok)")
    # Devam tablosundan ATR yüzünden düşmeyen olay patikanın kendi sebebini taşır.
    o["haber"]["olcu_disi"]["devam_atr"] = []
    assert "05.01.2024 (EUR/USD: tatil günü ya da günlük ATR yok)" in sekil._patika_dislanan(o, "NFP",
                                                                                           ["EURUSD", "GBPUSD"])
    assert sekil._patika_dislanan(o, "CPI", ["EURUSD", "GBPUSD"]) == ""


def _var():
    return {k: False for k in ("seviye", "stop", "hedef", "olay", "takvim", "bb", "kc", "sikisma", "vwap", "vbant")}


def test_vwap_cizgisi_mumlarla_ayni_sirada():
    t = np.arange(5) * 900 + 1_700_000_000
    sec = np.array([True, True, False, True, True])
    x = {"cizgi": {"tur": "vwap_donus", "vwap": [110000, 110010, 110020, None, 110040],
                   "bant_ust": [110100] * 5, "bant_alt": [109900] * 5}}
    fig = make_subplots(rows=1, cols=1)
    var = _var()
    sekil._cizgi_ekle(fig, x, sec, t, 900, 1e-5, 1, var, 2.0, "%{y:.5f}")
    ad = [tr.name for tr in fig.data]
    assert ad == ["VWAP (gün içinde yürür)", "VWAP ± 2,0σ bandı", "VWAP ± 2,0σ bandı"]
    assert [tr.showlegend for tr in fig.data] == [True, True, False]       # bandın iki kenarı tek lejant
    y = list(fig.data[0].y)
    assert y[:2] == pytest.approx([1.1, 1.1001]) and y[2] is None and y[3] == pytest.approx(1.1004)
    assert var["vwap"] and var["vbant"]
    # Geri çekilmede bant yoktur.
    fig = make_subplots(rows=1, cols=1)
    sekil._cizgi_ekle(fig, {"cizgi": {"tur": "vwap_cekilme", "vwap": [110000] * 5}}, sec, t, 900, 1e-5, 1, _var(),
                      2.0, "%{y:.5f}")
    assert [tr.name for tr in fig.data] == ["VWAP (gün içinde yürür)"]
    with pytest.raises(SystemExit, match="aynı boyda değil"):
        sekil._cizgi_ekle(make_subplots(rows=1, cols=1), {"cizgi": {"tur": "vwap_donus", "vwap": [1, 2]}}, sec, t,
                          900, 1e-5, 1, _var(), 2.0, "%{y:.5f}")
    fig = make_subplots(rows=1, cols=1)
    sekil._cizgi_ekle(fig, {"cizgi": {}}, sec, t, 900, 1e-5, 1, _var(), 2.0, "%{y:.5f}")
    assert len(fig.data) == 0


def test_sikisma_bantlari_ve_gölgeli_mum_kosulari():
    t = np.arange(6) * 900 + 1_700_000_000
    sec = np.ones(6, bool)
    cz = {"tur": "sikisma", "bb_ust": [2.0] * 6, "bb_alt": [1.0] * 6, "kc_ust": [2.5] * 6, "kc_alt": [0.5] * 6,
          "sikisma": [False, True, True, False, True, False]}
    fig = make_subplots(rows=1, cols=1)
    var = _var()
    sekil._cizgi_ekle(fig, {"cizgi": cz}, sec, t, 900, 1.0, 1, var, 2.0, "%{y:.5f}")
    assert [tr.name for tr in fig.data] == ["Bollinger bandı"] * 2 + ["Keltner kanalı"] * 2
    assert len(fig.layout.shapes) == 2 and var["sikisma"]              # iki ardışık koşu → iki gölge
    cz["sikisma"] = cz["sikisma"][:5]
    with pytest.raises(SystemExit, match="sıkışma mumları"):
        sekil._cizgi_ekle(make_subplots(rows=1, cols=1), {"cizgi": cz}, sec, t, 900, 1.0, 1, _var(), 2.0, "")
