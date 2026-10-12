#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — analiz figürleri.

Bu bir HAT DEĞİL, tek bir analizin çizim katmanı. Analiz yayımlandığı günün
metnidir (karar 08.09.2026); figürler de o günün ölçümünü dondurur ve
`site/public/analiz/<slug>/` altına yazılır — hat figürleri gibi tazelenmez,
sayfa damgası basmaz, her figür kendi tarih aralığını kendi alt başlığında taşır.

GİRDİ TEK YERDEN: `veri/olcum.json` (`olcum.py` üretir). Figür ile metin iki
ayrı hesaptan beslenseydi bir gün sessizce ayrışırdı.

Biçim: ondalık virgül, binlik nokta, eksi U+2212 (`separators`; üzerine gelme
kutusu metni sözleşmeyle önceden yazılır — plotly'nin şablonu ASCII tire basar).
Plotly başlığı sarmaz, taşırır — başlık bloğu `sekil_ortak.baslik_koy` ile
telefonun gömme çerçevesine (353 piksel) göre sarılır. Çift y eksenli grafik
yok: iki ölçek iki alt panele bölünür. Renk: dört kategorik slot (bordo, mavi,
kehribar, yeşil) sabit sırayla; bağlam serileri gri.

Fonksiyon adı = yazıdaki şekil numarası = dosya adının öneki = figürün içindeki
"Şekil NN" başlığı (dogrula.py bunları sorar).

  python3 sekil.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
sys.dont_write_bytecode = True

import sekil_ortak as so  # noqa: E402
from sekil_ortak import go, make_subplots, vir, yuzde, tarih  # noqa: E402

O = json.loads(so.OLCUM.read_text(encoding="utf-8"))
SEKILLER = ["01_iki_brent", "02_egri", "03_dagilim", "04_pencereler", "05_egimler", "06_tcmb",
            "07_yabanci", "08_tufe", "09_otv", "10_cari", "11_tarih"]
CLARET, MAVI, KEHRIBAR, YESIL, GRI, MUREKKEP = so.CLARET, so.MAVI, so.TURUNCU, so.YESIL, so.GRI, so.MUREKKEP
ACIK = "#d8d4cc"
PENCERE_AD = ["Mart", "Mayıs", "Temmuz", "Eylül"]
PENCERE_RENK = [CLARET, MAVI, KEHRIBAR, YESIL]
PENCERE_SEMBOL = ["circle", "square", "diamond", "triangle-up"]


def bp(x: float, b: int = 0, arti: bool = True) -> str:
    return f"{vir(x, b) if (x <= 0 or not arti) else '+' + vir(x, b)} bp"


def isaretli(x: float, b: int = 1) -> str:
    return ("+" if x > 0 else "") + vir(x, b)


def _bitir(fig, ad: str, bas: str, alt: list[str], cizim: int) -> None:
    baslik = so.baslik_koy(fig, bas, alt)
    so._yaz(fig, ad, so.yukseklik(baslik, cizim), ust=so.ust_pay(baslik))


# ─────────────────────────────────────────────────────────────────────── 01
def sekil_01():
    s = O["sekil"]["iki_brent"]
    ib = O["iki_brent"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.66, 0.34],
                        subplot_titles=("USD/varil", "Fark: fiziki − vadeli, USD/varil"))
    fig.add_hrect(y0=125, y1=150, fillcolor="rgba(140,47,57,0.10)", line_width=0, row=1, col=1)
    for h in (125, 150):
        fig.add_hline(y=h, line=dict(color=CLARET, width=0.8, dash="dot"), row=1, col=1)
    fig.add_annotation(x=s["vadeli"]["t"][8], y=148, text="senaryo bandı 125–150", showarrow=False,
                       xanchor="left", yanchor="top", font=dict(size=11, color=CLARET), row=1, col=1)
    for ad, k, renk, gen in (("Fiziki Brent (EIA spot)", "fiziki", CLARET, 2.2),
                             ("Vadeli Brent (ön vade)", "vadeli", MAVI, 2.0)):
        fig.add_trace(go.Scatter(x=s[k]["t"], y=s[k]["v"], name=ad, mode="lines", line=dict(color=renk, width=gen),
                                 customdata=[f"{tarih(t)} · {vir(v, 2)}" for t, v in zip(s[k]["t"], s[k]["v"])],
                                 hovertemplate="%{customdata}<extra>" + ad + "</extra>"), row=1, col=1)
    ortak = sorted(set(s["fiziki"]["t"]) & set(s["vadeli"]["t"]))
    fz, vd = dict(zip(s["fiziki"]["t"], s["fiziki"]["v"])), dict(zip(s["vadeli"]["t"], s["vadeli"]["v"]))
    fark = [fz[t] - vd[t] for t in ortak]
    fig.add_trace(go.Scatter(x=ortak, y=fark, name="fark", mode="lines", line=dict(color=MUREKKEP, width=1.6),
                             fill="tozeroy", fillcolor="rgba(26,26,26,0.08)", showlegend=False,
                             customdata=[f"{tarih(t)} · {isaretli(v, 2)}" for t, v in zip(ortak, fark)],
                             hovertemplate="%{customdata}<extra>fark</extra>"), row=2, col=1)
    az = ib["tarihce_2000_2025"]
    fig.add_hline(y=az["azami"], line=dict(color=GRI, width=1, dash="dash"), row=2, col=1)
    fig.add_annotation(x=ortak[2], y=az["azami"], text=f"2000–2025'in en büyüğü {vir(az['azami'], 2)}",
                       showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11, color=GRI), row=2, col=1)
    fig.update_yaxes(row=1, col=1, range=[55, 152])
    _bitir(fig, "01_iki_brent.html",
           f"Şekil 01 — Fiziki Brent zaten {vir(ib['fiziki_son'], 2)} dolarda, vadeli {vir(ib['vadeli_ayni_gun'], 2)}",
           [f"EIA Europe Brent Spot Price FOB ve NYMEX Brent (BZ) ön vade kapanışı · {tarih(s['vadeli']['t'][0])}–{tarih(s['vadeli']['t'][-1])} "
            f"(fiziki serinin son günü {tarih(ib['son_gun'])})",
            "Alt panel: iki fiyatın farkı; kesikli çizgi 2000–2025 arasının en büyük farkı"], 560)


