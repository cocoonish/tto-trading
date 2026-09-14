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

import math
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(BURASI))
sys.path.insert(0, str(SITE / "public" / "indikatorler"))
sys.path.insert(0, str(SITE.parent))

import plotly.graph_objects as go                                # noqa: E402
from plotly.subplots import make_subplots                         # noqa: E402
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


def _mum(fig: go.Figure, s: R.Seri, fp: R.FiyatPaneli, bas: int, son: int,
         row: int | None = None, col: int | None = None) -> None:
    """Barları SINIFINA göre boyar — Pine'daki barcolor ile aynı dil."""
    x = list(range(bas, son))
    renk = []
    for i in x:
        renk.append(MAVI if fp.guclu_boga(i) else CLARET if fp.guclu_ayi(i)
                    else GRI if fp.sinif(i) == "doji"
                    else "#93b0cd" if s.c[i] > s.o[i] else "#c99aa0")
    yer = {} if row is None else {"row": row, "col": col}
    for i, c in zip(x, renk):
        fig.add_trace(go.Candlestick(
            x=[i], open=[s.o[i]], high=[s.h[i]], low=[s.l[i]], close=[s.c[i]],
            increasing=dict(line=dict(color=c, width=1), fillcolor=c),
            decreasing=dict(line=dict(color=c, width=1), fillcolor=c),
            showlegend=False, hoverinfo="skip"), **yer)


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


def sekil_indikator_gorunumu(kay: dict, no: str) -> Path:
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
    _duzen(fig, f"Şekil {no} · İndikatör grafikte ne çizer",
           f"BIST 100 · 1 saatlik · {_an(s.zaman[bas])} → {_an(s.zaman[son - 1])} — "
           "bar rengi sınıfı, zemin always-in yönünü, üçgen dönüş barını, "
           "n/4 sinyal kalitesini, H1–H4 geri çekilme sayımını gösterir", 600)
    yol = CIKTI / f"{no}_indikator_gorunumu.html"
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_okuma_sirasi(kay: dict, no: str) -> Path:
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
    _duzen(fig, f"Şekil {no} · Okuma sırası: rejim → yön → yasak → kurulum",
           f"BIST 100 · 1 saatlik · karar barı {_an(s.zaman[hedef])} — "
           "ders bu sırayı dayatır ve kurulumu EN SONA koyar", 620)
    yol = CIKTI / f"{no}_okuma_sirasi.html"
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_islem_mekanigi(kay: dict, no: str) -> Path:
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
    _duzen(fig, f"Şekil {no} · Emir mekaniği: giriş, stop, hedef",
           f"BIST 100 · 1 saatlik · sinyal barı {_an(s.zaman[hedef])} — "
           f"risk {B.sayi(risk, 0)} puan · bu pencerede {sonuc}. "
           "İndikatör emir vermez; bu ölçü dersin emir kuralının bar üzerindeki karşılığıdır", 560)
    yol = CIKTI / f"{no}_islem_mekanigi.html"
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_ne_beklemeli_siklik(kay: dict, no: str) -> Path:
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
    _duzen(fig, f"Şekil {no} · Ne beklemeli: kalıpların ölçülen sıklığı",
           f"13 seri · {B.sayi(bar, 0)} bar · 1 saatlik, 4 saatlik ve günlük — "
           "kırmızı olanlar sistemin EN SEYREK konuştuğu iki hâl", 620)
    return _yaz(fig, f"{no}_ne_beklemeli_siklik.html")


