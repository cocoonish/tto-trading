#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 8 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         make_subplots, tarih, vir, yuzde, _yaz)

REFERANS = dict(color="#9a9a9a", width=1)


def _baslik(ana: str, *alt: str) -> dict:
    """Plotly başlığı sarmaz: alt başlık satırları ~105 karakterde elle bölünür."""
    return dict(text=ana + "".join(f"<br><sub>{s}</sub>" for s in alt))


def _paneller_sola(fig, boyut: int = 13) -> None:
    """Panel başlıkları sola yaslanır: dar ekranda ortalı başlık iki uçtan birden kırpılıyordu."""
    for an in fig.layout.annotations:
        if an.yref == "paper" and an.yanchor == "bottom" and an.xref == "paper":
            an.update(x=0, xanchor="left", font=dict(size=boyut, color=MUREKKEP))


def _aralik(gecikmeler: list[int]) -> str:
    """Ardışık gecikme listesini '4–13' biçiminde yazar; ardışık değilse virgülle sayar."""
    if gecikmeler and gecikmeler == list(range(gecikmeler[0], gecikmeler[-1] + 1)):
        return f"{gecikmeler[0]}–{gecikmeler[-1]}"
    return ", ".join(str(g) for g in gecikmeler)


# ───────────────────────────────────────────────────────── Şekil 13
def s13_uc_denge(o: dict) -> None:
    b = o["b08"]
    s = b["sekil_13"]
    a = b["p8a"]
    ik = a["ikiz_acik"]
    q = s["ceyrek"]
    fig = make_subplots(rows=1, cols=1, subplot_titles=("Dört çeyreklik akım, % GSYH",))
    for ad, renk, etiket in (("kamu", MAVI, "kamu dengesi (merkezi yönetim bütçesi)"),
                             ("ozel", CLARET, "özel kesim dengesi = dış − kamu (artık)")):
        fig.add_trace(go.Bar(x=s["tarih"], y=s[ad], name=etiket, marker_color=renk, marker_line_width=0,
                             customdata=q, hovertemplate="%{customdata}: %{y:.2f}<extra>" + etiket + "</extra>"))
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["dis"], mode="lines",
                             name="dış denge = cari denge = çubukların toplamı",
                             line=dict(color=MUREKKEP, width=2.2), customdata=q,
                             hovertemplate="%{customdata}: %{y:.2f}<extra>dış denge (TL'ye aylık kurla)</extra>"))
    fig.add_trace(go.Scatter(x=s["tarih"], y=s["dis_usd"], mode="lines",
                             name="dış denge, resmî biçim (dolar cari / dolar GSYH)",
                             line=dict(color=GRI, width=1.3, dash="dot"), customdata=q,
                             hovertemplate="%{customdata}: %{y:.2f}<extra>dış denge (dolar / dolar)</extra>"))
    # OVP'nin gerçekleşme satırları: yalnız kontrol noktası sayılanlar (tahmin satırı programın tahmin hatasıdır)
    ox, oy, orenk, ometin = [], [], [], []
    for k in a["ovp_kontrol"]:
        if not k["kontrol_noktasi"]:
            continue
        yayim = ay(k["yayin_ay"] + "-01")
        for deger, renk, kalem, olcum in (
                (k["ovp_cari_gsyh_yuzde"], MUREKKEP, "cari denge", k["olcum_dis_tl_gsyh_yuzde"]),
                (k["ovp_genel_devlet_dengesi_gsyh_yuzde"], MAVI, "genel devlet dengesi",
                 k["olcum_kamu_merkezi_yonetim_gsyh_yuzde"]),
                (k["ovp_ozel_artik_gsyh_yuzde"], CLARET, "özel kesim (artık)", k["olcum_ozel_gsyh_yuzde"])):
            ox.append(f"{k['yil']}-12-31")
            oy.append(deger)
            orenk.append(renk)
            ometin.append(f"OVP ({yayim} yayımı), {k['yil']} gerçekleşme · {kalem}: {vir(deger, 1)}"
                          f" · bu figürün ölçümü: {vir(olcum, 2)}")
    # içi beyaz elmas: açık elmas aynı renkli çubuğun üstünde kayboluyordu (genel devlet, mavi çubukta)
    fig.add_trace(go.Scatter(x=ox, y=oy, mode="markers",
                             name="OVP gerçekleşme satırı, yıl sonu (renk: kalem; kamu = genel devlet)",
                             marker=dict(symbol="diamond", size=11, color="white", line=dict(width=2.2, color=orenk)),
                             text=ometin, hovertemplate="%{text}<extra></extra>"))
    fig.update_layout(barmode="relative", bargap=0.12)
    fig.add_hline(y=0, line=REFERANS)
    fig.update_yaxes(title_text="% GSYH (eksi: açık, artı: fazla)")
    fig.update_xaxes(zeroline=False)
    _paneller_sola(fig)
    ort = a["uc_degerler"]
    fig.update_layout(title=_baslik(
        "Şekil 13 — Cari dengeyi özel kesim sürüklüyor: kamu açığındaki artışı fazlasıyla dengeliyor",
        f"TCMB ödemeler dengesi, HMB merkezi yönetim bütçesi, TÜİK GSYH · çeyreklik {s['ilk_ceyrek']}–"
        f"{s['son_ceyrek']}",
        "kamu = merkezi yönetim (genel yönetim değil) · özel = dış − kamu (artık: kapsam farkı, net hata ve noksan)",
        f"dönem ortalaması: dış {vir(ort['dis']['ortalama_gsyh_yuzde'], 2)} = kamu "
        f"{vir(ort['kamu']['ortalama_gsyh_yuzde'], 2)} + özel {vir(ort['ozel']['ortalama_gsyh_yuzde'], 2)} · "
        f"kamu–dış seviye korelasyonu {vir(ik['seviye_korelasyonu_kamu_dis'], 2)}",
        f"4 çeyreklik değişimde dış = {vir(ik['egim'], 2)} × kamu (t {vir(ik['t'], 2)}; örneklem içi): kamu 1 puan "
        f"bozulunca özel {vir(ik['ozel_kesim_dengelemesi'], 2)} iyileşir"))
    _yaz(fig, "13_uc_denge.html", 680)


