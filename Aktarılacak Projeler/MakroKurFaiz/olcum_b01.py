#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 1 (Çerçeve) ölçüm katmanı.

Pratikler
  p1a   ABD: Δ10y (bp) ile Δdolar (%) arasındaki 60 iş günlük kayan korelasyon
        ve aynı pencerenin VIX ortalaması, 2000–2026; korelasyon işaretinin
        VIX'in genişleyen pencereli dörttebirliklerine göre dağılımı; iki vaka
        penceresi (2011 sonu güvenli liman · Nisan 2025 kurumsal risk).
  p1b   Türkiye: haftalık (perşembe; tuzak 5) Δ5y (bp) × ΔUSD/TRY (%) kadran payları, beş dönem;
        aynı tablo ABD için (Δ10y × dolar).
  rejim haftalık rejim etiketleri (ABD R1/R2/R5, Türkiye R3/R4/R5) —
        `rejim()` öbür bölüm modüllerine açıktır; b01 kimseyi içe aktarmaz.
  sekil_01  haftalık örneklenmiş kayan korelasyon + VIX.

ÖLÇÜLEREK BULUNAN TUZAKLAR (kod onları kapatır, metin adıyla anar)
  1. DİBS eğrisi Türkiye tatillerinde de satır taşıyor (2013–2026'da 136 gün;
     ör. 10–12.04.2024 Ramazan Bayramı). Gösterge değeri yayımlanmıyor ama
     sıfır kuponlu eğri gün kaydıyla yeniden kuruluyor, yani değişim SIFIR
     DEĞİL: 5 yıllıkta bu satırlarda ortalama |Δ| 14 bp (iş günlerinde 24 bp),
     piyasası olmayan bir günün sahte "hareketi". Türkiye takvimi Fonlama
     hattının EVDS iş günlerinden kurulur ve eğri o takvime indirilir.
  2. Kur kayması kadranı yutuyor: 2023-07 sonrası haftaların ≈%89'unda
     USD/TRY yükseliyor (kontrollü değer kaybı), yani ham kadran payı yalnız
     faizin işaretini ölçer. Ham tablo istenen ölçüdür ve öyle kalır; yanına
     kur değişiminin son 26 haftanın ortalamasından SAPMASIYLA kurulan tablo
     sağlamlık olarak konur ve rejim etiketi bu sapmayla kurulur.
  3. ABD Hazinesi par getirisi New York öğleden sonra kotasyonudur, CNBC
     kurları New York 17:00. Kapanıştan sonra duyurulan bir olayda (2 Nisan
     2025, 16:00 New York) kur günün kapanışında ilk tepkiyi taşır, getiri
     taşımaz; vaka penceresinde adıyla yazılır.
  4. DXY'nin Yahoo barında gövde/aralık sınaması bu arşivden KURULAMAZ:
     arşiv yalnız kapanışı taşır. Yerine tarih sözleşmesi gecikme
     korelasyonuyla sınanır (DXY, eşit ağırlıklı CNBC sepetiyle aynı gün mü,
     bir gün kaymış mı).
  5. 18.12.2023 öncesi Yahoo USD/TRY'de CUMARTESİ BARI YOK: düzeltilmiş günlük
     seride (bar, önceki hafta içi güne yazılır) cuma değeri pazartesi barının
     başından, yani hafta sonu açılışından SONRAKİ fiyattan geliyor — 987 cumanın
     987'si. 10.08.2018 cuma 6,82 yazıyor (TCMB cuma göstergesi 5,94), 19.03.2021
     cuma Ağbal'ın cumartesi görevden alınmasını taşıyor (8,10; TCMB 7,27). Cuma
     kapanışıyla kurulan haftalık değişim hafta sonu haberini yanlış haftaya
     yazar: 2018–2020'de Δ5y ile Δkur korelasyonu cuma örneklemesiyle 0,17,
     perşembe örneklemesiyle 0,39 (DİBS kaymasız; tuzak 6 düzeltilince 0,46 ve
     0,60). Türkiye haftası bu yüzden perşembe kapanışıyla örneklenir; cuma
     örneklemesi duyarlılık ızgarasında durur.
  6. DİBS gösterge eğrisinin ETİKETİ piyasa gününün iki iş günü İLERİSİNDE: seri
     TCMB gösterge kuru gibi valör tarihli ve öğleden önceki sabitlemeden
     geliyor (ölçüm Bölüm 2'de; ör. 22.03.2021 pazartesi çöküşü 5 yıllıkta
     pazartesi etiketinde yok, salı ve çarşamba etiketlerinde). Kaymasız
     haftalık eşleştirmede 2013–2017 korelasyonu 0,41, iki iş günü kaydırınca
     0,65. Haftalık kadran ve rejim etiketi kaydırılmış DİBS'le kurulur.
     HİZA: "gun_sonu" (`ortak_olc.DIBS_KAYMA`, k = 2) — kadranın öbür bacağı
     USD/TRY'nin GÜN SONU kapanışıdır (Londra gece yarısı / İstanbul 18:00);
     tanım ve kanıtı ortak_olc'de, ölçümü Bölüm 2'de.
  7. Güvenli liman rejiminde (VIX yüksek) riskten DÖNÜŞ haftası "prim"
     kadranına düşer (faiz ↑, dolar ↓; ör. 14.10.2011). Rejim kuralı bu
     yüzden R5'i önce sorar; "prim" kadranı R2'ye ancak VIX normalken yazılır.
  8. CNBC ARŞİVİNDE BOZUK KOTASYON (denetim turu, 02.10.2026; temizlik artık
     `ortak_olc.cnbc_kur` / `dolar_sepeti`te, CNBC'yi okuyan her modül için): EUR/USD
     01–03.01.2020'de 1,1774 · 1,1786 · 1,1853 yazıyor (öncesi 1,1210, sonrası
     1,1158–1,1193). Dolar sepetinin 02.01 değişimi −%0,58 çıkıyordu, aynı gün
     DXY +%0,48; 06.01'de sepet +%0,80, DXY −%0,18 — iki gün ters işaretle
     bozuk, 60 günlük kayan korelasyonu ve haftalık kadranı iki ay boyunca
     kirletiyor. Denetim bağımsız bir kaynakla, AYNI SAATTE: CNBC kurlarından
     DXY ağırlıklarıyla kurulan vekilin günlük değişimi Yahoo DXY'ninkinden
     `CNBC_DXY_FARK_ESIGI`nden fazla ayrışıyor ve birkaç gün içinde ters
     işaretle geri dönüyorsa aradaki günler CNBC takviminden çıkar. Eşik ölçülerek
     kondu: 2000–2026'da ayrışmanın en büyük meşru değeri %1,74 (Kasım 2008),
     bozuk blok %3,38 ve %3,54; aradaki %1,0–1,7'lik çiftlerin kaynağı DXY'nin
     kendi tekrarlanan kapanışları (ör. 28–29.05.2009 80,43 · 05–06.02.2015
     94,70), CNBC değil. Çıkan günler `p1a.veri_denetimi`nde adıyla durur.
  9. SEVİYE HEDEFİNDE "SIFIR" KIYASI RASTGELE YÜRÜYÜŞ DEĞİLDİR (inceleme, 03.10.2026).
     Blok regresyonunun hedefi bloğun korelasyonu, yani bir seviye; `ortak_olc`
     `oos_kiyas`ın "sıfır" kıyası burada sıfır korelasyon tahminidir ve kayıt onu
     "rastgele yürüyüş (değişim sıfır)" diye adlandırıyordu. Seviyede rastgele
     yürüyüş bir önceki bloğun korelasyonudur. Korelasyon kalıcı (blokların birinci
     özilintisi 0,59): VIX doğrusunun örneklem dışı karesel hatası sıfır korelasyonun
     0,68 katı, ama bir önceki bloğun 1,25 katı (71 blok, DM t +1,07) — hüküm
     "ölçülü"den "tarif edici"ye döndü. Hüküm koşulsuz ortalama ve seviye rastgele
     yürüyüşüyle (`_oos_onceki_seviye`) kurulur; sıfır korelasyon oranı bilgi olarak
     kalır, adıyla. O fonksiyonun döngüsü `oos_kiyas`ın kopyasıdır; `_oos_parite` aynı
     döngüyü koşulsuz ortalamayla koşup ortak sonuçla kıyaslar, ayrışırsa ölçüm durur
     (arıza enjeksiyonu: ortak DM gecikmesi, ortak ambargo ve kopyada eğitim sızıntısı
     üçü de yakalanıyor).
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import ortak_olc as oo

warnings.filterwarnings("ignore", category=FutureWarning)
try:  # pandas 3 sıralama uyarısı: birleştirmelerde sort açıkça verilir
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

