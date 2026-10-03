#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 10 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz, baslik_koy, yukseklik)

DONEM_GOLGE = "rgba(138,138,138,0.16)"


def _panel_basliklari(fig, n: int, boyut: float = 12.5) -> None:
    """Panel başlıkları sola yaslı ve gövde boyunda: dar ekranda ortalı büyük başlık taşar."""
    for a in list(fig.layout.annotations)[:n]:
        a.update(x=0, xanchor="left", font=dict(size=boyut, color=MUREKKEP))


def s17_emtia_paralari(o: dict) -> None:
    b = o["b10"]
    s = b["sekil_17"]
    p = b["p10a"]
    pet = p["petrol_2014_2016"]
    t = s["tarih"]
    cad_k, nok_k = p["cad_enerji"]["kayan_36ay"], p["nok_enerji"]["kayan_36ay"]
    # Başlık ölçümden kurulur. Birinci yarı tam örneklem korelasyonunun yalnız İŞARETİNİ söyler
    # ("izler" demez: ay sonu hizasında korelasyonlar orta düzeyde); ikinci yarı iki enerji
    # parasının son eksi dizisi aynı uzunluktaysa onu, ayrışırsa iki son değeri söyler.
    kor_tam = [p[c]["kor_ay_sonu"] for c in ("aud_metal", "cad_enerji", "nok_enerji")]
    bas = ("Emtia paraları emtiayla aynı yönde, bağ oynak" if all(k > 0 for k in kor_tam)
           else "Emtia paralarının emtiayla bağı tam örneklemde bile tek yönlü değil")
    if cad_k["son_eksi_dizi_ay"] and cad_k["son_eksi_dizi_ay"] == nok_k["son_eksi_dizi_ay"]:
        bulgu = f"CAD ve NOK'ta enerjiyle 36 aylık korelasyon {cad_k['son_eksi_dizi_ay']} aydır eksi"
    else:
        bulgu = f"enerjiyle 36 aylık korelasyon CAD'de {vir(cad_k['son'], 2)}, NOK'ta {vir(nok_k['son'], 2)}"
    # Son değerin işareti ay ortalaması hizasında da aynıysa alt başlık bunu söyler (sağlamlık).
    hiza_ayni = all((k["son"] < 0) == (k["ay_ortalamasi_son"] < 0) for k in (cad_k, nok_k))
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, row_heights=[0.36, 0.36, 0.28], vertical_spacing=0.07,
        subplot_titles=("AUD'nin dolara karşı değeri ve metal fiyatı",
                        "CAD ve NOK'un dolara karşı değeri ve enerji fiyatı",
                        "36 aylık kayan korelasyon (çizginin rengi: para)"))
    _panel_basliklari(fig, 3)
    hv = "%{x|%m.%Y}: %{y:.1f}<extra>"
    fig.add_trace(go.Scatter(x=t, y=s["aud_deger_2000_100"], mode="lines", legendgroup="aud",
                             name="AUD (artış: AUD değer kazanır)",
                             line=dict(color=MAVI, width=2.2), hovertemplate=hv + "AUD</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=s["metal_2000_100"], mode="lines", name="metal fiyat endeksi",
                             line=dict(color=YESIL, width=1.5), hovertemplate=hv + "metal</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=s["cad_deger_2000_100"], mode="lines", legendgroup="cad",
                             name="CAD (artış: CAD değer kazanır)",
                             line=dict(color=CLARET, width=2.2), hovertemplate=hv + "CAD</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=t, y=s["nok_deger_2000_100"], mode="lines", legendgroup="nok",
                             name="NOK (artış: NOK değer kazanır)",
                             line=dict(color=TURUNCU, width=2.2), hovertemplate=hv + "NOK</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=t, y=s["enerji_2000_100"], mode="lines", name="enerji fiyat endeksi",
                             line=dict(color=GRI, width=1.5), hovertemplate=hv + "enerji</extra>"), 2, 1)
    for anahtar, grup, renk, ad in (("kor36_aud_metal", "aud", MAVI, "AUD–metal"),
                                    ("kor36_cad_enerji", "cad", CLARET, "CAD–enerji"),
                                    ("kor36_nok_enerji", "nok", TURUNCU, "NOK–enerji")):
        fig.add_trace(go.Scatter(x=t, y=s[anahtar], mode="lines", legendgroup=grup, showlegend=False, name=ad,
                                 line=dict(color=renk, width=1.8),
                                 hovertemplate="%{x|%m.%Y}: %{y:.2f}<extra>" + ad + "</extra>"), 3, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=1), row=3, col=1)
    tv = [60, 80, 100, 150, 200, 300, 400]
    for r in (1, 2):
        fig.update_yaxes(type="log", tickvals=tv, ticktext=[str(v) for v in tv],
                         title_text="2000 = 100 (log ölçek)", row=r, col=1)
    fig.update_yaxes(range=[-0.6, 1.0], dtick=0.25, title_text="korelasyon", row=3, col=1)
    for r in (1, 2, 3):
        fig.add_vrect(x0=pet["ilk"], x1=pet["son"], fillcolor=DONEM_GOLGE, line_width=0, layer="below", row=r, col=1)
    fig.add_annotation(x=pet["son"], y=0.03, xref="x", yref="y domain",
                       text=f"{pet['ilk'][:4]}–{pet['son'][2:4]} petrol düşüşü", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=11, color=GRI))
    # İlk korelasyon, değişimler serinin ikinci ayından başladığı için i0 aylık değişimle kurulur:
    # pencerenin asgari gözlemi ölçümün kendisinden okunur, elle yazılmaz.
    i0 = next(i for i, v in enumerate(s["kor36_cad_enerji"]) if v is not None)
    kor_ilk, asgari = t[i0], i0
    hiza = (" · son değerin işareti emtianın ay ortalamasıyla eşlenen kurda da aynı" if hiza_ayni else "")
    # Başlık ortak sarma kuralıyla (sekil_ortak.baslik_koy); çizim alanı eskisiyle aynı (900 − 222 = 678).
    baslik = baslik_koy(fig, f"Şekil 17 — {bas}: {bulgu}", [
        f"Aylık, {ay(s['ilk'])}–{ay(s['son'])} · kur ay sonu (AUD, CAD New York 17:00; NOK ECB referans "
        "kurlarından euro çaprazı)",
        "emtia: Dünya Bankası Pink Sheet metal ve enerji endeksi, ay ortalaması (nominal dolar)",
        "seviye: 2000'in log ortalaması = 100 · korelasyon: aylık log değişimlerden, 36 aylık pencere",
        f"ilk değer {ay(kor_ilk)} (pencerede en az {asgari} ay){hiza}"])
    _yaz(fig, "17_emtia_paralari.html", yukseklik(baslik, 678))
