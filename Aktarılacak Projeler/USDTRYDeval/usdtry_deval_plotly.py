import requests
import pandas as pd
import numpy as np
from urllib.parse import urlencode
from datetime import date
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

# --- Tarih parametreleri (her çalıştırmada bugüne kadar güncellenir) ---
today = date.today()
display_end = pd.Timestamp(today)
fetch_end = today.strftime("%d-%m-%Y")
fetch_start = "01-02-2024"  # EVDS geçmiş veri başlangıcı
range_1y_start = pd.Timestamp("2025-03-01")  # 1Y grafik sabit başlangıç
range_3m_start = display_end - pd.Timedelta(days=90)
range_6m_start = display_end - pd.Timedelta(days=180)


def fmt_range(start: pd.Timestamp, end: pd.Timestamp) -> str:
    """Grafik başlıkları için tarih aralığı metni."""
    return f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"

EVDS_KEY = "5ILfFTTp8n"
EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"


def fetch_evds(series_code: str, start: str, end: str) -> pd.Series:
    params = {
        "series": series_code,
        "startDate": start,
        "endDate": end,
        "type": "json",
    }
    url = f"{EVDS_BASE}/{urlencode(params)}"
    r = requests.get(url, headers={"key": EVDS_KEY}, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError(f"EVDS no data for {series_code}")

    df = pd.DataFrame(items)
    raw = df["Tarih"].astype(str)
    if raw.iloc[0].count("-") == 2 and len(raw.iloc[0].split("-")[0]) == 2:
        df["Tarih"] = pd.to_datetime(raw, format="%d-%m-%Y")
    else:
        df["Tarih"] = pd.to_datetime(raw + "-01", format="%Y-%m-%d")

    col = series_code.replace(".", "_")
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[col]).sort_values("Tarih")
    return df.set_index("Tarih")[col].rename(series_code)


print(f"Veri aralığı: {fetch_start} – {fetch_end} (bugün: {today})")
print("EVDS'den veriler cekiliyor...")
usdtry = fetch_evds("TP.DK.USD.A.YTL", fetch_start, fetch_end)
tlref = fetch_evds("TP.BISTTLREF.ORAN", fetch_start, fetch_end)
kredi = fetch_evds("TP.KTF101", fetch_start, fetch_end)
mev_1m = fetch_evds("TP.TRYTAS.MT01", fetch_start, fetch_end)
mev_3m = fetch_evds("TP.TRYTAS.MT02", fetch_start, fetch_end)
mev_6m = fetch_evds("TP.TRYTAS.MT03", fetch_start, fetch_end)
mev_12m = fetch_evds("TP.TRYTAS.MT04", fetch_start, fetch_end)
print(f"  USD/TRY: {len(usdtry)}, TLREF: {len(tlref)}, Kredi: {len(kredi)}, "
      f"Mevduat: {len(mev_1m)}/{len(mev_3m)}/{len(mev_6m)}/{len(mev_12m)}")

usdtry_full = usdtry.asfreq("D").interpolate(method="time")
business = usdtry_full[usdtry_full.index.dayofweek < 5]

w_d, m_d, q_d = 5, 21, 63
deval_1w = ((business / business.shift(w_d)) ** (252 / w_d) - 1) * 100
deval_1m = ((business / business.shift(m_d)) ** (252 / m_d) - 1) * 100
deval_3m = ((business / business.shift(q_d)) ** (252 / q_d) - 1) * 100

C = {
    "deval_1w": "#eab308",
    "deval_1m": "#f97316",
    "deval_3m": "#b91c1c",
    "tlref": "#15803d",
    "kredi": "#db2777",
    "mev_1m": "#0891b2",
    "mev_3m": "#2563eb",
    "mev_6m": "#7c3aed",
    "mev_12m": "#92400e",
    "imamoglu": "#dc2626",
    "iran": "#ea580c",
    "bg_paper": "#ffffff",
    "bg_plot": "#fafbfc",
    "text": "#1e293b",
    "subtitle": "#64748b",
    "grid_major": "rgba(15, 23, 42, 0.08)",
    "grid_minor": "rgba(15, 23, 42, 0.03)",
    "zero": "rgba(15, 23, 42, 0.45)",
}

