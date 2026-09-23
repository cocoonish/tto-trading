#!/usr/bin/env python3
"""Boş seans onarımı ve TLREF uzantısı — ÜRETİM KODUYLA uçtan uca, canlı kaynağa karşı.

Duman sınamaları iki düzeltmeyi sahte girdiyle sınıyor (ağa çıkmazlar). Bu
betik aynı kodu GERÇEK kaynaklara karşı koşturur: `piyasa.topla(tazele=True)`
(toplu çekim + meta + onarım + özet) ve `ortak/tlref.cerceveye_ekle` (Borsa
İstanbul dosyası + EVDS). Depoya YAZMAZ — keşif işi `contents: read` koşar;
koşucunun kendi kopyasındaki önbellek dosyası iş bitince atılır.
"""
from __future__ import annotations

import sys
import datetime as dt
from pathlib import Path

sys.path.insert(0, ".")
KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "ortak"))

print(f"şimdi {dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M} UTC")

# ── 1. piyasa fotoğrafı
import piyasa as P  # noqa: E402

p = P.topla(tazele=True)
oz = p["seans_ozeti"]
print(f"\n(1) PİYASA · {oz['satir']} satır · kapanış {p['kapanis_seansi']}")
print("  dağılım:", ", ".join(f"{x['satir']} satır {x['tarih']}" for x in oz["dagilim"]))
print("  son işlem fiyatından kurulan:", "; ".join(f"{x['ad']} {x['gun']}" for x in oz["son_islemden"]) or "—")
print("  kaynağın boş verdiği, kurulamayan:",
      "; ".join(f"{x['ad']} {','.join(x['gunler'])} (satır {x['tarih']})" for x in oz["kaynak_bos"]) or "—")
print("  önbellekten devredilen:", "; ".join(f"{x['ad']} {','.join(x['gunler'])}" for x in oz["devredilen"]) or "—")
print("  sınanamayan:", " · ".join(p["seans_sinanamadi"]) or "—")
for g in p["gruplar"]:
    for s in g["satirlar"]:
        if s["kod"] in ("XU100.IS", "XU030.IS", "^GSPC", "^GDAXI", "BTC-USD", "DX-Y.NYB", "^TNX", "HYG"):
            print(f"    {s['kod']:10s} {s['tarih']} son {s['son']} 1g {s['d1']} "
                  f"onarım {s.get('onarim')} eksik {s.get('eksik_seans')} devir {s.get('devredilen')}")

# ── 2. TLREF uzantısı
print("\n(2) TLREF · EVDS + Borsa İstanbul")
import pandas as pd  # noqa: E402
sys.path.insert(0, str(KOK / "Aktarılacak Projeler" / "Fonlama"))
import veri as F  # noqa: E402
import tlref as T  # noqa: E402

bas = dt.date.today() - dt.timedelta(days=60)
j = F._cek(f"{F.BASE}/series=TP.BISTTLREF.ORAN-TP.BISTTLREF.KAPANIS&startDate={bas:%d-%m-%Y}"
           f"&endDate={dt.date.today():%d-%m-%Y}&type=json")
satir = [(pd.Timestamp(dt.datetime.strptime(s["Tarih"], "%d-%m-%Y")),
          s.get("TP_BISTTLREF_ORAN"), s.get("TP_BISTTLREF_KAPANIS")) for s in j.get("items") or []]
g = pd.DataFrame({"tlref": [float(o) if o not in (None, "") else None for _, o, _ in satir],
                  "tlref_endeks": [float(e) if e not in (None, "") else None for _, _, e in satir]},
                 index=pd.DatetimeIndex([t for t, _, _ in satir]))
print(f"  EVDS son gün: oran {g['tlref'].dropna().index[-1]:%d.%m.%Y} · "
      f"endeks {g['tlref_endeks'].dropna().index[-1]:%d.%m.%Y}")
g2, uy, bilgi = T.cerceveye_ekle(g, {"tlref": "oran", "tlref_endeks": "endeks"})
for k, b in bilgi.items():
    print(f"  {k}: {b}")
for u in uy:
    print("  uyarı:", u)
print(f"  uzantı sonrası son gün: oran {g2['tlref'].dropna().index[-1]:%d.%m.%Y} = "
      f"{g2['tlref'].dropna().iloc[-1]} · endeks {g2['tlref_endeks'].dropna().index[-1]:%d.%m.%Y} = "
      f"{g2['tlref_endeks'].dropna().iloc[-1]}")
print("\nbitti", dt.datetime.now(dt.timezone.utc).strftime("%H:%M:%S"), "UTC")
