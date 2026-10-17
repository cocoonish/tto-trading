#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dukascopy arşivinin kalite denetimi — boşluk, tatil, makas, sıçrama, çapraz sınama.

Neyi ölçer, neyi ölçmez:
  1. KAPSAM — her FX işlem gününün (önceki gün 17:00 ET → bugün 17:00 ET, 1440
     dakika) kaç dakikasında kotasyon var; eksik dakikaların ARDIŞIK koşuları
     (boşluk) uzunluklarına göre; ızgaranın dışındaki kotasyon, ikiye ayrılarak:
     örneklemin sağ kenarındaki kısmi gün ve gerçek hafta sonu (New York saatiyle).
  2. TATİL — kapsamı %50'nin altında kalan işlem günleri (Noel, yılbaşı vb.) ve
     %50–90 arası kısmi günler. Ders bunları adıyla dışarıda bırakır; sessizce değil.
     Ayrıca İngiltere'nin ve ABD'nin (Fed) hafta içi yerel tatillerinde kapsam (tatil.py):
     kurallar o günlerde sıradan gün gibi işlem açar.
  3. MAKAS — sıfır ve negatif makas (ask ≤ bid) sayısı; saat saat medyan ve
     95. yüzdelik; 17:00 ET devir dakikalarının makas profili (gün sonu
     kapanış saatinin gerekçesi).
  4. SIÇRAMA — 1 dakikalık orta fiyat getirisinde günün sağlam oynaklığının
     (MAD) 12 katını aşan ve ertesi dakika %70'ten fazlası geri dönen hareket
     ("kötü kotasyon" adayı); ayrıca gövdenin dışına uzanan aşırı fitil. Aday
     sayılır ve listelenir — veri DEĞİŞTİRİLMEZ. Haberle çakışanlar ayrıca
     işaretlenir (haber takvimi kurulduktan sonra).
  5. ÇAPRAZ SINAMA — dakika arşivinden kurulan saatlik bid ve ask mumları,
     Dukascopy'nin KENDİ saatlik mum dosyalarıyla alan alan karşılaştırılır
     (saklanan Ocak ve Temmuz ayları; sınanan ve dosyası olmayan aylar adıyla
     yazılır). Çözücüde ya da dolgu dakikalarının atılmasında bir kusur olsaydı
     burada görünürdü. Saatlik dosyalar dizinin SHA-256 sabitlemesine karşı
     sınanır (ozler.py).

Rapor yalnız ayardaki paritelerin anahtarlarını taşır; her paritenin kaydı, haber makasını kurduğu takvimin özünü
(olaylar.csv ve varsa ek.csv) yazar — ölçüm (ders_olcum) onu güncel takvimin özüyle kıyaslar.

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
    # Izgaranın (pencerenin hafta içi FX günleri) dışındaki kotasyonlar: örneklemin sağ kenarındaki, ızgarada olmayan
    # kısmi günün dakikaları ile gerçek hafta sonu kotasyonu (New York saatiyle cuma 17:00 → pazar 17:00) ayrı sayılır.
    disari_m = ~np.isin(t, izgara.ravel())
    disari = int(disari_m.sum())
    son_an = int(bas_sn[-1] + 1440 * 60)
    sag_kenar = int((disari_m & (t >= son_an)).sum())
    ny = pd.to_datetime(t, unit="s", utc=True).tz_convert(z.NEWYORK)
    hg = ny.dayofweek.to_numpy()
    sa = (ny.hour * 60 + ny.minute).to_numpy()
    hafta_sonu = int(((hg == 5) | ((hg == 4) & (sa >= 17 * 60)) | ((hg == 6) & (sa < 17 * 60))).sum())
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
        "izgara_disi_dakika": disari,
        "sag_kenar_dakika": sag_kenar,
        "hafta_sonu_dakika": hafta_sonu,
    }


