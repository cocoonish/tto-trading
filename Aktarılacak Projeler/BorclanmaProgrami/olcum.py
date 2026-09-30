#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BORÇLANMA PROGRAMI (30.09.2026) — yazının BÜTÜN sayılarını üreten tek yer.

Girdi yalnız `veri/` (yayım gününün dondurulmuş kopyaları; bkz. arsivle.py).
Çıktı `veri/olcum.json`; tüketicisi iki: `sekil.py` figürleri buradan çizer,
`dogrula.py` yayımlanan metni buna karşı sınar. İki ayrı hesap bir gün
sessizce ayrışır; sayıyı üreten yer tektir.

ÜÇ SÖZLEŞME, ADIYLA:

· BELGENİN SAYISI BELGEDEN OKUNUR. Finansman programı, ödeme takvimi ve ihraç
  takvimi strateji belgesinin arşivlenmiş metninden `belge.py` ile
  ayrıştırılır; hattın defterine bakılmaz. Hattın defteri yalnız hedefi
  (ihale + kamuya satış) tutar ve bu yazının asıl sorusu defterin DIŞINDA
  kalan satırda (doğrudan satışlar) duruyor.

· KARŞI OLGU AYNI YÖNTEMLE KURULUR. Eski ve yeni takvimin ihale satırları
  aynı kıyas tahminiyle ağırlıklandırılır (`kiyas.json`, bugünkü yöntem).
  Yöntemdeki bir değişiklik Hazine'nin kararı sanılmasın diye başlık payı
  (üç ayın toplamı) ile AYNI AY kıyası ayrı ayrı yazılır.

· KESİN AY İLK AYDIR. Her belge üç ay kapsar; yalnız ilk ayın takvimi
  kesindir, izleyen ikisi geçicidir. Tarihsel seriler her ayın KESİN
  planından (dönemi o ayla başlayan belgeden) kurulur.

Koşum:  python3 olcum.py
"""
from __future__ import annotations

import gzip
import io
import json
import re
import statistics as ist
import sys
from pathlib import Path

import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
sys.path.insert(0, str(BURASI))
import belge  # noqa: E402

ONCEKI_YAZI = KOK / "site/src/content/analiz/borclanma-programi-vade-2026-08-31.mdx"
DEGISKEN = {"TLREF'e Endeksli Devlet Tahvili", "Değişken Faizli Devlet Tahvili"}
NOMINAL_SABIT = {"Hazine Bonosu", "Sabit Kuponlu Devlet Tahvili", "Kuponsuz Devlet Tahvili"}
REEL = {"TÜFE'ye Endeksli Devlet Tahvili"}
REPRICE_DEGISKEN = 0.25            # değişken kuponun yenilenme süresi (yıl) — vekil
GERCEKLESME_VARSAYIMI = 0.92       # hattın planı ölçeklediği oran (takvim dosyasında yazılı)
MALIYET_PENCERE_AY = 4
KOVA = [(0, 1, "≤1 yıl"), (1, 3, "1–3 yıl"), (3, 6, "3–6 yıl"), (6, 100, "6 yıl+")]
PLAN_AYLARI = ["2026-10", "2026-11", "2026-12"]


def _oku(ad: str) -> bytes:
    return gzip.decompress((VERI / f"{ad}.gz").read_bytes())


def _csv(ad: str) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(_oku(ad)), encoding="utf-8-sig")


def _r(x, b=2):
    return None if x is None else round(float(x), b)


def _vade_yil(terim: str) -> float | None:
    return belge._vade_yil(str(terim).replace("Yıl /", "Yıl / ").replace("Ay /", "Ay / "))


def _kova(v: float) -> str:
    for a, b, ad in KOVA:
        if a < v <= b or (a == 0 and v <= b):
            return ad
    return KOVA[-1][2]


# ───────────────────────────────────────────────────────── 1 · belgeler
def belgeler() -> dict:
    arsiv = json.loads(_oku("strateji_arsivi.json"))
    B = sorted((belge.oku(k) for k in arsiv if "metin" in k), key=lambda b: b["duyuru"])
    yeni = next(b for b in B if b["donem"] == ("2026-10", "2026-12"))
    eski = next(b for b in B if b["donem"] == ("2026-09", "2026-11"))
    kesin = {b["donem"][0]: b for b in B}
    return {"hepsi": B, "yeni": yeni, "eski": eski, "kesin": kesin,
            "indirilemeyen": [k["baslik"].replace("&#8211;", "–") for k in arsiv if "metin" not in k],
            "belge_sayisi": len(arsiv)}


def finansman_ozet(f: dict) -> dict:
    """Bir ayın finansman satırlarından türetilen oranlar."""
    ib, isv = f["ic_borclanma"], f["ic_servis"]
    return {**f,
            "hedef": _r(f["ihale"] + f["kamu"], 1),
            "cevirme": _r(ib / isv * 100, 1) if isv else None,
            "dogrudan_pay": _r(f["dogrudan"] / ib * 100, 1) if ib else None,
            "ihale_pay": _r(f["ihale"] / ib * 100, 1) if ib else None,
            "kamu_pay": _r(f["kamu"] / ib * 100, 1) if ib else None,
            "faiz_pay": _r(f["ic_faiz"] / isv * 100, 1) if isv else None,
            "bdk_pay": _r(f["borclanma_disi"] / f["odemeler"] * 100, 1) if f["odemeler"] else None}


def program(D: dict) -> dict:
    yeni = {a: finansman_ozet(v) for a, v in D["yeni"]["finansman"].items()}
    eski = {a: finansman_ozet(v) for a, v in D["eski"]["finansman"].items()}
    fark = {}
    for a in ("2026-10", "2026-11"):
        fark[a] = {k: _r(yeni[a][k] - eski[a][k], 1) for k in
                   ("ihale", "dogrudan", "kamu", "hedef", "ic_borclanma", "ic_servis",
                    "ic_anapara", "ic_faiz", "dis_servis", "borclanma_disi", "odemeler")}
        fark[a]["hedef_yuzde"] = _r((yeni[a]["hedef"] / eski[a]["hedef"] - 1) * 100, 1)
    top = {k: _r(sum(yeni[a][k] for a in PLAN_AYLARI), 1) for k in
           ("ihale", "dogrudan", "kamu", "hedef", "ic_borclanma", "ic_servis", "ic_anapara",
            "ic_faiz", "dis_servis", "dis_anapara", "dis_faiz", "borclanma_disi", "odemeler")}
    top["cevirme"] = _r(top["ic_borclanma"] / top["ic_servis"] * 100, 1)
    top["faiz_pay"] = _r(top["ic_faiz"] / top["ic_servis"] * 100, 1)
    top["dogrudan_pay"] = _r(top["dogrudan"] / top["ic_borclanma"] * 100, 1)
    top["ihale_pay"] = _r(top["ihale"] / top["ic_borclanma"] * 100, 1)
    top["kamu_pay"] = _r(top["kamu"] / top["ic_borclanma"] * 100, 1)
    top["bdk_pay"] = _r(top["borclanma_disi"] / top["odemeler"] * 100, 1)
    return {"yeni": yeni, "eski": eski, "fark": fark, "ceyrek": top}


def odeme_gunleri(D: dict) -> dict:
    """Ödeme takviminin iki sürümü ve Ekim'in gün gün farkı."""
    y = {g["gun"]: g for g in D["yeni"]["odemeler"]["gunler"]}
    e = {g["gun"]: g for g in D["eski"]["odemeler"]["gunler"]}
    ekim = []
    for gun in sorted(set(y) | set(e)):
        if not gun.startswith("2026-10"):
            continue
        ekim.append({"gun": gun, "yeni": _r(y.get(gun, {}).get("toplam", 0) / 1000, 1),
                     "eski": _r(e.get(gun, {}).get("toplam", 0) / 1000, 1),
                     "fark": _r((y.get(gun, {}).get("toplam", 0) - e.get(gun, {}).get("toplam", 0)) / 1000, 1)})
    aylar = {a: {"toplam": _r(v["toplam"] / 1000, 1), "piyasa": _r(v["piyasa"] / 1000, 1),
                 "kamu": _r(v["kamu"] / 1000, 1), "gun": v["gun_sayisi"]}
             for a, v in D["yeni"]["odemeler"]["aylar"].items()}
    en_buyuk = max(D["yeni"]["odemeler"]["gunler"], key=lambda g: g["toplam"])
    ekim_top = D["yeni"]["odemeler"]["aylar"]["2026-10"]["toplam"]
    ekim_gun = [g for g in D["yeni"]["odemeler"]["gunler"] if g["gun"].startswith("2026-10")]
    diger = sum(g["toplam"] for g in ekim_gun if g["gun"] != en_buyuk["gun"]) / 1000
    # 7 Ekim valörlü olan yalnız takvimin satırları: ihale + doğrudan satış.
    # Kamuya satışın valörü belgede yok; o gün kasaya girdiği varsayılmaz.
    f10 = D["yeni"]["finansman"]["2026-10"]
    ekim_7 = f10["ihale"] + f10["dogrudan"]
    return {"ekim_diger_gunler_mlr": _r(diger, 1),
            "ekim_7_program_mlr": _r(ekim_7, 1),
            "ekim_7_fazla_mlr": _r(ekim_7 - en_buyuk["toplam"] / 1000, 1),
            "yeni_gunler": [{"gun": g["gun"], "toplam": _r(g["toplam"] / 1000, 1)}
                            for g in D["yeni"]["odemeler"]["gunler"]],
            "ekim": ekim, "aylar": aylar,
            "en_buyuk_gun": en_buyuk["gun"], "en_buyuk_mlr": _r(en_buyuk["toplam"] / 1000, 1),
            "en_buyuk_pay_ekim": _r(en_buyuk["toplam"] / ekim_top * 100, 1)}


