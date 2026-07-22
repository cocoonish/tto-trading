"""
Türkiye Reel Efektif Döviz Kuru Analizi
- %70 PPI (Yi-ÜFE) + %30 CPI (TÜFE) bazlı ağırlıklı REDK
- 10 yıllık hareketli ortalamadan % sapma hesaplama
- Plotly ile interaktif görselleştirme
"""

import os
from datetime import date
from urllib.parse import urlencode

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================
# PARAMETRİK DEĞİŞKENLER (Kolay değiştirilebilir)
# ============================================

# Tüm yollar script klasörüne göre — hangi dizinden çalıştırılırsa çalıştırılsın bulunur
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dosya yolları (EVDS erişilemezse kullanılan YEDEK kaynak)
CPI_FILE = os.path.join(SCRIPT_DIR, "TUFE.xlsx")  # CPI bazlı REDK dosyası
PPI_FILE = os.path.join(SCRIPT_DIR, "Yi-UFE.xlsx")  # PPI bazlı REDK dosyası

# ============================================
# EVDS (TCMB) — BİRİNCİL VERİ KAYNAĞI
# ============================================
# Seri kodları EVDS kategori 2504 (REEL EFEKTİF DÖVİZ KURLARI) altındaki
# veri gruplarından doğrulandı:
#   bie_rktufey → TP.RK.T1.Y  "TÜFE Bazlı Reel Efektif Döviz Kuru (2025=100)"
#   bie_rkufey  → TP.RK.U01.Y "Yİ-ÜFE Bazlı Reel Efektif Döviz Kuru (2025=100)"
# Her ikisi de 01-1994'ten itibaren aylık. Elle indirilen TUFE.xlsx / Yi-UFE.xlsx
# ile aynı serilerdir (2026-02 için fark 0,01 puan); Excel yolu yedek olarak durur.
EVDS_KEY = os.environ.get("TTO_EVDS_KEY", "5ILfFTTp8n")
EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
EVDS_CPI_SERIES = "TP.RK.T1.Y"    # TÜFE bazlı REDK
EVDS_PPI_SERIES = "TP.RK.U01.Y"   # Yİ-ÜFE bazlı REDK
EVDS_START = "01-01-1994"

# Veri kaynağı seçimi: "evds" (varsayılan) | "excel"
VERI_KAYNAGI = os.environ.get("TTO_REDK_KAYNAK", "evds").strip().lower()

# Ağırlıklar (toplam 1.0 olmalı)
PPI_WEIGHT = 0.30  # PPI (Yi-ÜFE) ağırlığı
CPI_WEIGHT = 0.70  # CPI (TÜFE) ağırlığı

# Hareketli ortalama pencereleri (ay cinsinden)
MA_WINDOW_10Y = 120  # 10 yıllık hareketli ortalama
MA_WINDOW_5Y = 60    # 5 yıllık hareketli ortalama

# Çıktı dosyası
OUTPUT_HTML = os.path.join(SCRIPT_DIR, "reer_analysis.html")

# Ev paleti (site/src/styles/global.css ile uyumlu)
TEAL = "#1d5c5c"       # birincil seri
BORDO = "#8e1f2f"      # ikincil / pozitif sapma (pahalı TL)
ALTIN = "#9a7327"      # vurgu
MUREKKEP = "#211b12"   # nötr çizgi
BORDO_KENAR = "rgba(142, 31, 47, 0.8)"
BORDO_DOLGU = "rgba(142, 31, 47, 0.3)"
TEAL_KENAR = "rgba(29, 92, 92, 0.8)"
TEAL_DOLGU = "rgba(29, 92, 92, 0.3)"

# ============================================
# VERİ YÜKLEME VE İŞLEME
# ============================================

def fetch_evds_series(series_code, start=EVDS_START, end=None):
    """EVDS'ten tek bir aylık seriyi çek → pd.Series (index: ay başı Timestamp).

    USDTRYDeval/usdtry_deval_plotly.py içindeki fetch_evds ile aynı kalıp;
    aylık seriler 'YYYY-M' formatında Tarih döndürdüğü için ay başına çevrilir.
    """
    import requests  # yalnız EVDS yolunda gerekli — Excel yolu bağımsız kalsın

    if end is None:
        end = date.today().strftime("%d-%m-%Y")
    params = {
        "series": series_code,
        "startDate": start,
        "endDate": end,
        "type": "json",
    }
    url = f"{EVDS_BASE}/{urlencode(params)}"
    r = requests.get(url, headers={"key": EVDS_KEY}, timeout=60)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError(f"EVDS boş yanıt: {series_code}")

    df = pd.DataFrame(items)
    col = series_code.replace(".", "_")
    if col not in df.columns:
        raise RuntimeError(f"EVDS yanıtında '{col}' sütunu yok: {list(df.columns)}")

    raw = df["Tarih"].astype(str)
    if raw.iloc[0].count("-") == 2 and len(raw.iloc[0].split("-")[0]) == 2:
        df["Tarih"] = pd.to_datetime(raw, format="%d-%m-%Y")
    else:  # aylık seri: 'YYYY-M' → ayın ilk günü
        df["Tarih"] = pd.to_datetime(raw + "-01", format="%Y-%m-%d")

    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[col]).sort_values("Tarih")
    return df.set_index("Tarih")[col]


