import os
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlencode
from datetime import date
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
from evds_ortak import evds_anahtari, EVDS_ILERI_GUN, EVDS_BASE, usdtry_serisi

# Çıktılar script'in kendi klasörüne yazılır (taşınmaya dayanıklı)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Tarih parametreleri (her çalıştırmada bugüne kadar güncellenir) ---
today = date.today()
# EVDS sorgu bitişi bilerek birkaç gün ileri alınır: TCMB, ertesi iş gününün gösterge
# kurunu bugün öğleden sonra yayımlar. endDate=bugün olduğunda o kur sistematik olarak
# dışarıda kalır (tazelik kaybı). Gelecek tarih için EVDS zaten veri döndürmez —
# ileri almak zararsızdır, yalnız yayımlanmış olanı alır.
fetch_end = (pd.Timestamp(today) + pd.Timedelta(days=EVDS_ILERI_GUN)).strftime("%d-%m-%Y")
fetch_start = "01-02-2024"  # EVDS geçmiş veri başlangıcı
range_1y_start = pd.Timestamp("2025-03-01")  # 1Y grafik sabit başlangıç


def fmt_range(start: pd.Timestamp, end: pd.Timestamp) -> str:
    """Grafik başlıkları için tarih aralığı metni."""
    return f"{start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"

EVDS_KEY = evds_anahtari()


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


def fetch_evds_opt(series_code: str, start: str, end: str):
    """Faiz katmanı için opsiyonel çekim: EVDS hata verirse None döner, grafik deval'siz kalmaz."""
    try:
        return fetch_evds(series_code, start, end)
    except Exception as e:
        print(f"  UYARI: {series_code} cekilemedi ({type(e).__name__}: {e}); bu seri grafikten cikarildi.")
        return None


print(f"Veri aralığı: {fetch_start} – {fetch_end} (bugün: {today})")
print("EVDS'den veriler cekiliyor...")
usdtry = usdtry_serisi(fetch_start)
tlref = fetch_evds_opt("TP.BISTTLREF.ORAN", fetch_start, fetch_end)
kredi = fetch_evds_opt("TP.KTF101", fetch_start, fetch_end)
mev_1m = fetch_evds_opt("TP.TRYTAS.MT01", fetch_start, fetch_end)
mev_3m = fetch_evds_opt("TP.TRYTAS.MT02", fetch_start, fetch_end)
mev_6m = fetch_evds_opt("TP.TRYTAS.MT03", fetch_start, fetch_end)
mev_12m = fetch_evds_opt("TP.TRYTAS.MT04", fetch_start, fetch_end)
print(f"  USD/TRY: {len(usdtry)}, TLREF: {0 if tlref is None else len(tlref)}, "
      f"Kredi: {0 if kredi is None else len(kredi)}")

# Grafik penceresi bugünle değil VERİYLE biter: EVDS ertesi iş gününün kurunu önceden
# yayımladığında o gözlem de eksene girsin (aksi hâlde filt() onu geri kırpardı).
display_end = max(pd.Timestamp(usdtry.index[-1]), pd.Timestamp(today))
range_3m_start = display_end - pd.Timedelta(days=90)
range_6m_start = display_end - pd.Timedelta(days=180)
print(f"  Son gözlem tarihi: {usdtry.index[-1].date()} (grafik sonu: {display_end.date()})")

usdtry_full = usdtry.asfreq("D").interpolate(method="time")
business = usdtry_full[usdtry_full.index.dayofweek < 5]


def deval_act365(s: pd.Series, n: int) -> pd.Series:
    """Yıllıklandırılmış devalüasyon, ACT/365 takvim günü tabanı.

    Pencere n GÖZLEM (iş günü) geriye gider; üs ise iki gözlem tarihinin
    GERÇEK takvim günü farkı Δd üzerinden hesaplanır:
        oran = (P_t / P_{t-n}) ** (365 / Δd) - 1
    Sabit 252/n (iş günü) üssü kullanılmaz.
    """
    ratio = s / s.shift(n)
    delta_d = pd.Series(s.index, index=s.index).diff(n).dt.days.astype(float)
    return (ratio ** (365.0 / delta_d) - 1) * 100


