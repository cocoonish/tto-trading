#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 9 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

import re

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz, baslik_koy, yukseklik)


def _paneller_sola(fig, boyut: int = 13) -> None:
    """Panel başlıkları sola yaslanır: dar ekranda ortalı başlık iki uçtan birden kırpılıyordu."""
    for an in fig.layout.annotations:
        if an.yref == "paper" and an.yanchor == "bottom" and an.xref == "paper":
            an.update(x=0, xanchor="left", font=dict(size=boyut, color=MUREKKEP))


def _donem_etiketi(ad: str, v: dict) -> str:
    """Dönem adı: yıl aralığıysa olduğu gibi, değilse kendi ilk/son haftasının ayından (AA.YYYY)."""
    if re.fullmatch(r"\d{4}–\d{4}", ad):
        return ad
    aralik = f"{ay(v['ilk'])}–{ay(v['son'])}"
    return f"yönetilen kur<br>{aralik}" if ad.startswith("yönetilen kur") else aralik


def s16_kur_baskisi(o: dict) -> None:
    b = o["b09"]
    s = b["sekil_16"]
    p = b["p9b"]
    d = p["donemler"]
    fig = make_subplots(rows=2, cols=1, row_heights=[0.64, 0.36], vertical_spacing=0.15,
                        subplot_titles=("Haftalık bileşenlerin ay içi toplamı (σ birimi)",
                                        "Dönemlere göre bileşen payları"))
    for ad, renk, etiket in (("kur", MAVI, "kur (TL değer kaybı)"), ("rezerv", CLARET, "rezerv kaybı"),
                             ("faiz", TURUNCU, "fonlama maliyeti artışı")):
        fig.add_trace(go.Bar(x=s["tarih"], y=s[ad], name=etiket, marker_color=renk, marker_line_width=0,
                             hovertemplate="%{x|%m.%Y}: %{y:.2f}<extra>" + etiket + "</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["emp"], mode="lines", name="endeks (bileşenlerin toplamı)",
                             line=dict(color=MUREKKEP, width=1.2),
                             hovertemplate="%{x|%m.%Y}: %{y:.2f}<extra>endeks</extra>"), 1, 1)
    fig.update_layout(barmode="relative", bargap=0.05)
    fig.update_yaxes(title_text="σ (haftalık birim, ay içi toplam)", row=1, col=1)
    fig.update_xaxes(zeroline=False, row=1, col=1)
    adlar = sorted(d, key=lambda k: d[k]["ilk"])             # kronolojik: sözlük sırası yönetilen kuru sona atıyordu
    kisa = [_donem_etiketi(a, d[a]) for a in adlar]
    # yönetilen kur dönemi üst panelde de gölgeli: alt paneldeki satırla aynı haftalar
    yon = next((a for a in adlar if a.startswith("yönetilen kur")), None)
    if yon:
        fig.add_vrect(x0=d[yon]["ilk"], x1=d[yon]["son"], fillcolor="rgba(138,138,138,0.13)", line_width=0,
                      layer="below", row=1, col=1)
        fig.add_annotation(x=d[yon]["ilk"], y=1, yref="y domain", xanchor="left", yanchor="top", showarrow=False,
                           text="yönetilen kur", font=dict(size=11, color=GRI), row=1, col=1)
    for ad, renk in (("kur", MAVI), ("rezerv", CLARET), ("faiz", TURUNCU)):
        pay = [d[a]["pay"][ad] * 100 for a in adlar]
        fig.add_trace(go.Bar(y=kisa, x=pay, orientation="h", marker_color=renk, showlegend=False, marker_line_width=0,
                             text=[yuzde(v, 0) for v in pay], textposition="inside", textangle=0,
                             insidetextanchor="middle", textfont=dict(color="white", size=11),
                             customdata=[d[a]["n_hafta"] for a in adlar],
                             hovertemplate="%{y}: " + ad + " payı %%{x:.1f} (%{customdata} hafta)<extra></extra>"),
                      2, 1)
    fig.update_layout(uniformtext=dict(minsize=9, mode="hide"))
    # eksen paylardan: kovaryans payı eksi çıkabilir, bugün hepsi artı (en küçüğü kur, son dönem)
    alt = min(0.0, min(sum(min(0.0, d[a]["pay"][k]) for k in ("kur", "rezerv", "faiz")) for a in adlar) * 100)
    ust = max(100.0, max(sum(max(0.0, d[a]["pay"][k]) for k in ("kur", "rezerv", "faiz")) for a in adlar) * 100)
    fig.update_xaxes(range=[alt - 2, ust + 2], title_text="endeks varyansındaki pay (%)", zeroline=False, row=2, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)
    _paneller_sola(fig)
    gecis = re.search(r"\d{2}\.\d{2}\.\d{4}", p["kur_cuma_notu"])
    gecis_metni = (f"{gecis.group(0)}'ten İstanbul 18:00, öncesinde Londra gece yarısı barı; perşembe" if gecis
                   else "İstanbul 18:00")
    # Başlık ortak sarma kuralıyla (sekil_ortak.baslik_koy); çizim alanı eskisiyle aynı (860 − 222 = 638).
    baslik = baslik_koy(fig, f"Şekil 16 — {ay(d[adlar[-1]]['ilk'])}–{ay(d[adlar[-1]]['son'])} döneminde kur "
                        "baskısı kura değil, rezerve ve faize yazılıyor", [
        f"Haftalık ölçüm {tarih(p['ilk'])}–{tarih(p['son'])}, {p['n']} hafta · üst panel ay içi toplam, "
        f"{ay(s['tarih'][0])}–{ay(s['tarih'][-1])}",
        f"kur: USD/TRY log değişimi, Yahoo Finance ({gecis_metni})",
        "rezerv: TCMB swap hariç net rezervin değişimi / önceki hafta brüt rezerv, işareti çevrili (artı: kayıp)",
        "faiz: TCMB ağırlıklı ortalama fonlama maliyetinin değişimi (puan) · her bileşen kendi σ'sına bölünür"])
    _yaz(fig, "16_kur_baskisi.html", yukseklik(baslik, 638))
