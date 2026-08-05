"""
EVDS Yurtdışı Yerleşikler DİBS ve Hisse Senedi Takip Sistemi
Ana parametreler ve çalıştırma dosyası
"""

# ============================================================================
# PARAMETRELER - Buradan kolayca değiştirilebilir
# ============================================================================

import os
from datetime import datetime

import pandas as pd

from evds_ortak import (
    EVDS_DIBS_SERIES,
    EVDS_HISSE_SERIES,
    EVDS_ILERI_GUN,
    EVDS_START,
    evds_anahtari,
)
from evds_fetcher import fetch_evds_data
from data_processor import process_data, calculate_cumulative, prepare_ytd_data
from visualizer import create_cumulative_charts, create_ytd_charts

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# EVDS anahtarı KAYNAĞA GÖMÜLMEZ; sırayla TTO_EVDS_KEY ortam değişkeninden ve
# bu klasördeki .evds_key dosyasından okunur (bkz. evds_ortak.py). İkisi de
# yoksa hat açık bir hatayla durur — anahtarsız istek atıp boş grafik üretmez.

# EVDS seri kodları (ayrıntılı açıklama: evds_ortak.py)
EVDS_HISSE_CODE = EVDS_HISSE_SERIES  # TP.MKNETHAR.M7 — hisse senedi net işlem
EVDS_DIBS_CODE = EVDS_DIBS_SERIES    # TP.MKNETHAR.M8 — DİBS kesin alım net işlem

# Veri çekme parametreleri
START_DATE = EVDS_START  # Serinin gerçek başlangıcı (01-09-2020)
END_DATE = None  # None ise bugünden EVDS_ILERI_GUN gün ileriye kadar çeker

# İşlenmiş veri: ozet_uret.py buradan okur. Böylece sayfa metnindeki sayılar,
# grafiklerin çizildiği AYNI çekimden gelir; ayrıca özet üretimi ağ gerektirmez.
DATA_CSV = os.path.join(SCRIPT_DIR, "foreign_holdings_data.csv")

# Grafik ayarları
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "charts")  # Grafiklerin kaydedileceği klasör
CHART_WIDTH = 1400
CHART_HEIGHT = 700
CHART_THEME = "plotly_white"  # plotly, plotly_white, plotly_dark, ggplot2, seaborn, simple_white, none

# Para birimi gösterimi
CURRENCY_UNIT = "M USD"  # Milyon USD

# ============================================================================
# ANA PROGRAM
# ============================================================================


def main():
    """Ana çalıştırma fonksiyonu"""

    api_key = evds_anahtari()  # yoksa RuntimeError — sessiz anahtarsız istek yok

    print("📊 EVDS Veri Çekme Başlatılıyor...")
    print(f"   Hisse Kodu: {EVDS_HISSE_CODE}")
    print(f"   DİBS Kodu: {EVDS_DIBS_CODE}")

    # Sorgu bitişi bilerek ileri alınır (gerekçe: evds_ortak.EVDS_ILERI_GUN).
    # Gelecek tarihli endDate EVDS'te yalnız yayımlanmış satırları döndürür.
    if END_DATE:
        end_date = END_DATE
    else:
        end_date = (pd.Timestamp.today()
                    + pd.Timedelta(days=EVDS_ILERI_GUN)).strftime("%d-%m-%Y")

    df = fetch_evds_data(
        api_key=api_key,
        hisse_code=EVDS_HISSE_CODE,
        dibs_code=EVDS_DIBS_CODE,
        start_date=START_DATE,
        end_date=end_date
    )

    if df is None or df.empty:
        print("❌ Veri çekilemedi!")
        raise SystemExit(1)

    print(f"✅ {len(df)} kayıt çekildi")
    print(f"   Tarih aralığı: {df['Tarih'].min():%d-%m-%Y} - {df['Tarih'].max():%d-%m-%Y}")

    # Veri işleme
    print("\n🔄 Veri işleniyor...")
    df_processed = process_data(df)
    df_cumulative = calculate_cumulative(df_processed)
    df_ytd = prepare_ytd_data(df_processed)

    # İşlenmiş seriyi diske yaz (ozet_uret.py'nin tek girdisi)
    kolonlar = ['Tarih', 'Hisse', 'DIBS', 'Toplam', 'Year', 'Week',
                'Hisse_Cumulative', 'DIBS_Cumulative', 'Toplam_Cumulative']
    df_cumulative[kolonlar].to_csv(DATA_CSV, index=False)
    print(f"   💾 İşlenmiş veri yazıldı: {os.path.basename(DATA_CSV)}")

    # Çıktı klasörü oluştur
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Grafikler oluştur
    print("\n📈 Grafikler oluşturuluyor...")

    # 1. Kümülatif grafikler
    print("   → Kümülatif grafikler...")
    create_cumulative_charts(
        df_cumulative,
        output_dir=OUTPUT_DIR,
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        theme=CHART_THEME,
        currency_unit=CURRENCY_UNIT
    )

    # 2. YTD grafikler
    print("   → YTD karşılaştırmalı grafikler...")
    create_ytd_charts(
        df_ytd,
        output_dir=OUTPUT_DIR,
        width=CHART_WIDTH,
        height=CHART_HEIGHT,
        theme=CHART_THEME,
        currency_unit=CURRENCY_UNIT
    )

    print(f"\n✅ Tüm grafikler '{OUTPUT_DIR}' klasörüne kaydedildi!")
    print(f"   Toplam {len(df_ytd['Year'].unique())} yıl için YTD grafikleri oluşturuldu")


if __name__ == "__main__":
    main()
