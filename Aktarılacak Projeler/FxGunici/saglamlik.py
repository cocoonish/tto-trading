#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sağlamlık: deflated Sharpe, aynı saatlerde rastgele yön, walk-forward, koşul kovaları.

DEFLATED SHARPE (Bailey & López de Prado, 2014). N parametre kombinasyonu
denenip en iyisi seçildiyse, en iyinin Sharpe'ı şansla da yüksek çıkar.
Beklenen azami Sharpe (gerçek kenar sıfırken):
    SR₀ = √V · [(1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))],  γ ≈ 0,5772
(V: denemelerin Sharpe'larının varyansı). Seçilen Sharpe'ın bunu aşma olasılığı
    DSR = Φ( (SR − SR₀)·√(T − 1) / √(1 − γ₃·SR + (γ₄ − 1)/4·SR²) )
(T gözlem; γ₃ çarpıklık, γ₄ basıklık; SR'ler yıllıklandırılmamış, günlük).
DSR ≥ 0,95 "seçim etkisinden arındırılınca da anlamlı" demektir.

İKİ EŞİK. Formülün V'si denemelerin KESİTSEL varyansıdır (Bailey ve López de Prado'nun
tanımı) ve bütün denemelerin gerçek Sharpe'ı sıfırken o varyans yalnız tahmin
gürültüsüdür. Izgaralarımızda kombinasyonlar gerçekten farklıdır (maliyet bazılarını
sistematik olarak eksiye iter); kesitsel varyans o farkları da taşır ve eşik şişer.
Bu yüzden ikinci eşik de yazılır: V₀ = 1/(T − 1), sıfır kenarlı bir Sharpe tahmininin
örnekleme varyansı — "N deneme yalnız şansla ne kadar yüksek bir en iyi üretirdi".
Hüküm kuralı ikisini de kullanmaz; ikisi de bilgi olarak basılır.

RASTGELE YÖN. Stratejinin AYNI giriş dakikaları, aynı risk uzaklığı ve aynı
çıkış kuralıyla (stop ve hedef ters yönde aynı uzaklıkta; zaman çıkışı aynı
dakikada), yalnız YÖN yazı turayla seçilir; 1000 tekrarın ortalama R
dağılımında gerçek ortalamanın yüzdeliği. Ters işlem kendi stop ve hedefiyle
yeniden simüle edildiği için çıkış dakikası çoğu zaman gerçek işleminkinden
farklıdır; ters koşuda tek pozisyon kuralı yoktur (aynı giriş kümesi). Zamanlamanın
ve oynaklığın getirdiği her şey iki tarafta da vardır; fark yalnız yönü seçmenin
değeridir. 20 işlemin altında sınama koşmaz.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

import metrik as mk
import motor as mt
from gunluk import Baglam

EULER = 0.5772156649015329
#: Rastgele yön sınamasının asgari işlem sayısı: altında sınama koşmaz ve kural "çalışıyor" diyemez.
ASGARI_RASTGELE = 20
#: Koşul analizinde "tuttu" hükmünün örneklem dışında seçilen kovalarda istediği asgari işlem sayısı.
ASGARI_KOSUL_OOS = 20


def dsr(sr_secilen: float, sr_denemeler: np.ndarray, gunluk: np.ndarray) -> dict:
    """Günlük (yıllıklandırılmamış) Sharpe'larla deflated Sharpe; iki eşikle (modülün başlığı)."""
    gunluk = np.asarray(gunluk, dtype=np.float64)
    T = len(gunluk)
    if T < 30:
        return dsr_ozetten(sr_secilen, sr_denemeler, T, float("nan"), float("nan"))
    return dsr_ozetten(sr_secilen, sr_denemeler, T, float(stats.skew(gunluk)),
                       float(stats.kurtosis(gunluk, fisher=False)))


def dsr_ozetten(sr_secilen: float, sr_denemeler: np.ndarray, T: int, g3: float, g4: float) -> dict:
    """Aynı deflated Sharpe, günlük serinin kendisi yerine özetinden (gözlem sayısı, çarpıklık, basıklık): ölçüm
    dosyası seçilenin bu üç sayısını taşır, yani deneme kümesi değişince (ör. ailenin bütün ızgarası) koşu yeniden
    yapılmadan kurulur."""
    sr_denemeler = np.asarray([x for x in sr_denemeler if np.isfinite(x)])
    N = len(sr_denemeler)
    if N < 2 or T < 30 or not np.isfinite(sr_secilen):
        return {"dsr": float("nan"), "psr": float("nan"), "sr0": float("nan"), "n_deneme": N}
    carpan = (1 - EULER) * stats.norm.ppf(1 - 1.0 / N) + EULER * stats.norm.ppf(1 - 1.0 / (N * math.e))
    V = float(np.var(sr_denemeler, ddof=1))
    sr0 = math.sqrt(V) * carpan
    sr0_g = math.sqrt(1.0 / (T - 1)) * carpan
    payda = math.sqrt(max(1e-12, 1 - g3 * sr_secilen + (g4 - 1) / 4.0 * sr_secilen ** 2))
    z_dsr = (sr_secilen - sr0) * math.sqrt(T - 1) / payda
    z_dsr_g = (sr_secilen - sr0_g) * math.sqrt(T - 1) / payda
    z_psr = sr_secilen * math.sqrt(T - 1) / payda
    yil = math.sqrt(mk.YIL_GUN)
    return {"dsr": float(stats.norm.cdf(z_dsr)), "psr": float(stats.norm.cdf(z_psr)),
            "sr0_yillik": float(sr0 * yil), "n_deneme": N, "T": int(T),
            "dsr_gurultu": float(stats.norm.cdf(z_dsr_g)), "sr0_gurultu_yillik": float(sr0_g * yil),
            "sr_yillik": float(sr_secilen * yil),
            "deneme_sr_ust_yillik": float(np.max(sr_denemeler) * yil),
            "deneme_sr_alt_yillik": float(np.min(sr_denemeler) * yil),
            "deneme_sr_sd_yillik": float(math.sqrt(V) * yil),
            "carpiklik": g3, "basiklik": g4}


def psr_tek(sr: float, gunluk: np.ndarray) -> dict:
    """Tek deneme (önceden kayıtlı varsayılan): seçim yoktur, deflated Sharpe probabilistic Sharpe'a eşittir ve
    iki eşik de tanımsızdır (beklenen azami Sharpe N = 1'de sıfırdır; gürültü eşiği N ≥ 2 ister)."""
    T = len(gunluk)
    if T < 30 or not np.isfinite(sr):
        return {"dsr": float("nan"), "psr": float("nan"), "n_deneme": 1, "sr0_yillik": 0.0,
                "dsr_gurultu": None, "sr0_gurultu_yillik": None}
    g3 = float(stats.skew(gunluk))
    g4 = float(stats.kurtosis(gunluk, fisher=False))
    payda = math.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2))
    psr = float(stats.norm.cdf(sr * math.sqrt(T - 1) / payda))
    return {"dsr": psr, "psr": psr, "n_deneme": 1, "T": int(T), "sr0_yillik": 0.0,
            "dsr_gurultu": None, "sr0_gurultu_yillik": None, "sr_yillik": float(sr * math.sqrt(mk.YIL_GUN)),
            "carpiklik": g3, "basiklik": g4}


