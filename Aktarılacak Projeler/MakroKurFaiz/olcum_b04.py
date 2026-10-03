#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 4 ölçüm katmanı: enflasyon ve işaret.

Pratikler
  p4a  Türkiye TÜFE sürprizi = gerçekleşen aylık TÜFE − PKA cari ay beklentisi
       (164 ay): anket etiketinin sınaması, dağılım ve işaret dengesi, kur çöküşü
       günleri ve ters nedensellik satırı; yayım günü tepkisi (plasebo sınamasına
       bağlı; yayım günleri argüman) ve kapı düşerse aylık ilişki.
  p4b  ABD TÜFE günleri: Δ2y ile ΔUSD/EUR ve ΔUSD/JPY kovaryansı, yayım günü ile
       sıradan gün (yayım günleri argüman; BLS takvimi gelmediyse kurulmaz).
  p4c  Türkiye 2021 (31.03–31.12) ile ABD 2022 (03.01–31.10) vaka tablosu.
  sekil_05 sürpriz × tepki (rejime göre), sekil_06 ABD TÜFE günü kovaryansı.

Ortak tanımlar `ortak_olc`ten gelir (regresyon ve hüküm, Türkiye takvimi, DİBS
hizası, günlük değişim çerçevesi, kanonik plasebo sınaması, dolar sepeti); yayım
günü oranı b03'ten. Aynı ölçü iki modülde iki kodla kurulmaz.

HİZA. Yayım günü ve yayım ayı çerçevesi DİBS değişimini USD/TRY'nin GÜN SONU
kapanışıyla aynı piyasa gününde ölçer: DİBS "gun_sonu" hizasındadır
(`ortak_olc.DIBS_KAYMA`, D gününe D+2 iş günü etiketli değer). Önceki sürüm
bir iş günlük (sabah) kaymayı kullanıyordu; o hizada D'nin değeri D sabahının
sabitlemesidir. 10:00'daki TÜFE için sabitlemenin saati ölçülmediğinden iki
hiza da Bölüm 2'de "saatle bağdaşan" kaymalardır; burada kurla aynı güne
oturan gün sonu hizası seçilir. CUMA: 2013–2026'daki TÜFE yayımlarının 26'sı
cumadır; 18.12.2023 öncesi cuma kur değişimi hafta sonunu taşıdığı için o
günlerin kur değişimi boşaltılır (`cuma_dus=True`), DİBS satırları kalır.
Aylık ilişkide (ay sonundan ay sonuna) bayrak uygulanmaz: cuma biten ayın
sonu bir hafta sonu kayar, perşembeye çekmek aynı büyüklükte ters yönlü bir
kayma üretir.

ÖLÇÜM TUZAKLARI (bu modül yazılırken ölçüldü)
1. Anket etiketi: PKA "cari ay" beklentisi o ayın kendi TÜFE'siyle en yüksek
   korelasyonu ve en düşük hatayı veriyor (bir ay önceki ve sonraki aya karşı
   ölçüldü); sürpriz aynı ayın gerçekleşmesiyle kurulur.
2. TÜFE YAYIM GÜNÜNDE KUR VE DİBS SIRADAN GÜNDEN AYRIŞMIYOR. Plasebo oranı
   USD/TRY'de 0,89 ile 1,02 arasında, DİBS 2 ve 5 yıllıkta 1'e yakın ve tepe
   yayım gününde değil (sabah ve gün sonu hizasında; ham etiketle 2 ve 5
   yıllıkta tepe 0'a düşüyor ama profil düz, ve ham etiket kurla iki gün kayık —
   Bölüm 2). Hangi düğümün güçlü plasebo sınamasını geçtiği `yayim_gunu.kapi` satırlarındadır.
   Yayım günü regresyonu sınamayı geçen seride kurulur; öbürleri kurulmadı ve
   yerine aylık ilişki verilir (yayım AYINI ölçer, yayım gününü değil).
3. Kur çöküşü eşiği (|Δ| > 4σ) sabit bir σ ile değil, önceki 250 iş gününün
   oynaklığıyla kurulur; yönetilen kur döneminde σ küçük olduğu için Haziran
   2023'ün ayarlama günleri de çöküş sayılır ve öyle işaretlenir. 18.12.2023
   öncesinde cuma etiketi hafta sonunu taşır; hafta sonu haberleri (7 Haziran
   2015 seçimi, 20.03.2021 görevden alma) cuma günü görünür.
4. TÜFE sürprizinin uç değeri 12.2021'dir (+10,2 puan). O ayın 4σ günleri
   değer KAZANCI günleridir (KKM, 20–21.12.2021); sürprizi yaratan değer kaybı
   Kasım'daydı (23.11.2021, +%11,7), yani Aralık çöküşün ERTESİ ayıdır.
   Sürprizin kurla ilişkisi bu yüzden yönü ve zamanlaması işaretlenerek, ayrı
   satırda okunur (tuzak 9).
5. TÜİK takviminde yayım günü, kapsadığı ayın ertesi ayındadır; 2013–2026'da
   164 yayımın her biri tek bir aya eşleniyor (eşleme benzersiz, sınandı).
