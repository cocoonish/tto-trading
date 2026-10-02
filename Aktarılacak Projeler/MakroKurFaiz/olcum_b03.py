#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 3 ölçüm katmanı: tepki fonksiyonu.

Pratikler
  p3a  Türkiye Taylor bandı (aylık): iki enflasyon ölçüsü × iki çıktı açığı
       sürümü × üç r*; AOFM ve politika faizi ile kıyas. `arac_taylor`: Araç 1'in
       açılış girdileri.
  p3b  PPK günleri (111 karar, 2016–2026): DİBS tarih hizası, ima sürprizinin
       (Δ3 ay) gürültüsü ve plasebo kapısı; anket sürprizi (PKA toplantı
       beklentisi) ve kur tepkisi dönem dönem; karar değişimi ile anket sürprizi.
  p3c  ABD–Almanya 2 yıllık farkı ile EUR/USD, haftalık, dört dönem.
  p3d  ABD istihdam ve Türkiye GSYH yayım günleri: varyans/kovaryans oranı.
  sekil_03 Taylor bandı, sekil_04 faiz farkı ↔ EUR/USD.

Öbür modüllerin kullanabileceği yardımcılar (b04 içe aktarır; b03 hiçbir bölüm
modülünü içe aktarmaz): `regresyon`, `tr_takvim`, `tr_gunluk_degisim`,
`dibs_gecikme`, `olay_kapisi`, `sakin_gunler`, `abd_gunluk_degisim`,
`yayim_gunu_orani`, `hp_suzgec`, `kurulmadi`.

ÖLÇÜM TUZAKLARI (bu modül yazılırken ölçüldü)
1. DİBS EĞRİSİNİN TARİHİ PİYASADAN BİR İŞ GÜNÜ GERİDE. Etiket t'deki değer
   t−1'in piyasasını taşıyor. Ölçü: DİBS 2 ve 5 yıllık günlük değişiminin TCMB
   gösterge kuruyla (15:30 ilanı) çapraz korelasyonu 2013–2021'in her yılında
   bir gün kaydırmada tepe yapıyor (5 yıllıkta 0,51–0,74; aynı günde ≈0).
   Olaylarla da tutuyor: Başkan'ın görevden alındığı cumartesinin ardından
   (22.03.2021 pazartesi) 2 yıllık sıçrama 23.03 etiketinde (+266 bp, 22.03'te
   +23 bp); 19.03.2025 sabahı başlayan satış 20.03 etiketinde (+227 bp); 24.08.2023
   kararının 3 aylık tepkisi 25.08 etiketinde. Bu modül DİBS'i ölçülen gecikme
   kadar öne alır (`dibs_gecikme`); Bölüm 1'in haftalık kadranı ve öbür bölümler
   saklı tarihle çalışıyorsa aynı haftada kur ile getiri bir gün kayık ölçülür.
2. PPK GÜNÜ DİBS DEĞİŞİMİ SIRADAN GÜNDEN AYRIŞMIYOR. Plasebo profilinin tepesi
   hiçbir düğümde ve hiçbir tarih sözleşmesinde (saklı, bir gün öne alınmış,
   iki günlük pencere) karar gününe oturmuyor; 3 aylık düğüm sıradan günlerde
   de yüzlerce baz puan oynuyor (ör. 08→09.04.2024 −489 bp). İma sürprizi bu
   seriden kurulamaz; kapı düştüğü için yayımlanmaz (`tani` altında, yalnız tanı).
   Kur (Yahoo) kapıyı geçiyor; tepki anket sürprizine karşı ölçülür.
3. TCMB gösterge kurunun PPK profili karar gününde değil ertesi günde tepe
   yapıyor: 15:30 ilanı 14:00 kararından sonradır ama kur tepkisinin büyüğü
   15:30'dan sonra geliyor. Sağlamlık sınaması bu yüzden PPK'da kurulmadı.
4. BIS'in Türkiye politika faizi (`em_politika_aylik.tur`) AY SONU değeridir:
   fonlama politika faiziyle örtüşen 94 ayın 94'ünde ay sonuna eşit. Politika
   faizi iki kaynakta da ay sonu alınır; AOFM ay ortalamasıdır.
5. 1 Haziran 2018 sadeleşmesinden önce bir hafta vadeli repo (2016–2018'de
   %7,5–8) etkin faiz değildi. PPK dosyası 23.05.2018'de 8,00, 07.06.2018'de
   17,75 yazar: aradaki 975 baz puan tanım değişikliğidir. 07.06.2018 kararının
   önceki etkin oranı AOFM'dir (16,50). Karar değişimi 07.06.2018'de başlar.
6. Fonlama dosyasında politika faizi ve AOFM karar gününün ertesi günü değişir;
   kararın kendisi PPK dosyasından okunur.
7. PKA toplantı beklentisi 05.2025'e kadar "cari ay sonu bir hafta vadeli repo",
   sonra "ilk toplantı" sorusudur. Karar ayının anketi eşlenir: ayın erken
   günlerindeki kararlardan dördünde (12.09.2019, 12.12.2019, 11.09.2025,
   11.12.2025) aynı ay anketi karardan sapıyor, yani anket karardan önce
   toplanmış. Önceki ay anketinin "cari ay sonu" sorusu önceki ayın sonunu
   sorar, eşlenmez. 10.09.2026 kararının anketi aylık çıpanın dışında.
8. "Gerçek zamanlı" HP açığı bugünkü veri sürümüyle kurulur: uç noktası
   sorununu ölçer, GSYH revizyonlarını ölçmez.
9. 18.12.2023 öncesi Yahoo USD/TRY serisinde cuma değeri pazartesi barının
   başındaki fiyattır (Bölüm 1); cuma günü düşen olaylarda kur değişimi hafta
   sonunu da taşır.
10. ÖRNEKLEM DIŞI KIYAS YALNIZ SIFIRA KARŞI YAPILIRSA SÜRÜKLENME KAPIYI AÇAR.
   Sürünen bir seride (2023 sonrası USD/TRY) sabit terim tek başına "değişim
   sıfır" tahminini yener: aylık kur–TÜFE sürprizi regresyonunda oran 0,13
   çıktı, koşulsuz ortalamaya karşı 0,91. `regresyon` iki kıyası da yapar ve
   hüküm için ikisini de ister.
11. Küçük örneklemde Newey–West t'si anlamsızlaşır: 2021-01…11'de 11 kararın
   yalnız dördünde anket sürprizi sıfırdan farklı ve kur eğiminin t'si −17
   çıkıyor; hüküm örneklem dışı sınama kurulamadığı için zaten "tarif edici".
   Birini dışarıda bırakma aralığı her regresyonda yazılır.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

# ─────────────────────────────────────────────────────────────── sabitler
PI_HEDEF = 5.0            # TCMB enflasyon hedefi, %
KATSAYI_PI = 0.5          # Taylor (1993)
KATSAYI_ACIK = 0.5        # Taylor (1993)
R_YILDIZ = (0.0, 2.0, 4.0)
R_YILDIZ_VARSAYILAN = 2.0
HP_LAMBDA = 1600
RT_ASGARI_CEYREK = 20     # gerçek zamanlı süzgecin ilk penceresi (çeyrek)
YAYIM_GECIKME_AY = 3      # çeyreğin açığı, son ayından üç ay sonra kullanılır
TAYLOR_ILK_AY = pd.Period("2006-01", "M")
GECIKME_YILLARI = range(2013, 2022)   # kurun serbest dalgalandığı ve korelasyonun okunur olduğu yıllar

