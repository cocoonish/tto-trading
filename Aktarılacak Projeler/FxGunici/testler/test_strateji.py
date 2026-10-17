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


def _ileri_bakma(birim: str, p: dict, t_kes: int) -> None:
    aile = kosu.BIRIMLER[birim]["aile"]
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


@pytest.mark.parametrize("birim,i,k", DURUMLAR)
def test_lookahead_kirpma_ve_bozma(birim, i, k):
    ornek = _ornekler(birim)
    if i >= len(ornek):
        pytest.skip("ızgara küçük")
    _ileri_bakma(birim, ornek[i], KESIMLER[k])


@pytest.mark.parametrize("birim,k", [(b, k) for b in kosu.YORUM for k in range(len(KESIMLER))])
def test_lookahead_yorum_okumasi(birim, k):
    """Yorum duyarlılığının harf okuması da (kosu.YORUM) aynı iki ileriye bakma sınamasından geçer: ölçülüp derste
    yazılan bir sayı, kural hangi okumayla kurulmuş olursa olsun geleceği görmemelidir."""
    _, v = kosu.izgara(birim)
    param, harf = kosu.YORUM[birim]
    _ileri_bakma(birim, {**v, param: harf}, KESIMLER[k])


# ───────────────────────────────────────────── sinyale çıpalı kesim
# Sabit kesim anları kararı kesimden en az iki mum önce olan sinyalleri kıyaslar: o payın içinde sinyal mumundan sonraki
# bir iki mum kesimden önce tamamlanır, yani bir iki mumluk ileri bakış görünmez; kesim gününde kıyaslanan bir sinyal
# yoksa günün kapanmamış verisine bakan bir sızıntı da görünmez. Burada kesim gerçek bir sinyalin KARAR anına konur:
# T = karar + 1 dk (giriş dakikası verinin içinde, sinyal mumundan sonraki mum henüz tamamlanmamış) ve T = karar + 1 mum
# + 1 dk (sonraki mum tamamlanmış, ikincisi değil). Kararı T − 1 dk'dan geç olmayan BÜTÜN sinyaller kıyaslanır; çıpanın
# kendisi kıyaslananların içinde olmalıdır (kesim gününde en az bir sinyal). Metodoloji dersi bu sabitleri okur.
CIPA_SAYISI = 2
CIPA_EK_MUM = (0, 1)


def _cipalar(b_tam, aile: str, p: dict) -> list[int]:
    """Tam veride sinyallerin karar anlarından deterministik çıpalar: dizinin üçte biri ve üçte ikisi (ısınma payının
    ve örneklem kenarının dışında), farklı günlerden."""
    tam, _ = _sinyaller(b_tam, aile, p)
    tam = tam[np.isfinite(tam["karar"])].sort_values(["karar", "yon"]).reset_index(drop=True)
    if not len(tam):
        return []
    out, gunler = [], set()
    for q in np.linspace(1 / 3, 2 / 3, CIPA_SAYISI):
        i = min(int(len(tam) * q), len(tam) - 1)
        karar = int(tam.loc[i, "karar"])
        gun = karar // 86400
        if gun in gunler:
            continue
        gunler.add(gun)
        out.append(karar)
    return out


