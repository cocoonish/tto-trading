# -*- coding: utf-8 -*-
"""TCMB fonlama & likidite — ozet.json üretimi.

Sayfa metnindeki OYNAK her sayı buradan beslenir (CLAUDE.md kural 5):
MDX'te `<Deger proje="fonlama-likidite" anahtar="..." ondalik={1}>yedek</Deger>`.
Tarihsel/metodolojik sabitler (formüller, kurum tanımları, 2017–18 vaka
sayıları) sayfada STATİK kalır — onlar veri tazelendikçe değişmez.

Bütün değerler data/ altındaki ÜRETİLMİŞ dosyalardan okunur; elle sayı
yazılmaz. Bir değer kaynakta yoksa anahtar ATLANIR ve stderr'e uyarı basılır —
MDX'teki statik yedek görünür, ama sessizce yanlış bir sayı basılmaz.

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from veri import PROJE, VERI, AY_TR, gun_ad, tazelik_tolerans

O: dict = {}


def uyar(m: str) -> None:
    print(f"UYARI: {m}", file=sys.stderr)


def tr_sayi(v, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi (binlik nokta, ondalık virgül).

    ozet.json'daki METİN anahtarları (kapsam/uyarı cümleleri) sayfaya olduğu
    gibi basılır; Python'un varsayılan `repr`i oraya "0.0" ve "33243.29" gibi
    İngilizce biçimler taşırdı.
    """
    if v is None:
        return "—"
    try:
        m = f"{float(v):,.{ondalik}f}"
    except (TypeError, ValueError):
        return str(v)
    # Sayfa tipografisi ASCII tire değil eksi işareti (U+2212) kullanır.
    return (m.replace(",", "\u00a0").replace(".", ",").replace("\u00a0", ".")
             .replace("-", "\u2212"))


def koy(anahtar: str, deger, ondalik: int | None = 2) -> None:
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        uyar(f"'{anahtar}' kaynakta yok — anahtar atlandı.")
        return
    if ondalik is None:
        O[anahtar] = deger
    elif ondalik == 0:
        O[anahtar] = int(round(float(deger)))
    else:
        O[anahtar] = round(float(deger), ondalik)


def son(s: pd.Series):
    s = s.dropna()
    return (float(s.iloc[-1]), s.index[-1]) if len(s) else (None, None)


def tr_tarih(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day:02d}.{t.month:02d}.{t.year}"