imamoglu = pd.Timestamp("2025-03-19")
iran_war = pd.Timestamp("2026-02-28")


def filt(s: pd.Series, start: pd.Timestamp) -> pd.Series:
    return s[(s.index >= start) & (s.index <= display_end)]


def linear_trend(series: pd.Series):
    """Linear regression (numpy polyfit) over a time-indexed series. Returns (x_dates, y_trend, slope_per_day)."""
    s = series.dropna()
    if len(s) < 2:
        return None, None, None
    x_days = (s.index - s.index[0]).days.values.astype(float)
    slope, intercept = np.polyfit(x_days, s.values, 1)
    trend = slope * x_days + intercept
    return s.index, trend, slope


def build_figure(title: str, start: pd.Timestamp, clip_high: float):
    fig = go.Figure()

    d1w = filt(deval_1w, start).clip(lower=-50, upper=clip_high)
    d1m = filt(deval_1m, start).clip(lower=-50, upper=clip_high)
    d3m = filt(deval_3m, start).clip(lower=-50, upper=clip_high)

    fig.add_trace(go.Scatter(
        x=d1w.index, y=d1w.values, name="Devalüasyon 1H (Ann.)",
        line=dict(color=C["deval_1w"], width=1.2, dash="dot"),
        opacity=0.7,
        legendgroup="d1w",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>1H Ann.: %{y:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=d1m.index, y=d1m.values, name="Devalüasyon 1A (Ann.)",
        line=dict(color=C["deval_1m"], width=2.2),
        legendgroup="d1m",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>1A Ann.: %{y:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=d3m.index, y=d3m.values, name="Devalüasyon 3A (Ann.)",
        line=dict(color=C["deval_3m"], width=3),
        legendgroup="d3m",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>3A Ann.: %{y:.1f}%<extra></extra>",
    ))

    for series, name, color, group in [
        (d1w, "1H Trend", C["deval_1w"], "d1w"),
        (d1m, "1A Trend", C["deval_1m"], "d1m"),
        (d3m, "3A Trend", C["deval_3m"], "d3m"),
    ]:
        idx, trend, slope = linear_trend(series)
        if trend is None:
            continue
        fig.add_trace(go.Scatter(
            x=idx, y=trend,
            name=f"{name} ({slope * 30:+.1f}%/ay)",
            line=dict(color=color, width=1.8, dash="longdash"),
            opacity=0.85,
            legendgroup=group,
            hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{name}: %{{y:.2f}}%<extra></extra>",
        ))

    tl = filt(tlref, start)
    fig.add_trace(go.Scatter(
        x=tl.index, y=tl.values, name="TLREF",
        line=dict(color=C["tlref"], width=3.2),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>TLREF: %{y:.2f}%<extra></extra>",
    ))

    buf = pd.Timedelta(days=14)
    kr = filt(kredi, start - buf)
    fig.add_trace(go.Scatter(
        x=kr.index, y=kr.values, name="İhtiyaç Kredisi",
        line=dict(color=C["kredi"], width=2),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>Kredi: %{y:.2f}%<extra></extra>",
    ))

    for series, name, key, dash in [
        (mev_1m, "Mevduat 1 Ay", "mev_1m", "solid"),
        (mev_3m, "Mevduat 3 Ay", "mev_3m", "solid"),
        (mev_6m, "Mevduat 6 Ay", "mev_6m", "solid"),
        (mev_12m, "Mevduat 12 Ay", "mev_12m", "solid"),
    ]:
        s = filt(series, start - buf)
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=name,
            line=dict(color=C[key], width=1.8, dash=dash),
            mode="lines+markers",
            marker=dict(size=4),
            hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{name}: %{{y:.2f}}%<extra></extra>",
        ))

    if start <= imamoglu <= display_end:
        ts = imamoglu.value // 10**6
        fig.add_shape(type="line", xref="x", yref="paper",
                      x0=ts, x1=ts, y0=0, y1=1,
                      line=dict(color=C["imamoglu"], width=2.5, dash="dash"),
                      layer="below")
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            name="📍 İmamoğlu Tutuklanması (19.03.2025)",
            line=dict(color=C["imamoglu"], width=2.5, dash="dash"),
            mode="lines",
        ))

    if start <= iran_war <= display_end:
        ts = iran_war.value // 10**6
        fig.add_shape(type="line", xref="x", yref="paper",
                      x0=ts, x1=ts, y0=0, y1=1,
                      line=dict(color=C["iran"], width=2.5, dash="dash"),
                      layer="below")
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            name="📍 İran-ABD Savaşı (28.02.2026)",
            line=dict(color=C["iran"], width=2.5, dash="dash"),
            mode="lines",
        ))

    fig.add_hline(y=0, line=dict(color=C["zero"], width=0.8, dash="dot"))

    fig.update_xaxes(
        showgrid=True, gridcolor=C["grid_major"], gridwidth=1,
        minor=dict(showgrid=True, gridcolor=C["grid_minor"], gridwidth=0.5,
                   ticks="outside", ticklen=3),
        tickformatstops=[
            dict(dtickrange=[None, 86400000 * 8], value="%d %b"),
            dict(dtickrange=[86400000 * 8, "M3"], value="%d %b\n%Y"),
            dict(dtickrange=["M3", None], value="%b %Y"),
        ],
        nticks=10,
        tickangle=0,
        tickfont=dict(size=11, color=C["text"]),
        # Kaleido PNG export icin Timestamp yerine datetime (JSON-serializable)
        range=[start.to_pydatetime(), display_end.to_pydatetime()],
        ticks="outside", ticklen=5,
        showline=True, linecolor="#94a3b8",
        title_font=dict(color=C["text"]),
    )

    fig.update_yaxes(
        title_text="<b>Oran (% Annualized)</b>",
        showgrid=True, gridcolor=C["grid_major"], gridwidth=1,
        minor=dict(showgrid=True, gridcolor=C["grid_minor"], gridwidth=0.5,
                   ticks="outside", ticklen=3),
        autorange=True,
        rangemode="tozero",
        zeroline=True, zerolinecolor="rgba(15,23,42,0.50)", zerolinewidth=1.2,
        tickfont=dict(size=11, color=C["text"]),
        title_font=dict(color=C["text"]),
        showline=True, linecolor="#94a3b8",
        ticksuffix="%",
    )

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=15, color=C["text"]),
            x=0.02, xanchor="left", y=0.97,
        ),
        paper_bgcolor=C["bg_paper"],
        plot_bgcolor=C["bg_plot"],
        font=dict(color=C["text"], family="Arial"),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.20,
            xanchor="center", x=0.5,
            bgcolor="rgba(255,255,255,0.98)",
            bordercolor="#cbd5e1",
            borderwidth=1,
            font=dict(size=11, color=C["text"]),
            itemwidth=70,
            traceorder="normal",
        ),
        margin=dict(l=80, r=80, t=55, b=170),
        height=520,
        autosize=True,
    )
    return fig


