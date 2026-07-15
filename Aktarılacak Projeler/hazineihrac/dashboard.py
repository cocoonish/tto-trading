#!/usr/bin/env python3
"""
Hazine İhraç Dashboard
=====================
Türk Hazinesi ihale verilerini interaktif olarak görüntüleyen Dash uygulaması.
Mevcut CSV verilerini okur ve http://127.0.0.1:8050 adresinde sunar.

Kullanım:
    python dashboard.py
"""

import os
import json
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, html, dcc, dash_table, callback, Input, Output, State
import dash_bootstrap_components as dbc
import yfinance as yf

# ============================================================
# VERİ YÜKLEME
# ============================================================

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

COLOR_MAP = {
    'Sabit Kuponlu Devlet Tahvili': '#1f77b4',
    'Hazine Bonosu': '#ff7f0e',
    "TÜFE'ye Endeksli Devlet Tahvili": '#2ca02c',
    "TLREF'e Endeksli Devlet Tahvili": '#d62728',
    'Değişken Faizli Devlet Tahvili': '#9467bd',
    'Kuponsuz Devlet Tahvili': '#8c564b',
}

SECURITY_ORDER = list(COLOR_MAP.keys())


def load_usdtry_rates():
    """yfinance'ten USD/TRY aylık kapanış kurlarını çek."""
    try:
        ticker = yf.Ticker("USDTRY=X")
        hist = ticker.history(period="max", interval="1mo")
        if hist.empty:
            # Fallback: günlük veriyle aylık resample
            hist = ticker.history(period="max", interval="1d")
            hist = hist.resample('ME').last()
        rates = hist['Close'].to_dict()
        # Key: Timestamp → "YYYY-MM" format
        monthly_rates = {}
        for dt, rate in rates.items():
            key = pd.Timestamp(dt).strftime('%Y-%m')
            monthly_rates[key] = float(rate)
        print(f"   → {len(monthly_rates)} aylık USD/TRY kuru yüklendi")
        return monthly_rates
    except Exception as e:
        print(f"   ⚠ USD/TRY kuru yüklenemedi: {e}")
        return {}


def load_strategy_history():
    """Strateji tarihsel cache'ini oku."""
    cache_path = os.path.join(DATA_DIR, '.strategy_history.json')
    try:
        if os.path.exists(cache_path):
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def load_data():
    """CSV dosyalarını yükle ve türet."""
    # Ana ihale verileri
    csv_path = os.path.join(DATA_DIR, 'hazine_ihale_verileri.csv')
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    df['İhale Tarihi'] = pd.to_datetime(df['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
    df = df.dropna(subset=['İhale Tarihi'])
    df = df.sort_values('İhale Tarihi', ascending=False).reset_index(drop=True)

    # Türetilmiş kolonlar
    df['Bid-to-Cover'] = np.where(
        df['Toplam(Gerçekleşme)'] > 0,
        df['Toplam(Teklif)'] / df['Toplam(Gerçekleşme)'],
        np.nan
    )
    df['Yıl'] = df['İhale Tarihi'].dt.year
    df['Ay'] = df['İhale Tarihi'].dt.month
    df['Yıl-Ay'] = df['İhale Tarihi'].dt.to_period('M').astype(str)
    df['Çeyrek'] = df['İhale Tarihi'].dt.to_period('Q').astype(str)

    # USD dönüşümü
    usd_rates = load_usdtry_rates()
    if usd_rates:
        df['USD_Kur'] = df['Yıl-Ay'].map(usd_rates)
        df['Toplam(Gerçekleşme) USD (M)'] = np.where(
            df['USD_Kur'] > 0,
            df['Toplam(Gerçekleşme)'] / df['USD_Kur'],
            np.nan
        )
    else:
        df['USD_Kur'] = np.nan
        df['Toplam(Gerçekleşme) USD (M)'] = np.nan

    # Vade analizi
    vade_path = os.path.join(DATA_DIR, 'hazine_vade_analizi.csv')
    df_vade = pd.read_csv(vade_path, encoding='utf-8-sig')
    df_vade['Tarih'] = pd.to_datetime(df_vade['Tarih'], errors='coerce')

    # Strateji hedef/gerçekleşme
    hedef_path = os.path.join(DATA_DIR, 'hazine_hedef_gerceklesme.csv')
    df_hedef = pd.read_csv(hedef_path, encoding='utf-8-sig')
    # Boş satırları temizle
    df_hedef = df_hedef.dropna(subset=['Ay-Yıl'])
    df_hedef = df_hedef[df_hedef['Ay-Yıl'].str.strip() != '']

    # Strateji tarihsel cache
    strategy_hist = load_strategy_history()

    # Planlanan (önümüzdeki) ihraçlar + tahminler — varsa
    planned_path = os.path.join(DATA_DIR, 'hazine_planlanan_ihaleler.csv')
    if os.path.exists(planned_path):
        df_planned = pd.read_csv(planned_path, encoding='utf-8-sig')
        for c in ['Tahmini Bid-to-Cover', 'Tahmini Gerçekleşme (Milyon TL)',
                  'Tahmini Teklif (Milyon TL)']:
            if c in df_planned.columns:
                df_planned[c] = pd.to_numeric(df_planned[c], errors='coerce')
        if 'İhale Tarihi' in df_planned.columns:
            df_planned['_d'] = pd.to_datetime(df_planned['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
            df_planned = df_planned.sort_values('_d').reset_index(drop=True)
    else:
        df_planned = pd.DataFrame()

    # Backtest: geçmiş ihalelerde tahmin vs gerçek — varsa
    bt_path = os.path.join(DATA_DIR, 'hazine_tahmin_dogrulama.csv')
    if os.path.exists(bt_path):
        df_backtest = pd.read_csv(bt_path, encoding='utf-8-sig')
        num_cols = [c for c in df_backtest.columns if 'Milyon TL' in c or 'Bid-to-Cover' in c or 'Sapma' in c]
        for c in num_cols:
            df_backtest[c] = pd.to_numeric(df_backtest[c], errors='coerce')
        df_backtest['_d'] = pd.to_datetime(df_backtest['İhale Tarihi'], format='%d.%m.%Y', errors='coerce')
        df_backtest = df_backtest.dropna(subset=['_d']).sort_values('_d').reset_index(drop=True)
    else:
        df_backtest = pd.DataFrame()

    return df, df_vade, df_hedef, strategy_hist, df_planned, df_backtest


df_main, df_vade, df_hedef, strategy_history, df_planned, df_backtest = load_data()


# ============================================================
# YARDIMCI FONKSİYONLAR
# ============================================================

def format_milyar(val):
    """Milyon TL → Milyar TL olarak formatla."""
    if pd.isna(val):
        return "-"
    return f"{val / 1000:,.1f}"


def format_number(val, decimals=1):
    if pd.isna(val):
        return "-"
    return f"{val:,.{decimals}f}"


def filter_df(df, start_date, end_date, security_types, isin_search):
    """Global filtreleri uygula."""
    dff = df.copy()
    if start_date:
        dff = dff[dff['İhale Tarihi'] >= pd.to_datetime(start_date)]
    if end_date:
        dff = dff[dff['İhale Tarihi'] <= pd.to_datetime(end_date)]
    if security_types:
        dff = dff[dff['Senet Tanımı'].isin(security_types)]
    if isin_search:
        dff = dff[dff['ISIN'].str.contains(isin_search.upper(), na=False)]
    return dff


def make_kpi_card(title, value, color="primary"):
    return dbc.Card(
        dbc.CardBody([
            html.P(title, className="card-title mb-1", style={"fontSize": "0.8rem", "color": "#6c757d"}),
            html.H4(value, className="card-text mb-0", style={"fontWeight": "bold"}),
        ]),
        className="shadow-sm",
        style={"borderLeft": f"4px solid var(--bs-{color})"},
    )


def empty_fig(msg="Veri bulunamadı"):
    fig = go.Figure()
    fig.add_annotation(text=msg, xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font_size=16)
    fig.update_layout(xaxis_visible=False, yaxis_visible=False, template="plotly_white", height=300, margin=dict(t=30, b=30, l=30, r=30))
    return fig


# ============================================================
# DASH UYGULAMASI
# ============================================================

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="Hazine İhraç Paneli",
    suppress_callback_exceptions=True,
)

# -- Senet tipi seçenekleri
senet_options = [{"label": s, "value": s} for s in df_main['Senet Tanımı'].unique() if pd.notna(s)]

# ============================================================
# LAYOUT
# ============================================================

app.layout = dbc.Container([
    # Başlık
    dbc.Row([
        dbc.Col(html.H3("🏛️ Hazine İhraç Paneli", className="mb-0 mt-3"), width="auto"),
        dbc.Col(html.Small(
            f"Son güncelleme: {df_main['İhale Tarihi'].max().strftime('%d.%m.%Y')} | {len(df_main)} ihale",
            className="text-muted mt-4"
        ), width="auto"),
    ], className="mb-3"),

    # KPI Kartları
    dbc.Row(id="kpi-row", className="mb-3 g-2"),

    # Filtreler
    dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Tarih Aralığı", className="fw-bold small"),
                    dcc.DatePickerRange(
                        id='date-picker',
                        min_date_allowed=df_main['İhale Tarihi'].min(),
                        max_date_allowed=df_main['İhale Tarihi'].max(),
                        display_format='DD.MM.YYYY',
                        start_date_placeholder_text="Başlangıç",
                        end_date_placeholder_text="Bitiş",
                        className="d-block",
                    ),
                ], md=4),
                dbc.Col([
                    html.Label("Senet Tipi", className="fw-bold small"),
                    dcc.Dropdown(
                        id='security-dropdown',
                        options=senet_options,
                        multi=True,
                        placeholder="Tüm tipler",
                    ),
                ], md=5),
                dbc.Col([
                    html.Label("ISIN Ara", className="fw-bold small"),
                    dbc.Input(id='isin-input', type='text', placeholder="örn: TRT08"),
                ], md=3),
            ], className="g-2"),
        ),
        className="mb-3 shadow-sm",
    ),

    # Tablar
    dbc.Tabs([
        dbc.Tab(label="Genel Bakış", tab_id="tab-overview"),
        dbc.Tab(label="İhale Detayları", tab_id="tab-detail"),
        dbc.Tab(label="Strateji Analizi", tab_id="tab-strategy"),
        dbc.Tab(label="Vade Analizi", tab_id="tab-maturity"),
        dbc.Tab(label="Faiz & Fiyat", tab_id="tab-rates"),
        dbc.Tab(label="Planlanan İhraçlar", tab_id="tab-planned"),
        dbc.Tab(label="Tahmin Doğrulama", tab_id="tab-backtest"),
    ], id="tabs", active_tab="tab-overview", className="mb-3"),

    # Tab içeriği (yüklenirken spinner göster)
    dcc.Loading(html.Div(id="tab-content"), type="default", color="#2c3e50"),

], fluid=True, className="pb-4")


