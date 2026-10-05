#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EYLÜL 2026 TÜFE YAZISI (05.10.2026) — analiz figürleri.

Bu bir HAT DEĞİL, tek bir analizin çizim katmanı. Analiz yayımlandığı günün
metnidir (karar 08.09.2026); figürler de o günün ölçümünü dondurur ve
`site/public/analiz/<slug>/` altına yazılır, her koşuda tazelenmez. Her figür
kendi tarih aralığını kendi alt başlığında taşır.

GİRDİ TEK YERDEN: `veri/<çıpa>/olcum.json` (`olcum.py` üretir). Figür ile metin
iki ayrı hesaptan beslenseydi bir gün sessizce ayrışırdı. Her HTML, çizildiği
ölçüm dosyasının sha256 özünü bir meta etiketinde taşır (`tto-olcum-ozu`);
ölçüm değişip figür yeniden çizilmezse `dogrula.py` düşer.

Başlık bloğu Makro dersinin ortak kuralıyla sarılır (`MakroKurFaiz/sekil_ortak`:
yazı genişliği em ile ölçülür, sınır 390 piksellik telefonun 353 piksellik gömme
çerçevesidir); kural iki yerde yazılmasın diye kopyalanmaz, içe aktarılır. Ev
stili (`site/tools/plotly_stil.py`) başlıklı figürde üst boşluğu 92 pikselde
sabitler; çok satırlı başlık ancak çizim alanının üstünde bir etiket varsa
satır sayısına göre büyür — her figürün birim etiketi bu yüzden çizim alanının
sol üstündedir (birim okura zaten verilmeli; kural onu bahane etmiyor).

Sayı biçimi sitenin sözleşmesidir: ondalık virgül, binlik nokta, eksi U+2212,
yüzde önde. Eksenler Türkçe ay kısaltmalı kategori ekseni: plotly'nin tarih
ekseni ay adlarını İngilizce basar.

Fonksiyon adı = yazıdaki şekil numarası = dosya adının öneki = figürün içindeki
"Şekil NN" başlığı (dogrula.py son üçünü sorar).

  python3 sekil.py            # çizer ve ev stilini uygular
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
OLCUM = BURASI / "veri" / "2026-10-05" / "olcum.json"
try:                                   # çizim kütüphanesi çizim yolunun bağımlılığıdır;
    import plotly.graph_objects as go  # kapı yolu (dogrula.py) onu istemez
except ImportError:                    # pragma: no cover
    go = None

_spec = importlib.util.spec_from_file_location(
    "tufe_sekil_ortak", KOK / "Aktarılacak Projeler/MakroKurFaiz/sekil_ortak.py")
ortak = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ortak)        # yalnız saf fonksiyonlar kullanılır (sar, başlık yeri, taşma)

SLUG = "tufe-eylul-ppk-2026-10-05"
CIKTI = KOK / "site" / "public" / "analiz" / SLUG
PLOTLY_JS = "/js/plotly-4.0.0.min.js"
MUREKKEP, CLARET, MAVI, GRI, ALTIN, YESIL, ACIK = (
    "#1a1a1a", "#8c2f39", "#2f5d8c", "#8a8a8a", "#b8860b", "#3a7d44", "#d8d4cc")
AY_KISA = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
SEKILLER = ["01_aylik", "02_katki", "03_yillik_yol", "04_hizmet_mal"]
CIZIM = 380                            # çizim alanı + alt pay (lejant), piksel


def vir(x: float, b: int = 2, arti: bool = False) -> str:
    s = f"{abs(x):,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not sifir) else s


def yz(x: float, b: int = 2) -> str:
    return ("−%" + vir(abs(x), b)) if x < 0 and vir(abs(x), b).strip("0,") else "%" + vir(abs(x), b)


def ay_et(a: str) -> str:
    return f"{AY_KISA[int(a[5:7])]} {a[2:4]}"


def ozu() -> str:
    return hashlib.sha256(OLCUM.read_bytes()).hexdigest()


