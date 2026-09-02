# -*- coding: utf-8 -*-
"""TCMB fonlama & likidite — metrik katmanı.

Ne hesaplar
-----------
1. **Fonlama kompozisyonu ve AOFM.** AOFM'nin paydası YALNIZ fonlama bacağıdır;
   fonlama sıfıra düştüğünde AOFM tanımsızdır ama EVDS o gün de bir sayı basar.
   Bu günler `aofm_gecerli = False` işaretlenir ve temiz seri NaN yapılır.
2. **AOSM — ağırlıklı ortalama sterilizasyon maliyeti (BU ÇALIŞMANIN
   TÜRETMESİ, TCMB serisi DEĞİLDİR).** Fazla likidite rejiminde marjinal fiyatı
   sterilizasyon belirler; AOFM'nin aynasıdır.
3. **Marjinal TCMB faizi.** Rejime göre AOFM ya da AOSM: sistem net borçluysa
   fonlamanın, net alacaklıysa sterilizasyonun fiyatı marjinaldir.
4. **Koridor konumu, spreadler, örtük sıkılaştırma dönemleri.**
5. **Net APİ fonlaması, swap stoku ve sistemin net likidite pozisyonu.**
6. **ZK bloke hesabı, ima edilen efektif ZK oranı, tesis dönemi adımları.**
7. **Fonlama maliyeti → kredi/mevduat faizi geçişkenliği** (yuvarlanan
   regresyon; NEDENSELLİK İDDİASI DEĞİLDİR, öyle etiketlenir).
8. **Bağımsız doğrulama.** Hesapladığımız serileri EVDS'in KENDİ yayımladığı
   karşılıklarıyla kıyaslar; eşik aşılırsa hat DURUR.

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import veri
from veri import PROJE, VERI, gun_ad


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

# --------------------------------------------------------------------------- eşikler
# AOFM'nin geçerli sayılması için gereken en küçük fonlama tabanı (milyon TL).
# 700 mn TL'lik bir fonlamanın ağırlıklı ortalaması "sistemin fonlama maliyeti"
# değildir; 5.000 mn TL (5 mlr TL) sistemin gün başı likiditesinin binde ikisi
# mertebesinde ve bu eşiğin altında AOFM bilgi taşımıyor sayılır.
AOFM_TABAN_ESIK = 5_000.0

# ZK tabanının iki bacağı iki AYRI veri grubundan gelir ve ölçekleri farklıdır
# (bin TL ↔ milyon TL). Elde kurulan toplam ile EVDS'in yayımladığı toplam bu
# bağıl eşikten fazla ayrışırsa birim varsayımı bozulmuştur ve hat DURUR.
ZK_TABAN_BIRIM_ESIK = 0.01

# Koridorun üstünde fonlama = örtük sıkılaştırma. Kotasyon yuvarlamalarını
# olay saymamak için 5 baz puanlık pay bırakılır; bir dönem sayılması için
# en az 5 iş günü sürmesi gerekir (tek günlük sapma "rejim" değildir).
KORIDOR_USTU_PAY = 0.05
DONEM_MIN_GUN = 5

# Geçişkenlik penceresi: 52 hafta. Bir yıldan kısa pencerede katsayı tek bir
# faiz kararının etrafında salınıyor; daha uzun pencerede rejim değişimi
# ortalamanın içinde kayboluyor.
GECIS_PENCERE = 52

# Doğrulama eşikleri (puan). Aşılırsa hat DURUR — yanlış sayı yayına gitmesin.
ESIK_NET_FONLAMA = 1e-6      # kimlik: A − B = APIFON3 (mn TL)
ESIK_POLITIKA_PP = 0.01      # günlük kotasyon ↔ EVDS'in aylık BIS serisi
ESIK_TLREF_PP = 1.00         # TLREF ↔ BİST gecelik repo AOF (bağımsız kaynak)
# AOFM'nin kalem kırılımından yeniden türetilmesi (TANI, durdurmaz): son 250 iş
# gününde medyan sapma bu eşiği aşarsa kalem eşlemesi bozulmuş demektir.
ESIK_AOFM_KOMPOZISYON_PP = 0.05

_UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def _sifir_nan(s: pd.Series) -> pd.Series:
    """SIFIR ≠ VERİ. Kotasyon serilerinde 0, 'bu yönde kotasyon yok' demektir;
    faiz oranı olarak yorumlanırsa koridor bandını tabana çeker."""
    return s.where(s != 0)


# ===========================================================================
# (1) FONLAMA / STERİLİZASYON KOMPOZİSYONU VE MALİYETİ
# ===========================================================================
def fonlama_metrikleri(g: pd.DataFrame) -> pd.DataFrame:
    M = pd.DataFrame(index=g.index)

    # --- seviyeler (milyon TL) --------------------------------------------
    for a in ("fon_top", "fon_ihale", "fon_kot_repo", "fon_kot_depo", "fon_glp",
              "ste_top", "ste_ihale", "ste_kot", "ste_liksen", "net_fonlama",
              "serbest_mevduat", "gun_basi_likidite"):
        if a in g.columns:
            M[a] = g[a]

    # Kotasyon toplamı ile alt kalemlerin farkı: EVDS'te A2 = A2a+A2b+A2c
    # olmalı; olmuyorsa alt kalem eklenmiş demektir ve yığılı alan grafiği
    # toplamı tutmaz. Artık ayrı iz olarak çizilir, gizlenmez.
    if {"fon_kot_top", "fon_kot_repo", "fon_kot_depo", "fon_glp"} <= set(g.columns):
        M["fon_kot_diger"] = (g["fon_kot_top"].fillna(0)
                              - g["fon_kot_repo"].fillna(0)
                              - g["fon_kot_depo"].fillna(0)
                              - g["fon_glp"].fillna(0))
    if {"ste_top", "ste_ihale", "ste_kot", "ste_liksen"} <= set(g.columns):
        M["ste_diger"] = (g["ste_top"].fillna(0) - g["ste_ihale"].fillna(0)
                          - g["ste_kot"].fillna(0) - g["ste_liksen"].fillna(0))

    # --- faizler -----------------------------------------------------------
    M["politika"] = _sifir_nan(g["politika"])
    M["koridor_alt"] = _sifir_nan(g["koridor_alt"])
    M["koridor_ust"] = _sifir_nan(g["koridor_ust"])
    M["glp_satis"] = _sifir_nan(g["glp_satis"])
    M["tlref"] = g.get("tlref")
    M["bist_on"] = g.get("bist_on")

    # --- AOFM: tabanı yokken yayımlanmaz ----------------------------------
    M["aofm_ham"] = g["aofm"]
    taban = g["fon_top"]
    M["aofm_gecerli"] = (taban.notna() & (taban >= AOFM_TABAN_ESIK)
                         & g["aofm"].notna())
    M["aofm"] = g["aofm"].where(M["aofm_gecerli"])

    # --- AOSM (TÜRETME) ----------------------------------------------------
    # Sterilizasyon ihalesinin ağırlıklı ortalama faizi. Gecelik depo alım
    # ihalesi (ONI) vadesi bir gün olduğu için o günkü kabul tutarı AYNI ZAMANDA
    # o günkü stoktur; ihale yoluyla sterilizasyon stokunun geri kalanı
    # (`ste_ihale − ONI`) haftalık depo alım ihalesinden (1HI) gelir ve
    # stokta ~5 iş günü kalır. Bu yüzden kalan bacak, son 5 iş gününün
    # TUTAR-AĞIRLIKLI 1HI faiziyle değerlenir.
    #   VARSAYIM: kalan bacağın tamamı 1HI'dır. ÖLÇÜLDÜ (bkz. dogrulama):
    #   kalan ≈ 5 × günlük 1HI tutarı; sapma raporlanır.
    #   Bu bir TCMB serisi DEĞİLDİR; `ozet.json`'da öyle etiketlenir.
    if {"sto_oni_tutar", "sto_oni_faiz", "sto_1hi_tutar", "sto_1hi_faiz",
            "ste_ihale"} <= set(g.columns):
        oni_t = g["sto_oni_tutar"] / 1000.0        # bin TL → milyon TL
        oni_r = g["sto_oni_faiz"]
        h_t = g["sto_1hi_tutar"] / 1000.0
        h_r = g["sto_1hi_faiz"]
        pay = (h_t * h_r).rolling(5, min_periods=1).sum()
        payda = h_t.rolling(5, min_periods=1).sum()
        h_r5 = (pay / payda).where(payda > 0)
        kalan = (g["ste_ihale"] - oni_t.fillna(0))
        M["aosm_kalan"] = kalan
        M["aosm_oni_tutar"] = oni_t
        M["aosm_1hi_faiz5"] = h_r5
        kalan_p = kalan.clip(lower=0)
        agirlik = oni_t.fillna(0) + kalan_p
        aosm = ((oni_t.fillna(0) * oni_r.fillna(0) + kalan_p * h_r5.fillna(0))
                / agirlik.where(agirlik > 0))
        # Bileşenlerinden biri eksikse AOSM üretilmez (yarım hesapla basmak yasak)
        gecerli = (oni_r.notna() & (agirlik > AOFM_TABAN_ESIK)
                   & (h_r5.notna() | (kalan_p <= 0)))
        M["aosm"] = aosm.where(gecerli)
        M["aosm_gecerli"] = gecerli.fillna(False)
    else:
        M["aosm"] = np.nan
        M["aosm_gecerli"] = False

    # --- rejim ve marjinal faiz -------------------------------------------
    # Net fonlama POZİTİF: sistem TCMB'ye net borçlu, marjinal fiyat AOFM.
    # NEGATİF: sistem net alacaklı, marjinal fiyatı sterilizasyon belirler.
    M["rejim_fonlama"] = g["net_fonlama"] > 0
    M["marjinal_faiz"] = np.where(M["rejim_fonlama"], M["aofm"], M["aosm"])
    M["marjinal_faiz"] = pd.Series(M["marjinal_faiz"], index=M.index)
    # AOSM yalnız 09.05.2024'ten var; öncesinde fazla likidite günlerinde
    # marjinal fiyat için TLREF vekil alınır ve bu AÇIKÇA işaretlenir.
    M["marjinal_kaynak"] = np.where(
        M["rejim_fonlama"] & M["aofm"].notna(), "AOFM",
        np.where(M["aosm"].notna(), "AOSM",
                 np.where(M["tlref"].notna(), "TLREF (vekil)", "yok")))
    M["marjinal_faiz"] = M["marjinal_faiz"].fillna(M["tlref"])

    # --- spreadler ---------------------------------------------------------
    M["spread_tlref_politika"] = M["tlref"] - M["politika"]
    M["spread_aofm_politika"] = M["aofm"] - M["politika"]
    M["spread_tlref_aofm"] = M["tlref"] - M["aofm"]
    M["spread_marjinal_politika"] = M["marjinal_faiz"] - M["politika"]

    # --- koridor konumu ----------------------------------------------------
    # 0 = koridorun tabanı, 1 = tavanı. Bant dışına çıkabilir (GLP dönemi);
    # kırpılmaz, çünkü asıl anlatılacak şey bant DIŞINA çıkmasıdır.
    bant = (M["koridor_ust"] - M["koridor_alt"]).where(
        lambda x: x.abs() > 1e-9)
    M["koridor_bant"] = bant
    M["konum_tlref"] = (M["tlref"] - M["koridor_alt"]) / bant
    M["konum_aofm"] = (M["aofm"] - M["koridor_alt"]) / bant
    M["konum_marjinal"] = (M["marjinal_faiz"] - M["koridor_alt"]) / bant
    M["aofm_koridor_ustu"] = M["aofm"] - M["koridor_ust"]
    # Simetrik ölçü: AOFM koridorun TABANININ altına da düşebilir (faiz artışı
    # sonrası stok gecikmesi). Tek yönlü bakmak olgunun yarısını gizler.
    M["aofm_koridor_alti"] = M["koridor_alt"] - M["aofm"]
    # Koridor SİMETRİK DEĞİLDİR: politika faizi bandın ortası değildir.
    M["koridor_asimetri"] = ((M["koridor_ust"] - M["politika"])
                             - (M["politika"] - M["koridor_alt"]))

    # --- swap ve net likidite pozisyonu ------------------------------------
    if {"swap_alim", "usdtry"} <= set(g.columns):
        kur = g["usdtry"].reindex(M.index).ffill()
        M["kur"] = kur
        M["swap_alim_usd"] = g["swap_alim"]
        M["swap_satim_usd"] = g["swap_satim"]
        # milyon USD × (TL/USD) = milyon TL — APİ tablosuyla AYNI birim
        M["swap_alim_tl"] = g["swap_alim"] * kur
        M["swap_satim_tl"] = g["swap_satim"] * kur
        for a in ("swap_tcmb_piy", "swap_bist", "swap_gelenek", "swap_miktar",
                  "swap_altin_piy", "swap_altin_ihale"):
            if a in g.columns:
                M[a] = g[a]
        # TCMB kaynaklı NET TL likidite: net APİ fonlaması + swap yoluyla
        # VERİLEN TL − swap yoluyla ÇEKİLEN TL. Swap bilanço DIŞI bacaktır ve
        # İKİ YÖNLÜDÜR: alım yönlü swapta TCMB döviz alıp TL verir, satım
        # yönlüsünde döviz satıp TL çeker. Yalnız alım bacağını eklemek, satım
        # stoku büyürken "TCMB'nin sağladığı TL" ölçüsünü sabit gösterir —
        # ölçüm gününde satım stokunun TL karşılığı yüzlerce milyar TL'dir.
        # SIFIR ≠ VERİ: kur serisi bir gün İLERİDEN yayımlandığı için panelin
        # son satırında swap bacaklarının ikisi de boş olabilir. fillna(0)
        # oradan sahte bir "net sıfır" üretir ve ozet.json son dolu değeri o
        # sıfırdan okur — tam olarak sessiz bayatlamanın küçük hâli.
        ikisi_bos = M["swap_alim_tl"].isna() & M["swap_satim_tl"].isna()
        M["swap_net_tl"] = (M["swap_alim_tl"].fillna(0)
                            - M["swap_satim_tl"].fillna(0)).where(~ikisi_bos)
        M["tcmb_tl_saglama"] = g["net_fonlama"] + M["swap_net_tl"]
        # Yalnız alım bacaklı eski tanım TANI olarak korunur; iki sayı yan yana
        # yayımlanınca satım bacağının büyüklüğü sayfada görünür hâle gelir.
        M["api_ve_swap_alim"] = g["net_fonlama"] + M["swap_alim_tl"].fillna(0)
        M["swap_pay"] = (M["swap_net_tl"].abs()
                         / (M["swap_net_tl"].abs() + g["fon_top"].abs())
                         .replace(0, np.nan))

    # --- analitik bilanço (bin TL → milyon TL) -----------------------------
    for a, ad in (("ab_zk_bloke", "zk_bloke"), ("ab_serbest", "ab_serbest_mev"),
                  ("ab_emisyon", "emisyon"), ("ab_rezerv_para", "rezerv_para"),
                  ("ab_mbp", "mb_parasi"), ("ab_api", "ab_api"),
                  ("ab_kamu_mev", "kamu_mevduati"),
                  ("ab_bankalar", "bankalar_mevduati")):
        if a in g.columns:
            M[ad] = g[a] / 1000.0
    return M


# ===========================================================================
# (2) ZORUNLU KARŞILIKLAR
# ===========================================================================
def zk_metrikleri(M: pd.DataFrame, h: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """ZK bloke hesabı, ima edilen efektif oran ve tesis dönemi adımları.

    ZK ORANLARI EVDS'te YAYIMLANMIYOR (675 veri grubunun tamamı tarandı).
    Yayımlanan yalnız SONUÇTUR: bloke hesap (`TP.AB.A19`, günlük) ve ZK'ya tabi
    taban (`bie_tldthvade` + `bie_zorundth`, haftalık). Bu yüzden burada
    hesaplanan oran, TCMB'nin tebliğle ilan ettiği ORAN DEĞİL, gerçekleşmiş
    TESİS oranıdır — vade dilimlerine ve para cinsine göre farklı oranların
    bileşimidir ve YP karşılıkların döviz olarak tutulabilmesi nedeniyle
    tebliğdeki hiçbir tek orana eşit değildir.
    """
    tani: dict = {}
    if "zk_bloke" not in M.columns:
        return pd.DataFrame(), {"durum": "ZK bloke hesabı yok"}

    # SIFIR ≠ VERİ — bu hattın en sinsi tuzağı.
    # ÖLÇÜLDÜ: TP.AB.A19 (ZK bloke hesabı) 1980'den 14.03.2024'e kadar TAM
    # SIFIR basıyor. Bu "zorunlu karşılık yoktu" demek DEĞİLDİR; analitik
    # bilanço o dönemde bankalar mevduatını bloke/serbest diye AYIRMIYORDU ve
    # tutarın tamamı A20'de duruyordu (A18 = A20, A19 = 0 kimliği o dönemde
    # birebir kapanıyor). Sıfırı veri sanmak, ima edilen tesis oranını on üç
    # yıl boyunca "%0" diye yayımlamak olurdu — grafik dolu, sayı yanlış.
    ham = M["zk_bloke"].dropna()
    zk = ham[ham != 0]
    if zk.empty:
        return pd.DataFrame(), {"durum": "ZK bloke hesabı tüm tarihçede sıfır"}
    tani["bloke_bas"] = str(zk.index[0].date())
    sifir_once = ham.loc[:zk.index[0]]
    tani["bloke_sifir_gun"] = int((sifir_once == 0).sum())
    if tani["bloke_sifir_gun"] > 250:
        uyar(f"AYRI KALEM DEĞİL: ZK bloke hesabı (TP.AB.A19) "
             f"{tani['bloke_sifir_gun']} iş günü boyunca tam sıfır basmış ve "
             f"{zk.index[0]:%d.%m.%Y} tarihinde doluyor. Öncesi 'ZK yoktu' "
             "değil, 'ayrı yayımlanmıyordu' demektir; sıfırlar veri sayılmadı "
             "ve ZK paneli o tarihten başlıyor.")
    # Tesis dönemi adımları: seri bir BASAMAK fonksiyonudur, iki haftada bir
    # (Cuma) güncellenir. Günlük farkını "günlük likidite etkisi" saymak yanlış.
    d = zk.diff()
    adim = d[d.abs() > 1e-6]
    tani["adim_sayisi"] = int(len(adim))
    if len(adim) > 3:
        araliklar = pd.Series(adim.index).diff().dt.days.dropna()
        tani["adim_ortalama_gun"] = float(araliklar.median())
        tani["adim_gun_dagilimi"] = {
            str(int(k)): int(v) for k, v in
            araliklar.value_counts().head(4).items()}
        haftaici = pd.Series(adim.index).dt.dayofweek.value_counts()
        tani["adim_gun_adi"] = {str(int(k)): int(v) for k, v in haftaici.items()}
    tani["son_adimlar"] = [
        {"tarih": str(t.date()), "degisim_mn_tl": float(v)}
        for t, v in adim.tail(8).items()]

    # Taban: haftalık. BİRİM TUZAĞI — iki veri grubu AYNI ÖLÇEKTE DEĞİL:
    #   TP.TLDTHVADE.KB6/KB12/KB18 (bie_tldthvade) → BİN TL
    #   TP.ZORUNDTH.KB8            (bie_zorundth)  → MİLYON TL
    # `zk_taban_tl + dth_tl` yazmak DTH bacağını 1000 kat küçültür ve tabanı
    # fiilen yalnız TL mevduata indirir; ima edilen tesis oranı %65 abartılı
    # çıkar. Doğru toplam EVDS'te zaten yayımlanıyor (KB18); onu kullanıyoruz.
    Z = pd.DataFrame(index=zk.index)
    Z["zk_bloke"] = zk
    if "zk_taban_toplam" in h.columns and h["zk_taban_toplam"].notna().any():
        taban = h["zk_taban_toplam"] / 1000.0                # bin TL → mn TL
        taban = taban.dropna()
        # BİRİM GÜVENLİĞİ (Kredi/kur_kur'daki denetimin eşdeğeri): elde kurulan
        # toplam ile EVDS'in yayımladığı toplam %1'den fazla ayrışırsa bir
        # serinin birimi değişmiştir — hat DURUR, yanlış oran yayına gitmez.
        if {"zk_taban_tl", "dth_tl"} <= set(h.columns):
            elde = (h["zk_taban_tl"] / 1000.0 + h["dth_tl"]).dropna()
            d = pd.concat([elde.rename("elde"),
                           taban.rename("evds")], axis=1).dropna()
            if len(d):
                bagil = ((d["elde"] - d["evds"]).abs() / d["evds"].abs())
                # DURDURUCU ÖLÇÜ MEDYAN VE SON GÖZLEMDİR, maksimum değil: bir
                # birim değişikliği HER HAFTAYI vurur (1000 kat hata ~%40
                # sapma verir), tek haftalık sapma ise iki tablonun vintaj
                # farkıdır (2018 gibi revizyon haftaları). Maksimuma bakan bir
                # denetim hattı tarihsel bir revizyon yüzünden durdururdu.
                medyan, sonuncu = float(bagil.median()), float(bagil.iloc[-1])
                tani["taban_birim_bagil_medyan"] = medyan
                tani["taban_birim_bagil_son"] = sonuncu
                tani["taban_birim_bagil_maks"] = float(bagil.max())
                tani["taban_birim_maks_tarih"] = str(bagil.idxmax().date())
                tani["taban_birim_n"] = int(len(d))
                if medyan > ZK_TABAN_BIRIM_ESIK or sonuncu > ZK_TABAN_BIRIM_ESIK:
                    tani["taban_birim_dur"] = (
                        "BİRİM: ZK tabanının elde kurulan toplamı "
                        f"(TL/1000 + DTH) EVDS toplamından bağıl medyan "
                        f"{medyan:.4f}, son gözlemde {sonuncu:.4f} sapıyor "
                        f"(eşik {ZK_TABAN_BIRIM_ESIK}). TP.TLDTHVADE.* / "
                        "TP.ZORUNDTH.* birimlerinden biri değişmiş olabilir; "
                        "ima edilen tesis oranı üretilmedi.")
                # Tekil sapmalar TANIDIR: iki tablonun aynı haftayı farklı
                # vintajla yayımladığı günler sessiz kalmasın.
                tekil = bagil[bagil > ZK_TABAN_BIRIM_ESIK]
                tani["taban_birim_tekil_gun"] = int(len(tekil))
                if len(tekil):
                    uyar(f"ZK TABANI VİNTAJ: {len(tekil)} haftada iki tablo "
                         "(vadeli mevduat tablosu ↔ zorunlu karşılık tablosu) %1'den fazla "
                         f"ayrışıyor; en büyüğü {bagil.idxmax():%d.%m.%Y} "
                         f"({_bicim().yuzde(bagil.max() * 100, 1)}). Birim değil, revizyon farkıdır "
                         "— taban EVDS toplamından okunduğu için hesap "
                         "etkilenmez.")
    elif {"zk_taban_tl", "dth_tl"} <= set(h.columns):
        uyar("ZK tabanı toplamı (TP.TLDTHVADE.KB18) yok — taban bacaklardan "
             "kuruldu (TL bin TL, DTH milyon TL; birimler ayrı ayrı çevrildi).")
        taban = (h["zk_taban_tl"] / 1000.0 + h["dth_tl"]).dropna()
    else:
        uyar("ZK tabanı serileri yok — ima edilen efektif oran hesaplanamadı.")
        taban = None

    if taban is not None and len(taban):
        tani["taban_kaynak"] = ("TP.TLDTHVADE.KB18 (bin TL → mn TL)"
                                if "zk_taban_toplam" in h.columns
                                else "TL/1000 + DTH (bacaklardan)")
        Z["zk_taban"] = taban.reindex(Z.index).ffill()
        # Taban 13 gün gecikmeli geliyor: ffill ile taşınan gözlem işaretlenir,
        # taşıma penceresi 21 günü aşarsa oran hesaplanmaz (bayat payda).
        tas = pd.Series(taban.index, index=taban.index).reindex(Z.index).ffill()
        yas = (pd.Series(Z.index, index=Z.index) - tas).dt.days
        Z["taban_yas_gun"] = yas
        Z["zk_oran"] = (Z["zk_bloke"] / Z["zk_taban"]).where(yas <= 21) * 100
        tani["taban_son_tarih"] = str(taban.index[-1].date())
        tani["taban_son_mn_tl"] = float(taban.iloc[-1])
        son_o = Z["zk_oran"].dropna()
        if len(son_o):
            tani["ima_oran_son"] = float(son_o.iloc[-1])
            tani["ima_oran_tarih"] = str(son_o.index[-1].date())
            tani["ima_oran_1y_once"] = (
                float(son_o.asof(son_o.index[-1] - pd.Timedelta(days=365)))
                if son_o.index[0] <= son_o.index[-1] - pd.Timedelta(days=365)
                else None)
    return Z, tani


# ===========================================================================
# (3) ÖRTÜK SIKILAŞTIRMA DÖNEMLERİ
# ===========================================================================
def donemler(M: pd.DataFrame) -> list[dict]:
    """AOFM'nin koridorun ÜSTÜNE çıktığı dönemler.

    Ölçülmüş bir Türkiye olgusudur: 2017–18'de fonlamanın tamamı geç likidite
    penceresinden yapılmış, AOFM ilan edilen politika faizinin yüzlerce baz
    puan üzerine ve koridorun TAVANININ DIŞINA çıkmıştır. O dönemde "politika
    faizi %8" cümlesi sistemin ödediği fiyat hakkında hiçbir şey söylemiyordu.
    """
    if "aofm_koridor_ustu" not in M.columns:
        return []
    isaret = (M["aofm_koridor_ustu"] > KORIDOR_USTU_PAY).fillna(False)
    out: list[dict] = []
    grup = (isaret != isaret.shift()).cumsum()
    for _, blok in M[isaret].groupby(grup[isaret]):
        if len(blok) < DONEM_MIN_GUN:
            continue
        out.append({
            "bas": str(blok.index[0].date()),
            "son": str(blok.index[-1].date()),
            "gun": int(len(blok)),
            "aofm_ort": float(blok["aofm"].mean()),
            "aofm_maks": float(blok["aofm"].max()),
            "koridor_ust_ort": float(blok["koridor_ust"].mean()),
            "asim_ort_pp": float(blok["aofm_koridor_ustu"].mean()),
            "asim_maks_pp": float(blok["aofm_koridor_ustu"].max()),
            "glp_ort": float(blok["glp_satis"].mean())
            if blok["glp_satis"].notna().any() else None,
            "politika_ort": float(blok["politika"].mean())
            if blok["politika"].notna().any() else None,
        })
    return out


def donemler_alti(M: pd.DataFrame) -> list[dict]:
    """AOFM'nin koridorun ALTINA düştüğü dönemler — üsttekinin AYNASI.

    Denetim tek yönlü kalırsa "AOFM sistemin ödediği fiyattır" cümlesi yalnız
    sıkılaştırma yönünde sınanmış olur. Oysa AOFM bir STOK ortalamasıdır: faiz
    artışı haftalarında eski, ucuz fonlama stokta durduğu için AOFM koridorun
    tabanının da altına düşebilir. Bu mekanik gecikmedir, "gevşeme" değildir;
    ama ölçülmeden anlatılamaz.
    """
    if "aofm_koridor_alti" not in M.columns:
        return []
    isaret = (M["aofm_koridor_alti"] > KORIDOR_USTU_PAY).fillna(False)
    out: list[dict] = []
    grup = (isaret != isaret.shift()).cumsum()
    for _, blok in M[isaret].groupby(grup[isaret]):
        if len(blok) < DONEM_MIN_GUN:
            continue
        out.append({
            "bas": str(blok.index[0].date()),
            "son": str(blok.index[-1].date()),
            "gun": int(len(blok)),
            "aofm_ort": float(blok["aofm"].mean()),
            "aofm_min": float(blok["aofm"].min()),
            "koridor_alt_ort": float(blok["koridor_alt"].mean()),
            "asim_ort_pp": float(blok["aofm_koridor_alti"].mean()),
            "asim_maks_pp": float(blok["aofm_koridor_alti"].max()),
            "politika_ort": float(blok["politika"].mean())
            if blok["politika"].notna().any() else None,
        })
    return out


# ===========================================================================
# (4) GEÇİŞKENLİK — fonlama maliyeti → kredi / mevduat faizi
# ===========================================================================
def _yuvarlanan_beta(y: pd.Series, x: pd.Series, pencere: int) -> pd.DataFrame:
    """y_t = α + β·x_t + ε üzerinde yuvarlanan EKK. statsmodels'e gerek yok."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    beta = pd.Series(index=d.index, dtype=float)
    r2 = pd.Series(index=d.index, dtype=float)
    for i in range(pencere - 1, len(d)):
        p = d.iloc[i - pencere + 1: i + 1]
        xv, yv = p["x"].to_numpy(), p["y"].to_numpy()
        if np.nanstd(xv) < 1e-12:
            continue
        A = np.column_stack([np.ones_like(xv), xv])
        kat, *_ = np.linalg.lstsq(A, yv, rcond=None)
        tahmin = A @ kat
        ss_tot = float(((yv - yv.mean()) ** 2).sum())
        beta.iloc[i] = float(kat[1])
        r2.iloc[i] = (1 - float(((yv - tahmin) ** 2).sum()) / ss_tot
                      if ss_tot > 1e-12 else np.nan)
    return pd.DataFrame({"beta": beta, "r2": r2})


