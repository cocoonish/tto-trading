#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hazine ihraç sistemi — web çıktıları (yalnız CSV/JSON okur; tek istisna:
ihrac_usd için yfinance'ten USD/TRY kuru çekilir, erişilemezse o grafik atlanır).

Girdi (aynı klasörde):
  - hazine_ihale_verileri.csv     : ihale bazında tam veri (faiz, fiyat, teklif…)
  - hazine_vade_analizi.csv       : aylık ağırlıklı ortalama vade
  - hazine_hedef_gerceklesme.csv  : aylık hedef vs gerçekleşen borçlanma
  - .strategy_history.json        : strateji dokümanı bazında hedef revizyonları
  - hazine_planlanan_ihaleler.csv : planlanan takvim + tahmin kolonları
  - hazine_tahmin_dogrulama.csv   : backtest (tahmin vs gerçekleşen, ihale bazında)

Çıktı (aynı klasöre) — dashboard.py'deki panellerin statik web karşılıkları:
  - planlanan_ihraclar.html : ihale bazında beklenen net satış + aylık hedef kıyası
  - tahmin_dogrulama.html   : tahmin vs gerçekleşen scatter + y=x + MAE/MAPE
  - ihrac_hacmi.html        : aylık ihraç hacmi senet türü kırılımı + tür payları
  - ihrac_usd.html          : aylık ihraç hacmi (milyar USD) + USD/TRY kuru
  - ihrac_tempo.html        : çeyreklik ihraç trendi + aylık ihale sayısı
  - faiz_gelisimi.html      : bileşik faiz gelişimi + teklif vs kesilen faiz
  - talep_analizi.html      : bid-to-cover serisi + ihale kabul oranı
  - fiyat_araligi.html      : son 50 ihalede fiyat bandı (min–ort–maks)
  - vade_dagilimi.html      : vade heatmap (yıl×ay) + çeyrek bazında dağılım
  - strateji_revizyon.html  : ay bazında strateji hedef revizyonları + kümülatif
  - tahmin_aylik.html       : backtest aylık toplam — gerçek vs üç tahmin modeli

Site standardı: include_plotlyjs='cdn', beyaz zemin, lejant altta yatay,
başlık solda, Türkçe etiketler, legendgroup kullanılmaz.
"""

import json
import os
from pathlib import Path

import numpy as np
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
    "Kuponsuz Devlet Tahvili": GRI,
}

# Reel getirili seri — nominal maliyet ortalamasına katılmaz
REEL_TIPLER = {"TÜFE'ye Endeksli Devlet Tahvili"}

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


# ================================================================
# ORTAK VERİ YÜKLEYİCİ
# ================================================================
def ihale_verisi() -> pd.DataFrame:
    """Ana ihale CSV'sini yükler ve türetilmiş kolonları ekler."""
    df = pd.read_csv(KOK / "hazine_ihale_verileri.csv", encoding="utf-8-sig")
    df["tarih"] = pd.to_datetime(df["İhale Tarihi"], format="%d.%m.%Y",
                                 errors="coerce")
    df = df.dropna(subset=["tarih"]).sort_values("tarih").reset_index(drop=True)
    df["ay"] = df["tarih"].dt.to_period("M")
    df["ceyrek"] = df["tarih"].dt.to_period("Q").astype(str)
    df["b2c"] = np.where(df["Toplam(Gerçekleşme)"] > 0,
                         df["Toplam(Teklif)"] / df["Toplam(Gerçekleşme)"],
                         np.nan)
    return df


def _panel_baslik_stili(fig: go.Figure) -> None:
    """make_subplots panel başlıklarını ev stiline çeker."""
    for a in fig.layout.annotations:
        a.font = dict(size=13, color=INK)


TR_AY_SIRA = {
    "Ocak": 1, "Şubat": 2, "Mart": 3, "Nisan": 4, "Mayıs": 5, "Haziran": 6,
    "Temmuz": 7, "Ağustos": 8, "Eylül": 9, "Ekim": 10, "Kasım": 11, "Aralık": 12,
}


def _ay_yil_sirala(s: str) -> tuple:
    """'Haziran 2026' → (2026, 6)."""
    parca = str(s).split()
    if len(parca) == 2 and parca[0] in TR_AY_SIRA:
        try:
            return (int(parca[1]), TR_AY_SIRA[parca[0]])
        except ValueError:
            pass
    return (0, 0)


