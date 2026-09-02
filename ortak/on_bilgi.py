# -*- coding: utf-8 -*-
"""MDX ön bilgisi (frontmatter) — tek ayrıştırıcı.

Analiz kapısı (site/tools/analiz_sinavi.py) ve X gönderisi üreticisi
(tweet/analiz.py) aynı dosyayı okur; iki ayrı ayrıştırıcı bir gün farklı
sonuç verirdi. Desteklenen biçim, yazım rehberinin istediği kadardır: tek
satırlık skaler (tek/çift tırnaklı ya da çıplak, '' kaçışıyla), köşeli liste.
Katlanmış YAML ('>' ve '|') desteklenmez ve açıkça söylenir.
"""
from __future__ import annotations

import re

_SATIR = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
_LISTE_OGE = re.compile(r"'(?:[^']|'')*'|\"[^\"]*\"|[^,]+")


class OnBilgiHatasi(ValueError):
    pass


def deger(ham: str):
    s = ham.strip()
    if not s:
        return ""
    if s in (">", "|", ">-", "|-"):
        raise OnBilgiHatasi("katlanmış YAML desteklenmiyor — değer tek satır olmalı")
    if s.startswith("[") and s.endswith("]"):
        ic = s[1:-1].strip()
        return [deger(p) for p in _LISTE_OGE.findall(ic)] if ic else []
    if len(s) >= 2 and s[0] == "'" and s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def ayristir(metin: str) -> dict:
    """'---' ile çevrili ön bilgiyi sözlüğe çevirir; yoksa boş sözlük."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---", metin, re.S)
    if not m:
        return {}
    d: dict = {}
    for satir in m.group(1).splitlines():
        km = _SATIR.match(satir)
        if km:
            d[km.group(1)] = deger(km.group(2))
    return d


def govde(metin: str) -> str:
    return re.sub(r"^---\r?\n.*?\r?\n---\r?\n?", "", metin, count=1, flags=re.S)
