#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tweet zinciri ÜRETİMİ — yazılmış bültenlerden, deterministik.

Zincir metni yalnız YAYIMLANMIŞ içerikten kurulur: günlük/haftalık bültenin
yazı katmanından geçmiş JSON'u ile teknik analizin yorum kapısından geçmiş
JSON'u. Burada yeni hüküm ÜRETİLMEZ — özet cümleleri yazı katmanının kendi
cümleleridir, sayılar ölçümün kendi sayılarıdır. Uydurma yok, sosyal medyada
da yok.

Gönderim ayrı (tweet/gonder.py); bu modül ağa çıkmaz, duman sınaması bunu
sentetik veriyle çağırır.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTENLER = KOK / "site" / "src" / "data" / "bulten"
TEKNIKLER = KOK / "site" / "src" / "data" / "teknik"

SITE = "https://cocoonish.github.io"
SINIR = 275                 # tek tweet üst sınırı (URL'siz gövde için)

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def _duz(metin: str) -> str:
    """HTML → düz metin: etiketler söker, boşluk normalleştirir."""
    m = re.sub(r"<[^>]+>", " ", metin or "")
    return re.sub(r"\s+", " ", m).strip()


def _kirp(metin: str, sinir: int = SINIR) -> str:
    """Cümle sınırında kırpar; sığmazsa kelime sınırında, '…' ile."""
    m = metin.strip()
    if len(m) <= sinir:
        return m
    # son tam cümle
    kes = -1
    for isaret in (". ", "! ", "? ", "; "):
        i = m.rfind(isaret, 0, sinir)
        kes = max(kes, i + 1 if i > 0 else -1)
    if kes > sinir * 0.5:
        return m[:kes].strip()
    i = m.rfind(" ", 0, sinir - 1)
    return (m[:i] if i > 0 else m[:sinir - 1]).rstrip(" ,;·") + "…"


def _tr_sayi(x: float, ondalik: int = 2) -> str:
    s = f"{x:+,.{ondalik}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".")


def _fiyat(x, ondalik: int = 2) -> str:
    """İşaretsiz Türkçe sayı: 14641.6 → '14.641,6'."""
    if x is None:
        return "—"
    nd = max(int(2 if ondalik is None else ondalik), 1)
    s = f"{float(x):,.{nd}f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return s.rstrip("0").rstrip(",") if "," in s else s


def _degisim_metni(x: float, birim: str) -> str:
    """Türkçe yazımla işaretli değişim: %'de işaret öne gelir (+%5,98)."""
    if abs(x) < 0.005:
        return "yatay"
    isaret = "+" if x > 0 else "−"
    govde = _tr_sayi(abs(x)).lstrip("+")
    if birim.strip() == "%":
        return f"{isaret}%{govde}"
    return f"{isaret}{govde}{birim}"


def _tr_tarih(iso: str) -> str:
    y, a, g = iso.split("-")
    return f"{int(g)} {AYLAR[int(a)]} {y}"


# ── bülten zinciri ───────────────────────────────────────────────────────────

def bulten_zinciri(b: dict) -> list[str]:
    """Günlük/haftalık bültenden 4 tweetlik zincir."""
    haftalik = bool(b.get("haftalik"))
    baslik = "Haftaya Bakış" if haftalik else "Sabah Bülteni"
    tarih = _tr_tarih(b["tarih"])
    tweets: list[str] = []

    oz = b.get("ozet") or {}
    ne_oldu = _duz(oz.get("ne_oldu") or "")
    if not ne_oldu:
        raise SystemExit("bülten özeti boş — tweet zinciri kurulamaz")
    tweets.append(_kirp(f"📰 {baslik} · {tarih}\n\n{ne_oldu}", SINIR))

    em = (b.get("piyasa") or {}).get("en_cok_hareket") or {}
    kip = em.get("sigma_kip") or ("haftalik" if haftalik else "gunluk")
    liste = em.get(kip) or []
    if liste:
        etiket = "Haftanın hareketleri" if kip == "haftalik" else "Günün hareketleri"
        satirlar = [f"• {h['ad']}: {_degisim_metni(h['deger'], h.get('birim', ''))}"
                    for h in liste[:5] if h.get("deger") is not None]
        tweets.append(_kirp(f"{etiket}:\n" + "\n".join(satirlar), SINIR))

    gost = b.get("gostergeler") or []
    satirlar = []
    for g in gost[:5]:
        if g.get("metin") and g.get("ad"):
            fark = f" ({g['fark_metin']})" if g.get("fark_metin") else ""
            satirlar.append(f"• {g['ad']}: {g['metin']}{fark}")
    if satirlar:
        tweets.append(_kirp("Pano:\n" + "\n".join(satirlar), SINIR))

    ne_bek = _duz(oz.get("ne_bekleniyor") or "")
    kuyruk = f"\n\nBültenin tamamı grafikler ve kaynaklarla:\n{SITE}/bulten/"
    govde = _kirp(ne_bek, SINIR - len(kuyruk)) if ne_bek else "Bültenin tamamı:"
    tweets.append(govde + kuyruk)
    return tweets


