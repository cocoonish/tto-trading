#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bulutta indirilen ham girdi dizinlerinin SHA-256 sabitlemesi: Dukascopy'nin saatlik mum dosyaları (kalite
denetiminin çapraz sınaması) ve takvimin ham sayfaları (takvim_kur).

Yıllık dakika dosyalarının özü kendi künyesinde durur (dukascopy.oku_ham). Bu iki dizin ise indirildikleri bulut
koşusunda yalnız boyutlarıyla kaydedilmişti; özleri dizinin kendi `ozler.json` dosyasında durur ve okuyucu dizini
okumadan önce sınar: değişmiş, eksik ya da kayıtsız bir dosya ölçüme giremez. Dosyayı indirici yazar (arşivin
bulut koşusu dizini tamamladığında); elle yazmak için:

    .venv/bin/python ozler.py yaz veri/dukascopy/saatlik veri/takvim/ham
    .venv/bin/python ozler.py sina veri/dukascopy/saatlik veri/takvim/ham
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

OZ_DOSYA = "ozler.json"


class OzHatasi(RuntimeError):
    """Ham girdi dizini kayıtlı özleriyle aynı değil."""


def _oz(yol: Path) -> str:
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for parca in iter(lambda: f.read(1 << 20), b""):
            h.update(parca)
    return h.hexdigest()


def _dosyalar(dizin: Path) -> list[Path]:
    return sorted(p for p in dizin.rglob("*") if p.is_file() and p.name != OZ_DOSYA)


def hesapla(dizin: Path) -> dict[str, str]:
    return {p.relative_to(dizin).as_posix(): _oz(p) for p in _dosyalar(dizin)}


def yaz(dizin: Path) -> int:
    oz = hesapla(dizin)
    (dizin / OZ_DOSYA).write_text(json.dumps(oz, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                  encoding="utf-8")
    return len(oz)


def sorunlar(dizin: Path) -> list[str]:
    """Kayıtlı özle ayrışan, kayıtlı olup diskte olmayan ve diskte olup kayıtlı olmayan dosyalar."""
    kayit_yol = dizin / OZ_DOSYA
    if not kayit_yol.exists():
        return [f"{dizin}: {OZ_DOSYA} yok"]
    kayit = json.loads(kayit_yol.read_text(encoding="utf-8"))
    simdi = hesapla(dizin)
    out = []
    out += [f"{a}: özü kayıtlı özle aynı değil" for a in sorted(set(kayit) & set(simdi)) if kayit[a] != simdi[a]]
    out += [f"{a}: kayıtlı dosya yok" for a in sorted(set(kayit) - set(simdi))]
    out += [f"{a}: dosya kayıtlı değil" for a in sorted(set(simdi) - set(kayit))]
    return out


def sina(dizin: Path) -> None:
    s = sorunlar(dizin)
    if s:
        raise OzHatasi(f"{dizin.name}: " + "; ".join(s[:8]) + (f" … (+{len(s) - 8})" if len(s) > 8 else ""))


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("yaz", "sina"):
        print(__doc__)
        return 2
    kod = 0
    for d in argv[1:]:
        dizin = Path(d).resolve()
        if argv[0] == "yaz":
            print(f"{dizin}: {yaz(dizin)} dosyanın özü yazıldı")
        else:
            s = sorunlar(dizin)
            print(f"{dizin}: " + ("temiz" if not s else "\n  ".join(["SORUN"] + s)))
            kod = kod or (1 if s else 0)
    return kod


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
