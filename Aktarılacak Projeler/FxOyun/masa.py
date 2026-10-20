#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX GÜN İÇİ — dersin MASA katmanı: şema mumlar, karar şemaları ve senaryo kartları.

Bu katman veri değildir; dersin ölçtüğü sonucun masada NASIL okunacağını ve NE ZAMAN yapılmayacağını anlatır.
Üç kuralı vardır ve kapı (`dogrula.masa`) üçünü de sorar:

  1. Şema bir ŞEMADIR: mumlar elle çizilmiş, ideal hâllerdir; her şemanın künyesi "Şema — gerçek veri değil"
     yazar ve şemanın hiçbir yazısında ölçülmüş bir sayı (ondalık, yüzde) durmaz.
  2. Her senaryo kartı ve her karar şemasının sonucu bir DAYANAĞA bağlıdır: dersin ölçtüğü bir sonucun adı
     ("N. ders, bölüm"). Dayanaksız bir kural, ölçülmemiş bir sezgidir.
  3. Kart bir kenar vaat etmez: her kartın altında aynı not durur (kural okuma kuralıdır; ölçüm maliyetten
     sonra kenar bulmadı).

Spesifikasyonlar `metin/masa/<slug>.toml`da durur; şablonlar `{{# sema id }}`, `{{# karar id }}`, `{{# kart id }}`
bloklarıyla çağırır. SVG telefon sütununa (360 birim) göre çizilir ve renkleri sitenin jetonlarından alır
(`global.css` → `.ms-*`). MDX'e satır içi girer: boş satır ve süslü parantez yazılmaz (MDX ikisini de JSX'in
sonu sayar), `<` ve `>` yazıda kullanılmaz.
"""
from __future__ import annotations

import html
import re
import sys
import tomllib
from pathlib import Path

BURASI = Path(__file__).resolve().parent
MASA = BURASI / "metin" / "masa"
SEMA_KAYNAK = "Şema — gerçek veri değil"
KART_NOTU = ("Bu bir okuma kuralıdır, kenar değil: ölçüm bu durumda maliyetten sonra artı bir işlem bulmadı. "
             "Kural, başka bir gerekçeyle masadaysan neyi yapmayacağını ve emri nereye koyacağını söyler.")
DAIRE = "①②③④⑤⑥⑦⑧⑨"
DAYANAK = re.compile(r"\b[1-9]\. ders\b")
OLCULMUS = re.compile(r"\d[.,]\d|%\s?\d|\d\s?%")          # şemada ölçülmüş sayı izi (ondalık, yüzde)

# ─────────────────────────────────────────────────────────────── spesifikasyon
_ONBELLEK: dict[str, dict] = {}


def spek(slug: str) -> dict:
    if slug not in _ONBELLEK:
        yol = MASA / f"{slug}.toml"
        _ONBELLEK[slug] = tomllib.loads(yol.read_text(encoding="utf-8")) if yol.exists() else {}
    return _ONBELLEK[slug]


def _bul(slug: str, tur: str, kimlik: str) -> dict:
    for x in spek(slug).get(tur, []):
        if x["id"] == kimlik:
            return x
    raise KeyError(f"{slug}: {tur} {kimlik!r} tanımsız (metin/masa/{slug}.toml)")


def _e(s: str) -> str:
    """SVG/HTML yazısı: kaçış + MDX'in JSX sayacağı karakterlerin kapısı."""
    if any(c in s for c in "{}<>"):
        raise ValueError(f"şema yazısında MDX'in JSX sayacağı karakter: {s!r}")
    return html.escape(s, quote=True)


def _sar(metin: str, en: int) -> list[str]:
    """Karakter sayısıyla sözcük sınırında sarma (SVG yazısı satır kırmaz)."""
    satirlar, sat = [], ""
    for k in metin.split():
        if sat and len(sat) + 1 + len(k) > en:
            satirlar.append(sat)
            sat = k
        else:
            sat = f"{sat} {k}".strip()
    return satirlar + ([sat] if sat else [])


# ─────────────────────────────────────────────────────────────── şema mum
GEN, SOL, MUM_SAG, ETIKET_X = 360, 10, 236, 244


