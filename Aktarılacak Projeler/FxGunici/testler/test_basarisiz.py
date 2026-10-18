# -*- coding: utf-8 -*-
"""Dokuzuncu dersin ölçüleri (basarisiz.py) ve ay sonunun eski tanımı (ders_olcum).

Her ölçü ders metninin bir cümlesinin tek tanımıdır. Girdiler sentetik ve küçük; beklenen sonuç elle sayılabilir ya
da bir özdeşlikten gelir (başabaş, ayrışım), ya da bilinen bir kapalı biçimden (gereken işlem sayısı).
"""
from __future__ import annotations

import json
import math
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import basarisiz as bs  # noqa: E402
import ders_olcum as do  # noqa: E402
import karsi_olgu as ko  # noqa: E402
import metrik as mk  # noqa: E402
import zaman as z  # noqa: E402


# ─────────────────────────────────────────────── başabaş özdeşliği
def test_isabet_ozdesligi_ve_sifir_kayiptir():
    r = np.array([2.0, -1.0, 0.0, 0.5, -1.0, 3.0])
    p, w, l, ps = bs._isabet(r)
    assert p == pytest.approx(3 / 6)                                  # sıfır sonuç kayıp sayılır
    assert w == pytest.approx((2.0 + 0.5 + 3.0) / 3) and l == pytest.approx(-2.0 / 3)
    assert ps == pytest.approx(abs(l) / (w + abs(l)))
    assert (p - ps) * (w + abs(l)) == pytest.approx(r.mean())          # E = (p − p*)(W̄ + |L̄|)


# ─────────────────────────────────────────────── ayrışım
def _sonuc(net, brut, makas, kayma0, ayna, ort, n=100):
    pen = {"n": n, "beklenti_r": net, "brut_r": brut, "beklenti_pip": net * 10, "brut_pip": brut * 10}
    return {"varsayilan_analiz": {
        "oos": pen, "tum": pen,
        "yalniz_makas": {"oos": {"beklenti_r": makas, "beklenti_pip": makas * 10},
                         "tum": {"beklenti_r": makas, "beklenti_pip": makas * 10}},
        "maliyet": {"0.0": {"oos": {"beklenti_r": kayma0}, "tum": {"beklenti_r": kayma0}}},
        "rastgele": {"oos": {"ters_ort": ayna, "ort": ort, "yuzdelik": 50.0},
                     "tum": {"ters_ort": ayna, "ort": ort, "yuzdelik": 50.0}}}}


def test_ayrisim_ozdesligi_ve_iki_maliyet():
    # y = 0,02, z = 0,03, c = 0,15 (makas 0,05 + kayma 0,10) → net = −0,10, ayna = −0,14
    s = {("a", "EURUSD"): _sonuc(-0.10, 0.05, 0.0, -0.02, -0.14, -0.12)}
    o = bs.ayrisim(s, {"a": {}})["oos"]
    assert o["ort"]["y"] == pytest.approx(0.02) and o["ort"]["z"] == pytest.approx(0.03)
    assert o["ort"]["c"] == pytest.approx(0.15)
    assert o["ort"]["c_makas"] == pytest.approx(0.05) and o["ort"]["c_kayma"] == pytest.approx(0.10)
    assert o["ic_tutarlilik"] == pytest.approx(0.0)                   # ort = (net + ayna)/2
    assert o["ayna_eksi"] == 1 and o["birlikte_eksi"] == 1 and o["yz_c"] == 0
    assert o["duyarlilik"]["yalniz_makas"] == 0 and o["duyarlilik"]["temel"] == 0


def test_ayrisim_aynasiz_bilesim_disarida_ve_adiyla():
    s = {("a", "EURUSD"): _sonuc(-0.1, 0.05, 0.0, -0.02, None, None),
         ("b", "EURUSD"): _sonuc(0.02, 0.10, 0.06, 0.05, -0.06, -0.02)}
    o = bs.ayrisim(s, {"a": {}, "b": {}})["oos"]
    assert o["bilesim"] == 1 and o["dislanan"] == ["a:EURUSD"]
    assert o["net_arti"] == 1 and o["yz_c"] == 1                      # y + z > c ⇔ net > 0 (tanım)
    assert o["duyarlilik"]["bilesim"] == 2 and o["duyarlilik"]["yalniz_makas"] == 1


