# -*- coding: utf-8 -*-
"""Arşivleyicinin kaldığı yerden sürmesi — ağ yerine sahte kaynakla.

Birinci koşuda bazı günler hatayla döner; arşiv o günler eksik hâlde yazılır.
İkinci koşu YALNIZ eksik günleri ister ve birimi tamamlar. Sınanan şey,
16.10.2026 bulut koşusunda iki yıllık birimin 16 ve 11 gün eksik yüzünden
bütünüyle atılmasının bir daha olmaması.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import arsiv_dukascopy as arsiv  # noqa: E402
import ayar as ay  # noqa: E402
import dukascopy as dk  # noqa: E402
from test_dukascopy import bi5, ornek_gun  # noqa: E402


def test_kaldigi_yerden_surer(tmp_path, monkeypatch):
    a = ay.oku()
    a = a.__class__(**{**a.__dict__, "ciftler": ("EURUSD",), "baslangic": date(2024, 1, 1),
                       "bitis": date(2024, 1, 10), "butce_dk": 5.0})
    monkeypatch.setattr(ay, "oku", lambda *x, **k: a)
    monkeypatch.setattr(ay, "DUKA", tmp_path / "dukascopy")
    istenen: list[str] = []
    bozuk = {"2024/00/03", "2024/00/07"}
    kosu = {"n": 1}

    def sahte_getir(url, deneme=6, zaman_asimi=20.0, son_an=None):
        istenen.append(url)
        if "candles_hour" in url:
            return dk.Yanit("yok")
        parca = url.split("/EURUSD/")[1][:10]
        if kosu["n"] == 1 and parca in bozuk:
            return dk.Yanit("hata", ayrinti="ReadTimeoutError", deneme=deneme)
        g = int(parca[-2:])
        return dk.Yanit("tamam", bi5(ornek_gun(60, tohum=g)), deneme=1)

    monkeypatch.setattr(dk, "getir", sahte_getir)
    assert arsiv.main() == 0
    k = dk.kunye_oku(ay.DUKA)["birimler"]["EURUSD/2024"]
    assert not k["tam"] and len(k["gun_hata"]) == 2 and k["gun_dolu"] == 8
    # ikinci koşu: yalnız iki eksik gün istenmeli
    kosu["n"] = 2
    istenen.clear()
    assert arsiv.main() == 0
    gunluk = [u for u in istenen if "candles_min" in u]
    assert len(gunluk) == 4 and all(any(b in u for b in bozuk) for u in gunluk)
    k = dk.kunye_oku(ay.DUKA)["birimler"]["EURUSD/2024"]
    assert k["tam"] and k["gun_dolu"] == 10 and k["satir"] == 600
    df = dk.oku_ham(ay.DUKA, "EURUSD")
    assert np.all(np.diff(df["t"].to_numpy()) > 0)
    # üçüncü koşu: tam birime dokunulmaz
    istenen.clear()
    assert arsiv.main() == 0
    assert not [u for u in istenen if "candles_min" in u]