# ───────────────────────────────────────────────────────── 2 · takvim
def _takvim_sat(b: dict, aylar: list[str]) -> list[dict]:
    return [r for r in b["takvim"] if r["ihale"][:7] in aylar]


def takvim_farki(D: dict) -> dict:
    """Ekim ve Kasım satırlarının iki belgedeki hâli: kalan, kayan, eklenen, çıkan.

    Eşleştirme AY İÇİNDE yapılır: aynı kâğıt (tür + itfa) iki ayda birden
    ihraç edilebiliyor (16.04.2031 hem Ekim'de hem Kasım'da) ve ay gözetmeyen
    bir eşleştirme Ekim satırını Kasım'ınkiyle eşleyip "kaydı" derdi."""
    satirlar = []
    for ay in ("2026-10", "2026-11"):
        E, Y = _takvim_sat(D["eski"], [ay]), _takvim_sat(D["yeni"], [ay])
        anahtar = lambda r: (r["senet"], r["itfa"])  # noqa: E731
        e_k, y_k = {anahtar(r): r for r in E}, {anahtar(r): r for r in Y}
        assert len(e_k) == len(E) and len(y_k) == len(Y), f"{ay}: aynı ayda aynı kâğıt iki kez"
        for k in sorted(set(e_k) | set(y_k), key=lambda k: ((y_k.get(k) or e_k.get(k))["ihale"], k)):
            e, y = e_k.get(k), y_k.get(k)
            if e and y:
                durum = "aynı" if e["ihale"] == y["ihale"] else "kaydı"
            else:
                durum = "eklendi" if y else "çıktı"
            satirlar.append({"ay": ay, "senet": k[0], "itfa": k[1], "durum": durum,
                             "eski_gun": e["ihale"] if e else None, "yeni_gun": y["ihale"] if y else None,
                             "eski_terim": e["terim"] if e else None, "yeni_terim": y["terim"] if y else None,
                             "yontem": (y or e)["yontem"], "dogrudan": (y or e)["dogrudan"]})
    Y = _takvim_sat(D["yeni"], ["2026-10", "2026-11"])
    aralik = _takvim_sat(D["yeni"], ["2026-12"])
    ekim_ihale = [r for r in Y if r["ihale"].startswith("2026-10") and not r["dogrudan"]]
    ekim_valor = sorted({r["valor"] for r in Y if r["ihale"].startswith("2026-10")})
    eski_ekim_valor = sorted({r["valor"] for r in _takvim_sat(D["eski"], ["2026-10"])})
    return {"satirlar": satirlar, "aralik": aralik, "ekim_ihale_gunleri":
            sorted({r["ihale"] for r in ekim_ihale}), "ekim_valor": ekim_valor,
            "eski_ekim_valor": eski_ekim_valor,
            "eski_ekim_ihale_gunleri": sorted({r["ihale"] for r in _takvim_sat(D["eski"], ["2026-10"])
                                               if not r["dogrudan"]}),
            # ayın ihale ve doğrudan satış satırlarının valör günleri (kamuya satışın valörü belgede yok)
            "valor_aylik": {a: sorted({r["valor"] for r in D["yeni"]["takvim"] if r["ihale"][:7] == a})
                            for a in PLAN_AYLARI},
            "yeni_satir": len(D["yeni"]["takvim"]),
            "yeni_ihale": sum(1 for r in D["yeni"]["takvim"] if not r["dogrudan"]),
            "yeni_dogrudan": sum(1 for r in D["yeni"]["takvim"] if r["dogrudan"])}


def takvim_tarihce(D: dict) -> dict:
    """Kesin takvimlerde: ihale günleri, ay içindeki son ihale, sonraki aya boşluk;
    bonosuz ardışık ay; kuponsuz tahvil vadeleri."""
    import datetime as dt
    plan = {a: [r for r in b["takvim"] if r["ihale"][:7] == a] for a, b in D["kesin"].items()}
    for a in ("2026-11", "2026-12"):
        plan[a] = [r for r in D["yeni"]["takvim"] if r["ihale"][:7] == a]
    aylar = sorted(plan)
    gunler = {a: sorted({r["ihale"] for r in plan[a] if not r["dogrudan"]}) for a in aylar}
    gunler = {a: g for a, g in gunler.items() if g}
    ay_s = sorted(gunler)
    kayit = []
    for i, a in enumerate(ay_s):
        son = dt.date.fromisoformat(gunler[a][-1])
        ertesi = gunler[ay_s[i + 1]][0] if i + 1 < len(ay_s) else None
        kayit.append({"ay": a, "gun_sayisi": len(gunler[a]), "ilk": int(gunler[a][0][8:]),
                      "son": son.day,
                      "bosluk": (dt.date.fromisoformat(ertesi) - son).days if ertesi else None})
    # Tarihsel ölçü yalnız KESİN aylardan: Ekim 2026'dan önceki aylar ve
    # boşlukları (bir sonraki ayın ilk ihalesi de o ayın kesin takviminden).
    onceki = [k for k in kayit if k["ay"] < "2026-10" and k["bosluk"] is not None]
    bos = [k["bosluk"] for k in onceki]
    ekim = next(k for k in kayit if k["ay"] == "2026-10")
    kesin_aylar = [k for k in kayit if k["ay"] <= "2026-10"]
    ilk_hafta = [k["ay"] for k in kesin_aylar if k["son"] <= 7]
    # bonosuz ardışık plan ayı
    kosu, c, en_uzun = {}, 0, (None, 0)
    for a in aylar:
        c = c + 1 if not any("Bono" in r["senet"] for r in plan[a]) else 0
        kosu[a] = c
        if c > en_uzun[1]:
            en_uzun = (a, c)
    kupon = [{"ay": a, "terim": r["terim"], "gun": int(re.search(r"/\s*(\d+)", r["terim"]).group(1)),
              "yontem": r["yontem"], "bono_ayni_ay": any("Bono" in x["senet"] for x in plan[a])}
             for a in aylar for r in plan[a] if "Kuponsuz" in r["senet"]]
    kupon_onceki = [k for k in kupon if k["ay"] != "2026-12"]
    # döviz/altın cinsi doğrudan satışlar: kesin takvimlerde hangi aylarda
    dvz = {a: sorted({r["senet"] for r in plan[a] if r["dogrudan"] and
                      any(w in r["senet"] for w in ("ABD Doları", "Avro", "Altın"))})
           for a in aylar}
    ekim_itfa, gor = [], set()
    for b in D["hepsi"]:
        for r in b["takvim"]:
            k = (r["ihale"], r["senet"], r["itfa"])
            if r["dogrudan"] and r["itfa"].startswith("2026-10") and k not in gor:
                gor.add(k)
                ekim_itfa.append({"ihale": r["ihale"], "valor": r["valor"], "itfa": r["itfa"],
                                  "senet": r["senet"], "terim": r["terim"]})
    ekim_itfa.sort(key=lambda r: (r["itfa"], r["senet"]))
    usd_tahvil = [a for a in aylar if any(r["senet"] == "ABD Doları Cinsi Devlet Tahvili"
                                          and r["dogrudan"] for r in plan[a])]
    # Geçici bir ayın ilk ihale günü, kesin plana geçerken ne sıklıkla değişiyor:
    # Kasım'ın 9 Kasım'ı (ve Ekim'in 34 günlük boşluğu) bugün geçicidir.
    gecis = []
    for a in sorted(D["kesin"]):
        y_, m_ = int(a[:4]), int(a[5:])
        onceki_ay = f"{y_ - 1}-12" if m_ == 1 else f"{y_}-{m_ - 1:02d}"
        if onceki_ay not in D["kesin"] or a > "2026-10":
            continue
        g_ = sorted({r["ihale"] for r in D["kesin"][onceki_ay]["takvim"] if r["ihale"][:7] == a and not r["dogrudan"]})
        k_ = sorted({r["ihale"] for r in D["kesin"][a]["takvim"] if r["ihale"][:7] == a and not r["dogrudan"]})
        if g_ and k_:
            gecis.append((a, (dt.date.fromisoformat(k_[0]) - dt.date.fromisoformat(g_[0])).days))
    bono_ay = {a: any("Bono" in r["senet"] for r in plan[a]) for a in aylar}
    kup_aylar = [k["ay"] for k in kupon_onceki]
    pencere = [a for a in aylar if kup_aylar and kup_aylar[0] <= a <= kup_aylar[-1]]
    return {"kayit": kayit, "kesin_ay_sayisi": len(kesin_aylar),
            "bosluk_medyan": ist.median(bos), "bosluk_maks": max(bos), "bosluk_n": len(bos),
            "bosluk_maks_aylar": [k["ay"] for k in onceki if k["bosluk"] == max(bos)],
            "bosluk_ekim_ve_ustu": sum(1 for x in bos if x >= ekim["bosluk"]),
            "ekim_bosluk": ekim["bosluk"], "ekim_son": ekim["son"],
            "ilk_haftada_biten": ilk_hafta,
            "bonosuz_kosu": {a: kosu[a] for a in aylar if a >= "2026-01"},
            "bonosuz_en_uzun": {"bitis": en_uzun[0], "ay": en_uzun[1]},
            "kuponsuz": kupon, "kuponsuz_n_onceki": len(kupon_onceki),
            "kuponsuz_maks_gun_onceki": max(k["gun"] for k in kupon_onceki),
            "kuponsuz_bonosuz_ay": sum(1 for k in kupon_onceki if not k["bono_ayni_ay"]),
            "doviz_altin": {a: v for a, v in dvz.items() if a >= "2024-01"},
            "usd_tahvil_aylari": usd_tahvil, "ekim_itfa_dogrudan": ekim_itfa,
            "doviz_altin_2026_ay": sum(1 for a in aylar if "2026-01" <= a <= "2026-09" and dvz[a]),
            "doviz_altin_2026_bos": [a for a in aylar if "2026-01" <= a <= "2026-09" and not dvz[a]],
            "ilk_gun_gecis": {"n": len(gecis), "ayni": sum(1 for _, f in gecis if f == 0),
                              "bir_gun": sum(1 for _, f in gecis if abs(f) == 1),
                              "bir_hafta": sum(1 for _, f in gecis if abs(f) == 7),
                              "one_cekilen": sum(1 for _, f in gecis if f <= -7),
                              "diger": sum(1 for _, f in gecis if abs(f) not in (0, 1, 7))},
            "son_gun_10_ve_once": [k["ay"] for k in kesin_aylar if k["son"] <= 10],
            "kuponsuz_bonolu_ay": sum(1 for k in kupon_onceki if k["bono_ayni_ay"]),
            "bonosuz_ay_pay": {"n": len(pencere), "bonosuz": sum(1 for a in pencere if not bono_ay[a]),
                               "bas": pencere[0] if pencere else None, "son": pencere[-1] if pencere else None}}


