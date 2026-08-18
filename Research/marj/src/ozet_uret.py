# -*- coding: utf-8 -*-
"""Canli ozet — output/ozet.json.

Sayfa metnindeki OYNAK sayilar buradan beslenir (CLAUDE.md kural 5):
MDX'te <Deger proje="yiyecek-hizmetleri-marj" anahtar="..."> ile okunur.
Tarihsel/metodolojik sabitler (agirliklar, 2013 capasi, replikasyon dogrulama
sayilari) sayfada STATIK kalir — onlar veri tazelendikce degismez.

Butun degerler output/ altindaki uretilmis dosyalardan OKUNUR; elle sayi yazilmaz.
Bir deger kaynakta bulunamazsa anahtar ATLANIR ve stderr'e uyari basilir.
"""
import json
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")
XLSX = os.path.join(OUT, "seriler.xlsx")

KONSEPTLER = ["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"]


def _uyar(m):
    print(f"UYARI: {m}", file=sys.stderr)


def main():
    ozet = {}

    # --- Fiyat/maliyet orani: guncel + uzun donem ortalama ---
    oran = pd.read_excel(XLSX, sheet_name="Fiyat_maliyet_orani", index_col=0)
    oran.index = pd.to_datetime(oran.index)
    son = oran.dropna(how="all").iloc[-1]
    ozet["_tarih"] = oran.dropna(how="all").index[-1].strftime("%m.%Y")
    ozet["donem"] = oran.dropna(how="all").index[-1].strftime("%B %Y")
    for ay_en, ay_tr in [("January", "Ocak"), ("February", "Şubat"), ("March", "Mart"),
                         ("April", "Nisan"), ("May", "Mayıs"), ("June", "Haziran"),
                         ("July", "Temmuz"), ("August", "Ağustos"), ("September", "Eylül"),
                         ("October", "Ekim"), ("November", "Kasım"), ("December", "Aralık")]:
        ozet["donem"] = ozet["donem"].replace(ay_en, ay_tr)

    # Donem etiketleri: guncel ay ve iki yil oncesi (sayfadaki "Temmuz 2026",
    # "Tem-2026", "Temmuz 2024" gibi her etiket buradan okunur; MDX'te sabit yazilmaz)
    AY_TR = {1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
             7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"}
    AY_KISA = {1: "Oca", 2: "Şub", 3: "Mar", 4: "Nis", 5: "May", 6: "Haz",
               7: "Tem", 8: "Ağu", 9: "Eyl", 10: "Eki", 11: "Kas", 12: "Ara"}
    t_son = oran.dropna(how="all").index[-1]
    t_once = t_son - pd.DateOffset(months=24)
    ozet["donem_kisa"] = f"{AY_KISA[t_son.month]}-{t_son.year}"
    ozet["donem_ay"] = AY_TR[t_son.month]
    ozet["donem_yil"] = int(t_son.year)
    ozet["once_donem"] = f"{AY_TR[t_once.month]} {t_once.year}"
    ozet["once_donem_kisa"] = f"{AY_KISA[t_once.month]}-{t_once.year}"
    ozet["once_yil"] = int(t_once.year)

    # Uzun donem ortalama: notun "normal" donemi 2013-2022
    uzun_pencere = oran.loc["2013-01-01":"2022-12-31"]
    once = oran.loc[t_once] if t_once in oran.index else None
    for k in KONSEPTLER:
        if k in oran.columns:
            ozet[f"oran_{k}"] = round(float(son[k]), 2)
            ozet[f"uzun_{k}"] = round(float(uzun_pencere[k].mean()), 2)
            if once is not None:
                ozet[f"oran2y_{k}"] = round(float(once[k]), 2)
        else:
            _uyar(f"Fiyat_maliyet_orani'nda '{k}' sutunu yok")
    # Oranlarin uzun donem ortalamasina kati (min-max): "1,2-1,4 kati" cumlesi
    katlar = [ozet[f"oran_{k}"] / ozet[f"uzun_{k}"] for k in KONSEPTLER if f"uzun_{k}" in ozet]
    if katlar:
        ozet["kat_min"] = round(min(katlar), 1); ozet["kat_max"] = round(max(katlar), 1)
    # Ev yemeklerine gore goreli oranlar (Sekil 05): uzun donem / iki yil once / guncel
    if "ev_yemekleri" in oran.columns and once is not None:
        for k in ("fast_food", "kirmizi_et", "tavuk"):
            if k in oran.columns:
                ozet[f"rel_uzun_{k}"] = round(float((uzun_pencere[k] / uzun_pencere["ev_yemekleri"]).mean()), 2)
                ozet[f"rel2y_{k}"] = round(float(once[k] / once["ev_yemekleri"]), 2)
                ozet[f"rel_{k}"] = round(float(son[k] / son["ev_yemekleri"]), 2)

    # --- Iki yillik maliyet artisi (katki tablosunun TOPLAM sutunu) ---
    kat_yol = os.path.join(OUT, "katki_ayristirma.csv")
    if os.path.exists(kat_yol):
        kat = pd.read_csv(kat_yol, index_col=0)
        toplam_kol = next((c for c in kat.columns if c.upper() == "TOPLAM"), None)
        if toplam_kol:
            ozet["maliyet_artisi_min"] = round(float(kat[toplam_kol].min()), 1)
            ozet["maliyet_artisi_max"] = round(float(kat[toplam_kol].max()), 1)
            for k in KONSEPTLER:
                if k in kat.index:
                    ozet[f"maliyet_artisi_{k}"] = round(float(kat.loc[k, toplam_kol]), 1)
            # en buyuk iki kalem katkisi (ortalama)
            kalemler = [c for c in kat.columns if c.upper() != "TOPLAM"]
            ort = kat[kalemler].mean().sort_values(ascending=False)
            ozet["katki_lider_kalem"] = str(ort.index[0])
            ozet["katki_lider_puan"] = round(float(ort.iloc[0]), 1)
            # Kalem bazinda konseptler arasi katki araligi ("gida 24-33 puan" cumlesi)
            for c in kalemler:
                ozet[f"katki_{c}_min"] = round(float(kat[c].min()), 1)
                ozet[f"katki_{c}_max"] = round(float(kat[c].max()), 1)
        else:
            _uyar("katki_ayristirma.csv'de TOPLAM sutunu yok")
    else:
        _uyar("katki_ayristirma.csv yok")

    # --- Ima edilen karlilik (merkez senaryo) ---
    try:
        merkez = pd.read_excel(XLSX, sheet_name="Ima_marj_%22.5_merkez", index_col=0)
        m_son = merkez.dropna(how="all").iloc[-1]
        for k in KONSEPTLER:
            if k in merkez.columns:
                ozet[f"marj_{k}"] = round(float(m_son[k]), 1)
    except Exception as exc:
        _uyar(f"ima marj sekmesi okunamadi: {exc}")

    # --- Duyarlilik: guncel oranin 18 senaryodaki araligi ---
    duy_yol = os.path.join(OUT, "duyarlilik.csv")
    if os.path.exists(duy_yol):
        duy = pd.read_csv(duy_yol)
        ozet["senaryo_adet"] = int(len(duy))
        for k in KONSEPTLER:
            kol = f"oran_son_{k}"
            if kol not in duy.columns:
                kol = f"oran26_{k}"   # eski sutun adi (geriye uyum)
            if kol in duy.columns:
                ozet[f"duy_min_{k}"] = round(float(duy[kol].min()), 2)
                ozet[f"duy_max_{k}"] = round(float(duy[kol].max()), 2)
    else:
        _uyar("duyarlilik.csv yok")

    # --- Enflasyon farklari ve kira temposu (EVDS_ham sekmesinden, guncel ay) ---
    # Sayfadaki "yemek hizmetleri - manset farki", "lokanta-oteller vs manset",
    # "konaklama", "kira enflasyonu zirvesi ve son degeri", "son uc ayin
    # yilliklandirilmis temposu" cumleleri buradan okunur.
    try:
        ev = pd.read_excel(XLSX, sheet_name="EVDS_ham", index_col=0)
        ev.index = pd.to_datetime(ev.index)
        yy = lambda kol: (ev[kol].pct_change(12) * 100)
        if "yemek_111" in ev and "tufe_genel" in ev:
            ozet["yh_yillik"] = round(float(yy("yemek_111").loc[t_son]), 1)
            ozet["manset_yillik"] = round(float(yy("tufe_genel").loc[t_son]), 1)
            ozet["yh_manset_fark"] = round(ozet["yh_yillik"] - ozet["manset_yillik"], 1)
            # iki yil once ayni fark ("2024'teki ~10 puan")
            ozet["yh_manset_fark_2y"] = round(float(yy("yemek_111").loc[t_once] - yy("tufe_genel").loc[t_once]), 1)
        if "lokanta_11" in ev:
            ozet["lokanta_yillik"] = round(float(yy("lokanta_11").loc[t_son]), 1)
        if "konaklama_1120" in ev:
            ozet["konaklama_yillik"] = round(float(yy("konaklama_1120").loc[t_son]), 1)
        if "kira_0411" in ev:
            kira_yy = yy("kira_0411")
            ozet["kira_yillik"] = round(float(kira_yy.loc[t_son]), 1)
            pencere = kira_yy.loc[t_once:t_son]
            ozet["kira_yillik_zirve"] = round(float(pencere.max()), 1)
            ozet["kira_yillik_zirve_ay"] = f"{AY_TR[pencere.idxmax().month]} {pencere.idxmax().year}"
            # son uc ayin yilliklandirilmis temposu
            k3 = ev["kira_0411"].loc[:t_son].iloc[-4:]
            ozet["kira_3ay_yillik"] = round(float(((k3.iloc[-1] / k3.iloc[0]) ** 4 - 1) * 100), 1)
            ozet["kira_2y_artis"] = round(float((ev["kira_0411"].loc[t_son] / ev["kira_0411"].loc[t_once] - 1) * 100), 0)
    except Exception as exc:
        _uyar(f"EVDS_ham enflasyon farklari okunamadi: {exc}")

    # --- Yemek hizmetleri enflasyonu - konsept maliyet enflasyonu farki (isaret) ---
    try:
        mal = pd.read_excel(XLSX, sheet_name="Konsept_maliyet", index_col=0)
        mal.index = pd.to_datetime(mal.index)
        mal_yy = (mal.pct_change(12) * 100).loc[t_son]
        if "yh_yillik" in ozet:
            farklar = [ozet["yh_yillik"] - float(mal_yy[k]) for k in KONSEPTLER if k in mal_yy]
            ozet["yh_maliyet_fark_min"] = round(min(farklar), 1)
            ozet["yh_maliyet_fark_max"] = round(max(farklar), 1)
    except Exception as exc:
        _uyar(f"Konsept_maliyet okunamadi: {exc}")

    yol = os.path.join(OUT, "ozet.json")
    json.dump(ozet, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(ozet, ensure_ascii=False))
    return ozet


if __name__ == "__main__":
    main()
