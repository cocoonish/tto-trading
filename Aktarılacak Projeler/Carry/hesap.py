#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TL taşıma (carry) defteri — hesap katmanı.

Bu hat kendi veri kaynağına GİTMEZ: kur, faiz ve DİBS serileri Fonlama ile
DIBS hatlarının depoya yazdığı CSV'lerden okunur. İki sonucu var. Birincisi,
hat çevrimdışı da koşar — EVDS anahtarı ve ağ gerekmez; CI'da Fonlama/DIBS
tazelendikten sonra koşturulması yeter. İkincisi, sayfadaki her sayı öbür
sayfalarla AYNI seriden gelir: taşıma sayfasının TLREF'i, fonlama sayfasının
TLREF'inden farklı olamaz.

Üç katman hesaplanır:

  makas      İLERİYE bakan taşıma: bugünkü faiz − bugünkü kur hızı. Trader'ın
             "bugün pozisyona girsem" sorusu. Kur hızı geçmiş pencereden
             ölçüldüğü için bu bir tahmindir ve öyle etiketlenir.
  endeks     GERİYE bakan gerçekleşme: 100'le başlayıp her gün TLREF'le
             büyüyen ve kur değişimiyle USD'ye çevrilen hedge'siz carry
             endeksi. "Taşımayı gerçekten taşısaydım ne olurdu" sorusu.
             Çöküş dönemleri buradan okunur.
  tahvil     DIBS hattının hazır taşıma kolonları (bileşik konvansiyonla).
             Nakit taşıma ile tahvil taşımasının çelişkisi bu iki katmanın
             yan yana konmasıdır.

Konvansiyon — bu sayfanın ana metodoloji dersi: TLREF, AOFM ve politika faizi
BASİT yıllık ilan edilir; DİBS getirileri BİLEŞİKTİR. Basit faizle hesaplanan
taşıma yanlış işaret verebilir (26.08.2026'da 2y taşıma bileşikle −8,47,
basitle +0,61 — işaret bile ters). Bütün kıyaslar bileşiğe çevrilerek yapılır:
r_bileşik = (1 + r_basit/365)^365 − 1.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent.parent
FONLAMA = KOK / "Aktarılacak Projeler" / "Fonlama" / "data"
DIBS = KOK / "Aktarılacak Projeler" / "DIBS" / "data"

# Deval hızı pencereleri (iş günü) — USDTRYDeval hattıyla aynı: 5/21/63.
PENCERE = {"d1h": 5, "d1a": 21, "d3a": 63}


def gecelik_bilesik(basit: pd.Series) -> pd.Series:
    """Basit yıllık gecelik faiz → bileşik yıllık. TLREF/AOFM/politika için."""
    return ((1 + basit / 100 / 365) ** 365 - 1) * 100


def yukle() -> pd.DataFrame:
    g = pd.read_csv(FONLAMA / "gunluk.csv", parse_dates=["tarih"])
    mf = pd.read_csv(FONLAMA / "metrik.csv", parse_dates=["tarih"])
    md = pd.read_csv(DIBS / "metrik.csv", parse_dates=["tarih"])

    d = g[["tarih", "usdtry", "tlref", "aofm", "politika",
           "koridor_alt", "koridor_ust"]].merge(
        mf[["tarih", "aofm_gecerli", "marjinal_faiz"]], on="tarih", how="left").merge(
        md[["tarih", "n3a", "n1y", "n2y", "tlref_bilesik", "aofm_bilesik",
            "politika_bilesik_gercek", "carry_2y_tlref", "carry_2y_politika",
            "carry_2y_aofm", "carry_3a_tlref", "carry_2y_tlref_basit",
            "f_1y1y"]], on="tarih", how="left")
    d = d.sort_values("tarih").set_index("tarih")
    # Politika faizi ve koridor ADIM fonksiyonudur: karar değişene kadar
    # geçerlidir. Kur satırı olup faiz satırı olmayan günlerde ileri taşımak
    # veri uydurmak değil, ilan edilmiş faizin tanımıdır. TLREF/AOFM taşınMAZ:
    # onlar her gün yeniden gerçekleşen ölçümlerdir.
    for a in ("politika", "koridor_alt", "koridor_ust"):
        d[a] = d[a].ffill()
    return d