def rastgele_yon(b: Baglam, isl: pd.DataFrame, tf: int, ofset: int | None, kayma_pip: float,
                 haber_kayma_pip: float, tekrar: int = 1000, tohum: int = 11) -> dict:
    """Aynı giriş dakikası, aynı R uzaklığı, ters yön → yazı tura karışımı.

    `ofset=None`: mum çıpası işlem başına (haber stratejileri); kapanış stop'unun
    sorulduğu mum sonu her işlemin kendi çıpasından okunur.
    """
    cift = _ayni_ters(b, isl, tf, ofset, kayma_pip, haber_kayma_pip)
    if cift is None:
        return {"yuzdelik": float("nan"), "ort": float("nan"), "p95": float("nan")}
    return _karisim(*cift, tekrar, tohum)


#: Yüzdeliğin duyarlılığı bu yüzdelikten itibaren ölçülür (eşiğin beş puan altı: geçenler ve eşiğe yakın kalanlar).
#: Tohum listesi sınır uçlarınınkiyle aynıdır (metrik.SINIR_TOHUM_TABAN + 0 … SINIR_TOHUM − 1): ikisi tek tanımdan
#: okunur.
DUYARLILIK_TABAN = 90.0
#: Kuyruk duyarlılığında çıkarılan en iyi işlem sayıları.
DUYARLILIK_EN_IYI = (1, 3)


