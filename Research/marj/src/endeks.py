# -*- coding: utf-8 -*-
"""
TCMB EN 24/17 replikasyonu — endeks kurgusu.

Kurgu (notun 4 aşaması):
  1. Maliyet ağırlıkları: işgücü %21, hammadde (gıda) %49, enerji %5, kira %10, diğer %15.
  2. Tarif bazlı gıda maliyet endeksleri (13 yemek, notun ekindeki paylar birebir).
  3. Gıda dışı kalemler: brüt asgari ücret; TÜFE-elektrik,gaz (045); TÜFE-kira (04110);
     diğer = ort(TÜFE genel, Yİ-ÜFE).
  4. Konsept maliyet = ağırlıklı ortalama (2013 Ocak = 100);
     fiyat/maliyet oranı = konsept fiyat / konsept maliyet (2013 Ocak = 1).

Veri notları (proxy etiketleri):
  * Madde düzeyi seriler TÜİK ortalama madde fiyatlarından (MEDAS) türetilen fiyat
    endeksleridir (2013 Ocak=100). TÜİK madde ENDEKSİ kamuya açık değildir; ortalama
    fiyat rölatifi PROXY olarak kullanılmıştır.
  * TÜİK, madde ortalama fiyatlarının yayımını Nisan 2022'de durdurmuştur. 2022/05
    sonrası her madde, eşlendiği COICOP-2018 5'li grup endeksinin aylık değişimleriyle
    UZATILMIŞTIR (splice). Bu dönemde dana/tavuk gibi tür ayrımları grup ortalamasına
    yakınsar; duyarlılık analizinde ayrıca ele alınır.
  * Fiyat tarafında yemek maddeleri de aynı yöntemle 11111 (tam sunum) / 11112
    (sınırlı sunum) endeksleriyle uzatılmıştır.
"""
import pathlib
import numpy as np
import pandas as pd

import veri

ROOT = pathlib.Path(__file__).resolve().parent.parent
CIKTI = ROOT / "output"
CIKTI.mkdir(exist_ok=True)

BAZ = "2013-01-01"          # 2013 Ocak = 100 / 1
UZUN_DONEM = ("2013-01-01", "2022-12-01")   # notun uzun dönem ortalama penceresi

# ---------------------------------------------------------------- ağırlık setleri
AGIRLIKLAR = {
    "nihai":   {"iscilik": 0.21, "gida": 0.49, "enerji": 0.05, "kira": 0.10, "diger": 0.15},
    "bist":    {"iscilik": 0.23, "gida": 0.49, "enerji": 0.05, "kira": 0.08, "diger": 0.16},
    "resim":   {"iscilik": 0.20, "gida": 0.49, "enerji": 0.05, "kira": 0.13, "diger": 0.14},
}

# ---------------------------------------------------------------- madde → 5'li grup eşlemesi (2022/05+ uzatma)
SPLICE_GRUBU = {
    "0111101": "g_tahillar_01111", "0111209": "g_tahillar_01111",
    "0111201": "g_unlar_01112", "0111301": "g_ekmek_01113",
    "0112201": "g_et_01122", "0112501": "g_et_01122",
    "0112701": "g_etkuru_01123", "0112703": "g_etkuru_01123",
    "0114101": "g_sut_01141", "0114301": "g_yogurt_01146",
    "0114401": "g_peynir_01145", "0114402": "g_peynir_01145", "0114501": "g_yumurta_01148",
    "0115101": "g_tereyagi_01152", "0115302": "g_bitkiselyag_01151", "0115301": "g_bitkiselyag_01151",
    "0117122": "g_meyvesebze_01172", "0117117": "g_meyvesebze_01172",
    "0117146": "g_digersebze_01174", "0117130": "g_digersebze_01174",
    "0117152": "g_yaprakli_01171", "0117153": "g_yaprakli_01171",
    "0117201": "g_yumrulu_01175", "0116130": "g_meyve_01162",
    "0117401": "g_baklagil_01176", "0117403": "g_baklagil_01176",
    "0117505": "g_salca_01179", "0117504": "g_salca_01179",
    "0119001": "g_baharat_01194", "0119002": "g_tuzsos_01193",
    "0119008": "g_tuzsos_01193", "0119009": "g_tuzsos_01193",
    # yemek maddeleri
    "1110101": "tam_sunum_11111", "1110102": "tam_sunum_11111",
    "1110103": "tam_sunum_11111", "1110104": "tam_sunum_11111",
    "1110105": "sinirli_11112", "1110106": "sinirli_11112",
    "1110108": "sinirli_11112", "1110110": "sinirli_11112",
}