# ═══════════════════════════════════════════════════════════════════════════
#  KÜÇÜK ÇOKLU — kural atlasının iş atı
#
#  Bir kuralı öğreten şey, sağlandığı hâl kadar SAĞLANMADIĞI hâldir; o yüzden
#  paneller yan yana ve AYNI bar sayısıyla çizilir. Bar sayısı eşit değilse
#  çubuk genişlikleri panelden panele değişir ve okur farkı biçim sanır.
# ═══════════════════════════════════════════════════════════════════════════
def _kucuk_coklu(kay: dict, baslik: str, alt: str, paneller: list[dict],
                 sutun: int = 3, panel_yuk: int = 250) -> go.Figure:
    """paneller: [{etiket, seri, bas, son, vurgu?, isaret?, not_?}]

    vurgu  : işaretlenecek bar indeksleri (tarama)
    cizgi  : [(y, renk, dash)] — panele yatay seviye
    isaret : [(i, metin, ust_mu, renk)] — bara ok/etiket
    ema    : True ise hattın kendi EMA'sı panele çizilir (kural ortalamaya
             göre tanımlıysa okur ortalamayı GÖRMEDEN kuralı izleyemez)
    not_   : panelin altına düşen tek cümlelik okuma notu
    """
    n = len(paneller)
    satir = (n + sutun - 1) // sutun
    # PANEL GENİŞLİKLERİ EŞİTLENİR. Farklı bar sayısı taşıyan paneller aynı
    # figürde yan yana çizilince çubuk genişliği panelden panele değişir ve
    # okur bunu VERİ farkı sanar — dar çubuklu panel "daha sıkışık bir piyasa"
    # gibi görünür. Çıpa korunarak pencere iki yana büyütülür; seri kenarına
    # dayanınca kalan pay öbür yandan alınır.
    hedef = max(p["son"] - p["bas"] for p in paneller)
    for p in paneller:
        boy = len(kay[p["seri"]].seri)
        eksik = hedef - (p["son"] - p["bas"])
        if eksik <= 0:
            continue
        sol = min(eksik // 2, p["bas"])
        sag = eksik - sol
        p["bas"] -= sol
        p["son"] += sag
        if p["son"] > boy:                      # sağa sığmadı, soldan al
            p["bas"] = max(0, p["bas"] - (p["son"] - boy))
            p["son"] = boy
    bar = {p["son"] - p["bas"] for p in paneller}
    if len(bar) > 1:
        # Seri kenarına dayanmış: eşitlenemedi, adıyla söylenir.
        print(f"  ! panel bar sayıları eşitlenemedi: {sorted(bar)} — seri kenarı")
    fig = make_subplots(
        rows=satir, cols=sutun, vertical_spacing=0.14, horizontal_spacing=0.05,
        subplot_titles=[p["etiket"] for p in paneller])
    for k, p in enumerate(paneller):
        r, c = k // sutun + 1, k % sutun + 1
        s = kay[p["seri"]].seri
        fp = R.FiyatPaneli(s)
        if p.get("ema"):
            xe = [i for i in range(p["bas"], p["son"]) if fp.ema[i] is not None]
            fig.add_trace(go.Scatter(
                x=xe, y=[fp.ema[i] for i in xe], mode="lines",
                line=dict(color="#c8a36a", width=1.4), showlegend=False,
                hoverinfo="skip"), row=r, col=c)
        _mum(fig, s, fp, p["bas"], p["son"], row=r, col=c)
        # TARAMA İZLERDEN SONRA EKLENİR. plotly 7'de `add_vrect(row=, col=)`
        # henüz İZ TAŞIMAYAN bir alt panele SESSİZCE düşüyor: istisna yok,
        # uyarı yok, koşu yeşil biter ve alt yazı okura "taralı barlar kalıbın
        # kendisi" der ama tarama hiç çizilmez. `add_hline` aynı yerde
        # çalıştığı için kusur daha da görünmez oluyordu. Aşağıdaki sayım
        # kapısı sessiz düşmeyi ADIYLA yakalar.
        for i in p.get("vurgu", []):
            fig.add_vrect(x0=i - 0.5, x1=i + 0.5, line_width=0,
                          fillcolor="#e8c8a8", opacity=0.55, layer="below",
                          row=r, col=c)
        for y, renk, dash in p.get("cizgi", []):
            fig.add_hline(y=y, line=dict(color=renk, width=1, dash=dash),
                          row=r, col=c)
        for i, metin, ust, renk in p.get("isaret", []):
            fig.add_annotation(
                x=i, y=s.h[i] if ust else s.l[i], text=metin, showarrow=False,
                yshift=16 if ust else -16, font=dict(size=10, color=renk),
                bgcolor="rgba(255,255,255,0.85)", borderpad=2, row=r, col=c)
        fig.update_xaxes(showticklabels=False, showgrid=False, row=r, col=c,
                         rangeslider=dict(visible=False))
        # ÜST BOŞLUK: bara konan etiket barın tepesinden yukarı kayıyor ve
        # otomatik aralıkta panel BAŞLIĞINA giriyor — iki metin üst üste
        # binince ikisi de okunmaz olur. Aralık bu yüzden elle kurulur ve
        # üstte bir etiket boyu pay bırakılır; EMA da menzile dahil, çünkü
        # ortalama barların dışına çıkabiliyor.
        dus = [s.l[i] for i in range(p["bas"], p["son"])]
        yuk = [s.h[i] for i in range(p["bas"], p["son"])]
        if p.get("ema"):
            e = [fp.ema[i] for i in range(p["bas"], p["son"]) if fp.ema[i] is not None]
            dus, yuk = dus + e, yuk + e
        for y, _, _ in p.get("cizgi", []):
            dus.append(y)
            yuk.append(y)
        alt_u, ust_u = min(dus), max(yuk)
        pay = (ust_u - alt_u) or 1.0
        fig.update_yaxes(showticklabels=False, showgrid=False, row=r, col=c,
                         range=[alt_u - pay * 0.08, ust_u + pay * 0.22])
        if p.get("not_"):
            # Notu panelin ALTINA, kâğıt koordinatında yaz: eksen kapalı
            # olduğu için veri koordinatı burada güvenilir bir çıpa değil.
            eks = fig.get_subplot(r, c)
            fig.add_annotation(
                x=(eks.xaxis.domain[0] + eks.xaxis.domain[1]) / 2,
                y=eks.yaxis.domain[0] - 0.035, xref="paper", yref="paper",
                text=p["not_"], showarrow=False, xanchor="center", yanchor="top",
                font=dict(size=9.5, color=GRI))
    bekle = sum(len(p.get("vurgu", [])) + len(p.get("cizgi", [])) for p in paneller)
    if len(fig.layout.shapes) != bekle:
        raise SystemExit(f"ENGEL · {bekle} şekil (tarama + seviye) isteniyor ama "
                         f"{len(fig.layout.shapes)} tanesi figüre girdi — sessizce "
                         "düşen şekil var, alt yazı okura göstermediği bir şeyi anlatır")
    for a in fig.layout.annotations[:n]:
        a.font.size = 11
        a.font.color = MUREKKEP
    _duzen(fig, baslik, alt, yuk=78 + satir * panel_yuk)
    return fig


def _yaz(fig: go.Figure, ad: str) -> Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    return yol


def sekil_kalite_hizasi(kay: dict, no: str) -> Path:
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
    _duzen(fig, f"Şekil {no} · Dört üzerinden dört bir işlem DEĞİLDİR",
           f"Ölçülen {top} adet 4/4 sinyal barından yalnız {hiza['aynı yönde (hizalı)']} tanesi "
           "always-in yönüyle aynı yönde. Puanın yüksekliği, dersin karşı yön yasağını "
           "geçersiz kılmaz", 480)
    return _yaz(fig, f"{no}_kalite_hizasi.html")


def sekil_rejim_dagilimi(kay: dict, no: str) -> Path:
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
    _duzen(fig, f"Şekil {no} · Rejim panosu çoğu zaman karar vermez",
           "Her serinin 70 barlık pencerelerinin rejim dağılımı — "
           "'ara' baskın hâldir ve bu bir kusur değil, ölçünün dürüstlüğüdür", 560)
    return _yaz(fig, f"{no}_rejim_dagilimi.html")


def sekil_cevirme_sayaci(kay: dict, no: str) -> Path:
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
    _duzen(fig, f"Şekil {no} · Sayaçta sinyal var, hüküm yok",
           f"Dönüş barlarında sayaç belirgin yüksek (medyan {sorted(flip)[len(flip)//2]} "
           f"karşı {sorted(hep)[len(hep)//2]}) — ama '>15 ise always-in çeviren kırılım' "
           f"hükmü tutmuyor: >15 diyen {B.sayi(ust, 0)} barın yalnız {ustf} tanesi dönüş "
           f"barı, kesinlik {B.yuzde(100 * ustf / ust, 2)}, taban oran "
           f"{B.yuzde(100 * len(flip) / len(hep), 2)}", 560)
    return _yaz(fig, f"{no}_cevirme_sayaci.html")


def sekil_kirilim_modu(kay: dict, no: str) -> Path:
    """KIRILIM MODU KALIPLARI — beşi de biçimdir, sözle anlatılamaz.

    Her panelde kalıbın kendisi taranmış, iki stop seviyesi çizili ve kalıptan
    SONRAKİ barlar görünür: ders bu kalıplarda yönün BİLİNMEDİĞİNİ söyler ve
    iki tarafa da emir koydurur, yani okur sonrasını görmeden kuralı anlayamaz.
    Son panel aynı kalıbın (ii) zıt sonucudur — kalıp aynı, çıkan yön başka.
    """
    # Örnekler TİPİK olana göre seçildi: kalıp yüksekliğinin serinin medyan bar
    # menziline oranı, o kalıbın medyanına en yakın olan. Mutlak yükseklikle
    # seçmek farklı fiyat ölçeklerini kıyaslamak olurdu.
    SEC = [
        ("ii",  "eurusd-s1", 313, 2),
        ("iii", "eurusd-s1", 187, 3),
        ("ioi", "us10y-s1",  137, 3),
        ("oio", "us10y-s1",  315, 3),
        ("oo",  "eurusd-s4",  60, 2),
        ("ii",  "us10y-s1",  319, 2),
    ]
    ONCE, SONRA = 8, 7
    paneller = []
    for k, (ad, ank, i, n) in enumerate(SEC):
        s = kay[ank].seri
        fp = R.FiyatPaneli(s)
        km = fp.kirilim_modu(i)
        if km is None or km["kalip"] != ad:
            raise SystemExit(f"ENGEL · {ank} i={i} artık '{ad}' değil "
                             f"({km['kalip'] if km else 'kalıp yok'}) — örnek yenilenmeli")
        # Kırılım yönü ÖLÇÜLÜR, varsayılmaz.
        yon, bar = "hiçbiri", None
        for j in range(i + 1, min(i + 1 + 5, len(s))):
            ust, alt = s.h[j] >= km["alis_stop"], s.l[j] <= km["satis_stop"]
            if ust and alt:
                yon, bar = "iki stop da aynı barda", j
                break
            if ust or alt:
                yon, bar = ("yukarı" if ust else "aşağı"), j
                break
        son_ek = f" · {bar - i}. barda" if bar else ""
        paneller.append(dict(
            etiket=f"{ad}" + ("  (aynı kalıp, başka sonuç)" if k == 5 else ""),
            seri=ank, bas=i - ONCE, son=i + SONRA + 1,
            vurgu=list(range(i - n + 1, i + 1)),
            cizgi=[(km["alis_stop"], MAVI, "dot"), (km["satis_stop"], CLARET, "dot")],
            isaret=[(bar, yon, True, MUREKKEP)] if bar else [],
            not_=f"{O.ENSTRUMAN_AD.get(ank.rsplit('-', 1)[0], ank)} · "
                 f"{_an(s.zaman[i])} — {yon}{son_ek}",
        ))
    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Kırılım modu kalıpları: ii · iii · ioi · oio · oo",
        "Taralı barlar kalıbın kendisi; noktalı çizgiler kalıbın kendi uçlarından türeyen iki stop "
        "seviyesi (üstte alış, altta satış). Ders bu kalıplarda yönü BİLMEZ ve iki tarafa da emir "
        "koydurur — panellerin ikisinde iki stop da aynı barda tetiklendi, kuralın en pahalı hâli. "
        "Ölçülen sıklık: ii 100 · oo 55 · ioi 43 · oio 35 · iii 17 (4.314 bar). "
        "Bu altı panel ÖRNEKTİR; kuralın 250 oluşumun tamamında sınanmış hâli "
        f"Şekil {_no('yon_bilinmez')}'dadır",
        paneller, sutun=3, panel_yuk=255)
    return _yaz(fig, f"{no}_kirilim_modu.html")


def _kirilim_olcusu(kay: dict, ufuk: int = 5) -> dict:
    """Kırılım modu kalıplarının SONRASINI ölçer — ve TABAN ORANI ile birlikte.

    Ders 'yön bilinmez' diyor. Bu cümle yalnız kalıp barlarına bakılarak
    SINANAMAZ: örneklem döneminde seriler yukarı eğilimliyse kalıp sonrası
    yukarı payı da yukarı çıkar ve kalıp haksız yere yön veriyor görünür.
    Kıyas ölçütü, AYNI braketin (son n barın tepesi/dibi) kalıp OLMAYAN
    barlara uygulanmış hâlidir; ancak o ölçüldükten sonra kalıba ait bir
    fark iddia edilebilir.

    Braket genişliği de eşleşmeli: 'iki stop da aynı barda' doğal olarak
    braket genişledikçe seyrelir, o yüzden n=2 kalıpları n=2 tabanla,
    n=3 kalıpları n=3 tabanla kıyaslanır — karışık kıyas, braket
    genişliğinin etkisini kalıba yazar.
    """
    def coz(s, i, n):
        tepe, dip = max(s.h[i - n + 1: i + 1]), min(s.l[i - n + 1: i + 1])
        for j in range(i + 1, min(i + 1 + ufuk, len(s))):
            ust, alt = s.h[j] >= tepe, s.l[j] <= dip
            if ust and alt:
                return "ikisi"
            if ust:
                return "yukari"
            if alt:
                return "asagi"
        return "yok"

    bos = lambda: {"yukari": 0, "asagi": 0, "ikisi": 0, "yok": 0}        # noqa: E731
    kalip = {2: bos(), 3: bos()}
    taban = {2: bos(), 3: bos()}
    for k in kay.values():
        s = k.seri
        fp = R.FiyatPaneli(s)
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(s)):
            km = fp.kirilim_modu(i)
            if km is not None:
                n = 3 if km["kalip"] in ("iii", "ioi", "oio") else 2
                kalip[n][coz(s, i, n)] += 1
            else:
                for n in (2, 3):
                    taban[n][coz(s, i, n)] += 1
    return {"kalip": kalip, "taban": taban, "ufuk": ufuk}


def _iki_oran_p(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float, float]:
    """İki oran için havuzlanmış z ve iki yönlü p. (p1, p2, p_degeri)"""
    p1, p2 = x1 / n1, x2 / n2
    hav = (x1 + x2) / (n1 + n2)
    if hav in (0.0, 1.0):
        return p1, p2, float("nan")
    z = (p1 - p2) / math.sqrt(hav * (1 - hav) * (1 / n1 + 1 / n2))
    return p1, p2, math.erfc(abs(z) / math.sqrt(2))


