#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TL taşıma (carry) defteri — hesap katmanı.

Bu hat kendi veri kaynağına GİTMEZ: kur, faiz ve DİBS serileri Fonlama ile
DIBS hatlarının depoya yazdığı CSV'lerden okunur. İki sonucu var. Birincisi,
hat çevrimdışı da koşar — EVDS anahtarı ve ağ gerekmez; CI'da Fonlama/DIBS
tazelendikten sonra koşturulması yeter. İkincisi, sayfadaki her sayı öbür
sayfalarla AYNI seriden gelir: taşıma sayfasının TLREF'i, fonlama sayfasının
TLREF'inden farklı olamaz.

Üç katman hesaplanır:

  makas      İLERİYE bakan taşıma: bugünkü faiz − bugünkü kur hızı. Trader'ın
             "bugün pozisyona girsem" sorusu. Kur hızı geçmiş pencereden
             ölçüldüğü için bu bir tahmindir ve öyle etiketlenir.
  endeks     GERİYE bakan gerçekleşme: 100'le başlayıp her gün TLREF'le
             büyüyen ve kur değişimiyle USD'ye çevrilen hedge'siz carry
             endeksi. "Taşımayı gerçekten taşısaydım ne olurdu" sorusu.
             Çöküş dönemleri buradan okunur.
  tahvil     DIBS hattının hazır taşıma kolonları (bileşik konvansiyonla).
             Nakit taşıma ile tahvil taşımasının çelişkisi bu iki katmanın
             yan yana konmasıdır.

Konvansiyon — bu sayfanın ana metodoloji dersi: TLREF, AOFM ve politika faizi
BASİT yıllık ilan edilir; DİBS getirileri BİLEŞİKTİR. Basit faizle hesaplanan
taşıma yanlış işaret verebilir (26.08.2026'da 2y taşıma bileşikle −8,47,
basitle +0,61 — işaret bile ters). Bütün kıyaslar bileşiğe çevrilerek yapılır:
r_bileşik = (1 + r_basit/365)^365 − 1.

Saat sözleşmesi — özetteki HER sayısal anahtar kendi gözlem gününü
`<anahtar>_tarih` ile taşır (tarihsel ölçüler hariç); hattın ana saati
(`_tarih`) kurun günüdür ve öbür anahtarların saati değildir. Tarihler okura
GG.AA.YYYY yazılır (ortak/bicim). Politika faizi iki anahtar: `politika`
EVDS satırının gözlemi, `politika_ilan` kur gününe taşınmış yürürlükteki
faiz. Sınama: duman.py (guncelle.py adımlardan önce koşturur).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent.parent
FONLAMA = KOK / "Aktarılacak Projeler" / "Fonlama" / "data"
DIBS = KOK / "Aktarılacak Projeler" / "DIBS" / "data"

# Tarih yazımı TEK kaynaktan (ortak/bicim.py = site/src/lib/bicim.ts): günlük
# saat GG.AA.YYYY. guncelle.py `ortak`ı PYTHONPATH'e koyar; elle koşuda yol
# buradan eklenir. 09.09.2026'da ölçüldü: çöküş ve en kötü ay tarihleri
# ISO yazımıyla (yıl-ay-gün) yazılıyordu — okura giden dosyada biçim sözleşmesi
# dışı (sayfa sınavı 17 "biçim" ailesi ISO tarihi sızıntı sayar).
try:
    from bicim import tarih_kisa, tarihe_cevir
except ImportError:                                   # elle koşu: PYTHONPATH yok
    sys.path.insert(0, str(KOK / "ortak"))
    from bicim import tarih_kisa, tarihe_cevir

# Ölçülemeyen değer: sayfanın adıyla çağırdığı anahtar ATLANMAZ, boş yazılır.
# JSON null Deger bileşeninde statik yedeği bırakır (donmuş sayı); "—" ise
# okura "ölçülemedi" der.
OLCULEMEDI = "—"

# Anahtar adından TARİHSEL olduğu anlaşılan ölçüler (Deger.astro ve
# bulten/ayar.TARIHSEL_ISARET ile aynı kalıp): "o zirve ne zaman yaşandı" gibi;
# tazelik saati taşımazlar. Kalan her sayısal anahtar KENDİ saatini taşır.
TARIHSEL = ("maks", "min", "zirve", "dip", "cipa", "bas", "baslangic", "en_derin",
            "enbuyuk", "encok", "cokus", "rekor", "referans")

