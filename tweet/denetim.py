#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet KALİTE KAPISI — gönderimden önce, araçta.

Neden var: tweet sitenin en kısa metni ve en geniş okur kitlesi. Bülten
denetimi (bulten/denetim.py) sayfayı sınıyor ama tweet o sayfadan KIRPILARAK
kuruluyor: kırpma bir cümleyi sayının ortasında kesebilir, iki bölüm aynı
cümleyi iki kez taşıyabilir, boş kalan bir bölümün etiketi yalnız başına
durabilir. Bunların hiçbirini sayfa denetimi göremez; tweet metnini ancak
tweet metni üzerinde koşan bir denetim görür.

İki sınıf bulgu:
  ENGEL  gönderim durur (tavsiye dili, link, HTML kalıntısı, site atfı,
         sayı ortasında kesilmiş cümle, boş bölüm etiketi, uzunluk, okur dili,
         sorumluluk notu eksik)
  UYARI  loga yazılır, gönderim sürer (tekrar eden cümle, ASCII eksi, çift boşluk)

Kullanım:
    engel, uyari = denetle(metin, tur)      # tur: bulten | teknik | analiz
    python3 tweet/denetim.py dosya.txt      # tek metni sına, çıkış 1 = engel

Kalıplar tek yerde durur: okur dili ortak/okur_dili.py'den, tavsiye dili
bulten/denetim.py'den alınır — üç ayrı liste bir gün sessizce ayrışırdı.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(KOK / "ortak"))
sys.path.insert(0, str(KOK / "bulten"))

import okur_dili  # noqa: E402

from tavsiye_dili import TAVSIYE  # noqa: E402  — bülten/teknik/analiz kapılarıyla AYNI kalıp

EN_AZ = 200          # bundan kısa bir tweet içerik değil, kaza
EN_COK = 3800        # uret.TEK_TAVAN ile aynı (Premium tavanı değil, okunurluk)

# Sorumluluk notu: her tür tweet aynı kapanışla biter. Kalıp esnek — "Analizdir;
# yatırım tavsiyesi değildir." ve "Analiz ve ölçümdür; yatırım tavsiyesi
# değildir." ikisi de geçer; aranan çekirdek ifade.
SORUMLULUK = re.compile(r"yatırım tavsiyesi değildir", re.I)

# Emoji ve süsleme: 30.08 kararı — yok. Aralıklar: semboller, piktogramlar,
# bayraklar, varyasyon seçicisi. Tipografik işaretler (−, ·, →, σ, ≈, ±) serbest.
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF️⭐⬆⬇✅❌]")

# Sayıdan hemen önce ASCII tire: "-1,88" yerine "−1,88" olmalı. Aralık tiresi
# ("%1,25-%2,10") de yakalanır ve o da yanlış — Türkçe yazımda aralık için
# uzun tire (–) kullanılır. UYARI seviyesinde: gönderimi durdurmaz, kaydı düşer.
ASCII_EKSI = re.compile(r"(?<![\w.,])-(?=[%\d])")

HTML_KALINTI = re.compile(r"<[a-zA-Z/][^>]*>|&nbsp;|&amp;|&lt;|&gt;|&#\d+;|&quot;")

# Bölüm etiketi yalnız kalmış: "Gündem" ya da "Pano:" satırının ardında içerik yok.
BOS_ETIKET = re.compile(r"^(?:[A-ZÇĞİÖŞÜ][^\n:]{1,40}):\s*$", re.M)

# Kırpma bir sayının ortasında bitmiş: "…%1," "…48,2…" "…(0," gibi.
SAYIDA_KESIK = re.compile(r"(?:[\d,.%(]|\bve|\bile|\bama|\bveya)\s*…\s*$", re.M)

# Cümle sınırı — uret._CUMLE ile aynı mantık: noktadan önce rakam olmayacak,
# sonrasında büyük harf gelecek (sıra sayısı ve binlik ayracı cümle sanılmaz).
_CUMLE = re.compile(r"(?<![0-9])(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ\"«(])")


def _site_izleri() -> tuple[str, ...]:
    """Site/bülten atfı izleri: uret.SITE_IZLERI + analiz yazıları için 'bu yazı'."""
    try:
        import uret
        temel = tuple(uret.SITE_IZLERI)
    except Exception:                                          # noqa: BLE001
        temel = ("bu sayfa", "sayfadaki", "sitede", "bülten", "yukarıda", "aşağıda")
    return temel + ("bu yazı", "bu yazıda", "yazının devamı", "yazıda ölç", "grafikte gör")


def _site_kaliplari() -> tuple:
    """'yukarıdaki tablo' gibi sayfa mobilyası kalıpları (uret ile tek tanım)."""
    try:
        import uret
        return tuple(uret.SITE_IZ_KALIPLARI)
    except Exception:                                          # noqa: BLE001
        return (re.compile(r"\b(yukarıda|aşağıda)(ki)?\s+(tablo|grafik|pano|bölüm|liste)", re.I),)


def _cumleler(metin: str) -> list[str]:
    out: list[str] = []
    for satir in metin.split("\n"):
        for c in _CUMLE.split(satir):
            c = c.strip()
            if c:
                out.append(c)
    return out


def _sade(c: str) -> str:
    return re.sub(r"[^a-z0-9çğıöşü ]", " ", c.lower()).strip()


