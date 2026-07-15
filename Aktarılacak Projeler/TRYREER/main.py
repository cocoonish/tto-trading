"""
Türkiye Reel Efektif Döviz Kuru Analizi
- %70 PPI (Yi-ÜFE) + %30 CPI (TÜFE) bazlı ağırlıklı REDK
- 10 yıllık hareketli ortalamadan % sapma hesaplama
- Plotly ile interaktif görselleştirme
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================
# PARAMETRİK DEĞİŞKENLER (Kolay değiştirilebilir)
# ============================================

# Dosya yolları
CPI_FILE = "TUFE.xlsx"  # CPI bazlı REDK dosyası
PPI_FILE = "Yi-UFE.xlsx"  # PPI bazlı REDK dosyası

# Ağırlıklar (toplam 1.0 olmalı)
PPI_WEIGHT = 0.30  # PPI (Yi-ÜFE) ağırlığı
CPI_WEIGHT = 0.70  # CPI (TÜFE) ağırlığı

# Hareketli ortalama pencereleri (ay cinsinden)
MA_WINDOW_10Y = 120  # 10 yıllık hareketli ortalama
MA_WINDOW_5Y = 60    # 5 yıllık hareketli ortalama

# Çıktı dosyası
OUTPUT_HTML = "reer_analysis.html"

# ============================================
# VERİ YÜKLEME VE İŞLEME
# ============================================

def load_data():
    """Excel dosyalarından verileri yükle ve birleştir"""
    # CPI (TÜFE) verisi
    df_cpi = pd.read_excel(CPI_FILE)
    # NaN satırlarını temizle (TCMB notları vs.)
    df_cpi = df_cpi.dropna(subset=['Dönem'])
    df_cpi['Dönem'] = pd.to_datetime(df_cpi['Dönem'], errors='coerce')
    df_cpi = df_cpi.dropna(subset=['Dönem'])  # Geçersiz tarihleri temizle
    cpi_col = [col for col in df_cpi.columns if 'TÜFE  Bazlı' in col][0]
    df_cpi = df_cpi[['Dönem', cpi_col]].rename(columns={cpi_col: 'CPI_REER'})
    
    # PPI (Yi-ÜFE) verisi
    df_ppi = pd.read_excel(PPI_FILE)
    # NaN satırlarını temizle
    df_ppi = df_ppi.dropna(subset=['Dönem'])
    df_ppi['Dönem'] = pd.to_datetime(df_ppi['Dönem'], errors='coerce')
    df_ppi = df_ppi.dropna(subset=['Dönem'])  # Geçersiz tarihleri temizle
    ppi_col = [col for col in df_ppi.columns if 'Yi-ÜFE' in col][0]
    df_ppi = df_ppi[['Dönem', ppi_col]].rename(columns={ppi_col: 'PPI_REER'})
    
    # Birleştir
    df = pd.merge(df_cpi, df_ppi, on='Dönem', how='inner')
    df = df.sort_values('Dönem').reset_index(drop=True)
    
    return df


def calculate_composite_reer(df):
    """Ağırlıklı kompozit REDK hesapla"""
    df['Composite_REER'] = (PPI_WEIGHT * df['PPI_REER']) + (CPI_WEIGHT * df['CPI_REER'])
    return df


def calculate_moving_average_deviation(df):
    """5 ve 10 yıllık hareketli ortalama ve % sapma hesapla (Kompozit, PPI, CPI için)"""
    
    # === KOMPOZİT REDK ===
    df['MA_10Y'] = df['Composite_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['MA_5Y'] = df['Composite_REER'].rolling(window=MA_WINDOW_5Y, min_periods=MA_WINDOW_5Y).mean()
    df['Deviation_10Y_Pct'] = ((df['Composite_REER'] - df['MA_10Y']) / df['MA_10Y']) * 100
    df['Deviation_5Y_Pct'] = ((df['Composite_REER'] - df['MA_5Y']) / df['MA_5Y']) * 100
    
    # === %100 PPI REDK ===
    df['PPI_MA_10Y'] = df['PPI_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['PPI_Deviation_10Y_Pct'] = ((df['PPI_REER'] - df['PPI_MA_10Y']) / df['PPI_MA_10Y']) * 100
    
    # === %100 CPI REDK ===
    df['CPI_MA_10Y'] = df['CPI_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['CPI_Deviation_10Y_Pct'] = ((df['CPI_REER'] - df['CPI_MA_10Y']) / df['CPI_MA_10Y']) * 100
    
    return df


def create_plot(df):
    """Plotly ile interaktif grafik oluştur - Kompozit, PPI ve CPI karşılaştırmalı"""
    # Sadece 10Y MA'nın hesaplandığı dönemler
    df_plot = df.dropna(subset=['MA_10Y', 'Deviation_10Y_Pct']).copy()
    
    # 5 alt grafik: REDK+MA, Kompozit 10Y Sapma, Kompozit 5Y Sapma, PPI Sapma, CPI Sapma
    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.25, 0.19, 0.19, 0.19, 0.19],
        subplot_titles=(
            f'Türkiye Reel Efektif Döviz Kuru ({PPI_WEIGHT*100:.0f}% PPI + {CPI_WEIGHT*100:.0f}% CPI)',
            'Kompozit REDK - 10Y MA\'dan % Sapma',
            'Kompozit REDK - 5Y MA\'dan % Sapma',
            '100% PPI (Yi-ÜFE) Bazlı REDK - 10Y MA\'dan % Sapma',
            '100% CPI (TÜFE) Bazlı REDK - 10Y MA\'dan % Sapma'
        )
    )
    
    # === ROW 1: REDK ve MA'lar ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Composite_REER'],
            name='Kompozit REDK',
            line=dict(color='#1f77b4', width=2),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>REDK:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['MA_10Y'],
            name='10Y MA',
            line=dict(color='#ff7f0e', width=2, dash='dash'),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>10Y MA:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['MA_5Y'],
            name='5Y MA',
            line=dict(color='#2ca02c', width=2, dash='dot'),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>5Y MA:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # === ROW 2: Kompozit 10Y Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_10Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color='rgba(255, 0, 0, 0.8)', width=0.5),
            fillcolor='rgba(255, 0, 0, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_10Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color='rgba(0, 128, 0, 0.8)', width=0.5),
            fillcolor='rgba(0, 128, 0, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_10Y_Pct'],
            name='Kompozit 10Y Sapma',
            line=dict(color='#d62728', width=2),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>Kompozit 10Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=2, col=1
    )
    
    # === ROW 3: Kompozit 5Y Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_5Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color='rgba(255, 127, 14, 0.8)', width=0.5),
            fillcolor='rgba(255, 127, 14, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_5Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color='rgba(31, 119, 180, 0.8)', width=0.5),
            fillcolor='rgba(31, 119, 180, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=3, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['Deviation_5Y_Pct'],
            name='Kompozit 5Y Sapma',
            line=dict(color='#9467bd', width=2),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>Kompozit 5Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=3, col=1
    )
    
    # === ROW 4: %100 PPI Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['PPI_Deviation_10Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color='rgba(148, 103, 189, 0.8)', width=0.5),
            fillcolor='rgba(148, 103, 189, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['PPI_Deviation_10Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color='rgba(44, 160, 44, 0.8)', width=0.5),
            fillcolor='rgba(44, 160, 44, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=4, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['PPI_Deviation_10Y_Pct'],
            name='PPI 10Y Sapma',
            line=dict(color='#8c564b', width=2),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>PPI 10Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=4, col=1
    )
    
    # === ROW 5: %100 CPI Sapma ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['CPI_Deviation_10Y_Pct'].clip(lower=0),
            fill='tozeroy',
            line=dict(color='rgba(227, 119, 194, 0.8)', width=0.5),
            fillcolor='rgba(227, 119, 194, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=5, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['CPI_Deviation_10Y_Pct'].clip(upper=0),
            fill='tozeroy',
            line=dict(color='rgba(127, 127, 127, 0.8)', width=0.5),
            fillcolor='rgba(127, 127, 127, 0.3)',
            hoverinfo='skip',
            showlegend=False
        ),
        row=5, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['CPI_Deviation_10Y_Pct'],
            name='CPI 10Y Sapma',
            line=dict(color='#e377c2', width=2),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>CPI 10Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=5, col=1
    )
    
    # Sıfır çizgileri
    for row in [2, 3, 4, 5]:
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=row, col=1)
    
    # Son değerler
    last_date = df_plot['Dönem'].iloc[-1]
    last_deviation_10y = df_plot['Deviation_10Y_Pct'].iloc[-1]
    last_deviation_5y = df_plot['Deviation_5Y_Pct'].iloc[-1]
    last_ppi_dev = df_plot['PPI_Deviation_10Y_Pct'].iloc[-1]
    last_cpi_dev = df_plot['CPI_Deviation_10Y_Pct'].iloc[-1]
    last_reer = df_plot['Composite_REER'].iloc[-1]
    
    # Layout ayarları
    fig.update_layout(
        height=1200,
        title=dict(
            text=f"<b>Türkiye REDK Analizi ({last_date.strftime('%Y-%m')})</b><br>" +
                 f"<sup>Kompozit: 10Y={last_deviation_10y:+.1f}%, 5Y={last_deviation_5y:+.1f}% | " +
                 f"PPI: {last_ppi_dev:+.1f}% | CPI: {last_cpi_dev:+.1f}%</sup>",
            x=0.5,
            font=dict(size=18)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="center",
            x=0.5
        ),
        hovermode='x unified',
        template='plotly_white'
    )
    
    # Y ekseni etiketleri
    fig.update_yaxes(title_text="REDK", row=1, col=1)
    fig.update_yaxes(title_text="% Sapma", row=2, col=1)
    fig.update_yaxes(title_text="% Sapma", row=3, col=1)
    fig.update_yaxes(title_text="% Sapma", row=4, col=1)
    fig.update_yaxes(title_text="% Sapma", row=5, col=1)
    
    # X ekseni
    fig.update_xaxes(title_text="Tarih", row=5, col=1)
    
    return fig


def main():
    """Ana fonksiyon"""
    print("📊 Veri yükleniyor...")
    df = load_data()
    print(f"   ✅ {len(df)} satır veri yüklendi ({df['Dönem'].min().strftime('%Y-%m')} - {df['Dönem'].max().strftime('%Y-%m')})")
    
    print(f"\n📈 Kompozit REDK hesaplanıyor ({PPI_WEIGHT*100:.0f}% PPI + {CPI_WEIGHT*100:.0f}% CPI)...")
    df = calculate_composite_reer(df)
    
    print(f"\n📉 5Y ve 10Y hareketli ortalama ve % sapmalar hesaplanıyor...")
    df = calculate_moving_average_deviation(df)
    
    # Son değerler
    last_row = df.dropna(subset=['Deviation_10Y_Pct']).iloc[-1]
    print(f"\n📍 Son değerler ({last_row['Dönem'].strftime('%Y-%m')}):")
    print(f"   - PPI REDK: {last_row['PPI_REER']:.2f}")
    print(f"   - CPI REDK: {last_row['CPI_REER']:.2f}")
    print(f"   - Kompozit REDK: {last_row['Composite_REER']:.2f}")
    print(f"\n   Kompozit ({PPI_WEIGHT*100:.0f}% PPI + {CPI_WEIGHT*100:.0f}% CPI):")
    print(f"   - 10Y MA: {last_row['MA_10Y']:.2f} → Sapma: {last_row['Deviation_10Y_Pct']:+.2f}%")
    print(f"   - 5Y MA: {last_row['MA_5Y']:.2f} → Sapma: {last_row['Deviation_5Y_Pct']:+.2f}%")
    print(f"\n   %100 PPI (Yi-ÜFE):")
    print(f"   - 10Y MA: {last_row['PPI_MA_10Y']:.2f} → Sapma: {last_row['PPI_Deviation_10Y_Pct']:+.2f}%")
    print(f"\n   %100 CPI (TÜFE):")
    print(f"   - 10Y MA: {last_row['CPI_MA_10Y']:.2f} → Sapma: {last_row['CPI_Deviation_10Y_Pct']:+.2f}%")
    
    print(f"\n🎨 Grafik oluşturuluyor...")
    fig = create_plot(df)
    
    # HTML olarak kaydet
    fig.write_html(OUTPUT_HTML)
    print(f"   ✅ Grafik '{OUTPUT_HTML}' olarak kaydedildi")
    
    # Grafiği tarayıcıda aç
    try:
        import webbrowser
        import os
        webbrowser.open('file://' + os.path.realpath(OUTPUT_HTML))
        print(f"   🌐 Grafik tarayıcıda açılıyor...")
    except Exception as e:
        print(f"   ⚠️ Tarayıcı açılamadı: {e}")
    
    # İsteğe bağlı: Hesaplanmış veriyi CSV olarak kaydet
    output_csv = "reer_analysis_data.csv"
    df.to_csv(output_csv, index=False)
    print(f"   ✅ Veri '{output_csv}' olarak kaydedildi")
    
    return df, fig


if __name__ == "__main__":
    df, fig = main()