6. Yönetilen kur dönemi olay günleri yayım TARİHİNE göre atanır (12.2021'de
   yayımlanan Kasım TÜFE'si yönetilen döneme düşer); aylık dağılım KAPSANAN aya göre.
7. Aylık ilişkide 2013–2020 kur eğimi (sürpriz ↑ → yayım ayında USD/TRY ↓)
   eşikleri geçiyor ama tek gözleme bağlı: Eylül 2018 sürprizi (Ağustos çöküşünün
   ürünü) Ekim'deki toparlanmayla eşleşiyor. O ay dışarıda kalınca eğim üçte
   bir küçülüyor; kur çöküşü taşıyan aylar dışarıda kalınca örneklem dışı kıyas
   geçmiyor. Çöküş sonrası geri dönüş, ters nedenselliğin aylık izidir.
8. 03.10.2014 yayımı (Kurban Bayramı arifesi) Türkiye iş günü takviminde
   vardır ama DİBS o gün değer yayımlamadı: kur satırı ölçülür, DİBS satırları
   boştur (önceki sürüm DİBS'in gün kümesiyle kesişen takvimi kullanıyor ve
   yayımı bütünüyle düşürüyordu).
9. |Δ| > 4σ BİR YÖN DEĞİLDİR. 45 günün 13'ü TL'nin değer KAZANDIĞI günler
   (KKM, 24.08.2023 artırımı, 14.08.2018 toparlanması). "Çöküş ayı" kümesine
   değer kazancı günleri de girince ters nedensellik satırı (çöküş ayı
   ortalama sürprizi 1,07 puan) aslında politika tepkisi aylarını ölçüyordu:
   değer kaybı çöküşünün olduğu ayda sürpriz öbür aylardan ayrışmıyor (0,36'ya
   karşı 0,28; Welch t 0,28), ERTESİ ayda ayrışıyor (1,63'e karşı 0,15; t
   1,94). Kur çöküşü yalnız değer kaybı günüdür; iki yönlü 4σ kümesi yalnız
   aykırı gözlem dışlamasında kullanılır. Yönetilen dönemin "tasarım gereği"
   etiketi yalnız KURULMUŞ ve |t| < 2 olan eğime yazılır; kurulmamış satır
   sınanmamıştır.
"""
from __future__ import annotations

import math
import warnings
from functools import lru_cache

import numpy as np
import pandas as pd
from scipy import stats

import bulut
import olcum_b03 as b3
import ortak_olc as oo

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

DONEM_TUFE = [
    ("d2013_2020", "2013-01-01", "2020-12-31", "2013–2020"),
    ("d2021", "2021-01-01", oo.YON_ONCESI_SON, f"2021-01…{oo.YON_ONCESI_AY}"),
    ("yonetilen", oo.YON_ILK, oo.YON_SON, f"yönetilen kur {oo.YON_AY[0]}…{oo.YON_AY[1]}"),
    ("d2023_2026", oo.YON_SONRASI_ILK, "2026-09-30", f"{oo.YON_SONRASI_AY}…2026-09"),
]
HIZA = "gun_sonu"
COKUS_ESIK_SIGMA = 4.0
COKUS_PENCERE = 250
COKUS_ASGARI = 120
HUBER_K = 1.345
TR_2021 = (pd.Timestamp("2021-03-31"), pd.Timestamp("2021-12-31"))
ABD_2022 = (pd.Timestamp("2022-01-03"), pd.Timestamp("2022-10-31"))


_iso, _f = oo._iso, oo._f                  # tek tanımlar ortak_olc'de


def _liste(s) -> list:
    return [_f(v) for v in np.asarray(s, dtype=float)]


def _donem(t) -> str | None:
    t = pd.Timestamp(t)
    for k, a, b, _ in DONEM_TUFE:
        if pd.Timestamp(a) <= t <= pd.Timestamp(b):
            return k
    return None


# ─────────────────────────────────────────────────────────────── sağlamlık araçları
def _yonetilen_notu(r: dict) -> str:
    """Yönetilen kur döneminin etiketi: 'tasarım gereği' yalnız KURULMUŞ ve sıfırdan
    ayrışmayan bir eğim için yazılır; kurulmamış satır sınanmamıştır."""
    if r.get("t") is None:
        return "yönetilen kur dönemi; eğim sınanamadı (" + (r.get("not") or r.get("sebep") or "test kurulmadı") + ")"
    if abs(r["t"]) < 2:
        return "kur yönetildiği için eğimin sıfırdan ayrışmaması tasarım gereğidir"
    return "yönetilen dönemde de eğim sıfırdan ayrışıyor"


def huber_egim(y, x, k: float = HUBER_K, tur: int = 100) -> dict:
    """Huber M-kestirimi (IRLS): ağırlık min(1, k/|r/s|), ölçek MAD/0,6745."""
    y = np.asarray(y, float)
    x = np.asarray(x, float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    X = np.column_stack([np.ones(len(y)), x])
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    s = None
    for i in range(tur):
        r = y - X @ b
        s = np.median(np.abs(r - np.median(r))) / 0.6745
        if s <= 0:
            break
        u = np.abs(r / s)
        w = np.where(u <= k, 1.0, k / np.maximum(u, 1e-12))
        sw = np.sqrt(w)
        yeni = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
        if np.max(np.abs(yeni - b)) < 1e-10:
            b = yeni
            break
        b = yeni
    return {"sabit": _f(b[0]), "egim": _f(b[1]), "olcek": _f(s), "tur": int(i + 1), "k": k,
            "agirligi_dusen": int((np.abs((y - X @ b) / s) > k).sum()) if s else None}


def isaret_testi(y, x) -> dict:
    """Sürprizin işareti ile tepkinin işareti aynı mı: iki yanlı binom sınaması (p = 0,5)."""
    d = pd.concat([pd.Series(np.asarray(y, float)), pd.Series(np.asarray(x, float))], axis=1).dropna()
    d = d[(d.iloc[:, 0] != 0) & (d.iloc[:, 1] != 0)]
    n = len(d)
    if n == 0:
        return {"n": 0}
    ayni = int((np.sign(d.iloc[:, 0]) == np.sign(d.iloc[:, 1])).sum())
    p = stats.binomtest(ayni, n, 0.5).pvalue
    return {"n": int(n), "ayni_isaret": ayni, "ayni_isaret_pay": ayni / n, "p_iki_yanli": _f(p)}


def saglam_regresyon(y: pd.Series, x: pd.Series, ad: str, **kw) -> dict:
    r = oo.regresyon(y, x, **kw)
    r["ad"] = ad
    if r.get("durum") in ("vaka tablosu", "kurulmadi"):
        return r
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1, sort=True).dropna()
    r["huber"] = huber_egim(d["y"], d["x"])
    r["isaret"] = isaret_testi(d["y"], d["x"])
    return r


# ═══════════════════════════════════════════════════════════════ p4a
@lru_cache(maxsize=1)
def surpriz_serisi() -> pd.DataFrame:
    """Aylık: gerçekleşen aylık TÜFE (%), PKA cari ay beklentisi (%), sürpriz (puan)."""
    e = oo.oku("enflasyon_aylik")
    e.index = pd.PeriodIndex(e.index, freq="M")
    aylik = (e["tufe"] / e["tufe"].shift(1) - 1) * 100
    df = pd.DataFrame({"gercek": aylik, "beklenti": e["pka_ay_cari"]}).dropna()
    df["surpriz"] = df["gercek"] - df["beklenti"]
    df["rejim"] = [_donem(p.to_timestamp()) for p in df.index]
    return df


def etiket_sinamasi() -> dict:
    e = oo.oku("enflasyon_aylik")
    e.index = pd.PeriodIndex(e.index, freq="M")
    aylik = (e["tufe"] / e["tufe"].shift(1) - 1) * 100
    out = {}
    for k, ad in ((-1, "bir_onceki_ay"), (0, "ayni_ay"), (1, "bir_sonraki_ay")):
        x = pd.concat([e["pka_ay_cari"], aylik.shift(-k)], axis=1).dropna()
        out[ad] = {"n": int(len(x)), "korelasyon": _f(x.corr().iloc[0, 1]),
                   "ort_mutlak_hata_puan": _f((x.iloc[:, 0] - x.iloc[:, 1]).abs().mean())}
    en_iyi = max(out, key=lambda a: out[a]["korelasyon"])
    out["en_iyi"] = en_iyi
    out["yontem"] = ("PKA cari ay beklentisi bir önceki, aynı ve bir sonraki ayın gerçekleşen aylık TÜFE'siyle "
                     "korelasyon ve ortalama mutlak hata bakımından karşılaştırıldı.")
    return out


def _dagilim(s: pd.Series) -> dict:
    s = s.dropna()
    if not len(s):
        return {"n": 0}
    sira = s.sort_values(ascending=False)
    nz = s[s != 0]
    p = stats.binomtest(int((nz > 0).sum()), int(len(nz)), 0.5).pvalue if len(nz) else None
    return {"n": int(len(s)), "ilk": str(s.index.min()), "son": str(s.index.max()),
            "ort_puan": _f(s.mean()), "medyan_puan": _f(s.median()), "sd_puan": _f(s.std()),
            "ort_mutlak_puan": _f(s.abs().mean()),
            "pozitif": int((s > 0).sum()), "negatif": int((s < 0).sum()), "sifir": int((s == 0).sum()),
            "isaret_p_iki_yanli": _f(p),
            "en_buyuk_uc": [[str(i), _f(v)] for i, v in sira.head(3).items()],
            "en_kucuk_uc": [[str(i), _f(v)] for i, v in sira.tail(3).iloc[::-1].items()],
            "ar1": _f(oo.ar1(s)) if len(s) > 12 else None}


@lru_cache(maxsize=1)
def kur_cokus_gunleri() -> pd.DataFrame:
    """|ΔUSD/TRY| > 4σ günleri; σ önceki 250 iş gününün günlük log değişim oynaklığı."""
    k, _ = oo.usdtry()
    d = np.log(k).diff() * 100
    sig = d.rolling(COKUS_PENCERE, min_periods=COKUS_ASGARI).std().shift(1)
    z = d / sig
    c = pd.DataFrame({"degisim_yuzde": d, "sigma_yuzde": sig, "z": z}).dropna()
    return c[c["z"].abs() > COKUS_ESIK_SIGMA]


def tufe_gunu_tepkisi(yayim_gunleri) -> dict:
    """Yayım günü tepkisi. `yayim_gunleri`: TÜFE yayım günleri (DatetimeIndex);
    her gün bir önceki ayın TÜFE'sini duyurur. Seri sınamayı geçmezse kurulmaz."""
    sp = surpriz_serisi()
    g = pd.DatetimeIndex(yayim_gunleri)
    ref = g.to_period("M") - 1
    es = pd.Series(ref, index=g)
    es = es[es.isin(sp.index)]
    if not es.is_unique:
        return oo.kurulmadi("yayım günleri ile aylar birebir eşlenmiyor")
    deg = oo.tr_gunluk_degisim(HIZA, ("n1y", "n2y", "n5y"), kur=True, tcmb=True, cuma_dus=True)
    olay = es.index.intersection(deg.index)
    dusen = [_iso(t) for t in es.index if t not in deg.index]
    x = pd.Series(sp.loc[es.loc[olay].values, "surpriz"].values, index=olay, name="surpriz")
    kapilar = {c: oo.kapi_ozeti(oo.olay_kapisi(deg[c], olay, guclu=True, k_tohum=200 + i,
                                               haric=oo.YONETILEN if c.startswith("usdtry") else None))
               for i, c in enumerate(("n1y", "n2y", "n5y", "usdtry", "usdtry_tcmb"))}
    # 10:00 olayında sabah hizası da saatle bağdaşır (Bölüm 2): DİBS sınaması o hizada da sorulur
    sabah = oo.tr_gunluk_degisim("sabah", ("n1y", "n2y", "n5y"), kur=False, tcmb=False)
    kapi_sabah = {c: oo.kapi_ozeti(oo.olay_kapisi(sabah[c], olay, guclu=True, k_tohum=210 + i))
                  for i, c in enumerate(("n1y", "n2y", "n5y"))}
    cokus = kur_cokus_gunleri()
    out = {"n_yayim": int(len(olay)), "ilk": _iso(olay.min()), "son": _iso(olay.max()), "kapi": kapilar,
           "kapi_sabah_hizasi": kapi_sabah,
           "hiza_notu": ("Regresyonlar gün sonu hizasında kurulur (kurla aynı piyasa günü). 10:00'daki TÜFE için "
                         "sabitlemenin saati ölçülmediğinden sabah hizası (D gününe D+1 etiketli değer) da saatle "
                         "bağdaşır; DİBS sınaması o hizada ayrıca verilir, regresyon kurmaz."),
           "eslesme": "yayım günü → bir önceki ay (benzersiz)",
           "takvimde_olmayan_yayim": dusen,
           "dibs_degeri_olmayan_yayim": [_iso(t) for t in olay if pd.isna(deg.loc[t, "n2y"])],
           "cuma_kur_degisimi_bos_yayim": int(((olay.dayofweek == 4) & (olay < oo.GECIS_YAHOO_CUMA)).sum()),
           "cokus_gunune_denk_yayim": [_iso(t) for t in olay if t in cokus.index]}
    tablo = {}
    for c, birim in (("n2y", "bp / 1 puan sürpriz"), ("n5y", "bp / 1 puan sürpriz"),
                     ("usdtry", "% / 1 puan sürpriz"), ("n1y", "bp / 1 puan sürpriz")):
        if not kapilar[c]["gecti"]:
            tablo[c] = oo.kurulmadi(oo.kapi_sebebi(kapilar[c]), kapi=kapilar[c])
            continue
        tablo[c] = {"birim": birim}
        for k, a, b, ad in DONEM_TUFE:
            e = olay[(olay >= a) & (olay <= b)]
            r = saglam_regresyon(deg.loc[e, c], x.loc[e], ad)
            if k == "yonetilen" and c == "usdtry":
                r["yonetilen_kur"] = True
                r["not"] = _yonetilen_notu(r)
            tablo[c][k] = r
        if c == "usdtry":
            hm = olay[~oo.yonetilen_mi(olay)]
            temiz = hm[~hm.isin(cokus.index)]
            tablo[c]["cokus_gunleri_haric"] = saglam_regresyon(
                deg.loc[temiz, c], x.loc[temiz], "yönetilen kur dönemi ve 4σ kur hareketi günleri (iki yön) hariç (sağlamlık)")
    out["tepki"] = tablo
    out["noktalar"] = {"tarih": [_iso(t) for t in olay], "ay": [str(p) for p in es.loc[olay].values],
                       "surpriz_puan": _liste(x.values), "rejim": [_donem(t) for t in olay],
                       **{f"d_{c}": _liste(deg.loc[olay, c].values) for c in ("n1y", "n2y", "n5y", "usdtry")}}
    return out


def aylik_iliski() -> dict:
    """Yayım AYINDAKİ değişim (ay sonundan ay sonuna) ile bir önceki ayın sürprizi."""
    sp = surpriz_serisi()
    seviye = oo.tr_gunluk(HIZA, ("n2y", "n5y"), kur=True)
    seviye["lkur"] = np.log(seviye.pop("usdtry"))
    ay_sonu = seviye.groupby(seviye.index.to_period("M")).last()
    d = pd.DataFrame({"d_n2y": ay_sonu["n2y"].diff() * 100, "d_n5y": ay_sonu["n5y"].diff() * 100,
                      "d_usdtry": ay_sonu["lkur"].diff() * 100})
    d = d.shift(-1)                     # ay m satırı: m+1 ayındaki (yayım ayındaki) değişim
    z = pd.concat([sp[["surpriz", "rejim"]], d], axis=1).dropna(subset=["surpriz"])
    z.index = z.index.to_timestamp()
    out = {"yontem": "Bir ayın TÜFE sürprizi, sürprizin yayımlandığı ayın başından sonuna 2 ve 5 yıllık getiri "
                     "(bp) ile USD/TRY'nin (log, %) değişimine dönem dönem Newey–West ile regresyonlandı; ölçü yayım "
                     "gününü değil yayım ayını kapsar ve aynı aydaki başka haberleri de taşır.",
           "kaynak": ["enflasyon_aylik", "dibs_egri_gunluk", "usdtry_yahoo_gunluk", "fonlama_gunluk"]}
    for c, birim in (("d_n2y", "bp / 1 puan sürpriz"), ("d_n5y", "bp / 1 puan sürpriz"),
                     ("d_usdtry", "% / 1 puan sürpriz")):
        out[c] = {"birim": birim}
        for k, a, b, ad in DONEM_TUFE:
            e = z.loc[a:b]
            r = saglam_regresyon(e[c], e["surpriz"], ad, ilk_pencere=max(12, len(e) // 2))
            if k == "yonetilen" and c == "d_usdtry":
                r["yonetilen_kur"] = True
                r["not"] = _yonetilen_notu(r)
            out[c][k] = r
    # ters nedensellik sağlamlığı: kapsanan ayda ya da yayım ayında kur çöküşü olan aylar dışarıda
    c_ay = set(kur_cokus_gunleri().index.to_period("M"))
    temiz = z[[not (t.to_period("M") in c_ay or (t.to_period("M") + 1) in c_ay) for t in z.index]]
    hm = temiz[~oo.yonetilen_mi(temiz.index)]
    out["d_usdtry"]["cokus_aylari_haric"] = saglam_regresyon(
        hm["d_usdtry"], hm["surpriz"], "yönetilen kur dönemi ve 4σ kur hareketi (iki yön) taşıyan aylar (kapsanan ya da "
                                       "yayım ayı) hariç, 2013–2026 havuzlanmış (sağlamlık)", ilk_pencere=max(12, len(hm) // 2))
    for k, a, b, ad in DONEM_TUFE:
        if k == "yonetilen":
            continue
        e = temiz.loc[a:b]
        out["d_usdtry"][f"cokus_aylari_haric_{k}"] = saglam_regresyon(
            e["d_usdtry"], e["surpriz"], f"{ad}, 4σ kur hareketi taşıyan aylar hariç", ilk_pencere=max(12, len(e) // 2))
    out["_z"] = z
    return out


def p4a() -> dict:
    sp = surpriz_serisi()
    dag = {"tum": _dagilim(sp["surpriz"])}
    for k, a, b, ad in DONEM_TUFE:
        x = sp.loc[pd.Period(a[:7], "M"):pd.Period(b[:7], "M"), "surpriz"]
        dag[k] = {"ad": ad, **_dagilim(x)}
    # kur çöküşü ve ters nedensellik (tuzak 9: yön ve zamanlama)
    c = kur_cokus_gunleri()
    c_ay = sorted(set(c.index.to_period("M")))
    kayip_ay = sorted(set(c[c["degisim_yuzde"] > 0].index.to_period("M")))
    kazanc_ay = sorted(set(c[c["degisim_yuzde"] < 0].index.to_period("M")))

    def _kiyas(kume, ad):
        a = sp["surpriz"][sp.index.isin(kume)]
        b = sp["surpriz"][~sp.index.isin(kume)]
        return {"ad": ad, "n_ay": int(len(a)), "n_diger": int(len(b)),
                "ort_surpriz_puan": _f(a.mean()), "diger_ort_surpriz_puan": _f(b.mean()),
                "medyan_puan": _f(a.median()), "diger_medyan_puan": _f(b.median()),
                "welch_t": _f(stats.ttest_ind(a, b, equal_var=False).statistic) if len(a) > 1 else None,
                "aylar_ve_surpriz": [[str(p), _f(v)] for p, v in a.items()]}
    cokus = {"esik_sigma": COKUS_ESIK_SIGMA, "sigma_penceresi_is_gunu": COKUS_PENCERE,
             "n_gun": int(len(c)), "ilk": _iso(c.index.min()), "son": _iso(c.index.max()),
             "n_deger_kaybi_gunu": int((c["degisim_yuzde"] > 0).sum()),
             "n_deger_kazanci_gunu": int((c["degisim_yuzde"] < 0).sum()),
             "gunler": [[_iso(t), _f(r.degisim_yuzde), _f(r.sigma_yuzde), _f(r.z),
                         "değer kaybı" if r.degisim_yuzde > 0 else "değer kazancı"] for t, r in c.iterrows()],
             "gun_sutunlari": ["tarih", "degisim_yuzde", "sigma_yuzde", "z", "yon"],
             "aylar": [str(p) for p in c_ay],
             "deger_kaybi_aylari": [str(p) for p in kayip_ay],
             "deger_kazanci_aylari": [str(p) for p in kazanc_ay],
             "cuma_notu": "18.12.2023 öncesinde cuma etiketi hafta sonunu ve pazartesi sabahını da taşır "
                          "(7 Haziran 2015 seçimi, 20.03.2021 görevden alma ve 8 Ekim 2017 vize krizi cuma günü görünür).",
             "ters_nedensellik": {
                 "deger_kaybi_ayni_ay": _kiyas(kayip_ay, "değer kaybı çöküşünün olduğu ay"),
                 "deger_kaybi_ertesi_ay": _kiyas([p + 1 for p in kayip_ay], "değer kaybı çöküşünden sonraki ay"),
                 "deger_kazanci_ayni_ay": _kiyas(kazanc_ay, "4σ değer kazancının olduğu ay (politika tepkisi ayları)"),
                 "iki_yon_ayni_ay": _kiyas(c_ay, "her iki yönde 4σ hareketin olduğu ay"),
                 "not": "Değer kaybı çöküşü TÜFE'ye bir ay gecikmeyle geçiyor: çöküş ayının sürprizi öbür aylardan "
                        "ayrışmıyor, ertesi ayınki ayrışıyor. 4σ değer kazancı ayları kurun düştüğü değil, "
                        "çöküşe politika tepkisinin geldiği aylardır (Aralık 2021, Ağustos 2023) ve sürprizleri "
                        "yüksektir. Ayrım nedensellik sınaması değildir, işaretlemedir."},
             "yontem": "Günlük USD/TRY log değişimi önceki 250 iş gününün oynaklığının 4 katını aştığında gün 4σ kur "
                       "hareketi sayıldı ve yönüyle işaretlendi; TL'nin değer kaybettiği günler kur çöküşüdür, "
                       "sürprizle ilişkisi çöküş ayı ve ertesi ay için ayrı ölçüldü.",
             "kaynak": ["usdtry_yahoo_gunluk", "enflasyon_aylik"]}
    try:
        gunler = bulut.tufe_gunleri()
        tepki = tufe_gunu_tepkisi(gunler)
        tepki["kaynak"] = ["bulut/tuik_takvim", "dibs_egri_gunluk", "usdtry_yahoo_gunluk", "usdtry_tcmb_gunluk",
                           "enflasyon_aylik"]
        tepki["saat"] = ("TÜFE 10:00 TSİ; DİBS gün sonu hizasında (D'nin değeri D+1 sabahının sabitlemesi); USD/TRY "
                         "18.12.2023'ten İstanbul 18:00, öncesi Londra gece yarısı. 18.12.2023 öncesi cuma yayımlarının kur "
                         "değişimi hafta sonunu taşıdığı için boşaltıldı.")
    except bulut.VeriYok as h:
        tepki = oo.kurulmadi(f"TÜİK TÜFE yayım günleri elde yok ({h}); yalnız aylık ilişki kalır")
    ay = aylik_iliski()
    ay.pop("_z")
    return {
        "yontem": "TÜFE sürprizi her ay için gerçekleşen aylık TÜFE değişimi ile Piyasa Katılımcıları Anketi'nin "
                  "aynı ay beklentisinin farkıdır (puan); dağılımı, işaret dengesi ve piyasa tepkisi dönem dönem "
                  "ölçüldü.",
        "kaynak": ["enflasyon_aylik"],
        "n": int(len(sp)), "ilk": str(sp.index.min()), "son": str(sp.index.max()),
        "etiket_sinamasi": etiket_sinamasi(),
        "dagilim": dag,
        "kur_cokusu": cokus,
        "yayim_gunu": tepki,
        "aylik_iliski": ay,
    }


def sekil_05() -> dict:
    sp = surpriz_serisi()
    ay = aylik_iliski()["_z"]
    c = kur_cokus_gunleri()
    kayip = set(c[c["degisim_yuzde"] > 0].index.to_period("M"))
    kazanc = set(c[c["degisim_yuzde"] < 0].index.to_period("M"))
    out = {"baslik": "TÜFE sürprizi ve piyasa tepkisi, rejime göre", "birim": "sürpriz puan; DİBS bp; kur %",
           "n": int(len(sp)), "ilk": str(sp.index.min()), "son": str(sp.index.max()),
           "yontem": "Aylık TÜFE sürprizi (gerçekleşen − PKA beklentisi), aylık DİBS ve kur değişimi ve yayım günü "
                     "tepkisi, rejime göre.",
           "kaynak": ["enflasyon_aylik (TÜFE ve PKA cari ay beklentisi)", "dibs_egri_gunluk", "usdtry_yahoo_gunluk",
                      "bulut/tuik_takvim"],
           "surpriz": {"ay": [str(p) for p in sp.index], "deger_puan": _liste(sp["surpriz"]),
                       "rejim": list(sp["rejim"]),
                       "cokus_ayi": [bool(p in kayip) for p in sp.index],
                       "cokus_ertesi_ay": [bool((p - 1) in kayip) for p in sp.index],
                       "sert_deger_kazanci_ayi": [bool(p in kazanc) for p in sp.index],
                       "not": "çöküş ayı: TL'nin 4σ değer kaybettiği gün taşıyan ay; değer kazancı ayları ayrı işaretli"},
           "aylik": {"ay": [str(t.to_period("M")) for t in ay.index], "surpriz_puan": _liste(ay["surpriz"]),
                     "d_n2y_bp": _liste(ay["d_n2y"]), "d_usdtry_yuzde": _liste(ay["d_usdtry"]),
                     "rejim": list(ay["rejim"])},
           "rejimler": [[k, a, b, ad] for k, a, b, ad in DONEM_TUFE]}
    try:
        t = tufe_gunu_tepkisi(bulut.tufe_gunleri())
        gecen = [c for c in ("n2y", "n5y", "usdtry", "n1y") if t["kapi"][c]["gecti"]]
        out["yayim_gunu"] = {"kapiyi_gecen": gecen, **t["noktalar"],
                             "not": "Plasebo sınamasını geçmeyen serinin noktaları yalnız profil için durur; regresyon kurulmadı."}
    except bulut.VeriYok as h:
        out["yayim_gunu"] = oo.kurulmadi(f"TÜİK TÜFE yayım günleri elde yok ({h})")
    return out


# ═══════════════════════════════════════════════════════════════ p4b
DONEM_ABD = [("tum", "2000-01-01", "2026-09-30", "2000–2026"),
             ("d2000_2019", "2000-01-01", "2019-12-31", "2000–2019"),
             ("d2020_2026", "2020-01-01", "2026-09-30", "2020–2026")]


def abd_tufe_kovaryansi(yayim_gunleri) -> dict:
    """ABD TÜFE günlerinde Δ2y (bp) ile ΔUSD/EUR ve ΔUSD/JPY (%, dolar yönü)
    kovaryansı, yayım günü ile sıradan gün."""
    d = b3.abd_gunluk_degisim()[["us2", "usd_eur", "usd_jpy"]]
    r = b3.yayim_gunu_orani(d, yayim_gunleri, [("us2", "usd_eur"), ("us2", "usd_jpy")], DONEM_ABD, k_tohum=220)
    r["birim"] = "us2 baz puan; USD/EUR ve USD/JPY log değişim %, artış doların değer kazancı (EUR/USD yönü çevrildi)"
    r["saat"] = "ABD TÜFE 08:30 New York (15:30 TSİ); ABD Hazinesi kapanışı ve CNBC 17:00 New York aynı günü içerir."
    return r


def p4b() -> dict:
    base = {"yontem": "ABD TÜFE yayım günlerinde ve sıradan günlerde 2 yıllık getiri ile dolar kurlarının günlük "
                      "değişimlerinin varyansı ve kovaryansı karşılaştırıldı; sayısal beklenti olmadığı için sürpriz "
                      "hesaplanmaz.",
            "kaynak": ["abd_hazine_gunluk", "cnbc_kur_gunluk", "bulut/bls_takvim"]}
    try:
        return {**base, **abd_tufe_kovaryansi(bulut.abd_tufe_gunleri())}
    except bulut.VeriYok as h:
        return {**base, **oo.kurulmadi(f"BLS TÜFE yayım günleri elde yok ({h})")}


def sekil_06(p4b_sonuc: dict) -> dict:
    if p4b_sonuc.get("durum") == "kurulmadi":
        return {"baslik": "ABD TÜFE günü kovaryansı", **oo.kurulmadi(p4b_sonuc["sebep"]), "seriler": [],
                "n": 0, "ilk": None, "son": None}
    satir = []
    for k, _, _, ad in DONEM_ABD:
        r = p4b_sonuc.get(k, {})
        for cift in ("us2_usd_eur", "us2_usd_jpy"):
            v = r.get(f"kov_{cift}")
            if isinstance(v, dict) and v.get("durum") != "kurulmadi":
                satir.append({"donem": ad, "cift": cift, "kov_olay": v["kov_olay"], "kov_sakin": v["kov_sakin"],
                              "kor_olay": v["kor_olay"], "kor_sakin": v["kor_sakin"]})
    out = {"baslik": "ABD TÜFE günü kovaryansı", "birim": "bp × %", "seriler": satir, "n": len(satir),
           "ilk": DONEM_ABD[0][1], "son": DONEM_ABD[0][2],
           "yontem": "ABD TÜFE yayım günü ile sıradan günün 2 yıllık getiri × dolar kuru kovaryansı ve korelasyonu.",
           "kaynak": ["abd_hazine_gunluk", "cnbc_kur_gunluk", "bulut/bls_takvim"]}
    if not satir:
        kapi = p4b_sonuc.get("kapi", {})
        dusen = [c for c, k in kapi.items() if isinstance(k, dict) and not k.get("gecti")]
        okur = {"us2": "ABD 2 yıllık getiri", "usd_eur": "USD/EUR", "usd_jpy": "USD/JPY"}
        out.update(oo.kurulmadi("yayım günü kovaryansı kurulmadı: plasebo sınamasını geçmeyen seri "
                                + (", ".join(okur.get(c, c) for c in dusen) if dusen else "yok")))
    return out


# ═══════════════════════════════════════════════════════════════ p4c
def _asof(s: pd.Series, t) -> tuple:
    s = s.dropna()
    s = s[s.index <= t]
    return (s.index[-1], float(s.iloc[-1])) if len(s) else (None, None)


def p4c() -> dict:
    a, z = TR_2021
    dibs = oo.dibs(HIZA, ("n2y", "n5y"))                             # piyasa günü (gün sonu hizası)
    f = oo.oku("fonlama_gunluk")
    kur, _ = oo.usdtry()
    tc = oo.usdtry_tcmb()
    e = oo.oku("enflasyon_aylik")
    e.index = pd.PeriodIndex(e.index, freq="M")
    tr_yy = (e["tufe"] / e["tufe"].shift(12) - 1) * 100

    def satir(s, t0, t1):
        """Faiz düzeyi (%) ve değişimi (bp); 'ilk'/'son' gözlem günleridir."""
        g0, v0 = _asof(s, t0)
        g1, v1 = _asof(s, t1)
        return {"ilk": _iso(g0), "son": _iso(g1), "ilk_yuzde": _f(v0), "son_yuzde": _f(v1),
                "degisim_bp": _f((v1 - v0) * 100) if v0 is not None and v1 is not None else None}

    def yuzde(s, t0, t1):
        """Kur düzeyi ve değişimi (%); 'ilk'/'son' gözlem günleridir."""
        g0, v0 = _asof(s, t0)
        g1, v1 = _asof(s, t1)
        return {"ilk": _iso(g0), "son": _iso(g1), "ilk_duzey": _f(v0), "son_duzey": _f(v1),
                "degisim_yuzde": _f((v1 / v0 - 1) * 100), "log_degisim_yuzde": _f(math.log(v1 / v0) * 100)}

    pi0, pi1 = a.to_period("M"), z.to_period("M")
    pol = satir(f["politika"], a, z)
    tr = {
        "pencere": [_iso(a), _iso(z)],
        "politika": pol, "politika_degisim_bp": pol["degisim_bp"],
        "n2y": satir(dibs["n2y"], a, z), "n5y": satir(dibs["n5y"], a, z),
        "usdtry": yuzde(kur, a, z), "usdtry_tcmb_saglamlik": yuzde(tc, a, z),
        "yillik_tufe": {"ilk_ay": str(pi0), "son_ay": str(pi1), "ilk_yuzde": _f(tr_yy[pi0]),
                        "son_yuzde": _f(tr_yy[pi1]), "degisim_puan": _f(tr_yy[pi1] - tr_yy[pi0])},
        "reel_politika": {"ilk_puan": _f(pol["ilk_yuzde"] - tr_yy[pi0]), "son_puan": _f(pol["son_yuzde"] - tr_yy[pi1])},
        "birim": "getiri değişimi bp (DİBS gün sonu hizasında: D gününe D+2 iş günü etiketli değer); kur %",
    }
    a2, z2 = ABD_2022
    k = oo.oku("kuresel_aylik")
    fa = k["faiz_abd"].dropna()
    fa.index = pd.PeriodIndex(fa.index, freq="M")
    at = k["abd_tufe"].dropna()
    at.index = pd.PeriodIndex(at.index, freq="M")
    at_yy = (at / at.shift(12) - 1) * 100
    p0, p1 = a2.to_period("M") - 1, z2.to_period("M")     # dönem başında yürürlükteki: bir önceki ay sonu
    us = oo.oku("abd_hazine_gunluk")
    dol = oo.dolar_sepeti()["sepet"]
    dxy = oo.oku("yahoo_dxy_vix_gunluk")["dxy"]
    eur = oo.cnbc_kur()["eur"]
    dolar_g = {"ilk": _iso(_asof(dol, a2)[0]), "son": _iso(_asof(dol, z2)[0]),
               "log_degisim_yuzde": _f((_asof(dol, z2)[1] - _asof(dol, a2)[1]) * 100)}
    abd = {
        "pencere": [_iso(a2), _iso(z2)],
        "politika": {"ilk_ay": str(p0), "son_ay": str(p1), "ilk_yuzde": _f(fa[p0]), "son_yuzde": _f(fa[p1]),
                     "degisim_bp": _f((fa[p1] - fa[p0]) * 100)},
        "politika_degisim_bp": _f((fa[p1] - fa[p0]) * 100),
        "us2": satir(us["us2"], a2, z2), "us10": satir(us["us10"], a2, z2),
        "dolar_g10": dolar_g, "dxy_saglamlik": yuzde(dxy, a2, z2), "eurusd": yuzde(eur, a2, z2),
        "yillik_tufe": {"ilk_ay": str(p0), "son_ay": str(p1), "ilk_yuzde": _f(at_yy[p0]),
                        "son_yuzde": _f(at_yy[p1]), "degisim_puan": _f(at_yy[p1] - at_yy[p0])},
        "reel_politika": {"ilk_puan": _f(fa[p0] - at_yy[p0]), "son_puan": _f(fa[p1] - at_yy[p1])},
        "birim": "getiri değişimi bp; kur %; ABD politika faizi BIS tanımı, ay sonu",
    }
    return {
        "yontem": "İki dönemin başı ve sonu arasında politika faizi, 2 yıllık ve uzun vadeli getiri, kur ve yıllık "
                  "enflasyon değişimi yan yana kondu; iki gözlemli bir vaka tablosudur, test değildir.",
        "kaynak": ["fonlama_gunluk", "dibs_egri_gunluk", "usdtry_yahoo_gunluk", "usdtry_tcmb_gunluk", "enflasyon_aylik",
                   "kuresel_aylik", "abd_hazine_gunluk", "cnbc_kur_gunluk", "yahoo_dxy_vix_gunluk"],
        "n": 2, "ilk": _iso(a), "son": _iso(z2), "durum": "vaka tablosu",
        "turkiye_2021": tr, "abd_2022": abd,
        "not": "Türkiye'de uzun uç 5 yıl (10 yıllık düğüm arşivde yok), ABD'de 10 yıl. Dolar ölçüsü altı G10 "
               "kurunun eşit ağırlıklı sepetidir (CNBC New York 17:00); DXY sağlamlık. 31.12.2021 cumadır: o "
               "tarihteki Yahoo kuru 18.12.2023 öncesi sözleşmeyle pazartesi barının başındaki fiyattır, yani hafta "
               "sonunu da taşır; TCMB kuru sağlamlık için yan yana verilir.",
    }


# ═══════════════════════════════════════════════════════════════ giriş
def olc() -> dict:
    b = p4b()
    return oo.yuvarla({
        "p4a": p4a(),
        "p4b": b,
        "p4c": p4c(),
        "sekil_05": sekil_05(),
        "sekil_06": sekil_06(b),
    }, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.time()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"süre {time.time() - t0:.1f} sn")
