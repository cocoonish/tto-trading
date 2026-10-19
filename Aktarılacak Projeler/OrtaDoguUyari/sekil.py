#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABD'NİN ORTA DOĞU UYARISI (19.10.2026) — analiz figürleri.

Tek bir analizin çizim katmanı; figürler yayım gününün ölçümünü dondurur ve
`site/public/analiz/<slug>/` altına yazılır. GİRDİ TEK YERDEN: `veri/olcum.json`.

Fonksiyon adı = yazıdaki şekil numarası = dosya adının öneki = figürün içindeki
"Şekil NN" başlığı (dogrula.py bunları sorar). Çift y eksenli grafik yok.

  python3 sekil.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
sys.dont_write_bytecode = True

import sekil_ortak as so  # noqa: E402
from sekil_ortak import go, make_subplots, vir, yuzde, tarih  # noqa: E402

O = json.loads(so.OLCUM.read_text(encoding="utf-8"))
SEKILLER = ["01_takvim", "02_dalgalar", "03_tepki", "04_piyasa", "05_gecmis"]
CLARET, MAVI, KEHRIBAR, YESIL, GRI, MUREKKEP = so.CLARET, so.MAVI, so.TURUNCU, so.YESIL, so.GRI, so.MUREKKEP
AY = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
#: Dilin dört kademesi, en serti önce (olcum.KADEME ile aynı sıra ve ad).
KADEME_AD = {4: "sığın ya da derhal ayrıl", 3: "ayrılmayı düşün", 2: "seyahati yeniden düşün", 1: "tetikte ol"}
KADEME_RENK = {4: CLARET, 3: KEHRIBAR, 2: MAVI, 1: "#9fb6cc"}


SIRA = {7: "yedinci", 8: "sekizinci", 9: "dokuzuncu", 10: "onuncu", 11: "on birinci"}


def _bitir(fig, ad: str, bas: str, alt: list[str], cizim: int) -> None:
    baslik = so.baslik_koy(fig, bas, alt)
    so._yaz(fig, ad, so.yukseklik(baslik, cizim), ust=so.ust_pay(baslik))


def gun_ay(iso: str) -> str:
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]}"


def dalga_ad(d: dict) -> str:
    """Dalganın okur adı: tek günse gün, çok günse aralık ("5–20 Mar")."""
    if d["bas"] == d["bit"]:
        return gun_ay(d["bas"])
    return f"{int(d['bas'][8:10])}–{gun_ay(d['bit'])}"


def yz(z: float, b: int = 1) -> str:
    """İşaretli yüzde; sıfıra yuvarlanan değer işaretsiz (−%0,0 basılmaz)."""
    return yuzde(0.0 if round(z, b) == 0 else z, b, arti=True)


def pct(x: float, b: int = 1) -> str:
    return yuzde(x * 100, b)


