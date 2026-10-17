#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Strateji birimlerini ızgarada koşturur; seçim, sağlamlık ve koşul analizini kurar.

Bir STRATEJİ BİRİMİ, okura tek strateji olarak anlatılan şeydir: bir aile ve
sabitlenmiş alt tipi (ör. başarısız kırılımın ORB seviyesi, pivotun dönüş
varyantı, New York IB'nin 09:30 başlangıcı). Her birimin ızgarası, önceden
kayıtlı varsayılanı ve seçimi ayrıdır; deflated Sharpe'ın deneme sayısı da
birimin kendi ızgarasıdır.

Çıktı: `cikti/sonuc/<birim>.json` (bütün pariteler) ve `cikti/islem/<birim>/`
altında varsayılan ve seçilen kombinasyonun işlemleri (figürler için).
"""
from __future__ import annotations

import itertools
import json
import math
import sys
import time
import tomllib
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

import ayar as ay
import metrik as mk
import motor as mt
import saglamlik as sg
import strat_haber as sh
from gunluk import Baglam
from ozellik import giris_saati_tsi, ozellikler
from strat_ortak import kos
from strateji import AILE

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI / "cikti"
ONKAYIT = tomllib.loads((BURASI / "onkayit.toml").read_text(encoding="utf-8"))
GENEL = ONKAYIT["genel"]
KAYMA_TEMEL = float(GENEL["temel_kayma_pip"])
ZAMAN_MUM = int(GENEL["desen_zaman_mum"])
HABER_ZAMAN_MUM = int(ONKAYIT["haber"]["zaman_mum"])
AILE_TUM = {**AILE, **sh.HABER}

BIRIMLER: dict[str, dict] = {
    "orb": {"aile": "orb", "sabit": {}, "varsayilan": "varsayilan"},
    "asya": {"aile": "asya", "sabit": {}, "varsayilan": "varsayilan"},
    "nyib_0800": {"aile": "nyib", "sabit": {"baslangic_et": "08:00"}, "varsayilan": "varsayilan"},
    "nyib_0930": {"aile": "nyib", "sabit": {"baslangic_et": "09:30"}, "varsayilan": "varsayilan"},
    "icmum": {"aile": "icmum", "sabit": {}, "varsayilan": "varsayilan"},
    "sikisma": {"aile": "sikisma", "sabit": {}, "varsayilan": "varsayilan"},
    "pdhl": {"aile": "pdhl", "sabit": {}, "varsayilan": "varsayilan"},
    "sahte_orb": {"aile": "sahte", "sabit": {"seviye": "orb"}, "varsayilan": "varsayilan"},
    "sahte_asya": {"aile": "sahte", "sabit": {"seviye": "asya"}, "varsayilan": "varsayilan"},
    "sahte_pdhl": {"aile": "sahte", "sabit": {"seviye": "pdhl"}, "varsayilan": "varsayilan"},
    "vwap_donus": {"aile": "vwap_donus", "sabit": {}, "varsayilan": "varsayilan"},
    "vwap_cekilme": {"aile": "vwap_cekilme", "sabit": {}, "varsayilan": "varsayilan"},
    "pivot_donus": {"aile": "pivot", "sabit": {"tur": "donus"}, "varsayilan": "varsayilan_donus"},
    "pivot_kirilim": {"aile": "pivot", "sabit": {"tur": "kirilim"}, "varsayilan": "varsayilan_kirilim"},
    "fiks_momentum": {"aile": "fiks", "sabit": {"tur": "momentum", "gecikme_mum": 0, "tutma_mum": 1},
                      "varsayilan": "varsayilan_momentum"},
    "fiks_donus": {"aile": "fiks", "sabit": {"tur": "donus"}, "varsayilan": "varsayilan_donus"},
    "momentum": {"aile": "momentum", "sabit": {}, "varsayilan": "varsayilan"},
    # Haber stratejileri: olay takvimi bağlamdan gelir; mum çıpası olaydan olaya değişir.
    "n1": {"aile": "n1", "sabit": {}, "varsayilan": "varsayilan", "haber": True},
    "n2": {"aile": "n2", "sabit": {}, "varsayilan": "varsayilan", "haber": True},
    "n3": {"aile": "n3", "sabit": {}, "varsayilan": "varsayilan", "haber": True},
    "n4": {"aile": "n4", "sabit": {}, "varsayilan": "varsayilan", "haber": True},
    "n5": {"aile": "n5", "sabit": {}, "varsayilan": "varsayilan", "haber": True},
}

# Isı haritasının iki ekseni (öbür parametreler varsayılanda)
ISI = {
    "orb": ("tf", "son_giris_londra"), "asya": ("tf", "son_giris_londra"), "nyib_0800": ("tf", "ib_pencere"),
    "nyib_0930": ("tf", "ib_pencere"), "icmum": ("tf", "gecerlilik"), "sikisma": ("tf", "sure"),
    "pdhl": ("tf", "stop_kurali"), "sahte_orb": ("tf", "pencere"), "sahte_asya": ("tf", "pencere"),
    "sahte_pdhl": ("tf", "pencere"), "vwap_donus": ("tf", "k"), "vwap_cekilme": ("tf", "n"),
    "pivot_donus": ("tf", "seviye"), "pivot_kirilim": ("tf", "seviye"), "fiks_momentum": ("tf", "stop_turu"),
    "fiks_donus": ("tf", "tutma_mum"), "momentum": ("tf", "cikis_et"),
    "n1": ("tf", "giris_mumu"), "n2": ("tf", "k"), "n3": ("tf", "on_mum"), "n4": ("tf", "on_mum"),
    "n5": ("tf", "geri_cekilme"),
}
CIKIS_PARAM = ("stop_turu", "hedef")


def izgara(birim: str) -> tuple[list[dict], dict]:
    """Birimin kombinasyon listesi (geçersizler ayıklanmış) ve önceden kayıtlı varsayılanı."""
    tanim = BIRIMLER[birim]
    aile = tanim["aile"]
    kayit = ONKAYIT[aile]
    iz = dict(kayit["izgara"])
    for k, v in tanim["sabit"].items():
        iz[k] = [v]
    iz.pop("tur", None) if aile in ("pivot", "fiks") else None
    anahtarlar = list(iz)
    liste, gorulen = [], set()
    for deger in itertools.product(*(iz[k] for k in anahtarlar)):
        p = dict(zip(anahtarlar, deger))
        p.update({k: v for k, v in tanim["sabit"].items()})
        if aile == "nyib" and p["tf"] == 60 and p["ib_pencere"] == "60":
            continue
        if aile == "pivot" and p["tur"] == "kirilim" and p["hedef"] == "seviye":
            continue
        if aile in ("fiks", "momentum"):
            p.setdefault("hedef", "yok")
        if aile == "fiks" and p["tur"] == "momentum":
            p["gecikme_mum"], p["tutma_mum"] = 0, 1
        anahtar = tuple(sorted(p.items()))
        if anahtar in gorulen:
            continue
        gorulen.add(anahtar)
        liste.append(p)
    v = dict(kayit[tanim["varsayilan"]])
    v.update({k: val for k, val in tanim["sabit"].items()})
    if aile in ("fiks", "momentum"):
        v.setdefault("hedef", "yok")
    if aile == "fiks" and v.get("tur") == "momentum":
        v["gecikme_mum"], v["tutma_mum"] = 0, 1
    if aile == "nyib" and v["tf"] == 60 and v["ib_pencere"] == "60":
        v["ib_pencere"] = "tf"
    return liste, v


def _anahtar(p: dict) -> str:
    return "|".join(f"{k}={p[k]}" for k in sorted(p))


class Kosucu:
    def __init__(self, b: Baglam, a: ay.Ayar):
        self.b, self.a = b, a
        g = b.g
        gun = g.gun[~g.tatil]
        self.gun_is = gun[gun <= np.datetime64(a.ic_bitis)]
        self.gun_oos = gun[gun >= np.datetime64(a.dis_baslangic)]
        self.gun_tum = gun
        self._sinyal: dict = {}

    def sinyal(self, aile: str, p: dict):
        sp = {k: v for k, v in p.items() if k not in CIKIS_PARAM}
        anahtar = (aile, tuple(sorted(sp.items())))
        if anahtar not in self._sinyal:
            self._sinyal[anahtar] = AILE_TUM[aile](self.b, **sp)
        return self._sinyal[anahtar]

    def islem(self, aile: str, p: dict, kayma: float = KAYMA_TEMEL, haber_kayma: float | None = None) -> pd.DataFrame:
        """`haber_kayma`: haber penceresindeki dolumların ek kayması (verilmezse ayarın 1,0 pip'i; "yalnız makas"
        koşusu ikisini de sıfırlar)."""
        sin, ofset = self.sinyal(aile, p)
        stop_turu = p.get("stop_turu", "yok")
        hk = self.a.haber_kayma_pip if haber_kayma is None else float(haber_kayma)
        if ofset is None:           # haber: çıpa satır başına
            return sh.kos_haber(self.b, sin, int(p["tf"]), stop_turu, p.get("hedef", "yok"),
                                kayma, hk, HABER_ZAMAN_MUM)
        return kos(self.b, sin, int(p["tf"]), ofset, stop_turu, p.get("hedef", "yok"),
                   kayma, hk, ZAMAN_MUM)

    def haber_payi(self, isl: pd.DataFrame) -> float:
        """Alınan işlemlerin girişi haber penceresine düşen payı."""
        a = mk.alinan(isl)
        if not len(a):
            return float("nan")
        return float(self.b.haber[a["giris_i"].to_numpy(np.int64)].mean())

    def bol(self, isl: pd.DataFrame):
        if len(isl) == 0:
            return isl, isl
        g = isl["gun"].to_numpy()
        return isl[g <= np.datetime64(self.a.ic_bitis)], isl[g >= np.datetime64(self.a.dis_baslangic)]


#: Rastgele yön sınamasının asgari işlem sayısı (tek tanım saglamlik'te); altında sınama koşmaz ve kural "çalışıyor"
#: diyemez. Bilgi bayrağı `az_islem` bu sayıdan okunur; hükmü değiştirmez.
ASGARI_RASTGELE = sg.ASGARI_RASTGELE


def _hukum(m_oos: dict, ry: dict) -> str:
    """Ön kaydın [hukum] kuralı, harfi harfine. "ölçülemedi" yalnız dönemde hiç işlem yoksa (ortalama tanımsız).
    Az işlemde (n < 20) rastgele yön sınaması koşmaz, bootstrap 10 işlemin altında kurulmaz: ikisi de "çalışıyor"un
    şartıdır, yani az işlemli artı bir sonuç "zayıf" kalır."""
    esik = float(ONKAYIT["hukum"]["rastgele_esik_yuzdelik"])
    r = m_oos.get("beklenti_r", float("nan"))
    if r is None or not np.isfinite(r):
        return "olculemedi"
    if r <= 0:
        return "calismiyor"
    ga, yz = m_oos.get("ga_alt"), ry.get("yuzdelik")
    if ga is not None and np.isfinite(ga) and ga > 0 and yz is not None and np.isfinite(yz) and yz >= esik:
        return "calisiyor"
    return "zayif"


def _maliyet_bayragi(m: dict) -> bool:
    return bool(m.get("ga_brut_alt", -1) > 0 and m.get("beklenti_r", 1) <= 0)


#: Seçim eşitliğinin toleransı (günlük R serisinin yıllıklandırılmış Sharpe'ı). Ön kayıt eşitlikte "ızgaradaki ilk"
#: kombinasyonu ister; işlevsel kopyalar (ör. tek mum tutulan fiksing momentumunda kapanış stopu ile stop'suz: aynı
#: giriş, aynı çıkış dakikası) yalnız kayan nokta artığıyla (≤ 1e−14) ayrışır ve kesin karşılaştırma sonrakini seçerdi.
SECIM_TOLERANS = 1e-9


def _sec(adaylar: list[dict]) -> dict | None:
    """Ön kaydın seçim kuralı: en yüksek örneklem içi Sharpe; tolerans içindeki eşitlikte ızgaradaki ilk."""
    if not adaylar:
        return None
    en = max(s["is"]["sharpe"] for s in adaylar)
    return next(s for s in adaylar if s["is"]["sharpe"] >= en - SECIM_TOLERANS)


def islem_imzasi(isl: pd.DataFrame) -> tuple[str, np.ndarray] | None:
    """Alınan işlemlerin imzası: sıralı (giriş dakikası, çıkış dakikası, yön) üçlülerinin özü ve aynı sıradaki R'ler.
    Hiç işlem yoksa None."""
    import hashlib
    a = mk.alinan(isl)
    if not len(a):
        return None
    anahtar = np.stack([a["giris_i"].to_numpy(np.int64), a["cikis_i"].to_numpy(np.int64),
                        a["yon"].to_numpy(np.int64)])
    sira = np.lexsort(anahtar[::-1])
    h = hashlib.sha1(np.ascontiguousarray(anahtar[:, sira]).tobytes()).hexdigest()
    return h, a["r"].to_numpy(np.float64)[sira]


def imza_ozu(isl: pd.DataFrame) -> str | None:
    """İmzanın tek dizgelik özü (işlemler + 1e−9'a yuvarlanmış R'ler): ölçüm dosyasında iki kombinasyonun aynı işlem
    kümesini verip vermediği bu dizgeyle sorulur (ör. ay sonu ayrımlarının çoklu sınama paydası)."""
    import hashlib
    im = islem_imzasi(isl)
    if im is None:
        return None
    return im[0] + ":" + hashlib.sha1(np.round(im[1], 9).tobytes()).hexdigest()[:16]


def imza_ayni(x: tuple | None, y: tuple | None) -> bool:
    """İki imza aynı işlemleri ve aynı R'leri (1e−9 içinde) mi taşıyor; iki boş imza aynıdır."""
    if x is None or y is None:
        return x is None and y is None
    return x[0] == y[0] and len(x[1]) == len(y[1]) and bool(np.allclose(x[1], y[1], rtol=0.0, atol=1e-9))


class ImzaSiniflayici:
    """Izgaranın işlevsel kopyaları: aynı alınan işlemler (giriş ve çıkış dakikası, yön) ve aynı R sonuçları (1e−9
    içinde) veren kombinasyonlar aynı sınıftır. Hiç işlem üretmeyen kombinasyon None (boş). Izgara değişmez; tekil
    deneme sayısı bilgi olarak yazılır (deflated Sharpe'ın deneme sayısı ızgaranın kendisidir — kopyalar eşiği
    yükseltir, yani hüküm tarafında tutucudur)."""

    def __init__(self):
        self.siniflar: list[tuple[str, np.ndarray]] = []

    def sinif(self, isl: pd.DataFrame) -> int | None:
        return self.sinif_imzadan(islem_imzasi(isl))

    def sinif_imzadan(self, im: tuple | None) -> int | None:
        if im is None:
            return None
        for j, x in enumerate(self.siniflar):
            if imza_ayni(x, im):
                return j
        self.siniflar.append(im)
        return len(self.siniflar) - 1


#: Ön kaydın harfine göre İKİNCİ bir okuması olan kurallar: birim → ((sinyal parametresi, harfin okuması), …). Ölçümün
#: kuralı sonuçtan önce yazılmış okumadır (sinyal fonksiyonlarının varsayılanı) ve hüküm onunla verilir; harfin okuması
#: aynı koşuda ayrıca ölçülür ve etkisi derste yazılır (yorum_duyarlilik). Bir kuralın birden çok okuması varsa her biri
#: TEK BAŞINA ölçülür (öbürü ölçümün kuralında kalır). Okumalar strateji.py'de, fonksiyon belgelerinde:
#:   VWAP dönüşü ve geri çekilmesi   ilk saat: kuralın durumu da sıfırlanır ↔ yalnız sinyal verilmez (ön kaydın harfi)
#:   VWAP dönüşü                      bandın içine dönüş: yalnız çıkılan kenar sorulur ↔ kapanış iki bandın arasında
#:   pivot kırılımı                   R1 yalnız yukarı, S1 yalnız aşağı ↔ her seviyede iki yönde ilk kesiş (harf)
#:   başarısız kırılım                kırılım mumu bir kesiştir ↔ pencerenin ilk mumu dışarıda kapanırsa da kırılım
#:   başarısız kırılım                dönüş: kapanış kırılan kenarın berisinde ↔ aralığın içinde ("yeniden içeride")
#: Başarısız kırılımda ORB ve Asya'nın açılış okumaları tanım gereği aynıdır (pencerenin ilk mumundan önceki kapanış
#: aralığın içindedir); o iki birim de koşulur ki "aynı" bir beyan değil ölçüm olsun.
YORUM: dict[str, tuple[tuple[str, str], ...]] = {
    "vwap_donus": (("ilk_saat", "yalniz_sinyal"), ("bant", "iki_kenar")),
    "vwap_cekilme": (("ilk_saat", "yalniz_sinyal"),),
    "pivot_kirilim": (("kesis", "iki_yon"),),
    "sahte_pdhl": (("acilis", "acilis_ici"), ("donus", "iki_kenar")),
    "sahte_orb": (("acilis", "acilis_ici"), ("donus", "iki_kenar")),
    "sahte_asya": (("acilis", "acilis_ici"), ("donus", "iki_kenar")),
}


def birim_kos(birim: str, kosucu: Kosucu, ayrinti: bool = True) -> dict:
    tanim = BIRIMLER[birim]
    aile = tanim["aile"]
    liste, varsayilan = izgara(birim)
    k = kosucu
    satirlar = []
    yillik = {}
    imza = ImzaSiniflayici()
    for p in liste:
        isl = k.islem(aile, p)
        ic, dis = k.bol(isl)
        mi = mk.ozet(ic, k.gun_is, bootstrap=False)
        md = mk.ozet(dis, k.gun_oos, bootstrap=False)
        ss = mk.gunluk_r(ic, k.gun_is)
        im = islem_imzasi(isl)
        satirlar.append({"p": p, "anahtar": _anahtar(p), "is": mi, "oos": md, "haber_payi": k.haber_payi(isl),
                         "sr_gunluk_is": float(ss.mean() / ss.std(ddof=1)) if ss.std(ddof=1) > 0 else float("nan"),
                         "sinif": imza.sinif_imzadan(im), "imza": im if birim in YORUM else None})
        yillik[_anahtar(p)] = mk.yil_toplamlari(isl, k.gun_tum)
    sinif = [s["sinif"] for s in satirlar]
    asgari = int(ONKAYIT["secim"]["asgari_islem_haber" if tanim.get("haber") else "asgari_islem"])
    adaylar = [s for s in satirlar if s["is"]["n"] >= asgari and np.isfinite(s["is"]["sharpe"])]
    secilen = _sec(adaylar)
    ilk_sinif: dict = {}
    for s in satirlar:
        if s["sinif"] is not None:
            ilk_sinif.setdefault(s["sinif"], s["anahtar"])
    sonuc = {"birim": birim, "aile": aile, "kombinasyon": len(liste), "varsayilan": varsayilan,
             # Işlevsel kopyalar: aynı işlemleri veren kombinasyonlar tek deneme sayılır; boş: hiç işlem üretmeyen.
             "tekil_deneme": len(ilk_sinif), "bos_kombinasyon": sum(1 for c in sinif if c is None),
             "izgara": [{"anahtar": s["anahtar"], "p": s["p"], "haber_payi": s["haber_payi"],
                         "is": {x: s["is"].get(x) for x in ("n", "beklenti_r", "beklenti_pip", "sharpe", "isabet")},
                         "oos": {x: s["oos"].get(x) for x in ("n", "beklenti_r", "beklenti_pip", "sharpe", "isabet")},
                         "kopya": (ilk_sinif[s["sinif"]] if s["sinif"] is not None
                                   and ilk_sinif[s["sinif"]] != s["anahtar"] else None),
                         "bos": s["sinif"] is None}
                        for s in satirlar],
             "secilen": secilen["p"] if secilen else None,
             "secim_asgari": asgari,
             "en_cok_is_islem": max((s["is"]["n"] for s in satirlar), default=0)}
    if not ayrinti:
        return sonuc
    # Bu birimin bu paritedeki önceki işlem dosyaları silinir: seçim değiştiyse önceki koşunun seçtiği kombinasyonun
    # dosyası kalır ve işlem listesine bakan biri onu bugünün seçimi sanardı.
    for eski in (CIKTI / "islem" / birim).glob(f"{k.b.d.cift}__*.parquet"):
        eski.unlink()
    sr_denemeler = np.array([s["sr_gunluk_is"] for s in satirlar])
    # Tekil denemeler: her işlevsel kopya sınıfının ilk kombinasyonu (bilgi: kopyaların deflated Sharpe'a etkisi).
    gorulen: set = set()
    sr_tekil = []
    for s in satirlar:
        if s["sinif"] is not None and s["sinif"] not in gorulen:
            gorulen.add(s["sinif"])
            sr_tekil.append(s["sr_gunluk_is"])
    for ad, p in (("varsayilan", varsayilan), ("secilen", secilen["p"] if secilen else None)):
        if p is None:
            sonuc[f"{ad}_analiz"] = None
            continue
        sonuc[f"{ad}_analiz"] = derin(birim, aile, p, k, sr_denemeler if ad == "secilen" else None, yillik,
                                      ornek=(ad == "varsayilan"),
                                      sr_tekil=np.array(sr_tekil) if ad == "secilen" else None)
    sonuc["walk_forward"] = walk_forward(aile, liste, yillik, k, asgari)
    if tanim.get("haber"):
        sonuc["tf_haber_kaymasiz"] = tf_haber_kaymasiz(aile, liste, varsayilan, k)
    if birim in YORUM:
        sonuc["yorum"] = {param: yorum_duyarlilik(birim, aile, param, harf, varsayilan, satirlar, secilen, k, asgari)
                          for param, harf in YORUM[birim]}
    if aile == "fiks":
        sonuc["ay_sonu_tf"] = ay_sonu_tf(birim, aile, liste, varsayilan, k)
    return sonuc


def _yorum_sonuc(aile: str, p: dict, k: Kosucu, donemler: tuple[str, ...]) -> dict:
    """Bir kombinasyonun hüküm girdileri (birincil hükmün kuralıyla): dönem başına özet (bootstrap'lı), rastgele yön ve
    hüküm; sıfıra yakın hüküm ucu derin()'deki gibi ayrıca."""
    isl = k.islem(aile, p)
    ic, dis = k.bol(isl)
    kume = {"is": (ic, k.gun_is), "oos": (dis, k.gun_oos), "tum": (isl, k.gun_tum)}
    out = {}
    for d in donemler:
        x, gun = kume[d]
        m = mk.ozet(x, gun)
        ry = sg.rastgele_yon(k.b, x, int(p["tf"]), k.sinyal(aile, p)[1], KAYMA_TEMEL, k.a.haber_kayma_pip)
        satir = {"ozet": {kk: m.get(kk) for kk in ("n", "beklenti_r", "beklenti_pip", "sharpe", "isabet", "ga_alt",
                                                     "ga_ust", "ga_brut_alt")},
                 "rastgele": {"yuzdelik": ry.get("yuzdelik"), "n": ry.get("n")}, "hukum": _hukum(m, ry)}
        r_ = m.get("beklenti_r")
        if m.get("n") and r_ is not None and np.isfinite(r_):
            rr = mk.alinan(x)["r"].to_numpy(np.float64)
            s_ = (mk.sinir_bilgisi(rr, m.get("ga_alt"), "alt") if r_ > 0
                  else mk.sinir_bilgisi(rr, m.get("ga_ust"), "ust"))
            if s_:
                satir["sinir"] = {("ga_alt" if r_ > 0 else "ga_ust"): s_}
        out[d] = satir
    return out


def yorum_duyarlilik(birim: str, aile: str, param: str, harf: str, varsayilan: dict, satirlar: list[dict],
                     secilen: dict | None, k: Kosucu, asgari: int) -> dict:
    """Yorum duyarlılığı (YORUM): ızgara harfin okumasıyla baştan koşulur. Hüküm ölçümün okumasıyla verilir; bu kayıt
    harfin okuması seçilseydi neyin değişeceğini söyler. Bir kuralın her okuması ayrı bir kayıttır (öbür okumalar
    ölçümün kuralında kalır).

      degisen          işlemleri (giriş ve çıkış dakikası, yön, R) değişen kombinasyon sayısı; bos_kombinasyon:
                       harfin okumasında hiç işlem açmayan kombinasyon
      varsayilan       önceden kayıtlı varsayılan harfin okumasıyla: örneklem dışı ve bütün dönem (ön kaydın varsayılan
                       için örneklem dışı saydığı pencere), her birinde rastgele yön ve hüküm
      secilen          ızgaradan seçim harfin okumasıyla BAŞTAN (aynı kural: asgari işlem, en yüksek örneklem içi Sharpe,
                       tolerans içinde ızgaradaki ilk) ve seçilenin örneklem dışı hükmü
    Okumanın parametresi ızgaranın bir boyutu DEĞİLDİR: seçim ızgaranın kendi kombinasyonları arasında yapılır, deneme
    sayısı değişmez."""
    import inspect
    if (param, harf) not in YORUM[birim]:
        raise ValueError(f"{birim}: kayıtsız okuma {param}={harf}")
    olcum = inspect.signature(AILE_TUM[aile]).parameters[param].default
    alt = lambda p: {**p, param: harf}  # noqa: E731
    degisen, bos, adaylar, v_degisti = 0, 0, [], None
    v_anahtar = _anahtar(varsayilan)
    for s in satirlar:
        isl = k.islem(aile, alt(s["p"]))
        im = islem_imzasi(isl)
        ayni = imza_ayni(im, s["imza"])
        degisen += not ayni
        bos += im is None
        if s["anahtar"] == v_anahtar:
            v_degisti = not ayni
        ic, _ = k.bol(isl)
        mi = mk.ozet(ic, k.gun_is, bootstrap=False)
        if mi["n"] >= asgari and np.isfinite(mi["sharpe"]):
            adaylar.append({"p": s["p"], "anahtar": s["anahtar"], "is": mi})
    sec = _sec(adaylar)
    s_temel = _anahtar(secilen["p"]) if secilen else None
    return {"param": param, "olcum": olcum, "harf": harf, "kombinasyon": len(satirlar), "degisen": int(degisen),
            "bos_kombinasyon": int(bos),
            "varsayilan_degisti": v_degisti,
            "varsayilan": _yorum_sonuc(aile, alt(varsayilan), k, ("oos", "tum")),
            "secilen_p": sec["p"] if sec else None, "secilen_anahtar": sec["anahtar"] if sec else None,
            "secim_ayni": (sec["anahtar"] if sec else None) == s_temel,
            "secilen_is": ({x: sec["is"].get(x) for x in ("n", "beklenti_r", "sharpe")} if sec else None),
            "secilen": _yorum_sonuc(aile, alt(sec["p"]), k, ("oos",)) if sec else None}


def tf_haber_kaymasiz(aile: str, liste: list[dict], v: dict, k: Kosucu) -> dict:
    """Haber kuralının zaman dilimi kıyası haber kayması OLMADAN da: haber penceresi olaydan sonraki 15 dakikadır ve
    5 dakikalık mumla giriş pencerenin içinde, 15 ve 60 dakikalık mumla dışında kalır; kıyasın ne kadarının bu
    maliyet farkından geldiği ancak iki koşuyla ayrılır. Öbür parametreler varsayılanda."""
    out = {}
    for p in liste:
        if any(p.get(x) != v.get(x) for x in v if x != "tf"):
            continue
        isl = k.islem(aile, p, haber_kayma=0.0)
        ic, dis = k.bol(isl)
        out[str(p["tf"])] = {"is": mk.ozet(ic, k.gun_is, bootstrap=False)["beklenti_r"],
                             "oos": mk.ozet(dis, k.gun_oos, bootstrap=False)["beklenti_r"],
                             "tum": mk.ozet(isl, k.gun_tum, bootstrap=False)["beklenti_r"],
                             "haber_payi": k.haber_payi(isl)}
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def derin(birim: str, aile: str, p: dict, k: Kosucu, sr_denemeler, yillik, ornek: bool = False,
          sr_tekil=None) -> dict:
    isl = k.islem(aile, p)
    ic, dis = k.bol(isl)
    out = {"p": p, "imza": imza_ozu(isl),
           "is": mk.ozet(ic, k.gun_is), "oos": mk.ozet(dis, k.gun_oos), "tum": mk.ozet(isl, k.gun_tum)}
    # maliyet duyarlılığı
    maliyet = {}
    for s in k.a.kayma_pip:
        x = isl if s == KAYMA_TEMEL else k.islem(aile, p, kayma=s)
        xi, xd = k.bol(x)
        maliyet[str(s)] = {"is": mk.ozet(xi, k.gun_is, bootstrap=False), "oos": mk.ozet(xd, k.gun_oos, bootstrap=False),
                           "tum": mk.ozet(x, k.gun_tum, bootstrap=False)}
    out["maliyet"] = {s: {d: {kk: v[d][kk] for kk in ("n", "beklenti_r", "beklenti_pip", "sharpe")} for d in v}
                      for s, v in maliyet.items()}
    # Yalnız makas: temel kayma da haber kayması da sıfır — dolumlar yalnız o dakikanın gerçek bid/ask'ından. Merdivenin
    # "0,0 pip" kademesi haber penceresindeki dolumlarda 1,0 pip haber kaymasını taşır; ikisi ancak bu koşuyla ayrılır.
    x = k.islem(aile, p, kayma=0.0, haber_kayma=0.0)
    xi, xd = k.bol(x)
    out["yalniz_makas"] = {d: {kk: v[kk] for kk in ("n", "beklenti_r", "beklenti_pip", "sharpe")}
                           for d, v in (("is", mk.ozet(xi, k.gun_is, bootstrap=False)),
                                        ("oos", mk.ozet(xd, k.gun_oos, bootstrap=False)),
                                        ("tum", mk.ozet(x, k.gun_tum, bootstrap=False)))}
    # Haber penceresine düşen giriş payı dönem başına: maliyet tablosu örneklem dışını basar, notu da onun payını
    # söylemelidir (bütün dönemin payı ondan ayrışabilir).
    out["haber_payi"] = k.haber_payi(isl)
    out["haber_payi_donem"] = {"is": k.haber_payi(ic), "oos": k.haber_payi(dis), "tum": k.haber_payi(isl)}
    # başabaş: kayma ızgarasında işlem başına net R (serinin ölçüsü; her işlem 1 R riske eder) = 0'ın doğrusal
    # kestirimi, x ekseni dolum başına pip (haber kayması 1,0 pip'te sabit). Pip ortalaması R ortalamasıyla işaret
    # değiştirebilir (geniş stop'lu işlemler pipte ağır basar): ölçüldü, EUR/USD N4'te sıfır kaymada pip +2,48, R +0,05;
    # 1 pipte pip +1,13, R −0,03. İki dönemde: bütün dönem ve örneklem dışı (2024 →).
    xs = sorted(float(s) for s in maliyet)
    for d, son in (("tum", ""), ("oos", "_oos")):
        ys = [maliyet[str(s) if str(s) in maliyet else s][d]["beklenti_r"] for s in xs]
        out["basabas_kayma_pip" + son] = _sifir_kesisim(xs, ys)
        sifir = maliyet.get(str(0.0), {}).get(d) or {}
        out["basabas_sifir_r" + son] = sifir.get("beklenti_r")          # sıfır kaymada (haber kayması dahil) net R
        out["basabas_ek_maliyet_pip" + son] = sifir.get("beklenti_pip")   # aynı, pip'te (bilgi)
    # rastgele yön (örneklem dışı ve bütün dönem)
    ofset = k.sinyal(aile, p)[1]
    out["rastgele"] = {"oos": sg.rastgele_yon(k.b, dis, int(p["tf"]), ofset, KAYMA_TEMEL, k.a.haber_kayma_pip),
                       "tum": sg.rastgele_yon(k.b, isl, int(p["tf"]), ofset, KAYMA_TEMEL, k.a.haber_kayma_pip)}
    # Yüzdeliğin duyarlılığı (bilgi; hüküm önceden kayıtlı tohumla verilir): eşiğe yakın ya da üstündeki yüzdelik
    # tek işleme mi, tohuma mı bağlı — en iyi işlem(ler) çıkarılınca yüzdelik ve sabit bir tohum listesinde eşik payı.
    out["rastgele_duyarlilik"] = {}
    for d, x in (("oos", dis), ("tum", isl)):
        yz = out["rastgele"][d].get("yuzdelik")
        if yz is not None and np.isfinite(yz) and yz >= sg.DUYARLILIK_TABAN:
            out["rastgele_duyarlilik"][d] = sg.rastgele_duyarlilik(k.b, x, int(p["tf"]), ofset, KAYMA_TEMEL,
                                                                   k.a.haber_kayma_pip,
                                                                   float(ONKAYIT["hukum"]["rastgele_esik_yuzdelik"]))
    # deflated Sharpe (yalnız ızgaradan SEÇİLEN için anlamlı; varsayılanda PSR)
    gr_is = mk.gunluk_r(ic, k.gun_is)
    sr_is = float(gr_is.mean() / gr_is.std(ddof=1)) if gr_is.std(ddof=1) > 0 else float("nan")
    if sr_denemeler is not None:
        out["dsr"] = sg.dsr(sr_is, sr_denemeler, gr_is)
        if sr_tekil is not None:
            t = sg.dsr(sr_is, sr_tekil, gr_is)
            out["dsr"].update({"n_tekil": t.get("n_deneme"), "dsr_tekil": t.get("dsr"),
                               "dsr_gurultu_tekil": t.get("dsr_gurultu")})
    else:
        out["dsr"] = sg.psr_tek(sr_is, gr_is)
    # hüküm: birincil pencere örneklem dışı (2024 →); varsayılan için bütün dönem de örneklem dışıdır (ön kaydın başlığı)
    # ve onun hükmü ayrıca yazılır. Maliyet bayrağı iki dönemde.
    out["hukum"] = _hukum(out["oos"], out["rastgele"]["oos"])
    out["hukum_tum"] = _hukum(out["tum"], out["rastgele"]["tum"])
    out["maliyet_yiyor"] = _maliyet_bayragi(out["tum"])
    out["maliyet_yiyor_oos"] = _maliyet_bayragi(out["oos"])
    # Gün kümeli aralık (bilgi): hüküm ve maliyet bayrağı ön kaydın okumasıyla, işlemleri bağımsız örnekleyen aralıktan
    # verilir. Aynı paritede aynı gün açılan işlemler aynı haberi ve aynı seans hareketini taşır; bağımsız sayılmaları
    # aralığı daraltabilir. Aynı iki ölçüt gün kümeli aralıkla da sorulur ki bağımsızlık varsayımının hükmü ve bayrağı
    # ne kadar taşıdığı görünsün (havuzun aralığı zaten gün kümelidir).
    out["gun_kumeli"] = {}
    for d, x, gunler in (("oos", dis, k.gun_oos), ("tum", isl, k.gun_tum)):
        m = mk.ozet(x, gunler, kume_sutun="gun")
        g_ = {kk: m.get(kk) for kk in ("ga_alt", "ga_ust", "ga_brut_alt", "ga_brut_ust")}
        g_["hukum"] = _hukum({**out[d], "ga_alt": m.get("ga_alt")}, out["rastgele"][d])
        g_["maliyet_yiyor"] = _maliyet_bayragi({**out[d], "ga_brut_alt": m.get("ga_brut_alt", -1)})
        g_["n_gun"] = int(mk.alinan(x)["gun"].nunique()) if out[d].get("n") else 0
        out["gun_kumeli"][d] = g_
    # Sıfıra yakın uçlar (bilgi; hüküm ve bayrak önceden kayıtlı 2.000 tekrarla verilir): hükmü ayıran uç (net artı
    # iken net aralığın alt ucu), maliyet bayrağını ayıran uç (net ≤ 0 iken brüt aralığın alt ucu) ve "kayıp şansla
    # açıklanmıyor" cümlesini ayıran uç (net ≤ 0 iken net aralığın üst ucu; havuzda da aynı uç sorulur). Bütün dönem
    # yalnız varsayılanda bir hükümdür (seçilenin bütün dönemi seçim dönemini içerir).
    for d, x in (("oos", dis), ("tum", isl)):
        if d == "tum" and sr_denemeler is not None:
            continue
        m = out[d]
        r_ = m.get("beklenti_r")
        if not m.get("n") or r_ is None or not np.isfinite(r_):
            continue
        ax = mk.alinan(x)
        sinir = {}
        if r_ > 0:
            s_ = mk.sinir_bilgisi(ax["r"].to_numpy(np.float64), m.get("ga_alt"), "alt")
            if s_:
                sinir["ga_alt"] = s_
        else:
            s_ = mk.sinir_bilgisi(ax["r_brut"].to_numpy(np.float64), m.get("ga_brut_alt"), "alt")
            if s_:
                sinir["ga_brut_alt"] = s_
            s_ = mk.sinir_bilgisi(ax["r"].to_numpy(np.float64), m.get("ga_ust"), "ust")
            if s_:
                sinir["ga_ust"] = s_
        if sinir:
            m["sinir"] = sinir
    out["az_islem"] = {d: bool(out[d].get("n", 0) < ASGARI_RASTGELE) for d in ("is", "oos", "tum")}
    out["kuyruk"] = kuyruk(k, isl, KAYMA_TEMEL)
    # rejimler: yıl ve oynaklık tercili
    a = mk.alinan(isl)
    yil = pd.DatetimeIndex(a["gun"].to_numpy().astype("datetime64[ns]")).year
    out["yil"] = {int(y): _kisa(a[yil == y]) for y in sorted(set(yil))}
    yz = k.b.g.atr_yuzdelik[a["gun_k"].to_numpy(np.int64)]
    terc = np.where(np.isnan(yz), None, np.where(yz < 1 / 3, "düşük", np.where(yz < 2 / 3, "orta", "yüksek")))
    out["oynaklik"] = {t: _kisa(a[terc == t]) for t in ("düşük", "orta", "yüksek")}
    # giriş saati (TSİ)
    saat = giris_saati_tsi(a)
    out["saat_tsi"] = {int(h): _kisa(a[saat == h]) for h in sorted(set(saat))}
    # çıkış nedenleri
    out["neden"] = {str(n): int(c) for n, c in a["neden"].value_counts().items()}
    # koşullar
    f = ozellikler(k.b, a)
    icm = (a["gun"].to_numpy() <= np.datetime64(k.a.ic_bitis))
    out["kosul"] = sg.kova_analizi(f, icm, int(ONKAYIT["kosul"]["asgari_kova_islem"]))
    # Ön kaydın aileye özgü iki ölçüsü: fiksingde ay sonu ayrı ([fiks]), momentumda regresyon ([momentum]).
    if aile == "fiks":
        out["ay_sonu"] = ay_sonu_ayrimi(a, icm, ry=lambda x: sg.rastgele_yon(k.b, x, int(p["tf"]), ofset, KAYMA_TEMEL,
                                                                            k.a.haber_kayma_pip))
    if aile == "momentum":
        out["regresyon"] = momentum_regresyon(k, aile, p)
    if "olay" in a.columns:
        out["haber_kirilim"] = haber_kirilim(a, icm)
    # günlük birikimli eğri (figür)
    gr = mk.gunluk_r(isl, k.gun_tum)
    out["egri"] = {"gun": [str(x) for x in k.gun_tum], "r": [round(float(x), 4) for x in np.cumsum(gr)]}
    if ornek:
        out["ornek"] = ornek_gunler(k, birim, p, isl, k.sinyal(aile, p)[1])
    _islem_kaydet(birim, k.b.d.cift, p, isl)
    return out


#: Örnek işlemlerin R eşiği: kazanan net ≥ +0,5 R; kaybeden net ≤ −0,5 R ve işlem boyunca lehine 0,5 R'ye
#: ulaşmamış; tuzak, lehine en az 0,5 R gittikten sonra zararla kapanmış işlem.
ORNEK_ESIK = 0.5
#: Alıştırmaların "dolum daha kötü olsaydı" şıkkı: örnek işlem bu kadar EK kaymayla motorda yeniden koşturulur.
ORNEK_EK_KAYMA = 0.5


def _yeniden_kos(k: Kosucu, s: pd.Series, tf: int, ofset: int, kayma: float) -> pd.Series:
    """Tek bir işlemi aynı emirle (giriş dakikası, yön, stop kuralı, hedef kuralı, planlanan çıkış) motorda yeniden
    koşturur. R katı hedef ve yürütülen girişten konan stop, yeni dolum fiyatından yeniden kurulur."""
    e = mt.bos_emir(1)
    e["giris_i"] = int(s["giris_i"])
    e["yon"] = int(s["yon"])
    e["stop"] = float(s["stop_emir"])
    e["risk"] = float(s["risk_emir"])
    e["hedef_tur"] = int(s["hedef_tur"])
    e["hedef_k"] = float(s["hedef_k"])
    e["hedef_seviye"] = float(s["hedef_seviye_emir"])
    e["cikis_i"] = int(s["plan_cikis_i"])
    e["stop_tur"] = int(s["stop_tur"])
    e["kimlik"] = 0
    return mt.simule(k.b.d, e, k.b.bar_son(tf, ofset), k.b.haber, kayma, k.a.haber_kayma_pip,
                     tek_pozisyon=False).iloc[0]


def _sayi(v):
    return None if v is None or not np.isfinite(float(v)) else round(float(v), 1)


def ornek_gunler(k: Kosucu, birim: str, p: dict, isl: pd.DataFrame, ofset_sabit: int | None) -> list[dict]:
    """Ders figürünün örnek günleri: örneklem DIŞINDAN üç işlem.

      kazanan   net ≥ +0,5 R
      kaybeden  net ≤ −0,5 R ve işlem boyunca lehine 0,5 R'ye ulaşmamış
      tuzak     lehine en az 0,5 R gittikten sonra zararla kapanmış (kırılımda sahte kırılım, dönüşte süren hareket)
    Uygun işlemler arasından seçim SABİT bir çekilişle yapılır (ön kaydın tohumu, birim, parite ve etiketten); sonuca
    bakılarak seçilmez ve üç örnek ayrı günlerdedir. Uygun işlem yoksa yedek tanım (kazanan: net > 0; kaybeden: net
    < 0) kullanılır ve kayda geçer; tuzağın yedeği yoktur.

    Gün, stratejinin kendi zaman diliminin ÇIPALI mumlarıyla (orta fiyat, nokta) ve işlemin seviyeleriyle yazılır;
    işlem ayrıca dolum başına ORNEK_EK_KAYMA pip ek kaymayla motorda yeniden koşturulur (alıştırmaların "dolum
    daha kötü olsaydı" şıkkı elle değil motorla cevaplanır). Yeniden koşu temel kaymayla işlemin kendisini birebir
    vermiyorsa düşer: o zaman ek kaymalı koşu da aynı kuralı ölçmüyor demektir."""
    a = mk.alinan(isl)
    if len(a) == 0:
        return []
    dis = a[a["gun"].to_numpy() >= np.datetime64(k.a.dis_baslangic)].sort_values("giris_t", kind="stable")
    r, mfe = dis["r"], dis["mfe_r"]
    tanimlar = (("kazanan", r >= ORNEK_ESIK, r > 0),
                ("kaybeden", (r <= -ORNEK_ESIK) & (mfe < ORNEK_ESIK), r < 0),
                ("tuzak", (r < 0) & (mfe >= ORNEK_ESIK), None))
    tohum = int(GENEL["tohum"])
    kullanilan: list = []
    out = []
    for etiket, kosul, yedek in tanimlar:
        bos_gun = ~dis["gun"].isin(kullanilan)
        x, secim = dis[kosul & bos_gun], "kural"
        if not len(x) and yedek is not None:
            x, secim = dis[yedek & bos_gun], "yedek"
        if not len(x):
            continue
        s = x.iloc[zlib.crc32(f"{tohum}|{birim}|{k.b.d.cift}|{etiket}".encode()) % len(x)]
        kullanilan.append(s["gun"])
        tf = int(p["tf"])
        ofset = int(s["ofset"]) if ofset_sabit is None else int(ofset_sabit)
        ayni = _yeniden_kos(k, s, tf, ofset, KAYMA_TEMEL)
        if not (int(ayni["durum"]) == 0 and np.isclose(float(ayni["r"]), float(s["r"]), atol=1e-9)
                and int(ayni["cikis_t"]) == int(s["cikis_t"])):
            raise AssertionError(f"{birim} {k.b.d.cift} {etiket}: örnek işlem yeniden koşuda kendini vermedi")
        ek = _yeniden_kos(k, s, tf, ofset, KAYMA_TEMEL + ORNEK_EK_KAYMA)
        m = k.b.mumlar(tf, ofset)
        gk = int(s["gun_k"])
        t0 = int(k.b.g.gun_basi[gk])
        j0, j1 = np.searchsorted(m.bt, [t0, t0 + 86400])
        stopsuz = int(s["stop_tur"]) == mt.STOP_YOK
        ek_ok = int(ek["durum"]) == 0
        out.append({
            "etiket": etiket, "secim": secim, "gun": str(s["gun"])[:10], "tf": tf, "ofset": ofset,
            "mum": {"t": [int(v) for v in m.bt[j0:j1]], "o": [round(float(v), 1) for v in m.o[j0:j1]],
                    "h": [round(float(v), 1) for v in m.h[j0:j1]], "l": [round(float(v), 1) for v in m.l[j0:j1]],
                    "c": [round(float(v), 1) for v in m.c[j0:j1]]},
            "islem": {"yon": int(s["yon"]), "giris_t": int(s["giris_t"]), "cikis_t": int(s["cikis_t"]),
                      "giris_f": _sayi(s["giris_f"]), "cikis_f": _sayi(s["cikis_f"]),
                      "stop": None if stopsuz else _sayi(s["stop"]),
                      "hedef": _sayi(s["hedef"]), "neden": int(s["neden"]), "r": round(float(s["r"]), 3),
                      "pnl_pip": round(float(s["pnl_pip"]), 2), "R_pip": round(float(s["R_pip"]), 2),
                      "stop_tur": int(s["stop_tur"]), "hedef_tur": int(s["hedef_tur"]),
                      "hedef_k": float(s["hedef_k"]), "stopsuz": bool(stopsuz),
                      "mae_r": round(float(s["mae_r"]), 3), "mfe_r": round(float(s["mfe_r"]), 3),
                      "sinyal_t": int(s["sinyal_t"]) if "sinyal_t" in s else None,
                      "ust": _sayi(s.get("ust")), "alt": _sayi(s.get("alt")),
                      "seviye": _sayi(s.get("seviye")), "olay": str(s["olay"]) if "olay" in s else None,
                      "olay_t": int(s["t0"]) if "t0" in s and pd.notna(s.get("t0")) else None},
            "ek_kayma": {"kayma_pip": KAYMA_TEMEL + ORNEK_EK_KAYMA, "durum": int(ek["durum"]),
                         "giris_f": _sayi(ek["giris_f"]) if ek_ok else None,
                         "cikis_f": _sayi(ek["cikis_f"]) if ek_ok else None,
                         "stop": None if (stopsuz or not ek_ok) else _sayi(ek["stop"]),
                         "hedef": _sayi(ek["hedef"]) if ek_ok else None,
                         "cikis_t": int(ek["cikis_t"]) if ek_ok else None,
                         "neden": int(ek["neden"]) if ek_ok else None,
                         "r": round(float(ek["r"]), 3) if ek_ok else None,
                         "pnl_pip": round(float(ek["pnl_pip"]), 2) if ek_ok else None,
                         "R_pip": round(float(ek["R_pip"]), 2) if ek_ok else None},
        })
    return out


def kuyruk(k: Kosucu, isl: pd.DataFrame, kayma_pip: float) -> dict:
    """Ortalamanın kuyruğa duyarlılığı (betimleyici; hükmü değiştirmez). R ortalaması her işlemi riskine göre
    büyüklükler: riski makas düzeyine inen tek bir işlem onlarca R yazar ve ortalamayı tek başına taşıyabilir.

      r_tek_haric     en iyi tek işlem çıkarılınca ortalama R
      r_uc_haric      en iyi üç işlem çıkarılınca
      r_pahali_haric  beklenen gidiş-dönüş maliyeti (girişteki makas + iki dolumun temel kayması + giriş haber
                      penceresindeyse haber kayması) riskin yarısını aşan işlemler çıkarılınca — o işlemler girişte
                      bilinen bir ölçüyle ayrılır, yani bir "R tabanı" kuralının ne değiştireceğini gösterir"""
    a = mk.alinan(isl)
    if len(a) == 0:
        return {}
    d = k.b.d
    gi = a["giris_i"].to_numpy(np.int64)
    maliyet = (d.ao[gi] - d.bo[gi]) / d.pip + 2.0 * kayma_pip + np.where(k.b.haber[gi], k.a.haber_kayma_pip, 0.0)
    pahali = maliyet > 0.5 * a["R_pip"].to_numpy(np.float64)
    gun = a["gun"].to_numpy()
    out = {}
    for ad, m in (("is", gun <= np.datetime64(k.a.ic_bitis)), ("oos", gun >= np.datetime64(k.a.dis_baslangic)),
                  ("tum", np.ones(len(a), bool))):
        r = a["r"].to_numpy(np.float64)[m]
        n = len(r)
        if n < 4:
            out[ad] = {"n": int(n)}
            continue
        # Kararlı sıralama: en yüksek R'yi birden çok işlem paylaşıyorsa (1R/2R hedefte sık; ölçüldü: 88 varsayılanın
        # 24'ünde 23–150 işlem) "en iyi işlem" tek bir işlem değildir; o zaman tarih ve risk yazılmaz, eşit işlem
        # sayısı ve risk aralığı yazılır. Hariç ortalamalar hangi eşit işlemin çıktığına bağlı değildir.
        sira = np.argsort(-r, kind="stable")
        ax = a[m]
        en_r = float(r[sira[0]])
        esit = np.abs(r - en_r) <= 1e-9
        n_esit = int(esit.sum())
        risk_esit = ax["R_pip"].to_numpy(np.float64)[esit]
        en = ax.iloc[int(sira[0])]
        ph = pahali[m]
        out[ad] = {"n": int(n), "r": float(r.mean()),
                   "r_tek_haric": float(np.delete(r, sira[:1]).mean()),
                   "r_uc_haric": float(np.delete(r, sira[:3]).mean()),
                   "en_iyi_r": en_r, "en_iyi_esit": n_esit,
                   "en_iyi_gun": str(en["gun"])[:10] if n_esit == 1 else None,
                   "en_iyi_R_pip": float(en["R_pip"]) if n_esit == 1 else None,
                   "en_iyi_R_pip_alt": float(risk_esit.min()), "en_iyi_R_pip_ust": float(risk_esit.max()),
                   "n_pahali": int(ph.sum()), "pay_pahali": float(ph.mean()),
                   "r_pahali_haric": float(r[~ph].mean()) if (~ph).any() else float("nan"),
                   "pip": float(ax["pnl_pip"].to_numpy().mean())}
    return out


def haber_kirilim(a: pd.DataFrame, icm: np.ndarray) -> dict:
    """Haber stratejisinin işlemleri olay, ilk hareket kovası ve trend uyumuna göre (IS/OOS ayrı)."""
    out = {}
    for boyut in ("olay", "kova", "trend_uyum"):
        out[boyut] = {}
        for deger in sorted(a[boyut].dropna().unique()):
            m = (a[boyut] == deger).to_numpy()
            out[boyut][str(deger)] = {"tum": _kisa(a[m]), "is": _kisa(a[m & icm]), "oos": _kisa(a[m & ~icm])}
    out["olay_kova"] = {}
    for (o, kv), g in a.groupby(["olay", "kova"], sort=True):
        out["olay_kova"][f"{o}|{kv}"] = _kisa(g)
    return out


def _welch(x1: np.ndarray, x0: np.ndarray) -> dict:
    """İki kümenin ortalama farkı ve Welch t (eşit varyans varsayılmaz); iki yönlü p."""
    from scipy import stats
    if len(x1) < 2 or len(x0) < 2:
        return {"fark_r": None, "t": None, "p": None}
    t, p = stats.ttest_ind(x1, x0, equal_var=False)
    return {"fark_r": float(x1.mean() - x0.mean()), "t": float(t), "p": float(p)}


def ay_sonu_ayrimi(a: pd.DataFrame, icm: np.ndarray, ry=None) -> dict:
    """WM/R fiksingi, ön kayıt [fiks]: "bütün günler ve ay sonu (ayın son Londra iş günü) ayrı".

    Aynı kural, aynı işlemler; yalnız ayrı raporlanır (ay sonu için ayrı parametre SEÇİLMEZ). Her
    kümede örneklem içi, dışı ve bütün dönem: işlem sayısı, ortalama R ve bootstrap %95 aralığı;
    ay sonu ile öbür günlerin farkı Welch t ile. Ay sonu yılda on iki gündür: örneklem dışında küme
    otuz dolayında işlemdir ve aralık buna göre geniştir.

    `ry` (verilirse): ay sonu kümesinde rastgele yön sınaması (aynı giriş dakikaları, yazı tura yön). Ön kayıt ay
    sonuna ayrı hüküm vermez; bu, hüküm kuralının üçüncü şartının alt kümeye SONRADAN uygulanmasıdır ve derste öyle
    adlandırılır."""
    m = a["ay_sonu"].to_numpy(bool)
    out: dict = {"ay_sonu": {}, "diger": {}, "fark": {}}
    for d, dm in (("is", icm), ("oos", ~icm), ("tum", np.ones(len(a), bool))):
        for ad, mm in (("ay_sonu", m), ("diger", ~m)):
            x = a[mm & dm]
            kk = _kisa(x)
            if kk["n"] >= 2:
                kk["ga_alt"], kk["ga_ust"] = mk.bootstrap_ort(x["r"].to_numpy())
            if ry is not None and ad == "ay_sonu":
                r_ = ry(x)
                kk["rastgele"] = {"yuzdelik": r_.get("yuzdelik"), "n": r_.get("n")}
            out[ad][d] = kk
        out["fark"][d] = _welch(a[m & dm]["r"].to_numpy(), a[~m & dm]["r"].to_numpy())
    return out


def ay_sonu_tf(birim: str, aile: str, liste: list[dict], v: dict, k: Kosucu) -> dict:
    """Ay sonu ayrımı üç zaman diliminde: öbür parametreler varsayılanda, yalnız mum uzunluğu değişir (ön kaydın tf
    kıyası; varsayılanın kendi ayrımı derin()'de). Ayrımın çoklu sınama paydası derste ölçülen bütün ayrımlardan kurulur
    (varsayılan, seçilen, bu varyantlar; aynı işlem kümesi bir kez)."""
    out = {}
    for p in liste:
        if any(p.get(x) != v.get(x) for x in v if x != "tf"):
            continue
        isl = k.islem(aile, p)
        a = mk.alinan(isl)
        if not len(a):
            continue
        icm = (a["gun"].to_numpy() <= np.datetime64(k.a.ic_bitis))
        ofset = k.sinyal(aile, p)[1]
        out[str(p["tf"])] = {"p": p, "imza": imza_ozu(isl),
                             "ayrim": ay_sonu_ayrimi(a, icm, ry=lambda x, p=p, ofset=ofset: sg.rastgele_yon(
                                 k.b, x, int(p["tf"]), ofset, KAYMA_TEMEL, k.a.haber_kayma_pip))}
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def nw_ols(x: np.ndarray, y: np.ndarray, lag: int | None = None) -> dict:
    """y = α + β·x, sıradan en küçük kareler; standart hata Newey–West (Bartlett çekirdeği).

    Gecikme verilmezse Newey–West'in kural gecikmesi ⌊4·(n/100)^(2/9)⌋. Gözlemler zaman sırasında
    gelmelidir (gecikmeli çarpımlar komşu günleri eşler). p iki yönlü, normal yaklaşımla."""
    n = len(x)
    if n < 10:
        return {"n": int(n)}
    L = int(np.floor(4 * (n / 100) ** (2 / 9))) if lag is None else int(lag)
    X = np.column_stack([np.ones(n), x])
    xtx_ters = np.linalg.inv(X.T @ X)
    b = xtx_ters @ X.T @ y
    u = y - X @ b
    xu = X * u[:, None]
    S = xu.T @ xu
    for l in range(1, L + 1):
        w = 1 - l / (L + 1)
        G = xu[l:].T @ xu[:-l]
        S += w * (G + G.T)
    V = xtx_ters @ S @ xtx_ters
    se = np.sqrt(np.diag(V))
    t = b / se
    p = [math.erfc(abs(v) / math.sqrt(2)) for v in t]
    r2 = 1 - (u @ u) / ((y - y.mean()) @ (y - y.mean()))
    return {"n": int(n), "lag": L, "alfa": float(b[0]), "beta": float(b[1]), "se_beta": float(se[1]),
            "t_beta": float(t[1]), "p_beta": float(p[1]), "t_alfa": float(t[0]), "r2": float(r2),
            "isaret_isabet": float(np.mean(np.sign(x) == np.sign(y)))}


def momentum_regresyon(k: Kosucu, aile: str, p: dict) -> dict:
    """Ön kayıt [momentum]: "sinyalin öngörü gücü regresyonla (öğleden sonra getirisi ~ ilk tf getirisi;
    HAC) sınanır". Strateji işlemlerinden BAĞIMSIZ: maliyet, stop ve yürütme fiyatı yok, yalnız orta fiyat.

    x: Londra 08:00'den itibaren ilk tf mumunun getirisi (kapanış − açılış); y: giriş (12:00 ET) ile
    çıkış (16:00 ya da 16:55 ET) dakikalarının açılış orta fiyatı farkı. İkisi de o günün girişteki
    ATR(14, 60 dk)'sine bölünür, yani yıllar ve pariteler arası birimsizdir. Gözlem: sinyal üreten
    her işlem günü (ilk mum hareketsizse gün yok — strateji de o gün işlem açmaz)."""
    sin, _ = k.sinyal(aile, p)
    if not len(sin):
        return {}
    d = k.b.d
    gi = sin["giris_i"].to_numpy(np.int64)
    # çıkış dakikası, işlemlerdeki gibi gün sonuyla sınırlı (strat_ortak.emirler)
    ci = np.minimum(sin["cikis_i"].to_numpy(np.int64), k.b.g.sinir[sin["gun_k"].to_numpy(np.int64)])
    risk = sin["risk"].to_numpy(np.float64)
    ok = (gi >= 0) & (ci > gi) & (ci < len(d.t)) & np.isfinite(risk) & (risk > 0)
    gun = k.b.g.gun[sin["gun_k"].to_numpy(np.int64)][ok]
    x = sin["ilk_hareket"].to_numpy(np.float64)[ok] / risk[ok]
    y = (d.mo[ci[ok]] - d.mo[gi[ok]]) / risk[ok]
    sira = np.argsort(gun, kind="stable")
    gun, x, y = gun[sira], x[sira], y[sira]
    out = {}
    for ad, m in (("is", gun <= np.datetime64(k.a.ic_bitis)), ("oos", gun >= np.datetime64(k.a.dis_baslangic)),
                  ("tum", np.ones(len(gun), bool))):
        out[ad] = nw_ols(x[m], y[m])
    return out


def _kisa(a: pd.DataFrame) -> dict:
    if len(a) == 0:
        return {"n": 0}
    r = a["r"].to_numpy()
    return {"n": int(len(a)), "beklenti_r": float(r.mean()), "isabet": float((a["pnl_pip"] > 0).mean()),
            "beklenti_pip": float(a["pnl_pip"].mean())}


def _sifir_kesisim(xs, ys):
    for (x0, y0), (x1, y1) in zip(zip(xs, ys), zip(xs[1:], ys[1:])):
        if np.isfinite(y0) and np.isfinite(y1) and y0 >= 0 > y1:
            return float(x0 + (x1 - x0) * y0 / (y0 - y1))
    if ys and np.isfinite(ys[0]) and ys[0] < 0:
        return 0.0      # sıfır kaymada bile eksi
    return None         # ızgaranın sonunda da artı


def walk_forward(aile: str, liste: list[dict], yillik: dict, k: Kosucu, asgari: int) -> dict:
    """Genişleyen pencere: 2018 → Y−1 içinde seç, Y'de sına. Seçim şartı, örneklem içi
    seçimin altı yıllık asgari işlem sayısının yıl başına payıdır (her yıl ayrı sınanmaz)."""
    ilk = int(ONKAYIT["saglamlik"]["walk_forward_ilk_test_yili"])
    yillar = sorted({y for v in yillik.values() for y in v})
    asgari_yil = asgari / 6.0
    secimler, parcalar = {}, []
    for Y in [y for y in yillar if y >= ilk]:
        onceki = [y for y in yillar if y < Y]
        aday = []
        for p in liste:
            t = [yillik[_anahtar(p)][y] for y in onceki if y in yillik[_anahtar(p)]]
            sr, n = mk.sharpe_toplamdan(t)
            if n >= asgari_yil * len(onceki) and np.isfinite(sr):
                aday.append({"p": p, "is": {"sharpe": sr}})
        sec = _sec(aday)                          # örneklem içi seçimle aynı kural: tolerans içinde ızgaradaki ilk
        if sec is None:
            continue
        en_iyi = sec["p"]
        secimler[str(Y)] = _anahtar(en_iyi)
        isl = k.islem(aile, en_iyi)
        g = isl["gun"].to_numpy() if len(isl) else np.array([], dtype="datetime64[D]")
        yil = pd.DatetimeIndex(g.astype("datetime64[ns]")).year if len(isl) else np.array([])
        parcalar.append(isl[yil == Y] if len(isl) else isl)
    if not parcalar:
        return {"secimler": secimler, "sinanan_yillar": [], "ozet": None}
    birlesik = pd.concat(parcalar, ignore_index=True)
    # Gün kümesi yalnız SINANAN yıllardır: seçim yapılamayan bir yılın günleri sıfır sayılsaydı Sharpe seyrelir ve
    # "2020 → bugün" denen pencere aslında daha kısa olurdu.
    sinanan = sorted(int(y) for y in secimler)
    gunler = k.gun_tum[np.isin(pd.DatetimeIndex(k.gun_tum.astype("datetime64[ns]")).year, sinanan)]
    gr = mk.gunluk_r(birlesik, gunler)
    return {"secimler": secimler, "sinanan_yillar": sinanan, "ozet": mk.ozet(birlesik, gunler),
            "egri": {"gun": [str(x) for x in gunler], "r": [round(float(x), 4) for x in np.cumsum(gr)]}}


def _islem_kaydet(birim: str, cift: str, p: dict, isl: pd.DataFrame) -> None:
    yol = CIKTI / "islem" / birim
    yol.mkdir(parents=True, exist_ok=True)
    ad = _anahtar(p).replace("|", "__").replace("=", "-").replace(":", "")
    sutun = [c for c in isl.columns if c not in ("ust_alt",)]
    isl[sutun].to_parquet(yol / f"{cift}__{ad}.parquet", index=False)


def _json_yaz(yol: Path, veri: dict) -> None:
    def temiz(x):
        if isinstance(x, float):
            return None if not math.isfinite(x) else round(x, 6)
        if isinstance(x, (np.floating,)):
            return temiz(float(x))
        if isinstance(x, (np.integer,)):
            return int(x)
        if isinstance(x, (np.bool_,)):
            return bool(x)
        if isinstance(x, dict):
            return {str(k): temiz(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [temiz(v) for v in x]
        return x
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(temiz(veri), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    import haber_analiz as ha
    import veri as vr
    from gunluk import baglam_kur
    from takvim import olaylar_oku
    a = ay.oku()
    # --yalniz-haber: strateji birimleri koşmaz, yalnız haber analizleri (devam, patika, FOMC) yeniden ölçülür.
    birimler = ([] if "--yalniz-haber" in argv else [x for x in argv if x in BIRIMLER] or list(BIRIMLER))
    ciftler = [x for x in argv if x in a.ciftler] or list(a.ciftler)
    haber = "--haberli" in argv or "--yalniz-haber" in argv or not [x for x in argv if x in BIRIMLER]
    for cift in ciftler:
        t0 = time.monotonic()
        d = vr.oku(cift, a)
        b = baglam_kur(d, olaylar_oku(cift), tuple(a.haber_pencere_dk), orneklem=(a.baslangic, a.bitis))
        kos_ = Kosucu(b, a)
        print(f"{cift}: veri {len(d):,} dk · {len(b.olaylar)} olay · bağlam {time.monotonic() - t0:.0f} sn",
              flush=True)
        for birim in birimler:
            t1 = time.monotonic()
            s = birim_kos(birim, kos_)
            _json_yaz(CIKTI / "sonuc" / birim / f"{cift}.json", s)
            va, se = s.get("varsayilan_analiz") or {}, s.get("secilen_analiz") or {}
            print(f"  {birim:14s} {s['kombinasyon']:4d} komb · varsayılan OOS R {va.get('oos', {}).get('beklenti_r')}"
                  f" · seçilen OOS R {se.get('oos', {}).get('beklenti_r')} · {time.monotonic() - t1:.0f} sn",
                  flush=True)
        if haber:
            t1 = time.monotonic()
            h = ha.haber_analizi(b, cift, a.zaman_dilimleri, KAYMA_TEMEL, a.haber_kayma_pip,
                                 a.dis_baslangic.isoformat())
            ha.yaz(CIKTI / "sonuc" / "haber" / f"{cift}.json", h)
            print(f"  haber analizi · {sum(h['olay_sayisi'].values())} olay · {time.monotonic() - t1:.0f} sn",
                  flush=True)
    if haber:
        ha.yaz(CIKTI / "sonuc" / "haber" / "devam.json", ha.devam_toplu(a.ciftler))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