def main() -> int:
    M = pd.read_csv(VERI / "metrik.csv", index_col=0, parse_dates=True)
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))
    vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    # ZK büyüklükleri metrik_ozet.json'daki `zk` bloğundan okunur (oran, taban,
    # tesis adımları orada zaten türetilmiş); data/zk.csv yalnız grafik içindir.
    hyol = VERI / "haftalik_metrik.csv"
    H = pd.read_csv(hyol, index_col=0, parse_dates=True) if hyol.exists() else None

    s_gun = pd.Timestamp(m["son_gun"])
    s_hafta = pd.Timestamp(m["son_hafta"])
    bugun = pd.Timestamp.today().normalize()

    # --- dönem çıpaları ----------------------------------------------------
    O["_tarih"] = tr_tarih(s_gun)
    O["gun"] = gun_ad(s_gun)
    O["gun_kisa"] = tr_tarih(s_gun)
    O["hafta"] = gun_ad(s_hafta)
    O["hafta_kisa"] = tr_tarih(s_hafta)
    O["ay_ad"] = AY_TR[s_gun.month]
    O["yil"] = int(s_gun.year)
    O["kosum_tarihi"] = tr_tarih(bugun)
    # Yayım gecikmesi: APİ tablosu AYNI İŞ GÜNÜ yayımlanıyor; ölçülen gecikme
    # duvar saatine göre hesaplanır (verinin kendi son gününe göre değil).
    koy("yayim_gecikme_gun", (bugun - s_gun).days, 0)
    koy("hafta_gecikme_gun", (bugun - s_hafta).days, 0)

    # --- faizler -----------------------------------------------------------
    for ad, kol in (("politika", "politika"), ("koridor_alt", "koridor_alt"),
                    ("koridor_ust", "koridor_ust"), ("glp", "glp_satis"),
                    ("aofm", "aofm"), ("aosm", "aosm"),
                    ("marjinal", "marjinal_faiz"), ("tlref", "tlref"),
                    ("bist_on", "bist_on")):
        v, t = son(M[kol]) if kol in M.columns else (None, None)
        koy(ad, v, 2)
        if t is not None:
            O[f"{ad}_tarih"] = tr_tarih(t)
    v, _ = son(M["koridor_bant"])
    koy("koridor_bant", v, 2)
    # AOFM çıpa gününde geçerli mi? Sayfa metni bu bayrağa bağlanır: geçersizse
    # "fonlama maliyeti şu kadar" cümlesi KURULMAZ.
    O["aofm_gecerli"] = bool(M["aofm_gecerli"].reindex([s_gun]).fillna(False).iloc[0])
    O["aofm_ham"] = (round(float(M["aofm_ham"].loc[s_gun]), 2)
                     if s_gun in M.index and pd.notna(M["aofm_ham"].loc[s_gun])
                     else None)
    kaynak = (M["marjinal_kaynak"].loc[s_gun]
              if s_gun in M.index else None)
    O["marjinal_kaynak"] = str(kaynak) if kaynak is not None else "yok"
    # AOFM geçersizse SEBEBİ de dışarı çıkar. Aşağı akıştaki katmanlar (bülten
    # panosu) yalnız bayrağı görüp "kaynak güncel saymıyor" diye yazıyordu ve
    # okur bunu TCMB yayımlamıyor sanıyordu. Oysa TCMB yayımlıyor; eleyen bizim
    # taban eşiğimiz. Bayrağın yanında sebebi taşımayan bir alan, aşağıda
    # kaçınılmaz olarak yanlış cümleye dönüşüyor.
    if not O["aofm_gecerli"]:
        fon = (float(M["fon_top"].loc[s_gun])
               if s_gun in M.index and pd.notna(M["fon_top"].loc[s_gun]) else None)
        O["aofm_gecersiz_sebep"] = (
            "TCMB seriyi yayımlıyor (ham %s), ama fonlama tabanı %s — %s mlr TL "
            "eşiğinin altında olduğu için ölçü bilgi taşımıyor; bu rejimde "
            "marjinal TCMB faizi sterilizasyon tarafından belirleniyor"
            % (("%.2f" % O["aofm_ham"]).replace(".", ",") if O["aofm_ham"] is not None
               else "yok",
               ("%.1f mlr TL" % (fon / 1000.0)).replace(".", ",") if fon is not None
               else "yok",
               ("%.0f" % (((m.get("rejim") or {}).get("taban_esik_mn_tl") or 0) / 1000.0))))

    # Spreadlerin ÇIPASI kendi son dolu gününden okunur: AOFM tabansız
    # günlerde NaN olduğu için AOFM'li makasların son günü politika faizinin
    # son gününden GERİDE olabilir. Tek bir "_tarih" kullanmak, bir haftalık
    # gecikmeyi sessizce bugünmüş gibi gösterirdi.
    for ad in ("spread_tlref_politika", "spread_aofm_politika",
               "spread_tlref_aofm", "spread_marjinal_politika"):
        v, t = son(M[ad])
        koy(ad, v, 2)
        if t is not None:
            O[f"{ad}_tarih"] = tr_tarih(t)
    # ORTAK GÜN SPREADLERİ. Yukarıdaki üç makas kendi son dolu gününden
    # okunuyor ve AOFM'li olanlar 12 gün geride kalabiliyor; yan yana basılınca
    # aritmetik kapanmaz ((TLREF−politika) − (AOFM−politika) ≠ TLREF−AOFM).
    # Burada üçü de son ORTAK dolu güne çıpalanır; tanı satırı olarak iki
    # ailenin farkı da yazılır.
    ortak = M[["spread_tlref_politika", "spread_aofm_politika",
               "spread_tlref_aofm"]].dropna()
    if len(ortak):
        t_ortak = ortak.index[-1]
        O["spread_ortak_gun"] = tr_tarih(t_ortak)
        koy("spread_ortak_yas_gun", (s_gun - t_ortak).days, 0)
        for ad in ("spread_tlref_politika", "spread_aofm_politika",
                   "spread_tlref_aofm"):
            koy(f"{ad}_ortak_gun", float(ortak[ad].iloc[-1]), 2)
        # Vintaj farkının BÜYÜKLÜĞÜ: son dolu günlerden kurulan üçlü ile ortak
        # günden kurulan üçlünün kapanma artığı.
        artik = ((O.get("spread_tlref_politika") or 0)
                 - (O.get("spread_aofm_politika") or 0)
                 - (O.get("spread_tlref_aofm") or 0))
        koy("spread_vintaj_artik_pp", artik, 2)

    v, _ = son(M["konum_tlref"])
    koy("konum_tlref_yuzde", v * 100 if v is not None else None, 1)
    # Koridor SİMETRİK DEĞİLDİR ve marjinal fiyat tavanın üstüne çıkabilir:
    # konum ölçüsü %100'ü aşar. Bu bir hata değil, ölçünün tanımıdır.
    v, _ = son(M["konum_marjinal"])
    koy("konum_marjinal_yuzde", v * 100 if v is not None else None, 1)
    v, _ = son(M["koridor_asimetri"])
    koy("koridor_asimetri_pp", v, 2)
    O["koridor_simetrik"] = bool(v is not None and abs(v) < 1e-9)

    # --- APİ büyüklükleri (milyon TL → milyar TL) --------------------------
    for ad, kol in (("net_fonlama", "net_fonlama"), ("fonlama", "fon_top"),
                    ("sterilizasyon", "ste_top"), ("ste_ihale", "ste_ihale"),
                    ("ste_kotasyon", "ste_kot"), ("ste_liksen", "ste_liksen"),
                    ("fon_ihale", "fon_ihale"), ("fon_kot_repo", "fon_kot_repo"),
                    ("fon_glp", "fon_glp"),
                    ("serbest_mevduat", "serbest_mevduat"),
                    ("gun_basi_likidite", "gun_basi_likidite"),
                    ("tcmb_tl_saglama", "tcmb_tl_saglama")):
        if kol not in M.columns:
            continue
        v, _ = son(M[kol])
        koy(f"{ad}_mlr", v / 1000.0 if v is not None else None, 1)
    O["net_fonlama_isaret"] = (
        "sistem TCMB'ye net borçlu" if (O.get("net_fonlama_mlr") or 0) > 0
        else "sistem TCMB'nin net alacaklısı")
    st = O.get("sterilizasyon_mlr")
    if st:
        koy("pay_ste_ihale", 100 * (O.get("ste_ihale_mlr") or 0) / st, 1)
        koy("pay_ste_kotasyon", 100 * (O.get("ste_kotasyon_mlr") or 0) / st, 2)
        koy("pay_ste_liksen", 100 * (O.get("ste_liksen_mlr") or 0) / st, 2)

    # --- analitik bilanço --------------------------------------------------
    for ad in ("emisyon", "rezerv_para", "mb_parasi", "zk_bloke",
               "kamu_mevduati", "bankalar_mevduati"):
        if ad in M.columns:
            v, t = son(M[ad])
            koy(f"{ad}_mlr", v / 1000.0 if v is not None else None, 1)
            if t is not None and ad == "emisyon":
                O["bilanco_tarih"] = tr_tarih(t)

    # --- swap --------------------------------------------------------------
    if "swap_alim_usd" in M.columns:
        for ad, kol in (("swap_alim", "swap_alim_usd"),
                        ("swap_satim", "swap_satim_usd")):
            v, t = son(M[kol])
            koy(f"{ad}_mn_usd", v, 0)
            koy(f"{ad}_mlr_usd", v / 1000.0 if v is not None else None, 2)
            if t is not None:
                O[f"{ad}_tarih"] = tr_tarih(t)
        v, _ = son(M["swap_alim_tl"])
        koy("swap_alim_mlr_tl", v / 1000.0 if v is not None else None, 1)
        v, _ = son(M["swap_satim_tl"])
        koy("swap_satim_mlr_tl", v / 1000.0 if v is not None else None, 1)
        v, _ = son(M["swap_net_tl"])
        koy("swap_net_mlr_tl", v / 1000.0 if v is not None else None, 1)
        v, _ = son(M["api_ve_swap_alim"])
        koy("api_ve_swap_alim_mlr", v / 1000.0 if v is not None else None, 1)
        v, _ = son(M["kur"])
        koy("kur", v, 4)
    # HANGİ BACAKLAR DAHİL — sayfada başlık tek başına kaldığında okur
    # toplamın kapsamını bilemez; kapsam metin anahtarı olarak taşınır.
    O["tcmb_tl_saglama_kapsam"] = (
        "Net APİ fonlaması (A − B) + alım yönlü swap stokunun TL karşılığı "
        "− satım yönlü swap stokunun TL karşılığı. Satım bacağı bu koşuda "
        f"{tr_sayi(O.get('swap_satim_mlr_tl'), 1)} milyar TL'lik TL "
        "ÇEKİLMESİNE denk gelir ve toplamdan düşülmüştür; yalnız alım bacaklı "
        f"eski tanım {tr_sayi(O.get('api_ve_swap_alim_mlr'), 1)} milyar TL "
        "verirdi ve api_ve_swap_alim_mlr anahtarında tanı olarak durur.")

    # --- zorunlu karşılıklar ----------------------------------------------
    zk = m.get("zk") or {}
    koy("zk_oran", zk.get("ima_oran_son"), 2)
    if zk.get("ima_oran_tarih"):
        O["zk_oran_tarih"] = tr_tarih(zk["ima_oran_tarih"])
    koy("zk_oran_1y_once", zk.get("ima_oran_1y_once"), 2)
    if zk.get("ima_oran_son") is not None and zk.get("ima_oran_1y_once"):
        koy("zk_oran_1y_fark", zk["ima_oran_son"] - zk["ima_oran_1y_once"], 2)
    koy("zk_taban_mlr", (zk.get("taban_son_mn_tl") or 0) / 1000.0
        if zk.get("taban_son_mn_tl") else None, 0)
    if zk.get("taban_son_tarih"):
        O["zk_taban_tarih"] = tr_tarih(zk["taban_son_tarih"])
    koy("zk_adim_sayisi", zk.get("adim_sayisi"), 0)
    koy("zk_adim_medyan_gun", zk.get("adim_ortalama_gun"), 0)
    adimlar = zk.get("son_adimlar") or []
    if adimlar:
        a = adimlar[-1]
        O["zk_son_adim_tarih"] = tr_tarih(a["tarih"])
        koy("zk_son_adim_mlr", a["degisim_mn_tl"] / 1000.0, 1)
        en_buyuk = max(adimlar, key=lambda x: abs(x["degisim_mn_tl"]))
        O["zk_enbuyuk_adim_tarih"] = tr_tarih(en_buyuk["tarih"])
        koy("zk_enbuyuk_adim_mlr", en_buyuk["degisim_mn_tl"] / 1000.0, 1)

    # --- kredi/mevduat faizleri ve geçişkenlik -----------------------------
    if H is not None and not H.empty:
        for ad, kol in (("kredi_ticari", "f_ticari_tl"),
                        ("kredi_tuketici", "f_tuketici"),
                        ("kredi_ihtiyac", "f_ihtiyac"),
                        ("kredi_konut", "f_konut"),
                        ("mevduat_tl", "f_mevduat_tl"),
                        ("makas", "makas"), ("kredi_marj", "kredi_marj"),
                        ("mevduat_marj", "mevduat_marj")):
            if kol in H.columns:
                v, _ = son(H[kol])
                koy(ad, v, 2)
    g = (m.get("gecirgenlik") or {}).get("gecikme_taramasi", {})
    for ad, k in (("ticari", "ticari_tl"), ("mevduat", "mevduat_tl")):
        d = g.get(k) or {}
        koy(f"beta_{ad}_tam", d.get("tam_beta"), 2)
        koy(f"beta_{ad}_son", d.get("son_beta"), 2)
        koy(f"beta_{ad}_r2", d.get("son_r2"), 2)
        koy(f"beta_{ad}_gecikme", d.get("en_iyi_gecikme_hafta"), 0)
        koy(f"beta_{ad}_n", d.get("n"), 0)
    koy("gecis_pencere_hafta", (m.get("esik") or {}).get("gecis_pencere_hafta"), 0)

    # --- rejim -------------------------------------------------------------
    r = m.get("rejim") or {}
    for ad in ("pencere_gun", "net_negatif_gun", "net_pozitif_gun",
               "fonlama_sifir_gun", "aofm_gecersiz_gun",
               "aofm_gecersizken_dolu_gun"):
        koy(f"rejim_{ad}", r.get(ad), 0)
    if r.get("pencere_gun"):
        koy("rejim_negatif_pay", 100 * r["net_negatif_gun"] / r["pencere_gun"], 0)
    koy("aofm_taban_esik_mlr", (r.get("taban_esik_mn_tl") or 0) / 1000.0, 0)
    mk = r.get("marjinal_kaynak") or {}
    O["marjinal_kaynak_dagilim"] = " · ".join(
        f"{k}: {v} gün" for k, v in sorted(mk.items(), key=lambda x: -x[1]))

    # --- örtük sıkılaştırma dönemleri --------------------------------------
    don = m.get("donemler") or []
    koy("donem_sayisi", len(don), 0)
    if don:
        u = max(don, key=lambda d: d["gun"])
        O["donem_uzun_bas"] = tr_tarih(u["bas"])
        O["donem_uzun_son"] = tr_tarih(u["son"])
        koy("donem_uzun_gun", u["gun"], 0)
        koy("donem_uzun_aofm", u["aofm_ort"], 2)
        koy("donem_uzun_glp", u["glp_ort"], 2)
        koy("donem_uzun_tavan", u["koridor_ust_ort"], 2)
        koy("donem_uzun_asim", u["asim_ort_pp"], 2)
        d2 = max(don, key=lambda d: d["asim_maks_pp"])
        O["donem_derin_bas"] = tr_tarih(d2["bas"])
        koy("donem_derin_asim", d2["asim_maks_pp"], 2)
        O["donem_ilk_bas"] = tr_tarih(min(don, key=lambda d: d["bas"])["bas"])
        O["donem_son_son"] = tr_tarih(max(don, key=lambda d: d["son"])["son"])

    # --- koridor ALTI dönemler (simetrik denetim) --------------------------
    dona = m.get("donemler_alti") or []
    koy("donem_alti_sayisi", len(dona), 0)
    if dona:
        u = max(dona, key=lambda d: d["gun"])
        O["donem_alti_uzun_bas"] = tr_tarih(u["bas"])
        O["donem_alti_uzun_son"] = tr_tarih(u["son"])
        koy("donem_alti_uzun_gun", u["gun"], 0)
        koy("donem_alti_uzun_aofm", u["aofm_ort"], 2)
        koy("donem_alti_uzun_taban", u["koridor_alt_ort"], 2)
        koy("donem_alti_uzun_sapma", u["asim_ort_pp"], 2)
        d2 = max(dona, key=lambda d: d["asim_maks_pp"])
        O["donem_alti_derin_bas"] = tr_tarih(d2["bas"])
        koy("donem_alti_derin_sapma", d2["asim_maks_pp"], 2)
        koy("donem_alti_toplam_gun", sum(d["gun"] for d in dona), 0)

    # --- bayraklar (sıfıra düşmüş olgular) ---------------------------------
    # Sayfa metni bu bayraklara bağlanmazsa "swap ile TL sağlanıyor" cümlesi
    # olgu bittikten sonra da yayında kalır — hiç güncellenmeyen bir sayıdan
    # kötüdür, çünkü yanlış bir MEKANİZMA anlatır.
    for k, v in (m.get("bayrak") or {}).items():
        O[k] = bool(v)
    O["swap_cumlesi"] = (
        f"Alım yönlü swap stoku {O.get('swap_alim_mn_usd', 0)} milyon dolar — "
        "kanal bu ölçüm gününde kapalı." if not O.get("swap_alim_aktif")
        else f"Alım yönlü swap stoku {O.get('swap_alim_mlr_usd')} milyar dolar.")

    # --- doğrulama ---------------------------------------------------------
    D = m.get("dogrulama") or {}
    if "politika" in D and "n" in D["politika"]:
        koy("dog_politika_n", D["politika"]["n"], 0)
        koy("dog_politika_maks", D["politika"]["maks_fark_pp"], 3)
    if "net_fonlama" in D:
        koy("dog_net_n", D["net_fonlama"]["n"], 0)
        O["dog_net_maks"] = f"{D['net_fonlama']['maks_fark_mn_tl']:.1e}"
    if "tlref" in D:
        koy("dog_tlref_n", D["tlref"]["n"], 0)
        koy("dog_tlref_ort", D["tlref"]["ort_fark_pp"], 4)
        koy("dog_tlref_maks", D["tlref"]["maks_fark_pp"], 3)
    if "hatlar_arasi_swap" in D:
        koy("dog_swap_n", D["hatlar_arasi_swap"]["n"], 0)
        O["dog_swap_maks"] = f"{D['hatlar_arasi_swap']['maks_fark_mlr_usd']:.1e}"
    kim = (vd.get("kimlik") or {}).get("A24/1000 = −APIFON3") or {}
    if kim:
        koy("kimlik_api_n", kim.get("n_pencere"), 0)
        koy("kimlik_api_maks_mlr", (kim.get("pencere_maks_fark") or 0) / 1000.0, 2)
    ak = D.get("aofm_kompozisyon") or {}
    if ak:
        koy("dog_aofm_n", ak.get("n"), 0)
        koy("dog_aofm_medyan_pp", ak.get("medyan_fark_pp"), 3)
        koy("dog_aofm_p95_pp", ak.get("p95_fark_pp"), 2)
        koy("dog_aofm_son250_medyan_pp", ak.get("son250_medyan_pp"), 3)
        koy("dog_aofm_son_pp", ak.get("son_fark_pp"), 3)
        if ak.get("son_gun"):
            O["dog_aofm_son_gun"] = tr_tarih(ak["son_gun"])
        O["dog_aofm_gecti"] = bool(ak.get("gecti"))
    ab = D.get("aofm_bant") or {}
    if ab:
        koy("dog_bant_alt_gun", ab.get("alt_ihlal_gun"), 0)
        koy("dog_bant_ust_gun", ab.get("ust_ihlal_gun"), 0)
        if ab.get("alt_ihlal_son"):
            O["dog_bant_alt_son"] = tr_tarih(ab["alt_ihlal_son"])
    zt = (m.get("zk") or {})
    koy("zk_taban_birim_bagil_medyan", zt.get("taban_birim_bagil_medyan"), 6)
    koy("zk_taban_birim_bagil_son", zt.get("taban_birim_bagil_son"), 6)
    koy("zk_taban_birim_bagil_maks", zt.get("taban_birim_bagil_maks"), 4)
    koy("zk_taban_birim_tekil_gun", zt.get("taban_birim_tekil_gun"), 0)
    if zt.get("taban_birim_maks_tarih"):
        O["zk_taban_birim_maks_tarih"] = tr_tarih(zt["taban_birim_maks_tarih"])
    if zt.get("taban_kaynak"):
        O["zk_taban_kaynak"] = zt["taban_kaynak"]
    aos = D.get("aosm_taban") or {}
    koy("aosm_taban_kat", aos.get("medyan_kat"), 1)
    koy("aosm_taban_n", aos.get("n"), 0)

    # --- uyarılar ----------------------------------------------------------
    uyarilar = list(uy.get("uyarilar", []))
    # SON SAVUNMA: uyarilar.json bir önceki koşudan kalmış ya da metrik katmanı
    # devralmayı atlamış olabilir. veri_durum.json burada da okunur; sayım iki
    # kaynağın BİRLEŞİMİ üzerinden yapılır ki sayfadaki "n uyarı düştü" cümlesi
    # gerçekten düşen uyarı sayısını söylesin.
    for u in (vd.get("uyarilar") or []):
        if u not in uyarilar:
            uyarilar.append(u)

    # --- TAZELİK BAYRAĞI ---------------------------------------------------
    # Yayım gecikmesi aile toleransını aşarsa veri BAYATTIR. Bu bayrak sayfada
    # görünür bir kutuya bağlanır: kaynak durduğunda hat yeşil bitse bile
    # okurun gördüğü ilk şey bayatlık olur.
    tol_gun = tazelik_tolerans("gunluk")
    tol_hafta = tazelik_tolerans("haftalik")
    bayat_sebep: list[str] = []
    if (O.get("yayim_gecikme_gun") or 0) > tol_gun:
        bayat_sebep.append(
            f"günlük bacak {O['yayim_gecikme_gun']} gün geride "
            f"(tolerans {tol_gun} gün)")
    if (O.get("hafta_gecikme_gun") or 0) > tol_hafta:
        bayat_sebep.append(
            f"haftalık bacak {O['hafta_gecikme_gun']} gün geride "
            f"(tolerans {tol_hafta} gün)")
    # Veri katmanının kendi tazelik/önbellek uyarıları da bayatlık kanıtıdır.
    izler = [u for u in uyarilar
             if u.startswith(("TAZELİK", "ESKİ ÖNBELLEK", "BAYAT"))]
    if izler:
        bayat_sebep.append(f"veri katmanı {len(izler)} tazelik/önbellek "
                           "uyarısı bastı")
    O["bayat"] = bool(bayat_sebep)
    O["bayat_tolerans_gun"] = tol_gun
    O["bayat_tolerans_hafta"] = tol_hafta
    O["bayat_cumlesi"] = (
        "BAYAT VERİ: " + "; ".join(bayat_sebep)
        + ". Sayfadaki sayılar bu koşuda İLERLEMEMİŞ olabilir."
        if bayat_sebep else
        "Veri taze: yayım gecikmesi tolerans içinde, tazelik uyarısı yok.")

    O["uyari_sayisi"] = len(uyarilar)
    O["uyari_metni"] = ((O["bayat_cumlesi"] + " · " if O["bayat"] else "")
                        + (" · ".join(uyarilar) if uyarilar
                           else "Bu koşuda uyarı yok."))
    # Sayıyı ÇERÇEVELEYEN cümle de sayıdan türetilir; kendisiyle çelişen bir
    # metin ("tek uyarı budur" + 3 madde) kalmasın.
    O["uyari_cumlesi"] = (
        "Bu koşuda uyarı düşmedi." if not uyarilar else
        "Bu koşuda düşen tek uyarı budur:" if len(uyarilar) == 1 else
        f"Bu koşuda {len(uyarilar)} uyarı düştü:")
    O["aosm_not"] = m.get("aosm_not")
    O["zk_oran_not"] = m.get("zk_oran_not")

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · veri {O['gun']} "
          f"({O['yayim_gecikme_gun']} gün önce) · haftalık {O['hafta']}"
          + ("  ! BAYAT" if O.get("bayat") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