def deval_hizi(kur: pd.Series, gun: int) -> pd.Series:
    """ACT/365 yıllıklandırılmış kur değişim hızı — USDTRYDeval ile aynı tanım."""
    onceki = kur.shift(gun)
    takvim = (kur.index.to_series() - kur.index.to_series().shift(gun)).dt.days
    return ((kur / onceki) ** (365.0 / takvim) - 1) * 100


def carry_endeksi(d: pd.DataFrame) -> pd.DataFrame:
    """Hedge'siz TL taşıma endeksi, USD bazında.

    Kurgu: 1 USD bozdurulur, TL'si her gün TLREF'te (basit yıllık, ACT/365
    takvim günü tahakkuku) değerlenir, her gün kura bölünüp USD'ye çevrilir.
    TLREF öncesi dönem yok sayılır — vekil faizle tarih uzatmak, endeksin
    "gerçekleşme" iddiasını bozar.
    """
    e = d[["usdtry", "tlref"]].dropna().copy()
    gun = e.index.to_series().diff().dt.days.fillna(0)
    e["tl_birikim"] = (1 + e["tlref"].shift() / 100 * gun / 365).fillna(1).cumprod()
    e["endeks"] = 100 * e["tl_birikim"] * e["usdtry"].iloc[0] / e["usdtry"]
    e["zirveden"] = 100 * (e["endeks"] / e["endeks"].cummax() - 1)
    return e


def yillik_getiri(endeks: pd.Series, gun: int) -> pd.Series:
    onceki = endeks.shift(gun)
    takvim = (endeks.index.to_series() - endeks.index.to_series().shift(gun)).dt.days
    return ((endeks / onceki) ** (365.0 / takvim) - 1) * 100