# ─────────────────────────────────────────────── şans
def test_poisson_binom_toplam_ve_ortalama():
    p = np.array([0.1, 0.5, 0.25, 0.9])
    d = bs._poisson_binom(p)
    assert d.sum() == pytest.approx(1.0)
    assert (np.arange(len(d)) * d).sum() == pytest.approx(p.sum())
    assert d[0] == pytest.approx(np.prod(1 - p))


def test_kenarsiz_taban_belirlenimci_ve_sinirli():
    a = bs.kenarsiz_taban(sigma=(1, 2), yol=2000, adim=100, tohum=3)
    b = bs.kenarsiz_taban(sigma=(1, 2), yol=2000, adim=100, tohum=3)
    assert a == b
    for x in a["sigma"]:
        assert 0 < x["lehine"] < 1 and 0 <= x["ulasip_zarar"] < 1
    assert a["sigma"][1]["ulasip_zarar"] > a["sigma"][0]["ulasip_zarar"]   # ufuk uzadıkça geri verme artar


# ─────────────────────────────────────────────── güç
def test_gereken_islem_sayisi_kapali_bicim():
    z = 1.6448536269514722 + 0.8416212335729143
    assert bs._n_gerek(0.3, 1.2, 0.05) == pytest.approx((z * 1.2 / 0.3) ** 2)
    assert bs._gucu(0.3, 1.2, bs._n_gerek(0.3, 1.2, 0.05)) == pytest.approx(0.80, abs=1e-9)


def test_bakislar_bos_varsayimda_duzey():
    b = bs.bakislar({"etki": 0.3}, 1.2, 12, yol=40000, tohum=5)
    assert abs(b["bos"] - 0.05) < 0.006                               # sınır sabiti boşta %5 verecek biçimde
    assert b["sinir"][0] > b["sinir"][-1]                             # erken bakışta sıkı, sonda gevşek
    assert b["guc"]["etki"] < b["sabit_ufuk"]["etki"] + 0.03          # bakış bedeli gücü artırmaz


# ─────────────────────────────────────────────── işlem dosyasının özeti
def _islem(gunler, r):
    n = len(gunler)
    return pd.DataFrame({"gun": pd.to_datetime(gunler).astype("datetime64[ms]"), "r": r, "r_brut": np.array(r) + 0.1,
                         "pnl_pip": np.array(r) * 10, "brut_pip": np.array(r) * 10 + 1, "R_pip": np.full(n, 10.0),
                         "mfe_r": np.abs(r), "yon": np.ones(n, int), "giris_t": np.arange(n), "cikis_t": np.arange(n) + 1,
                         "durum": np.zeros(n, int)})


def _ozet(x):
    return {"n": len(x), "beklenti_r": float(np.mean(x["r"])) if len(x) else None,
            "brut_r": float(np.mean(x["r_brut"])) if len(x) else None}


def test_islemler_sonuc_ozetini_sinar(tmp_path):
    x = _islem(["2023-12-28", "2023-12-29", "2024-01-02"], [1.0, -1.0, 0.5])
    yol = tmp_path / "a.parquet"
    x.to_parquet(yol)
    ozet = {"is": _ozet(x.iloc[:2]), "oos": _ozet(x.iloc[2:]), "tum": _ozet(x)}
    s = {("a", "EURUSD"): {"varsayilan": {"tf": 5}, "varsayilan_analiz": ozet}}
    t = bs.islemler(tmp_path, s, lambda *_: yol, date(2023, 12, 31))
    assert list(t["pen"]) == ["is", "is", "oos"]
    ozet["oos"] = {"n": 1, "beklenti_r": 0.4, "brut_r": 0.6}          # dosya bu özeti üretmez
    with pytest.raises(ValueError):
        bs.islemler(tmp_path, s, lambda *_: yol, date(2023, 12, 31))


