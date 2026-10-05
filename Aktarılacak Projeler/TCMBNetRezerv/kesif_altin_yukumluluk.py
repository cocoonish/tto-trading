# -*- coding: utf-8 -*-
"""TCMB'nin ALTIN CİNSİNDEN YÜKÜMLÜLÜKLERİ — keşif (EVDS3, haftalık bilanço).

NİYE VAR (05.10.2026). Günlük net döviz alımı, net pozisyonun değişiminden
altın fiyat etkisi düşülerek kuruluyor: Γ = Q·ΔP, Q = IRFCL'deki BRÜT altın.
Ölçüldü: 2026'da dış varlıklar Γ'ya 1,08 ile tepki veriyor (beklenen), ama
yükümlülük tarafı (A02 − net dış varlık = A11 + A14) da 0,32 ile (t ≈ 7) —
TCMB'nin altın cinsinden yükümlülükleri var ve onlar da yeniden değerleniyor.
Net pozisyondan BRÜT altının fiyat etkisini düşmek fazla düşmek demek;
yayımlanan akımın Γ'ya eğimi −0,29 (t ≈ −3,6).

Yükümlülük altını TCMB haftalık bilançosunda (bie_mbblnch) SAFİ GRAM olarak
kalem kalem duruyor (katalog Research/analiz-tcmb-api/data/serieList_bie_mbblnch.json):
    TP.BL0823  P3112   Hazine altın mevduatı (kamu — A13'e düşer)
    TP.BL128   P32122  Yurt içi bankalar, teminat altın
    TP.BL137   P3213   Yurt içi bankalar, altın
    TP.BL0891  P3232   Zorunlu karşılık bloke hesabı, altın
    TP.BL142   P4.2    Yurt dışı bankalar, altın
    TP.BL1111  P121    Uluslararası standartta olmayan Hazine altınları (diğer pasifler)
Kod TAHMİN EDİLMEDİ, katalogdan okundu. Bu betik her kodu GERÇEKTEN çağırır ve
haftalık değerleri döker; hangi kalemin net pozisyona girdiği ölçümle (yerelde,
günlük seriye karşı regresyonla) kurulur, burada değil.

Koşum (yalnız iş akışından; oturum vekili tcmb.gov.tr'yi kapatıyor):
    veri.yml → kesif: Aktarılacak Projeler/TCMBNetRezerv/kesif_altin_yukumluluk.py
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

GRAM = {
    "hazine_g": "TP.BL0823",
    "banka_teminat_g": "TP.BL128",
    "banka_g": "TP.BL137",
    "zk_g": "TP.BL0891",
    "yd_banka_g": "TP.BL142",
    "hazine_std_disi_g": "TP.BL1111",
    "varlik_std_disi_g": "TP.BL0451",
}
# Aynı kalemlerin YP (TL karşılığı) değerleri — gram × fiyat × kur ile çapraz
# sınama için; ve varlık tarafındaki altının TL değeri.
DEGER = {
    "hazine_yp": "TP.BL0822",
    "banka_teminat_yp": "TP.BL132",
    "banka_yp": "TP.BL136",
    "zk_yp": "TP.BL089",
    "yd_banka_yp": "TP.BL141",
    "varlik_altin": "TP.BL001",
}


def anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    y = PROJE / ".evds_key"
    if y.exists():
        return y.read_text(encoding="utf-8").strip()
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
    bas, son = "01-12-2022", bugun.strftime("%d-%m-%Y")
    print("=" * 74)
    print("  TCMB ALTIN YÜKÜMLÜLÜKLERİ — haftalık bilanço (safi gram)")
    print("=" * 74, flush=True)
    tum = {**GRAM, **DEGER}
    veri: dict[str, dict[str, str]] = {}
    for ad, kod in tum.items():
        v = seri(kod, bas, son)
        veri[ad] = v
        if v:
            ks = sorted(v, key=lambda t: dt.datetime.strptime(t, "%d-%m-%Y"))
            print(f"  ✓ {ad:20s} {kod:12s} n={len(v):4d}  {ks[0]} → {ks[-1]}  son={v[ks[-1]]}", flush=True)
        else:
            print(f"  ✗ {ad:20s} {kod:12s} veri YOK", flush=True)
    tarihler = sorted({t for v in veri.values() for t in v},
                      key=lambda t: dt.datetime.strptime(t, "%d-%m-%Y"))
    adlar = list(tum)
    print("\nCSV_BAS")
    print("tarih;" + ";".join(adlar))
    for t in tarihler:
        print(t + ";" + ";".join(veri[a].get(t, "") for a in adlar))
    print("CSV_SON", flush=True)
    print(f"ÖZET: {sum(1 for v in veri.values() if v)}/{len(tum)} seri veri döndürdü · {len(tarihler)} hafta", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