w_d, m_d, q_d = 5, 21, 63
deval_1w = deval_act365(business, w_d)
deval_1m = deval_act365(business, m_d)
deval_3m = deval_act365(business, q_d)

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
        x=d1w.index, y=d1w.values, name="Deval 1H",
        line=dict(color=C["deval_1w"], width=1.2, dash="dot"),
        opacity=0.7,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>1H (ACT/365): %{y:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=d1m.index, y=d1m.values, name="Deval 1A",
        line=dict(color=C["deval_1m"], width=2.2),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>1A (ACT/365): %{y:.1f}%<extra></extra>",
    ))

    fig.add_trace(go.Scatter(
        x=d3m.index, y=d3m.values, name="Deval 3A",
        line=dict(color=C["deval_3m"], width=3),
        hovertemplate="<b>%{x|%d %b %Y}</b><br>3A (ACT/365): %{y:.1f}%<extra></extra>",
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
            hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{name}: %{{y:.2f}}%<extra></extra>",
        ))

    if tlref is not None:
        tl = filt(tlref, start)
        fig.add_trace(go.Scatter(
            x=tl.index, y=tl.values, name="TLREF",
            line=dict(color=C["tlref"], width=3.2),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>TLREF: %{y:.2f}%<extra></extra>",
        ))

    buf = pd.Timedelta(days=14)
    if kredi is not None:
        kr = filt(kredi, start - buf)
        fig.add_trace(go.Scatter(
            x=kr.index, y=kr.values, name="İht. Kredisi",
            line=dict(color=C["kredi"], width=2),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Kredi: %{y:.2f}%<extra></extra>",
        ))

    for series, name, key, dash in [
        (mev_1m, "Mevduat 1 Ay", "mev_1m", "solid"),
        (mev_3m, "Mevduat 3 Ay", "mev_3m", "solid"),
        (mev_6m, "Mevduat 6 Ay", "mev_6m", "solid"),
        (mev_12m, "Mevduat 12 Ay", "mev_12m", "solid"),
    ]:
        if series is None:
            continue
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
            showlegend=False, name="📍 İmamoğlu Tutuklanması (19.03.2025)",
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
            showlegend=False, name="📍 İran-ABD Savaşı (28.02.2026)",
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
        title_text="<b>Oran (% yıllıklandırılmış, ACT/365)</b>",
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
            borderwidth=0,
            font=dict(size=11, color=C["text"]),
            itemwidth=30,
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
        x=d1w.index, y=d1w.values, name="Deval 1H",
        line=dict(color=C["deval_1w"], width=1.0, dash="dot"),
        opacity=0.45,
        hovertemplate="<b>%{x|%d %b %Y}</b><br>1H: %{y:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=d1m.index, y=d1m.values, name="Deval 1A",
        line=dict(color=C["deval_1m"], width=1.4),
        opacity=0.55,
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

    # Sayfa metnindeki rejim tablosu bu eğimlerden okunur (ozet.json'a akar);
    # elle yazılmaz. Anahtarlar: seg_pre / seg_orta / seg_son (_egim, _bas, _son).
    seg_ist = {}
    seg_anahtar = {"Pre-İmamoğlu": "seg_pre", "İmamoğlu→Savaş": "seg_orta",
                   "Post-Savaş": "seg_son"}
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
            if series_name == "1A":
                k = seg_anahtar[label]
                seg_ist[f"{k}_egim"] = round(float(slope * 30), 1)
                seg_ist[f"{k}_bas"] = seg.index[0].strftime("%d.%m.%Y")
                seg_ist[f"{k}_son"] = seg.index[-1].strftime("%d.%m.%Y")
            label_with_slope = f"{series_name} | {label} ({slope*30:+.1f}%/ay)"
            fig.add_trace(go.Scatter(
                x=idx, y=trend,
                name=label_with_slope,
                line=dict(color=color, width=3 if series_name == "1A" else 2.2, dash=dash),
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
        showlegend=False, name="📍 İmamoğlu (19.03.2025)",
        line=dict(color=C["imamoglu"], width=2.5, dash="dash"),
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        showlegend=False, name="📍 İran-ABD Savaşı (28.02.2026)",
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
        title_text="<b>Devalüasyon (% yıllıklandırılmış, ACT/365)</b>",
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
            borderwidth=0,
            font=dict(size=11, color=C["text"]),
            itemwidth=30,
        ),
        margin=dict(l=80, r=80, t=70, b=180),
        height=560,
        autosize=True,
    )
    build_segmented_trend_figure.seg_ist = seg_ist
    return fig


fig_seg = build_segmented_trend_figure()

# Her figür ayrı, standart tek-figure HTML çıktısı (özel sarmalayıcı yok).
# usdtry_deval.html = ana figür (Son 1 Yıl) → site/public/projeler/usdtry-deval/ altına kopyalanır.
FIG_OUTPUTS = [
    (fig_1y, "usdtry_deval.html"),
    (fig_3m, "usdtry_deval_3m.html"),
    (fig_6m, "usdtry_deval_6m.html"),
    (fig_seg, "usdtry_deval_seg.html"),
]
for fig, fname in FIG_OUTPUTS:
    path = os.path.join(BASE_DIR, fname)
    fig.write_html(path, include_plotlyjs="cdn",
                   config={"responsive": True, "displaylogo": False})
    print(f"HTML kaydedildi: {path}")

# Son değer özeti (log/rapor için)
last_dt = deval_3m.dropna().index[-1]
# Rejim eğimleri sayfa metni için (ozet_uret.py birleştirir)
try:
    import json as _json
    _json.dump(build_segmented_trend_figure.seg_ist,
               open(os.path.join(BASE_DIR, "istatistik_seg.json"), "w"),
               ensure_ascii=False, indent=1)
except Exception as _e:
    print(f"istatistik_seg.json yazılamadı: {_e}")

print(f"\nSon gözlem ({last_dt.date()}): "
      f"1H {deval_1w.dropna().iloc[-1]:+.2f}% · "
      f"1A {deval_1m.dropna().iloc[-1]:+.2f}% · "
      f"3A {deval_3m.dropna().iloc[-1]:+.2f}%  (yıllıklandırılmış, ACT/365)")

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

    output_png = os.path.join(BASE_DIR, "usdtry_deval_plotly.png")
    combined.save(output_png)
    print(f"Birlestirilmis PNG: {output_png}")
except Exception as e:
    print(f"PNG yazma hatasi: {e}")
