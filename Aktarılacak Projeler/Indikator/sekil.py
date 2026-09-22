#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO · Yapı ve Momentum — sayfa figürleri (Plotly, ev stili).

Her figür `yapi_referans` kurallarını depodaki arşive koşturarak çizilir ya
da `site/src/data/yapi_backtest.json`daki ölçümü basar; elle sayı yazılmaz.
Çıktı `site/public/indikatorler/tto_NN_*.html`; `SIRA` listesi MDX'teki gömme
sırasıdır ve `mdx_sirasi_sina()` ikisini iki yönlü eşler (Brooks kalıbı).

    python3 sekil.py            # hepsini üret
    python3 sekil.py --denetle  # MDX sırası + dosyalar var mı"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
DEPO = KOK.parents[1]
SITE = DEPO / "site"
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(SITE / "tools"))
sys.path.insert(0, str(DEPO))
# plotly yalnız ÇİZİM için gerekir. Yayın kapısı (`dogrula.py` → sayfa sınavı)
# bu modülden yalnız `mdx_sirasi_sina()`yı ister ve yayın koşucusunda plotly
# KURULU DEĞİL — ilk yayın koşusu tam bu satırda düştü (ModuleNotFoundError).
# Kütüphane yoksa çizim yolu adıyla reddedilir, kapı yolu çalışır;
# `duman.py` ⑪ maddesi kapı yolunu plotly'siz koşturarak sınar.
try:
    import plotly.graph_objects as go                            # noqa: E402
    from plotly.subplots import make_subplots                     # noqa: E402
except ImportError:                                              # pragma: no cover
    go = make_subplots = None
import plotly_stil                                               # noqa: E402
import veri                                                      # noqa: E402
import yapi_referans as Y                                        # noqa: E402
import backtest as BT                                            # noqa: E402
from ortak import bicim as B                                     # noqa: E402

CIKTI = SITE / "public" / "indikatorler"
JSON = SITE / "src" / "data" / "yapi_backtest.json"
MDX = SITE / "src" / "content" / "indikatorler" / "tto-yapi-momentum.mdx"

MUREKKEP, CLARET, MAVI, YESIL, ALTIN, GRI, MOR, KAGIT = "#1a1a1a", "#8c2f39", "#2f5d8c", "#3a7d44", "#b8860b", "#8a8a8a", "#6a4c93", "#ffffff"
TF_AD = {"5m": "5 dk", "15m": "15 dk", "1h": "1 sa", "4h": "4 sa", "1d": "günlük"}
PAKET_AD = {"sweep_mss_fvg": "sweep → MSS → FVG", "ob_retest": "OB retest", "prz": "harmonik PRZ",
            "diverjans": "diverjans tablosu", "bos_devam": "BOS devam"}

SIRA = [
    ("tto_01_fiyat_paneli.html", "Fiyat paneli grafikte ne çizer"),
    ("tto_02_momentum_paneli.html", "Alt panel ekranda ne çizer"),
    ("tto_03_okuma_sirasi.html", "Okuma sırası tek bir karar barında"),
    ("tto_04_kurulumlar.html", "Beş kurulum paketi gerçek barlarda"),
    ("tto_05_harmonik_ornek.html", "Harmonik PRZ nasıl kurulur"),
    ("tto_06_olasiliklar.html", "Ölçülen taban oranlar"),
    ("tto_07_fvg_prz_yasam.html", "FVG ve PRZ yaşam döngüsü"),
    ("tto_08_paketler.html", "Kurulum paketlerinin backtest sonucu"),
    ("tto_09_ob_rastgele_seviye.html", "OB retest ile aynı derinlikte rastgele limit"),
    ("tto_10_diverjans.html", "Diverjans tablosu: kaynak iddiası ve ölçülen"),
    ("tto_11_seans_profili.html", "Seans profili: kill zone'daki kurulum ayrışıyor mu"),
]


def _sar(metin: str, en: int = 104) -> str:
    satir, simdi = [], ""
    for sozcuk in metin.split(" "):
        if simdi and len(simdi) + 1 + len(sozcuk) > en:
            satir.append(simdi); simdi = sozcuk
        else:
            simdi = f"{simdi} {sozcuk}".strip()
    if simdi:
        satir.append(simdi)
    return "<br>".join(satir)


def _duzen(fig: go.Figure, baslik: str, alt: str, yuk: int = 560) -> go.Figure:
    alt = _sar(alt)
    fig.update_layout(
        title=dict(text=f"<b>{baslik}</b><br><span style='font-size:12px;color:{GRI}'>{alt}</span>",
                   x=0, xanchor="left", y=1, yanchor="top", yref="container", pad=dict(t=14),
                   font=dict(size=15, color=MUREKKEP)),
        height=yuk, paper_bgcolor=KAGIT, plot_bgcolor=KAGIT,
        font=dict(family="IBM Plex Mono, ui-monospace, monospace", size=11, color=MUREKKEP),
        margin=dict(l=56, r=24, t=48 + 16 * (alt.count("<br>") + 1), b=48),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0, font=dict(size=10)),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRI, rangeslider=dict(visible=False))
    fig.update_yaxes(gridcolor="#ececec", zeroline=False, linecolor=GRI)
    return fig


def _yaz(fig: go.Figure, ad: str) -> Path:
    yol = CIKTI / ad
    fig.write_html(yol, include_plotlyjs="cdn", config=dict(displayModeBar=False))
    plotly_stil.isle(yol)
    return yol


