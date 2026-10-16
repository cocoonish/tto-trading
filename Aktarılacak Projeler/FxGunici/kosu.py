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
from pathlib import Path

import numpy as np
import pandas as pd

import ayar as ay
import metrik as mk
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

    def islem(self, aile: str, p: dict, kayma: float = KAYMA_TEMEL) -> pd.DataFrame:
        sin, ofset = self.sinyal(aile, p)
        stop_turu = p.get("stop_turu", "yok")
        if ofset is None:           # haber: çıpa satır başına
            return sh.kos_haber(self.b, sin, int(p["tf"]), stop_turu, p.get("hedef", "yok"),
                                kayma, self.a.haber_kayma_pip, HABER_ZAMAN_MUM)
        return kos(self.b, sin, int(p["tf"]), ofset, stop_turu, p.get("hedef", "yok"),
                   kayma, self.a.haber_kayma_pip, ZAMAN_MUM)

    def bol(self, isl: pd.DataFrame):
        if len(isl) == 0:
            return isl, isl
        g = isl["gun"].to_numpy()
        return isl[g <= np.datetime64(self.a.ic_bitis)], isl[g >= np.datetime64(self.a.dis_baslangic)]


def _hukum(m_oos: dict, ry: dict) -> str:
    esik = float(ONKAYIT["hukum"]["rastgele_esik_yuzdelik"])
    r = m_oos.get("beklenti_r", float("nan"))
    if not np.isfinite(r) or m_oos.get("n", 0) < 20:
        return "olculemedi"
    if r <= 0:
        return "calismiyor"
    if m_oos.get("ga_alt", -1) > 0 and ry.get("yuzdelik", 0) >= esik:
        return "calisiyor"
    return "zayif"


def _maliyet_bayragi(m: dict) -> bool:
    return bool(m.get("ga_brut_alt", -1) > 0 and m.get("beklenti_r", 1) <= 0)


def birim_kos(birim: str, kosucu: Kosucu, ayrinti: bool = True) -> dict:
    tanim = BIRIMLER[birim]
    aile = tanim["aile"]
    liste, varsayilan = izgara(birim)
    k = kosucu
    satirlar = []
    yillik = {}
    t0 = time.monotonic()
    for p in liste:
        isl = k.islem(aile, p)
        ic, dis = k.bol(isl)
        mi = mk.ozet(ic, k.gun_is, bootstrap=False)
        md = mk.ozet(dis, k.gun_oos, bootstrap=False)
        ss = mk.gunluk_r(ic, k.gun_is)
        satirlar.append({"p": p, "anahtar": _anahtar(p), "is": mi, "oos": md,
                         "sr_gunluk_is": float(ss.mean() / ss.std(ddof=1)) if ss.std(ddof=1) > 0 else float("nan")})
        yillik[_anahtar(p)] = mk.yil_toplamlari(isl, k.gun_tum)
    asgari = int(ONKAYIT["secim"]["asgari_islem_haber" if tanim.get("haber") else "asgari_islem"])
    adaylar = [s for s in satirlar if s["is"]["n"] >= asgari and np.isfinite(s["is"]["sharpe"])]
    secilen = max(adaylar, key=lambda s: s["is"]["sharpe"]) if adaylar else None
    sonuc = {"birim": birim, "aile": aile, "kombinasyon": len(liste), "varsayilan": varsayilan,
             "izgara": [{"anahtar": s["anahtar"], "p": s["p"],
                         "is": {x: s["is"].get(x) for x in ("n", "beklenti_r", "beklenti_pip", "sharpe", "isabet")},
                         "oos": {x: s["oos"].get(x) for x in ("n", "beklenti_r", "beklenti_pip", "sharpe", "isabet")}}
                        for s in satirlar],
             "secilen": secilen["p"] if secilen else None,
             "sure_izgara_sn": round(time.monotonic() - t0, 1)}
    if not ayrinti:
        return sonuc
    sr_denemeler = np.array([s["sr_gunluk_is"] for s in satirlar])
    for ad, p in (("varsayilan", varsayilan), ("secilen", secilen["p"] if secilen else None)):
        if p is None:
            sonuc[f"{ad}_analiz"] = None
            continue
        sonuc[f"{ad}_analiz"] = derin(birim, aile, p, k, sr_denemeler if ad == "secilen" else None, yillik,
                                      ornek=(ad == "varsayilan"))
    sonuc["walk_forward"] = walk_forward(aile, liste, yillik, k, asgari)
    return sonuc


