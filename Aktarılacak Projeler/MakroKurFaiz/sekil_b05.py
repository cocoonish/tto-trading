#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 5 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         baslik_koy, make_subplots, tarih, vir, yukseklik, yuzde, _yaz)

ULKE_RENK = {"ABD": MAVI, "İngiltere": CLARET}
# Kadran figüründe okura gösterilen kısa ad (tam ad ipucunda); hangi panelde ve
# noktanın hangi yanında yazılacağı: (panel, xanchor, yanchor, dx, dy).
KISA = {
    "abd_2016_secim": ("2016 seçimi → Aralık FOMC", 1, "right", "middle", -9, 0),
    "abd_2025_tarife": ("Nisan 2025 tarife", 1, "left", "middle", 9, 0),
    "igb_2022_mini_butce": ("2022 mini bütçe → BoE", 1, "left", "middle", 9, 0),
    "igb_2022_zirve": ("BoE müdahalesi öncesi", 1, "left", "middle", 9, 0),
    "abd_2017_vergi": ("2017 vergi yasası (karşı örnek)", 2, "left", "middle", 9, 0),
    "abd_2025_moodys_3g": ("Moody's 2025, üç gün", 2, "left", "middle", 9, 0),  # 16.05.2025 indirimi
    "abd_2025_moodys_1g": ("Moody's, ilk gün", 2, "right", "top", -6, -7),
    "abd_2023_agustos": ("Ağustos 2023: arz + Fitch", 2, "right", "middle", -9, 0),
    "abd_2023_fitch_gunu": ("02.08.2023 tek gün", 2, "left", "top", 6, -7),
}
# kadranın kısa yazımı (dar ekranda iki üst köşe çakışmasın); uzun adı b01'in kadran sözlüğündedir
OK = {"prim": "faiz ↑ · para ↓", "politika": "faiz ↑ · para ↑", "gevseme": "faiz ↓ · para ↓",
      "guvenli_liman": "faiz ↓ · para ↑"}
KADRAN_AD = {"prim": "prim", "politika": "politika", "gevseme": "gevşeme", "guvenli_liman": "güvenli liman"}
# alt pencere → ana olayı (bağlantı çizgisi)
ANA = {"igb_2022_zirve": "igb_2022_mini_butce", "abd_2025_moodys_3g": "abd_2025_moodys_1g",
       "abd_2023_fitch_gunu": "abd_2023_agustos"}
# büyütülen bölge (alt panel) — kümenin hepsi içinde kalmalı (aşağıda sınanır)
YAKIN_X, YAKIN_Y = (-1.6, 1.15), (-4.0, 19.0)


def _panel_basliklari_sola(fig, n: int, boy: float = 13) -> None:
    for ann in list(fig.layout.annotations)[:n]:
        ann.update(x=0, xanchor="left", font=dict(size=boy))


def _isaretli(x: float, b: int) -> str:
    return ("+" if x > 0 else "") + vir(x, b)


def _xy(e: dict) -> tuple[float, float]:
    """Kadran ekseni: x paranın değeri (log %, artış değer kazancı), y 10 yıllık getiri (bp)."""
    if e["ulke"] == "İngiltere":
        return e["d_sterlin_yuzde"], e["d_gb10y_bp"]
    return e["d_dolar_yuzde"], e["d_us10_bp"]


