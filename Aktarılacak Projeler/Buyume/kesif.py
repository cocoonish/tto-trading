# -*- coding: utf-8 -*-
"""Büyüme (GSYH) hattı — KEŞİF katmanı (EVDS3).

veri.py yazılmadan ÖNCE hangi serilerin GERÇEKTEN var olduğunu, hangi birimde
ve frekansta geldiğini, nerede başlayıp nerede bittiğini ÖLÇER. Uydurma seri
kodu hatta girmez.

Bu oturumun ağ vekili tcmb.gov.tr'yi kapatıyor; betik EVDS anahtarının durduğu
GitHub koşucusunda çalışır (kesif.yml). Çıktı hem loga basılır hem
data/kesif_sonuc.json'a yazılır.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PROJE = Path(__file__).resolve().parent
KOK = PROJE.parent.parent
BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

# OdemelerDengesi/veri.py ile AYNI sıra. Anahtar koda GÖMÜLMEZ.
ANAHTAR_YOLLARI = (PROJE / ".evds_key", KOK / ".evds_key",
                   KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key")


def _anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    for y in ANAHTAR_YOLLARI:
        if y.exists():
            a = y.read_text(encoding="utf-8").strip()
            if a:
                return a
    raise SystemExit("EVDS anahtarı yok (TTO_EVDS_KEY ya da .evds_key)")


_A: str | None = None


def _cek(url: str, deneme: int = 3):
    global _A
    if _A is None:
        _A = _anahtar()
    son = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"key": _A, "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            son = ex
    raise RuntimeError(f"EVDS düştü: {url[:110]} — {son}")


# GSYH ailesini adından tanı; kod öneki tek başına yetmiyor (bie_gsyh*, TP.GSYIH*)
ARANAN = re.compile(r"gayrisafi|gsyh|gsyih|hasıla|hasila|büyüme|buyume|"
                    r"harcama yöntemi|üretim yöntemi|uretim yontemi", re.I)


def main() -> int:
    print("── EVDS: GSYH ailesi keşfi", flush=True)
    gruplar = _cek(f"{BASE}/datagroups/mode=0&type=json")
    print(f"   toplam veri grubu: {len(gruplar)}")

    # ARŞİV ve İL bazlı gruplar dışarıda: ilki donmuş (2006'da bitiyor),
    # ikincisi yıllık ve 81 il × 5 seri ile raporu boğuyor. Aranan şey
    # ULUSAL, ÜÇ AYLIK hesaplar.
    ARSIV = re.compile(r"arşiv|arsiv|archive", re.I)
    canli, arsiv = [], []
    for g in gruplar:
        ad = str(g.get("DATAGROUP_NAME") or "")
        kod = str(g.get("DATAGROUP_CODE") or "")
        if not (ARANAN.search(ad) or ARANAN.search(kod)):
            continue
        frek = str(g.get("FREQUENCY_STR") or g.get("FREQUENCY") or "")
        kayit = (kod, ad, frek, str(g.get("START_DATE") or ""), str(g.get("END_DATE") or ""))
        (arsiv if ARSIV.search(ad) else canli).append(kayit)

    print(f"   eşleşen: {len(canli) + len(arsiv)}  (canlı {len(canli)} · arşiv {len(arsiv)})")
    print("\n   ARŞİV grupları (incelenmeyecek): "
          + ", ".join(k for k, *_ in sorted(arsiv)) + "\n")

    rapor: dict = {"gruplar": {}}
    for kod, ad, frek, bas, bit in sorted(canli):
        print(f"══ {kod}  |  {ad}")
        print(f"   frekans={frek}  aralık={bas} → {bit}")
        try:
            d = _cek(f"{BASE}/serieList/type=json&code={kod}")
        except Exception as ex:
            print(f"   ! serieList düştü: {ex}\n")
            continue
        seriler = d if isinstance(d, list) else (d.get("series") or d.get("Series") or [])
        print(f"   seri sayısı: {len(seriler)}")
        kayit = []
        for s_ in seriler:
            skod = str(s_.get("SERIE_CODE") or s_.get("SERIE_NAME") or "")
            sad = str(s_.get("SERIE_NAME_ENG") or s_.get("SERIE_NAME") or "")
            birim = str(s_.get("BIRIMI") or s_.get("UNIT") or "")
            sbas, sbit = str(s_.get("START_DATE") or ""), str(s_.get("END_DATE") or "")
            kayit.append({"kod": skod, "ad": sad, "birim": birim, "bas": sbas, "bit": sbit})
            print(f"      {skod:<28} {sad[:70]:<72} [{birim}] {sbas}→{sbit}")
        rapor["gruplar"][kod] = {"ad": ad, "frekans": frek, "seriler": kayit}
        print()

    (PROJE / "data").mkdir(exist_ok=True)
    (PROJE / "data" / "kesif_sonuc.json").write_text(
        json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")

    # DİZİN EN SONA: log kuyruğu kesilse bile hangi grubun ne olduğu görünsün.
    print("\n" + "═" * 78)
    print("DİZİN — canlı GSYH grupları (kod · frekans · seri · aralık · ad)")
    print("═" * 78)
    for kod, ad, frek, bas, bit in sorted(canli):
        n = len(rapor["gruplar"].get(kod, {}).get("seriler", []))
        print(f"{kod:<22} {frek:<10} {n:>4} seri  {bas[:10]}→{bit[:10]}  {ad[:52]}")
    print(f"\n── yazıldı: data/kesif_sonuc.json ({len(rapor['gruplar'])} grup)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