# ───────────────────────────────────────────────────────── sabitler (adlı eşikler)
ILK_GUN = pd.Timestamp("2000-01-01")
KOR_PENCERE = 60                  # iş günü
KOR_ASGARI = 55                   # pencerede en az bu kadar gözlem
VIX_DORTTEBIR_ASGARI = 250        # genişleyen dörttebirlik için asgari geçmiş (gün)
VIX_R5_YUZDELIK = 0.75            # R5: haftalık VIX ≥ genişleyen 75. yüzdelik
VIX_R5_ASGARI_HAFTA = 52          # yüzdeliğin asgari geçmişi (hafta)
DIKLESME_SD = 0.5                 # ayılı dikleşme: Δeğim > 0,5 × kayan σ(Δeğim)
KUR_SAPMA_SD = 0.5                # "prim" için para kaybı: kur sapması > 0,5 × kayan σ(kur sapması)
DIKLESME_SD_PENCERE = 52          # σ'nın kayan penceresi (hafta, bir önceki haftaya kadar)
DIKLESME_SD_ASGARI = 26
KUR_KAYMA_PENCERE = 26            # kur sapması: son 26 haftanın ortalama değişimi (bir önceki haftaya kadar)
BLOK_ILK_PENCERE = 40             # blok regresyonunun örneklem dışı ilk eğitim penceresi (blok)
KIYAS_SIFIR_KOR = "sıfır korelasyon"                                  # seviye hedefinde sıfır tahmini
KIYAS_RW_SEVIYE = "rastgele yürüyüş (bir önceki bloğun korelasyonu)"  # seviye hedefinde rastgele yürüyüş
YONETILEN = oo.YONETILEN                    # tek tanım ortak_olc'de
# Türkiye haftası PERŞEMBE kapanışıyla örneklenir (perşembe tatilse haftanın ondan
# önceki son iş günü): 18.12.2023 öncesi Yahoo USD/TRY serisinde cumartesi barı yok
# ve cuma değeri PAZARTESİ barının başından (hafta sonu açılışından sonra) geliyor.
TR_ORNEK_SON_GUN = 3              # 0 pazartesi … 3 perşembe, 4 cuma
# DİBS gösterge eğrisinin hizası `ortak_olc.DIBS_KAYMA`dan (tek tanım): kadran
# USD/TRY gün sonu kapanışıyla kurulduğu için "gun_sonu" — D gününün piyasasına
# DİBS'in D+2 iş günü etiketli değeri yazılır.
DIBS_HIZA = "gun_sonu"

DONEMLER_TR = [
    ("2013-2017", "2013-01-01", "2017-12-31"),
    ("2018-2020", "2018-01-01", "2020-12-31"),
    (f"2021-01_{oo.YON_ONCESI_AY}", "2021-01-01", oo.YON_ONCESI_SON),
    (f"yonetilen_kur_{oo.YON_AY[0]}_{oo.YON_AY[1]}", oo.YON_ILK, oo.YON_SON),
    (f"{oo.YON_SONRASI_AY}_2026-09", oo.YON_SONRASI_ILK, "2026-09-30"),
]
DONEMLER_ABD_EK = [("2000-2012", "2000-01-01", "2012-12-31"), ("tum_2000-2026", "2000-01-01", "2026-09-30")]

VAKALAR = {
    "guvenli_liman_2011": ("2011-08-01", "2011-12-30"),
    "kurumsal_risk_2025": ("2025-04-02", "2025-04-30"),
}

KAYNAK_ABD = ["abd_hazine_gunluk", "cnbc_kur_gunluk", "yahoo_dxy_vix_gunluk"]
KAYNAK_TR = ["dibs_egri_gunluk", "usdtry_yahoo_gunluk", "fonlama_gunluk (yalnız iş günü takvimi)"]


# ───────────────────────────────────────────────────────── okuyucular
def _hafta_ici(df: pd.DataFrame | pd.Series):
    return df[df.index.dayofweek < 5]


@lru_cache(maxsize=1)
def _abd_gunluk() -> pd.DataFrame:
    """ABD ortak gün çerçevesi (`ortak_olc.abd_gunluk`: us2, us10, dolar sepeti,
    dxy, vix; CNBC bozuk kotasyon günleri çıkarılmış), 2000 sonrası."""
    df = oo.abd_gunluk()
    return df[df.index >= ILK_GUN - pd.Timedelta(days=10)]


@lru_cache(maxsize=4)
def _tr_gunluk(hiza: str = "ham") -> pd.DataFrame:
    """Türkiye ORTAK gün çerçevesi: n3a, n2y, n5y (%), USD/TRY (Yahoo); dört
    sütunun birlikte bulunduğu Türkiye iş günleri (`ortak_olc.tr_gunluk`). "ham"
    etiket Bölüm 2'nin hiza kapısı ve duyarlılık ızgarası içindir."""
    return oo.tr_gunluk(hiza, ("n3a", "n2y", "n5y")).dropna()


def _haftalik(df: pd.DataFrame, son_gun: int = 4) -> pd.DataFrame:
    """Cuma etiketli hafta; haftanın `son_gun`e kadarki son ortak günü (o gün
    tatilse bir önceki iş günü). `_gun` örneklenen gerçek günü taşır."""
    df = df[df.index.dayofweek <= son_gun]
    w = df.resample("W-FRI").last()
    gun = df.index.to_series().resample("W-FRI").last()
    w["_gun"] = gun
    # çıpa haftası kısmidir (28–30.09.2026: cuma etiketi çıpanın ilerisinde);
    # kadran tabloları onu almaz, rejim etiketi adıyla işaretler
    w["_kismi"] = w.index > oo.CIPA_GUN
    return w.dropna(subset=[c for c in df.columns if c not in ("vix", "dxy")])


@lru_cache(maxsize=1)
def _vix_gunluk() -> pd.Series:
    return oo.oku("yahoo_dxy_vix_gunluk")["vix"].dropna()


# ───────────────────────────────────────────────────────── kadran
KADRAN_ADI_DM, KADRAN_ADI_EM = oo.KADRAN_ADI_DM, oo.KADRAN_ADI_EM
_kadran = oo.kadran                         # tek tanım ortak_olc'de


def _kadran_tablosu(dfaiz: pd.Series, dpara_deger: pd.Series, dordu: str, gun: pd.Series | None = None) -> dict:
    d = pd.concat([dfaiz.rename("y"), dpara_deger.rename("p")], axis=1).dropna()
    gunler = pd.DatetimeIndex(gun.reindex(d.index)) if gun is not None else d.index
    if len(d) < 5:
        return {"n": int(len(d)), "durum": "kurulmadi", "sebep": "dönemde yeterli hafta yok"}
    k = _kadran(d["y"], d["p"], dordu)
    sifir = int((k == "sifir").sum())
    gecerli = k[k != "sifir"]
    pay = {ad: float((gecerli == ad).mean()) for ad in ("politika", "prim", "gevseme", dordu)}
    sayi = {ad: int((gecerli == ad).sum()) for ad in ("politika", "prim", "gevseme", dordu)}
    m = len(gecerli)
    return {
        "n": int(len(d)), "n_sifir_disi": int(m), "sifir": sifir,
        "ilk": str(gunler.min().date()), "son": str(gunler.max().date()),
        "pay": pay, "sayi": sayi,
        "pay_se": {ad: float(np.sqrt(p * (1 - p) / m)) if m else None for ad, p in pay.items()},
        # C (risk primi) imzası: faiz ile para DEĞERİ TERS yönde — prim (faiz ↑, para ↓) ve
        # güvenli liman / prim düşüşü (faiz ↓, para ↑). B (faiz farkı) imzası: aynı yönde —
        # politika (faiz ↑, para ↑) ve gevşeme (faiz ↓, para ↓).
        "c_payi": float(pay["prim"] + pay[dordu]),
        "b_payi": float(pay["politika"] + pay["gevseme"]),
        "korelasyon_faiz_para_kaybi": float(np.corrcoef(d["y"], -d["p"])[0, 1]),
        "ort_faiz_bp": float(d["y"].mean()), "ort_para_deger_yuzde": float(d["p"].mean()),
        "para_deger_kaybi_haftasi_payi": float((d["p"] < 0).mean()),
    }


def _gun_dilimi(df: pd.DataFrame, a, b) -> pd.DataFrame:
    """Haftalık çerçeveyi ÖRNEKLENEN GERÇEK GÜNE göre keser (cuma etiketine göre
    değil): 01.01.2021 cuma etiketli haftanın örnek günü 31.12.2020'dir ve
    değişimi tamamen 2020'ye aittir; etiketle kesilince 2021 dönemine düşüyordu."""
    g = pd.DatetimeIndex(df["_gun"])
    return df[(g >= pd.Timestamp(a)) & (g <= pd.Timestamp(b))]


