#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO Trading — günlük bülten üret (kural tabanlı çekirdek).

  python3 bulten.py                 # bugünün bülteni: olay + takvim + haber
  python3 bulten.py --habersiz      # RSS taramasını atla (hızlı, ağsız)
  python3 bulten.py --guncelle      # önce hafif hatları koştur, sonra bülteni üret
  python3 bulten.py --ufuk 35       # takvim ufkunu uzat (gün)
  python3 bulten.py --tur haftalik  # pazar akşamı "haftaya bakış" bülteni
  python3 bulten.py --denetle       # yalnız kalite denetimi (yayın ön koşulu)
  python3 bulten.py --gecmis-kur    # git geçmişinden anlık görüntü deposunu kur (bir kez)
  python3 bulten.py --yeniden-olc   # YAZILMIŞ bülteni bilerek yeniden ölç

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
    ap.add_argument("--denetle", nargs="?", const="bugun", default=None,
                    metavar="TARİH",
                    help="yalnız kalite denetimi koştur (üretim yapma); "
                         "isteğe bağlı YYYY-AA-GG")
    ap.add_argument("--yeniden-olc", action="store_true",
                    help="yazılmış bülteni bilerek yeniden ölç (metni sonra "
                         "güncel ölçüye göre gözden geçirmek şartıyla)")
    ap.add_argument("--gecmis-kur", action="store_true",
                    help="git geçmişinden anlık görüntü deposunu doldur")
    a = ap.parse_args()

    # Bülten dosyalarının git birleştirme sürücüsünü her koşuda yerel
    # yapılandırmaya yaz. `.gitattributes` depoda taşınır ama sürücünün komutu
    # .git/config'de durduğu için makine başına bir kez kurulması gerekir;
    # burada yapmak her makinede kendiliğinden çalışmasını sağlar.
    try:
        import birlestir
        birlestir.kur()
    except Exception:
        pass                      # sürücü kurulamazsa bülten üretimi etkilenmez

    if a.denetle:
        import denetim
        sys.argv = ["denetim.py"] + ([] if a.denetle == "bugun" else [a.denetle]) + ["--ayrinti"]
        return denetim.main()

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
    import json
    from datetime import date
    # Pazar akşamı bülteni haftalıktır; hafta içi sabah bülteni günlük. Cumartesi
    # bülten üretilmez (kullanıcı kararı) ama elle koşulursa günlük kipte çıkar.
    tur = a.tur or ("haftalik" if date.today().weekday() == 6 else "gunluk")

    # ── YAZILMIŞ BÜLTEN EZİLMEZ ────────────────────────────────────────────
    # Ölçüm koşusu yazı katmanından ÖNCE gelir. Tersi olduğunda sayfa
    # ölçülmeyen sayıları anlatmaya başlar: metin korunur (yorum ve gündem
    # korunuyor) ama piyasa fotoğrafı, rejim panosu ve en büyük hareketler
    # ayaklarının altından değişir. 26.08.2026'da tam bu oldu — yazı 04:31'de,
    # ölçüm 05:01'de koştu ve sayfa dört enerji serisinde yayımladığımız
    # sayıları tutmadı.
    #
    # Bu bir varsayım değil, zamanlayıcının fiilî davranışı: bu depoda kayda
    # geçen zamanlanmış koşuların TAMAMI 30–60 dakika gecikmeli başladı.
    # 03:23'e kurulmuş bir ölçüm 04:15'teki yazı katmanının ARDINDAN düşebilir
    # ve o zaman yazıyı sessizce geçersizleştirir. Kapı bu yüzden koda konuldu:
    # rutin metnine ya da iş akışına yazılan bir kural, aracın kendisi
    # dayatmadıkça sigorta sayılmaz.
    hedef = uret.CIKTI / f"{date.today().isoformat()}.json"
    if hedef.exists() and not a.yeniden_olc:
        try:
            onceki = json.loads(hedef.read_text(encoding="utf-8"))
        except Exception:
            onceki = {}
        if onceki.get("gundem_kaynagi") == "yazili":
            print(f"  {hedef.name} ZATEN YAZILMIŞ — ölçüm yeniden kurulmuyor.")
            print(f"  yazı damgası: {onceki.get('yorum_zamani') or '—'} · "
                  f"ölçüm damgası: {onceki.get('olusturma') or '—'}")
            print("  Yazının altındaki ölçüyü değiştirmek, sayfayı ölçmediğimiz")
            print("  sayıları anlatır hale getirir. Ölçüm gerçekten yenilenecekse")
            print("  --yeniden-olc ver ve ARDINDAN metni güncel ölçüye göre")
            print("  gözden geçir (yalnız yorum/özet/gündem korunur).")
            return 0

    b = uret.uret(haber_tara=not a.habersiz, takvim_ufku=a.ufuk, tur=tur)
    print(uret.ozet_yaz(b))
    y = uret.yaz(b)
    print(f"\n  yazıldı: {y.relative_to(KOK)}")
    # Üretimden sonra kalite denetimi HER ZAMAN koşar. Kural tabanlı koşuda yazı
    # katmanı henüz çalışmadığı için engeller beklenir; yorum katmanı yazdıktan
    # sonra bu denetimin TEMİZ geçmesi yayının ön koşuludur.
    print()
    import denetim
    kod = denetim.Denetim(b).kos()
    print("\n  siteyi görmek için: python3 site_baslat.py  →  http://localhost:4321/bulten/")
    if kod:
        print("  (yazı katmanı henüz çalışmadıysa bu engeller normaldir)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