def sekil_yon_bilinmez(kay: dict, no: str) -> Path:
    """'YÖN BİLİNMEZ' ÖLÇÜLDÜ — ve taban oran olmadan ters sonuç çıkıyordu.

    Kalıp barlarında yukarı payı %58 çıkıyor ve tek başına bakıldığında
    yazı-turadan ayrışıyor (binom p = 0,021). Ama AYNI braketin kalıp
    olmayan barlardaki tabanı da %54 — yani sayının neredeyse tamamı
    örneklemin kendi yukarı eğilimi. Eşleşmiş kıyasla fark ayırt
    edilemiyor ve ders doğrulanıyor.

    Ayırt edilen tek şey kuralın EN PAHALI hâli: iki stopun aynı barda
    tetiklenmesi kalıplarda tabanın iki–üç katı.
    """
    o = _kirilim_olcusu(kay)
    et, kal, tab, notlar, yon_p = [], [], [], [], []
    for n, ad in ((2, "ii · oo<br>(2 barlık braket)"), (3, "iii · ioi · oio<br>(3 barlık braket)")):
        kd, td = o["kalip"][n], o["taban"][n]
        for olcu, baslik in (("yon", "kırılım YUKARI"), ("ikisi", "iki stop da AYNI barda")):
            if olcu == "yon":
                x1, m1 = kd["yukari"], kd["yukari"] + kd["asagi"]
                x2, m2 = td["yukari"], td["yukari"] + td["asagi"]
            else:
                x1, m1 = kd["ikisi"], sum(kd.values())
                x2, m2 = td["ikisi"], sum(td.values())
            p1, p2, pd = _iki_oran_p(x1, m1, x2, m2)
            et.append(f"{baslik}<br>{ad}")
            kal.append(100 * p1)
            tab.append(100 * p2)
            # Farkın birimi PUAN'dır, yüzde değil: %58'den %54'e inen iki oranın
            # farkı 4 puandır ve "%4" yazmak başka bir büyüklüğü adlandırır.
            notlar.append(f"fark {B.sayi(100 * (p1 - p2), 1, isaret=True)} puan · "
                          f"p = {B.sayi(pd, 3)}" if pd == pd else "p ölçülemedi")
            if olcu == "yon":
                yon_p.append(pd)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=et, y=kal, name="kalıp barları", marker=dict(color=CLARET),
                         text=[B.yuzde(v, 1) for v in kal], textposition="outside",
                         textfont=dict(size=11), hoverinfo="skip"))
    fig.add_trace(go.Bar(x=et, y=tab, name="aynı braket, kalıp OLMAYAN barlar (taban oran)",
                         marker=dict(color=GRI), text=[B.yuzde(v, 1) for v in tab],
                         textposition="outside", textfont=dict(size=11), hoverinfo="skip"))
    for i, nt in enumerate(notlar):
        fig.add_annotation(x=i, y=max(kal[i], tab[i]) + 9, text=nt, showarrow=False,
                           font=dict(size=10, color=MUREKKEP), yanchor="bottom")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="oluşumların yüzdesi", range=[0, 78])
    fig.update_xaxes(tickfont=dict(size=10))
    kd2, kd3 = o["kalip"][2], o["kalip"][3]
    nk = sum(kd2.values()) + sum(kd3.values())
    _duzen(fig, f"Şekil {no} · 'Yön bilinmez' ölçüldü — ve taban oran olmadan TERS sonuç çıkıyor",
           f"Kalıp sonrası {o['ufuk']} bar içinde hangi stopun önce tetiklendiği, {nk} oluşumda. "
           "Yalnız sol çubuklara bakan biri 'kalıp yukarı çalışıyor' der; oysa AYNI braket kalıp "
           "olmayan barlara kurulduğunda da yukarı payı benzer çıkıyor — fark ayırt edilemiyor "
           f"(p = {B.sayi(yon_p[0], 2)} ve {B.sayi(yon_p[1], 2)}), yani ders haklı. Ayırt edilen "
           "tek şey kuralın en pahalı hâli: iki stopun aynı barda tetiklenmesi kalıplarda "
           "tabanın iki–üç katı", 560)
    return _yaz(fig, f"{no}_yon_bilinmez.html")


NITELIK_AD = {
    "n1": "açılış/kapanış yönü",
    "n2": "kuyruk geometrisi",
    "n3": "örtüşme sınırı",
    "n5": "yeni uç",
}


def sekil_kalite_skoru(kay: dict, no: str) -> Path:
    """KALİTE SKORU BİR BARIN BİÇİMİDİR — 4/4 · 3/4 · 2/4 yan yana.

    Sayfa "3/4 gördüğünüzde ipucundan hangi niteliğin düştüğüne bakın" diyor
    ama düşen niteliğin NASIL göründüğünü göstermiyor. Üç panel AYNI seansın
    ardışık üç barı: aynı piyasa, aynı saat, üç farklı skor — yani fark
    bağlamdan değil BARIN BİÇİMİNDEN doğuyor ve ancak yan yana görülür.
    """
    # Barlar ELLE değil ÖLÇÜMLE seçilir: aynı SEANSTA 4/4, 3/4 ve 2/4 veren
    # üçlü aranır. Elle seçilmiş bir indis veri yenilendiğinde sessizce başka
    # bir barı gösterir; arama, eşleşme kalmazsa ADIYLA düşer.
    ISTENEN = (4, 3, 2)
    en_iyi = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        gun: dict[str, dict[int, list[int]]] = {}
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(s)):
            for boga in (True, False):
                if not fp.donus_bari(i, boga):
                    continue
                d = gun.setdefault(f"{s.zaman[i][:10]}|{int(boga)}", {})
                d.setdefault(fp.kalite(i, boga), []).append(i)
        for anahtar, skor in gun.items():
            if not all(x in skor for x in ISTENEN):
                continue
            sec = [skor[x][0] for x in ISTENEN]
            yayilim = max(sec) - min(sec)
            if en_iyi is None or yayilim < en_iyi[0]:
                en_iyi = (yayilim, ank, anahtar.endswith("|1"), sec)
    if en_iyi is None:
        raise SystemExit("ENGEL · aynı seansta 4/4 · 3/4 · 2/4 veren üçlü yok — "
                         "örnek ölçüyle yenilenmeli")
    _, ANK, BOGA, SEC = en_iyi
    s = kay[ANK].seri
    fp = R.FiyatPaneli(s)
    paneller = []
    for i in SEC:
        n = fp.nitelikler(i, BOGA)
        k = sum(n.values())
        dusen = [NITELIK_AD[a] for a, v in n.items() if not v]
        # Barın SINIFI ile SKORU ayrı şeylerdir; ikisi de yazılır.
        paneller.append(dict(
            etiket=f"{k}/4 — " + ("dördü birden tutuyor" if k == 4
                                  else "düşen: " + " · ".join(dusen)),
            seri=ANK, bas=i - 7, son=i + 4, vurgu=[i],
            isaret=[(i, f"{k}/4", True, MUREKKEP if k == 4 else CLARET)],
            not_=f"{_an(s.zaman[i])} · {fp.sinif(i)} · gövde/menzil "
                 f"{B.sayi(fp.govde_orani(i), 2)} · örtüşme "
                 f"{B.yuzde(100 * fp.ortusme(i), 0)}",
        ))
    ad = O.ENSTRUMAN_AD.get(ANK.rsplit("-", 1)[0], ANK)
    skorlar = " · ".join(f"{sum(fp.nitelikler(i, BOGA).values())}/4" for i in SEC)
    # Skorun HÜKÜM OLMADIĞI sayfanın kendi ölçümü; burada tekrarlanmaz.
    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Kalite skoru barın biçimidir: {skorlar}",
        f"Üçü de {ad} serisinin {_an(s.zaman[SEC[0]])[:10]} seansından, "
        f"{'boğa' if BOGA else 'ayı'} kurulumu olarak puanlandı — aynı piyasa, aynı gün, üç farklı "
        "skor. Panel başlığı hangi niteliğin DÜŞTÜĞÜNÜ yazar; skorun kendisi bir işlem izni "
        "değildir, dördü de tutan bir bar always-in yönüne ters düşüyorsa indikatör etiketi basmaz",
        paneller, sutun=3, panel_yuk=270)
    return _yaz(fig, f"{no}_kalite_skoru.html")