def _kur_sapma(dkur: pd.Series) -> pd.Series:
    """Haftalık kur değişiminin son 26 haftalık ortalamasından sapması (o hafta hariç)."""
    ort = dkur.rolling(KUR_KAYMA_PENCERE, min_periods=13).mean().shift(1)
    return dkur - ort


# ───────────────────────────────────────────────────────── p1a
def _vix_esikleri(gunler: pd.DatetimeIndex) -> pd.DataFrame:
    """VIX 60 günlük ortalamasının GENİŞLEYEN pencereli dörttebirlikleri (o güne
    kadarki geçmiş, o gün hariç). VIX'in kendi takviminde 1990'dan kurulur,
    sonra ortak günlere taşınır."""
    v = _vix_gunluk()
    v60 = v.rolling(KOR_PENCERE, min_periods=KOR_ASGARI).mean().dropna()
    e = pd.DataFrame({f"q{int(q * 100)}": v60.expanding(VIX_DORTTEBIR_ASGARI).quantile(q).shift(1)
                      for q in (0.25, 0.50, 0.75)})
    return e.reindex(gunler, method="ffill")


def _dortte_bir(x: pd.Series, e: pd.DataFrame) -> pd.Series:
    q = pd.Series(np.nan, index=x.index)
    ok = x.notna() & e["q25"].notna()
    q[ok & (x <= e["q25"])] = 1
    q[ok & (x > e["q25"]) & (x <= e["q50"])] = 2
    q[ok & (x > e["q50"]) & (x <= e["q75"])] = 3
    q[ok & (x > e["q75"])] = 4
    return q


@lru_cache(maxsize=1)
def _p1a_seri() -> pd.DataFrame:
    df = _abd_gunluk()
    dl = df.diff()
    out = pd.DataFrame({
        "d10_bp": dl["us10"] * 100.0,
        "d2_bp": dl["us2"] * 100.0,
        "ddolar_yuzde": dl["sepet"] * 100.0,
        "ddxy_yuzde": dl["dxy"] * 100.0,
        "vix": df["vix"],
        "dvix": df["vix"].diff(),
    }).iloc[1:]
    out = out[out.index >= ILK_GUN]
    out["kor"] = out["d10_bp"].rolling(KOR_PENCERE, min_periods=KOR_ASGARI).corr(out["ddolar_yuzde"])
    out["kor_dxy"] = out["d10_bp"].rolling(KOR_PENCERE, min_periods=KOR_ASGARI).corr(out["ddxy_yuzde"])
    out["vix60"] = out["vix"].rolling(KOR_PENCERE, min_periods=KOR_ASGARI).mean()
    e = _vix_esikleri(out.index)
    out = out.join(e)
    out["vix_q"] = _dortte_bir(out["vix60"], e)
    return out


def _pencere_ozeti(o: pd.DataFrame, ilk: str, son: str) -> dict:
    w = o.loc[ilk:son].dropna(subset=["d10_bp", "ddolar_yuzde"])
    ab = _abd_gunluk()
    # birikimli değişim: pencereden önceki son ortak günden pencerenin son gününe
    once = ab.index[ab.index < pd.Timestamp(ilk)].max()
    sonu = w.index.max()
    bir10 = (ab.loc[sonu, "us10"] - ab.loc[once, "us10"]) * 100
    bir2 = (ab.loc[sonu, "us2"] - ab.loc[once, "us2"]) * 100
    birdol = (ab.loc[sonu, "sepet"] - ab.loc[once, "sepet"]) * 100
    kad = oo.kadran(float(bir10), float(birdol), "guvenli_liman")
    return {
        "n": int(len(w)), "ilk": str(w.index.min().date()), "son": str(sonu.date()),
        "kor_d10_ddolar": float(w["d10_bp"].corr(w["ddolar_yuzde"])),
        "kor_d10_dvix": float(w["d10_bp"].corr(w["dvix"])),
        "kor_ddolar_dvix": float(w["ddolar_yuzde"].corr(w["dvix"])),
        "vix_ort": float(w["vix"].mean()), "vix_azami": float(w["vix"].max()),
        "birikimli_d10_bp": float(bir10), "birikimli_d2_bp": float(bir2),
        "birikimli_egim_bp": float(bir10 - bir2), "birikimli_dolar_yuzde": float(birdol),
        "birikimli_kadran": kad, "kiyas_gunu": str(once.date()),
        "kayan_kor_pencere_sonu": float(o.loc[:sonu, "kor"].dropna().iloc[-1]),
    }