# ───────────────────────────────────────────────────────── Şekil 14
def s14_j_egrisi(o: dict) -> None:
    b = o["b08"]
    s = b["sekil_14"]
    p = b["p8b"]
    y = p["yillik_dagitilmis_gecikme"]
    g = s["gecikme_ay"]
    fig = make_subplots(rows=2, cols=1, row_heights=[0.64, 0.36], vertical_spacing=0.17,
                        subplot_titles=("Her gecikme ayrı regresyon (dolu işaret: |t| ≥ 2)",
                                        "Üç yıl tek regresyonda (±2 standart hata)"))
    oz, ozg = p["ozet"], p["gelir_kontrollu"]["ozet"]
    for (eg, se, tt, renk, acik, ad, cizgi, bant_dolgu, aralik) in (
            (s["egim"], s["se"], p["profil"]["t"], MAVI, ACIK_MAVI, "ana tanım", "solid", True,
             oz["anlamli_eksi_gecikmeler_ay"]),
            (s["egim_gelir_kontrollu"], s["se_gelir_kontrollu"], p["gelir_kontrollu"]["profil"]["t"], CLARET,
             ACIK_CLARET, "büyüme kontrollü", "dash", False, ozg["anlamli_eksi_gecikmeler_ay"])):
        alt = [e - 2 * h for e, h in zip(eg, se)]
        ust = [e + 2 * h for e, h in zip(eg, se)]
        if bant_dolgu:
            fig.add_trace(go.Scatter(x=g, y=alt, mode="lines", line=dict(width=0), showlegend=False,
                                     hoverinfo="skip", legendgroup=ad), 1, 1)
            fig.add_trace(go.Scatter(x=g, y=ust, mode="lines", line=dict(width=0), fill="tonexty", fillcolor=acik,
                                     showlegend=False, hoverinfo="skip", legendgroup=ad), 1, 1)
        else:                          # ikinci bant dolgusuz: iki dolgu üst üste binince okunmuyordu
            for kenar in (alt, ust):
                fig.add_trace(go.Scatter(x=g, y=kenar, mode="lines", line=dict(color=renk, width=0.9, dash="dot"),
                                         showlegend=False, hoverinfo="skip", legendgroup=ad), 1, 1)
        # dolu işaret ölçümün KENDİ t'sinden (yuvarlanmış eğim/se oranından değil): eşik ölçümle aynı yerde kesilir
        dolu = [abs(v) >= 2 for v in tt]
        fig.add_trace(go.Scatter(x=g, y=eg, mode="lines+markers",
                                 name=(f"{ad}: anlamlı eksi {_aralik(aralik)} ay ("
                                       + ("gölge: ±2 standart hata" if bant_dolgu else "noktalı: aynı bant") + ")"),
                                 legendgroup=ad, line=dict(color=renk, width=2, dash=cizgi),
                                 marker=dict(size=7, color=[renk if d else "white" for d in dolu],
                                             line=dict(color=renk, width=1.5)),
                                 customdata=[[v] for v in tt],
                                 hovertemplate="gecikme %{x} ay: %{y:.3f} (t %{customdata[0]:.2f})<extra>" + ad
                                               + "</extra>"), 1, 1)
    fig.add_hline(y=0, line=REFERANS, row=1, col=1)
    fig.update_xaxes(title_text="gecikme k (ay)", dtick=3, range=[-0.5, 24.5], zeroline=False, row=1, col=1)
    fig.update_yaxes(title_text="eğim: puan / REDK'de %1 artış", row=1, col=1)

    kat = ["son 12 ay", "12–24 ay önce", "24–36 ay önce"]
    for anahtar, renk, ad in (("gelirsiz", MAVI, "ana tanım"), ("gelir_kontrollu", CLARET, "büyüme kontrollü")):
        d = y[anahtar]
        eg = [d[f"yil{i}_egim"] for i in range(3)]
        se = [d[f"yil{i}_se"] for i in range(3)]
        tt = [d[f"yil{i}_t"] for i in range(3)]
        fig.add_trace(go.Bar(x=kat, y=eg, name=ad, legendgroup=ad, showlegend=False, marker_color=renk,
                             marker_line_width=0, error_y=dict(type="data", array=[2 * h for h in se], color=MUREKKEP,
                                                               thickness=1.2, width=5),
                             customdata=[[t] for t in tt],
                             hovertemplate="%{x}: %{y:.3f} (t %{customdata[0]:.2f})<extra>" + ad + "</extra>"), 2, 1)
    fig.update_layout(barmode="group", bargap=0.35)
    fig.add_hline(y=0, line=REFERANS, row=2, col=1)
    fig.update_xaxes(title_text="reel kur değişiminin dönemi", row=2, col=1)
    fig.update_yaxes(title_text="eğim: puan / %1", row=2, col=1)
    _paneller_sola(fig)
    # J-eğrisi REDK ARTIŞINA (reel değer kazancı) göre kısa gecikmede ARTI, sonra EKSİ eğim ister. Grafikteki
    # çukur Marshall–Lerner yönüdür; eksik olan J'nin kısa koludur.
    fig.update_layout(title=_baslik(
        f"Şekil 14 — J-eğrisinin kısa kolu yok: reel değer kazancı mal dengesini "
        f"{_aralik(oz['anlamli_eksi_gecikmeler_ay'])} ay gecikmeyle bozuyor",
        f"TCMB ödemeler dengesi, REDK (TÜFE bazlı), TÜİK GSYH · aylık {ay(s['ilk'])}–{ay(s['son'])}, "
        f"{s['n']} gözlem · Newey–West",
        "bağımlı: altın ve enerji hariç mal dengesinin 12 aylık değişimi, başlangıçtaki dolar GSYH'ye oranla (puan)",
        "açıklayıcı: REDK'nin k ay önce biten 12 aylık log değişimi · eksi eğim: reel değer kazancı dengeyi bozar",
        f"J-eğrisi kısa gecikmede artı eğim ister: anlamlı artı yok · en derin {oz['en_eksi_gecikme_ay']}. ay "
        f"({vir(oz['en_eksi_egim_puan_yuzde'], 3)}; t {vir(oz['en_eksi_t'], 2)})"))
    _yaz(fig, "14_j_egrisi.html", 840)


