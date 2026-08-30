#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kredi tweetinin grafikleri — depodaki ölçülmüş seriden, PNG.

Kaynak: Aktarılacak Projeler/Kredi/data/metrik_haftalik.csv (kredi hattının
işlenmiş çıktısı; kur etkisinden arındırılmış, 13 hafta yıllıklandırılmış).
Çıktı: tweet/ozel/cikti/kredi-buyume.png · kredi-segment.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
CSV = KOK / "Aktarılacak Projeler" / "Kredi" / "data" / "metrik_haftalik.csv"
CIKTI = Path(__file__).resolve().parent / "ozel" / "cikti"

INK = "#1a1a1a"
CLARET = "#7a1f2b"
MAVI = "#365f91"
GRI = "#8a8a8a"


def _eksen(ax):
    for k in ("top", "right"):
        ax.spines[k].set_visible(False)
    ax.grid(axis="y", linewidth=0.4, alpha=0.35)
    ax.tick_params(labelsize=9, colors=INK)


def buyume(df: pd.DataFrame) -> None:
    son3y = df.tail(156)
    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    for kolon, ad, renk, kalin in (
            ("g_ar_13y", "Toplam", INK, 2.2),
            ("g_tuketici_13y", "Tüketici", CLARET, 1.6),
            ("g_ticari_13y", "Ticari", MAVI, 1.6)):
        ax.plot(son3y["tarih"], son3y[kolon], label=ad, color=renk,
                linewidth=kalin)
        son = son3y[kolon].dropna().iloc[-1]
        ax.annotate(f"%{son:.1f}".replace(".", ","),
                    (son3y["tarih"].iloc[-1], son),
                    textcoords="offset points", xytext=(6, -3),
                    fontsize=9, color=renk, fontweight="bold")
    _eksen(ax)
    ax.set_title("Kredi büyümesi — kur etkisinden arındırılmış, "
                 "13 hafta yıllıklandırılmış (%)",
                 fontsize=12, loc="left", color=INK, pad=12)
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    son_tarih = son3y["tarih"].iloc[-1].strftime("%d.%m.%Y")
    fig.text(0.01, 0.01, f"Veri: TCMB haftalık bülteni · {son_tarih} haftası",
             fontsize=8, color=GRI)
    fig.tight_layout()
    fig.savefig(CIKTI / "kredi-buyume.png", facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def segment(df: pd.DataFrame) -> None:
    son = df.iloc[-1]
    kalemler = [
        ("Kurumsal kart", son["g_kurumsal_kart_13y"]),
        ("Tüketici", son["g_tuketici_13y"]),
        ("İhtiyaç", son["g_ihtiyac_13y"]),
        ("Konut", son["g_konut_13y"]),
        ("KOBİ", son["g_kobi_13y"]),
        ("Ticari", son["g_ticari_13y"]),
        ("Taşıt", son["g_tasit_13y"]),
    ]
    kalemler.sort(key=lambda x: x[1])
    adlar = [k for k, _ in kalemler]
    degerler = [v for _, v in kalemler]
    renkler = [CLARET if v >= 0 else MAVI for v in degerler]

    fig, ax = plt.subplots(figsize=(9, 5), dpi=200)
    cubuklar = ax.barh(adlar, degerler, color=renkler, height=0.62)
    for c, v in zip(cubuklar, degerler):
        x = c.get_width()
        if x >= 0:
            ax.annotate(f"%{v:.1f}".replace(".", ","),
                        (x, c.get_y() + c.get_height() / 2),
                        xytext=(5, 0), textcoords="offset points",
                        va="center", ha="left", fontsize=9, color=INK)
        else:
            # Negatif çubukta etiket İÇERİDE: dışına konunca eksendeki
            # segment adının üstüne biniyordu (ilk çizimde görüldü).
            ax.annotate(f"%{v:.1f}".replace(".", ","),
                        (x, c.get_y() + c.get_height() / 2),
                        xytext=(6, 0), textcoords="offset points",
                        va="center", ha="left", fontsize=9,
                        color="white", fontweight="bold")
    ax.axvline(0, color=INK, linewidth=0.8)
    toplam = son["g_ar_13y"]
    ax.axvline(toplam, color=GRI, linewidth=1, linestyle="--")
    ax.text(0.99, 0.03, f"kesikli çizgi: toplam %{toplam:.1f}".replace(".", ","),
            transform=ax.transAxes, ha="right", fontsize=8.5, color=GRI)
    _eksen(ax)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", linewidth=0.4, alpha=0.35)
    ax.set_title("Segment bazında kredi büyümesi — kur etkisinden arındırılmış, "
                 "13 hafta yıllıklandırılmış (%)",
                 fontsize=12, loc="left", color=INK, pad=12)
    son_tarih = son["tarih"].strftime("%d.%m.%Y")
    fig.text(0.01, 0.01, f"Veri: TCMB haftalık bülteni · {son_tarih} haftası",
             fontsize=8, color=GRI)
    fig.tight_layout()
    fig.savefig(CIKTI / "kredi-segment.png", facecolor="white",
                bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    df = pd.read_csv(CSV, parse_dates=["tarih"])
    df = df.dropna(subset=["g_ar_13y"])
    CIKTI.mkdir(parents=True, exist_ok=True)
    buyume(df)
    segment(df)
    print(f"çizildi: {CIKTI}/kredi-buyume.png · kredi-segment.png "
          f"(son hafta {df['tarih'].iloc[-1].date()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