# ================================================================
# 3) AYLIK İHRAÇ HACMİ — SENET TÜRÜ KIRILIMI + PAY
# ================================================================
def ihrac_hacmi() -> dict:
    df = ihale_verisi()
    aylik = (df.groupby(["ay", "Senet Tanımı"])["Toplam(Gerçekleşme)"]
             .sum().unstack(fill_value=0.0) / 1000.0)  # milyar TL
    pay = aylik.div(aylik.sum(axis=1), axis=0) * 100
    x = aylik.index.to_timestamp()
    sira = aylik.sum().sort_values(ascending=False).index
    toplam_pay = aylik.sum() / aylik.values.sum() * 100

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.6, 0.4], shared_xaxes=True,
        vertical_spacing=0.16,
        subplot_titles=("Aylık ihraç hacmi — senet türü kırılımı (milyar TL)",
                        "Senet türlerinin aylık pay dağılımı (%)"),
    )
    for tip in sira:
        renk = TIP_RENK.get(tip, GRI)
        fig.add_trace(go.Bar(
            x=x, y=aylik[tip].round(2),
            name=f"{tip} (dönem payı %{tr(float(toplam_pay[tip]))})",
            marker_color=renk,
            hovertemplate=f"{tip}: %{{y:.1f}} milyar TL<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Bar(
            x=x, y=pay[tip].round(1), marker_color=renk, showlegend=False,
            hovertemplate=f"{tip}: %{{y:.1f}}%<extra></extra>",
        ), row=2, col=1)

    fig.update_layout(barmode="relative")
    ortak_stil(fig, "Hazine ihraçları — aylık hacim ve senet türü kırılımı")
    _panel_baslik_stili(fig)
    fig.update_yaxes(title_text="Milyar TL", row=1, col=1)
    fig.update_yaxes(title_text="Pay (%)", range=[0, 100], row=2, col=1)

    fig.write_html(KOK / "ihrac_hacmi.html", include_plotlyjs="cdn")
    return {
        "ihale_adet": len(df),
        "donem": (df["tarih"].min().strftime("%d.%m.%Y"),
                  df["tarih"].max().strftime("%d.%m.%Y")),
        "toplam_mlr": float(aylik.values.sum()),
        "tip_pay": {t: round(float(v), 1) for t, v in toplam_pay.items()},
    }


# ================================================================
# 4) AYLIK İHRAÇ HACMİ USD + USD/TRY KURU
# ================================================================
def _bayat_sil(yol) -> None:
    """Üretilemeyen bir figürün ESKİ dosyasını sil.

    Bir grafik bu koşuda çizilemediyse, önceki koşudan kalan dosya sitede
    durmaya devam eder ve üstünde tarih yazmadığı için taze görünür. Depoda
    aynı kural El Niño küresel bloğunda da işliyor.
    """
    try:
        if os.path.exists(yol):
            os.remove(yol)
            print(f"  · bayat {os.path.basename(str(yol))} silindi")
    except OSError as e:
        print(f"  ! bayat dosya silinemedi: {e}")


def _kur_evds() -> dict[str, float]:
    """USD/TRY ay sonu kuru — EVDS (TP.DK.USD.A.YTL), deponun KENDİ kaynağı.

    Neden yfinance birincil değil: 'USDTRY=X' bu koşuculardan yalnız altı aylık
    ve YANLIŞ bir seri döndürüyordu (son kur 32,89 — yılların gerisi). Grafik
    yine de çiziliyor, koşu yeşil bitiyordu; kusur ancak sayfaya bir sayı
    bağlanmak istendiğinde görüldü. Depoda zaten anahtarlı, günlük ve 2005
    öncesine uzanan bir USD/TRY serisi var (USDTRYDeval hattı); doğru kaynak o.
    Anahtar arama sırası TEK KAYNAKTAN gelsin diye o hattın evds_ortak'ı
    içe aktarılıyor — burada ikinci bir kopyası tutulmuyor.
    """
    import sys
    kardes = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "USDTRYDeval")
    if kardes not in sys.path:
        sys.path.insert(0, kardes)
    from evds_ortak import evds_anahtari, EVDS_BASE, EVDS_ILERI_GUN  # type: ignore
    from urllib.parse import urlencode
    import requests

    bitis = (pd.Timestamp.today() + pd.Timedelta(days=EVDS_ILERI_GUN)).strftime("%d-%m-%Y")
    params = {"series": "TP.DK.USD.A.YTL", "startDate": "01-01-2000",
              "endDate": bitis, "type": "json"}
    r = requests.get(f"{EVDS_BASE}/{urlencode(params)}",
                     headers={"key": evds_anahtari()}, timeout=45)
    r.raise_for_status()
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError("EVDS boş döndü")
    d = pd.DataFrame(items)
    d["Tarih"] = pd.to_datetime(d["Tarih"].astype(str), format="%d-%m-%Y")
    d["v"] = pd.to_numeric(d["TP_DK_USD_A_YTL"], errors="coerce")
    d = d.dropna(subset=["v"]).sort_values("Tarih").set_index("Tarih")["v"]
    ay = d.resample("ME").last()
    return {pd.Timestamp(t).strftime("%Y-%m"): float(v) for t, v in ay.items() if pd.notna(v)}


