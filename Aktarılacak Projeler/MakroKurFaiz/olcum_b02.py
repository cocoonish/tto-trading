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
  USD/TRY (%) Yahoo: 18.12.2023'ten İstanbul 18:00; öncesinde Londra gece
             yarısı kapanışı, bir hafta içi geri yazılmış (`ortak_olc.usdtry`).
  USD/TRY TCMB (%) gösterge kuru; valör tarihi bir iş günü geri alınmış
             (`ortak_olc.usdtry_tcmb`), sabitleme 14:00 öncesi (tuzak 2) — yalnız sağlamlık.
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
     20,17. PPK × DİBS kapısı bu yüzden kaymasız DÜŞÜYOR (tepe +2) ve 2 yıllık
     iki iş günü kaymada güçlü geçiyor. Bölüm 1'in sabiti
     (`olcum_b01.DIBS_ETIKET_ONCU`) bu ölçüme karşı sınanır.
  2. TCMB GÖSTERGE KURU ÖĞLEDEN ÖNCE SABİTLENİYOR: PPK günü (14:00) ilanı kararı
     taşımıyor. 13.09.2018: önceki ilan 6,3945, karar günü ilanı 6,3566,
     ertesi gün 6,0659; Yahoo karar günü kapanışı 6,1287. PPK × TCMB tepe +1.
  3. `ortak_olc.usdtry_tcmb()` valörü Türkiye takvimini bilmeyen bir iş
     günüyle geri alıyor: tatilden önceki ilan TATİL gününe düşüyor (15.04.2024
     valörlü kur 12.04.2024'e; ilan 09.04.2024); 2013–2026'da 88 iş günü TCMB
     değeri olmadan kalıyor. Kapı satırı ortak fonksiyonla kurulur; Türkiye
     takvimiyle geri alınmış sürüm yanında durur (hüküm değişmiyor).
  4. DİBS eğrisi Türkiye tatillerinde satır taşıyor (değişimi sıfır değil):
     bütün Türkiye serileri EVDS iş günü takvimine indirilir.
  5. HAFTANIN GÜNÜ ETKİSİ: PPK'ların 87/111'i perşembe, yani +1 kayması çoğunlukla
     cuma, −2 salı. 18.12.2023 sonrası Yahoo USD/TRY'de cuma |Δ| öbür günlerin
     iki katı (0,23 · 0,10–0,12 %), TCMB'de pazartesi |Δ| iki katı. Koşulsuz
     taban bu yüzden profili bozar; olay günü oranı, haftanın günü bileşimi
     aynı 1.000 rastgele gün kümesiyle kıyaslanır.
  6. KAPININ RASTGELE GEÇME OLASILIĞI ≈ %15–22: tepe beş kaymadan birine düşer.
     "Güçlü kapı" ayrıca oran[0]'ın rastgele kümelerin %95'ini aşmasını ister.
  7. AY İÇİ TAKVİM: TÜFE ayın 2.–3. iş gününe düşüyor ve DİBS değişimi ayın 2.
     iş gününde takvim gereği büyük (2 yıllık 32,4 · ortalama 27,5 bp). TÜFE ×
     DİBS'in kaymasız geçişi DİBS'in iki günlük öncülüğüyle de çelişiyor; olay
     çalışmasına dayanak sayılmaz.
  8. `bulut.fomc_gunleri()` belgesinde "planlı" der ama plansız toplantı ve
     telekonferansları da döndürür (170 günün 18'i); planlılar ayıklanır.
"""
from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

import bulut
import olcum_b01 as b01
import ortak_olc as oo

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

PENCERE = 2
K_RASTGELE = 1000
TOHUM = 20261002
GECIS = pd.Timestamp("2023-12-18")
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
             "usdtry_tcmb": "TCMB ilanı, valör bir iş günü geri; sabitleme 14:00 öncesi",
             "us2": "New York öğleden sonra", "dolar_sepeti": "New York 17:00"}
TR_SERILER = ("n3a", "n2y", "n5y", "usdtry", "usdtry_tcmb")
ABD_SERILER = ("us2", "dolar_sepeti")
OLAY_AD = {"ppk": "PPK karar günü (14:00 TSİ)", "tufe": "TÜİK TÜFE yayımı (10:00 TSİ)",
           "abd_istihdam": "ABD istihdam raporu (08:30 New York)", "abd_tufe": "ABD TÜFE (08:30 New York)",
           "fomc": "planlı FOMC kararı (14:00 New York)"}


# ───────────────────────────────────────────────────────── seriler
@lru_cache(maxsize=1)
def _tr_takvim() -> pd.DatetimeIndex:
    return b01._tr_takvim()


def _tcmb_tr_takvim() -> pd.Series:
    """TCMB valör tarihini TÜRKİYE iş günü takvimiyle bir gün geri alır (tuzak 2)."""
    raw = oo.oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"].dropna()
    cal = _tr_takvim()
    j = cal.searchsorted(raw.index) - 1          # valör gününden ÖNCEKİ son iş günü
    ok = j >= 0
    s = pd.Series(raw.values[ok], index=cal[j[ok]])
    s = s[~s.index.duplicated(keep="last")]
    return s[s.index <= oo.CIPA_GUN]


@lru_cache(maxsize=1)
def _tr_degisim() -> pd.DataFrame:
    """Türkiye serilerinin günlük değişimi, ortak takvimde (DİBS ∩ Yahoo ∩ EVDS iş günü)."""
    g = b01._tr_gunluk()
    cal = g.index
    t = oo.usdtry_tcmb().reindex(cal)
    t2 = _tcmb_tr_takvim().reindex(cal)
    d = pd.DataFrame({
        "n3a": g["n3a"].diff() * 100.0,
        "n2y": g["n2y"].diff() * 100.0,
        "n5y": g["n5y"].diff() * 100.0,
        "usdtry": np.log(g["usdtry"]).diff() * 100.0,
        "usdtry_tcmb": np.log(t).diff() * 100.0,
        "usdtry_tcmb_trtakvim": np.log(t2).diff() * 100.0,
    }).iloc[1:]
    return d


@lru_cache(maxsize=1)
def _abd_degisim() -> pd.DataFrame:
    g = b01._abd_gunluk()
    d = pd.DataFrame({"us2": g["us2"].diff() * 100.0, "dolar_sepeti": g["sepet"].diff() * 100.0}).iloc[1:]
    return d[d.index >= b01.ILK_GUN]


def _seri(ad: str) -> pd.Series:
    for df in (_tr_degisim(), _abd_degisim()):
        if ad in df.columns:
            return df[ad]
    raise KeyError(f"tanımsız seri: {ad} (geçerli: {', '.join(list(_tr_degisim().columns) + list(_abd_degisim().columns))})")


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
    """Planlı FOMC karar günleri. `bulut.fomc_gunleri()` belgesinde "planlı" der ama
    plansız toplantı ve telekonferansları da döndürür; ayrım takvimin `planli`
    sütunundadır (bulut okuyucusunun kendi dosyası, aynı öz kapısı)."""
    tum = pd.DatetimeIndex(bulut.fomc_gunleri()).normalize()
    try:
        df = bulut._oku("fomc_takvim", "Federal Reserve FOMC takvimi")
        planli = pd.DatetimeIndex(df.index[df["planli"].astype(bool)]).normalize()
    except (KeyError, bulut.VeriYok):
        planli = tum
    _FOMC_DENETIM.update({"toplam": int(len(tum)), "planli": int(len(planli)),
                          "plansiz_ayiklanan": int(len(tum) - len(planli)),
                          "ilk": str(tum.min().date()), "son": str(tum.max().date())})
    return pd.DatetimeIndex(sorted(set(planli)))


OLAY_SERI = {"ppk": TR_SERILER, "tufe": TR_SERILER,
             "abd_istihdam": ABD_SERILER, "abd_tufe": ABD_SERILER, "fomc": ABD_SERILER}


# ───────────────────────────────────────────────────────── profil ve kapı
def _kapi_hukmu(prof: dict) -> bool:
    """Tepe sıfırda ve oran[0] öbür kaymaların en büyüğünü aşıyor."""
    o = prof.get("oran", {})
    o0 = o.get("0")
    oteki = [v for k, v in o.items() if k != "0" and v is not None]
    if o0 is None or not oteki:
        return False
    return bool(prof.get("tepe") == 0 and o0 > max(oteki))


def _hizli_profil(a: np.ndarray, poz: np.ndarray, pencere: int = PENCERE) -> np.ndarray:
    """`ortak_olc.olay_profili` ile aynı hesap, konumlar üzerinden (rastgele kümeler için)."""
    n = len(a)
    maske = np.zeros(n, dtype=bool)
    for k in range(-pencere, pencere + 1):
        p = poz + k
        maske[p[(p >= 0) & (p < n)]] = True
    taban = a[~maske].mean()
    out = np.empty(2 * pencere + 1)
    for i, k in enumerate(range(-pencere, pencere + 1)):
        p = poz + k
        p = p[(p >= 0) & (p < n)]
        out[i] = a[p].mean() / taban
    return out


def _konumlar(s: pd.Series, olaylar: pd.DatetimeIndex) -> np.ndarray:
    idx = s.index
    j = idx.searchsorted(olaylar)
    ok = (j < len(idx))
    j = j[ok]
    return j[idx[j] == olaylar[ok]]


def _rastgele_dagilim(s: pd.Series, olaylar: pd.DatetimeIndex, k_tohum: int,
                      gun_eslemeli: bool = True, n_olay: int | None = None) -> dict:
    """Olay pencerelerinin (±2) DIŞINDAKİ günlerden rastgele gün kümeleri.

    `gun_eslemeli`: kümenin haftanın günü bileşimi olay günlerininkiyle aynı
    (PPK'ların ≈%78'i perşembe; +1 kayması çoğunlukla cumadır ve bazı serilerde
    cuma |Δ| yapısal olarak büyük — tuzak 5). Kapalıysa düzgün dağılımlı küme."""
    s = s.dropna()
    a = np.abs(s.values)
    poz = _konumlar(s, olaylar)
    yasak = np.zeros(len(s), dtype=bool)
    for k in range(-PENCERE, PENCERE + 1):
        p = poz + k
        yasak[p[(p >= 0) & (p < len(s))]] = True
    aday = np.flatnonzero(~yasak)
    aday = aday[(aday >= PENCERE) & (aday < len(s) - PENCERE)]
    gun = s.index.dayofweek.values
    rng = np.random.default_rng(TOHUM + k_tohum)
    if gun_eslemeli and len(poz):
        sayim = {w: int((gun[poz] == w).sum()) for w in range(5)}
        havuz = {w: aday[gun[aday] == w] for w in range(5)}
        if any(len(havuz[w]) < c for w, c in sayim.items()):
            gun_eslemeli = False
    n = int(n_olay if n_olay is not None else len(poz))

    def cek() -> np.ndarray:
        if gun_eslemeli and len(poz):
            return np.sort(np.concatenate([rng.choice(havuz[w], size=c, replace=False)
                                           for w, c in sayim.items() if c]))
        return np.sort(rng.choice(aday, size=n, replace=False))

    prof = np.empty((K_RASTGELE, 2 * PENCERE + 1))
    for i in range(K_RASTGELE):
        prof[i] = _hizli_profil(a, cek())
    o0 = prof[:, PENCERE]
    oteki = np.delete(prof, PENCERE, axis=1).max(axis=1)
    return {"oran0": o0, "fark": o0 - oteki, "kapi": (prof.argmax(axis=1) == PENCERE) & (o0 > oteki),
            "ort_profil": prof.mean(axis=0), "ornek_kume": s.index[cek()], "gun_eslemeli": bool(gun_eslemeli)}


def _profil_satiri(seri: str, olay: str, s: pd.Series, olaylar: pd.DatetimeIndex, k_tohum: int,
                   ilk: str | None = None, son: str | None = None, kayma: int = 0) -> dict:
    """Bir seri × olay satırı. `kayma` k: olay gününe serinin k iş günü SONRAKİ
    değişimi yazılır (tarih sözleşmesi taraması)."""
    s = s.dropna()
    if kayma:
        s = s.shift(-kayma).dropna()
    if len(olaylar):
        # örneklem olay listesinin kapsadığı dönemle sınırlı: listede olmayan eski olaylar
        # (ör. 2016 öncesi PPK'lar) sıradan gün sayılmasın
        k_ilk = olaylar.min() - pd.Timedelta(days=10)
        k_son = olaylar.max() + pd.Timedelta(days=10)
        ilk = str(max(k_ilk, pd.Timestamp(ilk)).date()) if ilk else str(k_ilk.date())
        son = str(min(k_son, pd.Timestamp(son)).date()) if son else str(k_son.date())
    if ilk or son:
        s = s.loc[ilk:son]
        olaylar = olaylar[(olaylar >= s.index.min()) & (olaylar <= s.index.max())]
    prof = oo.olay_profili(s, olaylar, PENCERE)
    poz = _konumlar(s, olaylar)
    # hızlı hesap ortak fonksiyonla birebir mi (rastgele dağılımın geçerliliği buna bağlı)
    hz = _hizli_profil(np.abs(s.values), poz)
    resmi = np.array([prof["oran"][str(k)] for k in range(-PENCERE, PENCERE + 1)], dtype=float)
    assert np.allclose(hz, resmi, rtol=1e-10, atol=1e-12), (seri, olay)
    o = prof["oran"]
    oteki = max(v for k, v in o.items() if k != "0")
    rd = _rastgele_dagilim(s, olaylar, k_tohum)
    p0 = float((1 + (rd["oran0"] >= o["0"]).sum()) / (1 + K_RASTGELE))
    pf = float((1 + (rd["fark"] >= o["0"] - oteki).sum()) / (1 + K_RASTGELE))
    ort = {str(k): float(v) for k, v in zip(range(-PENCERE, PENCERE + 1), rd["ort_profil"])}
    fazla = {k: float(o[k] / ort[k]) for k in o}
    k_gecer = _kapi_hukmu(prof)
    return {
        "seri": seri, "olay": olay, "kayma": int(kayma), "durum": "olculdu", "kapi": k_gecer,
        "kapi_guclu": bool(k_gecer and p0 < 0.05),
        "oran": {k: float(v) for k, v in o.items()}, "tepe": prof["tepe"],
        "oran0": float(o["0"]), "oteki_azami": float(oteki), "oran0_fazlasi": float(o["0"] - oteki),
        "rastgele_ort_profil": ort, "gun_etkisinden_arindirilmis": fazla,
        "arindirilmis_tepe": int(max(fazla, key=lambda k: fazla[k])),
        "p_rastgele_oran0": p0, "p_rastgele_kapi_farki": pf,
        "kapi_rastgele_gecme_orani": float(rd["kapi"].mean()),
        "n_olay": prof["n_olay"], "n_olay_listede": int(len(olaylar)),
        "taban_abs": float(prof["taban_abs"]), "birim": SERI_BIRIM.get(seri.split(":")[0], ""),
        "gun_eslemeli_kiyas": rd["gun_eslemeli"],
        "ilk": str(s.index.min().date()), "son": str(s.index.max().date()),
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
        u.append("TÜFE ayın 2.–3. iş gününe düşüyor ve DİBS değişimi o günlerde takvim gereği büyük; "
                 "geçiş olaydan değil ay içi takvimden gelebilir")
    if seri == "usdtry_tcmb" and olay in ("ppk", "fomc", "abd_istihdam", "abd_tufe"):
        u.append("TCMB gösterge kuru öğleden önceki sabitlemeden gelir; 14:00 sonrası olay ertesi günün ilanına düşer")
    return u


def kayma_onerisi(seri: str, olay: str = "ppk") -> int | None:
    """PPK kayma taramasında güçlü kapıyı geçen EN KÜÇÜK kayma (iş günü); yoksa None."""
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
    """Hiza kapısı.

    kapi("n2y", "ppk")            → tablodaki hüküm (kurulmamış satır False döner);
    kapi("n2y", "ppk", kayma=2)   → olay gününe serinin 2 iş günü sonraki değişimi yazılarak;
    kapi(..., guclu=True)         → ayrıca oran[0], haftanın günü eşlemeli 1.000 rastgele kümenin
                                     %95'inden yüksek;
    kapi(degisim_serisi, gunler)  → aynı kural doğrudan hesaplanır (yalnız temel kural).
    Kural: plasebo profilinin tepesi 0'da ve oran[0] öbür kaymaların en büyüğünü aşıyor."""
    if isinstance(seri, str):
        if kayma == 0:
            r = next((x for x in _tablo()[0] if x["seri"] == seri and x["olay"] == olay), None)
            if r is None:
                r = _kaymali_satir(seri, olay, 0)
        else:
            r = _kaymali_satir(seri, olay, int(kayma))
        return bool(r.get("kapi_guclu") if guclu else r.get("kapi"))
    return _kapi_hukmu(oo.olay_profili(seri, olay, pencere))


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
        tarama[seri] = [{k_: r[k_] for k_ in ("kayma", "kapi", "kapi_guclu", "tepe", "oran0", "oteki_azami",
                                              "p_rastgele_oran0", "arindirilmis_tepe", "n_olay")} | {"oran": r["oran"]}
                        for r in (_kaymali_satir(seri, "ppk", k) for k in KAYMA_TARAMA)]
    # iki yarıda tepe (seçimin kararlılığı)
    ppk = _olaylar()["ppk"]
    orta = ppk[len(ppk) // 2]
    yari = {}
    for seri in DIBS_SERILER + ("usdtry_tcmb",):
        s_ = _seri(seri).dropna()
        yari[seri] = {}
        for ad, ev in (("ilk_yari", ppk[ppk < orta]), ("son_yari", ppk[ppk >= orta])):
            pr = oo.olay_profili(s_, ev, PENCERE)
            yari[seri][ad] = {"n_olay": pr["n_olay"], "tepe": pr["tepe"],
                              "oran": {k: float(v) for k, v in pr["oran"].items()},
                              "ilk": str(ev.min().date()), "son": str(ev.max().date())}
    # ay içi iş günü etkisi (TÜFE ayın başına düşer)
    idx = d.index
    ig = pd.Series(idx.to_series().groupby([idx.year, idx.month]).cumcount().values + 1, index=idx)
    tufe = _olaylar()["tufe"]
    ay_ici = {"ortalama_abs_bp": {s_: {str(i): float(d[s_].abs()[ig == i].mean()) for i in range(1, 7)}
                                  for s_ in DIBS_SERILER},
              "tum_gunler_abs_bp": {s_: float(d[s_].abs().mean()) for s_ in DIBS_SERILER}}
    if not isinstance(tufe, str):
        tp = tufe[tufe.isin(idx)]
        ay_ici["tufe_ay_ici_is_gunu"] = {str(k_): int(v_) for k_, v_ in ig.loc[tp].value_counts().sort_index().items()}
        ay_ici["tufe_kayma_taramasi"] = [{k_: r[k_] for k_ in ("kayma", "kapi", "kapi_guclu", "tepe", "oran0",
                                                               "p_rastgele_oran0")} | {"seri": s_}
                                         for s_ in DIBS_SERILER for r in (_kaymali_satir(s_, "tufe", k) for k in (0, 1, 2))]
    # sonuç
    yah = capraz["usdtry_yahoo"]["2013-2021"]
    tcm = capraz["usdtry_tcmb_ilan"]["2013-2021"]
    yahoo_onculuk = sorted({yah[s_]["en_yuksek_kayma"] for s_ in ("n2y", "n5y")})
    tcmb_onculuk = sorted({tcm[s_]["en_yuksek_kayma"] for s_ in ("n2y", "n5y")})
    b01_sabit = getattr(b01, "DIBS_ETIKET_ONCU", None)
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
        "b01_sabiti": b01_sabit,
        "b01_sabiti_tutarli": bool(b01_sabit is not None and yahoo_onculuk == [b01_sabit]),
        "ornek_hafta_sonu_soku": {"aciklama": "20.03.2021 cumartesi merkez bankası başkanı görevden alındı; "
                                              "piyasa pazartesi 22.03'te açıldı",
                                  "degerler": ornek},
        "sonuc": ("DİBS gösterge eğrisinin günü, TCMB gösterge kuru gibi VALÖR günüdür ve fiyat öğleden önceki "
                  "sabitlemeden gelir: etiket X'in değeri X'ten bir iş günü önceki ilan anının piyasasını "
                  "taşır. Gün sonu kapanışlarına (USD/TRY, VIX, ZAR) göre iki iş günü öndedir; 14:00'teki PPK "
                  "kararı etiketin iki iş günü sonrasında görünür."),
        "oneri": {"ogleden_sonra_olayi_icin_kayma_is_gunu": {"n3a": 2, "n2y": 2, "n5y": 2, "usdtry_tcmb": 1, "usdtry": 0},
                  "aciklama": "14:00 ve sonrasındaki bir olayın tepkisi için olay gününe kaç iş günü sonraki etiketin değişimi yazılır: çapraz korelasyondan "
                              "(bütün günler) okunur; PPK taramasında 2 yıllık iki, 3 ay ve 5 yıllık ile TCMB "
                              "kuru üç iş günü kaymada güçlü kapıyı geçiyor, çünkü PPK sonrası oynaklık birkaç "
                              "gün sürüyor. Öğleden önceki olaylar (TÜFE 10:00) için TCMB sabitleme saati bu "
                              "arşivden ölçülemedi."},
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
        n_olay = len(_konumlar(s, ppk)) if seri in TR_SERILER else len(ppk)
        rd = _rastgele_dagilim(s, ev, 500 + i, gun_eslemeli=False, n_olay=n_olay)
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
            "ilk": str(s.index.min().date()), "son": str(s.index.max().date()),
        })

    # alt dönemler: Yahoo'nun iki tanımı ve TCMB, PPK günlerinde
    alt = []
    for seri in ("usdtry", "usdtry_tcmb", "n2y"):
        for ad, a, b in (("gecis_oncesi", None, str((GECIS - pd.Timedelta(days=1)).date())),
                         ("gecis_sonrasi", str(GECIS.date()), None)):
            alt.append(_profil_satiri(f"{seri}:{ad}", "ppk", _seri(seri), ppk, 900 + len(alt), a, b))

    # takvim tuzağı (TCMB geri alma)
    cal = b01._tr_gunluk().index
    t_ortak = oo.usdtry_tcmb()
    t_ortak13 = t_ortak[t_ortak.index >= cal.min()]
    tuzak = {
        "takvim_disina_dusen_tcmb_degeri": int((~t_ortak13.index.isin(_tr_takvim())).sum()),
        "tcmb_degeri_olmayan_is_gunu": int((~cal.isin(t_ortak.index)).sum()),
        "duzeltilmis_surumde_olmayan_is_gunu": int((~cal.isin(_tcmb_tr_takvim().index)).sum()),
        "ornek": {"valor": "2024-04-15", "ortak_fonksiyon_gunu": "2024-04-12 (tatil)",
                  "ilan_gunu": "2024-04-09"},
        "ilk": str(cal.min().date()), "son": str(cal.max().date()),
    }
    r_duz = _profil_satiri("usdtry_tcmb_trtakvim", "ppk", _seri("usdtry_tcmb_trtakvim"), ppk, 950)
    tuzak["duzeltilmis_ppk_profili"] = {k: r_duz[k] for k in ("oran", "tepe", "kapi", "n_olay", "p_rastgele_oran0")}
    kapi_tcmb = next(r for r in satirlar if r["seri"] == "usdtry_tcmb" and r["olay"] == "ppk")
    tuzak["ortak_fonksiyon_ppk_kapi"] = kapi_tcmb["kapi"]
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
            "gecmeyen": [f'{r["seri"]}×{r["olay"]} (tepe {r["tepe"]:+d})' for r in olculen if not r["kapi"]],
            "kurulmayan": sorted({f'{r["olay"]}: {r["sebep"]}' for r in satirlar if r["durum"] == "kurulmadi"}),
            "olculen_satir": len(olculen), "toplam_satir": len(satirlar)}
    return {
        "kapi": satirlar, "kapi_ozet": ozet,
        "kontrol_rastgele": kontrol,
        "alt_donem_ppk": alt,
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
                  "kapı geçer. Olay günü oranı, haftanın günü bileşimi aynı 1.000 rastgele gün kümesiyle "
                  "kıyaslandı; güçlü kapı ayrıca bu kıyasın %95'ini aşmayı ister.",
        "kural": "Pencere ölçülür, varsayılmaz: kapıdan geçmeyen seri × olay ikilisinde olay çalışması kurulmaz.",
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
    s0, s_en = satir["0"], satir[en_iyi]
    ikinci = sorted(satir, key=lambda k: satir[k]["ort_mutlak_hata_puan"])[1]
    sonuc = (f"cari ay beklentisi aynı ayın gerçekleşmesine ait (etiket doğru): ortalama mutlak hata "
             f"{s_en['ort_mutlak_hata_puan']:.2f} puan, en yakın rakip kaymada {satir[ikinci]['ort_mutlak_hata_puan']:.2f}"
             if en_iyi == "0" else
             f"etiket {en_iyi} ay kaymış görünüyor: hata {s_en['ort_mutlak_hata_puan']:.2f} puan, sıfır kaymada "
             f"{s0['ort_mutlak_hata_puan']:.2f}")
    return {
        "kaymalar": satir, "etiket_kaymasi": int(en_iyi), "etiket_kaymasi_medyanla": int(en_iyi_medyan),
        "olculen_hata_puan": s_en["ort_mutlak_hata_puan"], "alt_donem": alt, "sonuc": sonuc,
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
            sat.append({"seri": r["seri"], "olay": r["olay"], "durum": "kurulmadi"})
            continue
        sat.append({"seri": r["seri"], "olay": r["olay"], "durum": "olculdu", "kapi": r["kapi"],
                    "kapi_guclu": r["kapi_guclu"], "n_olay": r["n_olay"],
                    "oran": [r["oran"][str(k)] for k in range(-PENCERE, PENCERE + 1)],
                    "rastgele_gun_eslemeli": [r["rastgele_ort_profil"][str(k)] for k in range(-PENCERE, PENCERE + 1)]})
    for seri, liste in p["tarih_sozlesmesi"]["ppk_kayma_taramasi"].items():
        for r in liste:
            if r["kayma"]:
                sat.append({"seri": seri, "olay": f"ppk_kayma_{r['kayma']}", "durum": "olculdu", "kapi": r["kapi"],
                            "kapi_guclu": r["kapi_guclu"], "n_olay": r["n_olay"],
                            "oran": [r["oran"][str(k)] for k in range(-PENCERE, PENCERE + 1)]})
    for r in p["kontrol_rastgele"]:
        sat.append({"seri": r["seri"], "olay": "rastgele", "durum": "olculdu", "kapi": r["ornek_kume_kapi"],
                    "n_olay": r["n_gun_kume"],
                    "oran": [r["ort_profil"][str(k)] for k in range(-PENCERE, PENCERE + 1)],
                    "not": "1.000 rastgele kümenin ortalama profili"})
    return {"kayma": list(range(-PENCERE, PENCERE + 1)), "satirlar": sat,
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
