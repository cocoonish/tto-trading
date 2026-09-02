# -*- coding: utf-8 -*-
"""DİBS verim eğrisi & reel faiz — metrik katmanı.

Ne hesaplar
-----------
1. **SPOT (ZERO) EĞRİ — bootstrap YOK.** TCMB her sabit kuponlu DİBS'in
   strip'lerini ayrı ayrı yayımlıyor; strip sıfır kuponlu olduğu için spot
   getiri doğrudan okunur:

       y = (ödeme / fiyat)^(365 / kalan gün) − 1        (ACT/365, yıllık bileşik)

   Ödeme: ANAPARA strip'inde 100, KUPON strip'inde o serinin kendi `.ORAN`
   değeri — DÖNEMSEL kupon TUTARI, yıllık oran DEĞİL (veri.py'deki birim
   notuna bakın; yıllık sanılırsa eğri ~15 puan kayar).
2. **Sabit vadeli düğümler** (3 ay … 9 yıl) — vade ekseninde doğrusal ara
   değer, EKSTRAPOLASYON YOK ve büyük boşlukların üstünden atlama YOK.
3. **Eğim, bükülme (kelebek), ileri (forward) oranlar, taşıma (carry).**
4. **Ana bileşenler (PCA)** — seviye / eğim / bükülme.
5. **PAR GETİRİ ve YTM ÇAPRAZ SINAMASI** — eğriden türetilen 2 yıllık par
   getiri ile piyasadaki kuponlu tahvillerin gerçek fiyatından hesaplanan
   bileşik YTM karşılaştırılır. Tahvilin nakit akışı UYDURULMAZ: aynı tahvile
   ait strip'lerin kendi itfa günleri ve ödemeleri kullanılır.
6. **TÜFEX REEL EĞRİ ve BAŞABAŞ ENFLASYON** — Hazine'nin referans endeksi
   yeniden kurularak.
7. **REEL FAİZ — FISHER** (bu depoda BAĞLAYICI karar; basit çıkarma DEĞİL):

       ileri  : r = (1 + i) / (1 + π^e) − 1      π^e = PKA 12 ay beklentisi
       geriye : r = (1 + i) / (1 + π)   − 1      π  = gerçekleşen yıllık TÜFE

   Basit çıkarma (i − π) YALNIZ "iki yöntem arasındaki fark" dersini
   göstermek için hesaplanır; ana ölçü değildir.
8. **KİMLİK DENETİMİ** — aynı itfa gününe düşen BAĞIMSIZ strip'ler aynı
   getiriyi vermeli. Sapma büyürse ödeme tanımı ya da etiket sınıflandırması
   bozulmuştur (ör. değişken faizli kıymet nominal eğriye sızmıştır).

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

import veri
from veri import PROJE, VERI, gun_ad, ay_ad


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı (ondalık virgül, eksi U+2212,
    yüzde önde). Hat kendi klasöründen elle koşturulursa ortak/ PYTHONPATH'te
    olmayabilir; depo kökünden bulunur."""
    try:
        import bicim
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim

# --------------------------------------------------------------------------- eşikler
# Kalan vadesi bu kadar günden kısa strip EĞRİYE ALINMAZ: fiyat üç haneye
# yuvarlanıyor ve 100/99,98 gibi bir orandan 365/5 kuvvetiyle yıllık getiri
# üretmek gürültüyü onlarca puana çeviriyor.
MIN_GUN = 15

# Getiri makul aralığı. Dışına çıkan nokta bir SINIFLANDIRMA hatasının
# işaretidir (değişken faizli sızması, ölçek dışı kıymet, bozuk ödeme).
GETIRI_ALT, GETIRI_UST = -0.20, 5.00        # −%20 … %500

# Bir günün eğri kurmaya yetmesi için gereken en az nokta sayısı.
GUN_MIN_NOKTA = 12

# --------------------------------------------------------------------- konvansiyon
# FONLAMA FAİZLERİ BASİT, EĞRİ BİLEŞİKTİR. TCMB/BİST gecelik ve haftalık
# oranları BASİT yıllık yayımlar (TLREF'in ayrıca bir "TLREF Endeksi" ile
# günlük bileşiklenmesi bunun kanıtıdır; TCMB haftalık repo ihalesinde de
# "basit" ve "bileşik" faiz ayrı ayrı ilan edilir). Strip getirisi ise
# y = (ödeme/fiyat)^(365/gün) − 1 ile YILLIK BİLEŞİKTİR.
#
# İkisini doğrudan çıkarmak taşımanın İŞARETİNİ ters çevirir: 21.08.2026'da
# TLREF %39,86 basit → bileşik %48,94; 2 yıllık spot %40,46. Basit farkla
# taşıma +0,61 puan (POZİTİF) görünür, konvansiyon uyumlu farkla −8,48 puan
# (NEGATİF). Bu yüzden fonlama faizleri önce eğrinin konvansiyonuna çevrilir.
GUN_SAYISI = 365.0          # ACT/365 — eğriyle aynı gün sayımı
POLITIKA_VADE_GUN = 7.0     # 1 hafta repo

# AOFM'nin yayımlanabilmesi için gereken en az APİ fonlaması (MİLYON TL).
# Fonlama hattındaki AOFM_TABAN_ESIK ile AYNI sayı olmalıdır.
AOFM_TABAN_ESIK_MN = 5_000.0

# Σ strip fiyatı = kuponlu tahvil fiyatı ÖZDEŞLİĞİNİN kabul eşiği (TL, 100
# nominal ölçeğinde). TCMB fiyatları üç haneye yuvarlanmış yayımlıyor;
# 0,0005 yuvarlama payıdır. Aşılırsa hat DURUR.
OZDESLIK_ESIK = 0.0005


def gecelik_bilesik(r: pd.Series) -> pd.Series:
    """BASİT yıllık gecelik oran → YILLIK BİLEŞİK (günlük çevrim)."""
    return ((1 + r / 100.0 / GUN_SAYISI) ** GUN_SAYISI - 1) * 100.0


def vadeli_bilesik(r: pd.Series, vade_gun: float) -> pd.Series:
    """BASİT yıllık `vade_gun` vadeli oran → YILLIK BİLEŞİK."""
    k = GUN_SAYISI / vade_gun
    return ((1 + r / 100.0 * vade_gun / GUN_SAYISI) ** k - 1) * 100.0

# Düğümler (yıl). 10 yıl BİLİNÇLİ YOK: aktif sıfır kuponlu evrenin en uzun
# noktası ~9 yıl; "10 yıllık" düğüm çoğu gün UYDURMA olurdu.
DUGUM = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 9.0]
DUGUM_AD = {0.25: "n3a", 0.5: "n6a", 1.0: "n1y", 2.0: "n2y", 3.0: "n3y",
            5.0: "n5y", 7.0: "n7y", 9.0: "n9y"}
# PCA panelinde 9 YIL BİLİNÇLİ YOK: uzun uç her dönem yayımda değil (3.558
# günün 2.969'unda var) ve PCA tam satır istediği için 9 yıl dahil edilince
# 2019–2021 arası SKOR SERİSİ PARÇALANIYORDU. Kalan yedi düğüm her gün dolu.
PCA_DUGUM = ["n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y"]
REEL_DUGUM = [1.0, 2.0, 3.0, 5.0, 7.0]
REEL_AD = {1.0: "r1y", 2.0: "r2y", 3.0: "r3y", 5.0: "r5y", 7.0: "r7y"}


def maks_bosluk(h: float) -> float:
    """Bir düğümü saran iki komşu nokta arasındaki EN BÜYÜK kabul edilebilir
    vade boşluğu (yıl). Boşluk bundan genişse ara değer 'veri' değil çizgidir;
    düğüm o gün NaN kalır. Uzun uçta gevşek, kısa uçta sıkı."""
    return max(0.5, 0.35 * h)


# Kimlik denetimi eşikleri (puan). Aynı itfa gününe düşen bağımsız strip'lerin
# getiri farkı. Keşifte ölçülen: medyan 0,0055 · maks 0,2561 puan.
SAPMA_MEDYAN_ESIK = 0.15     # görünür uyarı
SAPMA_MAKS_ESIK = 3.00       # hattı DURDURUR: sınıflandırma bozulmuş demektir

# Anket / TÜİK yayım gecikmesi. Aylık seriler EVDS'te ayın 1'i etiketiyle
# durur ama o gün YAYIMLANMAMIŞTIR; ileri doldurmayı ay başından yapmak
# GELECEĞE BAKAR (o tarihte piyasanın bilmediği bir beklentiyle reel faiz
# hesaplanır). PKA ayın ikinci yarısında, TÜFE ertesi ayın ilk günlerinde
# açıklanır — seriler bu kadar geciktirilerek günlüğe yayılır.
PKA_YAYIM_GUN = 20           # ayın 20'sinden itibaren geçerli
TUFE_YAYIM_GECIKME = 5       # ertesi ayın 5'inden itibaren geçerli

_UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


# ===========================================================================
# (0) YÜKLEME
# ===========================================================================
_ANAHTAR_RX = re.compile(r"^(\d+T\d+)(?:A|K\d+?)(\d{6})$")


def _strip_anahtari(etiket: str) -> str | None:
    """Strip etiketinden ANA TAHVİL kimliği.

    Etiket "<gövde><A|K n><ggaayy>" biçiminde ve sondaki ggaayy strip'in
    kendi itfası DEĞİL, ait olduğu TAHVİLİN itfasıdır:
        24T2A150328 → 24T2 vadesi 15.03.2028 olan tahvilin ANAPARA strip'i
        24T2K1150328 → aynı tahvilin 1. KUPONU (kendi itfası 16.09.2026)
    Bu eşleme olmadan tahvilin nakit akışı yeniden kurulamaz ve YTM çapraz
    sınaması yapılamaz.
    """
    m = _ANAHTAR_RX.match(etiket or "")
    return f"{m.group(1)}-{m.group(2)}" if m else None


def yukle() -> dict:
    F = pd.read_csv(VERI / "fiyat_nominal.csv.gz", index_col=0, parse_dates=True)
    K = pd.read_csv(VERI / "kunye_nominal.csv")
    G = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    A = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    T = pd.read_csv(VERI / "fiyat_tufex.csv.gz", index_col=0, parse_dates=True)
    KT = pd.read_csv(VERI / "kunye_tufex.csv")
    yol_b = VERI / "fiyat_tahvil.csv.gz"
    B = pd.read_csv(yol_b, index_col=0, parse_dates=True) if yol_b.exists() else pd.DataFrame()
    KB = pd.read_csv(VERI / "kunye_tahvil.csv")
    cpi = pd.read_csv(VERI / "tufe_zincir.csv", index_col=0, parse_dates=True).iloc[:, 0]
    vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    K["anahtar"] = K["etiket"].map(_strip_anahtari)
    KB["anahtar"] = KB["govde"].astype(str) + "-" + KB["isin"].str[3:9]
    return {"F": F, "K": K, "G": G, "A": A, "T": T, "KT": KT, "B": B, "KB": KB,
            "cpi": cpi, "vd": vd}


# ===========================================================================
# (1) SPOT EĞRİ PANELİ
# ===========================================================================
def _getiri_matrisi(F: pd.DataFrame, K: pd.DataFrame):
    """(tarih × kıymet) getiri ve vade matrisleri.

    HAFTA SONLARI BİLİNÇLİ DIŞARIDA: TCMB gösterge değeri takvim günü işliyor
    (Cumartesi/Pazar fiyatı Cuma'nın tekrarı DEĞİL, işlemiş değer — ölçüldü),
    ama TLREF/politika faizi iş günü serileridir. Eğriyi takvim gününde
    tutmak taşıma (carry) ölçülerini bir gün kaydırırdı; panel iş gününe
    hizalanır.
    """
    K = K[K["kod"].isin(F.columns)].copy()
    kodlar = K["kod"].tolist()
    P = F.loc[F.index.dayofweek < 5, kodlar]
    itfa = pd.to_datetime(K["itfa"]).values.astype("datetime64[D]").astype(np.int64)
    tarih = P.index.values.astype("datetime64[D]").astype(np.int64)
    GUN = itfa[None, :] - tarih[:, None]                     # kalan gün
    odeme = K["odeme"].to_numpy(dtype=float)
    Pv = P.to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        oran = np.where((Pv > 0.0) & (GUN >= MIN_GUN), odeme[None, :] / Pv, np.nan)
        Y = oran ** (365.0 / np.where(GUN >= MIN_GUN, GUN, np.nan)) - 1.0
    T = GUN / 365.0
    disarida = int(np.sum(np.isfinite(Y) & ((Y < GETIRI_ALT) | (Y > GETIRI_UST))))
    Y = np.where((Y >= GETIRI_ALT) & (Y <= GETIRI_UST), Y, np.nan)
    # Ham FİYAT da döner: strip toplamı özdeşliğinin birim sınaması getiriden
    # değil doğrudan fiyattan yapılır (getiriye çevirip geri dönmek
    # yuvarlamayı büyütürdü).
    return P.index, np.asarray(T), Y, K, disarida, Pv


def _ara_deger(t: np.ndarray, y: np.ndarray, hedefler) -> np.ndarray:
    """Vade ekseninde doğrusal ara değer.

    · EKSTRAPOLASYON YOK: hedef [t_min, t_max] dışındaysa NaN.
    · BOŞLUK GUARDI: hedefi saran iki nokta `maks_bosluk` kadar uzaksa NaN —
      aksi hâlde 2 yıl ile 7 yıl arasına çekilen düz çizgi "5 yıllık faiz"
      diye okunur.
    """
    out = np.full(len(hedefler), np.nan)
    if len(t) == 0:
        return out
    for j, h in enumerate(hedefler):
        if h < t[0] or h > t[-1]:
            continue
        i = int(np.searchsorted(t, h))
        if i < len(t) and t[i] == h:
            out[j] = y[i]
            continue
        t0, t1 = t[i - 1], t[i]
        if t1 - t0 > maks_bosluk(h):
            continue
        out[j] = y[i - 1] + (y[i] - y[i - 1]) * (h - t0) / (t1 - t0)
    return out


def _bilesik_ytm(vadeler: np.ndarray, tutarlar: np.ndarray, fiyat: float) -> float:
    """Yıllık BİLEŞİK iç verim (Türkiye piyasa konvansiyonu).

    DF(t) = (1+y)^−t, ACT/365. İkiye bölme (bisection) kullanılır: nakit
    akışları pozitif olduğu için fiyat y'de kesin azalandır, kök tektir.
    """
    if fiyat <= 0 or len(vadeler) == 0:
        return np.nan
    alt, ust = -0.90, 10.0

    def f(y):
        return float(np.sum(tutarlar * (1.0 + y) ** (-vadeler))) - fiyat

    fa, fu = f(alt), f(ust)
    if not np.isfinite(fa) or not np.isfinite(fu) or fa * fu > 0:
        return np.nan
    for _ in range(80):
        orta = 0.5 * (alt + ust)
        fo = f(orta)
        if fa * fo <= 0:
            ust, fu = orta, fo
        else:
            alt, fa = orta, fo
    return 0.5 * (alt + ust)


def _par_getiri(t: np.ndarray, y: np.ndarray, vade: float = 2.0,
                sıklık: int = 2) -> float:
    """Eğriden türetilen PAR getiri = 'gösterge tahvilin' sabit vadeli karşılığı.

    Kupon zamanları vadeden geriye altı ayda bir. Eğriden okunan iskonto
    çarpanlarıyla kuponu başabaş (100) fiyat verecek şekilde çöz, sonra o
    başabaş tahvilin BİLEŞİK YTM'sini hesapla — piyasanın "gösterge bileşik
    faiz" dediği büyüklük budur.
    """
    n = int(round(vade * sıklık))
    zaman = np.array([vade - k / sıklık for k in range(n)][::-1])
    s = _ara_deger(t, y, zaman)
    if not np.all(np.isfinite(s)):
        return np.nan
    df = (1.0 + s) ** (-zaman)
    if df.sum() <= 0:
        return np.nan
    kupon = 100.0 * (1.0 - df[-1]) / df.sum()
    tutar = np.full(n, kupon)
    tutar[-1] += 100.0
    return _bilesik_ytm(zaman, tutar, 100.0)