def _cipali_ileri_bakma(birim: str, p: dict, karar: int, ek_mum: int, b_tam=None) -> int:
    """Çıpanın karar anından sonra kesilen veride ve geleceği bozulan veride, kararı kesimden önceki son dakikadan geç
    olmayan bütün sinyaller tam veriyle birebir aynı; çıpa kıyaslananların içinde. Kıyaslanan sinyal sayısını döndürür."""
    aile = kosu.BIRIMLER[birim]["aile"]
    tf = int(p["tf"])
    t_kes = karar + 60 + ek_mum * tf * 60
    b_tam = b_tam or B_TAM
    b_kes, b_boz = (baglam_kur(D.dilim(t_kes), OLAY), baglam_kur(boz(D, t_kes), OLAY))
    sinir = t_kes - 60
    sec = lambda x: x[x["karar"] <= sinir].sort_values(["bt", "yon"]).reset_index(drop=True)  # noqa: E731
    a = sec(_sinyaller(b_tam, aile, p)[0])
    assert (a["karar"] == karar).any(), f"{birim}: çıpa kıyaslananların içinde değil"
    pd.testing.assert_frame_equal(a, sec(_sinyaller(b_kes, aile, p)[0]), check_dtype=False,
                                  obj=f"{birim} çıpalı kırpma (+{ek_mum} mum)")
    pd.testing.assert_frame_equal(a, sec(_sinyaller(b_boz, aile, p)[0]), check_dtype=False,
                                  obj=f"{birim} çıpalı bozma (+{ek_mum} mum)")
    return len(a)


CIPALI = [(b, e) for b in kosu.BIRIMLER for e in CIPA_EK_MUM]


@pytest.mark.parametrize("birim,ek_mum", CIPALI)
def test_lookahead_sinyale_cipali(birim, ek_mum):
    _, v = kosu.izgara(birim)
    aile = kosu.BIRIMLER[birim]["aile"]
    cipalar = _cipalar(B_TAM, aile, v)
    assert cipalar, f"{birim}: sentetik veride çıpa olacak sinyal yok"
    for karar in cipalar:
        _cipali_ileri_bakma(birim, v, karar, ek_mum)


@pytest.mark.parametrize("birim,ek_mum", [(b, e) for b in kosu.YORUM for e in CIPA_EK_MUM])
def test_lookahead_sinyale_cipali_yorum(birim, ek_mum):
    _, v = kosu.izgara(birim)
    param, harf = kosu.YORUM[birim]
    p = {**v, param: harf}
    cipalar = _cipalar(B_TAM, kosu.BIRIMLER[birim]["aile"], p)
    assert cipalar
    for karar in cipalar:
        _cipali_ileri_bakma(birim, p, karar, ek_mum)


@pytest.mark.parametrize("kaydir", [1, 2])
def test_cipali_sinama_bir_iki_mumluk_ileri_bakisi_yakalar(kaydir, monkeypatch):
    """Sınamanın kendisinin sınaması: aralık kırılımı kararını `kaydir` mum SONRAKİ mumun kapanışından verecek biçimde
    bozulur (bir iki mumluk ileri bakış). Sinyale çıpalı kesim bunu yakalamalı; sabit kesimin iki mumluk payı yakalayamaz."""
    import strateji as st

    def sizdiran(b, m, tf, ust, alt, a_sn, b_sn, stop_yeri, gunler):
        j0, j1 = st.gun_mum_araligi(m, a_sn, b_sn, tf)
        satir = []
        for k in gunler:
            H, L = ust[k], alt[k]
            if not (np.isfinite(H) and np.isfinite(L)) or H <= L or j1[k] + kaydir > len(m.c):
                continue
            c = m.c[j0[k] + kaydir:j1[k] + kaydir]          # karar s mumunda, bilgi s + kaydir mumundan
            i = st.ilk_dogru((c > H) | (c < L))
            if i < 0:
                continue
            s = j0[k] + i
            yon = 1 if c[i] > H else -1
            stop = (L if yon == 1 else H) if stop_yeri == "karsi_uc" else (H + L) / 2.0
            satir.append((k, s, yon, stop, H - L, H, L))
        return st._tablo(satir)

    monkeypatch.setattr(st, "_aralik_kirilimi", sizdiran)
    b_tam = baglam_kur(D, OLAY)
    _, v = kosu.izgara("orb")
    cipalar = _cipalar(b_tam, "orb", v)
    assert cipalar
    yakalandi = 0
    for karar in cipalar:
        try:
            _cipali_ileri_bakma("orb", v, karar, 0, b_tam=b_tam)
        except AssertionError:
            yakalandi += 1
    assert yakalandi == len(cipalar), "çıpalı sınama bir iki mumluk ileri bakışı yakalamadı"