def _mum(fig, s, bas, son, row=None, col=None):
    x = list(range(bas, son))
    yer = {} if row is None else {"row": row, "col": col}
    fig.add_trace(go.Candlestick(x=x, open=s.o[bas:son], high=s.h[bas:son], low=s.l[bas:son], close=s.c[bas:son],
                                 increasing=dict(line=dict(color="#93b0cd", width=1), fillcolor="#93b0cd"),
                                 decreasing=dict(line=dict(color="#c99aa0", width=1), fillcolor="#c99aa0"),
                                 showlegend=False, hoverinfo="skip"), **yer)


def _zaman(s, i) -> str:
    import datetime as dt
    return dt.datetime.fromtimestamp(int(s.zaman[i]), dt.timezone.utc).strftime("%d.%m.%Y %H:%M")


def _tarih_ekseni(fig, s, bas: int, son: int, adim: int | None = None, **yer) -> None:
    """Bar indeksi okura bir şey söylemez; eksen etiketleri tarih olur."""
    import datetime as dt
    adim = adim or max(1, (son - bas) // 8)
    vals = list(range(bas, son, adim))
    fig.update_xaxes(tickvals=vals, ticktext=[dt.datetime.fromtimestamp(int(s.zaman[i]), dt.timezone.utc).strftime("%d.%m %H:%M") for i in vals], **yer)


def _pencere_sec(y: Y.Yapi, n: int, uzun: int = 220) -> tuple[int, int]:
    """Son MSS'in içinde olduğu, PRZ ve FVG de barındıran bir pencere."""
    son = n
    mss = [o.bar for o in y.olaylar if o.tur == "MSS"]
    if mss:
        son = min(n, mss[-1] + 60)
    return max(0, son - uzun), son


# ── 01 · fiyat paneli ────────────────────────────────────────────────────────
def sekil_fiyat(s, y: Y.Yapi, bas: int, son: int, ad: str, kaynak: str) -> Path:
    fig = go.Figure()
    _mum(fig, s, bas, son)
    x = list(range(bas, son))
    # dealing range ve EQ
    arL = [y.aralik[i][0] if y.aralik[i] else None for i in x]
    arH = [y.aralik[i][1] if y.aralik[i] else None for i in x]
    fig.add_trace(go.Scatter(x=x, y=arH, mode="lines", line=dict(color=MUREKKEP, width=1, dash="dot"), name="dealing range üstü"))
    fig.add_trace(go.Scatter(x=x, y=arL, mode="lines", line=dict(color=MUREKKEP, width=1, dash="dot"), name="dealing range altı"))
    fig.add_trace(go.Scatter(x=x, y=[(a + b) / 2 if a and b else None for a, b in zip(arL, arH)], mode="lines", line=dict(color=GRI, width=1), name="EQ (%50)"))
    # OTE bandı
    ote_a, ote_u = [], []
    for i in x:
        ar = y.aralik[i]
        if ar and y.trend[i] != 0:
            L, H = ar
            if y.trend[i] > 0:
                ote_a.append(H - 0.79 * (H - L)); ote_u.append(H - 0.62 * (H - L))
            else:
                ote_a.append(L + 0.62 * (H - L)); ote_u.append(L + 0.79 * (H - L))
        else:
            ote_a.append(None); ote_u.append(None)
    fig.add_trace(go.Scatter(x=x + x[::-1], y=ote_u + ote_a[::-1], fill="toself", fillcolor="rgba(184,134,11,0.15)", line=dict(width=0), name="OTE 0,62–0,79", hoverinfo="skip"))
    # yapı olayları
    for o in y.olaylar:
        if bas <= o.bar < son:
            renk = MUREKKEP if o.tur == "BOS" else CLARET if o.tur == "MSS" else ALTIN
            fig.add_shape(type="line", x0=max(o.kaynak_bar, bas), x1=o.bar, y0=o.seviye, y1=o.seviye, line=dict(color=renk, width=2 if o.tur == "MSS" else 1, dash="solid" if o.tur == "BOS" else "dash"))
            fig.add_annotation(x=o.bar, y=o.seviye, text=o.tur, showarrow=False, yshift=12 if o.yon > 0 else -12, font=dict(size=10, color=renk))
    # FVG
    for f in y.fvgler:
        if bas <= f.bar < son:
            bitis = min(son - 1, f.dolu_bar if f.dolu_bar is not None else son - 1)
            fig.add_shape(type="rect", x0=f.bar - 2, x1=bitis, y0=f.alt, y1=f.ust, line=dict(color=MOR, width=1), fillcolor="rgba(106,76,147,0.18)" if f.durum in ("taze", "ce") else "rgba(138,138,138,0.10)")
    # OB
    for ob in y.oblar:
        if bas <= ob.olay_bar < son:
            bitis = min(son - 1, ob.bitis_bar if ob.bitis_bar is not None else son - 1)
            fig.add_shape(type="rect", x0=ob.bar, x1=bitis, y0=ob.alt, y1=ob.ust, line=dict(color=MAVI, width=1), fillcolor="rgba(47,93,140,0.15)")
    # PRZ
    for p in y.przler:
        if bas <= p.cizim_bar < son:
            bitis = min(son - 1, p.durum_bar if p.durum_bar is not None else son - 1)
            fig.add_shape(type="rect", x0=p.cizim_bar, x1=bitis, y0=p.alt, y1=p.ust, line=dict(color=ALTIN, width=1), fillcolor="rgba(184,134,11,0.25)")
            fig.add_annotation(x=p.cizim_bar, y=p.ust, text=f"PRZ {p.ad}", showarrow=False, yshift=10, xanchor="left", font=dict(size=10, color=ALTIN))
    # sweep işaretleri
    sw = [(b, sev) for b, adh, sev, yon in y.sweepler if bas <= b < son]
    fig.add_trace(go.Scatter(x=[b for b, _ in sw], y=[s.h[b] for b, _ in sw], mode="markers", marker=dict(symbol="x", color=ALTIN, size=8), name="sweep (fitil ötede, kapanış geride)"))
    # swing'ler
    swx = [w.bar for w in y.swingler if bas <= w.bar < son]
    fig.add_trace(go.Scatter(x=swx, y=[s.h[w.bar] if w.tur == "H" else s.l[w.bar] for w in y.swingler if bas <= w.bar < son], mode="markers",
                             marker=dict(symbol=["triangle-down" if w.tur == "H" else "triangle-up" for w in y.swingler if bas <= w.bar < son], color=GRI, size=7), name="onaylı swing"))
    _duzen(fig, "Fiyat paneli grafikte ne çizer",
           f"{kaynak} · {_zaman(s, bas)} → {_zaman(s, son - 1)} (UTC). Noktalı çizgiler dealing range ve EQ, altın bant OTE 0,62–0,79; "
           "siyah çizgi BOS, altın kesik CHoCH, claret kalın MSS; mor kutu FVG (gri: dolmuş), mavi kutu order block, altın kutu harmonik PRZ; "
           "çarpı sweep, gri üçgen onaylı swing. Hepsi kapanmış barlardan.", 620)
    _tarih_ekseni(fig, s, bas, son)
    return _yaz(fig, ad)


# ── 02 · momentum paneli ─────────────────────────────────────────────────────
def sekil_momentum(s, y: Y.Yapi, m: Y.Momentum, bas: int, son: int, ad: str, kaynak: str) -> Path:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.42, 0.3, 0.28], vertical_spacing=0.04)
    _mum(fig, s, bas, son, 1, 1)
    x = list(range(bas, son))
    fig.add_trace(go.Scatter(x=x, y=[m.rsi[i] for i in x], mode="lines", line=dict(color=MUREKKEP, width=2), name="RSI 14"), row=2, col=1)
    fig.add_trace(go.Scatter(x=x, y=[None if m.rsi_sira[i] is None else m.rsi_sira[i] for i in x], mode="lines", line=dict(color=MAVI, width=1), name="RSI göreli sırası (280 bar)"), row=2, col=1)
    fig.add_hline(y=50, line=dict(color=GRI, width=1), row=2, col=1)
    fig.add_trace(go.Bar(x=x, y=[None if m.itki_sira[i] is None else m.itki_sira[i] for i in x],
                         marker=dict(color=[ALTIN if (m.itki_sira[i] or 0) >= 80 else "#d8cfae" for i in x]), name="itki göreli sırası (gövde/ATR)"), row=3, col=1)
    disp = [i for i in x if y.displacement(i)]
    fig.add_trace(go.Scatter(x=disp, y=[5] * len(disp), mode="markers", marker=dict(symbol="diamond", color=CLARET, size=6), name="displacement barı"), row=3, col=1)
    dv = [d for d in m.diverjanslar if bas <= d.bar < son]
    fig.add_trace(go.Scatter(x=[d.pivot for d in dv], y=[m.rsi[d.pivot] for d in dv], mode="markers+text",
                             text=[("Div" if d.tip <= 2 else "Gizli") + (f" #{d.tablo}" if d.tablo is not None else "") for d in dv], textposition="top center", textfont=dict(size=9),
                             marker=dict(symbol=["triangle-up" if d.tip in (1, 3) else "triangle-down" for d in dv], color=[YESIL if d.tip in (1, 3) else CLARET for d in dv], size=9), name="RSI diverjansı (kullanıcı kuralı)"), row=2, col=1)
    _duzen(fig, "Alt panel ekranda ne çizer",
           f"{kaynak} · aynı pencere. Orta: RSI (siyah) ve son 280 bara göre göreli sırası (mavi, 0–100); üçgenler kullanıcı kuralıyla bulunan "
           "diverjanslar, numara tablo satırı. Alt: itki = gövde/ATR'nin göreli sırası; altın sütun sıra ≥ 80, claret baklava SMC displacement eşiği.", 720)
    fig.update_yaxes(title_text="RSI · sıra", row=2, col=1)
    fig.update_yaxes(title_text="itki sırası", row=3, col=1)
    _tarih_ekseni(fig, s, bas, son, row=3, col=1)
    return _yaz(fig, ad)


