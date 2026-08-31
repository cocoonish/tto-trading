# -*- coding: utf-8 -*-
"""El Niño hattı — ÖZET: site/public/projeler/el-nino/ozet.json"""
from __future__ import annotations

import json
from pathlib import Path

PROJE = Path(__file__).resolve().parent
DATA = PROJE / "data"


def main() -> int:
    M = json.loads((DATA / "metrik.json").read_text(encoding="utf-8"))
    duz = {k: v for k, v in M.items()
           if not isinstance(v, (list, dict)) and not k.startswith("_")}
    duz["_tarih"] = M["_tarih"]
    duz["_ay"] = M["_ay"]
    duz["epizot_sayisi"] = len(M.get("epizotlar") or [])
    duz["olculen_epizot"] = len(M.get("epizot_sonrasi") or [])
    hedef = PROJE.parent.parent / "site" / "public" / "projeler" / "el-nino"
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / "ozet.json").write_text(
        json.dumps(duz, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── özet yazıldı: {hedef/'ozet.json'} ({len(duz)} alan)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
