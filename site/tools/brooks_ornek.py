#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Brooks indikatörünün PYTHON REFERANS UYGULAMASI — yalnız ÖRNEK üretmek için.

NEDEN VAR. İndikatör sayfasındaki "nasıl kullanılır" bölümü uydurma barlarla
anlatılamaz (CLAUDE.md: uydurma yok). Örnekler GERÇEK OHLC'den ölçülür ve
ölçen kod burada durur: Pine'ın kurallarını aynen uygular, depodaki gerçek
barlar üzerinde koşar ve bulduğu olayları tarihi, sayısı ve hangi niteliğin
tuttuğuyla birlikte JSON'a yazar.

TEK KAYNAK KURALI. Aynı kuralın iki uygulaması bir gün sessizce ayrışır
(CLAUDE.md, birden çok yerde ölçülmüş). Bu yüzden buradaki hiçbir eşik ELLE
yazılmaz: hepsi .pine dosyalarının `input.*(...)` varsayılanlarından
AYRIŞTIRILIR. Pine'da bir eşik değişirse örnekler kendiliğinden o eşikle
yeniden ölçülür; ayrıştırılamayan bir eşik ENGEL üretir, sessizce varsayılana
düşmez.

VERİ KAYNAĞI. Bu oturumlardan Yahoo'ya çıkılamıyor (proxy 403). Barlar
depodaki teknik bülten figürlerinin İÇİNDEN okunuyor: site/public/teknik/
altındaki Plotly HTML'leri mum grafiğinin OHLC dizilerini gömülü taşır ve
o diziler teknik/olc.py'nin kapanmış-bar disiplininden geçmiştir.

KAPSAM. Kurallar ölçek bağımsız kurulur; dersin eşikleri 5 dakikalık barda
kalibre edilmiştir. Burada ölçülen barlar 1 saatlik ve 4 saatliktir ve bu
çıktının künyesine YAZILIR — örnek, dersin kalibrasyon ölçeği değildir.

Kullanım:
    python3 site/tools/brooks_ornek.py            # ölçer, JSON yazar
    python3 site/tools/brooks_ornek.py --denetle  # yalnız kapıları koşturur
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BURASI = Path(__file__).resolve().parent
SITE = BURASI.parent
KOK = SITE.parent
TEKNIK = SITE / "public" / "teknik"
PINE_FH = SITE / "public" / "indikatorler" / "brooks-fiyat-hareketi.pine"
PINE_RP = SITE / "public" / "indikatorler" / "brooks-rejim-panosu.pine"
CIKTI = SITE / "src" / "data" / "brooks_ornek.json"


# ── Pine sabitlerini AYRIŞTIRMA (tek kaynak) ────────────────────────────────
_INPUT = re.compile(
    r"^\s*(?P<ad>\w+)\s*=\s*input\.(?P<tip>float|int|bool)\(\s*(?P<deger>[^,]+?)\s*,",
    re.M,
)


def pine_sabitleri(yol: Path) -> dict[str, float | int | bool]:
    """`.pine` dosyasının input varsayılanlarını okur. Tek kaynak burasıdır."""
    metin = yol.read_text(encoding="utf-8")
    out: dict[str, float | int | bool] = {}
    for m in _INPUT.finditer(metin):
        ham = m.group("deger")
        tip = m.group("tip")
        if tip == "bool":
            out[m.group("ad")] = ham.strip() == "true"
        elif tip == "int":
            out[m.group("ad")] = int(ham)
        else:
            out[m.group("ad")] = float(ham)
    return out


def sabit(sozluk: dict, ad: str, kaynak: Path):
    """Eşiği ADIYLA ister. Bulamazsa ENGEL — sessizce varsayılana düşmez."""
    if ad not in sozluk:
        raise SystemExit(
            f"ENGEL · '{ad}' eşiği {kaynak.name} içinde bulunamadı. "
            f"Dosyada bulunan girdiler: {', '.join(sorted(sozluk)) or '(yok)'}"
        )
    return sozluk[ad]


