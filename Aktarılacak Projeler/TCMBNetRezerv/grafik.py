"""TCMB Net Rezerv günlük grafiği (Plotly).

Kullanım:
  python grafik.py                          # 2026 başından bugüne
  python grafik.py --start 01-04-2026       # belirli aralık
  python grafik.py --output rezerv.html     # kayıt yolu
  python grafik.py --no-open                # tarayıcıda açma
"""

from __future__ import annotations

import argparse
import datetime as dt
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

pd_notna = pd.notna

from net_rezerv import (
    calculate_daily_net_reserves,
    calculate_weekly_net_reserves,
    fetch_evds,
    fetch_latest_weekly_pdf,
    parse_weekly_pdf,
)


def build_figure(daily, weekly, title: str) -> go.Figure:
    daily = daily.copy()
    if "swap_haric_net_rezerv_usd" not in daily.columns:
        raise RuntimeError("Swap Hariç Net Rezerv kolonu eksik (PDF anchor şart)")
    daily["delta"] = daily["swap_haric_net_rezerv_usd"].diff()

    # 2-decimal'a yuvarlanmış kopyalar (Plotly hovertemplate bazen
    # full-precision floatları gösteriyor — round edilmiş seri en garantili)
    sh_round = daily["swap_haric_net_rezerv_usd"].round(2)
    delta_round = daily["delta"].round(2)
    delta_text = [f"{v:+.2f}" if pd_notna(v) else "" for v in delta_round]

    bar_colors = [
        "rgba(46,204,113,0.85)" if (v is not None and v >= 0)
        else "rgba(231,76,60,0.85)"
        for v in delta_round.fillna(0)
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Sol eksen — Swap Hariç Net Rezerv (çizgi)
    fig.add_trace(
        go.Scatter(
            x=daily.index,
            y=sh_round,
            mode="lines+markers",
            name="Swap Hariç Net Rezerv",
            line=dict(color="#2c3e50", width=2.6),
            marker=dict(size=5),
            hovertemplate="Swap Hariç: <b>%{y:.2f}</b> mlr USD<extra></extra>",
        ),
        secondary_y=False,
    )

    # Cuma anchor noktaları (resmi haftalık değer)
    weekly_in_range = weekly.loc[weekly.index.isin(daily.index)].copy()
    weekly_in_range["sh_resmi"] = (
        sh_round.reindex(weekly_in_range.index)
    )
    if len(weekly_in_range):
        fig.add_trace(
            go.Scatter(
                x=weekly_in_range.index,
                y=weekly_in_range["sh_resmi"],
                mode="markers",
                name="Resmi (Cuma)",
                marker=dict(color="#27ae60", size=11, symbol="diamond",
                            line=dict(color="white", width=1.5)),
                hovertemplate="Resmi: <b>%{y:.2f}</b> mlr USD<extra></extra>",
            ),
            secondary_y=False,
        )

    # Sağ eksen — günlük değişim (bar). text + texttemplate
    fig.add_trace(
        go.Bar(
            x=daily.index,
            y=delta_round,
            text=delta_text,
            name="Günlük Değişim",
            marker_color=bar_colors,
            opacity=0.6,
            hovertemplate="Δ: <b>%{text}</b> mlr USD<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center",
                   font=dict(size=20)),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        bargap=0.15,
        margin=dict(l=70, r=70, t=90, b=60),
        height=620,
    )
    # Sıfır çizgileri her iki eksende aynı yatay seviyede olacak şekilde
    # simetrik aralık (-m, +m). Sıfır oranı = 0.5 ⇒ aynı pixel.
    def sym_range(series, pad=0.08):
        v = series.dropna()
        m = max(abs(float(v.min())), abs(float(v.max()))) * (1 + pad)
        return [-m, m]

    left_range = sym_range(daily["swap_haric_net_rezerv_usd"])
    right_range = sym_range(daily["delta"])

    fig.update_xaxes(title_text="Tarih", showgrid=True, gridcolor="#ecf0f1",
                     hoverformat="%d %b %Y")
    fig.update_yaxes(title_text="Swap Hariç Net Rezerv (milyar USD)",
                     secondary_y=False, range=left_range,
                     showgrid=True, gridcolor="#ecf0f1",
                     zeroline=True, zerolinecolor="#7f8c8d", zerolinewidth=1.5,
                     hoverformat=".2f")
    fig.update_yaxes(title_text="Günlük Değişim (milyar USD)",
                     secondary_y=True, range=right_range,
                     showgrid=False,
                     zeroline=True, zerolinecolor="#7f8c8d", zerolinewidth=1.5,
                     hoverformat="+.2f")
    return fig


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="01-01-2026")
    ap.add_argument("--end", default=dt.date.today().strftime("%d-%m-%Y"))
    ap.add_argument("--output", default="tcmb_rezerv_grafik.html")
    ap.add_argument("--no-open", action="store_true",
                    help="dosyayı tarayıcıda açma")
    args = ap.parse_args()

    raw = fetch_evds(args.start, args.end)
    weekly = calculate_weekly_net_reserves(raw)

    pdf_bytes, ymd = fetch_latest_weekly_pdf()
    swap_pdf = parse_weekly_pdf(pdf_bytes)
    ii2 = (swap_pdf.get("II_2_acik_M", 0)
           + swap_pdf.get("II_2_fazla_M", 0)) / 1000.0
    ii3 = swap_pdf.get("II_3_toplam_M", 0) / 1000.0
    sh_anchor = {d: r["net_rezerv_usd"] + ii2 + ii3
                 for d, r in weekly.iterrows()}

    daily = calculate_daily_net_reserves(raw, sh_anchor)

    pdf_d = f"{ymd[6:8]}.{ymd[4:6]}.{ymd[:4]}"
    last = daily.iloc[-1]
    title = (
        f"TCMB Swap Hariç Net Uluslararası Rezerv — Günlük"
        f"<br><sup>Son: {last.name:%d %b %Y} | "
        f"Swap Hariç: {last['swap_haric_net_rezerv_usd']:.2f} mlr$ | "
        f"IRFCL anchor: {pdf_d}</sup>"
    )

    fig = build_figure(daily, weekly, title)
    out = Path(args.output).resolve()
    fig.write_html(out, include_plotlyjs="cdn")
    print(f"Grafik kaydedildi: {out}")

    if not args.no_open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
