import os
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlencode
from datetime import date
import plotly.graph_objects as go

# Çıktılar script'in kendi klasörüne yazılır (taşınmaya dayanıklı)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Tarih parametreleri (otomatik: bugün) ---
today = date.today()
display_end = pd.Timestamp(today)
fetch_end = today.strftime("%d-%m-%Y")
display_start = pd.Timestamp("2025-03-01")  # grafik sabit başlangıç (İmamoğlu dönemi)
fetch_start = "01-12-2023"  # EVDS geçmiş veri başlangıcı

EVDS_KEY = "5ILfFTTp8n"
EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"


def fetch_evds(series_code: str, start: str, end: str) -> pd.Series:
    params = {"series": series_code, "startDate": start, "endDate": end, "type": "json"}
    url = f"{EVDS_BASE}/{urlencode(params)}"
    r = requests.get(url, headers={"key": EVDS_KEY}, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    df = pd.DataFrame(items)
    df["Tarih"] = pd.to_datetime(df["Tarih"].astype(str), format="%d-%m-%Y")
    col = series_code.replace(".", "_")
    df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[col]).sort_values("Tarih")
    return df.set_index("Tarih")[col].rename(series_code)


print(f"Veri aralığı: {fetch_start} – {fetch_end} (bugün: {today})")
print("EVDS'den USD/TRY cekiliyor...")
usdtry = fetch_evds("TP.DK.USD.A.YTL", fetch_start, fetch_end)
print(f"  {len(usdtry)} kayit, {usdtry.index[0].date()} - {usdtry.index[-1].date()}")

usdtry_full = usdtry.asfreq("D").interpolate(method="time")
business = usdtry_full[usdtry_full.index.dayofweek < 5]


def deval_act365(s: pd.Series, n: int) -> pd.Series:
    """Yıllıklandırılmış devalüasyon, ACT/365 takvim günü tabanı.

    Pencere n GÖZLEM (iş günü) geriye gider; üs, iki gözlem tarihinin GERÇEK
    takvim günü farkı Δd üzerinden: oran = (P_t / P_{t-n}) ** (365 / Δd) - 1.
    """
    ratio = s / s.shift(n)
    delta_d = pd.Series(s.index, index=s.index).diff(n).dt.days.astype(float)
    return (ratio ** (365.0 / delta_d) - 1) * 100


m_d = 21
deval_1m = deval_act365(business, m_d)

d1m = deval_1m[(deval_1m.index >= display_start) & (deval_1m.index <= display_end)].dropna()

imamoglu = pd.Timestamp("2025-03-19")
iran_war = pd.Timestamp("2026-02-28")

palette = [
    "#2563eb", "#dc2626", "#16a34a", "#7c3aed", "#ea580c",
    "#0891b2", "#db2777", "#65a30d", "#9333ea", "#14b8a6",
    "#be123c", "#0e7490", "#7c2d12", "#1e40af", "#a16207",
]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=d1m.index, y=d1m.values,
    name="USDTRY 1A Devalüasyon — yıllıklandırılmış (ACT/365)",
    line=dict(color="#64748b", width=1.6),
    opacity=0.55,
    hovertemplate="<b>%{x|%d %b %Y}</b><br>1A (ACT/365): %{y:.2f}%<extra></extra>",
))

monthly_groups = d1m.groupby(pd.Grouper(freq="MS"))

monthly_summary = []
for i, (month_start, month_data) in enumerate(monthly_groups):
    if len(month_data) < 5:
        continue
    avg = month_data.mean()
    x_days = (month_data.index - month_data.index[0]).days.values.astype(float)
    slope, intercept = np.polyfit(x_days, month_data.values, 1)
    trend = slope * x_days + intercept

    month_label_tr = month_start.strftime("%b %Y")
    color = palette[i % len(palette)]
    monthly_summary.append((month_label_tr, avg, slope * 30, color, month_start))

    fig.add_trace(go.Scatter(
        x=month_data.index, y=trend,
        name=f"<b>{month_label_tr}</b>  ·  avg %{avg:.1f}  ·  {slope*30:+.2f}%/ay",
        line=dict(color=color, width=3.5),
        hovertemplate=(f"<b>{month_label_tr}</b><br>"
                       f"Trend değeri: %{{y:.2f}}<br>"
                       f"Aylık ortalama: %{avg:.2f}<br>"
                       f"Eğim: {slope*30:+.2f}%/ay<extra></extra>"),
    ))

    mid_idx = len(month_data) // 2
    if mid_idx < len(month_data):
        mid_date = month_data.index[mid_idx]
        fig.add_annotation(
            x=mid_date.to_pydatetime(), y=avg,
            text=f"<b>%{avg:.1f}</b>",
            showarrow=False,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=color, borderwidth=1.2, borderpad=3,
            font=dict(size=10, color=color, family="Arial Black"),
            yshift=18,
        )

