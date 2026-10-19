# -*- coding: utf-8 -*-
"""Dokuzuncu dersin (neden başarısız) motor blokları ve biçimleri: girdiler sentetik ve küçük, beklenen metin elle
yazılabilir. Bloklar ölçümün basarisiz kaydını okur; sayıların tanımı basarisiz.py'de (testler/test_basarisiz.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import adlar  # noqa: E402
import ders_motor as dm  # noqa: E402

KUNYE = {"bitis": "2026-10-15", "baslangic": "2018-01-01", "ic_bitis": "2023-12-31", "dis_baslangic": "2024-01-01",
         "ciftler": ["EURUSD", "GBPUSD"], "nokta": {"EURUSD": 1e-5, "GBPUSD": 1e-5},
         "pip": {"EURUSD": 1e-4, "GBPUSD": 1e-4}, "uygulama_esik": {"rastgele": 20}}


def _kural(y, c, n=100):
    return {"y": y, "z": 0.0, "c": c, "c_makas": c / 2, "c_kayma": c / 2, "net": y - c, "ayna": -y - c, "n": n,
            "bilesim": 2}


def _u(ayrisim: dict | None = None, ek: dict | None = None):
    birim = {b: {"varsayilan": {}, "cift": {}} for bl in adlar.DERS_BIRIM.values() for b in bl}
    o = {"kunye": dict(KUNYE), "birim": birim, "basarisiz": {"ayrisim": ayrisim or {}}}
    o.update(ek or {})
    return dm.Uretim(o, {})


def test_bicim_puan_ve_dort_hane():
    assert dm.bicimle(0.084, "pu") == "+8,4"            # kesirlerin farkı puan, işaretli
    assert dm.bicimle(-0.015111, "pu") == "−1,5"
    assert dm.bicimle(0.0004, "pu") == "0,0"            # sıfıra yuvarlanan işaretsiz
    assert dm.bicimle(0.006741, "s4") == "0,0067"


def test_hesap_dort_islem_ve_sabit_ikinci_terim():
    u = _u()
    ctx = {"O": {"a": 1.6, "b": 11.5, "c": -0.015}}
    assert dm.blok_hesap(u, ctx, "bol", "O.a", "O.b", "yz0") == "%14"
    assert dm.blok_hesap(u, ctx, "carp", "O.c", "-100", "s1") == "1,5"      # açığın büyüklüğü, puan
    assert dm.blok_hesap(u, ctx, "fark", "O.b", "O.a", "s1") == "9,9"
    assert dm.blok_hesap(u, ctx, "topla", "O.a", "0.5", "s1") == "2,1"
    with pytest.raises(dm.SablonHatasi):
        dm.blok_hesap(u, ctx, "us", "O.a", "O.b", "s1")                     # bilinmeyen işlem
    with pytest.raises(dm.SablonHatasi):
        dm.blok_hesap(u, ctx, "bol", "O.yok", "O.b", "s1")                  # ölçülemeyen değer sessizce basılmaz


def test_kurallar_derslerin_sirasiyla_ve_bos_liste_duser():
    u = _u()
    ctx = u.kok_ctx()
    ctx["L"] = ["momentum", "orb", "icmum"]
    assert dm.blok_kurallar(u, ctx, "L") == "Londra ORB, İç mum ve Gün içi momentum"
    ctx["L"] = []
    with pytest.raises(dm.SablonHatasi):
        dm.blok_kurallar(u, ctx, "L")


def test_yon_cumlesi_aile_sayimi_ve_en_buyuk_pay():
    fade = adlar.DERS_BIRIM["fx-gunici-fade"]
    kir = adlar.DERS_BIRIM["fx-gunici-seans-kirilimlari"] + adlar.DERS_BIRIM["fx-gunici-yapi-kirilimlari"]
    oos = {b: _kural(0.02, 0.2) for b in fade}
    oos.update({b: _kural(-0.01 if i % 2 else 0.01, 0.1) for i, b in enumerate(kir)})
    oos["n2"] = _kural(0.09, 0.18, n=266)
    tum = {b: _kural(-0.01, 0.2) for b in fade}
    tum.update({b: _kural(0.01, 0.1) for b in kir})
    m = dm.blok_neden_yon_cumle(_u({"oos": {"kural": oos}, "tum": {"kural": tum}}), {})
    assert m.startswith("2024 → penceresinde yön payı fade dersinin altı kuralının hepsinde artı (bütün dönemde "
                        "hiçbirinde), seans kırılımları dersinin dört kuralının ikisinde artı (bütün dönemde hepsinde) "
                        "ve yapı kırılımları dersinin dört kuralının ikisinde artı (bütün dönemde hepsinde).")
    assert "ayırmaz" not in m                                # seans kırılımlarının hepsi artı değil: ters bahis yok
    assert "N2 fade (266 işlem): +0,090 R, maliyeti 0,180 R; yön payı maliyetin %50 kadarını karşılıyor." in m
    # Geri dönüşe (fade) ve devama (seans kırılımları) bahis giren iki aile aynı pencerede birlikte artıysa tablo
    # yönü ayırmaz ve cümle bunu söyler.
    oos2 = {**oos, **{b: _kural(0.01, 0.1) for b in adlar.DERS_BIRIM["fx-gunici-seans-kirilimlari"]}}
    m2 = dm.blok_neden_yon_cumle(_u({"oos": {"kural": oos2}, "tum": {"kural": tum}}), {})
    assert "seans kırılımları dersinin dört kuralının hepsinde artı" in m2
    assert ("tablo bu yüzden gün içi fiyatın devam mı geri dönüş mü eğiliminde olduğunu ayırmaz. Yön payının en büyük "
            "olduğu kural N2 fade") in m2
    with pytest.raises(dm.SablonHatasi):                                    # artı yön payı yoksa cümle kurulmaz
        dm.blok_neden_yon_cumle(_u({"oos": {"kural": {b: _kural(-0.01, 0.1) for b in fade + kir}},
                                    "tum": {"kural": tum}}), {})


def test_ayrisim_notu_tamamen_ve_kismen_disarida_kalanlari_ayirir():
    k = {"orb": _kural(0.05, 0.15), "asya": _kural(0.01, 0.08)}
    a = {"oos": {"kural": k, "dislanan": ["n4:EURUSD", "n4:GBPUSD", "asya:GBPUSD"]}}
    m = dm.blok_neden_ayrisim(_u(a), {})
    assert "Tabloda yok: N4 başarısız (paritelerinin hepsinde örneklem dışında 20 işlemden az" in m
    assert "Bazı paritesi dışarıda (aynı sebeple): Asya aralığı." in m
    assert m.index("| Asya aralığı") < m.index("| Londra ORB")              # net sonuca göre sıralı (−0,07 > −0,10)


def _ay_sonu_kume():
    def pen(r, a, b):
        return {"beklenti_r": r, "ga_alt": a, "ga_ust": b}
    uye = {"birim": "fiks_momentum", "cift": "GBPUSD", "kim": "varsayilan",
           "ay_sonu": {"is": pen(0.38, 0.055, 0.706), "oos": pen(0.198, -0.193, 0.598)},
           "degisen": [{"gun": "2024-03-28", "tanim": "bugun", "r": 0.4}, {"gun": "2024-03-29", "tanim": "eski", "r": -2.18},
                       {"gun": "2022-04-14", "tanim": "bugun", "r": 1.0}, {"gun": "2022-04-15", "tanim": "eski", "r": 0.2}]}
    return {"olculen": 1, "olculemedi": 1, "tutan_bugun": [dict(uye)], "tutan_eski": [],
            "uye": [uye, {"birim": "fiks_momentum", "cift": "GBPUSD", "kim": "tf15", "ay_sonu": None}]}


def test_ay_sonu_eski_tanim_iki_kip_ve_orneklem_disi_aylar():
    u = _u(ek={"karsi_olgu": {"ay_sonu_alt_kume": _ay_sonu_kume()}})
    kisa = dm.blok_ay_sonu_eski_tanim(u, {}, "kisa")
    assert "2024 → penceresinde +0,198 R (aralık −0,193 / +0,598)" in kisa
    assert "Mart 2024'te eski tanım 29.03.2024 günü −2,18 R, bugünkü tanım 28.03.2024 günü +0,40 R" in kisa
    assert "2022" not in kisa                                               # örneklem içinde ayrışan ay yazılmaz
    assert kisa.endswith("Derslerdeki ay sonu sayılarının hepsi ön kaydın tanımıyladır.")
    uzun = dm.blok_ay_sonu_eski_tanim(u, {})
    assert "eski tanımla ailenin hiçbir biçimi bu ölçütü sağlamaz" in uzun
    k = _ay_sonu_kume()
    k["uye"][1]["kim"] = "secilen"                                         # ölçülemeyen biçim zaman dilimi değil
    with pytest.raises(dm.SablonHatasi):
        dm.blok_ay_sonu_eski_tanim(_u(ek={"karsi_olgu": {"ay_sonu_alt_kume": k}}), {}, "kisa")


def test_kuyruk_cumlesi_donen_ve_parite_sayimi():
    def v(r, tek, uc, n=40):
        return {"varsayilan": {"oos": {"beklenti_r": r}, "kuyruk": {"oos": {"n": n, "r": r, "r_tek_haric": tek,
                                                                            "r_uc_haric": uc, "en_iyi_r": 5.0,
                                                                            "en_iyi_gun": "2024-05-01"}}}}
    u = _u()
    u.O["birim"]["orb"]["cift"] = {"EURUSD": v(0.1, 0.05, -0.01), "GBPUSD": v(0.2, 0.1, 0.05)}
    u.O["birim"]["asya"]["cift"] = {"GBPUSD": v(0.05, 0.04, 0.03), "EURUSD": v(-0.1, -0.2, -0.3)}
    m = dm.blok_neden_kuyruk_cumle(u, {})
    assert m == ("Örneklem dışında net sonucu artı kalan üç bileşimin birinde en iyi bir ya da üç işlem çıkınca sonuç "
                 "sıfıra ya da eksiye dönüyor; iki tanesi GBP/USD.")
