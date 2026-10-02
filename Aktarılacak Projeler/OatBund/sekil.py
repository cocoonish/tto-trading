#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND (02.10.2026) — analiz figürleri.

Bu bir HAT DEĞİL, tek bir analizin çizim katmanı. Analiz yayımlandığı günün
metnidir (karar 08.09.2026); figürler de o günün ölçümünü dondurur ve
`site/public/analiz/<slug>/` altına yazılır — hat figürleri gibi tazelenmez,
sayfa damgası basmaz, her figür kendi tarihini kendi alt başlığında taşır.

GİRDİ TEK YERDEN: `veri/olcum.json` (`olcum.py` üretir). Figür ile metin iki
ayrı hesaptan beslenseydi bir gün sessizce ayrışırdı.

Biçim: ondalık virgül, binlik nokta, eksi U+2212 (`separators`; üzerine gelme
kutusu metni `customdata`dan, sözleşmeyle önceden yazılır — plotly'nin
şablonu ASCII tire ve İngilizce ay adı basar). Plotly başlığı sarmaz,
taşırır — başlık ve alt yazı `_sar` ile bölünür. Renk: üç kategorik slot
(bordo, mavi, kehribar) doğrulayıcıdan geçti (CVD ΔE ≥ 12,4, normal görüş ≥
18,1, kontrast ≥ 3:1); bağlam serileri gri. Çift y eksenli grafik yok: iki
ölçek iki alt panele bölünür.

Fonksiyon adı = yazıdaki şekil numarası = dosya adının öneki = figürün içindeki
"Şekil NN" başlığı (dogrula.py bunları sorar).

  python3 sekil.py
"""
from __future__ import annotations

import hashlib
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
OLCUM_OZ = ""
CIKTI = KOK / "site" / "public" / "analiz" / SLUG
PLOTLY_JS = "/js/plotly-4.0.0.min.js"
MUREKKEP, CLARET, MAVI, KEHRIBAR, GRI, ACIK = (
    "#1a1a1a", "#a8304f", "#2766b0", "#a8741a", "#8a8a8a", "#d8d4cc")
KOYU = "#5c5c5c"
# Renk sözleşmesi bütün figürlerde aynı: Fransa farkı bordo, İtalya mavi,
# EUR/USD mürekkep, euro bacağı (EUR/GBP) kehribar, dolar bacağı ve 30 Haziran
# gri, 2011 mavi (İtalya'nın krizi), öbür ülkeler ve öbür epizotlar koyu gri
# (KOYU; 2024 feshi kesikli). Mavi ve kehribar başka bir anlam taşımaz. Açık
# gri (ACIK) yalnız çizgi ve ızgarada: beyaz zeminde 1,48:1, veri taşıyan
# işarete konmaz.
SEKILLER = ["01_tarihce", "02_yil", "03_akranlar", "04_egri", "05_capraz",
            "06_kayan", "07_gun_ici", "08_epizotlar", "09_ileri"]
SATIR = 64          # alt yazının satır başına azami karakteri: 358 px telefonda taşmasın (ölçüldü)
BASLIK_SATIR = 50
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


_EK = {"1": "den", "2": "den", "3": "ten", "4": "ten", "5": "ten", "6": "dan", "7": "den", "8": "den",
       "9": "dan"}
_EK_ONLAR = {"1": "dan", "2": "den", "3": "dan", "4": "tan", "5": "den", "6": "tan", "7": "ten", "8": "den",
             "9": "dan"}


def ek_dan(sayi: str) -> str:
    """Ayrılma eki, sayının OKUNUŞUNA göre: 2026'dan · 2012'den · 2011'den · 2030'dan · 2000'den."""
    d = sayi.lstrip("0") or "0"
    if d[-1] != "0":
        return _EK[d[-1]]
    if len(d) >= 2 and d[-2] != "0":
        return _EK_ONLAR[d[-2]]
    return "den"   # yüz · bin: yüzden · binden


def tarih(t: str) -> str:
    return f"{int(t[8:10])} {AYLAR[int(t[5:7])]} {t[:4]}"


def tarih_g(t: str) -> str:
    """Yılsız: 1 Ekim."""
    return f"{int(t[8:10])} {AYLAR[int(t[5:7])]}"


