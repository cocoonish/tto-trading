# -*- coding: utf-8 -*-
"""Büyüme hattı — ÖZET katmanı: site/public/projeler/buyume/ozet.json.

Sayfa metnindeki oynak sayılar <Deger proje anahtar> ile buraya bağlanır;
JSON tazelenince metin MDX'e dokunmadan güncellenir (CLAUDE.md kural 5).
"""
from __future__ import annotations

import json
from pathlib import Path

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"


def main() -> int:
    M = json.loads((DATA / "metrik.json").read_text(encoding="utf-8"))
    o: dict = {
        "_tarih": M["_tarih"],
        "_ceyrek": M["_ceyrek"],
        "buyume_yillik": M["buyume_yillik"],
        "buyume_ceyreklik": M["buyume_ceyreklik"],
        "buyume_yillik_uretim": M["buyume_yillik_uretim"],
        "agirlik_donemi": M["agirlik_donemi"],
        "katki_toplami": M["katki_toplami"],
        "artik": M["artik"],
    }
    for kod, v in M["katkilar"].items():
        o[f"k_{kod.lower()}_buyume"] = v["buyume"]
        o[f"k_{kod.lower()}_katki"] = v["katki"]
        o[f"k_{kod.lower()}_agirlik"] = v["agirlik"]
    for kod, v in M["sektorler"].items():
        o[f"s_{kod.lower()}_buyume"] = v["buyume"]
        o[f"s_{kod.lower()}_agirlik"] = v["agirlik"]
    for kod, v in M["dayaniklilik"].items():
        o[f"d_{kod.lower()}_buyume"] = v["nominal_buyume"]
        o[f"d_{kod.lower()}_pay"] = v["pay"]

    hedef = PROJE.parent.parent / "site" / "public" / "projeler" / "buyume"
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / "ozet.json").write_text(
        json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── özet yazıldı: {hedef/'ozet.json'} ({len(o)} alan)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
