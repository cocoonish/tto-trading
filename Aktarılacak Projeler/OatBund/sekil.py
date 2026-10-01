#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND (02.10.2026) — analiz figürleri.

Bu bir HAT DEĞİL, tek bir analizin çizim katmanı. Analiz yayımlandığı günün
metnidir (karar 08.09.2026); figürler de o günün ölçümünü dondurur ve
`site/public/analiz/<slug>/` altına yazılır — hat figürleri gibi tazelenmez,
sayfa damgası basmaz, her figür kendi tarihini kendi alt başlığında taşır.

GİRDİ TEK YERDEN: `veri/olcum.json` (`olcum.py` üretir). Figür ile metin iki
ayrı hesaptan beslenseydi bir gün sessizce ayrışırdı.

Biçim: ondalık virgül, binlik nokta, eksi U+2212 (`separators`); plotly
başlığı sarmaz, taşırır — alt yazı `_sar` ile bölünür. Renk: üç kategorik
slot (bordo Fransa, mavi, kehribar) doğrulayıcıdan geçti (CVD ΔE ≥ 12,4,
normal görüş ≥ 18,1, kontrast ≥ 3:1); bağlam serileri etiketli gri. Çift
y eksenli grafik yok: iki ölçek iki alt panele bölünür.

Fonksiyon adı = yazıdaki şekil numarası = dosya adının öneki = figürün içindeki
"Şekil NN" başlığı (dogrula.py bunları sorar).

  python3 sekil.py
