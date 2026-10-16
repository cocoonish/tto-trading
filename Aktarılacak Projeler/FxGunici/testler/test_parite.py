# -*- coding: utf-8 -*-
"""Parite sözlükleri ayar.toml'dan türer: ders motoru ve şekiller elle tutulan bir parite listesi taşımaz.

Ölçüm dosyasının künyesi parite listesini ve nokta/pip büyüklüklerini ayardan yazar (ders_olcum.kur); ders motoru
(ders_motor.parite_kur) ve figürler (sekil.parite_kur) onları künyeden kurar. Künyede tanımı olmayan bir parite
üretimi DÜŞÜRÜR: tahmin edilen bir nokta büyüklüğü fiyatı on kat kaydırır ve metin ya da figür yine yazılırdı.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BURASI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BURASI))
import ayar as ay  # noqa: E402
import ders_motor as dm  # noqa: E402

A = ay.oku()


def _kunye(ciftler=None) -> dict:
    cs = list(ciftler or A.ciftler)
    return {"ciftler": cs, "nokta": {c: A.nokta[c] for c in cs if c in A.nokta},
            "pip": {c: A.pip[c] for c in cs if c in A.pip}}


def test_ders_motoru_pariteleri_kunyeden_kurar():
    dm.parite_kur(_kunye())
    assert list(dm.PARITE) == list(A.ciftler)
    for c in A.ciftler:
        assert dm.PARITE[c] == f"{c[:3]}/{c[3:]}"
        assert dm.NOKTA[c] == A.nokta[c] and dm.PIP[c] == A.pip[c]
        assert 10 ** -dm.HANE[c] == pytest.approx(A.nokta[c])
    assert dm.ana() == A.ciftler[0]


def test_ders_motoru_sira_kunyenin_sirasi():
    ters = list(reversed(A.ciftler))
    dm.parite_kur(_kunye(ters))
    try:
        assert list(dm.PARITE) == ters and dm.ana() == ters[0]
    finally:
        dm.parite_kur(_kunye())


def test_ders_motoru_tanimsiz_pariteyle_duser():
    k = _kunye()
    k["ciftler"] = k["ciftler"] + ["EURCHF"]
    with pytest.raises(dm.SablonHatasi):
        dm.parite_kur(k)
    with pytest.raises(dm.SablonHatasi):
        dm.parite_kur({"ciftler": [], "nokta": {}, "pip": {}})


def test_sekiller_pariteleri_kunyeden_kurar():
    sekil = pytest.importorskip("sekil")
    sekil.parite_kur(_kunye())
    assert list(sekil.PARITE) == list(A.ciftler) and sekil.ANA == A.ciftler[0]
    assert all(sekil.NOKTA[c] == A.nokta[c] for c in A.ciftler)
    assert len(set(sekil.RENK.values())) == len(A.ciftler)      # her paritenin kendi rengi
    k = _kunye()
    del k["nokta"][A.ciftler[-1]]
    with pytest.raises(SystemExit):
        sekil.parite_kur(k)


def test_kodda_elle_parite_listesi_yok():
    """Motor ve şekil kaynağında parite sembolleri yalnız tanımlı yerlerde geçer: kısa kök eşlemesi (E/G/J/A) ve
    renk tablosu. Yeni bir elle liste bu sınamayı düşürür."""
    for ad, izinli in (("ders_motor.py", ("KISA_AD",)), ("sekil.py", ("RENK_SABIT",))):
        for satir in (BURASI / ad).read_text(encoding="utf-8").splitlines():
            kod = satir.split("#", 1)[0]
            if sum(f'"{c}"' in kod for c in A.ciftler) >= 3 and not any(i in kod for i in izinli):
                pytest.fail(f"{ad}: elle yazılmış parite listesi: {satir.strip()[:100]}")