# ── 03 · okuma sırası ────────────────────────────────────────────────────────
def sekil_okuma(s, y: Y.Yapi, m: Y.Momentum, ad: str, kaynak: str) -> Path:
    # bacağında FVG olan son MSS: paketin dört adımı da dolu bir bar
    mss = [o for o in y.olaylar if o.tur == "MSS" and any(f.yon == o.yon and o.bar - 10 <= f.bar <= o.bar for f in y.fvgler)]
    o = mss[-1]
    i = o.bar
    bas, son = max(0, i - 60), min(len(s), i + 25)
    fig = go.Figure()
    _mum(fig, s, bas, son)
    ar = y.aralik[i]
    fig.add_vline(x=i, line=dict(color=GRI, width=1, dash="dot"))
    fig.add_shape(type="line", x0=o.kaynak_bar, x1=i, y0=o.seviye, y1=o.seviye, line=dict(color=CLARET, width=2))
    sw = [(b, adh, sev, yon) for b, adh, sev, yon in y.sweepler if i - 10 <= b < i and yon == -o.yon]
    d = y.durum(i)
    not_ = [f"① Yapı: {'YÜKSELİŞ' if d['trend'] > 0 else 'DÜŞÜŞ'} · son olay MSS {'↑' if o.yon > 0 else '↓'} (bu bar)",
            f"② Konum: {d['bolge']} {B.sayi(d['konum'], 1)} %" if d["konum"] is not None else "② Konum: aralık yok",
            f"③ Likidite: {sw[-1][1]} süpürüldü ({i - sw[-1][0]} bar önce)" if sw else "③ Likidite: yakın sweep yok",
            "④ Kurulum: sweep → MSS → FVG (CE'ye limit)" if any(f.yon == o.yon and i - 10 <= f.bar <= i for f in y.fvgler) else "④ Kurulum: FVG yok — paket kurulmaz",
            f"Alt panel: itki sırası {B.sayi(m.itki_sira[i] or 0, 0)} % · RSI {B.sayi(m.rsi[i] or 0, 1)} (sıra {B.sayi(m.rsi_sira[i] or 0, 0)} %)"]
    for k, t in enumerate(not_):
        fig.add_annotation(xref="paper", yref="paper", x=0.01, y=0.97 - 0.055 * k, text=t, showarrow=False, xanchor="left", font=dict(size=11, color=MUREKKEP), bgcolor="rgba(255,255,255,0.85)")
    if sw:
        fig.add_trace(go.Scatter(x=[sw[-1][0]], y=[sw[-1][2]], mode="markers", marker=dict(symbol="x", color=ALTIN, size=11), name="süpürülen havuz"))
    for f in y.fvgler:
        if f.yon == o.yon and i - 10 <= f.bar <= i:
            fig.add_shape(type="rect", x0=f.bar - 2, x1=son - 1, y0=f.alt, y1=f.ust, line=dict(color=MOR, width=1), fillcolor="rgba(106,76,147,0.18)")
            fig.add_hline(y=f.ce, line=dict(color=MOR, width=1, dash="dash"), annotation_text="FVG CE (limit)", annotation_position="right")
            break
    _duzen(fig, "Okuma sırası tek bir karar barında",
           f"{kaynak} · MSS barı {_zaman(s, i)} (UTC), noktalı dikey çizgi. Dört adım fiyat panelinden, beşincisi alt panelden; hepsi barın kapanışında biliniyor. "
           "Claret çizgi kırılan korunan seviye, çarpı kırılımdan önce süpürülen havuz, mor kutu bacağın FVG'si.", 600)
    _tarih_ekseni(fig, s, bas, son, 12)
    return _yaz(fig, ad)


