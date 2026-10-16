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
T_KES = int(pd.Timestamp("2023-12-27 14:07", tz="UTC").timestamp())
# Takvim önceden bilinir (fiyat değildir): kırpılmış ve bozulmuş bağlam da aynı takvimi taşır.
B_TAM = baglam_kur(D, OLAY)
B_KES = baglam_kur(D.dilim(T_KES), OLAY)
B_BOZ = baglam_kur(boz(D, T_KES), OLAY)
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
    secim = [v] + [liste[i] for i in r.choice(len(liste), size=min(4, len(liste)), replace=False)]
    return secim


DURUMLAR = [(b, i) for b in kosu.BIRIMLER for i in range(5)]


@pytest.mark.parametrize("birim,i", DURUMLAR)
def test_lookahead_kirpma_ve_bozma(birim, i):
    ornek = _ornekler(birim)
    if i >= len(ornek):
        pytest.skip("ızgara küçük")
    p = ornek[i]
    aile = kosu.BIRIMLER[birim]["aile"]
    tam, _ = _sinyaller(B_TAM, aile, p)
    kes, _ = _sinyaller(B_KES, aile, p)
    bozuk, _ = _sinyaller(B_BOZ, aile, p)
    # Kırpılmış veride sinyal, T'den önce GİRİLEBİLECEK olanlardır (sonraki mum T'den önce açılır).
    sinir = T_KES - 2 * int(p["tf"]) * 60
    sec = lambda x: x[x["karar"] <= sinir].sort_values(["bt", "yon"]).reset_index(drop=True)  # noqa: E731
    a, b_, c = sec(tam), sec(kes), sec(bozuk)
    pd.testing.assert_frame_equal(a, b_, check_dtype=False, obj=f"{birim} kırpma")
    pd.testing.assert_frame_equal(a, c, check_dtype=False, obj=f"{birim} bozma")


@pytest.mark.parametrize("birim", list(kosu.BIRIMLER))
def test_islem_girisi_bozmadan_etkilenmez(birim):
    _, v = kosu.izgara(birim)
    aile = kosu.BIRIMLER[birim]["aile"]
    sonuc = []
    sutun = ["giris_t", "yon", "giris_f", "stop", "R"]
    for b in (B_TAM, B_BOZ):
        isl = _islem(b, aile, v)
        if len(isl) == 0:
            sonuc.append(pd.DataFrame(columns=sutun))
            continue
        a = isl[(isl["durum"] == 0) & (isl["giris_t"] < T_KES - 3600)]
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


def test_izgara_sayilari_ve_varsayilan_izgarada():
    for birim in kosu.BIRIMLER:
        liste, v = kosu.izgara(birim)
        anahtarlar = {kosu._anahtar(p) for p in liste}
        assert kosu._anahtar(v) in anahtarlar, f"{birim}: varsayılan ızgarada yok"
        assert len(anahtarlar) == len(liste)
