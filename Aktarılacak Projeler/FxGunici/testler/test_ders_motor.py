# -*- coding: utf-8 -*-
"""Ders motoru: biçim sözleşmesi, yol, koşul, iddia, sabit ve blok davranışı."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ders_motor as dm  # noqa: E402

O = {"kunye": {"bitis": "2026-10-15"},
     "birim": {"orb": {"aile": "orb", "varsayilan": {"tf": 15},
                       "cift": {"EURUSD": {"varsayilan": {"oos": {"beklenti_r": -0.0412, "n": 1431, "isabet": 0.2798,
                                                                  "ga_alt": -0.091, "bos": None},
                                                          "maliyet": {"0.5": {"oos": {"beklenti_r": -0.04}}},
                                                          "hukum": "calismiyor"},
                                           "ornek": [{"gun": "2026-10-14", "islem": {"giris_f": 111986.0}}]}},
                       "havuz": {"varsayilan": {}}}}}


def _u():
    return dm.Uretim(O, {"orb": {"izgara": {"tf": [5, 15]}}})


def test_bicim_sozlesmesi():
    assert dm.bicimle(-0.0412, "r") == "−0,04"
    assert dm.bicimle(0.0412, "r") == "+0,04"
    assert dm.bicimle(-0.001, "r") == "0,00"            # sıfıra yuvarlanan işaretsiz
    assert dm.bicimle(0.2798, "yz1") == "%28,0"
    assert dm.bicimle(-0.031, "yz1") == "−%3,1"           # işaret yüzdeden önce
    assert dm.bicimle(1431, "n") == "1.431"
    assert dm.bicimle("2026-10-14", "tarih_uzun") == "14 Ekim 2026"
    with pytest.raises(dm.SablonHatasi):
        dm.bicimle(None, "r")                            # ölçülemeyen değer sessizce basılmaz
    assert dm.bicimle(None, "r?") == "—"


def test_yol_ve_tirnakli_anahtar():
    u = _u()
    ctx = u.birim_ctx("orb")
    assert dm.yol_coz('E.varsayilan.maliyet."0.5".oos.beklenti_r', ctx) == -0.04
    assert dm.yol_coz("E.ornek.[0].gun", ctx) == "2026-10-14"
    assert dm.yol_coz("E.yok.boyle", ctx) is None
    with pytest.raises(dm.SablonHatasi):
        dm.yol_coz("Z.x", ctx)


def test_kosul_ve_iddia():
    u = _u()
    ctx = u.birim_ctx("orb")
    assert dm.kosul('E.varsayilan.hukum == "calismiyor" and E.varsayilan.oos.n > 1000', ctx)
    assert dm.kosul('E.varsayilan.oos.beklenti_r > 0 or E.varsayilan.oos.n >= 1431', ctx)
    assert not dm.kosul("not E.varsayilan.oos.n", ctx)
    assert u.isle("A{{? E.varsayilan.oos.ga_alt < 0 }}B", ctx) == "AB"
    with pytest.raises(dm.SablonHatasi, match="İDDİA"):
        u.isle("{{? E.varsayilan.oos.beklenti_r > 0 }}", ctx)
    with pytest.raises(dm.SablonHatasi):            # ölçülemeyenle büyüklük kıyası tanımsız
        dm.kosul("E.varsayilan.oos.bos > 0", ctx)


def test_if_elif_else_ic_ice():
    u = _u()
    ctx = u.birim_ctx("orb")
    s = ('{% if E.varsayilan.hukum == "calisiyor" %}X{% elif E.varsayilan.oos.n > 1000 %}'
         '{% if E.varsayilan.oos.isabet > 0.5 %}Y{% else %}Z{% endif %}{% else %}W{% endif %}')
    assert u.isle(s, ctx) == "Z"
    with pytest.raises(dm.SablonHatasi):
        u.isle("{% if E.varsayilan.oos.n %}açık kaldı", ctx)


def test_sabit_bildirilir_ve_fiyat():
    u = _u()
    ctx = u.birim_ctx("orb")
    assert u.isle('BB({{= "20" }}, {{= "2" }})', ctx) == "BB(20, 2)"
    assert u.sabitler == ["20", "2"]
    assert u.isle("{{ E.ornek.[0].islem.giris_f | fiyat }}", ctx) == "1,11986"
    with pytest.raises(dm.SablonHatasi):
        u.isle("{{ E.varsayilan.oos.n }}", ctx)          # biçimsiz yer tutucu yok


def test_sekil_numarasi_ve_import():
    sablon = "---\ntitle: 'x'\n---\n\n{{! sekil karsilastirma-ozet Özet }}\n{{! sekil veri-makas Makas }}\n"
    m, u = dm.ders_uret(sablon, O, {})
    assert "import GrafikEmbed" in m and m.index("import") > m.index("---\n", 4)
    assert 'no="01"' in m and 'no="02"' in m and u.sekiller == ["karsilastirma-ozet", "veri-makas"]
