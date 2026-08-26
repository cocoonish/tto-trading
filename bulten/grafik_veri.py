#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — sayfadaki küçük grafiklerin verisi.

Proje sayfalarındaki Plotly buraya GİRMEZ. Gömülü plotly.js tek bir grafikte
4,6 MB'a çıkıyor; bir sabah notu o ağırlığı kaldırmaz ve zaten etkileşime de
ihtiyacı yoktur. Onun yerine sayfada satır içi SVG çizilir — kütüphanesiz,
istemci tarafı kodsuz, birkaç kilobayt.

Bu modül yalnız SAYIYI hazırlar; çizim Astro bileşenlerinde.

Kıyas serilerinin adlandırılmasında kural: uydurma etiket yok. Depo 20.08.2026'da
başladığı için "1 ay önce" diye bir eğri henüz YOK; olan en eski anlık görüntü
alınır ve kendi tarihiyle, kaç gün önce olduğuyla etiketlenir. Tarihçe biriktikçe
kıyas noktaları kendiliğinden hedeflenen ufuklara oturur.
"""
from __future__ import annotations

from datetime import datetime

import gozlem

# DİBS eğrisinin çizilecek noktaları: (ozet anahtarı, eksen etiketi, vade yılı)
EGRI = (
    ("spot_3a", "3a", 0.25), ("spot_6a", "6a", 0.5), ("spot_1y", "1y", 1.0),
    ("spot_2y", "2y", 2.0), ("spot_3y", "3y", 3.0), ("spot_5y", "5y", 5.0),
    ("spot_7y", "7y", 7.0), ("spot_9y", "9y", 9.0),
)
# Hedeflenen kıyas ufukları (gün). Tarihçe yetmezse en eskisiyle yetinilir.
KIYAS_UFUK = (7, 30)


def _nokta(d: dict) -> list[float | None]:
    return [d.get(a) if isinstance(d.get(a), (int, float)) else None for a, _, _ in EGRI]


def _yas(t: str) -> int | None:
    try:
        an = datetime.fromisoformat(str(t).replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None
    return (datetime.now() - an).days


def egri() -> dict:
    """DİBS spot eğrisi: bugün + elde ne kadar geçmiş varsa o kadar kıyas."""
    simdi = gozlem.anlik("dibs-verim-egrisi")
    if not simdi:
        return {}
    bugun = _nokta(simdi)
    if sum(x is not None for x in bugun) < 3:
        return {}

    kayitlar = gozlem.gecmis_oku("dibs-verim-egrisi")
    simdiki_v = gozlem._tarih_of(simdi)
    seriler = [{"ad": "bugün", "tarih": simdiki_v, "yas": 0, "deger": bugun}]
    kullanilan = {simdiki_v}
    for ufuk in KIYAS_UFUK:
        aday = None
        for k in kayitlar:                       # eskiden yeniye
            yas = _yas(k.get("t", ""))
            if yas is None or k.get("v") in kullanilan:
                continue
            # Ufka EN YAKIN ama ondan genç olmayan kayıt; yoksa en eskisi.
            if aday is None or abs(yas - ufuk) < abs(aday[0] - ufuk):
                aday = (yas, k)
        if aday is None:
            continue
        yas, k = aday
        nokta = _nokta(k.get("d") or {})
        if sum(x is not None for x in nokta) < 3:
            continue
        kullanilan.add(k.get("v"))
        seriler.append({"ad": f"{yas} gün önce" if yas else "bugün",
                        "tarih": str(k.get("v")), "yas": yas, "deger": nokta})

    return {
        "etiketler": [e for _, e, _ in EGRI],
        "vadeler": [v for _, _, v in EGRI],
        "birim": "%",
        "seriler": seriler,
    }


def hazirla() -> dict:
    e = egri()
    return {"egri": e} if e else {}


if __name__ == "__main__":
    g = hazirla()
    if not g.get("egri"):
        print("eğri verisi yok")
        raise SystemExit(0)
    e = g["egri"]
    print("DİBS spot eğrisi")
    print("  vade   " + "  ".join(f"{x:>6s}" for x in e["etiketler"]))
    for s in e["seriler"]:
        d = "  ".join(f"{x:>6.2f}" if x is not None else "     —" for x in s["deger"])
        print(f"  {s['ad']:>12s} ({s['tarih']})  {d}")
