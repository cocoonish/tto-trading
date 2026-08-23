# -*- coding: utf-8 -*-
"""Merkezi Yönetim Bütçesi & Borç Stoku — metrik katmanı.

Ne hesaplar
-----------
1. **Merkezi yönetim dengesi ve faiz dışı dengesi.** EVDS'te HAZIR YOK:
   GEL001 − GID001 ile TÜRETİLİR. Genel bütçe karşılığı (GEN35/GEN34) yalnız
   ÇAPRAZ KONTROL için tutulur; kapsam farkı %12,6 civarındadır ve sıfır
   BEKLENMEZ (özel bütçeli idareler + düzenleyici kurumlar).
2. **REEL BÜTÇE — hattın asıl hikâyesi.** Gelir ve harcama TÜFE ile deflate
   edilip SON AY FİYATLARINA taşınır, sonra 12 aylık birikimli alınır. Nominal
   seri tek başına yanıltıcıdır: aynı dönemde nominal gelir +%44 iken reel
   gelir +%10 olabiliyor.
3. **Reel değişim ÇARPIMSAL konvansiyonla.** reel_yy = (1+nominal)/(1+enf) − 1.
   Basit çıkarma (nominal − enflasyon) bu depoda YASAK (Fisher kararı); yüksek
   enflasyonda iki tanım 10 puandan fazla ayrışır.
4. **Faiz yükü:** faiz/vergi geliri, faiz/GSYH, faiz giderinin iç/dış/kira
   sertifikası/iskonto ayrışması.
5. **Borç stoku:** iç borç (bin TL) + dış borç (milyon USD × kur) → toplam;
   döviz payı; stok/GSYH; net stok (Hazine nakit varlığı düşülmüş).
6. **Kur duyarlılığı:** USD/TRY şoku −%10…+%30 senaryoları; paralel şok ve
   yalnız-USD şoku ayrı ayrı (eurobondun para birimi ağırlıklarıyla).
7. **DİBS sahiplik ve vade yapısı.** Vade/para tabloları PİYASA değeri
   üzerindedir; paylar HER ZAMAN kendi tablosunun toplamına bölünür.
8. **İç borç çevirme oranı** (12 aylık birikimli; anapara ve anapara+faiz).
   Aylık oran kullanılamaz — itfasız aylarda payda sıfıra yaklaşıp oran patlar.
9. **Stok ayrıştırması:** Δstok = net borçlanma + kur farkı + ARTIK. Artık
   açıkça gösterilir; toplamı kapatmak için düzeltme YAPILMAZ.
10. **Bağımsız doğrulama.** Türettiğimiz büyüklükleri EVDS'in kendi yayımladığı
    karşılıklarıyla kıyaslar (DİBS+eurobond ↔ finansal hesaplar F.3;
    MY dengesi ↔ GB dengesi; ayrıştırma artığı). Eşik aşılırsa uyarı düşer.

ORAN METRİKLERİ AKIM SERİLERİNDEN ERKEN BİTER. GSYH ve finansal hesaplar
145 gün gecikmeli; GSYH'yi ffill ile ileri taşıyıp daha yeni bir oran üretmek
SESSİZ BAYATLAMADIR ve burada yapılmaz.

Koşum:  python3 metrik.py   (önce veri.py)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import veri
from veri import PROJE, VERI, ay_ad, ceyrek_ad, gun_ad

# --------------------------------------------------------------------------- ölçekler
# BİRİM DÖNÜŞÜMÜ TEK YERDE. Kaynak birimler EVDS'ten okunur ve veri.py'de her
# koşuda doğrulanır (birim_denetimi); buradaki çarpanlar o birimlere bağlıdır.
#   bütçe akımları, iç borç, finansal hesaplar, GSYH : bin TL
#   DİBS                                             : milyon TL
#   eurobond, brüt dış borç                          : milyon ABD doları
BINTL_MLR = 1e-6      # bin TL → milyar TL
BINTL_TRL = 1e-9      # bin TL → trilyon TL
MNTL_TRL = 1e-6       # milyon TL → trilyon TL
MUSD_MLRUSD = 1e-3    # milyon ABD doları → milyar ABD doları
MUSD_BINTL = 1e3      # milyon ABD doları → bin TL, KUR İLE ÇARPILARAK
# Mertebe kıyası (kodda yorumla belgelenmesi kuralı): 93.222 milyon USD dış
# borç × 1e3 × 44 TL ≈ 4,1e9 bin TL = 4,1 trilyon TL. İç borç 9,0 trilyon TL.
# Toplam ≈ 13,1 trilyon TL; 4 çeyreklik GSYH ≈ 67 trilyon TL → %19. Türkiye
# için bilinen bant %15–35; mertebe tutuyor.

# --------------------------------------------------------------------------- eşikler
# Kur duyarlılık senaryoları (USD/TRY'de oransal şok).
KUR_SOKLARI = [-0.10, -0.05, 0.0, 0.05, 0.10, 0.20, 0.30]

# DİBS + eurobond ile finansal hesapların F.3 kalemi ÖZDEŞ DEĞİL, BANTLIDIR:
# finansal hesaplar PİYASA değerli ve kapsamı biraz geniş. Ölçülen fark son
# çeyreklerde −%7…−%12. Bunu sıfıra zorlayan düzeltme YAPILMAZ; bant denetlenir.
F3_BANT = (-0.20, 0.05)

# MY dengesi ile GB dengesi arasındaki kapsam farkı. %0 BEKLENMEZ; bu eşik
# "kapsam farkı makul mü" sorusunu yanıtlar, özdeşlik aramaz.
KAPSAM_ESIK = 0.35

# Stok ayrıştırmasında artığın kabul edilebilir payı (|artık| / |Δstok|).
# Artık; genel bütçe ↔ merkezi yönetim kapsam farkını, dış borcun üç aylık
# adımlanmasını, nakit dışı ihracı ve değerleme etkilerini içerir.
ARTIK_ESIK = 0.60

# Çevirme oranının mertebe bandı (12 aylık birikimli). Ölçülen son 5 yıl
# bandı %113–%593; aylık oran kullanılsaydı payda sıfıra yaklaşıp patlardı.
CEVIRME_BANT = (0.5, 8.0)

_UYARI: list[str] = []


def uyar(m: str) -> None:
    if m not in _UYARI:
        _UYARI.append(m)
    print("  ! " + m, flush=True)


def _q(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Aylık damgayı ait olduğu ÇEYREĞİN SON GÜNÜNE taşır (GSYH ile hizalama)."""
    return pd.PeriodIndex(idx, freq="Q").to_timestamp(how="end").normalize()


