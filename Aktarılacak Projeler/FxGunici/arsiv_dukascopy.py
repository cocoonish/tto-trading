#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dukascopy 1 dakikalık bid/ask arşivini kurar (kaldığı yerden sürer).

Koşum (iki yol, aynı betik):
  · Bulut: `.github/workflows/arastirma-veri.yml`, betik =
    "Aktarılacak Projeler/FxGunici/arsiv_dukascopy.py", paketler = "pyarrow".
    İş akışı yalnız bu klasörün `veri/` dizinini dala commit eder.
  · Yerel (kaynağa ağ erişimi olan makinede):  .venv/bin/python arsiv_dukascopy.py

Birim parite × yıldır ve ATOMİKtir: bir yılın tek günü bile hatayla dönerse o
yıl yazılmaz, künyede hatasıyla görünür ve bir sonraki koşu onu yeniden dener.
Tamamlanmış, özü tutan birimlere dokunulmaz. Süre bütçesi (ayar.toml
`butce_dk`) birimler ARASINDA sınanır; bulutun 21 dakikalık sınırından önce
durur, künyeyi yazar, kalan birimler bir sonraki koşuya kalır.

Çapraz sınama için her parite ve yılın Ocak ve Temmuz aylarının Dukascopy
SAATLİK mum dosyaları da ham hâliyle saklanır (`saatlik/`); kalite denetimi
dakika arşivinden kurduğu saatlik mumları onlarla karşılaştırır.
"""
from __future__ import annotations

import platform
import sys
import time
from datetime import date, datetime, timezone

import numpy as np
import pyarrow

import ayar as ay
import dukascopy as dk


def icerik_ozu(df) -> str:
    """Dosya kodlamasından bağımsız içerik özü (parquet sürümü değişse de aynı kalır)."""
    import hashlib
    h = hashlib.sha256()
    for s in dk.SUTUNLAR:
        h.update(np.ascontiguousarray(df[s].to_numpy()).tobytes())
    return h.hexdigest()


def saatlik_indir(a: ay.Ayar, kunye: dict) -> int:
    hedef = ay.DUKA / "saatlik"
    yeni = 0
    for sembol in a.ciftler:
        for yil in range(a.baslangic.year, a.bitis.year + 1):
            for ay_ in (1, 7):
                if date(yil, ay_, 28) > a.bitis or date(yil, ay_, 1) < a.baslangic.replace(day=1):
                    continue
                for taraf in ("BID", "ASK"):
                    yol = hedef / sembol / f"{yil}-{ay_:02d}_{taraf}.bi5"
                    if yol.exists():
                        continue
                    y = dk.getir(dk.saatlik_url(sembol, yil, ay_, taraf), a.deneme, a.zaman_asimi_sn)
                    if y.durum != "tamam":
                        print(f"  saatlik {sembol} {yil}-{ay_:02d} {taraf}: {y.durum} {y.ayrinti}")
                        continue
                    dk.coz(y.ham, adim_sn=3600, azami=744)   # bozuk dosya saklanmaz
                    yol.parent.mkdir(parents=True, exist_ok=True)
                    yol.write_bytes(y.ham)
                    yeni += 1
    return yeni


def main() -> int:
    a = ay.oku()
    dizin = ay.DUKA
    kunye = dk.kunye_oku(dizin)
    kunye.setdefault("birimler", {})
    kunye.update({
        "kaynak": dk.KOK_URL + "/<SEMBOL>/<YYYY>/<AA-1>/<GG>/<BID|ASK>_candles_min_1.bi5",
        "kapsam": {"ciftler": list(a.ciftler), "baslangic": a.baslangic.isoformat(), "bitis": a.bitis.isoformat()},
        "nokta": {c: a.nokta[c] for c in a.ciftler},
        "kod_ozu": dk.oz(ay.BURASI / "dukascopy.py"),
        "ortam": {"python": platform.python_version(), "pyarrow": pyarrow.__version__},
    })
    t0 = time.monotonic()
    butce = a.butce_dk * 60
    yapilan, kalan, hatali = 0, 0, 0
    for sembol in a.ciftler:
        for yil in range(a.baslangic.year, a.bitis.year + 1):
            anahtar = f"{sembol}/{yil}"
            yol = dizin / sembol / f"{yil}.parquet"
            son_hedef = min(a.bitis, date(yil, 12, 31)).isoformat()
            ilk_hedef = max(a.baslangic, date(yil, 1, 1)).isoformat()
            m = kunye["birimler"].get(anahtar)
            if (m and m.get("tam") and m.get("son_gun") == son_hedef and m.get("ilk_gun") == ilk_hedef
                    and yol.exists() and dk.oz(yol) == m.get("sha256")):
                continue
            if time.monotonic() - t0 > butce:
                kalan += 1
                continue
            t1 = time.monotonic()
            df, k = dk.yil_indir(sembol, yil, a.baslangic, a.bitis, a.es_zamanli, a.deneme, a.zaman_asimi_sn)
            k["sure_sn"] = round(time.monotonic() - t1, 1)
            k["indirme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if k["tam"]:
                k["sha256"] = dk.yaz(df, yol)
                k["icerik_ozu"] = icerik_ozu(df)
                k["bayt"] = yol.stat().st_size
                yapilan += 1
                print(f"✓ {anahtar}: {k['satir']:,} dakika · {k['gun_dolu']}/{k['gun']} gün · "
                      f"{k['bayt'] / 1e6:.1f} MB · {k['sure_sn']} sn", flush=True)
            else:
                hatali += 1
                print(f"✗ {anahtar}: {len(k['gun_hata'])} gün hatalı — yazılmadı; ilk: {k['gun_hata'][:3]}",
                      flush=True)
            kunye["birimler"][anahtar] = k
            dk.kunye_yaz(dizin, kunye)       # her birimden sonra: koşu kesilse de ilerleme kalır
    if time.monotonic() - t0 <= butce:
        n = saatlik_indir(a, kunye)
        print(f"saatlik çapraz sınama dosyası: {n} yeni")
    dk.kunye_yaz(dizin, kunye)
    toplam = len(a.ciftler) * (a.bitis.year - a.baslangic.year + 1)
    tamam = sum(1 for v in kunye["birimler"].values() if v.get("tam"))
    print(f"özet: bu koşuda {yapilan} birim yazıldı · {hatali} hatalı · {kalan} bütçeye kaldı · "
          f"arşivde {tamam}/{toplam} birim tam · {time.monotonic() - t0:.0f} sn")
    # Bütçeye kalan birim bir kusur değil, sürecek iştir; çıkış 0. Hatalı birim 1.
    return 1 if hatali else 0


if __name__ == "__main__":
    sys.exit(main())
