#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — dersin BÜTÜN ölçülmüş sayılarını üreten tek katman.

Bölüm başına bir modül (`olcum_b01.py` … `olcum_b13.py`); bu dosya onları
koşturur ve `veri/olcum.json`a yazar. Metin (`dogrula.py`) ve figürler
(`sekil.py`) yalnız bu dosyadan okur: sayıyı üreten yer tektir.

Ölçüm dosyası iki öz taşır: okunan her arşiv dosyasının sha256'sı (künyeden)
ve her ölçüm betiğinin kendi özü. Arşiv ya da betik değişip bu adım yeniden
koşulmazsa doğrulayıcı düşer.

Koşum:  python3 olcum.py            (veri/olcum.json'u yazar)
        python3 olcum.py --denetle  (yeniden hesaplar, depodakiyle kıyaslar)
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import time
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
import ortak_olc as oo  # noqa: E402

CIKTI = BURASI / "veri" / "olcum.json"
MODULLER = [f"olcum_b{i:02d}" for i in range(1, 14)]
ORTAK_BETIKLER = ["ortak_olc.py", "bulut.py", "hazirla.py", "hazirla_bulut.py"]


def betik_ozleri() -> dict:
    out = {}
    for ad in ORTAK_BETIKLER + [f"{m}.py" for m in MODULLER]:
        p = BURASI / ad
        if p.exists():
            out[ad] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def hesapla() -> dict:
    out = {"cipa": {"gunluk": str(oo.CIPA_GUN.date()), "aylik": str(oo.CIPA_AY), "ceyreklik": str(oo.CIPA_CEYREK)},
           "arsiv_ozleri": oo.ozler(), "betik_ozleri": betik_ozleri(), "sure_sn": {}, "eksik_modul": []}
    for m in MODULLER:
        if not (BURASI / f"{m}.py").exists():
            out["eksik_modul"].append(m)
            continue
        t0 = time.monotonic()
        mod = importlib.import_module(m)
        out[m.replace("olcum_", "")] = mod.olc()
        out["sure_sn"][m] = round(time.monotonic() - t0, 1)
        print(f"  · {m}: {out['sure_sn'][m]} sn", flush=True)
    return out


def _metin(d: dict) -> str:
    # süre ölçüm değildir; kıyas ve öz dışı tutulur
    kopya = {k: v for k, v in d.items() if k != "sure_sn"}
    return json.dumps(kopya, ensure_ascii=False, indent=1, sort_keys=True, allow_nan=False)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--denetle", action="store_true")
    a = ap.parse_args()
    d = hesapla()
    if a.denetle:
        eski = json.loads(CIKTI.read_text(encoding="utf-8"))
        if _metin(eski) != _metin(d):
            farkli = sorted(k for k in set(eski) | set(d) if k != "sure_sn" and eski.get(k) != d.get(k))
            print(f"✗ ölçüm dosyası güncel değil; farklı anahtarlar: {farkli}")
            return 1
        print("✓ ölçüm dosyası yeniden hesapla birebir aynı")
        return 0
    CIKTI.write_text(_metin(d) + "\n", encoding="utf-8")
    print(f"── {CIKTI.name} yazıldı ({CIKTI.stat().st_size // 1024} KB; eksik: {d['eksik_modul']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