def sema_svg(s: dict) -> str:
    mumlar = s["mumlar"]
    n = len(mumlar)
    yuk = int(s.get("yukseklik", 250))
    ust, alt = 14, yuk - 22
    fiyat = [p for m in mumlar for p in m]
    for c in s.get("cizgi", []):
        fiyat.append(c["y"])
    for b in s.get("bolge", []):
        fiyat += [b["y1"], b["y2"]]
    for yol in s.get("yol", []):
        fiyat += [p[1] for p in yol["noktalar"]]
    lo, hi = min(fiyat), max(fiyat)
    pay = (hi - lo) * 0.06 or 1
    lo, hi = lo - pay, hi + pay
    y = lambda p: alt - (p - lo) / (hi - lo) * (alt - ust)
    adim = (MUM_SAG - SOL) / n
    x = lambda i: SOL + adim * (i + 0.5)
    gov = max(3.0, adim * 0.62)
    kim = re.sub(r"[^a-z0-9]", "", s["id"])
    k = []
    k.append(f'<svg viewBox="0 0 {GEN} {yuk}" class="mum-sema" role="img" aria-label="{_e(s["baslik"])}">')
    k.append(f'<defs><marker id="ok-{kim}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" '
             f'orient="auto"><path d="M0,0 L8,4 L0,8 z" class="ms-ok-ucu" /></marker></defs>')
    for b in s.get("bolge", []):
        i0, i1 = b.get("i0", 0), b.get("i1", n - 1)
        x0, x1 = SOL + adim * i0, SOL + adim * (i1 + 1)
        ya, yb = sorted((y(b["y1"]), y(b["y2"])))
        k.append(f'<rect x="{x0:.1f}" y="{ya:.1f}" width="{x1 - x0:.1f}" height="{yb - ya:.1f}" '
                 f'class="ms-bolge ms-{b.get("tur", "bekle")}" />')
        if b.get("etiket"):
            for j, sat in enumerate(_sar(b["etiket"], 16)):
                k.append(f'<text x="{ETIKET_X}" y="{(ya + yb) / 2 + 4 + 13 * j - 6 * (len(_sar(b["etiket"], 16)) - 1):.1f}" '
                         f'class="ms-etiket ms-{b.get("tur", "bekle")}-yazi">{_e(sat)}</text>')
    for c in s.get("cizgi", []):
        i0, i1 = c.get("i0", 0), c.get("i1", n - 1)
        yy = y(c["y"])
        k.append(f'<line x1="{SOL + adim * i0:.1f}" x2="{SOL + adim * (i1 + 1):.1f}" y1="{yy:.1f}" y2="{yy:.1f}" '
                 f'class="ms-cizgi ms-{c.get("tur", "seviye")}" />')
        if c.get("etiket"):
            k.append(f'<text x="{ETIKET_X}" y="{yy + 4:.1f}" class="ms-etiket ms-{c.get("tur", "seviye")}-yazi">'
                     f'{_e(c["etiket"])}</text>')
    vurgu = set(s.get("vurgu", []))
    for i, (o, h, l, c) in enumerate(mumlar):
        sinif = "ms-artis" if c >= o else "ms-azalis"
        if i in vurgu:
            sinif += " ms-vurgu"
        if i in set(s.get("soluk", [])):
            sinif += " ms-soluk"
        k.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{y(h):.1f}" y2="{y(l):.1f}" class="ms-fitil {sinif}" />')
        ya, yb = sorted((y(o), y(c)))
        k.append(f'<rect x="{x(i) - gov / 2:.1f}" y="{ya:.1f}" width="{gov:.1f}" height="{max(yb - ya, 1.2):.1f}" '
                 f'class="ms-govde {sinif}" />')
    for yol in s.get("yol", []):
        nok = " ".join(f"{x(i):.1f},{y(p):.1f}" for i, p in yol["noktalar"])
        k.append(f'<polyline points="{nok}" class="ms-yol ms-yol-{yol.get("tur", "olasi")}" '
                 f'marker-end="url(#ok-{kim})" />')
        if yol.get("etiket"):
            i, p = yol["noktalar"][-1]
            k.append(f'<text x="{min(x(i) + 6, ETIKET_X - 4):.1f}" y="{y(p) + 4:.1f}" class="ms-etiket ms-yol-yazi">'
                     f'{_e(yol["etiket"])}</text>')
    for m in s.get("isaret", []):
        cx, cy = x(m["i"]), y(m["y"])
        k.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="8" class="ms-isaret" />')
        k.append(f'<text x="{cx:.1f}" y="{cy + 3.6:.1f}" class="ms-isaret-yazi">{int(m["n"])}</text>')
    if s.get("eksen"):
        k.append(f'<text x="{SOL}" y="{yuk - 6}" class="ms-eksen">{_e(s["eksen"])}</text>')
    k.append("</svg>")
    return "\n".join(k)


