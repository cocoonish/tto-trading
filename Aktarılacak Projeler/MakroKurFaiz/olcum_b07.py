#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BÖLÜM 7 — Reel efektif kur ve PPP: ölçümler.

YÖN. TCMB REDK'nin ARTIŞI TL'nin REEL DEĞER KAZANCIDIR (ders q'sunun tersi).
Bütün sapmalar log(REDK) cinsindendir; artı sapma "ortalamaya göre pahalı TL".

YARI ÖMÜR. ρ, ortalaması çıkarılmış log REDK'nin AR(1) katsayısıdır; yarı ömür
ln 0,5 / ln ρ ay. Küçük örneklemde OLS ρ aşağı yanlıdır (Andrews 1993), bu
yüzden nokta değil medyan-yansız kestirim ve %90 aralığı verilir; üst uç
1'e dayanırsa yarı ömrün üst sınırı SONSUZDUR ve öyle yazılır.

BENZETİM (inceleme 03.10.2026). Kestirici `ortak_olc.ar1_medyan_yansiz`ın
kendisidir (aynı ızgara, aynı çekiliş sırası; aynı tohum ve deneme sayısıyla
birebir aynı sonucu verir — `_egriler` yalnız özyinelemeyi C'de koşturur,
iki arındırmayı aynı yapay serilerden hesaplar ve eğriyi önbelleğe alır).
Deneme 400'den `BENZETIM_DENEME`ye çıktı, çünkü ρ 1'e bu kadar yakınken 400
seriyle nokta kestirim tohuma göre 12,6–24,7 yıl oynuyordu. KURAL: ana kestirim
tek sabit tohumla (`ANA_TOHUM`); benzetim aralığı aynı kestirimin `TOHUMLAR`daki
(ana tohum dahil) en küçük ve en büyük sonucudur. Benzetim eğrisi yalnız seri
uzunluğuna, arındırma biçimine, tohuma ve deneme sayısına bağlıdır, veriye bağlı
değildir: aynı uzunluktaki seriler AYNI yapay serilerle ters çevrilir (TCMB'nin
iki REDK'si ve BIS'in on dokuz ülkesi, 392 ay). Böylece TCMB ile BIS Türkiye
kestirimlerinin SIRASI her tohumda yalnız iki serinin kendi OLS ρ'sundan gelir
(`p7c.tr_tcmb_kiyas`); farkın büyüklüğü eğrinin eğimiyle tohumdan tohuma oynar.
Izgara noktaları bağımsız çekildiği için eğri yer yer monoton değildir (kısa
serilerde sık); ikili arama ancak ρ̂ eğriyi tek yerde kesiyorsa doğrudur, bu
yüzden her blok `ters_cevirme_tek_kesisim` bayrağını taşır.
SONSUZ: aylık ρ ≥ `SONSUZ_RHO` (0,9999) ise yarı ömür sonsuzdur (None); kural nokta
kestirime, iki uca, tohum aralığına, grup medyanına ve TCMB–BIS kıyasına AYNI uygulanır.

ADF. Sabitli Dickey–Fuller; gecikme sayısı 0…12 arasında Akaike ölçütüyle,
ortak örneklemde seçilir. Kritik değerler MacKinnon (2010) sabitli, N = 1
yanıt yüzeyinden: `kritik` asimptotik (β∞; %5 −2,86154, %10 −2,56677),
`kritik_sonlu` T = sınama regresyonunun gözlem sayısında
β∞ + β1/T + β2/T² + β3/T³. HÜKÜM sonlu örneklem eşiğiyle verilir
(`birim_kok_red_*_sonlu`, `hukum`); son eki olmayan bayraklar asimptotiktir.

BALASSA–SAMUELSON VEKİLİ İKİ TANE. (1) Hizmet/mal göreli fiyatı (TÜFE alt
endeksleri, 2005+). (2) TÜFE bazlı ile Yİ-ÜFE bazlı REDK'nin oranı (1994+):
TÜFE ticarete konu olmayan hizmetleri içerir, ÜFE büyük ölçüde ticarete konu
mallardır; iki reel kurun ayrışması bu yüzden göreli fiyat kanalının izidir.
Verimlilik bacağı ölçülmedi.

İSVİÇRE 2015 VAKASI. CNBC kurları ortak tanımdan okunur (`ortak_olc.cnbc_kur`:
hafta içi, bozuk kotasyon günleri çıkarılmış); 14–15.01.2015 o günlerden değil.

YUVARLAMA. Bu modül (ve Bölüm 9) altı ondalıkla yuvarlanır, öbürleri dört: ρ
1'e yakınken dördüncü ondalık yarı ömrü aylarla oynatır (ρ 0,985 → 45,9 ay,
0,9854 → 47,1 ay); yarı ömür ρ'dan yeniden hesaplanabilsin diye ρ altı ondalık
taşınır.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.signal import lfilter

import bulut
import ortak_olc as oo