# ─────────────────────────────────────────────── ay sonunun eski tanımı
def test_ay_sonu_eski_tatilin_kendisini_bugunku_bir_onceki_gunu_isaretler():
    # Mart 2024: 29.03 cuma İngiltere'de tatil (Kutsal Cuma). Eski tanım 29.03'ü, bugünkü 28.03'ü işaretler.
    assert do.ay_sonu_eski(date(2024, 3, 29)) and not do.ay_sonu_eski(date(2024, 3, 28))
    assert z.londra_ay_sonu(date(2024, 3, 28)) and not z.londra_ay_sonu(date(2024, 3, 29))
    assert do.ay_sonu_eski(date(2024, 4, 30)) and z.londra_ay_sonu(date(2024, 4, 30))
    assert not do.ay_sonu_eski(date(2024, 3, 30))                     # hafta sonu


def test_ay_sonu_eski_yamanin_eski_metniyle_ayni():
    """Eski tanım, karşı olgu yamasının ESKİ metninin kendisiyle (günlük dizinin sırası, son eleman hariç) aynı
    günleri verir: tam hafta içi dizide ve ay_sonu_kayan'ın aylarıyla."""
    yama = next(x for x in ko.DEGISIKLIKLER if x["ad"] == "ay_sonu")["yama"][0][2]
    gun = np.array(pd.bdate_range("2018-01-01", "2026-10-16").date, dtype="datetime64[D]")
    kapsam = {"np": np, "gun": gun}
    exec(textwrap.dedent(yama), kapsam)
    eski = kapsam["ay_sonu"]
    g = [x.astype(date) for x in gun]
    beklenen = np.array([do.ay_sonu_eski(x) for x in g], dtype=bool)
    assert (eski[:-1] == beklenen[:-1]).all() and not eski[-1]
    ayrisan = sorted({f"{x.year:04d}-{x.month:02d}" for x, e in zip(g, beklenen) if e and not z.londra_ay_sonu(x)})
    assert ayrisan == do.ay_sonu_kayan(date(2018, 1, 1), date(2026, 10, 15))


def test_ay_sonu_sart_iki_ayrik_pencere():
    def ayrim(oa, op, ia, ip):
        return {"ay_sonu": {"oos": {"ga_alt": oa, "beklenti_r": 0.1}, "is": {"ga_alt": ia, "beklenti_r": 0.1}},
                "fark": {"oos": {"p": op}, "is": {"p": ip}}}
    assert do.ay_sonu_sart(ayrim(0.01, 0.001, 0.02, 0.001), 0.0018)[1]
    assert not do.ay_sonu_sart(ayrim(0.01, 0.001, -0.02, 0.001), 0.0018)[1]   # örneklem içi alt uç eksi
    assert not do.ay_sonu_sart(ayrim(0.01, 0.01, 0.02, 0.001), 0.0018)[1]     # fark eşiği aşmıyor
    s, _ = do.ay_sonu_sart(ayrim(0.01, 0.001, 0.02, 0.001), None)
    assert not s["oos"]["fark_esik"]                                          # eşik yoksa şart sağlanmaz


