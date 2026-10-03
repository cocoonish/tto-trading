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
  p12        Türkiye kredi notu kararları (2012–2024; her karar `veri/kaynaklar.json`
             kaydına bağlı, doğrulama durumu ve günün dayanağı kayıttan — sayımlar
             ölçümde): ilan anının (İstanbul saati) iki yanındaki gözlemler arasında
             ΔUSD/TRY (%) ve Δ5y (bp), seri başına kendi gözlem saatiyle; yön
             gruplarına göre ortalama (bütün kararlar · yalnız doğrulanmışlar). Olay
             çalışması ancak dersin kanonik plasebo sınaması (`ortak_olc.olay_kapisi`,
             güçlü kural; kur serisinde yönetilen kur dönemi dışarıda) geçerse
             kurulur. Kapının değişim serisi TABLONUN düzey serisinden kurulur
             (tuzak 6); günü kaynakta yazmayan kararlar dışarıda bırakılarak kapı
             ayrıca sorulur (tuzak 8).

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
  5. DİBS HİZASI "gun_sonu" (`ortak_olc.DIBS_KAYMA`, k = 2): L etiketli değer
     L−1'in sabah sabitlemesidir; haftalık değişim ve not kararı tepkisi gün
     sonu kurla (Yahoo) aynı güne oturtulur — D gününe D'den iki Türkiye iş günü
     sonraki etiket yazılır.
  6. 18.12.2023 ÖNCESİ YAHOO USD/TRY'NİN D DEĞERİ D'NİN LONDRA GECE YARISIDIR
     (İstanbul 02:00–03:00): akşam açıklanan HER not kararı — yalnız cuma
     akşamı değil — o gün etiketine düşer; cuma değeri ayrıca hafta sonu
     açılışından sonraki fiyattır (Bölüm 1 tuzak 5). Yani bu dönemde "karar
     günü kapanışından sonraki işlem günü" ölçüsü kararın ilk tepkisini
     KAÇIRABİLİR; DİBS ise gün sonu (kararın öncesi) kalır. Not kararı tepkisi
     bu yüzden iki ölçüyle verilir: karar günü kapanışından sonraki işlem
     gününe (istenen ölçü) ve karar gününden önceki işlem gününden sonraki
     işlem gününe (iki günlük; 2023-12-18 öncesinde kur için birincil okuma).
     Plasebo sınaması her seri için ayrı sorulur ve bu kaymayı ölçer. CUMA
     (`usdtry(cuma_dus=True)`): not kararları çoğunlukla cuma akşamı açıklanır
     ve geçiş öncesi cuma değeri pazartesi barının başıdır (kararın ilk
     tepkisini zaten taşır); o cumalar çerçeveden düşer, yani cuma kararının
     tabanı perşembe kapanışı, tepkisi pazartesi kapanışıdır. Haftalık vekil
     perşembe örnekler, cumaya dokunmaz.
     PLASEBO SERİSİ AYNI DÜZEY SERİSİNDEN: kapının değişim serisi tablonun
     gözlemlerinin ardışık log farkıdır (yalnız hafta içi, kendi işlem günleri).
     `tr_gunluk_degisim(cuma_dus=True)` KULLANILMAZ: o çerçeve cuma DEĞİŞİMİNİ
     boşaltıp pazartesi değişimini cuma değerinden başlatır, yani cuma akşamı ve
     hafta sonu kararlarında ilk tepkiyi (perşembe → cuma değeri) hiçbir kaymaya
     koymaz; ayrıca Türkiye takvimine oturduğu için Türkiye tatilindeki tepki
     günlerini (01.05, 15.07) ve 2013 öncesini düşürür. Bedeli: 18.12.2023
     öncesinde pazartesi değişimi İKİ seans taşır (perşembe → pazartesi; ölçüldü:
     ortalama |Δ| pazartesi ≈ 1,4 × öbür günler), temel kural pazartesi olaylarında
     kolaylaşır; hüküm haftanın günü eşlemeli rastgele kıyastan (güçlü kural)
     okunur. Eşleme 18.12.2023 öncesi ile sonrasının pazartesilerini AYIRMAZ
     (sonrasında pazartesi tek seanslık; ölçüldü: o dönemde pazartesi |Δ| öbür
     günlerle aynı), yani 2024 tepki günleri rastgele kümelerde payından az temsil
     edilir; kapı bu yüzden yalnız geçiş öncesiyle de sorulur (`gecis_oncesi`,
     oranlar `pazartesi_abs`). Bu kararlarda −1 kayması perşembe, −2 çarşambadır. İlan bir gözlemin
     aralığına düşen ya da saati bilinmeyen kararlarda tablo penceresi iki adımdır
     ama kapının olay günü yalnız tepki gününün değişimidir (`iki_adimli_pencere`).
  7. BAYRAM HAFTALARI: 2013-10, 2016-07 ve 2016-09'da haftanın bütün iş günleri
     tatildir; satır düşer ve sonraki fark iki haftalık olur. Bu üç fark
     haftalık değişim sayılmaz.
  8. GÜNÜ KAYNAKTA YAZMAYAN KARARLAR (`gun_dayanagi`): üç kararın günü ertesi
     günün ilk haberinden çıkarıldı, birininki kurumun önceden ilan ettiği
     takvimden; kaynakta yalnız ilk haberin damgası var (`ilk_iz`). Liste onları
     işaretli taşır, kapı ayrıca onlarsız sorulur (`plasebo_kapisi_gunu_kaynakta`).
     Aynı durumdaki Fitch Ağustos 2016 listede yok: ilk çağdaş haberi iki gün
     sonra (pazartesi), yani gün ertesi sabahla da sınırlanamıyor.
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

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

