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

import metrik
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
    if ondalik is not None and isinstance(deger, str):
        # ÖLÇÜLEMEYEN GİRDİ, ÖLÇÜLEMEYEN ÇIKTI verir — çökme değil. Türetilmiş
        # bir anahtar boş bir bacaktan hesaplanıyorsa doğru cevap "—"dir;
        # `round(float("—"))` ise hattın adımını düşürür ve panoyu dondurur.
        # Yalnız YER TUTUCU böyle geçer: başka bir dizge gerçek bir kusurdur
        # ve ADIYLA patlar — sessizce boşa çevrilmez.
        if deger != OLCULEMEDI:
            raise TypeError(f"'{anahtar}' için sayı bekleniyordu, dizge geldi: "
                            f"{deger!r}")
        uyar(f"'{anahtar}' ölçülemeyen bir değerden türüyor — boş yazıldı.")
        O[anahtar] = OLCULEMEDI
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


# Sayfanın "—" ile boş bıraktığı ölçülemeyen değer. Anahtar SİLİNMEZ: sayfa
# anahtarı adıyla çağırıyor ve silinen anahtar yayın kapısında ENGEL olur
# (08.09.2026: `kiyas_*_9y_degisim_bp` düştü, yayın üç kez durdu); yer tutucu
# olsaydı okur statik yedekteki DONMUŞ sayıyı görürdü. Boş bir hücre ikisinden
# de dürüsttür — bileşen sayı olmayan değeri olduğu gibi basar.
OLCULEMEDI = "—"


def olculdu(*anahtarlar: str) -> bool:
    """Anahtar(lar) ÖLÇÜLDÜ mü — `"x" in O` bu soruyu ARTIK cevaplamaz.

    09.09.2026'da `anlik()` genelleştirildi: sayfanın adıyla çağırdığı anahtar
    ölçülemese de yazılır (OLCULEMEDI). Kural doğru, ama TÜKETİCİLERİNE
    uygulanmadı: o günden sonra `"x" in O` her zaman doğru döner ve türetilmiş
    anahtarların kapıları sessizce açık kaldı. Bedeli 15.09.2026'da ölçüldü —
    dokuz yıl düğümü toleransı aşınca `abs("—")` bu dosyayı düşürdü, hat komple
    atlandı, panosu dondu ve veri tazeleme yedi koşu boyunca kırmızı bitti.
    Türetilmiş bir anahtarın kapısı VARLIĞI değil DEĞERİ sorar."""
    return all(isinstance(O.get(a), (int, float)) and not isinstance(O.get(a), bool)
               for a in anahtarlar)


# Okura yazılan vade adları (kıyas uyarıları için).
VADE_AD = {"2y": "iki yıl", "1y": "bir yıl", "9y": "dokuz yıl"}

# Kıyas döngüsünün kapsamı — SÖZLEŞME, elle yazılmış bir kalıp DEĞİL.
KIYAS_DONEM = (("1ay", "kiyas_1ay"), ("3ay", "kiyas_3ay"), ("1yil", "kiyas_1yil"))
KIYAS_VADE = (("n2y", "2y"), ("n1y", "1y"), ("n9y", "9y"))


def kiyas_anahtarlari() -> set:
    """Kıyas döngüsünün ÜRETEBİLECEĞİ anahtarların tamamı — tek tanım.

    Duman sınaması "sayfa, döngünün üretmediği bir kıyas anahtarı çağırıyor
    mu" diye sorarken bu kümeyi okur. Eskiden orada elle yazılmış bir düzenli
    ifade duruyordu ve `_degisim_bp_tarih` sonekini HİÇ tanımıyordu — oysa
    döngü onu 08.09.2026 kararından beri her koşuda üretiyor (kaydırılmış
    bitiş günü okura o anahtarla gösterilir). Sayfa o anahtarı çağırdığı ilk
    gün sınama "üretilmemiş anahtar" deyip düşecek, `guncelle.py` hattı
    adımlardan ÖNCE atlayacak ve hat hiç koşmayacaktı — TÜFEX'in 10.09
    arızasının birebir eşi, kaynağı da aynı: bir kuralı ÖLÇEN ölçüt, kuralı
    yeniden yazarsa iki taraf sessizce ayrışır.

    ÜST KÜME olması tanımın parçası: ölçülemeyen bir kıyasta
    `_degisim_bp_tarih` yazılmaz. Soru "bugün üretildi mi" değil, "döngü bunu
    üretebilir mi"dir.
    """
    a: set = set()
    for _, etiket in KIYAS_DONEM:
        a.add(etiket)
        for _, sonek in KIYAS_VADE:
            a.add(f"{etiket}_{sonek}")
            a.add(f"{etiket}_{sonek}_degisim_bp")
            a.add(f"{etiket}_{sonek}_degisim_bp_tarih")
    return a



def ay_kisa(t) -> str:
    """Aylık SAAT yazımı — ortak/bicim sözleşmesi: `AA.YYYY`. Ayın günü
    YAZILMAZ ("01.08.2026" okura o günün ölçümü gibi görünür); Türkçe ay adı
    ("Ağustos 2026") saat anahtarında YASAK — bicim onu çözmez, çözülemeyen
    saat denetlenmeyen saattir."""
    t = pd.Timestamp(t)
    return f"{t.month:02d}.{t.year}"


