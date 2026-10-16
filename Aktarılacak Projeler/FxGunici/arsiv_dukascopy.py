#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dukascopy 1 dakikalık bid/ask arşivini kurar (kaldığı yerden sürer).

Koşum (iki yol, aynı betik):
  · Bulut: `.github/workflows/arastirma-veri.yml`, betik =
    "Aktarılacak Projeler/FxGunici/arsiv_dukascopy.py", paketler = "pyarrow==26.0.0" (arşivin baytlarını
    pyarrow belirler; sürümü künyeye de yazılır).
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

PARÇA. `TTO_PARCA` ortam değişkeni boşlukla ayrık jetonlar alır: `EURUSD` (paritenin
bütün yılları), `EURUSD-2019` (tek yıl) ya da `EURUSD-2018-2020` (aralık). İş akışı
parçaları ayrı koşucularda aynı anda çalıştırır (`parcalar` girdisi); her iş yalnız
kendi birimlerinin parquet ve künye dosyalarına yazar (`kunye/<SEMBOL>_<YYYY>.json`),
dala gönderirken çakışma doğmaz.

KUYRUK. Bir parçanın eksik bütün dosyaları TEK ertelemeli kuyruğa girer
(`dukascopy.toplu_getir`): kaynağın geçici olarak reddettiği dosya bir dakika sonra
yeniden istenir, öbürleri beklemez; birimler liste sırasıyla tamamlanır.
"""
from __future__ import annotations

import os
import platform
import re
import sys
import time
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq

import ayar as ay
import dukascopy as dk
import ozler


def icerik_ozu(df) -> str:
    """Dosya kodlamasından bağımsız içerik özü (tek tanım: dukascopy.icerik_ozu; okuyucu da onu sınar)."""
    return dk.icerik_ozu(df)


def saatlik_indir(a: ay.Ayar, birimler: list[tuple[str, int]], son_an: float) -> int:
    hedef = ay.DUKA / "saatlik"
    yeni = 0
    for sembol, yil in birimler:
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
    if hedef.exists():
        ozler.yaz(hedef)        # saatlik dosyaların SHA-256 sabitlemesi (kalite.py okumadan önce sınar)
    return yeni


JETON = re.compile(r"^([A-Z]{6})(?:-(\d{4})(?:-(\d{4}))?)?$")


def parca(a: ay.Ayar) -> list[tuple[str, int]]:
    """`TTO_PARCA` jetonlarından (parite, yıl) birimleri; boşsa bütün birimler."""
    ilk, son = a.baslangic.year, a.bitis.year
    istenen = os.environ.get("TTO_PARCA", "").split()
    if not istenen:
        return [(s, y) for s in a.ciftler for y in range(ilk, son + 1)]
    out: list[tuple[str, int]] = []
    for j in istenen:
        m = JETON.match(j)
        if not m:
            raise SystemExit(f"TTO_PARCA jetonu tanınmadı: {j!r} (SEMBOL · SEMBOL-YYYY · SEMBOL-YYYY-YYYY)")
        sembol = m.group(1)
        if sembol not in a.ciftler:
            raise SystemExit(f"TTO_PARCA'da ayar.toml'da olmayan parite: {sembol}")
        y1 = int(m.group(2)) if m.group(2) else ilk
        y2 = int(m.group(3)) if m.group(3) else (y1 if m.group(2) else son)
        if not ilk <= y1 <= y2 <= son:
            raise SystemExit(f"TTO_PARCA yılı kapsam dışında: {j} (kapsam {ilk}–{son})")
        out += [(sembol, y) for y in range(y1, y2 + 1)]
    return list(dict.fromkeys(out))


def main() -> int:
    a = ay.oku()
    dizin = ay.DUKA
    birimler = parca(a)
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
    son_an = t0 + a.butce_dk * 60
    ad = " ".join(f"{s}-{y}" for s, y in birimler)
    print(f"parça: {ad} · başlangıç hızı {hiz.hiz:.1f} istek/sn · tavan {hiz.tavan:.1f} · "
          f"eşzamanlı {a.es_zamanli}", flush=True)

    # 1) Plan: tamamlanmamış her birimin istenecek günleri.
    plan = []
    for sembol, yil in birimler:
        anahtar = f"{sembol}/{yil}"
        yol = dizin / sembol / f"{yil}.parquet"
        son_hedef = min(a.bitis, date(yil, 12, 31))
        ilk_hedef = max(a.baslangic, date(yil, 1, 1))
        m = kunye["birimler"].get(anahtar)
        gecerli = (bool(m) and yol.exists() and dk.oz(yol) == m.get("sha256")
                   and m.get("ilk_gun") == ilk_hedef.isoformat())
        if gecerli and m.get("tam") and m.get("son_gun") == son_hedef.isoformat():
            continue
        yalniz = None
        if gecerli:
            # Kaldığı yerden: yalnız hatalı günler ve bitiş ilerlediyse yeni günler.
            hatali = {date.fromisoformat(x[:10]) for x in m.get("gun_hata", [])}
            eski_son = date.fromisoformat(m["son_gun"])
            yeni_gunler = set(dk.gunler(eski_son, son_hedef)) - {eski_son} if son_hedef > eski_son else set()
            yalniz = sorted(hatali | yeni_gunler)
        liste = dk.gun_listesi(yil, a.baslangic, a.bitis, yalniz)
        plan.append((anahtar, sembol, yil, yol, m if gecerli else None, ilk_hedef, son_hedef, liste))
    urller = [dk.dakika_url(s, g, t) for (_, s, _, _, _, _, _, liste) in plan for g in liste for t in ("BID", "ASK")]
    print(f"plan: {len(plan)} birim eksik · {len(urller):,} dosya", flush=True)

    # 2) Tek ertelemeli kuyruk.
    olcum: dict = {}
    yanitlar = dk.toplu_getir(urller, a.es_zamanli, a.zaman_asimi_sn, son_an - 30, a.tavan_deneme, a.ara_sn,
                              olcum=olcum) if urller else {}
    sure = time.monotonic() - t0

    # 3) Her birimi kur, var olan arşivle birleştir, yaz.
    yapilan, kalan, eksik_birim = 0, 0, 0
    for anahtar, sembol, yil, yol, m, ilk_hedef, son_hedef, liste in plan:
        yan = {(g, t): yanitlar[dk.dakika_url(sembol, g, t)] for g in liste for t in ("BID", "ASK")}
        if not any(y.deneme for y in yan.values()):
            kalan += 1            # bu koşuda hiç denenmedi (bütçe): birime dokunulmaz
            continue
        df, k = dk.yil_kur(yil, a.baslangic, a.bitis, liste, lambda g, t: yan[(g, t)])
        if m is not None:
            eski = pq.read_table(yol).to_pandas()
            df = (pd.concat([eski, df], ignore_index=True).drop_duplicates("t", keep="last")
                  .sort_values("t", kind="mergesort").reset_index(drop=True))
            for alan in ("gun_dolu_liste", "gun_bos", "gun_404"):
                k[alan] = sorted(set(m.get(alan, [])) | set(k[alan]))
            for alan in ("dolgu_dakika", "istek", "ret"):
                k[alan] = int(m.get(alan, 0)) + int(k[alan])
        k["ilk_gun"], k["son_gun"] = ilk_hedef.isoformat(), son_hedef.isoformat()
        k["gun"] = sum(1 for g in dk.gunler(ilk_hedef, son_hedef) if dk.istenecek(g))
        # Cumartesiler istenmez (dk.istenecek); eski koşulardan kalan cumartesi kayıtları düşer.
        k["gun_bos"] = [x for x in k["gun_bos"] if dk.istenecek(date.fromisoformat(x[:10]))]
        k["gun_dolu"] = len(k["gun_dolu_liste"])
        k["satir"] = int(len(df))
        k["tam"] = not k["gun_hata"]
        k["indirme"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        k["kod_ozu"] = kunye["kod_ozu"]
        if len(df):
            k["sha256"] = dk.yaz(df, yol)
            k["icerik_ozu"] = icerik_ozu(df)
            k["bayt"] = yol.stat().st_size
        yapilan += 1
        eksik_birim += 0 if k["tam"] else 1
        print(f"{'✓' if k['tam'] else '…'} {anahtar}: {k['satir']:,} dakika · {k['gun_dolu']}/{k['gun']} gün dolu · "
              f"{len(k['gun_hata'])} gün eksik · {k.get('bayt', 0) / 1e6:.1f} MB", flush=True)
        if k["gun_hata"]:
            print(f"    eksik örnek: {k['gun_hata'][:2]}", flush=True)
        kunye["birimler"][anahtar] = k
        dk.kunye_yaz(dizin, kunye, [anahtar])

    # 4) Ölçüm: deneme sırasına göre sonuç, geçici hata türleri, başarılı istek süresi.
    s = hiz.sayac
    istek = s["tamam"] + s["ret"] + s["ag"]
    print(f"indirme: {sure:.0f} sn · {istek} istek ({istek / sure if sure > 0 else 0:.2f}/sn) · hız şimdi "
          f"{hiz.hiz:.2f} (en düşük {s['en_dusuk_hiz']:.2f}, en yüksek {s['en_yuksek_hiz']:.2f}) · "
          f"bekleme {s['bekleme_sn']:.0f} sn", flush=True)
    for n in sorted(olcum.get("deneme", {}), key=int):
        print(f"    deneme {n}: {olcum['deneme'][n]}", flush=True)
    if olcum.get("gecici"):
        print(f"    geçici hata türleri: {olcum['gecici']}", flush=True)
    if olcum.get("sure_tamam"):
        q = np.quantile(olcum["sure_tamam"], [0.5, 0.9, 0.99])
        print(f"    başarılı istek süresi: medyan {q[0]:.2f} · p90 {q[1]:.2f} · p99 {q[2]:.2f} sn", flush=True)

    if time.monotonic() < son_an - 60:
        n = saatlik_indir(a, birimler, son_an - 30)
        print(f"saatlik çapraz sınama dosyası: {n} yeni")
    tamam = sum(1 for s_, y_ in birimler if kunye["birimler"].get(f"{s_}/{y_}", {}).get("tam"))
    print(f"özet ({ad}): bu koşuda {yapilan} birim işlendi · {eksik_birim} birimde eksik gün kaldı · "
          f"{kalan} birim bütçeye kaldı · parçada {tamam}/{len(birimler)} birim tam · "
          f"{time.monotonic() - t0:.0f} sn")
    # Eksik gün ya da bütçeye kalan birim bir kusur değil, sürecek iştir: bir sonraki
    # koşu kaldığı yerden devam eder. Çıkış 0 — commit adımı her durumda koşar.
    return 0


if __name__ == "__main__":
    sys.exit(main())