# ── Barları depodaki figürlerin içinden okuma ───────────────────────────────
@dataclass(frozen=True)
class Seri:
    slug: str
    dilim: str
    zaman: list[str]
    o: list[float]
    h: list[float]
    l: list[float]
    c: list[float]

    def __len__(self) -> int:
        return len(self.c)


_NEWPLOT = re.compile(r'Plotly\.newPlot\(\s*"[^"]+",\s*(\[.*?\]),\s*\{', re.S)


def bar_oku(yol: Path) -> Seri:
    m = _NEWPLOT.search(yol.read_text(encoding="utf-8"))
    if not m:
        raise SystemExit(f"ENGEL · {yol.name} içinde Plotly verisi bulunamadı.")
    izler = json.loads(m.group(1))
    mum = next((t for t in izler if t.get("type") == "candlestick"), None)
    if mum is None:
        raise SystemExit(f"ENGEL · {yol.name} içinde mum izi yok.")
    slug, _, dilim = yol.stem.partition("-")
    seri = Seri(slug, dilim, mum["x"], mum["open"], mum["high"], mum["low"], mum["close"])
    # Eksik gözlem sessizce sıfır olmasın (CLAUDE.md: çizim katmanı da veri doldurur).
    for ad, dizi in (("open", seri.o), ("high", seri.h), ("low", seri.l), ("close", seri.c)):
        if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in dizi):
            raise SystemExit(f"ENGEL · {yol.name} · {ad} dizisinde boş gözlem var.")
    return seri


# ── Göstergeler (Pine semantiği) ────────────────────────────────────────────
def ema(x: list[float], n: int) -> list[float | None]:
    """TradingView ta.ema: ilk n-1 bar na, n'inci bar SMA ile tohumlanır."""
    a = 2.0 / (n + 1.0)
    out: list[float | None] = [None] * len(x)
    if len(x) < n:
        return out
    out[n - 1] = sum(x[:n]) / n
    for i in range(n, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]  # type: ignore[operator]
    return out


def en_yuksek(x: list[float], i: int, n: int) -> float:
    """ta.highest(x[1], n) karşılığı: i-1'de biten n barın azamisi."""
    return max(x[max(0, i - n) : i])


def en_dusuk(x: list[float], i: int, n: int) -> float:
    return min(x[max(0, i - n) : i])


