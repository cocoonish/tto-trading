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
from datetime import date, datetime, timedelta
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
# HAFTALIK KİP (01.10.2026): pazar sayısı bir önceki PAZAR sayısıyla kıyaslanır
# ve pencereler bir haftadır. Günlük pencerelerle (1 gün) hafta içinde açılıp
# kapanan kayıtlar pazar sayısında "değişmeden duran" altında tek satır
# basılıyordu — oysa haftalık okurun asıl sorusu "bu hafta hangi söz kapandı".
HAFTA_PENCERE = 7


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
        # Kapanış günü (yazı katmanı kaydı kapatırken yazar; eski kayıtlarda yok).
        "kapanis": k.get("kapanis", ""),
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


def hafta_karnesi(kayitlar: list[dict], onceki_izleme: dict | None, bugun: date,
                  onceki_gun: date | None = None) -> dict:
    """HAFTANIN KARNESİ — bir önceki haftalık SAYIDAN bu yana defterde ne oldu.

    KIYAS NOKTASI BİR ÖNCEKİ HAFTALIK SAYININ BASTIĞI DEFTERDİR, takvim günü
    DEĞİL (01.10.2026). İlk yazım (bugün−7, bugün] takvim penceresini
    kullanıyordu; ölçüm pazar 14:03'te, yazı katmanı ondan SONRA çalıştığı için
    pazar günü açılan bir senaryo sözü ne o haftanın ne sonraki haftanın
    "açılan" listesine giriyordu, pazar günü kapanan da hiçbir haftanın
    "kapanan"ına — rehberin "karne ölçülen katmandan kurulur" sözü tam da
    senaryo sözleri için tutmuyordu. Aynı sayfadaki söz defteri ise iki ucu
    dahil yedi günlük pencereyle "yeni" diyordu ve iki blok çelişiyordu.

    Kural okurun gördüğünden türer:
    - kapanan: şimdi kapalı, önceki haftalık sayıda KAPALI basılmamış ve ya
      orada AÇIK basılmış, ya o sayının gününden sonra açılmış (arada açılıp
      kapanmış) ya da kapanış günü son yedi günde. Önceki sayıda zaten kapalı
      basılan kayıt bu haftaya sayılmaz; tarihi olmayan, hiç basılmamış kayıt
      da sayılmaz (kapanış gününü bilmediğimiz kaydı atamak karneyi şişirir).
    - açılan: şimdi açık ve önceki sayının açık listesinde yok (o liste
      defterin tamamıdır).
    - yaklaşan: açık ve vadesine 0–7 gün var; vadesi GEÇMİŞ açık kayıt ayrı
      listede (`gecikmis`) — "önümüzdeki haftaya düşen" bir söz değildir.
    Önceki haftalık sayı yoksa yalnız kapanış günü pencerede olan kayıtlar
    sayılır ve `kiyas_var: False` yazılır. Karne SAYIMDIR, oran değil: oran
    zaten bütün defter için `karne`de durur. Söz defterinin haftalık "yeni"
    ayrımı bu fonksiyonun listelerinden okur (`ozet`) — iki tanım tutulmaz.
    """
    # Defteri boş basılmış bir sayı (`izleme: {}`) kıyas noktası olamaz: her
    # açık kayıt "bu hafta açılan" görünürdü.
    kiyas_var = isinstance(onceki_izleme, dict) and "acik" in onceki_izleme
    onceki_acik = ({str(k.get("konu")) for k in (onceki_izleme.get("acik") or []) if isinstance(k, dict)}
                   if kiyas_var else set())
    onceki_kapali = ({str(k.get("konu")) for k in (onceki_izleme.get("kapanan") or [])
                      if isinstance(k, dict)}
                     if kiyas_var else set())
    onceki_hepsi = onceki_acik | onceki_kapali
    taban = (onceki_gun or (bugun - timedelta(days=HAFTA_PENCERE))).toordinal()

    def pencerede(g: date | None) -> bool:
        return g is not None and bugun.toordinal() - HAFTA_PENCERE < g.toordinal() <= bugun.toordinal()

    def sonra_acildi(g: date | None) -> bool:
        return g is not None and taban <= g.toordinal() <= bugun.toordinal()

    kapanan, acilan, yaklasan, gecikmis = [], [], [], []
    for k in kayitlar:
        konu = str(k.get("konu") or "")
        acilis = _gun(k.get("acilis", ""))
        if k.get("durum") == "kapandi":
            kap = _gun(k.get("kapanis", ""))
            if kiyas_var:
                # Önceki sayıda KAPALI basılmışsa okur onu çoktan gördü.
                bu_hafta = konu not in onceki_kapali and (
                    konu in onceki_acik or sonra_acildi(acilis) or pencerede(kap))
            else:
                bu_hafta = pencerede(kap)
            if bu_hafta:
                kapanan.append(k)
        elif k.get("durum") == "acik":
            # Önceki sayının açık listesi defterin TAMAMIDIR; orada olmayan açık
            # kayıt okur için yenidir (açılış günü ne olursa olsun).
            if (konu not in onceki_hepsi) if kiyas_var else pencerede(acilis):
                acilan.append(k)
            kalan = k.get("gun_kalan")
            if kalan is not None and 0 <= kalan <= HAFTA_PENCERE:
                yaklasan.append(k)
            elif kalan is not None and kalan < 0:
                gecikmis.append(k)
    say = lambda n: sum(1 for k in kapanan if k.get("isabet") == n)  # noqa: E731
    return {
        "kiyas_var": kiyas_var,
        "pencere_gun": HAFTA_PENCERE,
        "kapanan": [{a: k.get(a) for a in ("konu", "soz", "sonuc", "isabet", "acilis", "kapanis", "vade")}
                    for k in kapanan],
        "acilan": [{a: k.get(a) for a in ("konu", "soz", "acilis", "vade")} for k in acilan],
        "yaklasan": [{a: k.get(a) for a in ("konu", "soz", "vade", "gun_kalan")}
                     for k in sorted(yaklasan, key=lambda x: x.get("gun_kalan") or 0)],
        "gecikmis": [{a: k.get(a) for a in ("konu", "soz", "vade", "gun_kalan")}
                     for k in sorted(gecikmis, key=lambda x: x.get("gun_kalan") or 0)],
        "tuttu": say("tuttu"), "kismen": say("kısmen"), "tutmadi": say("tutmadı"),
        "notsuz": sum(1 for k in kapanan if not k.get("isabet")),
    }


