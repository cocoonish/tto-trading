#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — beşinci arşiv geçişi: yazının ATIF verdiği kaynak sayfaları.

Neden gerekli: yazıdaki kurum kuralları (TCMB'nin "Brent'te %10 → TÜFE'de 1 puan" ve
"10 dolar → cari açığa 2,6 milyar dolar" kuralları, IMF'nin %10 → küresel enflasyonda 40
baz puan kuralı, ECB/OECD senaryoları …) bu oturumun araştırma ajanlarınca YALNIZ arama
motoru alıntısından okunabildi; bu oturumların koşucusu sayfalara çıkamıyor. Arama
özetleri ölçülerek güvenilmez bulundu (bir özet USD/TRY'yi 34,85 yazıyordu, gerçek
48,46). Kural: bir alıntı, kaynağın kendi metninde görülmeden yayımlanmaz. Bu betik
sayfaları bulutta İNDİRİR ve olduğu gibi saklar; alıntının metinde geçip geçmediği yerelde
`dogrula.py` ile sorulur.

Resmî Gazete: akaryakıt ÖTV tutarlarını belirleyen kararlar. 01.10.2026'da 11822 sayılı
"Bazı Mallara Uygulanan Özel Tüketim Vergisi Tutarlarının Yeniden Belirlenmesi Hakkında
Karar" yayımlandı (başlık bültenin RG kaydında); motorinde eşel mobilin bitip kademeli
takvimin başladığı karar Ağustos ortasında (bültenin 02.09 metni: "13 Ağustos'ta sona
erdi"). Günün fihristi indirilir, adında "Özel Tüketim Vergisi" geçen bağlantılar izlenir —
karar adresi TAHMİN EDİLMEZ, fihristten çözülür.

Liste `kaynak_url.json` (araştırma iddialarının kaynak adresleri; depoda zaten birincil
arşivi duranlar — EIA ve Dünya Bankası dosyaları, TCMB PPK metinleri — listede yok).
Yardımcılar ve ilkeler `arsiv_brent.py` başlığında; künye `kunye_kaynak.json`.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.parse

import arsiv_brent as ab

LISTE = ab.BURASI / "kaynak_url.json"
RG_GUNLER = ["20261001", "20260812", "20260813", "20260814"]
RG_KOK = "https://www.resmigazete.gov.tr/eskiler"


def _ad(url: str) -> str:
    oz = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    alan = urllib.parse.urlparse(url).netloc.replace("www.", "")
    return f"{ab._dosya_adi(alan)[:30]}_{oz}"


def _uzanti(govde: bytes, url: str) -> str:
    if govde[:5] == b"%PDF-":
        return "pdf"
    if url.lower().endswith((".xls", ".xlsx")):
        return url.rsplit(".", 1)[-1].lower()
    return "html"


@ab.kaynak("Kaynak sayfaları")
def sayfalar() -> dict:
    sonuc = {}
    for url in json.loads(LISTE.read_text(encoding="utf-8")):
        if ab.kalan() < 90:
            sonuc[url] = "bütçe doldu"
            continue
        try:
            d, gv = ab.al(url, sn=45, baslik={"Accept": "text/html,application/pdf,*/*;q=0.8",
                                              "Accept-Language": "tr,en;q=0.8"})
        except RuntimeError as e:
            sonuc[url] = f"hata {e}"[:140]
            print(f"   ! {url[:90]}: {sonuc[url]}", flush=True)
            continue
        if d == 200 and gv:
            yol = f"kaynak/{_ad(url)}.{_uzanti(gv, url)}.gz"
            ab.yaz(yol, gv, url, d, not_="atıf kaynağı")
            sonuc[url] = {"durum": d, "bayt": len(gv), "dosya": yol}
        else:
            sonuc[url] = {"durum": d, "bayt": len(gv)}
        print(f"   {d} {len(gv):>8} {url[:100]}", flush=True)
        time.sleep(0.5)
    return sonuc


@ab.kaynak("Resmî Gazete ÖTV kararları")
def resmi_gazete() -> dict:
    sonuc = {}
    for gun in RG_GUNLER:
        fihrist = f"{RG_KOK}/{gun[:4]}/{gun[4:6]}/{gun}.htm"
        try:
            d, gv = ab.al(fihrist, sn=40)
        except RuntimeError as e:
            sonuc[gun] = f"hata {e}"[:140]
            continue
        if d != 200:
            sonuc[gun] = {"durum": d}
            continue
        ab.yaz(f"resmigazete/{gun}_fihrist.html.gz", gv, fihrist, d, not_="RG fihristi")
        metin = gv.decode("utf-8", errors="replace")
        baglar = []
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', metin, flags=re.S | re.I):
            yazi = re.sub(r"<[^>]+>", " ", m.group(2))
            yazi = re.sub(r"\s+", " ", yazi).strip()
            if "Özel Tüketim Vergisi" in yazi or "ÖZEL TÜKETİM VERGİSİ" in yazi.upper():
                baglar.append((urllib.parse.urljoin(fihrist, m.group(1)), yazi))
        kayit = {"durum": d, "bag": []}
        for u, yazi in baglar:
            try:
                d2, g2 = ab.al(u, sn=40)
            except RuntimeError as e:
                kayit["bag"].append({"url": u, "yazi": yazi, "hata": str(e)[:120]})
                continue
            if d2 == 200 and g2:
                yol = f"resmigazete/{gun}_{_ad(u)}.{_uzanti(g2, u)}.gz"
                ab.yaz(yol, g2, u, d2, not_=yazi[:160])
            kayit["bag"].append({"url": u, "yazi": yazi, "durum": d2, "bayt": len(g2)})
            time.sleep(0.5)
        sonuc[gun] = kayit
        print(f"   RG {gun}: {len(baglar)} ÖTV bağlantısı", flush=True)
    return sonuc


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    resmi_gazete()
    sayfalar()
    ab.kaydet("kaynak")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
