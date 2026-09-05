# -*- coding: utf-8 -*-
"""Yurt içi yerleşiklerin YP mevduatı — KEŞİF katmanı (EVDS3).

NİYE VAR. Bu hattın sorusu "DTH ne kadar arttı" değil, "artışın ne kadarı
GERÇEK giriş, ne kadarı DEĞERLEME": DTH milyon USD cinsinden yayımlanıyor ama
sepetin içinde euro, sterlin ve ALTIN var; euro dolara karşı değer kazandığında
USD karşılığı hiçbir yeni para girmeden yükseliyor. Ayrıştırma ancak sepetin
BİLEŞİMİ ve pariteler ölçülebiliyorsa kurulabilir.

Bu yüzden hat kurulmadan önce ÜÇ şey ölçülür — tahmin edilmez:
  1. Haftalık tablolarda GERÇEK KİŞİ / TÜZEL KİŞİ kırılımı var mı, hangi kodda?
  2. KIYMETLİ MADEN depo hesapları ayrı bir satır mı, hangi birimde?
  3. Sepet bileşimi (USD/EUR/maden/diğer payları) hangi frekansta ve ne kadar
     geriye gidiyor?

"Bulamadım" ile "yok" aynı şey değildir (CLAUDE.md): bu betik kod TAHMİN ETMEZ,
önce `serieList` ile GRUBUN TAMAMINI ister ve ne bulduğunu adıyla döker. Eşleşme
tutmazsa grubun GERÇEK seri adları raporlanır — yoksa her düzeltme için ayrı bir
keşif koşusu gerekir.

Koşum (yalnız iş akışından; bu oturumların ağ vekili tcmb.gov.tr'yi kapatıyor):
    Keşif (veri kaynağı ölçümü) → betik: Aktarılacak Projeler/YPMevduat/kesif.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.request

PROJE = pathlib.Path(__file__).resolve().parent
KOK = PROJE.parent.parent
VERI = PROJE / "data"
VERI.mkdir(parents=True, exist_ok=True)

BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

_ADAYLAR = [PROJE / ".evds_key", KOK / ".evds_key",
            KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key"]


def anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    for yol in _ADAYLAR:
        if yol.exists() and yol.read_text(encoding="utf-8").strip():
            return yol.read_text(encoding="utf-8").strip()
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
    print(f"  ! çekilemedi: {yol[:90]} → {type(son).__name__}: {son}", flush=True)
    return None


# --------------------------------------------------------------------------- 1. katalog
# ARANAN KAVRAMLAR. Kod uzayı DAR tutuluyor: ıskalanan her kod istemcinin
# yeniden deneme bütçesini yakar (CLAUDE.md). Bunlar seri KODU değil, seri
# ADINDA aranacak Türkçe kavramlar — katalog ne veriyorsa onu görürüz.
KAVRAMLAR = {
    "gercek_tuzel": re.compile(r"gerçek kişi|tüzel kişi|gerçek ve tüzel", re.I),
    "maden": re.compile(r"kıymetli maden|altın depo|maden depo", re.I),
    "yp_mevduat": re.compile(r"yp|yabancı para|döviz tevdiat|dth", re.I),
    "usd_birim": re.compile(r"milyon usd|milyon abd|usd\)", re.I),
}

# Haftalık Para ve Banka İstatistikleri aile kökü + sepet bileşimi grubu.
# hpbitablo2 zaten Kredi hattında kullanılıyor (TP.HPBITABLO2.10 = YP mevduat,
# milyon USD) — bu hattın manşet serisi o. Aranan EK kırılım aynı ailenin
# başka tablolarında olabilir, o yüzden 1–7 birden taranıyor.
GRUPLAR = [f"bie_hpbitablo{i}" for i in range(1, 8)] + ["bie_zorundth"]


def grup_serileri(grup: str) -> list[dict]:
    d = cek(f"serieList/type=json&code={grup}")
    if not d:
        return []
    if isinstance(d, dict):
        d = d.get("items") or d.get("serieList") or []
    return d if isinstance(d, list) else []


def main() -> int:
    print("=" * 74)
    print("  YP MEVDUATI — KAYNAK YOKLAMASI (EVDS3)")
    print("=" * 74, flush=True)

    bulgu: dict = {"gruplar": {}, "adaylar": {}, "kavram": {k: [] for k in KAVRAMLAR}}

    for grup in GRUPLAR:
        seriler = grup_serileri(grup)
        print(f"\n── {grup}: {len(seriler)} seri", flush=True)
        if not seriler:
            print("   (boş ya da erişilemedi — grup kodu yanlış OLABİLİR)", flush=True)
            continue
        birimler = {str(s.get("BIRIMI") or s.get("birimi") or "?") for s in seriler}
        bulgu["gruplar"][grup] = {"n": len(seriler), "birimler": sorted(birimler)}
        print(f"   birimler: {', '.join(sorted(birimler))[:150]}", flush=True)
        for s in seriler:
            kod = str(s.get("SERIE_CODE") or s.get("serieCode") or "")
            ad = str(s.get("SERIE_NAME") or s.get("serieName") or "")
            birim = str(s.get("BIRIMI") or s.get("birimi") or "")
            if not kod:
                continue
            for kavram, kalip in KAVRAMLAR.items():
                if kalip.search(ad) or kalip.search(birim):
                    bulgu["kavram"][kavram].append({"kod": kod, "ad": ad, "birim": birim,
                                                    "grup": grup})
        # GRUBUN TAMAMI dökülür: eşleşme tutmazsa "neyin bulunabileceği" görünsün.
        for s in seriler:
            kod = str(s.get("SERIE_CODE") or s.get("serieCode") or "")
            ad = str(s.get("SERIE_NAME") or s.get("serieName") or "")
            birim = str(s.get("BIRIMI") or s.get("birimi") or "")
            print(f"     {kod:26s} {birim:16s} {ad[:78]}", flush=True)

    print("\n" + "=" * 74)
    print("  KAVRAM EŞLEŞMELERİ")
    print("=" * 74, flush=True)
    for kavram, liste in bulgu["kavram"].items():
        print(f"\n▶ {kavram}: {len(liste)} eşleşme", flush=True)
        for x in liste[:40]:
            print(f"   {x['kod']:26s} [{x['grup']}] {x['birim']:14s} {x['ad'][:70]}",
                  flush=True)

    # ----------------------------------------------------------------- 2. yoklama
    # Eşleşen her kodu GERÇEKTEN çağır: dönen son gözlem, tarihi, gözlem sayısı.
    # Çağrılmamış kod hatta GİRMEZ.
    adaylar = []
    for liste in bulgu["kavram"].values():
        for x in liste:
            if x["kod"] not in [a["kod"] for a in adaylar]:
                adaylar.append(x)
    print("\n" + "=" * 74)
    print(f"  SERİ YOKLAMASI — {len(adaylar)} aday çağrılıyor")
    print("=" * 74, flush=True)
    for x in adaylar[:60]:
        d = cek(f"series={x['kod']}&startDate=01-01-2024&endDate=31-12-2026&type=json")
        items = (d or {}).get("items") or []
        kolon = x["kod"].replace(".", "_")
        dolu = [i for i in items if str(i.get(kolon, "")).strip() not in ("", "null", "None")]
        if dolu:
            son = dolu[-1]
            x.update({"n": len(dolu), "ilk": dolu[0].get("Tarih"),
                      "son_tarih": son.get("Tarih"), "son_deger": son.get(kolon)})
            print(f"  ✓ {x['kod']:26s} n={len(dolu):4d}  {dolu[0].get('Tarih')} → "
                  f"{son.get('Tarih')}  son={son.get(kolon)}", flush=True)
        else:
            x.update({"n": 0})
            print(f"  ✗ {x['kod']:26s} veri YOK (kod var ama boş)", flush=True)
    bulgu["adaylar"] = adaylar

    yol = VERI / "kesif.json"
    yol.write_text(json.dumps(bulgu, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nyazıldı: {yol}", flush=True)
    print(f"ÖZET: {len(bulgu['gruplar'])} grup okundu · "
          f"{sum(len(v) for v in bulgu['kavram'].values())} kavram eşleşmesi · "
          f"{sum(1 for a in adaylar if a.get('n'))} seri veri döndürdü", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
