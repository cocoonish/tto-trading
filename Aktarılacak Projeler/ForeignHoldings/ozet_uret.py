#!/usr/bin/env python3
"""Canlı özet — main.py'nin yazdığı foreign_holdings_data.csv'den, internetsiz.

Neden CSV'den (EVDS'i yeniden çağırmak yerine):
  Sayfa metnindeki "son hafta" ile hemen altındaki grafiğin son gözlemi AYNI
  çekimden gelmek zorunda. Özet ayrıca EVDS'e gitseydi, iki istek arasında
  TCMB yeni haftayı yayımladığında metin ile grafik ayrışırdı.

Üretilen anahtarlar Deger bileşeni tarafından okunur:
  <Deger proje="yabanci-pozisyon" anahtar="toplam_ytd" ondalik={0}>…</Deger>

YAPI: hesabın tamamı fonksiyonlardadır ve dosyanın SONUNDAKİ `__main__` kapısı
yalnız `main()`i çağırır. Sebebi duman sınaması: modül içe aktarılabilir
olmasaydı `ozet_kur` sentetik bir çerçeveyle ve UYDURMA bir "bugün" ile hiç
koşturulamaz, aşağıdaki tazelik sözleşmesi de sınanamazdı.
"""

from __future__ import annotations

import json
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "foreign_holdings_data.csv")

# ---------------------------------------------------------------------------
# TAZELİK — ve bu ölçünün SINIRI
# ---------------------------------------------------------------------------
# TCMB Haftalık Menkul Kıymet İstatistikleri'ni, Cuma biten haftayı izleyen
# PERŞEMBE yayımlar. Yani son gözlem ile bugün arasındaki normal gecikme 6-13
# gündür (yayım günü 6, yayımdan bir gün önce 13). 15 günü aşması, bir yayımın
# hiç alınamadığı anlamına gelir.
#
# SINIR — BU HÜKÜM KOŞU ANINDA ÖLÇÜLÜR VE DOSYAYA DONAR. Hattın koşmadığını
# GÖREMEZ: hat bir ay hiç koşmazsa dosyada yazan "güncel" bir ay boyunca öyle
# kalır. 09.09.2026'da ölçüldü — depodaki özet 03.09 koşusundan kalma
# `gecikme_gun: 6` taşıyordu, verinin o günkü gerçek yaşı ise 12 gündü ve
# sayfa o donmuş 6'yı "bugüne göre 6 gün gecikme" diye basıyordu. Bu yüzden
# gecikme alanı SAYFA SÖZLEŞMESİNDE DEĞİL ve adı koşu-anı anlamını taşıyor
# (`kosu_gecikme_gun`): okurun gördüğü yaş, sayfa başındaki veri durumu
# şeridinde `_tarih`ten HER ZİYARETTE yeniden hesaplanır.
TAZELIK_ESIGI_GUN = 15


def tazelik_hukmu(son_tarih: pd.Timestamp, bugun: pd.Timestamp) -> tuple[int, str]:
    """(koşu anındaki gecikme, hüküm) — hüküm yalnız `bugun`e GÖREDİR.

    Ayrı bir fonksiyon olmasının sebebi ölçülebilirlik: duman sınaması aynı
    son gözlemi iki farklı "bugün" ile sorup hükmün gerçekten koşu anına bağlı
    olduğunu gösterebilsin (donmuş bir bayrak her iki çağrıda da aynı yanıtı
    verirdi ve kusur görünmezdi).
    """
    gecikme = int((bugun - son_tarih).days)
    return gecikme, ("bayat" if gecikme > TAZELIK_ESIGI_GUN else "güncel")


def topla(df: pd.DataFrame, kolon: str, hafta: int) -> float:
    """Son `hafta` gözlemin net toplamı (M USD)."""
    return float(df[kolon].tail(hafta).sum())


def uclu(hisse: float, dibs: float) -> tuple[float, float, float]:
    """(hisse, dibs, toplam) — hepsi tam sayıya yuvarlanmış, toplam BİLEŞENLERDEN.

    Toplamı ham veriden ayrıca yuvarlamak sayfada toplanmayan üçlüler üretiyordu:
    38,85 + 805,51 = 844,36 → 844 iken bileşenler 39 ve 806 basılıyor (=845).
    Sayfada üçü de yan yana göründüğü için toplam DAİMA basılan bileşenlerin
    toplamıdır; okuyucu kâğıt üstünde doğrulayabilsin.
    """
    h, d = round(hisse), round(dibs)
    return float(h), float(d), float(h + d)


