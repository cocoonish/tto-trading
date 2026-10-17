# -*- coding: utf-8 -*-
"""Okur adları ve saat yazımı (adlar): ders metninin ve figürlerin tek tanımı.

TSİ karşılığı üç saat rejiminden (yaz · kış · ara hafta) hesaplanır ve aynı sonucu veren rejim bir kez yazılır; saat
değiştirmeyen bir şehir tek saatle yazılır. Olay adı bir parantezin içine girerken kendi kısaltma parantezini bırakır
(iç içe parantez açılmaz). Artı kalan pariteler metin ile figürün ortak listesidir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adlar  # noqa: E402


def test_tsi_yaz_rejimleri_ve_tekillestirme():
    # Londra saati: ara hafta (ABD yaz, İngiltere kış saatinde) kışla aynıdır, bir kez yazılır.
    assert adlar.tsi_yaz(["Londra 08:00"]) == "TSİ yazın 10:00, kışın 11:00"
    # New York saati: ara hafta yazla aynıdır.
    assert adlar.tsi_yaz(["New York 08:30"]) == "TSİ yazın 15:30, kışın 16:30"
    # İki şehir birlikte üç rejimin üçü de ayrı.
    assert adlar.tsi_yaz(["Londra 08:00", "New York 14:00"], "→") == \
        "TSİ yazın 10:00 → 21:00, kışın 11:00 → 22:00, ara haftalarda 11:00 → 21:00"
    # Aralık biçimi.
    assert adlar.tsi_yaz(["Londra 15:55–16:00"]) == "TSİ yazın 17:55–18:00, kışın 18:55–19:00"


def test_tsi_yaz_saat_degistirmeyen_sehir_tek_saat():
    # Tokyo yaz saati uygulamaz: "yazın" demek kışın başka olduğunu ima ederdi.
    assert adlar.tsi_yaz(["Tokyo 09:55"]) == "TSİ 03:55"


def test_tsi_yaz_okunamayan_saat_duser():
    with pytest.raises(ValueError):
        adlar.tsi_yaz(["Paris 10:00"])
    with pytest.raises(ValueError):
        adlar.tsi_yaz(["Londra 8:00"])
    with pytest.raises(ValueError):
        adlar.tsi_yaz([])


def test_olay_ic_parantez_icinde_parantez_acmaz():
    assert adlar.olay_ic("CPI") == "ABD TÜFE"
    assert adlar.olay_ic("NFP") == "ABD tarım dışı istihdam"
    assert adlar.olay_ic("FOMC_karar") == adlar.OLAY["FOMC_karar"] == "FOMC kararı"
    assert adlar.olay_ic("bilinmeyen") == "bilinmeyen"
    for k in adlar.OLAY:
        assert "(" not in adlar.olay_ic(k)


def test_arti_pariteler_verilen_sirayla():
    b = {"cift": {"EURUSD": {"varsayilan": {"hukum": "calismiyor", "oos": {"beklenti_r": -0.1}}},
                  "GBPUSD": {"varsayilan": {"hukum": "zayif", "oos": {"beklenti_r": -0.01}}},
                  "USDJPY": {"varsayilan": {"hukum": "calismiyor", "oos": {"beklenti_r": 0.02}}},
                  "AUDUSD": {"varsayilan": {}}}}
    # Hükmü zayıf olan (net eksi olsa da) ve net artı kalan girer; ölçümü olmayan ve ölçümde bulunmayan girmez.
    assert adlar.arti_pariteler(b, ["USDJPY", "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"]) == ["USDJPY", "GBPUSD"]
    assert adlar.arti_pariteler(b, ["GBPUSD", "USDJPY"]) == ["GBPUSD", "USDJPY"]
    assert adlar.arti_pariteler({}, ["EURUSD"]) == []
