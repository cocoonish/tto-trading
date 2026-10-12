#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — altıncı arşiv geçişi: akaryakıt ÖTV kararlarının metni.

Neden ayrı bir geçiş: beşinci geçiş (`arsiv_brent_kaynak.py`) Resmî Gazete fihristini
indirdi ama karar bağlantılarını BULAMADI — sayfalar `windows-1254` kodlu ve betik onları
UTF-8 sanıp çözdü; "Özel Tüketim Vergisi" dizgesi bozuk harflerle hiç eşleşmedi (12.10.2026
14:45 koşusu: dört günün dördünde "0 bağlantı", oysa 01.10 ve 13.08 fihristlerinde karar
duruyordu). Kural: bir sayfanın kodlaması SAYFANIN KENDİSİNDEN okunur (`charset`), tahmin
edilmez; bulunamayan bağlantı "yok" değil "eşleşmedi" diye yazılır.

Kapsam: eşel mobilin başladığı Mart 2026 başı, motorinde eşel mobilin bittiği ve kademeli
takvimin başladığı Ağustos ortası–Eylül başı, benzinin kararının çıktığı Ekim başı. Her gün
için asıl sayı ve ilk mükerrer sayı (`M1`) yoklanır; adında ÖTV geçen her bağlantı izlenir.
Karar adresi TAHMİN EDİLMEZ, fihristten çözülür. Künye `kunye_rg.json`, rapor `rapor_rg.json`.
"""
from __future__ import annotations

import re
import sys
import time
import urllib.parse
from datetime import date, timedelta

import arsiv_brent as ab

RG_KOK = "https://www.resmigazete.gov.tr/eskiler"
ARALIKLAR = [(date(2026, 3, 2), date(2026, 3, 10)), (date(2026, 8, 10), date(2026, 9, 2)),
             (date(2026, 9, 28), date(2026, 10, 2))]
ARANAN = ("özel tüketim vergisi",)


def _coz(govde: bytes) -> str:
    m = re.search(rb'charset=["\']?([\w-]+)', govde[:4000], flags=re.I)
    kod = m.group(1).decode("ascii", "replace") if m else "utf-8"
    try:
        return govde.decode(kod, errors="replace")
    except LookupError:
        return govde.decode("utf-8", errors="replace")


def _gunler():
    for a, b in ARALIKLAR:
        g = a
        while g <= b:
            yield g
            g += timedelta(days=1)


@ab.kaynak("Resmî Gazete ÖTV kararları (kodlama düzeltilmiş)")
def resmi_gazete() -> dict:
    sonuc = {}
    for g in _gunler():
        if ab.kalan() < 60:
            sonuc[g.isoformat()] = "bütçe doldu"
            continue
        for ek in ("", "M1"):
            gun = g.strftime("%Y%m%d") + ek
            fihrist = f"{RG_KOK}/{g:%Y}/{g:%m}/{gun}.htm"
            try:
                d, gv = ab.al(fihrist, sn=30, deneme=1)
            except RuntimeError as e:
                sonuc[gun] = f"hata {e}"[:140]
                continue
            if d != 200 or not gv:
                sonuc[gun] = {"durum": d}
                continue
            metin = _coz(gv)
            if "Resm" not in metin:
                sonuc[gun] = {"durum": d, "not": "fihrist değil"}
                continue
            baglar = []
            for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', metin, flags=re.S | re.I):
                yazi = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).replace("&nbsp;", " ").strip()
                if any(a in yazi.lower() for a in ARANAN) or "ÖZEL TÜKETİM VERGİSİ" in yazi:
                    baglar.append((urllib.parse.urljoin(fihrist, m.group(1)), yazi))
            kayit = {"durum": d, "bag": []}
            if baglar:
                ab.yaz(f"resmigazete/{gun}_fihrist.html.gz", gv, fihrist, d, not_="RG fihristi")
            for u, yazi in baglar:
                try:
                    d2, g2 = ab.al(u, sn=40)
                except RuntimeError as e:
                    kayit["bag"].append({"url": u, "yazi": yazi, "hata": str(e)[:120]})
                    continue
                if d2 == 200 and g2:
                    uz = "pdf" if g2[:5] == b"%PDF-" else "html"
                    ad = u.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                    ab.yaz(f"resmigazete/karar_{ad}.{uz}.gz", g2, u, d2, not_=yazi[:200])
                kayit["bag"].append({"url": u, "yazi": yazi, "durum": d2, "bayt": len(g2)})
                time.sleep(0.4)
            sonuc[gun] = kayit
            print(f"   RG {gun}: {len(baglar)} ÖTV bağlantısı", flush=True)
            time.sleep(0.3)
    return sonuc


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    resmi_gazete()
    ab.kaydet("rg")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
