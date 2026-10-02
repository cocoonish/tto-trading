#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 12 (Ülke primi: not, CDS, siyaset) ölçüm katmanı.

Pratikler
  p12_dm     DM not kararları, vaka tablosu (n = 2, t yazılmaz):
             Fitch ABD 01.08.2023 (New York kapanışından sonra → tepki günü
             02.08.2023) ve Moody's ABD 16.05.2025 cuma (kapanıştan sonra →
             tepki günü 19.05.2025). Δ2y ve Δ10y (bp; ABD Hazinesi par getirisi),
             Δdolar sepeti (%; CNBC altı para, New York 17:00), ΔVIX (puan),
             ΔDXY (%); her birinin 250 iş günlük günlük değişim oynaklığına göre
             z'si ve |Δ|'nın o 250 gün içindeki yüzdelik sırası. İki günlük pencere
             (tepki günü + ertesi gün) yanında.
  p12_vekil  Türkiye ülke primi VEKİLLERİ, kusurlarıyla: TÜFEX reel getirisi
             (2 ve 5 yıl; seyreklik ölçülür), DİBS 5 yıl − ABD 10 yıl farkı
             (seviye, haftalık değişimin USD/TRY ve VIX ile ilişkisi). Elde
             olmayanlar (CDS, eurobond fiyat serisi, banka endeksi) "kurulmadı".
  p12        Türkiye kredi notu kararı günleri: sonraki işlem günü ΔUSD/TRY (%) ve
             Δ5y (bp), yön gruplarına (+1 iyileşme · −1 bozulma) göre ortalama;
             kaynak bulut arşivi, gelmediyse "kurulmadı". Olay çalışması ancak
             Bölüm 2'nin plasebo kapısı (tepe 0'da) geçerse kurulur.

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. SAAT: ABD Hazinesi par getirisi New York kapanışı, CNBC kurları New York
     17:00, VIX 16:15 New York. İki karar da bu saatlerden SONRA duyuruldu
     (ders planının tanımı), yani karar günü kapanışı kararı taşımaz; tepki
     günü bir sonraki işlem günüdür. Karar günü kapanışına kadarki hareket ayrı
     satırdadır (duyuru öncesi sızıntı ya da başka haber).
  2. İKİ GÖZLEM KURAL DEĞİLDİR: n = 2 kesit vaka tablosudur; z skoru bir
     test değil, hareketin o serinin sıradan gününe göre büyüklüğünün tarifidir.
     Tepki günü başka duyuruları da taşıyabilir; tablo notun saf etkisi diye
     okunmaz.
  3. TÜFEX REEL GETİRİSİ SEYREKTİR: 2 yıllık iş günlerinin ≈%54'ünde, 5 yıllık
     ≈%22'sinde değer var; boşluk günleri ve en uzun boşluk ölçülüp yazılır.
     Sığ bir kâğıdın getirisi ülke primi değil, o kâğıdın likiditesini de taşır.
  4. DİBS 5y − ABD 10y FARKI KREDİ PRİMİ DEĞİLDİR: TL faizi Türkiye'nin
     enflasyon beklentisini ve politika faizini taşır; fark çoğunlukla enflasyon
     ve politika farkıdır. Konvansiyon da ayrı: DİBS sıfır kuponlu yıllık
     bileşik, ABD par getirisi altı aylık kuponlu. Vekil olarak okunur.
  5. DİBS GÖSTERGE ETİKETİ İKİ İŞ GÜNÜ ÖNDEDİR (Bölüm 1 tuzak 6): haftalık
     değişim ve not kararı tepkisi kaydırılmış etiketle kurulur.
  6. 18.12.2023 ÖNCESİ YAHOO USD/TRY'DE CUMA DEĞERİ PAZARTESİ AÇILIŞIDIR
     (Bölüm 1 tuzak 5): cuma akşamı açıklanan bir not kararının ilk tepkisi
     cuma etiketine düşebilir. Not kararı tepkisi bu yüzden iki ölçüyle
     verilir: karar günü kapanışından sonraki işlem gününe (istenen ölçü) ve
     karar gününden önceki işlem gününden sonraki işlem gününe (iki günlük).
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo
import olcum_b01 as b01
import olcum_b08 as b08

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

kurulmadi = b08.kurulmadi
hukum = b08.hukum

