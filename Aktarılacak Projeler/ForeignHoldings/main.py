"""
EVDS Yurtdışı Yerleşikler DIBS ve Hisse Senedi Takip Sistemi
Ana parametreler ve çalıştırma dosyası
"""

# ============================================================================
# PARAMETRELER - Buradan kolayca değiştirilebilir
# ============================================================================

# EVDS API anahtarı (EVDS web sitesinden alınmalı)
EVDS_API_KEY = "YOUR_API_KEY_HERE"  # .env dosyasından da yüklenebilir

# EVDS seri kodları
EVDS_HISSE_CODE = "TP.MKNETHAR.M7"  # Hisse senedi kesin alım-satım
EVDS_DIBS_CODE = "TP.MKNETHAR.M8"   # DIBS kesin alım-satım

# Veri çekme parametreleri
START_DATE = "01-01-2000"  # Başlangıç tarihi (format: DD-MM-YYYY)
END_DATE = None  # None ise yıl sonuna kadar çeker (tüm mevcut veriler için)

# Grafik ayarları
OUTPUT_DIR = "charts"  # Grafiklerin kaydedileceği klasör
CHART_WIDTH = 1400
CHART_HEIGHT = 700
CHART_THEME = "plotly_white"  # plotly, plotly_white, plotly_dark, ggplot2, seaborn, simple_white, none

# Para birimi gösterimi
CURRENCY_UNIT = "M USD"  # Milyon USD

# ============================================================================
# ANA PROGRAM
# ============================================================================

import os
from datetime import datetime
from dotenv import load_dotenv
from evds_fetcher import fetch_evds_data
from data_processor import process_data, calculate_cumulative, prepare_ytd_data
from visualizer import create_cumulative_charts, create_ytd_charts

def main():
    """Ana çalıştırma fonksiyonu"""
    
    # .env dosyasından API key yükle (varsa)
    load_dotenv()
    api_key = os.getenv("EVDS_API_KEY", EVDS_API_KEY)
    
    if api_key == "YOUR_API_KEY_HERE":
        print("⚠️  UYARI: EVDS_API_KEY ayarlanmamış!")
        print("   Lütfen .env dosyasına EVDS_API_KEY=your_key ekleyin veya main.py'de güncelleyin")
        return
    
    print("📊 EVDS Veri Çekme Başlatılıyor...")
    print(f"   Hisse Kodu: {EVDS_HISSE_CODE}")
    print(f"   DIBS Kodu: {EVDS_DIBS_CODE}")
    
    # Veri çekme
    # END_DATE None ise, mevcut yılın sonuna kadar çek (tüm haftalık veriler için)
    if END_DATE:
        end_date = END_DATE
    else:
        # Mevcut yılın sonuna kadar çek
        current_year = datetime.now().year
        end_date = f"31-12-{current_year}"
    df = fetch_evds_data(
        api_key=api_key,
        hisse_code=EVDS_HISSE_CODE,
        dibs_code=EVDS_DIBS_CODE,
        start_date=START_DATE,
        end_date=end_date
    )
    
    if df is None or df.empty:
        print("❌ Veri çekilemedi!")
        return
    
    print(f"✅ {len(df)} kayıt çekildi")
    print(f"   Tarih aralığı: {df['Tarih'].min()} - {df['Tarih'].max()}")
    
    # Veri işleme
    print("\n🔄 Veri işleniyor...")
    df_processed = process_data(df)
    df_cumulative = calculate_cumulative(df_processed)
    df_ytd = prepare_ytd_data(df_processed)
    
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

