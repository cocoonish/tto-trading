#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KUR SAATİ (3) — üretimin saatlik çağrısı bulutta gerçekten dönüyor mu?

NEDEN. Döviz kapanışı 02.10.2026'dan beri saatlik bardan kuruluyor
(`ortak/fx_kapanis.py`). Üretim iki dönemle çağırıyor: kur hatları
`period="730d"` (yfinance'in 60 dakikalık sınırı), bülten `period="1y"`.
Önceki keşif yalnız 60 günü indirmişti; bu iki dönem bu koşuculardan HİÇ
sorulmadı. Yahoo bir dönemi reddederse her hat sessizce yedek yola (günlük
bar) düşer — dış kaynak önce yoklanır, sonra kurulur.

Bu betik ÜRETİMİN KENDİ fonksiyonunu çağırır (`fx_kapanis.yfinance_saatlik`)
ve her sembol için bar sayısını, ilk/son barı, aradaki en uzun boşluğu ve
`saatlik_kapanislar`ın kurduğu günlük kapanış sayısını yazar. Ham bar
arşivlenmez (730 günlük on iki seri büyük); hüküm kurmaz, ölçüm yerelde.

Yalnız `arastirma-veri.yml` ile bulutta koşar (paketler: yfinance).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(KOK / "ortak"))
import fx_kapanis as F  # noqa: E402

VERI = BURASI / "veri"
SEMBOLLER = ["USDTRY=X", "EURTRY=X", "GBPTRY=X", "EURUSD=X", "USDJPY=X", "GBPUSD=X",
             "USDCHF=X", "AUDUSD=X", "NZDUSD=X", "USDCAD=X", "USDSEK=X", "USDNOK=X"]


def olc(donem: str, semboller: list[str]) -> dict:
    t0 = time.time()
    out: dict = {"donem": donem, "semboller": {}}
    try:
        seri = F.yfinance_saatlik(semboller, donem=donem)
    except Exception as e:  # noqa: BLE001
        out["hata"] = f"{type(e).__name__}: {e}"[:300]
        out["sure_sn"] = round(time.time() - t0, 1)
        return out
    simdi = dt.datetime.now(dt.timezone.utc)
    for k in semboller:
        s = seri.get(k)
        if s is None or not len(s):
            out["semboller"][k] = {"bar": 0}
            continue
        aralik = s.index.to_series().diff().dropna()
        kp = F.saatlik_kapanislar(s, F.kesim_turu(k), simdi)
        out["semboller"][k] = {
            "bar": int(len(s)), "ilk": s.index[0].isoformat(), "son": s.index[-1].isoformat(),
            "en_uzun_bosluk_saat": round(aralik.max().total_seconds() / 3600, 1) if len(aralik) else None,
            "kapanis_gun": int(len(kp.seri)),
            "ilk_kapanis": str(kp.seri.index[0].date()) if len(kp.seri) else None,
            "son_kapanis": str(kp.seri.index[-1].date()) if len(kp.seri) else None,
            "son_deger": float(kp.seri.iloc[-1]) if len(kp.seri) else None,
            "olculemeyen": kp.olculemeyen[-20:], "olculemeyen_sayi": len(kp.olculemeyen),
            "canli": kp.canli,
        }
    out["sure_sn"] = round(time.time() - t0, 1)
    return out


def main() -> int:
    VERI.mkdir(exist_ok=True)
    bas = dt.datetime.now(dt.timezone.utc)
    sonuc = {"baslangic_utc": bas.isoformat(timespec="seconds"),
             "kur_hatti_730d": olc("730d", ["USDTRY=X"]),
             "bulten_1y": olc("1y", SEMBOLLER)}
    time.sleep(2)
    sonuc["bulten_730d"] = olc("730d", SEMBOLLER)
    ad = f"saatlik_donem_{bas:%Y-%m-%dT%H%M}.json"
    (VERI / ad).write_text(json.dumps(sonuc, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    for anahtar in ("kur_hatti_730d", "bulten_1y", "bulten_730d"):
        r = sonuc[anahtar]
        print(f"── {anahtar}: {r.get('hata') or ''} {r['sure_sn']} sn")
        for k, v in r["semboller"].items():
            print(f"   {k:9s} bar {v.get('bar')} · {v.get('ilk', '')[:16]} → {v.get('son', '')[:16]} · kapanış "
                  f"{v.get('kapanis_gun')} gün · ölçülemeyen {v.get('olculemeyen_sayi')} · en uzun boşluk "
                  f"{v.get('en_uzun_bosluk_saat')} sa", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