# ─────────────────────────────────────────────────────────────────────── 02
def sekil_02():
    E = O["sekil"]["egri"]
    on = O["sekil"]["egri_on_vade"]
    y = O["senaryo_yeri"]
    fig = go.Figure()
    def ay(t: str) -> str:
        return f"{t[5:]}.{t[:4]}"
    sira = sorted({t for e in E.values() for t in e["teslim"]})
    for (gun, e), renk, cizgi in zip(E.items(), (GRI, MAVI, CLARET), ("dot", "dash", "solid")):
        ad = f"{tarih(gun)} (ön vade {vir(on[gun], 2)})"
        fig.add_trace(go.Scatter(x=[ay(t) for t in e["teslim"]], y=e["fiyat"], name=ad, mode="lines+markers",
                                 line=dict(color=renk, width=2 if cizgi == "solid" else 1.6, dash=cizgi),
                                 marker=dict(size=5, color=renk),
                                 customdata=[f"{tarih(gun)} · teslim {ay(t)}: {vir(v, 2)}" for t, v in zip(e["teslim"], e["fiyat"])],
                                 hovertemplate="%{customdata}<extra></extra>"))
    for h in (125, 150):
        fig.add_hline(y=h, line=dict(color=CLARET, width=0.8, dash="dot"))
    fig.add_annotation(x=ay(E[y["baz_gun"]]["teslim"][1]), y=125, text=f" Ocak 2027: {vir(y['ikinci_vade_bugun'], 2)} → 125 için +%{vir(y['senaryo']['125']['yuzde_devirsiz'], 1)}",
                       showarrow=False, xanchor="left", yanchor="bottom", font=dict(size=11, color=CLARET))
    fig.update_yaxes(title="USD/varil", range=[60, 155])
    fig.update_xaxes(type="category", categoryorder="array", categoryarray=[ay(t) for t in sira])
    son = E[y["baz_gun"]]
    aralik27 = son["fiyat"][son["teslim"].index("2027-12")]
    _bitir(fig, "02_egri.html",
           f"Şekil 02 — Vade eğrisi 125'i değil normalleşmeyi fiyatlıyor: Aralık 2027 vadesi {vir(aralik27, 2)}",
           ["NYMEX Brent (BZ) kontratlarının kapanışı, yatay eksen teslim ayı · yalnız arşiv günü listeli kontratlar (Aralık 2026 ve sonrası)",
            f"Bir ay sonra (hedef gün {tarih(y['hedef_gun'])}) ön vade bugünün Ocak 2027 kontratıdır · kaynak: Yahoo Finance"], 430)


