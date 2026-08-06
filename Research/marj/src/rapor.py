# -*- coding: utf-8 -*-
"""
TCMB EN 24/17 replikasyonu — Excel çıktısı (tüm seriler, ham + endeksli, ayrı sekmeler).
"""
import datetime, pathlib
import pandas as pd

import veri, endeks, analiz

ROOT = pathlib.Path(__file__).resolve().parent.parent
CIKTI = ROOT / "output"


def excel_yaz(dosya=None):
    dosya = dosya or (CIKTI / "seriler.xlsx")
    sonuc = endeks.hepsi()
    evds = veri.tum_evds()
    medas = veri.medas_madde_fiyatlari()
    tarim = veri.medas_tarim_ufe()
    au = veri.asgari_ucret_serisi()
    kars = analiz.karsilastirma_tablosu(sonuc)
    katki = analiz.katki_ayristirma()
    try:
        duy = pd.read_csv(CIKTI / "duyarlilik.csv")
    except FileNotFoundError:
        duy = analiz.duyarlilik()

    meta = pd.DataFrame([
        ["Üretim tarihi", datetime.datetime.now().isoformat(timespec="seconds")],
        ["Kaynak 1", "TCMB EVDS3 API — TÜFE (2025=100, COICOP-2018, 2005'e geri taşınmış), TÜFE (2003=100 arşiv), Yİ-ÜFE (TP.TUFE1YI.T1), Yeni Kiracı Kira Endeksi (TP.YKKE.TR)"],
        ["Kaynak 2", "TÜİK MEDAS — Tüketici Madde Fiyatları (2003=100), 2005/01–2022/04 (yayın Nisan 2022'de durdu)"],
        ["Kaynak 3", "TÜİK MEDAS — Tarım Ürünleri ÜFE (2020=100) tür detayı (01.42 sığır-besi, 01.47 kümes, 01.45 koyun-keçi)"],
        ["Kaynak 4", "TÜİK Veri Portalı — Hizmet Ciro Endeksi (2015=100, arşiv), TÜFE ağırlık tabloları"],
        ["Kaynak 5", "Asgari Ücret Tespit Komisyonu kararları (Resmî Gazete) — brüt asgari ücret; 2024'te ara zam yok"],
        ["PROXY notu 1", "Madde 'endeksleri' TÜİK ortalama madde fiyatı rölatifleridir (madde endeksi kamuya açık değil)"],
        ["PROXY notu 2", "2022/05 sonrası maddeler COICOP-2018 5'li grup endeksleriyle uzatıldı (splice); dana/tavuk için ilaveten Tarım-ÜFE tür kaması"],
        ["PROXY notu 3", "Fiyat tarafında kırmızı et/tavuk ayrımı TÜİK madde yapısında yoktur (kebap/döner ortak); fark yalnızca maliyet tarafından gelir"],
        ["Ağırlıklar (nihai)", "işgücü %21, gıda %49, enerji %5, kira %10, diğer %15 (EN 24/17, Tablo 4)"],
        ["Uzun dönem penceresi", "2013-01 – 2022-12 (notla aynı)"],
    ], columns=["alan", "değer"])

    with pd.ExcelWriter(dosya, engine="openpyxl") as w:
        meta.to_excel(w, "META", index=False)
        evds.to_excel(w, "EVDS_ham")
        medas.to_excel(w, "MEDAS_madde_fiyat_TL")
        tarim.to_excel(w, "TarimUFE_2020")
        au.to_frame().to_excel(w, "AsgariUcret_brut")
        sonuc["madde"].to_excel(w, "Madde_endeks_2013=100")
        sonuc["madde_meta"].to_excel(w, "Madde_meta")
        sonuc["yemek"].to_excel(w, "Yemek_gida_endeksleri")
        sonuc["gida"].to_excel(w, "Konsept_gida")
        sonuc["bilesen"].to_excel(w, "Maliyet_bilesenleri")
        sonuc["maliyet"].to_excel(w, "Konsept_maliyet")
        sonuc["fiyat"].to_excel(w, "Konsept_fiyat")
        sonuc["oran"].to_excel(w, "Fiyat_maliyet_orani")
        kars.to_excel(w, "Karsilastirma", index=False)
        duy.to_excel(w, "Duyarlilik", index=False)
        katki.to_excel(w, "Katki_Tem24_Tem26")
    print(f"Excel yazıldı: {dosya}")
    return dosya


if __name__ == "__main__":
    excel_yaz()
