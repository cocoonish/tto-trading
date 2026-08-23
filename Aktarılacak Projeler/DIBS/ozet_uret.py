# -*- coding: utf-8 -*-
"""DİBS verim eğrisi & reel faiz — ozet.json üretimi.

Sayfa metnindeki OYNAK her sayı buradan beslenir (CLAUDE.md kural 5):
MDX'te `<Deger proje="dibs-verim-egrisi" anahtar="..." ondalik={2}>yedek</Deger>`.
Tarihsel/metodolojik sabitler (formüller, kurum tanımları, doğrulama örnekleri)
sayfada STATİK kalır — onlar veri tazelendikçe değişmez.

Bütün değerler data/ altındaki ÜRETİLMİŞ dosyalardan okunur; elle sayı
yazılmaz. Bir değer kaynakta yoksa anahtar ATLANIR ve stderr'e uyarı basılır —
MDX'teki statik yedek görünür, ama sessizce yanlış bir sayı basılmaz.

İKİ FREKANS: eğri GÜNLÜK, beklenti/enflasyon AYLIKTIR. Bu yüzden iki çıpa
tarihi taşınır: `_tarih` (eğri) ve `_tarih2` (anket ayı).

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from veri import PROJE, VERI, AY_TR, gun_ad, ay_ad, tazelik_tolerans

O: dict = {}

# Bir "anlık" değerin ÇIPA GÜNÜNE ait sayılması için izin verilen en büyük
# gecikme (takvim günü). Reel/başabaş düğümler kimi gün kurulamıyor (vade
# boşluğu); iki ay eski bir başabaş oranını bugünün sayılarının yanına
# koymak yanıltıcı olurdu — o anahtar ATLANIR.
ANLIK_TOLERANS_GUN = 7


def uyar(m: str) -> None:
    print(f"UYARI: {m}", file=sys.stderr)


def tr_sayi(v, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi (binlik nokta, ondalık virgül, eksi U+2212).

    ozet.json'daki METİN anahtarları sayfaya olduğu gibi basılır; Python'un
    varsayılan biçimi oraya "0.0" ve "-3.18" gibi İngilizce yazımlar taşırdı.
    """
    if v is None:
        return "—"
    try:
        m = f"{float(v):,.{ondalik}f}"
    except (TypeError, ValueError):
        return str(v)
    return (m.replace(",", " ").replace(".", ",").replace(" ", ".")
             .replace("-", "−"))


def koy(anahtar: str, deger, ondalik: int | None = 2) -> None:
    if deger is None or (isinstance(deger, float) and (pd.isna(deger)
                                                       or not np.isfinite(deger))):
        uyar(f"'{anahtar}' kaynakta yok — anahtar atlandı.")
        return
    if ondalik is None:
        O[anahtar] = deger
    elif ondalik == 0:
        O[anahtar] = int(round(float(deger)))
    else:
        O[anahtar] = round(float(deger), ondalik)


def tr_tarih(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day:02d}.{t.month:02d}.{t.year}"


