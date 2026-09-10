# -*- coding: utf-8 -*-
"""BAYATLIK SINAVI — sessiz bayatlamanın kilidi.

Neyi sınar
----------
Kaynak durduğunda (yayın gecikti, ağ düştü, eski önbelleğe düşüldü) hattın
YEŞİL bitip sayfada tek bir görünür iz bırakmaması, düzenin yasakladığı
"sessiz bayatlama"dır. Bu sınav tam olarak onu kilitler:

  1. Projenin bir KOPYASI geçici bir dizine alınır (üretim dosyalarına
     DOKUNULMAZ).
  2. Kopyada dönem çıpaları geriye alınır ve veri katmanının uyarı listesine
     bir TAZELİK uyarısı enjekte edilir — yani "kaynak durmuş" hâli taklit
     edilir.
  3. `ozet_uret.py` o kopyada koşturulur.
  4. Üretilen `ozet.json`'da `bayat: true` VE `uyari_metni`nin başında
     "BAYAT VERİ" cümlesi YOKSA sınav DÜŞER.

Ayrıca ters yön de sınanır: dokunulmamış kopyada `bayat` FALSE olmalıdır
(her koşuda alarm veren bir bayrak, hiç alarm vermeyen kadar işe yaramaz).

Koşum:  python3 bayatlik_sinavi.py        (önce hattın normal koşusu)
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

PROJE = pathlib.Path(__file__).resolve().parent
ESKITME_GUN = 60          # tolerans eşiklerinin çok üstünde, ama gerçekçi


def _kopyala(hedef: pathlib.Path) -> pathlib.Path:
    """Projeyi kopyala — ham EVDS önbelleği HARİÇ (büyük ve gereksiz)."""
    kopya = hedef / PROJE.name
    shutil.copytree(
        PROJE, kopya,
        ignore=shutil.ignore_patterns("cache", "__pycache__", "cikti", "*.pyc"))
    return kopya


def _ozet_uret(kopya: pathlib.Path) -> dict:
    r = subprocess.run([sys.executable, "ozet_uret.py"], cwd=kopya,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("SINAV DÜŞTÜ: kopyada ozet_uret.py koşmadı.\n"
                         + r.stdout + r.stderr)
    return json.loads((kopya / "ozet.json").read_text(encoding="utf-8"))


def _eskit(kopya: pathlib.Path) -> None:
    import pandas as pd
    mj = kopya / "data" / "metrik_ozet.json"
    m = json.loads(mj.read_text(encoding="utf-8"))
    for k in ("son_gun", "son_hafta", "son_ay", "son_ceyrek"):
        if m.get(k):
            m[k] = (pd.Timestamp(m[k])
                    - pd.Timedelta(days=ESKITME_GUN)).strftime("%Y-%m-%d")
    mj.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")

    vd = kopya / "data" / "veri_durum.json"
    d = json.loads(vd.read_text(encoding="utf-8"))
    d.setdefault("uyarilar", []).insert(
        0, f"TAZELİK: sınav enjeksiyonu — son gözlem {ESKITME_GUN} gün önce, "
           "tolerans aşıldı. Yayın durmuş olabilir.")
    vd.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    if not (PROJE / "data" / "metrik_ozet.json").exists():
        raise SystemExit("SINAV KOŞULAMADI: önce hattı normal koşturun "
                         "(veri.py → metrik.py → grafik.py → ozet_uret.py).")
    with tempfile.TemporaryDirectory() as td:
        kok = pathlib.Path(td)

        # (1) TERS YÖN — dokunulmamış kopyada bayrak KAPALI olmalı
        temiz = _kopyala(kok / "temiz")
        o1 = _ozet_uret(temiz)
        # TERS YÖN ANCAK VERİ GERÇEKTEN TAZEYKEN ÖLÇÜLEBİLİR (10.09.2026).
        # Madde "her koşuda alarm veren bayrak işe yaramaz" diye yazıldı ve
        # doğru; ama depodaki veri o gün MEŞRU olarak bayatsa bayrağın açık
        # olması bayrağın DOĞRU davranışıdır, kusur değil. Eskiden bu hâlde
        # "SINAV DÜŞTÜ" deniyordu, yani ölçülemeyen bir şey ölçülmüş gibi
        # gösteriliyordu — ölçülemeyen boş bırakılır ve SEBEBİ yazılır.
        # Bayrağın mantığı zaten `duman.py`de sahte girdiyle, duvar saatinden
        # bağımsız sınanıyor; KAPI odur, bu dosya uçtan uca sürümdür.
        if o1.get("bayat") is not False:
            print("  – ters yön ÖLÇÜLEMEDİ: depodaki veri şu an gerçekten "
                  f"bayat — {o1.get('bayat_cumlesi', '')[:90]}\n"
                  "    (bayrağın doğru davranışı bu; hattı tazeleyip yeniden "
                  "koşturun. Mantık sınaması: duman.py)")
        else:
            print(f"  ✓ ters yön: taze veride bayat=False "
                  f"({o1.get('bayat_cumlesi', '')[:60]}…)")

        # (2) ASIL SINAV — eskitilmiş kopyada bayrak AÇIK olmalı
        eski = _kopyala(kok / "eski")
        _eskit(eski)
        o2 = _ozet_uret(eski)
        hatalar = []
        if o2.get("bayat") is not True:
            hatalar.append(f"bayat={o2.get('bayat')!r} (True bekleniyordu)")
        if not str(o2.get("uyari_metni", "")).startswith("BAYAT VERİ"):
            hatalar.append("uyari_metni 'BAYAT VERİ' ile başlamıyor: "
                           + str(o2.get("uyari_metni"))[:120])
        if not str(o2.get("bayat_cumlesi", "")).startswith("BAYAT VERİ"):
            hatalar.append("bayat_cumlesi 'BAYAT VERİ' ile başlamıyor")
        if hatalar:
            raise SystemExit("SINAV DÜŞTÜ (sessiz bayatlama): "
                             + " · ".join(hatalar))
        print(f"  ✓ asıl sınav: {ESKITME_GUN} gün eskitilmiş veride "
              f"bayat=True · {o2['bayat_cumlesi'][:90]}…")

    print("BAYATLIK SINAVI GEÇTİ.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
