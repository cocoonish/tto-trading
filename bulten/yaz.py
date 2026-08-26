#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Yazı katmanının bülten dosyasına güvenle yazması için ara katman.

Yazı katmanı (bir Claude oturumu) bültenin ÖLÇÜLEN kısmına dokunmamalı: piyasa
fotoğrafı, takvim, göstergeler ve hat hat değişim hep deterministik koşudan
gelir. Yazan taraf yalnız dört alana dokunur:

    yorum     "Günün/Haftanın okuması" — HTML paragraflar
    ozet      {"ne_oldu": "...", "ne_bekleniyor": "..."}
    gundem    bölüm kimliği → HTML metin (bkz. ayar.GUNDEM_YAZI_BOLUMLERI)
    (gundem_kaynagi otomatik "yazili" olur — sayfa yalnız bunu yayımlar)

Kullanım — yama dosyası ya da borudan JSON:

    python3 bulten/yaz.py yama.json
    cat yama.json | python3 bulten/yaz.py -
    python3 bulten/yaz.py yama.json --tarih 2026-08-26

Yama, mevcut içeriğin ÜZERİNE yazar ama dosyadaki diğer her şeyi korur; bir
bölümü boş göndermek onu silmez (kazara boşaltmaya karşı). Silmek gerekirse
alanın değeri olarak açıkça null verilir.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

BURASI = Path(__file__).resolve().parent
BULTEN = BURASI.parent / "site" / "src" / "data" / "bulten"

YAZILABILIR = ("yorum", "ozet", "gundem")


def uygula(hedef: Path, yama: dict) -> tuple[dict, list[str]]:
    b = json.loads(hedef.read_text(encoding="utf-8"))
    degisen: list[str] = []

    yabanci = [k for k in yama if k not in YAZILABILIR]
    if yabanci:
        raise SystemExit(
            f"yazı katmanı bu alanlara dokunamaz: {', '.join(yabanci)}\n"
            f"dokunabileceği alanlar: {', '.join(YAZILABILIR)}\n"
            "ölçülen alanlar (piyasa, takvim, gostergeler, gruplar) deterministik "
            "koşudan gelir; elle yazılırsa bülten ölçüm olmaktan çıkar.")

    if "yorum" in yama:
        y = yama["yorum"]
        if y is None:
            b["yorum"], b["yorum_zamani"] = None, None
            degisen.append("yorum silindi")
        elif str(y).strip():
            b["yorum"] = y
            b["yorum_zamani"] = date.today().isoformat()
            degisen.append(f"yorum ({len(str(y).split())} kelime)")

    if "ozet" in yama and isinstance(yama["ozet"], dict):
        mevcut = b.get("ozet") or {}
        for k in ("ne_oldu", "ne_bekleniyor"):
            if k in yama["ozet"] and str(yama["ozet"][k] or "").strip():
                mevcut[k] = yama["ozet"][k]
                degisen.append(f"ozet.{k}")
        b["ozet"] = mevcut

    if "gundem" in yama and isinstance(yama["gundem"], dict):
        mevcut = b.get("gundem") or {}
        for k, v in yama["gundem"].items():
            if str(v or "").strip():
                mevcut[k] = v
                degisen.append(f"gundem.{k} ({len(str(v).split())} kelime)")
        b["gundem"] = mevcut
        # Sayfa yalnız 'yazili' bültenleri yayımlar; yazan taraf bunu elle
        # işaretlemek zorunda kalmasın diye burada damgalanır.
        if mevcut:
            b["gundem_kaynagi"] = "yazili"

    return b, degisen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("yama", help="yama JSON dosyası ('-' → standart girdi)")
    ap.add_argument("--tarih", default=None, help="YYYY-MM-DD (varsayılan: bugün)")
    ap.add_argument("--yazma", action="store_true", help="dosyaya yazma, ne olacağını göster")
    a = ap.parse_args()

    ham = sys.stdin.read() if a.yama == "-" else Path(a.yama).read_text(encoding="utf-8")
    try:
        yama = json.loads(ham)
    except ValueError as e:
        print(f"yama okunamadı: {e}", file=sys.stderr)
        return 2

    t = a.tarih or date.today().isoformat()
    hedef = BULTEN / f"{t}.json"
    if not hedef.exists():
        print(f"bülten yok: {hedef.name} — önce 'python3 bulten.py' koşmalı", file=sys.stderr)
        return 2

    # Birleştirme sürücüsünü kur. Bülten dosyasına hem otomatik koşu hem yazı
    # katmanı dokunuyor; sürücü .git/config'de durduğu ve depoyla taşınmadığı
    # için her koşuda yeniden yazılmalı. Eskiden yalnız bulten.py kuruyordu,
    # ama yazı katmanı bülten zaten üretilmişse bulten.py'yi hiç çağırmıyor —
    # o durumda push sırasındaki çakışma çözümsüz kalıyordu.
    try:
        sys.path.insert(0, str(BURASI))
        import birlestir
        birlestir.kur()
    except Exception:
        pass                       # sürücü kurulamazsa yazma işlemi etkilenmez

    b, degisen = uygula(hedef, yama)
    if not degisen:
        print("yamada yazılacak içerik yok")
        return 0
    if a.yazma:
        print("(yazılmadı) " + " · ".join(degisen))
        return 0
    hedef.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{hedef.name} güncellendi: " + " · ".join(degisen))
    return 0


if __name__ == "__main__":
    sys.exit(main())