# ── teknik zinciri ───────────────────────────────────────────────────────────

def _teknik_satir(e: dict) -> str | None:
    d1 = (e.get("degisim") or {}).get("h1")
    ondalik = e.get("ondalik")
    birim = " bp" if e.get("tip") == "getiri" else "%"
    parca = f"• {e['ad']}: {_fiyat(e.get('son'), ondalik)}"
    if d1 is not None:
        parca += f" (1h {_degisim_metni(d1, birim)})"
    # yapı bayrağı: en bilgilendirici olanı tek kelimeyle
    gun = (e.get("dilimler") or {}).get("gun") or {}
    s1 = (e.get("dilimler") or {}).get("s1") or {}
    for kaynak, ad in ((s1, "1s"), (gun, "günlük")):
        y = kaynak.get("yapi") or {}
        if y.get("sikisma"):
            return parca + f" — {ad} sıkışma"
        if y.get("cift_tepe"):
            return parca + f" — {ad} çift tepe {_fiyat(y['cift_tepe']['seviye'], ondalik)}"
        if y.get("cift_dip"):
            return parca + f" — {ad} çift dip {_fiyat(y['cift_dip']['seviye'], ondalik)}"
    return parca


def _grupla(satirlar: list[str], baslik: str, sinir: int = SINIR) -> list[str]:
    """Satırları tweetlere böler — HİÇBİR SATIR ATILMAZ, ortadan kırpılmaz.
    İlk tweet başlığı taşır; sığmayan satır sonraki tweete taşar."""
    tweets: list[str] = []
    govde = baslik
    for s in satirlar:
        aday = (govde + "\n" + s) if govde else s
        if len(aday) > sinir and govde and govde != baslik:
            tweets.append(govde)
            govde = s
        else:
            govde = aday
    if govde and govde != baslik:
        tweets.append(govde)
    return tweets


def teknik_zinciri(t: dict) -> list[str]:
    """Haftalık teknik analizden zincir: kapak + enstrüman satırları + link."""
    tarih = _tr_tarih(t["tarih"])
    giris = _duz(t.get("giris") or "")
    if not giris:
        raise SystemExit("teknik giriş boş — tweet zinciri kurulamaz")
    tweets = [_kirp(f"📐 Haftalık Teknik Analiz · {tarih}\n\n{giris}", SINIR)]

    satirlar = [s for s in (_teknik_satir(e) for e in t.get("enstrumanlar") or [])
                if s]
    if satirlar:
        n = len(satirlar)
        tweets += _grupla(satirlar, f"{n} enstrüman · 1S/4S/G üç dilimde:")

    tweets.append("Her seviyenin dokunuş sayısı, formasyonların ölçülü "
                  "noktaları ve 17 grafik sayfada — yorum yapay zekâ, her "
                  f"sayı ölçümden:\n{SITE}/teknik/")
    return tweets


# ── kaynak seçimi ────────────────────────────────────────────────────────────

def yazilmis_bulten(tarih: str) -> dict | None:
    yol = BULTENLER / f"{tarih}.json"
    if not yol.exists():
        return None
    b = json.loads(yol.read_text(encoding="utf-8"))
    return b if b.get("gundem_kaynagi") == "yazili" else None


def yazilmis_teknik(tarih: str) -> dict | None:
    yol = TEKNIKLER / f"{tarih}.json"
    if not yol.exists():
        return None
    t = json.loads(yol.read_text(encoding="utf-8"))
    return t if t.get("yazili") else None
