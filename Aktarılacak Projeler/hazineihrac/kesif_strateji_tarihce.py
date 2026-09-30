# -*- coding: utf-8 -*-
"""KEŞİF — bütün İç Borçlanma Stratejisi belgelerinin METİN ARŞİVİ.

Neden: hattın strateji defteri her ay için yalnız hedefi (ihale + kamuya
satış) ve borç servisini tutar. Bir stratejiyi tarihsel yerine oturtmak için
belgenin öbür satırları da gerekir — doğrudan satışlar (altın, döviz cinsi
senet, kira sertifikası), borçlanma dışı kaynaklar, iç borç servisinin
anapara/faiz ayrımı ve takvimin kendisi (hangi ayda bono, kuponsuz tahvil,
döviz cinsi senet var). Bu satırlar belgelerde duruyor ama depoda yok.

Betik HMB duyuru akışındaki bütün strateji belgelerini indirir, her birinin
pypdf metnini çıkarır ve metinlerin TAMAMINI tek bir sıkıştırılmış yük olarak
koşu kaydına basar (gzip + base64, parçalı). Yorum yapmaz, ayrıştırmaz, depoya
yazmaz: ayrıştırma yerelde, arşivlenmiş metin üzerinde yapılır — ayrıştırıcı
düzeltilirse kaynak yeniden indirilmez.

Her belge için künye: duyuru tarihi, başlık, PDF adresi, bayt, sha256,
sayfa sayısı. Yükün kendi sha256'sı da basılır; yerelde çözülen yük onunla
sınanır.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

API = "https://www.hmb.gov.tr/portal/v2/posts"
KOK = "https://www.hmb.gov.tr"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
KALIP = re.compile(r"i[çc]\s*bor[çc]lanma\s*stratejis", re.I)
SAYFA_TAVANI = 120
PARCA = 3000


def kur() -> None:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "pypdf", "beautifulsoup4"], check=True)


def getir(url: str, zaman: int = 60, deneme: int = 3) -> bytes:
    son = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=zaman) as r:
                return r.read()
        except Exception as ex:  # noqa: BLE001 — sebep adıyla basılır
            son = ex
            time.sleep(2 * (i + 1))
    raise son  # type: ignore[misc]


def sayfa(n: int, adet: int) -> list[dict]:
    q = {"page": n, "per_page": adet, "category_name": "kamu-finansmani"}
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


def duyurular() -> list[tuple[str, str, str]]:
    """(tarih, başlık, içerik) — en yeni önce, başlığa göre tekil."""
    adet = 100
    try:
        ilk = sayfa(1, adet)
    except Exception as ex:  # noqa: BLE001
        print(f"  per_page=100 düştü ({type(ex).__name__}) — 20'ye iniliyor")
        ilk = []
    if not ilk:
        adet, ilk = 20, sayfa(1, 20)
    print(f"  sayfa başı {adet} duyuru")
    bulunan, gorulen, bos = [], set(), 0
    kayitlar, n = ilk, 1
    while kayitlar and n <= SAYFA_TAVANI:
        yeni = 0
        for k in kayitlar:
            b = alan(k, "title", "baslik", "name")
            if KALIP.search(b) and b not in gorulen:
                gorulen.add(b)
                bulunan.append((alan(k, "date", "publishDate", "tarih")[:19], b,
                                alan(k, "content", "icerik")))
                yeni += 1
        son_tarih = alan(kayitlar[-1], "date", "publishDate", "tarih")[:10]
        print(f"  sayfa {n}: {len(kayitlar)} duyuru, {yeni} strateji "
              f"(son duyuru {son_tarih})")
        # 2019 Aralık öncesine inilince dur: defterin ilk belgesi o ay.
        if son_tarih and son_tarih < "2019-10-01":
            break
        n += 1
        try:
            kayitlar = sayfa(n, adet)
        except Exception as ex:  # noqa: BLE001
            print(f"  sayfa {n} düştü: {type(ex).__name__}: {str(ex)[:90]}")
            bos += 1
            if bos >= 3:
                break
            kayitlar = [{}]
            continue
    bulunan.sort(key=lambda x: x[0], reverse=True)
    return bulunan


def main() -> int:
    kur()
    from pypdf import PdfReader
    print("── Strateji duyuruları taranıyor")
    liste = duyurular()
    print(f"\n── {len(liste)} strateji duyurusu bulundu\n")
    arsiv: list[dict] = []
    for tarih, baslik, icerik in liste:
        url = pdf_adresi(icerik)
        kayit = {"duyuru": tarih, "baslik": baslik, "pdf": url}
        if not url:
            kayit["hata"] = "içerikte PDF bağlantısı yok"
        else:
            try:
                ham = getir(url, 90)
                kayit["bayt"] = len(ham)
                kayit["sha256"] = hashlib.sha256(ham).hexdigest()
                r = PdfReader(io.BytesIO(ham))
                kayit["sayfa"] = len(r.pages)
                kayit["metin"] = [p.extract_text() or "" for p in r.pages]
            except Exception as ex:  # noqa: BLE001
                kayit["hata"] = f"{type(ex).__name__}: {str(ex)[:160]}"
        arsiv.append(kayit)
        print(f"  {tarih[:10]}  {baslik[:60]:60}  "
              f"{kayit.get('bayt', '—'):>8}  {kayit.get('sayfa', '—')}  "
              f"{kayit.get('sha256', kayit.get('hata', ''))[:16]}")
    yuk = gzip.compress(json.dumps(arsiv, ensure_ascii=False).encode("utf-8"), 9)
    b64 = base64.b64encode(yuk).decode("ascii")
    print(f"\nYUK_SHA256 {hashlib.sha256(yuk).hexdigest()}")
    print(f"YUK_BAYT {len(yuk)}  PARCA {len(range(0, len(b64), PARCA))}")
    print("YUK_BASLA")
    for i in range(0, len(b64), PARCA):
        print(f"B64 {i // PARCA:04d} {b64[i:i + PARCA]}")
    print("YUK_BITTI")
    hata = sum(1 for k in arsiv if "hata" in k)
    print(f"\n{len(arsiv)} belge, {hata} hatalı")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
