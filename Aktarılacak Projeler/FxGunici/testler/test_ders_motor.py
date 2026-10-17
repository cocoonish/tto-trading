# -*- coding: utf-8 -*-
"""Ders motoru: biçim sözleşmesi, yol, koşul, iddia, sabit ve blok davranışı."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ders_motor as dm  # noqa: E402

# Künye pariteleri tanımlar (ders_motor.parite_kur): motor elle tutulan bir parite listesi taşımaz.
O = {"kunye": {"bitis": "2026-10-15", "ciftler": ["EURUSD"], "nokta": {"EURUSD": 1e-5}, "pip": {"EURUSD": 1e-4}},
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


def _pratik_u(ek_neden: int, ek_cikis_t: int) -> tuple:
    """Hedefte kapanan bir örnek işlem ve onun ek kaymalı yeniden koşusu (çıkış nedeni ve anı parametre)."""
    kunye = {"bitis": "2026-10-15", "ciftler": ["EURUSD"], "nokta": {"EURUSD": 1e-5}, "pip": {"EURUSD": 1e-4},
             "gun_sonu_et": "16:55", "temel_kayma_pip": 0.5, "haber_kayma_pip": 1.0, "haber_pencere_dk": [-2, 15]}
    islem = {"yon": 1, "giris_t": 1760436000, "cikis_t": 1760439600, "giris_f": 111986.0, "stop": 111836.0,
             "cikis_f": 112286.0, "hedef": 112286.0, "neden": 2, "hedef_tur": 1, "hedef_k": 2.0, "r": 2.0,
             "pnl_pip": 30.0, "R_pip": 15.0, "stopsuz": False}
    hedefte = ek_neden in (2, 6)
    ek_cikis = 112316.0 if hedefte else 112100.0
    ek = {"kayma_pip": 1.5, "durum": 0, "giris_f": 111996.0, "stop": 111836.0, "hedef": 112316.0,
          "cikis_f": ek_cikis, "cikis_t": ek_cikis_t, "neden": ek_neden,
          "pnl_pip": (ek_cikis - 111996.0 - 10) / 10 if not hedefte else 32.0, "R_pip": 16.0}
    ek["r"] = ek["pnl_pip"] / ek["R_pip"]
    o = {"kunye": kunye, "birim": {"orb": {"aile": "orb", "varsayilan": {}, "havuz": {"varsayilan": {}},
                                           "cift": {"EURUSD": {"ornek": [{"etiket": "kazanan", "gun": "2025-10-14",
                                                                          "islem": islem, "ek_kayma": ek,
                                                                          "takvim": []}]}}}}}
    u = dm.Uretim(o, {"orb": {"izgara": {}}})
    return u, u.birim_ctx("orb")


def test_pratik_ek_kayma_hedefe_yine_ulasinca_ulasilamadi_yazilmaz():
    # Ek kaymalı koşu da hedefte (30 dakika sonra) kapanırsa: "yine ulaşıldı", "ulaşılamadı" değil.
    u, ctx = _pratik_u(2, 1760441400)
    m = dm.blok_pratik_islem(u, ctx, "orb", "Alıştırma", "kazanan")
    assert "yine ulaşıldı" in m and "ulaşılamadı" not in m
    # Ek kaymalı koşu hedefe değmeden başka bir çıkışla kapanırsa: "ulaşılamadı".
    u, ctx = _pratik_u(3, 1760443200)
    m = dm.blok_pratik_islem(u, ctx, "orb", "Alıştırma", "kazanan")
    assert "ulaşılamadı" in m


def test_pratik_r_gosterilen_sayilardan():
    # "a / b = c" satırında c gösterilen a ve b'den: 30 / 15 = +2,00.
    u, ctx = _pratik_u(2, 1760441400)
    m = dm.blok_pratik_islem(u, ctx, "orb", "Alıştırma", "kazanan")
    assert "30,0 / 15,0 = **+2,00 R**" in m
    assert dm._oran_yaz("22,8", "29,05") == "+0,78"      # kayıttaki 0,785'in ikinci yuvarlaması 0,79 yazardı


def test_mevsim_kovalari_tek_tanim():
    """Tek bir yerel saatte giren kuralın iki kovası (yaz, kış); metin ve figür aynı tanımı okur."""
    import adlar
    k = lambda d: {str(h): {"n": n} for h, n in d.items()}
    assert adlar.mevsim_kovalari(k({17: 1358, 18: 913})) == (17, 18)
    assert adlar.mevsim_kovalari(k({23: 900, 0: 500})) == (23, 0)          # gece yarısını aşan ardışık saatler
    assert adlar.mevsim_kovalari(k({17: 500, 18: 900})) is None             # geç kova kalabalıksa mevsim değil
    assert adlar.mevsim_kovalari(k({17: 900, 19: 500})) is None             # ardışık değil
    assert adlar.mevsim_kovalari(k({17: 393, 18: 847, 19: 361})) is None    # üç kova
    assert adlar.mevsim_kovalari(k({17: 900, 18: 500, 19: 0})) == (17, 18)  # boş kova sayılmaz
    st = {"17": {"n": 1358, "beklenti_r": -0.20}, "18": {"n": 913, "beklenti_r": -0.19}}
    u = _u()
    ctx = {"B": {"cift": {"EURUSD": {"varsayilan": {"saat_tsi": st}}}}}
    u.ON = {"kosul": {"asgari_kova_islem": 30}}
    metin = dm.blok_saat_okuma(u, ctx, "EURUSD")
    assert "yaz saatinde 17:00–17:59 TSİ" in metin and "kış saatinde 18:00–18:59 TSİ" in metin
