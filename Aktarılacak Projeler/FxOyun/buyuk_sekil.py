#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mum derslerinin figürleri (FX gün içi serisinin 6–9. dersleri).

GİRDİ TEK YERDEN: `veri/buyuk_ders.json` (buyuk_ders_olcum.py). Figürler `site/public/arastirma/<slug>/NN_ad.html`
dosyasına yazılır; dosya adının öneki = dersteki gömmenin numarası = başlıktaki "Şekil NN" (dogrula.py sorar).
Çift y eksenli grafik yok. Saatler TSİ.

  python3 buyuk_sekil.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
sys.dont_write_bytecode = True

import sekil_ortak as so  # noqa: E402
from sekil_ortak import go, make_subplots, vir  # noqa: E402

OLCUM = BURASI / "veri" / "buyuk_ders.json"
D = json.loads(OLCUM.read_text(encoding="utf-8"))
CLARET, MAVI, GRI, TURUNCU, YESIL, MUREKKEP = so.CLARET, so.MAVI, so.GRI, so.TURUNCU, so.YESIL, so.MUREKKEP
TSI = timezone(timedelta(hours=3))
DONEM = {"ic": "2018–2023", "dis": "2024 →"}
TF = ["5", "15", "60"]
TF_AD = {"5": "5 dakika", "15": "15 dakika", "60": "1 saat"}
TF_RENK = {"5": MAVI, "15": TURUNCU, "60": CLARET}
KAYNAK = "Dukascopy 1 dakikalık alış-satış fiyatları · " + ", ".join(f"{c[:3]}/{c[3:]}" for c in D["kunye"]["ciftler"])
#: Ders → figürler (buyuk_ders_yaz.SEKIL ile aynı; kapı ikisini kıyaslar).
SEKILLER = {
    "fx-buyuk-mum": ["01_ornek", "02_yol", "03_geri"],
    "fx-buyuk-suzgec": ["01_net", "02_yarisi"],
    "fx-buyuk-giris": ["01_izgara", "02_ters_secim", "03_maliyet"],
    "fx-buyuk-plan": ["01_bacaklar", "02_egri"],
}
SUZ_AD = {"kova": "Büyüklük", "kapanis": "Kapanışın yeri", "seans": "Seans", "haber": "Takvimdeki haber",
          "trend": "Günlük trend", "kosu": "Önceki koşu", "gun_ucu": "Günün yeni ucu", "oynaklik": "Günlük oynaklık",
          "ardisik": "Yakında başka büyük mum"}
DEGER_AD = {"uc": "uca yakın", "orta": "ortada", "geri": "geri verilmiş", "asya": "Asya", "londra": "Londra",
            "ortusme": "örtüşme", "ny": "NY öğleden sonra", "haber": "var", "haber_yok": "yok",
            "trendle": "trend yönünde", "karsi": "trende karşı", "yatay": "yatay", "ayni": "aynı yönde",
            "ters": "ters yönde", "sakin": "sakin", "evet": "evet", "hayir": "hayır", "dusuk": "düşük",
            "yuksek": "yüksek", "2-3": "2–3 ATR", "3-4": "3–4 ATR", "4-5": "4–5 ATR", "5+": "5+ ATR"}
EMIR_AD = {"piyasa": "piyasa", "limit_0.25": "limit %25", "limit_0.5": "limit %50", "limit_0.62": "limit %62",
           "stop": "stop", "onayli": "onaylı", "limit_uc": "limit uçta", "limit_ote": "limit uç + ½ ATR"}
YON_AD = {"devam": "mumun yönünde", "ters": "mumun tersine"}


def pay(x: float, b: int = 0) -> str:
    return so.yuzde(x * 100, b)


def rr(x: float) -> str:
    return ("+" if round(x, 2) > 0 else "") + vir(0.0 if round(x, 2) == 0 else x, 2)


def giris_ad(g: str, kisa: bool = False) -> str:
    y, e, s, h = g.split(":")
    ad = f"{YON_AD[y]} · {EMIR_AD[e]}"
    return ad if kisa else f"{ad} · stop {s[1:]} ATR · hedef {h[1:]} R"


def _bitir(fig, slug: str, ad: str, bas: str, alt: list[str], cizim: int) -> None:
    baslik = so.baslik_koy(fig, bas, alt)
    alan = cizim - 78
    so._yaz(fig, slug, f"{ad}.html", so.yukseklik(baslik, cizim), ust=so.ust_pay(baslik),
            lejant_y=-min(0.16, 70 / max(alan, 1)), olcum=OLCUM)


