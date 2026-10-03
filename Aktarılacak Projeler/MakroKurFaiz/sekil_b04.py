#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 4 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from datetime import date

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         baslik_koy, make_subplots, tarih, vir, yukseklik, yuzde, _yaz)

# Dönemlerin rengi (varlığı dönem belirler): yönetilen kur dönemi gri, çünkü orada kurun
# sürprize tepki vermemesi tasarım gereğidir.
DONEM_RENK = {"d2013_2020": MAVI, "d2021": CLARET, "yonetilen": GRI, "d2023_2026": TURUNCU}
YAZI_GRI = "#5f5f5f"                   # gri dönemin yazısı (açık gri metin okunmaz)


def _isaretli(x: float, b: int) -> str:
    """Eğim yazımı: işaret her zaman yazılır (+122 · −1,48)."""
    return ("+" if x > 0 else "") + vir(x, b)


def _donem_adi(r: dict, kod: str) -> str:
    on = "yönetilen kur " if kod == "yonetilen" else ""
    return f"{on}{ay(r['ilk'])}–{ay(r['son'])} · {r['n']} ay"


def _panel_basliklari_sola(fig, n: int, boy: float = 13) -> None:
    """make_subplots başlıkları ortalıdır ve dar ekranda iki yandan taşar: sola yasla, küçült."""
    for ann in list(fig.layout.annotations)[:n]:
        ann.update(x=0, xanchor="left", font=dict(size=boy))


