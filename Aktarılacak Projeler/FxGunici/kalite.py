#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dukascopy arşivinin kalite denetimi — boşluk, tatil, makas, sıçrama, çapraz sınama.

Neyi ölçer, neyi ölçmez:
  1. KAPSAM — her FX işlem gününün (önceki gün 17:00 ET → bugün 17:00 ET, 1440
     dakika) kaç dakikasında kotasyon var; eksik dakikaların ARDIŞIK koşuları
     (boşluk) uzunluklarına göre; işlem saatleri dışında (hafta sonu) kotasyon.
  2. TATİL — kapsamı %50'nin altında kalan işlem günleri (Noel, yılbaşı vb.) ve
     %50–90 arası kısmi günler. Ders bunları adıyla dışarıda bırakır; sessizce değil.
  3. MAKAS — sıfır ve negatif makas (ask ≤ bid) sayısı; saat saat medyan ve
     95. yüzdelik; 17:00 ET devir dakikalarının makas profili (gün sonu
     kapanış saatinin gerekçesi).
  4. SIÇRAMA — 1 dakikalık orta fiyat getirisinde günün sağlam oynaklığının
     (MAD) 12 katını aşan ve ertesi dakika %70'ten fazlası geri dönen hareket
     ("kötü kotasyon" adayı); ayrıca gövdenin dışına uzanan aşırı fitil. Aday
     sayılır ve listelenir — veri DEĞİŞTİRİLMEZ. Haberle çakışanlar ayrıca
     işaretlenir (haber takvimi kurulduktan sonra).
  5. ÇAPRAZ SINAMA — dakika arşivinden kurulan saatlik bid mumları,
     Dukascopy'nin KENDİ saatlik mum dosyalarıyla alan alan karşılaştırılır
     (Ocak ve Temmuz ayları). Çözücüde ya da dolgu dakikalarının atılmasında bir
     kusur olsaydı burada görünürdü.

Koşum:  .venv/bin/python kalite.py            (bütün pariteler → veri/dukascopy/kalite.json)
        .venv/bin/python kalite.py EURUSD     (tek parite)
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

import ayar as ay
import dukascopy as dk
import zaman as z

SICRAMA_K = 12.0
SICRAMA_DONUS = 0.70
FITIL_K = 12.0


def beklenen_izgara(bas: date, bit: date) -> tuple[pd.DatetimeIndex, np.ndarray]:
    """Penceredeki hafta içi işlem günleri ve her birinin ilk dakikası (UTC epoch sn)."""
    gunler = pd.date_range(bas, bit, freq="D")
    gunler = gunler[gunler.dayofweek < 5]
    onceki = gunler - pd.Timedelta(days=1)
    bas_utc = z.yerel_utc(onceki, "17:00", z.NEWYORK)
    return gunler, bas_utc.as_unit("s").asi8


def _kosular(eksik: np.ndarray) -> np.ndarray:
    """Bir boolean dizideki True koşularının uzunlukları."""
    if not eksik.any():
        return np.empty(0, dtype=np.int64)
    d = np.diff(np.concatenate([[0], eksik.astype(np.int8), [0]]))
    basl, bit = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return bit - basl


