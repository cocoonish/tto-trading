#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — günlük bülten üret (kural tabanlı çekirdek).

  python3 bulten.py                 # bugünün bülteni: olay + takvim + haber
  python3 bulten.py --habersiz      # RSS taramasını atla (hızlı, ağsız)
  python3 bulten.py --guncelle      # önce hafif hatları koştur, sonra bülteni üret
  python3 bulten.py --ufuk 35       # takvim ufkunu uzat (gün)
  python3 bulten.py --tur haftalik  # pazar akşamı "haftaya bakış" bülteni
  python3 bulten.py --gecmis-kur    # git geçmişinden anlık görüntü deposunu kur (bir kez)

Çıktı: site/src/data/bulten/YYYY-MM-DD.json  → site /bulten/ sayfasında yayımlanır.

Bu script YORUM YAZMAZ. Yorum katmanı ayrı koşar (zamanlanmış Claude görevi) ve
aynı dosyanın 'yorum' alanını doldurur; bu script o alanı KORUR.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK / "bulten"))

for _akis in (sys.stdout, sys.stderr):
    try:
        _akis.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--habersiz", action="store_true")
    ap.add_argument("--guncelle", action="store_true",
                    help="önce guncelle.py ile hafif hatları tazele")
    ap.add_argument("--ufuk", type=int, default=None)
    ap.add_argument("--tur", choices=("gunluk", "haftalik"), default=None,
                    help="haftalik = pazar akşamı 'haftaya bakış' bülteni "
                         "(varsayılan: pazar günü haftalık, diğer günler günlük)")
    ap.add_argument("--gecmis-kur", action="store_true",
                    help="git geçmişinden anlık görüntü deposunu doldur")
    a = ap.parse_args()

    if a.gecmis_kur:
        import gozlem
        from ayar import RITIM
        print("git geçmişinden anlık görüntü deposu kuruluyor…")
        gozlem.git_bootstrap(list(RITIM))
        return 0

    if a.guncelle:
        print("▶ veri hatları tazeleniyor (guncelle.py --hepsi)")
        r = subprocess.run([sys.executable, str(KOK / "guncelle.py"), "--hepsi"], cwd=KOK)
        if r.returncode != 0:
            print("  [uyarı] bazı hatlar düştü; bülten mevcut veriyle üretilecek")

    import uret
    from datetime import date
    # Pazar akşamı bülteni haftalıktır; hafta içi sabah bülteni günlük. Cumartesi
    # bülten üretilmez (kullanıcı kararı) ama elle koşulursa günlük kipte çıkar.
    tur = a.tur or ("haftalik" if date.today().weekday() == 6 else "gunluk")
    b = uret.uret(haber_tara=not a.habersiz, takvim_ufku=a.ufuk, tur=tur)
    print(uret.ozet_yaz(b))
    y = uret.yaz(b)
    print(f"\n  yazıldı: {y.relative_to(KOK)}")
    print("  siteyi görmek için: python3 site_baslat.py  →  http://localhost:4321/bulten/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