def main() -> int:
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))
    M = pd.read_csv(VERI / "metrik.csv", index_col=0, parse_dates=True)
    KE = pd.read_csv(VERI / "kesit_egri.csv")
    yol_r = VERI / "kesit_reel.csv"
    KR = pd.read_csv(yol_r) if yol_r.exists() else None

    s_gun = pd.Timestamp(m["son_gun"])
    s_ay = pd.Timestamp(m["son_ay"]) if m.get("son_ay") else None
    bugun = pd.Timestamp.today().normalize()
    a = m["anlik"]

    # --- dönem çıpaları ----------------------------------------------------
    O["_tarih"] = tr_tarih(s_gun)                    # GÜNLÜK bacak (eğri)
    if s_ay is not None:
        O["_tarih2"] = f"{s_ay.year}-{s_ay.month:02d}"   # AYLIK bacak (anket)
        O["anket_ay"] = ay_ad(s_ay)
    O["gun"] = gun_ad(s_gun)
    O["gun_kisa"] = tr_tarih(s_gun)
    O["ay_ad"] = AY_TR[s_gun.month]
    O["yil"] = int(s_gun.year)
    O["kosum_tarihi"] = tr_tarih(bugun)
    koy("yayim_gecikme_gun", (bugun - s_gun).days, 0)
    if s_ay is not None:
        # Gecikme ay SONUNDAN değil VARSAYILAN YAYIM GÜNÜNDEN ölçülür: PKA ayın
        # ikinci yarısında açıklanıyor, ay sonu referansı içinde bulunduğumuz
        # ayın anketini "henüz gelmemiş" gösterip eksi gün üretiyordu.
        yayim = s_ay.replace(day=min(m["esik"]["pka_yayim_gun"], s_ay.days_in_month))
        koy("anket_gecikme_gun", max(0, (bugun - yayim).days), 0)
        O["anket_varsayilan_yayim"] = tr_tarih(yayim)

    # --- eğri düğümleri ----------------------------------------------------
    # Her anahtar KENDİ son dolu gününden okunur; çıpadan uzaksa atlanır.
    def anlik(kaynak_ad: str, hedef_ad: str, ondalik: int = 2,
              tolerans: int = ANLIK_TOLERANS_GUN) -> bool:
        v = a.get(kaynak_ad)
        t = a.get(kaynak_ad + "_tarih")
        if v is None or t is None:
            uyar(f"'{hedef_ad}' ({kaynak_ad}) metrik özetinde yok — atlandı.")
            return False
        yas = (s_gun - pd.Timestamp(t)).days
        if yas > tolerans:
            uyar(f"'{hedef_ad}' ({kaynak_ad}) son dolu günü {t}, çıpadan {yas} "
                 "gün geride — anahtar ATLANDI (bayat sayı basılmasın).")
            return False
        koy(hedef_ad, v, ondalik)
        O[hedef_ad + "_tarih"] = tr_tarih(t)
        return True

    for kaynak, hedef in (
            ("n3a", "spot_3a"), ("n6a", "spot_6a"), ("n1y", "spot_1y"),
            ("n2y", "spot_2y"), ("n3y", "spot_3y"), ("n5y", "spot_5y"),
            ("n7y", "spot_7y"), ("n9y", "spot_9y"), ("par2y", "par_2y")):
        anlik(kaynak, hedef)
    for kaynak, hedef in (
            ("egim_2y9y", "egim_2y9y"), ("egim_2y5y", "egim_2y5y"),
            ("egim_2y3a", "egim_2y3a"), ("kelebek_1_2_5", "kelebek_1_2_5"),
            ("kelebek_2_5_9", "kelebek_2_5_9"),
            ("f_1y1y", "forward_1y1y"), ("f_2y1y", "forward_2y1y"),
            ("f_2y3y", "forward_2y3y"),
            ("carry_2y_tlref", "carry_2y_tlref"),
            ("carry_2y_politika", "carry_2y_politika"),
            ("carry_2y_aofm", "carry_2y_aofm"),
            ("carry_3a_tlref", "carry_3a_tlref")):
        anlik(kaynak, hedef)

    # --- referans faizler --------------------------------------------------
    for kaynak, hedef in (("tlref", "tlref"), ("politika", "politika"),
                          ("aofm", "aofm"), ("koridor_alt", "koridor_alt"),
                          ("koridor_ust", "koridor_ust")):
        anlik(kaynak, hedef)

    # --- beklenti / enflasyon (AYLIK bacak; toleransı ay ritmine göre geniş)
    for kaynak, hedef in (("pka_12a", "pka_12a"), ("pka_24a", "pka_24a"),
                          ("pka_5y", "pka_5y"),
                          ("pka_faiz_12a", "pka_faiz_12a"),
                          ("pka_faiz_24a", "pka_faiz_24a"),
                          ("tufe_yillik", "tufe_yillik"),
                          ("pka_12a_n", "pka_katilimci")):
        anlik(kaynak, hedef, ondalik=0 if kaynak == "pka_12a_n" else 2,
              tolerans=45)

    # Aylık kökenli anahtarların "_tarih" alanı yukarıda GÜNLÜK çıpayı
    # gösteriyordu (seri günlüğe basamak olarak yayıldığı için). Bu yanıltıcı:
    # 23,69 sayısı 21.08.2026 günü GEÇERLİDİR ama Ağustos 2026 ANKETİNDEN gelir.
    # Tarih alanları kaynak aya çevrilir.
    A = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    for hedef, kaynak_kol in (("pka_12a", "pka_12a"), ("pka_24a", "pka_24a"),
                              ("pka_5y", "pka_5y"),
                              ("pka_faiz_12a", "pka_faiz_12a"),
                              ("pka_faiz_24a", "pka_faiz_24a"),
                              ("pka_katilimci", "pka_12a_n"),
                              ("tufe_yillik", "tufe_2025")):
        if hedef not in O or kaynak_kol not in A.columns:
            continue
        s = A[kaynak_kol].dropna()
        if s.empty:
            continue
        O[hedef + "_tarih"] = ay_ad(s.index[-1])
    if "tufe_2025" in A.columns and A["tufe_2025"].notna().any():
        O["tufe_ay"] = ay_ad(A["tufe_2025"].dropna().index[-1])

    # --- REEL FAİZ (Fisher) ------------------------------------------------
    anlik("reel_ileri", "reel_ileri")
    anlik("reel_geriye", "reel_geriye")
    anlik("reel_ileri_2y", "reel_ileri_2y")
    anlik("reel_ileri_basit", "reel_ileri_basit")
    anlik("fisher_basit_fark", "fisher_basit_fark")
    anlik("reel_makas", "reel_makas")
    # Fisher dersinin cümlesi de sayıdan TÜRETİLİR: yöntem farkının işareti
    # enflasyon seviyesiyle döner, elle yazılmış bir cümle yanlışa düşer.
    if "fisher_basit_fark" in O and "reel_ileri" in O:
        f = O["fisher_basit_fark"]
        O["fisher_cumlesi"] = (
            f"Basit çıkarma reel faizi {tr_sayi(abs(f), 2)} puan "
            + ("YÜKSEK" if f > 0 else "DÜŞÜK") + " gösteriyor: "
            f"%{tr_sayi(O.get('reel_ileri_basit'), 2)} yerine Fisher "
            f"%{tr_sayi(O['reel_ileri'], 2)} veriyor.")

    # --- TÜFEX reel eğri ve başabaş ---------------------------------------
    for kaynak, hedef in (("r1y", "reel_egri_1y"), ("r2y", "reel_egri_2y"),
                          ("r3y", "reel_egri_3y"), ("r5y", "reel_egri_5y"),
                          ("r7y", "reel_egri_7y")):
        anlik(kaynak, hedef)
    basabas_var = []
    for kaynak, hedef, etiket in (("be_1y", "basabas_1y", "1 yıl"),
                                  ("be_2y", "basabas_2y", "2 yıl"),
                                  ("be_3y", "basabas_3y", "3 yıl"),
                                  ("be_5y", "basabas_5y", "5 yıl"),
                                  ("be_7y", "basabas_7y", "7 yıl")):
        if anlik(kaynak, hedef):
            basabas_var.append(etiket)
    O["basabas_vadeler"] = ", ".join(basabas_var) if basabas_var else "—"
    for kaynak, hedef in (("prim_1y", "risk_primi_1y"),
                          ("prim_2y", "risk_primi_2y"),
                          ("prim_5y", "risk_primi_5y")):
        anlik(kaynak, hedef)
    if KR is not None and not KR.empty:
        koy("tufex_nokta", len(KR), 0)
        koy("tufex_vade_min", float(KR["vade_yil"].min()), 2)
        koy("tufex_vade_maks", float(KR["vade_yil"].max()), 2)
        koy("tufex_reel_min", float(KR["reel_getiri"].min()), 2)
        koy("tufex_reel_maks", float(KR["reel_getiri"].max()), 2)
        kisa = KR[KR["vade_yil"] <= 3.0]["reel_getiri"]
        uzun = KR[KR["vade_yil"] > 3.0]["reel_getiri"]
        if len(kisa) > 1:
            koy("tufex_kisa_sacilma", float(kisa.max() - kisa.min()), 2)
            koy("tufex_kisa_alt", float(kisa.min()), 2)
            koy("tufex_kisa_ust", float(kisa.max()), 2)
        if len(uzun) > 1:
            koy("tufex_uzun_sacilma", float(uzun.max() - uzun.min()), 2)
            koy("tufex_uzun_alt", float(uzun.min()), 2)
            koy("tufex_uzun_ust", float(uzun.max()), 2)
    zin = m.get("tufe_zinciri") or {}
    koy("tufe_zincir_kat", zin.get("kat"), 4)
    if zin.get("ortusme_ay"):
        O["tufe_zincir_ay"] = tr_tarih(zin["ortusme_ay"])

    # --- eğri kesiti / kapsama --------------------------------------------
    kap = m["kapsama"]
    koy("nokta_sayisi", kap["nokta_son"], 0)
    koy("nokta_medyan", kap["nokta_medyan"], 0)
    koy("vade_min", float(M.loc[s_gun, "vade_min"]), 2)
    koy("vade_maks", float(M.loc[s_gun, "vade_maks"]), 2)
    koy("gun_sayisi", kap["gun_sayisi"], 0)
    O["tarihce_bas"] = tr_tarih(kap["ilk_gun"])
    bugun_kesit = KE[KE["kesit"] == "bugun"]
    koy("kesit_anapara", int((bugun_kesit["strip"] == "anapara").sum()), 0)
    koy("kesit_kupon", int((bugun_kesit["strip"] == "kupon").sum()), 0)
    O["reel_kapsama_notu"] = kap.get("reel_notu", "")
    for ad, alan in (("dugum_9y_dolu", "n9y"), ("dugum_7y_dolu", "n7y")):
        koy(ad, kap["dugum_dolu"].get(alan), 0)
    koy("dugum_9y_pay", (kap["dugum_dolu"].get("n9y", 0) / kap["gun_sayisi"]) * 100, 1)

    # --- evren -------------------------------------------------------------
    ev = m.get("evren") or {}
    for ad, alan in (("evren_kiymet", "toplam_kiymet"),
                     ("evren_nominal", "nominal_sifir_kuponlu"),
                     ("evren_tufex", "tufex_anapara"),
                     ("evren_tahvil", "aktif_kuponlu_tahvil"),
                     ("evren_degisken_atilan", "degisken_kupon_atilan"),
                     ("evren_oransiz_kupon", "kupon_oran_kardesi_yok")):
        koy(ad, ev.get(alan), 0)
    koy("getiri_araligi_disi", m.get("getiri_araligi_disi"), 0)

    # --- kimlik denetimi ---------------------------------------------------
    kim = m["kimlik"]
    koy("kimlik_medyan_sapma", kim.get("medyan_son"), 4)
    koy("kimlik_medyan_tarihce", kim.get("medyan_medyan"), 4)
    koy("kimlik_maks_sapma", kim.get("maks_maks"), 3)
    if kim.get("maks_tarih"):
        O["kimlik_maks_tarih"] = tr_tarih(kim["maks_tarih"])
    koy("kimlik_cok_kaynakli", kim.get("cok_kaynakli_vade_son"), 0)
    koy("kimlik_esik_medyan", kim.get("esik_medyan"), 2)
    koy("kimlik_esik_maks", kim.get("esik_maks"), 1)
    O["kimlik_gecti"] = bool(kim.get("gecti"))

    # --- YTM çapraz sınaması ----------------------------------------------
    ytm = m.get("ytm_sinamasi") or {}
    if ytm:
        koy("ytm_n", ytm.get("n"), 0)
        koy("ytm_medyan_fark", ytm.get("medyan_fark_puan"), 4)
        koy("ytm_maks_fark", ytm.get("maks_fark_puan"), 3)
        koy("ytm_medyan_fiyat_fark", ytm.get("medyan_fiyat_fark"), 3)
        # Gösterge tahvile en yakın vadeli kıymet: sayfada "gösterge 2 yıllık"
        # cümlesi buna bağlanır.
        tablo = ytm.get("tablo") or []
        if tablo:
            en_yakin = min(tablo, key=lambda r: abs(r["vade_yil"] - 2.0))
            koy("gosterge_ytm", en_yakin["piyasa_ytm"], 2)
            koy("gosterge_vade", en_yakin["vade_yil"], 2)
            O["gosterge_itfa"] = tr_tarih(en_yakin["itfa"])
            koy("gosterge_fiyat", en_yakin["piyasa_fiyat"], 3)
            koy("gosterge_model_ytm", en_yakin["model_ytm"], 2)
            koy("gosterge_nakit_akisi", en_yakin["nakit_akisi_n"], 0)

    # --- ana bileşenler ----------------------------------------------------
    pca = m.get("pca") or {}
    pay = pca.get("aciklanan_pay") or []
    for i, p in enumerate(pay[:3], start=1):
        koy(f"pca_pay_pc{i}", p * 100, 1)
    koy("pca_pay_toplam", (pca.get("toplam_pay_3") or 0) * 100, 1)
    koy("pca_gun", pca.get("n_gun"), 0)
    O["pca_dugum"] = ", ".join(pca.get("dugum") or [])
    for ad, kol in (("pc1", "pc1"), ("pc2", "pc2"), ("pc3", "pc3")):
        if kol in M.columns and M[kol].notna().any():
            koy(f"{ad}_son", float(M[kol].dropna().iloc[-1]), 2)

    # --- eşikler (sayfadaki "en az … " cümleleri buradan okur) -------------
    e = m["esik"]
    koy("esik_min_gun", e["min_gun"], 0)
    koy("esik_min_nokta", e["gun_min_nokta"], 0)
    koy("esik_pka_yayim_gun", e["pka_yayim_gun"], 0)
    koy("esik_tufe_yayim_gecikme", e["tufe_yayim_gecikme"], 0)

    # --- kıyas günleri -----------------------------------------------------
    kiyas = m.get("kiyas_gunleri") or {}
    for ad, etiket in (("1ay", "kiyas_1ay"), ("3ay", "kiyas_3ay"),
                       ("1yil", "kiyas_1yil")):
        if ad in kiyas:
            O[etiket] = tr_tarih(kiyas[ad])
            g = pd.Timestamp(kiyas[ad])
            for kol, sonek in (("n2y", "2y"), ("n1y", "1y"), ("n9y", "9y")):
                if g in M.index and np.isfinite(M.loc[g, kol]):
                    koy(f"{etiket}_{sonek}", float(M.loc[g, kol]), 2)
                    koy(f"{etiket}_{sonek}_degisim_bp",
                        (float(M.loc[s_gun, kol]) - float(M.loc[g, kol])) * 100, 0)

    # --- ters eğri / rejim tanısı -----------------------------------------
    egim = M["egim_2y9y"].dropna()
    if len(egim):
        ters = egim < 0
        koy("ters_egri_gun", int(ters.sum()), 0)
        koy("ters_egri_pay", float(ters.mean() * 100), 1)
        O["egri_ters_mi"] = bool(ters.iloc[-1])
        if ters.any():
            O["ters_egri_son"] = tr_tarih(egim.index[ters][-1])
        # Kesintisiz süren güncel ters eğri dönemi kaç iş günü?
        if ters.iloc[-1]:
            n = 0
            for v in ters.iloc[::-1]:
                if not v:
                    break
                n += 1
            koy("ters_egri_suren_gun", n, 0)
    car = M["carry_2y_aofm"].dropna()
    if len(car):
        koy("carry_negatif_gun", int((car < 0).sum()), 0)
        koy("carry_negatif_pay", float((car < 0).mean() * 100), 1)
        O["carry_pozitif_mi"] = bool(car.iloc[-1] > 0)
    O["carry_cumlesi"] = (
        f"2 yıllık spot getiri fonlama maliyetinin {tr_sayi(abs(O.get('carry_2y_aofm', 0)), 2)} "
        + ("PUAN ÜSTÜNDE — taşıma pozitif" if O.get("carry_pozitif_mi")
           else "PUAN ALTINDA — taşıma negatif, pozisyon ancak faiz inişi "
                "beklentisiyle tutulur") + ".")
    O["egim_cumlesi"] = (
        "Eğri TERS: 2 yıllık getiri 9 yıllıktan "
        f"{tr_sayi(abs(O.get('egim_2y9y', 0)), 2)} puan yüksek."
        if O.get("egri_ters_mi") else
        "Eğri NORMAL (yukarı eğimli): 9 yıllık getiri 2 yıllıktan "
        f"{tr_sayi(abs(O.get('egim_2y9y', 0)), 2)} puan yüksek.")
    O["reel_faiz_cumlesi"] = (
        f"Fisher ileri reel faiz %{tr_sayi(O.get('reel_ileri'), 2)}, geriye "
        f"dönük %{tr_sayi(O.get('reel_geriye'), 2)}; makas "
        f"{tr_sayi(O.get('reel_makas'), 2)} puan.")
    if "risk_primi_5y" in O and "basabas_5y" in O and "pka_5y" in O:
        O["basabas_cumlesi"] = (
            f"5 yıllık başabaş enflasyon %{tr_sayi(O['basabas_5y'], 1)}, aynı "
            f"vadede anket beklentisi %{tr_sayi(O['pka_5y'], 1)}: "
            f"{tr_sayi(O['risk_primi_5y'], 1)} puanlık fark risk primi, "
            "likidite primi ve TÜFE ölçümüne güvensizliğin karışımıdır — "
            "'piyasanın enflasyon beklentisi' DEĞİLDİR.")

    # --- uyarılar ----------------------------------------------------------
    uyarilar = list(uy.get("uyarilar", []))
    # SON SAVUNMA: uyarilar.json bir önceki koşudan kalmış ya da metrik katmanı
    # devralmayı atlamış olabilir; veri_durum.json burada da okunur.
    for u in (vd.get("uyarilar") or []):
        if u not in uyarilar:
            uyarilar.append(u)

    # --- TAZELİK BAYRAĞI ---------------------------------------------------
    tol_gun = tazelik_tolerans("gunluk")
    tol_ay = tazelik_tolerans("aylik")
    bayat_sebep: list[str] = []
    if (O.get("yayim_gecikme_gun") or 0) > tol_gun:
        bayat_sebep.append(f"eğri bacağı {O['yayim_gecikme_gun']} gün geride "
                           f"(tolerans {tol_gun} gün)")
    if (O.get("anket_gecikme_gun") or 0) > tol_ay:
        bayat_sebep.append(f"anket bacağı {O['anket_gecikme_gun']} gün geride "
                           f"(tolerans {tol_ay} gün)")
    izler = [u for u in uyarilar
             if u.startswith(("TAZELİK", "ESKİ ÖNBELLEK", "BAYAT", "SERİ YOK"))]
    if izler:
        bayat_sebep.append(f"veri katmanı {len(izler)} tazelik/önbellek uyarısı bastı")
    O["bayat"] = bool(bayat_sebep)
    O["bayat_tolerans_gun"] = tol_gun
    O["bayat_tolerans_ay"] = tol_ay
    O["bayat_cumlesi"] = (
        "BAYAT VERİ: " + "; ".join(bayat_sebep)
        + ". Sayfadaki sayılar bu koşuda İLERLEMEMİŞ olabilir."
        if bayat_sebep else
        "Veri taze: yayım gecikmesi tolerans içinde, tazelik uyarısı yok.")

    O["uyari_sayisi"] = len(uyarilar)
    O["uyari_metni"] = ((O["bayat_cumlesi"] + " · " if O["bayat"] else "")
                        + (" · ".join(uyarilar) if uyarilar
                           else "Bu koşuda uyarı yok."))
    O["uyari_cumlesi"] = (
        "Bu koşuda uyarı düşmedi." if not uyarilar else
        "Bu koşuda düşen tek uyarı budur:" if len(uyarilar) == 1 else
        f"Bu koşuda {len(uyarilar)} uyarı düştü:")

    # --- metodoloji notları (sayfaya olduğu gibi basılabilir) --------------
    for ad, metin in (m.get("notlar") or {}).items():
        O[f"not_{ad}"] = metin

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · eğri {O['gun']} "
          f"({O['yayim_gecikme_gun']} gün önce)"
          + (f" · anket {O.get('anket_ay')}" if O.get("anket_ay") else "")
          + ("  ! BAYAT" if O.get("bayat") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