def rastgele_duyarlilik(b: Baglam, isl: pd.DataFrame, tf: int, ofset: int | None, kayma_pip: float,
                        haber_kayma_pip: float, esik: float, tekrar: int = 1000, tohum: int = 11) -> dict:
    """Rastgele yön yüzdeliğinin iki duyarlılığı (bilgi; hüküm önceden kayıtlı tohumla verilir):

      haric_<k>   en iyi k işlem (net R'ye göre) çıkarılınca aynı tohumla yüzdelik: geçiş tek işleme mi bağlı
      tohum_pay   aynı yordam SINIR_TOHUM farklı tohumla koşunca yüzdeliğin eşiği geçme payı; medyan, en düşük, en
                  yüksek. Pay %5–95 arasındaysa "sınırda": eşiğin hangi yanında kaldığı tohum gürültüsüne bağlıdır."""
    cift = _ayni_ters(b, isl, tf, ofset, kayma_pip, haber_kayma_pip)
    if cift is None:
        return {}
    r_ayni, r_ters = cift
    out: dict = {"yuzdelik": _karisim(r_ayni, r_ters, tekrar, tohum)["yuzdelik"], "esik": esik}
    sira = np.argsort(-r_ayni, kind="stable")
    for kk in DUYARLILIK_EN_IYI:
        tut = np.ones(len(r_ayni), bool)
        tut[sira[:kk]] = False
        out[f"haric_{kk}"] = (_karisim(r_ayni[tut], r_ters[tut], tekrar, tohum)["yuzdelik"]
                              if tut.sum() >= ASGARI_RASTGELE else float("nan"))
        out[f"en_iyi_{kk}_r"] = [float(x) for x in r_ayni[sira[:kk]]]
    yz = np.array([_karisim(r_ayni, r_ters, tekrar, mk.SINIR_TOHUM_TABAN + t)["yuzdelik"]
                   for t in range(mk.SINIR_TOHUM)])
    pay = float((yz >= esik).mean())
    out.update({"tohum_sayisi": mk.SINIR_TOHUM, "tohum_pay": pay, "tohum_medyan": float(np.median(yz)),
                "tohum_min": float(yz.min()), "tohum_max": float(yz.max()),
                "sinirda": bool(0.05 <= pay <= 0.95)})
    return out


def _karisim(r_ayni: np.ndarray, r_ters: np.ndarray, tekrar: int, tohum: int) -> dict:
    """Her işlemde yazı tura: gerçek yön ya da ters yön; tekrarların ortalama R dağılımında gerçek ortalamanın
    yüzdeliği."""
    rng = np.random.default_rng(tohum)
    ort = np.empty(tekrar)
    for q in range(0, tekrar, 200):
        n = min(200, tekrar - q)
        secim = rng.random((n, len(r_ayni))) < 0.5
        ort[q:q + n] = np.where(secim, r_ayni, r_ters).mean(axis=1)
    gercek = float(r_ayni.mean())
    return {"yuzdelik": float((ort < gercek).mean() * 100), "ort": float(ort.mean()),
            "p05": float(np.percentile(ort, 5)), "p95": float(np.percentile(ort, 95)),
            "ters_ort": float(r_ters.mean()), "n": int(len(r_ayni))}


def _ayni_ters(b: Baglam, isl: pd.DataFrame, tf: int, ofset: int | None, kayma_pip: float,
               haber_kayma_pip: float) -> tuple[np.ndarray, np.ndarray] | None:
    """Gerçek işlemlerin R'leri ve aynı giriş dakikasında ters yönde simüle edilmiş eşlerinin R'leri (geçerli
    çiftler); işlem sayısı asgarinin altındaysa None."""
    a = mk.alinan(isl).reset_index(drop=True)
    if len(a) < ASGARI_RASTGELE:
        return None
    d = b.d
    i = a["giris_i"].to_numpy(np.int64)
    yon_t = -a["yon"].to_numpy(np.int8)
    k = kayma_pip * d.pip
    hk = haber_kayma_pip * d.pip
    s0 = k + np.where(b.haber[i], hk, 0.0)
    dolum = np.where(yon_t == 1, d.ao[i] + s0, d.bo[i] - s0)
    R = a["R"].to_numpy(np.float64)
    e = mt.bos_emir(len(a))
    e["giris_i"] = i
    e["yon"] = yon_t
    st = a["stop_tur"].to_numpy(np.int8)
    e["stop_tur"] = st
    e["stop"] = np.where(st != mt.STOP_YOK, dolum - yon_t * R, np.nan)
    e["risk"] = R
    ht = a["hedef_tur"].to_numpy(np.int8)
    e["hedef_tur"] = ht
    e["hedef_k"] = a["hedef_k"].to_numpy(np.float64)
    uzak = np.abs(a["hedef"].to_numpy(np.float64) - a["giris_f"].to_numpy(np.float64))
    e["hedef_seviye"] = np.where(ht == mt.HEDEF_SEVIYE, dolum + yon_t * uzak, np.nan)
    e["cikis_i"] = a["plan_cikis_i"].to_numpy(np.int64)
    e["kimlik"] = np.arange(len(a))
    if ofset is None:
        ofs = a["ofset"].to_numpy(np.int64)
        parca = [mt.simule(d, e[ofs == o], b.bar_son(tf, int(o)), b.haber, kayma_pip, haber_kayma_pip,
                           tek_pozisyon=False) for o in np.unique(ofs)]
        ters = pd.concat(parca, ignore_index=True)
    else:
        ters = mt.simule(d, e, b.bar_son(tf, ofset), b.haber, kayma_pip, haber_kayma_pip, tek_pozisyon=False)
    ters = ters.sort_values("kimlik")
    r_ayni = a["r"].to_numpy()
    r_ters = ters["r"].to_numpy()
    gecerli = np.isfinite(r_ters)
    return r_ayni[gecerli], r_ters[gecerli]


