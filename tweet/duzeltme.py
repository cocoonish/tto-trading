#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DÜZELTME YANITI — yayımlanmış bir gönderideki hatalı sayı ya da iddia için
orijinalin altına "Düzeltme" yanıtı (karar 05.10.2026).

Sitede her yayımlanmış sayının tarihli bir düzeltme kaydı var (bülten JSON'unun
`duzeltmeler` alanı, analiz ön bilgisinin `duzeltmeler` listesi); X'te yoktu.
Hatalı bir sayı X'te düzeltilmeden duruyordu.

TETİK AÇIKTIR. Hangi düzeltmenin X'e gideceğine YAZAR karar verir: düzeltme
kaydına iki isteğe bağlı alan yazar —

    gonderi        hedef gönderinin defter anahtarı ("bulten:2026-10-04",
                   "analiz:<slug>"); tweet/defter.json'da KİMLİKLİ olmalı
    gonderi_metni  yazarın kısa düzeltme metni (düz metin, sayfa yapısı anmaz)

Otomatik alt dize tetiği bilerek YOK. Ölçüldü (05.10.2026): kayıtların `eski`
değerini arşivde aramak 85 kaydın yalnız 9'unda eşleşiyor ve bunların 3'ü
YANLIŞ gönderiye düşüyor ("%2,56" → "Brent −%2,56"); gerçek vakaları da
kaçırıyor (bileşik `eski` metni gönderide birebir geçmiyor). İlgisiz bir
gönderinin altına atılan herkese açık bir "Düzeltme", korumak istediği güveni
doğrudan zedeler.

Metin alanlardan mekanik KURULMAZ: kayıtların beşte biri sayfa yapısını anıyor
("gösterge şeridi", "Türkiye bölümü") ve X okurunun elinde o sayfa yok. Gönderi
yazarın `gonderi_metni`dir; araç yalnız başlığı ("Düzeltme — <hedefin başlığı>")
ve sorumluluk notunu ekler.

DEFTER ANAHTARI içeriğe bağlıdır: duzeltme:<hedef>:<sha1(eski|yeni)[:8]>.
Aynı kayıt birkaç bülten dosyasında çoğalsa da (yazı katmanı listeyi bütünüyle
yeniden yazar) tek gönderi çıkar; düzeltmenin düzeltmesi başka bir eski→yeni
çifti olduğu için ayrı anahtarla, AYNI ana gönderinin altına gider.

PENCERE: son PENCERE_GUN günün bülten dosyaları ve son PENCERE_GUN gün içinde
tarihlenmiş analiz kayıtları. Geçmiş gönderiler için düzeltme ATILMAZ: bugün
hiçbir kayıt `gonderi` taşımıyor (kullanıcı ayrıca karar verir).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
import uret  # noqa: E402
import analiz as analiz_m  # noqa: E402

ARSIV = BURASI / "arsiv"
PENCERE_GUN = 21
ON_EK = "duzeltme"
HEDEF_RE = re.compile(r"^(bulten|analiz|teknik|ozel):\S+$")

AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]


def anahtar(hedef: str, eski: str, yeni: str) -> str:
    """İçeriğe bağlı defter anahtarı — sıraya değil (sıra her yamada kayar)."""
    oz = hashlib.sha1(f"{eski}|{yeni}".encode("utf-8")).hexdigest()[:8]
    return f"{ON_EK}:{hedef}:{oz}"


def kimlikli(defter: dict, hedef: str) -> str | None:
    """Hedefin zincirindeki İLK kimlik; kimliksizse None (yanıt atılamaz)."""
    idler = (defter.get(hedef) or {}).get("idler") or []
    return str(idler[0]) if idler else None


# ── kaynaklar ────────────────────────────────────────────────────────────────

def _bulten_kayitlari(bugun: dt.date, dizin: Path) -> list[dict]:
    out = []
    if not dizin.exists():
        return out
    for p in sorted(dizin.glob("*.json")):
        try:
            gun = dt.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if not (bugun - dt.timedelta(days=PENCERE_GUN) <= gun <= bugun):
            continue
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                      # noqa: BLE001
            continue
        for d in b.get("duzeltmeler") or []:
            if isinstance(d, dict) and (d.get("gonderi") or d.get("gonderi_metni")):
                out.append({**d, "kaynak": f"bulten:{p.stem}"})
    return out


_FM = re.compile(r"^---\r?\n(.*?)\r?\n---", re.S)
_OGE = re.compile(r"^(\s*)-\s+([A-Za-z_]\w*):\s*(.*)$")
_ALAN = re.compile(r"^(\s+)([A-Za-z_]\w*):\s*(.*)$")


def on_bilgi_duzeltmeleri(metin: str) -> list[dict]:
    """Analiz ön bilgisindeki `duzeltmeler:` listesi (ortak/on_bilgi yalnız tek
    satırlık skaler okur). Biçim, depodaki yazıların kullandığı kadardır:
    `  - alan: '…'` ile açılan öğe, `    alan: '…'` ile süren alanlar; değerler
    on_bilgi.deger ile çözülür (tek tanım: tırnak ve '' kaçışı)."""
    m = _FM.match(metin)
    if not m:
        return []
    out: list[dict] = []
    icinde = False
    for satir in m.group(1).splitlines():
        if not icinde:
            if re.match(r"^duzeltmeler:\s*$", satir):
                icinde = True
            continue
        if satir and not satir[0].isspace():
            break                                              # liste bitti
        o = _OGE.match(satir)
        if o:
            out.append({o.group(2): analiz_m._on_bilgi.deger(o.group(3))})
            continue
        a = _ALAN.match(satir)
        if a and out:
            out[-1][a.group(2)] = analiz_m._on_bilgi.deger(a.group(3))
    return out