def sema_blok(slug: str, kimlik: str, no: str) -> str:
    s = _bul(slug, "sema", kimlik)
    notlar = s.get("not", [])
    liste = "\n".join(f"- {DAIRE[i]} {n}" for i, n in enumerate(notlar))
    return (f'<Diyagram no="{no}" baslik="{_e(s["baslik"])}" kaynak="{SEMA_KAYNAK}" azami={{480}}>\n'
            f"{sema_svg(s)}\n</Diyagram>\n\n" + (liste + "\n" if liste else ""))


# ─────────────────────────────────────────────────────────────── karar şeması (merdiven)
SORU_G, SONUC_X, SONUC_G = 184, 222, 134


def karar_svg(s: dict) -> str:
    adimlar = s["adim"]
    k, yy = [], 10
    bloklar = []
    for a in adimlar:
        soru = _sar(a["soru"], 26)
        sonuc = _sar(a["sonuc"], 20)
        h = max(18 + 15 * len(soru), 18 + 14 * len(sonuc))
        bloklar.append((yy, h, soru, sonuc, a))
        yy += h + 26
    son = _sar(s["son"], 44)
    son_h = 18 + 15 * len(son)
    yuk = yy + son_h + 10
    kim = re.sub(r"[^a-z0-9]", "", s["id"])
    k.append(f'<svg viewBox="0 0 {GEN} {yuk}" class="karar-sema" role="img" aria-label="{_e(s["baslik"])}">')
    k.append(f'<defs><marker id="ko-{kim}" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" '
             f'orient="auto"><path d="M0,0 L8,4 L0,8 z" class="ks-ok-ucu" /></marker></defs>')
    for j, (y0, h, soru, sonuc, a) in enumerate(bloklar):
        k.append(f'<rect x="4" y="{y0}" width="{SORU_G}" height="{h}" rx="3" class="ks-soru" />')
        for i, sat in enumerate(soru):
            k.append(f'<text x="14" y="{y0 + 17 + 15 * i}" class="ks-yazi">{_e(sat)}</text>')
        orta = y0 + h / 2
        k.append(f'<line x1="{4 + SORU_G}" x2="{SONUC_X - 2}" y1="{orta:.1f}" y2="{orta:.1f}" class="ks-ok" '
                 f'marker-end="url(#ko-{kim})" />')
        k.append(f'<text x="{4 + SORU_G + 5}" y="{orta - 5:.1f}" class="ks-dal">{_e(a["cikis"])}</text>')
        sinif = f"ks-sonuc ks-{a.get('tur', 'yapma')}"
        k.append(f'<rect x="{SONUC_X}" y="{y0}" width="{SONUC_G}" height="{h}" rx="3" class="{sinif}" />')
        for i, sat in enumerate(sonuc):
            k.append(f'<text x="{SONUC_X + 8}" y="{y0 + 16 + 14 * i}" class="ks-yazi-kucuk">{_e(sat)}</text>')
        alt_y = bloklar[j + 1][0] if j + 1 < len(bloklar) else yy
        k.append(f'<line x1="40" x2="40" y1="{y0 + h}" y2="{alt_y - 2}" class="ks-ok" marker-end="url(#ko-{kim})" />')
        k.append(f'<text x="46" y="{y0 + h + 16}" class="ks-dal">{_e(a.get("devam", "hayır"))}</text>')
    k.append(f'<rect x="4" y="{yy}" width="{GEN - 8}" height="{son_h}" rx="3" class="ks-son" />')
    for i, sat in enumerate(son):
        k.append(f'<text x="14" y="{yy + 17 + 15 * i}" class="ks-yazi">{_e(sat)}</text>')
    k.append("</svg>")
    return "\n".join(k)


def karar_blok(slug: str, kimlik: str, no: str) -> str:
    s = _bul(slug, "karar", kimlik)
    dayanak = "; ".join(sorted({a["dayanak"] for a in s["adim"]}))
    return (f'<Diyagram no="{no}" baslik="{_e(s["baslik"])}" kaynak="Karar şeması — dayanak: {_e(dayanak)}" '
            f'azami={{480}}>\n{karar_svg(s)}\n</Diyagram>\n')


# ─────────────────────────────────────────────────────────────── senaryo kartı
KART_ALAN = [("gorursun", "Ne görürsün"), ("yaparsin", "Ne yaparsın"), ("yapmazsin", "Ne yapmazsın"),
             ("emir", "Emir, stop, hedef"), ("dayanak", "Dayanak")]