# ── Fiyat paneli indikatörü ─────────────────────────────────────────────────
class FiyatPaneli:
    def __init__(self, s: Seri, p: dict):
        self.s = s
        self.p = p
        self.ema = ema(s.c, int(sabit(p, "maUzunluk", PINE_FH)))
        self.n = len(s)

    # bar anatomisi ---------------------------------------------------------
    def menzil(self, i: int) -> float:
        return self.s.h[i] - self.s.l[i]

    def govde_oran(self, i: int) -> float:
        m = self.menzil(i)
        return abs(self.s.c[i] - self.s.o[i]) / m if m > 0 else 0.0

    def sinif(self, i: int) -> str:
        g = self.govde_oran(i)
        if g >= sabit(self.p, "gucluGovde", PINE_FH):
            return "güçlü trend"
        if g >= sabit(self.p, "trendGovde", PINE_FH):
            return "trend"
        if g <= sabit(self.p, "dojiGovde", PINE_FH):
            return "doji"
        return "ara"

    def guclu_boga(self, i: int) -> bool:
        return self.govde_oran(i) >= sabit(self.p, "gucluGovde", PINE_FH) and self.s.c[i] > self.s.o[i]

    def guclu_ayi(self, i: int) -> bool:
        return self.govde_oran(i) >= sabit(self.p, "gucluGovde", PINE_FH) and self.s.c[i] < self.s.o[i]

    def ortusme(self, i: int) -> float:
        if i == 0:
            return 0.0
        onceki = self.s.h[i - 1] - self.s.l[i - 1]
        if onceki <= 0:
            return 0.0
        kesisim = min(self.s.h[i], self.s.h[i - 1]) - max(self.s.l[i], self.s.l[i - 1])
        return max(0.0, kesisim) / onceki

    # always-in ------------------------------------------------------------
    def always_in(self) -> tuple[list[int], list[int]]:
        """Her barda always-in yönü + dönüş barlarının indeksleri."""
        ai, yon, donus = 0, [], []
        for i in range(self.n):
            onceki = ai
            iki_boga = i >= 3 and self.guclu_boga(i - 1) and self.guclu_boga(i - 2)
            iki_ayi = i >= 3 and self.guclu_ayi(i - 1) and self.guclu_ayi(i - 2)
            if iki_boga and self.s.c[i] >= self.s.o[i]:
                ai = 1
            elif iki_ayi and self.s.c[i] <= self.s.o[i]:
                ai = -1
            yon.append(ai)
            if ai != onceki and i > 0:
                donus.append(i)
        return yon, donus

    # sinyal barı ----------------------------------------------------------
    def nitelikler(self, i: int, boga: bool) -> dict[str, bool]:
        s, p = self.s, self.p
        m = self.menzil(i)
        alt = min(s.o[i], s.c[i]) - s.l[i]
        ust = s.h[i] - max(s.o[i], s.c[i])
        kp = int(sabit(p, "kapanisPenc", PINE_FH))
        up = int(sabit(p, "ucPenc", PINE_FH))
        esik = sabit(p, "ortusmeEsik", PINE_FH)
        if boga:
            n1 = s.o[i] <= s.c[i - 1] and s.c[i] > s.o[i] and s.c[i] > s.c[i - 1]
            n2 = m > 0 and m / 3 <= alt <= m / 2 and ust <= m * 0.15
            n5 = s.c[i] > en_yuksek(s.c, i, kp) and s.h[i] > en_yuksek(s.h, i, up)
        else:
            n1 = s.o[i] >= s.c[i - 1] and s.c[i] < s.o[i] and s.c[i] < s.c[i - 1]
            n2 = m > 0 and m / 3 <= ust <= m / 2 and alt <= m * 0.15
            n5 = s.c[i] < en_dusuk(s.c, i, kp) and s.l[i] < en_dusuk(s.l, i, up)
        return {"n1": n1, "n2": n2, "n3": self.ortusme(i) <= esik, "n5": n5}

    def kalite(self, i: int, boga: bool) -> int:
        return sum(self.nitelikler(i, boga).values())

    def donus_bari(self, i: int, boga: bool) -> bool:
        orta = (self.s.h[i] + self.s.l[i]) / 2
        return (self.s.c[i] > self.s.o[i] or self.s.c[i] > orta) if boga else (
            self.s.c[i] < self.s.o[i] or self.s.c[i] < orta
        )

    # ortalama ilişkisi ----------------------------------------------------
    def yon_filtresi(self, i: int) -> str:
        pen = int(sabit(self.p, "yonPencere", PINE_FH))
        esik = int(sabit(self.p, "yonEsik", PINE_FH))
        if i + 1 < pen:
            return "serbest"
        pencere = range(i - pen + 1, i + 1)
        e = [self.ema[j] for j in pencere]
        if any(v is None for v in e):
            return "serbest"
        ust = sum(1 for j in pencere if self.s.c[j] > self.ema[j])  # type: ignore[operator]
        alt = sum(1 for j in pencere if self.s.c[j] < self.ema[j])  # type: ignore[operator]
        if ust >= esik:
            return "yalnız AL"
        if alt >= esik:
            return "yalnız SAT"
        return "serbest"

    def gap_sayac(self) -> list[int]:
        out, sayac = [], 0
        for i in range(self.n):
            e = self.ema[i]
            dokundu = e is not None and self.s.l[i] <= e <= self.s.h[i]
            sayac = 0 if dokundu else sayac + 1
            out.append(sayac)
        return out