def _yaz(fig, ad: str, bas: str, alt: list[str], birim: str, cizim: int = CIZIM) -> None:
    baslik = ortak.baslik_metni(bas, alt)
    ust = ortak.ust_pay(baslik)
    fig.update_layout(title=ortak.baslik_yeri(baslik))
    # birim etiketi çizim alanının sol üstünde (ev stilinin üst boşluk kuralının dayandığı etiket)
    fig.add_annotation(text=birim, x=0, xref="paper", y=1.0, yref="paper", xanchor="left", yanchor="bottom",
                       showarrow=False, font=dict(size=11, color=GRI))
    fig.update_layout(
        # üst boşluk ev stilinin kuralına bırakılır: stil, başlıklı figürde 92 piksel yazar ve yalnız
        # mevcut değer gerekenin ALTINDAYSA satır sayısına göre büyütür (eşitse 92'de bırakır) — bu yüzden
        # gerekenin bir piksel altı verilir; stilsiz açılan dosyada fark bir pikseldir.
        height=ust + cizim, margin=dict(l=56, r=24, t=ust - 1, b=96), separators=",.",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        legend=dict(orientation="h", yanchor="top", y=-0.12, x=0),
        hoverlabel=dict(bgcolor="white", font=dict(color=MUREKKEP)),
    )
    fig.update_xaxes(showgrid=False, linecolor=ACIK, ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    html = fig.to_html(include_plotlyjs=PLOTLY_JS, full_html=True,
                       config={"displayModeBar": False, "responsive": True})
    html = html.replace("<head>", f'<head><meta name="tto-olcum-ozu" content="{ozu()}">', 1)
    (CIKTI / f"{ad}.html").write_text(html, encoding="utf-8")
    print(f"  ✓ {(CIKTI / (ad + '.html')).relative_to(KOK)}")
    for s in ortak.tasan_satirlar(baslik):
        print(f"  ! {ad}: başlık satırı telefonun gömme çerçevesinde taşar — {s}")


def _eksen(fig, etiketler: list[str], adim: int) -> None:
    """Ay ekseni SAYISAL konumla kurulur, etiket Türkçe kısaltmadır; her `adim` ayda bir etiket, son ay
    her zaman görünür. Kategori ekseni kullanılmaz: ev stili 24'ten fazla kategoride etiketleri kendi
    seyreltir ve eğer, eğik etiketler dar ekranda lejantın üstüne biniyordu."""
    n = len(etiketler)
    sec = [i for i in range(n) if (n - 1 - i) % adim == 0]
    fig.update_xaxes(tickmode="array", tickvals=sec, ticktext=[etiketler[i] for i in sec],
                     range=[-0.6, n - 0.4], tickangle=0)


# ─────────────────────────────────────────────────────────────── 01
def sekil01(o: dict) -> None:
    s, d = o["seriler"]["01"], o["degerler"]
    x = [ay_et(a) for a in s["ay"]]
    fig = go.Figure()
    for k, ad, renk, kal in (("tufe", "TÜFE", CLARET, 3), ("b", "B", MAVI, 1.6), ("c", "C", ALTIN, 1.6)):
        fig.add_trace(go.Scatter(x=list(range(len(x))), y=s[k], name=ad, mode="lines+markers" if k == "tufe" else "lines",
                                 line=dict(color=renk, width=kal), marker=dict(size=5),
                                 customdata=[f"{e} · {ad}: {yz(v)}" for e, v in zip(x, s[k])],
                                 hovertemplate="%{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(x=list(range(len(x))), y=s["pka"], name="TCMB anketi", mode="markers",
                             marker=dict(size=8, symbol="circle-open", color=MUREKKEP, line=dict(width=1.4)),
                             customdata=[f"{e} · anket: {yz(v)}" if v is not None else "" for e, v in
                                         zip(x, s["pka"])],
                             hovertemplate="%{customdata}<extra></extra>"))
    aa, alt_, ust_ = d["aa_beklenti"]["deger"], d["aa_alt"]["deger"], d["aa_ust"]["deger"]
    fig.add_trace(go.Scatter(x=[len(x) - 1], y=[aa], name="AA Finans (dış kaynak)", mode="markers",
                             marker=dict(size=10, symbol="diamond-open", color=GRI, line=dict(width=1.6)),
                             error_y=dict(type="data", symmetric=False, array=[ust_ - aa], arrayminus=[aa - alt_],
                                          color=GRI, thickness=1.2, width=6),
                             customdata=[f"Eyl 26 · AA Finans ortalaması {yz(aa)}, aralık {yz(alt_)}–{vir(ust_)}"],
                             hovertemplate="%{customdata}<extra></extra>"))
    _eksen(fig, x, 6)
    fig.update_yaxes(ticksuffix="", tickformat=",.1f")
    _yaz(fig, "01_aylik", "Şekil 01 — Eylül'de manşet anketin altında, C çekirdeği manşetin üstünde",
         ["Aylık değişim. Ekim 2024–Eylül 2026. TÜFE, B ve C: TÜİK, TCMB EVDS.",
          "Halkalar: TCMB Piyasa Katılımcıları Anketi'nin o ay için beklentisi. Eylül'deki baklava: AA Finans "
          "anketinin ortalaması (20 ekonomist), dikey çizgi en düşük ve en yüksek tahmin."],
         "aylık değişim, %")


# ─────────────────────────────────────────────────────────────── 02
def sekil02(o: dict) -> None:
    s, d = o["seriler"]["02"], o["degerler"]
    sira = list(reversed(s["sira"]))                # yatay çubukta en büyük en üstte
    ad = [s["ad"][k] for k in sira]
    agu = [s["ana"][k]["2026-08"]["katki"] for k in sira]
    eyl = [s["ana"][k]["2026-09"]["katki"] for k in sira]
    r_agu = [s["ana"][k]["2026-08"]["aylik"] for k in sira]
    r_eyl = [s["ana"][k]["2026-09"]["aylik"] for k in sira]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=ad, x=agu, orientation="h", name=f"Ağustos (manşet {d['tufe_aylik_agu']['metin']})",
                         marker_color=ACIK, marker_line=dict(color=GRI, width=0.8),
                         customdata=[f"{a} · Ağustos: {vir(c)} puan (grup aylık {yz(r)})" for a, c, r in
                                     zip(ad, agu, r_agu)],
                         hovertemplate="%{customdata}<extra></extra>"))
    fig.add_trace(go.Bar(y=ad, x=eyl, orientation="h", name=f"Eylül (manşet {d['tufe_aylik']['metin']})",
                         marker_color=CLARET,
                         customdata=[f"{a} · Eylül: {vir(c)} puan (grup aylık {yz(r)})" for a, c, r in
                                     zip(ad, eyl, r_eyl)],
                         hovertemplate="%{customdata}<extra></extra>"))
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_xaxes(zeroline=True, zerolinecolor=GRI, tickformat=",.1f", showgrid=True, gridcolor="#ececec")
    fig.update_yaxes(automargin=True, tickfont=dict(size=11), showgrid=False)
    # başlıktaki sayılar ölçüm dosyasının metin alanlarından; ek sayıya değil "puan" sözcüğüne bağlanır
    _yaz(fig, "02_katki",
         f"Şekil 02 — Aynı aylık oran, farklı bileşim: ulaştırmanın katkısı {d['ana07_katki_agu']['metin']}dan "
         f"{d['ana07_katki']['metin']}a indi, giyiminki {d['ana03_katki_agu']['metin']}dan "
         f"{d['ana03_katki']['metin']}a döndü",
         ["13 ana harcama grubunun aylık TÜFE'ye katkısı: grubun bir önceki aydaki etkin ağırlığı çarpı aylık "
          "değişimi. Ağustos ve Eylül 2026.",
          f"Ağırlıklar yayımlanmadığı için zincir Laspeyres kimliğinden tahmin edildi; 2025 ağırlığıyla tek bir "
          f"grubun Eylül katkısı en çok {d['katki13_w_fark_maks']['metin']} değişiyor."],
         "katkı, puan", cizim=560)


