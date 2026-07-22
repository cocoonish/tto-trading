"""
USDTRY ve Reel Efektif Döviz Kuru Sapması İlişkisi Analizi
- Yahoo Finance'ten USDTRY verisi
- REDK uzun vadeli ortalamalarından sapma
- Sapma ile USDTRY değişimi arasındaki korelasyon
- Öngörü gücü analizi (lead-lag)
"""

import os
import sys

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from datetime import datetime, timedelta

# ============================================
# PARAMETRİK DEĞİŞKENLER
# ============================================

# Tüm yollar script klasörüne göre — hangi dizinden çalıştırılırsa çalıştırılsın bulunur
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# main.py'den ağırlıkları ve ortak veri yükleyiciyi import et
# (load_data: önce TCMB EVDS, hata olursa TUFE.xlsx / Yi-UFE.xlsx yedeği)
from main import PPI_WEIGHT, CPI_WEIGHT, CPI_FILE, PPI_FILE, load_data

# Hareketli ortalama pencereleri (ay)
MA_WINDOW_10Y = 120
MA_WINDOW_5Y = 60

# Analiz pencereleri (ay) - sapma sonrası USDTRY değişimi
FORWARD_WINDOWS = [1, 3, 6, 12]  # 1, 3, 6, 12 ay sonraki değişim

# Yerel USDTRY önbelleği (önceki çalıştırmanın çıktısı) — önce buradan okunur,
# yoksa/eksikse yfinance'e düşülür
USDTRY_LOCAL_CSV = os.path.join(SCRIPT_DIR, "usdtry_reer_data.csv")

# Çıktı dosyası
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "usdtry_reer_analysis.html")

# ============================================
# VERİ YÜKLEME
# ============================================

