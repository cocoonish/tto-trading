# -*- coding: utf-8 -*-
"""Canli ozet — output/ozet.json.

Sayfa metnindeki OYNAK sayilar buradan beslenir (CLAUDE.md kural 5):
MDX'te <Deger proje="yiyecek-hizmetleri-marj" anahtar="..."> ile okunur.
Tarihsel/metodolojik sabitler (agirliklar, 2013 capasi, replikasyon dogrulama
sayilari) sayfada STATIK kalir — onlar veri tazelendikce degismez.

Butun degerler output/ altindaki uretilmis dosyalardan OKUNUR; elle sayi yazilmaz.
Bir deger kaynakta bulunamazsa anahtar ATLANIR ve stderr'e uyari basilir.
"""
import json
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")
XLSX = os.path.join(OUT, "seriler.xlsx")

KONSEPTLER = ["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"]


def _uyar(m):
    print(f"UYARI: {m}", file=sys.stderr)


def main():
    ozet = {}

    # --- Fiyat/maliyet orani: guncel + uzun donem ortalama ---
    oran = pd.read_excel(XLSX, sheet_name="Fiyat_maliyet_orani", index_col=0)
    oran.index = pd.to_datetime(oran.index)
    son = oran.dropna(how="all").iloc[-1]
    ozet["_tarih"] = oran.dropna(how="all").index[-1].strftime("%m.%Y")
    ozet["donem"] = oran.dropna(how="all").index[-1].strftime("%B %Y")
    for ay_en, ay_tr in [("January", "Ocak"), ("February", "Şubat"), ("March", "Mart"),
                         ("April", "Nisan"), ("May", "Mayıs"), ("June", "Haziran"),
                         ("July", "Temmuz"), ("August", "Ağustos"), ("September", "Eylül"),
                         ("October", "Ekim"), ("November", "Kasım"), ("December", "Aralık")]:
        ozet["donem"] = ozet["donem"].replace(ay_en, ay_tr)

    # Uzun donem ortalama: notun "normal" donemi 2013-2022
    uzun_pencere = oran.loc["2013-01-01":"2022-12-31"]
    for k in KONSEPTLER:
        if k in oran.columns:
            ozet[f"oran_{k}"] = round(float(son[k]), 2)
            ozet[f"uzun_{k}"] = round(float(uzun_pencere[k].mean()), 2)
        else:
            _uyar(f"Fiyat_maliyet_orani'nda '{k}' sutunu yok")

    # --- Iki yillik maliyet artisi (katki tablosunun TOPLAM sutunu) ---
    kat_yol = os.path.join(OUT, "katki_ayristirma.csv")
    if os.path.exists(kat_yol):
        kat = pd.read_csv(kat_yol, index_col=0)
        toplam_kol = next((c for c in kat.columns if c.upper() == "TOPLAM"), None)
        if toplam_kol:
            ozet["maliyet_artisi_min"] = round(float(kat[toplam_kol].min()), 1)
            ozet["maliyet_artisi_max"] = round(float(kat[toplam_kol].max()), 1)
            for k in KONSEPTLER:
                if k in kat.index:
                    ozet[f"maliyet_artisi_{k}"] = round(float(kat.loc[k, toplam_kol]), 1)
            # en buyuk iki kalem katkisi (ortalama)
            kalemler = [c for c in kat.columns if c.upper() != "TOPLAM"]
            ort = kat[kalemler].mean().sort_values(ascending=False)
            ozet["katki_lider_kalem"] = str(ort.index[0])
            ozet["katki_lider_puan"] = round(float(ort.iloc[0]), 1)
        else:
            _uyar("katki_ayristirma.csv'de TOPLAM sutunu yok")
    else:
        _uyar("katki_ayristirma.csv yok")

    # --- Ima edilen karlilik (merkez senaryo) ---
    try:
        merkez = pd.read_excel(XLSX, sheet_name="Ima_marj_%22.5_merkez", index_col=0)
        m_son = merkez.dropna(how="all").iloc[-1]
        for k in KONSEPTLER:
            if k in merkez.columns:
                ozet[f"marj_{k}"] = round(float(m_son[k]), 1)
    except Exception as exc:
        _uyar(f"ima marj sekmesi okunamadi: {exc}")

    # --- Duyarlilik: guncel oranin 18 senaryodaki araligi ---
    duy_yol = os.path.join(OUT, "duyarlilik.csv")
    if os.path.exists(duy_yol):
        duy = pd.read_csv(duy_yol)
        ozet["senaryo_adet"] = int(len(duy))
        for k in KONSEPTLER:
            kol = f"oran26_{k}"
            if kol in duy.columns:
                ozet[f"duy_min_{k}"] = round(float(duy[kol].min()), 2)
                ozet[f"duy_max_{k}"] = round(float(duy[kol].max()), 2)
    else:
        _uyar("duyarlilik.csv yok")

    yol = os.path.join(OUT, "ozet.json")
    json.dump(ozet, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(ozet, ensure_ascii=False))
    return ozet


if __name__ == "__main__":
    main()
