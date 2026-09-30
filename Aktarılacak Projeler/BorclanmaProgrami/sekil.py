#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BORÇLANMA PROGRAMI (30.09.2026) — analiz figürleri.

Bu bir HAT DEĞİL, tek bir analizin çizim katmanı. Analiz yayımlandığı günün
metnidir (karar 08.09.2026); figürler de o günün ölçümünü dondurur ve
`site/public/analiz/<slug>/` altına yazılır — hat figürleri gibi her koşuda
tazelenmez, sayfa damgası basmaz, her figür kendi tarihini kendi alt
başlığında taşır.

GİRDİ TEK YERDEN: `veri/olcum.json` (`olcum.py` üretir). Figür ile metin iki
ayrı hesaptan beslenseydi bir gün sessizce ayrışırdı. Gerçekleşen vade de
oradan gelir (ihale sonuçlarından, valörden itfaya gün/365) — hattın kendi
vade defteri başka bir konvansiyon taşıyor ve bir ihaleyi düşürüyor.

Sayı biçimi sitenin sözleşmesidir: ondalık virgül, binlik nokta, eksi U+2212.
Plotly'nin eksen ve ipucu biçimi `separators` ile aynı sözleşmeye çekilir.
Plotly başlığı SARMAZ, taşırır: alt yazı `_sar` ile satırlara bölünür ve üst
boşluk satır sayısından türer.

