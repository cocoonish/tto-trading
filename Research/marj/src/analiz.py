# -*- coding: utf-8 -*-
"""
TCMB EN 24/17 replikasyonu — analiz katmanı.

1) kirilma_testi(): 2025=100 geri taşımanın eski 2003=100 seriyle tutarlılığı
   (aylık değişim farkları + Ocak 2026 zincirleme kontrolü).
2) karsilastirma_tablosu(): orijinal hedefler vs replikasyon vs güncel dönem.
3) duyarlilik(): ağırlık seti x kira senaryosu x tür-düzeltme ızgarası.
4) katki_ayristirma(): maliyet artışında kalem katkıları (Bölüm 5 soruları).
"""
import pathlib
import numpy as np
import pandas as pd

import veri, endeks

ROOT = pathlib.Path(__file__).resolve().parent.parent
CIKTI = ROOT / "output"
CIKTI.mkdir(exist_ok=True)


# ------------------------------------------------------------------ 1. Kırılma testi
def kirilma_testi():
    evds = veri.tum_evds()
    yeni = evds["tufe_genel"]              # 2025=100, 2005'e geri taşınmış
    eski = evds["eski_genel"]              # 2003=100, arşiv (son gözlem 2026-01)
    mm_y = yeni.pct_change() * 100
    mm_e = eski.pct_change() * 100
    ortak = pd.concat([mm_y, mm_e], axis=1, keys=["yeni", "eski"]).dropna()
    ortak = ortak.loc["2005-02-01":"2025-12-01"]
    fark = (ortak["yeni"] - ortak["eski"])
    rapor = {
        "donem": f"{ortak.index.min():%Y-%m} → {ortak.index.max():%Y-%m}",
        "aylik_fark_ort_puan": round(float(fark.mean()), 4),
        "aylik_fark_mutlak_ort": round(float(fark.abs().mean()), 4),
        "aylik_fark_maks": round(float(fark.abs().max()), 4),
        "maks_fark_ayi": fark.abs().idxmax().strftime("%Y-%m"),
        "korelasyon": round(float(ortak["yeni"].corr(ortak["eski"])), 6),
    }
    # Ocak 2026 zinciri: eski serinin 2026-01 m/m'i (arşivde tek uzatma gözlemi varsa)
    try:
        eski_ocak = float(eski.loc["2026-01-01"] / eski.loc["2025-12-01"] - 1) * 100
        yeni_ocak = float(yeni.loc["2026-01-01"] / yeni.loc["2025-12-01"] - 1) * 100
        rapor["ocak2026_mm_eski"] = round(eski_ocak, 3)
        rapor["ocak2026_mm_yeni"] = round(yeni_ocak, 3)
    except KeyError:
        rapor["ocak2026_mm_eski"] = None
    # Alt seriler: gıda, kira, enerji, yemek hizmetleri karşılaştırması (2005-2025)
    ciftler = [("gida_alkolsuz", "eski_gida"), ("kira_0411", "eski_kira41"),
               ("enerji_045", "eski_enerji45"), ("yemek_111", "eski_yemek111")]
    alt = {}
    for y, e in ciftler:
        a = evds[y].pct_change() * 100
        b = evds[e].pct_change() * 100
        f = (a - b).dropna().loc["2005-02-01":"2025-12-01"]
        alt[y] = {"mutlak_ort_fark": round(float(f.abs().mean()), 4),
                  "maks_fark": round(float(f.abs().max()), 3),
                  "maks_ay": f.abs().idxmax().strftime("%Y-%m")}
    df_alt = pd.DataFrame(alt).T
    return rapor, df_alt


# ------------------------------------------------------------------ 2. Karşılaştırma tablosu
HEDEFLER = {
    ("maliyet_kat_ara19_tem24", "kirmizi_et"): 8.1,
    ("maliyet_kat_ara19_tem24", "ev_yemekleri"): 6.6,
    ("oran_tem24", "ev_yemekleri"): 1.30,
    ("oran_tem24", "kirmizi_et"): 1.54,
    ("oran_tem24", "tavuk"): 1.79,
    ("oran_tem24", "fast_food"): 2.08,
    ("uzun_donem_ort", "ev_yemekleri"): 0.94,
    ("uzun_donem_ort", "kirmizi_et"): 1.05,
    ("uzun_donem_ort", "tavuk"): 1.09,
    ("uzun_donem_ort", "fast_food"): 1.17,
    ("ev_2022_dip", "ev_yemekleri"): 0.77,
}

GEREKCELER = {
    "oran_tem24|kirmizi_et": ("Fiyat tarafı: TÜİK'te kebap/pide/döner maddeleri kırmızı et–tavuk ayrımı "
                              "içermez (TCMB kendi mikro verisiyle ayrıştırmış); ayrıca Nis-2022 sonrası "
                              "madde fiyatı yayımı durduğu için fiyatlar 11111/11112 agregatlarıyla uzatıldı — "
                              "kebap özelindeki fiyat sıçraması agregata törpülenir."),
    "oran_tem24|tavuk": ("Aynı fiyat tarafı kısıtı; tavuk maliyeti Tarım-ÜFE kaması ile ayrıştırıldı fakat "
                         "fiyat tarafı kırmızı et ile ortak madde setinden gelir."),
    "oran_tem24|ev_yemekleri": "Uyum yüksek; kalan fark splice dönemindeki agregat fiyat uzatmasından.",
    "oran_tem24|fast_food": "Birebir uyum.",
    "uzun_donem_ort|fast_food": ("1110105 maddesi 2022 sepetinde 'Köfteler' (2024 sepetinde çiğ köfte); "
                                 "ortalama fiyat rölatifleri ile TCMB ürün endeksi arasındaki kompozisyon farkı."),
    "ev_2022_dip|ev_yemekleri": ("Dip, madde fiyatı yayınının durduğu Nis-2022 SONRASINDA gerçekleşti; "
                                 "uzatma agregat 11111 ile yapıldığından konsepte özgü fiyat frenlemesi "
                                 "kısmen gözlenemiyor."),
    "maliyet_kat_ara19_tem24|kirmizi_et": ("Dana eti Nis-2022'ye kadar gerçek; sonrası 01122+Tarım-ÜFE sığır kaması "
                                           "proxy'si. Ayrıca 'diğer' kalemi ve baharat sepeti bileşim farkları."),
    "maliyet_kat_ara19_tem24|ev_yemekleri": "Uyum yüksek.",
}


