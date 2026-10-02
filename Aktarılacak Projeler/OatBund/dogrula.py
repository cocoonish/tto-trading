#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND YAZISI (02.10.2026) — yayımlanan metni sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
pandas/numpy/plotly YOK: betik yalnız standart kütüphaneyle çalışır, ağa
çıkmaz, duvar saati okumaz (girdisi depodaki arşiv). Beş soru sorar:

1. ARŞİV — `veri/` altındaki her dosyanın sıkıştırılmamış içeriğinin özü
   künyedekiyle aynı mı; ölçüm dosyası bu özlerle ve BUGÜNKÜ `olcum.py` ile mi
   üretilmiş; figürler bugünkü ölçüm dosyasından mı çizilmiş? Girdi, ölçüm kodu
   ya da ölçüm değişip ardındaki adım koşulmamışsa yazının sayıları gerekçesiz
   kalır.
2. METİN — yazının tablolarındaki ve cümlelerindeki her ölçülmüş sayı
   `veri/olcum.json` ile aynı mı? Beklenen değerler buraya ELLE yazılmaz;
   ölçüm dosyasından okunur, tablolar ayrıştırılıp hücre hücre karşılaştırılır.
   Ön bilgi (açıklama, kart özeti) gövdeden AYRI sınanır: bir ifadenin gövdede
   geçmesi, kartta yanlış yazılmadığını göstermez.
3. ENVANTER — metindeki HER ondalık sayı ya ölçümle sınanmış bir ifadenin ya da
   hücrenin içinde, ya da adıyla yazılmış bir dış kaynak ifadesinin (haber,
   resmî belge) içinde durmalı. Sınanmamış bir sayı yazıya girerse kapı düşer:
   kapsam, bir ifade listesinin tuttuğu kadar değil, metnin kendisi kadardır.
4. BİÇİM — gövdede ASCII tire ile yazılmış eksi sayı ya da arkaya yazılmış
   yüzde işareti yok (eksi U+2212, yüzde önde).
5. FİGÜRLER — dokuz figür yayın dizininde var mı, metin her birini sırayla
   gömüyor mu, figürün içindeki "Şekil NN" başlığı gömmenin numarasıyla aynı
   mı, ve Şekil 02'deki her olayın günü metinde anılıyor mu?

Koşum:  python3 dogrula.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
SLUG = "oat-bund-2026-10-02"
MDX = KOK / "site/src/content/analiz" / f"{SLUG}.mdx"
SEKIL = KOK / "site/public/analiz" / SLUG

hatalar: list[str] = []
sayac = {"hucre": 0, "metin": 0, "arsiv": 0, "dis": 0, "sayi": 0}
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
      "Eylül", "Ekim", "Kasım", "Aralık"]


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 1, arti: bool = False) -> str:
    """Ondalık virgül, binlik nokta, eksi U+2212; sıfıra yuvarlanan değer işaretsiz."""
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if round(x, b) < 0 and float(s.replace(".", "").replace(",", ".")) != 0:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0) else s


def yz(x: float, b: int = 2, arti: bool = False) -> str:
    s = "%" + sayi(abs(x), b)
    sifir = float(sayi(abs(x), b).replace(".", "").replace(",", ".")) == 0
    if round(x, b) < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0 and not sifir) else s


def bp(x: float, b: int = 1, arti: bool = False) -> str:
    return f"{sayi(x, b, arti)} bp"


def gun(iso: str) -> str:
    """'2026-10-01' → '1 Ekim 2026'."""
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]} {iso[:4]}"


def tarih_ga(iso: str) -> str:
    """'2026-01-27' → '27 Ocak' (yılsız)."""
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]}"


def ay_yil(iso: str) -> str:
    return f"{AY[int(iso[5:7])]} {iso[:4]}"