def _oos_onceki_seviye(y: pd.Series, x: pd.Series, ilk_pencere: int, ambargo: int = 1,
                       kiyas: str = "onceki") -> dict:
    """Seviye hedefinde rastgele yürüyüş kıyası (tuzak 9): `ortak_olc.oos_kiyas` ile
    AYNI genişleyen pencere, aynı model tahmini (y_t = a + b·x_t, x_t bilinen, eğitim
    hedefi t anında gerçekleşmiş satırlarla) ve aynı Diebold–Mariano t'si; yalnız saf
    kıyasın tahmini sıfır ya da ortalama değil, hedefin `ambargo` dönem önceki değeri
    (ambargo = 1: bir önceki blok). Oran < 1 ve eksi t modelin lehine.
    `kiyas="ortalama"` yalnız `_oos_parite` içindir: aynı döngü koşulsuz ortalamayla
    koşulur ve `ortak_olc.oos_kiyas`ın sonucuyla birebir tutmalıdır."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1, sort=True).dropna()
    e_m, e_k = [], []
    for t in range(ilk_pencere, len(d)):
        egit = d.iloc[: t - ambargo + 1]
        if len(egit) < oo.OOS_ASGARI or t - ambargo < 0:
            continue
        X = np.column_stack([np.ones(len(egit)), egit["x"].values])
        b = np.linalg.lstsq(X, egit["y"].values, rcond=None)[0]
        tah = b[0] + b[1] * d["x"].iloc[t]
        kiy = d["y"].iloc[t - ambargo] if kiyas == "onceki" else egit["y"].mean()
        e_m.append((d["y"].iloc[t] - tah) ** 2)
        e_k.append((d["y"].iloc[t] - kiy) ** 2)
    if len(e_m) < oo.OOS_ASGARI:
        return oo.kurulmadi("örneklem dışı sınama için en az on tahmin gerekir", n=int(len(e_m)),
                            kiyas=KIYAS_RW_SEVIYE)
    e_m, e_k = np.array(e_m), np.array(e_k)
    fark = e_m - e_k
    gecikme = oo.otomatik_gecikme(len(fark))
    if ambargo > 1:
        gecikme = max(int(gecikme), int(ambargo))
    dm = oo.hac(fark, np.zeros((len(fark), 0)), gecikme=gecikme, sabit=True)
    return {"n": int(len(e_m)), "mse_oran": oo._f(e_m.mean() / e_k.mean()) if e_k.mean() else None,
            "dm_t": oo._f((dm.get("t") or [None])[0]), "kiyas": KIYAS_RW_SEVIYE,
            "ilk": oo._iso(d.index[ilk_pencere]), "ambargo": int(ambargo), "dm_gecikme": int(gecikme),
            "model_ortalama_karesel_hata": oo._f(e_m.mean()),
            "kiyas_ortalama_karesel_hata": oo._f(e_k.mean())}


def _oos_parite(y: pd.Series, x: pd.Series, ilk_pencere: int, ortak: dict) -> None:
    """`_oos_onceki_seviye`nin döngüsü `ortak_olc.oos_kiyas`ın KOPYASIDIR (seviye kıyası
    oraya eklenmedi); iki kopya bir gün sessizce ayrışır ve rastgele yürüyüş oranı öbür
    iki orandan başka bir pencereyle, başka bir DM gecikmesiyle ölçülmüş olur. Kilit:
    aynı döngü koşulsuz ortalamayla koşulur ve `ortak` (`regresyon`un "oos_ortalama"
    kaydı) ile alan alan karşılaştırılır; tutmazsa ölçüm DURUR."""
    k = _oos_onceki_seviye(y, x, ilk_pencere, kiyas="ortalama")
    if k.get("durum") == "kurulmadi" and ortak.get("durum") == "kurulmadi" and k.get("n") == ortak.get("n"):
        return
    ayrisan = [a for a in ("n", "ilk", "ambargo", "dm_gecikme") if k.get(a) != ortak.get(a)]
    ayrisan += [a for a in ("mse_oran", "dm_t")
                if k.get(a) is None or ortak.get(a) is None or abs(k[a] - ortak[a]) > 1e-9]
    if ayrisan:
        raise RuntimeError("olcum_b01._oos_onceki_seviye ortak_olc.oos_kiyas'tan ayrıştı "
                           f"({', '.join(ayrisan)}): kopya döngü ortak tanıma göre güncellenmeli")


def p1a() -> dict:
    o = _p1a_seri()
    k = o.dropna(subset=["kor"])
    imin, imax = k["kor"].idxmin(), k["kor"].idxmax()
    ozet = {
        "n_gun": int(len(k)), "ilk": str(k.index.min().date()), "son": str(k.index.max().date()),
        "kor_ort": float(k["kor"].mean()), "kor_medyan": float(k["kor"].median()),
        "pozitif_pay": float((k["kor"] > 0).mean()), "negatif_pay": float((k["kor"] < 0).mean()),
        "kor_asgari": float(k["kor"].min()), "kor_asgari_tarih": str(imin.date()),
        "kor_azami": float(k["kor"].max()), "kor_azami_tarih": str(imax.date()),
        "bagimsiz_pencere_sayisi": int(len(k) // KOR_PENCERE),
        "gunluk_sd_d10_bp": float(o["d10_bp"].std()), "gunluk_sd_ddolar_yuzde": float(o["ddolar_yuzde"].std()),
    }
    # yıllık ortalama korelasyon (figür metni için)
    yillik = k["kor"].groupby(k.index.year).mean()
    ozet["yillik_ort_kor"] = {str(y): float(v) for y, v in yillik.items()}

    # dörttebirlik dağılımı (60 günlük VIX ortalaması, genişleyen eşikler)
    q = k.dropna(subset=["vix_q"])
    dort = {}
    for i in (1, 2, 3, 4):
        z = q[q["vix_q"] == i]
        dort[f"q{i}"] = {
            "n_gun": int(len(z)), "bagimsiz_pencere": float(len(z) / KOR_PENCERE),
            "pozitif_pay": float((z["kor"] > 0).mean()) if len(z) else None,
            "negatif_pay": float((z["kor"] < 0).mean()) if len(z) else None,
            "kor_ort": float(z["kor"].mean()) if len(z) else None,
            "kor_medyan": float(z["kor"].median()) if len(z) else None,
            "vix60_ort": float(z["vix60"].mean()) if len(z) else None,
        }
    son_esik = q.iloc[-1]
    dort_meta = {"ilk": str(q.index.min().date()), "son": str(q.index.max().date()),
                 "son_esikler": {"q25": float(son_esik["q25"]), "q50": float(son_esik["q50"]),
                                 "q75": float(son_esik["q75"])},
                 "yontem": "Her günün 60 günlük VIX ortalaması, 1990'dan o güne kadar (o gün hariç) "
                           "biriken 60 günlük ortalamaların dörttebirlikleriyle sınıflandırıldı; "
                           "korelasyonun işareti her sınıfta sayıldı."}

    # koşullu anlık korelasyon: günlük VIX'in bir önceki günkü genişleyen dörttebirliğine göre
    v = _vix_gunluk()
    eg = pd.DataFrame({f"q{int(qq * 100)}": v.expanding(VIX_DORTTEBIR_ASGARI).quantile(qq).shift(1)
                       for qq in (0.25, 0.5, 0.75)}).reindex(o.index, method="ffill")
    vdun = v.shift(1).reindex(o.index, method="ffill")
    gq = _dortte_bir(vdun, eg)
    kosullu = {}
    for i in (1, 2, 3, 4):
        z = o[gq == i].dropna(subset=["d10_bp", "ddolar_yuzde"])
        kosullu[f"q{i}"] = {"n_gun": int(len(z)), "kor": float(z["d10_bp"].corr(z["ddolar_yuzde"]))}

    # örtüşmeyen 60 günlük bloklar: korelasyon ~ VIX ortalaması
    o2 = o.dropna(subset=["d10_bp", "ddolar_yuzde", "vix"])
    blok_no = np.arange(len(o2)) // KOR_PENCERE
    bl = o2.groupby(blok_no).apply(lambda g: pd.Series({
        "kor": g["d10_bp"].corr(g["ddolar_yuzde"]), "vix": g["vix"].mean(), "n": len(g),
        "tarih": g.index.max()}))
    bl = bl[bl["n"] >= KOR_ASGARI]
    bl.index = pd.DatetimeIndex(bl["tarih"])
    yk, xv = bl["kor"].astype(float), bl["vix"].astype(float)
    reg = oo.regresyon(yk, xv, ilk_pencere=BLOK_ILK_PENCERE)
    oos = reg["oos_ortalama"]
    # Hedef bir SEVİYE (bloğun korelasyonu): rastgele yürüyüş bir önceki bloğun değeridir
    # (tuzak 9). ortak_olc'nin "sıfır" kıyası burada sıfır korelasyon tahminidir; bilgi
    # olarak kalır, hükme girmez. Kopya döngünün ortak tanımla aynı kaldığı önce sınanır.
    _oos_parite(yk, xv, BLOK_ILK_PENCERE, oos)
    rw = _oos_onceki_seviye(yk, xv, ilk_pencere=BLOK_ILK_PENCERE)
    sifir = {**reg["oos"], "kiyas": KIYAS_SIFIR_KOR}
    hk = oo.hukum(reg["t"], [oos.get("mse_oran"), rw.get("mse_oran")])
    blok = {
        "n": int(reg["n"]), "ilk": str(bl.index.min().date()), "son": str(bl.index.max().date()),
        "sabit": reg["sabit"], "egim_vix_basina": reg["egim"], "se_egim": reg["se"], "t_egim": reg["t"],
        "r2": reg["r2"], "gecikme": reg["gecikme"],
        "oos_mse_oran": oos.get("mse_oran"), "oos_dm_t": oos.get("dm_t"), "oos_n": oos.get("n"),
        "oos_kiyas": oos.get("kiyas"),
        "oos_rastgele_yuruyus": rw,
        "oos_sifir": sifir,
        "hukum": hk,
        "hukum_kiyaslari": [oos.get("kiyas"), rw.get("kiyas")],
        "oos_dm_anlamli": bool(oos.get("dm_t") is not None and abs(oos["dm_t"]) >= 2),
        "oos_rw_dm_anlamli": bool(rw.get("dm_t") is not None and abs(rw["dm_t"]) >= 2),
        "blok_kor_ozilinti_1": float(yk.autocorr(1)),
        "yontem": "Örtüşmeyen 60 iş günlük blokların her birinde korelasyon, aynı bloğun VIX "
                  "ortalamasına regrese edildi; standart hata Newey–West. Örneklem dışı kıyas "
                  "genişleyen pencerede iki saf ölçüte karşı: koşulsuz ortalama ve rastgele "
                  "yürüyüş — hedef bir seviye olduğu için rastgele yürüyüşün tahmini bir önceki "
                  "bloğun korelasyonudur. Hüküm ikisini de ister; sıfır korelasyon kıyası bilgi "
                  "olarak verilir, hükme girmez.",
    }

    vakalar = {ad: _pencere_ozeti(o, a, b) for ad, (a, b) in VAKALAR.items()}
    # 2 Nisan 2025 duyurusu (New York 16:00) Hazine kotasyonundan sonra, kur kapanışından (17:00) önce
    # geldi: ilk tepki kurda 2 Nisan, getiride 3 Nisan gözlemindedir. İki gün tek gözlemde birleştirilir
    # (yalnız 2 Nisan'ı atmak kurun ilk tepkisini atıp getirininkini tutardı).
    w25 = o.loc[VAKALAR["kurumsal_risk_2025"][0]:VAKALAR["kurumsal_risk_2025"][1], ["d10_bp", "ddolar_yuzde"]].dropna().copy()
    t2, t3 = pd.Timestamp("2025-04-02"), pd.Timestamp("2025-04-03")
    if t2 in w25.index and t3 in w25.index:
        w25.loc[t3] = w25.loc[t2] + w25.loc[t3]
        w25 = w25.drop(index=t2)
        vakalar["kurumsal_risk_2025"]["kor_d10_ddolar_2_3nisan_birlesik"] = float(w25["d10_bp"].corr(w25["ddolar_yuzde"]))
        vakalar["kurumsal_risk_2025"]["n_2_3nisan_birlesik"] = int(len(w25))
    vakalar["kurumsal_risk_2025"]["saat_notu"] = (
        "2 Nisan 2025 gümrük duyurusu New York 16:00'da geldi; o günün kur kapanışı (17:00) ilk tepkiyi "
        "taşır, Hazine getirisi öğleden sonraki kotasyon olduğu için ilk tepkiyi 3 Nisan'da taşır; "
        "sağlamlıkta iki gün tek gözlem sayıldı.")

    # DXY tarih sözleşmesi sınaması (gövde/aralık kurulamıyor)
    gec = {}
    for ad, L in (("dxy_onceki_gun", 1), ("dxy_ayni_gun", 0), ("dxy_ertesi_gun", -1)):
        j = pd.concat([o["ddolar_yuzde"], o["ddxy_yuzde"].shift(L)], axis=1, sort=True).dropna()
        gec[ad] = float(j.corr().iloc[0, 1])
    kk = k.dropna(subset=["kor_dxy"])
    dxy = {
        "govde_aralik": {"durum": "kurulmadi",
                         "sebep": "arşiv DXY'nin yalnız kapanışını taşıyor; açılış, en yüksek ve en düşük yok"},
        "gecikme_korelasyonu": gec, "n": int(len(o.dropna(subset=["ddolar_yuzde", "ddxy_yuzde"]))),
        "kayan_kor_isaret_uyumu": float((np.sign(kk["kor"]) == np.sign(kk["kor_dxy"])).mean()),
        "kayan_kor_fark_ort": float((kk["kor_dxy"] - kk["kor"]).mean()),
        "hukum": ("DXY kapanışı sepetle aynı güne oturuyor; bir günlük kayma yok"
                  if gec["dxy_ayni_gun"] > max(gec["dxy_onceki_gun"], gec["dxy_ertesi_gun"]) + 0.5
                  else "DXY tarih sözleşmesi sepetle ayrışıyor"),
        "yontem": "DXY'nin günlük log değişimi, eşit ağırlıklı CNBC dolar sepetinin değişimiyle aynı "
                  "günde ve bir gün kaydırılarak karşılaştırıldı; birincil dolar ölçüsü sepettir.",
    }

    dxy["dxy_sifir_degisim_gunu"] = int((_abd_gunluk()["dxy"].diff() == 0).sum())
    dxy["dxy_sifir_degisim_notu"] = ("DXY'nin Yahoo kapanışı bazı günlerde bir önceki günü birebir tekrarlar "
                                     "(iki haneli kotasyonda kısmen doğal); CNBC sepetiyle bir günlük ayrışmaların "
                                     "kaynağı çoğunlukla budur.")
    return {
        "ozet": ozet, "dortte_bir": dort, "dortte_bir_meta": dort_meta, "kosullu_anlik_kor": kosullu,
        "blok_regresyon": blok, "vakalar": vakalar, "dxy_sinama": dxy,
        "veri_denetimi": oo.cnbc_denetimi(),
        "n": ozet["n_gun"], "ilk": ozet["ilk"], "son": ozet["son"],
        "yontem": "ABD 10 yıllık getirisinin günlük değişimi (baz puan) ile eşit ağırlıklı altı G10 "
                  "kurundan kurulan dolar sepetinin günlük log değişimi (yüzde, artış doların değer "
                  "kazancı) arasında 60 iş günlük kayan korelasyon; VIX aynı pencerenin ortalaması.",
        "saat": "ABD Hazinesi par getirisi New York öğleden sonra kotasyonu; CNBC kurları New York 17:00; "
                "VIX New York kapanışı.",
        "kaynak": KAYNAK_ABD,
        "isaret": "Sepet: EUR, GBP, AUD karşısında işaret çevrildi (XXX/USD), CHF, JPY, CAD olduğu gibi "
                  "(USD/XXX); pozitif korelasyon = faiz artarken dolar değer kazanıyor.",
    }


# ───────────────────────────────────────────────────────── p1b
@lru_cache(maxsize=4)
def _tr_haftalik(son_gun: int = TR_ORNEK_SON_GUN, hiza: str = DIBS_HIZA) -> pd.DataFrame:
    w = _haftalik(_tr_gunluk(hiza), son_gun)
    d = pd.DataFrame({
        "d5_bp": w["n5y"].diff() * 100.0,
        "d2_bp": w["n2y"].diff() * 100.0,
        "dkur_yuzde": np.log(w["usdtry"]).diff() * 100.0,
        "_gun": w["_gun"], "_kismi": w["_kismi"],
    }).iloc[1:]
    d["degim_bp"] = d["d5_bp"] - d["d2_bp"]
    d["kur_sapma_yuzde"] = _kur_sapma(d["dkur_yuzde"])
    v = _vix_gunluk()
    d["vix"] = v.reindex(pd.DatetimeIndex(d["_gun"]), method="ffill").values
    return d


def _cuma_tuzagi() -> dict:
    """18.12.2023 öncesi cuma değerlerinin hangi Yahoo barından geldiği (sayım
    ortak_olc.usdtry künyesinde; tek tanım)."""
    s, k = oo.usdtry()
    gecis = pd.Timestamp(k["gecis"])
    cuma = s[(s.index.dayofweek == 4) & (s.index < gecis)]
    pzt = k["cuma_pazartesi_barindan"]
    t = oo.usdtry_tcmb()
    ornek = {g: {"yahoo_usdtry": float(s.get(pd.Timestamp(g), np.nan)),
                 "tcmb_gosterge": float(t.get(pd.Timestamp(g), np.nan))}
             for g in ("2018-08-10", "2021-03-19")}
    return {"cuma_gunu": int(len(cuma)), "pazartesi_barindan": int(pzt),
            "pay": float(pzt / len(cuma)) if len(cuma) else None,
            "ilk": str(cuma.index.min().date()), "son": str(cuma.index.max().date()),
            "ornek": ornek,
            "aciklama": "Arşivde 18.12.2023 öncesi cumartesi barı yok; düzeltilmiş günlük seride cuma değeri "
                        "pazartesi barının başındaki (hafta sonu açılışından sonraki) fiyattır ve hafta sonu "
                        "haberini cumaya yazar. Haftalık örnekleme bu yüzden perşembe kapanışıyla yapıldı."}


@lru_cache(maxsize=1)
def _abd_haftalik() -> pd.DataFrame:
    w = _haftalik(_abd_gunluk()[["us2", "us10", "sepet"]])
    d = pd.DataFrame({
        "d10_bp": w["us10"].diff() * 100.0,
        "d2_bp": w["us2"].diff() * 100.0,
        "ddolar_yuzde": w["sepet"].diff() * 100.0,
        "_gun": w["_gun"], "_kismi": w["_kismi"],
    }).iloc[1:]
    d = d[d.index >= ILK_GUN]
    d["degim_bp"] = d["d10_bp"] - d["d2_bp"]
    d["dolar_sapma_yuzde"] = _kur_sapma(d["ddolar_yuzde"])
    return d


def _tarih_tr(t) -> str:
    return pd.Timestamp(t).strftime("%d.%m.%Y")


def _kismi_hafta_notu() -> str:
    """Çıpa haftasının nereye kadar uzandığı VERİDEN: Türkiye'nin son örnek günü,
    DİBS'in iki iş günü sonraki etiketi gerektiği için çıpadan iki iş günü önce biter."""
    tr, ab = _tr_haftalik(), _abd_haftalik()
    parca = []
    for ad, h in (("Türkiye'de", tr), ("ABD'de", ab)):
        tam = h[~h["_kismi"].astype(bool)]
        kis = h[h["_kismi"].astype(bool)]
        p = f"{ad} son tam hafta {_tarih_tr(tam['_gun'].iloc[-1])}"
        if len(kis):
            p += f", yarım hafta {_tarih_tr(kis['_gun'].iloc[-1])} günüyle kesiliyor"
        parca.append(p)
    return ("Çıpa haftası yarım kaldığı için tablolara girmedi; " + "; ".join(parca) +
            ". Türkiye'nin yarım haftası çıpa gününe ulaşmaz, çünkü 5 yıllık getiri iki iş günü sonraki "
            "etiketten okunur.")


