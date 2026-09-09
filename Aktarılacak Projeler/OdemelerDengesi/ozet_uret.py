# -*- coding: utf-8 -*-
"""Ödemeler dengesi ve dış finansman — ozet.json üretimi.

Sayfa metnindeki OYNAK her sayı buradan beslenir (CLAUDE.md kural 5):
MDX'te `<Deger proje="odemeler-dengesi" anahtar="..." ondalik={1}>yedek</Deger>`.
Tarihsel/metodolojik sabitler (formüller, kurum tanımları, BPM6 kuralları)
sayfada STATİK kalır — onlar veri tazelendikçe değişmez.

DÖRT DÖNEM ÇIPASI. Bu hatta dört ayrı yayım ritmi var ve hepsi ayrı anahtar
olarak taşınır; tek etiket kullanmak 145 gün geride kalan GSYH oranını "bu ayın
sayısı" gibi gösterirdi:
    _tarih   → aylık ödemeler dengesi (başrol)
    _tarih2  → üç aylık GSYH (cari denge/GSYH oranının kendi dönemi)
    _tarih3  → haftalık dış borç ödemeleri (hattın en taze verisi)
    _tarih4  → günlük kur (GSYH dönüşümünün girdisi)

ŞEKİL DAMGALARI. Aynı ayrışma sayfadaki ŞEKİLLERİN altındaki "veri <tarih>"
etiketinde de var: o etiket, ayrı bir anahtar verilmemişse hattın ANA saatini
basar ve on iki figürün ikisi aynı saatte değil. İkisinin damgası bu yüzden
kendi anahtarını taşır ve sayfada tarihAnahtari ile bağlanır:
    oran_kisa     → Şekil 04 (yalnız çeyreklik seriden çizilir)
    sekil12_kisa  → Şekil 12 (iki ayrı ritimdeki panelleri birden yazar)

Bütün değerler data/ altındaki ÜRETİLMİŞ dosyalardan okunur; elle sayı
yazılmaz. Bir değer kaynakta yoksa anahtar ATLANIR ve stderr'e uyarı basılır —
MDX'teki statik yedek görünür, ama sessizce yanlış bir sayı basılmaz.

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from veri import (PROJE, VERI, AY_TR, ay_ad, ceyrek_ad, donem_sonu, gun_ad,
                  tazelik_tolerans)

O: dict = {}


def uyar(m: str) -> None:
    print(f"UYARI: {m}", file=sys.stderr)


def tr_sayi(v, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi (binlik nokta, ondalık virgül, eksi U+2212).

    ozet.json'daki METİN anahtarları sayfaya olduğu gibi basılır; Python'un
    varsayılan biçimi oraya "0.0" ve "-38888.0" gibi İngilizce diziler taşırdı.
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
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        uyar(f"'{anahtar}' kaynakta yok — anahtar atlandı.")
        return
    if ondalik is None:
        O[anahtar] = deger
    elif ondalik == 0:
        O[anahtar] = int(round(float(deger)))
    else:
        O[anahtar] = round(float(deger), ondalik)


def mia(v, ondalik: int = 1):
    """Milyon USD → milyar USD. Sayfada 'milyar' yazan her sayı buradan geçer."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return round(float(v) / 1000.0, ondalik)


def son(s: pd.Series):
    s = s.dropna()
    return (float(s.iloc[-1]), s.index[-1]) if len(s) else (None, None)


def tr_tarih(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day:02d}.{t.month:02d}.{t.year}"


def tr_ay(t) -> str:
    """AYLIK ve ÇEYREKLİK saatlerin yazımı: AA.YYYY (ortak/bicim sözleşmesi).

    Aylık bir gözlem GÜN gibi yazılamaz — "30.06.2026" okura o GÜNÜN ölçümü
    gibi görünür, oysa ölçü Haziran AYINA aittir. 09.09.2026'da ölçüldü: aynı
    anahtarı (`ay_kisa`) yazan kardeş hat butce-borc "06.2026" yazıyordu, bu
    hat "30.06.2026" — tek anahtar, iki sözleşme. Çeyreklik saat de aynı
    yazımı kullanır ve çeyreğin SON ayını gösterir; etiket ayrı anahtarda
    (`ceyrek`) durur.
    """
    t = pd.Timestamp(t)
    return f"{t.month:02d}.{t.year}"