def egri_paneli(F: pd.DataFrame, K: pd.DataFrame):
    """Günlük spot eğri → düğüm paneli + tanı paneli + günlük ham kesitler."""
    tarih, T, Y, K, disarida, Pv = _getiri_matrisi(F, K)
    strip = K["strip"].to_numpy()
    n_gun, n_kod = Y.shape
    dugum_ad = [DUGUM_AD[d] for d in DUGUM]
    N = np.full((n_gun, len(DUGUM)), np.nan)
    par2 = np.full(n_gun, np.nan)
    tani = np.full((n_gun, 8), np.nan)     # nokta, tmin, tmax, kisa, orta, uzun, sapma_med, sapma_maks
    kesitler: dict[pd.Timestamp, pd.DataFrame] = {}
    for i in range(n_gun):
        m = np.isfinite(Y[i])
        n_nokta = int(m.sum())
        if n_nokta < GUN_MIN_NOKTA:
            tani[i, 0] = n_nokta
            continue
        ti, yi = T[i, m], Y[i, m]
        sira = np.argsort(ti)
        ti, yi = ti[sira], yi[sira]
        # AYNI İTFA GÜNÜNE düşen bağımsız strip'ler → kimlik denetimi.
        # Sonra tekilleştirme: aynı vadede birden çok gözlem varsa MEDYAN
        # alınır (ortalama tek bir bozuk noktadan etkilenir).
        tekil, ilk = np.unique(np.round(ti, 6), return_index=True)
        if len(tekil) < len(ti):
            sap = []
            baslangic = 0
            for j in range(1, len(ti) + 1):
                if j == len(ti) or round(ti[j], 6) != round(ti[baslangic], 6):
                    if j - baslangic > 1:
                        blok = yi[baslangic:j]
                        sap.append((blok.max() - blok.min()) * 100.0)
                    baslangic = j
            if sap:
                tani[i, 6] = float(np.median(sap))
                tani[i, 7] = float(np.max(sap))
            y_tekil = np.array([np.median(yi[np.isclose(ti, v)]) for v in tekil])
        else:
            y_tekil = yi
        N[i] = _ara_deger(tekil, y_tekil, DUGUM)
        par2[i] = _par_getiri(tekil, y_tekil, 2.0)
        tani[i, 0] = n_nokta
        tani[i, 1], tani[i, 2] = float(ti[0]), float(ti[-1])
        tani[i, 3] = int(np.sum(ti <= 1.0))          # kısa uç ≤1y
        tani[i, 4] = int(np.sum((ti > 1.0) & (ti <= 5.0)))
        tani[i, 5] = int(np.sum(ti > 5.0))
        kesitler[tarih[i]] = pd.DataFrame({
            "kod": K["kod"].to_numpy()[m][sira],
            "strip": strip[m][sira],
            "itfa": K["itfa"].to_numpy()[m][sira],
            "vade_yil": ti, "getiri": yi * 100.0,
            "fiyat": Pv[i][m][sira]})
    Ndf = pd.DataFrame(N, index=tarih, columns=dugum_ad)
    Ndf["par2y"] = par2
    Tdf = pd.DataFrame(tani, index=tarih, columns=[
        "nokta", "vade_min", "vade_maks", "nokta_kisa", "nokta_orta",
        "nokta_uzun", "sapma_medyan", "sapma_maks"])
    return Ndf * 100.0, Tdf, kesitler, disarida


# ===========================================================================
# (2) TÜFEX REEL EĞRİ — Hazine referans endeksinin yeniden kurulması
# ===========================================================================
def referans_endeks(gunler: pd.DatetimeIndex, cpi: pd.Series) -> pd.Series:
    """RefEndeks(t) = TÜFE(m−3) + (gün−1)/D × [TÜFE(m−2) − TÜFE(m−3)]

    Hazine'nin TÜFE'ye endeksli kıymetlerde kullandığı ÜÇ AY GECİKMELİ,
    ay içinde DOĞRUSAL ara değerli referans endeksi. EVDS'te bu seri YOK;
    burada yeniden kuruluyor. Taban 2003=100 zinciridir (veri.py, TÜİK 2025
    baz değişikliği zincirlenerek).
    """
    if cpi.empty:
        return pd.Series(np.nan, index=gunler)
    aylik = cpi.copy()
    aylik.index = pd.PeriodIndex(aylik.index, freq="M")
    p = pd.PeriodIndex(gunler, freq="M")
    a = pd.Series(aylik.reindex(p - 3).to_numpy(), index=gunler)
    b = pd.Series(aylik.reindex(p - 2).to_numpy(), index=gunler)
    gun_sayisi = gunler.days_in_month.to_numpy(dtype=float)
    pay = (gunler.day.to_numpy(dtype=float) - 1.0) / gun_sayisi
    return a + pay * (b - a)


def reel_paneli(T: pd.DataFrame, KT: pd.DataFrame, cpi: pd.Series,
                tarih: pd.DatetimeIndex):
    """TÜFEX anapara strip'lerinden reel spot eğri.

        reel getiri = (100 × RefEndeks(t)/RefEndeks(ihraç) / fiyat)^(365/gün) − 1

    TÜFEX'in yayımlanan "Değer"i ENDEKSLENMİŞ TL fiyatıdır; endeks oranına
    bölünmeden reel getiri çıkmaz (fiyat 100'ün çok üstünde görünür ve getiri
    negatife düşer).
    """
    KT = KT[KT["kod"].isin(T.columns)].copy()
    if KT.empty:
        return pd.DataFrame(index=tarih), {}, pd.DataFrame()
    P = T.reindex(tarih)[KT["kod"].tolist()]
    It = referans_endeks(P.index, cpi)
    I0 = np.array([referans_endeks(pd.DatetimeIndex([pd.Timestamp(x)]), cpi).iloc[0]
                   for x in KT["ihrac"]])
    itfa = pd.to_datetime(KT["itfa"]).values.astype("datetime64[D]").astype(np.int64)
    t_int = P.index.values.astype("datetime64[D]").astype(np.int64)
    GUN = itfa[None, :] - t_int[:, None]
    oran = It.to_numpy()[:, None] / I0[None, :]
    Pv = P.to_numpy(dtype=float)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        taban = np.where((Pv > 0) & (GUN >= 60), 100.0 * oran / Pv, np.nan)
        R = taban ** (365.0 / np.where(GUN >= 60, GUN, np.nan)) - 1.0
    # Reel getiride makul aralık nominalden dar: −%30 … +%60.
    R = np.where((R >= -0.30) & (R <= 0.60), R, np.nan)
    Ty = GUN / 365.0
    out = np.full((len(tarih), len(REEL_DUGUM)), np.nan)
    kesitler: dict[pd.Timestamp, pd.DataFrame] = {}
    for i in range(len(tarih)):
        m = np.isfinite(R[i])
        if m.sum() < 4:
            continue
        ti, yi = Ty[i, m], R[i, m]
        s = np.argsort(ti)
        ti, yi = ti[s], yi[s]
        tekil = np.unique(np.round(ti, 6))
        y_tekil = np.array([np.median(yi[np.isclose(ti, v)]) for v in tekil])
        out[i] = _ara_deger(tekil, y_tekil, REEL_DUGUM)
        kesitler[tarih[i]] = pd.DataFrame({
            "kod": KT["kod"].to_numpy()[m][s], "itfa": KT["itfa"].to_numpy()[m][s],
            "vade_yil": ti, "reel_getiri": yi * 100.0,
            "endeks_orani": oran[i][m][s]})
    Rdf = pd.DataFrame(out * 100.0, index=tarih,
                       columns=[REEL_AD[d] for d in REEL_DUGUM])
    return Rdf, kesitler, KT


# ===========================================================================
# (3) BEKLENTİ SERİLERİNİN GÜNLÜĞE YAYILMASI
# ===========================================================================
def gunluge_yay(aylik: pd.Series, tarih: pd.DatetimeIndex, yayim_gun: int,
                ay_gecikme: int = 0) -> pd.Series:
    """Aylık anket/enflasyon serisini günlük eksene BASAMAK olarak yayar.

    Ay etiketi yayım günü DEĞİLDİR. PKA ayın ikinci yarısında, TÜFE ertesi
    ayın başında açıklanır; ay başından ileri doldurmak GELECEĞE BAKAR ve
    reel faiz serisine yapay sıçrama koyar. Değer, yayım gününden itibaren
    geçerli sayılır.
    """
    s = aylik.dropna()
    if s.empty:
        return pd.Series(np.nan, index=tarih)
    idx = []
    for t in s.index:
        g = pd.Timestamp(t) + pd.DateOffset(months=ay_gecikme)
        idx.append(g.replace(day=min(yayim_gun, g.days_in_month)))
    yeni = pd.Series(s.to_numpy(), index=pd.DatetimeIndex(idx)).sort_index()
    yeni = yeni[~yeni.index.duplicated(keep="last")]
    return yeni.reindex(yeni.index.union(tarih)).ffill().reindex(tarih)


def yayim_gunleri(aylik: pd.Series, tarih: pd.DatetimeIndex, yayim_gun: int,
                  ay_gecikme: int = 0) -> list[pd.Timestamp]:
    s = aylik.dropna()
    out = []
    for t in s.index:
        g = pd.Timestamp(t) + pd.DateOffset(months=ay_gecikme)
        g = g.replace(day=min(yayim_gun, g.days_in_month))
        if tarih[0] <= g <= tarih[-1]:
            out.append(g)
    return out