# ─────────────────────────────────────────────────────────────────────── 03
def sekil_03():
    d = O["sekil"]["dagilim"]
    y = O["senaryo_yeri"]
    n = d["n"]
    x = [k + 1.25 for k in d["kova_alt"]]
    pay = [g / n * 100 for g in d["gun"]]
    renk = [CLARET if k + 2.5 > y["senaryo"]["125"]["log"] else GRI for k in d["kova_alt"]]
    fig = go.Figure(go.Bar(x=x, y=pay, marker_color=renk, marker_line_width=0, width=2.2, showlegend=False,
                           customdata=[f"{vir(k, 1)} ile {vir(k + 2.5, 1)} arası · günlerin payı %{vir(p, 2)}"
                                       for k, p in zip(d["kova_alt"], pay)],
                           hovertemplate="%{customdata}<extra></extra>"))
    for ad, renk_ in (("125", CLARET), ("150", MUREKKEP)):
        v = y["senaryo"][ad]
        fig.add_vline(x=v["log"], line=dict(color=renk_, width=1.4, dash="dash"))
        fig.add_annotation(x=v["log"], y=max(pay) * (0.62 if ad == "125" else 0.40), xanchor="left",
                           text=f" {ad} dolar<br> +%{vir(v['yuzde'], 1)}", showarrow=False, font=dict(size=11, color=renk_))
    sik = y["siklik"]["vadeli_1988"]
    fig.update_xaxes(title="21 iş günlük log değişim, ×100", range=[-62, 66])
    fig.update_yaxes(title="günlerin yüzdesi", ticksuffix="")
    _bitir(fig, "03_dagilim.html",
           f"Şekil 03 — Bir ayda +%{vir(y['senaryo']['125']['yuzde'], 1)}: görülme oranı %{vir(sik['125']['pay'], 1)}; "
           f"+%{vir(y['senaryo']['150']['yuzde'], 1)} yalnız {sik['150']['epizot']} kez",
           [f"Vadeli Brent ön vade kapanışı, 21 iş günlük değişim · {tarih(d['ilk'])}–{tarih(d['son'])}, {d['n']:,} gün".replace(",", "."),
            f"Bordo: 125 senaryosunun eşiğini aşan kovalar · bugün {isaretli(d['son_deger'], 1)}"], 420)


# ─────────────────────────────────────────────────────────────────────── 04
P04_YUZDE = [("^GSPC", "S&P 500"), ("^STOXX", "STOXX Europe 600"), ("^N225", "Nikkei 225"), ("EEM", "Gelişen piyasa hisseleri"),
             ("JETS", "ABD havayolları"), ("XOP", "ABD petrol üreticileri"), ("GC=F", "Altın"), ("DX-Y.NYB", "Dolar endeksi"),
             ("HYG", "ABD yüksek getirili kredi"), ("XU100.IS", "BIST 100"), ("XBANK.IS", "BIST Bankacılık"),
             ("TUPRS_IS", "Tüpraş"), ("USDTRY=X", "USD/TRY")]
P04_BP = [("us2y", "ABD 2 yıllık"), ("us10y", "ABD 10 yıllık"), ("n2y", "DİBS 2 yıllık"), ("tlref", "TLREF")]


def sekil_04():
    r = O["rejim_2026"]
    pen = r["pencereler"]
    V = r["varlik"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10, row_heights=[0.74, 0.26],
                        subplot_titles=("Fiyat değişimi, %", "Faiz değişimi, baz puan"))
    for j, p in enumerate(pen):
        ad = f"{PENCERE_AD[j]} (Brent +%{vir(p['brent_yuzde'], 1)})"
        for satir, kume, birim in ((1, P04_YUZDE, "%"), (2, P04_BP, "bp")):
            ys = [a for k, a in kume if k in V]
            xs = [V[k]["pencere_yuzde"][j] for k, _ in kume if k in V]
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=ad, legendgroup=ad, showlegend=(satir == 1),
                                     marker=dict(color=PENCERE_RENK[j], symbol=PENCERE_SEMBOL[j], size=10,
                                                 line=dict(color="white", width=1)),
                                     customdata=[f"{a} · {PENCERE_AD[j]}: " + (yuzde(x, 1, True) if birim == "%" else f"{isaretli(x, 0)} bp")
                                                 for a, x in zip(ys, xs)],
                                     hovertemplate="%{customdata}<extra></extra>"), row=satir, col=1)
    for satir in (1, 2):
        fig.add_vline(x=0, line=dict(color=GRI, width=1), row=satir, col=1)
    fig.update_yaxes(autorange="reversed", row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)
    fig.update_layout(legend=dict(y=-0.08))
    _bitir(fig, "04_pencereler.html",
           "Şekil 04 — 2026'nın dört petrol yükselişinde öbür piyasalar ne yaptı",
           [f"Her pencere Brent'in 21 iş günlük yükselişinin tepe yaptığı gün biter: "
            + ", ".join(f"{PENCERE_AD[j]} {tarih(p['bas'])}–{tarih(p['son'])}" for j, p in enumerate(pen)),
            "Kaynak: bülten piyasa fotoğrafı, ABD Hazinesi, TCMB, Borsa İstanbul"], 820)


