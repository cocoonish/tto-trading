#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — atıf kaynaklarının METNİ (donmuş).

Bulutun indirdiği ham sayfalar (`veri/ham/kaynak/`, `veri/ham/resmigazete/`) olduğu gibi
durur; bu betik onlardan okunabilir metni çıkarıp `veri/kaynak_metin/<ad>.txt.gz` altına
yazar. Neden ayrı bir adım: yazının alıntılarını sınayan kapı (`dogrula.py`, sayfa sınavı
26) yalnız standart kütüphaneyle koşar ve PDF çözemez. Metin bir kez burada çıkarılır,
kaynağın sha256'sıyla birlikte dondurulur; kapı (1) ham dosyanın özünü bulut künyesiyle,
(2) metnin hangi ham dosyadan çıkarıldığını, (3) alıntının o metinde geçtiğini sorar.

Kodlama sayfanın kendisinden okunur (`charset`; Resmî Gazete windows-1254). HTML'de
betik/stil blokları atılır. PDF'de satır sonunda bölünen sözcük birleştirilir. Hiçbir
metin "düzeltilmez": normalleştirme yalnız boşluk, tipografik tırnak/tire ve yumuşak tire.

  python3 kaynak_metin.py          # yerelde; pypdf gerekir (PDF'ler için)
"""
from __future__ import annotations

import gzip
import hashlib
import html
import io
import json
import re
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "ham"
CIKTI = BURASI / "veri" / "kaynak_metin"
DIZIN = BURASI / "veri" / "kaynak_metin.json"
KUNYELER = ("kunye_kaynak.json", "kunye_rg.json")


def normal(s: str) -> str:
    """Kapı da AYNI fonksiyonu kullanır (dogrula.py içinde birebir kopyası, duman eşitliği sorar)."""
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("­", "")
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), ("–", "-"),
                 ("—", "-"), ("−", "-"), (" ", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


class _Metin(HTMLParser):
    ATLA = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parca: list[str] = []
        self.derin = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.ATLA:
            self.derin += 1
        elif tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "td", "th", "section", "article"):
            self.parca.append(" ")

    def handle_endtag(self, tag):
        if tag in self.ATLA and self.derin:
            self.derin -= 1
        elif tag in ("p", "div", "li", "tr", "td", "th"):
            self.parca.append(" ")

    def handle_data(self, data):
        if not self.derin:
            self.parca.append(data)


def html_metin(govde: bytes) -> str:
    m = re.search(rb'charset=["\']?([\w-]+)', govde[:5000], flags=re.I)
    kod = m.group(1).decode("ascii", "replace") if m else "utf-8"
    try:
        s = govde.decode(kod, errors="replace")
    except LookupError:
        s = govde.decode("utf-8", errors="replace")
    p = _Metin()
    p.feed(s)
    return html.unescape("".join(p.parca))


# Kırık yazı tipi: OVP 2027–2029 PDF'inin tablo yazı tipi Unicode eşlemesi taşımıyor ve metin
# çıkarıcı GLİF NUMARASINI karakter diye veriyor (rakamlar U+0372–U+037B, virgül U+01E1 …).
# Eşleme ÖLÇÜLDÜ, tahmin edilmedi: Tablo 1.1'in "Ham Petrol Fiyatı" satırı bu eşlemeyle
# 69,1 · 88,0 · 76,0 · 72,0 · 67,0 okunuyor ve sitenin OVP hattının elle aktardığı tabloyla
# (OVP/programlar.json) birebir aynı; "Enerji İthalatı" satırı da öyle. Yalnız bu imzayı
# taşıyan PDF'e uygulanır (100'den fazla glif rakamı) ve dizine `glif_esleme` diye yazılır.
# NFKC'DEN ÖNCE uygulanmak zorunda: NFKC U+037A'yı (8) boşluk + birleşik işarete böler.
GLIF = {0x372 + i: str(i) for i in range(10)}
GLIF.update({0x1E1: ",", 0x1E4: ".", 0x1E6: "-", 0x20B: "(", 0x20C: ")", 0x200: "/", 0x1E3: ":", 0x1E2: ";",
             0x03: " "})


def pdf_metin(govde: bytes) -> tuple[str, bool]:
    import pypdf  # yalnız bu adımda; kapı PDF açmaz
    r = pypdf.PdfReader(io.BytesIO(govde))
    sayfa = []
    for pg in r.pages:
        try:
            sayfa.append(pg.extract_text() or "")
        except Exception as e:  # bozuk sayfa metni düşürür, sessiz değil
            sayfa.append(f" [sayfa çözülemedi: {e!r}] ")
    s = "\n".join(sayfa)
    glif = sum(1 for ch in s if 0x372 <= ord(ch) <= 0x37B) > 100
    if glif:
        s = s.translate(GLIF)
    return re.sub(r"(\w)-\n(\w)", r"\1\2", s), glif


def main() -> int:
    CIKTI.mkdir(parents=True, exist_ok=True)
    dizin = {}
    for kn in KUNYELER:
        p = HAM / kn
        if not p.exists():
            print(f"  · {kn} yok, atlandı")
            continue
        for yol, k in json.loads(p.read_text(encoding="utf-8")).items():
            if not (yol.startswith("kaynak/") or (yol.startswith("resmigazete/karar_"))):
                continue
            ham = (HAM / yol).read_bytes()
            govde = gzip.decompress(ham)
            oz = hashlib.sha256(govde).hexdigest()
            if oz != k["sha256"]:
                raise SystemExit(f"öz tutmuyor: {yol} ({oz[:12]} ≠ {k['sha256'][:12]})")
            tur = "pdf" if govde[:5] == b"%PDF-" else "html"
            glif = False
            if tur == "pdf":
                ham_metin, glif = pdf_metin(govde)
            else:
                ham_metin = html_metin(govde)
            metin = normal(ham_metin)
            ad = Path(yol).name.split(".")[0]
            hedef = CIKTI / f"{ad}.txt.gz"
            veri = metin.encode("utf-8")
            with open(hedef, "wb") as f:
                with gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
                    g.write(veri)
            dizin[yol] = {"url": k["url"], "tur": tur, "kaynak_sha256": oz, "metin": f"kaynak_metin/{ad}.txt.gz",
                          "metin_sha256": hashlib.sha256(veri).hexdigest(), "karakter": len(metin),
                          **({"glif_esleme": True} if glif else {})}
            print(f"  ✓ {tur:4s} {len(metin):>8,} {yol}")
    DIZIN.write_text(json.dumps(dict(sorted(dizin.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── {len(dizin)} kaynak metni → {DIZIN.relative_to(BURASI)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