def load_reer_data():
    """REDK verilerini yükle (main.load_data → EVDS, yedeği Excel)"""
    df = load_data()

    # Kompozit REDK
    df['Composite_REER'] = (PPI_WEIGHT * df['PPI_REER']) + (CPI_WEIGHT * df['CPI_REER'])
    
    # MA ve Sapma hesapla
    df['MA_10Y'] = df['Composite_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['MA_5Y'] = df['Composite_REER'].rolling(window=MA_WINDOW_5Y, min_periods=MA_WINDOW_5Y).mean()
    df['Deviation_10Y'] = ((df['Composite_REER'] - df['MA_10Y']) / df['MA_10Y']) * 100
    df['Deviation_5Y'] = ((df['Composite_REER'] - df['MA_5Y']) / df['MA_5Y']) * 100
    
    # PPI ve CPI sapmaları - 10Y
    df['PPI_MA_10Y'] = df['PPI_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['CPI_MA_10Y'] = df['CPI_REER'].rolling(window=MA_WINDOW_10Y, min_periods=MA_WINDOW_10Y).mean()
    df['PPI_Deviation_10Y'] = ((df['PPI_REER'] - df['PPI_MA_10Y']) / df['PPI_MA_10Y']) * 100
    df['CPI_Deviation_10Y'] = ((df['CPI_REER'] - df['CPI_MA_10Y']) / df['CPI_MA_10Y']) * 100
    
    # PPI ve CPI sapmaları - 5Y
    df['PPI_MA_5Y'] = df['PPI_REER'].rolling(window=MA_WINDOW_5Y, min_periods=MA_WINDOW_5Y).mean()
    df['CPI_MA_5Y'] = df['CPI_REER'].rolling(window=MA_WINDOW_5Y, min_periods=MA_WINDOW_5Y).mean()
    df['PPI_Deviation_5Y'] = ((df['PPI_REER'] - df['PPI_MA_5Y']) / df['PPI_MA_5Y']) * 100
    df['CPI_Deviation_5Y'] = ((df['CPI_REER'] - df['CPI_MA_5Y']) / df['CPI_MA_5Y']) * 100
    
    return df


def load_usdtry_local():
    """Yerel usdtry_reer_data.csv'den aylık USDTRY serisini oku.

    Dosya önceki çalıştırmanın birleştirilmiş çıktısıdır; USDTRY sütunu zaten
    aylık ortalama olarak kayıtlıdır. Dosya yoksa/sütunlar eksikse None döner.
    """
    if not os.path.exists(USDTRY_LOCAL_CSV):
        return None
    try:
        df = pd.read_csv(USDTRY_LOCAL_CSV)
        if not {'Dönem', 'USDTRY'}.issubset(df.columns):
            return None
        df['Dönem'] = pd.to_datetime(df['Dönem'], errors='coerce')
        for col in ['High', 'Low']:
            if col not in df.columns:
                df[col] = np.nan
        df = df[['Dönem', 'USDTRY', 'High', 'Low']].dropna(subset=['Dönem', 'USDTRY'])
        df = df.sort_values('Dönem').reset_index(drop=True)
        if df.empty:
            return None
        return df
    except Exception as e:
        print(f"   ⚠️ Yerel CSV okunamadı ({e}) — yfinance'e geçiliyor")
        return None


def fetch_usdtry_yfinance():
    """Yahoo Finance'ten USDTRY verisi çek (aylık ortalamaya indirgenir)"""
    import yfinance as yf

    print("📥 Yahoo Finance'ten USDTRY verisi çekiliyor...")

    # Geniş tarih aralığı
    ticker = yf.Ticker("TRY=X")
    df = ticker.history(period="max")

    if df.empty:
        # Alternatif ticker dene
        ticker = yf.Ticker("USDTRY=X")
        df = ticker.history(period="max")

    if df.empty:
        raise RuntimeError("yfinance boş veri döndürdü (TRY=X ve USDTRY=X)")

    df = df.reset_index()
    df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)

    # Aylık ortalamalara dönüştür (REDK aylık)
    df['YearMonth'] = df['Date'].dt.to_period('M')
    monthly = df.groupby('YearMonth').agg({
        'Close': 'mean',
        'High': 'max',
        'Low': 'min',
        'Volume': 'sum'
    }).reset_index()

    monthly['Dönem'] = monthly['YearMonth'].dt.to_timestamp()
    monthly = monthly.rename(columns={'Close': 'USDTRY'})
    monthly = monthly[['Dönem', 'USDTRY', 'High', 'Low']]

    print(f"   ✅ {len(monthly)} aylık veri çekildi ({monthly['Dönem'].min().strftime('%Y-%m')} - {monthly['Dönem'].max().strftime('%Y-%m')})")

    return monthly


def fetch_usdtry(reer_last_date=None):
    """USDTRY verisini getir: önce yerel CSV, yoksa/eksikse yfinance.

    reer_last_date verilirse yerel serinin REDK verisinin sonunu kapsayıp
    kapsamadığı kontrol edilir; kapsamıyorsa yfinance denenir, o da
    başarısız olursa eldeki yerel seriyle devam edilir.
    """
    local = load_usdtry_local()

    if local is not None:
        yeterli = reer_last_date is None or local['Dönem'].max() >= reer_last_date
        if yeterli:
            print(f"📥 USDTRY yerel CSV'den okundu: {len(local)} ay "
                  f"({local['Dönem'].min().strftime('%Y-%m')} - {local['Dönem'].max().strftime('%Y-%m')})")
            return local
        print(f"   ℹ️ Yerel USDTRY serisi {local['Dönem'].max().strftime('%Y-%m')}'de bitiyor, "
              f"REDK {reer_last_date.strftime('%Y-%m')}'e kadar gidiyor — yfinance deneniyor")

    try:
        return fetch_usdtry_yfinance()
    except Exception as e:
        if local is not None:
            print(f"   ⚠️ yfinance başarısız ({e}) — yerel CSV ile devam ediliyor")
            return local
        raise RuntimeError(f"USDTRY verisi alınamadı: yerel CSV yok, yfinance hatası: {e}")


def merge_data(df_reer, df_usdtry):
    """REDK ve USDTRY verilerini birleştir"""
    df = pd.merge(df_reer, df_usdtry, on='Dönem', how='inner')
    df = df.sort_values('Dönem').reset_index(drop=True)
    
    # USDTRY değişimleri hesapla
    df['USDTRY_Change_1M'] = df['USDTRY'].pct_change(1) * 100
    df['USDTRY_Change_3M'] = df['USDTRY'].pct_change(3) * 100
    df['USDTRY_Change_6M'] = df['USDTRY'].pct_change(6) * 100
    df['USDTRY_Change_12M'] = df['USDTRY'].pct_change(12) * 100
    
    # İleri dönük değişimler (sapma sonrası ne oldu?)
    for months in FORWARD_WINDOWS:
        df[f'USDTRY_Forward_{months}M'] = df['USDTRY'].shift(-months).div(df['USDTRY']).sub(1).mul(100)
    
    return df


def calculate_correlations(df, ma_type='10Y'):
    """Sapma ve USDTRY değişimi arasındaki korelasyonları hesapla (RSE dahil)"""
    df_clean = df.dropna()
    
    results = {
        'Sapma Türü': [],
        'USDTRY Penceresi': [],
        'Korelasyon': [],
        'R2': [],
        'RSE': [],
        'P-Value': [],
        'Örneklem': []
    }
    
    # MA tipine göre sütunlar
    if ma_type == '10Y':
        deviation_cols = ['Deviation_10Y', 'Deviation_5Y', 'PPI_Deviation_10Y', 'CPI_Deviation_10Y']
        deviation_names = ['Kompozit 10Y', 'Kompozit 5Y', 'PPI 10Y', 'CPI 10Y']
    else:  # 5Y
        deviation_cols = ['Deviation_5Y', 'Deviation_10Y', 'PPI_Deviation_5Y', 'CPI_Deviation_5Y']
        deviation_names = ['Kompozit 5Y', 'Kompozit 10Y', 'PPI 5Y', 'CPI 5Y']
    
    for dev_col, dev_name in zip(deviation_cols, deviation_names):
        if dev_col not in df_clean.columns:
            continue
        for months in FORWARD_WINDOWS:
            forward_col = f'USDTRY_Forward_{months}M'
            
            # NaN olmayan verileri al
            mask = df_clean[[dev_col, forward_col]].notna().all(axis=1)
            x = df_clean.loc[mask, dev_col]
            y = df_clean.loc[mask, forward_col]
            
            if len(x) > 10:
                # Regresyon ile RSE hesapla
                slope, intercept, r, pval, se = stats.linregress(x, y)
                y_pred = slope * x + intercept
                residuals = y - y_pred
                rse = np.sqrt(np.sum(residuals**2) / (len(x) - 2))
                
                results['Sapma Türü'].append(dev_name)
                results['USDTRY Penceresi'].append(f'{months}M Sonra')
                results['Korelasyon'].append(r)
                results['R2'].append(r**2)
                results['RSE'].append(rse)
                results['P-Value'].append(pval)
                results['Örneklem'].append(len(x))
    
    return pd.DataFrame(results)


def analyze_deviation_bands(df, ma_type='10Y'):
    """Sapma bantlarına göre ortalama USDTRY değişimi"""
    dev_col = f'Deviation_{ma_type}'
    df_clean = df.dropna(subset=[dev_col])
    
    # Sapma bantları tanımla
    bands = [
        ('< -20%', df_clean[dev_col] < -20),
        ('-20% ile -10%', (df_clean[dev_col] >= -20) & (df_clean[dev_col] < -10)),
        ('-10% ile 0%', (df_clean[dev_col] >= -10) & (df_clean[dev_col] < 0)),
        ('0% ile +10%', (df_clean[dev_col] >= 0) & (df_clean[dev_col] < 10)),
        ('+10% ile +20%', (df_clean[dev_col] >= 10) & (df_clean[dev_col] < 20)),
        ('> +20%', df_clean[dev_col] >= 20),
    ]
    
    results = []
    for band_name, mask in bands:
        subset = df_clean[mask]
        if len(subset) > 0:
            for months in FORWARD_WINDOWS:
                forward_col = f'USDTRY_Forward_{months}M'
                avg_change = subset[forward_col].mean()
                median_change = subset[forward_col].median()
                count = subset[forward_col].notna().sum()
                
                results.append({
                    'Sapma Bandı': band_name,
                    'Pencere': f'{months}M',
                    'Ort. USDTRY Değişimi': avg_change,
                    'Medyan Değişim': median_change,
                    'Gözlem Sayısı': count
                })
    
    return pd.DataFrame(results)


def create_change_regression_plot(df, ma_type='10Y', periods=(1, 3, 6)):
    """Eşzamanlı sapma değişimi vs USDTRY değişimi regresyon grafikleri.

    periods: incelenecek değişim pencereleri (ay). Varsayılan (1, 3, 6) üç
    panelli grafik üretir; tek eleman verilirse (ör. [3]) tek panelli odak
    grafik üretilir — usdtry_regression_3m.html bu yolla üretilir.
    """
    dev_col = f'Deviation_{ma_type}'
    df_plot = df.dropna(subset=[dev_col, 'USDTRY']).copy()

    # Farklı pencereler için eşzamanlı değişimler hesapla
    periods = list(periods)
    for p in periods:
        df_plot[f'Deviation_Change_{p}M'] = df_plot[dev_col].diff(p)
        df_plot[f'USDTRY_Change_{p}M'] = df_plot['USDTRY'].pct_change(p) * 100

    # Pencere başına bir subplot
    fig = make_subplots(
        rows=1, cols=len(periods),
        subplot_titles=[f'{p} Aylık Değişim' for p in periods],
        horizontal_spacing=0.08
    )
    
    colors = ['#1f77b4', '#2ca02c', '#d62728']
    regression_stats = []
    
    for i, (period, color) in enumerate(zip(periods, colors)):
        dev_col = f'Deviation_Change_{period}M'
        usd_col = f'USDTRY_Change_{period}M'
        
        # Temiz veri
        mask = df_plot[[dev_col, usd_col]].notna().all(axis=1)
        df_clean = df_plot[mask]
        
        x = df_clean[dev_col]
        y = df_clean[usd_col]
        
        # Regresyon hesapla
        slope, intercept, r, p, se = stats.linregress(x, y)
        
        # Residual Standard Error (RSE) hesapla
        y_pred = slope * x + intercept
        residuals = y - y_pred
        rse = np.sqrt(np.sum(residuals**2) / (len(x) - 2))  # n-2 serbestlik derecesi
        
        regression_stats.append({
            'period': period,
            'r2': r**2,
            'corr': r,
            'pval': p,
            'slope': slope,
            'intercept': intercept,
            'rse': rse,  # Residual Standard Error
            'n': len(x)
        })
        
        # Scatter noktaları
        fig.add_trace(
            go.Scatter(
                x=x, y=y,
                mode='markers',
                marker=dict(size=6, color=color, opacity=0.5),
                text=df_clean['Dönem'].dt.strftime('%Y-%m'),
                hovertemplate=f'<b>%{{text}}</b><br>Sapma Δ{period}M: %{{x:.1f}}<br>USDTRY Δ{period}M: %{{y:.1f}}%<extra></extra>',
                showlegend=False
            ),
            row=1, col=i+1
        )
        
        # Regresyon çizgisi
        x_line = np.linspace(x.min(), x.max(), 100)
        y_line = slope * x_line + intercept
        fig.add_trace(
            go.Scatter(
                x=x_line, y=y_line,
                mode='lines',
                line=dict(color='red', width=2),
                name=f'{period}M: R²={r**2:.3f}' if i == 0 else None,
                showlegend=(i == 0)
            ),
            row=1, col=i+1
        )
        
        # Sıfır çizgileri
        fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=0.5, row=1, col=i+1)
        fig.add_vline(x=0, line_dash="dash", line_color="gray", line_width=0.5, row=1, col=i+1)
        
        # İstatistik annotation (RSE eklendi)
        pval_str = f"{p:.2e}" if p < 0.001 else f"{p:.4f}"
        fig.add_annotation(
            text=f"<b>R² = {r**2:.3f}</b><br>r = {r:.3f}<br>Eğim = {slope:.2f}<br>σ = {rse:.2f}%<br>p = {pval_str}<br>N = {len(x)}",
            xref=f"x{i+1}" if i > 0 else "x", yref=f"y{i+1}" if i > 0 else "y",
            x=x.min() + (x.max()-x.min())*0.05,
            y=y.max() - (y.max()-y.min())*0.05,
            showarrow=False, font=dict(size=10),
            align='left', bgcolor='rgba(255,255,255,0.9)',
            bordercolor='gray', borderwidth=1
        )
        
        # Son değer
        last_row = df_clean.iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=[last_row[dev_col]], y=[last_row[usd_col]],
                mode='markers',
                marker=dict(size=12, color='red', symbol='star'),
                hovertemplate=f"SON: {last_row['Dönem'].strftime('%Y-%m')}<extra></extra>",
                showlegend=False
            ),
            row=1, col=i+1
        )
    
    # Başlık: tek pencereli odak grafikte pencereyi belirt
    if len(periods) == 1:
        baslik = f"<b>Eşzamanlı {periods[0]} Aylık Değişim: REDK Sapması ({ma_type}) vs USDTRY</b>"
    else:
        baslik = f"<b>Eşzamanlı Değişimler: REDK Sapması ({ma_type}) vs USDTRY</b>"

    # Layout - yatay olarak büyütülmüş
    fig.update_layout(
        height=550,
        width=max(750, 500 * len(periods)),  # Panel sayısına göre genişlik
        title=dict(
            text=baslik,
            x=0.5, y=0.98,
            font=dict(size=20)
        ),
        template='plotly_white',
        margin=dict(t=100, r=50, b=70, l=70)  # Üst margin artırıldı
    )
    
    # Alt başlık annotation
    fig.add_annotation(
        text=f"Aynı dönemdeki {ma_type} sapma değişimi ve kur değişimi nasıl ilişkili?",
        xref="paper", yref="paper", x=0.5, y=1.08,
        showarrow=False, font=dict(size=13, color="gray")
    )
    
    # Eksen başlıkları
    for i, period in enumerate(periods):
        fig.update_xaxes(title_text=f"Sapma Δ{period}M (puan)", row=1, col=i+1)
        fig.update_yaxes(title_text=f"USDTRY Δ{period}M (%)", row=1, col=i+1)
    
    return fig, df_plot, regression_stats


