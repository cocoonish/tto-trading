#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — Bölüm 2 figürleri. Sayılar `veri/olcum.json`dan (sekil_ortak üzerinden)."""
from __future__ import annotations

from sekil_ortak import (ACIK_CLARET, ACIK_MAVI, CLARET, GRI, MAVI, MUREKKEP, TURUNCU, YESIL, ay, go,  # noqa: F401
                         baslik_koy, make_subplots, tarih, vir, yukseklik, yuzde, _yaz)

SERI_AD = {"n3a": "DİBS 3 ay", "n2y": "DİBS 2 yıl", "n5y": "DİBS 5 yıl", "usdtry": "USD/TRY",
           "usdtry_tcmb": "TCMB kuru", "us2": "ABD 2 yıl", "dolar_sepeti": "dolar sepeti"}
OLAY_AD = {"ppk": "PPK kararı", "tufe": "TÜFE yayımı", "fomc": "FOMC kararı",
           "abd_istihdam": "ABD istihdam", "abd_tufe": "ABD TÜFE"}
# ısı ölçeği: 1 = sıradan gün (beyaz); altı sakin (mavi), üstü hareketli (bordo)
OLCEK = [[0.0, "#5f86ad"], [0.42, "#dfe7ef"], [0.5, "#ffffff"], [0.58, "#f1dcdf"], [1.0, CLARET]]
ZMIN, ZMAX = 0.4, 1.6


def _hukum(r: dict) -> tuple[str, str]:
    """Satırın kapı hükmü (okur dili) ve rengi."""
    if r.get("kurulabilir"):
        return "kurulur", YESIL
    if not r.get("kapi"):
        return "geçmedi", CLARET
    if r.get("guclu_sinirda"):
        bas = "sınırda"
    elif r.get("kapi_guclu"):
        bas = "güçlü"
    else:
        bas = "zayıf"
    return (bas + " · saate uymaz" if not r.get("saat_tutarli") else bas), TURUNCU


