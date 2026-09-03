# -*- coding: utf-8 -*-
"""Merkezi Yönetim Bütçesi & Borç Stoku — ozet.json üretimi.

Sayfa metnindeki OYNAK her sayı buradan beslenir (CLAUDE.md kural 5):
MDX'te `<Deger proje="butce-borc" anahtar="..." ondalik={1}>yedek</Deger>`.
Tarihsel/metodolojik sabitler (formüller, kurum tanımları, doğrulama örnekleri)
sayfada STATİK kalır — onlar veri tazelendikçe değişmez.

Bütün değerler data/ altındaki ÜRETİLMİŞ dosyalardan okunur; elle sayı
yazılmaz. Bir değer kaynakta yoksa anahtar ATLANIR ve stderr'e uyarı basılır —
MDX'teki statik yedek görünür, ama sessizce yanlış bir sayı basılmaz.

ŞEKİL SAATLERİ — hattın figürleri dört ayrı ritimde biter, GrafikEmbed ise açık
anahtar verilmezse hattın tek ana saatini basar. MDX'te `tarihAnahtari` ile
bağlanan anahtarlar:

    sekil02_kisa  → Şekil 02 (yalnız çeyreklik GSYH oranı)
    sekil07_kisa  → Şekil 07 (aylık stok + çeyreklik oran; birleşik damga)
    sekil08_kisa  → Şekil 08 (aylık kompozisyon + haftalık eurobond kırılımı)
    sekil09_kisa  → Şekil 09 (aylık stok çıpası + çeyreklik oran sütunu)
    sekil13_kisa  → Şekil 13 (çeyreklik finansal hesaplar)
    hafta_kisa    → Şekil 10 · 11 (yalnız haftalık menkul kıymet tabloları)

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from veri import PROJE, VERI, AY_TR, TAZELIK, ay_ad, ceyrek_ad, gun_ad

O: dict = {}

# Koşmamış denetimlerin defteri. Boş bırakılırsa sayfa "%0,0 fark" basar — yani
# hiç koşmamış bir denetim MÜKEMMEL UYUM olarak görünür (sessiz sıfır sınıfı).
EKSIK_DENETIM: list[str] = []


def uyar(m: str) -> None:
    print(f"UYARI: {m}", file=sys.stderr)


def koy_denetim(anahtar: str, deger, ondalik: int, sinav: str) -> None:
    """DENETİM çıktısı için koy(). 'or 0' kalıbı burada YASAKTIR.

    Bir denetim koşmadıysa değeri 0,0'a çevirmek sayfada "%0,0 fark" yazdırır;
    bu, okurun görebileceği EN GÜÇLÜ onay cümlesidir ve tam tersini anlatır.
    Değer yoksa anahtar ATLANIR (MDX'teki statik yedek görünür) ve uyarı düşer.
    """
    if deger is None or (isinstance(deger, float) and pd.isna(deger)):
        # Defter SINAV başına tutulur (anahtar başına değil): bir denetim üç
        # anahtar üretiyorsa uyarı cümlesi üç kez tekrarlanmasın.
        m = f"DOĞRULAMA KOŞMADI: {sinav}."
        print(f"UYARI: {m} ('{anahtar}' üretilmedi.)", file=sys.stderr)
        if m not in EKSIK_DENETIM:
            EKSIK_DENETIM.append(m)
        return
    koy(anahtar, deger, ondalik)


def tr_sayi(v, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi (binlik nokta, ondalık virgül, eksi U+2212).

    ozet.json'daki METİN anahtarları (kapsam/uyarı cümleleri) sayfaya olduğu
    gibi basılır; Python'un varsayılan `repr`i oraya "0.0" ve "13353.29" gibi
    İngilizce biçimler taşırdı.
    """
    if v is None:
        return "—"
    try:
        m = f"{float(v):,.{ondalik}f}"
    except (TypeError, ValueError):
        return str(v)
    return (m.replace(",", " ").replace(".", ",").replace(" ", ".")
             .replace("-", "−"))


def tr_yuzde(v, ondalik: int = 1) -> str:
    """İşaret yüzde iminin ÖNÜNE gelir: "−%8,2" ("%−8,2" değil)."""
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return ("−" if f < 0 else "") + "%" + tr_sayi(abs(f), ondalik)


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
    s = pd.Series(s).dropna()
    return (float(s.iloc[-1]), s.index[-1]) if len(s) else (None, None)


def tr_tarih(t) -> str:
    t = pd.Timestamp(t)
    return f"{t.day:02d}.{t.month:02d}.{t.year}"


def tr_ay(t) -> str:
    """AYLIK çıpa için "06.2026". Aylık damga ay BAŞINA oturuyor; gün
    yazılırsa ("01.06.2026") okur o güne ait bir gözlem sanır."""
    t = pd.Timestamp(t)
    return f"{t.month:02d}.{t.year}"


def _seri(df: pd.DataFrame, kol: str) -> pd.Series:
    return df[kol] if kol in df.columns else pd.Series(dtype=float)


def _bacak_ucu(df: pd.DataFrame, kolonlar) -> "pd.Timestamp | None":
    """Bir figür BACAĞININ ucu: çizilen sütunların son geçerli gözlemlerinin
    EN ESKİSİ.

    Neden en eski: bacağın sözü serilerin KIYASIDIR ve kıyas ancak hepsinin
    ölçüldüğü güne kadar kurulabilir. Yapısal yazılır — bugün hangi sütunun
    daha uzun olduğuna bakmaz.

    Kolon yoksa ya da hepsi boşsa None döner: o zaman damga YAZILMAZ ve sayfa
    o şeklin altına tarih hiç basmaz. Yanlış bir tarih, tarihsizlikten kötüdür.
    """
    uclar = []
    for k in kolonlar:
        sr = _seri(df, k).dropna()
        if len(sr):
            uclar.append(sr.index[-1])
    return min(uclar) if uclar else None


def main() -> int:
    M = pd.read_csv(VERI / "aylik_metrik.csv", index_col=0, parse_dates=True)
    C = pd.read_csv(VERI / "ceyreklik_metrik.csv", index_col=0, parse_dates=True)
    H = pd.read_csv(VERI / "haftalik_metrik.csv", index_col=0, parse_dates=True)
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    vd = json.loads((VERI / "veri_durum.json").read_text(encoding="utf-8"))
    uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))

    s_ay = pd.Timestamp(m["son_ay"])
    s_ceyrek = pd.Timestamp(m["son_ceyrek"])
    s_dis = pd.Timestamp(m["son_dis_ceyrek"])
    s_hafta = pd.Timestamp(m["son_hafta"])
    s_gun = pd.Timestamp(m["son_gun"])
    bugun = pd.Timestamp.today().normalize()

    # ===================================================== dönem çıpaları
    # "_tarih" hattın BAŞROL dönemidir: bütçe ayı. İkinci ve üçüncü frekanslar
    # ayrı anahtarlarla taşınır — sayfada hangi cümlenin hangi tarihe
    # çıpalandığı okunabilsin.
    O["_tarih"] = tr_ay(s_ay)
    O["_tarih2"] = tr_tarih(s_hafta)          # haftalık menkul kıymet bacağı
    O["_tarih3"] = ceyrek_ad(s_ceyrek)        # üç aylık GSYH / finansal hesap
    O["ay"] = ay_ad(s_ay)
    O["ay_kisa"] = tr_ay(s_ay)
    O["ay_ad"] = AY_TR[s_ay.month]
    O["yil"] = int(s_ay.year)
    O["ceyrek"] = ceyrek_ad(s_ceyrek)
    O["dis_ceyrek"] = ceyrek_ad(s_dis)
    O["hafta"] = gun_ad(s_hafta)
    O["hafta_kisa"] = tr_tarih(s_hafta)
    O["kur_gun"] = gun_ad(s_gun)
    O["kosum_tarihi"] = tr_tarih(bugun)
    # Yayım gecikmesi DUVAR SAATİNE göre. Verinin kendi son gününü referans
    # almak denetimi kendi kendine referanslı yapar.
    koy("gecikme_butce_gun", (bugun - s_ay).days, 0)
    koy("gecikme_hafta_gun", (bugun - s_hafta).days, 0)
    koy("gecikme_ceyrek_gun", (bugun - s_ceyrek).days, 0)
    koy("gecikme_dis_gun", (bugun - s_dis).days, 0)
    koy("gecikme_kur_gun", (bugun - s_gun).days, 0)

    # ===================================================== bütçe: düzeyler
    for ad, kol, ond in (
            ("denge_12a", "denge_12a", 2), ("fdd_12a", "fdd_12a", 2),
            ("gelir_12a", "gelir_12a", 2), ("gider_12a", "gider_12a", 2),
            ("fdg_12a", "fdg_12a", 2), ("faiz_12a", "faiz_12a", 2),
            ("vergi_12a", "vergi_12a", 2),
            ("gb_denge_12a", "gb_denge_12a", 2),
            ("denge_ay", "denge_ay", 1), ("fdd_ay", "fdd_ay", 1),
            ("gelir_ay", "gelir_ay", 1), ("gider_ay", "gider_ay", 1),
            ("faiz_ay", "faiz_ay", 1)):
        v, t = son(_seri(M, kol))
        koy(ad, v, ond)
    O["denge_isaret"] = ("açık" if (O.get("denge_12a") or 0) < 0 else "fazla")
    O["fdd_isaret"] = ("açık" if (O.get("fdd_12a") or 0) < 0 else "fazla")
    koy("denge_12a_mutlak", abs(O.get("denge_12a") or 0), 2)
    koy("fdd_12a_mutlak", abs(O.get("fdd_12a") or 0), 2)

    # ===================================================== bütçe: reel
    for ad, kol in (("reel_gelir_12a", "reel_gelir_12a"),
                    ("reel_fdg_12a", "reel_fdg_12a"),
                    ("reel_faiz_12a", "reel_faiz_12a"),
                    ("reel_vergi_12a", "reel_vergi_12a")):
        v, _ = son(_seri(M, kol))
        koy(ad, v, 2)
    for ad, kol in (("gelir_reel_yy", "gelir_reel_yy"),
                    ("fdg_reel_yy", "fdg_reel_yy"),
                    ("gider_reel_yy", "gider_reel_yy"),
                    ("faiz_reel_yy", "faiz_reel_yy"),
                    ("vergi_reel_yy", "vergi_reel_yy"),
                    ("gelir_nom_yy", "gelir_nom_yy"),
                    ("fdg_nom_yy", "fdg_nom_yy"),
                    ("faiz_nom_yy", "faiz_nom_yy"),
                    ("vergi_nom_yy", "vergi_nom_yy")):
        v, _ = son(_seri(M, kol))
        koy(ad, v, 1)
    # TÜFE VİNTAJI. `son()` en son DOLU gözlemi alır; TÜFE bütçeden bir ay
    # ÖNDE yayımlandığı için bu, sayfanın anlattığı bütçe ayından farklı bir
    # aya çıpalanır. Bütün reel/Fisher hesapları bütçe ayının TÜFE'sini
    # kullandığından sayfada iki ayrı enflasyon sayısı dolaşırdı.
    if "tufe_yy" in M.columns and s_ay in M.index:
        koy("tufe_yy", float(M.loc[s_ay, "tufe_yy"]), 1)     # BÜTÇE ayına pinli
    else:
        uyar("tufe_yy bütçe ayına çıpalanamadı — anahtar atlandı.")
    v_manset, t_manset = son(_seri(M, "tufe_yy"))            # son yayımlanan ay
    koy("tufe_yy_manset", v_manset, 1)
    O["deflator_taban"] = m["butce"]["deflator_taban_ay"]
    koy("deflator_taban_endeks", m["butce"].get("deflator_taban_endeks"), 2)
    O["tufe_son_ay"] = m["butce"].get("tufe_son_ay")
    # Sayfada takvim ayı ELLE yazılmasın diye TÜFE ayının Türkçe adı.
    try:
        O["tufe_son_ay_ad"] = AY_TR[pd.Timestamp(O["tufe_son_ay"]).month]
    except Exception:
        uyar("tufe_son_ay_ad üretilemedi — anahtar atlandı.")
    # Fisher: aynı veriden basit çıkarmayla kaç puan farklı bir sayı çıkardı.
    koy("fisher_basit_fark_pp",
        m["butce"]["fisher"].get("basit_cikarma_farki_son_pp"), 2)
    O["fisher_notu"] = m["butce"]["fisher"]["not"]
    # Reel ile nominalin makası — sayfanın ana cümlesi bu farkın üstüne kurulur.
    if O.get("gelir_nom_yy") is not None and O.get("gelir_reel_yy") is not None:
        koy("gelir_makas_pp", O["gelir_nom_yy"] - O["gelir_reel_yy"], 1)
    # 12 AYLIK BİRİKİMLİ SERİNİN KENDİ DEFLATÖRÜ. Manşet TÜFE (tek ayın y/y'si)
    # bu serinin deflatörü DEĞİLDİR: 12 aylık birikimli reel seri, on iki ayrı
    # aylık deflatörün ağırlıklı bileşimini taşır. Şekil 03 tablosunda nominal
    # ve reel satırların yanında duran sayı bu olmalı — özdeşlikten türetilir:
    #   (1 + nominal) / (1 + reel) − 1
    if (O.get("gelir_nom_yy") is not None and O.get("gelir_reel_yy") is not None
            and O["gelir_reel_yy"] != -100):
        koy("deflator_12a_yy",
            ((1 + O["gelir_nom_yy"] / 100) / (1 + O["gelir_reel_yy"] / 100) - 1) * 100, 1)

    # ===================================================== kompozisyon
    for kol in ("pay_v_gelir", "pay_v_kurumlar", "pay_v_kdv_dahil",
                "pay_v_kdv_ithal", "pay_v_otv", "pay_v_damga", "pay_v_diger",
                "pay_personel", "pay_sgk_primi", "pay_mal_hizmet",
                "pay_cari_transfer", "pay_sermaye_gider",
                "pay_sermaye_transfer", "pay_borc_verme", "pay_faiz",
                "pay_gider_diger"):
        v, _ = son(_seri(M, kol))
        koy(kol, v, 1)
    for kol in ("v_gelir", "v_kurumlar", "v_kdv_dahil", "v_kdv_ithal",
                "v_otv", "v_damga", "personel", "sgk_primi", "mal_hizmet",
                "cari_transfer", "sermaye_gider", "sermaye_transfer",
                "borc_verme"):
        v, _ = son(_seri(M, f"{kol}_reel_yy"))
        koy(f"{kol}_reel_yy", v, 1)
        v2, _ = son(_seri(M, f"{kol}_12a"))
        koy(f"{kol}_12a", v2, 2)

    # ===================================================== faiz yükü
    for ad, kol, ond in (("faiz_vergi", "faiz_vergi", 1),
                         ("faiz_gelir", "faiz_gelir", 1),
                         ("faiz_ic_12a", "faiz_ic_12a", 2),
                         ("faiz_dis_12a", "faiz_dis_12a", 2),
                         ("faiz_kira_12a", "faiz_kira_12a", 2),
                         ("faiz_iskonto_12a", "faiz_iskonto_12a", 2),
                         ("ima_faiz_nominal", "ima_faiz_nominal", 1),
                         ("ima_faiz_reel", "ima_faiz_reel", 1),
                         ("ima_faiz_reel_basit", "ima_faiz_reel_basit", 1)):
        v, _ = son(_seri(M, kol))
        koy(ad, v, ond)
    if O.get("faiz_ic_12a") and O.get("faiz_12a"):
        koy("faiz_ic_pay", O["faiz_ic_12a"] / O["faiz_12a"] * 100, 1)
        koy("faiz_dis_pay", (O.get("faiz_dis_12a") or 0) / O["faiz_12a"] * 100, 1)
    koy("fisher_ima_faiz_fark_pp", m["stok"].get("fisher_ima_faiz_fark_son_pp"), 2)
    O["fisher_ima_faiz_notu"] = m["stok"].get("fisher_ima_faiz_notu")

    # ===================================================== borç stoku
    # STOK BLOĞU TEK BİR AYA ÇIPALIDIR. Bacaklar farklı frekanslardan gelir —
    # iç borç aylık, eurobond haftalık (bir ay ileride bitiyor), dış kredi üç
    # aylık. Her bacağı kendi son dolu gözleminden almak, TOPLAMI TUTMAYAN bir
    # tablo üretirdi: sayfada iç + senet + kredi ≠ toplam görünürdü.
    _stok_s = _seri(M, "toplam_borc_trl").dropna()
    t_stok = _stok_s.index[-1] if len(_stok_s) else None
    for ad, kol, ond in (("ic_borc_trl", "ic_borc_trl", 2),
                         ("dis_borc_trl", "dis_borc_trl", 2),
                         ("dis_senet_trl", "dis_senet_trl", 2),
                         ("dis_kredi_trl", "dis_kredi_trl", 2),
                         ("doviz_borc_trl", "doviz_borc_trl", 2),
                         ("toplam_borc_trl", "toplam_borc_trl", 2),
                         ("eski_tanim_trl", "eski_tanim_trl", 2),
                         ("doviz_pay", "doviz_pay", 1),
                         ("yurt_disi_pay", "yurt_disi_pay", 1),
                         ("dis_borc_musd", "dis_borc_musd", 0),
                         ("dis_senet_musd", "dis_senet_musd", 0),
                         ("dis_kredi_musd", "dis_kredi_musd", 0),
                         ("dibs_yurtdisi_trl", "dibs_yurtdisi_trl", 2),
                         ("eb_yurtici_net_trl", "eb_yurtici_net_trl", 2),
                         ("eb_kendi_trl", "eb_kendi_trl", 2),
                         ("pay_ic_satis_doviz", "pay_ic_satis_doviz", 1),
                         ("pay_ic_odeme_doviz", "pay_ic_odeme_doviz", 1),
                         ("ic_tahvil_trl", "ic_tahvil_trl", 2),
                         ("ic_bono_trl", "ic_bono_trl", 2)):
        if t_stok is not None and kol in M.columns:
            v = M.loc[t_stok, kol]
        else:
            v, _ = son(_seri(M, kol))
        koy(ad, v, ond)
    # Kur ise BİLEREK en güncel ay sonu değeridir: sayfa bunu "stokun kuru
    # DEĞİLDİR" uyarısında kullanıyor. Stokun değerlendiği kur senaryo
    # bloğunda (senaryo_kur) ayrı anahtarla veriliyor.
    koy("kur_ay", son(_seri(M, "kur_ay"))[0], 4)
    for ad, kaynak in (("dis_borc_mlrusd", "dis_borc_musd"),
                       ("dis_senet_mlrusd", "dis_senet_musd"),
                       ("dis_kredi_mlrusd", "dis_kredi_musd")):
        if O.get(kaynak):
            koy(ad, O[kaynak] / 1000, 1)
    # TL bacağı = iç borç bacağı. Bu bacak SAF TL DEĞİLDİR: içinde
    # ayrıştırılamayan döviz cinsi yurt içi ihraç da vardır — bu yüzden
    # "TL payı" bir ÜST SINIRDIR ve sayfada öyle etiketlenir.
    if O.get("doviz_pay") is not None:
        koy("tl_pay", 100 - O["doviz_pay"], 1)
    O["stok_son_ay"] = m["stok"].get("birlesik_stok_son_ay")
    O["stok_ilk_ay"] = m["stok"].get("birlesik_stok_ilk_ay")
    O["doviz_payi_notu"] = m["stok"].get("doviz_payi_notu")
    O["yurt_disi_payi_notu"] = m["stok"].get("yurt_disi_payi_notu")
    O["stok_tanim_notu"] = m["stok"].get("stok_tanim_notu")
    # Tanım düzeltmesinin büyüklüğü — sayfa bunu ELLE değil buradan yazar.
    bil = m["stok"].get("stok_bilesen") or {}
    koy("stok_cift_sayim_trl", bil.get("cift_sayilan_dibs_trl"), 2)
    koy("stok_eksik_eurobond_trl", bil.get("eksik_eurobond_trl"), 2)
    koy("stok_duzeltme_yuzde", bil.get("duzeltme_yuzde"), 1)

    # ===================================================== GSYH oranları
    for ad, kol in (("denge_gsyh", "denge_gsyh"), ("fdd_gsyh", "fdd_gsyh"),
                    ("faiz_gsyh", "faiz_gsyh"), ("gelir_gsyh", "gelir_gsyh"),
                    ("gider_gsyh", "gider_gsyh"), ("vergi_gsyh", "vergi_gsyh"),
                    ("stok_gsyh", "stok_gsyh"), ("net_stok_gsyh", "net_stok_gsyh"),
                    ("net_fin_deger_gsyh", "net_fin_deger_gsyh")):
        v, t = son(_seri(C, kol))
        koy(ad, v, 2)
    v, t = son(_seri(C, "gsyh_yil_trl"))
    koy("gsyh_yil_trl", v, 1)
    if t is not None:
        O["oran_ceyregi"] = ceyrek_ad(t)
    for ad, kol in (("net_fin_deger_trl", "net_fin_deger_trl"),
                    ("yukum_toplam_trl", "yukum_toplam_trl"),
                    ("varlik_toplam_trl", "varlik_toplam_trl"),
                    ("nakit_trl", "nakit_trl"),
                    ("borc_senedi_trl", "borc_senedi_trl"),
                    ("krediler_trl", "krediler_trl"),
                    ("fh_borc_trl", "fh_borc_trl"),
                    ("net_stok_trl", "net_stok_trl")):
        v, _ = son(_seri(C, kol))
        koy(ad, v, 2)
    koy("fh_borc_gsyh", son(_seri(C, "fh_borc_gsyh"))[0], 2)
    # ORAN ÇEYREĞİNE ÇIPALI stok. `son()` kullanılsaydı stok serisi GSYH'den
    # bir çeyrek ileri gittiği için bu sayı Şekil 07'nin aylık stokuyla
    # ÖZDEŞLEŞİR ve sayfanın "iki farklı çeyrek" açıklaması yalan olurdu.
    if t is not None and "stok_trl" in C.columns and t in C.index:
        koy("stok_ceyrek_trl", float(C.loc[t, "stok_trl"]), 2)
    else:
        koy("stok_ceyrek_trl", son(_seri(C, "stok_trl"))[0], 2)
    # BRÜT DIŞ BORÇ TABLOSU KENDİ ÇEYREĞİNE ÇIPALIDIR. GSYH'ye kelepçelenirse
    # yayımlanmış çeyrek sessizce düşer ve sayfada aynı seri iki farklı sayıyla
    # geçer (yukarıda 2026-Ç2, tabloda 2026-Ç1).
    for ad, kol in (("db_toplam_mlrusd", "db_toplam_mlrusd"),
                    ("db_my_mlrusd", "db_my_mlrusd"),
                    ("db_my_kisa_mlrusd", "db_my_kisa_mlrusd"),
                    ("db_my_uzun_mlrusd", "db_my_uzun_mlrusd"),
                    ("db_ozel_mlrusd", "db_ozel_mlrusd"),
                    ("db_tcmb_mlrusd", "db_tcmb_mlrusd")):
        v, t_db = son(_seri(C, kol))
        koy(ad, v, 1)
    _db_q = m["ceyrek"].get("db_son_ceyrek")
    if _db_q:
        O["db_ceyregi"] = ceyrek_ad(pd.Timestamp(_db_q))
    O["oran_gecikme_notu"] = m["ceyrek"].get("oran_gecikme_notu")

    # ===================================================== çevirme oranı
    cev = m["stok"].get("cevirme") or {}
    koy("cevirme", cev.get("son"), 0)
    koy("cevirme_faiz", cev.get("son_faiz_dahil"), 0)
    koy("cevirme_bant_min", cev.get("bant_5y_min"), 0)
    koy("cevirme_bant_max", cev.get("bant_5y_max"), 0)
    O["cevirme_notu"] = cev.get("not")
    for ad, kol, ond in (("ic_satis_12a", "ic_satis_12a", 2),
                         ("ic_odeme_12a", "ic_odeme_12a", 2),
                         ("ic_borclanma_net_ay", "ic_borclanma_net_ay", 1),
                         ("dis_borclanma_net_ay", "dis_borclanma_net_ay", 1)):
        v, _ = son(_seri(M, kol))
        koy(ad, v, ond)

    # ===================================================== stok ayrıştırması
    ayr = m["stok"].get("ayrıstirma") or {}
    for ad, kol in (("ayr_d_stok", "ayr_d_stok"),
                    ("ayr_net_borclanma", "ayr_net_borclanma"),
                    ("ayr_kur_farki", "ayr_kur_farki"),
                    ("ayr_artik", "ayr_artik")):
        ort = M[["ayr_d_stok", "ayr_net_borclanma", "ayr_kur_farki",
                 "ayr_artik"]].dropna()
        v = float(ort[kol].iloc[-1]) if len(ort) else None
        koy(ad, v, 2)
        if len(ort) and ad == "ayr_d_stok":
            O["ayr_donem"] = ay_ad(ort.index[-1])
    _ap = ayr.get("artik_pay_son")
    koy_denetim("ayr_artik_pay", None if _ap is None else _ap * 100, 1,
                "stok ayrıştırması (Δstok = net borçlanma + kur farkı + artık)")
    O["ayr_notu"] = ayr.get("not")

    # ===================================================== haftalık: sahiplik & vade
    for ad, kol in (("pay_dibs_tcmb", "pay_dibs_tcmb"),
                    ("pay_dibs_bankalar", "pay_dibs_bankalar"),
                    ("pay_dibs_fonlar", "pay_dibs_fonlar"),
                    ("pay_dibs_yurtdisi", "pay_dibs_yurtdisi"),
                    ("pay_dibs_diger_yurtici", "pay_dibs_diger_yurtici"),
                    ("pay_dibs_kv_kisa", "pay_dibs_kv_kisa"),
                    ("pay_dibs_ov_kisa", "pay_dibs_ov_kisa"),
                    ("pay_eb_kv_kisa", "pay_eb_kv_kisa"),
                    ("pay_eb_yurtdisi", "pay_eb_yurtdisi"),
                    ("pay_eb_kendi", "pay_eb_kendi"),
                    ("pay_eb_usd", "pay_eb_usd"), ("pay_eb_eur", "pay_eb_eur"),
                    ("pay_eb_jpy", "pay_eb_jpy")):
        v, _ = son(_seri(H, kol))
        koy(ad, v, 1)
    for ad, kol, ond in (("dibs_toplam_trl", "dibs_toplam_trl", 2),
                         ("dibs_pd_trl", "dibs_pd_trl", 2),
                         ("eb_toplam_mlrusd", "eb_toplam_mlrusd", 1),
                         ("eb_pd_mlrusd", "eb_pd_mlrusd", 1),
                         ("dibs_piyasa_yazili_oran", "dibs_piyasa_yazili_oran", 3)):
        v, _ = son(_seri(H, kol))
        koy(ad, v, ond)
    O["vade_notu"] = m["haftalik"].get("vade_notu")
    O["sahiplik_notu"] = m["haftalik"].get("sahiplik_notu")
    O["eb_toplam_notu"] = (m["haftalik"].get("eb_toplam_farki") or {}).get("not")

    # ===================================================== kur duyarlılığı
    sen = m.get("senaryo") or {}
    koy("senaryo_kur", sen.get("kur"), 4)
    koy("senaryo_stok_trl", sen.get("toplam_trl"), 2)
    O["senaryo_cipa_ay"] = sen.get("cipa_ay")
    O["senaryo_cipa_ceyrek"] = sen.get("cipa_ceyrek")
    O["senaryo_notu"] = sen.get("not")
    for a in ("usd", "eur", "jpy"):
        koy(f"agirlik_{a}", (sen.get("agirlik") or {}).get(a, 0) * 100, 1)
    # Her şok düzeyi ayrı anahtar: sayfa metni "+%10'luk bir kur şoku stoku
    # şu kadar büyütür" cümlesini ELLE değil buradan kurar.
    for r in sen.get("satirlar", []):
        # Anahtar adı MDX'te ELLE yazılacak; okunur olsun:
        #   sok_eksi10 · sok_0 · sok_arti10 …
        yuzde = int(round(r["sok"] * 100))
        anahtar = ("sok_0" if yuzde == 0 else
                   f"sok_{'arti' if yuzde > 0 else 'eksi'}{abs(yuzde)}")
        koy(f"{anahtar}_kur", r["kur"], 2)
        koy(f"{anahtar}_stok_trl", r["stok_paralel_trl"], 2)
        koy(f"{anahtar}_degisim", r["degisim_paralel_yuzde"], 1)
        koy(f"{anahtar}_stok_yalniz_usd_trl", r["stok_yalniz_usd_trl"], 2)
        if "stok_gsyh_paralel" in r:
            koy(f"{anahtar}_stok_gsyh", r["stok_gsyh_paralel"], 1)
    # +%10 senaryosu sayfanın ana örneğidir; okunması kolay bir ad da verilir.
    if "sok_arti10_stok_trl" in O:
        koy("sok10_stok_trl", O["sok_arti10_stok_trl"], 2)
        koy("sok10_degisim", O.get("sok_arti10_degisim"), 1)
        if O.get("sok_arti10_stok_gsyh") is not None and O.get("stok_gsyh") is not None:
            koy("sok10_gsyh_puan", O["sok_arti10_stok_gsyh"] - O["stok_gsyh"], 2)

    # ===================================================== şekil saatleri
    # HATTIN SAATİ, ŞEKLİN SAATİ DEĞİLDİR. GrafikEmbed açık bir anahtar
    # verilmemişse hattın TEK ana saatini (`_tarih`, bütçe ayı) basar; bu hattın
    # figürleri ise DÖRT ayrı ritimde: aylık bütçe/stok, haftalık menkul kıymet
    # tabloları, çeyreklik GSYH oranları ve çeyreklik finansal hesaplar. Tek
    # damga iki yönde birden yalan söylüyordu — haftalık paneller iki buçuk ay
    # eski görünüyor, çeyreklik paneller üç ay taze görünüyordu.
    #
    # Değerler TÜRETİLMEZ, figürün ÇİZDİĞİ sütunlardan ölçülür; MDX'te
    # `tarihAnahtari` ile bağlanır. İki ritmi birden taşıyan figürde tek bir uç
    # seçmek öbür panel hakkında yalan olurdu, o yüzden BİRLEŞİK damga yazılır
    # (bileşen tanımadığı dizgeyi olduğu gibi basar; sayfa sınavı 18b içindeki
    # her tarihi ayrıca sınar).
    #
    #   Şekil 02 — yalnız çeyreklik GSYH oranları
    #   Şekil 07 — aylık stok düzeyi + çeyreklik stok/GSYH
    #   Şekil 08 — aylık para kompozisyonu + haftalık eurobond kırılımı
    #   Şekil 09 — aylık stok çıpası + çeyreklik stok/GSYH sütunu
    #   Şekil 13 — çeyreklik finansal hesaplar (GSYH ailesinden AYRI yayımlanır)
    #   Şekil 10 · 11 — yalnız haftalık: `hafta_kisa` yeter, yeni anahtar yok.
    _u02 = _bacak_ucu(C, ("denge_gsyh", "fdd_gsyh", "faiz_gsyh"))
    if _u02 is not None:
        O["sekil02_kisa"] = tr_tarih(_u02)
    else:
        uyar("'sekil02_kisa' ölçülemedi — Şekil 02 hattın aylık saatiyle "
             "damgalanır ve çeyreklik panel olduğundan taze görünür.")
    _u07a = _bacak_ucu(M, ("ic_borc_trl", "dis_senet_trl", "dis_kredi_trl",
                           "toplam_borc_trl"))
    _u07c = _bacak_ucu(C, ("stok_gsyh", "net_stok_gsyh", "fh_borc_gsyh"))
    if _u07a is not None and _u07c is not None:
        O["sekil07_kisa"] = f"aylık {tr_ay(_u07a)} · çeyreklik {tr_tarih(_u07c)}"
    else:
        uyar("'sekil07_kisa' ölçülemedi — Şekil 07 hattın ana saatiyle damgalanır.")
    _u08a = _bacak_ucu(M, ("doviz_pay", "yurt_disi_pay", "pay_ic_satis_doviz"))
    _u08h = _bacak_ucu(H, ("pay_eb_usd", "pay_eb_eur", "pay_eb_jpy"))
    if _u08a is not None and _u08h is not None:
        O["sekil08_kisa"] = f"aylık {tr_ay(_u08a)} · haftalık {tr_tarih(_u08h)}"
    else:
        uyar("'sekil08_kisa' ölçülemedi — Şekil 08 hattın ana saatiyle damgalanır.")
    # Şekil 09'un yatay ekseni TARİH DEĞİL (USD/TRY düzeyi); çerçevenin ucu
    # senaryonun kendi çıpalarıdır ve ikisi de ölçüm katmanında ölçülür.
    _s09a, _s09c = sen.get("cipa_ay"), sen.get("cipa_ceyrek")
    if _s09a and _s09c:
        O["sekil09_kisa"] = (f"aylık {tr_ay(pd.Timestamp(_s09a))} · "
                             f"çeyreklik {tr_tarih(pd.Timestamp(_s09c))}")
    elif _s09a:
        O["sekil09_kisa"] = tr_ay(pd.Timestamp(_s09a))
    else:
        uyar("'sekil09_kisa' ölçülemedi — Şekil 09 hattın ana saatiyle damgalanır.")
    # Finansal hesaplar GSYH oranlarından AYRI bir yayım ailesidir; ikisi bugün
    # aynı çeyrekte bitiyor ama ayrışabilirler, o yüzden ayrı ölçülür.
    # LİSTE FİGÜRÜN ÇİZDİĞİ BÜTÜN SÜTUNLARI SAYAR — alt paneldeki iki stok
    # düzeyi (brüt · net) dahil. Bugün ikisi de min'i değiştirmiyor (brüt bir
    # çeyrek İLERİDE, net aynı çeyrekte bitiyor) ama min yapısal yazılır:
    # bugünkü sıralamaya göre eksik bırakılan bir bacak, sıralama döndüğü gün
    # damgayı sessizce taze gösterir.
    _u13 = _bacak_ucu(C, ("yukum_toplam_trl", "varlik_toplam_trl",
                          "net_fin_deger_trl", "borc_senedi_trl", "nakit_trl",
                          "stok_trl", "net_stok_trl"))
    if _u13 is not None:
        O["sekil13_kisa"] = tr_tarih(_u13)
    else:
        uyar("'sekil13_kisa' ölçülemedi — Şekil 13 hattın aylık saatiyle "
             "damgalanır ve çeyreklik panel olduğundan taze görünür.")

    # ===================================================== kapsam ve doğrulama
    _kf = m["butce"].get("kapsam_farki_24ay")
    koy_denetim("kapsam_farki", None if _kf is None else _kf * 100, 1,
                "merkezi yönetim dengesi ↔ genel bütçe dengesi kapsam farkı")
    O["kapsam_notu"] = m.get("kapsam_notu")
    O["eksik_veri_notu"] = m.get("eksik_veri_notu")
    d = m.get("dogrulama") or {}

    def _bant(anahtar_on: str, sinav: str, ondalik: int = 1) -> None:
        r = d.get(sinav) or {}
        koy_denetim(f"{anahtar_on}_fark",
                    None if r.get("son_fark") is None else r["son_fark"] * 100,
                    ondalik, sinav)
        koy_denetim(f"{anahtar_on}_bant_min",
                    None if r.get("son6_min") is None else r["son6_min"] * 100,
                    ondalik, sinav)
        koy_denetim(f"{anahtar_on}_bant_max",
                    None if r.get("son6_max") is None else r["son6_max"] * 100,
                    ondalik, sinav)

    _bant("f34", "Toplam stok ↔ finansal hesaplar F.3+F.4")
    _bant("f3", "DİBS+eurobond ↔ finansal hesaplar F.3")
    _bant("f4", "Dış kredi artığı ↔ finansal hesaplar F.4")
    for a_ in ("f34_fark", "f3_fark", "f4_fark"):
        if O.get(a_) is not None:
            koy(f"{a_}_mutlak", abs(O[a_]), 1)

    # PAYDA BEKLENEN DENETİM LİSTESİNDEN gelir, sözlüğün uzunluğundan DEĞİL.
    # Sözlükten alınsaydı bir denetim hiç koşmadığında payda da küçülür
    # (5/5 → 4/4) ve eksilme sayfada GÖRÜNMEZDİ.
    beklenen = list(m.get("dogrulama_beklenen") or d.keys())
    kosmayan = [ad for ad in beklenen if ad not in d]
    for ad in kosmayan:
        mm = f"DOĞRULAMA KOŞMADI: {ad}."
        uyar(mm)
        if mm not in EKSIK_DENETIM:
            EKSIK_DENETIM.append(mm)
    O["dogrulama_sayisi"] = len(beklenen)
    O["dogrulama_gecen"] = sum(1 for ad in beklenen
                               if (d.get(ad) or {}).get("gecti"))
    O["dogrulama_kosmayan"] = len(kosmayan)
    O["dogrulama_cumlesi"] = (
        f"{O['dogrulama_gecen']}/{O['dogrulama_sayisi']} bağımsız doğrulama geçti."
        + (f" {len(kosmayan)} denetim bu koşuda HİÇ KOŞMADI." if kosmayan else "")
        if O["dogrulama_sayisi"] else "Bu koşuda bağımsız doğrulama koşmadı.")

    # Birim denetimi — sayfada "birim EVDS'ten okunur" cümlesinin kanıtı.
    birim = vd.get("birim") or {}
    O["birim_denetim_sayisi"] = len(birim)
    O["birim_denetim_gecen"] = sum(1 for r in birim.values() if r.get("uyusuyor"))
    O["birim_cumlesi"] = (
        f"Birim, EVDS'in veri grubu kataloğundan okunur ve her koşuda kodda "
        f"yazılıyla karşılaştırılır: {O['birim_denetim_gecen']}/"
        f"{O['birim_denetim_sayisi']} veri grubunda uyuşuyor.")
    kim = vd.get("kimlik") or {}
    O["kimlik_sayisi"] = len(kim)
    O["kimlik_gecen"] = sum(1 for r in kim.values() if r.get("gecti"))

    # ===================================================== tazelik bayrağı
    uyarilar: list[str] = list(uy.get("uyarilar") or [])
    for u in (vd.get("uyarilar") or []):
        if u not in uyarilar:
            uyarilar.append(u)

    # Aile bazlı bayat denetimi. Tek eşik bu hatta ANLAMSIZ: kur 2 günde,
    # GSYH 145 günde gelir ve ikisi de normaldir.
    aile_gecikme = {
        "butce": (O.get("gecikme_butce_gun"), s_ay),
        "disborc": (O.get("gecikme_dis_gun"), s_dis),
        "menkul": (O.get("gecikme_hafta_gun"), s_hafta),
        "ceyrek": (O.get("gecikme_ceyrek_gun"), s_ceyrek),
        "kur": (O.get("gecikme_kur_gun"), s_gun),
    }
    bayat_sebep: list[str] = []
    for aile, (gec, t) in aile_gecikme.items():
        if gec is None:
            continue
        etiket, tol, negatif_muaf = TAZELIK[aile]
        O[f"tolerans_{aile}_gun"] = tol
        if gec < 0 and negatif_muaf:
            continue
        if gec > tol:
            bayat_sebep.append(f"{etiket} {gec} gün geride (tolerans {tol} gün)")
    izler = [u for u in uyarilar
             if u.startswith(("TAZELİK", "ESKİ ÖNBELLEK", "BAYAT", "SERİ YOK"))]
    if izler:
        bayat_sebep.append(f"veri katmanı {len(izler)} tazelik/önbellek uyarısı bastı")
    # KOŞMAMIŞ DENETİM DE BAYATLIK SEBEBİDİR. Aksi hâlde sayfa denetimsiz
    # kalır ama "taze" görünür; üstelik atlanan anahtarların yerine MDX'teki
    # statik yedek basılacağı için sayı da eskiyle aynı kalır.
    for mm in EKSIK_DENETIM:
        uyarilar.append(mm)
        bayat_sebep.append(mm)
    O["bayat"] = bool(bayat_sebep)
    O["bayat_cumlesi"] = (
        "BAYAT VERİ: " + "; ".join(bayat_sebep)
        + ". Sayfadaki sayılar bu koşuda İLERLEMEMİŞ olabilir."
        if bayat_sebep else
        "Veri taze: altı yayım ailesinin de gecikmesi kendi toleransı içinde, "
        "tazelik uyarısı yok.")
    # Gecikmeyi ÇERÇEVELEYEN cümle de sayıdan türetilir; sayfa "bütçe verisi
    # üç ay geriden gelir" gibi elle yazılmış bir ifadeyle çelişmesin.
    O["gecikme_cumlesi"] = (
        f"Bütçe gerçekleşmeleri {O.get('gecikme_butce_gun')} gün, brüt dış borç "
        f"{O.get('gecikme_dis_gun')} gün, haftalık menkul kıymet istatistikleri "
        f"{O.get('gecikme_hafta_gun')} gün, GSYH ve finansal hesaplar "
        f"{O.get('gecikme_ceyrek_gun')} gün geriden geliyor.")

    O["uyari_sayisi"] = len(uyarilar)
    O["uyari_metni"] = ((O["bayat_cumlesi"] + " · " if O["bayat"] else "")
                        + (" · ".join(uyarilar) if uyarilar
                           else "Bu koşuda uyarı yok."))
    O["uyari_cumlesi"] = (
        "Bu koşuda uyarı düşmedi." if not uyarilar else
        "Bu koşuda düşen tek uyarı budur:" if len(uyarilar) == 1 else
        f"Bu koşuda {len(uyarilar)} uyarı düştü:")

    # ===================================================== hazır cümleler
    # Sayıyı çerçeveleyen ifadeler de SAYIDAN türetilir; "rekor" / "ilk kez"
    # gibi elle yazılmış nitelemeler veri değişince sessizce yanlışa döner.
    O["denge_cumlesi"] = (
        f"12 aylık birikimli merkezi yönetim bütçesi {ay_ad(s_ay)} itibarıyla "
        f"{tr_sayi(abs(O.get('denge_12a') or 0), 2)} trilyon TL {O['denge_isaret']} "
        f"veriyor; faiz dışı denge {tr_sayi(abs(O.get('fdd_12a') or 0), 2)} trilyon TL "
        f"{O['fdd_isaret']}.")
    O["reel_cumlesi"] = (
        f"Aynı dönemde gelir nominal olarak {tr_yuzde(O.get('gelir_nom_yy'))} artarken "
        f"reel artış {tr_yuzde(O.get('gelir_reel_yy'))}; reel faiz dışı harcama "
        f"{tr_yuzde(O.get('fdg_reel_yy'))}.")
    O["stok_cumlesi"] = (
        f"Merkezi yönetim borç stoku {O.get('stok_son_ay')} itibarıyla "
        f"{tr_sayi(O.get('toplam_borc_trl'), 2)} trilyon TL "
        f"(iç borç {tr_sayi(O.get('ic_borc_trl'), 2)} + yurt dışında ihraç senet "
        f"{tr_sayi(O.get('dis_senet_trl'), 2)} + dış kredi "
        f"{tr_sayi(O.get('dis_kredi_trl'), 2)}); döviz payı en az "
        f"{tr_yuzde(O.get('doviz_pay'))}. "
        f"Stok/GSYH oranı {O.get('oran_ceyregi')} itibarıyla "
        f"{tr_yuzde(O.get('stok_gsyh'))}.")
    O["faiz_cumlesi"] = (
        f"Faiz gideri 12 aylık birikimli {tr_sayi(O.get('faiz_12a'), 2)} trilyon TL; "
        f"vergi gelirlerine oranı {tr_yuzde(O.get('faiz_vergi'))}, GSYH'ye oranı "
        f"{tr_yuzde(O.get('faiz_gsyh'), 2)}. Toplam faiz içinde iç borç faizinin payı "
        f"{tr_yuzde(O.get('faiz_ic_pay'))}.")
    O["ima_faiz_cumlesi"] = (
        f"Stok üzerinden ima edilen ortalama nominal faiz "
        f"{tr_yuzde(O.get('ima_faiz_nominal'))}; Fisher konvansiyonuyla reel karşılığı "
        f"{tr_yuzde(O.get('ima_faiz_reel'))}. Basit çıkarma aynı veriden "
        f"{tr_yuzde(O.get('ima_faiz_reel_basit'))} verirdi — "
        f"{tr_sayi(abs(O.get('fisher_ima_faiz_fark_pp') or 0), 2)} puan fark.")
    O["cevirme_cumlesi"] = (
        f"12 aylık iç borç çevirme oranı {tr_yuzde(O.get('cevirme'), 0)}; "
        f"iç borç faizi paydaya eklendiğinde {tr_yuzde(O.get('cevirme_faiz'), 0)}. "
        f"Son beş yıl bandı {tr_yuzde(O.get('cevirme_bant_min'), 0)}–"
        f"{tr_yuzde(O.get('cevirme_bant_max'), 0)}.")
    O["sahiplik_cumlesi"] = (
        f"{gun_ad(s_hafta)} itibarıyla DİBS stokunda bankaların payı "
        f"{tr_yuzde(O.get('pay_dibs_bankalar'))}, yurt dışı yerleşiklerin payı "
        f"{tr_yuzde(O.get('pay_dibs_yurtdisi'))}, TCMB'nin payı "
        f"{tr_yuzde(O.get('pay_dibs_tcmb'))}.")
    O["vade_cumlesi"] = (
        f"DİBS stokunda kalan vadesi bir yıldan kısa olanların payı "
        f"{tr_yuzde(O.get('pay_dibs_kv_kisa'))}; eurobondda aynı oran "
        f"{tr_yuzde(O.get('pay_eb_kv_kisa'))}. Her iki oran da PİYASA değerli "
        f"tablolardan alınmıştır.")
    O["kur_cumlesi"] = (
        f"USD/TRY'de %10'luk bir değer kaybı stoku EN AZ "
        f"{tr_sayi(O.get('sok10_stok_trl'), 2)} trilyon TL'ye taşır "
        f"({tr_yuzde(O.get('sok10_degisim'))}); stok/GSYH oranı EN FAZLA "
        f"{tr_sayi(O.get('sok10_gsyh_puan'), 1)} puan yükselir.")

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · bütçe {O['ay']} "
          f"({O['gecikme_butce_gun']} gün önce) · menkul {O['hafta']} · "
          f"GSYH {O['ceyrek']}" + ("  ! BAYAT" if O.get("bayat") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
