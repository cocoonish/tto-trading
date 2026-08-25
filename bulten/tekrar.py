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

# Ölçüm dışı kalıplar: kaçınılmaz ve anlamlı tekrar eden teknik ifadeler.
MUAF = re.compile(
    r"52 haftalık aralığın|baz puan|yılbaşından bu yana|milyar dolar|"
    r"politika faizi|merkez bankası|abd hazinesi", re.I)


def _duz(h: str) -> str:
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", h or ""))).strip()


def _kelimeler(t: str) -> list[str]:
    return re.findall(r"\w+", t.lower())


def bolumler(b: dict) -> dict[str, str]:
    """Bültenin ölçülecek yazı bölümleri (gündem + okuma), düz metin."""
    out = {k: _duz(v) for k, v in (b.get("gundem") or {}).items() if _duz(v)}
    y = _duz(b.get("yorum") or "")
    if y:
        out["yorum"] = y
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
    agir = [(s, y) for s, y in ifade if len([x for x in y if x not in OZET_BOLUMLER]) >= 2]
    kelime = sum(len(t.split()) for t in bol.values()) or 1
    return {"bolum_sayisi": len(bol), "kelime": kelime,
            "ifade": ifade, "agir": agir, "sayi": sayi,
            "yogunluk": round(len(agir) / kelime * 1000, 1)}