# ───────────────────────────────────────────────── 3 · tarihsel finansman
def finansman_tarihce(D: dict) -> dict:
    seri = {}
    for a, b in sorted(D["kesin"].items()):
        seri[a] = finansman_ozet(b["finansman"][a])
    aylar = sorted(seri)
    ek = seri["2026-10"]

    def sira(anahtar):
        v = [seri[a][anahtar] for a in aylar]
        return {"deger": ek[anahtar], "buyukten_sira": sorted(v, reverse=True).index(ek[anahtar]) + 1,
                "n": len(v), "yuzdelik": _r(sum(x <= ek[anahtar] for x in v) / len(v) * 100, 0)}
    yil26 = [a for a in aylar if a.startswith("2026") and a <= "2026-09"]
    # Çeyreklik iç borç servisi (kesin aylık planlardan) — Q4 2026 için Kasım ve
    # Aralık yeni belgenin GEÇİCİ sütunlarından gelir ve öyle etiketlenir.
    ceyrek = {}
    tum = dict(seri)
    for a in ("2026-11", "2026-12"):
        tum[a] = finansman_ozet(D["yeni"]["finansman"][a])
    for a, f in tum.items():
        y, m = int(a[:4]), int(a[5:])
        q = f"{y}-Ç{(m - 1) // 3 + 1}"
        c = ceyrek.setdefault(q, {"ic_servis": 0.0, "ic_faiz": 0.0, "ic_anapara": 0.0, "ic_borclanma": 0.0,
                                   "dogrudan": 0.0, "ay": 0})
        for k in ("ic_servis", "ic_faiz", "ic_anapara", "ic_borclanma", "dogrudan"):
            c[k] += f[k]
        c["ay"] += 1
    ceyrek = {q: {**{k: _r(v, 1) for k, v in c.items() if k != "ay"}, "ay": c["ay"],
                  "faiz_pay": _r(c["ic_faiz"] / c["ic_servis"] * 100, 1)}
              for q, c in sorted(ceyrek.items()) if c["ay"] == 3}
    q4 = {q: v for q, v in ceyrek.items() if q.endswith("Ç4")}
    return {"seri": seri, "ilk": aylar[0], "son": aylar[-1], "n": len(aylar), "ceyrek": ceyrek,
            "q4": q4, "q4_servis_artis_yuzde": _r((q4["2026-Ç4"]["ic_servis"] / q4["2025-Ç4"]["ic_servis"] - 1) * 100, 1),
            "q4_faiz_artis_yuzde": _r((q4["2026-Ç4"]["ic_faiz"] / q4["2025-Ç4"]["ic_faiz"] - 1) * 100, 1),
            "ekim_sira": {k: sira(k) for k in ("dogrudan", "dogrudan_pay", "borclanma_disi",
                                                "ic_servis", "ic_borclanma", "cevirme")},
            "yil26": {k: _r(ist.mean(seri[a][k] for a in yil26), 1)
                      for k in ("dogrudan", "dogrudan_pay", "cevirme", "borclanma_disi")},
            "yil26_aylar": {a: {k: seri[a][k] for k in ("dogrudan", "dogrudan_pay", "cevirme")}
                            for a in yil26},
            "yil26_dogrudan_min": min((seri[a]["dogrudan"], a) for a in yil26),
            "yil26_dogrudan_maks": max((seri[a]["dogrudan"], a) for a in yil26),
            "yil25_dogrudan_ort": _r(ist.mean(seri[a]["dogrudan"] for a in aylar if a.startswith("2025")), 1),
            "yil24_dogrudan_ort": _r(ist.mean(seri[a]["dogrudan"] for a in aylar if a.startswith("2024")), 1)}


def dogrudan_revizyon(D: dict) -> dict:
    """Doğrudan satış hedefinin belgeden belgeye revizyonu: bir ayın İLK
    yayımlanan değeri ile KESİN değeri (dönemi o ayla başlayan belge)."""
    surum: dict[str, list] = {}
    for b in D["hepsi"]:
        for a, f in b["finansman"].items():
            if "dogrudan" in f:
                surum.setdefault(a, []).append((b["duyuru"], f["dogrudan"]))
    kesin_aylar = set(D["kesin"])
    rev = [(a, s[0][1], s[-1][1]) for a, s in sorted(surum.items())
           if a in kesin_aylar and len(s) >= 2]
    dusuk26 = [(a, i, k) for a, i, k in rev if a.startswith("2026") and i <= 25]
    # Kasım'ın sınaması İKİNCİ sürümden kesine (25,0 → 20,0 → ?), Aralık'ınki sıfırdan kesine.
    uc = [(a, [v for _, v in s_]) for a, s_ in sorted(surum.items()) if a in kesin_aylar and len(s_) >= 3]
    ikinci = [(a, v[1], v[-1]) for a, v in uc]
    asagi_sonra = [(a, v[1], v[-1]) for a, v in uc if v[1] < v[0]]
    sifir = [(a, s_[0][1], s_[-1][1]) for a, s_ in sorted(surum.items())
             if a in kesin_aylar and len(s_) >= 2 and s_[0][1] == 0]
    return {"ikinci_kesin": {"n": len(ikinci), "yukari": sum(1 for _, i, k in ikinci if k > i),
                             "asagi": sum(1 for _, i, k in ikinci if k < i),
                             "ayni": sum(1 for _, i, k in ikinci if k == i)},
            "asagi_sonra": {"n": len(asagi_sonra), "yukari": sum(1 for _, i, k in asagi_sonra if k > i)},
            "sifirdan": {"n": len(sifir), "yukari": sum(1 for _, i, k in sifir if k > 0),
                         "yukari_medyan": _r(ist.median([k for _, i, k in sifir if k > 0]), 1)
                         if any(k > 0 for _, i, k in sifir) else None},
            "n": len(rev), "yukari": sum(1 for _, i, k in rev if k > i),
            "asagi": sum(1 for _, i, k in rev if k < i), "ayni": sum(1 for _, i, k in rev if k == i),
            "medyan_fark": _r(ist.median(k - i for _, i, k in rev), 1),
            "zincir": {a: [v for _, v in surum[a]] for a in ("2026-09", "2026-10", "2026-11", "2026-12")},
            "dusuk_ilk_2026": dusuk26,
            "dusuk_ilk_2026_yukari": sum(1 for _, i, k in dusuk26 if k > i)}


# ───────────────────────────────────────────────────── 4 · vade ve faiz riski
def _plan(ad: str) -> pd.DataFrame:
    k = json.loads(_oku("kiyas.json"))["takvimler"][ad]
    d = _csv(f"{ad}.csv")
    d["ham"] = [x.get("ham") for x in k]
    d["kiyas"] = [x.get("kiyas") for x in k]
    d["n"] = [x.get("n") for x in k]
    d["btc"] = [x.get("btc") for x in k]
    d["g"] = pd.to_numeric(d["Tahmini Gerçekleşme (Milyon TL)"], errors="coerce")
    d["v"] = d["Vade Terimi"].map(_vade_yil)
    d["ay"] = pd.to_datetime(d["İhale Tarihi"], dayfirst=True).dt.strftime("%Y-%m")
    d["ihale"] = d["Yöntem"].astype(str).str.contains("hale")
    d["rp"] = [REPRICE_DEGISKEN if s in DEGISKEN else v for s, v in zip(d["Senet Tanımı"], d["v"])]
    return d


def _agirlikli(d: pd.DataFrame, deger: str, agirlik: str) -> float:
    return float((d[deger] * d[agirlik]).sum() / d[agirlik].sum())