CLIP = {"3 Ay": 60, "6 Ay": 80, "1 Yıl": 100}
fig_3m = build_figure(f"Son 3 Ay  ·  {fmt_range(range_3m_start, display_end)}", range_3m_start, CLIP["3 Ay"])
fig_6m = build_figure(f"Son 6 Ay  ·  {fmt_range(range_6m_start, display_end)}", range_6m_start, CLIP["6 Ay"])
fig_1y = build_figure(f"Son 1 Yıl  ·  {fmt_range(range_1y_start, display_end)}", range_1y_start, CLIP["1 Yıl"])


def build_segmented_trend_figure():
    fig = go.Figure()
    seg_start = pd.Timestamp("2024-06-01")
    seg_end = display_end

    d1w = deval_1w[(deval_1w.index >= seg_start) & (deval_1w.index <= seg_end)].clip(lower=-50, upper=200)
    d1m = deval_1m[(deval_1m.index >= seg_start) & (deval_1m.index <= seg_end)].clip(lower=-50, upper=200)

    fig.add_trace(go.Scatter(
        x=d1w.index, y=d1w.values, name="Devalüasyon 1H (Ann.)",
        line=dict(color=C["deval_1w"], width=1.0, dash="dot"),
        opacity=0.45,
        legendgroup="d1w_data",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>1H: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=d1m.index, y=d1m.values, name="Devalüasyon 1A (Ann.)",
        line=dict(color=C["deval_1m"], width=1.4),
        opacity=0.55,
        legendgroup="d1m_data",
        hovertemplate="<b>%{x|%d %b %Y}</b><br>1A: %{y:.1f}%<extra></extra>",
    ))

    seg_colors = {
        "Pre-İmamoğlu": "#2563eb",
        "İmamoğlu→Savaş": "#ea580c",
        "Post-Savaş": "#dc2626",
    }
    segments = [
        ("Pre-İmamoğlu", seg_start, imamoglu),
        ("İmamoğlu→Savaş", imamoglu, iran_war),
        ("Post-Savaş", iran_war, seg_end + pd.Timedelta(days=1)),
    ]

    for label, sg_start, sg_end in segments:
        color = seg_colors[label]
        for series, series_name, dash, group in [
            (d1w, "1H", "dash", "d1w_trend"),
            (d1m, "1A", "solid", "d1m_trend"),
        ]:
            seg = series[(series.index >= sg_start) & (series.index < sg_end)]
            idx, trend, slope = linear_trend(seg)
            if trend is None:
                continue
            label_with_slope = f"{series_name} | {label} ({slope*30:+.1f}%/ay)"
            fig.add_trace(go.Scatter(
                x=idx, y=trend,
                name=label_with_slope,
                line=dict(color=color, width=3 if series_name == "1A" else 2.2, dash=dash),
                legendgroup=group,
                hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{label_with_slope}<br>%{{y:.2f}}%<extra></extra>",
            ))

    ts_im = imamoglu.value // 10**6
    ts_ir = iran_war.value // 10**6
    fig.add_shape(type="line", xref="x", yref="paper",
                  x0=ts_im, x1=ts_im, y0=0, y1=1,
                  line=dict(color=C["imamoglu"], width=2.5, dash="dash"),
                  layer="below")
    fig.add_shape(type="line", xref="x", yref="paper",
                  x0=ts_ir, x1=ts_ir, y0=0, y1=1,
                  line=dict(color=C["iran"], width=2.5, dash="dash"),
                  layer="below")
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        name="📍 İmamoğlu (19.03.2025)",
        line=dict(color=C["imamoglu"], width=2.5, dash="dash"),
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        name="📍 İran-ABD Savaşı (28.02.2026)",
        line=dict(color=C["iran"], width=2.5, dash="dash"),
        mode="lines",
    ))

    fig.add_hline(y=0, line=dict(color=C["zero"], width=0.8, dash="dot"))

    fig.update_xaxes(
        showgrid=True, gridcolor=C["grid_major"], gridwidth=1,
        minor=dict(showgrid=True, gridcolor=C["grid_minor"], gridwidth=0.5,
                   ticks="outside", ticklen=3),
        tickformatstops=[
            dict(dtickrange=[None, 86400000 * 8], value="%d %b"),
            dict(dtickrange=[86400000 * 8, "M3"], value="%d %b\n%Y"),
            dict(dtickrange=["M3", None], value="%b %Y"),
        ],
        nticks=12,
        tickfont=dict(size=11, color=C["text"]),
        range=[seg_start.to_pydatetime(), seg_end.to_pydatetime()],
        ticks="outside", ticklen=5,
        showline=True, linecolor="#94a3b8",
    )

    fig.update_yaxes(
        title_text="<b>Devalüasyon (% Annualized)</b>",
        showgrid=True, gridcolor=C["grid_major"], gridwidth=1,
        minor=dict(showgrid=True, gridcolor=C["grid_minor"], gridwidth=0.5,
                   ticks="outside", ticklen=3),
        autorange=True,
        rangemode="tozero",
        zeroline=True, zerolinecolor="rgba(15,23,42,0.50)", zerolinewidth=1.2,
        tickfont=dict(size=11, color=C["text"]),
        title_font=dict(color=C["text"]),
        showline=True, linecolor="#94a3b8",
        ticksuffix="%",
    )

    fig.update_layout(
        title=dict(
            text="<b>1H & 1A Devalüasyon — Olay Bazlı Trend Segmentasyonu</b>"
                 "<br><sub>Trend çizgileri: linear regression · Segment bazında %/ay eğim</sub>",
            font=dict(size=15, color=C["text"]),
            x=0.02, xanchor="left", y=0.97,
        ),
        paper_bgcolor=C["bg_paper"],
        plot_bgcolor=C["bg_plot"],
        font=dict(color=C["text"], family="Arial"),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="top", y=-0.20,
            xanchor="center", x=0.5,
            bgcolor="rgba(255,255,255,0.98)",
            bordercolor="#cbd5e1",
            borderwidth=1,
            font=dict(size=11, color=C["text"]),
            itemwidth=70,
        ),
        margin=dict(l=80, r=80, t=70, b=180),
        height=560,
        autosize=True,
    )
    return fig


