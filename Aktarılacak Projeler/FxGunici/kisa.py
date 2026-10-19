#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kısa serinin ölçüleri (ders_olcum → olcum["kisa"]): stop ve hedef seçimi kazanma oranını ve net sonucu nasıl değiştirir.

Girdi koşunun ızgara sonuçlarıdır (cikti/sonuc/<birim>/<parite>.json → izgara): her kural × parite için ön kayıtta
yazılmış bütün parametre bileşimleri, iki pencerede (2018–2023 · 2024 →) işlem sayısı, kazanma oranı (isabet) ve
işlem başına net R. Kopya satırlar (aynı işlemleri üreten iki bileşim) ve boş bileşimler sayılmaz; bir pencerede
ASGARI işlemden azı olan bileşim o pencerenin ölçüsüne girmez.

Ölçüler betimlemedir: iki pencere de görüldükten sonra kuruldu ve hiçbir kuralın hükmünü değiştirmez (hükümler ön
kayıtlı varsayılanlarındır). Üç soru sorar:
  1. Hedef türüne göre kazanma oranı ve net sonuç (yakın hedef 1R, uzak hedef 2R, hedefsiz çıkış, kurala özgü hedef).
  2. EŞLİ kıyas: aynı kural, aynı parite, öbür bütün parametreler aynıyken YALNIZ hedef (1R ↔ 2R), yalnız stop türü
     (sert ↔ kapanış) ya da yalnız stop yeri (karşı uç ↔ orta) değişince kazanma oranı ve net R ne kadar değişir.
     Gruplar arası kıyas kural karışımına bağlıdır (gün sonu hedefi yalnız kırılım kurallarında var); eşli kıyas değil.
  3. Yüksek kazanma oranı ve "en iyi ayarı seçmek": örneklem dışında kazanma oranı yüksek ayarların net sonucu, ve
     örneklem içinde en iyi çıkan ayarların örneklem dışındaki net sonucu.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

#: Bir pencerenin ölçüsüne girmek için asgari işlem sayısı (bileşim başına).
ASGARI = 30
#: Hedef türlerinin grupları (okur adı ders motorunda).
HEDEF_GRUP = {"1R": "yakin", "2R": "uzak", "gun_sonu": "hedefsiz", "zaman": "hedefsiz", "yok": "hedefsiz"}
GRUP_SIRA = ("yakin", "uzak", "hedefsiz", "ozel")
#: Eşli kıyasların parametresi ve iki değeri (birinci → ikinci).
ESLI = (("hedef", "1R", "2R"), ("stop_turu", "sert", "kapanis"), ("stop_yeri", "karsi_uc", "orta"))
#: "En iyi ayarı seçmek" kıyasında örneklem içinden alınan ayar sayısı.
SECIM_N = 20
#: Yüksek kazanma oranı eşikleri (örneklem dışı).
ISABET_ESIK = (0.5, 0.6)


def _medyan(x: list[float]) -> float | None:
    s = sorted(v for v in x if v is not None and not math.isnan(v))
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else 0.5 * (s[m - 1] + s[m])


def _ort(x: list[float]) -> float | None:
    s = [v for v in x if v is not None]
    return sum(s) / len(s) if s else None


def satirlar(kok: Path, birimler: dict) -> list[dict]:
    """Izgaranın sayılan satırları: kopya ve boş olmayan, iki pencerede de en az ASGARI işlemli bileşimler."""
    out = []
    for b, v in birimler.items():
        for c in v["cift"]:
            s = json.loads((kok / "sonuc" / b / f"{c}.json").read_text(encoding="utf-8"))
            for iz in s.get("izgara") or []:
                if iz.get("kopya") is not None or iz.get("bos"):
                    continue
                i, o = iz.get("is") or {}, iz.get("oos") or {}
                if (i.get("n") or 0) < ASGARI or (o.get("n") or 0) < ASGARI:
                    continue
                if None in (i.get("isabet"), o.get("isabet"), i.get("beklenti_r"), o.get("beklenti_r")):
                    continue
                out.append({"kural": b, "cift": c, "p": {k: str(x) for k, x in iz["p"].items()},
                            "is_isabet": i["isabet"], "is_r": i["beklenti_r"],
                            "oos_isabet": o["isabet"], "oos_r": o["beklenti_r"]})
    return out


