#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Makroihtiyati çerçevenin ölçülen izi — hesap katmanı.

Bu sayfa düzenleme METİNLERİNİ değil, düzenlemelerin VERİDEKİ ayak izini
ölçer. Kredi hattının kendi sayfasında gerekçelendirilmiş bir yasak var:
tebliğle değişen tarih ve oranlar koda gömülmez, çünkü bir sonraki duyuruda
sessizce yanlışa dönerler. Bu hat o yasağa uyar — sınırın kendisini çizmez,
sınırın bıraktığı üç izi çizer:

  ayrışma    Aynı ekonomide tüketici kredisi %43, ticari %19 büyüyorsa bu
             piyasa sonucu değil, kanal bazlı tavanların doğrudan ürünüdür.
  kaçak      Tavanın kapsamadığı kanala akış: bireysel kredi kartı büyümesinin
             tüketici kredisinden, kurumsal kartın ticariden farkı.
  fiyat      Miktar kısıtı fiyata yansır: ihtiyaç kredisi faizinin politika
             faizinden makası, kısıtın gölge fiyatıdır.

Düzenleme defteri (duzenlemeler.json) elle bakılan ayrı bir DOSYADIR, kod
değil: her kaydın kaynağı ve doğrulama durumu vardır ve sayfa yalnız
"dogrulandi" işaretli kayıtları basar. Doğrulanmamış tarih yayımlamak, bu
sitenin uydurma yasağının ihlalidir.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent.parent
KREDI = KOK / "Aktarılacak Projeler" / "Kredi" / "data"
FONLAMA = KOK / "Aktarılacak Projeler" / "Fonlama" / "data"


def yukle():
    h = pd.read_csv(KREDI / "metrik_haftalik.csv", parse_dates=["tarih"]).set_index("tarih")
    f = pd.read_csv(KREDI / "faiz.csv", parse_dates=["tarih"]).set_index("tarih")
    b = pd.read_csv(KREDI / "ceyreklik.csv", parse_dates=["tarih"]).set_index("tarih")
    g = pd.read_csv(FONLAMA / "gunluk.csv", parse_dates=["tarih"],
                    usecols=["tarih", "politika"]).set_index("tarih")
    g["politika"] = g["politika"].ffill()          # adım fonksiyonu (bkz. Carry hattı)
    # Faiz serisi haftalık (cuma); politika o güne eşlenir.
    # faiz.csv kendi 'politika' kolonunu taşıyor; kaynak tek olsun diye o
    # atılır, Fonlama'nın günlük ve ffill'li serisi kullanılır.
    f = f.drop(columns=["politika"], errors="ignore").join(g, how="left")
    f["politika"] = f["politika"].ffill()
    for kanal in ("ihtiyac", "ticari_tl", "konut"):
        f[f"makas_{kanal}"] = f[f"f_{kanal}"] - f["politika"]
    f["makas_mevduat"] = f["mev_tl"] - f["politika"]
    # Kaçak: kapsam dışı kanalın kapsanan kanaldan büyüme farkı
    h["kacak_bkk"] = h["g_bkk_13y"] - h["g_tuketici_13y"]
    h["kacak_kurumsal_kart"] = h["g_kurumsal_kart_13y"] - h["g_ticari_13y"]
    h["ayrisma"] = h["g_tuketici_13y"] - h["g_ticari_13y"]
    return h, f, b


def defter() -> dict:
    y = BURASI / "duzenlemeler.json"
    if not y.exists():
        return {"kayitlar": []}
    try:
        return json.loads(y.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"kayitlar": []}


def hesapla():
    h, f, b = yukle()

    def son(df, kolon, ondalik=1):
        s = df[kolon].dropna()
        return (None, "") if s.empty else (round(float(s.iloc[-1]), ondalik),
                                           f"{s.index[-1]:%d.%m.%Y}")

    ozet = {}
    for kolon in ("g_ar_13y", "g_tuketici_13y", "g_ticari_13y", "g_kobi_13y",
                  "g_bkk_13y", "g_kurumsal_kart_13y", "ayrisma", "kacak_bkk",
                  "kacak_kurumsal_kart", "npl", "kredi_mevduat"):
        d, t = son(h, kolon)
        if d is not None:
            ozet[kolon], ozet[f"{kolon}_tarih"] = d, t
    for kolon in ("makas_ihtiyac", "makas_ticari_tl", "makas_konut",
                  "makas_mevduat", "f_ihtiyac", "f_ticari_tl", "mev_tl", "politika"):
        d, t = son(f, kolon, 2)
        if d is not None:
            ozet[kolon], ozet[f"{kolon}_tarih"] = d, t
    for kolon in ("bkea_std_isletme", "bkea_std_kobi", "bkea_std_konut",
                  "bkea_std_diger", "bkea_talep"):
        d, t = son(b, kolon)
        if d is not None:
            ozet[kolon], ozet[f"{kolon}_tarih"] = d, t

    dfr = defter()
    kayitlar = dfr.get("kayitlar", [])
    ozet["_tarih"] = ozet.get("g_ar_13y_tarih", "")
    ozet["defter_toplam"] = len(kayitlar)
    ozet["defter_dogrulanmis"] = sum(1 for k in kayitlar
                                     if k.get("dogrulama") == "dogrulandi")
    return h, f, b, ozet


if __name__ == "__main__":
    h, f, b, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("veri tarihi:", ozet["_tarih"])
    print(f"  ayrışma (tüketici − ticari)  {ozet['ayrisma']:+.1f} puan "
          f"({ozet['g_tuketici_13y']} vs {ozet['g_ticari_13y']})")
    print(f"  kaçak: BKK − tüketici        {ozet['kacak_bkk']:+.1f} puan (BKK {ozet['g_bkk_13y']})")
    print(f"  kaçak: kur. kart − ticari    {ozet['kacak_kurumsal_kart']:+.1f} puan")
    print(f"  makas: ihtiyaç − politika    {ozet['makas_ihtiyac']:+.2f} puan")
    print(f"  makas: ticari − politika     {ozet['makas_ticari_tl']:+.2f} puan")
    print(f"  makas: mevduat − politika    {ozet['makas_mevduat']:+.2f} puan")
    print(f"  BKEA işletme std (son çeyrek) {ozet['bkea_std_isletme']:+.1f}")
    print(f"  defter: {ozet['defter_toplam']} kayıt, {ozet['defter_dogrulanmis']} doğrulanmış")
