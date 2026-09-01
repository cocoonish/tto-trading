# -*- coding: utf-8 -*-
"""Enflasyon panosu — hesap katmanı.

Panonun MERKEZİ ölçüsü yıllık enflasyon DEĞİL, momentumdur: mevsimsellikten
arındırılmış aylık değişimin 3 ve 6 aylık yıllıklandırılmış hâli (SAAR).
Yıllık oran, momentumun 12 aylık hareketli ortalamasıdır ve bugünkü fiyatlama
davranışını bir yıl geriye yayarak bulanıklaştırır.

Bu dosyanın ürettikleri (data/ altına):
  metrik.csv        her ana seri için m/m, SA m/m, 3a/6a SAAR (ham ve SA), 12a,
                    ECB tipi 3a/3a momentum
  sa.csv            mevsimsellikten arındırılmış endeks düzeyleri
  sa_tani.json      arındırma tanıları: ana seriler + ALT KALEMLER (mevsimsellik
                    anlamlı mı, tatil regresörü t/katsayı), koşular arası iz ve
                    GERÇEK uç-nokta revizyon testi (vintage)
  alt_kalem.csv     kesitin 45 üç haneli grup endeksi (dağılım ölçülerinin
                    önbelleğe bağlı kalmadan denetlenebilmesi için)
  agirlik.json      hiyerarşik kısıtlı EKK ile TAHMİN edilen TÜFE ağırlıkları
  katki.csv         beş grubun yıllık ve aylık katkısı (tam toplanabilir)
  dagilim.csv       kırpılmış ortalama (α=0,05/0,08/0,10), ağırlıklı medyan,
                    difüzyon endeksleri
  baz_senaryo.csv   önümüzdeki 12 ayın üç senaryolu yıllık enflasyon patikası
  reel_faiz.csv     ex-post / ex-ante / ana eğilime göre reel faiz
  beklenti.json     PKA isabet ölçüleri (MAE, yanlılık, RMSE; 36 ve 60 ay)
  metrik_ozet.json  ozet_uret.py'nin okuduğu tekil sayılar
  uyarilar.json     veri katmanının uyarıları + hesap katmanının uyarıları

YÖNTEM SEÇİMLERİ VE GEREKÇELERİ
-------------------------------
1. Yıllıklandırma ZİNCİR (geometrik): (P_t/P_{t-n})^(12/n) − 1. Basit
   ölçekleme (12·ortalama) YASAK — Temmuz 2026'da 3 aylıkta 1,5, 6 aylıkta
   3,6 puan sapıtıyor. Aritmetik-ortalama-sonra-bileşikle fark 0,01–0,08 puan;
   zincir seçiliyor çünkü doğrudan endeks düzeyinden gelir, ara yuvarlamaya
   dokunmaz ve "bu tempo 12 ay sürerse yıllık enflasyon şu olur" ifadesinin
   tam karşılığıdır.
2. Mevsimsellikten arındırma: LOG-STL. TÜİK'in resmî arındırılmış TÜFE'si
   EVDS'te YOK (52.694 seri tarandı, tek bir arındırılmış fiyat serisi yok);
   X-13ARIMA-SEATS ise `x13as` ikili dosyasına bağımlı ve cron ortamında
   sessiz kırılma riski taşıyor. Bu yüzden: ön aşamada hareketli dinî tatil
   (Ramazan / Ramazan Bayramı / Kurban Bayramı) regresörü, sonra
   STL(log, period=12, seasonal=13, robust=True), mevsimsel bileşen çıkarılıp
   exp ile geri alınır (çarpımsal arındırmaya denk). Sayfada "TCMB'nin
   arındırılmış serisi" DENMEZ — "bu çalışmanın STL arındırması" denir.
3. Ağırlıklar EVDS'te YAYIMLANMIYOR. Zincir-Laspeyres özdeşliğinden
   (P_t/P_Ara = Σ w_i · P_it/P_i,Ara) kısıtlı en küçük karelerle TAHMİN
   ediliyor; her düğümde artık raporlanıyor. Bağımsız doğrulama: yöntem 2026
   için hizmet ağırlığında +7,5, enerjide −3,2, temel malda −2,9 puanlık
   değişim buluyor — TCMB Blog'un yayımladığı +7,4 / −3,2 / −3,0 ile
   örtüşüyor. Kimlik artığı eşiği aşarsa katkı grafiği ÜRETİLMEZ.

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import datetime as dt
import json
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL

import veri
from veri import VERI, ad_uzun

warnings.filterwarnings("ignore", category=RuntimeWarning)

UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in UYARI:
        UYARI.append(m)
    print("  ! " + m, flush=True)


# ===========================================================================
# 1. Hareketli dinî tatil regresörü (Ramazan, Ramazan Bayramı, Kurban Bayramı)
# ===========================================================================
# Hicri takvime bağlı tatiller Miladi takvimde her yıl ~11 gün geriye kayar ve
# 33 yılda tüm ayları dolaşır. "Yıldan yıla aynı ayda tekrar eden" mevsimsellik
# tanımına UYMAZLAR: otomatik mevsimsel filtreler bu etkiyi mevsimsel bileşene
# ayrıştıramaz, düzensiz bileşene atar. Doğru yer, filtreden ÖNCEKİ ön-arındırma
# aşamasıdır (TÜİK'in mevsim-takvim çerçevesi de dört takvim etkisinden birini
# "arefe günleriyle birlikte Ramazan ve Kurban bayramları" olarak tanımlar).
#
# Takvim: aritmetik (tabular) Hicri takvim — Kuveyti algoritma. Diyanet'in
# rasat tabanlı ilanından ±1 gün sapabilir; AYLIK bir regresör için bu sapma
# ihmal edilebilir (bir ayın kaç gününün Ramazan'a düştüğünü ölçüyoruz).
# Merkezleme: Census Bureau `genhol` mantığı — regresör uzun dönem takvim ayı
# ortalamasıyla merkezlenir, böylece yıllık toplamda mevsimsel bileşene sızmaz.

def _hicri_ay_basi_jdn(hy: int, hm: int) -> int:
    """Hicri (hy, hm, 1) → Julian Day Number (aritmetik takvim)."""
    return (int((11 * hy + 3) / 30) + 354 * hy + 30 * hm
            - int((hm - 1) / 2) + 1 - 385 + 1948440 - 1)


def _jdn(y: int, m: int, d: int) -> int:
    """Miladi → Julian Day Number."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    return d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045


def _hicri_yil_araligi(g_bas: int, g_son: int) -> range:
    return range(int((g_bas - 622) * 33 / 32) - 1, int((g_son - 622) * 33 / 32) + 3)


def tatil_regresorleri(idx: pd.DatetimeIndex) -> pd.DataFrame:
    """Aylık, MERKEZLENMİŞ hareketli tatil regresörleri.

    ramazan : ayın kaç gününün Ramazan'a (Hicri 9. ay) düştüğü / ay uzunluğu
    bayram  : Ramazan Bayramı (1–3 Şevval) + arefe, aynı biçimde
    kurban  : Kurban Bayramı (10–13 Zilhicce) + arefe, aynı biçimde
    """
    def _pay(y0: int, y1: int) -> pd.DataFrame:
        gun = pd.date_range(f"{y0}-01-01", f"{y1}-12-31", freq="D")
        jd = np.array([_jdn(t.year, t.month, t.day) for t in gun])
        ram = np.zeros(len(gun), bool)
        bay = np.zeros(len(gun), bool)
        kur = np.zeros(len(gun), bool)
        for hy in _hicri_yil_araligi(y0, y1):
            r0 = _hicri_ay_basi_jdn(hy, 9)          # Ramazan başı
            r1 = _hicri_ay_basi_jdn(hy, 10) - 1     # Ramazan sonu
            ram |= (jd >= r0) & (jd <= r1)
            b0 = _hicri_ay_basi_jdn(hy, 10)         # 1 Şevval
            bay |= (jd >= b0 - 1) & (jd <= b0 + 2)  # arefe + 3 gün
            k0 = _hicri_ay_basi_jdn(hy, 12) + 9     # 10 Zilhicce
            kur |= (jd >= k0 - 1) & (jd <= k0 + 3)  # arefe + 4 gün
        d = pd.DataFrame({"ramazan": ram, "bayram": bay, "kurban": kur},
                         index=gun).astype(float)
        ay = d.resample("MS").mean()
        return ay

    # Uzun dönem merkezleme: dört Hicri döngüyü kapsayan pencere (~132 yıl).
    uzun = _pay(1930, 2060)
    ort = uzun.groupby(uzun.index.month).mean()
    kisa = _pay(idx.min().year - 1, idx.max().year + 2)
    kisa = kisa.reindex(idx)
    for c in kisa.columns:
        kisa[c] = kisa[c].values - ort[c].reindex(idx.month).values
    return kisa


# ===========================================================================
# 2. Mevsimsellikten arındırma
# ===========================================================================
SA_SEASONAL = 13     # STL mevsimsel pencere
SA_PERIOD = 12
SA_YONTEM = "STL(log, period=12, seasonal=13, robust) + hareketli tatil ön-arındırması"
MEVSIM_P_ESIK = 0.10   # ay kuklalarının ortak anlamlılık eşiği


def _f_testi(dy: pd.Series) -> float:
    """Δln P üzerinde 11 ay kuklasının ortak anlamlılığı — F testi p-değeri.

    ÖNCE TREND ALINIR (13 aylık ortalanmış hareketli ortalama çıkarılır).
    Gerekçe: Türkiye'de aylık enflasyonun ORTALAMASI 2005–2026 boyunca %0,5 ile
    %5 arasında geziniyor; ham Δln P üzerinde ay kuklaları bu sürüklenmeyle
    yarıştığı için test gücü çöküyordu — çekirdek B için ham veriyle p=0,15
    (mevsimsellik yok) çıkarken, trendden arındırılmış veriyle p=0,002 çıkıyor.
    Bu ayrım pazarlık konusu değil: mevsimsellik yanlışlıkla "yok" sayılırsa
    3 aylık SAAR ham hâline döner ve anlamını yitirir."""
    from scipy import stats
    d = (dy - dy.rolling(13, center=True).mean()).dropna()
    if len(d) < 48:
        return 1.0
    X = pd.get_dummies(d.index.month, drop_first=True).astype(float).values
    X = np.column_stack([np.ones(len(d)), X])
    y = d.values
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e1 = y - X @ beta
    e0 = y - y.mean()
    k = X.shape[1] - 1
    n = len(y)
    ssr1, ssr0 = float(e1 @ e1), float(e0 @ e0)
    if ssr1 <= 0 or n - k - 1 <= 0:
        return 0.0
    F = ((ssr0 - ssr1) / k) / (ssr1 / (n - k - 1))
    return float(1 - stats.f.cdf(F, k, n - k - 1))


def arindir(p: pd.Series) -> tuple[pd.Series, dict]:
    """Log-STL arındırma + hareketli tatil ön-arındırması.

    Dönen: (arındırılmış endeks, tanı sözlüğü). Mevsimsellik istatistiksel
    olarak anlamsız çıkarsa seri ARINDIRILMAZ (yalnız tatil düzeltmesi
    uygulanır) ve tanıda `mevsimsel=False` işaretlenir — TCMB'nin işlenmiş gıda
    için düştüğü notun aynısı.
    """
    p = p.dropna().astype(float)
    tani = {"n": int(len(p))}
    if len(p) < 60:
        tani.update({"mevsimsel": False, "not": "60 aydan kısa seri — arındırılmadı"})
        return p, tani
    y = np.log(p)
    dy = y.diff()
    # --- ön aşama: hareketli tatil regresyonu
    R = tatil_regresorleri(pd.DatetimeIndex(p.index))
    ort = R.loc[dy.dropna().index]
    X = np.column_stack([np.ones(len(ort)), ort.values])
    yy = dy.dropna().values
    beta, *_ = np.linalg.lstsq(X, yy, rcond=None)
    e = yy - X @ beta
    s2 = float(e @ e) / max(len(yy) - X.shape[1], 1)
    XtX_inv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.diag(XtX_inv) * s2)
    t_ist = beta[1:] / np.where(se[1:] == 0, np.nan, se[1:])
    # yalnız |t|>1,96 olan regresörler çıkarılır (gürültü eklememek için)
    kat = np.where(np.abs(t_ist) > 1.96, beta[1:], 0.0)
    duzelt = pd.Series(R.values @ kat, index=R.index).reindex(dy.index).fillna(0.0)
    dy_adj = (dy - duzelt).dropna()
    y_adj = pd.concat([pd.Series([y.iloc[0]], index=[y.index[0]]),
                       y.iloc[0] + dy_adj.cumsum()])
    tani["tatil_katsayi"] = {k: round(float(v) * 100, 4)
                             for k, v in zip(R.columns, kat)}
    tani["tatil_t"] = {k: (round(float(v), 2) if np.isfinite(v) else None)
                       for k, v in zip(R.columns, t_ist)}
    # --- mevsimsellik anlamlı mı
    p_deger = _f_testi(dy_adj)
    tani["mevsim_p"] = round(p_deger, 4)
    if p_deger > MEVSIM_P_ESIK:
        tani["mevsimsel"] = False
        return np.exp(y_adj), tani
    tani["mevsimsel"] = True
    r = STL(y_adj, period=SA_PERIOD, seasonal=SA_SEASONAL, robust=True).fit()
    sa = np.exp(y_adj - r.seasonal)
    tani["mevsimsel_genlik_pp"] = round(float(r.seasonal.diff().abs().tail(24).mean()) * 100, 3)
    return sa, tani


# ===========================================================================
# 3. Momentum ölçüleri
# ===========================================================================
def saar(p: pd.Series, n: int) -> pd.Series:
    """Zincir (geometrik) yıllıklandırma: (P_t/P_{t-n})^(12/n) − 1, yüzde.
    Üs 12/n'dir, n/12 DEĞİL (3 ay için ×4, 6 ay için ×2)."""
    return ((p / p.shift(n)) ** (12.0 / n) - 1) * 100


def saar_aritmetik(p: pd.Series, n: int) -> pd.Series:
    """Aylık oranların aritmetik ortalaması → bileşik. Zincirle farkı Jensen
    eşitsizliğinden gelir (0,01–0,08 puan); karşılaştırma için tutuluyor."""
    m = p / p.shift(1) - 1
    return ((1 + m.rolling(n).mean()) ** 12 - 1) * 100


def saar_basit(p: pd.Series, n: int) -> pd.Series:
    """12 × ortalama aylık — YANLIŞ ama yaygın tanım. Yalnız tuzağı göstermek
    için hesaplanır, hiçbir grafikte ana seri olarak KULLANILMAZ."""
    m = p / p.shift(1) - 1
    return m.rolling(n).mean() * 1200


def ecb_momentum(p: pd.Series) -> pd.Series:
    """ECB tanımı: üç aylık hareketli ORTALAMALARIN oranı, yıllıklandırılmış.
    İki kez düzleştirdiği için daha az oynak ama ~1,5 ay daha gecikmeli."""
    m3 = p.rolling(3).mean()
    return ((m3 / m3.shift(3)) ** 4 - 1) * 100


def aylik(p: pd.Series) -> pd.Series:
    return (p / p.shift(1) - 1) * 100


def yillik(p: pd.Series) -> pd.Series:
    return (p / p.shift(12) - 1) * 100


# ===========================================================================
# 4. Ağırlık tahmini (hiyerarşik, kısıtlı EKK)
# ===========================================================================
# TÜFE yıl içinde bir önceki yılın ARALIK ayını temel alan zincir Laspeyres'tir:
#     P_t / P_Ara,y-1 = Σ_i w_i^y · (P_it / P_i,Ara,y-1)
# Bu, w üzerinde TAM DOĞRUSAL bir denklem sistemidir. Yıl içindeki her ay bir
# denklem, Σw=1 bir kısıt. Aşırı belirlenmişse EKK; yıl içi ay sayısı yetmezse
# (cari yıl) kimlikler TAM sağlanacak biçimde ÖNCEKİ YILIN ağırlıklarından EN AZ
# sapan çözüm seçilir ve sapma raporlanır.
AGIRLIK_ARTIK_ESIK_PP = 0.05   # kimlik artığı bunu aşarsa katkı üretilmez


def _agirlik_coz(ust: pd.Series, alt: pd.DataFrame, yil: int,
                 oncul: pd.Series | None = None) -> dict | None:
    """Bir yılın paylarını çözer. Yıl içinde TAM VERİSİ OLAN çocuklar kullanılır:
    kimi alt kalem sonradan sepete girer (093 Bahçe ürünleri 12.2018), kimi
    sınıflama değişiminde düşer (095 Kültürel mallar 12.2025'te bitiyor). Eksik
    çocuğun payı atfedilemez; artık bunu görünür kılar."""
    ara = pd.Timestamp(f"{yil - 1}-12-01")
    if ara not in alt.index or pd.isna(ust.get(ara)):
        return None
    aylar = [t for t in alt.index if t.year == yil and not pd.isna(ust.get(t))]
    if len(aylar) < 2:
        return None
    tam = [c for c in alt.columns
           if not pd.isna(alt.loc[ara, c]) and not alt.loc[aylar, c].isna().any()]
    if len(tam) < 2:
        return None
    X = (alt.loc[aylar, tam] / alt.loc[ara, tam]).values.astype(float)
    y = (ust.loc[aylar] / ust.loc[ara]).values.astype(float)
    k = len(tam)
    Xr, yr = X[:, :-1] - X[:, [-1]], y - X[:, -1]
    onc_v = None
    if oncul is not None:
        o = oncul.reindex(tam)
        if not o.isna().any() and abs(float(o.sum())) > 1e-9:
            onc_v = (o / o.sum()).values
    if len(aylar) >= k - 1 and onc_v is None:
        w_k, *_ = np.linalg.lstsq(Xr, yr, rcond=None)
        kip = "EKK"
    else:
        onc = (onc_v if onc_v is not None else np.ones(k) / k)[:-1]
        w_k = onc + np.linalg.lstsq(Xr, yr - Xr @ onc, rcond=None)[0]
        kip = "öncüle en yakın" if onc_v is not None else "eşit ağırlık öncüllü"
    w = np.append(w_k, 1 - w_k.sum())
    artik = float(np.abs(X @ w - y).max()) * 100
    return {"paylar": pd.Series(w, index=tam), "artik_pp": round(artik, 4),
            "n_ay": len(aylar), "kip": kip,
            "negatif": int((w < -1e-6).sum()),
            "eksik_cocuk": int(alt.shape[1] - k)}


