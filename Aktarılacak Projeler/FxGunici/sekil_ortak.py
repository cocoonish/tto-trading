#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX GÜN İÇİ STRATEJİLER — figürlerin ortak yardımcıları (renkler, biçim, yazım).

Figürler `sekil.py`dedir; sayılar `cikti/ders/olcum.json`dan gelir. Başlık sarma, telefon
genişliği denetimi ve yazım sözleşmesi makro dersinin modülünden (`MakroKurFaiz/sekil_ortak.py`)
alındı; ölçüler orada sayfada sınanmıştı.

Ders yayımlandığı günün metnidir; figürler de o günün ölçümünü dondurur ve
statik yola yazılır (`site/public/arastirma/fx-gunici/`). Her figür
kendi tarih aralığını kendi alt başlığında taşır. Her HTML, çizildiği ölçüm
dosyasının sha256 özünü bir meta etiketinde taşır (`tto-olcum-ozu`);
ölçüm dosyası değişip figür yeniden çizilmezse doğrulayıcı düşer.

"""
from __future__ import annotations

import hashlib
import html as _html
import json
import math
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
OLCUM = BURASI / "cikti" / "ders" / "olcum.json"

try:                                   # çizim kütüphanesi çizim yolunun bağımlılığıdır
    import plotly.graph_objects as go  # (kapı yolu `dogrula.py` onu istemez)
    from plotly.subplots import make_subplots
except ImportError:                    # pragma: no cover
    go = None

SLUG = "fx-gunici"
CIKTI = KOK / "site" / "public" / "arastirma" / SLUG
PLOTLY_JS = "/js/plotly-4.0.0.min.js"
MUREKKEP, CLARET, MAVI, GRI, TURUNCU, YESIL = "#1a1a1a", "#8c2f39", "#2f5d8c", "#8a8a8a", "#b8860b", "#3a7d44"
ACIK_MAVI, ACIK_CLARET = "rgba(47,93,140,0.16)", "rgba(140,47,57,0.14)"


def vir(x: float, b: int = 2) -> str:
    """Site sözleşmesi: ondalık virgül, eksi U+2212, binlik nokta."""
    s = f"{x:,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return s.replace("-", "−")


def yuzde(x: float, b: int = 2, arti: bool = False) -> str:
    """Yüzde işareti önde; işaret yüzdeden de önce: −%0,86 · +%1,78."""
    isaret = "−" if x < 0 else ("+" if arti and x > 0 else "")
    return f"{isaret}%{vir(abs(x), b)}"


def tarih(gun: str) -> str:
    y, a, g = gun[:10].split("-")
    return f"{g}.{a}.{y}"


def ay(gun: str) -> str:
    y, a, _ = gun[:10].split("-")
    return f"{a}.{y}"


# ─────────────────────────────────────────────────────── başlık bloğu: sarma ve üst boşluk
# Plotly başlığı SARMAZ, taşırır: satırın sağ ucu çizim alanının dışında kalır ve dar ekranda okura
# hiç ulaşmaz. Satırlar bu yüzden çizim katmanında sözcük sınırında sarılır. Ölçü karakter sayısı
# değil yazının GENİŞLİĞİDİR: rakamlı satır harfli satırdan geniştir ve aynı karakter sayısında biri
# sığıp öbürü taşar. Genişlik tablosu Arial/Helvetica ilerleme genişlikleridir (ev stilinin yazısı;
# Linux'taki karşılığı Liberation Sans aynı ölçüyü taşır) ve ekran görüntüsünde satır satır sınandı:
# tahmin ile çizilen genişlik %0,5 içinde.
# Sınırın ölçüsü SAYFADAKİ genişliktir, figür dosyasının kendi penceresi değil: okur figürü ders
# sayfasındaki gömme çerçevesinde görür ve 390 piksellik telefonda çerçeve (16 px kenar boşluğu,
# kenarlık) 353 piksel genişliğindedir (geniş gömme 356; derlenmiş sayfada ölçüldü). Figür dosyası
# tek başına 390 pikselde açılınca sığan bir satır sayfada sağdan kırpılır: 390'a göre kurulmuş
# 35,5 em'lik alt başlık satırı 377 piksele uzanıyor ve çerçevede son 20–25 pikseli görünmüyordu.
# Başlık x'i genişliğin %1'i (≈ 4 px). Sınır: başlık (15 px) 22,8 em ≈ 342 px, alt başlık (<sub>,
# 15 px'in %70'i) 32,6 em ≈ 342 px; sağ uç ≈ 346 px, çerçevenin 7 piksel içinde (ölçüm hatası ~2 px).
BASLIK_EM, ALT_EM = 22.8, 32.6
_TAVAN_PX, _BASLIK_PX, _ALT_PX = 351, 15.0, 10.5      # taşma denetimi: 353 px'lik çerçevede çizilebilen sağ uç
_GENISLIK = {
    " ": 278, "\u00a0": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191, "(": 333,
    ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278, ":": 278, ";": 278, "<": 584,
    "=": 584, ">": 584, "?": 556, "@": 1015, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556, "|": 260,
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778, "H": 722, "I": 278, "J": 500,
    "K": 667, "L": 556, "M": 833, "N": 722, "O": 778, "P": 667, "Q": 778, "R": 722, "S": 667, "T": 611,
    "U": 722, "V": 667, "W": 944, "X": 667, "Y": 667, "Z": 611,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556, "h": 556, "i": 222, "j": 222,
    "k": 500, "l": 222, "m": 833, "n": 556, "o": 556, "p": 556, "q": 556, "r": 333, "s": 500, "t": 278,
    "u": 556, "v": 500, "w": 722, "x": 500, "y": 500, "z": 500,
    "ç": 500, "ğ": 556, "ı": 278, "ö": 556, "ş": 500, "ü": 556, "â": 556, "î": 278, "é": 556,
    "Ç": 722, "Ğ": 778, "İ": 278, "Ö": 778, "Ş": 667, "Ü": 722,
    "–": 556, "—": 1000, "·": 278, "−": 584, "×": 584, "→": 1000, "≥": 549, "≤": 549, "≈": 549, "±": 584,
    "…": 1000, "’": 222, "‘": 222, "“": 333, "”": 333, "²": 333, "°": 400, "σ": 600, "β": 556, "ρ": 556,
    "π": 556, "α": 556, "Δ": 668, "∞": 713, "↑": 500, "↓": 500,
    **{d: 556 for d in "0123456789"},
}
_TANIMSIZ = 1000                     # tabloda olmayan işaret (○ ● ◆ ◇ …): geniş say, taşma payı kalsın
_CIPLAK_SAYI = re.compile(r"\(?[+−-]?%?\d+(?:[.,]\d+)*")   # "(164 yayım" de bölünmez
_BAGLI_ISARET = ("·", "−", "+", "=", "×", "≥", "≤", "≈", "→")   # satır başına düşmez (sar)


def satir_em(metin: str) -> float:
    """Bir başlık satırının yazı genişliği, em (etiketler sayılmaz, &amp; gibi kaçışlar çözülür)."""
    duz = _html.unescape(re.sub(r"<[^>]+>", "", metin))
    return sum(_GENISLIK.get(c, _TANIMSIZ) for c in duz) / 1000


def _satirla(kelimeler: list[str], en: float) -> list[list[str]]:
    """Sözcükleri en az satıra, satır sonlarını dengeleyerek dağıtır (dinamik programlama). Önce satır
    sayısı en küçüklenir (açgözlü sarmanın verdiği sayı), sonra son satır dışındaki satırların boşluk
    karelerinin toplamı; son satır sınırın dörtte birinden kısaysa cezalanır (dul satır: "CNBC",
    "da taşır)" tek başına kalmaz). Sınırdan uzun tek sözcük kendi satırına düşer."""
    bosluk = _GENISLIK[" "] / 1000
    g = [satir_em(k) for k in kelimeler]
    n = len(kelimeler)
    en_iyi: list[tuple] = [(0, 0.0, -1)] + [(math.inf, math.inf, -1)] * n   # (satır, maliyet, başlangıç)
    for j in range(1, n + 1):
        gen = -bosluk
        for i in range(j - 1, -1, -1):
            gen += bosluk + g[i]
            if gen > en and i < j - 1:
                break
            if en_iyi[i][0] == math.inf:
                continue
            if j == n:
                ceza = 100 * max(0.0, en / 4 - gen) ** 2 if i > 0 else 0.0   # dul satır, ağır ceza
            else:
                ceza = max(0.0, en - gen) ** 2
            aday = (en_iyi[i][0] + 1, en_iyi[i][1] + ceza, i)
            if aday[:2] < en_iyi[j][:2]:
                en_iyi[j] = aday
    satirlar, j = [], n
    while j > 0:
        i = en_iyi[j][2]
        satirlar.insert(0, kelimeler[i:j])
        j = i
    return satirlar or [[]]


def sar(metin: str, en: float) -> list[str]:
    """Metni sözcük sınırında en çok `en` em genişliğinde satırlara böler (`_satirla`). Var olan <br>
    korunur; bölünmez boşluk (U+00A0) bölünmez. Ayraç " · " ve iki yanı boşluklu işlem işaretleri
    (− + = × ≥ ≤ ≈ →) bir önceki sözcüğe bağlanır: satır onlarla BAŞLAMAZ, onlarla biter — satır başındaki
    "− yıllık TÜFE" bir eksi işaretli terim gibi okunur. Çıplak sayı ardından gelen sözcükten ayrılmaz
    ("5 yıl", "164 yayım" satır sonunda bölünmez). Sınırdan uzun tek bir sözcük bölünmez, kendi satırında
    kalır (taşma denetimi `tasan_satirlar` onu adıyla gösterir)."""
    cikti = []
    for isaret in _BAGLI_ISARET:
        metin = metin.replace(f" {isaret} ", f"\u00a0{isaret} ")
    for parca in metin.split("<br>"):
        kelimeler = []
        for k in parca.split(" "):
            if kelimeler and k[:1].isalpha() and _CIPLAK_SAYI.fullmatch(kelimeler[-1].rsplit("\u00a0", 1)[-1]):
                kelimeler[-1] += "\u00a0" + k
            else:
                kelimeler.append(k)
        cikti.extend(" ".join(s) for s in _satirla(kelimeler, en))
    return cikti


def baslik_metni(bas: str, alt: list[str]) -> str:
    """Başlık bloğu: başlık BASLIK_EM'de, alt başlığın her öğesi ALT_EM'de sarılır. Alt başlık
    öğeleri ayrı satırdan başlar (öğe = bir anlam birimi: kaynak, pencere, işaretlerin anlamı)."""
    a = [s for parca in alt for s in sar(parca, ALT_EM)]
    return "<br>".join(sar(bas, BASLIK_EM)) + ("<br><sub>" + "<br>".join(a) + "</sub>" if a else "")


def ust_pay(baslik: str) -> int:
    """Ev stilinin üst boşluğu (site/tools/plotly_stil.py): 92 + <br> başına 26 + panel başlığı 26 piksel.
    Ev stili, en üstte panel başlığı olan figürde bu değeri DAYATIR: daha küçük üst boşluk bu değere
    çıkar, daha büyüğü 92'ye döner. Figür yüksekliği bu yüzden bu payla kurulur: sabit yükseklikte her
    yeni satır çizim alanını 26 piksel ezer."""
    return 92 + 26 * baslik.count("<br>") + 26


def baslik_yeri(baslik: str) -> dict:
    """Başlık bloğu üstten çapalanır ve ev stilinin üst payı içinde ORTALANIR (sekil_b10_surucu ile aynı
    kalıp): pay satır başına 26 piksel büyür, blok satır başına ~19,7 piksel tutar; çapasız çok satırlı
    başlık 7 satırdan sonra ilk panel başlığına biniyordu. 33 piksel: pad 48'de bloğun ölçülen üst
    kenarı; 30 piksel: ilk panelin başlığı."""
    satir = baslik.count("<br>") + 1
    kaydir = max(0.0, (ust_pay(baslik) - 30 - 2 * 33 - 19.7 * satir) / 2)
    return dict(text=baslik, y=1, yref="container", yanchor="top", pad=dict(t=int(48 + kaydir)))


def baslik_koy(fig, bas: str, alt: list[str]) -> str:
    """Sarılmış başlık bloğunu figüre üstten çapalı koyar; metni döndürür (yükseklik ondan kurulur)."""
    baslik = baslik_metni(bas, alt)
    fig.update_layout(title=baslik_yeri(baslik))
    return baslik


def yukseklik(baslik: str, cizim: int) -> int:
    """Figür yüksekliği = ev stilinin üst payı + çizim ve alt pay (başlığın satır sayısından bağımsız)."""
    return ust_pay(baslik) + cizim


def tasan_satirlar(baslik: str) -> list[str]:
    """390 piksellik telefonun gömme çerçevesinde (353 px) sağ ucu çizilemeyen başlık satırları (tahmini genişlikle)."""
    tasan, alt = [], False
    for s in baslik.split("<br>"):
        alt = alt or "<sub>" in s
        px = 4 + satir_em(s) * (_ALT_PX if alt else _BASLIK_PX)
        if px > _TAVAN_PX:
            tasan.append(f"{px:.0f} px: {_html.unescape(re.sub(r'<[^>]+>', '', s))[:60]}")
        alt = alt and "</sub>" not in s
    return tasan


#: Ev stilinin yan payları (site/tools/plotly_stil.py: margin.l = margin.r = 64) ve panel başlığının
#: yazısı (make_subplots'un ek açıklaması, 16 px; ev stili ek açıklamaların yazısına dokunmaz). Eksen
#: etiketi uzunsa ev stilinin `automargin`i sol payı büyütür: panel sağa kayar, sağdaki pay daralır.
_YAN_PX, _PANEL_PX, _TIK_PX, _CERCEVE_PX = 64, 16.0, 11.0, 353


def _sozluk(fig) -> dict:
    """Figürün düzeni ve izleri sözlük olarak: çizim kütüphanesinin nesnesi ya da HTML'den okunmuş JSON (kapı,
    dogrula.py, çizim kütüphanesi olmadan aynı ölçüyü koşturur)."""
    return fig.to_dict() if hasattr(fig, "to_dict") else fig


def _sol_pay(d: dict) -> float:
    """Sol payın tahmini: kategori ekseninin en uzun etiketi (11 px yazı + 12 px tik payı) ya da 64."""
    pay = _YAN_PX
    yazi = (d.get("layout", {}).get("yaxis") or {}).get("ticktext")
    if yazi is not None and len(yazi):           # etiketler elle yazıldıysa eksende görünen odur
        return max(pay, 12 + max(satir_em(v) for v in yazi if v) * _TIK_PX)
    for iz in d.get("data") or []:
        y = iz.get("y")
        if y is None or isinstance(y, (dict, str)):  # ikili kodlanmış sayı dizisi kategori değildir
            continue
        y = [v for v in y if v is not None]           # değeri olmayan iz (boş parite) sayılmaz
        if y and all(isinstance(v, str) for v in y):
            pay = max(pay, 12 + max(satir_em(v) for v in y) * _TIK_PX)
    return pay


def panel_tasmasi(fig) -> list[str]:
    """353 piksellik gömme çerçevesinde panel başlıklarının (make_subplots ek açıklamaları) taşması ve
    yan yana panellerde birbirine binmesi (tahmini genişlikle; ölçüt `tasan_satirlar`ın eşi). `fig`: çizim
    kütüphanesinin figürü ya da {"data", "layout"} sözlüğü."""
    d = _sozluk(fig)
    sol = _sol_pay(d)
    alan = _CERCEVE_PX - sol - _YAN_PX
    bas = []
    for a in d.get("layout", {}).get("annotations") or []:
        if a.get("yref") != "paper" or a.get("yanchor") != "bottom" or not a.get("text"):
            continue
        gen = max(satir_em(s) for s in a["text"].split("<br>")) * _PANEL_PX
        orta = sol + (a.get("x") or 0) * alan
        bas.append((orta - gen / 2, orta + gen / 2, round(a.get("y") or 0, 3), a["text"]))
    sorun = []
    for x0, x1, _, metin in bas:
        if x0 < 0 or x1 > _CERCEVE_PX:
            sorun.append(f"{x0:.0f}–{x1:.0f} px (çerçeve 0–{_CERCEVE_PX}): {_html.unescape(metin)[:60]}")
    for i, (a0, a1, ay, am) in enumerate(bas):
        for b0, b1, by, bm in bas[i + 1:]:
            if ay == by and a0 < b1 and b0 < a1:
                sorun.append(f"üst üste: {_html.unescape(am)[:30]} ↔ {_html.unescape(bm)[:30]}")
    return sorun


def olcum_ozu() -> str:
    return hashlib.sha256(OLCUM.read_bytes()).hexdigest()


#: Bu koşuda yazılan figür dosyaları (ev stili yalnız onlara uygulanır).
YAZILAN: list[Path] = []
#: Ev stilinin dosyaya koyduğu işaret (site/tools/plotly_stil.py: ISARET); kapı figürde onu arar.
EV_STILI_ISARET = "<!-- tto-ev-stili -->"
EV_STILI = KOK / "site" / "tools" / "plotly_stil.py"


def ev_stili(dosyalar: list[Path]) -> int:
    """Sitenin ev stilini (site/tools/plotly_stil.py) çizilen dosyalara uygular. Figürlerin yüksekliği ve başlık yeri
    o stilin üst payıyla kurulur (`ust_pay`): stil uygulanmamış bir figürde çok satırlı başlık çizim alanına biner.
    Stil figürün verisine dokunmaz ve tekrar uygulanabilir."""
    import subprocess
    if not dosyalar:
        return 0
    s = subprocess.run([sys.executable, str(EV_STILI), *map(str, dosyalar)], capture_output=True, text=True)
    eksik = [d.name for d in dosyalar if EV_STILI_ISARET not in d.read_text(encoding="utf-8")]
    if s.returncode != 0 or eksik:
        print(s.stdout[-2000:], s.stderr[-2000:])
        print(f"  ✗ ev stili uygulanamadı: {', '.join(eksik[:5]) or 'araç düştü'}")
        return 1
    print(f"  ✓ ev stili: {len(dosyalar)} figür")
    return 0


def _yaz(fig, ad: str, yukseklik: int = 500) -> None:
    fig.update_layout(
        height=yukseklik, margin=dict(l=64, r=28, t=96, b=78),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Newsreader, Georgia, serif", size=13, color=MUREKKEP),
        title=dict(x=0, xanchor="left", font=dict(size=15)),
        legend=dict(orientation="h", yanchor="top", y=-0.16, x=0),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor="#d8d4cc", ticks="outside")
    fig.update_yaxes(gridcolor="#ececec", zeroline=False)
    CIKTI.mkdir(parents=True, exist_ok=True)
    # div kimliği figürün adından: plotly'nin öntanımlısı rastgele (uuid4) ve her koşu bayt bayt farklı bir dosya
    # yazardı; aynı ölçümden aynı figür birebir aynı dosya olmalı.
    kimlik = "sekil-" + re.sub(r"[^a-z0-9_-]", "-", Path(ad).stem.lower())
    html = fig.to_html(include_plotlyjs=PLOTLY_JS, full_html=True, div_id=kimlik,
                       config={"displayModeBar": False, "responsive": True})
    html = html.replace("<head>", f'<head><meta name="tto-olcum-ozu" content="{olcum_ozu()}">', 1)
    (CIKTI / ad).write_text(html, encoding="utf-8")
    yol = CIKTI / ad
    YAZILAN.append(yol)
    print(f"  ✓ {yol.relative_to(KOK) if yol.is_relative_to(KOK) else yol}")
    for s in tasan_satirlar(fig.layout.title.text or ""):     # uyarı: çizim düşmez, satır adıyla görünür
        print(f"  ! {ad}: başlık satırı telefonun gömme çerçevesinde taşar — {s}")
    for s in panel_tasmasi(fig):
        print(f"  ! {ad}: panel başlığı telefonun gömme çerçevesinde — {s}")
