#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörünün REHBER FİGÜRLERİ — gerçek barlardan.

NEDEN VAR. "Nasıl okunur, nasıl işlem yapılır, ne beklemeli" soruları metinle
tam anlatılamaz: indikatörün ürettiği şey görseldir. Bu araç o görseli
depodaki GERÇEK barlardan çizer — uydurma bar yok, uydurma işlem yok.

TEK KAYNAK. Kuralların kendisi burada DEĞİL: figürler `brooks_referans`i içe
aktarır, yani sayfadaki kodun ürettiği şeyi çizer. Üçüncü bir uygulama
tutulsaydı figür ile kod bir gün sessizce ayrışır ve okur hangisine
bakacağını bilemezdi.

ÇIKTI: site/public/indikatorler/*.html — sayfaya GrafikEmbed ile girer.

    python3 site/tools/brooks_sekil.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(SITE / "public" / "indikatorler"))
sys.path.insert(0, str(SITE.parent))

import plotly.graph_objects as go                                # noqa: E402
import brooks_ornek as O                                         # noqa: E402
import brooks_referans as R                                      # noqa: E402
import plotly_stil                                               # noqa: E402
from ortak import bicim as B                                     # noqa: E402

CIKTI = SITE / "public" / "indikatorler"

# Ev paleti — Pine dosyalarındaki renklerle AYNI olmalı, yoksa okur figürde
# gördüğü rengi grafikte bulamaz.
MUREKKEP = "#1a1a1a"
CLARET = "#8c2f39"
MAVI = "#2f5d8c"
GRI = "#8a8a8a"
KAGIT = "#ffffff"


def _kaynaklar() -> dict[str, O.Kaynak]:
    kay = [O.bar_oku(y) for y in sorted((SITE / "public" / "teknik").glob("*.html"))]
    return {k.anahtar: k for k in kay if O.govde_kunyesi(k.seri)["gecti"]}


def _sar(metin: str, en: int = 104) -> str:
    """Alt yazıyı satırlara böler. Plotly başlığı kırpmaz, TAŞIRIR: bir alt
    yazının sağ ucu figürün dışında kalırsa okur onu hiç görmez ve eksik
    kaldığını da anlamaz."""
    satir, simdi = [], ""
    for sozcuk in metin.split(" "):
        if simdi and len(simdi) + 1 + len(sozcuk) > en:
            satir.append(simdi)
            simdi = sozcuk
        else:
            simdi = f"{simdi} {sozcuk}".strip()
    if simdi:
        satir.append(simdi)
    return "<br>".join(satir)


def _duzen(fig: go.Figure, baslik: str, alt: str, yuk: int = 560) -> go.Figure:
    alt = _sar(alt)
    fig.update_layout(
        title=dict(text=f"<b>{baslik}</b><br><span style='font-size:12px;color:{GRI}'>{alt}</span>",
                   x=0, xanchor="left", font=dict(size=15, color=MUREKKEP)),
        height=yuk, paper_bgcolor=KAGIT, plot_bgcolor=KAGIT,
        font=dict(family="IBM Plex Mono, ui-monospace, monospace", size=11, color=MUREKKEP),
        margin=dict(l=56, r=24, t=62 + 16 * alt.count("<br>"), b=48),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, font=dict(size=10)),
        xaxis=dict(showgrid=False, linecolor=GRI, rangeslider=dict(visible=False)),
        yaxis=dict(gridcolor="#ececec", zeroline=False, linecolor=GRI),
        hovermode="x unified",
    )
    return fig


def _mum(fig: go.Figure, s: R.Seri, fp: R.FiyatPaneli, bas: int, son: int) -> None:
    """Barları SINIFINA göre boyar — Pine'daki barcolor ile aynı dil."""
    x = list(range(bas, son))
    renk = []
    for i in x:
        renk.append(MAVI if fp.guclu_boga(i) else CLARET if fp.guclu_ayi(i)
                    else GRI if fp.sinif(i) == "doji"
                    else "#93b0cd" if s.c[i] > s.o[i] else "#c99aa0")
    for i, c in zip(x, renk):
        fig.add_trace(go.Candlestick(
            x=[i], open=[s.o[i]], high=[s.h[i]], low=[s.l[i]], close=[s.c[i]],
            increasing=dict(line=dict(color=c, width=1), fillcolor=c),
            decreasing=dict(line=dict(color=c, width=1), fillcolor=c),
            showlegend=False, hoverinfo="skip"))


def _an(iso: str) -> str:
    """"2026-08-31T12:30" → "31.08.2026 12:30" — ISO yazım okur metnine girmez."""
    g, sa = iso[:10], iso[11:16]
    return f"{g[8:10]}.{g[5:7]}.{g[:4]}" + (f" {sa}" if sa else "")


def _zaman_ekseni(fig: go.Figure, s: R.Seri, bas: int, son: int, adim: int = 8) -> None:
    """Yatay eksende BAR SIRA NUMARASI değil SEANS SAATİ yazar.

    Mumlar sıra numarasına çizilmek zorunda (hafta sonu boşluğu bir bar
    genişliğinde kalsın diye), ama okurun elinde sıra numarası YOKTUR —
    "360" bir gözlem değil bizim dizinimizdir."""
    yer = list(range(bas, son, adim))
    fig.update_xaxes(tickmode="array", tickvals=yer,
                     ticktext=[_an(s.zaman[i])[:5] + _an(s.zaman[i])[10:] for i in yer],
                     tickfont=dict(size=9))


def sekil_01(kay: dict) -> Path:
    """İndikatör grafikte NASIL GÖRÜNÜR — bütün katmanlar tek pencerede."""
    k = kay["xu100-s1"]
    s = k.seri
    fp = R.FiyatPaneli(s)
    yon, donus, _ = fp.always_in()
    sayim = fp.bar_sayimi()
    hedef = max(i for i in donus if i < len(s) - 20)
    bas, son = max(0, hedef - 34), min(len(s), hedef + 26)

    fig = go.Figure()
    # Always-in zemini
    i = bas
    while i < son:
        j = i
        while j < son and yon[j] == yon[i]:
            j += 1
        if yon[i] != 0:
            fig.add_vrect(x0=i - 0.5, x1=j - 0.5, line_width=0,
                          fillcolor=MAVI if yon[i] == 1 else CLARET, opacity=0.06)
        i = j
    _mum(fig, s, fp, bas, son)
    fig.add_trace(go.Scatter(x=list(range(bas, son)), y=[fp.ema[i] for i in range(bas, son)],
                             mode="lines", line=dict(color=GRI, width=2), name="20 barlık EMA"))
    for i in donus:
        if bas <= i < son:
            fig.add_annotation(x=i, y=s.l[i] if yon[i] == 1 else s.h[i],
                               text="▲" if yon[i] == 1 else "▼", showarrow=False,
                               yshift=-16 if yon[i] == 1 else 16,
                               font=dict(size=15, color=MAVI if yon[i] == 1 else CLARET))
    for i in range(bas, son):
        for boga in (True, False):
            if not fp.donus_bari(i, boga):
                continue
            kal = fp.kalite(i, boga)
            filtre = fp.yon_filtresi(i)
            if kal < 3 or (filtre == "yalnız AL" and not boga) or (filtre == "yalnız SAT" and boga):
                continue
            fig.add_annotation(x=i, y=s.l[i] if boga else s.h[i], text=f"{kal}/4",
                               showarrow=False, yshift=-22 if boga else 22,
                               font=dict(size=10, color=MAVI if boga else CLARET))
        if sayim[i]:
            fig.add_annotation(x=i, y=s.h[i] if sayim[i][0] == "H" else s.l[i], text=sayim[i],
                               showarrow=False, yshift=13 if sayim[i][0] == "H" else -13,
                               font=dict(size=9, color=MAVI if sayim[i][0] == "H" else CLARET))
    for ad, c in (("güçlü boğa barı", MAVI), ("güçlü ayı barı", CLARET), ("doji · ara", GRI)):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                 marker=dict(color=c, size=8, symbol="square"), name=ad))
    _zaman_ekseni(fig, s, bas, son)
    _duzen(fig, "Şekil 01 · İndikatör grafikte ne çizer",
           f"BIST 100 · 1 saatlik · {_an(s.zaman[bas])} → {_an(s.zaman[son - 1])} — "
           "bar rengi sınıfı, zemin always-in yönünü, üçgen dönüş barını, "
           "n/4 sinyal kalitesini, H1–H4 geri çekilme sayımını gösterir", 600)
    yol = CIKTI / "01_indikator_gorunumu.html"
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_02(kay: dict) -> Path:
    """OKUMA SIRASI — dört adım, tek karar barında."""
    k = kay["xu100-s1"]
    s = k.seri
    fp = R.FiyatPaneli(s)
    rp = R.RejimPanosu(s)
    yon, donus, _ = fp.always_in()
    hedef = None
    for i in range(len(s) - 20, 120, -1):
        if fp.donus_bari(i, False) and fp.kalite(i, False) == 4 and yon[i] == -1:
            hedef = i
            break
    hedef = hedef or max(donus)
    bas, son = max(0, hedef - 30), min(len(s), hedef + 14)

    fig = go.Figure()
    i = bas
    while i < son:
        j = i
        while j < son and yon[j] == yon[i]:
            j += 1
        if yon[i] != 0:
            fig.add_vrect(x0=i - 0.5, x1=j - 0.5, line_width=0,
                          fillcolor=MAVI if yon[i] == 1 else CLARET, opacity=0.06)
        i = j
    _mum(fig, s, fp, bas, son)
    fig.add_trace(go.Scatter(x=list(range(bas, son)), y=[fp.ema[i] for i in range(bas, son)],
                             mode="lines", line=dict(color=GRI, width=2), name="20 barlık EMA"))
    fig.add_vline(x=hedef, line=dict(color=MUREKKEP, width=1, dash="dot"))

    o = rp.olcu(hedef) or {}
    boga = fp.kalite(hedef, True) >= fp.kalite(hedef, False)
    kal = fp.kalite(hedef, boga)
    adim = [
        ("① REJİM", f"{o.get('n', '—')}/5 → {o.get('rejim', 'ölçülemedi')}",
         "bant ise bar sayımına dayalı stop girişi bırakılır"),
        ("② YÖN", {1: "LONG", -1: "SHORT", 0: "belirsiz"}[yon[hedef]],
         "karşı yön işlemi dersin varsayılan yasağı"),
        ("③ YASAK", fp.yon_filtresi(hedef), "yasak varsa o yönde etiket basılmaz"),
        ("④ KURULUM", f"{kal}/4 {'boğa' if boga else 'ayı'}",
         "en son bakılır — sıra bozulursa yanlış günde doğru kurulum alınır"),
    ]
    ust = max(s.h[i] for i in range(bas, son))
    alt = min(s.l[i] for i in range(bas, son))
    ad = ust - alt
    for n, (baslik, deger, not_) in enumerate(adim):
        fig.add_annotation(x=bas + 0.5, y=ust + ad * (0.30 - n * 0.075),
                           text=f"<b>{baslik}</b>  {deger}  <span style='color:{GRI}'>· {not_}</span>",
                           showarrow=False, xanchor="left", align="left",
                           font=dict(size=11, color=MUREKKEP))
    fig.update_yaxes(range=[alt - ad * 0.10, ust + ad * 0.40])
    _zaman_ekseni(fig, s, bas, son)
    _duzen(fig, "Şekil 02 · Okuma sırası: rejim → yön → yasak → kurulum",
           f"BIST 100 · 1 saatlik · karar barı {_an(s.zaman[hedef])} — "
           "ders bu sırayı dayatır ve kurulumu EN SONA koyar", 620)
    yol = CIKTI / "02_okuma_sirasi.html"
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_03(kay: dict) -> Path:
    """İŞLEM MEKANİĞİ — giriş, stop, hedef; hepsi barın kendi sayılarından.

    İndikatör emir vermez; bu figür DERSİN emir kuralını gerçek bir bar
    üzerinde aritmetiğiyle gösterir. Sayılar barın ucundan türer, bizden
    değil: giriş barın ucunun bir tick ötesi, stop karşı ucun bir tick
    ötesi, ilk hedef en az bir bar boyu."""
    k = kay["xu100-s1"]
    s = k.seri
    fp = R.FiyatPaneli(s)
    yon, donus, _ = fp.always_in()
    hedef = None
    for i in range(len(s) - 25, 120, -1):
        if fp.donus_bari(i, False) and fp.kalite(i, False) == 4 and yon[i] == -1 \
                and fp.yon_filtresi(i) != "yalnız AL":
            hedef = i
            break
    if hedef is None:
        raise SystemExit("ENGEL · hizalı 4/4 ayı örneği bulunamadı")
    bas, son = max(0, hedef - 12), min(len(s), hedef + 18)

    giris, stop = s.l[hedef], s.h[hedef]
    risk = stop - giris
    hedef1 = giris - risk

    fig = go.Figure()
    _mum(fig, s, fp, bas, son)
    for deger, ad, renk, dash in (
            (stop, f"stop {B.sayi(stop, 0)} — barın karşı ucunun bir tick ötesi", CLARET, "dash"),
            (giris, f"giriş {B.sayi(giris, 0)} — barın ucunun bir tick ötesi", MUREKKEP, "solid"),
            (hedef1, f"ilk hedef {B.sayi(hedef1, 0)} — bir bar boyu (1R)", MAVI, "dot")):
        fig.add_hline(y=deger, line=dict(color=renk, width=1.4, dash=dash))
        fig.add_annotation(x=son - 1, y=deger, text=ad, showarrow=False, xanchor="right",
                           yshift=9, font=dict(size=10, color=renk),
                           bgcolor="rgba(255,255,255,0.82)", borderpad=2)
    fig.add_vrect(x0=hedef - 0.5, x1=hedef + 0.5, line_width=0, fillcolor=MUREKKEP, opacity=0.05)
    fig.add_annotation(x=hedef, y=s.h[hedef], text="sinyal barı 4/4", showarrow=True,
                       arrowhead=0, arrowwidth=1, arrowcolor=CLARET, ax=0, ay=-34,
                       font=dict(size=11, color=CLARET),
                       bgcolor="rgba(255,255,255,0.9)", borderpad=3)
    ulasti = [i for i in range(hedef + 1, son) if s.l[i] <= hedef1]
    vurdu = [i for i in range(hedef + 1, son) if s.h[i] >= stop]
    sonuc = ("hedefe ulaştı" if ulasti and (not vurdu or ulasti[0] < vurdu[0])
             else "stop oldu" if vurdu else "pencere içinde ikisi de görülmedi")
    _zaman_ekseni(fig, s, bas, son)
    _duzen(fig, "Şekil 03 · Emir mekaniği: giriş, stop, hedef",
           f"BIST 100 · 1 saatlik · sinyal barı {_an(s.zaman[hedef])} — "
           f"risk {B.sayi(risk, 0)} puan · bu pencerede {sonuc}. "
           "İndikatör emir vermez; bu ölçü dersin emir kuralının bar üzerindeki karşılığıdır", 560)
    yol = CIKTI / "03_islem_mekanigi.html"
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_04(kay: dict) -> Path:
    """NE BEKLEMELİ — kalıpların ölçülen sıklığı."""
    import collections
    say = collections.Counter()
    bar = 0
    for k in kay.values():
        fp = R.FiyatPaneli(k.seri)
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(k.seri)):
            bar += 1
            if fp.tirasli(i):
                say[fp.tirasli(i)] += 1
            if fp.kalip(i):
                say["kırılım modu kalıbı"] += 1
            if fp.iki_barlik_donus(i):
                say["iki barlık dönüş"] += 1
            if fp.mikro_cift(i):
                say[fp.mikro_cift(i)] += 1
            if fp.bar_boyu(i):
                say[fp.bar_boyu(i)] += 1
            if abs(fp.mikro_kanal(i)) >= 5:
                say["mikro kanal ≥ 5 bar"] += 1
            if fp.iptal_kurali(i)["iptal"]:
                say["beş bar iptal kuralı"] += 1
        _, donus, _ = fp.always_in()
        say["always-in dönüşü"] += len([i for i in donus if i >= 3])
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(k.seri)):
            for boga in (True, False):
                if fp.donus_bari(i, boga) and fp.kalite(i, boga) == 4:
                    say["4/4 sinyal barı"] += 1

    sirali = say.most_common()
    fig = go.Figure(go.Bar(
        x=[100 * v / bar for _, v in sirali], y=[a for a, _ in sirali], orientation="h",
        marker=dict(color=[CLARET if a in ("always-in dönüşü", "4/4 sinyal barı") else MAVI
                           for a, _ in sirali]),
        text=[f"{B.sayi(v, 0)}  ·  {B.yuzde(100 * v / bar, 2)}" for _, v in sirali], textposition="outside",
        textfont=dict(size=10), hoverinfo="skip", showlegend=False))
    fig.update_xaxes(title="barların yüzdesi", range=[0, max(100 * v / bar for _, v in sirali) * 1.45])
    fig.update_yaxes(autorange="reversed")
    _duzen(fig, "Şekil 04 · Ne beklemeli: kalıpların ölçülen sıklığı",
           f"13 seri · {B.sayi(bar, 0)} bar · 1 saatlik, 4 saatlik ve günlük — "
           "kırmızı olanlar sistemin EN SEYREK konuştuğu iki hâl", 620)
    return _yaz(fig, "04_ne_beklemeli_siklik.html")


def _yaz(fig: go.Figure, ad: str) -> Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_05(kay: dict) -> Path:
    """4/4 BİR İŞLEM DEĞİLDİR — en yüksek skorun always-in ile hizası."""
    hiza = {"aynı yönde (hizalı)": 0, "ters yönde": 0, "always-in belirsiz": 0}
    for k in kay.values():
        fp = R.FiyatPaneli(k.seri)
        yon, _, _ = fp.always_in()
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(k.seri)):
            for boga in (True, False):
                if not (fp.donus_bari(i, boga) and fp.kalite(i, boga) == 4):
                    continue
                if yon[i] == 0:
                    hiza["always-in belirsiz"] += 1
                elif (yon[i] == 1) == boga:
                    hiza["aynı yönde (hizalı)"] += 1
                else:
                    hiza["ters yönde"] += 1
    top = sum(hiza.values())
    fig = go.Figure(go.Bar(
        x=list(hiza.keys()), y=list(hiza.values()),
        marker=dict(color=[MAVI, CLARET, GRI]),
        text=[f"{v}" for v in hiza.values()], textposition="outside",
        textfont=dict(size=13), hoverinfo="skip", showlegend=False))
    fig.update_yaxes(title="4/4 sinyal barı sayısı", range=[0, max(hiza.values()) * 1.35])
    _duzen(fig, "Şekil 05 · Dört üzerinden dört bir işlem DEĞİLDİR",
           f"Ölçülen {top} adet 4/4 sinyal barından yalnız {hiza['aynı yönde (hizalı)']} tanesi "
           "always-in yönüyle aynı yönde. Puanın yüksekliği, dersin karşı yön yasağını "
           "geçersiz kılmaz", 480)
    return _yaz(fig, "05_kalite_hizasi.html")


def sekil_06(kay: dict) -> Path:
    """REJİM DAĞILIMI — pano çoğu zaman 'ne o, ne bu' der."""
    ad, bant, ara, trend = [], [], [], []
    for a, k in kay.items():
        rp = R.RejimPanosu(k.seri)
        d = {"BANT": 0, "ara": 0, "trend": 0}
        for i in range(len(k.seri)):
            o = rp.olcu(i)
            if o:
                d[o["rejim"]] += 1
        n = sum(d.values())
        if not n:
            continue
        ad.append(f"{O.ENSTRUMAN_AD.get(k.slug, k.slug)} · {O.DILIM_AD.get(k.dilim, k.dilim)}")
        bant.append(100 * d["BANT"] / n)
        ara.append(100 * d["ara"] / n)
        trend.append(100 * d["trend"] / n)
    fig = go.Figure()
    for v, nm, c in ((bant, "BANT", CLARET), (ara, "ara", GRI), (trend, "trend", MAVI)):
        fig.add_trace(go.Bar(x=v, y=ad, orientation="h", name=nm, marker=dict(color=c)))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(title="pencerelerin yüzdesi", range=[0, 100])
    fig.update_yaxes(autorange="reversed")
    _duzen(fig, "Şekil 06 · Rejim panosu çoğu zaman karar vermez",
           "Her serinin 70 barlık pencerelerinin rejim dağılımı — "
           "'ara' baskın hâldir ve bu bir kusur değil, ölçünün dürüstlüğüdür", 560)
    return _yaz(fig, "06_rejim_dagilimi.html")


def sekil_07(kay: dict) -> Path:
    """ÇEVİRME SAYACI — sinyal var, hüküm yok. Ölçüm bir eşiğin hükmünü çürüttü."""
    hep, flip = [], []
    for k in kay.values():
        fp = R.FiyatPaneli(k.seri)
        _, donus, _ = fp.always_in()
        dset = {i for i in donus if i >= 3}
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(k.seri)):
            c = fp.cevirme(i)["kapanis"]
            hep.append(c)
            if i in dset:
                flip.append(c)
    kova = [0, 1, 2, 3, 5, 8, 15, 30, 60, 101]
    et = ["0", "1", "2", "3–4", "5–7", "8–14", "15–29", "30–59", "60+"]

    def pay(v):
        out = [0] * (len(kova) - 1)
        for x in v:
            for j in range(len(kova) - 1):
                if kova[j] <= x < kova[j + 1]:
                    out[j] += 1
                    break
        return [100 * o / len(v) for o in out]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=et, y=pay(hep), name=f"bütün barlar ({B.sayi(len(hep), 0)})", marker=dict(color=GRI)))
    fig.add_trace(go.Bar(x=et, y=pay(flip), name=f"always-in dönüş barları ({len(flip)})",
                         marker=dict(color=CLARET)))
    fig.update_layout(barmode="group")
    fig.update_xaxes(title="bar kapanışını tersine çeviren ardışık bar sayısı")
    fig.update_yaxes(title="kendi kümesinin yüzdesi")
    ust = sum(1 for v in hep if v > 15)
    ustf = sum(1 for v in flip if v > 15)
    _duzen(fig, "Şekil 07 · Sayaçta sinyal var, hüküm yok",
           f"Dönüş barlarında sayaç belirgin yüksek (medyan {sorted(flip)[len(flip)//2]} "
           f"karşı {sorted(hep)[len(hep)//2]}) — ama '>15 ise always-in çeviren kırılım' "
           f"hükmü tutmuyor: >15 diyen {B.sayi(ust, 0)} barın yalnız {ustf} tanesi dönüş "
           f"barı, kesinlik {B.yuzde(100 * ustf / ust, 2)}, taban oran "
           f"{B.yuzde(100 * len(flip) / len(hep), 2)}", 560)
    return _yaz(fig, "07_cevirme_sayaci.html")


def main() -> None:
    CIKTI.mkdir(parents=True, exist_ok=True)
    kay = _kaynaklar()
    if not kay:
        raise SystemExit("ENGEL · gövde kapısından geçen seri yok")
    for fn in (sekil_01, sekil_02, sekil_03, sekil_04, sekil_05, sekil_06, sekil_07):
        yol = fn(kay)
        durum = plotly_stil.isle(yol)
        print(f"  {yol.name:34s} {durum}")
    print(f"\n{len(kay)} seri · figürler {CIKTI.relative_to(SITE.parent)} altında")


if __name__ == "__main__":
    main()