def _kur_yfinance() -> dict[str, float]:
    import yfinance as yf
    h = yf.Ticker("USDTRY=X").history(period="max", interval="1d")
    if h.empty:
        raise RuntimeError("boş kur serisi")
    kur = h["Close"].resample("ME").last()
    return {pd.Timestamp(t).strftime("%Y-%m"): float(v)
            for t, v in kur.items() if pd.notna(v)}


def ihrac_usd() -> dict | None:
    kurlar, kaynak = {}, ""
    for ad, cek in (("EVDS", _kur_evds), ("yfinance", _kur_yfinance)):
        try:
            kurlar = cek()
            kaynak = ad
            print(f"  ihrac_usd: kur kaynağı {ad} — {len(kurlar)} ay, "
                  f"son {max(kurlar)} {kurlar[max(kurlar)]:.2f}")
            break
        except Exception as e:
            print(f"  ! ihrac_usd: {ad} kuru alınamadı ({type(e).__name__}: {str(e)[:80]})")
    if not kurlar:
        print("  ! ihrac_usd atlandı — hiçbir kur kaynağı yanıt vermedi")
        _bayat_sil(KOK / "ihrac_usd.html")
        return None

    df = ihale_verisi()
    aylik = df.groupby("ay")["Toplam(Gerçekleşme)"].sum().reset_index()
    aylik["anahtar"] = aylik["ay"].astype(str)
    aylik["kur"] = aylik["anahtar"].map(kurlar)
    aylik = aylik.dropna(subset=["kur"])
    # KAPSAMA KAPISI. Kur serisi ihale aylarının sonuna yetişmiyorsa grafik
    # doğru görünüp yanlış olur: son çubuk eski bir kurla dolara çevrilir.
    # Böyle bir çıktı yayımlamaktansa çizilmez ve BAYAT DOSYA SİLİNİR —
    # tarihini üstünde taşımayan bayat bir grafik, eksik bir grafikten kötüdür.
    if not len(aylik):
        print("  ! ihrac_usd atlandı — kur ile ihale ayları hiç örtüşmedi")
        _bayat_sil(KOK / "ihrac_usd.html")
        return None
    son_ihale = df["ay"].max()
    son_kur_ay = pd.Period(max(kurlar), freq="M")
    gecikme = (son_ihale.year - son_kur_ay.year) * 12 + (son_ihale.month - son_kur_ay.month)
    if len(aylik) < 12 or gecikme > 2:
        print(f"  ! ihrac_usd atlandı — kur serisi yetersiz "
              f"({len(aylik)} ay, son kur {son_kur_ay}, son ihale {son_ihale}; "
              f"kaynak {kaynak})")
        _bayat_sil(KOK / "ihrac_usd.html")
        return None
    aylik["usd_mlr"] = aylik["Toplam(Gerçekleşme)"] / aylik["kur"] / 1000.0
    x = aylik["ay"].dt.to_timestamp()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=x, y=aylik["usd_mlr"].round(2), name="Aylık ihraç (milyar USD)",
        marker_color=TEAL, opacity=0.85,
        hovertemplate="İhraç: %{y:.2f} milyar USD<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=x, y=aylik["kur"].round(2), name="USD/TRY (ay sonu)",
        mode="lines", line=dict(color=CLARET, width=2),
        hovertemplate="USD/TRY: %{y:.2f}<extra></extra>",
    ), secondary_y=True)

    ortak_stil(fig, "Aylık ihraç hacmi dolar bazında ve USD/TRY kuru")
    fig.update_yaxes(title_text="Milyar USD", secondary_y=False)
    fig.update_yaxes(title_text="USD/TRY", secondary_y=True, showgrid=False)

    fig.write_html(KOK / "ihrac_usd.html", include_plotlyjs="cdn")
    return {
        "ay_adet": len(aylik),
        "toplam_usd_mlr": float(aylik["usd_mlr"].sum()),
        "son_ay_usd_mlr": float(aylik["usd_mlr"].iloc[-1]),
        "son_kur": float(aylik["kur"].iloc[-1]),
        "kur_kaynak": kaynak,
    }


