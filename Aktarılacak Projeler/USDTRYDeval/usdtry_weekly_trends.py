import os
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlencode
from datetime import date
import plotly.graph_objects as go
import plotly.colors as pc
from evds_ortak import evds_anahtari, EVDS_ILERI_GUN, EVDS_BASE

# Çıktılar script'in kendi klasörüne yazılır (taşınmaya dayanıklı)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Tarih parametreleri (otomatik: bugün) ---
today = date.today()
# EVDS sorgu bitişi bilerek birkaç gün ileri alınır: TCMB, ertesi iş gününün gösterge
# kurunu bugün öğleden sonra yayımlar. endDate=bugün olduğunda o kur sistematik olarak
# dışarıda kalır. Gelecek tarih için EVDS boş döner — ileri almak zararsızdır.
fetch_end = (pd.Timestamp(today) + pd.Timedelta(days=EVDS_ILERI_GUN)).strftime("%d-%m-%Y")
display_start = pd.Timestamp(today.replace(month=1, day=1))  # YTD başlangıç
fetch_start = (display_start - pd.Timedelta(days=60)).strftime("%d-%m-%Y")  # deval hesabı için buffer

EVDS_KEY = evds_anahtari()


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

# Grafik penceresi bugünle değil VERİYLE biter; erken yayımlanan ertesi iş günü kuru
# da son haftanın regresyonuna girsin.
display_end = max(pd.Timestamp(usdtry.index[-1]), pd.Timestamp(today))

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


w_d = 5
deval_1w = deval_act365(business, w_d)

d1w = deval_1w[(deval_1w.index >= display_start) & (deval_1w.index <= display_end)].dropna()

iran_war = pd.Timestamp("2026-02-28")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=d1w.index, y=d1w.values,
    name="USDTRY 1H Devalüasyon — yıllıklandırılmış (ACT/365)",
    line=dict(color="#94a3b8", width=1.4),
    opacity=0.55,
    hovertemplate="<b>%{x|%d %b %Y}</b><br>1H (ACT/365): %{y:.2f}%<extra></extra>",
))

weekly_groups = d1w.groupby(pd.Grouper(freq="W-SUN"))
n_weeks = sum(1 for _, g in weekly_groups if len(g) >= 2)

palette = pc.sample_colorscale("turbo", [i / max(n_weeks - 1, 1) for i in range(n_weeks)])

weekly_summary = []
week_len = {}   # hafta başlangıcı → gözlem sayısı ("son TAM hafta" seçimi için)
ci = 0
for week_end, week_data in weekly_groups:
    if len(week_data) < 2:
        continue
    week_len[week_data.index[0]] = len(week_data)
    avg = week_data.mean()
    x_days = (week_data.index - week_data.index[0]).days.values.astype(float)
    if x_days.std() == 0:
        continue
    slope, intercept = np.polyfit(x_days, week_data.values, 1)
    trend = slope * x_days + intercept

    week_start = week_data.index[0]
    week_label = f"{week_start.strftime('%d %b %y')}"
    color = palette[ci]
    ci += 1
    weekly_summary.append((week_label, avg, slope * 7, color, week_start))

    fig.add_trace(go.Scatter(
        x=week_data.index, y=trend,
        name=f"<b>{week_label}</b>  ·  avg %{avg:.1f}  ·  {slope*7:+.2f}%/hf",
        line=dict(color=color, width=3.2),
        showlegend=False,
        hovertemplate=(f"<b>Hafta: {week_label}</b><br>"
                       f"Trend: %{{y:.2f}}<br>"
                       f"Haftalık avg: %{avg:.2f}<br>"
                       f"Eğim: {slope*7:+.2f}%/hf<extra></extra>"),
    ))

    mid_idx = len(week_data) // 2
    if mid_idx < len(week_data):
        mid_date = week_data.index[mid_idx]
        fig.add_annotation(
            x=mid_date.to_pydatetime(), y=avg,
            text=f"<b>%{avg:.1f}</b>",
            showarrow=False,
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=color, borderwidth=1.2, borderpad=3,
            font=dict(size=10, color=color, family="Arial Black"),
            yshift=14,
        )

ts_ir = iran_war.value // 10**6
fig.add_shape(type="line", xref="x", yref="paper",
              x0=ts_ir, x1=ts_ir, y0=0, y1=1,
              line=dict(color="#ea580c", width=2.5, dash="dash"),
              layer="below")