YON_BAS, YON_SON = b01.YONETILEN
OYNAKLIK_PENCERE = 250
DM_KARARLARI = (
    {"ad": "Fitch ABD notunu AAA'dan AA+'ya indirdi", "kurum": "Fitch", "karar_gunu": "2023-08-01",
     "tepki_gunu": "2023-08-02", "saat": "New York kapanışından sonra"},
    {"ad": "Moody's ABD notunu Aaa'dan Aa1'e indirdi", "kurum": "Moody's", "karar_gunu": "2025-05-16",
     "tepki_gunu": "2025-05-19", "saat": "cuma, New York kapanışından sonra"},
)
VEKIL_DONEM = (("oncesi", "2013-01-01", "2021-11-30", "2013-01 … 2021-11"),
               ("yonetilen", "2021-12-01", "2023-06-30", "yönetilen kur 2021-12 … 2023-06 (ayrı dönem)"),
               ("sonrasi", "2023-07-01", "2026-09-30", "2023-07 … 2026-09"))
VAKA_ASGARI = 10


def _iso(t) -> str:
    return str(pd.Timestamp(t).date())


# ───────────────────────────────────────────────────────── p12_dm
@lru_cache(maxsize=1)
def _abd() -> pd.DataFrame:
    a = b01._abd_gunluk()
    return pd.DataFrame({"us2_bp": a["us2"] * 100, "us10_bp": a["us10"] * 100, "dolar_yuzde": a["sepet"] * 100,
                         "dxy_yuzde": a["dxy"] * 100, "vix": a["vix"]})


ALANLAR = (("us2_bp", "d2y_bp"), ("us10_bp", "d10y_bp"), ("dolar_yuzde", "ddolar_yuzde"),
           ("vix", "dvix_puan"), ("dxy_yuzde", "ddxy_yuzde"))


def _pencere(df: pd.DataFrame, bas: pd.Timestamp, son: pd.Timestamp, oyn: pd.Series, kok: float) -> dict:
    out = {}
    for kol, ad in ALANLAR:
        d = float(df.at[son, kol] - df.at[bas, kol])
        s = float(oyn[kol])
        out[ad] = d
        out[ad.rsplit("_", 1)[0] + "_z"] = d / (s * kok) if s else None
    return out


def _dm_vaka(k: dict) -> dict:
    df = _abd()
    kg, tg = pd.Timestamp(k["karar_gunu"]), pd.Timestamp(k["tepki_gunu"])
    idx = df.index
    if kg not in idx or tg not in idx:
        return {**k, **kurulmadi("karar ya da tepki günü ortak işlem günleri arasında yok")}
    j = idx.get_loc(tg)
    if idx[j - 1] != kg:
        return {**k, **kurulmadi("karar günü tepki gününden önceki ortak işlem günü değil")}
    gecmis = df.iloc[j - 1 - OYNAKLIK_PENCERE:j]          # karar gününe kadar (dahil) 250 günlük değişim
    dg = gecmis.diff().iloc[1:]
    oyn = dg.std(ddof=1)
    tepki = _pencere(df, idx[j - 1], tg, oyn, 1.0)
    iki = _pencere(df, idx[j - 1], idx[j + 1], oyn, math.sqrt(2)) if j + 1 < len(idx) else kurulmadi("ertesi gün yok")
    once = _pencere(df, idx[j - 2], kg, oyn, 1.0)
    sira = {}
    for kol, ad in ALANLAR:
        d = abs(float(df.at[tg, kol] - df.at[kg, kol]))
        sira[ad.rsplit("_", 1)[0] + "_yuzdelik"] = float((dg[kol].abs() < d).mean())
    return {**k, "tepki": tepki, "tepki_yuzdelik_sirasi": sira, "iki_gun": {**iki, "son_gun": _iso(idx[j + 1])} if isinstance(iki, dict) and "durum" not in iki else iki,
            "karar_gunu_kapanisa_kadar": once,
            "oynaklik_250": {ad.rsplit("_", 1)[0] + "_sd": float(oyn[kol]) for kol, ad in ALANLAR},
            "oynaklik_ilk": _iso(dg.index.min()), "oynaklik_son": _iso(dg.index.max())}


def p12_dm() -> dict:
    vakalar = [_dm_vaka(k) for k in DM_KARARLARI]
    ilk = min(v["karar_gunu"] for v in vakalar)
    son = max(v["tepki_gunu"] for v in vakalar)
    return {"vakalar": vakalar, "n": len(vakalar), "ilk": ilk, "son": son, "tur": "vaka tablosu (n < 10, t yazılmaz)",
            "yontem": "Her not kararında karar günü kapanışından tepki günü kapanışına ABD 2 ve 10 yıllık getirisinin, altı paralı dolar sepetinin, VIX'in ve DXY'nin değişimi alındı ve karar gününe kadarki 250 iş gününün günlük değişim oynaklığına bölündü; iki günlük pencerede bölen oynaklığın √2 katıdır.",
            "isaret": "dolar sepetinde artış doların değer kazancı; getiride artış faiz yükselişi",
            "saat": "ABD Hazinesi par getirisi New York kapanışı, CNBC kurları New York 17:00, VIX 16:15 New York; iki karar da bu saatlerden sonra duyuruldu",
            "kaynak": ["abd_hazine_gunluk", "cnbc_kur_gunluk", "yahoo_dxy_vix_gunluk"]}