# ================================================================
# 5) İHRAÇ TEMPOSU — ÇEYREKLİK TREND + AYLIK İHALE SAYISI
# ================================================================
def ihrac_tempo() -> dict:
    df = ihale_verisi()
    ceyrek = (df.groupby("ceyrek")["Toplam(Gerçekleşme)"].sum() / 1000.0
              ).reset_index(name="mlr")
    # kategori ekseni yerine tarih ekseni: 27 çeyrek etiketi basılmaz,
    # Plotly otomatik yıl tikleri atar; çeyrek adı hover'da (customdata)
    ceyrek["t"] = pd.PeriodIndex(ceyrek["ceyrek"], freq="Q").to_timestamp()
    sayi = df.groupby("ay").size().reset_index(name="adet")
    x_ay = sayi["ay"].dt.to_timestamp()

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.55, 0.45], vertical_spacing=0.18,
        subplot_titles=("Çeyreklik toplam ihraç (milyar TL)",
                        "Aylık ihale sayısı"),
    )
    fig.add_trace(go.Scatter(
        x=ceyrek["t"], y=ceyrek["mlr"].round(1),
        name="Çeyreklik ihraç", mode="lines+markers",
        line=dict(color=CLARET, width=2.5), marker=dict(size=6),
        fill="tozeroy", fillcolor="rgba(142,31,47,0.08)",
        customdata=ceyrek["ceyrek"],
        hovertemplate="%{customdata}: %{y:.1f} milyar TL<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=x_ay, y=sayi["adet"], name="Aylık ihale sayısı",
        marker_color=SLATE,
        hovertemplate="İhale sayısı: %{y}<extra></extra>",
    ), row=2, col=1)

    ortak_stil(fig, "İhraç temposu — çeyreklik hacim ve ihale sıklığı")
    _panel_baslik_stili(fig)
    fig.update_yaxes(title_text="Milyar TL", row=1, col=1)
    fig.update_yaxes(title_text="Adet", row=2, col=1)

    fig.write_html(KOK / "ihrac_tempo.html", include_plotlyjs="cdn")
    return {
        "ceyrek_adet": len(ceyrek),
        "son_ceyrek": (ceyrek["ceyrek"].iloc[-1], float(ceyrek["mlr"].iloc[-1])),
        "aylik_ort_ihale": float(sayi["adet"].mean()),
    }


# ================================================================
# 6) FAİZ GELİŞİMİ — BİLEŞİK FAİZ + TEKLİF vs KESİLEN
# ================================================================
def faiz_gelisimi() -> dict:
    df = ihale_verisi()
    gcol = "Ortalama Yıllık Bileşik(Gerçekleşme)"
    tcol = "Ortalama Yıllık Bileşik(Teklif)"

    # nominal (sabit getirili) ihraçların hacim ağırlıklı aylık ortalama maliyeti
    nom = df[~df["Senet Tanımı"].isin(REEL_TIPLER)].dropna(subset=[gcol])
    agirlikli = (nom.assign(carpim=nom[gcol] * nom["Toplam(Gerçekleşme)"])
                 .groupby("ay")
                 .agg(pay=("carpim", "sum"), hacim=("Toplam(Gerçekleşme)", "sum")))
    agirlikli["maliyet"] = agirlikli["pay"] / agirlikli["hacim"]

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.58, 0.42], vertical_spacing=0.16,
        subplot_titles=(
            "İhale bazında bileşik faiz (%) — TÜFE'ye endeksliler reel getiri",
            "Teklif edilen vs kesilen ortalama bileşik faiz (%)",
        ),
    )

    sira = df["Senet Tanımı"].value_counts().index
    for tip in sira:
        sub = df[df["Senet Tanımı"] == tip].dropna(subset=[gcol])
        renk = TIP_RENK.get(tip, GRI)
        fig.add_trace(go.Scatter(
            x=sub["tarih"], y=sub[gcol], name=tip, mode="markers",
            marker=dict(size=5, color=renk, opacity=0.6),
            hovertemplate=(f"{tip}<br>%{{x|%d.%m.%Y}} · "
                           "Bileşik: %{y:.2f}%<extra></extra>"),
        ), row=1, col=1)
        sub2 = sub.dropna(subset=[tcol])
        fig.add_trace(go.Scatter(
            x=sub2[tcol], y=sub2[gcol], mode="markers", showlegend=False,
            marker=dict(size=5, color=renk, opacity=0.55),
            customdata=sub2["tarih"].dt.strftime("%d.%m.%Y"),
            hovertemplate=(f"{tip}<br>%{{customdata}}<br>"
                           "Teklif: %{x:.2f}% · Kesilen: %{y:.2f}%"
                           "<extra></extra>"),
        ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=agirlikli.index.to_timestamp(), y=agirlikli["maliyet"].round(2),
        name="Aylık ağırlıklı ort. maliyet (nominal ihraçlar)",
        mode="lines", line=dict(color=INK, width=2.5),
        hovertemplate="Ağırlıklı ort. maliyet: %{y:.2f}%<extra></extra>",
    ), row=1, col=1)

    ust = float(max(df[tcol].max(), df[gcol].max())) * 1.03
    fig.add_trace(go.Scatter(
        x=[0, ust], y=[0, ust], mode="lines", name="y = x (teklif = kesilen)",
        line=dict(color=GRI, width=1.5, dash="dash"), hoverinfo="skip",
    ), row=2, col=1)

    ortak_stil(fig, "Borçlanma maliyeti — bileşik faiz gelişimi",
               hovermode="closest")
    _panel_baslik_stili(fig)
    fig.update_yaxes(title_text="Bileşik faiz (%)", row=1, col=1)
    fig.update_xaxes(title_text="Teklif ortalama bileşik (%)", row=2, col=1)
    fig.update_yaxes(title_text="Kesilen ortalama bileşik (%)", row=2, col=1)

    fig.write_html(KOK / "faiz_gelisimi.html", include_plotlyjs="cdn")
    son = agirlikli.dropna(subset=["maliyet"])
    return {
        "son_ay": str(son.index[-1]),
        "son_ay_maliyet": float(son["maliyet"].iloc[-1]),
        "zirve_maliyet": float(son["maliyet"].max()),
        "zirve_ay": str(son["maliyet"].idxmax()),
    }