# Deval hızı pencereleri (iş günü) — USDTRYDeval hattıyla aynı: 5/21/63.
PENCERE = {"d1h": 5, "d1a": 21, "d3a": 63}


def gun(t) -> str:
    """pd.Timestamp → "GG.AA.YYYY" — ortak/bicim sözleşmesi, tek tanım."""
    return tarih_kisa(t)


def tarihsel_mi(anahtar: str) -> bool:
    """Anahtar adı tarihsel bir ölçüyü mü adlandırıyor (saat taşımaz)?"""
    parcalar = anahtar.strip("_").split("_")
    return any(p in TARIHSEL for p in parcalar)


def son_gozlem(seri: pd.Series) -> tuple[float | None, pd.Timestamp | None]:
    """Serinin son DOLU gözlemi ve o gözlemin GÜNÜ; seri boşsa (None, None).

    ANAHTAR BAŞINA SAAT. Bu hattın çerçevesi kur gününe hizalıdır ve kur en
    taze seridir; TLREF bir gün, DİBS taşıma kolonları bir gün geriden gelir.
    Bir anahtarın değeri hangi satırdan okunuyorsa saati de o satırın günüdür —
    hattın ana saati (_tarih) değil. 09.09.2026'da ölçüldü: carry_2y_tlref,
    n2y, f_1y1y, tlref_b, getiri_1y ve zirveden 07.09 satırından okunuyor,
    kendi saatleri yazılmadığı için sayfa ipucu hattın saatini (08.09)
    gösteriyordu — bir gün bayat sayı taze görünüyordu.
    """
    s = seri.dropna()
    if s.empty:
        return None, None
    return float(s.iloc[-1]), s.index[-1]


ILAN_KOLONLARI = ("politika", "koridor_alt", "koridor_ust")


def ilan_tasi(d: pd.DataFrame) -> pd.DataFrame:
    """İlan edilmiş faizleri kur günlerine ileri taşır; GÖZLEMİ ayrı tutar.

    Politika faizi ve koridor ADIM fonksiyonudur: karar değişene kadar
    geçerlidir. Kur satırı olup faiz satırı olmayan günlerde ileri taşımak veri
    uydurmak değil, ilan edilmiş faizin tanımıdır. TLREF/AOFM taşınMAZ: onlar
    her gün yeniden gerçekleşen ölçümlerdir.

    İki kolon, iki saat: `politika` EVDS satırının kendisidir (gözlem, taşınmaz;
    saati o satırın günü), `politika_ilan` kur gününe taşınmış yürürlükteki
    faizdir (saati kur günü). 09.09.2026'da ölçüldü: taşınmış değer
    `politika_tarih` ile KUR gününe (08.09) etiketleniyordu, oysa EVDS satırı
    07.09'da bitiyor; Fonlama sayfası aynı seriyi 07.09 diye yazıyordu — aynı
    seri iki sayfada iki gün taşıyordu. PPK günü riski ayrıca duman.py'de.
    """
    d = d.copy()
    d["politika_ilan"] = d["politika"].ffill()
    for a in ILAN_KOLONLARI[1:]:
        d[a] = d[a].ffill()
    return d


def gecelik_bilesik(basit: pd.Series) -> pd.Series:
    """Basit yıllık gecelik faiz → bileşik yıllık. TLREF/AOFM/politika için."""
    return ((1 + basit / 100 / 365) ** 365 - 1) * 100


def yukle() -> pd.DataFrame:
    g = pd.read_csv(FONLAMA / "gunluk.csv", parse_dates=["tarih"])
    mf = pd.read_csv(FONLAMA / "metrik.csv", parse_dates=["tarih"])
    md = pd.read_csv(DIBS / "metrik.csv", parse_dates=["tarih"])

    d = g[["tarih", "usdtry", "tlref", "aofm", "politika",
           "koridor_alt", "koridor_ust"]].merge(
        mf[["tarih", "aofm_gecerli", "marjinal_faiz"]], on="tarih", how="left").merge(
        md[["tarih", "n3a", "n1y", "n2y", "tlref_bilesik", "aofm_bilesik",
            "politika_bilesik_gercek", "carry_2y_tlref", "carry_2y_politika",
            "carry_2y_aofm", "carry_3a_tlref", "carry_2y_tlref_basit",
            "f_1y1y"]], on="tarih", how="left")
    d = d.sort_values("tarih").set_index("tarih")
    return ilan_tasi(d)