def vade(D: dict) -> dict:
    yeni, karsi = _plan("takvim_yeni"), _plan("takvim_karsi")
    Y, K = yeni[yeni["ihale"]], karsi[karsi["ihale"]]
    aylik = {}
    for a in PLAN_AYLARI:
        y = Y[Y["ay"] == a]
        r = {"aov": _r(_agirlikli(y, "v", "ham")), "reprice": _r(_agirlikli(y, "rp", "ham")),
             "tlref_pay": _r(y[y["Senet Tanımı"].isin(DEGISKEN)]["ham"].sum() / y["ham"].sum() * 100, 1),
             "plan_mlr": _r(y["g"].sum() / 1000, 1), "hedef": float(y["Aylık Strateji Hedefi (Milyar TL)"].iloc[0])}
        k = K[K["ay"] == a]
        if len(k):
            r.update({"aov_karsi": _r(_agirlikli(k, "v", "ham")),
                      "reprice_karsi": _r(_agirlikli(k, "rp", "ham")),
                      "tlref_pay_karsi": _r(k[k["Senet Tanımı"].isin(DEGISKEN)]["ham"].sum() / k["ham"].sum() * 100, 1),
                      "plan_mlr_karsi": _r(k["g"].sum() / 1000, 1),
                      "hedef_karsi": float(k["Aylık Strateji Hedefi (Milyar TL)"].iloc[0])})
            r["aov_fark"] = _r(r["aov"] - r["aov_karsi"])
        aylik[a] = r
    # Üç ayın planı HEDEFE ÖLÇEKLİ ağırlıkla: 6.1 tablosunun tutarları, TLREF
    # payı ve yeniden fiyatlama vadesi bu ağırlıkla; ham ağırlık aylar arası
    # oranları hedeften bağımsız bırakır ve yalnız karşılaştırma için tutulur.
    plan_aov_ham = _r(_agirlikli(Y, "v", "ham"))
    plan_aov_g = _r(_agirlikli(Y, "v", "g"))
    plan_rp = _r(_agirlikli(Y, "rp", "g"))
    tlref_pay = _r(Y[Y["Senet Tanımı"].isin(DEGISKEN)]["g"].sum() / Y["g"].sum() * 100, 1)
    # gerçekleşen seri (ihale sonuçlarından, tek konvansiyon) + 3 aylık yuvarlanan
    h = ihale_seti()
    GA = gercek_aylik(h)
    gecmis = {a: (v["aov"], v["toplam"]) for a, v in GA.items()}

    def yuvarlanan(ek: dict) -> dict:
        s = dict(gecmis)
        s.update(ek)
        a_ = sorted(s)
        out = {}
        for i, a in enumerate(a_):
            p = a_[max(0, i - 2): i + 1]
            w = sum(s[x][1] for x in p)
            out[a] = sum(s[x][0] * s[x][1] for x in p) / w
        return out
    yuv = yuvarlanan({a: (aylik[a]["aov"], aylik[a]["plan_mlr"] * 1000) for a in PLAN_AYLARI})
    yuv_k = yuvarlanan({a: (aylik[a]["aov_karsi"], aylik[a]["plan_mlr_karsi"] * 1000)
                        for a in ("2026-10", "2026-11")})
    son_g = max(gecmis)
    gs = pd.Series({a: v for a, v in yuv.items() if a <= son_g}).sort_index()
    d3 = gs.diff(3).dropna()
    # fark, tabloya basılan (yuvarlanmış) iki uçtan: okur 4,03 − 3,77'yi kendisi hesaplar
    uzama = round(yuv["2026-12"], 2) - round(yuv[son_g], 2)
    # son on üç ay (Eylül 2025 – Eylül 2026) gerçekleşen yeniden fiyatlama
    h12 = h[h["_d"] >= "2025-09-01"].copy()
    # duyarlılık: değişken kuponu tam kupon dönemi (0,5 yıl) saymak hükmü değiştirir mi
    rp5 = lambda d: [0.5 if s in DEGISKEN else v for s, v in zip(d["Senet Tanımı"], d["v"])]  # noqa: E731
    h12["rp5"], Y5, K5 = rp5(h12), Y.copy(), K.copy()
    Y5["rp5"], K5["rp5"] = rp5(Y5), rp5(K5)
    duyarlilik = {"plan": _r(_agirlikli(Y5, "rp5", "g")), "gecmis_13a": _r(_agirlikli(h12, "rp5", "Toplam(Gerçekleşme)")),
                  "ekim": _r(_agirlikli(Y5[Y5["ay"] == "2026-10"], "rp5", "ham")),
                  "ekim_karsi": _r(_agirlikli(K5[K5["ay"] == "2026-10"], "rp5", "ham"))}
    return {"aylik": aylik, "plan_aov": plan_aov_g, "plan_aov_ham": plan_aov_ham,
            "reprice_duyarlilik_05": duyarlilik,
            "gercek_aylik": {a: {k: (_r(v, 3) if isinstance(v, float) else v) for k, v in GA[a].items()}
                             for a in sorted(GA) if a >= "2025-09"},
            "plan_reprice": plan_rp, "plan_tlref_pay": tlref_pay,
            "plan_sabit_pay": _r(100 - tlref_pay, 1),
            "gecmis_son_ay": son_g, "gecmis_son_aov": _r(gecmis[son_g][0]),
            "yuvarlanan": {a: _r(v) for a, v in yuv.items() if a >= "2025-09"},
            "yuvarlanan_karsi": {a: _r(yuv_k[a]) for a in ("2026-10", "2026-11")},
            "uzama_3a": _r(uzama), "uzama_n": int(len(d3)),
            "uzama_yuzdelik": _r((d3.abs() <= abs(round(uzama, 2))).mean() * 100, 0),
            "gecmis_12a_reprice": _r(_agirlikli(h12, "rp", "Toplam(Gerçekleşme)")),
            "gecmis_12a_aov": _r(_agirlikli(h12, "v", "Toplam(Gerçekleşme)")),
            "gerceklesme_varsayimi": float(yeni["Gerçekleşme Oranı Varsayımı (%)"].iloc[0]),
            "satirlar": [{"gun": r["İhale Tarihi"], "senet": r["Senet Tanımı"], "terim": r["Vade Terimi"],
                          "itfa": r["İtfa Tarihi"], "yontem": r["Yöntem"], "v": _r(r["v"]),
                          "g_mlr": _r(r["g"] / 1000, 1), "ham_mlr": _r(r["ham"] / 1000, 1),
                          "kiyas": r["kiyas"], "n": r["n"], "btc": r["btc"]}
                         for _, r in Y.iterrows()]}


# ────────────────────────────────────────────────────── 5 · Eylül karnesi
def ihale_seti() -> pd.DataFrame:
    """İhale sonuçları. Vade TEK konvansiyonla, valörden itfaya gün/365 (`v`):
    planın vadesi de takvimdeki gün sayısından gün/365 okunur. Veri setinin kendi
    "Vade (Yıl)" sütunu gün/365,25 ile yuvarlanmış ve bir satırda (10.04.2023
    TLREF) boş — o sütunla kurulan bir ortalama o ihaleyi sessizce düşürür."""
    h = _csv("ihale.csv")
    for c in ("Toplam(Gerçekleşme)", "Toplam(Teklif)", "Vade (Yıl)", "Ortalama Yıllık Bileşik(Gerçekleşme)",
              "Ortalama Yıllık Bileşik(Teklif)", "En Yüksek Yıllık Bileşik(Teklif)",
              "En Yüksek Yıllık Bileşik(Gerçekleşme)", "ROT Toplam(Gerçekleşme)", "ROT Toplam(Teklif)",
              "İhale(Gerçekleşme)", "İhale(Teklif)", "ROT Kamu(Gerçekleşme)",
              "ROT Piyasa Yapıcılar(Gerçekleşme)", "ROT Piyasa Yapıcılar(Teklif)"):
        h[c] = pd.to_numeric(h[c], errors="coerce")
    h["_d"] = pd.to_datetime(h["İhale Tarihi"], format="%d.%m.%Y")
    h["v"] = (pd.to_datetime(h["İtfa Tarihi"], format="%d.%m.%Y")
              - pd.to_datetime(h["Valör Tarihi"], format="%d.%m.%Y")).dt.days / 365
    h["ay"] = h["_d"].dt.strftime("%Y-%m")
    h["rp"] = [REPRICE_DEGISKEN if s in DEGISKEN else v for s, v in zip(h["Senet Tanımı"], h["v"])]
    return h[h["Toplam(Gerçekleşme)"] > 0].sort_values("_d").reset_index(drop=True)


def gercek_aylik(h: pd.DataFrame) -> dict:
    """Gerçekleşen yeni ihracın ay ay bileşimi (tek konvansiyon: `v`)."""
    out = {}
    for a, g in h.groupby("ay"):
        w = g["Toplam(Gerçekleşme)"]
        nb = g[~g["Senet Tanımı"].eq("Hazine Bonosu")]
        out[a] = {"aov": float((g["v"] * w).sum() / w.sum()),
                  "aov_bonosuz": float((nb["v"] * nb["Toplam(Gerçekleşme)"]).sum() / nb["Toplam(Gerçekleşme)"].sum())
                  if len(nb) else None,
                  "reprice": float((g["rp"] * w).sum() / w.sum()),
                  "tlref_pay": float(w[g["Senet Tanımı"].isin(DEGISKEN)].sum() / w.sum() * 100),
                  "sabit_pay": float(w[g["Senet Tanımı"].isin(NOMINAL_SABIT)].sum() / w.sum() * 100),
                  "bono_pay": float(w[g["Senet Tanımı"].eq("Hazine Bonosu")].sum() / w.sum() * 100),
                  "toplam": float(w.sum()), "n": int(len(g))}
    return out