def sekil_always_in_donusu(kay: dict, no: str) -> Path:
    """ALWAYS-IN DÖNÜŞÜ — üçgen neden BU barda, bir önceki güçlü barda değil.

    Kural üç parçalı (iki güçlü bar + doğru kapanışlı takip barı) ve sayfada
    yalnız düz yazı. Üç panel kuralın hangi parçasının nerede düştüğünü
    gösterir; kuralın MALİYETİ de ölçülü: geç ve seyrek işaretler.
    """
    # Seri ELLE seçilmez: kuralın üç hâlini birden taşıyan seri ARANIR.
    # Elle seçim, veri yenilendiğinde sessizce başka bir olayı gösterir.
    secim = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        yon, donus, onaysiz = fp.always_in()
        # Sıfırdan KURULMA ile DÖNÜŞ aynı şey değil: `donus` ilk kez yön
        # alındığı barı da taşır ve ona "döndü" demek olmamış bir olay
        # anlatmaktır. 13 serinin 13'ünde sıfırdan kurulma var, gerçek
        # dönüş yalnız 6 seride.
        gercek = [j for j in donus if yon[j - 1] != 0]
        if not gercek:
            continue
        d = gercek[0]
        uzak = [j for j in onaysiz if abs(j - d) > 6]
        if not uzak:
            continue
        kurulu = set(donus) | set(onaysiz)
        tek = next((i for i in range(int(R.SABIT_FH["maUzunluk"]) + 2, len(s))
                    if not any(abs(i - j) <= 4 for j in kurulu)
                    and (fp.guclu_boga(i) or fp.guclu_ayi(i))
                    and not (fp.guclu_boga(i - 1) or fp.guclu_ayi(i - 1))), None)
        if tek is None:
            continue
        secim = (ank, d, uzak[0], tek)
        break
    if secim is None:
        raise SystemExit("ENGEL · kuralın üç hâlini birden taşıyan seri yok — "
                         "örnek ölçüyle yenilenmeli")
    ANK, d, o1, tek = secim
    s = kay[ANK].seri
    fp = R.FiyatPaneli(s)
    ad = O.ENSTRUMAN_AD.get(ANK.rsplit("-", 1)[0], ANK)
    paneller = [
        dict(etiket="① Onaylandı — iki güçlü bar, takip barı doğru kapandı",
             seri=ANK, bas=d - 8, son=d + 5, vurgu=[d - 2, d - 1, d],
             isaret=[(d, "always-in DÖNDÜ", True, MUREKKEP)],
             not_=f"{_an(s.zaman[d])} · işaret ancak dizinin ÜÇÜNCÜ barında basılıyor"),
        dict(etiket="② Dizi kuruldu, takip barı ELEDİ",
             seri=ANK, bas=o1 - 8, son=o1 + 5, vurgu=[o1 - 2, o1 - 1, o1],
             isaret=[(o1, "onay YOK", True, CLARET)],
             not_=f"{_an(s.zaman[o1])} · iki güçlü bar var, üçüncü barın kapanışı tutmuyor"),
        dict(etiket="③ Tek güçlü bar — dizi hiç kurulmuyor",
             seri=ANK, bas=tek - 8, son=tek + 5, vurgu=[tek],
             isaret=[(tek, "dizi yok", True, GRI)],
             not_=f"{_an(s.zaman[tek])} · güçlü bar tek başına always-in'i çevirmez"),
    ]
    # Seçiciliğin ölçüsü: OLAY ile DÖNÜŞ ayrı sayılır, çünkü her serinin ilk
    # olayı sıfırdan kurulmadır ve onu dönüş saymak sayıyı iki katına çıkarır.
    n_olay = n_donus = n_onaysiz = n_bar = 0
    for k in kay.values():
        y, dn, on = R.FiyatPaneli(k.seri).always_in()
        n_olay += len(dn)
        n_donus += sum(1 for j in dn if y[j - 1] != 0)
        n_onaysiz += len(on)
        n_bar += len(k.seri)
    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Always-in dönüşü: üçgen neden bu barda basıldı",
        "Kural üç parçalı — ardışık iki güçlü trend barı, sonra kapanışı diziyi onaylayan bir takip "
        f"barı. Üç panel de {ad} serisinden, yani fark enstrümandan değil kuralın hangi parçasının "
        f"düştüğünden geliyor. Seçicilik ölçülü: {B.sayi(n_bar, 0)} barda {n_olay} olay, bunların "
        f"{n_donus} tanesi gerçek YÖN DEĞİŞİMİ (kalanı serinin ilk kez yön alması), ve "
        f"{n_onaysiz} dizi "
        "takip barında elendi",
        paneller, sutun=3, panel_yuk=270)
    return _yaz(fig, f"{no}_always_in_donusu.html")


def sekil_gap_yon_filtresi(kay: dict, no: str) -> Path:
    """GAP SAYACI BİR SİNYAL DEĞİL SAYAÇTIR — aynı eşik, ters iki sonuç.

    Sayfa "gap sayacı 20'yi geçince ⚑ çıkar" diyor ve dersin okumasını
    aktarıyor; okur ⚑'nin bir sayaç mı sinyal mi olduğunu metinden ayırt
    edemiyor. İki gerçek örnek bunu çözüyor, üçüncü panel yön filtresinin
    bir YASAK olduğunu gösteriyor.
    """
    ESIK = int(R.SABIT_FH["gapEsik"])
    aday = []
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        g = fp.gap_sayaci()
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(s) - 12):
            if g[i] == ESIK:                       # eşiğin TAM aşıldığı bar
                # Eşikten sonra trend sürdü mü, yoksa ortalamaya mı döndü?
                zirve = max(g[i:min(i + 25, len(s))])
                aday.append((ank, i, zirve))
    if len(aday) < 2:
        raise SystemExit(f"ENGEL · gap eşiği ({ESIK}) yeterince örnek vermiyor: {len(aday)}")
    aday.sort(key=lambda a: -a[2])
    surdu = aday[0]                                # en uzun koşu
    kisa = min(aday, key=lambda a: a[2])           # eşikte kalıp hemen dönen
    paneller = []
    for et, (ank, i, zirve) in (("A · eşik aşıldı, koşu SÜRDÜ", surdu),
                                ("B · aynı eşik, ortalamaya HEMEN dönüldü", kisa)):
        s = kay[ank].seri
        ad = O.ENSTRUMAN_AD.get(ank.rsplit("-", 1)[0], ank)
        paneller.append(dict(
            etiket=f"{et} (tepe {zirve})", seri=ank, bas=i - 6, son=min(i + 16, len(s)),
            vurgu=[i], ema=True, isaret=[(i, f"gap {ESIK}", True, CLARET)],
            not_=f"{ad} · {_an(s.zaman[i])} — sayaç aynı eşikte, sonrası başka"))
    # Üçüncü panel: yön filtresinin YASAK koyduğu bir pencere.
    yasak = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 12, len(s) - 4):
            f = fp.yon_filtresi(i)
            if f != "serbest" and fp.yon_filtresi(i - 1) == "serbest":
                yasak = (ank, i, f)
                break
        if yasak:
            break
    if yasak is None:
        raise SystemExit("ENGEL · yön filtresinin kapandığı bar bulunamadı")
    ank, i, f = yasak
    s = kay[ank].seri
    fp = R.FiyatPaneli(s)
    pen = int(R.SABIT_FH["yonPencere"])
    # Yasağı doğuran taraf hangisiyse O sayılır: "yalnız SAT" filtresi
    # ortalamanın ALTINDA kapanan barlardan doğar; üstteki sayıyı yazmak
    # okura kuralın tersini anlatır.
    sat = f == "yalnız SAT"
    yan = "altında" if sat else "üstünde"
    ust = sum(1 for j in range(i - pen + 1, i + 1)
              if (s.c[j] < fp.ema[j] if sat else s.c[j] > fp.ema[j]))
    paneller.append(dict(
        etiket=f"C · yön filtresi KAPANDI — {f}", seri=ank, bas=i - pen - 7, son=i + 5,
        vurgu=list(range(i - pen + 1, i + 1)), ema=True,
        isaret=[(i, f, True, CLARET)],
        not_=f"{O.ENSTRUMAN_AD.get(ank.rsplit('-', 1)[0], ank)} · {_an(s.zaman[i])} — "
             f"son {pen} barın {ust} tanesi ortalamanın {yan} kapandı"))
    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Gap sayacı bir sinyal değil sayaçtır; yön filtresi bir yasaktır",
        f"Sol iki panel AYNI eşikte ({ESIK} bar ortalamaya dokunmadı) ve ters sonuç veriyor — sayaç "
        "ne olacağını söylemez, ortalamadan ne kadar uzaklaşıldığını sayar. Sağdaki panel yön "
        "filtresinin kapandığı bar: taralı pencerenin çoğu ortalamanın bir yanında kapandığı için "
        "indikatör KARŞI yönde etiket basmayı bırakır",
        paneller, sutun=3, panel_yuk=270)
    return _yaz(fig, f"{no}_gap_yon_filtresi.html")


def _dort_satir(fp, yon, i: int) -> tuple:
    """Fiyat panelinin OKUMA SIRASI bölümü — kutuda okura görünen dört satır.

    Kutunun kendi metnini kurar, çünkü figürün iddiası tam olarak budur:
    iki barda bu DÖRT satır birebir aynı."""
    kb, ka = fp.kalite(i, True), fp.kalite(i, False)
    f = fp.yon_filtresi(i)
    kur_b = fp.donus_bari(i, True) and kb > 0 and f != "yalnız SAT"
    kur_a = fp.donus_bari(i, False) and ka > 0 and f != "yalnız AL"
    if kur_b and kur_a:
        kur = f"iki yönlü — {kb}/4 boğa · {ka}/4 ayı"
    elif kur_b:
        kur = f"{kb}/4 boğa"
    elif kur_a:
        kur = f"{ka}/4 ayı"
    else:
        kur = "kurulum yok"
    hizali = (kur_b and yon[i] == 1) or (kur_a and yon[i] == -1)
    ek = " ✓ yönle hizalı" if hizali else ("  ⚠ yönle hizasız" if (kur_b or kur_a) else "")
    ai = "LONG" if yon[i] == 1 else "SHORT" if yon[i] == -1 else "henüz belirsiz"
    return (ai, f, kur + ek)


