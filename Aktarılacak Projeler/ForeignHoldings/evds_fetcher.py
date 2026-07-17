"""
EVDS API'den veri çekme modülü
TCMB Elektronik Veri Dağıtım Sistemi entegrasyonu
"""

import pandas as pd
from datetime import datetime
from evds import evdsAPI

def fetch_evds_data(api_key: str, hisse_code: str, dibs_code: str, 
                   start_date: str, end_date: str) -> pd.DataFrame:
    """
    EVDS API'den hisse ve DIBS verilerini çeker
    
    Args:
        api_key: EVDS API anahtarı
        hisse_code: Hisse senedi seri kodu (örn: TP.MKNETHAR.M7)
        dibs_code: DIBS seri kodu (örn: TP.MKNETHAR.M8)
        start_date: Başlangıç tarihi (DD-MM-YYYY formatında)
        end_date: Bitiş tarihi (DD-MM-YYYY formatında)
    
    Returns:
        DataFrame: Tarih, Hisse ve DIBS verilerini içeren DataFrame
    """
    try:
        # Seri kodlarını düzelt (nokta/iki nokta üst üste tutarsızlığını gider)
        hisse_code = hisse_code.replace(":", ".")
        dibs_code = dibs_code.replace(":", ".")
        
        print(f"   📡 EVDS API'ye bağlanılıyor...")
        print(f"      Seriler: {hisse_code}, {dibs_code}")
        
        # EVDS API nesnesini oluştur
        evds = evdsAPI(api_key)
        
        # Verileri çek
        data = evds.get_data(
            [hisse_code, dibs_code],
            startdate=start_date,
            enddate=end_date
        )
        
        if data is None or data.empty:
            print("   ⚠️  EVDS'den veri dönmedi")
            return None
        
        
        # Sütun isimlerini düzenle
        # EVDS genellikle 'Tarih' ve seri kodlarını sütun olarak döner
        data.columns = data.columns.str.strip()
        
        # Tarih sütununu bul ve düzenle
        date_col = None
        for col in data.columns:
            if 'tarih' in col.lower() or 'date' in col.lower():
                date_col = col
                break
        
        if date_col is None:
            # İlk sütun genellikle tarih olur
            date_col = data.columns[0]
        
        # Tarih sütununu datetime'a çevir
        # EVDS tarihleri DD-MM-YYYY formatında gelir, dayfirst=True kullan
        data[date_col] = pd.to_datetime(data[date_col], format='%d-%m-%Y', errors='coerce')
        # Eğer format çalışmazsa, alternatif formatları dene
        if data[date_col].isna().any():
            data[date_col] = pd.to_datetime(data[date_col], dayfirst=True, errors='coerce')
        data = data.rename(columns={date_col: 'Tarih'})
        
        # Seri kodlarını sütun isimlerinden bul
        # EVDS sütun isimlerini alt çizgi ile döndürür: TP_MKNETHAR_M7, TP_MKNETHAR_M8
        hisse_col = None
        dibs_col = None
        
        # Önce tam eşleşmeyi dene (alt çizgi formatı)
        hisse_code_underscore = hisse_code.replace('.', '_')
        dibs_code_underscore = dibs_code.replace('.', '_')
        
        for col in data.columns:
            col_upper = col.upper()
            # Hem nokta hem alt çizgi formatını kontrol et
            # EVDS sütun isimleri: TP_MKNETHAR_M7, TP_MKNETHAR_M8 formatında
            if (hisse_code in col or hisse_code_underscore in col or 
                ('M7' in col_upper and 'TP' in col_upper and 'MKNETHAR' in col_upper) or
                col == 'TP_MKNETHAR_M7'):
                hisse_col = col
            if (dibs_code in col or dibs_code_underscore in col or 
                ('M8' in col_upper and 'TP' in col_upper and 'MKNETHAR' in col_upper) or
                col == 'TP_MKNETHAR_M8'):
                dibs_col = col
        
        if hisse_col is None or dibs_col is None:
            print(f"   ⚠️  Seri sütunları bulunamadı. Mevcut sütunlar: {list(data.columns)}")
            # Alternatif: sütunları manuel olarak atama
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            # YEARWEEK gibi sütunları hariç tut
            numeric_cols = [col for col in numeric_cols if 'YEARWEEK' not in col.upper()]
            if len(numeric_cols) >= 2:
                # M7 ve M8 sırasına göre atama yap
                for col in numeric_cols:
                    if 'M7' in col.upper() and hisse_col is None:
                        hisse_col = col
                    if 'M8' in col.upper() and dibs_col is None:
                        dibs_col = col
                # Eğer hala bulunamadıysa sırayla al
                if hisse_col is None or dibs_col is None:
                    if len(numeric_cols) >= 2:
                        hisse_col = numeric_cols[0]
                        dibs_col = numeric_cols[1]
                    else:
                        return None
            else:
                return None
        
        # Sütunları yeniden adlandır
        data = data.rename(columns={
            hisse_col: 'Hisse',
            dibs_col: 'DIBS'
        })
        
        # Sadece gerekli sütunları al
        df = data[['Tarih', 'Hisse', 'DIBS']].copy()
        
        # Tarih sütununu tekrar kontrol et (datetime'a çevrilmiş olabilir)
        if not pd.api.types.is_datetime64_any_dtype(df['Tarih']):
            # EVDS tarihleri DD-MM-YYYY formatında, dayfirst=True kullan
            df['Tarih'] = pd.to_datetime(df['Tarih'], format='%d-%m-%Y', dayfirst=True, errors='coerce')
        
        # Gelecek tarihleri de dahil et (NaN olmayan tüm tarihleri tut)
        # Sadece gerçekten geçersiz tarihleri (NaN) temizle
        invalid_dates = df['Tarih'].isna()
        if invalid_dates.any():
            print(f"   ⚠️  {invalid_dates.sum()} geçersiz tarih bulundu, temizleniyor...")
            df = df.dropna(subset=['Tarih'])
        
        df = df.sort_values('Tarih').reset_index(drop=True)
        
        # Sayısal değerleri temizle (virgül, nokta gibi karakterleri düzelt)
        for col in ['Hisse', 'DIBS']:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace(' ', '')
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print(f"   ✅ Veri başarıyla çekildi: {len(df)} kayıt")
        
        return df
        
    except Exception as e:
        print(f"   ❌ EVDS veri çekme hatası: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

