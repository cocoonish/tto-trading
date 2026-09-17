# -*- coding: utf-8 -*-
"""ZAMAN SINAVI — kapıları İLERİ TARİHLERDE koşturur, saatli bombayı arar.

ARADIĞI KUSUR SINIFI: "donmuş girdi, canlı ölçü". Bir sınama fikstürü sabit
bir tarih taşır, ölçüsü duvar saatini okur; aradaki mesafe büyüdükçe madde
BİR GÜN kendiliğinden düşer. Kapı adımlardan ÖNCE koştuğu için bedeli ağır:
hat komple atlanır, panosu donar, iş akışı her koşuda kırmızı biter — ve
takvim ilerlediği için kendiliğinden GEÇMEZ.

NEDEN KAYNAK OKUYARAK BULUNAMAZ: bu kusurların hepsi BUGÜN yeşil geçer.
17.09.2026'da yayın kapısının ilk basamağı böyle düştü (dört koşu) ve aynı
gün OVP hattında 16.10'da patlayacak bir eşi yalnız ileri tarihli koşuyla
görüldü.

ORTAM UYDURULMAZ, guncelle.py'DEN TÜRETİLİR: kapı üretimdeki gibi bir ALT
SÜREÇ olarak, hattın kendi klasöründe, PYTHONPATH'inde ortak/ ile koşar.
Kendi `runpy` kurulumumuz üç kapıyı gölgeleyip sahte bulgu üretmişti.

VE ÖNCE KENDİNİ SINAR. Bozuk bir harness her kapı için "temiz" (ya da her
kapı için "bomba") der ve ikisi de gerçek sonuca tıpatıp benzer; bu araç
yazılırken tam olarak beş kez böyle oldu. `--kendini-sina` sentetik bir
bomba kurar ve YAKALAYAMAZSA sınav DÜŞER.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import os
import subprocess
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
ORTAK = KOK / "ortak"
# İLERİ GÜNLER: yarın (en yakın bomba), bir ay, bir çeyrek, yarım yıl, bir yıl.
# Yıl sonu ve yıl başı ayrıca — tatil/yıl sınırı kuralları orada kayar.
ILERI_GUN = (1, 30, 90, 180, 365)


def gunler(bugun: dt.date) -> list[str]:
    g = {bugun + dt.timedelta(days=n) for n in ILERI_GUN}
    g |= {dt.date(bugun.year, 12, 31), dt.date(bugun.year + 1, 1, 4)}
    return [x.isoformat() for x in sorted(g) if x > bugun]


def kapilar() -> list[Path]:
    """KAPSAM SÖZLEŞMEDEN: diskteki her `duman.py` artı yayın kapısının ilk
    basamağı. Elle tutulan bir liste, yarın eklenecek hattı sessizce dışarıda
    bırakırdı."""
    y = sorted(KOK.glob("Aktarılacak Projeler/*/duman.py"))
    y += sorted(KOK.glob("Research/*/duman.py"))
    y += sorted(KOK.glob("Research/*/*/duman.py"))
    if (KOK / "bulten/duman.py").exists():
        y.append(KOK / "bulten/duman.py")
    if (KOK / "site/tools/duman_sinav.py").exists():
        y.append(KOK / "site/tools/duman_sinav.py")
    return y


def _kos(yol: Path, gun: str | None) -> int:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
           "PYTHONPATH": os.pathsep.join(
               [str(ORTAK)] + ([p] if (p := os.environ.get("PYTHONPATH")) else []))}
    if gun:
        env["TTO_SAHTE_GUN"] = gun
    else:
        env.pop("TTO_SAHTE_GUN", None)
    try:
        r = subprocess.run([sys.executable, "-u", yol.name], cwd=yol.parent,
                           env=env, capture_output=True, timeout=900)
        return r.returncode
    except subprocess.TimeoutExpired:
        return 124


def _ad(yol: Path) -> str:
    return yol.parent.name if yol.name == "duman.py" else yol.stem


def bir_kapi(yol: Path, gun_listesi: list[str]) -> tuple[str, int, list[str]]:
    taban = _kos(yol, None)
    ayrisan = [g for g in gun_listesi if _kos(yol, g) != taban]
    return _ad(yol), taban, ayrisan


def kendini_sina() -> bool:
    """Sentetik bir bomba kurar: girdisi DONMUŞ, ölçüsü CANLI. Harness onu
    yakalayamıyorsa bu aracın bütün "temiz" hükümleri geçersizdir."""
    with tempfile.TemporaryDirectory(prefix="zaman-sinav-") as d:
        p = Path(d) / "duman.py"
        yarin = dt.date.today() + dt.timedelta(days=1)
        p.write_text(
            "import datetime as dt, sys\n"
            f"CIPA = dt.date({yarin.year}, {yarin.month}, {yarin.day})\n"
            "# DONMUŞ girdi, CANLI ölçü — aranan sınıfın ta kendisi.\n"
            "sys.exit(0 if CIPA > dt.date.today() else 1)\n",
            encoding="utf-8")
        taban = _kos(p, None)
        ileri = _kos(p, (dt.date.today() + dt.timedelta(days=30)).isoformat())
        return taban == 0 and ileri == 1


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument("--is-parcacigi", type=int, default=6)
    a.add_argument("--hizli", action="store_true",
                   help="yalnız harness kendini sınasın, tam tarama yapma")
    n = a.parse_args()

    print("▶ ZAMAN SINAVI — harness önce KENDİNİ sınar")
    if not kendini_sina():
        print("  ✗ harness sentetik bombayı YAKALAYAMADI — ölçüm GEÇERSİZ")
        print("    (bu araç 'temiz' dese de hiçbir hükmü geçerli değil)")
        return 2
    print("  ✓ sentetik bomba yakalandı; ölçüm geçerli")
    if n.hizli:
        return 0

    bugun = dt.date.today()
    gl = gunler(bugun)
    ks = kapilar()
    print(f"\n▶ {len(ks)} kapı × {len(gl)} ileri gün  (taban: bugün {bugun})")
    bomba, atlanan = [], []
    with cf.ThreadPoolExecutor(max_workers=n.is_parcacigi) as hav:
        for ad, taban, ayrisan in hav.map(lambda y: bir_kapi(y, gl), ks):
            if taban != 0:
                atlanan.append((ad, taban))
                print(f"  ? {ad:26} BUGÜN de düşüyor (çıkış {taban}) — "
                      "zaman sınavı hüküm veremez")
            elif ayrisan:
                bomba.append((ad, ayrisan))
                print(f"  ‼ {ad:26} BOMBA → {' '.join(ayrisan)}")
            else:
                print(f"  ✓ {ad:26} {len(gl)} ileri günde sabit")

    print(f"\n{len(ks) - len(bomba) - len(atlanan)}/{len(ks)} kapı temiz · "
          f"bomba {len(bomba)} · hüküm verilemeyen {len(atlanan)}")
    if bomba:
        print("\nBir kapı ileri bir günde bugünden FARKLI sonuç veriyorsa,")
        print("o gün kendiliğinden düşecek demektir. Fikstürün girdisi donmuşsa")
        print("ölçüsü de donmalı; ölçü canlı kalacaksa girdi duvar saatinden türemeli.")
    return 1 if bomba else 0


if __name__ == "__main__":
    raise SystemExit(main())