# ───────────────────────────────────────────────────────── p12_vekil
def _seyreklik(s: pd.Series, takvim: pd.DatetimeIndex) -> dict:
    s = s.dropna()
    t = takvim[(takvim >= s.index.min()) & (takvim <= s.index.max())]
    var = t.isin(s.index)
    konum = np.flatnonzero(var)
    bosluk = np.diff(konum) - 1
    j = int(np.argmax(bosluk)) if len(bosluk) else 0
    son = s.index.max()
    hedef = son - pd.DateOffset(years=1)
    yil_once = s[(s.index <= hedef) & (s.index >= hedef - pd.Timedelta(days=14))]   # boşluğa düşerse yazılmaz
    s52 = s[s.index > son - pd.DateOffset(weeks=52)]
    return {"n": int(len(s)), "ilk": _iso(s.index.min()), "son": _iso(son),
            "is_gunu_dolulugu": float(var.mean()),
            "son_252_is_gunu_dolulugu": float(var[-252:].mean()),
            "medyan_bosluk_is_gunu": float(np.median(bosluk)) if len(bosluk) else 0.0,
            "en_uzun_bosluk_is_gunu": int(bosluk.max()) if len(bosluk) else 0,
            "en_uzun_bosluk_basi": _iso(t[konum[j]]) if len(bosluk) else None,
            "en_uzun_bosluk_sonu": _iso(t[konum[j + 1]]) if len(bosluk) else None,
            "son_deger_yuzde": float(s.iloc[-1]),
            "bir_yil_once_yuzde": float(yil_once.iloc[-1]) if len(yil_once) else None,
            "bir_yil_once_gun": _iso(yil_once.index[-1]) if len(yil_once) else None,
            "bir_yil_once_not": None if len(yil_once) else "bir yıl önceki gün bir boşluğa düşüyor; değer yazılmadı",
            "bosluk_sayisi": int((bosluk > 0).sum()),
            "son_52_hafta_gozlem": int(len(s52)),
            "son_52_hafta_en_dusuk_yuzde": float(s52.min()), "son_52_hafta_en_yuksek_yuzde": float(s52.max())}


@lru_cache(maxsize=1)
def _fark_haftalik() -> pd.DataFrame:
    tr = b01._tr_gunluk(b01.DIBS_ETIKET_ONCU)[["n5y", "usdtry"]]
    a = b01._abd_gunluk()[["us10", "vix"]]
    df = tr.join(a, how="inner").dropna(subset=["n5y", "usdtry", "us10"])
    df["fark"] = df["n5y"] - df["us10"]
    w = b01._haftalik(df, b01.TR_ORNEK_SON_GUN)
    w = w[~w["_kismi"].astype(bool)]
    out = pd.DataFrame({"fark": w["fark"], "dfark_bp": w["fark"].diff() * 100, "d5_bp": w["n5y"].diff() * 100,
                        "dus10_bp": w["us10"].diff() * 100, "dkur_yuzde": np.log(w["usdtry"]).diff() * 100,
                        "dvix": w["vix"].diff()}).iloc[1:]
    out["yonetilen"] = (out.index >= YON_BAS) & (out.index <= YON_SON + pd.Timedelta(days=6))
    return out


def _fark_iliski(z: pd.DataFrame) -> dict:
    r = b08._reg(z["dkur_yuzde"], z["dfark_bp"], gecikme=None) if len(z) > 20 else kurulmadi("20 haftadan az")
    return {"n": int(len(z)), "ilk": _iso(z.index.min()), "son": _iso(z.index.max()),
            "kor_kur": float(z["dfark_bp"].corr(z["dkur_yuzde"])), "kor_vix": float(z["dfark_bp"].corr(z["dvix"])),
            "kor_5y_kur": float(z["d5_bp"].corr(z["dkur_yuzde"])),
            "egim_kur_yuzde_100bp": (r["b"][0] * 100) if "b" in r else None, "egim_t": r["t"][0] if "t" in r else None,
            "r2": r.get("r2")}