kurulmadi, hukum = oo.kurulmadi, oo.hukum      # tek tanımlar ortak_olc'de
_reg = oo.reg

YON_BAS, YON_SON = oo.YONETILEN
DIBS_HIZA = "gun_sonu"                          # tuzak 5
OYNAKLIK_PENCERE = 250
DM_KARARLARI = (
    {"ad": "Fitch ABD notunu AAA'dan AA+'ya indirdi", "kurum": "Fitch", "karar_gunu": "2023-08-01",
     "tepki_gunu": "2023-08-02", "saat": "New York kapanışından sonra"},
    {"ad": "Moody's ABD notunu Aaa'dan Aa1'e indirdi", "kurum": "Moody's", "karar_gunu": "2025-05-16",
     "tepki_gunu": "2025-05-19", "saat": "cuma, New York kapanışından sonra"},
)
VEKIL_DONEM = (("oncesi", "2013-01-01", oo.YON_ONCESI_SON, f"2013-01 … {oo.YON_ONCESI_AY}"),
               ("yonetilen", oo.YON_ILK, oo.YON_SON, f"yönetilen kur {oo.YON_AY[0]} … {oo.YON_AY[1]} (ayrı dönem)"),
               ("sonrasi", oo.YON_SONRASI_ILK, "2026-09-30", f"{oo.YON_SONRASI_AY} … 2026-09"))
VAKA_ASGARI = 10


_iso = oo._iso                                  # tek tanım ortak_olc'de


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
    tr = b01._tr_gunluk(DIBS_HIZA)[["n5y", "usdtry"]]
    a = b01._abd_gunluk()[["us10", "vix"]]
    df = tr.join(a, how="inner").dropna(subset=["n5y", "usdtry", "us10"])
    df["fark"] = df["n5y"] - df["us10"]
    w = b01._haftalik(df, b01.TR_ORNEK_SON_GUN)
    w = w[~w["_kismi"].astype(bool)]
    out = pd.DataFrame({"fark": w["fark"], "dfark_bp": w["fark"].diff() * 100, "d5_bp": w["n5y"].diff() * 100,
                        "dus10_bp": w["us10"].diff() * 100, "dkur_yuzde": np.log(w["usdtry"]).diff() * 100,
                        "dvix": w["vix"].diff(), "_gun": w["_gun"]}).iloc[1:]
    # Tuzak 7: Türkiye'de bütün haftayı kaplayan bayramlarda (2013-10, 2016-07, 2016-09)
    # haftanın ortak günü yok ve satır düşer; sonraki farkı İKİ haftalık değişimdir. Haftalık
    # değişim sayılmaz, boş bırakılır (seviye kalır).
    iki = out.index.to_series().diff().dt.days > 7
    out.loc[iki, ["dfark_bp", "d5_bp", "dus10_bp", "dkur_yuzde", "dvix"]] = np.nan
    out["iki_haftalik"] = iki
    out["yonetilen"] = (out.index >= YON_BAS) & (out.index <= YON_SON + pd.Timedelta(days=6))
    return out