# ============================================================
# CALLBACKS
# ============================================================

# --- KPI Kartları ---
@callback(
    Output("kpi-row", "children"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
    Input("security-dropdown", "value"),
    Input("isin-input", "value"),
)
def update_kpis(start, end, types, isin):
    dff = filter_df(df_main, start, end, types, isin)

    if dff.empty:
        return [dbc.Col(make_kpi_card(t, "-")) for t in
                ["Toplam İhraç", "Ort. Vade", "Son Faiz", "İhale Sayısı", "Kabul Oranı", "Gerçekleşme"]]

    total_issuance = dff['Toplam(Gerçekleşme)'].sum()
    wam_num = (dff['Vade (Yıl)'] * dff['Toplam(Gerçekleşme)']).sum()
    wam_den = dff['Toplam(Gerçekleşme)'].sum()
    wam = wam_num / wam_den if wam_den > 0 else 0

    latest = dff.sort_values('İhale Tarihi', ascending=False).iloc[0]
    latest_rate = latest.get('Ortalama Yıllık Bileşik(Gerçekleşme)', np.nan)

    avg_accept = dff['İhale Kabul Oranı (%)'].mean()

    # Strateji gerçekleşme
    hedef_total = df_hedef['Hedef Borçlanma (Milyar TL)'].sum()
    gercek_total = df_hedef['Gerçekleşen Borçlanma (Milyar TL)'].sum()
    strat_rate = (gercek_total / hedef_total * 100) if hedef_total > 0 else 0

    cards = [
        dbc.Col(make_kpi_card("Toplam İhraç", f"{format_milyar(total_issuance)} Milyar TL", "primary"), md=2),
        dbc.Col(make_kpi_card("Ağırlıklı Ort. Vade", f"{wam:.2f} Yıl", "success"), md=2),
        dbc.Col(make_kpi_card("Son Bileşik Faiz", f"%{format_number(latest_rate, 2)}", "info"), md=2),
        dbc.Col(make_kpi_card("İhale Sayısı", f"{len(dff)}", "warning"), md=2),
        dbc.Col(make_kpi_card("Ort. Kabul Oranı", f"%{format_number(avg_accept, 1)}", "danger"), md=2),
        dbc.Col(make_kpi_card("Strateji Gerçekleşme", f"%{format_number(strat_rate, 1)}", "secondary"), md=2),
    ]
    return cards


# --- Tab İçerik Yönlendirme ---
@callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
    Input("security-dropdown", "value"),
    Input("isin-input", "value"),
)
def render_tab(tab, start, end, types, isin):
    dff = filter_df(df_main, start, end, types, isin)

    if tab == "tab-overview":
        return render_overview(dff)
    elif tab == "tab-detail":
        return render_detail(dff)
    elif tab == "tab-strategy":
        return render_strategy(dff)
    elif tab == "tab-maturity":
        return render_maturity(dff, start, end)
    elif tab == "tab-rates":
        return render_rates(dff)
    elif tab == "tab-planned":
        return render_planned()
    elif tab == "tab-backtest":
        return render_backtest(start, end)
    return html.Div("Sekme bulunamadı")


# ============================================================
# TAB 1: GENEL BAKIŞ
# ============================================================

