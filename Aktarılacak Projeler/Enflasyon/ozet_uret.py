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


def ay_okur(iso: str | None) -> str | None:
    """'2024-05' → 'Mayıs 2024'. ISO ay kodu MAKİNE yazımıdır; okur metninde
    ay adı geçer. Türkçe ekler de buna bağlı: '2025-04'de' yanlış ('dört'
    sesiyle 'te' gerekirdi), 'Nisan 2025' ise ek almadan cümleye girer."""
    try:
        y, a = str(iso).split("-")
        return f"{AY_TR[int(a)]} {int(y)}"
    except (ValueError, KeyError, IndexError, AttributeError):
        return None


def koy_ay(anahtar: str, iso: str | None) -> None:
    """Ay anahtarını İKİ biçimde yazar: makine (ISO) ve okur ('<anahtar>_ad').

    Sayfa hangisini basacağına kendi karar verir; grafik ve tablo sıralaması
    ISO ister, okur cümlesi ad ister."""
    koy(anahtar, iso, None)
    ad = ay_okur(iso)
    if ad:
        koy(f"{anahtar}_ad", ad, None)


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
    # YAYIMLANAN AYIN SÜRPRİZİ: anket ne diyordu, ne geldi. Sayının kendisi
    # kadar anketin KENDİ hata dağılımı da sayfaya çıkar — 0,2 puanlık bir
    # sapmanın sürpriz olup olmadığı ancak onunla okunur.
    _sa = bi.get("son_ay") or {}
    if _sa:
        koy("anket_ay", _sa.get("ad"), None)
        koy("anket_ay_bek", _sa.get("anket"), 2)
        koy("anket_ay_gercek", _sa.get("gercek"), 2)
        koy("anket_ay_surpriz", _sa.get("surpriz"), 2)
        # HÜKÜM KODDA: eşik anketin ölçülmüş ortalama mutlak hatasıdır, sabit
        # bir sayı değil; örneklem büyüdükçe eşik de değişmelidir.
        _mae = (bi.get("h0", {}).get("p36") or {}).get("mae")
        _sp = _sa.get("surpriz")
        if _mae and _sp is not None:
            koy("anket_ay_hukum",
                ("anketin ortalama mutlak hatasının altında — bu ölçüye göre "
                 "sürpriz sayılmaz" if abs(_sp) <= _mae else
                 "anketin ortalama mutlak hatasını aşıyor — bu ölçüye göre "
                 "sürpriz"), None)
            koy("anket_ay_mae_kati", abs(_sp) / _mae, 2)
    for h, kis in (("h1", "1"), ("h2", "2")):
        _il = (bi.get("ileri") or {}).get(h) or {}
        if _il:
            koy(f"anket_ileri{kis}_ad", _il.get("ad"), None)
            koy(f"anket_ileri{kis}", _il.get("oran"), 2)

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
        # MOMENTUM PATİKASININ DİBİ: yıllık enflasyon bu senaryoda önce
        # DÜŞÜP sonra geri tırmanıyor, çünkü elverişli baz Eylül–Ekim'de,
        # elverişsiz baz Kasım–Aralık'ta. Yalnız yıl sonunu yazmak bu V'yi
        # gizler ve aradaki dip, kararın alındığı aylara denk geliyor.
        if "son3_sa" in bz.columns:
            _s = bz["son3_sa"].dropna()
            if len(_s):
                _i = int(_s.idxmin())
                koy("baz_momentum_dip", float(_s.min()), 2)
                _dt = bz["tarih"].iloc[_i]
                O["baz_momentum_dip_ay"] = f"{AY_TR[_dt.month]} {_dt.year}"
                koy("baz_momentum_ilk", float(_s.iloc[0]), 2)
                O["baz_momentum_ilk_ay"] = (
                    f"{AY_TR[bz['tarih'].iloc[0].month]} {bz['tarih'].iloc[0].year}")
        # DÜŞEN AYLAR AY AY: patikanın şeklini açıklayan sayı bunlar. Yalnız
        # "elverişli aylar" cümlesi hangi ayın ne kadar elverişli olduğunu
        # söylemiyor.
        for _t, _o in zip(bz["tarih"], bz["dusen_aylik"]):
            koy(f"baz_dus_{_t.month:02d}", float(_o), 2)
    except Exception as ex:
        uyar(f"baz_senaryo.csv okunamadı ({ex}) — 'baz_dusen' anahtarı atlandı.")

    # YIL SONU ARİTMETİĞİ: anketin yıl sonu tahmini kalan aylarda ne oran ister,
    # bugünkü momentum ne veriyor. İkisi arasındaki açık, "beklenti mi momentum
    # mu" tartışmasının tek sayıya indirgenmiş hâli.
    ys = m.get("yilsonu") or {}
    if ys:
        koy("ys_kumulatif", ys.get("kumulatif"), 2)
        koy("ys_anket", ys.get("anket"), 2)
        koy("ys_kalan_ay", ys.get("kalan_ay"), 0)
        koy("ys_gereken_aylik", ys.get("gereken_aylik"), 2)
        koy("ys_momentum_aylik", ys.get("momentum_aylik"), 2)
        koy("ys_acik_puan", ys.get("acik_puan"), 2)

    # ------------------------------------------------- ana harcama grupları
    # KAYNAK, İSTATİSTİK KURUMUNUN KENDİ TABLOSUDUR. Bu hattın katkı
    # ayrıştırması özel kapsamlı eksende (gıda · enerji · temel mal ·
    # alkol-tütün-altın · hizmet) kuruluyor; on üç harcama grubu ekseni ayrı
    # bir kırılım ve o eksende resmî tablo hem daha erken hem daha kesin.
    # KİMLİK yine sorulur: katkılar manşete toplanmıyorsa hiçbir anahtar
    # yazılmaz — yarım bir tablo, olmayan bir tablodan tehlikelidir.
    try:
        yy = json.loads((PROJE / "tuik_yayim.json").read_text(encoding="utf-8"))
    except Exception:
        yy = {}
    _say = m.get("son_ay")
    _ay_s = _say[:7] if _say else None
    _gr = ((yy.get("gruplar") or {}).get(_ay_s) or {}) if _ay_s else {}
    _manset = O.get("tufe_aylik")
    if _gr and _manset is not None:
        _top = sum(float(v.get("katki", 0)) for v in _gr.values())
        if abs(_top - float(_manset)) > 0.02:
            uyar(f"GRUP KATKISI KİMLİĞİ TUTMADI ({_ay_s}): toplam {_top:.2f}, "
                 f"manşet {_manset:.2f} — grup anahtarları yazılmadı.")
        else:
            for kod, blok in _gr.items():
                koy(f"grup{kod}_aylik", blok.get("aylik"), 2)
                koy(f"grup{kod}_katki", blok.get("katki"), 2)
                O[f"grup{kod}_ad"] = veri.ANA_GRUP_AD.get(kod, kod)
            # YOĞUNLAŞMA: manşetin ne kadarı kaç gruptan geliyor. Grup ADI da
            # yazılır — sayfa "ulaştırma" diye sabitlenirse bir sonraki ay
            # yalan söyler.
            _sir = sorted(_gr.items(), key=lambda kv: -float(kv[1].get("katki", 0)))
            _en = _sir[0]
            O["katki_en_ad"] = veri.ANA_GRUP_AD.get(_en[0], _en[0])
            koy("katki_en_puan", float(_en[1].get("katki", 0)), 2)
            koy("katki_en_pay", float(_en[1].get("katki", 0)) / float(_manset) * 100, 0)
            _u3 = sum(float(v.get("katki", 0)) for _, v in _sir[:3])
            koy("ilk3_katki", _u3, 2)
            koy("ilk3_pay", _u3 / float(_manset) * 100, 0)
            O["ilk3_ad"] = " · ".join(veri.ANA_GRUP_AD.get(k, k) for k, _ in _sir[:3])
            _son = _sir[-1]
            O["katki_en_dusuk_ad"] = veri.ANA_GRUP_AD.get(_son[0], _son[0])
            koy("katki_en_dusuk_puan", float(_son[1].get("katki", 0)), 2)
    # ALT SINIF SAYIMI: kaç ürün arttı, kaç azaldı. Yayılımın en ham ölçüsü.
    _mn = ((yy.get("mansetler") or {}).get(_ay_s) or {}) if _ay_s else {}
    for _a in ("alt_sinif_artan", "alt_sinif_azalan", "alt_sinif_degismeyen",
               "alt_sinif_toplam"):
        koy(_a, _mn.get(_a), 0)

    # KESİT ARINDIRMASININ KAPSAMI: kaç grup arındırılmadan geçti, ağırlıkça
    # ne kadar. Difüzyon ve kırpılmış ortalama bu kesitten çıkıyor; kapsamı
    # yazılmazsa okur ölçünün ne kadarının arındırılmış olduğunu bilemez.
    _kt = m.get("kesit_tani") or {}
    koy("kesit_n", _kt.get("n"), 0)
    koy("kesit_arindirilmayan", _kt.get("arindirilmayan_n"), 0)
    koy("kesit_arindirilmayan_agirlik", _kt.get("arindirilmayan_agirlik"), 1)
    koy("kesit_tatil_gecen", _kt.get("tatil_gecen_n"), 0)

    # ANKETİN FAİZ PATİKASI: 12 ay sonrası politika faizi beklentisi bugünkü
    # seviyeden kaç baz puan aşağıda. Fark okurun aradığı sayı; iki seviyeyi
    # yan yana yazıp çıkarmayı ona bırakmak, sayfanın işi değil.
    _pf = m.get("reel__faiz")
    _bf = O.get("bek_faiz_12a")
    if _pf is not None and _bf is not None:
        koy("bek_faiz_indirim_bp", (float(_pf) - float(_bf)) * 100, 0)

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
        # ÖRNEKLEM İKİ TÜRLÜDÜR ve sayfa ikisini de anmak zorunda: TAM örneklem
        # (tabloda ve grafikte görünen) ile KESTİRİM örneklemi (dışlanan yıllar
        # çıkarılmış). Tek bir "n" yazmak, okuru grafikte saydığı aylarla
        # metindeki n arasında çelişkiye düşürürdü.
        koy("itp_pencere", ip.get("pencere_ay"), 0)
        koy("itp_n", ip.get("n_toplam"), 0)           # kestirim örneklemi
        koy("itp_ilk_ay", ip.get("ilk_ay"), None)
        koy("itp_son_ay", ip.get("son_ay"), None)
        koy("itp_n_tam", ip.get("n_tam"), 0)          # tam örneklem
        koy("itp_tam_ilk_ay", ip.get("tam_ilk_ay"), None)
        koy("itp_tam_son_ay", ip.get("tam_son_ay"), None)
        for k, o_ in (("ort", 2), ("medyan", 2), ("std", 2), ("min", 2),
                      ("maks", 2), ("mutlak_ort", 2), ("ustte_pay", 0),
                      ("t", 2), ("p", 4)):
            koy(f"itp_{k}", f_.get("ito_ustte_pay" if k == "ustte_pay" else k), o_)
        koy("itp_min_ay", f_.get("min_ay"), None)
        koy("itp_maks_ay", f_.get("maks_ay"), None)
        # Kestirim örnekleminin TAMAMI (yalnız son 24 ay değil).
        ft = ip.get("fark_tum") or {}
        for k, o_ in (("ort", 2), ("medyan", 2), ("std", 2), ("mutlak_ort", 2),
                      ("ustte_pay", 0), ("t", 2), ("p", 4), ("n", 0),
                      ("min", 2), ("maks", 2)):
            koy(f"itp_tum_{k}", ft.get("ito_ustte_pay" if k == "ustte_pay" else k), o_)
        koy_ay("itp_tum_min_ay", ft.get("min_ay"))
        koy_ay("itp_tum_maks_ay", ft.get("maks_ay"))
        for k in ("sabit", "egim", "se_egim", "se_sabit", "r", "spearman",
                  "r2", "se_artik"):
            koy(f"itp_{k}", r_.get(k), 3)
        koy("itp_t_bir", r_.get("t_egim_bir"), 2)
        koy("itp_p_bir", r_.get("p_egim_bir"), 4)

        # ---- KİMLİK DOĞRULAMASI. Serinin ne olduğu adına bakarak değil,
        # İTO'nun kendi yayımıyla tutmasıyla biliniyor; ölçü sayfada durmalı.
        km = ip.get("kimlik") or {}
        koy("itp_k_ortak", km.get("ortak_ay"), 0)
        koy("itp_k_maks_sapma", km.get("maks_sapma"), 4)
        koy("itp_k_ort_sapma", km.get("ort_sapma"), 4)
        koy("itp_k_esik", km.get("esik"), 2)
        koy("itp_k_sapan", km.get("sapan_ay"), 0)
        koy("itp_k_dolduruldu_n", km.get("dolduruldu_n"), 0)
        koy("itp_k_dolduruldu", ", ".join(km.get("dolduruldu") or []) or "yok", None)
        koy("itp_k_hukum",
            ("seri İTO'nun yayımıyla tutuyor — kimlik sayıyla doğrulandı"
             if km.get("dogrulandi") else
             "SERİ İTO'NUN YAYIMIYLA TUTMUYOR — sayfadaki İTO iddiaları "
             "güvenilmez, hattın kaynağı gözden geçirilmeli"), None)
        ms = (km.get("manset") or [{}])[0]
        koy("itp_k_yillik_bizim", ms.get("yillik_bizim"), 2)
        koy("itp_k_yillik_ito", ms.get("yillik_ito"), 2)
        koy("itp_k_yilsonu_bizim", ms.get("yilsonu_bizim"), 2)
        koy("itp_k_yilsonu_ito", ms.get("yilsonu_ito"), 2)

        # ---- DIŞLAMA: kararın kendisi ve gerekçesinin ÖLÇÜSÜ
        ds = ip.get("dislama") or {}
        koy("itp_d_n", ds.get("n"), 0)
        koy("itp_d_yillar", ", ".join(str(y) for y in ds.get("yillar") or []), None)
        koy("itp_d_ilk_ay", ds.get("ilk_ay"), None)
        koy("itp_d_son_ay", ds.get("son_ay"), None)
        df_ = ds.get("fark") or {}
        for k, o_ in (("ort", 2), ("medyan", 2), ("std", 2), ("min", 2),
                      ("maks", 2), ("mutlak_ort", 2), ("ustte_pay", 0)):
            koy(f"itp_d_{k}", df_.get("ito_ustte_pay" if k == "ustte_pay" else k), o_)
        koy("itp_d_min_ay", df_.get("min_ay"), None)
        koy("itp_d_maks_ay", df_.get("maks_ay"), None)
        for k in ("tufe_min", "tufe_maks", "tufe_std", "ito_std",
                  "kalan_tufe_std", "kalan_tufe_min", "kalan_tufe_maks",
                  "std_orani", "tufe_std_orani"):
            koy(f"itp_d_{k}", ds.get(k), 2)
        koy("itp_d_welch_t", ds.get("welch_t"), 2)
        koy("itp_d_welch_p", ds.get("welch_p"), 4)
        # DIŞLAMANIN GEREKÇESİ İKİ AYRI SORUDUR ve ikisi de ölçülüyor:
        # ortalama fark ayrışıyor mu (Welch) ve OYNAKLIK ayrışıyor mu (std
        # oranı). Rejim yılı iddiası asıl ikincisidir; ortalama aynı çıksa
        # bile dört kat oynak bir dönem kestirimi kendine çeker.
        # HÜKÜM ÜÇ HÂLLİDİR. n=0 iken "ayrışmıyor" yazmak, yapılmamış bir
        # sınamanın sonucunu bildirmek olurdu: dışlanacak ay yoksa Welch
        # sınaması hiç koşmuyor. Sayfa bu anahtarı koşulsuz bastığı için
        # üçüncü hâl açıkça yazılıyor.
        koy("itp_d_hukum",
            ("bugün dışlanan ay yok — kural kurulu ama örneklemde o yıllar "
             "hiç bulunmuyor, dolayısıyla karşılaştırma da yapılmadı"
             if not ds.get("n") else
             "dışlanan dönemin ortalama farkı kalan örneklemden ayrışıyor"
             if ds.get("ort_ayrisiyor") else
             "ortalama fark istatistiksel olarak ayrışmıyor; dışlamanın "
             "gerekçesi ortalama değil OYNAKLIK"), None)

        # ---- DIŞLAMANIN SONUCU: aynı kod, iki örneklem
        ka = ip.get("karsilastirma") or {}
        if ka:
            koy("itp_k_n_dahil", ka.get("n_dahil"), 0)
            koy("itp_k_n_haric", ka.get("n_haric"), 0)
            for yon in ("dahil", "haric"):
                blok = ka.get(yon) or {}
                for k in ("egim", "se_egim", "sabit", "r", "r2", "se_artik",
                          "s_egim", "s_t", "s_r2"):
                    koy(f"itp_{yon}_{k}", blok.get(k), 3)
                koy(f"itp_{yon}_p_bir", blok.get("p_egim_bir"), 4)
                koy(f"itp_{yon}_kazanan", blok.get("kazanan"), None)

        ku = ip.get("kural") or {}
        sk, skd = ku.get("skor") or {}, ku.get("skor_dar") or {}
        koy("itp_k_n", ku.get("n"), 0)
        koy("itp_k_ilk", ku.get("ilk_ay"), None)
        koy("itp_k_son", ku.get("son_ay"), None)
        koy("itp_k_asgari", ku.get("asgari"), 0)
        koy("itp_k_asgari_dar", ku.get("asgari_dar"), 0)
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
            koy("itp_s_se_sabit", sp.get("se_sabit"), 3)
            koy("itp_s_t_sabit", sp.get("t_sabit"), 2)
            koy("itp_s_p_sabit", sp.get("p_sabit"), 4)
            koy("itp_s_sabit_hukum",
                ("sabit sıfırdan ayrışıyor: anket bu örneklemde sistematik yanlı"
                 if sp.get("sabit_anlamli") else
                 "sabit sıfırdan ayırt edilemiyor — İTO ankete denk geldiğinde "
                 "kanalın söyleyecek bir şeyi yok"), None)
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

        # ---- BEKLEYEN AY (İTO geldi, TÜFE bekleniyor) ya da son ayın KARNESİ
        bk = ip.get("bekleyen") or {}
        if bk:
            koy("itp_b_ay", bk.get("ay"), None)
            koy("itp_b_ad", bk.get("ad"), None)
            koy("itp_b_ito", bk.get("ito"), 2)
            koy("itp_b_n", bk.get("n_gecmis"), 0)
            for k in ("naif", "sabit", "oransal", "regresyon", "alt", "ust"):
                koy(f"itp_b_{k}", bk.get(k), 2)
            koy("itp_b_ayni_n", bk.get("ayni_ay_n"), 0)
            koy("itp_b_ayni_ort", bk.get("ayni_ay_ort_fark"), 2)
            koy("itp_b_takvimli", bk.get("takvimli"), 2)
            koy("itp_b_ayni_t", bk.get("ayni_ay_t"), 2)
            koy("itp_b_ayni_p", bk.get("ayni_ay_p"), 3)
            koy("itp_b_ayni_ayrim", bk.get("ayni_ay_genel_ayrim"), 2)
            # HÜKÜM KODDA. "Ağustos'ta fark daha küçük gelir" cümlesi ancak
            # o ayın farkı diğer aylardan ayrışıyorsa kurulabilir; MDX'e elle
            # yazılırsa bir sonraki ay yanlış hüküm basılır.
            if bk.get("ayni_ay_p") is not None:
                koy("itp_b_ayni_hukum",
                    (f"{bk.get('ad', '').split()[0]} ayının farkı diğer aylardan "
                     f"ölçülebilir biçimde ayrışıyor"
                     if bk.get("ayni_ay_ayrisiyor") else
                     f"{bk.get('ad', '').split()[0]} ayının farkı diğer aylardan "
                     f"AYRIŞMIYOR (p = "
                     + f"{bk['ayni_ay_p']:.3f}".replace(".", ",") +
                     f", n = {bk.get('ayni_ay_n')}); elimizdeki şey bir kural "
                     f"değil, birkaç gözlemin ortalaması"), None)
            # ÖZET CÜMLESİ İKİ HÂLLİ. Yönetici özeti bu tek anahtarı basıyor;
            # "gerçekleşen" alanı ay beklerken YOK ve MDX onu koşulsuz
            # çağırırsa sayfa sınavı (haklı olarak) düşer. Şeklin değiştiği
            # yerde metin de koddan gelmeli.
            def _t(v, n=2):
                return f"{v:.{n}f}".replace(".", ",") if v is not None else "—"
            if bk.get("beklemede"):
                koy("itp_b_ozet_metin",
                    f"{bk.get('ad')} İTO'su %{_t(bk.get('ito'))} geldi; "
                    f"kurallar TÜFE için %{_t(bk.get('sabit'))}–%{_t(bk.get('regresyon'))} "
                    f"bandını, piyasa anketi ise %{_t(bk.get('anket'))} diyor. "
                    f"TÜFE yayımlanınca blok karneye döner", None)
            else:
                koy("itp_b_ozet_metin",
                    f"{bk.get('ad')}: İTO %{_t(bk.get('ito'))} geldi, sabit kaydırma "
                    f"%{_t(bk.get('sabit'))} dedi, gerçekleşen "
                    f"%{_t(bk.get('gercek'))}", None)
            koy("itp_b_kaynak", bk.get("ito_kaynak"), None)
            koy("itp_b_elle",
                ("EVDS bu ayı henüz yayımlamadı; okuma elle girildi ve kaynağı "
                 "yukarıda yazılı. EVDS yayımladığı an iki sayı karşılaştırılır."
                 if bk.get("ito_elle") else
                 "okuma EVDS'ten geliyor"), None)
            koy("itp_b_anket", bk.get("anket"), 2)
            koy("itp_b_sapma", bk.get("ito_sapma"), 2)
            koy("itp_b_surpriz", bk.get("beklenen_surpriz"), 2)
            koy("itp_b_surpriz_tufe", bk.get("surprizden_tufe"), 2)
            koy("itp_b_gercek", bk.get("gercek"), 2)
            for k in ("naif", "sabit", "oransal", "regresyon"):
                koy(f"itp_b_hata_{k}", bk.get(f"hata_{k}"), 2)
            koy("itp_b_ayni_ay", bk.get("ayni_ay"), None)
            # DURUM METNİ: sayfa aynı bloğu iki hâlde de basıyor. Hangi hâlde
            # olduğunu MDX'e yazmak, bir gün yanlış hâli basmak demekti.
            if bk.get("beklemede"):
                koy("itp_b_durum",
                    f"{bk.get('ad')} İTO'su yayımlandı, TÜFE henüz gelmedi — "
                    f"aşağıdaki sayılar TAHMİNDİR", None)
            else:
                ger = bk.get("gercek")
                g_tr = f"{ger:.2f}".replace(".", ",")
                koy("itp_b_durum",
                    f"{bk.get('ad')} TÜFE'si yayımlandı: %{g_tr}. Aşağıdaki "
                    "tahminler o gün, YALNIZ o aya kadarki veriyle kurulmuş "
                    "olsaydı ne verirdi — karnesiyle birlikte", None)
                koy("itp_b_aralik_tuttu",
                    "öngörü aralığı gerçekleşmeyi İÇERDİ" if bk.get("aralik_tuttu")
                    else "öngörü aralığı gerçekleşmeyi KAÇIRDI", None)
                # En iyi kural bu ay hangisiydi (mutlak hata en küçük)
                hatalar = {k: abs(bk[f"hata_{k}"]) for k in
                           ("naif", "sabit", "oransal", "regresyon")
                           if bk.get(f"hata_{k}") is not None}
                if hatalar:
                    en = min(hatalar, key=hatalar.get)
                    AD = {"naif": "naif kural", "sabit": "sabit kaydırma",
                          "oransal": "oransal kural", "regresyon": "regresyon"}
                    koy("itp_b_en_iyi", AD[en], None)
                    koy("itp_b_en_iyi_hata", hatalar[en], 2)

            # ---- TAHMİN BULUTU. Nokta tahmin okura sahte bir kesinlik verir
            # ve en çok sorulan soruyu hiç cevaplamaz: TÜFE İTO'nun ÜSTÜNDE
            # gelebilir mi? Üç kuruluş yan yana basılıyor çünkü tek kuruluş
            # modelin kendisini gizler; aralarındaki fark okurun görmesi
            # gereken belirsizliğin bir parçası.
            bl = bk.get("bulut") or {}
            if bl:
                koy("itp_bulut_n", bl.get("n"), 0)
                koy("itp_bulut_ito", bl.get("ito"), 2)
                koy("itp_bulut_merkez_reg", bl.get("merkez_reg"), 2)
                koy("itp_bulut_merkez_sabit", bl.get("merkez_sabit"), 2)
                koy("itp_bulut_carpiklik", bl.get("carpiklik"), 2)
                koy("itp_bulut_shapiro", bl.get("shapiro_p"), 3)
                pu = bl.get("p_ustunde") or {}
                koy("itp_bulut_p_par", pu.get("parametrik"), 0)
                koy("itp_bulut_p_amp", pu.get("ampirik"), 0)
                koy("itp_bulut_p_tar", pu.get("tarihsel"), 0)
                koy("itp_bulut_ustunde_n", bl.get("ustunde_n"), 0)
                # Yüzdelikler: her kuruluş için ayrı anahtar. Tablo MDX'te
                # elle yazılamaz — sayılar her ay değişiyor.
                KIS = {"parametrik": "a", "ampirik": "b", "tarihsel": "c"}
                for kur, kis in KIS.items():
                    v = bl.get(f"y_{kur}") or []
                    for i, q in enumerate(bl.get("yuzdelikler") or []):
                        if i < len(v):
                            koy(f"itp_bulut_{kis}_p{q}", v[i], 2)
                for e in bl.get("esik") or []:
                    ad = f"{e['esik']:.1f}".replace(".", "")
                    koy(f"itp_bulut_{'ust' if e['yon'] == '>' else 'alt'}{ad}",
                        e.get("p"), 0)
                # HÜKÜM KODDA: "gelebilir" ile "gelemez" arasındaki fark bir
                # sayıdan geliyor; o sayı değişince cümlenin de değişmesi
                # gerekir. MDX'e elle yazılsaydı bir ay sonra yanlış olurdu.
                un = bl.get("ustunde_n") or 0
                if un:
                    koy("itp_bulut_hukum",
                        f"gelebilir: örneklemin {bl.get('n')} ayının {un}'inde "
                        f"TÜFE İTO'nun ÜSTÜNDE geldi. Bu ay için olasılık "
                        f"%{pu.get('ampirik', 0):.0f} (ampirik) — düşük ama "
                        f"yok sayılacak kadar değil", None)
                else:
                    koy("itp_bulut_hukum",
                        f"bu örneklemin {bl.get('n')} ayının HİÇBİRİNDE TÜFE "
                        f"İTO'nun üstünde gelmedi", None)
                # ZAMAN KİPİ KODDA: aynı bölüm ay beklerken de, TÜFE geldikten
                # sonra da basılıyor. "gelebilir mi" cümlesi karne kipinde
                # geçmiş zamana dönmeli — MDX'e tek kip yazmak, ayın yarısında
                # yanlış kipi yayımlamak demekti.
                koy("itp_bulut_zaman",
                    ("aşağıdaki bulut, TÜFE yayımlanmadan ÖNCE, yalnız bu aya "
                     "kadarki veriyle kuruldu"
                     if bk.get("beklemede") else
                     "aşağıdaki bulut o gün, TÜFE yayımlanmadan önceki veriyle "
                     "kurulmuş olsaydı böyle görünecekti; gerçekleşme yukarıda"),
                    None)
                ua = bl.get("ustunde_aylar") or []
                if ua:
                    en_b = min(ua, key=lambda r: r["fark"])
                    koy_ay("itp_bulut_en_ay", en_b.get("ay"))
                    koy("itp_bulut_en_fark", abs(en_b.get("fark", 0)), 2)
                    koy("itp_bulut_ustunde_aylar", ua, None)
                    koy("itp_bulut_ustunde_metin",
                        " · ".join(ay_okur(r["ay"]) or r["ay"] for r in ua), None)

        yo = ip.get("yillik_ozet") or {}
        for k in ("ort", "son", "maks", "min", "son_ito", "son_tufe"):
            koy(f"itp_y_{k}", yo.get(k), 2)
        koy_ay("itp_y_maks_ay", yo.get("maks_ay"))

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

    # ------------------------------------------------- ÜGE (ücretliler geçinme)
    # AYRI DOSYA, AYRI KOŞUL: İTO'nun tüketici endeksi üretilemese bile ÜGE
    # ölçümü ayakta kalabilir ve tersi de doğru. Tek koşula bağlanırsa biri
    # düştüğünde sayfa iki bölümü birden statik yedeğe düşürürdü.
    ugy = VERI / "uge_profil.json"
    up = json.loads(ugy.read_text(encoding="utf-8")) if ugy.exists() else {}
    if not up.get("n"):
        uyar("uge_profil.json yok ya da boş — ÜGE anahtarları atlandı.")
    else:
        koy("uge_n", up.get("n"), 0)
        koy("uge_ilk_ay", up.get("ilk_ay"), None)
        koy("uge_son_ay", up.get("son_ay"), None)
        # Üç fark birden: ÜGE−TÜFE, İTO−TÜFE, ÜGE−İTO. Üçüncüsü olmadan okur
        # ayrışmanın ne kadarının ÜGE'ye ait olduğunu göremez.
        for on, blok in (("uge_ut", "uge_tufe"), ("uge_it", "ito_tufe"),
                         ("uge_ui", "uge_ito")):
            f = up.get(blok) or {}
            for k in ("ort", "medyan", "std", "min", "maks", "mutlak_ort"):
                koy(f"{on}_{k}", f.get(k), 2)
            koy(f"{on}_t", f.get("t"), 2)
            koy(f"{on}_p", f.get("p"), 4)
            koy(f"{on}_ustte_pay", f.get("ito_ustte_pay"), 0)
            koy(f"{on}_maks_ay", f.get("maks_ay"), None)
            koy(f"{on}_min_ay", f.get("min_ay"), None)
        for on, blok in (("uge_ruge", "reg_uge"), ("uge_rito", "reg_ito")):
            r = up.get(blok) or {}
            for k in ("sabit", "egim", "se_egim", "r", "r2", "sigma"):
                koy(f"{on}_{k}", r.get(k), 3)
            koy(f"{on}_t_bir", r.get("t_bir"), 2)
            koy(f"{on}_p_bir", r.get("p_bir"), 4)
        ya = up.get("yaris") or {}
        for k in ("mae_uge", "mae_ito", "esli_fark"):
            koy(f"uge_{k}", ya.get(k), 3)
        koy("uge_yaris_n", ya.get("n"), 0)
        koy("uge_yaris_ilk_ay", ya.get("ilk_ay"), None)
        koy("uge_esli_t", ya.get("esli_t"), 2)
        koy("uge_esli_p", ya.get("esli_p"), 3)
        koy("uge_yaris_hukum", ya.get("hukum"), None)
        bk = up.get("bekleyen") or {}
        koy("uge_b_ay", bk.get("ay"), None)
        koy("uge_b_ad", bk.get("ad"), None)
        koy("uge_b_uge", bk.get("uge"), 2)
        koy("uge_b_sabit", bk.get("sabit"), 2)
        koy("uge_b_regresyon", bk.get("regresyon"), 2)
        koy("uge_b_n", bk.get("n_gecmis"), 0)
        ki = up.get("kimlik") or {}
        koy("uge_k_ortak", ki.get("ortak"), 0)
        koy("uge_k_maks_sapma", ki.get("maks_sapma"), 4)
        koy("uge_k_ort_sapma", ki.get("ort_sapma"), 4)
        koy("uge_k_sapan", ki.get("sapan"), 0)
        va = up.get("varyant") or {}
        koy("uge_v_son_95", va.get("son_95"), 2)
        koy("uge_v_son_85", va.get("son_85"), 2)
        koy("uge_v_ort_fark", va.get("ort_mutlak_fark"), 2)
        koy("uge_v_maks_fark", va.get("maks_mutlak_fark"), 2)
        koy_ay("uge_v_maks_ay", va.get("maks_ay"))
        koy("uge_v_n", va.get("n"), 0)
        # HÜKÜM KODDA: "hangi endeks daha yukarıda" cümlesi iki ortalamanın
        # sırasına bağlı ve o sıra değişebilir.
        ut, it_ = (up.get("uge_tufe") or {}), (up.get("ito_tufe") or {})
        if ut.get("ort") is not None and it_.get("ort") is not None:
            fark = ut["ort"] - it_["ort"]
            koy("uge_kiyas_hukum",
                (f"ÜGE, TÜFE'den ortalama "
                 + f"{ut['ort']:.2f}".replace(".", ",") + " puan yukarıda; "
                 f"İTO'nun tüketici endeksi ise "
                 + f"{it_['ort']:.2f}".replace(".", ",") + " puan. Aradaki "
                 + f"{abs(fark):.2f}".replace(".", ",") + " puanlık açıklık "
                 + ("ÜGE" if fark > 0 else "tüketici endeksi") +
                 " tarafında"), None)

    # ------------------------------------------------ ÜÇLÜ BİRLEŞİK TAHMİN
    biy = VERI / "birlesik.json"
    bp = json.loads(biy.read_text(encoding="utf-8")) if biy.exists() else {}
    if not bp.get("n"):
        uyar("birlesik.json yok ya da boş — birleşik tahmin anahtarları atlandı.")
    else:
        koy("br_n", bp.get("n"), 0)
        koy_ay("br_ilk_ay", bp.get("ilk_ay"))
        koy_ay("br_son_ay", bp.get("son_ay"))
        koy("br_r_ito_uge", bp.get("r_ito_uge"), 3)
        koy("br_adj_kazanc", bp.get("adj_kazanc"), 4)
        for on, blok in (("br_i", "ito"), ("br_u", "uge"), ("br_b", "birlesik")):
            mm = bp.get(blok) or {}
            for k in ("r2", "adj_r2", "sigma", "sabit"):
                koy(f"{on}_{k}", mm.get(k), 3)
            for c in ("ito", "uge"):
                if f"b_{c}" in mm:
                    koy(f"{on}_b_{c}", mm[f"b_{c}"], 3)
                    koy(f"{on}_se_{c}", mm[f"se_{c}"], 3)
                    koy(f"{on}_t_{c}", mm[f"t_{c}"], 2)
                    koy(f"{on}_p_{c}", mm[f"p_{c}"], 4)
        # KAPSAMA HÜKMÜ: hangi öncünün hangisini kapsadığı katsayıdan çıkar.
        kap = bp.get("kapsama")
        koy("br_kapsama_hukum", {
            "ito": ("İTO'nun tüketici endeksi ÜGE'yi KAPSIYOR: ikisi aynı "
                    "regresyona konduğunda ÜGE'nin katsayısı sıfırdan ayırt "
                    "edilemiyor, tüketici endeksininki ise güçlü kalıyor"),
            "uge": ("ÜGE tüketici endeksini KAPSIYOR: birleşik modelde yalnız "
                    "ÜGE'nin katsayısı anlamlı"),
            "ikisi": ("iki öncü de birleşik modelde anlamlı — ikisi ayrı bilgi "
                      "taşıyor"),
            "hicbiri": ("birleşik modelde iki katsayı da anlamsız; bu, ikisinin "
                        "birbirine çok yakın olmasının işareti"),
        }.get(kap, ""), None)
        ya = bp.get("yaris") or {}
        koy("br_yaris_n", ya.get("n"), 0)
        koy("br_yaris_ilk_ay", ya.get("ilk_ay"), None)
        koy("br_en_iyi_ad", ya.get("en_iyi_ad"), None)
        koy("br_yaris_hukum", ya.get("hukum"), None)
        KIS = {"ito_sabit": "is", "uge_sabit": "us", "ito_reg": "ir",
               "uge_reg": "ur", "birlesik_reg": "br", "esit_ortalama": "eo",
               "ters_mse": "tm"}
        for ad, kis in KIS.items():
            v = (ya.get("adaylar") or {}).get(ad) or {}
            koy(f"br_{kis}_mae", v.get("mae"), 3)
            koy(f"br_{kis}_rmse", v.get("rmse"), 3)
            koy(f"br_{kis}_yanlilik", v.get("yanlilik"), 3)
            koy(f"br_{kis}_p", v.get("p_vs_en_iyi"), 3)
        bk = bp.get("bekleyen") or {}
        if bk:
            koy("br_b_ay", bk.get("ay"), None)
            koy("br_b_ad", bk.get("ad"), None)
            koy("br_b_ito", bk.get("ito"), 2)
            koy("br_b_uge", bk.get("uge"), 2)
            koy("br_b_merkez", bk.get("merkez"), 2)
            koy("br_b_merkez_ad", bk.get("en_iyi_ad"), None)
            koy("br_b_yayilim", bk.get("yayilim"), 2)
            koy("br_b_agirlik", bk.get("ters_mse_agirlik"), 2)
            koy("br_b_n", bk.get("n_gecmis"), 0)
            for ad, kis in KIS.items():
                koy(f"br_b_{kis}", (bk.get("tahmin") or {}).get(ad), 2)
            for q, v in zip(bk.get("yuzdelikler") or [], bk.get("bulut") or []):
                koy(f"br_b_p{q}", v, 2)
            koy("br_b_p_ito_ustu", bk.get("p_ito_ustu"), 0)
            for e in bk.get("esik") or []:
                ad_ = f"{e['esik']:.1f}".replace(".", "")
                koy(f"br_b_{'ust' if e['yon'] == '>' else 'alt'}{ad_}", e.get("p"), 0)
        # KARNE: yayımdan sonra tahminin kendisi kadar TUTUP TUTMADIĞI da
        # sayfada durur. Anahtarlar bekleyen ayınkiyle aynı kalıpta (br_k_*)
        # çünkü sayfa ikisini yan yana yazıyor.
        kr = bp.get("karne") or {}
        if kr:
            koy("br_k_ay", kr.get("ay"), None)
            koy("br_k_ad", kr.get("ad"), None)
            koy("br_k_ito", kr.get("ito"), 2)
            koy("br_k_uge", kr.get("uge"), 2)
            koy("br_k_gercek", kr.get("gercek"), 2)
            koy("br_k_merkez", kr.get("merkez"), 2)
            koy("br_k_merkez_ad", kr.get("en_iyi_ad"), None)
            koy("br_k_merkez_sapma", kr.get("merkez_sapma"), 2)
            koy("br_k_yayilim", kr.get("yayilim"), 2)
            koy("br_k_agirlik", kr.get("ters_mse_agirlik"), 2)
            koy("br_k_n", kr.get("n_gecmis"), 0)
            koy("br_k_en_yakin_ad", kr.get("en_yakin_ad"), None)
            koy("br_k_en_yakin_sapma", kr.get("en_yakin_sapma"), 2)
            koy("br_k_yuzdelik", kr.get("gercek_yuzdelik"), 0)
            koy("br_k_hukum", kr.get("hukum"), None)
            for ad, kis in KIS.items():
                koy(f"br_k_{kis}", (kr.get("tahmin") or {}).get(ad), 2)
                koy(f"br_k_{kis}_sapma", (kr.get("sapma") or {}).get(ad), 2)
            for q, v in zip(kr.get("yuzdelikler") or [], kr.get("bulut") or []):
                koy(f"br_k_p{q}", v, 2)
            koy("br_k_p_ito_ustu", kr.get("p_ito_ustu"), 0)
            for e in kr.get("esik") or []:
                ad_ = f"{e['esik']:.1f}".replace(".", "")
                on_ = "ust" if e["yon"] == ">" else "alt"
                koy(f"br_k_{on_}{ad_}", e.get("p"), 0)
                O[f"br_k_{on_}{ad_}_tuttu"] = "evet" if e.get("tuttu") else "hayır"
            # BANT HÜKMÜ KODDA: gerçekleşmenin hangi banda düştüğü, bandın
            # kendisinden okunur; metne sabit yazılırsa bir sonraki ay yalan
            # söyler.
            koy("br_k_bant", ("%50" if kr.get("bant_50") else
                              "%80" if kr.get("bant_80") else
                              "%90" if kr.get("bant_90") else "%90 dışı"), None)
            koy("br_k_tufe_ito_ustu", "evet" if kr.get("tufe_ito_ustu") else "hayır",
                None)
            koy("br_k_tufe_uge_ustu", "evet" if kr.get("tufe_uge_ustu") else "hayır",
                None)

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
