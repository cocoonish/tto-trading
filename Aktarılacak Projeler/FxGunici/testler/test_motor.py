# -*- coding: utf-8 -*-
"""İşlem motorunun birim testleri — elle kurulmuş dakikalarla, her kural ayrı ayrı."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import motor as mt  # noqa: E402
from veri import Dakika  # noqa: E402

MAKAS = 2.0  # nokta


def dakikalar(mid: list[tuple[float, float, float, float]], makas: float = MAKAS) -> Dakika:
    """mid (o, h, l, c) listesinden bid/ask dakikaları (sabit makas)."""
    m = np.array(mid, dtype=np.float64)
    o, h, l, c = m.T
    yari = makas / 2
    t = 1_700_000_000 + 60 * np.arange(len(m), dtype=np.int64)
    return Dakika("TEST", 10, t, o - yari, h - yari, l - yari, c - yari, o + yari, h + yari, l + yari, c + yari,
                  o, h, l, c, np.ones(len(m)), np.zeros(len(m), dtype="datetime64[D]"))


def emir(giris_i, yon, stop=np.nan, risk=np.nan, hedef_tur=0, k=0.0, seviye=np.nan, cikis_i=10, stop_tur=1, kimlik=0):
    e = mt.bos_emir(1)
    e[0] = (giris_i, yon, stop, risk, hedef_tur, k, seviye, cikis_i, stop_tur, kimlik)
    return e


def kos(d, e, bar_son=None, kayma=0.0, haber=None, haber_kayma=0.0):
    bar_son = np.ones(len(d), dtype=bool) if bar_son is None else bar_son
    return mt.simule(d, e, bar_son, haber=haber, kayma_pip=kayma, haber_kayma_pip=haber_kayma)


DUZ = [(100, 101, 99, 100)] * 3


def test_uzun_hedefe_ulasir_tam_1R():
    # giriş dakika 1 açılışı: ask = 101; stop 91 → R = 10; hedef 111 (bid ≥ 111 gerekir)
    d = dakikalar([(100, 100, 100, 100), (100, 102, 99, 101), (105, 109, 104, 108), (110, 113, 109, 112), (112, 112, 112, 112)])
    r = kos(d, emir(1, 1, stop=91.0, hedef_tur=mt.HEDEF_R, k=1.0, cikis_i=4))
    x = r.iloc[0]
    assert x.durum == 0 and x.giris_f == 101.0 and x.R == 10.0
    assert mt.NEDEN[x.neden] == "hedef" and x.cikis_f == 111.0 and abs(x.r - 1.0) < 1e-12


def test_uzun_stop_kayma_ile():
    d = dakikalar([(100, 100, 100, 100), (100, 100.5, 99.5, 100), (98, 98, 90, 91), (91, 91, 91, 91)])
    r = kos(d, emir(1, 1, stop=95.0, hedef_tur=mt.HEDEF_R, k=2.0, cikis_i=3), kayma=0.5)  # 0,5 pip = 5 nokta
    x = r.iloc[0]
    assert x.giris_f == 101.0 + 5.0                 # ask 101 + kayma
    assert mt.NEDEN[x.neden] == "stop" and x.cikis_f == 95.0 - 5.0
    assert x.pnl == (90.0 - 106.0)


def test_bosluk_stopun_otesinde_acilis():
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (90, 91, 89, 90), (90, 90, 90, 90)])
    x = kos(d, emir(1, 1, stop=95.0, hedef_tur=mt.HEDEF_R, k=1.0, cikis_i=3)).iloc[0]
    assert mt.NEDEN[x.neden] == "bosluk_stop" and x.cikis_f == 90.0 - 1.0   # bid açılışı


def test_ayni_dakika_stop_ve_hedef_stop_sayilir():
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (100, 130, 70, 100), (100, 100, 100, 100)])
    x = kos(d, emir(1, 1, stop=95.0, hedef_tur=mt.HEDEF_R, k=1.0, cikis_i=3)).iloc[0]
    assert mt.NEDEN[x.neden] == "stop" and bool(x.belirsiz)


def test_kapanis_stopu_sonraki_mum_acilisi():
    # stop 95; dakika 2 kapanışı 94 (mid) → dakika 3 açılışında bid'den çık
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (99, 99, 93, 94), (96, 96, 96, 96), (96, 96, 96, 96)])
    bar_son = np.array([False, False, True, False, True])
    x = kos(d, emir(1, 1, stop=95.0, cikis_i=4, stop_tur=mt.STOP_KAPANIS), bar_son=bar_son).iloc[0]
    assert mt.NEDEN[x.neden] == "kapanis_stop" and x.cikis_f == 96.0 - 1.0
    # aynı veri sert stop'la: dakika 2'de bid 92 ≤ 95 → stop seviyesinde çıkış
    x2 = kos(d, emir(1, 1, stop=95.0, cikis_i=4, stop_tur=mt.STOP_SERT)).iloc[0]
    assert mt.NEDEN[x2.neden] == "stop" and x2.cikis_f == 95.0


def test_zaman_cikisi_ve_kisa_yon():
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (97, 98, 96, 97), (95, 95, 95, 95)])
    x = kos(d, emir(1, -1, stop=110.0, cikis_i=3)).iloc[0]
    assert x.giris_f == 99.0                        # bid
    assert mt.NEDEN[x.neden] == "zaman" and x.cikis_f == 96.0   # ask açılışı (95 + 1)
    assert x.pnl == 3.0


def test_tek_pozisyon_ve_gecersiz_risk():
    d = dakikalar([(100, 100, 100, 100)] * 8)
    e = mt.bos_emir(3)
    e[0] = (1, 1, 90.0, np.nan, 0, 0.0, np.nan, 5, 1, 0)
    e[1] = (2, 1, 90.0, np.nan, 0, 0.0, np.nan, 6, 1, 1)     # pozisyon açıkken → alınmaz
    e[2] = (6, 1, 105.0, np.nan, 0, 0.0, np.nan, 7, 1, 2)    # giriş stop'un altında → R ≤ 0
    r = kos(d, e).set_index("kimlik")
    assert r.loc[0, "durum"] == 0 and mt.DURUM[r.loc[1, "durum"]] == "pozisyon_acik"
    assert mt.DURUM[r.loc[2, "durum"]] == "risk_gecersiz"


def test_zaman_cikisindan_sonra_ayni_dakikada_yeni_giris_alinir():
    d = dakikalar([(100, 100, 100, 100)] * 8)
    e = mt.bos_emir(2)
    e[0] = (1, 1, 90.0, np.nan, 0, 0.0, np.nan, 4, 1, 0)
    e[1] = (4, -1, 110.0, np.nan, 0, 0.0, np.nan, 6, 1, 1)
    r = kos(d, e).set_index("kimlik")
    assert (r["durum"] == 0).all()


def test_haber_kaymasi_yalniz_haber_dakikasinda():
    d = dakikalar([(100, 100, 100, 100)] * 5)
    haber = np.array([False, True, False, False, False])
    x = kos(d, emir(1, 1, stop=90.0, cikis_i=3), kayma=0.0, haber=haber, haber_kayma=1.0).iloc[0]
    assert x.giris_f == 101.0 + 10.0 and x.cikis_f == 99.0     # çıkış dakikası haber dışı


def test_brut_mid_ile_olculur():
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (104, 104, 104, 104)])
    x = kos(d, emir(1, 1, stop=90.0, cikis_i=2)).iloc[0]
    assert x.brut == 4.0 and x.pnl == 4.0 - MAKAS


def test_stopsuz_risk_birimi_ile():
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (106, 106, 106, 106)])
    x = kos(d, emir(1, 1, risk=20.0, cikis_i=2, stop_tur=mt.STOP_YOK)).iloc[0]
    assert x.R == 20.0 and x.pnl == 4.0 and abs(x.r - 0.2) < 1e-12


def test_seviye_hedefi_yanlis_taraftaysa_islem_yok():
    d = dakikalar([(100, 100, 100, 100)] * 4)
    x = kos(d, emir(1, 1, stop=90.0, hedef_tur=mt.HEDEF_SEVIYE, seviye=99.0, cikis_i=3)).iloc[0]
    assert mt.DURUM[x.durum] == "hedef_gecersiz"


def test_risk_verilip_seviye_verilmezse_stop_yurutulen_girisden():
    # Emir yalnız risk taşır (fiksing/momentum "stop 1·ATR"): stop yürütülen girişten (ask 101 + kayma 5) 10 nokta uzakta.
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100)])
    x = kos(d, emir(1, 1, stop=np.nan, risk=10.0, cikis_i=3, stop_tur=mt.STOP_SERT), kayma=0.5).iloc[0]
    assert x.durum == 0 and x.giris_f == 106.0 and x.R == 10.0 and x.stop == 96.0
    # Stop'suz aynı emir: R yine 10, stop seviyesi yok
    y = kos(d, emir(1, 1, stop=np.nan, risk=10.0, cikis_i=3, stop_tur=mt.STOP_YOK), kayma=0.5).iloc[0]
    assert y.R == 10.0 and np.isnan(y.stop)


def test_hedef_dakikasinin_ters_ucu_mae_ye_girer():
    # Hedefin dolduğu dakika önce 95'e iner, sonra hedefe dolar: MAE o dakikanın dibini taşır.
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (100, 112, 95, 111), (111, 111, 111, 111)])
    x = kos(d, emir(1, 1, stop=80.0, hedef_tur=mt.HEDEF_R, k=0.4, cikis_i=3)).iloc[0]
    assert mt.NEDEN[x.neden] == "hedef"
    assert x.mae == (95.0 - 1.0) - 101.0            # bid dibi − giriş
    assert x.mae <= x.pnl <= x.mfe


def test_bosluklu_stopta_mae_acilisi_tasir():
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (90, 91, 89, 90), (90, 90, 90, 90)])
    x = kos(d, emir(1, 1, stop=95.0, hedef_tur=mt.HEDEF_R, k=1.0, cikis_i=3)).iloc[0]
    assert mt.NEDEN[x.neden] == "bosluk_stop"
    assert x.mae <= x.pnl and x.mae == (90.0 - 1.0) - 101.0


def test_kayma_islem_yaratmaz_ask_stop_ile_kaymali_dolum_arasinda():
    # Uzun: ask açılışı 101, stop 101,5 — giriş tarafının kaymasız açılışı stop'un ötesinde. Kaymalı dolum (101 + 5)
    # stop'un berisine geçse de işlem yok: kayma işlem yaratamaz (eskiden R = 4,5 nokta ile alınıyordu).
    d = dakikalar([(100, 100, 100, 100)] * 4)
    for kayma in (0.0, 0.5, 1.0):
        x = kos(d, emir(1, 1, stop=101.5, hedef_tur=mt.HEDEF_R, k=2.0, cikis_i=3), kayma=kayma).iloc[0]
        assert mt.DURUM[x.durum] == "risk_gecersiz", kayma
    # Kısa simetrik: bid açılışı 99, stop 98,5
    for kayma in (0.0, 0.5):
        x = kos(d, emir(1, -1, stop=98.5, hedef_tur=mt.HEDEF_R, k=2.0, cikis_i=3), kayma=kayma).iloc[0]
        assert mt.DURUM[x.durum] == "risk_gecersiz", kayma
    # Haber kayması da işlem yaratmaz
    x = kos(d, emir(1, 1, stop=101.5, cikis_i=3), kayma=0.0, haber=np.ones(4, bool), haber_kayma=1.0).iloc[0]
    assert mt.DURUM[x.durum] == "risk_gecersiz"


def test_giris_dakikasinda_bosluklu_sert_stop_bid_stop_ask():
    # Uzun: ask 101 > stop 99,5 (giriş geçerli), bid 99 ≤ stop — makas stop'u kapsıyor: çıkış giriş dakikasının bid
    # açılışından (boşluk), stop seviyesinden değil.
    d = dakikalar([(100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100), (100, 100, 100, 100)])
    x = kos(d, emir(1, 1, stop=99.5, hedef_tur=mt.HEDEF_R, k=2.0, cikis_i=3), kayma=0.5).iloc[0]
    assert x.durum == 0 and x.giris_f == 106.0
    assert mt.NEDEN[x.neden] == "bosluk_stop" and x.cikis_i == 1 and x.cikis_f == 99.0 - 5.0
    assert x.mae <= x.pnl <= x.mfe
    # Kısa simetrik: bid 99 < stop 100,5 ≤ ask 101
    y = kos(d, emir(1, -1, stop=100.5, hedef_tur=mt.HEDEF_R, k=2.0, cikis_i=3)).iloc[0]
    assert mt.NEDEN[y.neden] == "bosluk_stop" and y.cikis_f == 101.0


def test_giris_dakikasi_boslugundan_sonra_ayni_dakikada_yeni_giris_yok():
    d = dakikalar([(100, 100, 100, 100)] * 5)
    e = mt.bos_emir(2)
    e[0] = (1, 1, 99.5, np.nan, 0, 0.0, np.nan, 3, 1, 0)       # giriş dakikasında boşluklu stop
    e[1] = (1, -1, 110.0, np.nan, 0, 0.0, np.nan, 3, 1, 1)     # aynı dakikada: açık pozisyon sayılır
    r = kos(d, e).set_index("kimlik")
    assert mt.NEDEN[r.loc[0, "neden"]] == "bosluk_stop"
    assert mt.DURUM[r.loc[1, "durum"]] == "pozisyon_acik"


def test_gun_sonu_girisi_ayri_sayilir():
    d = dakikalar([(100, 100, 100, 100)] * 4)
    x = kos(d, emir(mt.GIRIS_GUN_SONU, 1, stop=90.0, cikis_i=3)).iloc[0]
    assert mt.DURUM[x.durum] == "gun_sonu"
    y = kos(d, emir(-1, 1, stop=90.0, cikis_i=3)).iloc[0]
    assert mt.DURUM[y.durum] == "veri_yok"


def test_seviye_hedefi_kaymaya_bagli_gecersiz():
    # Ask 101, hedef 104: kayma 0'da alınır; 0,5 pip (5 nokta) kaymayla yürütülen giriş 106 hedefin ötesinde → atılır.
    d = dakikalar([(100, 100, 100, 100)] * 4)
    a = kos(d, emir(1, 1, stop=90.0, hedef_tur=mt.HEDEF_SEVIYE, seviye=104.0, cikis_i=3), kayma=0.0).iloc[0]
    b = kos(d, emir(1, 1, stop=90.0, hedef_tur=mt.HEDEF_SEVIYE, seviye=104.0, cikis_i=3), kayma=0.5).iloc[0]
    assert a.durum == 0 and mt.DURUM[b.durum] == "hedef_gecersiz"