def ozet_kur(df: pd.DataFrame, bugun: pd.Timestamp) -> dict:
    """Sayfanın okuduğu bütün anahtarlar. `bugun` yalnız tazelik ölçüsüne girer."""
    son = df.iloc[-1]
    son_tarih = son["Tarih"]
    kosu_gecikme_gun, tazelik = tazelik_hukmu(son_tarih, bugun)

    # Cari yıl YTD (son gözlemin yılı)
    cari_yil = int(son["Year"])
    cari = df[df["Year"] == cari_yil]

    # Geçen yılın AYNI hafta numarasına kadarki YTD — YTD grafiğinin okunması için
    # gereken karşılaştırma. Hafta = "yılın kaçıncı Cuma'sı" (bkz. data_processor).
    gecen = df[(df["Year"] == cari_yil - 1) & (df["Week"] <= int(son["Week"]))]

    h_hafta, d_hafta, t_hafta = uclu(float(son["Hisse"]), float(son["DIBS"]))
    h_4, d_4, t_4 = uclu(topla(df, "Hisse", 4), topla(df, "DIBS", 4))
    h_13, d_13, t_13 = uclu(topla(df, "Hisse", 13), topla(df, "DIBS", 13))
    h_ytd, d_ytd, t_ytd = uclu(float(cari["Hisse"].sum()), float(cari["DIBS"].sum()))
    h_gec, d_gec, t_gec = uclu(float(gecen["Hisse"].sum()), float(gecen["DIBS"].sum()))
    h_kum, d_kum, t_kum = uclu(float(son["Hisse_Cumulative"]),
                               float(son["DIBS_Cumulative"]))

    ozet = {
        "_tarih": son_tarih.strftime("%d.%m.%Y"),
        "son_hafta": son_tarih.strftime("%d.%m.%Y"),
        # YIL bir sayı değil ETİKETTİR: sayı olarak yazılırsa sayfanın biçim
        # sözleşmesi onu binlik ayracıyla "2.026" diye basar. Adlandırdığı şey
        # bir gözlem değil bir SÜTUN olan her anahtar metin yazılır.
        "yil": str(cari_yil),
        "hafta_no": int(son["Week"]),

        # --- son hafta (tek haftalık net işlem) ---
        "hisse_hafta": h_hafta,
        "dibs_hafta": d_hafta,
        "toplam_hafta": t_hafta,

        # --- kısa vadeli momentum ---
        "hisse_4h": h_4,
        "dibs_4h": d_4,
        "toplam_4h": t_4,
        "hisse_13h": h_13,
        "dibs_13h": d_13,
        "toplam_13h": t_13,

        # --- yılbaşından bugüne ---
        "hisse_ytd": h_ytd,
        "dibs_ytd": d_ytd,
        "toplam_ytd": t_ytd,

        # --- geçen yılın aynı haftasına kadarki YTD ---
        "hisse_ytd_gecen": h_gec,
        "dibs_ytd_gecen": d_gec,
        "toplam_ytd_gecen": t_gec,

        # --- serinin başından bugüne kümülatif ---
        "hisse_kum": h_kum,
        "dibs_kum": d_kum,
        "toplam_kum": t_kum,

        # --- seri künyesi ---
        "baslangic": df["Tarih"].iloc[0].strftime("%d.%m.%Y"),
        "hafta_sayisi": int(len(df)),

        # --- koşu anının kendi ölçüsü (SAYFA BU İKİSİNİ METNE BASMAZ) ---
        # `kosu_gecikme_gun` bu koşuda ölçülmüş yaştır ve dosyada donar; okurun
        # gördüğü yaş sayfa başındaki şeritte `_tarih`ten yeniden hesaplanır.
        # `tazelik` ise şeridin bayatlık hükmüdür — aynı sınırla: hat koşmazsa
        # hüküm de ilerlemez.
        "kosu_gecikme_gun": kosu_gecikme_gun,
        "bayat_tolerans_gun": TAZELIK_ESIGI_GUN,
        "tazelik": tazelik,
    }

    # Kümülatif toplamın zirvesi ve zirveden bu yana çekilme.
    # Çekilme, basılan iki sayının FARKI olarak yazılır (yukarıdaki `uclu` ile aynı
    # gerekçe: okuyucu sayfadaki sayılarla doğrulayabilsin).
    zirve_i = df["Toplam_Cumulative"].idxmax()
    ozet["kum_zirve"] = float(round(df.loc[zirve_i, "Toplam_Cumulative"]))
    ozet["kum_zirve_tarih"] = df.loc[zirve_i, "Tarih"].strftime("%d.%m.%Y")
    ozet["kum_zirveden"] = ozet["toplam_kum"] - ozet["kum_zirve"]
    return ozet


def veri_oku() -> pd.DataFrame:
    if not os.path.exists(CSV):
        raise SystemExit(
            f"HATA: {CSV} yok. Önce `python main.py` çalıştırın "
            "(özet o CSV'den üretilir)."
        )
    df = (pd.read_csv(CSV, parse_dates=["Tarih"])
          .sort_values("Tarih").reset_index(drop=True))
    if df.empty:
        raise SystemExit(f"HATA: {CSV} boş.")
    return df


def main() -> None:
    df = veri_oku()
    ozet = ozet_kur(df, pd.Timestamp.today().normalize())

    if ozet["tazelik"] != "güncel":
        print(f"UYARI: seri bayat — son gözlem {ozet['_tarih']}, "
              f"gecikme {ozet['kosu_gecikme_gun']} gün "
              f"(tolerans {TAZELIK_ESIGI_GUN}). "
              f"main.py'yi yeniden koşturun.", file=sys.stderr)

    with open(os.path.join(BASE, "ozet.json"), "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=1)
    print(json.dumps(ozet, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