def test_ay_sonu_eski_tanim_kayitli_ayrimi_sinar(tmp_path):
    import kosu
    gunler, r = [], []
    g = date(2023, 3, 1)
    rng = np.random.default_rng(1)
    while g <= date(2024, 4, 30):
        if g.weekday() < 5:
            gunler.append(g)
            r.append(float(rng.normal(0.0, 1.0)))
        g += timedelta(days=1)
    x = _islem([d.isoformat() for d in gunler], r)
    x["ay_sonu"] = [z.londra_ay_sonu(d) for d in gunler]
    (tmp_path / "islem" / "fiks_momentum").mkdir(parents=True)
    p = {"tf": 5}
    yol = do._islem_dosyasi(tmp_path, "fiks_momentum", "GBPUSD", p)
    x.to_parquet(yol)
    icm = x["gun"].to_numpy().astype("datetime64[D]") <= np.datetime64(date(2023, 12, 31))
    kayit = kosu.ay_sonu_ayrimi(mk.alinan(x), icm)
    birimler = {"fiks_momentum": {"cift": {"GBPUSD": {"varsayilan": {"ay_sonu": kayit}}}}}
    aile = {"esik": 0.05, "uye": [{"birim": "fiks_momentum", "cift": "GBPUSD", "kim": "varsayilan", "p": p,
                                   "tutar": False},
                                  {"birim": "fiks_momentum", "cift": "GBPUSD", "kim": "tf15", "p": p, "tutar": False}]}
    o = do.ay_sonu_eski_tanim(tmp_path, aile, birimler, date(2023, 12, 31), do.ay_sonu_kayan(date(2023, 1, 1),
                                                                                             date(2024, 4, 30)))
    assert o["olculen"] == 1 and o["olculemedi"] == 1
    u = o["uye"][0]
    # Pencerede tek kayan ay Mart 2024: eski tanım 29.03'ü (Kutsal Cuma), bugünkü tanım 28.03'ü işaretler.
    assert [(d["gun"], d["tanim"]) for d in u["degisen"]] == [("2024-03-28", "bugun"), ("2024-03-29", "eski")]
    assert u["ay_sonu"]["oos"]["n"] == kayit["ay_sonu"]["oos"]["n"]          # küme boyu değişmez
    # kayıtlı ayrım dosyayla ayrışırsa ölçüm yazılmaz
    birimler["fiks_momentum"]["cift"]["GBPUSD"]["varsayilan"]["ay_sonu"]["ay_sonu"]["oos"]["beklenti_r"] += 0.1
    with pytest.raises(ValueError):
        do.ay_sonu_eski_tanim(tmp_path, aile, birimler, date(2023, 12, 31), do.ay_sonu_kayan(date(2023, 1, 1),
                                                                                             date(2024, 4, 30)))


# ─────────────────────────────────────────────── tuzak payları
def test_tuzak_paylari_kaybedenler_ve_hedefe_ulasanlar():
    x = _islem(["2024-01-02"] * 6, [-1.0, -1.0, 0.0, 0.8, -0.2, 1.5])
    x["mfe_r"] = [0.6, 0.1, 0.5, 1.2, 1.0, 1.5]
    x["pen"], x["kural"], x["cift"] = "oos", "a", "EURUSD"
    x = pd.concat([x, x.assign(pen="is", mfe_r=0.0)], ignore_index=True)   # tuzak payları yalnız örneklem dışından
    tz = bs.basabas(x, {"a": {}}, {})["tuzak"]
    # kaybedenler (sonuç ≤ 0): −1 (0,6), −1 (0,1), 0 (0,5), −0,2 (1,0) → üçü +0,5 R'ye değmiş
    assert tz["kural"]["a"]["kaybeden"] == 4 and tz["kural"]["a"]["lehine"] == pytest.approx(3 / 4)
    # +1 R'ye değenler: 0,8 (1,2), −0,2 (1,0), 1,5 (1,5) → biri zararla kapanmış
    assert tz["kural"]["a"]["ulasan"] == 3 and tz["kural"]["a"]["ulasip_zarar"] == pytest.approx(1 / 3)
    assert tz["esik"] == {"lehine": bs.TUZAK_LEHINE, "ulasma": bs.TUZAK_ULASMA}


# ─────────────────────────────────────────────── başabaş maliyeti
def _esik_islem(kural, cift, pen, r_brut, R_pip, maliyet_pip):
    r_brut, R_pip = np.asarray(r_brut, float), np.asarray(R_pip, float)
    brut_pip = r_brut * R_pip
    pnl = brut_pip - maliyet_pip
    n = len(r_brut)
    return pd.DataFrame({"kural": kural, "cift": cift, "pen": pen, "r_brut": r_brut, "R_pip": R_pip,
                         "brut_pip": brut_pip, "pnl_pip": pnl, "r": pnl / R_pip, "yon": np.ones(n, int),
                         "giris_t": np.arange(n) * 10, "cikis_t": np.arange(n) * 10 + 5})


