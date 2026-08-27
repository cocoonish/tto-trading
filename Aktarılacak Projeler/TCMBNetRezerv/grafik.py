"""TCMB rezerv hattının grafikleri (Plotly, ev stili).

Üretilen dosyalar (hepsi include_plotlyjs="cdn"):

  tcmb_rezerv_grafik.html  Swap hariç net rezerv (piyasa tanımı) + günlük değişim
  brut_kirilim.html        Brüt rezerv = altın + döviz (yığılı alan),
                           ikinci eksende altın fiyatı
  altin_ayristirma.html    Δ(swap hariç net) = net alım + altın miktar etkisi
                           + altın fiyat etkisi + kamu hareketi (+ swap çapa
                           revizyonu); kimliğin SOL TARAFI ayrı çizilir —
                           akım artık olarak tanımlı olduğu için kimliğin
                           kapanması bir doğrulama DEĞİLDİR
  akim.html                Günlük net döviz alımı/satımı (iki tanım) +
                           çıpadan birikimli; belirsizlik bantları ve geçici
                           (revize olacak) günler işaretli
  swap.html                Toplam swap stoku + yerli/yabancı kırılımı;
                           haftalık çapaya dayanan bölgeler gölgeli
  tanim_farki.html         Piyasa tanımı ile Stand-By 2A yan yana + fark alanı
                           + farkın yuvarlanan medyanı (fark sabit değildir)

Varsayılan olarak gunluk.csv + haftalik_rezerv.csv'den (çevrimdışı) koşar;
EVDS/PDF'ten taze veri çekmek için --online verin.

Kullanım:
  python grafik.py                          # CSV'lerden (çevrimdışı)
  python grafik.py --online                 # EVDS + IRFCL PDF'ten çek
  python grafik.py --start 01-01-2026       # belirli aralık
  python grafik.py --no-open                # tarayıcıda açma
  python grafik.py --sadece akim swap       # yalnız seçilen grafikler
"""

from __future__ import annotations

import argparse
import datetime as dt
import webbrowser
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import altin_etkisi

pd_notna = pd.notna

# Belirsizlik bantları TEK KAYNAKTAN gelir (altin_etkisi.py'deki hata
# bütçesi); grafikte yeniden yazılmaz ki sayfa ile grafik ayrışmasın.
AKIM_BANT_GUNLUK = altin_etkisi.AKIM_BANT_GUNLUK
AKIM_BANT_BIRIKIMLI = altin_etkisi.AKIM_BANT_BIRIKIMLI_6AY

# Ev paleti (site/src/styles/global.css ile uyumlu)
TEAL = "#1d5c5c"      # birincil seri
BORDO = "#8e1f2f"     # ikincil / negatif
ALTIN = "#9a7327"     # altın kalemleri ve vurgu
LACIVERT = "#2f4858"  # üçüncü seri (döviz bacağı)
KURSUNI = "#7a7266"   # nötr / "diğer" bileşen
TEAL_RGBA = "rgba(29,92,92,0.7)"
BORDO_RGBA = "rgba(142,31,47,0.7)"
ALTIN_RGBA = "rgba(154,115,39,0.55)"
LACIVERT_RGBA = "rgba(47,72,88,0.55)"
KURSUNI_RGBA = "rgba(122,114,102,0.65)"

IZGARA = "#ecf0f1"
SIFIR = "#7f8c8d"


def ev_duzeni(fig: go.Figure, baslik: str, yukseklik: int = 620) -> go.Figure:
    """Ev stili: başlık solda, lejant altta, beyaz zemin, responsive.

    site/tools/plotly_stil.py siteye kopyalanınca bunu bir kez daha uygular;
    burada da uygulanması, dosyanın tek başına açıldığında da düzgün
    görünmesini sağlar.
    """
    fig.update_layout(
        title=dict(text=baslik, x=0.01, xanchor="left", font=dict(size=16)),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left",
                    x=0),
        bargap=0.15,
        margin=dict(l=70, r=70, t=90, b=90),
        height=yukseklik,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
    )
    fig.update_xaxes(title_text="Tarih", showgrid=True, gridcolor=IZGARA,
                     hoverformat="%d %b %Y")
    return fig


def _sim_aralik(seri: pd.Series, pay: float = 0.08) -> list[float]:
    """Sıfır çizgisi iki eksende aynı piksele düşsün diye simetrik aralık."""
    v = seri.dropna()
    if v.empty:
        return [-1.0, 1.0]
    m = max(abs(float(v.min())), abs(float(v.max()))) * (1 + pay)
    return [-m, m] if m else [-1.0, 1.0]


def _son(seri: pd.Series):
    """Serinin son GEÇERLİ (tarih, değer) çifti; yoksa (None, None)."""
    g = seri.dropna()
    return (g.index[-1], g.iloc[-1]) if len(g) else (None, None)


