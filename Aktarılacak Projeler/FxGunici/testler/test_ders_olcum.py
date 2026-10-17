# -*- coding: utf-8 -*-
"""Ölçüm katmanının ikinci tur parçaları (ders_olcum): seçilenin komşuları, ay sonu ailesi, büyük olay günü
yoğunluğu ve takvimde durup bir haber ölçüsüne girmeyen olaylar.

Her biri ders metninin bir cümlesinin tek tanımıdır; metin onları yeniden hesaplamaz. Girdiler sentetik ve küçük,
beklenen sonuç elle sayılabilir.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ayar as ay  # noqa: E402
import ders_olcum as do  # noqa: E402
import haber_analiz as ha  # noqa: E402


# ─────────────────────────────────────────────── seçilenin tek parametre komşuları
def _satir(tf, k, hedef, oos):
    return {"p": {"tf": tf, "k": k, "hedef": hedef, "capa": "londra"}, "is": {"beklenti_r": 0.0},
            "oos": {"beklenti_r": oos}}


def test_komsular_yalniz_bir_parametresi_degisenler():
    izgara = [_satir(tf, k, h, round(0.01 * tf + k + (h == "2R"), 3))
              for tf in (5, 15, 30) for k in (1.0, 1.5) for h in ("1R", "2R")
              if (tf, k, h) != (30, 1.0, "2R")]                      # ızgarada tanımsız bileşim
    s = {"secilen": {"tf": 15, "k": 1.0, "hedef": "2R", "capa": "londra"}, "izgara": izgara}
    k = do.komsular(s)
    tf = k["parametre"]["tf"]
    assert [x["deger"] for x in tf["satir"]] == [5, 15]               # 30 dk komşusu ızgarada yok
    assert tf["tanimsiz"] == 1 and [x["secilen"] for x in tf["satir"]] == [False, True]
    assert [x["deger"] for x in k["parametre"]["k"]["satir"]] == [1.0, 1.5]
    assert [x["deger"] for x in k["parametre"]["hedef"]["satir"]] == ["1R", "2R"]
    assert "capa" not in k["parametre"]                               # tek değerli boyut komşu üretmez
    # Her satırda öbür parametreler seçilenin değerindedir.
    for ad, p in k["parametre"].items():
        for x in p["satir"]:
            assert x["oos"]["beklenti_r"] == round(0.01 * (x["deger"] if ad == "tf" else 15)
                                                   + (x["deger"] if ad == "k" else 1.0)
                                                   + ((x["deger"] if ad == "hedef" else "2R") == "2R"), 3)
    assert do.komsular({"secilen": None, "izgara": izgara}) is None


# ─────────────────────────────────────────────── ay sonu ailesi
def _ayrim(oos_alt, oos_p, is_alt, is_p, tum_alt=-1.0):
    return {"ay_sonu": {"oos": {"ga_alt": oos_alt, "beklenti_r": 0.1}, "is": {"ga_alt": is_alt, "beklenti_r": 0.1},
                        "tum": {"ga_alt": tum_alt}},
            "fark": {"oos": {"p": oos_p}, "is": {"p": is_p}, "tum": {"p": 0.9}}}


def test_ay_sonu_ailesi_tekillestirme_esik_ve_iki_ayrik_donem():
    tutan = _ayrim(0.01, 0.01, 0.02, 0.02)
    birimler = {
        "fiks_momentum": {"aile": "fiks", "varsayilan": {"tf": 5}, "cift": {"EURUSD": {
            "varsayilan": {"p": {"tf": 5}, "imza": "a", "ay_sonu": tutan},
            "secilen_p": {"tf": 15}, "secilen": {"imza": "a", "ay_sonu": tutan},       # aynı işlem kümesi
            "ay_sonu_tf": {"15": {"p": {"tf": 15}, "imza": "b", "ayrim": _ayrim(0.01, 0.03, 0.02, 0.01)},
                           "30": {"p": {"tf": 30}, "imza": None, "ayrim": None}}}}},  # hiç işlem açmayan biçim
        "orb": {"aile": "orb", "varsayilan": {}, "cift": {"EURUSD": {"varsayilan": {"imza": "x", "ay_sonu": tutan}}}},
    }
    a = do.ay_sonu_ailesi(birimler)
    assert a["n"] == 2 and a["esik"] == pytest.approx(0.05 / 2)
    v = next(u for u in a["uye"] if u["kim"] == "varsayilan")
    assert v["esdeger"] == ["secilen"] and v["tutar"]
    t15 = next(u for u in a["uye"] if u["kim"] == "tf15")
    assert not t15["tutar"] and not t15["sart"]["oos"]["fark_esik"]   # p 0,03 > 0,025
    assert a["tutan"] == [{"birim": "fiks_momentum", "cift": "EURUSD", "kim": "varsayilan"}]
    # Örneklem içi şartı tutmayan ayrım tutmaz; bütün dönem tutarlılık ölçütü değildir.
    birimler["fiks_momentum"]["cift"]["EURUSD"]["varsayilan"]["ay_sonu"] = _ayrim(0.01, 0.01, -0.01, 0.01, 0.5)
    birimler["fiks_momentum"]["cift"]["EURUSD"]["secilen"]["ay_sonu"] = _ayrim(0.01, 0.01, -0.01, 0.01, 0.5)
    assert do.ay_sonu_ailesi(birimler)["tutan"] == []
    assert do.ay_sonu_ailesi({})["n"] == 0 and do.ay_sonu_ailesi({})["esik"] is None


# ─────────────────────────────────────────────── büyük olay günü yoğunluğu
A = ay.oku()


def _yogunluk(tmp_path, monkeypatch, r, olay_gunleri, oos_n=None):
    gun = pd.to_datetime([f"2024-0{1 + i // 9}-{1 + i % 9:02d}" for i in range(len(r))])
    yol = tmp_path / "x.parquet"
    pd.DataFrame({"gun": gun, "r": np.asarray(r, float), "durum": 0}).to_parquet(yol)
    monkeypatch.setattr(do, "_islem_dosyasi", lambda *a_, **k_: yol)
    hg = {gun[i].date() for i in olay_gunleri}
    monkeypatch.setattr(do, "_haber_gunleri", lambda c: hg)
    kosul = [{"degisken": "haber_gunu", "kovalar": [{"kova": "haber günü",
                                                    "oos_n": len(hg) if oos_n is None else oos_n}]}]
    return do.haber_gunu_yogunlugu(tmp_path, "orb", "EURUSD", {}, kosul, A)


def test_haber_gunu_yogunlugu_pay_ve_en_iyi_tek_islem(tmp_path, monkeypatch):
    y = _yogunluk(tmp_path, monkeypatch, [2.5, -1, -1, 0.5, 1.0, -1, 1.5, 0.2], [0, 6])
    assert y["n"] == 8 and y["n_olay"] == 2 and y["toplam_r"] == pytest.approx(2.7)
    assert y["pay"] == pytest.approx(4.0 / 2.7) and y["islem_payi"] == pytest.approx(0.25)
    assert y["en_iyi_r"] == 2.5 and y["en_iyi_olay_gunu"] and y["en_iyi_tekil"]
    assert y["pay_en_iyi_haric"] == pytest.approx((4.0 - 2.5) / (2.7 - 2.5))
    # En iyi değeri iki işlem paylaşıyorsa (2R hedefi) "en iyi tek işlem" yoktur.
    y = _yogunluk(tmp_path, monkeypatch, [2.0, -1, 2.0, -1, 0.5], [0])
    assert not y["en_iyi_tekil"]


def test_haber_gunu_yogunlugu_eksi_toplam_ve_iki_tanim(tmp_path, monkeypatch):
    assert _yogunluk(tmp_path, monkeypatch, [-1.0, 0.5, -0.2], [0]) is None          # eksi toplamın payı okunmaz
    with pytest.raises(ValueError, match="haber_gunu_yogunlugu"):                       # iki tanım ayrışmasın
        _yogunluk(tmp_path, monkeypatch, [1.0, 0.5, -0.2], [0], oos_n=2)
    monkeypatch.setattr(do, "_islem_dosyasi", lambda *a_, **k_: tmp_path / "yok.parquet")
    assert do.haber_gunu_yogunlugu(tmp_path, "orb", "EURUSD", {}, [], A) is None


# ─────────────────────────────────────────────── ölçünün gerçek düşürmeleri
def test_olcu_disi_gercek_dusurmeler(tmp_path, monkeypatch):
    tf, uf = str(ha.ANA_TF), [int(u) for u in ha.UFUK]
    h = tmp_path / "sonuc" / "haber"
    h.mkdir(parents=True)
    devam_cpi = {str(u): [{"olay": "CPI", "tarih": "2024-04-10", "neden": "ilk_mumda_yon_yok"}] for u in uf}
    devam_cpi[str(uf[-1])].append({"olay": "NFP", "tarih": "2024-05-03", "neden": "cikis_fiyati_yok"})
    (h / "EURUSD.json").write_text(json.dumps({
        "atlanan_olay": {tf: [{"olay": "NFP", "tarih": "2024-03-08", "neden": "giris_dakikasi_yok"}]},
        "patika": {"CPI": {"dislanan": [{"tarih": "2024-02-13", "neden": "tatil_ya_da_atr_yok"}]}},
        "devam_dusen": {tf: devam_cpi}}))
    (h / "GBPUSD.json").write_text(json.dumps({
        "atlanan_olay": {tf: [{"olay": "NFP", "tarih": "2024-03-08", "neden": "giris_dakikasi_yok"}]}}))
    (h / "devam.json").write_text(json.dumps({"atr_dusen": [
        {"cift": "EURUSD", "olay": "CPI", "tarih": "2024-02-13"},
        {"cift": "USDCAD", "olay": "CPI", "tarih": "2024-02-13"}]}))       # ayardaki pariteler dışı: sayılmaz
    takvim_ = pd.DataFrame({"olay": ["NFP", "CPI", "CPI", "NFP"],
                            "tarih": ["2024-03-08", "2024-04-10", "2024-02-13", "2024-05-03"],
                            "ciftler": ["EURUSD GBPUSD"] * 4})
    monkeypatch.setattr(do.takvim, "tumu", lambda: takvim_)
    od = do.olcu_disi(tmp_path, ["EURUSD", "GBPUSD"], n1_tf=int(tf))
    assert od["cerceve"] == [{"olay": "NFP", "tarih": "2024-03-08",
                              "parite": {"EURUSD": "giris_dakikasi_yok", "GBPUSD": "giris_dakikasi_yok"},
                              "her_paritede": True}]
    cpi = next(e for e in od["devam"] if e["olay"] == "CPI")
    assert cpi["tum_ufuk"] == {"EURUSD": True} and not cpi["her_paritede"]
    assert cpi["ufuk"]["EURUSD"]["ilk_mumda_yon_yok"] == uf
    nfp = next(e for e in od["devam"] if e["olay"] == "NFP")
    assert nfp["tum_ufuk"] == {"EURUSD": False} and nfp["ufuk"]["EURUSD"] == {"cikis_fiyati_yok": [uf[-1]]}
    assert od["devam_atr"] == [{"olay": "CPI", "tarih": "2024-02-13", "parite": {"EURUSD": "gunluk_atr_yok"},
                                "her_paritede": False}]
    assert od["patika"][0]["parite"] == {"EURUSD": "tatil_ya_da_atr_yok"}
    assert od["n1_ana_mumda"] is True and od["ufuklar"] == sorted(uf)
    assert do.olcu_disi(tmp_path, ["EURUSD", "GBPUSD"])["n1_ana_mumda"] is None


# ─────────────────────────────────────────────── stratejilerin tatil takvimi ↔ arşivin kapsamı
def test_tatil_uyum_takvim_ile_kapsam():
    kalite = {"EURUSD": {"ilk": "2023-12-21 22:00", "son": "2024-01-05 21:59",
                         "kapsam": {"tatil_gunleri": [["2023-12-25", 0.0], ["2024-01-01", 3.1]]}},
              "GBPUSD": {"ilk": "2023-12-21 22:00", "son": "2024-01-05 21:59",
                         "kapsam": {"tatil_gunleri": [["2023-12-25", 0.0]]}},
              "meta": "parite değil"}
    t = do.tatil_uyum(kalite)
    assert t["EURUSD"]["ayni"] and t["EURUSD"]["takvim"] == 2
    assert not t["GBPUSD"]["ayni"] and t["GBPUSD"]["yalniz_takvim"] == ["2024-01-01"]
    assert "meta" not in t and do.tatil_uyum(None) is None
    # 21.12.2023 22:00 UTC New York'ta 17:00: o an başlayan gün 22.12'nin FX günüdür.
    assert t["EURUSD"]["ilk_fx_gunu"] == "2023-12-22"
    assert do._fx_gunu("2024-01-05 21:59") == date(2024, 1, 5)
