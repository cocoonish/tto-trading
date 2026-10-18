#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ders metinleri: metin/<slug>.md şablonlarını ölçüm dosyasıyla MDX'e çevirir ve siteye yazar.

Çıktı:
  site/src/content/arastirma/<slug>.mdx            serinin dersleri (adlar.DERS_SIRA)
  site/public/arastirma/fx-gunici/onkayit.toml     ön kaydın yayımlanan kopyası (metodoloji dersi bağ verir)

Sayıların hepsi ölçüm dosyasından gelir. Bir şablonda bir iddia tutmazsa, bir yer tutucu ölçülemezse ya da bir
dersin gömdüğü figür sitede yoksa üretim düşer ve HİÇBİR dosya yazılmaz: serinin dersleri aynı ölçümün görünüşleridir,
yarısı yeni yarısı eski bir seri yayımlanmaz.

Koşum:  .venv/bin/python ders_yaz.py [--olcum <yol>] [--denetle]
  --denetle   yazmaz; üretilen metni sitedeki dosyalarla karşılaştırır, fark varsa çıkış 1
"""
from __future__ import annotations

import shutil
import sys
import tomllib
from pathlib import Path

import adlar
import ders_motor as dm

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
OLCUM = BURASI / "cikti" / "ders" / "olcum.json"
ONKAYIT = BURASI / "onkayit.toml"
ICERIK = KOK / "site" / "src" / "content" / "arastirma"
SEKIL = KOK / "site" / "public" / "arastirma" / "fx-gunici"


def uret(olcum_yol: Path = OLCUM) -> dict[str, tuple[str, dm.Uretim]]:
    """Sekiz dersin MDX'i (sırayla). Hata varsa SablonHatasi yükselir; kısmi sonuç dönmez."""
    o = dm.olcum_oku(olcum_yol)
    on = tomllib.loads(ONKAYIT.read_text(encoding="utf-8"))
    cikti = {}
    for slug in adlar.DERS_SIRA:
        sablon = (BURASI / "metin" / f"{slug}.md").read_text(encoding="utf-8")
        try:
            cikti[slug] = dm.ders_uret(sablon, o, on)
        except dm.SablonHatasi as e:
            raise dm.SablonHatasi(f"{slug}: {e}") from e
    return cikti


def eksik_sekiller(cikti: dict[str, tuple[str, dm.Uretim]]) -> list[str]:
    return [f"{slug}: {ad}.html" for slug, (_, u) in cikti.items() for ad in u.sekiller
            if not (SEKIL / f"{ad}.html").exists()]


def main(argv: list[str]) -> int:
    olcum = OLCUM
    if "--olcum" in argv:
        olcum = Path(argv[argv.index("--olcum") + 1])
    try:
        cikti = uret(olcum)
    except dm.SablonHatasi as e:
        print(f"✗ {e}")
        return 1
    eksik = eksik_sekiller(cikti)
    if eksik:
        print("✗ gömülen figür sitede yok:\n  " + "\n  ".join(eksik))
        return 1
    if "--denetle" in argv:
        farkli = [s for s, (mdx, _) in cikti.items()
                  if not (ICERIK / f"{s}.mdx").exists() or (ICERIK / f"{s}.mdx").read_text(encoding="utf-8") != mdx]
        kopya = SEKIL / "onkayit.toml"
        if not kopya.exists() or kopya.read_bytes() != ONKAYIT.read_bytes():
            farkli.append("onkayit.toml (yayımlanan kopya)")
        if farkli:
            print("✗ sitedeki ders metni ölçümle ya da şablonla ayrışıyor:\n  " + "\n  ".join(farkli))
            return 1
        print(f"✓ {len(cikti)} ders güncel")
        return 0
    ICERIK.mkdir(parents=True, exist_ok=True)
    SEKIL.mkdir(parents=True, exist_ok=True)
    for slug, (mdx, u) in cikti.items():
        (ICERIK / f"{slug}.mdx").write_text(mdx, encoding="utf-8")
        print(f"✓ {slug}: {u.sekil_no} şekil · {u.iddia} iddia · {u.yer} yer tutucu")
    shutil.copyfile(ONKAYIT, SEKIL / "onkayit.toml")
    print("✓ ön kaydın yayımlanan kopyası")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