# ===========================================================================
# (3b) ANKET BEKLENTİSİNİ VADEYE KADARKİ ORTALAMAYA ÇEVİRME
# ===========================================================================
def anket_ortalama(cipalar: dict[float, pd.Series],
                   vadeler: list[float]) -> dict[float, pd.Series]:
    """PKA NOKTA beklentilerinden vadeye kadarki ORTALAMA enflasyonu kurar.

    Girdi `{yıl: seri}` — o YILIN tek yıllık enflasyon beklentisi
    (1: π12, 2: π24, 5: π5y). Çıktı `{vade: seri}` — vadeye kadarki
    GEOMETRİK ORTALAMA yıllık enflasyon:

        π̄(T) = [ Π_{k=1..T} (1 + π_k) ]^(1/T) − 1

    ARA YILLAR (3, 4): iki çıpa arasında log(1+π) ekseninde DOĞRUSAL ara
    değer. Anket bu yılları sormaz; patika bir VARSAYIMDIR ve sayfada
    metodoloji notu olarak yazılır.

    SON ÇIPADAN SONRASI (6, 7): SABİT tutulur — son çıpanın oranı devam eder.
    Trend ekstrapolasyonu yapılmaz; eğrinin kendisinde de ekstrapolasyon yasak.

    Neden gerekli: başabaş enflasyon vadeye kadarki ORTALAMA'dır, PKA serisi
    ise "X ay SONRASININ yıllık" oranıdır. İkisini doğrudan çıkarmak risk
    primini sistematik biçimde şişirir.
    """
    if not cipalar:
        return {}
    cipa_yil = sorted(cipalar)
    ind = cipalar[cipa_yil[0]].index
    maks_yil = int(max(max(vadeler), max(cipa_yil)))
    # log(1+π) ekseninde yıl yıl patika
    L = pd.DataFrame(index=ind, columns=range(1, maks_yil + 1), dtype=float)
    for y in cipa_yil:
        L[int(y)] = np.log1p(cipalar[y] / 100.0)
    for k in range(1, maks_yil + 1):
        if k in [int(y) for y in cipa_yil]:
            continue
        alt = [int(y) for y in cipa_yil if y < k]
        ust = [int(y) for y in cipa_yil if y > k]
        if alt and ust:
            a, b = max(alt), min(ust)
            w = (k - a) / (b - a)
            L[k] = L[a] * (1 - w) + L[b] * w
        elif alt:                       # son çıpadan sonrası: SABİT
            L[k] = L[max(alt)]
        else:                           # ilk çıpadan öncesi: SABİT
            L[k] = L[min(ust)]
    out: dict[float, pd.Series] = {}
    for v in vadeler:
        n = int(round(v))
        if n < 1:
            continue
        out[v] = (np.expm1(L[list(range(1, n + 1))].mean(axis=1)) * 100.0)
    return out


