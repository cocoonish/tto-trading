#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hazine ihraç TAHMİN sistemi — web çıktıları (İNTERNETSİZ, yalnız CSV okur).

Girdi (aynı klasörde):
  - hazine_planlanan_ihaleler.csv : planlanan takvim + tahmin kolonları
  - hazine_tahmin_dogrulama.csv   : backtest (tahmin vs gerçekleşen, ihale bazında)

Çıktı (aynı klasöre):
  - planlanan_ihraclar.html : ihale tarihi bazında beklenen net satış (stacked bar)
                              + aylık toplam beklenen vs strateji hedefi (2. panel)
  - tahmin_dogrulama.html   : tahmin vs gerçekleşen scatter + y=x + MAE/MAPE

Site standardı: include_plotlyjs='cdn', beyaz zemin, lejant altta yatay,
başlık solda, Türkçe etiketler.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

KOK = Path(__file__).resolve().parent

# --- ev paleti (site/src/styles/global.css jetonları) ---
CLARET = "#8e1f2f"
CLARET_KOYU = "#6d1322"
TEAL = "#1d5c5c"
GOLD = "#9a7327"
SLATE = "#3f5573"
INK = "#211b12"
GRI = "#8a8171"

TIP_RENK = {
    "Sabit Kuponlu Devlet Tahvili": CLARET,
    "Hazine Bonosu": GOLD,
    "TLREF'e Endeksli Devlet Tahvili": TEAL,
    "Değişken Faizli Devlet Tahvili": SLATE,
    "TÜFE'ye Endeksli Devlet Tahvili": CLARET_KOYU,
}

AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık",
}


def tr(x: float, ondalik: int = 1) -> str:
    """Türkçe sayı biçimi (ondalık virgül, binlik nokta)."""
    s = f"{x:,.{ondalik}f}"
    return s.replace(",", "@").replace(".", ",").replace("@", ".")


def ortak_stil(fig: go.Figure, baslik: str, hovermode: str = "x unified") -> None:
    fig.update_layout(
        title=dict(text=baslik, x=0.02, xanchor="left",
                   font=dict(size=16, color=INK)),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color=INK, size=12.5),
        legend=dict(orientation="h", yanchor="top", y=-0.12,
                    xanchor="left", x=0),
        hovermode=hovermode,
        margin=dict(t=72, r=48, b=96, l=64),
    )
    fig.update_xaxes(gridcolor="#efe9dc", linecolor="#d8cfba",
                     zerolinecolor="#cfc4ab")
    fig.update_yaxes(gridcolor="#efe9dc", linecolor="#d8cfba",
                     zerolinecolor="#cfc4ab")