# ─────────────────────────────────────────────────────────────── 03
def sekil03(o: dict) -> None:
    s, d = o["seriler"]["03"], o["degerler"]
    xg = [ay_et(a) for a in s["gercek_ay"]]
    xs = [ay_et(a) for a in s["ufuk"]]
    tum = xg + xs
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(len(xg))), y=s["gercek"], name="gerçekleşen", line=dict(color=CLARET, width=3),
                             customdata=[f"{e} · yıllık TÜFE {yz(v)}" for e, v in zip(xg, s["gercek"])],
                             hovertemplate="%{customdata}<extra></extra>"))
    for k, ad, renk, kesik in (
            ("anket", "anket", ALTIN, "dash"), ("momentum_mev25", "momentum, 2025 mevsimselliği", MAVI, "dash"),
            ("momentum_mev22", "momentum, 2022 mevsimselliği", MAVI, "dot"),
            ("son12_mev25", "son 12 ay, 2025 mevsimselliği", GRI, "dot")):
        y = [s["gercek"][-1]] + s["yol"][k]
        fig.add_trace(go.Scatter(x=list(range(len(xg) - 1, len(tum))), y=y, name=ad, line=dict(color=renk, width=2, dash=kesik),
                                 customdata=[f"{e} · {ad.split(':')[0]}: {yz(v)}" for e, v in zip([xg[-1]] + xs, y)],
                                 hovertemplate="%{customdata}<extra></extra>"))
    fig.add_hline(y=d["esik_30"]["deger"], line=dict(color=MUREKKEP, width=1, dash="dot"))
    fig.add_annotation(x=2, y=d["esik_30"]["deger"], text="%30", showarrow=False, yanchor="bottom",
                       font=dict(size=11, color=MUREKKEP))
    _eksen(fig, tum, 6)
    fig.update_yaxes(tickformat=",.0f")
    _yaz(fig, "03_yillik_yol",
         "Şekil 03 — Bugünkü hız, son yılın mevsimselliğiyle, yıllık oranı yıl sonunda %30'un altında "
         "tutuyor; marjı mevsim kalıbı belirliyor",
         ["Yıllık TÜFE. Gerçekleşen Ekim 2024–Eylül 2026; Ekim 2026–Eylül 2027 baz aritmetiği: düşen ayın "
          "oranı bilinir, senaryo yalnız gelen ayın varsayımıdır.",
          f"Momentum: arındırılmış son üç ayın ortalaması (aylık {d['mom_aylik']['metin']}), o takvim ayının "
          f"mevsim çarpanıyla ham aya çevrilir: Ekim–Aralık için 2025'in ya da 2022'nin çarpanı. Son 12 ay: aylık "
          f"{d['son12_aylik']['metin']}, 2025 çarpanlarıyla. Anket: TCMB Piyasa Katılımcıları Anketi, "
          f"Eylül 2026 — Ekim {d['pka_ekim']['metin']}, Kasım {d['pka_kasim']['metin']}, yıl sonu "
          f"{d['pka_yilsonu']['metin']}, 12 ay sonra {d['pka_12a']['metin']} (Aralık ve 2027 aylıkları bu "
          "çıpalardan çıkarıldı)."],
         "yıllık değişim, %", cizim=420)