fig.add_trace(go.Scatter(
    x=[None], y=[None],
    name="📍 İran-ABD Savaşı (28.02.2026)",
    line=dict(color="#ea580c", width=2.5, dash="dash"),
    mode="lines",
))
fig.add_trace(go.Scatter(
    x=[None], y=[None],
    name="<i>Renkli kalın çizgiler: haftalık linear regression trendi</i>",
    line=dict(color="#64748b", width=3),
    mode="lines",
))

fig.add_hline(y=0, line=dict(color="rgba(15,23,42,0.5)", width=1.2, dash="dot"))

fig.update_xaxes(
    showgrid=True, gridcolor="rgba(15,23,42,0.08)",
    minor=dict(showgrid=True, gridcolor="rgba(15,23,42,0.03)",
               ticks="outside", ticklen=3, dtick=86400000 * 7),
    tickformat="%d %b\n%Y",
    dtick="M1",
    tickfont=dict(size=11, color="#1e293b"),
    range=[display_start.to_pydatetime(), display_end.to_pydatetime()],
    ticks="outside", ticklen=5,
    showline=True, linecolor="#94a3b8",
)

fig.update_yaxes(
    title_text="<b>1 Haftalık Devalüasyon (%, yıllıklandırılmış ACT/365)</b>",
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
        text="<b>USDTRY 1H Devalüasyon, yıllıklandırılmış (ACT/365) — YTD Haftalık Trend</b>"
             f"<br><sub>YTD: {display_start.strftime('%d.%m.%Y')} – {display_end.strftime('%d.%m.%Y')} · "
             f"Toplam {len(weekly_summary)} haftalık segment · "
             "Her haftaya ait linear regression trendi · Etiket üstünde haftalık avg</sub>",
        font=dict(size=16, color="#0f172a"),
        x=0.02, xanchor="left", y=0.97,
    ),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#fafbfc",
    font=dict(color="#1e293b", family="Arial"),
    hovermode="closest",
    legend=dict(
        orientation="h",
        yanchor="top", y=-0.14,
        xanchor="center", x=0.5,
        bgcolor="rgba(255,255,255,0.98)",
        bordercolor="#cbd5e1", borderwidth=1,
        font=dict(size=11, color="#1e293b"),
        itemwidth=70,
    ),
    margin=dict(l=90, r=80, t=80, b=110),
    height=750,
    autosize=True,
)

print("\nHaftalık özet:")
print(f"{'Hafta Başlangıç':<18}{'Avg (%)':>12}{'Eğim (%/hf)':>16}")
print("-" * 46)
for label, avg, slope_w, _, _ in weekly_summary:
    print(f"{label:<18}{avg:>12.2f}{slope_w:>16.2f}")

print(f"\nToplam {len(weekly_summary)} haftalık segment")

# Sayfa metni için özet (ozet_uret.py birleştirir): segment sayısı, son TAM hafta
# (5 gözlemli) ortalaması/eğimi, en yüksek ortalamalı hafta. Elle yazılmaz.
import json as _json
_hepsi = [(l, a, sw, ws) for (l, a, sw, _, ws) in weekly_summary]
# "Son tam hafta": 5 iş günü gözlemi olan son hafta (içinde bulunulan yarım hafta
# ortalaması ve eğimi yanıltır)
_tam = [t for t in _hepsi if week_len.get(t[3], 0) >= 5] or _hepsi
_son = _tam[-1]
_zirve = max(_hepsi, key=lambda t: t[1])
_json.dump({
    "hafta_segment": len(weekly_summary),
    "hafta_yil": int(_son[3].year),
    "hafta_son_bas": _son[3].strftime("%d.%m.%Y"),
    "hafta_son_ort": round(float(_son[1]), 2),
    "hafta_son_egim": round(float(_son[2]), 1),
    "hafta_zirve_bas": _zirve[3].strftime("%d.%m.%Y"),
    "hafta_zirve_ort": round(float(_zirve[1]), 1),
}, open(os.path.join(BASE_DIR, "istatistik_hafta.json"), "w"), ensure_ascii=False, indent=1)

output_html = os.path.join(BASE_DIR, "usdtry_weekly_trends.html")
fig.write_html(output_html, include_plotlyjs="cdn",
               config={"responsive": True, "displaylogo": False})
print(f"\nHTML kaydedildi: {output_html}")

try:
    output_png = os.path.join(BASE_DIR, "usdtry_weekly_trends.png")
    fig.write_image(output_png, width=1800, height=850, scale=2)
    print(f"PNG kaydedildi: {output_png}")
except Exception as e:
    print(f"PNG yazma hatasi (HTML etkilenmez): {e}")