# ─────────────────────────────────────────────────────────────────────── 05
P05_YUZDE = [("CL=F", "WTI"), ("HO=F", "Motorin vadelisi (ULSD)"), ("GC=F", "Altın"), ("^GSPC", "S&P 500"),
             ("^STOXX", "STOXX Europe 600"), ("^N225", "Nikkei 225"), ("EEM", "Gelişen piyasa hisseleri"),
             ("JETS", "ABD havayolları"), ("XOP", "ABD petrol üreticileri"), ("^VIX", "VIX"), ("^MOVE", "MOVE"),
             ("DX-Y.NYB", "Dolar endeksi"), ("EURUSD=X", "EUR/USD"), ("USDJPY=X", "USD/JPY"), ("inr", "USD/INR"),
             ("HYG", "ABD yüksek getirili kredi"), ("EMB", "Gelişen ülke dolar tahvili"),
             ("USDTRY=X", "USD/TRY"), ("XU100.IS", "BIST 100"), ("bist_usd", "BIST 100 (dolar)"),
             ("XBANK.IS", "BIST Bankacılık"), ("TUPRS_IS", "Tüpraş"), ("THYAO_IS", "THY"), ("PGSUS_IS", "Pegasus")]
P05_BP = [("us2y", "ABD 2 yıllık"), ("us10y", "ABD 10 yıllık"), ("be5y", "ABD 5 yıllık başabaş"),
          ("n2y", "DİBS 2 yıllık"), ("n5y", "DİBS 5 yıllık"), ("be_2y", "TL 2 yıllık başabaş"), ("tlref", "TLREF")]
KANIT_RENK = {"guclu": CLARET, "orta": KEHRIBAR, "zayif": GRI}
KANIT_AD = {"guclu": "güçlü", "orta": "orta", "zayif": "zayıf"}


def sekil_05():
    V = O["rejim_2026"]["varlik"]
    T = O["senaryo_tablosu"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.07, row_heights=[0.77, 0.23],
                        subplot_titles=("Tepki, % (log ölçü)", "Tepki, baz puan"))
    gorulen = set()
    for satir, kume, birim in ((1, P05_YUZDE, "%"), (2, P05_BP, "bp")):
        for k, ad in kume:
            if k not in V or k not in T:
                continue
            u = V[k]["yukselis"]
            kn = T[k]["kanit"]
            e, h = u["egim"], 1.645 * u["se"]
            ilk = kn not in gorulen
            gorulen.add(kn)
            fig.add_trace(go.Scatter(x=[e], y=[ad], mode="markers", name=f"kanıt {KANIT_AD[kn]}", legendgroup=kn,
                                     showlegend=ilk, marker=dict(color=KANIT_RENK[kn], size=9,
                                                                 symbol="circle" if kn != "zayif" else "circle-open",
                                                                 line=dict(width=1.6, color=KANIT_RENK[kn])),
                                     error_x=dict(type="data", array=[h], color=KANIT_RENK[kn], thickness=1.4, width=0),
                                     customdata=[f"{ad}: " + (f"{yuzde(e, 2)} (%90 aralık {yuzde(e - h, 2)} – {yuzde(e + h, 2)})" if birim == "%"
                                                              else f"{vir(e, 2)} bp (%90 aralık {vir(e - h, 2)} – {vir(e + h, 2)} bp)")
                                                 + f" · kanıt {KANIT_AD[kn]}"],
                                     hovertemplate="%{customdata}<extra></extra>"), row=satir, col=1)
        fig.add_vline(x=0, line=dict(color=GRI, width=1), row=satir, col=1)
    fig.update_yaxes(autorange="reversed", row=1, col=1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)
    r = O["rejim_2026"]
    _bitir(fig, "05_egimler.html",
           "Şekil 05 — Petrol yükselirken: ABD faizleri, kredi ve havayolları tutarlı; S&P 500 ve altın değil",
           [f"Brent'in %1'lik yükselişine tepki: Brent'in yükseldiği günlerde 21 iş günlük değişimin Brent'in devirsiz "
            f"değişimine eğimi · {tarih(r['ilk'])}–{tarih(r['son'])}",
            "Çizgi: %90 aralık (Newey–West, 20 gecikme) · kanıt: bir-pencere-dışarıda sınama (Yöntem eki)"], 900)


