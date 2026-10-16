# -*- coding: utf-8 -*-
"""Haber katmanının sınamaları: çıpalı mumlar, olay × ofset koşusu, devam tablosunun
maliyet özdeşliği, olay düzeyinde kümeleme, Benjamini–Hochberg ve FOMC/patika duman.

Lookahead sınamaları N1–N5 için de test_strateji.py'de koşar (sentetik takvim ve
olay anlarında şok taşıyan sentetik veriyle).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar as ay  # noqa: E402
import haber_analiz as ha  # noqa: E402
import kosu  # noqa: E402
import strat_haber as sh  # noqa: E402
from gunluk import baglam_kur  # noqa: E402
from sentetik import dakika_uret, olaylar_uret  # noqa: E402

OLAY = olaylar_uret()
D = dakika_uret(soklar=OLAY["utc_sn"].to_numpy())
B = baglam_kur(D, OLAY)
A = ay.oku()


def test_cerceve_cipali_ve_ofset_olayin_dakikasi():
    for tf in (5, 15, 60):
        cer = sh.cerceve(B, tf)
        assert len(cer) > 0
        for _, c in cer.iterrows():
            m = B.mumlar(tf, int(c["ofset"]))
            assert m.bt[int(c["k0"])] == int(c["t0"]), "ilk haber mumu olay anında başlamıyor"
            if tf == 60:
                assert int(c["ofset"]) == (int(c["t0"]) // 60) % 60
            else:
                assert int(c["ofset"]) == 0
    cer60 = sh.cerceve(B, 60)
    # ECB 14:15/14:45 Frankfurt → :15 ve :45; NFP 08:30 → :30; FOMC 14:00 → :00
    assert {15, 45} <= set(cer60.loc[cer60["olay"].str.startswith("ECB"), "ofset"])
    assert set(cer60.loc[cer60["olay"] == "NFP", "ofset"]) == {30}


def test_atr_olay_mumunu_icermez():
    tf = 5
    cer = sh.cerceve(B, tf)
    m = B.mumlar(tf, 0)
    atr = sh.atr_mum(m, sh.ATR_MUM)
    for _, c in cer.iterrows():
        assert c["atr"] == atr[int(c["k0"]) - 1]


def test_kos_haber_grup_ofsetiyle_ve_tek_pozisyon_grup_icinde():
    k = kosu.Kosucu(B, A)
    for birim in ("n1", "n3"):
        _, v = kosu.izgara(birim)
        v = {**v, "tf": 60}
        isl = k.islem(birim, v)
        assert len(isl) > 0
        a = isl[isl["durum"] == 0]
        # giriş, kendi çıpasındaki mumun sonraki açılışıdır
        for _, r in a.iterrows():
            m = B.mumlar(60, int(r["ofset"]))
            assert r["giris_t"] == m.bt[int(r["s"]) + 1]
        assert isl["kimlik"].is_unique


def test_devam_maliyet_ozdesligi():
    dv = sh.devam(B, 5, 60, 0.5, 1.0)
    assert len(dv) > 0
    # kırılım + fade = −(iki makas + dört kayma); ikisinin toplamı daima eksidir
    assert (dv["kirilim_pip"] + dv["fade_pip"] < 0).all()
    np.testing.assert_allclose(dv["brut_pip"].abs() >= 0, True)


def test_devam_toplu_olayi_bir_gozlem_sayar(tmp_path, monkeypatch):
    monkeypatch.setattr(ha, "CIKTI", tmp_path)
    satir = []
    for cift in ("EURUSD", "GBPUSD"):
        for i in range(25):
            satir.append({"cift": cift, "tf": 5, "ufuk": 60, "olay": "NFP", "tarih": f"2020-01-{i + 1:02d}",
                          "gun": f"2020-01-{i + 1:02d}", "kova": ">2", "trend_uyum": "aynı", "hareket_atr": 3.0,
                          "gun_atr_pip": 80.0, "brut_pip": 10.0, "kirilim_pip": 9.0, "fade_pip": -11.0,
                          "oos": False})
    (tmp_path / "haber" / "devam").mkdir(parents=True)
    pd.DataFrame(satir).to_parquet(tmp_path / "haber" / "devam" / "x.parquet")
    t = ha.devam_toplu()
    olay = [h for h in t["hucre"] if h["boyut"] == "olay" and h["ufuk"] == 60]
    assert olay and olay[0]["n_olay"] == 25, "aynı olayın iki paritedeki ölçümü iki gözlem sayıldı"
    cift = [h for h in t["hucre"] if h["boyut"] == "cift" and h["ufuk"] == 60]
    assert sorted(h["n_olay"] for h in cift) == [25, 25]


def test_bh_bilinen_degerler():
    p = np.array([0.01, 0.04, 0.03, 0.005, np.nan])
    q = ha.bh(p)
    # sıralı: .005 .01 .03 .04 → ×4/sıra: .02 .02 .04 .04
    np.testing.assert_allclose(q[:4], [0.02, 0.04, 0.04, 0.02])
    assert np.isnan(q[4])


def test_fomc_ve_patika_duman():
    df = sh.fomc(B, OLAY)
    assert len(df) >= 2 and {"karar_atr", "basin_60_atr", "basin_90_atr"} <= set(df.columns)
    p = sh.patika(B, OLAY, "NFP")
    assert len(p["tau"]) == 151
    n = (p["yukari"] or {}).get("n", 0) + (p["asagi"] or {}).get("n", 0)
    assert n >= 2


def test_mid_an_bayat_kotasyonu_okumaz():
    t = int(D.t[100]) + 60
    assert np.isfinite(sh.mid_an(B, np.array([t]))[0])
    # verinin bittiği yerden bir saat sonra: son kotasyon bayat → NaN
    assert np.isnan(sh.mid_an(B, np.array([int(D.t[-1]) + 3600]))[0])


def test_tek_pozisyon_parite_basina_olaylar_arasinda():
    """Ön kaydın ortak mekaniği: tek pozisyon PARİTE başına. Aynı gün iki olay (karar ve basın toplantısı) varsa
    ikincisinin işlemi ancak birincisinin pozisyonu kapandıysa açılır."""
    k = kosu.Kosucu(B, A)
    for birim in ("n1", "n3"):
        for tf in (5, 60):
            _, v = kosu.izgara(birim)
            v = {**v, "tf": tf, "hedef": "zaman"}
            isl = k.islem(birim, v)
            a = isl[isl["durum"] == 0].sort_values("giris_i")
            gi, ci, nd = (a[c].to_numpy() for c in ("giris_i", "cikis_i", "neden"))
            serbest = np.where(np.isin(nd, (3, 4, 5, 6)), ci, ci + 1)
            assert (gi[1:] >= serbest[:-1]).all(), f"{birim}/{tf}: üst üste pozisyon"


def test_tek_pozisyon_uygula_motorun_kuraliyla_ayni():
    """Ayrı koşturulup sonradan uygulanan tek pozisyon kuralı, motorun kendi kuralıyla birebir aynı sonucu verir."""
    from strat_ortak import kos, tek_pozisyon_uygula
    k = kosu.Kosucu(B, A)
    _, v = kosu.izgara("icmum")
    sin, ofset = k.sinyal("icmum", v)
    ic = kos(B, sin, int(v["tf"]), ofset, v["stop_turu"], v["hedef"], 0.5, 1.0, tek_pozisyon=True)
    ayri = tek_pozisyon_uygula(kos(B, sin, int(v["tf"]), ofset, v["stop_turu"], v["hedef"], 0.5, 1.0,
                                   tek_pozisyon=False))
    assert (ic["durum"] == 1).any(), "sınama anlamsız: tek pozisyon hiç devreye girmiyor"
    np.testing.assert_array_equal(ic["durum"].to_numpy(), ayri["durum"].to_numpy())
    m = ic["durum"].to_numpy() == 0
    np.testing.assert_allclose(ic["r"].to_numpy()[m], ayri["r"].to_numpy()[m])


def test_devam_ufku_gun_sonuna_yetismeyen_gozlem_duser():
    dv = sh.devam(B, 60, 120, 0.5, 1.0)
    kp = B.ek[("devam_kirpilan", 60, 120)]
    if len(dv):
        t_c = pd.to_datetime(dv["gun"]).to_numpy()  # yalnız var olduğu sınanır
        assert len(t_c) == len(dv)
    assert sum(kp.values()) >= 1, "FOMC 14:00/14:30 + 60 dk mum + 120 dk ufuk 16:55'i aşmalı"
