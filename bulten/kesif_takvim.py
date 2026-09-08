"""KEŞİF — ulusal veri yayımlama takviminin (TÜİK/TCMB/HMB) GERİYE dönük listesi.

Depoya yazmaz; veri.yml'in `kesif` girdisiyle koşar (contents: read). Amaç: her
hattın tarifinin takvimde neye denk geldiğini ve tarifsiz kalan yayımları ADIYLA
görmek — "bulamadım" ile "yok" aynı şey değildir, katalog tahmin edilmez, istenir.
"""
from __future__ import annotations

import datetime as dt
import re
import sys
from collections import defaultdict
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(BURASI.parent))
import tazeleme as tz                                          # noqa: E402

simdi = dt.datetime.now()
yayim, ok = tz._yayimlar((simdi.year,))
print(f"takvim alındı: {ok} · kayıt {len(yayim)} · şimdi {simdi:%Y-%m-%d %H:%M}")
if not yayim:
    raise SystemExit(1)

def an(k):
    return tz._an(k.get("an", ""))

# 1) Her tarif için: eşleşen seriler, son yayım (≤ şimdi) ve sıradaki yayım (> şimdi)
print("\n══ TARİF → TAKVİM ══")
for t in tz.TETIKLER:
    kaliplar = [(t.kalip, t.kurum)] if t.kalip else []
    kaliplar += [(k, ku) for k, ku, _a in t.ek_kaynaklar]
    if not kaliplar:
        print(f"\n▶ {t.hat}: takvim tarifi yok (ihale={t.ihale} strateji={t.strateji} en_gec={t.en_gec})")
        continue
    print(f"\n▶ {t.hat} (en_gec {t.en_gec})")
    for kalip, kurum in kaliplar:
        eslesen = [k for k in yayim if (not kurum or k["kurum"] in kurum) and re.search(kalip, k["adi"], re.I)]
        adlar = defaultdict(list)
        for k in eslesen:
            a = an(k)
            if a: adlar[(k["kurum"], k["adi"])].append(a)
        if not adlar:
            print(f"   ✗ {kalip!r} {kurum}: takvimde EŞLEŞME YOK")
        for (ku, ad), anlar in sorted(adlar.items()):
            gec = [a for a in anlar if a <= simdi]; gel = [a for a in anlar if a > simdi]
            print(f"   · {ku}: {ad} — son {max(gec):%d.%m %H:%M} · sıradaki {min(gel):%d.%m %H:%M}" if gec and gel
                  else f"   · {ku}: {ad} — son {max(gec):%d.%m %H:%M}" if gec
                  else f"   · {ku}: {ad} — ilk {min(gel):%d.%m %H:%M}")

# 2) TCMB/HMB/TÜİK'in bütün serileri: son yayım ≤ şimdi, sıradaki, toplam sayı
print("\n══ KATALOG (kurum · seri · son yayım · sıradaki · yılda kaç) ══")
kat = defaultdict(list)
for k in yayim:
    a = an(k)
    if a and k["kurum"] in ("TCMB", "HMB", "TÜİK", "TUİK", "TÜİK "):
        kat[(k["kurum"], k["adi"])].append(a)
for (ku, ad), anlar in sorted(kat.items()):
    gec = [a for a in anlar if a <= simdi]; gel = [a for a in anlar if a > simdi]
    son = f"{max(gec):%d.%m}" if gec else "—"; sira = f"{min(gel):%d.%m}" if gel else "—"
    print(f"{ku:5s} · {ad[:70]:70s} · son {son} · sıradaki {sira} · {len(anlar)}/yıl")
print(f"\n{len(kat)} seri listelendi.")