# ─────────────────────────────────────────────────────────────── ders 6: büyük mumdan sonra
def mum_01():
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.09,
                        subplot_titles=[f"{TF_AD[k]} · {so.tarih(D['ornek'][k]['gun'])} · mum "
                                        f"{vir(D['ornek'][k]['kat'], 1)} ATR" for k in TF])
    for r, k in enumerate(TF, start=1):
        o = D["ornek"][k]
        olc = 10 ** 5
        zt = [datetime.fromtimestamp(m[0], TSI).strftime("%d.%m %H:%M") for m in o["mumlar"]]
        fig.add_trace(go.Candlestick(x=zt, open=[m[1] / olc for m in o["mumlar"]], high=[m[2] / olc for m in o["mumlar"]],
                                     low=[m[3] / olc for m in o["mumlar"]], close=[m[4] / olc for m in o["mumlar"]],
                                     increasing=dict(line=dict(color=MAVI, width=1), fillcolor=MAVI),
                                     decreasing=dict(line=dict(color=CLARET, width=1), fillcolor=CLARET),
                                     showlegend=False, hoverinfo="skip"), row=r, col=1)
        x0 = datetime.fromtimestamp(o["bt"], TSI).strftime("%d.%m %H:%M")
        orta = (o["h"] + o["l"]) / 2 / olc
        for y, dash, renk in ((o["h"] / olc, "solid", GRI), (o["l"] / olc, "solid", GRI), (orta, "dash", MUREKKEP)):
            fig.add_hline(y=y, line=dict(color=renk, width=1, dash=dash), row=r, col=1)
        fig.add_trace(go.Scatter(x=[x0], y=[(o["h"] if o["yon"] > 0 else o["l"]) / olc], mode="markers",
                                 marker=dict(symbol="triangle-down" if o["yon"] > 0 else "triangle-up", size=11,
                                             color=MUREKKEP), showlegend=False, hoverinfo="skip"), row=r, col=1)
        fig.update_xaxes(type="category", nticks=5, tickangle=0, rangeslider_visible=False, row=r, col=1)
        fig.update_yaxes(tickformat=".4f", nticks=4, row=r, col=1)
    _bitir(fig, "fx-buyuk-mum", "01_ornek",
           "Şekil 01 — Üç dilimde birer büyük mum: aralığı önceki ATR'nin 3–4 katı",
           ["EUR/USD, 2018–2023'ün son uygun olayları (haber yok, kapanış uca yakın). Üçgen büyük mumun ucu, düz "
            "çizgiler mumun iki ucu, kesikli çizgi mumun yarısı; sonrasında 24 mum. Saatler TSİ.", KAYNAK], 3 * 270 + 60)


def mum_02():
    fig = go.Figure()
    for k in TF:
        for dn, dash in (("ic", "solid"), ("dis", "dot")):
            v = D["yol"][k][dn]
            x, y = [p["mum"] for p in v], [p["ort"] for p in v]
            alt = [p["alt"] for p in v]
            ust = [p["ust"] for p in v]
            if dn == "ic":
                fig.add_trace(go.Scatter(x=x + x[::-1], y=ust + alt[::-1], fill="toself", line=dict(width=0),
                                         fillcolor=TF_RENK[k] + "22", showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", name=f"{TF_AD[k]} · {DONEM[dn]}",
                                     line=dict(color=TF_RENK[k], width=2, dash=dash),
                                     customdata=[f"{TF_AD[k]} · {DONEM[dn]} · {h}. mum: {rr(t)} ATR"
                                                 f" (%95 aralık {rr(a)} … {rr(u)})" for h, t, a, u in zip(x, y, alt, ust)],
                                     hovertemplate="%{customdata}<extra></extra>"))
    fig.add_hline(y=0, line=dict(color="#bdb8ad", width=1))
    fig.update_xaxes(title_text="büyük mumdan sonra, mum (dilimin kendi mumu)", title_font=dict(size=11), dtick=4)
    fig.update_yaxes(title_text="mumun yönünde ortalama hareket, ATR", title_font=dict(size=11))
    _bitir(fig, "fx-buyuk-mum", "02_yol",
           "Şekil 02 — Ortalama yol: 5 dakikada hafif geri, 1 saatte hafif ileri",
           ["Büyük mumun kapanışından sonra ortalama fiyat, mumun yönünde ve olayın ATR'si cinsinden. Düz çizgi "
            "2018–2023 (gölge: işlem günü düzeyinde %95 aralık), noktalı 2024 →. Maliyet yok.", KAYNAK], 500)