"""
from __future__ import annotations

import json
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
try:                                   # çizim kütüphanesi çizim yolunun bağımlılığıdır;
    import plotly.graph_objects as go  # kapı yolu (dogrula.py) onu istemez
    from plotly.subplots import make_subplots
except ImportError:                    # pragma: no cover
    go = None

SLUG = "oat-bund-2026-10-02"
CIKTI = KOK / "site" / "public" / "analiz" / SLUG
PLOTLY_JS = "/js/plotly-4.0.0.min.js"
MUREKKEP, CLARET, MAVI, KEHRIBAR, GRI, ACIK = (
    "#1a1a1a", "#a8304f", "#2766b0", "#a8741a", "#8a8a8a", "#d8d4cc")
SEKILLER = ["01_tarihce", "02_yil", "03_akranlar", "04_egri", "05_epizotlar",
            "06_kayan", "07_atif", "08_gun_ici", "09_ileri"]
SATIR = 100
AYLAR = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
         "Eylül", "Ekim", "Kasım", "Aralık"]


def vir(x: float, b: int = 1, isaret: bool = False) -> str:
    s = f"{abs(x):,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (isaret and x > 0 and not sifir) else s


def yuz(x: float, b: int = 2, isaret: bool = False) -> str:
    """Yüzde önde, işaret onun da önünde: −%0,55 (sitenin biçim sözleşmesi)."""
    g = vir(abs(x), b)
    sifir = float(g.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return f"−%{g}"
    return f"+%{g}" if (isaret and x > 0 and not sifir) else f"%{g}"


TR_AY_KISA = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]


def tarih(t: str) -> str:
    return f"{int(t[8:10])} {AYLAR[int(t[5:7])]} {t[:4]}"


def tarih_k(t: str) -> str:
    return f"{t[8:10]}.{t[5:7]}.{t[:4]}"


def _sar(metin: str, n: int = SATIR) -> str:
    satirlar, s = [], ""
    for k in metin.split(" "):
        if s and len(s) + 1 + len(k) > n:
            satirlar.append(s)
            s = k
        else:
            s = f"{s} {k}" if s else k
    satirlar.append(s)
    return "<br>".join(satirlar)


def _baslik(fig, no: str, metin: str, alt: str) -> None:
    alt_s = _sar(alt).replace("<br>", "</sub><br><sub>")
    fig.update_layout(title=dict(text=f"{_sar(f'Şekil {no} — {metin}', 90)}<br><sub>{alt_s}</sub>"))


def _yaz(fig, ad: str, yukseklik: int = 480) -> None:
    satir = (fig.layout.title.text or "").count("<br>") + 1
    fig.update_layout(
        height=yukseklik, margin=dict(l=64, r=28, t=40 + 21 * satir, b=74), separators=",.",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        title=dict(x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="top", y=-0.14, x=0),
        hoverlabel=dict(bgcolor="white", font=dict(color=MUREKKEP)),
    )
    fig.update_xaxes(showgrid=False, linecolor=ACIK, ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    fig.write_html(CIKTI / f"{ad}.html", include_plotlyjs=PLOTLY_JS, full_html=True,
                   config={"displayModeBar": False, "responsive": True})
    print(f"  ✓ {(CIKTI / (ad + '.html')).relative_to(KOK)}")


# ─────────────────────────────────────────────────────────────── 01
def sekil01(o: dict) -> None:
    s, it = o["seriler"]["spread"], o["seriler"]["spread_it"]
    sv = o["seviye"]
    f = go.Figure()
    f.add_trace(go.Scatter(x=it["t"], y=it["v"], name="İtalya − Almanya", line=dict(color=GRI, width=1),
                           hovertemplate="%{x}: %{y:,.1f} bp<extra>İtalya</extra>"))
    f.add_trace(go.Scatter(x=s["t"], y=s["v"], name="Fransa − Almanya", line=dict(color=CLARET, width=2),
                           hovertemplate="%{x}: %{y:,.1f} bp<extra>Fransa</extra>"))
    f.add_annotation(x=sv["tarihi_zirve_gun"], y=sv["tarihi_zirve"],
                     text=f"{tarih(sv['tarihi_zirve_gun'])}: {vir(sv['tarihi_zirve'])} bp",
                     showarrow=True, arrowhead=0, ax=60, ay=-10, font=dict(size=12))
    f.add_annotation(x=sv["gun"], y=sv["spread"], text=f"{tarih(sv['gun'])}: {vir(sv['spread'])} bp",
                     showarrow=True, arrowhead=0, ax=-150, ay=-95, font=dict(size=12, color=CLARET),
                     bgcolor="white")
    f.update_yaxes(title="baz puan", range=[-20, 420])
    f.update_xaxes(tickformat="%Y")
    _baslik(f, "01", f"Fransa'nın 10 yıllık farkı {tarih(sv['son_gorulme'])}'den beri en yüksek",
            "Fransa ve İtalya 10 yıllık gösterge getirisinin Almanya'nınkinden farkı, baz puan · "
            "günlük Avrupa kapanışı (Paris 17:30) · 2000–2026 · İtalya'nın 2011–12 zirvesi ölçeği "
            "kırpmasın diye eksen 420 bp'de kesildi.")
    _yaz(f, "01_tarihce", 470)


# ─────────────────────────────────────────────────────────────── 02
OLAYLAR = []  # (gün, kısa etiket) — doğrulanmış olgu defterinden yazıyla birlikte doldurulur


def sekil02(o: dict) -> None:
    s, it = o["seriler"]["spread"], o["seriler"]["spread_it"]
    bas = "2026-01-01"
    st = [(t, v) for t, v in zip(s["t"], s["v"]) if t >= bas]
    itt = [(t, v) for t, v in zip(it["t"], it["v"]) if t >= bas]
    f = go.Figure()
    f.add_trace(go.Scatter(x=[a for a, _ in itt], y=[b for _, b in itt], name="İtalya − Almanya",
                           line=dict(color=MAVI, width=1.6), hovertemplate="%{x}: %{y:,.1f} bp<extra>İtalya</extra>"))
    f.add_trace(go.Scatter(x=[a for a, _ in st], y=[b for _, b in st], name="Fransa − Almanya",
                           line=dict(color=CLARET, width=2.2), hovertemplate="%{x}: %{y:,.1f} bp<extra>Fransa</extra>"))
    ust = max(b for _, b in st) * 1.12
    for i, (gun, etiket) in enumerate(OLAYLAR):
        f.add_vline(x=gun, line=dict(color=ACIK, width=1, dash="dot"))
        f.add_annotation(x=gun, y=ust * (0.98 if i % 2 == 0 else 0.90), text=etiket, showarrow=False,
                         xanchor="left", font=dict(size=10, color="#555"))
    fi = o["fransa_italya"]
    aylar = [f"2026-{m:02d}-01" for m in range(1, 11)]
    f.update_xaxes(tickvals=aylar, ticktext=[TR_AY_KISA[int(a[5:7])] for a in aylar])
    f.update_yaxes(title="baz puan", range=[0, ust])
    _baslik(f, "02", f"2026: Fransa {tarih(fi['kesintisiz_bas'])}'ten beri İtalya'dan pahalı borçlanıyor",
            "10 yıllık gösterge getirisinin Almanya'ya farkı, baz puan · günlük Avrupa kapanışı · "
            f"1 Ocak – {tarih(o['son_gun'])} · kesikli çizgiler metindeki olay takvimi.")
    _yaz(f, "02_yil", 500)


# ─────────────────────────────────────────────────────────────── 03
def sekil03(o: dict) -> None:
    a = list(reversed(o["akranlar"]))
    ad = [r["ad"] for r in a]
    f = go.Figure()
    for r in a:
        f.add_trace(go.Scatter(x=[r["haziran"], r["spread"]], y=[r["ad"], r["ad"]], mode="lines",
                               line=dict(color=ACIK, width=3), showlegend=False, hoverinfo="skip"))
    f.add_trace(go.Scatter(x=[r["haziran"] for r in a], y=ad, mode="markers", name="30 Haziran 2026",
                           marker=dict(color=GRI, size=10), hovertemplate="%{y}: %{x:,.1f} bp<extra>30 Haziran</extra>"))
    f.add_trace(go.Scatter(x=[r["spread"] for r in a], y=ad, mode="markers+text", name=tarih(o["son_gun"]),
                           marker=dict(color=[CLARET if r["ulke"] == "fr" else MAVI for r in a], size=12),
                           text=[f"{vir(r['spread'])}" for r in a], textposition="middle right",
                           textfont=dict(size=11), hovertemplate="%{y}: %{x:,.1f} bp<extra>1 Ekim</extra>"))
    f.update_xaxes(title="Almanya'ya fark, baz puan", range=[0, max(r["spread"] for r in a) * 1.15])
    _baslik(f, "03", "Fransa, euro bölgesinin en geniş farkını taşıyor — Yunanistan ve İtalya'dan da geniş",
            "10 yıllık gösterge getirisinin Almanya'ya farkı · gri: 30 Haziran 2026, renkli: veri günü "
            "(Portekiz ve Yunanistan için kaynağın son kotasyonu 30 Eylül) · Avrupa kapanışı.")
    _yaz(f, "03_akranlar", 470)


# ─────────────────────────────────────────────────────────────── 04
def sekil04(o: dict) -> None:
    e = o["egri"]
    vade = ["2", "5", "10", "30"]
    f = go.Figure()
    f.add_trace(go.Bar(x=[f"{v} yıl" for v in vade], y=[e[v]["zirve"] for v in vade], name="15 Kasım 2011 (zirve)",
                       marker_color=ACIK, text=[vir(e[v]["zirve"]) for v in vade], textposition="outside"))
    f.add_trace(go.Bar(x=[f"{v} yıl" for v in vade], y=[e[v]["spread"] - e[v]["degisim_haziran"] for v in vade],
                       name="30 Haziran 2026", marker_color=MAVI,
                       text=[vir(e[v]["spread"] - e[v]["degisim_haziran"]) for v in vade], textposition="outside"))
    f.add_trace(go.Bar(x=[f"{v} yıl" for v in vade], y=[e[v]["spread"] for v in vade], name=tarih(o["son_gun"]),
                       marker_color=CLARET, text=[vir(e[v]["spread"]) for v in vade], textposition="outside"))
    f.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    f.update_yaxes(title="baz puan")
    _baslik(f, "04", "Açılma eğrinin her vadesinde; 2 yıllıkta bir günde "
            f"{vir(e['2']['degisim_1g'])} bp",
            "Fransa gösterge getirisinin aynı vadeli Almanya göstergesine farkı, baz puan · Avrupa kapanışı · "
            "2011 sütunları her vadenin o günkü (15 Kasım 2011) değeri.")
    _yaz(f, "04_egri", 470)


# ─────────────────────────────────────────────────────────────── 05
VURGU = {"2026": CLARET, "2011 euro bölgesi borç krizi": MAVI, "2024 meclisin feshi": KEHRIBAR}


def sekil05(o: dict) -> None:
    y = o["seriler"]["epizot_yollari"]
    f = go.Figure()
    for ad, yol in y.items():
        renk = VURGU.get(ad, GRI)
        f.add_trace(go.Scatter(x=list(range(len(yol))), y=yol, name=ad,
                               line=dict(color=renk, width=2.4 if ad in VURGU else 1),
                               opacity=1 if ad in VURGU else 0.7,
                               hovertemplate=f"{ad}<br>%{{x}}. iş günü: %{{y:+,.1f}} bp<extra></extra>"))
    f.add_hline(y=0, line=dict(color=ACIK, width=1))
    f.update_xaxes(title="başlangıçtan bu yana iş günü")
    f.update_yaxes(title="başlangıca göre fark değişimi, baz puan")
    f.update_layout(legend=dict(y=-0.24))
    _baslik(f, "05", "Bu epizot 2011'den bu yana en büyük açılma",
            "Fransa–Almanya 10 yıllık farkının epizot başlangıcına göre değişimi, baz puan · başlangıç günleri "
            "metindeki epizot tablosundan · 160 iş günü.")
    _yaz(f, "05_epizotlar", 580)


# ─────────────────────────────────────────────────────────────── 06
def sekil06(o: dict) -> None:
    k = o["seriler"]["kayan"]
    f = go.Figure()
    f.add_trace(go.Scatter(x=k["t"] + k["t"][::-1], y=k["ust"] + k["alt"][::-1], fill="toself",
                           fillcolor="rgba(168,48,79,0.13)", line=dict(width=0), name="±2 standart hata",
                           hoverinfo="skip"))
    f.add_trace(go.Scatter(x=k["t"], y=k["spr"], name="10 bp açılmanın kura etkisi",
                           line=dict(color=CLARET, width=2),
                           hovertemplate="%{x}: %{y:+,.2f} (yüzde)<extra></extra>"))
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1))
    kk = o["kayan"]
    f.update_yaxes(title="EUR/USD'de haftalık değişim, %", ticksuffix="")
    _baslik(f, "06", f"Euronun Fransa farkına duyarlılığı bugün 10 bp başına {yuz(kk['son'])}",
            "104 haftalık kayan pencere: haftalık EUR/USD log değişimi (ECB 14:15 kuru) = sabit + "
            "b₁·Δ(ABD−Almanya 2y) + b₂·Δ(OAT–Bund 10y); çizgi b₂×10 · gölge Newey–West ±2 s.h. · "
            f"2013–2019 ortalaması {yuz(kk['ort_2013_2019'])}, 2024 sonrası {yuz(kk['ort_2024_sonra'])}.")
    _yaz(f, "06_kayan", 470)


# ─────────────────────────────────────────────────────────────── 07
def sekil07(o: dict) -> None:
    a = o["atif"]["2026-08-26"]
    adlar = ["Ölçülen", "OAT–Bund kanalı", "Faiz farkı kanalı", "Sabit", "Açıklanamayan"]
    deg = [a["kur_gercek"], a["spread_payi"], a["faiz_payi"], a["sabit_payi"], a["artik"]]
    renk = [MUREKKEP, CLARET, MAVI, GRI, ACIK]
    f = go.Figure(go.Bar(x=adlar, y=deg, marker_color=renk, text=[yuz(v, 2, True) for v in deg],
                         textposition="outside", hovertemplate="%{x}: %{y:+,.2f} (yüzde)<extra></extra>"))
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1))
    k = a["katsayi"]
    f.update_yaxes(title="EUR/USD değişimi, %")
    _baslik(f, "07", f"{tarih(a['bas'])} – {tarih(a['son'])}: kurun düşüşünün büyük kısmı fark kanalında",
            f"EUR/USD (ECB 14:15) log değişimi ve kanallara atfı · katsayılar epizottan ÖNCE tahmin edildi "
            f"({tarih(k['bas'])}–{tarih(k['son'])}, {k['n']} hafta): 10 bp fark {yuz(k['b']['spr'] * 10)}, "
            f"10 bp faiz farkı {yuz(k['b']['rd'] * 10)} · fark +{vir(a['spr_toplam'])} bp, faiz farkı "
            f"{vir(a['rd_toplam'], 1, True)} bp · istatistiksel atıf, nedensellik değil.")
    _yaz(f, "07_atif", 470)


# ─────────────────────────────────────────────────────────────── 08
def sekil08(o: dict) -> None:
    g = o["seriler"]["gun_ici"]
    f = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.58, 0.42])
    f.add_trace(go.Scatter(x=g["t"], y=g["spr"], name="Fransa − Almanya 10y", line=dict(color=CLARET, width=2),
                           hovertemplate="%{x}: %{y:,.1f} bp<extra>Fransa 10y</extra>"), row=1, col=1)
    f.add_trace(go.Scatter(x=g["t"], y=g["ispr2"], name="İtalya − Almanya 2y", line=dict(color=MAVI, width=1.6),
                           hovertemplate="%{x}: %{y:,.1f} bp<extra>İtalya 2y</extra>"), row=1, col=1)
    f.add_trace(go.Scatter(x=g["t"], y=g["eurusd"], name="EUR/USD", line=dict(color=MUREKKEP, width=1.6),
                           hovertemplate="%{x}: %{y:.4f}<extra>EUR/USD</extra>"), row=2, col=1)
    for s_, et in (("14:15", "ECB kuru 14:15"), ("17:30", "kapanış 17:30")):
        if s_ in g["t"]:
            f.add_vline(x=s_, line=dict(color=GRI, width=1, dash="dot"))
            f.add_annotation(x=s_, y=1.0, yref="paper", text=et, showarrow=False, xanchor="left",
                             yanchor="bottom", font=dict(size=10, color="#555"))
    f.update_yaxes(title_text="baz puan", row=1, col=1)
    f.update_yaxes(title_text="EUR/USD", row=2, col=1)
    f.update_xaxes(title_text="Paris saati", row=2, col=1, nticks=12)
    gi = o["gun_ici"]
    _baslik(f, "08", f"{tarih(o['son_gun'])}: açılma 14:15'ten sonra geldi, euro onunla düştü",
            f"15 dakikalık son kotasyonlar · üst: fark (baz puan), alt: EUR/USD · kesikli: 14:15 (ECB kuru) ve "
            f"17:30 (kapanış) · fark 14:15'te {vir(gi['14:15']['spr'])}, 17:30'da {vir(gi['17:30']['spr'])} bp; "
            f"kur {vir(gi['14:15']['eurusd'], 4)} → {vir(gi['17:30']['eurusd'], 4)}.")
    _yaz(f, "08_gun_ici", 560)


# ─────────────────────────────────────────────────────────────── 09
def sekil09(o: dict) -> None:
    p = o["seriler"]["ileri_noktalar"]
    il = o["ileri"][0]
    f = go.Figure()
    f.add_trace(go.Scatter(x=p["g"], y=p["i"], mode="markers", name="geçmiş gözlemler",
                           marker=dict(color=MAVI, size=8, opacity=0.75),
                           text=[tarih_k(t) for t in p["t"]],
                           hovertemplate="%{text}<br>önceki 22 gün: %{x:+,.1f} bp<br>sonraki 22 gün: %{y:+,.1f} bp<extra></extra>"))
    f.add_vline(x=il["bugunku_acilma"], line=dict(color=CLARET, width=2, dash="dash"))
    f.add_annotation(x=il["bugunku_acilma"], y=max(p["i"]) if p["i"] else 0, text=f" bugün +{vir(il['bugunku_acilma'])} bp",
                     showarrow=False, xanchor="left", font=dict(color=CLARET, size=12))
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1))
    f.update_xaxes(title="önceki 22 iş günündeki açılma, baz puan")
    f.update_yaxes(title="sonraki 22 iş gününde değişim, baz puan")
    _baslik(f, "09", f"Bir ayda 30 bp'den hızlı açılmaların %{vir(il['daha_acildi_payi'], 0)}'ünde fark ertesi ay daha da açıldı",
            f"2000–2026, {il['gozlem']} gözlem, {il['epizot']} ayrı epizot (örtüşen günler bağımsız değildir) · "
            f"sonraki 22 iş günü medyanı {vir(il['medyan'], 1, True)} bp · geçmiş bir dağılımdır, tahmin değildir.")
    _yaz(f, "09_ileri", 480)


def main() -> int:
    if go is None:
        raise SystemExit("plotly yok — çizim için gerekli (kapı yolu bunu istemez)")
    o = json.loads((BURASI / "veri" / "olcum.json").read_text(encoding="utf-8"))
    print(f"OAT–Bund figürleri → {CIKTI.relative_to(KOK)}")
    for i, ad in enumerate(SEKILLER, 1):
        globals()[f"sekil{i:02d}"](o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
