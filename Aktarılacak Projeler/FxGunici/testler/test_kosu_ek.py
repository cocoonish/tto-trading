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


def test_secim_esitligi_toleransla_izgaradaki_ilk():
    """Ön kayıt: eşitlikte ızgaradaki ilk kombinasyon. İşlevsel kopyalar kayan nokta artığıyla (≤ 1e−14) ayrışır."""
    a = [{"p": "yok", "is": {"sharpe": -1.1153529309034298}},
         {"p": "sert", "is": {"sharpe": -1.4464}},
         {"p": "kapanis", "is": {"sharpe": -1.1153529309034196}}]
    assert kosu._sec(a)["p"] == "yok"
    b = [{"p": "a", "is": {"sharpe": 0.5}}, {"p": "b", "is": {"sharpe": 0.5 + 1e-6}}]
    assert kosu._sec(b)["p"] == "b"           # gerçek fark toleransın üstünde: büyük olan
    assert kosu._sec([]) is None


def test_imza_siniflayici_islevsel_kopya_ve_bos():
    def isl(gi, ci, yon, r, durum=None):
        n = len(gi)
        return pd.DataFrame({"giris_i": gi, "cikis_i": ci, "yon": yon, "r": r,
                             "durum": durum if durum is not None else np.zeros(n, int)})
    s = kosu.ImzaSiniflayici()
    a = s.sinif(isl([1, 5], [3, 9], [1, -1], [0.5, -1.0]))
    b = s.sinif(isl([1, 5], [3, 9], [1, -1], [0.5 + 1e-13, -1.0]))      # kayan nokta artığı: kopya
    c = s.sinif(isl([1, 5], [3, 9], [1, -1], [0.5, -0.9]))              # aynı dakikalar, farklı R: ayrı
    d = s.sinif(isl([1], [3], [1], [0.5], durum=np.array([2])))          # hiç alınan işlem yok: boş
    assert a == b and c != a and d is None


def test_kuyruk_esit_en_iyi_islemler_tarih_yazmaz():
    """En yüksek R'yi birden çok işlem paylaşıyorsa 'en iyi işlem' tarihi ve riski yazılmaz; eşit sayı ve risk aralığı
    yazılır; hariç ortalamalar hangi eşit işlemin çıktığından bağımsız."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ayar as ay
    from gunluk import baglam_kur
    from sentetik import dakika_uret
    b = baglam_kur(dakika_uret())
    k = kosu.Kosucu(b, ay.oku())
    gun = k.gun_tum[:8]
    r = np.array([2.0, -1.0, 2.0, 0.3, 2.0, -1.0, 0.1, -0.5])
    isl = pd.DataFrame({"durum": 0, "r": r, "gun": gun, "giris_i": np.arange(8) * 10 + 5,
                        "R_pip": [10.0, 5, 30, 8, 6, 7, 9, 4], "pnl_pip": r * 10})
    q = kosu.kuyruk(k, isl, 0.5)["tum"]
    assert q["en_iyi_esit"] == 3 and q["en_iyi_gun"] is None and q["en_iyi_R_pip"] is None
    assert q["en_iyi_R_pip_alt"] == 6.0 and q["en_iyi_R_pip_ust"] == 30.0
    assert q["r_tek_haric"] == pytest.approx(np.delete(r, 0).mean())
    tek = isl.copy()
    tek.loc[2, "r"] = 1.9
    tek.loc[4, "r"] = 1.8
    q1 = kosu.kuyruk(k, tek, 0.5)["tum"]
    assert q1["en_iyi_esit"] == 1 and q1["en_iyi_gun"] == str(gun[0])[:10] and q1["en_iyi_R_pip"] == 10.0


def test_yorum_duyarliligi_sentetik(tmp_path, monkeypatch):
    """Yorum duyarlılığı (kosu.YORUM): harfin okuması ızgarayı baştan koşar. ORB'de iki okuma tanım gereği aynıdır
    (sıfır değişen kombinasyon, aynı seçim, aynı hüküm); pivot kırılımında P satırları değişmez, değişen sayı
    ızgaranın R1S1 yarısını aşamaz. Hüküm alanları birincil hükmün kuralıyla kurulur."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ayar as ay
    from gunluk import baglam_kur
    from sentetik import dakika_uret, olaylar_uret
    monkeypatch.setattr(kosu, "CIKTI", tmp_path)
    olay = olaylar_uret()
    b = baglam_kur(dakika_uret(soklar=olay["utc_sn"].to_numpy()), olay)
    k = kosu.Kosucu(b, ay.oku())
    s = kosu.birim_kos("sahte_orb", k)
    assert set(s["yorum"]) == {param for param, _ in kosu.YORUM["sahte_orb"]}
    y = s["yorum"]["acilis"]
    assert (y["param"], y["olcum"], y["harf"]) == ("acilis", "kesis", "acilis_ici")
    assert y["degisen"] == 0 and y["varsayilan_degisti"] is False and y["secim_ayni"] is True
    assert y["kombinasyon"] == s["kombinasyon"]
    assert y["varsayilan"]["oos"]["hukum"] == s["varsayilan_analiz"]["hukum"]
    assert y["varsayilan"]["tum"]["hukum"] == s["varsayilan_analiz"]["hukum_tum"]
    assert y["varsayilan"]["oos"]["ozet"]["beklenti_r"] == pytest.approx(s["varsayilan_analiz"]["oos"]["beklenti_r"])
    # Her okuma ayrı bir kayıttır ve öbür okuma ölçümün kuralında kalır: dönüş okumasının kaydı kendi parametresini taşır.
    yd = s["yorum"]["donus"]
    assert (yd["param"], yd["olcum"], yd["harf"]) == ("donus", "tek_kenar", "iki_kenar")
    assert yd["kombinasyon"] == s["kombinasyon"] and 0 <= yd["degisen"] <= yd["kombinasyon"]
    with pytest.raises(ValueError):
        kosu.yorum_duyarlilik("sahte_orb", "sahte", "donus", "bilinmeyen", {}, [], None, k, 20)
    p = kosu.birim_kos("pivot_kirilim", k)
    yp = p["yorum"]["kesis"]
    liste, _ = kosu.izgara("pivot_kirilim")
    r1s1 = sum(1 for q in liste if q["seviye"] == "R1S1")
    assert 0 < yp["degisen"] <= r1s1
    for d in ("oos", "tum"):
        assert yp["varsayilan"][d]["hukum"] in ("calisiyor", "zayif", "calismiyor", "olculemedi")
    assert kosu.birim_kos("orb", k).get("yorum") is None