def test_esik_basabas_maliyeti_ve_ozet_sayimlari():
    t = pd.concat([
        # c* = ort(r_brüt) / ort(1/R_pip) = 0,1 / 0,1125 = 0,889 pip; ödenen 1 pip → ödenenin altında
        _esik_islem("orb", "EURUSD", "oos", [0.3, -0.1, 0.2, 0.0], [10, 5, 20, 10], 1.0),
        _esik_islem("b", "EURUSD", "oos", [-0.2, 0.1], [10, 10], 1.0),     # brüt eksi → c* ≤ 0
        _esik_islem("c", "EURUSD", "oos", [0.5, 0.5], [10, 10], 1.0),      # c* = 5 pip > ödenen 1 pip
        _esik_islem("orb", "EURUSD", "is", [0.1, 0.1], [10, 10], 0.5),
        _esik_islem("b", "EURUSD", "is", [0.1], [10], 0.5),
        _esik_islem("c", "EURUSD", "is", [0.1], [10], 0.5),
    ], ignore_index=True)
    alt = {"orb": -0.05, "b": -0.3, "c": 0.2}

    def havuz(b):
        return {d: {"ga_brut_alt": alt[b], "ga_brut_ust": 0.5} for d in ("oos", "tum")}
    birimler = {b: {"havuz": {"varsayilan": havuz(b)}} for b in ("orb", "b", "c")}

    def analiz(b):
        out = {}
        for d in ("oos", "tum"):
            y = t[t["kural"] == b] if d == "tum" else t[(t["kural"] == b) & (t["pen"] == d)]
            out[d] = {"brut_r": float(y["r_brut"].mean()), "beklenti_r": float(y["r"].mean()),
                      "brut_pip": float(y["brut_pip"].mean())}
        return out
    sonuclar = {(b, "EURUSD"): {"varsayilan_analiz": analiz(b)} for b in ("orb", "b", "c")}
    sonuclar[("orb", "EURUSD")]["varsayilan_analiz"]["yalniz_makas"] = {"oos": {"beklenti_pip": 0.25}}
    sonuclar[("orb", "EURUSD")]["varsayilan_analiz"]["basabas_kayma_pip_oos"] = 0.1
    o = bs.esik(t, birimler, sonuclar, {"EURUSD": {"makas": {"medyan_pip": 0.2}}})
    h = o["havuz"]["oos"]
    assert h["orb"]["cstar"] == pytest.approx(0.1 / 0.1125, abs=1e-6) and h["orb"]["odenen"] == pytest.approx(1.0)
    assert h["c"]["cstar"] == pytest.approx(5.0)
    oz = o["ozet"]["oos"]
    assert oz["sifir_alti"] == ["b"] and oz["sifir_alti_n"] == 1
    assert oz["ustu"] == ["c"] and oz["ustu_n"] == 1                    # c* > ödenen ⇔ ortalama net pip artı
    assert oz["alt_arti"] == ["c"] and oz["alt_arti_n"] == 1
    assert o["merdiven"]["cstar"] == pytest.approx(h["orb"]["cstar"])   # aynı tanım, aynı işlemler
    mak = sonuclar[("orb", "EURUSD")]["varsayilan_analiz"]["oos"]["brut_pip"] - 0.25
    assert o["merdiven"]["toplam"] == pytest.approx(mak + 2 * 0.1)
    assert o["lambda"]["oos"]["kat"]["0.0"] == 2                         # maliyetsiz: brütü artı iki bileşim