def kapsam(t: np.ndarray, gunler: pd.DatetimeIndex, bas_sn: np.ndarray) -> dict:
    izgara = bas_sn[:, None] + np.arange(1440, dtype=np.int64)[None, :] * 60
    var = np.isin(izgara, t, assume_unique=False)
    gun_kapsam = var.mean(axis=1)
    kova = {"1": 0, "2-4": 0, "5-14": 0, "15-59": 0, "60+": 0}
    en_uzun = []
    normal = gun_kapsam >= 0.9
    for i in np.flatnonzero(normal):
        eksik = ~var[i]
        for L in _kosular(eksik):
            if L == 1:
                kova["1"] += 1
            elif L < 5:
                kova["2-4"] += 1
            elif L < 15:
                kova["5-14"] += 1
            elif L < 60:
                kova["15-59"] += 1
            else:
                kova["60+"] += 1
        if (~var[i]).any():
            Ls = _kosular(~var[i])
            if Ls.max() >= 15:
                # en uzun koşunun başlangıcı
                d = np.diff(np.concatenate([[0], (~var[i]).astype(np.int8), [0]]))
                b = np.flatnonzero(d == 1)
                j = int(np.argmax(Ls))
                an = pd.Timestamp(int(bas_sn[i] + b[j] * 60), unit="s", tz="UTC")
                en_uzun.append((int(Ls[j]), an))
    en_uzun.sort(key=lambda x: -x[0])
    disari = int((~np.isin(t, izgara.ravel())).sum())
    tatil = [(gunler[i].date().isoformat(), round(float(gun_kapsam[i]) * 100, 1))
             for i in np.flatnonzero(gun_kapsam < 0.5)]
    kismi = [(gunler[i].date().isoformat(), round(float(gun_kapsam[i]) * 100, 1))
             for i in np.flatnonzero((gun_kapsam >= 0.5) & (gun_kapsam < 0.9))]
    normal_eksik = int((~var[normal]).sum())
    return {
        "islem_gunu": int(len(gunler)),
        "beklenen_dakika": int(var.size),
        "kotasyonlu_dakika": int(var.sum()),
        "kapsam_yuzde": round(float(var.mean()) * 100, 3),
        "normal_gun": int(normal.sum()),
        "normal_gun_eksik_dakika": normal_eksik,
        "normal_gun_kapsam_yuzde": round(float(var[normal].mean()) * 100, 3),
        "bosluk_kovalari": kova,
        "en_uzun_bosluklar": [{"uzunluk_dk": L, "baslangic_utc": an.strftime("%Y-%m-%d %H:%M"),
                               "tsi": z.tsi([an])[0].strftime("%H:%M")} for L, an in en_uzun[:10]],
        "tatil_gunleri": tatil,
        "kismi_gunler": kismi,
        "islem_saati_disi_dakika": disari,
    }


def makas(f: pd.DataFrame, pip: float) -> dict:
    sc, so = f["spr_c"].to_numpy() / pip, f["spr_o"].to_numpy() / pip
    sonuc = {
        "sifir_kapanis": int((np.abs(sc) < 1e-9).sum()),
        "sifir_acilis": int((np.abs(so) < 1e-9).sum()),
        "negatif_kapanis": int((sc < -1e-9).sum()),
        "negatif_acilis": int((so < -1e-9).sum()),
        "medyan_pip": round(float(np.median(sc)), 3),
        "p95_pip": round(float(np.percentile(sc, 95)), 3),
        "p99_pip": round(float(np.percentile(sc, 99)), 3),
    }
    # New York saatine göre saat saat (devir 17:00 ET'de)
    ny = f.index.tz_convert(z.NEWYORK)
    saat = pd.Series(sc, index=ny.hour)
    g = saat.groupby(level=0)
    sonuc["saatlik_ny"] = {int(h): {"medyan": round(float(v.median()), 3), "p95": round(float(v.quantile(0.95)), 3)}
                           for h, v in g}
    # Devir profili: 17:00 ET'ye göre −30 … +30 dakika
    dk_ = (ny.hour * 60 + ny.minute).to_numpy()
    fark = dk_ - 17 * 60
    profil = {}
    for d in range(-30, 31, 5):
        m = (fark >= d) & (fark < d + 5)
        if m.any():
            profil[d] = round(float(np.median(sc[m])), 3)
    sonuc["devir_profili_medyan_pip"] = profil
    # Yıllık medyan — besleme kalitesi zamanla değişiyor mu
    yil = pd.Series(sc, index=f.index.year)
    sonuc["yillik_medyan_pip"] = {int(y): round(float(v.median()), 3) for y, v in yil.groupby(level=0)}
    return sonuc