def mum_03():
    seviyeler = [("geri_0.25", "%25"), ("geri_0.5", "%50"), ("geri_0.62", "%62"), ("geri_1.0", "öbür uç")]
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True, subplot_titles=[TF_AD[k] for k in TF], horizontal_spacing=0.06)
    for c, k in enumerate(TF, start=1):
        for dn, renk, sembol in (("ic", GRI, "circle"), ("dis", CLARET, "diamond")):
            v = D["davranis"][k][dn]
            fig.add_trace(go.Scatter(x=[(v[m] - v[f"ayna_{m}"]) * 100 for m, _ in seviyeler], y=[ad for _, ad in seviyeler],
                                     mode="markers", name=DONEM[dn], showlegend=c == 1,
                                     marker=dict(color=renk, size=9, symbol=sembol),
                                     customdata=[f"{TF_AD[k]} · {DONEM[dn]} · {ad} geri çekilme: gerçek {pay(v[m])}, ayna "
                                                 f"{pay(v['ayna_' + m])}" for m, ad in seviyeler],
                                     hovertemplate="%{customdata}<extra></extra>"), row=1, col=c)
        fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1), row=1, col=c)
        fig.update_xaxes(range=[-8, 8], dtick=4, row=1, col=c)
    fig.update_xaxes(title_text="gerçek − ayna, puan", title_font=dict(size=11), row=1, col=2)
    fig.update_yaxes(autorange="reversed")
    _bitir(fig, "fx-buyuk-mum", "03_geri",
           "Şekil 03 — Geri çekilme şanstan sık mı? 5 dakikada evet, 1 saatte hayır",
           ["24 mum içinde fiyatın mumun ucundan %25, %50, %62 ve mumun öbür ucuna kadar geri gelme payı, eksi aynı "
            "payın aynalanmış yolda (yön rastgele olsaydı) değeri. Sağı şanstan sık. Gri 2018–2023, bordo 2024 →.",
            KAYNAK], 420)


# ─────────────────────────────────────────────────────────────── ders 7: süzgeçler
def _suzgec_satirlar():
    s = []
    for f, vals in [(f, list(D["suzgec"]["5"][f])) for f in SUZ_AD]:
        for v in vals:
            s.append((f, v, f"{SUZ_AD[f]} · {DEGER_AD[v]}"))
    return s


def suzgec_01():
    satir = _suzgec_satirlar()
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True, subplot_titles=[TF_AD[k] for k in TF], horizontal_spacing=0.05)
    for c, k in enumerate(TF, start=1):
        for dn, renk, sembol in (("ic", GRI, "circle"), ("dis", CLARET, "diamond")):
            xs, ys, er_a, er_u, cd = [], [], [], [], []
            for f, v, ad in satir:
                n = D["suzgec"][k][f][v][dn]
                if not n.get("n") or n["net_24"]["ort"] is None or n["net_24"]["alt"] is None:
                    continue
                t = n["net_24"]
                xs.append(t["ort"]), ys.append(ad), er_a.append(t["ort"] - t["alt"]), er_u.append(t["ust"] - t["ort"])
                cd.append(f"{TF_AD[k]} · {ad} · {DONEM[dn]} · {n['n']} olay · {rr(t['ort'])} ATR "
                          f"({rr(t['alt'])} … {rr(t['ust'])})")
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=DONEM[dn], showlegend=c == 1,
                                     marker=dict(color=renk, size=7, symbol=sembol),
                                     error_x=dict(type="data", symmetric=False, array=er_u, arrayminus=er_a,
                                                  color=renk, thickness=1, width=0),
                                     customdata=cd, hovertemplate="%{customdata}<extra></extra>"), row=1, col=c)
        fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1), row=1, col=c)
        fig.update_xaxes(range=[-1.2, 1.2], dtick=0.5, row=1, col=c)
    fig.update_xaxes(title_text="24 mum sonra mumun yönünde, ATR", title_font=dict(size=11), row=1, col=2)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    _bitir(fig, "fx-buyuk-suzgec", "01_net",
           "Şekil 01 — Süzgeçler 24 mum sonrasını çoğu zaman ayırmıyor",
           ["Her süzgeç değerinde büyük mumdan 24 mum sonra ortalama hareket (mumun yönünde, ATR), işlem günü düzeyinde "
            "%95 aralıkla. Gri 2018–2023, bordo 2024 →. Sağı mumun yönünde, solu tersine. Maliyet yok.", KAYNAK],
           22 * len(satir) + 140)