# ─────────────────────────────────────────────────────────────────────── 01
def sekil_01():
    u = O["uyari"]
    g = u["gunluk"]
    x, y = [t for t, _ in g], [n for _, n in g]
    renk = [CLARET if n >= u["esik"] else "#b9b4aa" for n in y]
    fig = go.Figure()
    fig.add_vrect(x0="2026-02-28", x1="2026-04-08", fillcolor="rgba(140,47,57,0.08)", line_width=0)
    fig.add_annotation(x="2026-03-18", y=13.4, text="savaş: 28 Şub – 7 Nis", showarrow=False,
                       font=dict(size=11, color=CLARET))
    fig.add_trace(go.Bar(x=x, y=y, marker_color=renk, name="uyarı yayımlayan temsilcilik",
                         customdata=[f"{tarih(t)} · {n} temsilcilik" for t, n in g],
                         hovertemplate="%{customdata}<extra></extra>"))
    sal = [t for t in O["saldiri_gunleri"] if t >= u["ortak_kapsam"] and not ("2026-02-28" <= t <= "2026-04-07")]
    fig.add_trace(go.Scatter(x=sal, y=[12.6] * len(sal), mode="markers", name="ABD'nin İran toprağına saldırısı (ateşkes sonrası)",
                             marker=dict(symbol="triangle-down", size=8, color=MUREKKEP),
                             customdata=[f"{tarih(t)} · ABD saldırısı" for t in sal],
                             hovertemplate="%{customdata}<extra></extra>"))
    fig.add_hline(y=u["esik"] - 0.5, line=dict(color=GRI, width=1, dash="dot"))
    fig.add_annotation(x="2026-04-12", y=u["esik"] - 0.5, text=f"dalga eşiği: en az {u['esik']} temsilcilik", showarrow=False,
                       xanchor="left", yanchor="bottom", font=dict(size=11, color=GRI))
    fig.update_yaxes(title="temsilcilik sayısı", range=[0, 14], dtick=2)
    fig.update_xaxes(tickformat="%d.%m", dtick="M1")
    son = u["donemler"][-1]
    sira = SIRA[len(u["donemler"])]
    _bitir(fig, "01_takvim.html",
           f"Şekil 01 — {tarih(son['bas'])} bu yılın {sira} uyarı dalgası; on ikinin on ikisi aynı gün",
           [f"Her gün güvenlik uyarısı yayımlayan ABD temsilciliği sayısı, on iki temsilcilik (Suudi Arabistan, BAE, Kuveyt, "
            f"Ürdün, Bahreyn, Umman, İran, Katar, Irak, Lübnan, Yemen, İsrail) · {tarih(u['ortak_kapsam'])}–{tarih(x[-1])}",
            "Bordo çubuk: dalga (aynı gün en az on temsilcilik) · üçgen: ABD'nin İran kara toprağını vurduğu gün · "
            "kaynak: temsilciliklerin kendi uyarı listeleri"], 380)


# ─────────────────────────────────────────────────────────────────────── 02
def sekil_02():
    D = O["uyari"]["donemler"]

    def sonraki(d: dict) -> str:
        if d["sonraki_saldiriya_gun"] is not None:
            return f"{d['sonraki_saldiriya_gun']} gün"
        return "açık" if d["acik_gun"] <= 1 else "yok"

    ad = [f"{dalga_ad(d)} · {sonraki(d)}" for d in D]
    fig = go.Figure()
    for k in (4, 3, 2, 1):
        fig.add_trace(go.Bar(y=ad, x=[d["kademe_dagilim"][str(k)] for d in D], name=KADEME_AD[k], orientation="h",
                             marker_color=KADEME_RENK[k],
                             customdata=[f"{dalga_ad(d)} · {d['kademe_dagilim'][str(k)]} temsilcilik: {KADEME_AD[k]} · "
                                         f"ayrılış statüsü anan {len(d['ayrilis_post'])}" for d in D],
                             hovertemplate="%{customdata}<extra></extra>"))
    fig.update_layout(barmode="stack", bargap=0.3, legend=dict(traceorder="normal"))
    fig.update_xaxes(title="temsilcilik (İran ve Yemen hariç)", range=[0, 10], dtick=2)
    fig.update_yaxes(type="category", autorange="reversed")
    son4 = D[-4:]
    yum = sum(d["kademe_dagilim"]["1"] for d in son4)
    top = sum(sum(d["kademe_dagilim"].values()) for d in son4)
    _bitir(fig, "02_dalgalar.html",
           f"Şekil 02 — Son dört dalga en yumuşak kademede ({top} metinden {yum}); bu dil 1 Eylül'de saldırının günü de geldi",
           ["Her dalganın ilk günü, her temsilciliğin metnindeki en sert talimat (dört kademe) · İran ve Yemen kalıcı "
            "\"seyahat etmeyin\" altında olduğu için sayılmaz",
            "Satır adındaki gün: dalganın ertesi gününden sonraki ilk ABD saldırısına kadar geçen süre · "
            "kaynak: temsilciliklerin uyarı metinleri"], 470)