def sicrama(f: pd.DataFrame, pip: float) -> dict:
    c = f["c"].to_numpy()
    r = np.diff(np.log(c))
    t = f.index[1:]
    gun = z.islem_gunu(t)
    s = pd.Series(r, index=t)
    mad = s.abs().groupby(gun).transform("median").to_numpy() * 1.4826
    mad = np.where(mad > 0, mad, np.nan)
    z_ = np.abs(r) / mad
    ileri = np.concatenate([r[1:], [0.0]])
    don = (np.sign(ileri) == -np.sign(r)) & (np.abs(ileri) > SICRAMA_DONUS * np.abs(r))
    aday = (z_ > SICRAMA_K) & don
    hareket_pip = np.abs(np.diff(c)) / pip
    idx = np.flatnonzero(aday)
    liste = sorted(((float(hareket_pip[i]), t[i]) for i in idx), key=lambda x: -x[0])[:10]
    # Fitil: gövdenin dışına uzanan kısım, günün medyan dakika aralığının FITIL_K katından büyük ve > 5 pip
    o, h, l = f["o"].to_numpy(), f["h"].to_numpy(), f["l"].to_numpy()
    govde_ust, govde_alt = np.maximum(o, c), np.minimum(o, c)
    fitil = np.maximum(h - govde_ust, govde_alt - l)
    aralik = pd.Series(h - l, index=f.index).groupby(z.islem_gunu(f.index)).transform("median").to_numpy()
    asiri = (fitil > FITIL_K * np.maximum(aralik, 1e-12)) & (fitil / pip > 5)
    return {
        "aday": int(aday.sum()),
        "aday_yillik": {int(y): int(n) for y, n in pd.Series(aday, index=t.year).groupby(level=0).sum().items()},
        "en_buyuk": [{"utc": an.strftime("%Y-%m-%d %H:%M"), "tsi": z.tsi([an])[0].strftime("%d.%m.%Y %H:%M"),
                      "pip": round(p, 1)} for p, an in liste],
        "asiri_fitil": int(asiri.sum()),
    }


def capraz(f_ham: pd.DataFrame, sembol: str, nokta: float) -> dict:
    """Dakika arşivinden kurulan saatlik bid mumları ↔ Dukascopy saatlik dosyaları."""
    dizin = ay.DUKA / "saatlik" / sembol
    if not dizin.exists():
        return {"durum": "saatlik dosya yok"}
    t = pd.to_datetime(f_ham["t"].to_numpy(np.int64), unit="s", utc=True)
    b = pd.DataFrame({"o": f_ham["b_o"].to_numpy(), "h": f_ham["b_h"].to_numpy(),
                      "l": f_ham["b_l"].to_numpy(), "c": f_ham["b_c"].to_numpy(),
                      "v": f_ham["b_v"].to_numpy(np.float64)}, index=t)
    saat = b.resample("1h").agg({"o": "first", "h": "max", "l": "min", "c": "last", "v": "sum"}).dropna()
    toplam = esit = 0
    alan_esit = {"o": 0, "h": 0, "l": 0, "c": 0}
    hacim_fark = []
    ornek = []
    for yol in sorted(dizin.glob("*_BID.bi5")):
        yil, ay_ = (int(x) for x in yol.stem.split("_")[0].split("-"))
        k = dk.coz(yol.read_bytes(), adim_sn=3600, azami=744)
        k = k[k["v"] > 0]
        t0 = pd.Timestamp(year=yil, month=ay_, day=1, tz="UTC")
        ix = t0 + pd.to_timedelta(k["s"].astype(np.int64), unit="s")
        ref = pd.DataFrame({"o": k["o"], "h": k["h"], "l": k["l"], "c": k["c"], "v": k["v"].astype(np.float64)}, index=ix)
        ort = ref.join(saat, how="inner", lsuffix="_ref")
        for a in "ohlc":
            alan_esit[a] += int((ort[f"{a}_ref"].astype(np.int64) == ort[a].astype(np.int64)).sum())
        tam = (ort[["o_ref", "h_ref", "l_ref", "c_ref"]].astype(np.int64).to_numpy()
               == ort[["o", "h", "l", "c"]].astype(np.int64).to_numpy()).all(axis=1)
        toplam += len(ort)
        esit += int(tam.sum())
        hacim_fark.extend(((ort["v"] - ort["v_ref"]) / ort["v_ref"].where(ort["v_ref"] > 0)).dropna().tolist())
        for an in ort.index[~tam][:2]:
            if len(ornek) < 6:
                r = ort.loc[an]
                ornek.append({"utc": an.strftime("%Y-%m-%d %H:%M"),
                              "ref": [int(r[f"{a}_ref"]) for a in "ohlc"], "arsiv": [int(r[a]) for a in "ohlc"]})
    hf = np.abs(np.array(hacim_fark)) if hacim_fark else np.array([np.nan])
    return {
        "saat": toplam,
        "tam_esit": esit,
        "tam_esit_yuzde": round(100 * esit / toplam, 3) if toplam else None,
        "alan_esit_yuzde": {a: round(100 * n / toplam, 3) if toplam else None for a, n in alan_esit.items()},
        "hacim_goreli_fark_medyan": float(np.nanmedian(hf)),
        "uyusmayan_ornekler": ornek,
    }


