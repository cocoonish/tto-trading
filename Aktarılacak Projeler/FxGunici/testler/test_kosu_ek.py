# -*- coding: utf-8 -*-
"""Ön kaydın aileye özgü iki ölçüsü: fiksingde ay sonu ayrımı, momentumda HAC regresyonu.

Regresyon elle kurulan bir örneğe karşı sınanır (standart hata formülü kodun kendisinden
türetilmez); ay sonu ayrımı sentetik bir işlem tablosunda kümeleri ve farkı doğru ayırmalı."""
from __future__ import annotations

import pytest
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kosu  # noqa: E402


def test_nw_ols_gecikme_sifirda_beyaz_standart_hata():
    # L = 0: HAC, White'ın varyansıdır. Elle: V = (X'X)^-1 (Σ u² x x') (X'X)^-1.
    rng = np.random.default_rng(3)
    x = rng.normal(size=400)
    y = 0.2 + 0.5 * x + rng.normal(size=400) * (1 + 0.5 * np.abs(x))
    r = kosu.nw_ols(x, y, lag=0)
    X = np.column_stack([np.ones(len(x)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    u = y - X @ b
    A = np.linalg.inv(X.T @ X)
    V = A @ (X.T * u ** 2) @ X @ A
    assert math.isclose(r["beta"], b[1], rel_tol=1e-10)
    assert math.isclose(r["se_beta"], math.sqrt(V[1, 1]), rel_tol=1e-10)
    assert r["lag"] == 0


def test_nw_ols_gecikme_ilintili_hatada_standart_hatayi_buyutur():
    # Pozitif ilintili x ve hata: Bartlett gecikmeleri standart hatayı büyütmeli.
    rng = np.random.default_rng(5)
    n = 2000
    e, v = rng.normal(size=n), rng.normal(size=n)
    x, u = np.zeros(n), np.zeros(n)
    for t in range(1, n):
        x[t] = 0.7 * x[t - 1] + v[t]
        u[t] = 0.7 * u[t - 1] + e[t]
    y = 0.1 * x + u
    beyaz = kosu.nw_ols(x, y, lag=0)["se_beta"]
    hac = kosu.nw_ols(x, y)["se_beta"]
    assert hac > 1.3 * beyaz
    assert kosu.nw_ols(x, y)["lag"] == int(np.floor(4 * (n / 100) ** (2 / 9)))


def test_ay_sonu_ayrimi_kumeler_ve_fark():
    gun = pd.date_range("2019-01-01", periods=200, freq="B").to_numpy().astype("datetime64[D]")
    ay_sonu = np.zeros(200, bool)
    ay_sonu[::20] = True
    r = np.where(ay_sonu, 1.0, -0.1) + np.linspace(-0.01, 0.01, 200)
    a = pd.DataFrame({"gun": gun, "ay_sonu": ay_sonu, "r": r, "pnl_pip": r * 10})
    icm = np.arange(200) < 120
    o = kosu.ay_sonu_ayrimi(a, icm)
    assert o["ay_sonu"]["tum"]["n"] == 10 and o["diger"]["tum"]["n"] == 190
    assert o["ay_sonu"]["is"]["n"] == 6 and o["ay_sonu"]["oos"]["n"] == 4
    assert o["fark"]["tum"]["fark_r"] > 1.0 and o["fark"]["tum"]["p"] < 1e-6
    assert o["ay_sonu"]["tum"]["ga_alt"] <= o["ay_sonu"]["tum"]["beklenti_r"] <= o["ay_sonu"]["tum"]["ga_ust"]


def test_basabas_kesisimi():
    """Başabaş kayma: net R'nin ızgarada sıfırı kestiği nokta (doğrusal), sıfırda bile eksi → 0, sonda bile artı → None."""
    import kosu
    assert kosu._sifir_kesisim([0.0, 0.5, 1.0, 2.0], [0.053, 0.011, -0.028, -0.1]) == pytest.approx(
        0.5 + 0.5 * 0.011 / (0.011 + 0.028))
    assert kosu._sifir_kesisim([0.0, 0.5], [-0.01, -0.05]) == 0.0
    assert kosu._sifir_kesisim([0.0, 0.5], [0.2, 0.1]) is None


def test_ornek_gunler_ve_kuyruk_sentetik(tmp_path, monkeypatch):
    """Örnek seçimi (R eşikleri, ayrı günler, sabit çekiliş), ek kaymalı yeniden koşu ve kuyruk duyarlılığı.
    Sentetik bağlamda; çıktı geçici dizine yazılır (sentetik parite adı gerçek arşivle aynıdır)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ayar as ay
    from gunluk import baglam_kur
    from sentetik import dakika_uret, olaylar_uret
    monkeypatch.setattr(kosu, "CIKTI", tmp_path)
    olay = olaylar_uret()
    b = baglam_kur(dakika_uret(soklar=olay["utc_sn"].to_numpy()), olay)
    k = kosu.Kosucu(b, ay.oku())
    for birim in ("asya", "fiks_donus"):
        s = kosu.birim_kos(birim, k)
        va = s["varsayilan_analiz"]
        orn = va["ornek"]
        assert orn, f"{birim}: örnek yok"
        gunler = [o["gun"] for o in orn]
        assert len(set(gunler)) == len(gunler), f"{birim}: aynı gün iki örnek"
        for o in orn:
            i, e = o["islem"], o["ek_kayma"]
            if o["secim"] == "kural":
                if o["etiket"] == "kazanan":
                    assert i["r"] >= kosu.ORNEK_ESIK
                elif o["etiket"] == "kaybeden":
                    assert i["r"] <= -kosu.ORNEK_ESIK and i["mfe_r"] < kosu.ORNEK_ESIK
                else:
                    assert i["r"] < 0 and i["mfe_r"] >= kosu.ORNEK_ESIK
            if i["stopsuz"]:
                assert i["stop"] is None and e["stop"] is None
            # R katı hedef yürütülen girişten kurulur: iki koşuda da hedefte kapanan işlem tam k R yazar
            if i["hedef_tur"] == 1 and i["neden"] == 2 and e["neden"] == 2:
                assert abs(e["r"] - i["hedef_k"]) < 1e-9 and abs(i["r"] - i["hedef_k"]) < 1e-9
            if e["durum"] == 0:
                assert e["kayma_pip"] == kosu.KAYMA_TEMEL + kosu.ORNEK_EK_KAYMA
        # aynı girdiyle aynı örnekler (çekiliş sabit)
        assert kosu.ornek_gunler(k, birim, s["varsayilan"], k.islem(s["aile"], s["varsayilan"]),
                                 k.sinyal(s["aile"], s["varsayilan"])[1]) == orn
        q = va["kuyruk"]
        assert {"is", "oos", "tum"} <= set(q)
        t = q["tum"]
        if t.get("n", 0) >= 4:
            assert t["r_tek_haric"] <= t["r"] + 1e-12
        assert va["hukum"] in ("calisiyor", "zayif", "calismiyor", "olculemedi")
        assert set(va["yalniz_makas"]) == {"is", "oos", "tum"}
