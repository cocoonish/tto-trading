#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analiz yazısından X gönderisi — yönetici özetinden, deterministik.

Analizler X'e şimdiye dek elle yazılan metinlerle (tweet/ozel/*.txt) çıktı;
her yazı için bir insan oturup özet yazdı ve iş akışını elle tetikledi. Bu
modül aynı işi ARAÇLA yapar: yazının kendi yönetici özetini (tez, soru–cevap
tablosu, altı anahtar ölçüm) alır ve gönderi metnine çevirir. Yeni hüküm
ÜRETMEZ — cümleler yazının kendi cümleleri, sayılar yazının kendi sayılarıdır.

Sayılar CANLI çözülür: yazıdaki her <Deger proje anahtar> etiketi, sayfanın
yaptığı gibi, hattın site/public/projeler/<proje>/ozet.json dosyasından okunur
ve Türkçe yazımla basılır. Yedek metin yalnız değer bulunamazsa kalır.

Ağa çıkmaz; duman sınaması gerçek yazılarla çağırır.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
ANALIZ_DIZIN = KOK / "site" / "src" / "content" / "analiz"
OZET_DIZIN = KOK / "site" / "public" / "projeler"

import uret  # tek tavan, tek kırpma, tek tipografi

TEZ_SINIR = 900            # tez paragrafı
SATIR_SINIR = 420          # tablo satırı başına
RAKAM_SINIR = 700          # rakam şeridi
GOVDE_SINIR = uret.TEK_TAVAN
_kirp = uret._kirp

# Yönetici özeti sayfa mobilyasına atıf yapabilir; tweet kendi başına durur.
IZLER = ("bu yazı", "yazının", "yazıda", "yukarıdaki", "aşağıdaki", "bölümünde",
         "bu sayfa", "sayfadaki", "grafikte", "tabloda", "sitede")

_CUMLE = re.compile(r"(?<![0-9])(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ\"«(])")


# ── ön bilgi ─────────────────────────────────────────────────────────────────
# Tek ayrıştırıcı: ortak/on_bilgi.py (analiz kapısıyla aynı).
import sys as _sys
_sys.path.insert(0, str(KOK / "ortak"))
import on_bilgi as _on_bilgi  # noqa: E402

on_bilgi = _on_bilgi.ayristir


def analizi_oku(yol: Path) -> dict:
    metin = yol.read_text(encoding="utf-8")
    fm = _on_bilgi.ayristir(metin)
    return {"slug": yol.stem, "yol": yol, "govde": _on_bilgi.govde(metin), **fm}


def analizler(dizin: Path | None = None) -> list[dict]:
    return [analizi_oku(y) for y in sorted((dizin or ANALIZ_DIZIN).glob("*.mdx"))]


# ── canlı sayı çözümü (<Deger>) ─────────────────────────────────────────────

_OZET_ONBELLEK: dict[str, dict] = {}


