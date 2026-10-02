#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 6 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)

GOLGE = "rgba(138,138,138,0.13)"          # dönem gölgesi (açık gri)
ACIK_TURUNCU = "rgba(184,134,11,0.42)"    # KKM'nin ikinci kısmı: aynı varlık, açık ton


def _baslik(ana: str, *satir: str) -> str:
    """Plotly başlığı sarmaz: alt başlık satırları elle kırılır (≈105 karakter)."""
    return ana + "<br><sub>" + "<br>".join(satir) + "</sub>"


def _paneller_sola(fig, boyut: int = 13) -> None:
    """Panel başlıkları sola yaslanır: dar ekranda ortalı başlık iki uçtan birden kırpılıyordu."""
    for an in fig.layout.annotations:
        if an.yref == "paper" and an.yanchor == "bottom" and an.xref == "paper":
            an.update(x=0, xanchor="left", font=dict(size=boyut, color=MUREKKEP))


def _isaretli(x: float, b: int = 1) -> str:
    """Artı işaretli sayı (eksi U+2212 vir'den)."""
    return ("+" if x > 0 else "") + vir(x, b)


# ═══════════════════════════════════════════════════════════════ Şekil 09
def s09_borc_ayrisimi(o: dict) -> None:
    b = o["b06"]
    s = b["sekil_09"]
    a = b["p6a"]
    # x ekseni sayısal: yıl t'nin çubuğu t−1 sonundan t sonuna değişimdir; son çubuk 2026 ilk yarısı.
    x = [int(d[:4]) for d in s["donem"]]
    yillik = [d.isdigit() for d in s["donem"]]
    etiket = [d if d.isdigit() else "2026 ilk yarı" for d in s["donem"]]
    desen = ["" if k else "/" for k in yillik]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.10,
                        subplot_titles=("Yıllık değişimin bileşenleri (GSYH puanı)",
                                        f"Borç stoku / GSYH (yıl sonu; son nokta {tarih(s['son'])})"))
    bilesen = (("kartopu_puan", TURUNCU, "kartopu: örtük faiz − nominal büyüme"),
               ("fdd_terimi_puan", CLARET, "faiz dışı denge (fazla borcu azaltır)"),
               ("kur_terimi_puan", MAVI, "kur: döviz payı × USD/TRY artışı"),
               ("artik_puan", GRI, "artık (açıklanmayan)"))
    for anahtar, renk, ad in bilesen:
        fig.add_trace(go.Bar(x=x, y=s[anahtar], name=ad, marker_color=renk, marker_line_width=0,
                             marker_pattern=dict(shape=desen, fgcolor="white", size=5, solidity=0.35),
                             customdata=etiket,
                             hovertemplate="%{customdata}: %{y:+.2f} puan<extra>" + ad + "</extra>"), 1, 1)
    # Δd çizgisi yalnız yıllık sütunları birleştirir; altı aylık son sütun ayrı işaret (yıllıkla toplanmaz).
    xa = [v for v, k in zip(x, yillik) if k]
    ya = [v for v, k in zip(s["delta_d_puan"], yillik) if k]
    fig.add_trace(go.Scatter(x=xa, y=ya, mode="lines+markers", name="toplam değişim Δd",
                             line=dict(color=MUREKKEP, width=1.6), marker=dict(size=6, color=MUREKKEP),
                             hovertemplate="%{x}: Δd %{y:+.2f} puan<extra></extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=[x[-1]], y=[s["delta_d_puan"][-1]], mode="markers", showlegend=False,
                             marker=dict(size=6, color=MUREKKEP),
                             hovertemplate="2026 ilk yarı: Δd %{y:+.2f} puan<extra></extra>"), 1, 1)
    fig.update_layout(barmode="relative", bargap=0.18)
    fig.update_yaxes(title_text="GSYH puanı (artı: oranı artırır)", zeroline=True, zerolinecolor="#b9b2a6",
                     zerolinewidth=1, row=1, col=1)

    # 2007–2025 toplamı: başlıktaki hükmün sayıları (son altı aylık sütun dahil değil)
    t = a["toplam_2007_2025"]
    fig.add_annotation(x=x[0] - 0.45, y=-9.5, xref="x", yref="y", xanchor="left", yanchor="top", align="left",
                       showarrow=False, font=dict(size=10.5, color=MUREKKEP), bgcolor="rgba(255,255,255,0.9)",
                       bordercolor="#d8d4cc", borderwidth=1, borderpad=4,
                       text=(f"{a['ilk']}–{a['son']} toplamı (GSYH puanı)<br>"
                             f"kartopu {_isaretli(t['kartopu_puan'])} · faiz dışı denge "
                             f"{_isaretli(t['fdd_terimi_puan'])}<br>"
                             f"kur {_isaretli(t['kur_terimi_puan'])} · artık {_isaretli(t['artik_puan'])} · "
                             f"Δd {_isaretli(t['delta_d_puan'])}"))

    # Düzey paneli: türetilmiş stok (2006 sonu → 2025; ilk çubuğun başlangıç düzeyinden), resmî stok (2020 →).
    dz = s["duzey"]
    yillar = [int(y) for y in dz["yil"]]
    bas = yillar.index(x[0] - 1)
    tx = yillar[bas:]
    fig.add_trace(go.Scatter(x=tx, y=dz["turetilmis_d"][bas:], mode="lines+markers", showlegend=False,
                             name="bileşenlerden türetilen stok",
                             line=dict(color=GRI, width=1.6), marker=dict(size=5, color=GRI),
                             hovertemplate="%{x} sonu: %%{y:.1f}<extra>türetilen stok</extra>"), 2, 1)
    rx = [yy for yy, v in zip(yillar, dz["resmi_d"]) if v is not None]
    ry = [v for v in dz["resmi_d"] if v is not None]
    iy = a["ilk_yari_2026"]
    rx.append(x[-1])
    ry.append(iy["d"])
    fig.add_trace(go.Scatter(x=rx, y=ry, mode="lines+markers", name="resmî borç stoku", showlegend=False,
                             line=dict(color=MUREKKEP, width=2), marker=dict(size=6, color=MUREKKEP),
                             customdata=[f"{v} sonu" for v in rx[:-1]] + [tarih(iy["son"])],
                             hovertemplate="%{customdata}: %%{y:.1f}<extra>resmî stok</extra>"), 2, 1)
    # Doğrudan etiketler (iki çizgi): lejant yalnız üst panelin beş öğesini taşır.
    fig.add_annotation(x=x[0] - 0.4, y=24.5, xref="x2", yref="y2", xanchor="left", yanchor="middle",
                       showarrow=False, text="türetilen stok (iç + dış borç)", font=dict(size=11, color=GRI))
    fig.add_annotation(x=2023.6, y=38.0, xref="x2", yref="y2", xanchor="center", yanchor="middle",
                       showarrow=False, text="resmî stok", font=dict(size=11, color=MUREKKEP))
    g = a["seri_gecisi"]
    gy = int(g["yil"])
    fig.add_trace(go.Scatter(x=[gy, gy], y=[g["turetilmis_d"], g["resmi_d"]], mode="lines", showlegend=False,
                             line=dict(color=MUREKKEP, width=1, dash="dot"), hoverinfo="skip"), 2, 1)
    fig.add_annotation(x=gy, y=g["resmi_d"], xref="x2", yref="y2", ax=-10, ay=-22, xanchor="right",
                       yanchor="bottom", text=f"{g['yil']} sonu fark<br>{vir(g['fark_puan'], 2)} puan", align="right",
                       hovertext="iki seri arasındaki düzey farkı hiçbir yılın değişimine girmez",
                       showarrow=True, arrowhead=0, arrowcolor=GRI, font=dict(size=10.5, color=MUREKKEP),
                       bgcolor="rgba(255,255,255,0.9)")
    fig.update_yaxes(title_text="% GSYH", row=2, col=1)

    # Resmî seri dönemi (2021 → 2026 ilk yarı) gölgeli; üstte iki dönemin adı.
    ilk_resmi = x[s["seri"].index("resmi")]
    for r in (1, 2):
        fig.add_vrect(x0=ilk_resmi - 0.5, x1=x[-1] + 0.5, fillcolor=GOLGE, line_width=0, layer="below", row=r, col=1)
    fig.add_annotation(x=(ilk_resmi - 0.5 + x[-1] + 0.5) / 2, y=1.0, xref="x", yref="y domain", yanchor="top",
                       text="resmî stok", showarrow=False, font=dict(size=11, color=MUREKKEP))
    fig.add_annotation(x=(x[0] + ilk_resmi - 1) / 2, y=1.0, xref="x", yref="y domain", yanchor="top",
                       text="türetilen stok", showarrow=False, font=dict(size=11, color=GRI))

    tv = list(range(x[0] - 1, x[-1] + 1))
    tt = [str(v) if v != x[-1] else "2026 İY" for v in tv]
    for r in (1, 2):
        fig.update_xaxes(tickmode="array", tickvals=tv, ticktext=tt, range=[x[0] - 1.6, x[-1] + 0.7], row=r, col=1)
    _paneller_sola(fig)
    fig.update_layout(title=dict(text=_baslik(
        "Şekil 09 — Borç oranını faizi aşan nominal büyüme düşürdü; kur terimi bu katkının yaklaşık üçte ikisini geri yazdı",
        f"Merkezi yönetim borç stoku / GSYH, yıllık {s['ilk']}–{x[-2]}; taralı son sütun {x[-1]} İY: ilk yarı, "
        f"{tarih(iy['ilk'])}–{tarih(s['son'])}, yıllık değil",
        f"{ilk_resmi}'den itibaren değişim resmî stoktan; öncesi iç borç + merkezi yönetim dış borcu (TCMB dönem "
        "sonu kuruyla)",
        "Kaynak: HMB bütçe ve borç istatistikleri (EVDS), TCMB · faiz dışı denge terimi fazlanın eksi işaretlisidir",
        "Artık: Hazine nakit hesabı, iskontolu ihraç, endeksli tahvil anaparası, dolar dışı değerleme, kapsam farkı,",
        f"{gy}'ye kadar iki stok tabanı arasındaki sapmanın değişimi · Δd = dört terimin toplamı")))
    _yaz(fig, "09_borc_ayrisimi.html", 840)