# ---------------------------------------------------------------- tarifler (notun eki, birebir)
# pay -> bileşen madde listesi (eşit bölüşülür)
TARIFLER = {
    "mercimek_corbasi": {
        "0117403": 40, "0115101": 30,
        ("0117146", "0117130", "0117201"): 20,
        ("0119001", "0119002"): 10,
    },
    "pirinc_pilavi": {
        "0111101": 58, ("0115101", "0115302"): 39, "0119002": 3,
    },
    "etsiz_kuru_fasulye": {
        "0117401": 40, ("0117146", "0117117", "0117122"): 30,
        "0119001": 15, ("0115101", "0115302"): 14, "0117505": 1,
    },
    "hamburger": {
        "0112201": 65, "0111301": 20, ("0117152", "0117122", "0117146"): 10,
        ("0119008", "0119009", "0117504"): 5,
    },
    "pizza": {
        "0114402": 50, ("0112701", "0112703"): 20, "0111201": 10,
        ("0117122", "0117117"): 10, "0115302": 5, "0119001": 3, "0117505": 2,
    },
    "cig_kofte": {
        "0119001": 60, "0111209": 15, ("0117146", "0117122", "0117152"): 18,
        "0117505": 4, "0115302": 3,
    },
    "kiymali_pide": {
        "0112201": 65, ("0117146", "0117122", "0117117"): 15, "0119001": 10,
        "0111201": 5, "0115101": 3, "0114501": 2,
    },
    "lahmacun": {
        "0112201": 80, ("0117146", "0117122", "0117153"): 11, "0111201": 4,
        "0119001": 4, "0115302": 1,
    },
    "iskender": {
        "0112201": 85, "0114301": 4, "0115101": 4, "0119001": 4, "0111201": 3,
    },
    "adana_kebap": {
        "0112201": 85, "0119001": 5, ("0115101", "0115302"): 5, "0111201": 3,
        ("0117146", "0117122"): 2,
    },
    "et_doner": {
        "0112201": 92, "0111301": 2, ("0115101", "0115302"): 2, "0119001": 2,
        ("0117146", "0117122"): 1, "0114301": 1,
    },
    "tavuk_sis": {
        "0112501": 77, "0119001": 12, ("0117146", "0117122"): 4,
        ("0115101", "0115302"): 4, "0114301": 3,
    },
    "tavuk_doner": {
        "0112501": 92, "0111301": 2, ("0115101", "0115302"): 2, "0119001": 2,
        ("0117146", "0117122"): 1,
    },
}

# konsept -> (yemekler, fiyat tarafı yemek maddeleri)
KONSEPTLER = {
    "kirmizi_et": {
        "yemekler": ["adana_kebap", "iskender", "kiymali_pide", "lahmacun", "et_doner"],
        "fiyat_maddeleri": ["1110103", "1110104", "1110106"],
    },
    "tavuk": {
        "yemekler": ["tavuk_sis", "tavuk_doner"],
        "fiyat_maddeleri": ["1110103", "1110106"],
    },
    "ev_yemekleri": {
        "yemekler": ["mercimek_corbasi", "pirinc_pilavi", "etsiz_kuru_fasulye"],
        "fiyat_maddeleri": ["1110101", "1110102"],
    },
    "fast_food": {
        "yemekler": ["hamburger", "pizza", "cig_kofte"],
        "fiyat_maddeleri": ["1110105", "1110108", "1110110"],
    },
}

KONSEPT_ETIKET = {
    "kirmizi_et": "Kırmızı et ağırlıklı", "tavuk": "Tavuk eti ağırlıklı",
    "ev_yemekleri": "Ev yemekleri", "fast_food": "Fast-food",
}


def yeniden_bazla(s, baz=BAZ, deger=100.0):
    """2013 Ocak=deger. Seri 2013 Ocak'ta yoksa (sepete sonradan giren maddeler:
    ör. pizza 1110110, turşu 0117504) İLK GEÇERLİ gözlemi baz alır — aksi hâlde
    NaN'a bölme tüm seriyi NaN yapar ve konsept ortalamalarından sessizce düşer."""
    b = s.loc[baz] if (baz in s.index and pd.notna(s.loc[baz])) else s.loc[s.first_valid_index()]
    return s / b * deger