# ================================================================
# 7) TALEP ANALİZİ — BID-TO-COVER + KABUL ORANI
# ================================================================
def talep_analizi() -> dict:
    df = ihale_verisi()
    aylik_b2c = (df.groupby("ay")
                 .agg(teklif=("Toplam(Teklif)", "sum"),
                      gercek=("Toplam(Gerçekleşme)", "sum")))
    aylik_b2c["b2c"] = np.where(aylik_b2c["gercek"] > 0,
                                aylik_b2c["teklif"] / aylik_b2c["gercek"],
                                np.nan)
    kabul = df.groupby("ay")["İhale Kabul Oranı (%)"].mean()

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.58, 0.42], vertical_spacing=0.16,
        subplot_titles=(
            "Bid-to-cover: toplam teklif / net satış (ihale bazında)",
            "İhale kabul oranı (%) — kesilen / teklif edilen tutar",
        ),
    )

    sira = df["Senet Tanımı"].value_counts().index
    for tip in sira:
        sub = df[df["Senet Tanımı"] == tip].dropna(subset=["b2c"])
        fig.add_trace(go.Scatter(
            x=sub["tarih"], y=sub["b2c"].round(2), name=tip, mode="markers",
            marker=dict(size=5, color=TIP_RENK.get(tip, GRI), opacity=0.55),
            hovertemplate=(f"{tip}<br>%{{x|%d.%m.%Y}} · "
                           "B/C: %{y:.2f}x<extra></extra>"),
        ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=aylik_b2c.index.to_timestamp(), y=aylik_b2c["b2c"].round(2),
        name="Aylık toplam B/C (Σteklif / Σsatış)",
        mode="lines", line=dict(color=INK, width=2.5),
        hovertemplate="Aylık B/C: %{y:.2f}x<extra></extra>",
    ), row=1, col=1)
    fig.add_hline(y=1.0, line_dash="dash", line_color=CLARET, line_width=1.2,
                  row=1, col=1,
                  annotation_text="1,0x — teklif = satış", annotation_font_size=11,
                  annotation_font_color=CLARET)

    fig.add_trace(go.Scatter(
        x=df["tarih"], y=df["İhale Kabul Oranı (%)"], mode="markers",
        showlegend=False, marker=dict(size=4, color=GRI, opacity=0.4),
        hovertemplate="Kabul: %{y:.1f}%<extra></extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=kabul.index.to_timestamp(), y=kabul.round(1),
        name="Aylık ortalama kabul oranı",
        mode="lines", line=dict(color=SLATE, width=2.5),
        hovertemplate="Aylık ort. kabul: %{y:.1f}%<extra></extra>",
    ), row=2, col=1)

    ortak_stil(fig, "İhale talebi — bid-to-cover ve kabul oranı",
               hovermode="closest")
    _panel_baslik_stili(fig)
    fig.update_yaxes(title_text="Bid-to-cover (x)", row=1, col=1)
    fig.update_yaxes(title_text="Kabul oranı (%)", row=2, col=1)

    fig.write_html(KOK / "talep_analizi.html", include_plotlyjs="cdn")
    son12 = aylik_b2c.tail(12)
    return {
        "b2c_son_ay": float(aylik_b2c["b2c"].iloc[-1]),
        "b2c_son12_ort": float(son12["b2c"].mean()),
        "kabul_son_ay": float(kabul.iloc[-1]),
        "kabul_tum_ort": float(df["İhale Kabul Oranı (%)"].mean()),
    }