def suzgec_02():
    satir = _suzgec_satirlar()
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True, subplot_titles=[TF_AD[k] for k in TF], horizontal_spacing=0.05)
    for c, k in enumerate(TF, start=1):
        for dn, renk, sembol in (("ic", GRI, "circle"), ("dis", CLARET, "diamond")):
            xs, ys, cd = [], [], []
            for f, v, ad in satir:
                n = D["suzgec"][k][f][v][dn]
                if not n.get("n"):
                    continue
                x = (n["sim_1.0"] - 0.5) * 100
                xs.append(x), ys.append(ad)
                cd.append(f"{TF_AD[k]} · {ad} · {DONEM[dn]} · {n['n']} olay · ±1 ATR'den önce mumun yönündeki: "
                          f"{pay(n['sim_1.0'])}")
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="markers", name=DONEM[dn], showlegend=c == 1,
                                     marker=dict(color=renk, size=7, symbol=sembol), customdata=cd,
                                     hovertemplate="%{customdata}<extra></extra>"), row=1, col=c)
        fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1), row=1, col=c)
        fig.update_xaxes(range=[-12, 12], dtick=5, row=1, col=c)
    fig.update_xaxes(title_text="mumun yönündeki +1 ATR önce, %50'den farkı, puan", title_font=dict(size=11), row=1, col=2)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    _bitir(fig, "fx-buyuk-suzgec", "02_yarisi",
           "Şekil 02 — Fiyat önce hangi yöne 1 ATR gidiyor: süzgeçler payı birkaç puan oynatıyor",
           ["Kapanıştan ±1 ATR'lik iki seviyeden önce görülenin mumun yönündeki seviye olma payı, %50'den farkı "
            "(puan). Sağı devam, solu dönüş. Gri 2018–2023, bordo 2024 →.", KAYNAK], 22 * len(satir) + 140)


# ─────────────────────────────────────────────────────────────── ders 8: giriş
def giris_01():
    fig = make_subplots(rows=1, cols=3, shared_yaxes=True, subplot_titles=[TF_AD[k] for k in TF], horizontal_spacing=0.05)
    etiketler = None
    for c, k in enumerate(TF, start=1):
        ic = {r["giris"]: r for r in D["izgara"][k]["ic"]}
        dis = {r["giris"]: r for r in D["izgara"][k]["dis"]}
        sec = sorted([g for g in ic if g.endswith(":s2:h1")], key=lambda g: (g.split(":")[0], g))
        etiket = [giris_ad(g, kisa=True) for g in sec]
        etiketler = etiket
        for alan, renk, sembol, ad in (("brut_R", GRI, "circle", "maliyetten önce"), ("ort_R", CLARET, "diamond", "maliyetten sonra")):
            for dn, op in (("ic", 0.45), ("dis", 1.0)):
                kaynak = ic if dn == "ic" else dis
                xs = [kaynak[g][alan] if g in kaynak and kaynak[g].get(alan) is not None else None for g in sec]
                fig.add_trace(go.Scatter(x=xs, y=etiket, mode="markers", name=f"{ad} · {DONEM[dn]}",
                                         showlegend=c == 1, opacity=op,
                                         marker=dict(color=renk, size=8, symbol=sembol),
                                         customdata=[f"{TF_AD[k]} · {e} · {ad} · {DONEM[dn]}: "
                                                     f"{rr(x) if x is not None else '—'} R" for e, x in zip(etiket, xs)],
                                         hovertemplate="%{customdata}<extra></extra>"), row=1, col=c)
        fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1), row=1, col=c)
    fig.update_xaxes(title_text="işlem başına, R", title_font=dict(size=11), row=1, col=2)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    _bitir(fig, "fx-buyuk-giris", "01_izgara",
           "Şekil 01 — On bir giriş biçimi: maliyetten önce sıfır çevresinde, sonra hepsi eksi",
           ["Stop 2 ATR, hedef 1 R. Gri maliyetten önce (orta fiyat, kaymasız), bordo maliyetten sonra; soluk "
            "2018–2023, koyu 2024 →. 2024 → ızgarası seçimde kullanılmadı.", KAYNAK], 30 * len(etiketler or []) + 160)