# ─────────────────────────────────────────────────────────────────────── 06
def sekil_06():
    f = O["sekil"]["fonlama"]
    rz = O["sekil"]["rezerv"]
    t = O["tcmb"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.09, row_heights=[0.55, 0.45],
                        subplot_titles=("TL fonlama, %", "TCMB net rezerv, milyar dolar"))
    for ad, k, renk, cizgi, gen in (("Koridor üstü (gecelik borç verme)", "koridor_ust", GRI, "dot", 1.2),
                                    ("Politika faizi", "politika", MUREKKEP, "dash", 1.2),
                                    ("Koridor altı", "koridor_alt", GRI, "dot", 1.2),
                                    ("TLREF", "tlref", CLARET, "solid", 2.0)):
        fig.add_trace(go.Scatter(x=f[k]["t"], y=f[k]["v"], name=ad, mode="lines", line=dict(color=renk, dash=cizgi, width=gen, shape="hv"),
                                 customdata=[f"{tarih(x)} · %{vir(v, 2)}" for x, v in zip(f[k]["t"], f[k]["v"])],
                                 hovertemplate="%{customdata}<extra>" + ad + "</extra>"), row=1, col=1)
    for ad, k, renk in (("Net rezerv", "net_rezerv_usd", MAVI), ("Swap hariç net rezerv", "swap_haric_net_rezerv_usd", KEHRIBAR)):
        fig.add_trace(go.Scatter(x=rz[k]["t"], y=rz[k]["v"], name=ad, mode="lines", line=dict(color=renk, width=2),
                                 customdata=[f"{tarih(x)} · {vir(v, 1)} milyar $" for x, v in zip(rz[k]["t"], rz[k]["v"])],
                                 hovertemplate="%{customdata}<extra>" + ad + "</extra>"), row=2, col=1)
    ub = t["ust_bant_2026"]
    for satir in (1, 2):
        fig.add_vrect(x0=ub["ara"], x1=ub["acilis"], fillcolor="rgba(140,47,57,0.06)", line_width=0, row=satir, col=1)
    fig.add_annotation(x=ub["ara"], y=40.6, text=" repo ihalesi yok", showarrow=False, xanchor="left", yanchor="bottom",
                       font=dict(size=11, color=CLARET), row=1, col=1)
    m = t["2026-03"]
    _bitir(fig, "06_tcmb.html",
           f"Şekil 06 — Mart'ın savunması: fonlama koridorun tavanında, swap hariç net rezerv {vir(m['swap_haric_bas'], 1)} → {vir(m['swap_haric_dip'], 1)} milyar dolar",
           [f"Gölge: bir hafta vadeli repo ihalesine ara verilen dönem, {tarih(ub['ara'])}–{tarih(ub['acilis'])} ({ub['is_gunu']} iş günü)",
            f"Kaynak: TCMB, Borsa İstanbul (TLREF) · son gözlem {tarih(t['rezerv_bugun']['gun'])}"], 600)