# ── 04 · kurulumlar ──────────────────────────────────────────────────────────
def sekil_kurulumlar(S: dict, ad: str) -> Path:
    fig = make_subplots(rows=1, cols=5, subplot_titles=[PAKET_AD[p] for p in BT.PAKETLER], horizontal_spacing=0.035)
    for c, paket in enumerate(BT.PAKETLER, start=1):
        # her paket için ilk uygun örneği bul (1 sa, EUR/USD öncelikli)
        ornek = None
        for ens in ("eurusd", "gbpusd", "xau", "spx", "usdjpy"):
            s = S["1h"][ens]; y = Y.Yapi(s); m = Y.Momentum(s)
            E = BT.paket_emirleri(s, y, m, paket, 2.0 if paket != "diverjans" else 1.0)
            for e in reversed(E):
                r = BT.islem(s, e["bar"], e["yon"], e["giris"], e["stop"], e["hedef"], e["limit"], BT.UFUK)
                if r is not None and r["cikis"] - e["bar"] <= 40:
                    ornek = (s, e, r, ens); break
            if ornek:
                break
        if not ornek:
            continue
        s, e, r, ens = ornek
        i = e["bar"]
        bas, son = max(0, i - 25), min(len(s), r["cikis"] + 5)
        _mum(fig, s, bas, son, 1, c)
        for yv, renk, dash, adx in ((e["giris"], MUREKKEP, "solid", "giriş"), (e["stop"], CLARET, "dash", "stop"), (e["hedef"], YESIL, "dot", "hedef")):
            fig.add_shape(type="line", x0=i, x1=son - 1, y0=yv, y1=yv, line=dict(color=renk, width=1.5, dash=dash), row=1, col=c)
        fig.add_vline(x=i, line=dict(color=GRI, width=1, dash="dot"), row=1, col=c)
        fig.add_annotation(xref="x domain" if c == 1 else f"x{c} domain", yref="y domain" if c == 1 else f"y{c} domain", x=0.03, y=0.97, text=f"{ens.upper()} · {B.sayi(r['R'], 2, True)} R", showarrow=False, xanchor="left", font=dict(size=10, color=MUREKKEP), bgcolor="rgba(255,255,255,0.8)")
        _tarih_ekseni(fig, s, bas, son, max(1, (son - bas) // 2), row=1, col=c)
    _duzen(fig, "Beş kurulum paketi gerçek barlarda",
           "1 saatlik arşivden her paketin son örneği: noktalı dikey çizgi sinyal barı (kapanmış), siyah giriş, claret kesik stop, yeşil noktalı hedef; başlıkta işlemin sonucu R olarak. "
           "Emir bir sonraki barda çalışır; limit paketlerde giriş seviyeye gelince dolar.", 520)
    fig.update_layout(showlegend=False, margin=dict(r=70))
    fig.update_xaxes(tickangle=0, tickfont=dict(size=9))
    return _yaz(fig, ad)


# ── 05 · harmonik örnek ─────────────────────────────────────────────────────
def sekil_harmonik(S: dict, ad: str) -> Path:
    ornek = None
    for ens in ("eurusd", "gbpusd", "xau", "usdjpy", "spx", "wti"):
        s = S["1h"][ens]; y = Y.Yapi(s)
        for p in reversed(y.przler):
            if p.durum == "teyit" and p.ad in Y.HARMONIK and p.durum_bar is not None:
                ornek = (s, y, p, ens); break
        if ornek:
            break
    s, y, p, ens = ornek
    bas, son = max(0, p.x - 8), min(len(s), p.durum_bar + 30)
    fig = go.Figure()
    _mum(fig, s, bas, son)
    pts = [(p.x, "X"), (p.a, "A"), (p.b, "B"), (p.c, "C")]
    xs = [b for b, _ in pts]
    ys = [s.l[b] if (p.yon > 0) == (k % 2 == 0) else s.h[b] for k, (b, _) in enumerate(pts)]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers+text", text=[t for _, t in pts], textposition="top center", line=dict(color=MUREKKEP, width=1.5), marker=dict(size=7, color=MUREKKEP), name="X-A-B-C"))
    fig.add_shape(type="rect", x0=p.cizim_bar, x1=son - 1, y0=p.alt, y1=p.ust, line=dict(color=ALTIN, width=1), fillcolor="rgba(184,134,11,0.25)")
    fig.add_hline(y=p.stop, line=dict(color=CLARET, width=1, dash="dash"), annotation_text="stop (kalıp geçersizliği)", annotation_position="top right", annotation_font=dict(size=10, color=CLARET))
    fig.add_hline(y=p.t1, line=dict(color=YESIL, width=1, dash="dot"), annotation_text="T1 0,382 AD", annotation_position="top right", annotation_font=dict(size=10, color=YESIL))
    fig.add_hline(y=p.t2, line=dict(color=YESIL, width=1, dash="dot"), annotation_text="T2 0,618 AD", annotation_position="top right", annotation_font=dict(size=10, color=YESIL))
    fig.add_vline(x=p.cizim_bar, line=dict(color=GRI, width=1, dash="dot"))
    fig.add_vline(x=p.durum_bar, line=dict(color=YESIL, width=1, dash="dot"))
    fig.add_annotation(x=p.cizim_bar, y=p.ust, text="PRZ çizildi (C onaylandı)", showarrow=False, yshift=14, xanchor="left", font=dict(size=10, color=GRI))
    fig.add_annotation(x=p.durum_bar, y=p.alt, text="teyit: dönüş mumu", showarrow=False, yshift=-14, xanchor="left", font=dict(size=10, color=YESIL))
    _duzen(fig, "Harmonik PRZ nasıl kurulur",
           f"{ens.upper()} · 1 saatlik · {p.ad} · {_zaman(s, p.x)} → {_zaman(s, son - 1)} (UTC). PRZ üç sayıdan: kalıbın XA oranı, C'nin derinliğine göre BC katı ve AB=CD; "
           "C onaylandığı bar çizilir (gri dikey), fiyat bölgeye girip yön lehine gövdeli kapanış verince teyit (yeşil dikey). Stop kalıbın geçersizlik oranı, hedefler D→A'nın 0,382 ve 0,618'i.", 600)
    _tarih_ekseni(fig, s, bas, son)
    return _yaz(fig, ad)


# ── 06 · olasılıklar ─────────────────────────────────────────────────────────
def sekil_olasiliklar(d: dict, ad: str) -> Path:
    olc = [("bos_t1", "BOS → 0,618 aralık hedefi"), ("mss_devam", "MSS → yeni yönde BOS"), ("sweep_tepki", "sweep → 1 ATR ters"),
           ("fvg_dolu50", "FVG 50 barda dolar"), ("fvg_ce_tepki", "FVG CE → 1 ATR tepki"), ("ob_tepki", "OB ilk dokunuş → 1 ATR"),
           ("prz_teyit", "PRZ'ye giren → teyit"), ("prz_t1", "PRZ teyit → T1")]
    fig = go.Figure()
    renk = {"5m": "#d8cfae", "15m": ALTIN, "1h": MAVI, "4h": MUREKKEP, "1d": CLARET}
    for tf in BT.ZAMAN_DILIMLERI:
        t = d["olasilik"][tf]["toplam"]
        ys = [100 * (t[k]["oran"] or 0) for k, _ in olc]
        err = [100 * ((t[k]["ca_ust"] - t[k]["ca_alt"]) / 2 if t[k].get("oran") is not None else 0) for k, _ in olc]
        fig.add_trace(go.Bar(name=TF_AD[tf], x=[a for _, a in olc], y=ys, error_y=dict(type="data", array=err, visible=True, thickness=1),
                             marker_color=renk[tf], text=[f"n={t[k]['n']}" for k, _ in olc], textposition="outside", textfont=dict(size=8)))
    fig.add_hline(y=50, line=dict(color=GRI, width=1, dash="dash"), annotation_text="yazı tura", annotation_position="right")
    _duzen(fig, "Ölçülen taban oranlar",
           "15 enstrüman, beş zaman dilimi, kapanmış barlar; çubuk = oran, ince çizgi %95 güven aralığı, üstte N. "
           "BOS hedefi üç kırılımın birinde geliyor; sweep sonrası dönüş yazı tura; FVG dörtte üç dolar; PRZ'ye giren fiyatın üçte ikisi dönüş mumu verir ve o zaman T1 üçte ikide gelir — ama T1 yakın, stop uzak (paket sonucuna bakın).", 620)
    fig.update_layout(barmode="group", yaxis_title="%", yaxis_range=[0, 100])
    return _yaz(fig, ad)


# ── 07 · FVG ve PRZ yaşam döngüsü ───────────────────────────────────────────
def sekil_yasam(d: dict, ad: str) -> Path:
    fig = make_subplots(rows=1, cols=2, subplot_titles=["FVG: 50 barda ne oldu", "PRZ: çizilenlerin akıbeti"], horizontal_spacing=0.12)
    tfs = list(BT.ZAMAN_DILIMLERI)
    for k, (anahtar, adx, renk) in enumerate((("fvg_ce50", "CE'ye dokunuldu", MOR), ("fvg_dolu50", "tamamen doldu", GRI), ("fvg_ters50", "ters döndü (IFVG)", CLARET))):
        fig.add_trace(go.Bar(name=adx, x=[TF_AD[t] for t in tfs], y=[100 * (d["olasilik"][t]["toplam"][anahtar]["oran"] or 0) for t in tfs], marker_color=renk), row=1, col=1)
    for anahtar, adx, renk in (("prz_tamamlanma", "fiyat PRZ'ye geldi", ALTIN), ("prz_gecersiz_once", "gelmeden geçersiz", GRI), ("prz_teyit", "gelenin dönüş mumu vermesi", YESIL), ("prz_t1", "teyitten T1 (stoptan önce)", MAVI)):
        fig.add_trace(go.Bar(name=adx, x=[TF_AD[t] for t in tfs], y=[100 * (d["olasilik"][t]["toplam"][anahtar]["oran"] or 0) for t in tfs], marker_color=renk), row=1, col=2)
    _duzen(fig, "FVG ve PRZ yaşam döngüsü",
           "Sol: displacement'lı FVG'lerin 50 bar içinde CE'ye dokunma, tam dolma ve ters dönme oranı (aynı FVG birden çok kutuda sayılabilir). "
           "Sağ: çizilen PRZ'lerin ne kadarına fiyat geldi, gelenlerin ne kadarı dönüş mumu verdi, teyit alanların ne kadarı stoptan önce T1'e ulaştı.", 520)
    fig.update_layout(barmode="group", yaxis_title="%", yaxis_range=[0, 100], yaxis2_range=[0, 100])
    return _yaz(fig, ad)


# ── 08 · paketler ────────────────────────────────────────────────────────────
def sekil_paketler(d: dict, ad: str) -> Path:
    fig = make_subplots(rows=1, cols=5, subplot_titles=[TF_AD[t] for t in BT.ZAMAN_DILIMLERI], shared_yaxes=True, horizontal_spacing=0.02)
    for c, tf in enumerate(BT.ZAMAN_DILIMLERI, start=1):
        sat = [p for p in d["paket_toplam"] if p["tf"] == tf and p["suzgec"] == "yok" and (p["hedef_R"] == 2.0 or p["paket"] == "diverjans")]
        sat.sort(key=lambda p: BT.PAKETLER.index(p["paket"]))
        x = [PAKET_AD[p["paket"]] for p in sat]
        fig.add_trace(go.Bar(name="brüt ort. R", x=x, y=[p["ort_R"] for p in sat], marker_color=MAVI, showlegend=c == 1), row=1, col=c)
        fig.add_trace(go.Bar(name="spread sonrası", x=x, y=[p["net_ort_R"] for p in sat], marker_color=CLARET, showlegend=c == 1), row=1, col=c)
        fig.add_trace(go.Scatter(name="rastgele giriş", x=x, y=[p["rastgele_ort_R"] for p in sat], mode="markers", marker=dict(symbol="line-ew-open", size=18, color=MUREKKEP, line=dict(width=2)), showlegend=c == 1), row=1, col=c)
        fig.add_trace(go.Scatter(name="N", x=x, y=[max(p["ort_R"], p["net_ort_R"], 0) + 0.05 for p in sat], mode="text", text=[f"n={p['n']}" for p in sat], textfont=dict(size=8, color=GRI), showlegend=False), row=1, col=c)
        fig.add_hline(y=0, line=dict(color=GRI, width=1), row=1, col=c)
    _duzen(fig, "Kurulum paketlerinin backtest sonucu",
           "Zaman dilimine göre beş paket (hedef 2R; diverjans tablonun kendi hedefi): mavi brüt ortalama R, claret spread varsayımı düşülmüş; siyah çizgi aynı sayıda rastgele girişin ortalaması (30 koşu). "
           "OB retest her dilimde rastgele girişi yeniyor — ama aynı derinlikteki rastgele limit de yeniyor (bir sonraki figür); 15 dk ve altında spread hepsini yutuyor.", 560)
    fig.update_layout(barmode="group", yaxis_title="ortalama R", yaxis_range=[-1.0, 0.6], margin=dict(r=40, b=110))
    return _yaz(fig, ad)


# ── 09 · OB ve rastgele seviye ──────────────────────────────────────────────
def sekil_ob(d: dict, ad: str) -> Path:
    sat = [p for p in d["paket_toplam"] if p["paket"] == "ob_retest" and p["suzgec"] == "yok" and p["hedef_R"] == 2.0]
    sat.sort(key=lambda p: BT.ZAMAN_DILIMLERI.index(p["tf"]))
    x = [f"{TF_AD[p['tf']]}<br>n={p['n']} · risk medyanı {B.sayi(p['risk_atr_p50'], 2)} ATR<br>seviye kıyasını geçen seri {p['seri_ustu_rastgele_seviye']}/{p['seri']}" for p in sat]
    fig = go.Figure()
    fig.add_trace(go.Bar(name="OB retest · brüt", x=x, y=[p["ort_R"] for p in sat], marker_color=MAVI))
    fig.add_trace(go.Bar(name="aynı derinlikte rastgele limit · brüt", x=x, y=[p["rastgele_seviye_ort_R"] for p in sat], marker_color="#93b0cd"))
    fig.add_trace(go.Bar(name="OB retest · spread sonrası", x=x, y=[p["net_ort_R"] for p in sat], marker_color=CLARET))
    fig.add_trace(go.Scatter(name="rastgele giriş (piyasa)", x=x, y=[p["rastgele_ort_R"] for p in sat], mode="markers", marker=dict(symbol="line-ew-open", size=22, color=MUREKKEP, line=dict(width=2))))
    fig.add_hline(y=0, line=dict(color=GRI, width=1))
    _duzen(fig, "OB retest ile aynı derinlikte rastgele limit",
           "Order block'a limit koymak (MT, stop fitil ötesi, 2R) her zaman diliminde rastgele piyasa girişini yeniyor. Aynı emir geometrisi — sinyal kapanışından aynı derinlikte, aynı risk, aynı hedef — rastgele bir barda kurulunca "
           "aynı sayıyı veriyor: kenar bloğun YERİNDE değil, geri çekilmeyi limitle almanın kendisinde. Risk medyanı 0,6 ATR olduğu için spread 15 dk ve altında sonucu eksiye çeviriyor.", 560)
    fig.update_layout(barmode="group", yaxis_title="ortalama R", margin=dict(b=90))
    return _yaz(fig, ad)


# ── 10 · diverjans tablosu ──────────────────────────────────────────────────
def sekil_diverjans(d: dict, ad: str) -> Path:
    fig = make_subplots(rows=1, cols=2, subplot_titles=["1 saatlik", "5 dakikalık"], shared_yaxes=True, horizontal_spacing=0.06)
    for c, tf in enumerate(("1h", "5m"), start=1):
        sat = [r for r in d["diverjans"][tf] if r["n"] >= 30]
        sat.sort(key=lambda r: r["satir"])
        x = [f"#{r['satir']}" for r in sat]
        fig.add_trace(go.Bar(name="kaynak iddiası", x=x, y=[r["iddia"] for r in sat], marker_color="#d8cfae", showlegend=c == 1), row=1, col=c)
        fig.add_trace(go.Bar(name="ölçülen isabet", x=x, y=[100 * r["oran"] for r in sat], marker_color=MAVI,
                             error_y=dict(type="data", array=[100 * (r["ca_ust"] - r["ca_alt"]) / 2 for r in sat], visible=True, thickness=1), showlegend=c == 1), row=1, col=c)
        fig.add_trace(go.Scatter(x=x, y=[max(r["iddia"], 100 * r["oran"]) + 4 for r in sat], mode="text", text=[f"n={r['n']}" for r in sat], textfont=dict(size=8, color=GRI), showlegend=False), row=1, col=c)
        fig.add_hline(y=50, line=dict(color=GRI, width=1, dash="dash"), row=1, col=c)
    _duzen(fig, "Diverjans tablosu: kaynak iddiası ve ölçülen",
           "Kullanıcı dosyasındaki 25 satırın N ≥ 30 olanları; bej kaynak yüzdesi (örneklem ve yöntem yok), mavi aynı satırın kendi SL/TP çarpanıyla arşivde ölçülen isabeti, %95 aralığıyla. "
           "En yüksek iddialı satır (#0, %63,6) her iki dilimde %30'un altında; satırların çoğu %50 çizgisinin etrafında.", 560)
    fig.update_layout(barmode="group", yaxis_title="%", yaxis_range=[0, 80])
    return _yaz(fig, ad)


# ── 11 · seans profili ─────────────────────────────────────────────────────
def seans_ozet_cumlesi(d: dict) -> str:
    """Kill zone ile dışı arasındaki ayrışmayı VERİDEN yazar: kıyaslanabilen
    satır sayısı, |t| ≥ 2 olan satır sayısı ve işaretleri, en büyük fark (hedef
    2R, diverjans kendi hedefi). Alt yazıya elle sayı girmez."""
    sat = [p for p in d["seans_toplam"] if (p["hedef_R"] == 2.0 or p["paket"] == "diverjans") and p.get("kz_fark")]
    if not sat:
        return "Kill zone ile dışı N ≥ 30 ile kıyaslanabilen paket yok."
    anlamli = [p for p in sat if p["kz_fark"]["t"] is not None and abs(p["kz_fark"]["t"]) >= 2]
    arti = sum(1 for p in anlamli if p["kz_fark"]["fark"] > 0)
    en = max(sat, key=lambda p: abs(p["kz_fark"]["fark"]))
    kz, dis, f = en["seans"]["kz"], en["seans"]["kz_disi"], en["kz_fark"]
    # Sayıya ek getirilmez ("3'ünde" / "4'ünde" ek sayıya göre değişir); cümle sayıyı ekten ayırır.
    return (f"Kıyaslanabilir satır {B.sayi(len(sat), 0)}; |t| ≥ 2 olan {B.sayi(len(anlamli), 0)} ({B.sayi(arti, 0)} kill zone lehine, "
            f"{B.sayi(len(anlamli) - arti, 0)} aleyhine). En büyük fark {B.sayi(f['fark'], 2, True)} R, t {B.sayi(f['t'], 1, True)} "
            f"({PAKET_AD[en['paket']]}, {TF_AD[en['tf']]}: kill zone {B.sayi(kz['ort_R'], 2, True)} R · n {B.sayi(kz['n'], 0)}, "
            f"dışı {B.sayi(dis['ort_R'], 2, True)} R · n {B.sayi(dis['n'], 0)}).")


def sekil_seans(d: dict, ad: str) -> Path:
    tfs = list(BT.GUN_ICI)
    kovalar = [a for a, _, _ in Y.SEANSLAR] + ["diger"]
    renk = {"sweep_mss_fvg": MAVI, "ob_retest": MOR, "prz": ALTIN, "diverjans": GRI, "bos_devam": CLARET}
    fig = make_subplots(rows=1, cols=3, subplot_titles=[TF_AD[t] for t in tfs], shared_yaxes=True, horizontal_spacing=0.03)
    for c, tf in enumerate(tfs, start=1):
        for paket in BT.PAKETLER:
            sat = next((p for p in d["seans_toplam"] if p["tf"] == tf and p["paket"] == paket
                        and (p["hedef_R"] == 2.0 or paket == "diverjans")), None)
            if not sat:
                continue
            pr = sat["seans"]
            n = [pr.get(k, {}).get("n", 0) for k in kovalar]
            y = [pr[k]["ort_R"] if nn else None for k, nn in zip(kovalar, n)]
            fig.add_trace(go.Bar(name=PAKET_AD[paket], x=[Y.SEANS_AD[k] for k in kovalar], y=y,
                                 marker=dict(color=renk[paket], opacity=[1.0 if nn >= 30 else 0.35 for nn in n]),
                                 customdata=n, hovertemplate="%{x} · " + PAKET_AD[paket] + ": %{y:.2f} R · n=%{customdata}<extra></extra>",
                                 showlegend=c == 1), row=1, col=c)
        # kill zone kovaları (Londra, NY AM) gölgeli — kategori ekseninde 1 ve 2. sıra
        fig.add_vrect(x0=0.5, x1=2.5, fillcolor=ALTIN, opacity=0.08, line_width=0, row=1, col=c)
        fig.add_hline(y=0, line=dict(color=GRI, width=1), row=1, col=c)
    _duzen(fig, "Seans profili: kill zone'daki kurulum ayrışıyor mu",
           "Süzgeçsiz paketlerin işlemleri sinyal barının New York seansına kovalandı (ders 5.2 tablosu; gölgeli iki kova kill zone). "
           "Çubuk brüt ortalama R, hedef 2R; soluk çubuk n < 30. " + seans_ozet_cumlesi(d), 560)
    fig.update_layout(barmode="group", yaxis_title="ortalama R", margin=dict(b=120))
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=9))
    return _yaz(fig, ad)


