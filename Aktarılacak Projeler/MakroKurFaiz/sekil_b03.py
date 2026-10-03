#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 3 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

import math

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz, baslik_koy, yukseklik)

AYLAR = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
SAYI_YER = {0: "hiçbirinde", 1: "birinde", 2: "ikisinde", 3: "üçünde", 4: "dördünde"}
SAYI = {0: "hiçbir", 1: "bir", 2: "iki", 3: "üç", 4: "dört"}
DONEM_RENK = (MAVI, CLARET, TURUNCU, YESIL)


def _ay_adi(aa: str) -> str:
    y, a = aa[:7].split("-")
    return f"{AYLAR[int(a) - 1]} {y}"


def _sola(fig, basliklar) -> None:
    """Alt grafik başlıkları sola, dar ekrana sığacak boyda."""
    for a in fig.layout.annotations:
        if a.yanchor == "bottom" and a.yref == "paper" and a.text in basliklar:
            a.update(x=0, xanchor="left", font=dict(size=12.5))


def _konum(x: float, alt: float, ust: float) -> str:
    return "altında" if x < alt else ("üstünde" if x > ust else "içinde")


def s03_taylor_bandi(o: dict) -> None:
    b = o["b03"]
    s = b["sekil_03"]
    par = b["p3a"]["parametreler"]
    son = b["p3a"]["son_ay"]
    t = s["tarih"]
    basliklar = ("Taylor bandı, AOFM ve politika faizi (%)", "Çıktı açığı: iki HP sürümü (puan)")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.72, 0.28], vertical_spacing=0.08,
                        subplot_titles=basliklar)

    def bant(alt, ust, renk, dolgu, ad):
        i0 = next(i for i, v in enumerate(s[alt]) if v is not None)
        x = t[i0:]
        fig.add_trace(go.Scatter(x=x, y=s[alt][i0:], mode="lines", line=dict(color=renk, width=0.7),
                                 showlegend=False, legendgroup=ad,
                                 hovertemplate="%{x|%m.%Y}: alt %%{y:.1f}<extra>" + ad + "</extra>"), 1, 1)
        fig.add_trace(go.Scatter(x=x, y=s[ust][i0:], mode="lines", line=dict(color=renk, width=0.7), fill="tonexty",
                                 fillcolor=dolgu, name=ad, legendgroup=ad,
                                 hovertemplate="%{x|%m.%Y}: üst %%{y:.1f}<extra>" + ad + "</extra>"), 1, 1)
        return x[0]

    bant("bant_gercek_alt", "bant_gercek_ust", CLARET, "rgba(140,47,57,0.20)", "Taylor bandı: gerçekleşen enflasyonla")
    pka_i = next(i for i, v in enumerate(s["bant_pka_alt"]) if v is not None)
    pka_ilk = bant("bant_pka_alt", "bant_pka_ust", MAVI, "rgba(47,93,140,0.22)",
                   f"Taylor bandı: PKA 12 ay beklentisiyle ({ay(s['tarih'][pka_i] + '-01')}'ten)")
    fig.add_trace(go.Scatter(x=t, y=s["aofm"], mode="lines", name="AOFM (aylık ortalama)",
                             line=dict(color=MUREKKEP, width=2),
                             hovertemplate="%{x|%m.%Y}: %%{y:.2f}<extra>AOFM</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=s["politika"], mode="lines", name="politika faizi, ay sonu (06.2018 öncesi etkin değil)",
                             line=dict(color=TURUNCU, width=1.4, shape="hv"),
                             hovertemplate="%{x|%m.%Y}: %%{y:.2f}<extra>politika faizi</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=t, y=s["acik_tam"], mode="lines", name="çıktı açığı: tam örneklem HP",
                             line=dict(color=YESIL, width=1.6),
                             hovertemplate="%{x|%m.%Y}: %{y:.2f} puan<extra>tam örneklem</extra>"), 2, 1)
    fig.add_trace(go.Scatter(x=t, y=s["acik_gercek_zamanli"], mode="lines", name="çıktı açığı: gerçek zamanlı HP",
                             line=dict(color=YESIL, width=1.4, dash="dot"),
                             hovertemplate="%{x|%m.%Y}: %{y:.2f} puan<extra>gerçek zamanlı</extra>"), 2, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.7), row=2, col=1)
    # dönem gölgeleri (izlerden sonra; katman altta) ve adları
    def _ay_sonu(z: str) -> str:
        """Aylık dönem ayın sonuna kadar sürer: gölge ertesi ayın başında biter."""
        y_, m_ = int(z[:4]), int(z[5:7])
        return f"{y_ + m_ // 12}-{m_ % 12 + 1:02d}-01"

    gol = (None, "rgba(138,138,138,0.12)", "rgba(138,138,138,0.24)", "rgba(138,138,138,0.12)")
    kisa = ("2013–2020", "2021", "yönetilen kur", "07.2023 sonrası")
    # adlar bantların üstündeki şeritte, üç sıra: dar ekranda (390 px) son üç dönem birkaç
    # piksellik genişliğe sığar ve tek sırada üst üste biniyordu; sonuncusu sağa yaslanır
    sira = (0.97, 0.97, 0.91, 0.85)
    for i, ((a, z, _), g, ad, yy) in enumerate(zip(s["donemler"], gol, kisa, sira)):
        if g:
            fig.add_vrect(x0=a + "-01", x1=_ay_sonu(z), fillcolor=g, line_width=0, layer="below", row="all", col=1)
        son_donem = i == len(s["donemler"]) - 1
        fig.add_annotation(x=_ay_sonu(z) if son_donem else a + "-01", y=yy, xref="x", yref="y domain", text=ad,
                           showarrow=False, xanchor="right" if son_donem else "left", xshift=-2 if son_donem else 2,
                           font=dict(size=10.5, color="#555"))
    # x aralığı veriden: ad etiketleri eksen aralığını kendiliğinden genişletiyordu (390 px'te 2029'a)
    fig.update_xaxes(range=[t[0] + "-01", _ay_sonu(t[-1])], row="all", col=1)
    tepe = max(v for v in s["bant_gercek_ust"] if v is not None)
    # bantların tepesi eksenin ~%78'inde kalır: üstteki şerit dönem adlarına ayrılır
    fig.update_yaxes(range=[0, math.ceil(tepe / 0.78 / 10) * 10], title_text="%", row=1, col=1)
    fig.update_yaxes(title_text="puan", row=2, col=1)
    _sola(fig, basliklar)
    ayad = _ay_adi(son["ay"])
    k_g = _konum(son["aofm_ay_ort_yuzde"], son["bant_gercek_alt_yuzde"], son["bant_gercek_ust_yuzde"])
    k_p = _konum(son["aofm_ay_ort_yuzde"], son["bant_pka_alt_yuzde"], son["bant_pka_ust_yuzde"])
    r = ", ".join(yuzde(x, 0) for x in par["r_yildiz_yuzde"])
    # başlık + alt başlık en çok 7 satır (ev stilinin üst boşluğu ancak bu kadarını taşır; ölçüldü)
    fig.update_layout(legend=dict(y=-0.1))
    # Başlık ortak sarma kuralıyla (sekil_ortak.baslik_koy); çizim alanı eskisiyle aynı (860 − 274 = 586).
    baslik = baslik_koy(fig, f"Şekil 03 — {ayad}'da AOFM, gerçekleşen enflasyonla kurulan bandın {k_g}, "
                        f"beklentiyle kurulan bandın {k_p}", [
        f"Aylık, {ay(t[0] + '-01')}–{ay(t[-1] + '-01')} · TÜİK TÜFE ve reel GSYH, TCMB AOFM ve Piyasa "
        "Katılımcıları Anketi (PKA), politika faizi ay sonu (09.2018 öncesi BIS)",
        f"kural = r* + π + {vir(par['katsayi_pi'], 1)}(π − {vir(par['pi_hedef_yuzde'], 0)}) + "
        f"{vir(par['katsayi_acik'], 1)}·açık, hedef {yuzde(par['pi_hedef_yuzde'], 0)}",
        f"her bant: iki açık sürümü × üç r* ({r}), en düşük ile en yüksek bileşim arası"])
    _yaz(fig, "03_taylor_bandi.html", yukseklik(baslik, 586))