def kart_blok(slug: str, kimlik: str) -> str:
    s = _bul(slug, "kart", kimlik)
    sat = [f'<div class="senaryo" id="kart-{_e(s["id"])}">',
           f'<p class="senaryo-durum"><span class="etiket">Durum</span> {_e(s["durum"])}</p>',
           "<dl>"]
    for alan, ad in KART_ALAN:
        if s.get(alan):
            sat.append(f"<dt>{ad}</dt>")
            sat.append(f"<dd>{_e(s[alan])}</dd>")
    sat += ["</dl>", f'<p class="senaryo-not">{_e(KART_NOTU)}</p>', "</div>"]
    return "\n".join(sat) + "\n"


# ─────────────────────────────────────────────────────────────── şablon blokları
BLOKLAR = ("sema", "karar", "kart", "ornek")


def blok(slug: str, tur: str, kimlik: str, no: str) -> str:
    if tur == "sema":
        return sema_blok(slug, kimlik, no)
    if tur == "karar":
        return karar_blok(slug, kimlik, no)
    if tur == "kart":
        return kart_blok(slug, kimlik)
    import masa_ornek
    return masa_ornek.ornek_blok(slug, kimlik, no)


# ─────────────────────────────────────────────────────────────── kapı
def denetle(slug: str, metin: str) -> list[str]:
    """Spesifikasyonun ve şablonun masa kuralları. Hata listesi döner."""
    h = []
    S = spek(slug)
    kul = {t: re.findall(r"\{\{#\s*" + t + r"\s+([\w-]+)", metin) for t in BLOKLAR}
    for tur in BLOKLAR:
        tanimli = [x["id"] for x in S.get(tur, [])]
        if len(tanimli) != len(set(tanimli)):
            h.append(f"{slug}: {tur} kimliği iki kez tanımlı")
        for x in set(tanimli) - set(kul[tur]):
            h.append(f"{slug}: {tur} {x!r} tanımlı ama şablonda yok")
        for x in kul[tur]:
            if kul[tur].count(x) > 1:
                h.append(f"{slug}: {tur} {x!r} şablonda birden çok kez")
    for s in S.get("sema", []):
        yazi = [s["baslik"], s.get("eksen", "")] + s.get("not", []) + [c.get("etiket", "") for c in s.get("cizgi", [])] \
            + [b.get("etiket", "") for b in s.get("bolge", [])] + [y.get("etiket", "") for y in s.get("yol", [])]
        for t in yazi:
            if OLCULMUS.search(t):
                h.append(f"{slug}: şema {s['id']}: ölçülmüş sayı izi {t!r}")
        sayi = len(s.get("not", []))
        isaret = sorted(int(m["n"]) for m in s.get("isaret", []))
        if isaret != list(range(1, sayi + 1)):
            h.append(f"{slug}: şema {s['id']}: işaretler {isaret} ile notlar ({sayi}) eşleşmiyor")
        for o, hh, ll, c in s["mumlar"]:
            if not (ll <= min(o, c) and hh >= max(o, c)):
                h.append(f"{slug}: şema {s['id']}: mum {o, hh, ll, c} geçersiz")
    for s in S.get("kart", []):
        for alan, _ in [("durum", "")] + KART_ALAN:
            if s.get(alan) and OLCULMUS.search(s[alan]):
                h.append(f"{slug}: kart {s['id']}: elle yazılmış ölçülmüş sayı izi ({alan}: {s[alan]!r})")
        for alan in ("durum", "gorursun", "yaparsin", "yapmazsin", "dayanak"):
            if not s.get(alan):
                h.append(f"{slug}: kart {s['id']}: {alan} boş")
        if s.get("dayanak") and not DAYANAK.search(s["dayanak"]):
            h.append(f"{slug}: kart {s['id']}: dayanak bir dersi adıyla anmıyor ({s['dayanak']!r})")
    for s in S.get("karar", []):
        for t in [s["baslik"], s["son"]] + [x for a in s["adim"] for x in (a["soru"], a["sonuc"])]:
            if OLCULMUS.search(t):
                h.append(f"{slug}: karar {s['id']}: ölçülmüş sayı izi {t!r}")
        for a in s["adim"]:
            if not DAYANAK.search(a.get("dayanak", "")):
                h.append(f"{slug}: karar {s['id']}: '{a['soru']}' adımının dayanağı yok")
    return h


if __name__ == "__main__":
    sys.exit("modül; şablon blokları ders_yaz.py ve buyuk_ders_yaz.py'den çağrılır")