def main() -> int:
    M = pd.read_csv(VERI / "metrik.csv", index_col=0, parse_dates=True)
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))
    vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    gyol, hyol = VERI / "ceyrek_metrik.csv", VERI / "haftalik_metrik.csv"
    G = pd.read_csv(gyol, index_col=0, parse_dates=True) if gyol.exists() else None
    H = pd.read_csv(hyol, index_col=0, parse_dates=True) if hyol.exists() else None

    s_ay = pd.Timestamp(m["son_ay"])
    s_ceyrek = pd.Timestamp(m["son_ceyrek"])
    s_hafta = pd.Timestamp(m["son_hafta"])
    s_gun = pd.Timestamp(m["son_gun"])
    bugun = pd.Timestamp.today().normalize()

    # ======================================================= dönem çıpaları
    O["_tarih"] = tr_ay(donem_sonu(s_ay, "ay"))
    O["_tarih2"] = tr_ay(s_ceyrek)
    O["_tarih3"] = tr_tarih(s_hafta)
    O["_tarih4"] = tr_tarih(s_gun)
    O["ay"] = ay_ad(s_ay)
    O["ay_ad"] = AY_TR[s_ay.month]
    O["yil"] = int(s_ay.year)
    O["ay_kisa"] = tr_ay(donem_sonu(s_ay, "ay"))
    O["ceyrek"] = ceyrek_ad(s_ceyrek)
    O["ceyrek_kisa"] = tr_ay(s_ceyrek)
    O["hafta"] = gun_ad(s_hafta)
    O["hafta_kisa"] = tr_tarih(s_hafta)
    O["kur_gun"] = gun_ad(s_gun)
    O["kosum_tarihi"] = tr_tarih(bugun)
    # ŞEKİL 12'NİN KARMA DAMGASI. Sayfa her şeklin altına "veri <tarih>" basar
    # ve ayrı bir anahtar verilmezse hattın ANA saatini (_tarih = aylık
    # ödemeler dengesi) kullanır. Şekil 12'nin üç paneli İKİ ayrı saatte:
    # (a) ve (b) eurobond akımı ödemeler dengesi ritminde, (c) haftalık dış
    # borç ödeme takvimi kendi çarşamba ritminde. 03.09.2026 doğrulama turunda
    # ölçüldü: aylık bacak 30.06.2026'da, haftalık bacak 26.08.2026'da bitiyor,
    # yani aradaki mesafe 57 GÜN. Tek damga hangi bacağı seçerse seçsin YALAN
    # söylüyor — aylık damga en taze paneli 57 gün bayat gösteriyordu, haftalık
    # damga da Haziran'da duran iki paneli iki ay taze gösterirdi. Bu yüzden
    # damga İKİSİNİ birden yazar; tarihYaz() tanımadığı dizgeyi olduğu gibi
    # geçirir. Şekil saat defterine konamaz: orada yalnız ÇÖZÜLEBİLİR tek bir
    # tarih ya da null durabilir (sayfa sınavı 18 ENGEL üretir), yani bu
    # birleşik damga şeklin kendi etiketinden, tarihAnahtari ile bağlanır.
    O["sekil12_kisa"] = f"aylık {O['ay_kisa']} · haftalık {O['hafta_kisa']}"
    # Yayım gecikmesi DÖNEM SONUNDAN ve DUVAR SAATİNE göre ölçülür; verinin
    # kendi son gününü referans almak denetimi kendi kendine referanslı
    # yapardı ("son gözlem bugün, demek ki taze").
    koy("yayim_gecikme_gun", (bugun - donem_sonu(s_ay, "ay")).days, 0)
    koy("ceyrek_gecikme_gun", (bugun - s_ceyrek).days, 0)
    koy("hafta_gecikme_gun", (bugun - s_hafta).days, 0)
    koy("kur_gecikme_gun", (bugun - s_gun).days, 0)
    O["donem_cumlesi"] = (
        f"Ödemeler dengesi {O['ay']} verisiyle "
        f"({O['yayim_gecikme_gun']} gün gecikme), cari denge/GSYH oranı "
        f"{O['ceyrek']} çeyreğiyle ({O['ceyrek_gecikme_gun']} gün), haftalık "
        f"dış borç ödeme takvimi {O['hafta']} ile ({O['hafta_gecikme_gun']} "
        "gün) günceldir.")

    b = m["basrol"]

    # ======================================================= cari denge
    koy("cari_ay_mn", b.get("cari_aylik_mn_usd"), 0)
    koy("cari_ay_mia", mia(b.get("cari_aylik_mn_usd")), 1)
    koy("cekirdek_ay_mia", mia(b.get("cekirdek_aylik_mn_usd")), 1)
    koy("cari12_mn", b.get("cari12_mn_usd"), 0)
    koy("cari12_mia", mia(b.get("cari12_mn_usd")), 1)
    koy("cekirdek12_mn", b.get("cekirdek12_mn_usd"), 0)
    koy("cekirdek12_mia", mia(b.get("cekirdek12_mn_usd")), 1)
    koy("makas12_mn", b.get("makas12_mn_usd"), 0)
    koy("makas12_mia", mia(b.get("makas12_mn_usd")), 1)
    koy("altin_net12_mia", mia(b.get("altin_net12_mn_usd")), 1)
    koy("enerji_net12_mia", mia(b.get("enerji_net12_mn_usd")), 1)
    for anahtar, kol in (("mal12_mia", "mal_denge12"),
                         ("hizmet12_mia", "hizmet_denge12"),
                         ("birincil12_mia", "birincil_denge12"),
                         ("ikincil12_mia", "ikincil_denge12"),
                         ("ihracat12_mia", "ihracat12"),
                         ("ithalat12_mia", "ithalat12"),
                         ("altin_haric12_mia", "altin_haric12"),
                         ("enerji_haric12_mia", "enerji_haric12")):
        v, _ = son(M[kol])
        koy(anahtar, mia(v), 1)
    # Cari denge AÇIK mı FAZLA mı — cümlenin kendisi de sayıdan türetilir.
    O["cari_yon"] = "açık" if (b.get("cari12_mn_usd") or 0) < 0 else "fazla"
    O["cekirdek_yon"] = ("fazla" if (b.get("cekirdek12_mn_usd") or 0) > 0
                         else "açık")
    O["cari_cumlesi"] = (
        f"12 aylık birikimli cari {O['cari_yon']} "
        f"{tr_sayi(abs(O.get('cari12_mia', 0)), 1)} milyar USD; altın ve enerji "
        f"hariç çekirdek cari denge ise {tr_sayi(abs(O.get('cekirdek12_mia', 0)), 1)} "
        f"milyar USD {O['cekirdek_yon']}. Aradaki makas "
        f"{tr_sayi(abs(O.get('makas12_mia', 0)), 1)} milyar USD.")

    # ======================================================= CA / GSYH
    gs = m.get("gsyh", {})
    koy("cari_gsyh", gs.get("cari_gsyh_son"), 2)
    koy("cekirdek_gsyh", gs.get("cekirdek_gsyh_son"), 2)
    koy("cari_gsyh_min", gs.get("cari_gsyh_min"), 2)
    koy("cari_gsyh_maks", gs.get("cari_gsyh_maks"), 2)
    O["cari_gsyh_min_donem"] = (ceyrek_ad(gs["cari_gsyh_min_donem"])
                                if gs.get("cari_gsyh_min_donem") else None)
    O["cari_gsyh_maks_donem"] = (ceyrek_ad(gs["cari_gsyh_maks_donem"])
                                 if gs.get("cari_gsyh_maks_donem") else None)
    koy("gsyh4_trilyon_usd", gs.get("gsyh4_trilyon_usd"), 3)
    koy("gsyh4_mia_usd", (gs.get("gsyh4_trilyon_usd") or 0) * 1000, 0)
    koy("nokta_kur_farki_yuzde", gs.get("nokta_kur_farki_yuzde"), 2)
    O["gsyh_mertebe_gecti"] = bool(gs.get("mertebe_gecti"))
    O["gsyh_bant"] = gs.get("mertebe_bant_trn")
    # Oranın aylık cari dengeden kaç ay geride kaldığı — ölçülür, uydurulmaz.
    gecik_ay = round((donem_sonu(s_ay, "ay") - s_ceyrek).days / 30.44, 1)
    koy("oran_gecikmesi_ay", gecik_ay, 1)
    O["oran_donem_cumlesi"] = (
        f"Cari denge/GSYH oranı {O['ceyrek']} çeyreğine aittir; aylık cari "
        f"denge ondan {tr_sayi(gecik_ay, 1)} ay ilerdedir. Oranı 'son ayın "
        "sayısı' diye sunmak sessiz bayatlama olurdu.")
    # ŞEKİL 04'ÜN DAMGASI — ORANIN KENDİ ÇEYREĞİ. Bu şekil aylık metriğe HİÇ
    # dokunmaz: yalnız çeyreklik çerçeveden cari_gsyh / cekirdek_gsyh / gsyh4
    # çizer, yani ucu ÇEYREKTİR. Şeklin kendi alt metni bunu zaten söylüyordu
    # ("ORANIN çıpası …") ama sayfa üstündeki damga hattın aylık saatini
    # basıyordu.
    #
    # BUGÜN AYRIŞMA YOK: 03.09.2026 koşusunda aylık bacak da çeyreklik oran da
    # 30.06.2026'da bitiyor (oran_gecikmesi_ay = 0,0), yani damga değişmiyor.
    # Kural yine de şimdi konur, çünkü ayrışma bu hattın TABİATINDA var: aylık
    # ödemeler dengesi her ay ilerler, oran ise paydası GSYH olduğu için ancak
    # çeyreklik hesap yayımlanınca ilerler ve bu ikisi arasındaki mesafe bir
    # çeyreğe kadar açılabilir. O gün geldiğinde kuralın devreye girmesi,
    # birinin o gün hatırlamasına bel bağlamaktan güvenlidir; sayfanın kendi
    # metni de zaten aynı sessiz bayatlamaya karşı uyarıyor.
    #
    # ceyrek_kisa DEĞİL: o çıpa GSYH'nin (gsyh_bin_tl) son çeyreğidir ve
    # ödemeler dengesi geciktiğinde oran ondan bir çeyrek GERİDE kalabilir.
    # Damga figürün BAĞLAYICI, yani en eski bacağından okunur: cari_gsyh'nin
    # ölçülen son çeyreği. Alt panelin GSYH bacağı bundan ileri olabilir ve
    # ortak ölçüm oranın bittiği yerde biter.
    if gs.get("cari_gsyh_donem"):
        O["oran_kisa"] = tr_tarih(gs["cari_gsyh_donem"])
    else:
        uyar("'oran_kisa' kaynakta yok — Şekil 04 hattın aylık saatiyle "
             "damgalanır ve bir çeyrek taze görünebilir.")
    if G is not None and not G.empty:
        v, t = son(G["usdtry_ceyrek_ort"])
        koy("usdtry_ceyrek_ort", v, 2)
        v, _ = son(G["usdtry_ceyrek_son"])
        koy("usdtry_ceyrek_son", v, 2)

    # ======================================================= finans hesabı
    koy("fin_giris12_mia", mia(b.get("fin_giris12_mn_usd")), 1)
    koy("brut_yukumluluk12_mia", mia(b.get("brut_yukumluluk12_mn_usd")), 1)
    koy("yerlesik_varlik12_mia", mia(b.get("yerlesik_varlik12_mn_usd")), 1)
    koy("rezerv_akim12_mia", mia(b.get("rezerv_akim12_mn_usd")), 1)
    for anahtar, kol in (("dyy_giris12_mia", "dyy_giris12"),
                         ("portfoy_giris12_mia", "portfoy_giris12"),
                         ("diger_giris12_mia", "diger_giris12"),
                         ("turev_giris12_mia", "turev_giris12"),
                         ("yuk_dyy12_mia", "yuk_dyy12"),
                         ("yuk_port_hisse12_mia", "yuk_port_hisse12"),
                         ("yuk_port_borc12_mia", "yuk_port_borc12"),
                         ("yuk_mevduat12_mia", "yuk_mevduat12"),
                         ("yuk_kredi12_mia", "yuk_kredi12"),
                         ("ticari_kredi_net12_mia", "ticari_kredi_net12"),
                         ("nhn12_mia", "nhn12"),
                         ("sermaye_hesabi12_mia", "sermaye_hesabi12")):
        v, _ = son(M[kol])
        koy(anahtar, mia(v), 1)
    O["rezerv_yon"] = ("arttı" if (b.get("rezerv_akim12_mn_usd") or 0) > 0
                       else "azaldı")

    # ======================================================= kalite
    k = m.get("kalite", {})
    koy("kaliteli12_mia", mia(k.get("kaliteli_12ay")), 1)
    koy("kaliteli12_mn", k.get("kaliteli_12ay"), 0)
    koy("dyy12_mia", mia(k.get("dyy_12ay")), 1)
    koy("ozel_uv_kredi12_mia", mia(k.get("ozel_uv_kredi_12ay")), 1)
    koy("sicak_para12_mia", mia(k.get("sicak_para_12ay")), 1)
    koy("kalite_pay_brut", k.get("pay_brut_son"), 1)
    koy("kalite_pay_acik", k.get("pay_acik_son"), 1)
    koy("kalite_pay_brut_medyan", k.get("pay_brut_medyan_2010"), 1)
    koy("kalite_pay_acik_medyan", k.get("pay_acik_medyan_2010"), 1)
    # PAYDANIN İKİ TANIMI + TANIM KIRILMASI. Ana payda finansal türevleri
    # İÇERİR (BPM6'da hepsi NET yükümlülük oluşumudur) ve türev bacağı negatif
    # olduğunda oranı yukarı savurur; kalem 2014-01'de başladığı için "2010
    # sonrası medyan" iki farklı paydanın karışımıdır. İkisi de yayımlanır ki
    # sayfa hangi tanımı okuduğunu söyleyebilsin.
    koy("kalite_pay_turevsiz", k.get("pay_turevsiz_son"), 1)
    koy("kalite_pay_brut_medyan_2014", k.get("pay_brut_medyan_2014"), 1)
    koy("kalite_pay_turevsiz_medyan_2014", k.get("pay_turevsiz_medyan_2014"), 1)
    koy("payda_brut12_mia", mia(k.get("payda_brut_12ay")), 1)
    koy("payda_turevsiz12_mia", mia(k.get("payda_turevsiz_12ay")), 1)
    koy("turev_bacagi12_mia", mia(k.get("turev_bacagi_12ay")), 1)
    O["payda_notu"] = k.get("payda_notu")
    if (k.get("pay_brut_son") is not None
            and k.get("pay_turevsiz_son") is not None):
        koy("kalite_pay_turev_farki",
            abs(k["pay_brut_son"] - k["pay_turevsiz_son"]), 1)
        O["payda_cumlesi"] = (
            f"Kalite payının paydası BPM6'nın NET yükümlülük oluşumudur ve "
            f"finansal türevleri içerir: türev bacağı "
            f"{tr_sayi(O.get('turev_bacagi12_mia'), 1)} milyar USD olduğu için "
            f"payda {tr_sayi(O.get('payda_brut12_mia'), 1)} milyar USD'ye "
            f"iniyor ve oran %{tr_sayi(O.get('kalite_pay_brut'), 1)} çıkıyor; "
            f"türevsiz paydayla ({tr_sayi(O.get('payda_turevsiz12_mia'), 1)} "
            f"milyar USD) aynı oran %"
            f"{tr_sayi(O.get('kalite_pay_turevsiz'), 1)}, yani "
            f"{tr_sayi(O.get('kalite_pay_turev_farki'), 1)} puan aşağıda.")
    koy("kalite_bos_ay_brut", k.get("pay_brut_bos_ay"), 0)
    koy("kalite_bos_ay_acik", k.get("pay_acik_bos_ay"), 0)
    koy("payda_esik_mia", mia(k.get("payda_esik_mn_usd"), 0), 0)
    O["kalite_cumlesi"] = (
        f"Son 12 ayda kaliteli finansman {tr_sayi(O.get('kaliteli12_mia'), 1)} "
        f"milyar USD: bunun {tr_sayi(O.get('ozel_uv_kredi12_mia'), 1)} milyar "
        f"USD'si özel sektörün net uzun vadeli kredisi, "
        f"{tr_sayi(O.get('dyy12_mia'), 1)} milyar USD'si net doğrudan yatırım. "
        f"Sıcak para {tr_sayi(O.get('sicak_para12_mia'), 1)} milyar USD.")
    O["kalite_payda_notu"] = (
        f"Kalite oranları payda mutlak {tr_sayi(O.get('payda_esik_mia'), 0)} "
        "milyar USD'nin altındayken hesaplanmaz ve grafikte boş bırakılır; "
        f"ölçülen boş ay sayısı brüt paydada {O.get('kalite_bos_ay_brut')}, "
        f"cari açık paydasında {O.get('kalite_bos_ay_acik')}.")

    # ======================================================= çevirme oranı
    r = m.get("rollover", {})
    for anahtar, kaynak in (("roll_bnk", "roll_bnk_son"),
                            ("roll_dgr", "roll_dgr_son"),
                            ("roll_bnk_tcmb", "roll_bnk_tcmb_son"),
                            ("roll_dgr_tcmb", "roll_dgr_tcmb_son"),
                            ("roll_bnk_min", "roll_bnk_min_2010"),
                            ("roll_bnk_maks", "roll_bnk_maks_2010"),
                            ("roll_bnk_medyan", "roll_bnk_medyan_2010"),
                            ("roll_dgr_min", "roll_dgr_min_2010"),
                            ("roll_dgr_maks", "roll_dgr_maks_2010"),
                            ("roll_dgr_medyan", "roll_dgr_medyan_2010"),
                            ("roll_bnk_kapsam_farki",
                             "roll_bnk_kapsam_farki_ort_puan"),
                            ("roll_dgr_kapsam_farki",
                             "roll_dgr_kapsam_farki_ort_puan")):
        koy(anahtar, r.get(kaynak), 1)
    koy("roll_bnk_100_alti_ay", r.get("roll_bnk_100_alti_ay"), 0)
    koy("roll_dgr_100_alti_ay", r.get("roll_dgr_100_alti_ay"), 0)
    koy("roll_ay_sayisi", r.get("roll_bnk_ay"), 0)
    O["roll_kapsam_notu"] = r.get("kapsam_notu")
    O["roll_cumlesi"] = (
        f"Uzun vadeli dış borç çevirme oranı bankalarda %"
        f"{tr_sayi(O.get('roll_bnk'), 1)}, reel sektörde %"
        f"{tr_sayi(O.get('roll_dgr'), 1)}. TCMB'nin kısa+uzun vadeyi kapsayan "
        f"kendi oranı sırasıyla %{tr_sayi(O.get('roll_bnk_tcmb'), 1)} ve %"
        f"{tr_sayi(O.get('roll_dgr_tcmb'), 1)}; fark kapsam farkıdır.")

    # ======================================================= NHN
    n = m.get("nhn", {})
    koy("nhn12_mia_ozet", mia(n.get("nhn12_son")), 1)
    koy("nhn12_min_mia", mia(n.get("nhn12_min")), 1)
    koy("nhn12_maks_mia", mia(n.get("nhn12_maks")), 1)
    O["nhn12_min_donem"] = (ay_ad(n["nhn12_min_donem"])
                            if n.get("nhn12_min_donem") else None)
    O["nhn12_maks_donem"] = (ay_ad(n["nhn12_maks_donem"])
                             if n.get("nhn12_maks_donem") else None)
    koy("nhn_oran", n.get("nhn_oran_son"), 1)
    koy("nhn_yuzdelik36", n.get("nhn_yuzdelik36_son"), 1)
    koy("nhn_yuzdelik_tarihce", n.get("nhn12_yuzdelik_tam_tarihce"), 1)
    koy("nhn_std12_mia", mia(n.get("nhn_std12_son")), 2)
    # YÖN CÜMLELERİ KODDA SEÇİLİR, MDX'E GÖMÜLMEZ. "Tarihçenin en negatif
    # ucuna yakın" ve "o ayın kendisi olağandışı değil" hükümleri yalnız bu
    # koşunun yüzdelik dilimlerinde doğruydu; bir sonraki ayda dilim %95'e
    # çıksa cümle MDX'te aynı kalır ve sessizce yalan olurdu.
    yt = n.get("nhn12_yuzdelik_tam_tarihce")
    if yt is not None:
        O["nhn_konum_cumlesi"] = (
            "tarihçenin en negatif ucuna yakın" if yt <= 10 else
            "tarihçenin negatif yarısında" if yt < 40 else
            "tarihçenin orta bandında" if yt <= 60 else
            "tarihçenin pozitif yarısında" if yt < 90 else
            "tarihçenin en pozitif ucuna yakın")
    y36 = n.get("nhn_yuzdelik36_son")
    if y36 is not None:
        O["nhn_ay_cumlesi"] = (
            "o ayın kendisi olağandışı değil" if y36 <= 80 else
            "o ay son 36 ayın üst dilimlerinde" if y36 <= 95 else
            "o ayın kendisi de olağandışı: son 36 ayın en büyükleri arasında")

    # ======================================================= finansman ihtiyacı
    t = m.get("ihtiyac", {})
    for anahtar, kaynak in (("ihtiyac12_mia", "ihtiyac12_son"),
                            ("cari_acik12_mia", "cari_acik_12ay"),
                            ("uv_anapara12_mia", "uv_anapara_12ay"),
                            ("uv_kullanim12_mia", "uv_kullanim_12ay"),
                            ("uv_net12_mia", "uv_net_12ay"),
                            # A1/A2 = KISA VADE DÂHİL toplam (Şekil 12).
                            ("eb_kullanim12_mia", "eb_kullanim_12ay"),
                            ("eb_odeme12_mia", "eb_odeme_12ay"),
                            ("eb_net12_mia", "eb_net_12ay"),
                            # A11/A21 = YALNIZ uzun vadeli (Şekil 11'in
                            # anapara ve brüt kullanım bacağı). İki kapsam
                            # aynı etiketle sunulunca okur 86,8 milyar USD'lik
                            # anaparayı 5,4 milyar USD şaşarak tutturamıyordu.
                            ("eb_kullanim_uv12_mia", "eb_kullanim_uv_12ay"),
                            ("eb_odeme_uv12_mia", "eb_odeme_uv_12ay"),
                            # Anaparanın sektör bacakları: okur toplamı elle
                            # doğrulayabilsin.
                            ("anapara_bnk12_mia", "anapara_bnk_12ay"),
                            ("anapara_dgr12_mia", "anapara_dgr_12ay"),
                            ("anapara_gh12_mia", "anapara_gh_12ay")):
        koy(anahtar, mia(t.get(kaynak)), 1)
    koy("ihtiyacta_cari_acik_payi", t.get("ihtiyacta_cari_acik_payi_yuzde"), 1)
    O["eurobond_kapsam_notu"] = t.get("eurobond_kapsam_notu")
    O["ihtiyac_kimlik_notu"] = t.get("kimlik_tautoloji_notu")
    O["ihtiyac_cumlesi"] = (
        f"Brüt dış finansman ihtiyacı son 12 ayda "
        f"{tr_sayi(O.get('ihtiyac12_mia'), 1)} milyar USD: "
        f"{tr_sayi(O.get('cari_acik12_mia'), 1)} milyar USD cari açık, "
        f"{tr_sayi(O.get('uv_anapara12_mia'), 1)} milyar USD uzun vadeli "
        "anapara geri ödemesi.")

    # --- KARŞILAŞTIRMA ANAHTARLARI ---------------------------------------
    # Sayfa metnindeki "üç katından fazla", "cari açığın altında kalıyor" gibi
    # ORANSAL hükümler MDX'e gömülüyse, sayı değişince cümle sessizce yanlış
    # olur ve kimse fark etmez (MDX'e dokunulmaz). Karşılaştırmanın kendisi
    # de bir sayıdır ve buradan gelir.
    ih, ca = t.get("ihtiyac12_son"), t.get("cari_acik_12ay")
    if ih is not None and ca:
        koy("ihtiyac_cari_kat", ih / ca, 1)
    fg = b.get("fin_giris12_mn_usd")
    if fg is not None and ca:
        koy("fin_acik_karsilama", fg / ca * 100, 1)
        O["fin_acik_yon"] = ("altında kalıyor" if fg < ca else "üstünde")
    # Uzun vadeli bacağın YÖNÜ: pozitifken "yeni borçlanma", negatifken
    # "net geri ödeme". Cümle bu anahtardan kurulur, elle yazılmaz.
    uvn = t.get("uv_net_12ay")
    if uvn is not None:
        O["uv_net_yon"] = ("net yeni borçlanma" if uvn > 0
                           else "net geri ödeme" if uvn < 0 else "başa baş")
        O["uv_net_cumlesi"] = (
            "uzun vadeli bacak yalnız çevrilmiyor, üstüne yeni borçlanma da "
            "yapılıyor" if uvn > 0 else
            "uzun vadeli bacak tam çevrilemiyor: vadesi gelen anaparanın bir "
            "kısmı yeni borçlanmayla değil kaynakla kapatılıyor" if uvn < 0
            else "uzun vadeli bacak tam olarak çevriliyor")

    # ======================================================= haftalık takvim
    hf = m.get("haftalik", {})
    koy("hafta_odeme_mn", hf.get("son_hafta_mn_usd"), 1)
    koy("hafta_odeme_4h_mn", hf.get("son_4hafta_mn_usd"), 0)
    koy("hafta_odeme_52h_mia", mia(hf.get("son_52hafta_mn_usd")), 1)
    koy("hafta_odeme_hazine_mn", hf.get("son_hafta_hazine_mn_usd"), 1)
    koy("hafta_odeme_diger_mn", hf.get("son_hafta_diger_mn_usd"), 1)
    koy("hafta_odeme_tcmb_mn", hf.get("son_hafta_tcmb_mn_usd"), 1)

    # ======================================================= kimlik/doğrulama
    # SAYIM KURALI: sayılan küme ile YAYIMLANAN küme AYNI olmalı.
    # Eskiden sayım 5 (elle seçilmiş metrik kimliği) + 16 (veri katmanı) = 21
    # yapıyordu, ama uyarilar.json yalnız metrik katmanının 11 kaydını
    # taşıyordu: 16'sı hiçbir yayımlanan dosyada yoktu, 6'sı da sayıma
    # girmiyordu. Okur 21'i doğrulayamıyordu. Artık sayım, uyarilar.json'a
    # yazılan İKİ sözlüğün tamamı üzerinden yapılır ve TAUTOLOJİLER DÜŞÜLÜR:
    # sol tarafı sağdan türetilen bir kayıt hiçbir şeyi sınamaz, "sınandı"
    # diye sayılamaz (kaydı yayımlanır, sayıya girmez).
    D = m.get("dogrulama", {})
    vk = vd.get("kimlik") or {}
    # Sayfa metninin ayrı ayrı andığı kimliklerin anahtarları (n ve sapma).
    kimlikler = {
        "kimlik_bop": "−CA = fin_giris + KA + NHN − Rezerv (aylık)",
        "kimlik_isaret": "fin_giris = yükümlülük oluşumu (net) − yerleşik varlık edinimi",
        "kimlik_cekirdek": "manşet CA(12a) = çekirdek + altın net + enerji net",
        "kimlik_alt_kalem": "CA(12a) = mal + hizmet + birincil + ikincil",
    }
    for anahtar, ad in kimlikler.items():
        r_ = D.get(ad) or {}
        if not r_:
            uyar(f"'{anahtar}' doğrulama kaydı yok — sayfada boş görünecek.")
            continue
        koy(f"{anahtar}_n", r_.get("n"), 0)
        koy(f"{anahtar}_maks_sapma", r_.get("maks_fark"), 3)
        O[f"{anahtar}_gecti"] = bool(r_.get("gecti"))
    gecen = toplam = tautoloji = 0
    for kaynak in (D, vk):
        for ad, r_ in kaynak.items():
            if not isinstance(r_, dict) or "gecti" not in r_:
                continue
            if r_.get("tautoloji"):
                tautoloji += 1
                continue
            toplam += 1
            gecen += 1 if r_.get("gecti") else 0
    O["kimlik_gecen"] = gecen
    O["kimlik_toplam"] = toplam
    O["kimlik_tautoloji"] = tautoloji
    O["kimlik_cumlesi"] = (
        f"Bu koşuda {toplam} denetim çalıştı, {gecen} tanesi geçti"
        if gecen == toplam else
        f"Bu koşuda {toplam} denetim çalıştı ve {toplam - gecen} tanesi DÜŞTÜ")
    O["kimlik_cumlesi"] += (
        f"; ayrıca {tautoloji} sunum tutarlılığı kaydı tautoloji olduğu için "
        "sayıma girmedi." if tautoloji else ".")
    # Şekil 05 ve Şekil 11'in yığın denetimleri (tautoloji YERİNE konan
    # gerçek sınavlar) sayfada ayrıca anılır.
    artik = D.get("artık bandı: Q25 − (Q143+Q157+Q184+Q203) ÷ brüt ciro") or {}
    koy("artik_son_yuzde", artik.get("son_yuzde"), 2)
    koy("artik_maks_yuzde", artik.get("maks_yuzde"), 2)
    koy("artik_esik_yuzde", artik.get("esik_yuzde"), 0)
    mert = D.get("mertebe: UV anapara(12a) ÷ haftalık dış borç ödemesi(52h)") or {}
    koy("uv_hafta_oran", mert.get("son_oran"), 2)
    koy("uv_hafta_bant_alt", (mert.get("bant") or [None, None])[0], 1)
    koy("uv_hafta_bant_ust", (mert.get("bant") or [None, None])[1], 1)
    kopru = vk.get("köprü: Q101(rezerv dahil) = Q13(rezerv hariç) + Q33") or {}
    koy("kopru_n", kopru.get("n"), 0)
    koy("kopru_maks_sapma", kopru.get("maks_fark"), 3)
    isaret = vd.get("isaret_rezerv") or {}
    koy("rezerv_korelasyon", isaret.get("korelasyon"), 3)
    koy("rezerv_ayni_yon", (isaret.get("ayni_yon_orani") or 0) * 100, 1)
    koy("rezerv_isaret_n", isaret.get("n"), 0)
    kiyas = D.get("kıyas: UV çevirme oranı ↔ TCMB ODEROLL (banka)") or {}
    koy("roll_kiyas_fark", kiyas.get("ortalama_mutlak_fark_puan"), 1)
    koy("roll_kiyas_n", kiyas.get("n"), 0)

    # ======================================================= seri/kapsam sayıları
    koy("seri_sayisi_aylik", vd.get("aylik_seri"), 0)
    koy("seri_sayisi_haftalik", vd.get("haftalik_seri"), 0)
    koy("gozlem_aylik", vd.get("aylik_gozlem"), 0)
    O["olu_seri_notu"] = "; ".join(vd.get("olu_seri_hatta_alinmadi") or [])
    tani = vd.get("tani_serileri") or {}
    if tani:
        O["tani_seri_notu"] = " ".join(tani.values())

    # ======================================================= notlar
    for anahtar in ("tanim_notu", "isaret_notu", "kalite_notu", "fisher_not",
                    "revizyon_notu"):
        if m.get(anahtar):
            O[anahtar] = m[anahtar]

    # ======================================================= uyarılar
    uyarilar = list(uy.get("uyarilar", []))
    # SON SAVUNMA: uyarilar.json bir önceki koşudan kalmış ya da metrik katmanı
    # devralmayı atlamış olabilir. veri_durum.json burada da okunur; sayım iki
    # kaynağın BİRLEŞİMİ üzerinden yapılır ki sayfadaki "n uyarı düştü" cümlesi
    # gerçekten düşen uyarı sayısını söylesin.
    for u in (vd.get("uyarilar") or []):
        if u not in uyarilar:
            uyarilar.append(u)

    # ======================================================= TAZELİK BAYRAĞI
    # Yayım gecikmesi aile toleransını aşarsa veri BAYATTIR. Dört ailenin
    # toleransı AYRI: tek eşik her koşuda yanlış alarm üretirdi.
    tol = {"aylik": tazelik_tolerans("aylik"),
           "ceyrek": tazelik_tolerans("ceyrek"),
           "haftalik": tazelik_tolerans("haftalik"),
           "gunluk": tazelik_tolerans("gunluk")}
    O["bayat_tolerans_ay"] = tol["aylik"]
    O["bayat_tolerans_ceyrek"] = tol["ceyrek"]
    O["bayat_tolerans_hafta"] = tol["haftalik"]
    O["bayat_tolerans_gun"] = tol["gunluk"]
    bayat_sebep: list[str] = []
    for ad, anahtar, etiket in (("aylik", "yayim_gecikme_gun", "aylık ödemeler dengesi"),
                                ("ceyrek", "ceyrek_gecikme_gun", "üç aylık GSYH"),
                                ("haftalik", "hafta_gecikme_gun", "haftalık borç ödemeleri"),
                                ("gunluk", "kur_gecikme_gun", "günlük kur")):
        gec = O.get(anahtar)
        if gec is not None and gec > tol[ad]:
            bayat_sebep.append(f"{etiket} {gec} gün geride "
                               f"(tolerans {tol[ad]} gün)")
    izler = [u for u in uyarilar
             if u.startswith(("TAZELİK", "ESKİ ÖNBELLEK", "BAYAT", "SERİ YOK"))]
    if izler:
        bayat_sebep.append(f"veri katmanı {len(izler)} tazelik/önbellek "
                           "uyarısı bastı")
    O["bayat"] = bool(bayat_sebep)
    O["bayat_cumlesi"] = (
        "BAYAT VERİ: " + "; ".join(bayat_sebep)
        + ". Sayfadaki sayılar bu koşuda İLERLEMEMİŞ olabilir."
        if bayat_sebep else
        "Veri taze: dört yayım ritminin dördü de kendi toleransı içinde, "
        "tazelik uyarısı yok.")

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

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · ödemeler dengesi {O['ay']} "
          f"({O['yayim_gecikme_gun']} gün önce) · GSYH {O['ceyrek']} "
          f"({O['ceyrek_gecikme_gun']} gün) · haftalık {O['hafta']} "
          f"({O['hafta_gecikme_gun']} gün)"
          + ("  ! BAYAT" if O.get("bayat") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
