# -*- coding: utf-8 -*-
"""Enflasyon panosu — ozet.json üretimi.

Sayfa metnindeki OYNAK her sayı buradan beslenir (CLAUDE.md kural 5):
MDX'te <Deger proje="enflasyon" anahtar="..." ondalik={1}>statik yedek</Deger>.
Tarihsel/metodolojik sabitler (formüller, kurum tanımları, doğrulama örnekleri)
sayfada STATİK kalır — onlar veri tazelendikçe değişmez.

Bütün değerler data/ altındaki üretilmiş dosyalardan OKUNUR; elle sayı yazılmaz.
Bir değer kaynakta yoksa anahtar ATLANIR ve stderr'e uyarı basılır.

Koşum:  python3 ozet_uret.py   (önce veri.py → metrik.py → grafik.py)
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

import veri
from veri import PROJE, VERI, AY_TR, AY_KISA

O: dict = {}


def uyar(m: str) -> None:
    print(f"UYARI: {m}", file=sys.stderr)


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


# TÜİK, TÜFE'yi ertesi ayın 3'ünde saat 10:00'da açıklar (3'ü tatile denk
# gelirse ilk iş günü). Yayım gecikmesi bu takvimden ölçülür.
YAYIM_GUNU = 3


def yayim_tarihi(son_ay: pd.Timestamp) -> dt.date:
    t = (son_ay + pd.DateOffset(months=1)).replace(day=YAYIM_GUNU).date()
    while t.weekday() >= 5:                     # hafta sonuysa ilk iş günü
        t += dt.timedelta(days=1)
    return t


def kalem_ad(x: str) -> str:
    """COICOP grup adından sayı önekini at: "011. Gıda" → "Gıda"."""
    t = str(x)
    return t.split(". ", 1)[1] if ". " in t[:6] else t


def ay_araliklari(aylar: list[int]) -> str:
    """[8, 9, 10] → "Ağustos–Ekim" · [11, 1] → "Kasım ve Ocak".

    Ay adları MDX'e GÖMÜLMEZ: pencere bir ay kaydığında cümle sessizce yanlışa
    dönerdi. Ardışıklık takvim ayı üzerinden (Aralık→Ocak sarması dahil) okunur.
    """
    if not aylar:
        return "yok"
    kume: list[list[int]] = [[aylar[0]]]
    for x in aylar[1:]:
        if x == (kume[-1][-1] % 12) + 1:
            kume[-1].append(x)
        else:
            kume.append([x])
    parca = [AY_TR[k[0]] if len(k) == 1 else f"{AY_TR[k[0]]}–{AY_TR[k[-1]]}"
             for k in kume]
    if len(parca) == 1:
        return parca[0]
    return ", ".join(parca[:-1]) + " ve " + parca[-1]


def main() -> int:
    m = json.loads((VERI / "metrik_ozet.json").read_text(encoding="utf-8"))
    uy = json.loads((PROJE / "uyarilar.json").read_text(encoding="utf-8"))
    son = pd.Timestamp(m["son_ay"])

    # ---------------------------------------------------------------- dönem
    O["_tarih"] = son.strftime("%m.%Y")
    O["donem"] = f"{AY_TR[son.month]} {son.year}"
    O["donem_kisa"] = f"{AY_KISA[son.month]}-{str(son.year)[2:]}"
    O["donem_ay"] = AY_TR[son.month]
    O["donem_yil"] = son.year
    onc = son - pd.DateOffset(months=1)
    O["onceki_ay"] = AY_TR[onc.month]
    yt = yayim_tarihi(son)
    O["yayim_tarihi"] = yt.strftime("%d.%m.%Y")
    O["yayim_gecikme_gun"] = (dt.date.today() - yt).days
    O["kosum_tarihi"] = dt.date.today().strftime("%d.%m.%Y")

    # ---------------------------------------------------------------- momentum
    kisa = {"tufe": "tufe", "cekirdek_b": "b", "cekirdek_c": "c",
            "hizmet": "hizmet", "temel_mal": "mal", "kira": "kira",
            "enerji": "enerji", "gida": "gida",
            "islenmemis_gida": "hamgida", "islenmis_gida": "islgida",
            "alkol_tutun_altin": "atg", "yonetilen_haric": "fharic",
            "yi_ufe": "ufe"}
    for uzun, k in kisa.items():
        koy(f"{k}_12a", m.get(f"{uzun}__yillik"))
        koy(f"{k}_3a", m.get(f"{uzun}__saar3_sa"))
        koy(f"{k}_6a", m.get(f"{uzun}__saar6_sa"))
        # HAM (arındırılmamış) yıllıklandırılmış — arındırılmışın yanında BİRİNCİ
        # SINIF metrik olarak her seri için yayımlanır. Sebep: arındırma bir MODEL
        # çıktısıdır (uç ayda revize olur, hizmette 4 puana kadar); ham seri ise
        # yayımlanmış endeksten doğrudan çıkar, yeniden üretilebilir ve model
        # varsayımı taşımaz. İkisi birlikte okunur: ayrıştıkları yer mevsimselliğin
        # o ay ne kadar iş yaptığını söyler.
        koy(f"{k}_3a_ham", m.get(f"{uzun}__saar3_ham"))
        koy(f"{k}_6a_ham", m.get(f"{uzun}__saar6_ham"))
        koy(f"{k}_aylik", m.get(f"{uzun}__aylik_ham"))
        koy(f"{k}_aylik_sa", m.get(f"{uzun}__aylik_sa"))
        # arındırmanın o serideki bedeli (puan): SA − ham
        s3, h3 = m.get(f"{uzun}__saar3_sa"), m.get(f"{uzun}__saar3_ham")
        if s3 is not None and h3 is not None:
            koy(f"{k}_3a_fark", s3 - h3)
        s6, h6 = m.get(f"{uzun}__saar6_sa"), m.get(f"{uzun}__saar6_ham")
        if s6 is not None and h6 is not None:
            koy(f"{k}_6a_fark", s6 - h6)
    # (enerji_3a_ham / enerji_6a_ham artık yukarıdaki döngüden geliyor — enerji
    #  arındırmanın en çok iş yaptığı seridir, farkı _3a_fark anahtarında görünür.)
    koy("enerji_mevsim_p", m.get("enerji_mevsim_p"), 3)
    koy("enerji_sa_ham_maks", m.get("enerji_sa_ham_maks_pp"), 2)
    koy("enerji_sa_ham_son", m.get("enerji_sa_ham_son_pp"), 2)
    # Baz etkisi aracının başlangıç değeri: ozet.json'daki 2 ondalıklı tufe_12a ile
    # 4 ondalıklı baz_dusen dizisi arasındaki artık, "geçen yıl tekrar" patikasında
    # −0,00 gibi eksi sıfırlar üretiyordu.
    koy("tufe_12a_tam", m.get("tufe__yillik"), 4)
    # Mevsimsellik testinden geçemeyen ana seriler (sayfadaki ° satırları)
    if m.get("arindirilmayan_ana_metin"):
        O["sa_arindirilmayanlar"] = m["arindirilmayan_ana_metin"]
        O["sa_arindirilmayan_n"] = len(m.get("arindirilmayan_ana") or [])
    koy("sa_p_islgida", m.get("islenmis_gida__mevsim_p"), 3)
    koy("sa_p_ufe", m.get("yi_ufe__mevsim_p"), 3)
    koy("sa_p_tufe", m.get("tufe__mevsim_p"), 4)
    koy("ocak_ham_ort", m.get("ocak_ham_ort"))
    koy("ocak_sa_ort", m.get("ocak_sa_ort"))
    koy("ocak_duzeltme_pp", m.get("ocak_duzeltme_pp"), 2)
    koy("ocak_n", m.get("ocak_n"), 0)
    koy("hedef_yillik", m.get("hedef_yillik"), 1)
    koy("hedef_aylik", m.get("hedef_aylik"), 2)
    koy("tufe_ecb3", m.get("tufe__ecb3"))
    if m.get("tufe__saar3_sa") is not None and m.get("tufe__saar3_ham") is not None:
        koy("tufe_3a_arindirma_farki",
            m["tufe__saar3_sa"] - m["tufe__saar3_ham"])
    if m.get("hizmet__yillik") is not None and m.get("temel_mal__yillik") is not None:
        koy("makas_12a", m["hizmet__yillik"] - m["temel_mal__yillik"])
    if m.get("hizmet__saar3_sa") is not None and m.get("temel_mal__saar3_sa") is not None:
        koy("makas_3a", m["hizmet__saar3_sa"] - m["temel_mal__saar3_sa"])

    # ---------------------------------------------------------------- dağılım
    koy("medyan_aylik", m.get("dagilim__medyan"))
    koy("medyan_3a", m.get("dagilim__medyan_saar3"))
    koy("kirpma_aylik", m.get("dagilim__kirpma_08"))
    koy("kirpma_3a", m.get("dagilim__kirpma_08_saar3"))
    alt = [m.get(f"dagilim__kirpma_{a}_saar3") for a in ("05", "08", "10")]
    alt = [x for x in alt if x is not None]
    if alt:
        koy("kirpma_bant_alt", min(alt))
        koy("kirpma_bant_ust", max(alt))
    koy("difuzyon", m.get("dagilim__difuzyon_0"), 1)
    koy("difuzyon_hedef", m.get("dagilim__difuzyon_hedef"), 1)
    koy("difuzyon_mansete_gore", m.get("dagilim__difuzyon_mansete_gore"), 1)
    koy("kesit_n", m.get("dagilim__kesit_n"), 0)
    # KESİT TANISI — "43 grubun arındırılmış aylık değişimleri" cümlesinin
    # nitelendirilmesi: dörtte biri ham geçiyor, kesit yoğun.
    kt = m.get("kesit_tani") or {}
    koy("kesit_arindirilmayan_n", kt.get("arindirilmayan_n"), 0)
    koy("kesit_arindirilmayan_agirlik", kt.get("arindirilmayan_agirlik"), 1)
    yog = kt.get("yogunlasma") or {}
    koy("kesit_hhi", yog.get("hhi"), 4)
    koy("kesit_esdeger_n", yog.get("esdeger_kalem"), 1)
    koy("kesit_en_buyuk_pay", yog.get("en_buyuk_pay"), 1)
    koy("kesit_ilk3_pay", yog.get("ilk3_pay"), 1)
    if yog.get("en_buyuk_ad"):
        O["kesit_en_buyuk_ad"] = kalem_ad(yog["en_buyuk_ad"])
    mk = kt.get("medyan_kalem") or {}
    if mk.get("en_sik_ad"):
        O["medyan_kalem_ad"] = kalem_ad(mk["en_sik_ad"])
        koy("medyan_kalem_pay", mk.get("en_sik_pay"), 0)
        koy("medyan_kalem_ay", mk.get("ay"), 0)
        O["medyan_kalem_bas"] = str(mk.get("bas", ""))
    if mk.get("son_ad"):
        O["medyan_kalem_son_ad"] = kalem_ad(mk["son_ad"])
    # Hareketli tatil ön-arındırması nerede iş yapıyor?
    koy("tatil_gecen_alt", kt.get("tatil_gecen_n"), 0)
    koy("tatil_ana_maks_t", m.get("tatil_ana_maks_t"), 2)
    koy("tatil_ana_gecen", m.get("tatil_ana_gecen"), 0)
    tg = kt.get("tatil_gecen") or {}
    if tg:
        O["tatil_gecen_alt_ad"] = ", ".join(
            sorted(kalem_ad(v.get("ad") or k) for k, v in tg.items()))

    # ---------------------------------------------------------------- katkı
    grup_ad = {f"oktg{v[1][-2:]}": v[0] for v in veri.KATKI_GRUP.values()}
    ky = m.get("katki_yillik") or {}
    if ky:
        koy("katki_toplam", sum(ky.values()))
        sirali = sorted(ky.items(), key=lambda x: -x[1])
        for i, (k, v) in enumerate(sirali[:3], start=1):
            O[f"katki{i}_ad"] = grup_ad.get(k, k)
            koy(f"katki{i}_puan", v)
        for k, v in ky.items():
            koy(f"katki_{k[-2:]}_puan", v)
        if m.get("tufe_12a") is None and m.get("tufe__yillik"):
            pass
    ka = m.get("katki_aylik") or {}
    for k, v in ka.items():
        koy(f"katki_aylik_{k[-2:]}_puan", v)
    # AYLIK ve YILLIK artık ayrı anahtarlarda: eşikleri de farklı (aylık 0,02 —
    # Σ C_it = π_t birebir sağlanmalı; yıllık 0,05 — ağırlık tahmininin payı var).
    koy("katki_ay_artik_pp", m.get("katki_ay_artik_pp"), 4)
    koy("katki_ay_artik_tum_pp", m.get("katki_ay_artik_tum_pp"), 4)
    koy("katki_yil_artik_pp", m.get("katki_yil_artik_pp"), 4)
    koy("katki_yil_artik_tum_pp", m.get("katki_yil_artik_tum_pp"), 4)

    # ---------------------------------------------------------------- ağırlık
    ag = m.get("agirlik_son_yil") or {}
    for k, v in (ag.get("katki") or {}).items():
        koy(f"agirlik_{k[-2:]}", v, 1)
    O["agirlik_yil"] = ag.get("yil")
    koy("agirlik_artik_pp", ag.get("artik_pp"), 4)
    for k, v in (m.get("agirlik_kayma_pp") or {}).items():
        koy(f"agirlik_kayma_{k[-2:]}", v, 1)

    # ---------------------------------------------------------------- beklenti
    koy("bek_12a", m.get("bek__pka_12a"))
    koy("bek_24a", m.get("bek__pka_24a"))
    koy("bek_yilsonu", m.get("bek__pka_yilsonu"))
    koy("bek_5y", m.get("bek__pka_5y"))
    koy("bek_medyan_12a", m.get("bek__pka_12a_medyan"))
    koy("bek_std_12a", m.get("bek__pka_12a_std"))
    koy("bek_n", m.get("bek__pka_12a_n"), 0)
    koy("bek_faiz_12a", m.get("bek__pka_faiz_12a"))
    koy("bek_reel_kesim_12a", m.get("bek__reel_kesim_12a"))
    koy("bek_hane_12a", m.get("bek__hanehalki_12a"))
    if m.get("bek__pka_12a_tarih"):
        t = pd.Timestamp(m["bek__pka_12a_tarih"])
        O["pka_tarih"] = t.strftime("%m.%Y")
        O["pka_donem"] = f"{AY_TR[t.month]} {t.year}"
    bi = m.get("beklenti_isabet") or {}
    for h in ("h0", "h1", "h2"):
        for pen in ("p36", "p60"):
            d = bi.get(h, {}).get(pen)
            if not d:
                continue
            koy(f"isabet_{h}_{pen}_mae", d["mae"])
            koy(f"isabet_{h}_{pen}_yanlilik", d["yanlilik"])
            koy(f"isabet_{h}_{pen}_rmse", d["rmse"])
    # "60 aylık pencerede hatalar 36 aylığın iki katı" iddiası yuvarlamaydı;
    # oranı hesaplayıp yazıyoruz (bu koşuda ~1,8).
    _o = [bi.get(h, {}).get("p60", {}).get("mae") / bi[h]["p36"]["mae"]
          for h in ("h0", "h1", "h2")
          if bi.get(h, {}).get("p60", {}).get("mae") and bi.get(h, {}).get("p36", {}).get("mae")]
    if _o:
        koy("isabet_p60_p36_orani", sum(_o) / len(_o), 1)

    # ---------------------------------------------------------------- reel faiz
    koy("faiz", m.get("reel__faiz"))
    koy("reel_expost", m.get("reel__ex_post"))
    koy("reel_exante", m.get("reel__ex_ante"))
    koy("reel_egilim", m.get("reel__egilime_gore"))
    koy("reel_ileri", m.get("reel__ileri_ex_ante"))
    if m.get("reel__faiz_tarih"):
        O["faiz_tarih"] = pd.Timestamp(m["reel__faiz_tarih"]).strftime("%m.%Y")
    # Günlük bacağın GERÇEK son gözlem günü. guncelle.py'nin tazelik denetimi
    # bunu ayrı bir anahtar olarak izler: aylık TÜFE ayda bir ilerlerken faiz
    # her iş günü ilerlemeli; biri donarken diğeri ilerleyebiliyor.
    try:
        gg = pd.read_csv(VERI / "gunluk.csv", index_col=0, parse_dates=True)
        if "aofm" in gg.columns and gg["aofm"].notna().any():
            O["faiz_gun"] = gg["aofm"].dropna().index[-1].strftime("%d.%m.%Y")
    except Exception as ex:
        uyar(f"günlük faiz tarihi okunamadı ({ex}).")
    if m.get("reel__ex_post_faiz") is not None:
        koy("reel_expost_faiz", m["reel__ex_post_faiz"])
    if m.get("reel__faiz") is not None and m.get("tufe__yillik") is not None:
        koy("reel_yaklasik_hata",
            (m["reel__faiz"] - m["tufe__yillik"]) - (m.get("reel__ex_post") or 0))

    # ---------------------------------------------------------------- baz etkisi
    baz = m.get("baz") or {}
    for ad, k in (("son3_sa", "momentum"), ("son12_ort", "son12"),
                  ("gecen_yil", "tekrar")):
        d = baz.get(ad) or {}
        koy(f"baz_{k}_12ay", d.get("12ay_sonra"))
        koy(f"baz_{k}_aylik", d.get("aylik_varsayim"))
        koy(f"baz_{k}_yilsonu", d.get("yil_sonu"))

    # Sayfadaki BazEtkisiHesaplayici bileşeninin beslemesi. Kimliğin paydası
    # (düşen aylar) tamamen bilinen bir dizidir; araç yalnız payı kullanıcıdan
    # alır. Diziyi ozet.json'a yazmak, aracın veriyle birlikte tazelenmesini
    # sağlar — MDX'e sabit sayı gömmek sessiz bayatlama üretirdi.
    try:
        bz = pd.read_csv(VERI / "baz_senaryo.csv", parse_dates=["tarih"])
        O["baz_dusen"] = [
            {"kod": t.strftime("%m.%Y"),
             "ay": f"{AY_KISA[t.month]}-{str(t.year)[2:]}",
             "oran": round(float(o), 4)}
            for t, o in zip(bz["tarih"], bz["dusen_aylik"])
        ]
        O["baz_ufuk"] = len(O["baz_dusen"])
        # Baz elverişli mi? Düşen ay ileri varsayımdan YÜKSEKse yıllık enflasyon
        # mekanik olarak geriler. Kıyas ölçütü momentum senaryosunun aylık
        # varsayımıdır (yoksa son 12 ay ortalaması).
        ileri = O.get("baz_momentum_aylik", O.get("baz_son12_aylik"))
        if ileri is not None:
            elv, elz = [], []
            for d in O["baz_dusen"]:
                ay = int(d["kod"][:2])
                (elv if d["oran"] > ileri else elz).append(ay)
            O["baz_elverisli_aylar"] = ay_araliklari(elv)
            O["baz_elverissiz_aylar"] = ay_araliklari(elz)
            koy("baz_kiyas_aylik", ileri)
            O["baz_elverisli_n"] = len(elv)
    except Exception as ex:
        uyar(f"baz_senaryo.csv okunamadı ({ex}) — 'baz_dusen' anahtarı atlandı.")

    # ---------------------------------------------------------------- atalet, İTO
    for ad, k in (("hizmet", "hizmet"), ("temel_mal", "mal"),
                  ("tufe", "tufe"), ("kira", "kira")):
        koy(f"atalet_{k}", (m.get("atalet") or {}).get(ad), 3)
    ito = m.get("ito") or {}
    koy("ito_sabit", ito.get("sabit"), 3)
    koy("ito_egim", ito.get("egim"), 3)
    koy("ito_r", ito.get("r"), 3)
    koy("ito_r2", ito.get("r2"), 3)
    koy("ito_r_onceden", ito.get("r_bir_ay_onceden"), 3)
    koy("ito_n", ito.get("n"), 0)
    koy("ito_son_aylik", ito.get("son_ito_aylik"))
    koy("ito_se_sabit", ito.get("se_sabit"), 3)
    koy("ito_se_egim", ito.get("se_egim"), 3)
    koy("ito_se_artik", ito.get("se_artik"), 2)
    koy("ito_ima_aylik", ito.get("ima_aylik"))
    # NOKTA TAHMİN DEĞİL ARALIK: %95 ÖNGÖRÜ aralığı (güven aralığı değil —
    # yeni bir gözlemin nereye düşeceğini sorar, ortalamanın değil).
    koy("ito_ima_alt", ito.get("ima_alt"))
    koy("ito_ima_ust", ito.get("ima_ust"))
    koy("ito_ima_yari", ito.get("ima_yari_genislik"))

    # ---------------------------------------------------------------- İTO profili
    # ito_profil.json ayrı bir dosyadır ve metrik_ozet.json'a GÖMÜLMEZ: içinde
    # tablo/satır listeleri var, özet dosyası ise skaler sözlük olarak okunuyor.
    # Dosya YOKSA anahtarlar yazılmaz ve sayfadaki statik yedekler görünür —
    # ama o zaman sayfa sınavının 1. kuralı düşer, yani sessizce donmaz.
    ipy = VERI / "ito_profil.json"
    ip = json.loads(ipy.read_text(encoding="utf-8")) if ipy.exists() else {}
    if not ip.get("tablo"):
        uyar("ito_profil.json yok ya da boş — İTO profili anahtarları atlandı.")
    else:
        f_, r_ = ip["fark"], ip["regresyon"]
        koy("itp_pencere", ip.get("pencere_ay"), 0)
        koy("itp_n", ip.get("n_toplam"), 0)
        koy("itp_ilk_ay", ip.get("ilk_ay"), None)
        koy("itp_son_ay", ip.get("son_ay"), None)
        for k, o_ in (("ort", 2), ("medyan", 2), ("std", 2), ("min", 2),
                      ("maks", 2), ("mutlak_ort", 2), ("ustte_pay", 0),
                      ("t", 2), ("p", 4)):
            koy(f"itp_{k}", f_.get("ito_ustte_pay" if k == "ustte_pay" else k), o_)
        koy("itp_min_ay", f_.get("min_ay"), None)
        koy("itp_maks_ay", f_.get("maks_ay"), None)
        for k in ("sabit", "egim", "se_egim", "se_sabit", "r", "spearman",
                  "r2", "se_artik"):
            koy(f"itp_{k}", r_.get(k), 3)
        koy("itp_t_bir", r_.get("t_egim_bir"), 2)
        koy("itp_p_bir", r_.get("p_egim_bir"), 4)

        ku = ip.get("kural") or {}
        sk, skd = ku.get("skor") or {}, ku.get("skor_dar") or {}
        koy("itp_k_n", ku.get("n"), 0)
        koy("itp_k_ilk", ku.get("ilk_ay"), None)
        koy("itp_k_son", ku.get("son_ay"), None)
        koy("itp_k_asgari", ku.get("asgari"), 0)
        for c in ("naif", "sabit", "medyan", "oransal", "regresyon", "takvimli"):
            koy(f"itp_mae_{c}", (sk.get(c) or {}).get("mae"), 3)
            koy(f"itp_maed_{c}", (skd.get(c) or {}).get("mae"), 3)
            koy(f"itp_is05_{c}", (sk.get(c) or {}).get("isabet_05"), 0)
        KURAL_AD = {"naif": "naif kural (TÜFE = İTO)", "sabit": "sabit kaydırma",
                    "medyan": "medyan kaydırma", "oransal": "oransal kural",
                    "regresyon": "regresyon", "takvimli": "takvim ayı düzeltmesi"}
        koy("itp_kazanan", KURAL_AD.get(ku.get("kazanan"), ku.get("kazanan")), None)
        koy("itp_kazanan_dar", KURAL_AD.get(ku.get("kazanan_dar"), ku.get("kazanan_dar")),
            None)
        koy("itp_takvimli_zarar", ku.get("takvimli_zarar"), 3)
        # Sıralama pencereye duyarlıysa "en iyi kural şudur" CÜMLESİ KURULMAZ.
        # Metin bu anahtarı basar; hüküm koda gömülü, MDX'te elle yazılmaz.
        koy("itp_siralama_metin",
            ("aynı kural iki pencerede de kazanıyor"
             if ku.get("siralama_dayanikli") else
             "sıralama pencereye duyarlı — hiçbir kural için 'en iyisi budur' "
             "denemez"), None)

        an = ip.get("anket") or {}
        if an:
            koy("itp_pka_mae", an.get("pka_mae"), 3)
            koy("itp_ito_mae", an.get("ito_mae"), 3)
            koy("itp_esli", an.get("esli_fark"), 3)
            koy("itp_esli_t", an.get("esli_t"), 2)
            koy("itp_esli_p", an.get("esli_p"), 3)
            koy("itp_anket_n", an.get("n_disi"), 0)
            koy("itp_anket_hukum",
                ("İTO kuralı anketten ölçülebilir biçimde iyi"
                 if an.get("ito_anlamli_iyi") else
                 "aradaki fark istatistiksel olarak ayırt edilemiyor"), None)

        sp = ip.get("surpriz") or {}
        if sp:
            koy("itp_s_egim", sp.get("egim"), 3)
            koy("itp_s_se", sp.get("se_egim"), 3)
            koy("itp_s_sabit", sp.get("sabit"), 3)
            koy("itp_s_t", sp.get("t"), 2)
            koy("itp_s_p", sp.get("p"), 4)
            koy("itp_s_r2", sp.get("r2"), 2)
            koy("itp_s_r", sp.get("r"), 3)
            koy("itp_s_n", sp.get("n"), 0)
            koy("itp_s_uyum", sp.get("isaret_uyumu"), 0)
            koy("itp_s_uyum_p", sp.get("isaret_p"), 4)
            koy("itp_s_uyum25", sp.get("isaret_uyumu_25"), 0)
            koy("itp_s_n25", sp.get("n_25"), 0)

        orn = ip.get("oranti") or {}
        for k in ("egim", "se", "t", "r", "oran_medyan", "kayan_ilk", "kayan_son",
                  "kayan_maks", "kayan_r_min", "kayan_r_maks",
                  "kayan_egim_min", "kayan_egim_maks"):
            koy(f"itp_o_{k}", orn.get(k), 3)
        koy("itp_o_p", orn.get("p"), 4)
        koy("itp_o_n", orn.get("kayan_n"), 0)
        koy("itp_o_hukum",
            ("fark İTO seviyesiyle ölçülebilir biçimde artıyor"
             if orn.get("anlamli") else
             "seviye bağımlılığı bu örneklemde istatistiksel olarak "
             "doğrulanamıyor"), None)

        yo = ip.get("yillik_ozet") or {}
        for k in ("ort", "son", "maks", "min", "son_ito", "son_tufe"):
            koy(f"itp_y_{k}", yo.get(k), 2)
        koy("itp_y_maks_ay", yo.get("maks_ay"), None)

        # Koşullu eşleme tablosu OLDUĞU GİBİ taşınır: hem MDX tablosu hem de
        # sayfadaki hesap aracı aynı diziyi okur. İki yerde iki kopya olsaydı
        # bir gün sessizce ayrışırlardı.
        koy("itp_esleme", ip.get("esleme"), None)
        koy("itp_tablo", ip.get("tablo"), None)
        for e in ip.get("esleme") or []:
            k = f"{e['ito']:.1f}".replace(".", "")
            koy(f"itp_es{k}", e["tufe"], 2)
            koy(f"itp_es{k}_alt", e["alt"], 2)
            koy(f"itp_es{k}_ust", e["ust"], 2)

    # ---------------------------------------------------------------- denetim
    dg = m.get("dogrulama") or {}
    koy("dogrulama_yillik_pp", (dg.get("yillik") or {}).get("maks_fark_pp"), 4)
    koy("dogrulama_aylik_pp", (dg.get("aylik") or {}).get("maks_fark_pp"), 4)
    koy("dogrulama_n", (dg.get("yillik") or {}).get("n"), 0)
    # KOŞULAR ARASI iz: yalnız içerik gerçekten değiştiyse yazılır. Aynı veriyle
    # iki kez koşulduğunda ölçü yapısal olarak 0 çıkar; 0,00 yazmak SAHTE
    # GÜVENCE olurdu, bu yüzden anahtar ATLANIR ve durum metni yazılır.
    rev = m.get("kosular_arasi") or {}
    if rev.get("var"):
        koy("kosu_revizyon_maks", rev.get("maks_pp"), 3)
        koy("kosu_revizyon_ort", rev.get("ort_pp"), 3)
        O["kosu_revizyon_durum"] = (
            f"önceki koşuya ({rev.get('onceki_kosum', '?')}) göre ölçüldü")
    else:
        O["kosu_revizyon_durum"] = str(
            rev.get("not") or "koşular arası revizyon bu koşuda ölçülemedi")
    # GERÇEK uç-nokta revizyonu (vintage): seri k ay kesilip yeniden arındırılır.
    # Sayfadaki "revizyon riski" güvencesi BURADAN beslenir.
    vg = m.get("vintage") or {}
    koy("sa_rev_k", vg.get("k_maks"), 0)
    _rev_kisa = {"tufe": "tufe", "cekirdek_c": "c", "hizmet": "hizmet",
                 "temel_mal": "mal", "gida": "gida"}
    for uzun, k in _rev_kisa.items():
        d = (vg.get("seriler") or {}).get(uzun) or {}
        koy(f"sa_rev_{k}_maks", d.get("mm_maks_pp"), 3)
        koy(f"sa_rev_{k}_ort", d.get("mm_ort_pp"), 3)
        koy(f"sa_rev_{k}_saar3", d.get("saar3_maks_pp"), 2)
    eo = vg.get("en_oynak") or {}
    if eo.get("ad"):
        O["sa_rev_enoynak_ad"] = str(eo["ad"])
        koy("sa_rev_enoynak_maks", eo.get("mm_maks_pp"), 3)
        koy("sa_rev_enoynak_ort", eo.get("mm_ort_pp"), 3)
        koy("sa_rev_enoynak_saar3", eo.get("saar3_maks_pp"), 2)
    # "oynak" etiketli seriler ayrı: enerjinin revizyonu merkezî ölçülerle aynı
    # cümlede anılmaz, ama gizlenmez de.
    eo2 = vg.get("en_oynak_etiketli") or {}
    if eo2.get("ad"):
        O["sa_rev_oynak_ad"] = str(eo2["ad"])
        koy("sa_rev_oynak_maks", eo2.get("mm_maks_pp"), 3)
        koy("sa_rev_oynak_saar3", eo2.get("saar3_maks_pp"), 2)
    O["sa_yontem"] = m.get("sa_yontem")
    uyarilar = uy.get("uyarilar", [])
    O["uyari_sayisi"] = len(uyarilar)
    O["uyari_metni"] = (" · ".join(uyarilar) if uyarilar
                        else "Bu koşuda uyarı yok.")
    # Sayıyı ÇERÇEVELEYEN cümle de sayıdan türetilir: "tek uyarı budur (3 adet)"
    # gibi kendisiyle çelişen bir metin kalmasın.
    O["uyari_cumlesi"] = (
        "Bu koşuda uyarı düşmedi." if not uyarilar else
        "Bu koşuda düşen tek uyarı budur:" if len(uyarilar) == 1 else
        f"Bu koşuda {len(uyarilar)} uyarı düştü:")

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · veri {O['donem']} · "
          f"yayım {O['yayim_tarihi']} ({O['yayim_gecikme_gun']} gün önce)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