def denetle(sembol: str, a: ay.Ayar) -> dict:
    ham = dk.oku_ham(ay.DUKA, sembol)
    ham = ham[(ham["t"] >= int(pd.Timestamp(a.baslangic, tz="UTC").timestamp()))
              & (ham["t"] < int(pd.Timestamp(a.bitis + timedelta(days=1), tz="UTC").timestamp()))]
    f = dk.fiyatla(ham, a.nokta[sembol])
    gunler, bas_sn = beklenen_izgara(a.baslangic + timedelta(days=1), a.bitis)
    t = ham["t"].to_numpy(np.int64)
    sonuc = {
        "satir": int(len(ham)),
        "ilk": f.index[0].strftime("%Y-%m-%d %H:%M"),
        "son": f.index[-1].strftime("%Y-%m-%d %H:%M"),
        "kapsam": kapsam(t, gunler, bas_sn),
        "makas": makas(f, a.pip[sembol]),
        "sicrama": sicrama(f, a.pip[sembol]),
        "capraz": capraz(ham, sembol, a.nokta[sembol]),
        "hacim": {"sifir_hacimli_dakika": int(((ham["b_v"] == 0) & (ham["a_v"] == 0)).sum()),
                  "medyan": float(np.median(ham["b_v"] + ham["a_v"]))},
    }
    return sonuc


def yazdir(sembol: str, s: dict) -> None:
    k, m, sc, cp = s["kapsam"], s["makas"], s["sicrama"], s["capraz"]
    print(f"\n━━ {sembol}  {s['ilk']} → {s['son']} UTC  ·  {s['satir']:,} dakika")
    print(f"  kapsam: {k['kapsam_yuzde']}% ({k['kotasyonlu_dakika']:,}/{k['beklenen_dakika']:,})  ·  "
          f"normal günlerde {k['normal_gun_kapsam_yuzde']}% ({k['normal_gun']} gün)")
    print(f"  boşluklar (normal günler): {k['bosluk_kovalari']}")
    print(f"  tatil (<%50): {len(k['tatil_gunleri'])} gün · kısmi (%50–90): {len(k['kismi_gunler'])} gün · "
          f"işlem saati dışı kotasyon: {k['islem_saati_disi_dakika']:,} dk")
    print(f"  makas: medyan {m['medyan_pip']} pip · p95 {m['p95_pip']} · p99 {m['p99_pip']} · "
          f"sıfır (kapanış) {m['sifir_kapanis']:,} · negatif {m['negatif_kapanis']:,}")
    print(f"  devir profili (17:00 ET'ye göre dk → medyan pip): {m['devir_profili_medyan_pip']}")
    print(f"  sıçrama adayı: {sc['aday']} · aşırı fitil: {sc['asiri_fitil']} · en büyükler: {sc['en_buyuk'][:3]}")
    if "tam_esit_yuzde" in cp:
        print(f"  çapraz sınama (saatlik): {cp['tam_esit']}/{cp['saat']} saat birebir ({cp['tam_esit_yuzde']}%) · "
              f"alan alan {cp['alan_esit_yuzde']}")
    else:
        print(f"  çapraz sınama: {cp}")


def main(argv: list[str]) -> int:
    a = ay.oku()
    hedef = argv or list(a.ciftler)
    rapor = {}
    yol = ay.DUKA / "kalite.json"
    if yol.exists():
        rapor = json.loads(yol.read_text(encoding="utf-8"))
    for c in hedef:
        rapor[c] = denetle(c, a)
        yazdir(c, rapor[c])
    yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