def agirlik_tahmini(a: pd.DataFrame, ust_ad: str, alt_adlar: list[str],
                    yillar: list[int]) -> dict:
    """Bir düğümün çocuk paylarını yıl yıl tahmin eder (öncül = önceki yıl)."""
    out: dict[str, dict] = {}
    onc: pd.Series | None = None
    for yil in yillar:
        r = _agirlik_coz(a[ust_ad], a[alt_adlar], yil, oncul=onc)
        if r is None:
            continue
        out[str(yil)] = {"paylar": {k: round(float(v), 6)
                                    for k, v in r["paylar"].items()},
                         "artik_pp": r["artik_pp"], "n_ay": r["n_ay"],
                         "kip": r["kip"], "negatif_pay": r["negatif"],
                         "eksik_cocuk": r["eksik_cocuk"]}
        onc = r["paylar"]
    return out


def etkin_agirlik(w_yil: dict[str, dict], a: pd.DataFrame, alt_adlar: list[str],
                  ay: pd.Timestamp) -> pd.Series | None:
    """ω_{i,t-1} = w_i^y (P_{i,t-1}/P_{i,Ara,y-1}) / Σ_j (…)

    Yıl başı ağırlığıyla değil CARİ ETKİN ağırlıkla çalışmak zorunlu: kalem yıl
    içinde göreli olarak pahalılaştıkça sepetteki payı büyür, yıl sonuna doğru
    sapma birikir. Aynı ω hem kırpma/medyanda hem katkı ayrıştırmasında
    kullanılır. O ay fiyatı olmayan kalem kesitten düşer ve ω yeniden
    ölçeklenir (payı atfedilmez, kayıp GÖRÜNÜR kalır: kesit_n sütunu)."""
    yil = ay.year
    oncek = ay - pd.DateOffset(months=1)
    ara = pd.Timestamp(f"{yil - 1}-12-01")
    if str(yil) not in w_yil or ara not in a.index or oncek not in a.index:
        return None
    w = pd.Series(w_yil[str(yil)]["paylar"])
    ad = [c for c in alt_adlar if c in w.index]
    if not ad:
        return None
    oran = (a.loc[oncek, ad] / a.loc[ara, ad]).astype(float)
    om = (w[ad] * oran).dropna()
    om = om[om.index[a.loc[ay, om.index].notna().values]] if ay in a.index else om
    if om.empty or om.sum() == 0:
        return None
    return om / om.sum()


# ===========================================================================
# 5. Katkı ayrıştırma
# ===========================================================================
def katki_hesapla(a: pd.DataFrame, alt_adlar: list[str], w_yil: dict,
                  baslangic: pd.Timestamp) -> pd.DataFrame:
    """Aylık katkı C_it = ω_{i,t-1}·r_it (Σ C_it = π_t birebir) ve yıllık katkı
    (aylık katkıların İLERİYE BİLEŞİKLENMİŞ 12 aylık toplamı).

    Yaygın hata yıllık katkıyı w_i·(P_it/P_i,t-12 − 1) ile yazmaktır; Aralık
    ağırlık güncellemesi bu formülü bozar ve toplam manşete oturmaz."""
    aylar = [t for t in a.index if t >= baslangic and not pd.isna(a.loc[t, "tufe"])]
    kayit = []
    for t in aylar:
        om = etkin_agirlik(w_yil, a, alt_adlar, t)
        if om is None:
            continue
        onc = t - pd.DateOffset(months=1)
        ad = list(om.index)
        r = (a.loc[t, ad] / a.loc[onc, ad] - 1).astype(float)
        c = om * r
        pi = float(a.loc[t, "tufe"] / a.loc[onc, "tufe"] - 1)
        kayit.append({"tarih": t, **{f"c_{k}": float(v) for k, v in c.items()},
                      "pi": pi, "artik": pi - float(c.sum())})
    k = pd.DataFrame(kayit).set_index("tarih")
    if k.empty:
        return k
    # yıllık katkı: C^(12)_it = Σ_{s=t-11}^{t} C_is · Π_{u=s+1}^{t} (1+π_u)
    kol = [f"c_{x}" for x in alt_adlar]
    yil_k = pd.DataFrame(index=k.index, columns=[f"y_{x}" for x in alt_adlar],
                         dtype=float)
    for i in range(11, len(k)):
        pen = k.iloc[i - 11:i + 1]
        # ileri bileşikleme çarpanı: s ayından t'ye kadar (1+π_u), u=s+1..t
        carp = np.array([np.prod(1 + pen["pi"].values[j + 1:]) for j in range(12)])
        yil_k.iloc[i] = (pen[kol].values * carp[:, None]).sum(axis=0)
    k = k.join(yil_k)
    k["pi_12"] = a["tufe"].reindex(k.index) / a["tufe"].reindex(
        k.index - pd.DateOffset(months=12)).values - 1
    # min_count=1: ilk 11 ayda yıllık katkı henüz TANIMLI DEĞİL (12 aylık pencere
    # dolmadı). Düz .sum() bu satırlarda NaN'ları 0 sayıp artığı manşetin
    # kendisi kadar (10–12 puan) gösteriyordu — sahte bir tanı.
    k["yil_artik"] = k["pi_12"] - k[[f"y_{x}" for x in alt_adlar]].sum(
        axis=1, min_count=1)
    return k


# ===========================================================================
# 6. Kırpılmış ortalama, medyan, difüzyon
# ===========================================================================
KIRPMA = (0.05, 0.08, 0.10)      # Cleveland Fed standardı α=0,08 (%16 kırpma)
HEDEF_YILLIK = 5.0               # TCMB hedefi → aylık eşdeğer tempo
HEDEF_AYLIK = ((1 + HEDEF_YILLIK / 100) ** (1 / 12) - 1) * 100


def kirpilmis(deger: pd.Series, agirlik: pd.Series, alfa: float) -> float:
    d = pd.DataFrame({"r": deger, "w": agirlik}).dropna().sort_values("r")
    if d.empty:
        return np.nan
    d["w"] = d["w"] / d["w"].sum()
    F = d["w"].cumsum() - d["w"] / 2          # kalem ORTASINDAKİ kümülatif ağırlık
    sec = (F >= alfa) & (F <= 1 - alfa)
    if not sec.any() or d.loc[sec, "w"].sum() == 0:
        return np.nan
    return float((d.loc[sec, "r"] * d.loc[sec, "w"]).sum() / d.loc[sec, "w"].sum())


def agirlikli_medyan(deger: pd.Series, agirlik: pd.Series, kalem: bool = False):
    """Ağırlıklı medyan — kirpilmis() ile AYNI kümülatif konvansiyon.

    F_i = Σ_{l≤i} ω_l − ω_i/2 (kalemin ORTASINDAKİ kümülatif ağırlık) ve
    F_i ≥ 0,5 olan ilk kalem seçilir. Üst-kenar konvansiyonu (cumsum ≥ 0,5)
    aynı kesitte medyanı bir tam kalem kaydırabilirdi; kesit yoğunken (tek bir
    kalem ağırlığın ~%22'sini taşıyor) bu fark medyanı kırpılmış ortalamayla
    tutarsız kılar. Orta-nokta konvansiyonu α→0,5 limitinde kırpılmış ortalamayla
    medyanın çakışmasını da sağlar.

    kalem=True ise (değer, kalem_adı) döner — medyanı hangi kalemin verdiğini
    izlemek için (kesit yoğunlaşması tanısı).
    """
    d = pd.DataFrame({"r": deger, "w": agirlik}).dropna().sort_values("r")
    if d.empty:
        return (np.nan, None) if kalem else np.nan
    w = d["w"] / d["w"].sum()
    F = w.cumsum() - w / 2
    sec = F.index[F >= 0.5]
    k = sec[0] if len(sec) else d.index[-1]
    return (float(d.loc[k, "r"]), str(k)) if kalem else float(d.loc[k, "r"])


def difuzyon(deger: pd.Series, agirlik: pd.Series, esik: float) -> float:
    d = pd.DataFrame({"r": deger, "w": agirlik}).dropna()
    if d.empty:
        return np.nan
    return float((d.loc[d["r"] > esik, "w"].sum() / d["w"].sum()) * 100)


# ===========================================================================
# 7. Baz etkisi patikası
# ===========================================================================
def baz_patikasi(p: pd.Series, p_sa: pd.Series, ufuk: int = 12) -> pd.DataFrame:
    """1+π^(12)_{t+h} = (1+π^(12)_t) · Π(1+π_{t+s}) / Π(1+π_{t+s-12})

    Paydadaki çarpım TAMAMEN BİLİNİR — baz etkisi bir öngörü değil, muhasebe
    kimliğidir. "Baz etkisiyle enflasyon düşecek" cümlesi, ileri aylık patika
    varsayımı yazılmadan anlamsızdır; bu yüzden her senaryonun aylık varsayımı
    çıktıda ayrı sütun olarak taşınır.

    Üç senaryo:
      son3_sa    — mevsimsellikten arındırılmış son 3 ayın ortalama aylık
                   temposu sabit devam eder (momentum senaryosu)
      son12_ort  — son 12 ayın ortalama aylık temposu sabit devam eder
      gecen_yil  — geçen yılın aynı aylık oranları tekrarlanır; bu senaryoda
                   yıllık enflasyon SABİT kalır ve aracın kendini doğrulamasıdır
    """
    m = (p / p.shift(1) - 1).dropna()
    m_sa = (p_sa / p_sa.shift(1) - 1).dropna()
    son = p.index[-1]
    dusen = [float(m.get(son - pd.DateOffset(months=12 - s), np.nan))
             for s in range(1, ufuk + 1)]
    yil_son = float(p.iloc[-1] / p.iloc[-13] - 1)
    sen = {
        "son3_sa": [float((1 + m_sa.tail(3)).prod() ** (1 / 3) - 1)] * ufuk,
        "son12_ort": [float((1 + m.tail(12)).prod() ** (1 / 12) - 1)] * ufuk,
        "gecen_yil": list(dusen),
    }
    kayit = []
    for h in range(1, ufuk + 1):
        t = son + pd.DateOffset(months=h)
        satir = {"tarih": t}
        payda = float(np.prod([1 + x for x in dusen[:h]]))
        satir["dusen_aylik"] = dusen[h - 1] * 100
        for ad, patika in sen.items():
            pay = float(np.prod([1 + x for x in patika[:h]]))
            satir[ad] = ((1 + yil_son) * pay / payda - 1) * 100
            satir[f"{ad}_aylik"] = patika[h - 1] * 100
        kayit.append(satir)
    return pd.DataFrame(kayit).set_index("tarih")


# ===========================================================================
# 8. Beklenti isabeti
# ===========================================================================
def beklenti_isabeti(a: pd.DataFrame) -> dict:
    """e_{t,h} = π_t − π^e_{t|t-h}. Yanlılık > 0 → anket EKSİK tahmin etmiş.

    PKA ayın ilk yarısında yapılır ve CARİ AY etiketiyle yayımlanır:
      TP.PKAUO.S01.A.U  → o ayın aylık TÜFE'si            (h = 0, nowcast)
      TP.PKAUO.S01.B.U  → bir SONRAKİ ayın aylık TÜFE'si  (h = 1)
      TP.PKAUO.S01.C.U  → iki ay sonrasının aylık TÜFE'si (h = 2)
    """
    m = aylik(a["tufe"].dropna())
    out: dict[str, dict] = {}
    for h, kod in ((0, "pka_ay_cari"), (1, "pka_ay_1"), (2, "pka_ay_2")):
        if kod not in a.columns:
            continue
        bek = a[kod].dropna()
        hedef = bek.copy()
        hedef.index = hedef.index + pd.DateOffset(months=h)
        d = pd.DataFrame({"g": m, "b": hedef}).dropna()
        if d.empty:
            continue
        e = d["g"] - d["b"]
        out[f"h{h}"] = {}
        for pen in (36, 60):
            ee = e.tail(pen)
            out[f"h{h}"][f"p{pen}"] = {
                "n": int(len(ee)),
                "mae": round(float(ee.abs().mean()), 3),
                "yanlilik": round(float(ee.mean()), 3),
                "rmse": round(float(np.sqrt((ee ** 2).mean())), 3),
            }
    return out


# ===========================================================================
# 9. Reel faiz
# ===========================================================================
def reel(i_pct: float, pi_pct: float) -> float:
    """Tam Fisher: (1+i)/(1+π) − 1. Yaklaşık (i−π) yüksek enflasyonda
    kullanılamaz: i=%40, π=%32 iken tam formül %6,06 verirken yaklaşık %8,00
    verir — 2 puanlık hata."""
    return ((1 + i_pct / 100) / (1 + pi_pct / 100) - 1) * 100


# ===========================================================================
# 10. İTO nowcast regresyonu
# ===========================================================================
def ito_nowcast(a: pd.DataFrame) -> dict:
    """İTO İstanbul endeksi TÜİK'ten 1–2 gün ÖNCE yayımlanır ama gelecek ayın
    öncüsü DEĞİLDİR (bir ay önceden korelasyon ≈ 0). Doğru kullanım: aynı ayın
    nowcast'i. Katsayı her koşuda yeniden tahmin edilir, koda gömülmez."""
    if "ito_ist" not in a.columns:
        return {}
    d = pd.DataFrame({"tufe": aylik(a["tufe"].dropna()),
                      "ito": aylik(a["ito_ist"].dropna())}).dropna()
    if len(d) < 12:
        return {"n": int(len(d)), "not": "örneklem yetersiz"}
    X = np.column_stack([np.ones(len(d)), d["ito"].values])
    b, *_ = np.linalg.lstsq(X, d["tufe"].values, rcond=None)
    ong = X @ b
    e = d["tufe"].values - ong
    nn, kk = len(d), X.shape[1]
    s2 = float(e @ e) / max(nn - kk, 1)          # artık varyansı
    se_artik = float(np.sqrt(s2))
    XtX_inv = np.linalg.pinv(X.T @ X)
    se_b = np.sqrt(np.diag(XtX_inv) * s2)
    r2 = 1 - ((d["tufe"].values - ong) ** 2).sum() / (
        (d["tufe"].values - d["tufe"].mean()) ** 2).sum()
    ileri = pd.DataFrame({"tufe": d["tufe"], "ito1": d["ito"].shift(1)}).dropna()
    # ÖNGÖRÜ aralığı (güven aralığı DEĞİL): x0 = son İTO aylık için
    #   se_ong = sqrt(s2 · (1 + x0' (X'X)^-1 x0))
    # Kritik değer normal yaklaşımıyla değil t(n−2) ile alınır; n=30 mertebesinde
    # fark 0,05 puan civarıdır ama küçük örneklemde t doğrusudur.
    from scipy import stats as _st
    x0 = np.array([1.0, float(d["ito"].iloc[-1])])
    se_ong = float(np.sqrt(s2 * (1.0 + x0 @ XtX_inv @ x0)))
    tkrit = float(_st.t.ppf(0.975, max(nn - kk, 1)))
    ima = float(b[0] + b[1] * x0[1])
    return {
        "n": int(len(d)),
        "ilk_ay": d.index[0].strftime("%Y-%m-%d"),
        "sabit": round(float(b[0]), 4),
        "egim": round(float(b[1]), 4),
        "se_sabit": round(float(se_b[0]), 4),
        "se_egim": round(float(se_b[1]), 4),
        "se_artik": round(se_artik, 4),
        "r": round(float(d["tufe"].corr(d["ito"])), 3),
        "r2": round(float(r2), 3),
        "r_bir_ay_onceden": round(float(ileri["tufe"].corr(ileri["ito1"])), 3),
        "son_ito_aylik": round(float(d["ito"].iloc[-1]), 3),
        "ima_aylik": round(ima, 4),
        "ima_alt": round(ima - tkrit * se_ong, 4),
        "ima_ust": round(ima + tkrit * se_ong, 4),
        "ima_yari_genislik": round(tkrit * se_ong, 4),
        "ornek_disi_sinandi": False,   # geri-sınama YOK; R² tamamen örneklem içi
        "son_ay": d.index[-1].strftime("%Y-%m-%d"),
    }


# 2023 ÖRNEKLEM DIŞI TUTULUYOR — VE BU BİR KARAR OLDUĞU İÇİN ÖLÇÜLÜYOR.
# 2023 Türkiye enflasyonunda rejim yılıydı: Haziran'da seçim sonrası kur
# sıçraması, Temmuz'da ÖTV/KDV ayarlamaları ve %34'lük asgari ücret ara zammı
# tek bir yıla sığdı. Aylık TÜFE aynı yıl içinde %0,04 ile %9,49 arasında
# dolaştı. Böyle bir yılda İTO ile TÜFE arasındaki fark, iki sepetin yapısal
# farkını değil o ayın şokunun iki sepete hangi hızda girdiğini ölçer.
#
# Ama "outlier" demek yetmez; dışlamanın KENDİSİ bir varsayımdır ve sınanmadan
# kabul edilirse tam da kaçındığımız şey olur. Bu yüzden modül her ölçümü İKİ
# örneklemde birden koşturuyor (`karsilastirma` bloğu) ve dışlanan dönemin
# istatistikleri ayrıca yazılıyor (`dislama` bloğu): okur farkın gerçekten
# ayrıştığını GÖRÜR, bize güvenmek zorunda kalmaz.
DISLANAN_YIL = (2023,)


