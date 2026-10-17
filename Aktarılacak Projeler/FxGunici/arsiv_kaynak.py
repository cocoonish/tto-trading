#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dokuzuncu dersin atıf kaynakları (bulut koşucusu): künye, özet ve tam metinden kısa pasajlar.

Neden gerekli: dersin literatür cümleleri bu oturumun araştırma ajanlarınca arama motoru alıntılarından okundu ve 35
kaynağın 19'unda arama bütçesi dolduğu için hiç okunamadı. Kural: bir atıf, kaynağın kendi metninde görülmeden
yayımlanmaz. Bu betik her kaynağı bulutta çözer ve ne bulduysa olduğu gibi saklar; cümlenin kaynakta geçip geçmediği
yerelde sorulur (veri/kaynak/kaynaklar.json, dogrula.py).

Çözüm sırası (serbest metin araması YAPILMAZ; adres tahmin edilmez, kimlikten çözülür):
  1. DOI adayları (aday.json) Crossref'te çözülür; başlık adayla tutmazsa sıradakine geçilir.
  2. DOI yoksa künye koordinatı (dergi ISSN'i, cilt, ilk sayfa) OpenAlex kataloğunda süzgeçle aranır.
  3. Künyesi çözülen eserin özeti: Crossref (JATS), OpenAlex (ters dizin) ve Semantic Scholar; üçü ayrı saklanır.
  4. Açık erişimli metin: aday.json'daki adresler ile OpenAlex ve Semantic Scholar'ın açık erişim adresleri, sırayla.
     İlk okunabilen metinde aday ifadeler aranır; bulunan her ifadenin çevresi (±240 karakter) sayfa numarasıyla
     saklanır. Tam metin depoya YAZILMAZ (yayımlanmış eserin kendisi): yalnız indirilen dosyanın SHA-256 özü, boyutu,
     sayfa sayısı ve ilk sayfanın başı (künyenin kimliği için).

Çıktı: veri/kaynak/<id>.json (kaynak başına), veri/kaynak/kunye.json (koşunun özeti), veri/kaynak/ozler.json (dizinin
özleri; okuyucu okumadan önce sınar). Var olan ve metni okunmuş kaynak yeniden indirilmez (TTO_PARCA=yenile hepsini
yeniler; "yenile <id> <id>…" yalnız adı verilenleri).
"""
from __future__ import annotations

import hashlib
import html
import io
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

import ozler
from atif import normal  # eşleme biçiminin tek tanımı (kapı da onu kullanır)

BURASI = Path(__file__).resolve().parent
DIZIN = BURASI / "veri" / "kaynak"
ADAY = DIZIN / "aday.json"
BASLIK = {"User-Agent": "tto-trading-arastirma/1.0 (+https://cocoonish.github.io)",
          "Accept": "application/pdf,text/html,application/json;q=0.9,*/*;q=0.8"}
#: Koşunun bütçesi (iş akışının `timeout 21m`inden önce, kayıt yazmaya yer bırakarak).
BUTCE = 19 * 60
#: Bir indirmenin azami boyutu.
AZAMI_BAYT = 25 * 1024 * 1024
#: Pasajın ifadenin iki yanındaki karakter sayısı; ifade başına en çok iki geçiş.
PAY = 240
GECIS = 2
BASLANGIC = time.monotonic()


def kalan() -> float:
    return BUTCE - (time.monotonic() - BASLANGIC)


def _sade_baslik(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def baslik_tutar(a: str | None, b: str | None) -> bool:
    """Adayın başlığı ile katalogdaki başlık: sözcüklerin en az %70'i ortak (alt başlık ve noktalama farkı tolere)."""
    x, y = set(_sade_baslik(a).split()), set(_sade_baslik(b).split())
    x -= {"the", "a", "an", "of", "and", "in", "on", "for", "to", "at"}
    y -= {"the", "a", "an", "of", "and", "in", "on", "for", "to", "at"}
    if not x or not y:
        return False
    return len(x & y) / min(len(x), len(y)) >= 0.7


def al(url: str, sn: int = 45, json_: bool = False, deneme=(0, 4, 12)):
    son = ""
    for bekle in deneme:
        if bekle:
            time.sleep(bekle)
        try:
            r = requests.get(url, headers=BASLIK, timeout=(15, sn), stream=True, allow_redirects=True)
            govde = b""
            for parca in r.iter_content(1 << 16):
                govde += parca
                if len(govde) > AZAMI_BAYT:
                    return {"durum": "boyut sınırı", "url": url}
        except requests.RequestException as e:
            son = type(e).__name__
            continue
        if r.status_code in (200, 203):          # 203: vekil ya da önbellek üzerinden gelen tam yanıt
            out = {"durum": 200, "url": url, "son_url": r.url, "tur": r.headers.get("content-type", ""), "govde": govde}
            if json_:
                try:
                    out["json"] = json.loads(govde.decode("utf-8"))
                except ValueError:
                    return {"durum": "json değil", "url": url}
            return out
        son = f"HTTP {r.status_code}"
        if r.status_code in (400, 401, 403, 404, 410, 451):
            break
    return {"durum": son, "url": url}


# ───────────────────────────────────────────── künye
def _jats(s: str | None) -> str | None:
    if not s:
        return None
    return normal(html.unescape(re.sub(r"<[^>]+>", " ", s)))


def crossref(doi: str) -> dict | None:
    r = al("https://api.crossref.org/works/" + requests.utils.quote(doi, safe="/()"), json_=True)
    if r.get("durum") != 200:
        return {"durum": r.get("durum"), "doi": doi}
    m = r["json"].get("message", {})
    yil = None
    for alan in ("published-print", "published-online", "issued"):
        dp = (m.get(alan) or {}).get("date-parts") or [[None]]
        if dp[0] and dp[0][0]:
            yil = dp[0][0]
            break
    return {"durum": 200, "doi": m.get("DOI"), "baslik": " ".join(m.get("title") or []),
            "alt_baslik": " ".join(m.get("subtitle") or []),
            "yazarlar": [{"soyad": a.get("family"), "ad": a.get("given"), "ad_tam": a.get("name")}
                         for a in m.get("author") or []],
            "dergi": " ".join(m.get("container-title") or []), "cilt": m.get("volume"), "sayi": m.get("issue"),
            "sayfa": m.get("page"), "yil": yil, "tur": m.get("type"), "yayinci": m.get("publisher"),
            "ozet": _jats(m.get("abstract")), "url": m.get("URL"),
            "bag": [x.get("URL") for x in m.get("link") or [] if x.get("URL")][:6]}


def _ters_dizin(d: dict | None) -> str | None:
    if not d:
        return None
    yer = {}
    for sozcuk, konum in d.items():
        for k in konum:
            yer[k] = sozcuk
    return normal(" ".join(yer[k] for k in sorted(yer)))


def _openalex_kayit(w: dict) -> dict:
    b = w.get("biblio") or {}
    loc = []
    for x in [w.get("best_oa_location") or {}] + (w.get("locations") or []):
        for alan in ("pdf_url", "landing_page_url"):
            u = (x or {}).get(alan)
            if u and u not in loc:
                loc.append(u)
    kaynak = ((w.get("primary_location") or {}).get("source") or {})
    return {"durum": 200, "id": w.get("id"), "doi": (w.get("doi") or "").replace("https://doi.org/", "") or None,
            "baslik": w.get("title"), "yil": w.get("publication_year"),
            "yazarlar": [(a.get("author") or {}).get("display_name") for a in w.get("authorships") or []],
            "dergi": kaynak.get("display_name"), "issn": kaynak.get("issn"), "cilt": b.get("volume"),
            "sayi": b.get("issue"), "ilk_sayfa": b.get("first_page"), "son_sayfa": b.get("last_page"),
            "ozet": _ters_dizin(w.get("abstract_inverted_index")),
            "acik": (w.get("open_access") or {}).get("oa_url"), "adresler": loc[:10]}


def openalex_doi(doi: str) -> dict | None:
    r = al("https://api.openalex.org/works/doi:" + requests.utils.quote(doi, safe="/()"), json_=True)
    if r.get("durum") != 200:
        return {"durum": r.get("durum")}
    return _openalex_kayit(r["json"])


def openalex_koordinat(issn: str, cilt: str, ilk: str, sayi: str = "") -> list[dict]:
    """Künye koordinatıyla katalog süzgeci (serbest metin değil): dergi ISSN'i, cilt, sayı ve ilk sayfa. Sayfa
    verilmezse o cildin (sayının) bütün eserleri listelenir ve başlık yerelde eşlenir."""
    f = [f"primary_location.source.issn:{issn}"]
    if cilt:
        f.append(f"biblio.volume:{cilt}")
    if sayi:
        f.append(f"biblio.issue:{sayi}")
    if ilk:
        f.append(f"biblio.first_page:{ilk}")
    r = al("https://api.openalex.org/works?per-page=100&filter=" + ",".join(f), json_=True)
    if r.get("durum") != 200:
        return [{"durum": r.get("durum"), "koordinat": [issn, cilt, ilk, sayi]}]
    return [_openalex_kayit(w) for w in r["json"].get("results") or []]


def semantic(doi: str) -> dict | None:
    alan = "title,abstract,year,venue,openAccessPdf,externalIds,authors"
    r = al(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{requests.utils.quote(doi, safe='/()')}?fields={alan}",
           json_=True, deneme=(0, 5, 20))
    if r.get("durum") != 200:
        return {"durum": r.get("durum")}
    j = r["json"]
    return {"durum": 200, "baslik": j.get("title"), "yil": j.get("year"), "dergi": j.get("venue"),
            "ozet": normal(j["abstract"]) if j.get("abstract") else None,
            "acik": (j.get("openAccessPdf") or {}).get("url"),
            "yazarlar": [a.get("name") for a in j.get("authors") or []]}


# ───────────────────────────────────────────── tam metin
class _Metin(HTMLParser):
    ATLA = {"script", "style", "noscript", "svg", "head", "nav", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parca: list[str] = []
        self.derin = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.ATLA:
            self.derin += 1
        elif tag in ("p", "br", "div", "li", "tr", "h1", "h2", "h3", "h4", "td", "th", "section", "article"):
            self.parca.append("\n")

    def handle_endtag(self, tag):
        if tag in self.ATLA and self.derin:
            self.derin -= 1

    def handle_data(self, data):
        if not self.derin:
            self.parca.append(data)


def sayfalar(govde: bytes, tur: str) -> list[str] | None:
    """Belgenin sayfa sayfa metni (HTML tek sayfa). Okunamazsa None."""
    if govde[:5] == b"%PDF-":
        try:
            from pypdf import PdfReader
        except ImportError:
            return None
        try:
            okuyucu = PdfReader(io.BytesIO(govde))
            return [(p.extract_text() or "") for p in okuyucu.pages]
        except Exception:  # noqa: BLE001 — bozuk ya da şifreli PDF okunamaz sayılır
            return None
    if "html" in tur.lower() or govde.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")):
        m = re.search(rb"charset=[\"']?([A-Za-z0-9_\-]+)", govde[:4000])
        try:
            metin = govde.decode(m.group(1).decode() if m else "utf-8", errors="replace")
        except LookupError:
            metin = govde.decode("utf-8", errors="replace")
        p = _Metin()
        p.feed(metin)
        return ["".join(p.parca)]
    return None


def pasajlar(sayfa: list[str], ifadeler: list[str]) -> tuple[list[dict], list[str]]:
    bulunan, eksik = [], []
    norm = [normal(s) for s in sayfa]
    kucuk = [s.lower() for s in norm]
    for ifade in ifadeler:
        hedef = normal(ifade).lower()
        say = 0
        for no, (s, k) in enumerate(zip(norm, kucuk), start=1):
            i = k.find(hedef)
            while i >= 0 and say < GECIS:
                bulunan.append({"ifade": ifade, "sayfa": no,
                                "pasaj": s[max(0, i - PAY): i + len(hedef) + PAY]})
                say += 1
                i = k.find(hedef, i + len(hedef))
            if say >= GECIS:
                break
        if not say:
            eksik.append(ifade)
    return bulunan, eksik


def metin_getir(adresler: list[str], baslik: str | None, ifadeler: list[str]) -> dict:
    """Adresleri sırayla dener; başlığı ilk iki sayfada geçen ilk okunabilir belgeyi kullanır."""
    deneme = []
    for url in adresler:
        if kalan() < 60:
            deneme.append({"url": url, "durum": "bütçe doldu"})
            break
        r = al(url, sn=60, deneme=(0, 5))
        if r.get("durum") != 200:
            deneme.append({"url": url, "durum": r.get("durum")})
            continue
        sy = sayfalar(r["govde"], r.get("tur", ""))
        if not sy or not any(len(s.strip()) > 200 for s in sy):
            deneme.append({"url": url, "durum": "metin okunamadı", "tur": r.get("tur")})
            continue
        bas = normal(" ".join(sy[:2]))
        kimlik = bool(baslik) and baslik_tutar(baslik, bas[:6000]) or \
            (bool(baslik) and _sade_baslik(baslik)[:40] in _sade_baslik(bas[:8000]))
        if not kimlik:
            deneme.append({"url": url, "durum": "başlık ilk iki sayfada yok", "ilk": bas[:300]})
            continue
        bul, eksik = pasajlar(sy, ifadeler)
        deneme.append({"url": url, "durum": 200})
        return {"durum": 200, "url": url, "son_url": r.get("son_url"), "tur": r.get("tur"),
                "sha256": hashlib.sha256(r["govde"]).hexdigest(), "bayt": len(r["govde"]),
                "sayfa": len(sy), "ilk_sayfa": normal(sy[0])[:1500], "pasaj": bul, "eksik": eksik,
                "deneme": deneme}
    return {"durum": "okunamadı", "deneme": deneme}


# ───────────────────────────────────────────── kaynak başına
def kaynak(a: dict) -> dict:
    out = {"id": a["id"], "aday_baslik": a.get("baslik"), "aday_yil": a.get("yil"),
           "zaman": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    cr, oa, doi = None, None, None
    for d in a.get("doi_aday") or []:
        c = crossref(d)
        out.setdefault("crossref_deneme", []).append({"doi": d, "durum": c.get("durum"), "baslik": c.get("baslik")})
        if c.get("durum") == 200 and (baslik_tutar(a.get("baslik"), c.get("baslik"))
                                      or baslik_tutar(a.get("baslik"), f"{c.get('baslik')} {c.get('alt_baslik')}")):
            cr, doi = c, c.get("doi") or d
            break
        time.sleep(0.3)
    if doi:
        oa = openalex_doi(doi)
    else:
        for koor in a.get("koordinat") or []:
            issn, cilt, ilk = koor[:3]
            sayi = koor[3] if len(koor) > 3 else ""
            adaylar = openalex_koordinat(issn, cilt, ilk, sayi)
            out.setdefault("koordinat_deneme", []).append(
                {"koordinat": koor, "bulunan": [(x.get("baslik"), x.get("doi")) for x in adaylar][:12]})
            tut = [x for x in adaylar if x.get("durum") == 200 and baslik_tutar(a.get("baslik"), x.get("baslik"))]
            if tut:
                oa = tut[0]
                doi = oa.get("doi")
                if doi:
                    c = crossref(doi)
                    if c.get("durum") == 200:
                        cr = c
                break
            time.sleep(0.3)
    out["crossref"], out["openalex"] = cr, oa
    out["semantic"] = semantic(doi) if doi else None
    adres = list(a.get("url") or [])
    for x in (oa or {}).get("adresler") or []:
        if x not in adres:
            adres.append(x)
    for x in ((out["semantic"] or {}).get("acik"), (oa or {}).get("acik")):
        if x and x not in adres:
            adres.append(x)
    baslik = (cr or {}).get("baslik") or (oa or {}).get("baslik") or a.get("baslik")
    out["metin"] = metin_getir(adres, baslik, a.get("ifade") or [])
    out["kunye_cozuldu"] = bool(cr or oa)
    out["ozet_var"] = bool((cr or {}).get("ozet") or (oa or {}).get("ozet") or (out["semantic"] or {}).get("ozet"))
    return out


def main() -> int:
    DIZIN.mkdir(parents=True, exist_ok=True)
    aday = json.loads(ADAY.read_text(encoding="utf-8"))["kaynak"]
    parca = os.environ.get("TTO_PARCA", "").split()
    yenile = set(parca[1:]) if parca[:1] == ["yenile"] else set()       # "yenile a b" → yalnız a ve b yeniden
    hepsi = parca == ["yenile"]
    ozet = {"zaman": datetime.now(timezone.utc).isoformat(timespec="seconds"), "kaynak": {}}
    for a in aday:
        yol = DIZIN / f"{a['id']}.json"
        if yol.exists() and not hepsi and a["id"] not in yenile:
            eski = json.loads(yol.read_text(encoding="utf-8"))
            if (eski.get("metin") or {}).get("durum") == 200 and eski.get("kunye_cozuldu"):
                ozet["kaynak"][a["id"]] = {"durum": "var"}
                continue
        if kalan() < 90:
            ozet["kaynak"][a["id"]] = {"durum": "bütçe doldu"}
            continue
        try:
            k = kaynak(a)
        except Exception as e:  # noqa: BLE001 — bir kaynağın kusuru öbürlerini götürmez; adıyla yazılır
            ozet["kaynak"][a["id"]] = {"durum": f"hata {type(e).__name__}: {e}"[:200]}
            print(a["id"], ozet["kaynak"][a["id"]], flush=True)
            continue
        yol.write_text(json.dumps(k, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        m = k["metin"]
        ozet["kaynak"][a["id"]] = {"kunye": k["kunye_cozuldu"], "ozet": k["ozet_var"], "metin": m.get("durum"),
                                   "pasaj": len(m.get("pasaj") or []), "eksik": len(m.get("eksik") or [])}
        print(f"{a['id']:24} künye={k['kunye_cozuldu']!s:5} özet={k['ozet_var']!s:5} metin={m.get('durum')} "
              f"pasaj={len(m.get('pasaj') or [])} eksik={len(m.get('eksik') or [])} · {kalan():.0f} sn", flush=True)
        time.sleep(1.0)
    (DIZIN / "kunye.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                      encoding="utf-8")
    ozler.yaz(DIZIN)
    cozulen = sum(1 for v in ozet["kaynak"].values() if v.get("kunye") or v.get("durum") == "var")
    print(f"künyesi çözülen {cozulen}/{len(aday)}", flush=True)
    return 0 if cozulen else 1


if __name__ == "__main__":
    sys.exit(main())