def sekil_ayni_kurulum(kay: dict, no: str) -> Path:
    """AYNI KURULUM, İKİ REJİM — fiyat paneli bu iki barı AYIRAMIYOR.

    Dersin en pahalı hatası "doğru kurulumu yanlış günde almak" ve sayfa bunu
    bir CÜMLE olarak söylüyor. Gösterilebilir: aynı seride, aynı zaman
    diliminde, fiyat panelinin DÖRT satırı da birebir aynı olan iki gerçek
    bar var; ayrışan tek şey alt panel. Okur "neden alt panele bakayım"
    sorusunun cevabını ancak ikisini yan yana görünce alır.

    Çift ARANIR, elle yazılmaz: veri yenilendiğinde başka bir çift geçerli
    olabilir ve elle seçilmiş bir indis sessizce başka bir hikâye anlatır.
    """
    aday = []
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        rp = R.RejimPanosu(s)
        yon, _, _ = fp.always_in()
        kova: dict[tuple, list] = {}
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(s)):
            o = rp.olcu(i)
            if o is None:
                continue
            satir = _dort_satir(fp, yon, i)
            if satir[2] == "kurulum yok":
                continue          # kurulumu olmayan bar bu soruyu sormaz
            kova.setdefault(satir, []).append((i, o["n"]))
        for satir, v in kova.items():
            bant = [x for x in v if x[1] >= 4]
            trend = [x for x in v if x[1] <= 1]
            if bant and trend:
                # Hizalı kurulum daha güçlü bir örnek: okur "zaten hizasızdı"
                # diyip geçemez, itiraz YALNIZCA rejimden gelir.
                aday.append((0 if "hizalı" in satir[2] else 1,
                             ank, satir, bant[0], trend[0]))
    if not aday:
        raise SystemExit("ENGEL · dört satırı aynı, rejimi ZIT olan bar çifti yok — "
                         "figürün iddiası bu veriyle kurulamıyor")
    aday.sort(key=lambda a: (a[0], a[1]))
    _, ANK, satir, (i_bant, n_bant), (i_trend, n_trend) = aday[0]
    s = kay[ANK].seri
    ad = O.ENSTRUMAN_AD.get(ANK.rsplit("-", 1)[0], ANK)
    w = int(R.SABIT_RP["pencere"])
    paneller = [
        dict(etiket=f"Alt panel: trend ({n_trend}/5) — geri çekilme kurulumları geçerli",
             seri=ANK, bas=i_trend - w + 1, son=i_trend + 4, vurgu=[i_trend], ema=True,
             isaret=[(i_trend, "trend", True, MAVI)],
             not_=f"{_an(s.zaman[i_trend])} · fade edilmez, bar sayımı geçerli"),
        dict(etiket=f"Alt panel: BANT ({n_bant}/5) — bar sayımına dayalı stop girişi YOK",
             seri=ANK, bas=i_bant - w + 1, son=i_bant + 4, vurgu=[i_bant], ema=True,
             isaret=[(i_bant, "BANT", True, CLARET)],
             not_=f"{_an(s.zaman[i_bant])} · bandın içinde dönüş barı aranmaz"),
    ]
    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Aynı kurulum, iki rejim: fiyat paneli bu iki barı AYIRAMIYOR",
        f"İki bar da {ad} serisinden ve fiyat panelinin DÖRT satırı birebir aynı: "
        f"always-in {satir[0]} · yön filtresi \"{satir[1]}\" · kurulum \"{satir[2]}\". "
        "Üst panele bakan biri ikisini ayırt edemez. Ayrışan tek şey alt panelin hükmü — "
        "ve ders bu iki barda ZIT davranmayı söylüyor. \"Doğru kurulumu yanlış günde almak\" "
        "dersin en pahalı hatasıysa, alt panel onu önleyen tek katmandır. Paneller "
        f"hükmün ÖLÇÜLDÜĞÜ {w} barlık pencereyi gösteriyor — taralı bar çıpa; dar bir "
        "pencere hükmün kanıtını figürün dışında bırakırdı",
        paneller, sutun=2, panel_yuk=300)
    return _yaz(fig, f"{no}_ayni_kurulum.html")


def sekil_bar_sozlugu(kay: dict, no: str) -> Path:
    """BAR SÖZLÜĞÜ — dört sınıf, ve sınıfın AYIRT EDEMEDİĞİ şey.

    Bölüm okura üç sayı veriyor (gövde menzilin %50'si · %75'i · %10'u) ve tek
    bir resim vermiyor; yani eşiği gerçek bir bara uygulanmış hâlde hiç
    görmüyor. İkinci panel sınıfın SINIRINI gösteriyor: aynı sınıf, aynı gövde
    oranı, zıt kapanış yeri — etiket bu iki barı ayırt edemiyor.
    """
    # ── Panel ①: DÖRT SINIF TEK PENCEREDE ────────────────────────────────
    # Tek pencere şart: sınıflar ayrı ayrı gösterilse okur ölçek farkını
    # sınıf farkı sanardı. Aynı pencere, aynı fiyat ekseni, aynı enstrüman.
    SINIFLAR = ("güçlü trend", "trend", "ara", "doji")
    medyan: dict[str, float] = {}
    havuz: dict[str, list[float]] = {s: [] for s in SINIFLAR}
    for k in kay.values():
        fp = R.FiyatPaneli(k.seri)
        for i in range(int(R.SABIT_FH["maUzunluk"]), len(k.seri)):
            s_ad = fp.sinif(i)
            if s_ad in havuz:
                havuz[s_ad].append(fp.govde_orani(i))
    for s_ad, v in havuz.items():
        medyan[s_ad] = sorted(v)[len(v) // 2] if v else float("nan")

    PENCERE = 24
    en_iyi = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        bas0 = int(R.SABIT_FH["maUzunluk"])
        for b in range(bas0, len(s) - PENCERE):
            pen = range(b, b + PENCERE)
            temsil: dict[str, tuple[float, int]] = {}
            for i in pen:
                s_ad = fp.sinif(i)
                if s_ad not in SINIFLAR:
                    continue
                d = abs(fp.govde_orani(i) - medyan[s_ad])
                if s_ad not in temsil or d < temsil[s_ad][0]:
                    temsil[s_ad] = (d, i)
            if len(temsil) < 4:
                continue
            # Sınıfının MEDYANINA en yakın dörtlüyü taşıyan pencere: seçilen
            # barlar sınıfının sınırında değil ORTASINDA olsun, yoksa okur
            # eşiği değil bir istisnayı öğrenir.
            skor = sum(d for d, _ in temsil.values())
            if en_iyi is None or skor < en_iyi[0]:
                en_iyi = (skor, ank, b, {a: i for a, (_, i) in temsil.items()})
    if en_iyi is None:
        raise SystemExit("ENGEL · dört sınıfı birden taşıyan pencere yok — "
                         "sözlük bu veriyle tek pencerede kurulamıyor")
    _, ANK1, b1, sec = en_iyi
    s1 = kay[ANK1].seri
    fp1 = R.FiyatPaneli(s1)
    isaret1 = []
    for s_ad in SINIFLAR:
        i = sec[s_ad]
        renk = MAVI if s1.c[i] > s1.o[i] else CLARET if s1.c[i] < s1.o[i] else GRI
        isaret1.append((i, f"{s_ad}<br>{B.sayi(fp1.govde_orani(i), 2)}", True, renk))

    # ── Panel ②: AYNI SINIF, AYNI GÖVDE, ZIT KAPANIŞ ────────────────────
    cift = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        menziller = sorted(fp.menzil(i) for i in range(len(s)))
        med_menzil = menziller[len(menziller) // 2]
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 1, len(s)):
            j = i - 1
            if fp.sinif(i) != fp.sinif(j):
                continue
            if (s.c[i] > s.o[i]) != (s.c[j] > s.o[j]):
                continue                      # aynı YÖN: fark yalnız kapanışta olsun
            if abs(fp.govde_orani(i) - fp.govde_orani(j)) > 0.03:
                continue
            fark = abs(fp.kapanis_yeri(i) - fp.kapanis_yeri(j))
            if fark < 0.32 or min(fp.menzil(i), fp.menzil(j)) < med_menzil:
                continue
            if cift is None or fark > cift[0]:
                cift = (fark, ank, j, i)
    if cift is None:
        raise SystemExit("ENGEL · aynı sınıf + aynı gövde oranı + zıt kapanış yeri "
                         "taşıyan bitişik çift yok")
    _, ANK2, j2, i2 = cift
    s2 = kay[ANK2].seri
    fp2 = R.FiyatPaneli(s2)
    isaret2 = [(x, f"kapanış %{B.sayi(100 * fp2.kapanis_yeri(x), 0)}",
                fp2.kapanis_yeri(x) >= 0.5, CLARET if fp2.kapanis_yeri(x) < 0.5 else MAVI)
               for x in (j2, i2)]

    ad1 = O.ENSTRUMAN_AD.get(ANK1.rsplit("-", 1)[0], ANK1)
    ad2 = O.ENSTRUMAN_AD.get(ANK2.rsplit("-", 1)[0], ANK2)
    paneller = [
        dict(etiket="① Dört sınıf TEK pencerede — eşik barın kendi oranıdır",
             seri=ANK1, bas=b1, son=b1 + PENCERE, vurgu=sorted(sec.values()),
             isaret=isaret1,
             not_=f"{ad1} · {_an(s1.zaman[b1])} → {_an(s1.zaman[b1 + PENCERE - 1])} — "
                  "dördü de aynı fiyat ekseninde"),
        dict(etiket="② Aynı sınıf, aynı gövde oranı — ZIT kapanış yeri",
             seri=ANK2, bas=i2 - 9, son=i2 + 4, vurgu=[j2, i2], isaret=isaret2,
             not_=f"{ad2} · {_an(s2.zaman[i2])} — sınıf ikisine de "
                  f"'{fp2.sinif(i2)}' diyor, gövde oranı farkı "
                  f"{B.sayi(abs(fp2.govde_orani(i2) - fp2.govde_orani(j2)), 3)}"),
    ]
    esik = R.SABIT_FH
    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Bar sözlüğü: dört sınıf, ve sınıfın ayırt EDEMEDİĞİ şey",
        f"Sınıfı belirleyen barın büyüklüğü değil GÖVDE/MENZİL oranı: güçlü trend "
        f"≥ {B.sayi(esik['gucluGovde'], 2)} · trend ≥ {B.sayi(esik['trendGovde'], 2)} · "
        f"doji ≤ {B.sayi(esik['dojiGovde'], 2)}, arası 'ara'. Soldaki dört bar sınıfının "
        "MEDYANINA en yakın olanlar, yani sınırda değil ortasında. Sağdaki panel sınıfın "
        "sınırını gösteriyor: iki bar aynı etiketi ve neredeyse aynı gövde oranını "
        "taşıyor, ayıran tek şey kapanışın menzil içindeki yeri — sınıf onları ayırt "
        "edemiyor, o yüzden indikatör ikisini AYRI satırda yazar",
        paneller, sutun=2, panel_yuk=300)
    return _yaz(fig, f"{no}_bar_sozlugu.html")


