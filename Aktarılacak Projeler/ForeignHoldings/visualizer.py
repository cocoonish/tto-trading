"""
Grafik oluşturma modülü
Plotly ile interaktif grafikler
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

def create_cumulative_charts(df: pd.DataFrame, output_dir: str = "charts",
                            width: int = 1400, height: int = 700,
                            theme: str = "plotly_white", currency_unit: str = "M USD"):
    """
    Kümülatif grafikleri oluşturur
    DIBS ve Hisse bir eksende, Toplam ikincil eksende
    
    Args:
        df: Kümülatif veriler içeren DataFrame
        output_dir: Çıktı klasörü
        width: Grafik genişliği
        height: Grafik yüksekliği
        theme: Plotly tema
        currency_unit: Para birimi etiketi
    """
    # İlk değişim noktasından sonrasını al
    df_plot = df[df['Toplam_Cumulative'] != 0].copy()
    
    if df_plot.empty:
        print("   ⚠️  Kümülatif veri bulunamadı")
        return
    
    # Dual axis grafik oluştur
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Birincil eksen: DIBS ve Hisse
    fig.add_trace(
        go.Scatter(
            x=df_plot['Tarih'],
            y=df_plot['DIBS_Cumulative'],
            name='DIBS',
            mode='lines',
            line=dict(color='#1f77b4', width=2),
            hovertemplate='<b>DIBS</b><br>' +
                         'Tarih: %{x|%d-%m-%Y}<br>' +
                         f'Değer: %{{y:,.2f}} {currency_unit}<extra></extra>'
        ),
        secondary_y=False
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Tarih'],
            y=df_plot['Hisse_Cumulative'],
            name='Hisse',
            mode='lines',
            line=dict(color='#2ca02c', width=2),
            hovertemplate='<b>Hisse</b><br>' +
                         'Tarih: %{x|%d-%m-%Y}<br>' +
                         f'Değer: %{{y:,.2f}} {currency_unit}<extra></extra>'
        ),
        secondary_y=False
    )
    
    # İkincil eksen: Toplam
    fig.add_trace(
        go.Scatter(
            x=df_plot['Tarih'],
            y=df_plot['Toplam_Cumulative'],
            name='Toplam',
            mode='lines',
            line=dict(color='#d62728', width=2.5, dash='dash'),
            hovertemplate='<b>Toplam</b><br>' +
                         'Tarih: %{x|%d-%m-%Y}<br>' +
                         f'Değer: %{{y:,.2f}} {currency_unit}<extra></extra>'
        ),
        secondary_y=True
    )
    
    # Eksen değer aralıklarını hesapla
    y1_min = min(df_plot['DIBS_Cumulative'].min(), df_plot['Hisse_Cumulative'].min())
    y1_max = max(df_plot['DIBS_Cumulative'].max(), df_plot['Hisse_Cumulative'].max())
    y2_min = df_plot['Toplam_Cumulative'].min()
    y2_max = df_plot['Toplam_Cumulative'].max()
    
    # Y ekseni için grid aralığını hesapla (daha fazla grid çizgisi için)
    y1_range = y1_max - y1_min
    y1_dtick = y1_range / 20  # 20 major grid çizgisi için
    
    # X ekseni için tarih aralığını hesapla
    date_range = (df_plot['Tarih'].max() - df_plot['Tarih'].min()).days
    # Daha fazla tarih gösterimi için tick sayısını artır
    num_ticks = min(25, max(15, date_range // 30))  # Her ay veya daha sık
    
    # Eksen etiketleri ve grid ayarları
    fig.update_xaxes(
        title_text="Tarih",
        # Daha fazla tarih gösterimi için tick ayarları
        tickmode='auto',
        nticks=num_ticks,  # Daha fazla tick
        tickformat='%d-%m-%Y',
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.3)',
        showspikes=True
    )
    
    # Primary axis (DIBS ve Hisse) - daha fazla grid çizgisi
    fig.update_yaxes(
        title_text=f"DIBS ve Hisse ({currency_unit})",
        secondary_y=False,
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.3)',
        dtick=y1_dtick,  # Major grid aralığı
        # Daha fazla grid için range'i biraz genişlet
        range=[y1_min - y1_range * 0.05, y1_max + y1_range * 0.05]
    )
    
    # Secondary axis (Toplam) - Primary ile aynı grid çizgileri için
    # Secondary axis'in grid'ini kapat, primary'deki grid görünsün
    # Ancak değerleri primary ile uyumlu hale getir
    y2_range = y2_max - y2_min
    y2_dtick = y2_range / 20  # Aynı sayıda grid çizgisi
    
    fig.update_yaxes(
        title_text=f"Toplam ({currency_unit})",
        secondary_y=True,
        showgrid=False,  # Secondary axis grid'ini kapat (primary'deki görünsün)
        dtick=y2_dtick,
        range=[y2_min - y2_range * 0.05, y2_max + y2_range * 0.05]
    )
    
    # Layout ayarları
    fig.update_layout(
        title={
            'text': 'Yurtdışı Yerleşikler DIBS ve Hisse Senedi Kesin Alım-Satım - Kümülatif Toplamlar',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 16}
        },
        width=width,
        height=height,
        template=theme,
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Kaydet
    output_path = os.path.join(output_dir, "cumulative_chart.html")
    fig.write_html(output_path)
    print(f"      ✅ Kümülatif grafik kaydedildi: {output_path}")

def create_ytd_charts(df: pd.DataFrame, output_dir: str = "charts",
                     width: int = 1400, height: int = 700,
                     theme: str = "plotly_white", currency_unit: str = "M USD"):
    """
    YTD karşılaştırmalı grafikleri oluşturur
    Her yıl için ayrı grafik: Hisse, DIBS ve Toplam
    
    Args:
        df: YTD verileri içeren DataFrame
        output_dir: Çıktı klasörü
        width: Grafik genişliği
        height: Grafik yüksekliği
        theme: Plotly tema
        currency_unit: Para birimi etiketi
    """
    years = sorted(df['Year'].unique())
    
    if len(years) == 0:
        print("   ⚠️  YTD veri bulunamadı")
        return
    
    # Her kategori için ayrı grafik (Hisse, DIBS, Toplam)
    categories = [
        ('Hisse', 'Hisse_YTD', '#2ca02c'),
        ('DIBS', 'DIBS_YTD', '#1f77b4'),
        ('Toplam', 'Toplam_YTD', '#d62728')
    ]
    
    for category_name, column_name, color in categories:
        fig = go.Figure()
        
        # Her yıl için çizgi ekle (sadece veri olan yıllar)
        for year in years:
            year_data = df[df['Year'] == year].copy()
            year_data = year_data.sort_values('Week').reset_index(drop=True)
            
            if year_data.empty:
                continue
            
            # Yılın son değerini kontrol et - eğer tüm yıl sıfırsa dahil etme
            if len(year_data) > 0:
                last_value = year_data[column_name].iloc[-1]
                # Eğer yılın sonunda değer sıfırsa, bu yılı atla
                if last_value == 0 and year_data[column_name].abs().max() == 0:
                    continue
            
            fig.add_trace(
                go.Scatter(
                    x=year_data['Week'],
                    y=year_data[column_name],
                    name=str(year),
                    mode='lines+markers',
                    line=dict(width=2),
                    marker=dict(size=4),
                    hovertemplate=f'<b>{year}</b><br>' +
                                 'Hafta: %{x}<br>' +
                                 f'Değer: %{{y:,.2f}} {currency_unit}<extra></extra>'
                )
            )
        
        # Ay başlangıçlarını bul (her yıl için)
        # Tüm yılların verilerini birleştirerek ay başlangıç haftalarını belirle
        month_starts_by_year = {}  # {year: {month: week}}
        
        for year in years:
            year_data = df[df['Year'] == year].copy()
            if year_data.empty:
                continue
            
            # Tarih sütununu kullanarak ay başlangıçlarını bul
            year_data = year_data.sort_values('Tarih')
            year_data['Month'] = year_data['Tarih'].dt.month
            year_data['Day'] = year_data['Tarih'].dt.day
            
            # Her ayın ilk haftasını bul (ayın 1. gününe en yakın hafta)
            month_weeks = {}
            for month in range(1, 13):
                month_data = year_data[year_data['Month'] == month]
                if not month_data.empty:
                    # Ayın 1. gününe en yakın kaydı bul
                    # Önce 1. günü ara, yoksa en küçük günü al
                    first_day_data = month_data[month_data['Day'] == 1]
                    if first_day_data.empty:
                        # 1. gün yoksa, en küçük günü al (ayın başına en yakın)
                        first_day_data = month_data[month_data['Day'] == month_data['Day'].min()]
                    
                    if not first_day_data.empty:
                        # İlk günün haftasını al
                        month_weeks[month] = first_day_data.iloc[0]['Week']
            
            month_starts_by_year[year] = month_weeks
        
        # Y ekseni aralığını hesapla (ay çizgileri için)
        y_min = df[column_name].min()
        y_max = df[column_name].max()
        y_range = y_max - y_min
        
        # Tüm yıllar için ortak ay başlangıç haftalarını belirle
        # Her ay için ortalama hafta numarasını hesapla
        month_names = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                      'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
        
        if month_starts_by_year:
            # Her ay için tüm yıllardan hafta numaralarını topla
            month_week_lists = {month: [] for month in range(1, 13)}
            for year, month_weeks in month_starts_by_year.items():
                for month, week in month_weeks.items():
                    month_week_lists[month].append(week)
            
            # Her ay için ortalama hafta numarasını hesapla ve dikey çizgi ekle
            # Tüm aylar için çizgi ekle (veri olmasa bile)
            for month in range(1, 13):
                if month_week_lists[month]:
                    # Tüm yıllardan hafta numaralarını al
                    weeks = month_week_lists[month]
                    # ISO hafta numaraları 53'e kadar çıkabilir, bunları düzelt
                    # Eğer hafta 53 ise, muhtemelen yılın ilk haftası (1. hafta olmalı)
                    normalized_weeks = []
                    for w in weeks:
                        if w >= 53:
                            normalized_weeks.append(1)  # Yılın ilk haftası
                        else:
                            normalized_weeks.append(w)
                    
                    avg_week = sum(normalized_weeks) / len(normalized_weeks)
                    week_num = round(avg_week)
                    
                    # Hafta numarasını 1-52 aralığında tut
                    if week_num < 1:
                        week_num = 1
                    elif week_num > 52:
                        week_num = 52
                    
                    # Dikey çizgi ekle (ay başlangıcı)
                    fig.add_shape(
                        type="line",
                        x0=week_num,
                        x1=week_num,
                        y0=y_min - y_range * 0.05,
                        y1=y_max + y_range * 0.05,
                        line=dict(
                            color="rgba(128, 128, 128, 0.4)",
                            width=1,
                            dash="dot"
                        ),
                        layer="below"
                    )
                    
                    # Ay etiketi ekle (tüm aylar için)
                    fig.add_annotation(
                        x=week_num,
                        y=y_max + y_range * 0.02,
                        text=month_names[month-1],
                        showarrow=False,
                        font=dict(size=9, color="rgba(128, 128, 128, 0.7)"),
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        bordercolor="rgba(128, 128, 128, 0.3)",
                        borderwidth=1
                    )
                else:
                    # Veri yoksa bile, yaklaşık hafta numarasını hesapla
                    # Her ay yaklaşık 4.33 hafta (52/12)
                    estimated_week = round((month - 1) * 4.33 + 1)
                    if estimated_week > 52:
                        estimated_week = 52
                    
                    # Dikey çizgi ekle (tahmini ay başlangıcı)
                    fig.add_shape(
                        type="line",
                        x0=estimated_week,
                        x1=estimated_week,
                        y0=y_min - y_range * 0.05,
                        y1=y_max + y_range * 0.05,
                        line=dict(
                            color="rgba(128, 128, 128, 0.3)",
                            width=1,
                            dash="dot"
                        ),
                        layer="below"
                    )
                    
                    # Ay etiketi ekle
                    fig.add_annotation(
                        x=estimated_week,
                        y=y_max + y_range * 0.02,
                        text=month_names[month-1],
                        showarrow=False,
                        font=dict(size=9, color="rgba(128, 128, 128, 0.6)"),
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        bordercolor="rgba(128, 128, 128, 0.3)",
                        borderwidth=1
                    )
        
        # Y ekseni aralığını hesapla (grid çizgileri için)
        y_min = df[column_name].min()
        y_max = df[column_name].max()
        y_range = y_max - y_min
        y_dtick = y_range / 30  # 30 major grid çizgisi (daha sık)
        
        # Layout ayarları
        fig.update_layout(
            title={
                'text': f'YTD Karşılaştırması - {category_name} (Hafta Hafta)',
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 16}
            },
            xaxis_title='Hafta',
            yaxis_title=f'{category_name} ({currency_unit})',
            width=width,
            height=height,
            template=theme,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # X ve Y ekseni grid ayarları (daha fazla minör çizgi)
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128, 128, 128, 0.3)',
            minor=dict(
                showgrid=True,
                gridwidth=0.5,
                gridcolor='rgba(128, 128, 128, 0.15)',
                griddash='dot',
                nticks=4  # Her major tick arasında 4 minor tick
            )
        )
        
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128, 128, 128, 0.3)',
            dtick=y_dtick,  # Major grid aralığı
            minor=dict(
                showgrid=True,
                gridwidth=0.5,
                gridcolor='rgba(128, 128, 128, 0.15)',
                griddash='dot',
                nticks=4  # Her major tick arasında 4 minor tick
            ),
            range=[y_min - y_range * 0.05, y_max + y_range * 0.05]
        )
        
        # Kaydet
        output_path = os.path.join(output_dir, f"ytd_{category_name.lower()}.html")
        fig.write_html(output_path)
        print(f"      ✅ YTD {category_name} grafiği kaydedildi: {output_path}")