def onceki_yazi() -> dict:
    """31.08 yazısının yayımlanmış sayıları, KENDİ metninden (yedek metinler)."""
    m = ONCEKI_YAZI.read_text(encoding="utf-8")
    out = {}
    for a, v in re.findall(r'anahtar="(\w+)"[^>]*>([^<]+)</Deger>', m):
        out.setdefault(a, v.strip())
    return out


def _s(x: str) -> float:
    return float(x.replace("−", "-").replace("+", "").replace(".", "").replace(",", "."))


def eylul() -> dict:
    h = ihale_seti()
    ey = h[(h["_d"] >= "2026-09-01") & (h["_d"] < "2026-10-01")]
    plan = _csv("takvim_0831.csv")
    plan = plan[plan["İhale Tarihi"].str.endswith(".09.2026") & plan["Yöntem"].str.contains("hale")]
    satir = []
    for _, p in plan.iterrows():
        g = ey[(ey["İtfa Tarihi"] == p["İtfa Tarihi"]) & (ey["Senet Tanımı"] == p["Senet Tanımı"])]
        r = g.iloc[0]
        satir.append({"gun": p["İhale Tarihi"], "senet": p["Senet Tanımı"], "itfa": p["İtfa Tarihi"],
                      "v": _r(r["v"]), "plan_mlr": _r(p["Tahmini Gerçekleşme (Milyon TL)"] / 1000, 1),
                      "gerc_mlr": _r(r["Toplam(Gerçekleşme)"] / 1000, 1),
                      "kat": _r(r["Toplam(Gerçekleşme)"] / p["Tahmini Gerçekleşme (Milyon TL)"], 2),
                      "teklif_mlr": _r(r["Toplam(Teklif)"] / 1000, 1),
                      "btc": _r(r["Toplam(Teklif)"] / r["Toplam(Gerçekleşme)"], 2),
                      "bilesik": _r(r["Ortalama Yıllık Bileşik(Gerçekleşme)"]),
                      "rot_mlr": _r(r["ROT Toplam(Gerçekleşme)"] / 1000, 1),
                      "rot_kamu_mlr": _r((r["ROT Kamu(Gerçekleşme)"] if pd.notna(r["ROT Kamu(Gerçekleşme)"]) else 0) / 1000, 1),
                      "rot_py_mlr": _r((r["ROT Piyasa Yapıcılar(Gerçekleşme)"] if pd.notna(r["ROT Piyasa Yapıcılar(Gerçekleşme)"]) else 0) / 1000, 1),
                      "rekabetci_mlr": _r(r["İhale(Gerçekleşme)"] / 1000, 1),
                      "rekabetci_teklif_mlr": _r(r["İhale(Teklif)"] / 1000, 1),
                      "rekabetci_kabul": _r(r["İhale(Gerçekleşme)"] / r["İhale(Teklif)"] * 100, 1),
                      # piyasa yapıcıların rekabetçi olmayan teklifi: aynı seçicilik o kanalda da var mı
                      "rot_py_teklif_mlr": _r(float(r["ROT Piyasa Yapıcılar(Teklif)"]) / 1000, 1),
                      "rot_py_kabul": _r(float(r["ROT Piyasa Yapıcılar(Gerçekleşme)"])
                                         / float(r["ROT Piyasa Yapıcılar(Teklif)"]) * 100, 1),
                      "plan_btc": _r(p["Tahmini Bid-to-Cover"], 2)})
    top_g = float(ey["Toplam(Gerçekleşme)"].sum())
    top_p = float(plan["Tahmini Gerçekleşme (Milyon TL)"].sum())
    plan = plan.copy()
    plan["v"] = plan["Vade Terimi"].map(_vade_yil)
    plan["rp"] = [REPRICE_DEGISKEN if s_ in DEGISKEN else v for s_, v in zip(plan["Senet Tanımı"], plan["v"])]
    plan["g"] = plan["Tahmini Gerçekleşme (Milyon TL)"]
    t31 = _csv("takvim_0831.csv")
    ek31 = t31[t31["İhale Tarihi"].str.endswith(".10.2026") & t31["Yöntem"].str.contains("hale")]
    ek31_tl = float(ek31[ek31["Senet Tanımı"].isin(DEGISKEN)]["Tahmini Gerçekleşme (Milyon TL)"].sum())
    ek31_top = float(ek31["Tahmini Gerçekleşme (Milyon TL)"].sum())
    ey = ey.copy()
    tl_g = float(ey[ey["Senet Tanımı"].isin(DEGISKEN)]["Toplam(Gerçekleşme)"].sum())
    tl_p = float(plan[plan["Senet Tanımı"].isin(DEGISKEN)]["Tahmini Gerçekleşme (Milyon TL)"].sum())
    uz = h[(h["v"] > 6)]
    agu = uz[(uz["_d"] >= "2026-08-01") & (uz["_d"] < "2026-09-01")].iloc[-1]
    ey8 = uz[(uz["_d"] >= "2026-09-01")].iloc[-1]
    hg = _csv("hedef_gerceklesme.csv")
    hg_e = hg[hg["Ay-Yıl"] == "Eylül 2026"].iloc[0]
    uz5_8 = [r for r in satir if r["itfa"] in ("16.04.2031", "27.09.2034")]
    k31 = h[(h["İtfa Tarihi"] == "16.04.2031") & (h["_d"] >= "2026-01-01")]
    O = onceki_yazi()
    km = re.findall(r"(\w+) 2026 ([\d,]+) → ([\d,]+) yıl", O["vp_karsilastirma_metin"])
    yazi_aov = {ay: {"karsi": _s(a), "plan": _s(b)} for ay, a, b in km}
    kas = re.search(r"\| Kasım 2026 \| \*\(kapsam dışı\)\* \| \*\*([\d,]+) yıl\*\*", ONCEKI_YAZI.read_text(encoding="utf-8"))
    yazi_aov["Kasım"] = {"karsi": None, "plan": _s(kas.group(1))}
    return {"satirlar": satir, "gerc_mlr": _r(top_g / 1000, 1), "plan_mlr": _r(top_p / 1000, 1),
            "yazi_aov": yazi_aov,
            "hedef": float(hg_e["Hedef Borçlanma (Milyar TL)"]),
            "gerceklesme_orani": float(hg_e["Gerçekleşme Oranı (%)"]),
            "aov_gerc": _r(_agirlikli(ey, "v", "Toplam(Gerçekleşme)")),
            "aov_plan_yazi": yazi_aov["Eylül"]["plan"],
            "reprice_gerc": _r(_agirlikli(ey, "rp", "Toplam(Gerçekleşme)")),
            "tlref_pay_gerc": _r(tl_g / top_g * 100, 1), "tlref_pay_plan": _r(tl_p / top_p * 100, 1),
            "reprice_plan": _r(_agirlikli(plan, "rp", "g")),
            "ekim_tlref_pay_0831": _r(ek31_tl / ek31_top * 100, 1),
            "rot_pay_gerc": _r(float(ey["ROT Toplam(Gerçekleşme)"].sum()) / top_g * 100, 1),
            "uzun_sabit_gerc_mlr": _r(sum(float(ey[ey["İtfa Tarihi"] == r["itfa"]]["Toplam(Gerçekleşme)"].sum()) for r in uz5_8) / 1000, 1),
            "uzun_sabit_plan_mlr": _r(sum(float(plan[plan["İtfa Tarihi"] == r["itfa"]]["g"].sum()) for r in uz5_8) / 1000, 1),
            "t160431_aylar_2026": sorted(k31["_d"].dt.strftime("%Y-%m").unique().tolist()),
            "sabit_pay_gerc": _r(float(ey[ey["Senet Tanımı"].isin(NOMINAL_SABIT)]["Toplam(Gerçekleşme)"].sum()) / top_g * 100, 1),
            "maliyet_gerc": _r(_agirlikli(ey, "Ortalama Yıllık Bileşik(Gerçekleşme)", "Toplam(Gerçekleşme)")),
            "uzun_agu": {"gun": agu["İhale Tarihi"], "v": _r(agu["v"]),
                         "gerc_mlr": _r(agu["Toplam(Gerçekleşme)"] / 1000, 1),
                         "teklif_mlr": _r(agu["Toplam(Teklif)"] / 1000, 1),
                         "btc": _r(agu["Toplam(Teklif)"] / agu["Toplam(Gerçekleşme)"], 2),
                         "bilesik": _r(agu["Ortalama Yıllık Bileşik(Gerçekleşme)"])},
            "uzun_eyl": {"gun": ey8["İhale Tarihi"], "v": _r(ey8["v"]),
                         "gerc_mlr": _r(ey8["Toplam(Gerçekleşme)"] / 1000, 1),
                         "teklif_mlr": _r(ey8["Toplam(Teklif)"] / 1000, 1),
                         "btc": _r(ey8["Toplam(Teklif)"] / ey8["Toplam(Gerçekleşme)"], 2),
                         "bilesik": _r(ey8["Ortalama Yıllık Bileşik(Gerçekleşme)"]),
                         "kabul_teklif_orani": _r(ey8["Toplam(Gerçekleşme)"] / ey8["Toplam(Teklif)"] * 100, 1)},
            "uzun_rekor_oncesi": _r(uz[uz["_d"] < "2026-08-01"]["Toplam(Gerçekleşme)"].max() / 1000, 1),
            "onceki": {k: O.get(k) for k in ("vp_plan_ay1_aov", "vp_plan_ay1_yuv", "vp_plan_ay2_yuv",
                                             "vp_plan_ay3_yuv", "vp_gecmis_yuv_son", "vp_plan_tlref_pay",
                                             "vp_plan_sabit_pay", "vp_reprice_plan", "vp_plan_maliyet",
                                             "vp_plan_aov_toplam", "vp_rev_ay2_zincir", "vp_son_uzun_mlr")}}