# ─────────────────────────────────────────────────────────────────────── 03
def sekil_04():
    t = O["tahmin"]["abd_31ekim"]
    gun = {}
    for d, p in t["gunluk"]:            # aynı güne iki nokta düşerse sonuncusu (günün kapanışa en yakın noktası)
        gun[d] = p
    x, y = list(gun), [gun[d] * 100 for d in gun]
    sa = t["saatlik_19ekim"]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.16, row_heights=[0.58, 0.42],
                        subplot_titles=("günlük, %", "saatlik, 18–19 Ekim (UTC), %"))
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", line=dict(color=CLARET, width=2), marker=dict(size=4),
                             name="31 Ekim'e kadar ABD saldırısı",
                             customdata=[f"{tarih(d)} · {pct(gun[d])}" for d in gun],
                             hovertemplate="%{customdata}<extra></extra>"), row=1, col=1)
    for d in ("2026-09-19", "2026-10-08", "2026-10-18"):
        fig.add_vline(x=d, line=dict(color=GRI, width=1, dash="dot"), row=1, col=1)
        fig.add_annotation(x=d, y=66, text=f"dalga {gun_ay(d)}", showarrow=False, xanchor="left",
                           font=dict(size=10.5, color=GRI), row=1, col=1)
    fig.update_yaxes(range=[0, 70], dtick=10, row=1, col=1)
    fig.update_xaxes(tickformat="%d.%m", row=1, col=1)
    fig.add_trace(go.Scatter(x=[a for a, _ in sa], y=[p * 100 for _, p in sa], mode="lines+markers",
                             line=dict(color=MAVI, width=1.6, shape="hv"), marker=dict(size=4), showlegend=False,
                             customdata=[f"{a[8:10]}.{a[5:7]} {a[11:16]} UTC · {pct(p)}" for a, p in sa],
                             hovertemplate="%{customdata}<extra></extra>"), row=2, col=1)
    fig.update_yaxes(range=[0, 70], dtick=20, row=2, col=1)
    fig.update_xaxes(tickformat="%d.%m %H:%M", row=2, col=1)
    fig.update_layout(showlegend=False)
    _bitir(fig, "04_piyasa.html",
           f"Şekil 04 — Piyasa 31 Ekim'e kadar ABD saldırısına {pct(t['saldiri_son'])} veriyor; 18 Ekim uyarısı fiyatı yükseltmedi",
           [f"Polymarket \"US x Iran ceasefire continues through October 31?\" piyasasında HAYIR'ın fiyatı (1 − EVET) · "
            f"{tarih(x[0])}–{tarih(t['son_an'][:10])}, son nokta {t['son_an'][11:16]} UTC",
            "Çözüm kuralı: ABD'nin İran kara toprağına (iç suları dahil) saldırısı; denizdeki saldırı sayılmaz · "
            "kesikli çizgi: uyarı dalgası"], 560)