def ozet(bugun_metni: str = "", onceki_izleme: dict | None = None,
         haftalik: bool = False, onceki_gun: str = "") -> dict:
    """Bültene girecek söz defteri kesiti: açık sözler, yeni kapananlar, karne.

    `onceki_izleme` bir önceki sayının `izleme` bloğudur; verilirse metni
    değişmemiş kayıtlar `duran: True` ile işaretlenir ve sayfa onları tek
    satırda basar (bkz. yukarıdaki not). Haftalık sayıda önceki sayı bir
    önceki HAFTALIK sayıdır, pencereler bir hafta ve `hafta` alanı haftanın
    karnesini taşır.
    """
    yeni_pencere = HAFTA_PENCERE if haftalik else YENI_PENCERE
    vade_yakin_gun = HAFTA_PENCERE if haftalik else VADE_YAKIN
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
    #
    # KIYAS NORMALİZE KAYITLA YAPILIR (01.10.2026). `_degisenler` HAM defter
    # kaydını önceki sayının BASILMIŞ (normalize) kaydıyla kıyaslıyordu: ham
    # isabet "tutmadi", basılan "tutmadı" — imza her gün farklı çıktı ve
    # kapanmış iki kayıt (437 kelime) 28–30.09'da her sabah "değişen" diye
    # tam metniyle basıldı. İki taraf da aynı süzgeçten (`_kayit`) geçer.
    degisen_konu = _degisenler([_kayit(h, bugun) for h in kayitlar], onceki_izleme)
    # HAFTALIK SAYIDA "YENİ" KARNENİN KENDİ LİSTESİDİR (01.10.2026): iki ucu
    # dahil yedi günlük pencere, bir önceki pazar "yeni" basılmış kaydı bu pazar
    # yine "yeni" sayıyordu, karne ise listelemiyordu — aynı sayfada iki blok
    # çelişti. Tanım tek: `hafta_karnesi`.
    hafta = (hafta_karnesi([_kayit(h, bugun) for h in kayitlar], onceki_izleme, bugun,
                           _gun(onceki_gun))
             if haftalik else None)
    karne_yeni = ({str(k.get("konu")) for k in hafta["kapanan"] + hafta["acilan"]}
                  if hafta is not None and hafta["kiyas_var"] else None)
    # Önceki sayıda zaten KAPALI basılan kayıtlar: "bugün kapandı" ölçüsünün
    # veriden türeyen tabanı (kapanış günü yazılmamış eski kayıtlar için).
    onceki_kapali = ({str(k.get("konu")) for k in (onceki_izleme.get("kapanan") or [])
                      if isinstance(k, dict)}
                     if isinstance(onceki_izleme, dict) else None)
    for k in acik + kapanan:
        metin_degisti = str(k.get("konu") or "") in degisen_konu
        kalan = k.get("gun_kalan")
        if k["durum"] == "kapandi":
            # KAPANMIŞ bir kayıt için "vade yakın" ANLAMSIZDIR — vade zaten
            # geçti, kayıt onunla birlikte kapandı. İlk yazımda ölçüt ayrım
            # yapmıyordu ve 17 kapanan kaydın 16'sını "değişen" sayıyordu,
            # yani tekrarın büyük kısmı yerinde kalıyordu. Kapanan kayıt
            # yalnız YENİ kapandıysa ya da metni değiştiyse öne çıkar.
            #
            # "YENİ KAPANDI" KAPANIŞ GÜNÜNDEN TÜRER, VADEDEN DEĞİL (01.10.2026):
            # vadesinden ÖNCE kapanan bir kayıt ("Fon krizinin bedeli…", vade
            # 01.10) vade gelene kadar her gün `-kalan <= 1` ile "yeni" sayıldı.
            # Sıra: kayıttaki kapanış günü → önceki sayıda kapalı mıydı → yoksa
            # "yeni" denmez (ölçemediğimiz bir değişikliği işaretlemeyiz).
            kap = _gun(k.get("kapanis", ""))
            if karne_yeni is not None:
                yeni_mi = str(k.get("konu") or "") in karne_yeni
            elif kap is not None:
                yeni_mi = 0 <= (bugun - kap).days <= yeni_pencere
            elif onceki_kapali is not None:
                yeni_mi = str(k.get("konu") or "") not in onceki_kapali
            else:
                yeni_mi = False
            vade_yakin = False
        else:
            yeni_mi = (str(k.get("konu") or "") in karne_yeni if karne_yeni is not None
                       else (k.get("yas_gun") is not None and k["yas_gun"] <= yeni_pencere))
            # Vadesi GELEN ya da GEÇEN açık söz öne çıkar: bülten önce kendi
            # gecikmesini gösterir.
            vade_yakin = kalan is not None and kalan <= vade_yakin_gun
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
        **({"hafta": hafta} if hafta is not None else {}),
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
