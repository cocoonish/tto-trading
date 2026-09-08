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
    # Duyarlılık ızgarası (18 koşu) pahalı; önbellekten okunur AMA yalnız güncel
    # aya aitse. Eskiden dosya varsa körlemesine okunuyordu → veri ilerlese de 18
    # senaryo eski ayda kalırdı (sessiz bayatlama). donem_son sütunu yoksa ya da
    # farklıysa yeniden hesaplanır.
    duy = None
    try:
        duy = pd.read_csv(CIKTI / "duyarlilik.csv")
        if "donem_son" not in duy.columns or str(duy["donem_son"].iloc[0]) != veri.son_ay()[:7]:
            print(f"duyarlilik.csv bayat/eski biçim → yeniden hesaplanıyor ({veri.son_ay()[:7]})")
            duy = None
    except FileNotFoundError:
        pass
    if duy is None:
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

    # ATOMİK YAZIM (08.09.2026). Bloğun içinde bir satır düşerse ExcelWriter
    # kapanışta yine de kaydeder ve geride SAYFASIZ bir xlsx kalır (ölçüldü:
    # 3 KB, "At least one sheet must be visible"); zincirin sonraki iki adımı
    # (web_cikti, ozet_uret) o dosyayı okuyup düşer ve dosya depoya girerse
    # sonraki her koşu da düşer. Geçici dosyaya yazılır, ancak tamamlanınca
    # hedefe taşınır — yarım kalan yazım eski sürümü hiç bozmaz.
    gecici = dosya.with_name(dosya.stem + ".tmp.xlsx")
    if gecici.exists():
        gecici.unlink()
    with pd.ExcelWriter(gecici, engine="openpyxl") as w:
        meta.to_excel(w, sheet_name="META", index=False)
        evds.to_excel(w, sheet_name="EVDS_ham")
        medas.to_excel(w, sheet_name="MEDAS_madde_fiyat_TL")
        tarim.to_excel(w, sheet_name="TarimUFE_2020")
        au.to_frame().to_excel(w, sheet_name="AsgariUcret_brut")
        sonuc["madde"].to_excel(w, sheet_name="Madde_endeks_2013=100")
        sonuc["madde_meta"].to_excel(w, sheet_name="Madde_meta")
        sonuc["yemek"].to_excel(w, sheet_name="Yemek_gida_endeksleri")
        sonuc["gida"].to_excel(w, sheet_name="Konsept_gida")
        sonuc["bilesen"].to_excel(w, sheet_name="Maliyet_bilesenleri")
        sonuc["maliyet"].to_excel(w, sheet_name="Konsept_maliyet")
        sonuc["fiyat"].to_excel(w, sheet_name="Konsept_fiyat")
        sonuc["oran"].to_excel(w, sheet_name="Fiyat_maliyet_orani")
        kars.to_excel(w, sheet_name="Karsilastirma", index=False)
        duy.to_excel(w, sheet_name="Duyarlilik", index=False)
        katki.to_excel(w, sheet_name="Katki_2y")  # iki yıl önce → güncel ay (veri.once_ay → son_ay)
        marj = endeks.ima_edilen_marj(sonuc["oran"])
        (marj[0.225] * 100).to_excel(w, sheet_name="Ima_marj_%22.5_merkez")
        bant = pd.concat({f"cipa_%{int(m0*1000)/10}": (df * 100).loc[[veri.once_ay(), veri.son_ay()]]
                          for m0, df in marj.items()}, axis=0)
        bant.round(1).to_excel(w, sheet_name="Ima_marj_bant")
        import marj_seviye
        ms = marj_seviye.hesapla(sonuc)
        (ms["fc"] * 100).round(1).to_excel(w, sheet_name="FoodCost_orani_%")
        ms["tl_gida"].round(2).to_excel(w, sheet_name="FoodCost_TL_gida")
        ms["p_net"].round(2).to_excel(w, sheet_name="FoodCost_TL_netfiyat")
    gecici.replace(dosya)
    print(f"Excel yazıldı: {dosya}")
    return dosya


if __name__ == "__main__":
    excel_yaz()
