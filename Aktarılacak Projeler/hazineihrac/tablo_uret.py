#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Site tabloları için JSON — Excel'in üç sekmesi + planlı takvim + backtest.

Sayfadaki VeriTablosu bileşeni bu dosyaları istemcide çekip sıralanabilir,
filtrelenebilir tablo olarak gösterir. Excel'deki HER sütun aynen taşınır
(CLAUDE.md: hiçbir şey atlanmaz); sayfa hangilerini varsayılan göstereceğini
kendi seçer, gerisi "sütun grupları" seçicisiyle açılır.

Çıktı: tablolar.json  →  {"uretim": ..., "tablolar": {ad: {"sutunlar": [...], "satirlar": [[...]]}}}
Cron ve guncelle.py bunu ozet_uret.py ile birlikte siteye kopyalar.
"""
import json, os, math
from datetime import datetime
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))

KAYNAKLAR = {
    # ad → (dosya, açıklama, tarih sütunları)
    "ihaleler":     ("hazine_ihale_verileri.csv",     "İhale verileri — Excel 'İhale Verileri' sekmesi, tüm sütunlar",
                     ["İhale Tarihi", "Valör Tarihi", "İtfa Tarihi"]),
    "hedef":        ("hazine_hedef_gerceklesme.csv",  "Aylık strateji hedefi vs gerçekleşme", []),
    "vade":         ("hazine_vade_analizi.csv",       "Ay bazında ağırlıklı ortalama vade", ["Tarih"]),
    "planli":       ("hazine_planlanan_ihaleler.csv", "Planlı ihraç takvimi ve tahminler", ["İhale Tarihi", "İtfa Tarihi", "Son İhale Tarihi"]),
    "backtest":     ("hazine_tahmin_dogrulama.csv",   "İhale bazında tahmin vs gerçekleşen (backtest)", []),
}


def _temiz(v):
    """JSON'a güvenli değer: NaN → None, Timestamp → 'GG.AA.YYYY', numpy → python."""
    if v is None or v is pd.NaT: return None
    if isinstance(v, float) and math.isnan(v): return None
    if isinstance(v, pd.Timestamp): return v.strftime("%d.%m.%Y")
    if pd.isna(v): return None
    if hasattr(v, "item"): return v.item()
    return v


def main():
    cikti = {"uretim": datetime.now().strftime("%d.%m.%Y %H:%M"), "tablolar": {}}
    for ad, (dosya, aciklama, tarihler) in KAYNAKLAR.items():
        yol = os.path.join(BASE, dosya)
        if not os.path.exists(yol):
            print(f"  atlandı (yok): {dosya}"); continue
        d = pd.read_csv(yol, encoding="utf-8-sig")
        for t in tarihler:
            if t in d.columns:
                d[t] = pd.to_datetime(d[t], dayfirst=True, errors="coerce")
        # tarih sütunları GG.AA.YYYY, ama sıralama için ISO da tut (istemci kullanır)
        satirlar = []
        for _, r in d.iterrows():
            satirlar.append([_temiz(v) for v in r.tolist()])
        cikti["tablolar"][ad] = {
            "aciklama": aciklama,
            "sutunlar": [str(c) for c in d.columns],
            "tarih_sutunlari": [c for c in tarihler if c in d.columns],
            "satirlar": satirlar,
        }
        print(f"  {ad:10s} {len(satirlar):4d} satır × {len(d.columns):2d} sütun  ← {dosya}")
    yol = os.path.join(BASE, "tablolar.json")
    json.dump(cikti, open(yol, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"yazıldı: {yol}  ({os.path.getsize(yol)//1024} KB)")


if __name__ == "__main__":
    main()
