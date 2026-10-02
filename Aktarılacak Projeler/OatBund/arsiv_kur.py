#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND ANALİZİ — EK ARŞİV: döviz çaprazları EUR/USD ile AYNI kaynaktan.

NEDEN AYRI BİR BETİK. Ana arşiv (`arsiv_veri.py`) 01.10.2026'da indirildi ve
yayımlanan her sayı onun özlerine bağlı. Onu yeniden koşturmak bütün dosyaları
yeni bir güne taşır (CNBC 2 Ekim'in canlı barını da verir, geçmiş kotasyonlar
revize olabilir); bu betik YALNIZ yeni dosyalar yazar ve künyeye yalnız onların
girdisini EKLER — mevcut hiçbir dosyaya ve özüne dokunmaz.

NEDEN GEREKTİ. Çapraz kurlar (EUR/GBP, EUR/CHF, EUR/JPY) Yahoo'dan geliyordu
ve Yahoo'nun döviz barı New York kapanışından bir gün kaymış: D etiketli bar
D−1'in New York kapanışını taşır, analiz bu yüzden barları bir iş günü geri
kaydırıyordu. Kaydırma pazartesi barını CUMAYA yazar — ama pazartesi barı cuma
kapanışı değil, hafta sonu açılışından (pazar akşamı) sonraki fiyattır. Cuma
uçlu her olay penceresi bu yüzden hafta sonunu ölçmüyordu (02.10.2026
incelemesi, ölçüldü: 24.04.2017'de kaydırılmış seri −%0,08, CNBC +%1,31).
EUR/USD zaten CNBC'nin New York 17:00 barından okunuyor; çaprazları da aynı
uçtan almak saat sorusunu yapısal olarak kapatır.

Ayrıca Avrupa DIŞI bir dolar sepeti (JPY · CAD · AUD) — "kaybın ortak payı dolar
mı, Avrupa mı" sorusu sterlin ve frankla ayrılamıyor — ve ECB'nin 14:15 GBP/CHF
referans kurları (EUR/USD fixi gibi yalnız sağlamlık için).

Yalnız `arastirma-veri.yml` ile bulutta koşar.
"""
from __future__ import annotations

import json
import time
import urllib.request
from datetime import datetime, timezone

import pandas as pd

import arsiv_veri as av

# CNBC sembolleri: `<KUR>=` ABD doları karşısında (GBP= → GBP/USD, JPY= →
# USD/JPY); `EURxxx=` euro çaprazı. EUR= yeniden çekilir ama ana dosyaya
# YAZILMAZ: 1 Ekim'in günlük barı ana arşivde yoktu (gün içi 23:00 kotasyonu
# kullanıldı); burada yalnız o kotasyonu sınamak için durur.
KUR_SEM = ["EURGBP=", "EURCHF=", "EURJPY=", "GBP=", "CHF=", "JPY=", "CAD=", "AUD=", "EUR="]


def _ad(sem: str) -> str:
    return sem.rstrip("=").lower()


def cnbc_kur() -> None:
    gunluk = {}
    bugun = datetime.now(timezone.utc)
    yarin = (bugun + pd.Timedelta(days=1)).strftime("%Y%m%d")
    for sem in KUR_SEM:
        parca = []
        for bas in range(2000, bugun.year + 1, 5):
            son = f"{bas + 4}1231235959" if bas + 4 < bugun.year else f"{yarin}000000"
            u = (f"https://ts-api.cnbc.com/harmony/app/bars/{urllib.request.quote(sem)}/1D/"
                 f"{bas}0101000000/{son}/adjusted/EST5EDT.json")
            try:
                s = av._cnbc_bar(av.al(u, sn=30, deneme=3))
                if not s.empty:
                    parca.append(s)
            except Exception as e:  # noqa: BLE001
                av.UYARILAR.append(f"CNBC kur {sem} {bas}: {e!r}")
        if parca:
            gunluk[_ad(sem)] = pd.concat(parca)
        print(f"  · CNBC {sem}: günlük {len(gunluk.get(_ad(sem), []))}", flush=True)
    if gunluk:
        av.gz_yaz(pd.DataFrame(gunluk), "cnbc_kur_gunluk.csv.gz", "CNBC (Tullett Prebon), günlük bar ucu",
                  "Döviz, New York 17:00 kapanışı; eurgbp/eurchf/eurjpy = euro çaprazı, gbp/aud = ABD doları "
                  "karşısında (XXX/USD), chf/jpy/cad = USD/XXX; eur = EUR/USD (yalnız sınama); tarih CNBC "
                  "işlem günü (New York saati); hafta sonu barları kaynakta cumanın kopyası",
                  beklenen_ilk="2000-01-10")


def ecb_kur() -> None:
    parca = {}
    for kod in ("GBP", "CHF", "JPY"):
        try:
            df = av.ecb_csv(f"EXR/D.{kod}.EUR.SP00.A")
            parca[f"eur{kod.lower()}_ecb"] = df.assign(t=pd.to_datetime(df["TIME_PERIOD"])).set_index("t")["OBS_VALUE"]
        except Exception as e:  # noqa: BLE001
            av.UYARILAR.append(f"ECB EXR {kod}: {e!r}")
    if parca:
        av.gz_yaz(pd.DataFrame(parca), "ecb_kur.csv.gz", "ECB, EXR.D.<GBP|CHF|JPY>.EUR.SP00.A",
                  "Euro referans kurları (14:15 CET), 1 euro = x birim", beklenen_ilk="1999-01-05")


def main() -> int:
    av.VERI.mkdir(exist_ok=True)
    t0 = time.monotonic()
    for ad, f in (("CNBC kur", cnbc_kur), ("ECB kur", ecb_kur)):
        print(f"── {ad}", flush=True)
        try:
            f()
        except Exception as e:  # noqa: BLE001
            av.UYARILAR.append(f"{ad} DÜŞTÜ: {e!r}")
            print(f"  ✗ {ad}: {e!r}", flush=True)
    yol = av.VERI / "kunye.json"
    kunye = json.loads(yol.read_text(encoding="utf-8"))
    for ad, k in av.KAYNAKLAR.items():
        kunye["dosyalar"][ad] = k
    kunye.setdefault("ek_arsivler", []).append({
        "betik": "arsiv_kur.py", "olusturma": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sure_sn": round(time.monotonic() - t0, 1), "dosyalar": sorted(av.KAYNAKLAR), "uyarilar": av.UYARILAR})
    yol.write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"── bitti · {len(av.KAYNAKLAR)} dosya · {len(av.UYARILAR)} uyarı")
    for u in av.UYARILAR:
        print("  ! " + u)
    return 0 if av.KAYNAKLAR else 1


if __name__ == "__main__":
    raise SystemExit(main())
