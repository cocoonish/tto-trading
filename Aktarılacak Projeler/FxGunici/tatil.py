#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yerel tatiller: İngiltere'de banka tatilleri (England and Wales) ve ABD'de Federal Reserve Bankalarının kapalı
olduğu günler, bulutta indirilmiş resmî kaynaklardan (arsiv_tatil.py → veri/tatil/ham).

Stratejilere GİRMEZ. Kuralların tatil takvimi gunluk.TATIL_TAKVIM'dir (hafta içine düşen 25 Aralık ve 1 Ocak); öbür
yerel tatillerde kurallar sıradan gün gibi işlem açar. Bu liste o günleri yalnız BETİMLER (ön kayıt dışı):
veri denetiminin kapsam satırı (kalite.py) ve işlemlerin tatil günlerindeki sonucu (ders_olcum.tatil_betimi).

  İngiltere  gov.uk'un banka tatilleri dosyası, England and Wales bölümü (ikame günler ve tek seferlik tatiller dahil).
             Dosya 2019'da başlar; daha önceki yılın günleri aynı tatil kuralını izleyen kütüphane takviminden
             (holidays, GB/England) alınır ve satırında kaynağı yazılır. Kütüphane, resmî dosyayla örtüştüğü BÜTÜN
             yıllarda hafta içi günlerde resmî listeyle birebir aynı olmalıdır; ayrışırsa liste kurulmaz (kütüphane
             hafta sonuna düşen asıl günü de taşır — o günler işlem günü değildir, kıyasa girmez).
  ABD        OPM'nin federal tatil takvimi (federal çalışanların gözlem günleri) ve Fed'in kendi kuralı (K.8 sayfası):
             cumartesiye düşen tatilde Federal Reserve Bankaları önceki cuma AÇIKTIR (federal çalışanlar o cuma tatil
             yapar), pazara düşen tatilde sonraki pazartesi kapalıdır. Inauguration Day yalnız Washington bölgesindeki
             federal çalışanların tatilidir ve Fed'in listesinde yoktur. Sınamalar: OPM'nin her satırının haftanın
             günü kendi yazdığıyla aynı; sabit tarihli tatillerde gözlem günü federal kuralın verdiği gün; Fed'in K.8
             tablosu (yalnız yakın yıllar) örtüştüğü yıllarda aynı kapanış günlerini veriyor; OPM'nin gözlem günleri
             kütüphanenin federal takvimiyle aynı. Biri tutmazsa liste kurulmaz.

Ham dizin okunmadan önce dizinin kendi özleriyle (ozler.json) ve indirme künyesinin SHA-256 kaydıyla sınanır.

Koşum:  .venv/bin/python tatil.py          (iki listenin özeti ve sınamaların sonucu)
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import ozler

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "tatil" / "ham"

AYLAR = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December"]
AY = {m: i for i, m in enumerate(AYLAR, 1)}

#: Sabit tarihli federal tatiller (ay, gün): gözlem günü hafta sonuna göre kayar. Juneteenth 2021'de yasalaştı.
SABIT_TARIHLI = {"New Year's Day": (1, 1), "Juneteenth National Independence Day": (6, 19),
                 "Independence Day": (7, 4), "Veterans Day": (11, 11), "Christmas Day": (12, 25)}
#: Fed'in listesinde olmayan OPM satırları (yalnız Washington bölgesindeki federal çalışanlar).
FED_DISI = ("Inauguration Day",)

FED_KURALI = ("For holidays falling on Saturday, Federal Reserve Banks and Branches will be open the preceding Friday; "
              "however, the Board of Governors will be closed. For holidays falling on Sunday, all Federal Reserve "
              "offices will be closed the following Monday.")


class TatilHatasi(RuntimeError):
    """Ham kaynak okunamıyor ya da sınamalardan biri tutmuyor: liste kurulmaz."""


def _ad(s: str) -> str:
    """Tipografik kesme işaretini düz olana çevirir (OPM iki yazımı da kullanıyor)."""
    return s.replace("’", "'").strip()