# ================================================================
# 8) FİYAT ARALIĞI — SON 50 İHALE
# ================================================================
def fiyat_araligi() -> dict:
    df = ihale_verisi().dropna(subset=[
        "Ortalama Fiyat(Gerçekleşme)", "En Düşük Fiyat(Gerçekleşme)",
        "En Yüksek Fiyat(Gerçekleşme)"]).tail(50).reset_index(drop=True)
    # aynı güne düşen ihaleler ayrışsın diye sıra ekseni + tarih etiketi
    etiket = (df["tarih"].dt.strftime("%d.%m.%Y") + " · "
              + df["Senet Tanımı"].str.replace(" Devlet Tahvili", "", regex=False))
    custom = list(zip(df["ISIN"], df["Senet Tanımı"],
                      df["tarih"].dt.strftime("%d.%m.%Y")))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(df))), y=df["En Yüksek Fiyat(Gerçekleşme)"],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=list(range(len(df))), y=df["En Düşük Fiyat(Gerçekleşme)"],
        name="Min–maks fiyat bandı", mode="lines", line=dict(width=0),
        fill="tonexty", fillcolor="rgba(63,85,115,0.18)", hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=list(range(len(df))), y=df["Ortalama Fiyat(Gerçekleşme)"],
        name="Ortalama kesim fiyatı", mode="lines+markers",
        line=dict(color=CLARET, width=2), marker=dict(size=4),
        customdata=custom,
        hovertemplate=("<b>%{customdata[1]}</b> · %{customdata[2]}<br>"
                       "ISIN: %{customdata[0]}<br>"
                       "Ortalama fiyat: %{y:.3f}<extra></extra>"),
    ))
    fig.update_xaxes(tickmode="array",
                     tickvals=list(range(0, len(df), 5)),
                     ticktext=[etiket[i] for i in range(0, len(df), 5)],
                     tickangle=-40)
    ortak_stil(fig, "Kesim fiyatı aralığı — son 50 ihale", hovermode="x")
    fig.update_yaxes(title_text="Fiyat (100 üzerinden)")

    fig.write_html(KOK / "fiyat_araligi.html", include_plotlyjs="cdn")
    return {"n": len(df),
            "donem": (df["tarih"].iloc[0].strftime("%d.%m.%Y"),
                      df["tarih"].iloc[-1].strftime("%d.%m.%Y"))}


# ================================================================
# 9) VADE DAĞILIMI — HEATMAP + ÇEYREK BAZINDA KUTU GRAFİĞİ
# ================================================================
def vade_dagilimi() -> dict:
    df = ihale_verisi()
    pivot = (df.assign(yil=df["tarih"].dt.year, ayno=df["tarih"].dt.month)
             .groupby(["yil", "ayno"])["Vade (Yıl)"].mean().unstack())
    ay_kisa = ["Oca", "Şub", "Mar", "Nis", "May", "Haz",
               "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.42, 0.58], vertical_spacing=0.16,
        subplot_titles=("Ortalama ihraç vadesi — yıl × ay (yıl cinsinden)",
                        "Çeyrek bazında vade dağılımı — senet türüne göre"),
    )
    fig.add_trace(go.Heatmap(
        z=pivot.values.round(2),
        x=[ay_kisa[int(c) - 1] for c in pivot.columns],
        y=[str(y) for y in pivot.index],
        colorscale=[[0.0, "#f5f0e6"], [0.55, GOLD], [1.0, CLARET]],
        colorbar=dict(title=dict(text="Vade (yıl)", font=dict(size=11)),
                      len=0.32, y=0.86, thickness=12),
        hoverongaps=False,
        hovertemplate="%{y} %{x}: ort. %{z:.2f} yıl<extra></extra>",
    ), row=1, col=1)

    sira = df["Senet Tanımı"].value_counts().index
    for tip in sira:
        sub = df[df["Senet Tanımı"] == tip]
        fig.add_trace(go.Box(
            x=sub["ceyrek"], y=sub["Vade (Yıl)"], name=tip,
            marker_color=TIP_RENK.get(tip, GRI),
            line=dict(width=1.2), marker=dict(size=3), boxpoints=False,
        ), row=2, col=1)

    fig.update_layout(boxmode="group")
    ortak_stil(fig, "İhraçların vade dağılımı — ısı haritası ve çeyreklik kutu grafiği",
               hovermode="closest")
    _panel_baslik_stili(fig)
    fig.update_yaxes(title_text="Vade (yıl)", row=2, col=1)
    # kutu grafiği kategorik çeyrek ekseni ister; 27 kategoride her etiketi
    # basmak yerine tik seyrelt (okunabilirlik kuralı: nticks 12-16)
    fig.update_xaxes(nticks=14, tickangle=-40, row=2, col=1)

    fig.write_html(KOK / "vade_dagilimi.html", include_plotlyjs="cdn")
    return {"yil_adet": len(pivot.index),
            "ort_vade": float(df["Vade (Yıl)"].mean())}