def s04_faiz_farki_eurusd(o: dict) -> None:
    b = o["b03"]
    s = b["sekil_04"]
    d = b["p3c"]["donemler"]
    t, f, e = s["tarih"], s["fark_puan"], s["eurusd"]
    basliklar = ("ABD 2 yıllık − Almanya 2 yıllık getiri (puan)",
                 "EUR/USD (artış: euro değer kazanır, dolar zayıflar)",
                 "Haftalık değişimler ve dönem regresyonu")
    fig = make_subplots(rows=3, cols=1, row_heights=[0.29, 0.29, 0.42], vertical_spacing=0.085,
                        subplot_titles=basliklar)
    donem = list(d.values())
    sinir = [x[0] for x in s["donemler"]] + ["9999"]
    for j, (dd, renk) in enumerate(zip(donem, DONEM_RENK)):
        a, z = sinir[j], sinir[j + 1]
        idx = [i for i, x in enumerate(t) if a <= x < z]
        cizgi = ([idx[0] - 1] if idx[0] > 0 else []) + idx          # dönemler arası çizgi kesilmesin
        reg = dd["degisim"]
        ad = (f"{dd['ad'].split(' (')[0]} · eğim {vir(reg['egim'], 2)} (t {vir(reg['t'], 1)})"
              f" · seviye korelasyonu {vir(dd['seviye_korelasyon'], 2) if dd['seviye_korelasyon'] < 0 else '+' + vir(dd['seviye_korelasyon'], 2)}")
        fig.add_trace(go.Scatter(x=[t[i] for i in cizgi], y=[f[i] for i in cizgi], mode="lines", name=ad,
                                 legendgroup=str(j), line=dict(color=renk, width=1.4),
                                 hovertemplate="%{x|%d.%m.%Y}: %{y:.2f} puan<extra></extra>"), 1, 1)
        fig.add_trace(go.Scatter(x=[t[i] for i in cizgi], y=[e[i] for i in cizgi], mode="lines", showlegend=False,
                                 legendgroup=str(j), line=dict(color=renk, width=1.4),
                                 hovertemplate="%{x|%d.%m.%Y}: %{y:.4f}<extra></extra>"), 2, 1)
        # haftalık değişim: fark (bp) ve EUR/USD log değişimi (%); ilk hafta bir önceki dönemin son haftasına göre
        dx = [(f[i] - f[i - 1]) * 100 for i in idx if i > 0]
        dy = [math.log(e[i] / e[i - 1]) * 100 for i in idx if i > 0]
        ipucu = [f"{tarih(t[i])} · fark {vir(a_, 0)} bp · EUR/USD {yuzde(b_, 2, arti=True)}"
                 for i, a_, b_ in zip([i for i in idx if i > 0], dx, dy)]
        fig.add_trace(go.Scatter(x=dx, y=dy, mode="markers", showlegend=False, legendgroup=str(j),
                                 marker=dict(color=renk, size=4, opacity=0.35, line_width=0), customdata=ipucu,
                                 hovertemplate="%{customdata}<extra></extra>"), 3, 1)
        x0, x1 = min(dx), max(dx)
        fig.add_trace(go.Scatter(x=[x0, x1], y=[reg["sabit"] + reg["egim"] * x0 / 10, reg["sabit"] + reg["egim"] * x1 / 10],
                                 mode="lines", showlegend=False, legendgroup=str(j), line=dict(color=renk, width=2.6),
                                 hoverinfo="skip"), 3, 1)
    fig.add_hline(y=0, line=dict(color=MUREKKEP, width=0.7), row=1, col=1)
    fig.add_hline(y=0, line=dict(color="#bdbdbd", width=0.7), row=3, col=1)
    fig.add_vline(x=0, line=dict(color="#bdbdbd", width=0.7), row=3, col=1)
    fig.update_xaxes(matches="x", showticklabels=False, row=1, col=1)
    fig.update_xaxes(matches="x", row=2, col=1)
    fig.update_xaxes(title_text="fark değişimi, bp (artış: ABD lehine)", zeroline=False, row=3, col=1)
    fig.update_yaxes(title_text="puan", row=1, col=1)
    fig.update_yaxes(title_text="EUR/USD", tickformat=".1f", row=2, col=1)
    fig.update_yaxes(title_text="EUR/USD değişimi, % (log)<br>eksi: dolar değer kazanır", row=3, col=1)
    _sola(fig, basliklar)
    eksi = sum(1 for v in donem if v["degisim"]["egim"] < 0 and v["degisim"]["t"] < -2)
    ters = sum(1 for v in donem if v["seviye_korelasyon"] > 0)
    # başlık + alt başlık en çok 7 satır (ev stilinin üst boşluğu ancak bu kadarını taşır; ölçüldü)
    seviye = (f"seviyede {SAYI[ters]} dönemde işaret tersine döner" if ters
              else "seviyede de işaret beklenen yönde")
    fig.update_layout(legend=dict(y=-0.07), title=dict(text=(
        f"Şekil 04 — ABD lehine açılan 2 yıllık fark, {SAYI[len(donem)]}<br>dönemin {SAYI_YER[eksi]} "
        f"doların güçlendiği haftaya<br>düşer; {seviye}"
        f"<br><sub>Haftalık, {tarih(t[0])}–{tarih(t[-1])} · ABD Hazinesi ve Bundesbank 2 yıllık<br>"
        "par getirileri · EUR/USD CNBC, New York 17:00 · eğim (örneklem içi):<br>"
        "10 bp fark değişimi başına EUR/USD % değişimi, Newey–West t · seviye<br>"
        "korelasyonu birim kök yüzünden sahte olabilir</sub>")))
    _yaz(fig, "04_faiz_farki_eurusd.html", 900)