Fonksiyon adı = yazıdaki şekil numarası = dosya adının öneki = figürün içindeki
"Şekil NN" başlığı (dogrula.py son üçünü sorar).

  python3 sekil.py
  python3 site/tools/plotly_stil.py site/public/analiz/borclanma-programi-vade-2026-09-30/*.html
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

SLUG = "borclanma-programi-vade-2026-09-30"
CIKTI = KOK / "site" / "public" / "analiz" / SLUG
PLOTLY_JS = "/js/plotly-4.0.0.min.js"
MUREKKEP, CLARET, MAVI, GRI, ALTIN, YESIL, ACIK = (
    "#1a1a1a", "#8c2f39", "#2f5d8c", "#8a8a8a", "#b8860b", "#3a7d44", "#d8d4cc")
AY_KISA = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
AY_UZUN = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
           "Eylül", "Ekim", "Kasım", "Aralık"]
SEKILLER = ["01_odeme_takvimi", "02_finansman", "03_dogrudan_tarihce", "04_servis_ceyrek",
            "05_vade_patika", "06_eylul", "07_kisa_uc", "08_egri"]
SATIR = 100                            # alt yazının satır başına azami karakteri


def vir(x: float, b: int = 1) -> str:
    s = f"{x:,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return s.replace("-", "−")


def ay_etiket(a: str) -> str:
    return f"{AY_KISA[int(a[5:])]} {a[2:4]}"


def ay_uzun(a: str) -> str:
    return f"{AY_UZUN[int(a[5:])]} {a[:4]}"


def _sar(metin: str, n: int = SATIR) -> str:
    """Sözcük sınırında satırlara böler (plotly başlığı kırpmaz, taşırır)."""
    satirlar, s = [], ""
    for k in metin.split(" "):
        if s and len(s) + 1 + len(k) > n:
            satirlar.append(s)
            s = k
        else:
            s = f"{s} {k}" if s else k
    satirlar.append(s)
    return "<br>".join(satirlar)


def _yaz(fig, ad: str, yukseklik: int = 480) -> None:
    satir = (fig.layout.title.text or "").count("<br>") + 1
    fig.update_layout(
        height=yukseklik, margin=dict(l=64, r=28, t=40 + 21 * satir, b=74), separators=",.",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        title=dict(x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor=ACIK, ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    fig.write_html(CIKTI / f"{ad}.html", include_plotlyjs=PLOTLY_JS, full_html=True,
                   config={"displayModeBar": False, "responsive": True})
    print(f"  ✓ {(CIKTI / (ad + '.html')).relative_to(KOK)}")


def _baslik(fig, no: str, metin: str, alt: str) -> None:
    alt_s = _sar(alt).replace("<br>", "</sub><br><sub>")
    fig.update_layout(title=dict(text=f"{_sar(f'Şekil {no} — {metin}', 90)}<br><sub>{alt_s}</sub>"))


def _veri_sonu(o: dict) -> str:
    v = o["maliyet"]["veri_sonu"]
    return f"{v[8:10]}.{v[5:7]}.{v[:4]}"


# ─────────────────────────────────────────────────────────────── 01
def sekil01(o: dict) -> None:
    od = o["odeme"]["yeni_gunler"]
    pr = o["program"]["yeni"]
    vl = o["takvim"]["valor_aylik"]
    # Takvimin valör verdiği satırlar: ihale + doğrudan satış. Kamuya satışın
    # valörü belgede yok; çubuğa girmez. Her ayın bu satırları tek valör gününde.
    assert all(len(vl[a]) == 1 for a in vl), vl
    valor = {vl[a][0]: pr[a]["ihale"] + pr[a]["dogrudan"] for a in sorted(vl)}
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[g["gun"] for g in od], y=[g["toplam"] for g in od], name="iç borç ödemesi",
                         marker_color=CLARET, width=86400000 * 1.4,
                         hovertemplate="%{x|%d.%m.%Y}: %{y:.1f} milyar TL ödeme<extra></extra>"))
    fig.add_trace(go.Bar(x=list(valor), y=list(valor.values()),
                         name="ayın ihale ve doğrudan satış programı (valör günü)",
                         marker_color=MAVI, opacity=0.55, width=86400000 * 1.4, offset=86400000 * 0.8,
                         hovertemplate="%{x|%d.%m.%Y} valörlü planlı ihraç: %{y:.1f} milyar TL<extra></extra>"))
    fig.add_annotation(x="2026-10-07", y=o["odeme"]["en_buyuk_mlr"],
                       text=f"7 Ekim: {vir(o['odeme']['en_buyuk_mlr'])} milyar TL ödeme<br>"
                            "Ekim'in ihale ve doğrudan satışları bu gün valörlü",
                       showarrow=True, ax=90, ay=-30, font=dict(size=11))
    for g in ("2026-10-14", "2026-10-21"):
        fig.add_vline(x=g, line=dict(color=GRI, width=1, dash="dot"))
    fig.add_annotation(x="2026-10-28", y=190, text="noktalı çizgiler: Ekim'in öbür iki ödeme günü<br>"
                       "(önceki takvimde 12–13 Ekim ihaleleri 14 Ekim valörlüydü)",
                       showarrow=False, font=dict(size=10, color=GRI), xanchor="left")
    fig.update_yaxes(title_text="milyar TL")
    fig.update_xaxes(tickformat="%d.%m", range=["2026-09-28", "2026-12-31"])
    _baslik(fig, "01", "Ekim'in ihraçları tek güne, çeyreğin en büyük ödemesine toplandı",
            "30.09.2026 belgesi · ödemeler: iç borç ödeme takvimi · program: finansman tablosunun ihale ve "
            "doğrudan satış satırları, takvimdeki valör gününe konmuş (kamuya satışın valörü belgede yok)")
    _yaz(fig, "01_odeme_takvimi", 480)


# ─────────────────────────────────────────────────────────────── 02
def sekil02(o: dict) -> None:
    y, e = o["program"]["yeni"], o["program"]["eski"]
    satirlar = [("Ekim · 31 Ağustos belgesi", e["2026-10"]), ("Ekim · 30 Eylül belgesi", y["2026-10"]),
                ("Kasım · 31 Ağustos belgesi", e["2026-11"]), ("Kasım · 30 Eylül belgesi", y["2026-11"]),
                ("Aralık · 30 Eylül belgesi", y["2026-12"])]
    ad = [s[0] for s in satirlar][::-1]
    fig = go.Figure()
    for anahtar, etiket, renk in (("ihale", "piyasadan ihale", MAVI), ("dogrudan", "doğrudan satış", ALTIN),
                                  ("kamu", "kamuya satış", YESIL),
                                  ("borclanma_disi", "borçlanma dışı kaynaklar", ACIK)):
        v = [s[1][anahtar] for s in satirlar][::-1]
        fig.add_trace(go.Bar(y=ad, x=v, orientation="h", name=etiket, marker_color=renk,
                             text=[vir(x) if x >= 30 else "" for x in v], textposition="inside",
                             insidetextanchor="middle", textangle=0, insidetextfont=dict(size=11),
                             hovertemplate="%{y}<br>" + etiket + ": %{x:.1f} milyar TL<extra></extra>"))
    fig.add_trace(go.Scatter(y=ad, x=[s[1]["ic_servis"] for s in satirlar][::-1], mode="markers",
                             name="iç borç servisi", marker=dict(symbol="line-ns-open", size=22,
                                                                  color=CLARET, line=dict(width=3)),
                             hovertemplate="%{y}<br>iç borç servisi: %{x:.1f} milyar TL<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title_text="milyar TL")
    _baslik(fig, "02", "İki belge, ortak iki ay: Ekim'in finansmanı ihaleden doğrudan satışa kaydı",
            "HMB İç Borçlanma Stratejisi, 31.08.2026 ve 30.09.2026 belgelerinin finansman programı · "
            "çubuğun tamamı = ödemeler (iç + dış borç servisi); dış borçlanma sıfır · Kasım ve Aralık "
            "sütunları belgede geçici · 30'un altındaki dilimlerin tutarı ipucunda")
    _yaz(fig, "02_finansman", 490)


# ─────────────────────────────────────────────────────────────── 03
def sekil03(o: dict) -> None:
    ft = o["finansman_tarihce"]
    seri = ft["seri"]
    aylar = sorted(seri)
    renk = [CLARET if a == "2026-10" else (ALTIN if a.startswith("2026") else GRI) for a in aylar]
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=aylar, y=[seri[a]["dogrudan"] for a in aylar], marker_color=renk,
                         name="doğrudan satış (milyar TL)", showlegend=False,
                         customdata=[ay_etiket(a) for a in aylar],
                         hovertemplate="%{customdata}: %{y:.1f} milyar TL<extra></extra>"), secondary_y=False)
    for etiket, r in (("2025 ve öncesi", GRI), ("2026", ALTIN), ("Ekim 2026", CLARET)):
        fig.add_trace(go.Bar(x=[None], y=[None], marker_color=r, name=f"doğrudan satış · {etiket}"),
                      secondary_y=False)
    fig.add_trace(go.Scatter(x=aylar, y=[seri[a]["dogrudan_pay"] for a in aylar], mode="lines",
                             name="iç borçlanmadaki payı (%)", line=dict(color=MAVI, width=1.4),
                             customdata=[ay_etiket(a) for a in aylar],
                             hovertemplate="%{customdata}: %%{y:.1f}<extra></extra>"), secondary_y=True)
    ek, ey = seri["2026-10"], seri["2026-09"]
    fig.add_annotation(x="2026-10", y=ek["dogrudan"], text=f"Ekim 2026: {vir(ek['dogrudan'])} milyar TL",
                       showarrow=True, ax=-150, ay=-120, font=dict(size=11, color=CLARET),
                       bgcolor="rgba(255,255,255,0.85)")
    fig.add_annotation(x="2026-09", y=ey["dogrudan"], text=f"Eylül 2026: {vir(ey['dogrudan'])}",
                       showarrow=True, ax=-120, ay=-40, font=dict(size=11),
                       bgcolor="rgba(255,255,255,0.85)")
    fig.update_yaxes(title_text="milyar TL", secondary_y=False)
    fig.update_yaxes(title_text="iç borçlanmadaki pay (%)", secondary_y=True, showgrid=False, range=[0, 100],
                     tickmode="array", tickvals=[0, 20, 40, 60, 80, 100])
    fig.update_xaxes(tickformat="%Y", dtick="M12")
    fig.update_layout(barmode="overlay")
    _baslik(fig, "03", "Doğrudan satışlar: 2026 ayrı bir rejim, Eylül istisnaydı",
            f"Her ayın kesin planı (dönemi o ayla başlayan strateji belgesi), {ay_uzun(ft['ilk'])} – "
            f"{ay_uzun(ft['son'])}, {ft['n']} ay · altın, döviz cinsi senet ve kira sertifikası · planlanan tutar")
    _yaz(fig, "03_dogrudan_tarihce", 480)


# ─────────────────────────────────────────────────────────────── 04
def sekil04(o: dict) -> None:
    c = o["finansman_tarihce"]["ceyrek"]
    q = [k for k in sorted(c) if k >= "2022-Ç1"]
    et = {k: f"{k[5:]} {k[2:4]}" + (" (plan)" if k == "2026-Ç4" else "") for k in q}
    fig = go.Figure()
    fig.add_trace(go.Bar(x=q, y=[c[k]["ic_anapara"] for k in q], name="anapara", marker_color="#b9b4aa",
                         hovertemplate="%{x}: anapara %{y:.1f} milyar TL<extra></extra>"))
    fig.add_trace(go.Bar(x=q, y=[c[k]["ic_faiz"] for k in q], name="faiz",
                         marker_color=[CLARET if k == "2026-Ç4" else "#c98a91" for k in q],
                         hovertemplate="%{x}: faiz %{y:.1f} milyar TL<extra></extra>"))
    son = c["2026-Ç4"]
    fig.add_annotation(x="2026-Ç4", y=son["ic_servis"],
                       text=f"plan: {vir(son['ic_servis'])} milyar TL<br>faiz payı %{vir(son['faiz_pay'])}",
                       showarrow=True, ax=-10, ay=-50, font=dict(size=11, color=CLARET))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickmode="array", tickvals=q, ticktext=[et[k] for k in q], tickangle=-45)
    fig.update_yaxes(title_text="milyar TL")
    _baslik(fig, "04", "Dördüncü çeyrek 2026'nın en hafif borç servisi çeyreği ve üçte ikisi faiz",
            "Çeyreklik iç borç servisi, her ayın kesin planından · 2026 Ç4'te Kasım ve Aralık belgenin "
            "geçici sütunları")
    _yaz(fig, "04_servis_ceyrek", 470)


# ─────────────────────────────────────────────────────────────── 05
def sekil05(o: dict) -> None:
    v = o["vade"]
    ga = v["gercek_aylik"]
    aylar_g = [a for a in sorted(ga) if a >= "2025-09"]
    plan = ["2026-10", "2026-11", "2026-12"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[ay_etiket(a) for a in aylar_g], y=[ga[a]["aov"] for a in aylar_g], name="gerçekleşen",
                         marker_color=[CLARET if a >= "2026-08" else "#b9b4aa" for a in aylar_g],
                         hovertemplate="%{x}: %{y:.2f} yıl<extra></extra>"))
    fig.add_trace(go.Bar(x=[ay_etiket(a) for a in plan], y=[v["aylik"][a]["aov"] for a in plan],
                         name="30 Eylül programı (kıyas tahminimiz)", marker_color=MAVI,
                         hovertemplate="%{x} program: %{y:.2f} yıl<extra></extra>"))
    ey31 = o["eylul"]["aov_plan_yazi"]
    fig.add_trace(go.Scatter(x=[ay_etiket("2026-09")], y=[ey31], mode="markers",
                             name="Eylül için 31 Ağustos tahminimiz",
                             marker=dict(symbol="line-ew-open", size=30, color=MUREKKEP, line=dict(width=3)),
                             hovertemplate="Eyl 26, 31.08 tahmini: %{y:.2f} yıl<extra></extra>"))
    fig.add_trace(go.Scatter(x=[ay_etiket(a) for a in ("2026-10", "2026-11")],
                             y=[v["aylik"][a]["aov_karsi"] for a in ("2026-10", "2026-11")],
                             mode="markers", name="aynı ay, 31 Ağustos takvimi (aynı kural)",
                             marker=dict(symbol="diamond", size=12, color=ALTIN, line=dict(color=MUREKKEP, width=1)),
                             hovertemplate="%{x} önceki takvim: %{y:.2f} yıl<extra></extra>"))
    yuv = v["yuvarlanan"]
    ya = [a for a in sorted(yuv)]
    fig.add_trace(go.Scatter(x=[ay_etiket(a) for a in ya], y=[yuv[a] for a in ya], mode="lines+markers",
                             name="3 aylık yuvarlanan (hacim ağırlıklı)", line=dict(color=YESIL, width=2.4),
                             hovertemplate="%{x} yuvarlanan: %{y:.2f} yıl<extra></extra>"))
    eo = o["eylul"]["onceki"]
    p31 = {"2026-08": eo["vp_gecmis_yuv_son"], "2026-09": eo["vp_plan_ay1_yuv"],
           "2026-10": eo["vp_plan_ay2_yuv"], "2026-11": eo["vp_plan_ay3_yuv"]}
    fig.add_trace(go.Scatter(x=[ay_etiket(a) for a in p31], y=[float(x.replace(",", ".")) for x in p31.values()],
                             mode="lines+markers", name="31 Ağustos'ta yayımlanan yuvarlanan projeksiyon",
                             line=dict(color=GRI, width=1.6, dash="dash"),
                             hovertemplate="%{x} 31.08 projeksiyonu: %{y:.2f} yıl<extra></extra>"))
    fig.update_yaxes(title_text="ağırlıklı ortalama vade (yıl)", range=[0, 5.2])
    g = [ga[a]["aov"] for a in ("2026-07", "2026-08", "2026-09")]
    _baslik(fig, "05", f"Vade ihalelerde uzuyor: Temmuz {vir(g[0], 2)}, Ağustos {vir(g[1], 2)}, "
                       f"Eylül {vir(g[2], 2)} yıl",
            f"İhale sonuçları {_veri_sonu(o)}'ya kadar · vade valörden itfaya gün/365 · program ayları "
            "kıyas ihalelerinin son üç satışıyla, hedefin %92'sine ölçekli · kırmızı: Ağustos ve Eylül")
    _yaz(fig, "05_vade_patika", 520)


# ─────────────────────────────────────────────────────────────── 06
def sekil06(o: dict) -> None:
    S = o["eylul"]["satirlar"]
    ad = {"13.09.2028": "2 yıl sabit<br>14.09", "11.09.2030": "4 yıl TLREF<br>14.09",
          "16.04.2031": "5 yıl sabit<br>15.09", "27.09.2034": "8 yıl sabit<br>15.09"}
    x = [ad[r["itfa"]] for r in S]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=[r["plan_mlr"] for r in S], name="31 Ağustos tahminimiz", offsetgroup="p",
                         marker=dict(color="white", line=dict(color=MUREKKEP, width=1.5)),
                         hovertemplate="%{x}<br>tahmin: %{y:.1f} milyar TL<extra></extra>"))
    for anahtar, etiket, renk in (("rekabetci_mlr", "rekabetçi ihale", MAVI),
                                  ("rot_py_mlr", "rekabetçi olmayan · piyasa yapıcı", ALTIN),
                                  ("rot_kamu_mlr", "rekabetçi olmayan · kamu", YESIL)):
        fig.add_trace(go.Bar(x=x, y=[r[anahtar] for r in S], name=etiket, offsetgroup="g", marker_color=renk,
                             hovertemplate="%{x}<br>" + etiket + ": %{y:.1f} milyar TL<extra></extra>"))
    for xi, r in zip(x, S):
        fig.add_annotation(x=xi, y=max(r["gerc_mlr"], r["plan_mlr"]) + 9,
                           text=f"kabul %{vir(r['rekabetci_kabul'], 1)}", showarrow=False,
                           font=dict(size=11, color=CLARET))
    fig.update_layout(barmode="relative")
    fig.update_yaxes(title_text="milyar TL")
    tk, sk = o["eylul"]["tlref_kabul"], o["eylul"]["sabit4_kabul"]
    _baslik(fig, "06", "Eylül: TLREF'te kabul olağan, uzun sabit kuponda 2025–2026'nın en yükseği",
            f"Boş çubuk 31 Ağustos'taki kıyas tahminimiz (hedefin %{vir(o['eylul']['tahmin_0831']['varsayim'], 0)}'si), "
            "dolu çubuk gerçekleşen satış · kabul: rekabetçi ihalede satılanın gelen rekabetçi teklife oranı · "
            f"2025–2026'da öbür TLREF ihalelerinde medyan %{vir(tk['diger_medyan'])}, 4 yıl üstü öbür sabit "
            f"kuponlularda en çok %{vir(sk['diger_maks'])}")
    _yaz(fig, "06_eylul", 500)


# ─────────────────────────────────────────────────────────────── 07
def sekil07(o: dict) -> None:
    import gzip
    import csv
    import io
    ham = gzip.decompress((BURASI / "veri/ihale.csv.gz").read_bytes()).decode("utf-8-sig")
    bono, kup = {}, {}
    for r in csv.DictReader(io.StringIO(ham)):
        g, a, y = r["İhale Tarihi"].split(".")
        ay = f"{y}-{a}"
        if ay < "2024-01":
            continue
        t = float(r["Toplam(Gerçekleşme)"] or 0) / 1000
        if r["Senet Tanımı"] == "Hazine Bonosu":
            bono[ay] = bono.get(ay, 0) + t
        elif r["Senet Tanımı"] == "Kuponsuz Devlet Tahvili":
            kup[ay] = kup.get(ay, 0) + t
    aylar = []
    y_, a_ = 2024, 1
    while (y_, a_) <= (2026, 12):
        aylar.append(f"{y_}-{a_:02d}")
        a_ += 1
        if a_ == 13:
            y_, a_ = y_ + 1, 1
    arz = o["arz"]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[ay_etiket(a) for a in aylar], y=[bono.get(a, 0) for a in aylar],
                         name="Hazine bonosu (≤ 1 yıl)", marker_color=CLARET,
                         hovertemplate="%{x}: %{y:.1f} milyar TL bono<extra></extra>"))
    fig.add_trace(go.Bar(x=[ay_etiket(a) for a in aylar], y=[kup.get(a, 0) for a in aylar],
                         name="kuponsuz devlet tahvili", marker_color=ALTIN,
                         hovertemplate="%{x}: %{y:.1f} milyar TL kuponsuz<extra></extra>"))
    fig.add_trace(go.Bar(x=[ay_etiket("2026-12")], y=[arz["kuponsuz_mlr"]],
                         name="Aralık programı: 16 aylık kuponsuz (kıyas tahminimiz)",
                         marker=dict(color="white", line=dict(color=ALTIN, width=2), pattern=dict(shape="/")),
                         hovertemplate="Ara 26 programı: %{y:.1f} milyar TL<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="milyar TL (ihale satışı; Aralık: tahmin)")
    tt = o["takvim_tarihce"]
    _baslik(fig, "07", "Kısa uç: Eylül–Aralık dört ayda bono yok, Aralık'ta 16 aylık kuponsuz var",
            f"Gerçekleşen ihale satışları ({_veri_sonu(o)}'ya kadar) · arşivin kesin takvimlerindeki "
            f"{tt['kuponsuz_n_onceki']} önceki kuponsuz satırının en uzunu {tt['kuponsuz_maks_gun_onceki']} gün")
    _yaz(fig, "07_kisa_uc", 470)


# ─────────────────────────────────────────────────────────────── 08
def sekil08(o: dict) -> None:
    P = o["piyasa"]
    d, once = P["guncel"]["dibs-verim-egrisi"], P["onceki"]
    dug = ["spot_3a", "spot_6a", "spot_1y", "spot_2y", "spot_3y", "spot_5y", "spot_7y"]
    et = ["3 ay", "6 ay", "1 yıl", "2 yıl", "3 yıl", "5 yıl", "7 yıl"]
    fig = make_subplots(rows=1, cols=2, column_widths=[0.56, 0.44], horizontal_spacing=0.12,
                        subplot_titles=("Sıfır kuponlu getiri (%)", "Değişim (baz puan)"))
    fig.add_trace(go.Scatter(x=et, y=[once[k] for k in dug], mode="lines+markers", name="28.08.2026",
                             line=dict(color=GRI, width=2, dash="dash"),
                             hovertemplate="%{x}: %%{y:.2f}<extra>28.08</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=et, y=[d[k] for k in dug], mode="lines+markers", name=d["_tarih"],
                             line=dict(color=CLARET, width=2.6),
                             hovertemplate="%{x}: %%{y:.2f}<extra>" + d["_tarih"][:5] + "</extra>"), 1, 1)
    fark = [P["fark_bp"][k] for k in dug]
    fig.add_trace(go.Bar(x=et, y=fark, marker_color=[CLARET if f > 0 else MAVI for f in fark], showlegend=False,
                         text=[vir(f, 0) for f in fark], textposition="outside",
                         hovertemplate="%{x}: %{y:.0f} bp<extra></extra>"), 1, 2)
    fig.add_hline(y=0, line=dict(color="#bbb", width=1), row=1, col=2)
    fig.update_yaxes(range=[-40, 230], row=1, col=2)
    # alt başlıkların (subplot) konumu üst boşluk büyüyünce kaymasın diye aynı kalır
    _baslik(fig, "08", "Eylül'de eğrinin 3–7 yıl bölgesi 150–190 baz puan satıldı",
            f"TCMB DİBS gösterge değerlerinden sıfır kuponlu getiri · 28.08.2026 ile {d['_tarih']} · "
            "9 yıl düğümü bu aralıkta ölçülemedi")
    _yaz(fig, "08_egri", 470)


def main() -> int:
    if go is None:
        raise SystemExit("plotly kurulu değil — figürler çizilemez")
    o = json.loads((BURASI / "veri/olcum.json").read_text(encoding="utf-8"))
    for f in (sekil01, sekil02, sekil03, sekil04, sekil05, sekil06, sekil07, sekil08):
        f(o)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