# ================================================================
# 10) STRATEJİ REVİZYONLARI + KÜMÜLATİF GERÇEKLEŞME
# ================================================================
def strateji_revizyon() -> dict:
    hist = json.loads((KOK / ".strategy_history.json").read_text(encoding="utf-8"))
    hedef = pd.read_csv(KOK / "hazine_hedef_gerceklesme.csv", encoding="utf-8-sig")
    hedef = hedef.dropna(subset=["Ay-Yıl"])
    hedef = hedef[hedef["Ay-Yıl"].str.strip() != ""].copy()
    hedef["sira"] = hedef["Ay-Yıl"].map(_ay_yil_sirala)
    hedef = hedef.sort_values("sira").reset_index(drop=True)
    gercek_map = dict(zip(hedef["Ay-Yıl"],
                          hedef["Gerçekleşen Borçlanma (Milyar TL)"]))

    aylar = sorted(hist.keys(), key=_ay_yil_sirala)
    listeler = {}
    for ayk in aylar:
        v = hist[ayk]
        hl = v.get("history") if isinstance(v, dict) else None
        if not hl:
            hl = [{"target": v.get("target", v) if isinstance(v, dict) else v,
                   "source": v.get("source", "") if isinstance(v, dict) else ""}]
        listeler[ayk] = hl
    max_rev = max(len(v) for v in listeler.values())

    OFSET_RENK = {0: CLARET, 1: SLATE, 2: "rgba(154,115,39,0.55)"}
    OFSET_AD = {0: "Son strateji öngörüsü", 1: "Bir önceki strateji",
                2: "İki önceki strateji"}

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.55, 0.45], vertical_spacing=0.18,
        subplot_titles=(
            "Aylık hedefin strateji dokümanları arasındaki revizyonu (milyar TL)",
            "Kümülatif hedef vs gerçekleşen borçlanma (milyar TL)",
        ),
    )

    # --- üst panel: revizyon bar'ları (en eski → en yeni doküman) ---
    for ofset in range(max_rev - 1, -1, -1):
        xs, ys, docs = [], [], []
        for ayk in aylar:
            hl = listeler[ayk]
            idx = len(hl) - 1 - ofset
            if idx < 0:
                continue
            xs.append(ayk)
            ys.append(round(float(hl[idx]["target"]), 1))
            docs.append(hl[idx].get("source", "—"))
        if not xs:
            continue
        fig.add_trace(go.Bar(
            x=xs, y=ys, name=OFSET_AD.get(ofset, f"{ofset} strateji önce"),
            marker_color=OFSET_RENK.get(ofset, GRI),
            customdata=docs,
            hovertemplate="%{customdata}<br>Hedef: %{y:.1f} milyar TL<extra></extra>",
        ), row=1, col=1)

    ger_x = [a for a in aylar if float(gercek_map.get(a, 0) or 0) > 0]
    fig.add_trace(go.Bar(
        x=ger_x, y=[round(float(gercek_map[a]), 1) for a in ger_x],
        name="Gerçekleşen", marker=dict(color="rgba(33,27,18,0.0)",
                                        line=dict(color=INK, width=2)),
        hovertemplate="Gerçekleşen: %{y:.1f} milyar TL<extra></extra>",
    ), row=1, col=1)

    # --- alt panel: kümülatif hedef vs gerçekleşen ---
    kum = hedef.copy()
    kum["kum_hedef"] = kum["Hedef Borçlanma (Milyar TL)"].cumsum()
    kum["kum_gercek"] = kum["Gerçekleşen Borçlanma (Milyar TL)"].cumsum()
    # gelecekteki (henüz sıfır gerçekleşmeli) aylarda gerçekleşen çizgisi kesilir
    son_dolu = kum[kum["Gerçekleşen Borçlanma (Milyar TL)"] > 0].index.max()
    kum.loc[kum.index > son_dolu, "kum_gercek"] = np.nan
    # 79 aylık seride kategori etiketi basılmaz — tarih ekseni, ay adı hover'da
    kum["t"] = kum["sira"].map(
        lambda s: pd.Timestamp(year=s[0], month=s[1], day=1)
        if s != (0, 0) else pd.NaT)

    fig.add_trace(go.Scatter(
        x=kum["t"], y=kum["kum_hedef"].round(1), name="Kümülatif hedef",
        mode="lines", line=dict(color=GOLD, width=2),
        fill="tozeroy", fillcolor="rgba(154,115,39,0.10)",
        customdata=kum["Ay-Yıl"],
        hovertemplate="%{customdata} · Kümülatif hedef: %{y:.0f} milyar TL<extra></extra>",
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=kum["t"], y=kum["kum_gercek"].round(1), name="Kümülatif gerçekleşen",
        mode="lines", line=dict(color=CLARET, width=2.5),
        fill="tozeroy", fillcolor="rgba(142,31,47,0.10)",
        customdata=kum["Ay-Yıl"],
        hovertemplate="%{customdata} · Kümülatif gerçekleşen: %{y:.0f} milyar TL<extra></extra>",
    ), row=2, col=1)

    fig.update_layout(barmode="group")
    ortak_stil(fig, "Strateji hedefleri — revizyon tarihçesi ve kümülatif gerçekleşme")
    _panel_baslik_stili(fig)
    fig.update_yaxes(title_text="Milyar TL", row=1, col=1)
    fig.update_yaxes(title_text="Milyar TL", row=2, col=1)

    fig.write_html(KOK / "strateji_revizyon.html", include_plotlyjs="cdn")

    toplam_hedef = float(hedef["Hedef Borçlanma (Milyar TL)"].sum())
    toplam_gercek = float(hedef["Gerçekleşen Borçlanma (Milyar TL)"].sum())
    return {
        "revizyonlu_ay": len(aylar),
        "toplam_hedef_mlr": toplam_hedef,
        "toplam_gercek_mlr": toplam_gercek,
        "gerceklesme_orani": toplam_gercek / toplam_hedef * 100,
    }


