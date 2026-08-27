#!/usr/bin/env python3
"""Statik web ciktisi ureticisi — FX haber-duyarlilik endeksi.

Cekirdek ciktilar INTERNETSIZ calisir (data/ altindaki onbelleklerden okur);
yalnizca duyarlilik-getiri sacilimi fiyat icin yfinance'e baglanir (basarisiz
olursa atlanir). Site standardi: include_plotlyjs='cdn', beyaz zemin, lejant
altta, baslik solda.

  cikti/endeks_tarihce.html         — her parite icin endeks tarihcesi (cizgi)
  cikti/endeks_son.html             — son snapshot, sirali yatay bar (+makale sayisi hover)
  cikti/optimizasyon.html           — varlik basina optimizasyon korelasyonu (bar)
  cikti/rejim.html                  — rejim dedektoru: spread / korelasyon / PC1
  cikti/rejim_tarihce.html          — rejim bilesenlerinin tarihcesi (3 panel)
  cikti/korelasyon_matrisi.html     — capraz duyarlilik korelasyon isi haritasi
  cikti/yuvarlanan_korelasyon.html  — 20g yuvarlanan korelasyon, 1g VE 5g ufuk
  cikti/fiyat_endeks.html           — fiyat + gunluk duyarlilik (cift eksen)
  cikti/son_mansetler.html          — son mansetler + FinBERT skor tablosu
  cikti/duyarlilik_getiri.html      — haftalik duyarlilik vs 5 gunluk ileri getiri

Kullanim:  python3 web_cikti.py
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import plotly.graph_objects as go

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(config.DATA_DIR, "index_history.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "cikti")

# Ev stili renkler
TEAL = "#1d5c5c"      # pozitif / bullish
CLARET = "#8e1f2f"    # negatif / bearish
INK = "#1a1a1a"
GRID = "#e8e4dc"
GRI = "#90a4ae"
GOLD = "#9a7327"   # vurgu (ev stili)

# Kategori esikleri TEK KAYNAKTAN gelir: config.SENTIMENT_THRESHOLDS.
# Buradaki bantlar grafigin gorsel katmani, etiketler ise
# sentiment_analyzer.get_sentiment_label() ciktisi; ikisi ayni sayilardan
# turemezse grafik "notr" gorunen bir noktayi "Asiri Satici" diye etiketler.
ESIK_1 = config.SENTIMENT_THRESHOLDS["bullish"]            # Alici/Satici siniri
ESIK_2 = config.SENTIMENT_THRESHOLDS["extremely_bullish"]  # Asiri siniri

# 15 parite icin ayirt edilebilir cizgi paleti
CIZGI_RENKLERI = [
    "#1d5c5c", "#8e1f2f", "#b8860b", "#2f4b7c", "#665191",
    "#a05195", "#d45087", "#f95d6a", "#ff7c43", "#7a9e7e",
    "#4d7ea8", "#c46210", "#5c5346", "#3a7ca5", "#9b2226",
]

KATEGORI_TR = {
    "Extremely Bullish": "Asiri Alici",
    "Bullish": "Alici",
    "Neutral": "Notr",
    "Bearish": "Satici",
    "Extremely Bearish": "Asiri Satici",
}

REJIM_TR = {
    "Risk-Off": "Riskten Kaçış (Risk-Off)",
    "Risk-On": "Risk İştahı (Risk-On)",
    "Transitioning": "Geçiş (Transitioning)",
}

REJIM_RENK = {
    "Risk-Off": CLARET,
    "Risk-On": TEAL,
    "Transitioning": "#b8860b",
}

# Optimize parametre yoksa kullanilacak yedek (basit agirlikli ortalama)
YEDEK_PARAMS = {
    "time_decay_halflife": 2.0,
    "aggregation": "weighted_mean",
    "score_transform": "raw",
    "lag_days": 0,
    "neutral_filter": 0.0,
    "momentum_weight": 0.0,
    "volume_normalize": False,
}


def _gorunen_ad(anahtar):
    """Parite anahtarini okunur ada cevir (config.ASSETS varsa oradan)."""
    varlik = config.ASSETS.get(anahtar)
    if varlik and varlik.get("name"):
        return varlik["name"]
    return anahtar


def _ortak_stil(fig, baslik):
    """Site ev stili: beyaz zemin, baslik solda, lejant yatay ve altta."""
    fig.update_layout(
        title=dict(text=baslik, x=0.02, xanchor="left",
                   font=dict(size=17, color=INK)),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans, Helvetica, Arial, sans-serif",
                  size=12, color=INK),
        legend=dict(orientation="h", yanchor="top", y=-0.12,
                    xanchor="left", x=0),
        margin=dict(l=60, r=30, t=60, b=60),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def _snapshot_saati(kayit):
    """Bir snapshot'in VERI saati — kosu saati degil.

    Endeks degerleri kosu aninda, geriye 7 gunluk pencereyle kuruluyor; o
    pencereye giren en yeni makalenin yayim gunu bu snapshot'in olcum ucudur
    ve `veri_sonu` alaninda yazar. Eski kayitlarda bu alan yok (snapshot
    kendi ucunu yazmiyordu); orada elde yalnizca kosu gunu var, onu kullaniriz
    ve hover'da kosu zamanini acikca gosteririz — uydurulmus bir tarih degil,
    kaydedilmemis bir tarihin en iyi yerine gecenidir.

    Rejim panelinin `as_of`u BILEREK yedek olarak kullanilmaz: o baska bir
    olcumun (GDELT haftalik onbellegi) saatidir, bu serinin degil.
    """
    uc = kayit.get("veri_sonu")
    if uc:
        return str(uc)[:10]
    return (kayit.get("timestamp") or "")[:10]


def _son_kosunun_veri_ucu(kayit):
    """SON snapshot'in olculen veri ucu (ISO), yoksa None.

    Snapshot kendi `veri_sonu`unu yazmiyorsa (eski kosular) ayni buyukluk
    data/sentiment_scores.json'dan olculebilir: o dosya SON kosunun
    skorladigi makaleleri tutar, uc da onlarin en yenisidir. Bu yuzden
    yalnizca son snapshot icin gecerlidir — daha eski bir snapshot'a
    uygulanirsa baska bir kosunun makalelerinden tarih uydurulmus olur.
    """
    uc = kayit.get("veri_sonu")
    if uc:
        return str(uc)
    try:
        with open(config.SENTIMENT_SCORES, "r", encoding="utf-8") as f:
            sk = json.load(f)
        yayim = [m["published"] for v in sk.values()
                 for m in v.get("articles", [])
                 if "score" in m and m.get("published")]
        if yayim:
            return max(yayim)
    except Exception:
        pass
    return None


def yukle_tarihce():
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _makale_sayilari():
    """Varlik basina skorlanmis makale sayisi: data/sentiment_scores.json.

    Son okuma (endeks_son) hover'inda gosterilir — dashboard Overview
    sekmesindeki 'N articles (real-time)' bilgisinin web karsiligi.
    Dosya yoksa bos dict doner (hover'da makale satiri atlanir).
    """
    try:
        with open(config.SENTIMENT_SCORES, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except Exception:
        return {}
    sayilar = {}
    for anahtar, kayit in veri.items():
        makaleler = kayit.get("articles", []) if isinstance(kayit, dict) else []
        sayilar[anahtar] = sum(1 for m in makaleler if "score" in m)
    return sayilar


# ═══════════════════════════════════════════════════════════════════════════════
# Ortak veri hazirlik yardimcilari (gecmis haber onbellegi → duyarlilik serileri)
# ═══════════════════════════════════════════════════════════════════════════════

def _optimize_paramlar():
    """data/optimized_params.json'daki parametreler; yoksa bos dict."""
    try:
        import correlation_optimizer
        return correlation_optimizer.load_optimized_params()
    except Exception:
        return {}


def _varlik_parametresi(opt_params, anahtar):
    """Varlik icin optimize parametre; yoksa weighted_mean yedegi."""
    p = opt_params.get(anahtar)
    return dict(p) if p else dict(YEDEK_PARAMS)


def _skor_ters(makaleler):
    """invert_sentiment varliklari icin skorlari kopya uzerinde tersle
    (tahviller: dusuk getiri haberi = fiyat bullish)."""
    return [dict(a, score=-a.get("score", 0.0)) for a in makaleler]


def _gdelt_haftalik(anahtar, onbellek):
    """Gecmis haber onbelleginden {hafta_sonu: [skorlanmis makale]} dondur."""
    haftalik = onbellek.get(anahtar) or {}
    sonuc = {}
    for hafta, kayit in haftalik.items():
        makaleler = [a for a in kayit.get("articles", []) if "score" in a]
        if not makaleler:
            continue
        if config.ASSETS.get(anahtar, {}).get("invert_sentiment", False):
            makaleler = _skor_ters(makaleler)
        sonuc[hafta] = makaleler
    return sonuc


def haftalik_seriler():
    """Varlik basina haftalik duyarlilik serisi: {varlik: {hafta_sonu: deger}}.

    Kaynak: data/gdelt_cache.json (skorlanmis makaleler). Endeks,
    index_builder.build_weekly_index_series ile optimize parametrelerle
    (yoksa weighted_mean) hesaplanir — bakis-ileri (look-ahead) yok:
    her hafta yalnizca o haftanin sonuna kadarki makaleleri kullanir.
    """
    import news_fetcher
    import index_builder

    onbellek = news_fetcher._load_historical_cache()
    opt = _optimize_paramlar()
    seriler = {}
    for anahtar in config.ASSETS:
        haftalik = _gdelt_haftalik(anahtar, onbellek)
        if not haftalik:
            continue
        params = _varlik_parametresi(opt, anahtar)
        seriler[anahtar] = index_builder.build_weekly_index_series(haftalik, params)
    return seriler


def duyarlilik_matrisi():
    """Varlik basina GUNLUK duyarlilik serisi (pd.Series) — rejim dedektoru girdisi.

    index_builder.build_daily_index_series: 7 gunluk pencere, zaman agirligi,
    z-skor normalizasyonu + EMA yumusatma. Agir bir hesaptir (dakika mertebesi).
    """
    import pandas as pd
    import news_fetcher
    import index_builder

    onbellek = news_fetcher._load_historical_cache()
    opt = _optimize_paramlar()
    seriler = {}
    for anahtar in config.ASSETS:
        haftalik = _gdelt_haftalik(anahtar, onbellek)
        if not haftalik:
            continue
        makaleler = [a for arts in haftalik.values() for a in arts]
        haftalar = sorted(haftalik.keys())
        bas = datetime.fromisoformat(haftalar[0]).replace(tzinfo=timezone.utc) - timedelta(days=6)
        son = datetime.fromisoformat(haftalar[-1]).replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc)
        params = _varlik_parametresi(opt, anahtar)
        gunluk = index_builder.build_daily_index_series(makaleler, params, bas, son)
        if not gunluk:
            continue
        s = pd.Series(gunluk)
        s.index = pd.to_datetime(s.index)
        seriler[anahtar] = s.sort_index()
    return seriler