def _ipucu(e: dict) -> str:
    x, y = _xy(e)
    bas = (f"<b>{e['ad']}</b><br>{tarih(e['ilk'])} kapanışı → {tarih(e['son'])} · {e['n_gun']} iş günü"
           f"{' · alt pencere' if e['alt_pencere'] else ''}<br>kadran: {KADRAN_AD[e['kadran']]}<br>")
    if e["ulke"] == "İngiltere":
        return bas + (f"gilt 2 y {_isaretli(e['d_gb2y_bp'], 1)} · 10 y {_isaretli(e['d_gb10y_bp'], 1)} · "
                      f"30 y {_isaretli(e['d_gb30y_bp'], 1)} bp<br>sterlin (dolara karşı) {yuzde(x, 2, arti=True)}")
    return bas + (f"2 y {_isaretli(e['d_us2_bp'], 0)} · 10 y {_isaretli(e['d_us10_bp'], 0)} bp · "
                  f"10 y vade primi (ACM) {_isaretli(e['d_acmtp10_bp'], 1)} bp<br>dolar sepeti "
                  f"{yuzde(x, 2, arti=True)} · VIX {vir(e['vix_bas'], 2)} → {vir(e['vix_son'], 2)}")


def s07_dm_mali_kadran(o: dict) -> None:
    s = o["b05"]["sekil_07"]
    ad_k = o["b01"]["p1b"]["kadran_adlari_abd"]
    for k, v in OK.items():                          # kısa yazım ölçümün kadran tanımıyla aynı yönde
        assert ("↑" in v.split("·")[0]) == ("↑" in ad_k[k]) and ("para ↑" in v) == ("kazanır" in ad_k[k]), k
    olay = {e["kimlik"]: e for e in s["olaylar"]}
    for k, e in olay.items():                        # büyütülen kümenin noktaları büyütmenin içinde
        x, y = _xy(e)
        if KISA[k][1] == 2:
            assert YAKIN_X[0] < x < YAKIN_X[1] and YAKIN_Y[0] < y < YAKIN_Y[1], k

    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.15, row_heights=[0.58, 0.42],
                        subplot_titles=("Uzun faiz × paranın değeri: dört kadran",
                                        "Merkeze yakın olaylar, büyütülmüş"))
    _panel_basliklari_sola(fig, 2)
    for satir in (1, 2):
        eks = "" if satir == 1 else "2"
        for k, e in olay.items():
            x, y = _xy(e)
            if satir == 2 and KISA[k][1] != 2:
                continue
            renk = ULKE_RENK[e["ulke"]]
            # alt pencereyi ana olayına ince bir çizgiyle bağla
            if k in ANA:
                ax, ay_ = _xy(olay[ANA[k]])
                fig.add_trace(go.Scatter(x=[ax, x], y=[ay_, y], mode="lines", showlegend=False, hoverinfo="skip",
                                         line=dict(color=renk, width=1, dash="dot")), satir, 1)
            fig.add_trace(go.Scatter(
                x=[x], y=[y], mode="markers", showlegend=False, hovertemplate=_ipucu(e) + "<extra></extra>",
                marker=dict(size=11 if not e["alt_pencere"] else 10, color="white" if e["alt_pencere"] else renk,
                            symbol="circle", line=dict(width=2, color=renk))), satir, 1)
            ad, panel, xa, ya, dx, dy = KISA[k]
            if panel == satir:
                # beyaz zemin: alt pencereyi bağlayan noktalı çizgi etiketin üstünden geçmesin
                fig.add_annotation(x=x, y=y, xref=f"x{eks}", yref=f"y{eks}", text=ad, showarrow=False,
                                   xanchor=xa, yanchor=ya, xshift=dx, yshift=dy, bgcolor="rgba(255,255,255,0.85)",
                                   font=dict(size=11, color=renk))
    # lejant: ülke rengi ve alt pencere imi (boş izler)
    for ad, renk, bos in (("ABD", MAVI, False), ("İngiltere", CLARET, False),
                          ("alt pencere (aynı olay; sayıma girmez)", GRI, True)):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=ad,
                                 marker=dict(size=10, color="white" if bos else renk, line=dict(width=2, color=renk))))
    # kadran adları, üst panelin dört köşesinde
    koseler = (("prim", 0.01, 0.99, "left", "top"), ("politika", 0.99, 0.99, "right", "top"),
               ("gevseme", 0.01, 0.01, "left", "bottom"), ("guvenli_liman", 0.99, 0.01, "right", "bottom"))
    for anahtar, xk, yk, xa, ya in koseler:
        baslik = KADRAN_AD[anahtar]
        fig.add_annotation(xref="x domain", yref="y domain", x=xk, y=yk, xanchor=xa, yanchor=ya, showarrow=False,
                           align=xa, text=f"<b>{baslik}</b><br>{OK[anahtar]}",
                           font=dict(size=10.5, color="#5f5f5f"))
    for anahtar, xk, xa in (("prim", 0.01, "left"), ("politika", 0.99, "right")):
        fig.add_annotation(xref="x2 domain", yref="y2 domain", x=xk, y=0.99, xanchor=xa, yanchor="top",
                           showarrow=False, text=f"<b>{anahtar}</b>", font=dict(size=10.5, color="#5f5f5f"))
    # büyütülen bölgenin çerçevesi
    fig.add_shape(type="rect", xref="x", yref="y", x0=YAKIN_X[0], x1=YAKIN_X[1], y0=YAKIN_Y[0], y1=YAKIN_Y[1],
                  line=dict(color=GRI, width=1, dash="dash"))
    fig.add_annotation(xref="x", yref="y", x=YAKIN_X[1], y=YAKIN_Y[0], xanchor="left", yanchor="top",
                       showarrow=False, text="alt panelde büyütüldü", font=dict(size=10, color="#5f5f5f"))
    for satir, (xr, yr) in ((1, ([-6.3, 6.3], [-45, 128])), (2, (list(YAKIN_X), list(YAKIN_Y)))):
        fig.update_xaxes(range=xr, zeroline=True, zerolinecolor="#8a8a8a", zerolinewidth=1.2, row=satir, col=1)
        fig.update_yaxes(range=yr, zeroline=True, zerolinecolor="#8a8a8a", zerolinewidth=1.2,
                         title_text="10 yıllık getiri değişimi (bp)", row=satir, col=1)
        fig.update_xaxes(title_text="paranın değerindeki değişim, log % (artış: değer kazancı)", row=satir, col=1)
    ks = s["kadran_sayisi"]
    ana = [e for e in s["olaylar"] if not e["alt_pencere"]]
    # başlıktaki sayım ölçümün kadran sayımıdır (sözcükle yazıldığı için sınanır)
    assert len(ana) == s["n"] == 6 and ks == {"prim": 4, "politika": 2}
    assert ks == {kd: sum(e["kadran"] == kd for e in ana) for kd in ks}
    # Başlık bloğu dar ekrana göre sarılır ve üstten çapalanır; yükseklik satır sayısından (sekil_ortak).
    baslik = baslik_koy(fig, "Şekil 07 — ABD ve İngiltere'de altı mali olayın dördü prim kadranında: uzun faiz ↑, "
                             "para ↓", [
        f"Olay öncesi kapanıştan pencere sonuna, {tarih(s['ilk'])}–{tarih(s['son'])} · ABD: 10 yıllık getiri "
        "(ABD Hazinesi, ≈15:30 New\u00a0York), para: altı G10 kurunun dolar yönünde eşit ağırlıklı sepeti (CNBC, "
        "New\u00a0York 17:00) · İngiltere: 10 yıllık gilt (Londra kapanışı), para: sterlin dolara karşı (CNBC, New\u00a0"
        f"York 17:00) · ana pencerelerin kadranı: {ks.get('prim', 0)} prim, {ks.get('politika', 0)} politika · on "
        "olaydan az bağımsız gözlem, test istatistiği yok",
    ])
    _yaz(fig, "07_dm_mali_kadran.html", yukseklik(baslik, 658))   # 658: çizim ve alt pay (eski 880 − 222)