def deval_hizi(kur: pd.Series, gun: int) -> pd.Series:
    """ACT/365 yıllıklandırılmış kur değişim hızı — USDTRYDeval ile aynı tanım."""
    onceki = kur.shift(gun)
    takvim = (kur.index.to_series() - kur.index.to_series().shift(gun)).dt.days
    return ((kur / onceki) ** (365.0 / takvim) - 1) * 100


def carry_endeksi(d: pd.DataFrame) -> pd.DataFrame:
    """Hedge'siz TL taşıma endeksi, USD bazında.

    Kurgu: 1 USD bozdurulur, TL'si her gün TLREF'te (basit yıllık, ACT/365
    takvim günü tahakkuku) değerlenir, her gün kura bölünüp USD'ye çevrilir.
    TLREF öncesi dönem yok sayılır — vekil faizle tarih uzatmak, endeksin
    "gerçekleşme" iddiasını bozar.
    """
    e = d[["usdtry", "tlref"]].dropna().copy()
    gun = e.index.to_series().diff().dt.days.fillna(0)
    e["tl_birikim"] = (1 + e["tlref"].shift() / 100 * gun / 365).fillna(1).cumprod()
    e["endeks"] = 100 * e["tl_birikim"] * e["usdtry"].iloc[0] / e["usdtry"]
    e["zirveden"] = 100 * (e["endeks"] / e["endeks"].cummax() - 1)
    return e


def yillik_getiri(endeks: pd.Series, gun: int) -> pd.Series:
    onceki = endeks.shift(gun)
    takvim = (endeks.index.to_series() - endeks.index.to_series().shift(gun)).dt.days
    return ((endeks / onceki) ** (365.0 / takvim) - 1) * 100