AY_DAN = {1: "tan", 2: "tan", 3: "tan", 4: "dan", 5: "tan", 6: "dan", 7: "dan", 8: "tan", 9: "den",
          10: "den", 11: "dan", 12: "tan"}


def tarih_g_dan(t: str) -> str:
    """Yılsız tarih ve ayrılma eki ayın adına göre: 4 Ağustos'tan · 1 Eylül'den."""
    return f"{tarih_g(t)}'{AY_DAN[int(t[5:7])]}"


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
    fig.update_layout(title=dict(text=f"{_sar(f'Şekil {no} — {metin}', BASLIK_SATIR)}<br><sub>{alt_s}</sub>"))


def _yaz(fig, ad: str, yukseklik: int = 480, ek_ust: int = 0, lejant_y: float = -0.16, alt: int = 80) -> None:
    satir = (fig.layout.title.text or "").count("<br>") + 1
    fig.update_layout(
        height=yukseklik + 21 * max(0, satir - 4), margin=dict(l=64, r=28, t=26 + 21 * satir + ek_ust, b=alt),
        separators=",.", plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        # Başlık kabın üstüne yaslanır ve aşağı doğru büyür; üst boşluk satır
        # sayısından hesaplanır (satır aralığı ~20 px, ölçüldü). Plotly'nin
        # kendiliğinden konumu başlığı boşluğun ortasına koyuyor ve çok satırlı
        # alt yazı çizim alanına taşıyordu.
        title=dict(x=0, xanchor="left", y=1, yref="container", yanchor="top", pad=dict(t=10),
                   font=dict(size=15)),
        legend=dict(orientation="h", yanchor="top", y=lejant_y, x=0),
        hoverlabel=dict(bgcolor="white", font=dict(color=MUREKKEP)),
    )
    fig.update_xaxes(showgrid=False, linecolor=ACIK, ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    yol = CIKTI / f"{ad}.html"
    fig.write_html(yol, include_plotlyjs=PLOTLY_JS, full_html=True,
                   config={"displayModeBar": False, "responsive": True})
    # Figür hangi ölçümden çizildi: kapı (dogrula.py) bu özü bugünkü
    # olcum.json'un özüyle kıyaslar; ölçüm değişip figür çizilmezse düşer.
    yol.write_text(yol.read_text(encoding="utf-8").rstrip("\n") + f"\n<!-- olcum.json sha256: {OLCUM_OZ} -->\n",
                   encoding="utf-8")
    print(f"  ✓ {(CIKTI / (ad + '.html')).relative_to(KOK)}")


def _bp_metin(t: list, v: list, etiket: str) -> list:
    """Üzerine gelme kutusu metni, sözleşmeyle (gün.ay.yıl · ondalık virgül · U+2212)."""
    return [f"{tarih_k(a)} · {etiket}: {vir(b)} bp" for a, b in zip(t, v)]


# ─────────────────────────────────────────────────────────────── 01
def sekil01(o: dict) -> None:
    s, it = o["seriler"]["spread"], o["seriler"]["spread_it"]
    sv = o["seviye"]
    f = go.Figure()
    f.add_trace(go.Scatter(x=it["t"], y=it["v"], name="İtalya − Almanya", line=dict(color=MAVI, width=1),
                           customdata=_bp_metin(it["t"], it["v"], "İtalya"),
                           hovertemplate="%{customdata}<extra></extra>"))
    f.add_trace(go.Scatter(x=s["t"], y=s["v"], name="Fransa − Almanya", line=dict(color=CLARET, width=2),
                           customdata=_bp_metin(s["t"], s["v"], "Fransa"),
                           hovertemplate="%{customdata}<extra></extra>"))
    # Etiketler VERİ koordinatıyla ve iki satır: piksel ofseti dar ekranda
    # etiketi İtalya çizgisinin üstüne kaydırıyordu, tek satırlık 2026 etiketi
    # telefonda grafiğin dışına taşıyordu.
    f.add_annotation(x=sv["tarihi_zirve_gun"], y=sv["tarihi_zirve"], axref="x", ayref="y",
                     ax="2002-06-01", ay=300, xanchor="left",
                     text=f"{tarih(sv['tarihi_zirve_gun'])}<br>{vir(sv['tarihi_zirve'])} bp",
                     showarrow=True, arrowhead=0, arrowcolor=GRI, font=dict(size=12), bgcolor="white")
    f.add_annotation(x=sv["gun"], y=sv["spread"], axref="x", ayref="y", ax="2026-06-01", ay=385, xanchor="right",
                     text=f"{tarih(sv['gun'])}<br>{vir(sv['spread'])} bp",
                     showarrow=True, arrowhead=0, arrowcolor=CLARET, font=dict(size=12, color=CLARET),
                     bgcolor="white")
    f.update_yaxes(title="baz puan", range=[-20, 420])
    f.update_xaxes(tickformat="%Y")
    _baslik(f, "01", f"Fransa'nın farkı {tarih(sv['son_gorulme'])}'{ek_dan(sv['son_gorulme'][:4])} beri en yüksek",
            "Fransa ve İtalya 10 yıllık gösterge getirisinin Almanya'nınkinden farkı, baz puan · "
            "günlük Avrupa kapanışı · 2000–2026 · İtalya'nın 2011–12 zirvesi ölçeği kırpmasın diye "
            "eksen 420 bp'de kesildi.")
    _yaz(f, "01_tarihce", 480)


# ─────────────────────────────────────────────────────────────── 02
# (gün, kısa etiket). Metinde anılan ve birincil kaynakta ya da bir yayıncıda
# doğrulanmış olaylar (keşif #33–#34). dogrula.py her olayın gününün metinde
# geçtiğini sorar.
OLAYLAR = [
    ("2026-02-02", "2026 bütçesi kabul"),
    ("2026-03-02", "Hürmüz şoku"),
    ("2026-06-11", "ECB +25 bp"),
    ("2026-07-07", "Le Pen kararı"),
    ("2026-09-10", "ECB +25 bp"),
    ("2026-09-17", "54 milyar avroluk çaba"),
    ("2026-10-01", "2027 bütçe tasarısı"),
]


def sekil02(o: dict) -> None:
    s, it = o["seriler"]["spread"], o["seriler"]["spread_it"]
    bas = "2026-01-01"
    st = [(t, v) for t, v in zip(s["t"], s["v"]) if t >= bas]
    itt = [(t, v) for t, v in zip(it["t"], it["v"]) if t >= bas]
    f = go.Figure()
    f.add_trace(go.Scatter(x=[a for a, _ in itt], y=[b for _, b in itt], name="İtalya − Almanya",
                           line=dict(color=MAVI, width=1.6),
                           customdata=_bp_metin([a for a, _ in itt], [b for _, b in itt], "İtalya"),
                           hovertemplate="%{customdata}<extra></extra>"))
    f.add_trace(go.Scatter(x=[a for a, _ in st], y=[b for _, b in st], name="Fransa − Almanya",
                           line=dict(color=CLARET, width=2.2),
                           customdata=_bp_metin([a for a, _ in st], [b for _, b in st], "Fransa"),
                           hovertemplate="%{customdata}<extra></extra>"))
    ust = max(b for _, b in st) * 1.12
    # Olaylar numaralı işaretle; açıklaması alt yazıda. Yakın günlerin metin
    # etiketleri birbirini örtüyordu.
    for i, (gun, etiket) in enumerate(OLAYLAR, 1):
        f.add_vline(x=gun, line=dict(color=GRI, width=1, dash="dot"))
        f.add_annotation(x=gun, y=ust * (0.97 - 0.06 * ((i - 1) % 2)), text=f"<b>{i}</b>", showarrow=False,
                         font=dict(size=11, color=MUREKKEP), bgcolor="white", borderpad=1)
    # 15 Haziran: gösterge kâğıt değişimi (olay değil, seviye kayması) ayrı işaretle.
    gi = o["hiz"]["gosterge_imza"]["2026-06-15"]
    f.add_annotation(x="2026-06-15", y=gi["spr_gun"], text="G", showarrow=True, arrowhead=0, ax=0, ay=-28,
                     font=dict(size=10, color=KOYU), bgcolor="white", borderpad=1)
    fi = o["fransa_italya"]
    aylar = [f"2026-{m:02d}-01" for m in range(1, 11)]
    f.update_xaxes(tickvals=aylar, ticktext=[TR_AY_KISA[int(a[5:7])] for a in aylar])
    f.update_yaxes(title="baz puan", range=[0, ust])
    nb = "\u00a0"   # numara, gün ve ay satır sonunda bölünmesin
    olay = " · ".join(f"({i}){nb}{tarih_g(g).replace(' ', nb)}: {e}" for i, (g, e) in enumerate(OLAYLAR, 1))
    _baslik(f, "02", f"Fransa {tarih_g_dan(fi['kesintisiz_bas'])} beri İtalya'dan pahalı borçlanıyor",
            "10 yıllık gösterge getirisinin Almanya'ya farkı, baz puan · günlük Avrupa kapanışı · "
            f"1 Ocak – {tarih(o['son_gun'])} · olaylar: {olay} · G: 15{nb}Haziran gösterge kâğıt değişimi, "
            f"farkta {vir(gi['spr'], 1, True)} bp seviye kayması (olay değil).")
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
                           marker=dict(color=GRI, size=10),
                           customdata=[f"{r['ad']} · 30.06.2026: {vir(r['haziran'])} bp" for r in a],
                           hovertemplate="%{customdata}<extra></extra>"))
    for grup, renk, filtre in (("Fransa, " + tarih_g(o["son_gun"]), CLARET, lambda r: r["ulke"] == "fr"),
                               ("İtalya, " + tarih_g(o["son_gun"]), MAVI, lambda r: r["ulke"] == "it"),
                               ("öbür ülkeler, son kotasyon", KOYU, lambda r: r["ulke"] not in ("fr", "it"))):
        rr = [r for r in a if filtre(r)]
        f.add_trace(go.Scatter(x=[r["spread"] for r in rr], y=[r["ad"] for r in rr], mode="markers+text",
                               name=grup, marker=dict(color=renk, size=12), cliponaxis=False,
                               text=[vir(r["spread"]) for r in rr], textposition="middle right",
                               textfont=dict(size=11),
                               customdata=[f"{r['ad']} · {tarih_k(r['gun'])}: {vir(r['spread'])} bp" for r in rr],
                               hovertemplate="%{customdata}<extra></extra>"))
    f.update_xaxes(title="Almanya'ya fark, baz puan", range=[0, max(r["spread"] for r in a) * 1.25])
    _baslik(f, "03", "Ölçülen sekiz euro ülkesinin en geniş farkı Fransa'da",
            "10 yıllık gösterge getirisinin Almanya'ya farkı · gri: 30 Haziran 2026 · renkli: son kotasyon "
            "(Yunanistan ve Portekiz 30 Eylül, öbürleri 1 Ekim) · Avrupa kapanışı.")
    _yaz(f, "03_akranlar", 480, lejant_y=-0.22, alt=96)