# ─────────────────────────────────────────────── kenar: yıl hücreleri ve seçilenlerin büzülmesi
def _kenar_islem():
    """Beş bileşim, dokuz yıl (2018–2026; 2024 → örneklem dışı), yılda 10 işlem (e'nin örneklem dışında 4). Bir yılın
    işlemleri ort ± 0,5 (simetrik): yıl ortalaması tam istenen değer. Brütü artı yıl sayısı a 9, b 6, c 0, d 7, e 9."""
    isaret = {"a": {}, "b": {2019: -1, 2021: -1, 2025: -1}, "c": None, "d": {2020: -1, 2024: -1}, "e": {}}
    buyukluk = {"a": 0.3, "b": 0.1, "c": -0.05, "d": 0.05, "e": 0.02}
    satir = []
    for k in "abcde":
        for yil in range(2018, 2027):
            n = 4 if (k == "e" and yil >= 2024) else 10
            m = buyukluk[k] if isaret[k] is None else buyukluk[k] * isaret[k].get(yil, 1)
            for i in range(n):
                rb = m + (0.5 if i % 2 else -0.5)
                satir.append({"kural": k, "cift": "EURUSD", "gun": pd.Timestamp(yil, 3, 1 + i),
                              "pen": "is" if yil <= 2023 else "oos", "r_brut": rb, "r": rb - 0.1})
    return pd.DataFrame(satir)


def test_kenar_yil_esigi_ve_secilenlerin_ongorusu():
    t = _kenar_islem()
    birimler = {k: {"havuz": {"varsayilan": {d: {"beklenti_r": float(bs._pencere(t[t["kural"] == k], d)["r"].mean()),
                                                 "brut_r": float(bs._pencere(t[t["kural"] == k], d)["r_brut"].mean())}
                                             for d in bs.PEN}}} for k in "abcde"}
    sonuclar = {(k, "EURUSD"): {"varsayilan_analiz": {d: {"ga_brut_alt": 0.1 if k == "a" else -0.1,
                                                          "beklenti_r": birimler[k]["havuz"]["varsayilan"][d]["beklenti_r"]}
                                                      for d in ("oos", "tum")}} for k in "abcde"}
    o = bs.kenar(t, birimler, sonuclar)
    y = o["yil"]
    assert y["yil"] == 9 and y["esik"] == bs.YIL_ESIK == 7
    assert y["brut_yedi"] == 3                                          # a (9), d (7), e (9)
    assert y["beklenen_yari"] == pytest.approx(5 * (36 + 9 + 1) / 512)  # 5 × P(Binom(9; 0,5) ≥ 7)
    assert o["dislanan"] == ["e:EURUSD"]                                # örneklem dışında 12 < 20 işlem
    s = o["is_anlamli"]
    assert s["bilesim"] == 1 and s["is"] == pytest.approx(0.3) and s["oos"] == pytest.approx(0.3)
    # büzülme öngörüsü: μ + ρ(seçilenlerin ortalaması − μ); μ ve ρ ayrışımın dışarıda bıraktığı e'siz kümeden
    ic = t[t["pen"] == "is"].groupby("kural")["r_brut"].agg(["mean", "std", "size"]).drop("e")
    mu = float(ic["mean"].mean())
    se2 = float(((ic["std"] / np.sqrt(ic["size"])) ** 2).mean())
    rho = (float(ic["mean"].var(ddof=1)) - se2) / float(ic["mean"].var(ddof=1))
    assert s["mu_is"] == pytest.approx(mu, abs=1e-6) and s["rho_is"] == pytest.approx(rho, abs=1e-6)
    assert s["ongoru"] == pytest.approx(mu + rho * (0.3 - mu), abs=1e-6)
    assert min(mu, 0.3) <= s["ongoru"] <= max(mu, 0.3)                  # 0 ≤ ρ ≤ 1: öngörü iki uç arasında
    a_oos = t[(t["kural"] == "a") & (t["pen"] == "oos")]["r_brut"]
    se_oos = float(a_oos.std() / np.sqrt(len(a_oos)))
    assert s["oos_se"] == pytest.approx(se_oos, abs=1e-6)
    assert s["ongoru_z"] == pytest.approx((0.3 - s["ongoru"]) / se_oos, abs=1e-4)
    assert o["brut_aralik"]["oos"]["brut_alt_arti"] == 1 and o["brut_aralik"]["oos"]["net_eksi"] == 0