# ─────────────────────────────────────────────────────────────── 04
def sekil04(o: dict) -> None:
    s, d = o["seriler"]["04"], o["degerler"]
    x = [ay_et(a) for a in s["ay"]]
    fig = go.Figure()
    for k, ad, renk, kal, kesik in (("hizmet", "hizmet", CLARET, 2.6, "solid"), ("kira", "kira", ALTIN, 1.6, "dot"),
                                    ("tufe", "TÜFE", GRI, 1.6, "solid"), ("mal", "temel mallar", MAVI, 2.6, "solid")):
        fig.add_trace(go.Scatter(x=list(range(len(x))), y=s[k], name=ad, line=dict(color=renk, width=kal, dash=kesik),
                                 customdata=[f"{e} · {ad}: {yz(v)}" for e, v in zip(x, s[k])],
                                 hovertemplate="%{customdata}<extra></extra>"))
    _eksen(fig, x, 6)
    fig.update_yaxes(tickformat=",.0f")
    _yaz(fig, "04_hizmet_mal",
         f"Şekil 04 — Hizmet ile mal arasındaki makas {d['hizmet_mal_makas']['metin']}; hizmet yıllığı "
         f"{d['hizmet_yillik_dusuk_beri']['metin']}'den bu yana en düşük",
         ["Yıllık değişim. Ekim 2023–Eylül 2026. Hizmet, temel mallar, kira: TCMB EVDS özel kapsamlı "
          "göstergeleri; TÜFE: TÜİK."],
         "yıllık değişim, %")


def main() -> int:
    if go is None:
        print("plotly kurulu değil — çizim yolu koşamaz")
        return 2
    o = json.loads(OLCUM.read_text(encoding="utf-8"))
    for ad in SEKILLER:
        globals()[f"sekil{ad[:2]}"](o)
    dosyalar = [str(CIKTI / f"{ad}.html") for ad in SEKILLER]
    s = subprocess.run([sys.executable, str(KOK / "site/tools/plotly_stil.py"), *dosyalar],
                       capture_output=True, text=True)
    if s.returncode != 0:
        print(s.stdout, s.stderr)
        return 1
    print("  ✓ ev stili uygulandı")
    return 0


if __name__ == "__main__":
    sys.exit(main())