# Aylık kökenli sayfa anahtarları → aylik.csv'de ait oldukları sütun. Saat
# (`<anahtar>_tarih`) ve okur etiketi (`<anahtar>_ay_ad`) bu eşlemeden yazılır.
AYLIK_ANAHTARLAR = (("pka_12a", "pka_12a"), ("pka_24a", "pka_24a"),
                    ("pka_5y", "pka_5y"), ("pka_faiz_12a", "pka_faiz_12a"),
                    ("pka_faiz_24a", "pka_faiz_24a"), ("pka_katilimci", "pka_12a_n"),
                    ("tufe_yillik", "tufe_2025"),
                    # Ortalamaya çevrilmiş anket serileri de ANKET AYINA aittir
                    # (günlüğe basamak olarak yayılıyorlar).
                    ("pka_ort_1y", "pka_12a"), ("pka_ort_2y", "pka_12a"),
                    ("pka_ort_5y", "pka_12a"), ("pka_ort_7y", "pka_12a"))


def aylik_saatleri(A: pd.DataFrame, eslesme=AYLIK_ANAHTARLAR) -> dict[str, str]:
    """Aylık anahtarların saati ve okur etiketi; `A` = data/aylik.csv.

    09.09.2026'da ölçüldü: on bir aylık saat anahtarı ("pka_12a_tarih",
    "tufe_yillik_tarih", "pka_ort_2y_tarih" …) "Ağustos 2026" diye Türkçe ay
    adıyla yazılıyordu. ortak/bicim ile lib/bicim bu yazımı ÇÖZMEZ; yani
    bileşenin bayatlık denetimi ve sayfa sınavının saat ölçütleri bu on bir
    anahtarı hiç görmüyordu — ayrıştıramayan bir denetim hep "sorun yok" der.
    Saat `AA.YYYY` yazılır, okura basılan etiket AYRI anahtardadır
    (`<anahtar>_ay_ad` = "Ağustos 2026") ve sayfa tabloda onu çağırır.
    """
    out: dict[str, str] = {}
    for hedef, kol in eslesme:
        if kol not in A.columns:
            continue
        s = A[kol].dropna()
        if s.empty:
            continue
        out[hedef + "_tarih"] = ay_kisa(s.index[-1])
        out[hedef + "_ay_ad"] = ay_ad(s.index[-1])
    return out


def anket_yayim_cumlesi(s_ay, yayim_gun: int) -> str:
    """Anketin yayım gününün VARSAYIM olduğu okura yazılır (09.09.2026'da
    ölçüldü: Piyasa Katılımcıları Anketi ulusal yayım takviminde ayrı kalem
    değil, seri yalnız ay etiketi taşıyor, hattın kayıtlarında gerçek yayım
    tarihi yok). Gün TEK tanımdan (metrik.yayim_gunu) gelir."""
    g = metrik.yayim_gunu(s_ay, yayim_gun)
    return ("Anketin yayım günü bir varsayımdır: Piyasa Katılımcıları Anketi "
            "resmî veri takviminde ayrı bir kalem olarak yer almıyor ve seri "
            f"yalnız ay etiketi taşıyor. Hat her ayın {metrik.gun_eki(yayim_gun)} "
            "(hafta sonuna denk gelirse ilk iş gününden) itibaren geçerli sayar — "
            f"{ay_ad(s_ay)} anketi için {tr_tarih(g)}.")