# ================================================================
# 11) BACKTEST — AYLIK TOPLAM: GERÇEK vs ÜÇ TAHMİN MODELİ
# ================================================================
def tahmin_aylik() -> dict:
    df = pd.read_csv(KOK / "hazine_tahmin_dogrulama.csv", encoding="utf-8-sig")
    df["tarih"] = pd.to_datetime(df["İhale Tarihi"], format="%d.%m.%Y")
    df["ay"] = df["tarih"].dt.to_period("M")
    aylik = (df.groupby("ay")
             .agg(g=("Gerçek Gerçekleşme (Milyon TL)", "sum"),
                  ham=("Tahmin-Ham (Milyon TL)", "sum"),
                  duz=("Tahmin-Düzeltilmiş (Milyon TL)", "sum"),
                  strj=("Tahmin-Strateji (Milyon TL)", "sum")) / 1000.0)
    x = aylik.index.to_timestamp()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=aylik["g"].round(1), name="Gerçekleşen (aylık toplam)",
        marker_color="rgba(33,27,18,0.35)",
        hovertemplate="Gerçek: %{y:.1f} milyar TL<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=aylik["duz"].round(1), name="Tahmin — düzeltilmiş model",
        mode="lines", line=dict(color=CLARET, width=2.5),
        hovertemplate="Düzeltilmiş: %{y:.1f} milyar TL<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=aylik["ham"].round(1), name="Tahmin — ham geçmiş ortalaması",
        mode="lines", line=dict(color=TEAL, width=1.8),
        hovertemplate="Ham: %{y:.1f} milyar TL<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=aylik["strj"].round(1), name="Tahmin — saf strateji hedefi",
        mode="lines", line=dict(color=GOLD, width=1.8, dash="dash"),
        hovertemplate="Strateji: %{y:.1f} milyar TL<extra></extra>",
    ))

    ortak_stil(fig, "Backtest aylık toplamlar — gerçek vs üç tahmin modeli")
    fig.update_yaxes(title_text="Milyar TL")

    fig.write_html(KOK / "tahmin_aylik.html", include_plotlyjs="cdn")

    hata = {}
    for k, ad in [("ham", "ham"), ("duz", "duzeltilmis"), ("strj", "strateji")]:
        m = aylik["g"] > 0
        hata[ad] = float(((aylik.loc[m, k] - aylik.loc[m, "g"]).abs()
                          / aylik.loc[m, "g"]).mean() * 100)
    return {"ay_adet": len(aylik), "aylik_mape": hata}


if __name__ == "__main__":
    ciktilar = {
        "planlanan_ihraclar.html": planlanan_ihraclar(),
        "tahmin_dogrulama.html": tahmin_dogrulama(),
        "ihrac_hacmi.html": ihrac_hacmi(),
        "ihrac_usd.html": ihrac_usd(),
        "ihrac_tempo.html": ihrac_tempo(),
        "faiz_gelisimi.html": faiz_gelisimi(),
        "talep_analizi.html": talep_analizi(),
        "fiyat_araligi.html": fiyat_araligi(),
        "vade_dagilimi.html": vade_dagilimi(),
        "strateji_revizyon.html": strateji_revizyon(),
        "tahmin_aylik.html": tahmin_aylik(),
    }
    for ad, bilgi in ciktilar.items():
        print(f"{ad:28s} -> {bilgi}")

    # Figürlerin ölçümlerini DOSYAYA yaz. ozet_uret.py bu dosyayı okuyor
    # (usd_son_ay_mlr oradan geliyor) ama onu yazan kimse yoktu: depodaki
    # grafik_ozet.json 25.08'de elle koşulmuş bir sürümden kalmıştı ve her
    # bulut koşusunda olduğu gibi duruyordu. Yani sayfa, aylar önce ölçülmüş
    # bir kur serisini "canlı" sanarak okuyacaktı — usd_son_ay_mlr'nin bir
    # türlü yazılamamasının sebebi de buydu, kur çekimi düzeldikten sonra bile.
    # Ölü bir bağımlılık, kırık bir bağımlılıktan sinsidir: dosya vardır,
    # okunur, hiçbir şey hata vermez.
    with open(KOK / "grafik_ozet.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in ciktilar.items() if v is not None},
                  f, ensure_ascii=False, indent=1)
    print(f"yazildi: {KOK / 'grafik_ozet.json'}")