def _ay_bas(a: str) -> str:
    return a + "-01"


def _ay_son(a: str) -> str:
    """AA ayının son günü (dönem medyanı çizgisi ayın sonuna kadar uzar)."""
    y, m = int(a[:4]), int(a[5:7])
    gun = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31,
           30, 31][m - 1]
    return f"{a}-{gun:02d}"


def s08_beklenti_disi_fark(o: dict) -> None:
    b = o["b05"]
    s = b["sekil_08"]
    p = b["p5c"]
    k = p["kirlilik"]
    x = [_ay_bas(a) for a in s["ay"]]
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.065,
                        row_heights=[0.27, 0.27, 0.20, 0.26],
                        subplot_titles=("1y1y forward ve anket patikası (%, bileşik)",
                                        "Beklenti dışı fark = forward − anket (bp)",
                                        "Koridor farkı: fonlama maliyeti − politika faizi (bp)",
                                        "DİBS–TLREF bazı: 3 ay DİBS − TLREF (bp)"))
    _panel_basliklari_sola(fig, 4)
    ip = "%{x|%m.%Y}: %%{y:.2f}"                       # yüzde önde (ilk % düz yazıdır)
    # 1) seviyeler
    fig.add_trace(go.Scatter(x=x, y=s["f_1y1y"], mode="lines", name="1 yıl sonrası 1 yıllık forward (DİBS)",
                             line=dict(color=MAVI, width=1.8), hovertemplate=ip + "<extra>forward</extra>"), 1, 1)
    fig.add_trace(go.Scatter(x=x, y=s["anket_bilesik"], mode="lines",
                             name="anket faiz patikası (12 ve 24 ay ortalaması)", line=dict(color=CLARET, width=1.8),
                             hovertemplate=ip + "<extra>anket</extra>"), 1, 1)
    # 2) fark ve dönem medyanları
    fig.add_trace(go.Scatter(x=x, y=s["fark_bp"], mode="lines", showlegend=False, line=dict(color=MUREKKEP, width=1.6),
                             hovertemplate="%{x|%m.%Y}: %{y:.0f} bp<extra>beklenti dışı fark</extra>"), 2, 1)
    mx, my, mt = [], [], []
    for d in p["donem"].values():
        mx += [_ay_bas(d["ilk"]), _ay_son(d["son"]), None]
        my += [d["fark_medyan_bp"]] * 2 + [None]
        etik = f"{ay(_ay_bas(d['ilk']))}–{ay(_ay_bas(d['son']))} medyanı {vir(d['fark_medyan_bp'], 0)} bp ({d['n']} ay)"
        mt += [etik, etik, None]
    fig.add_trace(go.Scatter(x=mx, y=my, mode="lines", name="dönem medyanı", line=dict(color=TURUNCU, width=2.6),
                             text=mt, hovertemplate="%{text}<extra></extra>"), 2, 1)
    # 3) koridor farkı (faizin ay içinde değiştiği 2018 öncesi aylar ölçülmedi: boşluk)
    fig.add_trace(go.Scatter(x=x, y=s["koridor_bp"], mode="lines", showlegend=False, connectgaps=False,
                             line=dict(color=GRI, width=1.6),
                             hovertemplate="%{x|%m.%Y}: %{y:.0f} bp<extra>koridor farkı</extra>"), 3, 1)
    # 4) DİBS–TLREF bazı, iki tanım
    fig.add_trace(go.Scatter(x=x, y=s["baz_basit_bp"], mode="lines", name="baz, TLREF basit", connectgaps=False,
                             line=dict(color=YESIL, width=1.8),
                             hovertemplate="%{x|%m.%Y}: %{y:.0f} bp<extra>TLREF basit</extra>"), 4, 1)
    fig.add_trace(go.Scatter(x=x, y=s["baz_bp"], mode="lines", name="baz, TLREF bileşiğe çevrilmiş",
                             connectgaps=False, line=dict(color=YESIL, width=1.4, dash="dot"),
                             hovertemplate="%{x|%m.%Y}: %{y:.0f} bp<extra>TLREF bileşik</extra>"), 4, 1)
    # yönetilen kur dönemi: dört panelde gölge, üst panelde adı
    y0, y1 = s["yonetilen_kur_donemi"]
    fig.add_vrect(x0=_ay_bas(y0), x1=_ay_son(y1), fillcolor="rgba(138,138,138,0.16)", line_width=0, layer="below",
                  row="all", col=1)
    fig.add_annotation(xref="x", yref="y domain", x=_ay_bas(y0), y=0.98, xanchor="right", yanchor="top",
                       showarrow=False, text="yönetilen kur", font=dict(size=10.5, color="#5f5f5f"))
    for satir, bas in ((1, "%"), (2, "bp"), (3, "bp"), (4, "bp")):
        fig.update_yaxes(title_text=bas, row=satir, col=1)
        if satir > 1:
            fig.update_yaxes(zeroline=True, zerolinecolor="#8a8a8a", zerolinewidth=1, row=satir, col=1)
    fig.update_xaxes(range=[_ay_bas(s["ay"][0]), _ay_son(s["ay"][-1])], tickformat="%Y")
    kor_ilk = k["koridor_farki"]["karar_sonrasi"]["ilk"]
    tlref_ilk = k["dibs_tlref_bazi"]["dugum_tanisi"]["ilk"]
    ah = k["anket_ay_etiketi"]
    # başlığın iddiası: son dönemin medyanı dönemlerin en büyüğü (medyanla da ortalamayla da)
    dd = sorted(p["donem"].values(), key=lambda d: d["ilk"])
    son_d = dd[-1]
    assert son_d["fark_medyan_bp"] == max(d["fark_medyan_bp"] for d in dd)
    assert son_d["fark_ort_bp"] == max(d["fark_ort_bp"] for d in dd) and son_d["ilk"][:4] == "2023"  # ek: 2023'ten
    # Başlık hükmü sınırlayan kirliliklerin SAYISINI söyler: üç kirlilik var (koridor farkı, DİBS–TLREF bazı,
    # anketin ay etiketi), ikisi çizili; üçüncüsünün büyüklüğü alt başlıkta.
    baslik = baslik_koy(fig, f"Şekil 08 — Beklenti dışı fark {ay(_ay_bas(son_d['ilk']))}'ten beri dönemlerin en "
                             f"genişi (medyan {vir(son_d['fark_medyan_bp'], 0)} bp); üç kirlilik hükmü sınırlıyor "
                             "(ikisi çizili)", [
        f"Aylık ortalama, {ay(_ay_bas(s['ilk']))}–{ay(_ay_bas(s['son']))} (günlük {tarih(p['ilk_gun'])}–"
        f"{tarih(p['son_gun'])}) · forward: TCMB DİBS göstergelerinden sıfır kupon eğri, yıllık bileşik · anket: "
        "Piyasa Katılımcıları Anketi 12 ve 24 ay sonrası politika faizi, yamuk ortalama, "
        "(1\u00a0+\u00a0r/52)^52\u00a0−\u00a01 · gölge: yönetilen kur",     # formül satır sonunda bölünmez
        f"Koridor farkı: TCMB ağırlıklı ortalama fonlama maliyeti − politika faizi; {tarih(kor_ilk)} öncesi faizin "
        f"ay içinde değiştiği aylar boş · baz: 3 aylık DİBS − TLREF, TLREF'in başladığı {tarih(tlref_ilk)}'den · "
        "üçüncü kirlilik çizilmedi: anket ayın ilk gününden geçerli sayılsa aylık fark ortalama "
        f"{vir(ah['karsi_hiza_ort_mutlak_bp'], 0)} bp oynar",
    ])
    _yaz(fig, "08_beklenti_disi_fark.html", yukseklik(baslik, 652))   # 652: çizim ve alt pay (eski 900 − 248)
