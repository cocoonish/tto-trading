"""EVDS API'den veri çekme modülü — TCMB Elektronik Veri Dağıtım Sistemi.

Uç nokta doğrudan `requests` ile çağrılır (evds3 REST). Eski `evds` PyPI paketi
evds2'ye gider, anahtarı URL'e gömer ve CI imajında kurulu değildir; depodaki
diğer EVDS hatları da (TRYREER, USDTRYDeval, TCMBNetRezerv) doğrudan requests
kullanır — bu modül aynı deseni izler.
"""

import pandas as pd
import requests
from urllib.parse import urlencode

from evds_ortak import EVDS_BASE, gizle_anahtar


def fetch_evds_data(api_key: str, hisse_code: str, dibs_code: str,
                    start_date: str, end_date: str) -> pd.DataFrame:
    """EVDS'ten hisse ve DİBS net işlem serilerini çeker.

    Args:
        api_key: EVDS API anahtarı (`key` başlığında gönderilir, URL'e girmez)
        hisse_code: Hisse senedi seri kodu (ör. TP.MKNETHAR.M7)
        dibs_code: DİBS seri kodu (ör. TP.MKNETHAR.M8)
        start_date: Başlangıç tarihi (DD-MM-YYYY)
        end_date: Bitiş tarihi (DD-MM-YYYY)

    Returns:
        DataFrame: Tarih, Hisse, DIBS sütunları — yalnızca VERİSİ OLAN haftalar.
        Hata durumunda None.
    """
    try:
        # Seri kodlarını düzelt (nokta/iki nokta üst üste tutarsızlığını gider)
        hisse_code = hisse_code.replace(":", ".")
        dibs_code = dibs_code.replace(":", ".")

        print("   📡 EVDS API'ye bağlanılıyor...")
        print(f"      Seriler: {hisse_code}, {dibs_code}")
        print(f"      Pencere: {start_date} → {end_date}")

        parametre = {
            "series": f"{hisse_code}-{dibs_code}",
            "startDate": start_date,
            "endDate": end_date,
            "type": "json",
        }
        yanit = requests.get(
            f"{EVDS_BASE}/{urlencode(parametre)}",
            headers={"key": api_key},
            timeout=60,
        )
        yanit.raise_for_status()
        icerik = yanit.json()

        satirlar = icerik.get("items") if isinstance(icerik, dict) else None
        if not satirlar:
            print("   ⚠️  EVDS'den veri dönmedi")
            return None

        data = pd.DataFrame(satirlar)
        data.columns = data.columns.str.strip()

        # EVDS sütun adlarında noktalar alt çizgiye döner: TP.MKNETHAR.M7 → TP_MKNETHAR_M7
        hisse_col = hisse_code.replace(".", "_")
        dibs_col = dibs_code.replace(".", "_")
        eksik = [c for c in (hisse_col, dibs_col) if c not in data.columns]
        if eksik:
            print(f"   ⚠️  Seri sütunları bulunamadı: {eksik}. "
                  f"Dönen sütunlar: {list(data.columns)}")
            return None

        data["Tarih"] = pd.to_datetime(data["Tarih"], format="%d-%m-%Y", errors="coerce")
        for col in (hisse_col, dibs_col):
            data[col] = pd.to_numeric(data[col], errors="coerce")

        df = data[["Tarih", hisse_col, dibs_col]].rename(
            columns={hisse_col: "Hisse", dibs_col: "DIBS"}
        )
        df = df.dropna(subset=["Tarih"])

        # KRİTİK: veri grubu (bie_mknethar) 2007'ye kadar haftalık satır iskeleti
        # döndürür, ama BU İKİ SERİ 11-09-2020'de başlar; öncesi boştur. O boşluk
        # "o hafta net işlem sıfırdı" DEĞİL, "veri yok" demektir. Sıfırla doldurmak
        # kümülatif seriyi bozmaz ama YTD grafiklerine 13 yıllık sahte düz-sıfır
        # çizgi basar ve yıllık istatistikleri seyreltir — o yüzden atılır.
        oncesi = len(df)
        df = df.dropna(subset=["Hisse", "DIBS"], how="all")
        if oncesi != len(df):
            print(f"   ℹ️  {oncesi - len(df)} boş hafta atıldı (seri henüz başlamamış)")

        df = df.sort_values("Tarih").reset_index(drop=True)

        # Serinin içinde tek taraflı boşluk kalırsa sessizce sıfırlanmasın diye uyar
        for col in ("Hisse", "DIBS"):
            bos = int(df[col].isna().sum())
            if bos:
                print(f"   ⚠️  {col} serisinde {bos} hafta boş (0 varsayılacak)")

        print(f"   ✅ Veri başarıyla çekildi: {len(df)} kayıt "
              f"({df['Tarih'].min():%d-%m-%Y} → {df['Tarih'].max():%d-%m-%Y})")

        return df

    except Exception as e:
        print(f"   ❌ EVDS veri çekme hatası: {gizle_anahtar(str(e))}")
        import traceback
        traceback.print_exc()
        return None
