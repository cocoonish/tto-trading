#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAĞIT VE OIS DERSİ — girdi arşivini BİR KEZ dondurur.

Ders yayımlandığı günün ölçümüdür (karar 08.09.2026): figürler ve metindeki
sayılar CANLI hatlardan okunamaz — DİBS hattının `metrik.csv`'si her koşuda
yeniden yazılır ve ders bir gün sessizce başka bir eğriyi anlatmaya başlardı
("BİR REHBERİN GİRDİSİ, KAYAN BİR PENCEREDEN OKUNAMAZ"). Bu betik ölçümün
ihtiyaç duyduğu sütunları çıpa gününe kadar keser, `veri/` altına sıkıştırıp
yazar ve her dosyanın özünü (sha256) künyeye koyar. `olcum.py` yalnız buradan
okur, `dogrula.py` özleri her yayın kapısında yeniden sınar.

Var olan arşivin ÜSTÜNE YAZMAZ: yeni bir pencere yeni bir derstir ve metnin
sayıları onunla birlikte yeniden yazılır. Bilinçli yenileme için `--yeniden`.

Koşum:  python3 hazirla.py [--yeniden]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
DIBS = KOK / "Aktarılacak Projeler/DIBS/data"

CIPA = "2026-09-22"          # eğrinin son günü (TCMB gösterge değerleri)
DUGUM = ["n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y", "n9y"]


def _gz_yaz(df: pd.DataFrame, ad: str) -> dict:
    # CSV metni sabit biçimle yazılır (ondalık 6 basamak): aynı girdi her
    # seferinde BİREBİR aynı baytları üretsin, öz yalnız veri değişince değişsin.
    metin = df.to_csv(float_format="%.6f", lineterminator="\n")
    ham = metin.encode("utf-8")
    # gzip zaman damgası 0: sıkıştırılmış dosya da deterministik kalır.
    tampon = io.BytesIO()
    with gzip.GzipFile(fileobj=tampon, mode="wb", mtime=0) as g:
        g.write(ham)
    (VERI / ad).write_bytes(tampon.getvalue())
    return {"sha256": hashlib.sha256(ham).hexdigest(), "satir": int(len(df)),
            "ilk": str(df.index.min().date()), "son": str(df.index.max().date())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yeniden", action="store_true",
                    help="var olan arşivin üstüne yaz (yeni bir ders penceresi demektir)")
    a = ap.parse_args()
    if (VERI / "kunye.json").exists() and not a.yeniden:
        print("arşiv zaten var — üstüne yazılmaz (bilinçli yenileme: --yeniden)")
        return 0
    VERI.mkdir(parents=True, exist_ok=True)

    m = pd.read_csv(DIBS / "metrik.csv", index_col=0, parse_dates=True)
    egri = m.loc[:CIPA, DUGUM + ["r2y"]]
    egri = egri[egri.index.dayofweek < 5]
    g = pd.read_csv(DIBS / "gunluk.csv", index_col=0, parse_dates=True)
    fon = g.loc[:CIPA, ["tlref", "politika", "koridor_alt", "koridor_ust", "aofm"]]

    sys.path.insert(0, str(KOK / "bulten"))
    import ppk_endeks  # noqa: E402  (karar arşivi: depodaki TCMB duyuruları)
    ks = ppk_endeks.kararlar()
    ppk = pd.DataFrame([{"tarih": pd.Timestamp(k["tarih"]), "politika": float(k["politika"])}
                        for k in ks]).set_index("tarih").sort_index()
    ppk = ppk.loc[:CIPA]

    # Hazine ihale sonuçları (2020 → çıpa): yalnız dersin kullandığı sütunlar
    ih = pd.read_csv(KOK / "Aktarılacak Projeler/hazineihrac/hazine_ihale_verileri.csv")
    ih["tarih"] = pd.to_datetime(ih["İhale Tarihi"], dayfirst=True)
    ih = ih[ih["tarih"] <= CIPA]
    ihale = pd.DataFrame({
        "tur": ih["Senet Tanımı"], "vade_yil": ih["Vade (Yıl)"],
        "rot": ih["ROT Toplam(Gerçekleşme)"],
        "rot_kamu": ih["ROT Kamu(Gerçekleşme)"].fillna(0),     # boş = o ihalede kamu ROT'u yok
        "rot_py": ih["ROT Piyasa Yapıcılar(Gerçekleşme)"].fillna(0),
        "ihale_teklif": ih["İhale(Teklif)"],
        "ihale_satis": ih["İhale(Gerçekleşme)"], "toplam": ih["Toplam(Gerçekleşme)"],
        "bilesik": ih["Ortalama Yıllık Bileşik(Gerçekleşme)"],
    })
    ihale.index = ih["tarih"]
    ihale = ihale.sort_index()
    ihale.index.name = "tarih"

    kunye = {
        "cipa": CIPA,
        "not": ("Ders girdisi. Eğri: TCMB DİBS gösterge değerlerinden sıfır kuponlu "
                "spot getiriler (yıllık bileşik, ACT/365; düğümler strip getirilerinin "
                "vade ekseninde doğrusal ara değeri). Fonlama: TLREF (basit, ACT/365), "
                "politika faizi, koridor ve AOFM. PPK: depodaki karar arşivi. İhale: Hazine "
                "ihale sonuçları (2020 → çıpa)."),
        "dosyalar": {
            "egri_gunluk.csv.gz": _gz_yaz(egri, "egri_gunluk.csv.gz"),
            "fonlama_gunluk.csv.gz": _gz_yaz(fon, "fonlama_gunluk.csv.gz"),
            "ppk_kararlari.csv.gz": _gz_yaz(ppk, "ppk_kararlari.csv.gz"),
            "ihale.csv.gz": _gz_yaz(ihale, "ihale.csv.gz"),
        },
    }
    (VERI / "kunye.json").write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n",
                                     encoding="utf-8")
    for ad, k in kunye["dosyalar"].items():
        print(f"  ✓ {ad}: {k['satir']} satır · {k['ilk']} → {k['son']} · {k['sha256'][:12]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
