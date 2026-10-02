#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 11 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

import re

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)

DONEM_GOLGE = "rgba(138,138,138,0.16)"
VIX_GOLGE = "rgba(184,134,11,0.16)"


def _panel_basliklari(fig, n: int, boyut: float = 12.5) -> None:
    """Panel başlıkları sola yaslı ve gövde boyunda: dar ekranda ortalı büyük başlık taşar."""
    for a in list(fig.layout.annotations)[:n]:
        a.update(x=0, xanchor="left", font=dict(size=boyut, color=MUREKKEP))


def _ay1(a: str) -> str:
    """'YYYY-MM' → 'YYYY-MM-01' (çizim ve tarih biçimi için)."""
    return a if len(a) >= 10 else f"{a[:7]}-01"


def _ay_orta(a: str) -> str:
    """Aylık gözlemi ayın ortasına koyar; gölgeler ayın başından sonraki ayın başına uzanır."""
    return f"{a[:7]}-15"


def _sonraki_ay(a: str) -> str:
    y, m = int(a[:4]), int(a[5:7])
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return f"{y:04d}-{m:02d}-01"


def _ay_say(a: str) -> int:
    return int(a[:4]) * 12 + int(a[5:7])


def _bloklar(tarihler: list, bayrak: list) -> list:
    """Ardışık bayraklı ayları [ilk ay, son ay] bloklarına toplar."""
    out, bas, onceki = [], None, None
    for t, f in zip(tarihler, bayrak):
        if f and bas is None:
            bas = t
        elif f and onceki is not None and _ay_say(t) - _ay_say(onceki) != 1:
            out.append((bas, onceki))
            bas = t
        elif not f and bas is not None:
            out.append((bas, onceki))
            bas = None
        if f:
            onceki = t
    if bas is not None:
        out.append((bas, onceki))
    return out


def _etiket(e: str) -> str:
    """Ölçümdeki çubuk adını kısa eksen etiketine çevirir; dönem dizgesi AA.YYYY yazılır.

    Yönetilen kuru dışarıda bırakan satırların ayracı etikete girmez (alt başlık söyler):
    iki satırlı komşu etiketler 390 px'te birbirine değiyordu. Yalnız yönetilen kur
    satırı dönemini ikinci satırda taşır."""
    e = re.sub(r"(\d{4})-(\d{2}) … (\d{4})-(\d{2})", r"\2.\1–\4.\3", e)
    if e.startswith("TRY yönetilen kur "):
        return "TRY yönetilen kur<br>" + e[len("TRY yönetilen kur "):]
    e = re.sub(r" \(yönetilen( kur)? hariç\)$", "", e)
    return e


