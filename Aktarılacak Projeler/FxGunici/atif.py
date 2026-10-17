#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Serinin literatür atıfları: tanım, kayıt ve kapı (yalnız standart kütüphane; dogrula.py ve ders_motor.py okur).

Bir atıf, kaynağın kendi metninde görülmeden yayımlanmaz. Kaynağın künyesi, özeti ve tam metninden aranan ifadelerin
çevresi bulutta dondurulur (arsiv_kaynak.py → veri/kaynak/<id>.json, özleri veri/kaynak/ozler.json). Hangi cümlenin
hangi kaynağa dayandığı ve kaynağın o cümleyi taşıyan kendi ifadesi elle yazılır (veri/kaynaklar.json). Kapı:

  1. Dondurulmuş dizin kayıtlı özleriyle aynıdır (değişmiş, eksik ya da kayıtsız dosya yok).
  2. Derslerin metnindeki her atıf (anlatı "Evans (2018)" ve parantez "(Holm, 1979)" biçimi, aynı parantezde ";" ile
     birden çok) bir kayda karşılık gelir; kaydın durumu "dogrulandi" ya da "kismen"dir ve kayıt o dersi adıyla anar.
     Bir kaydın andığı ders o atfı taşımıyorsa da düşer (kaynakça listesi sessizce şişmesin).
  3. Kaydın her alıntısı dondurulmuş kaynakta geçer (özet, ilk sayfa ya da pasajlardan birinde; biçim `normal`).
  4. Kaydın künyesi dondurulmuş künyeyle tutar: yıl, cilt, sayı ve sayfa aralığı (iki taraf da biliyorsa) ve başlığın
     sözcükleri. Bellekten yazılmış bir künye kayan ciltle ya da sayfayla düşer.
Kaynakça listesi kayıttan basılır (ders_motor `kaynaklar` bloğu): liste ile metin arasında elle tutulan ikinci bir
kopya yoktur.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KAYIT = BURASI / "veri" / "kaynaklar.json"
DONMUS = BURASI / "veri" / "kaynak"
DURUMLAR = ("dogrulandi", "kismen", "dogrulanamadi")


def normal(s: str) -> str:
    """Eşleme biçimi: NFKC, tipografik tırnak ve tire düz, yumuşak tire ve bağlı harfler çözülmüş, satır sonunda
    bölünmüş sözcük birleşik, boşluk tek. Bulut betiği (arsiv_kaynak) aynı fonksiyonu kullanır."""
    s = unicodedata.normalize("NFKC", s).replace("­", "")
    for a, b in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), ("−", "-"),
                 (" ", " "), ("ﬁ", "fi"), ("ﬂ", "fl")):
        s = s.replace(a, b)
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)
    return re.sub(r"\s+", " ", s).strip()