def _ito_yayim() -> dict:
    """İTO'nun KENDİ yayımladığı aylık değişim oranları (ito_yayim.json).

    Bu dosya bir kolaylık değil, bir SİGORTADIR. Hattımızdaki İTO serisi
    EVDS'te `TP.FG.IST1.23` koduyla duruyor ve EVDS erişilebilir hiçbir uçtan
    bu kodun ADINI vermiyor: veri yanıtında ad yok, `datagroups` uçları 404,
    `serieList` boş dönüyor. Yani seriyi "İstanbul TÜFE" diye etiketlemek
    ölçülmemiş bir iddiaydı ve bir süre öyle kaldı.

    Kimlik artık ADLA değil SAYIYLA pinleniyor: her koşuda kendi
    hesapladığımız aylık değişimler İTO'nun yayımıyla karşılaştırılır. 30 ayın
    30'u 0,01 puan içinde tutuyor ve manşet agregaları (yıllık, yıl sonuna
    göre) tam olarak yeniden üretiliyor. Kod bir gün başka bir seriye
    çevrilirse ya da EVDS içeriği değişirse bu karşılaştırma DÜŞER."""
    y = VERI.parent / "ito_yayim.json"
    if not y.exists():
        return {}
    try:
        return json.loads(y.read_text(encoding="utf-8"))
    except Exception as ex:
        uyar(f"ito_yayim.json okunamadı ({type(ex).__name__}) — İTO kimlik "
             f"doğrulaması YAPILAMADI.")
        return {}


# Yuvarlamadan doğan fark 0,01 puanı geçmez (İTO iki ondalık yayımlıyor,
# biz seviye endeksinden hesaplıyoruz). Eşik onun iki katı.
ITO_DOGRULAMA_ESIK = 0.02


def _ito_seri(a: pd.DataFrame) -> tuple[pd.Series, dict]:
    """İTO aylık değişim serisi + kimlik doğrulaması.

    Seri EVDS seviye endeksinden hesaplanır; İTO'nun yayımı hem DOĞRULAR hem
    de EVDS'in veremediği ayları DOLDURUR. Doldurulan ay işaretlenir — bir
    sayının nereden geldiği, sayının kendisi kadar önemli."""
    # dropna ŞART: pct_change ilk ayı NaN bırakır ve o ay indekste DURUR.
    # Düşürülmezse iki kusur birden çıkar — boş ay "ortak ay" diye sayılıp
    # doğrulama örneklemini şişirir, ve indekste göründüğü için doldurma da
    # onu atlar. Seviye endeksinin başladığı ayın değişimi ancak İTO'nun
    # yayımından gelebilir; tam da doldurmanın var oluş sebebi bu.
    ham = (aylik(a["ito_ist"].dropna()).dropna()
           if "ito_ist" in a.columns else pd.Series(dtype=float))
    yay = _ito_yayim()
    kayit = {pd.Timestamp(k + "-01"): float(v)
             for k, v in (yay.get("aylik") or {}).items()}
    tani: dict = {"yayim_ay": len(kayit)}
    if not kayit:
        tani["durum"] = "İTO yayımı yok — kimlik doğrulanamadı"
        return ham, tani

    ortak = [t for t in ham.index if t in kayit]
    if ortak:
        sap = pd.Series({t: ham.loc[t] - kayit[t] for t in ortak})
        tani.update({
            "ortak_ay": len(ortak),
            "maks_sapma": round(float(sap.abs().max()), 4),
            "ort_sapma": round(float(sap.abs().mean()), 4),
            "esik": ITO_DOGRULAMA_ESIK,
            "sapan_ay": int((sap.abs() > ITO_DOGRULAMA_ESIK).sum()),
            "ilk_ay": min(ortak).strftime("%Y-%m"),
            "son_ay": max(ortak).strftime("%Y-%m"),
        })
        tani["dogrulandi"] = bool(tani["sapan_ay"] == 0)
        if not tani["dogrulandi"]:
            kotu = sap[sap.abs() > ITO_DOGRULAMA_ESIK]
            uyar(f"İTO KİMLİK DOĞRULAMASI DÜŞTÜ: {len(kotu)} ayda hesapladığımız "
                 f"değişim İTO'nun yayımıyla {ITO_DOGRULAMA_ESIK} puandan fazla "
                 f"ayrışıyor (en kötü {kotu.abs().max():.3f} puan, "
                 f"{kotu.abs().idxmax():%Y-%m}). EVDS serisi İTO İstanbul TÜFE "
                 f"OLMAYABİLİR ya da içeriği değişmiştir.")
    else:
        tani["durum"] = "ortak ay yok — doğrulama yapılamadı"

    # DOLDURMA: EVDS'in veremediği aylar. Seviye endeksi 2024-01'de başlıyor,
    # yani o ayın değişimi hesaplanamaz; son ay da EVDS'e birkaç gün geç düşer.
    eklenen = sorted(t for t in kayit if t not in ham.index)
    for t in eklenen:
        ham = pd.concat([ham, pd.Series([kayit[t]], index=[t])])
    ham = ham.sort_index()
    tani["dolduruldu"] = [t.strftime("%Y-%m") for t in eklenen]
    tani["dolduruldu_n"] = len(eklenen)

    # MANŞET AGREGALARI da yeniden üretilir: aylık oran tutup yıllık tutmuyorsa
    # seri doğru ama BİZİM zincirimiz bozuk demektir.
    ms = (yay.get("mansetler") or {})
    lv = a["ito_ist"].dropna() if "ito_ist" in a.columns else pd.Series(dtype=float)
    kontrol = []
    for ay_s, m in ms.items():
        t = pd.Timestamp(ay_s + "-01")
        onceki = t - pd.DateOffset(months=1)
        if onceki not in lv.index:
            continue
        sev = float(lv.loc[onceki]) * (1 + float(m["aylik"]) / 100.0)
        gecen = t - pd.DateOffset(months=12)
        aralik = pd.Timestamp(f"{t.year - 1}-12-01")
        satir = {"ay": ay_s}
        if gecen in lv.index and m.get("yillik") is not None:
            satir["yillik_bizim"] = round((sev / float(lv.loc[gecen]) - 1) * 100, 2)
            satir["yillik_ito"] = float(m["yillik"])
        if aralik in lv.index and m.get("yil_sonuna_gore") is not None:
            satir["yilsonu_bizim"] = round((sev / float(lv.loc[aralik]) - 1) * 100, 2)
            satir["yilsonu_ito"] = float(m["yil_sonuna_gore"])
        kontrol.append(satir)
        for k1, k2, ad in (("yillik_bizim", "yillik_ito", "yıllık"),
                           ("yilsonu_bizim", "yilsonu_ito", "yıl sonuna göre")):
            if k1 in satir and abs(satir[k1] - satir[k2]) > ITO_DOGRULAMA_ESIK:
                uyar(f"İTO {ay_s} {ad} agregası tutmuyor: bizim "
                     f"{satir[k1]:.2f} · İTO {satir[k2]:.2f}.")
    if kontrol:
        tani["manset"] = kontrol
    return ham, tani


def _ito_kestir(d: pd.DataFrame, a: pd.DataFrame, asgari: int) -> dict:
    """Bir örneklem üzerinde bütün kestirimleri koşturur.

    AYRI FONKSİYON OLMASININ SEBEBİ: aynı hesabın "2023 dahil" ve "2023 hariç"
    iki kopyasını yan yana yazmak, iki kopyanın bir gün sessizce ayrışması
    demekti. Dışlamanın etkisini ölçmek istiyorsak iki ölçüm AYNI koddan
    çıkmalı; yoksa ölçtüğümüz şey dışlama değil, iki kopya arasındaki fark
    olur."""
    from scipy import stats as _st
    if len(d) < 12:
        return {}
    out: dict = {}

    # ---- regresyon (örneklem içi) ve EĞİM = 1 SINAMASI
    X = np.column_stack([np.ones(len(d)), d["ito"].values])
    b_, *_ = np.linalg.lstsq(X, d["tufe"].values, rcond=None)
    e_ = d["tufe"].values - X @ b_
    nn, kk = len(d), X.shape[1]
    s2 = float(e_ @ e_) / max(nn - kk, 1)
    XtX_inv = np.linalg.pinv(X.T @ X)
    se_b = np.sqrt(np.diag(XtX_inv) * s2)
    tkrit = float(_st.t.ppf(0.975, max(nn - kk, 1)))
    t_bir = float((b_[1] - 1.0) / se_b[1]) if se_b[1] else float("nan")
    p_bir = float(2 * (1 - _st.t.cdf(abs(t_bir), max(nn - kk, 1))))
    out["regresyon"] = {
        "n": int(nn), "ilk_ay": d.index[0].strftime("%Y-%m"),
        "son_ay": d.index[-1].strftime("%Y-%m"),
        "sabit": round(float(b_[0]), 3), "se_sabit": round(float(se_b[0]), 3),
        "egim": round(float(b_[1]), 3), "se_egim": round(float(se_b[1]), 3),
        "r": round(float(d["tufe"].corr(d["ito"])), 3),
        "spearman": round(float(_st.spearmanr(d["ito"], d["tufe"]).statistic), 3),
        "r2": round(float(1 - (e_ @ e_) / (((d["tufe"] - d["tufe"].mean()) ** 2).sum())), 3),
        "se_artik": round(float(np.sqrt(s2)), 3),
        "t_egim_bir": round(t_bir, 2), "p_egim_bir": round(p_bir, 4),
        "egim_birden_farkli": bool(p_bir < 0.05),
    }

    # ---- koşullu eşleme: nokta tahmin + ÖNGÖRÜ aralığı (güven aralığı DEĞİL).
    # se_ong = sqrt(s2·(1 + x0'(X'X)^-1 x0)); katsayı belirsizliğine artık
    # varyansı da eklenir — okurun sorduğu "TÜFE nereye düşer" sorusu tek bir
    # gözlemin nereye düşeceği sorusudur.
    esleme = []
    for x in np.arange(0.5, 5.01, 0.5):
        x0 = np.array([1.0, float(x)])
        se = float(np.sqrt(s2 * (1.0 + x0 @ XtX_inv @ x0)))
        m = float(b_[0] + b_[1] * x)
        esleme.append({"ito": round(float(x), 2), "tufe": round(m, 2),
                       "alt": round(m - tkrit * se, 2), "ust": round(m + tkrit * se, 2),
                       "sabit_kural": round(float(x - d["fark"].mean()), 2)})
    out["esleme"] = esleme

    # ---- ORANTISALLIK: fark İTO seviyesine mi bağlı?
    Xo = np.column_stack([np.ones(len(d)), d["ito"].values])
    bo, *_ = np.linalg.lstsq(Xo, d["fark"].values, rcond=None)
    eo = d["fark"].values - Xo @ bo
    s2o = float(eo @ eo) / max(len(d) - 2, 1)
    seo = np.sqrt(np.diag(np.linalg.pinv(Xo.T @ Xo)) * s2o)
    to = float(bo[1] / seo[1]) if seo[1] else float("nan")
    po = float(2 * (1 - _st.t.cdf(abs(to), max(len(d) - 2, 1))))

    # ---- KAYAN KARARLILIK (12 aylık pencere)
    kayan = []
    for i in range(12, len(d) + 1):
        g = d.iloc[i - 12:i]
        Xk = np.column_stack([np.ones(12), g["ito"].values])
        bk, *_ = np.linalg.lstsq(Xk, g["tufe"].values, rcond=None)
        kayan.append({"ay": g.index[-1].strftime("%Y-%m"),
                      "r": round(float(g["tufe"].corr(g["ito"])), 3),
                      "egim": round(float(bk[1]), 3),
                      "ort_fark": round(float(g["fark"].mean()), 3)})
    out["kayan"] = kayan
    out["oranti"] = {
        "egim": round(float(bo[1]), 3), "se": round(float(seo[1]), 3),
        "t": round(to, 2), "p": round(po, 4),
        "r": round(float(d["fark"].corr(d["ito"])), 3),
        "anlamli": bool(po < 0.05),
        "oran_medyan": round(float((d["tufe"] / d["ito"]).median()), 3),
        "kayan_ilk": round(float(kayan[0]["ort_fark"]), 3) if kayan else None,
        "kayan_son": round(float(kayan[-1]["ort_fark"]), 3) if kayan else None,
        "kayan_maks": round(float(max(x["ort_fark"] for x in kayan)), 3) if kayan else None,
        "kayan_r_min": round(float(min(x["r"] for x in kayan)), 3) if kayan else None,
        "kayan_r_maks": round(float(max(x["r"] for x in kayan)), 3) if kayan else None,
        "kayan_egim_min": round(float(min(x["egim"] for x in kayan)), 3) if kayan else None,
        "kayan_egim_maks": round(float(max(x["egim"] for x in kayan)), 3) if kayan else None,
        "kayan_n": len(kayan),
    }

    # ---- KURAL YARIŞI — genişleyen pencere, örneklem DIŞI.
    # Her ay için kuralın bütün parametreleri yalnız o ana kadarki veriyle
    # kurulur; hiçbir kural kendi geleceğini görmez.
    def _yaris(asg: int) -> tuple[dict, list]:
        satir = []
        for k in range(asg, len(d)):
            g, x = d.iloc[:k], d.iloc[k]
            xi, ay = float(x["ito"]), d.index[k].month
            Xg = np.column_stack([np.ones(len(g)), g["ito"].values])
            bg, *_ = np.linalg.lstsq(Xg, g["tufe"].values, rcond=None)
            ga = g[g.index.month == ay]
            satir.append({
                "ay": d.index[k].strftime("%Y-%m"),
                "gercek": round(float(x["tufe"]), 2),
                "naif": round(xi, 3),
                "sabit": round(xi - float(g["fark"].mean()), 3),
                "medyan": round(xi - float(g["fark"].median()), 3),
                "oransal": round(xi * float((g["tufe"] / g["ito"]).median()), 3),
                "regresyon": round(float(bg[0] + bg[1] * xi), 3),
                "takvimli": round(xi - float(ga["fark"].mean() if len(ga) >= 2
                                             else g["fark"].mean()), 3),
            })
        if not satir:
            return {}, []
        df = pd.DataFrame(satir).set_index("ay")
        skor = {}
        for c in ("naif", "sabit", "medyan", "oransal", "regresyon", "takvimli"):
            h = (df[c] - df["gercek"]).values
            skor[c] = {"mae": round(float(np.abs(h).mean()), 3),
                       "rmse": round(float(np.sqrt((h ** 2).mean())), 3),
                       "yanlilik": round(float(h.mean()), 3),
                       "isabet_03": round(float((np.abs(h) <= 0.3).mean() * 100), 0),
                       "isabet_05": round(float((np.abs(h) <= 0.5).mean() * 100), 0)}
        return skor, satir

    skor, yaris_satir = _yaris(asgari)
    skor_dar, _ = _yaris(asgari + 6)
    kazanan = min(skor, key=lambda c: skor[c]["mae"]) if skor else None
    kazanan_dar = min(skor_dar, key=lambda c: skor_dar[c]["mae"]) if skor_dar else None
    out["kural"] = {
        "asgari": asgari, "asgari_dar": asgari + 6,
        "n": len(yaris_satir),
        "ilk_ay": yaris_satir[0]["ay"] if yaris_satir else None,
        "son_ay": yaris_satir[-1]["ay"] if yaris_satir else None,
        "skor": skor, "kazanan": kazanan,
        "skor_dar": skor_dar, "kazanan_dar": kazanan_dar,
        "siralama_dayanikli": bool(kazanan is not None and kazanan == kazanan_dar),
        "takvimli_zarar": (round(skor["takvimli"]["mae"] - skor[kazanan]["mae"], 3)
                           if kazanan else None),
        "satir": yaris_satir,
    }

    # ---- ANKET KIYASI ve SÜRPRİZ REGRESYONU
    # PKA'nın cari ay sorusu ayın İLK YARISINDA sorulur; İTO ayın SONUNDA
    # oluşur ve ertesi ayın başında yayımlanır. Yani İTO ankete göre iki üç
    # haftalık YENİ bilgidir ve "sürpriz sürprizi öngörür mü" sorusu meşrudur.
    out["anket"], out["surpriz"] = {}, {}
    if "pka_ay_cari" in a.columns:
        dp = pd.DataFrame({"tufe": d["tufe"], "ito": d["ito"],
                           "pka": a["pka_ay_cari"].dropna()}).dropna()
        if len(dp) >= 18:
            e_pka = (dp["pka"] - dp["tufe"]).values
            ort_fark = float(d["fark"].mean())
            e_ito = (dp["ito"] - ort_fark - dp["tufe"]).values      # örneklem İÇİ
            oh_p, oh_i = [], []
            for k in range(asgari, len(dp)):
                g, x = dp.iloc[:k], dp.iloc[k]
                oh_p.append(float(x["pka"] - x["tufe"]))
                oh_i.append(float(x["ito"] - (g["ito"] - g["tufe"]).mean() - x["tufe"]))
            fark_mae = np.abs(np.array(oh_i)) - np.abs(np.array(oh_p))
            t_e, p_e = (_st.ttest_1samp(fark_mae, 0.0) if len(fark_mae) > 1
                        else (float("nan"),) * 2)
            out["anket"] = {
                "n": int(len(dp)), "ilk_ay": dp.index[0].strftime("%Y-%m"),
                "pka_mae_ici": round(float(np.abs(e_pka).mean()), 3),
                "ito_mae_ici": round(float(np.abs(e_ito).mean()), 3),
                "n_disi": len(oh_p),
                "pka_mae": round(float(np.abs(oh_p).mean()), 3),
                "ito_mae": round(float(np.abs(oh_i).mean()), 3),
                "esli_fark": round(float(fark_mae.mean()), 3),
                "esli_t": round(float(t_e), 2), "esli_p": round(float(p_e), 3),
                "ito_anlamli_iyi": bool(p_e < 0.05 and fark_mae.mean() < 0),
            }
            sr = dp["tufe"] - dp["pka"]            # TÜFE sürprizi (fiyatlanan sayıya göre)
            si = dp["ito"] - dp["pka"]             # İTO'nun aynı ankete göre sapması
            Xs = np.column_stack([np.ones(len(dp)), si.values])
            bs, *_ = np.linalg.lstsq(Xs, sr.values, rcond=None)
            es = sr.values - Xs @ bs
            s2s = float(es @ es) / max(len(dp) - 2, 1)
            ses = np.sqrt(np.diag(np.linalg.pinv(Xs.T @ Xs)) * s2s)
            ts = float(bs[1] / ses[1]) if ses[1] else float("nan")
            uyum = ((si > 0) == (sr > 0))
            b25 = si.abs() >= 0.25
            u25 = ((si[b25] > 0) == (sr[b25] > 0))
            t_sab = float(bs[0] / ses[0]) if ses[0] else float("nan")
            p_sab = float(2 * (1 - _st.t.cdf(abs(t_sab), max(len(dp) - 2, 1))))
            out["surpriz"] = {
                "n": int(len(dp)), "sabit": round(float(bs[0]), 3),
                # SABİT AYRI BİR İDDİADIR. Negatif bir sabit "anket sistematik
                # olarak yukarı yanlı" demektir; İTO ankete denk geldiği aylarda
                # tahmini AŞAĞI çeken tek terim de budur. Sınanmadan kullanılırsa
                # gürültü, sinyal diye okunur.
                "se_sabit": round(float(ses[0]), 3),
                "t_sabit": round(t_sab, 2), "p_sabit": round(p_sab, 4),
                "sabit_anlamli": bool(p_sab < 0.05),
                "egim": round(float(bs[1]), 3), "se_egim": round(float(ses[1]), 3),
                "t": round(ts, 2),
                "p": round(float(2 * (1 - _st.t.cdf(abs(ts), max(len(dp) - 2, 1)))), 4),
                "r": round(float(sr.corr(si)), 3),
                "r2": round(float(1 - (es @ es) / (((sr - sr.mean()) ** 2).sum())), 3),
                "isaret_uyumu": round(float(uyum.mean() * 100), 0),
                "isaret_p": round(float(_st.binomtest(int(uyum.sum()), len(uyum), 0.5).pvalue), 4),
                "isaret_uyumu_25": round(float(u25.mean() * 100), 0) if len(u25) else None,
                "n_25": int(b25.sum()),
                "anlamli": bool(2 * (1 - _st.t.cdf(abs(ts), max(len(dp) - 2, 1))) < 0.05),
            }
    return out