# ───────────────────────────────────────────────────────────── Şekil 21
def s18_fama_beta(o: dict) -> None:
    b = o["b11"]
    s = b["sekil_18"]
    p = b["p11a"]
    cub = s["cubuk"]
    ayri = [("yönetilen" in c["etiket"] and "hariç" not in c["etiket"]) for c in cub]
    havuz = [("havuz" in c["etiket"]) or ("1990–2026" in c["etiket"]) for c in cub]
    normal = [c for c, a in zip(cub, ayri) if not a]
    xmin = min(c["alt"] for c in normal) - 0.5
    xmax = max(c["ust"] for c in normal) + 0.5
    n_para = p["g10"]["havuz"]["para_sayisi"]
    g10_yil = f"{p['g10']['havuz']['ilk'][:4]}–{p['g10']['havuz']['son'][:4]}"
    etiket = [f"G10 havuz ({n_para} para)" if c["etiket"] == "G10 havuz" else _etiket(c["etiket"]) for c in cub]
    tr_hep_alti = all(c["beta"] < 1 for c in cub if c["grup"] == "TRY")
    # aralığın tamamı 1'in altında mı: yönetilen kur satırı (19 ay, tasarım gereği bilgi taşımaz) hariç
    tr_aralik = [c for c, a in zip(cub, ayri) if c["grup"] == "TRY" and not a]
    tr_aralik_alti = sum(c["ust"] < 1 for c in tr_aralik)
    g10 = [c for c in cub if c["grup"] == "G10"]
    g10_kapsar = all(c["alt"] < 0 < c["ust"] and c["alt"] < 1 < c["ust"] for c in g10)

    k = s["kayan"]
    fig = make_subplots(rows=2, cols=1, row_heights=[0.6, 0.4], vertical_spacing=0.155,
                        subplot_titles=("Fama β ve ±2 standart hata",
                                        f"TRY: {k['pencere_ay']} aylık kayan β"))
    _panel_basliklari(fig, 2)
    for grup, renk, ad in (("TRY", CLARET, "TRY dönemleri"), ("G10", MAVI, f"G10 paraları ({g10_yil})")):
        idx = [i for i, c in enumerate(cub) if c["grup"] == grup]
        x, alt, ust = [], [], []
        for i in idx:
            c = cub[i]
            x.append(c["beta"])
            ust.append(min(c["ust"], xmax) - c["beta"])
            alt.append(c["beta"] - max(c["alt"], xmin))
        fig.add_trace(go.Bar(
            y=[etiket[i] for i in idx], x=x, orientation="h", name=ad,
            marker=dict(color=[renk] * len(idx), opacity=[0.45 if ayri[i] else 1.0 for i in idx],
                        pattern=dict(shape=["/" if havuz[i] else "" for i in idx], fgcolor="white", size=6),
                        line=dict(width=0)),
            error_x=dict(type="data", symmetric=False, array=ust, arrayminus=alt, color=MUREKKEP, thickness=1.3,
                         width=4),
            customdata=[[vir(cub[i]["beta"], 2), vir(cub[i]["alt"], 2), vir(cub[i]["ust"], 2), cub[i]["n"]] for i in idx],
            hovertemplate="%{y}<br>β %{customdata[0]} · aralık %{customdata[1]} … %{customdata[2]} · "
                          "n %{customdata[3]} ay<extra></extra>"), 1, 1)
    fig.add_trace(go.Bar(y=[None], x=[None], orientation="h", name="taralı: havuzlu ya da tam örneklem",
                         marker=dict(color="white", line=dict(color=MUREKKEP, width=1),
                                     pattern=dict(shape="/", fgcolor=MUREKKEP, size=6)),
                         hoverinfo="skip"), 1, 1)
    fig.add_vline(x=0, line=dict(color=GRI, width=1.4), row=1, col=1)
    fig.add_vline(x=1, line=dict(color=MUREKKEP, width=1.4, dash="dash"), row=1, col=1)
    for i, c in enumerate(cub):                      # β sütunu sağ kenarda; kırpılan aralık adıyla
        fig.add_annotation(x=1.005, xref="paper", y=etiket[i], yref="y", text=vir(c["beta"], 2), showarrow=False,
                           xanchor="left", font=dict(size=11, color=MUREKKEP))
        if c["alt"] < xmin or c["ust"] > xmax:          # kırpılan uç üçgenle, tam aralık yazıyla
            uclar = [(xmin, "triangle-left")] * (c["alt"] < xmin) + [(xmax, "triangle-right")] * (c["ust"] > xmax)
            fig.add_trace(go.Scatter(x=[u[0] for u in uclar], y=[etiket[i]] * len(uclar), mode="markers",
                                     marker=dict(symbol=[u[1] for u in uclar], size=9, color=MUREKKEP),
                                     cliponaxis=False, showlegend=False,
                                     hovertemplate=f"aralık {vir(c['alt'], 2)} … {vir(c['ust'], 2)}<extra></extra>"),
                          1, 1)
            # yazı çizginin ÜSTÜNDE: altında bir sonraki satırın (tam örneklem) bıyığına biniyordu
            fig.add_annotation(x=xmax, y=etiket[i], xref="x", yref="y", yshift=2, xshift=-12,
                               text=f"aralık {vir(c['alt'], 2)} … {vir(c['ust'], 2)}",
                               showarrow=False, xanchor="right", yanchor="bottom", font=dict(size=10, color=GRI))
    fig.add_annotation(x=1.005, xref="paper", y=1.0, yref="y domain", text="β", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=11, color=MUREKKEP))
    fig.update_xaxes(range=[xmin, xmax], dtick=1, zeroline=False, title_text="β (düz çizgi 0 · kesikli çizgi 1 = faiz paritesi)",
                     row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=1, col=1)

    # kayan β: yönetilen kur aylarının boşluğunda çizgi kesilir
    t = [_ay1(x) for x in k["tarih"]]
    kes = [i for i in range(1, len(t)) if _ay_say(t[i]) - _ay_say(t[i - 1]) != 1]
    sinir = [0] + kes + [len(t)]
    YMIN, YMAX = -14.0, 15.0
    for j in range(len(sinir) - 1):
        a, z = sinir[j], sinir[j + 1]
        fig.add_trace(go.Scatter(x=t[a:z], y=k["alt"][a:z], mode="lines", line=dict(width=0), showlegend=False,
                                 hoverinfo="skip", legendgroup="bant"), 2, 1)
        fig.add_trace(go.Scatter(x=t[a:z], y=k["ust"][a:z], mode="lines", line=dict(width=0), fill="tonexty",
                                 fillcolor=ACIK_CLARET, name="±2 standart hata", showlegend=(j == 0),
                                 legendgroup="bant", hoverinfo="skip"), 2, 1)
        fig.add_trace(go.Scatter(x=t[a:z], y=k["beta"][a:z], mode="lines", line=dict(color=CLARET, width=2),
                                 name="kayan β (pencerenin son sinyal ayı)", showlegend=(j == 0), legendgroup="kb",
                                 hovertemplate="%{x|%m.%Y}: β %{y:.2f}<extra></extra>"), 2, 1)
    for i in kes:
        fig.add_vrect(x0=_sonraki_ay(t[i - 1]), x1=t[i], fillcolor=DONEM_GOLGE, line_width=0, layer="below",
                      row=2, col=1)
        fig.add_annotation(x=_sonraki_ay(t[i - 1]), y=0.02, xref="x2", yref="y2 domain", text="yönetilen kur",
                           showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=10, color=GRI))
    fig.add_hline(y=0, line=dict(color=GRI, width=1.4), row=2, col=1)
    fig.add_hline(y=1, line=dict(color=MUREKKEP, width=1.4, dash="dash"), row=2, col=1)
    tas = [i for i, u in enumerate(k["ust"]) if u > YMAX]
    if tas:
        j = max(tas, key=lambda i: k["ust"][i])
        fig.add_annotation(x=t[j], y=YMAX, xref="x2", yref="y2", text=f"bandın üst ucu {vir(k['ust'][j], 1)}",
                           showarrow=False, xanchor="left", yanchor="top", xshift=4, font=dict(size=10, color=GRI))
    fig.update_yaxes(range=[YMIN, YMAX], title_text="β", row=2, col=1)
    fig.update_xaxes(range=[t[0], _sonraki_ay(t[-1])], row=2, col=1)

    # Başlık NOKTA kestirimini söyler; aralık hükmü alt başlıkta, sayımıyla (yönetilen kur hariç).
    baslik = ("Şekil 21 — Faiz farkı kura bire bir yansımadı: TRY'nin Fama β'sı her dönemde 1'in altında"
              if tr_hep_alti else "Şekil 21 — TRY'nin Fama β'sı dönemden döneme 1'in iki yanına düşüyor")
    if tr_aralik_alti == len(tr_aralik):
        aralik_bulgu = f"yönetilen kur dışındaki {len(tr_aralik)} TRY aralığının hepsi 1'in altında"
    else:
        aralik_bulgu = f"yönetilen kur dışındaki {len(tr_aralik)} TRY aralığından {tr_aralik_alti} tanesi 1'in altında"
    g10_bulgu = (" · G10'da bütün aralıklar hem 0'ı hem 1'i kapsıyor" if g10_kapsar else "")
    fig.update_layout(barmode="overlay", bargap=0.35, title=dict(text=(
        f"{baslik}"
        f"<br><sub>Aylık, {ay(_ay1(s['ilk']))}–{ay(_ay1(s['son']))} (sinyal ayı) · ertesi ayın kur log değişimi "
        "= a + β·(TL faizi − ABD faizi)/12"
        "<br>artış: yerel para değer kaybeder · TL gecelik faiz zinciri, ABD ve G10 politika faizleri (BIS)"
        "<br>forward yerine faiz farkı (örtülü faiz paritesi varsayımı) · yönetilen kur ayları yalnız kendi "
        f"satırında<br>{aralik_bulgu}{g10_bulgu}</sub>")),
        legend=dict(traceorder="normal"))
    _yaz(fig, "21_fama_beta.html", 900)


