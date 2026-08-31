# -*- coding: utf-8 -*-
"""KEŞİF — yürürlükteki İç Borçlanma Stratejisi'nin AY BAZINDA ne yazdığı.

Neden: 31.08.2026'da inen "Eylül – Kasım 2026" stratejisinde Kasım hedefi
85,4 milyar TL çıktı — Eylül'ün (261,9) ve Ekim'in (229,1) üçte biri. Bir
dokümanın üçüncü ayı tarihsel olarak bu kadar küçük gelmiyordu (Ekim ilk kez
235,1, Eylül 294,2, Ağustos 355,8 olarak girmişti). Sayı ya gerçek (Kasım'da
itfa az) ya da ayrıştırma kusuru; ikisi de sayfaya YAZILMADAN ÖNCE bilinmeli.

Bu betik hiçbir şey yazmaz, ayrıştırma MANTIĞINI de tekrarlamaz: PDF'in
finansman programı tablosunun HAM SATIRLARINI basar. Sayı satırda ne yazıyorsa
okur onu görür — araya bir yorum katmanı girmez.

Kullanım:
    python kesif_hedef.py [pdf_url]
URL verilmezse .processed_urls.json'daki EN YENİ strateji PDF'i seçilir.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")
STRAT = re.compile(r"Ic-Borclanma-Stratejisi|İç-Borçlanma-Stratejisi", re.I)
# Finansman programı tablosunun ilgilendiğimiz satırları. Hedef =
# "Piyasadan İhale Yoluyla İç Borçlanma" + "Kamuya Satışlar" (bkz. main.py).
SATIRLAR = ("Piyasadan İhale Yoluyla İç Borçlanma", "Kamuya Satışlar",
            "Doğrudan Satışlar", "İç Borçlanma", "Toplam", "İtfa", "Borç Servisi")
SAYI = re.compile(r"-?\d[\d.,]*")


def en_yeni_url() -> str | None:
    yol = os.path.join(BASE, ".processed_urls.json")
    if not os.path.exists(yol):
        return None
    adaylar = [u for u in set(re.findall(r"https?://[^\"\s,]+",
                                         json.dumps(json.load(open(yol, encoding="utf-8")),
                                                    ensure_ascii=False)))
               if STRAT.search(u)]
    # uploads/YYYY/AA/ yolundaki tarihe göre sırala — dosya adı biçimi değişse de tutar
    def anahtar(u: str):
        m = re.search(r"/uploads/(\d{4})/(\d{2})/", u)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    return max(adaylar, key=anahtar) if adaylar else None


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else en_yeni_url()
    if not url:
        print("PDF adresi yok: argüman verilmedi ve .processed_urls.json'da strateji bulunamadı.")
        return 2
    print(f"── PDF: {url}\n")
    try:
        import PyPDF2
    except ImportError:
        print("PyPDF2 yok — iş akışına 'paketler: PyPDF2' geçin.")
        return 2
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ham = r.read()
    print(f"  indirildi: {len(ham)/1024:.0f} KB")
    metin = ""
    for s in PyPDF2.PdfReader(io.BytesIO(ham)).pages:
        metin += (s.extract_text() or "") + "\n"
    satirlar = metin.splitlines()
    print(f"  metin: {len(satirlar)} satır\n")

    baslik = re.search(r"([A-Za-zçğıöşüÇĞİÖŞÜ]+)\s*(?:\d{4}\s*)?[-–]\s*"
                       r"([A-Za-zçğıöşüÇĞİÖŞÜ]+)\s+(\d{4})", metin)
    print(f"── Dönem başlığı: {baslik.group(0) if baslik else 'BULUNAMADI'}\n")

    print("── Finansman programı — HAM SATIRLAR (sütun sırası = dönemin ayları)")
    for ad in SATIRLAR:
        vurdu = [x for x in satirlar if ad in x]
        if not vurdu:
            print(f"  [{ad}] satır yok")
            continue
        for x in vurdu[:3]:
            print(f"  [{ad}]\n      ham : {x.strip()[:200]}")
            print(f"      sayı: {SAYI.findall(x)}")
    print("\n── 'Kasım' geçen satırlar (ayın adıyla anılan her yer)")
    for x in satirlar:
        if "Kasım" in x:
            print(f"  {x.strip()[:180]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