# ─────────────────────────────────────────────────────────────── 04
def sekil04(o: dict) -> None:
    e = o["egri"]
    vade = ["2", "5", "10", "30"]
    x = [f"{v} yıl" for v in vade]
    # Paneller alt alta: yan yana dizilince dar ekranda çubuk etiketleri ve
    # sağ panelin eksen yazıları okunmuyordu.
    f = make_subplots(rows=2, cols=1, vertical_spacing=0.16, row_heights=[0.58, 0.42],
                      subplot_titles=["fark, bp", f"{tarih_g(o['son_gun'])} getiri değişimi, bp"])
    for ad_, deg, renk in (("15 Kasım 2011 (10 yıllık zirve günü)", [e[v]["zirve"] for v in vade], MAVI),
                           ("30 Haziran 2026", [e[v]["spread"] - e[v]["degisim_haziran"] for v in vade], GRI),
                           (tarih(o["son_gun"]), [e[v]["spread"] for v in vade], CLARET)):
        f.add_trace(go.Bar(x=x, y=deg, name=ad_, marker_color=renk, text=[vir(d) for d in deg],
                           textposition="outside", cliponaxis=False, constraintext="none", textfont=dict(size=11),
                           customdata=[f"{ad_} · {a}: {vir(d)} bp" for a, d in zip(x, deg)],
                           hovertemplate="%{customdata}<extra></extra>"), row=1, col=1)
    fr = [e[f"fr{v}y_1g_bp"] for v in vade]
    de = [e[f"de{v}y_1g_bp"] for v in vade]
    for ad_, deg, renk in (("Fransa getirisi", fr, CLARET), ("Almanya getirisi", de, MUREKKEP)):
        f.add_trace(go.Bar(x=x, y=deg, name=ad_, marker_color=renk, text=[vir(d, 1, True) for d in deg],
                           textposition="outside", cliponaxis=False, showlegend=False, constraintext="none",
                           textfont=dict(size=11),
                           customdata=[f"{ad_} · {a}: {vir(d, 1, True)} bp" for a, d in zip(x, deg)],
                           hovertemplate="%{customdata}<extra></extra>"), row=2, col=1)
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1), row=2, col=1)
    f.update_layout(barmode="group", bargap=0.25, bargroupgap=0.08)
    f.update_yaxes(range=[0, max(e[v]["zirve"] for v in vade) * 1.18], row=1, col=1)
    f.update_yaxes(range=[min(de) * 1.6, max(fr) * 1.7], row=2, col=1)
    for an in f.layout.annotations:
        an.font = dict(size=12)
    _baslik(f, "04", f"1 Ekim'de 2 yıllık fark {vir(e['2']['degisim_1g'], 1, True)} bp açıldı; "
            f"bunun %{vir(e['2']['de_payi'] * 100, 0)}'i Alman 2 yıllığının düşüşü",
            "üst: Fransa gösterge getirisinin aynı vadeli Almanya göstergesine farkı (2011 sütunları her vadenin "
            "15 Kasım 2011 değeri) · alt: veri gününde Fransa (bordo) ve Almanya (siyah) getirisinin kendi "
            "değişimi · Avrupa kapanışı.")
    _yaz(f, "04_egri", 640, ek_ust=26, lejant_y=-0.1)


