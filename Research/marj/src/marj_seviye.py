# -*- coding: utf-8 -*-
"""
Maliyetten (aşağıdan yukarı) türetilen SEVİYE metrikleri.

İki metrik:
  1. FOOD-COST ORANI = porsiyon gıda maliyeti (TL) / KDV'den arındırılmış satış
     fiyatı (TL). Tek varsayım porsiyon GRAMAJI'dır; çıpa marjı gerekmez.
     Restoran endüstrisinin standart "food cost %" göstergesidir.
  2. m49 = 1 − (gıda maliyeti / 0,49) / net fiyat: gıda %49 maliyet-payı
     varsayımıyla TAM marj. Bu pay MENÜ ORTALAMASI olduğundan yemek düzeyinde
     kırılır (çorbada aşırı yüksek, dönerde negatif çıkar) — kimlik/teşhis
     kısıtının kanıtı olarak raporlanır.

TL düzeyleri: MEDAS ortalama fiyatları (Nis 2022'ye kadar gerçek); sonrası her
serinin kendi (splice'lı) endeks büyümesiyle uzatılır. KDV: yiyecek-içecek
hizmetlerinde %8, Temmuz 2023'ten itibaren %10.
"""
import pathlib
import pandas as pd

import veri, endeks

ROOT = pathlib.Path(__file__).resolve().parent.parent
CIKTI = ROOT / "output"

# Porsiyon gramajları (gram; ml≈g) — standart lokanta porsiyonu varsayımı.
# Kaynak: notun kuru fasulye tarifi ölçüleri + yaygın standart porsiyonlar.
# Duyarlılık: ±%25 gramaj bandı raporlanır.
GRAMAJ = {
    "Mercimek çorbası": {"0117403": 60, "0115101": 10, "0117146": 20, "0117130": 15, "0111201": 5, "0119001": 4},
    "Kuru fasulye":     {"0117401": 70, "0117146": 30, "0117117": 25, "0117122": 70, "0115101": 5, "0115302": 5, "0117505": 8, "0119001": 4},
    "Pirinç pilavı":    {"0111101": 90, "0115101": 10, "0115302": 5, "0119002": 2},
    "Adana kebap":      {"0112201": 140, "0119001": 6, "0111201": 60, "0117122": 50, "0117146": 25, "0117117": 15},
    "Et döner (ekmekarası)": {"0112201": 55, "0111301": 70, "0117122": 15, "0117146": 10, "0119001": 2, "0115302": 3},
    # 1110108 "Burgerler" maddesi basit/sokak tipi burgeri temsil eder (2013 ort.
    # fiyatı 2,86 TL) — gramaj buna göre küçük porsiyondur.
    "Hamburger":        {"0112201": 50, "0111301": 60, "0117152": 10, "0117122": 15, "0117146": 8, "0119008": 8, "0119009": 8, "0117504": 5},
    "Pizza":            {"0111201": 130, "0114402": 90, "0112701": 20, "0112703": 15, "0117122": 30, "0117117": 15, "0117505": 15, "0115302": 8, "0119001": 2},
}
FIYAT_ESLEME = {
    "Mercimek çorbası": "1110101", "Kuru fasulye": "1110102", "Pirinç pilavı": "1110102",
    "Adana kebap": "1110103", "Et döner (ekmekarası)": "1110106", "Hamburger": "1110108", "Pizza": "1110110",
}


def hesapla(sonuc=None):
    """Dönen: dict(fc=DataFrame, m49=DataFrame, tl_gida=DataFrame, p_net=DataFrame)."""
    if sonuc is None:
        sonuc = endeks.hepsi()
    mad = sonuc["madde"]
    tl = veri.medas_madde_fiyatlari()

    def tl_seviye(kod):
        baz = tl[kod].reindex(mad.index)
        e = mad[kod]
        son = baz.last_valid_index()
        out = baz.copy()
        out.loc[out.index > son] = float(baz.loc[son]) * (e.loc[e.index > son] / float(e.loc[son]))
        return out

    kdv = pd.Series(1.08, index=mad.index)
    kdv.loc["2023-07-01":] = 1.10   # yiyecek-içecek hizmeti KDV artışı

    fc, m49, cgida, pnet = {}, {}, {}, {}
    for yemek, gramlar in GRAMAJ.items():
        # eksik bileşen aylarında (sepete geç girenler) mevcut gramajla hesapla
        parcalar = pd.DataFrame({k: tl_seviye(k) * g / 1000 for k, g in gramlar.items()})
        cg = parcalar.sum(axis=1, skipna=True)
        p = tl_seviye(FIYAT_ESLEME[yemek]) / kdv
        fc[yemek] = cg / p
        m49[yemek] = 1 - (cg / 0.49) / p
        cgida[yemek], pnet[yemek] = cg, p
    out = dict(fc=pd.DataFrame(fc), m49=pd.DataFrame(m49),
               tl_gida=pd.DataFrame(cgida), p_net=pd.DataFrame(pnet))
    (out["fc"] * 100).round(1).to_csv(CIKTI / "food_cost_orani.csv")
    return out


def ozet_tablo(h):
    """Yemek bazında özet: FC uzun ort./Tem-24/Tem-26 + m49 Tem-26 (gramaj ±%25 bandı)."""
    fc, m49 = h["fc"], h["m49"]
    satirlar = []
    for yemek in fc.columns:
        f = fc[yemek]
        # gramaj ±%25 → gıda maliyeti ±%25 → m49 bandı
        cg_p = h["tl_gida"][yemek]; p = h["p_net"][yemek]
        m_dus = 1 - (cg_p * 0.75 / 0.49) / p
        m_yuk = 1 - (cg_p * 1.25 / 0.49) / p
        yz = lambda x: ("%" + f"{x*100:.0f}").replace(".", ",")
        satirlar.append({
            "Yemek": yemek,
            "FC 2013-2022 ort.": yz(float(f.loc["2013-01-01":"2022-12-01"].mean())),
            "FC Tem-2024": yz(float(f.loc["2024-07-01"])),
            "FC Tem-2026": yz(float(f.loc["2026-07-01"])),
            "m49 Tem-2026 (gramaj ±%25)": f"{yz(float(m_yuk.loc['2026-07-01']))} … {yz(float(m_dus.loc['2026-07-01']))}",
        })
    return pd.DataFrame(satirlar)


if __name__ == "__main__":
    h = hesapla()
    pd.set_option("display.width", 160)
    print(ozet_tablo(h).to_string(index=False))