def render_overview(dff):
    if dff.empty:
        return html.Div(dcc.Graph(figure=empty_fig()))

    # Aylık ihraç hacmi (stacked bar)
    monthly = dff.groupby(['Yıl-Ay', 'Senet Tanımı'])['Toplam(Gerçekleşme)'].sum().reset_index()
    monthly['Milyar TL'] = monthly['Toplam(Gerçekleşme)'] / 1000

    fig1 = px.bar(
        monthly, x='Yıl-Ay', y='Milyar TL', color='Senet Tanımı',
        color_discrete_map=COLOR_MAP,
        title="Aylık İhraç Hacmi (Milyar TL)",
        category_orders={"Senet Tanımı": SECURITY_ORDER},
    )
    fig1.update_layout(
        template="plotly_white", height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        xaxis_title="", yaxis_title="Milyar TL",
        xaxis=dict(tickangle=-45, dtick=3),
        margin=dict(t=40, b=80),
    )

    # Senet tipi dağılımı (donut)
    type_dist = dff.groupby('Senet Tanımı')['Toplam(Gerçekleşme)'].sum().reset_index()
    fig2 = px.pie(
        type_dist, values='Toplam(Gerçekleşme)', names='Senet Tanımı',
        hole=0.4, title="Senet Tipi Dağılımı",
        color='Senet Tanımı', color_discrete_map=COLOR_MAP,
    )
    fig2.update_layout(template="plotly_white", height=400, margin=dict(t=40, b=20),
                       legend=dict(orientation="h", yanchor="bottom", y=-0.3))

    # Aylık ihraç hacmi USD
    has_usd = dff['Toplam(Gerçekleşme) USD (M)'].notna().any()
    fig_usd = go.Figure()
    if has_usd:
        monthly_usd = dff.groupby('Yıl-Ay').agg({
            'Toplam(Gerçekleşme) USD (M)': 'sum',
            'USD_Kur': 'mean'
        }).reset_index()
        monthly_usd['Milyar USD'] = monthly_usd['Toplam(Gerçekleşme) USD (M)'] / 1000
        monthly_usd = monthly_usd.sort_values('Yıl-Ay')

        fig_usd = make_subplots(specs=[[{"secondary_y": True}]])
        fig_usd.add_trace(
            go.Bar(name="İhraç (Milyar USD)", x=monthly_usd['Yıl-Ay'], y=monthly_usd['Milyar USD'],
                   marker_color='#27ae60', opacity=0.7),
            secondary_y=False,
        )
        fig_usd.add_trace(
            go.Scatter(name="USD/TRY Kuru", x=monthly_usd['Yıl-Ay'], y=monthly_usd['USD_Kur'],
                       mode='lines+markers', line=dict(color='#e74c3c', width=2),
                       marker=dict(size=4)),
            secondary_y=True,
        )
        fig_usd.update_layout(
            title="Aylık İhraç Hacmi (Milyar USD) & USD/TRY Kuru",
            template="plotly_white", height=400,
            legend=dict(orientation="h", yanchor="bottom", y=-0.3),
            xaxis=dict(tickangle=-45, dtick=3),
            margin=dict(t=40, b=80),
        )
        fig_usd.update_yaxes(title_text="Milyar USD", secondary_y=False)
        fig_usd.update_yaxes(title_text="USD/TRY", secondary_y=True)
    else:
        fig_usd = empty_fig("USD kuru verisi yüklenemedi")

    # Çeyreklik trend
    quarterly = dff.groupby('Çeyrek')['Toplam(Gerçekleşme)'].sum().reset_index()
    quarterly['Milyar TL'] = quarterly['Toplam(Gerçekleşme)'] / 1000
    fig3 = px.line(
        quarterly, x='Çeyrek', y='Milyar TL',
        title="Çeyreklik İhraç Trendi",
        markers=True,
    )
    fig3.update_layout(template="plotly_white", height=350, xaxis_title="", yaxis_title="Milyar TL",
                       xaxis=dict(tickangle=-45, dtick=2), margin=dict(t=40, b=60))

    # Aylık ihale sayısı
    auction_count = dff.groupby('Yıl-Ay').size().reset_index(name='Sayı')
    fig4 = px.bar(
        auction_count, x='Yıl-Ay', y='Sayı',
        title="Aylık İhale Sayısı",
    )
    fig4.update_layout(template="plotly_white", height=350, xaxis_title="", yaxis_title="İhale Sayısı",
                       xaxis=dict(tickangle=-45, dtick=3), margin=dict(t=40, b=60))
    fig4.update_traces(marker_color='#1f77b4')

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), md=7),
            dbc.Col(dcc.Graph(figure=fig2), md=5),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig_usd), md=12),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig3), md=6),
            dbc.Col(dcc.Graph(figure=fig4), md=6),
        ]),
    ])


# ============================================================
# TAB 2: İHALE DETAYLARI
# ============================================================

def render_detail(dff):
    display_cols = [
        'ISIN', 'Senet Tanımı', 'İhale Tarihi', 'Vade (Yıl)',
        'Toplam(Teklif)', 'Toplam(Gerçekleşme)',
        'Ortalama Yıllık Bileşik(Gerçekleşme)', 'İhale Kabul Oranı (%)', 'Bid-to-Cover'
    ]
    col_names = {
        'ISIN': 'ISIN',
        'Senet Tanımı': 'Senet Tipi',
        'İhale Tarihi': 'Tarih',
        'Vade (Yıl)': 'Vade (Yıl)',
        'Toplam(Teklif)': 'Teklif (M TL)',
        'Toplam(Gerçekleşme)': 'Gerçekleşme (M TL)',
        'Ortalama Yıllık Bileşik(Gerçekleşme)': 'Bileşik Faiz (%)',
        'İhale Kabul Oranı (%)': 'Kabul Oranı (%)',
        'Bid-to-Cover': 'Bid/Cover',
    }

    table_df = dff[display_cols].copy()
    table_df['İhale Tarihi'] = table_df['İhale Tarihi'].dt.strftime('%d.%m.%Y')
    table_df = table_df.round(2)

    columns = [
        {"name": col_names.get(c, c), "id": c, "type": "numeric" if c not in ['ISIN', 'Senet Tanımı', 'İhale Tarihi'] else "text"}
        for c in display_cols
    ]

    return html.Div([
        dash_table.DataTable(
            id='detail-table',
            data=table_df.to_dict('records'),
            columns=columns,
            page_size=20,
            sort_action='native',
            filter_action='native',
            export_format='csv',
            style_table={'overflowX': 'auto'},
            style_header={
                'backgroundColor': '#2c3e50',
                'color': 'white',
                'fontWeight': 'bold',
                'fontSize': '0.85rem',
            },
            style_cell={
                'textAlign': 'left',
                'padding': '8px',
                'fontSize': '0.85rem',
                'minWidth': '80px',
            },
            style_data_conditional=[
                {
                    'if': {'filter_query': '{İhale Kabul Oranı (%)} < 30', 'column_id': 'İhale Kabul Oranı (%)'},
                    'backgroundColor': '#ffdddd',
                    'color': '#c0392b',
                    'fontWeight': 'bold',
                },
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': '#f8f9fa',
                },
            ],
        ),
        html.Small(f"Toplam {len(table_df)} ihale gösteriliyor.", className="text-muted mt-2 d-block"),
    ])


# ============================================================
# TAB 3: STRATEJİ ANALİZİ
# ============================================================

def _build_full_strategy_comparison(dff):
    """Tarihsel strateji cache + CSV'den tam hedef/gerçekleşme tablosu oluştur."""
    TR_MONTHS = {
        'Ocak': 1, 'Şubat': 2, 'Mart': 3, 'Nisan': 4, 'Mayıs': 5, 'Haziran': 6,
        'Temmuz': 7, 'Ağustos': 8, 'Eylül': 9, 'Ekim': 10, 'Kasım': 11, 'Aralık': 12,
    }
    EN_TO_TR = {
        'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
        'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
        'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık',
    }

    # 1. Strateji tarihsel cache'den hedefler (yeni format: history array)
    targets = {}
    sources = {}
    for month_key, info in strategy_history.items():
        if isinstance(info, dict):
            targets[month_key] = info.get("target", 0)
            sources[month_key] = info.get("source", "")
        else:
            targets[month_key] = float(info)
            sources[month_key] = ""

    # 2. CSV'deki hedeflerle güncelle (daha güncel olabilir)
    for _, row in df_hedef.iterrows():
        key = row['Ay-Yıl']
        if pd.notna(key) and str(key).strip():
            targets[key] = row['Hedef Borçlanma (Milyar TL)']

    # 3. Gerçekleşen verileri hesapla (tüm ihale verisinden)
    monthly_realized = {}
    for _, row in dff.iterrows():
        dt = row['İhale Tarihi']
        en_month = dt.strftime('%B')
        tr_month = EN_TO_TR.get(en_month, en_month)
        key = f"{tr_month} {dt.year}"
        total = row.get('Toplam(Gerçekleşme)', 0)
        if pd.notna(total) and total > 0:
            monthly_realized[key] = monthly_realized.get(key, 0) + total

    # 4. Birleştir
    rows = []
    for month_key in sorted(targets.keys(), key=lambda k: _parse_month_key(k, TR_MONTHS)):
        target = targets[month_key]
        realized = monthly_realized.get(month_key, 0) / 1000  # Milyon → Milyar
        source = sources.get(month_key, "")
        rows.append({
            'Ay-Yıl': month_key,
            'Hedef Borçlanma (Milyar TL)': target,
            'Gerçekleşen Borçlanma (Milyar TL)': round(realized, 2),
            'Fark (Milyar TL)': round(realized - target, 2),
            'Gerçekleşme Oranı (%)': round((realized / target * 100) if target > 0 else 0, 1),
            'Kaynak': source,
        })

    return pd.DataFrame(rows) if rows else pd.DataFrame()


