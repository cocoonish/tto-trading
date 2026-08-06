# -*- coding: utf-8 -*-
"""
TCMB EN 24/17 replikasyonu — Grafik 1-14 (orijinal format, Temmuz 2026'ya uzatılmış).

Bazlar grafik başlıklarında açık: 2013 Ocak=100 / 2013 Ocak=1 / 2019 Aralık=100.
Nisan 2022 sonrası madde düzeyi verinin proxy (5'li grup uzatması) olduğu dönem,
maliyet/oran grafiklerinde dikey kesikli çizgiyle işaretlenir.
"""
import pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import veri, endeks

ROOT = pathlib.Path(__file__).resolve().parent.parent
GRAF = ROOT / "output" / "grafikler"
GRAF.mkdir(parents=True, exist_ok=True)

# dataviz doğrulanmış kategorik palet (4 konsept, sabit sıra)
RENK = {"kirmizi_et": "#eb6834", "tavuk": "#eda100", "ev_yemekleri": "#2a78d6", "fast_food": "#1baf7a"}
GRI = "#52514e"; ACIK_GRI = "#d9d8d4"
SPLICE = pd.Timestamp("2022-04-01")

plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.edgecolor": ACIK_GRI, "axes.grid": True, "grid.color": ACIK_GRI,
    "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 9.5, "axes.titlesize": 10.5, "axes.titleweight": "bold",
    "text.color": "#0b0b0b", "axes.labelcolor": "#0b0b0b",
    "xtick.color": GRI, "ytick.color": GRI, "font.family": "DejaVu Sans",
})

