#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ORTA DOĞU UYARISI — atıf kaynaklarının METNİ (donmuş).

Bulutun indirdiği ham sayfalar (`veri/ham/kaynak/`, `elcilik/`, `wiki/`, `tahmin/`) olduğu gibi durur; bu betik onlardan
okunabilir metni çıkarıp `veri/kaynak_metin/<ad>.txt.gz` altına yazar. Çıkarma ve normalleştirme Brent analizinin
`kaynak_metin` modülünden (tek tanım: alıntıyı sınayan kapı da aynı `normal`i kullanır). Kapı (`dogrula.py`) ham
dosyanın özünü bulut künyesiyle, metnin hangi ham dosyadan çıkarıldığını ve alıntının o metinde geçtiğini sorar.

  python3 kaynak_metin.py          # yerelde; pypdf gerekir (PDF'ler için)
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "ham"
CIKTI = BURASI / "veri" / "kaynak_metin"
DIZIN = BURASI / "veri" / "kaynak_metin.json"
KLASOR = ("kaynak/", "elcilik/", "wiki/", "tahmin/")


def _brent():
    spec = importlib.util.spec_from_file_location("brent_kaynak_metin", BURASI.parent / "BrentSenaryo" / "kaynak_metin.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main() -> int:
    km = _brent()
    CIKTI.mkdir(parents=True, exist_ok=True)
    dizin = {}
    for p in sorted(HAM.glob("kunye_*.json")):
        for yol, k in json.loads(p.read_text(encoding="utf-8")).items():
            if not yol.startswith(KLASOR) or k.get("durum") != 200:
                continue
            govde = gzip.decompress((HAM / yol).read_bytes())
            oz = hashlib.sha256(govde).hexdigest()
            if oz != k["sha256"]:
                raise SystemExit(f"öz tutmuyor: {yol} ({oz[:12]} ≠ {k['sha256'][:12]})")
            if govde[:5] == b"%PDF-":
                tur, (ham_metin, _) = "pdf", km.pdf_metin(govde)
            elif govde.lstrip()[:1] in (b"{", b"["):
                tur, ham_metin = "json", govde.decode("utf-8", errors="replace")
            else:
                tur, ham_metin = "html", km.html_metin(govde)
            metin = km.normal(ham_metin)
            ad = yol.replace("/", "__").split(".")[0]
            veri = metin.encode("utf-8")
            with open(CIKTI / f"{ad}.txt.gz", "wb") as f:
                with gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
                    g.write(veri)
            dizin[yol] = {"url": k["url"], "tur": tur, "kaynak_sha256": oz, "metin": f"kaynak_metin/{ad}.txt.gz",
                          "metin_sha256": hashlib.sha256(veri).hexdigest(), "karakter": len(metin)}
    DIZIN.write_text(json.dumps(dict(sorted(dizin.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── {len(dizin)} kaynak metni → {DIZIN.relative_to(BURASI)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
