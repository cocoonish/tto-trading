#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JEOPOLİTİK DEFTERİ — yazının bütün sayılarını ÜRETEN tek ölçüm.

Neden ayrı bir betik: yazının üç yıllık dağılım sayıları ilk turda yalnız
koşu kaydında vardı, depoda değildi — yani hiçbir kapı onları bir daha
soramazdı. Arşiv depoda durur (yayımlanmış bir gözlem bir daha değişmez);
bu betik o arşivi TEK bir JSON bloğu olarak basar ve depoya o blok yazılır.

İki kaynak, iki sözleşme:

1) ENERJİ — ham ön vade kapanışı. Vade devri için geriye ölçeklenmiş seri
   bir CRACK SPREAD'e uygulanamaz: üç bacak farklı oranla ölçeklenir
   (ölçüldü: HO 0,956 · CL 0,954 · RB 0,926) ve aradaki fark spread'in
   kendisi kadar büyür. Bir crack, aynı gün gerçekten kote edilmiş üç
   fiyatın aritmetiğidir; seviye cümlesi de ("14 Eylül'de 100,75 gördü")
   kote edilmiş fiyattır. Bu yüzden ölçü `auto_adjust=False` ham kapanış.
   Deponun kendi `kapanis_ham` serisiyle örtüşen pencerede karşılaştırılıp
   sapması yazılıyor — iki uç ayrışırsa hüküm kurulmadan görünsün.

2) DARBOĞAZ — IMF PortWatch günlük geçiş sayımı. Yüzdeler YUVARLANMAMIŞ
   ortalamalardan hesaplanıp öyle yazılıyor: defter yalnız yuvarlanmış
   ortalamayı taşısaydı yüzdeyi yeniden kuran her okuyucu başka bir sayı
   bulurdu (biçimlenmiş bir dizge yeniden ayrıştırılmaz).