# ─────────────────────────────────────────────────────────────────────── 07
def sekil_07():
    s = O["sekil"]["yabanci"]
    y = O["yabanci"]
    fig = go.Figure()
    for ad, k, renk in (("DİBS", "dibs", CLARET), ("Hisse senedi", "hisse", MAVI)):
        fig.add_trace(go.Scatter(x=s[k]["t"], y=s[k]["v"], name=ad, mode="lines", line=dict(color=renk, width=2.2, shape="hv"),
                                 customdata=[f"{tarih(x)} haftası · {isaretli(v, 2)} milyar $" for x, v in zip(s[k]["t"], s[k]["v"])],
                                 hovertemplate="%{customdata}<extra>" + ad + "</extra>"))
    for gun, etiket in (("2025-03-19", "19 Mart 2025"), ("2026-03-02", "2 Mart 2026")):
        fig.add_vline(x=gun, line=dict(color=GRI, width=1, dash="dash"))
        fig.add_annotation(x=gun, y=1, yref="paper", text=f" {etiket}", showarrow=False, xanchor="left", yanchor="top",
                           font=dict(size=11, color=GRI))
    fig.add_hline(y=0, line=dict(color=ACIK, width=1))
    fig.update_yaxes(title="birikimli net alım, milyar dolar")
    m = y["2026-03"]
    g = y["geri_donus_2026"]
    _bitir(fig, "07_yabanci.html",
           f"Şekil 07 — Yabancı Mart'ta DİBS'ten {vir(-m['dibs'] / 1000, 1)} milyar dolar çıktı; geri dönen {vir(g['dibs'] / 1000, 1)} milyar dolar",
           [f"Yurt dışı yerleşiklerin haftalık net alımı, {tarih(s['bas'])} haftasından birikimli · kaynak: TCMB menkul kıymet istatistikleri",
            f"Son hafta {tarih(g['son'])}"], 440)


# ─────────────────────────────────────────────────────────────────────── 08
def sekil_08():
    T = O["tufe_aktarim"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16, row_heights=[0.55, 0.45],
                        subplot_titles=("Kalem fiyatı, iki ayda %", "TÜFE'ye katkı, puan"))
    kalem = [("motorin", "Motorin"), ("benzin", "Benzin"), ("akaryakit", "Akaryakıt"), ("enerji", "Enerji")]
    for j, (sen, renk) in enumerate((("125", MAVI), ("150", CLARET))):
        ys = [T["senaryo"][sen]["kalem"][k] for k, _ in kalem]
        fig.add_trace(go.Bar(x=[a for _, a in kalem], y=ys, name=f"{sen} dolar", marker_color=renk, legendgroup=sen,
                             customdata=[f"{a}: +%{vir(v, 1)} ({sen} dolar)" for (_, a), v in zip(kalem, ys)],
                             hovertemplate="%{customdata}<extra></extra>"), row=1, col=1)
        ys2 = [T["senaryo"][sen]["tufe_2ay_petrol"], T["senaryo"][sen]["tufe_12ay_tcmb"]]
        fig.add_trace(go.Bar(x=["2 ay, ölçülen", "12 ay, TCMB kuralı"], y=ys2, name=f"{sen} dolar", marker_color=renk,
                             legendgroup=sen, showlegend=False,
                             customdata=[f"{a}: +{vir(v, 1)} puan ({sen} dolar)" for a, v in zip(("2 ay", "12 ay"), ys2)],
                             hovertemplate="%{customdata}<extra></extra>"), row=2, col=1)
    fig.update_layout(barmode="group", bargap=0.25)
    fig.update_xaxes(tickangle=0)
    _bitir(fig, "08_tufe.html",
           f"Şekil 08 — 150 dolarda akaryakıt iki ayda +%{vir(T['senaryo']['150']['kalem']['akaryakit'], 0)}, TÜFE'ye "
           f"{vir(T['senaryo']['150']['tufe_2ay_petrol'], 1)} puan",
           [f"Yalnız petrolün payı: kalem esnekliği ({T['donem']}, aylık; aynı ay ve bir ay gecikme) × ön vade Brent'in log değişimi; "
            "kurun payı dışarıda, çünkü yönetilen patika petrol olmasa da sürer",
            "ÖTV ve eşel mobil kararları bu hesabın dışında (Şekil 09) · 12 ay: TCMB'nin %10 → 1 puan kuralı"], 620)