fig_seg = build_segmented_trend_figure()

html_parts = [
    """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>USDTRY Devalüasyon & Faiz Analizi</title>
<style>
  body { background: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
         margin: 0; padding: 30px 20px; color: #1e293b; }
  .container { max-width: 1500px; margin: 0 auto; }
  h1 { text-align: center; font-size: 24px; margin: 0 0 8px 0; color: #0f172a; font-weight: 700; }
  .subtitle { text-align: center; color: #64748b; font-size: 13px; margin-bottom: 30px; }
  .fig-wrap { background: #ffffff; border-radius: 10px; padding: 16px;
              margin-bottom: 24px; box-shadow: 0 2px 8px rgba(15,23,42,0.06); }
  .footer { text-align: center; color: #94a3b8; font-size: 12px; margin-top: 20px; }
</style>
</head>
<body>
<div class="container">
<h1>USDTRY Annualized Devalüasyon vs TLREF & Mevduat/Kredi Faizleri</h1>
<p class="subtitle">Sol eksen: Devalüasyon (annualized %) · Sağ eksen: Faiz oranları (%) · Kaynak: TCMB EVDS API</p>
"""]

for fig in (fig_3m, fig_6m, fig_1y, fig_seg):
    html_parts.append('<div class="fig-wrap">')
    html_parts.append(pio.to_html(fig, full_html=False, include_plotlyjs="cdn",
                                  config={"responsive": True, "displaylogo": False}))
    html_parts.append('</div>')

