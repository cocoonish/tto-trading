# -*- coding: utf-8 -*-
"""Stratejilerin duman ve LOOKAHEAD sınamaları (sentetik veri).

Lookahead iki biçimde sınanır, her strateji biriminin varsayılan ve birkaç
başka kombinasyonunda:
  (1) KIRPMA — veri T anında kesilince, kapanışı T'den önce olan bütün sinyaller
      tam veriyle üretilenlerle birebir aynı olmalı (gün, mum, yön, stop, seviye).
  (2) GELECEK BOZMA — T'den sonraki fiyatlar bambaşka bir yürüyüşle değişince,
      kapanışı T'den önce olan sinyaller değişmemeli; T'den önce GİRİLEN
      işlemlerin giriş fiyatı, stop'u ve R'si de değişmemeli.
Bir kural bugünün tamamlanmamış yüksek/düşüğünü, sonraki mumun fiyatını ya da
günün kapanışını kullansaydı bu iki sınamadan biri düşerdi.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ayar as ay  # noqa: E402
import kosu  # noqa: E402
from gunluk import baglam_kur  # noqa: E402
from sentetik import boz, dakika_uret, olaylar_uret  # noqa: E402

AILE = kosu.AILE_TUM
OLAY = olaylar_uret()
D = dakika_uret(soklar=OLAY["utc_sn"].to_numpy())
# Kesim anları: gün ortası (NY sabahı), Londra sabahı, Londra açılışından önce ve UTC gece yarısından hemen sonra.
# Günün bütününden kurulan bir alan (ör. günün kapsamından okunan bir tatil bayrağı) günün ortasındaki bir kesimde
# değişir ve o günün sinyallerini siler; tek bir kesim anı bunu ancak tesadüfen görür.
KESIMLER = [int(pd.Timestamp(x, tz="UTC").timestamp())
            for x in ("2023-12-27 14:07", "2023-12-27 09:30", "2023-12-28 07:45", "2024-01-03 00:10")]
T_KES = KESIMLER[0]
# İlk kesimde varsayılan ve dört kombinasyon, öbür kesimlerde varsayılan ve bir kombinasyon daha. Metodoloji dersi
# sınamanın kapsamını bu adlardan okur (ders_olcum.ileri_bakma_kapsami): sayı değişirse ders de değişir.
ORNEK_ILK = 5
ORNEK_OTEKI = 2
# Takvim önceden bilinir (fiyat değildir): kırpılmış ve bozulmuş bağlam da aynı takvimi taşır.
B_TAM = baglam_kur(D, OLAY)
_BAG: dict = {}


def _bag(t: int):
    """Kesim anı t için (kırpılmış, geleceği bozulmuş) bağlam çifti."""
    if t not in _BAG:
        _BAG[t] = (baglam_kur(D.dilim(t), OLAY), baglam_kur(boz(D, t), OLAY))
    return _BAG[t]


B_KES, B_BOZ = _bag(T_KES)
A = ay.oku()


def _islem(b, aile, p, kayma=0.5):
    return kosu.Kosucu(b, A).islem(aile, p, kayma=kayma)


def _sinyaller(b, aile, p):
    sp = {k: v for k, v in p.items() if k not in kosu.CIKIS_PARAM}
    sin, ofset = AILE[aile](b, **sp)
    if len(sin) == 0:
        return pd.DataFrame(columns=["bt", "yon", "stop", "seviye", "giris_t", "kapanis", "karar"]), ofset
    s = sin["s"].to_numpy()
    if ofset is None:           # haber: çıpa satır başına
        bt = np.array([b.mumlar(int(p["tf"]), int(o)).bt[i] for o, i in zip(sin["ofset"], s)])
    else:
        bt = b.mumlar(int(p["tf"]), ofset).bt[s]
    out = pd.DataFrame({"bt": bt, "yon": sin["yon"].to_numpy(),
                        "stop": sin["stop"].to_numpy(),
                        "seviye": sin["seviye"].to_numpy() if "seviye" in sin else np.nan,
                        "giris_t": b.d.t[sin["giris_i"].to_numpy()] if "giris_i" in sin else np.nan})
    out["kapanis"] = out["bt"] + int(p["tf"]) * 60
    # Karar anı: girişi sinyalden geç olan stratejilerde (gün içi momentum, fiksing)
    # giriş dakikası; yoksa sinyal mumunun kapanışı. Kırpılmış veride o andan sonraki
    # bir giriş dakikası henüz yoktur — sinyalin "bilinmemesi" değil, girişin olmamasıdır.
    out["karar"] = np.where(np.isfinite(out["giris_t"]), np.maximum(out["kapanis"], out["giris_t"]), out["kapanis"])
    return out, ofset


def _ornekler(birim):
    liste, v = kosu.izgara(birim)
    r = np.random.default_rng(len(birim))
    secim = [v] + [liste[i] for i in r.choice(len(liste), size=min(ORNEK_ILK - 1, len(liste)), replace=False)]
    return secim


DURUMLAR = [(b, i, 0) for b in kosu.BIRIMLER for i in range(ORNEK_ILK)] + \
           [(b, i, k) for b in kosu.BIRIMLER for i in range(ORNEK_OTEKI) for k in range(1, len(KESIMLER))]


@pytest.mark.parametrize("birim,i,k", DURUMLAR)
def test_lookahead_kirpma_ve_bozma(birim, i, k):
    ornek = _ornekler(birim)
    if i >= len(ornek):
        pytest.skip("ızgara küçük")
    p = ornek[i]
    aile = kosu.BIRIMLER[birim]["aile"]
    t_kes = KESIMLER[k]
    b_kes, b_boz = _bag(t_kes)
    tam, _ = _sinyaller(B_TAM, aile, p)
    kes, _ = _sinyaller(b_kes, aile, p)
    bozuk, _ = _sinyaller(b_boz, aile, p)
    # Kırpılmış veride sinyal, T'den önce GİRİLEBİLECEK olanlardır (sonraki mum T'den önce açılır).
    sinir = t_kes - 2 * int(p["tf"]) * 60
    sec = lambda x: x[x["karar"] <= sinir].sort_values(["bt", "yon"]).reset_index(drop=True)  # noqa: E731
    a, b_, c = sec(tam), sec(kes), sec(bozuk)
    pd.testing.assert_frame_equal(a, b_, check_dtype=False, obj=f"{birim} kırpma")
    pd.testing.assert_frame_equal(a, c, check_dtype=False, obj=f"{birim} bozma")


@pytest.mark.parametrize("birim,k", [(b, k) for b in kosu.BIRIMLER for k in range(len(KESIMLER))])
def test_islem_girisi_bozmadan_etkilenmez(birim, k):
    _, v = kosu.izgara(birim)
    aile = kosu.BIRIMLER[birim]["aile"]
    sonuc = []
    sutun = ["giris_t", "yon", "giris_f", "stop", "R"]
    t_kes = KESIMLER[k]
    for b in (B_TAM, _bag(t_kes)[1]):
        isl = _islem(b, aile, v)
        if len(isl) == 0:
            sonuc.append(pd.DataFrame(columns=sutun))
            continue
        a = isl[(isl["durum"] == 0) & (isl["giris_t"] < t_kes - 3600)]
        sonuc.append(a[sutun].sort_values(["giris_t", "yon"]).reset_index(drop=True))
    if len(sonuc[0]) == 0 and len(sonuc[1]) == 0:
        return
    pd.testing.assert_frame_equal(sonuc[0], sonuc[1], check_dtype=False)


@pytest.mark.parametrize("birim", list(kosu.BIRIMLER))
def test_duman_varsayilan_islem_uretir_ve_giris_kapanistan_sonra(birim):
    _, v = kosu.izgara(birim)
    aile = kosu.BIRIMLER[birim]["aile"]
    isl = _islem(B_TAM, aile, v)
    assert len(isl) > 0, f"{birim}: sentetik 70 günde hiç sinyal yok"
    a = isl[isl["durum"] == 0]
    assert len(a) > 0
    assert (a["giris_t"] >= a["sinyal_t"]).all()
    assert (a["cikis_t"] >= a["giris_t"]).all()
    # gün sonu: hiçbir pozisyon 16:55 ET'den sonra açık kalmaz
    sinir = B_TAM.g.an["ny_1655"][a["gun_k"].to_numpy()]
    assert (a["cikis_t"].to_numpy() <= sinir + 60).all()


def test_fiks_stop_giristen_bir_atr():
    """Ön kayıt [fiks] ve [momentum]: "R birimi girişteki ATR(14); 'sert'/'kapanis' stop 1·ATR" — stop YÜRÜTÜLEN
    girişten ölçülür. Sinyal tablosu stop seviyesi taşımaz, yalnız riski; motor stop'u gerçek giriş fiyatından
    (makas ve kayma dahil) risk kadar uzağa koyar. Böylece stop'lu ve stop'suz varyantın R'si aynıdır: tam ATR."""
    for tur, gec in (("donus", 0), ("donus", 1), ("momentum", 0)):
        sin, _ = AILE["fiks"](B_TAM, tf=15, tur=tur, gecikme_mum=gec, tutma_mum=2)
        assert len(sin), f"{tur}/{gec}: sentetik veride sinyal yok"
        assert sin["stop"].isna().all(), f"{tur}/{gec}: tablo stop seviyesi taşımamalı"
        assert (sin["risk"] > 0).all()
    kayma = 0.5
    d = B_TAM.d
    for stop_turu in ("sert", "kapanis", "yok"):
        p = {"tf": 15, "tur": "donus", "gecikme_mum": 1, "tutma_mum": 2, "stop_turu": stop_turu, "hedef": "yok"}
        isl = _islem(B_TAM, "fiks", p, kayma=kayma)
        a = isl[isl["durum"] == 0]
        assert len(a), stop_turu
        np.testing.assert_allclose(a["R"].to_numpy(), a["risk"].to_numpy(), err_msg=stop_turu)
        if stop_turu == "yok":
            assert a["stop"].isna().all(), "stop'suz işlem stop seviyesi taşımamalı"
        else:
            uzak = (a["giris_f"] - a["stop"]).to_numpy() * a["yon"].to_numpy()
            np.testing.assert_allclose(uzak, a["risk"].to_numpy(), err_msg=stop_turu)
    sin, _ = AILE["momentum"](B_TAM, tf=60, cikis_et="16:00")
    if len(sin):
        assert sin["stop"].isna().all()


