#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber takviminin DÖRDÜNCÜ geçişi: FOMC basın toplantısının saati, tarih tarih (bulut koşucusu).

Üçüncü geçiş ölçtü: Fed'in aylık etkinlik sayfaları geçmiş toplantıları tek kayda indiriyor ("FOMC
Meeting · 2:00 p.m. · Press Conference") ve basın toplantısına ayrı saat yazmıyor; ayrı saatli kayıt
("FOMC Press Conference · 2:30 p.m.") yalnız Fed'in takvim beslemesinde (`json/calendar.json`) duruyor
ve besleme bugün yalnız Eylül 2025'ten sonrasını taşıyor. Beslemenin GEÇMİŞ kopyaları Internet
Archive'da: her kopya o günün takvimidir ve yaklaşan toplantının basın toplantısını saatiyle listeler.

Bu geçiş:
  1. Internet Archive dizininden beslemenin bütün kopyalarının listesini ister (içerik özüyle tekilleşmiş).
  2. 2017-12'den bu yana her takvim ayından ilk kopyayı indirir ve kopyanın TAMAMINI değil, basın
     toplantısı geçen kayıtlarını saklar (`ham/fed_takvim_basin.json`): başlık, saat, ay, gün, tür,
     açıklama. Kopyanın sha256'sı ve arşiv adresi de yazılır: kayıt yeniden indirilip sınanabilir.
  3. Beslemenin kopyası olmayan ay için aynı ayın aylık etkinlik sayfasının o ay İÇİNDE alınmış
     kopyasını dener (sayfa o tarihte yaklaşan etkinliği ayrı saatle gösteriyor olabilir) ve yalnız
     "Press Conference" geçen satırları saklar.
Yalnız indirir; hangi saatin kabul edildiği ayrıştırmada (`takvim_kur.py`): bir tarih için bütün
kopyalar aynı saati yazıyorsa o saat, çelişiyorsa hiçbiri.

PARÇA (`TTO_PARCA`): `fed-basin` · `londra-tatil` (İngiltere ve Galler resmî tatil listesi). Internet Archive istekleri arası 4 sn, bütçe 18 dakika.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import arsiv_takvim3 as a3

import ozler

HAM = a3.HAM
ALAN = ("title", "time", "month", "days", "type", "description", "location")


class Kunye4(a3.Kunye):
    def __init__(self, parca: str):
        self.yol = HAM / f"manifest4_{parca}.json"
        self.v = json.loads(self.yol.read_text(encoding="utf-8")) if self.yol.exists() else {}


def _basin_kayitlari(veri: bytes) -> list[dict] | None:
    try:
        d = json.loads(veri.decode("utf-8-sig", errors="replace"))
    except ValueError:
        return None
    olaylar = d.get("events") if isinstance(d, dict) else d
    if not isinstance(olaylar, list):
        return None
    out = []
    for e in olaylar:
        if isinstance(e, dict) and "press conference" in json.dumps(e, ensure_ascii=False).lower():
            out.append({k: (str(e[k])[:300] if k == "description" else e[k]) for k in ALAN if k in e})
    return out