def karsilastirma_tablosu(sonuc=None):
    if sonuc is None:
        sonuc = endeks.hepsi()
    m, o = sonuc["maliyet"], sonuc["oran"]
    kat = m.loc["2024-07-01"] / m.loc["2019-12-01"]
    uzun = endeks.uzun_donem_ort(o)
    satirlar = []
    for (metrik, konsept), hedef in HEDEFLER.items():
        if metrik == "maliyet_kat_ara19_tem24":
            rep = float(kat[konsept]); guncel = float(m.loc["2026-07-01", konsept] / m.loc["2019-12-01", konsept])
        elif metrik == "oran_tem24":
            rep = float(o.loc["2024-07-01", konsept]); guncel = float(o.loc["2026-07-01", konsept])
        elif metrik == "uzun_donem_ort":
            rep = float(uzun[konsept]); guncel = rep
        elif metrik == "ev_2022_dip":
            rep = float(o.loc["2022-01-01":"2022-12-01", "ev_yemekleri"].min())
            guncel = float(o.loc["2026-07-01", "ev_yemekleri"])
        sapma = rep - hedef
        satirlar.append({
            "metrik": metrik, "konsept": konsept, "orijinal": hedef,
            "replikasyon": round(rep, 2), "sapma": round(sapma, 2),
            "guncel_2026_07": round(guncel, 2),
            "gerekce": GEREKCELER.get(f"{metrik}|{konsept}", "—"),
        })
    df = pd.DataFrame(satirlar)
    df.to_csv(CIKTI / "karsilastirma_tablosu.csv", index=False)
    return df


# ------------------------------------------------------------------ 3. Duyarlılık
def duyarlilik():
    """Ağırlık seti x kira senaryosu x tür-düzeltme ızgarası; kritik metrikler."""
    satirlar = []
    for agirlik in ["nihai", "bist", "resim"]:
        for kira in ["tufe", "tavan25", "ykke"]:
            for tur in [True, False]:
                r = endeks.hepsi(agirlik=agirlik, kira_senaryo=kira, tur_duzeltme=tur)
                o, m = r["oran"], r["maliyet"]
                uzun = endeks.uzun_donem_ort(o)
                satir = {"agirlik": agirlik, "kira": kira, "tur_kamasi": tur}
                for k in endeks.KONSEPTLER:
                    satir[f"oran24_{k}"] = round(float(o.loc["2024-07-01", k]), 2)
                    satir[f"oran26_{k}"] = round(float(o.loc["2026-07-01", k]), 2)
                    satir[f"uzun_{k}"] = round(float(uzun[k]), 2)
                satir["kat_kirmizi"] = round(float(m.loc["2024-07-01", "kirmizi_et"] / m.loc["2019-12-01", "kirmizi_et"]), 2)
                satirlar.append(satir)
    df = pd.DataFrame(satirlar)
    df.to_csv(CIKTI / "duyarlilik.csv", index=False)
    return df


# ------------------------------------------------------------------ 4. Katkı ayrıştırması
def katki_ayristirma(bas="2024-07-01", son="2026-07-01", agirlik="nihai"):
    """Kalem bazında maliyet artışı katkıları (aritmetik, yüzde puan)."""
    r = endeks.hepsi(agirlik=agirlik)
    w = endeks.AGIRLIKLAR[agirlik]
    b, g = r["bilesen"], r["gida"]
    satirlar = {}
    for konsept in endeks.KONSEPTLER:
        parcalar = {"gida": g[konsept]}
        for kalem in ["iscilik", "enerji", "kira", "diger"]:
            parcalar[kalem] = b[kalem]
        toplam_bas = sum(w[k] * parcalar[k].loc[bas] for k in w)
        katkilar = {}
        for k in w:
            katkilar[k] = w[k] * (parcalar[k].loc[son] - parcalar[k].loc[bas]) / toplam_bas * 100
        katkilar["TOPLAM"] = sum(katkilar.values())
        satirlar[konsept] = katkilar
    df = pd.DataFrame(satirlar).T.round(1)
    df.to_csv(CIKTI / "katki_ayristirma.csv")
    return df


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    rapor, alt = kirilma_testi()
    print("=== KIRILMA TESTİ (2025=100 geri taşıma vs 2003=100 arşiv) ===")
    for k, v in rapor.items(): print(f"  {k}: {v}")
    print(alt.to_string())
    print("\n=== KARŞILAŞTIRMA TABLOSU ===")
    print(karsilastirma_tablosu().drop(columns="gerekce").to_string(index=False))
    print("\n=== KATKI AYRIŞTIRMASI (Tem24→Tem26, % puan) ===")
    print(katki_ayristirma().to_string())