def p1b() -> dict:
    tr = _tr_haftalik()
    ab = _abd_haftalik()
    tr, ab = tr[~tr["_kismi"].astype(bool)], ab[~ab["_kismi"].astype(bool)]
    tablo_tr, tablo_tr_sapma, tablo_abd, tablo_abd_sapma = {}, {}, {}, {}
    for ad, a, b in DONEMLER_TR:
        z = _gun_dilimi(tr, a, b)
        # Türkiye: para değeri = −ΔUSD/TRY
        tablo_tr[ad] = _kadran_tablosu(z["d5_bp"], -z["dkur_yuzde"], "prim_dusus", z["_gun"])
        tablo_tr_sapma[ad] = _kadran_tablosu(z["d5_bp"], -z["kur_sapma_yuzde"], "prim_dusus", z["_gun"])
        y = _gun_dilimi(ab, a, b)
        tablo_abd[ad] = _kadran_tablosu(y["d10_bp"], y["ddolar_yuzde"], "guvenli_liman", y["_gun"])
        tablo_abd_sapma[ad] = _kadran_tablosu(y["d10_bp"], y["dolar_sapma_yuzde"], "guvenli_liman", y["_gun"])
    izgara = {}
    for gun_ad, gun in (("persembe", 3), ("cuma", 4)):
        for hz in ("ham", DIBS_HIZA):
            kay = oo.DIBS_KAYMA[hz]
            h = _tr_haftalik(gun, hz)
            h = h[~h["_kismi"].astype(bool)]
            izgara[f"{gun_ad}_dibs_kayma_{kay}"] = {}
            for ad, a, b in DONEMLER_TR:
                hz = _gun_dilimi(h, a, b)
                izgara[f"{gun_ad}_dibs_kayma_{kay}"][ad] = {
                    k_: v_ for k_, v_ in _kadran_tablosu(hz["d5_bp"], -hz["dkur_yuzde"], "prim_dusus", hz["_gun"]).items()
                    if k_ in ("n", "korelasyon_faiz_para_kaybi", "c_payi", "pay")}
    tablo_tr["tum_2013-2026"] = _kadran_tablosu(tr["d5_bp"], -tr["dkur_yuzde"], "prim_dusus", tr["_gun"])
    gtr = pd.DatetimeIndex(tr["_gun"])
    tum_dis = tr[~oo.yonetilen_mi(gtr)]
    tablo_tr["tum_yonetilen_haric"] = _kadran_tablosu(tum_dis["d5_bp"], -tum_dis["dkur_yuzde"], "prim_dusus", tum_dis["_gun"])
    for ad, a, b in DONEMLER_ABD_EK:
        y = _gun_dilimi(ab, a, b)
        tablo_abd[ad] = _kadran_tablosu(y["d10_bp"], y["ddolar_yuzde"], "guvenli_liman", y["_gun"])
        tablo_abd_sapma[ad] = _kadran_tablosu(y["d10_bp"], y["dolar_sapma_yuzde"], "guvenli_liman", y["_gun"])

    # karşılaştırma: aynı dönemde "aynı yön" (C) payı TR − ABD
    kars = {}
    for ad, _, _ in DONEMLER_TR:
        t, u = tablo_tr[ad], tablo_abd[ad]
        if "pay" in t and "pay" in u:
            kars[ad] = {"tr_c_payi": t["c_payi"], "abd_c_payi": u["c_payi"],
                        "fark_puan": 100.0 * (t["c_payi"] - u["c_payi"]),
                        "tr_prim": t["pay"]["prim"], "abd_prim": u["pay"]["prim"],
                        "tr_politika": t["pay"]["politika"], "abd_politika": u["pay"]["politika"]}
    gun_persembe_disi = int((pd.DatetimeIndex(tr["_gun"]).dayofweek != TR_ORNEK_SON_GUN).sum())
    return {
        "turkiye": tablo_tr, "turkiye_kur_sapmasi": tablo_tr_sapma,
        "turkiye_duyarlilik": izgara, "cuma_tuzagi": _cuma_tuzagi(),
        "dibs_etiket_oncu_is_gunu": oo.DIBS_KAYMA[DIBS_HIZA], "dibs_hiza": DIBS_HIZA,
        "abd": tablo_abd, "abd_dolar_sapmasi": tablo_abd_sapma, "karsilastirma": kars,
        "kadran_adlari_tr": KADRAN_ADI_EM, "kadran_adlari_abd": KADRAN_ADI_DM,
        "n": int(len(tr)), "ilk": str(pd.Timestamp(tr["_gun"].iloc[0]).date()),
        "son": str(pd.Timestamp(tr["_gun"].iloc[-1]).date()),
        "n_abd": int(len(ab)), "ilk_abd": str(pd.Timestamp(ab["_gun"].iloc[0]).date()),
        "son_abd": str(pd.Timestamp(ab["_gun"].iloc[-1]).date()),
        "persembe_disi_ornek_gunu": gun_persembe_disi,
        "kismi_hafta_notu": _kismi_hafta_notu(),
        "yontem": "Türkiye'de perşembe kapanışından perşembe kapanışına USD/TRY'nin haftalık log değişimi "
                  "(yüzde) ile aynı piyasa gününe denk gelen 5 yıllık DİBS getirisinin haftalık değişimi (baz "
                  "puan; gösterge eğrisinin iki iş günü sonraki etiketi) dört kadrana ayrıldı; ABD'de cuma "
                  "kapanışıyla 10 yıllık getiri ve eşit ağırlıklı dolar sepeti aynı kuralla.",
        "sapma_yontemi": "Sağlamlık tablosunda kur değişimi, son 26 haftanın ortalama değişiminden (o "
                         "hafta hariç) sapma olarak alındı; kontrollü değer kaybı dönemlerinde ham kadran "
                         "kur yönünü neredeyse her hafta aynı gösterdiği için.",
        "saat": "USD/TRY 18.12.2023'ten İstanbul 18:00, öncesinde Londra gece yarısı kapanışı; DİBS gösterge "
                "değeri valör tarihli ve öğleden önce sabitlendiği için iki iş günü sonraki etiketinden alındı "
                "(perşembe piyasası → pazartesi etiketi).",
        "yonetilen_kur_notu": f"{oo.YON_AY[0]}…{oo.YON_AY[1]} kur koruma ve kontrollü kur dönemidir; ayrı dönem "
                              "olarak raporlanır, havuza katılmaz.",
        "kaynak": KAYNAK_TR + KAYNAK_ABD[:2],
    }


