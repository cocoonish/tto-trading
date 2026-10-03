#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 2 (Veri günü mekaniği) ölçüm katmanı.

Pratik 2 — HİZA KAPISI. Bir olay çalışması ancak serinin tarih sözleşmesi
olay saatini doğru güne yazıyorsa kurulabilir. Ölçü: olay günlerinin −2…+2
iş günü kaymasında |Δ| ortalamasının, olay pencerelerinin dışındaki sıradan
günlerin |Δ| ortalamasına oranı (plasebo profili, `ortak_olc.olay_profili`).
Kapı: tepe 0'da ve oran[0] öbür dört kaymanın en büyüğünü aşıyor (`kapi()`).

Seriler ve saatleri
  DİBS n3a · n2y · n5y (bp)  TCMB gösterge değeri; görev tanımında "gün sonu" diye
             geçiyordu, ölçüm valör tarihli ve öğleden önce sabitlenmiş çıkardı (tuzak 1).
             Bu modül HAM etiketi sınar (`ortak_olc.dibs("ham")`); ölçtüğü hiza sabiti
             `ortak_olc.DIBS_KAYMA` (gun_sonu 2 · sabah 1) buradaki ölçüme karşı tutulur.
  USD/TRY (%) Yahoo: 18.12.2023'ten İstanbul 18:00; öncesinde Londra gece
             yarısı kapanışı, bir hafta içi geri yazılmış (`ortak_olc.usdtry`).
  USD/TRY TCMB (%) gösterge kuru; valör tarihi Türkiye iş günü takvimiyle bir gün
             geri alınmış (`ortak_olc.usdtry_tcmb`), sabitleme 14:00 öncesi (tuzak 2) —
             yalnız sağlamlık.
  ABD 2 yıllık (bp) ABD Hazinesi par getirisi, New York öğleden sonra.
  Dolar sepeti (%) CNBC altı G10 kuru, New York 17:00 (Bölüm 1'in tanımı).
Olay saatleri: PPK 14:00 TSİ · TÜFE 10:00 TSİ · ABD istihdam ve TÜFE 08:30 New
York (15:30 TSİ) · FOMC 14:00 New York. Hepsi gün sonu kapanışlarından önce;
TCMB sabitlemesinden ve DİBS gösterge değerinden önce DEĞİL.

Anket etiketi: PKA "cari ay" aylık TÜFE beklentisinin hangi aya ait olduğu,
gerçekleşen aylık TÜFE ile 0 ve ±1, ±2 ay kaydırmada sınanır.

ÖLÇÜLEREK BULUNAN TUZAKLAR
  1. DİBS EĞRİSİNİN ETİKETİ PİYASA GÜNÜNÜN İKİ İŞ GÜNÜ ÖNÜNDE. Gösterge
     değerleri TCMB gösterge kuru gibi VALÖR tarihlidir ve öğleden önceki
     sabitlemeden gelir. 2013–2021'de günlük değişimin sıra korelasyonu
     USD/TRY (Londra kapanışı) ile kaymasız 0,06, DİBS iki iş günü
     kaydırılınca 0,36–0,43; ZAR ve VIX ile de en yüksek korelasyon iki iş
     günü kaymada; TCMB'nin ilan günlü kuruyla bir iş günü kaymada (0,48–0,59).
     Örnek: 20.03.2021 cumartesi görevden alma, piyasa 22.03 pazartesi çöktü;
     5 yıllık pazartesi etiketinde 14,96 (değişmedi), salı 17,91, çarşamba
     20,17. PPK × DİBS sınaması bu yüzden kaymasız DÜŞÜYOR (tepe +2) ve 2 yıllık
     iki iş günü kaymada güçlü geçiyor. Ortak hiza sabiti
     (`ortak_olc.DIBS_KAYMA`: gün sonuna 2, sabah sabitlemesine 1) bu ölçüme karşı sınanır.
  2. TCMB GÖSTERGE KURU ÖĞLEDEN ÖNCE SABİTLENİYOR: PPK günü (14:00) ilanı kararı
     taşımıyor. 13.09.2018: önceki ilan 6,3945, karar günü ilanı 6,3566,
     ertesi gün 6,0659; Yahoo karar günü kapanışı 6,1287. PPK × TCMB tepe +1.
  3. VALÖRÜ TAKVİMSİZ BİR İŞ GÜNÜYLE GERİ ALMAK tatilden önceki ilanı TATİL gününe
     yazar (02.04.2025 valörlü kur 01.04.2025 bayramına; ilan 28.03.2025 cuma) ve
     2013–2026'da 88 iş gününü TCMB değeri olmadan bırakır. Bu ölçümden sonra
     `ortak_olc.usdtry_tcmb()` Türkiye iş günü takvimiyle geri alır (tutarlılık turu,
     02.10.2026); takvimsiz sürüm (`geri_alma="is_gunu"`) yalnız bu tuzağın ölçümü
     için yanında durur. YARIM GÜNDE İLAN YOK (doğrulama turu): bayram arifelerinde
     ve 28 Ekim'de TCMB ilan etmez, arşiv tatil sonrası valöre önceki ilanı tekrar
     yazar (15.04.2024 valörü 32,0060 = 08.04.2024 ilanı; 09.04 arifesinde ilan yok).
     Takvimle geri alınınca bu tekrar arifeye sıfır değişim olarak düşüyordu (TÜFE
     günü 03.10.2014, 04.07.2016, 03.06.2019 dahil); ortak sürüm o günleri boş bırakır.
  4. DİBS eğrisi Türkiye tatillerinde satır taşıyor (değişimi sıfır değil):
     bütün Türkiye serileri EVDS iş günü takvimine indirilir.
  5. HAFTANIN GÜNÜ ETKİSİ: PPK'ların 87/111'i perşembe, yani +1 kayması çoğunlukla
     cuma, −2 salı. 18.12.2023 sonrası Yahoo USD/TRY'de cuma |Δ| öbür günlerin
     iki katı (0,23 · 0,10–0,12 %), TCMB'de pazartesi |Δ| iki katı. Koşulsuz
     taban bu yüzden profili bozar; olay günü oranı, haftanın günü bileşimi
     aynı 1.000 rastgele gün kümesiyle kıyaslanır.
  6. KAPININ RASTGELE GEÇME OLASILIĞI ≈ %15–22: tepe beş kaymadan birine düşer.
     "Güçlü kural" ayrıca oran[0]'ın rastgele kümelerin %95'ini aşmasını ister.
  7. TÜFE × DİBS KAYMASIZ GEÇİŞİ SAATLE BAĞDAŞMIYOR. İlk yazımda bunun sebebi
     "ayın 2. iş gününde DİBS değişimi takvim gereği büyük" diye kondu; o ölçü
     DÖNGÜSELDİ: TÜFE her ay ayın 3'üne (ya da ertesi iş gününe) düştüğü için ayın
     k. iş gününün ortalaması TÜFE'nin kendisini içerir. Ayrıştırılmış ölçü (aylar
     TÜFE'nin düştüğü iş gününe göre gruplanır) takvim etkisi göstermiyor: TÜFE
     3. iş gününe düştüğü aylarda 2. iş günü sıradandır (2 yıllıkta 28,6 bp; genel
     27,5), TÜFE gününe göre göreli profil 2 ve 5 yıllıkta düz. Geçişin asıl
     çelişkisi saattedir: D etiketi D'den önceki iş gününün sabahki sabitlemesidir
     ve 10:00'daki TÜFE'yi taşıyamaz. Saatle bağdaşan kaymalar 1 ve 2'dir ve
     orada hiçbir DİBS serisi geçmiyor; 3 aylığın kaymasız p'si (0,04) beş seri ×
     iki olay arasında tesadüfle uyumlu ve düzeltilmiş tabanla 0,05'i aşıyor.
  8. FOMC takvimi plansız toplantı ve telekonferansları da taşır (170 günün 18'i);
     `bulut.fomc_gunleri(planli=True)` yalnız planlıları döndürür.
  9. RASTGELE KÜMENİN TABANI (denetim turu): gerçek olay profilinin tabanı olay
     pencerelerinin DIŞINDAKİ günlerdir, rastgele kümelerinki ise olay günlerini de
     içeriyordu. Olay günleri oynak olduğu için rastgele oranlar %2–5 düşük çıkıyor
     ve p değerleri olay lehine yanlıydı (USD/TRY × PPK rastgele medyanı 0,89 ·
     doğrusu 0,94; 3 aylık × TÜFE p 0,041 → 0,054). Rastgele kümelerin tabanından
     da olay pencereleri çıkarılır.
 10. YÖNETİLEN KUR DÖNEMİ HAVUZA GİRİYORDU: kur serilerinin (USD/TRY, TCMB) bütün
     satırları 2021-12…2023-06'yı da kapsıyordu; sözleşme gereği bu dönem kur
     tepkisinde ayrıdır. Havuz USD/TRY × PPK profilinin +2 kaymasını şişiriyordu
     (havuz 1,42 · dönem dışı 1,12 · dönem içi 19 olayda 2,92). Kur satırları
     dönemi dışarıda bırakır, dönemin içi `yonetilen_kur_donemi`nde ayrı durur.
 11. SAAT TUTARLILIĞI: tepe sıfırda olsa bile geçiş, serinin ölçülmüş saatiyle
     bağdaşmıyorsa tesadüftür. Her serinin gün sonu kapanışına göre öncülüğü
     bütün günlerden ölçülür (`_saat_onculugu`: DİBS 2 · TCMB 1 · Yahoo ve ABD
     0); 14:00 sonrası olayda beklenen kayma bu öncülük, 10:00 olayında (TÜFE)
     sabitlemenin 10:00'a göre saati ölçülmediği için iki komşu kayma. Olay
     çalışması (`kurulabilir`, `kapi(..., guclu=True)`) güçlü kuralı VE saati ister.
 12. İKİ YARI SINAMASI bütün seriyle kuruluyordu: taban öbür yarının oynaklığını
     taşıyor, oranlar 1'e göre okunamıyordu (DİBS'te ilk yarı her kaymada < 1, son
     yarı > 1,8). Tepe değişmiyordu; oranlar artık her yarının kendi penceresinde.
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import olcum_b01 as b01
import ortak_olc as oo
import bicim  # noqa: E402  (ortak/; yolu ortak_olc ekler) — okura giden sayı tek sözleşmeden

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

PENCERE = oo.OLAY_PENCERE          # 2
K_RASTGELE = oo.OLAY_RASTGELE_K    # 1000
TOHUM = oo.OLAY_TOHUM              # 20261002
GECIS = oo.GECIS_YAHOO_CUMA                # 2023-12-18, tek tanım ortak_olc'de
DIBS_SERILER = ("n3a", "n2y", "n5y")
KAYMA_TARAMA = (0, 1, 2, 3)
KAYMA_CAPRAZ = (-1, 0, 1, 2, 3)
_FOMC_DENETIM: dict = {}

SERI_BIRIM = {"n3a": "bp", "n2y": "bp", "n5y": "bp", "usdtry": "yuzde", "usdtry_tcmb": "yuzde",
              "us2": "bp", "dolar_sepeti": "yuzde"}
SERI_AD = {"n3a": "DİBS 3 ay sıfır kuponlu getiri", "n2y": "DİBS 2 yıl sıfır kuponlu getiri",
           "n5y": "DİBS 5 yıl sıfır kuponlu getiri", "usdtry": "USD/TRY (Yahoo)",
           "usdtry_tcmb": "USD/TRY (TCMB gösterge, sağlamlık)", "us2": "ABD 2 yıllık getiri",
           "dolar_sepeti": "eşit ağırlıklı G10 dolar sepeti"}
_DIBS_SAAT = "gösterge değeri, valör tarihli; etiket gün sonu piyasasının iki iş günü önünde"
SERI_SAAT = {"n3a": _DIBS_SAAT, "n2y": _DIBS_SAAT, "n5y": _DIBS_SAAT,
             "usdtry": "18.12.2023'ten İstanbul 18:00, öncesi Londra gece yarısı",
             "usdtry_tcmb": "TCMB ilanı, valör Türkiye iş günü takvimiyle bir gün geri; sabitleme 14:00 öncesi",
             "us2": "New York öğleden sonra", "dolar_sepeti": "New York 17:00"}
TR_SERILER = ("n3a", "n2y", "n5y", "usdtry", "usdtry_tcmb")
ABD_SERILER = ("us2", "dolar_sepeti")
OLAY_AD = {"ppk": "PPK karar günü (14:00 TSİ)", "tufe": "TÜİK TÜFE yayımı (10:00 TSİ)",
           "abd_istihdam": "ABD istihdam raporu (08:30 New York)", "abd_tufe": "ABD TÜFE (08:30 New York)",
           "fomc": "planlı FOMC kararı (14:00 New York)"}


# ───────────────────────────────────────────────────────── seriler
def _tr_takvim() -> pd.DatetimeIndex:
    return oo.tr_takvim()


@lru_cache(maxsize=1)
def _tr_degisim() -> pd.DataFrame:
    """Türkiye serilerinin günlük değişimi (`ortak_olc.tr_gunluk_degisim`, HAM DİBS
    etiketi; sütun başına Türkiye iş günü takviminde). `usdtry_tcmb_takvimsiz`
    yalnız tuzak 3'ün ölçümüdür: valörü takvimsiz iş günüyle geri alınmış kur."""
    d = oo.tr_gunluk_degisim("ham", DIBS_SERILER, kur=True, tcmb=True)
    t0 = oo.usdtry_tcmb(geri_alma="is_gunu").reindex(d.index)
    d["usdtry_tcmb_takvimsiz"] = np.log(t0).diff() * 100.0
    return d.iloc[1:]


@lru_cache(maxsize=1)
def _abd_degisim() -> pd.DataFrame:
    g = oo.abd_gunluk_degisim()
    d = pd.DataFrame({"us2": g["us2_bp"], "dolar_sepeti": g["dolar_yuzde"]})
    return d[d.index >= b01.ILK_GUN]


def _seri(ad: str) -> pd.Series:
    for df in (_tr_degisim(), _abd_degisim()):
        if ad in df.columns:
            return df[ad]
    raise KeyError(f"tanımsız seri: {ad} (geçerli: {', '.join(list(_tr_degisim().columns) + list(_abd_degisim().columns))})")


# ───────────────────────────────────────────────────────── yönetilen kur (tuzak 10)
KUR_SERILER = ("usdtry", "usdtry_tcmb", "usdtry_tcmb_takvimsiz")
YONETILEN = oo.YONETILEN


def _kok(seri: str) -> str:
    return seri.split(":")[0]


def _yonetilen_disi(s: pd.Series, olaylar: pd.DatetimeIndex) -> tuple[pd.Series, pd.DatetimeIndex, int]:
    """Kur serisinden yönetilen kur dönemini çıkarır (`ortak_olc.donem_disi`)."""
    return oo.donem_disi(s, pd.DatetimeIndex(olaylar), YONETILEN, PENCERE)


# ───────────────────────────────────────────────────────── saat tutarlılığı (tuzak 11)
OLAY_SAAT_SINIFI = {"ppk": "ogleden_sonra", "tufe": "sabah", "fomc": "abd", "abd_istihdam": "abd", "abd_tufe": "abd"}


@lru_cache(maxsize=1)
def _saat_onculugu() -> dict:
    """Her serinin etiketinin, gün sonu kapanışına (Yahoo USD/TRY, saati bilinen
    referans) göre kaç iş günü ÖNDE olduğu — ÖLÇÜLÜR, varsayılmaz: bütün
    günlerde (olaylar değil) k iş günü kaydırılmış sıra korelasyonunun tepesi,
    2013–2021 (yönetilen kur ve İstanbul 18:00 geçişinden önce). TCMB kuru ile
    DİBS aynı sabitleme saatini paylaştığı için DİBS'in TCMB'ye göre öncülüğü de
    yazılır. ABD serileri ve Yahoo kuru gün sonu kapanışıdır (0)."""
    d = _tr_degisim().loc["2013-01-01":str((YONETILEN[0] - pd.Timedelta(days=1)).date())]
    y = d["usdtry"]
    out = {"usdtry": 0, "us2": 0, "dolar_sepeti": 0}
    kor_tcmb = {k: float(y.corr(d["usdtry_tcmb"].shift(-k), method="spearman")) for k in KAYMA_CAPRAZ}
    out["usdtry_tcmb"] = int(max(kor_tcmb, key=kor_tcmb.get))
    out["usdtry_tcmb_takvimsiz"] = out["usdtry_tcmb"]
    kor = {}
    for s_ in DIBS_SERILER:
        kor[s_] = {k: float(d[s_].shift(-k).corr(y, method="spearman")) for k in KAYMA_CAPRAZ}
        out[s_] = int(max(kor[s_], key=kor[s_].get))
    return {"oncu": out, "kor_tcmb_yahoo": kor_tcmb, "kor_dibs_yahoo": kor,
            "ilk": str(d.index.min().date()), "son": str(d.index.max().date())}


def _beklenen_kaymalar(seri: str, olay: str) -> list:
    """Olay saatiyle serinin ölçülmüş saati bağdaşan kaymalar. 14:00 TSİ sonrası
    olay (PPK) ve ABD olayları: etiketin öncülüğü L. 10:00 TSİ olay (TÜFE):
    sabitleme saati 10:00'a göre ölçülmediği için {L−1, L}."""
    L = _saat_onculugu()["oncu"].get(_kok(seri))
    if L is None:
        return []
    sinif = OLAY_SAAT_SINIFI.get(olay.split("_kayma")[0], "ogleden_sonra")
    if sinif == "sabah":
        return sorted({k for k in (L - 1, L) if k >= 0})
    return [L]


# ───────────────────────────────────────────────────────── olaylar
def _ppk() -> tuple[pd.DatetimeIndex, dict]:
    p = oo.oku("ppk_kararlari")
    idx = pd.DatetimeIndex(p.index).normalize()
    denet = {
        "satir": int(len(p)), "tekil_gun": int(idx.nunique()),
        "ayni_gun_iki_satir": int(idx.duplicated().sum()),
        "hafta_sonu": int((idx.dayofweek >= 5).sum()),
        "gun_dagilimi": {g: int(v) for g, v in zip(("pzt", "sal", "car", "per", "cum"),
                                                   [(idx.dayofweek == i).sum() for i in range(5)])},
        "en_kisa_aralik_gun": int(np.diff(idx.sort_values().values).astype("timedelta64[D]").astype(int).min()),
        "ilk": str(idx.min().date()), "son": str(idx.max().date()),
    }
    return pd.DatetimeIndex(sorted(set(idx))), denet


def _olaylar() -> dict:
    """{olay: DatetimeIndex} ya da {olay: VeriYok mesajı (str)}."""
    out: dict = {}
    out["ppk"], _ = _ppk()
    for ad, f in (("tufe", bulut.tufe_gunleri), ("abd_istihdam", bulut.abd_istihdam_gunleri),
                  ("abd_tufe", bulut.abd_tufe_gunleri), ("fomc", _fomc_planli)):
        try:
            out[ad] = pd.DatetimeIndex(f()).normalize()
        except bulut.VeriYok as e:
            out[ad] = str(e)
    return out


def _fomc_planli() -> pd.DatetimeIndex:
    """Planlı FOMC karar günleri (`bulut.fomc_gunleri(planli=True)`); denetim
    satırı plansızlarla birlikte bütün kayıtları sayar."""
    tum = bulut.fomc_gunleri(planli=False)
    planli = bulut.fomc_gunleri(planli=True)
    _FOMC_DENETIM.update({"toplam": int(len(tum)), "planli": int(len(planli)),
                          "plansiz_ayiklanan": int(len(tum) - len(planli)),
                          "ilk": str(tum.min().date()), "son": str(tum.max().date())})
    return planli


OLAY_SERI = {"ppk": TR_SERILER, "tufe": TR_SERILER,
             "abd_istihdam": ABD_SERILER, "abd_tufe": ABD_SERILER, "fomc": ABD_SERILER}


# ───────────────────────────────────────────────────────── profil ve kapı
# Kapının makinesi (plasebo profili, gün eşlemeli rastgele kümeler, dönem dışlama)
# `ortak_olc.olay_kapisi`dedir; bu modül onun tablo satırlarını kurar ve saati sınar.
_kapi_hukmu = oo.kapi_hukmu
_konumlar = oo._konumlar


def _profil_satiri(seri: str, olay: str, s: pd.Series, olaylar: pd.DatetimeIndex, k_tohum: int,
                   ilk: str | None = None, son: str | None = None, kayma: int = 0,
                   yonetilen: str = "haric") -> dict:
    """Bir seri × olay satırı. `kayma` k: olay gününe serinin k iş günü SONRAKİ
    değişimi yazılır (tarih sözleşmesi taraması).

    `yonetilen`: kur serilerinde (USD/TRY, TCMB) yönetilen kur dönemi ayrı
    dönemdir ve havuza katılmaz — "haric" (öntanımlı) dönemi çıkarır, "yalniz"
    yalnız dönemin içini ölçer. Kur dışı serilerde (DİBS, ABD) yok sayılır."""
    s = s.dropna()
    if kayma:
        s = s.shift(-kayma).dropna()
    kur = _kok(seri) in KUR_SERILER
    k = oo.olay_kapisi(s, olaylar, guclu=True, pencere=PENCERE, k_tohum=k_tohum, ilk=ilk, son=son,
                       haric=YONETILEN if (kur and yonetilen == "haric") else None,
                       yalniz=YONETILEN if (kur and yonetilen == "yalniz") else None)
    beklenen = _beklenen_kaymalar(seri, olay)
    saat_ok = bool(int(kayma) in beklenen)
    return {
        "seri": seri, "olay": olay, "kayma": int(kayma), "durum": "olculdu", "kapi": k["kapi"],
        "kapi_guclu": k["kapi_guclu"],
        "saat_beklenen_kayma": beklenen, "saat_tutarli": saat_ok,
        # olay çalışması ancak istatistik (güçlü kural) VE saat birlikte izin verirse kurulur
        "kurulabilir": bool(k["kapi_guclu"] and saat_ok),
        "yonetilen_kur": (("hariç" if yonetilen == "haric" else "yalnız dönem içi") if kur else "uygulanmaz"),
        "yonetilen_siniri_dusen_olay": int(k["donem_siniri_dusen_olay"]),
        "oran": {kk: float(v) for kk, v in k["oran"].items()}, "tepe": k["tepe"],
        "oran0": k["oran0"], "oteki_azami": k["oteki_azami"], "oran0_fazlasi": k["oran0_fazlasi"],
        "rastgele_ort_profil": k["rastgele_ort_profil"], "gun_etkisinden_arindirilmis": k["gun_etkisinden_arindirilmis"],
        "arindirilmis_tepe": k["arindirilmis_tepe"],
        "p_rastgele_oran0": k["p_rastgele_oran0"], "p_rastgele_kapi_farki": k["p_rastgele_kapi_farki"],
        "p_rastgele_hata": k["p_rastgele_hata"], "guclu_sinirda": k["guclu_sinirda"],
        "kapi_rastgele_gecme_orani": k["kapi_rastgele_gecme_orani"],
        "n_olay": k["n_olay"], "n_olay_listede": k["n_olay_listede"],
        "taban_abs": float(k["taban_abs"]), "birim": SERI_BIRIM.get(seri.split(":")[0], ""),
        "gun_eslemeli_kiyas": k["gun_eslemeli_kiyas"],
        "ilk": k["ilk"], "son": k["son"],
    }


@lru_cache(maxsize=1)
def _tablo() -> tuple[list, dict]:
    olaylar = _olaylar()
    satirlar, k = [], 0
    for olay, seriler in OLAY_SERI.items():
        ev = olaylar[olay]
        for seri in seriler:
            k += 1
            if isinstance(ev, str):
                satirlar.append({"seri": seri, "olay": olay, "kayma": 0, "durum": "kurulmadi", "kapi": None,
                                 "kapi_guclu": None, "sebep": ev})
                continue
            r = _profil_satiri(seri, olay, _seri(seri), ev, k)
            r["uyari"] = _uyarilar(seri, olay)
            satirlar.append(r)
    return satirlar, olaylar


def _uyarilar(seri: str, olay: str) -> list:
    u = []
    if seri in DIBS_SERILER:
        u.append("DİBS gösterge eğrisinin etiketi gün sonu piyasasının iki iş günü önündedir (tarih "
                 "sözleşmesi bölümü); kaymasız profil olay gününü ölçmez")
    if seri in DIBS_SERILER and olay == "tufe":
        u.append("kaymasız satır olay gününü ölçemez: D etiketi D'den önceki iş gününün sabahki "
                 "sabitlemesidir ve 10:00'daki TÜFE'yi taşıyamaz; saatle bağdaşan kaymalar 1 ve 2 iş "
                 "günüdür (tarih sözleşmesi bölümündeki ay içi tablo, TÜFE'nin hangi iş gününe düştüğüne "
                 "göre ayrılmış ölçüdür)")
    if seri == "usdtry_tcmb" and olay in ("ppk", "fomc", "abd_istihdam", "abd_tufe"):
        u.append("TCMB gösterge kuru öğleden önceki sabitlemeden gelir; 14:00 sonrası olay ertesi günün ilanına düşer")
    return u


def kayma_onerisi(seri: str, olay: str = "ppk") -> int | None:
    """PPK kayma taramasında güçlü kuralı geçen EN KÜÇÜK kayma (iş günü); yoksa None."""
    for k in KAYMA_TARAMA:
        r = _kaymali_satir(seri, olay, k)
        if r.get("kapi_guclu"):
            return int(k)
    return None


@lru_cache(maxsize=None)
def _kaymali_satir(seri: str, olay: str, kayma: int) -> dict:
    ev = _olaylar()[olay]
    if isinstance(ev, str):
        return {"seri": seri, "olay": olay, "kayma": kayma, "durum": "kurulmadi", "kapi": None,
                "kapi_guclu": None, "sebep": ev}
    return _profil_satiri(seri, olay, _seri(seri), ev, 300 + 10 * kayma + len(seri), kayma=kayma)


def kapi(seri, olay=None, pencere: int = PENCERE, kayma: int = 0, guclu: bool = False) -> bool:
    """Hiza sınaması.

    kapi("n2y", "ppk")            → tablodaki hüküm (kurulmamış satır False döner);
    kapi("n2y", "ppk", kayma=2)   → olay gününe serinin 2 iş günü sonraki değişimi yazılarak;
    kapi(..., guclu=True)         → olay çalışması KURULABİLİR mi: ayrıca oran[0], haftanın günü
                                     eşlemeli 1.000 rastgele kümenin %95'inden yüksek VE kayma,
                                     serinin ölçülmüş saatinin olay saatiyle bağdaştığı kaymalardan
                                     biri (`saat_beklenen_kayma`; tuzak 11) — saatle bağdaşmayan bir
                                     geçiş tesadüftür;
    kapi(degisim_serisi, gunler)  → aynı kural doğrudan hesaplanır (`ortak_olc.olay_kapisi`;
                                     guclu=True ise gün eşlemeli rastgele kıyas dahil, saat
                                     çağıranın hizasındadır).
    Kural: plasebo profilinin tepesi 0'da ve oran[0] öbür kaymaların en büyüğünü aşıyor.
    Kur serilerinde yönetilen kur dönemi (oo.YONETILEN) havuza girmez."""
    if isinstance(seri, str):
        if kayma == 0:
            r = next((x for x in _tablo()[0] if x["seri"] == seri and x["olay"] == olay), None)
            if r is None:
                r = _kaymali_satir(seri, olay, 0)
        else:
            r = _kaymali_satir(seri, olay, int(kayma))
        return bool(r.get("kurulabilir") if guclu else r.get("kapi"))
    return bool(oo.olay_kapisi(seri, olay, guclu=guclu, pencere=pencere)["gecti"])


# ───────────────────────────────────────────────────────── tarih sözleşmesi
def _capraz(dibs: pd.DataFrame, x: pd.Series, a: str, b: str) -> dict:
    z = dibs.loc[a:b]
    xx = x.reindex(z.index).loc[a:b]
    out = {}
    for s_ in DIBS_SERILER:
        kor = {str(k): float(z[s_].shift(-k).corr(xx, method="spearman")) for k in KAYMA_CAPRAZ}
        out[s_] = {"korelasyon": kor, "en_yuksek_kayma": int(max(kor, key=lambda k: kor[k])),
                   "n": int(pd.concat([z[s_], xx], axis=1).dropna().shape[0])}
    return out


_SERI_KISA = {"n3a": "3 aylık", "n2y": "2 yıllık", "n5y": "5 yıllık", "usdtry_tcmb": "TCMB kuru", "usdtry": "USD/TRY"}


def _oneri_ppk_cumlesi() -> str:
    """PPK kayma taramasının ölçülmüş saatle karşılaştırması, veriden cümle."""
    L = _saat_onculugu()["oncu"]
    ayni, gec, yok = [], [], []
    for s_ in DIBS_SERILER + ("usdtry_tcmb", "usdtry"):
        k = kayma_onerisi(s_, "ppk")
        if k is None:
            yok.append(_SERI_KISA[s_])
        elif k == L[s_]:
            ayni.append(_SERI_KISA[s_])
        else:
            gec.append(f"{_SERI_KISA[s_]} {k}")
    parca = []
    if ayni:
        parca.append("PPK taramasında güçlü kural ölçülen saatte geçiyor: " + ", ".join(ayni))
    if gec:
        parca.append("başka kaymada geçen (iş günü): " + ", ".join(gec))
    if yok:
        parca.append("hiçbir kaymada güçlü geçmeyen: " + ", ".join(yok))
    return "; ".join(parca) + "."


def tarih_sozlesmesi() -> dict:
    d = _tr_degisim()
    vix = oo.oku("yahoo_dxy_vix_gunluk")["vix"].dropna().diff()
    zar = np.log(oo.em_kur("zar")).diff() * 100.0
    olcu = {
        "usdtry_tcmb_ilan": ("TCMB gösterge kuru, ilan günü (sabitleme öğleden önce)", d["usdtry_tcmb"]),
        "usdtry_yahoo": ("USD/TRY Yahoo kapanışı (Londra gece yarısı / İstanbul 18:00)", d["usdtry"]),
        "vix": ("VIX, New York kapanışı", vix),
        "zar": ("USD/ZAR Yahoo, Londra gece yarısı", zar),
    }
    capraz = {}
    for ad, (aciklama, x) in olcu.items():
        capraz[ad] = {"aciklama": aciklama,
                      "2013-2021": _capraz(d, x, "2013-01-01", "2021-12-31"),
                      "2022-2026": _capraz(d, x, "2022-01-01", "2026-09-30")}
    # PPK kayma taraması: olay gününe k iş günü sonraki değişim
    tarama = {}
    for seri in DIBS_SERILER + ("usdtry_tcmb", "usdtry"):
        tarama[seri] = [{k_: r[k_] for k_ in ("kayma", "kapi", "kapi_guclu", "saat_tutarli", "kurulabilir", "tepe",
                                              "oran0", "oteki_azami", "p_rastgele_oran0", "arindirilmis_tepe",
                                              "n_olay", "yonetilen_kur")} | {"oran": r["oran"]}
                        for r in (_kaymali_satir(seri, "ppk", k) for k in KAYMA_TARAMA)]
    # iki yarıda tepe (seçimin kararlılığı). Her yarının serisi kendi olay penceresiyle
    # sınırlı (tuzak 12): bütün seriyle kurulunca taban öbür yarının oynaklığını taşıyor ve
    # oranlar 1'e göre okunamıyordu (DİBS'te ilk yarı her kaymada < 1, son yarı > 1,8).
    ppk = _olaylar()["ppk"]
    orta = ppk[len(ppk) // 2]
    yari = {}
    for seri in DIBS_SERILER + ("usdtry_tcmb",):
        yari[seri] = {}
        for ad, ev in (("ilk_yari", ppk[ppk < orta]), ("son_yari", ppk[ppk >= orta])):
            r = _profil_satiri(seri, "ppk", _seri(seri), ev, 700 + len(seri) + (0 if ad == "ilk_yari" else 1))
            yari[seri][ad] = {"n_olay": r["n_olay"], "tepe": r["tepe"], "oran": r["oran"],
                              "p_rastgele_oran0": r["p_rastgele_oran0"], "yonetilen_kur": r["yonetilen_kur"],
                              "ilk": r["ilk"], "son": r["son"]}
    # ay içi iş günü etkisi. TÜFE her ay ayın 3'üne (ya da ertesi iş gününe) düştüğü için
    # "ayın k. iş günü" ortalaması TÜFE'nin kendi etkisini içerir ve takvim etkisini ondan
    # ayıramaz (tuzak 7). Ayırmanın yolu: TÜFE'nin ayın kaçıncı iş gününe düştüğüne göre aylar
    # gruplanır; etki takvimden geliyorsa aynı iş günü her grupta büyük, olaydan geliyorsa
    # büyüklük TÜFE gününü izler.
    idx = d.index
    ig = pd.Series(idx.to_series().groupby([idx.year, idx.month]).cumcount().values + 1, index=idx)
    tufe = _olaylar()["tufe"]
    ay_ici = {"tum_gunler_abs_bp": {s_: float(d[s_].abs().mean()) for s_ in DIBS_SERILER}}
    if not isinstance(tufe, str):
        tp = tufe[tufe.isin(idx)]
        ay_ici["tufe_ay_ici_is_gunu"] = {str(k_): int(v_) for k_, v_ in ig.loc[tp].value_counts().sort_index().items()}
        tufe_ig = pd.Series(ig.loc[tp].values, index=pd.PeriodIndex(tp, freq="M"))
        ay_tufe = pd.Series(tufe_ig.reindex(pd.PeriodIndex(idx, freq="M")).values, index=idx)
        rel = ig - ay_tufe
        grup, goreli = {}, {}
        for s_ in DIBS_SERILER:
            a_ = d[s_].abs()
            grup[s_] = {f"tufe_{int(g)}_is_gununde": {str(i): float(a_[(ay_tufe == g) & (ig == i)].mean())
                                                      for i in range(1, 6)}
                        for g in sorted(ay_tufe.dropna().unique()) if (ay_tufe == g).sum() >= 200}
            goreli[s_] = {str(k_): float(a_[rel == k_].mean()) for k_ in range(-2, 4)}
        ay_ici["tufe_gunune_gore_gruplu_abs_bp"] = grup
        ay_ici["tufe_gunune_gore_goreli_abs_bp"] = goreli
        ay_ici["okuma"] = ("Aylar TÜFE'nin düştüğü iş gününe göre gruplandı: bir iş günü yalnız TÜFE o güne "
                           "düştüğü aylarda büyük çıkıyorsa etki takvimden değil olaydan gelir; TÜFE gününe göre "
                           "göreli ortalama da bu yüzden ayrıca verildi.")
        ay_ici["tufe_kayma_taramasi"] = [{k_: r[k_] for k_ in ("kayma", "kapi", "kapi_guclu", "saat_tutarli",
                                                               "kurulabilir", "tepe", "oran0",
                                                               "p_rastgele_oran0")} | {"seri": s_}
                                         for s_ in DIBS_SERILER for r in (_kaymali_satir(s_, "tufe", k) for k in (0, 1, 2))]
    # sonuç
    yah = capraz["usdtry_yahoo"]["2013-2021"]
    tcm = capraz["usdtry_tcmb_ilan"]["2013-2021"]
    yahoo_onculuk = sorted({yah[s_]["en_yuksek_kayma"] for s_ in ("n2y", "n5y")})
    tcmb_onculuk = sorted({tcm[s_]["en_yuksek_kayma"] for s_ in ("n2y", "n5y")})
    sabit = dict(oo.DIBS_KAYMA)
    ornek = {}
    g = b01._tr_gunluk()
    for t in ("2021-03-19", "2021-03-22", "2021-03-23", "2021-03-24"):
        T = pd.Timestamp(t)
        if T in g.index:
            ornek[t] = {"n5y": float(g.loc[T, "n5y"]), "usdtry_tcmb": float(oo.usdtry_tcmb().get(T, np.nan))}
    return {
        "capraz_korelasyon": capraz, "ppk_kayma_taramasi": tarama, "ppk_yarilar": yari,
        "ay_ici_gun_etkisi": ay_ici,
        "guclu_kapi_icin_en_kucuk_kayma": {s_: kayma_onerisi(s_, "ppk") for s_ in DIBS_SERILER + ("usdtry_tcmb", "usdtry")},
        "dibs_etiket_onculugu_yahooya_gore_is_gunu": yahoo_onculuk,
        "dibs_etiket_onculugu_tcmb_ilanina_gore_is_gunu": tcmb_onculuk,
        "ortak_hiza_sabiti": {"gun_sonu": sabit["gun_sonu"], "sabah": sabit["sabah"]},
        "ortak_hiza_sabiti_tutarli": bool(yahoo_onculuk == [sabit["gun_sonu"]] and tcmb_onculuk == [sabit["sabah"]]),
        "ornek_hafta_sonu_soku": {"aciklama": "20.03.2021 cumartesi merkez bankası başkanı görevden alındı; "
                                              "piyasa pazartesi 22.03'te açıldı",
                                  "degerler": ornek},
        "sonuc": ("DİBS gösterge eğrisinin günü, TCMB gösterge kuru gibi VALÖR günüdür ve fiyat öğleden önceki "
                  "sabitlemeden gelir: etiket X'in değeri X'ten bir iş günü önceki ilan anının piyasasını "
                  "taşır. Gün sonu kapanışlarına (USD/TRY, VIX, ZAR) göre iki iş günü öndedir; 14:00'teki PPK "
                  "kararı etiketin iki iş günü sonrasında görünür."),
        "saat_onculugu": _saat_onculugu(),
        "oneri": {"ogleden_sonra_olayi_icin_kayma_is_gunu": {s_: int(L) for s_, L in _saat_onculugu()["oncu"].items()
                                                             if s_ in DIBS_SERILER + ("usdtry_tcmb", "usdtry")},
                  "sabah_olayi_icin_kayma_is_gunu": {s_: _beklenen_kaymalar(s_, "tufe")
                                                     for s_ in DIBS_SERILER + ("usdtry_tcmb", "usdtry")},
                  "aciklama": "14:00 ve sonrasındaki bir olayın tepkisi için olay gününe kaç iş günü sonraki etiketin "
                              "değişimi yazılır; değer, bütün günlerde gün sonu kapanışıyla sıra korelasyonunun "
                              "tepesinden okunur (2013–2021, yönetilen kur öncesi). 10:00'daki bir olay için "
                              "sabitleme saati 10:00'a göre ölçülemediği için iki komşu kayma birlikte verilir. "
                              + _oneri_ppk_cumlesi()},
        "yontem": "DİBS getirilerinin günlük değişimi, saatleri bilinen dört serinin değişimiyle k iş günü "
                  "kaydırılarak sıra korelasyonuyla karşılaştırıldı; PPK profili 0–3 iş günü kaydırılarak "
                  "yeniden kuruldu ve olay listesi iki yarıya bölünerek tepe kararlılığı sınandı.",
        "kaynak": ["dibs_egri_gunluk", "usdtry_yahoo_gunluk", "usdtry_tcmb_gunluk", "yahoo_dxy_vix_gunluk",
                   "em_kur_yahoo_gunluk", "ppk_kararlari"],
    }


# ───────────────────────────────────────────────────────── pratik 2
def p2() -> dict:
    satirlar, olaylar = _tablo()
    _, ppk_denet = _ppk()
    ppk = olaylar["ppk"]

    # KONTROL: sıradan günler (PPK pencereleri dışından, düzgün dağılımlı, sabit tohum)
    kontrol = []
    for i, seri in enumerate(TR_SERILER + ABD_SERILER):
        s = _seri(seri).dropna()
        ev = ppk if seri in TR_SERILER else pd.DatetimeIndex([])
        if seri in KUR_SERILER:
            s, ev, _ = _yonetilen_disi(s, ev)
        n_olay = len(_konumlar(s, ev)) if seri in TR_SERILER else len(ppk)
        rd = oo.rastgele_profil(s, ev, 500 + i, gun_eslemeli=False, n_olay=n_olay, pencere=PENCERE, k=K_RASTGELE)
        ornek = oo.olay_profili(s, rd["ornek_kume"], PENCERE)
        kontrol.append({
            "seri": seri, "n_gun_kume": int(n_olay), "kume_sayisi": K_RASTGELE,
            "ornek_kume_profili": {k: float(v) for k, v in ornek["oran"].items()},
            "ornek_kume_kapi": _kapi_hukmu(ornek),
            "ort_profil": {str(k): float(v) for k, v in zip(range(-PENCERE, PENCERE + 1), rd["ort_profil"])},
            "kapi_rastgele_gecme_orani": float(rd["kapi"].mean()),
            "oran0_medyan": float(np.median(rd["oran0"])),
            "oran0_yuzdelik_95": float(np.quantile(rd["oran0"], 0.95)),
            "oran0_yuzdelik_99": float(np.quantile(rd["oran0"], 0.99)),
            "yonetilen_kur": "hariç" if seri in KUR_SERILER else "uygulanmaz",
            "ilk": str(s.index.min().date()), "son": str(s.index.max().date()),
            "yontem": "PPK pencerelerinin dışındaki günlerden, sabit tohumla, PPK sayısı kadar günlük 1.000 "
                      "rastgele küme çekildi ve her kümenin profili aynı kuralla kuruldu.",
        })

    # alt dönemler: Yahoo'nun iki tanımı ve TCMB, PPK günlerinde
    alt = []
    for seri in ("usdtry", "usdtry_tcmb", "n2y"):
        for ad, a, b in (("gecis_oncesi", None, str((GECIS - pd.Timedelta(days=1)).date())),
                         ("gecis_sonrasi", str(GECIS.date()), None)):
            alt.append(_profil_satiri(f"{seri}:{ad}", "ppk", _seri(seri), ppk, 900 + len(alt), a, b))

    # yönetilen kur dönemi: kur serilerinde ayrı dönem, yalnız dönemin içi (havuza girmez)
    yonetilen = []
    for j_, (seri, olay) in enumerate((("usdtry", "ppk"), ("usdtry_tcmb", "ppk"), ("usdtry", "tufe"), ("usdtry_tcmb", "tufe"))):
        ev = olaylar[olay]
        if isinstance(ev, str):
            yonetilen.append({"seri": seri, "olay": olay, "durum": "kurulmadi", "sebep": ev})
            continue
        r = _profil_satiri(f"{seri}:yonetilen_kur", olay, _seri(seri), ev, 960 + j_, yonetilen="yalniz")
        r["not"] = "olay sayısı 10'dan az olabilir; profil vaka niteliğindedir" if r["n_olay"] < 10 else ""
        yonetilen.append(r)

    # takvim tuzağı (TCMB geri alma): takvimsiz iş günüyle geri alma ile ortak (Türkiye takvimli) sürüm
    cal = b01._tr_gunluk().index
    t_takvimsiz = oo.usdtry_tcmb(geri_alma="is_gunu")
    t_takvimsiz13 = t_takvimsiz[t_takvimsiz.index >= cal.min()]
    # örnekler VERİDEN: valörü bir iş günü geri alınca Türkiye tatiline düşen değerler
    raw_v = oo.oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"].dropna()
    tk = _tr_takvim()
    t_ortak = oo.usdtry_tcmb()
    ilansiz = oo.tcmb_ilansiz_gunler()
    ornekler = []
    for v in raw_v.index[(raw_v.index >= pd.Timestamp("2024-01-01")) & (raw_v.index <= oo.CIPA_GUN)]:
        g = v - pd.offsets.BDay(1)
        if g not in tk and g >= tk.min():
            j_ = tk.searchsorted(v) - 1
            # ilan günü: değerin gerçekten ilan edildiği gün. Önceki Türkiye iş günü
            # ilansız bir arifeyse (yarım gün) değer ondan önceki ilanın tekrarıdır.
            il = t_ortak.index[t_ortak.index <= tk[j_]][-1]
            ornekler.append({"valor": str(v.date()), "takvimsiz_geri_alma_gunu": str(g.date()),
                             "takvimsiz_geri_alma_gunu_is_gunu_mu": False, "ilan_gunu": str(il.date()),
                             "onceki_is_gunu_ilansiz_arife": bool(tk[j_] in ilansiz)})
    ilansiz_cal = ilansiz[ilansiz.isin(cal)]
    tuzak = {
        "takvimsiz_surumde_takvim_disina_dusen_deger": int((~t_takvimsiz13.index.isin(_tr_takvim())).sum()),
        "takvimsiz_surumde_degeri_olmayan_is_gunu": int((~cal.isin(t_takvimsiz.index)).sum()),
        "ortak_surumde_degeri_olmayan_is_gunu": int((~cal.isin(t_ortak.index)).sum()),
        "ilan_olmayan_arife_gunu": int(len(ilansiz_cal)),
        "ilan_olmayan_arife_ornek": [str(t.date()) for t in ilansiz_cal[-3:]],
        "ornek": ornekler[:3],
        "ilk": str(cal.min().date()), "son": str(cal.max().date()),
        "not": "Ortak sürüm valörü Türkiye iş günü takvimiyle geri alır; takvimsiz sürüm yalnız bu tuzağın "
               "büyüklüğünü göstermek için kurulur. Ortak sürümde değeri olmayan günler ilan yapılmayan yarım "
               "günlerdir (bayram arifeleri ve 28 Ekim): arşiv tatil sonrası valöre önceki ilanı tekrar yazar, o "
               "tekrar arife gününe sıfır değişim olarak düşmesin diye boş bırakılır.",
    }
    r_duz = _profil_satiri("usdtry_tcmb_takvimsiz", "ppk", _seri("usdtry_tcmb_takvimsiz"), ppk, 950)
    tuzak["takvimsiz_ppk_profili"] = {k: r_duz[k] for k in ("oran", "tepe", "kapi", "n_olay", "p_rastgele_oran0",
                                                            "yonetilen_kur")}
    kapi_tcmb = next(r for r in satirlar if r["seri"] == "usdtry_tcmb" and r["olay"] == "ppk")
    tuzak["ortak_surum_ppk_kapi"] = kapi_tcmb["kapi"]
    tuzak["kapi_hukmu_degisiyor_mu"] = bool(r_duz["kapi"] != kapi_tcmb["kapi"])
    # TCMB sabitleme saati: iki büyük PPK günü (karar 14:00)
    raw = oo.oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"]
    yh, _ = oo.usdtry()
    sab = {}
    for t, (v0, v1) in {"2018-09-13": ("2018-09-14", "2018-09-17"),
                        "2023-08-24": ("2023-08-25", "2023-08-28")}.items():
        sab[t] = {"tcmb_karar_gunu_ilani": float(raw.get(pd.Timestamp(v0))),
                  "tcmb_ertesi_gun_ilani": float(raw.get(pd.Timestamp(v1))),
                  "tcmb_onceki_gun_ilani": float(oo.usdtry_tcmb().get(pd.Timestamp(t) - pd.offsets.BDay(1))),
                  "yahoo_karar_gunu_kapanisi": float(yh.get(pd.Timestamp(t)))}
    tuzak["sabitleme_saati_ornek"] = sab

    # cuma tuzağı (Yahoo geçiş öncesi): günlük |Δ| haftanın günlerine göre
    d = _tr_degisim()
    gun = {}
    for ad, a, b in (("gecis_oncesi", None, GECIS - pd.Timedelta(days=1)), ("gecis_sonrasi", GECIS, None)):
        z = d.loc[a:b]
        gun[ad] = {s_: {g: float(z[s_][z.index.dayofweek == i].abs().mean())
                        for i, g in enumerate(("pzt", "sal", "car", "per", "cum"))}
                   for s_ in ("usdtry", "usdtry_tcmb", "n2y")}
    ppk_gun = {g: int((ppk.dayofweek == i).sum()) for i, g in enumerate(("pzt", "sal", "car", "per", "cum"))}

    olculen = [r for r in satirlar if r["durum"] == "olculdu"]
    ozet = {"gecen": [f'{r["seri"]}×{r["olay"]}' for r in olculen if r["kapi"]],
            "guclu_gecen": [f'{r["seri"]}×{r["olay"]}' for r in olculen if r["kapi_guclu"]],
            "saatle_bagdasmayan_gecis": [f'{r["seri"]}×{r["olay"]}' for r in olculen
                                         if r["kapi"] and not r["saat_tutarli"]],
            "kurulabilir": [f'{r["seri"]}×{r["olay"]}' for r in olculen if r["kurulabilir"]],
            # güçlü kural p değeri 1.000 rastgele kümenin tahmin hatası içinde 0,05'e değiyor: tohuma bağlı
            "guclu_sinirda": [f'{r["seri"]}×{r["olay"]}' for r in olculen if r.get("guclu_sinirda")],
            "gecmeyen": [f'{r["seri"]}×{r["olay"]} (tepe {bicim.sayi(r["tepe"], 0, isaret=True)})' for r in olculen if not r["kapi"]],
            "kurulmayan": sorted({f'{r["olay"]}: {r["sebep"]}' for r in satirlar if r["durum"] == "kurulmadi"}),
            "olculen_satir": len(olculen), "toplam_satir": len(satirlar)}
    return {
        "kapi": satirlar, "kapi_ozet": ozet,
        "kontrol_rastgele": kontrol,
        "alt_donem_ppk": alt,
        "yonetilen_kur_donemi": yonetilen,
        "tarih_sozlesmesi": tarih_sozlesmesi(),
        "ppk_denetimi": ppk_denet,
        "fomc_denetimi": _FOMC_DENETIM,
        "tcmb_takvim_tuzagi": tuzak,
        "gun_etkisi_ortalama_abs": {"degisim": gun, "ppk_gun_dagilimi": ppk_gun},
        "seriler": {k: {"ad": SERI_AD[k], "birim": SERI_BIRIM[k], "saat": SERI_SAAT[k]} for k in SERI_AD},
        "olay_turleri": OLAY_AD,
        "n": int(sum(r.get("n_olay", 0) for r in olculen)),
        "ilk": min(r["ilk"] for r in olculen), "son": max(r["son"] for r in olculen),
        "yontem": "Her seri için olay günlerinin iki iş günü öncesinden iki iş günü sonrasına mutlak günlük "
                  "değişim ortalaması, olay pencerelerinin dışındaki günlerin mutlak değişim ortalamasına "
                  "bölündü; tepe olay gününde ve olay günü oranı öbür dört kaymanın en büyüğünden yüksekse "
                  "sınama geçer. Olay günü oranı, haftanın günü bileşimi aynı 1.000 rastgele gün kümesiyle "
                  "kıyaslandı (rastgele kümelerin tabanı da olay pencerelerinin dışındaki sıradan günler); "
                  "güçlü kural ayrıca bu kıyasın %95'ini aşmayı ister, olay çalışması ise ek olarak geçişin "
                  "serinin ölçülmüş saatiyle bağdaşmasını. Kur serilerinde yönetilen kur dönemi ayrı ölçüldü.",
        "kural": "Pencere ölçülür, varsayılmaz: plasebo sınamasından geçmeyen seri × olay ikilisinde olay çalışması kurulmaz.",
        "kaynak": ["dibs_egri_gunluk", "usdtry_yahoo_gunluk", "usdtry_tcmb_gunluk", "ppk_kararlari",
                   "fonlama_gunluk (yalnız iş günü takvimi)", "abd_hazine_gunluk", "cnbc_kur_gunluk",
                   "bulut: TÜİK yayım takvimi, FOMC takvimi (BLS takvimi elde yok)"],
    }


# ───────────────────────────────────────────────────────── anket etiketi
def anket_etiketi() -> dict:
    e = oo.oku("enflasyon_aylik")
    gercek = (e["tufe"] / e["tufe"].shift(1) - 1.0) * 100.0
    pka = e["pka_ay_cari"]
    satir = {}
    for k in (-2, -1, 0, 1, 2):
        g = gercek.shift(-k)          # pka[m] ↔ gerçekleşen[m+k]
        j = pd.concat([pka.rename("p"), g.rename("g")], axis=1).dropna()
        hata = j["p"] - j["g"]
        dj = j.diff().dropna()
        satir[str(k)] = {
            "n": int(len(j)), "ilk": str(j.index.min().date())[:7], "son": str(j.index.max().date())[:7],
            "ort_mutlak_hata_puan": float(hata.abs().mean()),
            "medyan_mutlak_hata_puan": float(hata.abs().median()),
            "ort_hata_puan": float(hata.mean()),
            "korelasyon": float(j["p"].corr(j["g"])),
            "fark_korelasyonu": float(dj["p"].corr(dj["g"])),
        }
    en_iyi = min(satir, key=lambda k: satir[k]["ort_mutlak_hata_puan"])
    en_iyi_medyan = min(satir, key=lambda k: satir[k]["medyan_mutlak_hata_puan"])
    alt = {}
    for ad, a, b in (("2013-2020", "2013-01-01", "2020-12-31"), ("2021-2026", "2021-01-01", "2026-08-31")):
        z = {}
        for k in (-1, 0, 1):
            j = pd.concat([pka.rename("p"), gercek.shift(-k).rename("g")], axis=1).dropna().loc[a:b]
            z[str(k)] = {"n": int(len(j)), "ort_mutlak_hata_puan": float((j["p"] - j["g"]).abs().mean()),
                         "korelasyon": float(j["p"].corr(j["g"]))}
        z["en_iyi_kayma"] = int(min(z, key=lambda k: z[k]["ort_mutlak_hata_puan"]))
        alt[ad] = z
    # bağımsız sınama: anketin 1 ve 2 ay sonrası beklentileri de doğru etiketliyse en iyi kayma
    # ufka eşit çıkmalı (cari ay 0 · 1 ay sonrası +1 · 2 ay sonrası +2)
    try:
        pe = bulut.pka_enflasyon()
        ufuk = {}
        for col, h in (("cari_ay", 0), ("ay1", 1), ("ay2", 2)):
            if col not in pe.columns:
                continue
            mae = {}
            for k in (-1, 0, 1, 2, 3):
                j = pd.concat([pe[col].rename("p"), gercek.shift(-k).rename("g")], axis=1).dropna()
                mae[str(k)] = float((j["p"] - j["g"]).abs().mean())
            ufuk[col] = {"ufuk_ay": h, "ort_mutlak_hata_puan": mae,
                         "en_iyi_kayma": int(min(mae, key=mae.get)),
                         "ufukla_tutarli": bool(int(min(mae, key=mae.get)) == h)}
        ufuk_sinamasi = {"satirlar": ufuk,
                         "cari_ay_depodakiyle_ayni": bool(np.allclose(
                             pe["cari_ay"].reindex(pka.dropna().index).values, pka.dropna().values, atol=1e-9)),
                         "yontem": "Anketin 1 ve 2 ay sonrası aylık TÜFE beklentileri aynı kuralla kaydırılarak "
                                   "gerçekleşen aylık TÜFE ile karşılaştırıldı; etiket doğruysa en iyi kayma ufka eşittir.",
                         "kaynak": ["bulut: EVDS Piyasa Katılımcıları Anketi"]}
    except bulut.VeriYok as e_:
        ufuk_sinamasi = {"durum": "kurulmadi", "sebep": str(e_)}
    s0, s_en = satir["0"], satir[en_iyi]
    ikinci = sorted(satir, key=lambda k: satir[k]["ort_mutlak_hata_puan"])[1]
    sonuc = (f"cari ay beklentisi aynı ayın gerçekleşmesine ait (etiket doğru): ortalama mutlak hata "
             f"{bicim.sayi(s_en['ort_mutlak_hata_puan'], 2)} puan, en yakın rakip kaymada "
             f"{bicim.sayi(satir[ikinci]['ort_mutlak_hata_puan'], 2)} puan"
             if en_iyi == "0" else
             f"etiket {bicim.sayi(int(en_iyi), 0, isaret=True)} ay kaymış görünüyor: hata "
             f"{bicim.sayi(s_en['ort_mutlak_hata_puan'], 2)} puan, sıfır kaymada "
             f"{bicim.sayi(s0['ort_mutlak_hata_puan'], 2)} puan")
    return {
        "kaymalar": satir, "etiket_kaymasi": int(en_iyi), "etiket_kaymasi_medyanla": int(en_iyi_medyan),
        "olculen_hata_puan": s_en["ort_mutlak_hata_puan"], "alt_donem": alt, "sonuc": sonuc,
        "ufuk_sinamasi": ufuk_sinamasi,
        "yayim_gunu": {"durum": "kurulmadi",
                       "sebep": "anketin yayım takvimi arşivde yok; günlük seriye yayılmış beklentiler ayın "
                                "20'si varsayımıyla kurulmuş, yani yayım günü onlardan ölçülemez"},
        "n": s_en["n"], "ilk": s_en["ilk"], "son": s_en["son"],
        "yontem": "Piyasa Katılımcıları Anketi'nin cari ay TÜFE beklentisi, TÜFE endeksinden hesaplanan aylık "
                  "yüzde değişimle aynı ayda ve bir, iki ay kaydırılarak karşılaştırıldı; ortalama mutlak hatası "
                  "en küçük kayma etiket sayıldı.",
        "kaynak": ["enflasyon_aylik"],
        "birim": "aylık yüzde değişim; hata puan",
    }


# ───────────────────────────────────────────────────────── şekil 02
def sekil_02(p: dict) -> dict:
    sat = []
    for r in p["kapi"]:
        if r["durum"] != "olculdu":
            sat.append({"seri": r["seri"], "olay": r["olay"], "durum": "kurulmadi",
                        "sebep": r.get("sebep") or "olay günleri elde yok"})
            continue
        sat.append({"seri": r["seri"], "olay": r["olay"], "durum": "olculdu", "kapi": r["kapi"],
                    "kapi_guclu": r["kapi_guclu"], "saat_tutarli": r["saat_tutarli"],
                    "kurulabilir": r["kurulabilir"], "n_olay": r["n_olay"],
                    "oran": [r["oran"][str(k)] for k in range(-PENCERE, PENCERE + 1)],
                    "rastgele_gun_eslemeli": [r["rastgele_ort_profil"][str(k)] for k in range(-PENCERE, PENCERE + 1)]})
    for seri, liste in p["tarih_sozlesmesi"]["ppk_kayma_taramasi"].items():
        for r in liste:
            if r["kayma"]:
                sat.append({"seri": seri, "olay": f"ppk_kayma_{r['kayma']}", "durum": "olculdu", "kapi": r["kapi"],
                            "kapi_guclu": r["kapi_guclu"], "saat_tutarli": r["saat_tutarli"],
                            "kurulabilir": r["kurulabilir"], "n_olay": r["n_olay"],
                            "oran": [r["oran"][str(k)] for k in range(-PENCERE, PENCERE + 1)]})
    for r in p["kontrol_rastgele"]:
        sat.append({"seri": r["seri"], "olay": "rastgele", "durum": "olculdu", "kapi": r["ornek_kume_kapi"],
                    "n_olay": r["n_gun_kume"],
                    "oran": [r["ort_profil"][str(k)] for k in range(-PENCERE, PENCERE + 1)],
                    "not": "1.000 rastgele kümenin ortalama profili"})
    olcu = [r for r in p["kapi"] if r["durum"] == "olculdu"]
    return {"n": len(sat), "n_olcu": len(olcu),
            "ilk": min((r["ilk"] for r in olcu if r.get("ilk")), default=None),
            "son": max((r["son"] for r in olcu if r.get("son")), default=None),
            "kayma": list(range(-PENCERE, PENCERE + 1)), "satirlar": sat,
            "yontem": "Seri × olay türü × kayma için olay günü mutlak değişim ortalamasının sıradan gün "
                      "ortalamasına oranı.",
            "kaynak": p["kaynak"]}


# ───────────────────────────────────────────────────────── giriş
def olc() -> dict:
    p = p2()
    p["anket_etiketi"] = anket_etiketi()
    return oo.yuvarla({"p2": p, "sekil_02": sekil_02(p)}, 4)


if __name__ == "__main__":
    import json
    print(json.dumps(olc(), ensure_ascii=False, indent=1)[:6000])