def _analiz_kayitlari(bugun: dt.date, dizin: Path) -> list[dict]:
    out = []
    if not dizin.exists():
        return out
    for y in sorted(dizin.glob("*.mdx")):
        for d in on_bilgi_duzeltmeleri(y.read_text(encoding="utf-8")):
            if not (d.get("gonderi") or d.get("gonderi_metni")):
                continue
            try:
                gun = dt.date.fromisoformat(str(d.get("tarih") or "")[:10])
            except ValueError:
                continue
            if bugun - dt.timedelta(days=PENCERE_GUN) <= gun <= bugun:
                out.append({**d, "kaynak": f"analiz:{y.stem}"})
    return out


def adaylar(bugun: dt.date, defter: dict, bulten_dizin: Path | None = None,
            analiz_dizin: Path | None = None) -> tuple[list[dict], list[str]]:
    """(gönderilecek düzeltmeler, uyarılar). Dizinler çağrı anında okunur
    (uret.BULTENLER, analiz.ANALIZ_DIZIN) — duman fikstürü onları yamar.

    Her aday: {anahtar, hedef, ust, metin_ham, eski, yeni, kaynak}. Defterde
    olan anahtar atlanır; hedefi kimliksiz kayıt GÖNDERİLMEZ ve adıyla uyarılır
    (yazma kapısı bunu zaten reddeder; analiz ön bilgisi o kapıdan geçmez)."""
    bd = bulten_dizin or uret.BULTENLER
    ad = analiz_dizin or analiz_m.ANALIZ_DIZIN
    kayitlar = _bulten_kayitlari(bugun, bd) + _analiz_kayitlari(bugun, ad)
    secilen: dict[str, dict] = {}
    uyari: list[str] = []
    for d in kayitlar:
        hedef = str(d.get("gonderi") or "").strip()
        govde = str(d.get("gonderi_metni") or "").strip()
        if not hedef or not govde:
            uyari.append(f"{d['kaynak']}: düzeltme kaydında gonderi ve gonderi_metni birlikte "
                         "yazılır — biri eksik, X'e gitmedi")
            continue
        if not HEDEF_RE.match(hedef):
            uyari.append(f"{d['kaynak']}: düzeltme hedefi bir defter anahtarı değil ({hedef!r})")
            continue
        ust = kimlikli(defter, hedef)
        if not ust:
            uyari.append(f"{d['kaynak']}: düzeltme hedefi {hedef} defterde kimliksiz — yanıt atılamaz")
            continue
        k = anahtar(hedef, str(d.get("eski") or ""), str(d.get("yeni") or ""))
        if k in defter or k in secilen:
            continue
        secilen[k] = {"anahtar": k, "hedef": hedef, "ust": ust, "metin_ham": govde,
                      "eski": d.get("eski"), "yeni": d.get("yeni"), "kaynak": d["kaynak"]}
    return list(secilen.values()), uyari


# ── metin ────────────────────────────────────────────────────────────────────

def hedef_basligi(hedef: str, arsiv: Path | None = None) -> str:
    """Hedef gönderinin başlığı ve tarihi: arşivdeki gönderilmiş metnin ilk
    satırından ("Haftaya Bakış — 4 Ekim 2026" → "Haftaya Bakış, 4 Ekim 2026";
    analizde başlık satırı da eklenir). Arşiv yoksa anahtardan kurulur."""
    yol = (arsiv or ARSIV) / (hedef.replace(":", "-") + ".txt")
    if yol.exists():
        govde = yol.read_text(encoding="utf-8").split("\n", 2)
        satirlar = [s.strip() for s in (govde[2] if len(govde) > 2 else "").split("\n") if s.strip()]
        if satirlar:
            bas = satirlar[0].replace(" — ", ", ", 1)
            if hedef.startswith("analiz:") and len(satirlar) > 1:
                bas += ": " + satirlar[1].split(" — ")[0].strip()
            return bas
    tur, ad = hedef.split(":", 1)
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", ad)
    tarih = (f"{int(m.group(3))} {AYLAR[int(m.group(2))]} {m.group(1)}" if m else "")
    if tur == "bulten" and m:
        gun = dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return f"{'Haftaya Bakış' if gun.weekday() == 6 else 'Sabah Notu'}, {tarih}"
    return f"{'Analiz' if tur == 'analiz' else tur.capitalize()}{', ' + tarih if tarih else ''}"


def metin(aday: dict, arsiv: Path | None = None) -> str:
    """'Düzeltme — <hedef başlığı>' + yazarın metni + sorumluluk notu."""
    govde = uret._tipografi(re.sub(r"\s+", " ", aday["metin_ham"]).strip())
    not_ = uret.SORUMLULUK_TEKNIK if aday["hedef"].startswith("analiz:") else uret.SORUMLULUK_BULTEN
    return f"Düzeltme — {hedef_basligi(aday['hedef'], arsiv)}\n\n{govde}\n\n{not_}"


if __name__ == "__main__":                                     # kuru döküm
    import gonder
    bugun = dt.datetime.now(dt.timezone.utc).date()
    a, u = adaylar(bugun, gonder._defter_oku(gonder.DEFTER))
    for x in u:
        print("!", x)
    for x in a:
        print(f"── {x['anahtar']} → yanıt {x['ust']}\n{metin(x)}\n")
    if not a:
        print("gönderilecek düzeltme yok")
