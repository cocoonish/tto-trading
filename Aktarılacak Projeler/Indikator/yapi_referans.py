#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO · Yapı ve Momentum — iki panelli indikatörün Python REPLİKASYONU.

Pine'ın koşturacağı her kural burada, kapanmış OHLC barlarından, bar bar
hesaplanır; backtest ve figürler bu dosyadan beslenir, Pine bu dosyayla
eşleştirilir (sabit paritesi + geleceğe bakma sınaması). Kaynaklar ve
mekanik seçimler (uydurma yok; her seçim ADIYLA):

  · Swing: 2k+1 fraktal, KESİN eşitsizlik (SMC dersi 2.1; Pine ta.pivothigh
    ile aynı). Pivot, k bar sonra onaylanır — onay gecikmesi, repaint değil.
  · Yapı: onaylı swing'lerin almaşmalı dizisi (kullanıcı Pine'ı 60–86).
    BOS = kapanış son onaylı swing'in ÖTESİNDE (gövde; SMC 2.5); fitil aşımı
    BOS değil SWEEP'tir. CHoCH = korunan swing'in ters yönde gövdeyle
    kırılması (SMC 2.6). MSS = CHoCH + kırılım bacağında yer değiştirme
    (displacement: gövde/menzil ≥ 0,60 ve menzil ≥ 1,5× son 10 bar
    ortalaması, SMC 4.1) + kırılımdan önceki `SWEEP_PENCERE` barda adlandırılmış
    bir havuzun süpürülmüş olması (SMC 2.6 dört koşul).
  · Dealing range: son dış swing çifti (kırılan dip → kırılım tepesi);
    EQ, premium/discount, OTE 0,62–0,79 (0,705) (SMC 2.7–2.8).
  · Havuzlar: önceki gün/hafta H/L (UTC gün; kapanmış dönem), onaylı
    swing'ler, eşit tepe/dip (fark ≤ 0,15×ATR14; SMC 3.2). Sweep = fitil
    ötede, kapanış geride, aşım ≥ `ASIM_ATR`×ATR14 (SMC 3.3, 14.3); run =
    kapanış ötede.
  · FVG: üç bar; boşluk ≥ `FVG_ATR`×ATR14; orta bar displacement eşiklerini
    karşılar (SMC 4.2). Durum: taze → CE'ye dokunuldu → dolduruldu → ters
    döndü (IFVG, gövdeyle karşı kenar; SMC 4.3).
  · OB: yapı kıran bacaktaki displacement'tan önceki son ZIT renkli mum,
    gövde bölgesi, MT = orta (SMC 4.4). Yumuşak okul: gövde kapanışı uzak
    kenarı geçmedikçe canlı; ilk dokunuşta 'taze' düşer.
  · Harmonik: dersin tarayıcı bantları (harmonik ders 9.3, satır 992) —
    Gartley · Bat · Alt Bat · Butterfly · Crab · Deep Crab · Cypher · Shark;
    PRZ, C onaylanınca ÖNCEDEN çizilir; tamamlanma PRZ'ye giriş; teyit
    dönüş mumu kapanışı; stop ve hedef dersin tablosundan (6.3–6.5).
  · Diverjans: kullanıcı Pine'ının kuralı — HAM pivotlarda fiyat/RSI kıyası
    (pivot barında), BB dilimi · RSI dilimi · trend ONAY barında, 25 satırlık
    koşul tablosu (ttoallinone.pine 108–242). İsabet yüzdeleri KAYNAK
    İDDİASIDIR, burada yeniden ölçülür.
  · Momentum (alt panel): RSI14; itki = gövde/ATR; göreli sıra (percentrank,
    280 bar, Brooks v2 sözleşmesi); dealing range içindeki konum (%).