def rejim_ozeti(seriler=None):
    """Rejim dedektorunun guncel ciktisi: sepet spread'i, ortalama korelasyon,
    PCA birinci bilesen payi ve rejim sinifi.

    - Sepet spread = ort(guvenli liman duyarliligi) - ort(risk varligi duyarliligi),
      20 gunluk yuvarlanan ortalama. > +0.15 Risk-Off, < -0.10 Risk-On.
    - Ortalama korelasyon = 20 gunluk pencerede tum varlik ciftlerinin
      duyarlilik korelasyonlarinin ortalamasi.
    - PC1 payi = son 60 gunluk (yon-birlestirilmis) duyarlilik matrisinde
      birinci temel bilesenin acikladigi varyans orani.
    """
    import numpy as np
    import regime_detector

    if seriler is None:
        seriler = duyarlilik_matrisi()
    if len(seriler) < 3:
        raise ValueError("Rejim icin en az 3 varligin gunluk serisi gerekli")

    sonuc = regime_detector.compute_regime(seriler)

    ort_kor = 0.0
    if len(sonuc["avg_corr_series"]) > 0:
        ort_kor = float(sonuc["avg_corr_series"].iloc[-1])

    # PC1 payi: son 60 gun, USDXXX yonu birlestirilmis matris
    birlesik = regime_detector.build_sentiment_matrix(seriler, unify_direction=True)
    pencere = birlesik.iloc[-60:].dropna(axis=1, how="any")
    pc1_pay = 0.0
    if pencere.shape[1] >= 3 and len(pencere) >= 10:
        try:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=1).fit(pencere.values)
            pc1_pay = float(pca.explained_variance_ratio_[0])
        except Exception:
            ozdegerler = np.linalg.eigvalsh(np.cov(pencere.values.T))
            pc1_pay = float(ozdegerler.max() / ozdegerler.sum())

    son_gun = None
    for s in seriler.values():
        u = s.index.max()
        son_gun = u if son_gun is None or u > son_gun else son_gun

    return {
        "label": sonuc["regime"],
        "basket_spread": round(float(sonuc["basket_spread"]), 4),
        "avg_correlation": round(ort_kor, 4),
        "pc1_share": round(pc1_pay, 4),
        "as_of": son_gun.strftime("%Y-%m-%d") if son_gun is not None else None,
        "n_assets": len(seriler),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Grafikler
# ═══════════════════════════════════════════════════════════════════════════════

def ciz_tarihce(tarihce, cikti_yolu):
    """Her parite bir cizgi; y=0 referans, +-0.3/+-0.7 kategori bantlari."""
    # parite -> (x, y) serileri
    # Eksen VERI saatinde, kosu saatinde degil. Onceden x = snapshot'in
    # `timestamp`i idi: 26.08 Carsamba 22:44'te kosan bir olcum eksende
    # 26.08 gorunuyor, ama ayni sayfadaki rejim/korelasyon panelleri
    # "veri sonu 23.08" diyordu. Ayni hatta iki tarih, ikisi de dogru,
    # hicbiri hangi saatin hangisi oldugunu soylemiyordu. Artik nokta kendi
    # veri ucunda durur; kosu zamani hover'a yazilir.
    seriler = {}
    for kayit in tarihce:
        gun = _snapshot_saati(kayit)
        kosu = (kayit.get("timestamp") or "")[:16].replace("T", " ")
        kaydedilmis = bool(kayit.get("veri_sonu"))
        for parite, veri in kayit.get("indices", {}).items():
            seriler.setdefault(parite, {"x": [], "y": [], "c": []})
            seriler[parite]["x"].append(gun)
            seriler[parite]["y"].append(veri.get("value"))
            seriler[parite]["c"].append([
                kosu + " UTC",
                "veri ucu" if kaydedilmis else "veri ucu kaydedilmemis - kosu gunu",
            ])

    # Eksen siniri: endeks tipik olarak [-1, 1] ama tasarsa genislet
    tum_degerler = [d for s in seriler.values() for d in s["y"] if d is not None]
    sinir = max(1.0, max(abs(d) for d in tum_degerler)) * 1.05

    fig = go.Figure()
    for i, (parite, s) in enumerate(sorted(seriler.items())):
        fig.add_trace(go.Scatter(
            x=s["x"], y=s["y"],
            mode="lines+markers",
            name=_gorunen_ad(parite),
            line=dict(width=1.8, color=CIZGI_RENKLERI[i % len(CIZGI_RENKLERI)]),
            marker=dict(size=4),
            customdata=s["c"],
            hovertemplate=("%{y:+.4f}"
                           "<br><span style='font-size:11px'>%{customdata[1]}: "
                           "%{x}<br>koşu: %{customdata[0]}</span>"),
        ))

    # Kategori bantlari: soluk yatay bolgeler
    bantlar = [
        (ESIK_1, ESIK_2, TEAL, 0.06),      # Bullish
        (ESIK_2, sinir, TEAL, 0.12),       # Extremely Bullish
        (-ESIK_2, -ESIK_1, CLARET, 0.06),  # Bearish
        (-sinir, -ESIK_2, CLARET, 0.12),   # Extremely Bearish
    ]
    for y0, y1, renk, opaklik in bantlar:
        fig.add_hrect(y0=y0, y1=y1, fillcolor=renk, opacity=opaklik,
                      line_width=0, layer="below")

    # y=0 referans cizgisi
    fig.add_hline(y=0, line_color=INK, line_width=1, opacity=0.5)
    # Esik cizgileri (ince, kesikli)
    for esik in (ESIK_1, ESIK_2, -ESIK_1, -ESIK_2):
        fig.add_hline(y=esik, line_color=INK, line_width=0.5,
                      line_dash="dot", opacity=0.25)

    _ortak_stil(fig, "FX haber-duyarlılık endeksi — tarihçe"
                "<br><span style='font-size:11.5px;color:#6b6b6b'>"
                "Yatay eksen her koşunun VERİ ucu (endekse giren en yeni haberin "
                "günü), koşunun saati değil. Rejim ve korelasyon panelleri ayrı "
                "bir kaynaktan (GDELT haftalık önbelleği) gelir ve son TAM "
                "haftada biter; o yüzden onların tarihi buradakinden birkaç gün "
                "geride olabilir.</span>")
    fig.update_layout(hovermode="x unified", margin=dict(l=60, r=30, t=96, b=60))
    fig.update_yaxes(title_text="Endeks değeri", range=[-sinir, sinir])
    fig.update_xaxes(title_text=None)

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def ciz_son_snapshot(tarihce, cikti_yolu):
    """Son snapshot: degere gore sirali yatay bar + kategori etiketi.
    Hover'da varligin okumaya giren skorlanmis makale sayisi da gosterilir
    (data/sentiment_scores.json; dashboard Overview'daki makale sayaci)."""
    son = tarihce[-1]
    ts = son.get("timestamp", "")
    kayitlar = sorted(son.get("indices", {}).items(),
                      key=lambda kv: kv[1].get("value", 0))
    makale_sayisi = _makale_sayilari()

    adlar = [_gorunen_ad(k) for k, _ in kayitlar]
    degerler = [v.get("value", 0) for _, v in kayitlar]
    kategoriler = [KATEGORI_TR.get(v.get("category", ""), v.get("category", ""))
                   for _, v in kayitlar]
    makaleler = [(f"{makale_sayisi[k]} makale" if makale_sayisi.get(k) else "")
                 for k, _ in kayitlar]
    renkler = [TEAL if d >= 0 else CLARET for d in degerler]
    etiketler = [f"{d:+.2f}  {k}" for d, k in zip(degerler, kategoriler)]
    # Etiket kirpilmasi duzeltmesi: asiri (uzun) barlarda etiket bar ICINE
    # (beyaz) yazilir; kisa barlarda disarida kalir. Boylece en negatif
    # barlarin "Asiri Satici" metni sol kenardan tasip eksen adlarina binmez.
    konumlar = ["inside" if abs(d) >= 0.5 else "outside" for d in degerler]

    fig = go.Figure(go.Bar(
        x=degerler, y=adlar,
        orientation="h",
        marker=dict(color=renkler),
        text=etiketler,
        textposition=konumlar,
        textfont=dict(size=11),
        insidetextfont=dict(color="#ffffff"),
        insidetextanchor="middle",
        cliponaxis=False,  # etiket eksen sinirina tasarsa kirpilmasin
        customdata=list(zip(kategoriler, makaleler)),
        hovertemplate=("%{y}: %{x:+.4f} (%{customdata[0]})"
                       "<br>%{customdata[1]}<extra></extra>"),
        showlegend=False,
    ))

    fig.add_vline(x=0, line_color=INK, line_width=1, opacity=0.5)

    # Baslikta ONCE veri ucu, SONRA kosu saati. Eskiden yalniz kosu saati
    # yaziyordu ve okur onu veri tarihi saniyordu.
    kosu = ts[:16].replace("T", " ") if ts else ""
    uc = _son_kosunun_veri_ucu(son)
    uc_yazi = ".".join(reversed(str(uc)[:10].split("-"))) if uc else ""
    alt = (f"Veri ucu {uc_yazi} · koşu {kosu} UTC" if uc_yazi
           else f"Koşu {kosu} UTC · bu koşu veri ucunu kaydetmemiş")
    _ortak_stil(fig, "FX haber-duyarlılık endeksi — son okuma"
                f"<br><span style='font-size:11.5px;color:#6b6b6b'>{alt}</span>")
    fig.update_layout(
        height=max(420, 34 * len(adlar) + 120),
        margin=dict(l=90, r=140, t=82, b=40),
    )
    # Dis etiketlere (deger + kategori) yer birakmak icin genis sinir
    sinir = max(1.0, max(abs(d) for d in degerler)) * 1.35
    fig.update_xaxes(title_text="Endeks değeri", range=[-sinir, sinir])
    fig.update_yaxes(gridcolor="#ffffff")

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def ciz_optimizasyon(cikti_yolu):
    """Varlik basina optimizasyonun ulastigi korelasyon (sirali yatay bar).

    Kaynak: data/optimized_params.json. Bar = optimizasyon hedefi olan
    20 gunluk yuvarlanan korelasyonun ortalamasi (gunluk duyarlilik vs
    5 gunluk ileri getiri). Hover'da secilen parametreler.
    """
    with open(config.OPTIMIZED_PARAMS, "r", encoding="utf-8") as f:
        veri = json.load(f)

    kayitlar = []
    for anahtar, v in veri.items():
        params = v.get("params", {})
        kor = v.get("rolling_mean")
        ufuk = v.get("return_col", "")
        if kor is None:  # dual-format yedegi
            kor = max(v.get("rolling_mean_1d", 0.0), v.get("rolling_mean_5d", 0.0))
            ufuk = v.get("best_return_col", ufuk)
        detay = (
            f"yöntem: {params.get('aggregation', '?')}"
            f"<br>half-life: {params.get('time_decay_halflife', '?')} gün"
            f" · lag: {params.get('lag_days', '?')} gün"
            f"<br>transform: {params.get('score_transform', '?')}"
            f" · nötr filtre: {params.get('neutral_filter', '?')}"
            f"<br>momentum ağırlığı: {params.get('momentum_weight', '?')}"
            f"<br>getiri ufku: {ufuk.replace('Return_', '')}"
        )
        spearman = v.get("in_sample_spearman")
        if spearman is not None:
            detay += f" · Spearman (IS): {spearman:+.4f}"
        kayitlar.append((anahtar, float(kor), detay))

    if not kayitlar:
        raise ValueError(f"Bos optimizasyon dosyasi: {config.OPTIMIZED_PARAMS}")

    kayitlar.sort(key=lambda k: k[1])
    adlar = [_gorunen_ad(k) for k, _, _ in kayitlar]
    degerler = [d for _, d, _ in kayitlar]
    detaylar = [t for _, _, t in kayitlar]
    renkler = [TEAL if d >= 0 else CLARET for d in degerler]

    fig = go.Figure(go.Bar(
        x=degerler, y=adlar,
        orientation="h",
        marker=dict(color=renkler),
        text=[f"{d:+.3f}" for d in degerler],
        textposition="outside",
        textfont=dict(size=11),
        cliponaxis=False,
        customdata=detaylar,
        hovertemplate="<b>%{y}</b>: %{x:+.4f}<br>%{customdata}<extra></extra>",
        showlegend=False,
    ))
    fig.add_vline(x=0, line_color=INK, line_width=1, opacity=0.5)

    _ortak_stil(fig, "Parametre optimizasyonu — varlık başına korelasyon")
    fig.update_layout(
        height=max(420, 34 * len(adlar) + 120),
        margin=dict(l=110, r=70, t=60, b=60),
    )
    alt = min(0.0, min(degerler)) - 0.05
    ust = max(degerler) * 1.25 + 0.02
    fig.update_xaxes(
        title_text="20 günlük yuvarlanan korelasyonun ortalaması (duyarlılık → 5g getiri)",
        range=[alt, ust])
    fig.update_yaxes(gridcolor="#ffffff")

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def ciz_rejim(ozet, cikti_yolu):
    """Rejim dedektoru: sepet spread'i, ortalama korelasyon, PC1 payi —
    uc etiketli yatay bar (her biri kendi ekseninde, sifir tabanli);
    rejim sinifi baslik altinda."""
    from plotly.subplots import make_subplots

    spread = ozet["basket_spread"]
    ort_kor = ozet["avg_correlation"]
    pc1 = ozet["pc1_share"]
    rejim = ozet["label"]
    renk = REJIM_RENK.get(rejim, GRI)
    risk_off = config.REGIME_THRESHOLDS["risk_off"]
    risk_on = config.REGIME_THRESHOLDS["risk_on"]

    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.12)

    def _bar(satir, deger, bar_renk, metin, hover):
        fig.add_trace(go.Bar(
            x=[deger], y=[""], orientation="h",
            marker=dict(color=bar_renk),
            width=0.55,
            text=[metin], textposition="outside",
            textfont=dict(size=15, color=INK),
            cliponaxis=False,
            hovertemplate=hover + "<extra></extra>",
            showlegend=False,
        ), row=satir, col=1)

    # Once barlar (bos subplot'a eklenen shape'leri plotly sessizce dusurur;
    # bu yuzden vrect/vline'lar barlardan SONRA eklenir)
    # 1) Sepet spread'i — rejim sinyalinin kendisi
    aralik = max(0.5, abs(spread) * 1.3)
    _bar(1, spread, renk, f"{spread:+.3f}",
         f"Sepet spread'i: {spread:+.4f}<br>"
         f"güvenli liman ort. − risk varlığı ort. (20g yuvarlanan)")
    fig.update_xaxes(range=[-aralik, aralik], tickformat="+.2f", row=1, col=1)

    # 2) Ortalama ikili korelasyon (20 gunluk pencere)
    _bar(2, ort_kor, TEAL if ort_kor >= 0 else CLARET, f"{ort_kor:+.3f}",
         f"Ortalama ikili korelasyon: {ort_kor:+.4f}<br>"
         f"tüm varlık çiftleri, 20 günlük pencere")
    fig.update_xaxes(range=[-1, 1], tickformat="+.1f", row=2, col=1)

    # 3) PCA birinci bilesen payi (aciklanan varyans)
    _bar(3, pc1 * 100, "#b8860b", f"{pc1 * 100:.1f}%",
         f"PC1 açıklanan varyans payı: {pc1:.1%}<br>"
         f"son 60 gün, yön-birleştirilmiş duyarlılık matrisi")
    fig.update_xaxes(range=[0, 100], ticksuffix="%", row=3, col=1)

    # Esik bolgeleri ve cizgiler
    fig.add_vrect(x0=-aralik, x1=risk_on, fillcolor=TEAL, opacity=0.10,
                  line_width=0, layer="below", row=1, col=1)
    fig.add_vrect(x0=risk_on, x1=risk_off, fillcolor="#000000", opacity=0.04,
                  line_width=0, layer="below", row=1, col=1)
    fig.add_vrect(x0=risk_off, x1=aralik, fillcolor=CLARET, opacity=0.10,
                  line_width=0, layer="below", row=1, col=1)
    for esik in (risk_on, risk_off):
        fig.add_vline(x=esik, line_color=INK, line_width=0.8, line_dash="dot",
                      opacity=0.4, row=1, col=1)
    fig.add_vline(x=50, line_color=INK, line_width=0.8, line_dash="dot",
                  opacity=0.4, row=3, col=1)

    # Sifir cizgileri (spread ve korelasyon eksenleri)
    for satir in (1, 2):
        fig.add_vline(x=0, line_color=INK, line_width=1, opacity=0.5,
                      row=satir, col=1)

    # Satir alanlarini asagi sikistir; ustte rejim yazisina yer birak
    alanlar = [(0.63, 0.76), (0.36, 0.49), (0.09, 0.22)]
    for i, (alt, ust) in enumerate(alanlar):
        eksen = "yaxis" if i == 0 else f"yaxis{i + 1}"
        fig.layout[eksen].domain = [alt, ust]
        fig.layout[eksen].showticklabels = False

    # Satir basliklari (bar adlari + kisa aciklama)
    basliklar = [
        ("<b>Sepet spread'i</b>  <span style='font-size:11px;color:#6b6355'>"
         "güvenli liman − risk, 20g yuvarlanan ort.</span>", alanlar[0][1]),
        ("<b>Ortalama korelasyon</b>  <span style='font-size:11px;color:#6b6355'>"
         "varlık çiftleri, 20g pencere</span>", alanlar[1][1]),
        ("<b>PC1 payı</b>  <span style='font-size:11px;color:#6b6355'>"
         "açıklanan varyans, son 60 gün</span>", alanlar[2][1]),
    ]
    for metin, ust in basliklar:
        fig.add_annotation(x=0.0, y=ust + 0.02, xref="paper", yref="paper",
                           xanchor="left", yanchor="bottom", showarrow=False,
                           text=metin, font=dict(size=13, color=INK))

    # Rejim sinifi — baslik altinda
    fig.add_annotation(
        x=0.0, y=0.99, xref="paper", yref="paper",
        xanchor="left", yanchor="top", showarrow=False, align="left",
        text=(f"Rejim: <b><span style='color:{renk}'>{REJIM_TR.get(rejim, rejim)}</span></b>"
              f"<br><span style='font-size:11px;color:#6b6355'>"
              f"eşikler: spread &gt; {risk_off:+.2f} → Risk-Off · "
              f"spread &lt; {risk_on:+.2f} → Risk-On · arası Geçiş</span>"
              f"<br><span style='font-size:11px;color:#6b6355'>"
              f"{ozet.get('n_assets', '?')} varlık · veri sonu {ozet.get('as_of', '?')}</span>"),
        font=dict(size=15, color=INK),
    )

    tarih = ozet.get("as_of") or ""
    _ortak_stil(fig, f"Rejim dedektörü — güncel okuma ({tarih})")
    fig.update_layout(height=560, margin=dict(l=30, r=70, t=60, b=40),
                      bargap=0)

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def ciz_duyarlilik_getiri(cikti_yolu):
    """Varlik basina 'haftalik duyarlilik vs izleyen 5 is gunu getirisi' sacilimi.

    x = o haftanin duyarlilik endeksi (gdelt onbellegi, hafta sonu itibariyla,
    look-ahead yok); y = hafta kapanisindan sonraki 5 islem gununun yuzde
    getirisi (yfinance gunluk kapanis). Varlik secimi dropdown ile; her varlikta
    OLS trend dogrusu ve Pearson korelasyonu + n annotation'i.
    Dondurulen ikinci deger: {varlik: (r, n)} korelasyon ozeti.
    """
    import numpy as np
    import pandas as pd
    import yfinance as yf
    from scipy import stats

    seriler = haftalik_seriler()
    if not seriler:
        raise ValueError("Haftalik duyarlilik serisi kurulamadi (gdelt onbellegi bos?)")

    fig = go.Figure()
    varliklar = []       # cizilen varliklar (sirali)
    anotasyonlar = {}    # varlik -> annotation dict
    kor_ozet = {}        # varlik -> (pearson_r, n)
    atlananlar = []

    for anahtar, seri in seriler.items():
        ad = _gorunen_ad(anahtar)
        ticker = config.ASSETS[anahtar]["ticker"]
        haftalar_tum = sorted(seri.keys())
        try:
            bas = (datetime.fromisoformat(haftalar_tum[0]) - timedelta(days=10)).strftime("%Y-%m-%d")
            son = (datetime.fromisoformat(haftalar_tum[-1]) + timedelta(days=20)).strftime("%Y-%m-%d")
            fdf = yf.download(ticker, start=bas, end=son, auto_adjust=True, progress=False)
        except Exception as exc:
            print(f"  UYARI: {anahtar} fiyati cekilemedi ({exc}); atlandi")
            atlananlar.append(anahtar)
            continue
        if fdf is None or fdf.empty:
            print(f"  UYARI: {anahtar} icin bos fiyat verisi; atlandi")
            atlananlar.append(anahtar)
            continue
        if isinstance(fdf.columns, pd.MultiIndex):
            fdf.columns = fdf.columns.get_level_values(0)
        kapanis = fdf["Close"].ffill()

        x, y, hafta_etiket = [], [], []
        for hafta in haftalar_tum:
            duy = seri[hafta]
            # hafta sonu (Pazar) itibariyla son kapanis = o haftanin Cuma'si
            poz = int(kapanis.index.searchsorted(pd.Timestamp(hafta), side="right")) - 1
            if poz < 0 or poz + 5 >= len(kapanis):
                continue  # ileri getiri henuz olusmadi
            taban = float(kapanis.iloc[poz])
            ileri = float(kapanis.iloc[poz + 5])
            if taban == 0:
                continue
            x.append(duy)
            y.append((ileri / taban - 1.0) * 100.0)
            hafta_etiket.append(hafta)

        if len(x) < 10:
            print(f"  UYARI: {anahtar} icin yetersiz eslesme (n={len(x)}); atlandi")
            atlananlar.append(anahtar)
            continue

        r, p = stats.pearsonr(x, y)
        egim, kesisim = np.polyfit(x, y, 1)
        xs = [min(x), max(x)]
        ys = [egim * v + kesisim for v in xs]
        kor_ozet[anahtar] = (round(float(r), 4), len(x))

        gorunur = len(varliklar) == 0  # ilk varlik acilista gorunur
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="markers",
            name="Haftalık gözlem",
            marker=dict(size=8, color=TEAL, opacity=0.7,
                        line=dict(width=0.5, color="#ffffff")),
            customdata=hafta_etiket,
            hovertemplate=("hafta sonu %{customdata}<br>duyarlılık: %{x:+.3f}"
                           "<br>izleyen 5 gün: %{y:+.2f}%<extra></extra>"),
            visible=gorunur,
        ))
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines",
            name="OLS trend",
            line=dict(color=CLARET, width=2, dash="dash"),
            hoverinfo="skip",
            visible=gorunur,
        ))
        anotasyonlar[anahtar] = dict(
            x=0.99, y=0.98, xref="paper", yref="paper",
            xanchor="right", yanchor="top", showarrow=False, align="right",
            text=(f"<b>{ad}</b><br>Pearson r = {r:+.3f} (p = {p:.3f})"
                  f"<br>n = {len(x)} hafta · eğim = {egim:+.2f}"),
            font=dict(size=12, color=INK),
            bgcolor="rgba(255,255,255,0.85)", bordercolor=GRID, borderwidth=1,
        )
        varliklar.append(anahtar)

    if not varliklar:
        raise ValueError("Hicbir varlik icin fiyat verisi cekilemedi")

    # Dropdown: her varlik icin 2 trace (sacilim + trend) gorunurlugu
    dugmeler = []
    for i, anahtar in enumerate(varliklar):
        gorunurluk = [False] * (2 * len(varliklar))
        gorunurluk[2 * i] = gorunurluk[2 * i + 1] = True
        dugmeler.append(dict(
            label=_gorunen_ad(anahtar),
            method="update",
            args=[{"visible": gorunurluk},
                  {"annotations": [anotasyonlar[anahtar]]}],
        ))

    ilk = varliklar[0]
    _ortak_stil(fig, "Duyarlılık vs 5 günlük ileri getiri — haftalık")
    fig.update_layout(
        height=520,
        annotations=[anotasyonlar[ilk]],
        updatemenus=[dict(
            buttons=dugmeler, direction="down",
            x=0.99, xanchor="right", y=1.12, yanchor="top",
            bgcolor="#ffffff", bordercolor=GRID,
            font=dict(size=12, color=INK),
        )],
        margin=dict(l=60, r=30, t=70, b=70),
    )
    fig.add_hline(y=0, line_color=INK, line_width=0.8, opacity=0.35)
    fig.add_vline(x=0, line_color=INK, line_width=0.8, opacity=0.35)
    fig.update_xaxes(title_text="Haftalık duyarlılık endeksi")
    fig.update_yaxes(title_text="İzleyen 5 iş günü getirisi (%)")

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    if atlananlar:
        print(f"  Not: fiyat verisi olmayan varliklar atlandi: {', '.join(atlananlar)}")
    return cikti_yolu, kor_ozet