# ───────────────────────────────────────────────────────────── Şekil 22
def s19_em_tasima_vix(o: dict) -> None:
    b = o["b11"]
    s = b["sekil_19"]
    vk = b["p11b"]["sepet"]["vix_kosullu"]
    vh = b["p11b"]["sepet_try_haric"]["vix_kosullu"]
    n_para = len(b["p11b"]["paralar"])
    em_ad = ", ".join(k.upper() for k in b["p11b"]["paralar"] if k != "try")
    t = [_ay_orta(x) for x in s["tarih"]]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.6, 0.4], vertical_spacing=0.09,
                        subplot_titles=("EM taşıma sepeti: kümülatif getiri", "VIX: ay ortalaması ve eşik"))
    _panel_basliklari(fig, 2)
    fig.add_trace(go.Scatter(x=t, y=s["sepet_kumulatif_yuzde"], mode="lines", name=f"sepet, TRY dahil ({n_para} para)",
                             line=dict(color=CLARET, width=2.2),
                             hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra>TRY dahil</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=s["sepet_try_haric_kumulatif_yuzde"], mode="lines",
                             name=f"sepet, TRY hariç ({em_ad})", line=dict(color=MAVI, width=2.2),
                             hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra>TRY hariç</extra>"), 1, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=1), row=1, col=1)
    fig.add_trace(go.Scatter(x=t, y=s["vix_ay_ort"], mode="lines", name="VIX ay ortalaması",
                             line=dict(color=MUREKKEP, width=1.5),
                             hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra>VIX</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=t, y=s["vix_esik"], mode="lines",
                             name="eşik: önceki ayların ortalamalarının 75. yüzdeliği",
                             line=dict(color=TURUNCU, width=1.6, dash="dash"),
                             hovertemplate="%{x|%m.%Y}: %{y:.1f}<extra>eşik</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name="gölge: VIX eşiğin üstünde",
                             marker=dict(symbol="square", size=12, color="rgba(184,134,11,0.35)"),
                             hoverinfo="skip"), 2, 1)
    for i0, i1 in _bloklar(s["tarih"], s["yuksek_vix"]):      # gölge izlerden SONRA: boş panel atlanır
        for r in (1, 2):
            fig.add_vrect(x0=_ay1(i0), x1=_sonraki_ay(i1), fillcolor=VIX_GOLGE, line_width=0, layer="below",
                          row=r, col=1)
    fig.update_yaxes(title_text="kümülatif log getiri, %", row=1, col=1)
    fig.update_yaxes(title_text="VIX", row=2, col=1)
    son_dahil, son_haric = s["sepet_kumulatif_yuzde"][-1], s["sepet_try_haric_kumulatif_yuzde"][-1]

    # Başlık koşullu ortalamaları SAYISIYLA söyler: "eksi" tek başına farkın büyüklüğünü ve
    # öbür ayların işaretini gizliyordu. Farkın gücü (t) alt başlıkta, tarif olarak.
    vix_bulgu = (f"{n_para} paralı EM taşıma sepeti yüksek VIX aylarında ayda ortalama {yuzde(vk['ort_yuksek_aylik_yuzde'], 2, True)}, "
                 f"öbür aylarda {yuzde(vk['ort_diger_aylik_yuzde'], 2, True)} getirdi")
    # Eşiğin genişleyen penceresinin başlangıç yılı ölçümde bir alan olarak yok: figüre yazılmaz.
    fig.update_layout(title=dict(text=(
        f"Şekil 22 — {vix_bulgu}"
        f"<br><sub>Aylık, {ay(_ay1(s['ilk']))}–{ay(_ay1(s['son']))} · son kümülatif log getiri: TRY dahil "
        f"{yuzde(son_dahil, 1, True)}, TRY hariç {yuzde(son_haric, 1, True)}"
        "<br>yerel para alınır, dolar borçlanılır · getiri = önceki ay sonu politika faizi farkı/12 − aylık kur "
        "log değişimi"
        "<br>eşit ağırlıklı sepet · kümülatif = aylık log getirilerin toplamı · VIX eşiği yalnız önceki ayların "
        f"verisinden<br>TRY hariç sepette {yuzde(vh['ort_yuksek_aylik_yuzde'], 2, True)} ve "
        f"{yuzde(vh['ort_diger_aylik_yuzde'], 2, True)} · farkın t'si {vir(vk['fark_t'], 2)} (TRY dahil): aynı "
        "ayın VIX'iyle, öngörü değil</sub>")))
    _yaz(fig, "22_em_tasima_vix.html", 780)


# ───────────────────────────────────────────────────────────── Şekil 23
def s20_try_artik_akim(o: dict) -> None:
    b = o["b11"]
    s = b["sekil_20"]
    t = s["tarih"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.5, 0.5], vertical_spacing=0.09,
                        subplot_titles=("TRY'nin EM sepetine göre kümülatif artığı", "Yabancıların kümülatif net alımı"))
    _panel_basliklari(fig, 2)
    yon = [x for x, f in zip(t, s["yonetilen"]) if f]
    fig.add_trace(go.Scatter(x=t, y=s["try_artik_kumulatif_yuzde"], mode="lines", name="TRY artığı, kümülatif",
                             line=dict(color=CLARET, width=2.2),
                             hovertemplate="%{x|%d.%m.%Y}: %{y:.1f}<extra>TRY artığı</extra>"), 1, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=1), row=1, col=1)
    for anahtar, renk, ad, gen in (("akim_dibs_kumulatif_milyar_usd", MAVI, "DİBS (kesin alım)", 2.2),
                                   ("akim_hisse_kumulatif_milyar_usd", TURUNCU, "hisse senedi", 2.2),
                                   ("akim_toplam_kumulatif_milyar_usd", MUREKKEP, "toplam (DİBS + hisse)", 1.2)):
        fig.add_trace(go.Scatter(x=t, y=s[anahtar], mode="lines", name=f"yabancı akımı: {ad}",
                                 line=dict(color=renk, width=gen, dash="dot" if ad.startswith("toplam") else None),
                                 hovertemplate="%{x|%d.%m.%Y}: %{y:.2f}<extra>" + ad + "</extra>"), 2, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=1), row=2, col=1)
    if yon:                                                      # gölge izlerden SONRA: boş panel atlanır
        for r in (1, 2):
            fig.add_vrect(x0=yon[0], x1=yon[-1], fillcolor=DONEM_GOLGE, line_width=0, layer="below", row=r, col=1)
        fig.add_annotation(x=yon[0], y=0.98, xref="x", yref="y domain", text="yönetilen kur dönemi",
                           showarrow=False, xanchor="left", yanchor="top", xshift=4, font=dict(size=11, color=GRI))
    fig.update_yaxes(title_text="% (log; artış: TL fazladan zayıflar)", row=1, col=1)
    fig.update_yaxes(title_text="milyar ABD doları (artı: net alım)", row=2, col=1)
    artik = [x for x in s["try_artik_kumulatif_yuzde"] if x is not None]
    dibs = s["akim_dibs_kumulatif_milyar_usd"]
    son_yon = max(i for i, f in enumerate(s["yonetilen"]) if f) if yon else None
    bulgu1 = ("Lira EM sepetinin açıkladığından fazla değer kaybetti" if artik[-1] > 0
              else "Lira EM sepetinin açıkladığından az değer kaybetti")
    if son_yon is not None and dibs[-1] - dibs[son_yon] > abs(dibs[son_yon]):
        bulgu2 = "yabancı DİBS alımı yönetilen kurdan sonra birikti"
    else:
        bulgu2 = "yabancı DİBS ve hisse akımı aynı yönde değil" if dibs[-1] * s["akim_hisse_kumulatif_milyar_usd"][-1] < 0 \
            else "yabancı akımı iki piyasada aynı yönde"
    # Artık regresyonun sabit terimini taşır: yönetilen kurdan sonraki ortalaması ve son eğim
    # alt başlıkta SAYISIYLA durur, yoksa "açıkladığından fazla" bir şok gibi okunur.
    ta = b["p11c"]["try_artik"]
    egilim = (f"artık TL'nin kendi değer kaybı eğilimini taşır: yönetilen kurdan sonra yılda ortalama "
              f"{yuzde(ta['sonrasi_yillik_ort_yuzde'], 1, True)}, son sepet eğimi {vir(ta['son_beta'], 2)}")
    fig.update_layout(title=dict(text=(
        f"Şekil 23 — {bulgu1}; {bulgu2}"
        f"<br><sub>Haftalık (perşembe kapanışı, cuma etiketli), {tarih(s['ilk'])}–{tarih(s['son'])} · akım: yurt "
        "dışı yerleşiklerin net alımı (TCMB)"
        "<br>artık = TRY'nin haftalık log değişimi − önceki 52 haftanın eğimi × EM sepeti (BRL, MXN, ZAR, INR)"
        f"<br>{egilim}"
        f"<br>EM kurlarının serisi bittiği için artık {tarih(s['artik_son'])} haftasında durur</sub>")))
    _yaz(fig, "23_try_artik_akim.html", 800)