def test_vwap_ilk_saat_okumalari():
    """İlk saatin iki okuması (strateji.VWAP_ILK_SAAT), tarayıcıların kendisinde. `ok`: kuralın durumu yürür;
    `ok_s`: sinyal verilebilir. Ölçümün okumasında ikisi aynıdır (çapa + 60 dk); harfin okumasında durum çapadan yürür."""
    import strateji as st
    ilk = np.array([0, 0, 0, 1, 1, 1], bool)          # ilk üç mum çapanın ilk saati
    hep = np.ones(6, bool)
    bk = np.zeros(6, np.int64)
    vw = np.ones(6)
    # Geri çekilme: üç mum VWAP'ın üstünde kapanır (ilk saat), dördüncü mum VWAP'a iner ve üstünde kapanır.
    c = np.array([1.1, 1.1, 1.1, 1.05, 1.1, 1.1])
    h, l = c + 0.01, c - 0.01
    l[3] = 0.99
    assert len(st._vwap_cekilme_tara(c, h, l, vw, bk, ilk, ilk, 3)[0]) == 0      # ölçüm: sayaç ilk saatte sıfır
    s, y, _ = st._vwap_cekilme_tara(c, h, l, vw, bk, hep, ilk, 3)                 # harf: sayaç ilk saatte birikir
    assert list(s) == [3] and list(y) == [1]
    # Dönüş: ilk saatte üst bandın dışına çıkılır, ilk saatten SONRA içeride kapanılır → yalnız harfte satış sinyali.
    sg = np.full(6, 0.1)
    c = np.array([1.0, 1.3, 1.35, 1.2, 1.0, 1.0])
    h, l = c + 0.02, c - 0.02
    assert len(st._vwap_donus_tara(c, h, l, vw, sg, bk, ilk, ilk, 2.0)[0]) == 0
    s, y, stop, _ = st._vwap_donus_tara(c, h, l, vw, sg, bk, hep, ilk, 2.0)
    assert list(s) == [3] and list(y) == [-1] and stop[0] == pytest.approx(1.37)
    # Gezinti ilk saatin içinde biterse iki okumada da sinyal yok ve durum sonraki mumlara taşınmaz.
    c = np.array([1.0, 1.3, 1.1, 1.1, 1.0, 1.0])
    h, l = c + 0.02, c - 0.02
    for ok in (ilk, hep):
        assert len(st._vwap_donus_tara(c, h, l, vw, sg, bk, ok, ilk, 2.0)[0]) == 0
    # Ölçümün okuması tam koşuda da değişmedi: varsayılan okuma ile adıyla verilen "durum_sifir" aynı sinyaller.
    for aile, p in (("vwap_donus", {"tf": 15, "capa": "londra", "k": 2.0}), ("vwap_cekilme", {"tf": 15, "capa": "londra", "n": 12})):
        a, _ = AILE[aile](B_TAM, **p)
        b, _ = AILE[aile](B_TAM, **p, ilk_saat="durum_sifir")
        pd.testing.assert_frame_equal(a, b)
        with pytest.raises(ValueError):
            AILE[aile](B_TAM, **p, ilk_saat="bilinmeyen")


def _pivot_seviyeleri(b):
    g = b.g
    P = (g.onceki_h + g.onceki_l + g.onceki_c) / 3.0
    return 2 * P - g.onceki_l, 2 * P - g.onceki_h


