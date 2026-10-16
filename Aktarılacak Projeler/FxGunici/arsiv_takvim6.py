#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber takviminin ALTINCI geçişi: kuraldan ayrılan BoE saatleri ve örneklemin sonundaki TÜFE yayımı (bulut koşucusu).

İnceleme (16.10.2026) iki boşluk buldu; ikisi de tarih tarih kaynak ister, fiyattan saat yazılmaz:
  · BoE — takvim her kararın saatini BoE'nin yayım KURALINDAN ("published at 12 noon on a Thursday") alıyor. 2020'nin
    üç Para Politikası Raporu günü (07.05, 06.08, 05.11) fiyat 07:00 Londra'yı gösteriyor. BoE iki duyurusunda saati
    kendisi yazıyor (Ağustos ve Kasım 2020; adresler bu oturumda arama motoruyla bulundu, BILINEN). Mayıs 2020'nin
    duyurusu bilinmiyor: geçiş Internet Archive dizininden BoE'nin 2020 haber sayfalarının ADLARINI öğrenir (adres
    tahmin edilmez), saat değişikliği ya da rapor düzeni geçen sayfaları BoE'den ister ve "upcoming MPC dates"
    sayfasının 2020 kopyalarını alır. Ayrıştırma yerelde (takvim_kur.boe_saat); okunamayan tarih adıyla kalır.
  · BLS — son okunan TÜFE bülteni (11.09.2026) bir sonraki yayımı "Wednesday, October 14, 2026, at 8:30 a.m." diye
    yazıyor; o tarih örneklemin içinde ve kopya arşivde yok. Geçiş Internet Archive dizinini o tarihten sonrası için
    yeniden sorar; kopya varsa ambargo satırı üçüncü geçişin biçimiyle deftere eklenir (bls.gov'a istek atılmaz).

PARÇA (`TTO_PARCA`): `boe-saat` · `bls-son`; boşsa ikisi. Yalnız indirir. Var olan dosya yeniden indirilmez.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path

import arsiv_takvim3 as a3

import ozler

HAM = a3.HAM
BOE = "https://www.bankofengland.co.uk"
#: Arama motoruyla bulunan BoE metinleri (16.10.2026): Ağustos 2020 ve Kasım 2020 saat duyuruları, FPC'nin Nisan 2020
#: açıklaması (ara Finansal İstikrar Raporu'nun 7 Mayıs'ı), Mayıs 2020 rapor sayfası, 2020 MPC takvimi duyurusu.
BILINEN = [
    "/news/2020/july/boe-statement-august-monetary-policy-report-and-financial-stability-report",
    "/news/2020/november/time-change-november-monetary-policy-report-and-monetary-policy-committee-decision-and-minutes",
    "/-/media/boe/files/statement/fpc/2020/financial-policy-committee-statement-april-2020.pdf",
    "/report/2020/monetary-policy-report-financial-stability-report-may-2020",
    "/news/2019/september/monetary-policy-committee-dates-for-2020",
]
#: Haber sayfasının adı saat ya da rapor düzeni anıyorsa istenir (Mart–Kasım 2020).
ADAY_AD = re.compile(r"(?i)time|timing|publication|arrangement|monetary-policy-report|monetary-policy-committee|"
                     r"mpc|statement")
UPCOMING = "bankofengland.co.uk/monetary-policy/upcoming-mpc-dates"


class Kunye6(a3.Kunye):
    def __init__(self, parca: str):
        self.yol = HAM / f"manifest6_{parca}.json"
        self.v = json.loads(self.yol.read_text(encoding="utf-8")) if self.yol.exists() else {}


def _cdx(k: Kunye6, url: str) -> list[list[str]]:
    s = k.kaydet(a3.getir(url, a3.IA_BEKLE))
    time.sleep(a3.IA_ARA)
    if not s.get("dosya"):
        return []
    try:
        return json.loads((HAM / s["dosya"]).read_text(encoding="utf-8"))[1:]
    except ValueError:
        return []


def _getir(url: str) -> dict:
    """a3.getir; PDF kendi uzantısıyla saklanır (yerelde metni pdftotext ile okunur)."""
    if not url.lower().endswith(".pdf"):
        return a3.getir(url)
    yol = HAM / a3.ad(url, ".pdf")
    if yol.exists():
        return {"url": url, "durum": "var", "dosya": yol.name}
    durum, veri = a3.iste(url)
    if durum == 200:
        yol.write_bytes(veri)
        return {"url": url, "durum": 200, "dosya": yol.name, "bayt": len(veri)}
    return {"url": url, "durum": durum}


def boe_saat() -> None:
    k = Kunye6("boe-saat")
    for yol in BILINEN:
        k.kaydet(_getir(BOE + yol))
        time.sleep(1.0)
    # 2020 haber sayfalarının adları Internet Archive dizininden (Mart–Kasım).
    satir = _cdx(k, "https://web.archive.org/cdx/search/cdx?url=bankofengland.co.uk/news/2020/&matchType=prefix"
                    "&output=json&fl=original,timestamp,statuscode&collapse=urlkey&filter=statuscode:200&limit=20000")
    adaylar: list[str] = []
    for orij, _ts, _d in satir:
        m = re.search(r"/news/2020/(march|april|may|june|july|august|september|october|november)/([a-z0-9-]+)/?$",
                      orij.split("?")[0])
        if m and ADAY_AD.search(m.group(2)):
            yol = f"/news/2020/{m.group(1)}/{m.group(2)}"
            if yol not in adaylar and yol not in BILINEN:
                adaylar.append(yol)
    print(f"BoE 2020 haber sayfası adayı: {len(adaylar)}", flush=True)
    k.v["_boe_adaylar"] = adaylar
    for yol in adaylar[:120]:
        if a3.kalan() < 120:
            break
        k.kaydet(a3.getir(BOE + yol))
        time.sleep(1.0)
    # "Upcoming MPC dates" sayfasının 2020 kopyaları (saat değişikliği o sayfaya da yazılmış olabilir).
    satir = _cdx(k, f"https://web.archive.org/cdx/search/cdx?url={UPCOMING}&from=20200401&to=20201106"
                    "&output=json&fl=timestamp,statuscode,digest&filter=statuscode:200&collapse=digest&limit=200")
    for ts, _d, _g in satir[:12]:
        if a3.kalan() < 60:
            break
        k.kaydet(a3.getir(f"https://web.archive.org/web/{ts}id_/https://www.{UPCOMING}", a3.IA_BEKLE))
        time.sleep(a3.IA_ARA)
    k.yaz()


def bls_son() -> None:
    """Örneklemin sonuna düşen TÜFE yayımları: dizin 10.09.2026'dan sonrası için yeniden sorulur (üçüncü geçişin
    dizin kopyası o anın listesidir ve yeniden indirilmez)."""
    k = Kunye6("bls-son")
    hedef = HAM / "bls_cpi_ambargo.json"
    defter = json.loads(hedef.read_text(encoding="utf-8")) if hedef.exists() else {}
    satir = _cdx(k, "https://web.archive.org/cdx/search/cdx?url=bls.gov/news.release/archives/cpi_&matchType=prefix"
                    "&from=20260910&output=json&fl=original,timestamp,statuscode,mimetype&collapse=urlkey"
                    "&filter=statuscode:200&limit=2000")
    aday: dict[str, tuple[str, str]] = {}
    for orij, ts, durum, _mime in satir:
        m = re.search(r"archives/cpi_(\d{2})(\d{2})(\d{4})\.htm$", orij)
        if not m or durum != "200":
            continue
        try:
            g = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        except ValueError:
            continue
        if a3.BAS <= g <= a3.BIT and g.isoformat() not in aday:
            aday[g.isoformat()] = (orij, ts)
    for g in sorted(aday):
        if g in defter and defter[g].get("ambargo"):
            continue
        orij, ts = aday[g]
        url = f"https://web.archive.org/web/{ts}id_/{orij}"
        durum, veri = a3.iste(url, a3.IA_BEKLE)
        kayit = {"url": url, "orijinal": orij, "wayback": ts, "durum": durum}
        if durum == 200:
            metin = a3.duz(veri)
            i = metin.find("Transmission of material")
            bas = re.search(r"(?is)<title>(.*?)</title>", veri.decode("utf-8", errors="replace"))
            kayit.update({"sha256": hashlib.sha256(veri).hexdigest(), "bayt": len(veri),
                          "baslik": html.unescape(bas.group(1).strip()) if bas else "",
                          "ambargo": metin[i:i + 400] if i >= 0 else ""})
        defter[g] = kayit
        print(f"{durum}\t{g}\t{kayit.get('ambargo', '')[:90]}", flush=True)
        time.sleep(a3.IA_ARA)
    hedef.write_text(json.dumps(defter, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    k.v["bls:cpi:son"] = {"aday": sorted(aday), "okunan": sorted(g for g in aday if defter.get(g, {}).get("ambargo"))}
    k.yaz()


PARCALAR = {"boe-saat": boe_saat, "bls-son": bls_son}


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    istenen = os.environ.get("TTO_PARCA", "").split() or list(PARCALAR)
    bilinmeyen = [p for p in istenen if p not in PARCALAR]
    if bilinmeyen:
        raise SystemExit(f"bilinmeyen parça: {bilinmeyen} (tanınan: {list(PARCALAR)})")
    for p in istenen:
        print(f"── {p}", flush=True)
        PARCALAR[p]()
    print(f"bitti: {time.monotonic() - a3.T0:.0f} sn")
    ozler.yaz(HAM)      # ham sayfaların SHA-256 sabitlemesi (takvim_kur okumadan önce sınar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