def sade(s: str | None) -> str:
    """Anahtar biçimi: küçük harf, aksansız, noktalama boşluk."""
    s = unicodedata.normalize("NFKD", (s or "").replace("İ", "I").replace("ı", "i").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ───────────────────────────────────────────── atıfın biçimi
_AD = r"[A-ZÇĞİÖŞÜ][\w'’\-]+(?: de [A-ZÇĞİÖŞÜ][\w'’\-]+)?"
_LISTE = rf"{_AD}(?:(?:, | ve ){_AD})*"
ANLATI = re.compile(rf"({_LISTE}) \((\d{{4}})[a-z]?\)")
PARANTEZ = re.compile(r"\(([^()]*?\d{4}[a-z]?)\)")
PARCA = re.compile(rf"^({_LISTE}), (\d{{4}})[a-z]?$")


def atiflar(metin: str) -> list[tuple[str, int]]:
    """Metindeki atıflar (yazar dizgesi, yıl), geçiş sırasıyla. Parantez içinde ";" ile ayrılmış her parça ayrıca;
    yılı olmayan parça (ör. "kazananın laneti") atıf değildir."""
    n = re.sub(r"\s+", " ", metin)
    out = [(m.group(1), int(m.group(2)), m.start()) for m in ANLATI.finditer(n)]
    for m in PARANTEZ.finditer(n):
        for parca in m.group(1).split(";"):
            p = PARCA.match(parca.strip())
            if p:
                out.append((p.group(1), int(p.group(2)), m.start()))
    return [(a, y) for a, y, _ in sorted(out, key=lambda x: x[2])]


def anahtar(yazarlar: str, yil: int) -> str:
    return f"{sade(yazarlar)}|{yil}"


# ───────────────────────────────────────────── künye
KUNYE = re.compile(r"^(?P<yazar>.+?) \((?P<yil>\d{4})\)\. (?P<geri>.+)$")
DERGI = re.compile(r"_(?P<dergi>[^_]+)_, (?P<cilt>\d+)(?:\((?P<sayi>[\w\-–]+)\))?, (?P<ilk>\d+)[–-](?P<son>\d+)\.?$")


def kunye_ayristir(satir: str) -> dict:
    m = KUNYE.match(satir.strip())
    if not m:
        return {}
    out = {"yazar": m.group("yazar"), "yil": int(m.group("yil"))}
    geri = m.group("geri")
    d = DERGI.search(geri)
    if d:
        out.update({k: d.group(k) for k in ("dergi", "cilt", "sayi", "ilk", "son")})
        out["baslik"] = geri[: d.start()].rstrip(" .")
    else:
        out["baslik"] = geri.split(". ")[0]
    return out


def _sozcukler(s: str | None) -> set[str]:
    return set(sade(s).split()) - {"the", "a", "an", "of", "and", "in", "on", "for", "to", "at", "ve"}


def baslik_tutar(a: str | None, b: str | None) -> bool:
    x, y = _sozcukler(a), _sozcukler(b)
    return bool(x and y) and len(x & y) / min(len(x), len(y)) >= 0.7


def _metinler(d: dict) -> list[str]:
    """Dondurulmuş kaydın alıntı aranabilen metinleri."""
    out = []
    for alan in ("crossref", "openalex", "semantic"):
        oz = (d.get(alan) or {}).get("ozet")
        if oz:
            out.append(oz)
    m = d.get("metin") or {}
    if m.get("ilk_sayfa"):
        out.append(m["ilk_sayfa"])
    out += [p["pasaj"] for p in m.get("pasaj") or []]
    return [normal(x).lower() for x in out]


def _sayfa(s: str | None) -> tuple[str | None, str | None]:
    if not s:
        return None, None
    p = re.split(r"[–-]", str(s))
    return p[0].strip() or None, (p[1].strip() if len(p) > 1 else None) or None


def kunye_denetimi(kayit: dict, d: dict) -> list[str]:
    """Kaydın künyesini dondurulmuş künyeyle karşılaştırır (Crossref önce, sonra OpenAlex)."""
    k = kunye_ayristir(kayit["kunye"])
    ad = kayit["id"]
    if not k:
        return [f"{ad}: künye biçimi okunamadı: {kayit['kunye'][:80]}"]
    cr, oa = d.get("crossref") or {}, d.get("openalex") or {}
    if not (cr or oa):
        return []                                 # kurum belgesi: künyesi adresinden (kayıt notunda)
    hata = []
    yil = cr.get("yil") or oa.get("yil")
    if yil and int(yil) != k["yil"]:
        hata.append(f"{ad}: künyenin yılı {k['yil']}, kaynağın {yil}")
    baslik = cr.get("baslik") or oa.get("baslik")
    tam = f"{baslik or ''} {cr.get('alt_baslik') or ''}"
    if baslik and not (baslik_tutar(k.get("baslik"), baslik) or baslik_tutar(k.get("baslik"), tam)):
        hata.append(f"{ad}: künyenin başlığı kaynağınkiyle tutmuyor ({baslik[:70]})")
    if "cilt" in k:
        cilt = cr.get("cilt") or oa.get("cilt")
        if cilt and str(cilt) != k["cilt"]:
            hata.append(f"{ad}: künyenin cildi {k['cilt']}, kaynağın {cilt}")
        sayi = cr.get("sayi") or oa.get("sayi")
        if k.get("sayi") and sayi and str(sayi) != k["sayi"]:
            hata.append(f"{ad}: künyenin sayısı {k['sayi']}, kaynağın {sayi}")
        ilk, son = _sayfa(cr.get("sayfa"))
        ilk = ilk or oa.get("ilk_sayfa")
        son = son or oa.get("son_sayfa")
        if ilk and str(ilk) != k["ilk"]:
            hata.append(f"{ad}: künyenin ilk sayfası {k['ilk']}, kaynağın {ilk}")
        if son and str(son) != k["son"]:
            hata.append(f"{ad}: künyenin son sayfası {k['son']}, kaynağın {son}")
    return hata


# ───────────────────────────────────────────── kayıt
def kayitlar(yol: Path = KAYIT) -> list[dict]:
    return json.loads(yol.read_text(encoding="utf-8"))["kaynak"]


def ders_kaynaklari(slug: str, yol: Path = KAYIT) -> list[dict]:
    """Bir dersin kaynakçası: kaydın andığı ve atfı doğrulanmış kayıtlar, künyenin alfabe sırasıyla."""
    return sorted((k for k in kayitlar(yol) if slug in k.get("ders", []) and k["durum"] in ("dogrulandi", "kismen")),
                  key=lambda k: sade(k["kunye"]))


def denetim(metinler: dict[str, str], yol: Path = KAYIT, donmus: Path = DONMUS) -> list[str]:
    """metinler: ders → üretilmiş MDX. Hata listesi (boşsa geçti)."""
    import ozler
    hata: list[str] = []
    if not yol.exists():
        return [f"atıf kaydı yok: {yol.name}"]
    hata += [f"dondurulmuş kaynak: {s}" for s in ozler.sorunlar(donmus)]
    kay = kayitlar(yol)
    dizin: dict[str, dict] = {}
    for k in kay:
        if k.get("durum") not in DURUMLAR:
            hata.append(f"{k.get('id')}: tanımsız durum {k.get('durum')!r}")
        a = anahtar(k["atif"], k["yil"])
        if a in dizin:
            hata.append(f"{k['id']}: aynı atıf iki kayıtta ({dizin[a]['id']})")
        dizin[a] = k
        dosya = donmus / f"{k['id']}.json"
        if k.get("durum") == "dogrulanamadi":
            continue
        if not dosya.exists():
            hata.append(f"{k['id']}: dondurulmuş kaynak yok ({dosya.name})")
            continue
        d = json.loads(dosya.read_text(encoding="utf-8"))
        if not k.get("alinti"):
            hata.append(f"{k['id']}: doğrulanmış kayıtta alıntı yok")
        metin = _metinler(d)
        for al in k.get("alinti") or []:
            hedef = normal(al).lower()
            if not any(hedef in m for m in metin):
                hata.append(f"{k['id']}: alıntı dondurulmuş kaynakta yok: {al[:70]!r}")
        hata += kunye_denetimi(k, d)
    for slug, mdx in metinler.items():
        govde = mdx.split("\n## Kaynaklar", 1)[0]
        anilan = set()
        for yazar, yil in atiflar(govde):
            k = dizin.get(anahtar(yazar, yil))
            if k is None:
                hata.append(f"{slug}: atıf kayıtta yok: {yazar} ({yil})")
                continue
            anilan.add(k["id"])
            if k["durum"] not in ("dogrulandi", "kismen"):
                hata.append(f"{slug}: atıf doğrulanmamış ({k['durum']}): {yazar} ({yil})")
            if slug not in k.get("ders", []):
                hata.append(f"{slug}: atıf kaydı bu dersi anmıyor: {k['id']}")
        for k in kay:
            if slug in k.get("ders", []) and k["id"] not in anilan:
                hata.append(f"{slug}: kayıt bu dersi anıyor ama metinde atfı yok: {k['id']}")
    return hata