# ── Alt panel: rejim panosu ─────────────────────────────────────────────────
class RejimPanosu:
    def __init__(self, s: Seri, p: dict):
        self.s = s
        self.p = p
        self.pencere = int(sabit(p, "pencere", PINE_RP))
        self.ema = ema(s.c, int(sabit(p, "maUzunluk", PINE_RP)))

    def olcu(self, i: int) -> dict | None:
        s, p, w = self.s, self.p, self.pencere
        if i + 1 < w or self.ema[i] is None or self.ema[i - w + 1] is None:
            return None
        pencere = range(i - w + 1, i + 1)
        g_esik = sabit(p, "ortusmeEsik", PINE_RP)
        d_esik = sabit(p, "dojiGovde", PINE_RP)

        def govde(j: int) -> float:
            m = s.h[j] - s.l[j]
            return abs(s.c[j] - s.o[j]) / m if m > 0 else 0.0

        def ort(j: int) -> float:
            onceki = s.h[j - 1] - s.l[j - 1]
            if j == 0 or onceki <= 0:
                return 0.0
            return max(0.0, min(s.h[j], s.h[j - 1]) - max(s.l[j], s.l[j - 1])) / onceki

        ortusme_oran = sum(1 for j in pencere if ort(j) >= g_esik) / w
        doji_oran = sum(1 for j in pencere if govde(j) <= d_esik) / w
        kesisme = sum(
            1
            for j in pencere
            if self.ema[j] is not None
            and self.ema[j - 1] is not None
            and (
                (s.c[j] > self.ema[j] and s.c[j - 1] <= self.ema[j - 1])
                or (s.c[j] < self.ema[j] and s.c[j - 1] >= self.ema[j - 1])
            )
        )
        aralik = max(s.h[j] for j in pencere) - min(s.l[j] for j in pencere)
        net = abs(s.c[i] - s.c[i - w + 1])
        net_aralik = net / aralik if aralik > 0 else 0.0

        dizi = azami = 0
        yon = 0
        for j in pencere:
            trend = govde(j) >= 0.50
            bu = 1 if (trend and s.c[j] > s.o[j]) else -1 if (trend and s.c[j] < s.o[j]) else 0
            dizi = dizi + 1 if (bu != 0 and bu == yon) else (1 if bu != 0 else 0)
            yon = bu
            azami = max(azami, dizi)

        isaret = {
            "ortusme": ortusme_oran >= sabit(p, "ortusmePay", PINE_RP),
            "doji": doji_oran >= sabit(p, "dojiPay", PINE_RP),
            "kesisme": kesisme >= int(sabit(p, "kesismeEsik", PINE_RP)),
            "net": net_aralik <= sabit(p, "netEsik", PINE_RP),
            "dizi": azami < int(sabit(p, "diziEsik", PINE_RP)),
        }
        n = sum(isaret.values())
        return {
            "ortusme_oran": round(ortusme_oran, 3),
            "doji_oran": round(doji_oran, 3),
            "kesisme": kesisme,
            "net_aralik": round(net_aralik, 3),
            "azami_dizi": azami,
            "isaret": isaret,
            "n": n,
            "rejim": "BANT" if n >= 4 else "trend" if n <= 1 else "ara",
        }


# ── Gövde kapısı: bir seri GERÇEK mum taşımıyorsa örneğe giremez ────────────
#
# ÖLÇÜLDÜ (16 seri, 5.354 bar). Doji payı iki kümede toplanıyor ve aralarında
# geniş bir boşluk var: sağlıklı serilerde 0,088–0,145 · bozuk serilerde
# 0,954–0,977. Bozuk üçlüde medyan gövde/menzil 0,000–0,014, yani bar
# ANATOMİSİ diye bir şey yok — açılış ile kapanış aynı kotasyondan geliyor.
# Bu, indikatörün kusuru değil BESLEMENİN kusurudur ve her ölçüsünü çürütür:
# bar sınıfı, always-in, kalite, hepsi gövdeden okunur.
#
# Eşik ölçülen boşluğun ortasına konur; sezgiyle değil. Dışlanan seri
# SİLİNMEZ, künyeye SEBEBİYLE yazılır (CLAUDE.md: dışlama işaretlemektir).
GOVDE_KAPISI = 0.50


