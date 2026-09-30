#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STRATEJİ BELGESİ AYRIŞTIRICISI — İç Borçlanma Stratejisi'nin üç tablosu.

Girdi bir belgenin sayfa sayfa metnidir (keşif koşusunun arşivi; ayrıştırıcı
düzeltilirse kaynak yeniden indirilmez). Üç tablo okunur:

  A. İç borç ödemeleri — ödeme günü × (piyasa, kamu, toplam), milyon TL
  B. Finansman programı — kalem × ay, milyar TL
  C. İç borç ihraç takvimi — ihale günü, valör, itfa, senet, vade, yöntem

YALNIZ STANDART KÜTÜPHANE: yayın kapısındaki doğrulayıcı bu modülü içe
aktarır ve yayın koşucusunda pandas yok.

SAYI SÖZLEŞMESİ. Belgeler iki biçimi karıştırıyor: ödeme tablosu milyon TL ve
binlik NOKTA ("243.114"), finansman tablosu milyar TL ve ondalık VİRGÜL
("436,6"); eski belgelerde ondalık nokta da görülüyor ("24.4"). Ayırıcıdan
sonra tam üç rakam geliyorsa binlik, bir-iki rakam geliyorsa ondalık sayılır —
tahmin değil, tabloların kendi yazım kuralı.
"""
from __future__ import annotations

import re

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
AY_NO = {a: i + 1 for i, a in enumerate(AYLAR)}
_AY_BUYUK = {a.upper().replace("İ", "I"): a for a in AYLAR}

SAYI = r"[−\-]?\d+(?:[.,]\d+)*"


def sayi(s: str) -> float:
    s = s.strip().replace("−", "-")
    if "," in s and "." in s:                     # 1.234,5
        return float(s.replace(".", "").replace(",", "."))
    for ayr in (",", "."):
        if ayr in s:
            bas, son = s.rsplit(ayr, 1)
            # Ayırıcıdan sonra tam ÜÇ rakam: binlik ("243.114", 2021
            # belgelerinde "7,648"). Finansman tablosu hep tek ondalıklıdır,
            # ödeme tablosu hep tam sayı milyon TL — üç ondalıklı sayı yok.
            if len(son) == 3:
                return float(s.replace(ayr, ""))
            return float(bas.replace(".", "").replace(",", "") + "." + son)
    return float(s)


def _gun(s: str) -> str:
    g, a, y = s.split(".")
    return f"{int(y):04d}-{int(a):02d}-{int(g):02d}"


# ───────────────────────────────────────────────────────────── A · ödemeler
_ODEME = re.compile(r"^\s*(\d{1,2}\.\d{1,2}\.\d{4})(?:\s*\([^)]*\))?\s+(" + SAYI + r")\s+(" + SAYI
                    + r")\s+(" + SAYI + r")\s*$")
_TOPLAM = re.compile(r"^\s*TOPLAM\s+(" + SAYI + r")\s+(" + SAYI + r")\s+(" + SAYI + r")\s*$")


def odemeler(metin: str) -> dict:
    """{'gunler': [{gun, piyasa, kamu, toplam}], 'aylar': {YYYY-MM: {...}}}"""
    gunler, aylar = [], {}
    kume = []
    for satir in metin.splitlines():
        m = _ODEME.match(satir)
        if m:
            gunler.append({"gun": _gun(m.group(1)), "piyasa": sayi(m.group(2)),
                           "kamu": sayi(m.group(3)), "toplam": sayi(m.group(4))})
            kume.append(gunler[-1])
            continue
        m = _TOPLAM.match(satir)
        if m and kume:
            ay = kume[0]["gun"][:7]
            aylar[ay] = {"piyasa": sayi(m.group(1)), "kamu": sayi(m.group(2)),
                         "toplam": sayi(m.group(3)), "gun_sayisi": len(kume)}
            kume = []
    return {"gunler": gunler, "aylar": aylar}


# ───────────────────────────────────────────────────────── B · finansman
KALEMLER = [
    ("odemeler", r"Ödemeler"),
    ("ic_servis", r"İç Borç Servisi"),
    ("dis_servis", r"Dış Borç Servisi"),
    ("finansman", r"Finansman"),
    ("borclanma_disi", r"Borçlanma Dışı Kaynaklar"),
    ("ihale", r"Piyasadan İhale Yoluyla İç Borçlanma"),
    # 2020 sonu belgelerinde aynı kalemin adı "Kira Sertifikası (4)" —
    # dipnotu da aynı (piyasa koşullarına bağlı tutar), yani aynı satır.
    ("dogrudan", r"(?:Doğrudan Satışlar|Kira Sertifikası)"),
    ("kamu", r"Kamuya Satışlar"),
    ("dis_borclanma", r"Dış Borçlanma"),
    ("ic_borclanma", r"İç Borçlanma"),
    ("borclanma", r"Borçlanma"),
    ("anapara", r"Anapara"),
    ("faiz", r"Faiz"),
]


def finansman(metin: str) -> dict:
    """{YYYY-MM: {kalem: milyar TL}} — Anapara/Faiz üst kalemine göre adlanır."""
    aylar: list[str] = []
    out: dict[str, dict] = {}
    ust = None
    # Etiketi ile sayıları ayrı satıra düşen kalem ("Borçlanma Dışı Kaynaklar
    # (2)(3)" / "-45,7 90,4 -41,2", 2023–2024 belgeleri) birleştirilir: satır
    # yalnız sayılardan oluşuyorsa bir önceki sayısız etiket satırına eklenir.
    satirlar: list[str] = []
    for satir in metin.splitlines():
        if (satirlar and re.fullmatch(r"\s*(?:" + SAYI + r"\s*)+", satir)
                and not re.search(SAYI + r"\s*$", satirlar[-1].split(")")[-1])):
            satirlar[-1] = satirlar[-1].rstrip() + " " + satir.strip()
        else:
            satirlar.append(satir)
    for satir in satirlar:
        if "(Milyar" in satir and not aylar:
            aylar = [f"{y}-{AY_NO[a]:02d}" for a, y in
                     re.findall(r"(" + "|".join(AYLAR) + r")\s+(\d{4})", satir)]
            for a in aylar:
                out[a] = {}
            continue
        if not aylar:
            continue
        s = satir.strip()
        for ad, kalip in KALEMLER:
            m = re.match(r"^" + kalip + r"(?:\s*\(\d\))*\s+((?:" + SAYI + r"\s*){%d})$" % len(aylar), s)
            if not m:
                continue
            degerler = [sayi(x) for x in re.findall(SAYI, m.group(1))]
            if len(degerler) != len(aylar):
                continue
            if ad == "ic_servis":
                ust = "ic"
            elif ad == "dis_servis":
                ust = "dis"
            anahtar = ad
            if ad in ("anapara", "faiz"):
                if ust is None:
                    break
                anahtar = f"{ust}_{ad}"
            for a, v in zip(aylar, degerler):
                out[a].setdefault(anahtar, v)
            break
    return out


# ─────────────────────────────────────────────────────────── C · takvim
_TAKVIM = re.compile(
    r"(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+(\d{1,2}\.\d{1,2}\.\d{4})\s+"
    r"(.+?)\s+(\d+(?:[.,]\d+)?\s*(?:Yıl|Ay|Gün)\s*/\s*[\d.]+\s*Gün|\d+(?:[.,]\d+)?\s*(?:Yıl|Ay))\s+"
    r"(İhale\s*/\s*(?:Yeniden|İlk)\s*[İi]hra[cç]|Doğrudan\s*Satış|Halka\s*Arz|[İi]hale)",
    re.IGNORECASE)


def _vade_yil(terim: str) -> float | None:
    m = re.search(r"/\s*([\d.]+)\s*Gün", terim)
    if m:
        return int(m.group(1).replace(".", "")) / 365.0
    m = re.match(r"(\d+(?:[.,]\d+)?)\s*Yıl", terim)          # "1,5 Yıl"
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.match(r"(\d+)\s*Ay", terim)
    return float(m.group(1)) / 12.0 if m else None


def takvim(metin: str) -> list[dict]:
    duz = re.sub(r"\s+", " ", metin)
    out = []
    for m in _TAKVIM.finditer(duz):
        yontem = re.sub(r"\s+", " ", m.group(6)).strip()
        out.append({
            "ihale": _gun(m.group(1)), "valor": _gun(m.group(2)), "itfa": _gun(m.group(3)),
            "senet": re.sub(r"\s+", " ", m.group(4)).strip(),
            "terim": re.sub(r"\s+", " ", m.group(5)).strip(),
            "vade": _vade_yil(m.group(5)),
            "yontem": yontem,
            "dogrudan": yontem.lower().startswith("doğrudan"),
        })
    return out


def donem(metin: str) -> tuple[str, str] | None:
    """Belgenin kapsadığı ilk ve son ay: ('2026-10', '2026-12')."""
    duz = re.sub(r"\s+", " ", metin)
    m = re.search(r"İÇ BORÇLANMA STRATEJİSİ\s+([A-ZÇĞİÖŞÜ]+)\s*(\d{4})?\s*[–\-]\s*([A-ZÇĞİÖŞÜ]+)\s+(\d{4})", duz)
    if not m:
        return None
    a1 = _AY_BUYUK.get(m.group(1).replace("İ", "I"))
    a2 = _AY_BUYUK.get(m.group(3).replace("İ", "I"))
    if not a1 or not a2:
        return None
    y2 = int(m.group(4))
    y1 = int(m.group(2)) if m.group(2) else (y2 if AY_NO[a1] <= AY_NO[a2] else y2 - 1)
    return f"{y1}-{AY_NO[a1]:02d}", f"{y2}-{AY_NO[a2]:02d}"


def oku(kayit: dict) -> dict:
    """Arşiv kaydı (künye + sayfa metinleri) → üç tablo."""
    metin = "\n".join(kayit.get("metin") or [])
    return {"baslik": kayit["baslik"].replace("&#8211;", "–"),
            "duyuru": kayit["duyuru"][:10], "sha256": kayit.get("sha256"),
            "donem": donem(metin), "odemeler": odemeler(metin),
            "finansman": finansman(metin), "takvim": takvim(metin)}