def _grup(s: dict) -> str:
    return HEDEF_GRUP.get(s["p"].get("hedef", "yok"), "ozel")


def _ozet(sat: list[dict]) -> dict:
    return {"n": len(sat),
            "isabet": _medyan([s["oos_isabet"] for s in sat]),
            "r": _medyan([s["oos_r"] for s in sat]),
            "ikisi_arti": sum(1 for s in sat if s["is_r"] > 0 and s["oos_r"] > 0)}


def esli(sat: list[dict], param: str, a: str, b: str) -> dict:
    """Aynı kural, parite ve öbür parametrelerle yalnız `param` a → b değişen çiftler."""
    def anahtar(s):
        return (s["kural"], s["cift"], tuple(sorted((k, v) for k, v in s["p"].items() if k != param)))
    sol = {anahtar(s): s for s in sat if s["p"].get(param) == a}
    sag = {anahtar(s): s for s in sat if s["p"].get(param) == b}
    ortak = [k for k in sol if k in sag]
    if not ortak:
        return {"n": 0}
    di = [sag[k]["oos_isabet"] - sol[k]["oos_isabet"] for k in ortak]
    dr = [sag[k]["oos_r"] - sol[k]["oos_r"] for k in ortak]
    return {"n": len(ortak), "kural": len({k[0] for k in ortak}),
            "a_isabet": _medyan([sol[k]["oos_isabet"] for k in ortak]),
            "b_isabet": _medyan([sag[k]["oos_isabet"] for k in ortak]),
            "a_r": _medyan([sol[k]["oos_r"] for k in ortak]),
            "b_r": _medyan([sag[k]["oos_r"] for k in ortak]),
            "d_isabet": _medyan(di), "d_r": _medyan(dr),
            "b_iyi_pay": sum(1 for x in dr if x > 0) / len(dr),
            "a_arti": sum(1 for k in ortak if sol[k]["oos_r"] > 0),
            "b_arti": sum(1 for k in ortak if sag[k]["oos_r"] > 0)}


def bolum(kok: Path, birimler: dict) -> dict:
    sat = satirlar(kok, birimler)
    if not sat:
        raise ValueError("kisa: ızgarada sayılan satır yok")
    gruplar = {g: _ozet([s for s in sat if _grup(s) == g]) for g in GRUP_SIRA}
    yuksek = {}
    for e in ISABET_ESIK:
        x = [s for s in sat if s["oos_isabet"] >= e]
        yuksek[f"{e:.1f}"] = {"n": len(x), "r": _medyan([s["oos_r"] for s in x]),
                              "arti": sum(1 for s in x if s["oos_r"] > 0)}
    en_iyi = sorted(sat, key=lambda s: (-s["is_r"], s["kural"], s["cift"], sorted(s["p"].items())))[:SECIM_N]
    return {
        "asgari": ASGARI,
        "grup_sira": list(GRUP_SIRA),
        "toplam": {**_ozet(sat), "kural": len({s["kural"] for s in sat}),
                   "oos_arti": sum(1 for s in sat if s["oos_r"] > 0)},
        "grup": gruplar,
        "esli": {param: esli(sat, param, a, b) for param, a, b in ESLI},
        "yuksek_isabet": yuksek,
        "secim": {"n": len(en_iyi), "is_r": _ort([s["is_r"] for s in en_iyi]),
                  "oos_r": _ort([s["oos_r"] for s in en_iyi]),
                  "oos_arti": sum(1 for s in en_iyi if s["oos_r"] > 0)},
        # Figürün noktaları (örneklem dışı kazanma oranı, net R, hedef grubu); dört haneye yuvarlı.
        "nokta": [[round(s["oos_isabet"], 4), round(s["oos_r"], 4), GRUP_SIRA.index(_grup(s))] for s in sat],
    }
