#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reel sektör döviz pozisyonu — EVDS'ten veri çekme.

Kaynak: TCMB "Finansal Kesim Dışındaki Firmaların Döviz Varlık ve
Yükümlülükleri" (veri grubu `bie_fdvy`, aylık, Aralık 2002'den beri).

Seri kodları KODA GÖMÜLMEZ: ilk koşuda grubun seri listesi EVDS'ten çekilir,
adlarıyla birlikte data/seriler.json'a yazılır ve hangi kolonun ne olduğu
ADDAN eşlenir. TCMB bir serinin adını/kodunu değiştirirse eşleme düşer ve hat
sessizce yanlış kolon okumak yerine açık hata verir — tazeleme hattındaki
"ölü kalıp" ilkesinin buradaki karşılığı.

Anahtar sırası bütün hatlarla aynı: TTO_EVDS_KEY → .evds_key (proje, kök,
TCMBNetRezerv). Anahtar üstbilgide gider, URL'de değil.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

BURASI = Path(__file__).resolve().parent
DATA = BURASI / "data"
BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
GRUP = "bie_fdvy"
UA = "Mozilla/5.0 (TTO Trading veri hattı)"


def anahtar() -> str:
    a = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if a:
        return a
    kok = BURASI.parent.parent
    for yol in (BURASI / ".evds_key", kok / ".evds_key",
                kok / "Aktarılacak Projeler" / "TCMBNetRezerv" / ".evds_key"):
        if yol.exists():
            a = yol.read_text(encoding="utf-8").strip()
            if a:
                return a
    raise SystemExit("EVDS anahtarı yok: TTO_EVDS_KEY ya da .evds_key gerekli.")


def _cek(url: str, deneme: int = 3):
    son = None
    for i in range(deneme):
        try:
            req = urllib.request.Request(url, headers={"key": anahtar(), "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:                                   # noqa: BLE001
            son = ex
            if i < deneme - 1:
                time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"EVDS isteği düştü: {son}") from son


# Kolon → seri ADI kalıbı. Kod değil AD eşlenir; adlar metaveriyle birlikte
# data/seriler.json'a yazılır ki eşleme her koşuda denetlenebilir olsun.
KALIPLAR = {
    "varlik_toplam": r"^Varlıklar$|^VARLIKLAR$|Varlık.*Toplam|Toplam Varlık",
    "yukumluluk_toplam": r"^Yükümlülükler$|^YÜKÜMLÜLÜKLER$|Yükümlülük.*Toplam|Toplam Yükümlülük",
    "net_pozisyon": r"Net Döviz Pozisyon",
    "kv_varlik": r"Kısa Vadeli Varlık",
    "kv_yukumluluk": r"Kısa Vadeli Yükümlülük",
    "kv_net": r"Kısa Vadeli Net Döviz Pozisyon",
    "ihracat_alacak": r"İhracat Alacak",
    "ithalat_borc": r"İthalat Borç",
    "yi_kredi": r"Yurt İçi.*Kredi|Yurt İçinden Sağlanan.*Kredi",
    "yd_kredi": r"Yurt Dışı.*Kredi|Yurt Dışından Sağlanan.*Kredi",
    "mevduat": r"Mevduat|DTH",
}


def kesfet() -> dict:
    """Grubun seri listesini çek, kalıplara eşle, data/seriler.json'a yaz."""
    ham = _cek(f"{BASE}/serieList/type=json&code={GRUP}")
    seriler = ham if isinstance(ham, list) else ham.get("items", [])
    dokum = [{"kod": s.get("SERIE_CODE"), "ad": (s.get("SERIE_NAME") or "").strip()}
             for s in seriler if s.get("SERIE_CODE")]
    esleme, kullanilmis = {}, set()
    for kolon, kalip in KALIPLAR.items():
        for s in dokum:
            if s["kod"] in kullanilmis:
                continue
            if re.search(kalip, s["ad"], re.I):
                esleme[kolon] = s
                kullanilmis.add(s["kod"])
                break
    DATA.mkdir(exist_ok=True)
    (DATA / "seriler.json").write_text(json.dumps(
        {"_aciklama": "bie_fdvy grubunun seri dökümü ve kolon eşlemesi. Eşleme "
                      "AD kalıbıyla yapılır; TCMB adı değiştirirse eşleme düşer ve "
                      "hat açık hata verir — sessiz yanlış kolon okunmaz.",
         "grup": GRUP, "esleme": esleme, "tum_seriler": dokum},
        ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    eksik = [k for k in ("varlik_toplam", "yukumluluk_toplam", "net_pozisyon")
             if k not in esleme]
    if eksik:
        raise SystemExit(f"KEŞİF EKSİK — zorunlu kolonlar eşlenemedi: {eksik}. "
                         f"data/seriler.json'daki adlara bakıp KALIPLAR güncellenmeli.")
    return esleme


def indir(esleme: dict):
    import pandas as pd
    kodlar = [v["kod"] for v in esleme.values()]
    url = (f"{BASE}/series={('-'.join(kodlar))}&startDate=01-12-2002"
           f"&endDate=01-12-2099&type=json&formulas=0")
    ham = _cek(url)
    kayitlar = ham.get("items", ham) if isinstance(ham, dict) else ham
    df = pd.DataFrame(kayitlar)
    ters = {v["kod"].replace(".", "_"): k for k, v in esleme.items()}
    df = df.rename(columns=ters)
    df["tarih"] = pd.to_datetime(df["Tarih"], format="%m-%Y", errors="coerce")
    kolonlar = ["tarih"] + [k for k in esleme if k in df.columns]
    df = df[kolonlar].dropna(subset=["tarih"]).sort_values("tarih")
    for k in esleme:
        if k in df.columns:
            df[k] = pd.to_numeric(df[k], errors="coerce")
    df.to_csv(DATA / "fdvy.csv", index=False)
    print(f"fdvy.csv: {len(df)} satır, {df['tarih'].min():%Y-%m} → {df['tarih'].max():%Y-%m}")


if __name__ == "__main__":
    esleme = kesfet()
    print("eşlenen kolonlar:", ", ".join(esleme))
    indir(esleme)