def _parse_month_key(key, tr_months):
    """'Ocak 2026' → sortable tuple (2026, 1)"""
    parts = key.split()
    if len(parts) == 2:
        month_num = tr_months.get(parts[0], 0)
        try:
            return (int(parts[1]), month_num)
        except ValueError:
            pass
    return (0, 0)


def render_strategy(dff):
    # Tam tarihsel karşılaştırma tablosu oluştur
    full_comparison = _build_full_strategy_comparison(dff)

    if full_comparison.empty and df_hedef.empty:
        return html.Div(dcc.Graph(figure=empty_fig("Strateji verisi bulunamadı")))

    hedef = full_comparison if not full_comparison.empty else df_hedef.copy()

    # KPI satırı
    total_hedef = hedef['Hedef Borçlanma (Milyar TL)'].sum()
    total_gercek = hedef['Gerçekleşen Borçlanma (Milyar TL)'].sum()
    rate = (total_gercek / total_hedef * 100) if total_hedef > 0 else 0

    kpi_row = dbc.Row([
        dbc.Col(make_kpi_card("Toplam Hedef", f"{total_hedef:.1f} Milyar TL", "primary"), md=4),
        dbc.Col(make_kpi_card("Toplam Gerçekleşen", f"{total_gercek:.1f} Milyar TL", "success"), md=4),
        dbc.Col(make_kpi_card("Gerçekleşme Oranı", f"%{rate:.1f}", "info"), md=4),
    ], className="mb-3 g-2")

    # Grouped bar + achievement line
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    fig1.add_trace(
        go.Bar(name="Hedef", x=hedef['Ay-Yıl'], y=hedef['Hedef Borçlanma (Milyar TL)'],
               marker_color='#3498db', opacity=0.8),
        secondary_y=False,
    )
    fig1.add_trace(
        go.Bar(name="Gerçekleşen", x=hedef['Ay-Yıl'], y=hedef['Gerçekleşen Borçlanma (Milyar TL)'],
               marker_color='#2ecc71', opacity=0.8),
        secondary_y=False,
    )
    fig1.add_trace(
        go.Scatter(name="Gerçekleşme Oranı (%)", x=hedef['Ay-Yıl'], y=hedef['Gerçekleşme Oranı (%)'],
                   mode='lines+markers', line=dict(color='#e74c3c', width=3),
                   marker=dict(size=10)),
        secondary_y=True,
    )
    fig1.update_layout(
        title="Hedef vs Gerçekleşme (Tüm Dönemler)", template="plotly_white", height=400, barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        margin=dict(t=40, b=60),
    )
    fig1.update_yaxes(title_text="Milyar TL", secondary_y=False)
    fig1.update_yaxes(title_text="Gerçekleşme Oranı (%)", secondary_y=True)

    # Kümülatif grafik
    hedef_cum = hedef.copy()
    hedef_cum['Kümülatif Hedef'] = hedef_cum['Hedef Borçlanma (Milyar TL)'].cumsum()
    hedef_cum['Kümülatif Gerçekleşen'] = hedef_cum['Gerçekleşen Borçlanma (Milyar TL)'].cumsum()

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        name="Kümülatif Hedef", x=hedef_cum['Ay-Yıl'], y=hedef_cum['Kümülatif Hedef'],
        fill='tozeroy', fillcolor='rgba(52,152,219,0.2)', line=dict(color='#3498db', width=2),
    ))
    fig2.add_trace(go.Scatter(
        name="Kümülatif Gerçekleşen", x=hedef_cum['Ay-Yıl'], y=hedef_cum['Kümülatif Gerçekleşen'],
        fill='tozeroy', fillcolor='rgba(46,204,113,0.2)', line=dict(color='#2ecc71', width=2),
    ))
    fig2.update_layout(
        title="Kümülatif Gerçekleşme", template="plotly_white", height=350,
        yaxis_title="Milyar TL",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        margin=dict(t=40, b=60),
    )

    # Strateji detay tablosu
    table_cols = ['Ay-Yıl', 'Hedef Borçlanma (Milyar TL)', 'Gerçekleşen Borçlanma (Milyar TL)',
                  'Fark (Milyar TL)', 'Gerçekleşme Oranı (%)']
    if 'Kaynak' in hedef.columns:
        table_cols.append('Kaynak')

    strategy_table = dash_table.DataTable(
        data=hedef[table_cols].round(2).to_dict('records'),
        columns=[{"name": c, "id": c} for c in table_cols],
        page_size=12,
        sort_action='native',
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#2c3e50', 'color': 'white',
            'fontWeight': 'bold', 'fontSize': '0.8rem',
        },
        style_cell={'textAlign': 'left', 'padding': '6px', 'fontSize': '0.8rem'},
        style_data_conditional=[
            {'if': {'filter_query': '{Fark (Milyar TL)} >= 0', 'column_id': 'Fark (Milyar TL)'},
             'color': '#27ae60', 'fontWeight': 'bold'},
            {'if': {'filter_query': '{Fark (Milyar TL)} < 0', 'column_id': 'Fark (Milyar TL)'},
             'color': '#e74c3c'},
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
        ],
    )

    # Ay bazında strateji değişimi bölümü
    TR_MONTHS_SORT = {
        'Ocak': 1, 'Şubat': 2, 'Mart': 3, 'Nisan': 4, 'Mayıs': 5, 'Haziran': 6,
        'Temmuz': 7, 'Ağustos': 8, 'Eylül': 9, 'Ekim': 10, 'Kasım': 11, 'Aralık': 12,
    }
    month_options = sorted(
        [k for k in strategy_history.keys()],
        key=lambda k: _parse_month_key(k, TR_MONTHS_SORT),
    )
    default_month = month_options[0] if month_options else None

    month_detail_section = html.Div([
        html.Hr(),
        html.H5("📊 Ay Bazında Strateji Değişimi", className="mt-3 mb-2"),
        html.P("Bir ay seçerek, o ay için farklı strateji dökümanlarında öngörülen tutarları ve gerçekleşmeyi karşılaştırın.",
               style={"fontSize": "0.85rem", "color": "#6c757d"}),
        dbc.Row([
            dbc.Col([
                html.Label("Ay Seçin:", style={"fontWeight": "bold", "fontSize": "0.85rem"}),
                dcc.Dropdown(
                    id='strategy-month-dropdown',
                    options=[{"label": m, "value": m} for m in month_options],
                    value=default_month,
                    clearable=False,
                    style={"fontSize": "0.9rem"},
                ),
            ], md=3),
        ], className="mb-3"),
        html.Div(id='strategy-month-detail'),
    ]) if month_options else html.Div()

    return html.Div([
        kpi_row,
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), md=7),
            dbc.Col(dcc.Graph(figure=fig2), md=5),
        ], className="mb-3"),
        month_detail_section,
        html.Hr(),
        html.H6("Strateji Detay Tablosu", className="mt-3 mb-2"),
        strategy_table,
    ])