# ───────────────────────────────────────────────────────── Şekil 15
def s15_redk_cari(o: dict) -> None:
    b = o["b08"]
    s = b["sekil_15"]
    c = b["p8c"]["cari"]
    ss = b["p8c"]["sapma_son"]
    dag = b["p8c"]["sapma_dagilimi"]
    t, x, yy = s["tarih"], s["redk_sapma_yuzde"], s["sonraki_12ay_cari_degisim_puan"]
    i_ok = [i for i, v in enumerate(yy) if v is not None]   # sonraki 12 ayı gerçekleşmiş başlangıç ayları
    tx = [t[i] for i in i_ok]
    xx = [x[i] for i in i_ok]
    yv = [yy[i] for i in i_ok]
    fig = make_subplots(rows=1, cols=1, subplot_titles=("Her nokta bir başlangıç ayı",))
    fig.add_trace(go.Scatter(x=xx, y=yv, mode="markers", name="aylık gözlem",
                             marker=dict(color=MAVI, size=6, opacity=0.45, line=dict(width=0)),
                             customdata=[ay(v) for v in tx],
                             hovertemplate="%{customdata}: sapma %{x:.1f} · sonraki 12 ay %{y:.2f} puan<extra></extra>"))
    x0, x1 = min(xx), max(xx)
    fig.add_trace(go.Scatter(x=[x0, x1], y=[c["sabit"] + c["egim_puan_yuzde"] * x0,
                                            c["sabit"] + c["egim_puan_yuzde"] * x1],
                             mode="lines", line=dict(color=MUREKKEP, width=2),
                             name=(f"eğim {vir(c['egim_puan_yuzde'], 3)} puan / %1 sapma "
                                   f"(Newey–West t {vir(c['t'], 2)}; R² {vir(c['r2'], 2)})"), hoverinfo="skip"))
    j = len(xx) - 1
    fig.add_trace(go.Scatter(x=[xx[j]], y=[yv[j]], mode="markers+text",
                             name=f"son gerçekleşen gözlem ({ay(tx[j])} başlangıçlı)",
                             marker=dict(color=CLARET, size=12, line=dict(color="white", width=1.5)),
                             text=[ay(tx[j])], textposition="top left", textfont=dict(color=CLARET, size=12),
                             hovertemplate=f"{ay(tx[j])}: sapma %{{x:.1f}} · sonraki 12 ay %{{y:.2f}} puan"
                                           "<extra></extra>"))
    for gun, kayma, dik, ne in ((dag["en_dusuk_tarih"], 24, 34, "en düşük sapma"),
                                (dag["en_yuksek_tarih"], -24, -52, "en yüksek sapma")):
        if gun in tx:
            k = tx.index(gun)
            fig.add_annotation(x=xx[k], y=yv[k], text=f"{ay(gun)}<br>{ne}", showarrow=True, arrowhead=0,
                               ax=kayma, ay=dik, align="left" if kayma > 0 else "right",
                               xanchor="left" if kayma > 0 else "right", bgcolor="rgba(255,255,255,0.85)",
                               font=dict(size=11, color=MUREKKEP), arrowcolor=GRI)
    fig.add_vline(x=ss["sapma_yuzde"], line=dict(color=TURUNCU, width=1.6, dash="dash"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color=TURUNCU, width=1.6, dash="dash"),
                             name=f"bugünkü sapma ({ay(ss['tarih'])}: {yuzde(ss['sapma_yuzde'], 1)})"))
    fig.add_hline(y=0, line=REFERANS)
    fig.add_vline(x=0, line=REFERANS)
    fig.update_xaxes(title_text="REDK sapması (%, log; artı: TL reel olarak pahalı)",
                     zeroline=False)
    fig.update_yaxes(title_text="sonraki 12 ayda cari denge değişimi (puan; artı: iyileşme)")
    _paneller_sola(fig)
    oo_ = c["oos"]
    fig.update_layout(title=_baslik(
        "Şekil 15 — Reel kur sapması sonraki yılın cari dengesini öngörmüyor: eğim eksi ama anlamsız",
        f"TCMB REDK (TÜFE bazlı) ve ödemeler dengesi, TÜİK GSYH · başlangıç ayı {ay(tx[0])}–{ay(tx[-1])}, "
        f"{len(xx)} gözlem",
        "yatay: log REDK'nin o aya kadar gözlenen bütün geçmişin ortalamasından farkı (genişleyen pencere)",
        "dikey: 12 aylık cari dengenin sonraki 12 aydaki dolar değişimi / başlangıçtaki 12 aylık dolar GSYH (puan)",
        f"örneklem dışı hata kare oranı {vir(oo_['ortalama']['mse_oran'], 2)} (ortalamaya) · "
        f"{vir(oo_['sifir']['mse_oran'], 2)} (rastgele yürüyüşe); 1'in üstü: model kıyastan kötü"))
    _yaz(fig, "15_redk_cari.html", 700)