def giris_02():
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=["Limit doldu", "Limit dolmadı"],
                        horizontal_spacing=0.06)
    satir = [r for r in D["ters_secim"]["ic"] if r["giris"].endswith(":s2:h1")]
    etiket = [f"{TF_AD[str(r['tf'])]} · {giris_ad(r['giris'], kisa=True)}" for r in satir]
    for c, (alan, ad) in enumerate((("piyasa_kazanma_dolan", "doldu"), ("piyasa_kazanma_kacan", "dolmadı")), start=1):
        for dn, renk, sembol in (("ic", GRI, "circle"), ("dis", CLARET, "diamond")):
            kaynak = {(r["tf"], r["giris"]): r for r in D["ters_secim"][dn]}
            xs = [kaynak[(r["tf"], r["giris"])][alan] for r in satir]
            xs = [None if x is None else x * 100 for x in xs]
            fig.add_trace(go.Scatter(x=xs, y=etiket, mode="markers", name=DONEM[dn], showlegend=c == 1,
                                     marker=dict(color=renk, size=8, symbol=sembol),
                                     customdata=[f"{e} · {ad} · {DONEM[dn]} · aynı anda piyasadan girilseydi kazanma "
                                                 f"{'—' if x is None else so.yuzde(x, 0)}" for e, x in zip(etiket, xs)],
                                     hovertemplate="%{customdata}<extra></extra>"), row=1, col=c)
        fig.add_vline(x=50, line=dict(color="#bdb8ad", width=1), row=1, col=c)
        fig.update_xaxes(range=[0, 100], dtick=25, ticksuffix="", tickprefix="%", row=1, col=c)
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    _bitir(fig, "fx-buyuk-giris", "02_ters_secim",
           "Şekil 02 — Limit, kaybedecek işlemde dolar, kazanacak işlemi kaçırır",
           ["Aynı olayda, limit emir koyulsaydı dolduğu ve dolmadığı durumlar ayrı ayrı: aynı anda piyasadan, aynı "
            "stop (2 ATR) ve hedefle (1 R) girilseydi kazanma oranı. Gri 2018–2023, bordo 2024 →.", KAYNAK],
           32 * len(satir) + 160)


def giris_03():
    fig = go.Figure()
    for k in TF:
        for s, sembol in (("s1", "circle"), ("s2", "diamond")):
            rs = [r for r in D["izgara"][k]["ic"] if f":{s}:" in r["giris"] and r.get("maliyet_R") is not None]
            fig.add_trace(go.Scatter(x=[r["risk_pip_med"] for r in rs], y=[r["maliyet_R"] for r in rs], mode="markers",
                                     name=f"{TF_AD[k]} · stop {s[1:]} ATR", marker=dict(color=TF_RENK[k], symbol=sembol, size=8,
                                                                                     opacity=0.75),
                                     customdata=[f"{TF_AD[k]} · {giris_ad(r['giris'])} · risk {vir(r['risk_pip_med'], 1)} pip · "
                                                 f"maliyet {vir(r['maliyet_R'], 2)} R" for r in rs],
                                     hovertemplate="%{customdata}<extra></extra>"))
    fig.update_xaxes(title_text="planlanan risk, medyan pip", title_font=dict(size=11), type="log")
    fig.update_yaxes(title_text="maliyet, R (maliyetten önce − sonra)", title_font=dict(size=11), rangemode="tozero")
    _bitir(fig, "fx-buyuk-giris", "03_maliyet",
           "Şekil 03 — Stop ne kadar yakınsa maliyet o kadar büyük bir R",
           ["2018–2023, giriş ızgarasının her hücresi: yatayda planlanan riskin medyanı (logaritmik), dikeyde makas ve "
            "kaymanın R cinsinden payı. Dilim ve stop uzaklığı ayrı işaretli.", KAYNAK], 480)


# ─────────────────────────────────────────────────────────────── ders 9: plan
def _bacak_ad(b: dict) -> str:
    ad = f"{TF_AD[str(b['tf'])]} · {giris_ad(b['giris'], kisa=True)}"
    if b["suzgec"]:
        ad += f" · {SUZ_AD[b['suzgec']].lower()} {DEGER_AD[b['deger']]}"
    return ad + (" (işlem)" if b["rol"] == "islem" else "")