def p12_vekil() -> dict:
    takvim = b01._tr_takvim()
    d = oo.oku("dibs_egri_gunluk")
    d = d[d.index.isin(takvim)]
    tufex = {k: _seyreklik(d[k], takvim) for k in ("r2y", "r5y")}
    w = _fark_haftalik()
    ay = w["fark"].groupby(w.index.to_period("M")).last()
    don = {ad: {"etiket": et, **_fark_iliski(w.loc[a:b])} for ad, a, b, et in VEKIL_DONEM}
    don["tum_yonetilen_haric"] = {"etiket": "2013–2026, yönetilen kur hariç", **_fark_iliski(w[~w["yonetilen"]])}
    j_max, j_min = w["fark"].idxmax(), w["fark"].idxmin()
    return {
        "tufex_reel": {**tufex,
                       "yontem": "TÜFEX reel getirisinin değer taşıdığı iş günleri Türkiye iş günü takvimiyle karşılaştırıldı; doluluk, ardışık iki gözlem arasındaki boşluk ve en uzun boşluk ölçüldü.",
                       "uyari": "sığ işlem gören kâğıdın getirisi; ülke primi değil, reel faiz ile likiditeyi birlikte taşır",
                       "kaynak": ["dibs_egri_gunluk", "fonlama_gunluk (iş günü takvimi)"]},
        "dibs5y_abd10y": {
            "son_puan": float(w["fark"].iloc[-1]), "son_gun": _iso(w.index[-1]),
            "ort_puan": float(w["fark"].mean()), "en_yuksek_puan": float(w["fark"].max()), "en_yuksek_hafta": _iso(j_max),
            "en_dusuk_puan": float(w["fark"].min()), "en_dusuk_hafta": _iso(j_min),
            "donemler": don,
            "aylik": {"ay": [str(p) for p in ay.index], "fark_puan": ay.tolist()},
            "n": int(len(w)), "ilk": _iso(w.index.min()), "son": _iso(w.index.max()),
            "yontem": "Perşembe kapanışlı haftalık seride DİBS 5 yıllık sıfır kuponlu getirisi ile ABD 10 yıllık par getirisinin farkı alındı; farkın haftalık değişimi USD/TRY ve VIX değişimiyle karşılaştırıldı, eğim Newey–West standart hatalıdır.",
            "uyari": "fark kredi primi değildir; enflasyon ve politika faizi farkını taşır, vade ve faiz konvansiyonu da ayrıdır",
            "kaynak": ["dibs_egri_gunluk", "abd_hazine_gunluk", "usdtry_yahoo_gunluk", "yahoo_dxy_vix_gunluk"]},
        "cds": kurulmadi("Türkiye CDS serisi arşivde yok; ücretsiz ve sürekli bir kaynak bulunamadı"),
        "eurobond_fiyat": kurulmadi("Türkiye eurobond fiyat ya da getiri serisi arşivde yok"),
        "banka_endeksi": kurulmadi("Borsa İstanbul banka endeksi arşivde yok; göreli performans kurulamadı"),
        "n": int(len(w)), "ilk": _iso(w.index.min()), "son": _iso(w.index.max()),
        "yontem": "Ülke primi doğrudan ölçülemediği için elde olan vekiller kusurlarıyla verildi; hiçbiri CDS diye sunulmaz.",
        "kaynak": ["dibs_egri_gunluk", "abd_hazine_gunluk", "usdtry_yahoo_gunluk", "yahoo_dxy_vix_gunluk"],
    }


# ───────────────────────────────────────────────────────── p12 Türkiye not kararları
def _grup(df: pd.DataFrame, kol: str) -> dict:
    x = df[kol].dropna()
    out = {"n": int(len(x))}
    if not len(x):
        return out
    out.update({"ort": float(x.mean()), "medyan": float(x.median())})
    if len(x) >= VAKA_ASGARI:
        r = oo.hac(x.values, np.zeros((len(x), 0)), gecikme=0)
        out["t"] = r["t"][0] if not r.get("yetersiz") else None
        out["tur"] = "test (olaylar bağımsız sayıldı)"
    else:
        out["tur"] = "vaka tablosu (n < 10, t yazılmaz)"
    return out