# ===========================================================================
# (4) ANA BİLEŞENLER
# ===========================================================================
def ana_bilesenler(N: pd.DataFrame):
    """Seviye / eğim / bükülme — düğüm panelinin ana bileşenleri.

    Ölçek NORMALLEŞTİRİLMEZ (bütün düğümler zaten puan cinsinden); ortalama
    çıkarılır. İşaret keyfîdir, sabitlenir: PC1 yüklemelerinin toplamı
    pozitif (seviye YUKARI), PC2 uzun uçta pozitif (eğri DİKLEŞİYOR),
    PC3 ortada pozitif (BÜKÜLME artıyor). İşaret sabitlenmezse koşumdan
    koşuma grafik ters dönerdi.
    """
    X = N[PCA_DUGUM].dropna()
    if len(X) < 60:
        return pd.DataFrame(), {}
    ort = X.mean()
    Z = (X - ort).to_numpy()
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    pay = (S ** 2) / float(np.sum(S ** 2))
    isaret = np.ones(3)
    if Vt[0].sum() < 0:
        isaret[0] = -1
    if Vt[1][-1] - Vt[1][0] < 0:
        isaret[1] = -1
    if Vt[2][len(PCA_DUGUM) // 2] < 0:
        isaret[2] = -1
    skor = pd.DataFrame(
        {f"pc{i + 1}": U[:, i] * S[i] * isaret[i] for i in range(3)}, index=X.index)
    tani = {
        "aciklanan_pay": [round(float(p), 4) for p in pay[:3]],
        "toplam_pay_3": round(float(pay[:3].sum()), 4),
        "n_gun": int(len(X)),
        "dugum": PCA_DUGUM,
        "yukleme": {f"pc{i + 1}": [round(float(v * isaret[i]), 4) for v in Vt[i]]
                    for i in range(3)},
        "ortalama": {k: round(float(v), 3) for k, v in ort.items()},
    }
    return skor, tani


# ===========================================================================
# (5) YTM ÇAPRAZ SINAMASI — eğri, gerçek tahvil fiyatını açıklıyor mu?
# ===========================================================================
def ytm_sinamasi(B: pd.DataFrame, KB: pd.DataFrame, K: pd.DataFrame,
                 kesit: pd.DataFrame, gun: pd.Timestamp) -> dict:
    """Çıpa gününde her aktif kuponlu tahvil için İÇ TUTARLILIK denetimi.

    BU BAĞIMSIZ BİR DOĞRULAMA DEĞİLDİR — ÖZDEŞLİKTİR. Şöyle:

      · nakit akışı = tahvilin KENDİ strip'lerinin (itfa, ödeme) çiftleri,
      · iskonto oranı = eğrinin o vadedeki değeri, yani TAM O STRİP'İN
        kendi getirisi: s_i = (CF_i / P_i)^(365/gün) − 1,
      · dolayısıyla CF_i · (1 + s_i)^(−t_i) = P_i ve
        model_fiyat = Σ P_i.

    TCMB'nin yayımladığı kuponlu tahvil "Değer"i de tam olarak strip
    fiyatlarının toplamıdır (50 tahvilin 50'sinde |fark| < 5e-13 ölçüldü).
    Kalan mikroskobik sapma yalnız AYNI VADEDE birden çok strip bulunduğunda
    alınan MEDYANDAN gelir.

    O hâlde bu ne işe yarar? Bir BİRİM SINAMASIDIR: özdeşlik bozulursa
    (ödeme tanımı, etiket sınıflandırması, strip↔tahvil eşlemesi ya da
    fiyat ölçeği bozulmuşsa) buradan görünür. Sayfada "bağımsız çapraz
    sınama" DİYE SUNULMAZ; gerçek bağımsız sınama Hazine ihale sonuçları ya
    da BİST kesin alım-satım kapanışıyla yapılırdı, bu hatta ikisi de yok.
    """
    if B.empty or gun not in B.index or kesit.empty:
        return {}
    t = kesit["vade_yil"].to_numpy()
    y = kesit["getiri"].to_numpy() / 100.0
    sira = np.argsort(t)
    t, y = t[sira], y[sira]
    tekil = np.unique(np.round(t, 6))
    y_tekil = np.array([np.median(y[np.isclose(t, v)]) for v in tekil])
    fiyatlar = B.loc[gun]
    fiyatlar_strip = kesit.set_index("kod")["fiyat"] if "fiyat" in kesit.columns \
        else pd.Series(dtype=float)
    K_ind = K.dropna(subset=["anahtar"]).groupby("anahtar")
    satir = []
    for _, b in KB.iterrows():
        p = fiyatlar.get(b["kod"])
        if p is None or not np.isfinite(p) or p <= 0:
            continue
        if b["anahtar"] not in K_ind.groups:
            continue
        akis = K_ind.get_group(b["anahtar"])
        akis = akis[pd.to_datetime(akis["itfa"]) > gun]
        if akis.empty:
            continue
        vade = ((pd.to_datetime(akis["itfa"]) - gun).dt.days / 365.0).to_numpy()
        tutar = akis["odeme"].to_numpy(dtype=float)
        piyasa = _bilesik_ytm(vade, tutar, float(p))
        s = _ara_deger(tekil, y_tekil, vade)
        if not np.all(np.isfinite(s)):
            continue
        model_fiyat = float(np.sum(tutar * (1.0 + s) ** (-vade)))
        model = _bilesik_ytm(vade, tutar, model_fiyat)
        # ÖZDEŞLİK AYAĞI: tahvilin gözlenen fiyatı, kendi strip fiyatlarının
        # toplamı MI? (Eğriden geçmeden, doğrudan fiyat toplamı.)
        # Bacaklardan biri kesitte yoksa (vadesi MIN_GUN'ün altına inmiş ya da
        # getirisi makul aralığın dışında kalmış) toplam EKSİK olur; o tahvil
        # özdeşlik denetimine ALINMAZ, "eksik bacak" diye işaretlenir.
        bacak = [fiyatlar_strip.get(kk, np.nan) for kk in akis["kod"]]
        ozdes_tam = bool(np.all(np.isfinite(np.asarray(bacak, dtype=float))))
        strip_fiyat = float(np.sum(bacak)) if ozdes_tam else np.nan
        satir.append({
            "kod": b["kod"], "itfa": b["itfa"],
            "vade_yil": round(float(vade.max()), 4),
            "nakit_akisi_n": int(len(vade)),
            "piyasa_fiyat": round(float(p), 4),
            "model_fiyat": round(model_fiyat, 4),
            "strip_toplam": round(strip_fiyat, 6) if ozdes_tam else None,
            "ozdeslik_fark": (round(abs(strip_fiyat - float(p)), 8)
                              if ozdes_tam else None),
            "piyasa_ytm": round(piyasa * 100.0, 4),
            "model_ytm": round(model * 100.0, 4),
            "fark_puan": round((piyasa - model) * 100.0, 4)})
    if not satir:
        return {}
    d = pd.DataFrame(satir)
    # BİRİM SINAMASI: Σ strip fiyatı = tahvil fiyatı. Bu bir DOĞRULAMA değil,
    # veri düzeninin özdeşliğidir; bozulursa ödeme/etiket/eşleme bozulmuştur.
    oz = d["ozdeslik_fark"].dropna()
    ozdes_maks = float(oz.max()) if len(oz) else float("nan")
    ozdes_gecti = bool(len(oz) and ozdes_maks < OZDESLIK_ESIK)
    if len(oz) and not ozdes_gecti:
        raise SystemExit(
            f"DUR: strip toplamı özdeşliği bozuldu — en büyük |Σ strip − "
            f"tahvil fiyatı| {ozdes_maks:.6f} TL (eşik {OZDESLIK_ESIK}). "
            "Ödeme tanımı, etiket sınıflandırması ya da strip↔tahvil "
            "eşlemesi bozulmuş olabilir; siteye kopyalama YAPILMAZ.")
    if not len(oz):
        uyar("ÖZDEŞLİK SINANAMADI: hiçbir tahvilin bütün strip bacakları "
             "günlük kesitte bulunamadı.")
    return {
        "n": int(len(d)),
        "gun": str(gun.date()),
        "medyan_fark_puan": round(float(d["fark_puan"].abs().median()), 4),
        "maks_fark_puan": round(float(d["fark_puan"].abs().max()), 4),
        "medyan_fiyat_fark": round(float((d["model_fiyat"] - d["piyasa_fiyat"]).abs().median()), 4),
        # DÜRÜST ETİKET: bu bir özdeşliktir, bağımsız sınama değildir.
        "ozdeslik": True,
        "ozdeslik_n": int(len(oz)),
        "ozdeslik_maks_tl": (round(ozdes_maks, 8) if len(oz) else None),
        "ozdeslik_esik_tl": OZDESLIK_ESIK,
        "ozdeslik_gecti": ozdes_gecti,
        "tablo": d.to_dict("records"),
    }


# ===========================================================================
# (6) ANA AKIŞ
# ===========================================================================
def kos() -> int:
    d = yukle()
    F, K, G, A = d["F"], d["K"], d["G"], d["A"]
    print("DİBS verim eğrisi & reel faiz — metrikler")

    # --- spot eğri ---------------------------------------------------------
    N, TANI, kesitler, disarida = egri_paneli(F, K)
    if disarida:
        print(f"  · {disarida} gözlem makul getiri aralığının "
              f"[%{GETIRI_ALT * 100:.0f}, %{GETIRI_UST * 100:.0f}] dışında kaldı "
              "ve eğriye alınmadı.")
    tarih = N.index
    s_gun = veri.son_gun(F)
    if s_gun.dayofweek >= 5:
        # Çıpa İŞ GÜNÜDÜR: hafta sonu gösterge değeri işlemiş değerdir ama
        # referans faizler o gün yayımlanmaz; taşıma ölçüleri boş çıkardı.
        s_gun = tarih[tarih <= s_gun][-1]
    if s_gun not in N.index or not np.isfinite(N.loc[s_gun, "n2y"]):
        raise SystemExit(
            f"DUR: çıpa gününde ({s_gun:%d.%m.%Y}) 2 yıllık düğüm kurulamadı — "
            "eğri o gün yeterince dolu değil. Siteye kopyalama YAPILMAZ.")
    print(f"  çıpa günü: {gun_ad(s_gun)} · "
          f"{int(TANI.loc[s_gun, 'nokta'])} sıfır kuponlu nokta · vade "
          f"{TANI.loc[s_gun, 'vade_min']:.2f}–{TANI.loc[s_gun, 'vade_maks']:.2f} yıl")

    M = N.join(TANI)

    # --- eğim / bükülme ----------------------------------------------------
    # 10 yıl ucu YOK: en uzun nokta ~9 yıl. "2y−10y" yerine 2y−9y kullanılır
    # ve bu VEKİL olduğu sayfada açıkça yazılır.
    M["egim_2y9y"] = M["n9y"] - M["n2y"]
    M["egim_2y5y"] = M["n5y"] - M["n2y"]
    M["egim_2y3a"] = M["n2y"] - M["n3a"]   # uzun − kısa (diğer eğimlerle aynı yön)
    M["kelebek_1_2_5"] = 2 * M["n2y"] - M["n1y"] - M["n5y"]
    M["kelebek_2_5_9"] = 2 * M["n5y"] - M["n2y"] - M["n9y"]

    # --- ileri (forward) oranlar ------------------------------------------
    # f(t1→t2) = [ (1+s2)^t2 / (1+s1)^t1 ]^(1/(t2−t1)) − 1
    def ileri(a_ad, a_t, b_ad, b_t):
        s1 = M[a_ad] / 100.0
        s2 = M[b_ad] / 100.0
        return (((1 + s2) ** b_t / (1 + s1) ** a_t) ** (1.0 / (b_t - a_t)) - 1) * 100.0

    M["f_1y1y"] = ileri("n1y", 1.0, "n2y", 2.0)
    M["f_2y1y"] = ileri("n2y", 2.0, "n3y", 3.0)
    M["f_2y3y"] = ileri("n2y", 2.0, "n5y", 5.0)
    M["f_5y4y"] = ileri("n5y", 5.0, "n9y", 9.0)

    # --- referans faizler ve taşıma ---------------------------------------
    for kol in ("tlref", "politika", "aofm", "koridor_alt", "koridor_ust",
                "bist_on", "politika_ger", "fon_top"):
        if kol in G.columns:
            M[kol] = G[kol].reindex(tarih)

    # AOFM GEÇERLİLİK KAPISI (Fonlama hattıyla AYNI eşik, tek yerde tanımlı
    # olamıyor çünkü iki hat ayrı depolarda koşuyor — eşik ikisinde de 5
    # milyar TL ve ozet.json'a basılıyor ki karşılaştırılabilsin).
    # AOFM bir AĞIRLIKLI ORTALAMADIR; APİ fonlaması sıfıra inince ağırlık
    # kalmaz ve yayımlanan sayı son değerinde DONAR (12.08–21.08.2026 boyunca
    # 40,00 sabit). Böyle bir günün AOFM'sini "fiilî fonlama maliyeti" diye
    # manşete koymak yanlıştır: sistemin marjinal fiyatını o gün
    # sterilizasyon belirler.
    M["aofm_ham"] = M["aofm"]
    if "fon_top" in M.columns:
        M["aofm_gecerli"] = (M["fon_top"].notna()
                             & (M["fon_top"] >= AOFM_TABAN_ESIK_MN)
                             & M["aofm"].notna())
    else:
        uyar("AOFM TABANI YOK: TP.APIFON1.TOP çekilemedi — AOFM geçerlilik "
             "kapısı uygulanamıyor, ham seri kullanılıyor.")
        M["aofm_gecerli"] = M["aofm"].notna()
    M["aofm"] = M["aofm_ham"].where(M["aofm_gecerli"])

    # 2018 öncesinde 1 hafta repo SATIŞ kotasyonu yok; gerçekleşen haftalık
    # repo faizi VEKİL alınır (bu vekil sayfada açıkça yazılır).
    # AD NOTU: bu kolon iki seriyi BİRLEŞTİRİR, bileşikleştirmez — eski adı
    # (`politika_bilesik`) tam da bu yüzden yanıltıcıydı.
    M["politika_birlesik"] = M["politika"].fillna(M["politika_ger"])

    # Konvansiyon dönüşümü: BASİT → BİLEŞİK. Taşıma YALNIZ bunlardan hesaplanır.
    M["tlref_bilesik"] = gecelik_bilesik(M["tlref"])
    M["aofm_bilesik"] = gecelik_bilesik(M["aofm"])
    M["politika_bilesik_gercek"] = vadeli_bilesik(M["politika_birlesik"],
                                                  POLITIKA_VADE_GUN)
    M["carry_2y_tlref"] = M["n2y"] - M["tlref_bilesik"]
    M["carry_2y_politika"] = M["n2y"] - M["politika_bilesik_gercek"]
    M["carry_2y_aofm"] = M["n2y"] - M["aofm_bilesik"]
    M["carry_3a_tlref"] = M["n3a"] - M["tlref_bilesik"]
    # Basit farkı da tut: sayfada "konvansiyon farkı ne kadar" dersi buradan
    # okunur ve ham (basit) sayı gizlenmez.
    M["carry_2y_tlref_basit"] = M["n2y"] - M["tlref"]
    M["carry_2y_aofm_basit"] = M["n2y"] - M["aofm"]
    M["konvansiyon_farki_tlref"] = M["tlref_bilesik"] - M["tlref"]

    # --- beklenti ve enflasyon (günlüğe yayılmış) --------------------------
    pka12 = gunluge_yay(A["pka_12a"], tarih, PKA_YAYIM_GUN)
    pka24 = gunluge_yay(A["pka_24a"], tarih, PKA_YAYIM_GUN)
    pka5y = gunluge_yay(A["pka_5y"], tarih, PKA_YAYIM_GUN) if "pka_5y" in A else pd.Series(np.nan, index=tarih)
    pka_faiz12 = gunluge_yay(A["pka_faiz_12a"], tarih, PKA_YAYIM_GUN)
    pka_faiz24 = gunluge_yay(A["pka_faiz_24a"], tarih, PKA_YAYIM_GUN)
    tufe_yillik_ay = A["tufe_2025"].pct_change(12, fill_method=None) * 100.0
    tufe_yillik = gunluge_yay(tufe_yillik_ay, tarih, TUFE_YAYIM_GECIKME, ay_gecikme=1)
    M["pka_12a"], M["pka_24a"], M["pka_5y"] = pka12, pka24, pka5y
    M["pka_faiz_12a"], M["pka_faiz_24a"] = pka_faiz12, pka_faiz24
    M["tufe_yillik"] = tufe_yillik
    M["pka_12a_n"] = gunluge_yay(A["pka_12a_n"], tarih, PKA_YAYIM_GUN)

    # --- ANKET BEKLENTİSİNİN VADE YAPISI -----------------------------------
    # PKA serileri NOKTA oranlardır, ORTALAMA değildir (EVDS meta verisinden
    # doğrudan okundu):
    #   TP.PKAUO.S01.E.U = "12 Ay SONRASININ Yıllık TÜFE Beklentisi"
    #   TP.PKAUO.S01.F.U = "24 Ay SONRASININ Yıllık TÜFE Beklentisi"
    #   TP.PKAUO.S01.G.U = "5 Yıl SONRASININ Yıllık TÜFE Beklentisi"
    # Yani π24 İKİNCİ YILIN tek yıllık oranıdır, iki yıllık ortalama DEĞİL.
    # Başabaş enflasyon ise tanımı gereği vadeye kadarki yıllık ORTALAMA'dır.
    # İkisini doğrudan çıkarmak risk primini şişirir: 21.08.2026'da 2 yıllık
    # ortalama beklenti √(1,2369·1,1803)−1 = %20,83'tür; nokta beklentiyi
    # (%18,03) kullanmak primi 9,01 yerine 11,80 puan gösterir (%31 şişik).
    #
    # VARSAYIM (metodoloji notu): çıpalar arasında yıllık enflasyon patikası
    # LOG-DOĞRUSAL ara değerle kurulur — 1. yıl π12, 2. yıl π24, 5. yıl π5y;
    # 3. ve 4. yıl bu iki çıpa arasında log(1+π) ekseninde doğrusaldır.
    # Patika bir VARSAYIMDIR; anket 3. ve 4. yılı sormaz.
    ort_bek = anket_ortalama({1: pka12, 2: pka24, 5: pka5y}, REEL_DUGUM)
    for v, seri in ort_bek.items():
        M[f"pka_ort_{REEL_AD[v][1:]}"] = seri

    # --- REEL FAİZ (FISHER — bağlayıcı konvansiyon) ------------------------
    #   r = (1 + i) / (1 + π) − 1     ·  basit çıkarma (i − π) DEĞİL
    M["reel_ileri"] = ((1 + M["n1y"] / 100) / (1 + pka12 / 100) - 1) * 100.0
    M["reel_geriye"] = ((1 + M["n1y"] / 100) / (1 + tufe_yillik / 100) - 1) * 100.0
    # 2 yıllık reel faizde π olarak İKİ YILLIK ORTALAMA beklenti kullanılır;
    # 2 yıllık nominal getiri de yıllıklandırılmış ortalamadır — iki taraf
    # ancak böyle aynı ufku ölçer.
    M["reel_ileri_2y"] = ((1 + M["n2y"] / 100)
                          / (1 + M["pka_ort_2y"] / 100) - 1) * 100.0
    M["reel_ileri_basit"] = M["n1y"] - pka12           # YALNIZ ders için
    M["fisher_basit_fark"] = M["reel_ileri_basit"] - M["reel_ileri"]
    M["reel_makas"] = M["reel_ileri"] - M["reel_geriye"]

    # --- TÜFEX reel eğri ve başabaş enflasyon ------------------------------
    R, reel_kesitler, KT = reel_paneli(d["T"], d["KT"], d["cpi"], tarih)
    M = M.join(R)
    for v, ad in REEL_AD.items():
        n_ad = DUGUM_AD[v]
        if n_ad in M.columns and ad in M.columns:
            M[f"be_{ad[1:]}"] = (((1 + M[n_ad] / 100) / (1 + M[ad] / 100) - 1)
                                 * 100.0)
    # Enflasyon risk primi / şüphe payı: BAŞABAŞ ≠ BEKLENTİ.
    # HER İKİ TARAF DA VADEYE KADARKİ ORTALAMADIR (yukarıdaki patika notu).
    # prim_1y'de iki taraf zaten aynıydı (π12 ilk yılın oranı = ilk yılın
    # ortalaması); 2, 5 ve 7 yılda ortalamaya çevirmek şart.
    M["prim_1y"] = M["be_1y"] - M["pka_ort_1y"]
    M["prim_2y"] = M["be_2y"] - M["pka_ort_2y"]
    M["prim_3y"] = M["be_3y"] - M["pka_ort_3y"] if "be_3y" in M.columns else np.nan
    M["prim_5y"] = M["be_5y"] - M["pka_ort_5y"]
    M["prim_7y"] = M["be_7y"] - M["pka_ort_7y"] if "be_7y" in M.columns else np.nan

    # --- ana bileşenler ----------------------------------------------------
    PC, pca_tani = ana_bilesenler(M)
    if not PC.empty:
        M = M.join(PC)
        print(f"  ana bileşenler: {len(PC)} gün · açıklanan pay "
              f"{', '.join(f'%{p * 100:.1f}' for p in pca_tani['aciklanan_pay'])}")
    else:
        uyar("PCA kurulamadı — düğüm paneli 60 tam günden az.")

    # --- kimlik denetimi ---------------------------------------------------
    sap_med = M["sapma_medyan"].dropna()
    sap_maks = M["sapma_maks"].dropna()
    kimlik = {
        "n_gun": int(len(sap_med)),
        "medyan_medyan": round(float(sap_med.median()), 4) if len(sap_med) else None,
        "medyan_son": round(float(sap_med.iloc[-1]), 4) if len(sap_med) else None,
        "maks_maks": round(float(sap_maks.max()), 4) if len(sap_maks) else None,
        "maks_tarih": str(sap_maks.idxmax().date()) if len(sap_maks) else None,
        "esik_medyan": SAPMA_MEDYAN_ESIK, "esik_maks": SAPMA_MAKS_ESIK,
        "cok_kaynakli_vade_son": int(
            kesitler[s_gun].groupby("itfa").size().gt(1).sum()) if s_gun in kesitler else 0,
    }
    dur: list[str] = []
    if len(sap_med) and float(sap_med.iloc[-1]) > SAPMA_MEDYAN_ESIK:
        uyar(f"EĞRİ TUTARSIZ: çıpa gününde aynı itfaya düşen strip'ler arasında "
             f"medyan {sap_med.iloc[-1]:.3f} puan fark var (eşik "
             f"{SAPMA_MEDYAN_ESIK}). Sınıflandırma bozulmuş olabilir.")
    if len(sap_maks) and float(sap_maks.iloc[-1]) > SAPMA_MAKS_ESIK:
        dur.append(f"KİMLİK BOZUK: çıpa gününde iki bağımsız strip aynı itfada "
                   f"{sap_maks.iloc[-1]:.2f} puan ayrışıyor (eşik "
                   f"{SAPMA_MAKS_ESIK}) — değişken faizli kıymet nominal eğriye "
                   "sızmış olabilir.")
    kimlik["gecti"] = not dur

    # --- YTM çapraz sınaması ----------------------------------------------
    ytm = ytm_sinamasi(d["B"], d["KB"], K, kesitler.get(s_gun, pd.DataFrame()), s_gun)
    if ytm:
        print(f"  YTM çapraz sınaması: {ytm['n']} tahvil · medyan |fark| "
              f"{ytm['medyan_fark_puan']:.3f} puan · maks {ytm['maks_fark_puan']:.3f}")
        if ytm["medyan_fark_puan"] > 1.0:
            uyar(f"YTM SAPMASI: eğri, kuponlu tahvil fiyatlarını medyan "
                 f"{ytm['medyan_fark_puan']:.2f} puan hatayla açıklıyor. "
                 "Gösterge fiyatlar eşzamanlı olmayabilir; eğri yine de "
                 "yayımlanıyor ama bu fark sayfada görünür.")
    else:
        uyar("YTM çapraz sınaması yapılamadı — kuponlu tahvil fiyatı ya da "
             "nakit akışı eşlenemedi.")

    # --- kapsama tanısı ----------------------------------------------------
    kapsama = {
        "ilk_gun": str(tarih[0].date()), "son_gun": str(s_gun.date()),
        "gun_sayisi": int(len(tarih)),
        "dugum_dolu": {k: int(M[k].notna().sum()) for k in DUGUM_AD.values()},
        "dugum_ilk_dolu": {k: (str(M[k].dropna().index[0].date())
                               if M[k].notna().any() else None)
                           for k in DUGUM_AD.values()},
        "reel_dolu": {k: int(M[k].notna().sum()) for k in REEL_AD.values()
                      if k in M.columns},
        "nokta_medyan": int(M["nokta"].median()),
        "nokta_son": int(M.loc[s_gun, "nokta"]),
    }
    for k, v in kapsama["dugum_dolu"].items():
        if v < 0.30 * len(tarih):
            uyar(f"KAPSAMA: '{k}' düğümü {len(tarih)} günün yalnız {v}'inde "
                 "kurulabildi — o vadede yeterli sıfır kuponlu nokta yok.")
    # REEL düğümlerin seyrekliği bir ARIZA DEĞİL, evrenin kendisidir: TÜFEX
    # anapara strip'i sayısı 20 ve vade ekseninde büyük boşluklar var. Boşluğun
    # üstünden atlamak yerine düğüm NaN bırakılıyor (ör. çıpa gününde 2,8 yıl
    # ile 4,8 yıl arasında hiç kıymet olmadığı için 3 yıllık REEL düğüm yok).
    # Bu sayı sayfada görünür: "reel eğri nominal eğri kadar sık değildir".
    kapsama["reel_notu"] = (
        f"TÜFEX evreni {len(KT)} anapara strip'i; reel düğümler nominal "
        "düğümler kadar sık kurulamaz ve vade boşluğu geniş olan düğüm o gün "
        "BOŞ bırakılır (uydurulmuş ara değer basılmaz).")

    # --- kesit dosyaları ---------------------------------------------------
    # Karşılaştırma günleri VERİDEN türetilir (sabit tarih YASAK): çıpadan
    # geriye 1 ay / 3 ay / 1 yıl, panelin o tarihe eşit ya da ondan önceki
    # son dolu günü.
    def _geri(ay: int) -> pd.Timestamp | None:
        hedef = s_gun - pd.DateOffset(months=ay)
        onceki = tarih[tarih <= hedef]
        return onceki[-1] if len(onceki) else None

    kiyas = {"bugun": s_gun}
    for ad, ay in (("1ay", 1), ("3ay", 3), ("1yil", 12)):
        g = _geri(ay)
        if g is not None and g in kesitler and np.isfinite(M.loc[g, "n2y"]):
            kiyas[ad] = g
    parcalar = []
    for ad, g in kiyas.items():
        p = kesitler[g].copy()
        p.insert(0, "kesit", ad)
        p.insert(1, "tarih", g.date())
        parcalar.append(p)
    pd.concat(parcalar).to_csv(VERI / "kesit_egri.csv", index=False)

    if s_gun in reel_kesitler:
        rk = reel_kesitler[s_gun].copy()
        rk.insert(0, "tarih", s_gun.date())
        rk.to_csv(VERI / "kesit_reel.csv", index=False)
    else:
        uyar("TÜFEX kesiti çıpa gününde kurulamadı — reel eğri grafiği eksik kalır.")
    # Reel getirilerin kıymet bazında SAÇILMASI (grafik 08c): tek çizgiye
    # indirgenirse yanlış kesinlik üretir, ham dağılım korunur.
    if reel_kesitler:
        son_gunler = [g for g in tarih[-260:] if g in reel_kesitler]
        if son_gunler:
            dag = pd.concat([reel_kesitler[g].assign(tarih=g.date())
                             for g in son_gunler])
            dag.to_csv(VERI / "reel_dagilim.csv", index=False)

    # --- yazım -------------------------------------------------------------
    M.to_csv(VERI / "metrik.csv", float_format="%.6f")

    def _son(kol: str):
        s = M[kol].dropna()
        return (round(float(s.iloc[-1]), 4), str(s.index[-1].date())) if len(s) else (None, None)

    anlik = {}
    for kol in ("n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y", "n9y", "par2y",
                "egim_2y9y", "egim_2y5y", "egim_2y3a", "kelebek_1_2_5",
                "kelebek_2_5_9", "f_1y1y", "f_2y1y", "f_2y3y",
                "carry_2y_tlref", "carry_2y_politika", "carry_2y_aofm",
                "carry_3a_tlref", "reel_ileri", "reel_geriye", "reel_ileri_2y",
                "reel_ileri_basit", "fisher_basit_fark", "reel_makas",
                "r1y", "r2y", "r3y", "r5y", "r7y",
                "be_1y", "be_2y", "be_3y", "be_5y", "be_7y",
                "prim_1y", "prim_2y", "prim_3y", "prim_5y", "prim_7y",
                "pka_ort_1y", "pka_ort_2y", "pka_ort_3y", "pka_ort_5y",
                "pka_ort_7y",
                "carry_2y_tlref_basit", "carry_2y_aofm_basit",
                "tlref_bilesik", "aofm_bilesik", "politika_bilesik_gercek",
                "politika_birlesik", "konvansiyon_farki_tlref", "fon_top",
                "tlref", "politika", "aofm", "aofm_ham", "koridor_alt",
                "koridor_ust",
                "pka_12a", "pka_24a", "pka_5y", "pka_faiz_12a", "pka_faiz_24a",
                "tufe_yillik", "pka_12a_n"):
        if kol in M.columns:
            v, t = _son(kol)
            anlik[kol] = v
            anlik[kol + "_tarih"] = t

    # --- AOFM geçerlilik durumu -------------------------------------------
    aofm_ge = M["aofm_gecerli"].reindex([s_gun]).fillna(False).iloc[0]
    gec_seri = M.index[M["aofm_gecerli"].fillna(False)]
    aofm_durum = {
        "gecerli": bool(aofm_ge),
        "esik_mn_tl": AOFM_TABAN_ESIK_MN,
        "taban_mn_tl": (float(M.loc[s_gun, "fon_top"])
                        if "fon_top" in M.columns
                        and np.isfinite(M.loc[s_gun, "fon_top"]) else None),
        "son_gecerli_gun": (str(gec_seri[-1].date()) if len(gec_seri) else None),
        "gecersiz_gun_son1y": int((~M["aofm_gecerli"].tail(260)).sum()),
    }
    if not aofm_ge:
        _b = _bicim()
        uyar("AOFM GEÇERSİZ: çıpa gününde APİ fonlaması "
             f"{_b.sayi((aofm_durum['taban_mn_tl'] or 0) / 1000, 1)} milyar TL ile "
             f"{_b.sayi(AOFM_TABAN_ESIK_MN / 1000, 0)} milyar TL eşiğinin altında; "
             "AOFM manşet taşıma ölçüsü olarak KULLANILMAZ (yerine TLREF).")

    # --- başabaş vade yapısının ŞEKLİ (elle 'yukarı eğimli' yazmak yasak) ---
    be_nokta = [(v, float(M.loc[s_gun, f"be_{REEL_AD[v][1:]}"]))
                for v in REEL_DUGUM
                if f"be_{REEL_AD[v][1:]}" in M.columns
                and np.isfinite(M.loc[s_gun, f"be_{REEL_AD[v][1:]}"])]
    basabas_sekil = None
    if len(be_nokta) >= 3:
        vadeler = [v for v, _ in be_nokta]
        degerler = [x for _, x in be_nokta]
        tepe = int(np.argmax(degerler))
        dip = int(np.argmin(degerler))
        if tepe == len(degerler) - 1:
            sekil, tepe_vade = "yukarı eğimli", None
        elif dip == len(degerler) - 1 and tepe == 0:
            sekil, tepe_vade = "aşağı eğimli", None
        elif 0 < tepe < len(degerler) - 1:
            sekil, tepe_vade = "kambur", vadeler[tepe]
        elif 0 < dip < len(degerler) - 1:
            sekil, tepe_vade = "çukur", vadeler[dip]
        else:
            sekil, tepe_vade = "aşağı eğimli", None
        basabas_sekil = {
            "sekil": sekil, "tepe_vade": tepe_vade,
            "vadeler": vadeler, "degerler": [round(x, 4) for x in degerler],
            "ilk_son_fark": round(degerler[-1] - degerler[0], 4),
        }

    # --- çıpa gününde kurulamayan REEL düğümler ---------------------------
    reel_bos = [f"{int(v)} yıl" for v in REEL_DUGUM
                if REEL_AD[v] not in M.columns
                or not np.isfinite(M.loc[s_gun, REEL_AD[v]])]

    ozet = {
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        "son_ay": (str(A["pka_12a"].dropna().index[-1].date())
                   if A["pka_12a"].notna().any() else None),
        "esik": {
            "min_gun": MIN_GUN, "gun_min_nokta": GUN_MIN_NOKTA,
            "getiri_alt_pct": GETIRI_ALT * 100, "getiri_ust_pct": GETIRI_UST * 100,
            "sapma_medyan_esik": SAPMA_MEDYAN_ESIK,
            "sapma_maks_esik": SAPMA_MAKS_ESIK,
            "pka_yayim_gun": PKA_YAYIM_GUN,
            "tufe_yayim_gecikme": TUFE_YAYIM_GECIKME,
        },
        "dugum": DUGUM, "dugum_ad": DUGUM_AD,
        "anlik": anlik,
        "kapsama": kapsama,
        "kimlik": kimlik,
        "aofm_durum": aofm_durum,
        "basabas_sekil": basabas_sekil,
        "reel_bos_dugumler": reel_bos,
        "konvansiyon": {
            "gun_sayisi": GUN_SAYISI,
            "politika_vade_gun": POLITIKA_VADE_GUN,
            "not": ("Fonlama faizleri (TLREF, AOFM, 1 hafta repo) BASİT yıllık "
                    "yayımlanır; eğri getirisi YILLIK BİLEŞİKTİR. Taşıma "
                    "hesabında fonlama faizleri önce bileşiğe çevrilir."),
        },
        "pca": pca_tani,
        "ytm_sinamasi": ytm,
        "kiyas_gunleri": {k: str(v.date()) for k, v in kiyas.items()},
        "tufe_zinciri": d["vd"].get("tufe_zinciri", {}),
        "evren": d["vd"].get("evren", {}),
        "getiri_araligi_disi": disarida,
        "notlar": {
            "bootstrap": ("Spot eğri BOOTSTRAP GEREKTİRMEZ: TCMB her tahvilin "
                          "strip'lerini ayrı yayımlıyor ve strip sıfır kuponludur; "
                          "getiri doğrudan ödeme/fiyat oranından okunur."),
            "on_yil": ("Aktif sıfır kuponlu evrenin en uzun noktası ~9 yıl. "
                       "'2y−10y' eğimi burada 2y−9y ile VEKİL edilmiştir."),
            "gosterge_fiyat": ("bie_pydibs TCMB'nin GÖSTERGE NİTELİĞİNDEKİ "
                               "değerleridir; işlem görmemiş kıymette model "
                               "fiyatı olabilir. Noktalar tam bağımsız gözlem "
                               "değildir — eğrinin bu kadar tutarlı çıkması "
                               "kısmen bunun sonucudur."),
            "basabas": ("Başabaş enflasyon PİYASA BEKLENTİSİ DEĞİLDİR: içinde "
                        "enflasyon risk primi, likidite primi ve TÜFE ölçümüne "
                        "güvensizlik vardır."),
            "referans_endeks": ("TÜFEX referans endeksi EVDS'te YOK; Hazine'nin "
                                "3 ay gecikmeli doğrusal ara değerli tanımı "
                                "yeniden kurulmuştur. Zincir katsayısı örtüşme "
                                "ayından HER KOŞUDA okunur, sabit yazılmaz."),
            "fisher": ("Reel faiz FISHER kimliğiyle hesaplanır: (1+i)/(1+π)−1. "
                       "Basit çıkarma yalnız yöntem farkını göstermek için "
                       "hesaplanmıştır."),
            "konvansiyon": ("TAŞIMA KONVANSİYONU: TLREF, AOFM ve 1 hafta repo "
                            "faizi BASİT yıllık yayımlanır; strip getirisi "
                            "yıllık BİLEŞİKTİR. Karşılaştırmadan önce fonlama "
                            "faizleri bileşiğe çevrilir — gecelik için "
                            "(1+r/365)^365−1, 1 hafta için (1+r·7/365)^(365/7)−1. "
                            "Çevrilmezse taşımanın İŞARETİ ters çıkabilir."),
            "ytm_ozdeslik": ("YTM sınaması BAĞIMSIZ BİR DOĞRULAMA DEĞİL, bir "
                             "İÇ TUTARLILIK ÖZDEŞLİĞİDİR: tahvilin nakit akışı "
                             "kendi strip'lerinden kurulup yine o strip'lerin "
                             "kendi getirileriyle iskonto edildiği için model "
                             "fiyatı zorunlu olarak strip fiyatlarının "
                             "toplamına eşittir — TCMB'nin yayımladığı tahvil "
                             "'Değer'i de odur. Birim sınaması olarak "
                             "değerlidir (ödeme/etiket/eşleme bozulursa "
                             "görünür), doğrulama olarak değil."),
            "anket_patikasi": ("PKA serileri 'X ay SONRASININ yıllık' TÜFE "
                               "oranlarıdır, vadeye kadarki ORTALAMA değil. "
                               "Başabaş enflasyonla karşılaştırmak için 12 ay, "
                               "24 ay ve 5 yıl çıpaları arasında log-doğrusal "
                               "bir yıllık enflasyon PATİKASI kurulur ve "
                               "vadeye kadarki geometrik ortalama alınır. "
                               "Ara yıllar (3, 4) VARSAYIMDIR; son çıpanın "
                               "ötesi (6, 7) sabit tutulur."),
        },
        "uyarilar": list(_UYARI),
    }
    (VERI / "metrik_ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    # Veri katmanının uyarıları da devralınır — devralınmazsa tazelik ve
    # önbellek uyarıları uyarilar.json'a hiç girmez ve sayfada görünmez.
    vd_uy = d["vd"].get("uyarilar") or []
    hepsi = list(dict.fromkeys(vd_uy + _UYARI))
    (PROJE / "uyarilar.json").write_text(json.dumps(
        {"tarih": s_gun.strftime("%Y-%m-%d"),
         "kosum": pd.Timestamp.today().strftime("%Y-%m-%d"),
         "uyarilar": hepsi, "kimlik": kimlik, "ytm_sinamasi":
             {k: v for k, v in (ytm or {}).items() if k != "tablo"}},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  yazıldı: data/metrik.csv ({M.shape[0]}x{M.shape[1]}), "
          f"kesit_egri.csv, kesit_reel.csv, metrik_ozet.json")
    print(f"  çıpa: 3a %{anlik.get('n3a')} · 1y %{anlik.get('n1y')} · "
          f"2y %{anlik.get('n2y')} · 5y %{anlik.get('n5y')} · 9y %{anlik.get('n9y')}")
    print(f"  Fisher ileri reel %{anlik.get('reel_ileri')} · geriye "
          f"%{anlik.get('reel_geriye')} · basit çıkarma "
          f"%{anlik.get('reel_ileri_basit')} (fark "
          f"{anlik.get('fisher_basit_fark')} puan)")
    print(f"  kimlik: medyan sapma {kimlik['medyan_son']} puan "
          f"({kimlik['cok_kaynakli_vade_son']} vadede çoklu kaynak)")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    if dur:
        for x in dur:
            print("  ✗ " + x)
        raise SystemExit(
            "DUR: kimlik denetimi düştü. Yanlış sayı yayına gitmesin diye "
            "grafik ve özet üretilmiyor. Ayrıntı: uyarilar.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(kos())
