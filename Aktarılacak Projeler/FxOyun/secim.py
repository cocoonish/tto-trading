#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ön kayıttaki seçim kuralını 2018–2023 aday tablosuna uygular → veri/plan.json (işlem + referans bacakları).

Kural onkayit_oyun.toml'da; bu betik yalnız onu uygular. Çıktı git'e 2024 sınaması koşmadan girer.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path

BURASI = Path(__file__).resolve().parent


def bacak_coz(ad: str) -> dict:
    """gelistir.bacak_ad çıktısını geri çözer: 'katil:1.0:t0.5' → {tur, hedef, tampon, bekle}."""
    p = ad.split(":")
    hedef = p[1] if p[1] in ("uc", "orta") else float(p[1])
    tampon = float(p[2][1:]) if len(p) > 2 else 0.1
    return {"tur": p[0], "hedef": hedef, "tampon": tampon, "bekle": 60}


def main() -> int:
    on_yol = BURASI / "onkayit_oyun.toml"
    on = tomllib.loads(on_yol.read_text(encoding="utf-8"))
    g = json.loads((BURASI / "veri" / "gelistir.json").read_text(encoding="utf-8"))
    kural = on["secim"]
    hucre: dict[tuple, list] = {}
    for r in g["satir"]:
        if r["anahtar"] != "+".join(kural["duzey"] + ["bacak"]):
            continue
        hucre.setdefault((r["aile"], r["sinif"]), []).append(r)
    islem, izle = [], []
    for (aile, sinif), rs in sorted(hucre.items()):
        uygun = [r for r in rs if r["n"] >= kural["en_az_islem"] and r["ort_R"] > 0]
        if not uygun:
            izle.append({"aile": aile, "sinif": sinif, "aday": len(rs),
                         "en_iyi": max(rs, key=lambda r: r["ort_R"])["bacak"],
                         "en_iyi_R": max(r["ort_R"] for r in rs)})
            continue
        en = max(uygun, key=lambda r: r["ort_R"])
        islem.append({"aile": aile, "sinif": sinif, "bacak": bacak_coz(en["bacak"]), "ad": en["bacak"],
                      "aday": len(rs), "ic": {k: en[k] for k in ("n", "kazanma", "ort_R", "brut_R", "risk_pip_med")}})
    referans = []
    for rf in on["referans"]:
        for s in rf["sinif"]:
            referans.append({"aile": rf["aile"], "sinif": s, "bacak": dict(rf["bacak"]), "okuma": rf["okuma"]})
    out = {"onkayit_ozu": hashlib.sha256(on_yol.read_bytes()).hexdigest(),
           "gelistir_ozu": hashlib.sha256((BURASI / "veri" / "gelistir.json").read_bytes()).hexdigest(),
           "islem": islem, "izle": izle, "referans": referans}
    (BURASI / "veri" / "plan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for x in islem:
        print(f"  İŞLEM  {x['aile']:8} {x['sinif']:11} {x['ad']:18} 2018–2023: n {x['ic']['n']} · kazanma "
              f"{x['ic']['kazanma']:.1%} · net {x['ic']['ort_R']:+.3f} R")
    print(f"  izle, işlem yok: {len(izle)} hücre · referans bacak: {len(referans)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