def _tur_kamasi(idx):
    """Dana/tavuk için 2022/05+ tür-kaması: Tarım-ÜFE tür endekslerinin karma sepete
    göre GÖRECE aylık değişimleri. Dönen: {'dana': Series, 'tavuk': Series} (aylık çarpan).

    karma = 0.65*sığır(01.42) + 0.30*kümes(01.47) + 0.05*koyun(01.45) — TÜFE et grubu
    içindeki yaklaşık tür bileşimi (dokümante edilmiş varsayım).
    Tarım-ÜFE'nin bittiği aydan sonra çarpan 1 (grup dinamiğine döner).
    """
    t = veri.medas_tarim_ufe().reindex(idx)
    sigir, kumes, koyun = t.get("01.42"), t.get("01.47"), t.get("01.45")
    baz = "2022-04-01"
    parcalar = {}
    for ad, s in [("sigir", sigir), ("kumes", kumes), ("koyun", koyun)]:
        parcalar[ad] = s / s.loc[baz]
    karma = 0.65 * parcalar["sigir"] + 0.30 * parcalar["kumes"] + 0.05 * parcalar["koyun"]
    out = {}
    for ad, hedef in [("dana", parcalar["sigir"]), ("tavuk", parcalar["kumes"])]:
        gorece = hedef / karma
        carpan = (gorece / gorece.shift(1))
        out[ad] = carpan.fillna(1.0)
    return out


def madde_endeksleri(bitis=None, tur_duzeltme=True):
    """MEDAS ortalama fiyatlarından madde fiyat endeksleri (2013-01=100); 2022/05+
    5'li grup endeksleriyle uzatılır. tur_duzeltme=True ise dana/tavuk uzatmasına
    Tarım-ÜFE tür-kaması uygulanır. Dönen: (df, kaynak_etiketi_df)."""
    fiyatlar = veri.medas_madde_fiyatlari()
    evds = veri.tum_evds()
    bitis = bitis or veri.son_ay(evds)
    idx = pd.date_range("2013-01-01", bitis, freq="MS")
    kama = _tur_kamasi(idx) if tur_duzeltme else None
    endeksler, etiketler = {}, {}
    for kod in veri.MADDE_ADLARI:
        if kod not in fiyatlar.columns:
            continue
        s = fiyatlar[kod].reindex(idx)
        grup = SPLICE_GRUBU[kod]
        g = evds[grup].reindex(idx)
        son = s.last_valid_index()
        birlesik = s.copy()
        ek_kaynak = ""
        if son is not None and son < idx[-1]:
            oran = g / g.shift(1)
            if tur_duzeltme and kod == "0112201":      # Dana Eti
                oran = oran * kama["dana"]; ek_kaynak = " + Tarım-ÜFE sığır kaması"
            elif tur_duzeltme and kod == "0112501":    # Tavuk Eti
                oran = oran * kama["tavuk"]; ek_kaynak = " + Tarım-ÜFE kümes kaması"
            for t in idx[idx > son]:
                onceki = birlesik.loc[t - pd.offsets.MonthBegin(1)]
                birlesik.loc[t] = onceki * oran.loc[t]
        endeksler[kod] = yeniden_bazla(birlesik.astype(float))
        etiketler[kod] = {
            "ad": veri.MADDE_ADLARI[kod],
            "gercek_veri_sonu": None if son is None else son.strftime("%Y-%m"),
            "uzatma_kaynagi": veri.EVDS_SERILER[grup] + ek_kaynak,
        }
    df = pd.DataFrame(endeksler)
    meta = pd.DataFrame(etiketler).T
    return df, meta


def _pay_cozumle(tarif):
    """Tarif sözlüğünü {kod: pay} düz haline getirir (tuple anahtarlar eşit bölünür)."""
    duz = {}
    for k, pay in tarif.items():
        if isinstance(k, tuple):
            for kk in k:
                duz[kk] = duz.get(kk, 0) + pay / len(k)
        else:
            duz[k] = duz.get(k, 0) + pay
    toplam = sum(duz.values())
    return {k: v / toplam for k, v in duz.items()}


def yemek_gida_endeksleri(madde_df):
    """Her yemek için tarif paylı gıda maliyet endeksi (2013-01=100).
    Bir bileşen o ay için eksikse (sepete geç giren maddeler, ör. turşu 2021+)
    kalan bileşenlerin payları yeniden normalize edilir."""
    out = {}
    for yemek, tarif in TARIFLER.items():
        paylar = _pay_cozumle(tarif)
        alt = madde_df[list(paylar)]
        w = pd.Series(paylar)
        pay_toplam = alt.notna().mul(w, axis=1).sum(axis=1)
        seri = alt.mul(w, axis=1).sum(axis=1, skipna=True) / pay_toplam
        out[yemek] = yeniden_bazla(seri)
    return pd.DataFrame(out)