# ---------------------------------------------------------------------------
# 01 — Swap hariç net rezerv + günlük değişim
# ---------------------------------------------------------------------------
def sekil_swap_haric(daily: pd.DataFrame) -> go.Figure:
    if "swap_haric_net_rezerv_usd" not in daily.columns:
        raise RuntimeError("swap_haric_net_rezerv_usd kolonu eksik "
                           "(önce net_rezerv.py koşturun)")
    d = daily.copy()
    d["delta"] = d["swap_haric_net_rezerv_usd"].diff()

    # Plotly hovertemplate zaman zaman tam hassasiyetli float basıyor;
    # yuvarlanmış kopya en garantili yol.
    sh = d["swap_haric_net_rezerv_usd"].round(2)
    delta = d["delta"].round(2)
    delta_metin = [f"{v:+.2f}" if pd_notna(v) else "" for v in delta]
    renkler = [TEAL_RGBA if (v is not None and v >= 0) else BORDO_RGBA
               for v in delta.fillna(0)]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=d.index, y=sh, mode="lines", name="Swap hariç net rezerv",
        line=dict(color=TEAL, width=2), connectgaps=False,
        hovertemplate="Swap hariç: <b>%{y:.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)

    # IRFCL gözlem noktaları: swap kaleminin YAYIMLANMIŞ olduğu tarihler.
    # Aradaki günlerde yabancı MB bacağı taşınıyor; okuyucu gerçek gözlem ile
    # taşınan değeri ayırt edebilsin diye işaretleniyor.
    if "swap_gozlem" in d.columns:
        gz = d.index[d["swap_gozlem"].astype(str).str.lower()
                     .isin(["true", "1"])]
        if len(gz):
            fig.add_trace(go.Scatter(
                x=gz, y=sh.reindex(gz), mode="markers",
                name="IRFCL gözlemi (swap verisi yayımlandı)",
                marker=dict(color=ALTIN, size=8, symbol="diamond",
                            line=dict(color="white", width=1)),
                hovertemplate="IRFCL gözlemi: <b>%{y:.2f}</b> mlr USD"
                              "<extra></extra>",
            ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=d.index, y=delta, text=delta_metin, textposition="none",
        name="Günlük değişim", marker_color=renkler, opacity=0.6,
        hovertemplate="Δ: <b>%{text}</b> mlr USD<extra></extra>",
    ), secondary_y=True)

    t, v = _son(d["swap_haric_net_rezerv_usd"])
    baslik = ("TCMB swap hariç net rezerv — günlük (piyasa tanımı)"
              f"<br><sup>Son: {t:%d %b %Y} · {v:.2f} mlr USD · "
              "net dış varlık = (Dış Varlıklar − Dış Yükümlülükler − Bankalar "
              "Döviz Mevduatı)/USDTRY, eksi toplam swap stoku</sup>")
    ev_duzeni(fig, baslik)
    fig.update_yaxes(title_text="Swap hariç net rezerv (milyar USD)",
                     secondary_y=False,
                     range=_sim_aralik(d["swap_haric_net_rezerv_usd"]),
                     showgrid=True, gridcolor=IZGARA, zeroline=True,
                     zerolinecolor=SIFIR, zerolinewidth=1.5, hoverformat=".2f")
    fig.update_yaxes(title_text="Günlük değişim (milyar USD)",
                     secondary_y=True, range=_sim_aralik(d["delta"]),
                     showgrid=False, zeroline=True, zerolinecolor=SIFIR,
                     zerolinewidth=1.5, hoverformat="+.2f")
    return fig


