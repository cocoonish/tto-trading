"""Büyük mum: ATR, olay tanımı ve giriş simülatörünün dolum kuralları — sentetik verilerle."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import buyuk_mum as bm  # noqa: E402
import buyuk_sim as bs  # noqa: E402
from veri import Dakika, Mumlar  # noqa: E402

PIP = 10.0
YARIM = 1.0
BOS = np.array([], np.int64)


def dakikalar(yol, t0=1_700_000_000):
    y = np.array(yol, float)
    n = len(y)
    t = np.arange(n, dtype=np.int64) * 60 + t0
    mo, mh, ml, mc = y.T
    return Dakika("EURUSD", 10, t, mo - YARIM, mh - YARIM, ml - YARIM, mc - YARIM,
                  mo + YARIM, mh + YARIM, ml + YARIM, mc + YARIM, mo, mh, ml, mc, np.ones(n),
                  np.array(["2020-01-01"] * n, dtype="datetime64[D]"))


def olay(d, h=1100.0, l=1000.0, o=1005.0, c=1090.0, yon=1, A=40.0, tf=5):
    # Mum, dakika 0'dan önce kapanmış sayılır: bt = t0 − tf·60; izleme dakika 0'da başlar.
    return {"cift": "EURUSD", "tf": tf, "bt": int(d.t[0]) - tf * 60, "o": o, "h": h, "l": l, "c": c, "A": A,
            "yon": yon, "j0": 0, "j1": len(d.t), "i_son": 0, "pip": PIP}


def _mumlar(bt, h, l, c):
    n = len(bt)
    return Mumlar(5, 0, bt, c.copy(), h, l, c, np.full(n, 5), np.arange(n), np.arange(n), np.zeros(n, "datetime64[D]"))


def test_atr_wilder_ve_bosluk():
    n = 20
    h, l, c = np.full(n, 110.0), np.full(n, 100.0), np.full(n, 105.0)
    c[14] = 300.0                                      # 15. mumdan önce kapanış çok uzakta
    bitisik = np.arange(n, dtype=np.int64) * 300
    a = bm.atr(_mumlar(bitisik, h, l, c))
    assert np.isnan(a[12]) and a[13] == 10.0 and a[14] == 10.0
    # bitişik: 15. mumun gerçek aralığı 300 − 100 = 200 → Wilder: 10 + (200 − 10) / 14
    assert abs(a[15] - (10 + 190 / 14)) < 1e-12
    bosluklu = bitisik.copy()
    bosluklu[15:] += 3600                              # boşluk: gerçek aralık mumun kendi aralığı (10)
    a2 = bm.atr(_mumlar(bosluklu, h, l, c))
    assert a2[15] == 10.0


def test_yol_simetrik_ve_ayna():
    # Boğa mumu, kapanış 1090, A = 40. Yol önce 1130'a (+1A) çıkıyor, sonra 1050'ye iniyor.
    d = dakikalar([(1090, 1100, 1085, 1095), (1095, 1131, 1094, 1120), (1120, 1121, 1049, 1050)] + [(1050,) * 4] * 30)
    e = olay(d)
    g, y = bm.olc(d, e)
    assert g["sim_1.0"] == 1.0 and y["sim_1.0"] == 0.0
    assert g["uc_asma"] and g["geri_0.5"]               # 1050 = ucun 0,5 R altı
    assert not g["geri_1.0"]


def test_limit_devam_kapanis_zaten_geride_ise_emir_yok():
    d = dakikalar([(1040, 1045, 1035, 1040)] * 10)
    e = olay(d, c=1040.0)                               # kapanış 1040 < %50 seviyesi 1050
    assert bs.emir(d, e, bs.Giris("devam", "limit_0.5", 1.0, 1.0)) is None
    assert bs.emir(d, e, bs.Giris("devam", "limit_0.62", 1.0, 1.0)) is not None   # 1038 < 1040


def test_limit_devam_dolar_hedef_dolum_dakikasinda_sayilmaz():
    # %50 seviyesi 1050; dakika 1 1049'a iner (ask 1050 ≤ 1050) ve aynı dakikada 1100'e çıkar → hedef sayılmaz.
    d = dakikalar([(1080, 1085, 1075, 1080), (1080, 1100, 1049, 1090), (1090, 1100, 1089, 1095)] + [(1095,) * 4] * 30)
    x = bs.simule(d, olay(d), bs.Giris("devam", "limit_0.5", 1.0, 1.0), BOS, kayma_pip=0)
    assert x["giris_dk"] == int(d.t[1]) and x["neden"] == "hedef" and x["cikis_dk"] == int(d.t[2])
    # hedef = 1050 + 40 = 1090: dakika 2'nin bid yükseği 1099 ≥ 1090


def test_ters_limit_uc_ve_ayni_dakika_stop():
    # Boğa mumunu ucunda (1100) sat; stop 1100 + 40 = 1140. Aynı dakikada hem 1141 hem 1060 → stop.
    d = dakikalar([(1095, 1102, 1094, 1100), (1100, 1142, 1059, 1100)] + [(1100,) * 4] * 30)
    x = bs.simule(d, olay(d), bs.Giris("ters", "limit_uc", 1.0, 1.0), BOS, kayma_pip=0)
    assert x["giris_dk"] == int(d.t[0]) and x["neden"] == "stop"


def test_onayli_sonraki_mum_tersse_emir_yok():
    # tf = 5: sonraki mum dakika 0–4; kapanışı 1080 < 1090 → devam onaylı emir yok, ters onaylı var.
    d = dakikalar([(1090, 1092, 1078, 1080)] * 5 + [(1080,) * 4] * 30)
    e = olay(d)
    assert bs.emir(d, e, bs.Giris("devam", "onayli", 1.0, 1.0)) is None
    em = bs.emir(d, e, bs.Giris("ters", "onayli", 1.0, 1.0))
    assert em["j_bas"] == 5 and em["s"] == -1


def test_piyasa_kayma_ve_haber_kaymasi():
    d = dakikalar([(1090, 1091, 1089, 1090)] * 40)
    e = olay(d)
    g = bs.Giris("devam", "piyasa", 1.0, 5.0)
    x0 = bs.simule(d, e, g, BOS, kayma_pip=0.5, haber_kayma_pip=1.0)
    x1 = bs.simule(d, e, g, np.array([int(d.t[0])], np.int64), kayma_pip=0.5, haber_kayma_pip=1.0)
    # haber penceresinde giriş 1 pip (10 nokta) daha kötü; çıkış penceresin sonunda (haberden 39 dk sonra) değil
    assert abs((x0["R"] - x1["R"]) * 40.0 - 10.0) < 1e-9


def test_en_az_risk():
    d = dakikalar([(1090, 1091, 1089, 1090)] * 40)
    assert bs.simule(d, olay(d, A=2.0), bs.Giris("devam", "piyasa", 1.0, 1.0), BOS) is None


def test_stop_girisi_dolum_dakikasinda_dolumdan_onceki_fiyatla_stop_yazilmaz():
    # Boğa mumu (1000–1100, kapanış 1090, orta 1050), A = 30. "Tersine stop" satışı ortada (1050); koruyucu stop
    # 1050 + 30 = 1080 kapanışın altında. Dakika 3 1088'den 1049'a iner ve 1050'de kapanır: önce stop bölgesindeydi,
    # sonra satış tetiklendi; dolumdan sonra 1080'e hiç dönülmedi → stop sayılmaz.
    d = dakikalar([(1090, 1092, 1088, 1090)] * 3 + [(1088, 1089, 1049, 1050)] + [(1050, 1052, 1048, 1050)] * 40)
    e = olay(d, A=30.0)
    x = bs.simule(d, e, bs.Giris("ters", "stop", 1.0, 1.0), BOS, kayma_pip=0, haber_kayma_pip=0)
    assert x["giris_dk"] == int(d.t[3]) and x["neden"] == "zaman"
    assert x["R"] > -1.0
    # Dolum dakikası stopun ötesinde kapanırsa (dolumdan sonra stopa dönülmüş) stop o dakikada, stop seviyesinden.
    d2 = dakikalar([(1090, 1092, 1088, 1090)] * 3 + [(1060, 1090, 1049, 1085)] + [(1085,) * 4] * 40)
    x2 = bs.simule(d2, e, bs.Giris("ters", "stop", 1.0, 1.0), BOS, kayma_pip=0, haber_kayma_pip=0)
    assert x2["neden"] == "stop" and x2["cikis_dk"] == x2["giris_dk"]
    assert abs(x2["R"] + 1.0) < 1e-9                    # giriş 1050, çıkış 1080: tam −1 R
