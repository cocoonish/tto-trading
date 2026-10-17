# -*- coding: utf-8 -*-
"""Bir modülde aynı adla iki üst düzey tanım olmaz.

Python ikinci tanımı sessizce birinciden sonra bağlar: birinci tanımı çağıran her yer, çağrı anında ikincisine
düşer. sekil.py'de saat yazımını dakikaya çeviren yeni bir yardımcı, dosyanın ilerisindeki dakika farkını yazan
aynı adlı fonksiyonla gölgelendi ve şekil adımı ancak koşuda düştü (derleme ve içe aktarma temiz geçiyordu);
ders_motor.py'de bir ölü tanım aynı yoldan susmuştu. Soru statiktir, koşturmadan sorulur.
"""
from __future__ import annotations

import ast
import collections
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def _cift_tanimlar(kaynak: str) -> dict[str, int]:
    agac = ast.parse(kaynak)
    sayim = collections.Counter(d.name for d in agac.body
                                if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
    return {ad: n for ad, n in sayim.items() if n > 1}


def test_modullerde_cift_tanim_yok():
    dosyalar = sorted(KOK.glob("*.py")) + sorted((KOK / "testler").glob("*.py"))
    assert dosyalar, "proje modülü bulunamadı"
    cift = {str(p.relative_to(KOK)): c for p in dosyalar if (c := _cift_tanimlar(p.read_text(encoding="utf-8")))}
    assert not cift, f"aynı adla iki üst düzey tanım: {cift}"


def test_cift_tanim_yakalanir():
    assert _cift_tanimlar("def f(a):\n    return a\n\n\ndef f(b, c):\n    return b\n") == {"f": 2}
    assert _cift_tanimlar("def f():\n    pass\n\n\ndef g():\n    pass\n") == {}
