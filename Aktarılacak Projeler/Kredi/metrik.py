# -*- coding: utf-8 -*-
"""Kredi & parasal büyüklükler — hesap katmanı.

Girdi   data/haftalik.csv · data/arsiv.csv · data/gunluk.csv · data/aylik.csv
        data/ceyreklik.csv        (veri.py üretir)
Çıktı   data/metrik_haftalik.csv  haftalık metrik paneli
        data/metrik_aylik.csv     aylık metrik paneli (banka türü, KKM, katılım)
        data/ayristirma.csv       Laspeyres kur/akım ayrıştırması + kimlik artığı
        data/dolarizasyon.csv     ham ve arındırılmış DTH payı
        data/capraz.csv           kredi büyümesi ↔ enflasyon momentumu eşlemesi
        data/metrik_ozet.json     son dönem değerleri + doğrulama
        uyarilar.json             veri + hesap katmanının uyarıları (görünür)

Yöntem omurgası (ayrıntı: README.md)
------------------------------------
1. Kur etkisinden arındırma ZİNCİRLEME yapılır: haftalık büyüme oranı
       g_s = [K_TL_s + K_YP_s·(e_{s-1}/e_s)] / [K_TL_{s-1} + K_YP_{s-1}] − 1
   ve 13 haftalık yıllıklandırma (1+G13)^4 − 1 ile bileşiklenir. SIRA
   BAĞLAYICIDIR: önce arındır, sonra zincirle, sonra yıllıklandır. Ters sırada
   kur etkisi de yıllıklandırılır ve hata dört katına çıkar.
2. Kur olarak DTH'dan İMA EDİLEN SEPET kullanılır (ZK'ya tabi DTH'ın TL
   karşılığı / USD karşılığı); USD ile hesap TANI olarak tutulur. Sepet, ZK
   tabanının 13 gün gecikmesi yüzünden son 1–2 haftada boştur; o kuyruk USD+EUR
   ile tahmin edilir ve `sepet_kaynak` alanında İŞARETLENİR.
3. Laspeyres ayrıştırması (rezerv hattındaki altin_etkisi.py ile aynı çerçeve):
   Γ = kur etkisi, Λ = gerçek akım, Γ+Λ = ΔK kimliği artıksız kapanmalı.
4. Doğrulama: TCMB'nin KENDİ kur etkisinden arındırılmış para arzı endeksleri
   (TP.KAVRAMSAL.ARIM*) bizim yöntemimizin bağımsız sınavıdır. Ham endeks
   sınavı (HAMM2 ↔ hpbitablo1 seviyeleri) tutmazsa hat DURUR.

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

import veri
from veri import PROJE, VERI, ad_gun, ad_uzun, ad_ceyrek


def _bicim():
    """ortak/bicim — okura giden sayının TEK yazımı (ondalık virgül, eksi U+2212,
    yüzde önde). Hat kendi klasöründen elle koşturulursa ortak/ PYTHONPATH'te
    olmayabilir; depo kökünden bulunur."""
    try:
        import bicim
    except ImportError:
        import pathlib as _pl
        import sys as _sys
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[2] / "ortak"))
        import bicim
    return bicim

UYARI: list[str] = []

# ------ eşikler (hepsi ayrı: farklı sınıf hatalar aynı eşikle ölçülemez) ----
ESIK_HAM_ENDEKS_PP = 2.0     # HAMM* ↔ seviye kimliği — aşılırsa hat DURUR
ESIK_AR_ENDEKS_PP = 6.0      # ARIM2 ↔ bizim arındırma: YANLILIK eşiği (uyarı)
ESIK_KREDI_CAPRAZ_PP = 3.0   # haftalık ↔ aylık kredi serisi, 12 aylık büyüme
ESIK_CIPA_ZINCIR_PP = 1.5    # çıpalı ↔ zincirleme arındırma farkı
ESIK_USD_SEPET_PP = 2.0      # USD ↔ sepet kuru farkı
ESIK_KIMLIK = 1e-6           # Laspeyres Γ+Λ=ΔK bağıl artığı
ESIK_ORTUSME = 0.001         # arşiv/yeni örtüşme oranının sürüklenmesi
ESIK_SEPET_KUYRUK_HAFTA = 4  # sepet kurunun tahmin edildiği kuyruk uzunluğu

YIL_HAFTA = 52               # yıllıklandırma varsayımı: yılda 52 haftalık gözlem
PENCERE = 13                 # bir çeyrek — makro ihtiyati çerçevenin ufku
GECIKME_UFKU = 18            # kredi ↔ enflasyon gecikmeli korelasyon penceresi (ay)


def uyar(m: str) -> None:
    if m not in UYARI:
        UYARI.append(m)
    print("  ! " + m, flush=True)


# ===========================================================================
#  yardımcılar
# ===========================================================================
def _oku(ad: str) -> pd.DataFrame:
    d = pd.read_csv(VERI / ad, index_col=0, parse_dates=True)
    return d.sort_index()


# AOFM'nin geçerli sayılması için gereken en küçük fonlama tabanı (milyon TL).
# Fonlama & likidite hattındaki AOFM_TABAN_ESIK ile BİREBİR AYNI olmalıdır;
# iki hat aynı büyüklük için farklı eşik kullanırsa aynı gün iki sayfa iki
# farklı "fonlama maliyeti" yayımlar.
AOFM_TABAN_ESIK = 5_000.0

# PKA (Piyasa Katılımcıları Anketi) 12 aylık TÜFE beklentisi aylıktır ve
# haftalık eksene ffill edilir. Bu yaşı aşarsa anket yayını gecikmiş demektir
# ve reel faizler sessizce eski beklentiyle hesaplanıyor olur.
PKA_YAS_ESIK_GUN = 45


def geri_tasi(gunluk: pd.Series, tarihler: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    """Haftalık (Cuma) gözlemlere iş günü serisini eşle.

    Cuma tatilse EN YAKIN ÖNCEKİ iş gününe düşülür ve gözlem işaretlenir.
    İLERİ taşıma YAPILMAZ: gelecekteki bir kurla geçmiş bir stoğu değerlemek,
    ölçüm gününde bilinmeyen bilgiyi kullanmaktır.
    """
    g = gunluk.dropna().sort_index()
    if g.empty:
        return (pd.Series(index=tarihler, dtype=float),
                pd.Series(index=tarihler, dtype=object))
    ind = g.index.searchsorted(tarihler, side="right") - 1
    deger, kaynak = [], []
    for t, i in zip(tarihler, ind):
        if i < 0:
            deger.append(np.nan); kaynak.append("yok"); continue
        deger.append(float(g.iloc[i]))
        kaynak.append("aynigun" if g.index[i] == t else "geri_tasima")
    return (pd.Series(deger, index=tarihler),
            pd.Series(kaynak, index=tarihler))


def zincir_yillik(g: pd.Series, n: int = PENCERE) -> pd.Series:
    """(∏(1+g))^(52/n) − 1, yüzde. Basit ölçekleme (n·ort) KULLANILMAZ:
    bileşiklenmeyi ihmal eder ve bu ölçekte 2 puana kadar sapar."""
    bir = (1.0 + g).astype(float)
    bilesik = bir.rolling(n).apply(np.prod, raw=True)
    return (bilesik ** (YIL_HAFTA / n) - 1.0) * 100.0


def zincir_donem(g: pd.Series, n: int = PENCERE) -> pd.Series:
    """Yıllıklandırılmamış n haftalık bileşik değişim, yüzde."""
    return ((1.0 + g).rolling(n).apply(np.prod, raw=True) - 1.0) * 100.0


def ar_buyume(k_tl: pd.Series, k_yp: pd.Series, e: pd.Series) -> pd.Series:
    """Kur etkisinden arındırılmış HAFTALIK büyüme oranı (zincirleme tanım)."""
    getiri = e / e.shift(1)                     # e_s / e_{s-1}
    pay = k_tl + k_yp / getiri                  # YP, ÖNCEKİ haftanın kuruyla
    payda = (k_tl + k_yp).shift(1)
    return (pay / payda - 1.0)


def ham_buyume(k_tl: pd.Series, k_yp: pd.Series) -> pd.Series:
    t = (k_tl + k_yp)
    return t / t.shift(1) - 1.0


# ===========================================================================
#  1. Kur: ima edilen sepet + USD tanısı
# ===========================================================================
def kur_kur(H: pd.DataFrame, G: pd.DataFrame) -> pd.DataFrame:
    """Haftalık kur paneli: usd, eur, sepet (ima edilen), sepet_kaynak."""
    idx = H.index
    usd, usd_kaynak = geri_tasi(G["usd"], idx)
    eur, _ = geri_tasi(G["eur"], idx)

    # İma edilen sepet kuru: ZK'ya tabi DTH'ın TL karşılığı / USD karşılığı.
    # İkisi de MİLYON cinsinden yayımlanıyor; oran doğrudan TL/USD verir.
    sepet_ham = (H["dth_tl"] / H["dth_usd"]).replace([np.inf, -np.inf], np.nan)

    # BİRİM GÜVENLİĞİ: birim varsayımı yanlışsa oran 1000 kat sapar. USD kuruyla
    # makullük denetimi bunu ilk koşuda yakalar (kalibrasyon değil, DENETİM).
    ort = pd.concat([sepet_ham, usd], axis=1).dropna()
    if len(ort):
        oran = (ort.iloc[:, 0] / ort.iloc[:, 1]).tail(52)
        if not (0.5 < float(oran.median()) < 2.0):
            uyar(f"BİRİM: ima edilen sepet kuru USD kurunun {float(oran.median()):.4g} "
                 "katı çıkıyor — TP.ZORUNDTH.KB7/KB8 birimi değişmiş olabilir. "
                 "Sepet kuru kullanılmadı, USD'ye düşüldü.")
            sepet_ham = pd.Series(index=idx, dtype=float)

    # Kuyruk tahmini: ZK tabanı 13 gün gecikmeli, son 1–2 hafta boş kalır.
    # Sepeti USD+EUR ile (sabitsiz EKK, son 104 hafta) doldururuz ve İŞARETLERİZ.
    kaynak = pd.Series("olculdu", index=idx, dtype=object)
    kaynak[sepet_ham.isna()] = "yok"
    sepet = sepet_ham.copy()
    tahmin_bilgi: dict = {"n": 0}
    egitim = pd.concat([sepet_ham, usd, eur], axis=1).dropna().tail(104)
    egitim.columns = ["sepet", "usd", "eur"]
    if len(egitim) >= 26:
        X = egitim[["usd", "eur"]].to_numpy()
        y = egitim["sepet"].to_numpy()
        w, *_ = np.linalg.lstsq(X, y, rcond=None)
        tahmin = usd * w[0] + eur * w[1]
        artik = egitim["sepet"] - (egitim["usd"] * w[0] + egitim["eur"] * w[1])
        tahmin_bilgi = {"n": int(len(egitim)), "w_usd": float(w[0]),
                        "w_eur": float(w[1]),
                        "artik_maks_pct": float((artik / egitim["sepet"]).abs().max() * 100),
                        "artik_std_pct": float((artik / egitim["sepet"]).std() * 100)}
        bos = sepet.isna() & tahmin.notna()
        sepet[bos] = tahmin[bos]
        kaynak[bos] = "tahmin"
    kuyruk = int((kaynak.loc[sepet.notna()] == "tahmin").iloc[-8:].sum()) if sepet.notna().any() else 0
    if kuyruk > ESIK_SEPET_KUYRUK_HAFTA:
        uyar(f"SEPET KURU: son {kuyruk} hafta ölçülmedi, USD+EUR ile TAHMİN edildi "
             f"(tolerans {ESIK_SEPET_KUYRUK_HAFTA} hafta). ZK tabanı yayını gecikmiş olabilir.")
    if sepet.isna().all():
        uyar("SEPET KURU üretilemedi — arındırmada USD kuruna düşüldü. "
             "Bu, YP kredinin tamamı dolar varsayımıdır ve haftalık ölçüde "
             "0,4 puana kadar sahte akım üretebilir.")
        sepet = usd.copy()
        kaynak = pd.Series("usd_yedek", index=idx, dtype=object)

    K = pd.DataFrame({"usd": usd, "eur": eur, "sepet": sepet,
                      "sepet_kaynak": kaynak, "kur_gun_kaynak": usd_kaynak})
    K.attrs["tahmin"] = tahmin_bilgi
    return K


def kur_duyarlilik(H: pd.DataFrame, K: pd.DataFrame, M: pd.DataFrame) -> dict:
    """Kur seçiminin ve TAHMİN edilen sepet kuyruğunun büyümeye etkisi.

    Sayfa kur seçimi duyarlılığını üç ölçülmüş seçenekle yayımlıyordu (sepet,
    USD, çıpalı). Ama son haftaların sepet kuru çoğu koşuda ÖLÇÜLMEZ, USD+EUR
    ile TAHMİN edilir; tahminin artığı yalnız KUR düzeyinde yayımlanıyordu.
    Asıl merak edilen belirsizlik kur değil BÜYÜME düzeyindedir: aynı artık
    büyümeyi kaç puan oynatıyor? Burada ölçülüyor.

    İkinci ölçü çıpa seçimi: `g_cipa_13y` yalnız PENCERE İÇİ (t−13) çıpayı
    sınıyor. Çıpa yıl başı ya da 52 hafta öncesi seçilseydi sonuç nereye
    giderdi — sayfa çıpanın keyfî olduğunu söylüyor, büyüklüğünü de söylemeli.
    """
    out: dict = {}
    e, tl, yp = K["sepet"], H["kredi_tl"], H["kredi_yp"]
    kaynak = K["sepet_kaynak"]
    ana_s = M["g_ar_13y"].dropna()
    if ana_s.empty:
        return out
    ana, son = float(ana_s.iloc[-1]), ana_s.index[-1]
    out["g_ar_13y_ana"] = ana

    # (1) TAHMİN BANDI — tahmin edilen haftaları ±artık_maks kaydır
    bilgi = K.attrs.get("tahmin") or {}
    amax = bilgi.get("artik_maks_pct")
    tah = (kaynak == "tahmin")
    out["tahmin_hafta"] = int(tah.sum())
    if amax and tah.any():
        uclar = []
        for isaret in (1, -1):
            e2 = e.copy()
            e2[tah] = e2[tah] * (1.0 + isaret * amax / 100.0)
            g = zincir_yillik(ar_buyume(tl, yp, e2)).dropna()
            uclar.append(float(g.iloc[-1]) if len(g) else np.nan)
        if not any(pd.isna(u) for u in uclar):
            out["g_ar_13y_tahmin_ust"] = max(uclar)
            out["g_ar_13y_tahmin_alt"] = min(uclar)
            out["sepet_tahmin_buyume_bandi_pp"] = (max(uclar) - min(uclar)) / 2.0
            out["tahmin_artik_maks_pct"] = float(amax)

    # (2) ÇIPA SEÇİMİ — pencere DIŞI çıpalar
    def _sabit_cipa(t_cipa: pd.Timestamp):
        ec = e.dropna().asof(t_cipa)
        if pd.isna(ec):
            return None
        kt = tl + yp * (ec / e)
        oran = kt / kt.shift(PENCERE)
        g = ((oran ** (YIL_HAFTA / PENCERE) - 1.0) * 100.0).dropna()
        return float(g.iloc[-1]) if len(g) else None

    cipalar = {
        "yilbasi": pd.Timestamp(son.year, 1, 1),
        "52hafta": son - pd.Timedelta(weeks=YIL_HAFTA),
    }
    degerler = [ana]
    for ad, t in cipalar.items():
        v = _sabit_cipa(t)
        if v is not None:
            out[f"g_cipa_{ad}_13y"] = v
            out[f"cipa_{ad}_tarih"] = t.strftime("%Y-%m-%d")
            degerler.append(v)
    icteki = M["g_cipa_13y"].dropna()
    if len(icteki):
        degerler.append(float(icteki.iloc[-1]))
    if len(degerler) > 1:
        out["cipa_yayilim_pp"] = max(degerler) - min(degerler)
    return out


# ===========================================================================
#  2. Kredi büyümesi — arındırılmış, ham, kırılım
# ===========================================================================
def kredi_metrikleri(H: pd.DataFrame, K: pd.DataFrame) -> pd.DataFrame:
    M = pd.DataFrame(index=H.index)
    e, e_usd = K["sepet"], K["usd"]

    tl, yp = H["kredi_tl"], H["kredi_yp"]
    M["g_ar"] = ar_buyume(tl, yp, e)
    M["g_ham"] = ham_buyume(tl, yp)
    M["g_ar_usd"] = ar_buyume(tl, yp, e_usd)          # TANI: tek para varsayımı
    M["g_tl"] = tl / tl.shift(1) - 1.0
    # YP kredinin DÖVİZ cinsinden büyümesi: TL karşılığından kur getirisi çıkarılır
    M["g_yp_ar"] = (yp / yp.shift(1)) * (e.shift(1) / e) - 1.0

    for ad in ("g_ar", "g_ham", "g_ar_usd", "g_tl", "g_yp_ar"):
        M[f"{ad}_13y"] = zincir_yillik(M[ad])
        M[f"{ad}_52"] = zincir_donem(M[ad], YIL_HAFTA)
    M["kur_etkisi_13y"] = M["g_ham_13y"] - M["g_ar_13y"]
    M["usd_sepet_farki_13y"] = M["g_ar_usd_13y"] - M["g_ar_13y"]

    # ÇIPALI arındırma (tanı): tüm pencere boyunca t−13'ün kuruyla değerleme.
    cipa_e = e.shift(PENCERE)
    kt = tl + yp * (cipa_e / e)
    kt_gec = (tl + yp).shift(PENCERE)
    M["g_cipa_13y"] = ((kt / kt_gec) ** (YIL_HAFTA / PENCERE) - 1.0) * 100.0
    M["cipa_zincir_farki"] = M["g_cipa_13y"] - M["g_ar_13y"]

    # --- kırılım -----------------------------------------------------------
    # Tüketici kalemleri TL+YP BİRLEŞİK yayımlanıyor (ayrıştırılamaz) → HAM.
    # Ticari ve KOBİ'de TL/YP ayrı → arındırılabilir.
    for ad, kol in (("tuketici", "k_tuketici"), ("konut", "k_konut"),
                    ("tasit", "k_tasit"), ("ihtiyac", "k_ihtiyac"),
                    ("bkk", "k_bkk"), ("kurumsal_kart", "k_kurumsal_kart"),
                    ("finansal", "k_finansal")):
        if kol in H.columns:
            s = H[kol]
            M[f"g_{ad}_13y"] = zincir_yillik(s / s.shift(1) - 1.0)
    for ad, ktl, kyp in (("ticari", "k_ticari_tl", "k_ticari_yp"),
                         ("kobi", "k_kobi_tl", "k_kobi_yp")):
        if {ktl, kyp} <= set(H.columns):
            M[f"g_{ad}_13y"] = zincir_yillik(ar_buyume(H[ktl], H[kyp], e))
            M[f"g_{ad}_ham_13y"] = zincir_yillik(ham_buyume(H[ktl], H[kyp]))

    # --- stok, pay, kalite -------------------------------------------------
    M["kredi_toplam"] = H["kredi_toplam"] / 1e6          # bin TL → milyar TL
    M["kredi_tl_mlr"] = tl / 1e6
    M["kredi_yp_mlr"] = yp / 1e6
    M["yp_pay"] = yp / (tl + yp) * 100.0
    M["npl"] = (H["takip_toplam"] / (H["kredi_toplam"] + H["takip_toplam"])) * 100.0
    if {"k_takip_tuk", "k_tuketici"} <= set(H.columns):
        M["npl_tuketici"] = (H["k_takip_tuk"]
                             / (H["k_tuketici"] + H["k_takip_tuk"])) * 100.0
    if {"k_takip_tic", "k_fkdk"} <= set(H.columns):
        M["npl_ticari"] = (H["k_takip_tic"] / (H["k_fkdk"] + H["k_takip_tic"])) * 100.0
    if {"k_karsilik", "takip_toplam"} <= set(H.columns):
        M["karsilik_orani"] = (H["k_karsilik"] / H["takip_toplam"]) * 100.0
    # PAYDA: sektör bilançosunun TOPLAM mevduatı (yurt içi + yurt dışı).
    # Pay da TOPLAM kredidir. Bu oran, TL/YP kırılımından kurulan ZK tabanı
    # mevduatıyla AYNI büyüklük DEĞİLDİR; ozet.json'a tabanı adında taşıyan
    # ayrı bir anahtar olarak yazılır.
    M["kredi_mevduat"] = (H["kredi_toplam"] / H["mevduat_toplam"]) * 100.0
    M["mevduat_sektor_toplam_mlr"] = H["mevduat_toplam"] / 1e6
    return M


# ===========================================================================
#  3. Laspeyres ayrıştırma — Γ (kur etkisi) / Λ (gerçek akım)
# ===========================================================================
def ayristir(H: pd.DataFrame, K: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Γ_s = K^{YP,fc}_{s−1}·Δe_s   ·   Λ_s = ΔK^{TL}_s + e_s·ΔK^{YP,fc}_s
    Kimlik: Γ + Λ = ΔK. Artık makine hassasiyetinde olmalı."""
    e = K["sepet"]
    tl, yp = H["kredi_tl"], H["kredi_yp"]
    yp_fc = yp / e                                   # YP kredi, döviz cinsinden
    gama = yp_fc.shift(1) * (e - e.shift(1))
    lamda = (tl - tl.shift(1)) + e * (yp_fc - yp_fc.shift(1))
    delta = (tl + yp) - (tl + yp).shift(1)
    artik = gama + lamda - delta
    # Simetrik (Bennet) varyant — TANI: Γ_L − Γ_B = −½·ΔK^fc·Δe
    gama_b = 0.5 * (yp_fc.shift(1) + yp_fc) * (e - e.shift(1))
    A = pd.DataFrame({"gama": gama / 1e6, "lamda": lamda / 1e6,
                      "delta": delta / 1e6, "artik": artik / 1e6,
                      "gama_bennet": gama_b / 1e6,
                      "yp_fc_mn": yp_fc / 1e3})     # bin TL/kur → milyon döviz
    bagil = (artik.abs() / delta.abs().replace(0, np.nan)).dropna()
    maks = float(bagil.max()) if len(bagil) else np.nan
    if pd.notna(maks) and maks > ESIK_KIMLIK:
        uyar(f"KİMLİK: Laspeyres ayrıştırmasında Γ+Λ=ΔK kimliği kapanmıyor "
             f"(en büyük bağıl artık {maks:.2e}, tolerans {ESIK_KIMLIK:.0e}).")
    # Zincirleme sapması D_T (yayımlanmaz, DENETLENİR)
    son = A.index[-1]
    cipa_i = max(0, len(A) - 1 - PENCERE)
    cipa = A.index[cipa_i]
    d_t = float(gama.loc[cipa:son].sum()
                - yp_fc.loc[cipa] * (e.loc[son] - e.loc[cipa])) / 1e6
    tani = {"artik_bagil_maks": maks,
            "d_zincir_mlr": d_t,
            "d_cipa": cipa.strftime("%Y-%m-%d"),
            "gama_bennet_farki_mlr": float((A["gama"] - A["gama_bennet"])
                                           .loc[cipa:son].sum())}
    return A, tani