def hesapla() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    d = yukle()
    for ad, gun in PENCERE.items():
        d[ad] = deval_hizi(d["usdtry"], gun)

    # İleriye bakan makaslar — hepsi BİLEŞİK faizle
    d["tlref_b"] = gecelik_bilesik(d["tlref"])
    d["politika_b"] = gecelik_bilesik(d["politika"])
    d["makas_politika_d1a"] = d["politika"] - d["d1a"]      # rejim panosuyla aynı tanım
    d["makas_tlref_b_d3a"] = d["tlref_b"] - d["d3a"]
    d["makas_tlref_b_d1a"] = d["tlref_b"] - d["d1a"]

    e = carry_endeksi(d)
    e["getiri_1y"] = yillik_getiri(e["endeks"], 252)
    d = d.join(e[["endeks", "zirveden", "getiri_1y"]])

    son = d.dropna(subset=["usdtry"]).iloc[-1]
    son_tlref = d.dropna(subset=["tlref"]).iloc[-1]
    son_dibs = d.dropna(subset=["carry_2y_tlref"]).iloc[-1]
    son_endeks = d.dropna(subset=["endeks"]).iloc[-1]

    # Çöküş dönemleri: endeksin zirveden %10'dan derin düştüğü aralıklar
    cokusler = []
    seri = e["zirveden"]
    icinde = False
    for t, v in seri.items():
        if not icinde and v <= -10:
            icinde, bas, dip, dip_t = True, t, v, t
        elif icinde:
            if v < dip:
                dip, dip_t = v, t
            if v >= -1:                    # zirveye dönüş sayılır
                cokusler.append({"bas": f"{bas:%Y-%m-%d}", "dip_tarih": f"{dip_t:%Y-%m-%d}",
                                 "dip": round(dip, 1), "bitis": f"{t:%Y-%m-%d}"})
                icinde = False
    if icinde:
        cokusler.append({"bas": f"{bas:%Y-%m-%d}", "dip_tarih": f"{dip_t:%Y-%m-%d}",
                         "dip": round(dip, 1), "bitis": ""})

    # En kötü 1 aylık pencereler: "carry ne zaman ölür" sorusunun ölçülen
    # cevabı. Tek dev bir zirveden-düşüş aralığından daha okunur, çünkü çöküş
    # dönemleri gerçekte kısa ve şiddetlidir. Aynı krize ait pencereler
    # (±45 gün) tek kayda indirgenir.
    a1 = e["endeks"].pct_change(21).dropna() * 100
    kotu = []
    for t, v in a1.sort_values().items():
        if any(abs((t - pd.Timestamp(x["tarih"])).days) < 45 for x in kotu):
            continue
        kotu.append({"tarih": f"{t:%Y-%m-%d}", "getiri_1a": round(float(v), 1)})
        if len(kotu) == 5:
            break
    kotu = [{**x, "tarih": x["tarih"]} for x in sorted(kotu, key=lambda x: x["tarih"])]

    getiri = e["endeks"].pct_change().dropna()
    yil = 252
    sharpe3y = (getiri.tail(3 * yil).mean() / getiri.tail(3 * yil).std() * np.sqrt(yil)
                if len(getiri) > 3 * yil else np.nan)

    def r(x, n=1):
        return None if pd.isna(x) else round(float(x), n)

    ozet = {
        "_tarih": f"{son.name:%d.%m.%Y}",
        "kur": r(son["usdtry"], 4),
        "d1a": r(son["d1a"]), "d3a": r(son["d3a"]),
        "politika": r(son["politika"], 2),
        "politika_tarih": f"{son.name:%d.%m.%Y}",
        "tlref": r(son_tlref["tlref"], 2),
        "tlref_b": r(son_tlref["tlref_b"], 2),
        "tlref_tarih": f"{son_tlref.name:%d.%m.%Y}",
        "makas_politika_d1a": r(son["makas_politika_d1a"]),
        "makas_tlref_b_d3a": r(d["makas_tlref_b_d3a"].dropna().iloc[-1]),
        "makas_tlref_b_d3a_tarih": f"{d['makas_tlref_b_d3a'].dropna().index[-1]:%d.%m.%Y}",
        "carry_2y_tlref": r(son_dibs["carry_2y_tlref"], 2),
        "carry_2y_tlref_basit": r(son_dibs["carry_2y_tlref_basit"], 2),
        "carry_2y_politika": r(son_dibs["carry_2y_politika"], 2),
        "carry_3a_tlref": r(son_dibs["carry_3a_tlref"], 2),
        "carry_tarih": f"{son_dibs.name:%d.%m.%Y}",
        "n2y": r(son_dibs["n2y"], 2), "f_1y1y": r(son_dibs["f_1y1y"], 2),
        "endeks": r(son_endeks["endeks"]),
        "endeks_tarih": f"{son_endeks.name:%d.%m.%Y}",
        "endeks_bas": f"{e.index[0]:%d.%m.%Y}",
        "getiri_1y": r(son_endeks["getiri_1y"]),
        "zirveden": r(son_endeks["zirveden"]),
        "sharpe_3y": r(sharpe3y, 2),
        "cokus_sayisi": len(cokusler),
        "en_derin_cokus": min((c["dip"] for c in cokusler), default=None),
        "en_derin_cokus_tarih": next((c["dip_tarih"] for c in cokusler
                                      if c["dip"] == min(x["dip"] for x in cokusler)), ""),
        "cokusler": cokusler,
        "kotu_aylar": kotu,
    }
    return d, e, ozet


if __name__ == "__main__":
    d, e, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"seri: {d.index[0]:%Y-%m-%d} → {d.index[-1]:%Y-%m-%d}")
    for k in ("kur", "d1a", "makas_politika_d1a", "makas_tlref_b_d3a", "carry_2y_tlref",
              "carry_2y_tlref_basit", "endeks", "getiri_1y", "zirveden", "sharpe_3y",
              "cokus_sayisi", "en_derin_cokus", "en_derin_cokus_tarih"):
        print(f"  {k:24s} {ozet[k]}")
    print("  en kötü 1 aylık pencereler:")
    for x in ozet["kotu_aylar"]:
        print(f"    {x['tarih']}  {x['getiri_1a']:+.1f}%")
    print("  çöküşler:")
    for c in ozet["cokusler"]:
        print(f"    {c['bas']} → dip {c['dip_tarih']} ({c['dip']}%) → {c['bitis'] or 'sürüyor'}")
