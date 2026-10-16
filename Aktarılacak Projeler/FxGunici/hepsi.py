#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bütün zincir tek komutla: sınamalar → veri denetimi → takvim → koşu → ölçüm → şekiller → ders metinleri → kapı.

Fiyat arşivi ve takvimin ham sayfaları bulutta indirilir (arastirma-veri.yml) ve depoda durur; bu betik ağa çıkmaz.
Arşivin her yıl dosyası okunurken künyedeki özüne karşı sınanır (dukascopy.oku_ham), yani zincir değişmiş bir
dosyayla koşamaz. Adımlardan biri düşerse sonrakiler koşmaz: yarısı yeni yarısı eski bir seri yazılmaz.

Koşum:  .venv/bin/python hepsi.py [--sinamasiz] [--kosusuz]
  --sinamasiz   birim sınamalarını atlar (yalnız yerel yineleme için; yayından önceki koşu sınamalıdır)
  --kosusuz     strateji koşusunu atlar ve depodaki koşu çıktısından ölçer (ders metni yinelemesi için)
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

BURASI = Path(__file__).resolve().parent
PY = sys.executable

ADIMLAR = [
    ("sınamalar", [PY, "-m", "pytest", "-q", "testler"], "sinama"),
    ("veri denetimi", [PY, "kalite.py"], None),
    ("takvim", [PY, "takvim_kur.py"], None),
    ("takvimin fiyat sınaması", [PY, "takvim_sina.py"], None),
    ("strateji koşusu", [PY, "kosu.py"], "kosu"),
    ("ölçüm", [PY, "ders_olcum.py"], None),
    ("şekiller", [PY, "sekil.py"], None),
    ("ders metinleri", [PY, "ders_yaz.py"], None),
    ("kapı", [PY, "dogrula.py"], None),
]


def main(argv: list[str]) -> int:
    atla = {"sinama"} if "--sinamasiz" in argv else set()
    if "--kosusuz" in argv:
        atla.add("kosu")
    t0 = time.monotonic()
    for ad, komut, anahtar in ADIMLAR:
        if anahtar in atla:
            print(f"· {ad}: atlandı")
            continue
        t1 = time.monotonic()
        print(f"▶ {ad}", flush=True)
        r = subprocess.run(komut, cwd=BURASI)
        if r.returncode != 0:
            print(f"✗ {ad} düştü (çıkış {r.returncode}); sonraki adımlar koşmadı")
            return r.returncode
        print(f"✓ {ad} · {time.monotonic() - t1:.0f} sn", flush=True)
    print(f"✓ zincir tamam · {(time.monotonic() - t0) / 60:.1f} dk")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