TLREF = "TLREF'e Endeksli Devlet Tahvili"
TABAN_BAS = "2025-01-01"          # taban oranların penceresi: 2025–2026 ihaleleri


def _kabul(r) -> float:
    return float(r["İhale(Gerçekleşme)"] / r["İhale(Teklif)"] * 100)


def eylul_ek(E: dict, P: dict) -> dict:
    """Eylül'ün kendi taban oranları: 'bir karar mı, mekanik mi' sorusunun ölçüleri.

    Kıyas noktası iki türlüdür ve karıştırılmaz: 31 Ağustos TAHMİNİMİZ (kıyas
    ortalaması, hedefin %87'sine ölçekli — Hazine kâğıt başına tutar yayımlamaz)
    ve GERÇEKLEŞMİŞ aylar (ihale sonuçları)."""
    h = ihale_seti()
    ey = h[(h["_d"] >= "2026-09-01") & (h["_d"] < "2026-10-01")]
    # TLREF ihalelerinde rekabetçi kabul: Eylül olağan mı
    tl = h[h["Senet Tanımı"].eq(TLREF) & (h["_d"] >= TABAN_BAS)].copy()
    tl["kabul"] = [_kabul(r) for _, r in tl.iterrows()]
    tl["py_kabul"] = tl["ROT Piyasa Yapıcılar(Gerçekleşme)"] / tl["ROT Piyasa Yapıcılar(Teklif)"] * 100
    tl_e = tl[tl["İhale Tarihi"].eq("14.09.2026")].iloc[0]
    tl_o = tl[~tl["İhale Tarihi"].eq("14.09.2026")]
    tl_onceki = tl_o[tl_o["_d"] < "2026-09-14"].iloc[-1]
    py_sira = int((tl["py_kabul"] < tl_e["py_kabul"]).sum()) + 1
    # 4 yıl ve üstü sabit kuponlu ihalelerde rekabetçi kabul
    sb = h[h["Senet Tanımı"].eq("Sabit Kuponlu Devlet Tahvili") & (h["v"] >= 4) & (h["_d"] >= TABAN_BAS)].copy()
    sb["kabul"] = [_kabul(r) for _, r in sb.iterrows()]
    sb_o = sb[~sb["İhale Tarihi"].eq("15.09.2026")]
    # fiyat: reddedilen teklifin ortalaması (tutar ağırlıklı ortalamalardan)
    T, G = float(tl_e["İhale(Teklif)"]), float(tl_e["İhale(Gerçekleşme)"])
    red = (T * tl_e["Ortalama Yıllık Bileşik(Teklif)"] - G * tl_e["Ortalama Yıllık Bileşik(Gerçekleşme)"]) / (T - G)
    kuyruk = {}
    for itfa in ("13.09.2028", "11.09.2030", "16.04.2031", "27.09.2034"):
        r = ey[ey["İtfa Tarihi"].eq(itfa)].iloc[0]
        kuyruk[itfa] = {"kesme": _r(r["En Yüksek Yıllık Bileşik(Gerçekleşme)"]),
                        "en_pahali_teklif": _r(r["En Yüksek Yıllık Bileşik(Teklif)"]),
                        "fark_bp": _r((r["En Yüksek Yıllık Bileşik(Teklif)"] - r["En Yüksek Yıllık Bileşik(Gerçekleşme)"]) * 100, 0),
                        "rekabetci_btc": _r(r["İhale(Teklif)"] / r["İhale(Gerçekleşme)"], 2)}
    # hedefin son ihale gününde doldurulması
    gun = ey.groupby("İhale Tarihi")["Toplam(Gerçekleşme)"].sum()
    hg = _csv("hedef_gerceklesme.csv")
    hg = hg[pd.to_numeric(hg["Gerçekleşen Borçlanma (Milyar TL)"], errors="coerce") > 0].copy()
    hg["oran"] = (pd.to_numeric(hg["Gerçekleşen Borçlanma (Milyar TL)"]) /
                  pd.to_numeric(hg["Hedef Borçlanma (Milyar TL)"]) * 100)
    agu9 = h[h["İhale Tarihi"].eq("18.08.2026") & (h["v"] > 6)].iloc[0]
    t31 = _csv("takvim_0831.csv")
    t31e = t31[t31["İhale Tarihi"].str.endswith(".09.2026") & t31["Yöntem"].str.contains("hale")]
    tl31 = t31e[t31e["Senet Tanımı"].eq(TLREF)].iloc[0]
    tl_son3 = h[h["Senet Tanımı"].eq(TLREF) & (h["_d"] < "2026-08-31")].tail(3)
    y8 = h[h["İtfa Tarihi"].eq("27.09.2034")]
    GA = gercek_aylik(h)
    pka24 = P["guncel"]["dibs-verim-egrisi"]["pka_faiz_24a"]
    pka24_bil = ((1 + pka24 / 100 * 7 / 365) ** (365 / 7) - 1) * 100
    y8_bil = float(ey[ey["İtfa Tarihi"].eq("27.09.2034")].iloc[0]["Ortalama Yıllık Bileşik(Gerçekleşme)"])
    return {
        "tlref_kabul": {"eylul": _r(tl_e["kabul"], 1), "diger_n": int(len(tl_o)),
                        "diger_medyan": _r(tl_o["kabul"].median(), 1),
                        "diger_50_alti": int((tl_o["kabul"] < 50).sum()),
                        "onceki_gun": tl_onceki["İhale Tarihi"], "onceki_kabul": _r(tl_onceki["kabul"], 1),
                        "py_kabul_eylul": _r(tl_e["py_kabul"], 1), "py_sira_kucukten": py_sira,
                        "py_n": int(len(tl)), "py_teklif_mlr": _r(tl_e["ROT Piyasa Yapıcılar(Teklif)"] / 1000, 1),
                        "py_mlr": _r(tl_e["ROT Piyasa Yapıcılar(Gerçekleşme)"] / 1000, 1)},
        "sabit4_kabul": {"diger_n": int(len(sb_o)), "diger_maks": _r(sb_o["kabul"].max(), 1),
                         "diger_medyan": _r(sb_o["kabul"].median(), 1),
                         "eylul_5y": _r(sb[sb["İhale Tarihi"].eq("15.09.2026") & sb["İtfa Tarihi"].eq("16.04.2031")]["kabul"].iloc[0], 1),
                         "eylul_8y": _r(sb[sb["İhale Tarihi"].eq("15.09.2026") & sb["İtfa Tarihi"].eq("27.09.2034")]["kabul"].iloc[0], 1)},
        "fiyat": {"tlref_red_ort": _r(red), "tlref_red_mlr": _r((T - G) / 1000, 1), "kuyruk": kuyruk},
        "hedef_doldurma": {"hedef": E["hedef"], "gun14_mlr": _r(gun["14.09.2026"] / 1000, 1),
                           "kalan_mlr": _r(E["hedef"] - gun["14.09.2026"] / 1000, 1),
                           "gun15_mlr": _r(gun["15.09.2026"] / 1000, 1),
                           "oran_ham": _r(float(hg[hg["Ay-Yıl"].eq("Eylül 2026")]["oran"].iloc[0]), 2),
                           "ay_n": int(len(hg)), "yarim_puan_ici": int(((hg["oran"] - 100).abs() <= 0.5).sum()),
                           "bir_puan_ici": int(((hg["oran"] - 100).abs() <= 1).sum())},
        "btc_rekabetci": {"tlref": kuyruk["11.09.2030"]["rekabetci_btc"], "y8": kuyruk["27.09.2034"]["rekabetci_btc"],
                          "agu9": _r(agu9["İhale(Teklif)"] / agu9["İhale(Gerçekleşme)"], 2)},
        "tahmin_0831": {"varsayim": float(t31e["Gerçekleşme Oranı Varsayımı (%)"].iloc[0]),
                        "tlref_kiyas_mlr": _r(tl31["Geçmiş Ort. Gerçekleşme (Milyon TL)"] / 1000, 1),
                        "tlref_son3": [{"gun": r["İhale Tarihi"], "mlr": _r(r["Toplam(Gerçekleşme)"] / 1000, 1)}
                                       for _, r in tl_son3.iterrows()],
                        "y8_son_ihale": t31e[t31e["İtfa Tarihi"].eq("27.09.2034")]["Son İhale Tarihi"].iloc[0]},
        "y8_son3": [{"gun": r["İhale Tarihi"], "mlr": _r(r["Toplam(Gerçekleşme)"] / 1000, 1)}
                    for _, r in y8.tail(3).iterrows()],
        "gercek_seri": {a: {k: (_r(v, 2) if isinstance(v, float) else v) for k, v in GA[a].items()}
                        for a in ("2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09")},
        "anket_24a_bilesik": _r(pka24_bil), "y8_anket_fark": _r(y8_bil - pka24_bil, 1),
    }


