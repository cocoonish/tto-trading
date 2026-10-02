#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 11 (Taşıma, UIP, akım, küresel faktör) ölçüm katmanı.

Pratikler
  p11a  TRY Fama β, aylık (ay sonu), 1990–2026: Δs_{t+1} = a + β·(i − i*)_t/12.
        s = log(USD/TRY)×100, i TL gecelik faiz zinciri (bankalararası gecelik
        1990 → TCMB ağırlıklı ortalama fonlama maliyeti 03.01.2011 → TLREF
        28.12.2018), i* ABD politika faizi (BIS). f − s yerine i − i* alınır:
        örtülü faiz paritesi (CIP) VARSAYIMI, çünkü USD/TRY forward serisi yok.
        Alt dönemler 1990–2001, 2002–2017, 2018–2026; yönetilen kur dönemi
        (hedef ay 2021-12 … 2023-06) ayrı satırdır, havuzlanmaz. G10 bacağı
        (EUR, GBP, CHF, JPY, CAD, AUD; CNBC New York 17:00 ay sonu, BIS politika
        faizleri) para başına ve havuzlu (Driscoll–Kraay).
  p11b  EM taşıma sepeti (BRL, MXN, ZAR, INR, TRY), aylık, 2010-02 … 2026-07:
        r_{t+1} = (i − i*)_t/12 − Δs_{t+1}; eşit ağırlıklı sepet; ortalama,
        oynaklık, çarpıklık, en kötü üç ay, azami düşüş; VIX'in aynı ay
        ortalaması genişleyen pencereli 75. yüzdeliği aşınca ve aşmayınca.
        ECB referans kurlarıyla çapraz sınama.
  p11c  Haftalık TRY ve EM sepetinin dolar sepeti (CNBC G10), ΔVIX ve Δ10y'ye
        betaları (dönem regresyonları ve 52 haftalık kayan); TRY'nin EM
        sepetine göre artığı (TRY − β·sepet, β bir önceki 52 haftadan).
  p11d  Yabancı DİBS ve hisse akımı ↔ haftalık ΔUSD/TRY ve Δ2y, 2020-09+.
  p11e  TRY ex-ante UIP primi (PKA 12 ay sonrası kur beklentisi; TL 1 yıllık
        DİBS, ABD Hazinesi 1 yıllık): ufuk eşleşmeli.
  arac_kur  Araç 4'ün varsayılanları (son TLREF, ABD 1y, taşıma başabaşı).
  sekil_18  Fama β çubukları (TRY dönemleri, G10) + TRY 60 aylık kayan β + saçılım.
  sekil_19  EM taşıma sepeti kümülatif getirisi + VIX ve eşiği (aylık).
  sekil_20  TRY artığı ve yabancı akımının kümülatifi (haftalık, 2020-09+).

YÖN. s = log(USD/yerel)×100; artış yerel paranın DEĞER KAYBI. CNBC'de EUR,
GBP, AUD XXX/USD (işaret çevrilir), CHF, JPY, CAD USD/XXX. Taşıma getirisi
yerel parayı alıp doları borçlanan pozisyonun getirisidir (artı = kazanç).

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. FAİZ ZİNCİRİNİN EKLEM YERİ BİR BASAMAKTIR. 2011'in ilk yılında TCMB
     fonlama maliyeti bankalararası gecelik faizin ortalama 3,35 puan
     (medyan 4,75) üstündeydi: koridor döneminde piyasa gecelik faizi
     koridorun alt bandına yapışıyordu. TLREF ile fonlama maliyeti 2019'da
     ortalama −0,13 puan ayrışıyor. Eklem günleri ve ayrışmalar sonuçta
     yazılıdır; bankalararası faizi baştan sona kullanan satır sağlamlıktır
     (2002–2017 β −0,16 yerine −0,15; fark yok).
  2. KRİZ AYLARININ AY SONU GECELİK FAİZİ GELECEK AYIN FAİZİ DEĞİLDİR. 1994
     Nisan sonunda %398, 2000 Kasım sonunda %316: on ikide biri ayda %33 ve
     %26 "beklenen değer kaybı" gibi regresyona girer. 1990–2001 β ay sonu
     faizle 0,15, ayın ortalama faiziyle 0,41, 1994-01…06 ve 2000-11…2001-06
     dışarıda 0,04 — hiçbiri 1'e yaklaşmıyor (t(β=1) −2,4 ile −6,9 arası).
  3. BASİT /12 İLE GÜNLÜK BİLEŞİK BİRİKİM AYNI SAYIDIR: gecelik faizin aylık
     log birikimi ile i/12 arasındaki fark medyanda 0,0006 puan, en çok 0,18
     puan (kriz ayı). Seçim (basit) sonucu değiştirmez.
  4. KUR KAYNAĞININ EKLEMİ: Aralık 2004'e kadar TCMB gösterge kurunun aylık
     değişimi, Ocak 2005'ten Yahoo'nunki; iki ucu farklı kaynaktan gelen ay
     yok. Ortak 261 ayda iki kaynağın aylık değişim farkı medyanda 0,34
     puan (korelasyon 0,977); TCMB kuruyla kurulan satır sağlamlıktır.
  5. TAM ÖRNEKLEMİN POZİTİF β'SI REJİMLER ARASI BİR SEVİYE FARKIDIR: dönem
     içinde β 0,15 · −0,16 · −0,79 iken havuzlu 1990–2026 β 0,40 (t 2,9)
     çıkıyor; yüksek faizli 1990'lar aynı zamanda yüksek değer kaybı yılları.
     Havuzlu satır örneklem dışında koşulsuz ortalamayı geçiyor (0,91) ama
     sıfır değişim kıyasını geçemiyor (1,04): hüküm tarif edici.
  6. G10'DA 2000–2026 FAİZ FARKLARI KÜÇÜK VE UZUN SÜRE SIFIRDA: β'ların
     standart hatası 1,2–2,2; Japonya'nın BIS politika faizi 106 ayda boş
     (sıfır faiz ve miktarsal genişleme yılları). Havuzlu β −0,05 (se 1,15):
     ne 0'dan ne 1'den ayrışıyor. Klasik "Fama bulmacası" bu örneklemde
     ölçülemiyor; yalnız yen 2000–2008 (n 42) −6,8 (se 3,4).
  7. YAHOO EM KURLARI 20.08.2026'DA BİTİYOR: Ağustos 2026 ay sonu yok, sepet
     2026-07'de biter. Depodaki politika faizi aynasının eksik son ayları BIS
     bulut arşivinden (örtüşen bütün aylarda birebir) tamamlanır ve adıyla
     yazılır (BRL, MXN, ZAR 2026-07…08; INR 2026-06).
  8. YAHOO GÜNLÜK BARINDA CUMA DEĞERİ PAZARTESİ AÇILIŞIDIR (18.12.2023 öncesi
     TRY ve bütün EM kurları; Bölüm 1 tuzak 5): haftalık ölçüler perşembe
     kapanışıyla örneklenir. Ölçüldü (2010–2021-11): TRY'nin EM sepetine
     eğimi cuma ile 0,71, perşembe ile 0,71, ama R² 0,17'ye karşı 0,24 —
     cuma örneklemesi ortak hareketin dörtte birini hafta sonuna kaydırıyor.
     Aylık örnekte aynı kayma cuma biten aylarda bir günlüktür.
  9. "KAYIP VIX İLE GELİR" SEVİYEDE DEĞİL DEĞİŞİMDE GÖRÜNÜR: sepetin en kötü
     %10'luk aylarının yalnız %20'si VIX ortalamasının genişleyen 75.
     yüzdeliği aştığı aylardır (taban oran %17), ama %70'i VIX'in yükseldiği
     aylardır (taban oran %46); getiri ile ΔVIX korelasyonu −0,35. Eşik 1990'dan
     kurulduğu için (son değer 22,9) 2010–2026'nın sakin VIX'i eşiği az aşar.
 10. TCMB'NİN FİİLİ FONLAMA FAİZİ POLİTİKA FAİZİ DEĞİLDİR. Koridor döneminde
     (ör. 2018 başı: politika %8, fonlama %12,75–16,5) politikayla kurulan
     TRY taşıması kazancı eksik sayar; fonlama maliyetiyle yıllık ortalama
     fark +0,89 puan. Sepetin TRY bacağı ayrıca fonlama maliyetiyle verilir.
 11. DİBS GÖSTERGE ETİKETİ İKİ İŞ GÜNÜ ÖNDEDİR (Bölüm 1 tuzak 6): haftalık Δ2y
     ve ex-ante primin TL 1 yıllık faizi kaydırılmış etiketle kurulur.
 12. DXY'NİN GÖVDE/ARALIK SINAMASI KURULAMAZ: arşiv yalnız kapanışı taşır.
     Tarih sözleşmesi sınandı: günlükte aynı gün korelasyonu 0,90 (önceki ve
     sonraki gün ±0,05), haftalıkta 0,93. Birincil dolar ölçüsü CNBC sepetidir.
 13. AKIM HAFTASI FİYAT HAFTASINDAN BİR ADIM GERİDE OKUNUYOR: 2023-07 sonrası
     akım ile bir önceki haftanın kur değişimi −0,20, aynı haftanınki −0,06.
     Akımın hangi işlem günlerini kapsadığı kaynakta yazmıyor; ±1 hafta
     tablosu bu belirsizliği gösterir, hüküm kurmaz.
 14. EX-ANTE PRİMİN PENCERESİ VARSAYIMDIR: anketin yanıt günleri arşivde yok.
     Ayın ilk yarısının ortalaması ile bir önceki ay sonu arasında prim farkı
     medyanda 1,07 puan; sonuç tablosu iki tanımı da taşır.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats

import bulut
import ortak_olc as oo
import olcum_b01 as b01
import olcum_b08 as b08

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

kurulmadi = b08.kurulmadi
hukum = b08.hukum

# ───────────────────────────────────────────────────────── sabitler (adlı)
YON_BAS, YON_SON = b01.YONETILEN                  # 2021-12-01 … 2023-06-30
SIGNAL_SON = pd.Timestamp(str(oo.CIPA_AY.to_timestamp().date()))   # 2026-08-01 (aylık çıpa)
KUR_EKLEM = pd.Timestamp("2005-01-01")            # bu aydan itibaren Yahoo değişimi
FAMA_DONEM = (("1990-2001", "1990-01-01", "2001-12-01"),
              ("2002-2017", "2002-01-01", "2017-12-01"),
              ("2018-2026", "2018-01-01", "2026-08-01"))
KRIZ = (("1994-01-01", "1994-06-01"), ("2000-11-01", "2001-06-01"))
FAMA_KAYAN = 60                                   # ay
G10 = (("eur", "XM", "EUR", True), ("gbp", "GB", "GBP", True), ("chf", "CH", "CHF", False),
       ("jpy", "JP", "JPY", False), ("cad", "CA", "CAD", False), ("aud", "AU", "AUD", True))
G10_OOS_ILK = 120
EM = (("brl", "bra", "BR", "Brezilya reali"), ("mxn", "mex", "MX", "Meksika pesosu"),
      ("zar", "zaf", "ZA", "Güney Afrika randı"), ("inr", "ind", "IN", "Hindistan rupisi"))
EM_BAS = pd.Timestamp("2010-01-01")
TR_POLITIKA_EKLEM = pd.Timestamp("2018-09-01")    # bu aydan itibaren TCMB politika faizi (fonlama hattı)
VIX_YUZDELIK = 0.75
VIX_ASGARI_AY = 60
HAFTA_PENCERE = 52
HAFTA_DONEM = (("oncesi", "2010-01-01", "2021-11-30", "2010-01 … 2021-11"),
               ("yonetilen", "2021-12-01", "2023-06-30", "yönetilen kur 2021-12 … 2023-06 (ayrı dönem)"),
               ("sonrasi", "2023-07-01", "2026-09-30", "2023-07 … 2026-09"))
AKIM_DONEM = (("oncesi", "2020-09-01", "2021-11-30", "2020-09 … 2021-11"),
              ("yonetilen", "2021-12-01", "2023-06-30", "yönetilen kur 2021-12 … 2023-06 (ayrı dönem)"),
              ("sonrasi", "2023-07-01", "2026-09-30", "2023-07 … 2026-09"))
PRIM_DONEM = (("oncesi", "2013-01-01", "2021-11-01", "2013-01 … 2021-11"),
              ("yonetilen", "2021-12-01", "2023-06-01", "yönetilen kur 2021-12 … 2023-06 (ayrı dönem)"),
              ("sonrasi", "2023-07-01", "2026-08-01", "2023-07 … 2026-08"))
ANKET_PENCERE_GUN = 15                            # anket yanıt penceresi varsayımı: ayın 1–15'i


def _iso(t) -> str:
    return str(pd.Timestamp(t).date())


def _ay(t) -> str:
    return pd.Timestamp(t).strftime("%Y-%m")


def _yonetilen_ay(t: pd.Timestamp) -> bool:
    return bool(YON_BAS <= t <= YON_SON)


def _aysonu(s: pd.Series) -> pd.Series:
    """Ayın son hafta içi gözlemi, ay başı etiketli."""
    s = s.dropna()
    s = s[s.index.dayofweek < 5]
    return s.resample("MS").last()


def _ozet_seri(s: pd.Series) -> dict:
    return {"n": int(s.notna().sum()), "ilk": _iso(s.dropna().index.min()), "son": _iso(s.dropna().index.max())}


def _reg(y: pd.Series, X, gecikme: int | None = None) -> dict:
    if isinstance(X, pd.Series):
        X = X.to_frame()
    d = pd.concat([y.rename("_y"), X], axis=1).dropna()
    r = oo.hac(d["_y"].values, d.drop(columns="_y").values, gecikme=gecikme)
    if r.get("yetersiz"):
        return {"n": r["n"], **kurulmadi("regresyon için gözlem yetersiz")}
    return {"n": r["n"], "ilk": _iso(d.index.min()), "son": _iso(d.index.max()),
            "sabit": r["b"][0], "sabit_t": r["t"][0], "b": r["b"][1:], "se": r["se"][1:], "t": r["t"][1:],
            "r2": r["r2"], "gecikme": r["gecikme"]}


def _oos(y: pd.Series, x: pd.Series, ilk: int) -> dict:
    out = {}
    for kiy in ("ortalama", "sifir"):
        o = oo.oos_kiyas(y, x, ilk, kiy)
        if not o.get("n"):
            out[kiy] = kurulmadi("örneklem dışı sınama için gözlem yetersiz")
        else:
            out[kiy] = {"n": o["n"], "mse_oran": o.get("mse_oran"), "dm_t": o.get("dm_t"), "ilk": o.get("ilk")}
    return out


def _hukum_oos(t: float | None, oos: dict) -> str:
    oranlar = [v.get("mse_oran") for v in oos.values() if isinstance(v, dict) and "mse_oran" in v]
    return hukum(t, oranlar) if len(oranlar) == 2 else "tarif edici"


# ───────────────────────────────────────────────────────── TL faiz zinciri
@lru_cache(maxsize=1)
def _tl_zincir():
    """Günlük TL gecelik faiz zinciri (%) ve kaynak etiketi; eklem günleri."""
    g = oo.oku("gecelik_gunluk")["gecelik_ao"].dropna()
    f = oo.oku("fonlama_gunluk")
    aofm, tlref = f["aofm"].dropna(), f["tlref"].dropna()
    b1, b2 = aofm.index.min(), tlref.index.min()
    z = pd.concat([g[g.index < b1], aofm[(aofm.index >= b1) & (aofm.index < b2)], tlref[tlref.index >= b2]]).sort_index()
    z = z[~z.index.duplicated(keep="last")]
    z = z[z.index.dayofweek < 5]
    kaynak = pd.Series(np.select([z.index < b1, z.index < b2], ["gecelik", "fonlama"], "tlref"), index=z.index)
    return z, kaynak, b1, b2, g, aofm, tlref


def _eklem_ozeti() -> dict:
    z, _, b1, b2, g, aofm, tlref = _tl_zincir()

    def fark(a: pd.Series, b: pd.Series, bas: pd.Timestamp) -> dict:
        j = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
        j = j[(j.index >= bas) & (j.index < bas + pd.DateOffset(years=1))]
        d = j["a"] - j["b"]
        return {"ortak_gun": int(len(d)), "ort_fark_puan": float(d.mean()), "medyan_fark_puan": float(d.median()),
                "ilk": _iso(j.index.min()), "son": _iso(j.index.max())}
    return {"gecelik_bitis": _iso(b1 - pd.offsets.BDay(1)), "fonlama_baslangic": _iso(b1), "tlref_baslangic": _iso(b2),
            "fonlama_eksi_gecelik_ilk_yil": fark(aofm, g, b1),
            "tlref_eksi_fonlama_ilk_yil": fark(tlref, aofm, b2)}


@lru_cache(maxsize=1)
def _fama_cerceve() -> pd.DataFrame:
    """Satır t (ay başı etiketli sinyal ayı): x = (i − i*)_t/12, y = Δs_{t+1}."""
    z, kay, *_ = _tl_zincir()
    g = oo.oku("gecelik_gunluk")["gecelik_ao"].dropna()
    i_son, i_ort = _aysonu(z), z[z.index.dayofweek < 5].resample("MS").mean()
    i_kay = kay.resample("MS").last()
    g_son = _aysonu(g)
    istar = oo.oku("kuresel_aylik")["faiz_abd"]
    tc = _aysonu(oo.usdtry_tcmb())
    ya = _aysonu(oo.usdtry()[0])
    ds_tc = np.log(tc).diff() * 100
    ds_ya = np.log(ya).diff() * 100
    ds = pd.concat([ds_tc[ds_tc.index < KUR_EKLEM], ds_ya[ds_ya.index >= KUR_EKLEM]]).sort_index()
    df = pd.DataFrame({"i": i_son, "i_ort": i_ort, "i_gecelik": g_son, "istar": istar, "kaynak": i_kay})
    df["x"] = (df["i"] - df["istar"]) / 12
    df["x_ort"] = (df["i_ort"] - df["istar"]) / 12
    df["x_gecelik"] = (df["i_gecelik"] - df["istar"]) / 12
    # tuzak 3: günlük bileşik aylık log birikimi (ay başına 365/12 gün)
    df["x_bilesik"] = (np.log1p(df["i"] / 36500) * (365 / 12) - np.log1p(df["istar"] / 36500) * (365 / 12)) * 100
    df["y"] = ds.shift(-1).reindex(df.index)
    df["y_tcmb"] = ds_tc.shift(-1).reindex(df.index)
    df["hedef"] = df.index + pd.offsets.MonthBegin(1)
    df["yonetilen"] = df["hedef"].map(_yonetilen_ay)
    kr = pd.Series(False, index=df.index)
    for a, b in KRIZ:
        a, b = pd.Timestamp(a), pd.Timestamp(b)
        kr |= ((df.index >= a) & (df.index <= b)) | ((df["hedef"] >= a) & (df["hedef"] <= b))
    df["kriz"] = kr
    # gecelik 20.08.2026'da bitiyor: Ağustos 2026 ay sonu yok
    df.loc[df.index > _tam_ay_sonu(g), "x_gecelik"] = np.nan
    df = df[(df.index >= pd.Timestamp("1990-01-01")) & (df.index <= SIGNAL_SON)]
    return df