def p12() -> dict:
    try:
        nk = bulut.not_kararlari()
    except bulut.VeriYok as e:
        return {**kurulmadi(f"Türkiye kredi notu kararlarının tarih listesi gelmedi: {e}"),
                "yontem": "Kurulduğunda: her not kararında karar günü kapanışından sonraki işlem günü kapanışına USD/TRY log değişimi ve DİBS 5 yıllık getiri değişimi alınır, yön (iyileşme ya da bozulma) gruplarına göre ortalanır.",
                "kaynak": ["bulut/not_kararlari", "usdtry_yahoo_gunluk", "dibs_egri_gunluk"]}
    tr = b01._tr_gunluk(b01.DIBS_ETIKET_ONCU)[["n5y", "usdtry"]].dropna()
    idx = tr.index
    satir = []
    for t, r in nk.sort_index().iterrows():
        d = pd.Timestamp(t).normalize()
        i_b = idx.searchsorted(d, side="right") - 1          # karar günü ya da öncesindeki son işlem günü
        i_r = idx.searchsorted(d, side="right")              # karar gününden sonraki ilk işlem günü
        i_o = idx.searchsorted(d, side="left") - 1           # karar gününden önceki son işlem günü
        if i_b < 0 or i_r >= len(idx) or i_o < 0:
            continue
        b, rr, o = idx[i_b], idx[i_r], idx[i_o]
        satir.append({"tarih": _iso(d), "kurum": r.get("kurum"), "eylem": r.get("eylem"),
                      "yon": int(r["yon"]) if pd.notna(r.get("yon")) else None,
                      "taban_gun": _iso(b), "tepki_gunu": _iso(rr),
                      "dkur_yuzde": float(np.log(tr.at[rr, "usdtry"] / tr.at[b, "usdtry"]) * 100),
                      "d5y_bp": float((tr.at[rr, "n5y"] - tr.at[b, "n5y"]) * 100),
                      "iki_gun_dkur_yuzde": float(np.log(tr.at[rr, "usdtry"] / tr.at[o, "usdtry"]) * 100),
                      "iki_gun_d5y_bp": float((tr.at[rr, "n5y"] - tr.at[o, "n5y"]) * 100),
                      "yonetilen": bool(YON_BAS <= d <= YON_SON)})
    if not satir:
        return kurulmadi("not kararlarının hiçbiri kur ve getiri serisinin kapsamına düşmüyor")
    S = pd.DataFrame(satir)
    normal = S[~S["yonetilen"]]
    # Bölüm 2 plasebo kapısı: tepki günleri kur değişim serisinde tepe 0'da mı
    try:
        import olcum_b02 as b02
        dk = np.log(tr["usdtry"]).diff() * 100
        gun = pd.DatetimeIndex(sorted(set(pd.to_datetime(normal["tepki_gunu"]))))
        prof = oo.olay_profili(dk, gun, b02.PENCERE)
        kapi = {"gecti": bool(b02._kapi_hukmu(prof)), "profil": prof}
    except Exception as e:  # noqa: BLE001
        kapi = kurulmadi(f"plasebo kapısı kurulamadı: {e}")
    if isinstance(kapi, dict) and kapi.get("gecti"):
        gruplar = {}
        for yon, ad in ((1, "iyilesme"), (-1, "bozulma"), (0, "notr")):
            g = normal[normal["yon"] == yon]
            gruplar[ad] = {k: _grup(g, k) for k in ("dkur_yuzde", "d5y_bp", "iki_gun_dkur_yuzde", "iki_gun_d5y_bp")}
    else:
        gruplar = kurulmadi("plasebo kapısı geçmedi: tepki günü kur hareketi komşu günlerden ayrışmıyor; kararlar yalnız vaka listesi olarak verilir")
    return {"kararlar": satir, "gruplar": gruplar, "plasebo_kapisi": kapi,
            "olay_calismasi": "kuruldu" if isinstance(kapi, dict) and kapi.get("gecti") else "kurulmadi: plasebo kapısı geçmedi, tablo vaka listesi olarak okunur",
            "n": int(len(S)), "ilk": S["tarih"].min(), "son": S["tarih"].max(),
            "yonetilen_disarida": int(S["yonetilen"].sum()),
            "yontem": "Her not kararında karar günü kapanışından sonraki işlem günü kapanışına USD/TRY log değişimi ve DİBS 5 yıllık getiri değişimi alındı; iki günlük ölçü karar gününden önceki işlem gününden başlar. Yönetilen kur dönemindeki kararlar gruplara girmez.",
            "saat": "USD/TRY Yahoo (2023-12-18'e kadar Londra gece yarısı, sonra İstanbul 18:00); DİBS gösterge etiketi iki iş günü kaydırılmış",
            "kaynak": ["bulut/not_kararlari", "usdtry_yahoo_gunluk", "dibs_egri_gunluk", "fonlama_gunluk (iş günü takvimi)"]}


def olc() -> dict:
    out = {"p12_dm": p12_dm(), "p12_vekil": p12_vekil(), "p12": p12()}
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"\n{time.monotonic() - t0:.1f} sn")