def yerel_tatil_kapsam(t: np.ndarray, gunler: pd.DatetimeIndex, bas_sn: np.ndarray) -> dict:
    """İngiltere'nin ve ABD'nin (Federal Reserve Bankalarının kapalı olduğu) hafta içi yerel tatillerinde kotasyonlu
    dakika payı (tatil.py). Kurallar yalnız 25 Aralık ve 1 Ocak'ı işlem günü saymaz (gunluk.TATIL_TAKVIM); o iki gün
    hariç her yerel tatilde sıradan gün gibi işlem açarlar, yani verinin o günlerde de tam olup olmadığı ayrıca sorulur.
    `tatil_ozu`: listenin kurulduğu ham dizinin özü (ölçüm güncel listeyle kıyaslar)."""
    import tatil
    from gunluk import TATIL_TAKVIM
    gun_iso = [g.date().isoformat() for g in gunler]
    sira = {g: i for i, g in enumerate(gun_iso)}
    out: dict = {"tatil_ozu": tatil.ozu()}
    for ad, liste in (("ingiltere", tatil.ingiltere()), ("abd", tatil.abd())):
        secim = [x["tarih"] for x in tatil.hafta_ici(liste, gunler[0].date(), gunler[-1].date(), set(TATIL_TAKVIM))
                 if x["tarih"] in sira]
        if not secim:
            out[ad] = {"gun": 0}
            continue
        ix = np.array([sira[g] for g in secim], dtype=np.int64)
        izgara = bas_sn[ix][:, None] + np.arange(1440, dtype=np.int64)[None, :] * 60
        pay = np.isin(izgara, t).mean(axis=1)
        out[ad] = {"gun": int(len(ix)), "kapsam_ort_yuzde": round(float(pay.mean()) * 100, 2),
                   "kapsam_min_yuzde": round(float(pay.min()) * 100, 1), "en_dusuk_gun": secim[int(np.argmin(pay))],
                   "dusuk_gun": [(g, round(float(v) * 100, 1)) for g, v in zip(secim, pay) if v < 0.9]}
    return out


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


HABER_DK = list(range(-5, 16))


def _yerel(t_sn: np.ndarray, bolge: str) -> tuple[np.ndarray, np.ndarray]:
    """UTC saniyelerin bir bölgedeki yerel günün dakikası ve haftanın günü (0 = pazartesi)."""
    ix = pd.to_datetime(np.asarray(t_sn, dtype=np.int64), unit="s", utc=True).tz_convert(bolge)
    return (ix.hour * 60 + ix.minute).to_numpy(np.int64), ix.dayofweek.to_numpy()