def zincirli_ortalama(df):
    """Kolonların aylık değişim ORTALAMASIYLA zincirlenmiş endeks (ilk ay=100).
    Sepete sonradan giren seri, girdiği ayı izleyen aydan itibaren bileşime
    süreksizlik yaratmadan katılır (farklı bazlı endekslerin aritmetik
    ortalamasındaki seviye çarpıklığını önler)."""
    buyume = df.pct_change(fill_method=None).mean(axis=1)
    endeks = (1 + buyume.fillna(0)).cumprod()
    return endeks / endeks.iloc[0] * 100


def konsept_gida(yemek_df):
    out = {}
    for konsept, tanim in KONSEPTLER.items():
        out[konsept] = yeniden_bazla(yemek_df[tanim["yemekler"]].mean(axis=1))
    return pd.DataFrame(out)


def maliyet_bilesenleri(bitis=None, kira_senaryo="tufe"):
    """İşgücü, enerji, kira, diğer bileşen endeksleri (2013-01=100).

    kira_senaryo:
      'tufe'      — TÜFE 04110 kiracı tarafından ödenen gerçek kira (baz).
      'tavan25'   — Haz2022–Haz2024 arasında konut kirasındaki %25 tavanın etkisini,
                    bu dönemde kira artışını TÜFE 12 aylık ortalamasına (işyeri
                    kirası yasal endeksleme kuralı) bağlayarak düzeltir.
      'ykke'      — 2018+ TCMB Yeni Kiracı Kira Endeksi (yeni sözleşme kiraları) ile
                    2018 öncesi TÜFE kira; piyasa kirası duyarlılığı.
    """
    evds = veri.tum_evds()
    bitis = bitis or veri.son_ay(evds)
    idx = pd.date_range("2013-01-01", bitis, freq="MS")
    ucret = veri.asgari_ucret_serisi(bitis[:7]).reindex(idx)
    enerji = evds["enerji_045"].reindex(idx)
    tufe = evds["tufe_genel"].reindex(idx)
    yiufe = evds["yi_ufe"].reindex(idx)
    kira_tufe = evds["kira_0411"].reindex(idx)

    if kira_senaryo == "tufe":
        kira = kira_tufe.copy()
    elif kira_senaryo == "tavan25":
        kira = kira_tufe.copy()
        pencere = (idx > "2022-06-01") & (idx <= "2024-06-01")
        # işyeri kira artışı: TBK md.344 — TÜFE 12 aylık ortalama değişimi (aylıklandırılmış)
        oniki_ort = tufe.rolling(12).mean()
        yillik = oniki_ort / oniki_ort.shift(12) - 1
        aylik_esdeger = (1 + yillik) ** (1 / 12)
        for t in idx[pencere]:
            kira.loc[t] = kira.loc[t - pd.offsets.MonthBegin(1)] * aylik_esdeger.loc[t]
        # pencere sonrası: TÜFE kira aylık değişimleriyle devam
        sonra = idx[idx > "2024-06-01"]
        oran = kira_tufe / kira_tufe.shift(1)
        for t in sonra:
            kira.loc[t] = kira.loc[t - pd.offsets.MonthBegin(1)] * oran.loc[t]
    elif kira_senaryo == "ykke":
        ykke = evds["ykke"].reindex(idx)
        kira = kira_tufe.copy()
        gecis = pd.Timestamp("2018-01-01")
        oran = ykke / ykke.shift(1)
        for t in idx[idx > gecis]:
            if pd.notna(oran.loc[t]):
                kira.loc[t] = kira.loc[t - pd.offsets.MonthBegin(1)] * oran.loc[t]
            else:  # YKKE'nin son ayı sonrası TÜFE kira ile devam
                kira.loc[t] = kira.loc[t - pd.offsets.MonthBegin(1)] * (kira_tufe.loc[t] / kira_tufe.shift(1).loc[t])
    else:
        raise ValueError(kira_senaryo)

    diger = (yeniden_bazla(tufe) + yeniden_bazla(yiufe)) / 2
    return pd.DataFrame({
        "iscilik": yeniden_bazla(ucret),
        "enerji": yeniden_bazla(enerji),
        "kira": yeniden_bazla(kira),
        "diger": yeniden_bazla(diger),
    })


