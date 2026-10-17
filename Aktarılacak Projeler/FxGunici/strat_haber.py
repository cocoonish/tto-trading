#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber stratejileri N1–N5, kırılım ↔ fade devam tablosu, FOMC karar ↔ basın, olay patikaları.

Mumlar olay anına ÇIPALIDIR: k. mum [t0 + k·tf, t0 + (k+1)·tf); ilk haber mumu
k = 0. Bütün resmi olay saatleri çeyrek saatin katı olduğu için 5 ve 15
dakikalık UTC ızgarası zaten çıpalıdır; 60 dakikada ofset olayın dakikasıdır
(NY 08:30 → 30, ECB 13:45 → 45). Olay saati ızgaraya düşmüyorsa (kullanıcının ek
dosyasında 08:20 gibi) olay o zaman diliminde ATLANIR ve sebebiyle sayılır.
ATR, olaydan ÖNCEKİ 14 mumdan (aynı ızgara) — olay mumunu içermez.

Bir stratejinin sinyal tablosu her satırda kendi `ofset`ini taşır (60 dakikada
olaydan olaya değişir); işlemler olay × ofset grubunda koşturulur (kapanış stop'u
her grubun kendi mum sonunda sorulur). Tek pozisyon kuralı ise PARİTE BAŞINA
geçerlidir (ön kaydın ortak mekaniği): aynı gün iki olay varsa (FOMC kararı 14:00
ve basın toplantısı 14:30) ikincisinin işlemi ancak birincisinin pozisyonu
kapandıysa açılır. Gruplar tek pozisyon kuralı olmadan koşturulur, kural sonra
bütün işlemlere giriş sırasıyla uygulanır.

SÜRPRİZ VEKİLİ. Konsensüs beklentisi elimizde yok; sürpriz yerine ilk haber
mumunun hareketi ATR'ye bölünerek kullanılır (|kapanış − açılış| / ATR). Bu bir
ÖLÇÜM değil vekildir: büyük hareket büyük sürprizin de, sığ likiditenin de
sonucu olabilir. Derste bu açıkça yazılır.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

import zaman as z
from gunluk import Baglam
from strat_ortak import atr_mum, kos, tek_pozisyon_uygula
from veri import mum_dizini

ONKAYIT = tomllib.loads((Path(__file__).resolve().parent / "onkayit.toml").read_text(encoding="utf-8"))
H = ONKAYIT["haber"]
KOVA = [float(x) for x in H["kova_atr"]]
KOVA_ADI = ["<0,5", "0,5–1", "1–2", ">2"]
ATR_MUM = int(H["atr_mum"])
TREND_MUM = int(H["oncesi_trend_mum"])
SUTUN = ["gun_k", "s", "yon", "stop", "yapi", "ust", "alt", "olay", "tarih", "t0", "ofset", "kova",
         "trend_uyum", "hareket_atr"]


def kova_adi(oran: float) -> str:
    return KOVA_ADI[int(np.searchsorted(KOVA, abs(oran), side="right"))]


def gun_sirasi(b: Baglam, t_sn) -> np.ndarray:
    """UTC epoch saniyelerinin FX işlem günü sırası (−1: tabloda yok)."""
    t = np.atleast_1d(np.asarray(t_sn, dtype=np.int64))
    etiket = z.islem_gunu(pd.to_datetime(t, unit="s", utc=True)).to_numpy().astype("datetime64[D]")
    return b.g.indeks(etiket)