def s02_plasebo(o: dict) -> None:
    b = o["b02"]
    s = b["sekil_02"]
    kapi = {(r["seri"], r["olay"]): r for r in b["p2"]["kapi"]}
    sat = {(r["seri"], r["olay"]): r for r in s["satirlar"]}
    kayma = s["kayma"]

    def satir(seri, olay, etiket=None):
        r = dict(sat[(seri, olay)])
        k = kapi.get((seri, olay), {})
        r["guclu_sinirda"] = k.get("guclu_sinirda", False)
        r["etiket"] = etiket or SERI_AD[seri]
        return r

    tr = ("n3a", "n2y", "n5y", "usdtry", "usdtry_tcmb")
    hiza = []
    for seri in tr:                       # kaymasız satır saatle bağdaşmıyorsa serinin ölçülmüş saatine kaydır
        k = kapi[(seri, "ppk")]
        if not k["saat_tutarli"]:
            for L in k["saat_beklenen_kayma"]:
                if L and (seri, f"ppk_kayma_{L}") in sat:
                    hiza.append(satir(seri, f"ppk_kayma_{L}", f"{SERI_AD[seri]} (+{L})"))
    gruplar = [
        ("PPK kararı, 14:00 TSİ: etiketin kendi günü", [satir(x, "ppk") for x in tr]),
        ("PPK kararı, seri kendi saatine hizalı (+k iş günü)", hiza),
        ("TÜFE yayımı, 10:00 TSİ", [satir(x, "tufe") for x in tr]),
        ("FOMC kararı, 14:00 New York", [satir(x, "fomc") for x in ("us2", "dolar_sepeti")]),
    ]
    n = [len(g[1]) for g in gruplar]
    fig = make_subplots(rows=len(gruplar), cols=1, shared_xaxes=True, row_heights=[x / sum(n) for x in n],
                        vertical_spacing=0.075, subplot_titles=[g[0] for g in gruplar])
    for gi, (_, rows) in enumerate(gruplar, start=1):
        z = [r["oran"] for r in rows]
        cd = [[f"{r['etiket']} · {OLAY_AD.get(r['olay'].split('_kayma')[0], r['olay'])} · {r['n_olay']} olay"] * len(kayma)
              for r in rows]
        fig.add_trace(go.Heatmap(z=z, x=kayma, y=list(range(len(rows))), coloraxis="coloraxis", xgap=2, ygap=2,
                                 customdata=cd,
                                 hovertemplate="%{customdata}<br>uzaklık %{x} iş günü: oran %{z:.2f}<extra></extra>"),
                      gi, 1)
        # hücre değerleri (renge göre yazı rengi) ve tepe çerçevesi
        xs, ys, tx, renk = [], [], [], []
        for yi, r in enumerate(rows):
            for kk, v in zip(kayma, r["oran"]):
                xs.append(kk), ys.append(yi), tx.append(vir(v, 2)), renk.append("white" if v >= 1.42 else MUREKKEP)
            tepe = kayma[max(range(len(kayma)), key=lambda j: r["oran"][j])]
            fig.add_shape(type="rect", x0=tepe - 0.47, x1=tepe + 0.47, y0=yi - 0.45, y1=yi + 0.45,
                          line=dict(color=MUREKKEP, width=2), row=gi, col=1)
            h, hr = _hukum(r)
            fig.add_annotation(x=2.68, y=yi, text=h, showarrow=False, xanchor="left", align="left",
                               font=dict(size=10.5, color=hr), row=gi, col=1)
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="text", text=tx, textfont=dict(size=10.5, color=renk),
                                 hoverinfo="skip", showlegend=False), gi, 1)
        fig.update_yaxes(tickvals=list(range(len(rows))), ticktext=[r["etiket"] for r in rows],
                         autorange="reversed", showgrid=False, ticks="", row=gi, col=1)
        fig.update_xaxes(range=[-2.55, 4.55], tickvals=kayma, ticktext=["−2", "−1", "0", "+1", "+2"],
                         showticklabels=True, showgrid=False, ticks="", showline=False, row=gi, col=1)
    # alt grafik başlıkları sola; 12 px: 12,5'te en uzunu ("seri kendi saatine hizalı") telefonun gömme
    # çerçevesinde (geniş gömme 356 px) sağ ucundan 6 piksel kırpılıyordu
    for a in fig.layout.annotations:
        if a.yanchor == "bottom" and a.yref == "paper" and a.text in [g[0] for g in gruplar]:
            a.update(x=0, xanchor="left", font=dict(size=12))
    fig.update_layout(coloraxis=dict(colorscale=OLCEK, cmin=ZMIN, cmax=ZMAX, showscale=False), showlegend=False)

    # alt not: hükümlerin anlamı, kontrol kümesinin düzlüğü, kurulmayan olaylar
    kontrol = [v for r in s["satirlar"] if r["olay"] == "rastgele" for v in r["oran"]]
    kurulmayan = sorted({OLAY_AD[r["olay"]].replace("ABD ", "") for r in s["satirlar"] if r["durum"] == "kurulmadi"})
    kurulmayan[0] = "ABD " + kurulmayan[0]
    sebep = sorted({r["sebep"] for r in s["satirlar"] if r["durum"] == "kurulmadi"})
    yk = b["p2"]["yonetilen_kur_donemi"][0]
    # TÜFE'de DİBS satırları serinin saatine kaydırılınca (+1, +2): profil ölçümde yok, yalnız hüküm var
    tk = [r for r in b["p2"]["tarih_sozlesmesi"]["ay_ici_gun_etkisi"]["tufe_kayma_taramasi"] if r["saat_tutarli"]]
    tk_kayma = ", ".join(f"+{k}" for k in sorted({r["kayma"] for r in tk}))
    tk_gecen = sum(1 for r in tk if r["kapi"])
    tk_hukum = "hiçbiri geçmez" if tk_gecen == 0 else f"{tk_gecen} tanesi geçer"
    notlar = [
        "hücre: olay gününe k iş günü uzaklıkta ortalama mutlak değişim / sıradan",
        "günlerinki (1 = sıradan gün) · çerçeve: tepe · takvimler TCMB, TÜİK, Fed",
        "kurulur: tepe 0'da, rastgele kümelerin %95'ini aşar ve serinin saatine uyar",
        "zayıf: %95'i aşmaz · sınırda: aşma benzetim hata payında, hüküm dönebilir",
        "geçmedi: tepe 0'da değil · saate uymaz: serinin ölçülmüş saatiyle bağdaşmaz",
        f"TÜFE'de DİBS kendi saatine kaydırılınca ({tk_kayma}): {len(tk)} satırın {tk_hukum}",
        f"kontrol: rastgele gün kümelerinin ortalama profili {vir(min(kontrol), 2)}–{vir(max(kontrol), 2)}",
        f"kurulmadı: {' ve '.join(kurulmayan)} ({'; '.join(sebep)})",
    ]
    # ev stilinin alt boşluğu (110 px) altı satır alır: paneller kâğıdın üstüne doğru sıkıştırılır,
    # açılan şeride not girer (eksen alanları, panel başlıkları birlikte kayar)
    pay = 0.085
    for k in list(fig.layout):
        if k.startswith("yaxis") and fig.layout[k].domain:
            d0, d1 = fig.layout[k].domain
            fig.layout[k].domain = [pay + d0 * (1 - pay), pay + d1 * (1 - pay)]
    for a in fig.layout.annotations:
        if a.yref == "paper" and a.yanchor == "bottom":
            a.y = pay + a.y * (1 - pay)
    # not, alt grafiğin sol kenarından değil şeklin sol kenarından başlar (satır adlarının genişliği kadar sola)
    fig.add_annotation(x=0, y=pay - 0.045, xref="paper", yref="paper", xanchor="left", yanchor="top", align="left",
                       xshift=-88, showarrow=False, text="<br>".join(notlar), font=dict(size=10, color="#4a4a4a"))
    # Tarih aralıkları ÖRNEKLEMİN penceresidir (ilk olaydan 10 takvim günü önce → son olaydan 10 gün sonra,
    # serinin ucuyla kırpılmış; ortak_olc.olay_kapisi), olay günleri değil: adı üç aralığın önüne BİR kez
    # yazılır. Olay adı ile sayısı bölünmez boşlukla bağlı ("FOMC 152" satır sonunda ayrılmasın).
    # Başlık bloğu üstten çapalı ve yüksekliği satır sayısından (sekil_ortak.baslik_koy · yukseklik):
    # eski 7 satır sınırı çapasız başlığın sınırıydı (ilk satırın tabanı üst boşluğun ortasında, kalan
    # satırlar aşağı akıyordu); çapalı blok satır başına 19,7 px tutar, üst boşluk 26 px büyür.
    pk, tf, fo = kapi[("n2y", "ppk")], kapi[("n2y", "tufe")], kapi[("us2", "fomc")]
    pk_kur = kapi[("usdtry", "ppk")]
    nb = "\u00a0"
    baslik = baslik_koy(
        fig, "Şekil 02 — PPK'da kur ve hizalanmış 2 yıllık olay gününde tepe yapar; TÜFE gününde hiçbir "
        "Türkiye serisi olay çalışmasına izin vermez",
        [f"Günlük · örneklem pencereleri (olay ±10 gün): PPK{nb}{pk['n_olay']} karar, "
         f"{tarih(pk['ilk'])}–{tarih(pk['son'])} · TÜFE{nb}{tf['n_olay']} yayım, {tarih(tf['ilk'])}–"
         f"{tarih(tf['son'])} · FOMC{nb}{fo['n_olay']} planlı karar, {tarih(fo['ilk'])}–{tarih(fo['son'])}",
         f"kur satırlarında yönetilen kur dönemi ({ay(yk['ilk'])}–{ay(yk['son'])}) hariç (PPK'da "
         f"{pk_kur['n_olay']})",
         "DİBS ve gösterge kuru TCMB, USD/TRY Yahoo Finance, ABD Hazinesi, CNBC"])
    _yaz(fig, "02_plasebo.html", yukseklik(baslik, 626))   # 626: çizim ve alt pay (eski 900 − 7 satırın 274'ü)
