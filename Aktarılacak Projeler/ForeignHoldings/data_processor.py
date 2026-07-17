"""
Veri işleme modülü
Kümülatif hesaplamalar ve YTD veri hazırlama
"""

import pandas as pd
import numpy as np

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ham veriyi işler ve temizler
    
    Args:
        df: Ham EVDS verisi (Tarih, Hisse, DIBS sütunları)
    
    Returns:
        İşlenmiş DataFrame
    """
    df = df.copy()
    
    # Tarih sütununu datetime'a çevir (eğer değilse)
    if not pd.api.types.is_datetime64_any_dtype(df['Tarih']):
        df['Tarih'] = pd.to_datetime(df['Tarih'], errors='coerce')
    
    # Tarihe göre sırala
    df = df.sort_values('Tarih').reset_index(drop=True)
    
    # NaN değerleri 0 ile doldur (veri eksikliği durumunda)
    df['Hisse'] = df['Hisse'].fillna(0)
    df['DIBS'] = df['DIBS'].fillna(0)
    
    # Toplam hesapla
    df['Toplam'] = df['Hisse'] + df['DIBS']
    
    # Yıl ve hafta bilgilerini ekle (YTD için)
    df['Year'] = df['Tarih'].dt.year
    df['Week'] = df['Tarih'].dt.isocalendar().week
    
    return df

def calculate_cumulative(df: pd.DataFrame) -> pd.DataFrame:
    """
    Kümülatif toplamları hesaplar
    İlk değişim noktasından başlayarak toplam rakamı bulur
    
    Args:
        df: İşlenmiş veri
    
    Returns:
        Kümülatif değerler eklenmiş DataFrame
    """
    df = df.copy()
    
    # İlk sıfır olmayan değerleri bul
    hisse_first_idx = df[df['Hisse'] != 0].index
    dibs_first_idx = df[df['DIBS'] != 0].index
    
    if len(hisse_first_idx) > 0:
        hisse_start = hisse_first_idx[0]
    else:
        hisse_start = 0
    
    if len(dibs_first_idx) > 0:
        dibs_start = dibs_first_idx[0]
    else:
        dibs_start = 0
    
    # En erken başlangıç noktasını bul
    start_idx = min(hisse_start, dibs_start) if (hisse_first_idx.size > 0 and dibs_first_idx.size > 0) else (hisse_start if hisse_first_idx.size > 0 else dibs_start)
    
    # Kümülatif hesaplamalar (başlangıç noktasından itibaren)
    df['Hisse_Cumulative'] = 0.0
    df['DIBS_Cumulative'] = 0.0
    df['Toplam_Cumulative'] = 0.0
    
    # Başlangıç noktasından itibaren kümülatif topla
    for i in range(start_idx, len(df)):
        if i == start_idx:
            df.loc[i, 'Hisse_Cumulative'] = df.loc[i, 'Hisse']
            df.loc[i, 'DIBS_Cumulative'] = df.loc[i, 'DIBS']
        else:
            df.loc[i, 'Hisse_Cumulative'] = df.loc[i-1, 'Hisse_Cumulative'] + df.loc[i, 'Hisse']
            df.loc[i, 'DIBS_Cumulative'] = df.loc[i-1, 'DIBS_Cumulative'] + df.loc[i, 'DIBS']
        
        df.loc[i, 'Toplam_Cumulative'] = df.loc[i, 'Hisse_Cumulative'] + df.loc[i, 'DIBS_Cumulative']
    
    return df

def prepare_ytd_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    YTD (Year-to-Date) verilerini hazırlar
    Her yıl için hafta hafta kümülatif toplamları hesaplar
    Tüm yıl sıfır olan yılları filtreler
    
    Args:
        df: İşlenmiş veri
    
    Returns:
        YTD verileri içeren DataFrame (sıfır yıllar hariç)
    """
    df = df.copy()
    
    # Her yıl için ayrı ayrı YTD hesapla
    ytd_list = []
    
    for year in sorted(df['Year'].unique()):
        year_data = df[df['Year'] == year].copy()
        year_data = year_data.sort_values('Tarih').reset_index(drop=True)
        
        # Yıl içinde hafta hafta kümülatif toplam
        year_data['Hisse_YTD'] = year_data['Hisse'].cumsum()
        year_data['DIBS_YTD'] = year_data['DIBS'].cumsum()
        year_data['Toplam_YTD'] = year_data['Hisse_YTD'] + year_data['DIBS_YTD']
        
        # Yılın son değerlerini kontrol et (tüm yıl sıfır mı?)
        # Eğer yılın sonunda tüm YTD değerleri sıfırsa, bu yılı dahil etme
        if len(year_data) > 0:
            last_row = year_data.iloc[-1]
            # Yılın sonunda en az bir değer sıfır değilse dahil et
            if (last_row['Hisse_YTD'] != 0 or 
                last_row['DIBS_YTD'] != 0 or 
                last_row['Toplam_YTD'] != 0):
                ytd_list.append(year_data)
    
    if len(ytd_list) == 0:
        return pd.DataFrame()
    
    # Tüm yılları birleştir
    df_ytd = pd.concat(ytd_list, ignore_index=True)
    
    return df_ytd