# ───────────────────────────────────────────── koşul kovaları
SUREKLI = {"range_atr", "asya_atr", "onceki_gun_range_atr", "acilis_farki_atr", "oynaklik_yuzdelik"}


def kova_analizi(f: pd.DataFrame, ic: np.ndarray, asgari: int = 30) -> list[dict]:
    """Her değişken için kova başına IS/OOS metrikleri ve IS seçimi → OOS sonucu.

    `f`: işlem başına özellik tablosu (sütun: değişkenler + r + pnl_pip).
    `ic`: örneklem içi maskesi. Sürekli değişkenlerin kova sınırları YALNIZ
    örneklem içinden (terciller) kurulur ve örneklem dışına taşınır.
    """
    sonuc = []
    r = f["r"].to_numpy()
    gorulen: list[tuple[str, pd.Series]] = []
    for ad in [c for c in f.columns if c not in ("r", "pnl_pip", "is")]:
        x = f[ad]
        if x.isna().all():
            continue
        # Aynı ölçünün iki adı (ör. Asya kuralında "aralık / ATR" ile "Asya aralığı / ATR") tek değişkendir: iki kez
        # sayılırsa "tutan değişken" sayımı ve çoklu sınama payı şişer. Bütün işlemlerde aynı değeri taşıyan değişken
        # düşer ve neye eşit olduğu kayda geçer.
        es = next((o for o, y in gorulen if x.equals(y)), None)
        if es is not None:
            sonuc.append({"degisken": ad, "esdeger": es, "hukum": "esdeger"})
            continue
        gorulen.append((ad, x))
        # Koşulsuz ortalama, değişkenin TANIMLI olduğu işlemlerden: kovalar yalnız onlardan kurulur ve kıyas aynı
        # kümede yapılmalı (değişkenin tanımsız olduğu işlemler koşulsuz ortalamayı başka bir kümeye çekerdi).
        tanimli = x.notna().to_numpy()
        ic_ort = float(np.nanmean(r[ic & tanimli])) if (ic & tanimli).any() else float("nan")
        if ad in SUREKLI:
            q = np.nanpercentile(x[ic], [100 / 3, 200 / 3]) if (ic & x.notna().to_numpy()).sum() >= 30 else None
            if q is None or not np.isfinite(q).all() or q[0] == q[1]:
                continue
            kova = np.where(x.isna(), None, np.where(x < q[0], "alt", np.where(x < q[1], "orta", "üst")))
            sinir = [float(q[0]), float(q[1])]
        else:
            kova = x.astype(object).where(x.notna(), None).to_numpy()
            sinir = None
        kova = pd.Series(kova, index=f.index)
        # Örneklem dışının en iyi TEK işleminin kovası (bilgi; hükmü değiştirmez): bir kovanın örneklem dışı katkısının
        # ne kadarının o işleme dayandığını ders bununla yazar (kuyruk duyarlılığının kova eşi; işlemin kendisi
        # kuyruk kaydında). Eşit en iyi işlemler varsa ilki; kaç tane olduğu kuyruk kaydında (en_iyi_esit).
        dis_i = np.flatnonzero(~ic & np.isfinite(r))
        en_iyi_kova = None
        if len(dis_i):
            v_ = kova.iloc[int(dis_i[int(np.argmax(r[dis_i]))])]
            en_iyi_kova = None if v_ is None or pd.isna(v_) else str(v_)
        satirlar = []
        # Eksik değer kova değildir: pandas `where(..., None)` nesne dizisinde None'u NaN'a
        # çevirebiliyor ve NaN kovası tablolara "nan" adıyla, sıfır işlemle giriyordu.
        for k in [v for v in pd.unique(kova) if v is not None and pd.notna(v)]:
            m = (kova == k).to_numpy()
            mi, md = m & ic, m & ~ic
            satirlar.append({
                "kova": str(k),
                "is_n": int(mi.sum()), "is_r": float(r[mi].mean()) if mi.any() else float("nan"),
                "is_isabet": float((f["pnl_pip"].to_numpy()[mi] > 0).mean()) if mi.any() else float("nan"),
                "oos_n": int(md.sum()), "oos_r": float(r[md].mean()) if md.any() else float("nan"),
                "oos_isabet": float((f["pnl_pip"].to_numpy()[md] > 0).mean()) if md.any() else float("nan"),
            })
        secilen = [s["kova"] for s in satirlar if s["is_n"] >= asgari and np.isfinite(s["is_r"]) and s["is_r"] > ic_ort]
        hukum, oos_sec, oos_ters = _secim_sina(kova, r, ic, secilen, len(satirlar))
        # Ters seçim (betimleyici; ön kayıtta yoktu, hükmü değiştirmez): örneklem içinde ortalamanın ALTINDA kalan
        # kovalar seçilseydi aynı örneklem dışı ölçütü geçer miydi? Kova farkları gürültüyse iki seçimin geçme oranı
        # aynı olur; gerçek seçimin oranı ters seçiminkini aşmıyorsa "tuttu" sayısı şansla açıklanır.
        ters = [s["kova"] for s in satirlar if s["is_n"] >= asgari and np.isfinite(s["is_r"]) and s["is_r"] < ic_ort]
        t_hukum, t_sec, t_ters = _secim_sina(kova, r, ic, ters, len(satirlar))
        ms = kova.isin(secilen).to_numpy() if secilen else np.zeros(len(kova), bool)
        md = ms & ~ic
        mt_ = (~ms) & ~ic & tanimli
        pp = f["pnl_pip"].to_numpy()
        sonuc.append({"degisken": ad, "sinir": sinir, "kovalar": satirlar, "secilen": secilen,
                      "hukum": hukum, "oos_secilen_r": oos_sec, "oos_tamamlayan_r": oos_ters,
                      "ic_kosulsuz_r": ic_ort,
                      "oos_secilen_n": int(md.sum()), "oos_tamamlayan_n": int(mt_.sum()),
                      "oos_secilen_isabet": float((pp[md] > 0).mean()) if md.any() else float("nan"),
                      "oos_tamamlayan_isabet": float((pp[mt_] > 0).mean()) if mt_.any() else float("nan"),
                      "oos_en_iyi_kova": en_iyi_kova,
                      "ters_secim": {"secilen": ters, "hukum": t_hukum, "oos_secilen_r": t_sec,
                                     "oos_tamamlayan_r": t_ters}})
    return sonuc