def haber_makasi(f: pd.DataFrame, pip: float, olaylar: pd.DataFrame) -> dict:
    """Haber dakikalarında makas: olay anına göre −5 … +15 dakika, her dakikanın medyan kapanış makası (pip).

    Kıyas: olayın KENDİ bölgesindeki aynı YEREL dakikada (08:30 ET'deki bir olay için 08:29 ET, yaz ve kış), bu
    paritenin takvimindeki olayların olmadığı hafta içi günlerin medyan makası. Gün içi makas profili yerel saate bağlı
    olduğu için kıyas aynı yerel saatten kurulur; aynı UTC dakikası yaz ve kış günlerinde iki ayrı yerel saate düşerdi.
    Kıyas günleri "olaysız" değildir: takvimde olmayan başka veriler (ör. 08:30 ET'deki öbür ABD verileri) o günlerde
    de çıkabilir. Oran = haber / kıyas. Dakikası arşivde olmayan gözlem atlanır (sayı yazılır). Ölçü makastır; kayma
    ve derinlik ölçülmez.

    İkinci kıyas (`kiyas_gun_pip`): aynı yerel dakika ve olayla AYNI HAFTA GÜNÜ (her olay kendi gününün kıyasını alır).
    Takvimde olmayan haftalık bir veri o günün o dakikasında her hafta çıkıyorsa (ABD haftalık işsizlik başvuruları,
    perşembe 08:30 New York) ilk kıyas onu öbür günlerle sulandırır, ikincisi taşır.

    Bir olay türünün birden çok yerel saati varsa (ECB basın toplantısı 14:30 → 21.07.2022'den bu yana 14:45; ECB
    kararı 13:45 → 14:15) aynı ölçü saat saat de yazılır (`saat`): iki saat iki ayrı piyasa dakikasına düşebilir."""
    if olaylar is None or len(olaylar) == 0:
        return {}
    # Çözünürlükten bağımsız saniye (pandas 3 dizini saniye ya da nanosaniye çözünürlükte kurabilir).
    t = pd.DatetimeIndex(f.index).as_unit("s").asi8
    sc = f["spr_c"].to_numpy() / pip
    gun = pd.DatetimeIndex(f.index).normalize().as_unit("s").asi8
    olay_gunu = set(pd.DatetimeIndex(pd.to_datetime(olaylar["utc_sn"].to_numpy(np.int64), unit="s", utc=True))
                    .normalize().as_unit("s").asi8)
    olaysiz = ~np.isin(gun, list(olay_gunu))
    kiyas_bolge: dict[str, tuple[pd.Series, pd.Series]] = {}

    def kiyas_seri(bolge: str) -> tuple[pd.Series, pd.Series]:
        """(yerel dakika → medyan) ve ((hafta günü, yerel dakika) → medyan), olaysız hafta içi günlerden."""
        if bolge not in kiyas_bolge:
            dk, hg = _yerel(t, bolge)
            m = olaysiz & (hg < 5)
            tum = pd.Series(sc[m], index=dk[m]).groupby(level=0).median()
            gunluk = pd.Series(sc[m], index=hg[m] * 10_000 + dk[m]).groupby(level=0).median()
            kiyas_bolge[bolge] = (tum, gunluk)
        return kiyas_bolge[bolge]

    def profil(g: pd.DataFrame, bolge: str) -> dict:
        ks, ks_gun = kiyas_seri(bolge)
        satir, kiyas, kiyas_gun, n_gozlem = [], [], [], []
        for k in HABER_DK:
            hedef = g["utc_sn"].to_numpy(np.int64) + 60 * k
            j = np.searchsorted(t, hedef)
            ok = (j < len(t)) & (t[np.clip(j, 0, len(t) - 1)] == hedef)
            deger = sc[j[ok]]
            satir.append(round(float(np.median(deger)), 3) if ok.any() else None)
            n_gozlem.append(int(ok.sum()))
            dk_yerel, hg_yerel = (_yerel(hedef[ok], bolge) if ok.any()
                                  else (np.empty(0, np.int64), np.empty(0, np.int64)))
            kv = ks.reindex(dk_yerel).dropna().to_numpy()
            kiyas.append(round(float(np.median(kv)), 3) if len(kv) else None)
            kg = ks_gun.reindex(hg_yerel * 10_000 + dk_yerel).dropna().to_numpy()
            kiyas_gun.append(round(float(np.median(kg)), 3) if len(kg) else None)
        oran = [round(h / c, 2) if h is not None and c else None for h, c in zip(satir, kiyas)]
        oran_gun = [round(h / c, 2) if h is not None and c else None for h, c in zip(satir, kiyas_gun)]
        z = max((i for i in range(len(oran)) if oran[i] is not None), key=lambda i: oran[i], default=None)
        return {"n_olay": int(len(g)), "bolge": bolge, "dk": HABER_DK, "medyan_pip": satir,
                "kiyas_pip": kiyas, "oran": oran, "kiyas_gun_pip": kiyas_gun, "oran_gun": oran_gun, "gozlem": n_gozlem,
                "zirve": ({"dk": HABER_DK[z], "pip": satir[z], "kiyas_pip": kiyas[z], "oran": oran[z],
                           "kiyas_gun_pip": kiyas_gun[z], "oran_gun": oran_gun[z]} if z is not None else None)}

    out = {}
    for olay, g in olaylar.groupby("olay"):
        bolgeler = sorted(set(g["bolge"]))
        if len(bolgeler) != 1:
            raise SystemExit(f"haber makası: {olay} olayının birden çok bölgesi var: {bolgeler}")
        out[str(olay)] = profil(g, bolgeler[0])
        if g["yerel_saat"].nunique() > 1:
            out[str(olay)]["saat"] = {}
            for s, gs in g.groupby("yerel_saat"):
                out[str(olay)]["saat"][str(s)] = {**profil(gs, bolgeler[0]), "ilk": str(gs["tarih"].min()),
                                                  "son": str(gs["tarih"].max())}
    return out