def load_data_evds():
    """TCMB EVDS API'sinden TÜFE ve Yi-ÜFE bazlı REDK serilerini çek."""
    cpi = fetch_evds_series(EVDS_CPI_SERIES)
    ppi = fetch_evds_series(EVDS_PPI_SERIES)
    df = pd.DataFrame({"CPI_REER": cpi, "PPI_REER": ppi}).dropna()
    df = df.rename_axis("Dönem").reset_index().sort_values("Dönem").reset_index(drop=True)
    if df.empty:
        raise RuntimeError("EVDS'ten ortak tarihli REDK verisi gelmedi")
    return df[["Dönem", "CPI_REER", "PPI_REER"]]


def load_data_excel():
    """Excel dosyalarından verileri yükle ve birleştir (EVDS yedeği)"""
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


def load_data():
    """REDK ham serilerini getir: önce EVDS, hata olursa Excel yedeği.

    TTO_REDK_KAYNAK=excel ile doğrudan Excel yoluna zorlanabilir.
    Dönen sütunlar: Dönem, CPI_REER, PPI_REER.
    """
    if VERI_KAYNAGI != "excel":
        try:
            df = load_data_evds()
            print(f"   📡 Kaynak: TCMB EVDS ({EVDS_CPI_SERIES} + {EVDS_PPI_SERIES})")
            return df
        except Exception as e:
            print(f"   ⚠️ EVDS'ten çekilemedi ({type(e).__name__}: {e}) — Excel yedeğine düşülüyor")
    else:
        print("   📄 Kaynak: Excel (TTO_REDK_KAYNAK=excel)")
    df = load_data_excel()
    print(f"   📄 Kaynak: yerel Excel ({os.path.basename(CPI_FILE)}, {os.path.basename(PPI_FILE)})")
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
        vertical_spacing=0.05,
        row_heights=[0.24, 0.19, 0.19, 0.19, 0.19],
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
            line=dict(color=TEAL, width=2),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>REDK:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['MA_10Y'],
            name='10Y MA',
            line=dict(color=BORDO, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>10Y MA:</b> %{y:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df_plot['Dönem'],
            y=df_plot['MA_5Y'],
            name='5Y MA',
            line=dict(color=ALTIN, width=1.5),
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
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
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
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
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
            line=dict(color=MUREKKEP, width=1.5),
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
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
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
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
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
            line=dict(color=MUREKKEP, width=1.5),
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
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
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
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
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
            line=dict(color=MUREKKEP, width=1.5),
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
            line=dict(color=BORDO_KENAR, width=0.5),
            fillcolor=BORDO_DOLGU,
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
            line=dict(color=TEAL_KENAR, width=0.5),
            fillcolor=TEAL_DOLGU,
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
            line=dict(color=MUREKKEP, width=1.5),
            hovertemplate='<b>Tarih:</b> %{x|%Y-%m}<br><b>CPI 10Y:</b> %{y:.2f}%<extra></extra>'
        ),
        row=5, col=1
    )
    
    # Sıfır çizgileri
    for row in [2, 3, 4, 5]:
        fig.add_hline(y=0, line_dash="solid", line_color="#90a4ae", line_width=1, row=row, col=1)
    
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
            x=0.01,
            xanchor="left",
            font=dict(size=16)
        ),
        # Lejant altta — üstte tutulursa ana başlık ve ilk panel başlığıyla çakışıyor
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.04,
            xanchor="left",
            x=0
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
    
    # HTML olarak kaydet (plotly.js CDN'den — dosya ~4.6MB yerine ~100KB olur)
    fig.write_html(OUTPUT_HTML, include_plotlyjs='cdn')
    print(f"   ✅ Grafik '{OUTPUT_HTML}' olarak kaydedildi")

    # Grafiği tarayıcıda aç (TTO_TARAYICI_ACMA=1 ile bastırılabilir; otomasyon için)
    if not os.environ.get("TTO_TARAYICI_ACMA"):
        try:
            import webbrowser
            webbrowser.open('file://' + os.path.realpath(OUTPUT_HTML))
            print(f"   🌐 Grafik tarayıcıda açılıyor...")
        except Exception as e:
            print(f"   ⚠️ Tarayıcı açılamadı: {e}")

    # İsteğe bağlı: Hesaplanmış veriyi CSV olarak kaydet
    output_csv = os.path.join(SCRIPT_DIR, "reer_analysis_data.csv")
    df.to_csv(output_csv, index=False)
    print(f"   ✅ Veri '{output_csv}' olarak kaydedildi")
    
    return df, fig


if __name__ == "__main__":
    df, fig = main()