def hesapla(d: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Üç katmanı hesaplar ve özeti kurar. `d` verilmezse depodan yüklenir;
    duman sınaması sentetik çerçeveyi buradan geçirir (ağa çıkmaz)."""
    if d is None:
        d = yukle()
    for ad, gun_ in PENCERE.items():
        d[ad] = deval_hizi(d["usdtry"], gun_)

    # İleriye bakan makaslar — hepsi BİLEŞİK faizle. Politika bacağı kur
    # gününe taşınmış İLAN üzerinden: kur satırı olan her gün için yürürlükteki
    # faiz budur (gözlem satırı bir gün geride kalsa da).
    d["tlref_b"] = gecelik_bilesik(d["tlref"])
    d["politika_b"] = gecelik_bilesik(d["politika_ilan"])
    d["makas_politika_d1a"] = d["politika_ilan"] - d["d1a"]  # rejim panosuyla aynı tanım
    d["makas_tlref_b_d3a"] = d["tlref_b"] - d["d3a"]
    d["makas_tlref_b_d1a"] = d["tlref_b"] - d["d1a"]

    e = carry_endeksi(d)
    e["getiri_1y"] = yillik_getiri(e["endeks"], 252)
    d = d.join(e[["endeks", "zirveden", "getiri_1y"]])

    son = d.dropna(subset=["usdtry"]).iloc[-1]

    # ŞEKİL 03'ÜN KENDİ SAATİ. Hattın ana saati (_tarih) kurun günüdür, çünkü
    # kur en taze seridir: 03.09.2026'da kur o günü doldurmuşken TLREF henüz
    # yayımlanmamıştı ve TLREF'e bağlı HER seri 02.09'da bitiyordu. Şekil 03'ün
    # iki bacağı da o gruptan: nakit bacağı (TLREF bileşik − 1a deval) Fonlama
    # hattının TLREF'ine, tahvil bacağı (2y DİBS taşıması) DİBS hattının taşıma
    # kolonuna bağlı — ve ikisi AYRI hattın CSV'sinden geldiği için ayrı da
    # düşebilir. Damga bu yüzden bağlayıcı, yani EN ESKİ bacaktır: figürün sözü
    # iki serinin KIYASI ve kıyas ancak ikisinin birden olduğu güne kadar
    # kurulabilir. Ana saatle damgalanınca şekil 02.09 kesitini gösterirken
    # sayfada "veri 03.09.2026" yazıyordu — bir gün bayat figür taze görünüyor.
    sekil_nakit_tahvil = min(d["makas_tlref_b_d1a"].dropna().index[-1],
                             d["carry_2y_tlref"].dropna().index[-1])

    # ŞEKİL 01 DE İKİ SAATLİ. İki iz çiziliyor: politika − 1a deval (politika
    # faizi günlük, kur günlük → bugün) ve TLREF bileşik − 3a deval (TLREF bir
    # gün geriden gelir). Damga ana saatten okununca EN TAZE bacağı söylüyordu,
    # yani TLREF izinin bir gün bayat olduğu her gün figür taze görünüyordu.
    # Kural şekil 03'teki ile aynı: figürün sözü iki makasın KIYASI ve kıyas
    # ancak ikisinin de ölçüldüğü güne kadar kurulabilir — damga bağlayıcı,
    # yani EN ESKİ bacaktır. min() burada yapısaldır, bugünkü sıralamaya
    # bakmaz: TLREF beslemesi öne geçerse damga kendiliğinden öbür bacağa döner.
    sekil_makas = min(d["makas_politika_d1a"].dropna().index[-1],
                      d["makas_tlref_b_d3a"].dropna().index[-1])

    # ŞEKİL 04 aynı kuralla: bileşik ve basit konvansiyon izlerinin ESKİSİ.
    # İkisi aynı DİBS satırından türediği için bugün aynı günde biter; min()
    # yine yapısal — bir kolon tek başına düşerse damga onu izler.
    sekil_konvansiyon = min(d["carry_2y_tlref"].dropna().index[-1],
                            d["carry_2y_tlref_basit"].dropna().index[-1])

    # Çöküş dönemleri: endeksin zirveden %10'dan derin düştüğü aralıklar.
    # Tarihler okura GG.AA.YYYY (ortak/bicim); süren çöküşün bitişi boş.
    cokusler = []
    seri = e["zirveden"]
    icinde = False
    for t, v in seri.items():
        if not icinde and v <= -10:
            icinde, bas, dip, dip_t = True, t, v, t
        elif icinde:
            if v < dip:
                dip, dip_t = v, t
            if v >= -1:                    # zirveye dönüş sayılır
                cokusler.append({"bas": gun(bas), "dip_tarih": gun(dip_t),
                                 "dip": round(dip, 1), "bitis": gun(t)})
                icinde = False
    if icinde:
        cokusler.append({"bas": gun(bas), "dip_tarih": gun(dip_t),
                         "dip": round(dip, 1), "bitis": ""})

    # En kötü 1 aylık pencereler: "carry ne zaman ölür" sorusunun ölçülen
    # cevabı. Tek dev bir zirveden-düşüş aralığından daha okunur, çünkü çöküş
    # dönemleri gerçekte kısa ve şiddetlidir. Aynı krize ait pencereler
    # (±45 gün) tek kayda indirgenir. SIRALAMA ZAMAN DAMGASIYLA yapılır, metinle
    # değil: ISO yazımı sözlük sırasında tesadüfen kronolojikti, "GG.AA.YYYY"
    # metni güne göre dizilir ("07.04.2020" < "31.03.2021" doğru ama
    # "09.06.2022" < "21.12.2021" yanlış).
    a1 = e["endeks"].pct_change(21).dropna() * 100
    secilen: list[tuple[pd.Timestamp, float]] = []
    for t, v in a1.sort_values().items():
        if any(abs((t - s_).days) < 45 for s_, _ in secilen):
            continue
        secilen.append((t, float(v)))
        if len(secilen) == 5:
            break
    kotu = [{"tarih": gun(t), "getiri_1a": round(v, 1)} for t, v in sorted(secilen)]

    getiri = e["endeks"].pct_change().dropna()
    yil = 252
    sharpe3y = (getiri.tail(3 * yil).mean() / getiri.tail(3 * yil).std() * np.sqrt(yil)
                if len(getiri) > 3 * yil else np.nan)

    ozet: dict = {"_tarih": gun(son.name)}

    def koy(ad: str, seri: pd.Series, ondalik: int = 1) -> None:
        """Değer ve SAATİ birlikte yazılır: değer serinin son dolu gözlemi,
        saat o gözlemin günü (`<ad>_tarih`). Seri boşsa değer "—", saat yok —
        anahtar atlanmaz (sayfa onu adıyla çağırıyor)."""
        v, t = son_gozlem(seri)
        if v is None:
            ozet[ad] = OLCULEMEDI
            return
        ozet[ad] = round(v, ondalik)
        ozet[f"{ad}_tarih"] = gun(t)

    # Kur günündeki ölçüler — saatleri ana saatle aynı, yine de açık yazılır:
    # sözleşme "her sayısal anahtar kendi saatini taşır", istisnası tarihsel
    # ölçüler (bkz. tarihsel_mi).
    koy("kur", d["usdtry"], 4)
    koy("d1a", d["d1a"])
    koy("d3a", d["d3a"])
    # Politika faizi: GÖZLEM (EVDS satırı, kendi günü) ve İLAN (kur gününe
    # taşınmış yürürlükteki faiz). İki saat arasındaki fark taşımanın kendisidir;
    # okur ipucunda görür, denetim iki tarihi kıyaslayabilir.
    koy("politika", d["politika"], 2)
    koy("politika_ilan", d["politika_ilan"], 2)
    koy("tlref", d["tlref"], 2)
    koy("tlref_b", d["tlref_b"], 2)
    koy("makas_politika_d1a", d["makas_politika_d1a"])       # ilan bacağı: kur günü
    koy("makas_tlref_b_d3a", d["makas_tlref_b_d3a"])
    # DİBS satırından gelenler: her biri kendi son dolu gününden. Taşıma
    # kolonları TLREF'e kapılı (bir gün geride), n2y ve 1y1y forward kurun
    # gününe kadar gelebilir — 08.09.2026'da öyleydi (n2y 40,04 · f_1y1y 41,26
    # dolu, carry_2y_tlref boş).
    for ad in ("carry_2y_tlref", "carry_2y_tlref_basit", "carry_2y_politika",
               "carry_3a_tlref", "n2y", "f_1y1y"):
        koy(ad, d[ad], 2)
    # Şekil damgaları: bağlayıcı bacak (en eski). MDX `tarihAnahtari` ile okur.
    ozet["carry_tarih"] = gun(sekil_konvansiyon)
    ozet["nakit_tahvil_tarih"] = gun(sekil_nakit_tahvil)
    ozet["makas_tarih"] = gun(sekil_makas)
    koy("endeks", d["endeks"])
    ozet["endeks_bas"] = gun(e.index[0])
    koy("getiri_1y", d["getiri_1y"])
    koy("zirveden", d["zirveden"])
    if pd.isna(sharpe3y):
        ozet["sharpe_3y"] = OLCULEMEDI
    else:
        ozet["sharpe_3y"] = round(float(sharpe3y), 2)
        ozet["sharpe_3y_tarih"] = gun(getiri.index[-1])
    ozet["cokus_sayisi"] = len(cokusler)
    ozet["en_derin_cokus"] = min((c["dip"] for c in cokusler), default=None)
    ozet["en_derin_cokus_tarih"] = next((c["dip_tarih"] for c in cokusler
                                         if c["dip"] == min(x["dip"] for x in cokusler)), "")
    ozet["cokusler"] = cokusler
    ozet["kotu_aylar"] = kotu
    return d, e, ozet


if __name__ == "__main__":
    d, e, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"seri: {gun(d.index[0])} → {gun(d.index[-1])}")
    for k in ("kur", "d1a", "makas_politika_d1a", "makas_tlref_b_d3a", "carry_2y_tlref",
              "carry_2y_tlref_basit", "endeks", "getiri_1y", "zirveden", "sharpe_3y",
              "cokus_sayisi", "en_derin_cokus", "en_derin_cokus_tarih"):
        print(f"  {k:24s} {ozet[k]}")
    print("  en kötü 1 aylık pencereler:")
    for x in ozet["kotu_aylar"]:
        print(f"    {x['tarih']}  {x['getiri_1a']:+.1f}%")
    print("  çöküşler:")
    for c in ozet["cokusler"]:
        print(f"    {c['bas']} → dip {c['dip_tarih']} ({c['dip']}%) → {c['bitis'] or 'sürüyor'}")