# ─────────────────────────────────────────────────────────────────────── 04
def sekil_05():
    G = O["tahmin"]["gecmis"]
    tanim = [
        ("haziran2025", "Haziran 2025 · EVET çözüldü<br>\"Temmuz'dan önce ABD askerî eylemi\"", "2025-05-20", "2025-06-22",
         [("2025-06-11", "11 Haz: Bağdat'tan zorunlu ayrılış"), ("2025-06-22", "22 Haz: ABD saldırısı", 80)]),
        ("subat2026", "Şubat 2026 · EVET çözüldü<br>\"28 Şubat'a kadar ABD ya da İsrail saldırısı\"", "2026-01-28", "2026-02-28",
         [("2026-02-23", "23 Şub: Beyrut'tan zorunlu ayrılış"), ("2026-02-27", "27 Şub: İsrail'den izinli ayrılış", 70),
          ("2026-02-28", "28 Şub: savaş", 48)]),
        ("ocak2026", "Ocak 2026 · HAYIR çözüldü<br>\"31 Ocak'a kadar ABD ya da İsrail saldırısı\"", "2026-01-09", "2026-02-01",
         [("2026-01-14", "14 Oca: tepe")]),
    ]
    fig = make_subplots(rows=3, cols=1, vertical_spacing=0.13, subplot_titles=[t[1] for t in tanim])
    fig.update_annotations(font_size=12.5)      # alt başlıklar telefon çerçevesine (353 piksel) sığsın
    for i, (k, _, a, b, isaret) in enumerate(tanim, start=1):
        s = [(d, p) for d, p in G[k]["seri"] if a <= d <= b]
        fig.add_trace(go.Scatter(x=[d for d, _ in s], y=[p * 100 for _, p in s], mode="lines+markers",
                                 line=dict(color=[MAVI, CLARET, GRI][i - 1], width=2), marker=dict(size=3.5),
                                 showlegend=False,
                                 customdata=[f"{tarih(d)} · {pct(p)}" for d, p in s],
                                 hovertemplate="%{customdata}<extra></extra>"), row=i, col=1)
        for d, ad, *yy in isaret:
            fig.add_vline(x=d, line=dict(color=MUREKKEP, width=1, dash="dot"), row=i, col=1)
            fig.add_annotation(x=d, y=yy[0] if yy else 92, text=ad, showarrow=False, xanchor="right", font=dict(size=10.5, color=MUREKKEP),
                               row=i, col=1)
        fig.update_yaxes(range=[0, 100], dtick=25, row=i, col=1)
        fig.update_xaxes(tickformat="%d.%m", row=i, col=1)
    f = {k: G[k]["fiyat"] for k in G}
    _bitir(fig, "05_gecmis.html",
           f"Şekil 05 — Saldırıdan bir gün önce piyasa {pct(f['subat2026']['2026-02-27'])} ve "
           f"{pct(f['haziran2025']['2025-06-21'])} diyordu; olmayan saldırıya {pct(G['ocak2026']['en_yuksek'][0])}",
           ["Polymarket'in kapanmış üç piyasasında EVET'in günlük fiyatı, %",
            f"Kesikli çizgi: temsilciliğin personel ayrılışı ve olayın günü · Haziran 2025 piyasası "
            f"{gun_ay(G['haziran2025']['en_yuksek'][1])}'da {pct(G['haziran2025']['en_yuksek'][0])} gördü"],
           760)


# ─────────────────────────────────────────────────────────────────────── 05
def sekil_03():
    D = [d for d in O["uyari"]["donemler"] if d["bas"] in O["tepki"]]
    T, H = O["tepki"], O["son_hafta"]
    ad = [dalga_ad(d) for d in D] + ["9–16 Eki"]
    renk = [CLARET if d["atesli"] else MAVI for d in D] + [GRI]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12,
                        subplot_titles=("Brent, %", "BIST 100, %"))
    for j, (a, ar) in enumerate((("brent", [-22, 40]), ("bist100", [-11, 7])), start=1):
        v = [T[d["bas"]][a]["d5"] * 100 for d in D] + [H[a]["degisim"] * 100]
        fig.add_trace(go.Bar(y=ad, x=v, orientation="h", marker_color=renk, showlegend=False,
                             text=[yz(z) for z in v], textposition="outside", cliponaxis=False,
                             customdata=[f"{n} · {yz(z)}" for n, z in zip(ad, v)],
                             hovertemplate="%{customdata}<extra></extra>"), row=j, col=1)
        fig.add_vline(x=0, line=dict(color=MUREKKEP, width=1), row=j, col=1)
        fig.update_xaxes(range=ar, row=j, col=1)
        fig.update_yaxes(autorange="reversed", type="category", row=j, col=1)
    _bitir(fig, "03_tepki.html",
           "Şekil 03 — Büyük hareket uyarıyla değil saldırıyla geldi; sakin iki dalgada Brent "
           + " ve ".join(yz(T[d["bas"]]["brent"]["d5"] * 100) for d in D if not d["atesli"]),
           ["Dalgadan önceki son kapanıştan beş işlem günü sonrasına değişim · bordo: saldırıya yakın dalga (dalga günü ya "
            "da önceki yedi günde ABD saldırısı), mavi: sakin, gri: 18 Ekim dalgasından önceki hafta (9–16 Ekim)",
            "Kaynak: vadeli Brent ön vade ve BIST 100 kapanışları (CNBC)"], 720)


def main() -> int:
    if go is None:
        print("plotly kurulu değil — figürler çizilemez", file=sys.stderr)
        return 1
    for ad in SEKILLER:
        globals()[f"sekil_{ad[:2]}"]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