def olay_cercevesi(b: Baglam, tf: int, olaylar: pd.DataFrame, on_trend: int = TREND_MUM) -> pd.DataFrame:
    """Her olay için çıpalı mum dizini, ATR, ilk mum hareketi, haber öncesi trend.

    Atlanan olaylar sebebiyle `b.ek[("haber_atlanan", tf)]` sayacına, adıyla (olay, tarih, sebep)
    `b.ek[("haber_atlanan_olay", tf)]` listesine yazılır: takvimde durup hiçbir haber ölçüsüne girmeyen bir olay
    (ör. piyasa kapalıyken, pazar 17:00 New York'ta açıklanan karar) sayıyla değil adıyla görünsün.
    """
    satir = []
    atlanan: dict[str, int] = {}
    atlanan_olay: list[dict] = []
    def atla(neden):
        atlanan[neden] = atlanan.get(neden, 0) + 1
        atlanan_olay.append({"olay": str(o["olay"]), "tarih": str(o["tarih"]), "neden": neden})
    for _, o in olaylar.iterrows():
        t0 = int(o["utc_sn"])
        dk = (t0 // 60) % 60
        if tf < 60 and dk % tf:
            atla("izgara_disi")
            continue
        ofset = dk if tf == 60 else 0
        m = b.mumlar(tf, ofset)
        k0 = int(mum_dizini(m, np.array([t0]))[0])
        if k0 < 0:
            atla("olay_mumu_yok")
            continue
        pencere = on_trend + ATR_MUM + 1
        if k0 < pencere or k0 + 1 >= len(m):
            atla("veri_kenari")
            continue
        # Olay öncesi ATR ve trend penceresi bir boşluğun (hafta sonu, veri kesintisi)
        # üstünden ölçülmez: pazar 17:00 ET'deki olağanüstü bir karar cuma barlarıyla kıyaslanırdı.
        if m.bt[k0] - m.bt[k0 - pencere] > (pencere + 6) * tf * 60:
            atla("on_pencerede_bosluk")
            continue
        atr = atr_mum(m, ATR_MUM)[k0 - 1]
        if not np.isfinite(atr) or atr <= 0:
            atla("atr_yok")
            continue
        if m.n[k0] < max(1, tf // 2):
            atla("seyrek_mum")
            continue
        gun_k = int(b.g.indeks(np.array([m.gun[k0]]))[0])
        if gun_k < 0 or b.g.tatil[gun_k]:
            atla("tatil")
            continue
        hareket = float(m.c[k0] - m.o[k0])
        trend = float(m.c[k0 - 1] - m.c[k0 - 1 - on_trend])
        if hareket == 0 or trend == 0:
            uyum = "belirsiz"
        else:
            uyum = "aynı" if np.sign(trend) == np.sign(hareket) else "ters"
        satir.append({"olay": o["olay"], "tarih": o["tarih"], "t0": t0, "ofset": ofset, "k0": k0,
                      "gun_k": gun_k, "atr": float(atr), "hareket": hareket, "hareket_atr": hareket / atr,
                      "kova": kova_adi(hareket / atr), "trend_uyum": uyum})
    b.ek[("haber_atlanan", tf)] = atlanan
    b.ek[("haber_atlanan_olay", tf)] = atlanan_olay
    return pd.DataFrame(satir, columns=["olay", "tarih", "t0", "ofset", "k0", "gun_k", "atr", "hareket",
                                        "hareket_atr", "kova", "trend_uyum"])


def cerceve(b: Baglam, tf: int) -> pd.DataFrame:
    """Bağlamın takvimi için olay çerçevesi (bağlamda önbellekli)."""
    anahtar = ("haber_cer", tf)
    if anahtar not in b.ek:
        olaylar = b.olaylar if b.olaylar is not None and len(b.olaylar) else pd.DataFrame(columns=["olay", "tarih", "utc_sn"])
        b.ek[anahtar] = olay_cercevesi(b, tf, olaylar)
    return b.ek[anahtar]


def _satir(c, s, yon, stop, yapi, **ek) -> dict:
    return {"gun_k": int(c["gun_k"]), "s": int(s), "yon": int(yon), "stop": float(stop), "yapi": float(yapi),
            "ust": np.nan, "alt": np.nan, "olay": c["olay"], "tarih": c["tarih"], "t0": int(c["t0"]),
            "ofset": int(c["ofset"]), "kova": c["kova"], "trend_uyum": c["trend_uyum"],
            "hareket_atr": float(c["hareket_atr"]), **ek}


def _tablo(out: list[dict], ek_sutun=()) -> pd.DataFrame:
    return pd.DataFrame(out, columns=SUTUN + list(ek_sutun))


def n1(b: Baglam, tf: int, giris_mumu: int):
    """İlk haber mumunun yönünde, `giris_mumu` mum kapandıktan sonra."""
    out = []
    for _, c in cerceve(b, tf).iterrows():
        m = b.mumlar(tf, int(c["ofset"]))
        k0 = int(c["k0"])
        if c["hareket"] == 0:
            continue
        yon = 1 if c["hareket"] > 0 else -1
        s = k0 + int(giris_mumu) - 1
        if s + 1 >= len(m):
            continue
        stop = m.l[k0] if yon == 1 else m.h[k0]
        out.append(_satir(c, s, yon, stop, m.h[k0] - m.l[k0]))
    return _tablo(out), None


def n2(b: Baglam, tf: int, k: float, giris: str):
    """|ilk hareket| > k·ATR ise ters yönde: ilk kapanışta ya da ters kapanan teyit mumundan sonra."""
    out = []
    for _, c in cerceve(b, tf).iterrows():
        if abs(c["hareket_atr"]) <= k:
            continue
        m = b.mumlar(tf, int(c["ofset"]))
        k0 = int(c["k0"])
        itki = 1 if c["hareket"] > 0 else -1
        if giris == "ilk_kapanis":
            s = k0
        else:
            s = -1
            for q in range(k0 + 1, min(k0 + 4, len(m) - 1)):
                if (m.c[q] - m.o[q]) * itki < 0:
                    s = q
                    break
            if s < 0:
                continue
        stop = m.h[k0:s + 1].max() if itki == 1 else m.l[k0:s + 1].min()
        out.append(_satir(c, s, -itki, stop, m.h[k0] - m.l[k0], seviye=float(m.o[k0])))
    return _tablo(out, ["seviye"]), None


def n3(b: Baglam, tf: int, on_mum: int, stop_yeri: str):
    """Haber öncesi aralığın dışında kapanan ilk mumun yönünde (olaydan sonraki 6 mum içinde)."""
    out = []
    for _, c in cerceve(b, tf).iterrows():
        m = b.mumlar(tf, int(c["ofset"]))
        k0 = int(c["k0"])
        Hs, Ls = m.h[k0 - on_mum:k0].max(), m.l[k0 - on_mum:k0].min()
        s, yon = -1, 0
        for q in range(k0, min(k0 + 6, len(m) - 1)):
            if m.c[q] > Hs:
                s, yon = q, 1
                break
            if m.c[q] < Ls:
                s, yon = q, -1
                break
        if s < 0:
            continue
        stop = (Ls if yon == 1 else Hs) if stop_yeri == "karsi_uc" else (Hs + Ls) / 2.0
        r = _satir(c, s, yon, stop, Hs - Ls)
        r["ust"], r["alt"] = float(Hs), float(Ls)
        out.append(r)
    return _tablo(out), None


def n4(b: Baglam, tf: int, on_mum: int):
    """İlk mum aralığın dışında kapanır, ikinci mum içeride kapanırsa ters yönde."""
    out = []
    for _, c in cerceve(b, tf).iterrows():
        m = b.mumlar(tf, int(c["ofset"]))
        k0 = int(c["k0"])
        if k0 + 2 >= len(m):
            continue
        Hs, Ls = m.h[k0 - on_mum:k0].max(), m.l[k0 - on_mum:k0].min()
        c0, c1 = m.c[k0], m.c[k0 + 1]
        # "Yeniden içeride" iki kenarı da sorar: karşı kenarın ötesinde kapanan ikinci mum
        # başarısız bir kırılım değil, öbür yöne yeni bir kırılımdır.
        icerde = Ls <= c1 <= Hs
        if c0 > Hs and icerde:
            yon, stop, karsi = -1, max(m.h[k0], m.h[k0 + 1]), Ls
        elif c0 < Ls and icerde:
            yon, stop, karsi = 1, min(m.l[k0], m.l[k0 + 1]), Hs
        else:
            continue
        r = _satir(c, k0 + 1, yon, stop, Hs - Ls, seviye=float(karsi))
        r["ust"], r["alt"] = float(Hs), float(Ls)
        out.append(r)
    return _tablo(out, ["seviye"]), None


def n5(b: Baglam, tf: int, geri_cekilme: float):
    """İtkiden sonra oran kadar geri çekilme, ardından itki yönünde kapanan mumda devam."""
    out = []
    for _, c in cerceve(b, tf).iterrows():
        if abs(c["hareket_atr"]) < 0.5:
            continue
        m = b.mumlar(tf, int(c["ofset"]))
        k0 = int(c["k0"])
        itki = 1 if c["hareket"] > 0 else -1
        uc = m.h[k0] if itki == 1 else m.l[k0]
        boy = abs(uc - m.o[k0])
        seviye = uc - itki * geri_cekilme * boy
        dokundu, s = False, -1
        for q in range(k0 + 1, min(k0 + 7, len(m) - 1)):
            if not dokundu and ((m.l[q] <= seviye) if itki == 1 else (m.h[q] >= seviye)):
                dokundu = True
            if dokundu and (m.c[q] - m.o[q]) * itki > 0:
                s = q
                break
        if s < 0:
            continue
        stop = m.l[k0 + 1:s + 1].min() if itki == 1 else m.h[k0 + 1:s + 1].max()
        out.append(_satir(c, s, itki, stop, boy, seviye=float(uc)))
    return _tablo(out, ["seviye"]), None


HABER = {"n1": n1, "n2": n2, "n3": n3, "n4": n4, "n5": n5}


def kos_haber(b: Baglam, sin: pd.DataFrame, tf: int, stop_turu: str, hedef: str, kayma_pip: float,
              haber_kayma_pip: float, zaman_mum: int) -> pd.DataFrame:
    """Sinyalleri olay × ofset grubunda koşturur; tek pozisyon kuralı parite başına, bütün gruplara birlikte."""
    if len(sin) == 0:
        return pd.DataFrame()
    parcalar = []
    for (_, ofset), grup in sin.groupby(["olay", "ofset"], sort=True):
        isl = kos(b, grup.reset_index(drop=True), tf, int(ofset), stop_turu, hedef, kayma_pip, haber_kayma_pip,
                  zaman_mum, tek_pozisyon=False)
        if len(isl):
            parcalar.append(isl)
    if not parcalar:
        return pd.DataFrame()
    out = tek_pozisyon_uygula(pd.concat(parcalar, ignore_index=True))
    sira = np.where(out["giris_i"].to_numpy() >= 0, out["giris_t"].to_numpy(), out["sinyal_t"].to_numpy())
    out = out.iloc[np.argsort(sira, kind="stable")].reset_index(drop=True)
    out["kimlik"] = np.arange(len(out))
    return out


# ───────────────────────────────────────────── fiyat okuma
def mid_an(b: Baglam, t: np.ndarray, azami_bayat_sn: int = 300) -> np.ndarray:
    """Her an için o andan ÖNCE kapanmış son dakikanın mid kapanışı; son kotasyon
    `azami_bayat_sn`'den eskiyse NaN (veri boşluğunun üstünden fiyat okunmaz)."""
    t = np.asarray(t, dtype=np.int64)
    i = np.searchsorted(b.d.t, t, side="left") - 1
    ok = i >= 0
    ii = np.clip(i, 0, len(b.d.t) - 1)
    ok &= (t - (b.d.t[ii] + 60)) <= azami_bayat_sn
    out = np.full(len(t), np.nan)
    out[ok] = b.d.mc[ii[ok]]
    return out


def _dakika_ici(b: Baglam, t: np.ndarray) -> np.ndarray:
    """t anında AÇILAN dakikanın dizini (yoksa −1)."""
    i = np.searchsorted(b.d.t, t, side="left")
    ok = (i < len(b.d.t)) & (b.d.t[np.clip(i, 0, len(b.d.t) - 1)] == t)
    return np.where(ok, i, -1)


# ───────────────────────────────────────────── kırılım ↔ fade devam tablosu
def devam(b: Baglam, tf: int, ufuk_dk: int, kayma_pip: float, haber_kayma_pip: float) -> pd.DataFrame:
    """İlk haber mumu kapandıktan sonra, ilk hareketin yönünde ve tersinde `ufuk_dk` tutulan işlem.

    Stop yok, hedef yok; giriş ilk haber mumundan sonraki mumun ilk dakikasının
    açılışı (alış ask, satış bid, kayma dahil), çıkış ufkun açılışı (gün sonunu aşamaz).
    Kırılım ve fade aynı anlarda ters yönlü iki işlemdir; ikisi de kendi
    maliyetini öder, yani biri kazandığında öbürü maliyetin iki katı kadar kaybeder.
    Ufku gün sonuna (16:55 ET) yetişmeyen gözlem DÜŞER: kırpılmış bir tutuş o hücrenin
    ufkunu ölçmez (60 dakikalık mumda FOMC'nin 120 dakikası 16:55'i aşar). Düşenler
    olay olay `b.ek[("devam_kirpilan", tf, ufuk)]` sayacına yazılır.
    """
    cer = cerceve(b, tf)
    d, g = b.d, b.g
    satir = []
    kirpilan: dict[str, int] = {}
    for _, c in cer.iterrows():
        m = b.mumlar(tf, int(c["ofset"]))
        k0 = int(c["k0"])
        if k0 + 1 >= len(m) or c["hareket"] == 0:
            continue
        t_g = int(m.bt[k0]) + tf * 60
        gi = int(_dakika_ici(b, np.array([t_g]))[0])
        if gi < 0:
            continue
        gun_sonu = int(g.sinir[int(c["gun_k"])])
        t_c = t_g + ufuk_dk * 60
        ci = int(np.searchsorted(d.t, t_c, side="left"))
        if ci > gun_sonu:
            kirpilan[c["olay"]] = kirpilan.get(c["olay"], 0) + 1
            continue
        if ci <= gi or ci >= len(d.t) or (d.t[ci] - t_c) > 300:
            continue
        yon = 1 if c["hareket"] > 0 else -1
        s_g = (kayma_pip + (haber_kayma_pip if b.haber[gi] else 0.0)) * d.pip
        s_c = (kayma_pip + (haber_kayma_pip if b.haber[ci] else 0.0)) * d.pip
        # kırılım (ilk hareket yönünde) ve fade (tersi), yürütülebilir fiyatlarla
        if yon == 1:
            kir = (d.bo[ci] - s_c) - (d.ao[gi] + s_g)
            fad = (d.bo[gi] - s_g) - (d.ao[ci] + s_c)
        else:
            kir = (d.bo[gi] - s_g) - (d.ao[ci] + s_c)
            fad = (d.bo[ci] - s_c) - (d.ao[gi] + s_g)
        brut = (d.mo[ci] - d.mo[gi]) * yon
        satir.append({"olay": c["olay"], "tarih": c["tarih"], "gun": str(g.gun[int(c["gun_k"])]),
                      "kova": c["kova"], "trend_uyum": c["trend_uyum"], "hareket_atr": float(c["hareket_atr"]),
                      "gun_atr_pip": float(g.atr[int(c["gun_k"])]) / d.pip,
                      "brut_pip": brut / d.pip, "kirilim_pip": kir / d.pip, "fade_pip": fad / d.pip})
    b.ek[("devam_kirpilan", tf, ufuk_dk)] = kirpilan
    return pd.DataFrame(satir)


# ───────────────────────────────────────────── FOMC
def fomc(b: Baglam, olaylar: pd.DataFrame) -> pd.DataFrame:
    """Basın toplantılı toplantılar: karar (14:00→14:30) ve basın (14:30→15:30, →16:00) hareketleri."""
    k = olaylar[olaylar["olay"] == "FOMC_karar"]
    bs = olaylar[olaylar["olay"] == "FOMC_basin"]
    ortak = sorted(set(k["tarih"]) & set(bs["tarih"]))
    satir = []
    for t in ortak:
        t_k = int(k.loc[k["tarih"] == t, "utc_sn"].iloc[0])
        t_b = int(bs.loc[bs["tarih"] == t, "utc_sn"].iloc[0])
        p = mid_an(b, np.array([t_k, t_b, t_b + 3600, t_b + 5400]))
        gun_k = int(gun_sirasi(b, t_k)[0])
        atr = b.g.atr[gun_k] if gun_k >= 0 else np.nan
        if gun_k < 0 or not np.isfinite(p).all() or not np.isfinite(atr) or atr <= 0:
            continue
        satir.append({"tarih": t, "gun_k": gun_k, "karar": p[1] - p[0], "basin_60": p[2] - p[1],
                      "basin_90": p[3] - p[1], "atr": atr})
    df = pd.DataFrame(satir, columns=["tarih", "gun_k", "karar", "basin_60", "basin_90", "atr"])
    if len(df):
        for c in ("karar", "basin_60", "basin_90"):
            df[c + "_atr"] = df[c] / df["atr"]
            df[c + "_pip"] = df[c] / b.d.pip
    return df


def fomc_ozet(df: pd.DataFrame, tekrar: int = 2000, tohum: int = 7) -> dict:
    """Karar ↔ basın hareketi: işaret uyumu, korelasyon, karar büyüklüğüne göre dönüş olasılığı."""
    if len(df) < 8:
        return {"n": int(len(df))}
    rng = np.random.default_rng(tohum)
    k, p60, p90 = (df[c + "_atr"].to_numpy() for c in ("karar", "basin_60", "basin_90"))
    def oran_ga(x):
        x = np.asarray(x, dtype=float)
        if len(x) == 0:
            return {"n": 0}
        bs = rng.choice(x, size=(tekrar, len(x)), replace=True).mean(axis=1)
        return {"n": int(len(x)), "oran": float(x.mean()), "alt": float(np.percentile(bs, 2.5)),
                "ust": float(np.percentile(bs, 97.5))}
    sonuc = {"n": int(len(df))}
    for ad, p in (("basin_60", p60), ("basin_90", p90)):
        gecerli = (k != 0) & (p != 0)
        donus = (np.sign(p[gecerli]) != np.sign(k[gecerli])).astype(float)
        r = float(np.corrcoef(k, p)[0, 1]) if np.std(k) > 0 and np.std(p) > 0 else float("nan")
        idx = rng.integers(0, len(k), size=(tekrar, len(k)))
        rb = np.array([np.corrcoef(k[i], p[i])[0, 1] for i in idx])
        kovalar = {}
        for ad_k, (lo, hi) in {"<0,5": (0, 0.5), "0,5–1": (0.5, 1.0), ">1": (1.0, np.inf)}.items():
            mk_ = gecerli & (np.abs(k) >= lo) & (np.abs(k) < hi)
            kovalar[ad_k] = oran_ga((np.sign(p[mk_]) != np.sign(k[mk_])).astype(float))
        sonuc[ad] = {"donus": oran_ga(donus), "korelasyon": r,
                     "korelasyon_alt": float(np.nanpercentile(rb, 2.5)),
                     "korelasyon_ust": float(np.nanpercentile(rb, 97.5)),
                     "karar_buyukluk": kovalar,
                     "ort_mutlak_karar_atr": float(np.abs(k).mean()), "ort_mutlak_basin_atr": float(np.abs(p).mean())}
    return sonuc


# ───────────────────────────────────────────── patikalar
def patika(b: Baglam, olaylar: pd.DataFrame, olay: str, once_dk: int = 30, sonra_dk: int = 120) -> dict:
    """Günlük ATR'ye bölünmüş ortalama fiyat patikası; ilk 5 dakikanın yönüne göre iki küme. Patikaya girmeyen olay
    adıyla ve sebebiyle `dislanan` listesinde durur (tatil ya da ATR yok · pencerede fiyat yok · ilk beş dakikada yön
    yok)."""
    o = olaylar[olaylar["olay"] == olay]
    tau = np.arange(-once_dk, sonra_dk + 1)
    yukari, asagi, dislanan = [], [], []
    for _, r in o.iterrows():
        t0 = int(r["utc_sn"])
        gun_k = int(gun_sirasi(b, t0)[0])
        if gun_k < 0 or b.g.tatil[gun_k] or not np.isfinite(b.g.atr[gun_k]) or b.g.atr[gun_k] <= 0:
            dislanan.append({"tarih": str(r["tarih"]), "neden": "tatil_ya_da_atr_yok"})
            continue
        p = mid_an(b, t0 + tau * 60)
        p0 = mid_an(b, np.array([t0]))[0]
        p5 = mid_an(b, np.array([t0 + 300]))[0]
        if not (np.isfinite(p).all() and np.isfinite(p0) and np.isfinite(p5)):
            dislanan.append({"tarih": str(r["tarih"]), "neden": "pencerede_fiyat_yok"})
            continue
        if p5 == p0:
            dislanan.append({"tarih": str(r["tarih"]), "neden": "ilk_bes_dakikada_yon_yok"})
            continue
        yol = (p - p0) / b.g.atr[gun_k]
        (yukari if p5 > p0 else asagi).append(yol)

    def ozet(x):
        if not x:
            return None
        a = np.vstack(x)
        sd = a.std(axis=0, ddof=1) if len(a) > 1 else np.zeros(a.shape[1])
        se = sd / np.sqrt(len(a))
        return {"n": int(len(a)), "ort": a.mean(axis=0).round(4).tolist(),
                "medyan": np.median(a, axis=0).round(4).tolist(),
                "alt": (a.mean(axis=0) - 1.96 * se).round(4).tolist(),
                "ust": (a.mean(axis=0) + 1.96 * se).round(4).tolist()}
    return {"tau": tau.tolist(), "yukari": ozet(yukari), "asagi": ozet(asagi), "dislanan": dislanan}