# ─────────────────────────────────────────────────────────────────────── 09
def sekil_09():
    """ÖTV tamponu: senaryonun litre başına maliyeti (KDV hariç) ile yürürlükteki ÖTV."""
    T = O["otv_tampon"]
    urunler = [("motorin", "Motorin", "motorin"), ("kurşunsuz benzin 95 oktan", "Benzin (95 oktan)", "benzin")]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.20, shared_xaxes=True,
                        subplot_titles=("Motorin, TL/litre (KDV hariç)", "Benzin 95, TL/litre (KDV hariç)"))
    for satir, (urun, ad, k) in enumerate(urunler, start=1):
        for sen, renk in (("125", MAVI), ("150", CLARET)):
            S = T["senaryo"][sen]
            for bacak, etiket, desen in (("ham_tl_litre", "ham petrol", ""), (f"{k}_urun_tl_litre", "ürün fiyatı", "/")):
                v = S[bacak]
                fig.add_trace(go.Bar(x=[v], y=[f"{sen} dolar · {etiket}"], orientation="h", marker_color=renk,
                                     marker_pattern_shape=desen, marker_pattern_fgcolor="white", showlegend=False,
                                     customdata=[f"{ad} · {sen} dolar · {etiket}: +{vir(v, 2)} TL/litre"],
                                     hovertemplate="%{customdata}<extra></extra>"), row=satir, col=1)
        o = T["otv"][urun]
        for deger, renk_ in ((o["baz"], GRI), (o["hedef"], MUREKKEP)):
            fig.add_vline(x=deger, line=dict(color=renk_, width=1.4, dash="dash"), row=satir, col=1)
    # ÖTV çizgilerinin adı ve değeri lejantta (çizginin yanına yazılan etiket telefonda panel başlığıyla çakışıyordu)
    mo, be = T["otv"]["motorin"], T["otv"]["kurşunsuz benzin 95 oktan"]
    for ay_ad, a, b_, renk_ in (("Ekim", mo["baz"], be["baz"], GRI), ("Kasım", mo["hedef"], be["hedef"], MUREKKEP)):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=renk_, width=1.4, dash="dash"),
                                 name=f"{ay_ad} ÖTV'si: motorin {vir(a, 2)} · benzin {vir(b_, 2)}", hoverinfo="skip"),
                      row=1, col=1)
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="TL/litre, KDV hariç", row=2, col=1)
    m = T["senaryo"]["125"]
    _bitir(fig, "09_otv.html",
           f"Şekil 09 — 125 dolarda motorinin litre maliyeti +{vir(m['ham_tl_litre'], 1)} ile +{vir(m['motorin_urun_tl_litre'], 1)} TL arası; "
           f"Kasım'da ÖTV {vir(T['otv']['motorin']['hedef'], 0)} TL",
           [f"Ham petrol: ön vadenin varil başına artışı (125'te +{vir(m['brent_artis_varil'], 2)}, 150'de "
            f"+{vir(T['senaryo']['150']['brent_artis_varil'], 2)} dolar) / 158,99 litre × senaryonun USD/TRY'si; marj sabit",
            "Ürün fiyatı (taralı): ABD motorin (ULSD) ve benzin (RBOB) vadelisinin senaryodaki artışı; Akdeniz ürün fiyatının vekili",
            "Kesikli çizgi: yürürlükteki ÖTV (11606 ve 11822 sayılı kararlar) — vergi indirimiyle karşılanabilecek azami tutar"], 520)


# ─────────────────────────────────────────────────────────────────────── 10
def sekil_10():
    E = O["enerji_faturasi"]["senaryo_kural"]
    adlar = [("bugun", "bugünkü fiyat"), ("125", "125 dolar"), ("150", "150 dolar")]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16,
                        subplot_titles=("Yıllık ek enerji faturası, milyar dolar", "Cari denge, GSYH'nin %'si"))
    for kural, renk, etiket in (("petrol", MAVI, "yalnız petrol (gaz sabit)"), ("petrol_gaz", CLARET, "petrol ve gaz birlikte")):
        ys = [E[a][kural]["ek"] for a, _ in adlar]
        fig.add_trace(go.Bar(x=[b for _, b in adlar], y=ys, name=etiket, marker_color=renk, legendgroup=kural,
                             customdata=[f"{b}: +{vir(v, 1)} milyar $ ({etiket})" for (_, b), v in zip(adlar, ys)],
                             hovertemplate="%{customdata}<extra></extra>"), row=1, col=1)
        cs = [E[a][kural]["cari_gsyh"] for a, _ in adlar]
        fig.add_trace(go.Bar(x=[b for _, b in adlar], y=cs, name=etiket, marker_color=renk, legendgroup=kural, showlegend=False,
                             customdata=[f"{b}: {vir(v, 2)} ({etiket})" for (_, b), v in zip(adlar, cs)],
                             hovertemplate="%{customdata}<extra></extra>"), row=2, col=1)
    ef = O["enerji_faturasi"]
    fig.add_hline(y=ef["cari_gsyh"], line=dict(color=GRI, width=1, dash="dash"), row=2, col=1)
    fig.update_layout(barmode="group")
    fig.update_xaxes(tickangle=0)
    _bitir(fig, "10_cari.html",
           f"Şekil 10 — 150 dolar bir yıl kalırsa cari açık/GSYH %{vir(-E['150']['petrol']['cari_gsyh'], 1)}–"
           f"{vir(-E['150']['petrol_gaz']['cari_gsyh'], 1)}",
           [f"Son 12 ay (son ay {ef['son_ay'][5:]}.{ef['son_ay'][:4]}): net enerji faturası {vir(ef['net_12a'], 1)}, cari açık {vir(-ef['cari_12a'], 1)} milyar dolar "
            f"(cari açık/GSYH %{vir(-ef['cari_gsyh'], 2)}, kesikli çizgi); o dönemin Brent ortalaması {vir(ef['brent_12a_ort_vadeli'], 1)}",
            "Kural: aylık net enerji faturasının Brent'e eğimi, 0–6 ay gecikme, 2010+ (Yöntem eki); fatura bir yıl o fiyatta kalırsa"], 640)