# ═══════════════════════════════════════════════════════════════ Şekil 10
def s10_pb_yildiz_fan(o: dict) -> None:
    b = o["b06"]
    s = b["sekil_10"]
    p = b["p6b"]
    iz = s["izgara"]
    bg = s["bugun"]
    mf = s["marjinal_faizle"]
    fan = s["kur_fani"]
    kkm = p["kkm"]
    rg, dd = iz["r_eksi_g_puan"], iz["d_yuzde"]
    z = [[iz["pb_yildiz_gsyh"][i][j] for i in range(len(rg))] for j in range(len(dd))]   # z[d][r−g]
    ceyrek = f"{bg['ceyrek'][:4]}Ç{bg['ceyrek'][-1]}"
    zr = kkm["toplam_zirve"]
    zr_ay = ay(zr["ay"] + "-01")

    fig = make_subplots(rows=2, cols=1, row_heights=[0.62, 0.38], vertical_spacing=0.17,
                        subplot_titles=("Borcu sabit tutan faiz dışı fazla pb* (% GSYH)",
                                        "Kur şokunun anlık etkisi (GSYH puanı)"))
    fdd = bg["fdd_gsyh"]
    # Bugünkü faiz dışı dengeyle borç oranının düştüğü (pb* < fdd) ve arttığı bölge.
    fig.add_trace(go.Contour(x=rg, y=dd, z=z, contours=dict(start=fdd, end=fdd, size=1, coloring="fill"),
                             colorscale=[[0, ACIK_MAVI], [1, ACIK_CLARET]], showscale=False, line=dict(width=0),
                             hoverinfo="skip", showlegend=False), 1, 1)
    fig.add_trace(go.Contour(x=rg, y=dd, z=z, contours=dict(start=-8, end=4, size=2, coloring="none", showlabels=True,
                                                            labelfont=dict(size=11, color="#5a5a5a")),
                             line=dict(color=GRI, width=1), showscale=False, showlegend=True,
                             name="pb* eşyükselti çizgisi (% GSYH)",
                             hovertemplate="r − g %{x:.0f} puan · borç %%{y:.0f} → pb* %{z:.2f} (% GSYH)<extra></extra>"), 1, 1)
    fig.add_trace(go.Contour(x=rg, y=dd, z=z, contours=dict(start=fdd, end=fdd, size=1, coloring="none"),
                             line=dict(color=CLARET, width=2, dash="dash"), showscale=False, showlegend=True,
                             name=f"pb* = bugünkü faiz dışı fazla ({yuzde(fdd, 2)}, son dört çeyrek)",
                             hoverinfo="skip"), 1, 1)
    fig.add_vline(x=0, line=dict(color=MUREKKEP, width=1.2), row=1, col=1)
    fig.add_annotation(x=0, y=dd[-1], xref="x", yref="y", text="r = g", showarrow=False, xanchor="right", xshift=-4,
                       yanchor="top", font=dict(size=11, color=MUREKKEP))
    fig.add_annotation(x=rg[0] + 1, y=dd[-1] - 2, xref="x", yref="y", xanchor="left", yanchor="top",
                       text="bugünkü faiz dışı fazlayla<br>borç oranı düşer (kur hariç)", showarrow=False,
                       font=dict(size=11, color=MAVI), align="left", bgcolor="rgba(255,255,255,0.75)")
    fig.add_annotation(x=rg[-1] - 0.3, y=dd[-1] - 2, xref="x", yref="y", xanchor="right", yanchor="top",
                       text="artar", showarrow=False, font=dict(size=11, color=CLARET),
                       bgcolor="rgba(255,255,255,0.75)")

    # Bugünkü nokta üç ayrı faizle (aynı borç oranı, aynı nominal büyüme)
    noktalar = (
        (bg["r_eksi_g_puan"], bg["pb_yildiz_gsyh"],
         f"{ceyrek}, örtük faiz {yuzde(p['bugun']['ortuk_faiz_yuzde'], 1)}",
         f"<br>pb* {yuzde(bg['pb_yildiz_gsyh'], 2)} (kur dahil {yuzde(p['bugun']['pb_yildiz_kur_ile_gsyh'], 2)})",
         "circle", 11, -6, 56, "left"),
        (mf["n5y"]["r_eksi_g_puan"], mf["n5y"]["pb_yildiz_gsyh"], f"5 yıllık DİBS {yuzde(mf['n5y']['faiz_yuzde'], 1)}",
         f"<br>pb* {yuzde(mf['n5y']['pb_yildiz_gsyh'], 2)}", "circle-open", 10, 0, 118, "center"),
        (mf["n2y"]["r_eksi_g_puan"], mf["n2y"]["pb_yildiz_gsyh"], f"2 yıllık DİBS {yuzde(mf['n2y']['faiz_yuzde'], 1)}",
         f"<br>pb* {yuzde(mf['n2y']['pb_yildiz_gsyh'], 2, arti=True)}", "diamond-open", 10, 4, 56, "left"),
    )
    for xv, pb, ad, ek, sembol, boy, ax, ay_, yasla in noktalar:
        fig.add_trace(go.Scatter(x=[xv], y=[bg["d_yuzde"]], mode="markers", showlegend=False,
                                 marker=dict(size=boy, color=MUREKKEP, symbol=sembol, line=dict(width=1.6, color=MUREKKEP)),
                                 hovertemplate=f"{ad}: r − g {vir(xv, 2)} puan · borç %{{y:.2f}} · pb* {yuzde(pb, 2)}"
                                               "<extra></extra>"),
                      1, 1)
        fig.add_annotation(x=xv, y=bg["d_yuzde"], xref="x", yref="y", ax=ax, ay=-ay_, showarrow=True,
                           arrowhead=0, arrowwidth=1, arrowcolor=GRI, xanchor=yasla, yanchor="bottom", align="left",
                           text=ad + ek, font=dict(size=10.5, color=MUREKKEP), bgcolor="rgba(255,255,255,0.88)")
    fig.update_xaxes(title_text="r − g: faiz − nominal büyüme (puan)", range=[rg[0] - 0.4, rg[-1] + 0.4], dtick=5,
                     row=1, col=1)
    fig.update_yaxes(title_text="borç stoku / GSYH (%)", range=[dd[0] - 1.5, dd[-1] + 1], row=1, col=1)

    # Kur şoku fanı: borç oranının sıçraması (bugün) ve KKM'nin brüt kur maliyeti (zirve ayı).
    # Şok sonrası pb* (örtük faizle) alt başlıkta ve ipucunda: borç oranı sıçrar, pb* az kımıldar.
    kat = [f"+%{k['kur_artisi_yuzde']}" for k in fan["soklar"]]
    fig.add_trace(go.Bar(x=kat, y=[k["delta_d_puan"] for k in fan["soklar"]], offsetgroup="borc",
                         name=f"borç oranı sıçraması, {ceyrek} (döviz payı {yuzde(fan['alfa_yuzde'], 1)})",
                         marker_color=MAVI, marker_line_width=0,
                         text=[f"+{vir(k['delta_d_puan'], 2)}" for k in fan["soklar"]], textposition="outside",
                         textfont=dict(size=11, color=MUREKKEP), cliponaxis=False,
                         customdata=[[k["kur_artisi_yuzde"], yuzde(k["d_yeni"], 2), yuzde(k["pb_yildiz_yeni_gsyh"], 2)]
                                     for k in fan["soklar"]],
                         hovertemplate="USD/TRY +%%{customdata[0]}: borç oranı +%{y:.2f} puan → %{customdata[1]}; "
                                       "pb* %{customdata[2]}<extra></extra>"), 2, 1)
    dv = [k["doviz_donusumlu_gsyh_yuzde"] for k in zr["soklar"]]
    tl = [k["tl_kkm_gsyh_yuzde"] for k in zr["soklar"]]
    yuzdeler = [k["kur_artisi_yuzde"] for k in zr["soklar"]]
    fig.add_trace(go.Bar(x=kat, y=dv, offsetgroup="kkm", name=f"KKM döviz dönüşümlü, {zr_ay}",
                         marker_color=TURUNCU, marker_line_width=0, customdata=yuzdeler,
                         hovertemplate="USD/TRY +%%{customdata}: döviz dönüşümlü KKM %{y:.2f} puan"
                                       "<extra></extra>"), 2, 1)
    fig.add_trace(go.Bar(x=kat, y=tl, base=dv, offsetgroup="kkm", name=f"KKM TL'den dönüşen, {zr_ay}",
                         marker_color=ACIK_TURUNCU, marker_line_width=0, customdata=yuzdeler,
                         hovertemplate="USD/TRY +%%{customdata}: TL'den dönüşen KKM %{y:.2f} puan<extra></extra>"),
                  2, 1)
    sa = kkm["son_ay"]
    fig.add_annotation(x=1.0, y=1.0, xref="x2 domain", yref="y2 domain", xanchor="right", yanchor="top",
                       text=(f"{ay(sa['ay'] + '-01')}: KKM stoku {vir(sa['toplam_mlr_tl'], 2)} milyar TL;<br>"
                             f"+%{sa['soklar'][-1]['kur_artisi_yuzde']} şokta maliyet GSYH'nin "
                             f"%{vir(sa['soklar'][-1]['doviz_donusumlu_gsyh_yuzde'], 4)}'i"),
                       showarrow=False, align="right", font=dict(size=10.5, color=MUREKKEP),
                       bgcolor="rgba(255,255,255,0.88)")
    fig.update_layout(barmode="group", bargap=0.30, bargroupgap=0.08)
    ust = max(a + c for a, c in zip(dv, tl))
    fig.update_yaxes(title_text="GSYH puanı", range=[0, ust * 1.45], row=2, col=1)
    fig.update_xaxes(title_text="USD/TRY'de anlık artış (TL değer kaybı)", row=2, col=1)
    _paneller_sola(fig)
    fig.update_layout(title=dict(text=_baslik(
        "Şekil 10 — Örtük faizle borç oranı faiz dışı açıkla bile sabit kalır; piyasa faiziyle bu pay daralır ya da kaybolur",
        f"pb* = (r − g)/(1 + g) × d · d: borç stoku / GSYH · g: dört çeyreklik nominal GSYH artışı, {ceyrek} "
        f"({yuzde(iz['nominal_buyume_yuzde'], 1)})",
        "r: son dört çeyreğin faiz gideri / bir yıl önceki stok (örtük faiz) ya da DİBS sıfır kupon getirisi "
        f"({tarih(mf['n2y']['piyasa_gunu'])})",
        "kur şoku: borç oranı × döviz payı (alt sınır) × kur artışı, anlık; şok sonrası pb* sırayla "
        + " · ".join(yuzde(k["pb_yildiz_yeni_gsyh"], 2) for k in fan["soklar"]) + " (örtük faizle)",
        "KKM: stok × kur artışı, mevduat faizi düşülmeden (brüt) · Kaynak: HMB bütçe ve borç istatistikleri (EVDS),",
        "TCMB DİBS gösterge değerleri, TCMB kur korumalı mevduat istatistikleri")))
    _yaz(fig, "10_pb_yildiz_fan.html", 900)