def ciz_fiyat_endeks(cikti_yolu, seriler=None):
    """Varlik basina 'fiyat + gunluk duyarlilik' cift eksenli grafik.

    Dashboard'daki 'Price vs Daily Sentiment' panelinin web karsiligi:
    sol eksende gunluk kapanis fiyati (cizgi), sag eksende [-1,1] araliginda
    gunluk duyarlilik endeksi (isarete gore renkli bar). Varlik dropdown ile
    secilir. seriler verilmezse duyarlilik_matrisi() ile hesaplanir (agir).
    """
    import pandas as pd
    import yfinance as yf
    from plotly.subplots import make_subplots

    if seriler is None:
        seriler = duyarlilik_matrisi()
    if not seriler:
        raise ValueError("Gunluk duyarlilik matrisi bos (gdelt onbellegi?)")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    varliklar = []
    atlananlar = []

    for anahtar, seri in seriler.items():
        ad = _gorunen_ad(anahtar)
        ticker = config.ASSETS[anahtar]["ticker"]
        try:
            bas = (seri.index.min() - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            son = (seri.index.max() + pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            fdf = yf.download(ticker, start=bas, end=son, auto_adjust=True, progress=False)
        except Exception as exc:
            print(f"  UYARI: {anahtar} fiyati cekilemedi ({exc}); atlandi")
            atlananlar.append(anahtar)
            continue
        if fdf is None or fdf.empty:
            atlananlar.append(anahtar)
            continue
        if isinstance(fdf.columns, pd.MultiIndex):
            fdf.columns = fdf.columns.get_level_values(0)
        kapanis = fdf["Close"].ffill()

        gorunur = len(varliklar) == 0
        fig.add_trace(go.Scatter(
            x=kapanis.index, y=kapanis.values, mode="lines",
            name=f"{ad} fiyat", line=dict(color=INK, width=1.8),
            hovertemplate="%{x|%d.%m.%Y}<br>fiyat: %{y:.4f}<extra></extra>",
            visible=gorunur,
        ), secondary_y=False)
        renkler = [TEAL if v >= 0 else CLARET for v in seri.values]
        fig.add_trace(go.Bar(
            x=seri.index, y=seri.values,
            name="Günlük duyarlılık", marker_color=renkler, opacity=0.55,
            hovertemplate="%{x|%d.%m.%Y}<br>duyarlılık: %{y:+.3f}<extra></extra>",
            visible=gorunur,
        ), secondary_y=True)
        varliklar.append(anahtar)

    if not varliklar:
        raise ValueError("Hicbir varlik icin fiyat verisi cekilemedi")

    dugmeler = []
    for i, anahtar in enumerate(varliklar):
        gorunurluk = [False] * (2 * len(varliklar))
        gorunurluk[2 * i] = gorunurluk[2 * i + 1] = True
        dugmeler.append(dict(
            label=_gorunen_ad(anahtar), method="update",
            args=[{"visible": gorunurluk}],
        ))

    _ortak_stil(fig, "Fiyat vs günlük haber duyarlılığı")
    fig.update_layout(
        height=520,
        updatemenus=[dict(
            buttons=dugmeler, direction="down",
            x=0.99, xanchor="right", y=1.12, yanchor="top",
            bgcolor="#ffffff", bordercolor=GRID,
            font=dict(size=12, color=INK),
        )],
        margin=dict(l=60, r=60, t=70, b=70),
        bargap=0.15,
    )
    fig.update_yaxes(title_text="Fiyat (günlük kapanış)", secondary_y=False)
    fig.update_yaxes(title_text="Duyarlılık endeksi", range=[-1, 1],
                     secondary_y=True, showgrid=False, zeroline=True,
                     zerolinecolor=GRID)

    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    if atlananlar:
        print(f"  Not: fiyat verisi olmayan varliklar atlandi: {', '.join(atlananlar)}")
    return cikti_yolu


def ciz_rejim_tarihce(seriler, cikti_yolu):
    """Rejim bilesenlerinin TARIHCESI: sepet spread'i (+ rejim bantlari),
    yon-birlestirilmis ortalama korelasyon ve PC1 faktor serisi — 3 panel."""
    from plotly.subplots import make_subplots
    import regime_detector

    sonuc = regime_detector.compute_regime(seriler)
    spread = sonuc["basket_spread_series"].dropna()
    kor = sonuc["avg_corr_series"].dropna()
    pc1 = sonuc["pc1_series"].dropna()

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
        subplot_titles=("Risk-Off sepet spread'i (20g, yön-birleştirilmiş)",
                        "Ortalama çapraz duyarlılık korelasyonu (20g, yön-birleştirilmiş)",
                        "PC1 — piyasa geneli duyarlılık faktörü (60g)"))

    t = config.REGIME_THRESHOLDS
    fig.add_trace(go.Scatter(x=spread.index, y=spread.values, mode="lines",
                             name="Sepet spread", line=dict(color=INK, width=1.8),
                             hovertemplate="%{x|%d.%m.%Y}<br>spread: %{y:+.3f}<extra></extra>"),
                  row=1, col=1)
    fig.add_hline(y=t["risk_off"], line_dash="dot", line_color=CLARET,
                  annotation_text="Risk-Off eşiği", annotation_font_size=10, row=1, col=1)
    fig.add_hline(y=t["risk_on"], line_dash="dot", line_color=TEAL,
                  annotation_text="Risk-On eşiği", annotation_font_size=10, row=1, col=1)
    fig.add_hrect(y0=t["risk_off"], y1=max(float(spread.max()), t["risk_off"]) + 0.05,
                  fillcolor=CLARET, opacity=0.06, line_width=0, row=1, col=1)
    fig.add_hrect(y0=min(float(spread.min()), t["risk_on"]) - 0.05, y1=t["risk_on"],
                  fillcolor=TEAL, opacity=0.06, line_width=0, row=1, col=1)

    fig.add_trace(go.Scatter(x=kor.index, y=kor.values, mode="lines",
                             name="Ort. korelasyon", line=dict(color=GOLD, width=1.8),
                             hovertemplate="%{x|%d.%m.%Y}<br>ort. korelasyon: %{y:+.3f}<extra></extra>"),
                  row=2, col=1)
    fig.add_hline(y=0, line_color=GRID, row=2, col=1)

    fig.add_trace(go.Scatter(x=pc1.index, y=pc1.values, mode="lines",
                             name="PC1 skoru", line=dict(color=TEAL, width=1.8),
                             hovertemplate="%{x|%d.%m.%Y}<br>PC1: %{y:+.3f}<extra></extra>"),
                  row=3, col=1)
    fig.add_hline(y=0, line_color=GRID, row=3, col=1)

    _ortak_stil(fig, "Rejim bileşenlerinin tarihçesi")
    fig.update_layout(height=760, showlegend=False,
                      margin=dict(l=60, r=30, t=70, b=50))
    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def ciz_korelasyon_matrisi(seriler, cikti_yolu):
    """Capraz duyarlilik korelasyon isi haritasi (son 20 gun,
    yon-birlestirilmis matris; terslenen varliklar * ile isaretli)."""
    import regime_detector

    sonuc = regime_detector.compute_regime(seriler)
    hm = sonuc["heatmap"]
    etiket = [(_gorunen_ad(k) + (" *" if k in config.PC1_INVERT_ASSETS else ""))
              for k in hm.columns]

    fig = go.Figure(go.Heatmap(
        z=hm.values.round(2), x=etiket, y=etiket,
        colorscale=[[0, CLARET], [0.5, "#ffffff"], [1, TEAL]],
        zmin=-1, zmax=1, text=hm.values.round(2), texttemplate="%{text}",
        textfont=dict(size=9), colorbar=dict(title="r"),
        hovertemplate="%{y} × %{x}: %{z:+.2f}<extra></extra>"))
    _ortak_stil(fig, "Çapraz duyarlılık korelasyonları — son 20 gün")
    fig.update_layout(height=640, margin=dict(l=110, r=40, t=70, b=110))
    fig.add_annotation(x=0, y=-0.22, xref="paper", yref="paper", showarrow=False,
                       xanchor="left", font=dict(size=11, color=GRI),
                       text="* USD-bazlı parite terslenmiştir (ortak makro yön: USD zayıf = pozitif)")
    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


def ciz_yuvarlanan_korelasyon(seriler, cikti_yolu):
    """Varlik basina YUVARLANAN 20 gunluk korelasyon — IKI getiri ufku:
    gunluk duyarlilik vs izleyen 1 is gunu VE izleyen 5 is gunu getirisi.

    Dashboard Correlation sekmesindeki 1g/5g tablolarinin ve 1g-vs-5g
    karsilastirmasinin web karsiligi: her varlikta iki cizgi (1g altin,
    5g petrol yesili), varlik secimi dropdown ile. Dondurulen ikinci deger
    {varlik: {"1g": ort, "5g": ort}} — 20g yuvarlanan korelasyon ortalamalari.
    """
    import pandas as pd
    import yfinance as yf

    UFUKLAR = [(1, "1 günlük ileri getiri", GOLD, "dot"),
               (5, "5 günlük ileri getiri", TEAL, "solid")]

    fig = go.Figure()
    varliklar = []
    ort_ozet = {}
    for anahtar, seri in seriler.items():
        ticker = config.ASSETS[anahtar]["ticker"]
        try:
            bas = (seri.index.min() - pd.Timedelta(days=5)).strftime("%Y-%m-%d")
            son = (seri.index.max() + pd.Timedelta(days=15)).strftime("%Y-%m-%d")
            fdf = yf.download(ticker, start=bas, end=son, auto_adjust=True, progress=False)
        except Exception:
            continue
        if fdf is None or fdf.empty:
            continue
        if isinstance(fdf.columns, pd.MultiIndex):
            fdf.columns = fdf.columns.get_level_values(0)
        kapanis = fdf["Close"].ffill()

        yuvlar = {}
        for gun, _, _, _ in UFUKLAR:
            ileri = kapanis.shift(-gun) / kapanis - 1.0
            birlesik = (pd.DataFrame({"duy": seri})
                        .join(ileri.rename("get"), how="inner").dropna())
            if len(birlesik) < 40:
                continue
            yuvlar[gun] = birlesik["duy"].rolling(20).corr(birlesik["get"]).dropna()
        if len(yuvlar) < len(UFUKLAR):
            continue  # iki ufuk da kurulamayan varlik atlanir

        gorunur = len(varliklar) == 0
        for gun, ad, renk, cizgi in UFUKLAR:
            yuv = yuvlar[gun]
            fig.add_trace(go.Scatter(
                x=yuv.index, y=yuv.values, mode="lines",
                name=ad, line=dict(color=renk, width=1.8, dash=cizgi),
                hovertemplate=("%{x|%d.%m.%Y}<br>20g korelasyon (" + f"{gun}g"
                               + "): %{y:+.3f}<extra></extra>"),
                visible=gorunur))
        ort_ozet[anahtar] = {f"{gun}g": round(float(yuvlar[gun].mean()), 4)
                             for gun, _, _, _ in UFUKLAR}
        varliklar.append(anahtar)

    if not varliklar:
        raise ValueError("Yuvarlanan korelasyon icin veri yok")

    n_ufuk = len(UFUKLAR)
    dugmeler = []
    for i, anahtar in enumerate(varliklar):
        gorunurluk = [False] * (n_ufuk * len(varliklar))
        for j in range(n_ufuk):
            gorunurluk[n_ufuk * i + j] = True
        dugmeler.append(dict(label=_gorunen_ad(anahtar), method="update",
                             args=[{"visible": gorunurluk}]))

    _ortak_stil(fig, "Yuvarlanan duyarlılık-getiri korelasyonu (20 gün) — 1g ve 5g ufuk")
    fig.update_layout(
        height=480,
        updatemenus=[dict(buttons=dugmeler, direction="down",
                          x=0.99, xanchor="right", y=1.14, yanchor="top",
                          bgcolor="#ffffff", bordercolor=GRID,
                          font=dict(size=12, color=INK))],
        margin=dict(l=60, r=30, t=70, b=80), showlegend=True)
    fig.add_hline(y=0, line_color=INK, line_width=0.8, opacity=0.35)
    fig.update_yaxes(title_text="Pearson r (20 günlük pencere)", range=[-1, 1])
    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu, ort_ozet


def ciz_son_mansetler(cikti_yolu, adet=40):
    """Son manşetler tablosu: varlık, başlık, FinBERT skoru, kaynak, tarih."""
    import sentiment_analyzer

    satirlar = []
    for anahtar in config.ASSETS:
        makaleler = sentiment_analyzer.load_scores(anahtar) or []
        for m in makaleler:
            if "score" not in m:
                continue
            satirlar.append({
                "varlik": _gorunen_ad(anahtar),
                "baslik": (m.get("title") or "")[:110],
                "skor": float(m["score"]),
                "kaynak": m.get("source", ""),
                "tarih": (m.get("published") or "")[:16].replace("T", " "),
            })
    if not satirlar:
        raise ValueError("Skorlanmis manset bulunamadi")
    satirlar.sort(key=lambda r: r["tarih"], reverse=True)
    satirlar = satirlar[:adet]

    renkler = [TEAL if r["skor"] > 0.05 else (CLARET if r["skor"] < -0.05 else GRI)
               for r in satirlar]
    fig = go.Figure(go.Table(
        columnwidth=[16, 60, 10, 14],
        header=dict(values=["<b>Varlık</b>", "<b>Başlık</b>", "<b>Skor</b>", "<b>Tarih</b>"],
                    fill_color=INK, font=dict(color="#f5f0e6", size=12), align="left",
                    height=30),
        cells=dict(
            values=[[r["varlik"] for r in satirlar],
                    [r["baslik"] for r in satirlar],
                    [f"{r['skor']:+.3f}" for r in satirlar],
                    [r["tarih"] for r in satirlar]],
            align="left", height=26,
            fill_color="#ffffff",
            font=dict(size=11.5, color=[[INK] * len(satirlar), [INK] * len(satirlar),
                                        renkler, [GRI] * len(satirlar)]))))
    _ortak_stil(fig, f"Son {len(satirlar)} manşet ve FinBERT skorları")
    fig.update_layout(height=30 + 30 + 26 * len(satirlar) + 90,
                      margin=dict(l=20, r=20, t=60, b=20))
    fig.write_html(cikti_yolu, include_plotlyjs="cdn")
    return cikti_yolu


# ═══════════════════════════════════════════════════════════════════════════════
# Uretim akisi
# ═══════════════════════════════════════════════════════════════════════════════

def uret(cikti_dizini=None, rejim=None, yalniz_anlik=False):
    """Tum HTML ciktilarini uret; uretilen dosya yollarini dondur.

    Hafif ciktilar (tarihce, son okuma, optimizasyon) internetsiz ve hizlidir.
    Agir adimlar opsiyoneldir: rejim (CPU-yogun gunluk matris) ve
    duyarlilik-getiri (yfinance) hatada atlanir, pipeline durmaz.
    rejim parametresi verilirse (run.py'den) matris yeniden hesaplanmaz.

    yalniz_anlik=True: YALNIZ anlik endeks grafikleri (tarihce + son okuma).
    Bu kip GUNLUK kosu icindir. Sayfanin geri kalani — rejim, korelasyon,
    fiyat-endeks, sacilim — GDELT haftalik arsivinden gelir ve o arsiv gun
    icinde ILERLEMEZ; onlari her gun yeniden cizmek hem dakikalar suren gunluk
    duyarlilik matrisini bosuna kosturur, hem de `rejim_ozet.json`i (sayfadaki
    "veri sonu" damgasi) degismeyen bir icerikle yeniden yazar. Haftalik saat,
    haftalik kosuda ilerler.
    """
    hedef = cikti_dizini or OUTPUT_DIR
    os.makedirs(hedef, exist_ok=True)
    tarihce = yukle_tarihce()
    if not tarihce:
        raise ValueError(f"Bos tarihce: {HISTORY_FILE}")
    yollar = [
        ciz_tarihce(tarihce, os.path.join(hedef, "endeks_tarihce.html")),
        ciz_son_snapshot(tarihce, os.path.join(hedef, "endeks_son.html")),
    ]
    if yalniz_anlik:
        return yollar

    try:
        yollar.append(ciz_optimizasyon(os.path.join(hedef, "optimizasyon.html")))
    except Exception as exc:
        print(f"UYARI: optimizasyon.html uretilemedi: {exc}")

    # gunluk duyarlilik matrisi agir — bir kez hesapla, rejim ve
    # fiyat+endeks grafigi paylassin
    matris = None
    try:
        matris = duyarlilik_matrisi()
    except Exception as exc:
        print(f"UYARI: gunluk duyarlilik matrisi kurulamadi: {exc}")

    try:
        ozet = rejim if rejim else rejim_ozeti(seriler=matris)
        print(f"  Rejim ozeti: {ozet['label']} | spread {ozet['basket_spread']:+.4f}"
              f" | ort. korelasyon {ozet['avg_correlation']:+.4f}"
              f" | PC1 payi {ozet['pc1_share']:.1%}"
              f" | {ozet.get('n_assets', '?')} varlik | veri sonu {ozet.get('as_of', '?')}")
        yollar.append(ciz_rejim(ozet, os.path.join(hedef, "rejim.html")))
        # Sayfa metnindeki "veri sonu" damgası buradan okunur (ozet_uret.py
        # birleştirir) — elle yazılmaz; önbellek ilerlemezse sayfada da ilerlemez.
        with open(os.path.join(hedef, "rejim_ozet.json"), "w", encoding="utf-8") as f:
            json.dump(ozet, f, ensure_ascii=False, indent=1)
    except Exception as exc:
        print(f"UYARI: rejim.html uretilemedi: {exc}")

    try:
        yollar.append(ciz_fiyat_endeks(
            os.path.join(hedef, "fiyat_endeks.html"), seriler=matris))
    except Exception as exc:
        print(f"UYARI: fiyat_endeks.html uretilemedi: {exc}")

    if matris:
        for ad, fn in [("rejim_tarihce.html", ciz_rejim_tarihce),
                       ("korelasyon_matrisi.html", ciz_korelasyon_matrisi)]:
            try:
                yollar.append(fn(matris, os.path.join(hedef, ad)))
            except Exception as exc:
                print(f"UYARI: {ad} uretilemedi: {exc}")
        try:
            yol, ort_ozet = ciz_yuvarlanan_korelasyon(
                matris, os.path.join(hedef, "yuvarlanan_korelasyon.html"))
            yollar.append(yol)
            print("  Yuvarlanan korelasyon ortalamalari (20g pencere ort.):")
            for anahtar, degerler in sorted(ort_ozet.items()):
                print(f"    {anahtar:<8} 1g {degerler['1g']:+.4f} | 5g {degerler['5g']:+.4f}")
        except Exception as exc:
            print(f"UYARI: yuvarlanan_korelasyon.html uretilemedi: {exc}")

    try:
        yollar.append(ciz_son_mansetler(os.path.join(hedef, "son_mansetler.html")))
    except Exception as exc:
        print(f"UYARI: son_mansetler.html uretilemedi: {exc}")

    try:
        yol, kor_ozet = ciz_duyarlilik_getiri(os.path.join(hedef, "duyarlilik_getiri.html"))
        yollar.append(yol)
        print("  Haftalik duyarlilik → 5g ileri getiri (Pearson r, n hafta):")
        for anahtar, (r, n) in sorted(kor_ozet.items()):
            print(f"    {anahtar:<8} r {r:+.4f} (n={n})")
    except Exception as exc:
        print(f"UYARI: duyarlilik_getiri.html uretilemedi: {exc}")

    return yollar


def main():
    import sys
    anlik = "--anlik" in sys.argv[1:]
    yollar = uret(yalniz_anlik=anlik)
    if anlik:
        print("  (anlik kip: yalniz endeks grafikleri; GDELT tabanli paneller "
              "haftalik kosuda tazelenir)")
    for yol in yollar:
        print(f"  Yazildi: {yol}")


if __name__ == "__main__":
    main()
