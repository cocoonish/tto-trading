# -*- coding: utf-8 -*-
"""Bülten içi TEKRAR ölçeri.

Sorun şuydu: bülten uzadıkça aynı olay birden çok bölümde yeniden ANLATILIYOR.
25 Ağustos 2026 bülteninde çekirdek repo hikâyesi ("gecelik repo faizi %39,86'dan
%36,93'e") dört ayrı bölümde neredeyse kelimesi kelimesine tekrarlandı; ölçüm 202
ayrı 7 kelimelik birebir tekrar öbeği buldu. Okur aynı cümleyi dördüncü kez
gördüğünde bülteni değil, bültenin kendini tekrar ettiğini okur.

Ayrım önemli — her tekrar kötü değil:

  · **Birebir ifade tekrarı** (aynı 7+ kelimenin başka bölümde yeniden geçmesi)
    neredeyse her zaman saf tekrardır. Ölçülür ve engellenir.
  · **Sayı tekrarı** meşru olabilir: politika faizi birçok bölümde geçer, ama her
    seferinde ÜZERİNDE YENİ BİR İŞLEM yapılıyorsa. Bu yüzden sayı tekrarı engel
    değil uyarıdır ve en çok tekrarlanan sayılar ADIYLA raporlanır ki yazar
    hangisini kesip atacağını görsün.

Kural: **bir olgu bir kez tam anlatılır.** İkinci geçişinde ya yeni bir işlem
yapılır (ör. aynı faiz taşıma hesabına girer) ya da tek cümleyle anılıp geçilir.
"""
from __future__ import annotations

import html as _html
import re
from collections import defaultdict

# Birebir tekrar sayılan en kısa öbek (kelime). 7, Türkçede bir yan cümleyi
# kapsayacak kadar uzun; rastgele çakışma üretmeyecek kadar da uzun.
OBEK = 7

# Eşikler BİN KELİME BAŞINA ağır tekrar sayısıdır — uzun bülteni haksız yere
# cezalandırmamak için normalize edilir. Kalibrasyon gerçek bültenlerle yapıldı:
#   24.08.2026 (günlük, temiz)   →  5,4   ← hedef bant
#   23.08.2026 (haftalık)        → 11,5   ← uyarı
#   25.08.2026 (günlük, sorunlu) → 13,1   ← engel
YOGUNLUK_UYARI = 7.0
YOGUNLUK_ENGEL = 12.0

# Bir sayı bu kadar AYRI bölümde geçiyorsa raporlanır (uyarı).
SAYI_BOLUM_ESIK = 4

# Kaç sayı bu eşiği aşarsa uyarı verilir.
SAYI_ADET_ESIK = 6

# Tekrar ölçümü dışında tutulan bölümler: özet niteliğindeki "kilit" ve "yorum"
# bölümlerinin tanımı gereği başka bölümlerdeki olguya değmesi gerekir. Yine de
# bunlar BİRBİRİYLE ve diğerleriyle karşılaştırılır — muaf değil, yalnız
# birebir ifade eşiği bunlar için ayrı sayılır (aşağıya bak).
OZET_BOLUMLER = {"kilit", "yorum"}


def _ozet_mi(ad: str) -> bool:
    """Bu bölüm 'başka bölümlere değmesi TANIMI GEREĞİ meşru' ailesinden mi?

    Kapsam sözleşmeye genişletilince (özet, temalar, söz defteri) İÇ tekrar
    ölçüsü yapısal olarak şişti: 13 sayının 3'ü ENGEL eşiğini aşıyordu ve
    hiçbiri gerçek kusur değildi. Sebebi basit — söz defteri "bültenin ne
    dediğinin kaydı"dır, özet de özettir; ikisinin de gövdeye DEĞMESİ
    gerekir. Aynı gerekçeyle `kilit` ve `yorum` zaten muaftı.

    Muafiyet İÇ ölçüye özgüdür. GÜNLER ARASI ölçüde söz defteri tam tersine
    asıl bakılacak yerdir: gövdeye değmesi meşru, kendini her gün yeniden
    basması değil.
    """
    return ad in OZET_BOLUMLER or ad.startswith("ozet.") or ad == "soz_defteri"

# Ölçüm dışı kalıplar: kaçınılmaz ve anlamlı tekrar eden teknik ifadeler.
MUAF = re.compile(
    r"52 haftalık aralığın|baz puan|yılbaşından bu yana|milyar dolar|"
    r"politika faizi|merkez bankası|abd hazinesi", re.I)


