#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAĞIT VE OIS DERSİ — figürler. Sayıların tamamı `olcum.py`den gelir.

Ders yayımlandığı günün metnidir; figürler de o günün ölçümünü dondurur ve
çıktı statik yola yazılır (`site/public/arastirma/<slug>/`). Özet dosyası
yoktur, GrafikEmbed altyazıya tarih basmaz: her figür kendi tarihini kendi
alt başlığında taşır.

  python3 sekil.py
  python3 site/tools/plotly_stil.py site/public/arastirma/kagit-ve-ois-trading/*.html
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))
import olcum  # noqa: E402

try:                                   # çizim kütüphanesi çizim yolunun bağımlılığıdır
    import plotly.graph_objects as go  # (kapı yolu `dogrula.py` onu istemez)
    from plotly.subplots import make_subplots
except ImportError:                    # pragma: no cover
    go = None

SLUG = "kagit-ve-ois-trading"
CIKTI = KOK / "site" / "public" / "arastirma" / SLUG
PLOTLY_JS = "/js/plotly-4.0.0.min.js"
MUREKKEP, CLARET, MAVI, GRI, TURUNCU, YESIL = "#1a1a1a", "#8c2f39", "#2f5d8c", "#8a8a8a", "#b8860b", "#3a7d44"


def vir(x: float, b: int = 2) -> str:
    """Site sözleşmesi: ondalık virgül, eksi U+2212, binlik nokta."""
    s = f"{x:,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return s.replace("-", "−")


def yuzde(x: float, b: int = 2, arti: bool = False) -> str:
    """Yüzde işareti önde; eksi/artı işareti yüzdeden de önce: −%0,86 · +%1,78."""
    isaret = "−" if x < 0 else ("+" if arti and x > 0 else "")
    return f"{isaret}%{vir(abs(x), b)}"


# Vade ekseni karekök ölçekte: 3 ay ile 6 ay doğrusal eksende üst üste biniyordu.
def kok(t: float) -> float:
    return float(np.sqrt(t))


def _yaz(fig, ad: str, yukseklik: int = 480) -> None:
    fig.update_layout(
        height=yukseklik, margin=dict(l=64, r=28, t=86, b=70),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        title=dict(x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.28, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor="#d8d4cc", ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    fig.write_html(CIKTI / ad, include_plotlyjs=PLOTLY_JS, full_html=True,
                   config={"displayModeBar": False, "responsive": True})
    print(f"  ✓ {(CIKTI / ad).relative_to(KOK)}")


def _tarih(gun: str) -> str:
    y, a, g = gun.split("-")
    return f"{g}.{a}.{y}"


# ─────────────────────────────────────────────────────────────── Bölüm 1
def s01_egri_tasima(o: dict) -> None:
    bg = o["bugun"]
    vade = [0.25, 0.5, 1, 2, 3, 5, 7]
    getiri = [bg["egri"][d] for d in olcum.DUGUM]
    etiket = ["3a", "6a", "1y", "2y", "3y", "5y", "7y"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.52, 0.48], horizontal_spacing=0.10,
                        subplot_titles=("Sıfır kuponlu eğri ve fonlama", "3 aylık taşıma + roll · altta başabaş"))
    fig.add_trace(go.Scatter(x=[kok(v) for v in vade], y=getiri, mode="lines+markers", name="DİBS sıfır kuponlu getiri",
                             text=etiket, hovertemplate="%{text}: %{y:.2f}<extra></extra>",
                             line=dict(color=MAVI, width=2.4), marker=dict(size=8)), 1, 1)
    for y, ad, renk, kesik in ((bg["tlref_etkin"], f"TLREF bileşik karşılığı %{vir(bg['tlref_etkin'])}", CLARET, "solid"),
                               (bg["tlref"], f"TLREF fixingi %{vir(bg['tlref'])} (basit)", CLARET, "dot"),
                               (bg["politika"], f"politika faizi %{vir(bg['politika'])}", GRI, "dash")):
        fig.add_trace(go.Scatter(x=[kok(0.2), kok(7.3)], y=[y, y], mode="lines", name=ad,
                                 line=dict(color=renk, width=1.6, dash=kesik)), 1, 1)
    fig.update_xaxes(tickvals=[kok(v) for v in vade], ticktext=etiket, title_text="vade (karekök ölçek)", row=1, col=1)
    fig.update_yaxes(title_text="yıllık bileşik (%)", range=[31, 46], row=1, col=1)
    anah = ["0.5", "1", "2", "3", "5", "7"]
    ad2 = ["6a", "1y", "2y", "3y", "5y", "7y"]
    tas = [bg["tasima"][k]["tasima_yuzde"] for k in anah]
    rol = [bg["tasima"][k]["roll_yuzde"] for k in anah]
    top = [bg["tasima"][k]["toplam_yuzde"] for k in anah]
    bas = [bg["tasima"][k]["basabas_bp"] for k in anah]
    fig.add_trace(go.Bar(x=ad2, y=tas, name="taşıma (getiri − fonlama)", marker_color=CLARET), 1, 2)
    fig.add_trace(go.Bar(x=ad2, y=rol, name="roll (vade kısalırken eğri boyunca kayma)", marker_color=MAVI), 1, 2)
    fig.update_layout(barmode="relative")
    for x, t, ta, ro in zip(ad2, top, tas, rol):
        taban = min(ta, 0) + min(ro, 0)        # yığının en alt ucu: etiket onun altına
        fig.add_annotation(x=x, y=taban - 0.25, text=f"<b>{yuzde(t)}</b>",
                           showarrow=False, font=dict(size=11), row=1, col=2)
    # başabaş eksen etiketinde: bar etiketleriyle yan yana binmesin
    fig.update_xaxes(tickvals=ad2, ticktext=[f"{a}<br>{vir(b, 0)} bp" for a, b in zip(ad2, bas)],
                     title_text="", row=1, col=2)
    fig.update_yaxes(title_text="% (3 ay)", range=[-5.4, 1.2], row=1, col=2)
    fig.add_hline(y=0, line=dict(color="#bbb", width=1), row=1, col=2)
    fig.update_layout(title=dict(text=(
        f"Şekil 01 — {_tarih(bg['gun'])} eğrisi: kâğıdı fonlamanın bedeli"
        f"<br><sub>TCMB DİBS gösterge değerlerinden sıfır kuponlu getiri · fonlama TLREF {_tarih(bg['tlref_gun'])} "
        "fixingi, günlük bileşiklenmiş · başabaş: 3 ayda getirinin ne kadar düşmesi gerektiği</sub>")))
    _yaz(fig, "01_egri_tasima.html", 520)


def s02_durasyon(o: dict, S) -> None:
    d = S["durasyon"]
    s = d[d["T"] == 5.0]
    blok = o["durasyon"]["5y"]
    fig = go.Figure()
    for ters, ad, renk in ((True, f"eğri ters (7y < 3a) · ort. {yuzde(blok['ters']['ort'])}", CLARET),
                           (False, f"eğri ters değil · ort. {yuzde(blok['duz']['ort'], arti=True)}", MAVI)):
        x = s[s.ters == ters]
        fig.add_trace(go.Scatter(
            x=x.cr, y=x.fazla, mode="markers", name=ad,
            marker=dict(color=renk, size=7, opacity=0.7),
            text=[t.strftime("%m.%Y") for t in x.t0],
            hovertemplate="%{text}<br>taşıma+roll %{x:.2f}%<br>gerçekleşen %{y:.2f}%<extra></extra>"))
    xs = np.linspace(s.cr.min(), s.cr.max(), 50)
    b, a = np.polyfit(s.cr, s.fazla, 1)
    fig.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", name=f"doğrusal uyum · eğim {vir(blok['egim'])}",
                             line=dict(color=GRI, width=2, dash="dash")))
    fig.add_hline(y=0, line=dict(color="#bbb", width=1))
    fig.add_vline(x=0, line=dict(color="#bbb", width=1))
    fig.update_xaxes(title_text="ex-ante 3 aylık taşıma + roll (%, eğri sabit varsayımıyla)")
    fig.update_yaxes(title_text="gerçekleşen 3 aylık fonlama üstü getiri (%)")
    fig.update_layout(title=dict(text=(
        "Şekil 02 — 5 yıllık kâğıdın fonlama üstü getirisi: başlangıçtaki taşıma+roll ve gerçekleşen"
        f"<br><sub>{o['pca']['ilk'][:4]}–{o['pca']['son'][:4]} · ay sonu başlangıç, 3 ay elde tutma · "
        "sinyal 5 iş günü önceki eğriden · fonlama gecelik bileşik</sub>")))
    _yaz(fig, "02_durasyon_getiri.html", 520)


# ─────────────────────────────────────────────────────────────── Bölüm 2
def s03_tlref(o: dict, S) -> None:
    d = S["tlref"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=d.index, y=d.koridor_ust, mode="lines", line=dict(color=GRI, width=0.6),
                             name="koridor üst sınırı", showlegend=False), 1, 1)
    fig.add_trace(go.Scatter(x=d.index, y=d.koridor_alt, mode="lines", line=dict(color=GRI, width=0.6),
                             fill="tonexty", fillcolor="rgba(138,138,138,0.16)", name="faiz koridoru"), 1, 1)
    fig.add_trace(go.Scatter(x=d.index, y=d.politika, mode="lines", name="politika faizi",
                             line=dict(color=MUREKKEP, width=1.6, shape="hv")), 1, 1)
    fig.add_trace(go.Scatter(x=d.index, y=d.tlref, mode="lines", name="TLREF fixingi",
                             line=dict(color=CLARET, width=1.4)), 1, 1)
    fig.add_trace(go.Scatter(x=d.index, y=d.baz, mode="lines", name="TLREF − politika (bp)",
                             line=dict(color=MAVI, width=1.1), fill="tozeroy",
                             fillcolor="rgba(47,93,140,0.15)"), 2, 1)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="bp", row=2, col=1)
    tb = o["tlref_baz"]
    fig.update_layout(title=dict(text=(
        "Şekil 03 — TLREF politika faizini izler, ama her zaman değil"
        f"<br><sub>{_tarih(tb['ilk'])} → {_tarih(tb['son'])} · gün payı: fark 100 bp'nin üstünde "
        f"%{vir(tb['mutlak_100_ustu'], 0)} · TLREF koridor tavanına en yakın %{vir(tb['tavanda'], 0)}, "
        f"tabanına en yakın %{vir(tb['tabanda'], 0)}</sub>")))
    _yaz(fig, "03_tlref_politika.html", 560)


# ─────────────────────────────────────────────────────────────── Bölüm 3
def s04_pca(o: dict) -> None:
    p = o["pca"]
    vade = [0.25, 0.5, 1, 2, 3, 5, 7]
    etiket = ["3a", "6a", "1y", "2y", "3y", "5y", "7y"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.62, 0.38], horizontal_spacing=0.12,
                        subplot_titles=("Bileşen yükleri (ay sonu değişimleri)", "Seviye bileşeninin payı ve frekans"))
    for i, (ad, renk) in enumerate((("seviye", CLARET), ("eğim", MAVI), ("büküm", TURUNCU))):
        y = [p["yuk"][f"pc{i + 1}"][dd] for dd in olcum.DUGUM]
        fig.add_trace(go.Scatter(x=[kok(v) for v in vade], y=y, mode="lines+markers",
                                 name=f"{ad}: varyansın %{vir(p['pay'][i], 1)}'i",
                                 line=dict(color=renk, width=2.4), marker=dict(size=8)), 1, 1)
    fig.add_hline(y=0, line=dict(color="#bbb", width=1), row=1, col=1)
    fig.update_xaxes(tickvals=[kok(v) for v in vade], ticktext=etiket, title_text="vade (karekök ölçek)", row=1, col=1)
    fig.update_yaxes(title_text="yük", row=1, col=1)
    fr = o["pca_frekans"]
    ad = ["günlük", "haftalık", "ay sonu", "ay ortalaması"]
    an = ["gunluk", "haftalik", "ay_sonu", "ay_ortalamasi"]
    fig.add_trace(go.Bar(x=ad, y=[fr[a]["pay"][0] for a in an], marker_color=[GRI, GRI, CLARET, GRI],
                         text=[f"%{vir(fr[a]['pay'][0], 1)}" for a in an], textposition="outside",
                         name="seviye payı", showlegend=False), 1, 2)
    fig.update_yaxes(title_text="% varyans", range=[0, 85], row=1, col=2)
    fig.update_layout(title=dict(text=(
        f"Şekil 04 — Eğrinin üç hareketi: seviye, eğim, büküm ({p['ilk'][:4]}–{p['son'][:4]})"
        f"<br><sub>DİBS sıfır kuponlu eğri, 3 ay – 7 yıl · {p['n']} aylık değişim · günlük veride "
        "ölçüm gürültüsü seviye payını düşürür</sub>")))
    _yaz(fig, "04_pca.html", 500)


def s05_kadran(o: dict) -> None:
    k = o["kadran"]
    KAD = [("ayı yataylaşma", CLARET), ("boğa dikleşme", MAVI), ("ayı dikleşme", TURUNCU), ("boğa yataylaşma", GRI)]
    satir = [("Tüm aylar", {q: k["pay"][q] for q, _ in KAD}, k["n"]),
             ("Seviye |Δ| > 100 bp", {q: 100 * k["buyuk"][q] / k["buyuk_n"] for q, _ in KAD}, k["buyuk_n"])]
    for f, ad in (("artırım", "Artırım ayları"), ("indirim", "İndirim ayları"), ("sabit", "Sabit tutulan aylar")):
        n = k["faz"][f]["n"]
        satir.append((ad, {q: 100 * k["faz"][f][q] / n for q, _ in KAD}, n))
    etiket = [f"{a} (n={n})" for a, _, n in satir][::-1]
    fig = go.Figure()
    for q, renk in KAD:
        v = [s[q] for _, s, _ in satir][::-1]
        fig.add_trace(go.Bar(y=etiket, x=v, orientation="h", name=q, marker_color=renk,
                             text=[f"%{vir(x, 0)}" for x in v], textposition="inside",
                             insidetextanchor="middle", textfont=dict(color="white", size=11)))
    fig.update_layout(barmode="stack", legend=dict(traceorder="normal"))
    fig.update_xaxes(title_text="% ay", range=[0, 100])
    fig.update_layout(title=dict(text=(
        "Şekil 05 — Aylık eğri hareketinin dört kadranı ve PPK kararı"
        "<br><sub>seviye = (Δ2y + Δ7y)/2 · eğim = Δ(7y − 2y) · ayı = faiz yukarı · PPK fazı: o ay "
        "alınan kararların toplam faiz değişimi (arşiv 2016'da başlar)</sub>")))
    _yaz(fig, "05_kadran.html", 460)


def s06_egim_beta(o: dict, S) -> None:
    A = S["A"]
    D = A.diff().dropna() * 100
    e = D.n7y - D.n2y
    es = o["egim_seviye"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=D.n2y, y=e, mode="markers", name="aylık değişim",
                             marker=dict(color=MAVI, size=7, opacity=0.65),
                             text=[t.strftime("%m.%Y") for t in D.index],
                             hovertemplate="%{text}<br>Δ2y %{x:.0f} bp<br>Δ(7y−2y) %{y:.0f} bp<extra></extra>"))
    xs = np.linspace(D.n2y.min(), D.n2y.max(), 50)
    b, a = np.polyfit(D.n2y, e, 1)
    fig.add_trace(go.Scatter(x=xs, y=a + b * xs, mode="lines", name=f"doğrusal uyum · korelasyon {vir(es['corr_2y_2s7s'])}",
                             line=dict(color=CLARET, width=2.2)))
    fig.add_hline(y=0, line=dict(color="#bbb", width=1))
    fig.add_vline(x=0, line=dict(color="#bbb", width=1))
    fig.update_xaxes(title_text="Δ 2 yıllık getiri (bp, ay)")
    fig.update_yaxes(title_text="Δ (7y − 2y) eğimi (bp, ay)")
    fig.update_layout(title=dict(text=(
        "Şekil 06 — Kısa uç yükselirken eğri yataylaşır: seviye ve eğim aynı hareketin iki yüzü"
        f"<br><sub>{o['pca']['ilk'][:4]}–{o['pca']['son'][:4]} ay sonu değişimleri · 7 yıllık, 2 yıllığın "
        f"hareketinin ortalama %{vir(es['beta_7y_2y'] * 100, 0)}'si kadar hareket ediyor</sub>")))
    _yaz(fig, "06_egim_seviye.html", 500)


def s07_kalicilik(o: dict) -> None:
    k = o["kalicilik"]["seri"]
    sira = [("2y", "2y"), ("5y", "5y"), ("7y", "7y"), ("2s5s", "2s5s"), ("2s7s", "2s7s"),
            ("fly50", "fly 50:50"), ("flyPCA", "fly PCA")]
    renk = [CLARET, CLARET, CLARET, MAVI, MAVI, TURUNCU, TURUNCU]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.12,
                        subplot_titles=("Yarı ömür (ay)", "Aylık oynaklık (bp)"))
    fig.add_trace(go.Bar(x=[a for _, a in sira], y=[k[s]["yari_omur_ay"] for s, _ in sira], marker_color=renk,
                         text=[vir(k[s]["yari_omur_ay"], 1) for s, _ in sira], textposition="outside",
                         showlegend=False), 1, 1)
    fig.add_trace(go.Bar(x=[a for _, a in sira], y=[k[s]["sigma_bp_ay"] for s, _ in sira], marker_color=renk,
                         text=[vir(k[s]["sigma_bp_ay"], 0) for s, _ in sira], textposition="outside",
                         showlegend=False), 1, 2)
    fig.update_yaxes(range=[0, 52], row=1, col=1)
    fig.update_yaxes(range=[0, 280], row=1, col=2)
    fig.update_layout(title=dict(text=(
        "Şekil 07 — Seviye yıllarca, eğim bir yıl, büküm birkaç ay hafızalı"
        f"<br><sub>{o['pca']['ilk'][:4]}–{o['pca']['son'][:4]} ay sonu · yarı ömür: aylık AR(1) katsayısından "
        "ln 0,5 / ln φ · fly = 2×5y − 2y − 7y · PCA ağırlıkları metinde</sub>")))
    _yaz(fig, "07_kalicilik.html", 460)


def s08_fly(o: dict, S) -> None:
    F = S["fly"]
    A = S["A"]
    a, b = o["kalicilik"]["agirlik_pca"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.4, 0.6], vertical_spacing=0.07)
    fig.add_trace(go.Scatter(x=A.index, y=A.n2y, mode="lines", name="2 yıllık getiri (%)",
                             line=dict(color=MUREKKEP, width=1.6)), 1, 1)
    fig.add_trace(go.Scatter(x=F.index, y=F.fly50, mode="lines", name="fly 50:50 = 2×5y − 2y − 7y",
                             line=dict(color=TURUNCU, width=1.8)), 2, 1)
    fig.add_trace(go.Scatter(x=F.index, y=F.flyPCA, mode="lines",
                             name=f"PCA-nötr fly = 5y − {vir(a, 3)}×2y − {vir(b, 3)}×7y",
                             line=dict(color=MAVI, width=1.8)), 2, 1)
    fig.update_yaxes(title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="bp", row=2, col=1)
    fig.update_layout(title=dict(text=(
        "Şekil 08 — Aynı büküm, iki ağırlık: 50:50 fly seviyeyi de taşır"
        f"<br><sub>ay sonu · korelasyon, seviye bileşeniyle: 50:50 fly {vir(o['kalicilik']['fly50_korelasyon'][0])} · "
        f"PCA-nötr fly {vir(o['kalicilik']['flyPCA_korelasyon'][0])} (tanım gereği)</sub>")))
    _yaz(fig, "08_fly_agirlik.html", 560)


def s09_barbell(o: dict) -> None:
    bb = o["barbell"]
    dy = np.linspace(-600, 600, 121)
    konv = 0.5 * bb["konv_fark"] * (dy / 1e4) ** 2 * 100
    toplam = bb["cr_fark"] + konv
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dy, y=konv, mode="lines", name="yalnız konveksite farkı (anlık paralel kayma)",
                             line=dict(color=MAVI, width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=dy, y=toplam, mode="lines",
                             name=f"3 aylık taşıma+roll farkı dahil ({yuzde(bb['cr_fark'], arti=True)})",
                             line=dict(color=CLARET, width=2.4)))
    fig.add_hline(y=0, line=dict(color="#bbb", width=1))
    fig.update_xaxes(title_text="paralel getiri değişimi (bp)")
    fig.update_yaxes(title_text="barbell − bullet getirisi (%)")
    fig.update_layout(title=dict(text=(
        f"Şekil 09 — {_tarih(bb['gun'])}: 2y/7y barbell ile 5y bullet"
        f"<br><sub>nakit ve durasyon nötr: %{vir(bb['agirlik_2y'] * 100, 1)} 2y + %{vir(bb['agirlik_7y'] * 100, 1)} 7y · "
        f"konveksite farkı +{vir(bb['konv_fark'])} · büküm riski bu çizimde yok — metinde</sub>")))
    _yaz(fig, "09_barbell_bullet.html", 480)


def main() -> int:
    if go is None:
        print("çizim için plotly gerekir")
        return 1
    o, S = olcum.hesapla()
    s01_egri_tasima(o)
    s02_durasyon(o, S)
    s03_tlref(o, S)
    s04_pca(o)
    s05_kadran(o)
    s06_egim_beta(o, S)
    s07_kalicilik(o)
    s08_fly(o, S)
    s09_barbell(o)
    return 0


if __name__ == "__main__":
    sys.exit(main())