# ───────────────────────────────────────────────────────── rejim
def _kayan_sd(x: pd.Series) -> pd.Series:
    """Son 52 haftanın standart sapması, o hafta HARİÇ (bir önceki haftaya kadar)."""
    return x.rolling(DIKLESME_SD_PENCERE, min_periods=DIKLESME_SD_ASGARI).std().shift(1)


@lru_cache(maxsize=1)
def _rejim_girdi() -> pd.DataFrame:
    v = _vix_gunluk().resample("W-FRI").last().dropna()
    v_esik = v.expanding(VIX_R5_ASGARI_HAFTA).quantile(VIX_R5_YUZDELIK).shift(1)
    ab, tr = _abd_haftalik(), _tr_haftalik()
    idx = ab.index.union(tr.index)
    r = pd.DataFrame(index=idx)
    r["vix"] = v.reindex(idx)
    r["vix_esik"] = v_esik.reindex(idx)
    r["abd_vix"] = r["vix"]
    r["tr_vix"] = tr["vix"].reindex(idx)
    for u in ("abd", "tr"):
        r[f"{u}_r5"] = (r[f"{u}_vix"] >= r["vix_esik"]) & r["vix_esik"].notna()
    for ulke, h, uzun, dordu in (("abd", ab, "d10_bp", "guvenli_liman"), ("tr", tr, "d5_bp", "prim_dusus")):
        kayip = (-h["dolar_sapma_yuzde"]) if ulke == "abd" else h["kur_sapma_yuzde"]   # + = para değer kaybı
        r[f"{ulke}_uzun_bp"] = h[uzun]
        r[f"{ulke}_kisa_bp"] = h["d2_bp"]
        r[f"{ulke}_egim_bp"] = h["degim_bp"]
        r[f"{ulke}_para_kaybi_yuzde"] = kayip
        r[f"{ulke}_kadran"] = _kadran(h[uzun], -kayip, dordu)
        r[f"{ulke}_sd_egim_bp"] = _kayan_sd(h["degim_bp"])
        r[f"{ulke}_sd_para_yuzde"] = _kayan_sd(kayip)
        r[f"{ulke}_gun"] = h["_gun"]
    r["tr_yonetilen"] = oo.yonetilen_mi(idx)
    r["kismi"] = idx > oo.CIPA_GUN
    return r


def _etiketle(r: pd.DataFrame, ulke: str, kat_para: float = KUR_SAPMA_SD,
              kat_egim: float = DIKLESME_SD, egri: bool = True) -> pd.Series:
    """Öncelik: R5 → (prim, eşikli) ∧ ayılı dikleşme → normal."""
    yuksek, orta, normal = ("R5", "R2", "R1") if ulke == "abd" else ("R5", "R4", "R3")
    u, e, k = r[f"{ulke}_uzun_bp"], r[f"{ulke}_egim_bp"], r[f"{ulke}_para_kaybi_yuzde"]
    sde, sdk = r[f"{ulke}_sd_egim_bp"], r[f"{ulke}_sd_para_yuzde"]
    ok = u.notna() & k.notna() & sde.notna() & sdk.notna() & r["vix_esik"].notna()
    prim = (u > 0) & (k > kat_para * sdk)
    dik = (u > 0) & (e > kat_egim * sde)
    kosul = prim & dik if egri else prim
    lab = pd.Series(None, index=r.index, dtype=object)
    r5 = r[f"{ulke}_r5"]
    lab[ok & r5] = yuksek
    lab[ok & ~r5 & kosul] = orta
    lab[ok & lab.isna()] = normal
    return lab