def damga_sinamasi(f: pd.DataFrame, pip: float, nfp_gunleri: set | None = None) -> dict:
    """Zaman damgası ve DST sınaması: veri saatinin hareketi DOĞRU dakikada mı?

    ABD tarım dışı istihdam (NFP) verisi 08:30 New York saatinde yayımlanır. Damgalar UTC'yse ve yaz saati doğru
    işleniyorsa, NFP günlerinde 1 dakikalık mum aralığının ortalaması yazın da kışın da tam 08:30 ET dakikasında
    zirve yapmalıdır (yazın 12:30, kışın 13:30 UTC). Bir saatlik kayma zirveyi ±60 dakikaya taşır; bu ölçüt onu
    görür. Günler takvimdeki NFP yayımlarının New York tarihleridir (`nfp_gunleri`): sınama yalnız GÜNÜ takvimden
    alır, dakikayı fiyattan ölçer, yani takvimin saatine dayanmaz. Takvim verilmezse ayın ilk cuması (çoğu ay NFP
    günü; bazı aylarda yayım ikinci cumaya kayar)."""
    ny = f.index.tz_convert(z.NEWYORK)
    if nfp_gunleri is not None:
        gun = np.asarray(ny.date)
        ilk_cuma = np.isin(gun, np.array(sorted(nfp_gunleri), dtype=object))
    else:
        ilk_cuma = (ny.dayofweek == 4) & (ny.day <= 7)
    ofs = (ny.hour * 60 + ny.minute).to_numpy() - (8 * 60 + 30)
    # Yaz saati: New York ofseti −4 saat (yerel saat − UTC saati = −4)
    fark_saat = ((ny.hour.to_numpy() - f.index.hour.to_numpy()) % 24)
    yaz_mi = fark_saat == 20          # −4 ≡ 20 (mod 24); kışta −5 ≡ 19
    aralik = (f["h"].to_numpy() - f["l"].to_numpy()) / pip
    sonuc = {}
    for ad, maske in (("yaz", yaz_mi), ("kis", ~yaz_mi)):
        m = ilk_cuma & maske & (np.abs(ofs) <= 15)
        if not m.any():
            sonuc[ad] = None
            continue
        s = pd.Series(aralik[m], index=ofs[m]).groupby(level=0).mean()
        sonuc[ad] = {"zirve_dk": int(s.idxmax()), "zirve_pip": round(float(s.max()), 2),
                     "komsu_medyan_pip": round(float(s.drop(s.idxmax()).median()), 2),
                     "gun": int(len(np.unique(ny[m].normalize())))}
    return sonuc


def nfp_gunleri(sembol: str) -> set:
    """Takvimdeki NFP yayımlarının New York tarihleri (damga sınamasının günleri)."""
    import takvim
    o = takvim.olaylar_oku(sembol)
    o = o[o["olay"] == "NFP"]
    return {x.date() for x in pd.to_datetime(o["utc_sn"].to_numpy(np.int64), unit="s", utc=True).tz_convert(z.NEWYORK)}