# ─────────────────────────────────────────────────────────────── 05
CAPRAZ_AD = {("2026-02-25", "2026-10-01"): "25 Şub → 1 Eki", ("2026-06-30", "2026-08-31"): "30 Haz → 31 Ağu",
             ("2026-08-31", "2026-09-28"): "31 Ağu → 28 Eyl", ("2026-09-28", "2026-10-01"): "28 Eyl → 1 Eki",
             ("2026-08-31", "2026-10-01"): "31 Ağu → 1 Eki"}


def sekil05(o: dict) -> None:
    c = [r for r in o["capraz"] if (r["bas"], r["son"]) in CAPRAZ_AD]
    x = [CAPRAZ_AD[(r["bas"], r["son"])] for r in c]
    # Paneller alt alta ve kategori adları iki satır: yan yana dizilince dar
    # ekranda iki panelin eğik eksen yazıları birbirine giriyordu.
    xh = list(x)
    x = [a.replace(" → ", "<br>→ ") for a in x]
    f = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                      subplot_titles=["sterline göre (EUR/GBP)", "franka göre (EUR/CHF)"])
    for j, (kod, dolar) in enumerate((("eurgbp", "dolar_gbp"), ("eurchf", "dolar_chf")), 1):
        para = "sterlin" if kod == "eurgbp" else "frank"
        f.add_trace(go.Bar(x=x, y=[r[dolar] for r in c], name="dolar bacağı", marker_color=GRI,
                           marker_line=dict(color="white", width=1), legendgroup="d", showlegend=j == 1,
                           customdata=[f"{a} · dolar bacağı ({para}): {yuz(r[dolar], 2, True)}" for a, r in zip(xh, c)],
                           hovertemplate="%{customdata}<extra></extra>"), row=j, col=1)
        f.add_trace(go.Bar(x=x, y=[r[kod] for r in c], name="euro bacağı", marker_color=KEHRIBAR,
                           marker_line=dict(color="white", width=1), legendgroup="e", showlegend=j == 1,
                           customdata=[f"{a} · euro bacağı ({kod[:3].upper()}/{kod[3:].upper()}): "
                                       f"{yuz(r[kod], 2, True)}" for a, r in zip(xh, c)],
                           hovertemplate="%{customdata}<extra></extra>"), row=j, col=1)
        f.add_trace(go.Scatter(x=x, y=[r["fx"] for r in c], mode="markers+text", name="EUR/USD (toplam)",
                               marker=dict(color=MUREKKEP, size=10, symbol="diamond"), legendgroup="t",
                               showlegend=j == 1, text=[yuz(r["fx"], 2, True) for r in c],
                               textposition="middle right", textfont=dict(size=10), cliponaxis=False,
                               customdata=[f"{a} · EUR/USD: {yuz(r['fx'], 2, True)}" for a, r in zip(xh, c)],
                               hovertemplate="%{customdata}<extra></extra>"), row=j, col=1)
        f.add_hline(y=0, line=dict(color=MUREKKEP, width=1), row=j, col=1)
        f.update_yaxes(title_text="log değişim, %", row=j, col=1)
    f.update_layout(barmode="relative", bargap=0.35)
    f.update_xaxes(tickangle=0, tickfont=dict(size=11))
    for an in f.layout.annotations:
        an.font = dict(size=12)
    ev1 = next(r for r in c if r["bas"] == "2026-08-31" and r["son"] == "2026-09-28")
    ev2 = next(r for r in c if r["bas"] == "2026-09-28")
    _baslik(f, "05", f"31 Ağustos'tan bu yana euroya özgü kayıp son üç günde: sterline karşı "
            f"{yuz(ev2['eurgbp'], 2, True)}, önceki dört haftada {yuz(ev1['eurgbp'], 2, True)}",
            "EUR/USD log değişimi = dolar bacağı (GBP/USD ya da CHF/USD) + euro bacağı (EUR/GBP ya da EUR/CHF) · "
            "kurlar New York kapanışı · özdeşliktir, tahmin değil.")
    _yaz(f, "05_capraz", 700, ek_ust=26, lejant_y=-0.1, alt=96)