def _fark_ozet(f: pd.Series) -> dict:
    from scipy import stats as _st
    if f.empty:
        return {}
    t_ist, p_ist = (_st.ttest_1samp(f.values, 0.0) if len(f) > 1
                    else (float("nan"),) * 2)
    return {
        "n": int(len(f)),
        "ort": round(float(f.mean()), 2),
        "medyan": round(float(f.median()), 2),
        "std": round(float(f.std(ddof=1)), 2) if len(f) > 1 else None,
        "min": round(float(f.min()), 2),
        "maks": round(float(f.max()), 2),
        "mutlak_ort": round(float(f.abs().mean()), 2),
        "ito_ustte_pay": round(float((f > 0).mean() * 100), 0),
        "min_ay": f.idxmin().strftime("%Y-%m"),
        "maks_ay": f.idxmax().strftime("%Y-%m"),
        "t": round(float(t_ist), 2), "p": round(float(p_ist), 4),
        "anlamli": bool(p_ist < 0.05),
    }


def ito_profil(a: pd.DataFrame, aylar: int = 24,
               dislanan: tuple[int, ...] = DISLANAN_YIL) -> dict:
    """İTO ile TÜFE arasındaki farkın AY AY profili ve "İTO şu geldiyse TÜFE'den
    ne beklenir" sorusunun ölçülmüş cevabı.

    ito_nowcast() regresyonu kurar ve örneklem İÇİ uyumu (R²) verir. Bu modül
    onun cevaplayamadığı altı soruyu ölçer:

    (1) FARKIN KENDİSİ VE ANLAMLILIĞI. Regresyon katsayısı farkın ortalamasını
        gizler; okur "İTO kaç puan yukarıda gelir" diye sorar. Fark ay ay
        yazılır ve sıfırdan farklı olup olmadığı t ile sınanır.
    (2) EĞİM 1 Mİ. Eğim 1'den ayırt edilemiyorsa ilişki "sabit kaydırma"dır ve
        regresyon eğimi kurmaya değmez.
    (3) HANGİ KURAL. Altı aday kural genişleyen pencereyle, örneklem DIŞI
        kıyaslanır. Örneklem içi R² iyimserdir; asıl soru "yarın hangisini
        kullanayım"dır. Sıralamanın pencereye duyarlılığı da ölçülür.
    (4) ANKETTEN İYİ Mİ. Asıl kıyas naif kural değil PİYASA BEKLENTİSİdir.
    (5) SÜRPRİZ SÜRPRİZİ ÖNGÖRÜR MÜ. Tradable soru budur.
    (6) DIŞLAMA HAKLI MI. `dislanan` yıllar kestirimden çıkarılır ama tablodan
        ve grafikten ÇIKARILMAZ; dışlanan dönemin istatistikleri ayrıca
        yazılır ve bütün kestirim İKİ örneklemde birden koşturulur. Bir
        gözlemi atmak veriye müdahaledir; müdahalenin sonucu görünmezse
        okurun elinde yalnız bizim sözümüz kalır.
    """
    if "ito_ist" not in a.columns:
        return {}
    ito_ay, kimlik = _ito_seri(a)
    tam = pd.DataFrame({"tufe": aylik(a["tufe"].dropna()),
                        "ito": ito_ay}).dropna()
    if len(tam) < 18:
        return {"n": int(len(tam)), "not": "örneklem yetersiz"}
    tam["fark"] = tam["ito"] - tam["tufe"]

    disli = tam.index.year.isin(dislanan)
    d = tam[~disli]                      # KESTİRİM örneklemi
    dis = tam[disli]                     # dışlanan dönem — ölçülür, atılmaz
    if len(d) < 18:
        # Dışlama örneklemi kestirilemez hâle getiriyorsa dışlama YAPILMAZ ve
        # bu durum açıkça yazılır. Sessizce tam örnekleme dönmek, sayfada
        # "2023 hariç" yazarken 2023'ü dahil etmek olurdu.
        d, dis, dislanan = tam, tam.iloc[:0], ()

    AY_AD = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs",
             6: "Haziran", 7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim",
             11: "Kasım", 12: "Aralık"}

    # TABLO TAM ÖRNEKLEMDİR; dışlanan satırlar İŞARETLENİR, silinmez.
    tablo = [{"ay": i.strftime("%Y-%m"),
              "ad": f"{AY_AD[i.month]} {i.year}",
              "ito": round(float(r["ito"]), 2),
              "tufe": round(float(r["tufe"]), 2),
              "fark": round(float(r["fark"]), 2),
              "dislandi": bool(i.year in dislanan)}
             for i, r in tam.iterrows()]

    son = d.tail(aylar)
    fark_ozet = _fark_ozet(son["fark"])
    fark_tum = _fark_ozet(d["fark"])

    # Takvim ayı mevsimselliği — KESTİRİM örnekleminden. Ay başına gözlem
    # sayısı yazılır; bu tablodan KURAL çıkarılmaz, kuralın işe yarayıp
    # yaramadığı yarışta örneklem dışı sınanıyor.
    takvim = []
    for ay_no, g in d.groupby(d.index.month):
        takvim.append({"ay": int(ay_no), "ad": AY_AD[int(ay_no)], "n": int(len(g)),
                       "ort_fark": round(float(g["fark"].mean()), 2),
                       "ort_ito": round(float(g["ito"].mean()), 2),
                       "ort_tufe": round(float(g["tufe"].mean()), 2)})
    takvim.sort(key=lambda x: x["ay"])

    # ---- ASGARİ PENCERE. Kural yarışının başlangıç penceresi örneklemin
    # boyuna göre ölçeklenir: sabit 12 yazmak, örneklem büyüdükçe yarışı
    # gereksiz kısa bir tarihçeyle kurmak demekti. Üçte bir, en az 12.
    asgari = max(12, len(d) // 3)

    kestirim = _ito_kestir(d, a, asgari)
    # Dışlamanın etkisi: AYNI kod, AYNI başlangıç penceresi, tam örneklemle.
    # İki sonuç yan yana durunca "2023'ü attık" cümlesi bir iddia değil,
    # ölçülmüş bir farka dönüşüyor.
    #
    # asgari'yi ikisinde de aynı tutmak zorunlu: farklı pencerelerle koşsalardı
    # aradaki fark dışlamanın değil pencerenin eseri olurdu. Yine de kural
    # yarışının MAE'leri BİREBİR kıyaslanamaz — tam örneklemde yarış dışlanan
    # ayları da PUANLIYOR, yani iki MAE farklı ay kümelerinde ölçülüyor. Bu
    # yüzden karşılaştırmaya yalnız kazananın ADI giriyor, MAE'si değil;
    # katsayılar (regresyon, sürpriz) ise aynı tanım üzerinden kıyaslanabilir.
    kestirim_tam = _ito_kestir(tam, a, asgari) if len(dis) else {}

    from scipy import stats as _st
    dislama = {"yillar": list(dislanan), "n": int(len(dis))}
    if len(dis):
        dislama.update({
            "ilk_ay": dis.index[0].strftime("%Y-%m"),
            "son_ay": dis.index[-1].strftime("%Y-%m"),
            "fark": _fark_ozet(dis["fark"]),
            "tufe_min": round(float(dis["tufe"].min()), 2),
            "tufe_maks": round(float(dis["tufe"].max()), 2),
            "tufe_std": round(float(dis["tufe"].std(ddof=1)), 2),
            "ito_std": round(float(dis["ito"].std(ddof=1)), 2),
            "kalan_tufe_std": round(float(d["tufe"].std(ddof=1)), 2),
            "kalan_tufe_min": round(float(d["tufe"].min()), 2),
            "kalan_tufe_maks": round(float(d["tufe"].max()), 2),
        })
        # İKİ DÖNEMİN FARKI GERÇEKTEN AYRIŞIYOR MU? Welch t (eşit varyans
        # varsaymaz — dışlamanın gerekçesi zaten varyansın farklı olması).
        tw, pw = _st.ttest_ind(dis["fark"].values, d["fark"].values,
                               equal_var=False)
        dislama.update({
            "welch_t": round(float(tw), 2), "welch_p": round(float(pw), 4),
            "ort_ayrisiyor": bool(pw < 0.05),
            # Oynaklık oranı: dışlanan dönemin farkı ne kadar daha oynak?
            "std_orani": (round(float(dis["fark"].std(ddof=1)
                                      / d["fark"].std(ddof=1)), 2)
                          if len(dis) > 1 and d["fark"].std(ddof=1) else None),
            "tufe_std_orani": (round(float(dis["tufe"].std(ddof=1)
                                           / d["tufe"].std(ddof=1)), 2)
                               if len(dis) > 1 and d["tufe"].std(ddof=1) else None),
        })

    # ---- BEKLEYEN AY: İTO GELDİ, TÜFE HENÜZ GELMEDİ.
    # Ayın başında sahne hep aynı: İTO yayımlanmış, TÜİK'i bekliyoruz. Bu blok
    # o boşluğu doldurur — üç kuralın beklentisi, öngörü aralığı, varsa anket
    # ve sürpriz kanalı. AYA ÖZEL DEĞİL, GENEL: hangi ay bekliyorsa onu bulur.
    # Belirli bir ayı koda gömmek, bir sonraki ay sessizce yanlış ayı
    # göstermek demekti.
    #
    # TÜFE geldiğinde blok kendini SÖZ DEFTERİNE çevirir: tahmin ile
    # gerçekleşme yan yana durur ve hata ölçülür. Tahmini yayımlayıp sonucu
    # ölçmemek, karnesi olmayan bir tahmin demektir.
    i_ham = ito_ay
    t_ham = aylik(a["tufe"].dropna())
    dolduruldu = set(kimlik.get("dolduruldu") or [])

    bekleyen = {}
    if len(i_ham):
        son_ito_ay = i_ham.index[-1]
        beklemede = son_ito_ay not in t_ham.index
        # Kural parametreleri YALNIZ o aydan ÖNCEKİ veriyle kurulur; bekleyen
        # ay kestirime giremez (zaten TÜFE'si yok) ama gerçekleşme geldikten
        # sonra da geriye dönük "kendi geleceğini görmüş" bir tahmin
        # üretmemeliyiz — karne ancak böyle dürüst olur.
        gec = d[d.index < son_ito_ay]
        if len(gec) >= 12:
            x = float(i_ham.iloc[-1])
            Xg = np.column_stack([np.ones(len(gec)), gec["ito"].values])
            bg, *_ = np.linalg.lstsq(Xg, gec["tufe"].values, rcond=None)
            eg = gec["tufe"].values - Xg @ bg
            s2g = float(eg @ eg) / max(len(gec) - 2, 1)
            Vg = np.linalg.pinv(Xg.T @ Xg)
            x0 = np.array([1.0, x])
            seg = float(np.sqrt(s2g * (1.0 + x0 @ Vg @ x0)))
            tk = float(_st.t.ppf(0.975, max(len(gec) - 2, 1)))
            reg = float(bg[0] + bg[1] * x)
            bekleyen = {
                "ay": son_ito_ay.strftime("%Y-%m"),
                "ad": f"{AY_AD[son_ito_ay.month]} {son_ito_ay.year}",
                "beklemede": bool(beklemede),
                "ito": round(x, 2),
                "ito_kaynak": ("İTO resmî yayımı (EVDS'e henüz düşmedi)"
                               if son_ito_ay.strftime("%Y-%m") in dolduruldu
                               else "EVDS · TP.FG.IST1.23"),
                "ito_elle": bool(son_ito_ay.strftime("%Y-%m") in dolduruldu),
                "n_gecmis": int(len(gec)),
                "naif": round(x, 2),
                "sabit": round(x - float(gec["fark"].mean()), 2),
                "oransal": round(x * float((gec["tufe"] / gec["ito"]).median()), 2),
                "regresyon": round(reg, 2),
                "alt": round(reg - tk * seg, 2),
                "ust": round(reg + tk * seg, 2),
            }
            # Aynı TAKVİM AYININ geçmişi — betimleyicidir, kural değildir
            # (takvim düzeltmesi örneklem dışı yarışta sonuncu çıkıyor).
            ayni = d[d.index.month == son_ito_ay.month]
            bekleyen["ayni_ay"] = [
                {"ay": i.strftime("%Y-%m"), "ito": round(float(r["ito"]), 2),
                 "tufe": round(float(r["tufe"]), 2), "fark": round(float(r["fark"]), 2)}
                for i, r in ayni.iterrows()]
            bekleyen["ayni_ay_n"] = int(len(ayni))
            bekleyen["ayni_ay_ort_fark"] = (round(float(ayni["fark"].mean()), 2)
                                            if len(ayni) else None)
            # TAKVİM AYI KURALI da hesaplanır — ama YANINDA sınamasıyla.
            # "Bu ay tipik olarak şöyle gelir" cümlesi ancak o ayın farkı
            # diğer aylardan AYRIŞIYORSA kurulabilir; ayrışmıyorsa elimizdeki
            # şey iki üç gözlemin ortalamasıdır ve tahmin değildir.
            if len(ayni):
                bekleyen["takvimli"] = round(x - float(ayni["fark"].mean()), 2)
                digeri = d[d.index.month != son_ito_ay.month]
                if len(ayni) > 1 and len(digeri) > 1:
                    tw, pw = _st.ttest_ind(ayni["fark"].values, digeri["fark"].values,
                                           equal_var=False)
                    bekleyen["ayni_ay_t"] = round(float(tw), 2)
                    bekleyen["ayni_ay_p"] = round(float(pw), 3)
                    bekleyen["ayni_ay_ayrisiyor"] = bool(pw < 0.05)
                bekleyen["ayni_ay_genel_ayrim"] = round(
                    float(d["fark"].mean() - ayni["fark"].mean()), 2)
            if "pka_ay_cari" in a.columns:
                pk = a["pka_ay_cari"].dropna()
                if son_ito_ay in pk.index:
                    bek = float(pk.loc[son_ito_ay])
                    sp_ = kestirim.get("surpriz") or {}
                    bekleyen["anket"] = round(bek, 2)
                    bekleyen["ito_sapma"] = round(x - bek, 2)
                    if sp_.get("egim") is not None:
                        bs_ = sp_["sabit"] + sp_["egim"] * (x - bek)
                        bekleyen["beklenen_surpriz"] = round(float(bs_), 2)
                        bekleyen["surprizden_tufe"] = round(float(bek + bs_), 2)
            # ---- TAHMİN BULUTU: nokta tahmin YETMİYOR.
            # "İTO 1,66 geldi, TÜFE 1,4 olur" cümlesi okura yanlış bir kesinlik
            # veriyor ve en çok merak edilen soruyu hiç cevaplamıyor: TÜFE
            # İTO'nun ÜSTÜNDE gelebilir mi? Gelebiliyor — örneklemde dört ayda
            # bir oluyor. Bulut, o olasılığı sayıyla söyler.
            #
            # ÜÇ KURULUŞ, ÇÜNKÜ TEK KURULUŞ MODELİNİ GİZLER:
            #  A parametrik  — regresyon merkezi + t dağılımı. SİMETRİ VARSAYAR.
            #  B ampirik artık — aynı merkez, ama dağılım geçmiş artıklardan.
            #                    Simetri varsaymaz; A ile farkı, varsayımın
            #                    fiyatını gösterir.
            #  C tarihsel fark — sabit kaydırma merkezi + geçmiş farklar.
            #                    En ham hâli: "geçmişteki her ay tekrarlasa".
            # Üçü de basılır. Ayrışıyorlarsa okur bunu görmeli.
            reg_art = gec["tufe"].values - Xg @ bg
            xi = x                       # bekleyen ayın İTO okuması
            merkez_sabit = xi - float(gec["fark"].mean())
            YUZDE = (5, 10, 25, 50, 75, 90, 95)
            bulutlar = {
                "parametrik": np.array([reg + _st.t.ppf(q / 100, max(len(gec) - 2, 1)) * seg
                                        for q in YUZDE]),
                "ampirik": np.percentile(reg + reg_art, YUZDE),
                "tarihsel": np.percentile(xi - gec["fark"].values, YUZDE),
            }
            bulut = {
                "n": int(len(gec)), "ito": round(xi, 2),
                "merkez_reg": round(reg, 2), "merkez_sabit": round(merkez_sabit, 2),
                "yuzdelikler": list(YUZDE),
                "carpiklik": round(float(_st.skew(reg_art)), 2),
                "shapiro_p": round(float(_st.shapiro(reg_art).pvalue), 3),
            }
            for ad, v in bulutlar.items():
                bulut[f"y_{ad}"] = [round(float(x), 2) for x in v]
            # TÜFE İTO'NUN ÜSTÜNDE GELİR Mİ? Üç kuruluşun da cevabı yazılır.
            ust_amp = (reg + reg_art) > xi
            ust_tar = (xi - gec["fark"].values) > xi          # ≡ fark < 0
            bulut["p_ustunde"] = {
                "parametrik": round(float((1 - _st.t.cdf((xi - reg) / seg,
                                                         max(len(gec) - 2, 1))) * 100), 0),
                "ampirik": round(float(ust_amp.mean() * 100), 0),
                "tarihsel": round(float(ust_tar.mean() * 100), 0),
            }
            bulut["ustunde_n"] = int(ust_tar.sum())
            bulut["ustunde_aylar"] = [
                {"ay": t.strftime("%Y-%m"), "ito": round(float(r["ito"]), 2),
                 "tufe": round(float(r["tufe"]), 2), "fark": round(float(r["fark"]), 2)}
                for t, r in gec[gec["fark"] < 0].iterrows()]
            # Eşik olasılıkları — ampirik bulut (simetri varsaymayan)
            amp = reg + reg_art
            bulut["esik"] = [
                {"esik": e, "yon": yon,
                 "p": round(float(((amp > e) if yon == ">" else (amp < e)).mean() * 100), 0)}
                for e, yon in ((2.5, ">"), (2.0, ">"), (1.5, ">"), (1.0, "<"), (0.5, "<"))]
            # BULUTUN KENDİ İÇ TUTARLILIĞI ÖLÇÜLÜR. Yüzdelikler monoton
            # olmalı ve "tarihsel" kuruluşun P(TÜFE>İTO) değeri, tanım gereği,
            # eksi farklı ay payına EŞİT olmalı (xi − fark > xi ⟺ fark < 0).
            # İkisi de bir gün sessizce bozulabilir; sessiz bozulma en pahalısı,
            # çünkü sayfa yine yeşil koşar ve okur yanlış olasılığı okur.
            for ad, v in bulutlar.items():
                if any(v[i] > v[i + 1] + 1e-9 for i in range(len(v) - 1)):
                    uyar(f"BULUT: {ad} kuruluşunun yüzdelikleri monoton değil "
                         f"({[round(float(z), 2) for z in v]}) — sayfadaki "
                         f"olasılıklar güvenilmez.")
            _bekl = round(float((gec["fark"] < 0).mean() * 100), 0)
            if abs(bulut["p_ustunde"]["tarihsel"] - _bekl) > 1e-9:
                uyar(f"BULUT: tarihsel P(TÜFE>İTO) = "
                     f"{bulut['p_ustunde']['tarihsel']}%, eksi farklı ay payı ise "
                     f"{_bekl}% — ikisi tanım gereği aynı olmalıydı.")
            bekleyen["bulut"] = bulut

            if not beklemede:
                ger = float(t_ham.loc[son_ito_ay])
                bekleyen["gercek"] = round(ger, 2)
                for k in ("naif", "sabit", "oransal", "regresyon"):
                    bekleyen[f"hata_{k}"] = round(bekleyen[k] - ger, 2)
                bekleyen["aralik_tuttu"] = bool(bekleyen["alt"] <= ger <= bekleyen["ust"])

    yil = pd.DataFrame({"tufe": yillik(a["tufe"].dropna()),
                        "ito": yillik(a["ito_ist"].dropna())}).dropna()
    yillik_tablo = [{"ay": i.strftime("%Y-%m"),
                     "ito": round(float(r["ito"]), 2),
                     "tufe": round(float(r["tufe"]), 2),
                     "fark": round(float(r["ito"] - r["tufe"]), 2)}
                    for i, r in yil.iterrows()]
    yfark = yil["ito"] - yil["tufe"]
    yillik_ozet = {"n": int(len(yfark)), "ort": round(float(yfark.mean()), 2),
                   "son": round(float(yfark.iloc[-1]), 2),
                   "maks": round(float(yfark.max()), 2),
                   "maks_ay": yfark.idxmax().strftime("%Y-%m"),
                   "min": round(float(yfark.min()), 2),
                   "min_ay": yfark.idxmin().strftime("%Y-%m"),
                   "son_ito": round(float(yil["ito"].iloc[-1]), 2),
                   "son_tufe": round(float(yil["tufe"].iloc[-1]), 2)}

    cikti = {"pencere_ay": int(len(son)), "tablo": tablo,
             "fark": fark_ozet, "fark_tum": fark_tum, "takvim": takvim,
             "dislama": dislama, "bekleyen": bekleyen,
             "kimlik": kimlik,
             "yillik": yillik_tablo, "yillik_ozet": yillik_ozet,
             "tam_ilk_ay": tam.index[0].strftime("%Y-%m"),
             "tam_son_ay": tam.index[-1].strftime("%Y-%m"),
             "n_tam": int(len(tam)),
             "ilk_ay": d.index[0].strftime("%Y-%m"),
             "son_ay": d.index[-1].strftime("%Y-%m"),
             "n_toplam": int(len(d))}
    cikti.update(kestirim)
    if kestirim_tam:
        cikti["karsilastirma"] = {
            "n_dahil": int(len(tam)), "n_haric": int(len(d)),
            "dahil": {
                "egim": kestirim_tam["regresyon"]["egim"],
                "se_egim": kestirim_tam["regresyon"]["se_egim"],
                "sabit": kestirim_tam["regresyon"]["sabit"],
                "r": kestirim_tam["regresyon"]["r"],
                "r2": kestirim_tam["regresyon"]["r2"],
                "se_artik": kestirim_tam["regresyon"]["se_artik"],
                "p_egim_bir": kestirim_tam["regresyon"]["p_egim_bir"],
                "kazanan": (kestirim_tam.get("kural") or {}).get("kazanan"),
                "s_egim": (kestirim_tam.get("surpriz") or {}).get("egim"),
                "s_t": (kestirim_tam.get("surpriz") or {}).get("t"),
                "s_r2": (kestirim_tam.get("surpriz") or {}).get("r2"),
            },
            "haric": {
                "egim": kestirim["regresyon"]["egim"],
                "se_egim": kestirim["regresyon"]["se_egim"],
                "sabit": kestirim["regresyon"]["sabit"],
                "r": kestirim["regresyon"]["r"],
                "r2": kestirim["regresyon"]["r2"],
                "se_artik": kestirim["regresyon"]["se_artik"],
                "p_egim_bir": kestirim["regresyon"]["p_egim_bir"],
                "kazanan": (kestirim.get("kural") or {}).get("kazanan"),
                "s_egim": (kestirim.get("surpriz") or {}).get("egim"),
                "s_t": (kestirim.get("surpriz") or {}).get("t"),
                "s_r2": (kestirim.get("surpriz") or {}).get("r2"),
            },
        }
    return cikti


# ===========================================================================
# 11. Ana akış
# ===========================================================================
# Momentum tablosuna giren seriler. Enerji ve işlenmemiş gıda BİLİNÇLİ olarak
# "merkezî" sayılmaz — 3a SAAR'ları ±%25 salınıyor; grafikte oynak etiketiyle
# ayrı gösterilir.
MERKEZI = ["tufe", "cekirdek_b", "cekirdek_c", "hizmet", "temel_mal"]
TABLO = MERKEZI + ["kira", "enerji", "gida", "islenmemis_gida", "islenmis_gida",
                   "alkol_tutun_altin", "yonetilen_haric", "yi_ufe"]
OYNAK = {"enerji", "islenmemis_gida"}
SERI_AD = {
    "tufe": "TÜFE", "cekirdek_b": "Çekirdek B", "cekirdek_c": "Çekirdek C",
    "hizmet": "Hizmet", "temel_mal": "Temel mallar", "kira": "Kira",
    "enerji": "Enerji", "gida": "Gıda", "islenmemis_gida": "İşlenmemiş gıda",
    "islenmis_gida": "İşlenmiş gıda", "alkol_tutun_altin": "Alkol, tütün, altın",
    "yonetilen_haric": "Yönetilen fiyatlar hariç", "yi_ufe": "Yİ-ÜFE",
    "ykke": "YKKE (yeni kiracı kirası)",
}


def kos() -> dict:
    print("Enflasyon — hesap katmanı")
    a = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    g = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    durum = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    for u in durum.get("uyarilar", []):
        UYARI.append(u)
    s_ay = pd.Timestamp(durum["son_ay"])
    print(f"  son ay: {ad_uzun(s_ay)}")

    # ---------------------------------------------------------------- DOĞRULUK ŞARTI
    # Hesapladığımız 12 aylık, EVDS'in kendi y/y formül çıktısıyla (formulas=3)
    # 0,05 puan içinde tutmalı. Tutmazsa hat DURUR.
    dogrulama = capraz_dogrula(a, s_ay)

    # ---------------------------------------------------------------- arındırma
    print("  mevsimsellikten arındırma (log-STL + hareketli tatil)")
    sa: dict[str, pd.Series] = {}
    sa_tani: dict[str, dict] = {}
    for ad in TABLO:
        if ad not in a.columns or a[ad].dropna().empty:
            uyar(f"SERİ YOK: {ad} — momentum tablosundan düşürüldü.")
            continue
        s, t = arindir(a[ad])
        sa[ad], sa_tani[ad] = s, t
        if not t.get("mevsimsel", True):
            print(f"    {SERI_AD.get(ad, ad)}: mevsimsellik anlamsız "
                  f"(p={t.get('mevsim_p')}) — arındırılmadı")
    SA = pd.DataFrame(sa)
    SA.index.name = "tarih"
    SA.to_csv(VERI / "sa.csv")

    # ---------------------------------------------------------------- revizyon izi
    # Arındırma GEÇMİŞİ DEĞİŞTİREN bir işlemdir: yeni ay eklendiğinde filtre
    # yeniden koşar, önceki ayların SA aylık değişimleri revize olur. Bu bizim
    # ürettiğimiz bir revizyondur, TÜİK'in değil.
    rev = kosular_arasi_izi(SA)
    # GERÇEK uç-nokta revizyonu: seri k=1..6 ay kesilip yeniden arındırılır.
    print(f"  uç-nokta revizyon testi (vintage, k=1..{VINTAGE_K})")
    vintage = vintage_revizyon(a, SA, TABLO)
    if vintage.get("en_oynak"):
        e = vintage["en_oynak"]
        print(f"    en oynak: {e['ad']} — SA m/m maks {e['mm_maks_pp']} pp · "
              f"3a SAAR maks {e['saar3_maks_pp']} pp")

    # ---------------------------------------------------------------- momentum
    print("  momentum ölçüleri (3a/6a SAAR, 12a, ECB 3a/3a)")
    satir = []
    for ad in TABLO:
        if ad not in SA.columns:
            continue
        ham, s = a[ad].dropna(), SA[ad].dropna()
        satir.append(pd.DataFrame({
            "seri": ad,
            "aylik_ham": aylik(ham), "aylik_sa": aylik(s),
            "saar3_ham": saar(ham, 3), "saar3_sa": saar(s, 3),
            "saar6_ham": saar(ham, 6), "saar6_sa": saar(s, 6),
            "yillik": yillik(ham),
            "ecb3": ecb_momentum(s),
            "saar3_aritmetik": saar_aritmetik(s, 3),
            "saar3_basit": saar_basit(s, 3),
            "saar6_aritmetik": saar_aritmetik(s, 6),
            "saar6_basit": saar_basit(s, 6),
        }))
    M = pd.concat(satir)
    M.index.name = "tarih"
    M.to_csv(VERI / "metrik.csv")

    # ---------------------------------------------------------------- ağırlıklar
    print("  ağırlık tahmini (hiyerarşik kısıtlı EKK)")
    yillar = sorted({t.year for t in a.index if t.year >= 2006 and t <= s_ay})
    katki_adlar = [f"oktg{k[-2:]}" for _, k in
                   [(v[0], v[1]) for v in veri.KATKI_GRUP.values()]]
    katki_adlar = [f"oktg{v[1][-2:]}" for v in veri.KATKI_GRUP.values()]
    w_katki = agirlik_tahmini(a, "tufe", katki_adlar, yillar)
    ana_adlar = [f"ana_{k}" for k in veri.ANA_GRUP_AD]
    w_ana = agirlik_tahmini(a, "tufe", ana_adlar, yillar)
    agac = pd.read_csv(VERI / "agac.csv") if (VERI / "agac.csv").exists() else pd.DataFrame()
    w_alt, alt_adlar = alt_agirliklar(a, agac, w_ana, yillar, s_ay)

    son_yil = str(s_ay.year)
    a_pp = w_katki.get(son_yil, {}).get("artik_pp", 99)
    print(f"    katkı grupları {son_yil}: artık {a_pp} pp "
          f"({w_katki.get(son_yil, {}).get('kip')}, "
          f"{w_katki.get(son_yil, {}).get('n_ay')} ay)")
    if a_pp > AGIRLIK_ARTIK_ESIK_PP:
        # Sayfada "üretilmez" yazıyordu ama kodda yalnız uyarı vardı: yayımlanan
        # davranışla fiilî davranış ayrışmıştı. Artık HAT DURUR — ağırlık kimliği
        # tutmuyorsa katkı ayrıştırması yanlıştır ve sessizce yayımlanamaz.
        uyar(f"AĞIRLIK: katkı gruplarının kimlik artığı {a_pp} pp "
             f"(eşik {AGIRLIK_ARTIK_ESIK_PP}).")
        with open(PROJE_UYARI, "w", encoding="utf-8") as f:
            json.dump({"tarih": s_ay.strftime("%Y-%m-%d"),
                       "kosum": dt.date.today().isoformat(),
                       "uyarilar": UYARI, "dogrulama": dogrulama},
                      f, ensure_ascii=False, indent=1)
        raise SystemExit(
            f"DUR: katkı gruplarının ağırlık kimliği {a_pp} puan artık veriyor "
            f"(eşik {AGIRLIK_ARTIK_ESIK_PP}). Katkı ayrıştırması güvenilmez; "
            "sessizce eski/yanlış ağırlıkla yayımlamak yerine hat DURDURULDU.")
    (VERI / "agirlik.json").write_text(json.dumps(
        {"katki": w_katki, "ana_grup": w_ana, "alt": w_alt,
         "yontem": "zincir-Laspeyres kimliğinden kısıtlı EKK (EVDS ağırlık yayımlamıyor)",
         "alt_adlar": alt_adlar},
        ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------------------------------------------------------------- katkı
    print("  katkı ayrıştırma (aylık tam + yıllık bileşiklenmiş)")
    K = katki_hesapla(a, katki_adlar, w_katki, pd.Timestamp("2006-01-01"))
    if not K.empty:
        K.to_csv(VERI / "katki.csv")
        art = float(K["artik"].abs().tail(24).max()) * 100
        yart = float(K["yil_artik"].abs().tail(24).max()) * 100
        art_tum = float(K["artik"].abs().max()) * 100
        yart_tum = float(K["yil_artik"].abs().max()) * 100
        print(f"    aylık artık (son 24 ay, maks): {art:.4f} pp · "
              f"yıllık artık: {yart:.4f} pp · tüm tarihçe: {art_tum:.4f} / "
              f"{yart_tum:.4f} pp")
        if yart_tum > 0.05:
            uyar(f"KATKI: yıllık katkı toplamı tüm tarihçede manşetten en çok "
                 f"{yart_tum:.3f} pp sapıyor (eşik 0,05). Ağırlık tahmini bazı "
                 "yıllarda tutmamış olabilir.")
        if art > 0.02:
            uyar(f"KATKI: aylık katkı toplamı manşetten {art:.3f} pp sapıyor "
                 "(Σ C_it = π_t birebir sağlanmalıydı).")

    # ---------------------------------------------------------------- dağılım
    print("  kırpılmış ortalama · medyan · difüzyon")
    ad_map = ({f"g3_{r['kuyruk']}": r["ad"] for _, r in agac.iterrows()
               if str(r.get("hane")) == "3"} if not agac.empty else {})
    D, kesit_tani = dagilim_hesapla(a, alt_adlar, w_alt, s_ay, ad_map)
    if not D.empty:
        D.to_csv(VERI / "dagilim.csv")
    # Kesitin 45 alt kalem serisi ÜRETİLMİŞ DOSYAYA yazılır: dağılım ölçüleri
    # yalnız önbellek dururken değil, tek bir CSV'den denetlenebilsin.
    if alt_adlar:
        a[alt_adlar].to_csv(VERI / "alt_kalem.csv")
    if kesit_tani.get("arindirilmayan_n"):
        print(f"    kesit: {kesit_tani['arindirilmayan_n']}/{kesit_tani['n']} grup "
              f"arındırılmadan geçti (ağırlıkça "
              f"%{kesit_tani.get('arindirilmayan_agirlik', 0):.1f})")

    # ---------------------------------------------------------------- baz etkisi
    B = baz_patikasi(a["tufe"].dropna(), SA["tufe"].dropna())
    B.to_csv(VERI / "baz_senaryo.csv")

    # ---------------------------------------------------------------- reel faiz
    print("  reel faiz (ex-post · ex-ante · ana eğilim)")
    R = reel_faiz_serisi(a, g, SA)
    R.to_csv(VERI / "reel_faiz.csv")

    # ---------------------------------------------------------------- beklenti
    bek = beklenti_isabeti(a)
    (VERI / "beklenti.json").write_text(
        json.dumps(bek, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------------------------------------------------------------- hizmet ataleti
    atalet = atalet_olc(SA)

    ito = ito_nowcast(a)
    profil = ito_profil(a)
    if profil:
        (VERI / "ito_profil.json").write_text(
            json.dumps(profil, ensure_ascii=False, indent=1), encoding="utf-8")
    # ÜGE AYRI DOSYA: İTO'nun ikinci başlık endeksi ayrı bir ölçüm zinciri ve
    # kendi kimlik doğrulaması var. Aynı dosyaya gömülseydi, biri üretilemeyince
    # diğeri de sayfadan düşerdi — iki endeksin kaderi birbirine bağlı değil.
    uge = uge_profil(a)
    if uge:
        (VERI / "uge_profil.json").write_text(
            json.dumps(uge, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---------------------------------------------------------------- özet
    ozet = ozet_topla(a, g, SA, M, K, D, B, R, bek, atalet, ito, w_katki, w_ana,
                      sa_tani, rev, dogrulama, s_ay, vintage, kesit_tani)
    (VERI / "metrik_ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    (VERI / "sa_tani.json").write_text(
        json.dumps({"yontem": SA_YONTEM, "pencere_sonu": s_ay.strftime("%Y-%m-%d"),
                    "seriler": sa_tani,
                    "alt_kalemler": kesit_tani,
                    "kosular_arasi": rev,
                    "vintage": vintage},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    with open(PROJE_UYARI, "w", encoding="utf-8") as f:
        json.dump({"tarih": s_ay.strftime("%Y-%m-%d"),
                   "kosum": dt.date.today().isoformat(),
                   "uyarilar": UYARI,
                   "dogrulama": dogrulama}, f, ensure_ascii=False, indent=1)

    yaz_tablo(M, s_ay)
    print(f"\n  yazıldı: metrik.csv · sa.csv · katki.csv · dagilim.csv · "
          f"agirlik.json · baz_senaryo.csv · reel_faiz.csv · beklenti.json")
    if UYARI:
        print(f"\n[{len(UYARI)} uyarı — uyarilar.json]")
    return ozet


PROJE_UYARI = veri.PROJE / "uyarilar.json"


# ---------------------------------------------------------------------------
def capraz_dogrula(a: pd.DataFrame, s_ay: pd.Timestamp) -> dict:
    """FORMÜL VE KOLON HİZALAMASI denetimi — hattı DURDURUR.

    Bizim endeks seviyelerinden hesapladığımız 12 aylık değişim, EVDS'in kendi
    y/y formül çıktısıyla (formulas=3) 0,05 puan içinde tutmalı; a/a (formulas=1)
    için eşik 0,01 puan (uyarı).

    NE ÖLÇMEZ: bu bir TAZELİK denetimi DEĞİLDİR. EVDS'in formül çıktısı bizim
    indirdiğimiz serinin sunucu tarafındaki dönüşümüdür; seri bayatlarsa iki
    taraf birlikte bayatlar ve KESİŞEN tarihlerde her zaman birebir tutar
    (endeks 0/3/6 ay bayatlatılarak sınandı: üçünde de maks fark 0,000000 pp).
    Yakaladığı hata sınıfı: yanlış kolon eşleşmesi, kayan seri kaydı, baz
    değişimi, yıllıklandırma formülünün bozulması.

    Tazelik denetimi ayrı ve aile bazlıdır (veri.py:tazelik_denetimi).
    Buradaki TEK tazelik katkısı: pencere KOŞUM GÜNÜNDEN türetilir ve EVDS'in
    döndürdüğü son ay bizim son ayımızdan ileriyse GÖRÜNÜR uyarı düşer — yani
    "EVDS yeni ay yayımlamış, biz almamışız" hâli yakalanır.
    """
    sonuc = {"esik_yillik_pp": 0.05, "esik_aylik_pp": 0.01,
             "not": "formül/kolon hizalaması denetimi — tazelik denetimi değildir"}
    try:
        # Pencere s_ay'dan DEĞİL koşum gününden türetilir: s_ay bayat veriyle
        # birlikte geriye kayar ve denetim kendi penceresini de bayatlatırdı.
        bugun = pd.Timestamp(dt.date.today())
        bas = (bugun - pd.DateOffset(months=36)).strftime("01-%m-%Y")
        son = (bugun + pd.DateOffset(months=2)).strftime("01-%m-%Y")
        for etiket, formul, kolonsonek, hesap in (
                ("yillik", 3, "-3", yillik(a["tufe"].dropna())),
                ("aylik", 1, "-1", aylik(a["tufe"].dropna()))):
            url = (f"{veri.BASE}/series=TP.TUKFIY2025.GENEL&startDate={bas}"
                   f"&endDate={son}&type=json&formulas={formul}")
            items = veri._cek(url).get("items", [])
            df = pd.DataFrame(items)
            kol = "TP_TUKFIY2025_GENEL" + kolonsonek
            df["t"] = pd.to_datetime(df["Tarih"], format="%Y-%m")
            e = pd.to_numeric(df.set_index("t")[kol], errors="coerce").dropna()
            ort = pd.DataFrame({"biz": hesap, "evds": e}).dropna()
            fark = (ort["biz"] - ort["evds"]).abs()
            sonuc[etiket] = {
                "n": int(len(ort)),
                "maks_fark_pp": round(float(fark.max()), 6),
                "son_ay_biz": round(float(ort["biz"].iloc[-1]), 4),
                "son_ay_evds": round(float(ort["evds"].iloc[-1]), 4),
                "evds_son_ay": e.index[-1].strftime("%Y-%m"),
            }
            # TAZELİK KATKISI: EVDS bizden ileri bir ay döndürdüyse elimizdeki
            # seri bayattır — kesişimde tutuyor olması bunu gizler.
            if e.index[-1] > s_ay:
                uyar(f"BAYAT VERİ: EVDS {etiket} formül çıktısı "
                     f"{e.index[-1].strftime('%m.%Y')}'e kadar geliyor, bizim son "
                     f"ayımız {s_ay.strftime('%m.%Y')}. Yeni ay yayımlanmış ama "
                     "elimizdeki seriye girmemiş (önbellek ya da çekim hatası).")
    except Exception as ex:
        uyar(f"ÇAPRAZ DOĞRULAMA YAPILAMADI: EVDS formül çıktısı alınamadı ({ex}). "
             "12 aylık hesabımız bu koşuda bağımsız olarak doğrulanmadı.")
        sonuc["hata"] = str(ex)
        return sonuc

    y = sonuc.get("yillik", {}).get("maks_fark_pp")
    m = sonuc.get("aylik", {}).get("maks_fark_pp")
    print(f"  çapraz doğrulama · 12 aylık maks fark {y} pp (eşik 0,05) · "
          f"aylık maks fark {m} pp (eşik 0,01)")
    if y is not None and y > 0.05:
        raise SystemExit(
            f"DUR: hesapladığımız 12 aylık enflasyon EVDS'in kendi y/y serisinden "
            f"{y} puan sapıyor (eşik 0,05). Olası nedenler: endeks kolonu yanlış "
            f"eşleşti, seri kaydı kayıyor ya da EVDS baz değiştirdi. "
            f"Hat DURDURULDU — bayat/yanlış sayı yayımlanmasın.")
    if m is not None and m > 0.01:
        uyar(f"ÇAPRAZ DOĞRULAMA: aylık değişimimiz EVDS formül çıktısından "
             f"{m} pp sapıyor (eşik 0,01). Yuvarlama dışı bir fark olabilir.")
    return sonuc


def kosular_arasi_izi(SA: pd.DataFrame) -> dict:
    """KOŞULAR ARASI tanı: bir önceki koşunun SA serisiyle kıyas.

    DİKKAT — bu bir revizyon ÖLÇÜSÜ DEĞİLDİR. Aynı veriyle iki kez koşulduğunda
    sa.csv ile sa_onceki.csv bayt-bayt aynı çıkar ve bu ölçü YAPISAL OLARAK 0
    verir; sayfada "revizyon en fazla 0,00 puan" diye okunursa SAHTE GÜVENCE
    üretir. Bu yüzden içerik gerçekten değişmediyse `var=False` işaretlenir ve
    ozet.json'a hiçbir sayı YAZILMAZ (ozet_uret.py `var` bayrağına bakar).

    Gerçek uç-nokta revizyonu `vintage_revizyon()` ile ölçülür: seri k ay
    kesilip yeniden arındırılır, o ay "son ay" iken hesaplanan değerle bugünkü
    değer karşılaştırılır. Sayfada güvence olarak O sayı kullanılır.
    """
    onceki_yol = VERI / "sa_onceki.csv"
    out: dict = {"var": False, "not": "önceki koşu yok"}
    if onceki_yol.exists():
        try:
            eski = pd.read_csv(onceki_yol, index_col=0, parse_dates=True)
            ortak = [c for c in SA.columns if c in eski.columns]
            # İÇERİK gerçekten değişti mi? Kıyas BAYT düzeyinde: kayan nokta
            # artığı (1e-13 mertebesi) "değişti" sayılırsa ölçü yine 0,000 çıkar
            # ve sahte güvence geri gelir.
            ayni = onceki_yol.read_text(encoding="utf-8") == SA.to_csv()
            yeni_m = aylik(SA["tufe"].dropna()) if "tufe" in ortak else None
            eski_m = aylik(eski["tufe"].dropna()) if "tufe" in ortak else None
            if ayni:
                out = {"var": False,
                       # CÜMLE OKURA GİDİYOR: sayfada <Deger> ile basılıyor,
                       # dolayısıyla dosya adı taşıyamaz.
                       "not": "önceki ölçüm aynı veriyle yapılmış — iki ölçüm "
                              "arasındaki revizyon bu kez ölçülemedi",
                       "onceki_kosum": dt.datetime.fromtimestamp(
                           onceki_yol.stat().st_mtime).strftime("%Y-%m-%d")}
            elif yeni_m is not None and eski_m is not None:
                d = pd.DataFrame({"y": yeni_m, "e": eski_m}).dropna().tail(12)
                if len(d):
                    fark = (d["y"] - d["e"]).abs()
                    out = {"var": True, "n": int(len(d)),
                           "maks_pp": round(float(fark.max()), 3),
                           "ort_pp": round(float(fark.mean()), 3),
                           "onceki_kosum": dt.datetime.fromtimestamp(
                               onceki_yol.stat().st_mtime).strftime("%Y-%m-%d")}
                    if out["maks_pp"] > 0.30:
                        uyar(f"SA REVİZYON: önceki koşuya göre son 12 ayın "
                             f"arındırılmış aylık değişimi en çok {out['maks_pp']} pp "
                             "oynadı. Serinin ucu henüz oturmamış olabilir.")
        except Exception as ex:
            print(f"    (koşular arası iz okunamadı: {ex})")
    SA.to_csv(onceki_yol)
    return out


# Uç-nokta revizyonunun ölçüldüğü ufuk: seri kaç aya kadar geriden kesilip
# yeniden arındırılacak. 6 ay, STL'in tek taraflıya döndüğü bölgeyi kapsar.
VINTAGE_K = 6
VINTAGE_TUFE_ESIK_PP = 0.30      # manşet SA m/m revizyonu bu eşiği aşarsa uyarı


def vintage_revizyon(a: pd.DataFrame, SA: pd.DataFrame, seriler: list[str],
                     k_maks: int = VINTAGE_K) -> dict:
    """GERÇEK uç-nokta revizyon testi (koşular arası kıyas DEĞİL).

    Her seri için k = 1..k_maks ay kesilir, `arindir()` YENİDEN koşulur ve o ay
    "son ay" iken hesaplanan SA m/m ile 3 aylık SAAR, bugünkü (tam örneklemli)
    değerleriyle karşılaştırılır. Yani soru şudur: *o ayın arındırılmış temposunu
    o gün yayımlamış olsaydık, bugün ne kadar sapmış olurdu?*

    Bu ölçü veriye bağlı DEĞİLDİR — veri hiç değişmese bile sıfır çıkmaz, çünkü
    iki taraflı filtre serinin ucunda tek taraflıya döner. Sayfadaki "revizyon
    riski" güvencesi buradan beslenir.
    """
    out: dict = {"k_maks": int(k_maks), "seriler": {}}
    for ad in seriler:
        if ad not in a.columns or ad not in SA.columns:
            continue
        ham = a[ad].dropna()
        bugun = SA[ad].dropna()
        mm_b, s3_b = aylik(bugun), saar(bugun, 3)
        mm_f, s3_f = [], []
        for k in range(1, k_maks + 1):
            kesik = ham.iloc[:-k]
            if len(kesik) < 60:
                continue
            try:
                sa_k, _ = arindir(kesik)
            except Exception as ex:
                print(f"    (vintage {ad} k={k} koşulamadı: {ex})")
                continue
            t = sa_k.index[-1]
            mm_k = aylik(sa_k)
            s3_k = saar(sa_k, 3)
            if t in mm_b.index and pd.notna(mm_k.get(t)) and pd.notna(mm_b.get(t)):
                mm_f.append(abs(float(mm_k.loc[t]) - float(mm_b.loc[t])))
            if t in s3_b.index and pd.notna(s3_k.get(t)) and pd.notna(s3_b.get(t)):
                s3_f.append(abs(float(s3_k.loc[t]) - float(s3_b.loc[t])))
        if not mm_f:
            continue
        out["seriler"][ad] = {
            "n": len(mm_f),
            "mm_maks_pp": round(max(mm_f), 3),
            "mm_ort_pp": round(sum(mm_f) / len(mm_f), 3),
            "saar3_maks_pp": round(max(s3_f), 3) if s3_f else None,
            "saar3_ort_pp": round(sum(s3_f) / len(s3_f), 3) if s3_f else None,
        }
    tv = out["seriler"].get("tufe", {})
    if tv.get("mm_maks_pp", 0) > VINTAGE_TUFE_ESIK_PP:
        uyar(f"SA REVİZYON (vintage): manşet TÜFE'nin arındırılmış aylık değişimi "
             f"uç-nokta testinde en çok {tv['mm_maks_pp']} pp revize oluyor "
             f"(eşik {VINTAGE_TUFE_ESIK_PP}). Son ayların momentumu oturmamış.")
    # En çok revize olan seri — sayfada ADIYLA anılır, tek bir manşet sayısıyla
    # geçilmez (hizmetin momentumu manşetinkinden kat kat oynak revize oluyor).
    aday = {k: v for k, v in out["seriler"].items() if k not in OYNAK}
    if aday:
        en = max(aday.items(), key=lambda kv: kv[1].get("saar3_maks_pp") or 0)
        out["en_oynak"] = {"seri": en[0], "ad": SERI_AD.get(en[0], en[0]),
                           **{k: v for k, v in en[1].items()}}
    # Oynak etiketli seriler ayrı raporlanır: revizyonları merkezî ölçülerle
    # aynı cümlede anılırsa sayfanın güvencesi haksız yere kötü görünür.
    oyn = {k: v for k, v in out["seriler"].items() if k in OYNAK}
    if oyn:
        en2 = max(oyn.items(), key=lambda kv: kv[1].get("saar3_maks_pp") or 0)
        out["en_oynak_etiketli"] = {"seri": en2[0], "ad": SERI_AD.get(en2[0], en2[0]),
                                    **{k: v for k, v in en2[1].items()}}
    return out


def alt_agirliklar(a: pd.DataFrame, agac: pd.DataFrame, w_ana: dict,
                   yillar: list[int], s_ay: pd.Timestamp) -> tuple[dict, list[str]]:
    """Kırpılmış ortalama / medyan / difüzyon için geniş kesit.

    Kesit olarak ÜÇ HANELİ (SEVİYE 2, 45 grup) düzeyi seçildi: Cleveland Fed'in
    medyan TÜFE'si de bu mertebede bir kesit kullanır; 4–5 haneli düzeyde ise
    TÜİK'in kendi duyurusu 2026 sınıflama değişiminde "bazı alt endekslerde
    farklılık görülebilir" diyor, geriye dönük kıyas güvenli değil.

    Paylar hiyerarşik çözülür: önce 13 ana grubun TÜFE içindeki payı, sonra her
    ana grubun çocuklarının kendi içindeki payı; çarpımları toplam ağırlıktır.
    Ana grup düğümü bir tam yılda TAM BELİRLENMİŞTİR (12 denklem + Σw=1 kısıtı,
    13 bilinmeyen) — artığı sıfır çıkar, bu bir doğrulama DEĞİLDİR; alt
    düğümler aşırı belirlenmiştir ve artıkları anlamlıdır.
    """
    if agac.empty:
        return {}, []
    ucluler = agac[(agac["hane"] == 3) & (agac["kuyruk"].str.isdigit())].copy()
    if ucluler.empty:
        return {}, []
    # Sessiz bayatlama tuzağı: END_DATE'i genel endeksle uyuşmayan kalemler
    # (ör. TP.TUKFIY2025.0815, 12.2025'te biten) kesite ALINMAZ.
    olu = []
    kod_map: dict[str, str] = {}
    for _, r in ucluler.iterrows():
        kod_map[r["kuyruk"]] = r["kod"]
    # verisi çekilmemiş üçlüler: bu adımda EVDS'ten TOPLU çekilir
    eksik = [k for k in kod_map if f"g3_{k}" not in a.columns]
    if eksik:
        for k in eksik:
            try:
                a[f"g3_{k}"] = veri.evds_aylik(kod_map[k])
            except Exception as ex:
                olu.append(k)
                print(f"    (üçlü grup {k} alınamadı: {ex})")
    adlar = []
    for k in sorted(kod_map):
        c = f"g3_{k}"
        if c not in a.columns or a[c].dropna().empty:
            continue
        adlar.append(c)
        if a[c].dropna().index[-1] < s_ay:
            olu.append(k)
    if olu:
        # Ağırlık tahmininde HÂLÂ kullanılırlar (yaşadıkları yıllarda kimliğin
        # parçasıdırlar); yalnız son ayın kesitinden düşerler ve ω yeniden
        # ölçeklenir.
        # Mesaj KISA tutulur: açıklaması sayfada duruyor, uyarı satırı onu
        # tekrar ederse paragraf kekeliyor (uyari_metni doğrudan MDX'e basılıyor).
        uyar(f"ALT KALEM: {len(set(olu))} adet üç haneli grup son ayda "
             f"({ad_uzun(s_ay)}) veri vermiyor: {', '.join(sorted(set(olu)))}.")
    # ana grup → çocukları (yıl bazında TAM VERİSİ OLAN çocuklarla)
    w_alt: dict[str, dict] = {}
    for ana in veri.ANA_GRUP_AD:
        cocuk = [c for c in adlar if c[3:].startswith(ana)]
        if not cocuk:
            continue
        if len(cocuk) == 1:
            w_alt[ana] = {str(y): {"paylar": {cocuk[0]: 1.0}, "artik_pp": 0.0,
                                   "n_ay": 0, "kip": "tek çocuk",
                                   "negatif_pay": 0, "eksik_cocuk": 0}
                          for y in yillar}
            continue
        w_alt[ana] = agirlik_tahmini(a, f"ana_{ana}", cocuk, yillar)
    # birleştir: toplam ağırlık = ana grup payı × grup içi pay
    toplam: dict[str, dict] = {}
    for yil in yillar:
        y = str(yil)
        if y not in w_ana:
            continue
        paylar: dict[str, float] = {}
        artik, atfedilen = 0.0, 0.0
        for ana in veri.ANA_GRUP_AD:
            wa = w_ana[y]["paylar"].get(f"ana_{ana}")
            if wa is None:
                continue
            if ana not in w_alt or y not in w_alt[ana]:
                continue          # o yıl bu ana grubun kırılımı çözülemedi
            artik = max(artik, w_alt[ana][y]["artik_pp"])
            atfedilen += wa
            for c, sp in w_alt[ana][y]["paylar"].items():
                paylar[c] = wa * sp
        if not paylar:
            continue
        # atfedilemeyen pay (kırılımı çözülemeyen ana gruplar) yeniden ölçeklenir
        top = sum(paylar.values())
        if top > 0:
            paylar = {k: v / top for k, v in paylar.items()}
        toplam[y] = {"paylar": paylar, "artik_pp": round(artik, 4),
                     "n_ay": w_ana[y]["n_ay"], "kip": "hiyerarşik",
                     "kapsanan_pay": round(atfedilen, 4),
                     "negatif_pay": int(sum(1 for v in paylar.values() if v < 0))}
    if toplam:
        sy = str(s_ay.year)
        if sy in toplam:
            t = toplam[sy]
            print(f"    alt kesit: {len(t['paylar'])} üç haneli grup · "
                  f"grup içi maks artık {t['artik_pp']} pp · "
                  f"kapsanan pay {t['kapsanan_pay']:.4f}")
            if t["kapsanan_pay"] < 0.97:
                uyar(f"KESİT: üç haneli kırılım TÜFE sepetinin yalnız "
                     f"%{t['kapsanan_pay']*100:.1f}'ini kapsıyor; kırpılmış "
                     "ortalama ve difüzyon bu daralmış kesitle okunmalı.")
            if t["negatif_pay"]:
                uyar(f"AĞIRLIK: {t['negatif_pay']} alt grupta NEGATİF pay tahmin "
                     "edildi (kimlik çözümü sınırda). Kırpma/medyan bu kalemlerde "
                     "gürültülü olabilir.")
    return toplam, adlar


# Medyan kalemi sıklığı bu tarihten itibaren sayılır (güncel rejim).
MEDYAN_SIKLIK_BAS = "2021-01-01"


def dagilim_hesapla(a: pd.DataFrame, alt_adlar: list[str], w_alt: dict,
                    s_ay: pd.Timestamp, ad_map: dict | None = None
                    ) -> tuple[pd.DataFrame, dict]:
    """Kesitin arındırılmış aylık değişimleriyle kırpılmış ortalama, ağırlıklı
    medyan ve difüzyon. Kırpma seviyesi KEYFÎDİR — üç α birden verilip aradaki
    bant ölçü belirsizliğinin görsel ifadesi olarak sunulur.

    İkinci dönüş değeri KESİT TANISIDIR ve yayımlanır:
      · alt kalemlerin tek tek arındırma tanıları (mevsim_p, tatil t ve katsayı)
      · mevsimsellik testinden geçemeyip HAM geçen kalem sayısı ve ağırlığı
      · kesit yoğunlaşması (en büyük pay, Herfindahl, eşdeğer kalem sayısı)
      · medyanı hangi kalemin verdiği ve bunun sıklığı
    Bunlar olmadan "43 grubun arındırılmış aylık değişimleri" cümlesi ölçülmemiş
    bir iddiadır: kesitin dörtte biri ham geçiyor ve eşdeğer kalem sayısı 43
    değil ~13.
    """
    if not alt_adlar or not w_alt:
        uyar("DAĞILIM: alt kalem kesiti kurulamadı — kırpılmış ortalama, medyan "
             "ve difüzyon üretilmedi.")
        return pd.DataFrame(), {}
    print(f"    kesit arındırılıyor ({len(alt_adlar)} grup)")
    ad_map = ad_map or {}
    sa_alt: dict[str, pd.Series] = {}
    tani_alt: dict[str, dict] = {}
    ham_gecen: list[str] = []
    tatil_gecen: dict[str, dict] = {}
    for c in alt_adlar:
        s, t = arindir(a[c])
        t["ad"] = ad_map.get(c, c)
        tani_alt[c] = t
        if not t.get("mevsimsel", True):
            ham_gecen.append(c)
        # hangi alt kalemde hareketli tatil regresörü eşiği GEÇTİ?
        gecen = {k: v for k, v in (t.get("tatil_t") or {}).items()
                 if v is not None and abs(v) > 1.96}
        if gecen:
            tatil_gecen[c] = {"ad": t["ad"], "t": gecen,
                              "katsayi_pp": {k: (t.get("tatil_katsayi") or {}).get(k)
                                             for k in gecen}}
        sa_alt[c] = s
    SAA = pd.DataFrame(sa_alt)
    if ham_gecen:
        print(f"      {len(ham_gecen)} grupta mevsimsellik anlamsız — "
              "arındırılmadan geçirildi (dipnota girer)")
    if tatil_gecen:
        print(f"      {len(tatil_gecen)} grupta hareketli tatil regresörü "
              "|t|>1,96 eşiğini geçti — düzeltme uygulandı")
    r_sa = (SAA / SAA.shift(1) - 1) * 100
    r_ham = (a[alt_adlar] / a[alt_adlar].shift(1) - 1) * 100
    aylar = [t for t in a.index if t >= pd.Timestamp("2007-01-01") and t <= s_ay]
    kayit = []
    medyan_kalem: dict[pd.Timestamp, str] = {}
    son_om = None
    for t in aylar:
        om = etkin_agirlik(w_alt, a, alt_adlar, t)
        if om is None or t not in r_sa.index:
            continue
        ad = list(om.index)
        rs, rh = r_sa.loc[t, ad], r_ham.loc[t, ad]
        pi_sa = float((om * rs).sum())
        med, med_k = agirlikli_medyan(rs, om, kalem=True)
        if med_k is not None:
            medyan_kalem[t] = med_k
        satir = {"tarih": t, "medyan": med,
                 "medyan_ham": agirlikli_medyan(rh, om),
                 "difuzyon_0": difuzyon(rs, om, 0.0),
                 "difuzyon_hedef": difuzyon(rs, om, HEDEF_AYLIK),
                 "difuzyon_mansete_gore": difuzyon(rs, om, pi_sa),
                 "kesit_n": int(rs.notna().sum())}
        for al in KIRPMA:
            satir[f"kirpma_{int(al*100):02d}"] = kirpilmis(rs, om, al)
        kayit.append(satir)
        son_om = om
    D = pd.DataFrame(kayit).set_index("tarih")
    tani = _kesit_tanisi(tani_alt, ham_gecen, tatil_gecen, medyan_kalem,
                         son_om, ad_map)
    if D.empty:
        return D, tani
    # Aylık ölçüleri okunur kılmak için 3 aylık ortalamanın yıllıklandırılmışı
    # (TCMB'nin ana eğilim sunumu da 3 aylık ortalamadır).
    for c in ["medyan"] + [f"kirpma_{int(al*100):02d}" for al in KIRPMA]:
        D[f"{c}_saar3"] = ((1 + D[c].rolling(3).mean() / 100) ** 12 - 1) * 100
    return D, tani


def _kesit_tanisi(tani_alt: dict, ham_gecen: list, tatil_gecen: dict,
                  medyan_kalem: dict, son_om, ad_map: dict) -> dict:
    """Kesitin yayımlanabilir tanısı — dagilim_hesapla()'nın yan ürünü."""
    t: dict = {"n": len(tani_alt), "kalemler": tani_alt,
               "tatil_gecen": tatil_gecen,
               "tatil_gecen_n": len(tatil_gecen),
               "arindirilmayan_n": len(ham_gecen),
               "arindirilmayan": [{"kod": c, "ad": ad_map.get(c, c),
                                   "mevsim_p": tani_alt[c].get("mevsim_p")}
                                  for c in ham_gecen]}
    if son_om is not None and len(son_om):
        w = son_om / son_om.sum()
        t["arindirilmayan_agirlik"] = round(
            float(w.reindex(ham_gecen).fillna(0.0).sum()) * 100, 2)
        # Yoğunlaşma: 43 kalem var ama kaç BAĞIMSIZ kalem eder?
        hhi = float((w ** 2).sum())
        enb = w.sort_values(ascending=False)
        t["yogunlasma"] = {
            "hhi": round(hhi, 4),
            "esdeger_kalem": round(1.0 / hhi, 1) if hhi > 0 else None,
            "en_buyuk_pay": round(float(enb.iloc[0]) * 100, 1),
            "en_buyuk_kod": str(enb.index[0]),
            "en_buyuk_ad": ad_map.get(str(enb.index[0]), str(enb.index[0])),
            "ilk3_pay": round(float(enb.iloc[:3].sum()) * 100, 1),
        }
    if medyan_kalem:
        ser = pd.Series(medyan_kalem)
        pen = ser[ser.index >= pd.Timestamp(MEDYAN_SIKLIK_BAS)]
        if len(pen):
            say = pen.value_counts()
            t["medyan_kalem"] = {
                "bas": MEDYAN_SIKLIK_BAS[:7],
                "ay": int(len(pen)),
                "en_sik_kod": str(say.index[0]),
                "en_sik_ad": ad_map.get(str(say.index[0]), str(say.index[0])),
                "en_sik_n": int(say.iloc[0]),
                "en_sik_pay": round(float(say.iloc[0]) / len(pen) * 100, 1),
                "son_kod": str(ser.iloc[-1]),
                "son_ad": ad_map.get(str(ser.iloc[-1]), str(ser.iloc[-1])),
            }
    return t


def reel_faiz_serisi(a: pd.DataFrame, g: pd.DataFrame, SA: pd.DataFrame) -> pd.DataFrame:
    """Dört reel faiz: ex-post (12a gerçekleşme), ex-ante (PKA 12 ay),
    ana eğilime göre (3a SAAR) ve ileriye dönük ex-ante (12 ay sonraki beklenen
    faiz / 24 ay sonraki beklenen enflasyon)."""
    if "aofm" not in g.columns or g["aofm"].dropna().empty:
        uyar("REEL FAİZ: fonlama maliyeti (TP.APIFON4) yok — reel faiz üretilemedi.")
        return pd.DataFrame()
    i = g["aofm"].dropna().resample("MS").last()
    pi = yillik(a["tufe"].dropna())
    egilim = saar(SA["tufe"].dropna(), 3) if "tufe" in SA.columns else pd.Series(dtype=float)
    d = pd.DataFrame({"faiz": i, "pi12": pi, "egilim3": egilim,
                      "bek12": a.get("pka_12a"), "bek24": a.get("pka_24a"),
                      "bek_faiz12": a.get("pka_faiz_12a")})
    d = d[d.index >= "2011-01-01"]
    d["ex_post"] = [reel(f, p) if pd.notna(f) and pd.notna(p) else np.nan
                    for f, p in zip(d["faiz"], d["pi12"])]
    d["ex_ante"] = [reel(f, p) if pd.notna(f) and pd.notna(p) else np.nan
                    for f, p in zip(d["faiz"], d["bek12"])]
    d["egilime_gore"] = [reel(f, p) if pd.notna(f) and pd.notna(p) else np.nan
                         for f, p in zip(d["faiz"], d["egilim3"])]
    d["ileri_ex_ante"] = [reel(f, p) if pd.notna(f) and pd.notna(p) else np.nan
                          for f, p in zip(d["bek_faiz12"], d["bek24"])]
    return d


def atalet_olc(SA: pd.DataFrame) -> dict:
    """Hizmet ataleti: 36 aylık yuvarlanan AR(1) kalıcılık katsayısı ρ.
    π^MA_t = c + ρ·π^MA_{t-1} + ε — ρ ne kadar yüksekse fiyatlama o kadar geçmişe
    bağlıdır. Aynı regresyon temel mal için de koşulup ikisi kıyaslanır."""
    out: dict = {}
    for ad in ("hizmet", "temel_mal", "tufe", "kira"):
        if ad not in SA.columns:
            continue
        m = aylik(SA[ad].dropna()).dropna()
        rho = []
        for i in range(36, len(m)):
            pen = m.iloc[i - 36:i]
            x, y = pen.values[:-1], pen.values[1:]
            X = np.column_stack([np.ones(len(x)), x])
            b, *_ = np.linalg.lstsq(X, y, rcond=None)
            rho.append((m.index[i], float(b[1])))
        if rho:
            s = pd.Series(dict(rho))
            out[ad] = {"son": round(float(s.iloc[-1]), 3),
                       "seri": {k.strftime("%Y-%m-%d"): round(float(v), 4)
                                for k, v in s.items()}}
    return out


def ozet_topla(a, g, SA, M, K, D, B, R, bek, atalet, ito, w_katki, w_ana,
               sa_tani, rev, dogrulama, s_ay, vintage=None, kesit_tani=None) -> dict:
    """ozet_uret.py'nin okuduğu tekil sayılar."""
    def son(df, kol, seri=None):
        d = df[df["seri"] == seri] if seri is not None else df
        if kol not in d.columns:
            return None
        v = d[kol].dropna()
        return float(v.iloc[-1]) if len(v) else None

    o: dict = {"son_ay": s_ay.strftime("%Y-%m-%d"),
               "son_ay_ad": ad_uzun(s_ay),
               "sa_yontem": SA_YONTEM,
               "dogrulama": dogrulama,
               "kosular_arasi": rev,
               "vintage": vintage or {},
               "kesit_tani": kesit_tani or {},
               "hedef_yillik": HEDEF_YILLIK,
               "hedef_aylik": round(HEDEF_AYLIK, 4)}
    # Ana serilerde hareketli tatil regresörü eşiği geçti mi? (Alt kalemlerde
    # geçenler kesit_tani içinde.) Geçmiyorsa bu ilan edilmeli: yöntem duyuruluyor
    # ama manşet ve çekirdekte fiilen ATIL kalıyor.
    ana_t = [abs(v) for d in sa_tani.values()
             for v in (d.get("tatil_t") or {}).values() if v is not None]
    o["tatil_ana_maks_t"] = round(max(ana_t), 2) if ana_t else None
    o["tatil_ana_gecen"] = int(sum(1 for x in ana_t if x > 1.96))
    # Enerji: arındırmanın sınırda olduğu ve en büyük tutarsızlığı ürettiği seri
    if "enerji" in SA.columns and "enerji" in a.columns:
        sa_y = yillik(SA["enerji"].dropna())
        ham_y = yillik(a["enerji"].dropna())
        d10 = pd.DataFrame({"s": sa_y, "h": ham_y}).dropna().tail(120)
        if len(d10):
            o["enerji_sa_ham_maks_pp"] = round(float((d10["s"] - d10["h"]).abs().max()), 3)
            o["enerji_sa_ham_son_pp"] = round(float(d10["s"].iloc[-1] - d10["h"].iloc[-1]), 3)
        o["enerji_mevsim_p"] = sa_tani.get("enerji", {}).get("mevsim_p")
    # Ocak'ın ortalama mevsimsel düzeltmesi: kesitin bir kısmı arındırılmadan
    # geçtiği için bu düzeltmenin O kalemlerde hiç uygulanmadığını sayfada
    # örneklerken kullanılıyor. Sabit yazılmaz, veriden okunur.
    if "tufe" in SA.columns:
        hm, sm = aylik(a["tufe"].dropna()), aylik(SA["tufe"].dropna())
        d1 = pd.DataFrame({"h": hm, "s": sm}).dropna()
        oc = d1[d1.index.month == 1]
        if len(oc):
            o["ocak_ham_ort"] = round(float(oc["h"].mean()), 2)
            o["ocak_sa_ort"] = round(float(oc["s"].mean()), 2)
            o["ocak_duzeltme_pp"] = round(float((oc["h"] - oc["s"]).mean()), 3)
            o["ocak_n"] = int(len(oc))
    for ad in TABLO:
        if ad not in set(M["seri"]):
            continue
        for kol in ("aylik_ham", "aylik_sa", "saar3_sa", "saar6_sa", "yillik",
                    "saar3_ham", "saar6_ham", "ecb3"):
            o[f"{ad}__{kol}"] = son(M, kol, ad)
        o[f"{ad}__oynak"] = ad in OYNAK
        o[f"{ad}__mevsimsel"] = bool(sa_tani.get(ad, {}).get("mevsimsel", True))
        o[f"{ad}__mevsim_p"] = sa_tani.get(ad, {}).get("mevsim_p")
    # Mevsimsellik testinden geçemeyip HAM geçen ana seriler — sayfadaki "°"
    # işaretli satırların listesi buradan türer, MDX'e gömülmez.
    ham_ana = [SERI_AD.get(ad, ad) for ad in TABLO
               if ad in set(M["seri"]) and not sa_tani.get(ad, {}).get("mevsimsel", True)]
    o["arindirilmayan_ana"] = ham_ana
    o["arindirilmayan_ana_metin"] = (" ve ".join(ham_ana) if ham_ana
                                     else "hiçbiri")
    if not D.empty:
        for kol in D.columns:
            v = D[kol].dropna()
            if len(v):
                o[f"dagilim__{kol}"] = float(v.iloc[-1])
    if not K.empty:
        sonk = K.dropna(subset=[c for c in K.columns if c.startswith("y_")]).iloc[-1]
        o["katki_yillik"] = {c[2:]: float(sonk[c]) * 100
                             for c in K.columns if c.startswith("y_")}
        o["katki_aylik"] = {c[2:]: float(sonk[c]) * 100
                            for c in K.columns if c.startswith("c_")}
        o["katki_ay_artik_pp"] = round(float(K["artik"].abs().tail(24).max()) * 100, 4)
        o["katki_ay_artik_tum_pp"] = round(float(K["artik"].abs().max()) * 100, 4)
        o["katki_yil_artik_pp"] = round(float(K["yil_artik"].abs().tail(24).max()) * 100, 4)
        o["katki_yil_artik_tum_pp"] = round(float(K["yil_artik"].abs().max()) * 100, 4)
    if not B.empty:
        o["baz"] = {ad: {"12ay_sonra": float(B[ad].iloc[-1]),
                         "aylik_varsayim": float(B[f"{ad}_aylik"].iloc[0]),
                         "yil_sonu": (float(B[ad][B.index.month == 12].iloc[0])
                                      if (B.index.month == 12).any() else None)}
                    for ad in ("son3_sa", "son12_ort", "gecen_yil")}
    if not R.empty:
        for kol in ("faiz", "ex_post", "ex_ante", "egilime_gore", "ileri_ex_ante"):
            v = R[kol].dropna()
            o[f"reel__{kol}"] = float(v.iloc[-1]) if len(v) else None
        v = R["faiz"].dropna()
        o["reel__faiz_tarih"] = v.index[-1].strftime("%Y-%m-%d") if len(v) else None
        v = R["ex_post"].dropna()
        o["reel__ex_post_tarih"] = v.index[-1].strftime("%Y-%m-%d") if len(v) else None
        if len(v):
            o["reel__ex_post_faiz"] = float(R.loc[v.index[-1], "faiz"])
    for ad in ("pka_yilsonu", "pka_12a", "pka_24a", "pka_5y", "pka_12a_medyan",
               "pka_12a_std", "pka_12a_n", "pka_faiz_12a",
               "reel_kesim_12a", "hanehalki_12a"):
        if ad in a.columns:
            s = a[ad].dropna()
            if len(s):
                o[f"bek__{ad}"] = float(s.iloc[-1])
                o[f"bek__{ad}_tarih"] = s.index[-1].strftime("%Y-%m-%d")
    o["beklenti_isabet"] = bek
    o["atalet"] = {k: v["son"] for k, v in atalet.items()}
    o["ito"] = ito
    sy = str(s_ay.year)
    o["agirlik_son_yil"] = {
        "yil": sy,
        "katki": {k: round(v * 100, 2)
                  for k, v in w_katki.get(sy, {}).get("paylar", {}).items()},
        "artik_pp": w_katki.get(sy, {}).get("artik_pp"),
        "kip": w_katki.get(sy, {}).get("kip"),
    }
    # ağırlık kayması (bir önceki yıla göre) — 2026 sınıflama değişiminin izi
    onc = str(s_ay.year - 1)
    if sy in w_katki and onc in w_katki:
        o["agirlik_kayma_pp"] = {
            k: round((w_katki[sy]["paylar"][k] - w_katki[onc]["paylar"][k]) * 100, 2)
            for k in w_katki[sy]["paylar"]}
    o["uyari_sayisi"] = len(UYARI)
    return o


def yaz_tablo(M: pd.DataFrame, s_ay: pd.Timestamp) -> None:
    print(f"\n  MOMENTUM TABLOSU · {ad_uzun(s_ay)}")
    print(f"  {'seri':<26}{'m/m':>7}{'SA m/m':>8}{'3a SAAR':>9}{'6a SAAR':>9}"
          f"{'12a':>8}{'(3a ham)':>10}{'ECB 3a':>8}")
    for ad in TABLO:
        d = M[M["seri"] == ad]
        if d.empty:
            continue
        r = d.iloc[-1]
        etiket = SERI_AD.get(ad, ad) + (" *" if ad in OYNAK else "")
        def f(x):
            return f"{x:>8.2f}" if pd.notna(x) else "       ·"
        print(f"  {etiket:<26}{r['aylik_ham']:>7.2f}{r['aylik_sa']:>8.2f}"
              f"{r['saar3_sa']:>9.2f}{r['saar6_sa']:>9.2f}{r['yillik']:>8.2f}"
              f"{r['saar3_ham']:>10.2f}{f(r['ecb3'])}")
    print("  * oynak: 3a SAAR ±%25 salınıyor, merkezî ölçü olarak okunmaz.")


if __name__ == "__main__":
    kos()


# ---------------------------------------------------------------------------
def uge_profil(a: pd.DataFrame, dislanan: tuple[int, ...] = DISLANAN_YIL) -> dict:
    """İTO'NUN İKİNCİ BAŞLIK ENDEKSİ: Ücretliler Geçinme Endeksi.

    NEDEN AYRI BİR ÖLÇÜM: ÜGE, tüketici fiyat endeksinin başka bir adı değil.
    Aynı şehri ölçüyor ama başka bir soruyu cevaplıyor — bir ücretli hanenin
    GEÇİM MALİYETİ. Sepeti farklı bir harcama yapısına göre ağırlıklandırılmış,
    dolayısıyla aynı ay için farklı bir sayı üretmesi normaldir, hata değil.
    Okurun sorusu şu: TÜİK TÜFE'sini kestirmek için hangisi daha iyi bir öncü?

    ÜÇLÜ KARŞILAŞTIRMA. İki değil üç seri hizalanıyor (ÜGE · İTO TÜFE · TÜİK
    TÜFE) ve üç fark birden ölçülüyor. İki serilik kıyas "ÜGE TÜFE'den yukarıda"
    der ve okur bunu ÜGE'ye özgü sanır; oysa İTO'nun tüketici endeksi de
    yukarıda. Ayrışmanın ÜGE'ye ait olan kısmı ancak üçüncü seri masadayken
    görünür.

    HANGİ ÜGE. Endeksin dört baz varyantı var (1963/1968/1985/1995) ve aylık
    değişimleri BİRBİRİNDEN FARKLI. "ÜGE %şu kadar arttı" cümlesi hangi varyant
    olduğu söylenmeden kurulamaz; sayfa bu farkı bir sayıyla gösterebilsin diye
    1985 varyantı da taşınıyor ve iki varyantın açıklığı ölçülüyor.
    """
    from scipy import stats as _st
    if "ito_uge" not in a.columns:
        return {}
    uge_ay = aylik(a["ito_uge"].dropna()).dropna()
    if uge_ay.empty:
        return {}

    # ---- KİMLİK: EVDS serisi İTO'nun yayımladığı tabloyla ay ay kıyaslanır.
    # Ad artık EVDS'ten okunabiliyor; doğrulama yine de kalkmıyor. Ad kaynağın
    # ETİKETİ, sayı kaynağın KENDİSİDİR — biri değişip diğeri değişmeyebilir.
    yay = (_ito_yayim().get("uge") or {})
    kimlik: dict = {"esik": ITO_DOGRULAMA_ESIK}
    if yay:
        y = pd.Series({pd.Timestamp(k + "-01"): float(v) for k, v in yay.items()})
        ortak = uge_ay.index.intersection(y.index)
        if len(ortak):
            sapma = (uge_ay.loc[ortak] - y.loc[ortak]).abs()
            kimlik.update({
                "ortak": int(len(ortak)),
                "maks_sapma": round(float(sapma.max()), 4),
                "ort_sapma": round(float(sapma.mean()), 4),
                "sapan": int((sapma > ITO_DOGRULAMA_ESIK).sum()),
            })
            if kimlik["sapan"]:
                kotu = sapma[sapma > ITO_DOGRULAMA_ESIK]
                uyar(f"ÜGE KİMLİK DOĞRULAMASI DÜŞTÜ: {len(kotu)} ayda EVDS "
                     f"serisi İTO'nun yayımıyla tutmuyor (en büyük sapma "
                     f"{kotu.max():.3f} puan, {kotu.idxmax():%Y-%m}). Sayfadaki "
                     f"ÜGE iddiaları askıya alınmalı.")

    # ---- ÜÇLÜ HİZALAMA
    ito_ay, _ = _ito_seri(a)
    ucu = pd.DataFrame({"uge": uge_ay,
                        "ito": ito_ay,
                        "tufe": aylik(a["tufe"].dropna())}).dropna()
    if len(ucu) < 18:
        return {"n": int(len(ucu)), "not": "örneklem yetersiz", "kimlik": kimlik}
    ucu["uge_tufe"] = ucu["uge"] - ucu["tufe"]
    ucu["ito_tufe"] = ucu["ito"] - ucu["tufe"]
    ucu["uge_ito"] = ucu["uge"] - ucu["ito"]

    out: dict = {"n": int(len(ucu)), "kimlik": kimlik,
                 "ilk_ay": ucu.index[0].strftime("%Y-%m"),
                 "son_ay": ucu.index[-1].strftime("%Y-%m")}
    for ad, sut in (("uge_tufe", "uge_tufe"), ("ito_tufe", "ito_tufe"),
                    ("uge_ito", "uge_ito")):
        out[ad] = _fark_ozet(ucu[sut])

    # ---- İLİŞKİNİN BİÇİMİ: her iki öncü için AYNI kod, aynı örneklem.
    # İki ayrı yerde iki ayrı regresyon yazmak, bir gün ikisinin farklı
    # örneklemde koşması demekti; kıyasın anlamı da o gün biterdi.
    def _regres(x: pd.Series, y: pd.Series) -> dict:
        X = np.column_stack([np.ones(len(x)), x.values])
        kat, *_ = np.linalg.lstsq(X, y.values, rcond=None)
        art = y.values - X @ kat
        n, k = len(x), 2
        s2 = float(art @ art) / (n - k)
        se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
        ss_t = float(((y.values - y.values.mean()) ** 2).sum())
        r = float(np.corrcoef(x.values, y.values)[0, 1])
        return {"sabit": round(float(kat[0]), 3), "egim": round(float(kat[1]), 3),
                "se_egim": round(float(se[1]), 3),
                "t_bir": round(float((kat[1] - 1) / se[1]), 2),
                "p_bir": round(float(2 * (1 - _st.t.cdf(abs((kat[1] - 1) / se[1]),
                                                        n - k))), 4),
                "r": round(r, 3), "r2": round(1 - float(art @ art) / ss_t, 3),
                "sigma": round(float(np.sqrt(s2)), 3)}
    out["reg_uge"] = _regres(ucu["uge"], ucu["tufe"])
    out["reg_ito"] = _regres(ucu["ito"], ucu["tufe"])

    # ---- HANGİSİ DAHA İYİ ÖNCÜ: örneklem DIŞI, genişleyen pencere, sabit
    # kaydırma kuralı. Örneklem içi R² iyimserdir ve iki seriyi kıyaslarken
    # asıl soru "geçmişe hangisi uydu" değil, "yarın hangisini kullanayım".
    asgari = max(12, len(ucu) // 3)
    hata_uge, hata_ito, aylar_od = [], [], []
    for i in range(asgari, len(ucu)):
        gec, simdi = ucu.iloc[:i], ucu.iloc[i]
        hata_uge.append((simdi["uge"] - gec["uge_tufe"].mean()) - simdi["tufe"])
        hata_ito.append((simdi["ito"] - gec["ito_tufe"].mean()) - simdi["tufe"])
        aylar_od.append(ucu.index[i])
    if hata_uge:
        hu, hi = np.array(hata_uge), np.array(hata_ito)
        esli_t, esli_p = _st.ttest_rel(np.abs(hu), np.abs(hi))
        out["yaris"] = {
            "n": len(hu),
            "ilk_ay": aylar_od[0].strftime("%Y-%m"),
            "mae_uge": round(float(np.abs(hu).mean()), 3),
            "mae_ito": round(float(np.abs(hi).mean()), 3),
            "esli_fark": round(float((np.abs(hu) - np.abs(hi)).mean()), 3),
            "esli_t": round(float(esli_t), 2),
            "esli_p": round(float(esli_p), 3),
        }
        # HÜKÜM KODDA: "ÜGE daha iyi öncü" cümlesi ancak fark ayırt
        # edilebiliyorsa kurulabilir. Metne elle yazılsaydı örneklem
        # büyüdüğünde yanlış hüküm basılırdı.
        y = out["yaris"]
        if y["esli_p"] < 0.05:
            iyi = "ÜGE" if y["esli_fark"] < 0 else "tüketici endeksi"
            y["hukum"] = (f"{iyi} ölçülebilir biçimde daha isabetli "
                          f"(eşli fark {abs(y['esli_fark']):.3f} puan, "
                          f"p = {y['esli_p']:.3f})".replace(".", ","))
        else:
            y["hukum"] = ("iki öncünün isabeti bu örneklemde birbirinden "
                          "AYIRT EDİLEMİYOR (p = "
                          + f"{y['esli_p']:.3f}".replace(".", ",") + ")")

    # ---- BEKLEYEN AY: ÜGE geldi, TÜFE bekleniyor.
    son_uge_ay = uge_ay.index[-1]
    t_ham = aylik(a["tufe"].dropna())
    if son_uge_ay not in t_ham.index:
        gec = ucu[ucu.index < son_uge_ay]
        x = float(uge_ay.loc[son_uge_ay])
        r = out["reg_uge"]
        out["bekleyen"] = {
            "ay": son_uge_ay.strftime("%Y-%m"),
            "ad": ad_uzun(son_uge_ay),
            "uge": round(x, 2),
            "sabit": round(x - float(gec["uge_tufe"].mean()), 2),
            "regresyon": round(r["sabit"] + r["egim"] * x, 2),
            "n_gecmis": int(len(gec)),
        }

    # ---- HANGİ ÜGE: varyantlar arası açıklık. Tek bir "ÜGE" yok.
    if "ito_uge_85" in a.columns:
        v85 = aylik(a["ito_uge_85"].dropna()).dropna()
        ortak = uge_ay.index.intersection(v85.index)
        if len(ortak) > 6:
            fark = (uge_ay.loc[ortak] - v85.loc[ortak])
            out["varyant"] = {
                "n": int(len(ortak)),
                "son_95": round(float(uge_ay.loc[ortak[-1]]), 2),
                "son_85": round(float(v85.loc[ortak[-1]]), 2),
                "ort_mutlak_fark": round(float(fark.abs().mean()), 2),
                "maks_mutlak_fark": round(float(fark.abs().max()), 2),
                "maks_ay": fark.abs().idxmax().strftime("%Y-%m"),
            }
    return out