# ---------------------------------------------------------------------------
# 02 — Brüt rezervin altın/döviz kırılımı (YENİ)
# ---------------------------------------------------------------------------
def sekil_brut_kirilim(daily: pd.DataFrame) -> go.Figure:
    """Yığılı alan: brüt = altın + döviz; ikinci eksende altın fiyatı.

    Altının payı yalnız TCMB altın alıp sattığı için değil, altın FİYATI
    oynadığı için de değişir — ikinci eksendeki fiyat serisi bu ikisini
    gözle ayırt etmeyi sağlar. "Döviz" satırı saf döviz değildir: IMF rezerv
    pozisyonu ve SDR'ları da içerir.
    """
    d = daily.dropna(subset=["altin_usd", "doviz_usd"]).copy()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=d.index, y=d["altin_usd"].round(2), name="Altın",
        mode="lines", stackgroup="brut", line=dict(color=ALTIN, width=0.8),
        fillcolor=ALTIN_RGBA,
        hovertemplate="Altın: <b>%{y:.1f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d.index, y=d["doviz_usd"].round(2), name="Döviz + IMF pozisyonu + SDR",
        mode="lines", stackgroup="brut", line=dict(color=LACIVERT, width=0.8),
        fillcolor=LACIVERT_RGBA,
        hovertemplate="Döviz: <b>%{y:.1f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d.index, y=d["brut_usd"].round(2), name="Brüt rezerv (toplam)",
        mode="lines", line=dict(color=TEAL, width=2, dash="dot"),
        hovertemplate="Brüt: <b>%{y:.1f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d.index, y=d["altin_fiyat"].round(0), name="Altın fiyatı (USD/ons)",
        mode="lines", line=dict(color=BORDO, width=1.6),
        hovertemplate="Altın: <b>%{y:,.0f}</b> USD/ons<extra></extra>",
    ), secondary_y=True)

    t, v = _son(d["brut_usd"])
    pay = d["altin_usd"].iloc[-1] / v * 100 if v else float("nan")
    baslik = ("Brüt rezervin altın / döviz kırılımı"
              f"<br><sup>Son: {t:%d %b %Y} · brüt {v:.1f} mlr USD · "
              f"altın {d['altin_usd'].iloc[-1]:.1f} mlr USD (%{pay:.0f}) · "
              f"altın fiyatı {d['altin_fiyat'].iloc[-1]:,.0f} USD/ons</sup>")
    ev_duzeni(fig, baslik)
    fig.update_yaxes(title_text="Milyar USD", secondary_y=False,
                     showgrid=True, gridcolor=IZGARA, rangemode="tozero",
                     hoverformat=".1f")
    fig.update_yaxes(title_text="Altın fiyatı (USD/ons)", secondary_y=True,
                     showgrid=False, hoverformat=",.0f")
    return fig