def _secim_sina(kova: pd.Series, r: np.ndarray, ic: np.ndarray, secilen: list, n_kova: int) -> tuple:
    """Örneklem içinde seçilen kovaların örneklem dışı sınaması (ön kayıt [kosul]): seçilenlerin örneklem dışı
    ortalaması sıfırın ve tamamlayanın üstünde, en az ASGARI_KOSUL_OOS işlemle. Seçim boşsa 'secilmedi', bütün kovaları
    kapsıyorsa 'hepsi' (tamamlayan yok, sınama kurulamaz)."""
    if not secilen:
        return "secilmedi", float("nan"), float("nan")
    if len(secilen) >= n_kova:
        return "hepsi", float("nan"), float("nan")
    ms = kova.isin(secilen).to_numpy()
    msd, mtd = ms & ~ic, (~ms) & ~ic & kova.notna().to_numpy()
    oos_sec = float(r[msd].mean()) if msd.any() else float("nan")
    oos_ters = float(r[mtd].mean()) if mtd.any() else float("nan")
    n_oos = int(msd.sum())
    hukum = "tuttu" if (n_oos >= ASGARI_KOSUL_OOS and np.isfinite(oos_sec) and oos_sec > 0
                        and np.isfinite(oos_ters) and oos_sec > oos_ters) else "tutmadi"
    return hukum, oos_sec, oos_ters