@lru_cache(maxsize=1)
def _rejim_kur() -> pd.DataFrame:
    r = _rejim_girdi().copy()
    for ulke in ("abd", "tr"):
        r[f"{ulke}_prim_esikli"] = (r[f"{ulke}_uzun_bp"] > 0) & (
            r[f"{ulke}_para_kaybi_yuzde"] > KUR_SAPMA_SD * r[f"{ulke}_sd_para_yuzde"])
        r[f"{ulke}_dik"] = (r[f"{ulke}_uzun_bp"] > 0) & (r[f"{ulke}_egim_bp"] > DIKLESME_SD * r[f"{ulke}_sd_egim_bp"])
        r[ulke] = _etiketle(r, ulke)
    return r


def rejim() -> pd.DataFrame:
    """Haftalık rejim etiketleri (cuma etiketli hafta; `kismi` çıpa haftasını işaretler).

    Sütunlar: `abd` (R1 DM normal · R2 DM mali kaygı · R5 küresel riskten kaçış),
    `tr` (R3 EM güvenilir merkez bankası · R4 EM mali baskınlık · R5), ve etiketin
    girdileri (`<ülke>_uzun_bp`, `_kisa_bp` (2 yıllık), `_egim_bp`, `_para_kaybi_yuzde`,
    `_kadran`, eşikler).
    Hafta cuma etiketlidir; ABD cuma kapanışıyla, Türkiye perşembe kapanışıyla
    örneklenir (`abd_gun`, `tr_gun` gerçek günü taşır). Türkiye'nin DİBS bacağı
    gösterge eğrisinin "gun_sonu" hizasından (`ortak_olc.DIBS_KAYMA`, 2 iş günü sonraki etiket) alınır.
    Kural (öncelik sırasıyla):
      1. R5: örnek gününün VIX kapanışı ≥ VIX'in genişleyen 75. yüzdeliği
         (1990'dan bir önceki haftaya kadar haftalık kapanışlar, asgari 52 hafta).
      2. R2 (ABD) / R4 (TR): uzun uç yükseliyor VE para, kur değişiminin son 26
         haftalık ortalamasına göre 0,5 × σ'dan fazla değer kaybediyor VE eğri
         ayılı dikleşiyor: Δ(uzun − 2 yıllık) > 0,5 × σ (σ'lar son 52 haftanın,
         o hafta hariç). Uzun uç ABD'de 10 yıllık, Türkiye'de 5 yıllık.
      3. Öbür haftalar R1 (ABD) / R3 (TR).
    `tr_yonetilen` 2021-12…2023-06 haftalarını işaretler (kur tepkisinde ayrı dönem)."""
    return _rejim_kur().copy()


def _hafta_satiri(r: pd.DataFrame, t, ulke: str) -> dict:
    z = r.loc[t]
    return {"hafta": str(t.date()), "etiket": z[ulke], "kadran": z[f"{ulke}_kadran"],
            "uzun_bp": float(z[f"{ulke}_uzun_bp"]), "kisa_bp": float(z[f"{ulke}_kisa_bp"]),
            "egim_bp": float(z[f"{ulke}_egim_bp"]),
            "para_kaybi_yuzde": float(z[f"{ulke}_para_kaybi_yuzde"]), "vix": float(z[f"{ulke}_vix"]),
            "ornek_gunu": str(pd.Timestamp(z[f"{ulke}_gun"]).date()),
            "yonetilen": bool(z["tr_yonetilen"]) if ulke == "tr" else False}


NORMAL_SINIFLARI = ("ayili_yassilasma", "diklesme_esik_alti", "kur_sapmasi_esik_alti", "uzun_uc_yukselmedi")


def _normal_ayrisimi(z: pd.DataFrame, ulke: str, normal: str) -> dict:
    """En büyük on para kaybı haftasından NORMAL rejime (ABD R1 · Türkiye R3) düşenlerde
    orta rejimin (R2 · R4) hangi şartı tutmadı — eğriye göre ayrık ve tam bir bölüntü:
      ayili_yassilasma      uzun uç yükseldi ve eğri yassılaştı (kısa uç uzun uçtan fazla yükseldi)
      diklesme_esik_alti    uzun uç yükseldi, eğri dikleşti ama eşiğin altında kaldı
      kur_sapmasi_esik_alti uzun uç yükseldi, ayılı dikleşme var, para kaybı eşiğin altında
      uzun_uc_yukselmedi    uzun uç yükselmedi (düştü ya da yerinde)
    Normal etiket R5 değil ve (prim ∧ dikleşme) değil demektir, yani dört sınıf etiketin
    bütün hâllerini kapsar; `yassilasan` eğrinin düştüğü haftaları sınıftan bağımsız sayar
    (ayılı ve boğalı birlikte)."""
    zn = z[z[ulke] == normal]
    u, e = zn[f"{ulke}_uzun_bp"], zn[f"{ulke}_egim_bp"]
    dik, prim = zn[f"{ulke}_dik"].astype(bool), zn[f"{ulke}_prim_esikli"].astype(bool)
    yuk = u > 0
    maske = {
        "ayili_yassilasma": yuk & (e < 0),
        "diklesme_esik_alti": yuk & (e >= 0) & ~dik,
        "kur_sapmasi_esik_alti": yuk & dik & ~prim,
        "uzun_uc_yukselmedi": ~yuk,
    }
    say = {k: int(maske[k].sum()) for k in NORMAL_SINIFLARI}
    return {
        "etiket": normal, "n": int(len(zn)), "sayim": say,
        "haftalar": {k: [str(t.date()) for t in zn.index[maske[k].values]] for k in NORMAL_SINIFLARI},
        "bolunu_tam": bool(sum(say.values()) == len(zn)),
        "yassilasan": int((e < 0).sum()),
        "yontem": "En büyük on para kaybı haftasının normal rejime düşenleri, orta rejimin eğri ve kur "
                  "şartlarına göre ayrıldı: uzun uç yükselip eğri yassılaştıysa kısa uç uzun uçtan fazla "
                  "yükselmiştir; uzun uç yükselip eğri dikleştiyse dikleşme eşiğin altında kalmıştır "
                  "(ya da dikleşme eşiği aşıp para kaybı eşiğin altında kalmıştır); uzun uç "
                  "yükselmediyse kural haftayı orta rejime yazamaz.",
    }