Pine paritesi: `SABIT` sözlüğü Pine `input` öntanımlılarıyla birebir tutulur
ve `duman.py` ikisini karşılaştırır."""
from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

KOK = Path(__file__).resolve().parent
DEPO = KOK.parents[1]
sys.dont_write_bytecode = True   # public altına __pycache__ bırakma: yayın kapısı düşer
sys.path.insert(0, str(DEPO / "site" / "public" / "indikatorler"))
from brooks_referans import Seri  # noqa: E402

# ── Pine input öntanımlıları (parite kapısı bunları Pine'la karşılaştırır) ──
SABIT: dict[str, float | int] = {
    "k_swing": 3,            # yapı swing'i: 2k+1 fraktal
    "k_ic": 1,               # iç swing / diverjans pivotu (kullanıcı: L=R=1)
    "atr_n": 14,
    "rsi_n": 14,
    "ema_n": 50,             # diverjans trend süzgeci (kullanıcı: EMA 50)
    "bb_n": 20, "bb_k": 2.0,
    "disp_govde": 0.60,      # gövde/menzil eşiği (SMC 4.1)
    "disp_kat": 1.5,         # menzil ≥ kat × son 10 bar ortalama menzili
    "disp_pencere": 10,
    "fvg_atr": 0.5,          # boşluk ≥ fvg_atr × ATR14
    "esit_atr": 0.15,        # EQH/EQL toleransı (ATR14 katı)
    "asim_atr": 0.10,        # sweep için asgari fitil aşımı (ATR14 katı)
    "sweep_pencere": 10,     # MSS için: kırılımdan önce kaç barda sweep aranır
    "ote_alt": 0.62, "ote_ust": 0.79, "ote_orta": 0.705,
    "tarihce": 280,          # göreli sıra penceresi (Brooks v2 ile aynı)
    "harmonik_tol": 0.0,     # bantlar dersin tarayıcı bantları; ek tolerans yok
    "prz_azami_xa": 0.10,    # PRZ yayılımı ≤ %10 XA (ders: ≤%3 sıkı · %5–8 kabul · üstü gevşek; 10 son sınır)
}

# ── Harmonik kalıp bantları — ders 9.3 (satır 992) tarayıcı bantları ────────
# (B = |AB|/|XA| · D = |AD|/|XA| · BC = |CD|/|BC|); C bandı hepsinde 0,382–0,886
# ve C, A'yı aşmaz (Cypher/Shark hariç). Geçersizlik ve hedef: ders 6.3–6.5.
HARMONIK = {
    #  ad          B_alt  B_ust  D_alt  D_ust  BC_alt BC_ust  stop (XA katı)   T1/T2 (AD)
    "Gartley":   (0.588, 0.648, 0.75, 0.82, 1.13, 1.70, 1.00, (0.382, 0.618)),
    "Bat":       (0.36,  0.52,  0.85, 0.92, 1.60, 2.70, 1.00, (0.382, 0.618)),
    "Alt Bat":   (0.30,  0.40,  1.10, 1.16, 2.00, 3.618, 1.272, (0.382, 0.618)),
    "Butterfly": (0.75,  0.82,  1.22, 1.66, 1.60, 2.70, 1.618, (0.382, 0.618)),
    "Crab":      (0.36,  0.65,  1.55, 1.70, 2.50, 3.70, 2.00, (0.382, 0.618)),
    "Deep Crab": (0.85,  0.92,  1.55, 1.70, 2.24, 3.618, 2.00, (0.382, 0.618)),
}
IDEAL_D = {"Gartley": 0.786, "Bat": 0.886, "Alt Bat": 1.13, "Butterfly": 1.27, "Crab": 1.618, "Deep Crab": 1.618}
# Cypher: C, A'yı 1,272–1,414 aşar; D = 0,786 XC; stop X. Shark: B, X'i aşar
# (AB = 1,13–1,618 XA); C = 0,886–1,13 · 0X ve 1,618–2,24 · AB; işlem C'de.
CYPHER = {"B": (0.382, 0.618), "C_xa": (1.272, 1.414), "D_xc": 0.786, "D_bant": (0.75, 0.82), "stop": 1.00}
SHARK = {"B_xa": (1.13, 1.618), "C_0x": (0.886, 1.13), "C_ab": (1.618, 2.24), "stop_0x": 1.13}

# ── Kullanıcı Pine'ının 25 satırlık diverjans tablosu (ttoallinone.pine 126–150)
# (div tipi 1 RegBull 2 RegBear 3 HidBull 4 HidBear · BB dilimi 1–6 · RSI dilimi
#  1–6 · trend 0 Any 1 Up 2 Down · SL×ATR · TP×ATR · kaynağın isabet iddiası)
DIV_TABLO = [
    (3, 5, 6, 1, 2.0, 6.0, 63.6), (1, 1, 1, 2, 3.0, 3.0, 62.5), (2, 3, 4, 2, 3.0, 6.0, 61.5),
    (1, 6, 5, 1, 2.5, 2.5, 60.7), (1, 1, 2, 2, 2.5, 2.5, 60.7), (4, 3, 4, 1, 3.0, 3.0, 60.0),
    (2, 5, 5, 0, 3.0, 6.0, 60.0), (1, 3, 2, 0, 2.0, 3.0, 60.0), (2, 2, 4, 1, 3.0, 3.0, 57.9),
    (2, 5, 4, 2, 3.0, 3.0, 55.7), (1, 5, 4, 2, 2.0, 2.0, 54.5), (1, 4, 3, 1, 2.0, 6.0, 54.5),
    (1, 2, 2, 2, 2.5, 2.5, 54.1), (4, 3, 3, 1, 2.5, 3.0, 53.7), (1, 2, 1, 2, 2.0, 2.0, 53.5),
    (3, 2, 4, 1, 2.0, 2.0, 52.6), (4, 1, 2, 2, 2.5, 2.5, 52.4), (3, 4, 4, 1, 2.5, 2.5, 52.2),
    (2, 4, 3, 1, 2.5, 3.0, 51.7), (1, 3, 3, 1, 2.0, 2.0, 51.5), (1, 6, 6, 1, 2.5, 4.0, 51.2),
    (1, 2, 3, 2, 2.5, 2.5, 51.0), (4, 6, 5, 1, 2.0, 6.0, 50.0), (3, 3, 4, 2, 3.0, 5.0, 50.0),
    (4, 1, 1, 2, 2.0, 2.0, 50.0),
]


# ═══════════════════════════════════════════════════════════════════════════
#  Pine gösterge karşılıkları
# ═══════════════════════════════════════════════════════════════════════════
def rma(x: list[float], n: int) -> list[float | None]:
    """Pine ta.rma: ilk değer SMA(n), sonrası Wilder yumuşatma."""
    out: list[float | None] = [None] * len(x)
    if len(x) < n:
        return out
    v = sum(x[:n]) / n
    out[n - 1] = v
    for i in range(n, len(x)):
        v = (v * (n - 1) + x[i]) / n
        out[i] = v
    return out


def atr(s: Seri, n: int) -> list[float | None]:
    tr = [s.h[0] - s.l[0]] + [max(s.h[i] - s.l[i], abs(s.h[i] - s.c[i - 1]), abs(s.l[i] - s.c[i - 1]))
                              for i in range(1, len(s))]
    return rma(tr, n)


def rsi(c: list[float], n: int) -> list[float | None]:
    """Pine ta.rsi: rma(up)/rma(down)."""
    up = [0.0] + [max(c[i] - c[i - 1], 0.0) for i in range(1, len(c))]
    dn = [0.0] + [max(c[i - 1] - c[i], 0.0) for i in range(1, len(c))]
    ru, rd = rma(up[1:], n), rma(dn[1:], n)
    out: list[float | None] = [None] * len(c)
    for i in range(1, len(c)):
        a, b = ru[i - 1], rd[i - 1]
        if a is None or b is None:
            continue
        out[i] = 100.0 if b == 0 else (0.0 if a == 0 else 100 - 100 / (1 + a / b))
    return out


def ema(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(x)
    if len(x) < n:
        return out
    v = sum(x[:n]) / n
    out[n - 1] = v
    a = 2 / (n + 1)
    for i in range(n, len(x)):
        v = a * x[i] + (1 - a) * v
        out[i] = v
    return out


def sma(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(x)
    if len(x) < n:
        return out
    top = sum(x[:n])
    out[n - 1] = top / n
    for i in range(n, len(x)):
        top += x[i] - x[i - n]
        out[i] = top / n
    return out


def stdev(x: list[float], n: int) -> list[float | None]:
    """Pine ta.stdev: popülasyon σ."""
    out: list[float | None] = [None] * len(x)
    for i in range(n - 1, len(x)):
        w = x[i - n + 1:i + 1]
        m = sum(w) / n
        out[i] = math.sqrt(sum((v - m) ** 2 for v in w) / n)
    return out


def percentrank(x: list[float | None], i: int, n: int) -> float | None:
    """Pine ta.percentrank: önceki n değerin yüzde kaçı ≤ bugünkü (0–100)."""
    if i < n or x[i] is None:
        return None
    w = [v for v in x[i - n:i] if v is not None]
    if len(w) < n:
        return None
    return 100.0 * sum(1 for v in w if v <= x[i]) / n


def pivotlar(s: Seri, k: int) -> tuple[list[int], list[int]]:
    """Onaylı pivot barları (KESİN eşitsizlik). Pivot j, bar j+k'de onaylanır.
    Döner: (pivot high bar listesi, pivot low bar listesi)."""
    ph, pl = [], []
    for j in range(k, len(s) - k):
        hj, lj = s.h[j], s.l[j]
        if all(hj > s.h[m] for m in range(j - k, j)) and all(hj > s.h[m] for m in range(j + 1, j + k + 1)):
            ph.append(j)
        if all(lj < s.l[m] for m in range(j - k, j)) and all(lj < s.l[m] for m in range(j + 1, j + k + 1)):
            pl.append(j)
    return ph, pl


# ═══════════════════════════════════════════════════════════════════════════
#  Yapı motoru — bar bar durum makinesi
# ═══════════════════════════════════════════════════════════════════════════
@dataclass
class Swing:
    bar: int          # pivot barı
    onay: int         # onaylandığı bar (pivot + k)
    fiyat: float
    tur: str          # 'H' | 'L'
    alindi: bool = False  # havuz olarak süpürüldü/koşuldu mu


@dataclass
class Olay:
    bar: int
    tur: str          # 'BOS' | 'CHOCH' | 'MSS'
    yon: int          # +1 boğa · −1 ayı
    seviye: float     # kırılan seviye
    kaynak_bar: int   # kırılan swing'in barı
    displacement: bool
    sweep_once: bool


@dataclass
class FVG:
    bar: int          # M3 barı (kesinleştiği bar)
    yon: int
    alt: float
    ust: float
    ce: float
    durum: str = "taze"   # taze | ce | dolu | ters
    ce_bar: int | None = None
    dolu_bar: int | None = None
    ters_bar: int | None = None

    def acik(self, i: int) -> bool:
        """i barında hâlâ ekranda mı (dolmamış ve ters dönmemiş)."""
        return self.bar <= i and (self.dolu_bar is None or self.dolu_bar > i) and (self.ters_bar is None or self.ters_bar > i)


@dataclass
class OB:
    bar: int          # OB mumunun barı
    olay_bar: int     # onu tanımlayan yapı olayının barı
    yon: int
    alt: float        # gövde
    ust: float
    mt: float
    fitil: float      # stop referansı (boğa: low, ayı: high)
    taze: bool = True
    canli: bool = True
    taze_bar: int | None = None    # ilk dokunuş
    bitis_bar: int | None = None   # gövde kapanışı uzak kenarı geçti

    def acik(self, i: int) -> bool:
        return self.olay_bar <= i and (self.bitis_bar is None or self.bitis_bar > i)

    def taze_mi(self, i: int) -> bool:
        return self.acik(i) and (self.taze_bar is None or self.taze_bar > i)


@dataclass
class Havuz:
    ad: str           # 'PDH' 'PDL' 'PWH' 'PWL' 'SWH' 'SWL' 'EQH' 'EQL'
    seviye: float
    yon: int          # +1 üstte (BSL) · −1 altta (SSL)
    bar: int          # oluştuğu/onaylandığı bar
    durum: str = "acik"   # acik | sweep | run
    durum_bar: int | None = None


@dataclass
class PRZ:
    ad: str
    yon: int              # +1 boğa (D dip) · −1 ayı
    x: int; a: int; b: int; c: int   # pivot barları
    cizim_bar: int        # C onaylandığı bar (PRZ buradan itibaren bilinir)
    alt: float
    ust: float
    stop: float
    t1: float
    t2: float
    durum: str = "bekliyor"   # bekliyor | tamam | teyit | gecersiz | kacti
    durum_bar: int | None = None
    tamam_bar: int | None = None


class Yapi:
    """Fiyat panelinin bütün kuralları. `kos()` bar bar ilerler; her `i` için
    yalnız 0..i barları okunur (geleceğe bakma sınaması bunu ölçer)."""

    def __init__(self, s: Seri, sabit: dict | None = None):
        self.s = s
        self.p = dict(SABIT, **(sabit or {}))
        n = len(s)
        self.atr = atr(s, int(self.p["atr_n"]))
        self.menzil = [s.h[i] - s.l[i] for i in range(n)]
        self.ort_menzil = sma(self.menzil, int(self.p["disp_pencere"]))
        # çıktılar
        self.swingler: list[Swing] = []
        self.olaylar: list[Olay] = []
        self.fvgler: list[FVG] = []
        self.oblar: list[OB] = []
        self.havuzlar: list[Havuz] = []
        self.przler: list[PRZ] = []
        self.sweepler: list[tuple[int, str, float, int]] = []   # (bar, havuz adı, seviye, yön)
        self.trend = [0] * n
        self.pH: list[float | None] = [None] * n
        self.pL: list[float | None] = [None] * n
        self.aralik: list[tuple[float, float] | None] = [None] * n   # dealing range (L, H)
        self.konum: list[float | None] = [None] * n   # aralık içindeki konum 0–100
        self._ph, self._pl = pivotlar(s, int(self.p["k_swing"]))
        self._ph_set = {j + int(self.p["k_swing"]): j for j in self._ph}   # onay barı → pivot barı
        self._pl_set = {j + int(self.p["k_swing"]): j for j in self._pl}
        self._gun_hl: dict[int, tuple[float, float]] = {}
        self._hafta_hl: dict[int, tuple[float, float]] = {}
        self._kos()

    # ── yardımcılar ──────────────────────────────────────────────────────────
    def displacement(self, i: int) -> bool:
        m = self.menzil[i]
        om = self.ort_menzil[i - 1] if i >= 1 else None
        if m <= 0 or om is None or om <= 0:
            return False
        govde = abs(self.s.c[i] - self.s.o[i])
        return govde / m >= self.p["disp_govde"] and m >= self.p["disp_kat"] * om

    def _gun(self, i: int) -> int:
        return int(self.s.zaman[i]) // 86400

    def _hafta(self, i: int) -> int:
        # ISO benzeri: Pazartesi 00:00 UTC başlangıç (1970-01-01 Perşembe → +3 gün kaydır)
        return (int(self.s.zaman[i]) // 86400 + 3) // 7

    def _son_swing(self, tur: str, once: int | None = None) -> Swing | None:
        for sw in reversed(self.swingler):
            if sw.tur == tur and (once is None or sw.bar < once):
                return sw
        return None

    # ── ana döngü ────────────────────────────────────────────────────────────
    def _kos(self) -> None:
        s, p = self.s, self.p
        n = len(s)
        k = int(p["k_swing"])
        trend = 0
        pH: Swing | None = None
        pL: Swing | None = None
        ar_L: float | None = None
        ar_H: float | None = None
        bacak_bas: int | None = None      # dealing range bacağının başladığı bar
        gun_onceki: int | None = None
        hafta_onceki: int | None = None
        gun_h, gun_l = None, None
        hafta_h, hafta_l = None, None
        for i in range(n):
            # 1) Gün/hafta kapanışı → PDH/PDL/PWH/PWL havuzları (kapanmış dönem)
            if s.zaman is not None:
                g, w = self._gun(i), self._hafta(i)
                if gun_onceki is not None and g != gun_onceki:
                    self._kapat_havuz("PDH", "PDL")
                    self.havuzlar.append(Havuz("PDH", gun_h, +1, i))
                    self.havuzlar.append(Havuz("PDL", gun_l, -1, i))
                    gun_h, gun_l = None, None
                if hafta_onceki is not None and w != hafta_onceki:
                    self._kapat_havuz("PWH", "PWL")
                    self.havuzlar.append(Havuz("PWH", hafta_h, +1, i))
                    self.havuzlar.append(Havuz("PWL", hafta_l, -1, i))
                    hafta_h, hafta_l = None, None
                gun_h = s.h[i] if gun_h is None else max(gun_h, s.h[i])
                gun_l = s.l[i] if gun_l is None else min(gun_l, s.l[i])
                hafta_h = s.h[i] if hafta_h is None else max(hafta_h, s.h[i])
                hafta_l = s.l[i] if hafta_l is None else min(hafta_l, s.l[i])
                gun_onceki, hafta_onceki = g, w

            # 2) Havuz durumları: bu barın fitili/gövdesi neyi süpürdü, neyi koştu
            a = self.atr[i] or 0.0
            for hv in self.havuzlar:
                if hv.durum != "acik" or hv.bar >= i:
                    continue
                if hv.yon > 0 and s.h[i] > hv.seviye:
                    if s.c[i] > hv.seviye:
                        hv.durum, hv.durum_bar = "run", i
                    elif s.h[i] - hv.seviye >= p["asim_atr"] * a:
                        hv.durum, hv.durum_bar = "sweep", i
                        self.sweepler.append((i, hv.ad, hv.seviye, +1))
                elif hv.yon < 0 and s.l[i] < hv.seviye:
                    if s.c[i] < hv.seviye:
                        hv.durum, hv.durum_bar = "run", i
                    elif hv.seviye - s.l[i] >= p["asim_atr"] * a:
                        hv.durum, hv.durum_bar = "sweep", i
                        self.sweepler.append((i, hv.ad, hv.seviye, -1))

            # 3) FVG / OB durumları (bu barın fiyatıyla)
            for f in self.fvgler:
                if f.durum in ("dolu", "ters") or f.bar >= i:
                    continue
                if f.yon > 0:
                    if s.c[i] < f.alt:
                        f.durum, f.ters_bar = "ters", i
                        f.dolu_bar = f.dolu_bar if f.dolu_bar is not None else i
                    elif s.l[i] <= f.alt:
                        f.durum, f.dolu_bar = "dolu", i
                    elif s.l[i] <= f.ce and f.durum == "taze":
                        f.durum, f.ce_bar = "ce", i
                else:
                    if s.c[i] > f.ust:
                        f.durum, f.ters_bar = "ters", i
                        f.dolu_bar = f.dolu_bar if f.dolu_bar is not None else i
                    elif s.h[i] >= f.ust:
                        f.durum, f.dolu_bar = "dolu", i
                    elif s.h[i] >= f.ce and f.durum == "taze":
                        f.durum, f.ce_bar = "ce", i
            for ob in self.oblar:
                if not ob.canli or ob.olay_bar >= i:
                    continue
                if ob.yon > 0:
                    if s.c[i] < ob.alt:
                        ob.canli, ob.bitis_bar = False, i
                    elif s.l[i] <= ob.ust and ob.taze:
                        ob.taze, ob.taze_bar = False, i
                else:
                    if s.c[i] > ob.ust:
                        ob.canli, ob.bitis_bar = False, i
                    elif s.h[i] >= ob.alt and ob.taze:
                        ob.taze, ob.taze_bar = False, i

            # 4) Yeni FVG (üç bar; orta bar displacement)
            if i >= 2 and a > 0 and self.displacement(i - 1):
                if s.l[i] > s.h[i - 2] and s.l[i] - s.h[i - 2] >= p["fvg_atr"] * a:
                    self.fvgler.append(FVG(i, +1, s.h[i - 2], s.l[i], (s.h[i - 2] + s.l[i]) / 2))
                elif s.h[i] < s.l[i - 2] and s.l[i - 2] - s.h[i] >= p["fvg_atr"] * a:
                    self.fvgler.append(FVG(i, -1, s.h[i], s.l[i - 2], (s.h[i] + s.l[i - 2]) / 2))

            # 5) Pivot onayı → almaşmalı swing dizisi + swing havuzları + eşit tepe/dip
            yeni: list[Swing] = []
            if i in self._ph_set:
                yeni.append(Swing(self._ph_set[i], i, s.h[self._ph_set[i]], "H"))
            if i in self._pl_set:
                yeni.append(Swing(self._pl_set[i], i, s.l[self._pl_set[i]], "L"))
            for sw in yeni:
                self._swing_ekle(sw, a)

            # 6) Yapı: başlangıç / BOS / CHoCH / MSS (gövde kapanışıyla)
            if trend == 0 and len(self.swingler) >= 3:
                s1, s2 = self.swingler[-2], self.swingler[-1]
                if s1.tur == "L" and s2.tur == "H":
                    trend, pH, pL = +1, s2, s1
                elif s1.tur == "H" and s2.tur == "L":
                    trend, pH, pL = -1, s1, s2
                if trend != 0:
                    ar_L, ar_H, bacak_bas = pL.fiyat, pH.fiyat, min(pL.bar, pH.bar)
            elif trend != 0 and pH is not None and pL is not None:
                # Kırılım yalnız ONAYLI bir swing'e karşı sorulur: koşan uç
                # (henüz onaysız tepe/dip) kırılamaz — aksi hâlde trend içinde
                # her yeni kapanış bir BOS sayılır (ölçüldü: 823 → sahte).
                if trend > 0:
                    if pH.onay != pH.bar and s.c[i] > pH.fiyat:
                        self._olay(i, "BOS", +1, pH)
                        yeni_L = self._son_swing("L")
                        if yeni_L is not None and yeni_L.bar > pH.bar:
                            pL = yeni_L
                        ar_L, bacak_bas = pL.fiyat, pL.bar
                        pH = Swing(i, i, s.h[i], "H")   # koşan tepe; onaylı swing gelince sabitlenir
                    elif s.c[i] < pL.fiyat:
                        self._olay(i, "CHOCH", -1, pL)
                        trend = -1
                        yeni_H = self._son_swing("H")
                        if yeni_H is not None and yeni_H.bar > pL.bar:
                            pH = yeni_H
                        pL = Swing(i, i, s.l[i], "L")
                        ar_H, ar_L, bacak_bas = pH.fiyat, s.l[i], pH.bar
                else:
                    if pL.onay != pL.bar and s.c[i] < pL.fiyat:
                        self._olay(i, "BOS", -1, pL)
                        yeni_H = self._son_swing("H")
                        if yeni_H is not None and yeni_H.bar > pL.bar:
                            pH = yeni_H
                        ar_H, bacak_bas = pH.fiyat, pH.bar
                        pL = Swing(i, i, s.l[i], "L")
                    elif s.c[i] > pH.fiyat:
                        self._olay(i, "CHOCH", +1, pH)
                        trend = +1
                        yeni_L = self._son_swing("L")
                        if yeni_L is not None and yeni_L.bar > pH.bar:
                            pL = yeni_L
                        pH = Swing(i, i, s.h[i], "H")
                        ar_L, ar_H, bacak_bas = pL.fiyat, s.h[i], pL.bar
                # Koşan uç: kırılımdan sonra onaylanan, kırılım barından SONRAKİ
                # ilk swing korunan ucu sabitler; ona kadar uç koşan max/min'dir.
                if trend > 0:
                    if pH.onay == pH.bar:
                        if s.h[i] > pH.fiyat:
                            pH = Swing(i, i, s.h[i], "H")
                        son_H = self._son_swing("H")
                        if son_H is not None and son_H.onay == i and son_H.bar >= bacak_bas:
                            pH = son_H
                    # korunan dip: kırılım bacağının dibi (onaylı HL); bacak
                    # ilerlerken daha yüksek bir HL onaylanırsa o alınır
                    son_L = self._son_swing("L")
                    if son_L is not None and son_L.onay == i and son_L.bar > pL.bar and son_L.fiyat > pL.fiyat and son_L.bar >= bacak_bas:
                        pL = son_L
                        ar_L = pL.fiyat
                    ar_H = max(ar_H if ar_H is not None else s.h[i], pH.fiyat)
                else:
                    if pL.onay == pL.bar:
                        if s.l[i] < pL.fiyat:
                            pL = Swing(i, i, s.l[i], "L")
                        son_L = self._son_swing("L")
                        if son_L is not None and son_L.onay == i and son_L.bar >= bacak_bas:
                            pL = son_L
                    son_H = self._son_swing("H")
                    if son_H is not None and son_H.onay == i and son_H.bar > pH.bar and son_H.fiyat < pH.fiyat and son_H.bar >= bacak_bas:
                        pH = son_H
                        ar_H = pH.fiyat
                    ar_L = min(ar_L if ar_L is not None else s.l[i], pL.fiyat)

            self.trend[i] = trend
            self.pH[i] = pH.fiyat if pH else None
            self.pL[i] = pL.fiyat if pL else None
            if ar_L is not None and ar_H is not None and ar_H > ar_L:
                self.aralik[i] = (ar_L, ar_H)
                self.konum[i] = 100.0 * (s.c[i] - ar_L) / (ar_H - ar_L)

            # 7) Harmonik: yeni onaylı pivot → PRZ adayları; açık PRZ'lerin durumu
            if yeni:
                self._harmonik_tara(i)
            self._prz_guncelle(i)

    # ── swing dizisi ─────────────────────────────────────────────────────────
    def _swing_ekle(self, sw: Swing, a: float) -> None:
        """Almaşma (kullanıcı Pine'ı 60–86): aynı türden ardışık ikinci swing
        yalnız daha uçtaysa öncekini GÜNCELLER, değilse atılır."""
        p = self.p
        if self.swingler and self.swingler[-1].tur == sw.tur:
            son = self.swingler[-1]
            if (sw.tur == "H" and sw.fiyat > son.fiyat) or (sw.tur == "L" and sw.fiyat < son.fiyat):
                self.swingler[-1] = sw
            else:
                return
        else:
            self.swingler.append(sw)
        # swing havuzu
        self.havuzlar.append(Havuz("SWH" if sw.tur == "H" else "SWL", sw.fiyat, +1 if sw.tur == "H" else -1, sw.onay))
        # eşit tepe/dip: aynı türden önceki onaylı swing'lerle fark ≤ esit_atr × ATR
        if a > 0:
            for once in self.swingler[-6:-1]:
                if once.tur == sw.tur and abs(once.fiyat - sw.fiyat) <= p["esit_atr"] * a:
                    sev = max(once.fiyat, sw.fiyat) if sw.tur == "H" else min(once.fiyat, sw.fiyat)
                    self.havuzlar.append(Havuz("EQH" if sw.tur == "H" else "EQL", sev, +1 if sw.tur == "H" else -1, sw.onay))
                    break

    def _kapat_havuz(self, *adlar: str) -> None:
        """Dönem yenilenince önceki dönemin açık PDH/PDL (PWH/PWL) havuzu
        listeden düşmez, ama artık 'önceki gün' değildir: adı arşivlenir."""
        for hv in self.havuzlar:
            if hv.ad in adlar and hv.durum == "acik":
                hv.durum, hv.durum_bar = "eski", None

    # ── yapı olayı + OB ──────────────────────────────────────────────────────
    def _olay(self, i: int, tur: str, yon: int, kirilan: Swing) -> Olay:
        p, s = self.p, self.s
        # kırılım bacağı: kırılan swing'in karşı ucundan (son ters swing) i'ye
        bas = kirilan.bar
        ters = self._son_swing("L" if yon > 0 else "H")
        if ters is not None and ters.bar > bas:
            bas = ters.bar
        disp = any(self.displacement(j) and ((s.c[j] > s.o[j]) if yon > 0 else (s.c[j] < s.o[j]))
                   for j in range(max(bas, i - int(p["sweep_pencere"])), i + 1))
        pencere = range(max(0, i - int(p["sweep_pencere"])), i)
        sweep_once = any(sw_bar in pencere and sw_yon == -yon for sw_bar, _, _, sw_yon in self.sweepler)
        if tur == "CHOCH" and disp and sweep_once:
            tur = "MSS"
        ol = Olay(i, tur, yon, kirilan.fiyat, kirilan.bar, disp, sweep_once)
        self.olaylar.append(ol)
        # OB: bacakta displacement'tan önceki son zıt renkli mum
        ob_bar = None
        for j in range(i, bas, -1):
            zit = (s.c[j] < s.o[j]) if yon > 0 else (s.c[j] > s.o[j])
            if zit:
                ob_bar = j
                break
        if ob_bar is not None:
            alt, ust = min(s.o[ob_bar], s.c[ob_bar]), max(s.o[ob_bar], s.c[ob_bar])
            self.oblar.append(OB(ob_bar, i, yon, alt, ust, (alt + ust) / 2, s.l[ob_bar] if yon > 0 else s.h[ob_bar]))
        return ol

    # ── harmonik tarayıcı ────────────────────────────────────────────────────
    def _harmonik_tara(self, i: int) -> None:
        """Son onaylı pivot C ise (X, A, B, C almaşmalı dört swing) kalıp
        bantlarını sorar ve PRZ'yi kurar. PRZ, C onaylandığı bar bilinir."""
        sw = self.swingler
        if len(sw) < 4 or sw[-1].onay != i:
            return
        X, A, B, C = sw[-4], sw[-3], sw[-2], sw[-1]
        if not (X.tur == B.tur and A.tur == C.tur and X.tur != A.tur):
            return
        yon = +1 if X.tur == "L" else -1        # boğa: X dip, A tepe, B dip, C tepe, D dip
        xa = abs(A.fiyat - X.fiyat)
        ab = abs(A.fiyat - B.fiyat)
        bc = abs(C.fiyat - B.fiyat)
        if xa <= 0 or ab <= 0 or bc <= 0:
            return
        rB = ab / xa
        rC = bc / ab
        c_asti = (C.fiyat > A.fiyat) if yon > 0 else (C.fiyat < A.fiyat)
        adaylar: list[PRZ] = []

        def d_fiyat(kat_xa: float) -> float:
            return A.fiyat - yon * kat_xa * xa

        # Klasik aile: C, A'yı aşmaz ve 0,382–0,886 AB. PRZ üç SAYIDAN kurulur
        # (ders 3.3): D_XA kalıbın ideal oranı; D_BC katsayısı C'nin derinliğinden
        # (ders 1.4 reciprocal tablosu) ve kalıbın BC bandına kırpılır; AB=CD katı
        # {1 · 1,27 · 1,618} içinden D_XA'ya en yakını. Üç sayının yayılımı
        # `prz_azami_xa`×XA'yı aşarsa küme yok, PRZ yok. Bant uçlarından değil
        # ideal sayılardan kurulur: bant uçları bölgeyi şişirir ve Gartley'in
        # B bandını paylaşan Crab'i aynı C'de sahte aday yapar (ölçüldü).
        if not c_asti and 0.382 <= rC <= 0.886:
            r_bc_tablo = 2.24 if rC < 0.5 else 2.0 if rC < 0.618 else 1.618 if rC < 0.786 else 1.27 if rC < 0.886 else 1.13
            for ad, (b0, b1, d0, d1, bc0, bc1, stop_kat, hedef) in HARMONIK.items():
                if not (b0 <= rB <= b1):
                    continue
                ideal = IDEAL_D[ad]
                d_xa = d_fiyat(ideal)
                r_bc = min(max(r_bc_tablo if ad != "Gartley" else (1.27 if rC >= 0.786 else 1.618), bc0), bc1)
                d_bc = C.fiyat - yon * r_bc * bc
                d_abcd = min((C.fiyat - yon * kk * ab for kk in (1.0, 1.27, 1.618)), key=lambda d: abs(d - d_xa))
                sayilar = [d_xa, d_bc, d_abcd]
                lo, hi = min(sayilar), max(sayilar)
                if hi - lo > self.p["prz_azami_xa"] * xa:
                    continue
                stop = d_fiyat(stop_kat)
                d_ref = hi if yon > 0 else lo          # A'ya yakın kenar (temkinli giriş)
                t1 = d_ref + yon * hedef[0] * abs(A.fiyat - d_ref)
                t2 = d_ref + yon * hedef[1] * abs(A.fiyat - d_ref)
                adaylar.append(PRZ(ad, yon, X.bar, A.bar, B.bar, C.bar, i, lo, hi, stop, t1, t2))
        # Cypher: C, A'yı 1,272–1,414 XA aşar; D = 0,786 XC
        if c_asti and CYPHER["B"][0] <= rB <= CYPHER["B"][1]:
            xc = abs(C.fiyat - X.fiyat)
            r_xc = xc / xa
            if CYPHER["C_xa"][0] <= r_xc <= CYPHER["C_xa"][1]:
                d_xc = C.fiyat - yon * CYPHER["D_xc"] * xc
                d_abcd = min((C.fiyat - yon * kk * ab for kk in (1.0, 1.27, 1.618)), key=lambda d: abs(d - d_xc))
                lo, hi = min(d_xc, d_abcd), max(d_xc, d_abcd)
                if hi - lo > self.p["prz_azami_xa"] * xa:
                    lo, hi = d_xc, d_xc
                stop = X.fiyat
                d_ref = hi if yon > 0 else lo
                t1 = d_ref + yon * 0.382 * abs(C.fiyat - d_ref)
                t2 = d_ref + yon * 0.618 * abs(C.fiyat - d_ref)
                adaylar.append(PRZ("Cypher", yon, X.bar, A.bar, B.bar, C.bar, i, lo, hi, stop, t1, t2))
        # Shark (0-X-A-B-C): son üç swing 0=X̄, X=A, A=B; B X'i aşar, C = 0,886–1,13·0X
        if len(sw) >= 4:
            O_, Xs, As, Bs = sw[-4], sw[-3], sw[-2], sw[-1]
            yon_s = +1 if O_.tur == "L" else -1     # boğa Shark: 0 dip, X tepe, A dip, B tepe (X'i aşar), C dip
            ox = abs(Xs.fiyat - O_.fiyat)
            xa_s = abs(As.fiyat - Xs.fiyat)
            ab_s = abs(Bs.fiyat - As.fiyat)
            if ox > 0 and xa_s > 0 and ab_s > 0 and SHARK["B_xa"][0] <= ab_s / xa_s <= SHARK["B_xa"][1]:
                b_asti = (Bs.fiyat > Xs.fiyat) if yon_s > 0 else (Bs.fiyat < Xs.fiyat)
                if b_asti:
                    c0 = [Bs.fiyat - yon_s * r * ab_s for r in SHARK["C_ab"]]
                    c1 = [Xs.fiyat - yon_s * r * ox for r in SHARK["C_0x"]]
                    lo, hi = max(min(c0), min(c1)), min(max(c0), max(c1))
                    if lo < hi:
                        stop = Xs.fiyat - yon_s * SHARK["stop_0x"] * ox
                        d_ref = hi if yon_s > 0 else lo
                        t1 = d_ref + yon_s * 0.382 * abs(Bs.fiyat - d_ref)
                        t2 = d_ref + yon_s * 0.618 * abs(Bs.fiyat - d_ref)
                        adaylar.append(PRZ("Shark", yon_s, O_.bar, Xs.bar, As.bar, Bs.bar, i, lo, hi, stop, t1, t2))
        for pz in adaylar:
            # aynı C için bir kalıp bir kez
            if any(q.ad == pz.ad and q.c == pz.c for q in self.przler):
                continue
            self.przler.append(pz)

    def _prz_guncelle(self, i: int) -> None:
        s = self.s
        for pz in self.przler:
            if pz.durum in ("teyit", "gecersiz", "kacti") or pz.cizim_bar >= i:
                continue
            if pz.durum == "bekliyor":
                # geçersizlik: kapanış stopun ötesinde (PRZ'ye hiç uğramadan da olabilir)
                if (pz.yon > 0 and s.c[i] < pz.stop) or (pz.yon < 0 and s.c[i] > pz.stop):
                    pz.durum, pz.durum_bar = "gecersiz", i
                    continue
                girdi = (s.l[i] <= pz.ust) if pz.yon > 0 else (s.h[i] >= pz.alt)
                if girdi:
                    pz.durum, pz.tamam_bar = "tamam", i
                    # tamamlandığı barda dönüş mumu da olabilir
                    if self._donus_mumu(i, pz.yon):
                        pz.durum, pz.durum_bar = "teyit", i
                    continue
                # kaçtı: PRZ, çizildiği bardan sonra XC süresinin iki katı içinde
                # (en az 20 bar) dokunulmadı — ders 13'ün tamamlanma penceresi.
                # (T1'in üstünde olmak kaçış DEĞİL: fiyat C'den D'ye inerken
                # T1'in üstündedir; ilk yazım bunu kaçış sayıp her PRZ'yi bir
                # bar sonra kapatıyordu.)
                if i - pz.cizim_bar > max(20, 2 * (pz.c - pz.x)):
                    pz.durum, pz.durum_bar = "kacti", i
            elif pz.durum == "tamam":
                if (pz.yon > 0 and s.c[i] < pz.stop) or (pz.yon < 0 and s.c[i] > pz.stop):
                    pz.durum, pz.durum_bar = "gecersiz", i
                elif self._donus_mumu(i, pz.yon):
                    pz.durum, pz.durum_bar = "teyit", i
                elif i - pz.tamam_bar > 12:
                    pz.durum, pz.durum_bar = "kacti", i    # 12 barda teyit gelmedi (ders: zaman penceresi)

    def _donus_mumu(self, i: int, yon: int) -> bool:
        """Ders 6.1 teyit: PRZ içinde/sonrasında yön lehine gövdeli kapanış —
        kapanış önceki barın kapanışını ve kendi açılışını yön lehine geçer,
        gövde/menzil ≥ 0,5."""
        s = self.s
        m = s.h[i] - s.l[i]
        if m <= 0 or i == 0:
            return False
        if yon > 0:
            return s.c[i] > s.o[i] and s.c[i] > s.c[i - 1] and (s.c[i] - s.o[i]) / m >= 0.5
        return s.c[i] < s.o[i] and s.c[i] < s.c[i - 1] and (s.o[i] - s.c[i]) / m >= 0.5

    # ── okuma: bir barda ekranda ne var ──────────────────────────────────────
    def durum(self, i: int) -> dict:
        """Kapanmış `i` barında fiyat panelinin ilan ettiği durum (parite kapısı
        ve kutu bunu okur)."""
        ar = self.aralik[i]
        acik_fvg = [f for f in self.fvgler if f.acik(i)]
        acik_ob = [o for o in self.oblar if o.acik(i)]
        son_olay = next((o for o in reversed(self.olaylar) if o.bar <= i), None)
        prz = [z for z in self.przler if z.cizim_bar <= i and (z.durum_bar is None or z.durum_bar > i)]
        return {
            "trend": self.trend[i], "pH": self.pH[i], "pL": self.pL[i],
            "aralik": ar, "konum": None if self.konum[i] is None else round(self.konum[i], 1),
            "bolge": None if self.konum[i] is None else ("discount" if self.konum[i] < 50 else "premium"),
            "son_olay": None if son_olay is None else (son_olay.tur, son_olay.yon, son_olay.bar),
            "acik_fvg": len(acik_fvg), "acik_ob": len(acik_ob), "taze_ob": sum(o.taze_mi(i) for o in acik_ob),
            "acik_prz": [z.ad for z in prz],
        }


# ═══════════════════════════════════════════════════════════════════════════
#  Momentum paneli — RSI, diverjans (kullanıcı kuralı), itki, göreli sıra
# ═══════════════════════════════════════════════════════════════════════════
def bb_dilim(bb: float) -> int:
    return 1 if bb < -1.0 else 2 if bb < -0.5 else 3 if bb < 0.0 else 4 if bb < 0.5 else 5 if bb < 1.0 else 6


def rsi_dilim(r: float) -> int:
    return 1 if r < 30 else 2 if r < 40 else 3 if r < 50 else 4 if r < 60 else 5 if r < 70 else 6


@dataclass
class Diverjans:
    bar: int            # onay barı (ikinci pivotun onayı)
    pivot: int          # ikinci pivot barı
    tip: int            # 1 RegBull 2 RegBear 3 HidBull 4 HidBear
    bb: int
    rsi: int
    trend: int          # 1 Up 2 Down
    tablo: int | None   # eşleşen satır (0–24) ya da None
    sl_atr: float | None
    tp_atr: float | None


class Momentum:
    def __init__(self, s: Seri, sabit: dict | None = None):
        self.s = s
        self.p = dict(SABIT, **(sabit or {}))
        n = len(s)
        self.rsi = rsi(s.c, int(self.p["rsi_n"]))
        self.ema = ema(s.c, int(self.p["ema_n"]))
        self.atr = atr(s, int(self.p["atr_n"]))
        basis = sma(s.c, int(self.p["bb_n"]))
        sd = stdev(s.c, int(self.p["bb_n"]))
        self.bb_pos: list[float | None] = [None] * n
        for i in range(n):
            if basis[i] is None or sd[i] is None:
                continue
            yarim = self.p["bb_k"] * sd[i]
            self.bb_pos[i] = 0.0 if yarim <= 0 else (s.c[i] - basis[i]) / yarim
        # itki: gövde/ATR ve göreli sırası
        self.itki: list[float | None] = [None if self.atr[i] in (None, 0) else abs(s.c[i] - s.o[i]) / self.atr[i] for i in range(n)]
        self.itki_sira: list[float | None] = [percentrank(self.itki, i, int(self.p["tarihce"])) for i in range(n)]
        self.rsi_sira: list[float | None] = [percentrank(self.rsi, i, int(self.p["tarihce"])) for i in range(n)]
        self.diverjanslar: list[Diverjans] = []
        self._diverjans()

    def _diverjans(self) -> None:
        """Kullanıcı Pine'ı 165–242: HAM pivotlar (k_ic), ardışık pivot çifti,
        fiyat ve RSI pivot barında; BB dilimi, RSI dilimi, trend ONAY barında."""
        s, p = self.s, self.p
        k = int(p["k_ic"])
        ph, pl = pivotlar(s, k)
        for liste, dip in ((pl, True), (ph, False)):
            onceki = None
            for j in liste:
                i = j + k
                if self.rsi[j] is None:
                    onceki = j
                    continue
                if onceki is not None and self.rsi[onceki] is not None:
                    f0, f1 = (s.l[onceki], s.l[j]) if dip else (s.h[onceki], s.h[j])
                    r0, r1 = self.rsi[onceki], self.rsi[j]
                    tip = None
                    if dip:
                        if f1 < f0 and r1 > r0:
                            tip = 1
                        elif f1 > f0 and r1 < r0:
                            tip = 3
                    else:
                        if f1 > f0 and r1 < r0:
                            tip = 2
                        elif f1 < f0 and r1 > r0:
                            tip = 4
                    if tip is not None and self.bb_pos[i] is not None and self.rsi[i] is not None and self.ema[i] is not None:
                        bb, rs = bb_dilim(self.bb_pos[i]), rsi_dilim(self.rsi[i])
                        tr = 1 if s.c[i] > self.ema[i] else 2
                        satir = next((n for n, (dt, cb, cr, ct, *_r) in enumerate(DIV_TABLO)
                                      if dt == tip and cb == bb and cr == rs and (ct == 0 or ct == tr)), None)
                        sl = DIV_TABLO[satir][4] if satir is not None else None
                        tp = DIV_TABLO[satir][5] if satir is not None else None
                        self.diverjanslar.append(Diverjans(i, j, tip, bb, rs, tr, satir, sl, tp))
                onceki = j
        self.diverjanslar.sort(key=lambda d: d.bar)

    def durum(self, i: int) -> dict:
        return {"rsi": None if self.rsi[i] is None else round(self.rsi[i], 2),
                "rsi_sira": self.rsi_sira[i], "itki_sira": self.itki_sira[i],
                "bb": None if self.bb_pos[i] is None else round(self.bb_pos[i], 3)}


# ═══════════════════════════════════════════════════════════════════════════
#  Kapı: geleceğe bakma sınaması
# ═══════════════════════════════════════════════════════════════════════════
def gelecege_bakma_sinamasi(s: Seri, bas: int = 400, adim: int = 1, azami: int | None = None) -> list[str]:
    """Seriyi i'de kırp; i'deki bütün ilanlar (yapı durumu, havuz sayısı,
    FVG/OB/PRZ listeleri, momentum) BİREBİR aynı kalmalı. Adım her bar."""
    hata: list[str] = []
    tam = Yapi(s)
    mo_tam = Momentum(s)
    son = len(s) if azami is None else min(len(s), bas + azami)
    for i in range(bas, son, adim):
        k = s.kirp(i + 1)
        y = Yapi(k)
        if tam.durum(i) != y.durum(i):
            hata.append(f"yapı i={i}: tam {tam.durum(i)} ≠ kırpık {y.durum(i)}")
        if mo_tam.durum(i) != Momentum(k).durum(i):
            hata.append(f"momentum i={i}")
        if len(hata) > 5:
            break
    return hata


if __name__ == "__main__":
    import veri
    ad = sys.argv[1] if len(sys.argv) > 1 else "eurusd-1h"
    s = veri.oku(ad)
    y = Yapi(s)
    m = Momentum(s)
    print(f"{ad}: {len(s)} bar · swing {len(y.swingler)} · olay {len(y.olaylar)} "
          f"(BOS {sum(o.tur=='BOS' for o in y.olaylar)} · CHoCH {sum(o.tur=='CHOCH' for o in y.olaylar)} · MSS {sum(o.tur=='MSS' for o in y.olaylar)}) "
          f"· FVG {len(y.fvgler)} · OB {len(y.oblar)} · havuz {len(y.havuzlar)} · sweep {len(y.sweepler)} · PRZ {len(y.przler)} · div {len(m.diverjanslar)}")
    print(y.durum(len(s) - 1))
