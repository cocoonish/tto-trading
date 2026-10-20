#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ön kayıttaki seçim kuralını 2018–2023 giriş tablosuna uygular → veri/buyuk_plan.json (işlem + referans).

Kural onkayit_buyuk.toml [secim]'de; bu betik yalnız onu uygular. Çıktı git'e 2024 sınaması koşmadan girer.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"


def main() -> int:
    on_yol = BURASI / "onkayit_buyuk.toml"
    on = tomllib.loads(on_yol.read_text(encoding="utf-8"))
    gel_yol = VERI / "buyuk_gelistir.json"
    g = json.loads(gel_yol.read_text(encoding="utf-8"))
    k = on["secim"]
    adaylar = [{**r, "suzgec": None, "deger": None} for r in g["hucre"]] + g["suzgec"]
    islem, yok, sayim = [], [], {}
    for tf in on["tanim"]["dilimler"]:
        for yon in ("devam", "ters"):
            rs = [r for r in adaylar if r["tf"] == tf and r["giris"].startswith(yon + ":")]
            sayim[f"{tf}_{yon}"] = len(rs)
            uygun = [r for r in rs if r["n"] >= k["en_az_islem"] and r["ort_R"] > 0
                     and (r.get("y1_R") or 0) > 0 and (r.get("y2_R") or 0) > 0]
            if not uygun:
                en = max((r for r in rs if r["n"] >= k["en_az_islem"]), key=lambda r: r["ort_R"], default=None)
                if en is None:
                    yok.append({"tf": tf, "yon": yon, "aday": len(rs), "en_iyi": None, "en_iyi_suzgec": None,
                                "en_iyi_deger": None, "en_iyi_R": None, "en_iyi_y1": None, "en_iyi_y2": None,
                                "en_iyi_n": 0})
                    continue
                yok.append({"tf": tf, "yon": yon, "aday": len(rs), "en_iyi": en["giris"], "en_iyi_suzgec": en["suzgec"],
                            "en_iyi_deger": en["deger"], "en_iyi_R": en["ort_R"], "en_iyi_y1": en.get("y1_R"),
                            "en_iyi_y2": en.get("y2_R"), "en_iyi_n": en["n"]})
                continue
            en = max(uygun, key=lambda r: r["ort_R"])
            islem.append({"tf": tf, "yon": yon, "giris": en["giris"], "suzgec": en["suzgec"], "deger": en["deger"],
                          "aday": len(rs), "uygun": len(uygun),
                          "ic": {x: en.get(x) for x in ("n", "dolum", "kazanma", "ort_R", "brut_R", "y1_R", "y2_R",
                                                         "risk_pip_med")}})
    referans = [{"tf": tf, "giris": r["giris"], "okuma": r["okuma"], "suzgec": None, "deger": None}
                for tf in on["tanim"]["dilimler"] for r in on["referans"]]
    out = {"onkayit_ozu": hashlib.sha256(on_yol.read_bytes()).hexdigest(),
           "gelistir_ozu": hashlib.sha256(gel_yol.read_bytes()).hexdigest(),
           "aday_toplam": sum(sayim.values()), "aday": sayim, "islem": islem, "islem_yok": yok, "referans": referans}
    (VERI / "buyuk_plan.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for x in islem:
        i = x["ic"]
        print(f"  İŞLEM {x['tf']:>2} dk {x['yon']:5} {x['giris']:24} {x['suzgec'] or '—'}={x['deger'] or '—'} "
              f"(uygun {x['uygun']}/{x['aday']}) n {i['n']} kaz {i['kazanma']:.1%} net {i['ort_R']:+.3f} "
              f"[{i['y1_R']:+.3f} · {i['y2_R']:+.3f}]")
    for x in yok:
        print(f"  işlem yok {x['tf']:>2} dk {x['yon']:5} (en iyi {x['en_iyi']} {x['en_iyi_suzgec']}={x['en_iyi_deger']} "
              f"{x['en_iyi_R']:+.3f})")
    print(f"  aday toplam {out['aday_toplam']} · referans {len(referans)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