# ─────────────────────────────────────────────────────────────── 06
def sekil06(o: dict) -> None:
    k = o["seriler"]["kayan"]
    kk = o["kayan"]
    f = go.Figure()
    f.add_trace(go.Scatter(x=k["t"] + k["t"][::-1], y=k["ust"] + k["alt"][::-1], fill="toself",
                           fillcolor="rgba(26,26,26,0.10)", line=dict(width=0), name="EUR/USD ±2 standart hata",
                           hoverinfo="skip"))
    f.add_trace(go.Scatter(x=k["t"], y=k["spr"], name="EUR/USD", line=dict(color=MUREKKEP, width=2),
                           customdata=[f"{tarih_k(a)} · EUR/USD: {yuz(v, 2, True)}" for a, v in zip(k["t"], k["spr"])],
                           hovertemplate="%{customdata}<extra></extra>"))
    f.add_trace(go.Scatter(x=k["t"], y=k["eurgbp"], name="EUR/GBP (euroya özgü)", line=dict(color=KEHRIBAR, width=1.6),
                           customdata=[f"{tarih_k(a)} · EUR/GBP: {yuz(v, 2, True)}" for a, v in zip(k["t"], k["eurgbp"])],
                           hovertemplate="%{customdata}<extra></extra>"))
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1))
    f.update_yaxes(title="10 bp başına kur değişimi, %")
    f.update_xaxes(title="pencerenin bitişi")
    _baslik(f, "06", f"30 Eylül'de biten pencerede 10 bp açılmaya EUR/USD'de {yuz(kk['son'], 2, True)}, "
            f"EUR/GBP'de {yuz(kk['eurgbp_son'], 2, True)} eşlik ediyor",
            "104 haftalık kayan pencere: haftalık kur log değişimi = sabit + b₁·Δ(ABD−Almanya 2y) + "
            "b₂·Δ(OAT–Bund 10y); çizgiler b₂×10 · kurlar New York kapanışı · gölge Newey–West ±2 s.h. · "
            "Mart 2020 – Mart 2022 basamağı tek bir haftadan (18 Mart 2020) gelir: hafta pencereye girdiği ve "
            "çıktığı günlerde çizgiler sıçrar.")
    _yaz(f, "06_kayan", 480, lejant_y=-0.2, alt=90)