DONEM_PPK = [
    ("d2016_2020", "2016-01-01", "2020-12-31", "2016–2020"),
    ("d2021", "2021-01-01", "2021-11-30", "2021-01…2021-11"),
    ("yonetilen", "2021-12-01", "2023-06-30", "yönetilen kur 2021-12…2023-06"),
    ("d2023_2026", "2023-07-01", "2026-09-30", "2023-07…2026-09"),
]
DONEM_TAYLOR = [
    ("d2013_2020", "2013-01", "2020-12", "2013–2020"),
    ("d2021", "2021-01", "2021-11", "2021-01…2021-11"),
    ("yonetilen", "2021-12", "2023-06", "yönetilen kur 2021-12…2023-06"),
    ("d2023_2026", "2023-07", "2026-08", "2023-07…2026-08"),
]
DONEM_3C = [
    ("d1999_2007", "1999-01-01", "2007-12-31", "1999–2007"),
    ("d2008_2014", "2008-01-01", "2014-12-31", "2008–2014"),
    ("d2015_2019", "2015-01-01", "2019-12-31", "2015–2019"),
    ("d2020_2026", "2020-01-01", "2026-09-30", "2020–2026"),
]
KARAR_ILK = pd.Timestamp("2018-06-07")   # tuzak 5
DIBS_DUGUM = ("n3a", "n6a", "n1y", "n2y", "n5y", "n7y")


# ─────────────────────────────────────────────────────────────── yardımcılar
def _iso(t) -> str | None:
    if t is None:
        return None
    if isinstance(t, pd.Period):
        return str(t)
    try:
        return str(pd.Timestamp(t).date())
    except (ValueError, TypeError):
        return str(t)