def sekil_bar_sayimi(kay: dict, no: str) -> Path:
    """GERİ ÇEKİLMEYİ SAYMAK — ve sayacın nerede SIFIRLANDIĞI.

    Sayım bir dizi değil bir DURUM (Pine'da `var int hSayac`) ve bir durumun
    sıfırlanması düz yazıyla anlatılamaz; barların üstünde görünür. Cevabın
    yarısı sayının kendisi değil, sayacın ne zaman sıfırlandığıdır.
    """
    # Panel A: TAM BİR TUR — H1→H4 ve ardından yeni bacak zirvesiyle sıfır.
    # Panel B: H4 bir TAVAN — sayaç 4'ün üstüne çıkar, etiket H4'te kalır.
    A = B_ = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        et = fp.bar_sayimi()
        sayac = fp.bar_sayaci()
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 6, len(s) - 3):
            if et[i] != "H4":
                continue
            # geriye doğru H3-H2-H1 var mı
            gerek = ["H3", "H2", "H1"]
            yer, bul = i - 1, []
            while yer > 0 and gerek:
                if et[yer] == gerek[0]:
                    bul.append(yer)
                    gerek.pop(0)
                elif et[yer] in ("H4", "H3", "H2", "H1"):
                    break
                yer -= 1
            if gerek:
                continue
            h1 = bul[-1]
            # A: bu turdan SONRA sayaç sıfırlanıyor mu (yeni bacak zirvesi)
            sifir = next((j for j in range(i + 1, min(i + 8, len(s)))
                          if sayac[j] == "H0"), None)
            if A is None and sifir is not None and h1 - 4 >= 0:
                A = (ank, h1, i, sifir, bul[::-1])
            # B: aynı turdan sonra H4 ETİKETİ tekrar ediyor mu (sayaç >4)
            tekrar = [j for j in range(i + 1, min(i + 10, len(s))) if et[j] == "H4"]
            if B_ is None and len(tekrar) >= 2:
                B_ = (ank, h1, i, tekrar)
        if A and B_:
            break
    if A is None:
        raise SystemExit("ENGEL · H1→H4 turu ve ardından sıfırlanma taşıyan pencere yok")
    if B_ is None:
        raise SystemExit("ENGEL · H4 etiketinin tekrar ettiği (sayaç > 4) pencere yok")

    paneller = []
    ankA, h1A, h4A, sifA, tur = A
    sA = kay[ankA].seri
    fpA = R.FiyatPaneli(sA)
    etA = fpA.bar_sayimi()
    isA = [(j, etA[j], True, MAVI) for j in tur + [h4A]]
    isA.append((sifA, "YENİ BACAK ZİRVESİ → sayaç SIFIR", True, CLARET))
    paneller.append(dict(
        etiket="A · Tam bir tur: H1 → H2 → H3 → H4, sonra sıfır",
        seri=ankA, bas=h1A - 5, son=min(sifA + 4, len(sA)), vurgu=[sifA], isaret=isA,
        not_=f"{O.ENSTRUMAN_AD.get(ankA.rsplit('-', 1)[0], ankA)} · "
             f"{_an(sA.zaman[h4A])} — sayacı sıfırlayan şey yeni bir bacak zirvesidir"))

    ankB, h1B, h4B, tekB = B_
    sB = kay[ankB].seri
    fpB = R.FiyatPaneli(sB)
    etB, hamB = fpB.bar_sayimi(), fpB.bar_sayaci_ham()
    isB = [(h4B, f"H4 <span style='color:{GRI}'>(sayaç {abs(hamB[h4B])})</span>", True, MAVI)]
    for j in tekB:
        isB.append((j, f"H4 <span style='color:{GRI}'>(sayaç {abs(hamB[j])})</span>",
                    True, MAVI))
    paneller.append(dict(
        etiket="B · H4 bir TAVAN — sayının sonu değil",
        seri=ankB, bas=h1B - 4, son=min(tekB[-1] + 4, len(sB)), vurgu=tekB, isaret=isB,
        not_=f"{O.ENSTRUMAN_AD.get(ankB.rsplit('-', 1)[0], ankB)} · "
             f"{_an(sB.zaman[h4B])} — etiket H4'te durur, iç sayaç saymaya devam eder"))

    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Geri çekilmeyi saymak: H1'den H4'e, ve sayacın nerede sıfırlandığı",
        "Sayım bir dizi değil bir DURUMDUR: etiket yalnız bar bir ÖNCEKİNİN zirvesini "
        "geçtiğinde basılır, eşitlik saymaz, ve yeni bir bacak zirvesi sayacı SIFIRLAR. "
        "Sağdaki panel ikinci bir inceliği gösteriyor — H4 bir TAVAN: etiket dörtte durur "
        "ama iç sayaç saymaya devam eder, yani 'arka arkaya iki H4' art arda iki bar demek "
        "değildir. İndikatörün durum kutusu etiketi değil SAYACI yazar",
        paneller, sutun=2, panel_yuk=300)
    return _yaz(fig, f"{no}_bar_sayimi.html")