# ============================================================
# AY BAZINDA STRATEJİ DEĞİŞİMİ CALLBACK
# ============================================================

@callback(
    Output("strategy-month-detail", "children"),
    Input("strategy-month-dropdown", "value"),
    Input("date-picker", "start_date"),
    Input("date-picker", "end_date"),
    Input("security-dropdown", "value"),
    Input("isin-input", "value"),
    prevent_initial_call=False,
)
def render_month_strategy_detail(selected_month, start, end, types, isin):
    """Seçilen ay için strateji dökümanları arasındaki değişimi gösterir."""
    if not selected_month or selected_month not in strategy_history:
        return html.Div("Bu ay için strateji verisi bulunamadı.", className="text-muted")

    EN_TO_TR = {
        'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
        'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
        'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık',
    }

    entry = strategy_history[selected_month]
    history_list = entry.get("history", [])
    if not history_list:
        # Eski format fallback
        history_list = [{"target": entry.get("target", 0), "source": entry.get("source", "Bilinmiyor")}]

    # Gerçekleşen değeri hesapla
    dff = filter_df(df_main, start, end, types, isin)
    realized = 0
    for _, row in dff.iterrows():
        dt = row['İhale Tarihi']
        en_month = dt.strftime('%B')
        tr_month = EN_TO_TR.get(en_month, en_month)
        key = f"{tr_month} {dt.year}"
        if key == selected_month:
            total = row.get('Toplam(Gerçekleşme)', 0)
            if pd.notna(total) and total > 0:
                realized += total
    realized_milyar = realized / 1000  # Milyon → Milyar

    # Bar chart oluştur
    labels = [h.get("source", "Bilinmiyor") for h in history_list]
    values = [round(h.get("target", 0), 1) for h in history_list]
    colors = ['#3498db'] * len(history_list)

    # Gerçekleşen değeri ekle
    if realized_milyar > 0:
        labels.append("Gerçekleşen")
        values.append(round(realized_milyar, 2))
        colors.append('#2ecc71')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f"{v:.1f}" for v in values],
        textposition='outside',
        textfont=dict(size=14, color='#2c3e50'),
    ))

    # Değişim annotation'ları ekle
    for i in range(1, len(history_list)):
        prev_val = history_list[i - 1]["target"]
        curr_val = history_list[i]["target"]
        if prev_val > 0:
            change_pct = ((curr_val - prev_val) / prev_val) * 100
            change_color = '#27ae60' if change_pct >= 0 else '#e74c3c'
            change_symbol = '▲' if change_pct >= 0 else '▼'
            fig.add_annotation(
                x=labels[i], y=curr_val,
                text=f"{change_symbol} {abs(change_pct):.1f}%",
                showarrow=True, arrowhead=2, arrowcolor=change_color,
                font=dict(color=change_color, size=12, family="Arial Black"),
                ax=0, ay=-35,
            )

    # Gerçekleşen vs son hedef karşılaştırma
    if realized_milyar > 0 and len(history_list) > 0:
        last_target = history_list[-1]["target"]
        if last_target > 0:
            diff_pct = ((realized_milyar - last_target) / last_target) * 100
            diff_color = '#27ae60' if diff_pct >= 0 else '#e74c3c'
            diff_symbol = '▲' if diff_pct >= 0 else '▼'
            fig.add_annotation(
                x="Gerçekleşen", y=realized_milyar,
                text=f"Hedefe göre: {diff_symbol} {abs(diff_pct):.1f}%",
                showarrow=True, arrowhead=2, arrowcolor=diff_color,
                font=dict(color=diff_color, size=11),
                ax=0, ay=-35,
            )

    fig.update_layout(
        title=f"{selected_month} — Strateji Dökümanlarında Öngörülen Borçlanma",
        yaxis_title="Milyar TL",
        template="plotly_white",
        height=400,
        showlegend=False,
        margin=dict(t=50, b=80),
        xaxis=dict(tickangle=-15),
    )

    # Detay tablosu
    detail_rows = []
    for i, h in enumerate(history_list):
        row_data = {
            "Sıra": i + 1,
            "Strateji Dökümanı": h.get("source", "Bilinmiyor"),
            "Öngörülen (Milyar TL)": round(h.get("target", 0), 1),
        }
        if i > 0:
            prev = history_list[i - 1]["target"]
            curr = h["target"]
            row_data["Değişim (Milyar TL)"] = round(curr - prev, 2)
            row_data["Değişim (%)"] = round(((curr - prev) / prev * 100) if prev > 0 else 0, 1)
        else:
            row_data["Değişim (Milyar TL)"] = "-"
            row_data["Değişim (%)"] = "-"
        detail_rows.append(row_data)

    if realized_milyar > 0:
        last_t = history_list[-1]["target"] if history_list else 0
        detail_rows.append({
            "Sıra": "✓",
            "Strateji Dökümanı": "GERÇEKLEŞEN",
            "Öngörülen (Milyar TL)": round(realized_milyar, 2),
            "Değişim (Milyar TL)": round(realized_milyar - last_t, 2) if last_t > 0 else "-",
            "Değişim (%)": round(((realized_milyar - last_t) / last_t * 100) if last_t > 0 else 0, 1),
        })

    detail_table = dash_table.DataTable(
        data=detail_rows,
        columns=[
            {"name": "Sıra", "id": "Sıra"},
            {"name": "Strateji Dökümanı", "id": "Strateji Dökümanı"},
            {"name": "Öngörülen (Milyar TL)", "id": "Öngörülen (Milyar TL)"},
            {"name": "Değişim (Milyar TL)", "id": "Değişim (Milyar TL)"},
            {"name": "Değişim (%)", "id": "Değişim (%)"},
        ],
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#34495e', 'color': 'white',
            'fontWeight': 'bold', 'fontSize': '0.8rem',
        },
        style_cell={'textAlign': 'center', 'padding': '8px', 'fontSize': '0.85rem'},
        style_data_conditional=[
            {'if': {'filter_query': '{Strateji Dökümanı} = "GERÇEKLEŞEN"'},
             'backgroundColor': '#d5f5e3', 'fontWeight': 'bold'},
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
        ],
    )

    return html.Div([
        dcc.Graph(figure=fig),
        html.H6("Döküman Bazında Detay", className="mt-2 mb-2"),
        detail_table,
    ])


# ============================================================
# TAB 4: VADE ANALİZİ
# ============================================================