def konsept_maliyet(gida_df, bilesen_df, agirlik="nihai"):
    w = AGIRLIKLAR[agirlik]
    out = {}
    for konsept in KONSEPTLER:
        out[konsept] = (w["gida"] * gida_df[konsept] + w["iscilik"] * bilesen_df["iscilik"]
                        + w["enerji"] * bilesen_df["enerji"] + w["kira"] * bilesen_df["kira"]
                        + w["diger"] * bilesen_df["diger"])
    return pd.DataFrame(out)


def konsept_fiyat(madde_df):
    """Konsept fiyat endeksi: madde endekslerinin ZİNCİRLİ ortalaması.
    (Pizza 1110110 sepete 2016'da girer; zincirleme, farklı bazlı serilerin
    aritmetik ortalamasındaki süreksizliği önler.)"""
    out = {}
    for konsept, tanim in KONSEPTLER.items():
        out[konsept] = zincirli_ortalama(madde_df[tanim["fiyat_maddeleri"]])
    return pd.DataFrame(out)


def oranlar(fiyat_df, maliyet_df):
    r = fiyat_df / maliyet_df
    return r.div(r.loc[BAZ])


def uzun_donem_ort(oran_df):
    pencere = oran_df.loc[UZUN_DONEM[0]:UZUN_DONEM[1]]
    return pencere.mean()


def ima_edilen_marj(oran_df, cipalar=(0.15, 0.225, 0.30)):
    """İma edilen kâr marjı DÜZEYİ (deneysel, senaryolu türetim).

    Fiyat/maliyet oranı tek başına marj seviyesi vermez; bir ÇIPA varsayımı gerekir.
    Çıpa: sektör derneği (TURYİD, notun 7 no'lu dipnotu) işletmelerin tipik olarak
    %70-85 maliyet / %15-30 kârlılıkla çalıştığını bildirir. Bu bandın 2013-2022
    "normal" dönem ortalamasında geçerli olduğu varsayılırsa:

        marj(t) = 1 - (1 - m0) / r(t),   r(t) = Oran(t) / Oran_2013-2022_ort
        (marj = (satış - maliyet) / satış; m0 = çıpa marjı)

    Mekanik türetimdir: kalite, kompozisyon ve verimlilik değişimlerini de "marj"
    sayar; sonuçlar bant olarak ve uyarı notuyla raporlanmalıdır.
    Dönen: {m0: DataFrame} (marj, satışın oranı olarak).
    """
    uzun = uzun_donem_ort(oran_df)
    r = oran_df.div(uzun, axis=1)
    return {m0: 1 - (1 - m0) / r for m0 in cipalar}


def hepsi(bitis=None, agirlik="nihai", kira_senaryo="tufe", tur_duzeltme=True):
    """Uçtan uca: tüm ara ve nihai tabloları döndürür. bitis verilmezse
    veri.son_ay() (TÜFE'nin bulunduğu son ay)."""
    bitis = bitis or veri.son_ay()
    madde_df, meta = madde_endeksleri(bitis, tur_duzeltme)
    yemek_df = yemek_gida_endeksleri(madde_df)
    gida_df = konsept_gida(yemek_df)
    bilesen_df = maliyet_bilesenleri(bitis, kira_senaryo)
    maliyet_df = konsept_maliyet(gida_df, bilesen_df, agirlik)
    fiyat_df = konsept_fiyat(madde_df)
    oran_df = oranlar(fiyat_df, maliyet_df)
    return dict(madde=madde_df, madde_meta=meta, yemek=yemek_df, gida=gida_df,
                bilesen=bilesen_df, maliyet=maliyet_df, fiyat=fiyat_df, oran=oran_df)


if __name__ == "__main__":
    r = hepsi()
    m, o = r["maliyet"], r["oran"]
    pd.set_option("display.width", 160)
    print("=== MALİYET ENDEKSLERİ (2013 Ocak=100) ===")
    SON, ONCE = veri.son_ay(), veri.once_ay()
    for t in ["2019-12-01", "2024-07-01", SON]:
        print(t[:7], m.loc[t].round(0).to_dict())
    print("\nAralık 2019 → Temmuz 2024 kat:", (m.loc["2024-07-01"] / m.loc["2019-12-01"]).round(2).to_dict())
    print("\n=== FİYAT/MALİYET ORANLARI (2013 Ocak=1) ===")
    for t in [ONCE, veri.once_ay(ay=12), SON]:
        print(t[:7], r["oran"].loc[t].round(2).to_dict())
    print("\nUzun dönem ort. (2013-2022):", uzun_donem_ort(o).round(2).to_dict())
    print("\nEv yemekleri 2022 dip:", round(float(o.loc["2022-01-01":"2022-12-01", "ev_yemekleri"].min()), 2))