def s05_tufe_surprizi(o: dict) -> None:
    b = o["b04"]
    s = b["sekil_05"]
    a = s["aylik"]
    sp = s["surpriz"]
    yg = b["p4a"]["yayim_gunu"]
    ai = b["p4a"]["aylik_iliski"]
    if s["yayim_gunu"]["kapiyi_gecen"]:              # bu figür aylık ilişkinin figürüdür; kapı geçerse
        raise SystemExit("Şekil 05: yayım günü kapısını geçen seri var; figür yeniden tasarlanmalı")  # pragma: no cover

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
                        subplot_titles=("2 yıllık DİBS: yayım ayındaki değişim (bp)",
                                        "USD/TRY: yayım ayındaki değişim (log %)"))
    _panel_basliklari_sola(fig, 2)
    seriler = (("d_n2y", "d_n2y_bp", 1), ("d_usdtry", "d_usdtry_yuzde", 2))
    kodlar = [k for k, *_ in s["rejimler"]]
    assert a["ay"] == sp["ay"], "aylık tepki ile çöküş işaretleri aynı aylara dizili olmalı"
    tablo = {1: ["<b>eğim, bp/puan (t)</b>"], 2: ["<b>eğim, log %/puan (t)</b>"]}
    for kod in kodlar:
        renk = DONEM_RENK[kod]
        yazi = YAZI_GRI if renk == GRI else renk
        idx = [i for i, r in enumerate(a["rejim"]) if r == kod]
        for anahtar, ser, satir in seriler:
            reg = ai[anahtar][kod]
            xs = [a["surpriz_puan"][i] for i in idx]
            ys = [a[ser][i] for i in idx]
            # ipucu sayıları sözleşmeyle (ondalık virgül, eksi U+2212, yüzde önde) önceden yazılır
            cd = [[ay(a["ay"][i] + "-01"), _isaretli(xs[j], 2),
                   (f"{_isaretli(ys[j], 0)} bp" if satir == 1 else yuzde(ys[j], 2, arti=True))]
                  for j, i in enumerate(idx)]
            fig.add_trace(go.Scatter(
                x=xs, y=ys, mode="markers", name=_donem_adi(reg, kod), legendgroup=kod, showlegend=(satir == 1),
                marker=dict(color=renk, size=7, opacity=0.8, line=dict(width=0.6, color="white")),
                customdata=cd,
                hovertemplate=("%{customdata[0]} TÜFE'si · sürpriz %{customdata[1]} puan<br>yayım ayında "
                               + ("2 yıllık DİBS" if satir == 1 else "USD/TRY (log)")
                               + " %{customdata[2]}<extra></extra>")), satir, 1)
            # dönem içi en küçük kareler doğrusu, dönemin kendi sürpriz aralığında
            x0, x1 = min(xs), max(xs)
            olculu = reg["hukum"] == "ölçülü"
            egim_y = (f"{_isaretli(reg['egim'], 0)}" if satir == 1 else f"{yuzde(reg['egim'], 2, arti=True)}")
            fig.add_trace(go.Scatter(
                x=[x0, x1], y=[reg["sabit"] + reg["egim"] * x0, reg["sabit"] + reg["egim"] * x1], mode="lines",
                legendgroup=kod, showlegend=False,
                line=dict(color=renk, width=2.6 if olculu else 2.0, dash="solid" if olculu else "dash"),
                hovertemplate=(f"{_donem_adi(reg, kod)}<br>eğim {egim_y}{' bp' if satir == 1 else ''}/puan · "
                               f"t {vir(reg['t'], 1)} · {reg['hukum']}<extra></extra>")), satir, 1)
            kisa = ("yönetilen" if kod == "yonetilen" else reg["ilk"][:4] if reg["ilk"][:4] == reg["son"][:4]
                    else f"{reg['ilk'][:4]}–{reg['son'][2:4]}")       # dar ekranda tablo boş köşeye sığsın
            tablo[satir].append(f"<span style='color:{yazi}'>{kisa} {egim_y} ({vir(reg['t'], 1)})"
                                f"{' ölçülü' if olculu else ''}</span>")
    # kur çöküşü işaretleri yalnız kur panelinde: ters nedensellik kurun kendi hareketinden doğar.
    # İşaret noktanın TÜFE ayına aittir (x'in ayı); dikey eksen bir sonraki ayın (yayım ayının) değişimidir.
    isaretler = (("cokus_ayi", "circle-open", 14, "halka: TÜFE ayında 4σ TL değer kaybı günü var"),
                 ("cokus_ertesi_ay", "square-open", 12, "kare: o çöküşten sonraki TÜFE ayı"))
    for alan, sembol, boy, ad in isaretler:
        idx = [i for i, v in enumerate(sp[alan]) if v]
        fig.add_trace(go.Scatter(
            x=[a["surpriz_puan"][i] for i in idx], y=[a["d_usdtry_yuzde"][i] for i in idx], mode="markers",
            name=ad, legendgroup=alan, hoverinfo="skip",
            marker=dict(symbol=sembol, size=boy, color=MUREKKEP, line=dict(width=1.1, color=MUREKKEP))), 2, 1)
    # eğim tabloları boş köşelerde: 2 yıllıkta sağ alt, kurda sağ üst
    for satir, (yk, ya) in ((1, (0.02, "bottom")), (2, (0.98, "top"))):
        eks = "" if satir == 1 else "2"
        fig.add_annotation(xref=f"x{eks} domain", yref=f"y{eks} domain", x=0.995, y=yk, xanchor="right",
                           yanchor=ya, align="left", showarrow=False, text="<br>".join(tablo[satir]),
                           font=dict(size=10, color=MUREKKEP), bgcolor="rgba(255,255,255,0.85)")

    # y aralıkları tablolara boş köşe bırakır (2 yıllıkta altta, kurda üstte); bütün noktalar içeride
    for satir, bas, aralik in ((1, "bp", [-1000, 950]), (2, "log % (artış: TL değer kaybı)", [-12, 41])):
        fig.update_yaxes(title_text=bas, zeroline=True, zerolinecolor="#cfc4ab", range=aralik, row=satir, col=1)
        fig.update_xaxes(zeroline=True, zerolinecolor="#cfc4ab", range=[-2.9, 11.2], row=satir, col=1)
    fig.update_xaxes(title_text="TÜFE sürprizi (puan)", row=2, col=1)
    # Başlığın iki iddiası ölçümün hükmüne bağlı: 2 yıllık eğimleri artı ama tarif edici; kurda ölçülü tek
    # eğim 2013–2020, ve çöküş ayları dışarıda kalınca ölçülü olmaktan çıkıyor.
    k2y, kur = ai["d_n2y"], ai["d_usdtry"]
    assert k2y["d2021"]["egim"] > 0 and k2y["d2023_2026"]["egim"] > 0
    assert [k for k in kodlar if kur[k]["hukum"] == "ölçülü"] == ["d2013_2020"]
    assert kur["cokus_aylari_haric_d2013_2020"]["hukum"] == "tarif edici"
    assert all(k2y[k]["hukum"] == "tarif edici" for k in kodlar)
    assert all(ai[c][k]["oos"].get("durum") == "kurulmadi" for c in ("d_n2y", "d_usdtry") for k in ("d2021", "yonetilen"))
    # Başlık bloğu dar ekrana göre sarılır ve üstten çapalanır; yükseklik satır sayısından (sekil_ortak).
    # Alt başlığın her öğesi bir anlam birimidir: cümle satır ortasından elle bölünmez.
    baslik = baslik_koy(fig, "Şekil 05 — Sürpriz yüksekken 2 yıllık 2021'de ve 2023'ten sonra yükseliyor; kurdaki "
                             "tek ölçülü eğim çöküşlere yaslı", [
        "Sürpriz = gerçekleşen aylık TÜFE (TÜİK) − Piyasa Katılımcıları Anketi'nin aynı ay beklentisi (TCMB), "
        f"puan · TÜFE ayları {ay(s['ilk'] + '-01')}–{ay(s['son'] + '-01')} ({yg['n_yayim']} yayım, "
        f"{tarih(yg['ilk'])}–{tarih(yg['son'])}) · renk: TÜFE ayının dönemi",
        "Yayım günü penceresi kurulmadı (tepki yayım gününde sıradan günlerden ayrışmıyor): her nokta yayım "
        "ayında ay sonundan ay sonuna değişimdir, o ayın öbür haberlerini de taşır · USD/TRY: Yahoo Finance",
        "doğru: dönem içi en küçük kareler, t Newey–West · düz: ölçülü (|t| ≥ 2, iki örneklem dışı kıyas da "
        "geçiliyor) · kesikli: tarif edici (t eşiği ya da örneklem dışı kıyas geçilmiyor; 2021'de ve yönetilen "
        "kurda kıyas kurulamıyor)",
    ])
    _yaz(fig, "05_tufe_surprizi.html", yukseklik(baslik, 626))   # 626: çizim ve alt pay (eski 900 − 274)