def _ceyrek_sonu(s: pd.Series) -> pd.Series:
    """Aylık seriden yalnız ÇEYREK SONU aylarını alıp çeyrek damgasına taşır.

    Çeyreğin üç ayını da alıp aynı damgaya yazmak son değeri sessizce
    Ocak'ınkiyle değiştirebilirdi; yalnız 3/6/9/12 alınır.
    """
    x = s[s.index.month.isin([3, 6, 9, 12])].dropna()
    if x.empty:
        return x
    x = x.copy()
    x.index = _q(x.index)
    return x[~x.index.duplicated(keep="last")]


# ===========================================================================
# (1) BÜTÇE — nominal, reel, 12 aylık birikimli
# ===========================================================================
def butce_metrikleri(a: pd.DataFrame, s_ay: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    M = pd.DataFrame(index=a.index)
    tani: dict = {}

    # --- deflatör ----------------------------------------------------------
    # TÜFE bütçeden bir ay ÖNDE yayımlanıyor. Deflatörün TABANI son BÜTÇE ayıdır
    # (son TÜFE ayı değil): "son ay fiyatlarıyla" derken kastedilen, sayfanın
    # anlattığı bütçe ayıdır. Taban ileri alınsaydı bütün reel seri, henüz
    # bütçesi yayımlanmamış bir ayın fiyatlarına taşınırdı.
    tufe = a["tufe"].dropna()
    if s_ay not in tufe.index:
        raise SystemExit(f"DUR: TÜFE {s_ay:%Y-%m} ayında yok — reel seri "
                         "üretilemez.")
    taban = float(tufe.loc[s_ay])
    M["tufe"] = a["tufe"]
    M["deflator"] = taban / a["tufe"]
    # fill_method=None ZORUNLU. pandas'ın varsayılanı NaN'ları İLERİ DOLDURUP
    # (pad) oran hesaplıyor: bütçe serisinin bittiği aydan SONRAKİ aylar için
    # bile bir y/y değeri üretiyordu (ölçüldü: bütçe 2026-06'da bitiyor, ama
    # gelir_reel_yy 2026-07'de dolu geliyordu). Tam da yasaklanan sessiz
    # bayatlama sınıfı: seri ilerlemediği hâlde sayfa ilerlemiş görünür.
    M["tufe_yy"] = a["tufe"].pct_change(12, fill_method=None) * 100
    tani["deflator_taban_ay"] = s_ay.strftime("%Y-%m")
    tani["deflator_taban_endeks"] = taban
    tani["tufe_son_ay"] = tufe.index[-1].strftime("%Y-%m")

    # --- düzeyler (milyar TL) ---------------------------------------------
    NOMINAL = {
        "gelir": "my_gelir", "gider": "my_gider", "fdg": "faiz_disi_gider",
        "faiz": "faiz_gideri", "vergi": "vergi",
        "v_gelir": "v_gelir", "v_kurumlar": "v_kurumlar",
        "v_kdv_dahil": "v_kdv_dahil", "v_kdv_ithal": "v_kdv_ithal",
        "v_otv": "v_otv", "v_damga": "v_damga",
        "personel": "personel", "sgk_primi": "sgk_primi",
        "mal_hizmet": "mal_hizmet", "cari_transfer": "cari_transfer",
        "sermaye_gider": "sermaye_gider", "sermaye_transfer": "sermaye_transfer",
        "borc_verme": "borc_verme",
        "faiz_ic": "faiz_ic", "faiz_dis": "faiz_dis",
        "faiz_kira": "faiz_kira_sert", "faiz_iskonto": "faiz_iskonto",
    }
    for ad, kol in NOMINAL.items():
        if kol not in a.columns:
            uyar(f"KALEM YOK: {kol} — '{ad}' metrikleri üretilmedi.")
            continue
        M[f"{ad}_ay"] = a[kol] * BINTL_MLR                        # milyar TL
        M[f"{ad}_12a"] = a[kol].rolling(12).sum() * BINTL_TRL      # trilyon TL
        # Reel: önce AYLIK deflate, sonra 12 aylık toplam. Sıra bağlayıcı —
        # önce toplayıp sonra tek bir deflatörle bölmek, yıl içindeki fiyat
        # hareketini yok sayar ve yüksek enflasyonda %5'e varan hata verir.
        reel = a[kol] * M["deflator"]
        M[f"reel_{ad}_12a"] = reel.rolling(12).sum() * BINTL_TRL

    M = M.copy()                   # parçalanma giderilir (sütunlar tek tek eklendi)

    # --- dengeler ----------------------------------------------------------
    # MERKEZİ YÖNETİM dengesi TÜRETİLİR (EVDS'te hazır yok).
    M["denge_ay"] = (a["my_gelir"] - a["my_gider"]) * BINTL_MLR
    M["fdd_ay"] = (a["my_gelir"] - a["faiz_disi_gider"]) * BINTL_MLR
    M["denge_12a"] = (a["my_gelir"] - a["my_gider"]).rolling(12).sum() * BINTL_TRL
    M["fdd_12a"] = (a["my_gelir"] - a["faiz_disi_gider"]).rolling(12).sum() * BINTL_TRL
    # GENEL BÜTÇE karşılıkları — yalnız çapraz kontrol için, grafikte MY ile
    # aynı eksene KARIŞTIRILMAZ.
    M["gb_denge_12a"] = a["gb_denge"].rolling(12).sum() * BINTL_TRL
    M["gb_fdd_12a"] = a["gb_faiz_disi_denge"].rolling(12).sum() * BINTL_TRL

    x = pd.concat([M["denge_12a"], M["gb_denge_12a"]], axis=1).dropna().tail(24)
    if len(x):
        kapsam = float((x["denge_12a"] - x["gb_denge_12a"]).abs().sum()
                       / x["gb_denge_12a"].abs().sum())
        tani["kapsam_farki_24ay"] = kapsam
        tani["kapsam_esik"] = KAPSAM_ESIK
        if kapsam > KAPSAM_ESIK:
            uyar(f"KAPSAM: merkezi yönetim dengesi ile genel bütçe dengesi son "
                 f"24 ayda %{kapsam*100:.0f} ayrışıyor (eşik %{KAPSAM_ESIK*100:.0f}). "
                 "Kalem eşlemesi değişmiş olabilir.")

    # --- reel ve nominal y/y (ÇARPIMSAL konvansiyon) -----------------------
    for ad in ("gelir", "gider", "fdg", "faiz", "vergi", "v_gelir", "v_kurumlar",
               "v_kdv_dahil", "v_kdv_ithal", "v_otv", "v_damga", "personel",
               "sgk_primi", "mal_hizmet", "cari_transfer", "sermaye_gider",
               "sermaye_transfer", "borc_verme", "faiz_ic", "faiz_dis",
               "faiz_kira", "faiz_iskonto"):
        if f"{ad}_12a" not in M.columns:
            continue
        M[f"{ad}_nom_yy"] = M[f"{ad}_12a"].pct_change(12, fill_method=None) * 100
        M[f"{ad}_reel_yy"] = M[f"reel_{ad}_12a"].pct_change(12, fill_method=None) * 100

    # FISHER DENETİMİ. Reel değişim, iki reel düzeyin oranından geliyor; bu
    # cebirsel olarak (1+nominal)/(1+deflatör) − 1 demektir. Basit çıkarma
    # (nominal − enflasyon) kullanılsaydı aşağıdaki artık sıfır ÇIKMAZDI.
    # Depo kararı: çarpımsal konvansiyon bağlayıcı.
    nom = M["gelir_12a"].pct_change(12, fill_method=None)
    reel = M["reel_gelir_12a"].pct_change(12, fill_method=None)
    defl = (M["gelir_12a"] / M["reel_gelir_12a"]).pct_change(12, fill_method=None)
    fisher_artik = (reel - ((1 + nom) / (1 + defl) - 1)).abs()
    basit_fark = (reel - (nom - defl)).abs()
    tani["fisher"] = {
        "carpimsal_artik_maks_pp": float(fisher_artik.max() * 100),
        "basit_cikarma_farki_maks_pp": float(basit_fark.max() * 100),
        "basit_cikarma_farki_son_pp": float(basit_fark.dropna().iloc[-1] * 100)
        if basit_fark.notna().any() else None,
        "not": ("Reel değişim çarpımsal (Fisher) konvansiyonla hesaplanır: "
                "(1+nominal)/(1+deflatör) − 1. Basit çıkarma bu depoda yasak."),
    }
    if float(fisher_artik.max()) > 1e-9:
        uyar("FISHER: çarpımsal özdeşlik tutmuyor — reel seri türetimi bozulmuş.")

    M = M.copy()

    # --- kompozisyon payları (12 aylık birikimli üzerinden) ----------------
    # Paylar 12 AYLIK BİRİKİMLİDEN alınır: aylık paylar mevsimsellikten
    # (kurumlar vergisi Şub/Nis/Ağu'da yığılır) okunamaz hâle gelir.
    vergi12 = M["vergi_12a"]
    for ad in ("v_gelir", "v_kurumlar", "v_kdv_dahil", "v_kdv_ithal",
               "v_otv", "v_damga"):
        M[f"pay_{ad}"] = M[f"{ad}_12a"] / vergi12 * 100
    # min_count=1 ZORUNLU. pandas'ın varsayılanı bütün bileşenler NaN olan
    # satırda toplamı 0 sayıyor ve artık kalem 100 çıkıyordu: 12 aylık pencere
    # dolmadan önceki 47 ay ve bütçesi HENÜZ YAYIMLANMAMIŞ son ay için yığın
    # "tamamı diğer vergiler" gösteriyordu (ölçüldü: 48 satır). ozet.json da o
    # sahte 100'ü son değer diye okuyordu — sessiz bayatlamanın ta kendisi.
    M["pay_v_diger"] = 100 - M[[f"pay_{x}" for x in
                                ("v_gelir", "v_kurumlar", "v_kdv_dahil",
                                 "v_kdv_ithal", "v_otv", "v_damga")]].sum(
                                     axis=1, min_count=1)
    gider12 = M["gider_12a"]
    for ad in ("personel", "sgk_primi", "mal_hizmet", "cari_transfer",
               "sermaye_gider", "sermaye_transfer", "borc_verme", "faiz"):
        M[f"pay_{ad}"] = M[f"{ad}_12a"] / gider12 * 100
    # min_count=1 — yukarıdaki ile aynı gerekçe.
    M["pay_gider_diger"] = 100 - M[[f"pay_{x}" for x in
                                    ("personel", "sgk_primi", "mal_hizmet",
                                     "cari_transfer", "sermaye_gider",
                                     "sermaye_transfer", "borc_verme",
                                     "faiz")]].sum(axis=1, min_count=1)

    # --- faiz yükü ---------------------------------------------------------
    M["faiz_vergi"] = M["faiz_12a"] / M["vergi_12a"] * 100
    M["faiz_gelir"] = M["faiz_12a"] / M["gelir_12a"] * 100
    return M.copy(), tani          # copy(): sütun sütun eklemeden gelen parçalanmayı gider


# ===========================================================================
# (2) BORÇ STOKU — iç + dış (TL karşılığı), döviz payı, ayrıştırma
# ===========================================================================
def stok_metrikleri(a: pd.DataFrame, c: pd.DataFrame, g: pd.DataFrame,
                    M: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    tani: dict = {}

    # Ay sonu kuru: stok büyüklüğü ay SONU kuruyla değerlenir (ortalama kur
    # akım kalemleri içindir). Aylık damga ay BAŞI olduğu için kur, o ayın
    # içindeki son iş gününden alınır.
    kur_ay = g["usdtry"].dropna().resample("MS").last()
    eur_ay = g["eurtry"].dropna().resample("MS").last()
    M["kur_ay"] = kur_ay.reindex(M.index)
    M["eur_ay"] = eur_ay.reindex(M.index)

    # Dış borç ÜÇ AYLIK; ay içine BASAMAK olarak taşınır (çeyrek içinde sabit).
    # SON yayımlanan çeyreğin ÖTESİNE taşınmaz — ffill ile ileri uzatmak
    # sessiz bayatlamadır. Bu yüzden birleşik stok, dış borcun son çeyreğini
    # aşan aylarda ÜRETİLMEZ.
    dis = c["db_merkezi_yon"].dropna()                       # milyon USD
    son_dis_ay = dis.index[-1].to_period("M").to_timestamp()
    dis_ay = dis.copy()
    dis_ay.index = dis_ay.index.to_period("M").to_timestamp()
    dis_ay = dis_ay.reindex(M.index).ffill()
    dis_ay[M.index > son_dis_ay] = np.nan

    M["dis_borc_musd"] = dis_ay
    # milyon USD → bin TL → trilyon TL   (1 milyon USD = 1e3 bin TL × kur)
    M["dis_borc_trl"] = dis_ay * MUSD_BINTL * M["kur_ay"] * BINTL_TRL
    M["ic_borc_trl"] = a["ic_borc_toplam"] * BINTL_TRL
    M["toplam_borc_trl"] = M["ic_borc_trl"] + M["dis_borc_trl"]
    M["doviz_pay"] = M["dis_borc_trl"] / M["toplam_borc_trl"] * 100
    # İç borç araç kırılımı (yapısal sıfırlar grafiğe girmez, toplamda kalır)
    M["ic_tahvil_trl"] = a["ic_tahvil"] * BINTL_TRL
    M["ic_bono_trl"] = a["ic_bono"] * BINTL_TRL

    tani["son_dis_ceyrek"] = f"{dis.index[-1]:%Y-%m-%d}"
    tani["birlesik_stok_son_ay"] = (
        f"{M['toplam_borc_trl'].dropna().index[-1]:%Y-%m}"
        if M["toplam_borc_trl"].notna().any() else None)
    tani["doviz_payi_notu"] = (
        "Döviz payı YALNIZ dış borç üzerinden verilir. Döviz cinsi YURT İÇİ "
        "ihraçlar iç borç stokunun içinde kalır ve EVDS'te ayrıştırılamaz: "
        "GEN52/53/54 akımlarını kümüle ederek stok tahmin etmek kur farkı "
        "revalüasyonunu yok saydığı için iç borcun yalnız ~%1,2'sini verir "
        "(gerçek pay bunun çok üstünde). O yüzden bu tahmin REDDEDİLDİ.")

    # --- ima edilen faiz oranı (nominal) ve FISHER REEL --------------------
    # i = 12 aylık faiz gideri / ortalama borç stoku. Ortalama, yıl içinde
    # büyüyen stokta uç noktalardan birini seçmenin yarattığı yanı giderir.
    ort_stok = (M["toplam_borc_trl"] + M["toplam_borc_trl"].shift(12)) / 2
    M["ima_faiz_nominal"] = M["faiz_12a"] / ort_stok * 100
    # FISHER — basit çıkarma DEĞİL: r = (1+i)/(1+π) − 1.
    M["ima_faiz_reel"] = (((1 + M["ima_faiz_nominal"] / 100)
                           / (1 + M["tufe_yy"] / 100)) - 1) * 100
    M["ima_faiz_reel_basit"] = M["ima_faiz_nominal"] - M["tufe_yy"]
    s = (M["ima_faiz_reel"] - M["ima_faiz_reel_basit"]).dropna()
    tani["fisher_ima_faiz_fark_son_pp"] = float(s.iloc[-1]) if len(s) else None
    tani["fisher_ima_faiz_notu"] = (
        "İma edilen reel faiz Fisher konvansiyonuyla hesaplanır: "
        "(1+i)/(1+π) − 1. Basit çıkarma (i − π) yüksek enflasyonda aynı "
        "veriden puanlarca farklı bir sayı üretir; bu depoda kullanılmaz.")

    # --- çevirme oranı (12 aylık birikimli) --------------------------------
    sat = ["bono_tl_satis", "bono_dov_satis", "tahvil_tl_satis", "tahvil_dov_satis"]
    ode = ["bono_tl_odeme", "bono_dov_odeme", "tahvil_tl_odeme", "tahvil_dov_odeme"]
    sat = [k for k in sat if k in a.columns]
    ode = [k for k in ode if k in a.columns]
    # min_count=1: döviz cinsi bono kalemleri 2019 öncesinde HİÇ YOK (NaN);
    # sıfır sayılmaları doğru, ama bütün kalemler NaN ise toplam da NaN olmalı.
    s12 = a[sat].sum(axis=1, min_count=1).rolling(12).sum()
    o12 = a[ode].sum(axis=1, min_count=1).abs().rolling(12).sum()
    M["ic_satis_12a"] = s12 * BINTL_TRL
    M["ic_odeme_12a"] = o12 * BINTL_TRL
    M["cevirme"] = s12 / o12 * 100
    # Faiz dahil varyant: paydaya İÇ BORÇ FAİZ ÖDEMELERİ eklenir (GID153).
    faiz_ic12 = a["faiz_ic"].rolling(12).sum()
    M["cevirme_faiz"] = s12 / (o12 + faiz_ic12) * 100
    M["ic_borclanma_net_ay"] = a["ic_borclanma_net"] * BINTL_MLR
    M["dis_borclanma_net_ay"] = a["dis_borclanma_net"] * BINTL_MLR

    cev = M["cevirme"].dropna()
    if len(cev):
        son = float(cev.iloc[-1]) / 100
        tani["cevirme"] = {
            "son": float(cev.iloc[-1]),
            "son_faiz_dahil": float(M["cevirme_faiz"].dropna().iloc[-1]),
            "bant_5y_min": float(cev.tail(60).min()),
            "bant_5y_max": float(cev.tail(60).max()),
            "not": ("İç borç ÇEVİRME oranı finansman tablosundan (satış/ödeme) "
                    "hesaplanır ve Hazine İhraç hattındaki İHALE bazlı karşılama "
                    "oranıyla AYNI ŞEY DEĞİLDİR. 12 aylık birikimli zorunlu: "
                    "itfasız aylarda payda sıfıra yaklaşır ve aylık oran patlar."),
        }
        if not (CEVIRME_BANT[0] <= son <= CEVIRME_BANT[1]):
            uyar(f"ÇEVİRME ORANI BANT DIŞI: %{son*100:.0f} "
                 f"(bant %{CEVIRME_BANT[0]*100:.0f}–%{CEVIRME_BANT[1]*100:.0f}).")

    # --- stok ayrıştırması: Δstok = net borçlanma + kur farkı + ARTIK ------
    d_stok = M["toplam_borc_trl"].diff(12)
    net_borc = a["borclanma_net"].rolling(12).sum() * BINTL_TRL
    # Kur farkı: geçen yılki DÖVİZ stoku × kurdaki değişim.
    kur_farki = (M["dis_borc_musd"].shift(12) * MUSD_BINTL
                 * (M["kur_ay"] - M["kur_ay"].shift(12)) * BINTL_TRL)
    M["ayr_d_stok"] = d_stok
    M["ayr_net_borclanma"] = net_borc
    M["ayr_kur_farki"] = kur_farki
    M["ayr_artik"] = d_stok - net_borc - kur_farki
    M = M.copy()                   # parçalanma giderilir (159 sütun tek tek eklendi)
    art = (M["ayr_artik"] / d_stok.abs()).dropna()
    if len(art):
        tani["ayrıstirma"] = {
            "artik_pay_son": float(art.iloc[-1]),
            "artik_pay_maks_5y": float(art.tail(60).abs().max()),
            "esik": ARTIK_ESIK,
            "not": ("ARTIK; genel bütçe (GEN41) ile merkezi yönetim stoku "
                    "arasındaki kapsam farkını, dış borcun üç aylık "
                    "adımlanmasını, nakit dışı ihracı ve değerleme etkilerini "
                    "içerir. Toplamı kapatmak için düzeltme YAPILMAZ."),
        }
        if abs(float(art.iloc[-1])) > ARTIK_ESIK:
            uyar(f"AYRIŞTIRMA ARTIĞI BÜYÜK: son gözlemde artık, stok "
                 f"değişiminin %{abs(art.iloc[-1])*100:.0f}'i "
                 f"(eşik %{ARTIK_ESIK*100:.0f}). Kalemler eksik olabilir.")
    return M, tani


# ===========================================================================
# (3) ÜÇ AYLIK — GSYH oranları ve net borç
# ===========================================================================
def ceyrek_metrikleri(c: pd.DataFrame, M: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    tani: dict = {}
    gs = c["gsyh_cari"].dropna()
    # 4 çeyrek TOPLAMI: çeyreklik akım GSYH'yi yıllığa çevirir. Tek çeyreği
    # dörtle çarpmak mevsimselliği (Ç4 şişkin) orana taşırdı.
    gsyh_yil = gs.rolling(4).sum().dropna()
    C = pd.DataFrame(index=gsyh_yil.index)
    C["gsyh_yil_trl"] = gsyh_yil * BINTL_TRL

    for ad, kol in (("denge", "denge_12a"), ("fdd", "fdd_12a"),
                    ("faiz", "faiz_12a"), ("gelir", "gelir_12a"),
                    ("gider", "gider_12a"), ("vergi", "vergi_12a")):
        # BİRİM DENETİMİ: M[kol] 12 aylık birikimli AKIM, trilyon TL;
        # gsyh_yil_trl 4 çeyrek toplamı, trilyon TL. Aynı birim → oran
        # birimsiz. Biri bin TL kalsaydı oran 1e9 katı çıkardı; %3,65'lik
        # faiz/GSYH mertebesi bu kıyasın kanıtıdır.
        q = _ceyrek_sonu(M[kol])
        C[f"{ad}_gsyh"] = q.reindex(C.index) / C["gsyh_yil_trl"] * 100

    stok_q = _ceyrek_sonu(M["toplam_borc_trl"]).reindex(C.index)
    C["stok_trl"] = stok_q
    C["stok_gsyh"] = stok_q / C["gsyh_yil_trl"] * 100

    # --- net borç (finansal hesaplar) -------------------------------------
    for ad, kol in (("net_fin_deger", "fh_net_fin_deger"),
                    ("yukum_toplam", "fh_yukum_toplam"),
                    ("varlik_toplam", "fh_varlik_toplam"),
                    ("nakit", "fh_mevduat"),
                    ("borc_senedi", "fh_borc_senedi"),
                    ("bs_kisa", "fh_bs_kisa"), ("bs_uzun", "fh_bs_uzun"),
                    ("krediler", "fh_krediler")):
        if kol in c.columns:
            C[f"{ad}_trl"] = c[kol].reindex(C.index) * BINTL_TRL
    if "nakit_trl" in C.columns:
        C["net_stok_trl"] = C["stok_trl"] - C["nakit_trl"]
        C["net_stok_gsyh"] = C["net_stok_trl"] / C["gsyh_yil_trl"] * 100
        C["net_fin_deger_gsyh"] = C["net_fin_deger_trl"] / C["gsyh_yil_trl"] * 100

    # --- dış borç bağlamı --------------------------------------------------
    for ad, kol in (("db_toplam", "db_toplam"), ("db_my", "db_merkezi_yon"),
                    ("db_my_kisa", "db_my_kisa"), ("db_my_uzun", "db_my_uzun"),
                    ("db_tcmb", "db_tcmb"), ("db_ozel", "db_ozel")):
        if kol in c.columns:
            C[f"{ad}_mlrusd"] = c[kol].reindex(C.index) * MUSD_MLRUSD

    son_ortak = C[["stok_gsyh"]].dropna()
    tani["son_ortak_ceyrek"] = (f"{son_ortak.index[-1]:%Y-%m-%d}"
                                if len(son_ortak) else None)
    tani["gsyh_son_ceyrek"] = f"{gs.index[-1]:%Y-%m-%d}"
    tani["oran_gecikme_notu"] = (
        "Oran metrikleri EN SON ORTAK ÇEYREKTE biter. GSYH ve finansal "
        "hesaplar akım serilerinden ~2 çeyrek geridedir; GSYH'yi ileri "
        "taşıyıp (ffill) daha yeni bir oran üretmek sessiz bayatlamadır.")
    return C, tani


# ===========================================================================
# (4) HAFTALIK — DİBS sahiplik, vade, eurobond para birimi
# ===========================================================================
def haftalik_metrikleri(h: pd.DataFrame, g: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    H = pd.DataFrame(index=h.index)
    tani: dict = {}

    H["dibs_toplam_trl"] = h["dibs_toplam"] * MNTL_TRL      # milyon TL → trl TL
    # SAHİPLİK PAYLARI — YAZILI değer tablosunun KENDİ toplamına bölünür.
    for ad, kol in (("tcmb", "dibs_tcmb"), ("bankalar", "dibs_bankalar"),
                    ("fonlar", "dibs_fonlar"), ("yurtdisi", "dibs_yurtdisi")):
        H[f"pay_dibs_{ad}"] = h[kol] / h["dibs_toplam"] * 100
    # Diğer yurt içi = S.1 − (TCMB + bankalar + fonlar); artık kalem AÇIKÇA
    # gösterilir, "diğer" adıyla gizlenmez.
    H["pay_dibs_diger_yurtici"] = (
        (h["dibs_yurtici"] - h["dibs_tcmb"] - h["dibs_bankalar"]
         - h["dibs_fonlar"]) / h["dibs_toplam"] * 100)

    # VADE — PİYASA değeri tablosu. Pay, kendi tablosunun toplamına bölünür;
    # yazılı stoka uygulanırsa %22'lik sessiz hata olur.
    H["dibs_pd_trl"] = h["dibs_pd_toplam"] * MNTL_TRL
    H["pay_dibs_kv_kisa"] = (h["dibs_kv_kisa"]
                             / (h["dibs_kv_kisa"] + h["dibs_kv_uzun"]) * 100)
    H["pay_dibs_ov_kisa"] = (h["dibs_ov_kisa"]
                             / (h["dibs_ov_kisa"] + h["dibs_ov_uzun"]) * 100)
    H["dibs_piyasa_yazili_oran"] = h["dibs_pd_toplam"] / h["dibs_toplam"]

    # EUROBOND — yazılı değer (stok) ve piyasa değeri (vade/para tablosu) AYRI.
    H["eb_toplam_mlrusd"] = h["eb_toplam_yaz"] * MUSD_MLRUSD
    H["eb_pd_mlrusd"] = h["eb_toplam_pd"] * MUSD_MLRUSD
    H["pay_eb_yurtdisi"] = h["eb_yurtdisi_yaz"] / h["eb_toplam_yaz"] * 100
    # S1311: merkezi yönetimin KENDİ eurobondunu tutması → konsolidasyonda
    # düşülecek kalem; toplam borca EKLENMEZ, payı ayrı gösterilir.
    H["pay_eb_kendi"] = h["eb_merkezi_yon"] / h["eb_toplam_yaz"] * 100
    for ad, kol in (("usd", "eb_usd_ihrac"), ("eur", "eb_eur_ihrac"),
                    ("jpy", "eb_jpy_ihrac")):
        H[f"pay_eb_{ad}"] = h[kol] / h["eb_toplam_pd"] * 100
    H["pay_eb_kv_kisa"] = (h["eb_kv_kisa"]
                           / (h["eb_kv_kisa"] + h["eb_kv_uzun"]) * 100)

    son = H.dropna(how="all").index[-1]
    tani["son_hafta"] = f"{son:%Y-%m-%d}"
    tani["vade_notu"] = (
        "Ortalama vade EVDS'te YOK. Kısa vade payı (kalan vadesi 1 yıldan az "
        "olanın toplama oranı) VEKİL göstergedir ve öyle etiketlenir. "
        "Vade ve para birimi tabloları PİYASA değeri üzerindendir.")
    tani["sahiplik_notu"] = (
        "Sektör kırılımı İHRAÇÇI değil senedi ELİNDE TUTAN taraftır. Yurt dışı "
        "yerleşik payı ForeignHoldings hattıyla çakışır; burada yalnız borç "
        "stoku bağlamında verilir.")
    tani["eb_toplam_farki"] = {
        "yazili_mlrusd": float(H["eb_toplam_mlrusd"].dropna().iloc[-1]),
        "piyasa_mlrusd": float(H["eb_pd_mlrusd"].dropna().iloc[-1]),
        "not": ("Eurobond para birimi tablosunun toplamı (C8 ≡ piyasa değeri) "
                "yazılı değer toplamından KÜÇÜKTÜR; ikisi birbirinin yerine "
                "kullanılamaz."),
    }
    return H, tani


# ===========================================================================
# (5) KUR DUYARLILIĞI
# ===========================================================================
def kur_senaryolari(M: pd.DataFrame, C: pd.DataFrame, H: pd.DataFrame) -> dict:
    """USD/TRY şoku altında borç stoku ve stok/GSYH.

    İKİ SENARYO AİLESİ:
      · PARALEL: TL bütün dövizlere karşı aynı oranda değer kaybeder. Dış
        bacağın TL karşılığı doğrudan (1+s) ile ölçeklenir.
      · YALNIZ USD: TL yalnız dolara karşı değer kaybeder; EUR/TRY ve JPY/TRY
        sabit kalır. Yalnız dolar cinsi bacak şoklanır.
    Para birimi ağırlıkları EUROBOND tablosundan gelir (USD/EUR/JPY) ve dış
    borç stokunun tamamına VEKİL olarak uygulanır — dış borcun kredi bacağının
    para kompozisyonu EVDS'te ayrı yayımlanmıyor. Bu vekillik açıkça yazılır.

    GSYH SABİT VARSAYILIR (kısa vadeli, nominal). Kur şokunun GSYH deflatörüne
    geçişi bu senaryoda modellenmez; oran bu yüzden ÜST SINIR okunmalıdır.
    """
    stok = M[["ic_borc_trl", "dis_borc_trl", "toplam_borc_trl", "kur_ay"]].dropna()
    if stok.empty:
        return {}
    t = stok.index[-1]
    ic = float(stok["ic_borc_trl"].iloc[-1])
    dis = float(stok["dis_borc_trl"].iloc[-1])
    kur = float(stok["kur_ay"].iloc[-1])

    agirlik = {"usd": float(H["pay_eb_usd"].dropna().iloc[-1]) / 100,
               "eur": float(H["pay_eb_eur"].dropna().iloc[-1]) / 100,
               "jpy": float(H["pay_eb_jpy"].dropna().iloc[-1]) / 100}

    # Oran bacağı: stok ve GSYH'nin SON ORTAK çeyreği. Stokun son ayı ile
    # GSYH'nin son çeyreğini karıştırmak oranı sahte biçimde tazeler.
    ortak = C[["stok_trl", "gsyh_yil_trl"]].dropna()
    q = ortak.index[-1] if len(ortak) else None
    stok_q = float(ortak["stok_trl"].iloc[-1]) if q is not None else None
    gsyh_q = float(ortak["gsyh_yil_trl"].iloc[-1]) if q is not None else None
    # Çeyrek anındaki iç/dış ayrımı (şok yalnız dış bacağa uygulanır)
    dis_q = float(_ceyrek_sonu(M["dis_borc_trl"]).reindex([q]).iloc[0]) \
        if q is not None else None

    satirlar = []
    for s in KUR_SOKLARI:
        dis_par = dis * (1 + s)
        dis_usd = dis * (1 + s * agirlik["usd"])
        satir = {
            "sok": s,
            "kur": kur * (1 + s),
            "stok_paralel_trl": ic + dis_par,
            "stok_yalniz_usd_trl": ic + dis_usd,
            "degisim_paralel_yuzde": (ic + dis_par) / (ic + dis) * 100 - 100,
            "degisim_yalniz_usd_yuzde": (ic + dis_usd) / (ic + dis) * 100 - 100,
        }
        if q is not None and gsyh_q:
            satir["stok_gsyh_paralel"] = (stok_q + dis_q * s) / gsyh_q * 100
            satir["stok_gsyh_yalniz_usd"] = (
                (stok_q + dis_q * s * agirlik["usd"]) / gsyh_q * 100)
        satirlar.append(satir)

    return {
        "cipa_ay": t.strftime("%Y-%m"),
        "cipa_ceyrek": f"{q:%Y-%m-%d}" if q is not None else None,
        "kur": kur, "ic_trl": ic, "dis_trl": dis, "toplam_trl": ic + dis,
        "agirlik": agirlik,
        "satirlar": satirlar,
        "not": ("Para birimi ağırlıkları eurobond tablosundan alınıp dış borç "
                "stokunun tamamına VEKİL olarak uygulanmıştır; dış borcun "
                "kredi bacağının para kompozisyonu EVDS'te yayımlanmıyor. "
                "GSYH sabit varsayılmıştır — oran ÜST SINIR okunmalıdır."),
    }


# ===========================================================================
# (6) BAĞIMSIZ DOĞRULAMA
# ===========================================================================
def dogrula(c: pd.DataFrame, h: pd.DataFrame, g: pd.DataFrame,
            C: pd.DataFrame) -> dict:
    """Türetilmiş büyüklükleri EVDS'in kendi yayımladıklarıyla kıyaslar."""
    D: dict = {}

    # DİBS (yazılı, milyon TL) + eurobond (yazılı, milyon USD × kur) ↔ F.3.
    # ÖZDEŞ DEĞİL, BANTLI: finansal hesaplar piyasa değerli ve kapsamı biraz
    # geniş (genel yönetim ↔ merkezi yönetim, kira sertifikaları vb.).
    # Ölçülen fark son çeyreklerde −%7…−%12. Sıfıra zorlayan düzeltme YAPILMAZ.
    if "borc_senedi_trl" in C.columns:
        kur_h = g["usdtry"].dropna()
        dibs_trl = h["dibs_toplam"].dropna() * MNTL_TRL
        eb_trl = (h["eb_toplam_yaz"].dropna() * MUSD_BINTL
                  * kur_h.reindex(h.index).ffill() * BINTL_TRL).dropna()
        senet = (dibs_trl + eb_trl).dropna()
        # Haftalık seriden çeyrek sonuna en yakın gözlem (asof)
        x = []
        for q in C.index:
            v = senet.asof(q)
            f3 = C["borc_senedi_trl"].get(q)
            if pd.notna(v) and pd.notna(f3) and f3:
                x.append((q, float(v), float(f3), float(v) / float(f3) - 1))
        if x:
            son6 = x[-6:]
            farklar = [r[3] for r in son6]
            gecti = all(F3_BANT[0] <= f <= F3_BANT[1] for f in farklar)
            D["DİBS+eurobond ↔ finansal hesaplar F.3"] = {
                "n": len(x), "son_ceyrek": f"{son6[-1][0]:%Y-%m-%d}",
                "elde_trl": son6[-1][1], "f3_trl": son6[-1][2],
                "son_fark": son6[-1][3],
                "son6_min": min(farklar), "son6_max": max(farklar),
                "bant": list(F3_BANT), "gecti": bool(gecti),
                "aciklama": ("Özdeşlik BEKLENMEZ: finansal hesaplar piyasa "
                             "değerli ve kapsamı geniş. Bant denetlenir."),
            }
            if not gecti:
                uyar("DOĞRULAMA: DİBS+eurobond toplamı ile finansal hesapların "
                     f"F.3 kalemi arasındaki fark bant dışına çıktı "
                     f"({min(farklar):+.1%}…{max(farklar):+.1%}, bant "
                     f"{F3_BANT[0]:+.0%}…{F3_BANT[1]:+.0%}).")

    # Dış borç: merkezi yönetim ≤ genel hükümet ≤ kamu ≤ toplam (hiyerarşi)
    kol = ["db_merkezi_yon", "db_genel_hukumet", "db_kamu", "db_toplam"]
    if set(kol) <= set(c.columns):
        x = c[kol].dropna()
        ihlal = int(((x["db_merkezi_yon"] > x["db_genel_hukumet"] + 1)
                     | (x["db_genel_hukumet"] > x["db_kamu"] + 1)
                     | (x["db_kamu"] > x["db_toplam"] + 1)).sum())
        D["Dış borç hiyerarşisi"] = {
            "n": int(len(x)), "ihlal": ihlal, "gecti": ihlal == 0,
            "aciklama": "MY ≤ genel hükümet ≤ kamu ≤ toplam olmalı."}
        if ihlal:
            uyar(f"DOĞRULAMA: dış borç hiyerarşisi {ihlal} çeyrekte ihlal "
                 "edildi — seri eşlemesi değişmiş olabilir.")

    # Eurobond para birimi kırılımı toplamı ≈ piyasa değeri toplamı
    if {"eb_usd_ihrac", "eb_eur_ihrac", "eb_jpy_ihrac", "eb_toplam_pd"} <= set(h.columns):
        x = h[["eb_usd_ihrac", "eb_eur_ihrac", "eb_jpy_ihrac", "eb_toplam_pd"]].dropna()
        if len(x):
            kalan = (x["eb_toplam_pd"]
                     - x[["eb_usd_ihrac", "eb_eur_ihrac", "eb_jpy_ihrac"]].sum(axis=1))
            pay = float((kalan / x["eb_toplam_pd"]).abs().max())
            D["Eurobond para birimi toplamı"] = {
                "n": int(len(x)), "maks_artik_pay": pay,
                "gecti": bool(pay < 0.02),
                "aciklama": "USD+EUR+JPY, piyasa değeri toplamını vermeli."}
            if pay >= 0.02:
                uyar("DOĞRULAMA: eurobond para birimi kırılımı toplamı "
                     f"tutmuyor (artık payı %{pay*100:.1f}).")
    return D


# ===========================================================================
def kos() -> int:
    a = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    c = pd.read_csv(VERI / "ceyreklik.csv", index_col=0, parse_dates=True)
    h = pd.read_csv(VERI / "haftalik.csv", index_col=0, parse_dates=True)
    g = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)

    s_ay = veri.son_ay(a)
    s_ceyrek = veri.son_ceyrek(c)
    s_dis = veri.son_dis_ceyrek(c)
    s_hafta = veri.son_hafta(h)
    s_gun = veri.son_gun(g)
    print(f"Merkezi yönetim bütçesi & borç stoku — metrik · bütçe {ay_ad(s_ay)}")

    # VERİ KATMANININ UYARILARI BURADA DEVRALINIR. Devralınmazsa tazelik ve
    # "ESKİ ÖNBELLEK" uyarıları uyarilar.json'a hiç girmez ve sayfada GÖRÜNMEZ
    # — düzenin yasakladığı sessiz bayatlama.
    devir: list[str] = list(veri.uyarilar())
    try:
        durum = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
        devir += list(durum.get("uyarilar") or [])
    except Exception as ex:
        uyar(f"veri_durum.json okunamadı ({ex}) — veri katmanının uyarıları "
             "devralınamadı. Tazelik uyarıları bu koşuda GÖRÜNMEYEBİLİR.")
        durum = {}
    for u in devir:
        if u not in _UYARI:
            _UYARI.append(u)
            print("  ! (veri) " + u, flush=True)

    M, t_butce = butce_metrikleri(a, s_ay)
    M, t_stok = stok_metrikleri(a, c, g, M)
    C, t_ceyrek = ceyrek_metrikleri(c, M)
    H, t_hafta = haftalik_metrikleri(h, g)
    senaryo = kur_senaryolari(M, C, H)
    D = dogrula(c, h, g, C)

    M.to_csv(VERI / "aylik_metrik.csv")
    C.to_csv(VERI / "ceyreklik_metrik.csv")
    H.to_csv(VERI / "haftalik_metrik.csv")

    ozet = {
        "son_ay": s_ay.strftime("%Y-%m-%d"),
        "son_ceyrek": s_ceyrek.strftime("%Y-%m-%d"),
        "son_dis_ceyrek": s_dis.strftime("%Y-%m-%d"),
        "son_hafta": s_hafta.strftime("%Y-%m-%d"),
        "son_gun": s_gun.strftime("%Y-%m-%d"),
        "esik": {
            "f3_bant": list(F3_BANT), "kapsam_esik": KAPSAM_ESIK,
            "artik_esik": ARTIK_ESIK, "cevirme_bant": list(CEVIRME_BANT),
            "kur_soklari": KUR_SOKLARI,
        },
        "butce": t_butce, "stok": t_stok, "ceyrek": t_ceyrek,
        "haftalik": t_hafta, "senaryo": senaryo, "dogrulama": D,
        "kapsam_notu": (
            "Bu hat borç STOKUNU ve BÜTÇEYİ anlatır. İhale tarafı (teklif, "
            "karşılama, kesim faizi) Hazine İhraç hattındadır; iki sayfa "
            "birbirine referans verir, sayı tekrarlanmaz."),
        "eksik_veri_notu": (
            "Merkezi yönetim borç stokunun SABİT / DEĞİŞKEN / TÜFE'ye endeksli "
            "kırılımı ve ORTALAMA VADESİ EVDS'te YOK (675 veri grubu tarandı). "
            "Bu üç kalem sayfada uydurma vekille doldurulmaz."),
        "uyarilar": list(_UYARI),
    }
    (VERI / "metrik_ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1, default=float),
        encoding="utf-8")
    (PROJE / "uyarilar.json").write_text(json.dumps(
        {"tarih": s_ay.strftime("%Y-%m-%d"),
         "kosum": pd.Timestamp.today().strftime("%Y-%m-%d"),
         "uyarilar": list(_UYARI), "dogrulama": D},
        ensure_ascii=False, indent=1, default=float), encoding="utf-8")

    print(f"  yazıldı: data/aylik_metrik.csv ({M.shape[0]}x{M.shape[1]}), "
          f"ceyreklik_metrik.csv ({C.shape[0]}x{C.shape[1]}), "
          f"haftalik_metrik.csv ({H.shape[0]}x{H.shape[1]})")
    print(f"  dönem: bütçe {ay_ad(s_ay)} · GSYH {ceyrek_ad(s_ceyrek)} · "
          f"dış borç {ceyrek_ad(s_dis)} · menkul {gun_ad(s_hafta)} · "
          f"kur {gun_ad(s_gun)}")
    for ad, r in D.items():
        print(f"    doğrulama {'✓' if r.get('gecti') else '✗'} {ad} (n={r.get('n')})")
    if _UYARI:
        print(f"\n[{len(_UYARI)} uyarı]")
    return 0


if __name__ == "__main__":
    raise SystemExit(kos())