# ================================================================
# 1) PLANLANAN İHRAÇLAR
# ================================================================
def planlanan_ihraclar() -> dict:
    df = pd.read_csv(KOK / "hazine_planlanan_ihaleler.csv", encoding="utf-8-sig")
    df["tarih"] = pd.to_datetime(df["İhale Tarihi"], format="%d.%m.%Y")

    ihale = df[df["Tahmini Gerçekleşme (Milyon TL)"].notna()].copy()
    dogrudan = df[df["Tahmini Gerçekleşme (Milyon TL)"].isna()]
    ihale["beklenen_mlr"] = ihale["Tahmini Gerçekleşme (Milyon TL)"] / 1000.0
    ihale["teklif_mlr"] = ihale["Tahmini Teklif (Milyon TL)"] / 1000.0

    # aylık toplam beklenen (ihale) vs strateji hedefi
    ihale["ay"] = ihale["tarih"].dt.to_period("M")
    df["ay"] = df["tarih"].dt.to_period("M")
    aylik = (
        ihale.groupby("ay")
        .agg(beklenen=("beklenen_mlr", "sum"))
        .join(df.groupby("ay")["Aylık Strateji Hedefi (Milyar TL)"].first()
              .rename("hedef"))
        .reset_index()
    )
    aylik["etiket"] = aylik["ay"].map(lambda p: f"{AYLAR[p.month]} {p.year}")

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.62, 0.38], vertical_spacing=0.17,
        subplot_titles=(
            "İhale bazında beklenen net satış (milyar TL)",
            "Aylık toplam: beklenen ihale satışı vs strateji hedefi",
        ),
    )

    # --- üst panel: senet tipine göre (aynı günde üst üste yığılı) ---
    kumule: dict = {}  # tarih -> o güne kadar yığılan toplam
    sira = (ihale.groupby("Senet Tanımı")["beklenen_mlr"].sum()
            .sort_values(ascending=False).index)
    for tip in sira:
        sub = ihale[ihale["Senet Tanımı"] == tip].sort_values("tarih")
        taban = [kumule.get(t, 0.0) for t in sub["tarih"]]
        for t, y in zip(sub["tarih"], sub["beklenen_mlr"]):
            kumule[t] = kumule.get(t, 0.0) + y
        custom = list(zip(
            sub["Senet Tanımı"],
            sub["Vade Terimi"],
            sub["İtfa Tarihi"],
            [tr(v) if pd.notna(v) else "—" for v in sub["teklif_mlr"]],
            [tr(v, 2) if pd.notna(v) else "—" for v in sub["Tahmini Bid-to-Cover"]],
            sub["Kıyas Bazı"],
        ))
        fig.add_trace(go.Bar(
            x=sub["tarih"], y=sub["beklenen_mlr"], base=taban,
            offsetgroup="plan", width=86_400_000 * 0.9,
            name=tip, marker_color=TIP_RENK.get(tip, GRI),
            customdata=custom,
            hovertemplate=(
                "<b>%{customdata[0]}</b> — %{customdata[1]}<br>"
                "Beklenen net satış: %{y:.1f} milyar TL<br>"
                "Beklenen teklif: %{customdata[3]} milyar TL "
                "(B/C ≈ %{customdata[4]})<br>"
                "İtfa: %{customdata[2]} · Kıyas: %{customdata[5]}"
                "<extra></extra>"
            ),
        ), row=1, col=1)

    # --- alt panel: aylık hedef vs beklenen ---
    fig.add_trace(go.Bar(
        x=aylik["etiket"], y=aylik["hedef"], offsetgroup="hedef",
        name="Aylık strateji hedefi (toplam borçlanma)",
        marker=dict(color="rgba(154,115,39,0.28)",
                    line=dict(color=GOLD, width=1.5)),
        hovertemplate="Strateji hedefi: %{y:.1f} milyar TL<extra></extra>",
    ), row=2, col=1)
    fig.add_trace(go.Bar(
        x=aylik["etiket"], y=aylik["beklenen"], offsetgroup="beklenen",
        name="Beklenen ihale satışı (toplam)",
        marker_color=INK,
        hovertemplate="Beklenen ihale toplamı: %{y:.1f} milyar TL<extra></extra>",
    ), row=2, col=1)

    # alt panelin başlığına not satırı (alta koymak site stilinde kırpılıyor)
    fig.layout.annotations[1].text = (
        "Aylık toplam: beklenen ihale satışı vs strateji hedefi<br>"
        f"<sup>{len(dogrudan)} doğrudan satış (altın/dolar senetleri, kira "
        "sertifikaları) ihale tahmini dışında; hedef toplam iç borçlanmayı "
        "kapsar</sup>"
    )

    fig.update_layout(barmode="group")
    ortak_stil(fig, "Hazine planlı ihraçlar — beklenen net satış")
    fig.update_yaxes(title_text="Milyar TL", row=1, col=1)
    fig.update_yaxes(title_text="Milyar TL", row=2, col=1)
    fig.update_xaxes(
        tickformat="%d.%m.%Y", row=1, col=1,
        range=[ihale["tarih"].min() - pd.Timedelta(days=2),
               ihale["tarih"].max() + pd.Timedelta(days=2)],
    )
    for a in fig.layout.annotations[:2]:
        a.font = dict(size=13, color=INK)

    fig.write_html(KOK / "planlanan_ihraclar.html", include_plotlyjs="cdn")

    return {
        "ihale_adet": len(ihale),
        "dogrudan_adet": len(dogrudan),
        "toplam_beklenen_mlr": float(ihale["beklenen_mlr"].sum()),
        "aylik": aylik[["etiket", "beklenen", "hedef"]].values.tolist(),
        "donem": (ihale["tarih"].min().strftime("%d.%m.%Y"),
                  ihale["tarih"].max().strftime("%d.%m.%Y")),
    }