def gun_k(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


# ─────────────────────────────────────────────── metin alanları ve kapsam
def _ek_sil(s: str) -> str:
    """Kesme işaretinden sonraki eki siler: "54,9'dan" → "54,9'". Kapı ekin
    doğruluğunu değil sayının kendisini sorar."""
    return re.sub(r"'[a-zçğıöşüâîû]+", "'", s)


def _norm(s: str) -> str:
    return _ek_sil(re.sub(r"\s+", " ", s.replace("''", "'")))


# Ondalık sayı: "140,9", "3.595,5", "1,1241". Binlik ayraçlı tam sayı ("6.967")
# ve madde numarası ("49.3") ondalık değildir.
ONDALIK = re.compile(r"(?<![\d.,])\d{1,3}(?:\.\d{3})*,\d+|(?<![\d.,])\d+,\d+")


class Alan:
    """Normalize edilmiş bir metin alanı ve hangi karakterlerinin bir ölçütle
    kapsandığı. Kapsam bütün eşleşmeleri işaretler: aynı ifade iki yerde
    geçiyorsa ikisi de sınanmış sayılır (metin aynı)."""

    def __init__(self, ad: str, ham: str) -> None:
        self.ad, self.n = ad, _norm(ham)
        self.kapsam = bytearray(len(self.n))

    def isaretle(self, parca: str) -> bool:
        p = _norm(parca)
        bulundu, i = False, self.n.find(p)
        while i >= 0:
            bulundu = True
            self.kapsam[i:i + len(p)] = b"\x01" * len(p)
            i = self.n.find(p, i + 1)
        return bulundu

    def kapsanmayan(self) -> list[str]:
        out = []
        for x in ONDALIK.finditer(self.n):
            if not all(self.kapsam[x.start():x.end()]):
                out.append(f"{self.ad}: {self.n[max(0, x.start() - 50):x.end() + 25]!r}")
        return out


ALAN: dict[str, Alan] = {}


def metinde(parca: str, ad: str, yer: str = "govde") -> None:
    """Ölçümden kurulmuş bir ifade metinde birebir geçmeli."""
    sayac["metin"] += 1
    if not ALAN[yer].isaretle(parca):
        hatalar.append(f"{yer} · metinde yok ({ad}): {parca!r}")


def dis(parca: str, kaynak: str, yer: str = "govde") -> None:
    """Bir dış kaynağın (haber, resmî belge, ajans notu) sayısı: ölçümle
    sınanamaz ama adıyla bildirilir. İfade metinden kalkarsa kapı düşer —
    liste sessizce çürümez."""
    sayac["dis"] += 1
    if not ALAN[yer].isaretle(parca):
        hatalar.append(f"{yer} · dış kaynak ifadesi metinde yok ({kaynak}): {parca!r}")


def dogru(kosul: bool, mesaj: str) -> None:
    sayac["metin"] += 1
    if not kosul:
        hatalar.append(mesaj)


# ─────────────────────────────────────────────── tablo ayrıştırma
class Tablo(list):
    """Satır listesi; her hücrenin bir ölçütle sınanıp sınanmadığını tutar."""

    def __init__(self, satirlar: list[list[str]]) -> None:
        super().__init__(satirlar)
        self.kapsam = [[False] * len(r) for r in satirlar]


TABLOLAR: list[Tablo] = []


def tablolar(metin: str) -> list[Tablo]:
    out, blok = [], []
    for satir in metin.splitlines():
        s = satir.strip()
        if s.startswith("|") and s.endswith("|"):
            hucre = [h.strip().replace("**", "") for h in s[1:-1].split("|")]
            if not all(set(h) <= set("-: ") for h in hucre):
                blok.append(hucre)
        elif blok:
            out.append(Tablo(blok))
            blok = []
    if blok:
        out.append(Tablo(blok))
    return out


def tablo(*baslik: str) -> Tablo:
    """Başlık satırı verilen hücrelerle başlayan TEK tablo (iki tablo aynı
    önekle başlıyorsa önek ayırt edici değildir — hata)."""
    bulunan = [x for x in TABLOLAR if x and tuple(x[0][:len(baslik)]) == baslik]
    if len(bulunan) != 1:
        hatalar.append(f"tablo bulunamadı ya da tekil değil ({len(bulunan)}): {baslik!r}")
        return Tablo([])
    t = bulunan[0]
    t.kapsam[0] = [True] * len(t[0])           # başlık satırı
    return t


def hucre(t: Tablo, ilk: str, sutun: int, beklenen: str, ad: str) -> None:
    """Etiketi `ilk` olan HER satırın `sutun` hücresi beklenen değer olmalı."""
    sayac["hucre"] += 1
    satirlar = [i for i, r in enumerate(t) if r and r[0] == ilk]
    if not satirlar:
        hatalar.append(f"{ad}: satır yok: {ilk!r}")
        return
    if len(satirlar) > 1:
        hatalar.append(f"{ad}: aynı etiketli {len(satirlar)} satır: {ilk!r}")
    for i in satirlar:
        r = t[i]
        t.kapsam[i][0] = True
        g = r[sutun] if sutun < len(r) else "(yok)"
        if g != beklenen:
            hatalar.append(f"{ad} · '{ilk}' sütun {sutun + 1}: metin {g!r}, ölçüm {beklenen!r}")
        elif sutun < len(r):
            t.kapsam[i][sutun] = True


def dis_hucre(t: Tablo, ilk: str, sutun: int, parca: str, kaynak: str) -> None:
    """Hücredeki bir dış kaynak sayısı (ölçümle sınanamaz, adıyla bildirilir)."""
    sayac["dis"] += 1
    for i, r in enumerate(t):
        if r and r[0] == ilk and sutun < len(r) and parca in r[sutun]:
            t.kapsam[i][sutun] = True
            return
    hatalar.append(f"dış kaynak hücresi yok ({kaynak}): {ilk!r} sütun {sutun + 1}: {parca!r}")


def envanter() -> None:
    """Sınanmamış ondalık sayı kalmasın: ifade alanları ve tablo hücreleri."""
    for a in ALAN.values():
        for k in a.kapsanmayan():
            hatalar.append(f"kapsanmayan sayı · {k}")
        sayac["sayi"] += len(ONDALIK.findall(a.n))
    for t in TABLOLAR:
        for i, r in enumerate(t):
            for j, h in enumerate(r):
                if ONDALIK.search(h):
                    sayac["sayi"] += 1
                    if not t.kapsam[i][j]:
                        hatalar.append(f"kapsanmayan tablo hücresi · {t[0][0]!r} · {r[0]!r} · sütun {j + 1}: {h!r}")


# ─────────────────────────────────────────────── 1 · arşiv
def _oz(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def arsiv() -> dict:
    kunye = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
    for ad, k in kunye["dosyalar"].items():
        sayac["arsiv"] += 1
        yol = VERI / ad
        if not yol.exists():
            hatalar.append(f"arşiv dosyası yok: {ad}")
            continue
        oz = hashlib.sha256(gzip.decompress(yol.read_bytes())).hexdigest()
        if oz != k["sha256"]:
            hatalar.append(f"arşiv özü künyeyle tutmuyor: {ad}")
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    sayac["arsiv"] += 2
    if o["arsiv"] != {ad: k["sha256"] for ad, k in kunye["dosyalar"].items()}:
        hatalar.append("ölçüm dosyası bu arşivle üretilmemiş (özler ayrışıyor) — olcum.py yeniden koşulmalı")
    if o.get("olcum_py_oz") != _oz(BURASI / "olcum.py"):
        hatalar.append("ölçüm dosyası bugünkü olcum.py ile üretilmemiş — olcum.py yeniden koşulmalı")
    return o


def kur_kaynagi(o: dict) -> None:
    """Kur bacaklarının kaynağı: EUR/USD iki indirmede birebir, sentetik GBP/USD
    kaynağın kendi GBP/USD serisinden yalnız yuvarlama kadar ayrık."""
    kk = o["kur_kaynak"]
    dogru(kk["eurusd_azami_fark"] == 0 and kk["eurusd_ortak_gun"] > 6900,
          f"EUR/USD iki indirmede birebir değil: azami fark {kk['eurusd_azami_fark']}")
    dogru(kk["gbp_ozdeslik_medyan_bp"] < 5 and kk["chf_ozdeslik_medyan_bp"] < 5,
          "sentetik GBP/USD ya da CHF kuru kaynağın kendi serisinden yuvarlamanın ötesinde ayrışıyor")
    dogru(kk["veri_gunu_bar"] == o["kur"]["son"], "veri gününün kuru günlük bardan okunmuyor")
    yh = kk["yahoo_eurgbp_gun_medyan_yuzde"]
    dogru(yh["cuma"] > 1.5 * max(v for g, v in yh.items() if g != "cuma"),
          "kaydırılmış seride cuma sapması öbür günlerin belirgin üstünde değil")


# ─────────────────────────────────────────────── 2 · metin
def bolumler(m: str) -> tuple[dict, str]:
    """Ön bilgi alanları ve gövde."""
    _, on, govde = m.split("---", 2)
    alan = {}
    for ad in ("title", "description", "ozet"):
        x = re.search(rf"^{ad}: '((?:[^']|'')*)'$", on, re.M)
        alan[ad] = x.group(1).replace("''", "'") if x else ""
        if not x:
            hatalar.append(f"ön bilgi alanı okunamadı: {ad}")
    return alan, govde


def duz_metin(govde: str) -> str:
    """Envanterin taradığı düz metin: tablolar (hücre hücre sınanır), formüller,
    figür gömmeleri ve rakam şeridi (ayrı sınanır) dışarıda."""
    g = re.sub(r"\$\$.*?\$\$", " ", govde, flags=re.S)
    g = re.sub(r"\$[^$\n]+\$", " ", g)
    g = re.sub(r"`[^`]*`", " ", g)
    g = re.sub(r"<GrafikEmbed[^>]*/>", " ", g)
    g = re.sub(r'<ul class="rakamlar">.*?</ul>', " ", g, flags=re.S)
    return "\n".join(s for s in g.splitlines() if not (s.strip().startswith("|") and s.strip().endswith("|")))


def _cap(o: dict, bas: str, son: str = "2026-10-01") -> dict:
    return next(r for r in o["capraz"] if r["bas"] == bas and r["son"] == son)


def rakamlar(govde: str, o: dict) -> None:
    sv, d = o["seviye"], o["duyarlilik"]["2024–2026"]
    ey, e2c = _cap(o, "2026-08-31"), _cap(o, "2026-09-28")
    e1c = _cap(o, "2026-08-31", "2026-09-28")
    il, ilb = o["ileri"][0], o["ileri"][4]
    beklenen = [
        (bp(sv["spread"]), "OAT–Bund 10 yıllık farkı, 1 Ekim Avrupa kapanışı"),
        (bp(o["hiz"]["10y_22"]["degisim"], 1, True),
         f"son 22 iş günündeki açılma ({ay_yil(o['hiz']['10y_22']['son_gorulme'])}'den beri en hızlı)"),
        (yz(ey["fx"], 2, True), "EUR/USD, 31 Ağustos → 1 Ekim, New York kapanışı (log değişim)"),
        (yz(e2c["eurgbp"], 2, True), f"EUR/GBP, 28 Eylül → 1 Ekim — önceki dört haftada {yz(e1c['eurgbp'], 2, True)} "
                                     "iken son üç günün euroya özgü kaybı"),
        (yz(d["gbpusd"]["b"]["spr"] * 10, 2, True),
         f"EUR/USD'de {yz(d['faiz+fr']['b']['spr'] * 10, 2, True)} iken Fransa farkındaki 10 bp açılmaya eşlik eden "
         "haftalık GBP/USD hareketi, 2024–2026"),
        (yz(il["daha_acildi_payi"], 1),
         "bir ayda 30 bp'den hızlı açılmaların ardından farkın ertesi ay daha da açıldığı gözlemlerin payı "
         f"({il['gozlem']} gözlem, {il['epizot']} küme; bugünkü hızı aşan {ilb['gozlem']} gözlemde hiç yok)"),
    ]
    dogru(ilb["daha_acildi_payi"] == 0, "rakam şeridi: bugünkü hızı aşan gözlemlerde daha açılan var")
    bas = govde.index('<ul class="rakamlar">')
    blok = govde[bas:govde.index("</ul>", bas)]
    yazili = [(b, _norm(s)) for b, s in re.findall(r"<li><b>([^<]+)</b><span>([^<]+)</span></li>", blok)]
    sayac["hucre"] += 2 * len(beklenen)
    if yazili != [(b, _norm(s)) for b, s in beklenen]:
        for i, (y, b) in enumerate(zip(yazili + [None] * 6, beklenen)):
            if y != (b[0], _norm(b[1])):
                hatalar.append(f"rakam şeridi {i + 1}: metin {y!r}, ölçüm {b!r}")
        if len(yazili) != len(beklenen):
            hatalar.append(f"rakam şeridi {len(yazili)} öğe, beklenen {len(beklenen)}")


ZAMAN = {"gun": "gün içi", "aksam": "akşam", "haftasonu": "hafta sonu"}


def tablolar_sina(o: dict) -> None:
    # gün içi saatler
    t = tablo("saat (Paris)")
    gi, p = o["gun_ici"], o["gun_ici_pencere"]
    noktalar = {"09:00": gi["09:00"], "14:15": gi["14:15"], "17:30": gi["17:30"],
                p["bas"]: {"spr": p["spr"]["bas"], "ispr2": p["ispr2"]["bas"], "rd": p["rd"]["bas"],
                           "eurusd": p["eurusd"]["bas"]}}
    for saat, r in noktalar.items():
        hucre(t, saat, 1, bp(r["spr"]), "gün içi")
        hucre(t, saat, 2, bp(r["ispr2"]), "gün içi")
        hucre(t, saat, 3, bp(r["rd"]), "gün içi")
        hucre(t, saat, 4, sayi(r["eurusd"], 4), "gün içi")
    dogru(abs(gi["17:30"]["spr"] - p["spr"]["son"]) < 1e-9, "gün içi pencere sonu 17:30 noktasıyla aynı değil")
    dogru(gi["17:30"]["eurusd"] == o["kur"]["son"], "gün içi 17:30 kuru ile New York kapanışı ayrı (tablo 1,1241 diyor)")
    # bacaklar
    t = tablo("başlangıç")
    etiket = {"2026-02-25": "25 Şubat 2026 (yılın dibi)", "2026-06-30": "30 Haziran 2026",
              "2026-08-31": "31 Ağustos 2026", "2026-09-28": "28 Eylül 2026"}
    for r in o["bacaklar"]:
        for i, k in enumerate(("fr_bp", "de_bp", "spr_bp", "it_spr_bp", "us10_bp"), 1):
            hucre(t, etiket[r["bas"]], i, bp(r[k], 1, True), "bacaklar")
    # evreler: ülke farkları
    t = tablo("Bund'a fark, değişim")
    etiket = {"2026-08-31": "birinci evre: 31 Ağustos → 28 Eylül", "2026-09-28": "ikinci evre: 28 Eylül → 1 Ekim"}
    for r in o["evreler"]:
        for i, k in enumerate(("fr", "it", "be", "es", "gr", "pt", "at", "nl", "fr_eksi_it"), 1):
            hucre(t, etiket[r["bas"]], i, bp(r[k], 1, True), "evreler")
    # beta
    t = tablo("dönem", "Fransa", "İtalya", "Avusturya")
    for r in o["beta"]["donemler"]:
        e = "2026 Eylül (30 Eylül'e kadar)" if r["ad"] == "2026 Eylül" else r["ad"]
        hucre(t, e, 1, sayi(r["fr_b"], 2), "beta")
        hucre(t, e, 2, sayi(r["it_b"], 2), "beta")
        hucre(t, e, 3, sayi(r["at_b"], 2), "beta")
        hucre(t, e, 4, sayi(r["n"], 0), "beta")
    # büyük günler
    t = tablo("gün", "fark")
    for r in o["buyuk_gunler"]:
        e = f"{r['gun'][8:10]}.{r['gun'][5:7]}"
        hucre(t, e, 1, bp(r["spr"], 1, True), "büyük günler")
        for i, k in enumerate(("fr", "de", "us10", "it_spr"), 2):
            hucre(t, e, i, sayi(r[k], 1, True), "büyük günler")
    # çapraz kur ayrıştırması
    ad = {("2026-02-25", "2026-10-01"): "25 Şubat → 1 Ekim", ("2026-06-30", "2026-08-31"): "30 Haziran → 31 Ağustos",
          ("2026-08-31", "2026-09-28"): "31 Ağustos → 28 Eylül", ("2026-09-28", "2026-10-01"): "28 Eylül → 1 Ekim",
          ("2026-08-31", "2026-10-01"): "31 Ağustos → 1 Ekim"}
    t = tablo("pencere", "EUR/USD")
    for r in o["capraz"]:
        e = ad.get((r["bas"], r["son"]))
        if e is None:
            continue
        for i, k in enumerate(("fx", "dolar_gbp", "eurgbp", "dolar_chf", "eurchf"), 1):
            hucre(t, e, i, yz(r[k], 2, True), "çapraz")
        hucre(t, e, 6, bp(r["spr"], 1, True), "çapraz")
        hucre(t, e, 7, bp(r["ispr"], 1, True), "çapraz")
    # Avrupa dışı dolar sepeti
    t = tablo("pencere", "dolar / yen")
    for (b_, s_), e in ad.items():
        if b_ < "2026-08-31":
            continue
        r = _cap(o, b_, s_)
        for i, k in enumerate(("usdjpy", "usdcad", "usdaud", "dolar_avrupa"), 1):
            hucre(t, e, i, yz(r[k], 2, True), "Avrupa dışı")
        dogru(abs(r["dolar_avrupa"] + (r["dolar_gbp"] + r["dolar_chf"]) / 2) < 1e-4,
              f"'sterlin ve frank (ortalama)' sütunu iki dolar bacağının ortalamasının tersi değil: {e}")
    # duyarlılık (EUR/USD)
    t = tablo("dönem", "hafta")
    for ad_, mm in o["duyarlilik"].items():
        f = mm["faiz+fr"]
        hucre(t, ad_, 1, sayi(f["n"], 0), "duyarlılık")
        hucre(t, ad_, 2, yz(f["b"]["spr"] * 10, 2, True), "duyarlılık")
        hucre(t, ad_, 3, sayi(f["t"]["spr"], 1, True), "duyarlılık")
        hucre(t, ad_, 4, yz(f["b"]["rd"] * 10, 2, True), "duyarlılık")
        hucre(t, ad_, 5, sayi(f["t"]["rd"], 1, True), "duyarlılık")
        hucre(t, ad_, 6, sayi(f["r2"], 3), "duyarlılık")
    # yanlışlama: aynı model dört kurda
    t = tablo("dönem", "EUR/USD", "GBP/USD")
    for ad_, mm in o["duyarlilik"].items():
        for i, k in enumerate(("faiz+fr", "gbpusd", "eurgbp", "eurchf"), 1):
            r = mm[k]
            hucre(t, ad_, i, f"{yz(r['b']['spr'] * 10, 2, True)} (t {sayi(r['t']['spr'], 1, True)})", "yanlışlama")
    # örneklem dışı
    t = tablo("tahmin dönemi")
    for k, (eg, te) in {"2004_2023": ("2004–2023", "2024–2026"), "2013_2023": ("2013–2023", "2024–2026"),
                        "2004_2019": ("2004–2019", "2020–2026")}.items():
        r = o["orneklem_disi"]["fx"][k]
        hucre(t, eg, 1, te, "örneklem dışı")
        hucre(t, eg, 2, sayi(r["test_n"], 0), "örneklem dışı")
        hucre(t, eg, 3, sayi(r["faiz"]["r2_dis"], 3), "örneklem dışı")
        hucre(t, eg, 4, sayi(r["faiz+fr"]["r2_dis"], 3), "örneklem dışı")
        hucre(t, eg, 5, sayi(r["esli_t"], 2), "örneklem dışı")
        hucre(t, eg, 6, sayi(o["orneklem_disi"]["gbpusd"][k]["esli_t"], 2), "örneklem dışı")
        hucre(t, eg, 7, sayi(o["orneklem_disi"]["eurgbp"][k]["esli_t"], 2), "örneklem dışı")
    # atıf
    t = tablo("katsayıların tahmin dönemi")
    etiket = {"2024-01-03–2026-06-24": "Ocak 2024 – Haziran 2026", "2004-01-07–2023-12-27": "2004–2023",
              "2013-01-02–2023-12-27": "2013–2023", "2010-01-06–2012-12-26": "2010–2012",
              "2004-01-07–2026-06-24": "2004 – Haziran 2026"}
    ad_ = o["atif_duyarlilik"]
    for i, r in enumerate(ad_["fx"]):
        e = etiket[r["egitim"]]
        hucre(t, e, 1, sayi(r["n"], 0), "atıf")
        hucre(t, e, 2, yz(r["spread_payi"], 2, True), "atıf")
        hucre(t, e, 3, yz(r["faiz_payi"], 2, True), "atıf")
        hucre(t, e, 4, yz(r["sabit_payi"], 2, True), "atıf")
        hucre(t, e, 5, yz(r["artik"], 2, True), "atıf")
        hucre(t, e, 6, yz(ad_["gbpusd"][i]["spread_payi"], 2, True), "atıf")
        hucre(t, e, 7, yz(ad_["eurgbp"][i]["spread_payi"], 2, True), "atıf")
        hucre(t, e, 8, yz(ad_["eurchf"][i]["spread_payi"], 2, True), "atıf")
        dogru(ad_["gbpusd"][i]["egitim"] == r["egitim"] == ad_["eurgbp"][i]["egitim"] == ad_["eurchf"][i]["egitim"],
              "atıf satırları hizalı değil")
        for y in ("fx", "gbpusd", "eurgbp", "eurchf"):
            q = ad_[y][i]
            dogru(abs(q["spread_payi"] + q["faiz_payi"] + q["sabit_payi"] + q["artik"] - q["kur_gercek"]) < 1e-5,
                  f"atıf toplamı ölçülene eşit değil: {y} {e}")
    # epizotlar: fark
    t = tablo("epizot", "başlangıç → zirve")
    for r in o["epizotlar"]:
        hucre(t, r["ad"], 1, f"{gun_k(r['bas'])} → {gun_k(r['zirve_gun'])}", "epizot")
        hucre(t, r["ad"], 2, bp(r["bas_seviye"]), "epizot")
        hucre(t, r["ad"], 3, bp(r["zirve"]), "epizot")
        hucre(t, r["ad"], 4, bp(r["acilma"], 1, True), "epizot")
        hucre(t, r["ad"], 5, sayi(r["is_gunu"], 0), "epizot")
        hucre(t, r["ad"], 6, bp(r["it_bp"], 1, True), "epizot")
        for i, k in ((7, "sonra_1a"), (8, "sonra_3a")):
            hucre(t, r["ad"], i, "—" if r[k] is None else bp(r[k], 1, True), "epizot")
    # epizotlar: kurlar
    t = tablo("epizot", "EUR/USD")
    for r in o["epizotlar"]:
        hucre(t, r["ad"], 1, yz(r["eurusd_yuzde"], 2, True), "epizot kur")
        hucre(t, r["ad"], 2, yz(r["eurgbp_yuzde"], 2, True), "epizot kur")
        hucre(t, r["ad"], 3, sayi(r["eurgbp_z"], 1, True) + "σ", "epizot kur")
        hucre(t, r["ad"], 4, yz(r["eurchf_yuzde"], 2, True), "epizot kur")
    # olay tepkileri
    t = tablo("olay", "zaman")
    for r in o["olay_tepkileri"]:
        hucre(t, r["ad"], 1, ZAMAN[r["zaman"]], "olay")
        hucre(t, r["ad"], 2, gun_k(r["sonra"]), "olay")
        hucre(t, r["ad"], 3, bp(r["spr"], 1, True), "olay")
        hucre(t, r["ad"], 4, bp(r["it"], 1, True), "olay")
        hucre(t, r["ad"], 5, yz(r["fx"], 2, True), "olay")
        hucre(t, r["ad"], 6, "—" if r["eurgbp"] is None else yz(r["eurgbp"], 2, True), "olay")
        # pencere sözleşmesi: getiri ve kur hangi günden ölçüldü
        if r["zaman"] == "gun":
            dogru(r["kur_once"] == r["once"], f"gün içi olayın kur penceresi getiriyle aynı değil: {r['ad']}")
        elif r["zaman"] == "aksam":
            dogru(r["kur_once"] < r["once"], f"akşam olayının kur penceresi olay gününden önce başlamıyor: {r['ad']}")
        else:
            dogru(r["kur_once"] == r["once"] and r["once"] < r["sonra"],
                  f"hafta sonu olayının penceresi cuma → pazartesi değil: {r['ad']}")
    dogru(len(t) - 1 == len(o["olay_tepkileri"]), "olay tablosunun satır sayısı ölçümle aynı değil")
    # katalizör ve izleme tablolarındaki sayılar
    t = tablo("tarih", "olay")
    ev = {r["bas"]: r for r in o["evreler"]}
    eg2 = o["egri"]["2"]["spread"]
    hucre(t, "Ekim boyunca", 2, "Kurun dolar bacağı: eylülün birinci evresinde ABD 2 yıllığı "
          f"{bp(ev['2026-08-31']['us2y_bp'], 1, True)} yükseldi, ABD–Almanya 2 yıllık farkı "
          f"{bp(_cap(o, '2026-08-31', '2026-09-28')['rd'], 1, True)} açıldı", "katalizör")
    hucre(t, "15 Ekim 2026", 2, "Komisyon'un değerlendirmesi kasımda; İtalya'nın planı bulaşma tarafı. İhale orta "
          f"vadeli kâğıtlarda talebi gösterir; 2 yıllık fark 1 Ekim'de {bp(eg2)}", "katalizör")
    dis_hucre(t, "5 Kasım 2026", 2, "%4,93 ile satıldı, teklif/satış 2,0", "AFT ihale sonucu")
    dis_hucre(t, "18 Aralık 2026", 2, "%119,0", "INSEE")
    t = tablo("ne zaman", "ne")
    c2 = _cap(o, "2026-09-28")
    hucre(t, "Her gün: kurlar", 2, "Fark açılırken euro sterline ve franka karşı da düşüyorsa etki euroya özgü; "
          f"yalnız dolara karşı düşüyorsa ortak etken. 28 Eylül → 1 Ekim {yz(c2['eurgbp'], 2, True)} ve "
          f"{yz(c2['eurchf'], 2, True)}.", "izleme")
    hucre(t, "Her gün: fark", 2, "Bund düşerken OAT yükselmeye devam ederse ikinci evre sürüyor; ikisi birlikte "
          f"yükselirse yeniden küresel faiz hikâyesi. Bugün {bp(o['seviye']['spread'])}.", "izleme")
    ak = {r["ad"]: r for r in o["akranlar"]}
    hucre(t, "Her gün: bulaşma", 2, "Bulaşmanın ölçüsü; 2010–2012'de euroya özgü etki İtalya farkından geldi. 1 "
          f"Ekim'de İtalya {bp(ak['İtalya']['spread'])}, Fransa–İtalya {bp(o['fransa_italya']['fr_eksi_it'], 1, True)}.",
          "izleme")
    l17 = next(r for r in o["olay_tepkileri"] if r["ad"] == "2017 ilk tur: Macron–Le Pen")
    hucre(t, "Nisan–Mayıs 2027", 2, "2017'de birinci tur sonucu farkı bir günde "
          f"{bp(l17['spr'], 1, True)} daraltmıştı.", "izleme")


def cumleler(on: dict, o: dict) -> None:
    sv, h, k = o["seviye"], o["hiz"], o["kur"]
    fi, eg, oy = o["fransa_italya"], o["egri"], o["oynaklik"]
    D = o["duyarlilik"]
    d24 = D["2024–2026"]
    b, p = o["beta"], o["gun_ici_pencere"]
    ey, e1c, e2c, yaz_, dip = (_cap(o, "2026-08-31"), _cap(o, "2026-08-31", "2026-09-28"), _cap(o, "2026-09-28"),
                               _cap(o, "2026-06-30", "2026-08-31"), _cap(o, "2026-02-25"))
    ev1, ev2 = o["evreler"]
    bd = {r["ad"]: r for r in b["donemler"]}
    j26, eyl = bd["2026 Ocak–Ağustos"], bd["2026 Eylül"]
    ep = {r["ad"]: r for r in o["epizotlar"]}
    oy_ = {r["ad"]: r for r in o["olay_tepkileri"]}
    e2o = o["evre2_olcek"]
    il, il66, ilb = o["ileri"][0], o["ileri"][1], o["ileri"][4]
    ak = {r["ad"]: r for r in o["akranlar"]}
    l17, dr = oy_["2017 ilk tur: Macron–Le Pen"], oy_['Draghi: "ne gerekiyorsa"']
    notlar = [r for r in o["olay_tepkileri"] if r["tur"] == "not" and r["once"] >= "2024-01-01"]
    ns = sorted(notlar, key=lambda r: r["spr"])
    d2 = f"−%{sayi(abs(ey['dolar_gbp']), 1)}–{sayi(abs(ey['dolar_chf']), 1)}"
    s10 = ay_yil(sv["son_gorulme"])
    h22 = ay_yil(h["10y_22"]["son_gorulme"])

    # ── ön bilgi: başlık, açıklama, kart özeti (gövdeden ayrı)
    metinde(f"{gun(sv['gun'])[:-5]} Avrupa kapanışında {sayi(sv['spread'])} baz puana çıktı: {s10}'den beri en yüksek "
            f"seviye, son 22 iş gününde {bp(h['10y_22']['degisim'], 1, True)} ile {h22}'den beri en hızlı açılma",
            "açıklama seviye", "aciklama")
    metinde(f"EUR/USD 31 Ağustos'tan bu yana {yz(ey['fx'], 2, True)} kaybetti, ama sterlin ve frank da dolara karşı {d2} "
            "düştü: kaybın beşte dördü öbür Avrupa paralarıyla ortaktı", "açıklama kur", "aciklama")
    metinde(f"OAT–Bund farkı {bp(sv['spread'])} ile {s10}'den beri en yüksekte", "kart özeti", "ozet")
    metinde(f"{gun(SLUG[-10:])} OAT–Bund Farkı", "başlık tarihi (dosya adının tarihi)", "baslik")
    for kol in ("dolar_gbp", "dolar_chf"):
        dogru(0.75 <= ey[kol] / ey["fx"] <= 0.87, f"'kaybın beşte dördü ortaktı' tutmuyor: {kol} {ey[kol] / ey['fx']:.2f}")
    dogru(e1c["eurgbp"] > -0.1 and e1c["eurchf"] > -0.1 and e2c["eurgbp"] < -0.3 and e2c["eurchf"] < -0.3,
          "'euroya özgü kayıp son üç günde' tutmuyor")
    bag = [d for d, mm in D.items() if mm["eurgbp"]["b"]["spr"] < 0 and abs(mm["eurgbp"]["t"]["spr"]) >= 1.96]
    dogru(bag == ["2010–2012"], f"sterline karşı euroya özgü bağ yalnız 2010–12'de değil: {bag}")
    fr = o["saglamlik"]["frank"]
    dogru(abs(fr["2013–2019"]["snb_haric"]["t"]["spr"]) >= 1.96 and abs(fr["2013–2019"]["snb_haric_vix"]["t"]["spr"]) >= 1.96
          and abs(D["2013–2019"]["eurchf"]["t"]["spr"]) < 1.96
          and abs(D["2020–2023"]["eurchf"]["t"]["spr"]) >= 1.96 and abs(fr["2020–2023"]["vix"]["t"]["spr"]) < 1.96
          and abs(D["2024–2026"]["eurchf"]["t"]["spr"]) < 1.96,
          "franka karşı euroya özgü bağ '2013–2019'da SNB haftalarına, 2020–2023'te VIX'e duyarlı, 2024–2026'da yok' "
          "tutmuyor")
    dogru(abs(fr["2013–2019"]["it_snb_haric"]["t"]["spr"]) < 1.96 and abs(fr["2020–2023"]["vix"]["t"]["spr"]) < 1.96
          and abs(D["2010–2012"]["eurgbp_it"]["t"]["spr"]) < 1.96,
          "'geçmişteki euroya özgü bağın her biri tek bir kontrolle anlamsızlaşıyor' tutmuyor")
    e10g = D["2010–2012"]["eurgbp_it"]
    dogru(abs(e10g["t"]["spr"]) < 1.96 and e10g["t"]["ispr"] <= -1.96,
          "2010–12 sterlin bağı İtalya farkı eklenince İtalya'ya geçmiyor")
    # ── yönetici özeti: tez
    metinde(f"kapanışında {bp(sv['spread'])} ile {s10}'den beri en yüksekte; son 22 iş gününde "
            f"{bp(h['10y_22']['degisim'], 1, True)} açıldı", "tez seviye ve hız")
    metinde(f"EUR/USD 31 Ağustos'tan bu yana {yz(ey['fx'], 2, True)} kaybetti; sterlin ve frank da dolara karşı {d2} düştü, "
            "yani kaybın beşte dördü öbür Avrupa paralarıyla ortaktı", "tez dolar bacağı")
    dogru(ey["usdcad"] > 0 and ey["usdaud"] > 0 and ey["usdjpy"] < 0,
          "'dolar yen dışında Avrupa dışı paralara karşı da güçlendi' tutmuyor")
    metinde(f"(sterline karşı {yz(e2c['eurgbp'], 2, True)}, franka karşı {yz(e2c['eurchf'], 2, True)})", "tez euro bacağı")
    # ── yönetici özeti: tablo
    metinde(f"günlerin {yz(sv['yuzdelik_2000'], 1)}'inden üstünde; bu serideki tarihî zirve {bp(sv['tarihi_zirve'])} "
            f"({gun(sv['tarihi_zirve_gun'])})", "özet yüzdelik ve zirve")
    metinde(f"Fransa {tarih_ga(fi['kesintisiz_bas'])}'tan beri İtalya'dan pahalı borçlanıyor: 1 Ekim'de "
            f"{bp(fi['fr_eksi_it'])}", "özet Fransa–İtalya")
    dis("2026 açığı %5,4 ile hedefin üstünde, 2027'de %5'e inmek için 54 milyar", "HCFP görüşü, Lecornu söyleşisi")
    dis("borç GSYH'nin %119,0'ı", "INSEE")
    metinde(f"Bund'a betası 2026'nın ilk sekiz ayında {sayi(j26['fr_b'], 2)}, Avusturya ({sayi(j26['at_b'], 2)}) ile "
            f"İtalya ({sayi(j26['it_b'], 2)}) arasında", "özet beta")
    dogru(j26["at_b"] < j26["fr_b"] < j26["it_b"], "2026 betası Avusturya ile İtalya arasında değil")
    metinde(f"31 Ağustos → 28 Eylül euro {yz(e1c['fx'], 2, True)}, sterlin {yz(e1c['dolar_gbp'], 2, True)} kaybetti: "
            "euroya özgü kayıp yok", "özet evre 1")
    metinde(f"28 Eylül → 1 Ekim euro {yz(e2c['fx'], 2, True)}, sterlin {yz(e2c['dolar_gbp'], 2, True)} kaybetti; frank "
            "dolara karşı yükseldi", "özet evre 2")
    dogru(e2c["dolar_chf"] > 0, "ikinci evrede frank dolara karşı yükselmedi")
    metinde(f"10 bp açılmaya EUR/USD'de {yz(d24['faiz+fr']['b']['spr'] * 10, 2, True)} eşlik ediyor (2024–2026), "
            f"GBP/USD'de de {yz(d24['gbpusd']['b']['spr'] * 10, 2, True)}", "özet haftalık")
    metinde(f"Haftalık kur bağı anlamlı (t {sayi(d24['faiz+fr']['t']['spr'], 1)})", "özet t")
    dogru(abs(d24["faiz+fr+it"]["t"]["spr"]) < 1.96, "İtalya farkı eklenince Fransa katsayısı anlamsızlaşmıyor")
    metinde(f"sterline karşı olağan oynaklığın {sayi(abs(e2o['eurgbp']['z']), 1)}, franka karşı "
            f"{sayi(abs(e2o['eurchf']['z']), 1)} katı", "özet evre 2 ölçeği")
    metinde(f"bir aylık ±1,96σ bandı ±{bp(oy['bant_1a'])}", "özet bant")
    metinde(f"fark ertesi ay medyanda {bp(il['medyan'], 1, True)} geriledi", "özet ileri medyan")
    a11 = [c for c in il66["kumeler"] if c["bas"].startswith("2011-08")][0]
    metinde(f"dört gözlemin dördünde daha açıktı (medyan {bp(a11['ileri_medyan'], 1, True)})", "özet Ağustos 2011")
    dogru(a11["n"] == 4 and a11["daha_acilan"] == 4 and a11["azami_acilma"] < il66["bugunku_acilma"]
          and sum(1 for c in il66["kumeler"] if c["bas"][:7] == "2011-08") == 1,
          "Ağustos 2011 kümesi dört/dört / tek küme / bugünkü hızın altında değil")
    kb_ = [c for c in il["kumeler"] if c["bas"] <= ilb["kumeler"][0]["bas"] and ilb["kumeler"][-1]["son"] <= c["son"]]
    dogru(len(kb_) == 1 and kb_[0]["bas"][:7] == "2011-10" and kb_[0]["son"][:7] == "2012-01"
          and all(c["daha_acilan"] == 0 for c in ilb["kumeler"]),
          "bugünkü hızı aşan açılma: tek 30 bp kümesi (Ekim 2011 – Ocak 2012) / hepsi daraldı tutmuyor")
    dogru(len(ilb["kumeler"]) == 2 and ilb["kumeler"][0]["bas"][:7] == "2011-11" and ilb["kumeler"][-1]["bas"][:7] == "2012-01",
          "bugünkü eşikte kümeler Kasım 2011 ve Ocak 2012 değil")
    metinde(f"(2010 {yz(ep['2010 Yunanistan']['eurgbp_yuzde'], 2, True)}, 2011 "
            f"{yz(ep['2011 euro bölgesi borç krizi']['eurgbp_yuzde'], 2, True)})", "özet kriz EUR/GBP")
    dogru(all(0.8 <= abs(ep[x]["eurgbp_z"]) <= 1.4 for x in ("2010 Yunanistan", "2011 euro bölgesi borç krizi")),
          "'pencere uzunluğuna göre yaklaşık bir standart sapma' tutmuyor")
    metinde(f"euroyu sterline karşı bir günde {yz(l17['eurgbp'], 2, True)} yükseltti", "özet 2017")
    dogru(len(notlar) == 15, f"2024 sonrası not kararı sayısı {len(notlar)}, metin 'on beş'")
    on4 = [r for r in notlar if r["karisik"] is None]
    dogru(len(on4) == 14, "karışık olmayan not kararı on dört değil")
    metinde(f"on dördünde fark {sayi(min(r['spr'] for r in on4), 1, True)} ile {sayi(max(r['spr'] for r in on4), 1, True)} "
            "bp arasında oynadı", "özet not aralığı")

    # ── giriş ve Bölüm 1
    kf = o["kaynak"]["fr"]
    metinde(f"üçte iki büyüdü ({sayi(sv['seviye_agustos'])} → {bp(sv['spread'])}), yılın dibinden bu yana yaklaşık iki "
            f"buçuk katına çıktı (gösterge kâğıt değişimi dışarıda bırakılınca {sayi(sv['epizot_kat_gostergesiz'], 1)} "
            "katına)", "giriş")
    dogru(1.6 <= sv["spread"] / sv["seviye_agustos"] <= 1.72, "'üçte iki büyüdü' tutmuyor")
    dogru(2.4 <= sv["epizot_kat"] <= 2.7, "'yaklaşık iki buçuk katı' tutmuyor")
    metinde(f"Fransa 10 yıllığı %{sayi(sv['fr10'], 3)}, Almanya 10 yıllığı %{sayi(sv['de10'], 3)} kapandı; fark "
            f"({sayi(sv['fr10'], 3)} − {sayi(sv['de10'], 3)}) × 100 = {bp(sv['spread'])}", "tanım hesabı")
    metinde(f"resmî seriyle {kf['ay']} ayda {sayi(kf['korelasyon'], 3)} korelasyon veriyor; daha zorlu sınama olan aylık "
            f"değişimlerin korelasyonu {sayi(kf['degisim_korelasyonu'], 2)}. Ortalama fark {bp(kf['ort_fark'])} ve yıldan "
            f"yıla {sayi(kf['yillik_fark_min'], 1, True)} ile {bp(kf['yillik_fark_maks'], 1, True)} arasında oynuyor. "
            f"{ay_yil(kf['son_ay'] + '-01')} için resmî seri {sayi(kf['son_ay_resmi'])}, günlük seriden kurulan ortalama "
            f"{bp(kf['son_ay_cnbc'])}", "kaynak sınaması")
    kb, e17 = kf["bacak"], kf["ekim_2017"]
    metinde(f"(aylık ortalamalar arasındaki fark ortalamada {bp(kb['fr']['ort_fark'], 1, True)})", "Fransa bacağı")
    metinde(f"resmî seride de var ({sayi(e17[0]['resmi'], 0)} → {sayi(e17[1]['resmi'], 0)} bp)", "2017 resmî seride")
    dogru(e17[1]["resmi"] - e17[0]["resmi"] > 5 and e17[1]["cnbc"] - e17[0]["cnbc"] > 5, "Ekim 2017 kayması iki seride de yok")
    metinde(f"{bp(kf['ort_fark'])}'lik ortalama farkın tamamı Almanya bacağında: günlük Bund göstergesi resmî Alman "
            f"serisinden ortalama {bp(kb['de']['ort_fark'])} yüksek", "Almanya bacağı")
    dogru(abs(kb["fr"]["ort_fark"]) < 0.2 and abs(kb["de"]["ort_fark"] + kf["ort_fark"]) < 0.2,
          "'ortalama farkın tamamı Almanya bacağında' tutmuyor")
    bs = o["bar_saati"]
    avr = max(bs[c]["maks_bp"] for c in ("fr10y", "de10y", "it10y", "fr2y", "de2y"))
    metinde(f"en çok {bp(avr)} farklı", "Avrupa bar saati")
    metinde(f"(aynı karşılaştırmada medyan {sayi(min(bs['us2y']['medyan_bp'], bs['us10y']['medyan_bp']), 1)}–"
            f"{bp(max(bs['us2y']['medyan_bp'], bs['us10y']['medyan_bp']))}, en çok "
            f"{bp(max(bs['us2y']['maks_bp'], bs['us10y']['maks_bp']))} fark)", "ABD bar saati")
    dogru(bs["fr10y"]["gun"] == 8 and len(o["gun_ici_bes_gun"]["gunler"]) == 8, "gün içi gün sayısı sekiz değil")
    gi, gk, gq = o["gun_ici"], o["gun_ici"]["gunluk_kapanis"], o["gun_ici_kotasyon"]
    metinde(f"17:30'daki {bp(gi['17:30']['spr'])}, o dakikaya kadarki son kotasyondur (iki 10 yıllık bacakta "
            f"{gq['fr10y']['son']}); günlük kapanış barı {bp(gk['spr'])}", "17:30 iki sayı")
    dogru(gq["fr10y"]["son"] == gq["de10y"]["son"], "iki 10 yıllık bacağın son kotasyonu aynı dakikada değil")
    metinde(f"önceki kapanışa ({bp(o['buyuk_gunler'][-2]['spr_seviye'])}) yakın", "önceki kapanış")
    dogru(o["buyuk_gunler"][-2]["gun"] == "2026-09-30", "önceki kapanış 30 Eylül değil")
    dis("Gün içinde yayımlanan sayılar 127 ile 133 bp arasındaydı", "Reuters, 1 Ekim gün içi haberleri")
    s15 = o["seriler"]["gun_ici"]
    metinde(f"fark 15:45'te {bp(s15['spr'][s15['t'].index('15:45')])}'ye çıkmıştı", "15:45")
    metinde(f"1 Ekim'in referans kuru ({sayi(k['ecb_son'], 4)})", "ECB kuru")
    metinde(f"1 Ekim'in New York kapanışı {sayi(k['son'], 4)}; bu, {gun(k['son_gorulme'])}'ten beri en düşük kapanış ve "
            f"yılın zirvesinden ({tarih_ga(k['yil_zirve_gun'])}, {sayi(k['yil_zirve'], 4)}) log değişimle "
            f"{yz(k['zirveden'], 2, True)}", "NY kapanışı")
    tz, bo = o["temizlik"], o["bosluk"]
    metinde(f"tatil sayılıp atılıyor ({tz['tasinmis_atilan']} gün). Seri 3 Ocak 2000'de başlıyor; temizlikten sonra "
            f"{sayi(tz['temiz_gun'], 0)} iş günü kalıyor, iki bacağın birlikte ölçüldüğü gün "
            f"{sayi(len(o['seriler']['spread']['t']), 0)}", "seri uzunluğu")
    metinde(f"(2014 içinde {bo['uzun_bosluk_2014']} iş günü; yılın {bo['eksik_is_gunu_2014']} eksik gününün kalan "
            f"{['', 'biri', 'ikisi', 'üçü', 'dördü'][bo['eksik_is_gunu_2014'] - bo['uzun_bosluk_2014']]} tatil", "2014 boşluğu")
    # ── Bölüm 2
    metinde(f"Fark yıla {bp(sv['seviye_yb'])} ile başladı, {tarih_ga(sv['yil_dibi_gun'])}'ta {bp(sv['yil_dibi'])} ile "
            f"yılın dibini gördü. Yılın dibinden bu yana {bp(sv['epizot_degisim'], 1, True)} açıldı; bunun "
            f"{bp(sv['epizot_gosterge_payi'], 1, True)}'si 15 Haziran'daki gösterge kâğıt değişimidir", "yıl başı ve dip")
    dogru(sv["epizot_bas_tutarli"] and sv["epizot_gosterge_gunleri"] == ["2026-06-15"], "yılın dibi ya da gösterge günü kaymış")
    dogru(abs(sv["epizot_gosterge_payi"] - h["sicrama_2026"]["gun"] + h["sicrama_2026"]["once"]) < 0.02,
          "gösterge payı 15 Haziran sıçramasıyla aynı değil")
    metinde(f"Haziran sonunda {sayi(sv['seviye_haziran'])}, ağustos sonunda {bp(sv['seviye_agustos'])} idi; 31 Ağustos'tan "
            f"bu yana {bp(sv['degisim_agustos'], 1, True)} açıldı", "haziran-ağustos")
    g18 = next(r for r in o["buyuk_gunler"] if r["gun"] == "2026-09-18")
    metinde(f"Fark 18 Eylül'de {bp(g18['spr_seviye'])} ile {gun(sv['onceki_100'])}'den beri ilk kez 100 bp'nin üstünde "
            f"kapandı, 1 Ekim'de {bp(sv['spread'])} oldu. Son 5 iş gününde {sayi(sv['degisim_1h'], 1, True)}, son 22 iş "
            f"gününde (1 Eylül kapanışından) {bp(sv['degisim_1a'], 1, True)}", "100 eşiği ve pencereler")
    dogru(sv["ilk_100"] == "2026-09-18" and sv["tarih_1h"] == "2026-09-24" and sv["tarih_1a"] == "2026-09-01",
          "100 bp ilk aşım günü ya da 5/22 iş günü pencereleri kaymış")
    dogru(abs(sv["degisim_1a"] - h["10y_22"]["degisim"]) < 1e-9, "22 iş günü iki yerde iki ayrı ölçü")
    metinde(f"farkın o günkü {bp(sv['epizot_gosterge_payi'], 1, True)}'lik sıçraması bir olayın değil", "Şekil 02 G")
    metinde(f"Fransa {bp(ev1['fr10y_bp'], 1, True)}, Almanya {bp(ev1['de10y_bp'], 1, True)}, ABD 10 yıllığı "
            f"{bp(ev1['us10y_bp'], 1, True)}, ABD 2 yıllığı {bp(ev1['us2y_bp'], 1, True)} yükseldi. Fark "
            f"{bp(ev1['fr'], 1, True)} açıldı ve bunun {sayi(ev1['fr_eksi_it'], 1)} bp'si Fransa'nın İtalya'dan "
            "ayrışmasıydı", "evre 1")
    metinde(f"Almanya 10 yıllığı {bp(ev2['de10y_bp'], 1, True)}, 2 yıllığı {bp(ev2['de2y_bp'], 1, True)} düştü; İtalya "
            f"{sayi(ev2['it'], 1, True)}, Belçika {sayi(ev2['be'], 1, True)}, İspanya {sayi(ev2['es'], 1, True)}, Avusturya "
            f"{bp(ev2['at'], 1, True)} açıldı. Fransa–İtalya farkı yalnız {bp(ev2['fr_eksi_it'], 1, True)}", "evre 2")
    dogru(ev2["de2y_bp"] < 2 * ev2["de10y_bp"] * 0.95, "Alman 2 yıllığı 10 yıllığından iki kat hızlı düşmedi")
    dogru(ev1["fr_eksi_it"] > ev2["fr_eksi_it"], "Fransa'ya özgü ayrışma birinci evrede büyük değil")
    b10 = bd["2010–2012"]
    metinde(f"İtalya'nın betası eksi ({sayi(b10['it_b'], 2)}), Fransa'nınki Avusturya ile aynı", "2010–2012 beta")
    dogru(abs(b10["fr_b"] - b10["at_b"]) < 0.05 and b10["it_b"] < 0, "2010–2012: Fransa Avusturya ile aynı / İtalya eksi tutmuyor")
    metinde(f"Fransa'nın betası Ocak–Ağustos'ta Avusturya ({sayi(j26['at_b'], 2)}) ile İtalya ({sayi(j26['it_b'], 2)}) "
            f"arasına yerleşti ve ikisinden de ayrı: Fransa–Avusturya farkının Bund'a betası {sayi(j26['fr_at_b'], 2, True)} "
            f"(t {sayi(j26['fr_at_t'], 1)}), İtalya–Fransa farkınınki {sayi(j26['it_fr_b'], 2, True)} (t "
            f"{sayi(j26['it_fr_t'], 1)}). Eylülün {eyl['n']} gününde Fransa ({sayi(eyl['fr_b'], 2)}) İtalya'dan "
            f"({sayi(eyl['it_b'], 2)}) ayırt edilemiyor (İtalya–Fransa farkının betası {sayi(eyl['it_fr_b'], 2, True)}, t "
            f"{sayi(eyl['it_fr_t'], 1)})", "2026 beta ve fark betaları")
    dogru(j26["fr_at_t"] >= 1.96 and j26["it_fr_t"] >= 1.96 and abs(eyl["it_fr_t"]) < 1.96,
          "fark betalarının anlamlılık okuması tutmuyor")
    e1 = b["evre1"]
    metinde(f"birinci evrede Bund'un {bp(e1['de'], 1, True)} yükselişi, Ocak–Ağustos betasıyla ({sayi(e1['beta_once'], 2)}) "
            f"farkı {bp(e1['pay_once'], 1, True)}, evrenin kendi betasıyla ({sayi(e1['beta_ic'], 2)}; 31 Ağustos → 28 Eylül, "
            f"{e1['beta_ic_n']} iş günü — tablodaki eylül satırının {sayi(eyl['fr_b'], 2)}'sı Bund'un düştüğü 29–30 Eylül'ü de "
            f"taşır) {bp(e1['pay_ic'], 1, True)} açar; yani birinci evrenin {bp(e1['spr'], 1, True)}'lik açılmasının dörtte biri "
            "ile yarısı", "beta payı")
    dogru(0.18 <= e1["pay_once"] / e1["spr"] <= 0.3 and 0.45 <= e1["pay_ic"] / e1["spr"] <= 0.56,
          "'dörtte biri ile yarısı' tutmuyor")
    metinde(f"İkinci evrede Bund {bp(b['evre2']['de'], 1, True)} düşerken Fransa {bp(b['evre2']['fr'], 1, True)} yükseldi",
            "evre 2 imza")
    metinde("Fransa " + bp(ak["Fransa"]["degisim_haziran"], 1, True) + ", İtalya "
            + sayi(ak["İtalya"]["degisim_haziran"], 1, True) + ", Belçika " + sayi(ak["Belçika"]["degisim_haziran"], 1, True)
            + ", Yunanistan " + sayi(ak["Yunanistan"]["degisim_haziran"], 1, True) + ", İspanya "
            + sayi(ak["İspanya"]["degisim_haziran"], 1, True) + ", Portekiz " + sayi(ak["Portekiz"]["degisim_haziran"], 1, True)
            + ", Avusturya " + sayi(ak["Avusturya"]["degisim_haziran"], 1, True) + ", Hollanda "
            + bp(ak["Hollanda"]["degisim_haziran"], 1, True), "akran değişimleri")
    metinde(f"{bp(ak['Fransa']['spread'])}'ye karşı İtalya {sayi(ak['İtalya']['spread'])}, Yunanistan "
            f"{sayi(ak['Yunanistan']['spread'])} (30 Eylül), Belçika {sayi(ak['Belçika']['spread'])}, İspanya "
            f"{bp(ak['İspanya']['spread'])}. Fransa 10 yıllığı İtalya'nınkinin {bp(fi['fr_eksi_it'])} üstünde",
            "akran seviyeleri")
    dogru(o["akranlar"][0]["ad"] == "Fransa" and len(o["akranlar"]) == 8, "Fransa sekiz ülke içinde en geniş fark değil")
    for u in ("Yunanistan", "Portekiz"):
        dogru(ak[u]["gun"] == "2026-09-30", f"{u} son kotasyonu 30 Eylül değil: {ak[u]['gun']}")
    metinde(f"Avrupa kapanışında ilk kez {gun(fi['ilk_pozitif'])}'te oluştu ve {gun(fi['kesintisiz_bas'])}'tan beri her "
            f"gözlemde sürüyor ({fi['gun_sayisi']} gözlem; {fi['is_gunu']} iş gününün ikisinde kaynak kotasyon vermedi). "
            f"30 Eylül'deki {bp(fi['tarihce_zirve'], 1, True)} bu tersine dönüşün tarihî zirvesi", "Fransa–İtalya")
    dogru(len(fi["eksik_gunler"]) == 2 and fi["tarihce_zirve_gun"] == "2026-09-30", "Fransa–İtalya eksik gün/zirve günü kaymış")
    v = ["2", "5", "10", "30"]
    dogru(max(v, key=lambda x: eg[x]["degisim_haziran"]) == "10", "haziran sonundan bu yana en çok açılan 10 yıllık değil")
    metinde(f"en çok 10 yıllık fark açıldı ({bp(eg['10']['degisim_haziran'], 1, True)}; 5 yıllık "
            f"{sayi(eg['5']['degisim_haziran'], 1, True)}, 30 yıllık {sayi(eg['30']['degisim_haziran'], 1, True)}, 2 yıllık "
            f"{sayi(eg['2']['degisim_haziran'], 1, True)})", "haziran eğri")
    metinde(f"2 yıllık fark bir günde {bp(eg['2']['degisim_1g'], 1, True)} ile {bp(eg['2']['spread'])}'ye çıktı — "
            f"{bp(eg['2']['spread'])} en son {gun(eg['2']['son_gorulme'])}'de görülmüştü; 30 Haziran'da "
            f"{bp(eg['2']['spread'] - eg['2']['degisim_haziran'])} idi", "eğri 2y")
    metinde(f"(2 yıllık {sayi(eg['fr2y_1g_bp'], 1, True)}, 5 yıllık {sayi(eg['fr5y_1g_bp'], 1, True)}, 10 yıllık "
            f"{sayi(eg['fr10y_1g_bp'], 1, True)}, 30 yıllık {bp(eg['fr30y_1g_bp'], 1, True)})", "Fransa getirileri")
    metinde(f"2 yıllık {sayi(eg['de2y_1g_bp'], 1)}, 5 yıllık {sayi(eg['de5y_1g_bp'], 1)}, 10 yıllık "
            f"{sayi(eg['de10y_1g_bp'], 1)}, 30 yıllık {bp(eg['de30y_1g_bp'], 1)}. 2 yıllık fark sıçramasının "
            f"{yz(eg['2']['de_payi'] * 100, 0)}'i Alman bacağıdır", "Almanya getirileri")
    metinde(f"İtalya'nın 2 yıllık farkı da {bp(eg['it2']['degisim_1g'], 1, True)} açıldı; İtalya'nın kendi 2 yıllığı "
            f"{bp(eg['it2y_1g_bp'], 1, True)} yükseldi, yani o sıçramanın da {yz(eg['it2']['de_payi'] * 100, 0)}'u", "İtalya 2y")
    dogru(0.6 <= eg["2"]["de_payi"] <= 0.72, "'2 yıllık sıçramanın üçte ikisi Almanya'dan' tutmuyor")
    sp = [eg[x]["spread"] for x in v]
    dogru(sp == sorted(sp), "fark eğrisi yukarı eğimli değil")
    metinde(" / ".join(sayi(x) for x in sp) + " bp ile yukarı eğimli", "eğri seviyeleri")
    # ── Bölüm 3 — dış kaynak sayıları (adıyla) ve ölçülebilen kısımları
    dis("büyüme tahminini bu yıl üçüncü kez düşürerek %0,5'e indirdi", "Europe 1, Lescure 11 Eylül")
    dis("2026 için %5,4'lük açığı esas alıyor", "HCFP görüşü")
    dis("2027 açığı GSYH'nin %6,5'ine yaklaşırdı", "Lecornu, Le Figaro")
    dis("açık 2027'de %5,9'a, 2030'da %6,8'e kayabilir", "Ekonomi Bakanlığı raporu, LCP")
    dis("3.595,5 milyar avro, GSYH'nin %119,0'ı (ilk çeyrekte %117,5); çeyrekte +59,6 milyar avro", "INSEE n° 239")
    dis("339,7 milyar avro", "AFT 2027 programı")
    dis("2027'de 72,9 milyar avro: 2026 için güncellenen 62,6 milyarın 10,3 milyar, 2026 bütçe yasasındaki 59,3 "
        "milyarın 13,6 milyar üstünde", "AFT 2027 programı")
    dogru(round(72.9 - 62.6, 1) == 10.3 and round(72.9 - 59.3, 1) == 13.6, "AFT faiz maliyeti farkları aritmetiği tutmuyor")
    dis("faizin gelecek yıl 12,3 milyar avro artacağını", "Amiel, LCP 16 Temmuz")
    dis("10 yıllık borçlanma faizini %4,3 varsayıyor", "AFT 2027 programı")
    dis("ortalama %4,93 getiriyle satıldı (3 Eylül'de %4,23); 2048 vadeli kâğıt %5,40 ile (2 Nisan'da %4,35)",
        "AFT ihale sonuçları")
    dis("6,271 milyar avroluk 2036 kâğıdına 12,564 milyar avroluk teklif, teklif/satış 2,0", "AFT ihale sonuçları")
    dogru(f"{12.564 / 6.271:.1f}" == "2.0" and round((4.93 - 4.30) * 100) == 63,
          "ihale aritmetiği tutmuyor (teklif/satış ya da varsayıma uzaklık)")
    metinde("bütçe varsayımının 63 bp üstünde", "ihale ile varsayım farkı")
    ef = {r["gun"]: r["dfr"] for r in o["ecb_faiz"]}
    dogru(ef.get("2025-06-11") == 2.0 and ef.get("2026-06-17") == 2.25 and ef.get("2026-09-16") == 2.5,
          f"ECB mevduat faizi patikası metinle uyuşmuyor: {ef}")
    metinde(f"mevduat faizini 11 Haziran'da %{sayi(ef['2025-06-11'], 2)}'den %{sayi(ef['2026-06-17'], 2)}'e, 10 Eylül'de "
            f"%{sayi(ef['2026-09-16'], 2)}'ye çıkardı", "ECB patikası")
    metinde(f"ABD 10 yıllığı 30 Eylül'de %{sayi(sv['us10_onceki'], 2)}, 1 Ekim'de %{sayi(sv['us10_son'], 2)} kapandı",
            "ABD 10y")
    dogru(sv["us10_onceki_gun"] == "2026-09-30", "ABD 10y önceki gün 30 Eylül değil")
    g18_, g21 = g18, next(r for r in o["buyuk_gunler"] if r["gun"] == "2026-09-21")
    metinde(f"18 Eylül'ün {bp(g18_['spr'], 1, True)}'si indirimden önce geldi", "18 Eylül")
    metinde(f"indirimden sonraki pazartesi fark {bp(g21['spr'], 1, True)} daraldı", "21 Eylül")
    bg = o["buyuk_gunler"]
    dogru(all((r["de"] > 0) or (r["fr"] < 0) for r in bg[:4]) and all(r["de"] < 0 for r in bg[4:]),
          "büyük günler: ilk dört / son üç satır okuması tutmuyor")
    dis("politika faizini %3,75–4,00'e yükseltti", "Federal Reserve, 16 Eylül kararı")
    # ── Bölüm 4
    dis("borcu stoklarından birinde (3.595,5 milyar avro)", "INSEE n° 239")
    kk = o["kur_kaynak"]
    metinde(f"medyanda fiyatın on binde {sayi(kk['gbp_ozdeslik_medyan_bp'], 0)}'ü kadar ayrışıyor", "sentetik GBP/USD")
    metinde(f"31 Ağustos'tan bu yana euro dolara karşı {yz(ey['fx'], 2, True)} kaybetti; sterlin {yz(ey['dolar_gbp'], 2, True)}, "
            f"frank {yz(ey['dolar_chf'], 2, True)} kaybetti. Euroya özgü kısım sterline göre {yz(ey['eurgbp'], 2, True)}, "
            f"franka göre {yz(ey['eurchf'], 2, True)}: kaybın beşte biri kadar", "eylül ayrıştırması")
    dogru(0.13 <= ey["euro_payi_gbp"] <= 0.25 or 0.13 <= ey["eurgbp"] / ey["fx"] <= 0.25, "'beşte biri kadar' tutmuyor (sterlin)")
    dogru(0.13 <= ey["eurchf"] / ey["fx"] <= 0.25, "'beşte biri kadar' tutmuyor (frank)")
    metinde(f"dolar aynı pencerede Kanada dolarına karşı {yz(ey['usdcad'], 2, True)}, Avustralya dolarına karşı "
            f"{yz(ey['usdaud'], 2, True)} güçlendi, yalnız yene karşı {yz(ey['usdjpy'], 2, True)} değer kaybetti", "Avrupa dışı")
    metinde(f"31 Ağustos → 28 Eylül euro {yz(e1c['fx'], 2, True)}, sterlin {yz(e1c['dolar_gbp'], 2, True)} kaybetti; euro "
            f"sterline karşı {yz(e1c['eurgbp'], 2, True)}, franka karşı {yz(e1c['eurchf'], 2, True)} değer kazandı. Bu evrede "
            f"ABD 2 yıllığı {bp(e1c['us2'], 1, True)} yükseldi, ama Alman 2 yıllığı da yükseldiği için ABD–Almanya 2 yıllık "
            f"faiz farkı yalnız {bp(e1c['rd'], 1, True)} açıldı; dolar güçlendi, ama yene karşı {yz(e1c['usdjpy'], 2, True)} "
            f"değer kaybetti. Fransa farkı {bp(e1c['spr'], 1, True)} açıldı", "evre 1 çapraz")
    dogru(e1c["de2"] > 0 and e1c["rd"] < e1c["us2"] and e1c["usdjpy"] < 0,
          "evre 1: Alman 2y yükselmedi / faiz farkı ABD 2y'den az açılmadı / dolar yene karşı kaybetmedi")
    dogru(abs(e1c["us2"] - ev1["us2y_bp"]) < 0.05 and abs(e1c["spr"] - ev1["fr"]) < 0.05, "çapraz ve evre tabloları ayrışıyor")
    metinde(f"(aynı evrede Fransa İtalya'dan {bp(ev1['fr_eksi_it'], 1, True)} ayrıştı)", "evre 1 Fransa–İtalya")
    metinde(f"28 Eylül → 1 Ekim euro {yz(e2c['fx'], 2, True)} kaybederken sterlin yalnız {yz(e2c['dolar_gbp'], 2, True)} "
            f"kaybetti, frank dolara karşı {yz(e2c['dolar_chf'], 2, True)} kazandı. Euro sterline karşı "
            f"{yz(e2c['eurgbp'], 2, True)}, franka karşı {yz(e2c['eurchf'], 2, True)} düştü. Bu, bütün euro farklarının Bund'a "
            f"karşı birlikte açıldığı ve Alman 2 yıllığının {bp(e2c['de2'], 1, True)} düştüğü evredir", "evre 2 çapraz")
    dogru(e2o["bas"] == "2026-09-28" and e2o["is_gunu"] == 3 and abs(e2o["eurgbp"]["degisim"] - e2c["eurgbp"]) < 1e-6
          and abs(e2o["eurchf"]["degisim"] - e2c["eurchf"]) < 1e-6, "evre 2 ölçeği çapraz tablosuyla aynı pencere değil")
    metinde(f"sterline karşı kayıp, 2024'ten bu yana üç iş günlük değişimlerin standart sapmasının "
            f"{sayi(abs(e2o['eurgbp']['z']), 1)} katı (bu pencerelerin {yz(e2o['eurgbp']['daha_kotu_payi'], 1)}'sinde daha "
            f"büyük bir kayıp var); franka karşı {sayi(abs(e2o['eurchf']['z']), 1)} katı "
            f"({yz(e2o['eurchf']['daha_kotu_payi'], 1)})", "evre 2 ölçeği")
    c30 = _cap(o, "2026-09-30")
    dogru(abs(c30["eurchf"]) >= abs(e2c["eurchf"]) and e2c["dolar_chf"] > 0 and e2c["dolar_gbp"] < 0
          and min(e2c["usdjpy"], e2c["usdcad"], e2c["usdaud"]) > 0,
          "'franka karşı kaybın tamamı tek günden / frank dolara karşı yükselen tek para' tutmuyor")
    metinde(f"Tek başına 1 Ekim'de euro sterline karşı {yz(c30['eurgbp'], 2, True)}, franka karşı "
            f"{yz(c30['eurchf'], 2, True)} düştü", "1 Ekim çaprazları")
    metinde(f"Yılın dibinden bu yana euro sterline karşı {yz(dip['eurgbp'], 2, True)} kaybetti ama franka karşı "
            f"{yz(dip['eurchf'], 2, True)} kazandı", "uzun pencere")
    dogru(dip["eurgbp"] * dip["eurchf"] < 0 and yaz_["eurgbp"] * yaz_["eurchf"] < 0, "uzun pencerede kıyaslar ayrışmıyor")
    metinde(f"ertesi gün İtalya'nın 10 yıllık farkı {bp(eg['it10']['degisim_1g'], 1, True)} açıldı ve euro sterline karşı "
            f"{yz(c30['eurgbp'], 2, True)} düştü", "BBH sonrası")
    f04 = D["2004–2026"]["faiz+fr"]
    sg = o["saglamlik"]
    metinde(f"10 bp'lik açılmaya {yz(f04['b']['spr'] * 10, 2, True)} eşlik ediyor. Rejime bağlı", "tüm örneklem")
    s24 = sg["2024–2026"]["fx"]
    metinde(f"her hafta tek tek çıkarıldığında katsayı {yz(s24['b_maks'], 2, True)} ile {yz(s24['b_min'], 2, True)} arasında "
            f"kalıyor, en zayıf t {sayi(s24['t_en_zayif'], 1)}", "2024–26 tek hafta")
    i24_ = d24["faiz+fr+it"]
    metinde(f"ama İtalya farkı eklenince {yz(i24_['b']['spr'] * 10, 2, True)}'e iniyor ve anlamlılığını yitiriyor (t "
            f"{sayi(i24_['t']['spr'], 1)}; Yöntem eki)", "2024–26 İtalya eklenince")
    sh, sp20 = sg["salgin_haftasi"], sg["2020–2023_salgin_haric"]["fx"]
    metinde(f"2020–2023'teki {yz(D['2020–2023']['faiz+fr']['b']['spr'] * 10, 2, True)}'nin anlamlılığı ise tek bir haftaya "
            f"dayanıyor: 18 Mart 2020'nin salgın satışı (o hafta fark {bp(sh['spr'], 1, True)} açıldı, GBP/USD "
            f"{yz(sh['gbpusd'], 2, True)}) çıkarılınca katsayı {yz(sp20['b']['spr'] * 10, 2, True)}, t "
            f"{sayi(sp20['t']['spr'], 1)}", "salgın haftası")
    dogru(all(abs(mm["faiz+fr"]["t"]["rd"]) >= abs(mm["faiz+fr"]["t"]["spr"]) for mm in D.values()),
          "'faiz farkı her dönemde en az fark kadar güçlü' tutmuyor")
    metinde(f"2024–2026'da 10 bp'lik açılmaya GBP/USD'de {yz(d24['gbpusd']['b']['spr'] * 10, 2, True)} eşlik ediyor",
            "GBP/USD")
    dogru(abs(d24["gbpusd"]["b"]["spr"]) > abs(d24["faiz+fr"]["b"]["spr"]), "GBP/USD katsayısı EUR/USD'dekinden büyük değil")
    ikisi = [a for a, mm in D.items() if mm["eurgbp"]["b"]["spr"] < 0 and abs(mm["eurgbp"]["t"]["spr"]) >= 1.96]
    dogru(ikisi == ["2010–2012"], f"sterline karşı eksi ve anlamlı katsayı yalnız 2010–2012'de değil: {ikisi}")
    dogru(all(mm["eurchf"]["b"]["spr"] < 0 for mm in D.values()) and len(D) == 6,
          "franka karşı katsayı altı dönemin altısında eksi değil")
    fr13, fr20 = sg["frank"]["2013–2019"], sg["frank"]["2020–2023"]
    metinde(f"(21 Ocak 2015, EUR/CHF {yz(sg['snb_2015']['eurchf'], 2, True)})", "SNB 2015")
    metinde(f"bu hafta çıkarılınca katsayı {yz(fr13['snb_haric']['b']['spr'] * 10, 2, True)} (t "
            f"{sayi(fr13['snb_haric']['t']['spr'], 1)}), VIX sabit tutulunca da {yz(fr13['snb_haric_vix']['b']['spr'] * 10, 2, True)} "
            f"(t {sayi(fr13['snb_haric_vix']['t']['spr'], 1)})", "frank 2013–19")
    dogru(fr13["snb_haric"]["n"] == fr13["tam"]["n"] - 1, "2013–2019 frank sınamasında SNB haftası sayısı tutmuyor")
    metinde(f"2020–2023'te zaten anlamlı ({yz(fr20['tam']['b']['spr'] * 10, 2, True)}, t {sayi(fr20['tam']['t']['spr'], 1)}), "
            f"ama VIX eklenince {yz(fr20['vix']['b']['spr'] * 10, 2, True)}'e (t {sayi(fr20['vix']['t']['spr'], 1)}) iniyor",
            "frank 2020–23")
    f04f = sg["frank"]["2004–2026"]
    metinde(f"VIX'in katsayısı EUR/GBP'de artı (2004–2026, t {sayi(f04f['gbp_vix']['t']['vix'], 1, True)})", "VIX sterlin")
    metinde(f"aynı katsayı EUR/CHF'de eksi (t {sayi(f04f['vix']['t']['vix'], 1)})", "VIX frank")
    dis("6 Eylül 2011 – 15 Ocak 2015 arasında kur SNB'nin 1,20 tabanındaydı", "SNB, taban kuru")
    e10, e10c = D["2010–2012"]["eurgbp_it"], D["2010–2012"]["eurchf_it"]
    metinde(f"EUR/GBP'de Fransa'nın katsayısı kayboluyor ({yz(e10['b']['spr'] * 10, 2, True)}, t {sayi(e10['t']['spr'], 1)}) "
            f"ve İtalya'nınki kalıyor: İtalya farkındaki 10 bp'lik açılmaya EUR/GBP'de {yz(e10['b']['ispr'] * 10, 2, True)} "
            f"eşlik ediyor (t {sayi(e10['t']['ispr'], 1)})", "2010–12 İtalya")
    metinde(f"franka karşı bu sonucu doğrulamıyor ({yz(e10c['b']['ispr'] * 10, 2, True)}, t {sayi(e10c['t']['ispr'], 1, True)})",
            "2010–12 frank İtalya")
    e13c, e13g = D["2013–2019"]["eurchf_it"], D["2013–2019"]["eurgbp_it"]
    metinde(f"Frankta İtalya katsayısı 2013–2019'da eksi ve anlamlı ({yz(e13c['b']['ispr'] * 10, 2, True)}, t "
            f"{sayi(e13c['t']['ispr'], 1)}), sterlinde ters işaretli ({yz(e13g['b']['ispr'] * 10, 2, True)}, t "
            f"{sayi(e13g['t']['ispr'], 1, True)})", "2013–19 İtalya")
    x13 = sg["frank"]["2013–2019"]["it_snb_haric"]
    metinde(f"SNB haftası dışarıda bırakılıp İtalya farkı eklenince frankta Fransa katsayısı "
            f"{yz(fr13['snb_haric']['b']['spr'] * 10, 2, True)}'dan {yz(x13['b']['spr'] * 10, 2, True)}'ye (t "
            f"{sayi(x13['t']['spr'], 1)}) iniyor", "2013–19 frank İtalya ve SNB")
    dogru(abs(x13["t"]["spr"]) < 1.96 and x13["t"]["ispr"] <= -1.96, "2013–19 frank bağı İtalya'ya geçmiyor")
    e24g, e24c = d24["eurgbp_it"], d24["eurchf_it"]
    metinde(f"2024–2026'da sterlinde {yz(e24g['b']['ispr'] * 10, 2, True)} (t {sayi(e24g['t']['ispr'], 1, True)}), frankta "
            f"{yz(e24c['b']['ispr'] * 10, 2, True)} (t {sayi(e24c['t']['ispr'], 1)})", "2024–26 İtalya")
    dogru(abs(e24g["t"]["ispr"]) < 1.96 and abs(e24c["t"]["ispr"]) < 1.96 and e24g["b"]["ispr"] * e24c["b"]["ispr"] < 0,
          "2024–2026 İtalya katsayıları 'anlamsız ve zıt işaretli' değil")
    ec = d24["ecb"]
    metinde(f"faiz farkının katsayısı {yz(ec['b']['rd'] * 10, 2, True)}'e (t {sayi(ec['t']['rd'], 1)}) iniyor ve fark kuru "
            f"faiz farkından daha iyi açıklıyor gibi görünüyor ({yz(ec['b']['spr'] * 10, 2, True)}, t {sayi(ec['t']['spr'], 1)})",
            "ECB kuru sağlamlık")
    od = o["orneklem_disi"]
    dogru(all(od["fx"][x]["faiz+fr"]["r2_dis"] > od["fx"][x]["faiz"]["r2_dis"] for x in od["fx"]),
          "EUR/USD örneklem dışı payı üç sınamada da artmıyor")
    dogru(sum(od["fx"][x]["esli_t"] > 1.96 for x in od["fx"]) == 2, "'ikisinde anlamlı' tutmuyor")
    dogru(sum(od["gbpusd"][x]["esli_t"] > od["fx"][x]["esli_t"] for x in od["fx"]) == 2,
          "'GBP/USD'de iki sınamada daha güçlü' tutmuyor")
    dogru(all(od["eurgbp"][x]["esli_t"] < 1.96 for x in od["fx"]), "EUR/GBP'de örneklem dışı iyileşme var")
    metinde(f"2024–2026 sınamalarında eksi ({sayi(od['eurgbp']['2004_2023']['faiz+fr']['r2_dis'], 2)} ve "
            f"{sayi(od['eurgbp']['2013_2023']['faiz+fr']['r2_dis'], 2)})", "EUR/GBP örneklem dışı R²")
    kk_ = o["kayan"]
    metinde(f"EUR/USD'nin duyarlılığı {yz(kk_['son'], 2, True)} (bant {yz(kk_['son_alt'], 2, True)} ile "
            f"{yz(kk_['son_ust'], 2, True)}), EUR/GBP'ninki {yz(kk_['eurgbp_son'], 2, True)} (bant "
            f"{yz(kk_['eurgbp_son_alt'], 2, True)} ile {yz(kk_['eurgbp_son_ust'], 2, True)})", "kayan")
    dogru(kk_["son_tarih"] == "2026-09-30", "kayan pencerenin son haftası 30 Eylül değil")
    metinde(f"haftasında fark {bp(sh['spr'], 1, True)} açılırken GBP/USD {yz(sh['gbpusd'], 2, True)}, EUR/GBP "
            f"{yz(sh['eurgbp'], 2, True)} hareket etti", "kayan salgın haftası")
    dogru(kk_["salgin_giris"]["eurgbp"][1] - kk_["salgin_giris"]["eurgbp"][0] > 0.5
          and kk_["salgin_cikis"]["eurgbp"][0] - kk_["salgin_cikis"]["eurgbp"][1] > 0.5,
          "EUR/GBP çizgisinde salgın haftasının giriş/çıkış basamağı yok")
    pk = kk_["pozitif_kosular"]
    dogru(len(pk) == 2, f"pozitif koşu sayısı {len(pk)}")
    metinde(f"{ay_yil(pk[0][0])} ile {ay_yil(pk[0][1])} arasında ve {ay_yil(pk[1][0])} ile {ay_yil(pk[1][1])} arasında",
            "pozitif koşular")
    at = {y: o["atif"]["eylul"][y] for y in ("fx", "gbpusd", "eurgbp", "eurchf")}
    metinde(f"(Ocak 2024 – Haziran 2026, {at['fx']['katsayi']['n']} hafta)", "atıf tahmin penceresi")
    dogru(at["fx"]["katsayi"]["son"] < at["fx"]["bas"] and at["fx"]["bas"] == "2026-08-31", "atıf penceresi örneklem içi")
    metinde(f"EUR/USD'nin {yz(at['fx']['kur_gercek'], 2, True)}'lik kaybı şöyle ayrışıyor: fark kanalı "
            f"{yz(at['fx']['spread_payi'], 2, True)}, faiz kanalı {yz(at['fx']['faiz_payi'], 2, True)}, sabit "
            f"{yz(at['fx']['sabit_payi'], 2, True)}, kalan {yz(at['fx']['artik'], 2, True)}", "atıf EUR/USD")
    metinde(f"\"Fransa kanalı\" GBP/USD'ye {yz(at['gbpusd']['spread_payi'], 2, True)} yazıyor (10 bp başına "
            f"{yz(at['gbpusd']['katsayi']['b']['spr'] * 10, 2, True)}; EUR/USD'de {yz(at['fx']['katsayi']['b']['spr'] * 10, 2, True)}); "
            f"GBP/USD'nin kendisi {yz(at['gbpusd']['kur_gercek'], 2, True)} düştü", "atıf GBP/USD")
    dogru(abs(at["gbpusd"]["spread_payi"]) > abs(at["gbpusd"]["kur_gercek"]), "sterlinin bütün kaybından fazlası değil")
    metinde(f"fark kanalına EUR/GBP'de {yz(at['eurgbp']['spread_payi'], 2, True)} (gerçekleşen "
            f"{yz(at['eurgbp']['kur_gercek'], 2, True)}), EUR/CHF'de {yz(at['eurchf']['spread_payi'], 2, True)} (gerçekleşen "
            f"{yz(at['eurchf']['kur_gercek'], 2, True)}) yazıyor", "atıf çaprazlar")
    metinde(f"31 Ağustos → 1 Ekim, ölçülen: EUR/USD {yz(at['fx']['kur_gercek'], 2, True)}, GBP/USD "
            f"{yz(at['gbpusd']['kur_gercek'], 2, True)}, EUR/GBP {yz(at['eurgbp']['kur_gercek'], 2, True)}, EUR/CHF "
            f"{yz(at['eurchf']['kur_gercek'], 2, True)}", "atıf ölçülen")
    for y, kol in (("fx", "fx"), ("gbpusd", "dolar_gbp"), ("eurgbp", "eurgbp"), ("eurchf", "eurchf")):
        dogru(abs(at[y]["kur_gercek"] - ey[kol]) < 0.006, f"atıfın ölçülen kuru çapraz tablosuyla aynı değil: {y}")
    ad_ = o["atif_duyarlilik"]
    eksi = [r["egitim"] for r in ad_["eurgbp"] if r["spread_payi"] < 0]
    dogru(eksi == ["2010-01-06–2012-12-26"], f"EUR/GBP fark kanalı eksi olan tek dönem 2010–2012 değil: {eksi}")
    ch = ad_["eurchf"]
    dogru(all(r["spread_payi"] < 0 for r in ch), "frankta fark kanalı beş dönemin beşinde eksi değil")
    metinde(f"frankta beş tahmin döneminin beşinde de eksi ({yz(max(r['spread_payi'] for r in ch), 2, True)} ile "
            f"{yz(min(r['spread_payi'] for r in ch), 2, True)}), ama hiçbirinde katsayı anlamlı değil (|t| en çok "
            f"{sayi(max(abs(r['t_spr']) for r in ch), 1)})", "atıf frank")
    dogru(max(abs(r["t_spr"]) for r in ch) < 1.96, "frank atıf katsayılarından biri anlamlı")
    # gün içi
    dogru(all(gq[c]["dakika_kalan"] == [1] for c in ("fr10y", "de10y", "it2y", "de2y", "eurusd"))
          and gq["us2y"]["dakika_kalan"] == [0],
          "gün içi kotasyon dakikaları 'Avrupa ve EUR/USD 1/6, ABD 0/5' değil")
    metinde(f"Fransa farkı {sayi(p['spr']['bas'])}'dan {bp(p['spr']['son'])}'ye ({sayi(p['spr']['degisim'], 1, True)}), "
            f"İtalya'nın 2 yıllık farkı {sayi(p['ispr2']['bas'])}'dan {bp(p['ispr2']['son'])}'ye "
            f"({sayi(p['ispr2']['degisim'], 1, True)}) çıktı. ABD 2 yıllığı {bp(p['us2y']['degisim_bp'])}, Almanya 2 yıllığı "
            f"{bp(p['de2y']['degisim_bp'])} düştü; ABD–Almanya 2 yıllık farkı {bp(p['rd']['degisim'], 1, True)} açıldı. "
            f"Euro aynı iki saatte {sayi(p['eurusd']['bas'], 4)}'ten {sayi(p['eurusd']['son'], 4)}'e, "
            f"{yz(p['eurusd']['degisim_yuzde'], 2, True)} geriledi", "gün içi pencere")
    a1, a2, a3 = o["gun_ici_1530_1545"], o["gun_ici_ism"], o["gun_ici_pencere_1600"]
    metinde(f"Faiz farkının iki saatlik {bp(p['rd']['degisim'], 1, True)}'si üç adımda geldi: 15:30–15:45 "
            f"{bp(a1['rd']['degisim'], 1, True)}, 15:45–16:00 {bp(a2['rd']['degisim'], 1, True)}, 16:00–17:30 "
            f"{bp(a3['rd']['degisim'], 1, True)}", "faiz farkı adımları")
    dogru(abs(a1["rd"]["degisim"] + a2["rd"]["degisim"] + a3["rd"]["degisim"] - p["rd"]["degisim"]) < 0.06,
          "faiz farkının üç adımı iki saatlik değişime toplanmıyor")
    iq = o["ism_kotasyon"]["us2y"]
    metinde(f"ABD 2 yıllığı 15:55'teki %{sayi(iq['15:55']['deger'], 3)}'den 16:00'da %{sayi(iq['16:00']['deger'], 3)}'e "
            f"sıçradı, 16:05'te %{sayi(iq['16:05']['deger'], 3)}'ya döndü ve 16:15'te 15:45'teki seviyesinin altındaydı "
            f"(%{sayi(iq['16:15']['deger'], 3)}'a karşı %{sayi(iq['15:45']['deger'], 3)})", "ISM kotasyonları")
    dogru(iq["16:15"]["deger"] < iq["15:45"]["deger"] and all(iq[x]["dakika"] == x for x in iq), "ISM kotasyon okuması tutmuyor")
    b4 = o["gun_ici_1545_1615"]
    metinde(f"15:45 → 16:15 arasında faiz farkının {bp(b4['rd']['degisim'], 1, True)}'lik açılmasının tamamı Alman 2 "
            f"yıllığının düşüşüydü ({bp(b4['de2y']['degisim_bp'], 1, True)}; bunun {bp(a2['de2y']['degisim_bp'], 1, True)}'si "
            f"veriden önce). Euro aynı yarım saatte kımıldamadı ({yz(b4['eurusd']['degisim_yuzde'], 2, True)}); euronun "
            f"15:45 → 16:00 adımındaki {yz(a2['eurusd']['degisim_yuzde'], 2, True)} ise verinin öncesidir (15:56 kotasyonu)",
            "ISM çeyreği")
    dogru(abs(b4["us2y"]["degisim_bp"]) < 0.5 and abs(b4["eurusd"]["degisim_yuzde"]) < 0.05
          and gq["eurusd"]["dakika_kalan"] == [1],
          "'faiz farkı açılmasının tamamı Alman 2 yıllığı / euro kımıldamadı / euro 1-6 dakikalarında' tutmuyor")
    c5 = o["gun_ici_1615"]
    metinde(f"16:15'ten 17:30'a faiz farkı yalnız {bp(c5['rd']['degisim'], 1, True)} oynarken Fransa farkı "
            f"{bp(c5['spr']['degisim'], 1, True)} açıldı ve euro {yz(c5['eurusd']['degisim_yuzde'], 2, True)} geriledi; bu "
            f"açılmanın tamamına yakını Bund'un {bp(c5['de10y']['degisim_bp'], 1, True)}'lik düşüşü, Fransa 10 yıllığı yatay "
            f"({bp(c5['fr10y']['degisim_bp'], 1, True)})", "16:15 sonrası")
    metinde(f"günlük kapanışlar 1 Ekim'de euronun sterline karşı {yz(c30['eurgbp'], 2, True)}, franka karşı "
            f"{yz(c30['eurchf'], 2, True)} düştüğünü", "gün içi çaprazlar")
    g5 = o["gun_ici_bes_gun"]
    kt, k1 = g5["kontrollu"], g5["kontrollu_1ekim_haric"]
    metinde(f"EUR/USD'de {yz(kt['b']['spr'], 3, True)} eşlik ediyor (t {sayi(kt['t']['spr'], 1)}; {kt['n']} gözlem); "
            f"1 Ekim çıkarılınca {yz(k1['b']['spr'], 3, True)} (t {sayi(k1['t']['spr'], 1)})", "gün içi regresyon")
    pz = {r["kod"]: r for r in o["piyasalar"]}
    dogru(all(r["bas_gun"] == "2026-08-31" for r in o["piyasalar"]), "öbür piyasaların başlangıcı 31 Ağustos değil")
    metinde(f"CAC 40 {yz(pz['cac']['degisim'], 2, True)}, DAX {yz(pz['dax']['degisim'], 2, True)}, Euro Stoxx 50 "
            f"{yz(pz['sx5e']['degisim'], 2, True)}; Fransız bankaları BNP Paribas {yz(pz['bnp']['degisim'], 2, True)}, "
            f"Société Générale {yz(pz['socgen']['degisim'], 2, True)}, Crédit Agricole {yz(pz['cagri']['degisim'], 2, True)}",
            "hisseler")
    metinde(f"Euro dolara karşı {yz(ey['fx'], 2, True)} düşerken yene karşı {yz(pz['eurjpy']['degisim'], 2, True)}, sterline "
            f"karşı {yz(pz['eurgbp']['degisim'], 2, True)}, franka karşı {yz(pz['eurchf']['degisim'], 2, True)} kaybetti; dolar "
            f"endeksi {yz(pz['dxy']['degisim'], 2, True)}", "çaprazlar")
    dogru(abs(pz["eurgbp"]["degisim"] - ey["eurgbp"]) < 1e-6 and abs(pz["eurchf"]["degisim"] - ey["eurchf"]) < 1e-6,
          "öbür piyasalar çaprazları ayrıştırmayla aynı değil")
    dis("~52 bp ile Nisan 2017'den beri en yüksekte", "Reuters, 24 Eylül")
    metinde(f"CAC 40 DAX'tan {sayi(pz['dax']['degisim'] - pz['cac']['degisim'], 1)} puan fazla düştü", "CAC–DAX")
    # ── Bölüm 5
    metinde(f"2026 satırının açılması 15 Haziran'ın gösterge değişimini ({bp(sv['epizot_gosterge_payi'], 1, True)}) de taşır",
            "epizot tablosu notu")
    olay_bas = [r for r in o["epizotlar"] if r["ad"] not in ("2011 euro bölgesi borç krizi", "2026")]
    eb = max(olay_bas, key=lambda r: r["acilma"])
    dogru(eb["ad"] == "2020 salgın", f"olay günüyle başlayan en büyük öbür açılma 2020 değil: {eb['ad']}")
    dogru(abs(ep["2026"]["acilma"] - sv["epizot_degisim"]) < 0.05, "2026 epizot satırı seviye ölçüsüyle aynı değil")
    metinde(f"açılmanın {bp(sv['epizot_gosterge_payi'], 1, True)}'si 15 Haziran'ın gösterge değişimi. Gösterge payı "
            f"düşülünce {bp(sv['epizot_degisim_gostergesiz'])} kalıyor; başlangıç yılın dibi yerine 30 Haziran alınınca "
            f"{bp(sv['degisim_haziran'], 1, True)}, 31 Ağustos alınınca {bp(sv['degisim_agustos'], 1, True)}. Üçü de olay "
            f"günüyle başlayan en büyük öbür açılmanın ({bp(eb['acilma'])}, 2020) üstünde", "büyüklük")
    dogru(min(sv["epizot_degisim_gostergesiz"], sv["degisim_haziran"], sv["degisim_agustos"]) > eb["acilma"]
          and sv["tarih_haziran"] > max(sv["epizot_gosterge_gunleri"]) and sv["tarih_haziran"] == "2026-06-30"
          and sv["tarih_agustos"] == "2026-08-31",
          "gösterge payı düşülünce / 30 Haziran ya da 31 Ağustos'tan ölçülünce 2026 2020'nin altında ya da gösterge gününü içeriyor")
    e11 = ep["2011 euro bölgesi borç krizi"]
    metinde(f"aynı pencerede İtalya'nın farkı {bp(e11['it_bp'], 1, True)} açıldı, bu yıl {bp(ep['2026']['it_bp'], 1, True)}",
            "2011 İtalya")
    e10_ = ep["2010 Yunanistan"]
    metinde(f"Euro sterline karşı 2010'da {yz(e10_['eurgbp_yuzde'], 2, True)}, 2011'de {yz(e11['eurgbp_yuzde'], 2, True)}, "
            f"franka karşı 2010'da {yz(e10_['eurchf_yuzde'], 2, True)} kaybetti; olağan oynaklığa göre sterlin kayıpları "
            f"yaklaşık bir standart sapma ({sayi(e10_['eurgbp_z'], 1, True)}σ ve {sayi(e11['eurgbp_z'], 1, True)}σ)",
            "kriz epizotları")
    metinde(f"2010'un frank kaybı ise aynı ölçekle {sayi(e10_['eurchf_z'], 1, True)}σ", "2010 frank ölçeği")
    dogru(abs(e10_["eurchf_z"]) > 2 > max(abs(e10_["eurgbp_z"]), abs(e11["eurgbp_z"])), "'sterline karşı ölçek küçük, frank büyük' tutmuyor")
    dis("SNB 6 Eylül 2011'de 1,20 tabanını koydu", "SNB, 6 Eylül 2011")
    e17_, ef_, eby = ep["2017 cumhurbaşkanlığı seçimi"], ep["2024 meclisin feshi"], ep["2025 Bayrou güven oylaması"]
    metinde(f"2017 sterline {yz(e17_['eurgbp_yuzde'], 2, True)}, franka {yz(e17_['eurchf_yuzde'], 2, True)}; 2024 fesih "
            f"{yz(ef_['eurgbp_yuzde'], 2, True)} ve {yz(ef_['eurchf_yuzde'], 2, True)}; Bayrou {yz(eby['eurgbp_yuzde'], 2, True)} "
            f"ve {yz(eby['eurchf_yuzde'], 2, True)}", "Fransa epizotları")
    sp_ = dict(zip(o["seriler"]["spread"]["t"], o["seriler"]["spread"]["v"]))
    metinde(f"2017'de fark 21 Şubat'taki {bp(e17_['zirve'])} zirvesinden marta geriledi, nisan ortasında yeniden o zirvenin "
            f"hemen altına çıktı ve birinci turdan önceki son iş günü (21 Nisan) {bp(l17['spr_once'])}'deydi; birinci tur "
            f"sonucu bir günde {bp(l17['spr'], 1, True)} daha getirdi", "2017 seçim öncesi")
    dogru(e17_["zirve_gun"] == "2017-02-21" and l17["once"] == "2017-04-21"
          and min(v for t, v in sp_.items() if t[:7] == "2017-03") < e17_["zirve"] - 15
          and max(v for t, v in sp_.items() if "2017-04-10" <= t <= "2017-04-21") >= e17_["zirve"] - 1,
          "2017: şubat zirvesi / marttaki geri çekilme / nisan ortasında zirve yakını / 21 Nisan tutmuyor")
    metinde(f"2008 ve 2020'de euro sterline karşı kazandı ({yz(ep['2008 küresel finans krizi']['eurgbp_yuzde'], 2, True)}, "
            f"{yz(ep['2020 salgın']['eurgbp_yuzde'], 2, True)})", "2008-2020")
    ay = o["ayrisma"]
    metinde(f"2025'in ilk yarısında ({tarih_ga(ay['y2025']['bas'])} → {tarih_ga(ay['y2025']['son'])}) euro dolara karşı "
            f"{yz(ay['y2025']['fx'], 2, True)} kazanırken fark yalnız {bp(ay['y2025']['spr_bas'] - ay['y2025']['spr_son'])} "
            "daraldı", "2025 ayrışması")
    metinde(f"fark {ef_['is_gunu']} iş gününde {bp(ef_['acilma'], 1, True)} açıldı, bir ayda kısmen geri döndü ve fesih "
            f"öncesindeki {bp(ay['fesih_once'])}'ye bir daha hiç inmedi; ondan sonraki en düşük kapanış bu yılın dibi, "
            f"{bp(ay['fesih_sonrasi_dip'])}", "fesih primi")
    dogru(ay["fesih_sonrasi_dip_gun"] == sv["yil_dibi_gun"], "fesih sonrası dip bu yılın dibi değil")
    dn = o["donus_2011"]
    ed = dn["en_buyuk_daralma"]
    metinde(f"fark {dn['dip_is_gunu']} iş gününde {bp(dn['zirve'])}'den {bp(dn['dip'])}'ye indi. En büyük üç günü "
            f"{tarih_ga(ed[0][0])} ({bp(ed[0][1], 1, True)}), {tarih_ga(ed[1][0])} ({sayi(ed[1][1], 1, True)}) ve "
            f"{tarih_ga(ed[2][0])} ({sayi(ed[2][1], 1, True)})", "2011 dönüşü")
    dogru(dn["zirve_gun"] == sv["tarihi_zirve_gun"] and dn["zirve"] == sv["tarihi_zirve"], "2011 dönüşünün zirvesi tarihî zirve değil")
    metinde(f"8 Aralık'ta fark {bp(oy_['ECB: üç yıllık LTRO']['spr'], 1, True)} açıldı ve {gun(dn['son_gun'])}'de yeniden "
            f"{bp(dn['son'])}'deydi", "LTRO")
    # olay günleri
    dogru(len(notlar) == 15 and sum(1 for r in notlar if r["karisik"]) == 1, "not kararları on beş / biri karışık değil")
    metinde(f"tablodaki on beş not kararının on dördünde fark tepki gününde {sayi(min(r['spr'] for r in on4), 1, True)} ile "
            f"{bp(max(r['spr'] for r in on4), 1, True)} arasında oynadı", "not aralığı")
    kar = next(r for r in notlar if r["karisik"])
    metinde(f"on beşincisi, S&P'nin {gun(kar['once'])} teyidi ({bp(kar['spr'], 1, True)}), Barnier'nin 49.3'e başvurduğu güne "
            "denk geliyor", "karışık not günü")
    aa = o["aaa_2012"]
    metinde(f"haber 13 Ocak seansında sızdı ve fark o gün {bp(aa['sizma']['fr'], 1, True)} açıldı; aynı gün İspanya ve Belçika "
            f"farkları da {sayi(aa['sizma']['es'], 1, True)} ve {bp(aa['sizma']['be'], 1, True)} açıldı", "AAA sızma")
    dogru(aa["sizma"]["sonra"] == "2012-01-13" and oy_["S&P: Fransa AAA → AA+ (haber seans içinde sızdı)"]["spr"] == aa["sizma"]["fr"],
          "AAA satırı sızma günüyle aynı değil")
    metinde(f"Resmî karardan sonraki ilk işlem günü fark {bp(aa['pazartesi']['fr'], 1, True)} geri verdi", "AAA pazartesi")
    omt = oy_["ECB: OMT'nin ayrıntıları"]
    metinde(f"farkı bir günde {sayi(dr['spr'], 1)}, İtalya'yı {bp(dr['it'], 1)} daralttı ve euroyu {yz(dr['fx'], 2, True)} "
            f"yükseltti; OMT'nin ayrıntıları {bp(omt['spr'], 1)}", "Draghi")
    buyuk = max(o["olay_tepkileri"], key=lambda r: abs(r["spr"]))
    dogru(buyuk["ad"] == "2026: 2027 bütçe tasarısı", f"tablodaki en büyük tek günlük hareket {buyuk['ad']}")
    metinde(f"Tablodaki en büyük tek günlük hareket ise 1 Ekim 2026: {bp(buyuk['spr'], 1, True)}", "en büyük olay")
    metinde(f"fark {bp(l17['spr'], 1, True)} daraldı, euro dolara karşı {yz(l17['fx'], 2, True)}, sterline karşı "
            f"{yz(l17['eurgbp'], 2, True)} kazandı", "2017")
    dogru(l17["eurgbp"] >= l17["fx"], "2017'de 'hareketin tamamı euroya özgü' tutmuyor")
    bar, bay, lec = (oy_["2024: Barnier gensoruyla düştü"], oy_["2025: Bayrou hükümeti düştü"], oy_["2025: Lecornu istifa etti"])
    fes, but = oy_["2024: meclisin feshi"], oy_["2026: 2027 bütçe tasarısı"]
    metinde(f"fark {bp(bar['spr'], 1, True)} daraldı; Bayrou hükümetinin düşüşü {sayi(bay['spr'], 1, True)}, Lecornu'nun "
            f"istifası {bp(lec['spr'], 1, True)} açtı ve iki olayda da euro sterline karşı düştü ({yz(bay['eurgbp'], 2, True)} "
            f"ve {yz(lec['eurgbp'], 2, True)}). Feshin hafta sonunda euro sterline karşı {yz(fes['eurgbp'], 2, True)}, 2027 "
            f"bütçe tasarısının gününde {yz(but['eurgbp'], 2, True)} kaybetti", "hükümet düşüşleri")
    dogru(lec["zaman"] == "gun" and lec["once"] == "2025-10-03" and lec["sonra"] == "2025-10-06",
          "Lecornu penceresi cumadan pazartesiye değil")
    c54, csc = oy_["2026: 54 mlr € çaba açıklandı"], oy_["Scope: AA− → A+; DBRS: eğilim negatife"]
    metinde(f"54 milyarın açıklandığı akşam ise fark {bp(c54['spr'], 1, True)} açılırken euro sterline karşı "
            f"{yz(c54['eurgbp'], 2, True)}, dolara karşı {yz(c54['fx'], 2, True)} kazandı", "54 milyar istisnası")
    dogru(c54["spr"] > 0 and c54["eurgbp"] > 0 and c54["fx"] > 0
          and yz(oy_["2026: Le Pen istinaf kararı"]["eurgbp"], 2) == "%0,00", "54 milyar istisnası / Le Pen kımıldamadı tutmuyor")
    metinde(f"54 milyarın kur penceresi {int(c54['kur_once'][8:])} → {int(c54['sonra'][8:])} Eylül, Scope'unki "
            f"{int(csc['kur_once'][8:])} → {int(csc['sonra'][8:])} Eylül", "örtüşen pencereler")
    # ── Bölüm 7
    metinde(f"standart sapması {bp(oy['sigma_gunluk'], 2)}; 2013'ten bu yana standart sapma {bp(oy['sigma_2013_temiz'], 2)} "
            f"(gösterge kâğıt değişimi ve veri boşluğu günleri dışarıda) — {sayi(oy['oran_temiz'], 1)} katı", "oynaklık")
    metinde(f"±1,96σ bandı ±{bp(oy['bant_1a'])}", "bant")
    dogru(abs(oy["bant_1a"] - 1.96 * oy["sigma_gunluk"] * 22 ** 0.5) < 0.05, "bant 1,96·σ·√22 değil")
    metinde(f"bir ay sonrası için {sayi(oy['spread'] - oy['bant_1a'], 0)}–{sayi(oy['spread'] + oy['bant_1a'], 0)} bp'lik bir "
            "banda karşılık gelir", "bant uçları")
    dogru(il["p10"] < 0, "ileri dağılımın onda biri daralma değil")
    metinde(f"önceki açılması 30 bp'yi aşan {il['gozlem']} gözlem", "ileri gözlem")
    acilan = il["daha_acilan_gozlem"]
    dogru(len(acilan) == round(il["daha_acildi_payi"] * il["gozlem"] / 100) == 7, "daha açılan gözlem sayısı yedi değil")
    alt1 = sorted([x for x in acilan if x[1] <= 1], key=lambda x: -x[1])
    ust1 = [x for x in acilan if x[1] > 1]
    metinde(f"ertesi ay medyanda {bp(il['medyan'], 1, True)} geriledi; gözlemlerin {yz(il['daha_acildi_payi'], 1)}'inde "
            f"({il['gozlem']}'in {len(acilan)}'si) daha da açıldı, onda birinde {bp(abs(il['p10']), 1)}'den fazla daraldı. "
            f"Daha da açılan yedi gözlemin ikisi 1 bp'nin altında ({sayi(alt1[0][1], 1, True)} ve "
            f"{sayi(alt1[1][1], 1, True)}); 1 bp'den fazla açılanların payı {yz(il['daha_acildi_1bp_payi'], 1)} ve beşi de "
            f"{int(ust1[0][0][8:])}–{int(ust1[-1][0][8:])} {ay_yil(ust1[0][0])}'den", "ileri dağılım")
    dogru(len(alt1) == 2 and len(ust1) == 5 and all(x[0][:7] == "2011-10" for x in ust1), "1 bp ayrımı tutmuyor")
    dogru(il["epizot"] == 7 and il["medyani_artida_kume"] == 0, "yedi kümenin her birinin medyanı gerilemedi")
    dogru(il["kriz_disi_daha_acilan"] == 0 and il["kriz_disi_gozlem"] == 11,
          "'daha da açılan yedi gözlemin yedisi 2011–12'den / 11 gözlem' tutmuyor")
    km = il["kumeler"]
    k11 = next(c for c in km if c["bas"].startswith("2011-10"))
    k12 = next(c for c in km if c["bas"].startswith("2012-04"))
    metinde(f"({k11['n']} gözlemin {k11['daha_acilan']}'sı) ve Nisan–Mayıs 2012 ({k12['n']} gözlemin {k12['daha_acilan']}'i)",
            "açılan kümeler")
    metinde(f"2011–12 dışındaki {il['kriz_disi_gozlem']} gözlemin hiçbirinde", "kriz dışı")
    metinde(f"22 iş günündeki {bp(h['10y_22']['degisim'], 1, True)}'yi aşan açılma yalnız Kasım 2011 ile Ocak 2012 "
            f"arasında görüldü ve o sekiz gözlemin hepsinde fark ertesi ay "
            f"{sayi(-max(c['ileri_maks'] for c in ilb['kumeler']), 1)} ile {sayi(-min(c['ileri_min'] for c in ilb['kumeler']), 1)} "
            "bp arasında daraldı", "bugünkü hız")
    dogru(ilb["gozlem"] == 8 and ilb["daha_acildi_payi"] == 0, "bugünkü hız eşiği: sekiz gözlem / hiçbiri açılmadı tutmuyor")
    metinde(f"medyan {bp(il66['medyan'], 1, True)}, ama gözlemlerin {yz(il66['daha_acildi_payi'], 1)}'sı daha açık ve yedi "
            "kümenin üçünde", "66 gün")
    dogru(il66["daha_acilan_kume"] == 3, "66 günde daha açılan küme sayısı üç değil")
    metinde(f"dört gözlemin dördünde {sayi(a11['ileri_min'], 1, True)} ile {bp(a11['ileri_maks'], 1, True)} daha açıktı "
            f"(medyan {bp(a11['ileri_medyan'], 1, True)})", "Ağustos 2011")
    st_ = o["seriler"]["spread"]["t"]
    k17 = next(c for c in km if c["bas"].startswith("2017-02"))
    dogru(st_[st_.index(k12["son"]) + 22] < "2012-07-26" and st_[st_.index(k17["son"]) + 22] < "2017-04-23",
          "Nisan–Mayıs 2012 / Şubat 2017 kümelerinin ertesi ayı Draghi'den / birinci turdan önce bitmiyor")
    metinde(f"Bu serideki tarihî zirve {bp(sv['tarihi_zirve'])} ({gun(sv['tarihi_zirve_gun'])})", "referans zirve")
    metinde(f"2 yıllık farkın 2011 zirvesi {bp(eg['2']['zirve'])} (bugün {sayi(eg['2']['spread'])})", "2y zirve")
    dogru(all(eg[v_]["zirve_gun"] == sv["tarihi_zirve_gun"] for v_ in ("2", "5", "10", "30")),
          "dört vadenin zirve günü 10 yıllıkla aynı değil")
    dis("MUFG 24 Eylül'de 1,1340'ı kilit destek olarak gösterip kırılırsa 1,10–1,12 bölgesini", "FXStreet, MUFG notu")
    dis("ABD verisi güçlü kalırsa 1,11–1,12 bölgesini", "FXStreet, ING notu")
    metinde(f"1 Ekim'in New York kapanışı {sayi(k['son'], 4)}.", "kur referans")
    metinde(f"(EUR/GBP'de {yz(d24['eurgbp']['b']['spr'] * 10, 2, True)}, t {sayi(d24['eurgbp']['t']['spr'], 1, True)}; "
            f"EUR/CHF'de {yz(d24['eurchf']['b']['spr'] * 10, 2, True)}, t {sayi(d24['eurchf']['t']['spr'], 1, True)}); "
            f"EUR/USD'deki {yz(d24['faiz+fr']['b']['spr'] * 10, 2, True)} sterlinde de var", "aritmetik yok")
    dogru(abs(d24["eurgbp"]["t"]["spr"]) < 1.96 and abs(d24["eurchf"]["t"]["spr"]) < 1.96, "2024–2026'da euroya özgü katsayı anlamlı")
    tah = e10["b"]["ispr"] * e2c["ispr"]
    metinde(f"İtalya farkındaki 10 bp'lik açılmaya EUR/GBP'de {yz(e10['b']['ispr'] * 10, 2, True)} eşlik ediyordu. İkinci "
            f"evrede İtalya farkı {bp(e2c['ispr'], 1, True)} açıldı; bu katsayıyla {yz(tah, 2, True)}, gerçekleşen "
            f"{yz(e2c['eurgbp'], 2, True)}", "İtalya aritmetiği")
    metinde(f"Bugünkü rejimde aynı katsayı ters işaretli ve anlamsız ({yz(d24['eurgbp_it']['b']['ispr'] * 10, 2, True)}, t "
            f"{sayi(d24['eurgbp_it']['t']['ispr'], 1, True)})", "İtalya katsayısı bugün")
    dogru(all(not (mm["eurgbp_it"]["b"][k_] < 0 and abs(mm["eurgbp_it"]["t"][k_]) >= 1.96)
              for d_, mm in D.items() for k_ in ("spr", "ispr") if not (d_ == "2010–2012" and k_ == "ispr"))
          and D["2010–2012"]["eurgbp_it"]["t"]["ispr"] <= -1.96,
          "İtalya kontrollü sterlin modelinde eksi ve anlamlı tek katsayı 2010–12 İtalya değil")
    # ── Yöntem eki
    metinde(f"Günlük seri {sayi(tz['ham_bar'], 0)} kayıt; {sayi(tz['hafta_sonu_atilan'], 0)} hafta sonu kaydı ve iki bacağın "
            f"birden önceki günü taşıdığı {tz['tasinmis_atilan']} tatil günü atıldı, {sayi(tz['temiz_gun'], 0)} iş günü kaldı",
            "temizlik")
    gc = bo["gecis"]
    metinde(f"boşluğun iki ucundaki farklar (7 Mart 2014'te {bp(gc['2014-03-07']['fark'], 1, True)}, 2 Ocak 2015'te "
            f"{bp(gc['2015-01-02']['fark'], 1, True)})", "boşluk geçişleri")
    metinde(f"Hafta içine düşen {bo['target_tatil']} TARGET tatilinin {bo['target_tatil_seride']}'i seride kalıyor", "TARGET")
    metinde(f"mutlak günlük değişim medyanı {bp(bo['target_tatil_mutlak_medyan'], 1)}", "TARGET medyan")
    gs = h["gosterge_imza"]
    g17, g22a, g22b, g26 = gs["2017-10-09"], gs["2022-11-28"], gs["2022-11-30"], gs["2026-06-15"]
    dogru(sorted(gs) == ["2017-10-09", "2022-11-28", "2022-11-30", "2026-06-15"] and all(abs(x["goreli"]) >= 10 for x in gs.values()),
          "gösterge değişimi listesi ya da göreli imza eşiği tutmuyor")
    metinde(f"9 Ekim 2017'de Fransa 10 yıllığı {bp(g17['fr10y'], 1, True)} sıçrarken 5 yıllığı {sayi(g17['fr5y'], 1, True)}, "
            f"30 yıllığı {bp(g17['fr30y'], 1, True)}, Almanya {bp(g17['de10y'], 1, True)} hareket etti; 28 ve 30 Kasım 2022'de "
            f"aynı imza {sayi(g22a['fr10y'], 1, True)} ve {bp(g22b['fr10y'], 1, True)}. 15 Haziran 2026'da 10 yıllık "
            f"{bp(g26['fr10y'], 1, True)} yükselirken 5 ve 30 yıllık {sayi(g26['fr5y'], 1, True)} ve "
            f"{bp(g26['fr30y'], 1, True)} düştü; fark bir günde {bp(g26['spr'], 1, True)} sıçradı ve sonraki on iş gününde "
            f"{sayi(h['sicrama_2026']['sonraki_on_min'], 1)} ile {bp(h['sicrama_2026']['sonraki_on_maks'], 1)} arasında kaldı",
            "gösterge imzaları")
    dogru(abs(g26["fr10y"]) < 10 and g26["fr5y"] < 0 and g26["fr30y"] < 0,
          "'mutlak bir eşik bu günü kaçırırdı, bütün getirilerin düştüğü gün' tutmuyor")
    dis("(OAT %3,70 Kasım 2036; ilk ihalesi 4 Haziran 2026)", "AFT, yeni 10 yıllık kâğıt")
    g1 = h["10y_1_gercek"]
    dogru(g1["ayiklanan"] == sorted(gs), "tek gün kıyasında ayıklanan günler gösterge listesiyle aynı değil")
    metinde(f"yılın dibinden bu yana açılmanın {bp(sv['epizot_gosterge_payi'], 1, True)}'si 2026 geçişidir", "2026 geçişi")
    metinde(f"1 Ekim'in {bp(g1['degisim'], 1, True)}'lik açılması {gun(g1['son_gorulme'])}'den beri en büyük tek günlük açılma",
            "tek gün")
    s7, s22 = h["sicrama_2017"], h["sicrama_2022"]
    metinde(f"({bp(s22['once'])}'den iki gün sonra {bp(s22['sonra'])})", "2022 sıçrama")
    metinde(f"fark {bp(s7['once'])}'den {bp(s7['gun'])}'ye sıçradı, 20 Ekim'de {bp(s7['on_gun_sonra'])}'deydi", "2017 sıçrama")
    dogru(s7["on_gun_sonra_tarih"] == "2017-10-20", "2017 sıçrama sonrası gözlem günü 20 Ekim değil")
    metinde(f"Kaynağın iki ayrı indirmesinin EUR/USD'si {sayi(kk['eurusd_ortak_gun'], 0)} ortak günde birebir aynı; veri "
            f"gününün kapanışı ({sayi(kk['veri_gunu_bar'], 4)}) gün içi arşivin 23:00 kotasyonundan "
            f"({sayi(kk['veri_gunu_gun_ici_2300'], 4)}) iki puan ayrık", "kur kaynağı")
    dogru(round((kk["veri_gunu_bar"] - kk["veri_gunu_gun_ici_2300"]) * 1e4) == 2, "'iki puan ayrık' tutmuyor")
    metinde(f"kaynağın kendi GBP/USD serisinden medyanda {bp(kk['gbp_ozdeslik_medyan_bp'], 1)} (fiyatın on binde "
            f"{sayi(kk['gbp_ozdeslik_medyan_bp'], 0)}'ü) ayrışıyor", "sentetik GBP/USD medyanı")
    yh = kk["yahoo_eurgbp_gun_medyan_yuzde"]
    obur = [v for g, v in yh.items() if g != "cuma"]
    metinde(f"(EUR/GBP'de medyan {yz(yh['cuma'], 2)}'ye karşı %{sayi(min(obur), 2)}–{sayi(max(obur), 2)})", "Yahoo cuma sapması")
    dogru(1.6 <= yh["cuma"] / (sum(obur) / len(obur)) <= 2.4, "'cuma günleri öbür günlerin iki katı' tutmuyor")
    hz = d24["hazine+fr"]
    metinde(f"(fark {yz(hz['b']['spr'] * 10, 2, True)}, faiz farkı {yz(hz['b']['rdT'] * 10, 2, True)})", "Hazine sağlamlık")
    it24, it04, vx = d24["faiz+fr+it"], D["2004–2026"]["faiz+fr+it"], d24["faiz+fr+vix"]
    metinde(f"Fransa katsayısı {yz(it24['b']['spr'] * 10, 2, True)}'e iner ve anlamlılığını yitirir (t "
            f"{sayi(it24['t']['spr'], 1)}; İtalya'nınki {yz(it24['b']['ispr'] * 10, 2, True)}, t {sayi(it24['t']['ispr'], 1)}",
            "İtalya eklenince 2024–26")
    metinde(f"tüm örneklemde {yz(it04['b']['spr'] * 10, 2, True)}'e (t {sayi(it04['t']['spr'], 1)}) düşer ve açıklayıcılığı "
            f"İtalya farkı alır ({yz(it04['b']['ispr'] * 10, 2, True)}, t {sayi(it04['t']['ispr'], 1)})", "İtalya eklenince tüm")
    metinde(f"VIX eklemek katsayıyı değiştirmez ({yz(vx['b']['spr'] * 10, 2, True)}, t {sayi(vx['t']['spr'], 1)})", "VIX")
    metinde(f"1 Ekim'in tek günü (Bund {sayi(eg['de10y_1g_bp'], 1)}, Fransa {bp(eg['fr10y_1g_bp'], 1, True)}) betayı tek başına "
            f"{sayi(eyl['fr_b'], 2)}'dan {sayi(b['eylul_1ekim']['fr_b'], 2)}'ye indiriyor", "Eylül betası")
    dogru(eyl["n"] == 22 and b["eylul_1ekim"]["n"] == 23, "Eylül beta penceresi 22 gün değil")
    # ── Ne ölçmedik
    metinde(f"Alman 2 yıllığının {bp(ev2['de2y_bp'], 1, True)} düşüşü iki okumayı da destekliyor", "ne ölçmedik 2y")


def bicim(govde: str) -> None:
    g = re.sub(r"\$\$.*?\$\$", "", govde, flags=re.S)
    g = re.sub(r"\$[^$\n]+\$", "", g)
    g = re.sub(r"`[^`]*`", "", g)
    g = re.sub(r"<GrafikEmbed[^>]*/>", "", g)
    for x in re.finditer(r"(?<![\w/.\-–])-%?\d", g):
        hatalar.append(f"ASCII tireli eksi sayı: {g[max(0, x.start() - 30):x.end() + 10]!r}")
    for x in re.finditer(r"\d[ \t]*%", g):
        hatalar.append(f"arkaya yazılmış yüzde: {g[max(0, x.start() - 20):x.end() + 5]!r}")
    sayac["metin"] += 1


# ─────────────────────────────────────────────── 5 · figürler
def figurler(govde: str) -> None:
    kaynak = (BURASI / "sekil.py").read_text(encoding="utf-8")
    bas = kaynak.index("SEKILLER =")
    liste = re.findall(r'"(\d\d_[a-z_]+)"', kaynak[bas:kaynak.index("]", bas)])
    if len(liste) != 9:
        hatalar.append(f"figür listesi {len(liste)} öğe, beklenen 9")
    oz = _oz(VERI / "olcum.json")
    for ad in liste:
        yol = SEKIL / f"{ad}.html"
        if not yol.exists():
            hatalar.append(f"figür yok: {ad}.html")
            continue
        x = re.search(r"<!-- olcum\.json sha256: ([0-9a-f]{64}) -->\s*$", yol.read_text(encoding="utf-8"))
        sayac["arsiv"] += 1
        if not x or x.group(1) != oz:
            hatalar.append(f"figür bugünkü ölçüm dosyasından çizilmemiş — sekil.py yeniden koşulmalı: {ad}")
    gomulu = re.findall(r'<GrafikEmbed src="/analiz/' + SLUG + r'/(\d\d_[a-z_]+)\.html"[^>]*no="(\d\d)"', govde)
    if [a for a, _ in gomulu] != liste:
        hatalar.append(f"gömme sırası figür listesiyle aynı değil: {[a for a, _ in gomulu]}")
    if [n for _, n in gomulu] != [f"{i:02d}" for i in range(1, len(gomulu) + 1)]:
        hatalar.append(f"şekil numaraları sıralı değil: {[n for _, n in gomulu]}")
    for ad, no in gomulu:
        yol = SEKIL / f"{ad}.html"
        if not ad.startswith(no + "_"):
            hatalar.append(f"figür dosyasının öneki gömme numarasıyla aynı değil: {ad} · no {no}")
        if yol.exists():
            h = yol.read_text(encoding="utf-8")
            if f"Şekil {no} —" not in h and f"\\u015eekil {no} \\u2014" not in h:
                hatalar.append(f"figürün içindeki başlık 'Şekil {no}' değil: {ad}")
    # Şekil 02'nin olay takvimi metinde anılmalı
    blok = kaynak[kaynak.index("OLAYLAR = ["):kaynak.index("]", kaynak.index("OLAYLAR = ["))]
    duz = _norm(govde)
    for g in re.findall(r'"(\d{4}-\d\d-\d\d)"', blok):
        sayac["metin"] += 1
        if f"{int(g[8:10])} {AY[int(g[5:7])]}" not in duz:
            hatalar.append(f"Şekil 02 olayı metinde anılmıyor: {g}")


def main() -> int:
    o = arsiv()
    kur_kaynagi(o)
    m = MDX.read_text(encoding="utf-8")
    on, govde = bolumler(m)
    ALAN["govde"] = Alan("gövde", duz_metin(govde))
    ALAN["aciklama"] = Alan("açıklama", on["description"])
    ALAN["ozet"] = Alan("kart özeti", on["ozet"])
    ALAN["baslik"] = Alan("başlık", on["title"])
    TABLOLAR.extend(tablolar(govde))
    rakamlar(govde, o)
    tablolar_sina(o)
    cumleler(on, o)
    envanter()
    bicim(govde)
    figurler(govde)
    if hatalar:
        print(f"✗ OAT–Bund yazısı · {len(hatalar)} hata")
        for h in hatalar:
            print("  ·", h)
        return 1
    print(f"✓ OAT–Bund yazısı · {sayac['arsiv']} arşiv ölçütü, {sayac['hucre']} tablo hücresi, "
          f"{sayac['metin']} metin ölçütü, {sayac['dis']} dış kaynak ifadesi; {sayac['sayi']} ondalık sayının "
          "hepsi sınanmış ya da kaynağıyla bildirilmiş; 9 figür")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
