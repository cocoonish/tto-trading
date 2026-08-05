#!/usr/bin/env python3
"""Canlı özet — main.py'nin yazdığı foreign_holdings_data.csv'den, internetsiz.

Neden CSV'den (EVDS'i yeniden çağırmak yerine):
  Sayfa metnindeki "son hafta" ile hemen altındaki grafiğin son gözlemi AYNI
  çekimden gelmek zorunda. Özet ayrıca EVDS'e gitseydi, iki istek arasında
  TCMB yeni haftayı yayımladığında metin ile grafik ayrışırdı.

Üretilen anahtarlar Deger bileşeni tarafından okunur:
  <Deger proje="yabanci-pozisyon" anahtar="toplam_ytd" ondalik={0}>…</Deger>
"""

import json
import os
import sys

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "foreign_holdings_data.csv")

if not os.path.exists(CSV):
    raise SystemExit(
        f"HATA: {CSV} yok. Önce `python main.py` çalıştırın (özet o CSV'den üretilir)."
    )

df = pd.read_csv(CSV, parse_dates=["Tarih"]).sort_values("Tarih").reset_index(drop=True)
if df.empty:
    raise SystemExit(f"HATA: {CSV} boş.")

son = df.iloc[-1]
son_tarih = son["Tarih"]

# ---------------------------------------------------------------------------
# TAZELİK
# ---------------------------------------------------------------------------
# TCMB Haftalık Menkul Kıymet İstatistikleri'ni, Cuma biten haftayı izleyen
# PERŞEMBE yayımlar. Yani son gözlem ile bugün arasındaki normal gecikme 6-13
# gündür (yayım günü 6, yayımdan bir gün önce 13). 15 günü aşması, bir yayımın
# hiç alınamadığı (ya da hattın koşmadığı) anlamına gelir.
# Gecikme HER ZAMAN bugüne göre yeniden hesaplanır — damgalanıp kopyalanmaz.
TAZELIK_ESIGI_GUN = 15
bugun = pd.Timestamp.today().normalize()
gecikme_gun = int((bugun - son_tarih).days)
tazelik = "bayat" if gecikme_gun > TAZELIK_ESIGI_GUN else "güncel"


def topla(kolon: str, hafta: int) -> float:
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


# Cari yıl YTD (son gözlemin yılı)
cari_yil = int(son["Year"])
cari = df[df["Year"] == cari_yil]

# Geçen yılın AYNI hafta numarasına kadarki YTD — YTD grafiğinin okunması için
# gereken karşılaştırma. Hafta = "yılın kaçıncı Cuma'sı" (bkz. data_processor).
gecen = df[(df["Year"] == cari_yil - 1) & (df["Week"] <= int(son["Week"]))]

h_hafta, d_hafta, t_hafta = uclu(float(son["Hisse"]), float(son["DIBS"]))
h_4, d_4, t_4 = uclu(topla("Hisse", 4), topla("DIBS", 4))
h_13, d_13, t_13 = uclu(topla("Hisse", 13), topla("DIBS", 13))
h_ytd, d_ytd, t_ytd = uclu(float(cari["Hisse"].sum()), float(cari["DIBS"].sum()))
h_gec, d_gec, t_gec = uclu(float(gecen["Hisse"].sum()), float(gecen["DIBS"].sum()))
h_kum, d_kum, t_kum = uclu(float(son["Hisse_Cumulative"]), float(son["DIBS_Cumulative"]))

ozet = {
    "_tarih": son_tarih.strftime("%d.%m.%Y"),
    "son_hafta": son_tarih.strftime("%d.%m.%Y"),
    "yil": cari_yil,
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
    "gecikme_gun": gecikme_gun,
    "tazelik": tazelik,
}

# Kümülatif toplamın zirvesi ve zirveden bu yana çekilme.
# Çekilme, basılan iki sayının FARKI olarak yazılır (yukarıdaki `uclu` ile aynı
# gerekçe: okuyucu sayfadaki sayılarla doğrulayabilsin).
zirve_i = df["Toplam_Cumulative"].idxmax()
ozet["kum_zirve"] = float(round(df.loc[zirve_i, "Toplam_Cumulative"]))
ozet["kum_zirve_tarih"] = df.loc[zirve_i, "Tarih"].strftime("%d.%m.%Y")
ozet["kum_zirveden"] = ozet["toplam_kum"] - ozet["kum_zirve"]

if tazelik != "güncel":
    print(f"UYARI: seri bayat — son gözlem {ozet['_tarih']}, "
          f"gecikme {gecikme_gun} gün (eşik {TAZELIK_ESIGI_GUN}). "
          f"main.py'yi yeniden koşturun.", file=sys.stderr)

with open(os.path.join(BASE, "ozet.json"), "w", encoding="utf-8") as f:
    json.dump(ozet, f, ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False, indent=1))
