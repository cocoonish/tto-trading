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


def _ozet_mi(ad: str, bicim: int = 2) -> bool:
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
    # Tema da bu ailedendir: günün gelişmesini gövdeden süzer. Muafiyet
    # olmadan 13 sayının 4'ünde iç yoğunluk ENGEL eşiğini aşıyordu (17,8 > 12;
    # ölçüldü 30.09.2026) ve hiçbiri gerçek kusur değildi.
    # Manşet de: günün tezi tek cümledir ve gövdeden süzülür.
    # BİÇİM 3'te "Günün okuması" özet DEĞİLDİR: sayının ana yazısıdır ve
    # Türkiye/Küresel bölümleriyle aynı olguyu yeniden anlatması tam da
    # kullanıcının şikâyet ettiği tekrardır (yorum ↔ gündem öbekleri 01.10.2026
    # teşhisinde sayımın dışında kalıyordu). Özet ailesi: manşet, madde özeti,
    # söz defteri, temalar.
    if bicim >= 3:
        return (ad == "manset" or ad.startswith("ozet.") or ad == "soz_defteri"
                or ad.startswith("tema."))
    return (ad in OZET_BOLUMLER or ad.startswith("ozet.") or ad == "soz_defteri"
            or ad.startswith("tema.") or ad == "manset")

# Ölçüm dışı kalıplar: kaçınılmaz ve anlamlı tekrar eden teknik ifadeler.
MUAF = re.compile(
    r"52 haftalık aralığın|baz puan|yılbaşından bu yana|milyar dolar|"
    r"politika faizi|merkez bankası|abd hazinesi", re.I)