def plan_01():
    liste = D["bacak"]
    etiket = [_bacak_ad(b) for b in liste]
    fig = go.Figure()
    for dn, renk, sembol in (("ic", GRI, "circle"), ("dis", CLARET, "diamond")):
        xs = [b[dn]["ort_R"] for b in liste]
        kw = {}
        if dn == "dis":
            kw["error_x"] = dict(type="data", symmetric=False, array=[b["dis"]["ust"] - b["dis"]["ort_R"] for b in liste],
                                 arrayminus=[b["dis"]["ort_R"] - b["dis"]["alt"] for b in liste], color=renk, thickness=1,
                                 width=0)
        fig.add_trace(go.Scatter(x=xs, y=etiket, mode="markers", name=DONEM[dn], marker=dict(color=renk, size=8, symbol=sembol),
                                 customdata=[f"{e} · {DONEM[dn]} · {b[dn]['n']} işlem · kazanma {pay(b[dn]['kazanma'])} · "
                                             f"net {rr(b[dn]['ort_R'])} R" for e, b in zip(etiket, liste)],
                                 hovertemplate="%{customdata}<extra></extra>", **kw))
    fig.add_vline(x=0, line=dict(color="#bdb8ad", width=1))
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=10))
    fig.update_xaxes(title_text="işlem başına net, R", title_font=dict(size=11))
    eksi = sum(1 for b in liste if b["dis"]["ort_R"] <= 0)
    kac = "hepsi" if eksi == len(liste) else f"{eksi} tanesi"
    _bitir(fig, "fx-buyuk-plan", "01_bacaklar",
           f"Şekil 01 — {len(liste)} girişin {kac} 2024 sonrasında eksi ya da sıfırda",
           ["Ön kayıtlı üç işlem girişi ve on iki referans giriş. Gri 2018–2023 (işlem girişleri bu dönemden seçildi), "
            "bordo 2024 → ve işlem günü düzeyinde %95 aralık. Maliyet dahil.", KAYNAK], 30 * len(liste) + 160)


def plan_02():
    fig = go.Figure()
    renk = [CLARET, MAVI, TURUNCU]
    for i, b in enumerate([b for b in D["bacak"] if b["rol"] == "islem"]):
        seri = b["ic"]["gunluk"] + b["dis"]["gunluk"]
        top, xs, ys = 0.0, [], []
        for g, v in seri:
            top += v
            xs.append(g), ys.append(top)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", name=_bacak_ad(b), line=dict(color=renk[i % 3], width=2, shape="hv"),
                                 customdata=[f"{_bacak_ad(b)} · {so.tarih(x)} · birikimli {rr(y)} R" for x, y in zip(xs, ys)],
                                 hovertemplate="%{customdata}<extra></extra>"))
    fig.add_vline(x=D["kunye"]["donem"]["dis"][0], line=dict(color=MUREKKEP, width=1, dash="dash"))
    fig.add_hline(y=0, line=dict(color="#bdb8ad", width=1))
    fig.update_yaxes(title_text="birikimli net, R", title_font=dict(size=11))
    _bitir(fig, "fx-buyuk-plan", "02_egri",
           "Şekil 02 — Seçilen üç giriş: seçildikleri dönemde artı, sonrasında değil",
           ["İşlem günü başına toplanan maliyet sonrası sonuçların birikimi. Kesikli dikey çizgi 1 Ocak 2024: solu "
            "girişlerin seçildiği dönem, sağı hiç görülmeyen dönem.", KAYNAK], 460)


CIZ = {("fx-buyuk-mum", "01_ornek"): mum_01, ("fx-buyuk-mum", "02_yol"): mum_02, ("fx-buyuk-mum", "03_geri"): mum_03,
       ("fx-buyuk-suzgec", "01_net"): suzgec_01, ("fx-buyuk-suzgec", "02_yarisi"): suzgec_02,
       ("fx-buyuk-giris", "01_izgara"): giris_01, ("fx-buyuk-giris", "02_ters_secim"): giris_02,
       ("fx-buyuk-giris", "03_maliyet"): giris_03,
       ("fx-buyuk-plan", "01_bacaklar"): plan_01, ("fx-buyuk-plan", "02_egri"): plan_02}


def main() -> int:
    if go is None:
        print("✗ plotly kurulu değil; çizim yolu onu ister")
        return 1
    assert set(CIZ) == {(s, a) for s, ads in SEKILLER.items() for a in ads}
    for k in sorted(CIZ):
        CIZ[k]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