def test_ornek_cizgisi_kuralin_kendi_gostergesi():
    """Örnek günün çizgisi kuralın kendi tanımından gelir: sıkışmada strateji.sikisma_bantlari, VWAP kurallarında
    strateji._vwap_mum (dönüşte ± k·σ). Uzunluk mumlarınkiyle aynı; tanımsız değer None; öbür kurallar çizgi taşımaz."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ayar as ay
    import strateji as st
    from gunluk import baglam_kur
    from sentetik import dakika_uret, olaylar_uret
    olay = olaylar_uret()
    b = baglam_kur(dakika_uret(soklar=olay["utc_sn"].to_numpy()), olay)
    k = kosu.Kosucu(b, ay.oku())
    m = b.mumlar(15, 0)
    j0, j1 = 30, 30 + 96
    c = kosu._ornek_cizgi(k, "sikisma", {"tf": 15}, m, j0, j1)
    bt = st.sikisma_bantlari(m)
    assert c["tur"] == "sikisma" and len(c["bb_ust"]) == j1 - j0 == len(c["sikisma"])
    assert c["sikisma"] == [bool(x) for x in bt["sikisma"][j0:j1]]
    for i, (u, a, ku, ka) in enumerate(zip(c["bb_ust"], c["bb_alt"], c["kc_ust"], c["kc_alt"])):
        if None not in (u, a, ku, ka) and c["sikisma"][i]:
            assert u < ku + 0.1 and a > ka - 0.1           # yuvarlama payı: 0,1 nokta
    ilk = kosu._ornek_cizgi(k, "sikisma", {"tf": 15}, m, 0, 25)
    assert all(x is None for x in ilk["bb_ust"][:19])      # ilk 19 mumda 20 mumluk ortalama tanımsız
    for birim in ("vwap_donus", "vwap_cekilme"):
        p = {"tf": 15, "capa": "londra", "k": 2.0}
        v = kosu._ornek_cizgi(k, birim, p, m, j0, j1)
        _, _, vwb, sgb, _, _ = st._vwap_mum(b, 15, "londra")
        assert v["tur"] == birim and len(v["vwap"]) == j1 - j0
        assert v["vwap"] == [kosu._sayi(x) for x in vwb[j0:j1]]
        assert ("bant_ust" in v) == (birim == "vwap_donus")
        if birim == "vwap_donus":
            assert v["bant_ust"] == [kosu._sayi(x) for x in (vwb + 2.0 * sgb)[j0:j1]]
    assert kosu._ornek_cizgi(k, "orb", {"tf": 15}, m, j0, j1) is None
    with pytest.raises(AssertionError):
        kosu._ornek_cizgi(k, "vwap_donus", {"tf": 15, "capa": "londra", "k": 2.0}, b.mumlar(5, 0), j0, j1)
