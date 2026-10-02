#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — figürler. Sayıların tamamı `veri/olcum.json`dan gelir.

Ders yayımlandığı günün metnidir; figürler de o günün ölçümünü dondurur ve
statik yola yazılır (`site/public/arastirma/makro-kur-ve-faiz/`). Her figür
kendi tarih aralığını kendi alt başlığında taşır. Her HTML, çizildiği ölçüm
dosyasının sha256 özünü bir meta etiketinde taşır (`tto-olcum-ozu`);
ölçüm dosyası değişip figür yeniden çizilmezse doğrulayıcı düşer.

  python3 sekil.py [01 02 …]          (numara verilmezse hepsi)
  python3 site/tools/plotly_stil.py site/public/arastirma/makro-kur-ve-faiz/*.html
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


# ─────────────────────────────────────────────────────────────── Bölüm 7
def s12_redk(o: dict) -> None:
    b = o["b07"]
    s = b["sekil_12"]
    a = b["p7a"]["tufe"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.64, 0.36], horizontal_spacing=0.10,
                        subplot_titles=("TÜFE bazlı REDK ve dönüş yelpazesi", "Yarı ömür (yıl): kestirim ve %90 aralığı"))
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["redk_tufe"], mode="lines", name="REDK (TÜFE bazlı, 2025=100)",
                             line=dict(color=MAVI, width=2), hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra></extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=[s["tarih"][0], s["fan_tarih"][-1]], y=[s["ortalama_endeks"]] * 2, mode="lines",
                             name=f"1994–2026 ortalaması ({vir(s['ortalama_endeks'], 1)})",
                             line=dict(color=GRI, width=1.4, dash="dash")), 1, 1)
    f = s["fan"]
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["alt90"], mode="lines", line=dict(width=0), showlegend=False,
                             hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["ust90"], mode="lines", line=dict(width=0), fill="tonexty",
                             fillcolor=ACIK_CLARET, name="%90 aralığının yolları (60 ay)", hoverinfo="skip"), 1, 1)
    fig.add_trace(go.Scatter(x=s["fan_tarih"], y=f["mu"], mode="lines", name="medyan-yansız ρ ile sönüm",
                             line=dict(color=CLARET, width=2, dash="dot")), 1, 1)
    fig.update_yaxes(title_text="endeks (artış: TL reel değer kazancı)", row=1, col=1)

    satir = [("1994–2026", a["tam"])] + [(v["etiket"].split(" ")[0], v) for v in a["donemler"].values()]
    tavan = 20.0
    for i, (ad, v) in enumerate(satir):
        mu = v["yari_omur_mu_yil"]
        alt = v["yari_omur_alt90_yil"]
        ust = v["yari_omur_ust90_yil"]
        mu_c = tavan if mu is None else min(mu, tavan)
        ust_c = tavan if (ust is None or v.get("ust_sonsuz")) else min(ust, tavan)
        fig.add_trace(go.Scatter(x=[alt, ust_c], y=[ad, ad], mode="lines", line=dict(color=GRI, width=6),
                                 showlegend=(i == 0), name="%90 aralığı (sağ uç ∞ ise eksen tavanında)",
                                 hoverinfo="skip"), 1, 2)
        fig.add_trace(go.Scatter(x=[mu_c], y=[ad], mode="markers", marker=dict(color=CLARET, size=10),
                                 showlegend=(i == 0), name="medyan-yansız kestirim",
                                 hovertemplate=f"{ad}: {'∞' if mu is None else vir(mu, 1)} yıl<extra></extra>"), 1, 2)
        fig.add_trace(go.Scatter(x=[v["yari_omur_ols_yil"]], y=[ad], mode="markers",
                                 marker=dict(color=MAVI, size=8, symbol="diamond"), showlegend=(i == 0),
                                 name="sıradan en küçük kareler (aşağı yanlı)",
                                 hovertemplate=f"{ad}: {vir(v['yari_omur_ols_yil'], 1)} yıl<extra></extra>"), 1, 2)
    fig.update_xaxes(range=[0, tavan * 1.04], title_text="yıl", row=1, col=2)
    fig.update_yaxes(autorange="reversed", row=1, col=2)
    fig.update_layout(title=dict(text=(
        "Şekil 12 — Türkiye reel efektif kuru: ortalamadan uzak, dönüşü yavaş ve belirsiz"
        f"<br><sub>TCMB REDK (TÜFE bazlı), aylık {ay(s['tarih'][0])}–{ay(s['tarih'][-1])} · yelpaze bugünkü log "
        "sapmanın ρʰ ile sönümü, tahmin değil · aralık benzetimle (medyan-yansız)</sub>")))
    _yaz(fig, "12_redk.html", 540)


# ─────────────────────────────────────────────────────────────── Bölüm 9
def s16_kur_baskisi(o: dict) -> None:
    b = o["b09"]
    s = b["sekil_16"]
    d = b["p9b"]["donemler"]
    fig = make_subplots(rows=2, cols=1, row_heights=[0.66, 0.34], vertical_spacing=0.16,
                        subplot_titles=("Kur baskısı endeksinin aylık bileşenleri (σ birimi)",
                                        "Dönem dönem bileşen payları: cov(bileşen, endeks) / var(endeks)"))
    for ad, renk, etiket in (("kur", MAVI, "kur (TL değer kaybı)"), ("rezerv", CLARET, "rezerv kaybı"),
                             ("faiz", TURUNCU, "fonlama maliyeti artışı")):
        fig.add_trace(go.Bar(x=s["tarih"], y=s[ad], name=etiket, marker_color=renk, marker_line_width=0,
                             hovertemplate="%{x|%m.%Y}: %{y:.2f}<extra>" + etiket + "</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["emp"], mode="lines", name="endeks (toplam)",
                             line=dict(color=MUREKKEP, width=1.2)), 1, 1)
    fig.update_layout(barmode="relative", bargap=0.05)
    fig.update_yaxes(title_text="σ", row=1, col=1)
    adlar = list(d.keys())
    kisa = [a.replace("yönetilen kur (2021-12 … 2023-06)", "yönetilen kur").replace(" (Kasım'a kadar)", "") for a in adlar]
    for ad, renk in (("kur", MAVI), ("rezerv", CLARET), ("faiz", TURUNCU)):
        fig.add_trace(go.Bar(y=kisa, x=[d[a]["pay"][ad] for a in adlar], orientation="h", marker_color=renk,
                             showlegend=False, marker_line_width=0,
                             text=[yuzde(d[a]["pay"][ad] * 100, 0) if d[a]["pay"][ad] >= 0.05 else "" for a in adlar], textposition="inside",
                             insidetextanchor="middle", textfont=dict(color="white", size=11),
                             hovertemplate="%{y}: %{x:.2f}<extra>" + ad + "</extra>"), 2, 1)
    fig.update_xaxes(range=[-0.1, 1.05], title_text="pay", row=2, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)
    fig.update_layout(title=dict(text=(
        "Şekil 16 — Baskı kura mı yazılıyor, rezerve mi, faize mi?"
        f"<br><sub>Haftalık, {tarih(b['p9b']['ilk'])}–{tarih(b['p9b']['son'])} · kur USD/TRY, rezerv TCMB swap hariç net "
        "(brüt rezerve oranla), faiz TCMB ağırlıklı ortalama fonlama maliyeti · ağırlıklar bileşenin σ'sının tersi</sub>")))
    _yaz(fig, "16_kur_baskisi.html", 760)


SEKILLER = {"12": s12_redk, "16": s16_kur_baskisi}


def main(argv: list[str]) -> int:
    if go is None:
        print("plotly yok: figürler çizilemez (kapı yolu bundan etkilenmez)")
        return 1
    o = json.loads(OLCUM.read_text(encoding="utf-8"))
    secim = argv or sorted(SEKILLER)
    for n in secim:
        SEKILLER[n](o)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