# ================================================================
# 2) TAHMİN DOĞRULAMA (backtest)
# ================================================================
def tahmin_dogrulama() -> dict:
    df = pd.read_csv(KOK / "hazine_tahmin_dogrulama.csv", encoding="utf-8-sig")
    df["tarih"] = pd.to_datetime(df["İhale Tarihi"], format="%d.%m.%Y")
    df["gercek_mlr"] = df["Gerçek Gerçekleşme (Milyon TL)"] / 1000.0
    df["tahmin_mlr"] = df["Tahmin-Düzeltilmiş (Milyon TL)"] / 1000.0

    mae_mlr = (df["tahmin_mlr"] - df["gercek_mlr"]).abs().mean()
    mape = df["Tutar Sapma % (düzeltilmiş)"].abs().mean()
    mape_medyan = df["Tutar Sapma % (düzeltilmiş)"].abs().median()
    mape_ham = df["Tutar Sapma % (ham)"].abs().mean()
    mape_str = df["Tutar Sapma % (strateji)"].abs().mean()

    # son 12 ay — güncel rejimdeki performans (2020-21'de strateji hedefleri
    # gerçekçi olmadığından tüm-dönem MAPE'si aşırı şişer)
    son = df[df["tarih"] >= df["tarih"].max() - pd.DateOffset(months=12)]
    mae_son = (son["tahmin_mlr"] - son["gercek_mlr"]).abs().mean()
    mape_son = son["Tutar Sapma % (düzeltilmiş)"].abs().mean()

    fig = go.Figure()

    ust = max(df["gercek_mlr"].max(), df["tahmin_mlr"].max()) * 1.05
    fig.add_trace(go.Scatter(
        x=[0, ust], y=[0, ust], mode="lines", name="y = x (kusursuz tahmin)",
        line=dict(color=GRI, width=1.5, dash="dash"), hoverinfo="skip",
    ))

    stiller = {
        "Aynı tahvil (itfa eşleşmesi)": dict(renk=CLARET, sembol="circle"),
        "Aynı tip + benzer vade": dict(renk=TEAL, sembol="diamond"),
    }
    for kiyas, st in stiller.items():
        sub = df[df["Kıyas Bazı"] == kiyas]
        if sub.empty:
            continue
        custom = list(zip(
            sub["tarih"].dt.strftime("%d.%m.%Y"),
            sub["Senet Tanımı"],
            sub["Tutar Sapma % (düzeltilmiş)"],
        ))
        fig.add_trace(go.Scatter(
            x=sub["gercek_mlr"], y=sub["tahmin_mlr"], mode="markers",
            name=f"{kiyas} (n={len(sub)})",
            marker=dict(color=st["renk"], symbol=st["sembol"], size=7,
                        opacity=0.55, line=dict(width=0.5, color="#ffffff")),
            customdata=custom,
            hovertemplate=(
                "<b>%{customdata[1]}</b> · %{customdata[0]}<br>"
                "Gerçekleşen: %{x:.1f} milyar TL<br>"
                "Tahmin (düzeltilmiş): %{y:.1f} milyar TL<br>"
                "Sapma: %{customdata[2]:.1f}%"
                "<extra></extra>"
            ),
        ))

    donem = (f"{AYLAR[df['tarih'].min().month][:3]} {df['tarih'].min().year} – "
             f"{AYLAR[df['tarih'].max().month][:3]} {df['tarih'].max().year}")
    fig.add_annotation(
        text=(f"<b>Düzeltilmiş model</b> (n = {len(df)} ihale, {donem})<br>"
              f"MAE = {tr(mae_mlr, 2)} milyar TL · MAPE = %{tr(mape)} "
              f"(medyan %{tr(mape_medyan)})<br>"
              f"Son 12 ay (n = {len(son)}): MAE = {tr(mae_son, 2)} milyar TL · "
              f"MAPE = %{tr(mape_son)}<br>"
              f"<span style='color:{GRI}'>Kıyas MAPE — ham: %{tr(mape_ham)} · "
              f"strateji: %{tr(mape_str)}</span>"),
        xref="paper", yref="paper", x=0.02, y=0.98, xanchor="left",
        yanchor="top", showarrow=False, align="left",
        font=dict(size=12, color=INK),
        bgcolor="rgba(255,255,255,0.85)", bordercolor="#d8cfba",
        borderwidth=1, borderpad=6,
    )

    ortak_stil(fig, "Tahmin doğrulama — backtest: tahmin vs gerçekleşen",
               hovermode="closest")
    # x ekseni başlığı eksen altına yazılırsa site stilinde lejantla çakışıyor;
    # plot alanının sağ altına yerleştiriliyor (sol alt veriyle dolu)
    fig.add_annotation(
        text="Gerçekleşen net satış (milyar TL) →",
        xref="x domain", yref="y domain", x=0.99, y=0.03,
        xanchor="right", yanchor="bottom", showarrow=False,
        font=dict(size=12, color=GRI),
    )
    fig.update_xaxes(range=[0, ust])
    fig.update_yaxes(title_text="Tahmin — düzeltilmiş (milyar TL)",
                     range=[0, ust])

    fig.write_html(KOK / "tahmin_dogrulama.html", include_plotlyjs="cdn")

    return {
        "n": len(df), "mae_mlr": float(mae_mlr), "mape": float(mape),
        "mape_medyan": float(mape_medyan),
        "son12ay_n": len(son), "son12ay_mae_mlr": float(mae_son),
        "son12ay_mape": float(mape_son),
        "mape_ham": float(mape_ham), "mape_strateji": float(mape_str),
        "donem": donem,
    }


if __name__ == "__main__":
    p = planlanan_ihraclar()
    d = tahmin_dogrulama()
    print("planlanan_ihraclar.html  ->", p)
    print("tahmin_dogrulama.html    ->", d)