# ---------------------------------------------------------------------------
# 03 — Altın fiyat etkisi ayrıştırması (YENİ)
# ---------------------------------------------------------------------------
def sekil_altin_ayristirma(daily: pd.DataFrame) -> go.Figure:
    """Haftalık yığılı bar: Δ(swap hariç net rezerv) dört bileşene ayrılır.

        Δ(swap hariç net) = net döviz alımı (altın tamamen hariç)
                          + altın MİKTAR etkisi (Λ)
                          + altın FİYAT etkisi (Γ)
                          + kamu döviz mevduatı hareketi

    KİMLİK BİR DOĞRULAMA DEĞİLDİR. Akım kalemi ARTIK olarak tanımlıdır
    (N_fp = Δswap_haric − Δkamu − Γ), dolayısıyla toplam tanım gereği
    kapanır. Buradaki "kapanma" bir kanıt değil, cebirin sonucudur. Şeklin
    işlevi başka: Δ(swap hariç net) AYRI BİR ÇİZGİ olarak çizilir ki yığının
    onunla örtüştüğü GÖRÜLSÜN ve okur, Γ'daki her ölçüm hatasının doğrudan
    "net döviz alımı" barına yazıldığını — yani o barın en büyük epistemik
    riski taşıdığını — çıplak gözle takip edebilsin.

    Λ (miktar etkisi) dördüncü bileşen olarak ayrı gösterilir: "altın fiyat
    etkisi hariç" (N_fp) ile "altın tamamen hariç" (N) tanımları arasındaki
    tek fark odur ve başka hiçbir grafikte görünmez.

    Swap çapası yenilendiği haftalarda akıma giren revizyon ayrı bir bileşen
    olarak çıkarılır — o sıçrama TCMB'nin işlemi değil, geç gelen bilgidir.

    Günlük barlar okunmayacak kadar sık olduğu için haftaya toplulaştırılır;
    toplulaştırma toplama işlemidir, kimlik haftalıkta da tam kapanır.

    Pencere çıpadan başlar: birikimli seri ancak çıpadan sonra tanımlıdır ve
    üç yıllık haftalık bar dizisinin içine altı aylık bir çizgi koymak sağ
    ekseni okunmaz hâle getiriyordu.
    """
    d = daily.dropna(subset=["net_doviz_alimi", "altin_fiyat_etkisi"]).copy()
    bir_gecerli = d["net_doviz_alimi_birikimli"].dropna()
    if len(bir_gecerli):
        d = d.loc[bir_gecerli.index[0]:]
    d["kamu_delta"] = d["kamu_doviz_mev_usd"].shift(-1) - d["kamu_doviz_mev_usd"]
    # Kimliğin sol tarafı — yığının örtüşmesi gereken çizgi.
    d["d_swap_haric"] = (d["swap_haric_net_rezerv_usd"].shift(-1)
                         - d["swap_haric_net_rezerv_usd"])
    d["revizyon"] = d.get("swap_capa_revizyon", pd.Series(0.0, index=d.index)) \
        .fillna(0.0)
    # Net alım barından revizyonu ayır (toplam değişmez, okuma düzelir).
    d["net_temiz"] = d["net_doviz_alimi_altin_haric"] - d["revizyon"]

    bilesenler = ["net_temiz", "revizyon", "altin_miktar_etkisi",
                  "altin_fiyat_etkisi", "kamu_delta"]
    h = d[bilesenler + ["d_swap_haric"]] \
        .resample("W-FRI").sum(min_count=1).dropna(how="all")
    birikim = d["net_doviz_alimi_birikimli"].resample("W-FRI").last()

    # KOVA KENDİ SON GÜNÜNE ETİKETLENİR, HAFTA SONUNA DEĞİL.
    #
    # `resample("W-FRI")` her kovayı hafta sonu CUMA'yla adlandırır. Hafta
    # kapanmadan koşulduğunda bu, GELECEK bir tarih demektir: 27.08.2026
    # Perşembe günü üretilen grafik, elindeki son verinin 25.08 olmasına
    # rağmen son barı "28 Aug 2026" diye gösteriyordu — yayımlanmamış bir
    # günün ölçüsü gibi. Üstelik o kovada 5 değil 2 iş günü vardı ve bar,
    # yanındaki tam haftalarla aynı genişlikte çizildiği için toplamı da
    # kıyaslanabilir değildi.
    #
    # İki düzeltme: (1) etiket, kovadaki SON GERÇEK güne çekilir — gelecek
    # tarih üretilemez; (2) kovanın kaç iş günü taşıdığı hover'a yazılır ve
    # eksik olan "yarım hafta" diye işaretlenir. Bar silinmiyor: en taze
    # bilgiyi atmak yerine ne olduğunu söylüyoruz (bkz. CLAUDE.md "bir ölçüm
    # ancak KAPANMIŞ bir dönemi ölçebilir" — kapanmamışsa öyle etiketlenir).
    kova_son = d.index.to_series().resample("W-FRI").max()
    kova_gun = d.resample("W-FRI").size()
    tam = int(kova_gun.iloc[:-1].max()) if len(kova_gun) > 1 else int(kova_gun.max())
    yeni_ix, notlar = [], []
    for k in h.index:
        son_gun = kova_son.get(k)
        yeni_ix.append(son_gun if pd.notna(son_gun) else k)
        n = int(kova_gun.get(k, 0))
        notlar.append(f"<br><i>yarım hafta · {n}/{tam} iş günü</i>" if 0 < n < tam else "")
    h.index = pd.DatetimeIndex(yeni_ix)
    birikim = birikim.reindex(kova_son.index)
    birikim.index = pd.DatetimeIndex([kova_son.get(k) if pd.notna(kova_son.get(k)) else k
                                      for k in kova_son.index])
    birikim = birikim.dropna()
    yarim = notlar[-1] != "" if notlar else False

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for kolon, ad, renk, aciklama in [
        ("net_temiz", "Net döviz alımı / satımı (altın tamamen hariç)",
         TEAL_RGBA, "Net alım"),
        ("revizyon", "Swap çapa revizyonu (işlem değil, geç gelen bilgi)",
         "rgba(122,114,102,0.9)", "Çapa revizyonu"),
        ("altin_miktar_etkisi", "Altın miktar etkisi (Λ)",
         "rgba(154,115,39,0.85)", "Miktar etkisi"),
        ("altin_fiyat_etkisi", "Altın fiyat etkisi (Γ)", ALTIN_RGBA,
         "Fiyat etkisi"),
        ("kamu_delta", "Kamu döviz mevduatı hareketi", KURSUNI_RGBA, "Kamu"),
    ]:
        fig.add_trace(go.Bar(
            x=h.index, y=h[kolon].round(2), name=ad, marker_color=renk,
            customdata=notlar,
            hovertemplate=(aciklama + ": <b>%{y:+.2f}</b> mlr USD"
                           "%{customdata}<extra></extra>"),
        ), secondary_y=False)

    # Kimliğin sol tarafı: yığın bunun üstüne oturmalı.
    fig.add_trace(go.Scatter(
        x=h.index, y=h["d_swap_haric"].round(2),
        name="Δ swap hariç net rezerv (kimliğin sol tarafı)", mode="markers",
        marker=dict(color=LACIVERT, size=6, symbol="x-thin",
                    line=dict(color=LACIVERT, width=1.6)),
        hovertemplate="Δ swap hariç: <b>%{y:+.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=birikim.index, y=birikim.round(2),
        name="Çıpadan birikimli net döviz alımı", mode="lines",
        line=dict(color=BORDO, width=2, dash="dash"), connectgaps=False,
        hovertemplate="Birikimli: <b>%{y:+.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=True)

    t, v = _son(d["net_doviz_alimi_birikimli"])
    cipa = bir_gecerli.index[0] if len(bir_gecerli) else None
    cipa_s = f"{cipa:%d %b %Y}" if cipa is not None else "-"
    baslik = ("Rezerv değişiminin ayrıştırılması"
              f"<br><sup>Haftalık toplam · çıpa {cipa_s} · birikimli net alım "
              f"{v:+.1f} mlr USD ({t:%d %b %Y}) · akım ARTIK olarak tanımlıdır, "
              "kimliğin kapanması bir doğrulama değildir"
              + ("<br>Son bar YARIM HAFTA: hafta kapanmadı, kovadaki iş günü "
                 "sayısı hover'da yazar — yanındaki tam haftalarla toplamı "
                 "kıyaslanamaz." if yarim else "")
              + "</sup>")
    ev_duzeni(fig, baslik)
    fig.update_layout(barmode="relative")
    fig.update_yaxes(title_text="Haftalık katkı (milyar USD)",
                     secondary_y=False, showgrid=True, gridcolor=IZGARA,
                     zeroline=True, zerolinecolor=SIFIR, zerolinewidth=1.5,
                     hoverformat="+.2f")
    fig.update_yaxes(title_text="Birikimli net döviz alımı (milyar USD)",
                     secondary_y=True, showgrid=False, zeroline=True,
                     zerolinecolor=SIFIR, zerolinewidth=1, hoverformat="+.2f")
    return fig


# ---------------------------------------------------------------------------
# 04 — Günlük akım, iki tanım
# ---------------------------------------------------------------------------
def sekil_akim(daily: pd.DataFrame) -> go.Figure:
    """Günlük net döviz alımı (bar, iki tanım) + çıpadan birikimli (çizgi).

    Üç şey görünür kılınır:
      1. GÜNLÜK rakamların belirsizlik bandı (±AKIM_BANT_GUNLUK). Altın
         değerleme fiyatı farkı tek başına bu mertebede sahte akım üretir;
         bandın içinde kalan bir günlük hareket "TCMB döviz aldı" diye
         okunmamalıdır.
      2. BİRİKİMLİ çizginin bandı. Bu rakam kendi belirsizlik bandı kadar
         büyüktür — işareti bile garanti değildir.
      3. GEÇİCİ günler. Son miktar (ons) çapasından sonraki barlar soluk
         çizilir: yeni bir haftalık gözlem geldiğinde Q(t), dolayısıyla Γ(t)
         ve bu barların yüksekliği REVİZE OLUR.

    Pencere çıpadan başlar: birikimli seri ancak çıpadan sonra tanımlıdır.
    """
    d = daily.dropna(subset=["net_doviz_alimi"]).copy()
    bir = d["net_doviz_alimi_birikimli"].dropna()
    if len(bir):
        d = d.loc[bir.index[0]:]

    nfp = d["net_doviz_alimi"].round(2)
    if "akim_gecici" in d.columns:
        gecici = d["akim_gecici"].astype(str).str.lower().isin(["true", "1"])
    else:
        gecici = pd.Series(False, index=d.index)
    # Geçici günler soluk; ayrıca fiyatı taşınmış (ffill) günler de belirsiz.
    ffill = (d.get("altin_fiyat_kaynak", pd.Series("", index=d.index))
             .astype(str) == "ffill")
    belirsiz = gecici | ffill
    renkler = [
        ("rgba(29,92,92,0.28)" if b else TEAL_RGBA) if v >= 0
        else ("rgba(142,31,47,0.28)" if b else BORDO_RGBA)
        for v, b in zip(nfp.fillna(0), belirsiz)
    ]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    # Günlük gürültü bandı — barların arkasında yatay şerit.
    fig.add_hrect(y0=-AKIM_BANT_GUNLUK, y1=AKIM_BANT_GUNLUK,
                  fillcolor="rgba(122,114,102,0.13)", line_width=0,
                  layer="below", secondary_y=False)
    fig.add_trace(go.Bar(
        x=d.index, y=nfp, name="Net döviz alımı (altın fiyat etkisi hariç)",
        marker_color=renkler,
        hovertemplate="Net alım: <b>%{y:+.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)
    if belirsiz.any():
        fig.add_trace(go.Bar(
            x=[d.index[0]], y=[None],
            name=f"soluk barlar: geçici / fiyatı taşınmış gün "
                 f"({int(belirsiz.sum())} gün)",
            marker_color="rgba(29,92,92,0.28)", showlegend=True,
            hoverinfo="skip",
        ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d.index, y=d["net_doviz_alimi_altin_haric"].round(2),
        name="Net döviz alımı (altın tamamen hariç)", mode="markers",
        marker=dict(color=ALTIN, size=4, symbol="circle-open"),
        hovertemplate="Altın hariç: <b>%{y:+.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)

    # Birikimli çizgi + belirsizlik şeridi (sağ eksen)
    bk = d["net_doviz_alimi_birikimli"].round(2)
    fig.add_trace(go.Scatter(
        x=list(bk.index) + list(bk.index[::-1]),
        y=list((bk + AKIM_BANT_BIRIKIMLI).round(2))
          + list((bk - AKIM_BANT_BIRIKIMLI).round(2))[::-1],
        fill="toself", fillcolor="rgba(29,92,92,0.13)",
        line=dict(width=0), hoverinfo="skip",
        name=f"birikimli belirsizlik bandı (±{AKIM_BANT_BIRIKIMLI:.1f} mlr USD)",
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=d.index, y=bk,
        name="Çıpadan birikimli", mode="lines",
        line=dict(color=TEAL, width=2.2), connectgaps=False,
        hovertemplate="Birikimli: <b>%{y:+.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=True)

    t, v = _son(d["net_doviz_alimi_birikimli"])
    baslik = ("Günlük net döviz alımı / satımı — altın fiyat etkisinden "
              "arındırılmış"
              # Etiket hizası ÖLÇÜLDÜ (bkz. ozet_uret.py'deki hiza notu ve
              # net_rezerv.py --kontrol-dogrula): akım BAŞLANGIÇ gününe
              # etiketlenir. Alt başlık bir ara bunun tersini yazıyordu.
              f"<br><sup>Değer, etiketlenen günün kapanışından bir SONRAKİ iş "
              f"gününün kapanışına kadarki hareketi gösterir · birikimli {v:+.1f} ± {AKIM_BANT_BIRIKIMLI:.1f} mlr "
              f"USD ({t:%d %b %Y}) · gri şerit ±{AKIM_BANT_GUNLUK:.1f} mlr "
              "USD'lik günlük ölçüm gürültüsü</sup>")
    ev_duzeni(fig, baslik)
    fig.update_yaxes(title_text="Günlük net alım (milyar USD)",
                     secondary_y=False, range=_sim_aralik(d["net_doviz_alimi"]),
                     showgrid=True, gridcolor=IZGARA, zeroline=True,
                     zerolinecolor=SIFIR, zerolinewidth=1.5,
                     hoverformat="+.2f")
    fig.update_yaxes(title_text="Birikimli (milyar USD)", secondary_y=True,
                     range=_sim_aralik(d["net_doviz_alimi_birikimli"]),
                     showgrid=False, zeroline=True, zerolinecolor=SIFIR,
                     zerolinewidth=1, hoverformat="+.2f")
    return fig


# ---------------------------------------------------------------------------
# 05 — Swap stoku ve kırılımı
# ---------------------------------------------------------------------------
def sekil_swap(daily: pd.DataFrame) -> go.Figure:
    """Toplam swap stoku + yerli banka / yabancı merkez bankası kırılımı.

    Yabancı bacak basamak fonksiyonu gibi görünür: yalnız IRFCL yayımlandığında
    tazelenir, ay içi hareketi gözlenemez. Yerli bacak her iş günü yayımlanır.
    """
    d = daily.dropna(subset=["swap_toplam_usd"]).copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d.index, y=d["swap_toplam_usd"].round(2), name="Toplam swap stoku",
        mode="lines", line=dict(color=TEAL, width=2.2),
        hovertemplate="Toplam: <b>%{y:.2f}</b> mlr USD<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=d.index, y=d["swap_yabanci_usd"].round(2),
        name="Yabancı merkez bankası (IRFCL frekansında tazelenir)",
        mode="lines", line=dict(color=BORDO, width=1.8, shape="hv"),
        hovertemplate="Yabancı MB: <b>%{y:.2f}</b> mlr USD<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=d.index, y=d["swap_yerli_usd"].round(2),
        name="Yurt içi bankalar (günlük yayımlanır)", mode="lines",
        line=dict(color=ALTIN, width=1.8),
        hovertemplate="Yerli banka: <b>%{y:.2f}</b> mlr USD<extra></extra>",
    ))
    if "swap_gozlem" in d.columns:
        gz = d.index[d["swap_gozlem"].astype(str).str.lower()
                     .isin(["true", "1"])]
        if len(gz):
            fig.add_trace(go.Scatter(
                x=gz, y=d["swap_toplam_usd"].reindex(gz).round(2),
                mode="markers", name="IRFCL gözlemi",
                marker=dict(color=TEAL, size=7, symbol="diamond",
                            line=dict(color="white", width=1)),
                hovertemplate="IRFCL gözlemi<extra></extra>",
            ))

    # Çapa tipinin HAFTALIK olduğu bölgeler işaretlenir. Hassasiyet bu iki
    # rejim arasında on kat ayrışıyor (haftalık ±0,02 · aylık ±0,20 mlr USD);
    # son günün tipini başlıkta yazmak, tarihçenin büyük kısmının hangi
    # rejimde olduğunu gizliyordu.
    haftalik_oran = float("nan")
    if "swap_capa_tipi" in d.columns:
        hafta = (d["swap_capa_tipi"] == "haftalık")
        haftalik_oran = float(hafta.mean()) * 100
        blok = (hafta != hafta.shift()).cumsum()[hafta]
        for _, grup in hafta[hafta].groupby(blok):
            fig.add_vrect(x0=grup.index[0], x1=grup.index[-1],
                          fillcolor="rgba(29,92,92,0.07)", line_width=0,
                          layer="below")

    t, v = _son(d["swap_toplam_usd"])
    tip = d["swap_capa_tipi"].dropna().iloc[-1] if "swap_capa_tipi" in d else "-"
    baslik = ("TCMB toplam swap stoku ve kırılımı"
              f"<br><sup>Son: {t:%d %b %Y} · toplam {v:.2f} mlr USD · son çapa "
              f"{tip} · serinin %{haftalik_oran:.0f}'i haftalık IRFCL çapasına "
              "dayanıyor (gölgeli bölgeler; hata bandı haftalık ±0,02 · aylık "
              "±0,20 mlr USD) · pozitif stok = TCMB vadede döviz satıyor</sup>")
    ev_duzeni(fig, baslik)
    fig.update_yaxes(title_text="Swap stoku (milyar USD)", showgrid=True,
                     gridcolor=IZGARA, zeroline=True, zerolinecolor=SIFIR,
                     zerolinewidth=1.5, hoverformat=".2f")
    return fig


# ---------------------------------------------------------------------------
# 06 — İki tanım yan yana
# ---------------------------------------------------------------------------
def sekil_tanim_farki(daily: pd.DataFrame) -> go.Figure:
    """Piyasa tanımı ile TCMB'nin Stand-By 2A serisi yan yana + fark alanı.

    Fark tamamen VARLIK bacağındadır: 2A, varlık tarafında daha dar bir tanım
    olan brüt döviz rezervini kullanır. Yükümlülük bacakları örtüşür. İki ölçü
    de doğrudur; tanımları farklıdır.

    FARK SABİT DEĞİLDİR — bu şeklin asıl gösterdiği şey budur. Cuma
    ortalaması 2023'ten bu yana yukarı sürükleniyor ve tek tek haftalarda
    eksiye de geçiyor. "Aradaki ~2 milyar dolarlık yapısal fark" cümlesi
    yalnız son aylar için doğrudur; grafikte sürüklenmenin kendisi ve
    yuvarlanan medyan çizilir ki okur bunu bir sabit sanmasın.
    """
    d = daily.dropna(subset=["net_dis_varlik_usd", "eski_net_rezerv_usd"]).copy()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=d.index, y=d["net_dis_varlik_usd"].round(2),
        name="Net dış varlık (piyasa tanımı)", mode="lines",
        line=dict(color=TEAL, width=2.2),
        hovertemplate="Piyasa tanımı: <b>%{y:.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=d.index, y=d["eski_net_rezerv_usd"].round(2),
        name="Net Uluslararası Rezervler 2A (TCMB haftalık yayını)",
        mode="lines", line=dict(color=LACIVERT, width=1.8, dash="dot"),
        hovertemplate="Stand-By 2A: <b>%{y:.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=False)
    # Fark YALNIZ Cuma günleri çizilir. Stand-By 2A haftalık bir yayındır;
    # hafta içi değeri bir tahmindir (Cuma çapası + analitik bilanço deltası)
    # ve hafta içinde kayıp Cuma'da resmi değere geri oturur. Günlük farkı
    # çizmek, TANIM farkının üstüne bu TAHMİN hatasını bindirirdi.
    cuma = d[d.index.dayofweek == 4]
    fig.add_trace(go.Scatter(
        x=cuma.index, y=cuma["tanim_farki"].round(2),
        name="Tanım farkı — Cuma, resmi değer (sağ eksen)",
        mode="lines", line=dict(color=BORDO, width=1.4),
        fill="tozeroy", fillcolor=BORDO_RGBA.replace("0.7", "0.18"),
        hovertemplate="Fark: <b>%{y:+.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=True)

    # Yuvarlanan medyan: farkın SÜRÜKLENDİĞİNİ göster, sabit sanılmasın.
    med = cuma["tanim_farki"].rolling(26, min_periods=8).median()
    fig.add_trace(go.Scatter(
        x=cuma.index, y=med.round(2),
        name="Tanım farkı — 26 haftalık yuvarlanan medyan (sağ eksen)",
        mode="lines", line=dict(color=KURSUNI, width=1.8, dash="dot"),
        hovertemplate="Medyan: <b>%{y:+.2f}</b> mlr USD<extra></extra>",
    ), secondary_y=True)

    t, v = _son(cuma["tanim_farki"])
    cf = cuma["tanim_farki"].dropna()
    baslik = ("İki net rezerv tanımı yan yana"
              f"<br><sup>Son Cuma: {t:%d %b %Y} · fark {v:+.2f} mlr USD · fark "
              f"SABİT DEĞİL: {len(cf)} Cuma'da {cf.min():+.2f} ile "
              f"{cf.max():+.2f} arasında, medyanı yukarı sürükleniyor · fark "
              "tamamen varlık bacağındadır</sup>")
    ev_duzeni(fig, baslik)
    fig.update_yaxes(title_text="Net rezerv (milyar USD)", secondary_y=False,
                     showgrid=True, gridcolor=IZGARA, zeroline=True,
                     zerolinecolor=SIFIR, zerolinewidth=1.5, hoverformat=".2f")
    fig.update_yaxes(title_text="Tanım farkı (milyar USD)", secondary_y=True,
                     showgrid=False, hoverformat="+.2f")
    return fig


SEKILLER = {
    "rezerv": ("tcmb_rezerv_grafik.html", sekil_swap_haric),
    "brut": ("brut_kirilim.html", sekil_brut_kirilim),
    "ayristirma": ("altin_ayristirma.html", sekil_altin_ayristirma),
    "akim": ("akim.html", sekil_akim),
    "swap": ("swap.html", sekil_swap),
    "tanim": ("tanim_farki.html", sekil_tanim_farki),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default=None,
                    help="gg-aa-yyyy; verilmezse tüm CSV")
    ap.add_argument("--end", default=None)
    ap.add_argument("--cikti-dizin", default=None,
                    help="HTML'lerin yazılacağı dizin (varsayılan: proje klasörü)")
    ap.add_argument("--online", action="store_true",
                    help="EVDS + IRFCL PDF'ten taze veri çek "
                         "(varsayılan: gunluk.csv/haftalik_rezerv.csv)")
    ap.add_argument("--csv-daily", default="gunluk.csv")
    ap.add_argument("--csv-weekly", default="haftalik_rezerv.csv")
    ap.add_argument("--sadece", nargs="*", choices=sorted(SEKILLER),
                    help="yalnız bu grafikleri üret")
    ap.add_argument("--no-open", action="store_true",
                    help="dosyaları tarayıcıda açma")
    args = ap.parse_args()

    burasi = Path(__file__).resolve().parent
    cikti = Path(args.cikti_dizin).resolve() if args.cikti_dizin else burasi
    cikti.mkdir(parents=True, exist_ok=True)

    if args.online:
        from net_rezerv import hat_kos
        h = hat_kos(end=args.end or dt.date.today().strftime("%d-%m-%Y"))
        daily = h["gunluk"]
        for u in h["uyarilar"]:
            print(f"UYARI: {u}")
    else:
        csv_d = burasi / args.csv_daily
        if not csv_d.exists():
            raise RuntimeError(
                f"{csv_d} yok. Önce `python net_rezerv.py` koşturun ya da "
                "--online verin."
            )
        daily = pd.read_csv(csv_d, index_col=0, parse_dates=True)

    if args.start:
        daily = daily.loc[dt.datetime.strptime(args.start, "%d-%m-%Y"):]
    if args.end:
        daily = daily.loc[:dt.datetime.strptime(args.end, "%d-%m-%Y")]

    gerekli = ["swap_haric_net_rezerv_usd", "altin_usd", "net_doviz_alimi",
               "net_doviz_alimi_altin_haric", "altin_miktar_etkisi",
               "swap_capa_revizyon", "akim_gecici"]
    eksik = [c for c in gerekli if c not in daily.columns]
    if eksik:
        raise RuntimeError(
            "Günlük seri yeni tanımın sütunlarını taşımıyor: "
            + ", ".join(eksik) + ". net_rezerv.py'yi yeniden koşturun."
        )

    secili = args.sadece or list(SEKILLER)
    yazilan: list[Path] = []
    for ad in secili:
        dosya, uretici = SEKILLER[ad]
        try:
            fig = uretici(daily)
        except Exception as e:
            # Bir grafik düşerse diğerleri üretilsin ama SESSİZ kalmasın.
            print(f"HATA [{ad}]: {type(e).__name__}: {e}")
            continue
        yol = cikti / dosya
        fig.write_html(yol, include_plotlyjs="cdn")
        yazilan.append(yol)
        print(f"Grafik kaydedildi: {yol}")

    if len(yazilan) < len(secili):
        raise SystemExit(f"{len(secili) - len(yazilan)} grafik üretilemedi.")

    if not args.no_open and yazilan:
        webbrowser.open(yazilan[0].as_uri())


if __name__ == "__main__":
    main()