# ─────────────────────────────────────────────────────────────────────── 11
def sekil_11():
    pen = O["tum_yukselisler"]["pencere"]
    gruplar = [("2026", lambda p: p["son"] >= "2026-01-01", CLARET, "circle", 12),
               ("2026 öncesi, arz baskın", lambda p: p["son"] < "2026-01-01" and p["nyfed"] and p["nyfed"]["arz"] > p["nyfed"]["talep"], MAVI, "square", 9),
               ("2026 öncesi, talep baskın", lambda p: p["son"] < "2026-01-01" and p["nyfed"] and p["nyfed"]["arz"] <= p["nyfed"]["talep"], KEHRIBAR, "diamond", 10),
               ("2026 öncesi, ayrıştırılamayan", lambda p: p["son"] < "2026-01-01" and not p["nyfed"], GRI, "circle-open", 9)]
    fig = go.Figure()
    for ad, f, renk, sembol, boy in gruplar:
        ps = [p for p in pen if f(p) and p["deger"].get("spx") is not None and p["deger"].get("us2y") is not None]
        if not ps:
            continue
        fig.add_trace(go.Scatter(x=[p["deger_yuzde"]["spx"] for p in ps], y=[p["deger"]["us2y"] for p in ps], mode="markers", name=ad,
                                 marker=dict(color=renk, symbol=sembol, size=boy, line=dict(color="white" if "open" not in sembol else renk, width=1)),
                                 customdata=[f"{tarih(p['bas'])}–{tarih(p['son'])} · Brent {yuzde(p['brent_yuzde'], 1)} · S&P {yuzde(p['deger_yuzde']['spx'], 1)} · "
                                             f"ABD 2y {isaretli(p['deger']['us2y'], 0)} bp" for p in ps],
                                 hovertemplate="%{customdata}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=ACIK, width=1))
    fig.add_vline(x=0, line=dict(color=ACIK, width=1))
    fig.update_xaxes(title="S&P 500, 21 iş günlük değişim, %")
    fig.update_yaxes(title="ABD 2 yıllık, baz puan")
    t = O["tum_yukselisler"]
    _bitir(fig, "11_tarih.html",
           f"Şekil 11 — 2026'da ABD 2 yıllık her petrol yükselişinde arttı (medyan {bp(t['ozet']['y2026']['us2y']['medyan'], 1)}); "
           f"önceki arz kaynaklı yükselişlerde medyan {bp(t['ozet']['once_arz']['us2y']['medyan'], 1)}",
           [f"Vadeli Brent'in 21 iş günde en az +%{vir(O['senaryo_yeri']['senaryo']['125']['yuzde'], 1)} yükseldiği, birbirine 40 günden yakın olmayan pencereler, 1988–2026",
            "Arz/talep: NY Fed petrol fiyatı dinamikleri ayrıştırması (Kasım 2023'te durdu)"], 520)


def main() -> int:
    if go is None:
        raise SystemExit("plotly yok — figürler çizilemez (kapı yolu `dogrula.py` plotly istemez)")
    for ad in SEKILLER:
        globals()[f"sekil_{ad[:2]}"]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