def _kaydet(fig, ad, kaynak, not_=None):
    alt = f"Kaynak: {kaynak}"
    if not_:
        alt += f"\nNot: {not_}"
    fig.text(0.01, -0.045, alt, fontsize=7, color=GRI, va="top", wrap=True)
    fig.savefig(GRAF / ad, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  ✓ {ad}")

def _splice_cizgi(ax):
    ax.axvline(SPLICE, color=GRI, lw=0.8, ls=":", alpha=0.7)

def _yil_ekseni(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


# ------------------------------------------------------------------ Grafik 1: hizmet ciro
def hizmet_ciro_oku():
    """Hizmet ciro endeksi (2015=100) — bölüm bazında yıllık ortalama endeksler."""
    ham = pd.read_excel(ROOT / "data/raw/tuik_hizmet_ciro_2015.xls", sheet_name="T2", header=None)
    # bölüm başlıkları 4. satırda (index 4), blok başı kolonları
    basliklar = {}
    for j in range(ham.shape[1]):
        v = ham.iloc[4, j]
        if isinstance(v, str) and " - " in v.split("\n")[0]:
            basliklar[j] = v.split("\n")[0].strip()
    yillar = pd.to_numeric(ham.iloc[8:, 0], errors="coerce").ffill()
    aylar = pd.to_numeric(ham.iloc[8:, 1], errors="coerce")
    out = {}
    for j, ad in basliklar.items():
        vals = pd.to_numeric(ham.iloc[8:, j], errors="coerce")  # arındırılmamış endeks
        df = pd.DataFrame({"yil": yillar.values, "ay": aylar.values, "v": vals.values}).dropna()
        out[ad] = df.groupby("yil")["v"].mean()
    return pd.DataFrame(out)


def grafik_1():
    try:
        ciro = hizmet_ciro_oku()
    except Exception as e:
        print(f"  ✗ Grafik 1 atlandı: {e}")
        return
    yillik = ciro.pct_change() * 100
    etiketler = {
        "H - Ulaştırma ve depolama": "Ulaştırma ve\ndepolama",
        "I - Konaklama ve yiyecek hizmeti faaliyetleri": "Konaklama ve\nyiyecek hizm.",
        "J - Bilgi ve iletişim": "Bilgi ve\niletişim",
        "L - Gayrimenkul faaliyetleri": "Gayrimenkul",
        "M - Mesleki, bilimsel ve teknik faaliyetler": "Mesleki, bilimsel\nve teknik",
        "N - İdari ve destek hizmet faaliyetleri": "İdari ve destek\nhizmetleri",
    }
    mevcut = [k for k in etiketler if k in yillik.columns]
    if not mevcut:  # başlık eşleşmesi esnek olsun
        mevcut = [c for c in yillik.columns if c.split(" ")[0] in list("HIJLMN")][:6]
        etiketler = {c: c.split(" - ")[-1][:18] for c in mevcut}
    v2020 = yillik.loc[2020, mevcut]
    v2122 = yillik.loc[[2021, 2022], mevcut].mean()
    x = np.arange(len(mevcut)); w = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.bar(x - w/2, v2020.values, w, label="2020", color="#2a78d6")
    ax.bar(x + w/2, v2122.values, w, label="2021-2022 ort.", color="#eb6834")
    for i, (a, b) in enumerate(zip(v2020.values, v2122.values)):
        ax.text(i - w/2, a + (1.5 if a >= 0 else -3.5), f"{a:.0f}", ha="center", fontsize=8)
        ax.text(i + w/2, b + (1.5 if b >= 0 else -3.5), f"{b:.0f}", ha="center", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels([etiketler[c] for c in mevcut], fontsize=8)
    ax.axhline(0, color=GRI, lw=0.8)
    ax.set_title("Grafik 1: Hizmet Ciro Endeksleri (Yıllık % Değişim)")
    ax.legend(frameon=False)
    _kaydet(fig, "grafik_01_hizmet_ciro.png", "TÜİK, Ticaret ve Hizmet Ciro Endeksleri (2015=100).",
            "Cari fiyatlarla, arındırılmamış endekslerin yıllık ortalamalarından hesaplanmıştır.")


# ------------------------------------------------------------------ Grafik 2-4: TÜFE karşılaştırma
def _agirlik_paneli():
    """2025=100 ana grup ağırlıkları yıl paneli (2016+). Dönen: DataFrame[yıl x grup_kodu]."""
    ham = pd.read_excel(ROOT / "data/raw/tuik_2025_anagrup_agirliklar.xls", sheet_name=0, header=None)
    yil_satiri = 3
    yillar = [int(v) for v in ham.iloc[yil_satiri, 1:].dropna().astype(float)]
    gruplar = {4: "01", 15: "11"}  # satır tahmini yerine ada göre bul:
    isimler = ham.iloc[:, 0].astype(str)
    idx_gida = isimler[isimler.str.startswith("Gıda ve alkolsüz", na=False)].index
    idx_lok = isimler[isimler.str.contains("okanta", na=False)].index
    out = {}
    for ad, idx in [("gida", idx_gida), ("lokanta", idx_lok)]:
        if len(idx):
            vals = pd.to_numeric(ham.iloc[idx[0], 1:1+len(yillar)], errors="coerce")
            out[ad] = pd.Series(vals.values, index=yillar)
    return pd.DataFrame(out)


def gida_yemek_haric_tufe(evds):
    """Gıda (01) ve yemek hizmetleri (111) hariç TÜFE — yıllık ağırlıklarla zincirleme.
    Yemek hizmetleri ağırlığı: grup 11 ağırlığı x (111'in 11 içindeki payı, 2025 temel
    başlık dosyasından sabit oran ~= yemek/lokanta)."""
    agirlik = _agirlik_paneli()
    # 2025 temel başlık dosyasından 111/11 oranı
    tb = pd.read_excel(ROOT / "data/raw/tuik_2003_temel_baslik_agirliklar.xlsx", sheet_name=0, header=None)
    kodlar = tb.iloc[:, 0].astype(str).str.strip()
    p111 = pd.to_numeric(tb.loc[kodlar.str.startswith("111"), 3], errors="coerce").sum()
    p11 = pd.to_numeric(tb.loc[kodlar.isin(["11"]), 3], errors="coerce").sum()
    yemek_pay = p111 / p11 if p11 else 0.85
    tufe, gida, yemek = evds["tufe_genel"], evds["gida_alkolsuz"], evds["yemek_111"]
    idx = tufe.dropna().index
    exc = pd.Series(index=idx, dtype=float); exc.iloc[0] = 100.0
    for i in range(1, len(idx)):
        t = idx[i]; yil = t.year
        yılw = agirlik.reindex([yil]).ffill().iloc[0] if yil in agirlik.index else agirlik.iloc[-1 if yil > agirlik.index.max() else 0]
        wg = yılw["gida"] / 100
        wy = yılw["lokanta"] / 100 * yemek_pay
        mm = {s.name: s.loc[t] / s.loc[idx[i-1]] - 1 for s in (tufe, gida, yemek)}
        exc_mm = (mm[tufe.name] - wg * mm[gida.name] - wy * mm[yemek.name]) / (1 - wg - wy)
        exc.iloc[i] = exc.iloc[i-1] * (1 + exc_mm)
    exc.name = "gida_yemek_haric"
    return exc


def grafik_2_4():
    evds = veri.tum_evds()
    exc = gida_yemek_haric_tufe(evds)
    seriler = {
        "Gıda ve Yemek Hariç TÜFE": exc,
        "Gıda ve Alkolsüz İçecekler": evds["gida_alkolsuz"],
        "Yemek Hizmetleri": evds["yemek_111"],
    }
    renkler = ["#2a78d6", "#eb6834", "#1baf7a"]
    baz = pd.Timestamp("2019-12-01")
    # G2: endeks 2019 Aralık = 100
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for (ad, s), r in zip(seriler.items(), renkler):
        sb = (s / s.loc[baz] * 100).loc["2019-12-01":"2026-07-01"]
        ax.plot(sb.index, sb.values, color=r, lw=2, label=ad)
        ax.annotate(f"{sb.iloc[-1]:.0f}", (sb.index[-1], sb.iloc[-1]), xytext=(4, 0),
                    textcoords="offset points", color=r, fontsize=8, fontweight="bold")
    ax.set_title("Grafik 2: TÜFE Fiyat Endeksleri (2019 Aralık=100)")
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    _kaydet(fig, "grafik_02_tufe_endeks.png", "TÜİK, TCMB EVDS (TÜFE 2025=100 serisi); hesaplamalar.",
            "Gıda ve yemek hariç TÜFE, yıllık resmi ağırlıklarla zincirlenerek hesaplanmıştır.")
    # G3: aylık %
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for (ad, s), r in zip(seriler.items(), renkler):
        mm = (s.pct_change(fill_method=None) * 100).loc["2019-12-01":"2026-07-01"]
        ax.plot(mm.index, mm.values, color=r, lw=1.6, label=ad)
    ax.set_title("Grafik 3: TÜFE Fiyat Endeksleri (Aylık % Değişim)")
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    _kaydet(fig, "grafik_03_tufe_aylik.png", "TÜİK, TCMB EVDS; hesaplamalar.")
    # G4: yıllık %
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for (ad, s), r in zip(seriler.items(), renkler):
        yy = (s.pct_change(12, fill_method=None) * 100).loc["2019-12-01":"2026-07-01"]
        ax.plot(yy.index, yy.values, color=r, lw=2, label=ad)
        ax.annotate(f"%{yy.iloc[-1]:.0f}", (yy.index[-1], yy.iloc[-1]), xytext=(4, 0),
                    textcoords="offset points", color=r, fontsize=8, fontweight="bold")
    ax.set_title("Grafik 4: TÜFE Fiyat Endeksleri (Yıllık % Değişim)")
    ax.legend(frameon=False, loc="upper right", fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    _kaydet(fig, "grafik_04_tufe_yillik.png", "TÜİK, TCMB EVDS; hesaplamalar.")


# ------------------------------------------------------------------ Grafik 5-8: maliyet endeksleri
def grafik_5_8(sonuc):
    m = sonuc["maliyet"]
    sira = [("kirmizi_et", 5), ("tavuk", 6), ("ev_yemekleri", 7), ("fast_food", 8)]
    for konsept, no in sira:
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
        s = m[konsept]
        ax.plot(s.index, s.values, color=RENK[konsept], lw=2.2)
        _splice_cizgi(ax); _yil_ekseni(ax)
        for t, va in [("2019-12-01", "bottom"), ("2024-07-01", "bottom"), ("2026-07-01", "bottom")]:
            ax.annotate(f"{s.loc[t]:.0f}", (pd.Timestamp(t), s.loc[t]), xytext=(0, 6),
                        textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold",
                        color=RENK[konsept])
            ax.plot([pd.Timestamp(t)], [s.loc[t]], "o", ms=5, color=RENK[konsept])
        ax.set_title(f"Grafik {no}: Maliyet Endeksi — {endeks.KONSEPT_ETIKET[konsept]}\n(2013 Ocak=100)")
        _kaydet(fig, f"grafik_{no:02d}_maliyet_{konsept}.png",
                "TÜİK (MEDAS madde fiyatları, TÜFE, Tarım-ÜFE), TCMB EVDS, Asgari Ücret Tespit Komisyonu; hesaplamalar.",
                "Noktalı dikey çizgi (Nis 2022): madde fiyatı yayınının sonu; sonrası 5'li grup endeksleriyle uzatılmış proxy.")


# ------------------------------------------------------------------ Grafik 9-12: fiyat/maliyet
def grafik_9_12(sonuc):
    o = sonuc["oran"]
    uzun = endeks.uzun_donem_ort(o)
    sira = [("ev_yemekleri", 9), ("kirmizi_et", 10), ("tavuk", 11), ("fast_food", 12)]
    for konsept, no in sira:
        fig, ax = plt.subplots(figsize=(6.4, 4.0))
        s = o[konsept]
        ax.plot(s.index, s.values, color=RENK[konsept], lw=2.2, label="Fiyat/Maliyet")
        ax.axhline(uzun[konsept], color=GRI, lw=1.4, ls="--",
                   label=f"2013-2022 ort. ({uzun[konsept]:.2f})")
        _splice_cizgi(ax); _yil_ekseni(ax)
        for t in ["2024-07-01", "2026-07-01"]:
            ax.annotate(f"{s.loc[t]:.2f}", (pd.Timestamp(t), s.loc[t]), xytext=(0, 6),
                        textcoords="offset points", ha="center", fontsize=8.5,
                        fontweight="bold", color=RENK[konsept])
            ax.plot([pd.Timestamp(t)], [s.loc[t]], "o", ms=5, color=RENK[konsept])
        ax.set_title(f"Grafik {no}: Fiyat/Maliyet Oranı — {endeks.KONSEPT_ETIKET[konsept]}\n(2013 Ocak=1)")
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        _kaydet(fig, f"grafik_{no:02d}_oran_{konsept}.png",
                "TÜİK, TCMB EVDS; hesaplamalar.",
                "Oran kâr marjı SEVİYESİNİ göstermez; 2013 Ocak'a göre göreli seviyedir. "
                "Nis 2022 sonrası fiyat tarafı 11111/11112 endeksleriyle uzatılmış proxy'dir.")


# ------------------------------------------------------------------ Grafik 13-14: karşılaştırma barları
def grafik_13_14(sonuc):
    o = sonuc["oran"]
    uzun = endeks.uzun_donem_ort(o)
    t24 = o.loc["2024-07-01"]; t26 = o.loc["2026-07-01"]
    konseptler = ["ev_yemekleri", "kirmizi_et", "tavuk", "fast_food"]
    etiketler = [endeks.KONSEPT_ETIKET[k].replace(" ağırlıklı", "\nağırlıklı") for k in konseptler]
    x = np.arange(len(konseptler) + 1); w = 0.26
    # G13
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    u = list(uzun[konseptler].values) + [uzun[konseptler].mean()]
    a = list(t24[konseptler].values) + [t24[konseptler].mean()]
    b = list(t26[konseptler].values) + [t26[konseptler].mean()]
    ax.bar(x - w, u, w, label="2013-2022 ort.", color="#2a78d6")
    ax.bar(x,      a, w, label="Temmuz 2024", color="#eb6834")
    ax.bar(x + w,  b, w, label="Temmuz 2026", color="#1baf7a")
    for xi, (vu, va, vb) in zip(x, zip(u, a, b)):
        ax.text(xi - w, vu + 0.03, f"{vu:.2f}", ha="center", fontsize=7.5)
        ax.text(xi,     va + 0.03, f"{va:.2f}", ha="center", fontsize=7.5)
        ax.text(xi + w, vb + 0.03, f"{vb:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(etiketler + ["Tüm konseptler\n(ort.)"], fontsize=8)
    ax.set_title("Grafik 13: Fiyat/Maliyet Oranları (2013 Ocak=1)")
    ax.legend(frameon=False, fontsize=8)
    _kaydet(fig, "grafik_13_oran_karsilastirma.png", "TÜİK, TCMB EVDS; hesaplamalar.")
    # G14: ev yemekleri = 1 normalize
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    nu = uzun[konseptler] / uzun["ev_yemekleri"]
    na = t24[konseptler] / t24["ev_yemekleri"]
    nb = t26[konseptler] / t26["ev_yemekleri"]
    x = np.arange(len(konseptler))
    ax.bar(x - w, nu.values, w, label="2013-2022 ort.", color="#2a78d6")
    ax.bar(x,     na.values, w, label="Temmuz 2024", color="#eb6834")
    ax.bar(x + w, nb.values, w, label="Temmuz 2026", color="#1baf7a")
    for xi, (vu, va, vb) in zip(x, zip(nu.values, na.values, nb.values)):
        ax.text(xi - w, vu + 0.02, f"{vu:.2f}", ha="center", fontsize=7.5)
        ax.text(xi,     va + 0.02, f"{va:.2f}", ha="center", fontsize=7.5)
        ax.text(xi + w, vb + 0.02, f"{vb:.2f}", ha="center", fontsize=7.5)
    ax.set_xticks(x); ax.set_xticklabels(etiketler, fontsize=8)
    ax.axhline(1, color=GRI, lw=0.9, ls="--")
    ax.set_title("Grafik 14: Fiyat/Maliyet Oranları (Ev Yemekleri=1)")
    ax.legend(frameon=False, fontsize=8)
    _kaydet(fig, "grafik_14_oran_normalize.png", "TÜİK, TCMB EVDS; hesaplamalar.")


def hepsi():
    print("Grafikler üretiliyor…")
    sonuc = endeks.hepsi()
    grafik_1()
    grafik_2_4()
    grafik_5_8(sonuc)
    grafik_9_12(sonuc)
    grafik_13_14(sonuc)
    print("Tamam:", GRAF)

if __name__ == "__main__":
    hepsi()
