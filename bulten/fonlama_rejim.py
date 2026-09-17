#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İLAN EDİLEN faiz ile GERÇEKLEŞEN gecelik maliyetin ayrıştığı dönemleri ölçer.

NEDEN AYRI BİR ÖLÇÜ. Politika faizi 22.01.2026'dan beri %37,0'de sabit; bu
tek sayıya bakan biri 2026'da para politikasının hiç değişmediğini sanır.
Oysa piyasanın lirayı gecelik fonladığı oran (TLREF) aynı yıl içinde iki kez
ÜÇ PUANA yakın yer değiştirdi: 04.03'te koridor tavanına çıktı, 24.08'de
politika faizine geri döndü. İkisi de faiz kararıyla değil LİKİDİTE
kararlarıyla oldu ve ikisi de duyuru metinlerinde teknik bir cümleyle geçti.

ÖLÇÜ İKİ AYRI BÜYÜKLÜKTÜR ve ikisi de yazılır:
  · TLREF — piyasanın gerçekleşen gecelik referans oranı (BİST). Fiyatlamayı
    bu belirler; bir tahvilin taşıma maliyeti buradan doğar.
  · AOFM — TCMB'nin kendi fonlamasının ağırlıklı ortalama maliyeti. Fonlama
    sıfıra indiğinde ağırlık kalmaz ve seri GEÇERSİZ olur; o günlerde
    AOFM yazılmaz — ölçülemeyen boş bırakılır, son değerinde dondurulmaz.

REJİM TANIMI EŞİKSİZ VE YAPISAL. Bir gün, TLREF'in EN YAKIN durduğu ilan
edilmiş orana göre sınıflanır: politika faizi, koridorun üstü (gecelik borç
verme) ya da koridorun altı (gecelik borçlanma). Üçü de TCMB'nin kendi ilan
ettiği sayılardır; eşik SEÇİLMEZ, çıpalar verilidir. Bir eşik seçilseydi
eşiğin kendisi sonucu belirlerdi — ve bu depoda ölçülmemiş bir seviyeye eşik
konmaz. Ardışık aynı sınıftaki günler bir rejim bloğu olur.

Koşum:  python3 -u bulten/fonlama_rejim.py [--yil 2026]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

KOK = Path(__file__).resolve().parents[1]
METRIK = KOK / "Aktarılacak Projeler" / "Fonlama" / "data" / "metrik.csv"

# Bir blok bundan kısaysa rejim değil GÜRÜLTÜDÜR ve öyle İŞARETLENİR — tabloda
# durur, silinmez: ölçülmüş bir günü ölçülmemiş göstermek de bir kusurdur.
# Sayı ölçülmüş değil TAVAN ve öyle yazıldı.
ASGARI_GUN = 3

# TLREF'in hangi ilan edilmiş orana demirlendiği. Adlar okura basılmaz; bu
# dosya ölçer, hükmü yazı katmanı kurar.
CIPALAR = ("politika", "koridor_ust", "koridor_alt")


def yukle() -> pd.DataFrame:
    if not METRIK.exists():
        raise SystemExit(f"ölçüm dosyası yok: {METRIK}")
    return pd.read_csv(METRIK, index_col=0, parse_dates=True)


def cipa(M: pd.DataFrame) -> pd.Series:
    """Her gün TLREF'in EN YAKIN durduğu ilan edilmiş oranın adı."""
    G = M[M["tlref"].notna()]
    if G.empty:
        return pd.Series(dtype=object)
    mesafe = pd.DataFrame({c: (G["tlref"] - G[c]).abs() for c in CIPALAR})
    # Bir çıpanın kendisi ölçülemediği gün o gün SINIFLANMAZ — ölçülemeyen
    # boş bırakılır, en yakın ikinciye kaydırılmaz.
    return mesafe.idxmin(axis=1).where(mesafe.notna().all(axis=1))