def _metin(parca: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", parca))).strip()


@lru_cache(maxsize=1)
def kunye() -> dict:
    """İndirme künyesi; okumadan önce dizinin özleri ve künyenin SHA-256 kaydı sınanır."""
    try:
        ozler.sina(HAM)
    except ozler.OzHatasi as e:
        raise TatilHatasi(f"tatil arşivi özleriyle aynı değil: {e}") from None
    k = json.loads((HAM / "kunye.json").read_text(encoding="utf-8"))
    for ad, s in k["kaynak"].items():
        if not s.get("dosya"):
            raise TatilHatasi(f"{ad}: kaynak indirilmemiş ({s.get('durum')})")
        if ozler._oz(HAM / s["dosya"]) != s["sha256"]:
            raise TatilHatasi(f"{ad}: dosyanın özü indirme künyesindeki özle aynı değil")
    return k


def _kutuphane() -> dict:
    kunye()
    return json.loads((HAM / "holidays_kutuphanesi.json").read_text(encoding="utf-8"))


def ozu() -> str:
    """Ham dizinin tek dizgelik özü (dizinin özler dosyasının özü): veri denetimi ve ölçüm aynı listeyle mi koştu."""
    kunye()
    return ozler._oz(HAM / ozler.OZ_DOSYA)


# ───────────────────────────────────────────── İngiltere
@lru_cache(maxsize=1)
def ingiltere() -> tuple[dict, ...]:
    """England and Wales banka tatilleri (gözlem günleri): ({tarih, ad, kaynak}, …), tarih sırasıyla."""
    k = kunye()
    gov = json.loads((HAM / k["kaynak"]["gov_uk"]["dosya"]).read_text(encoding="utf-8"))["england-and-wales"]["events"]
    resmi = {e["date"]: e["title"] for e in gov}
    for t in resmi:
        if date.fromisoformat(t).weekday() >= 5:
            raise TatilHatasi(f"gov.uk: {t} hafta sonu (gözlem günü hafta içi olmalı)")
    lib = _kutuphane().get("ingiltere") or {}
    hafta_ici = {t: a for t, a in lib.items() if date.fromisoformat(t).weekday() < 5}
    resmi_yil = sorted({int(t[:4]) for t in resmi})
    ortak = sorted({int(t[:4]) for t in hafta_ici} & set(resmi_yil))
    for y in ortak:
        a = {t for t in resmi if t.startswith(f"{y}-")}
        b = {t for t in hafta_ici if t.startswith(f"{y}-")}
        if a != b:
            raise TatilHatasi(f"İngiltere {y}: kütüphane resmî listeyle ayrışıyor (yalnız resmî {sorted(a - b)}, "
                              f"yalnız kütüphane {sorted(b - a)})")
    out = [{"tarih": t, "ad": a, "kaynak": "gov_uk"} for t, a in resmi.items()]
    out += [{"tarih": t, "ad": a, "kaynak": "kutuphane"} for t, a in hafta_ici.items() if int(t[:4]) < resmi_yil[0]]
    return tuple(sorted(out, key=lambda x: x["tarih"]))


def ingiltere_sinama() -> dict:
    """Kütüphanenin resmî listeyle örtüştüğü yıllar ve kütüphaneden alınan yıllar (künye)."""
    liste = ingiltere()
    resmi = sorted({int(x["tarih"][:4]) for x in liste if x["kaynak"] == "gov_uk"})
    kut = sorted({int(x["tarih"][:4]) for x in liste if x["kaynak"] == "kutuphane"})
    lib = _kutuphane().get("ingiltere") or {}
    ortak = sorted({int(t[:4]) for t in lib} & set(resmi))
    return {"resmi_yil": [resmi[0], resmi[-1]], "kutuphane_yil": kut, "ortak_yil": ortak, "ayni": True,
            "kutuphane_surum": _kutuphane().get("surum")}


# ───────────────────────────────────────────── ABD
@lru_cache(maxsize=1)
def _opm() -> tuple[dict, ...]:
    """OPM tabloları (2018 ve sonrası): ({yil, ad, gozlem}, …). Aralık 31 tarihli Yılbaşı satırı tablonun yılının
    BİR ÖNCEKİ yılına aittir (1 Ocak cumartesiye düştüğünde OPM onu sonraki yılın tablosunda yazar)."""
    k = kunye()
    t = (HAM / k["kaynak"]["opm"]["dosya"]).read_text(encoding="utf-8")
    out = []
    for tb in re.findall(r"<table.*?</table>", t, re.S):
        cap = re.search(r"<caption[^>]*>(.*?)</caption>", tb, re.S)
        if not cap:
            continue
        m = re.match(r"(\d{4}) Holiday Schedule", _metin(cap.group(1)))
        if not m or int(m.group(1)) < 2018:
            continue
        y = int(m.group(1))
        for r in re.findall(r"<tr.*?</tr>", tb, re.S)[1:]:
            h = [_metin(x) for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
            mm = re.match(r"(\w+), (\w+) (\d+)", h[0])
            if not mm or mm.group(2) not in AY:
                raise TatilHatasi(f"OPM {y}: satır okunamadı: {h}")
            ad = _ad(h[1])
            yy = y - 1 if (AY[mm.group(2)] == 12 and ad == "New Year's Day") else y
            g = date(yy, AY[mm.group(2)], int(mm.group(3)))
            if g.strftime("%A") != mm.group(1):
                raise TatilHatasi(f"OPM {y}: {h[0]} — yazılan gün {g} tarihinin günü değil")
            out.append({"yil": y, "ad": ad, "gozlem": g})
    if not out:
        raise TatilHatasi("OPM: tatil tablosu bulunamadı")
    return tuple(out)


def _nominal(satir: dict) -> date:
    """Tatilin asıl günü: sabit tarihlilerde tablonun yılında (ay, gün); öbürlerinde gözlem günü."""
    if satir["ad"] in SABIT_TARIHLI:
        a, g = SABIT_TARIHLI[satir["ad"]]
        return date(satir["yil"], a, g)
    return satir["gozlem"]


def _fed_gunu(nominal: date) -> date | None:
    """Fed'in kuralı: cumartesi → kapanış yok (bankalar önceki cuma açık); pazar → sonraki pazartesi."""
    if nominal.weekday() == 5:
        return None
    if nominal.weekday() == 6:
        return nominal + timedelta(days=1)
    return nominal


@lru_cache(maxsize=1)
def abd() -> tuple[dict, ...]:
    """Federal Reserve Bankalarının kapalı olduğu hafta içi günler: ({tarih, ad, kaynak}, …), tarih sırasıyla."""
    out = []
    for s in _opm():
        if s["ad"] in FED_DISI:
            continue
        n = _nominal(s)
        # Federal çalışanların kuralı (OPM'nin dipnotu): cumartesi → önceki cuma, pazar → sonraki pazartesi.
        beklenen = n - timedelta(days=1) if n.weekday() == 5 else n + timedelta(days=1) if n.weekday() == 6 else n
        if s["gozlem"] != beklenen:
            raise TatilHatasi(f"OPM {s['yil']} {s['ad']}: gözlem günü {s['gozlem']} federal kuralın verdiği "
                              f"{beklenen} değil")
        f = _fed_gunu(n)
        if f is not None:
            out.append({"tarih": f.isoformat(), "ad": s["ad"], "kaynak": "opm"})
    out = sorted(out, key=lambda x: x["tarih"])
    _k8_sina(out)
    _kutuphane_abd_sina()
    return tuple(out)


def _k8() -> dict[int, list[date]]:
    """Fed'in K.8 tablosu: yıl → kapanış günleri (tablonun asıl günleri Fed'in kuralıyla kaydırılarak). Tablo asıl
    günü yazar; '*' cumartesiye, '**' pazara düşen tatili işaretler — işaret tarihin gününe karşı sınanır."""
    k = kunye()
    t = (HAM / k["kaynak"]["fed_k8"]["dosya"]).read_text(encoding="utf-8")
    if FED_KURALI not in _metin(t):
        raise TatilHatasi("K.8: Fed'in cumartesi/pazar kuralı sayfada beklenen biçimde yok")
    tb = re.findall(r"<table.*?</table>", t, re.S)
    if len(tb) != 1:
        raise TatilHatasi(f"K.8: {len(tb)} tablo (1 beklenir)")
    satirlar = [[_metin(x) for x in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S)]
                for r in re.findall(r"<tr.*?</tr>", tb[0], re.S)]
    yillar = [int(y) for y in satirlar[0][1:]]
    out: dict[int, list[date]] = {y: [] for y in yillar}
    for h in satirlar[1:]:
        for y, hucre in zip(yillar, h[1:]):
            m = re.match(r"(\w+) (\d+)(\**)$", hucre)
            if not m:
                raise TatilHatasi(f"K.8 {y}: hücre okunamadı: {hucre}")
            g = date(y, AY[m.group(1)], int(m.group(2)))
            isaret = {"": None, "*": 5, "**": 6}[m.group(3)]
            if (g.weekday() if g.weekday() >= 5 else None) != isaret:
                raise TatilHatasi(f"K.8 {y}: {hucre} — işaret tarihin gününe uymuyor")
            f = _fed_gunu(g)
            if f is not None:
                out[y].append(f)
    return out


def _k8_sina(liste: list[dict]) -> None:
    k8 = _k8()
    opm_yil = {int(x["tarih"][:4]) for x in liste}
    for y, gunler in k8.items():
        if y not in opm_yil:
            continue
        a = {x["tarih"] for x in liste if x["tarih"].startswith(f"{y}-")}
        b = {g.isoformat() for g in gunler}
        if a != b:
            raise TatilHatasi(f"ABD {y}: OPM + Fed kuralı K.8 tablosuyla ayrışıyor (yalnız OPM {sorted(a - b)}, "
                              f"yalnız K.8 {sorted(b - a)})")


def _kutuphane_abd_sina() -> None:
    """OPM'nin gözlem günleri (Inauguration Day hariç) kütüphanenin federal takvimiyle aynı mı (kütüphane hafta sonuna
    düşen asıl günü de taşır; o günler kıyasa girmez)."""
    lib = _kutuphane().get("abd") or {}
    lib_yil = {int(t[:4]) for t in lib}
    gozlem = {s["gozlem"].isoformat() for s in _opm() if s["ad"] not in FED_DISI}
    for y in sorted(lib_yil):
        a = {t for t in gozlem if t.startswith(f"{y}-")}
        b = {t for t in lib if t.startswith(f"{y}-") and date.fromisoformat(t).weekday() < 5}
        if a != b:
            raise TatilHatasi(f"ABD {y}: OPM kütüphaneyle ayrışıyor (yalnız OPM {sorted(a - b)}, "
                              f"yalnız kütüphane {sorted(b - a)})")


def abd_sinama() -> dict:
    liste = abd()
    k8 = _k8()
    opm_yil = sorted({int(x["tarih"][:4]) for x in liste})
    acik = [{"tarih": (_nominal(s) - timedelta(days=1)).isoformat(), "ad": s["ad"]}
            for s in _opm() if s["ad"] not in FED_DISI and _nominal(s).weekday() == 5]
    return {"opm_yil": [opm_yil[0], opm_yil[-1]], "k8_yil": sorted(y for y in k8 if y in set(opm_yil)),
            "ayni": True, "fed_kurali": FED_KURALI,
            # Federal çalışanların tatil yaptığı ama Fed bankalarının açık olduğu cumalar (asıl gün cumartesi)
            "fed_acik_cuma": sorted(acik, key=lambda x: x["tarih"])}


# ───────────────────────────────────────────── pencere
def hafta_ici(liste, bas: date, bit: date, haric: set[tuple[int, int]] = frozenset()) -> list[dict]:
    """Penceredeki hafta içi tatiller; `haric`: (ay, gün) — kuralların zaten işlem günü saymadığı günler
    (gunluk.TATIL_TAKVIM)."""
    out = []
    for x in liste:
        g = date.fromisoformat(x["tarih"])
        if bas <= g <= bit and g.weekday() < 5 and (g.month, g.day) not in haric:
            out.append(x)
    return out


def ozet(bas: date, bit: date, haric: set[tuple[int, int]] = frozenset()) -> dict:
    ing = hafta_ici(ingiltere(), bas, bit, haric)
    ab = hafta_ici(abd(), bas, bit, haric)
    ikisi = sorted({x["tarih"] for x in ing} & {x["tarih"] for x in ab})
    return {"ingiltere": ing, "abd": ab, "ikisi": ikisi, "ingiltere_sinama": ingiltere_sinama(),
            "abd_sinama": abd_sinama(), "zaman": kunye().get("zaman"),
            "kaynak": {ad: {"url": s["url"], "sha256": s["sha256"]} for ad, s in kunye()["kaynak"].items()}}


def main(argv: list[str]) -> int:
    import ayar as ay
    from gunluk import TATIL_TAKVIM
    a = ay.oku()
    o = ozet(a.baslangic, a.bitis, set(TATIL_TAKVIM))
    print(f"İngiltere: {len(o['ingiltere'])} hafta içi gün ({a.baslangic} → {a.bitis}; 25 Aralık ve 1 Ocak hariç) · "
          f"kütüphaneden: {o['ingiltere_sinama']['kutuphane_yil']} · resmîyle örtüşen yıllar "
          f"{o['ingiltere_sinama']['ortak_yil'][0]}–{o['ingiltere_sinama']['ortak_yil'][-1]}: aynı")
    print(f"ABD (Fed): {len(o['abd'])} hafta içi gün · K.8 ile örtüşen yıllar {o['abd_sinama']['k8_yil']}: aynı · "
          f"Fed'in açık olduğu cuma (asıl gün cumartesi): {len(o['abd_sinama']['fed_acik_cuma'])}")
    print(f"İkisi birden: {len(o['ikisi'])} gün {o['ikisi']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