def sekil_donus_kaliplari(kay: dict, no: str) -> Path:
    """DÖRT KURAL, DÖRT BİÇİM — her panelde eşiğin geçtiği yer görünür.

    Bu dört kural sayfada dört ayrı düz yazı bölümünde duruyor ve dördü de
    tanımı gereği ŞEKİL: "kabaca eşit gövdeler", "neredeyse aynı dipler",
    "orta noktanın ötesinde kapanış", "%75 örtüşme". Her panelde kalıbı bir
    kez SAĞLAYAN ve bir kez SAĞLAMAYAN hâl yan yana.
    """
    paneller = []
    ESIK = R.SABIT_FH["ortusmeEsik"]
    ESIT = R.TANIM["esitGovdeOran"]
    MIKRO_TOL = R.TANIM["mikroTolerans"]

    # ① İKİ BARLIK DÖNÜŞ — "kabaca eşit gövde"
    sec = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 1, len(s) - 3):
            if not fp.iki_barlik_donus(i):
                continue
            g0, g1 = fp.govde(i), fp.govde(i - 1)
            oran = min(g0, g1) / max(g0, g1) if max(g0, g1) > 0 else 0
            # Aynı pencerede kuralın TUTMADIĞI zıt yönlü trend bar çifti
            karsi = next((j for j in range(max(i - 8, 1), min(i + 9, len(s)))
                          if abs(j - i) > 1 and not fp.iki_barlik_donus(j)
                          and (fp.guclu_boga(j) or fp.guclu_ayi(j))
                          and (fp.guclu_boga(j - 1) or fp.guclu_ayi(j - 1))
                          and (s.c[j] > s.o[j]) != (s.c[j - 1] > s.o[j - 1])), None)
            if karsi is None:
                continue
            if sec is None or abs(oran - ESIT) < abs(sec[0] - ESIT):
                sec = (oran, ank, i, karsi)
    if sec is None:
        raise SystemExit("ENGEL · iki barlık dönüş + aynı pencerede karşı örnek yok")
    _, a1, i1, k1 = sec
    s1 = kay[a1].seri
    fp1 = R.FiyatPaneli(s1)
    g0, g1 = fp1.govde(i1), fp1.govde(i1 - 1)
    paneller.append(dict(
        etiket="① İki barlık dönüş — ölçü GÖVDE, kuyruk değil",
        seri=a1, bas=min(i1, k1) - 6, son=max(i1, k1) + 5, vurgu=[i1 - 1, i1],
        cizgi=[(max(s1.h[i1], s1.h[i1 - 1]), MAVI, "dot"),
               (min(s1.l[i1], s1.l[i1 - 1]), CLARET, "dot")],
        isaret=[(i1, fp1.iki_barlik_donus(i1), True, MUREKKEP),
                (k1, "kalıp YOK", True, GRI)],
        not_=f"{O.ENSTRUMAN_AD.get(a1.rsplit('-', 1)[0], a1)} · {_an(s1.zaman[i1])} — "
             f"küçük gövde / büyük gövde = {B.sayi(min(g0, g1) / max(g0, g1), 2)} "
             f"(eşik {B.sayi(ESIT, 2)}); giriş İKİ barın ötesinde"))

    # ② MİKRO ÇİFT — aynı bar çifti bir uçta kalıbı basıyor, öbür uçta basmıyor
    sec2 = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 1, len(s) - 3):
            m = fp.mikro_cift(i)
            if not m:
                continue
            dip_f = abs(s.l[i] - s.l[i - 1])
            tepe_f = abs(s.h[i] - s.h[i - 1])
            menzil = max(fp.menzil(i), 1e-12)
            # En öğretici hâl: bir uç TAM eşit, öbür uç toleransın dışında.
            if "dip" in m:
                yakin, uzak = dip_f / menzil, tepe_f / menzil
            else:
                yakin, uzak = tepe_f / menzil, dip_f / menzil
            # Öğretici hâl uzak ucun toleransı AZ AŞTIĞI yerdir; farkı
            # büyütmek, iki barın neredeyse hiç örtüşmediği dejenere bir
            # örnek bulur ve "tolerans" fikri görünmez olur.
            if uzak <= MIKRO_TOL:
                continue
            if sec2 is None or (uzak - MIKRO_TOL) < sec2[0]:
                sec2 = (uzak - MIKRO_TOL, ank, i, m, dip_f, tepe_f, menzil)
    if sec2 is None:
        raise SystemExit("ENGEL · bir ucu kalıbı basan, öbür ucu basmayan mikro çift yok")
    _, a2, i2, m2, dipf, tepef, men2 = sec2
    s2 = kay[a2].seri
    paneller.append(dict(
        etiket="② Mikro çift — tolerans BİZİM seçtiğimiz sayı",
        seri=a2, bas=i2 - 8, son=i2 + 6, vurgu=[i2 - 1, i2],
        cizgi=[(min(s2.l[i2], s2.l[i2 - 1]), CLARET, "dot"),
               (max(s2.h[i2], s2.h[i2 - 1]), MAVI, "dot")],
        isaret=[(i2, m2, True, MUREKKEP)],
        not_=f"{O.ENSTRUMAN_AD.get(a2.rsplit('-', 1)[0], a2)} · {_an(s2.zaman[i2])} — "
             f"dip farkı menzilin {B.yuzde(100 * dipf / men2, 1)}'i, tepe farkı "
             f"{B.yuzde(100 * tepef / men2, 1)}'i — tolerans "
             f"{B.yuzde(100 * MIKRO_TOL, 0)}: aynı çift bir uçta kalıp, öbüründe değil"))

    # ③ ORTA NOKTA ÖLÇÜTÜ — bitişik iki barda RET ve KABUL
    sec3 = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 1, len(s) - 2):
            for boga in (True, False):
                if fp.orta_nokta_olcutu(i, boga) and not fp.orta_nokta_olcutu(i - 1, boga):
                    pay = abs(s.c[i] - fp.orta_nokta(i - 1))
                    if sec3 is None or pay > sec3[0]:
                        sec3 = (pay, ank, i, boga)
    if sec3 is None:
        raise SystemExit("ENGEL · bitişik iki barda orta nokta ölçütünün ret+kabul hâli yok")
    _, a3, i3, boga3 = sec3
    s3 = kay[a3].seri
    fp3 = R.FiyatPaneli(s3)
    paneller.append(dict(
        etiket="③ Orta nokta ölçütü — ret ve kabul, bitişik iki barda",
        seri=a3, bas=i3 - 8, son=i3 + 5, vurgu=[i3 - 1, i3],
        cizgi=[(fp3.orta_nokta(i3 - 1), MUREKKEP, "dash"),
               (fp3.orta_nokta(i3 - 2), GRI, "dot")],
        isaret=[(i3, "GEÇTİ", True, MAVI if boga3 else CLARET),
                (i3 - 1, "kaldı", False, GRI)],
        not_=f"{O.ENSTRUMAN_AD.get(a3.rsplit('-', 1)[0], a3)} · {_an(s3.zaman[i3])} — "
             f"kesikli çizgi önceki barın ORTA NOKTASI; kapanış onun "
             f"{'üstünde' if boga3 else 'altında'} olmalı"))

    # ④ ÖRTÜŞME — eşiği aşan bar ve aşmayan komşusu
    sec4 = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 1, len(s) - 3):
            if fp.ortusme(i) <= ESIK:
                continue
            komsu = next((j for j in range(i + 1, min(i + 5, len(s)))
                          if fp.ortusme(j) < 0.3), None)
            if komsu is None:
                continue
            # Eşiğin hemen ÜSTÜ: %100 örtüşme kuralı anlatmaz, sınırı anlatan
            # şey eşiği az aşan bardır.
            if sec4 is None or (fp.ortusme(i) - ESIK) < (sec4[0] - ESIK):
                sec4 = (fp.ortusme(i), ank, i, komsu)
    if sec4 is None:
        raise SystemExit("ENGEL · örtüşme eşiğini aşan bar + düşük örtüşmeli komşu yok")
    _, a4, i4, k4 = sec4
    s4 = kay[a4].seri
    fp4 = R.FiyatPaneli(s4)
    paneller.append(dict(
        etiket="④ Örtüşme — tek barı değil İKİ barı okumak",
        seri=a4, bas=i4 - 7, son=k4 + 4, vurgu=[i4],
        cizgi=[(min(s4.h[i4], s4.h[i4 - 1]), MUREKKEP, "dot"),
               (max(s4.l[i4], s4.l[i4 - 1]), MUREKKEP, "dot")],
        isaret=[(i4, f"örtüşme {B.yuzde(100 * fp4.ortusme(i4), 0)}", True, CLARET),
                (k4, f"{B.yuzde(100 * fp4.ortusme(k4), 0)}", True, MAVI)],
        not_=f"{O.ENSTRUMAN_AD.get(a4.rsplit('-', 1)[0], a4)} · {_an(s4.zaman[i4])} — "
             f"eşik {B.yuzde(100 * ESIK, 0)}; aşıldığında bar REDDEDİLMEZ, "
             "iki barlık dönüş okunur"))

    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Dönüş kalıpları: dört kural, dört biçim",
        "Dördü de tanımı gereği ŞEKİL ve sayfada dört ayrı düz yazı bölümünde duruyor: "
        "\"kabaca eşit gövdeler\" · \"neredeyse aynı uçlar\" · \"orta noktanın ötesinde "
        "kapanış\" · \"örtüşme eşiği\". Her panelde ölçülen sayı barın üstünde yazılı, "
        "yani okur eşiğin nerede geçtiğini gözüyle kalibre ediyor. İkinci paneldeki çift "
        "kayda değer: AYNI iki bar bir ucunda kalıbı basıyor, öbür ucunda basmıyor — "
        "tolerans bizim seçtiğimiz bir sayıdır, verinin kendi özelliği değil",
        paneller, sutun=2, panel_yuk=290)
    return _yaz(fig, f"{no}_donus_kaliplari.html")