def create_analysis_plot(df, corr_df, band_df, ma_type='10Y'):
    """Kapsamlı analiz grafiği - Temiz ve anlaşılır layout"""
    dev_col = f'Deviation_{ma_type}'
    df_plot = df.dropna(subset=[dev_col, 'USDTRY']).copy()
    
    # 4 ayrı satır grafik - secondary_y ile çift eksen (dikey büyütülmüş)
    fig = make_subplots(
        rows=4, cols=2,
        specs=[
            [{"secondary_y": True, "colspan": 2}, None],
            [{"colspan": 2}, None],
            [{"type": "scatter"}, {"type": "scatter"}],
            [{"type": "bar"}, {"type": "table"}]
        ],
        vertical_spacing=0.10,
        horizontal_spacing=0.10,
        row_heights=[0.24, 0.20, 0.28, 0.28]  # Scatter ve bar için daha fazla alan
    )
    
    # === ROW 1: USDTRY ve Sapma (iki y ekseni) ===
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['USDTRY'],
            name='USDTRY',
            line=dict(color='#1f77b4', width=2.5),
            hovertemplate='%{x|%Y-%m}<br>USDTRY: %{y:.2f}<extra></extra>'
        ),
        row=1, col=1, secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot[dev_col],
            name=f'REDK Sapma {ma_type} %',
            line=dict(color='#d62728', width=2),
            hovertemplate='%{x|%Y-%m}<br>Sapma: %{y:.1f}%<extra></extra>'
        ),
        row=1, col=1, secondary_y=True
    )
    
    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1, row=1, col=1)
    
    # === ROW 2: İleri dönük USDTRY değişimleri ===
    colors_forward = {'1': '#17becf', '3': '#bcbd22', '6': '#9467bd', '12': '#e377c2'}
    for months in FORWARD_WINDOWS:
        forward_col = f'USDTRY_Forward_{months}M'
        fig.add_trace(
            go.Scatter(
                x=df_plot['Dönem'],
                y=df_plot[forward_col],
                name=f'{months}M sonra',
                line=dict(color=colors_forward[str(months)], width=1.5),
                hovertemplate=f'%{{x|%Y-%m}}<br>{months}M sonra: %{{y:.1f}}%<extra></extra>'
            ),
            row=2, col=1
        )
    
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1, row=2, col=1)
    
    # === ROW 3: Scatter plotlar ===
    # 6 ay scatter
    mask_6m = df_plot[[dev_col, 'USDTRY_Forward_6M']].notna().all(axis=1)
    fig.add_trace(
        go.Scatter(
            x=df_plot.loc[mask_6m, dev_col],
            y=df_plot.loc[mask_6m, 'USDTRY_Forward_6M'],
            mode='markers',
            marker=dict(color='#9467bd', size=5, opacity=0.5),
            hovertemplate='Sapma: %{x:.1f}%<br>6M sonra: %{y:.1f}%<extra></extra>',
            showlegend=False
        ),
        row=3, col=1
    )
    
    # 6M regresyon
    if mask_6m.sum() > 10:
        x_6m = df_plot.loc[mask_6m, dev_col]
        y_6m = df_plot.loc[mask_6m, 'USDTRY_Forward_6M']
        slope, intercept, r, p, se = stats.linregress(x_6m, y_6m)
        x_line = np.linspace(x_6m.min(), x_6m.max(), 100)
        y_line = slope * x_line + intercept
        fig.add_trace(
            go.Scatter(x=x_line, y=y_line, mode='lines',
                      line=dict(color='red', width=2), showlegend=False),
            row=3, col=1
        )
    
    # 12 ay scatter
    mask_12m = df_plot[[dev_col, 'USDTRY_Forward_12M']].notna().all(axis=1)
    fig.add_trace(
        go.Scatter(
            x=df_plot.loc[mask_12m, dev_col],
            y=df_plot.loc[mask_12m, 'USDTRY_Forward_12M'],
            mode='markers',
            marker=dict(color='#8c564b', size=5, opacity=0.5),
            hovertemplate='Sapma: %{x:.1f}%<br>12M sonra: %{y:.1f}%<extra></extra>',
            showlegend=False
        ),
        row=3, col=2
    )
    
    # 12M regresyon
    if mask_12m.sum() > 10:
        x_12m = df_plot.loc[mask_12m, dev_col]
        y_12m = df_plot.loc[mask_12m, 'USDTRY_Forward_12M']
        slope, intercept, r, p, se = stats.linregress(x_12m, y_12m)
        x_line = np.linspace(x_12m.min(), x_12m.max(), 100)
        y_line = slope * x_line + intercept
        fig.add_trace(
            go.Scatter(x=x_line, y=y_line, mode='lines',
                      line=dict(color='red', width=2), showlegend=False),
            row=3, col=2
        )
    
    # === ROW 4: Bant analizi bar chart ===
    band_12m = band_df[band_df['Pencere'] == '12M']
    if not band_12m.empty:
        colors = ['#2ca02c' if x < 15 else '#ff7f0e' if x < 25 else '#d62728' 
                  for x in band_12m['Ort. USDTRY Değişimi']]
        fig.add_trace(
            go.Bar(
                x=band_12m['Sapma Bandı'],
                y=band_12m['Ort. USDTRY Değişimi'],
                marker_color=colors,
                text=[f'{x:.0f}%' for x in band_12m['Ort. USDTRY Değişimi']],
                textposition='outside',
                showlegend=False
            ),
            row=4, col=1
        )
    
    # Korelasyon tablosu (R² ve σ eklendi)
    corr_filtered = corr_df[corr_df['Sapma Türü'] == f'Kompozit {ma_type}']
    fig.add_trace(
        go.Table(
            header=dict(
                values=['<b>Pencere</b>', '<b>R²</b>', '<b>r</b>', '<b>σ (%)</b>', '<b>P</b>'],
                fill_color='#2c3e50',
                font=dict(color='white', size=10),
                align='center', height=28
            ),
            cells=dict(
                values=[
                    corr_filtered['USDTRY Penceresi'].tolist(),
                    [f'{x:.3f}' for x in corr_filtered['R2']],
                    [f'{x:.3f}' for x in corr_filtered['Korelasyon']],
                    [f'{x:.1f}' for x in corr_filtered['RSE']],
                    ['<.01' if x < 0.01 else f'{x:.2f}' for x in corr_filtered['P-Value']]
                ],
                fill_color='#ecf0f1',
                align='center', font=dict(size=10), height=25
            )
        ),
        row=4, col=2
    )
    
    # Son değerler
    last_date = df_plot['Dönem'].iloc[-1]
    last_dev = df_plot[dev_col].iloc[-1]
    last_usdtry = df_plot['USDTRY'].iloc[-1]
    
    # Layout - TEMİZ (dikey olarak büyütülmüş)
    fig.update_layout(
        height=1800,  # Daha da büyük
        title=dict(
            text=f"<b>REDK Sapması ({ma_type}) ve USDTRY İlişkisi</b>",
            x=0.5, y=0.99,
            font=dict(size=22)
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="top", y=0.995,
            xanchor="center", x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            font=dict(size=11)
        ),
        template='plotly_white',
        margin=dict(t=120, r=60, b=60, l=70)
    )
    
    # Alt başlık annotation
    fig.add_annotation(
        text=f"Son: {last_date.strftime('%Y-%m')} | USDTRY: {last_usdtry:.2f} | Sapma: {last_dev:+.1f}%",
        xref="paper", yref="paper", x=0.5, y=1.01,
        showarrow=False, font=dict(size=13, color="gray")
    )
    
    # Panel başlıkları - düzeltilmiş pozisyonlar
    fig.add_annotation(text=f"<b>1. USDTRY ve REDK {ma_type} Sapması</b>", 
                      xref="paper", yref="paper", x=0.5, y=0.97, 
                      showarrow=False, font=dict(size=14))
    fig.add_annotation(text="<b>2. İleri Dönük USDTRY Değişimi (%)</b>", 
                      xref="paper", yref="paper", x=0.5, y=0.73, 
                      showarrow=False, font=dict(size=14))
    fig.add_annotation(text="<b>3. Scatter: Sapma vs 6M Sonra</b>", 
                      xref="paper", yref="paper", x=0.25, y=0.52, 
                      showarrow=False, font=dict(size=12))
    fig.add_annotation(text="<b>3. Scatter: Sapma vs 12M Sonra</b>", 
                      xref="paper", yref="paper", x=0.75, y=0.52, 
                      showarrow=False, font=dict(size=12))
    fig.add_annotation(text="<b>4. Sapma Bandına Göre 12M Sonra USDTRY</b>", 
                      xref="paper", yref="paper", x=0.25, y=0.25, 
                      showarrow=False, font=dict(size=12))
    fig.add_annotation(text="<b>Korelasyon Tablosu</b>", 
                      xref="paper", yref="paper", x=0.75, y=0.25, 
                      showarrow=False, font=dict(size=12))
    
    # Y ekseni başlıkları
    fig.update_yaxes(title_text="USDTRY", row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Sapma (%)", row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="USDTRY Değişim (%)", row=2, col=1)
    fig.update_yaxes(title_text="6M Sonra (%)", row=3, col=1)
    fig.update_yaxes(title_text="12M Sonra (%)", row=3, col=2)
    fig.update_yaxes(title_text="Ort. Değişim (%)", row=4, col=1)
    
    # X ekseni başlıkları
    fig.update_xaxes(title_text="", row=1, col=1)
    fig.update_xaxes(title_text="", row=2, col=1)
    fig.update_xaxes(title_text="Sapma (%)", row=3, col=1)
    fig.update_xaxes(title_text="Sapma (%)", row=3, col=2)
    fig.update_xaxes(title_text="", row=4, col=1, tickangle=30)
    
    return fig


def print_summary(df, corr_df, band_df, ma_type='10Y'):
    """Özet analiz yazdır"""
    dev_col = f'Deviation_{ma_type}'
    
    print(f"\n📈 Korelasyon Analizi (Kompozit {ma_type} Sapma):")
    print("-"*50)
    corr_filtered = corr_df[corr_df['Sapma Türü'] == f'Kompozit {ma_type}']
    for _, row in corr_filtered.iterrows():
        sig = "***" if row['P-Value'] < 0.01 else "**" if row['P-Value'] < 0.05 else "*" if row['P-Value'] < 0.1 else ""
        print(f"   {row['USDTRY Penceresi']}: r = {row['Korelasyon']:+.3f} {sig} (n={row['Örneklem']})")
    
    print("\n📊 Sapma Bantlarına Göre Ortalama USDTRY Değişimi (12M Sonra):")
    print("-"*50)
    band_12m = band_df[band_df['Pencere'] == '12M']
    for _, row in band_12m.iterrows():
        print(f"   {row['Sapma Bandı']:>15}: {row['Ort. USDTRY Değişimi']:+.1f}% (n={row['Gözlem Sayısı']:.0f})")
    
    print("\n💡 YORUM:")
    print("-"*50)
    
    # Son değerler
    last = df.dropna(subset=[dev_col]).iloc[-1]
    current_dev = last[dev_col]
    
    if current_dev > 10:
        print(f"   ⚠️ Güncel sapma ({current_dev:+.1f}%) ortalamanın üzerinde.")
        print("   → Tarihsel veriler, bu durumda USDTRY'nin yükselme eğiliminde olduğunu gösteriyor.")
    elif current_dev < -10:
        print(f"   ✅ Güncel sapma ({current_dev:+.1f}%) ortalamanın altında.")
        print("   → Tarihsel veriler, bu durumda USDTRY'nin düşme/stabil kalma eğiliminde olduğunu gösteriyor.")
    else:
        print(f"   ℹ️ Güncel sapma ({current_dev:+.1f}%) nötr bölgede.")
        print("   → USDTRY için güçlü bir yön sinyali yok.")
    
    print("\n   * Negatif korelasyon = Sapma düşükken (TL değersiz) USDTRY yükseliyor")
    print("   * Pozitif korelasyon = Sapma yüksekken (TL değerli) USDTRY yükseliyor")
    print("   *** p<0.01, ** p<0.05, * p<0.1")


def main():
    """Ana fonksiyon"""
    print("="*60)
    print("🔍 USDTRY - REDK SAPMA ANALİZİ BAŞLIYOR")
    print("="*60)
    
    # REDK verisi yükle
    print("\n📊 REDK verileri yükleniyor...")
    df_reer = load_reer_data()
    print(f"   ✅ REDK: {len(df_reer)} satır ({df_reer['Dönem'].min().strftime('%Y-%m')} - {df_reer['Dönem'].max().strftime('%Y-%m')})")
    
    # USDTRY verisi getir (önce yerel CSV, yoksa/eksikse yfinance)
    df_usdtry = fetch_usdtry(reer_last_date=df_reer['Dönem'].max())
    
    # Birleştir
    print("\n🔗 Veriler birleştiriliyor...")
    df = merge_data(df_reer, df_usdtry)
    print(f"   ✅ Birleştirilmiş: {len(df)} satır ({df['Dönem'].min().strftime('%Y-%m')} - {df['Dönem'].max().strftime('%Y-%m')})")
    
    # Her iki MA tipi için analiz yap
    for ma_type in ['10Y', '5Y']:
        print(f"\n{'='*60}")
        print(f"📊 {ma_type} HAREKETLI ORTALAMA ANALİZİ")
        print(f"{'='*60}")
        
        # Korelasyon analizi
        print(f"\n📐 {ma_type} Korelasyonlar hesaplanıyor...")
        corr_df = calculate_correlations(df, ma_type)
        
        # Bant analizi
        print(f"📊 {ma_type} Sapma bantları analiz ediliyor...")
        band_df = analyze_deviation_bands(df, ma_type)
        
        # Özet yazdır
        print_summary(df, corr_df, band_df, ma_type)
        
        # Ana analiz grafiği oluştur
        print(f"\n🎨 {ma_type} Grafikler oluşturuluyor...")
        fig = create_analysis_plot(df, corr_df, band_df, ma_type)
        
        # Kaydet (plotly.js CDN'den — dosya ~4.6MB yerine ~100KB olur)
        output_html = os.path.join(SCRIPT_DIR, f"usdtry_reer_analysis_{ma_type.lower()}.html")
        fig.write_html(output_html, include_plotlyjs='cdn')
        print(f"   ✅ Ana grafik '{output_html}' olarak kaydedildi")
        
        # Eşzamanlı değişim regresyon grafikleri (1M, 3M, 6M)
        print(f"\n📈 {ma_type} Eşzamanlı değişim regresyon grafikleri oluşturuluyor...")
        fig_regression, df_reg, reg_stats = create_change_regression_plot(df, ma_type)
        
        # Regresyon istatistiklerini yazdır
        print(f"\n📊 {ma_type} Eşzamanlı Değişim Regresyon Sonuçları:")
        print("-" * 75)
        print(f"{'Pencere':<10} {'R²':<10} {'Korelasyon':<12} {'Eğim':<10} {'Std.Sapma':<12} {'P-value':<12} {'N':<6}")
        print("-" * 75)
        for stat in reg_stats:
            print(f"{stat['period']}M{'':<7} {stat['r2']:<10.4f} {stat['corr']:<12.4f} {stat['slope']:<10.3f} {stat['rse']:<12.2f} {stat['pval']:<12.2e} {stat['n']:<6}")
        print("-" * 75)
        
        # Yorum
        best = max(reg_stats, key=lambda x: x['r2'])
        print(f"\n💡 En güçlü ilişki: {best['period']} aylık değişimlerde (R²={best['r2']:.3f})")
        print(f"   → Sapma {best['period']}M'de 1 puan artarsa, USDTRY {best['period']}M'de {best['slope']:.2f}% değişir")
        print(f"   → Tahmin standart sapması (σ): ±{best['rse']:.2f}%")
        
        # Son değerler
        print(f"\n📍 Son Değerler:")
        for period in [1, 3, 6]:
            last_dev = df_reg[f'Deviation_Change_{period}M'].dropna().iloc[-1]
            last_usd = df_reg[f'USDTRY_Change_{period}M'].dropna().iloc[-1]
            print(f"   {period}M: Sapma Δ = {last_dev:+.2f} puan, USDTRY Δ = {last_usd:+.1f}%")
        
        # Kaydet (plotly.js CDN'den — dosya ~4.6MB yerine ~100KB olur)
        regression_html = os.path.join(SCRIPT_DIR, f"usdtry_regression_{ma_type.lower()}.html")
        fig_regression.write_html(regression_html, include_plotlyjs='cdn')
        print(f"   ✅ Regresyon grafiği '{regression_html}' olarak kaydedildi")

        # 3M odak grafiği: 10Y sapma temelli, yalnız 3 aylık değişim penceresi.
        # (usdtry_regression_3m.html'in güncel karşılığı — eski dosya repo öncesi
        # dönemden kalan 10Y temelli üç panelli grafikti, artık tek panelli
        # 3M odak grafiği olarak yeniden üretiliyor.)
        if ma_type == '10Y':
            print(f"\n📈 3M odaklı regresyon grafiği oluşturuluyor (10Y sapma temelli)...")
            fig_reg_3m, _, reg_stats_3m = create_change_regression_plot(df, ma_type, periods=[3])
            regression_3m_html = os.path.join(SCRIPT_DIR, "usdtry_regression_3m.html")
            fig_reg_3m.write_html(regression_3m_html, include_plotlyjs='cdn')
            s3 = reg_stats_3m[0]
            print(f"   3M: R²={s3['r2']:.4f}, r={s3['corr']:.4f}, eğim={s3['slope']:.3f}, σ={s3['rse']:.2f}%, N={s3['n']}")
            print(f"   ✅ 3M regresyon grafiği '{regression_3m_html}' olarak kaydedildi")

    # Tarayıcıda aç (TTO_TARAYICI_ACMA=1 ile bastırılabilir; otomasyon için)
    if not os.environ.get("TTO_TARAYICI_ACMA"):
        try:
            import webbrowser
            for ma in ['10y', '5y']:
                webbrowser.open('file://' + os.path.join(SCRIPT_DIR, f'usdtry_reer_analysis_{ma}.html'))
                webbrowser.open('file://' + os.path.join(SCRIPT_DIR, f'usdtry_regression_{ma}.html'))
            print("   🌐 Tüm grafikler tarayıcıda açılıyor...")
        except Exception as e:
            print(f"   ⚠️ Tarayıcı açılamadı: {e}")

    # Veriyi kaydet
    output_csv = os.path.join(SCRIPT_DIR, "usdtry_reer_data.csv")
    df.to_csv(output_csv, index=False)
    print(f"   ✅ Veri '{output_csv}' olarak kaydedildi")

    # Korelasyon tablosunu kaydet
    corr_df.to_csv(os.path.join(SCRIPT_DIR, "correlation_analysis.csv"), index=False)
    print(f"   ✅ Korelasyon analizi 'correlation_analysis.csv' olarak kaydedildi")
    
    return df, corr_df, band_df, fig


if __name__ == "__main__":
    df, corr_df, band_df, fig = main()