def derin(birim: str, aile: str, p: dict, k: Kosucu, sr_denemeler, yillik, ornek: bool = False) -> dict:
    isl = k.islem(aile, p)
    ic, dis = k.bol(isl)
    out = {"p": p,
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
    # başabaş: kayma ızgarasında beklenti_pip(s) = 0'ın doğrusal kestirimi (dolum başına pip)
    xs = sorted(float(s) for s in maliyet)
    ys = [maliyet[str(s) if str(s) in maliyet else s]["tum"]["beklenti_pip"] for s in xs]
    out["basabas_kayma_pip"] = _sifir_kesisim(xs, ys)
    out["basabas_ek_maliyet_pip"] = maliyet[str(0.0)]["tum"]["beklenti_pip"] if str(0.0) in maliyet else None
    # rastgele yön (örneklem dışı ve bütün dönem)
    out["rastgele"] = {"oos": sg.rastgele_yon(k.b, dis, int(p["tf"]), k.sinyal(aile, p)[1], KAYMA_TEMEL,
                                              k.a.haber_kayma_pip),
                       "tum": sg.rastgele_yon(k.b, isl, int(p["tf"]), k.sinyal(aile, p)[1], KAYMA_TEMEL,
                                              k.a.haber_kayma_pip)}
    # deflated Sharpe (yalnız ızgaradan SEÇİLEN için anlamlı; varsayılanda PSR)
    gr_is = mk.gunluk_r(ic, k.gun_is)
    sr_is = float(gr_is.mean() / gr_is.std(ddof=1)) if gr_is.std(ddof=1) > 0 else float("nan")
    out["dsr"] = sg.dsr(sr_is, sr_denemeler, gr_is) if sr_denemeler is not None else \
        {**sg.dsr(sr_is, np.array([sr_is, sr_is]), gr_is), "n_deneme": 1}
    # hüküm
    out["hukum"] = _hukum(out["oos"], out["rastgele"]["oos"])
    out["hukum_tum"] = _hukum(out["tum"], out["rastgele"]["tum"])
    out["maliyet_yiyor"] = _maliyet_bayragi(out["tum"])
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
    if "olay" in a.columns:
        out["haber_kirilim"] = haber_kirilim(a, icm)
    # günlük birikimli eğri (figür)
    gr = mk.gunluk_r(isl, k.gun_tum)
    out["egri"] = {"gun": [str(x) for x in k.gun_tum], "r": [round(float(x), 4) for x in np.cumsum(gr)]}
    if ornek:
        out["ornek"] = ornek_gunler(k, p, isl, k.sinyal(aile, p)[1])
    _islem_kaydet(birim, k.b.d.cift, p, isl)
    return out


def ornek_gunler(k: Kosucu, p: dict, isl: pd.DataFrame, ofset_sabit: int | None) -> list[dict]:
    """Ders figürünün örnek günleri: örneklem DIŞININ en son kazanan ve en son kaybeden işlemi.

    Seçim kuralı sabittir (en son tarih), yani örnek sonuca bakılarak seçilmez. Gün, stratejinin
    kendi zaman diliminin ÇIPALI mumlarıyla (orta fiyat, nokta) ve işlemin seviyeleriyle yazılır:
    giriş ve çıkış dakikası ile fiyatı (yürütülen bid/ask), stop, hedef ve stratejinin referans
    seviyeleri (`ust`, `alt`, varsa `seviye`)."""
    a = mk.alinan(isl)
    if len(a) == 0:
        return []
    dis = a[a["gun"].to_numpy() >= np.datetime64(k.a.dis_baslangic)]
    out = []
    for etiket, x in (("kazanan", dis[dis["pnl_pip"] > 0]), ("kaybeden", dis[dis["pnl_pip"] <= 0])):
        if not len(x):
            continue
        s = x.iloc[-1]
        tf = int(p["tf"])
        ofset = int(s["ofset"]) if ofset_sabit is None else int(ofset_sabit)
        m = k.b.mumlar(tf, ofset)
        gk = int(s["gun_k"])
        t0 = int(k.b.g.gun_basi[gk])
        j0, j1 = np.searchsorted(m.bt, [t0, t0 + 86400])
        sayi = lambda v: None if v is None or not np.isfinite(float(v)) else round(float(v), 1)  # noqa: E731
        out.append({
            "etiket": etiket, "gun": str(s["gun"])[:10], "tf": tf, "ofset": ofset,
            "mum": {"t": [int(v) for v in m.bt[j0:j1]], "o": [round(float(v), 1) for v in m.o[j0:j1]],
                    "h": [round(float(v), 1) for v in m.h[j0:j1]], "l": [round(float(v), 1) for v in m.l[j0:j1]],
                    "c": [round(float(v), 1) for v in m.c[j0:j1]]},
            "islem": {"yon": int(s["yon"]), "giris_t": int(s["giris_t"]), "cikis_t": int(s["cikis_t"]),
                      "giris_f": sayi(s["giris_f"]), "cikis_f": sayi(s["cikis_f"]), "stop": sayi(s["stop"]),
                      "hedef": sayi(s["hedef"]), "neden": int(s["neden"]), "r": round(float(s["r"]), 3),
                      "pnl_pip": round(float(s["pnl_pip"]), 2), "sinyal_t": int(s["sinyal_t"]) if "sinyal_t" in s
                      else None, "ust": sayi(s.get("ust")), "alt": sayi(s.get("alt")),
                      "seviye": sayi(s.get("seviye")), "olay": str(s["olay"]) if "olay" in s else None},
        })
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
        en_iyi, en_sr = None, -np.inf
        for p in liste:
            t = [yillik[_anahtar(p)][y] for y in onceki if y in yillik[_anahtar(p)]]
            sr, n = mk.sharpe_toplamdan(t)
            if n >= asgari_yil * len(onceki) and np.isfinite(sr) and sr > en_sr:
                en_iyi, en_sr = p, sr
        if en_iyi is None:
            continue
        secimler[str(Y)] = _anahtar(en_iyi)
        isl = k.islem(aile, en_iyi)
        g = isl["gun"].to_numpy() if len(isl) else np.array([], dtype="datetime64[D]")
        yil = pd.DatetimeIndex(g.astype("datetime64[ns]")).year if len(isl) else np.array([])
        parcalar.append(isl[yil == Y] if len(isl) else isl)
    if not parcalar:
        return {"secimler": secimler, "ozet": None}
    birlesik = pd.concat(parcalar, ignore_index=True)
    gunler = k.gun_tum[pd.DatetimeIndex(k.gun_tum.astype("datetime64[ns]")).year >= ilk]
    gr = mk.gunluk_r(birlesik, gunler)
    return {"secimler": secimler, "ozet": mk.ozet(birlesik, gunler),
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
    birimler = [x for x in argv if x in BIRIMLER] or list(BIRIMLER)
    ciftler = [x for x in argv if x in a.ciftler] or list(a.ciftler)
    haber = "--haberli" in argv or not [x for x in argv if x in BIRIMLER]
    for cift in ciftler:
        t0 = time.monotonic()
        d = vr.oku(cift, a)
        b = baglam_kur(d, olaylar_oku(cift), tuple(a.haber_pencere_dk))
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
        ha.yaz(CIKTI / "sonuc" / "haber" / "devam.json", ha.devam_toplu())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