def _ozet(proje: str, dizin: Path | None = None) -> dict:
    if proje not in _OZET_ONBELLEK:
        yol = (dizin or OZET_DIZIN) / proje / "ozet.json"
        try:
            _OZET_ONBELLEK[proje] = json.loads(yol.read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            _OZET_ONBELLEK[proje] = {}
    return _OZET_ONBELLEK[proje]


def tr_sayi(v: float, ondalik: int, isaret: bool = False) -> str:
    """Deger bileşeniyle aynı yazım: tr-TR ayraçları, eksi U+2212, isteğe bağlı +."""
    s = f"{abs(float(v)):,.{ondalik}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    if v < 0:
        return "−" + s
    return ("+" if isaret and v > 0 else "") + s


_DEGER = re.compile(r"<Deger\s+([^>]*?)>(.*?)</Deger>", re.S)


def _nitelik(nit: str, ad: str) -> str | None:
    m = re.search(ad + r'=(?:"([^"]*)"|\{([^}]*)\})', nit)
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def degerleri_coz(html: str, ozet_dizin: Path | None = None) -> str:
    """<Deger …>yedek</Deger> → canlı değer (bulunamazsa yedek)."""
    def yerine(m: re.Match) -> str:
        nit, yedek = m.group(1), m.group(2)
        proje = _nitelik(nit, "proje") or ""
        anahtar = _nitelik(nit, "anahtar") or ""
        v = _ozet(proje, ozet_dizin).get(anahtar)
        if v is None or isinstance(v, bool):
            return yedek
        if isinstance(v, (int, float)):
            ond = int(_nitelik(nit, "ondalik") or 1)
            isaret = (_nitelik(nit, "isaret") or "").strip() == "true"
            return tr_sayi(v, ond, isaret)
        return str(v)
    return _DEGER.sub(yerine, html)


# ── yönetici özeti ───────────────────────────────────────────────────────────

def _duz(html: str) -> str:
    m = re.sub(r"<[^>]+>", " ", html or "")
    m = (m.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<")
          .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'"))
    m = re.sub(r"\{/\*.*?\*/\}", " ", m, flags=re.S)
    m = re.sub(r"\s+", " ", m).strip()
    # "% 1,48" → "%1,48": etiket sökümü yüzde ile sayı arasına boşluk bırakır
    m = re.sub(r"%\s+(?=[\d−+])", "%", m)
    m = re.sub(r"\s+([,.;:)])", r"\1", m)
    m = re.sub(r"\(\s+", "(", m)
    return m


def yonetici_ozeti(govde: str) -> dict | None:
    m = re.search(r'<div class="yonetici">(.*?)\n</div>', govde, re.S)
    if not m:
        return None
    blok = degerleri_coz(m.group(1))
    tez_m = re.search(r'<p class="tez">(.*?)</p>', blok, re.S)
    tez = _duz(tez_m.group(1)) if tez_m else ""
    satirlar: list[tuple[str, str]] = []
    for tr in re.findall(r"<tr>(.*?)</tr>", blok, re.S):
        hucreler = re.findall(r"<td>(.*?)</td>", tr, re.S)
        if len(hucreler) >= 2:
            satirlar.append((_duz(hucreler[0]), _duz(hucreler[1])))
    rakamlar: list[tuple[str, str]] = []
    rk = re.search(r'<ul class="rakamlar">(.*?)</ul>', blok, re.S)
    if rk:
        for li in re.findall(r"<li>(.*?)</li>", rk.group(1), re.S):
            # Sözleşme <li><b>değer</b><span>etiket</span></li>; eski bir yazı
            # span'ı atlayıp etiketi <b>'den sonra düz metin yazmış olabilir —
            # o durumda <b>'den sonrası etiket sayılır (rehber sonrası yazılarda
            # kapı tam işaretlemeyi zorunlu kılar).
            b = re.search(r"<b>(.*?)</b>", li, re.S)
            if not b:
                continue
            sp = re.search(r"<span>(.*?)</span>", li, re.S)
            etiket = _duz(sp.group(1)) if sp else _duz(li[b.end():])
            if etiket:
                rakamlar.append((_duz(b.group(1)), etiket))
    return {"tez": tez, "satirlar": satirlar, "rakamlar": rakamlar}


# ── gönderi metni ────────────────────────────────────────────────────────────

def _buyuk_tr(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def _site_disi(metin: str) -> str:
    """Sayfa mobilyasına atıf yapan cümleleri düşür; düşenler uret.DUSEN'e yazılır."""
    kalan = []
    for c in _CUMLE.split(metin or ""):
        if not c.strip():
            continue
        if any(iz in c.lower() for iz in IZLER) or uret._site_izi_var(c):
            uret.DUSEN.append(("analiz", c.strip()))
            continue
        kalan.append(c.strip())
    return " ".join(kalan)




_TARIH_ONEKI = re.compile(r"^\s*(\d{1,2}\s+(?:Ocak|Şubat|Mart|Nisan|Mayıs|Haziran|Temmuz|Ağustos|Eylül|Ekim|Kasım|Aralık)\s+\d{4})\s+")


def _baslik(a: dict) -> list[str]:
    """İlk satır bültenle aynı aileden: 'Analiz — 1 Eylül 2026'; ikinci satır
    yazının başlığı (tarih öneki soyulur — ilk satırda zaten var)."""
    title = str(a.get("title") or a["slug"])
    m = _TARIH_ONEKI.match(title)
    if m:
        tarih, govde = m.group(1), title[m.end():]
    else:
        pub = str(a.get("pubDate") or "")[:10]
        try:
            y, ay, g = pub.split("-")
            tarih = f"{int(g)} {AYLAR_TR[int(ay)]} {y}"
        except Exception:                                      # noqa: BLE001
            tarih = pub
        govde = title
    return [f"Analiz — {tarih}", govde.strip()]


AYLAR_TR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
            "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def analiz_zinciri(a: dict) -> list[str]:
    """Analizden TEK uzun gönderi. Yönetici özeti varsa ondan; yoksa ön
    bilgideki tez (ozet) ve açıklamadan. Link yok, emoji yok, site atfı yok."""
    uret.DUSEN.clear()
    yo = yonetici_ozeti(a.get("govde", ""))
    bolumler = ["\n".join(_baslik(a))]
    if yo and (yo["tez"] or yo["satirlar"]):
        tez = _site_disi(yo["tez"])
        if tez:
            bolumler.append(_kirp(tez, TEZ_SINIR))
        for soru, cevap in yo["satirlar"]:
            c = _site_disi(cevap)
            if not c:
                continue
            bolumler.append(f"{_buyuk_tr(soru).rstrip('.?!')}. {_kirp(c, SATIR_SINIR)}")
        if yo["rakamlar"]:
            parcalar = [f"{etiket}: {deger}" for deger, etiket in yo["rakamlar"] if deger and etiket]
            if parcalar:
                bolumler.append(_kirp("Kilit ölçümler — " + " · ".join(parcalar), RAKAM_SINIR))
    else:
        # Yedek yol: yalnız ön bilgideki TEZ (ozet). Açıklama alınmaz — statik
        # metindir, sayıları canlı değildir; yönetici özeti olmayan bir yazının
        # gönderisi kısa olur ve bunu söyler.
        tez = _site_disi(_duz(str(a.get("ozet") or "")))
        if not tez:
            raise SystemExit(f"{a['slug']}: yönetici özeti de tez de yok — gönderi kurulamaz")
        bolumler.append(_kirp(tez, TEZ_SINIR))
    # Tavan aşılıyorsa sondan değil ORTADAN kısılır: rakam şeridi ve tez kalır,
    # tablo satırları SONDAN itibaren düşer.
    def _metin() -> str:
        return uret._kapat("\n\n".join(b for b in bolumler if b), uret.SORUMLULUK_TEKNIK)
    metin = _metin()
    while len(metin) > GOVDE_SINIR and len(bolumler) > 3:
        # bolumler: [başlık, tez, satır…, (rakamlar)] — sondan bir önceki satır düşer
        cikar = len(bolumler) - 2 if bolumler[-1].startswith("Kilit ölçümler") else len(bolumler) - 1
        if cikar <= 1:
            break
        bolumler.pop(cikar)
        metin = _metin()
    return [metin]


def yedek_kalan_sayisi(html: str, ozet_dizin: Path | None = None) -> int:
    """Kaç <Deger> canlı çözülemedi (yedek metin kaldı) — uyarı ölçüsü."""
    n = 0
    for m in _DEGER.finditer(html):
        nit = m.group(1)
        v = _ozet(_nitelik(nit, "proje") or "", ozet_dizin).get(_nitelik(nit, "anahtar") or "")
        if v is None or isinstance(v, bool):
            n += 1
    return n


def bugunun_analizleri(gun: date | None = None, dizin: Path | None = None) -> list[dict]:
    """pubDate'i verilen güne eşit, yayımda (durum aktif) analizler."""
    gun = gun or date.today()
    out = []
    for a in analizler(dizin):
        if str(a.get("durum", "aktif")) != "aktif":
            continue
        if str(a.get("pubDate", "")).strip()[:10] == gun.isoformat():
            out.append(a)
    return out


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="analiz gönderisini bas (kuru)")
    p.add_argument("slug", nargs="?", help="analiz slug'ı (varsayılan: bugünün yazıları)")
    a = p.parse_args()
    secilen = [analizi_oku(ANALIZ_DIZIN / f"{a.slug}.mdx")] if a.slug else bugunun_analizleri()
    for an in secilen:
        t = analiz_zinciri(an)[0]
        print(f"── {an['slug']} ({len(t)} karakter)\n{t}\n")
