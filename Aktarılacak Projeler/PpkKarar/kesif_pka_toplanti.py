# -*- coding: utf-8 -*-
"""PİYASA KATILIMCILARI ANKETİ — politika faizi soruları (keşif, EVDS3).

NİYE VAR (22.10.2026). 22 Ekim PPK yazısı karar öncesi sayısal bir beklenti
olmadan "sürpriz" hesaplayamıyordu. Anket o beklentiyi soruyor: TP.PKAUO.S04.C.U
"ilk toplantı için politika faizi beklentisi" (2025-06'dan; öncesinde S04.A.U,
cari ay sonu bir hafta vadeli repo). Kodlar TAHMİN EDİLMEDİ: Makro→kur/faiz
dersinin bulut arşivi (MakroKurFaiz/hazirla_bulut.py) aynı grubu okuyor; oradaki
son gözlem Ağustos 2026 anketi. Bu betik her kodu çağırır ve değerleri olduğu gibi
döker; yorum yapmaz.

Koşum (yalnız iş akışından; oturum vekili tcmb.gov.tr'yi kapatıyor):
    veri.yml → kesif: Aktarılacak Projeler/PpkKarar/kesif_pka_toplanti.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import urllib.request

PROJE = pathlib.Path(__file__).resolve().parent
BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

KODLAR = {
    "cari_ay_sonu_repo": "TP.PKAUO.S04.A.U",
    "ay3_repo": "TP.PKAUO.S04.B.U",
    "ilk_toplanti": "TP.PKAUO.S04.C.U",
    "faiz_12a": "TP.PKAUO.S04.D.U",
    "faiz_24a": "TP.PKAUO.S04.E.U",
    "ikinci_toplanti": "TP.PKAUO.S04.F.U",
    "ucuncu_toplanti": "TP.PKAUO.S04.G.U",
    "yilsonu": "TP.PKAUO.S04.H.U",
    "s04_i": "TP.PKAUO.S04.I.U",
    "tufe_12a": "TP.PKAUO.S01.E.U",
}


def anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    raise RuntimeError("EVDS anahtarı yok (TTO_EVDS_KEY).")


def cek(yol: str, deneme: int = 3):
    url = f"{BASE}/{yol}"
    son = None
    for _ in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:                                  # noqa: BLE001
            son = ex
    print(f"  ! çekilemedi: {yol[:100]} → {type(son).__name__}: {son}", flush=True)
    return None


def seri(kod: str, bas: str, son: str) -> dict[str, str]:
    d = cek(f"series={kod}&startDate={bas}&endDate={son}&type=json")
    kolon = kod.replace(".", "_")
    out = {}
    for i in (d or {}).get("items") or []:
        v = i.get(kolon)
        if v not in (None, "", "null"):
            out[str(i.get("Tarih"))] = str(v)
    return out


def main() -> int:
    bugun = dt.date.today()
    bas, son = "01-01-2025", bugun.strftime("%d-%m-%Y")
    print("=" * 74)
    print("  PİYASA KATILIMCILARI ANKETİ — politika faizi soruları (uygun ortalama)")
    print("=" * 74, flush=True)
    veri: dict[str, dict[str, str]] = {}
    for ad, kod in KODLAR.items():
        v = seri(kod, bas, son)
        veri[ad] = v
        if v:
            ks = sorted(v)
            print(f"  ✓ {ad:18s} {kod:18s} n={len(v):3d}  {ks[0]} → {ks[-1]}  son={v[ks[-1]]}", flush=True)
        else:
            print(f"  ✗ {ad:18s} {kod:18s} veri YOK", flush=True)
    tarihler = sorted({t for v in veri.values() for t in v})
    adlar = list(KODLAR)
    print("\nCSV_BAS")
    print("tarih;" + ";".join(adlar))
    for t in tarihler:
        print(t + ";" + ";".join(veri[a].get(t, "") for a in adlar))
    print("CSV_SON", flush=True)
    print(f"ÖZET: {sum(1 for v in veri.values() if v)}/{len(KODLAR)} seri veri döndürdü · {len(tarihler)} anket",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