# ─────────────────────────────────────────────────────────────── 07
def sekil07(o: dict) -> None:
    """Üç fark AYNI panelde ve AYNI ölçekte, 15:30'a göre değişim olarak: ayrı
    panellerde ayrı ölçekle çizilince 1,9 bp'lik faiz farkı hareketi 5 bp'lik
    Fransa hareketinden iri görünüyordu. Figür Avrupa kapanışında (17:30) biter:
    sonrası günlük kapanış barının ötesindeki ince işlemdir."""
    g = o["seriler"]["gun_ici"]
    i0 = g["t"].index("15:30")
    f = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.62, 0.38])
    for kol, ad_, renk, w in (("spr", "Fransa − Almanya 10y", CLARET, 2.2),
                              ("ispr2", "İtalya − Almanya 2y", MAVI, 1.6),
                              ("rd", "ABD − Almanya 2y (faiz farkı)", GRI, 1.8)):
        b0 = g[kol][i0]
        yv = [None if v is None else round(v - b0, 2) for v in g[kol]]
        f.add_trace(go.Scatter(x=g["t"], y=yv, name=ad_, line=dict(color=renk, width=w),
                               customdata=[f"{a} · {ad_}: {vir(v) if v is not None else '—'} bp "
                                           f"(15:30'a göre {vir(d, 1, True) if d is not None else '—'})"
                                           for a, v, d in zip(g["t"], g[kol], yv)],
                               hovertemplate="%{customdata}<extra></extra>"), row=1, col=1)
    f.add_trace(go.Scatter(x=g["t"], y=g["eurusd"], name="EUR/USD", line=dict(color=MUREKKEP, width=1.6),
                           customdata=[f"{a} · EUR/USD: {vir(v, 4) if v is not None else '—'}"
                                       for a, v in zip(g["t"], g["eurusd"])],
                           hovertemplate="%{customdata}<extra></extra>"), row=2, col=1)
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1), row=1, col=1)
    for s_, et, yasla, yy in (("14:15", "ECB kuru ", "right", 0.995), ("15:30", "15:30 ", "right", 0.955),
                              ("16:00", " ISM", "left", 0.995), ("16:15", " 16:15", "left", 0.955)):
        if s_ in g["t"]:
            f.add_vline(x=s_, line=dict(color=GRI, width=1, dash="dot"))
            f.add_annotation(x=s_, y=yy, yref="paper", text=et, showarrow=False, xanchor=yasla,
                             yanchor="top", font=dict(size=10, color="#555"), bgcolor="rgba(255,255,255,0.85)")
    tum = [v - g[k][i0] for k in ("spr", "ispr2", "rd") for v in g[k] if v is not None]
    f.update_yaxes(title_text="15:30'a göre değişim, bp", range=[min(tum) - 1.5, max(tum) + 5], row=1, col=1)
    f.update_yaxes(title_text="EUR/USD", tickformat=".3f", row=2, col=1)
    f.update_xaxes(title_text="Paris saati", row=2, col=1, nticks=7, tickangle=0)
    q = o["gun_ici_1615"]
    _baslik(f, "07", f"{tarih_g(o['son_gun'])}, {q['bas']} → {q['son']}: faiz farkı {vir(q['rd']['degisim'], 1, True)} bp "
            f"oynarken fark {vir(q['spr']['degisim'], 1, True)} bp açıldı, euro {yuz(q['eurusd']['degisim_yuzde'], 2, True)}",
            "15 dakikalık ızgara, her nokta o saate kadarki son kotasyon · üst: üç fark, 15:30'a göre değişim, aynı "
            "ölçek · alt: EUR/USD · Avrupa seansı 08:00–17:30 · pencere veriye bakılarak seçildi.")
    _yaz(f, "07_gun_ici", 620, lejant_y=-0.2, alt=130)