def _fark_iliski(z: pd.DataFrame) -> dict:
    r = _reg(z["dkur_yuzde"], z["dfark_bp"], gecikme=None) if len(z) > 20 else kurulmadi("20 haftadan az")
    return {"n": int(z["dfark_bp"].notna().sum()), "ilk": _iso(z.index.min()), "son": _iso(z.index.max()),
            "kor_kur": float(z["dfark_bp"].corr(z["dkur_yuzde"])), "kor_vix": float(z["dfark_bp"].corr(z["dvix"])),
            "kor_5y_kur": float(z["d5_bp"].corr(z["dkur_yuzde"])),
            "egim_kur_yuzde_100bp": (r["b"][0] * 100) if "b" in r else None, "egim_t": r["t"][0] if "t" in r else None,
            "r2": r.get("r2"), **_oos_hukum(z, r)}


def _oos_hukum(z: pd.DataFrame, r: dict) -> dict:
    if "t" not in r or len(z) < 100:
        return {"hukum": "tarif edici",
                "hukum_notu": "100 haftadan kısa ya da ayrı dönem: örneklem dışı sınama kurulmadı, hüküm kurulmaz"}
    o = oo.oos_takimi(z["dkur_yuzde"], z["dfark_bp"], 52)          # iki saf kıyas, ufuk 1
    return {"oos": o, "hukum": hukum(r["t"][0], oo.takim_oranlari(o)),
            "hukum_notu": "eşzamanlı ilişki; örneklem dışı sınama aynı haftanın fark değişimi bilinirken kurulur"}


