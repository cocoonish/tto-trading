# -*- coding: utf-8 -*-
"""Koşul kovaları: sınırlar yalnız örneklem içinden, eksik değer kova değildir, hüküm kuralı."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import saglamlik as sg  # noqa: E402


def _tablo(n=400, tohum=5):
    r = np.random.default_rng(tohum)
    yon = r.choice(["aynı yön", "ters yön"], n).astype(object)
    yon[:25] = None                                      # eksik değer
    atr = r.uniform(0.2, 2.0, n)
    # "ters yön" günlerinde beklenti artı, öbürlerinde eksi — örneklem içinde VE dışında
    rr = np.where(yon == "ters yön", 0.4, -0.3) + r.normal(0, 0.5, n)
    return pd.DataFrame({"onceki_gun_yon": yon, "range_atr": atr, "r": rr, "pnl_pip": rr * 10})


def test_eksik_deger_kova_degildir_ve_hukum():
    f = _tablo()
    ic = np.arange(len(f)) < 250
    out = {k["degisken"]: k for k in sg.kova_analizi(f, ic, asgari=30)}
    y = out["onceki_gun_yon"]
    assert sorted(k["kova"] for k in y["kovalar"]) == ["aynı yön", "ters yön"]     # "nan" kovası yok
    assert y["secilen"] == ["ters yön"] and y["hukum"] == "tuttu"
    assert y["oos_secilen_r"] > 0 > y["oos_tamamlayan_r"]


def test_surekli_sinirlar_yalniz_orneklem_icinden():
    f = _tablo()
    ic = np.arange(len(f)) < 250
    f.loc[~ic, "range_atr"] += 5.0                       # örneklem dışı kaydırılırsa sınır değişmemeli
    out = {k["degisken"]: k for k in sg.kova_analizi(f, ic, asgari=30)}
    q = np.nanpercentile(f["range_atr"][ic], [100 / 3, 200 / 3])
    assert np.allclose(out["range_atr"]["sinir"], q)
    oos_ust = next(k for k in out["range_atr"]["kovalar"] if k["kova"] == "üst")["oos_n"]
    assert oos_ust == int((~ic).sum())                   # bütün kaydırılmış gözlemler üst kovada


def test_secim_orneklem_disinda_tutmazsa_tutmadi():
    f = _tablo()
    ic = np.arange(len(f)) < 250
    # örneklem dışında işaret döner: seçilen kova OOS'ta eksi
    f.loc[~ic, "r"] = np.where(f.loc[~ic, "onceki_gun_yon"] == "ters yön", -0.4, 0.3)
    out = {k["degisken"]: k for k in sg.kova_analizi(f, ic, asgari=30)}
    assert out["onceki_gun_yon"]["secilen"] == ["ters yön"] and out["onceki_gun_yon"]["hukum"] == "tutmadi"


def test_ters_secim_bilgili_kosulda_tutmaz():
    """Kova farkı gerçekse ters seçim (örneklem içinde ortalamanın altındaki kova) örneklem dışında tutmaz."""
    f = _tablo()
    ic = np.arange(len(f)) < 250
    y = {k["degisken"]: k for k in sg.kova_analizi(f, ic, asgari=30)}["onceki_gun_yon"]
    t = y["ters_secim"]
    assert t["secilen"] == ["aynı yön"] and t["hukum"] == "tutmadi"
    assert t["oos_secilen_r"] < 0 < t["oos_tamamlayan_r"]


def test_ters_secim_tersine_donen_kosulda_tutar():
    """İşaret örneklem dışında dönerse gerçek seçim tutmaz, ters seçim tutar: iki seçim simetriktir."""
    f = _tablo()
    ic = np.arange(len(f)) < 250
    f.loc[~ic, "r"] = np.where(f.loc[~ic, "onceki_gun_yon"] == "ters yön", -0.4, 0.3)
    y = {k["degisken"]: k for k in sg.kova_analizi(f, ic, asgari=30)}["onceki_gun_yon"]
    assert y["hukum"] == "tutmadi" and y["ters_secim"]["hukum"] == "tuttu"


def test_ters_secim_bos_kumede_secilmedi():
    """Bütün kovalar ortalamanın üstündeyse (tek kova) ters seçim boştur: 'secilmedi'."""
    f = _tablo()
    f["sabit"] = "tek"
    ic = np.arange(len(f)) < 250
    y = {k["degisken"]: k for k in sg.kova_analizi(f, ic, asgari=30)}["sabit"]
    assert y["hukum"] == "secilmedi" and y["ters_secim"]["hukum"] == "secilmedi"


def test_esdeger_degisken_tek_sayilir():
    """Aynı ölçünün iki adı tek değişkendir: ikincisi 'esdeger' diye kayda geçer, sayıma girmez."""
    f = _tablo()
    f["asya_atr"] = f["range_atr"]
    ic = np.arange(len(f)) < 250
    k = {x["degisken"]: x for x in sg.kova_analizi(f, ic, asgari=30)}
    assert k["asya_atr"]["hukum"] == "esdeger" and k["asya_atr"]["esdeger"] == "range_atr"
    assert k["range_atr"]["hukum"] in ("tuttu", "tutmadi", "secilmedi", "hepsi")


def test_kosulsuz_ortalama_tanimli_islemlerden_ve_hepsi_ayri():
    """Bütün kovaları seçilen değişken 'hepsi'dir, hiç kova seçilmeyen 'secilmedi': iki ayrı durum. Koşulsuz ortalama
    değişkenin tanımlı olduğu işlemlerden kurulur (tanımsız işlemler kıyası başka kümeye çekmez)."""
    f = _tablo()
    ic = np.arange(len(f)) < 250
    # yalnız ilk 100 işlemde tanımlı ve hepsi yüksek R'li iki kova: tanımlı işlemlerde biri ortalamanın üstünde
    x = np.full(len(f), None, dtype=object)
    x[:100] = np.where(np.arange(100) % 2 == 0, "a", "b")
    f["iki"] = x
    f.loc[:99, "r"] = np.where(np.arange(100) % 2 == 0, 2.0, 1.0)
    y = {k["degisken"]: k for k in sg.kova_analizi(f, ic, asgari=30)}["iki"]
    assert y["secilen"] == ["a"], y["secilen"]           # koşulsuz (tanımlı) ortalama 1,5: yalnız "a" üstünde
    assert abs(y["ic_kosulsuz_r"] - 1.5) < 1e-9


def test_dsr_gurultu_esigi_orneklem_hatasindan():
    """Gürültü eşiği V₀ = 1/(T−1)'den: denemeler ne kadar dağınık olursa olsun değişmez; kesitsel eşik dağınıklıkla büyür."""
    import math
    rng = np.random.default_rng(1)
    g = rng.normal(0, 1, 1500)
    dar = sg.dsr(0.01, rng.normal(0, 0.01, 100), g)
    genis = sg.dsr(0.01, rng.normal(-0.2, 0.3, 100), g)
    assert dar["sr0_gurultu_yillik"] == genis["sr0_gurultu_yillik"]
    assert genis["sr0_yillik"] > 5 * dar["sr0_yillik"]
    N, T = 100, 1500
    carpan = (1 - sg.EULER) * sg.stats.norm.ppf(1 - 1 / N) + sg.EULER * sg.stats.norm.ppf(1 - 1 / (N * math.e))
    assert abs(dar["sr0_gurultu_yillik"] - math.sqrt(1 / (T - 1)) * carpan * math.sqrt(252)) < 1e-12


def test_tek_denemede_psr_ve_tanimsiz_esikler():
    rng = np.random.default_rng(1)
    g = rng.normal(0.02, 1.0, 500)
    sr = g.mean() / g.std(ddof=1)
    t = sg.psr_tek(sr, g)
    eski = sg.dsr(sr, np.array([sr, sr]), g)          # eski kurulum: dsr alanı PSR'a eşitti
    assert t["n_deneme"] == 1 and t["dsr"] == t["psr"] == pytest.approx(eski["psr"])
    assert t["dsr_gurultu"] is None and t["sr0_gurultu_yillik"] is None and t["sr0_yillik"] == 0.0
