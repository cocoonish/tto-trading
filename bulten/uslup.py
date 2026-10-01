"""Bülten yazı katmanının ÜSLUP ölçütü — biçim 3 (sabah notu).

01.10.2026 teşhisi: bülten bir piyasa profesyonelinin notu gibi değil, ölçüm
sisteminin denetim raporu gibi okunuyordu. 30.09'da cümlelerin %13'ü okura
ölçüm tesisatını, kendi "kayıt"larını ve veri kısıtlarını anlatıyordu; bu
öz-atıf yoğunluğu ağustos sonunda bin kelimede 0–0,4 iken 25–30 Eylül'de
3,1–6,6'ya çıkmıştı. Kökü kurallardaydı ("metinde söyle" diyen ölçüm
dürüstlüğü kuralları veri notlarını düzyazıya taşıyordu); rehber düzeltildi,
bu modül de aynı dilin geri gelmesini ölçer.

Kalıplar 34 sayıda (23.08–30.09) koşturularak seçildi; ENGEL kümesinin bütün
eşleşmeleri tek tek okundu ve bülten içinde yanlış pozitif ÇIKMADI (Y02'nin
"temanın çürütücü ölçütü" biçimindeki eşleşmeleri de düzeltilebilir üslup).
Ölçüt YALNIZ biçim 3 sayının yazı alanlarına (manşet, özet, okuma, gündem)
uygulanır: tema ve söz defteri, ölçüm katmanı metinleri ve analiz yazıları
kapsam dışıdır (analizlerde "tablo satırı" gibi ifadeler meşrudur).

ENGEL yayın kapısında DEĞİL yazma kapısındadır (yaz.py denetimi): yazar
düzeltip yeniden yazar, site durmaz. Bütçeli kalıplar UYARI'dır: tek tek
meşru olabilirler, sorun yoğunluktur.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Kalip:
    kod: str
    ad: str
    desen: re.Pattern
    butce: int | None        # None → ENGEL (hiç geçmez); sayı → UYARI eşiği (sayı başına)
    oneri: str
    # YOĞUNLUK kalıbı mı: bütçe ~1.700 kelimelik sabah notuna göre konmuştur
    # ve uzun sayıda (haftaya bakış, 6.000–9.000 kelime) kelime sayısıyla
    # ölçeklenir. Mutlak kurallar (adsız kaynak, rakamla yazım, 52 hafta konumu,
    # standart adlar) ÖLÇEKLENMEZ: bir sayıda hiç geçmemesi gerekeni uzunluk
    # meşrulaştırmaz.
    olcekli: bool = False
    # Kalıbın SAYILMADIĞI alanlar (yazi_alanlari adlarıyla). Haftalık karne
    # bölümünün görevi geçmiş çağrıyı anlatmaktır; "demiştik" orada bütçeye
    # girmez, öbür bölümlerde girer (rehber: "geçmiş çağrı atfı yalnız karnede").
    muaf: tuple[str, ...] = ()


def _k(desen: str, bayrak=0) -> re.Pattern:
    # Büyük/küçük harf DUYARSIZ: kalıplar cümle ortası yazımıyla seçildi ve
    # "Hüküm kurulmadı", "Kaydımız" gibi cümle başı hâlleri ENGEL'den
    # kaçıyordu (duman fikstürü yakaladı). 34 sayıda ölçüldü: eklenen 19
    # eşleşmenin 19'u aynı kalıbın cümle başı hâli. Python'un Unicode
    # IGNORECASE'i ı/İ/i/I'yı birbirine eşler.
    return re.compile(desen, bayrak | re.I)


KALIPLAR: tuple[Kalip, ...] = (
    # ── ENGEL: okura ölçüm tesisatını, kendi defterini, veri kısıtını anlatmak
    Kalip("Y01", "evren/satır öz-atfı",
          _k(r"\b(?:[Öö]lçülen|[Öö]lçtüğümüz)\s+elli\s+bir\s+(?:satır|enstrüman)\w*"
             r"|\b(?:[Bb]itcoin|[Aa]ltın|[Gg]ümüş|[Ee]uro/dolar|Şanghay\s+Bileşik|GBP/TRY|"
             r"Türkiye|[Ff]aiz|[Rr]ejim)\s+satır(?:ı|ın|ları|larının|larını)\b"),
          None, "sayfanın satırına atıf yapma; olguyu kendi cümlesiyle söyle"),
    Kalip("Y02", "geçmiş çağrıya süreç atfı",
          _k(r"\b(?:çürüt(?:me|ücü)\s+ölçüt\w*|kaydın\s+(?:kendi\s+)?(?:çürüt|doğrula|iddia|vade|tez)\w*|"
             r"(?:kurduğumuz|açtığımız)\s+(?:bir\s+)?kay[ıi]t\w*|vadeli\s+(?:yeni\s+)?(?:bir\s+)?kay[ıi]t\w*|"
             r"kaydımız\w*)"),
          None, "geçmiş çağrı söz defterinde durur; düzyazıda '(20.09 notu)' diye an, "
                "tezini okur cümlesiyle yaz ('20.09 notunun tezi — TLREF tavana döner — tuttu')"),
    # Daraltma (01.10.2026 incelemesi): "dürüstçe" ve "şimdiden söyleniyor"
    # meşru piyasa cümlelerinde de geçiyor ("Powell dürüstçe kabul etti",
    # "kulislerde şimdiden söyleniyor"); öz-atıf yalnız birinci tekil/çoğul
    # yazar bağlamında aranır.
    Kalip("Y04", "ölçü uyarısı / meta not",
          _k(r"\b(?:ölçü(?:nün)?|okuma)\s+(?:bir\s+)?(?:uyarısı|kısıtı|boşluğu)\b"
             r"|\bbir\s+(?:ölçü|okuma)\s+(?:uyarısı|kısıtı|boşluğu)|kayda\s+geçsin|"
             r"dürüstçe\s+(?:söyle|yaz|belirt)\w*|şimdiden\s+(?:yazılıyor|yazmak)|not\s+olarak\s+yazılmalı|"
             r"önce\s+ölçünün\s+kendisi|veri\s+yaşı\s+notu", re.I),
          None, "veri kısıtını sayfa (dipnot) söyler; düzyazıya taşıma"),
    Kalip("Y05", "'hüküm kurulmadı'",
          _k(r"\bhüküm(?:ü)?\s+(?:kurulmadı|kurmuyoruz)|\bhükme\s+girmedi|"
             r"hiçbir\s+hükm(?:ünde|e)\s+(?:kullanılmadı|girmedi)"),
          None, "kullanmadığın seriyi anlatma; yalnız kullandığını yaz"),
    Kalip("Y06", "beklenti yokluğunu anlatma",
          # "sürpriz yapılmayacak" bir merkez bankası mesajı da olabilir
          # (Lagarde); kalıp yalnız ÖLÇÜNÜN yokluğunu arar.
          _k(r"sürpriz\s+(?:ölçü(?:mü|sü)?\s+)?(?:ölçülmeyecek|hesaplanmayacak|kurulmaz)"
             r"|sürpriz\s+ölçü(?:mü|sü)?\s+yapılmayacak"
             r"|beklenti(?:si|miz)?\s+elimizde\s+(?:yok|olmadığı)|beklentimiz\s+olmadığı|"
             r"beklenti\s+(?:alanı\s+boş|yayımlanmadığı)", re.I),
          None, "beklenti yoksa tablo '—' basar; yokluğu düzyazıda anlatma"),
    Kalip("Y07", "kod/süreç sözlüğü",
          # "defterde" (muhasebe: "itfa edilmiş maliyetle defterde") ve "hattının
          # haftalık" (boru hattı) meşru piyasa dilinde de geçiyor; kalıp
          # yalnız BİZİM tesisatımızın adlarını arar.
          _k(r"\b(?:hattımız\w*|vekilimiz\w*|defterimiz\w*|söz\s+defterinde|hat\s+hat\s+değişim\w*|"
             r"sürümünde\s+donmuş|ölçüm\s+hattı\w*)\b"),
          None, "hat, defter, sürüm okurun sözcüğü değil"),
    Kalip("Y08", "önemi kaynak sayısıyla gerekçeleme",
          _k(r"(?:en\s+çok|beş\s+ayrı|birden\s+çok)\s+kaynakta\s+(?:birden\s+)?yer\s+bul\w*", re.I),
          None, "önem fiyat etkisinden gelir; kaç yayının yazdığından değil"),
    Kalip("Y09", "veri tesisatı anlatısı",
          _k(r"kapanışını\s+taşıyor|(?:barını|seansını)\s+boş\s+verdi"),
          None, "satırın tarihi sayfada yazar; düzyazıya taşıma"),
    # ── UYARI (bütçeli): tek tek meşru, yoğunluğu kusur
    # ÖLÇEKLENMEZ (01.10.2026, inceleme): ilk yazım bütçeyi uzunlukla büyütüyordu
    # ve 9.000 kelimelik haftalıkta beş atfı her bölüme yaymaya izin veriyordu;
    # rehber ise haftalıkta atfı karneye hapseder. Karne muaf, kalanı bir.
    Kalip("Y03", "'yazmıştık' ailesi",
          _k(r"\b(?:yazmıştık|söylemiştik|demiştik|koymuştuk|beklemiştik|sormuştuk)\b"),
          1, "geçmişe atıf sayı başına en çok bir kez (haftalıkta yalnız karne bölümünde)",
          muaf=("gundem.karne",)),
    Kalip("Y10", "σ yerine uzun tanım",
          _k(r"kendi\s+(?:günlük\s+|haftalık\s+)?oynaklığ\w+\s+(?:\([^)]*\)\s+)?(?:göre\s+)?[\d,]+\s+(?:kat|standart)"),
          1, "olağandışılığı '(1,5σ)' biçiminde yaz", True),
    Kalip("Y11", "MOVE/VIX yerine dolaylama",
          _k(r"(?:[Tt]ahvil|[Hh]isse)\s+oynaklığı\s+ölçüsü"),
          0, "standart adı kullan: MOVE, VIX"),
    Kalip("Y12", "her gün yeniden yapılan tanım",
          _k(r"kur\s+arındırılmış\s+on\s+üç\s+haftalık\s+yıllıklandırılmış|fazla\s+likidite\s+rejiminde|"
             r"yıllıklandırma\s+tek\s+günlük|valör\s+(?:farkı\s+ya\s+da|ve)\s+tatil|"
             r"getiri\s+ödemeyen\s+madeni\s+taşıma|ülke\s+riski\s+(?:yeniden\s+)?fiyatlaması\s+"
             r"(?:önce\s+)?(?:bankalarda|kurda)|tahvili\s+gecelik\s+fonlamayla\s+taşı\w*", re.I),
          1, "tanım sözlükte durur; metinde kısa adı kullan", True),
    Kalip("Y14", "52 hafta konumu",
          _k(r"(?:52|elli\s+iki)\s+haftalık\s+aralığ\w*\s+(?:tam\s+)?(?:yalnız\s+)?(?:%\d+|tepe|dib|en\s+dib)"),
          3, "52 hafta konumunu yalnız uçlarda an"),
    Kalip("Y15", "tablo içi sıralama",
          _k(r"(?:günün|haftanın)\s+en\s+(?:büyük|olağandışı)\s+(?:(?:ikinci|üçüncü|dördüncü|beşinci|altıncı)\s+)?"
             r"(?:\w+\s+)?hareket\w*|listes\w*\s+(?:en|üçüncü)"),
          2, "sıralamayı tablo söyler; düzyazıda yalnız en büyüğü", True),
    Kalip("Y17", "adsız kaynak",
          _k(r"\b(?:[Bb]ir\s+(?:kaynağa|değerlendirmeye)\s+göre|[Hh]aber\s+akış(?:ına\s+göre|ında)|"
             r"[Bb]ir\s+(?:küresel\s+)?(?:yatırım\s+bankası|finans\s+yayını|yatırım\s+stratejisti|"
             r"uluslararası\s+kuruluş|bölge\s+başkanı)|bir\s+diğeri|bir\s+başkası)\b"),
          0, "kaynağı ve kişiyi adıyla yaz (Reuters, FT, Williams …)"),
    Kalip("Y18", "sayının yazıyla yazılması",
          _k(r"\b(?:[Oo]n\s+(?:yedi|üç|dört|beş|altı|sekiz|dokuz)\s+(?:Eylül|Ağustos|Ekim|Kasım|Aralık))"
             r"|\belli\s+(?:iki|bir)\s+(?:haftalık|satır|enstrüman)|\bon\s+dokuz\s+yılın"),
          0, "sayılar rakamla: '52 haftalık', '17 Eylül'"),
    Kalip("Y19", "'bir X değil bir Y' antitezi",
          _k(r"\bbir\s+\w+(?:\s+\w+)?\s+değil,?\s+bir\s+\w+"),
          2, "antitez kalıbını seyrek kullan", True),
)

OLCEK_KELIME = 1700          # yoğunluk bütçelerinin konduğu sayının uzunluğu (biçim 3 günlük üst sınırı)
YANI = re.compile(r"\byani\b", re.I)
YANI_KELIME = 300            # 300 kelimede en çok bir "yani"
CUMLE_ORT_UST = 22           # ortalama cümle (kelime)
CUMLE_UZUN = 35              # bu uzunluğu aşan cümle
CUMLE_UZUN_PAY = 0.08        # ... payı en çok %8


def _cumleler(metin: str) -> list[str]:
    # Ondalık virgül/nokta ve kısaltma noktası cümleyi bölmez: yalnız
    # [.!?] + boşluk + büyük harf ya da sayı sınırı.
    parca = re.split(r"(?<=[.!?…])\s+(?=[A-ZÇĞİÖŞÜ0-9%−\"“(])", metin.strip())
    return [p for p in parca if len(p.split()) >= 3]


def olc(alanlar: dict[str, str]) -> dict:
    """alanlar: alan adı → düz metin. Dönüş: {engel: [...], uyari: [...], sayim: {...}}."""
    engel, uyari, sayim = [], [], {}
    tum = " \n".join(alanlar.values())
    # Ölçek: her ~1.700 kelime bir sabah notu payı (günlük sayıda 1).
    kat = max(1, len(tum.split()) // OLCEK_KELIME)
    for k in KALIPLAR:
        bulunan = []
        for ad, t in alanlar.items():
            if ad in k.muaf:
                continue
            for m in k.desen.finditer(t):
                bulunan.append((ad, m.group(0)))
        sayim[k.kod] = len(bulunan)
        if not bulunan:
            continue
        ornek = "; ".join(f"[{a}] “{g}”" for a, g in bulunan[:3])
        if k.butce is None:
            engel.append(f"ÜSLUP {k.kod} ({k.ad}) — {len(bulunan)} yerde: {ornek}. {k.oneri}.")
        elif len(bulunan) > (butce := k.butce * (kat if k.olcekli else 1)):
            uyari.append(f"Üslup {k.kod} ({k.ad}) {len(bulunan)} kez (bütçe {butce}): {ornek}. {k.oneri}.")
    kelime = len(tum.split())
    yani = len(YANI.findall(tum))
    sayim["yani"] = yani
    if kelime and yani > max(1, kelime // YANI_KELIME):
        uyari.append(f"'yani' {yani} kez ({kelime} kelimede; bütçe {max(1, kelime // YANI_KELIME)}) — "
                     "bağlacı çıkar, cümleyi doğrudan kur.")
    cumle = [c for t in alanlar.values() for c in _cumleler(t)]
    if cumle:
        uz = [len(c.split()) for c in cumle]
        ort = sum(uz) / len(uz)
        pay = sum(1 for u in uz if u > CUMLE_UZUN) / len(uz)
        sayim["cumle_ort"] = round(ort, 1)
        sayim["cumle_uzun_pay"] = round(pay, 3)
        if ort > CUMLE_ORT_UST or pay > CUMLE_UZUN_PAY:
            en = max(cumle, key=lambda c: len(c.split()))
            uyari.append(f"Cümleler uzun: ortalama {ort:.1f} kelime; {CUMLE_UZUN} kelimeyi aşanların payı "
                         f"%{pay*100:.0f} (hedef ort. ≤{CUMLE_ORT_UST}, pay ≤%{CUMLE_UZUN_PAY*100:.0f}). En uzunu "
                         f"{len(en.split())} kelime: “{en[:90]}…”")
    return {"engel": engel, "uyari": uyari, "sayim": sayim}