# ───────────────────────────────────────────────── 6 · maliyet, hedef, talep
def maliyet(V: dict) -> dict:
    h = ihale_seti()
    son = h[h["_d"] >= h["_d"].max() - pd.DateOffset(months=MALIYET_PENCERE_AY)].dropna(
        subset=["Ortalama Yıllık Bileşik(Gerçekleşme)"]).copy()
    son["kova"] = son["v"].map(_kova)
    kova = {}
    for ad, kume in (("sabit", NOMINAL_SABIT), ("degisken", DEGISKEN), ("reel", REEL)):
        g = son[son["Senet Tanımı"].isin(kume)]
        for k, gg in g.groupby("kova"):
            kova[f"{ad}|{k}"] = {"maliyet": _r(_agirlikli(gg, "Ortalama Yıllık Bileşik(Gerçekleşme)", "Toplam(Gerçekleşme)")),
                                 "mlr": _r(gg["Toplam(Gerçekleşme)"].sum() / 1000, 1), "n": int(len(gg))}
    Y = _plan("takvim_yeni")
    Y = Y[Y["ihale"]].copy()
    Y["tip"] = ["degisken" if s in DEGISKEN else "reel" if s in REEL else "sabit" for s in Y["Senet Tanımı"]]
    Y["c"] = [kova.get(f"{t}|{_kova(v)}", {}).get("maliyet") for t, v in zip(Y["tip"], Y["v"])]
    kap = Y.dropna(subset=["c"])
    # İkinci bir fiyat: her kâğıt kendi EYLÜL ihalesinin bileşik faiziyle (yoksa kovası).
    # Kova ortalaması dört ayı taşır; Eylül ihalesi pencerenin en taze fiyatıdır.
    ey = h[h["_d"] >= "2026-09-01"]
    son_f = {(r["Senet Tanımı"], r["İtfa Tarihi"]): float(r["Ortalama Yıllık Bileşik(Gerçekleşme)"])
             for _, r in ey.iterrows()}
    Y["c_eyl"] = [son_f.get((s_, i_), c_) for s_, i_, c_ in zip(Y["Senet Tanımı"], Y["İtfa Tarihi"], Y["c"])]
    Y["eyl_kaynak"] = ["ihale" if (s_, i_) in son_f else "kova" for s_, i_ in zip(Y["Senet Tanımı"], Y["İtfa Tarihi"])]
    kap_e = Y.dropna(subset=["c_eyl"])
    return {"pencere_bas": (h["_d"].max() - pd.DateOffset(months=MALIYET_PENCERE_AY)).strftime("%Y-%m-%d"),
            "veri_sonu": h["_d"].max().strftime("%Y-%m-%d"), "kova": kova,
            "plan": _r(_agirlikli(kap, "c", "g")), "kapsam": _r(kap["g"].sum() / Y["g"].sum() * 100, 0),
            "plan_eylul_fiyat": _r(_agirlikli(kap_e, "c_eyl", "g")),
            "plan_eylul_ihale_pay": _r(Y[Y["eyl_kaynak"] == "ihale"]["g"].sum() / Y["g"].sum() * 100, 1),
            "makas_1a_6p": _r(kova["sabit|≤1 yıl"]["maliyet"] - kova["sabit|6 yıl+"]["maliyet"])}


def hedefler(D: dict) -> dict:
    """Hedefin (ihale + kamuya satış) belgeden belgeye revizyonu — ARŞİVDEN, yalnız
    KESİN ayı bilinen aylarda. Geçici bir ayın son sürümü henüz son değildir:
    Kasım 2026'yı örnekleme katmak, Kasım'ı onu da içeren bir dağılımla
    kıyaslamak olurdu. Tek sürümü okunabilen ay (Aralık 2019) revizyon ölçemez."""
    surum: dict[str, list] = {}
    for b in D["hepsi"]:
        for a, f in b["finansman"].items():
            surum.setdefault(a, []).append(round(f["ihale"] + f["kamu"], 1))
    kesin = set(D["kesin"])
    rv = {a: s_ for a, s_ in surum.items() if a in kesin and len(s_) >= 2 and s_[0] > 0}
    rev = [(s_[-1] - s_[0]) / s_[0] * 100 for s_ in rv.values()]
    aralik = {a: _r((s_[-1] - s_[0]) / s_[0] * 100, 1) for a, s_ in sorted(rv.items()) if a.endswith("-12")}
    zincir = {a: surum[a] for a in ("2026-09", "2026-10", "2026-11", "2026-12")}
    hg = _csv("hedef_gerceklesme.csv")
    hg = hg[pd.to_numeric(hg["Gerçekleşen Borçlanma (Milyar TL)"], errors="coerce") > 0]
    # oran YUVARLANMAMIŞ tutarlardan: yuvarlanmış %100,0, 261,86 / 261,9'u "tam" gösterir
    oran = (pd.to_numeric(hg["Gerçekleşen Borçlanma (Milyar TL)"]) /
            pd.to_numeric(hg["Hedef Borçlanma (Milyar TL)"]) * 100)
    s24 = oran.tail(24)
    return {"rev_n": len(rev), "rev_ilk": min(rv), "rev_son": max(rv),
            "rev_medyan": _r(ist.median(rev), 1),
            "rev_yukari_pay": _r(sum(x > 0 for x in rev) / len(rev) * 100, 0),
            "rev_mutlak_ort": _r(ist.mean(abs(x) for x in rev), 1),
            "rev_surum_ort": _r(ist.mean(len(s_) for s_ in rv.values()), 1),
            "aralik": aralik, "aralik_yukari": sum(1 for v in aralik.values() if v > 0),
            "aralik_asagi": sum(1 for v in aralik.values() if v < 0),
            "zincir": zincir,
            "ekim_ilk_fark_yuzde": _r((zincir["2026-10"][-1] / zincir["2026-10"][0] - 1) * 100, 1),
            "kasim_fark_yuzde": _r((zincir["2026-11"][-1] / zincir["2026-11"][0] - 1) * 100, 1),
            "gerc_24a": {"ort": _r(s24.mean(), 1), "medyan": _r(s24.median(), 1), "min": _r(s24.min(), 1),
                         "maks": _r(s24.max(), 1), "std": _r(s24.std(), 1),
                         "alti_n": int((s24 < 100).sum()), "n": int(len(s24)),
                         "alti_pay": _r((s24 < 100).mean() * 100, 0)}}


def arz(V: dict) -> dict:
    s = pd.DataFrame(V["satirlar"])
    uz = s[s["v"] > 6]
    gun = s.groupby("gun")["g_mlr"].sum().round(1).to_dict()
    kova = s.groupby(s["v"].map(_kova))["g_mlr"].sum()
    kup = s[s["senet"] == "Kuponsuz Devlet Tahvili"]
    tek = s[s["n"] == 1]
    return {"uzun_mlr": _r(uz["g_mlr"].sum(), 1), "uzun_adet": int(len(uz)),
            "kuponsuz_mlr": _r(kup["g_mlr"].sum(), 1), "kuponsuz_pay": _r(kup["g_mlr"].sum() / s["g_mlr"].sum() * 100, 1),
            "tek_kiyas_satir": int(len(tek)), "tek_kiyas_pay": _r(tek["g_mlr"].sum() / s["g_mlr"].sum() * 100, 1),
            "kuponsuz_aralik_pay": _r(kup["g_mlr"].sum() / s[s["gun"].str.endswith(".12.2026")]["g_mlr"].sum() * 100, 1),
            "uzun_satirlar": uz[["gun", "g_mlr"]].to_dict("records"),
            "gun_toplam": gun, "kova_pay": {k: _r(v / kova.sum() * 100, 1) for k, v in kova.items()},
            "toplam_mlr": _r(s["g_mlr"].sum(), 1)}


def kisa_uc() -> dict:
    h = ihale_seti()
    h["ay"] = h["_d"].dt.strftime("%Y-%m")
    bono = h[h["Senet Tanımı"] == "Hazine Bonosu"]
    kup = h[h["Senet Tanımı"] == "Kuponsuz Devlet Tahvili"]
    son_bono = bono.iloc[-1]
    son_kup = kup.iloc[-1]
    ay_top = h.groupby("ay")["Toplam(Gerçekleşme)"].sum()
    b_ay = bono.groupby("ay")["Toplam(Gerçekleşme)"].sum()
    k_ay = kup.groupby("ay")["Toplam(Gerçekleşme)"].sum()
    son24 = [a for a in sorted(ay_top.index) if a >= "2024-10"]
    return {"son_bono": {"gun": son_bono["İhale Tarihi"], "mlr": _r(son_bono["Toplam(Gerçekleşme)"] / 1000, 1)},
            "son_kuponsuz": {"gun": son_kup["İhale Tarihi"], "itfa": son_kup["İtfa Tarihi"],
                             "v": _r(son_kup["v"]), "mlr": _r(son_kup["Toplam(Gerçekleşme)"] / 1000, 1),
                             "bilesik": _r(son_kup["Ortalama Yıllık Bileşik(Gerçekleşme)"])},
            "kuponsuz_n": int(len(kup)),
            "kisa_pay_24a": {a: _r((b_ay.get(a, 0) + k_ay.get(a, 0)) / ay_top[a] * 100, 1) for a in son24},
            "bono_pay_24a_ort": _r(ist.mean(b_ay.get(a, 0) / ay_top[a] * 100 for a in son24), 1),
            "bono_12a_mlr": _r(bono[bono["_d"] > h["_d"].max() - pd.DateOffset(months=12)]["Toplam(Gerçekleşme)"].sum() / 1000, 1)}