# ===========================================================================
#  4. Uzun tarihçe — arşiv ile büyüme oranı düzeyinde birleştirme
# ===========================================================================
def uzun_tarihce(H: pd.DataFrame, ARS: pd.DataFrame, G: pd.DataFrame,
                 K: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Eski haftalık tablolar 31.01.2025'te kapandı, yeni tablolar 28.06.2024'te
    başladı. SEVİYEDE UÇ UCA EKLEME YASAK (yeni tanım ~%0,7 düşük ve oran
    sürükleniyor); birleştirme yalnız BÜYÜME ORANI düzeyinde yapılır ve
    kırılma tarihi ozet.json'a yazılır."""
    tl_kol = [c for c in ARS.columns if c.startswith("a_tl_")]
    yp_kol = [c for c in ARS.columns if c.startswith("a_yp_")]
    if not tl_kol or not yp_kol:
        uyar("UZUN TARİHÇE: arşiv TL/YP kalemleri yüklenemedi — kredi büyümesi "
             "yalnız yeni tabloların başladığı tarihten itibaren çizilecek.")
        return pd.DataFrame(), {}
    a_tl = ARS[tl_kol].sum(axis=1, min_count=len(tl_kol))
    a_yp = ARS[yp_kol].sum(axis=1, min_count=len(yp_kol))
    ars_e, _ = geri_tasi(G["sepet_gunluk"] if "sepet_gunluk" in G else G["usd"],
                         a_tl.index)
    # Arşiv penceresinde sepet kuru da var (ZK tabanı 2005'ten): haftalık panele
    # eşle; yoksa USD'ye düş.
    sepet_tam = K["sepet"].reindex(a_tl.index)
    ars_e = sepet_tam.where(sepet_tam.notna(), ars_e)
    g_ars = ar_buyume(a_tl, a_yp, ars_e)

    yeni_bas = H[["kredi_tl", "kredi_yp"]].dropna(how="any").index.min()
    ars_son = a_tl.dropna().index.max()
    # örtüşme denetimi: seviyede oran ve SÜRÜKLENMESİ
    ort = pd.concat([ARS["a_toplam"], H["kredi_toplam"]], axis=1).dropna()
    tani: dict = {"yeni_bas": yeni_bas.strftime("%Y-%m-%d"),
                  "arsiv_son": ars_son.strftime("%Y-%m-%d"),
                  "ortusme_hafta": int(len(ort))}
    if len(ort) >= 4:
        oran = (ort.iloc[:, 0] / ort.iloc[:, 1])
        surukleme = float(oran.iloc[-1] - oran.iloc[0])
        tani.update({"oran_ilk": float(oran.iloc[0]), "oran_son": float(oran.iloc[-1]),
                     "oran_surukleme": surukleme})
        if abs(surukleme) > ESIK_ORTUSME:
            _b = _bicim()
            uyar(f"SERİ KIRILMASI: arşiv/yeni kredi oranı örtüşme penceresinde "
                 f"{_b.sayi(oran.iloc[0], 5)} → {_b.sayi(oran.iloc[-1], 5)} sürüklendi "
                 f"({_b.sayi(surukleme, 5, isaret=True)}, tolerans ±{_b.sayi(ESIK_ORTUSME, 3)}). Tek çarpanla "
                 "dönüştürme yanlış olurdu; birleştirme büyüme oranı düzeyinde yapıldı.")
    # birleştirme: kırılmadan ÖNCE arşiv, SONRA yeni
    g_yeni = ar_buyume(H["kredi_tl"], H["kredi_yp"], K["sepet"])
    g = pd.concat([g_ars[g_ars.index < yeni_bas], g_yeni[g_yeni.index >= yeni_bas]])
    g = g[~g.index.duplicated(keep="last")].sort_index()
    g_ham_ars = ham_buyume(a_tl, a_yp)
    g_ham_yeni = ham_buyume(H["kredi_tl"], H["kredi_yp"])
    gh = pd.concat([g_ham_ars[g_ham_ars.index < yeni_bas],
                    g_ham_yeni[g_ham_yeni.index >= yeni_bas]])
    gh = gh[~gh.index.duplicated(keep="last")].sort_index()
    U = pd.DataFrame({"g_ar": g, "g_ham": gh})
    U["g_ar_13y"] = zincir_yillik(U["g_ar"])
    U["g_ham_13y"] = zincir_yillik(U["g_ham"])
    U["g_ar_52"] = zincir_donem(U["g_ar"], YIL_HAFTA)
    # Kırılma haftasında ZİNCİR KOPARILIR: 28.06.2024'ten önceki son arşiv
    # haftasıyla ilk yeni hafta arasındaki "büyüme" iki farklı tanımın farkıdır.
    U.loc[yeni_bas, ["g_ar", "g_ham"]] = np.nan
    tani["kirilma"] = yeni_bas.strftime("%Y-%m-%d")
    return U, tani


# ===========================================================================
#  5. Parasal büyüklükler, çarpan, doğrulama
# ===========================================================================
def para_metrikleri(H: pd.DataFrame, G: pd.DataFrame, K: pd.DataFrame
                    ) -> tuple[pd.DataFrame, dict]:
    P = pd.DataFrame(index=H.index)
    e = K["sepet"]
    # M1/M2/M3 seviyeleri (bin TL → milyar TL)
    for ad in ("m1", "m2", "m3"):
        P[f"{ad}_mlr"] = H[ad] / 1e6
    # TL / YP bacakları — arındırma için.
    # TL bacağı, YAYIMLANAN TOPLAMDAN türetilir (M − YP), bileşenler toplanarak
    # DEĞİL: M3'ün TL tarafındaki "ihraç edilen menkul kıymetler" kalemi
    # 31.12.2010'da başlıyor ve öncesinde boş; bileşenleri toplayıp boşluğu
    # sıfırla doldurmak seride sahte bir sıçrama üretiyordu (ölçüldü: HAMM3
    # endeksiyle 15 puana kadar ayrışma). Toplamdan çıkarma, TL+YP = yayımlanan
    # M kimliğini tanım gereği kapatır.
    m1_yp = H["vadesiz_yp"]
    m1_tl = H["m1"] - m1_yp
    m2_yp = m1_yp + H["vadeli_yp"]
    m2_tl = H["m2"] - m2_yp
    m3_yp = m2_yp
    m3_tl = H["m3"] - m3_yp
    # TCMB'nin KENDİ endeksleri (30.12.2005=100) — hem seri hem sınav
    for ad in ("m1", "m2", "m3"):
        for on in ("ham", "ar"):
            kol = f"{on}_{ad}"
            if kol in H.columns:
                idx = H[kol]
                P[f"tcmb_{on}_{ad}_13y"] = zincir_yillik(idx / idx.shift(1) - 1.0)

    # SERİ KIRILMASI — VERİDEN bulunur, tarih GÖMÜLMEZ.
    # Ölçüldü: para arzı SEVİYE tablosu (bie_hpbitablo1) 28.06.2024'te yeni
    # tanıma geçiyor ve M3 o hafta endekse göre %2,4 sıçrıyor; TCMB'nin kendi
    # endeksi (bie_kavramsal) kırılmayı zincirleyerek geçiyor. Seviyeden
    # hesaplanan haftalık büyüme o hafta İKİ FARKLI TANIMIN FARKIDIR, büyüme
    # değildir: zincir o haftada KOPARILIR (NaN) ve tarih ozet.json'a yazılır.
    kirilma: list[str] = []
    kirilma_okur: list[str] = []          # okura: "M3 (28.06.2024)" — anahtar:ISO değil
    for ad, tl, yp in (("m1", m1_tl, m1_yp), ("m2", m2_tl, m2_yp), ("m3", m3_tl, m3_yp)):
        g_ham = ham_buyume(tl, yp)
        g_ar = ar_buyume(tl, yp, e)
        kol = f"ham_{ad}"
        if kol in H.columns:
            g_idx = H[kol] / H[kol].shift(1) - 1.0
            sapan = ((g_ham - g_idx).abs() > 0.005) & g_idx.notna()
            for t in g_ham.index[sapan.fillna(False)]:
                g_ham.loc[t] = np.nan
                g_ar.loc[t] = np.nan
                iz = f"{ad}:{t:%Y-%m-%d}"
                if iz not in kirilma:
                    kirilma.append(iz)
                    kirilma_okur.append(f"{ad.upper()} ({t:%d.%m.%Y})")
        P[f"g_{ad}_ar_13y"] = zincir_yillik(g_ar)
        P[f"g_{ad}_ham_13y"] = zincir_yillik(g_ham)
    if kirilma:
        uyar("SERİ KIRILMASI (para arzı): seviye tablosu ile TCMB endeksi şu "
             "hafta(lar)da %0,5'ten fazla ayrıştı, zincir o haftalarda koparıldı: "
             + ", ".join(kirilma_okur) + ". Seviye grafiğinde kırılma işaretlenir.")
    P.attrs["kirilma"] = kirilma

    # Para çarpanı — rezerv para (analitik bilanço, iş günü) Cuma'ya eşlenir
    rp, _ = geri_tasi(G["ab_rezerv_para"], H.index)
    zk, _ = geri_tasi(G["ab_zk_bloke"], H.index)
    emisyon, _ = geri_tasi(G["ab_emisyon"], H.index)
    serbest, _ = geri_tasi(G["ab_serbest"], H.index)
    mbp, _ = geri_tasi(G["ab_mbp"], H.index)
    P["rezerv_para_mlr"] = rp / 1e6
    P["zk_bloke_mlr"] = zk / 1e6
    P["emisyon_mlr"] = emisyon / 1e6
    P["serbest_mevduat_mlr"] = serbest / 1e6
    P["mb_parasi_mlr"] = mbp / 1e6
    for ad in ("m1", "m2", "m3"):
        P[f"carpan_{ad}"] = H[ad] / rp
    P["emisyon_m1"] = emisyon / H["m1"] * 100.0
    # İma edilen bileşik ZK oranı — TCMB'nin İLAN ETTİĞİ oran DEĞİLDİR:
    # vade dilimine ve para cinsine göre farklı oranlar uygulanır, YP karşılık
    # döviz olarak tutulabilir. "Gerçekleşmiş tesis oranı" diye etiketlenir.
    if "zk_taban" in H.columns:
        P["zk_ima_oran"] = zk / H["zk_taban"] * 100.0

    # --- DOĞRULAMA ---------------------------------------------------------
    # İki ayrı sınav, iki ayrı soru:
    #  (A) HAM sınavı — KİMLİK sorusu. Seviye tablosundan (bie_hpbitablo1)
    #      hesapladığımız büyüme, TCMB'nin ayrı bir üründe yayımladığı ham
    #      endeksten (bie_kavramsal HAMM*) hesaplanan büyümeye EŞİT olmalıdır.
    #      Tutmazsa kalem eşlemesi ya da birim bozulmuştur → hat DURUR.
    #  (B) ARINDIRILMIŞ sınavı — YÖNTEM sorusu. TCMB'nin ARIM* endeksinin
    #      arındırma yöntemi yayımlanmıyor; eşitlik BEKLENMEZ. Ölçülen:
    #      yanlılık (ortalama işaretli fark), RMSE ve korelasyon. Yanlılık
    #      eşiği aşarsa uyarı düşer; sayfada ikisi birlikte gösterilir.
    dog: dict = {"ham": {}, "arindirilmis": {}}

    def _kiyas(biz: pd.Series, tcmb: pd.Series) -> dict:
        b, t = biz.dropna(), tcmb.dropna()
        ortak = b.index.intersection(t.index)[-104:]
        if len(ortak) < 13:
            return {"n": 0, "not": "ortak gözlem yetersiz"}
        f = b[ortak] - t[ortak]
        return {"n": int(len(ortak)),
                "yanlilik_pp": float(f.mean()),
                "maks_pp": float(f.abs().max()),
                "rmse_pp": float(np.sqrt((f ** 2).mean())),
                "korel": float(b[ortak].corr(t[ortak])),
                "biz_son": float(b[ortak[-1]]), "tcmb_son": float(t[ortak[-1]]),
                "tarih": ortak[-1].strftime("%Y-%m-%d")}

    for ad in ("m1", "m2", "m3"):
        if f"tcmb_ham_{ad}_13y" in P.columns:
            dog["ham"][ad] = _kiyas(P[f"g_{ad}_ham_13y"], P[f"tcmb_ham_{ad}_13y"])
        if f"tcmb_ar_{ad}_13y" in P.columns:
            dog["arindirilmis"][ad] = _kiyas(P[f"g_{ad}_ar_13y"], P[f"tcmb_ar_{ad}_13y"])
    dog["esik_ham_pp"] = ESIK_HAM_ENDEKS_PP
    dog["esik_ar_yanlilik_pp"] = ESIK_AR_ENDEKS_PP
    a2 = dog["arindirilmis"].get("m2") or {}
    if a2.get("n") and abs(a2["yanlilik_pp"]) > ESIK_AR_ENDEKS_PP:
        uyar(f"DOĞRULAMA (yöntem): bizim arındırdığımız M2 büyümesi TCMB'nin kendi "
             f"arındırılmış endeksinden (ARIM2) ortalama {a2['yanlilik_pp']:+.2f} puan "
             f"sapıyor (tolerans ±{ESIK_AR_ENDEKS_PP}). Arındırma yöntemi ya da kur "
             "seçimi gözden geçirilmeli.")
    dog["para_kirilma"] = P.attrs.get("kirilma", [])
    return P, dog


# ===========================================================================
#  6. Mevduat kompozisyonu ve dolarizasyon
# ===========================================================================
def dolarizasyon(H: pd.DataFrame, K: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Ham pay TL karşılığı üzerinden hesaplandığı için kur yükselirken
    KENDİLİĞİNDEN yükselir. Arındırılmış pay YP mevduatı ÇIPA haftasının
    kuruyla yeniden değerler. İkisi BİRLİKTE yayımlanır; ham pay tek başına
    yayımlanmaz."""
    D = pd.DataFrame(index=H.index)
    e = K["sepet"]
    tl, yp = H["zk_tl_taban"], H["zk_dth"]
    D["mevduat_tl_mlr"] = tl / 1e6
    D["mevduat_yp_mlr"] = yp / 1e6
    D["dth_pay_ham"] = yp / (tl + yp) * 100.0
    # ÇIPA: içinde bulunulan takvim yılının ilk gözlemi. Yıl dönünce çıpa da
    # döner; MDX metnindeki tarih ozet.json'dan gelir, elle yazılmaz.
    dolu = D["dth_pay_ham"].dropna()
    if dolu.empty:
        return D, {}
    son = dolu.index[-1]
    yil_ici = dolu[dolu.index >= pd.Timestamp(son.year, 1, 1)]
    cipa = yil_ici.index[0] if len(yil_ici) else dolu.index[max(0, len(dolu) - 53)]
    e_cipa = float(e.get(cipa, np.nan))
    yp_sabit = yp * (e_cipa / e)
    D["dth_pay_ar"] = yp_sabit / (tl + yp_sabit) * 100.0
    D["mevduat_yp_sabit_mlr"] = yp_sabit / 1e6
    # ÇIPADAN ÖNCESİ SİLİNİR. Sabit kurla değerlenmiş pay ÇIPAYA GÖRE tanımlıdır:
    # 2018'in DTH'ını 2026 kuruyla değerlemek payı %90'a çıkarır ve bu bir
    # dolarizasyon okuması değil, bir kur okumasıdır. Seriyi çıpanın gerisine
    # uzatmak, arındırmanın anlamını sessizce tersine çevirirdi.
    D.loc[D.index < cipa, ["dth_pay_ar", "mevduat_yp_sabit_mlr"]] = np.nan
    # bilanço tarafındaki karşılık (yurt içi yerleşik mevduat) — kıyas
    if {"mevduat_tl", "mevduat_yp"} <= set(H.columns):
        D["bilanco_pay_ham"] = (H["mevduat_yp"]
                                / (H["mevduat_tl"] + H["mevduat_yp"])) * 100.0
    if "mevduat_yp_usd" in H.columns:
        D["mevduat_yp_usd_mia"] = H["mevduat_yp_usd"] / 1e3   # mn USD → mia USD
    tani = {"cipa": cipa.strftime("%Y-%m-%d"), "cipa_kur": e_cipa,
            "ham_cipa": float(D["dth_pay_ham"].get(cipa, np.nan)),
            "ham_son": float(D["dth_pay_ham"].get(son, np.nan)),
            "ar_son": float(D["dth_pay_ar"].get(son, np.nan))}
    return D, tani


# ===========================================================================
#  7. Faizler, makas, reel faiz
# ===========================================================================
def faiz_metrikleri(H: pd.DataFrame, G: pd.DataFrame, A: pd.DataFrame) -> pd.DataFrame:
    F = pd.DataFrame(index=H.index)
    for k in ("f_ticari_tl", "f_ticari_dar", "f_ihtiyac", "f_konut", "f_tasit",
              "f_tuketici", "mev_tl", "kat_ticari", "kat_tuketici"):
        if k in H.columns:
            F[k] = H[k]
    for ad, kol in (("politika", "politika"), ("aofm", "aofm"),
                    ("koridor_alt", "koridor_alt"), ("koridor_ust", "koridor_ust")):
        if kol in G.columns:
            F[ad], kay = geri_tasi(G[kol], H.index)
            if ad == "aofm":
                F["aofm_kaynak_gun"] = kay
    # AOFM TABANI: fonlama sıfıra yakınken ağırlıklı ortalaması "sistemin
    # fonlama maliyeti" DEĞİLDİR — 0,7 milyar TL'lik bir fonlamanın fiyatı
    # sistem hakkında bilgi taşımaz. Fonlama hattı bu günleri geçersiz sayıp
    # metinde "fonlama maliyeti" cümlesi kurmuyor; iki kardeş sayfanın AYNI
    # GÜN aynı sayı için çelişmemesi adına eşik burada da BİREBİR aynıdır.
    if "aofm" in F.columns and "fon_toplam" in G.columns:
        taban, _ = geri_tasi(G["fon_toplam"], H.index)
        F["aofm_taban_mn_tl"] = taban
        F["aofm_gecerli"] = (taban.notna() & (taban >= AOFM_TABAN_ESIK)
                             & F["aofm"].notna())
        F["aofm_ham"] = F["aofm"]
        F["aofm"] = F["aofm"].where(F["aofm_gecerli"])
        gecersiz = int((F["aofm_ham"].notna() & ~F["aofm_gecerli"]).tail(52).sum())
        if gecersiz:
            uyar(f"AOFM TABANSIZ: son 52 haftanın {gecersiz}'inde APİ "
                 f"fonlaması {AOFM_TABAN_ESIK / 1000:.0f} milyar TL eşiğinin "
                 "altında olduğu hâlde EVDS bir AOFM basmış. O haftalar "
                 "geçersiz işaretlendi; 'kredi − AOFM' makası üretilmedi. "
                 "Fonlama hattı aynı eşiği kullanır.")
    if {"f_ticari_tl", "mev_tl"} <= set(F.columns):
        F["makas_kredi_mevduat"] = F["f_ticari_tl"] - F["mev_tl"]
    if {"f_ticari_tl", "politika"} <= set(F.columns):
        F["spread_politika"] = F["f_ticari_tl"] - F["politika"]
    if {"f_ticari_tl", "aofm"} <= set(F.columns):
        F["spread_aofm"] = F["f_ticari_tl"] - F["aofm"]
    # REEL kredi faizi — TAM FISHER. (i − π) yaklaşımı YASAK: %50'lik faiz ve
    # %30'luk beklenti düzeyinde iki tanım arasındaki fark puanlarla ölçülür.
    if "pka_12a" in A.columns:
        bek = A["pka_12a"].dropna()
        if len(bek):
            bek_h = bek.reindex(H.index.union(bek.index)).ffill().reindex(H.index)
            F["pka_12a"] = bek_h
            # BEKLENTİNİN YAŞI: aylık anket haftalık eksene ffill ediliyor.
            # Anket yayını gecikirse reel faiz sessizce ESKİ beklentiyle
            # hesaplanmaya devam eder; yaş taşınmazsa bu sayfada görünmez.
            tas = pd.Series(bek.index, index=bek.index).reindex(
                H.index.union(bek.index)).ffill().reindex(H.index)
            F["pka_yas_gun"] = (pd.Series(H.index, index=H.index) - tas).dt.days
            for ad, kol in (("reel_ticari", "f_ticari_tl"),
                            ("reel_tuketici", "f_tuketici"),
                            ("reel_mevduat", "mev_tl")):
                if kol in F.columns:
                    F[ad] = ((1 + F[kol] / 100) / (1 + bek_h / 100) - 1) * 100
                    F[f"{ad}_yaklasik"] = F[kol] - bek_h     # TANI: yasak tanım
    return F


# ===========================================================================
#  8. Aylık panel — banka türü, KKM, katılım dahil/hariç
# ===========================================================================
def aylik_metrikleri(A: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    M = pd.DataFrame(index=A.index)
    for k in ("kh_toplam", "kh_mevduat", "kh_katilim", "kh_kalkinma",
              "kh_sirket", "kh_hane", "kb_toplam"):
        if k in A.columns:
            M[f"{k}_mlr"] = A[k] / 1e6
    if {"kh_toplam", "kh_katilim"} <= set(A.columns):
        haric = A["kh_toplam"] - A["kh_katilim"]
        M["kh_haric_mlr"] = haric / 1e6
        # AYLIK veride TL/YP kırılımı yok → bu büyümeler HAM'dır, kur etkisi
        # içerir. Sayfada haftalık arındırılmış seriyle aynı cümlede anılmaz.
        M["g_kh_toplam_yil"] = (A["kh_toplam"] / A["kh_toplam"].shift(12) - 1) * 100
        M["g_kh_haric_yil"] = (haric / haric.shift(12) - 1) * 100
        M["g_kh_katilim_yil"] = (A["kh_katilim"] / A["kh_katilim"].shift(12) - 1) * 100
        M["katilim_pay"] = A["kh_katilim"] / A["kh_toplam"] * 100
    # KKM — aylık stok. "Bitmiş rejim" bayrağı: sıfıra düşmüş bir olguyu
    # yorumlamaya devam etmek, hiç güncellenmeyen bir sayıdan kötüdür.
    kkm_tani: dict = {}
    if "kkm_tl" in A.columns:
        M["kkm_tl_mlr"] = A["kkm_tl"]          # zaten milyar TL
        M["kkm_tl_degisim"] = A["kkm_tl"].diff()
        s = A["kkm_tl"].dropna()
        if len(s):
            zirve = s.idxmax()
            kkm_tani = {"zirve_tarih": zirve.strftime("%Y-%m-%d"),
                        "zirve_mlr_tl": float(s.max()),
                        "son_mlr_tl": float(s.iloc[-1]),
                        "son_tarih": s.index[-1].strftime("%Y-%m-%d"),
                        "aktif": bool(float(s.iloc[-1]) > 1.0)}
            # erime hızı: zirveden bugüne ortalama aylık düşüş
            ay = max(1, (s.index[-1].to_period("M") - zirve.to_period("M")).n)
            kkm_tani["erime_ay_mlr"] = float((s.max() - s.iloc[-1]) / ay)
            kkm_tani["erime_ay"] = int(ay)
            son12 = s.diff().tail(12).mean()
            kkm_tani["son12_ay_ort_degisim"] = float(son12) if pd.notna(son12) else None
    if "kkm_ddkkm" in A.columns:
        M["kkm_usd_mia"] = A["kkm_ddkkm"]      # milyar USD
        d = A["kkm_ddkkm"].dropna()
        if len(d):
            kkm_tani["ddkkm_son_mia_usd"] = float(d.iloc[-1])
            kkm_tani["ddkkm_zirve_mia_usd"] = float(d.max())
    if kkm_tani and not kkm_tani.get("aktif", True):
        uyar("KKM: program fiilen kapanmış (stok ~0). Sayfa metni programı "
             "kapanmış sayar; 'KKM çıkışı' gerekçesi güncel dolarizasyon "
             "yorumunda KULLANILMAZ — seri taze, olgu bitmiş.")
    return M, kkm_tani


def kredi_capraz_dogrulama(H: pd.DataFrame, A: pd.DataFrame) -> dict:
    """Kredi seviyesinin BAĞIMSIZ sınavı: haftalık yurt içi krediler
    (bie_hpbitablo6, Cuma) ile aylık bankacılık sektörü kredileri
    (bie_krehacbs, ay sonu) EVDS'te AYRI ürünlerdir ve ayrı derlenir.

    Bire bir eşitlik BEKLENMEZ: haftalık serinin ay içindeki son gözlemi Cuma'ya,
    aylık seri ayın son gününe denk gelir; kapsam da tıpatıp aynı değildir
    (yurt içi şubeler ↔ bankacılık sektörü). Sınav, SEVİYE ORANININ dar bir bantta
    kalması ve 12 aylık büyümelerin puan mertebesinde uyuşmasıdır."""
    if "k_yi_toplam" not in H.columns or "kh_toplam" not in A.columns:
        return {"n": 0, "not": "seriler yüklenemedi"}
    w = H["k_yi_toplam"].dropna().resample("MS").last()
    m = A["kh_toplam"].dropna()
    d = pd.concat([w.rename("haftalik"), m.rename("aylik")], axis=1).dropna()
    if len(d) < 6:
        return {"n": int(len(d)), "not": "örtüşme yetersiz"}
    oran = d["haftalik"] / d["aylik"]
    d["g_h"] = (d["haftalik"] / d["haftalik"].shift(12) - 1) * 100
    d["g_a"] = (d["aylik"] / d["aylik"].shift(12) - 1) * 100
    dd = d.dropna(subset=["g_h", "g_a"])
    cikti = {"n": int(len(d)), "oran_ort": float(oran.mean()),
             "oran_std": float(oran.std()),
             "oran_min": float(oran.min()), "oran_maks": float(oran.max()),
             "esik_pp": ESIK_KREDI_CAPRAZ_PP}
    if len(dd):
        f = dd["g_h"] - dd["g_a"]
        cikti.update({"buyume_n": int(len(dd)),
                      "buyume_yanlilik_pp": float(f.mean()),
                      "buyume_maks_pp": float(f.abs().max()),
                      "haftalik_son": float(dd["g_h"].iloc[-1]),
                      "aylik_son": float(dd["g_a"].iloc[-1]),
                      "tarih": dd.index[-1].strftime("%Y-%m-%d")})
        if float(f.abs().max()) > ESIK_KREDI_CAPRAZ_PP:
            uyar(f"DOĞRULAMA (kredi): haftalık ve aylık kredi serilerinin 12 aylık "
                 f"büyümesi en çok {f.abs().max():.2f} puan ayrışıyor "
                 f"(tolerans {ESIK_KREDI_CAPRAZ_PP}). İki ürün arasında kapsam ya da "
                 "hizalama değişmiş olabilir.")
    if not (0.98 < float(oran.mean()) < 1.02):
        uyar(f"DOĞRULAMA (kredi): haftalık/aylık kredi seviyesi oranı "
             f"{oran.mean():.4f} — 1'e yakın olmalıydı. Kapsam ya da birim değişmiş olabilir.")
    return cikti


# ===========================================================================
#  9. Kredi büyümesi ↔ enflasyon momentumu (Enflasyon hattıyla çapraz)
# ===========================================================================
ENF_YOL = veri.KOK / "Aktarılacak Projeler" / "Enflasyon" / "data" / "metrik.csv"


def enflasyon_caprazi(M: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Gecikmeli KORELASYON ölçüsüdür, NEDENSELLİK İDDİASI DEĞİLDİR.
    Aynı pencerede her iki seriyi de kur hareketi besliyor olabilir; kredi
    tarafında arındırılmış seriyi kullanmak bu yüzden yalnız doğruluk değil,
    AYRIŞTIRMA meselesidir."""
    if not ENF_YOL.exists():
        uyar(f"ÇAPRAZ: Enflasyon hattının metrik dosyası yok ({ENF_YOL}) — "
             "kredi/enflasyon şekli üretilemeyecek. Önce Enflasyon hattını koşun.")
        return pd.DataFrame(), {}
    try:
        E = pd.read_csv(ENF_YOL, index_col=0, parse_dates=True)
        E = E[E["seri"] == "tufe"][["saar3_sa", "saar6_sa", "yillik"]].sort_index()
    except Exception as ex:
        uyar(f"ÇAPRAZ: Enflasyon metrik dosyası okunamadı ({ex}).")
        return pd.DataFrame(), {}
    kredi_ay = M["g_ar_13y"].dropna().resample("MS").mean()
    ham_ay = M["g_ham_13y"].dropna().resample("MS").mean()
    C = pd.concat([kredi_ay.rename("kredi_ar_13y"), ham_ay.rename("kredi_ham_13y"),
                   E["saar3_sa"].rename("enf_3a"), E["saar6_sa"].rename("enf_6a"),
                   E["yillik"].rename("enf_yillik")], axis=1)
    C = C.dropna(subset=["kredi_ar_13y"], how="all")
    ort = C[["kredi_ar_13y", "enf_6a"]].dropna()
    tani: dict = {"n": int(len(ort))}
    if len(ort) >= 18:
        korel = {}
        for gecikme in range(-12, 13):
            x = ort["kredi_ar_13y"]
            y = ort["enf_6a"].shift(-gecikme)
            k = pd.concat([x, y], axis=1).dropna()
            if len(k) >= 12:
                korel[gecikme] = float(k.iloc[:, 0].corr(k.iloc[:, 1]))
        if korel:
            en = max(korel, key=lambda g: abs(korel[g]))
            tani.update({"korel": korel, "en_iyi_gecikme": int(en),
                         "en_iyi_korel": float(korel[en]),
                         "esanli_korel": float(korel.get(0, np.nan))})
    else:
        tani["not"] = ("örtüşen gözlem 18 aydan az — haftalık kredi kırılımı "
                       "28.06.2024'te başlıyor; korelasyon hesaplanmadı.")
        uyar("ÇAPRAZ: kredi–enflasyon örtüşmesi kısa; gecikmeli korelasyon "
             "hesaplanmadı (uzun tarihçe serisi ayrıca çiziliyor).")
    return C, tani


def uzun_capraz(U: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Uzun tarihçeli (arşiv+yeni birleşik) kredi büyümesi ile enflasyon
    momentumu — korelasyon buradan hesaplanır, örtüşme 2005'e uzanır."""
    if U.empty or not ENF_YOL.exists():
        return pd.DataFrame(), {}
    try:
        E = pd.read_csv(ENF_YOL, index_col=0, parse_dates=True)
        E = E[E["seri"] == "tufe"][["saar3_sa", "saar6_sa", "yillik"]].sort_index()
    except Exception:
        return pd.DataFrame(), {}
    kredi_ay = U["g_ar_13y"].dropna().resample("MS").mean()
    C = pd.concat([kredi_ay.rename("kredi_ar_13y"),
                   E["saar6_sa"].rename("enf_6a"),
                   E["saar3_sa"].rename("enf_3a"),
                   E["yillik"].rename("enf_yillik")], axis=1).dropna(
                       subset=["kredi_ar_13y"])
    ort = C[["kredi_ar_13y", "enf_6a"]].dropna()
    tani: dict = {"n": int(len(ort))}
    if len(ort) >= 36:
        # k > 0: kredi BUGÜN ↔ enflasyon k ay SONRA (kredi öncül)
        # k < 0: kredi bugün ↔ enflasyon k ay ÖNCE (enflasyon öncül)
        korel = {}
        for gecikme in range(-GECIKME_UFKU, GECIKME_UFKU + 1):
            k = pd.concat([ort["kredi_ar_13y"],
                           ort["enf_6a"].shift(-gecikme)], axis=1).dropna()
            if len(k) >= 24:
                korel[gecikme] = float(k.iloc[:, 0].corr(k.iloc[:, 1]))
        if korel:
            en = max(korel, key=lambda g: abs(korel[g]))
            tani.update({"korel": korel, "en_iyi_gecikme": int(en),
                         "en_iyi_korel": float(korel[en]),
                         "esanli_korel": float(korel.get(0, np.nan)),
                         "ufuk": GECIKME_UFKU,
                         "bas": ort.index[0].strftime("%Y-%m-%d"),
                         "son": ort.index[-1].strftime("%Y-%m-%d")})
            # Tepe pencerenin UCUNDAYSA gerçek tepe dışarıda olabilir; "öncül
            # gösterge" cümlesi bu durumda kurulmaz.
            if abs(en) == GECIKME_UFKU:
                tani["ucta"] = True
                uyar(f"ÇAPRAZ: gecikmeli korelasyonun tepesi pencerenin ucunda "
                     f"({en} ay). Gerçek tepe ±{GECIKME_UFKU} ayın dışında olabilir; "
                     "sayfada 'şu kadar ay öncül' cümlesi kurulmaz.")
    return C, tani


# ===========================================================================
#  ana akış
# ===========================================================================
def kos() -> dict:
    H = _oku("haftalik.csv")
    ARS = _oku("arsiv.csv")
    G = _oku("gunluk.csv")
    A = _oku("aylik.csv")
    C = _oku("ceyreklik.csv")
    durum = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    for u in durum.get("uyarilar", []):
        if u not in UYARI:
            UYARI.append(u)

    s_h = veri.son_hafta(H)
    s_g = veri.son_gun(G)
    s_a = veri.son_ay(A)
    s_c = veri.son_ceyrek(C)
    print(f"Kredi & parasal büyüklükler — hesap katmanı")
    print(f"  çıpa: hafta {ad_gun(s_h)} · iş günü {ad_gun(s_g)} · "
          f"ay {ad_uzun(s_a)} · çeyrek {ad_ceyrek(s_c)}")

    K = kur_kur(H, G)
    M = kredi_metrikleri(H, K)
    duyar = kur_duyarlilik(H, K, M)
    AY_, ayr_tani = ayristir(H, K)
    U, uzun_tani = uzun_tarihce(H, ARS, G, K)
    P, dog = para_metrikleri(H, G, K)
    D, dol_tani = dolarizasyon(H, K)
    F = faiz_metrikleri(H, G, A)
    AM, kkm_tani = aylik_metrikleri(A)
    CX, capraz_tani = enflasyon_caprazi(M)
    CU, uzun_capraz_tani = uzun_capraz(U)

    # --- yöntem tanıları -> uyarı ------------------------------------------
    cz = M["cipa_zincir_farki"].dropna()
    if len(cz) and float(cz.abs().tail(52).max()) > ESIK_CIPA_ZINCIR_PP:
        uyar(f"ARINDIRMA TANI: çıpalı ve zincirleme arındırma son bir yılda en çok "
             f"{cz.abs().tail(52).max():.2f} puan ayrıştı (tolerans "
             f"{ESIK_CIPA_ZINCIR_PP}). Kur ile YP kredi payı birlikte hareket "
             "ediyor olabilir.")
    us = M["usd_sepet_farki_13y"].dropna()
    if len(us) and float(us.abs().tail(52).max()) > ESIK_USD_SEPET_PP:
        uyar(f"KUR SEÇİMİ TANI: USD ile sepet kuru arındırması son bir yılda en çok "
             f"{us.abs().tail(52).max():.2f} puan ayrıştı (tolerans "
             f"{ESIK_USD_SEPET_PP}). Sepet varsayımı sayfada açıkça yazılmalı.")

    # --- DOĞRULAMA ---------------------------------------------------------
    kredi_dog = kredi_capraz_dogrulama(H, A)
    dog["kredi_capraz"] = kredi_dog
    for ad in ("m1", "m2", "m3"):
        h = (dog.get("ham") or {}).get(ad) or {}
        if h.get("n"):
            print(f"  DOĞRULAMA · ham {ad.upper()} (kimlik): seviyelerden "
                  f"{h['biz_son']:.2f}% ↔ TCMB endeksinden {h['tcmb_son']:.2f}% · "
                  f"maks fark {h['maks_pp']:.3f} puan (n={h['n']})")
    for ad in ("m1", "m2", "m3"):
        a = (dog.get("arindirilmis") or {}).get(ad) or {}
        if a.get("n"):
            print(f"  DOĞRULAMA · arındırılmış {ad.upper()} (yöntem): bizim yöntem "
                  f"{a['biz_son']:.2f}% ↔ TCMB {a['tcmb_son']:.2f}% · yanlılık "
                  f"{a['yanlilik_pp']:+.2f} puan · korel {a['korel']:.3f}")
    if kredi_dog.get("buyume_n"):
        print(f"  DOĞRULAMA · kredi (bağımsız ürün): haftalık {kredi_dog['haftalik_son']:.2f}% "
              f"↔ aylık {kredi_dog['aylik_son']:.2f}% (12 aylık) · yanlılık "
              f"{kredi_dog['buyume_yanlilik_pp']:+.2f} puan · seviye oranı "
              f"{kredi_dog['oran_ort']:.4f}±{kredi_dog['oran_std']:.4f}")
    he = (dog.get("ham") or {}).get("m2") or {}

    # --- son dönem özeti ---------------------------------------------------
    def _son_deger(df: pd.DataFrame, kol: str):
        if kol not in df.columns:
            return None
        s = df[kol].dropna()
        return float(s.iloc[-1]) if len(s) else None

    def _son_tarih(df: pd.DataFrame, kol: str):
        if kol not in df.columns:
            return None
        s = df[kol].dropna()
        return s.index[-1].strftime("%Y-%m-%d") if len(s) else None

    # Blok adı okura okur adıyla gider ('dol' değil 'dolarizasyon'); kayan
    # sütunların KODU koşu kaydına değil ozet.json'daki <blok>_kayan alanına yazılır.
    BLOK_ADI = {"dol": "dolarizasyon"}

    def _blok(df: pd.DataFrame, kolonlar: list[str], ad: str) -> dict:
        """Bir BLOĞUN tüm anahtarlarını TEK ORTAK tarihten okur.

        Sütunların son dolu gözlemleri farklı tarihlere düşebilir (ZK tabanı 13
        gün gecikmeli, bilanço aynı hafta gelir). Her sütunu bağımsız okumak
        ozet.json'da iki tarihi tek blokta karıştırır ve sayfa hepsini haftalık
        çıpa tarihliymiş gibi yan yana basar — 'aynı hafta karşılaştırması'
        diye sunulan fark, bir haftalık tarih kaymasının kendisi olur.
        """
        var = [k for k in kolonlar if k in df.columns and df[k].notna().any()]
        if not var:
            return {}
        sonlar = {k: df[k].dropna().index[-1] for k in var}
        ortak = min(sonlar.values())          # bloğun tümünün dolu olduğu tarih
        cikti = {f"{k}": float(df[k].dropna().asof(ortak)) for k in var
                 if pd.notna(df[k].dropna().asof(ortak))}
        cikti[f"{ad}_tarih"] = ortak.strftime("%Y-%m-%d")
        if len(set(sonlar.values())) > 1:
            en_yeni = max(sonlar.values())
            kayan = [k for k, t in sonlar.items() if t != ortak]
            uyar(f"BLOK TARİHİ: {BLOK_ADI.get(ad, ad)} bloğundaki seriler farklı "
                 f"tarihlerde bitiyor ({ortak:%d.%m.%Y} ↔ {en_yeni:%d.%m.%Y}); "
                 f"{len(kayan)} seri daha yeni. Blok, tümünün dolu olduğu ortak "
                 f"tarihe ({ortak:%d.%m.%Y}) çıpalandı — sayfada bu tarih "
                 "gösterilir.")
            cikti[f"{ad}_kayan"] = ", ".join(kayan)
            cikti[f"{ad}_en_yeni_tarih"] = en_yeni.strftime("%Y-%m-%d")
        return cikti

    o: dict = {
        "son_hafta": s_h.strftime("%Y-%m-%d"),
        "son_gun": s_g.strftime("%Y-%m-%d"),
        "son_ay": s_a.strftime("%Y-%m-%d"),
        "son_ceyrek": s_c.strftime("%Y-%m-%d"),
        "arindirma_yontem": "zincirleme_sepet",
        "kur_serisi": "TP.ZORUNDTH.KB8 / TP.ZORUNDTH.KB7 (ima edilen sepet); "
                      "tanı: TP.DK.USD.A.YTL",
        "sepet_kaynak_son": str(K["sepet_kaynak"].iloc[-1]),
        "sepet_tahmin": K.attrs.get("tahmin", {}),
        "kur_duyarlilik": duyar,
        "kur_gun_kaynak_son": str(K["kur_gun_kaynak"].iloc[-1]),
        "pencere_hafta": PENCERE,
        "yillik_us": YIL_HAFTA / PENCERE,
    }
    for kol in ("g_ar_13y", "g_ham_13y", "g_ar_usd_13y", "g_cipa_13y",
                "g_tl_13y", "g_yp_ar_13y", "kur_etkisi_13y",
                "g_ar_52", "g_ham_52", "g_tl_52", "g_yp_ar_52",
                "g_tuketici_13y", "g_ticari_13y", "g_kobi_13y", "g_bkk_13y",
                "g_konut_13y", "g_tasit_13y", "g_ihtiyac_13y",
                "g_kurumsal_kart_13y", "g_finansal_13y",
                "kredi_toplam", "kredi_tl_mlr", "kredi_yp_mlr", "yp_pay",
                "npl", "npl_tuketici", "npl_ticari", "karsilik_orani",
                "kredi_mevduat", "cipa_zincir_farki", "usd_sepet_farki_13y",
                "mevduat_sektor_toplam_mlr"):
        o[kol] = _son_deger(M, kol)
    for kol in ("m1_mlr", "m2_mlr", "m3_mlr", "g_m1_ar_13y", "g_m2_ar_13y",
                "g_m3_ar_13y", "g_m1_ham_13y", "g_m2_ham_13y", "g_m3_ham_13y",
                "tcmb_ar_m1_13y", "tcmb_ar_m2_13y", "tcmb_ar_m3_13y",
                "tcmb_ham_m2_13y", "carpan_m1", "carpan_m2", "carpan_m3",
                "rezerv_para_mlr", "zk_bloke_mlr", "emisyon_mlr",
                "serbest_mevduat_mlr", "mb_parasi_mlr", "emisyon_m1",
                "zk_ima_oran"):
        o[kol] = _son_deger(P, kol)
    # DOLARİZASYON BLOĞU TEK TARİHE ÇIPALANIR (bkz. _blok). ZK tabanı 13 gün
    # gecikmeli olduğu için dth_* serileri bilanço serilerinden bir hafta
    # geride kalıyor; ikisini bağımsız okumak "aynı haftanın taban farkı"
    # cümlesini bir haftalık kaymayla kirletir.
    o.update(_blok(D, ["dth_pay_ham", "dth_pay_ar", "mevduat_tl_mlr",
                       "mevduat_yp_mlr", "mevduat_yp_usd_mia",
                       "bilanco_pay_ham"], "dol"))
    for kol in ("f_ticari_tl", "f_ihtiyac", "f_konut", "f_tasit", "f_tuketici",
                "mev_tl", "kat_ticari", "kat_tuketici", "politika", "aofm",
                "koridor_alt", "koridor_ust", "makas_kredi_mevduat",
                "spread_politika", "spread_aofm", "pka_12a",
                "reel_ticari", "reel_tuketici", "reel_mevduat",
                "reel_ticari_yaklasik", "pka_yas_gun", "aofm_taban_mn_tl"):
        o[kol] = _son_deger(F, kol)
    # AOFM'nin VİNTAJI ve GEÇERLİLİĞİ. Sayı haftalık çıpaya geri taşınmış bir
    # iş günü değeridir; tarihi taşınmazsa okur onu haftalık çıpa tarihli sanır.
    o["aofm_tarih"] = _son_tarih(F, "aofm")
    o["spread_aofm_tarih"] = _son_tarih(F, "spread_aofm")
    o["aofm_ham"] = _son_deger(F, "aofm_ham")
    o["aofm_ham_tarih"] = _son_tarih(F, "aofm_ham")
    o["aofm_gecerli"] = bool(F["aofm_gecerli"].iloc[-1]) \
        if "aofm_gecerli" in F.columns and len(F) else False
    o["aofm_taban_esik_mn_tl"] = AOFM_TABAN_ESIK
    o["pka_tarih"] = None
    if "pka_12a" in F.columns and "pka_yas_gun" in F.columns:
        yas = _son_deger(F, "pka_yas_gun")
        st = _son_tarih(F, "pka_12a")
        if st is not None and yas is not None:
            o["pka_tarih"] = (pd.Timestamp(st)
                              - pd.Timedelta(days=int(yas))).strftime("%Y-%m-%d")
        if yas is not None and yas > PKA_YAS_ESIK_GUN:
            uyar(f"BEKLENTİ YAŞI: PKA 12 aylık TÜFE beklentisi {int(yas)} gün "
                 f"eski (eşik {PKA_YAS_ESIK_GUN} gün). Reel faizler bu koşuda "
                 "ESKİ beklentiyle hesaplandı; anket yayını gecikmiş olabilir.")
    for kol in ("kh_toplam_mlr", "kh_katilim_mlr", "kh_haric_mlr",
                "g_kh_toplam_yil", "g_kh_haric_yil", "g_kh_katilim_yil",
                "katilim_pay", "kkm_tl_mlr", "kkm_usd_mia"):
        o[kol] = _son_deger(AM, kol)
    for kol in C.columns:
        o[kol] = _son_deger(C, kol)
    o["dolarizasyon"] = dol_tani
    o["kkm"] = kkm_tani
    o["ayristirma"] = ayr_tani
    o["uzun"] = uzun_tani
    o["capraz"] = capraz_tani
    o["uzun_capraz"] = uzun_capraz_tani
    o["dogrulama"] = dog
    if len(U):
        o["uzun_g_ar_13y"] = _son_deger(U, "g_ar_13y")
        o["uzun_bas"] = U["g_ar_13y"].dropna().index[0].strftime("%Y-%m-%d")
    # ayrıştırmanın son 13 haftalık toplamı — kur etkisinin BÜYÜKLÜĞÜ (mlr TL)
    if len(AY_):
        son13 = AY_.tail(PENCERE)
        o["gama_13h_mlr"] = float(son13["gama"].sum())
        o["lamda_13h_mlr"] = float(son13["lamda"].sum())
        o["delta_13h_mlr"] = float(son13["delta"].sum())

    # --- yaz ---------------------------------------------------------------
    M.to_csv(VERI / "metrik_haftalik.csv")
    pd.concat([P, D, F], axis=1).loc[:, ~pd.concat([P, D, F], axis=1)
                                     .columns.duplicated()].to_csv(
        VERI / "metrik_para.csv")
    P.to_csv(VERI / "para.csv")
    D.to_csv(VERI / "dolarizasyon.csv")
    F.to_csv(VERI / "faiz.csv")
    AY_.to_csv(VERI / "ayristirma.csv")
    AM.to_csv(VERI / "metrik_aylik.csv")
    K.to_csv(VERI / "kur.csv")
    if len(U):
        U.to_csv(VERI / "uzun.csv")
    if len(CX):
        CX.to_csv(VERI / "capraz.csv")
    if len(CU):
        CU.to_csv(VERI / "capraz_uzun.csv")
    (VERI / "metrik_ozet.json").write_text(
        json.dumps(o, ensure_ascii=False, indent=1, allow_nan=True), encoding="utf-8")
    (PROJE / "uyarilar.json").write_text(json.dumps(
        {"hafta": s_h.strftime("%Y-%m-%d"), "kosum": dt.date.today().isoformat(),
         "uyarilar": UYARI, "dogrulama": dog}, ensure_ascii=False, indent=1),
        encoding="utf-8")

    print(f"  yazıldı: metrik_haftalik {M.shape} · para {P.shape} · "
          f"dolarizasyon {D.shape} · faiz {F.shape} · aylık {AM.shape}")
    if UYARI:
        print(f"\n[{len(UYARI)} uyarı — uyarilar.json]")

    # SESSİZ BAYATLAMANIN KAYNAK TARAFLI BİÇİMİ: seri taze ama hesap yanlış.
    # Ham endeks sınavı, seviye tablosu ile endeks tablosunun AYNI büyüklüğü
    # anlatıp anlatmadığını sorar; tutmuyorsa kalem eşlemesi bozulmuştur ve
    # yanlış bir M2 grafiği hiç grafik olmamasından kötüdür.
    dusen = [(ad, d) for ad, d in (dog.get("ham") or {}).items()
             if d.get("n") and d["maks_pp"] > ESIK_HAM_ENDEKS_PP]
    if dusen:
        ayrinti = " · ".join(f"{a.upper()}: {d['maks_pp']:.3f} puan" for a, d in dusen)
        raise SystemExit(
            f"DUR: ham para arzı doğrulaması düştü ({ayrinti}; tolerans "
            f"{ESIK_HAM_ENDEKS_PP}). Seviye tablosundan hesaplanan "
            "13 haftalık yıllıklandırılmış büyüme, TCMB'nin ayrı bir üründe "
            "yayımladığı ham endeksle uyuşmuyor — kalem "
            "numaralandırması ya da birim değişmiş olabilir. Siteye kopyalama "
            "YAPILMAZ; yanlış bir M2 grafiği hiç grafik olmamasından kötüdür.")
    return o


if __name__ == "__main__":
    kos()
