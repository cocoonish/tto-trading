#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dukascopy 1 dakikalık bid/ask arşivini kurar (kaldığı yerden sürer).

Koşum (iki yol, aynı betik):
  · Bulut: `.github/workflows/arastirma-veri.yml`, betik =
    "Aktarılacak Projeler/FxGunici/arsiv_dukascopy.py", paketler = "pyarrow".
    İş akışı yalnız bu klasörün `veri/` dizinini dala commit eder.
  · Yerel (kaynağa ağ erişimi olan makinede):  .venv/bin/python arsiv_dukascopy.py

Birim parite × yıldır ve KALDIĞI YERDEN sürer: indirilen günler yazılır,
hatayla dönen günler künyede `gun_hata`da kalır ve bir sonraki koşu YALNIZ
onları ister. Birim, eksik günü kalmayınca `tam` olur; tamamlanmış ve özü
tutan birimlere dokunulmaz. Süre bütçesi (ayar.toml `butce_dk`) her dosya
denemesinden önce sınanır: bütçe dolunca yeni deneme başlamaz, eldeki yazılır,
iş akışının 21 dakikalık sınırı betiği hiçbir zaman ortasında kesmez.

Çapraz sınama için her parite ve yılın Ocak ve Temmuz aylarının Dukascopy
SAATLİK mum dosyaları da ham hâliyle saklanır (`saatlik/`); kalite denetimi
dakika arşivinden kurduğu saatlik mumları onlarla karşılaştırır.