html_parts.append("""
<p class="footer">USDTRY: TP.DK.USD.A.YTL · TLREF: TP.BISTTLREF.ORAN · Kredi: TP.KTF101 · Mevduat: TP.TRYTAS.MT01-04</p>
</div></body></html>""")

output_html = "/Users/tunatanozmen/Documents/aktif projeler/USDTRYDeval/usdtry_deval_plotly.html"
with open(output_html, "w", encoding="utf-8") as f:
    f.write("\n".join(html_parts))
print(f"\nHTML kaydedildi: {output_html}")

try:
    from PIL import Image
    import io as bio

    pngs = []
    for fig, name, h in [(fig_3m, "3m", 520), (fig_6m, "6m", 520),
                          (fig_1y, "1y", 520), (fig_seg, "seg", 560)]:
        buf = bio.BytesIO()
        fig.write_image(buf, format="png", width=1500, height=h, scale=2)
        buf.seek(0)
        pngs.append(Image.open(buf))

    total_h = sum(im.height for im in pngs) + 20 * (len(pngs) - 1)
    max_w = max(im.width for im in pngs)
    combined = Image.new("RGB", (max_w, total_h), color=(241, 245, 249))
    y = 0
    for im in pngs:
        combined.paste(im, ((max_w - im.width) // 2, y))
        y += im.height + 20

    output_png = "/Users/tunatanozmen/Documents/aktif projeler/USDTRYDeval/usdtry_deval_plotly.png"
    combined.save(output_png)
    print(f"Birlestirilmis PNG: {output_png}")
except Exception as e:
    print(f"PNG yazma hatasi: {e}")