# ─────────────────────────────────────────────────────────────── 08
VURGU = {"2026": (CLARET, "solid"), "2011 euro bölgesi borç krizi": (MAVI, "solid"),
         "2024 meclisin feshi": (KOYU, "dash")}


def sekil08(o: dict) -> None:
    y = o["seriler"]["epizot_yollari"]
    f = go.Figure()
    ilk_gri = True
    # Kronolojik sıra ölçüm dosyasının epizot listesinden (sözlük anahtarları
    # JSON'da alfabetik dizilir).
    for e in o["epizotlar"]:
        ad, yol = e["ad"], y[e["ad"]]
        vurgu = ad in VURGU
        f.add_trace(go.Scatter(x=yol["x"], y=yol["y"], name=ad if vurgu else "öbür epizotlar",
                               legendgroup=ad if vurgu else "gri", showlegend=vurgu or ilk_gri,
                               line=dict(color=VURGU.get(ad, (GRI, "solid"))[0], width=2.4 if vurgu else 1,
                                         dash=VURGU.get(ad, (GRI, "solid"))[1]),
                               opacity=1 if vurgu else 0.75,
                               customdata=[f"{ad} · {a}. iş günü: {vir(b, 1, True)} bp" for a, b in zip(yol["x"], yol["y"])],
                               hovertemplate="%{customdata}<extra></extra>"))
        if not vurgu:
            ilk_gri = False
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1))
    f.update_xaxes(title="başlangıçtan bu yana iş günü")
    f.update_yaxes(title="başlangıca göre fark değişimi, bp")
    _baslik(f, "08", "2026 epizodu 2011'den bu yana en büyük açılma",
            "Fransa–Almanya 10 yıllık farkının epizot başlangıcına göre değişimi, baz puan · başlangıç günleri "
            "metindeki epizot tablosundan (2026: yılın dibi, sonradan seçildi; 15 Haziran gösterge değişimi "
            "yolun içinde) · 160 iş günü · gri: 2008, 2010, 2017, 2020, 2024 Barnier, 2025 Bayrou.")
    _yaz(f, "08_epizotlar", 560, lejant_y=-0.2, alt=96)