def gecirgenlik(M: pd.DataFrame, h: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Haftalık kredi/mevduat faizinin marjinal TCMB faizine duyarlılığı.

    NEDENSELLİK İDDİASI DEĞİLDİR: gecikmeli eşhareket ölçüsüdür. Aynı pencerede
    her iki seriyi de aynı üçüncü etken (kur, risk primi, PPK beklentisi)
    besliyor olabilir.
    """
    tani: dict = {}
    if h.empty:
        return pd.DataFrame(), {"durum": "haftalık faiz serisi yok"}
    H = pd.DataFrame(index=h.index)
    for a in ("f_ticari_tl", "f_tuketici", "f_ihtiyac", "f_konut",
              "f_mevduat_tl", "f_mevduat_3a"):
        if a in h.columns:
            H[a] = h[a]
    H["makas"] = H.get("f_ticari_tl") - H.get("f_mevduat_tl")

    # Marjinal faizi Cuma'ya taşı: haftalık faiz verisi Cuma itibarıyladır,
    # o hafta içinde geçerli olan marjinal fiyat o haftanın ORTALAMASIDIR.
    mj = M["marjinal_faiz"].dropna()
    if mj.empty:
        return H, {"durum": "marjinal faiz üretilemedi"}
    haftalik_mj = mj.resample("W-FRI").mean()
    H["marjinal"] = haftalik_mj.reindex(H.index)
    H["politika_h"] = M["politika"].dropna().resample("W-FRI").last().reindex(H.index)
    H["kredi_marj"] = H.get("f_ticari_tl") - H["marjinal"]
    H["mevduat_marj"] = H["marjinal"] - H.get("f_mevduat_tl")

    d_mj = H["marjinal"].diff()
    tani["gecikme_taramasi"] = {}
    for hedef, ad in (("f_ticari_tl", "ticari_tl"), ("f_mevduat_tl", "mevduat_tl")):
        if hedef not in H.columns:
            continue
        d_y = H[hedef].diff()
        kor = {}
        for k in range(0, 9):
            ort = pd.concat([d_y, d_mj.shift(k)], axis=1).dropna()
            if len(ort) > 30:
                kor[k] = float(ort.corr().iloc[0, 1])
        if kor:
            en_iyi = max(kor, key=lambda k: abs(kor[k]))
            tani["gecikme_taramasi"][ad] = {
                "korelasyon": {str(k): round(v, 4) for k, v in kor.items()},
                "en_iyi_gecikme_hafta": int(en_iyi),
                "en_iyi_korelasyon": round(kor[en_iyi], 4),
            }
            r = _yuvarlanan_beta(d_y, d_mj.shift(en_iyi), GECIS_PENCERE)
            H[f"beta_{ad}"] = r["beta"]
            H[f"r2_{ad}"] = r["r2"]
            # Tam örneklem katsayısı (yuvarlananın çıpası)
            ort = pd.concat([d_y.rename("y"), d_mj.shift(en_iyi).rename("x")],
                            axis=1).dropna()
            if len(ort) > 30:
                A = np.column_stack([np.ones(len(ort)), ort["x"].to_numpy()])
                kat, *_ = np.linalg.lstsq(A, ort["y"].to_numpy(), rcond=None)
                tani["gecikme_taramasi"][ad]["tam_beta"] = round(float(kat[1]), 4)
                tani["gecikme_taramasi"][ad]["n"] = int(len(ort))
            son = H[f"beta_{ad}"].dropna()
            if len(son):
                tani["gecikme_taramasi"][ad]["son_beta"] = round(float(son.iloc[-1]), 4)
                tani["gecikme_taramasi"][ad]["son_beta_tarih"] = str(son.index[-1].date())
                tani["gecikme_taramasi"][ad]["son_r2"] = round(
                    float(H[f"r2_{ad}"].dropna().iloc[-1]), 4)
    return H, tani


# ===========================================================================
# (5) BAĞIMSIZ DOĞRULAMA — hat DURDURUCU
# ===========================================================================
def dogrula(g: pd.DataFrame, M: pd.DataFrame, a: pd.DataFrame) -> tuple[dict, list[str]]:
    """Hesapladığımız serileri EVDS'in KENDİ yayımladığı karşılıklarıyla kıyasla.

    Üç bağımsız sınav:
      (1) Net fonlama kimliği: A − B, EVDS'in TP.APIFON3'ü ile aynı olmalı.
      (2) Politika faizi: kullandığımız GÜNLÜK kotasyonun (TP.PY.P02.1H) ay
          sonu değeri, EVDS'in AYRI yayımladığı aylık BIS derlemesiyle
          (TP.BISPOLFAIZ.TUR) aynı olmalı. İki seri farklı kaynaktan gelir.
      (3) TLREF ↔ BİST gecelik repo ağırlıklı ortalama faizi: aynı piyasanın
          iki ayrı ölçüsü; ayrışırsa TLREF beslemesinde sorun var demektir.
    Ayrıca AOSM'nin taban varsayımı ve aylık gecelik repo karşılaştırması TANI
    olarak raporlanır (bunlar farklı araç ölçtükleri için hattı durdurmaz).
    """
    D: dict = {}
    dur: list[str] = []

    # (1) net fonlama kimliği
    d = pd.DataFrame({"biz": g["fon_top"] - g["ste_top"],
                      "evds": g["net_fonlama"]}).dropna()
    fark = (d["biz"] - d["evds"]).abs()
    D["net_fonlama"] = {
        "kaynak": "TP.APIFON1.TOP − TP.APIFON2.TOP ↔ TP.APIFON3",
        "n": int(len(d)), "maks_fark_mn_tl": float(fark.max()),
        "esik_mn_tl": ESIK_NET_FONLAMA,
        "son_biz": float(d["biz"].iloc[-1]), "son_evds": float(d["evds"].iloc[-1]),
        "gecti": bool(fark.max() <= ESIK_NET_FONLAMA)}
    if fark.max() > ESIK_NET_FONLAMA:
        dur.append(f"DOĞRULAMA: net fonlama kimliği tutmuyor "
                   f"(maks {fark.max():.6f} mn TL).")

    # (2) politika faizi — günlük kotasyon ↔ aylık BIS derlemesi
    if "bis_politika" in a.columns:
        pol = M["politika"].dropna()
        ay_son = pol.resample("MS").last()
        d2 = pd.DataFrame({"biz": ay_son, "evds": a["bis_politika"]}).dropna()
        f2 = (d2["biz"] - d2["evds"]).abs()
        D["politika"] = {
            "kaynak": "TP.PY.P02.1H (ay sonu) ↔ TP.BISPOLFAIZ.TUR (aylık)",
            "n": int(len(d2)), "maks_fark_pp": float(f2.max()),
            "ort_fark_pp": float(f2.mean()), "esik_pp": ESIK_POLITIKA_PP,
            "evds_son_ay": str(d2.index[-1].date())[:7],
            "son_biz": float(d2["biz"].iloc[-1]),
            "son_evds": float(d2["evds"].iloc[-1]),
            "gecti": bool(f2.max() <= ESIK_POLITIKA_PP)}
        if f2.max() > ESIK_POLITIKA_PP:
            dur.append(f"DOĞRULAMA: politika faizi kotasyonu EVDS'in aylık "
                       f"serisinden {f2.max():.3f} puan sapıyor.")
    else:
        D["politika"] = {"durum": "TP.BISPOLFAIZ.TUR alınamadı — sınav yapılamadı"}
        uyar("DOĞRULAMA: politika faizi çapraz sınavı yapılamadı (aylık BIS serisi yok).")

    # (3) TLREF ↔ BİST gecelik repo AOF
    if {"tlref", "bist_on"} <= set(M.columns):
        d3 = M[["tlref", "bist_on"]].dropna()
        f3 = (d3["tlref"] - d3["bist_on"]).abs()
        D["tlref"] = {
            "kaynak": "TP.BISTTLREF.ORAN ↔ TP.AOFOBAP (BİST gecelik repo AOF)",
            "n": int(len(d3)), "maks_fark_pp": float(f3.max()),
            "ort_fark_pp": float(f3.mean()),
            "p99_fark_pp": float(f3.quantile(0.99)), "esik_pp": ESIK_TLREF_PP,
            "son_tlref": float(d3["tlref"].iloc[-1]),
            "son_bist": float(d3["bist_on"].iloc[-1]),
            "gecti": bool(f3.max() <= ESIK_TLREF_PP)}
        if f3.max() > ESIK_TLREF_PP:
            dur.append(f"DOĞRULAMA: TLREF ile BİST gecelik repo AOF arasında "
                       f"{f3.max():.3f} puanlık sapma var.")

    # (T1) AOSM taban varsayımı — TANI (durdurmaz)
    if {"aosm_kalan", "aosm"} <= set(M.columns) and "sto_1hi_tutar" in g.columns:
        k = M["aosm_kalan"].dropna()
        h_gun = (g["sto_1hi_tutar"] / 1000.0).reindex(k.index)
        oran = (k / h_gun).replace([np.inf, -np.inf], np.nan).dropna()
        D["aosm_taban"] = {
            "kaynak": "(TP.APIFON2.IHA − ONI) / günlük 1HI tutarı ≈ 5 iş günü",
            "n": int(len(oran)),
            "medyan_kat": float(oran.median()) if len(oran) else None,
            "negatif_kalan_gun": int((k < 0).sum()),
            "not": ("kalan bacağın tamamı haftalık depo alım ihalesi (1HI) "
                    "varsayılıyor; oran 5'ten belirgin saparsa varsayım zayıflar"),
        }
        if len(oran) and not (3.0 <= float(oran.median()) <= 7.0):
            uyar(f"AOSM VARSAYIMI ZAYIF: kalan sterilizasyon bacağı günlük 1HI "
                 f"tutarının {oran.median():.1f} katı (5 bekleniyordu). "
                 "Kalan bacakta başka bir ihale türü olabilir.")
        if int((k < 0).sum()) > 0:
            uyar(f"AOSM: {int((k < 0).sum())} günde ONI tutarı ihale "
                 "sterilizasyonundan büyük — o günlerde kalan bacak sıfırlandı.")

    # (T1b) HATLAR ARASI TUTARLILIK — rezerv hattıyla aynı swap serisi
    # Rezerv hattı (Aktarılacak Projeler/TCMBNetRezerv) yerleşik swap
    # düzeltmesini KENDİ boru hattında kuruyor. İki hat aynı EVDS serisini
    # farklı sorular için kullanıyor; sayı AYNI çıkmalı:
    #     swap_yerli_usd  =  (TOTALSTOKALIMYONLU − TOTALSTOKSATIMYONLU) / 1000
    # Tutmuyorsa iki sayfada iki farklı "swap stoku" dolaşıyor demektir.
    rez_yol = veri.KOK / "Aktarılacak Projeler" / "TCMBNetRezerv" / "gunluk.csv"
    if rez_yol.exists() and {"swap_alim_usd", "swap_satim_usd"} <= set(M.columns):
        try:
            R = pd.read_csv(rez_yol, index_col=0, parse_dates=True)
            d5 = pd.DataFrame({
                "biz": (M["swap_alim_usd"] - M["swap_satim_usd"]) / 1000.0,
                "rezerv_hatti": R.get("swap_yerli_usd")}).dropna()
            if len(d5):
                f5 = (d5["biz"] - d5["rezerv_hatti"]).abs()
                D["hatlar_arasi_swap"] = {
                    "kaynak": ("bu hat (TP.SWAPTEKTAR alım−satım)/1000 ↔ rezerv "
                               "hattı gunluk.csv · swap_yerli_usd"),
                    "n": int(len(d5)), "maks_fark_mlr_usd": float(f5.max()),
                    "son_biz": float(d5["biz"].iloc[-1]),
                    "son_rezerv": float(d5["rezerv_hatti"].iloc[-1]),
                    "son_tarih": str(d5.index[-1].date()),
                    "gecti": bool(f5.max() < 1e-6)}
                if f5.max() >= 1e-6:
                    uyar(f"HATLAR AYRIŞTI: swap stoku rezerv hattıyla "
                         f"{f5.max():.4f} mlr USD farklı. İki sayfada iki farklı "
                         "swap tanımı dolaşıyor olabilir.")
        except Exception as ex:
            uyar(f"REZERV HATTI OKUNAMADI ({type(ex).__name__}); hatlar arası swap "
                 "tutarlılığı sınanamadı.")
    else:
        uyar("REZERV HATTI ÇIKTISI YOK — hatlar arası swap tutarlılığı "
             "sınanamadı (Şekil 08 çapraz paneli eksik kalabilir).")

    # (T2) aylık gecelik repo AOF — TANI (farklı araç; durdurmaz)
    if "api_repo_ort" in a.columns and "bist_on" in M.columns:
        d4 = pd.DataFrame({"evds": a["api_repo_ort"],
                           "biz": M["bist_on"].dropna().resample("MS").mean()}).dropna()
        if len(d4):
            f4 = (d4["evds"] - d4["biz"]).abs()
            D["gecelik_repo_aylik"] = {
                "kaynak": "TP.API.REP.ORT.G1 (aylık, TCMB APİ repo) ↔ TP.AOFOBAP ay ort.",
                "n": int(len(d4)), "maks_fark_pp": float(f4.max()),
                "son12_maks_pp": float(f4.tail(12).max()),
                "not": ("iki seri AYNI ARACI ÖLÇMÜYOR (biri TCMB'nin APİ "
                        "reposu, öteki BİST piyasa reposu); makullük sınavıdır, "
                        "hattı durdurmaz")}

    # (T3) AOFM KOMPOZİSYON SINAVI — TANI (durdurmaz)
    # AOFM tek bir EVDS serisinden (TP.APIFON4) geliyor ve şimdiye kadar hiç
    # çaprazlanmıyordu. Oysa aynı gün kalem kırılımı da yayımlanıyor: ihale
    # fonlaması politika faizinden, kotasyon reposu koridorun tavanından, geç
    # likidite penceresi GLP satış faizinden fiyatlanır. Bu üçünün tutar
    # ağırlıklı ortalaması AOFM'yi yeniden kurar. Sınav bir KALİBRASYON DEĞİL,
    # kalem eşlemesinin bozulup bozulmadığının denetimidir: EVDS kodları
    # değişirse (KOT.A/KOT.B gibi) fark açılır ve uyarı düşer.
    gerek = {"fon_ihale", "fon_kot_repo", "fon_glp"}
    if gerek <= set(M.columns) and "aofm" in M.columns:
        w = pd.DataFrame({
            "ihale": M["fon_ihale"].fillna(0).clip(lower=0),
            "kot": M["fon_kot_repo"].fillna(0).clip(lower=0),
            "glp": M["fon_glp"].fillna(0).clip(lower=0)})
        f = pd.DataFrame({
            "ihale": M["politika"],
            "kot": M["koridor_ust"],
            "glp": M["glp_satis"].fillna(M["koridor_ust"])})
        payda = w.sum(axis=1)
        pay = (w * f).sum(axis=1)
        yeniden = (pay / payda.where(payda > 0))
        d6 = pd.DataFrame({"biz": yeniden, "evds": M["aofm"]}).dropna()
        if len(d6):
            f6 = (d6["biz"] - d6["evds"]).abs()
            son250 = f6.tail(250)
            D["aofm_kompozisyon"] = {
                "kaynak": ("(ihale×politika + kotasyon repo×koridor tavanı + "
                           "GLP×GLP satış) / toplam ↔ TP.APIFON4"),
                "n": int(len(d6)), "medyan_fark_pp": float(f6.median()),
                "p95_fark_pp": float(f6.quantile(0.95)),
                "maks_fark_pp": float(f6.max()),
                "son250_medyan_pp": float(son250.median()),
                "son_gun": str(d6.index[-1].date()),
                "son_fark_pp": float(f6.iloc[-1]),
                "esik_pp": ESIK_AOFM_KOMPOZISYON_PP,
                "not": ("Uç sapmalar geç likidite penceresi dönemlerinde ve "
                        "kompozisyon geçişlerinde yoğunlaşır; kalibrasyon "
                        "sabiti KULLANILMAZ."),
                "gecti": bool(son250.median() <= ESIK_AOFM_KOMPOZISYON_PP)}
            if son250.median() > ESIK_AOFM_KOMPOZISYON_PP:
                uyar(f"AOFM KOMPOZİSYONU: kalem kırılımından yeniden kurulan "
                     f"AOFM son 250 iş gününde medyan "
                     f"{son250.median():.3f} puan sapıyor "
                     f"(eşik {ESIK_AOFM_KOMPOZISYON_PP}). EVDS kalem "
                     "eşlemesi değişmiş olabilir.")

    # (T4) AOFM BANT DENETİMİ — TANI (durdurmaz)
    # AOFM tanım gereği koridor tabanı ile GLP satış faizi arasında olmalıdır:
    # sistem hiçbir günde tabanın altından borçlanamaz, tavanın (GLP varsa
    # GLP'nin) üstünde de fonlanmaz. Dışarı çıkması ya stok gecikmesidir ya da
    # veri hatası; ikisi de sessiz kalmamalı.
    if {"aofm", "koridor_alt"} <= set(M.columns):
        ust = M["glp_satis"].fillna(M["koridor_ust"])
        alt_ihlal = (M["aofm"] < M["koridor_alt"] - KORIDOR_USTU_PAY)
        ust_ihlal = (M["aofm"] > ust + KORIDOR_USTU_PAY)
        n_alt, n_ust = int(alt_ihlal.sum()), int(ust_ihlal.sum())
        D["aofm_bant"] = {
            "kaynak": "AOFM ∈ [koridor tabanı, GLP satış (yoksa tavan)]",
            "n": int(M["aofm"].notna().sum()),
            "alt_ihlal_gun": n_alt, "ust_ihlal_gun": n_ust,
            "alt_ihlal_son": (str(M.index[alt_ihlal][-1].date())
                              if n_alt else None),
            "ust_ihlal_son": (str(M.index[ust_ihlal][-1].date())
                              if n_ust else None),
            "not": ("AOFM bir STOK ortalamasıdır; faiz kararı haftalarında "
                    "eski fonlama stokta durduğu için bandın dışına düşebilir. "
                    "Tanı amaçlıdır, hattı durdurmaz."),
            "gecti": bool(n_ust == 0)}
        if n_ust:
            uyar(f"AOFM BANT DIŞI: {n_ust} iş gününde AOFM, GLP satış "
                 "faizinin de üstünde — tanım gereği imkânsız bir değer. "
                 "Kotasyon serilerinde eksik gün olabilir.")
    return D, dur


# ===========================================================================
def kos() -> int:
    g = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
    h = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    a = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)

    s_gun = veri.son_gun(g)
    s_hafta = veri.son_hafta(h)
    print(f"TCMB fonlama & likidite — metrik · veri {gun_ad(s_gun)}")

    # VERİ KATMANININ UYARILARI BURADA DEVRALINIR. Bunlar (tazelik alarmları,
    # "ESKİ ÖNBELLEK: n gün eski", ölü seri, düşen demet) veri.py'de basılıp
    # data/veri_durum.json'a yazılıyor; devralınmazsa uyarilar.json'a hiç
    # girmez ve sayfada GÖRÜNMEZ — düzenin yasakladığı sessiz bayatlama.
    # Aynı koşuda veri.py çağrılmışsa listesi bellekte de duruyor; iki kaynak
    # birleştirilir ki veri.py ayrı koşulmuş olsa bile uyarı kaybolmasın.
    devir: list[str] = list(veri.uyarilar())
    try:
        durum = json.loads(
            (VERI / "veri_durum.json").read_text(encoding="utf-8"))
        devir += list(durum.get("uyarilar") or [])
    except Exception as ex:
        uyar(f"VERİ KATMANI KAYDI OKUNAMADI ({type(ex).__name__}) — veri katmanının "
             "uyarıları devralınamadı; tazelik uyarıları bu koşuda GÖRÜNMEYEBİLİR.")
    for u in devir:
        if u not in _UYARI:
            _UYARI.append(u)
            print("  ! (veri) " + u, flush=True)

    M = fonlama_metrikleri(g)
    Z, zk_tani = zk_metrikleri(M, h)
    H, gec_tani = gecirgenlik(M, h)
    don = donemler(M)
    don_alt = donemler_alti(M)
    D, dur = dogrula(g, M, a)
    # ZK taban birim denetimi durdurucudur: yanlış birimle hesaplanan tesis
    # oranı hiç oran olmamasından kötüdür (dolu grafik, yanlış sayı).
    if zk_tani.get("taban_birim_dur"):
        dur.append(zk_tani["taban_birim_dur"])

    # --- rejim tanısı ------------------------------------------------------
    son1y = M.loc[M.index >= s_gun - pd.Timedelta(days=365)]
    rejim = {
        "pencere_gun": int(len(son1y)),
        "net_negatif_gun": int((son1y["net_fonlama"] < 0).sum()),
        "net_pozitif_gun": int((son1y["net_fonlama"] > 0).sum()),
        "fonlama_sifir_gun": int((son1y["fon_top"] == 0).sum()),
        "aofm_gecersiz_gun": int((~son1y["aofm_gecerli"]).sum()),
        "aofm_gecersizken_dolu_gun": int(
            ((~son1y["aofm_gecerli"]) & son1y["aofm_ham"].notna()).sum()),
        "taban_esik_mn_tl": AOFM_TABAN_ESIK,
        # Marjinal faizin son bir yılda hangi kaynaktan geldiği. Vekil (TLREF)
        # payı yükselirse "TCMB'nin marjinal fiyatı" cümlesi zayıflar; bu
        # yüzden pay gizlenmez, sayılır.
        "marjinal_kaynak": {str(k): int(v) for k, v
                            in son1y["marjinal_kaynak"].value_counts().items()},
    }
    rejim["marjinal_kaynak_tam"] = {
        str(k): int(v) for k, v in M["marjinal_kaynak"].value_counts().items()}
    if rejim["aofm_gecersizken_dolu_gun"] > 0:
        uyar(
            f"AOFM TABANSIZ: son bir yılda {rejim['aofm_gecersizken_dolu_gun']} "
            f"iş gününde fonlama {AOFM_TABAN_ESIK / 1000:.0f} milyar TL eşiğinin altında "
            "olduğu hâlde EVDS bir AOFM değeri basmış. O günler geçersiz "
            "işaretlendi; grafikte kesikli, metinde 'fonlama maliyeti' cümlesi "
            "kurulmuyor.")

    # --- sıfıra düşmüş olgular (bayrak) ------------------------------------
    swap_son = M["swap_alim_usd"].dropna() if "swap_alim_usd" in M else pd.Series(dtype=float)
    bayrak = {
        "swap_alim_aktif": bool(len(swap_son) and swap_son.iloc[-1] > 0),
        "swap_satim_aktif": bool("swap_satim_usd" in M
                                 and M["swap_satim_usd"].dropna().iloc[-1] > 0),
        "glp_aktif": bool(M["fon_glp"].dropna().tail(60).gt(0).any())
        if "fon_glp" in M else False,
        "likidite_senedi_aktif": bool(M["ste_liksen"].dropna().tail(60).gt(0).any())
        if "ste_liksen" in M else False,
        "ihale_fonlama_aktif": bool(M["fon_ihale"].dropna().tail(60).gt(0).any()),
    }
    if not bayrak["swap_alim_aktif"]:
        print("  · swap (alım yönlü) stoku SIFIR — 'swap ile TL sağlama' cümlesi "
              "sayfada bayrakla kapanır (seri taze, olgu yok).")

    # --- yazım -------------------------------------------------------------
    M.to_csv(VERI / "metrik.csv")
    if not Z.empty:
        Z.to_csv(VERI / "zk.csv")
    if not H.empty:
        H.to_csv(VERI / "haftalik_metrik.csv")

    ozet = {
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        # Grafik ve metin katmanı eşikleri BURADAN okur — iki yerde iki farklı
        # sayı dolaşmasın (şekil altındaki "en az 5 baz puan" cümlesi eşik
        # değişince sessizce yanlışa dönmesin).
        "esik": {
            "aofm_taban_mn_tl": AOFM_TABAN_ESIK,
            "koridor_ustu_pay_pp": KORIDOR_USTU_PAY,
            "donem_min_gun": DONEM_MIN_GUN,
            "gecis_pencere_hafta": GECIS_PENCERE,
        },
        "son_hafta": s_hafta.strftime("%Y-%m-%d"),
        "rejim": rejim,
        "bayrak": bayrak,
        "zk": zk_tani,
        "gecirgenlik": gec_tani,
        "donemler": don,
        "donemler_alti": don_alt,
        "dogrulama": D,
        "aosm_not": ("AOSM bu çalışmanın türetmesidir; TCMB tarafından "
                     "yayımlanan bir seri DEĞİLDİR."),
        "zk_oran_not": ("İma edilen ZK oranı gerçekleşmiş TESİS oranıdır; "
                        "TCMB'nin tebliğle ilan ettiği oran DEĞİLDİR."),
        "uyarilar": list(_UYARI),
    }
    (VERI / "metrik_ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1), encoding="utf-8")
    (PROJE / "uyarilar.json").write_text(json.dumps(
        {"tarih": s_gun.strftime("%Y-%m-%d"),
         "kosum": pd.Timestamp.today().strftime("%Y-%m-%d"),
         "uyarilar": list(_UYARI), "dogrulama": D},
        ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"  yazıldı: data/metrik.csv ({M.shape[0]}x{M.shape[1]})")
    for ad, r in D.items():
        if "gecti" in r:
            maks = next((r[k] for k in ("maks_fark_pp", "maks_fark_mn_tl",
                                        "maks_fark_mlr_usd") if k in r), None)
            print(f"    doğrulama {'✓' if r['gecti'] else '✗'} {ad}: n={r['n']}, "
                  f"maks {maks:.6g}" if maks is not None
                  else f"    doğrulama {'✓' if r['gecti'] else '✗'} {ad}")
    print(f"  örtük sıkılaştırma dönemi: {len(don)} · "
          f"koridor altı dönem: {len(don_alt)}")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    if dur:
        for x in dur:
            print("  ✗ " + x)
        raise SystemExit(
            "DUR: bağımsız doğrulama düştü. Yanlış sayı yayına gitmesin diye "
            "grafik ve ozet üretilmiyor. Ayrıntı: uyarilar.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(kos())