def _duz(h: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def _kelimeler(t: str) -> list[str]:
    return re.findall(r"\w+", t.lower())


def bolumler(b: dict) -> dict[str, str]:
    """Bültenin ölçülecek yazı bölümleri — düz metin.

    KAPSAM BİR LİSTEDEN DEĞİL SÖZLEŞMEDEN TÜRER: okura DÜZYAZI olarak basılan
    her yazı-katmanı alanı ölçüye girer. Kural bir kez elle tutulan listeye
    yazıldığında kaçınılmaz olarak geride kalır — ölçüldü (07.09.2026): liste
    yalnız gündem + yorum'u kapsıyordu, yani sayfadaki düzyazının %27'sini.
    Kapsam dışında kalan özet, temalar ve söz defteri, tekrarın asıl
    biriktiği yerlerdi ve ölçüt onlara hiç bakmıyordu — bakılmayan yer, geçen
    sınavla aynı görünür.
    """
    out = {k: _duz(v) for k, v in (b.get("gundem") or {}).items() if _duz(v)}
    y = _duz(b.get("yorum") or "")
    if y:
        out["yorum"] = y
    for k, v in (b.get("ozet") or {}).items():
        if _duz(v):
            out[f"ozet.{k}"] = _duz(v)
    for i, t in enumerate(b.get("temalar") or []):
        if not isinstance(t, dict):
            continue
        metin = _duz(" ".join(str(t.get(a) or "") for a in ("tez", "gelisme", "son_gozlem")))
        if metin:
            out[f"tema.{t.get('ad') or i}"] = metin
    iz = b.get("izleme") or {}
    if isinstance(iz, dict):
        kayit = []
        for grup in ("acik", "kapanan"):
            for k in (iz.get(grup) or []):
                if not isinstance(k, dict):
                    continue
                # DURAN kayıt sayfada tek satırla basılır; ölçüye de o hâliyle
                # girer. Tam metnini saymak, basılmayan bir metni tekrar
                # saymak olurdu.
                if k.get("degisti") is False:
                    kayit.append(str(k.get("konu") or ""))
                else:
                    kayit += [str(k.get(a) or "") for a in ("konu", "soz", "ne_bakilacak", "sonuc")]
        if _duz(" ".join(kayit)):
            out["soz_defteri"] = _duz(" ".join(kayit))
    return out


def ifade_tekrari(bol: dict[str, str]) -> list[tuple[str, list[str]]]:
    """Farklı bölümlerde birebir geçen kelime öbekleri.

    Kayan pencere üst üste binen öbekler ürettiği için (aynı cümle N-6 kez
    sayılır) sonuçlar ilk dört kelimeye göre teklenir; dönen sayı ANLATININ
    kaç kez tekrarlandığını yansıtır, kaç pencere çakıştığını değil.
    """
    sh: dict[str, list[str]] = defaultdict(list)
    for k, t in bol.items():
        w = _kelimeler(t)
        for i in range(len(w) - OBEK + 1):
            sh[" ".join(w[i:i + OBEK])].append(k)
    gorulen: set[str] = set()
    out: list[tuple[str, list[str]]] = []
    for s, yer in sh.items():
        if len(set(yer)) < 2 or MUAF.search(s):
            continue
        cekirdek = " ".join(s.split()[:4])
        if cekirdek in gorulen:
            continue
        gorulen.add(cekirdek)
        out.append((s, sorted(set(yer))))
    out.sort(key=lambda x: -len(x[1]))
    return out


def sayi_tekrari(bol: dict[str, str]) -> list[tuple[str, list[str]]]:
    """Birden çok bölümde geçen sayısal ifadeler (en çok yayılan önce)."""
    say: dict[str, list[str]] = defaultdict(list)
    for k, t in bol.items():
        for m in re.finditer(r"%?\d[\d.,]*\s?(?:baz puan|puan|bp|dolar|lira|"
                             r"milyar|mlr|euro|%)?", t):
            s = m.group(0).strip()
            if len(re.sub(r"\D", "", s)) >= 3:          # yıl/tek hane gürültüsü dışarıda
                say[s].append(k)
    out = [(s, sorted(set(y))) for s, y in say.items()
           if len(set(y)) >= SAYI_BOLUM_ESIK]
    out.sort(key=lambda x: -len(x[1]))
    return out


def olc(b: dict) -> dict:
    """Bülteni ölç; denetim bu sözlüğü okur."""
    bol = bolumler(b)
    ifade = ifade_tekrari(bol)
    sayi = sayi_tekrari(bol)
    # Özet bölümlerinin (kilit/yorum) diğerlerine değmesi tanımı gereği; ağır
    # ihlal, ÖZET OLMAYAN iki bölümün birbirini tekrar etmesidir.
    agir = [(s, y) for s, y in ifade if len([x for x in y if not _ozet_mi(x)]) >= 2]
    kelime = sum(len(t.split()) for t in bol.values()) or 1
    return {"bolum_sayisi": len(bol), "kelime": kelime,
            "ifade": ifade, "agir": agir, "sayi": sayi,
            "yogunluk": round(len(agir) / kelime * 1000, 1)}


# ── GÜNLER ARASI TEKRAR ────────────────────────────────────────────────────
#
# Yukarıdaki ölçü bir SAYININ kendi içindeki tekrarı görür. Okurun asıl
# şikâyeti ise başkaydı: "her gün aynı şeyleri söylemeyelim."
#
# Ölçüldü (07.09.2026, 13 sayı). Ardışık iki sayı arasında birebir 7-sözcük
# öbeği örtüşmesi 26.08'den 06.09'a düzenli tırmanmış: %0,5 → %19,1 → %25,8
# → %33,2 → %37,5 → %46,2. Kaynağı ayrıştırınca sebep tek bir yerde çıktı ve
# YAZARDA DEĞİLDİ: gündem %0,6 · yorum %0,3 · özet %2,7 örtüşüyor — yani her
# sabah yazılan düzyazı gerçekten yeni. Söz defteri ise %91,4 örtüşüyordu,
# çünkü 4.816 sözcüklük bölüm her gün kelimesi kelimesine yeniden basılıyordu.
# Defter düzeltildikten sonra aynı iki sayıda sayfa düzyazısının örtüşmesi
# %47,3'ten %21,1'e indi.
#
# Bu ölçü ENGEL DEĞİL UYARIDIR ve bu bilinçli: sakin bir haftada iki sayının
# birbirine benzemesi meşrudur, vadesi gelen bir söz yeniden anılmalıdır. Bir
# yayın kapısının yanlış alarmı, ölçtüğü kusurdan pahalıdır. Uyarı hangi
# BÖLÜMÜN sürüklediğini adıyla söyler — yazar neyi keseceğini görsün.
# EŞİKLER ÖLÇÜLEN İKİ HÂLDEN TÜRETİLDİ, sezgiden değil:
#   toplam    bozuk defter %47,3  ·  düzeltilmiş defter %21,1  → eşik 30
#   bölüm     bozuk defter %91,5–100 · düzeltilmiş defter %71,4 → eşik 80
# Bölüm eşiğinin 80 olması bilinçli: vadesi GELEN bir söz yeniden anılmalıdır
# ("şunu bekliyorduk, bugün belli oldu") ve o gün metni tekrarlanır. Bu
# tekrar okurun işine yarar; eşiği 60'a çekmek onu kusur sayar ve her sabah
# öten bir uyarı iki haftada okunmaz olur.
GUNLER_ARASI_UYARI = 30.0
GUNLER_ARASI_BOLUM_UYARI = 80.0


def gunler_arasi(bugun: dict[str, str], onceki: dict[str, str]) -> dict:
    """İki sayının düzyazısı arasındaki birebir öbek örtüşmesi.

    Girdi iki sayının `bolumler()` çıktısıdır. Dönen sözlük: toplam oran,
    bölüm bölüm oran ve en çok taşıyan bölümler. Önceki sayı yoksa çağrılmaz —
    ölçülmemiş bir oranı sıfır saymak, tekrarı yok saymaktır.
    """
    def _ob(t: str) -> set[tuple[str, ...]]:
        k = _kelimeler(t)
        return {tuple(k[i:i + OBEK]) for i in range(len(k) - OBEK + 1)}

    onc_hepsi: set[tuple[str, ...]] = set()
    for t in onceki.values():
        onc_hepsi |= _ob(t)

    bugun_hepsi: set[tuple[str, ...]] = set()
    bolum_orani: dict[str, float] = {}
    for ad, t in bugun.items():
        o = _ob(t)
        bugun_hepsi |= o
        if o:
            bolum_orani[ad] = round(100 * len(o & onc_hepsi) / len(o), 1)

    oran = (round(100 * len(bugun_hepsi & onc_hepsi) / len(bugun_hepsi), 1)
            if bugun_hepsi else 0.0)
    agir = sorted((a for a, v in bolum_orani.items() if v >= GUNLER_ARASI_BOLUM_UYARI),
                  key=lambda a: -bolum_orani[a])
    return {"oran": oran, "bolum": bolum_orani, "agir": agir,
            "uyari": oran >= GUNLER_ARASI_UYARI or bool(agir)}