# ═══════════════════════════════════════════════════════════════ Şekil 11
ULKE = {  # rengi ülke belirler (bütün panellerde aynı)
    "GR": ("Yunanistan", MAVI), "IT": ("İtalya", CLARET), "ES": ("İspanya", TURUNCU),
    "PT": ("Portekiz", YESIL), "IE": ("İrlanda", GRI), "FR": ("Fransa", MUREKKEP),
}


OLAY_KISA = {  # alt başlıkta kısa ad (tam ad işaretin üzerine gelince görünür)
    "yunanistan_2010_2012": "Yunanistan 2010–2012", "italya_2011": "İtalya 2011",
    "ispanya_2012": "İspanya 2012", "italya_2018_mayis": "İtalya 05.2018",
    "italya_2018_butce": "İtalya bütçesi 2018",
}


def s11_cevre_farklari(o: dict) -> None:
    b = o["b06"]
    s = b["sekil_11"]
    p = b["p6d"]
    tarihler = [a + "-15" for a in s["ay"]]
    fig = make_subplots(rows=3, cols=1, row_heights=[0.27, 0.40, 0.33], vertical_spacing=0.085,
                        subplot_titles=("Yunanistan (kendi ölçeğinde)",
                                        "İtalya, İspanya, Portekiz, İrlanda, Fransa",
                                        f"Yakın plan: altısı birlikte, {ay(s['ay'][s['ay'].index('2020-01')] + '-01')} sonrası"))
    for u, (ad, renk) in ULKE.items():
        satir = 1 if u == "GR" else 2
        fig.add_trace(go.Scatter(x=tarihler, y=s[f"{u}_bp"], mode="lines", name=ad, legendgroup=u,
                                 line=dict(color=renk, width=1.5), connectgaps=False,
                                 hovertemplate="%{x|%m.%Y}: %{y:.0f} bp<extra>" + ad + "</extra>"), satir, 1)

    # Yakın plan: 2020 sonrası aylık ortalama + günlük son kapanış (ayrı işaret, çizgiyle bağlanmaz)
    i0 = s["ay"].index("2020-01")
    for u, (ad, renk) in ULKE.items():
        fig.add_trace(go.Scatter(x=tarihler[i0:], y=s[f"{u}_bp"][i0:], mode="lines", name=ad, legendgroup=u,
                                 showlegend=False, line=dict(color=renk, width=1.8 if u in ("IT", "FR") else 1.4),
                                 hovertemplate="%{x|%m.%Y}: %{y:.0f} bp<extra>" + ad + "</extra>"), 3, 1)
    gl = p["gunluk"]
    gun_son = None
    for u, (ad, renk) in ULKE.items():
        if u not in gl:
            continue
        gun_son = gl[u]["son"]
        fig.add_trace(go.Scatter(x=[gl[u]["son"]], y=[gl[u]["son_bp"]], mode="markers", legendgroup=u,
                                 showlegend=False,
                                 marker=dict(size=8, color=renk, symbol="diamond", line=dict(width=0.8, color="white")),
                                 hovertemplate=f"{tarih(gl[u]['son'])}: %{{y:.1f}} bp<extra>{ad}, günlük</extra>"), 3, 1)
    fr, it = gl["FR"], gl["IT"]
    fig.add_annotation(x=fr["son"], y=fr["son_bp"], xref="x3", yref="y3", ax=-6, ay=-24, showarrow=True,
                       xanchor="right", yanchor="bottom",
                       arrowhead=0, arrowcolor=GRI, font=dict(size=10.5, color=MUREKKEP), align="right",
                       bgcolor="rgba(255,255,255,0.88)",
                       text=f"{tarih(fr['son'])} günlük<br>Fransa {vir(fr['son_bp'], 1)} bp<br>"
                            f"İtalya {vir(it['son_bp'], 1)} bp")

    # Olay pencereleri: gölge + numara; açıklama alt başlıkta
    ol = s["olaylar"]
    for k, r in enumerate(ol, start=1):
        satir = 1 if r["ulke"] == "GR" else 2
        x0 = r["ilk"] + ("-01" if len(r["ilk"]) == 7 else "")
        x1 = r["son"] + ("-28" if len(r["son"]) == 7 else "")
        fig.add_vrect(x0=x0, x1=x1, fillcolor=GOLGE, line_width=0, layer="below", row=satir, col=1)
        yuk = 0.97 if k % 2 else 0.84
        if satir == 1:      # Yunanistan penceresinin numarası zirve etiketinde durur
            continue
        fig.add_annotation(x=x0, y=yuk, xref="x2", yref="y2 domain",
                           xanchor="right", yanchor="top", text=f"{k}", showarrow=False,
                           font=dict(size=11, color=MUREKKEP), hovertext=r["ad"])
        if "zirve_gunu" in r:  # günlük olay zirvesi (Avrupa kapanışı) aylık ortalamanın üstünde
            adr, renk = ULKE[r["ulke"]]
            fig.add_trace(go.Scatter(x=[r["zirve_gunu"]], y=[r["zirve_bp"]], mode="markers", legendgroup=r["ulke"],
                                     showlegend=False,
                                     marker=dict(size=7, color="white", symbol="diamond",
                                                 line=dict(width=1.5, color=renk)),
                                     hovertemplate=(f"{r['ad']}: {tarih(r['zirve_gunu'])} günlük zirve "
                                                    "%{y:.1f} bp<extra></extra>")), 2, 1)
    # Yunanistan: aylık seride 07.2015 yok; günlük zirve o ay
    g = gl["GR"]
    fig.add_trace(go.Scatter(x=[g["azami_gunu"]], y=[g["azami_bp"]], mode="markers", legendgroup="GR",
                             showlegend=False, marker=dict(size=7, color="white", symbol="diamond",
                                                           line=dict(width=1.5, color=MAVI)),
                             hovertemplate=f"{tarih(g['azami_gunu'])} günlük kapanış %{{y:.1f}} bp<extra>Yunanistan"
                                           "</extra>"), 1, 1)
    eksik_ay = ay(g["azami_gunu"])
    fig.add_annotation(x=g["azami_gunu"], y=g["azami_bp"], xref="x", yref="y", ax=14, ay=6, showarrow=True,
                       arrowhead=0, arrowcolor=GRI, xanchor="left", yanchor="top", align="left",
                       font=dict(size=10.5, color=MUREKKEP), bgcolor="rgba(255,255,255,0.88)",
                       text=f"{tarih(g['azami_gunu'])} günlük {vir(g['azami_bp'], 0)} bp<br>"
                            f"({eksik_ay} aylık seride yok)")
    gz = next(r for r in ol if r["ulke"] == "GR")
    fig.add_annotation(x=gz["zirve_ayi"] + "-15", y=gz["zirve_bp"], xref="x", yref="y", ax=12, ay=0, showarrow=True,
                       arrowhead=0, arrowcolor=GRI, xanchor="left", align="left",
                       font=dict(size=10.5, color=MUREKKEP), bgcolor="rgba(255,255,255,0)",
                       text=f"{ol.index(gz) + 1} · {ay(gz['zirve_ayi'] + '-01')} aylık ortalama "
                            f"{vir(gz['zirve_bp'], 0)} bp",
                       hovertext=gz["ad"])

    fig.update_xaxes(matches="x", row=2, col=1)
    fig.update_xaxes(range=[s["ay"][0] + "-01", "2026-12-31"], row=1, col=1)
    fig.update_xaxes(range=["2019-12-01", "2026-11-15"], row=3, col=1)
    for r in (1, 2, 3):
        fig.update_yaxes(title_text="fark (bp)", rangemode="tozero", row=r, col=1)
    _paneller_sola(fig)
    fig.update_layout(legend=dict(traceorder="normal"))
    ol_metin = " · ".join(f"{k} {OLAY_KISA.get(r['kimlik'], r['ad'])}" for k, r in enumerate(ol, start=1))
    fig.update_layout(title=dict(text=_baslik(
        "Şekil 11 — Avro krizinde çevre farkları yüzlerce baz puana açıldı; Eylül 2026 sonunda Fransa'nınki "
        "İtalya'nınkinin üstünde",
        "Ülke 10 yıllık − Almanya 10 yıllık getiri farkı (bp) · çizgiler ECB Maastricht ölçütü, aylık ortalama "
        f"{ay(s['ilk'] + '-01')}–{ay(s['son'] + '-01')}",
        f"◆ {tarih(gun_son)} günlük kapanış · ◇ olay penceresinde günlük zirve · ikisi de CNBC, Avrupa kapanışı",
        "Aylık ortalama günlük zirveyi düzleştirir · İrlanda'nın günlük serisi yok",
        f"Gölgeler: {ol_metin}")))
    _yaz(fig, "11_cevre_farklari.html", 920)