"""
from __future__ import annotations

import json
import statistics as ist
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parent.parent
B = {"User-Agent": "Mozilla/5.0 (compatible; tto-arastirma/1.0)"}
KAT = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
       "Daily_Chokepoints_Data/FeatureServer/0")

# Taban = enerji fiyatlarındaki rejim kırılmasından ÖNCESİ (ölçüldü: 02.03.2026).
KIRILMA = "2026-03-02"
SIMDI_BAS = "2026-08-20"
# Yazının veri günü. Bugüne kadar çekip burada kesmek, koşu hangi gün
# tekrarlanırsa tekrarlansın aynı defteri üretir.
SON_GUN = "2026-09-18"
KODLAR = ["BZ=F", "CL=F", "RB=F", "HO=F", "NG=F"]


def gun(a: dict) -> str:
    t = a.get("date")
    if isinstance(t, (int, float)):
        return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")
    return str(t)[:10]


def cek(nerede: str) -> list[tuple[str, dict]]:
    """SAYFA BOYU VARSAYILMAZ, ÖLÇÜLÜR: servis 1000 kayıt veriyor ve
    `exceededTransferLimit` daha var olduğunu söylüyor. İlk yazımda döngü
    istek başına 2000 bekliyordu, ilk sayfada kırıldı ve 2026 HİÇ gelmedi —
    üstelik çıktı kusursuz görünüyordu."""
    out: list[dict] = []
    ofs = 0
    while True:
        r = requests.get(KAT + "/query", timeout=60, headers=B, params={
            "where": f"portname='{nerede}'", "outFields": "*", "f": "json",
            "orderByFields": "date ASC", "resultOffset": ofs,
            "resultRecordCount": 1000})
        js = r.json()
        ozl = js.get("features", [])
        out += [f["attributes"] for f in ozl]
        if not ozl or not js.get("exceededTransferLimit"):
            break
        ofs += len(ozl)
    return sorted(((gun(a), a) for a in out), key=lambda z: z[0])


def ort(kayit: list[dict], alan: str) -> float | None:
    v = [float(a[alan]) for a in kayit if a.get(alan) is not None]
    return ist.mean(v) if v else None


def enerji() -> dict:
    import yfinance as yf
    ham = yf.download(KODLAR, period="3y", interval="1d", progress=False,
                      auto_adjust=False, group_by="ticker", threads=True)
    seri: dict[str, dict[str, float]] = {}
    for k in KODLAR:
        c = ham[k]["Close"].dropna()
        seri[k] = {str(x.date()): float(v) for x, v in zip(c.index, c.values)
                   if str(x.date()) <= SON_GUN}
        print(f"  {k}: {len(seri[k])} gün  {min(seri[k])} → {max(seri[k])}")

    # KAPSAM: crack üç bacağın AYNI gününü ister; ortak günler alınır ve
    # düşen gün sayısı adıyla yazılır (sessiz bir kesişim, eksik bir bacağı
    # gizler).
    ortak = sorted(set.intersection(*(set(seri[k]) for k in KODLAR)))
    print(f"  ortak gün: {len(ortak)}  {ortak[0]} → {ortak[-1]}  "
          f"(düşen: {', '.join(f'{k}={len(seri[k]) - len(ortak)}' for k in KODLAR)})")

    # SÖZLEŞME SINAMASI — deponun kendi ham serisiyle örtüşen pencere.
    sapma = {}
    try:
        depo = json.loads((KOK / "bulten/onbellek/piyasa_ham.json").read_text())["seri"]
        for k in KODLAR:
            d = depo.get(k) or {}
            alan = "kapanis_ham" if d.get("kapanis_ham") else "kapanis"
            dd = dict(zip(d["tarih"], d[alan]))
            kesisim = [g for g in ortak if g in dd]
            if kesisim:
                fark = max(abs(seri[k][g] - dd[g]) / max(dd[g], 1e-9) for g in kesisim)
                sapma[k] = {"alan": alan, "gun": len(kesisim), "azami_bagil": fark}
        print("  depo karşılaştırması:", json.dumps(sapma, ensure_ascii=False))
    except Exception as ex:                                       # noqa: BLE001
        print(f"  depo karşılaştırması yapılamadı: {ex!r}")

    return {"gunler": ortak,
            "kapanis": {k: [seri[k][g] for g in ortak] for k in KODLAR},
            "depo_sapma": sapma}


def darbogaz() -> dict:
    r = requests.get(KAT + "/query", timeout=45, headers=B, params={
        "where": "1=1", "outFields": "portname", "returnDistinctValues": "true",
        "f": "json", "resultRecordCount": 100})
    adlar = sorted({f["attributes"]["portname"] for f in r.json()["features"]})
    print(f"  {len(adlar)} darboğaz: {' · '.join(adlar)}")

    out: dict[str, dict] = {}
    hurmuz: list[tuple[str, dict]] = []
    for ad in adlar:
        try:
            seri = cek(ad)
        except Exception as ex:                                   # noqa: BLE001
            print(f"  {ad}: DÜŞTÜ {ex!r}")
            continue
        if not seri:
            continue
        tb = [a for t, a in seri if t < KIRILMA]
        sn = [a for t, a in seri if t >= SIMDI_BAS]
        if not tb or not sn:
            print(f"  {ad}: taban/son penceresi boş (n={len(seri)})")
            continue
        kayit = {"n": len(seri), "bas": seri[0][0], "son": seri[-1][0]}
        for alan, etiket in (("n_total", "gemi"), ("n_tanker", "tanker")):
            a0, a1 = ort(tb, alan), ort(sn, alan)
            kayit[f"{etiket}_taban"] = a0
            kayit[f"{etiket}_simdi"] = a1
            kayit[f"{etiket}_degisim"] = (a1 / a0 * 100 - 100) if a0 else None
        out[ad] = kayit
        print(f"  {ad:<26} {kayit['gemi_taban']:8.3f} → {kayit['gemi_simdi']:7.3f} "
              f"({kayit['gemi_degisim']:+7.3f}%)  tanker {kayit['tanker_degisim']:+8.3f}%")
        if "Hormuz" in ad:
            hurmuz = seri

    aylik: dict[str, dict] = {}
    kova = defaultdict(lambda: defaultdict(list))
    for t, a in hurmuz:
        for alan in ("n_total", "n_tanker", "capacity_tanker", "capacity"):
            v = a.get(alan)
            if v is not None:
                kova[t[:7]][alan].append(float(v))
    for k in sorted(kova):
        if k < "2025-09":
            continue
        d = kova[k]
        aylik[k] = {"gemi": ist.mean(d["n_total"]), "tanker": ist.mean(d["n_tanker"]),
                    "kap_tanker": ist.mean(d["capacity_tanker"]),
                    "kapasite": ist.mean(d["capacity"]), "gun": len(d["n_total"])}

    # KAPSAM — sağ ucu eksik dolmuş bir seri "trafik çöktü" ile birebir aynı görünür.
    bugun = date.today()
    gunler = {t for t, _ in hurmuz}
    kapsam = {
        "son_kayit": hurmuz[-1][0],
        "gecikme_gun": (bugun - date.fromisoformat(hurmuz[-1][0])).days,
        "son30_dolu": sum(1 for i in range(30)
                          if (bugun - timedelta(days=i)).isoformat() in gunler),
        "toplam_gun": len(hurmuz), "bas": hurmuz[0][0],
        "olcum_gunu": bugun.isoformat(),
    }
    print("  KAPSAM:", json.dumps(kapsam, ensure_ascii=False))
    return {"darbogaz": out, "hurmuz_aylik": aylik, "kapsam": kapsam,
            "taban_sonu": KIRILMA, "simdi_bas": SIMDI_BAS}


def main() -> int:
    print("=" * 78)
    print("ENERJİ — üç yıllık HAM ön vade kapanışı")
    print("=" * 78)
    en = enerji()
    print()
    print("=" * 78)
    print("DARBOĞAZ — IMF PortWatch")
    print("=" * 78)
    db = darbogaz()
    defter = {"enerji": en, **db}
    print()
    print("DEFTER_BASI")
    print(json.dumps(defter, ensure_ascii=False, separators=(",", ":")))
    print("DEFTER_SONU")
    return 0


if __name__ == "__main__":
    sys.exit(main())
