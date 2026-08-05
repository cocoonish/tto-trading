"""TCMB Net Rezerv günlük grafiği (Plotly).

Varsayılan olarak gunluk.csv + haftalik_rezerv.csv'den (çevrimdışı) koşar;
EVDS/PDF'ten taze veri çekmek için --online verin.

Kullanım:
  python grafik.py                          # CSV'lerden (çevrimdışı)
  python grafik.py --online                 # EVDS + IRFCL PDF'ten çek
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

# Ev paleti (site/src/styles/global.css ile uyumlu)
TEAL = "#1d5c5c"      # birincil seri
BORDO = "#8e1f2f"     # ikincil / negatif
ALTIN = "#9a7327"     # vurgu
TEAL_RGBA = "rgba(29,92,92,0.7)"
BORDO_RGBA = "rgba(142,31,47,0.7)"


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
        TEAL_RGBA if (v is not None and v >= 0) else BORDO_RGBA
        for v in delta_round.fillna(0)
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Sol eksen — Swap Hariç Net Rezerv (çizgi; yüzlerce günlük noktada
    # marker basmak çizgiyi kalınlaştırıp okunmaz yapıyor → sadece çizgi).
    # connectgaps=False: swap düzeltmesinin gerçek verisi olmayan aralıklar
    # (ilk IRFCL gözleminden önce / son gözlemden çok sonra) boş kalır.
    fig.add_trace(
        go.Scatter(
            x=daily.index,
            y=sh_round,
            mode="lines",
            name="Swap Hariç Net Rezerv",
            line=dict(color=TEAL, width=2),
            connectgaps=False,
            hovertemplate="Swap Hariç: <b>%{y:.2f}</b> mlr USD<extra></extra>",
        ),
        secondary_y=False,
    )

    # IRFCL gözlem noktaları: swap düzeltmesinin (II.2+II.3) YAYIMLANMIŞ
    # olduğu tarihler. Aradaki günlerde düzeltme iki gözlem arasında ara
    # değerle taşınıyor — okuyucu gerçek/ara değer ayrımını görsün diye
    # işaretleniyor.
    if "swap_gozlem" in daily.columns:
        gozlem_idx = daily.index[daily["swap_gozlem"].astype(bool)]
    else:
        gozlem_idx = daily.index[[]]
    if len(gozlem_idx):
        fig.add_trace(
            go.Scatter(
                x=gozlem_idx,
                y=sh_round.reindex(gozlem_idx),
                mode="markers",
                name="IRFCL gözlemi (swap verisi yayımlandı)",
                marker=dict(color=ALTIN, size=8, symbol="diamond",
                            line=dict(color="white", width=1)),
                hovertemplate="IRFCL gözlemi: <b>%{y:.2f}</b> mlr USD"
                              "<extra></extra>",
            ),
            secondary_y=False,
        )

    # Sağ eksen — günlük değişim (bar). Metin etiketi basılmaz (kalabalık);
    # değer hover'da %{text} ile gösterilir.
    fig.add_trace(
        go.Bar(
            x=daily.index,
            y=delta_round,
            text=delta_text,
            textposition="none",
            name="Günlük Değişim",
            marker_color=bar_colors,
            opacity=0.6,
            hovertemplate="Δ: <b>%{text}</b> mlr USD<extra></extra>",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left",
                   font=dict(size=16)),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.12,
                    xanchor="left", x=0),
        bargap=0.15,
        margin=dict(l=70, r=70, t=90, b=90),
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
    ap.add_argument("--start", default=None,
                    help="gg-aa-yyyy; çevrimdışı modda verilmezse tüm CSV")
    ap.add_argument("--end", default=None)
    ap.add_argument("--output", default="tcmb_rezerv_grafik.html")
    ap.add_argument("--online", action="store_true",
                    help="EVDS + IRFCL PDF'ten taze veri çek "
                         "(varsayılan: gunluk.csv/haftalik_rezerv.csv)")
    ap.add_argument("--csv-daily", default="gunluk.csv")
    ap.add_argument("--csv-weekly", default="haftalik_rezerv.csv")
    ap.add_argument("--no-open", action="store_true",
                    help="dosyayı tarayıcıda açma")
    args = ap.parse_args()

    burasi = Path(__file__).resolve().parent
    csv_d = (burasi / args.csv_daily)
    csv_w = (burasi / args.csv_weekly)

    if not args.online and csv_d.exists() and csv_w.exists():
        # --- Çevrimdışı: net_rezerv.py'nin yazdığı CSV'lerden ---
        daily = pd.read_csv(csv_d, index_col=0, parse_dates=True)
        weekly = pd.read_csv(csv_w, index_col=0, parse_dates=True)
        if args.start:
            daily = daily.loc[dt.datetime.strptime(args.start, "%d-%m-%Y"):]
        if args.end:
            daily = daily.loc[:dt.datetime.strptime(args.end, "%d-%m-%Y")]
        # Son gerçek IRFCL gözlemi (swap düzeltmesinin en taze yayımlandığı gün)
        if "swap_gozlem" in daily.columns:
            gzm = daily.index[daily["swap_gozlem"].astype(bool)]
        else:
            gzm = daily.index[[]]
        pdf_d = f"{gzm[-1]:%d.%m.%Y}" if len(gzm) else "-"
    else:
        # --- Çevrimiçi: EVDS + IRFCL PDF ---
        from net_rezerv import (
            calculate_daily_net_reserves,
            calculate_weekly_net_reserves,
            fetch_evds,
            fetch_latest_weekly_pdf,
            gozlem_arsivine_ekle,
            parse_weekly_pdf,
            swap_duzeltme_serisi,
            swap_gozlem_maskesi,
            swap_gozlemleri,
        )
        start = args.start or "01-01-2026"
        end = args.end or dt.date.today().strftime("%d-%m-%Y")
        raw = fetch_evds(start, end)

        swap_pdf = parse_weekly_pdf(fetch_latest_weekly_pdf())
        gozlem_arsivine_ekle(swap_pdf)

        # Swap düzeltmesi: EVDS aylık IRFCL + haftalık gözlem arşivi + canlı PDF
        gozlem = swap_gozlemleri(start, end, swap_pdf)
        swap_duz = swap_duzeltme_serisi(gozlem, raw.index)
        swap_gzm = swap_gozlem_maskesi(gozlem, raw.index)

        weekly = calculate_weekly_net_reserves(raw, swap_duz)
        daily = calculate_daily_net_reserves(raw, swap_duz, swap_gzm)
        pdf_d = f"{swap_pdf['tarih']:%d.%m.%Y}" if "tarih" in swap_pdf else "-"

    # Başlıktaki "son" değer: swap hariç serinin son GEÇERLİ noktası (seri
    # son IRFCL gözleminden 3 hafta sonra NaN'a düştüğü için sona bakmak yetmez)
    gecerli = daily["swap_haric_net_rezerv_usd"].dropna()
    last = daily.loc[gecerli.index[-1]] if len(gecerli) else daily.iloc[-1]
    title = (
        f"TCMB Swap Hariç Net Uluslararası Rezerv — Günlük"
        f"<br><sup>Son: {last.name:%d %b %Y} | "
        f"Swap Hariç: {last['swap_haric_net_rezerv_usd']:.2f} mlr$ | "
        f"son IRFCL gözlemi: {pdf_d}</sup>"
    )

    fig = build_figure(daily, weekly, title)
    out = Path(args.output).resolve()
    fig.write_html(out, include_plotlyjs="cdn")
    print(f"Grafik kaydedildi: {out}")

    if not args.no_open:
        webbrowser.open(out.as_uri())


if __name__ == "__main__":
    main()
