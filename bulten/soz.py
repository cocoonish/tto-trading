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

# BİR DEFTER HER GÜN BAŞTAN ANLATILMAZ.
#
# Ölçüldü (07.09.2026, 13 sayı): bültenin düzyazısı günden güne tekrar
# ETMİYOR — gündem %0,6, yorum %0,3, özet %2,7 birebir öbek örtüşmesi. Buna
# karşılık söz defteri ardışık iki sayı arasında %91,4 örtüşüyor: 4.590
# sözcüklük bölüm her sabah kelimesi kelimesine yeniden basılıyordu. Sayfanın
# günler arası toplam örtüşmesi bu yüzden 26.08'den 06.09'a %0,5'ten %46,2'ye
# tırmandı — yazarın kusuru değil, defterin basım biçimi.
#
# Bir sabah notunda defterin işi "hangi sözü vermiştik"i her gün yeniden
# okutmak değil, BUGÜN NE DEĞİŞTİĞİNİ söylemektir. Kayıt SİLİNMİYOR: değişen
# kayıt tam metniyle, DURAN kayıt tek satırlık künyesiyle (konu · açılış ·
# kalan gün) basılır. Okur tam metni sayfada bir tık ötede bulur.
#
# Bir kaydın "değişmesi" üç şeyden biridir ve üçü de VERİDEN türer, tahminden
# değil: bugün açıldı · bugün kapandı · vadesi geldi geçiyor. Dördüncüsü
# metnin kendisinin değişmesidir ve onu ancak bir ÖNCEKİ SAYIYA bakarak
# bilebiliriz — `ozet()` o yüzden önceki sayının defterini argüman alır.
VADE_YAKIN = 1          # kalan gün ≤ bu ise kayıt "değişen" sayılır
YENI_PENCERE = 1        # bu kadar gün içinde açılan kayıt "yeni"


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


def _metin_imzasi(k: dict) -> str:
    """Kaydın OKURA GİDEN metni — iki sayı arasında değişip değişmediği bununla ölçülür."""
    return "\u241f".join(str(k.get(a) or "").strip()
                         for a in ("konu", "soz", "ne_bakilacak", "sonuc", "isabet", "durum"))


def _degisenler(kayitlar: list[dict], onceki_izleme: dict | None) -> set[str]:
    """Bu sayıda metni DEĞİŞEN kayıtların konuları.

    Önceki sayının `izleme` bloğu verilmezse boş küme döner ve karar yalnız
    veriden türeyen ölçütlere (bugün açıldı · bugün kapandı · vade yakın)
    kalır — uydurma yok: ölçemediğimiz bir değişikliği "değişti" diye
    işaretlemeyiz.
    """
    if not isinstance(onceki_izleme, dict):
        return set()
    onceki = {}
    for grup in ("acik", "kapanan"):
        for k in (onceki_izleme.get(grup) or []):
            if isinstance(k, dict) and k.get("konu"):
                onceki[str(k["konu"])] = _metin_imzasi(k)
    out = set()
    for k in kayitlar:
        konu = str(k.get("konu") or "")
        if not konu:
            continue
        eski_imza = onceki.get(konu)
        if eski_imza is None or eski_imza != _metin_imzasi(k):
            out.add(konu)
    return out


def ozet(bugun_metni: str = "", onceki_izleme: dict | None = None) -> dict:
    """Bültene girecek söz defteri kesiti: açık sözler, yeni kapananlar, karne.

    `onceki_izleme` bir önceki sayının `izleme` bloğudur; verilirse metni
    değişmemiş kayıtlar `duran: True` ile işaretlenir ve sayfa onları tek
    satırda basar (bkz. yukarıdaki not).
    """
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

    # DEĞİŞEN / DURAN ayrımı. Üç ölçüt veriden türer, dördüncüsü önceki sayıdan.
    degisen_konu = _degisenler(kayitlar, onceki_izleme)
    for k in acik + kapanan:
        metin_degisti = str(k.get("konu") or "") in degisen_konu
        kalan = k.get("gun_kalan")
        if k["durum"] == "kapandi":
            # KAPANMIŞ bir kayıt için "vade yakın" ANLAMSIZDIR — vade zaten
            # geçti, kayıt onunla birlikte kapandı. İlk yazımda ölçüt ayrım
            # yapmıyordu ve 17 kapanan kaydın 16'sını "değişen" sayıyordu,
            # yani tekrarın büyük kısmı yerinde kalıyordu. Kapanan kayıt
            # yalnız YENİ kapandıysa ya da metni değiştiyse öne çıkar.
            yeni_mi = kalan is not None and -kalan <= YENI_PENCERE
            vade_yakin = False
        else:
            yeni_mi = (k.get("yas_gun") is not None and k["yas_gun"] <= YENI_PENCERE)
            # Vadesi GELEN ya da GEÇEN açık söz öne çıkar: bülten önce kendi
            # gecikmesini gösterir.
            vade_yakin = kalan is not None and kalan <= VADE_YAKIN
        k["degisti"] = bool(yeni_mi or vade_yakin or metin_degisti)
        k["duran"] = not k["degisti"]
        # SEBEBİ de yazılır: okur "bu neden burada" diye sormasın, ve bir
        # sonraki oturum ölçütü tahmin etmesin.
        k["degisim_sebebi"] = ("yeni" if yeni_mi else
                               "vade" if vade_yakin else
                               "guncellendi" if metin_degisti else "")

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
            # Sayfa "bu sayıda defterde ne değişti"yi başlıkta söyleyebilsin.
            "degisen": sum(1 for k in acik + kapanan if k.get("degisti")),
            "duran": sum(1 for k in acik + kapanan if k.get("duran")),
            # Önceki sayı verilmediyse metin karşılaştırması KOŞMADI; sayfa
            # bunu bilerek yazsın, ölçülmemiş bir şeyi ölçülmüş sanmasın.
            "kiyas_var": onceki_izleme is not None,
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
