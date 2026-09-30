# -*- coding: utf-8 -*-
"""KEŞİF — en son İç Borçlanma Stratejisi belgesinin TAM METNİ.

Neden ayrı bir betik: hattın tam kipi belgeden yalnız iki şey okur (aylık
hedef satırları ve ihraç takvimi). Bir strateji ANALİZİ ise belgenin tamamını
ister — iç borç servisi, kompozisyon ifadeleri, dipnotlar, takvimin yöntem
sütunu. Bu betik belgeyi bulut koşucusunda indirir ve metni olduğu gibi
basar; yorum yapmaz, hüküm kurmaz, depoya hiçbir şey yazmaz. Çıktısı ham
girdidir: analiz metni kendi arşivini bu dökümden kurar.

Kaç belge: en yeni iki strateji (yenisi ve bir öncekini aynı çıkarıcıyla
okumak, iki sürümün karşılaştırmasını aynı ayrıştırma hatalarına maruz
bırakır — biri pypdf, öbürü başka bir araçla okunsaydı fark araçtan
gelebilirdi).

Her belge için: PDF adresi, bayt sayısı, sha256, sayfa sayısı, sayfa sayfa
pypdf metni ve pdfplumber'ın düzen korumalı metni + tabloları.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request

API = "https://www.hmb.gov.tr/portal/v2/posts"
KOK = "https://www.hmb.gov.tr"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
KALIP = re.compile(r"i[çc]\s*bor[çc]lanma\s*stratejis", re.I)
BELGE_SAYISI = 2
SAYFA_TAVANI = 12


def kur() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "pypdf", "pdfplumber", "beautifulsoup4"], check=True)


def getir(url: str, zaman: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=zaman) as r:
        return r.read()


def sayfa(n: int, kategori: str | None) -> list[dict]:
    q = {"page": n, "per_page": 20}
    if kategori:
        q["category_name"] = kategori
    veri = json.loads(getir(f"{API}?{urllib.parse.urlencode(q)}", 45)
                      .decode("utf-8", "replace"))
    if isinstance(veri, dict):
        veri = veri.get("data") or veri.get("items") or veri.get("posts") or []
    return veri if isinstance(veri, list) else []


def alan(k: dict, *adlar: str) -> str:
    for a in adlar:
        v = k.get(a)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            for x in ("rendered", "tr", "title"):
                if isinstance(v.get(x), str) and v[x].strip():
                    return v[x].strip()
    return ""


def pdf_adresi(html: str) -> str | None:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")
    for a in soup.find_all("a", href=True):
        t = a.get_text().strip().lower()
        if "tıklayınız" in t or "tiklayiniz" in t:
            return urllib.parse.urljoin(KOK, a["href"])
    for a in soup.find_all("a", href=True):
        if ".pdf" in a["href"].lower():
            return urllib.parse.urljoin(KOK, a["href"])
    return None


def dok(baslik: str, tarih: str, url: str) -> None:
    import pdfplumber
    from pypdf import PdfReader
    ham = getir(url, 90)
    print(f"\n{'=' * 78}\nBELGE  {baslik}\nDUYURU {tarih}\nPDF    {url}")
    print(f"BAYT   {len(ham)}\nSHA256 {hashlib.sha256(ham).hexdigest()}")
    r = PdfReader(io.BytesIO(ham))
    print(f"SAYFA  {len(r.pages)}")
    for i, p in enumerate(r.pages, 1):
        print(f"\n--- pypdf · sayfa {i} ---")
        print(p.extract_text() or "")
    with pdfplumber.open(io.BytesIO(ham)) as pdf:
        for i, p in enumerate(pdf.pages, 1):
            print(f"\n--- pdfplumber düzen · sayfa {i} ---")
            print(p.extract_text(layout=True) or "")
            for j, tab in enumerate(p.extract_tables() or [], 1):
                print(f"\n--- pdfplumber tablo · sayfa {i} · tablo {j} ---")
                for satir in tab:
                    print(" | ".join("" if h is None else
                                     " ".join(str(h).split()) for h in satir))
    print(f"\nSON   {baslik}")


def main() -> int:
    kur()
    bulunan: list[tuple[str, str, str]] = []
    gorulen: set[str] = set()
    for kategori in ("kamu-finansmani", None):
        for n in range(1, SAYFA_TAVANI + 1):
            try:
                kayitlar = sayfa(n, kategori)
            except Exception as ex:
                print(f"  {kategori or 'hepsi'} · sayfa {n} düştü: "
                      f"{type(ex).__name__}: {str(ex)[:90]}")
                break
            if not kayitlar:
                break
            for k in kayitlar:
                b = alan(k, "title", "baslik", "name")
                if not KALIP.search(b) or b in gorulen:
                    continue
                gorulen.add(b)
                bulunan.append((alan(k, "date", "publishDate", "tarih")[:19], b,
                                alan(k, "content", "icerik")))
            if len(bulunan) >= BELGE_SAYISI + 2:
                break
        if len(bulunan) >= BELGE_SAYISI:
            break
    bulunan.sort(key=lambda x: x[0], reverse=True)
    print("── Strateji duyuruları (en yeni önce)")
    for t, b, _ in bulunan:
        print(f"  {t}  {b[:110]}")
    for t, b, icerik in bulunan[:BELGE_SAYISI]:
        url = pdf_adresi(icerik)
        if not url:
            print(f"\n  {b}: içerikte PDF bağlantısı yok · içerik başı: "
                  f"{re.sub(r'<[^>]+>', ' ', icerik)[:300]}")
            continue
        try:
            dok(b, t, url)
        except Exception as ex:
            print(f"\n  {b}: indirilemedi/okunamadı: {type(ex).__name__}: {ex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
