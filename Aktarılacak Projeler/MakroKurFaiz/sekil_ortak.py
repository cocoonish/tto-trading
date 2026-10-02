#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — figürlerin ortak yardımcıları (renkler, biçim, yazım).

Her bölümün figürleri `sekil_bNN.py`dedir; `sekil.py` onları kaydeder ve çizer.
Sayıların tamamı `veri/olcum.json`dan gelir.

Ders yayımlandığı günün metnidir; figürler de o günün ölçümünü dondurur ve
statik yola yazılır (`site/public/arastirma/makro-kur-ve-faiz/`). Her figür
kendi tarih aralığını kendi alt başlığında taşır. Her HTML, çizildiği ölçüm
dosyasının sha256 özünü bir meta etiketinde taşır (`tto-olcum-ozu`);
ölçüm dosyası değişip figür yeniden çizilmezse doğrulayıcı düşer.

"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
OLCUM = BURASI / "veri" / "olcum.json"

try:                                   # çizim kütüphanesi çizim yolunun bağımlılığıdır
    import plotly.graph_objects as go  # (kapı yolu `dogrula.py` onu istemez)
    from plotly.subplots import make_subplots
except ImportError:                    # pragma: no cover
    go = None

SLUG = "makro-kur-ve-faiz"
CIKTI = KOK / "site" / "public" / "arastirma" / SLUG
PLOTLY_JS = "/js/plotly-4.0.0.min.js"
MUREKKEP, CLARET, MAVI, GRI, TURUNCU, YESIL = "#1a1a1a", "#8c2f39", "#2f5d8c", "#8a8a8a", "#b8860b", "#3a7d44"
ACIK_MAVI, ACIK_CLARET = "rgba(47,93,140,0.16)", "rgba(140,47,57,0.14)"


def vir(x: float, b: int = 2) -> str:
    """Site sözleşmesi: ondalık virgül, eksi U+2212, binlik nokta."""
    s = f"{x:,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return s.replace("-", "−")


def yuzde(x: float, b: int = 2, arti: bool = False) -> str:
    """Yüzde işareti önde; işaret yüzdeden de önce: −%0,86 · +%1,78."""
    isaret = "−" if x < 0 else ("+" if arti and x > 0 else "")
    return f"{isaret}%{vir(abs(x), b)}"


def tarih(gun: str) -> str:
    y, a, g = gun[:10].split("-")
    return f"{g}.{a}.{y}"


def ay(gun: str) -> str:
    y, a, _ = gun[:10].split("-")
    return f"{a}.{y}"


def olcum_ozu() -> str:
    return hashlib.sha256(OLCUM.read_bytes()).hexdigest()


def _yaz(fig, ad: str, yukseklik: int = 500) -> None:
    fig.update_layout(
        height=yukseklik, margin=dict(l=64, r=28, t=96, b=78),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        title=dict(x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor="#d8d4cc", ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    html = fig.to_html(include_plotlyjs=PLOTLY_JS, full_html=True,
                       config={"displayModeBar": False, "responsive": True})
    html = html.replace("<head>", f'<head><meta name="tto-olcum-ozu" content="{olcum_ozu()}">', 1)
    (CIKTI / ad).write_text(html, encoding="utf-8")
    print(f"  ✓ {(CIKTI / ad).relative_to(KOK)}")