def denetle(metin: str, tur: str = "bulten") -> tuple[list[str], list[str]]:
    """(engeller, uyarılar). Boş engel listesi = gönderilebilir."""
    engel: list[str] = []
    uyari: list[str] = []
    m = (metin or "").strip()

    # ── uzunluk
    if len(m) < EN_AZ:
        engel.append(f"metin çok kısa ({len(m)} karakter, en az {EN_AZ})")
    if len(m) > EN_COK:
        engel.append(f"metin çok uzun ({len(m)} karakter, en çok {EN_COK})")

    # ── içerik kuralları (kullanıcı kararları — 30.08 / 31.08)
    if re.search(r"https?://|www\.", m, re.I):
        engel.append("link var — tweetlerde link verilmez")
    if EMOJI.search(m):
        engel.append(f"emoji/süsleme var: {EMOJI.search(m).group(0)!r}")
    kalinti = HTML_KALINTI.search(m)
    if kalinti:
        engel.append(f"HTML kalıntısı: {kalinti.group(0)!r}")
    # Site atfı iki kademede: "bu sayfa", "sitede", "bülten", "panoda" gibi
    # izler kesin ENGEL; "yukarıda"/"aşağıda" ise Türkçede "daha yüksek/düşük"
    # anlamına da gelir ("İTO sistematik olarak yukarıda geliyor") — o ikisi
    # gönderimi durdurmaz, kayda düşer ve yazan kişi kararını kendisi verir.
    alt = m.lower()
    belirsiz = {"yukarıda", "aşağıda"}
    izler = [iz for iz in _site_izleri() if iz in alt]
    kesin = [iz for iz in izler if iz not in belirsiz]
    if kesin:
        engel.append("siteye/bültene atıf var: " + ", ".join(repr(i) for i in kesin[:4]))
    for kalip in _site_kaliplari():                       # "yukarıdaki tablo" → kesin atıf
        k = kalip.search(m)
        if k:
            engel.append(f"sayfa mobilyasına atıf: {k.group(0)!r}")
            break
    else:
        if re.search(r"\b(yukarıda|aşağıda)\b", alt):
            uyari.append("'yukarıda/aşağıda' geçiyor — sayfaya atıf mı, seviye mi? Okuyup karar ver.")

    # ── tavsiye dili (bülten denetimiyle aynı kalıp)
    t = TAVSIYE.search(m)
    if t:
        engel.append(f"tavsiye dili: {t.group(0)!r}")

    # ── okur dili (ortak tanım)
    bulgu = okur_dili.tara(m)
    if bulgu:
        dokum = " · ".join(f"{a}: {e!r}" for a, e, _ in bulgu[:4])
        engel.append("okura değil kendimize yazan dil — " + dokum)

    # ── biçim: kırpma kalitesi, boş etiket, kapanış
    if SAYIDA_KESIK.search(m):
        engel.append("kırpma bir sayının ya da bağlacın ortasında bitmiş ("
                     + SAYIDA_KESIK.search(m).group(0).strip() + ")")
    bos = BOS_ETIKET.findall(m)
    if bos:
        engel.append("içeriksiz bölüm etiketi: " + ", ".join(repr(b) for b in bos[:3]))
    if m and not re.search(r"[.!?…»\")]$", m):
        engel.append(f"metin cümle sonuyla bitmiyor: {m[-30:]!r}")
    if not SORUMLULUK.search(m):
        engel.append("sorumluluk notu yok ('… yatırım tavsiyesi değildir.')")

    # ── tekrar: aynı cümle (≥ 8 kelime) iki kez
    gorulen: dict[str, int] = {}
    for c in _cumleler(m):
        s = _sade(c)
        if len(s.split()) >= 8:
            gorulen[s] = gorulen.get(s, 0) + 1
    tekrar = [s for s, n in gorulen.items() if n > 1]
    if tekrar:
        uyari.append(f"{len(tekrar)} cümle iki kez geçiyor: {tekrar[0][:70]!r}…")

    # ── tipografi
    n_eksi = len(ASCII_EKSI.findall(m))
    if n_eksi:
        uyari.append(f"sayı önünde ASCII tire {n_eksi} yerde (− ya da – bekleniyor)")
    if "  " in m:
        uyari.append("çift boşluk var")
    if re.search(r"\s[,.;:!?]", m):
        uyari.append("noktalamadan önce boşluk var")

    return engel, uyari


def rapor(engel: list[str], uyari: list[str], baslik: str = "") -> str:
    satirlar = []
    if baslik:
        satirlar.append(f"── tweet denetimi: {baslik}")
    for e in engel:
        satirlar.append(f"  ✗ ENGEL  {e}")
    for u in uyari:
        satirlar.append(f"  ! UYARI  {u}")
    if not engel and not uyari:
        satirlar.append("  ✓ temiz")
    return "\n".join(satirlar)


def main() -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dosya", help="tweet metni (düz metin dosyası, '-' = stdin)")
    p.add_argument("--tur", choices=("bulten", "teknik", "analiz"), default="analiz")
    a = p.parse_args()
    metin = sys.stdin.read() if a.dosya == "-" else Path(a.dosya).read_text(encoding="utf-8")
    engel, uyari = denetle(metin, a.tur)
    print(rapor(engel, uyari, a.dosya))
    return 1 if engel else 0


if __name__ == "__main__":
    raise SystemExit(main())