def mdx_sirasi_sina() -> list[str]:
    if not MDX.exists():
        return [f"{MDX.name} yok"]
    metin = MDX.read_text(encoding="utf-8")
    gomulu = re.findall(r'src="/indikatorler/(tto_\d\d_[a-z_]+\.html)"', metin)
    hata = []
    for ad, _ in SIRA:
        if not (CIKTI / ad).exists():
            hata.append(f"figür dosyası yok: {ad}")
        if ad not in gomulu:
            hata.append(f"MDX'te gömülü değil: {ad}")
    for g in gomulu:
        if g not in [a for a, _ in SIRA]:
            hata.append(f"MDX'te SIRA dışı figür: {g}")
    if [g for g in gomulu if g in [a for a, _ in SIRA]] != [a for a, _ in SIRA if a in gomulu]:
        hata.append("MDX gömme sırası SIRA ile aynı değil")
    return hata


def main() -> int:
    if "--denetle" in sys.argv:
        h = mdx_sirasi_sina()
        print("\n".join(h) if h else "figür sırası ve dosyalar tamam")
        return 1 if h else 0
    if go is None:
        raise SystemExit("ENGEL · figür üretimi plotly ister ve kurulu değil (kapı yolu `--denetle` onsuz çalışır)")
    d = json.loads(JSON.read_text(encoding="utf-8"))
    S = BT.seriler_tf()
    s = S["1h"]["eurusd"]; y = Y.Yapi(s); m = Y.Momentum(s)
    bas, son = _pencere_sec(y, len(s))
    kaynak = "EUR/USD · 1 saatlik"
    sekil_fiyat(s, y, bas, son, SIRA[0][0], kaynak)
    sekil_momentum(s, y, m, bas, son, SIRA[1][0], kaynak)
    sekil_okuma(s, y, m, SIRA[2][0], kaynak)
    sekil_kurulumlar(S, SIRA[3][0])
    sekil_harmonik(S, SIRA[4][0])
    sekil_olasiliklar(d, SIRA[5][0])
    sekil_yasam(d, SIRA[6][0])
    sekil_paketler(d, SIRA[7][0])
    sekil_ob(d, SIRA[8][0])
    sekil_diverjans(d, SIRA[9][0])
    sekil_seans(d, SIRA[10][0])
    print(f"{len(SIRA)} figür → {CIKTI}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
