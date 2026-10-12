#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — üçüncü arşiv geçişi: CNBC'nin İLK geçişte BOŞ
döndürdüğü semboller ve BOŞ dönen beş yıllık parçalar.

İlk geçişte (12.10.2026 13:47 UTC) on üç sembolün yoklaması "durum 200, bar 0"
döndü — aralarında Brent, altın, EUR/USD, USD/JPY ve ABD 2 yıllık. Aynı semboller
2 Ekim'deki makro dersi geçişinde aynı uçtan bar vermişti; yani "200 ve boş
gövde" kaynağın o anki yanıtıdır, sembolün yokluğu değil ("bulamadım" ile "yok"
aynı şey değildir). Bu geçiş yoklamayı üç kez, aralıklı ve iki ayrı pencereyle
dener; yine boş dönen sembol rapora adıyla yazılır.

İkinci kusur aynı sınıftan: sembolü tutan araçların 59 beş yıllık parçası boş
geldi (ör. ABD 10 yıllık 2000–2004, 2010–2019; sterlin 2015–2019) ve yıllık bar
sayımı bunu gösterdi — boş parça, 21 günlük pencereyi bir boşluğun üstünden
ölçtürür. İlk geçişin raporundaki (`rapor_cnbc.json`) her boş parça yeniden
istenir; kaynağın gerçekten kapsamadığı yıllar (ör. CNH 2010 öncesi) yine boş
döner ve adıyla kalır.

Yardımcılar ve ilkeler `arsiv_brent.py` başlığında; künye `kunye_cnbc2.json`.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import timedelta

import arsiv_brent as ab

YENIDEN = {
    "brent": ["@LCO.1", "@BRN.1"], "altin": ["@GC.1"], "dogalgaz": ["@NG.1"],
    "eur": ["EUR="], "jpy": ["JPY="], "sek": ["SEK="], "idr": ["IDR="], "huf": ["HUF="],
    "us3m": ["US3M"], "us2y": ["US2Y"], "de10y": ["DE10Y-DE"], "jp10y": ["JP10Y-JP"],
    "gazyagi_gasoil": ["@LGO.1", "@GO.1"], "ttf": ["@TFM.1", "@TTF.1"],
    "sx5e": [".STOXX50E", ".SX5E"], "dem": ["DEM="],
}
UZUN = {"brent", "altin", "jpy", "dem", "us2y", "us3m"}


def _yokla(sem: str) -> tuple[int, int]:
    """Üç deneme, iki pencere (son iki yıl · son 60 gün); bar veren ilk yanıt kazanır."""
    yarin = (ab.SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    pencereler = [(ab.SIMDI - timedelta(days=730)).strftime("%Y%m%d"),
                  (ab.SIMDI - timedelta(days=60)).strftime("%Y%m%d")]
    son_d = 0
    for deneme in range(3):
        for bas in pencereler:
            try:
                d, gv = ab.al(ab._cnbc_url(sem, bas, f"{yarin}000000"), sn=30, deneme=1)
            except RuntimeError:
                d, gv = 0, b""
            son_d = d
            n = ab._bar_sayisi(gv) if d == 200 else 0
            if n > 20:
                return d, n
            time.sleep(2.0)
        time.sleep(4.0 * (deneme + 1))
    return son_d, 0


@ab.kaynak("CNBC yeniden")
def cnbc_yeniden() -> dict:
    sonuc = {}
    yarin = (ab.SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    for arac, adaylar in YENIDEN.items():
        if ab.kalan() < 240:
            sonuc[arac] = {"durum": "bütçe doldu"}
            continue
        secilen, yoklama = None, {}
        for sem in adaylar:
            d, n = _yokla(sem)
            yoklama[sem] = {"durum": d, "bar": n}
            if n:
                secilen = sem
                break
        if not secilen:
            sonuc[arac] = {"durum": "kapalı", "yoklama": yoklama}
            print(f"   {arac}: yine boş {yoklama}", flush=True)
            continue
        ilk = ab.CNBC_ILK_UZUN if arac in UZUN else ab.CNBC_ILK
        parcalar = {}
        for bas in range(ilk, ab.SIMDI.year + 1, 5):
            son = f"{bas + 4}1231235959" if bas + 4 < ab.SIMDI.year else f"{yarin}000000"
            u = ab._cnbc_url(secilen, f"{bas}0101", son)
            n, d = 0, 0
            for deneme in range(3):
                try:
                    d, gv = ab.al(u, sn=40)
                except RuntimeError:
                    d, gv = 0, b""
                n = ab._bar_sayisi(gv) if d == 200 else 0
                if n or bas < 2000:          # 2000 öncesi boş parça kaynağın kapsamıdır
                    break
                time.sleep(3.0 * (deneme + 1))
            if n:
                ab.yaz(f"cnbc/{arac}__{ab._dosya_adi(secilen)}_{bas}.json.gz", gv, u, d,
                       not_=f"{arac} · {secilen}")
            parcalar[bas] = {"durum": d, "bar": n}
            time.sleep(0.4)
        sonuc[arac] = {"durum": "tamam", "sembol": secilen, "yoklama": yoklama, "parcalar": parcalar}
        print(f"   {arac}: {secilen} · " + ", ".join(f"{k}:{v['bar']}" for k, v in parcalar.items()), flush=True)
    return sonuc


@ab.kaynak("CNBC boş parçalar")
def cnbc_parcalar() -> dict:
    rp = ab.HAM / "rapor_cnbc.json"
    if not rp.exists():
        raise RuntimeError("rapor_cnbc.json yok")
    ilk = list(json.loads(rp.read_text(encoding="utf-8")).values())[0]["CNBC"]
    yarin = (ab.SIMDI + timedelta(days=1)).strftime("%Y%m%d")
    sonuc = {}
    for arac, v in ilk.items():
        if not isinstance(v, dict) or v.get("durum") != "tamam":
            continue
        sem = v["sembol"]
        alt = ab.CNBC_ILK_UZUN if arac in ab.UZUN else ab.CNBC_ILK
        for yil, parca in v["parcalar"].items():
            bas = int(yil)
            if bas < alt or not isinstance(parca, dict) or parca.get("bar", 0) > 0:
                continue
            if ab.kalan() < 120:
                sonuc[f"{arac}:{yil}"] = "bütçe doldu"
                continue
            son = f"{bas + 4}1231235959" if bas + 4 < ab.SIMDI.year else f"{yarin}000000"
            u = ab._cnbc_url(sem, f"{bas}0101", son)
            n, d = 0, 0
            for deneme in range(3):
                try:
                    d, gv = ab.al(u, sn=40)
                except RuntimeError:
                    d, gv = 0, b""
                n = ab._bar_sayisi(gv) if d == 200 else 0
                if n:
                    break
                time.sleep(3.0 * (deneme + 1))
            if n:
                ab.yaz(f"cnbc/{arac}__{ab._dosya_adi(sem)}_{bas}.json.gz", gv, u, d, not_=f"{arac} · {sem}")
            sonuc[f"{arac}:{yil}"] = {"durum": d, "bar": n}
            print(f"   {arac} {yil}: {n} bar", flush=True)
            time.sleep(0.4)
    return sonuc


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    cnbc_yeniden()
    cnbc_parcalar()
    ab.kaydet("cnbc2")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