def test_mae_mfe_sonucu_kapsar():
    """MAE ≤ gerçekleşen sonuç ≤ MFE: hedefin dolduğu dakikanın ters ucu, boşluklu çıkışın açılışı ve çıkış
    kayması gezinmenin içinde kalır."""
    for aile, p in (("orb", {"tf": 15, "stop_yeri": "karsi_uc", "stop_turu": "sert", "hedef": "1R",
                            "son_giris_londra": "12:00"}),
                    ("orb", {"tf": 5, "stop_yeri": "orta", "stop_turu": "kapanis", "hedef": "2R",
                            "son_giris_londra": "14:00"})):
        isl = _islem(B_TAM, aile, p, kayma=0.5)
        a = isl[isl["durum"] == 0]
        assert len(a)
        assert (a["mae"] <= a["pnl"] + 1e-12).all() and (a["pnl"] <= a["mfe"] + 1e-12).all()


def test_izgara_sayilari_ve_varsayilan_izgarada():
    for birim in kosu.BIRIMLER:
        liste, v = kosu.izgara(birim)
        anahtarlar = {kosu._anahtar(p) for p in liste}
        assert kosu._anahtar(v) in anahtarlar, f"{birim}: varsayılan ızgarada yok"
        assert len(anahtarlar) == len(liste)