def piyasa() -> dict:
    P = json.loads(_oku("piyasa.json"))
    O = onceki_yazi()
    d = P["dibs-verim-egrisi"]
    once = {k: _s(O[k]) for k in ("spot_3a", "spot_6a", "spot_1y", "spot_2y", "spot_3y", "spot_5y", "spot_7y",
                                   "forward_1y1y", "forward_2y1y", "forward_2y3y", "risk_primi_5y",
                                   "basabas_5y", "pka_faiz_12a", "pka_12a") if k in O}
    fark = {k: _r((d[k] - v) * 100, 0) for k, v in once.items() if isinstance(d.get(k), (int, float))}
    egim_once = once["spot_5y"] - once["spot_2y"]
    return {"guncel": P, "onceki": once, "fark_bp": fark,
            "egim_2y5y_once": _r(egim_once), "egim_2y5y": _r(d["spot_5y"] - d["spot_2y"]),
            "reel_pka": _r(((1 + P["fonlama-likidite"]["politika"] / 100) / (1 + d["pka_12a"] / 100) - 1) * 100, 1),
            # 31.08 yazısının eşiği AYLIK çekirdek momentumdur (%1,9). Çekirdek C'nin
            # arındırılmış üç aylık yıllıklandırılmış hızı aylık karşılığına çevrilir;
            # `baz_momentum_aylik` ise MANŞET TÜFE'nin arındırılmış son üç ay ortalamasıdır
            # (Enflasyon hattı, baz_patikasi: a["tufe"], SA["tufe"]) — ikisi ayrı ölçüdür.
            "cekirdek_aylik_esdeger": _r(((1 + P["enflasyon"]["c_3a"] / 100) ** (1 / 12) - 1) * 100, 2)}


def karne(V: dict, E: dict, P: dict, TT: dict, H: dict) -> list[dict]:
    """31.08 yazısının altı beklentisi — her biri kendi ölçütüyle."""
    O = onceki_yazi()
    return [
        # gerçekleşen yalnız Eylül; Ekim–Aralık yeni bir projeksiyondur, sonuç değil
        {"no": 1, "beklenti": "3 aylık yuvarlanan vade Ekim'de ~3,8 yılda tepe yapar, sonra plato",
         "olculen": {"eylul_yuv": V["yuvarlanan"]["2026-09"], "ekim_yuv": V["yuvarlanan"]["2026-10"],
                     "kasim_yuv": V["yuvarlanan"]["2026-11"], "aralik_yuv": V["yuvarlanan"]["2026-12"],
                     "yazi_eylul_yuv": _s(O["vp_plan_ay1_yuv"]), "yazi_ekim_yuv": _s(O["vp_plan_ay2_yuv"])},
         "hukum": "Henüz sınanmadı"},
        {"no": 2, "beklenti": "Bono kalıcı olarak çıkmaz; Ekim–Aralık belgesi asıl test",
         "olculen": {"bonosuz_ardisik": TT["bonosuz_kosu"]["2026-12"],
                     "aralik_kuponsuz_gun": 483},
         "hukum": "Tutmadı"},
        {"no": 3, "beklenti": "Hedefler yeniden revize edilir; Kasım'ın 85,4'ü değişir",
         "olculen": {"ekim": H["zincir"]["2026-10"], "kasim": H["zincir"]["2026-11"]},
         "hukum": "Tuttu"},
        # ölçüt Ekim'in 8 yıllık ihalesi; o ihale 6 Ekim'de — sınanmadı ama sınanacak
        {"no": 4, "beklenti": "13.10'un teklif oranı Ağustos'un 1,63'ünün altına düşerse talep zayıflıyor",
         "olculen": {"eylul_8y_btc": E["uzun_eyl"]["btc"], "agustos_btc": E["uzun_agu"]["btc"],
                     "eylul_8y_teklif": E["uzun_eyl"]["teklif_mlr"], "agustos_teklif": E["uzun_agu"]["teklif_mlr"]},
         "hukum": "Henüz sınanmadı"},
        # 5 ve 6 koşullu: koşul (indirim · tersliğin kapanması) gerçekleşmediği için sınanamaz
        {"no": 5, "beklenti": "Faiz gideri indirime hızlı tepki verir",
         "olculen": {"politika": P["guncel"]["fonlama-likidite"]["politika"]}, "hukum": "Koşulu oluşmadı"},
        {"no": 6, "beklenti": "Eğrinin tersliği azalmadan vade uzaması sürmez; terslik kapanırsa Hazine kısaya döner",
         "olculen": {"egim_2y5y_once": P["egim_2y5y_once"], "egim_2y5y": P["egim_2y5y"],
                     "plan_aov": V["plan_aov"]}, "hukum": "Koşulu oluşmadı"},
    ]


def main() -> int:
    D = belgeler()
    PR = program(D)
    OG = odeme_gunleri(D)
    TF = takvim_farki(D)
    TT = takvim_tarihce(D)
    FT = finansman_tarihce(D)
    FT["dogrudan_revizyon"] = dogrudan_revizyon(D)
    V = vade(D)
    E = eylul()
    M = maliyet(V)
    H = hedefler(D)
    A = arz(V)
    K = kisa_uc()
    P = piyasa()
    out = {"cipa": json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))["cipa"],
           "belge": {"yeni": {k: D["yeni"][k] for k in ("baslik", "duyuru", "sha256", "donem")},
                     "eski": {k: D["eski"][k] for k in ("baslik", "duyuru", "sha256", "donem")},
                     "arsiv_belge": D["belge_sayisi"], "arsiv_metinli": len(D["hepsi"]),
                     "indirilemeyen": D["indirilemeyen"]},
           "program": PR, "odeme": OG, "takvim": TF, "takvim_tarihce": TT, "finansman_tarihce": FT,
           "vade": V, "eylul": E, "maliyet": M, "hedef": H, "arz": A, "kisa_uc": K, "piyasa": P}
    out["eylul"].update(eylul_ek(E, P))
    out["karne"] = karne(V, E, P, TT, H)
    # 31 Ağustos yazısının ana tezi: "vade uzuyor, faiz riski uzamıyor"
    O = onceki_yazi()
    out["karne_tez"] = {"beklenti": "Vade uzuyor, faiz riski uzamıyor",
                        "olculen": {"reprice_gecmis": _s(O["vp_reprice_gecmis"]),
                                    "reprice_plan": _s(O["vp_reprice_plan"]),
                                    "eylul_reprice": E["reprice_gerc"], "eylul_aov": E["aov_gerc"],
                                    "eylul_karsi": E["yazi_aov"]["Eylül"]["karsi"],
                                    "eylul_plan": E["yazi_aov"]["Eylül"]["plan"]},
                        "hukum": "Vade kısmı tuttu, faiz riski kısmı tutmadı"}
    # 31 Ağustos yazısının "momentum kırılmaz" kolu (Bölüm 12.3) — satır satır, kendi ölçütüyle
    PP, SA_ = out["piyasa"], out["eylul"]["gercek_seri"]
    tl_art = SA_["2026-08"]["tlref_pay"] < SA_["2026-07"]["tlref_pay"] and SA_["2026-09"]["tlref_pay"] < SA_["2026-07"]["tlref_pay"]
    out["karne_senaryo"] = {
        "esik": 1.9, "cekirdek": PP["cekirdek_aylik_esdeger"],
        "manset": PP["guncel"]["enflasyon"]["baz_momentum_aylik"],
        "kol": "kırılmaz" if min(PP["cekirdek_aylik_esdeger"], PP["guncel"]["enflasyon"]["baz_momentum_aylik"]) >= 1.9 else "kırılır",
        "satirlar": [
            {"ad": "2y", "hukum": "Tuttu" if PP["fark_bp"]["spot_2y"] >= 0 else "Tutmadı"},
            {"ad": "9y", "hukum": "Ölçülemedi"},
            {"ad": "terslik", "hukum": "Tutmadı (vekil ölçüyle)" if abs(PP["egim_2y5y"]) < abs(PP["egim_2y5y_once"]) else "Tuttu (vekil ölçüyle)"},
            {"ad": "risk_primi", "hukum": "Tuttu" if PP["fark_bp"]["risk_primi_5y"] > 0 else "Tutmadı"},
            {"ad": "sabit_pay", "hukum": "Belgede değil, ihalede tuttu" if tl_art else "Tutmadı"},
            {"ad": "ois", "hukum": "Ölçülemedi"},
        ]}
    # dördüncü çeyreğin faizi reel olarak: nominal artış ile yıllık TÜFE
    tufe = P["guncel"]["enflasyon"]["tufe_12a"]
    FT["q4_faiz_reel_yuzde"] = _r(((1 + FT["q4_faiz_artis_yuzde"] / 100) / (1 + tufe / 100) - 1) * 100, 1)
    FT["q4_faiz_reel_tufe"] = tufe
    (VERI / "olcum.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"yazıldı: {VERI / 'olcum.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
