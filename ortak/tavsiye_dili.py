# -*- coding: utf-8 -*-
"""Tavsiye dili kalıbı — yayına giden HER metnin ortak süzgeci.

Site analiz yayımlar, yatırım tavsiyesi vermez. "Alın", "satın", "hedef fiyat",
"pozisyon açın" kalıpları bültende (bulten/denetim.py), teknik yorumda
(teknik/yaz.py), analiz yazısında (site/tools/analiz_sinavi.py) ve X
gönderisinde (tweet/denetim.py) aynı listeyle yakalanır. Liste okur_dili.py ile
aynı sebeple TEK yerde durur: dört ayrı kopya bir gün sessizce ayrışır.

Kullanım:
    from tavsiye_dili import TAVSIYE
    if TAVSIYE.search(metin): ...
"""
from __future__ import annotations

import re

# "satın alma / satın alım" bir ekonomi terimidir, emir değil: "satın" ardından
# "al…" geliyorsa eşleşmez. "alın" tek başına emir kipidir; "alınan", "alındı"
# kelime sınırı yüzünden zaten eşleşmez. "alın teri" ve "sahibinin alın yazısı"
# gibi nadir kullanımlar için de ardından gelen sözcük bakılır.
TAVSIYE = re.compile(
    r"\b(al[ıi]n(?!\s+(?:teri|yazısı|çizgisi))|sat[ıi]n(?!\s+al)|"
    r"pozisyon a[çc](?:[ıi]n|malı)|hedef fiyat|tavsiye ediyoruz|"
    r"öneriyoruz|kesinlikle al|kesinlikle sat|portföy[üu]n[üu]ze ekleyin|"
    r"almanızı öneririz|satmanızı öneririz|stop ?loss koyun|kâr al[ıi]n)\b", re.I)


def tavsiye_var(metin: str) -> str | None:
    """İlk eşleşen kalıbı döndürür; yoksa None."""
    m = TAVSIYE.search(metin or "")
    return m.group(0) if m else None
