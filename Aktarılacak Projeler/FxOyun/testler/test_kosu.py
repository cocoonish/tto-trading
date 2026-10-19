"""Simülatörün dolum kuralları — sentetik dakikalarla."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import oyun_sim as kosu  # noqa: E402
from veri import Dakika  # noqa: E402

PIP = 10.0          # nokta / pip
YARIM = 1.0         # yarım makas (nokta): ask = mid + 1, bid = mid − 1


def dakikalar(yol):
    """yol: her dakika için (açılış, en yüksek, en düşük, kapanış) orta fiyat."""
    y = np.array(yol, float)
    n = len(y)
    t = np.arange(n, dtype=np.int64) * 60 + 1_700_000_000
    mo, mh, ml, mc = y.T
    return Dakika("EURUSD", 10, t, mo - YARIM, mh - YARIM, ml - YARIM, mc - YARIM,
                  mo + YARIM, mh + YARIM, ml + YARIM, mc + YARIM, mo, mh, ml, mc, np.ones(n),
                  np.array(["2020-01-01"] * n, dtype="datetime64[D]"))


def olay(d, h=1100.0, l=1000.0, o=1000.0, c=1090.0, yon=1):
    return {"cift": "EURUSD", "an": "londra_acilis", "t0": int(d.t[0]), "gun": "2020-01-01", "o": o, "h": h,
            "l": l, "c": c, "sinif": "guclu", "uyum": "yatay", "yon": yon, "j0": 0, "j1": len(d.t), "pip": PIP}


def test_limit_dolar_hedef_dolum_dakikasinda_sayilmaz():
    # orta = 1050. Dakika 0 1060'ta; dakika 1 1040'a iner (ask 1041 ≤ 1050 → dolar) ve aynı dakikada 1100'e çıkar.
    d = dakikalar([(1060, 1065, 1055, 1060), (1060, 1110, 1040, 1080), (1080, 1120, 1075, 1110)])
    x = kosu.simule(d, olay(d), kosu.Bacak("katil", "uc"), kayma_pip=0)
    assert x["neden"] == "hedef" and x["giris_dk"] == int(d.t[1]) and x["cikis_dk"] == int(d.t[2])


def test_ayni_dakikada_stop_ve_hedef_stop_sayilir():
    d = dakikalar([(1060, 1065, 1055, 1060), (1060, 1060, 1049, 1052), (1052, 1200, 900, 1000)])
    x = kosu.simule(d, olay(d), kosu.Bacak("katil", "uc"), kayma_pip=0)
    assert x["neden"] == "stop" and x["R"] < -0.9


def test_r_planlanan_riskle():
    # Stop = 1000 − 0,1 × 100 = 990; planlanan risk 60 nokta (1050'den). Bid 990'ın altında açılırsa (boşluk) çıkış
    # açılıştan, R planlanan riskle −1'den kötü olur.
    d = dakikalar([(1060, 1065, 1055, 1060), (1060, 1060, 1049, 1052), (900, 905, 895, 900)])
    x = kosu.simule(d, olay(d), kosu.Bacak("katil", "uc"), kayma_pip=0)
    assert x["neden"] == "stop" and abs(x["risk_pip"] - 6.0) < 1e-9 and x["R"] < -2


def test_dolmayan_limit_islem_degil():
    d = dakikalar([(1060, 1065, 1055, 1060)] * 5)
    assert kosu.simule(d, olay(d), kosu.Bacak("katil", "uc")) is None


def test_zaman_cikisi_ve_kayma():
    d = dakikalar([(1095, 1096, 1094, 1095)] * 3)
    x = kosu.simule(d, olay(d), kosu.Bacak("devam", 5.0), kayma_pip=0.5)
    assert x["neden"] == "zaman"
    # giriş ask açılış 1096 + 5, çıkış bid kapanış 1094 − 5 → −12 nokta
    risk = 1096 - 990
    assert abs(x["R"] - (-12 / risk)) < 1e-12


def test_kirilim_iki_uc_ayni_dakikada_islem_yok():
    d = dakikalar([(1050, 1200, 900, 1050)] * 3)
    e = olay(d, yon=0)
    assert kosu.simule(d, e, kosu.Bacak("kirilim", 1.0)) is None


def test_kirilim_brut_seviyeden_olculur():
    # Küçük mum 1000–1040 (boy 40 nokta = 4 pip, en az riskin üstünde). Dakika 1 1030'da açılıp 1041'e çıkar (kırılım),
    # dakika 2 hedefi geçer. Orta fiyattan maliyetsiz sonuç TAM hedef katıdır: giriş seviyeden (1040) sayılır, tetik
    # dakikasının açılışından (1030) değil.
    d = dakikalar([(1020, 1025, 1015, 1020), (1030, 1041, 1029, 1040), (1040, 1100, 1039, 1090)])
    e = {**olay(d, h=1040.0, l=1000.0, o=1020.0, c=1020.0, yon=0), "sinif": "kucuk"}
    b = kosu.Bacak("kirilim", 0.5)
    assert abs(kosu.brut(kosu.orta(d), e, b) - 0.5) < 1e-9
    x = kosu.simule(d, e, b, kayma_pip=0.5)
    assert x["R"] < 0.5                                   # gerçek işlem makas ve kayma öder