def _duz(h: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def _kelimeler(t: str) -> list[str]:
    return re.findall(r"\w+", t.lower())


def bolumler(b: dict, bayat_tema: bool = False) -> dict[str, str]:
    """Bültenin ölçülecek yazı bölümleri — düz metin.

    `bayat_tema=True` o sayıda güncellenmeyen temaları da katar: günler arası
    kıyasın ÖNCEKİ tarafı içindir. Temalar haftada bir yazılır; önceki sayıda
    hepsi bayat olduğu için kıyas kümesine hiç girmiyor, bugünün yeni tema
    metni hiçbir şeyle kıyaslanmıyordu (27.09'da %0,0; sayfada katlı basılan
    20.09 sürümüyle %8–20).

    KAPSAM BİR LİSTEDEN DEĞİL SÖZLEŞMEDEN TÜRER: okura DÜZYAZI olarak basılan
    her yazı-katmanı alanı ölçüye girer. Kural bir kez elle tutulan listeye
    yazıldığında kaçınılmaz olarak geride kalır — ölçüldü (07.09.2026): liste
    yalnız gündem + yorum'u kapsıyordu, yani sayfadaki düzyazının %27'sini.
    Kapsam dışında kalan özet, temalar ve söz defteri, tekrarın asıl
    biriktiği yerlerdi ve ölçüt onlara hiç bakmıyordu — bakılmayan yer, geçen
    sınavla aynı görünür.
    """
    out = {k: _duz(v) for k, v in (b.get("gundem") or {}).items() if _duz(v)}
    # MANŞET sayfanın h1'i ve RSS önizlemesidir; ihale iddiası ve uydurma sayı
    # denetimleri metni buradan okur ve manşete yazılan bir iddia ikisini de
    # aşıyordu (30.09.2026'da sınandı).
    m = _duz(b.get("manset") or "")
    if m:
        out["manset"] = m
    y = _duz(b.get("yorum") or "")
    if y:
        out["yorum"] = y
    for k, v in (b.get("ozet") or {}).items():
        if _duz(v):
            out[f"ozet.{k}"] = _duz(v)
    # TEMALAR HİÇ ÖLÇÜLMÜYORDU. Bülten JSON'unda alan bir sözlük
    # (`{"temalar": [...], "_son_guncelleme": …}`) ve döngü onu liste gibi
    # dolaşıyordu: anahtar adları dizge çıktı, `isinstance(t, dict)` hep yanlış
    # oldu ve temaların hepsi sessizce atlandı — belge kapsadığını söylerken
    # (30.09.2026'da ölçüldü; günler arası tema örtüşmesi %92'ydi ve hiçbir
    # ölçü onu görmüyordu). İki şekil de kabul edilir.
    #
    # Yalnız BU SAYIDA güncellenen tema girer. Güncellenmeyen tema sayfada
    # katlı basılır ve metni tanımı gereği önceki sayınınkiyle aynıdır; onu
    # saymak her sabah öten bir uyarı olurdu (söz defterinin duran kaydı gibi).
    tm = b.get("temalar") or []
    liste = tm.get("temalar") if isinstance(tm, dict) else tm
    for i, t in enumerate(liste or []):
        if not isinstance(t, dict):
            continue
        sg, gun = str(t.get("son_guncelleme") or ""), str(b.get("tarih") or "")
        if sg and gun and sg < gun and not bayat_tema:
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
            if re.fullmatch(r"(?:19|20)\d\d", s):       # birimsiz yıl sayı değil etikettir
                continue
            if len(re.sub(r"\D", "", s)) >= 3:          # tek/iki hane gürültüsü dışarıda
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
    bicim = int(b.get("surum") or 2)
    agir = [(s, y) for s, y in ifade if len([x for x in y if not _ozet_mi(x, bicim)]) >= 2]
    # Payda: tema ve manşet ölçüye 30.09.2026'da girdi ve ikisi de ağır
    # tekrardan muaf; paydaya girselerdi yoğunluk %13–18 seyrelir, eşikler
    # (7 uyarı · 12 engel) sessizce gevşerdi — 17.09'un "8,0 ağır tekrar"
    # uyarısı 6,9'a inip kayboluyordu. Eşiklerin kalibre edildiği kapsam korunur.
    # BİÇİM 3: söz defteri de paydadan çıkar. Defteri ölçüm katmanı basar ve
    # yazar onu denetlemez; paydada kalsaydı aynı yazı sakin bir sabahta
    # (değişmeyen kayıtlar tek satır) ENGEL, kalabalık bir sabahta UYARI
    # alırdı — 01.10.2026 incelemesinde ölçüldü (yoğunluk 18,8 ↔ 9,6).
    haric = (lambda k: k.startswith("tema.") or k == "manset" or k == "soz_defteri") if bicim >= 3 \
        else (lambda k: k.startswith("tema.") or k == "manset")
    kelime = sum(len(t.split()) for k, t in bol.items() if not haric(k)) or 1
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


# ── OLGU TEKRARI (biçim 3) ────────────────────────────────────────────────
#
# 01.10.2026 teşhisi: birebir cümle tekrarı yalnız %2–4 çıktı — tekrar
# PARAFRAZDAYDI. Aynı ondalıklı olgu (ör. "%5,594", "102,59") sayı başına
# 26–39 kez üç ya da daha çok bölümde geçiyordu; "Ne oldu"nun ondalıklarının
# %53–88'i "Günün okuması"nda yeniden sayılıyordu; politika faizi seti, ÖTV
# takvimi ve 40,7 milyar dolarlık cari açık iki haftanın 10–13 sabahında
# yeniden basılıyordu. 7'li öbek ölçüsü bunların hiçbirini görmez. Olgu imi
# ONDALIKLI sayıdır: tam sayılar yıl, gün, endeks adı (BIST 100) ve süre
# taşır, ondalık neredeyse her zaman bir ölçümdür.
#
# Eşikler KURALIN KENDİSİDİR, kalibre edilmiş bir seviye değil: "bir olgu
# tek yerde tam anlatılır, başka yerde en çok tek cümleyle anılır" → üç
# bölüm kuralın ihlalidir; "Ne oldu ile okuma en çok iki çapa rakam
# paylaşır" → üçüncüsü ihlaldir. Hepsi UYARI.

# Sağ sınır "rakam ya da VİRGÜL+RAKAM gelmez": Türkçe düzyazıda ondalığın
# ardından yan cümle virgülü gelir ("%40,50, koridor …") ve eski sınır
# `(?![\d,])` o olguyu hiç saymıyordu (duman fikstürü yakaladı).
OLGU = re.compile(r"(?<![\d,.])[−\-+]?%?\d{1,3}(?:\.\d{3})*,\d+(?!\d)(?!,\d)")
OLGU_BOLUM_ESIK = 3          # bir olgu bu kadar bölümde → ihlal
OZET_OKUMA_ORTAK = 2         # madde özeti ile okumanın paylaşabileceği olgu
KRONIK_ADET = 3              # dün ve evvelki gün de yazılmış olgu sayısı (UYARI üstü)
ACILIS_ORTUSME = 0.5         # okumanın ilk cümlesi önceki sayınınkiyle 5'li öbek örtüşmesi


def olgu_anahtari(s: str) -> str:
    """İşaret, yüzde ve binlik ayracı düşer: "−%2,56" ile "%2,56" aynı olgu."""
    return re.sub(r"[^\d,]", "", s)


def olgular(metin: str) -> set[str]:
    return {olgu_anahtari(m.group(0)) for m in OLGU.finditer(metin or "")}


def yazi_govdesi(b: dict) -> dict[str, str]:
    """Olgu ölçüsünün bölümleri: madde özeti, okuma ve gündem (manşet hariç —
    başlık maddedeki rakamı taşıyabilir; tema ve söz ayrı defterdir)."""
    out: dict[str, str] = {}
    oz = b.get("ozet") or {}
    if isinstance(oz, dict):
        for k, v in oz.items():
            if _duz(str(v or "")):
                out[f"ozet.{k}"] = _duz(str(v))
    if _duz(b.get("yorum") or ""):
        out["yorum"] = _duz(b.get("yorum") or "")
    for k, v in (b.get("gundem") or {}).items():
        if _duz(str(v or "")):
            out[k] = _duz(str(v))
    return out


def olgu_tekrari(govde: dict[str, str]) -> list[tuple[str, list[str]]]:
    """OLGU_BOLUM_ESIK ya da daha çok bölümde geçen olgular, en yaygını önce."""
    yer: dict[str, set[str]] = defaultdict(set)
    for ad, t in govde.items():
        for o in olgular(t):
            yer[o].add(ad)
    out = [(o, sorted(y)) for o, y in yer.items() if len(y) >= OLGU_BOLUM_ESIK]
    out.sort(key=lambda x: (-len(x[1]), x[0]))
    return out


def ozet_okuma_ortak(govde: dict[str, str]) -> set[str]:
    return olgular(govde.get("ozet.ne_oldu", "")) & olgular(govde.get("yorum", ""))


def kronik_olgular(bugun: dict[str, str], onceki: list[dict[str, str]]) -> set[str]:
    """Bugün yazılan ve ÖNCEKİ iki sayının ikisinde de yazılmış olgular —
    değişmeyen bir değerin her sabah yeniden basılması (politika faizi seti,
    cari açık, ihale modeli). Değişen bir seri her gün başka değer taşır."""
    if len(onceki) < 2:
        return set()
    # Sıfırla başlayan küçük ondalıklar (0,10 · 0,3) çoğunlukla günlük
    # DEĞİŞİMDİR ve iki ayrı olgu tesadüfen aynı yazılabilir; kronik ölçü
    # seviyelere bakar.
    k = {o for o in set().union(*(olgular(t) for t in bugun.values())) if not o.startswith("0,")}
    for g in onceki[:2]:
        k &= set().union(*(olgular(t) for t in g.values())) if g else set()
    return k


def _ilk_cumle(metin: str) -> str:
    m = re.split(r"(?<=[.!?])\s+", (metin or "").strip(), maxsplit=1)
    return m[0] if m else ""


def acilis_ortusme(bugun_yorum: str, onceki_yorum: str) -> float:
    """İki okumanın ilk cümlesinin 5'li öbek örtüşmesi (bugünün öbeklerinin payı).
    29.09 ve 30.09 okumaları birebir aynı cümleyle açılıyordu."""
    def ob(t):
        k = _kelimeler(t)
        return {tuple(k[i:i + 5]) for i in range(len(k) - 4)}
    a, b = ob(_ilk_cumle(bugun_yorum)), ob(_ilk_cumle(onceki_yorum))
    return round(len(a & b) / len(a), 2) if a else 0.0