def rejimler(M: pd.DataFrame, bas: str, son: str) -> list[dict]:
    """Çıpası sabit kalan ardışık gün blokları.

    Kısa bloklar komşuya KATILMAZ, ayrı satır olarak durur ve `gurultu` diye
    işaretlenir — silmek, ölçülmüş bir günü ölçülmemiş göstermek olurdu.
    """
    S = M.loc[bas:son]
    c = cipa(S).dropna()
    if c.empty:
        return []
    blok = (c != c.shift()).cumsum()
    out = []
    for _, x in c.groupby(blok):
        idx = x.index
        aofm = S.loc[idx, "aofm"].where(S.loc[idx, "aofm_gecerli"].astype(bool))
        tl = S.loc[idx, "tlref"]
        out.append({
            "cipa": str(x.iloc[0]),
            "bas": idx[0].strftime("%d.%m.%Y"),
            "son": idx[-1].strftime("%d.%m.%Y"),
            "gun": len(idx),
            "tlref_ort": round(float(tl.mean()), 2),
            "politika": round(float(S.loc[idx, "politika"].iloc[-1]), 2),
            "makas_politika_puan": round(float((tl - S.loc[idx, "politika"]).mean()), 2),
            "aofm_ort": (round(float(aofm.mean()), 2) if aofm.notna().any() else None),
            "aofm_gecersiz_gun": int(aofm.isna().sum()),
            "gurultu": len(idx) < ASGARI_GUN,
        })
    return out


def sicrama(M: pd.DataFrame, gun: str) -> dict:
    """Bir işlem gününün TLREF'i ile bir ÖNCEKİ İŞLEM GÜNÜNÜN TLREF'i.

    Takvim günü değil işlem günü: cuma ile pazartesi arasındaki hareket tek
    bir seans hareketidir ve bu depoda ölçülmüş hâli yazılı.
    """
    t = M["tlref"].dropna()
    i = t.index.get_loc(pd.Timestamp(gun))
    onc, yen = t.iloc[i - 1], t.iloc[i]
    return {
        "onceki_gun": t.index[i - 1].strftime("%d.%m.%Y"), "onceki": round(float(onc), 2),
        "gun": t.index[i].strftime("%d.%m.%Y"), "yeni": round(float(yen), 2),
        "bp": int(round((yen - onc) * 100)),
    }


def kos(yil: int, kac_sicrama: int = 3) -> dict:
    M = yukle()
    bas, son = f"{yil}-01-01", f"{yil}-12-31"
    S = M.loc[bas:son]
    t = S["tlref"].dropna()
    d = t.diff().dropna()
    enb = d.abs().sort_values(ascending=False).index[:kac_sicrama]
    pay = cipa(S).value_counts()
    return {
        "yil": yil,
        "olcum_gunu": M.index[-1].strftime("%d.%m.%Y"),
        "politika_sabit_mi": bool(S["politika"].nunique() == 1),
        "politika": round(float(S["politika"].iloc[-1]), 2),
        "tlref_min": round(float(t.min()), 2),
        "tlref_maks": round(float(t.max()), 2),
        "tlref_aralik_puan": round(float(t.max() - t.min()), 2),
        "gun_sayisi": {k: int(v) for k, v in pay.items()},
        "en_buyuk_hareketler": [sicrama(M, g.strftime("%Y-%m-%d")) for g in enb],
        "rejimler": rejimler(M, bas, son),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yil", type=int, default=2026)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = kos(a.yil)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print(f"ÖLÇÜM GÜNÜ {r['olcum_gunu']} · {r['yil']} · politika faizi "
          f"%{r['politika']:.2f}"
          + (" (yıl boyunca sabit)" if r["politika_sabit_mi"] else ""))
    print(f"TLREF aralığı: {r['tlref_min']:.2f} – {r['tlref_maks']:.2f} "
          f"({r['tlref_aralik_puan']:.2f} puan)")
    print("Çıpaya göre gün sayısı: "
          + " · ".join(f"{k} {v}" for k, v in r["gun_sayisi"].items()))
    print()
    print("En büyük tek seanslık TLREF hareketleri:")
    for s_ in r["en_buyuk_hareketler"]:
        print(f"  {s_['onceki_gun']} %{s_['onceki']:.2f} → {s_['gun']} "
              f"%{s_['yeni']:.2f} = {s_['bp']:+d} baz puan")
    print()
    print(f"{'çıpa':>12} {'başlangıç':>11} {'bitiş':>11} {'gün':>4} "
          f"{'TLREF ort':>10} {'makas':>7} {'AOFM ort':>9} {'AOFM yok':>9}")
    for x in r["rejimler"]:
        if x["gurultu"]:
            continue
        ao = f"{x['aofm_ort']:.2f}" if x["aofm_ort"] is not None else "—"
        print(f"{x['cipa']:>12} {x['bas']:>11} {x['son']:>11} {x['gun']:>4} "
              f"{x['tlref_ort']:>10.2f} {x['makas_politika_puan']:>+7.2f} "
              f"{ao:>9} {x['aofm_gecersiz_gun']:>9}")
    n = sum(1 for x in r["rejimler"] if x["gurultu"])
    print(f"\n(tabloda gösterilmeyen {n} kısa blok ölçümde DURUYOR; "
          f"--json hepsini yazar)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
