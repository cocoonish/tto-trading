#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAĞIT VE OIS DERSİ — dersin BÜTÜN ölçülmüş sayılarını üreten tek katman.

Girdi yalnız `veri/` (hazirla.py'nin dondurduğu arşiv, çıpa 22.09.2026).
İki tüketici var: `sekil.py` figürleri buradan çizer, `dogrula.py` metni
buradan yazılan `veri/olcum.json`a karşı sınar. Sayıyı üreten yer tektir.

ÖLÇÜM SÖZLEŞMELERİ, ADIYLA:

· FREKANS: AY SONU. TCMB gösterge değerlerinden türeyen günlük düğümler
  ölçüm gürültüsü taşır — günlük değişimlerin birinci gecikme otokorelasyonu
  belirgin NEGATİF (fiyat bir gün sapıp ertesi gün geri dönüyor) ve günlük
  PCA'da seviye bileşeni varyansın yalnız üçte birini açıklıyor. Gürültü her
  gözlemde bir kez girer, sinyal ise ufukla birikir: ay sonu değişimlerinde
  sinyal baskındır. Frekans karşılaştırması (`pca_frekans`) bu seçimin
  gerekçesini sayıyla verir; metin de onu anlatır.

· DÜĞÜMLER 3 ay … 7 yıl. 9 yıllık düğüm 2019–2020'de büyük ölçüde boştur
  (uzun kâğıt yoktu); PCA ve fly'lar kesintisiz yedi düğümle kurulur.

· FLY SEVİYESİ = 2 × gövde − kanatlar (getiri cinsinden; bp). Bu, gövde
  DV01'inin yarısı her kanada konan 50:50 DV01 yapının P&L'iyle orantılıdır.

· DURASYON GETİRİSİ: sabit vadeli sıfır kupon vekili, ay sonunda alınır,
  k ay sonra kısalmış vadesinin (düğümler arası doğrusal) getirisinden
  satılır; fonlama gecelik bileşik (TLREF; 2019 öncesi AOFM). SİNYAL
  (taşıma+roll, eğim) BEŞ İŞ GÜNÜ ÖNCEKİ eğriden kurulur: aynı günün
  ölçüm gürültüsü hem sinyale hem getiriye girerse sahte bir ilişki üretir.

· KONVANSİYON: TLREF basit faizdir (ACT/365, gecelik), DİBS getirisi yıllık
  bileşiktir. Kıyas her zaman bileşiğe çevrilerek yapılır:
      etkin = (1 + r/365)^365 − 1

Koşum:  python3 olcum.py            (veri/olcum.json'u yazar)
        python3 olcum.py --denetle  (yeniden hesaplar, depodakiyle kıyaslar)
"""
from __future__ import annotations

import argparse
import gzip
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
CIKTI = VERI / "olcum.json"

DUGUM = ["n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y"]
VADE = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0])
AD = {"n3a": "3 ay", "n6a": "6 ay", "n1y": "1 yıl", "n2y": "2 yıl", "n3y": "3 yıl",
      "n5y": "5 yıl", "n7y": "7 yıl"}
DONEMLER = (("2013", "2019"), ("2020", "2022"), ("2023-07", "2026"))
GECIKME = 5          # sinyal kaç iş günü önceki eğriden (gürültü ayrışması)
UFUK_GUN = 91        # bugünkü taşıma tablosunun ufku (3 ay)


# ─────────────────────────────────────────────────────────────── girdi
def _oku(ad: str) -> pd.DataFrame:
    ham = gzip.decompress((VERI / ad).read_bytes())
    return pd.read_csv(io.BytesIO(ham), index_col=0, parse_dates=True)


def yukle() -> dict:
    egri = _oku("egri_gunluk.csv.gz")
    fon = _oku("fonlama_gunluk.csv.gz")
    ppk = _oku("ppk_kararlari.csv.gz")
    ihale = _oku("ihale.csv.gz")
    return {"egri": egri, "fon": fon, "ppk": ppk, "ihale": ihale}


def gecelik(fon: pd.DataFrame) -> pd.Series:
    """Gecelik fonlama oranı, takvim günü (hafta sonu cuma oranı işler).
    TLREF 28.12.2018'de başlar; öncesinde TCMB ağırlıklı ortalama fonlama."""
    on = fon["tlref"].combine_first(fon["aofm"]).dropna()
    gun = pd.date_range(on.index.min(), on.index.max(), freq="D")
    return on.reindex(gun).ffill()


def etkin(r_basit: float) -> float:
    """Gecelik basit oran → yıllık bileşik eşdeğer (%, ACT/365)."""
    return ((1 + r_basit / 100 / 365) ** 365 - 1) * 100


# ─────────────────────────────────────────────────────────────── PCA
def pca(D: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Kovaryans matrisinin özvektörleri. İşaret sabitlenir: PC1 yüklerinin
    toplamı pozitif (seviye YUKARI), PC2 uzun uçta kısa uçtan büyük (eğri
    DİKLEŞİYOR), PC3 ortada pozitif (gövde yukarı) — sabitlenmezse koşudan
    koşuya grafik ters dönerdi."""
    Z = D - D.mean(axis=0)
    w, V = np.linalg.eigh(np.cov(Z.T))
    o = np.argsort(w)[::-1]
    w, V = w[o], V[:, o]
    if V[:, 0].sum() < 0:
        V[:, 0] *= -1
    if V[-1, 1] - V[0, 1] < 0:
        V[:, 1] *= -1
    if V[len(V) // 2, 2] < 0:
        V[:, 2] *= -1
    return w / w.sum(), V


def ay_sonu(egri: pd.DataFrame) -> pd.DataFrame:
    return egri[DUGUM].resample("ME").last().dropna()


def pca_frekans(egri: pd.DataFrame) -> dict:
    """Aynı eğri, dört frekans: seviye bileşeninin payı gürültüyle birlikte düşer."""
    X = egri[DUGUM].dropna()
    out = {}
    for ad, seri in (("gunluk", X),
                     ("haftalik", X.resample("W-FRI").last().dropna()),
                     ("ay_sonu", X.resample("ME").last().dropna()),
                     ("ay_ortalamasi", X.resample("ME").mean().dropna())):
        D = (seri.diff().dropna() * 100).to_numpy()
        pay, _ = pca(D)
        out[ad] = {"n": int(len(D)), "pay": [round(float(p) * 100, 1) for p in pay[:3]]}
    return out


def gurultu(egri: pd.DataFrame) -> dict:
    """Günlük değişimlerin birinci gecikme otokorelasyonu ve 20 günlük varyans
    oranı. Saf rastgele yürüyüşte AC1 ≈ 0 ve VR ≈ 1; ölçüm gürültüsü AC1'i
    negatife, VR'yi 1'in altına iter."""
    out = {}
    for bas, son in (("2013", "2019"), ("2023-07", "2026")):
        blok = {}
        for d in ("n2y", "n5y", "n7y"):
            s = egri.loc[bas:son, d].dropna() * 100
            d1 = s.diff().dropna()
            vr = s.diff(20).dropna().var() / (20 * d1.var())
            blok[d] = {"ac1": round(float(d1.autocorr(1)), 2), "vr20": round(float(vr), 2)}
        out[f"{bas}_{son}"] = blok
    return out


# ─────────────────────────────────────────────────────────────── eğim ve kadranlar
def egim_seviye(A: pd.DataFrame) -> dict:
    D = A.diff().dropna() * 100
    e = D.n7y - D.n2y
    b7 = np.polyfit(D.n2y, D.n7y, 1)
    b5 = np.polyfit(D.n2y, D.n5y, 1)
    c7 = float(np.corrcoef(D.n2y, D.n7y)[0, 1])
    out = {
        "n": int(len(D)),
        "corr_2y_2s7s": round(float(np.corrcoef(D.n2y, e)[0, 1]), 2),
        "beta_7y_2y": round(float(b7[0]), 2),
        "r2_7y_2y": round(c7 ** 2, 2),
        "beta_5y_2y": round(float(b5[0]), 2),
        "sigma_2y": round(float(D.n2y.std()), 0),
        "sigma_7y": round(float(D.n7y.std()), 0),
        "sigma_2s7s": round(float(e.std()), 0),
        "donem": {},
    }
    for bas, son in DONEMLER:
        d = D.loc[bas:son]
        out["donem"][f"{bas}_{son}"] = {
            "n": int(len(d)),
            "corr_2y_2s7s": round(float(np.corrcoef(d.n2y, d.n7y - d.n2y)[0, 1]), 2),
            "beta_7y_2y": round(float(np.polyfit(d.n2y, d.n7y, 1)[0]), 2),
            "beta_5y_2y": round(float(np.polyfit(d.n2y, d.n5y, 1)[0]), 2),
        }
    # Hedge oranı regresyonun YÖNÜNE bağlıdır: uzun ucu kısaya regresse etmek
    # "kısa uç hareket edince ortalama ne olur"u, tersi en küçük varyanslı hedge'i
    # verir; toplam en küçük kareler (iki bacağın 2×2 kovaryansının birinci
    # özvektörü) ikisini simetrik ele alır. Üçü de 7y (5y) DV01'i / 2y DV01'i
    # cinsinden eğimdir.
    for uzun in ("n5y", "n7y"):
        ters = float(np.polyfit(D[uzun], D.n2y, 1)[0])
        w_, V_ = np.linalg.eigh(np.cov(np.c_[D.n2y, D[uzun]].T))
        v_ = V_[:, int(np.argmax(w_))]
        out[f"beta_2y_{uzun[1:]}"] = round(ters, 2)
        out[f"tls_{uzun[1:]}_2y"] = round(float(v_[1] / v_[0]), 2)
    # 2 yıllık getirinin örneklemdeki uçları (ay sonu): dönemin hikâyesi
    out["y2_ilk"] = round(float(A.n2y.iloc[0]), 2)
    out["y2_min"] = [round(float(A.n2y.min()), 2), str(A.n2y.idxmin().date())[:7]]
    out["y2_max"] = [round(float(A.n2y.max()), 2), str(A.n2y.idxmax().date())[:7]]
    return out


def kadran(A: pd.DataFrame, ppk: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Aylık hareketin dört kadranı. Seviye = (Δ2y + Δ7y)/2, eğim = Δ(7y − 2y).
    PPK fazı: o ay içindeki kararların toplam faiz değişimi (artırım · indirim ·
    sabit), karar yoksa 'toplantı yok'."""
    D = A.diff().dropna() * 100
    sev = (D.n2y + D.n7y) / 2
    eg = D.n7y - D.n2y
    k = pd.Series(np.where(sev > 0, "ayı", "boğa"), index=D.index) + " " + \
        pd.Series(np.where(eg > 0, "dikleşme", "yataylaşma"), index=D.index)
    deg = ppk["politika"].diff()
    deg.iloc[0] = np.nan  # ilk kararın öncesi arşivde yok
    ay = deg.resample("ME").sum(min_count=1)
    faz = pd.Series("toplantı yok", index=D.index)
    for t, v in ay.items():
        if t in faz.index and np.isfinite(v):
            faz[t] = "artırım" if v > 0 else ("indirim" if v < 0 else "sabit")
    # PPK arşivi 2016'da başlar; öncesi faz tablosuna girmez
    faz[faz.index < ppk.index.min()] = "arşiv öncesi"
    KAD = ["ayı yataylaşma", "boğa dikleşme", "ayı dikleşme", "boğa yataylaşma"]
    pay = k.value_counts(normalize=True)
    buyuk = sev.abs() > 100
    out = {
        "n": int(len(k)),
        "pay": {q: round(float(pay.get(q, 0)) * 100, 1) for q in KAD},
        "buyuk_n": int(buyuk.sum()),
        "buyuk": {q: int((k[buyuk] == q).sum()) for q in KAD},
        "faz": {},
    }
    for f in ("artırım", "indirim", "sabit", "toplantı yok"):
        m = faz == f
        out["faz"][f] = {"n": int(m.sum()), **{q: int((k[m] == q).sum()) for q in KAD}}
    tablo = pd.DataFrame({"seviye": sev, "egim": eg, "kadran": k, "faz": faz})
    m = (faz == "indirim") & (sev > 0)
    out["indirim_seviye_artti"] = [[str(t.date())[:7], str(k[t]), round(float(sev[t]), 0),
                                    round(float(eg[t]), 0)] for t in tablo.index[m]]
    return out, tablo


# ─────────────────────────────────────────────────────────────── kalıcılık ve fly
def yari_omur(s: pd.Series) -> float:
    y = s.dropna().to_numpy()
    phi = float(np.polyfit(y[:-1], y[1:], 1)[0])
    return math.log(0.5) / math.log(phi) if 0 < phi < 1 else float("inf")


def fly_agirlik(V: np.ndarray, kanat1: str, govde: str, kanat2: str) -> tuple[float, float]:
    """Gövde − a·kanat1 − b·kanat2 yapısını PC1 ve PC2'ye nötr kılan a, b."""
    i1, i2, i3 = DUGUM.index(kanat1), DUGUM.index(govde), DUGUM.index(kanat2)
    M = np.array([[V[i1, 0], V[i3, 0]], [V[i1, 1], V[i3, 1]]])
    r = np.array([V[i2, 0], V[i2, 1]])
    a, b = np.linalg.solve(M, r)
    return float(a), float(b)


def kalicilik(A: pd.DataFrame, V: np.ndarray) -> tuple[dict, pd.DataFrame]:
    a, b = fly_agirlik(V, "n2y", "n5y", "n7y")
    S = pd.DataFrame({
        "2y": A.n2y, "5y": A.n5y, "7y": A.n7y,
        "2s7s": A.n7y - A.n2y, "2s5s": A.n5y - A.n2y,
        "fly50": 2 * A.n5y - A.n2y - A.n7y,
        "flyPCA": A.n5y - a * A.n2y - b * A.n7y,
    }) * 100
    out = {"agirlik_pca": [round(a, 3), round(b, 3)], "seri": {}}
    for k, s in S.items():
        out["seri"][k] = {"yari_omur_ay": round(yari_omur(s), 1),
                          "sigma_bp_ay": round(float(s.diff().std()), 0)}
    D = A.diff().dropna() * 100
    pc = D.to_numpy() @ V[:, :3]
    f50 = (2 * D.n5y - D.n2y - D.n7y).to_numpy()
    fpc = (D.n5y - a * D.n2y - b * D.n7y).to_numpy()
    out["fly50_korelasyon"] = [round(float(np.corrcoef(f50, pc[:, i])[0, 1]), 2) for i in range(3)]
    out["flyPCA_korelasyon"] = [round(float(np.corrcoef(fpc, pc[:, i])[0, 1]), 2) for i in range(3)]
    # ağırlıkların kararsızlığı: alt dönemlerde yeniden kestirilir
    out["agirlik_donem"] = {}
    for bas, son in (("2013", "2019"), ("2020", "2026")):
        d = A.loc[bas:son].diff().dropna() * 100
        _, Vd = pca(d.to_numpy())
        aa, bb = fly_agirlik(Vd, "n2y", "n5y", "n7y")
        out["agirlik_donem"][f"{bas}_{son}"] = [round(aa, 3), round(bb, 3)]
    return out, S


def _ar1(s: pd.Series) -> float:
    y = s.dropna().to_numpy()
    return float(np.polyfit(y[:-1], y[1:], 1)[0])


def katalog(A: pd.DataFrame, V: np.ndarray) -> dict:
    """Klasik spread ve fly'ların Türkiye eğrisindeki ölçüsü (ay sonu): aylık
    oynaklık, yarı ömür, seviye ve eğim bileşenleriyle korelasyon, çıpadaki
    seviye ve tarihsel yüzdeliği, ve AR(1) altında 1σ'lık sapmanın üç aylık
    beklenen dönüşünün aynı üç ayın gürültüsüne oranı:
        oran = √[(1 − φ³)/(1 + φ³)]   (φ aylık AR(1) katsayısı)
    Spread = uzun − kısa, fly = 2·gövde − kanatlar (50:50 DV01), bp."""
    S = A * 100
    yapilar = {
        "3a1y": S.n1y - S.n3a, "1y2y": S.n2y - S.n1y, "2y5y": S.n5y - S.n2y,
        "2y7y": S.n7y - S.n2y, "5y7y": S.n7y - S.n5y,
        "3a6a1y": 2 * S.n6a - S.n3a - S.n1y, "6a1y2y": 2 * S.n1y - S.n6a - S.n2y,
        "1y2y5y": 2 * S.n2y - S.n1y - S.n5y, "2y3y5y": 2 * S.n3y - S.n2y - S.n5y,
        "2y5y7y": 2 * S.n5y - S.n2y - S.n7y, "3y5y7y": 2 * S.n5y - S.n3y - S.n7y,
    }
    D = A.diff().dropna() * 100
    pc = D.to_numpy() @ V[:, :2]
    out = {}
    for ad, s in yapilar.items():
        d = s.diff().dropna()
        phi = _ar1(s)
        p3 = phi ** 3 if 0 < phi < 1 else float("nan")
        out[ad] = {
            "sigma_bp_ay": round(float(d.std()), 0),
            "yari_omur_ay": round(math.log(0.5) / math.log(phi), 1) if 0 < phi < 1 else None,
            "korelasyon_seviye": round(float(np.corrcoef(d.to_numpy(), pc[:, 0])[0, 1]), 2),
            "korelasyon_egim": round(float(np.corrcoef(d.to_numpy(), pc[:, 1])[0, 1]), 2),
            "seviye": round(float(s.iloc[-1]), 0),
            "yuzdelik": round(float((s < s.iloc[-1]).mean()) * 100, 0),
            "donus_gurultu_3ay": round(math.sqrt((1 - p3) / (1 + p3)), 2) if p3 == p3 else None,
        }
    # aynı oran seviye serileri ve PCA fly için (kıyas)
    a, b = fly_agirlik(V, "n2y", "n5y", "n7y")
    for ad, s in (("2y", S.n2y), ("7y", S.n7y), ("2y5y7y_pca", S.n5y - a * S.n2y - b * S.n7y)):
        phi = _ar1(s)
        p3 = phi ** 3
        out[ad] = {"yari_omur_ay": round(math.log(0.5) / math.log(phi), 1),
                   "donus_gurultu_3ay": round(math.sqrt((1 - p3) / (1 + p3)), 2)}
    return out


def fly_1y2y5y(A: pd.DataFrame, V: np.ndarray, bg: dict) -> dict:
    """Tümsek fly'ı (gövde 2 yıl, tümseğin tepesi): PCA ağırlıkları, taşıma ve
    kalıcılık. Gövdeyi almanın üç aylık taşıma + roll'u gövde DV01'i başına bp."""
    a, b = fly_agirlik(V, "n1y", "n2y", "n5y")
    t = bg["tasima"]
    be = {k: t[k]["toplam_yuzde"] / t[k]["mod_dur"] * 100 for k in ("1", "2", "5")}
    s = (A.n2y - a * A.n1y - b * A.n5y) * 100
    phi = _ar1(s)
    D = A.diff().dropna() * 100
    pc = D.to_numpy() @ V[:, :3]
    d = (D.n2y - a * D.n1y - b * D.n5y).to_numpy()
    return {"agirlik_pca": [round(a, 3), round(b, 3)],
            "tasima_50_bp": round(be["2"] - 0.5 * be["1"] - 0.5 * be["5"], 0),
            "tasima_pca_bp": round(be["2"] - a * be["1"] - b * be["5"], 0),
            "yari_omur_ay": round(math.log(0.5) / math.log(phi), 1),
            "sigma_bp_ay": round(float(s.diff().std()), 0),
            "korelasyon": [round(float(np.corrcoef(d, pc[:, k])[0, 1]), 2) for k in range(3)],
            "seviye_bp": round(float(s.iloc[-1]), 0),
            "yuzdelik": round(float((s < s.iloc[-1]).mean()) * 100, 0)}


def yapi_tasima(bg: dict, a: float, b: float) -> dict:
    """22.09.2026 eğrisinde eğri yapılarının üç aylık taşıma + roll'u, bp cinsinden.
    Her bacağın başabaşı (taşıma+roll)/D; DV01-nötr yapının taşıması bacak
    başabaşlarının DV01 ağırlıklı farkıdır. Yassılaştırıcı: uzun bacak alınır,
    kısa bacak satılır. Gövdeyi almak: gövde alınır, kanatlar satılır."""
    t = bg["tasima"]
    be = {k: t[k]["toplam_yuzde"] / t[k]["mod_dur"] * 100 for k in ("2", "5", "7")}
    return {
        "2s5s_yassilastirici_bp": round(be["5"] - be["2"], 0),
        "2s7s_yassilastirici_bp": round(be["7"] - be["2"], 0),
        # 50:50: gövde DV01'i 1, kanatlar 0,5'er → fly seviyesi cinsinden ×2
        "fly50_govde_al_bp_govde_dv01": round(be["5"] - 0.5 * be["2"] - 0.5 * be["7"], 0),
        "fly50_govde_al_bp_fly": round(2 * (be["5"] - 0.5 * be["2"] - 0.5 * be["7"]), 0),
        "flyPCA_govde_al_bp": round(be["5"] - a * be["2"] - b * be["7"], 0),
        # LONG fly (gövdede pay, kanatlarda receive) — yukarıdakilerin tam tersi işaret
        "fly50_long_bp_govde_dv01": round(-(be["5"] - 0.5 * be["2"] - 0.5 * be["7"]), 0),
        "fly50_long_bp_fly": round(-2 * (be["5"] - 0.5 * be["2"] - 0.5 * be["7"]), 0),
        "flyPCA_long_bp": round(-(be["5"] - a * be["2"] - b * be["7"]), 0),
        "2s5s_diklestirici_bp": round(be["2"] - be["5"], 0),
        "2s7s_diklestirici_bp": round(be["2"] - be["7"], 0),
    }


def faktor_maruziyet(V: np.ndarray, sigma: list[float], a: float, b: float) -> dict:
    """Yapıların seviye/eğim/büküm bileşenlerine maruziyeti: her bacağın DV01
    ağırlığı (uzun +, kısa −; ana bacak 10.000 TL/bp) ile 1σ'lık aylık faktör
    şokunun P&L'i (TL). P&L_k = −Σ_i w_i · v_{k,i} · σ_k · 10.000."""
    i = {d: j for j, d in enumerate(DUGUM)}
    yapilar = {
        "2y_uzun": {"n2y": 1.0},
        "2s5s_yassi_dv01": {"n5y": 1.0, "n2y": -1.0},
        "2s7s_yassi_dv01": {"n7y": 1.0, "n2y": -1.0},
        "3a1y_dik_dv01": {"n3a": 1.0, "n1y": -1.0},
        "fly50_govde_al": {"n5y": 1.0, "n2y": -0.5, "n7y": -0.5},
        "flyPCA_govde_al": {"n5y": 1.0, "n2y": -a, "n7y": -b},
        # long fly = gövdede pay (kâğıtta gövdeyi sat), kanatlarda receive (kanatları al)
        "fly50_long": {"n5y": -1.0, "n2y": 0.5, "n7y": 0.5},
        "flyPCA_long": {"n5y": -1.0, "n2y": a, "n7y": b},
    }
    out = {}
    for ad, w in yapilar.items():
        out[ad] = [round(float(-sum(wi * V[i[d], k] for d, wi in w.items()) * sigma[k] * 1e4), -2)
                   for k in range(3)]
    return out


def yapi_bugun(F: pd.DataFrame) -> dict:
    """Çıpadaki seviyelerin 2013–2026 ay sonu dağılımındaki yeri. Son satır
    çıpanın kendisidir (eylülün ay sonu yerine 22.09.2026)."""
    son = F.iloc[-1]
    out = {}
    for k in F.columns:
        s = F[k].dropna()
        out[k] = {"seviye": round(float(son[k]), 0),
                  "yuzdelik": round(float((s < son[k]).mean()) * 100, 0),
                  "yuzdelik_son36": round(float((s.iloc[-36:] < son[k]).mean()) * 100, 0),
                  "en_dusuk": [round(float(s.min()), 0), str(s.idxmin().date())[:7]],
                  "en_yuksek": [round(float(s.max()), 0), str(s.idxmax().date())[:7]]}
    return out


# ─────────────────────────────────────────────────────────────── durasyon getirisi
def _y(row: pd.Series, T: float) -> float:
    return float(np.interp(T, VADE, row[DUGUM].to_numpy() / 100))


def taşıma_roll(row: pd.Series, on_oran: float, hgun: int, T: float) -> float:
    """Eğri sabit kalırsa h gün sonra fonlama üstü getiri (oran, ondalık)."""
    h = hgun / 365
    p0 = (1 + _y(row, T)) ** (-T)
    p1 = (1 + _y(row, T - h)) ** (-(T - h))
    f = (1 + on_oran / 100 / 365) ** hgun - 1
    return p1 / p0 - 1 - f


def _hac(x: np.ndarray, y: np.ndarray, gecikme: int) -> tuple[float, float, float]:
    """y = a + b·x; Newey-West (Bartlett) HAC standart hatasıyla b'nin t'si."""
    X = np.c_[np.ones_like(x), x]
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    u = y - X @ beta
    S0 = (X * u[:, None]).T @ (X * u[:, None])
    for l in range(1, gecikme + 1):
        w = 1 - l / (gecikme + 1)
        G = (X[l:] * u[l:, None]).T @ (X[:-l] * u[:-l, None])
        S0 += w * (G + G.T)
    XtXi = np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(XtXi @ S0 @ XtXi))
    r2 = 1 - u.var() / y.var()
    return float(beta[1]), float(beta[1] / se[1]), float(r2)


def durasyon(egri: pd.DataFrame, on: pd.Series, k: int = 3) -> tuple[dict, pd.DataFrame]:
    N = egri[DUGUM].dropna()
    son_gunler = N.groupby(N.index.to_period("M")).apply(lambda x: x.index[-1]).tolist()
    satir = []
    for i, t0 in enumerate(son_gunler):
        if i + k >= len(son_gunler):
            break
        t1 = son_gunler[i + k]
        j = N.index.get_loc(t0)
        if j < GECIKME:
            continue
        ts = N.index[j - GECIKME]          # sinyal günü
        r = on.loc[t0:t1 - pd.Timedelta(days=1)] / 100
        fon = float(np.prod(1 + r / 365) - 1)
        h = (t1 - t0).days / 365
        for T in (2.0, 5.0, 7.0):
            p0 = (1 + _y(N.loc[t0], T)) ** (-T)
            p1 = (1 + _y(N.loc[t1], T - h)) ** (-(T - h))
            satir.append({
                "t0": t0, "T": T,
                "fazla": (p1 / p0 - 1 - fon) * 100,
                "cr": taşıma_roll(N.loc[ts], float(on.loc[:ts].iloc[-1]), (t1 - t0).days, T) * 100,
                "ters": bool(N.loc[ts, "n7y"] < N.loc[ts, "n3a"]),
            })
    S = pd.DataFrame(satir)
    out = {"ufuk_ay": k, "gecikme_gun": GECIKME}
    for T in (2.0, 5.0, 7.0):
        s = S[S["T"] == T]
        e = s.fazla
        b, t, r2 = _hac(s.cr.to_numpy(), e.to_numpy(), gecikme=k)
        blok = {
            "n": int(len(s)),
            "ort": round(float(e.mean()), 2), "medyan": round(float(e.median()), 2),
            "pozitif": round(float((e > 0).mean()) * 100, 0),
            "cr_pozitif": {"n": int((s.cr > 0).sum()), "ort": round(float(e[s.cr > 0].mean()), 2),
                           "pozitif": round(float((e[s.cr > 0] > 0).mean()) * 100, 0)},
            "cr_negatif": {"n": int((s.cr <= 0).sum()), "ort": round(float(e[s.cr <= 0].mean()), 2),
                           "pozitif": round(float((e[s.cr <= 0] > 0).mean()) * 100, 0)},
            "ters": {"n": int(s.ters.sum()), "ort": round(float(e[s.ters].mean()), 2),
                     "pozitif": round(float((e[s.ters] > 0).mean()) * 100, 0)},
            "duz": {"n": int((~s.ters).sum()), "ort": round(float(e[~s.ters].mean()), 2),
                    "pozitif": round(float((e[~s.ters] > 0).mean()) * 100, 0)},
            "egim": round(b, 2), "t_hac": round(t, 2), "r2": round(r2, 2),
            "yarilar": {},
        }
        for ad, m in (("2013_2019", s.t0 < "2020-01-01"), ("2020_2026", s.t0 >= "2020-01-01")):
            ss = s[m]
            blok["yarilar"][ad] = round(float(np.polyfit(ss.cr, ss.fazla, 1)[0]), 2)
        out[f"{int(T)}y"] = blok
    return out, S


# ─────────────────────────────────────────────────────────────── bugünkü eğri
def bugun(egri: pd.DataFrame, fon: pd.DataFrame, A: pd.DataFrame) -> dict:
    t = egri[DUGUM].dropna().index[-1]
    row = egri.loc[t]
    tlref_gun = fon["tlref"].dropna().index[-1]
    tl = float(fon.loc[tlref_gun, "tlref"])
    out = {
        "gun": str(t.date()), "tlref_gun": str(tlref_gun.date()),
        "tlref": round(tl, 2), "tlref_etkin": round(etkin(tl), 2), "tlref_tam": tl,
        "politika": round(float(fon.loc[tlref_gun, "politika"]), 2),
        "egri": {d: round(float(row[d]), 2) for d in DUGUM},
        "r2y": round(float(row["r2y"]), 2) if np.isfinite(row["r2y"]) else None,
        "tasima": {},
    }
    for T in (0.5, 1.0, 2.0, 3.0, 5.0, 7.0):
        cr = taşıma_roll(row, tl, UFUK_GUN, T) * 100
        y = _y(row, T) * 100
        D = T / (1 + y / 100)
        # taşıma: roll'suz kısım (vade kısalmadan aynı getiride kalsaydı)
        tas = ((1 + y / 100) ** (UFUK_GUN / 365) - 1 - ((1 + tl / 100 / 365) ** UFUK_GUN - 1)) * 100
        out["tasima"][f"{T:g}"] = {
            "getiri": round(y, 2), "mod_dur": round(D, 2),
            "tasima_yuzde": round(tas, 2), "roll_yuzde": round(cr - tas, 2),
            "toplam_yuzde": round(cr, 2), "basabas_bp": round(cr / D * 100, 0),
        }
    if out["r2y"]:
        out["basabas_enf_2y"] = round(((1 + row.n2y / 100) / (1 + row.r2y / 100) - 1) * 100, 2)
    # yakın dönem gerçekleşen oynaklık (ay sonu değişimleri, son 36 ay)
    Dm = A.diff().dropna() * 100
    out["sigma36"] = {d: round(float(Dm[d].iloc[-36:].std()), 0) for d in ("n1y", "n2y", "n5y", "n7y")}
    return out


def barbell(egri: pd.DataFrame, fon: pd.DataFrame, sigma_ay_bp: float) -> dict:
    """Nakit + durasyon nötr 2y/7y barbell'e karşı 5y bullet (sıfır kupon vekili).
    Yıllık bileşik sıfır kupon: modifiye durasyon T/(1+y), konveksite T(T+1)/(1+y)²."""
    t = egri[DUGUM].dropna().index[-1]
    row = egri.loc[t]
    tl = float(fon["tlref"].dropna().iloc[-1])
    y = {T: _y(row, T) for T in (2.0, 5.0, 7.0)}
    D = {T: T / (1 + y[T]) for T in y}
    C = {T: T * (T + 1) / (1 + y[T]) ** 2 for T in y}
    w7 = (D[5.0] - D[2.0]) / (D[7.0] - D[2.0])
    w2 = 1 - w7
    Cb = w2 * C[2.0] + w7 * C[7.0]
    cr = {T: taşıma_roll(row, tl, UFUK_GUN, T) * 100 for T in y}
    cr_b = w2 * cr[2.0] + w7 * cr[7.0]
    s_yil = sigma_ay_bp / 1e4 * math.sqrt(12)
    konv_deger = 0.5 * (Cb - C[5.0]) * s_yil ** 2 * (UFUK_GUN / 365) * 100
    # Portföy getirisi İKİ AYRI şeydir: vadeye kadar tek oranla iskonto eden iç
    # verim (IRR) ile üç aylık tahakkuku belirleyen piyasa değeri ağırlıklı getiri.
    # Barbell'de ikisi TERS işaret verebilir — metin bunu anlatır.
    N2 = w2 * (1 + y[2.0]) ** 2
    N7 = w7 * (1 + y[7.0]) ** 7
    alt, ust = 0.0, 2.0
    for _ in range(200):
        orta = (alt + ust) / 2
        if N2 / (1 + orta) ** 2 + N7 / (1 + orta) ** 7 > 1:
            alt = orta
        else:
            ust = orta
    irr = (alt + ust) / 2
    kiris = y[2.0] + (y[7.0] - y[2.0]) * (5 - 2) / (7 - 2)
    return {
        "gun": str(t.date()),
        "agirlik_2y": round(w2, 3), "agirlik_7y": round(w7, 3),
        "mod_dur": {f"{int(T)}y": round(D[T], 3) for T in D},
        "konveksite": {f"{int(T)}y": round(C[T], 2) for T in C},
        "konv_barbell": round(Cb, 2), "konv_fark": round(Cb - C[5.0], 2),
        "cr_bullet": round(cr[5.0], 2), "cr_barbell": round(cr_b, 2),
        "cr_fark": round(cr_b - cr[5.0], 2),
        "sigma_yillik_bp": round(s_yil * 1e4, 0),
        "konv_deger_3ay": round(konv_deger, 2),
        "fly_seviye_bp": round((2 * y[5.0] - y[2.0] - y[7.0]) * 1e4, 0),
        "getiri_bullet": round(y[5.0] * 100, 2),
        "getiri_barbell_irr": round(irr * 100, 2),
        "getiri_barbell_pd": round((w2 * y[2.0] + w7 * y[7.0]) * 100, 2),
        "kiris_5y": round(kiris * 100, 2),
        "kiris_fark_bp": round((y[5.0] - kiris) * 1e4, 0),
    }


def kupon_durasyon(bg: dict) -> list[dict]:
    """5 yıllık kâğıt, çıpadaki 5 yıllık getiriyle (iki basamak, metindeki sayı),
    altı ayda bir kupon: fiyat, Macaulay ve modifiye durasyon, 100 mn nominal
    başına DV01. Nakit akışları tek getiriyle yıllık bileşik iskonto edilir."""
    y = bg["egri"]["n5y"] / 100
    out = []
    for kupon in (0.0, 0.30, 0.35, 0.40):
        if kupon == 0:
            cf = [(5.0, 100.0)]
        else:
            cf = [(i / 2, kupon / 2 * 100 + (100 if i == 10 else 0)) for i in range(1, 11)]
        pv = [c * (1 + y) ** (-tt) for tt, c in cf]
        P = sum(pv)
        mac = sum(tt * v for (tt, _), v in zip(cf, pv)) / P
        mod = mac / (1 + y)
        out.append({"kupon": round(kupon * 100), "fiyat": round(P, 2), "macaulay": round(mac, 2),
                    "modifiye": round(mod, 2), "dv01_100mn": round(100e6 * P / 100 * mod * 1e-4, 0)})
    return out


def ppk_gunu(egri: pd.DataFrame, ppk: pd.DataFrame) -> dict:
    """PPK karar günlerinde eğrinin iki günlük hareketi (karar gününden bir önceki
    kapanıştan ertesi günün kapanışına; karar gün içinde açıklanır), diğer
    günlerin aynı ölçüsüyle kıyaslı. Mutlak değişimin medyanı ve 90. yüzdeliği."""
    N = egri[DUGUM].dropna() * 100
    d2 = N.diff(2).shift(-1)
    gun = [t for t in ppk.index if t in N.index]
    m = N.index.isin(gun)
    deg = ppk["politika"].diff()
    # arşivin ilk kararının öncesi yok: değişimi ölçülemeyen karar iki gruba da girmez
    degisen = [t for t in ppk.index[(deg.notna() & (deg != 0)).to_numpy()] if t in N.index]
    sabit = [t for t in ppk.index[(deg == 0).to_numpy()] if t in N.index]
    out = {"karar": len(gun), "degisen": len(degisen), "sabit": len(sabit), "vade": {}}
    for k in ("n3a", "n1y", "n2y", "n5y"):
        a, b = d2[k][m].abs().dropna(), d2[k][~m].abs().dropna()
        out["vade"][k] = {"ppk_medyan": round(float(a.median()), 0), "ppk_p90": round(float(a.quantile(0.9)), 0),
                          "diger_medyan": round(float(b.median()), 0), "diger_p90": round(float(b.quantile(0.9)), 0),
                          "oran": round(float(a.median() / b.median()), 1),
                          "degisen_medyan": round(float(d2[k][N.index.isin(degisen)].abs().median()), 0),
                          "sabit_medyan": round(float(d2[k][N.index.isin(sabit)].abs().median()), 0)}
    return out


def fly_orneklem_disi(egri: pd.DataFrame, on: pd.Series, ayrik: bool = True) -> dict:
    """Fly'ın ortalamaya dönüşünü ÖRNEKLEM DIŞI sınar. Her ay sonu t (ilk 37 ay
    ısınma): PCA ağırlıkları yalnız bir önceki ay sonuna kadarki değişimlerden
    kestirilir; fly'ın (girişten beş iş günü önceki) değeri son 36 ay sonunun
    ortalamasından en az bir standart sapma uzaksa ortalamaya doğru pozisyon
    alınır ve 3 ay tutulur. P&L gövde DV01'i başına bp: yön × Δfly + taşıma + roll (bacak
    başabaşları o ayın eğrisi ve fonlamasıyla). İşlem maliyeti dahil değil;
    pozisyonlar üst üste biner (aylık sinyal, üç aylık tutma)."""
    # GÜRÜLTÜ AYRIŞMASI (durasyon sınamasıyla aynı kural): sinyal girişten BEŞ İŞ
    # GÜNÜ önceki eğriden, ağırlıklar ve z-skorunun geçmişi BİR ÖNCEKİ ay sonuna
    # kadarki veriden kurulur. Aynı ay sonu gözlemi hem sinyale hem girişe girerse
    # ölçüm gürültüsünün ertesi ay geri dönmesi sahte bir "dönüş kârı" üretir.
    A = ay_sonu(egri)
    D = A.diff().dropna() * 100
    N = egri[DUGUM].dropna()
    idx = A.index
    satir = {"pca": [], "5050": []}
    for i in range(37, len(idx) - 3):
        t = idx[i]
        # ayrık değilse (karşılaştırma için): ağırlık ve z aynı ay sonu gözlemini içerir
        t_onceki = idx[i - 1] if ayrik else t
        _, V = pca(D.loc[:t_onceki].to_numpy())
        a, b = fly_agirlik(V, "n2y", "n5y", "n7y")
        giris = N.loc[:t].index[-1]
        sinyal = N.index[N.index.get_loc(giris) - GECIKME] if ayrik else giris
        row = N.loc[giris]
        r_on = float(on.loc[:giris].iloc[-1])
        be = {}
        for T in (2.0, 5.0, 7.0):
            y = _y(row, T)
            be[T] = taşıma_roll(row, r_on, UFUK_GUN, T) / (T / (1 + y)) * 1e4
        for kural, (wa, wb) in (("pca", (a, b)), ("5050", (0.5, 0.5))):
            F = (A.n5y - wa * A.n2y - wb * A.n7y) * 100
            g = F.loc[:t_onceki].iloc[-36:]
            f_sig = float((N.loc[sinyal, "n5y"] - wa * N.loc[sinyal, "n2y"] - wb * N.loc[sinyal, "n7y"]) * 100)
            z = (f_sig - g.mean()) / g.std()
            if abs(z) < 1:
                continue
            yon = -float(np.sign(z))                  # fly yüksekse sat, düşükse al
            fiyat = yon * (F.iloc[i + 3] - F.loc[t])
            tasima = -yon * (be[5.0] - wa * be[2.0] - wb * be[7.0])
            satir[kural].append({"t": t, "fiyat": fiyat, "tasima": tasima, "net": fiyat + tasima})
    out = {}
    for kural, r in satir.items():
        d = pd.DataFrame(r)
        yar = {ad: d[m] for ad, m in (("2016_2019", d.t < "2020-01-01"), ("2020_2026", d.t >= "2020-01-01"))}
        out[kural] = {"n": int(len(d)), "ilk": str(d.t.min().date())[:7], "son": str(d.t.max().date())[:7],
                      "isabet_net": round(float((d.net > 0).mean()) * 100, 0),
                      "fiyat_ort": round(float(d.fiyat.mean()), 1), "tasima_ort": round(float(d.tasima.mean()), 1),
                      "net_ort": round(float(d.net.mean()), 1), "net_medyan": round(float(d.net.median()), 1),
                      "net_sd": round(float(d.net.std()), 1),
                      "yarilar": {ad: {"n": int(len(x)), "net_ort": round(float(x.net.mean()), 1)}
                                  for ad, x in yar.items()}}
    return out


def barbell_kurallar(egri: pd.DataFrame, fon: pd.DataFrame, V: np.ndarray, sigma: list[float],
                     s_ay: float, h: int = UFUK_GUN) -> dict:
    """Aynı 2y/5y/7y barbell'i üç ağırlık kuralıyla (barbell–bullet aracıyla aynı
    formüller): 100 mn TL gövde nominali başına kanat nominalleri, net nakit,
    taşıma + roll farkı, konveksite değeri ve 1σ aylık faktör şoklarında P&L.
    Barbell yönü: gövde satılır, kanatlar alınır."""
    # Araçla BİREBİR aynı girdiler: düğüm getirileri iki basamağa yuvarlanmış (aracın
    # varsayılan eğrisi), yükler dört basamak (aracın gömülü tablosu).
    t0 = egri[DUGUM].dropna().index[-1]
    dugum = np.array([round(float(egri.loc[t0, d]), 2) for d in DUGUM]) / 100
    V = np.round(V, 4)
    tl = float(fon["tlref"].dropna().iloc[-1])
    f = (1 + tl / 100 / 365) ** h - 1

    def yv(T: float) -> float:
        return float(np.interp(T, VADE, dugum))

    def kagit(T: float) -> dict:
        y = yv(T)
        P = 100 * (1 + y) ** (-T)
        D = T / (1 + y)
        C = T * (T + 1) / (1 + y) ** 2
        Th = max(T - h / 365, 1 / 365)
        P1 = 100 * (1 + yv(Th)) ** (-Th)
        return {"P": P, "D": D, "C": C, "dv01": P * D * 1e-4, "cr": P1 - P - P * f}

    k1, kg, k3 = kagit(2.0), kagit(5.0), kagit(7.0)
    Ng = 100e6
    MVg, DVg = Ng / 100 * kg["P"], Ng / 100 * kg["dv01"]
    i1, ig, i3 = DUGUM.index("n2y"), DUGUM.index("n5y"), DUGUM.index("n7y")
    s_yil = s_ay / 1e4 * math.sqrt(12)
    out = {}
    for kural in ("nakit", "pca", "5050"):
        if kural == "nakit":
            mv1 = MVg * (k3["D"] - kg["D"]) / (k3["D"] - k1["D"])
            mv3 = MVg * (kg["D"] - k1["D"]) / (k3["D"] - k1["D"])
            dv1, dv3 = mv1 * k1["D"] * 1e-4, mv3 * k3["D"] * 1e-4
        elif kural == "pca":
            a, b = fly_agirlik(V, "n2y", "n5y", "n7y")
            dv1, dv3 = a * DVg, b * DVg
        else:
            dv1, dv3 = 0.5 * DVg, 0.5 * DVg
        N1, N3 = dv1 / k1["dv01"] * 100, dv3 / k3["dv01"] * 100
        MV1, MV3 = N1 / 100 * k1["P"], N3 / 100 * k3["P"]
        cr = (N1 / 100 * k1["cr"] + N3 / 100 * k3["cr"]) - Ng / 100 * kg["cr"]
        konv = 0.5 * ((MV1 * k1["C"] + MV3 * k3["C"]) - MVg * kg["C"]) * s_yil ** 2 * (h / 365)
        pc = [-(dv1 * V[i1, k] + dv3 * V[i3, k] - DVg * V[ig, k]) * sigma[k] for k in range(3)]
        out[kural] = {"kanat_nominal_mn": [round(N1 / 1e6, 1), round(N3 / 1e6, 1)],
                      "kanat_dv01": [round(dv1, 0), round(dv3, 0)],
                      "net_nakit_mn": round((MV1 + MV3 - MVg) / 1e6, 1),
                      "tasima_mn": round(cr / 1e6, 2), "tasima_yuzde": round(cr / MVg * 100, 2),
                      "konv_mn": round(konv / 1e6, 2), "konv_yuzde": round(konv / MVg * 100, 2),
                      "faktor_mn": [round(x / 1e6, 2) for x in pc]}
    return out


# ─────────────────────────────────────────────────────────────── TLREF bazı
CIPALAR = ("politika", "koridor_ust", "koridor_alt")


def cipa(d: pd.DataFrame) -> pd.Series:
    """Her gün TLREF'in EN YAKIN durduğu ilan edilmiş oran — `bulten/fonlama_rejim`
    ile aynı eşiksiz kural. İlk yazımda "tavanda" 10 bp'lik bir eşikle sayılıyordu
    ve 2026'nın tavan rejimi (02.03 → 21.08) TLREF'in tavanın 11–21 bp altına
    indiği birkaç günde bölünüp 57 iş günü çıkıyordu: eşiğin kendisi sonucu
    belirliyordu. Çıpası ölçülemeyen gün sınıflanmaz."""
    mesafe = pd.DataFrame({c: (d["tlref"] - d[c]).abs() for c in CIPALAR})
    return mesafe.idxmin(axis=1).where(mesafe.notna().all(axis=1))


def tlref_baz(fon: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    d = fon.dropna(subset=["tlref", "politika"]).copy()
    d["baz"] = (d.tlref - d.politika) * 100
    d["cipa"] = cipa(d)
    d["tavanda"] = d["cipa"] == "koridor_ust"
    sinif = d["cipa"].notna()

    def pay(x: pd.DataFrame, c: str) -> float:
        s = x.loc[x["cipa"].notna(), "cipa"]
        return round(float((s == c).mean()) * 100, 0)

    out = {"ilk": str(d.index.min().date()), "son": str(d.index.max().date()), "n": int(len(d)),
           "sinifli": int(sinif.sum()),
           "medyan": round(float(d.baz.median()), 0),
           "p10": round(float(d.baz.quantile(0.1)), 0), "p90": round(float(d.baz.quantile(0.9)), 0),
           "mutlak_100_ustu": round(float((d.baz.abs() > 100).mean()) * 100, 0),
           "tavanda": pay(d, "koridor_ust"), "tabanda": pay(d, "koridor_alt"),
           "donem": {}}
    for bas, son in (("2019", "2020"), ("2021", "2022"), ("2023-06", "2024"), ("2025", "2026")):
        x = d.loc[bas:son]
        out["donem"][f"{bas}_{son}"] = {
            "n": int(len(x)), "medyan": round(float(x.baz.median()), 0),
            "mutlak_100_ustu": round(float((x.baz.abs() > 100).mean()) * 100, 0),
            "tavanda": pay(x, "koridor_ust"), "tabanda": pay(x, "koridor_alt")}
    # 2026'da çıpası aynı kalan ardışık iş günü blokları (rejimler)
    c = d.loc["2026", "cipa"].dropna()
    blok = (c != c.shift()).cumsum()
    out["rejim_2026"] = [{"cipa": str(x.iloc[0]), "bas": str(x.index[0].date()),
                          "son": str(x.index[-1].date()), "is_gunu": int(len(x))}
                         for _, x in c.groupby(blok)]
    # Tavan bloğunun bir lira receive pozisyonuna maliyeti: politika faizine göre
    # fazladan ödenen yüzen bacak, takvim günü (hafta sonu cuma oranı işler).
    tavan = [r for r in out["rejim_2026"] if r["cipa"] == "koridor_ust"]
    if tavan:
        r = max(tavan, key=lambda r: r["is_gunu"])
        sonraki = d.loc[r["son"]:].index[1]          # rejimden sonraki ilk iş günü
        gun = pd.date_range(r["bas"], sonraki - pd.Timedelta(days=1), freq="D")
        bz = d["baz"].reindex(gun).ffill()
        tl = d["tlref"].reindex(gun).ffill() / 100
        po = d["politika"].reindex(gun).ffill() / 100
        # Yüzen bacak dönem içinde GÜNLÜK BİLEŞİKLENİR: maliyet, iki bileşiğin farkıdır
        # (basit toplam, %40 seviyesinde farkı belirgin biçimde küçük gösterir).
        fark = float(np.prod(1 + tl / 365) - np.prod(1 + po / 365))
        out["tavan_blok_2026"] = {**r, "takvim_gunu": int(len(gun)),
                                  "baz_ort_bp": round(float(bz.mean()), 0),
                                  "maliyet_100mn_mn": round(fark * 100, 2),
                                  "maliyet_basit_100mn_mn": round(float((bz / 1e4 / 365).sum() * 100), 2)}
    return out, d


# ─────────────────────────────────────────────────────────────── temsili OIS
# Trade Pratiği dersinin temsili eğrisi (çıpa 05.08.2026) ve temsili DV01 tablosu
# (100 mn TL başına). TRY OIS'in tarihsel kotasyon serisi bu derste yok; OIS
# örnekleri bu eğriyle kurulur ve metinde ADIYLA temsilidir.
TEMSILI_OIS = {
    "cipa": "2026-08-05", "tlref": 39.95,
    "egri": {"3m": 38.95, "6m": 37.50, "9m": 36.20, "1y": 35.25, "18m": 32.60, "2y": 30.40,
             "3y": 27.10, "4y": 25.30, "5y": 24.10, "6y": 23.40, "7y": 22.90, "10y": 22.10},
    "dv01_100mn": {"1y": 8300, "2y": 14700, "5y": 30400, "7y": 38900},
}


# Hesap aracının (OIS taşıma) eğri noktaları ve yöntemi — araçla BİREBİR aynı
# sayı çıksın diye aynı kural: doğrusal ara değer, uçlarda düz; çeyreklik kupon
# takvimi uzun son stub'la; iskonto 1/(1 + z·t), z o vadenin kotasyonu.
ARAC_EGRI = [(1 / 12, 39.90), (2 / 12, 39.45), (0.25, 38.95), (0.5, 37.50), (0.75, 36.20),
             (1.0, 35.25), (1.5, 32.60), (2.0, 30.40), (3.0, 27.10), (4.0, 25.30),
             (5.0, 24.10), (7.0, 22.90), (10.0, 22.10)]


def _arac_oran(t: float) -> float:
    xs = [a for a, _ in ARAC_EGRI]
    ys = [b for _, b in ARAC_EGRI]
    return float(np.interp(t, xs, ys))


def _arac_annuite(T: float, frek: int = 4) -> float:
    adim = 1 / frek
    odeme, x = [], adim
    while x < T - adim / 2:
        odeme.append(round(x, 6))
        x += adim
    odeme.append(T)
    A, onc = 0.0, 0.0
    for t in odeme:
        A += 1 / (1 + _arac_oran(t) / 100 * t) * (t - onc)
        onc = t
    return A


def _ceyrek_bootstrap(egri: dict) -> dict:
    """3m · 6m · 9m · 1y çeyreklik par oranlarından iskonto faktörleri, çeyreklik
    forward'lar ve her forward'ın GECELİK basit karşılığı (dönem 0,25 yıl ≈ 91,25
    gün yaklaşımı). Kotasyon ile fixing ancak aynı dile çevrilince kıyaslanır."""
    tau = 0.25
    df: list[float] = []
    for v in ("3m", "6m", "9m", "1y"):
        k = egri[v] / 100
        df.append((1 - k * tau * sum(df)) / (1 + k * tau))
    fwd = [(1 / df[0] - 1) / tau] + [(df[i - 1] / df[i] - 1) / tau for i in range(1, 4)]
    gece = [365 * ((1 + f * tau) ** (1 / (365 * tau)) - 1) for f in fwd]
    # 3 ay sonra başlayan 9 aylık par oran (forward-başlangıçlı swap)
    f39 = (df[0] - df[3]) / (tau * sum(df[1:4]))
    ort_gece = 365 * ((1 / df[3]) ** (1 / 365) - 1)
    return {"df": [round(x, 5) for x in df],
            "forward_yuzde": [round(f * 100, 2) for f in fwd],
            "gecelik_yuzde": [round(g * 100, 2) for g in gece],
            "forward_3m_9m": round(f39 * 100, 2),
            "ortalama_gecelik_1y": round(ort_gece * 100, 2)}


def temsili_ois(bg: dict) -> dict:
    T = TEMSILI_OIS
    N, K, h = 500e6, T["egri"]["1y"], 92

    def F(r: float) -> float:
        """Gecelik basit fixing sabit kalırsa h günlük dönemin bileşik yüzen oranı
        (dönem basit oranı cinsinden, %): [(1 + r/365)^h − 1]·365/h."""
        return ((1 + r / 100 / 365) ** h - 1) * 365 / h * 100

    def carry(r: float) -> float:        # receiver'ın fixing taşıması, mn TL
        return (K - F(r)) / 100 * h / 365 * N / 1e6

    def carry_basit(r: float) -> float:  # yaygın basit yaklaşım — karşılaştırma için
        return (K - r) / 100 * h / 365 * N / 1e6

    out = {"cipa": T["cipa"], "tlref": T["tlref"],
           "ornek": {"nominal_mn": 500, "vade": "1y", "K": K, "gun": h,
                     "F_tavan": round(F(T["tlref"]), 2), "F_bugun": round(F(bg["tlref"]), 2),
                     "carry_tavan": round(carry(T["tlref"]), 2),
                     "carry_bugun": round(carry(bg["tlref"]), 2), "tlref_bugun": bg["tlref"],
                     "carry_tavan_basit": round(carry_basit(T["tlref"]), 2)}}
    # Risk eşdeğeri: temsili DV01 × kâğıt eğrisinin son 36 aylık ölçülmüş aylık
    # oynaklığı. İki kaynak bilerek birleşiyor: DV01 enstrümanın, oynaklık eğrinin.
    risk = {}
    for v, dv in T["dv01_100mn"].items():
        s = bg["sigma36"][f"n{v}"]
        risk[v] = {"dv01": dv, "sigma_bp_ay": s, "risk_1s_mn": round(dv * s / 1e6, 2)}
    ref = risk["5y"]["risk_1s_mn"]
    for v in risk:
        risk[v]["esdeger_nominal_mn"] = round(100 * ref / risk[v]["risk_1s_mn"], 0)
    out["risk_esdeger"] = risk
    out["bootstrap"] = _ceyrek_bootstrap(T["egri"])
    # Aynı oran üç dilde: gecelik basit (fixing) · 92 günlük dönem basit (çeyreklik
    # swap kotasyonunun dili) · yıllık bileşik (tahvil getirisinin dili)
    tl_tam = bg["tlref_tam"]
    out["uc_dil"] = []
    for ad, r in (("bugun", tl_tam), ("politika", bg["politika"]), ("temsili", T["tlref"])):
        out["uc_dil"].append({"ad": ad, "gecelik": round(r, 2), "ceyrek_92g": round(F(r), 2),
                              "yillik": round(etkin(r), 2)})
    # Aracın varsayılan vakası (500 mn · 1y receive @ K · 92 gün · TLREF spot)
    Th = max(1 - h / 365, 1 / 365)
    A_T, A_Th, S_Th = _arac_annuite(1.0), _arac_annuite(Th), _arac_oran(Th)
    tas = (K - F(T["tlref"])) / 100 * h / 365 * N
    rol = (K - S_Th) / 100 * A_Th * N
    out["arac"] = {"A_T": round(A_T, 4), "A_Th": round(A_Th, 4), "S_Th": round(S_Th, 2),
                   "dv01": round(A_T * N * 1e-4, 0), "tasima_mn": round(tas / 1e6, 2),
                   "roll_mn": round(rol / 1e6, 2), "toplam_mn": round((tas + rol) / 1e6, 2),
                   "gunluk_bin": round(tas / h / 1e3, 0),
                   "basabas": round(K + tas / (A_Th * N / 100), 2)}
    # Senaryolar (ufuk sonunda 9 aylık kotasyon ve çeyrek boyunca ortalama TLREF):
    # varsayımdır, ölçüm değil — metin öyle yazar.
    senaryo = {"hizli_normallesme": (37.50, 32.00), "stres": (T["tlref"], 38.00)}
    out["senaryo"] = {}
    # A — forward'lar gerçekleşir: ilk dönemin yüzen oranı 3m kotasyonu (dönem dili),
    # 9 aylık kotasyon 3 ay sonra başlayan forward'a gelir. Toplam ≈ 0 olmalı.
    f39 = out["bootstrap"]["forward_3m_9m"]
    a = (K - T["egri"]["3m"]) / 100 * h / 365 * N
    b = (K - f39) / 100 * A_Th * N
    out["senaryo"]["forward"] = {"donem_orani": T["egri"]["3m"], "kotasyon_9m": f39,
                                 "tasima_mn": round(a / 1e6, 2), "mtm_mn": round(b / 1e6, 2),
                                 "toplam_mn": round((a + b) / 1e6, 2)}
    # Fixing hemen politika faizine inerse (eğrinin kalanı sabit): başabaş forward'a yaklaşır
    a = (K - F(37.00)) / 100 * h / 365 * N
    out["fixing_politikada"] = {"F": round(F(37.00), 2), "tasima_mn": round(a / 1e6, 2),
                                "toplam_mn": round((a + rol) / 1e6, 2),
                                "basabas": round(K + a / (A_Th * N / 100), 2)}
    # Başabaş–forward farkının kaynağı: ilk dönemde fiyatlanandan fazla ödenen fixing
    fazla = (F(T["tlref"]) - T["egri"]["3m"]) / 100 * h / 365 * N
    out["basabas_forward"] = {"fark_bp": round((f39 - out["arac"]["basabas"]) * 100, 0),
                              "fazla_fixing_mn": round(fazla / 1e6, 2),
                              "kalan_annuite_mn_puan": round(A_Th * N / 100 / 1e6, 3),
                              "karsilik_bp": round(fazla / (A_Th * N / 100) * 100, 0)}
    # Vaka: "tavan rejimi bir ay içinde biter" görüşü (varsayım): fixing 30 gün
    # %39,95, sonra 62 gün politika faizi %37,00. 3 aylık swap'ın dönem oranıyla kıyas.
    F_vaka = ((1 + T["tlref"] / 100 / 365) ** 30 * (1 + 0.37 / 365) ** 62 - 1) * 365 / 92 * 100
    ceyrek = T["egri"]["3m"]
    gece_esd = 365 * ((1 + F_vaka / 100 * 92 / 365) ** (1 / 92) - 1) * 100
    out["vaka_rejim"] = {"F": round(F_vaka, 2), "gecelik_esdeger": round(gece_esd, 2),
                         "fiyatlanan_donem": ceyrek,
                         "fiyatlanan_gecelik": out["bootstrap"]["gecelik_yuzde"][0],
                         "pay_3m_500mn": round((F_vaka - ceyrek) / 100 * 92 / 365 * 500, 2),
                         "rejim_3ay_surerse_pay_500mn": round((F(T["tlref"]) - ceyrek) / 100 * 92 / 365 * 500, 2)}
    # 1 yıllık swap = 3 aylık swap + 3 ay sonra başlayan 9 aylık swap (aynı nominal):
    # DV01 paylaşımı (bootstrap iskonto faktörleriyle)
    dfb = out["bootstrap"]["df"]
    a3, a39 = 0.25 * dfb[0], 0.25 * sum(dfb[1:4])
    out["serit"] = {"dv01_3m_500mn": round(a3 * 500e6 * 1e-4, 0), "dv01_3m9m_500mn": round(a39 * 500e6 * 1e-4, 0),
                    "pay_ilk_bacak": round(a3 / (a3 + a39) * 100, 0)}
    # Vade başına "kira": aracın yöntemiyle, 500 mn receive, 92 gün, fixing spot.
    # Görüş / kira kıyası için DV01 başına taşıma + roll (bp) de yazılır.
    out["kira"] = {}
    for v, T_ in (("6m", 0.5), ("1y", 1.0), ("2y", 2.0), ("5y", 5.0)):
        K_ = _arac_oran(T_)
        Th_ = max(T_ - h / 365, 1 / 365)
        A_T_, A_Th_, S_ = _arac_annuite(T_), _arac_annuite(Th_), _arac_oran(Th_)
        c_ = (K_ - F(T["tlref"])) / 100 * h / 365 * N
        r_ = (K_ - S_) / 100 * A_Th_ * N
        dv = A_T_ * N * 1e-4
        out["kira"][v] = {"K": K_, "dv01": round(dv, 0), "tasima_mn": round(c_ / 1e6, 2),
                          "roll_mn": round(r_ / 1e6, 2), "toplam_mn": round((c_ + r_) / 1e6, 2),
                          "dv01_basina_bp": round((c_ + r_) / dv, 0)}
    # 6 aylık kotasyonun gecelik karşılığı (alıştırma): 6 ayın ortalama gecelik faizi
    df6 = out["bootstrap"]["df"][1]
    out["gecelik_6m"] = round(365 * ((1 / df6) ** (1 / 182.5) - 1) * 100, 2)
    for ad, (r_ort, s9) in senaryo.items():
        a = (K - F(r_ort)) / 100 * h / 365 * N
        b = (K - s9) / 100 * A_Th * N
        out["senaryo"][ad] = {"tlref_ort": r_ort, "kotasyon_9m": s9, "tasima_mn": round(a / 1e6, 2),
                              "mtm_mn": round(b / 1e6, 2), "toplam_mn": round((a + b) / 1e6, 2)}
    return out


# ─────────────────────────────────────────────────────────────── stres ve ihale
def stres(A: pd.DataFrame) -> dict:
    """Ay sonu değişimlerinin uçları: durasyon bütçesinin stres kalibrasyonu."""
    D = A.diff().dropna() * 100
    out = {}
    for d in ("n2y", "n5y", "n7y"):
        s = D[d]
        out[d] = {"en_buyuk_artis": [round(float(s.max()), 0), str(s.idxmax().date())[:7]],
                  "en_buyuk_dusus": [round(float(s.min()), 0), str(s.idxmin().date())[:7]],
                  "p95_mutlak": round(float(s.abs().quantile(0.95)), 0),
                  "p95_mutlak_son36": round(float(s.iloc[-36:].abs().quantile(0.95)), 0),
                  # asimetri: büyük satışlar büyük rallilerden sık ve büyük mü?
                  # (örneklem faizin %6'dan %45'e çıktığı bir dönem — sürüklenme de içeride)
                  "carpiklik": round(float(s.skew()), 2),
                  "ay_200_ustu_artis": int((s > 200).sum()),
                  "ay_200_ustu_dusus": int((s < -200).sum()),
                  "en_buyuk10_artis_ort": round(float(s.nlargest(10).mean()), 0),
                  "en_buyuk10_dusus_ort": round(float(s.nsmallest(10).mean()), 0)}
    return out


def ihale_ozet(ih: pd.DataFrame) -> dict:
    """Hazine ihalelerinin bileşimi, ROT payı ve teklif/satış oranı."""
    rot_pay = ih["rot"] / ih["toplam"]
    tso = ih["ihale_teklif"] / ih["ihale_satis"]
    tur = ih["tur"].value_counts()
    sabit = ih[ih["tur"].str.contains("Sabit Kuponlu") & (ih.index >= "2024-01-01")]
    kova = sabit["vade_yil"].round(0)
    tso_s = (sabit["ihale_teklif"] / sabit["ihale_satis"])
    out = {"n": int(len(ih)), "ilk": str(ih.index.min().date()), "son": str(ih.index.max().date()),
           "tur": {k: int(v) for k, v in tur.items()},
           "rot_pay_medyan": round(float(rot_pay.median()) * 100, 1),
           "rot_sifir": int((ih["rot"] == 0).sum()),
           # ROT'u kim kullanıyor: hacim ağırlıklı pay (piyasa yapıcı · kamu)
           "rot_py_pay": round(float(ih["rot_py"].sum() / ih["rot"].sum()) * 100, 1),
           "rot_kamu_pay": round(float(ih["rot_kamu"].sum() / ih["rot"].sum()) * 100, 1),
           "rot_kamu_yok": int((ih["rot_kamu"] == 0).sum()),
           "sabit_2024": {}}
    for ad, m in (("2y", kova == 2), ("5y", kova == 5), ("10y", kova.isin([9, 10]))):
        out["sabit_2024"][ad] = {"n": int(m.sum()), "tso_medyan": round(float(tso_s[m].median()), 2)}
    return out


# ─────────────────────────────────────────────────────────────── taşıma, roll ve rejimler
# Bu bölümün vadeleri 1–7 yıldır. 3 ve 6 aylık düğümler BİLİLEREK dışarıda: kısa uçta
# bono getirisi TLREF'in belirgin altında işler (bono–TLREF bazı) ve kâğıdın fonlama
# üstü taşıması o bazı ölçer, eğrinin kendisini değil — 3a1y dikleştiricisi indirim
# pencerelerinde bile −260 bp çıkıyordu. Kısa ucun taşıma mantığı OIS'le anlatılır.
TENOR = {"n1y": 1.0, "n2y": 2.0, "n3y": 3.0, "n5y": 5.0, "n7y": 7.0}
GECIKMELER = (1, 5, 10, 21)   # gecikme profili: sinyal kaç iş günü önceki eğriden
YARILAR = (("2013_2019", "2013-01-01", "2020-01-01"), ("2020_2026", "2020-01-01", "2100-01-01"))


def _ay_son_gunleri(N: pd.DataFrame) -> list:
    return N.groupby(N.index.to_period("M")).apply(lambda x: x.index[-1]).tolist()


def _basabas(row: pd.Series, r_on: float, hgun: int, T: float) -> float:
    """Taşıma + roll'un başabaş getiri değişimi (bp): eğri sabitken h günlük fonlama
    üstü getirinin modifiye durasyona bölümü. DV01 başına P&L budur."""
    return taşıma_roll(row, r_on, hgun, T) / (T / (1 + _y(row, T))) * 1e4


def _basabas_parca(row: pd.Series, r_on: float, hgun: int, T: float) -> tuple[float, float]:
    """Başabaşın (bp) taşıma ve roll parçaları: taşıma = kendi getirisiyle tahakkuk eksi
    fonlama, roll = geri kalanı; ikisi de modifiye durasyona bölünür."""
    y = _y(row, T)
    D = T / (1 + y)
    tas = (1 + y) ** (hgun / 365) - 1 - ((1 + r_on / 100 / 365) ** hgun - 1)
    top = taşıma_roll(row, r_on, hgun, T)
    return tas / D * 1e4, (top - tas) / D * 1e4


def _bugun_basabas(egri: pd.DataFrame, fon: pd.DataFrame) -> dict:
    """Çıpa eğrisinde 1–7 yıllık düğümlerin 3 aylık başabaşı (bp), YUVARLANMAMIŞ: bugünkü
    taşımayı yazan bütün tablolar aynı sayıdan beslenir."""
    row = egri[DUGUM].dropna().iloc[-1]
    tl = float(fon["tlref"].dropna().iloc[-1])
    return {d: _basabas(row, tl, UFUK_GUN, T) for d, T in TENOR.items()}


def pencereler(egri: pd.DataFrame, on: pd.Series, ppk: pd.DataFrame, cipa_gun: pd.Series | None = None,
               k: int = 3) -> pd.DataFrame:
    """Üst üste binen üç aylık pencereler (her ay sonu bir giriş). Her pencere ve vade
    için gerçekleşen fonlama üstü getirinin ÜÇ PARÇASI (fiyatın yüzdesi):
      taşıma = (1 + y₀)^h − 1 − f           kendi getirisiyle tahakkuk eksi fonlama
      roll   = P(T−h; t₀ eğrisi)/P₀ − (1 + y₀)^h   eğri kımıldamasa vadenin kısalmasının getirisi
      fiyat  = [P₁ − P(T−h; t₀ eğrisi)]/P₀        eğrinin kendisinin hareketi
    f gerçekleşen gecelik fonlamanın bileşiğidir. Aynı pencerenin DV01 başına dili:
    be (başabaş, bp; giriş eğrisi ve giriş fonlamasıyla) ve dy (kısalmış vadenin
    getirisindeki değişim, bp) — DV01 başına P&L ≈ be − dy. Sinyal sütunları (be_sinyal)
    beş iş günü önceki eğriden. Pencere düzeyinde: PPK fazı (penceredeki kararların
    toplamı) ve sürpriz = t₁'deki 1 yıllık getiri − t₀'da fiyatlanan, 3 ay sonra
    başlayan 1 yıllık forward (bp; artı = piyasanın beklediğinden şahin).

    Ek sütunlar: fonlama sürprizi (girişteki fixing sabit kalsaydı taşıma − gerçekleşen
    taşıma; artı = fonlama beklenenden pahalı çıktı), sinyal gününün fonlama çıpası,
    penceredeki seviye hareketi (Δ(2y + 7y)/2, bp), forward'ın ima ettiği değişim
    fd = f(h, T−h) − y(T−h) (sinyal eğrisinden, bp) ve sinyalin 1 · 10 · 21 iş günü
    gecikmeli sürümleri (gecikme profili için)."""
    N = egri[DUGUM].dropna()
    son = _ay_son_gunleri(N)
    deg = ppk["politika"].diff()
    deg.iloc[0] = np.nan
    ppk_bas = ppk.index.min()
    satir = []
    for i, t0 in enumerate(son):
        if i + k >= len(son):
            break
        t1 = son[i + k]
        j = N.index.get_loc(t0)
        if j < GECIKME:
            continue
        ts = N.index[j - GECIKME]
        r0, r1, rs = N.loc[t0], N.loc[t1], N.loc[ts]
        hg = (t1 - t0).days
        h = hg / 365
        r = on.loc[t0:t1 - pd.Timedelta(days=1)] / 100
        f = float(np.prod(1 + r / 365) - 1)
        on0, ons = float(on.loc[:t0].iloc[-1]), float(on.loc[:ts].iloc[-1])
        f_on = (1 + on0 / 100 / 365) ** hg - 1          # girişteki fixing sabit kalsaydı
        if t0 < ppk_bas:
            faz = None
        else:
            s = deg.loc[t0 + pd.Timedelta(days=1):t1].dropna().sum()
            faz = "indirim" if s < 0 else ("artırım" if s > 0 else "sabit")
        yh, y1h = _y(r0, h), _y(r0, 1 + h)
        fwd = (1 + y1h) ** (1 + h) / (1 + yh) ** h - 1
        surpriz = (_y(r1, 1.0) - fwd) * 1e4
        cp = None
        if cipa_gun is not None and ts >= cipa_gun.index.min():
            cp = cipa_gun.loc[:ts].iloc[-1]
        seviye = ((r1.n2y + r1.n7y) - (r0.n2y + r0.n7y)) / 2 * 100
        gec = {}
        for L in GECIKMELER:
            if j - L >= 0:
                tL = N.index[j - L]
                gec[L] = (N.loc[tL], float(on.loc[:tL].iloc[-1]))
        for d, T in TENOR.items():
            y0 = _y(r0, T)
            p0 = (1 + y0) ** (-T)
            ps = (1 + _y(r0, T - h)) ** (-(T - h))
            p1 = (1 + _y(r1, T - h)) ** (-(T - h))
            tas = (1 + y0) ** h - 1 - f
            roll = ps / p0 - (1 + y0) ** h
            fiyat = (p1 - ps) / p0
            ysT, ysh = _y(rs, T), _y(rs, h)
            fwd_s = ((1 + ysT) ** T / (1 + ysh) ** h) ** (1 / (T - h)) - 1
            satir.append({
                "t0": t0, "d": d, "T": T, "faz": faz, "surpriz": surpriz, "cipa": cp, "seviye": seviye,
                "tasima": tas * 100, "roll": roll * 100, "fiyat": fiyat * 100,
                "toplam": (tas + roll + fiyat) * 100,
                "fon_surpriz": (f - f_on) * 100,
                "be": _basabas(r0, on0, hg, T), "be_sinyal": _basabas(rs, ons, hg, T),
                **{f"be_g{L}": (_basabas(gec[L][0], gec[L][1], hg, T) if L in gec else np.nan)
                   for L in GECIKMELER},
                "dy": (_y(r1, T - h) - _y(r0, T - h)) * 1e4,
                "fd": (fwd_s - _y(rs, T - h)) * 1e4,
            })
    return pd.DataFrame(satir)


def _nw_t(x: pd.Series, L: int = 2) -> float:
    """Üst üste binen pencerelerin ortalaması için Newey–West (Bartlett) t."""
    y = x.dropna().to_numpy()
    u = y - y.mean()
    n = len(y)
    s = (u @ u) / n
    for l in range(1, L + 1):
        s += 2 * (1 - l / (L + 1)) * (u[l:] @ u[:-l]) / n
    return float(y.mean() / math.sqrt(s / n))


def _oz(x: pd.Series) -> dict:
    return {"n": int(len(x)), "ort": round(float(x.mean()), 1), "medyan": round(float(x.median()), 1),
            "isabet": round(float((x > 0).mean()) * 100, 0)}


def _yarilar(d: pd.DataFrame, kol: str, zaman: str = "t0") -> dict:
    out = {}
    for ad, bas, son in YARILAR:
        x = d[(d[zaman] >= bas) & (d[zaman] < son)][kol]
        out[ad] = {"n": int(len(x)), "ort": round(float(x.mean()), 1),
                   "isabet": round(float((x > 0).mean()) * 100, 0)}
    return out


# Üç dönem: düşük faizli 2013–2019, pozitif taşımalı 2020–2022, sıkılaşma sonrası.
UC_DONEM = (("2013_2019", "2013-01-01", "2020-01-01"), ("2020_2022", "2020-01-01", "2023-01-01"),
            ("2023_2026", "2023-01-01", "2100-01-01"))


def tasima_ayristirma(P: pd.DataFrame) -> dict:
    """Gerçekleşen üç aylık fonlama üstü getirinin parçaları (fiyatın %'si), vade vade:
    ortalama, standart sapma, varyans payı [cov(parça, toplam)/var(toplam)]; fonlama
    sürprizi; PPK fazına ve üç döneme göre. Ardından TAŞIMA İŞARETİYLE ZAMANLAMA: sinyal
    anındaki taşıma + roll artıysa uzun, eksiyse kısa (kısa = kâğıdı ödünç alıp satmak ya
    da OIS'te pay; getirisi toplamın eksisi). Zamanlamanın katkısı ancak HEP KISA ve HEP
    UZUN kıyaslarıyla okunur: faizin yükseldiği bir örneklemde kısa durmak kendi başına
    kazandırır. t: üst üste binen pencereler için Newey–West (L = 2). Gecikme profili:
    sinyal 1 · 5 · 10 · 21 iş günü önceki eğriden."""
    out = {"n_pencere": int(P.t0.nunique()), "ilk": str(P.t0.min().date())[:7],
           "son": str(P.t0.max().date())[:7], "vade": {}, "faz": {}, "donem": {}, "zamanlama": {}}
    for d in TENOR:
        x = P[P.d == d]
        v = x.toplam.var()
        out["vade"][d] = {
            **{k: round(float(x[k].mean()), 2) for k in ("tasima", "roll", "fiyat", "toplam")},
            "toplam_medyan": round(float(x.toplam.median()), 2),
            "sd": {k: round(float(x[k].std()), 2) for k in ("tasima", "roll", "fiyat", "toplam")},
            "pay": {k: round(float(np.cov(x[k], x.toplam)[0, 1] / v) * 100, 0) for k in ("tasima", "roll", "fiyat")},
            "fon_surpriz": round(float(x.fon_surpriz.mean()), 2),
            "pozitif": round(float((x.toplam > 0).mean()) * 100, 0),
            "tasima_pozitif": round(float((x.tasima > 0).mean()) * 100, 0),
            "roll_pozitif": round(float((x.roll > 0).mean()) * 100, 0),
            "be_pozitif": round(float((x.be_sinyal > 0).mean()) * 100, 0),
        }
        yon = np.sign(x.be_sinyal)
        z = yon * x.toplam
        zz = x.assign(z=z, kisa=-x.toplam)
        blok = {"zamanlama": {**_oz(z), "t": round(_nw_t(z), 1), "yarilar": _yarilar(zz, "z")},
                "hep_uzun": {**_oz(x.toplam), "t": round(_nw_t(x.toplam), 1)},
                "hep_kisa": {**_oz(-x.toplam), "t": round(_nw_t(-x.toplam), 1), "yarilar": _yarilar(zz, "kisa")},
                "arti": {"n": int((yon > 0).sum()), "ort": round(float(x.toplam[yon > 0].mean()), 2),
                         "pozitif": round(float((x.toplam[yon > 0] > 0).mean()) * 100, 0)},
                "eksi": {"n": int((yon <= 0).sum()), "ort": round(float(x.toplam[yon <= 0].mean()), 2),
                         "pozitif": round(float((x.toplam[yon <= 0] > 0).mean()) * 100, 0)},
                "gecikme": {}}
        for L in GECIKMELER:
            y = x.dropna(subset=[f"be_g{L}"])
            blok["gecikme"][str(L)] = round(float((np.sign(y[f"be_g{L}"]) * y.toplam).mean()), 2)
        out["zamanlama"][d] = blok
    for f in ("indirim", "sabit", "artırım"):
        x = P[P.faz == f]
        out["faz"][f] = {"n": int(x.t0.nunique())}
        for d in TENOR:
            y = x[x.d == d]
            out["faz"][f][d] = {k: round(float(y[k].mean()), 2) for k in ("tasima", "roll", "fiyat", "toplam")}
    for ad, bas, son in UC_DONEM:
        x = P[(P.t0 >= bas) & (P.t0 < son)]
        out["donem"][ad] = {"n": int(x.t0.nunique())}
        for d in TENOR:
            y = x[x.d == d]
            out["donem"][ad][d] = {**{k: round(float(y[k].mean()), 2) for k in ("tasima", "roll", "fiyat", "toplam")},
                                   "fon_surpriz": round(float(y.fon_surpriz.mean()), 2),
                                   "tasima_pozitif": round(float((y.tasima > 0).mean()) * 100, 0)}
    return out


def forward_gerceklesme(P: pd.DataFrame) -> dict:
    """Forward'lar gerçekleşiyor mu? Kısalmış vadenin gerçekleşen değişimi (dy) forward'ın
    ima ettiği değişime (fd = f − y, sinyal eğrisinden) regresse edilir: dy = α + β·fd.
    β = 1 → forward ortalamada gerçekleşiyor, taşıma + roll kazanılmaz; β = 0 → eğri
    sabit kalıyor, taşıma + roll olduğu gibi kazanılır. HAC (L = 2) standart hata."""
    out = {}
    for d in TENOR:
        x = P[P.d == d]
        b, t, r2 = _hac(x.fd.to_numpy(), x.dy.to_numpy(), 2)
        se = b / t if t else float("nan")
        blok = {"n": int(len(x)), "beta": round(b, 2), "t0": round(t, 1), "t1": round((b - 1) / se, 1),
                "r2": round(r2, 2), "fd_ort": round(float(x.fd.mean()), 0), "dy_ort": round(float(x.dy.mean()), 0),
                "yarilar": {}}
        for ad, bas, son in YARILAR:
            y = x[(x.t0 >= bas) & (x.t0 < son)]
            blok["yarilar"][ad] = round(float(np.polyfit(y.fd, y.dy, 1)[0]), 2)
        out[d] = blok
    return out


# Eğri yapıları, DV01 ağırlıklarıyla. İşaret: artı = kâğıt uzun / OIS'te receive.
# Long fly = GÖVDEDE PAY (kâğıtta gövdeyi sat), kanatlarda receive: fly yükselince kazanır.
def _yapilar(V: np.ndarray) -> dict:
    a, b = fly_agirlik(V, "n2y", "n5y", "n7y")
    a2, b2 = fly_agirlik(V, "n1y", "n2y", "n5y")
    a3, b3 = fly_agirlik(V, "n2y", "n3y", "n5y")
    a4, b4 = fly_agirlik(V, "n3y", "n5y", "n7y")
    a5, b5 = fly_agirlik(V, "n1y", "n2y", "n3y")
    return {
        "2y_receive": {"n2y": 1.0},
        "5y_receive": {"n5y": 1.0},
        "7y_receive": {"n7y": 1.0},
        "2s5s_diklestirici": {"n2y": 1.0, "n5y": -1.0},
        "2s7s_diklestirici": {"n2y": 1.0, "n7y": -1.0},
        "1y2y3y_long50": {"n2y": -1.0, "n1y": 0.5, "n3y": 0.5},
        "1y2y3y_longpca": {"n2y": -1.0, "n1y": a5, "n3y": b5},
        "1y2y5y_long50": {"n2y": -1.0, "n1y": 0.5, "n5y": 0.5},
        "1y2y5y_longpca": {"n2y": -1.0, "n1y": a2, "n5y": b2},
        "2y3y5y_long50": {"n3y": -1.0, "n2y": 0.5, "n5y": 0.5},
        "2y3y5y_longpca": {"n3y": -1.0, "n2y": a3, "n5y": b3},
        "2y5y7y_long50": {"n5y": -1.0, "n2y": 0.5, "n7y": 0.5},
        "2y5y7y_longpca": {"n5y": -1.0, "n2y": a, "n7y": b},
        "3y5y7y_long50": {"n5y": -1.0, "n3y": 0.5, "n7y": 0.5},
        "3y5y7y_longpca": {"n5y": -1.0, "n3y": a4, "n7y": b4},
    }


def _yapi_pencere(P: pd.DataFrame, V: np.ndarray) -> pd.DataFrame:
    """Her pencere ve yapı için DV01 başına üç aylık P&L (bp; gövde ya da ana bacak
    DV01'i başına): taşıma+roll = Σ w·be, hareket = −Σ w·dy, toplam = ikisinin toplamı."""
    Y = _yapilar(V)
    be = P.pivot(index="t0", columns="d", values="be")
    dy = P.pivot(index="t0", columns="d", values="dy")
    ust = P.groupby("t0")[["faz", "surpriz", "cipa", "seviye"]].first()
    satir = []
    for ad, w in Y.items():
        c = sum(wi * be[d] for d, wi in w.items())
        m = -sum(wi * dy[d] for d, wi in w.items())
        satir.append(pd.DataFrame({"t0": be.index, "yapi": ad, "tasima": c.to_numpy(), "hareket": m.to_numpy(),
                                   "toplam": (c + m).to_numpy(), "faz": ust.faz.to_numpy(),
                                   "surpriz": ust.surpriz.to_numpy(), "cipa": ust.cipa.to_numpy(),
                                   "seviye": ust.seviye.to_numpy()}))
    return pd.concat(satir, ignore_index=True)


def _rejim_blok(y: pd.DataFrame) -> dict:
    return {"n": int(len(y)), "toplam": round(float(y.toplam.mean()), 0),
            "tasima": round(float(y.tasima.mean()), 0), "hareket": round(float(y.hareket.mean()), 0),
            "hareket_p25": round(float(y.hareket.quantile(0.25)), 0),
            "hareket_p75": round(float(y.hareket.quantile(0.75)), 0),
            "isabet": round(float((y.toplam > 0).mean()) * 100, 0)}


def rejim_yapi(P: pd.DataFrame, V: np.ndarray) -> tuple[dict, pd.DataFrame]:
    """Yapıların üç aylık P&L'i (DV01 başına bp) dört rejim tanımıyla:
    (1) GERÇEKLEŞEN PPK fazı (penceredeki kararların toplamı);
    (2) piyasanın fiyatladığına göre SÜRPRİZ — t₁'deki 1 yıllık getiri eksi t₀'da fiyatlanan,
        3 ay sonra başlayan 1 yıllık forward; üç eşit kovaya bölünür. Trader'ın asıl sorusu
        budur: yön değil, forward'a göre sapma para kazandırır;
    (3) sinyal gününün FONLAMA ÇIPASI (TLREF 2018 sonundan);
    (4) KUYRUK: penceredeki seviye hareketinin en üst ve en alt %10'u (satış · ralli).
    Fly ağırlıkları tam örneklem PCA'sı — rejim betimlemesi için; ticaret sınaması
    örneklem dışı ayrıca yapılır. Pencereler üst üste biner."""
    Y = _yapi_pencere(P, V)
    ust = Y.drop_duplicates("t0").set_index("t0")
    kova = pd.qcut(ust.surpriz, 3, labels=["guvercin", "orta", "sahin"])
    Y["kova"] = Y.t0.map(kova)
    q10, q90 = ust.seviye.quantile(0.1), ust.seviye.quantile(0.9)
    kuyruk = pd.Series(np.where(ust.seviye >= q90, "satis", np.where(ust.seviye <= q10, "ralli", "")),
                       index=ust.index)
    Y["kuyruk"] = Y.t0.map(kuyruk)
    sinir = [float(x) for x in ust.surpriz.quantile([1 / 3, 2 / 3])]
    out = {"n_pencere": int(len(ust)), "faz_n": {}, "kova_n": {}, "kova_surpriz": {}, "cipa_n": {},
           "kova_sinir_bp": [round(s, 0) for s in sinir],
           "surpriz_ort": round(float(ust.surpriz.mean()), 0),
           "surpriz_medyan": round(float(ust.surpriz.median()), 0),
           "kuyruk_sinir_bp": [round(float(q10), 0), round(float(q90), 0)],
           "kuyruk_seviye": {"satis": round(float(ust.seviye[kuyruk == "satis"].mean()), 0),
                             "ralli": round(float(ust.seviye[kuyruk == "ralli"].mean()), 0)},
           "faz": {}, "kova": {}, "cipa": {}, "kuyruk": {}}
    for f in ("indirim", "sabit", "artırım"):
        out["faz_n"][f] = int((ust.faz == f).sum())
    for kv in ("guvercin", "orta", "sahin"):
        m = kova == kv
        out["kova_n"][kv] = int(m.sum())
        out["kova_surpriz"][kv] = round(float(ust.surpriz[m].mean()), 0)
    for c in CIPALAR:
        out["cipa_n"][c] = int((ust.cipa == c).sum())
    for ad in Y.yapi.unique():
        y = Y[Y.yapi == ad]
        out["faz"][ad] = {f: _rejim_blok(y[y.faz == f]) for f in ("indirim", "sabit", "artırım")}
        out["kova"][ad] = {kv: _rejim_blok(y[y.kova == kv]) for kv in ("guvercin", "orta", "sahin")}
        out["cipa"][ad] = {c: _rejim_blok(y[y.cipa == c]) for c in CIPALAR if (y.cipa == c).sum() >= 5}
        out["kuyruk"][ad] = {k: _rejim_blok(y[y.kuyruk == k]) for k in ("satis", "ralli")}
    return out, Y


def aylik_rejim(A: pd.DataFrame, V: np.ndarray, faz: pd.Series) -> dict:
    """Aylık (ay sonu) getiri ve yapı hareketleri (bp): PPK ayı fazına göre ortalama, ve
    seviyenin 200 bp'den fazla arttığı (stres) ya da düştüğü (ralli) aylar."""
    a, b = fly_agirlik(V, "n2y", "n5y", "n7y")
    a2, b2 = fly_agirlik(V, "n1y", "n2y", "n5y")
    S = A * 100
    Yd = pd.DataFrame({"2y": S.n2y, "5y": S.n5y, "7y": S.n7y, "2s5s": S.n5y - S.n2y, "2s7s": S.n7y - S.n2y,
                       "1y2y5y": 2 * S.n2y - S.n1y - S.n5y, "1y2y5y_pca": S.n2y - a2 * S.n1y - b2 * S.n5y,
                       "2y5y7y": 2 * S.n5y - S.n2y - S.n7y,
                       "2y5y7y_pca": S.n5y - a * S.n2y - b * S.n7y}).diff().dropna()
    f = faz.reindex(Yd.index)
    out = {"faz": {}}
    for ad in ("indirim", "sabit", "artırım", "toplantı yok"):
        x = Yd[f == ad]
        out["faz"][ad] = {"n": int(len(x)), **{k: round(float(x[k].mean()), 0) for k in Yd.columns}}
    sev = (Yd["2y"] + Yd["7y"]) / 2
    for ad, m in (("stres", sev > 200), ("ralli", sev < -200)):
        x = Yd[m]
        out[ad] = {"n": int(len(x)), **{k: round(float(x[k].mean()), 0) for k in Yd.columns},
                   "aylar": [str(t.date())[:7] for t in x.index]}
    return out


def tasima_stratejileri(P: pd.DataFrame, A: pd.DataFrame) -> dict:
    """Taşımadan para kazanmanın eğri kuralları, DV01 başına bp, üç aylık tutma:
    (1) EN İYİ TAŞIMALI VADEYİ UZUN TUT: her ay sonu, beş iş günü önceki eğrinin
        taşıma + roll başabaşının son 36 ayın gerçekleşen oynaklığına oranı en yüksek
        vade alınır. Seviye riskini tümüyle taşır.
    (2) EĞRİ TİCARETİ: aynı oranın en yüksek olduğu vade alınır, en düşük olduğu vade
        satılır (DV01-nötr). Seviye riski büyük ölçüde düşer; kalan, eğrinin hangi
        bölgesinin bekleme bedelini fazla ödediğidir. Kıyaslar: sabit 1s7s ve 2s7s
        dikleştiricisi (kısa vade uzun, uzun vade kısa) ve pencerenin seviye hareketiyle
        korelasyon — kural gizlice bir eğim ya da seviye bahsine dönüşmüş mü?
    Oynaklık yalnız girişten önceki 36 aydan; oranın paydası σ·√3 (üç aylık)."""
    Dm = A.diff() * 100
    satir = []
    for t0, g in P.groupby("t0"):
        gecmis = Dm.loc[:t0 - pd.Timedelta(days=1)].iloc[-36:]
        if len(gecmis) < 24:
            continue
        g = g.set_index("d")
        sig = {d: gecmis[d].std() * math.sqrt(3) for d in TENOR}
        pnl = {d: g.loc[d, "be"] - g.loc[d, "dy"] for d in TENOR}
        rec = {"t0": t0, "seviye": float(g.seviye.iloc[0]),
               "dik17": pnl["n1y"] - pnl["n7y"], "dik27": pnl["n2y"] - pnl["n7y"],
               "esit": float(np.mean(list(pnl.values())))}
        for L in GECIKMELER:
            kol = "be_sinyal" if L == GECIKME else f"be_g{L}"
            if g[kol].isna().any():
                continue
            oran = {d: g.loc[d, kol] / sig[d] for d in TENOR}
            hi, lo = max(oran, key=oran.get), min(oran, key=oran.get)
            rec[f"ls{L}"] = pnl[hi] - pnl[lo]
            if L == GECIKME:
                rec.update({"hi": hi, "lo": lo, "ls": pnl[hi] - pnl[lo], "uzun": pnl[hi],
                            "dik": TENOR[hi] < TENOR[lo]})
        satir.append(rec)
    R = pd.DataFrame(satir)
    return {"n": int(len(R)), "ilk": str(R.t0.min().date())[:7], "son": str(R.t0.max().date())[:7],
            "egri_ticareti": {**_oz(R.ls), "sd": round(float(R.ls.std()), 0), "t": round(_nw_t(R.ls), 1),
                              "yarilar": _yarilar(R, "ls"),
                              "seviye_korelasyon": round(float(np.corrcoef(R.ls, R.seviye)[0, 1]), 2),
                              "diklestirici_pay": round(float(R.dik.mean()) * 100, 0),
                              "gecikme": {str(L): round(float(R[f"ls{L}"].dropna().mean()), 1) for L in GECIKMELER}},
            "en_iyi_uzun": {**_oz(R.uzun), "yarilar": _yarilar(R, "uzun")},
            "esit_uzun": {**_oz(R.esit), "yarilar": _yarilar(R, "esit")},
            "sabit_1s7s_dik": {**_oz(R.dik17), "yarilar": _yarilar(R, "dik17")},
            "sabit_2s7s_dik": {**_oz(R.dik27), "yarilar": _yarilar(R, "dik27")},
            "secim_uzun": {d: int((R.hi == d).sum()) for d in TENOR},
            "secim_kisa": {d: int((R.lo == d).sum()) for d in TENOR}}


def fonlama_gecis(egri: pd.DataFrame, tb_tablo: pd.DataFrame) -> dict:
    """TLREF'in çıpası (politika · koridor üstü · koridor altı) değiştiğinde eğri ne yaptı.
    En az on iş günü süren çıpa blokları arasındaki geçişler; geçişten önceki kapanıştan
    20 iş günü sonrasına ve — geçişi fark edip beş gün sonra girene — 5. günden 25.
    güne getiri değişimi (bp)."""
    c = tb_tablo["cipa"].dropna()
    blok = (c != c.shift()).cumsum()
    bl = [(x.iloc[0], x.index[0], len(x)) for _, x in c.groupby(blok)]
    tut = [b for b in bl if b[2] >= 10]
    N = egri[DUGUM].dropna() * 100
    olay = []
    for p, q in zip(tut, tut[1:]):
        if p[0] == q[0]:
            continue
        j = N.index.searchsorted(q[1])
        if j - 1 < 0 or j + 25 >= len(N):
            continue
        d20 = N.iloc[j + 20] - N.iloc[j - 1]
        d525 = N.iloc[j + 25] - N.iloc[j + 5]
        olay.append({"t": str(q[1].date()), "gecis": f"{p[0]}>{q[0]}", "gun": int(q[2]),
                     **{f"d20_{k}": float(d20[k]) for k in DUGUM},
                     **{f"d525_{k}": float(d525[k]) for k in DUGUM}})
    E = pd.DataFrame(olay)
    out = {"n": int(len(E)), "blok_n": int(len(tut)), "gecis": {}}
    for g, x in E.groupby("gecis"):
        out["gecis"][g] = {"n": int(len(x)), "tarih": list(x.t),
                           "d20": {k: round(float(x[f"d20_{k}"].mean()), 0) for k in DUGUM},
                           "d525": {k: round(float(x[f"d525_{k}"].mean()), 0) for k in DUGUM},
                           "d20_2y_isaret": int((x["d20_n2y"] > 0).sum())}
    return out


def fly_tasima_haritasi(A: pd.DataFrame, V: np.ndarray, egri: pd.DataFrame, fon: pd.DataFrame) -> dict:
    """Çıpa eğrisinde 1–7 yıllık düğümlerden kurulabilen on fly, iki ağırlıkla. Her biri
    için: kotasyon seviyesi (50:50 → 2·gövde − kanatlar; PCA → gövde − a·kanat₁ −
    b·kanat₂), tarihsel yüzdeliği ve son 36 ay sonuna göre z'si, LONG fly'ın (gövdede
    pay, kanatlarda receive) üç aylık taşıma + roll'u GÖVDE DV01'İ BAŞINA bp, aylık
    oynaklık (aynı P&L biriminde), taşıma/üç aylık oynaklık ve yarı ömür. Sinyal: z ≥ +1
    → fly pahalı (gövde ucuz) → short fly; z ≤ −1 → long fly."""
    import itertools
    row = egri[DUGUM].dropna().iloc[-1]
    tl = float(fon["tlref"].dropna().iloc[-1])
    be = {d: _basabas(row, tl, UFUK_GUN, T) for d, T in TENOR.items()}
    parca = {d: _basabas_parca(row, tl, UFUK_GUN, T) for d, T in TENOR.items()}
    S = A * 100
    out = {}
    for k1, g, k2 in itertools.combinations(list(TENOR), 3):
        a, b = fly_agirlik(V, k1, g, k2)
        ad = f"{k1[1:]}{g[1:]}{k2[1:]}"
        for w, (wa, wb) in (("50", (0.5, 0.5)), ("pca", (a, b))):
            P_ = S[g] - wa * S[k1] - wb * S[k2]                 # P&L birimi: gövde DV01'i başına
            kot = 2 * P_ if w == "50" else P_
            sig = float(P_.diff().std())
            tas = -(be[g] - wa * be[k1] - wb * be[k2])
            g36 = kot.iloc[-37:-1]
            z = (float(kot.iloc[-1]) - g36.mean()) / g36.std()
            sinyal = "short" if z >= 1 else ("long" if z <= -1 else "yok")
            out[f"{ad}_{w}"] = {
                "a": round(wa, 3), "b": round(wb, 3), "seviye_bp": round(float(kot.iloc[-1]), 0),
                "yuzdelik": round(float((kot < kot.iloc[-1]).mean()) * 100, 0), "z36": round(float(z), 2),
                "tasima_long_bp": round(tas, 0), "sigma_bp_ay": round(sig, 0),
                "tasima_parca_bp": round(-(parca[g][0] - wa * parca[k1][0] - wb * parca[k2][0]), 0),
                "roll_parca_bp": round(-(parca[g][1] - wa * parca[k1][1] - wb * parca[k2][1]), 0),
                "tasima_sigma": round(tas / (sig * math.sqrt(3)), 2),
                "yari_omur_ay": round(yari_omur(P_), 1), "sinyal": sinyal,
                "tasima_uyumlu": None if sinyal == "yok" else bool((tas > 0) == (sinyal == "long")),
            }
    return {"gun": str(row.name.date()), "basabas_bp": {d: round(x, 0) for d, x in be.items()},
            "tasima_bp": {d: round(p[0], 0) for d, p in parca.items()},
            "roll_bp": {d: round(p[1], 0) for d, p in parca.items()}, "fly": out}


FILTRE_FLY = (("n2y", "n5y", "n7y"), ("n1y", "n2y", "n5y"), ("n3y", "n5y", "n7y"), ("n2y", "n3y", "n5y"))


def fly_tasima_filtresi(egri: pd.DataFrame, on: pd.Series) -> dict:
    """Ortalamaya dönüş kuralının (fly_orneklem_disi, PCA) TAŞIMA ile birleşimi, dört
    fly'da örneklem dışı. P&L gövde DV01'i başına bp, 3 ay. Kollar:
      dönüş        |z| ≥ 1, ortalamaya doğru
      uyumlu       dönüş işlemi, sinyal anındaki taşıması aynı yönde olanlar
      ters         dönüş işlemi, taşıması ters yönde olanlar
      taşıma       her ay, taşımanın işareti yönünde (z'ye bakmadan)
      hep long     her ay long fly (gövdede pay) — kıyas
    Ağırlık ve z geçmişi bir önceki ay sonuna kadar; sinyal eğrisi beş iş günü önce.
    Gecikme profili: aynı kurallar 1 · 5 · 10 · 21 iş günü önceki eğriyle."""
    A = ay_sonu(egri)
    D = A.diff().dropna() * 100
    N = egri[DUGUM].dropna()
    idx = A.index
    out = {}
    for k1, g, k2 in FILTRE_FLY:
        rec = []
        for i in range(37, len(idx) - 3):
            t, tp = idx[i], idx[i - 1]
            _, Vt = pca(D.loc[:tp].to_numpy())
            a, b = fly_agirlik(Vt, k1, g, k2)
            giris = N.loc[:t].index[-1]
            jg = N.index.get_loc(giris)
            re = N.loc[giris]
            one = float(on.loc[:giris].iloc[-1])
            bg_ = {d: _basabas(re, one, UFUK_GUN, TENOR[d]) for d in (k1, g, k2)}
            F = (A[g] - a * A[k1] - b * A[k2]) * 100
            gec = F.loc[:tp].iloc[-36:]
            r = {"t0": t, "long": F.iloc[i + 3] - F.loc[t] - (bg_[g] - a * bg_[k1] - b * bg_[k2])}
            for L in GECIKMELER:
                sig = N.index[jg - L]
                rs = N.loc[sig]
                ons = float(on.loc[:sig].iloc[-1])
                bs = {d: _basabas(rs, ons, UFUK_GUN, TENOR[d]) for d in (k1, g, k2)}
                r[f"z{L}"] = (float((rs[g] - a * rs[k1] - b * rs[k2]) * 100) - gec.mean()) / gec.std()
                r[f"c{L}"] = -(bs[g] - a * bs[k1] - b * bs[k2])
            rec.append(r)
        R = pd.DataFrame(rec)

        def kollar(L: int) -> dict:
            z, c = R[f"z{L}"], R[f"c{L}"]
            mr = R[z.abs() >= 1].copy()
            yon = -np.sign(z[z.abs() >= 1])
            mr["pnl"] = yon * mr.long
            uy = mr[np.sign(c[z.abs() >= 1]) == yon]
            te = mr[np.sign(c[z.abs() >= 1]) != yon]
            ta = R.assign(pnl=np.sign(c) * R.long)
            return {"donus": mr, "uyumlu": uy, "ters": te, "tasima": ta}

        K = kollar(GECIKME)
        blok = {k: {**_oz(v.pnl), "yarilar": _yarilar(v, "pnl")} for k, v in K.items()}
        blok["tasima"]["t"] = round(_nw_t(K["tasima"].pnl), 1)
        blok["hep_long"] = {**_oz(R.long), "t": round(_nw_t(R.long), 1), "yarilar": _yarilar(R, "long")}
        blok["gecikme"] = {}
        for L in GECIKMELER:
            KL = kollar(L)
            blok["gecikme"][str(L)] = {k: round(float(KL[k].pnl.mean()), 1) for k in ("donus", "uyumlu", "ters", "tasima")}
        out[f"{k1[1:]}{g[1:]}{k2[1:]}"] = blok
    return out


def fly_pnl_ayrisimi(A: pd.DataFrame, V: np.ndarray) -> dict:
    """Long fly'ın aylık hareketi (gövde DV01'i başına bp; 50:50'de gövde − ½·kanatlar)
    faktörlere ayrılır: ΔF = Σ_k c_k·s_k + ε, c_k = v_{k,g} − a·v_{k,1} − b·v_{k,2},
    s_k k'nıncı bileşenin aylık skoru. Varyans payı = cov(parça, ΔF)/var(ΔF). Tam örneklem
    PCA'sında PCA fly'ın seviye ve eğim payı TANIM GEREĞİ sıfırdır; asıl bilgi, ağırlığı
    yalnız GEÇMİŞ 60 aydan kurulan fly'ın gerçekleşen sızıntısıdır (seviye ve eğim
    skoruyla korelasyon)."""
    D = A.diff().dropna() * 100
    s = D.to_numpy() @ V[:, :3]
    idx = {d: j for j, d in enumerate(DUGUM)}
    out = {}
    for k1, g, k2 in (("n2y", "n5y", "n7y"), ("n1y", "n2y", "n5y")):
        a, b = fly_agirlik(V, k1, g, k2)
        ad = f"{k1[1:]}{g[1:]}{k2[1:]}"
        for w, (wa, wb) in (("50", (0.5, 0.5)), ("pca", (a, b))):
            dF = (D[g] - wa * D[k1] - wb * D[k2]).to_numpy()
            c = [V[idx[g], k] - wa * V[idx[k1], k] - wb * V[idx[k2], k] for k in range(3)]
            parca = {n: c[k] * s[:, k] for k, n in enumerate(("seviye", "egim", "bukum"))}
            parca["artik"] = dF - sum(parca.values())
            v = dF.var(ddof=1)
            out[f"{ad}_{w}"] = {
                "sigma": round(float(dF.std(ddof=1)), 0),
                "pay": {n: round(float(np.cov(p, dF)[0, 1] / v) * 100, 0) for n, p in parca.items()},
                "sd": {n: round(float(p.std(ddof=1)), 0) for n, p in parca.items()},
                "c": [round(x, 3) for x in c],
            }
        # geçmiş 60 aylık ağırlıkla kurulan fly'ın gerçekleşen sızıntısı
        dfs, s1, s2, ag = [], [], [], []
        for i in range(60, len(D)):
            _, Vt = pca(D.iloc[i - 60:i].to_numpy())
            aa, bb = fly_agirlik(Vt, k1, g, k2)
            ag.append((aa, bb))
            dfs.append(D[g].iloc[i] - aa * D[k1].iloc[i] - bb * D[k2].iloc[i])
            s1.append(s[i, 0])
            s2.append(s[i, 1])
        aa_, bb_ = np.array([x[0] for x in ag]), np.array([x[1] for x in ag])
        out[f"{ad}_pca60"] = {"n": len(dfs),
                              "korelasyon_seviye": round(float(np.corrcoef(dfs, s1)[0, 1]), 2),
                              "korelasyon_egim": round(float(np.corrcoef(dfs, s2)[0, 1]), 2),
                              "a_aralik": [round(float(aa_.min()), 2), round(float(aa_.max()), 2)],
                              "b_aralik": [round(float(bb_.min()), 2), round(float(bb_.max()), 2)],
                              "son": [round(float(aa_[-1]), 3), round(float(bb_[-1]), 3)],
                              "a_aylik_degisim_medyan": round(float(np.median(np.abs(np.diff(aa_)))), 3)}
        for w, (wa, wb) in (("50", (0.5, 0.5)), ("pca", (a, b))):
            dF = (D[g] - wa * D[k1] - wb * D[k2]).to_numpy()[60:]
            out[f"{ad}_{w}"]["korelasyon_seviye_60"] = round(float(np.corrcoef(dF, s1)[0, 1]), 2)
            out[f"{ad}_{w}"]["korelasyon_egim_60"] = round(float(np.corrcoef(dF, s2)[0, 1]), 2)
    return out


def donum_noktalari(egri: pd.DataFrame, ppk: pd.DataFrame, V: np.ndarray) -> list[dict]:
    """PPK döngüsünün dönüm noktaları: faiz değişiminin işaretinin tersine döndüğü kararlar
    (arşivdeki ilk değişim, öncesi bilinmediği için işaretli). Karardan önceki kapanıştan
    1 · 3 · 6 ay (21 · 63 · 126 iş günü) sonrasına yapı hareketleri, bp. Yedi olay: istatistik
    değil vaka."""
    a, b = fly_agirlik(V, "n2y", "n5y", "n7y")
    a2, b2 = fly_agirlik(V, "n1y", "n2y", "n5y")
    N = egri[DUGUM].dropna() * 100
    Y = pd.DataFrame({"2y": N.n2y, "5y": N.n5y, "2s5s": N.n5y - N.n2y, "2s7s": N.n7y - N.n2y,
                      "2y5y7y_pca": N.n5y - a * N.n2y - b * N.n7y,
                      "1y2y5y_pca": N.n2y - a2 * N.n1y - b2 * N.n5y})
    d = ppk["politika"].diff()
    d = d[d.notna() & (d != 0)]
    isaret = np.sign(d)
    donus = isaret[isaret != isaret.shift()]
    out = []
    for t, s in donus.items():
        j = Y.index.searchsorted(t)
        if j - 1 < 0:
            continue
        rec = {"tarih": str(t.date()), "yon": "artırım" if s > 0 else "indirim",
               "adim_bp": round(float(d[t]) * 100, 0), "arsiv_basi": bool(t == d.index[0]), "hareket": {}}
        for ad, n in (("1a", 21), ("3a", 63), ("6a", 126)):
            if j + n < len(Y):
                rec["hareket"][ad] = {k: round(float(Y[k].iloc[j + n] - Y[k].iloc[j - 1]), 0) for k in Y.columns}
        out.append(rec)
    return out


def tumsek_konumu(A: pd.DataFrame, P: pd.DataFrame) -> dict:
    """Eğrinin tepesi (ay sonu en yüksek getirili düğüm) nerede ve ne kadar kalıyor.
    Roll-down işlemi 'tümsek yerinde kalır' bahsidir: tepenin tarihsel yeri, sürelerinin
    ortalaması (ardışık ay bloğu) ve her vadede roll'un pozitif olduğu pencere payı."""
    tepe = A[DUGUM].idxmax(axis=1)
    blok = (tepe != tepe.shift()).cumsum()
    sure = tepe.groupby(blok).agg(["first", "size"])
    son36 = tepe.iloc[-36:]
    return {"n": int(len(tepe)),
            "pay": {d: round(float((tepe == d).mean()) * 100, 0) for d in DUGUM},
            "pay_son36": {d: round(float((son36 == d).mean()) * 100, 0) for d in DUGUM},
            "ort_sure_ay": {d: round(float(sure[sure["first"] == d]["size"].mean()), 1)
                            for d in DUGUM if (sure["first"] == d).any()},
            "bugun": str(tepe.iloc[-1]),
            "bugun_sure_ay": int(sure["size"].iloc[-1]),
            "roll_pozitif": {d: round(float((P[P.d == d].roll > 0).mean()) * 100, 0) for d in TENOR}}


def senaryo_matrisi(rj: dict, be: dict, V: np.ndarray) -> dict:
    """Bugünkü taşıma + roll (çıpa eğrisi, TLREF sabit, 3 ay) ile her rejimde ölçülmüş
    eğri HAREKETİNİN toplamı: 'bu beklentideysem bu yapı ne getirir'. Hareket bileşeni
    tarihseldir (rejimin ortalaması, çeyrekler arası aralığıyla), taşıma bileşeni
    bugünündür — ikisi ayrı yazılır, çünkü tarihsel pencerelerin taşıması bugünkünden
    farklıydı. DV01 başına bp. Tahmin değildir; görüş doğruysa ne olduğunun ölçüsüdür."""
    Y = _yapilar(V)
    out = {}
    for ad, w in Y.items():
        tas = sum(wi * be[d] for d, wi in w.items())
        s = {"tasima_bugun": round(tas, 0)}
        for grup, anahtar in (("faz", ("indirim", "sabit", "artırım")), ("kova", ("guvercin", "orta", "sahin")),
                              ("kuyruk", ("satis", "ralli"))):
            for k in anahtar:
                h = rj[grup][ad][k]
                s[k] = {"ort": round(tas + h["hareket"], 0), "p25": round(tas + h["hareket_p25"], 0),
                        "p75": round(tas + h["hareket_p75"], 0)}
        out[ad] = s
    return out


def ois_fly(bg: dict, V: np.ndarray) -> dict:
    """Temsili OIS eğrisinde LONG fly'lar: gövdede 100 mn TL PAY, kanatlarda RECEIVE.
    Aracın yöntemiyle (doğrusal ara değer, çeyreklik annüite, iskonto 1/(1 + z·t)); ufuk
    92 gün, fixing sabit. Her bacak için nominal, DV01, taşıma ve roll; net yüzen bacak
    (receive edilen yüzen − ödenen yüzen) ve TLREF'in 100 bp yükselmesinin çeyreklik
    taşımaya etkisi. Taşıma iki fixingle: temsili eğrinin kendi fixingi ve 22.09.2026
    fixingi (eğri aynı; yalnız fixing bacağı değişir)."""
    T_ = TEMSILI_OIS
    h = 92

    def F(r: float) -> float:
        return ((1 + r / 100 / 365) ** h - 1) * 365 / h * 100

    def bacak(T: float, N: float, yon: int, r: float) -> dict:
        """yon +1 receive (sabit al), −1 pay."""
        K = _arac_oran(T)
        Th = max(T - h / 365, 1 / 365)
        A_T, A_Th, S = _arac_annuite(T), _arac_annuite(Th), _arac_oran(Th)
        return {"K": K, "S_Th": round(S, 2), "dv01": A_T * N * 1e-4,
                "tasima": yon * (K - F(r)) / 100 * h / 365 * N, "roll": yon * (K - S) / 100 * A_Th * N}

    Nb = 100e6
    out = {"cipa": T_["cipa"], "tlref": T_["tlref"], "tlref_bugun": bg["tlref"], "gun": h, "govde_nominal_mn": 100}
    for k1, g, k2 in (("2y", "5y", "7y"), ("1y", "2y", "5y")):
        T1, Tg, T2 = (float(x[:-1]) for x in (k1, g, k2))
        dvb = _arac_annuite(Tg) * Nb * 1e-4
        a, b = fly_agirlik(V, f"n{k1}", f"n{g}", f"n{k2}")
        blok = {"govde_dv01": round(dvb, 0), "fly_10bp_bin": round(10 * dvb / 1e3, 0)}
        for kural, (wa, wb) in (("5050", (0.5, 0.5)), ("pca", (a, b))):
            N1 = wa * dvb / (_arac_annuite(T1) * 1e-4)
            N2 = wb * dvb / (_arac_annuite(T2) * 1e-4)
            L = {k1: bacak(T1, N1, +1, T_["tlref"]), g: bacak(Tg, Nb, -1, T_["tlref"]), k2: bacak(T2, N2, +1, T_["tlref"])}
            Lb = {k1: bacak(T1, N1, +1, bg["tlref"]), g: bacak(Tg, Nb, -1, bg["tlref"]), k2: bacak(T2, N2, +1, bg["tlref"])}
            Lu = {k1: bacak(T1, N1, +1, T_["tlref"] + 1), g: bacak(Tg, Nb, -1, T_["tlref"] + 1),
                  k2: bacak(T2, N2, +1, T_["tlref"] + 1)}
            tas = sum(x["tasima"] for x in L.values())
            rol = sum(x["roll"] for x in L.values())
            tas_b = sum(x["tasima"] for x in Lb.values())
            tas_u = sum(x["tasima"] for x in Lu.values())
            blok[kural] = {
                "agirlik": [round(wa, 3), round(wb, 3)],
                "nominal_mn": {k1: round(N1 / 1e6, 1), g: 100.0, k2: round(N2 / 1e6, 1)},
                "K": {k: round(v["K"], 2) for k, v in L.items()},
                "S_Th": {k: v["S_Th"] for k, v in L.items()},
                "tasima_bin": {k: round(v["tasima"] / 1e3, 0) for k, v in L.items()},
                "roll_bin": {k: round(v["roll"] / 1e3, 0) for k, v in L.items()},
                "tasima_mn": round(tas / 1e6, 2), "roll_mn": round(rol / 1e6, 2),
                "toplam_mn": round((tas + rol) / 1e6, 2), "toplam_bp_govde": round((tas + rol) / dvb, 0),
                "tasima_bugun_mn": round(tas_b / 1e6, 2), "toplam_bugun_mn": round((tas_b + rol) / 1e6, 2),
                "toplam_bugun_bp_govde": round((tas_b + rol) / dvb, 0),
                "net_yuzen_mn": round((Nb - N1 - N2) / 1e6, 1),
                "tlref_100_etkisi_bin": round((tas_u - tas) / 1e3, 0),
            }
        out[f"{k1}{g}{k2}"] = blok
    return out


def ois_roll_haritasi() -> dict:
    """Temsili OIS eğrisinde receive pozisyonunun üç aylık taşıma ve roll'u, vade vade,
    DV01 başına bp (aracın yöntemi; fixing temsili TLREF'te sabit). Ters eğride receive
    her iki bileşeni de öder; pay her ikisini de kazanır."""
    T_ = TEMSILI_OIS
    h, N = 92, 100e6

    def F(r: float) -> float:
        return ((1 + r / 100 / 365) ** h - 1) * 365 / h * 100

    out = {}
    for v, T in (("6m", 0.5), ("9m", 0.75), ("1y", 1.0), ("18m", 1.5), ("2y", 2.0), ("3y", 3.0),
                 ("4y", 4.0), ("5y", 5.0), ("7y", 7.0), ("10y", 10.0)):
        K = _arac_oran(T)
        Th = max(T - h / 365, 1 / 365)
        dv = _arac_annuite(T) * N * 1e-4
        tas = (K - F(T_["tlref"])) / 100 * h / 365 * N
        rol = (K - _arac_oran(Th)) / 100 * _arac_annuite(Th) * N
        out[v] = {"K": round(K, 2), "S_Th": round(_arac_oran(Th), 2), "dv01": round(dv, 0),
                  "tasima_bp": round(tas / dv, 0), "roll_bp": round(rol / dv, 0),
                  "toplam_bp": round((tas + rol) / dv, 0)}
    return out


def ihale_etkisi(egri: pd.DataFrame, ih: pd.DataFrame, V: np.ndarray) -> dict:
    """Sabit kuponlu ihale günlerinde ihale edilen vadenin gövde olduğu fly: ihaleden
    önceki beş iş günü ve sonraki beş iş günü değişimi (bp), ortalama, medyan ve t.
    Hipotez (arz gövdeyi ucuzlatır, ihaleden sonra geri döner) ancak işaret, büyüklük ve
    ortalama–medyan birlikte tutarsa bir kuraldır."""
    N = egri[DUGUM].dropna() * 100
    sab = ih[ih["tur"].str.contains("Sabit")]
    out = {}
    for ad, (lo, hi), (k1, g, k2) in (("2y", (1.5, 2.5), ("n1y", "n2y", "n3y")),
                                      ("5y", (4.3, 5.7), ("n3y", "n5y", "n7y"))):
        gun = sorted(set(sab[(sab.vade_yil >= lo) & (sab.vade_yil <= hi)].index))
        a, b = fly_agirlik(V, k1, g, k2)
        blok = {}
        for w, (wa, wb) in (("50", (0.5, 0.5)), ("pca", (a, b))):
            F = N[g] - wa * N[k1] - wb * N[k2]
            if w == "50":
                F = 2 * F
            once, sonra = [], []
            for t in gun:
                j = F.index.searchsorted(t)
                if j - 5 < 0 or j + 5 >= len(F):
                    continue
                once.append(F.iloc[j] - F.iloc[j - 5])
                sonra.append(F.iloc[j + 5] - F.iloc[j])
            o_, s_ = np.array(once), np.array(sonra)
            taban = F.diff(5).dropna().loc["2020":]
            blok[w] = {"n": int(len(o_)),
                       "once_ort": round(float(o_.mean()), 1), "once_medyan": round(float(np.median(o_)), 1),
                       "once_t": round(float(o_.mean() / (o_.std(ddof=1) / math.sqrt(len(o_)))), 2),
                       "sonra_ort": round(float(s_.mean()), 1), "sonra_medyan": round(float(np.median(s_)), 1),
                       "sonra_t": round(float(s_.mean() / (s_.std(ddof=1) / math.sqrt(len(s_)))), 2),
                       "taban_sd": round(float(taban.std()), 0)}
        out[ad] = {"fly": f"{k1[1:]}{g[1:]}{k2[1:]}", **blok}
    return out


def tasima_ufuk(egri: pd.DataFrame, fon: pd.DataFrame) -> dict:
    """Çıpa eğrisinde taşıma + roll'un iki ufukta (1 ay = 30 gün, 3 ay = 91 gün) ölçüsü:
    taşıma, roll, toplam (fiyatın %'si) ve başabaş (bp). Başabaş ufukla doğrusal
    büyümez: roll eğrinin YEREL eğimidir ve ufuk uzadıkça eğrinin başka bir parçasına
    kayılır. Ayrıca ufuk sonunda başabaşı sağlayan FORWARD getiri: T − h vadenin t₀
    eğrisindeki getirisine başabaş eklenir (eğri o forward'a gelirse fazla getiri sıfır)."""
    t = egri[DUGUM].dropna().index[-1]
    row = egri.loc[t]
    tl = float(fon["tlref"].dropna().iloc[-1])
    out = {"gun": str(t.date()), "tlref": tl}
    for hg in (30, 91):
        blok = {}
        for T in (0.5, 1.0, 2.0, 3.0, 5.0, 7.0):
            y = _y(row, T)
            D = T / (1 + y)
            cr = taşıma_roll(row, tl, hg, T) * 100
            tas = ((1 + y) ** (hg / 365) - 1 - ((1 + tl / 100 / 365) ** hg - 1)) * 100
            be = cr / D * 100
            yTh = _y(row, T - hg / 365) * 100
            blok[f"{T:g}"] = {"tasima": round(tas, 2), "roll": round(cr - tas, 2), "toplam": round(cr, 2),
                              "basabas_bp": round(be, 0), "getiri_Th": round(yTh, 2),
                              "forward": round(yTh + be / 100, 2)}
        out[f"h{hg}"] = blok
    return out


def kuponlu_tasima(bg: dict, egri: pd.DataFrame) -> dict:
    """Kuponlu 5 yıllık kâğıdın (yıllık kupon %35, altı ayda bir) taşıması üç parça ve
    roll: 100 TL nominal başına, 1 ve 3 aylık ufuk, çıpa eğrisi, fonlama TLREF (bileşik).
      kupon tahakkuku  = kupon × gün/365
      fiyat çekimi     = aynı getiride vadenin kısalmasının temiz fiyata etkisi (primli
                         kâğıtta eksi — kâğıt par'a doğru çekilir)
      fonlama          = kirli fiyat × fonlamanın bileşiği
      roll             = getiri eğri boyunca kısalmış vadenin getirisine kaydığında fiyat farkı
    Kâğıt çıpada ihraç edilmiş sayılır (birikmiş faiz sıfır). Nakit akışları tek getiriyle
    yıllık bileşik iskonto edilir (1.2'deki durasyon tablosuyla aynı kural)."""
    y5 = bg["egri"]["n5y"] / 100
    row = egri[DUGUM].dropna().iloc[-1]
    tl = bg["tlref_tam"]
    kupon = 0.35

    def fiyat(y: float, kalan: float) -> float:
        """Kalan vadesi `kalan` yıl, altı ayda bir kupon; kirli fiyat."""
        ak = []
        x = kalan
        while x > 1e-9:
            ak.append(x)
            x -= 0.5
        return sum((kupon / 2 * 100 + (100 if abs(tt - kalan) < 1e-9 else 0)) * (1 + y) ** (-tt) for tt in ak)

    P0 = fiyat(y5, 5.0)
    kalan0 = [5.0 - 0.5 * i for i in range(10)]
    mac = sum(tt * (kupon / 2 * 100 + (100 if i == 0 else 0)) * (1 + y5) ** (-tt)
              for i, tt in enumerate(kalan0)) / P0
    Dm = mac / (1 + y5)
    out = {"kupon": 35, "getiri": round(y5 * 100, 2), "fiyat": round(P0, 2), "mod_dur": round(Dm, 2)}
    for hg in (30, 91):
        h = hg / 365
        # vade kısalınca kalan akışlar: t − h; kupon tarihi geçmediği için hepsi korunur
        kalan = [5.0 - 0.5 * i for i in range(10)]
        ak = [x - h for x in kalan]
        P_ayni = sum((kupon / 2 * 100 + (100 if i == 0 else 0)) * (1 + y5) ** (-tt) for i, tt in enumerate(ak))
        y_roll = _y(row, 5.0 - h)
        P_roll = sum((kupon / 2 * 100 + (100 if i == 0 else 0)) * (1 + y_roll) ** (-tt) for i, tt in enumerate(ak))
        birikmis = kupon * 100 * h
        tahakkuk = birikmis
        cekim = (P_ayni - birikmis) - P0          # temiz fiyatın değişimi, getiri sabit
        fonlama = P0 * ((1 + tl / 100 / 365) ** hg - 1)
        roll = P_roll - P_ayni
        out[f"h{hg}"] = {"kupon_tahakkuku": round(tahakkuk, 3), "fiyat_cekimi": round(cekim, 3),
                         "fonlama": round(-fonlama, 3), "tasima": round(tahakkuk + cekim - fonlama, 3),
                         "roll": round(roll, 3), "toplam": round(tahakkuk + cekim - fonlama + roll, 3),
                         "getiri_tahakkuku": round(P0 * ((1 + y5) ** h - 1), 3),
                         "tasima_yuzde": round((tahakkuk + cekim - fonlama) / P0 * 100, 2),
                         "roll_yuzde": round(roll / P0 * 100, 2),
                         "toplam_yuzde": round((tahakkuk + cekim - fonlama + roll) / P0 * 100, 2),
                         "basabas_bp": round((tahakkuk + cekim - fonlama + roll) / P0 / Dm * 1e4, 0)}
    return out


def tasima_oynaklik(egri: pd.DataFrame, fon: pd.DataFrame, A: pd.DataFrame, V: np.ndarray) -> dict:
    """Çıpa eğrisinde yapıların üç aylık taşıma + roll'u (yapının kendi P&L biriminde:
    DV01 başına bp) ile son 36 ayın aylık oynaklığının oranı. Outright uzun (receive),
    spread dikleştirici yönünde (kısa vade uzun / uzun vade kısa, DV01-nötr), fly long
    yönde (gövdede pay). Oran = taşıma / (σ·√3); short yönün oranı aynı sayının eksisidir."""
    row = egri[DUGUM].dropna().iloc[-1]
    tl = float(fon["tlref"].dropna().iloc[-1])
    be = {d: _basabas(row, tl, UFUK_GUN, T) for d, T in TENOR.items()}
    S = A * 100
    Y = {}
    for d in TENOR:
        Y[f"{d[1:]}_receive"] = ({d: 1.0}, S[d])
    for k, u in (("n1y", "n2y"), ("n2y", "n5y"), ("n2y", "n7y"), ("n5y", "n7y")):
        Y[f"{k[1:]}{u[1:]}_diklestirici"] = ({k: 1.0, u: -1.0}, S[u] - S[k])
    for k1, g, k2 in (("n1y", "n2y", "n3y"), ("n1y", "n2y", "n5y"), ("n2y", "n3y", "n5y"),
                      ("n2y", "n5y", "n7y"), ("n3y", "n5y", "n7y")):
        a, b = fly_agirlik(V, k1, g, k2)
        ad = f"{k1[1:]}{g[1:]}{k2[1:]}"
        for w, (wa, wb) in (("50", (0.5, 0.5)), ("pca", (a, b))):
            Y[f"{ad}_long{w}"] = ({g: -1.0, k1: wa, k2: wb}, S[g] - wa * S[k1] - wb * S[k2])
    out = {"gun": str(row.name.date())}
    for ad, (w, seri) in Y.items():
        tas = sum(wi * be[d] for d, wi in w.items())
        # P&L serisi: receive/dikleştirici/long fly yönünde getiri düşüşü kazançtır;
        # oynaklık için işaret önemsiz
        s36 = float(seri.diff().iloc[-36:].std())
        out[ad] = {"tasima_bp": round(tas, 0), "sigma36_bp_ay": round(s36, 0),
                   "oran": round(tas / (s36 * math.sqrt(3)), 2)}
    return out


def yapi_stres(A: pd.DataFrame, V: np.ndarray) -> dict:
    """Yapıların aylık hareketinin uçları (bp, P&L birimi: spread'de uzun − kısa, fly'da
    gövde DV01'i başına): tam örneklem ve son 36 ay σ'sı, en büyük aylık yükseliş ve
    düşüş, mutlak hareketin 95. yüzdeliği. Stop ve boyut bu dağılımdan kalibre edilir."""
    S = A * 100
    Y = {"1y2y": S.n2y - S.n1y, "2s5s": S.n5y - S.n2y, "2s7s": S.n7y - S.n2y, "5s7s": S.n7y - S.n5y}
    for k1, g, k2 in (("n1y", "n2y", "n3y"), ("n1y", "n2y", "n5y"), ("n2y", "n3y", "n5y"),
                      ("n2y", "n5y", "n7y"), ("n3y", "n5y", "n7y")):
        a, b = fly_agirlik(V, k1, g, k2)
        ad = f"{k1[1:]}{g[1:]}{k2[1:]}"
        Y[f"{ad}_50"] = S[g] - 0.5 * S[k1] - 0.5 * S[k2]
        Y[f"{ad}_pca"] = S[g] - a * S[k1] - b * S[k2]
    out = {}
    for ad, s in Y.items():
        d = s.diff().dropna()
        out[ad] = {"sigma": round(float(d.std()), 0), "sigma36": round(float(d.iloc[-36:].std()), 0),
                   "en_buyuk_artis": [round(float(d.max()), 0), str(d.idxmax().date())[:7]],
                   "en_buyuk_dusus": [round(float(d.min()), 0), str(d.idxmin().date())[:7]],
                   "p95": round(float(d.abs().quantile(0.95)), 0)}
    return out


def ppk_gunu_yapi(egri: pd.DataFrame, ppk: pd.DataFrame, V: np.ndarray) -> dict:
    """PPK karar günlerinde spread ve fly'ların iki günlük hareketi (ppk_gunu ile aynı
    pencere), diğer günlerle kıyaslı: mutlak hareketin medyanı ve 90. yüzdeliği (bp)."""
    N = egri[DUGUM].dropna() * 100
    Y = {"2s5s": N.n5y - N.n2y, "2s7s": N.n7y - N.n2y}
    for k1, g, k2 in (("n1y", "n2y", "n3y"), ("n1y", "n2y", "n5y"), ("n2y", "n5y", "n7y"), ("n3y", "n5y", "n7y")):
        a, b = fly_agirlik(V, k1, g, k2)
        Y[f"{k1[1:]}{g[1:]}{k2[1:]}_pca"] = N[g] - a * N[k1] - b * N[k2]
    gun = [t for t in ppk.index if t in N.index]
    m = N.index.isin(gun)
    out = {}
    for ad, s in Y.items():
        d2 = s.diff(2).shift(-1)
        a_, b_ = d2[m].abs().dropna(), d2[~m].abs().dropna()
        out[ad] = {"ppk_medyan": round(float(a_.median()), 0), "ppk_p90": round(float(a_.quantile(0.9)), 0),
                   "diger_medyan": round(float(b_.median()), 0), "diger_p90": round(float(b_.quantile(0.9)), 0)}
    return out


def oynaklik_barbell(egri: pd.DataFrame, Y: pd.DataFrame) -> dict:
    """Long fly = barbell = uzun konveksite: üç aylık pencereleri penceredeki GERÇEKLEŞEN
    seviye oynaklığına (günlük (2y + 7y)/2 değişimlerinin standart sapması) göre üçe
    bölüp long 2y5y7y'nin (50:50 ve PCA) P&L'i. Konveksitenin bu vadelerde küçük
    olduğu metinde sayıyla var; bu ölçü oynaklık görüşünün fly'da ne kadar para ettiğini
    gerçek pencerelerde sorar."""
    N = egri[DUGUM].dropna() * 100
    sev = (N.n2y + N.n7y) / 2
    son = _ay_son_gunleri(egri[DUGUM].dropna())
    oyn = {}
    for i, t0 in enumerate(son[:-3]):
        t1 = son[i + 3]
        oyn[t0] = float(sev.loc[t0:t1].diff().dropna().std())
    o = pd.Series(oyn)
    out = {}
    for ad in ("2y5y7y_long50", "2y5y7y_longpca"):
        y = Y[Y.yapi == ad].set_index("t0")
        y = y.join(o.rename("oyn"), how="inner")
        kova = pd.qcut(y.oyn, 3, labels=["dusuk", "orta", "yuksek"])
        out[ad] = {k: {"n": int((kova == k).sum()), "toplam": round(float(y.toplam[kova == k].mean()), 0),
                       "tasima": round(float(y.tasima[kova == k].mean()), 0),
                       "oynaklik_bp_gun": round(float(y.oyn[kova == k].mean()), 0)} for k in ("dusuk", "orta", "yuksek")}
    return out


def ois_yapilar(bg: dict) -> dict:
    """Temsili OIS eğrisinde DV01-nötr dikleştiriciler (kısa vadede receive, uzun vadede
    pay; kısa bacak 100 mn TL): nominaller, net yüzen nominal, üç aylık taşıma ve roll,
    TLREF'in 100 bp yükselmesinin taşımaya etkisi. DV01-nötr bir OIS yapısı nominal-nötr
    DEĞİLDİR: kısa bacağın nominali uzun bacağınkinden büyüktür ve fark fixinge açıktır."""
    T_ = TEMSILI_OIS
    h = 92

    def F(r: float) -> float:
        return ((1 + r / 100 / 365) ** h - 1) * 365 / h * 100

    def bacak(T: float, N: float, yon: int, r: float) -> tuple[float, float]:
        K = _arac_oran(T)
        Th = max(T - h / 365, 1 / 365)
        return (yon * (K - F(r)) / 100 * h / 365 * N, yon * (K - _arac_oran(Th)) / 100 * _arac_annuite(Th) * N)

    out = {}
    for k, u in ((1.0, 2.0), (2.0, 5.0), (2.0, 10.0)):
        Nk = 100e6
        dvk = _arac_annuite(k) * Nk * 1e-4
        Nu = dvk / (_arac_annuite(u) * 1e-4)
        t1, r1 = bacak(k, Nk, +1, T_["tlref"])
        t2, r2 = bacak(u, Nu, -1, T_["tlref"])
        t1b, _ = bacak(k, Nk, +1, bg["tlref"])
        t2b, _ = bacak(u, Nu, -1, bg["tlref"])
        t1u, _ = bacak(k, Nk, +1, T_["tlref"] + 1)
        t2u, _ = bacak(u, Nu, -1, T_["tlref"] + 1)
        out[f"{k:g}y{u:g}y"] = {"dv01": round(dvk, 0), "nominal_uzun_mn": round(Nu / 1e6, 1),
                                "net_yuzen_mn": round((Nu - Nk) / 1e6, 1),
                                "tasima_mn": round((t1 + t2) / 1e6, 2), "roll_mn": round((r1 + r2) / 1e6, 2),
                                "toplam_mn": round((t1 + t2 + r1 + r2) / 1e6, 2),
                                "toplam_bp": round((t1 + t2 + r1 + r2) / dvk, 0),
                                "tasima_bugun_mn": round((t1b + t2b) / 1e6, 2),
                                "tlref_100_etkisi_bin": round((t1u + t2u - t1 - t2) / 1e3, 0)}
    return out


def ois_kira_fixing(bg: dict) -> dict:
    """Temsili OIS eğrisinde receive'in üç aylık fixing taşıması üç fixing varsayımıyla
    (temsili eğrinin fixingi · politika faizi düzeyi · 22.09.2026 fixingi), DV01 başına
    bp. Roll fixingden bağımsızdır (ois_roll_haritasi)."""
    T_ = TEMSILI_OIS
    h, N = 92, 100e6

    def F(r: float) -> float:
        return ((1 + r / 100 / 365) ** h - 1) * 365 / h * 100

    out = {"fixing": {"temsili": T_["tlref"], "politika": bg["politika"], "bugun": bg["tlref"]}}
    for v, T in (("3m", 0.25), ("6m", 0.5), ("1y", 1.0), ("2y", 2.0), ("5y", 5.0), ("10y", 10.0)):
        K = _arac_oran(T)
        dv = _arac_annuite(T) * N * 1e-4
        out[v] = {"K": round(K, 2), **{ad: round((K - F(r)) / 100 * h / 365 * N / dv, 0)
                                       for ad, r in out["fixing"].items()}}
    for ad, r in out["fixing"].items():
        out[f"F_{ad}"] = round(F(r), 2)
    return out


# ─────────────────────────────────────────────────────────────── hepsi
def hesapla() -> tuple[dict, dict]:
    v = yukle()
    egri, fon, ppk = v["egri"], v["fon"], v["ppk"]
    A = ay_sonu(egri)
    D = (A.diff().dropna() * 100).to_numpy()
    pay, V = pca(D)
    on = gecelik(fon)
    eg = egim_seviye(A)
    kad, kad_tablo = kadran(A, ppk)
    kal, fly_seri = kalicilik(A, V)
    dur, dur_tablo = durasyon(egri, on)
    bg = bugun(egri, fon, A)
    bb = barbell(egri, fon, bg["sigma36"]["n5y"])
    tb, tb_tablo = tlref_baz(fon)
    ozet = {
        "cipa": egri.index.max().strftime("%Y-%m-%d"),
        "pca": {"n": int(len(D)), "ilk": str(A.index[1].date())[:7], "son": str(A.index[-1].date())[:7],
                "pay": [round(float(p) * 100, 1) for p in pay[:3]],
                # yükler dört basamak: PCA-nötr ağırlık 2×2 sistemden çözülür ve iki
                # basamağa yuvarlanmış yüklerle çözüm belirgin kayıyor (0,32 → 0,29)
                "yuk": {f"pc{i + 1}": {d: round(float(V[j, i]), 4) for j, d in enumerate(DUGUM)}
                        for i in range(3)},
                # bileşen skorunun aylık standart sapması (bp): 1σ faktör hareketi
                "sigma_bp_ay": [round(float(np.sqrt(np.var(D @ V[:, i], ddof=1))), 1) for i in range(3)]},
        "pca_frekans": pca_frekans(egri),
        "gurultu": gurultu(egri),
        "egim_seviye": eg,
        "kadran": kad,
        "kalicilik": kal,
        "durasyon": dur,
        "bugun": bg,
        "barbell": bb,
        "tlref_baz": tb,
        "stres": stres(A),
        "ihale": ihale_ozet(v["ihale"]),
        "yapi_bugun": yapi_bugun(fly_seri),
        "kupon_durasyon": kupon_durasyon(bg),
        "ppk_gunu": ppk_gunu(egri, ppk),
        "fly_orneklem_disi": {"ayrik": fly_orneklem_disi(egri, on, True),
                              "ayrismasiz": fly_orneklem_disi(egri, on, False)},
        "katalog": katalog(A, V),
        "yapi_tasima": yapi_tasima(bg, *kal["agirlik_pca"]),
        "faktor_maruziyet": faktor_maruziyet(
            V, [float(np.sqrt(np.var(D @ V[:, k], ddof=1))) for k in range(3)], *kal["agirlik_pca"]),
        "fly_1y2y5y": fly_1y2y5y(A, V, bg),
        "barbell_kurallar": barbell_kurallar(
            egri, fon, V, [float(np.sqrt(np.var(D @ V[:, k], ddof=1))) for k in range(3)],
            bg["sigma36"]["n5y"]),
        "temsili_ois": temsili_ois(bg),
    }
    P = pencereler(egri, on, ppk, tb_tablo["cipa"].dropna())
    rj, rj_tablo = rejim_yapi(P, V)
    ozet.update({
        "tasima_ayristirma": tasima_ayristirma(P),
        "forward_gerceklesme": forward_gerceklesme(P),
        "tasima_stratejileri": tasima_stratejileri(P, A),
        "tumsek": tumsek_konumu(A, P),
        "rejim_yapi": rj,
        "aylik_rejim": aylik_rejim(A, V, kad_tablo["faz"]),
        "senaryo_matrisi": senaryo_matrisi(rj, _bugun_basabas(egri, fon), V),
        "fonlama_gecis": fonlama_gecis(egri, tb_tablo),
        "donum_noktalari": donum_noktalari(egri, ppk, V),
        "fly_tasima_haritasi": fly_tasima_haritasi(A, V, egri, fon),
        "fly_tasima_filtresi": fly_tasima_filtresi(egri, on),
        "fly_pnl_ayrisimi": fly_pnl_ayrisimi(A, V),
        "ois_fly": ois_fly(bg, V),
        "ois_roll_haritasi": ois_roll_haritasi(),
        "ihale_etkisi": ihale_etkisi(egri, v["ihale"], V),
        "tasima_ufuk": tasima_ufuk(egri, fon),
        "kuponlu_tasima": kuponlu_tasima(bg, egri),
        "tasima_oynaklik": tasima_oynaklik(egri, fon, A, V),
        "yapi_stres": yapi_stres(A, V),
        "ppk_gunu_yapi": ppk_gunu_yapi(egri, ppk, V),
        "oynaklik_barbell": oynaklik_barbell(egri, rj_tablo),
        "ois_yapilar": ois_yapilar(bg),
        "ois_kira_fixing": ois_kira_fixing(bg),
    })
    seriler = {"A": A, "V": V, "pay": pay, "kadran": kad_tablo, "fly": fly_seri,
               "durasyon": dur_tablo, "tlref": tb_tablo, "egri": egri,
               "pencere": P, "rejim_yapi": rj_tablo}
    return ozet, seriler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--denetle", action="store_true")
    a = ap.parse_args()
    ozet, _ = hesapla()
    metin = json.dumps(ozet, ensure_ascii=False, indent=1) + "\n"
    if a.denetle:
        eski = CIKTI.read_text(encoding="utf-8") if CIKTI.exists() else ""
        if eski != metin:
            print("DÜŞTÜ: yeniden hesaplanan ölçüm depodaki olcum.json ile aynı değil")
            return 1
        print("GEÇTİ: olcum.json girdi arşivinden birebir yeniden üretiliyor")
        return 0
    CIKTI.write_text(metin, encoding="utf-8")
    print(f"yazıldı: {CIKTI.relative_to(BURASI)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