PARÇA. `TTO_PARCA` ortam değişkeni (boşlukla ayrık parite listesi) verilirse
yalnız o pariteler işlenir. İş akışı pariteleri ayrı koşucularda aynı anda
çalıştırabilir (`parcalar` girdisi); her iş yalnız kendi paritesinin dosyalarına
ve künyesine yazar. Kaynağın hız sınırı koşucu başınadır: tek koşucuda eşzamanlılığı
artırmak 503 üretiyordu, ayrı koşucular üretmiyorsa toplam hız parça sayısıyla artar.
"""
from __future__ import annotations

import os
import platform
import sys
import time
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq

import ayar as ay
import dukascopy as dk


def icerik_ozu(df) -> str:
    """Dosya kodlamasından bağımsız içerik özü (parquet sürümü değişse de aynı kalır)."""
    import hashlib
    h = hashlib.sha256()
    for s in dk.SUTUNLAR:
        h.update(np.ascontiguousarray(df[s].to_numpy()).tobytes())
    return h.hexdigest()


def saatlik_indir(a: ay.Ayar, semboller: list[str], son_an: float) -> int:
    hedef = ay.DUKA / "saatlik"
    yeni = 0
    for sembol in semboller:
        for yil in range(a.baslangic.year, a.bitis.year + 1):
            for ay_ in (1, 7):
                if date(yil, ay_, 28) > a.bitis or date(yil, ay_, 1) < a.baslangic.replace(day=1):
                    continue
                for taraf in ("BID", "ASK"):
                    yol = hedef / sembol / f"{yil}-{ay_:02d}_{taraf}.bi5"
                    if yol.exists():
                        continue
                    y = dk.getir(dk.saatlik_url(sembol, yil, ay_, taraf), a.deneme, a.zaman_asimi_sn, son_an)
                    if y.durum != "tamam":
                        print(f"  saatlik {sembol} {yil}-{ay_:02d} {taraf}: {y.durum} {y.ayrinti}")
                        continue
                    dk.coz(y.ham, adim_sn=3600, azami=744)   # bozuk dosya saklanmaz
                    yol.parent.mkdir(parents=True, exist_ok=True)
                    yol.write_bytes(y.ham)
                    yeni += 1
    return yeni


def parca(a: ay.Ayar) -> list[str]:
    istenen = os.environ.get("TTO_PARCA", "").split()
    if not istenen:
        return list(a.ciftler)
    bilinmeyen = [x for x in istenen if x not in a.ciftler]
    if bilinmeyen:
        raise SystemExit(f"TTO_PARCA'da ayar.toml'da olmayan parite: {bilinmeyen}")
    return istenen


def main() -> int:
    a = ay.oku()
    dizin = ay.DUKA
    semboller = parca(a)
    hiz = dk.hiz_kur(baslangic=a.hiz_baslangic, tavan=a.hiz_tavan)
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
    son_an = t0 + butce
    yapilan, kalan, eksik_birim = 0, 0, 0
    print(f"parça: {' '.join(semboller)} · başlangıç hızı {hiz.hiz:.1f} istek/sn · tavan {hiz.tavan:.1f}", flush=True)
    for sembol in semboller:
        for yil in range(a.baslangic.year, a.bitis.year + 1):
            anahtar = f"{sembol}/{yil}"
            yol = dizin / sembol / f"{yil}.parquet"
            son_hedef = min(a.bitis, date(yil, 12, 31)).isoformat()
            ilk_hedef = max(a.baslangic, date(yil, 1, 1)).isoformat()
            m = kunye["birimler"].get(anahtar)
            gecerli = bool(m) and yol.exists() and dk.oz(yol) == m.get("sha256") and m.get("ilk_gun") == ilk_hedef
            if gecerli and m.get("tam") and m.get("son_gun") == son_hedef:
                continue
            if time.monotonic() > son_an - 45:
                kalan += 1
                continue
            eski = None
            yalniz = None
            if gecerli:
                # Kaldığı yerden: yalnız hatalı günler ve bitiş ilerlediyse yeni günler.
                hatali = {date.fromisoformat(x[:10]) for x in m.get("gun_hata", [])}
                eski_son = date.fromisoformat(m["son_gun"])
                yeni_gunler = set(dk.gunler(eski_son, date.fromisoformat(son_hedef))) - {eski_son} \
                    if date.fromisoformat(son_hedef) > eski_son else set()
                yalniz = sorted(hatali | yeni_gunler)
                eski = pq.read_table(yol).to_pandas()
            t1 = time.monotonic()
            df, k = dk.yil_indir(sembol, yil, a.baslangic, a.bitis, a.es_zamanli, a.deneme, a.zaman_asimi_sn,
                                 yalniz=yalniz, son_an=son_an)
            sure = time.monotonic() - t1
            if eski is not None:
                df = (pd.concat([eski, df], ignore_index=True).drop_duplicates("t", keep="last")
                      .sort_values("t", kind="mergesort").reset_index(drop=True))
                for alan in ("gun_dolu_liste", "gun_bos", "gun_404"):
                    k[alan] = sorted(set(m.get(alan, [])) | set(k[alan]))
                k["dolgu_dakika"] = int(m.get("dolgu_dakika", 0)) + int(k["dolgu_dakika"])
                k["istek"] = int(m.get("istek", 0)) + int(k["istek"])
            k["ilk_gun"], k["son_gun"] = ilk_hedef, son_hedef
            k["gun"] = sum(1 for g in dk.gunler(date.fromisoformat(ilk_hedef), date.fromisoformat(son_hedef))
                           if dk.istenecek(g))
            # Cumartesiler istenmez (dk.istenecek); eski koşulardan kalan cumartesi kayıtları düşer.
            k["gun_bos"] = [x for x in k["gun_bos"] if dk.istenecek(date.fromisoformat(x[:10]))]
            k["gun_dolu"] = len(k["gun_dolu_liste"])
            k["satir"] = int(len(df))
            k["tam"] = not k["gun_hata"]
            k["sure_sn"] = round(sure, 1)
            k["indirme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if len(df):
                k["sha256"] = dk.yaz(df, yol)
                k["icerik_ozu"] = icerik_ozu(df)
                k["bayt"] = yol.stat().st_size
            olculen = k["istek"] / sure if sure > 0 else 0.0
            durum = "✓" if k["tam"] else "…"
            yapilan += 1
            eksik_birim += 0 if k["tam"] else 1
            print(f"{durum} {anahtar}: {k['satir']:,} dakika · {k['gun_dolu']}/{k['gun']} gün dolu · "
                  f"{len(k['gun_hata'])} gün eksik · {k.get('bayt', 0) / 1e6:.1f} MB · {sure:.0f} sn · "
                  f"{olculen:.1f} istek/sn", flush=True)
            if k["gun_hata"]:
                print(f"    eksik örnek: {k['gun_hata'][:2]}", flush=True)
            kunye["birimler"][anahtar] = k
            dk.kunye_yaz(dizin, kunye, [sembol])     # her birimden sonra: koşu kesilse de ilerleme kalır
            s = hiz.sayac
            print(f"    hız şimdi {hiz.hiz:.2f} istek/sn (en düşük {s['en_dusuk_hiz']:.2f}, en yüksek "
                  f"{s['en_yuksek_hiz']:.2f}) · ret {s['ret']} · ağ hatası {s['ag']} · bekleme {s['bekleme_sn']:.0f} sn",
                  flush=True)
    if time.monotonic() < son_an - 60:
        n = saatlik_indir(a, semboller, son_an - 30)
        print(f"saatlik çapraz sınama dosyası: {n} yeni")
    dk.kunye_yaz(dizin, kunye, semboller)
    toplam = len(semboller) * (a.bitis.year - a.baslangic.year + 1)
    tamam = sum(1 for x, v in kunye["birimler"].items() if v.get("tam") and x.split("/")[0] in semboller)
    print(f"özet ({' '.join(semboller)}): bu koşuda {yapilan} birim işlendi · {eksik_birim} birimde eksik gün "
          f"kaldı · {kalan} birim bütçeye kaldı · parçada {tamam}/{toplam} birim tam · "
          f"{time.monotonic() - t0:.0f} sn · istek {hiz.sayac['tamam']} başarılı, {hiz.sayac['ret']} ret")
    # Eksik gün ya da bütçeye kalan birim bir kusur değil, sürecek iştir: bir sonraki
    # koşu kaldığı yerden devam eder. Çıkış 0 — commit adımı her durumda koşar.
    return 0


if __name__ == "__main__":
    sys.exit(main())