DONEMLER = (("1994-01", "2001-12", "1994–2001 (sabit kura yakın rejim ve krizler)"),
            ("2002-01", "2017-12", "2002–2017 (dalgalı kur, enflasyon hedeflemesi)"),
            ("2018-01", "2026-08", "2018–2026 (yüksek oynaklık)"))
# MacKinnon (2010, Queen's Economics Department WP 1227), sabitli ADF, N = 1:
# kritik değer = β∞ + β1/T + β2/T² + β3/T³ (statsmodels `adfvalues.tau_c_2010` ile aynı tablo)
MACKINNON_2010_SABITLI = {"yuzde5": (-2.86154, -2.8903, -4.234, -40.040),
                          "yuzde10": (-2.56677, -1.5384, -2.809, 0.0)}
ADF_KRITIK = {k: v[0] for k, v in MACKINNON_2010_SABITLI.items()}      # asimptotik (T → ∞)
FAN_AY = 60
BIS_DM = ["US", "XM", "JP", "GB", "CH", "AU", "CA", "NO", "SE"]
BIS_EM = ["TR", "BR", "MX", "ZA", "IN", "ID", "PL", "HU", "CL", "KR"]

# Medyan-yansız kestirimin benzetim ayarı: TCMB (p7a) ve BIS kesiti (p7c) AYNI ayarı kullanır.
BENZETIM_DENEME = 4000
IZGARA = np.linspace(0.50, 1.0, 101)          # ortak_olc.ar1_medyan_yansiz'ın öntanımlı ızgarası
ANA_TOHUM = 20261002
TOHUMLAR = tuple(ANA_TOHUM + k for k in range(5))  # ilki ana tohum; aralık bu beşinin uçlarıdır
SONSUZ_RHO = 0.9999          # ρ bu değerde ve üstünde yarı ömür sonsuz sayılır (≈ 578 yıl; ızgara aralığı 0,005)
_SAYI_ADI = {2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz", 10: "on"}


def adf_kritik_sonlu(T: int) -> dict:
    """MacKinnon (2010) sabitli yanıt yüzeyi, T gözlemde."""
    return {k: float(b0 + b1 / T + b2 / T ** 2 + b3 / T ** 3)
            for k, (b0, b1, b2, b3) in MACKINNON_2010_SABITLI.items()}


def _adf_hukum(red: dict, red_sonlu: dict) -> str:
    """Hüküm sonlu örneklem eşiğiyle; asimptotik eşikte farklıysa adıyla söylenir (sayı içermez)."""
    def durum(d: str) -> str:
        if red_sonlu[d]:
            return "reddediliyor"
        return "yalnız asimptotik eşikle reddediliyor" if red[d] else "reddedilmiyor"
    d5, d10 = durum("yuzde5"), durum("yuzde10")
    if d5 == d10:
        return f"Birim kök %5'te de %10'da da {d5}."
    return f"Birim kök %10'da {d10}, %5'te {d5}."


def adf(y: pd.Series, azami_gecikme: int = 12) -> dict:
    """Sabitli ADF; gecikme AIC ile (ortak örneklem). Kritik değerler MacKinnon (2010):
    asimptotik ve T = regresyonun gözlem sayısında sonlu örneklem; hüküm sonlu örneklemle."""
    x = np.asarray(y.dropna(), dtype=float)
    dx = np.diff(x)
    n = len(dx)
    p = azami_gecikme
    Y = dx[p:]
    duzey = x[p:-1]
    gecik = np.column_stack([dx[p - j:n - j] for j in range(1, p + 1)]) if p else np.empty((len(Y), 0))
    en_iyi = None
    for k in range(0, p + 1):
        X = np.column_stack([np.ones(len(Y)), duzey] + ([gecik[:, :k]] if k else []))
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        e = Y - X @ b
        s2 = (e @ e) / (len(Y) - X.shape[1])
        aic = len(Y) * math.log((e @ e) / len(Y)) + 2 * X.shape[1]
        se = math.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
        aday = {"gecikme": k, "t": float(b[1] / se), "aic": aic}
        if en_iyi is None or aic < en_iyi["aic"]:
            en_iyi = aday
    t = en_iyi["t"]
    T = int(len(Y))
    sonlu = adf_kritik_sonlu(T)
    red = {k: bool(t < v) for k, v in ADF_KRITIK.items()}
    red_sonlu = {k: bool(t < v) for k, v in sonlu.items()}
    return {"t": t, "gecikme": en_iyi["gecikme"], "n": T, "kritik": dict(ADF_KRITIK),
            "birim_kok_red_yuzde5": red["yuzde5"], "birim_kok_red_yuzde10": red["yuzde10"],
            "kritik_sonlu": sonlu,
            "birim_kok_red_yuzde5_sonlu": red_sonlu["yuzde5"], "birim_kok_red_yuzde10_sonlu": red_sonlu["yuzde10"],
            "hukum_esigi": "sonlu örneklem", "hukum": _adf_hukum(red, red_sonlu)}


# ─────────────────────────────────────────────── medyan-yansız kestirim (benzetim)
@lru_cache(maxsize=None)
def _egriler(n: int, tohum: int, deneme: int) -> dict:
    """ρ ızgarasının her noktasında `deneme` yapay AR(1) serisi (durağan başlangıç, ρ = 1'de
    rastgele yürüyüş); her seri gözlenen seriyle AYNI biçimde arındırılır ('ortalama' ya da
    'egilim' = sabit + doğrusal eğilim) ve OLS ρ'su alınır. Dönen: arındırma başına medyan,
    5. ve 95. yüzdelik eğrileri. İki arındırma AYNI yapay serilerden hesaplanır (ayrı ayrı
    aynı tohumla koşturmakla birebir aynı sonuç, yarı süre). Çekiliş sırası
    `ortak_olc.ar1_medyan_yansiz`la aynıdır: 'ortalama' eğrileri aynı tohum ve deneme
    sayısında birebir aynıdır. Veriye bağlı değildir; önbelleklenir."""
    rng = np.random.default_rng(tohum)
    tc = np.arange(n, dtype=float)
    tc = tc - tc.mean()
    ttc = float(tc @ tc)
    egri = {a: ([], [], []) for a in ("ortalama", "egilim")}

    def ekle(a: str, y: np.ndarray) -> None:
        tah = np.einsum("ij,ij->i", y[:, 1:], y[:, :-1]) / np.einsum("ij,ij->i", y[:, :-1], y[:, :-1])
        med, q05, q95 = egri[a]
        med.append(np.median(tah)); q05.append(np.quantile(tah, 0.05)); q95.append(np.quantile(tah, 0.95))

    for r in IZGARA:
        e = rng.standard_normal((deneme, n))
        if r < 1:
            e[:, 0] = e[:, 0] / math.sqrt(max(1 - r * r, 1e-6))
        y = lfilter([1.0], [1.0, -r], e, axis=1)       # y_t = ρ y_{t−1} + e_t, y_0 = e_0
        y = y - y.mean(axis=1, keepdims=True)
        ekle("ortalama", y)
        ekle("egilim", y - ((y @ tc) / ttc)[:, None] * tc[None, :])
    return {a: tuple(np.array(v) for v in egri[a]) for a in egri}


def _ters(egri: np.ndarray, rho_hat: float) -> float:
    """Eğriyi (ızgarada artan) gözlenen ρ̂'da ters çevirir; doğrusal ara değer (ortak_olc ile aynı)."""
    if rho_hat <= egri[0]:
        return float(IZGARA[0])
    if rho_hat >= egri[-1]:
        return float(IZGARA[-1])
    j = int(np.searchsorted(egri, rho_hat))
    a, b = egri[j - 1], egri[j]
    return float(IZGARA[j - 1] + (rho_hat - a) / (b - a) * (IZGARA[j] - IZGARA[j - 1]))


def _tek_kesisim(egri: np.ndarray, rho_hat: float) -> bool:
    """Ters çevirme belirsiz mi? Bağımsız çekilen ızgara noktaları yüzünden eğri yer yer
    monoton değildir (kısa serilerde sık); `_ters`in ikili araması ancak ρ̂ eğriyi TEK yerde
    kesiyorsa (uçlara kırpılan hâlde HİÇ kesmiyorsa) doğru aralığı bulur."""
    lo, hi = np.minimum(egri[:-1], egri[1:]), np.maximum(egri[:-1], egri[1:])
    kesisim = int(np.sum((lo <= rho_hat) & (rho_hat <= hi)))
    icinde = egri[0] < rho_hat < egri[-1]
    return kesisim == 1 if icinde else kesisim == 0


def _rho_hat(x: np.ndarray, arindirma: str) -> float:
    if arindirma == "egilim":
        T = np.column_stack([np.ones(len(x)), np.arange(len(x))])
        r = x - T @ np.linalg.lstsq(T, x, rcond=None)[0]
        return float((r[1:] @ r[:-1]) / (r[:-1] @ r[:-1]))
    return oo.ar1(pd.Series(x))


def _yo(rho: float) -> float | None:
    """Yarı ömür (ay); ρ ≥ SONSUZ_RHO sonsuzdur (None). Kural nokta kestirime, iki uca, tohum
    aralığına ve grup medyanına AYNI uygulanır: son ızgara aralığında (0,995–1) doğrusal ara değerle
    bulunan 0,99996 gibi bir ρ yarı ömrü 1.350 yıl yazdırıyordu; üst uç aynı ρ'da sonsuz sayılırken
    nokta kestirimin sonlu sayılması, ızgara çözünürlüğünün altındaki bir farkı sayıya çeviriyordu."""
    return None if rho >= SONSUZ_RHO else oo.yari_omur(rho)


def medyan_yansiz(x, arindirma: str = "ortalama") -> dict:
    """Ana kestirim ANA_TOHUM'la; `tohumlar` her tohumdaki (ρ_mu, ρ_alt90, ρ_üst90)."""
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    n = len(x)
    rh = _rho_hat(x, arindirma)
    tohumlar, tek = [], True
    for t in TOHUMLAR:
        egriler = _egriler(n, t, BENZETIM_DENEME)[arindirma]
        med, q05, q95 = egriler
        tohumlar.append((_ters(med, rh), _ters(q95, rh), _ters(q05, rh)))   # q95'i tutturan ρ alt uçtur
        tek = tek and all(_tek_kesisim(e, rh) for e in egriler)
    mu, alt, ust = tohumlar[0]
    return {"n": int(n), "rho_ols": rh, "rho_mu": mu, "rho_alt90": alt, "rho_ust90": ust,
            "yo_ols": oo.yari_omur(rh), "yo_mu": _yo(mu), "yo_alt90": _yo(alt),
            "yo_ust90": _yo(ust), "ust_sonsuz": bool(ust >= SONSUZ_RHO), "tohumlar": tohumlar,
            "tek_kesisim": bool(tek)}


def _uc(degerler: list, bolen: float) -> tuple:
    """Yarı ömürlerin (ay; None = sonsuz) en küçüğü ve en büyüğü, `bolen`e bölünmüş; sonsuz None."""
    sonlu = [v for v in degerler if v is not None]
    en_kucuk = min(sonlu) / bolen if sonlu else None                       # hepsi sonsuzsa None
    en_buyuk = max(sonlu) / bolen if len(sonlu) == len(degerler) else None  # biri sonsuzsa None
    return en_kucuk, en_buyuk


def benzetim_araligi(mu: dict, ay: bool = True) -> dict:
    """Aynı kestirimin TOHUMLAR'daki en küçük/en büyük sonucu. Yarı ömür sonsuzsa (ρ_mu = 1)
    o uç None'dır ve sayısı yazılır; üst uç her tohumda 1'e dayanıyorsa `n_ust_sonsuz` tohum sayısıdır."""
    t = mu["tohumlar"]
    rmu = [a for a, _, _ in t]
    ralt = [b for _, b, _ in t]
    yo_mu = [_yo(v) for v in rmu]
    yo_alt = [_yo(v) for v in ralt]
    out = {"tohum_sayisi": len(t), "deneme": BENZETIM_DENEME,
           "rho_mu_min": min(rmu), "rho_mu_max": max(rmu),
           "n_mu_sonsuz": int(sum(v is None for v in yo_mu)),
           "rho_alt90_min": min(ralt), "rho_alt90_max": max(ralt),
           "n_ust_sonsuz": int(sum(c >= SONSUZ_RHO for _, _, c in t))}
    birimler = (("ay", 1.0), ("yil", 12.0)) if ay else (("yil", 12.0),)
    for ad, bolen in birimler:
        out[f"yari_omur_min_{ad}"], out[f"yari_omur_max_{ad}"] = _uc(yo_mu, bolen)
        out[f"yari_omur_alt90_min_{ad}"], out[f"yari_omur_alt90_max_{ad}"] = _uc(yo_alt, bolen)
    out["yari_omur_max_sonsuz"] = out["n_mu_sonsuz"] > 0
    # Her tohumda üç eğrinin (medyan, 5. ve 95. yüzdelik) üçü de gözlenen ρ̂'da belirsizsiz ters çevrildi mi
    out["ters_cevirme_tek_kesisim"] = mu["tek_kesisim"]
    return out


def _sonsuz_metin() -> str:
    return f"{SONSUZ_RHO:.4f}".replace(".", ",")


def benzetim_ayari() -> dict:
    """p7a ve p7c'nin ortak benzetim ayarı (aynı nesne iki blokta da yazılır)."""
    ad = _SAYI_ADI.get(len(TOHUMLAR), str(len(TOHUMLAR)))
    deneme = f"{BENZETIM_DENEME:,}".replace(",", ".")
    return {"deneme": BENZETIM_DENEME, "izgara_nokta": int(len(IZGARA)),
            "izgara_alt": float(IZGARA[0]), "izgara_ust": float(IZGARA[-1]),
            "ana_tohum": ANA_TOHUM, "aralik_tohumlari": list(TOHUMLAR),
            "sonsuz_rho": SONSUZ_RHO,
            "kural": (f"Izgaranın her noktasında {deneme} yapay seri. Ana kestirim tek ve sabit bir rastgele sayı "
                      f"tohumuyla kurulur; benzetim aralığı aynı kestirimin {ad} bağımsız tohumdaki (ana tohum "
                      "dahil) en küçük ve en büyük sonucudur. Yapay seriler veriye değil yalnız seri uzunluğuna, "
                      "arındırma biçimine ve tohuma bağlıdır; aynı uzunluktaki seriler her tohumda aynı yapay "
                      f"serilerle kestirilir. Aylık katsayı {_sonsuz_metin()} ve üstündeyse yarı ömür sonsuz "
                      "sayılır; kural nokta kestirime, %90 aralığının iki ucuna ve benzetim aralığına aynı "
                      "uygulanır.")}


def yari_omur_olc(s: pd.Series) -> dict:
    """Log seviye, ortalaması çıkarılmış: OLS ρ, medyan-yansız ρ ve %90 aralığı, benzetim aralığı, ADF."""
    ls = np.log(s.dropna())
    mu = medyan_yansiz(ls)
    out = {"n": mu["n"], "ilk": str(ls.index.min().date()), "son": str(ls.index.max().date()),
           "rho_ols": mu["rho_ols"], "rho_mu": mu["rho_mu"], "rho_alt90": mu["rho_alt90"],
           "rho_ust90": mu["rho_ust90"],
           "yari_omur_ols_ay": mu["yo_ols"], "yari_omur_mu_ay": mu["yo_mu"],
           "yari_omur_alt90_ay": mu["yo_alt90"], "yari_omur_ust90_ay": mu["yo_ust90"],
           "ust_sonsuz": mu["ust_sonsuz"], "adf": adf(ls)}
    for k in ("ols", "mu", "alt90", "ust90"):
        v = out[f"yari_omur_{k}_ay"]
        out[f"yari_omur_{k}_yil"] = None if v is None else v / 12
    out["benzetim_araligi"] = benzetim_araligi(mu, ay=True)
    return out


def mu_egilimli(ls: pd.Series) -> dict:
    """Doğrusal eğilimi çıkarılmış seride medyan-yansız ρ: benzetimde her yapay seri
    AYNI biçimde (sabit + eğilim) arındırılır, yoksa yanlılık düzeltmesi yanlış kalıba göre olur."""
    x = np.asarray(ls.dropna(), dtype=float)
    n = len(x)
    mu = medyan_yansiz(x, arindirma="egilim")
    T = np.column_stack([np.ones(n), np.arange(n)])
    egim = float(np.linalg.lstsq(T, x, rcond=None)[0][1]) * 12
    yil = (lambda v: None if v is None else v / 12)
    return {"n": n, "egilim_log_yil": egim, "rho_ols": mu["rho_ols"], "rho_mu": mu["rho_mu"],
            "rho_alt90": mu["rho_alt90"], "rho_ust90": mu["rho_ust90"],
            "yari_omur_mu_yil": yil(mu["yo_mu"]), "yari_omur_alt90_yil": yil(mu["yo_alt90"]),
            "yari_omur_ust90_yil": yil(mu["yo_ust90"]), "ust_sonsuz": mu["ust_sonsuz"],
            "benzetim_araligi": benzetim_araligi(mu, ay=False)}


def p7a() -> dict:
    r = oo.oku("redk_aylik")
    ay = benzetim_ayari()
    deneme = f"{BENZETIM_DENEME:,}".replace(",", ".")
    tohum_adi = _SAYI_ADI.get(len(TOHUMLAR), str(len(TOHUMLAR)))
    sonuc = {"yontem": ("Ortalaması çıkarılmış log reel efektif kurun birinci derece özbağlanım katsayısı. Küçük "
                        "örneklemde en küçük kareler katsayısı aşağı yanlı olduğu için medyan-yansız kestirim: "
                        f"0,50 ile 1,00 arasındaki {len(IZGARA)} noktalık ızgaranın her noktasında gözlenen seriyle "
                        f"aynı uzunlukta {deneme} yapay seri üretilir ve en küçük kareler kestirimlerinin medyanı "
                        "gözlenen katsayıya eşit olan değer ızgara noktaları arasında doğrusal ara değerle "
                        "bulunur; %90 aralığı aynı benzetimin 5. ve 95. yüzdeliklerinden. Ana kestirim tek ve "
                        "sabit bir rastgele sayı tohumuyla kurulur; benzetim aralığı aynı kestirimin "
                        f"{tohum_adi} bağımsız tohumdaki (ana tohum dahil) en küçük ve en büyük sonucudur. "
                        f"Aylık katsayı {_sonsuz_metin()} ve üstündeyse yarı ömür sonsuz sayılır. Eğilimden arındırılmış kestirimde yapay seriler de aynı biçimde (sabit ve "
                        "doğrusal eğilim) arındırılır. Birim kök için sabitli genişletilmiş Dickey–Fuller "
                        "sınaması, gecikme 0–12 arasında Akaike ölçütüyle; kritik değerler MacKinnon (2010) yanıt "
                        "yüzeyinden: asimptotik değerin yanında sınama regresyonunun gözlem sayısına göre sonlu "
                        "örneklem değeri. Hüküm sonlu örneklem eşiğiyle verilir."),
              "kaynak": ["redk_aylik (TCMB, 2025=100; artış TL'nin reel değer kazancı)"],
              "benzetim": ay}
    for sut, ad in (("redk_tufe", "tufe"), ("redk_ufe", "ufe")):
        tam = yari_omur_olc(r[sut])
        alt = {}
        for bas, son, etiket in DONEMLER:
            a = yari_omur_olc(r[sut].loc[bas:son])
            a["etiket"] = etiket
            alt[f"{bas[:4]}_{son[:4]}"] = a
        egilimli = mu_egilimli(np.log(r[sut].dropna()))
        sonuc[ad] = {"tam": tam, "donemler": alt, "egilimden_arindirilmis": egilimli}
    # Bugünkü sapma: tam örneklem ve 2003+ ortalamasına göre
    ls = np.log(r["redk_tufe"].dropna())
    son = ls.index.max()
    sonuc["sapma"] = {
        "tarih": str(son.date()), "redk_tufe": float(r["redk_tufe"].loc[son]),
        "sapma_tam_log": float(ls.loc[son] - ls.mean()),
        "sapma_2003_log": float(ls.loc[son] - ls.loc["2003":].mean()),
        "yuzdelik_tam": float((ls <= ls.loc[son]).mean() * 100),
        "ortalama_tam_endeks": float(math.exp(ls.mean())),
        "ortalama_2003_endeks": float(math.exp(ls.loc["2003":].mean())),
    }
    return sonuc


def p7b() -> dict:
    e = oo.oku("enflasyon_aylik")
    r = oo.oku("redk_aylik")
    gf = np.log(e["hizmet"] / e["mallar"]).dropna()
    t = (gf.index - gf.index[0]).days / 365.25
    egim = oo.hac(gf.values, np.asarray(t))
    q = np.log(r["redk_tufe"]).dropna()
    d12_gf = gf.diff(12)
    d12_q = q.diff(12).reindex(d12_gf.index)
    birlik = pd.concat([d12_gf.rename("gf"), d12_q.rename("q")], axis=1).dropna()
    # Örtüşen 12 aylık farklar: HAC gecikmesi ufkun üstünde tutulur.
    reg = oo.hac(birlik["q"].values, birlik["gf"].values, gecikme=18)
    oran = np.log(r["redk_tufe"] / r["redk_ufe"]).dropna()
    t2 = (oran.index - oran.index[0]).days / 365.25
    egim2 = oo.hac(oran.values, np.asarray(t2))
    return {
        "yontem": ("Hizmet fiyatlarının mal fiyatlarına oranının ve TÜFE bazlı reel kurun Yİ-ÜFE bazlı reel "
                   "kura oranının logaritmik eğilimi (yıllık), ve göreli fiyatın 12 aylık değişiminin reel "
                   "kurun 12 aylık değişimiyle ilişkisi."),
        "kaynak": ["enflasyon_aylik (hizmet, mallar)", "redk_aylik"],
        "goreli_fiyat": {"ilk": str(gf.index.min().date()), "son": str(gf.index.max().date()), "n": int(len(gf)),
                         "toplam_degisim_log": float(gf.iloc[-1] - gf.iloc[0]),
                         "toplam_degisim_yuzde": float((math.exp(gf.iloc[-1] - gf.iloc[0]) - 1) * 100),
                         "egim_log_yil": egim["b"][1], "egim_t": egim["t"][1]},
        "reel_kur_iliskisi": {"n": reg["n"], "egim": reg["b"][1], "t": reg["t"][1], "r2": reg["r2"],
                              "gecikme": reg["gecikme"],
                              "ilk": str(birlik.index.min().date()), "son": str(birlik.index.max().date())},
        "tufe_ufe_reel_kur_orani": {"ilk": str(oran.index.min().date()), "son": str(oran.index.max().date()),
                                    "n": int(len(oran)),
                                    "toplam_degisim_log": float(oran.iloc[-1] - oran.iloc[0]),
                                    "egim_log_yil": egim2["b"][1], "egim_t": egim2["t"][1]},
        "sinir": "Verimlilik bacağı (ticarete konu sektörde göreli verimlilik artışı) ölçülmedi.",
    }


def p7c() -> dict:
    try:
        df = bulut.bis_reer("R")
    except bulut.VeriYok as e:
        return oo.kurulmadi(str(e))
    out = {"yontem": ("BIS geniş reel efektif kurlarında (aylık) ülke başına medyan-yansız yarı ömür. Benzetim "
                      "ayarı TCMB serisininkiyle aynıdır: aynı ızgara, aynı deneme sayısı, aynı tohum kuralı. "
                      "Grup medyanında sonsuz yarı ömür düşürülmez; benzetim aralığı grup medyanının her tohumda "
                      "yeniden hesaplanmış en küçük ve en büyük değeridir."),
           "kaynak": ["BIS WS_EER (reel, geniş)"], "benzetim": benzetim_ayari(), "ulkeler": {}}
    tohumlu = {}          # ülke → her tohumda (yarı ömür_mu ay | None, yarı ömür_alt90 ay | None)
    for ulke in BIS_DM + BIS_EM:
        if ulke not in df.columns:
            out["ulkeler"][ulke] = oo.kurulmadi("BIS dosyasında yok")
            continue
        s = df[ulke].dropna()
        mu = medyan_yansiz(np.log(s))
        tohumlu[ulke] = mu
        out["ulkeler"][ulke] = {"grup": "DM" if ulke in BIS_DM else "EM", "n": mu["n"],
                                "ilk": str(s.index.min().date()), "son": str(s.index.max().date()),
                                "rho_ols": mu["rho_ols"], "rho_mu": mu["rho_mu"], "rho_alt90": mu["rho_alt90"],
                                "yari_omur_mu_yil": None if mu["yo_mu"] is None else mu["yo_mu"] / 12,
                                "yari_omur_alt90_yil": None if mu["yo_alt90"] is None else mu["yo_alt90"] / 12,
                                "ust_sonsuz": mu["ust_sonsuz"],
                                "benzetim_araligi": benzetim_araligi(mu, ay=False)}

    def grup_ozeti(uyeler: list, k: int) -> tuple:
        # Sonsuz yarı ömür (ρ_mu = 1) medyandan DÜŞÜRÜLMEZ: düşürülse medyan aşağı yanlı olur.
        yo = [_yo(tohumlu[u]["tohumlar"][k][0]) for u in uyeler]
        mu = [math.inf if v is None else v / 12 for v in yo]
        alt = [_yo(tohumlu[u]["tohumlar"][k][1]) for u in uyeler]
        alt = [v / 12 for v in alt if v is not None]
        med = float(np.median(mu)) if mu else None
        return (med, float(np.median(alt)) if alt else None, int(sum(1 for v in mu if math.isinf(v))))

    for g in ("DM", "EM"):
        uyeler = [u for u in (BIS_DM if g == "DM" else BIS_EM) if u in tohumlu]
        med, alt, n_sonsuz = grup_ozeti(uyeler, 0)
        kume = [grup_ozeti(uyeler, k) for k in range(len(TOHUMLAR))]
        meds = [m for m, _, _ in kume if m is not None]
        sonlu = [m for m in meds if not math.isinf(m)]
        alts = [a for _, a, _ in kume if a is not None]
        out[g.lower()] = {"n": len(uyeler), "n_mu_sonsuz": n_sonsuz,
                          "medyan_mu_yil": None if (med is None or math.isinf(med)) else med,
                          "medyan_mu_sonsuz": bool(med is not None and math.isinf(med)),
                          "medyan_alt90_yil": alt,
                          "benzetim_araligi": {
                              "tohum_sayisi": len(TOHUMLAR), "deneme": BENZETIM_DENEME,
                              "medyan_mu_min_yil": min(sonlu) if sonlu else None,
                              "medyan_mu_max_yil": max(sonlu) if len(sonlu) == len(meds) and sonlu else None,
                              "medyan_mu_sonsuz_tohum_sayisi": int(sum(1 for m in meds if math.isinf(m))),
                              "medyan_alt90_min_yil": min(alts) if alts else None,
                              "medyan_alt90_max_yil": max(alts) if alts else None,
                              "n_mu_sonsuz_min": min(n for _, _, n in kume),
                              "n_mu_sonsuz_max": max(n for _, _, n in kume)}}

    # TCMB TÜFE bazlı REDK ile BIS Türkiye: aynı uzunluktaysa her tohumda aynı yapay serilerle kestirilir.
    if "TR" in tohumlu:
        tcmb = medyan_yansiz(np.log(oo.oku("redk_aylik")["redk_tufe"].dropna()))
        bis = tohumlu["TR"]
        ayni = tcmb["n"] == bis["n"]
        yo_t = [_yo(m) for m, _, _ in tcmb["tohumlar"]]
        yo_b = [_yo(m) for m, _, _ in bis["tohumlar"]]
        farklar = [None if (a is None or b is None) else (a - b) / 12 for a, b in zip(yo_t, yo_b)]
        sonlu = [f for f in farklar if f is not None]
        out["tr_tcmb_kiyas"] = {
            "ayni_uzunluk": bool(ayni), "n_tcmb": tcmb["n"], "n_bis": bis["n"],
            "tcmb_rho_ols": tcmb["rho_ols"], "bis_rho_ols": bis["rho_ols"],
            "tcmb_rho_mu": tcmb["rho_mu"], "bis_rho_mu": bis["rho_mu"],
            "tcmb_yari_omur_mu_yil": None if yo_t[0] is None else yo_t[0] / 12,
            "bis_yari_omur_mu_yil": None if yo_b[0] is None else yo_b[0] / 12,
            "tcmb_yari_omur_alt90_yil": None if tcmb["yo_alt90"] is None else tcmb["yo_alt90"] / 12,
            "bis_yari_omur_alt90_yil": None if bis["yo_alt90"] is None else bis["yo_alt90"] / 12,
            "fark_yil": farklar[0], "fark_min_yil": min(sonlu) if sonlu else None,
            "fark_max_yil": max(sonlu) if len(sonlu) == len(farklar) and sonlu else None,
            "tcmb_uzun_tohum_sayisi": int(sum(1 for a, b in zip(yo_t, yo_b)
                                              if (a is None and b is not None) or
                                              (a is not None and b is not None and a > b))),
            "tohum_sayisi": len(TOHUMLAR), "deneme": BENZETIM_DENEME,
            "not": ("İki seri aynı uzunlukta olduğu için her tohumda aynı yapay serilerle kestirilir: hangisinin "
                    "daha kalıcı çıktığı benzetimden değil iki serinin kendi en küçük kareler katsayısından "
                    "gelir. Farkın büyüklüğü yine de tohuma göre değişir: ρ 1'e bu kadar yakınken küçük bir "
                    "katsayı farkı yıllarca yarı ömür farkı eder ve bu çeviri benzetime duyarlıdır.") if ayni else
                   ("İki seri farklı uzunlukta olduğu için ayrı yapay serilerle kestirilir; fark benzetimden "
                    "de gelebilir.")}
    return out


def vakalar() -> dict:
    r = oo.oku("redk_aylik")["redk_tufe"]
    out = {}
    for yil in (2021, 2023):
        alt = r.loc[str(yil)]
        dip = alt.idxmin()
        sonra = r.loc[dip + pd.DateOffset(months=12)] if (dip + pd.DateOffset(months=12)) in r.index else None
        out[f"tr_dip_{yil}"] = {"tarih": str(dip.date()), "redk_tufe": float(alt.min()),
                               "sonraki_12ay_redk": None if sonra is None else float(sonra),
                               "sonraki_12ay_degisim_yuzde": None if sonra is None else float((sonra / alt.min() - 1) * 100)}
    k = oo.cnbc_kur()
    eurchf = (k["eur"] * k["chf"]).dropna()          # EUR/USD × USD/CHF = EUR/CHF
    usdchf = k["chf"].dropna()
    g0, g1 = pd.Timestamp("2015-01-14"), pd.Timestamp("2015-01-15")
    out["isvicre_2015"] = {
        "tarih": "2015-01-15", "saat": "New York 17:00 kapanışları (CNBC)",
        "eurchf_once": float(eurchf.loc[g0]), "eurchf_sonra": float(eurchf.loc[g1]),
        "eurchf_degisim_yuzde": float((eurchf.loc[g1] / eurchf.loc[g0] - 1) * 100),
        "usdchf_degisim_yuzde": float((usdchf.loc[g1] / usdchf.loc[g0] - 1) * 100),
    }
    return out


def sekil_12(a: dict) -> dict:
    r = oo.oku("redk_aylik")["redk_tufe"].dropna()
    ls = np.log(r)
    ort = ls.mean()
    son = ls.index.max()
    sapma = float(ls.loc[son] - ort)
    tam = a["tufe"]["tam"]
    gelecek = pd.date_range(son, periods=FAN_AY + 1, freq="MS")
    yollar = {}
    for ad, rho in (("mu", tam["rho_mu"]), ("alt90", tam["rho_alt90"]), ("ust90", tam["rho_ust90"])):
        h = np.arange(FAN_AY + 1)
        yollar[ad] = [float(math.exp(ort + sapma * rho ** k)) for k in h]
    return {"n": int(len(r)), "ilk": str(r.index.min().date()), "son": str(son.date()),
            "yontem": "TCMB TÜFE bazlı reel efektif kur (aylık) ve tam örneklem log ortalaması; fan, bugünkü "
                      "sapmanın medyan-yansız ρ ve %90 aralığının iki ucuyla ρ^h söndüğü yoldur.",
            "kaynak": ["redk_aylik"], "fan_n": int(FAN_AY + 1),
            "tarih": [str(t.date()) for t in r.index], "redk_tufe": [float(v) for v in r.values],
            "ortalama_endeks": float(math.exp(ort)),
            "fan_tarih": [str(t.date()) for t in gelecek], "fan": yollar,
            "not": "Fan, bugünkü sapmanın ρ^h ile söndüğü yoldur; tahmin değil, kestirilen kalıcılığın görselidir."}


def arac_redk(a: dict) -> dict:
    tam = a["tufe"]["tam"]
    s = a["sapma"]
    rho = tam["rho_mu"]
    beklenen12 = (rho ** 12 - 1) * s["sapma_tam_log"]
    return {"sapma_log": s["sapma_tam_log"], "rho_aylik": rho, "rho_alt90": tam["rho_alt90"],
            "rho_ust90": tam["rho_ust90"],
            "beklenen_12ay_log": beklenen12,
            "beklenen_12ay_yuzde": (math.exp(beklenen12) - 1) * 100,
            "n": tam.get("n"), "ilk": tam.get("ilk"), "son": tam.get("son"),
            "yontem": ("Bugünkü reel kur sapması, medyan-yansız aylık kalıcılık katsayısının on ikinci kuvvetiyle "
                       "bir yıl ileri taşındı: beklenen değişim (ρ¹² − 1) × sapma."),
            "kaynak": a.get("kaynak"),
            "aciklama": ("Artı sapma ortalamaya göre pahalı TL'dir; ρ<1 ise beklenen yol reel değer "
                         "kaybıdır (REDK düşer). Bu bir çekim terimidir, yön ve zamanlama tahmini değildir.")}


def olc() -> dict:
    a = p7a()
    return oo.yuvarla({"p7a": a, "p7b": p7b(), "p7c": p7c(), "vakalar": vakalar(),
                       "sekil_12": sekil_12(a), "arac_redk": arac_redk(a)}, 6)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps({k: v for k, v in d.items() if k != "sekil_12"}, ensure_ascii=False, indent=1, allow_nan=False)[:6000])
    print(f"süre {time.monotonic() - t0:.1f} sn")
