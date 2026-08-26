#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reel sektör döviz pozisyonu — hesap katmanı.

data/fdvy.csv yoksa hat İLK KOŞUSUNU BEKLİYOR demektir: ozet.json'a yalnız o
durum yazılır ve grafikler yer tutucu olarak üretilir. Ölçülmemiş sayı
uydurulmaz; sayfa 'taslak' rozetiyle yayımlanır ve ilk başarılı veri
koşusunda kendiliğinden dolar.
"""
from __future__ import annotations

import json
from pathlib import Path

BURASI = Path(__file__).resolve().parent
DATA = BURASI / "data"
KOK = BURASI.parent.parent
REZERV_OZET = KOK / "site" / "public" / "projeler" / "tcmb-net-rezerv" / "ozet.json"


def bekliyor_ozet() -> dict:
    return {"_durum": "ilk koşu bekleniyor",
            "_aciklama": "Veri hattı henüz EVDS'ten ilk çekimini yapmadı. "
                         "CI'da veri_cek.py başarıyla koşunca bu dosya gerçek "
                         "ölçümlerle dolacak ve sayfa taslak rozetinden çıkacak."}


def hesapla():
    import pandas as pd
    y = DATA / "fdvy.csv"
    if not y.exists():
        return None, bekliyor_ozet()
    d = pd.read_csv(y, parse_dates=["tarih"]).set_index("tarih").sort_index()
    # BOŞ DOSYA "veri var" DEĞİLDİR. 26.08'de veri_cek.py tarih biçimini
    # ayrıştıramayıp yalnız BAŞLIK satırından ibaret bir CSV yazdı; burası
    # dosyanın varlığını veri sanıp `_tarih: ""` olan bir özet üretti — yani
    # "ilk koşu bekleniyor" diyen dürüst yer tutucudan DAHA KÖTÜ bir çıktı:
    # sayfa veri varmış gibi görünüyor ama hiçbir sayı yok.
    if d.empty:
        return None, bekliyor_ozet()

    def son(kolon, ondalik=1):
        if kolon not in d.columns:
            return None, ""
        s = d[kolon].dropna()
        return (None, "") if s.empty else (round(float(s.iloc[-1]) / 1000, ondalik),
                                           f"{s.index[-1]:%m.%Y}")   # mn → mlr USD

    ozet = {}
    for k in ("varlik_toplam", "yukumluluk_toplam", "net_pozisyon",
              "kv_varlik", "kv_yukumluluk", "kv_net"):
        deger, tarih = son(k)
        if deger is not None:
            ozet[k] = deger
            ozet[f"{k}_tarih"] = tarih
    ozet["_tarih"] = ozet.get("net_pozisyon_tarih", "")

    # 12 aylık değişimler (mlr USD)
    for k in ("net_pozisyon", "kv_net"):
        if k in d.columns and d[k].dropna().shape[0] > 12:
            s = d[k].dropna()
            ozet[f"{k}_d12a"] = round(float(s.iloc[-1] - s.iloc[-13]) / 1000, 1)

    # Rezerve oran: net açığın brüt rezerve bölümü — kırılganlığın ölçeği.
    try:
        rez = json.loads(REZERV_OZET.read_text(encoding="utf-8"))
        brut = rez.get("h_brut")
        if brut and ozet.get("net_pozisyon") is not None:
            ozet["acik_rezerv_orani"] = round(100 * abs(ozet["net_pozisyon"]) / brut, 1)
            ozet["acik_rezerv_tarih"] = rez.get("h_tarih", "")
    except (OSError, ValueError):
        pass
    return d, ozet


if __name__ == "__main__":
    d, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if d is None:
        print("veri yok — 'ilk koşu bekleniyor' özeti yazıldı")
    else:
        for k, v in ozet.items():
            if not k.startswith("_"):
                print(f"  {k:24s} {v}")