def p12_vekil() -> dict:
    takvim = oo.tr_takvim()
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
                       "tarih_notu": "tarihler DİBS gösterge etiketidir; piyasa günü iki iş günü geridedir",
                       "yontem": "TÜFEX reel getirisinin değer taşıdığı iş günleri Türkiye iş günü takvimiyle karşılaştırıldı; doluluk, ardışık iki gözlem arasındaki boşluk ve en uzun boşluk ölçüldü.",
                       "uyari": "sığ işlem gören kâğıdın getirisi; ülke primi değil, reel faiz ile likiditeyi birlikte taşır",
                       "kaynak": ["dibs_egri_gunluk", "fonlama_gunluk (iş günü takvimi)"]},
        "dibs5y_abd10y": {
            "son_puan": float(w["fark"].iloc[-1]), "son_gun": _iso(w.index[-1]),
            "son_ornek_gunu": _iso(w["_gun"].iloc[-1]),
            "tarih_notu": "hafta tarihleri cuma etiketidir; değer haftanın perşembe kapanışıdır (DİBS etiketi o güne iki iş günü kaydırılmış)",
            "iki_haftalik_dusen_degisim": [_iso(t) for t in w.index[w["iki_haftalik"]]],
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


SAAT_DIBS = ("10:00", "14:00")      # DİBS gösterge sabitlemesi bu aralıkta (Bölüm 2: PPK 14:00 ertesi sabah, TÜFE 10:00 aynı sabah)


def _an(gun: pd.Timestamp, saat: str) -> pd.Timestamp:
    h, m = saat.split(":")
    return gun + pd.Timedelta(hours=int(h), minutes=int(m))


def _gozlem_araligi(seri: str, gun: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Bir günlük gözlemin İstanbul saatiyle hangi aralıkta alındığı.
    DİBS (sabah hizası): o günün sabitlemesi, 10:00–14:00. USD/TRY: 18.12.2023'ten İstanbul 18:00;
    öncesinde Yahoo günlük barı bir iş günü geri alınmış, yani D'nin değeri D'nin Londra gece
    yarısıdır — New York kapanışından (İstanbul ≈ 00:00) Londra gece yarısına (İstanbul 02:00–03:00)."""
    if seri == "dibs":
        return _an(gun, SAAT_DIBS[0]), _an(gun, SAAT_DIBS[1])
    if gun >= oo.GECIS_YAHOO_CUMA:
        return _an(gun, "18:00"), _an(gun, "18:00")
    return gun + pd.Timedelta(days=1), gun + pd.Timedelta(days=1, hours=3)


def _ilan_penceresi(seri: str, idx: pd.DatetimeIndex, a_bas: pd.Timestamp, a_son: pd.Timestamp):
    """Taban: gözlemi kararın ilanından ÖNCE biten son gün; tepki: gözlemi ilandan SONRA başlayan ilk gün.
    İlan saati bilinmiyorsa ilan aralığı bütün gündür; ilan bir gözlem aralığının içine düşerse o gün
    ne taban ne tepki olur (pencere iki gözlem adımı olur)."""
    taban = tepki = None
    for d in idx[idx <= a_son.normalize()][::-1]:
        if _gozlem_araligi(seri, d)[1] < a_bas:
            taban = d
            break
    for d in idx[idx >= a_bas.normalize() - pd.Timedelta(days=1)]:
        if _gozlem_araligi(seri, d)[0] > a_son:
            tepki = d
            break
    return taban, tepki


def _metin(x) -> str | None:
    """Arşiv hücresi: boş dizge ve eksik değer None."""
    return x if isinstance(x, str) and x.strip() else None


GUN_DAYANAGI = ("kaynak", "takvim", "cikarim")
PLASEBO_SINIR = ("Rastgele kıyas yalnız olay günü oranını sınar; öbür kaymaların oranı tarif edicidir, ayrıca "
                 "sınanmadı.")


def _kapi(dk: pd.Series, gun: pd.DatetimeIndex, tohum: int, haric, gozlem: bool = False) -> dict:
    """Kanonik güçlü kural + tam seri profili + haftanın günü etkisinden arındırılmış profil.
    `gozlem`: kaymalar iş günü değil serinin kendi gözlemleridir (kur: 18.12.2023 öncesinde cuma
    gözlemi yok, pazartesinin bir öncesi perşembedir); sebep metni birimini taşır."""
    try:
        kp = oo.olay_kapisi(dk, gun, guclu=True, k_tohum=tohum, haric=haric)
    except Exception as e:  # noqa: BLE001 — kapı HESAPLANAMADI; "geçmedi" diye yazılmaz
        return kurulmadi(f"plasebo sınaması hesaplanamadı: {e}")
    out = {**oo.kapi_ozeti(kp), "profil": oo.olay_profili(dk, gun, oo.OLAY_PENCERE)}
    for a in ("gun_etkisinden_arindirilmis", "arindirilmis_tepe", "gun_eslemeli_kiyas"):
        if a in kp:
            out[a] = kp[a]
    if not kp["gecti"]:
        out["sebep"] = oo.kapi_sebebi(kp).replace("iş gününde", "gözlemde") if gozlem else oo.kapi_sebebi(kp)
    out["kayma_birimi"] = ("gözlem (18.12.2023 öncesinde cuma gözlemi yok: pazartesinin bir öncesi perşembe, iki "
                           "öncesi çarşamba)" if gozlem else "Türkiye iş günü")
    if kp.get("tepe") not in (None, 0):
        out["tepe_katkisi"] = _tepe_katkisi(dk, gun, haric, int(kp["tepe"]))
    out["sinir"] = PLASEBO_SINIR
    if gozlem:
        out["pazartesi_abs"] = _pazartesi_abs(dk, gun, haric)
        out["gecis_oncesi"] = _gecis_oncesi(dk, gun, tohum, haric)
    return out


def _ornek(dk: pd.Series, gun: pd.DatetimeIndex, haric) -> tuple[pd.Series, pd.DatetimeIndex]:
    """Kapının örneklemiyle aynı kesim: olay listesinin ±10 günü, `haric` dönemi dışarıda."""
    s = dk.dropna()
    s = s.loc[str((gun.min() - pd.Timedelta(days=10)).date()):str((gun.max() + pd.Timedelta(days=10)).date())]
    ev = gun[(gun >= s.index.min()) & (gun <= s.index.max())]
    if haric is not None:
        s, ev, _ = oo.donem_disi(s, ev, haric)
    return s, ev


def _pazartesi_abs(dk: pd.Series, gun: pd.DatetimeIndex, haric) -> dict:
    """Kapının örnekleminde pazartesi |Δ| ortalamasının öbür hafta içi günlerine oranı, 18.12.2023
    öncesi ve sonrası ayrı (tarif: haftanın günü eşlemesi iki dönemin pazartesisini ayırmaz)."""
    s, _ = _ornek(dk, gun, haric)
    out = {}
    for ad, x in (("gecis_oncesi", s[s.index < oo.GECIS_YAHOO_CUMA]), ("gecis_sonrasi", s[s.index >= oo.GECIS_YAHOO_CUMA])):
        a = x.abs()
        pzt, oteki = a[a.index.dayofweek == 0], a[a.index.dayofweek != 0]
        out[ad] = ({"pazartesi": float(pzt.mean()), "oteki_gunler": float(oteki.mean()),
                    "oran": float(pzt.mean() / oteki.mean()), "n_pazartesi": int(len(pzt)), "n_oteki": int(len(oteki))}
                   if len(pzt) and len(oteki) else None)
    out["not"] = ("plasebo sınamasının örneklemindeki bütün günler (olay pencereleri dahil): pazartesi mutlak değişiminin "
                  "ortalaması ve öbür hafta içi günlerinin ortalamasına oranı, 18.12.2023 öncesi ve sonrası ayrı")
    return out


def _gecis_oncesi(dk: pd.Series, gun: pd.DatetimeIndex, tohum: int, haric) -> dict:
    """Aynı kapı, yalnız 18.12.2023 öncesinin gözlemleri ve tepki günleriyle: o dönemde bütün
    pazartesiler iki seanslıktır, haftanın günü eşlemesi dönem farkını taşımaz."""
    on = dk[dk.index < oo.GECIS_YAHOO_CUMA]
    go = gun[gun < oo.GECIS_YAHOO_CUMA]
    n_sonra = int(len(gun) - len(go))
    yontem = ("Haftanın günü eşlemesi 18.12.2023 öncesindeki ve sonrasındaki pazartesileri ayırmaz: öncesinde "
              "pazartesi değişimi perşembeden pazartesiye uzanır, sonrasında cumadan pazartesiye. Plasebo sınaması yalnız "
              f"18.12.2023 öncesinin gözlemleri ve tepki günleriyle yeniden soruldu ({n_sonra} tepki günü sonraki "
              "dönemde kaldı); bu dönemde bütün pazartesiler aynı uzunluktadır.")
    if not len(go):
        return {**kurulmadi("18.12.2023 öncesinde tepki günü yok"), "yontem": yontem}
    try:
        kg = oo.olay_kapisi(on, go, guclu=True, k_tohum=tohum, haric=haric)
    except Exception as e:  # noqa: BLE001 — kapı HESAPLANAMADI; "geçmedi" diye yazılmaz
        return {**kurulmadi(f"plasebo sınaması hesaplanamadı: {e}"), "yontem": yontem}
    out = {**oo.kapi_ozeti(kg), "disarida_kalan_tepki_gunu": n_sonra}
    for a in ("gun_etkisinden_arindirilmis", "arindirilmis_tepe", "gun_eslemeli_kiyas"):
        if a in kg:
            out[a] = kg[a]
    if not kg["gecti"]:
        out["sebep"] = oo.kapi_sebebi(kg).replace("iş gününde", "gözlemde")
    out["yontem"] = yontem
    return out


def _tepe_katkisi(dk: pd.Series, gun: pd.DatetimeIndex, haric, tepe: int, k: int = 3) -> dict:
    """Tepenin düştüğü kaymada |Δ| toplamının en büyük `k` gözlemden gelen payı (tarif; kapının
    örneklemiyle aynı kesim: olay listesinin ±10 günü, `haric` dönemi dışarıda)."""
    s, ev = _ornek(dk, gun, haric)
    idx = s.index
    sat = []
    for e in ev:
        if e not in idx:
            continue
        p = idx.get_loc(e) + tepe
        if 0 <= p < len(idx):
            sat.append((abs(float(s.iloc[p])), _iso(e), _iso(idx[p])))
    sat.sort(key=lambda x: (-x[0], x[1]))
    top = sum(x[0] for x in sat[:k])
    return {"kayma": tepe, "n": len(sat), "en_buyuk": [{"olay_gunu": o, "kayma_gunu": g, "abs_degisim": a}
                                                        for a, o, g in sat[:k]],
            "en_buyuk_pay": top / sum(x[0] for x in sat) if sat else None,
            "not": f"tepe kaymasındaki mutlak değişim toplamının en büyük {k} gözlemden gelen payı"}


def p12() -> dict:
    try:
        nk = bulut.not_kararlari()
    except bulut.VeriYok as e:
        return {**kurulmadi(f"Türkiye kredi notu kararlarının tarih listesi gelmedi: {e}"),
                "kaynak": ["bulut/not_kararlari", "usdtry_yahoo_gunluk", "dibs_egri_gunluk"]}
    # DİBS Türkiye iş günü takviminde (sabah hizası); kur kendi işlem günlerinde (döviz Türkiye tatilinde de
    # işlem görür), 18.12.2023 öncesi cumalar boş (değer pazartesi barının başı)
    seri = {"dibs": oo.tr_gunluk("sabah", ("n5y",), kur=False)["n5y"].dropna(),
            "kur": oo.usdtry(cuma_dus=True)[0].dropna()}
    seri["kur"] = seri["kur"][seri["kur"].index.dayofweek < 5]
    satir = []
    for t, r in nk.sort_index().iterrows():
        g = pd.Timestamp(t).normalize()
        saat = r.get("ilan_saati")
        bilinen = isinstance(saat, str) and ":" in saat
        aksam = r.get("ilan_dilimi") == "aksam"
        if bilinen:
            a_bas = a_son = _an(g, saat)
        elif aksam:            # kaynak "akşam" diyor: İstanbul 18:00'den ertesi gün 03:00'e
            a_bas, a_son = _an(g, "18:01"), g + pd.Timedelta(days=1, hours=3)
        else:                  # saat bilinmiyor: bütün gün
            a_bas, a_son = g, g + pd.Timedelta(hours=23, minutes=59)
        dayanak = _metin(r.get("gun_dayanagi"))
        if dayanak not in GUN_DAYANAGI:
            raise ValueError(f"not kararı {r.get('anahtar')}: günün dayanağı tanınmıyor ({dayanak!r})")
        k = {"tarih": _iso(g), "ilan_saati": saat if bilinen else ("akşam" if aksam else None), "kurum": r.get("kurum"),
             "eylem": r.get("eylem"), "yon": int(r["yon"]), "durum": r.get("durum"), "anahtar": r.get("anahtar"),
             "gun_dayanagi": dayanak, "ilk_iz": _metin(r.get("ilk_iz")),
             "yonetilen": bool(YON_BAS <= g <= YON_SON)}
        for ad, x in seri.items():
            tb, tp = _ilan_penceresi(ad, x.index, a_bas, a_son)
            if tb is None or tp is None:
                k[f"{ad}_taban"] = k[f"{ad}_tepki"] = None
                continue
            k[f"{ad}_taban"], k[f"{ad}_tepki"] = _iso(tb), _iso(tp)
            k[f"{ad}_adim"] = int(((x.index > tb) & (x.index <= tp)).sum())
            k["d5y_bp" if ad == "dibs" else "dkur_yuzde"] = (
                float((x.at[tp] - x.at[tb]) * 100) if ad == "dibs" else float(np.log(x.at[tp] / x.at[tb]) * 100))
        satir.append(k)
    # aynı pencereyi paylaşan kararlar (aynı akşam iki kurum): tepki ayrıştırılamaz, işaretlenir
    for k in satir:
        k["ortak_pencere"] = [x["anahtar"] for x in satir if x is not k and x.get("kur_tepki") == k.get("kur_tepki")
                              and x.get("kur_taban") == k.get("kur_taban") and x.get("kur_tepki")]
    S = pd.DataFrame(satir)
    if not len(S):
        return kurulmadi("not kararlarının hiçbiri kur ve getiri serisinin kapsamına düşmüyor")
    normal = S[~S["yonetilen"]]
    # Tuzak 6: kapının değişim serisi TABLONUN düzey serisinden (aynı gözlemler, ardışık log farkı);
    # 18.12.2023 öncesinde pazartesi değişimi perşembe → pazartesi ve kararın ilk tepkisini taşır.
    dg = {"kur": (np.log(seri["kur"]).diff() * 100.0).dropna(), "dibs": (seri["dibs"].diff() * 100.0).dropna()}
    kapi, kapi_kaynak, gruplar, iki_adim = {}, {}, {}, {}
    kaynakta = normal[normal["gun_dayanagi"] == "kaynak"]
    for ad, kol, dk, haric, tohum in (("kur", "dkur_yuzde", dg["kur"], oo.YONETILEN, 300),
                                      ("dibs_5y", "d5y_bp", dg["dibs"], None, 301)):
        on = "kur" if ad == "kur" else "dibs"
        kt = f"{on}_tepki"
        gun = pd.DatetimeIndex(sorted(set(pd.to_datetime(normal[kt].dropna()))))
        kapi[ad] = _kapi(dk, gun, tohum, haric, gozlem=(ad == "kur"))
        kapi[ad]["seri"] = (
            "tablonun gözlemleri: USD/TRY'nin ardışık iki hafta içi gözlemi arasındaki log farkı ×100; 18.12.2023 "
            "öncesinde cuma kuru boş olduğu için pazartesi değişimi perşembe gözleminden pazartesi gözlemine uzanır, "
            "cuma akşamı ve hafta sonu ilan edilen kararın ilk tepkisini taşır ve iki seanslıktır; bu kararlarda bir "
            "önceki gözlem perşembe, iki önceki çarşambadır" if ad == "kur" else
            "tablonun gözlemleri: DİBS 5 yıllık getirisinin ardışık iki sabah sabitlemesi arasındaki fark, baz puan")
        ia = normal[(normal[f"{on}_adim"] > 1) & normal[kt].notna()][kt]
        iki_adim[ad] = sorted(set(ia) & {_iso(x) for x in gun})
        # Tuzak 8: günü kaynakta yazmayan kararlar dışarıda. Tohum aynı ama rastgele kümeler AYNI DEĞİL:
        # küme büyüklüğü, haftanın günü bileşimi ve yasak pencereler olay kümesine bağlı (ölçüldü: ortak gün 0).
        gk = pd.DatetimeIndex(sorted(set(pd.to_datetime(kaynakta[kt].dropna()))))
        kapi_kaynak[ad] = _kapi(dk, gk, tohum, haric, gozlem=(ad == "kur"))
        if kapi[ad].get("durum"):
            gruplar[ad] = kurulmadi("plasebo sınaması hesaplanamadığı için olay çalışması kurulmadı; kararlar yalnız vaka listesi olarak verilir")
        elif not kapi[ad]["gecti"]:
            gruplar[ad] = kurulmadi("plasebo sınaması geçmedi: tepki günü hareketi komşu günlerden ayrışmıyor; kararlar yalnız vaka listesi olarak verilir")
        else:
            gruplar[ad] = {}
            for kume, M in (("tum", normal), ("dogrulandi", normal[normal["durum"] == "dogrulandi"])):
                gruplar[ad][kume] = {yad: _grup(M[M["yon"] == yon], kol) for yon, yad in ((1, "iyilesme"), (-1, "bozulma"))}
    kurulan = [ad for ad in kapi if not kapi[ad].get("durum") and kapi[ad]["gecti"]]
    disi = S[S["gun_dayanagi"] != "kaynak"]
    return {"kararlar": satir, "gruplar": gruplar, "plasebo_kapisi": kapi,
            "plasebo_kapisi_gunu_kaynakta": {
                **kapi_kaynak, "n_karar": int(len(kaynakta)),
                "disarida": [x for x in normal["anahtar"] if x not in set(kaynakta["anahtar"])],
                "yontem": "Aynı plasebo sınaması, günü kaynakta yazan kararlarla yeniden soruldu (ertesi günün haberinden ya da "
                          "kurumun takviminden çıkarılan günler dışarıda); rastgele gün kümeleri bu olay kümesinin "
                          "büyüklüğü ve haftanın günü bileşimiyle yeniden çekildi."},
            "iki_adimli_pencere": {**iki_adim,
                                   "not": "Bu tepki günlerinde tablo penceresi iki gözlem adımıdır (ilan bir gözlemin "
                                          "aralığına düşüyor ya da saati bilinmiyor); plasebo sınamasının olay günü "
                                          "yalnız tepki gününün değişimidir."},
            "olay_calismasi": ("kuruldu: " + ", ".join(kurulan)) if kurulan else "kurulmadi: tablo vaka listesi olarak okunur",
            "n": int(len(S)), "n_dogrulandi": int((S["durum"] == "dogrulandi").sum()),
            "n_kismen": int((S["durum"] == "kismen").sum()),
            "gun_dayanagi_sayisi": {d: int((S["gun_dayanagi"] == d).sum()) for d in GUN_DAYANAGI},
            "gunu_kaynakta_olmayan": [{"anahtar": r["anahtar"], "tarih": r["tarih"], "kurum": r["kurum"],
                                       "dayanak": r["gun_dayanagi"], "ilk_iz": r["ilk_iz"]}
                                      for _, r in disi.iterrows()],
            "n_bozulma": int((S["yon"] == -1).sum()), "n_iyilesme": int((S["yon"] == 1).sum()),
            "ilk": S["tarih"].min(), "son": S["tarih"].max(),
            "yonetilen_disarida": int(S["yonetilen"].sum()),
            "saati_bilinen": int(S["ilan_saati"].notna().sum()),
            "yontem": ("Her kararın ilan anı İstanbul saatiyle haberin ilk arşiv damgasıdır. Pencerenin tabanı, gözlemi "
                       "ilandan ÖNCE alınan son gün; tepkisi, gözlemi ilandan SONRA alınan ilk gündür. Gözlemin saati "
                       "seriye göre ayrıdır: DİBS gösterge getirisi sabah sabitlemesidir (10:00–14:00), USD/TRY "
                       "18.12.2023'ten İstanbul 18:00 kapanışı, öncesinde Londra gece yarısı (İstanbul 00:00–03:00). "
                       "Kaynak saat vermeyip 'akşam' diyorsa ilan aralığı İstanbul 18:00 ile ertesi gün 03:00 arasıdır; hiç "
                       "bilinmiyorsa bütün gündür ve pencere o günü iki yandan kuşatır. "
                       "Yönetilen kur dönemindeki kararlar gruplara girmez; 18.12.2023 öncesi cuma kuru boştur. "
                       "Plasebo sınaması tablonun aynı gözlemlerinden kurulan değişim serisiyle yapılır: o dönemde "
                       "pazartesi değişimi perşembeden pazartesiye uzanır, cuma akşamı ve hafta sonu kararlarının ilk "
                       "tepkisini taşır ve iki seanslık olduğu için olay günü oranı haftanın günü aynı rastgele gün "
                       "kümeleriyle kıyaslanır. Bu eşleme 18.12.2023 sonrasının tek seanslık pazartesilerini öncekilerden "
                       "ayırmadığı için kur sınaması yalnız 18.12.2023 öncesiyle de yapıldı. Günü kaynakta yazmayan "
                       "kararlar listede işaretlidir; sınama onlarsız da yapıldı."),
            "saat": "ilan saati kaynak kaydından; DİBS sabah hizası (10:00–14:00); USD/TRY İstanbul 18:00 (18.12.2023'ten), öncesinde Londra gece yarısı",
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