def _f(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _liste(s: pd.Series) -> list:
    return [_f(v) for v in s.values]


def kurulmadi(sebep: str, **ek) -> dict:
    return {"durum": "kurulmadi", "sebep": sebep, **ek}


def hp_suzgec(y: np.ndarray, lam: float = HP_LAMBDA) -> np.ndarray:
    """Hodrick–Prescott eğilimi: (I + λ·DᵀD) τ = y; D ikinci fark matrisi."""
    y = np.asarray(y, dtype=float)
    n = len(y)
    D = np.zeros((n - 2, n))
    i = np.arange(n - 2)
    D[i, i], D[i, i + 1], D[i, i + 2] = 1.0, -2.0, 1.0
    return np.linalg.solve(np.eye(n) + lam * D.T @ D, y)


def regresyon(y: pd.Series, x: pd.Series, ilk_pencere: int | None = None) -> dict:
    """y = a + b·x, Newey–West; örneklem dışı genişleyen pencere kıyası; hüküm.

    n < 10 ise vaka tablosu (yalnız noktalar, t yok). Örneklem dışı kıyas İKİ
    saf ölçüte karşı yapılır: rastgele yürüyüş (değişim sıfır) ve koşulsuz
    ortalama (sürüklenmeli rastgele yürüyüş). Yalnız sıfıra karşı sınanınca
    sürüklenen bir seride (sürünen USD/TRY) sabit terim tek başına kıyası
    yener ve eğimin katkısı ölçülmez. Hüküm: |t| ≥ 2 ve İKİ oran da < 1 (en az
    on tahminle) birlikte yoksa "tarif edici"."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1, sort=True).dropna()
    n = len(d)
    out = {"n": int(n), "ilk": _iso(d.index.min()) if n else None, "son": _iso(d.index.max()) if n else None}
    if n < 10:
        out.update({"durum": "vaka tablosu", "not": "on gözlemden az: test istatistiği yazılmaz",
                    "noktalar": [[_iso(t), _f(r.x), _f(r.y)] for t, r in d.iterrows()]})
        return out
    if float(d["x"].std()) == 0.0:
        out.update(kurulmadi("açıklayıcı değişken bu dönemde hiç değişmiyor"))
        return out
    r = oo.hac(d["y"].values, d["x"].values)
    if r.get("yetersiz"):
        out.update(kurulmadi("regresyon için gözlem yetersiz"))
        return out
    out.update({"sabit": r["b"][0], "egim": r["b"][1], "se": r["se"][1], "t": r["t"][1],
                "r2": r["r2"], "gecikme": r["gecikme"],
                "korelasyon": _f(np.corrcoef(d["x"], d["y"])[0, 1])})
    ip = ilk_pencere if ilk_pencere is not None else max(10, n // 2)
    oranlar = []
    for anahtar, kiyas, ad in (("oos", "sifir", "rastgele yürüyüş (değişim sıfır)"),
                               ("oos_ortalama", "ortalama", "koşulsuz ortalama")):
        if n - ip >= 10:
            o = oo.oos_kiyas(d["y"], d["x"], ip, kiyas)
            out[anahtar] = {"n": o["n"], "mse_oran": o.get("mse_oran"), "dm_t": o.get("dm_t"),
                            "kiyas": ad, "ilk": o.get("ilk")}
            oranlar.append(o.get("mse_oran"))
        else:
            out[anahtar] = kurulmadi("örneklem dışı sınama için en az on tahmin gerekir")
            oranlar.append(None)
    gecti = abs(out["t"]) >= 2 and all(o is not None and o < 1 for o in oranlar)
    out["hukum"] = "ölçülü" if gecti else "tarif edici"
    out["birini_disarida_birak"] = loo_egim(d["y"], d["x"])
    return out


def loo_egim(y: pd.Series, x: pd.Series) -> dict:
    """Birini dışarıda bırakma: her gözlem tek tek atılınca EKK eğiminin aralığı
    ve eğimi en çok oynatan gözlem (kapalı biçim, döngüsüz)."""
    xv, yv = np.asarray(x, float), np.asarray(y, float)
    n = len(xv)
    sx, sy, sxx, sxy = xv.sum(), yv.sum(), (xv * xv).sum(), (xv * yv).sum()
    m = n - 1
    pay = m * (sxy - xv * yv) - (sx - xv) * (sy - yv)
    payda = m * (sxx - xv * xv) - (sx - xv) ** 2
    with np.errstate(divide="ignore", invalid="ignore"):
        b = np.where(payda > 0, pay / payda, np.nan)
    b_tam = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    if not np.isfinite(b).any():
        return kurulmadi("açıklayıcı değişken tek gözlem dışında sabit")
    j = int(np.nanargmax(np.abs(b - b_tam)))
    return {"egim_min": _f(np.nanmin(b)), "egim_max": _f(np.nanmax(b)),
            "en_etkili_gozlem": _iso(x.index[j]), "o_gozlemsiz_egim": _f(b[j])}


@lru_cache(maxsize=1)
def tr_takvim() -> pd.DatetimeIndex:
    """Türkiye iş günü takvimi: fonlama (EVDS iş günü; tatil yok) ∩ DİBS eğri günleri."""
    f = oo.oku("fonlama_gunluk").index
    d = oo.oku("dibs_egri_gunluk").index
    return pd.DatetimeIndex(f.intersection(d))


@lru_cache(maxsize=1)
def dibs_gecikme() -> dict:
    """DİBS etiket gecikmesi (iş günü): DİBS 2 ve 5 yıllık günlük değişiminin
    TCMB gösterge kuruyla (ilan günü, 15:30) çapraz korelasyonunun yıl yıl
    tepe yaptığı kayma; karar en sık tepe."""
    tk = tr_takvim()
    d = oo.oku("dibs_egri_gunluk")
    tc = oo.usdtry_tcmb()
    x = pd.DataFrame({"n2y": d["n2y"].reindex(tk).diff(), "n5y": d["n5y"].reindex(tk).diff(),
                      "tcmb": np.log(tc.reindex(tk)).diff()}, index=tk)
    yillik, tepeler = {}, []
    for yil in GECIKME_YILLARI:
        z = x.loc[str(yil)]
        satir = {}
        for c in ("n2y", "n5y"):
            kor = {k: _f(z[c].shift(-k).corr(z["tcmb"])) for k in (0, 1, 2)}
            tepe = max(kor, key=lambda k: kor[k] if kor[k] is not None else -9)
            tepeler.append(tepe)
            satir[c] = {"k0": kor[0], "k1": kor[1], "k2": kor[2], "tepe": tepe}
        yillik[str(yil)] = satir
    say = {k: tepeler.count(k) for k in (0, 1, 2)}
    karar = max(say, key=say.get)
    return {"gecikme_is_gunu": int(karar), "tepe_sayisi": {str(k): v for k, v in say.items()},
            "yillik": yillik, "ilk_yil": GECIKME_YILLARI[0], "son_yil": GECIKME_YILLARI[-1],
            "yontem": "DİBS 2 ve 5 yıllık getirisinin günlük değişimi, TCMB gösterge kurunun ilan günü değişimiyle "
                      "0, 1 ve 2 iş günü kaydırılarak yıl yıl korelasyona sokuldu; kur serbestçe dalgalanırken "
                      "korelasyonun en yüksek olduğu kayma etiket gecikmesidir.",
            "olay_kaniti": "22.03.2021 pazartesi (cumartesi görevden alma): 2 yıllık 22.03 etiketinde +23 bp, 23.03 "
                           "etiketinde +266 bp; 19.03.2025 sabahı başlayan satış: 19.03'te −45 bp, 20.03'te +227 bp."}


@lru_cache(maxsize=4)
def tr_gunluk_degisim(gecikme: int | None = None) -> pd.DataFrame:
    """Türkiye iş günü takviminde piyasa günü değişimi: DİBS düğümleri (bp; etiket
    `gecikme` iş günü öne alınır, varsayılan ölçülen gecikme), USD/TRY Yahoo ve
    TCMB (log, %). Sütunlar aynı piyasa gününü ölçer."""
    g = dibs_gecikme()["gecikme_is_gunu"] if gecikme is None else gecikme
    takvim = tr_takvim()
    dibs = oo.oku("dibs_egri_gunluk")[list(DIBS_DUGUM)]
    dibs = dibs.shift(-g).reindex(takvim)          # kendi gün sırasında öne al, sonra takvime indir
    out = {c: dibs[c].diff() * 100 for c in DIBS_DUGUM}
    kur, _ = oo.usdtry()
    out["usdtry"] = np.log(kur.reindex(takvim)).diff() * 100
    tc = oo.usdtry_tcmb()
    out["usdtry_tcmb"] = np.log(tc.reindex(takvim)).diff() * 100
    return pd.DataFrame(out, index=takvim)


def sakin_gunler(index: pd.DatetimeIndex, olaylar, pencere: int = 2) -> pd.DatetimeIndex:
    """Olay günlerinin ±pencere iş günü dışında kalan günler (olay_profili ile aynı tanım)."""
    poz = set()
    for o in pd.DatetimeIndex(olaylar):
        j = index.searchsorted(o)
        if j < len(index) and index[j] == o:
            for k in range(-pencere, pencere + 1):
                poz.add(j + k)
    return index[[i for i in range(len(index)) if i not in poz]]


def olay_kapisi(degisim: pd.Series, olaylar) -> dict:
    """Plasebo profili (−2…+2 iş günü, |Δ| ortalaması / sıradan gün): tepe 0'da
    değilse olay çalışması kurulmaz."""
    p = oo.olay_profili(degisim, olaylar, pencere=2)
    return {"n_olay": p["n_olay"], "oran": p["oran"], "tepe": p["tepe"], "gecti": bool(p["tepe_sifirda"])}


def _kapi_sebebi(k: dict) -> str:
    return (f"plasebo profilinin tepesi olay gününde değil ({k['tepe']:+d} iş gününde); "
            "olay penceresi kurulmaz")


def dolar_seviye() -> pd.Series:
    """Altı G10 kurunun (CNBC New York 17:00) dolar yönünde log ortalaması ×100.
    EUR, GBP, AUD XXX/USD kotelidir, yönü çevrilir; artış doların değer kazancı."""
    k = oo.oku("cnbc_kur_gunluk")
    k = k[k.index.dayofweek < 5][["eur", "gbp", "aud", "chf", "jpy", "cad"]].dropna()
    l = np.log(k)
    for c in ("eur", "gbp", "aud"):
        l[c] = -l[c]
    return l.mean(axis=1) * 100


@lru_cache(maxsize=1)
def abd_gunluk_degisim() -> pd.DataFrame:
    """ABD iş günleri: Δus2 (bp), G10 dolar endeksi, Δlog(USD/EUR) ve Δlog(USD/JPY)
    (%), hepsi aynı gün aralığında (ABD Hazinesi ve altı kurun birlikte olduğu günler)."""
    us = oo.oku("abd_hazine_gunluk")["us2"]
    dol = dolar_seviye()
    k = oo.oku("cnbc_kur_gunluk")
    k = k[k.index.dayofweek < 5]
    gun = us.index.intersection(dol.index)
    return pd.DataFrame({"us2": us.reindex(gun).diff() * 100, "dolar": dol.reindex(gun).diff(),
                         "usd_eur": -np.log(k["eur"].reindex(gun)).diff() * 100,
                         "usd_jpy": np.log(k["jpy"].reindex(gun)).diff() * 100}, index=gun)


def yayim_gunu_orani(degisim: pd.DataFrame, gunler, ciftler, donemler) -> dict:
    """Yayım günü ile sıradan günün varyans ve kovaryans oranı (sürpriz değil).

    Her sütun önce plasebo kapısından geçer; geçmeyen sütunun oranı ve onu içeren
    çiftin kovaryansı yazılmaz. `varyans_egim_y_x` heteroskedastisite ile
    tanımlanan eğimdir: (kov_olay − kov_sakin) / (var_olay(x) − var_sakin(x))."""
    gunler = pd.DatetimeIndex(gunler)
    kapi = {c: olay_kapisi(degisim[c], gunler) for c in degisim.columns}
    out = {"kapi": kapi}
    for k, a, b, ad in donemler:
        d = degisim.loc[a:b]
        e = d.loc[d.index.intersection(gunler)]
        s = d.loc[sakin_gunler(d.index, gunler)]
        r = {"ad": ad, "n_olay": int(len(e)), "n_sakin": int(len(s)),
             "ilk": _iso(e.index.min()) if len(e) else None, "son": _iso(e.index.max()) if len(e) else None}
        if len(e) < 10:
            r["durum"] = "vaka tablosu"
            out[k] = r
            continue
        for c in d.columns:
            if kapi[c]["gecti"]:
                r[f"varyans_orani_{c}"] = _f(e[c].var() / s[c].var())
            else:
                r[f"varyans_orani_{c}"] = kurulmadi(_kapi_sebebi(kapi[c]))
        for x, y in ciftler:
            if not (kapi[x]["gecti"] and kapi[y]["gecti"]):
                r[f"kov_{x}_{y}"] = kurulmadi("çiftin en az bir serisi plasebo kapısını geçmedi")
                continue
            ee, ss = e[[x, y]].dropna(), s[[x, y]].dropna()
            ce, cs = ee.cov().iloc[0, 1], ss.cov().iloc[0, 1]
            dv = ee[x].var() - ss[x].var()
            r[f"kov_{x}_{y}"] = {"kov_olay": _f(ce), "kov_sakin": _f(cs), "kov_orani": _f(ce / cs) if cs else None,
                                 "kor_olay": _f(ee.corr().iloc[0, 1]), "kor_sakin": _f(ss.corr().iloc[0, 1]),
                                 "varyans_egim": _f((ce - cs) / dv) if dv > 0 else None}
        out[k] = r
    return out


# ═══════════════════════════════════════════════════════════════ p3a
@lru_cache(maxsize=1)
def cikti_acigi() -> pd.DataFrame:
    """Çeyreklik çıktı açığı (log puan ×100): tam örneklem HP ve gerçek zamanlı
    HP (her çeyrekte o güne kadarki veriyle süzülüp son nokta)."""
    g = oo.oku("gsyh_ceyreklik")["gsyh_mta_hacim"].dropna()
    y = np.log(g.values) * 100
    tam = y - hp_suzgec(y)
    rt = np.full(len(y), np.nan)
    for j in range(RT_ASGARI_CEYREK - 1, len(y)):
        yy = y[: j + 1]
        rt[j] = (yy - hp_suzgec(yy))[-1]
    q = pd.PeriodIndex(g.index, freq="Q")
    return pd.DataFrame({"tam": tam, "gercek_zamanli": rt}, index=q)


def _rt_ceyrek(m: pd.Period) -> pd.Period:
    """Ay m'de kullanılabilen son çeyrek (yayım gecikmesi)."""
    hedef = m - YAYIM_GECIKME_AY
    q = hedef.asfreq("Q")
    return q - 1 if q.asfreq("M", "end") > hedef else q


def _aylik_acik(acik: pd.Series, aylar: pd.PeriodIndex, gecikmeli: bool) -> pd.Series:
    acik = acik.dropna()
    son_q = acik.index.max()
    vals = []
    for m in aylar:
        q = _rt_ceyrek(m) if gecikmeli else min(m.asfreq("Q"), son_q)
        vals.append(acik.get(q, np.nan))
    return pd.Series(vals, index=aylar)


def _taylor(r: float, pi: pd.Series, acik: pd.Series) -> pd.Series:
    return r + pi + KATSAYI_PI * (pi - PI_HEDEF) + KATSAYI_ACIK * acik


@lru_cache(maxsize=1)
def _taylor_cercevesi():
    enf = oo.oku("enflasyon_aylik")
    enf.index = pd.PeriodIndex(enf.index, freq="M")
    tufe = enf["tufe"]
    acik_q = cikti_acigi()
    aylar = pd.period_range(TAYLOR_ILK_AY, oo.CIPA_AY, freq="M")
    df = pd.DataFrame(index=aylar)
    df["pi_gercek"] = ((tufe / tufe.shift(12) - 1) * 100).reindex(aylar)
    df["pi_pka"] = enf["pka_12a"].reindex(aylar)
    df["acik_tam"] = _aylik_acik(acik_q["tam"], aylar, False)
    df["acik_gercek_zamanli"] = _aylik_acik(acik_q["gercek_zamanli"], aylar, True)
    bilesim = []
    for pk in ("gercek", "pka"):
        for ak in ("tam", "gercek_zamanli"):
            for r in R_YILDIZ:
                ad = f"i_{pk}_{ak}_r{int(r)}"
                df[ad] = _taylor(r, df[f"pi_{pk}"], df[f"acik_{ak}"])
                bilesim.append(ad)
    gcol = [c for c in bilesim if c.startswith("i_gercek")]
    pcol = [c for c in bilesim if c.startswith("i_pka")]
    df["bant_alt"] = df[bilesim].min(axis=1, skipna=True)
    df["bant_ust"] = df[bilesim].max(axis=1, skipna=True)
    df["bant_bilesim"] = df[bilesim].notna().sum(axis=1)
    df["bant_gercek_alt"], df["bant_gercek_ust"] = df[gcol].min(axis=1), df[gcol].max(axis=1)
    df["bant_pka_alt"], df["bant_pka_ust"] = df[pcol].min(axis=1), df[pcol].max(axis=1)
    f = oo.oku("fonlama_gunluk")
    aofm = f["aofm"].resample("MS").mean()
    aofm.index = pd.PeriodIndex(aofm.index, freq="M")
    pol_f = f["politika"].dropna().resample("MS").last()
    pol_f.index = pd.PeriodIndex(pol_f.index, freq="M")
    pol_e = oo.oku("em_politika_aylik")["tur"].dropna()
    pol_e.index = pd.PeriodIndex(pol_e.index, freq="M")
    gecis = pd.Period("2018-09", "M")
    politika = pd.concat([pol_e[pol_e.index < gecis], pol_f[pol_f.index >= gecis]]).sort_index()
    df["aofm"] = aofm.reindex(aylar)
    df["politika"] = politika.reindex(aylar)
    return df, bilesim, acik_q, f["politika"].dropna()


def _konum(x: pd.DataFrame, alt: str, ust: str) -> dict:
    a = x["aofm"] < x[alt]
    u = x["aofm"] > x[ust]
    return {"alt_pay": _f(a.mean()), "ic_pay": _f((~a & ~u).mean()), "ust_pay": _f(u.mean()),
            "aofm_eksi_alt_ort_puan": _f((x["aofm"] - x[alt]).mean()),
            "aofm_eksi_ust_ort_puan": _f((x["aofm"] - x[ust]).mean())}


def p3a() -> dict:
    df, bilesim, acik_q, _ = _taylor_cercevesi()
    tam = df.dropna(subset=["aofm"])
    tam = tam[tam["bant_bilesim"] == len(bilesim)]
    donem = {}
    for k, a, b, ad in DONEM_TAYLOR:
        x = tam.loc[pd.Period(a, "M"):pd.Period(b, "M")]
        if not len(x):
            continue
        donem[k] = {"ad": ad, "n": int(len(x)), "ilk": str(x.index.min()), "son": str(x.index.max()),
                    "tum_bant": _konum(x, "bant_alt", "bant_ust"),
                    "gercek_enflasyon_bandi": _konum(x, "bant_gercek_alt", "bant_gercek_ust"),
                    "pka_bandi": _konum(x, "bant_pka_alt", "bant_pka_ust"),
                    "bant_genislik_ort_puan": _f((x["bant_ust"] - x["bant_alt"]).mean())}
    m = oo.CIPA_AY
    s = df.loc[m]
    son = {"ay": str(m), "pi_gercek_yuzde": _f(s["pi_gercek"]), "pi_pka_yuzde": _f(s["pi_pka"]),
           "acik_tam_puan": _f(s["acik_tam"]), "acik_gercek_zamanli_puan": _f(s["acik_gercek_zamanli"]),
           "acik_tam_ceyrek": str(min(m.asfreq("Q"), acik_q["tam"].dropna().index.max())),
           "acik_gercek_zamanli_ceyrek": str(_rt_ceyrek(m)),
           "bilesimler_yuzde": {c[2:]: _f(s[c]) for c in bilesim},
           "bant_alt_yuzde": _f(s["bant_alt"]), "bant_ust_yuzde": _f(s["bant_ust"]),
           "bant_gercek_alt_yuzde": _f(s["bant_gercek_alt"]), "bant_gercek_ust_yuzde": _f(s["bant_gercek_ust"]),
           "bant_pka_alt_yuzde": _f(s["bant_pka_alt"]), "bant_pka_ust_yuzde": _f(s["bant_pka_ust"]),
           "aofm_ay_ort_yuzde": _f(s["aofm"]), "politika_ay_sonu_yuzde": _f(s["politika"]),
           "aofm_eksi_bant_alt_puan": _f(s["aofm"] - s["bant_alt"]),
           "aofm_eksi_bant_ust_puan": _f(s["aofm"] - s["bant_ust"]),
           "aofm_eksi_pka_bant_alt_puan": _f(s["aofm"] - s["bant_pka_alt"]),
           "aofm_eksi_pka_bant_ust_puan": _f(s["aofm"] - s["bant_pka_ust"]),
           "aofm_konum": ("bandın altında" if s["aofm"] < s["bant_alt"] else
                          "bandın üstünde" if s["aofm"] > s["bant_ust"] else "bandın içinde")}
    a = acik_q.dropna()
    a2 = a[a.index >= pd.Period("2005Q1", "Q")]
    fark = (a2["tam"] - a2["gercek_zamanli"]).abs()
    acik_ozet = {"n": int(len(a2)), "ilk": str(a2.index.min()), "son": str(a2.index.max()),
                 "korelasyon": _f(a2.corr().iloc[0, 1]),
                 "ort_mutlak_fark_puan": _f(fark.mean()), "azami_mutlak_fark_puan": _f(fark.max()),
                 "azami_fark_ceyrek": str(fark.idxmax()),
                 "isaret_uyum_pay": _f((np.sign(a2["tam"]) == np.sign(a2["gercek_zamanli"])).mean()),
                 "son_ceyrek": str(a.index.max()), "son_tam_puan": _f(a["tam"].iloc[-1]),
                 "son_gercek_zamanli_puan": _f(a["gercek_zamanli"].iloc[-1]),
                 "bir_onceki_ceyrek": str(a.index[-2]), "bir_onceki_tam_puan": _f(a["tam"].iloc[-2]),
                 "bir_onceki_gercek_zamanli_puan": _f(a["gercek_zamanli"].iloc[-2]),
                 "en_dusuk_tam_puan": _f(a["tam"].min()), "en_dusuk_tam_ceyrek": str(a["tam"].idxmin()),
                 "yontem": "Mevsim ve takvim etkisinden arındırılmış reel GSYH'nin logu HP süzgecinden (λ = 1600) "
                           "geçirildi; tam örneklem sürümü iki yanlı, gerçek zamanlı sürüm her çeyrekte yalnız o "
                           "güne kadarki veriyle süzülüp son noktası alındı (bugünkü veri sürümüyle; revizyon ölçülmez).",
                 "kaynak": ["gsyh_ceyreklik"]}
    once = df.loc[pd.Period("2013-01", "M"):pd.Period("2018-05", "M")].dropna(subset=["aofm", "politika"])
    repo_notu = {"n": int(len(once)), "ilk": str(once.index.min()), "son": str(once.index.max()),
                 "aofm_eksi_politika_ort_puan": _f((once["aofm"] - once["politika"]).mean()),
                 "aofm_eksi_politika_azami_puan": _f((once["aofm"] - once["politika"]).max()),
                 "azami_ay": str((once["aofm"] - once["politika"]).idxmax()),
                 "yontem": "Haziran 2018 öncesinde AOFM ile bir hafta vadeli repo arasındaki aylık fark; o dönemde etkin "
                           "fonlama faizi AOFM'dir.", "kaynak": ["fonlama_gunluk", "em_politika_aylik"]}
    dibs = oo.oku("dibs_egri_gunluk")
    r5 = dibs["r5y"].dropna()
    r5s = r5[r5.index > oo.CIPA_GUN - pd.Timedelta(days=365)]
    r_kiyas = {"tufex_r5y_son_yuzde": _f(r5.iloc[-1]), "tufex_r5y_son_etiket": _iso(r5.index[-1]),
               "tufex_r5y_son12ay_medyan_yuzde": _f(r5s.median()), "tufex_r5y_son12ay_n": int(len(r5s)),
               "tufex_r2y_son_yuzde": _f(dibs["r2y"].dropna().iloc[-1]),
               "not": "r* ölçülmez: 2 puan Taylor (1993) değeri, 0 ve 4 iki puanlık belirsizlik kenarıdır "
                      "(varsayım). Kıyas için piyasanın 5 yıllık reel getirisi verilir (TÜFEX, seyrek kotasyon)."}
    return {
        "yontem": "Kural faizi r* + π + 0,5(π − 5) + 0,5·açık iki enflasyon ölçüsü (gerçekleşen yıllık TÜFE, "
                  "PKA 12 ay sonrası beklentisi), iki çıktı açığı sürümü ve üç r* ile aylık hesaplandı; bant "
                  "on iki bileşimin en düşüğü ile en yükseğidir ve AOFM'nin aylık ortalamasıyla kıyaslandı.",
        "kaynak": ["enflasyon_aylik", "gsyh_ceyreklik", "fonlama_gunluk", "em_politika_aylik", "dibs_egri_gunluk"],
        "n": int(len(tam)), "ilk": str(tam.index.min()), "son": str(tam.index.max()),
        "parametreler": {"pi_hedef_yuzde": PI_HEDEF, "katsayi_pi": KATSAYI_PI, "katsayi_acik": KATSAYI_ACIK,
                         "r_yildiz_yuzde": list(R_YILDIZ), "hp_lambda": HP_LAMBDA,
                         "yayim_gecikmesi_ay": YAYIM_GECIKME_AY,
                         "yayim_gecikmesi_kural": "bir çeyreğin açığı çeyreğin son ayından üç ay sonra kullanılır "
                                                  "(Ağustos'ta 1. çeyrek, Eylül'de 2. çeyrek)",
                         "tam_ornek_kural": "ayın kendi çeyreği; veri bitmişse son çeyrek taşınır",
                         "politika_kaynak": "Eylül 2018'den fonlama politika faizi, öncesi BIS Türkiye politika "
                                            "faizi; ikisi de ay sonu"},
        "son_ay": son,
        "donemler": donem,
        "cikti_acigi": acik_ozet,
        "repo_etkin_degildi": repo_notu,
        "r_yildiz_kiyas": r_kiyas,
    }


def arac_taylor() -> dict:
    """Araç 1'in (Taylor kuralı) açılış girdileri."""
    df, _, _, pol = _taylor_cercevesi()
    s = df.loc[oo.CIPA_AY]
    acik = [_f(s["acik_tam"]), _f(s["acik_gercek_zamanli"])]
    kur = oo.oku("kuresel_aylik")
    fa = kur["faiz_abd"].dropna()
    at = kur["abd_tufe"].dropna()
    at_yy = ((at / at.shift(12) - 1) * 100).dropna()
    return {
        "ay": str(oo.CIPA_AY),
        "pi_gercek_yuzde": _f(s["pi_gercek"]), "pi_pka_yuzde": _f(s["pi_pka"]),
        "pi_hedef_yuzde": PI_HEDEF, "katsayi_pi": KATSAYI_PI, "katsayi_acik": KATSAYI_ACIK,
        "acik_tam_puan": acik[0], "acik_gercek_zamanli_puan": acik[1],
        "acik_alt_puan": min(acik), "acik_ust_puan": max(acik),
        "r_yildiz_yuzde": list(R_YILDIZ), "r_yildiz_varsayilan_yuzde": R_YILDIZ_VARSAYILAN,
        "aofm_ay_ort_yuzde": _f(s["aofm"]),
        "politika_yuzde": _f(pol.iloc[-1]), "politika_gun": _iso(pol.index[-1]),
        "yabanci": {"politika_abd_yuzde": _f(fa.iloc[-1]), "politika_abd_ay": str(fa.index[-1].to_period("M")),
                    "tufe_abd_yillik_yuzde": _f(at_yy.iloc[-1]), "tufe_abd_ay": str(at_yy.index[-1].to_period("M")),
                    "not": "ABD beklenti serisi arşivde yok; beklenen enflasyon yerine son yıllık TÜFE açılış "
                           "değeridir (araçta değiştirilebilir). ABD politika faizi BIS tanımıdır."},
        "yontem": "Aracın açılış değerleri çıpa ayının ölçümleridir; kural faizi ve beklenen reel faiz farkı "
                  "(B bloğu) araçta bu girdilerden hesaplanır.",
        "kaynak": ["enflasyon_aylik", "gsyh_ceyreklik", "fonlama_gunluk", "kuresel_aylik"],
    }


def sekil_03() -> dict:
    df, _, _, _ = _taylor_cercevesi()
    x = df.loc[pd.Period("2011-01", "M"):]
    kol = ["bant_alt", "bant_ust", "bant_gercek_alt", "bant_gercek_ust", "bant_pka_alt", "bant_pka_ust",
           "aofm", "politika", "pi_gercek", "pi_pka", "acik_tam", "acik_gercek_zamanli"]
    return {"baslik": "Türkiye Taylor bandı", "birim": "%, açık için puan", "siklik": "aylık",
            "tarih": [str(p) for p in x.index], **{k: _liste(x[k]) for k in kol},
            "donemler": [[a, b, ad] for _, a, b, ad in DONEM_TAYLOR],
            "not": "AOFM aylık ortalama, politika faizi ay sonu; 2013 öncesinde bant yalnız gerçekleşen "
                   "enflasyonla kurulur (PKA 2013'te başlar). Haziran 2018 öncesinde politika faizi etkin oran değildi."}


# ═══════════════════════════════════════════════════════════════ p3b
def _gurultu(seri: pd.Series, olaylar) -> dict:
    out = {}
    for k, a, b, ad in [("tum", "2016-01-01", str(oo.CIPA_GUN.date()), "2016–2026")] + DONEM_PPK:
        s = seri.loc[a:b].dropna()
        olay = s.loc[s.index.intersection(pd.DatetimeIndex(olaylar))]
        sakin = s.loc[sakin_gunler(s.index, olaylar)]
        if len(olay) < 3 or len(sakin) < 30:
            continue
        so, se = float(sakin.std()), float(olay.std())
        out[k] = {"ad": ad, "n_olay": int(len(olay)), "n_sakin": int(len(sakin)),
                  "sigma_sakin_bp": so, "sigma_olay_bp": se, "varyans_orani": (se / so) ** 2 if so else None,
                  "sakin_iki_sigma_ustu_olay_pay": _f((olay.abs() > 2 * so).mean())}
    return out


def anket_surprizi(ppk: pd.Series, beklenti: pd.DataFrame) -> pd.Series:
    """Karar − karar ayının PKA toplantı beklentisi (bp) (tuzak 7)."""
    b = beklenti["politika_beklenti"].dropna()
    b.index = pd.DatetimeIndex(b.index).to_period("M")
    vals = {t: (v - b[t.to_period("M")]) * 100 for t, v in ppk.items() if t.to_period("M") in b.index}
    return pd.Series(vals, name="anket_bp", dtype=float)


def _karar_degisimi(ppk: pd.Series) -> pd.Series:
    onceki = ppk.shift(1)
    onceki.loc[KARAR_ILK] = oo.oku("fonlama_gunluk").loc[KARAR_ILK, "aofm"]
    return ((ppk - onceki) * 100).loc[KARAR_ILK:].rename("karar_bp")


def _dagilim(s: pd.Series) -> dict:
    s = s.dropna()
    return {"n": int(len(s)), "sifir": int((s.abs() < 1).sum()), "pozitif": int((s >= 1).sum()),
            "negatif": int((s <= -1).sum()), "ort_bp": _f(s.mean()), "medyan_bp": _f(s.median()),
            "ort_mutlak_bp": _f(s.abs().mean()), "sd_bp": _f(s.std()),
            "en_buyuk": {"tarih": _iso(s.idxmax()), "bp": _f(s.max())} if len(s) else None,
            "en_kucuk": {"tarih": _iso(s.idxmin()), "bp": _f(s.min())} if len(s) else None}


def p3b() -> dict:
    ppk = oo.oku("ppk_kararlari")["politika"]
    olaylar = ppk.index
    hz = dibs_gecikme()
    deg = tr_gunluk_degisim()
    ev = deg.loc[deg.index.intersection(olaylar)]
    kaynak = ["ppk_kararlari", "dibs_egri_gunluk", "fonlama_gunluk", "usdtry_yahoo_gunluk", "usdtry_tcmb_gunluk",
              "bulut/evds_pka_toplanti"]

    # hiza: üç tarih sözleşmesinde plasebo kapısı
    saklı = tr_gunluk_degisim(0)
    tk = tr_takvim()
    dibs_ham = oo.oku("dibs_egri_gunluk")
    iki = {c: (dibs_ham[c].shift(-hz["gecikme_is_gunu"] - 1) - dibs_ham[c].shift(1 - hz["gecikme_is_gunu"]))
           .reindex(tk) * 100 for c in ("n3a", "n1y", "n2y", "n5y")}
    hiza = {"dibs_gecikme": hz,
            "kapi_sakli_tarih": {c: olay_kapisi(saklı[c], olaylar) for c in ("n3a", "n6a", "n1y", "n2y", "n5y")},
            "kapi_iki_gunluk": {c: olay_kapisi(iki[c], olaylar) for c in iki},
            "not": "DİBS değişimi ölçülen gecikme kadar öne alınarak piyasa gününe oturtuldu; iki günlük pencere "
                   "karar günü ile ertesi günün toplamıdır."}
    kapilar = {c: olay_kapisi(deg[c], olaylar) for c in ("n3a", "n6a", "n1y", "n2y", "n5y", "usdtry", "usdtry_tcmb")}
    gurultu = {c: _gurultu(deg[c], olaylar) for c in ("n3a", "n6a", "n1y")}

    # anket sürprizi (bulut)
    karar = _karar_degisimi(ppk)
    try:
        bek = bulut.pka_toplanti_beklentisi()
        ans = anket_surprizi(ppk, bek)
        seri_turu = bek["seri"].dropna().astype(str)
        seri_turu.index = pd.DatetimeIndex(seri_turu.index).to_period("M")
    except bulut.VeriYok as h:
        ans, seri_turu = None, None
        anket_hata = f"anketin toplantıya özgü faiz beklentisi elde yok ({h})"

    tepki = {}
    for hedef, birim in (("usdtry", "% / 100 bp anket sürprizi"), ("n2y", "bp / 100 bp anket sürprizi"),
                         ("n5y", "bp / 100 bp anket sürprizi")):
        if not kapilar[hedef]["gecti"]:
            tepki[hedef] = kurulmadi(_kapi_sebebi(kapilar[hedef]), kapi=kapilar[hedef])
            continue
        if ans is None:
            tepki[hedef] = kurulmadi(anket_hata)
            continue
        tepki[hedef] = {"birim": birim}
        x = (ans / 100).rename("anket_100bp")
        for k, a, b, ad in DONEM_PPK:
            e = ev.loc[a:b]
            r = regresyon(e[hedef], x.reindex(e.index))
            r["ad"] = ad
            if k == "yonetilen" and hedef == "usdtry":
                r["yonetilen_kur"] = True
                if r.get("t") is None or abs(r["t"]) < 2:
                    r["not"] = "kur yönetildiği için eğimin sıfırdan ayrışmaması tasarım gereğidir"
                else:
                    r["not"] = "yönetilen dönemde de eğim sıfırdan ayrışıyor"
            tepki[hedef][k] = r
        hm = ev.index[(ev.index < "2021-12-01") | (ev.index > "2023-06-30")]
        r = regresyon(ev.loc[hm, hedef], x.reindex(hm))
        r["ad"] = "2016–2026, yönetilen kur dönemi hariç (havuzlanmış; sağlamlık)"
        tepki[hedef]["yonetilen_haric"] = r
    if not kapilar["usdtry_tcmb"]["gecti"]:
        tepki["usdtry_tcmb"] = kurulmadi(
            _kapi_sebebi(kapilar["usdtry_tcmb"]), kapi=kapilar["usdtry_tcmb"],
            **{"not": "sağlamlık sınaması: TCMB gösterge kuru 15:30'da ilan edilir ve kararın kur tepkisinin "
                      "büyüğü 15:30'dan sonra geldiği için profil ertesi günde tepe yapıyor"})
    elif ans is not None:
        x = (ans / 100).rename("anket_100bp")
        hm = ev.index[(ev.index < "2021-12-01") | (ev.index > "2023-06-30")]
        tepki["usdtry_tcmb"] = {**regresyon(ev.loc[hm, "usdtry_tcmb"], x.reindex(hm)),
                                "ad": "sağlamlık: TCMB gösterge kuru, yönetilen kur dönemi hariç"}

    if ans is not None:
        a_d = {"tum": _dagilim(ans)}
        for k, a, b, ad in DONEM_PPK:
            a_d[k] = {"ad": ad, **_dagilim(ans.loc[a:b])}
        kd = pd.concat([karar, ans], axis=1, sort=True).dropna()
        kk = {"tum": regresyon(kd["anket_bp"], kd["karar_bp"])}
        kk["tum"]["ad"] = "2018-06…2026-07"
        for k, a, b, ad in DONEM_PPK:
            z = kd.loc[max(pd.Timestamp(a), KARAR_ILK):b]
            if len(z):
                kk[k] = {**regresyon(z["anket_bp"], z["karar_bp"]), "ad": ad}
        degisen = kd[kd["karar_bp"] != 0]
        anket = {
            "yontem": "Anket sürprizi, PPK kararı ile karar ayındaki Piyasa Katılımcıları Anketi'nin politika faizi "
                      "beklentisinin farkıdır (baz puan); Mayıs 2025'e kadar soru 'cari ay sonu bir hafta vadeli "
                      "repo', sonra 'ilk toplantı'dır.",
            "kaynak": ["ppk_kararlari", "bulut/evds_pka_toplanti"],
            "n": int(len(ans)), "ilk": _iso(ans.index.min()), "son": _iso(ans.index.max()),
            "soru": {"cari_ay_sonu_repo": int((seri_turu == "cari_ay_sonu_repo").sum()),
                     "ilk_toplanti": int((seri_turu == "ilk_toplanti").sum())},
            "eslesmeyen": [_iso(t) for t in ppk.index if t not in ans.index],
            "dagilim": a_d,
            "karar_ile": {"n": int(len(kd)), "ilk": _iso(kd.index.min()), "son": _iso(kd.index.max()),
                          "n_degisen": int(len(degisen)),
                          "degisen_kararda_sifir_surpriz_pay": _f((degisen["anket_bp"].abs() < 1).mean()),
                          "sabit_kararda_sifir_surpriz_pay": _f((kd.loc[kd["karar_bp"] == 0, "anket_bp"].abs() < 1).mean()),
                          "yon_uyum_pay": _f((np.sign(degisen["karar_bp"]) ==
                                              np.sign(degisen["anket_bp"]))[degisen["anket_bp"].abs() >= 1].mean()),
                          "regresyon": kk,
                          "yontem": "Anket sürprizi kararın politika faizinde yaptığı değişime (baz puan) Newey–West "
                                    "ile regresyonlandı; eğim değişimin beklenmeyen payıdır."},
            "erken_karar_kaniti": [{"tarih": _iso(t), "gun": int(t.day), "anket_bp": _f(ans[t])}
                                   for t in ans.index if t.day <= 12 and abs(ans[t]) >= 1],
        }
    else:
        anket = kurulmadi(anket_hata)

    # tanı: kapı düştüğü için yayımlanmaz
    tani = {"yayimlanmaz": True,
            "sebep": "DİBS düğümleri PPK günlerinde plasebo kapısını geçmedi; aşağıdaki sayılar yalnız tanıdır",
            "ima_anket_korelasyonu": {c: _f(pd.concat([ev[c], ans], axis=1, sort=True).dropna().corr().iloc[0, 1])
                                      for c in ("n3a", "n6a", "n1y", "n2y")} if ans is not None else None,
            "ima_ile_karar": regresyon(ev["n3a"], karar.reindex(ev.index)),
            "kur_ile_ima": {k: {**regresyon(ev.loc[a:b, "usdtry"], ev.loc[a:b, "n3a"]), "ad": ad}
                            for k, a, b, ad in DONEM_PPK}}

    tablo = ev[["n3a", "n6a", "n1y", "n2y", "n5y", "usdtry"]]
    return {
        "yontem": "Her PPK karar günü için DİBS düğümlerinin (etiketleri ölçülen gecikme kadar öne alınarak) ve "
                  "USD/TRY'nin aynı piyasa günündeki değişimi ölçüldü; önce plasebo kapısı soruldu, kur tepkisi "
                  "kararla anket beklentisinin farkına dönem dönem Newey–West ile regresyonlandı.",
        "kaynak": kaynak,
        "n": int(len(ev)), "ilk": _iso(ev.index.min()), "son": _iso(ev.index.max()),
        "saat": "Karar 14:00 TSİ; DİBS gösterge değerleri gün sonu (etiket bir iş günü geride, öne alındı); USD/TRY "
                "18.12.2023'ten İstanbul 18:00, öncesi Londra gece yarısı; TCMB gösterge kuru 15:30. Getiri ve kur "
                "aynı piyasa gününün değişimidir.",
        "hiza": hiza,
        "kapi": kapilar,
        "gurultu": gurultu,
        "ima_surprizi": kurulmadi("ima sürprizi (DİBS 3 aylık değişimi) PPK günlerinde plasebo kapısını geçmedi; "
                                  "sıradan gün gürültüsü karar günü sinyalinden büyük", kapi=kapilar["n3a"]),
        "tepki": tepki,
        "anket_surprizi": anket,
        "tani": tani,
        "olaylar": {"tarih": [_iso(t) for t in ev.index], "politika_yuzde": _liste(ppk.reindex(ev.index)),
                    "anket_bp": _liste(ans.reindex(ev.index)) if ans is not None else None,
                    **{f"d_{c}": _liste(tablo[c]) for c in tablo.columns},
                    "birim": "DİBS bp, kur log %"},
    }


# ═══════════════════════════════════════════════════════════════ p3c
@lru_cache(maxsize=1)
def haftalik_3c() -> pd.DataFrame:
    a = oo.oku("abd_hazine_gunluk")["us2"]
    d = oo.oku("bund_gunluk")["de2_par"]
    e = oo.oku("cnbc_kur_gunluk")["eur"]
    g = pd.concat([a, d, e], axis=1, sort=True).dropna()
    g = g[g.index.dayofweek < 5]
    h = g.groupby(g.index.to_period("W-FRI")).tail(1).copy()
    h["fark"] = h["us2"] - h["de2_par"]
    return h


def p3c() -> dict:
    h = haftalik_3c().copy()
    h["d_fark_10bp"] = h["fark"].diff() * 100 / 10
    h["d_eur"] = np.log(h["eur"]).diff() * 100
    donem = {}
    for k, a, b, ad in DONEM_3C:
        x = h.loc[a:b].dropna()
        if len(x) < 30:
            continue
        donem[k] = {"ad": ad, "n": int(len(x)), "ilk": _iso(x.index.min()), "son": _iso(x.index.max()),
                    "degisim": regresyon(x["d_eur"], x["d_fark_10bp"], ilk_pencere=52),
                    "degisim_korelasyon": _f(x[["d_fark_10bp", "d_eur"]].corr().iloc[0, 1]),
                    "seviye_korelasyon": _f(x[["fark", "eur"]].corr().iloc[0, 1]),
                    "seviye_ar1_fark": oo.ar1(x["fark"]), "seviye_ar1_eur": oo.ar1(x["eur"]),
                    "fark_ilk_puan": _f(x["fark"].iloc[0]), "fark_son_puan": _f(x["fark"].iloc[-1]),
                    "eur_ilk": _f(x["eur"].iloc[0]), "eur_son": _f(x["eur"].iloc[-1])}
    x = h.dropna()
    return {
        "yontem": "ABD ile Almanya 2 yıllık getirileri arasındaki farkın haftalık değişimi (10 baz puan birimi) ile "
                  "EUR/USD'nin haftalık log değişimi (%) dört dönemde Newey–West ile regresyonlandı; seviye "
                  "korelasyonu ayrıca verildi.",
        "kaynak": ["abd_hazine_gunluk", "bund_gunluk", "cnbc_kur_gunluk"],
        "n": int(len(x)), "ilk": _iso(x.index.min()), "son": _iso(x.index.max()),
        "birim": "eğim: EUR/USD % değişim / 10 bp fark değişimi; eksi işaret, ABD lehine açılan farkla doların "
                 "değer kazancıdır",
        "saat": "ABD Hazinesi par getirisi New York kapanışı, Bund Bundesbank günlük (Frankfurt), EUR/USD New York "
                "17:00; haftanın üç serinin birlikte bulunduğu son günü alınır. Avrupa getirisi New York öğleden "
                "sonrasını görmez.",
        "uyari": "Seviye korelasyonu sahte olabilir: iki seviye de birim köke yakın (birinci dereceden özilinti 1'e "
                 "yakın); ilişki değişimlerde sınanır.",
        "ilk_donem_notu": "CNBC kur arşivi 03.01.2000'de başlar; ilk dönem fiilen 2000–2007'dir.",
        "donemler": donem,
    }


def sekil_04() -> dict:
    h = haftalik_3c()
    return {"baslik": "ABD–Almanya 2 yıllık farkı ve EUR/USD", "siklik": "haftalık",
            "birim": "fark: puan; EUR/USD: düzey",
            "tarih": [_iso(t) for t in h.index], "fark_puan": _liste(h["fark"]),
            "eurusd": _liste(h["eur"]), "us2_yuzde": _liste(h["us2"]), "de2_yuzde": _liste(h["de2_par"]),
            "donemler": [[a, b, ad] for _, a, b, ad in DONEM_3C]}


# ═══════════════════════════════════════════════════════════════ p3d
def p3d() -> dict:
    out = {"yontem": "Yayım günlerinde ve olay penceresi dışındaki sıradan günlerde günlük değişimlerin varyansı ve "
                     "kovaryansı karşılaştırıldı; oran 1'in üstündeyse yayım günü bilgi taşır. Sayısal beklenti "
                     "olmadığı için sürpriz hesaplanmaz.",
           "kaynak": ["abd_hazine_gunluk", "cnbc_kur_gunluk", "dibs_egri_gunluk", "usdtry_yahoo_gunluk",
                      "bulut/bls_takvim", "bulut/tuik_takvim"]}
    try:
        g = bulut.abd_istihdam_gunleri()
        d = abd_gunluk_degisim()[["us2", "dolar"]]
        r = yayim_gunu_orani(d, g, [("us2", "dolar")],
                             [("tum", "2000-01-01", "2026-09-30", "2000–2026"),
                              ("d2000_2019", "2000-01-01", "2019-12-31", "2000–2019"),
                              ("d2020_2026", "2020-01-01", "2026-09-30", "2020–2026")])
        r["saat"] = "İstihdam 08:30 New York; ABD Hazinesi kapanışı ve CNBC 17:00 New York aynı günü içerir."
        r["birim"] = "us2 baz puan; dolar altı G10 kurunun eşit ağırlıklı log değişimi, %"
        out["abd_istihdam"] = r
    except bulut.VeriYok as h:
        out["abd_istihdam"] = kurulmadi(f"BLS istihdam yayım günleri elde yok ({h})")
    try:
        g = bulut.gsyh_gunleri()
        d = tr_gunluk_degisim()[["n2y", "n5y", "usdtry"]]
        r = yayim_gunu_orani(d, g, [("n2y", "usdtry")],
                             [("tum", "2013-01-01", "2026-09-30", "2013–2026"),
                              ("d2023_2026", "2023-07-01", "2026-09-30", "2023-07…2026-09")])
        r["saat"] = "GSYH 10:00 TSİ; DİBS gün sonu (etiket öne alındı) ve USD/TRY akşam kapanışı yayımı içerir."
        r["birim"] = "DİBS baz puan; USD/TRY log değişim, %"
        r["n_yayim"] = int(len(g))
        out["tr_gsyh"] = r
    except bulut.VeriYok as h:
        out["tr_gsyh"] = kurulmadi(f"TÜİK GSYH yayım günleri elde yok ({h})")
    return out


# ═══════════════════════════════════════════════════════════════ giriş
def olc() -> dict:
    return oo.yuvarla({
        "p3a": p3a(),
        "arac_taylor": arac_taylor(),
        "p3b": p3b(),
        "p3c": p3c(),
        "p3d": p3d(),
        "sekil_03": sekil_03(),
        "sekil_04": sekil_04(),
    }, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.time()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"süre {time.time() - t0:.1f} sn")