def s06_tr2021_abd2022(o: dict) -> None:
    """Türkiye 2021 (indirim döngüsü) ile ABD 2022 (artırım döngüsü): aynı enflasyon haberi, iki ters kur."""
    p = o["b04"]["p4c"]
    tr, us = p["turkiye_2021"], p["abd_2022"]
    TR, US = CLARET, MAVI
    tr_ad = f"Türkiye {tarih(tr['pencere'][0])}–{tarih(tr['pencere'][1])} (indirim döngüsü)"
    us_ad = f"ABD {tarih(us['pencere'][0])}–{tarih(us['pencere'][1])} (artırım döngüsü)"
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.13, row_heights=[0.36, 0.40, 0.24],
                        subplot_titles=("TÜFE ve reel politika faizi (%): ○ baş → ● son",
                                        "Faizin dönem değişimi (bp)",
                                        "Paranın değeri, log % (artış: değer kazancı)"))
    _panel_basliklari_sola(fig, 3)

    # 1) seviye: dönem başı → sonu (dumbbell); başın etiketi altta, sonunki üstte: yakın uçlar çakışmaz
    satirlar1 = [
        ("Türkiye TÜFE", TR, tr["yillik_tufe"]["ilk_yuzde"], tr["yillik_tufe"]["son_yuzde"],
         f"yıllık TÜFE {ay(tr['yillik_tufe']['ilk_ay'] + '-01')} → {ay(tr['yillik_tufe']['son_ay'] + '-01')}"),
        ("ABD TÜFE", US, us["yillik_tufe"]["ilk_yuzde"], us["yillik_tufe"]["son_yuzde"],
         f"yıllık TÜFE {ay(us['yillik_tufe']['ilk_ay'] + '-01')} → {ay(us['yillik_tufe']['son_ay'] + '-01')}"),
        ("Türkiye reel faiz", TR, tr["reel_politika"]["ilk_puan"], tr["reel_politika"]["son_puan"],
         "politika faizi − yıllık TÜFE"),
        ("ABD reel faiz", US, us["reel_politika"]["ilk_puan"], us["reel_politika"]["son_puan"],
         "politika faizi − yıllık TÜFE"),
    ]
    for ad, renk, bas, son, notu in satirlar1:
        fig.add_trace(go.Scatter(x=[bas, son], y=[ad, ad], mode="lines", line=dict(color=renk, width=2.2),
                                 showlegend=False, hoverinfo="skip"), 1, 1)
        fig.add_trace(go.Scatter(x=[bas], y=[ad], mode="markers+text", showlegend=False,
                                 marker=dict(symbol="circle-open", size=10, color=renk, line=dict(width=2)),
                                 text=[yuzde(bas, 1)], textposition="bottom center",
                                 textfont=dict(size=10.5, color=renk),
                                 hovertemplate=f"{ad} ({notu})<br>dönem başı {yuzde(bas, 2)}<extra></extra>"), 1, 1)
        fig.add_trace(go.Scatter(x=[son], y=[ad], mode="markers+text", showlegend=False,
                                 marker=dict(size=10, color=renk), text=[yuzde(son, 1)], textposition="top center",
                                 textfont=dict(size=10.5, color=renk),
                                 hovertemplate=f"{ad} ({notu})<br>dönem sonu {yuzde(son, 2)}<extra></extra>"), 1, 1)
    fig.update_yaxes(range=[len(satirlar1) - 0.4, -0.6], row=1, col=1)     # ters sıra + etiket payı
    fig.update_xaxes(title_text="%", zeroline=True, zerolinecolor="#cfc4ab", range=[-30, 44], row=1, col=1)

    # 2) faiz değişimi (bp): politika, 2 yıllık, uzun uç
    kat = ["politika faizi", "2 yıllık", "uzun uç<br>(5 y · 10 y)"]
    tr_bp = [tr["politika"]["degisim_bp"], tr["n2y"]["degisim_bp"], tr["n5y"]["degisim_bp"]]
    us_bp = [us["politika"]["degisim_bp"], us["us2"]["degisim_bp"], us["us10"]["degisim_bp"]]
    tr_ip = [f"{yuzde(tr['politika']['ilk_yuzde'], 2)} → {yuzde(tr['politika']['son_yuzde'], 2)}",
             f"{yuzde(tr['n2y']['ilk_yuzde'], 2)} → {yuzde(tr['n2y']['son_yuzde'], 2)}",
             f"5 yıllık {yuzde(tr['n5y']['ilk_yuzde'], 2)} → {yuzde(tr['n5y']['son_yuzde'], 2)}"]
    us_ip = [f"{yuzde(us['politika']['ilk_yuzde'], 3)} → {yuzde(us['politika']['son_yuzde'], 3)} (ay sonu)",
             f"{yuzde(us['us2']['ilk_yuzde'], 2)} → {yuzde(us['us2']['son_yuzde'], 2)}",
             f"10 yıllık {yuzde(us['us10']['ilk_yuzde'], 2)} → {yuzde(us['us10']['son_yuzde'], 2)}"]
    kat_ad = ["politika faizi", "2 yıllık", "uzun uç"]
    for ad, renk, deg, grup, ip in ((tr_ad, TR, tr_bp, "tr", tr_ip), (us_ad, US, us_bp, "us", us_ip)):
        fig.add_trace(go.Bar(y=kat, x=deg, orientation="h", name=ad, legendgroup=grup, marker_color=renk,
                             marker_line_width=0, text=[_isaretli(v, 0) for v in deg], textposition="inside",
                             insidetextanchor="middle", textfont=dict(size=11, color="white"),
                             customdata=[[k, f"{_isaretli(v, 0)} bp", i] for k, v, i in zip(kat_ad, deg, ip)],
                             hovertemplate="%{customdata[0]}: %{customdata[1]} · %{customdata[2]}<extra>" + ad
                                           + "</extra>"), 2, 1)
    fig.update_yaxes(autorange="reversed", row=2, col=1)
    fig.update_xaxes(title_text="bp", zeroline=True, zerolinecolor="#8a8a8a", range=[-560, 820], row=2, col=1)

    # 3) paranın değeri (log %): TL dolara karşı = −Δlog(USD/TRY); dolar altı G10 parasına karşı
    tl = -tr["usdtry"]["log_degisim_yuzde"]
    tl_tcmb = -tr["usdtry_tcmb_saglamlik"]["log_degisim_yuzde"]
    dolar = us["dolar_g10"]["log_degisim_yuzde"]
    cuma = date.fromisoformat(tr["pencere"][1]).weekday() == 4
    for k, v, renk, ad, grup, konum, ipucu in (
            ("TL<br>(dolara karşı)", tl, TR, tr_ad, "tr", "inside",
             f"USD/TRY {vir(tr['usdtry']['ilk_duzey'], 4)} → {vir(tr['usdtry']['son_duzey'], 4)}"
             f"{' (dönem sonu cuma: hafta sonunu da taşır)' if cuma else ''}"
             f"<br>TCMB gösterge kuruyla {yuzde(tl_tcmb, 2, arti=True)}"),
            ("dolar<br>(G10'a karşı)", dolar, US, us_ad, "us", "outside",
             f"altı G10 parasına karşı (eşit ağırlık)<br>DXY {vir(us['dxy_saglamlik']['ilk_duzey'], 2)} → "
             f"{vir(us['dxy_saglamlik']['son_duzey'], 2)}")):
        fig.add_trace(go.Bar(y=[k], x=[v], orientation="h", name=ad, legendgroup=grup, showlegend=False,
                             marker_color=renk, marker_line_width=0, text=[yuzde(v, 1, arti=True)],
                             textposition=konum, insidetextanchor="middle", cliponaxis=False,
                             textfont=dict(size=11, color="white" if konum == "inside" else renk),
                             hovertemplate=f"{k.replace('<br>', ' ')}: {yuzde(v, 2, arti=True)} (log)<br>{ipucu}"
                                           "<extra></extra>"), 3, 1)
    fig.update_yaxes(autorange="reversed", row=3, col=1)
    fig.update_xaxes(title_text="log %", zeroline=True, zerolinecolor="#8a8a8a", range=[-52, 32], row=3, col=1)
    fig.update_layout(barmode="group", bargap=0.26, bargroupgap=0.08)

    # başlığın dört iddiası verinin işaretleriyle sınanır
    assert tr["yillik_tufe"]["son_yuzde"] > tr["yillik_tufe"]["ilk_yuzde"]
    assert us["yillik_tufe"]["son_yuzde"] > us["yillik_tufe"]["ilk_yuzde"]
    assert tr["politika"]["degisim_bp"] < 0 < us["politika"]["degisim_bp"] and tl < 0 < dolar
    baslik = baslik_koy(fig, "Şekil 06 — Enflasyon ikisinde de yükseldi: faizi indiren Türkiye'de para değer "
                             "kaybetti, artıran ABD'de kazandı", [
        f"Dönem başı → sonu · Türkiye {tarih(tr['pencere'][0])}–{tarih(tr['pencere'][1])}: TCMB politika faizi "
        "(günlük), 2 ve 5 yıllık DİBS (gün sonu), yıllık TÜFE (TÜİK), USD/TRY Yahoo Finance günlük barı (Londra "
        "gece yarısı" + ("; dönem sonu cuma, kur hafta sonunu da taşır)" if cuma else ")")
        + f" · ABD {tarih(us['pencere'][0])}–{tarih(us['pencere'][1])}: politika faizi (BIS, ay sonu), 2 ve 10 yıllık "
        "Hazine, yıllık TÜFE (BLS), dolar: altı G10 kurunun eşit ağırlıklı sepeti (CNBC, New York 17:00) · reel "
        "faiz = politika − yıllık TÜFE · uzun uç: Türkiye 5 yıl (10 yıllık düğüm yok), ABD 10 yıl · iki gözlemli "
        "vaka karşılaştırması, test değil",
    ])
    _yaz(fig, "06_tr2021_abd2022.html", yukseklik(baslik, 652))   # 652: çizim ve alt pay (eski 900 − 248)