def _fama(d: pd.DataFrame, xcol: str = "x", ycol: str = "y", oos: bool = True, asgari: int = 24) -> dict:
    d = d[[ycol, xcol]].dropna()
    if len(d) < asgari:
        return {"n": int(len(d)), **kurulmadi(f"dönemde {asgari} aydan az gözlem var")}
    r = _reg(d[ycol], d[xcol])
    if r.get("durum"):
        return r
    b, se = r["b"][0], r["se"][0]
    out = {"n": r["n"], "ilk": r["ilk"], "son": r["son"], "beta": b, "se": se, "t_beta0": b / se,
           "t_beta1": (b - 1) / se, "sabit_yuzde": r["sabit"], "sabit_t": r["sabit_t"], "r2": r["r2"],
           "gecikme": r["gecikme"], "ort_x_yuzde": float(d[xcol].mean()), "ort_y_yuzde": float(d[ycol].mean())}
    if oos:
        o = _oos(d[ycol], d[xcol], max(36, len(d) // 3))
        out["oos"] = o
        out["hukum"] = _hukum_oos(out["t_beta0"], o)
    return out


def _duyarlilik(zz: pd.DataFrame, ana: dict) -> dict:
    """Seçimlerin ana satıra göre etkisi; örneklemi ana satırla birebir aynı olan seçim yazılmaz."""
    adaylar = {"ay_ortalamasi_faiz": _fama(zz, "x_ort", oos=False),
               "krizler_haric": _fama(zz[~zz["kriz"]], oos=False),
               "tcmb_kur": _fama(zz, ycol="y_tcmb", oos=False),
               "bankalararasi_gecelik_tum": _fama(zz, "x_gecelik", oos=False)}
    out, ayni = {}, []
    for k, r in adaylar.items():
        if "beta" in r and "beta" in ana and r["n"] == ana["n"] and abs(r["beta"] - ana["beta"]) < 1e-12:
            ayni.append(k)
        else:
            out[k] = r
    if ayni:
        out["ana_satirla_ayni"] = ayni
    return out


@lru_cache(maxsize=1)
def _fama_try() -> dict:
    df = _fama_cerceve()
    satir = {}
    secimler = {}
    for ad, a, b in FAMA_DONEM:
        z = df.loc[a:b]
        if ad == "2018-2026":
            satir["2018-2026_yonetilen_haric"] = _fama(z[~z["yonetilen"]])
            satir["2018-2026_yonetilen_dahil"] = {**_fama(z), "uyari": "yönetilen kur ayları dahil: yalnız kıyas, havuzlu hüküm kurulmaz"}
            zz, ana = z[~z["yonetilen"]], satir["2018-2026_yonetilen_haric"]
        else:
            satir[ad] = _fama(z)
            zz, ana = z, satir[ad]
        secimler[ad] = _duyarlilik(zz, ana)
    satir["yonetilen"] = {**_fama(df[df["yonetilen"]], oos=False, asgari=12),
                          "uyari": "ayrı dönem (19 ay); kur yönetildiği için eğim tasarım gereği bilgi taşımaz, havuzlu hükme girmez"}
    tum = df[~df["yonetilen"]]
    satir["tum_yonetilen_haric"] = _fama(tum)
    secimler["tum_yonetilen_haric"] = _duyarlilik(tum, satir["tum_yonetilen_haric"])
    # tuzak 3 ve 4: seçimlerin ölçülen etkisi
    bil = (df["x_bilesik"] - df["x"]).abs()
    j = df[["y", "y_tcmb"]].dropna()
    j = j[j.index >= KUR_EKLEM - pd.offsets.MonthBegin(1)]
    kur_fark = (j["y"] - j["y_tcmb"])
    kaynak_ay = df["kaynak"].value_counts().to_dict()
    return {"satirlar": satir, "duyarlilik": secimler,
            "eklem": _eklem_ozeti(),
            "faiz_kaynagi_ay_sayisi": {str(k): int(v) for k, v in kaynak_ay.items()},
            "basit_bilesik_fark_azami_puan": float(bil.max()), "basit_bilesik_fark_medyan_puan": float(bil.median()),
            "kur_kaynagi": {"eklem_ayi": _ay(KUR_EKLEM), "once": "TCMB gösterge kuru (döviz alış, bir iş günü geri alınmış valör)",
                            "sonra": "Yahoo (2023-12-18'den İstanbul 18:00, öncesi Londra gece yarısı kapanışı)",
                            "ortak_ay": int(len(kur_fark)), "aylik_degisim_farki_medyan_mutlak_puan": float(kur_fark.abs().median()),
                            "aylik_degisim_farki_ort_puan": float(kur_fark.mean()),
                            "korelasyon": float(j["y"].corr(j["y_tcmb"])),
                            "ilk": _iso(j.index.min()), "son": _iso(j.index.max())}}


# ───────────────────────────────────────────────────────── G10 bacağı
@lru_cache(maxsize=1)
def _cnbc_aysonu() -> pd.DataFrame:
    c = oo.oku("cnbc_kur_gunluk")
    c = c[c.index.dayofweek < 5]
    return c.resample("MS").last()


def _dk(df: pd.DataFrame, gecikme: int) -> dict:
    """Havuzlu Fama: para başına sabit (içten ortalamadan arındırma), Driscoll–Kraay
    standart hatası (ay başına skorlar toplanır, Bartlett ağırlıklı)."""
    d = df.dropna(subset=["x", "y"]).copy()
    d["xd"] = d["x"] - d.groupby("para")["x"].transform("mean")
    d["yd"] = d["y"] - d.groupby("para")["y"].transform("mean")
    X, y = d["xd"].values, d["yd"].values
    b = float(X @ y / (X @ X))
    e = y - b * X
    h = pd.Series(X * e, index=d["t"]).groupby(level=0).sum()
    h = h.reindex(pd.date_range(h.index.min(), h.index.max(), freq="MS"), fill_value=0.0).values
    S = float(h @ h)
    for L in range(1, gecikme + 1):
        S += 2 * (1 - L / (gecikme + 1)) * float(h[L:] @ h[:-L])
    se = math.sqrt(S) / float(X @ X)
    k = d["para"].nunique()
    r2 = 1 - float(e @ e) / float(y @ y)
    return {"beta": b, "se": se, "t_beta0": b / se, "t_beta1": (b - 1) / se, "n": int(len(d)), "para_sayisi": int(k),
            "ilk": _iso(d["t"].min()), "son": _iso(d["t"].max()), "gecikme": int(gecikme), "r2_ic": r2}


G10_ALT = (("2000-2008", "2000-01-01", "2008-12-01"), ("2009-2026", "2009-01-01", "2026-08-01"))


@lru_cache(maxsize=1)
def _fama_g10() -> dict:
    try:
        bis = bulut.bis_politika()
    except bulut.VeriYok as e:
        return kurulmadi(f"G10 politika faizleri gelmedi: {e}")
    c = _cnbc_aysonu()
    istar = bis["US"]
    para, havuz = {}, []
    for kol, ulke, ad, ters in G10:
        if ulke not in bis.columns:
            para[ad] = kurulmadi("bu ülkenin politika faizi BIS arşivinde yok")
            continue
        s = (-np.log(c[kol]) if ters else np.log(c[kol])) * 100
        ds = s.diff()
        d = pd.DataFrame({"x": (bis[ulke] - istar) / 12, "y": ds.shift(-1)})
        d = d[(d.index >= pd.Timestamp("2000-01-01")) & (d.index <= SIGNAL_SON)]
        r = _fama(d)
        r["eksik_faiz_ayi"] = int(d["x"].isna().sum())
        para[ad] = r
        dd = d.dropna().copy()
        dd["para"], dd["t"] = ad, dd.index
        havuz.append(dd)
    hv = pd.concat(havuz)

    def _dk_oto(z: pd.DataFrame) -> dict:
        n_t = z["t"].nunique()
        return _dk(z, int(math.floor(4 * (n_t / 100) ** (2 / 9))))
    havuzlu = _dk_oto(hv)
    alt = {}
    for ad, a, b in G10_ALT:
        z = hv[(hv["t"] >= a) & (hv["t"] <= b)]
        pb = {}
        for p in z["para"].unique():
            zp = z[z["para"] == p].set_index("t")
            r = _fama(zp, oos=False)
            if "beta" in r:
                pb[p] = {"beta": r["beta"], "se": r["se"], "n": r["n"]}
        alt[ad] = {"havuz": _dk_oto(z), "paralar": pb}
    return {"paralar": para, "havuz": havuzlu, "alt_donem": alt,
            "yontem": "Altı G10 parasında bir sonraki ayın dolar karşısındaki log değişimi, ay sonundaki politika faizi farkının on ikide birine regresyonla bağlandı; havuzlu tahminde her paraya ayrı sabit konur ve standart hata aylar arası ortak şoka dayanıklı biçimde (Driscoll–Kraay) hesaplanır.",
            "kaynak": ["cnbc_kur_gunluk", "bulut/bis_politika"],
            "saat": "CNBC kurları New York 17:00 ay sonu; BIS politika faizi ay sonu"}


def _kayan_beta(d: pd.DataFrame, pencere: int) -> pd.DataFrame:
    d = d[["x", "y"]].dropna()
    out = []
    for j in range(pencere, len(d) + 1):
        w = d.iloc[j - pencere:j]
        r = oo.hac(w["y"].values, w["x"].values)
        if r.get("yetersiz"):
            continue
        out.append((d.index[j - 1], r["b"][1], r["se"][1]))
    return pd.DataFrame(out, columns=["t", "beta", "se"]).set_index("t")


def p11a() -> dict:
    tr = _fama_try()
    g10 = _fama_g10()
    return {
        "try": tr,
        "g10": g10,
        "ilk": tr["satirlar"]["tum_yonetilen_haric"]["ilk"], "son": tr["satirlar"]["tum_yonetilen_haric"]["son"],
        "n": tr["satirlar"]["tum_yonetilen_haric"]["n"],
        "yontem": "Her ay sonunda TL gecelik faizi ile ABD politika faizi arasındaki farkın on ikide biri (aylık basit faiz farkı), bir sonraki ayın USD/TRY log değişimine Newey–West standart hatalı regresyonla bağlandı; forward kur yerine faiz farkı alındı, yani örtülü faiz paritesi varsayıldı. Tarihler sinyal ayıdır; değişim bir sonraki ayı ölçer.",
        "formul": "Δs(t+1) = a + β·(i − i*)(t)/12 + u;  H0: β = 1 (UIP), t(β=1) = (β − 1)/se",
        "kaynak": ["gecelik_gunluk", "fonlama_gunluk", "kuresel_aylik", "usdtry_tcmb_gunluk", "usdtry_yahoo_gunluk",
                   "cnbc_kur_gunluk", "bulut/bis_politika"],
        "saat": "TL faizi gün sonu (gecelik ortalama, fonlama maliyeti, TLREF); USD/TRY 2005 öncesi TCMB 15:30 gösterge, sonra Yahoo (2023-12-18'e kadar Londra gece yarısı, sonra İstanbul 18:00); ABD politika faizi ay sonu",
    }


def sekil_18() -> dict:
    tr = _fama_try()["satirlar"]
    g10 = _fama_g10()
    cubuk = []
    adlar = {"1990-2001": "TRY 1990–2001", "2002-2017": "TRY 2002–2017",
             "2018-2026_yonetilen_haric": "TRY 2018–2026 (yönetilen kur hariç)",
             "yonetilen": "TRY yönetilen kur 2021-12 … 2023-06", "tum_yonetilen_haric": "TRY 1990–2026 (yönetilen hariç)"}
    for k, et in adlar.items():
        r = tr.get(k, {})
        if "beta" in r:
            cubuk.append({"etiket": et, "grup": "TRY", "beta": r["beta"], "alt": r["beta"] - 2 * r["se"],
                          "ust": r["beta"] + 2 * r["se"], "n": r["n"]})
    if "paralar" in g10:
        for ad, r in g10["paralar"].items():
            if "beta" in r:
                cubuk.append({"etiket": ad, "grup": "G10", "beta": r["beta"], "alt": r["beta"] - 2 * r["se"],
                              "ust": r["beta"] + 2 * r["se"], "n": r["n"]})
        h = g10["havuz"]
        cubuk.append({"etiket": "G10 havuz", "grup": "G10", "beta": h["beta"], "alt": h["beta"] - 2 * h["se"],
                      "ust": h["beta"] + 2 * h["se"], "n": h["n"]})
    df = _fama_cerceve()
    dd = df[~df["yonetilen"]]
    kb = _kayan_beta(dd, FAMA_KAYAN)
    sac = df[["x", "y", "yonetilen"]].dropna()
    return {
        "cubuk": cubuk,
        "kayan": {"tarih": [_ay(t) for t in kb.index], "beta": kb["beta"].tolist(),
                  "alt": (kb["beta"] - 2 * kb["se"]).tolist(), "ust": (kb["beta"] + 2 * kb["se"]).tolist(),
                  "pencere_ay": FAMA_KAYAN, "not": "pencere yönetilen kur aylarını atlar; tarih pencerenin son sinyal ayı"},
        "sacilim": {"tarih": [_ay(t) for t in sac.index], "faiz_farki_aylik_yuzde": sac["x"].tolist(),
                    "kur_degisimi_yuzde": sac["y"].tolist(), "yonetilen": [int(v) for v in sac["yonetilen"]]},
        "referans": {"uip_beta": 1.0, "rastgele_yuruyus_beta": 0.0},
        "yontem": "Çubuklar Fama eğimini ±2 Newey–West standart hatasıyla gösterir; kayan çizgi TRY için 60 aylık pencerede aynı regresyondur.",
    }


# ───────────────────────────────────────────────────────── p11b EM taşıma sepeti
def _tam_ay_sonu(s: pd.Series) -> pd.Timestamp:
    """Serinin ay sonu değeri olan son ayı (son gözlem ayın son iş gününden önceyse bir önceki ay)."""
    son = s.dropna().index.max()
    ay_son_is = (son + pd.offsets.BMonthEnd(0)).normalize()
    m = son.to_period("M").to_timestamp()
    return m if son >= ay_son_is else m - pd.offsets.MonthBegin(1)


@lru_cache(maxsize=2)
def _em_cerceve(tr_faiz: str = "politika") -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(taşıma getirisi, bileşenler, künye). Satır: getirinin gerçekleştiği ay (hedef ay)."""
    ep = oo.oku("em_politika_aylik")
    try:
        bis = bulut.bis_politika()
    except bulut.VeriYok:
        bis = None
    istar = oo.oku("kuresel_aylik")["faiz_abd"]
    f = oo.oku("fonlama_gunluk")
    tamamlanan = {}
    s_d, i_d = {}, {}
    for kod, kol, iso, _ad in EM:
        s = oo.em_kur(kod)
        son_ay = _tam_ay_sonu(s)
        s_d[kod] = _aysonu(s).loc[:son_ay]
        i = ep[kol].copy()
        if bis is not None and iso in bis.columns:
            eksik = bis[iso][(bis[iso].index > i.dropna().index.max()) & bis[iso].notna()]
            if len(eksik):
                tamamlanan[kod] = [_ay(t) for t in eksik.index]
                i = pd.concat([i.dropna(), eksik]).sort_index()
        i_d[kod] = i
    s_try = _aysonu(oo.usdtry()[0])
    s_d["try"] = s_try
    pol = _aysonu(f["politika"])
    i_tr = pd.concat([ep["tur"][ep.index < TR_POLITIKA_EKLEM].dropna(), pol[pol.index >= TR_POLITIKA_EKLEM]]).sort_index()
    if tr_faiz == "fonlama":
        i_tr = _aysonu(f["aofm"])
    i_d["try"] = i_tr
    son_ortak = min(_tam_ay_sonu(oo.em_kur(k)) for k, *_ in EM)
    r_d, x_d, ds_d = {}, {}, {}
    for kod in list(s_d):
        s = np.log(s_d[kod]) * 100
        ds = s.diff()
        x = ((i_d[kod] - istar) / 12).reindex(ds.index)
        r = x.shift(1) - ds                       # r(t) = x(t−1) − Δs(t)
        r = r[(r.index > EM_BAS) & (r.index <= son_ortak)]
        r_d[kod], x_d[kod], ds_d[kod] = r, x.shift(1).reindex(r.index), ds.reindex(r.index)
    R = pd.DataFrame(r_d)
    B = pd.concat({"faiz": pd.DataFrame(x_d), "kur": -pd.DataFrame(ds_d)}, axis=1)
    kun = {"son_ay": _ay(son_ortak), "bis_ile_tamamlanan_aylar": tamamlanan,
           "tr_faiz": "TCMB fonlama maliyeti" if tr_faiz == "fonlama" else
           "BIS politika faizi (2018-08'e kadar) → TCMB politika faizi (2018-09'dan)"}
    return R, B, kun


def _getiri_ozeti(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 24:
        return {"n": int(len(r)), **kurulmadi("24 aydan az gözlem")}
    kum = r.cumsum()
    dusus = kum - kum.cummax()
    j = dusus.idxmin()
    tepe = kum.loc[:j].idxmax()
    t_ort = oo.hac(r.values, np.zeros((len(r), 0)))
    en_kotu = r.nsmallest(3)
    en_iyi = r.nlargest(3)
    return {"n": int(len(r)), "ilk": _ay(r.index.min()), "son": _ay(r.index.max()),
            "ort_aylik_yuzde": float(r.mean()), "ort_yillik_yuzde": float(r.mean() * 12),
            "ort_t": float(t_ort["t"][0]),
            "oynaklik_yillik_yuzde": float(r.std(ddof=1) * math.sqrt(12)),
            "oran_yillik": float(r.mean() * 12 / (r.std(ddof=1) * math.sqrt(12))),
            "carpiklik": float(stats.skew(r.values, bias=False)),
            "basiklik_fazla": float(stats.kurtosis(r.values, fisher=True, bias=False)),
            "en_kotu_3": [{"ay": _ay(t), "getiri_yuzde": float(v)} for t, v in en_kotu.items()],
            "en_iyi_3": [{"ay": _ay(t), "getiri_yuzde": float(v)} for t, v in en_iyi.items()],
            "azami_dusus_yuzde": float(dusus.min()), "azami_dusus_tepe": _ay(tepe), "azami_dusus_dip": _ay(j),
            "kumulatif_yuzde": float(kum.iloc[-1]), "kazanan_ay_payi": float((r > 0).mean())}


@lru_cache(maxsize=1)
def _vix_aylik() -> pd.DataFrame:
    v = oo.oku("yahoo_dxy_vix_gunluk")["vix"].dropna()
    m = v.resample("MS").mean()
    esik = m.expanding(VIX_ASGARI_AY).quantile(VIX_YUZDELIK).shift(1)
    return pd.DataFrame({"vix": m, "esik": esik, "yuksek": m > esik})


def _vix_kosullu(r: pd.Series) -> dict:
    v = _vix_aylik()
    d = pd.concat([r.rename("r"), v], axis=1, sort=True).dropna(subset=["r", "esik"])
    yuk, dus = d[d["yuksek"]]["r"], d[~d["yuksek"]]["r"]
    reg = _reg(d["r"], d["yuksek"].astype(float))
    alt10 = d["r"].quantile(0.10)
    kotu = d[d["r"] <= alt10]
    dvix = d["vix"].diff()
    return {"n": int(len(d)), "n_yuksek": int(len(yuk)), "n_diger": int(len(dus)),
            "ort_yuksek_aylik_yuzde": float(yuk.mean()), "ort_diger_aylik_yuzde": float(dus.mean()),
            "fark_aylik_yuzde": float(yuk.mean() - dus.mean()), "fark_t": reg["t"][0] if "t" in reg else None,
            "oynaklik_yuksek_yillik_yuzde": float(yuk.std(ddof=1) * math.sqrt(12)),
            "oynaklik_diger_yillik_yuzde": float(dus.std(ddof=1) * math.sqrt(12)),
            "en_kotu_yuzde10_ay_sayisi": int(len(kotu)), "en_kotu_yuzde10_icinde_yuksek_vix_payi": float(kotu["yuksek"].mean()),
            "en_kotu_yuzde10_icinde_vix_artan_payi": float((dvix.reindex(kotu.index) > 0).mean()),
            "vix_artan_ay_payi": float((dvix.dropna() > 0).mean()),
            "yuksek_vix_ay_payi": float(d["yuksek"].mean()),
            "korelasyon_getiri_dvix": float(d["r"].corr(dvix)),
            "esik_son": float(v["esik"].dropna().iloc[-1]), "esik_son_ay": _ay(v["esik"].dropna().index[-1])}


def _ecb_capraz(R: pd.DataFrame) -> dict:
    try:
        usd = bulut.ecb_kur("usd")
    except bulut.VeriYok as e:
        return kurulmadi(f"ECB referans kurları gelmedi: {e}")
    istar = oo.oku("kuresel_aylik")["faiz_abd"]
    _, B, _ = _em_cerceve("politika")
    out, r_ecb = {}, {}
    for kod in ("brl", "mxn", "zar", "inr", "try"):
        try:
            x = bulut.ecb_kur(kod)
        except bulut.VeriYok:
            out[kod] = kurulmadi("ECB arşivinde bu para yok")
            continue
        u = (x / usd.reindex(x.index)).dropna()
        ds_e = (np.log(_aysonu(u)) * 100).diff().reindex(R.index)
        ds_y = -B[("kur", kod)]
        j = pd.concat([ds_y.rename("y"), ds_e.rename("e")], axis=1).dropna()
        out[kod] = {"ortak_ay": int(len(j)), "korelasyon": float(j["y"].corr(j["e"])),
                    "medyan_mutlak_fark_puan": float((j["y"] - j["e"]).abs().median()),
                    "azami_mutlak_fark_puan": float((j["y"] - j["e"]).abs().max()),
                    "ort_fark_puan": float((j["y"] - j["e"]).mean())}
        r_ecb[kod] = B[("faiz", kod)] - ds_e
    Re = pd.DataFrame(r_ecb)
    sep_e = Re.mean(axis=1, skipna=False)
    oz = _getiri_ozeti(sep_e)
    sep_y = R.mean(axis=1, skipna=False)
    return {"paralar": out, "sepet_ecb": {k: oz[k] for k in ("n", "ilk", "son", "ort_yillik_yuzde", "oynaklik_yillik_yuzde", "carpiklik")},
            "sepet_korelasyon": float(pd.concat([sep_y, sep_e], axis=1).dropna().corr().iloc[0, 1]),
            "saat": "ECB referans kuru 14:15 Orta Avrupa; Yahoo Londra gece yarısı (2023-12-18'den TRY İstanbul 18:00)",
            "yontem": "Aynı taşıma getirisi kur bacağı ECB referans kurlarının euro çaprazından kurularak yeniden hesaplandı; iki kaynağın aylık kur değişimleri karşılaştırıldı."}


def p11b() -> dict:
    R, B, kun = _em_cerceve("politika")
    sepet = R.mean(axis=1, skipna=False)
    sepet_trh = R[[k for k, *_ in EM]].mean(axis=1, skipna=False)
    paralar = {}
    adlar = {k: a for k, _, _, a in EM}
    adlar["try"] = "Türk lirası"
    for kod in R.columns:
        oz = _getiri_ozeti(R[kod])
        oz["ort_faiz_bileseni_aylik_yuzde"] = float(B[("faiz", kod)].reindex(R[kod].dropna().index).mean())
        oz["ort_kur_bileseni_aylik_yuzde"] = float(B[("kur", kod)].reindex(R[kod].dropna().index).mean())
        oz["ad"] = adlar[kod]
        paralar[kod] = oz
    # TRY: yönetilen dönem ayrı
    rt = R["try"].dropna()
    yon = rt[(rt.index >= YON_BAS) & (rt.index <= YON_SON)]
    paralar["try"]["yonetilen_kur"] = {"n": int(len(yon)), "ort_aylik_yuzde": float(yon.mean()),
                                       "oynaklik_yillik_yuzde": float(yon.std(ddof=1) * math.sqrt(12)),
                                       "uyari": "ayrı dönem; havuzlu hükme girmez"}
    paralar["try"]["yonetilen_haric"] = {k: v for k, v in _getiri_ozeti(rt.drop(yon.index)).items()
                                         if k in ("n", "ort_yillik_yuzde", "oynaklik_yillik_yuzde", "carpiklik", "azami_dusus_yuzde")}
    # tuzak 7: TRY faizi TCMB fonlama maliyetiyle
    Rf, _, kunf = _em_cerceve("fonlama")
    sepet_f = Rf.mean(axis=1, skipna=False)
    tr_fark = (Rf["try"] - R["try"]).dropna()
    tr_fonlama = {"tr_faiz": kunf["tr_faiz"],
                  "try_ort_yillik_yuzde": float(Rf["try"].mean() * 12),
                  "politikaya_gore_ort_fark_yillik_puan": float(tr_fark.mean() * 12),
                  "farkin_buyuk_oldugu_aylar": [{"ay": _ay(t), "fark_aylik_puan": float(v)} for t, v in tr_fark.abs().nlargest(5).items()],
                  "sepet": {k: v for k, v in _getiri_ozeti(sepet_f).items()
                            if k in ("n", "ort_yillik_yuzde", "oynaklik_yillik_yuzde", "carpiklik", "azami_dusus_yuzde")}}
    return {
        "sepet": {**_getiri_ozeti(sepet), "vix_kosullu": _vix_kosullu(sepet)},
        "sepet_try_haric": {**_getiri_ozeti(sepet_trh), "vix_kosullu": _vix_kosullu(sepet_trh)},
        "paralar": paralar,
        "try_fonlama_maliyetiyle": tr_fonlama,
        "ecb_capraz": _ecb_capraz(R),
        "kunye": kun,
        "n": int(sepet.notna().sum()), "ilk": _ay(sepet.dropna().index.min()), "son": _ay(sepet.dropna().index.max()),
        "yontem": "Her para için aylık taşıma getirisi, bir önceki ay sonundaki politika faizi farkının on ikide biri eksi o ayki kur log değişimidir (yerel parayı alıp doları borçlanan pozisyon); sepet beş paranın eşit ağırlıklı ortalamasıdır. VIX koşulu, getiri ayının VIX ortalamasının o güne kadarki aylık ortalamaların 75. yüzdeliğini (bir önceki aya kadar) aşmasıdır.",
        "formul": "r(t) = (i − i*)(t−1)/12 − [s(t) − s(t−1)],  s = 100·ln(USD/yerel)",
        "kaynak": ["em_kur_yahoo_gunluk", "usdtry_yahoo_gunluk", "em_politika_aylik", "fonlama_gunluk", "kuresel_aylik",
                   "yahoo_dxy_vix_gunluk", "bulut/bis_politika", "bulut/ecb_kur"],
        "saat": "EM kurları Yahoo günlük barı (Londra gece yarısı; cuma değeri pazartesi açılışı), TRY 2023-12-18'den İstanbul 18:00; politika faizleri ay sonu; VIX ay ortalaması",
    }


def sekil_19() -> dict:
    R, _, _ = _em_cerceve("politika")
    sepet = R.mean(axis=1, skipna=False).dropna()
    trh = R[[k for k, *_ in EM]].mean(axis=1, skipna=False).reindex(sepet.index)
    v = _vix_aylik().reindex(sepet.index)
    return {"tarih": [_ay(t) for t in sepet.index],
            "sepet_kumulatif_yuzde": sepet.cumsum().tolist(),
            "sepet_try_haric_kumulatif_yuzde": trh.cumsum().tolist(),
            "vix_ay_ort": v["vix"].tolist(), "vix_esik": v["esik"].tolist(),
            "yuksek_vix": [int(bool(x)) for x in v["yuksek"].fillna(False)],
            "yontem": "Kümülatif çizgi aylık log taşıma getirilerinin toplamıdır (yüzde); gölgeli aylar VIX ortalamasının genişleyen 75. yüzdeliği aştığı aylardır."}


# ───────────────────────────────────────────────────────── p11c haftalık küresel faktör
@lru_cache(maxsize=4)
def _haftalik_kuresel(son_gun: int = b01.TR_ORNEK_SON_GUN, em: bool = True) -> pd.DataFrame:
    a = b01._abd_gunluk()[["us10", "sepet", "dxy", "vix"]]
    s, _ = oo.usdtry()
    df = a.join(np.log(s).rename("try"), how="inner")
    if em:
        e = pd.DataFrame({k: np.log(oo.em_kur(k)) for k, *_ in EM})
        df = df.join(e, how="inner")
    df = df.dropna(subset=[c for c in df.columns if c not in ("dxy", "vix")])
    w = b01._haftalik(df, son_gun)
    w = w[~w["_kismi"].astype(bool)]
    out = pd.DataFrame({"dtry": w["try"].diff() * 100, "ddolar": w["sepet"].diff() * 100,
                        "ddxy": w["dxy"].diff() * 100, "dvix": w["vix"].diff(), "dus10_bp": w["us10"].diff() * 100,
                        "_gun": w["_gun"]})
    if em:
        out["dem"] = pd.concat({k: w[k].diff() * 100 for k, *_ in EM}, axis=1).mean(axis=1)
    out = out.iloc[1:]
    out["yonetilen"] = (out.index >= YON_BAS) & (out.index <= YON_SON + pd.Timedelta(days=6))
    return out


def _beta_tablosu(d: pd.DataFrame, y: str) -> dict:
    cok = _reg(d[y], d[["ddolar", "dvix", "dus10_bp"]])
    if cok.get("durum"):
        return cok
    tek = {k: _reg(d[y], d[k]) for k in ("ddolar", "dvix", "dus10_bp")}
    return {"n": cok["n"], "ilk": cok["ilk"], "son": cok["son"],
            "cok_degiskenli": {"b_dolar": cok["b"][0], "t_dolar": cok["t"][0], "b_vix": cok["b"][1], "t_vix": cok["t"][1],
                               "b_us10_bp": cok["b"][2], "t_us10_bp": cok["t"][2], "r2": cok["r2"], "gecikme": cok["gecikme"]},
            "tek_degiskenli": {k: {"b": v["b"][0], "t": v["t"][0], "r2": v["r2"]} for k, v in tek.items() if "b" in v}}


def _kayan_cok(d: pd.DataFrame, y: str, xs: list, pencere: int) -> pd.DataFrame:
    z = d[[y] + xs].dropna()
    rows = []
    Y, X = z[y].values, np.column_stack([np.ones(len(z)), z[xs].values])
    for j in range(pencere, len(z) + 1):
        b = np.linalg.lstsq(X[j - pencere:j], Y[j - pencere:j], rcond=None)[0]
        rows.append([z.index[j - 1], *b[1:]])
    return pd.DataFrame(rows, columns=["t"] + xs).set_index("t")


@lru_cache(maxsize=1)
def _try_artik() -> pd.DataFrame:
    """TRY'nin EM sepetine göre artığı: e(t) = ΔTRY(t) − β(t−1)·ΔEM(t), β bir önceki
    52 yönetilen-dışı haftanın eğimi (yönetilen haftalarda dönem öncesi son β)."""
    d = _haftalik_kuresel()
    z = d[["dtry", "dem", "yonetilen"]].dropna()
    normal = z[~z["yonetilen"]]
    cov = normal["dtry"].rolling(HAFTA_PENCERE).cov(normal["dem"])
    var = normal["dem"].rolling(HAFTA_PENCERE).var()
    beta = (cov / var).shift(1).reindex(z.index).ffill()
    e = z["dtry"] - beta * z["dem"]
    out = pd.DataFrame({"beta": beta, "artik": e, "dtry": z["dtry"], "dem": z["dem"], "yonetilen": z["yonetilen"]}).dropna(subset=["artik"])
    out["artik_kum"] = out["artik"].cumsum()
    return out


def p11c() -> dict:
    d = _haftalik_kuresel()
    dt = _haftalik_kuresel(em=False)
    dt = dt[dt.index >= EM_BAS]
    don = {}
    for ad, a, b, et in HAFTA_DONEM:
        z, zt = d.loc[a:b], dt.loc[a:b]
        r_try = _beta_tablosu(zt, "dtry")
        r_em = _beta_tablosu(z, "dem")
        rs = _reg(z["dtry"], z["dem"])
        don[ad] = {"etiket": et, "try": r_try, "em_sepet": r_em,
                   "try_em_sepete": {"b": rs["b"][0], "t": rs["t"][0], "r2": rs["r2"], "n": rs["n"]} if "b" in rs else rs}
    tum = d[~d["yonetilen"]]
    tumt = dt[~dt["yonetilen"]]
    rs = _reg(tum["dtry"], tum["dem"])
    don["tum_yonetilen_haric"] = {"etiket": "2010–2026, yönetilen kur hariç",
                                  "try": _beta_tablosu(tumt, "dtry"), "em_sepet": _beta_tablosu(tum, "dem"),
                                  "try_em_sepete": {"b": rs["b"][0], "t": rs["t"][0], "r2": rs["r2"], "n": rs["n"]}}
    # cuma örneklemesi (tuzak 6)
    dc = _haftalik_kuresel(son_gun=4)
    cuma = {}
    for ad, a, b, _ in (HAFTA_DONEM[0], HAFTA_DONEM[2]):
        zc, zp = dc.loc[a:b], d.loc[a:b]
        rc, rp = _reg(zc["dtry"], zc["dem"]), _reg(zp["dtry"], zp["dem"])
        cuma[ad] = {"cuma_b": rc["b"][0], "cuma_r2": rc["r2"], "persembe_b": rp["b"][0], "persembe_r2": rp["r2"],
                    "cuma_kor_dolar": float(zc["dtry"].corr(zc["ddolar"])), "persembe_kor_dolar": float(zp["dtry"].corr(zp["ddolar"])),
                    "n_cuma": rc["n"], "n_persembe": rp["n"]}
    # DXY sınaması (tuzak 9)
    gec = {}
    for ad, L in (("dxy_onceki_hafta", 1), ("dxy_ayni_hafta", 0), ("dxy_sonraki_hafta", -1)):
        j = pd.concat([d["ddolar"], d["ddxy"].shift(L)], axis=1).dropna()
        gec[ad] = float(j.iloc[:, 0].corr(j.iloc[:, 1]))
    try:
        gunluk = b01.p1a()["dxy_sinama"]
    except Exception as e:  # noqa: BLE001 — Bölüm 1'in sınaması kurulamazsa adıyla
        gunluk = kurulmadi(f"Bölüm 1 günlük sınaması kurulamadı: {e}")
    dxy = {"govde_aralik": {"durum": "kurulmadi", "sebep": "arşiv DXY'nin yalnız kapanışını taşıyor; açılış, en yüksek ve en düşük yok"},
           "gunluk_tarih_sinamasi": gunluk, "haftalik_gecikme_korelasyonu": gec,
           "hukum": "DXY haftalık değişimi CNBC sepetiyle aynı haftaya oturuyor" if gec["dxy_ayni_hafta"] > max(gec["dxy_onceki_hafta"], gec["dxy_sonraki_hafta"]) + 0.5
           else "DXY haftası sepetle ayrışıyor",
           "birincil": "CNBC altı paralı eşit ağırlıklı dolar sepeti"}
    # kayan 52 hafta
    xs = ["ddolar", "dvix", "dus10_bp"]
    kt = _kayan_cok(dt[~dt["yonetilen"]], "dtry", xs, HAFTA_PENCERE)
    ke = _kayan_cok(d, "dem", xs, HAFTA_PENCERE)
    ks = _kayan_cok(d[~d["yonetilen"]], "dtry", ["dem"], HAFTA_PENCERE)
    art = _try_artik()
    def ayl(k: pd.DataFrame) -> pd.DataFrame:            # kompakt: her ayın son haftası
        return k.groupby(k.index.to_period("M")).tail(1)
    kt, ke, ks = ayl(kt), ayl(ke), ayl(ks)
    kayan = {"try": {"tarih": [_iso(t) for t in kt.index], "b_dolar": kt["ddolar"].tolist(), "b_vix": kt["dvix"].tolist(), "b_us10_bp": kt["dus10_bp"].tolist()},
             "em_sepet": {"tarih": [_iso(t) for t in ke.index], "b_dolar": ke["ddolar"].tolist(), "b_vix": ke["dvix"].tolist(), "b_us10_bp": ke["dus10_bp"].tolist()},
             "try_em_sepete": {"tarih": [_iso(t) for t in ks.index], "b": ks["dem"].tolist()},
             "pencere_hafta": HAFTA_PENCERE, "not": "52 haftalık pencere; her ayın son haftası yazılır; TRY pencereleri yönetilen kur haftalarını atlar"}
    sonr = art.loc["2023-07-01":]
    return {
        "donemler": don, "cuma_ornekleme": cuma, "dxy_sinama": dxy, "kayan": kayan,
        "try_artik": {"n": int(len(art)), "ilk": _iso(art.index.min()), "son": _iso(art.index.max()),
                      "kumulatif_yuzde": float(art["artik_kum"].iloc[-1]),
                      "yillik_ort_yuzde": float(art["artik"].mean() * 52),
                      "yonetilen_disi_yillik_ort_yuzde": float(art.loc[~art["yonetilen"], "artik"].mean() * 52),
                      "sonrasi_yillik_ort_yuzde": float(sonr["artik"].mean() * 52),
                      "son_beta": float(art["beta"].iloc[-1]),
                      "yontem": "TRY'nin haftalık değişiminden, bir önceki 52 haftanın (yönetilen kur haftaları hariç) TRY–EM sepeti eğimiyle çarpılmış EM sepet değişimi çıkarılır; kalan TRY'ye özgü kısımdır ve sabit terim (TRY'nin kendi değer kaybı eğilimi) artıkta kalır."},
        "n": don["tum_yonetilen_haric"]["try"]["n"], "ilk": don["tum_yonetilen_haric"]["try"]["ilk"], "son": don["tum_yonetilen_haric"]["try"]["son"],
        "yontem": "Haftalık (perşembe kapanışı) USD/TRY ve dört EM parasının (BRL, MXN, ZAR, INR) eşit ağırlıklı log değişimi, CNBC altı paralı dolar sepetinin değişimine, VIX değişimine ve ABD 10 yıllık getiri değişimine birlikte Newey–West regresyonla bağlandı; eğimler dönem başına ve 52 haftalık kayan pencerede verilir.",
        "kaynak": ["usdtry_yahoo_gunluk", "em_kur_yahoo_gunluk", "cnbc_kur_gunluk", "abd_hazine_gunluk", "yahoo_dxy_vix_gunluk"],
        "saat": "perşembe: TRY ve EM Londra gece yarısı (TRY 2023-12-18'den İstanbul 18:00), CNBC New York 17:00, VIX 16:15 New York, ABD getirisi New York kapanışı; EM kurları 20.08.2026'da biter",
    }


# ───────────────────────────────────────────────────────── p11d yabancı akım
@lru_cache(maxsize=1)
def _akim_cerceve() -> pd.DataFrame:
    w = b01._tr_haftalik(b01.TR_ORNEK_SON_GUN, b01.DIBS_ETIKET_ONCU)
    w = w[~w["_kismi"].astype(bool)][["dkur_yuzde", "d2_bp", "_gun"]]
    a = oo.oku("yabanci_akim_haftalik")
    a = a.copy()
    a["toplam"] = a["hisse"] + a["dibs"]
    df = w.join(a, how="inner")
    df["yonetilen"] = (df.index >= YON_BAS) & (df.index <= YON_SON + pd.Timedelta(days=6))
    return df


def _akim_satir(z: pd.DataFrame, oos: bool) -> dict:
    out = {"n": int(len(z)), "ilk": _iso(z.index.min()), "son": _iso(z.index.max())}
    for ak in ("dibs", "hisse", "toplam"):
        x = z[ak] / 1000.0                                 # milyar USD
        sat = {}
        for y, yad in (("dkur_yuzde", "kur"), ("d2_bp", "dibs_2y")):
            kor = {}
            for k in (-1, 0, 1):
                j = pd.concat([z[ak], z[y].shift(-k)], axis=1).dropna()
                kor[str(k)] = float(j.iloc[:, 0].corr(j.iloc[:, 1]))
            r0 = _reg(z[y], x)
            r1 = _reg(z[y].shift(-1), x)
            s = {"korelasyon_gecikme": kor,
                 "esanli": {"b_milyar_usd": r0["b"][0], "t": r0["t"][0], "r2": r0["r2"], "n": r0["n"]} if "b" in r0 else r0,
                 "bir_hafta_sonra": {"b_milyar_usd": r1["b"][0], "t": r1["t"][0], "r2": r1["r2"], "n": r1["n"]} if "b" in r1 else r1}
            if oos and "b" in r1 and r1["n"] >= 80:
                o = _oos(z[y].shift(-1).dropna(), x, 52)
                s["bir_hafta_sonra"]["oos"] = o
                s["bir_hafta_sonra"]["hukum"] = _hukum_oos(r1["t"][0], o)
                oe = _oos(z[y], x, 52)
                s["esanli"]["oos"] = oe
                s["esanli"]["hukum"] = _hukum_oos(r0["t"][0], oe)
            sat[yad] = s
        out[ak] = sat
    return out


def p11d() -> dict:
    df = _akim_cerceve()
    don = {}
    for ad, a, b, et in AKIM_DONEM:
        z = df.loc[a:b]
        don[ad] = {"etiket": et, **_akim_satir(z, oos=(ad == "sonrasi"))}
    don["tum_yonetilen_haric"] = {"etiket": "2020-09 … 2026-09, yönetilen kur hariç", **_akim_satir(df[~df["yonetilen"]], oos=True)}
    kum = df[["dibs", "hisse", "toplam"]].sum() / 1000.0
    return {
        "donemler": don,
        "toplam_akim_milyar_usd": {k: float(v) for k, v in kum.items()},
        "n": int(len(df)), "ilk": _iso(df.index.min()), "son": _iso(df.index.max()),
        "birim": "akım milyon ABD doları (yurt dışı yerleşiklerin haftalık net alımı); eğim 1 milyar ABD doları başına",
        "isaret": "artı akım = yabancı net alımı; kurda eksi değişim TL'nin değer kazancı, 2 yıllıkta eksi değişim getiri düşüşü",
        "yontem": "Yabancıların haftalık net DİBS ve hisse alımı, aynı haftanın (perşembe kapanışı) USD/TRY log değişimi ve 2 yıllık DİBS getirisi değişimiyle eşzamanlı ve ±1 hafta kaydırılarak karşılaştırıldı; eğimler Newey–West standart hatalıdır. Akımın hangi işlem günlerini kapsadığı kaynakta yazmadığı için ±1 hafta tablosu bu belirsizliği gösterir.",
        "kaynak": ["yabanci_akim_haftalik", "usdtry_yahoo_gunluk", "dibs_egri_gunluk", "fonlama_gunluk (iş günü takvimi)"],
        "saat": "akım haftası cuma etiketli; kur ve getiri perşembe kapanışı (DİBS etiketi iki iş günü kaydırılmış)",
    }


def sekil_20() -> dict:
    df = _akim_cerceve()
    art = _try_artik()
    a0 = df.index.min()
    ar = art.loc[a0:, "artik"]
    ar_kum = ar.cumsum()
    idx = df.index
    return {"tarih": [_iso(t) for t in idx],
            "try_artik_kumulatif_yuzde": ar_kum.reindex(idx).tolist(),
            "akim_dibs_kumulatif_milyar_usd": (df["dibs"].cumsum() / 1000).tolist(),
            "akim_hisse_kumulatif_milyar_usd": (df["hisse"].cumsum() / 1000).tolist(),
            "akim_toplam_kumulatif_milyar_usd": (df["toplam"].cumsum() / 1000).tolist(),
            "yonetilen": [int(v) for v in df["yonetilen"]],
            "artik_son": _iso(ar.index.max()),
            "yontem": "TRY artığı Pratik 11C'deki haftalık artığın 2020-09'dan toplamıdır (EM kurları 20.08.2026'da bittiği için orada durur); akımlar aynı tarihten kümülatif net alımdır."}


# ───────────────────────────────────────────────────────── p11e ex-ante UIP primi
FORMUL_11E = ("λ(t) = [ln(1 + i_TL,1y) − ln(1 + i_ABD,1y)] − ln(E_t[S(t+12)] / S(t)); "
              "i_TL,1y DİBS 1 yıllık sıfır kuponlu getiri (yıllık bileşik), i_ABD,1y ABD Hazinesi 1 yıllık par getirisi "
              "yıllık bileşiğe çevrilmiş, E_t[S(t+12)] Piyasa Katılımcıları Anketi'nin 12 ay sonrası USD/TRY beklentisi, "
              "S(t) anket penceresindeki USD/TRY; λ > 0 taşımanın beklenen fazla getirisidir")


def _pencere_ort(s: pd.Series, gun: int) -> pd.Series:
    s = s.dropna()
    s = s[s.index.day <= gun]
    return s.resample("MS").mean()


def p11e() -> dict:
    try:
        pka = bulut.pka_kur_beklentisi()
        us1y = bulut.abd_1y()
    except bulut.VeriYok as e:
        return {**kurulmadi(f"anket kur beklentisi ya da ABD 1 yıllık getirisi gelmedi: {e}"), "formul": FORMUL_11E}
    if "usdtry_12a" not in pka.columns:
        return {**kurulmadi("anketin 12 ay sonrası kur beklentisi arşivde yok"), "formul": FORMUL_11E}
    takvim = b01._tr_takvim()
    n1y = oo.oku("dibs_egri_gunluk")["n1y"]
    n1y = n1y[n1y.index.isin(takvim)].shift(-b01.DIBS_ETIKET_ONCU)   # tuzak 8
    s, _ = oo.usdtry()
    us_b = ((1 + us1y / 200) ** 2 - 1) * 100                           # yarıyıllık → yıllık bileşik
    E = pka["usdtry_12a"].dropna()

    def kur(pencere: str) -> pd.DataFrame:
        if pencere == "ayin_ilk_yarisi":
            S, i, j = _pencere_ort(s, ANKET_PENCERE_GUN), _pencere_ort(n1y, ANKET_PENCERE_GUN), _pencere_ort(us_b, ANKET_PENCERE_GUN)
        else:  # bir önceki ay sonu
            S, i, j = _aysonu(s).shift(1), _aysonu(n1y).shift(1), _aysonu(us_b).shift(1)
        d = pd.DataFrame({"S": S, "i": i, "j": j, "E": E}).dropna()
        d["faiz_farki"] = (np.log1p(d["i"] / 100) - np.log1p(d["j"] / 100)) * 100
        d["beklenen_deval"] = np.log(d["E"] / d["S"]) * 100
        d["prim"] = d["faiz_farki"] - d["beklenen_deval"]
        S12 = S.shift(-12).reindex(d.index)
        d["gerceklesen_deval"] = np.log(S12 / d["S"]) * 100
        d["gerceklesen_tasima"] = d["faiz_farki"] - d["gerceklesen_deval"]
        d["beklenti_hatasi"] = d["gerceklesen_deval"] - d["beklenen_deval"]
        return d

    d = kur("ayin_ilk_yarisi")
    d2 = kur("onceki_ay_sonu")

    def oz(z: pd.DataFrame) -> dict:
        g = z.dropna(subset=["gerceklesen_deval"])
        return {"n": int(len(z)), "ilk": _ay(z.index.min()), "son": _ay(z.index.max()),
                "prim_ort_puan": float(z["prim"].mean()), "prim_medyan_puan": float(z["prim"].median()),
                "prim_sd_puan": float(z["prim"].std(ddof=1)), "prim_eksi_ay_payi": float((z["prim"] < 0).mean()),
                "faiz_farki_ort_puan": float(z["faiz_farki"].mean()), "beklenen_deval_ort_yuzde": float(z["beklenen_deval"].mean()),
                "n_gerceklesen": int(len(g)),
                "gerceklesen_deval_ort_yuzde": float(g["gerceklesen_deval"].mean()) if len(g) else None,
                "gerceklesen_tasima_ort_puan": float(g["gerceklesen_tasima"].mean()) if len(g) else None,
                "beklenti_hatasi_ort_puan": float(g["beklenti_hatasi"].mean()) if len(g) else None}
    don = {ad: {"etiket": et, **oz(d.loc[a:b])} for ad, a, b, et in PRIM_DONEM}
    son = d.iloc[-1]
    fark = (d["prim"] - d2["prim"].reindex(d.index)).dropna()
    return {
        "donemler": don,
        "tum_yonetilen_haric": oz(d[(d.index < YON_BAS) | (d.index > YON_SON)]),
        "son": {"ay": _ay(d.index[-1]), "prim_puan": float(son["prim"]), "faiz_farki_puan": float(son["faiz_farki"]),
                "beklenen_deval_yuzde": float(son["beklenen_deval"]), "kur": float(son["S"]), "beklenti_12a": float(son["E"]),
                "tl_1y_yuzde": float(son["i"]), "abd_1y_yillik_bilesik_yuzde": float(son["j"])},
        "pencere_duyarliligi": {"karsilastirma": "anket ayının ilk yarısı ortalaması ile bir önceki ay sonu",
                                "prim_farki_medyan_mutlak_puan": float(fark.abs().median()), "prim_farki_ort_puan": float(fark.mean()),
                                "n": int(len(fark)),
                                "onceki_ay_sonu_donemler": {ad: {k: v for k, v in oz(d2.loc[a:b]).items()
                                                                 if k in ("n", "prim_ort_puan", "prim_medyan_puan", "prim_eksi_ay_payi")}
                                                            for ad, a, b, _ in PRIM_DONEM}},
        "seri": {"tarih": [_ay(t) for t in d.index], "prim_puan": d["prim"].tolist(), "faiz_farki_puan": d["faiz_farki"].tolist(),
                 "beklenen_deval_yuzde": d["beklenen_deval"].tolist(), "gerceklesen_deval_yuzde": d["gerceklesen_deval"].tolist()},
        "n": int(len(d)), "ilk": _ay(d.index.min()), "son_ay": _ay(d.index.max()),
        "formul": FORMUL_11E,
        "yontem": "Her anket ayında TL ve ABD 1 yıllık faizlerinin log farkından, ankette bildirilen 12 ay sonrası USD/TRY beklentisinin o günkü kura göre log değer kaybı çıkarıldı; kur ve faizler anket yanıt penceresi varsayımıyla ayın ilk on beş gününün ortalamasıdır, bir önceki ay sonu duyarlılık olarak verilir.",
        "kaynak": ["bulut/evds_pka_kur", "bulut/abd_hazine_1y", "dibs_egri_gunluk", "usdtry_yahoo_gunluk"],
        "uyari": "anket kur beklentisi bir ortalamadır (uygun ortalamalar); TL 1 yıllık faiz devlet tahvili getirisidir, mevduat ya da swap faizi değildir; anketin yanıt günleri arşivde yok, pencere varsayımdır",
    }


# ───────────────────────────────────────────────────────── Araç 4 varsayılanları
def arac_kur() -> dict:
    f = oo.oku("fonlama_gunluk")
    tl = f["tlref"].dropna()
    s, _ = oo.usdtry()
    try:
        us = bulut.abd_1y()
        i_star, i_star_ad, i_star_gun = float(us.iloc[-1]), "ABD Hazinesi 1 yıllık par getirisi", us.index[-1]
        i_star_b = ((1 + i_star / 200) ** 2 - 1) * 100
    except bulut.VeriYok:
        k = oo.oku("kuresel_aylik")["faiz_abd"].dropna()
        i_star, i_star_ad, i_star_gun = float(k.iloc[-1]), "ABD politika faizi (BIS)", k.index[-1]
        i_star_b = i_star
    i = float(tl.iloc[-1])
    i_b = ((1 + i / 36500) ** 365 - 1) * 100
    n1y = oo.oku("dibs_egri_gunluk")["n1y"].dropna()
    basabas_b = ((1 + i_b / 100) / (1 + i_star_b / 100) - 1) * 100
    out = {"i_tlref_yuzde": i, "i_tlref_gun": _iso(tl.index[-1]), "i_tlref_yillik_bilesik_yuzde": i_b,
           "i_yildiz_yuzde": i_star, "i_yildiz_ad": i_star_ad, "i_yildiz_gun": _iso(i_star_gun),
           "i_yildiz_yillik_bilesik_yuzde": i_star_b,
           "basabas_basit_puan": i - i_star,
           "basabas_bilesik_yuzde": basabas_b,
           "kur": float(s.iloc[-1]), "kur_gun": _iso(s.index[-1]),
           "basabas_kur_12a": float(s.iloc[-1]) * (1 + basabas_b / 100),
           "dibs_1y_yuzde": float(n1y.iloc[-1]), "dibs_1y_gun": _iso(n1y.index[-1]),
           "basabas_dibs1y_yuzde": ((1 + float(n1y.iloc[-1]) / 100) / (1 + i_star_b / 100) - 1) * 100,
           "yontem": "Taşıma başabaşı, bir yıllık tutuşta USD/TRY'nin taşıma getirisini sıfırlayan değer kaybıdır: basit hâli iki faizin farkı, bileşik hâli TLREF'in günlük bileşikle yıllığa çevrilmiş getirisinin ABD 1 yıllık getirisine oranıdır (gecelik faizin bir yıl sabit kaldığı varsayımıyla); piyasanın bir yıllık faizini kullanan hâli DİBS 1 yıllık getirisiyle kurulur. Aynı sayı, kurun risk primi bloğunda taşımayı sıfırlayan prim artışıdır.",
           "kaynak": ["fonlama_gunluk", "usdtry_yahoo_gunluk", "bulut/abd_hazine_1y", "dibs_egri_gunluk"]}
    try:
        pka = bulut.pka_kur_beklentisi()["usdtry_12a"].dropna()
        out["pka_12a_son"] = float(pka.iloc[-1])
        out["pka_ay"] = _ay(pka.index[-1])
    except (bulut.VeriYok, KeyError):
        out["pka_12a_son"] = None
    return out


def olc() -> dict:
    out = {"p11a": p11a(), "p11b": p11b(), "p11c": p11c(), "p11d": p11d(), "p11e": p11e(),
           "arac_kur": arac_kur(), "sekil_18": sekil_18(), "sekil_19": sekil_19(), "sekil_20": sekil_20()}
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"\n{time.monotonic() - t0:.1f} sn")