def sekil_barbwire(kay: dict, no: str) -> Path:
    """BARBWIRE — ölçüsü sayısal, tuzağı görsel.

    Dersin en sinsi hatası: "barbwire içindeki bir dönüş barını gerçek dönüş
    barı sanmak." Dar bantta dönüş barının ters çevirecek BİR ŞEYİ YOKTUR;
    bir doji gibi davranır. Bölüm bugün dersin sayısal ölçütünü aktarıyor ama
    tek bir resim vermiyor.
    """
    # Panel A: barbwire ÜÇLÜSÜNÜN içinde duran bir sinyal barı ve AKIBETİ.
    # Panel B: örtüşme koşulu geçen ama doji olmayan üçlü — ölçü "hayır" diyor.
    A = B_ = None
    for ank, k in kay.items():
        s = k.seri
        fp = R.FiyatPaneli(s)
        rp = R.RejimPanosu(s)
        for i in range(int(R.SABIT_FH["maUzunluk"]) + 2, len(s) - 8):
            bw = rp.barbwire(i)
            orta = i - 1
            if bw["var"]:
                for boga in (True, False):
                    if not (fp.donus_bari(orta, boga) and fp.kalite(orta, boga) >= 3):
                        continue
                    # Sinyalin yönüne göre AKIBET: dönüş barının ucu kırıldı mı?
                    if boga:
                        kirildi = min(s.l[orta + 1:orta + 8]) < s.l[orta]
                        mesafe = s.l[orta] - min(s.l[orta + 1:orta + 8])
                    else:
                        kirildi = max(s.h[orta + 1:orta + 8]) > s.h[orta]
                        mesafe = max(s.h[orta + 1:orta + 8]) - s.h[orta]
                    if A is None and kirildi:
                        A = (ank, i, orta, boga, fp.kalite(orta, boga), bw["oran"], mesafe)
            else:
                # Karşı örnek: örtüşme GEÇİYOR ama doji yok → barbwire değil
                om = s.h[i - 1] - s.l[i - 1]
                if om <= 0:
                    continue
                ko = min(s.h[i - 1], s.h[i - 2]) - max(s.l[i - 1], s.l[i - 2])
                ks = min(s.h[i - 1], s.h[i]) - max(s.l[i - 1], s.l[i])
                gecti = (max(0.0, ko) / om > R.SABIT_RP["bwOrtaPay"]
                         and max(0.0, ks) / om > R.SABIT_RP["bwOrtaPay"])
                if gecti and B_ is None:
                    B_ = (ank, i, i - 1, bw["oran"])
        if A and B_:
            break
    if A is None:
        raise SystemExit("ENGEL · içinde 3/4+ sinyal barı taşıyan ve ucu kırılan "
                         "barbwire üçlüsü yok")
    if B_ is None:
        raise SystemExit("ENGEL · örtüşmesi geçen ama doji taşımayan üçlü yok")

    ankA, iA, ortaA, bogaA, kalA, oranA, mesA = A
    sA = kay[ankA].seri
    fpA = R.FiyatPaneli(sA)
    ankB, iB, ortaB, oranB = B_
    sB = kay[ankB].seri

    n_bw = n_t = 0
    for k in kay.values():
        rp = R.RejimPanosu(k.seri)
        for i in range(2, len(k.seri)):
            n_t += 1
            if rp.barbwire(i)["var"]:
                n_bw += 1

    paneller = [
        dict(etiket=f"A · Barbwire'ın ortasında {kalA}/4 sinyal barı — ve akıbeti",
             seri=ankA, bas=iA - 8, son=min(iA + 9, len(sA)),
             vurgu=[iA - 2, iA - 1, iA],
             cizgi=[(sA.l[ortaA] if bogaA else sA.h[ortaA], CLARET, "dash")],
             isaret=[(ortaA, f"{kalA}/4 {'boğa' if bogaA else 'ayı'} — burada OKUNMAZ",
                      not bogaA, CLARET)],
             not_=f"{O.ENSTRUMAN_AD.get(ankA.rsplit('-', 1)[0], ankA)} · "
                  f"{_an(sA.zaman[ortaA])} — ortadaki barın menzilinin "
                  f"{B.yuzde(100 * oranA, 0)}'i komşularının içinde; dönüş barının ucu "
                  "sonraki barlarda kırıldı"),
        dict(etiket="B · Örtüşme GEÇİYOR ama doji yok — barbwire DEĞİL",
             seri=ankB, bas=iB - 8, son=min(iB + 7, len(sB)),
             vurgu=[iB - 2, iB - 1, iB],
             isaret=[(ortaB, "üçü de doji değil", True, GRI)],
             not_=f"{O.ENSTRUMAN_AD.get(ankB.rsplit('-', 1)[0], ankB)} · "
                  f"{_an(sB.zaman[ortaB])} — üç bar üst üste DURUYOR, ölçü 'hayır' diyor"),
    ]
    fig = _kucuk_coklu(
        kay, f"Şekil {no} · Barbwire: ölçüsü sayısal, tuzağı görsel",
        f"Ölçüt dersten ve SAYISAL: ortadaki barın menzilinin yarısından fazlası HEM önceki "
        f"HEM sonraki barın içindeyse ve üçünden en az biri doji ise barbwire. Ölçüldü: "
        f"{B.sayi(n_t, 0)} barın {B.sayi(n_bw, 0)}'i ({B.yuzde(100 * n_bw / n_t, 1)}). "
        "Soldaki panel dersin en sinsi tuzağı — dar bantta bir dönüş barının ters "
        "çevirecek bir şeyi yoktur, bir doji gibi davranır ve kalite skoru orada okunmaz. "
        "Sağdaki panel ölçünün seçiciliği: üç bar üst üste duruyor, örtüşme koşulu "
        "geçiyor, ama doji şartı tutmadığı için kalıp SAYILMIYOR",
        paneller, sutun=2, panel_yuk=300)
    return _yaz(fig, f"{no}_barbwire.html")


# ŞEKİL NUMARASI BİR KİMLİK DEĞİL, SAYFADAKİ YERDİR. Numara bu listedeki
# sıradan türer; şekil işlevleri kendi numaralarını BİLMEZ, dışarıdan alır.
# Sayfada Şekil 01'den sonra Şekil 08 gelmesi okuru şaşırtır ve bu kusur bir
# kez elle numaralandırıldığı için doğdu: her yeni figür sıranın SONUNA
# numara alıyordu, oysa metnin ORTASINA giriyordu.
SIRA = [
    ("indikator_gorunumu", lambda: sekil_indikator_gorunumu),
    ("bar_sozlugu",        lambda: sekil_bar_sozlugu),
    ("bar_sayimi",         lambda: sekil_bar_sayimi),
    ("kirilim_modu",       lambda: sekil_kirilim_modu),
    ("yon_bilinmez",       lambda: sekil_yon_bilinmez),
    ("donus_kaliplari",    lambda: sekil_donus_kaliplari),
    ("barbwire",           lambda: sekil_barbwire),
    ("cevirme_sayaci",     lambda: sekil_cevirme_sayaci),
    ("ne_beklemeli_siklik", lambda: sekil_ne_beklemeli_siklik),
    ("rejim_dagilimi",     lambda: sekil_rejim_dagilimi),
    ("ayni_kurulum",       lambda: sekil_ayni_kurulum),
    ("always_in_donusu",   lambda: sekil_always_in_donusu),
    ("kalite_skoru",       lambda: sekil_kalite_skoru),
    ("kalite_hizasi",      lambda: sekil_kalite_hizasi),
    ("gap_yon_filtresi",   lambda: sekil_gap_yon_filtresi),
    ("okuma_sirasi",       lambda: sekil_okuma_sirasi),
    ("islem_mekanigi",     lambda: sekil_islem_mekanigi),
]

MDX = SITE / "src" / "content" / "indikatorler" / "brooks-fiyat-hareketi.mdx"


def _no(kok: str) -> str:
    """Bir şeklin numarası — SIRA'daki yerinden. Kardeş şekle atıf veren
    metinler bunu çağırır, sayı YAZMAZ."""
    for k, (ad, _) in enumerate(SIRA, 1):
        if ad == kok:
            return f"{k:02d}"
    raise SystemExit(f"ENGEL · SIRA'da '{kok}' yok — atıf çözülemiyor")


def mdx_sirasi_sina() -> list[str]:
    """SAYFANIN gömme sırası ile SIRA aynı mı — ve `no` yerine mi denk geliyor.

    Sözleşme sayfanın kendisinde: okurun gördüğü sıra numaraların kaynağıdır.
    İki liste elle tutulsaydı bir gün sessizce ayrışır ve okur Şekil 07'yi
    Şekil 11'den sonra görürdü. Ölçüt iki yönlü: SIRA'daki her şekil sayfada
    var mı, sayfadaki her şekil SIRA'da mı.
    """
    import re
    if not MDX.exists():
        return [f"ENGEL · sayfa bulunamadı: {MDX}"]
    metin = MDX.read_text(encoding="utf-8")
    gomme = re.findall(r'src="/indikatorler/(\d\d)_([a-z_]+)\.html"[^>]*?no="(\d\d)"', metin)
    hata = []
    bekle = [(f"{k:02d}", ad) for k, (ad, _) in enumerate(SIRA, 1)]
    if len(gomme) != len(bekle):
        hata.append(f"ENGEL · sayfada {len(gomme)} şekil gömülü, SIRA {len(bekle)} tanım ediyor")
    for k, ((dosya_no, kok, etiket_no), (bek_no, bek_kok)) in enumerate(zip(gomme, bekle), 1):
        if kok != bek_kok:
            hata.append(f"ENGEL · {k}. sırada sayfada '{kok}', SIRA'da '{bek_kok}'")
        if dosya_no != bek_no or etiket_no != bek_no:
            hata.append(f"ENGEL · '{kok}' sayfada dosya {dosya_no} · etiket {etiket_no}, "
                        f"sırası {bek_no}")
    return hata


def main() -> None:
    CIKTI.mkdir(parents=True, exist_ok=True)
    hata = mdx_sirasi_sina()
    if hata:
        raise SystemExit("\n".join(hata))
    kay = _kaynaklar()
    if not kay:
        raise SystemExit("ENGEL · gövde kapısından geçen seri yok")
    for k, (kok, al) in enumerate(SIRA, 1):
        no = f"{k:02d}"
        yol = al()(kay, no)
        durum = plotly_stil.isle(yol)
        print(f"  {yol.name:34s} {durum}")
    # Sıra değiştiğinde eski numaralı dosyalar ARTAKALIR ve sayfa onları
    # çağırmasa da depoda durur; adıyla söylenir, sessizce bırakılmaz.
    gecerli = {f"{k:02d}_{kok}.html" for k, (kok, _) in enumerate(SIRA, 1)}
    artik = sorted(y.name for y in CIKTI.glob("[0-9][0-9]_*.html") if y.name not in gecerli)
    if artik:
        print(f"\n  ! artakalan dosya (sayfa çağırmıyor): {', '.join(artik)}")
    print(f"\n{len(kay)} seri · figürler {CIKTI.relative_to(SITE.parent)} altında")



if __name__ == "__main__":
    main()