ts_im = imamoglu.value // 10**6
ts_ir = iran_war.value // 10**6

fig.add_shape(type="line", xref="x", yref="paper",
              x0=ts_im, x1=ts_im, y0=0, y1=1,
              line=dict(color="#dc2626", width=2.5, dash="dash"),
              layer="below")
fig.add_shape(type="line", xref="x", yref="paper",
              x0=ts_ir, x1=ts_ir, y0=0, y1=1,
              line=dict(color="#ea580c", width=2.5, dash="dash"),
              layer="below")
fig.add_trace(go.Scatter(
    x=[None], y=[None],
    name="📍 İmamoğlu Tutuklanması (19.03.2025)",
    line=dict(color="#dc2626", width=2.5, dash="dash"),
    mode="lines",
))
fig.add_trace(go.Scatter(
    x=[None], y=[None],
    name="📍 İran-ABD Savaşı (28.02.2026)",
    line=dict(color="#ea580c", width=2.5, dash="dash"),
    mode="lines",
))

fig.add_hline(y=0, line=dict(color="rgba(15,23,42,0.5)", width=1.2, dash="dot"))

fig.update_xaxes(
    showgrid=True, gridcolor="rgba(15,23,42,0.08)",
    minor=dict(showgrid=True, gridcolor="rgba(15,23,42,0.03)",
               ticks="outside", ticklen=3),
    tickformat="%b\n%Y",
    dtick="M1",
    tickfont=dict(size=11, color="#1e293b"),
    range=[display_start.to_pydatetime(), display_end.to_pydatetime()],
    ticks="outside", ticklen=5,
    showline=True, linecolor="#94a3b8",
)

fig.update_yaxes(
    title_text="<b>1 Aylık Devalüasyon (%, yıllıklandırılmış ACT/365)</b>",
    showgrid=True, gridcolor="rgba(15,23,42,0.08)",
    minor=dict(showgrid=True, gridcolor="rgba(15,23,42,0.03)",
               ticks="outside", ticklen=3),
    autorange=True,
    rangemode="tozero",
    zeroline=True, zerolinecolor="rgba(15,23,42,0.50)", zerolinewidth=1.2,
    tickfont=dict(size=11, color="#1e293b"),
    title_font=dict(color="#1e293b"),
    showline=True, linecolor="#94a3b8",
    ticksuffix="%",
)

fig.update_layout(
    title=dict(
        text="<b>USDTRY 1A Devalüasyon, yıllıklandırılmış (ACT/365) — Aylık Trend & Ortalama</b>"
             f"<br><sub>{display_start.strftime('%d.%m.%Y')} – {display_end.strftime('%d.%m.%Y')} · "
             "Her aya ait linear regression trend çizgisi · Etiket üzerinde aylık avg</sub>",
        font=dict(size=16, color="#0f172a"),
        x=0.02, xanchor="left", y=0.97,
    ),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#fafbfc",
    font=dict(color="#1e293b", family="Arial"),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="top", y=-0.18,
        xanchor="center", x=0.5,
        bgcolor="rgba(255,255,255,0.98)",
        bordercolor="#cbd5e1", borderwidth=1,
        font=dict(size=10, color="#1e293b"),
        itemwidth=70,
        traceorder="normal",
    ),
    margin=dict(l=90, r=80, t=80, b=240),
    height=750,
    autosize=True,
)

print("\nAylık özet:")
print(f"{'Ay':<12}{'Avg (%)':>12}{'Eğim (%/ay)':>16}")
print("-" * 40)
for label, avg, slope_m, _, _ in monthly_summary:
    print(f"{label:<12}{avg:>12.2f}{slope_m:>16.2f}")

output_html = os.path.join(BASE_DIR, "usdtry_monthly_trends.html")
fig.write_html(output_html, include_plotlyjs="cdn",
               config={"responsive": True, "displaylogo": False})
print(f"\nHTML kaydedildi: {output_html}")

try:
    output_png = os.path.join(BASE_DIR, "usdtry_monthly_trends.png")
    fig.write_image(output_png, width=1800, height=850, scale=2)
    print(f"PNG kaydedildi: {output_png}")
except Exception as e:
    print(f"PNG yazma hatasi (HTML etkilenmez): {e}")
