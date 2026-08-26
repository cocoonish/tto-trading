#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — söz defteri: verilen sözlerin OKURA görünen hâli.

`izleme.json` bültenin "şunu izleyeceğiz", "yarın belli olacak", "sebebi
anlaşılmıyor" dediği her anın kaydı. Defter bugüne dek yalnız yazı katmanının
ve denetimin gördüğü bir iç belgeydi: bülten kendi çağrılarının hesabını
veriyordu ama okur bunu ancak metnin içine serpilmiş cümlelerden çıkarabiliyordu.

Bir sabah notunu güvenilir kılan şey büyük ölçüde budur — "üç gün önce şunu
bekliyorduk, oldu mu?" sorusunun açık cevabı. O yüzden defter artık bültenin
kendi verisine giriyor ve sayfada bir bölüm olarak duruyor.

Karne kasıtlı olarak İSABET ORANI DEĞİL, SAYIMDIR. Bir kaydın tutup tutmadığı
ancak yazı katmanı kaydı kapatırken `isabet` alanını doldurursa bilinir;
notlanmamış kayıtlardan yüzde türetmek defterin bütün anlamını götürür. Notlu
kayıt varsa oran da verilir, yoksa verilmez — eksik veriyle övünmek, hesap
vermenin tam tersidir.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

BURASI = Path(__file__).resolve().parent
DEFTER = BURASI / "izleme.json"

# Kapanan bir kayıt bültende bu kadar gün "yeni kapandı" diye gösterilir.
# Amaç arşiv sergilemek değil, hesabı SICAKKEN vermek.
KAPANAN_PENCERE = 10

# Yazı katmanının kaydı kapatırken verdiği not (bkz. YAZIM.md).
ISABET = {"tuttu": "tuttu", "tutmadi": "tutmadı", "kismen": "kısmen"}


def _gun(metin: str) -> date | None:
    try:
        return datetime.fromisoformat(str(metin)[:10]).date()
    except (ValueError, TypeError):
        return None


def oku() -> dict:
    if not DEFTER.exists():
        return {}
    try:
        return json.loads(DEFTER.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def _kayit(k: dict, bugun: date) -> dict:
    vade = _gun(k.get("vade", ""))
    acilis = _gun(k.get("acilis", ""))
    return {
        "konu": k.get("konu", ""),
        "soz": k.get("soz", ""),
        "ne_bakilacak": k.get("ne_bakilacak", ""),
        "sonuc": k.get("sonuc", ""),
        "durum": k.get("durum", ""),
        "acilis": k.get("acilis", ""),
        "vade": k.get("vade", ""),
        "isabet": ISABET.get(str(k.get("isabet", "")).lower(), ""),
        # Negatif = vadesi geçmiş. Okurun "bu söz gecikti mi" sorusu bu tek sayıda.
        "gun_kalan": (vade - bugun).days if vade else None,
        "yas_gun": (bugun - acilis).days if acilis else None,
    }


def ozet(bugun_metni: str = "") -> dict:
    """Bültene girecek söz defteri kesiti: açık sözler, yeni kapananlar, karne."""
    defter = oku()
    kayitlar = defter.get("kayitlar", [])
    if not kayitlar:
        return {}
    bugun = _gun(bugun_metni) or date.today()

    acik, kapanan = [], []
    for ham in kayitlar:
        k = _kayit(ham, bugun)
        if k["durum"] == "acik":
            acik.append(k)
        elif k["durum"] == "kapandi":
            # Kapanan kayıt yalnız bir süre gösterilir; vadesi yoksa açılışına bakılır.
            yas = k["yas_gun"] if k["gun_kalan"] is None else -k["gun_kalan"]
            if yas is not None and yas <= KAPANAN_PENCERE:
                kapanan.append(k)

    # Vadesi geçmiş açık sözler en üstte: bülten önce kendi gecikmesini göstersin.
    acik.sort(key=lambda k: (k["gun_kalan"] is None, k["gun_kalan"]))
    kapanan.sort(key=lambda k: k["vade"] or k["acilis"], reverse=True)

    notlu = [k for k in kayitlar if str(k.get("isabet", "")).lower() in ISABET]
    tuttu = sum(1 for k in notlu if str(k["isabet"]).lower() == "tuttu")
    kismen = sum(1 for k in notlu if str(k["isabet"]).lower() == "kismen")

    return {
        "acik": acik,
        "kapanan": kapanan,
        "karne": {
            "toplam": len(kayitlar),
            "acik": len(acik),
            "kapandi": sum(1 for k in kayitlar if k.get("durum") == "kapandi"),
            "vadesi_gecmis": sum(1 for k in acik
                                 if k["gun_kalan"] is not None and k["gun_kalan"] < 0),
            "notlanan": len(notlu),
            "tuttu": tuttu,
            "kismen": kismen,
            "tutmadi": len(notlu) - tuttu - kismen,
            # Yalnız notlanmış kayıtlar üzerinden; hiç not yoksa oran YOK.
            "isabet_orani": (round(100 * (tuttu + 0.5 * kismen) / len(notlu), 1)
                             if notlu else None),
        },
        "son_guncelleme": defter.get("_son_guncelleme", ""),
    }


if __name__ == "__main__":
    o = ozet()
    if not o:
        print("söz defteri boş")
        raise SystemExit(0)
    k = o["karne"]
    print(f"Söz defteri — {k['toplam']} kayıt · {k['acik']} açık "
          f"({k['vadesi_gecmis']} vadesi geçmiş) · {k['kapandi']} kapandı")
    if k["isabet_orani"] is not None:
        print(f"  notlanan {k['notlanan']}: {k['tuttu']} tuttu · {k['kismen']} kısmen "
              f"· {k['tutmadi']} tutmadı → %{k['isabet_orani']}")
    else:
        print("  (kapanan kayıtlar henüz notlanmamış — isabet oranı verilmiyor)")
    print("\nAçık sözler:")
    for x in o["acik"]:
        g = x["gun_kalan"]
        etiket = "vadesi geçti" if g is not None and g < 0 else f"{g} gün" if g is not None else "vadesiz"
        print(f"  · [{etiket:>12s}] {x['konu']}")
    print("\nYeni kapananlar:")
    for x in o["kapanan"]:
        print(f"  · {x['konu']}" + (f"  ({x['isabet']})" if x["isabet"] else ""))
