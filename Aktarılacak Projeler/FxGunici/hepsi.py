#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bütün zincir tek komutla: sınamalar → takvim → takvimin fiyat sınaması → veri denetimi → koşu → ölçüm →
şekiller (ev stiliyle) → ders metinleri → kapı.

Fiyat arşivi ve takvimin ham sayfaları bulutta indirilir (arastirma-veri.yml) ve depoda durur; bu betik ağa çıkmaz.
Arşivin yıllık dakika dosyaları, kalite denetiminin saatlik çapraz sınama dosyaları ve takvimin ham sayfaları okunurken
künyelerindeki SHA-256 özlerine karşı sınanır (dukascopy.oku_ham, kalite.saatlik_oz, takvim_kur), yani zincir
değişmiş bir girdi dosyasıyla koşamaz. Takvim veri denetiminden ÖNCE kurulur: veri denetiminin haber makası ölçüsü
takvimi okur ve eski bir takvimle ölçmemelidir.

Adımlardan biri düşerse SONRAKİ adımlar koşmaz; ama önceki adımların yazdığı dosyalar diskte kalır (ör. ders metinleri
adımı düşerse yeni ölçüm ve yeni figürler eski derslerle birlikte durur). Bu yarım hâli kapı (dogrula.py) yakalar ve
düşer: kapıdan geçmeyen bir çalışma ağacı commit edilmez.

Ön koşul: ön kaydın git geçmişini baştan sona taşıyan bir klon. Ön kaydın geçmişi (metodoloji dersindeki tablo)
depodan okunur; git'siz bir kopyada ya da sınırı ön kaydın ilk commit'ini kesen sığ bir klonda (git clone --depth 1,
actions/checkout öntanımlısı) zincir ilk adımda adıyla düşer — geçmiş uydurulmaz. Öyle bir klonda: git fetch
--deepen=N ya da --unshallow.

Ortam:  python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt   (sürümleri sabit)
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
    ("takvim", [PY, "takvim_kur.py"], None),
    ("takvimin fiyat sınaması", [PY, "takvim_sina.py"], None),
    ("veri denetimi", [PY, "kalite.py"], None),
    ("strateji koşusu", [PY, "kosu.py"], "kosu"),
    ("ölçüm", [PY, "ders_olcum.py"], None),
    ("şekiller", [PY, "sekil.py"], None),
    ("ders metinleri", [PY, "ders_yaz.py"], None),
    ("kapı", [PY, "dogrula.py"], None),
]


def git_on_kosulu() -> str | None:
    """Ön kaydın git geçmişi baştan sona okunabiliyor mu (tek tanım: ders_olcum.gecmis_sorunu); okunamıyorsa zincir
    hesaba girişmeden düşer."""
    import ders_olcum
    return ders_olcum.gecmis_sorunu()


def main(argv: list[str]) -> int:
    sorun = git_on_kosulu()
    if sorun:
        print(f"✗ ön koşul: {sorun}")
        return 2
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