def capraz(f_ham: pd.DataFrame, sembol: str, nokta: float) -> dict:
    """Dakika arşivinden kurulan saatlik mumlar ↔ Dukascopy'nin kendi saatlik dosyaları, BID ve ASK ayrı ayrı.

    Kapsam saklanan dosyalardır: her yılın Ocak ve Temmuz ayları (arsiv_dukascopy.saatlik_indir); hangi ayların
    sınandığı ve hangilerinin dosyası olmadığı sonuçta adıyla durur. Dosyalar okunmadan önce dizinin SHA-256
    sabitlemesine karşı sınanır (ozler)."""
    dizin = ay.DUKA / "saatlik" / sembol
    if not dizin.exists():
        return {"durum": "saatlik dosya yok"}
    t = pd.to_datetime(f_ham["t"].to_numpy(np.int64), unit="s", utc=True)
    out: dict = {"taraf": {}}
    toplam_saat = toplam_esit = 0
    tum_saat = int(pd.DatetimeIndex(t).floor("h").nunique())
    for taraf, kok in (("BID", "b"), ("ASK", "a")):
        if kok == "b":
            fiyat = {x: f_ham[f"b_{x}"].to_numpy(np.int64) for x in "ohlc"}
            v = f_ham["b_v"].to_numpy(np.float64)
        else:
            fiyat = {x: f_ham[f"b_{x}"].to_numpy(np.int64) + f_ham[f"d_{x}"].to_numpy(np.int64) for x in "ohlc"}
            v = f_ham["a_v"].to_numpy(np.float64)
        b = pd.DataFrame({**fiyat, "v": v}, index=t)
        saat = b.resample("1h").agg({"o": "first", "h": "max", "l": "min", "c": "last", "v": "sum"}).dropna()
        toplam = esit = 0
        alan_esit = {"o": 0, "h": 0, "l": 0, "c": 0}
        hacim_fark = []
        ornek = []
        aylar = []
        ay_esit: dict[str, list[int]] = {}
        for yol in sorted(dizin.glob(f"*_{taraf}.bi5")):
            yil, ay_ = (int(x) for x in yol.stem.split("_")[0].split("-"))
            k = dk.coz(yol.read_bytes(), adim_sn=3600, azami=744)
            k = k[k["v"] > 0]
            t0 = pd.Timestamp(year=yil, month=ay_, day=1, tz="UTC")
            ix = t0 + pd.to_timedelta(k["s"].astype(np.int64), unit="s")
            ref = pd.DataFrame({"o": k["o"], "h": k["h"], "l": k["l"], "c": k["c"],
                                "v": k["v"].astype(np.float64)}, index=ix)
            ort = ref.join(saat, how="inner", lsuffix="_ref")
            for a_ in "ohlc":
                alan_esit[a_] += int((ort[f"{a_}_ref"].astype(np.int64) == ort[a_].astype(np.int64)).sum())
            tam = (ort[["o_ref", "h_ref", "l_ref", "c_ref"]].astype(np.int64).to_numpy()
                   == ort[["o", "h", "l", "c"]].astype(np.int64).to_numpy()).all(axis=1)
            toplam += len(ort)
            esit += int(tam.sum())
            aylar.append(f"{yil}-{ay_:02d}")
            ay_esit[f"{yil}-{ay_:02d}"] = [int(len(ort)), int(tam.sum())]
            hacim_fark.extend(((ort["v"] - ort["v_ref"]) / ort["v_ref"].where(ort["v_ref"] > 0)).dropna().tolist())
            for an in ort.index[~tam][:2]:
                if len(ornek) < 6:
                    r = ort.loc[an]
                    ornek.append({"utc": an.strftime("%Y-%m-%d %H:%M"),
                                  "ref": [int(r[f"{a_}_ref"]) for a_ in "ohlc"], "arsiv": [int(r[a_]) for a_ in "ohlc"]})
        hf = np.abs(np.array(hacim_fark)) if hacim_fark else np.array([np.nan])
        out["taraf"][taraf] = {
            "saat": toplam, "tam_esit": esit,
            "tam_esit_yuzde": round(100 * esit / toplam, 3) if toplam else None,
            "alan_esit_yuzde": {a_: round(100 * n / toplam, 3) if toplam else None for a_, n in alan_esit.items()},
            "hacim_goreli_fark_medyan": float(np.nanmedian(hf)),
            # Kapsam taraf başına: kotasyonlu saatlerin bu tarafta sınanan payı (iki tarafın saklanan ayları ayrışabilir).
            "kapsam_yuzde": round(100 * toplam / tum_saat, 2) if tum_saat else None,
            "aylar": aylar, "ay_esit": ay_esit, "uyusmayan_ornekler": ornek}
        toplam_saat += toplam
        toplam_esit += esit
    # Kapsam: sınanan aylar ve örneklemde olup dosyası olmayan Ocak/Temmuz ayları; kotasyonlu saatlerin payı.
    bas, bit = t.min(), t.max()
    beklenen = [f"{y}-{m:02d}" for y in range(bas.year, bit.year + 1) for m in (1, 7)
                if pd.Timestamp(year=y, month=m, day=28, tz="UTC") <= bit and pd.Timestamp(year=y, month=m, day=1,
                                                                                         tz="UTC") >= bas.normalize().replace(day=1)]
    sinanan = sorted(set(out["taraf"]["BID"]["aylar"]) & set(out["taraf"]["ASK"]["aylar"]))
    # İki tarafı birlikte sınanamayan beklenen aylardan birinin saatlik dosyası saklıysa o taraf sınanmıştır.
    tek = {m: [tr for tr in ("BID", "ASK") if m in out["taraf"][tr]["aylar"]] for m in beklenen if m not in sinanan}
    out.update({
        "saat": toplam_saat, "tam_esit": toplam_esit,
        "tam_esit_yuzde": round(100 * toplam_esit / toplam_saat, 3) if toplam_saat else None,
        "sinanan_aylar": sinanan, "eksik_aylar": [m for m in beklenen if m not in sinanan],
        "tek_taraf_aylar": {m: v[0] for m, v in tek.items() if len(v) == 1},
        "kotasyonlu_saat": tum_saat,
        "kapsam_yuzde": round(100 * out["taraf"]["BID"]["saat"] / tum_saat, 2) if tum_saat else None,
    })
    return out