# ─────────────────────────────────────────────────────────────── 09
def sekil09(o: dict) -> None:
    p = o["seriler"]["ileri_noktalar"]
    il, ilb = o["ileri"][0], o["ileri"][4]
    f = go.Figure()
    # Fransa farkının gözlemleri: bordo. Ertesi ay 1 bp'den fazla açılanlar
    # içi boş işaretle; ikisi sıfırın hemen üstünde (+0,9 ve +0,4 bp).
    for ad_, sec, sembol in (("geçmiş gözlemler", [i <= 1 for i in p["i"]], "circle"),
                             ("ertesi ay 1 bp'den fazla açılanlar", [i > 1 for i in p["i"]], "circle-open")):
        f.add_trace(go.Scatter(x=[a for a, k in zip(p["g"], sec) if k], y=[b for b, k in zip(p["i"], sec) if k],
                               mode="markers", name=ad_,
                               marker=dict(color=CLARET, size=8 if sembol == "circle" else 10, opacity=0.8,
                                           symbol=sembol, line=dict(width=1.6, color=CLARET)),
                               customdata=[f"{tarih_k(t)} · önceki 22 iş günü: {vir(a, 1, True)} bp · sonraki 22 iş "
                                           f"günü: {vir(b, 1, True)} bp"
                                           for t, a, b, k in zip(p["t"], p["g"], p["i"], sec) if k],
                               hovertemplate="%{customdata}<extra></extra>"))
    f.add_vline(x=il["bugunku_acilma"], line=dict(color=MUREKKEP, width=1.6, dash="dash"))
    f.add_annotation(x=il["bugunku_acilma"], y=max(p["i"]) if p["i"] else 0,
                     text=f" bugün {vir(il['bugunku_acilma'], 1, True)} bp",
                     showarrow=False, xanchor="left", font=dict(color=MUREKKEP, size=12))
    f.add_hline(y=0, line=dict(color=MUREKKEP, width=1))
    f.update_xaxes(title="önceki 22 iş günündeki açılma, baz puan")
    f.update_yaxes(title="sonraki 22 iş gününde değişim, baz puan")
    _baslik(f, "09", f"30 bp'den hızlı açılmalardan sonra ertesi ay daha da açılan gözlemlerin payı "
            f"%{vir(il['daha_acildi_payi'], 1)}; bugünkü hızı aşanlarda %{vir(ilb['daha_acildi_payi'], 0)}",
            f"2000–2026, {il['gozlem']} gözlem, {il['epizot']} ayrı küme (örtüşen günler bağımsız değildir); "
            f"bugünkü hızı aşan {ilb['gozlem']} gözlem tek bir krizden, {ilb['epizot']} kümede · sonraki 22 iş "
            f"günü medyanı {vir(il['medyan'], 1, True)} bp · geçmiş bir dağılımdır, tahmin değildir.")
    _yaz(f, "09_ileri", 480, lejant_y=-0.2, alt=96)


def main() -> int:
    if go is None:
        raise SystemExit("plotly yok — çizim için gerekli (kapı yolu bunu istemez)")
    global OLCUM_OZ
    ham = (BURASI / "veri" / "olcum.json").read_bytes()
    OLCUM_OZ = hashlib.sha256(ham).hexdigest()
    o = json.loads(ham.decode("utf-8"))
    print(f"OAT–Bund figürleri → {CIKTI.relative_to(KOK)}")
    for i, ad in enumerate(SEKILLER, 1):
        globals()[f"sekil{i:02d}"](o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
