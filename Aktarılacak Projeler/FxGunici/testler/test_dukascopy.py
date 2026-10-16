# -*- coding: utf-8 -*-
"""Dukascopy çözücüsünün birim testleri — sentetik bi5 dosyalarıyla (ağa çıkmaz)."""
from __future__ import annotations

import lzma
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dukascopy as dk  # noqa: E402


def bi5(kayitlar: list[tuple], sira: str = "ocLH") -> bytes:
    """(saniye, o, h, l, c, hacim) listesini Dukascopy biçiminde (o, c, l, h) paketler.

    `sira="ohlc"` YANLIŞ sırayla paketler — çözücünün bunu yakaladığını sınamak için.
    """
    dizi = np.zeros(len(kayitlar), dtype=dk.KAYIT)
    for i, (s, o, h, l, c, v) in enumerate(kayitlar):
        if sira == "ocLH":
            dizi[i] = (s, o, c, l, h, v)
        else:
            dizi[i] = (s, o, h, l, c, v)
    return lzma.compress(dizi.tobytes(), format=lzma.FORMAT_ALONE)


def ornek_gun(n: int = 1440, tohum: int = 7, dolgu_her: int = 0):
    r = np.random.default_rng(tohum)
    fiyat = 110000
    satir = []
    for i in range(n):
        if dolgu_her and i % dolgu_her == 0:
            satir.append((i * 60, fiyat, fiyat, fiyat, fiyat, 0.0))
            continue
        o = fiyat
        c = fiyat + int(r.integers(-8, 9))
        h = max(o, c) + int(r.integers(0, 5))
        l = min(o, c) - int(r.integers(0, 5))
        satir.append((i * 60, o, h, l, c, float(r.uniform(0.5, 9.0))))
        fiyat = c
    return satir


def test_coz_dogru_sira():
    s = ornek_gun(100)
    k = dk.coz(bi5(s))
    assert len(k) == 100
    assert int(k["o"][5]) == s[5][1] and int(k["h"][5]) == s[5][2] and int(k["l"][5]) == s[5][3] and int(k["c"][5]) == s[5][4]


def test_coz_yanlis_sirayi_yakalar():
    with pytest.raises(dk.CozumHatasi):
        dk.coz(bi5(ornek_gun(100), sira="ohlc"))


def test_coz_bos_dosya():
    assert len(dk.coz(b"")) == 0


def test_coz_izgara_ve_artis_sinamasi():
    s = ornek_gun(10)
    s[3] = (s[3][0] + 30, *s[3][1:])       # dakika ızgarasına oturmayan ofset
    with pytest.raises(dk.CozumHatasi):
        dk.coz(bi5(s))
    s = ornek_gun(10)
    s[4], s[5] = s[5], s[4]                 # sıra bozuk
    with pytest.raises(dk.CozumHatasi):
        dk.coz(bi5(s))


def test_gun_cerceve_dolguyu_atar_ve_ask_bid_farkini_yazar():
    bid = ornek_gun(1440, tohum=1, dolgu_her=10)
    ask = [(s, o + 3, h + 4, l + 2, c + 3, v * 1.1) for (s, o, h, l, c, v) in bid]
    cer = dk.gun_cerceve(date(2024, 1, 2), dk.coz(bi5(bid)), dk.coz(bi5(ask)))
    assert len(cer) == 1440 - 144                       # her 10 dakikada bir dolgu
    assert cer["t"].iloc[0] == int(pd.Timestamp("2024-01-02 00:01", tz="UTC").timestamp())
    assert (cer["d_o"] == 3).all() and (cer["d_h"] == 4).all() and (cer["d_l"] == 2).all() and (cer["d_c"] == 3).all()


def test_yaz_oku_deterministik(tmp_path):
    bid = ornek_gun(600, tohum=3)
    ask = [(s, o + 2, h + 2, l + 2, c + 2, v) for (s, o, h, l, c, v) in bid]
    cer = dk.gun_cerceve(date(2024, 1, 3), dk.coz(bi5(bid)), dk.coz(bi5(ask)))
    oz1 = dk.yaz(cer, tmp_path / "X" / "2024.parquet")
    oz2 = dk.yaz(cer, tmp_path / "Y" / "2024.parquet")
    assert oz1 == oz2
    geri = dk.oku_ham(tmp_path, "X")
    assert geri["t"].tolist() == cer["t"].tolist()
    f = dk.fiyatla(geri, 1e-5)
    assert np.allclose(f["ask_c"] - f["bid_c"], 2e-5)
    assert np.allclose(f["c"], (f["ask_c"] + f["bid_c"]) / 2)
    assert str(f.index.tz) == "UTC"


def test_saatlik_url_ay_sifirdan():
    assert dk.dakika_url("EURUSD", date(2024, 1, 2), "BID").endswith("/EURUSD/2024/00/02/BID_candles_min_1.bi5")
    assert dk.saatlik_url("USDJPY", 2026, 12, "ASK").endswith("/USDJPY/2026/11/ASK_candles_hour_1.bi5")