def govde_kunyesi(s: Seri) -> dict:
    oran = []
    for i in range(len(s)):
        m = s.h[i] - s.l[i]
        oran.append(abs(s.c[i] - s.o[i]) / m if m > 0 else 0.0)
    sirali = sorted(oran)
    doji = sum(1 for v in oran if v <= 0.10) / len(oran)
    return {
        "doji_payi": round(doji, 3),
        "medyan_govde": round(sirali[len(sirali) // 2], 3),
        "sifir_govde_payi": round(sum(1 for v in oran if v == 0) / len(oran), 3),
        "gecti": doji < GOVDE_KAPISI,
    }


# ── Duman sınaması: referans uygulama SENTETİK barlarda sınanır ─────────────
def _duman(p_fh: dict, p_rp: dict) -> None:
    """Kuralın kendi ilan ettiği hâllere koşulur (CLAUDE.md: kuralı ölçen
    ölçüt de sınanır). Ağa çıkmaz, saniyeler sürer."""

    def seri(barlar: list[tuple[float, float, float, float]]) -> Seri:
        return Seri(
            "sinama",
            "test",
            [f"b{i}" for i in range(len(barlar))],
            [b[0] for b in barlar],
            [b[1] for b in barlar],
            [b[2] for b in barlar],
            [b[3] for b in barlar],
        )

    hata: list[str] = []

    # ① Always-in: iki güçlü boğa barı + takip barı ayı kapanışı DEĞİLSE long.
    #    Dizi: 2 dolgu, 2 güçlü boğa, 1 takip (boğa kapanış) → 4. barda dönüş.
    b = [(10, 10.4, 9.6, 10.0), (10, 10.4, 9.6, 10.0),
         (10.0, 11.0, 9.95, 10.95), (11.0, 12.0, 10.95, 11.95),
         (11.95, 12.2, 11.9, 12.10)]
    yon, donus = FiyatPaneli(seri(b), p_fh).always_in()
    if donus != [4] or yon[4] != 1:
        hata.append(f"① always-in long dönüşü 4. barda beklenirdi; dönüş={donus} yön={yon}")

    # ② Takip barının ölçütü bir YOKLUKTUR: aynı dizi, takip barı AYI kapanış
    #    → long'a dönüş OLMAZ.
    b2 = b[:4] + [(12.10, 12.2, 11.5, 11.60)]
    yon2, donus2 = FiyatPaneli(seri(b2), p_fh).always_in()
    if donus2:
        hata.append(f"② ayı kapanışlı takip barı long dönüşü üretmemeliydi; dönüş={donus2}")

    # ③ Tek güçlü trend barı yetmez (ders: bağlamla yeterli olabilir — ölçülemez).
    b3 = [(10, 10.4, 9.6, 10.0)] * 3 + [(10.0, 11.0, 9.95, 10.95), (10.95, 11.1, 10.9, 11.0)]
    if FiyatPaneli(seri(b3), p_fh).always_in()[1]:
        hata.append("③ tek güçlü trend barı always-in dönüşü üretmemeliydi")

    # ④ Canlı kalite tavanı DÖRTtür (beşinci nitelik sonraki bara bakar).
    tavan = 4
    fp = FiyatPaneli(seri(b), p_fh)
    if max(fp.kalite(i, True) for i in range(1, len(b))) > tavan:
        hata.append("④ canlı kalite 4'ü aşamaz")
    if len(fp.nitelikler(3, True)) != tavan:
        hata.append(f"④ nitelik sayısı {tavan} olmalı, {len(fp.nitelikler(3, True))} bulundu")

    # ⑤ Örtüşme: iç bar önceki barı %100 örtüyor (eşik aşılır, n3 düşer).
    b5 = [(10, 11, 9, 10.5), (10.2, 10.8, 9.2, 10.4)]
    o = FiyatPaneli(seri(b5), p_fh).ortusme(1)
    if not 0.79 <= o <= 0.81:
        hata.append(f"⑤ örtüşme 0,80 beklenirdi; {o:.3f}")
    if FiyatPaneli(seri(b5), p_fh).nitelikler(1, True)["n3"]:
        hata.append("⑤ eşiği aşan örtüşmede n3 tutmamalıydı")

    # ⑥ Rejim panosu: tamamen yatay, örtüşen, doji barlardan kurulu pencere
    #    BANT; tek yönde güçlü trend barlarından kurulu pencere trend.
    w = int(sabit(p_rp, "pencere", PINE_RP))
    # Pencere + EMA ısınması: ema[i-w+1] çözülebilmeli, yoksa ölçü None döner.
    n6 = w + int(sabit(p_rp, "maUzunluk", PINE_RP)) + 5
    bant = [(10.0, 10.5, 9.5, 10.0)] * n6
    rb = RejimPanosu(seri(bant), p_rp).olcu(n6 - 1)
    if rb is None or rb["rejim"] != "BANT":
        hata.append(f"⑥ yatay pencere BANT olmalıydı; {rb and rb['rejim']}")
    trend = [(10.0 + i, 10.9 + i, 9.95 + i, 10.85 + i) for i in range(n6)]
    rt = RejimPanosu(seri(trend), p_rp).olcu(n6 - 1)
    if rt is None or rt["rejim"] != "trend":
        hata.append(f"⑥ tek yönlü pencere trend olmalıydı; {rt and rt['rejim']}")

    # ⑦ Sabit ADIYLA istenir: olmayan eşik ENGEL üretir, varsayılana düşmez.
    try:
        sabit(p_fh, "olmayanEsik", PINE_FH)
    except SystemExit:
        pass
    else:
        hata.append("⑦ tanımsız eşik ENGEL üretmeliydi")

    if hata:
        print("DUMAN DÜŞTÜ:", file=sys.stderr)
        for h in hata:
            print("  ✗", h, file=sys.stderr)
        raise SystemExit(1)
    print("duman · 7 madde GEÇTİ")


# ── Örnek arama ─────────────────────────────────────────────────────────────
ENSTRUMAN_AD = {
    "eurusd": "EUR/USD",
    "dxy": "Dolar endeksi (DXY)",
    "usdchf": "USD/CHF",
    "xu100": "BIST 100",
    "us10y": "ABD 10 yıllık getiri",
    "us2y": "ABD 2 yıllık getiri",
}
DILIM_AD = {"s1": "1 saatlik", "s4": "4 saatlik", "gunluk": "günlük"}


def _bar_kunye(fp: FiyatPaneli, i: int, ond: int) -> dict:
    s = fp.s
    return {
        "zaman": s.zaman[i],
        "o": round(s.o[i], ond),
        "h": round(s.h[i], ond),
        "l": round(s.l[i], ond),
        "c": round(s.c[i], ond),
        "govde_oran": round(fp.govde_oran(i), 3),
        "sinif": fp.sinif(i),
        "ortusme": round(fp.ortusme(i), 3),
    }


def ornekleri_ara(seriler: list[Seri], p_fh: dict, p_rp: dict) -> dict:
    bulgu: dict = {"flip": [], "kalite": [], "ortusme_reddi": [], "yasak": [], "rejim": [], "sayim": {}}
    for s in seriler:
        ond = 4 if max(s.c) < 10 else 2 if max(s.c) < 1000 else 0
        fp = FiyatPaneli(s, p_fh)
        rp = RejimPanosu(s, p_rp)
        yon, donus = fp.always_in()
        gap = fp.gap_sayac()
        ad = f"{ENSTRUMAN_AD.get(s.slug, s.slug)} · {DILIM_AD.get(s.dilim, s.dilim)}"

        # ① always-in dönüşleri — dönüşü kuran ÜÇ bar birlikte yazılır
        for i in donus:
            if i < 3:
                continue
            bulgu["flip"].append({
                "ad": ad, "yon": "long" if yon[i] == 1 else "short",
                "barlar": [_bar_kunye(fp, j, ond) for j in (i - 2, i - 1, i)],
                "rejim": (rp.olcu(i) or {}).get("rejim"),
                "yon_filtresi": fp.yon_filtresi(i),
            })

        # ② sinyal barı kalitesi + ③ örtüşme reddi + ④ yön filtresi yasağı
        for i in range(max(10, int(sabit(p_fh, "kapanisPenc", PINE_FH))), len(s)):
            for boga in (True, False):
                if not fp.donus_bari(i, boga):
                    continue
                nit = fp.nitelikler(i, boga)
                k = sum(nit.values())
                filtre = fp.yon_filtresi(i)
                yasak = (filtre == "yalnız AL" and not boga) or (filtre == "yalnız SAT" and boga)
                kayit = {
                    "ad": ad, "yon": "boğa" if boga else "ayı", "kalite": k,
                    "nitelikler": nit, "bar": _bar_kunye(fp, i, ond),
                    "onceki": _bar_kunye(fp, i - 1, ond),
                    "always_in": {1: "long", -1: "short", 0: "—"}[yon[i]],
                    "yon_filtresi": filtre, "gap": gap[i],
                    "rejim": (rp.olcu(i) or {}).get("rejim"),
                }
                if k == 4:
                    bulgu["kalite"].append(kayit)
                if not nit["n3"] and k >= 2:
                    bulgu["ortusme_reddi"].append(kayit)
                if yasak and k >= 3:
                    bulgu["yasak"].append(kayit)

        # ⑤ rejim pencereleri
        for i in range(len(s)):
            o = rp.olcu(i)
            if o is None:
                continue
            o = dict(o, ad=ad, zaman=s.zaman[i], bas=s.zaman[i - rp.pencere + 1])
            bulgu["rejim"].append(o)

        bulgu["sayim"][ad] = {
            "bar": len(s),
            "bas": s.zaman[0],
            "son": s.zaman[-1],
            "flip": len([i for i in donus if i >= 3]),
            "kalite4": len([k for k in bulgu["kalite"] if k["ad"] == ad]),
            "azami_gap": max(gap),
        }
    return bulgu


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--denetle", action="store_true", help="yalnız kapıları koştur")
    a = ap.parse_args()

    p_fh = pine_sabitleri(PINE_FH)
    p_rp = pine_sabitleri(PINE_RP)
    _duman(p_fh, p_rp)
    if a.denetle:
        return

    yollar = sorted(TEKNIK.glob("*.html"))
    if not yollar:
        raise SystemExit(f"ENGEL · {TEKNIK} altında figür yok.")
    hepsi = [bar_oku(y) for y in yollar]
    govde = {f"{s.slug}-{s.dilim}": govde_kunyesi(s) for s in hepsi}
    seriler = [s for s in hepsi if govde[f"{s.slug}-{s.dilim}"]["gecti"]]
    dislanan = {k: v for k, v in govde.items() if not v["gecti"]}
    if not seriler:
        raise SystemExit("ENGEL · gövde kapısından geçen seri kalmadı.")
    bulgu = ornekleri_ara(seriler, p_fh, p_rp)
    bulgu["kunye"] = {
        "kaynak": "site/public/teknik/*.html (teknik/olc.py'nin kapanmış-bar disiplininden geçmiş OHLC)",
        "esik_kaynagi": {PINE_FH.name: p_fh, PINE_RP.name: p_rp},
        "govde_kapisi": GOVDE_KAPISI,
        "govde": govde,
        "dislanan": dislanan,
        "seri": len(seriler),
        "bar": sum(len(s) for s in seriler),
    }
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    CIKTI.write_text(json.dumps(bulgu, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"yazıldı · {CIKTI.relative_to(KOK)}")
    for ad, v in dislanan.items():
        print(f"  DIŞLANDI · {ad:26s} doji payı {v['doji_payi']:.3f} · medyan gövde/menzil "
              f"{v['medyan_govde']:.3f} — bu besleme gerçek mum gövdesi taşımıyor")
    for ad, s in bulgu["sayim"].items():
        print(f"  {ad:34s} {s['bar']:4d} bar  flip {s['flip']:3d}  4/4 {s['kalite4']:3d}  azami gap {s['azami_gap']:3d}")


if __name__ == "__main__":
    main()