def test_pivot_kirilim_iki_okuma():
    """Pivot kırılımı: ölçümün okumasında R1 yalnız yukarı, S1 yalnız aşağı kesişte sinyaldir; harfin okumasında her
    seviyenin günün İLK kesişi, iki yönde de. P'de iki okuma aynıdır; dönüş kuralı okumadan etkilenmez."""
    R1, S1 = _pivot_seviyeleri(B_TAM)
    m = B_TAM.mumlar(15, 0)
    for kesis in ("yonlu", "iki_yon"):
        sin, _ = AILE["pivot"](B_TAM, tf=15, seviye="R1S1", tur="kirilim", kesis=kesis)
        assert len(sin)
        k_, s = sin["gun_k"].to_numpy(), sin["s"].to_numpy()
        lv, yon = sin["ust"].to_numpy(), sin["yon"].to_numpy()
        r1 = np.isclose(lv, R1[k_])
        s1 = np.isclose(lv, S1[k_])
        assert (r1 | s1).all()
        # her sinyal kesiş yönünde bir kesiştir
        assert ((m.c[s] - lv) * yon > 0).all() and ((m.c[s - 1] - lv) * yon <= 0).all()
        if kesis == "yonlu":
            assert (yon[r1] == 1).all() and (yon[s1] == -1).all()
        else:
            ters = int((r1 & (yon == -1)).sum() + (s1 & (yon == 1)).sum())
            assert ters > 0, "sentetik veride R1'in aşağı ya da S1'in yukarı kesişi yok: sınama boş geçerdi"
    for seviye, tur in (("P", "kirilim"), ("R1S1", "donus"), ("P", "donus")):
        a, _ = AILE["pivot"](B_TAM, tf=15, seviye=seviye, tur=tur, kesis="yonlu")
        b, _ = AILE["pivot"](B_TAM, tf=15, seviye=seviye, tur=tur, kesis="iki_yon")
        pd.testing.assert_frame_equal(a, b, obj=f"{seviye} {tur}")


def test_sahte_acilis_okumasi():
    """Başarısız kırılımın açılış okuması (harfin okuması): pencerenin İLK mumu önceki kapanışa bakılmadan dışarıda
    kapanırsa da kırılım mumudur. ORB ve Asya'da iki okuma aynıdır (pencereden önceki kapanış aralığın içindedir);
    PDH/PDL'de açılış okuması yalnız açılıştaki adayı EKLER: ölçümün okumasının sinyal verdiği her gün harfin okumasında
    da sinyal vardır, ayrıştıkları günde harfin sinyali pencerenin ilk mumundaki kırılımdan doğar."""
    for seviye in ("orb", "asya"):
        a, _ = AILE["sahte"](B_TAM, tf=15, seviye=seviye, pencere=2)
        b, _ = AILE["sahte"](B_TAM, tf=15, seviye=seviye, pencere=2, acilis="acilis_ici")
        pd.testing.assert_frame_equal(a, b, obj=seviye)
    for tf, pencere in ((15, 2), (5, 3), (60, 1)):
        a, _ = AILE["sahte"](B_TAM, tf=tf, seviye="pdhl", pencere=pencere)
        b, _ = AILE["sahte"](B_TAM, tf=tf, seviye="pdhl", pencere=pencere, acilis="acilis_ici")
        assert set(a["gun_k"]) <= set(b["gun_k"])
        m = B_TAM.mumlar(tf, 0)
        from strat_ortak import gun_mum_araligi
        j0, _ = gun_mum_araligi(m, B_TAM.g.an["lon_0800"], B_TAM.g.an["ny_1400"], tf)
        x = a.set_index("gun_k")
        for _, r in b.iterrows():
            k_ = int(r["gun_k"])
            if k_ in x.index and int(x.loc[k_, "s"]) == int(r["s"]) and x.loc[k_, "yon"] == r["yon"]:
                continue
            # ayrışan gün: geri alınış pencerenin ilk mumundan sonra en çok 'pencere' mum içinde
            assert j0[k_] < int(r["s"]) <= j0[k_] + pencere
    a, _ = AILE["sahte"](B_TAM, tf=15, seviye="pdhl", pencere=2)
    b, _ = AILE["sahte"](B_TAM, tf=15, seviye="pdhl", pencere=2, acilis="kesis")
    pd.testing.assert_frame_equal(a, b)


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