def render_maturity(dff, start_date, end_date):
    vade = df_vade.copy()
    if start_date:
        vade = vade[vade['Tarih'] >= pd.to_datetime(start_date)]
    if end_date:
        vade = vade[vade['Tarih'] <= pd.to_datetime(end_date)]

    if vade.empty and dff.empty:
        return html.Div(dcc.Graph(figure=empty_fig()))

    # Dual-axis: WAM + İhraç hacmi
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    if not vade.empty:
        fig1.add_trace(
            go.Bar(name="İhraç Hacmi (Milyon TL)", x=vade['Dönem'],
                   y=vade['Toplam İhraç (Milyon TL)'],
                   marker_color='rgba(31,119,180,0.3)'),
            secondary_y=False,
        )
        fig1.add_trace(
            go.Scatter(name="Ağırlıklı Ort. Vade (Yıl)", x=vade['Dönem'],
                       y=vade['Ağırlıklı Ortalama Vade (Yıl)'],
                       mode='lines+markers', line=dict(color='#e74c3c', width=2.5),
                       marker=dict(size=5)),
            secondary_y=True,
        )
    fig1.update_layout(
        title="Ağırlıklı Ortalama Vade & İhraç Hacmi", template="plotly_white", height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        xaxis=dict(tickangle=-45, dtick=3),
        margin=dict(t=40, b=80),
    )
    fig1.update_yaxes(title_text="İhraç (Milyon TL)", secondary_y=False)
    fig1.update_yaxes(title_text="Vade (Yıl)", secondary_y=True)

    # 3 aylık hareketli ortalama
    fig2 = go.Figure()
    if not vade.empty and '3 Aylık Ağırlıklı Ortalama Vade' in vade.columns:
        fig2.add_trace(go.Scatter(
            name="3 Aylık Hareketli Ortalama", x=vade['Dönem'],
            y=vade['3 Aylık Ağırlıklı Ortalama Vade'],
            mode='lines', line=dict(color='#9b59b6', width=2.5),
            fill='tozeroy', fillcolor='rgba(155,89,182,0.1)',
        ))
        fig2.add_trace(go.Scatter(
            name="Aylık WAM", x=vade['Dönem'],
            y=vade['Ağırlıklı Ortalama Vade (Yıl)'],
            mode='markers', marker=dict(size=4, color='#e74c3c'),
        ))
    fig2.update_layout(
        title="3 Aylık Hareketli Ortalama Vade", template="plotly_white", height=350,
        yaxis_title="Yıl", xaxis=dict(tickangle=-45, dtick=3),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25),
        margin=dict(t=40, b=60),
    )

    # Vade dağılımı box plot
    fig3 = go.Figure()
    if not dff.empty:
        fig3 = px.box(
            dff.sort_values('Çeyrek'), x='Çeyrek', y='Vade (Yıl)',
            color='Senet Tanımı', color_discrete_map=COLOR_MAP,
            title="Çeyrek Bazında Vade Dağılımı",
        )
    fig3.update_layout(
        template="plotly_white", height=400,
        xaxis=dict(tickangle=-45), showlegend=False,
        margin=dict(t=40, b=60),
    )

    # Vade Heatmap
    fig4 = go.Figure()
    if not dff.empty:
        pivot = dff.groupby(['Yıl', 'Ay'])['Vade (Yıl)'].mean().reset_index()
        pivot_table = pivot.pivot(index='Yıl', columns='Ay', values='Vade (Yıl)')
        month_labels = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']
        fig4 = go.Figure(data=go.Heatmap(
            z=pivot_table.values,
            x=[month_labels[int(c) - 1] for c in pivot_table.columns],
            y=pivot_table.index,
            colorscale='RdYlBu_r',
            colorbar=dict(title="Vade (Yıl)"),
            hoverongaps=False,
        ))
    fig4.update_layout(
        title="Vade Heatmap (Yıl × Ay)", template="plotly_white", height=400,
        margin=dict(t=40, b=40),
    )

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), md=7),
            dbc.Col(dcc.Graph(figure=fig2), md=5),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig3), md=6),
            dbc.Col(dcc.Graph(figure=fig4), md=6),
        ]),
    ])


# ============================================================
# TAB 5: FAİZ & FİYAT
# ============================================================

def render_rates(dff):
    if dff.empty:
        return html.Div(dcc.Graph(figure=empty_fig()))

    # Bileşik faiz trendi
    rate_df = dff.dropna(subset=['Ortalama Yıllık Bileşik(Gerçekleşme)'])
    fig1 = px.scatter(
        rate_df.sort_values('İhale Tarihi'),
        x='İhale Tarihi', y='Ortalama Yıllık Bileşik(Gerçekleşme)',
        color='Senet Tanımı', color_discrete_map=COLOR_MAP,
        title="Bileşik Faiz Oranı Trendi (%)",
    )
    fig1.update_layout(
        template="plotly_white", height=400,
        yaxis_title="Bileşik Faiz (%)", xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        margin=dict(t=40, b=80),
    )

    # Teklif vs Gerçekleşme spread
    spread_df = dff.dropna(subset=['Ortalama Yıllık Bileşik(Teklif)', 'Ortalama Yıllık Bileşik(Gerçekleşme)'])
    fig2 = px.scatter(
        spread_df,
        x='Ortalama Yıllık Bileşik(Teklif)', y='Ortalama Yıllık Bileşik(Gerçekleşme)',
        color='Senet Tanımı', color_discrete_map=COLOR_MAP,
        title="Teklif vs Gerçekleşme Faiz",
        hover_data=['ISIN', 'İhale Tarihi'],
    )
    if not spread_df.empty:
        max_val = max(
            spread_df['Ortalama Yıllık Bileşik(Teklif)'].max(),
            spread_df['Ortalama Yıllık Bileşik(Gerçekleşme)'].max()
        )
        fig2.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode='lines', line=dict(dash='dash', color='gray'),
            name='45° Referans', showlegend=True,
        ))
    fig2.update_layout(
        template="plotly_white", height=400,
        xaxis_title="Teklif Faiz (%)", yaxis_title="Gerçekleşme Faiz (%)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        margin=dict(t=40, b=80),
    )

    # Fiyat aralığı
    price_df = dff.dropna(subset=['Ortalama Fiyat(Gerçekleşme)', 'En Düşük Fiyat(Gerçekleşme)', 'En Yüksek Fiyat(Gerçekleşme)'])
    price_df = price_df.sort_values('İhale Tarihi').tail(50)  # Son 50 ihale

    fig3 = go.Figure()
    if not price_df.empty:
        fig3.add_trace(go.Scatter(
            name="En Yüksek", x=price_df['İhale Tarihi'], y=price_df['En Yüksek Fiyat(Gerçekleşme)'],
            mode='lines', line=dict(width=0), showlegend=False,
        ))
        fig3.add_trace(go.Scatter(
            name="Fiyat Aralığı", x=price_df['İhale Tarihi'], y=price_df['En Düşük Fiyat(Gerçekleşme)'],
            fill='tonexty', fillcolor='rgba(31,119,180,0.2)',
            mode='lines', line=dict(width=0),
        ))
        fig3.add_trace(go.Scatter(
            name="Ortalama Fiyat", x=price_df['İhale Tarihi'], y=price_df['Ortalama Fiyat(Gerçekleşme)'],
            mode='lines+markers', line=dict(color='#e74c3c', width=2),
            marker=dict(size=4),
        ))
    fig3.update_layout(
        title="Fiyat Aralığı (Son 50 İhale)", template="plotly_white", height=400,
        yaxis_title="Fiyat", xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        margin=dict(t=40, b=60),
    )

    # Bid-to-Cover oranı
    btc_df = dff.dropna(subset=['Bid-to-Cover']).sort_values('İhale Tarihi')
    fig4 = px.scatter(
        btc_df, x='İhale Tarihi', y='Bid-to-Cover',
        color='Senet Tanımı', color_discrete_map=COLOR_MAP,
        title="Bid-to-Cover Oranı (Talep/Gerçekleşme)",
        hover_data=['ISIN'],
    )
    fig4.add_hline(y=1.0, line_dash="dash", line_color="red", annotation_text="1.0x")
    fig4.update_layout(
        template="plotly_white", height=400,
        yaxis_title="Bid/Cover", xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        margin=dict(t=40, b=80),
    )

    return html.Div([
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), md=6),
            dbc.Col(dcc.Graph(figure=fig2), md=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig3), md=6),
            dbc.Col(dcc.Graph(figure=fig4), md=6),
        ]),
    ])


# ============================================================
# TAB 6: PLANLANAN İHRAÇLAR (önümüzdeki ihraçlar + tahmin)
# ============================================================

