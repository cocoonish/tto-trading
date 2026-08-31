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
    # Küresel blok varsa düzleştirilip aynı özete katılır. YOKSA anahtarları da
    # yoktur — <Deger> statik yedeğe düşer. Eski değeri taşımak, ölçülmemiş bir
    # sayıyı ölçülmüş gibi göstermek olurdu.
    kur_yol = DATA / "kuresel.json"
    if kur_yol.exists():
        G = json.loads(kur_yol.read_text(encoding="utf-8"))
        duz.update({k: v for k, v in G.items()
                    if not isinstance(v, (list, dict)) and not k.startswith("_")})
        duz["kuresel_tarih"] = G["_tarih"]
        duz["kuresel_ay"] = G["_ay"]
        # Kırılımın tepesi ve dibi metinde adıyla anılıyor; listeyi MDX'e
        # taşımak yerine iki ucu alan olarak veriyoruz.
        kir = [d for d in (G.get("kirilim") or [])
               if d.get("fark") is not None and not d.get("toplu")]
        if kir:
            en = max(kir, key=lambda d: d["fark"]); dip = min(kir, key=lambda d: d["fark"])
            duz["kirilim_tepe_ad"] = en["baslik"]; duz["kirilim_tepe_fark"] = en["fark"]
            duz["kirilim_dip_ad"] = dip["baslik"]; duz["kirilim_dip_fark"] = dip["fark"]
        duz["fed_olculen"] = len(G.get("fed_yol") or [])
    else:
        print("  ! kuresel.json yok — özet yalnız Türkiye ölçümünü taşıyor")

    hedef = PROJE.parent.parent / "site" / "public" / "projeler" / "el-nino"
    hedef.mkdir(parents=True, exist_ok=True)
    (hedef / "ozet.json").write_text(
        json.dumps(duz, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"── özet yazıldı: {hedef/'ozet.json'} ({len(duz)} alan)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