def denetle(sembol: str, a: ay.Ayar) -> dict:
    ham = dk.oku_ham(ay.DUKA, sembol, gerekli=list(range(a.baslangic.year, a.bitis.year + 1)))
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
        "yerel_tatil": yerel_tatil_kapsam(t, gunler, bas_sn),
        "makas": makas(f, a.pip[sembol]),
        "sicrama": sicrama(f, a.pip[sembol]),
        "capraz": capraz(ham, sembol, a.nokta[sembol]),
        "damga": damga_sinamasi(f, a.pip[sembol], nfp_gunleri(sembol)),
        "hacim": {"sifir_hacimli_dakika": int(((ham["b_v"] == 0) & (ham["a_v"] == 0)).sum()),
                  "medyan": float(np.median(ham["b_v"] + ham["a_v"]))},
    }
    import takvim
    sonuc["haber_makasi"] = haber_makasi(f, a.pip[sembol], takvim.olaylar_oku(sembol))
    sonuc["takvim_ozu"] = takvim.ozler()
    return sonuc


def yazdir(sembol: str, s: dict) -> None:
    k, m, sc, cp = s["kapsam"], s["makas"], s["sicrama"], s["capraz"]
    print(f"\n━━ {sembol}  {s['ilk']} → {s['son']} UTC  ·  {s['satir']:,} dakika")
    print(f"  kapsam: {k['kapsam_yuzde']}% ({k['kotasyonlu_dakika']:,}/{k['beklenen_dakika']:,})  ·  "
          f"normal günlerde {k['normal_gun_kapsam_yuzde']}% ({k['normal_gun']} gün)")
    print(f"  boşluklar (normal günler): {k['bosluk_kovalari']}")
    print(f"  tatil (<%50): {len(k['tatil_gunleri'])} gün · kısmi (%50–90): {len(k['kismi_gunler'])} gün · "
          f"ızgara dışı kotasyon: {k['izgara_disi_dakika']:,} dk (sağ kenar {k['sag_kenar_dakika']:,} · "
          f"hafta sonu {k['hafta_sonu_dakika']:,})")
    print(f"  makas: medyan {m['medyan_pip']} pip · p95 {m['p95_pip']} · p99 {m['p99_pip']} · "
          f"sıfır (kapanış) {m['sifir_kapanis']:,} · negatif {m['negatif_kapanis']:,}")
    print(f"  devir profili (17:00 ET'ye göre dk → medyan pip): {m['devir_profili_medyan_pip']}")
    print(f"  sıçrama adayı: {sc['aday']} · aşırı fitil: {sc['asiri_fitil']} · en büyükler: {sc['en_buyuk'][:3]}")
    print(f"  zaman damgası (takvimdeki NFP günleri, 08:30 ET'ye göre zirve dakikası): {s['damga']}")
    if "tam_esit_yuzde" in cp:
        print(f"  çapraz sınama (saatlik, BID+ASK): {cp['tam_esit']}/{cp['saat']} saat birebir "
              f"({cp['tam_esit_yuzde']}%) · sınanan {len(cp['sinanan_aylar'])} ay · eksik {cp['eksik_aylar']}")
    else:
        print(f"  çapraz sınama: {cp}")