def _rejim_ozeti() -> dict:
    tam = _rejim_kur()
    cipa = tam[tam["kismi"]]
    r = tam[~tam["kismi"]]
    out = {}
    for ulke, etiketler in (("abd", ("R1", "R2", "R5")), ("tr", ("R3", "R4", "R5"))):
        lab = r[ulke].dropna()
        ok = lab.index
        say = {e: int((lab == e).sum()) for e in etiketler}
        n = int(len(lab))
        alanlar = (f"{ulke}_uzun_bp", f"{ulke}_egim_bp", f"{ulke}_para_kaybi_yuzde")
        harek = {e: {a.split("_", 1)[1]: float(r.loc[r[ulke] == e, a].mean()) for a in alanlar} for e in etiketler}
        orta = etiketler[1]
        duy = {}
        for kat in (0.0, 0.5, 1.0):
            duy[f"esik_{kat:g}_sd"] = float((_etiketle(r, ulke, kat, kat).loc[ok] == orta).mean())
        duy["egri_kosulsuz_0.5_sd"] = float((_etiketle(r, ulke, KUR_SAPMA_SD, DIKLESME_SD, egri=False).loc[ok] == orta).mean())
        z5 = r.loc[ok][lab == "R5"]
        en = r.loc[ok, f"{ulke}_para_kaybi_yuzde"].nlargest(10).index
        out_normal = _normal_ayrisimi(r.loc[en], ulke, etiketler[0])
        out[ulke] = {
            "n_hafta": n, "ilk": str(lab.index.min().date()), "son": str(lab.index.max().date()),
            "hafta": say, "pay": {e: say[e] / n for e in etiketler}, "ortalama_hareket": harek,
            "orta_rejim_payi_duyarlilik": duy,
            "r5_kadran_dagilimi": {k_: float(v_) for k_, v_ in z5[f"{ulke}_kadran"].value_counts(normalize=True).items()},
            "en_buyuk_10_para_kaybi_haftasi": [_hafta_satiri(r, t, ulke) for t in en],
            "en_buyuk_10_para_kaybi_etiketleri": {e: int((r.loc[en, ulke] == e).sum()) for e in etiketler},
            "en_buyuk_10_para_kaybi_bogali_ya_da_ayili_yassilasma": int((r.loc[en, f"{ulke}_egim_bp"] < 0).sum()),
            "en_buyuk_10_para_kaybi_normal_rejim_ayrisimi": out_normal,
        }
    # Türkiye dönemlere göre
    don = {}
    trg = pd.DatetimeIndex(r["tr_gun"])
    for ad, a, b in DONEMLER_TR:
        lab = r.loc[(trg >= pd.Timestamp(a)) & (trg <= pd.Timestamp(b)), "tr"].dropna()
        if len(lab):
            don[ad] = {"n_hafta": int(len(lab)), **{e: float((lab == e).mean()) for e in ("R3", "R4", "R5")}}
    out["tr"]["donemler"] = don
    out["tr"]["yonetilen_hafta"] = int(r.loc[r["tr"].notna(), "tr_yonetilen"].sum())
    # yönetilen kur dönemi kur tepkisinde ayrı dönemdir: havuz payının yanında hariç pay
    lab_dis = r.loc[r["tr"].notna() & ~r["tr_yonetilen"].astype(bool), "tr"]
    out["tr"]["yonetilen_haric"] = {"n_hafta": int(len(lab_dis)),
                                    "hafta": {e: int((lab_dis == e).sum()) for e in ("R3", "R4", "R5")},
                                    "pay": {e: float((lab_dis == e).mean()) for e in ("R3", "R4", "R5")}}
    # ham kur değişimiyle (26 haftalık ortalama düşülmeden) R4 payı — kayma tuzağının büyüklüğü
    tr_h = _tr_haftalik().reindex(r.index)
    ham = r.copy()
    ham["tr_para_kaybi_yuzde"] = tr_h["dkur_yuzde"]
    ham["tr_sd_para_yuzde"] = _kayan_sd(tr_h["dkur_yuzde"].dropna()).reindex(r.index)
    okt = r["tr"].dropna().index
    out["tr"]["r4_payi_ham_kurla"] = float((_etiketle(ham, "tr").loc[okt] == "R4").mean())
    # vaka haftaları
    vk = {}
    for ad, (a, b) in VAKALAR.items():
        z = r.loc[a:pd.Timestamp(b) + pd.Timedelta(days=6)]
        vk[ad] = {"haftalar": [str(t.date()) for t in z.index],
                  "abd": z["abd"].tolist(), "abd_kadran": z["abd_kadran"].tolist(),
                  "vix": [float(x) for x in z["vix"]]}
    son = r.dropna(subset=["abd"]).iloc[-1]
    son_tr = r.dropna(subset=["tr"]).iloc[-1]
    cipa_h = {}
    if len(cipa):
        c0 = cipa.iloc[-1]
        cipa_h = {"etiket": str(cipa.index[-1].date()), "abd_son_gun": str(pd.Timestamp(c0["abd_gun"]).date()),
                  "tr_son_gun": str(pd.Timestamp(c0["tr_gun"]).date()), "abd": c0["abd"], "tr": c0["tr"],
                  "abd_vix": float(c0["abd_vix"]), "tr_vix": float(c0["tr_vix"]), "vix_esik": float(c0["vix_esik"]),
                  "abd_kadran": c0["abd_kadran"], "tr_kadran": c0["tr_kadran"],
                  "abd_uzun_bp": float(c0["abd_uzun_bp"]), "tr_uzun_bp": float(c0["tr_uzun_bp"]),
                  "not": (f"yarım hafta: ABD'de {_tarih_tr(son['abd_gun'])} gününden {_tarih_tr(c0['abd_gun'])} "
                          f"gününe, Türkiye'de {_tarih_tr(son_tr['tr_gun'])} gününden {_tarih_tr(c0['tr_gun'])} "
                          "gününe; sayımlara girmedi")}
    out.update({
        "vaka_haftalari": vk,
        "son_tam_hafta": {"etiket": str(r.dropna(subset=["abd"]).index[-1].date()), "abd": son["abd"],
                          "tr": son_tr["tr"], "abd_ornek_gunu": str(pd.Timestamp(son["abd_gun"]).date()),
                          "tr_ornek_gunu": str(pd.Timestamp(son_tr["tr_gun"]).date()),
                          "abd_vix": float(son["abd_vix"]), "tr_vix": float(son_tr["tr_vix"]),
                          "vix_esik": float(son["vix_esik"])},
        "cipa_haftasi": cipa_h,
        "esikler": {"VIX_R5_YUZDELIK": VIX_R5_YUZDELIK, "VIX_R5_ASGARI_HAFTA": VIX_R5_ASGARI_HAFTA,
                    "KUR_SAPMA_SD": KUR_SAPMA_SD, "DIKLESME_SD": DIKLESME_SD,
                    "SD_PENCERE_HAFTA": DIKLESME_SD_PENCERE, "KUR_KAYMA_PENCERE_HAFTA": KUR_KAYMA_PENCERE,
                    "son_vix_esik": float(son["vix_esik"]),
                    "son_abd_diklesme_esik_bp": float(DIKLESME_SD * son["abd_sd_egim_bp"]),
                    "son_abd_dolar_esik_yuzde": float(KUR_SAPMA_SD * son["abd_sd_para_yuzde"]),
                    "son_tr_diklesme_esik_bp": float(DIKLESME_SD * son_tr["tr_sd_egim_bp"]),
                    "son_tr_kur_esik_yuzde": float(KUR_SAPMA_SD * son_tr["tr_sd_para_yuzde"])},
        "kural": "Öncelik sırası: (1) R5 — örnek gününün (ABD cuma, Türkiye perşembe) VIX kapanışı, VIX'in 1990'dan bir önceki haftaya "
                 "kadar biriken haftalık kapanışlarının 75. yüzdeliğinde ya da üstünde; (2) R2 (ABD) ya da "
                 "R4 (Türkiye) — uzun uç yükselirken para, son 26 haftanın ortalama hareketine göre yarım "
                 "standart sapmadan fazla değer kaybediyor ve eğri ayılı dikleşiyor (uzun eksi 2 yıllık fark "
                 "yarım standart sapmadan fazla açılıyor; standart sapmalar son 52 haftanın); (3) öbür "
                 "haftalar R1 ya da R3.",
        "sinir": "CDS yok: Türkiye'de küresel riskten kaçış ile yerel risk primi aynı kadrana (faiz ↑, kur ↑) "
                 "düşer ve iki rejimi yalnız VIX ayırır. ABD'de güvenli liman döneminin riskten dönüş "
                 "haftası 'prim' kadranına düşer, bu yüzden R5 önce sorulur. Ayılı dikleşme şartı "
                 "Türkiye'nin sert stres haftalarını da R3'e yazabilir: kısa uç uzun uçtan fazla "
                 "yükseldiğinde (likidite sıkılaşması) eğri yassılaşır ve dikleşme şartı tutmaz; en büyük "
                 "on TL değer kaybı haftasının etiketleri ve R3'e düşenlerin hangi şartı geçemediği "
                 "ayrıca verildi. Etiket haftalıktır ve tek haftanın gürültüsünü taşır; eşikler sabit "
                 "adlıdır ama sezgiyle seçildi, duyarlılık ayrıca verildi. Yönetilen kur döneminde kur "
                 "yönü piyasayı değil politikayı ölçer.",
        "n": int(r["abd"].notna().sum()), "ilk": str(r["abd"].dropna().index.min().date()),
        "son": str(r["abd"].dropna().index.max().date()),
        "yontem": "Haftalık kadran, VIX'in genişleyen 75. yüzdeliği ve eğrinin ayılı dikleşmesiyle beş "
                  "rejimden biri öncelik sırasıyla atandı.",
        "kaynak": KAYNAK_ABD + KAYNAK_TR,
    })
    return out


# ───────────────────────────────────────────────────────── şekil 01
def sekil_01() -> dict:
    o = _p1a_seri().dropna(subset=["kor"])
    # haftanın SON GERÇEK günü (cuma etiketi çıpa haftasında 30.09'un ilerisine düşerdi)
    hafta = o.index.to_period("W-FRI")
    w = o.groupby(hafta).tail(1).dropna(subset=["kor"])
    return {
        "tarih": [str(t.date()) for t in w.index],
        "kor": [round(float(x), 4) for x in w["kor"]],
        "vix60": [round(float(x), 4) if pd.notna(x) else None for x in w["vix60"]],
        "vix60_q75": [round(float(x), 4) if pd.notna(x) else None for x in w["q75"]],
        "vakalar": [{"ad": ad, "ilk": a, "son": b} for ad, (a, b) in VAKALAR.items()],
        "n": int(len(w)), "ilk": str(w.index.min().date()), "son": str(w.index.max().date()),
        "yontem": "Günlük kayan korelasyon ve 60 günlük VIX ortalaması haftanın son gününde örneklendi.",
        "kaynak": KAYNAK_ABD,
    }


# ───────────────────────────────────────────────────────── giriş
def olc() -> dict:
    out = {"p1a": p1a(), "p1b": p1b(), "rejim": _rejim_ozeti(), "sekil_01": sekil_01()}
    return oo.yuvarla(out, 4)


if __name__ == "__main__":
    import json
    print(json.dumps(olc(), ensure_ascii=False, indent=1)[:6000])