def render_planned():
    if df_planned is None or df_planned.empty:
        return html.Div(dcc.Graph(figure=empty_fig(
            "Planlı ihraç verisi bulunamadı. main.py çalıştırıldığında en güncel "
            "strateji raporundaki ihraç takviminden üretilir.")))

    dfp = df_planned.copy()
    auctions = dfp[dfp['Tahmini Gerçekleşme (Milyon TL)'].notna()].copy()
    direct = dfp[dfp['Tahmini Gerçekleşme (Milyon TL)'].isna()]

    # KPI satırı
    n_auction = len(auctions)
    gerc_col = 'Tahmini Gerçekleşme (Milyon TL)'
    teklif_col = 'Tahmini Teklif (Milyon TL)'
    total_gerc = auctions[gerc_col].sum() / 1000 if n_auction else 0
    total_teklif = auctions[teklif_col].sum() / 1000 if n_auction else 0
    date_range = f"{dfp['İhale Tarihi'].iloc[0]} – {dfp['İhale Tarihi'].iloc[-1]}" if len(dfp) else "-"
    kpi_row = dbc.Row([
        dbc.Col(make_kpi_card("Planlı İhale (tahminli)", f"{n_auction}", "primary"), md=3),
        dbc.Col(make_kpi_card("Tahmini Toplam Gerçekleşme", f"{total_gerc:,.1f} Milyar TL", "success"), md=3),
        dbc.Col(make_kpi_card("Tahmini Toplam Teklif (Bid)", f"{total_teklif:,.1f} Milyar TL", "warning"), md=3),
        dbc.Col(make_kpi_card("Dönem", date_range, "info"), md=3),
    ], className="mb-3 g-2")

    # Grafik 1: Tahmini Teklif (bid) + Gerçekleşme bar'ları + Bid-to-Cover noktası
    fig1 = make_subplots(specs=[[{"secondary_y": True}]])
    if n_auction:
        auctions = auctions.copy()
        auctions['etiket'] = auctions['İhale Tarihi'] + '<br>' + auctions['Senet Tanımı'].str.replace(' Devlet Tahvili', '', regex=False)
        # Teklif (arka plan, açık gri) — beklenen toplam talep
        fig1.add_trace(
            go.Bar(name="Tahmini Teklif / Bid (Milyon TL)", x=auctions['etiket'],
                   y=auctions[teklif_col], marker_color='#cfd6dc', opacity=0.85,
                   hovertemplate='Teklif: %{y:,.0f} M TL<extra></extra>'),
            secondary_y=False,
        )
        # Gerçekleşme (ön plan, senet rengi) — beklenen satış
        fig1.add_trace(
            go.Bar(name="Tahmini Gerçekleşme (Milyon TL)", x=auctions['etiket'],
                   y=auctions[gerc_col],
                   marker_color=[COLOR_MAP.get(s, '#7f8c8d') for s in auctions['Senet Tanımı']],
                   opacity=0.95,
                   text=[f"{v/1000:.1f}" for v in auctions[gerc_col]], textposition='inside',
                   hovertemplate='Gerçekleşme: %{y:,.0f} M TL<extra></extra>'),
            secondary_y=False,
        )
        # Bid-to-Cover (ikincil eksen, kırmızı baklava)
        fig1.add_trace(
            go.Scatter(name="Tahmini Bid-to-Cover", x=auctions['etiket'],
                       y=auctions['Tahmini Bid-to-Cover'],
                       mode='markers+text', marker=dict(size=11, color='#e74c3c', symbol='diamond'),
                       text=[f"{v:.2f}x" for v in auctions['Tahmini Bid-to-Cover']],
                       textposition='top center', textfont=dict(size=10, color='#c0392b'),
                       hovertemplate='Bid/Cover: %{y:.2f}x<extra></extra>'),
            secondary_y=True,
        )
    fig1.update_layout(
        title="Önümüzdeki Planlı İhaleler — Teklif (Bid) vs Gerçekleşme & Bid-to-Cover",
        template="plotly_white", height=440, barmode='overlay',
        legend=dict(orientation="h", yanchor="bottom", y=-0.38),
        xaxis=dict(tickangle=-35), margin=dict(t=50, b=120),
    )
    fig1.update_yaxes(title_text="Milyon TL", secondary_y=False)
    fig1.update_yaxes(title_text="Bid-to-Cover (x)", secondary_y=True, showgrid=False, rangemode='tozero')

    # Tablo
    table_cols = ['İhale Tarihi', 'Senet Tanımı', 'Vade Terimi', 'Yöntem',
                  'Aylık Strateji Hedefi (Milyar TL)',
                  'Tahmini Gerçekleşme (Milyon TL)', 'Tahmini Bid-to-Cover',
                  'Tahmini Teklif (Milyon TL)', 'Kıyas Bazı', 'Kıyas İhale Sayısı']
    table_cols = [c for c in table_cols if c in dfp.columns]
    tbl = dfp[table_cols].copy()
    for c in ['Tahmini Gerçekleşme (Milyon TL)', 'Tahmini Teklif (Milyon TL)']:
        if c in tbl.columns:
            tbl[c] = tbl[c].round(0)
    for c in ['Tahmini Bid-to-Cover']:
        if c in tbl.columns:
            tbl[c] = tbl[c].round(2)
    table = dash_table.DataTable(
        data=tbl.to_dict('records'),
        columns=[{"name": c, "id": c} for c in table_cols],
        page_size=20,
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': '#2c3e50', 'color': 'white',
                      'fontWeight': 'bold', 'fontSize': '0.75rem'},
        style_cell={'textAlign': 'left', 'padding': '6px', 'fontSize': '0.78rem', 'minWidth': '60px'},
        style_data_conditional=[
            {'if': {'filter_query': '{Yöntem} contains "Doğrudan"'},
             'backgroundColor': '#f4f6f7', 'color': '#7f8c8d'},
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
        ],
    )

    return html.Div([
        kpi_row,
        dbc.Alert([
            "Tahminler, en güncel strateji raporundaki ihraç takviminden alınan planlı ihraçların "
            "geçmiş benzer ihalelere (aynı tahvilin yeniden ihracı veya aynı tip + benzer vade) dayalı "
            "kestirimleridir. ",
            html.B(f"Gerçekleşme tahminleri, her ayın strateji hedefi × geçmiş gerçekleşme oranına "
                   f"(~%{_rate_txt}) ölçeklenir "),
            "— Hazine planının altında gerçekleştirdiği için (backtest'le doğrulandı) saf hedef yerine "
            "bu düzeltme kullanılır. Teklif (bid) = tahmini gerçekleşme × tahmini bid-to-cover. "
            "Doğrudan satışlar (kira sertifikası, altın, döviz) ihale verisiyle tahmin edilmez.",
        ], color="light", className="border small py-2"),
        dcc.Graph(figure=fig1),
        html.H6("Planlı İhraç Takvimi ve Tahminler", className="mt-3 mb-2"),
        table,
    ])


# ============================================================
# TAB 7: TAHMİN DOĞRULAMA (BACKTEST)
# ============================================================