def tablo(rapor: dict) -> str:
    """Kalite raporunun pariteler yan yana özet tablosu (markdown)."""
    c = list(rapor)
    def satir(ad, f):
        return f"| {ad} | " + " | ".join(f(rapor[x]) for x in c) + " |"
    t = ["| | " + " | ".join(c) + " |", "|---|" + "---|" * len(c)]
    t.append(satir("kotasyonlu dakika", lambda s: f"{s['satir']:,}".replace(",", ".")))
    t.append(satir("kapsam, normal günler", lambda s: f"%{s['kapsam']['normal_gun_kapsam_yuzde']:.2f}".replace(".", ",")))
    t.append(satir("boşluk 5–14 / 15–59 / 60+ dk", lambda s: "{5-14} / {15-59} / {60+}".format(**s["kapsam"]["bosluk_kovalari"])))
    t.append(satir("tatil (<%50) / kısmi gün", lambda s: f"{len(s['kapsam']['tatil_gunleri'])} / {len(s['kapsam']['kismi_gunler'])}"))
    for ad, et in (("ingiltere", "İngiltere tatili: gün / kapsam"), ("abd", "ABD (Fed) tatili: gün / kapsam")):
        t.append(satir(et, lambda s, ad=ad: (f"{s['yerel_tatil'][ad]['gun']} / "
                                            f"%{s['yerel_tatil'][ad]['kapsam_ort_yuzde']:.2f}".replace(".", ",")
                                            if (s.get("yerel_tatil") or {}).get(ad, {}).get("gun") else "—")))
    t.append(satir("makas medyan / p95 (pip)", lambda s: f"{s['makas']['medyan_pip']:.2f} / {s['makas']['p95_pip']:.2f}".replace(".", ",")))
    t.append(satir("sıfır / negatif makas (dk)", lambda s: f"{s['makas']['sifir_kapanis']:,} / {s['makas']['negatif_kapanis']:,}".replace(",", ".")))
    t.append(satir("sıçrama adayı / aşırı fitil", lambda s: f"{s['sicrama']['aday']} / {s['sicrama']['asiri_fitil']}"))
    t.append(satir("saatlik çapraz sınama", lambda s: (f"%{s['capraz']['tam_esit_yuzde']:.2f}".replace(".", ",")
                                                         if s["capraz"].get("tam_esit_yuzde") is not None else "—")))
    t.append(satir("NFP zirvesi yaz / kış (dk)", lambda s: f"{(s['damga'].get('yaz') or {}).get('zirve_dk', '—')} / "
                                                           f"{(s['damga'].get('kis') or {}).get('zirve_dk', '—')}"))
    return "\n".join(t)


def main(argv: list[str]) -> int:
    import ozler
    a = ay.oku()
    hedef = argv or list(a.ciftler)
    if (ay.DUKA / "saatlik").exists():
        ozler.sina(ay.DUKA / "saatlik")
    rapor = {}
    yol = ay.DUKA / "kalite.json"
    if yol.exists():
        # Tek parite kipi öbür paritelerin kaydını korur; ayardan çıkarılan paritenin eski kaydı düşer.
        rapor = {c: v for c, v in json.loads(yol.read_text(encoding="utf-8")).items() if c in a.ciftler}
    for c in hedef:
        rapor[c] = denetle(c, a)
        yazdir(c, rapor[c])
    yol.write_text(json.dumps(rapor, ensure_ascii=False, indent=1, default=str) + "\n", encoding="utf-8")
    print("\n" + tablo(rapor))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