def kiyas_degisim(M: pd.DataFrame, s_gun: pd.Timestamp, g: pd.Timestamp, kol: str,
                  tolerans: int = ANLIK_TOLERANS_GUN):
    """Kıyas günü `g`den çıpaya değişim (baz puan) ve değişimin BİTİŞ günü.

    Çıpa gününün düğümü kurulamadıysa (vade boşluğu — dokuz yıl düğümü günlerin
    %16'sında yok) toleransın içindeki SON DOLU gün alınır ve bitiş o günle
    damgalanır: `<anahtar>_tarih` sözleşmesi, sayfa ipucunda o günü yazar.
    Başlangıç sıkı: kıyas günü boşsa ölçü yoktur — kaydırılan bir başlangıcın
    sayfada yeri yok, kıyas günü başlıkta tek bir tarih olarak duruyor.
    Ölçülemezse None; anahtar yine de yazılır (OLCULEMEDI)."""
    if kol not in M.columns or g not in M.index:
        return None
    v0 = M.loc[g, kol]
    try:
        v0 = float(v0)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(v0):
        return None
    seri = M.loc[:s_gun, kol].dropna()
    seri = seri[np.isfinite(seri.astype(float))]
    if seri.empty:
        return None
    t1 = pd.Timestamp(seri.index[-1])
    if (pd.Timestamp(s_gun) - t1).days > tolerans:
        return None
    return (float(seri.iloc[-1]) - v0) * 100.0, t1


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
        # AYLIK bacak (anket). Yazım ortak/bicim sözleşmesi: `AA.YYYY`.
        # "2026-08" biçimi sözleşmede YOK (ISO yalnız tam gün için tanımlı) ve
        # çözülemeyen bir saat, denetlenmeyen bir saattir — bu alanın bayatlık
        # denetimi 07.09.2026'ya kadar sessizce kapalıydı.
        O["_tarih2"] = f"{s_ay.month:02d}.{s_ay.year}"
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
        # ayın anketini "henüz gelmemiş" gösterip eksi gün üretiyordu. Gün TEK
        # tanımdan (metrik.yayim_gunu — günlüğe yayma ve Şekil 05'in dikey
        # çizgileri de oradan): hafta sonuna denk gelirse ilk iş günü; burada
        # ayrı hesaplanınca 20 Eylül 2026 Pazar'ı yayım günü sayıp seriden bir
        # gün önce "gelmiş" gösterirdi.
        yayim = metrik.yayim_gunu(s_ay, m["esik"]["pka_yayim_gun"])
        koy("anket_gecikme_gun", max(0, (bugun - yayim).days), 0)
        O["anket_varsayilan_yayim"] = tr_tarih(yayim)
        O["anket_yayim_cumlesi"] = anket_yayim_cumlesi(s_ay, m["esik"]["pka_yayim_gun"])

    # --- eğri düğümleri ----------------------------------------------------
    # Her anahtar KENDİ son dolu gününden okunur; çıpadan uzaksa atlanır.
    def anlik(kaynak_ad: str, hedef_ad: str, ondalik: int = 2,
              tolerans: int = ANLIK_TOLERANS_GUN) -> bool:
        """Anlık anahtar: kendi son dolu gününden, kendi tarihiyle.

        SAYFANIN ADIYLA ÇAĞIRDIĞI ANAHTAR HER KOŞUDA YAZILIR (08.09.2026 kuralı,
        kıyas bloğunda kondu, 09.09'da buraya genellendi): ölçülemiyorsa boş
        (OLCULEMEDI), ATLANMAZ. Atlanan anahtar sayfada yedekteki donmuş sayıyı
        bırakır ve yayın kapısı eksik anahtarı ENGEL sayıp yayını durdurur —
        08.09'da dokuz yıl düğümü kurulamayınca tam bu oldu. Bayat olan
        sayı basılmaz; ölçülemediği okura "—" ile görünür, son dolu gün
        varsa `_tarih`i onu taşır."""
        v = a.get(kaynak_ad)
        t = a.get(kaynak_ad + "_tarih")
        if v is None or t is None:
            uyar(f"'{hedef_ad}' ({kaynak_ad}) metrik özetinde yok — boş yazıldı.")
            O[hedef_ad] = OLCULEMEDI
            return False
        yas = (s_gun - pd.Timestamp(t)).days
        if yas > tolerans:
            uyar(f"'{hedef_ad}' ({kaynak_ad}) son dolu günü {t}, çıpadan {yas} "
                 "gün geride — boş yazıldı (bayat sayı basılmasın).")
            O[hedef_ad] = OLCULEMEDI
            O[hedef_ad + "_tarih"] = tr_tarih(t)
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
            ("carry_3a_tlref", "carry_3a_tlref")):
        anlik(kaynak, hedef)
    # AOFM taşıması: geçersiz rejimde son GEÇERLİ güne ait olur, atlanmaz.
    anlik("carry_2y_aofm", "carry_2y_aofm", tolerans=400)

    # --- referans faizler --------------------------------------------------
    for kaynak, hedef in (("tlref", "tlref"), ("politika", "politika"),
                          ("koridor_alt", "koridor_alt"),
                          ("koridor_ust", "koridor_ust")):
        anlik(kaynak, hedef)
    # Bileşiğe çevrilmiş karşılıklar: sayfada HAM (basit) ve BİLEŞİK yan yana
    # gösterilir; taşıma yalnız bileşikten hesaplanır.
    for kaynak, hedef in (("tlref_bilesik", "tlref_bilesik"),
                          ("politika_bilesik_gercek", "politika_bilesik"),
                          ("konvansiyon_farki_tlref", "konvansiyon_farki"),
                          ("carry_2y_tlref_basit", "carry_2y_tlref_basit")):
        anlik(kaynak, hedef)

    # --- AOFM: GEÇERLİLİK KAPISI ------------------------------------------
    # AOFM geçersizken seri DONAR; tolerans dar tutulursa anahtar tamamen
    # atlanır ve sayfa statik yedeğe düşer (okur eski sayıyı canlı sanır).
    # Bunun yerine SON GEÇERLİ gün basılır ve yanına geçersizlik notu konur.
    ad = m.get("aofm_durum") or {}
    O["aofm_gecerli"] = bool(ad.get("gecerli"))
    koy("aofm_taban_esik_mlr", (ad.get("esik_mn_tl") or 0) / 1000.0, 0)
    if ad.get("taban_mn_tl") is not None:
        koy("aofm_taban_mlr", ad["taban_mn_tl"] / 1000.0, 1)
    anlik("aofm", "aofm", tolerans=400)
    anlik("aofm_bilesik", "aofm_bilesik", tolerans=400)
    if ad.get("son_gecerli_gun"):
        O["aofm_son_gecerli"] = tr_tarih(ad["son_gecerli_gun"])
        koy("aofm_yas_gun", (s_gun - pd.Timestamp(ad["son_gecerli_gun"])).days, 0)
    O["aofm_cumlesi"] = (
        "AOFM geçerli: çıpa gününde APİ fonlaması "
        f"{tr_sayi(O.get('aofm_taban_mlr'), 1)} milyar TL ile "
        f"{tr_sayi(O.get('aofm_taban_esik_mlr'), 0)} milyar TL eşiğinin üstünde."
        if O["aofm_gecerli"] else
        "AOFM bu koşuda GEÇERSİZ: çıpa gününde APİ fonlaması "
        f"{tr_sayi(O.get('aofm_taban_mlr'), 1)} milyar TL ile "
        f"{tr_sayi(O.get('aofm_taban_esik_mlr'), 0)} milyar TL eşiğinin altında. "
        "AOFM bir ağırlıklı ortalamadır; ağırlık kalmayınca yayımlanan sayı "
        "son değerinde donar. Tablodaki AOFM son GEÇERLİ güne aittir "
        f"({O.get('aofm_son_gecerli', '—')}, "
        f"{tr_sayi(O.get('aofm_yas_gun'), 0)} gün önce) ve manşet taşıma "
        "ölçüsü değildir; yerine TLREF okunur.")

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
    # Tarih alanları kaynak aya çevrilir — ortalamaya çevrilmiş anket
    # serileriyle birlikte, aşağıda `aylik_saatleri` ile tek yerden (onların
    # anlık değeri daha sonra yazılıyor; saat bu yüzden orada güncellenir).
    A = pd.read_csv(VERI / "aylik.csv", index_col=0, parse_dates=True)
    # Yıllık TÜFE'nin son ayı ölçüm katmanından (Şekil 05'in aylık bacağı da
    # oradan okur); eski bir ölçüm dosyasında alan yoksa aylık tablodan.
    tufe_son_ay = m.get("son_tufe_ay")
    if not tufe_son_ay and "tufe_2025" in A.columns and A["tufe_2025"].notna().any():
        tufe_son_ay = A["tufe_2025"].dropna().index[-1]
    if tufe_son_ay:
        O["tufe_ay"] = ay_ad(tufe_son_ay)

    # --- REEL FAİZ (Fisher) ------------------------------------------------
    anlik("reel_ileri", "reel_ileri")
    anlik("reel_geriye", "reel_geriye")
    anlik("reel_ileri_2y", "reel_ileri_2y")
    # DERS ÖLÇÜSÜ: paydaya ORTALAMA yerine PKA'nın ham 24 ay NOKTA beklentisi
    # konsaydı reel faiz ne kadar şişerdi? Sözel "yaklaşık üç puan" yazmak
    # yasak — fark koşuda hesaplanır.
    if olculdu("spot_2y", "pka_24a", "reel_ileri_2y"):
        nokta = ((1 + O["spot_2y"] / 100) / (1 + O["pka_24a"] / 100) - 1) * 100
        koy("reel_ileri_2y_nokta", nokta, 2)
        koy("reel_ileri_2y_sisme", nokta - O["reel_ileri_2y"], 2)
    else:
        O["reel_ileri_2y_nokta"] = OLCULEMEDI
        O["reel_ileri_2y_sisme"] = OLCULEMEDI
    anlik("reel_ileri_basit", "reel_ileri_basit")
    anlik("fisher_basit_fark", "fisher_basit_fark")
    anlik("reel_makas", "reel_makas")
    # Fisher dersinin cümlesi de sayıdan TÜRETİLİR: yöntem farkının işareti
    # enflasyon seviyesiyle döner, elle yazılmış bir cümle yanlışa düşer.
    if olculdu("fisher_basit_fark", "reel_ileri"):
        f = O["fisher_basit_fark"]
        O["fisher_cumlesi"] = (
            f"Basit çıkarma reel faizi {tr_sayi(abs(f), 2)} puan "
            + ("YÜKSEK" if f > 0 else "DÜŞÜK") + " gösteriyor: "
            f"%{tr_sayi(O.get('reel_ileri_basit'), 2)} yerine Fisher "
            f"%{tr_sayi(O['reel_ileri'], 2)} veriyor.")
    else:
        O["fisher_cumlesi"] = (
            "İki yöntem arasındaki fark bu koşuda ölçülemedi: reel faiz "
            "ölçülerinden en az biri tolerans içinde dolu bir gün bulamadı.")

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
                          ("prim_3y", "risk_primi_3y"),
                          ("prim_5y", "risk_primi_5y"),
                          ("prim_7y", "risk_primi_7y")):
        anlik(kaynak, hedef)
    # Anket beklentisinin VADEYE KADARKİ ORTALAMAYA çevrilmiş hâli: risk
    # primi bunun üzerinden hesaplanır, sayfada ham nokta beklentiyle yan
    # yana gösterilir.
    for kaynak, hedef in (("pka_ort_1y", "pka_ort_1y"),
                          ("pka_ort_2y", "pka_ort_2y"),
                          ("pka_ort_5y", "pka_ort_5y"),
                          ("pka_ort_7y", "pka_ort_7y")):
        anlik(kaynak, hedef, tolerans=45)
    # Aylık kökenli on bir anahtarın SAATİ (`AA.YYYY`) ve okur ETİKETİ
    # (`_ay_ad`, "Ağustos 2026") — tek eşlemeden, bütün anlık değerler
    # yazıldıktan sonra (anlik() saati günlük çıpayla yazıyor, burada ay
    # etiketiyle üzerine yazılır). Tarih alanı günlük çıpayı gösterirse okur
    # "bu sayı 21 Ağustos'ta ölçüldü" sanır.
    O.update(aylik_saatleri(A))
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

    # --- AYRIŞTIRMA TANISI (koşuda ölçülür, elle yazılmaz) ----------------
    at = vd.get("ayristirma_test") or {}
    if at:
        koy("ayristirma_seri", at.get("toplam"), 0)
        koy("ayristirma_saf_dusen", at.get("saf_dusen"), 0)
        koy("ayristirma_saf_yanlis", at.get("saf_yanlis"), 0)
        koy("ayristirma_hosgoru_dusen", at.get("hosgoru_dusen"), 0)
        bozuk = (at.get("saf_dusen") or 0) + (at.get("saf_yanlis") or 0)
        koy("ayristirma_saf_bozuk", bozuk, 0)
        if at.get("toplam"):
            koy("ayristirma_saf_pay", bozuk / at["toplam"] * 100, 1)
        O["ayristirma_cumlesi"] = (
            f"Bu koşuda taranan {tr_sayi(at.get('toplam'), 0)} seri adının "
            f"{tr_sayi(at.get('saf_dusen'), 0)}'ini tek biçim varsayan bir "
            f"ayrıştırıcı hiç çözemez, {tr_sayi(at.get('saf_yanlis'), 0)}'ini "
            "de etiketi '(Arşiv)' sanarak yanlış sınıflandırırdı — toplam "
            f"%{tr_sayi(O.get('ayristirma_saf_pay'), 1)}. Hoşgörülü "
            f"ayrıştırıcının çözemediği ad sayısı: "
            f"{tr_sayi(at.get('hosgoru_dusen'), 0)}.")

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
        # 1 puan = 100 baz puan. Sayfada "baz puanın binde biri" gibi SÖZEL
        # mertebe iddiası yazmak yasak — ölçünün kendisi basılır.
        if ytm.get("medyan_fark_puan") is not None:
            koy("ytm_medyan_fark_bp", ytm["medyan_fark_puan"] * 100, 2)
        if ytm.get("maks_fark_puan") is not None:
            koy("ytm_maks_fark_bp", ytm["maks_fark_puan"] * 100, 2)
        koy("ytm_maks_fark", ytm.get("maks_fark_puan"), 3)
        koy("ytm_medyan_fiyat_fark", ytm.get("medyan_fiyat_fark"), 3)
        # DÜRÜST ETİKET: bu bir özdeşliktir, bağımsız doğrulama değil.
        O["ytm_ozdeslik"] = bool(ytm.get("ozdeslik"))
        koy("ytm_ozdeslik_n", ytm.get("ozdeslik_n"), 0)
        koy("ytm_ozdeslik_maks_tl", ytm.get("ozdeslik_maks_tl"), 6)
        koy("ytm_ozdeslik_esik_tl", ytm.get("ozdeslik_esik_tl"), 4)
        O["ytm_ozdeslik_gecti"] = bool(ytm.get("ozdeslik_gecti"))
        O["ytm_ozdeslik_cumlesi"] = (
            f"Özdeşlik birim sınaması: {O.get('ytm_ozdeslik_n', 0)} tahvilin "
            "hepsinde |Σ strip fiyatı − tahvil fiyatı| en çok "
            f"{tr_sayi(O.get('ytm_ozdeslik_maks_tl'), 6)} TL "
            f"(eşik {tr_sayi(O.get('ytm_ozdeslik_esik_tl'), 4)} TL) — GEÇTİ."
            if O["ytm_ozdeslik_gecti"] else
            "Özdeşlik birim sınaması BU KOŞUDA YAPILAMADI.")
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
    # Yayım günü okura CÜMLE içinde geçer ("ayın 20'sinden") ve ek SAYIYA
    # bağlıdır (3'ünden · 5'inden · 20'sinden). Sayfada sayının ardına sabit
    # bir ek yapıştırılıyordu; TÜFE sabiti 5'ten 3'e çekildiğinde "3'inden"
    # basardı. Metin burada, tek ek tablosundan kurulur.
    O["pka_yayim_metni"] = metrik.gun_eki(e["pka_yayim_gun"])
    O["tufe_yayim_metni"] = metrik.gun_eki(e["tufe_yayim_gecikme"])

    # --- kıyas günleri -----------------------------------------------------
    kiyas = m.get("kiyas_gunleri") or {}
    for ad, etiket in KIYAS_DONEM:
        if ad in kiyas:
            O[etiket] = tr_tarih(kiyas[ad])
            g = pd.Timestamp(kiyas[ad])
            for kol, sonek in KIYAS_VADE:
                # Bu anahtarlar SAYFADA ADIYLA çağrılıyor; ölçülemeyen değer
                # atlanmaz, boş yazılır (bkz. OLCULEMEDI). Değişimin bitişi
                # çıpa günü değilse kendi tarihiyle damgalanır.
                seviye = M.loc[g, kol] if (g in M.index and kol in M.columns) else np.nan
                if np.isfinite(seviye):
                    koy(f"{etiket}_{sonek}", float(seviye), 2)
                else:
                    O[f"{etiket}_{sonek}"] = OLCULEMEDI
                    uyar(f"{VADE_AD[sonek]} düğümü kıyas gününde ({tr_tarih(g)}) "
                         "kurulamamış; seviye boş bırakıldı.")
                r = kiyas_degisim(M, s_gun, g, kol)
                if r is None:
                    O[f"{etiket}_{sonek}_degisim_bp"] = OLCULEMEDI
                    uyar(f"{VADE_AD[sonek]} düğümü için {tr_tarih(g)} kıyası kurulamadı "
                         f"(kıyas günü ya da son {ANLIK_TOLERANS_GUN} gün boş); "
                         "değişim boş bırakıldı.")
                else:
                    bp, t1 = r
                    koy(f"{etiket}_{sonek}_degisim_bp", bp, 0)
                    O[f"{etiket}_{sonek}_degisim_bp_tarih"] = tr_tarih(t1)

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
    # MANŞET TAŞIMA ÖLÇÜSÜ: AOFM geçerliyse AOFM, değilse TLREF. Sayfanın
    # kendi gerekçesi de bunu söylüyor (TLREF fiilen ödenen maliyete en yakın
    # ölçüdür); geçersiz AOFM'yi manşete koymak okuru yanıltır.
    manset_kol = "carry_2y_aofm" if O.get("aofm_gecerli") else "carry_2y_tlref"
    O["carry_olcusu"] = "AOFM" if O.get("aofm_gecerli") else "TLREF"
    # DOLAYLI OKUMA: anahtar adı değişkenden geliyor, yani kapı `olculdu`ya
    # o değişkenle sorulur. Kapı olmasaydı boş bir manşet bacağı ya koy()'u
    # düşürürdü ya da cümleye `O.get(..., 0)` üzerinden SAHTE BİR SIFIR
    # yazardı ("fonlama maliyetinin 0,00 puan üstünde") — ölçülemeyen bir
    # şeyi ölçülmüş göstermenin en sessiz biçimi.
    manset_var = olculdu(manset_kol)
    koy("carry_manset", O.get(manset_kol) if manset_var else OLCULEMEDI, 2)
    car = M[manset_kol].dropna()
    if len(car):
        koy("carry_negatif_gun", int((car < 0).sum()), 0)
        koy("carry_negatif_pay", float((car < 0).mean() * 100), 1)
        # PENCEREYİ DE BAS: TLREF 28.12.2018'de başlıyor, AOFM 2013'te. "Şu
        # kadar günde negatifti" cümlesi hangi pencerede ölçüldüğünü
        # söylemezse iki ölçü arasında sessizce kayar.
        koy("carry_tarihce_gun", int(len(car)), 0)
        O["carry_tarihce_bas"] = tr_tarih(car.index[0])
        O["carry_pozitif_mi"] = bool(car.iloc[-1] > 0)
    O["carry_cumlesi"] = (
        f"2 yıllık spot getiri fonlama maliyetinin ({O['carry_olcusu']}, "
        "bileşiğe çevrilmiş) "
        f"{tr_sayi(abs(O['carry_manset']), 2)} "
        + ("PUAN ÜSTÜNDE — taşıma pozitif" if O.get("carry_pozitif_mi")
           else "PUAN ALTINDA — taşıma negatif, pozisyon ancak faiz inişi "
                "beklentisiyle tutulur") + "."
        if manset_var else
        f"Manşet taşıma ({O['carry_olcusu']}) bu koşuda ölçülemedi: fonlama "
        "bacağı tolerans içinde dolu bir gün bulamadı.")
    # Politika faizi ile fiilî maliyet arasındaki sistematik fark: iki canlı
    # sayının arasına SABİT üçüncü bir sayı yazmak yasak (sayfa kuralı).
    # AYNI GÜN ŞARTI: AOFM geçersiz rejimde son geçerli güne ait olduğu için
    # iki taşıma farklı günlerden gelebilir; farkı almak o zaman "faiz
    # makası" değil "gün farkı + faiz makası" olur.
    if (O.get("carry_2y_politika_tarih") == O.get("carry_2y_aofm_tarih")
            and olculdu("carry_2y_politika", "carry_2y_aofm")):
        koy("spread_politika_aofm",
            O["carry_2y_politika"] - O["carry_2y_aofm"], 2)
    # AYNI GÜN ŞARTI SAYFAYI DA BAĞLAR. Şart düştüğünde anahtar yazılmıyordu ama
    # sayfa onu KOŞULSUZ çağırıyordu; sonuç, sayfa sınavının "ozet.json'da
    # olmayan anahtar" bulgusu ve okurun gördüğü donmuş statik yedek. TLREF iş
    # günü bir seri, politika faizi ise her gün taşınıyor: pazartesi koşusunda
    # tarihler ayrışıyor ve şart MEŞRU biçimde düşüyor. Yani kusur kapıda değil,
    # kapının ardında hiçbir şey yazmamasında. Sayı yoksa SEBEBİ yazılıyor;
    # sayfa her koşuda dolan tek bir metin anahtarı çağırıyor.
    if not olculdu("carry_2y_politika", "carry_2y_tlref"):
        # SEBEP AYRI YAZILIR: burada tarihler tutuyor olabilir, ölçünün
        # kendisi yok. "aynı güne ait değil" demek okura yanlış sebep verir.
        koy("spread_politika_tlref_metin",
            "iki taşımadan en az biri bu koşuda ölçülemedi; makas hesaplanmadı",
            None)
    elif O.get("carry_2y_politika_tarih") == O.get("carry_2y_tlref_tarih"):
        d = O["carry_2y_politika"] - O["carry_2y_tlref"]
        koy("spread_politika_tlref", d, 2)
        koy("spread_politika_tlref_metin",
            f"{abs(round(d, 2)):.2f}".replace(".", ",") + " puan", None)
    else:
        koy("spread_politika_tlref_metin",
            "aynı güne ait iki taşıma bu koşuda yok (politika "
            f"{O.get('carry_2y_politika_tarih', '?')}, TLREF "
            f"{O.get('carry_2y_tlref_tarih', '?')}); makas hesaplanmadı — "
            "farklı günlerin farkı faiz makası değil, gün farkı + faiz makasıdır",
            None)
    # Prose içinde İŞARETSİZ okunan ("… ondan X puan aşağıda") cümleler için
    # MUTLAK değerli anahtar: negatif sayı işaretiyle basılınca cümle çift
    # olumsuzlamaya düşüyordu ("ondan −10,2 puan aşağıda").
    for kaynak_ad, hedef_ad in (("egim_2y9y", "egim_2y9y_mutlak"),
                                ("egim_2y5y", "egim_2y5y_mutlak")):
        if olculdu(kaynak_ad):
            koy(hedef_ad, abs(O[kaynak_ad]), 2)
        else:
            O[hedef_ad] = OLCULEMEDI
    if not olculdu("egim_2y9y"):
        # Sayı yoksa CÜMLE de kurulmaz: "9 yıllıktan — puan yüksek" bir ölçüm
        # değil, ölçüm kılığında bir boşluktur. Sebep okura yazılır.
        O["egim_cumlesi"] = (
            "2 yıl – 9 yıl eğimi bu koşuda ölçülemedi: dokuz yıl düğümünün son "
            f"dolu günü {O.get('egim_2y9y_tarih', OLCULEMEDI)}, tolerans dışında "
            "kaldı — bayat bir sayıyla cümle kurulmuyor.")
    else:
        O["egim_cumlesi"] = (
            "Eğri TERS: 2 yıllık getiri 9 yıllıktan "
            f"{tr_sayi(abs(O['egim_2y9y']), 2)} puan yüksek."
            if O.get("egri_ters_mi") else
            "Eğri NORMAL (yukarı eğimli): 9 yıllık getiri 2 yıllıktan "
            f"{tr_sayi(abs(O['egim_2y9y']), 2)} puan yüksek.")
    if olculdu("reel_ileri", "reel_geriye", "reel_makas"):
        O["reel_faiz_cumlesi"] = (
            f"Fisher ileri reel faiz %{tr_sayi(O['reel_ileri'], 2)}, geriye "
            f"dönük %{tr_sayi(O['reel_geriye'], 2)}; makas "
            f"{tr_sayi(O['reel_makas'], 2)} puan.")
    else:
        # "%—, geriye dönük %—; makas — puan" ölçüm KILIĞINDA bir boşluktur:
        # cümlenin biçimi sayı vaat ediyor, içinde sayı yok. Üç bacaktan biri
        # bile ölçülemediyse cümle kurulmaz, sebebi yazılır.
        O["reel_faiz_cumlesi"] = (
            "Fisher reel faiz bu koşuda ölçülemedi: ileri, geriye dönük ve "
            "makas ölçülerinden en az biri tolerans içinde dolu bir gün "
            "bulamadı.")
    if olculdu("risk_primi_5y", "basabas_5y", "pka_ort_5y"):
        # DİKKAT: kıyas ORTALAMAYA çevrilmiş anket beklentisiyledir. PKA'nın
        # ham 5 yıl serisi "5 YIL SONRASININ yıllık" oranıdır, beş yıllık
        # ortalama değildir; onunla kıyaslamak primi şişirirdi.
        O["basabas_cumlesi"] = (
            f"5 yıllık başabaş enflasyon %{tr_sayi(O['basabas_5y'], 1)}; "
            "anketin aynı ufka çevrilmiş karşılığı (12 ay, 24 ay ve 5 yıl "
            "çıpalarından kurulan patikanın beş yıllık geometrik ortalaması) "
            f"%{tr_sayi(O['pka_ort_5y'], 1)} — ham 5 yıl serisi "
            f"(%{tr_sayi(O.get('pka_5y'), 1)}) BEŞİNCİ YILIN tek yıllık "
            f"oranıdır, ortalama değildir. {tr_sayi(O['risk_primi_5y'], 1)} "
            "puanlık fark risk primi, likidite primi ve TÜFE ölçümüne "
            "güvensizliğin karışımıdır — 'piyasanın enflasyon beklentisi' "
            "DEĞİLDİR.")

    # --- başabaşın VADE YAPISININ ŞEKLİ (elle 'yukarı eğimli' yazmak yasak)
    bs = m.get("basabas_sekil") or {}
    if bs:
        O["basabas_sekil"] = bs["sekil"]
        if bs.get("tepe_vade"):
            koy("basabas_tepe_vade", bs["tepe_vade"], 0)
        koy("basabas_ilk_son_fark", bs.get("ilk_son_fark"), 2)
        uc = f"{int(bs['vadeler'][-1])} yıl"
        ilk = f"{int(bs['vadeler'][0])} yıl"
        if bs["sekil"] == "kambur":
            O["basabas_vade_cumlesi"] = (
                f"Başabaş eğrisi KAMBUR: {int(bs['tepe_vade'])} yılda tepe "
                f"yapıp geriliyor — {uc} vadeli başabaş "
                f"({tr_sayi(bs['degerler'][-1], 2)}%) {ilk} vadeliden "
                f"({tr_sayi(bs['degerler'][0], 2)}%) "
                f"{tr_sayi(abs(bs['ilk_son_fark']), 2)} puan "
                + ("DÜŞÜK" if bs["ilk_son_fark"] < 0 else "YÜKSEK") + ". "
                "Enflasyon riskinin fiyatlanması orta vadede yoğunlaşıyor, "
                "uzun uçta değil.")
        elif bs["sekil"] == "yukarı eğimli":
            O["basabas_vade_cumlesi"] = (
                f"Başabaş eğrisi YUKARI EĞİMLİ: {uc} vadeli başabaş {ilk} "
                f"vadeliden {tr_sayi(abs(bs['ilk_son_fark']), 2)} puan yüksek. "
                "Nominal eğri aşağı eğimliyken bu, uzun vadede reel getirinin "
                "nominal getiriden daha hızlı düştüğünü söyler.")
        elif bs["sekil"] == "çukur":
            O["basabas_vade_cumlesi"] = (
                f"Başabaş eğrisi ÇUKUR: {int(bs['tepe_vade'])} yılda dip yapıp "
                f"toparlıyor; {uc} ile {ilk} arasındaki fark "
                f"{tr_sayi(bs['ilk_son_fark'], 2)} puan.")
        else:
            O["basabas_vade_cumlesi"] = (
                f"Başabaş eğrisi AŞAĞI EĞİMLİ: {uc} vadeli başabaş {ilk} "
                f"vadeliden {tr_sayi(abs(bs['ilk_son_fark']), 2)} puan düşük.")

    # --- kurulamayan reel düğümler (elle 'bu koşuda 3 yıl yok' yazmak yasak)
    bos = m.get("reel_bos_dugumler") or []
    O["reel_bos_dugumler"] = ", ".join(bos) if bos else "yok"
    O["reel_bos_cumlesi"] = (
        "Bu koşuda kurulamayan reel düğüm kalmadı; bütün vadelerde başabaş "
        "hesaplanabiliyor."
        if not bos else
        f"Bu koşuda {', '.join(bos)} reel düğümü — ve dolayısıyla o "
        "vade(ler)de başabaş — kurulamadı: o vade aralığında iki komşu kıymet "
        "arasındaki boşluk sınırı aşıyor.")

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
    # ÖNEK LİSTESİ TAM OLMALI: 'SERİ ALINAMADI', 'ÇEKİM DÜŞTÜ', 'BOŞ ÖNBELLEK'
    # ve 'demet düştü' bu listede yokken ağ düşse bile bayrak kalkmıyordu.
    izler = [u for u in uyarilar
             if u.startswith(("TAZELİK", "ESKİ ÖNBELLEK", "BAYAT", "SERİ YOK",
                              "SERİ ALINAMADI", "SERİ BOŞ", "ÇEKİM DÜŞTÜ",
                              "BOŞ ÖNBELLEK", "demet düştü"))]
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

    # --- şekil saat defteri ve damga ---------------------------------------
    # İKİ TÜKETİCİ, TEK DEFTER: aynı fonksiyonu grafik.py figürün KENDİ alt
    # başlığı için okuyor (metrik.sekil_saatleri). Sekiz figürün hepsi hattın
    # tek ana saatiyle (08.09) damgalanıyordu; taşıma figürü 07.09'da bitiyor,
    # üç figür aylık bacak taşıyor (09.09.2026'da ölçüldü). Birleşik damga
    # defterde duramaz (sayfa sınavı 18 tek bir tarih ister); ayrım MEKANİK.
    defter, birlesik = metrik.defter_ayir(metrik.sekil_saatleri(m))
    O["_sekil_tarih"] = defter
    O.update(birlesik)

    yol = PROJE / "ozet.json"
    yol.write_text(json.dumps(O, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ozet.json yazıldı: {len(O)} anahtar · eğri {O['gun']} "
          f"({O['yayim_gecikme_gun']} gün önce)"
          + (f" · anket {O.get('anket_ay')}" if O.get("anket_ay") else "")
          + ("  ! BAYAT" if O.get("bayat") else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