def fed_basin() -> None:
    k = Kunye4("fed-basin")
    hedef = HAM / "fed_takvim_basin.json"
    defter = json.loads(hedef.read_text(encoding="utf-8")) if hedef.exists() else {}
    cdx = ("https://web.archive.org/cdx/search/cdx?url=federalreserve.gov/json/calendar.json"
           "&output=json&fl=timestamp,statuscode,digest&filter=statuscode:200&collapse=digest&limit=20000")
    s = k.kaydet(a3.getir(cdx, a3.IA_BEKLE))
    time.sleep(a3.IA_ARA)
    kopyalar: list[str] = []
    if s.get("dosya"):
        try:
            kopyalar = [r[0] for r in json.loads((HAM / s["dosya"]).read_text(encoding="utf-8"))[1:]]
        except ValueError:
            kopyalar = []
    ilk: dict[str, str] = {}
    for ts in sorted(kopyalar):
        ay = f"{ts[:4]}-{ts[4:6]}"
        if "2017-12" <= ay <= "2025-10" and ay not in ilk:
            ilk[ay] = ts
    print(f"besleme kopyası: {len(kopyalar)} · ay başına ilk: {len(ilk)} "
          f"({min(ilk) if ilk else '—'} → {max(ilk) if ilk else '—'})", flush=True)
    for ay, ts in sorted(ilk.items()):
        if ts in defter and defter[ts].get("olay") is not None:
            continue
        if a3.kalan() < 90:
            break
        url = f"https://web.archive.org/web/{ts}id_/https://www.federalreserve.gov/json/calendar.json"
        durum, veri = a3.iste(url, a3.IA_BEKLE)
        kayit = {"url": url, "wayback": ts, "ay": ay, "durum": durum}
        if durum == 200:
            kayit.update({"sha256": hashlib.sha256(veri).hexdigest(), "bayt": len(veri),
                          "olay": _basin_kayitlari(veri)})
        defter[ts] = kayit
        n = len(kayit.get("olay") or [])
        print(f"{durum}\t{ay}\t{ts}\tbasın kaydı {n}", flush=True)
        time.sleep(a3.IA_ARA)
    # Beslemenin kopyası olmayan aylar: aylık etkinlik sayfasının o ay içindeki kopyası.
    eksik = [f"{y}-{m:02d}" for y in range(2018, 2026) for m in range(1, 13)
             if f"{y}-{m:02d}" not in ilk and f"{y}-{m:02d}" <= "2025-10"]
    print(f"beslemesi olmayan ay: {len(eksik)}", flush=True)
    for ay in eksik:
        if a3.kalan() < 90:
            break
        y, m = int(ay[:4]), int(ay[5:])
        sayfa = f"federalreserve.gov/newsevents/{y}-{a3.AYLAR[m - 1]}.htm"
        cdx_ay = (f"https://web.archive.org/cdx/search/cdx?url={sayfa}&output=json&fl=timestamp,statuscode"
                  f"&filter=statuscode:200&from={y}{m:02d}01&to={y}{m:02d}31&limit=50")
        durum, veri = a3.iste(cdx_ay, a3.IA_BEKLE)
        time.sleep(a3.IA_ARA)
        if durum != 200:
            defter[f"sayfa:{ay}"] = {"ay": ay, "durum": durum, "cdx": cdx_ay}
            continue
        try:
            satir = json.loads(veri.decode("utf-8", errors="replace"))[1:]
        except ValueError:
            satir = []
        if not satir:
            defter[f"sayfa:{ay}"] = {"ay": ay, "durum": "kopya yok", "cdx": cdx_ay}
            continue
        ts = satir[0][0]
        url = f"https://web.archive.org/web/{ts}id_/https://www.{sayfa}"
        durum, veri = a3.iste(url, a3.IA_BEKLE)
        kayit = {"url": url, "wayback": ts, "ay": ay, "durum": durum}
        if durum == 200:
            metin = a3.duz(veri)
            parca = [metin[max(0, mm.start() - 160): mm.end() + 120]
                     for mm in re.finditer(r"(?i)press conference", metin)]
            kayit.update({"sha256": hashlib.sha256(veri).hexdigest(), "bayt": len(veri), "satir": parca[:12]})
        defter[f"sayfa:{ay}"] = kayit
        print(f"{durum}\tsayfa {ay}\t{ts}\tsatır {len(kayit.get('satir') or [])}", flush=True)
        time.sleep(a3.IA_ARA)
    hedef.write_text(json.dumps(defter, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    k.v["fed:basin"] = {"durum": 200, "dosya": hedef.name, "besleme_kopya": len(kopyalar), "ay": len(ilk),
                        "okunan": sum(1 for x in defter.values() if x.get("olay") is not None or x.get("satir"))}
    k.yaz()


def londra_tatil() -> None:
    """İngiltere ve Galler resmî tatillerinin resmî listesi (gov.uk). Ders `zaman.londra_tatilleri`
    kuralını kullanır (ay sonu = ayın son Londra iş günü); bu dosya kuralın bağımsız kıyasıdır ve
    bir birim testi ikisini yıl yıl karşılaştırır. Liste yalnız yakın yılları taşıyabilir; kapsamı
    dosyanın kendisinden okunur. Aynı listenin geçmiş kopyası Internet Archive'dan da istenir
    (daha eski yılları taşıyabilir)."""
    k = Kunye4("londra-tatil")
    kayit = {}
    for ad, url in (("gov.uk", "https://www.gov.uk/bank-holidays.json"),
                    ("ia-2019", "https://web.archive.org/web/2019id_/https://www.gov.uk/bank-holidays.json")):
        durum, veri = a3.iste(url, a3.IA_BEKLE)
        x = {"url": url, "durum": durum}
        if durum == 200:
            try:
                d = json.loads(veri.decode("utf-8"))
                olay = (d.get("england-and-wales") or {}).get("events") or []
                x.update({"sha256": hashlib.sha256(veri).hexdigest(), "bayt": len(veri),
                          "olay": [{"date": e.get("date"), "title": e.get("title")} for e in olay]})
            except ValueError:
                x["durum"] = "ayrıştırılamadı"
        kayit[ad] = x
        print(f"{durum}\t{ad}\t{len(x.get('olay') or [])} olay", flush=True)
        time.sleep(a3.IA_ARA)
    hedef = HAM / "londra_tatil.json"
    hedef.write_text(json.dumps(kayit, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    k.v["londra:tatil"] = {"durum": 200, "dosya": hedef.name}
    k.yaz()


PARCALAR = {"fed-basin": fed_basin, "londra-tatil": londra_tatil}


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    istenen = os.environ.get("TTO_PARCA", "").split() or list(PARCALAR)
    bilinmeyen = [p for p in istenen if p not in PARCALAR]
    if bilinmeyen:
        raise SystemExit(f"bilinmeyen parça: {bilinmeyen} (tanınan: {list(PARCALAR)})")
    for p in istenen:
        print(f"── {p}", flush=True)
        PARCALAR[p]()
    print(f"bitti: {time.monotonic() - a3.T0:.0f} sn · {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    ozler.yaz(HAM)      # ham sayfaların SHA-256 sabitlemesi (takvim_kur okumadan önce sınar)
    return 0


if __name__ == "__main__":
    sys.exit(main())