def render_backtest(start_date, end_date):
    if df_backtest is None or df_backtest.empty:
        return html.Div(dcc.Graph(figure=empty_fig(
            "Backtest verisi yok. main.py çalıştırıldığında üretilir.")))

    bt = df_backtest.copy()
    if start_date:
        bt = bt[bt['_d'] >= pd.to_datetime(start_date)]
    if end_date:
        bt = bt[bt['_d'] <= pd.to_datetime(end_date)]
    if bt.empty:
        return html.Div(dcc.Graph(figure=empty_fig("Seçili tarih aralığında backtest verisi yok")))

    actual = 'Gerçek Gerçekleşme (Milyon TL)'
    strat = 'Tahmin-Strateji (Milyon TL)'
    ham = 'Tahmin-Ham (Milyon TL)'

    def _mape(fcol, acol):
        m = bt[acol].notna() & bt[fcol].notna() & (bt[acol] != 0)
        return float((bt.loc[m, fcol] - bt.loc[m, acol]).abs().div(bt.loc[m, acol]).mean() * 100) if m.any() else float('nan')

    def _bias(fcol, acol):
        m = bt[acol].notna() & bt[fcol].notna() & (bt[acol] != 0)
        return float(((bt.loc[m, fcol] - bt.loc[m, acol]) / bt.loc[m, acol]).mean() * 100) if m.any() else float('nan')

    kpi = dbc.Row([
        dbc.Col(make_kpi_card("Backtest İhale", f"{len(bt)}", "primary"), md=3),
        dbc.Col(make_kpi_card("Tutar Sapma — Ham (MAPE)", f"%{_mape(ham, actual):.0f}", "success"), md=3),
        dbc.Col(make_kpi_card("Tutar Sapma — Strateji (MAPE)", f"%{_mape(strat, actual):.0f}", "warning"), md=3),
        dbc.Col(make_kpi_card("Bid-to-Cover Sapma (MAPE)", f"%{_mape('Tahmin Bid-to-Cover', 'Gerçek Bid-to-Cover'):.0f}", "info"), md=3),
    ], className="mb-3 g-2")

    # Aylık gerçek vs tahmin
    bt['ay_d'] = bt['_d'].dt.to_period('M').dt.to_timestamp()
    monthly = bt.groupby('ay_d').agg(g=(actual, 'sum'), s=(strat, 'sum'), h=(ham, 'sum')).reset_index()
    for c in ['g', 's', 'h']:
        monthly[c] = monthly[c] / 1000
    fig1 = go.Figure()
    fig1.add_trace(go.Bar(name="Gerçek", x=monthly['ay_d'], y=monthly['g'],
                          marker_color='#2c3e50', opacity=0.8))
    fig1.add_trace(go.Scatter(name="Tahmin — ham geçmiş ort.", x=monthly['ay_d'], y=monthly['h'],
                              mode='lines+markers', line=dict(color='#27ae60', width=2)))
    fig1.add_trace(go.Scatter(name="Tahmin — strateji hedefi", x=monthly['ay_d'], y=monthly['s'],
                              mode='lines+markers', line=dict(color='#e67e22', width=2, dash='dash')))
    fig1.update_layout(title="Aylık Gerçekleşme: Gerçek vs Tahmin (Milyar TL)",
                       template="plotly_white", height=400,
                       legend=dict(orientation="h", yanchor="bottom", y=-0.3),
                       xaxis=dict(tickangle=-45, dtick="M3"), margin=dict(t=40, b=80))

    # Scatter: tahmin (strateji) vs gerçek
    fig2 = go.Figure()
    sc = bt.dropna(subset=[actual, strat])
    fig2.add_trace(go.Scatter(x=sc[actual] / 1000, y=sc[strat] / 1000, mode='markers',
                              name='İhale', marker=dict(size=6, color='#e67e22', opacity=0.5),
                              text=sc['Senet Tanımı'] + '<br>' + sc['İhale Tarihi'],
                              hovertemplate='%{text}<br>Gerçek: %{x:.1f}<br>Tahmin: %{y:.1f}<extra></extra>'))
    if not sc.empty:
        mx = max(float(sc[actual].max()), float(sc[strat].max())) / 1000
        fig2.add_trace(go.Scatter(x=[0, mx], y=[0, mx], mode='lines',
                                  line=dict(dash='dash', color='gray'), name='Birebir (45°)'))
    fig2.update_layout(title="Tahmin (strateji) vs Gerçek — ihale bazında",
                       template="plotly_white", height=400,
                       xaxis_title="Gerçek (Milyar TL)", yaxis_title="Tahmin (Milyar TL)",
                       legend=dict(orientation="h", yanchor="bottom", y=-0.3), margin=dict(t=40, b=60))

    # Detay tablo
    tcols = ['İhale Tarihi', 'Senet Tanımı', 'Gerçek Gerçekleşme (Milyon TL)',
             'Tahmin-Strateji (Milyon TL)', 'Tutar Sapma % (strateji)',
             'Gerçek Bid-to-Cover', 'Tahmin Bid-to-Cover', 'B2C Sapma %']
    tcols = [c for c in tcols if c in bt.columns]
    tbl = bt.sort_values('_d', ascending=False)[tcols].copy()
    for c in tcols:
        if 'Milyon TL' in c:
            tbl[c] = tbl[c].round(0)
        elif 'Bid-to-Cover' in c or 'Sapma' in c:
            tbl[c] = tbl[c].round(2)
    table = dash_table.DataTable(
        data=tbl.to_dict('records'),
        columns=[{"name": c, "id": c} for c in tcols],
        page_size=15, sort_action='native', filter_action='native',
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': '#2c3e50', 'color': 'white', 'fontWeight': 'bold', 'fontSize': '0.75rem'},
        style_cell={'textAlign': 'left', 'padding': '6px', 'fontSize': '0.78rem'},
        style_data_conditional=[
            {'if': {'filter_query': '{Tutar Sapma % (strateji)} > 30', 'column_id': 'Tutar Sapma % (strateji)'},
             'color': '#c0392b'},
            {'if': {'filter_query': '{Tutar Sapma % (strateji)} < -30', 'column_id': 'Tutar Sapma % (strateji)'},
             'color': '#2980b9'},
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
        ],
    )

    return html.Div([
        kpi,
        dbc.Alert([
            "Her geçmiş ihale, ", html.B("yalnızca o tarihten önceki veriyle"),
            " (look-ahead yok) ileriye dönük yöntemin aynısıyla tahmin edilip gerçeğe kıyaslanır. ",
            html.B("Bulgu: "), "Strateji hedefine ölçeklenen tahmin sistematik olarak FAZLA tahmin "
            "ediyor (Hazine planının altında gerçekleştiriyor); ham geçmiş ortalaması daha isabetli. "
            "MAPE = ortalama mutlak yüzde sapma (düşük = iyi). Erken dönem (2020-21) strateji "
            "hedefleri gerçekçi olmadığından tarih filtresiyle yakın döneme odaklanabilirsin.",
        ], color="light", className="border small py-2"),
        dbc.Row([
            dbc.Col(dcc.Graph(figure=fig1), md=7),
            dbc.Col(dcc.Graph(figure=fig2), md=5),
        ], className="mb-3"),
        html.H6("İhale Bazında Tahmin vs Gerçek", className="mt-2 mb-2"),
        table,
    ])


# ============================================================
# ÇALIŞTIR
# ============================================================

if __name__ == '__main__':
    print("🏛️ Hazine İhraç Paneli başlatılıyor...")
    print(f"   → {len(df_main)} ihale kaydı yüklendi")
    print(f"   → {len(df_vade)} aylık vade analizi yüklendi")
    print(f"   → {len(df_hedef)} strateji satırı yüklendi")
    if not df_planned.empty:
        print(f"   → {len(df_planned)} planlı ihraç yüklendi")
    port = int(os.environ.get('PORT', 8050))
    # NOT: debug=True, Dash'in ~7.5 MB'lık MINIFY EDİLMEMİŞ (dev) JS paketlerini
    # servis etmesine yol açıyor; tarayıcı bunu ayrıştırırken donup "unresponsive"
    # diyor. Varsayılan production (minified) paketler → hızlı açılış.
    # Geliştirme/hot-reload istenirse: DASH_DEBUG=1 ile çalıştır.
    debug = os.environ.get('DASH_DEBUG', '') == '1'
    print(f"   → http://127.0.0.1:{port} adresinde açılıyor... (debug={'açık' if debug else 'kapalı'})")
    app.run(debug=debug, port=port, threaded=True)
