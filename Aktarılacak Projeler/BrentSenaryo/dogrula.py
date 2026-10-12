#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU (12.10.2026) — yayımlanan metni sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
pandas/numpy/plotly YOK: betik yalnız standart kütüphaneyle çalışır, ağa
çıkmaz, duvar saati okumaz (girdisi depodaki arşiv). Yedi soru sorar:

1. ARŞİV — `veri/` altındaki her donmuş tablonun sıkıştırılmamış özü künyedekiyle
   aynı mı; ölçüm dosyası bu özlerle, bugünkü `olcum.py` ile ve bugünkü ÖTV kayıt
   dosyasıyla mı üretilmiş?
2. KAYNAKLAR — yazının atıf verdiği her dış ifade kaynağın KENDİ metninde geçiyor
   mu? Ham sayfalar bulutta indirildi (`veri/ham/kaynak/`, `veri/ham/resmigazete/`),
   özleri bulut künyesinde; metinleri `kaynak_metin.py` bir kez çıkarıp dondurdu
   (`veri/kaynak_metin/`). Kapı ham dosyanın özünü künyeyle, metnin hangi ham
   dosyadan çıktığını ve alıntının o metinde geçtiğini sorar (ALINTI). TCMB PPK
   metinleri ve bülten kayıtları deponun kendi arşivinden (`bulten/veri/ppk/`,
   `site/src/data/bulten/`) okunur. Resmî Gazete kararlarının sayfaları taranmış
   görüntüdür (metin katmanı yok): tutarlar `veri/otv_kararlar.json`a sayfadan
   okunup kaynak dosyanın özüyle kaydedildi; kapı özü künyeyle, metindeki her
   tutarı kayıtla sorar. Bir alıntı yazıdan kalkarsa da kapı düşer.
3. TABLOLAR — yedi senaryo tablosunun her hücresi ölçüm dosyasından bu betiğin
   kendi biçimleyicisiyle kurulur ve yayımlanan tabloyla hücre hücre kıyaslanır
   (`--tablo` aynı kodla tabloyu basar; yazıya oradan girer). Mart karşılaştırması,
   emsal tablosu, takvim ve izleme listesi de satır satır sorulur.
4. METİN — yazının cümlelerindeki her ölçülmüş sayı ölçüm dosyasından kurulmuş bir
   ifadenin içinde mi; sayıyı doğru yazıp hükmü yanlış kuran cümleler (sayımlar,
   yönler, sıralamalar) ölçümden ayrıca hesaplanır (`dogru`).
5. ENVANTER — metindeki HER ondalık sayı ve yüzde/baz puan/puan taşıyan HER tam
   sayı ya sınanmış bir ifadenin ya da adıyla bildirilmiş bir dış kaynak
   ifadesinin içinde durmalı. Ön bilgi (başlık, açıklama, kart özeti) ve figür
   gömmelerinin başlıkları gövdeden AYRI sınanır.
6. BİÇİM — ASCII tireyle eksi, arkaya yazılmış yüzde, analizde yasak canlı
   `<Deger>` etiketi yok.
7. FİGÜRLER — on bir figür yayın dizininde, metin her birini sırayla gömüyor,
   figürün "Şekil NN" başlığı gömmenin numarasıyla aynı, başlık satırları
   telefonun gömme çerçevesine sığıyor ve figür bugünkü ölçümden çizilmiş.

Koşum:  python3 dogrula.py            · python3 dogrula.py --tablo
"""
from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
HAM = VERI / "ham"
SLUG = "brent-senaryo-2026-10-12"
# arıza enjeksiyonu sınaması başka bir kopyayı okutabilir (yalnız sınama içindir)
MDX = Path(os.environ.get("BRENT_DOGRULA_MDX") or KOK / "site/src/content/analiz" / f"{SLUG}.mdx")
SEKIL = KOK / "site/public/analiz" / SLUG
PPK = KOK / "bulten/veri/ppk"
BULTEN = KOK / "site/src/data/bulten"
TAKVIM_ELLE = KOK / "bulten/takvim_elle.json"

hatalar: list[str] = []
sayac = {"hucre": 0, "metin": 0, "arsiv": 0, "dis": 0, "sayi": 0, "alinti": 0, "sekil": 0}
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
      "Eylül", "Ekim", "Kasım", "Aralık"]
SAYI_AD = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz"}


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def _sifir(s: str) -> bool:
    return float(s.replace(".", "").replace(",", ".")) == 0


def sayi(x: float, b: int = 1, arti: bool = False) -> str:
    """Ondalık virgül, binlik nokta, eksi U+2212; sıfıra yuvarlanan değer işaretsiz."""
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if x < 0 and not _sifir(s):
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not _sifir(s)) else s


def yz(x: float, b: int = 1, arti: bool = False) -> str:
    """Yüzde işareti önde, işaret yüzdeden de önce: −%0,9 · +%1,8."""
    s = sayi(abs(x), b)
    if x < 0 and not _sifir(s):
        return "−%" + s
    return ("+%" if (arti and x > 0 and not _sifir(s)) else "%") + s


def bp(x: float, b: int = 0, arti: bool = True) -> str:
    return f"{sayi(x, b, arti)} bp"


def gun(iso: str) -> str:
    """'2026-10-09' → '9 Ekim 2026'."""
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]} {iso[:4]}"


def gun_ay(iso: str) -> str:
    """'2026-10-09' → '9 Ekim' (yılsız)."""
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]}"


def gun_k(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


def ay_ad(iso: str) -> str:
    return AY[int(iso[5:7])]


# ─────────────────────────────────────────────── metin alanları ve kapsam
def _ek_sil(s: str) -> str:
    """Kesme işaretinden sonraki eki siler: "54,9'dan" → "54,9'". Kapı ekin
    doğruluğunu değil sayının kendisini sorar."""
    return re.sub(r"'[a-zçğıöşüâîû]+", "'", s)


def _norm(s: str) -> str:
    return _ek_sil(re.sub(r"\s+", " ", s.replace("''", "'").replace(" ", " ")))


# Ondalık sayı: "140,9", "3.595,5", "1,1241". Binlik ayraçlı tam sayı ("6.967") ve madde
# numarası ("49.3") ondalık değildir. Birimli tam sayı: yüzde işareti önde ("%40") ya da baz
# puan / puan arkada ("+34 bp", "300 baz puan", "1 puan").
ONDALIK = re.compile(r"(?<![\d.,])\d{1,3}(?:\.\d{3})*,\d+|(?<![\d.,])\d+,\d+")
BIRIMLI = re.compile(r"%\d+(?![\d,.])|(?<![\d.,])\d+(?= (?:bp|baz puan|puan)\b)")


class Alan:
    """Normalize edilmiş bir metin alanı ve hangi karakterlerinin bir ölçütle
    kapsandığı. Kapsam bütün eşleşmeleri işaretler."""

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
        for rx in (ONDALIK, BIRIMLI):
            for x in rx.finditer(self.n):
                if not all(self.kapsam[x.start():x.end()]):
                    out.append(f"{self.ad}: {self.n[max(0, x.start() - 70):x.end() + 30]!r}")
        return out

    def say(self) -> int:
        return len(ONDALIK.findall(self.n)) + len(BIRIMLI.findall(self.n))


ALAN: dict[str, Alan] = {}


def metinde(parca: str, ad: str, yer: str = "govde") -> None:
    """Ölçümden kurulmuş bir ifade metinde birebir geçmeli."""
    sayac["metin"] += 1
    if not ALAN[yer].isaretle(parca):
        hatalar.append(f"{yer} · metinde yok ({ad}): {parca!r}")


def dogru(kosul: bool, mesaj: str) -> None:
    sayac["metin"] += 1
    if not kosul:
        hatalar.append(mesaj)


# ─────────────────────────────────────────────── tablo ayrıştırma
class Tablo(list):
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
    """Başlık satırı verilen hücrelerle başlayan TEK tablo."""
    bulunan = [x for x in TABLOLAR if x and tuple(x[0][:len(baslik)]) == baslik]
    if len(bulunan) != 1:
        hatalar.append(f"tablo bulunamadı ya da tekil değil ({len(bulunan)}): {baslik!r}")
        return Tablo([])
    t = bulunan[0]
    t.kapsam[0] = [True] * len(t[0])
    return t


def hucre(t: Tablo, ilk: str, sutun: int, beklenen: str, ad: str) -> None:
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


def dis_hucre(t: Tablo, ilk: str, sutun: int, parca: str, kimlik: str, kaynak_parca: str) -> None:
    """Tablo hücresinde bir dış kaynak sayısı: hücrede geçmeli VE kaynağın kendi metninde."""
    sayac["dis"] += 1
    kaynakta(kimlik, kaynak_parca)
    for i, r in enumerate(t):
        if r and r[0] == ilk and sutun < len(r) and parca in r[sutun]:
            t.kapsam[i][sutun] = True
            return
    hatalar.append(f"dış kaynak hücresi yok ({kimlik}): {ilk!r} sütun {sutun + 1}: {parca!r}")


def envanter() -> None:
    for a in ALAN.values():
        for k in a.kapsanmayan():
            hatalar.append(f"kapsanmayan sayı · {k}")
        sayac["sayi"] += a.say()
    for t in TABLOLAR:
        for i, r in enumerate(t):
            for j, h in enumerate(r):
                if ONDALIK.search(h) or BIRIMLI.search(h):
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
        if hashlib.sha256(gzip.decompress(yol.read_bytes())).hexdigest() != k["sha256"]:
            hatalar.append(f"arşiv özü künyeyle tutmuyor: {ad}")
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    sayac["arsiv"] += 3
    if o["uretim"]["girdiler"] != {ad: k["sha256"] for ad, k in kunye["dosyalar"].items()}:
        hatalar.append("ölçüm dosyası bu arşivle üretilmemiş (özler ayrışıyor) — olcum.py yeniden koşulmalı")
    if o["uretim"]["olcum_py_sha256"] != _oz(BURASI / "olcum.py"):
        hatalar.append("ölçüm dosyası bugünkü olcum.py ile üretilmemiş — olcum.py yeniden koşulmalı")
    if o["uretim"].get("otv_kararlar_sha256") != _oz(VERI / "otv_kararlar.json"):
        hatalar.append("ölçüm dosyası bugünkü ÖTV kayıt dosyasıyla üretilmemiş — olcum.py yeniden koşulmalı")
    return o


# ─────────────────────────────────────────────── 2 · kaynaklar
def _km():
    """Kaynak metinlerini çıkaran betiğin KENDİ normalleştirmesi (aynı fonksiyon, kopya değil): metni
    üreten ile sorgulayan ayrışamaz. Betik yalnız standart kütüphaneyle içe aktarılır (PDF okuyucusu
    yalnız metin çıkarma adımında istenir)."""
    spec = importlib.util.spec_from_file_location("brent_kaynak_metin", BURASI / "kaynak_metin.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


KM = _km()


def normal(s: str) -> str:
    """Donmuş kaynak metinleri `kaynak_metin.normal`den geçmiştir; sorgu da aynı yoldan geçer. Ek
    olarak denetim karakterleri (kırık yazı tipinin glif artıkları) iki tarafta da düşer."""
    return re.sub(r"\s+", " ", "".join(ch for ch in KM.normal(s) if unicodedata.category(ch) not in ("Cc", "Cf", "Co"))).strip()


_KAYNAK: dict[str, str] = {}
DIZIN: dict = {}


def _dizi(o) -> list[str]:
    if isinstance(o, str):
        return [o]
    if isinstance(o, dict):
        return [x for v in o.values() for x in _dizi(v)]
    if isinstance(o, list):
        return [x for v in o for x in _dizi(v)]
    return []


def kaynak_metni(kimlik: str) -> str:
    if kimlik in _KAYNAK:
        return _KAYNAK[kimlik]
    if kimlik.startswith("ppk:"):
        ad = kimlik[4:]
        d = json.loads((PPK / ad[:4] / f"{ad}.json").read_text(encoding="utf-8"))
        t = normal(" ".join(d["paragraflar"]))
    elif kimlik.startswith("bulten:"):
        d = json.loads((BULTEN / f"{kimlik[7:]}.json").read_text(encoding="utf-8"))
        t = normal(" ".join(_dizi(d)))
    else:
        kayit = [v for v in DIZIN.values() if v["metin"] == f"kaynak_metin/{kimlik}.txt.gz"]
        if len(kayit) != 1:
            hatalar.append(f"kaynak metni dizinde yok ya da tekil değil: {kimlik}")
            t = ""
        else:
            t = normal(gzip.decompress((VERI / kayit[0]["metin"]).read_bytes()).decode("utf-8"))
    _KAYNAK[kimlik] = t
    return t


def kaynakta(kimlik: str, parca: str) -> None:
    sayac["alinti"] += 1
    if normal(parca) not in kaynak_metni(kimlik):
        hatalar.append(f"kaynakta yok ({kimlik}): {parca!r}")


def kaynak_butunlugu() -> None:
    """Ham dosyanın özü bulut künyesiyle, donmuş metnin özü dizinle aynı mı?"""
    global DIZIN
    DIZIN = json.loads((VERI / "kaynak_metin.json").read_text(encoding="utf-8"))
    kunye = {}
    for kn in ("kunye_kaynak.json", "kunye_rg.json"):
        kunye.update(json.loads((HAM / kn).read_text(encoding="utf-8")))
    for yol, v in DIZIN.items():
        sayac["arsiv"] += 1
        ham = HAM / yol
        if not ham.exists():
            hatalar.append(f"kaynağın ham dosyası yok: {yol}")
            continue
        oz = hashlib.sha256(gzip.decompress(ham.read_bytes())).hexdigest()
        if oz != v["kaynak_sha256"] or oz != kunye.get(yol, {}).get("sha256"):
            hatalar.append(f"kaynağın ham dosyası künyeyle tutmuyor: {yol}")
        m = VERI / v["metin"]
        if not m.exists() or hashlib.sha256(gzip.decompress(m.read_bytes())).hexdigest() != v["metin_sha256"]:
            hatalar.append(f"donmuş kaynak metni dizindeki özle tutmuyor: {v['metin']}")


def alinti(kimlik: str, kaynak_parca: str, mdx_parca: str, yer: str = "govde") -> None:
    """Dış kaynağın ifadesi: kaynağın kendi metninde geçmeli (kaynak_parca) VE yazıda
    adıyla durmalı (mdx_parca; envanterde kapsanmış sayılır)."""
    sayac["dis"] += 1
    kaynakta(kimlik, kaynak_parca)
    if not ALAN[yer].isaretle(mdx_parca):
        hatalar.append(f"{yer} · dış kaynak ifadesi metinde yok ({kimlik}): {mdx_parca!r}")


# ─────────────────────────────────────────────── 3 · senaryo tabloları
# Her tablo: (ilk başlık hücresi, [(kod, okur adı, seviye ondalığı)]). Kod ölçüm dosyasının
# `senaryo_tablosu` anahtarıdır; okur adı tablonun ilk sütunu. Ondalık yalnız SEVİYE içindir
# (değişim: yüzde 1, baz puan 0, milyar dolar 1 hane). Bir satır tablodan düşerse ya da yeni
# bir satır eklenirse kapı düşer: tablo bu tanımla birebir aynı olmalı.
KANIT_AD = {"guclu": "güçlü", "orta": "orta", "zayif": "zayıf"}
BASLIK = ("Bugün", "125 dolarda", "150 dolarda", "Kanıt")
TABLO_TANIM = [
    ("Emtia ve oynaklık", [
        ("CL=F", "WTI (dolar/varil)", 2), ("HO=F", "Motorin vadelisi, ULSD (dolar/galon)", 3),
        ("RB=F", "Benzin vadelisi, RBOB (dolar/galon)", 3), ("NG=F", "Doğal gaz, Henry Hub", 2),
        ("GC=F", "Altın (dolar/ons)", 0), ("SI=F", "Gümüş", 2), ("HG=F", "Bakır", 2),
        ("OVX", "Petrol oynaklığı (OVX)", 1), ("^VIX", "VIX", 1), ("^MOVE", "MOVE", 1)]),
    ("ABD faizi ve kredi", [
        ("us2y", "ABD 2 yıllık", 2), ("us10y", "ABD 10 yıllık", 2), ("us30y", "ABD 30 yıllık", 2),
        ("be5y", "ABD 5 yıllık başabaş enflasyon", 2), ("reel10y", "ABD 10 yıllık reel getiri", 2),
        ("HYG", "Yüksek getirili kredi (HYG)", 2), ("LQD", "Yatırım yapılabilir kredi (LQD)", 2),
        ("EMB", "Gelişen ülke dolar tahvili (EMB)", 2)]),
    ("Hisse endeksi", [
        ("^GSPC", "S&P 500", 0), ("^NDX", "Nasdaq 100", 0), ("^RUT", "Russell 2000", 0),
        ("^STOXX", "STOXX Europe 600", 1), ("^GDAXI", "DAX", 0), ("^FCHI", "CAC 40", 0),
        ("^FTSE", "FTSE 100", 0), ("^N225", "Nikkei 225", 0), ("^HSI", "Hang Seng", 0),
        ("000001.SS", "Şanghay Bileşik", 0), ("EEM", "Gelişen piyasa hisseleri (EEM)", 2)]),
    ("Sektör ve ülke fonu", [
        ("XOP", "ABD petrol üreticileri (XOP)", 2), ("XLE", "ABD enerji (XLE)", 2),
        ("JETS", "ABD havayolları (JETS)", 2), ("XLY", "ABD isteğe bağlı tüketim (XLY)", 2),
        ("XLP", "ABD temel tüketim (XLP)", 2), ("XLK", "ABD teknoloji (XLK)", 2),
        ("XLU", "ABD kamu hizmetleri (XLU)", 2), ("ITA", "ABD savunma (ITA)", 2),
        ("KSA", "Suudi Arabistan (KSA)", 2), ("UAE", "BAE (UAE)", 2), ("INDA", "Hindistan (INDA)", 2),
        ("EWY", "Güney Kore (EWY)", 2)]),
    ("Döviz", [
        ("DX-Y.NYB", "Dolar endeksi (DXY)", 2), ("EURUSD=X", "EUR/USD", 4), ("GBPUSD=X", "GBP/USD", 4),
        ("USDJPY=X", "USD/JPY", 2), ("USDCHF=X", "USD/CHF", 4), ("USDCAD=X", "USD/CAD", 4),
        ("USDNOK=X", "USD/NOK", 3), ("AUDUSD=X", "AUD/USD", 4), ("inr", "USD/INR", 2),
        ("krw", "USD/KRW", 0), ("zar", "USD/ZAR", 2), ("mxn", "USD/MXN", 2), ("brl", "USD/BRL", 3),
        ("pln", "USD/PLN", 3)]),
    ("Türkiye: kur ve hisse", [
        ("USDTRY=X", "USD/TRY", 2), ("EURTRY=X", "EUR/TRY", 2), ("XU100.IS", "BIST 100", 0),
        ("bist_usd", "BIST 100 (dolar)", 1), ("XBANK.IS", "BIST Bankacılık", 0), ("XUSIN.IS", "BIST Sınai", 0),
        ("TUR", "Türkiye fonu (TUR, dolar)", 2), ("TUPRS_IS", "Tüpraş", 2), ("PETKM_IS", "Petkim", 2),
        ("THYAO_IS", "Türk Hava Yolları", 2), ("PGSUS_IS", "Pegasus", 2), ("TAVHL_IS", "TAV Havalimanları", 2),
        ("AKBNK_IS", "Akbank", 2), ("GARAN_IS", "Garanti BBVA", 2), ("FROTO_IS", "Ford Otosan", 2),
        ("BIMAS_IS", "BİM", 2), ("ASELS_IS", "Aselsan", 2)]),
    ("Türkiye: faiz ve rezerv", [
        ("n3a", "DİBS 3 ay", 2), ("n2y", "DİBS 2 yıl", 2), ("n5y", "DİBS 5 yıl", 2),
        ("be_2y", "2 yıllık başabaş enflasyon", 2), ("r2y", "2 yıllık reel getiri", 2), ("tlref", "TLREF", 2),
        ("net_rezerv_usd", "TCMB net rezerv (milyar dolar)", 1),
        ("swap_haric_net_rezerv_usd", "Swap hariç net rezerv (milyar dolar)", 1)]),
]


def bugun_yaz(v: dict, dec: int) -> str:
    if v["birim"] == "bp":
        return yz(v["son_deger"], 2)
    return sayi(v["son_deger"], 1 if v["birim"] == "fark" else dec)


def senaryo_yaz(v: dict, sen: str, dec: int) -> str:
    """Hücre iki satır: orta değerin değişimi → seviyesi; altında %90 aralığın iki ucu (seviye).
    Fiyat değişimi YÜZDEDİR (ölçüm dosyasının `orta_yuzde`si): 91,85 × (1 + %44,7) = 132,9 — log ölçüde
    +37,0 yazılsaydı okurun çarpımı tutmazdı. Aralık log ölçüde simetriktir, yüzde ölçüde değil; bu
    yüzden ± ile değil iki uçla yazılır."""
    s = v[sen]
    if v["birim"] == "log":
        return (f"{yz(s['orta_yuzde'], 1, True)} → {sayi(s['seviye'], dec)}<br />"
                f"{sayi(s['seviye_alt'], dec)} – {sayi(s['seviye_ust'], dec)}")
    if v["birim"] == "bp":
        return (f"{sayi(s['orta'], 0, True)} bp → {yz(s['seviye'], 2)}<br />"
                f"{yz(s['seviye_alt'], 2)} – {yz(s['seviye_ust'], 2)}")
    return (f"{sayi(s['orta'], 1, True)} → {sayi(s['seviye'], 1)}<br />"
            f"{sayi(s['seviye_alt'], 1)} – {sayi(s['seviye_ust'], 1)}")


def tablo_satirlari(o: dict) -> list[tuple[str, list[list[str]]]]:
    st = o["senaryo_tablosu"]
    out = []
    for bas, kalemler in TABLO_TANIM:
        satir = []
        for k, ad, dec in kalemler:
            v = st[k]
            satir.append([ad, bugun_yaz(v, dec), senaryo_yaz(v, "125", dec), senaryo_yaz(v, "150", dec),
                          KANIT_AD[v["kanit"]]])
        out.append((bas, satir))
    return out


def tablo_bas(o: dict) -> None:
    for bas, satirlar in tablo_satirlari(o):
        print(f"| {bas} | " + " | ".join(BASLIK) + " |")
        print("|---|---:|---:|---:|---|")
        for r in satirlar:
            print("| " + " | ".join(r) + " |")
        print()


def senaryo_tablolari(o: dict) -> None:
    tanimli = {k for _, kalemler in TABLO_TANIM for k, _, _ in kalemler}
    dogru(tanimli == set(o["senaryo_tablosu"]),
          f"senaryo tabloları ölçüm dosyasının kalemleriyle aynı değil: eksik "
          f"{sorted(set(o['senaryo_tablosu']) - tanimli)}, fazla {sorted(tanimli - set(o['senaryo_tablosu']))}")
    for bas, satirlar in tablo_satirlari(o):
        t = tablo(bas, *BASLIK)
        if not t:
            continue
        beklenen = [r[0] for r in satirlar]
        yazili = [r[0] for r in t[1:]]
        if yazili != beklenen:
            hatalar.append(f"senaryo tablosu '{bas}': satırlar tanımla aynı değil: {yazili!r} ≠ {beklenen!r}")
        for r in satirlar:
            for j in range(1, 5):
                hucre(t, r[0], j, r[j], f"senaryo tablosu '{bas}'")


# ─────────────────────────────────────────────── 3b · öbür tablolar
def mart_tablosu(o: dict) -> None:
    a, b = o["tcmb"]["2025-03"], o["tcmb"]["2026-03"]
    t = tablo("Gösterge", "Mart 2025 (siyasi şok)", "Mart 2026 (petrol şoku)")
    ad = "Mart karşılaştırması"
    satir = [
        ("Pencere", lambda m: f"{gun_ay(m['bas'])} → {gun(m['son'])}"),
        ("Ağırlıklı ortalama fonlama maliyeti (zirve)", lambda m: f"{yz(m['aofm_bas'], 2)} → {yz(m['aofm_zirve'], 2)}"),
        ("TLREF", lambda m: f"{yz(m['tlref_bas'], 2)} → {yz(m['tlref_son'], 2)}"),
        ("Politika faizi", lambda m: f"{yz(m['politika_bas'], 2)} → {yz(m['politika_son'], 2)}"),
        ("21 iş gününde döviz satışı", lambda m: f"{sayi(-m['doviz_satisi_21g'], 2)} milyar dolar"),
        ("Net rezerv (dip)", lambda m: f"{sayi(m['net_rezerv_bas'], 2)} → {sayi(m['net_rezerv_dip'], 2)} milyar dolar"),
        ("Swap hariç net rezerv (dip)",
         lambda m: f"{sayi(m['swap_haric_bas'], 2)} → {sayi(m['swap_haric_dip'], 2)} milyar dolar"),
        ("Altının rezerve fiyat etkisi", lambda m: f"{sayi(m['altin_fiyat_etkisi_21g'], 2, True)} milyar dolar"),
        ("USD/TRY (TCMB gösterge kuru)", lambda m: yz(m["usdtry_tcmb_degisim"], 2, True)),
        ("DİBS 2 yıllık", lambda m: f"{yz(m['dibs_2y_bas'], 2)} → {yz(m['dibs_2y_son'], 2)}"),
    ]
    for ilk, f in satir:
        hucre(t, ilk, 1, f(a), ad)
        hucre(t, ilk, 2, f(b), ad)
    # ara verildiği gün TCMB'nin kendi metninden; ölçülen stok düşüşü aynı güne ya da ertesi iş gününe düşmeli
    hucre(t, "Repo ihalesine ara verilmesi (TCMB)", 1, "20 Mart 2025", ad)
    hucre(t, "Repo ihalesine ara verilmesi (TCMB)", 2, "2 Mart 2026", ad)
    kaynakta("ppk:2025-28-TR", "20 Mart tarihinde ara verilen bir hafta vadeli repo ihalelerine")
    kaynakta("ppk:2026-14-TR", "1 hafta vadeli repo ihalelerine 2 Mart itibarıyla ara verilmiştir")
    dogru(a["ihale_ara_ilk"] in ("2025-03-20", "2025-03-21"),
          f"2025 repo stoku TCMB'nin ara verdiği günden başka bir gün düşüyor: {a['ihale_ara_ilk']}")
    dogru(b["ihale_ara_ilk"] == "2026-03-02",
          f"2026 repo stoku TCMB'nin ara verdiği gün (2 Mart) düşmüyor: {b['ihale_ara_ilk']}")
    yazili = [r[0] for r in t[1:]]
    bek = ["Pencere", "Repo ihalesine ara verilmesi (TCMB)"] + [s for s, _ in satir[1:]]
    dogru(yazili == bek, f"Mart tablosunun satırları değişti: {yazili!r}")


EMSAL_AD = {"1990": "1990 Körfez", "2002": "2002 Venezuela grevi", "2003": "2003 Irak savaşı", "2011": "2011 Libya",
            "2019": "2019 Abqaiq", "2022": "2022 Rusya", "2025": "2025 İsrail–İran", "2026": "2026 Hürmüz"}
EMSAL_SUTUN = [("brent_fiziki", "log"), ("spx", "log"), ("us2y", "bp"), ("dxy", "log"), ("altin", "log"),
               ("try_tcmb", "log"), ("bist_usd", "log")]


def _pencere(bas: str, son: str) -> str:
    if bas[:4] == son[:4]:
        return f"{bas[8:10]}.{bas[5:7]} → {gun_k(son)}"
    return f"{gun_k(bas)} → {gun_k(son)}"


def emsal_tablosu(o: dict) -> list[tuple[str, dict]]:
    t = tablo("Olay", "Pencere", "Brent (fiziki)", "S&P 500", "ABD 2 yıllık", "Dolar endeksi", "Altın", "USD/TRY",
              "BIST 100 (dolar)")
    ad = "emsal tablosu"
    satirlar = []
    for k, m in o["emsaller"].items():
        ilk = EMSAL_AD[k]
        satirlar.append((ilk, m))
        hucre(t, ilk, 1, _pencere(m["bas"], m["son"]), ad)
        for j, (s, birim) in enumerate(EMSAL_SUTUN, 2):
            v = m["deger_yuzde"].get(s)
            bek = "—" if v is None else (f"{sayi(v, 0, True)} bp" if birim == "bp" else yz(v, 1, True))
            hucre(t, ilk, j, bek, ad)
    dogru([r[0] for r in t[1:]] == [EMSAL_AD[k] for k in o["emsaller"]], "emsal tablosunun satırları değişti")
    return satirlar


def takvim_tablosu(o: dict) -> None:
    """Her satırın günü ve olayı bir kaynakta: bülten takvimi (resmî yayım takvimleri), elle tutulan kesin
    takvim, kaynak metinleri ya da ölçüm dosyası."""
    t = tablo("Tarih", "Olay", "Senaryo için önemi")
    ad = "takvim tablosu"
    bulten_takvim = []
    for blok in json.loads((BULTEN / "2026-10-12.json").read_text(encoding="utf-8"))["takvim"]:
        bulten_takvim.extend(blok["kayitlar"])
    elle = json.loads(TAKVIM_ELLE.read_text(encoding="utf-8"))["kesin"]

    def resmi(tarih: str, desen: str) -> bool:
        return any(x["tarih"] == tarih and re.search(desen, x["olay"]) for x in bulten_takvim + elle)

    hedef = o["senaryo_yeri"]["hedef_gun"]
    kontrol = {
        "13 Ekim": lambda: resmi("2026-10-13", r"Ödemeler dengesi \(Ağustos"),
        "14 Ekim": lambda: resmi("2026-10-14", r"ABD TÜFE \(Eylül"),
        "22 Ekim": lambda: resmi("2026-10-22", r"PPK faiz kararı"),
        "28 Ekim": lambda: resmi("2026-10-28", r"FOMC"),
        "29 Ekim": lambda: resmi("2026-10-29", r"ECB"),
        "30 Ekim": lambda: resmi("2026-10-30", r"PPK toplantı özeti"),
        "1 Kasım": lambda: True,          # OPEC+ (CNBC) ve ÖTV adımı (kayıt) aşağıda ayrıca sorulur
        "3 Kasım": lambda: True,          # ara seçim (Bloomberg HT) aşağıda ayrıca sorulur
        "4 Kasım": lambda: resmi("2026-11-04", r"Quarterly Refunding"),
        "6 Kasım": lambda: resmi("2026-11-06", r"tarım dışı istihdam \(Ekim"),
        gun_ay(hedef): lambda: True,
    }
    yazili = [r[0] for r in t[1:]]
    dogru(yazili == list(kontrol), f"takvim tablosunun satırları değişti: {yazili!r}")
    k10, kg = o["enerji_faturasi"]["kural_2010"], o["enerji_faturasi"]["kural_2010_gazli"]
    t1, t2 = k10["sonraki_ay_tahmin_milyar"], kg["sonraki_ay_tahmin_milyar"]
    hucre(t, "13 Ekim", 2, f"Enerji faturası; kural {sayi(min(t1, t2), 2)}–{sayi(max(t1, t2), 2)} milyar dolar bekliyor "
                           f"(Ağustos 2025: {sayi(k10['gecen_yil_ayni_ay_milyar'], 2)})", ad)
    for r in t[1:]:
        sayac["hucre"] += 1
        if r[0] in kontrol and not kontrol[r[0]]():
            hatalar.append(f"{ad}: '{r[0]}' satırının olayı kaynak takvimlerde o güne düşmüyor: {r[1]!r}")
    kaynakta("cnbc_com_5dfd5ea085", "The seven will meet next on Nov. 1")
    kaynakta("bloomberght_com_d832ce5702", "3 Kasım'daki ara seçimlere kadar İran'a saldırı düzenlemeyeceklerini")
    otv = json.loads((VERI / "otv_kararlar.json").read_text(encoding="utf-8"))
    kasim = [d for kr in otv["kararlar"] for u in kr["urunler"] for d in u["donemler"] if d["bas"] == "2026-11-01"]
    dogru(len(kasim) >= 3, "ÖTV kayıtlarında 1 Kasım'da başlayan dönem yok")
    dogru(hedef == "2026-11-09", f"hedef gün 9 Kasım değil: {hedef}")


def izleme_tablosu(o: dict) -> None:
    t = tablo("tarih", "veri", "neyi doğrular / çürütür")
    dis_hucre(t, "12.11.2026", 2, "87,8 dolar", "arastirma_isyatirim_com_tr_5dbf6b4d88",
              "Brent petrol fiyat varsayımını 1,6 dolar aşağı çekerek 87,8 dolara")
    k10, kg = o["enerji_faturasi"]["kural_2010"], o["enerji_faturasi"]["kural_2010_gazli"]
    t1, t2 = k10["sonraki_ay_tahmin_milyar"], kg["sonraki_ay_tahmin_milyar"]
    hucre(t, "13.10.2026", 2, f"Net enerji faturası kuralın beklediği {sayi(min(t1, t2), 2)}–{sayi(max(t1, t2), 2)} milyar "
                              f"dolarla tutuyor mu (Ağustos 2025: {sayi(k10['gecen_yil_ayni_ay_milyar'], 2)})", "izleme")
    ot = o["otv_tampon"]["otv"]
    m, b = ot["motorin"]["adim"], ot["kurşunsuz benzin 95 oktan"]["adim"]
    hucre(t, "01.11.2026", 2, f"Arz kararı; motorinde {sayi(m, 0, True)}, benzinde {sayi(b, 2, True)} TL", "izleme")


# ─────────────────────────────────────────────── 4 · metin
def otv_kayitlari() -> dict:
    """ÖTV kayıt dosyası ve kaynağının bütünlüğü; ürün → dönem tablosu."""
    otv = json.loads((VERI / "otv_kararlar.json").read_text(encoding="utf-8"))
    kunye = json.loads((HAM / "kunye_rg.json").read_text(encoding="utf-8"))
    out = {}
    for kr in otv["kararlar"]:
        sayac["arsiv"] += 1
        yol = VERI / kr["dosya"]
        if not yol.exists():
            hatalar.append(f"ÖTV kararının ham dosyası yok: {kr['dosya']}")
        else:
            oz = hashlib.sha256(gzip.decompress(yol.read_bytes())).hexdigest()
            if oz != kr["sha256"] or oz != kunye.get(kr["dosya"].removeprefix("ham/"), {}).get("sha256"):
                hatalar.append(f"ÖTV kararının ham dosyası kayıttaki özle tutmuyor: {kr['dosya']}")
        for u in kr["urunler"]:
            out[u["ad"]] = {"karar": kr, "donem": {d["bas"]: d["otv"] for d in u["donemler"]}}
    return out


def metin(on: dict, o: dict) -> None:
    S, Y, IB, R = o["senaryo_tablosu"], o["senaryo_yeri"], o["iki_brent"], o["rejim_2026"]
    V, P = R["varlik"], R["pencereler"]
    T, TU, EF, YB = o["tcmb"], o["tufe_gecis"], o["enerji_faturasi"], o["yabanci"]
    AE, AS, TA, OT = o["abd_enflasyon"], o["abd_senaryo"], o["tufe_aktarim"], o["otv_tampon"]
    TY, TCB = o["tum_yukselisler"], o["birini_disarida"]
    YT = o["yontem"]
    sik = Y["siklik"]["vadeli_1988"]
    m26, m25 = T["2026-03"], T["2025-03"]

    def oy(k, sen, b=1):
        return yz(S[k][sen]["orta_yuzde"], b, True)

    def ob(k, sen):
        return sayi(S[k][sen]["orta"], 0, True)

    def of(k, sen, b=1):
        return sayi(S[k][sen]["orta"], b, True)

    def sv(k, sen, b=2):
        return sayi(S[k][sen]["seviye"], b)

    baz, ocak = Y["baz"], Y["ikinci_vade_bugun"]
    y125, y150 = Y["senaryo"]["125"]["yuzde"], Y["senaryo"]["150"]["yuzde"]
    yd125, yd150 = Y["senaryo"]["125"]["yuzde_devirsiz"], Y["senaryo"]["150"]["yuzde_devirsiz"]
    fark, fiz, vad = IB["fark_son"], IB["fiziki_son"], IB["vadeli_ayni_gun"]
    tar = IB["tarihce_2000_2025"]
    sh = m26["swap_haric_bas"] - m26["swap_haric_dip"]
    rz = T["rezerv_bugun"]
    ot125, ot150 = OT["senaryo"]["125"], OT["senaryo"]["150"]
    om, ob95 = OT["otv"]["motorin"], OT["otv"]["kurşunsuz benzin 95 oktan"]
    ek = EF["senaryo_kural"]

    # ── ön bilgi: açıklama
    d = "aciklama"
    metinde(f"Vadeli Brent 9 Ekim'de {sayi(baz, 2)} dolardı", "baz", d)
    metinde(f"125 dolara çıkması {yz(y125, 1, True)}, 150 dolara çıkması {yz(y150, 1, True)} demek", "hedef yüzde", d)
    metinde(f"günlerin {yz(sik['125']['pay'], 2)}'ünde ve {yz(sik['150']['pay'], 2)}'inde görüldü", "sıklık", d)
    metinde(f"6 Ekim'de zaten {sayi(fiz, 2)} dolardaydı, vadeliden {sayi(fark, 2)} dolar yukarıda", "iki Brent", d)
    metinde(f"bu fark hiç {sayi(tar['azami'], 2)} doları aşmamıştı", "tarihçe azami", d)
    metinde(f"ABD 2 yıllık getiri 125 dolarda {ob('us2y', '125')}, 150 dolarda {ob('us2y', '150')} baz puan", "us2y", d)
    metinde(f"BIST Bankacılık {oy('XBANK.IS', '125')} ve {oy('XBANK.IS', '150')}", "XBANK", d)
    metinde(f"USD/TRY yönetilen patikada {sv('USDTRY=X', '125')} ve {sv('USDTRY=X', '150')}", "USDTRY", d)
    metinde(f"swap hariç net rezerv {of('swap_haric_net_rezerv_usd', '125')} ve "
            f"{of('swap_haric_net_rezerv_usd', '150')} milyar dolar", "swap hariç", d)
    dogru(sik["125"]["pay"] < 3 and sik["150"]["epizot"] == 2, "açıklama: sıklık")

    # ── ön bilgi: kart özeti
    metinde(f"vadeli {sayi(baz, 2)}'de", "baz", "ozet")
    dogru(fiz >= 125, "kart özeti: fiziki Brent 125 dolarda değil")

    # ── yönetici özeti: tez
    g = "govde"
    metinde(f"Vadeli Brent 9 Ekim'de {sayi(baz, 2)} dolardı; bir ay içinde 125 dolara çıkması {yz(y125, 1, True)}, "
            f"150 dolara çıkması {yz(y150, 1, True)}'lik bir yükseliş demek ve 1988'den bu yana ikincisi yalnız "
            f"{SAYI_AD[sik['150']['epizot']]} kez görüldü", "tez")
    metinde(f"Avrupa Brent spot fiyatı 6 Ekim'de {sayi(fiz, 2)} dolardı, vadeliden {sayi(fark, 2)} dolar yukarıda; "
            f"2000–2025 arasında bu fark hiç {sayi(tar['azami'], 2)} doları aşmamıştı", "tez")
    for k, isaret in (("us2y", 1), ("JETS", -1), ("XU100.IS", -1), ("USDTRY=X", 1)):
        dogru(all((x or 0) * isaret > 0 for x in V[k]["pencere"]), f"tez: {k} dört pencerenin dördünde aynı yönde değil")
    metinde(f"Bu ilişkiler 125 dolarda ABD 2 yıllık için {ob('us2y', '125')}, 150 dolarda {ob('us2y', '150')} baz puan; "
            f"BIST Bankacılık için {oy('XBANK.IS', '125')} ve {oy('XBANK.IS', '150')}; USD/TRY için "
            f"{sv('USDTRY=X', '125')} ve {sv('USDTRY=X', '150')} veriyor", "tez")
    metinde(f"swap hariç net rezerv 21 iş gününde {sayi(sh, 1)} milyar dolar eridi (döviz satışı "
            f"{sayi(-m26['doviz_satisi_21g'], 2)}, altının fiyat etkisi {sayi(-m26['altin_fiyat_etkisi_21g'], 1)} milyar "
            f"dolar), bugünkü stok {sayi(rz['swap_haric'], 1)} milyar dolar", "tez")
    dogru(m26["altin_fiyat_etkisi_21g"] < 0 and abs(sh + m26["doviz_satisi_21g"] + m26["altin_fiyat_etkisi_21g"]) < 3,
          "tez: Mart erimesi döviz satışı ile altının fiyat etkisinin toplamına yakın değil")
    metinde(f"yeniden açılırsa Kasım'ın litre başına {sayi(om['kasim'], 0)} TL'lik ÖTV'si 125 dolarlık ham petrolün getirdiği "
            f"{sayi(ot125['ham_tl_litre'], 2)} TL'lik artışı karşılayabilir, ama rafineri marjı 2026'daki gibi açılırsa "
            f"gelen {sayi(ot125['motorin_urun_tl_litre'], 2)} TL'yi karşılayamaz", "tez")
    dogru(ot125["ham_tl_litre"] < om["kasim"] < ot125["motorin_urun_tl_litre"], "tez: ÖTV tamponu karşılaştırması")

    # ── yönetici özeti: tablo
    metinde(f"Fiziki kargo 6 Ekim'de {sayi(fiz, 2)} dolarda, vadeli {sayi(vad, 2)}'de; fark {sayi(fark, 2)} dolar",
            "tablo · hangi Brent")
    dogru(tar["son_gunden_buyuk_pay"] == 0, "2000–2025'te bugünkü farktan büyük gün var")
    metinde(f"o kontrat {sayi(ocak, 2)} dolarda: 125'e çıkması öbür piyasalar için {yz(yd125, 1, True)}, 150'ye "
            f"çıkması {yz(yd150, 1, True)}'lik bir hareket", "tablo · Ocak kontratı")
    metinde(f"1988'den bu yana günlerin {yz(sik['125']['pay'], 2)}'ünde vadeli Brent bir ayda en az "
            f"{yz(y125, 1, True)} yükseldi ({sik['125']['epizot']} ayrı epizot); {yz(y150, 1, True)} ise yalnız "
            f"{sik['150']['gun']} günde, {SAYI_AD[sik['150']['epizot']]} epizotta", "tablo · sıklık")
    ov = Y["ovx"]
    metinde(f"(OVX {sayi(ov['deger'], 2)}) hedef günün ön vadesi olan Ocak kontratına ay sonunda 125'in üstünde olmaya "
            f"{yz(ov['olasilik']['125'], 1)}, 150'nin üstünde olmaya {yz(ov['olasilik']['150'], 1)} olasılık", "tablo · OVX")
    dogru(abs(ov["dayanak"] - ocak) < 1e-9, "OVX olasılığının dayanağı hedef günün ön vadesi (Ocak kontratı) değil")
    rk = Y["rekor"]
    metinde(f"{sayi(rk['vadeli_kapanis'], 2)} dolarlık kapanış rekoru bugünün dolarıyla {sayi(rk['bugunun_dolariyla'], 2)}",
            "tablo · reel")
    metinde(f"ABD 2 yıllık getirisi 125 dolarda {ob('us2y', '125')}, 150 dolarda {ob('us2y', '150')} baz puan; "
            f"10 yıllık {ob('us10y', '125')} ve {bp(S['us10y']['150']['orta'])}", "tablo · faiz")
    dogru(TCB["us2y"]["rmse"] < TCB["us2y"]["rmse_egilim"] and TCB["us10y"]["rmse"] >= TCB["us10y"]["rmse_egilim"],
          "tablo: Brent'in büyüklüğü 2 yıllıkta katkı vermiyor ya da 10 yıllıkta veriyor")
    dogru(all(x > 0 for x in V["us10y"]["pencere"]), "tablo: 10 yıllık dördünde artmadı")
    metinde(f"Dolar endeksi için kanıt zayıf ({oy('DX-Y.NYB', '125')} ve {oy('DX-Y.NYB', '150')})", "tablo · DXY")
    dogru(S["DX-Y.NYB"]["kanit"] == "zayif", "tablo: DXY kanıtı zayıf değil")
    for k in ("inr", "zar", "pln", "USDCHF=X"):
        dogru(S[k]["kanit"] == "guclu" and S[k]["125"]["orta"] > 0, f"tablo: {k} değer kaybı güçlü kanıtlı değil")
    dogru(sum(x > 0 for x in V["^GSPC"]["pencere"]) == 2, "S&P 500 iki pencerede artmadı")
    dogru(sum(x < 0 for x in V["GC=F"]["pencere"]) == 3, "altın üç pencerede düşmedi")
    od = TY["orneklem_disi_2026"]
    dogru(od["spx"]["isaret_tutan"] < 3 and od["altin"]["isaret_tutan"] < 3, "S&P 500 ya da altın örneklem dışı geçiyor")
    metinde(f"ABD havayolları {oy('JETS', '125')} ve {oy('JETS', '150')}, ABD petrol üreticileri {oy('XOP', '125')} ve "
            f"{oy('XOP', '150')}; Avrupa (STOXX 600 {oy('^STOXX', '125')} ve {oy('^STOXX', '150')}) ve ABD küçük "
            f"şirketleri (Russell 2000 {oy('^RUT', '125')} ve {oy('^RUT', '150')}) güçlü kanıtla", "tablo · hisseler")
    for k in ("JETS", "XOP", "^STOXX", "^RUT"):
        dogru(S[k]["kanit"] == "guclu", f"tablo: {k} güçlü değil")
    u = V["USDTRY=X"]["pencere_yuzde"]
    metinde(f"USD/TRY dört yükselişin dördünde {yz(min(u), 1, True)} ile {yz(max(u), 1, True)} arasında kaldı",
            "tablo · USD/TRY")
    metinde(f"Mart'ta yük rezervdeydi: TCMB 21 iş gününde {sayi(-m26['doviz_satisi_21g'], 2)} milyar dolar sattı, repo "
            f"ihalesine ara verip fonlamayı koridorun tavanına ({yz(m26['aofm_zirve'], 0)}) taşıdı", "tablo · Mart")
    swp = V["swap_haric_net_rezerv_usd"]["pencere"]
    metinde(f"swap hariç net rezerv {sayi(m26['swap_haric_bas'], 2)}'dan {sayi(m26['swap_haric_dip'], 2)} milyar dolara "
            f"indi. Öbür üç yükselişte erime en çok {sayi(-min(swp[1:]), 1)} milyar dolardı ve rezerv kaleminin kanıtı zayıf. "
            f"Bugün {sayi(rz['swap_haric'], 2)} milyar dolar", "tablo · rezerv")
    dogru(S["swap_haric_net_rezerv_usd"]["kanit"] == "zayif", "tablo: rezerv kaleminin kanıtı zayıf değil")
    dogru(m26["politika_bas"] == m26["politika_son"], "Mart 2026'da politika faizi değişti")
    metinde(f"DİBS 2 yıllık 125 dolarda {ob('n2y', '125')}, 150 dolarda {ob('n2y', '150')} baz puan "
            f"({yz(S['n2y']['125']['seviye'], 2)} ve {yz(S['n2y']['150']['seviye'], 2)})", "tablo · DİBS")
    fb = T["fonlama_bugun"]
    metinde(f"tavan koridorun üst bandı, {yz(fb['koridor_ust'], 0)}", "tablo · koridor")
    metinde(f"BIST 100 dolar bazında {oy('bist_usd', '125')} ve {oy('bist_usd', '150')}, bankacılık "
            f"{oy('XBANK.IS', '125')} ve {oy('XBANK.IS', '150')}, Tüpraş {oy('TUPRS_IS', '125')} ve "
            f"{oy('TUPRS_IS', '150')}", "tablo · Türkiye hisse")
    dogru(S["PGSUS_IS"]["150"]["orta"] < 0 and S["THYAO_IS"]["150"]["orta"] < 0, "tablo: Pegasus/THY aşağıda değil")
    s125, s150 = TA["senaryo"]["125"], TA["senaryo"]["150"]
    metinde(f"Yalnız petrolün payı TÜFE'ye iki ayda {sayi(s125['tufe_2ay_petrol'], 2, True)} (125 dolar) ve "
            f"{sayi(s150['tufe_2ay_petrol'], 2, True)} puan (150 dolar); TCMB'nin 12 aylık kuralıyla "
            f"{sayi(s125['tufe_12ay_tcmb'], 2, True)} ve {sayi(s150['tufe_12ay_tcmb'], 2, True)} puan", "tablo · TÜFE")
    metinde(f"Motorinin ÖTV'si Ekim'de {sayi(om['baz'], 0)}, Kasım'da {sayi(om['kasim'], 0)} TL", "tablo · ÖTV")
    metinde(f"cari açık/GSYH {yz(-EF['cari_gsyh'], 2)}'dan {yz(-ek['150']['petrol']['cari_gsyh'], 2)}–"
            f"{sayi(-ek['150']['petrol_gaz']['cari_gsyh'], 2)}'a çıkar", "tablo · cari")
    nyuk = V["BZ=F"]["yukselis"]["n"]
    sayim = {"guclu": 0, "orta": 0, "zayif": 0}
    for v in S.values():
        sayim[v["kanit"]] += 1
    metinde(f"{R['n_gun']} günün {nyuk}'ında devirden arındırılmış Brent'in 21 günlük değişimi pozitifti, ama bağımsız "
            f"epizot {SAYI_AD[len(P)]} ve 150 dolar sütunu fiilen Mart'a dayanıyor", "tablo · kanıt")
    n2s = sum(1 for v in S.values() if v["kanit_ayrinti"]["ikinci_sinama"])
    metinde(f"uzun tarihçesi olan {n2s} kalemde 2026 öncesinin pencereleri 2026'ya uygulandı", "tablo · kanıt")
    metinde(f"{len(S)} kalemin {sayim['guclu']}'i güçlü, {sayim['orta']}'u orta, {sayim['zayif']}'sı zayıf", "tablo · kanıt")
    x30 = R["x30"]
    dogru(x30["ilk"] >= "2026-03-01" and x30["son"] <= "2026-04-30", "tablo: 30 log puanı aşan günler Mart şokunda değil")
    once = TY["ozet"]["once"]
    metinde(f"S&P 500 o pencerelerin {yz(once['spx']['arti_pay'], 1)}'inde yükseldi, ABD 2 yıllık medyanda yalnız "
            f"{bp(once['us2y']['medyan'], 1)} arttı", "tablo · 2026 öncesi")
    dogru(once["n"] == 40, "2026 öncesi pencere sayısı 40 değil")

    # ── yönetici özeti: rakam şeridi
    metinde(f"{sayi(fark, 2)} dolar fiziki ile vadeli Brent arasındaki fark, 6 Ekim; 2000–2025'in en büyüğü "
            f"{sayi(tar['azami'], 2)}", "şerit")
    metinde(f"{yz(sik['125']['pay'], 2)} 1988'den bu yana vadeli Brent'in bir ayda en az {yz(y125, 1, True)} "
            f"yükseldiği günlerin payı ({sik['125']['epizot']} epizot)", "şerit")
    metinde(f"{bp(S['us2y']['150']['orta'])} 150 dolarda ABD 2 yıllık getirinin orta değeri", "şerit")
    metinde(f"{oy('XBANK.IS', '150')} 150 dolarda BIST Bankacılık endeksinin orta değeri", "şerit")
    metinde(f"{sayi(sh, 1)} milyar dolar Mart'ta swap hariç net rezervin 21 iş günlük erimesi, "
            f"{sayi(-m26['altin_fiyat_etkisi_21g'], 1)} milyarı altının fiyat etkisi; bugünkü stok {sayi(rz['swap_haric'], 1)}",
            "şerit")
    metinde(f"{sayi(s150['tufe_2ay_petrol'], 2, True)} puan 150 dolarda petrolün iki ayda TÜFE'ye katkısı", "şerit")
    metinde(f"{sayi(ot125['motorin_urun_tl_litre'], 2, True)} TL 125 dolarda motorinin litre maliyetindeki artış", "şerit")
    metinde(f"(KDV hariç; Kasım ÖTV'si {sayi(om['kasim'], 0)} TL)", "şerit")

    # ── giriş
    metinde(f"Brent'in ön vadesi 9 Ekim'i {sayi(baz, 2)} dolardan kapattı", "giriş")
    alinti("aa_com_tr_300d27ad0c", "ABD'nin İran'a yeni saldırı hazırlığı iddiaları Brent petrol fiyatını yüzde 4'ten fazla",
           "yeni saldırı hazırlığı haberleriyle gün içinde yüzde 4'ün üzerinde yükselmişti (Anadolu Ajansı)")
    alinti("bulten:2026-10-12", "Brent TSİ 04:54'te %1,47 düşüşle 103,18 dolara",
           "TSİ 04:54'te %1,47 düşüşle 103,18 dolardaydı (Reuters)")
    alinti("bulten:2026-10-12", "Donald Trump'ın Rusya ve Ukrayna'nın enerji tesislerine yönelik saldırıları durdurmayı "
                                "kabul ettiğini açıklamasının ardından",
           "Trump'ın Rusya ve Ukrayna'nın enerji tesislerine yönelik saldırıları durdurmayı kabul ettiğini açıklamasının "
           "ardından geldi (Bloomberg HT)")
    metinde(f"Bir ay burada {YT['ufuk']} iş günüdür; hedef gün {gun(Y['hedef_gun'])}", "giriş")
    metinde("dört kez %20'nin üstünde yükseldi", "giriş")
    dogru(len(P) == 4 and all(p["brent_yuzde"] > 20 for p in P), "giriş: dört pencerenin hepsi %20'nin üstünde değil")
    alinti("bloomberght_com_90cce7c497", "aralık ayı Brent petrol fiyat tahminini varil başına 85 dolardan 90 dolara",
           "Goldman Sachs 12 Ekim'de Aralık ayı Brent tahminini 85 dolardan 90 dolara yükseltti (Bloomberg HT)")
    alinti("oilprice_com_b12323df4c", "Reuters' September poll puts the average 2026 Brent price at $89.05",
           "Eylül sonundaki Reuters anketi 2026 ortalamasını 89,05 dolar veriyordu (OilPrice)")

    # ── Bölüm 1
    metinde(f"2000–2025 arasındaki {sayi(tar['n'], 0)} ortak günde farkın medyanı {sayi(tar['medyan'], 2)} dolar, "
            f"günlerin %99'unda fark {sayi(tar['p99'], 2)} doların altında", "B1 · tarihçe")
    metinde(f"6 Ekim'de fiziki Brent {sayi(fiz, 2)}, vadeli {sayi(vad, 2)} dolardı: fark {sayi(fark, 2)} dolar", "B1")
    metinde(f"2000–2025'in en büyük farkı {sayi(tar['azami'], 2)} dolardı ({gun(tar['azami_gun'])})", "B1")
    metinde(f"Fark 2 Ekim'de {sayi(IB['fark_zirve_2026'], 2)} dolarla zirve yaptı (fiziki "
            f"{sayi(IB['fark_zirve_2026_fiziki'], 2)}, vadeli {sayi(IB['fark_zirve_2026_vadeli'], 2)})", "B1")
    dogru(IB["fark_zirve_2026_gun"] == "2026-10-02", "fark zirvesinin günü 2 Ekim değil")
    ay26 = IB["aylik_2026"]
    metinde(f"Nisan'da {sayi(ay26['2026-04']['fark'], 2)} dolardı, Temmuz'da kapandı ({sayi(ay26['2026-07']['fark'], 2)}), "
            f"Eylül'de {sayi(ay26['2026-09']['fark'], 2)}'ya, Ekim'in ilk {SAYI_AD[IB['ekim_gun']]} gününde "
            f"{sayi(IB['ekim_ort_fark'], 2)} dolara çıktı", "B1 · aylık")
    dogru(abs(ay26["2026-07"]["fark"]) < 0.5 < 10 < ay26["2026-04"]["fark"] and ay26["2026-09"]["fark"] > 10,
          "B1: farkın iki dalgası (Nisan açık, Temmuz kapalı, Eylül açık) tutmuyor")
    alinti("oilprice_com_3cf37f38d0", "The European diesel stock release, droned tankers in the Strait of Hormuz, and "
                                      "China reinstating its refined product export ban have all played their part in "
                                      "this week's extremely volatile trading",
           "OilPrice'ın 2 Ekim notu haftanın oynaklığını Avrupa'nın dizel stoku salımına, Hürmüz'de insansız hava aracıyla "
           "vurulan tankerlere ve Çin'in rafine ürün ihracat yasağını yeniden getirmesine bağlıyor")
    alinti("oilprice_com_3cf37f38d0", "with ICE Brent edging lower to $101 per barrel", "vadeli 101 dolara gerilerken")
    alinti("oilprice_com_3cf37f38d0", "jumping above $120 per barrel. This suggests the physical market is a lot tighter "
                                      "than news headlines would care to admit",
           "fiziki göstergenin 120 doların üstüne çıkmasını ise fiziki piyasanın başlıkların söylediğinden çok daha sıkı "
           "olmasına yoruyor")
    r2 = IB["ithalat_birim_deger_r2"]
    metinde(f"(aynı ay ve bir ay gecikmeyle R² {sayi(r2['fiziki'], 2)}, vadeliyle {sayi(r2['vadeli'], 2)}; "
            f"{IB['ithalat_birim_deger_n']} ay, {ay_ad(IB['ithalat_birim_deger_ilk'] + '-01')} "
            f"{IB['ithalat_birim_deger_ilk'][:4]}–{ay_ad(IB['ithalat_birim_deger_son'] + '-01')} "
            f"{IB['ithalat_birim_deger_son'][:4]})", "B1 · R²")
    metinde(f"fiziki kargoyu {sayi(125 + fark, 2)} dolara taşır, fiziki fiyatın {gun(IB['fiziki_rekor']['gun'])}'deki "
            f"rekorunun ({sayi(IB['fiziki_rekor']['deger'], 2)}) üstüne", "B1 · fiziki 125")
    dogru(125 + fark > IB["fiziki_rekor"]["deger"], "B1: 125 + fark rekorun üstünde değil")
    metinde(f"2026'nın fiziki zirvesi {sayi(IB['fiziki_zirve_2026'], 2)} dolardı ({gun_ay(IB['fiziki_zirve_2026_gun'])})",
            "B1 · fiziki zirve")
    ku = o["kaynak_uyumu"]
    metinde(f"CNBC'nin ön vade serisiyle örtüşen {ku['ortak_gun']} günün tamamında birebir aynı", "Şekil 01")
    dogru(ku["birebir_pay"] == 100.0, "Şekil 01: iki ön vade serisi birebir aynı değil")
    eg = Y["egri"]["brent"]
    metinde(f"9 Ekim'de Aralık 2026 kontratı {sayi(eg['BZZ26_NYM'], 2)}, Ocak 2027 {sayi(eg['BZF27_NYM'], 2)}, Aralık "
            f"2027 {sayi(eg['BZZ27_NYM'], 2)}, Aralık 2028 {sayi(eg['BZZ28_NYM'], 2)} dolar", "B1 · eğri")
    dogru(abs(eg["BZZ26_NYM"] - baz) < 1e-6 and Y["hedef_gun_on_vade"] == "BZF27_NYM",
          "B1: bugünün ön vadesi Aralık 2026 değil ya da hedef gün ön vadesi Ocak 2027 değil")
    a26 = Y["aralik26"]
    metinde(f"(31 Mart) {sayi(a26['2026-03-31']['fiyat'], 2)}, 1 Eylül'de {sayi(a26['2026-09-01']['fiyat'], 2)} dolardı",
            "B1 · Aralık kontratı")
    metinde(f"Ocak kontratının {sayi(ocak, 2)}'ten 125'e, {yz(yd125, 1, True)} yükselmesidir; 150 için {yz(yd150, 1, True)}",
            "B1 · devirsiz")
    metinde(f"vade devrinin kendisi yüzünden {sayi(Y['devir_payi'], 2)} log puan aşağı kayar", "B1 · devir payı")
    metinde(f"ön vade bugünün Ocak 2027 kontratıdır, o kontrat da {sayi(ocak, 2)} dolarda", "B1 · Ocak kontratı")
    bos = R["devir"]["wti_bosluk_2026"]
    du, dxb = S["us2y"]["duyarlilik_125"], S["XBANK.IS"]["duyarlilik_125"]
    metinde(f"Aralık–Ocak farkının 30 Ekim'deki devirde bugünkü {sayi(Y['devir_payi'], 2)} log puanda kalacağını varsayar",
            "B1 · üçüncü koşul")
    metinde(f"2026'da devir günündeki fark 1 Ekim'de {sayi(-bos['2026-10-01'], 2)}, 1 Nisan'da {sayi(-bos['2026-04-01'], 2)} "
            "log puandı", "B1 · üçüncü koşul")
    metinde(f"125 dolarda bile {sayi(Y['senaryo']['125']['log_devirsiz'], 2)} değil {sayi(du['x'], 2)} log puan olur",
            "B1 · üçüncü koşul")
    metinde(f"ABD 2 yıllık {ob('us2y', '125')} yerine {bp(du['orta'])}, BIST Bankacılık {oy('XBANK.IS', '125')} yerine "
            f"{yz(dxb['orta_yuzde'], 1, True)}", "B1 · üçüncü koşul")
    dogru(du["devir_gunu"] == "2026-04-01" and abs(du["devir_farki"] + bos["2026-04-01"]) < 1e-9
          and abs(du["x"] - (Y["senaryo"]["125"]["log"] + du["devir_farki"])) < 1e-9,
          "B1: duyarlılığın x'i ön vade değişimi + 1 Nisan devir farkı değil")
    metinde("%90 aralı", "yöntem sabiti (%90 aralık, 1,645)")

    # ── Bölüm 2
    metinde(f"1988'den bu yana {sayi(sik['n'], 0)} iş günü için", "B2")
    metinde(f"Bir ayda en az {yz(y125, 1, True)}'lük yükseliş günlerin {yz(sik['125']['pay'], 2)}'ünde görüldü: "
            f"{sik['125']['gun']} gün, {sik['125']['epizot']} ayrı epizot (araya en az {YT['ufuk']} iş günü", "B2")
    e150 = sik["150"]["epizotlar"]
    metinde(f"{yz(y150, 1, True)} ve üstü ise yalnız {sik['150']['gun']} günde ve {SAYI_AD[len(e150)]} epizotta görüldü: "
            f"{gun_ay(e150[0]['ilk'])}–{gun(e150[0]['son'])} arasında", "B2 · 150 epizotları")
    metinde(f"ve {int(e150[1]['ilk'][8:10])}–{gun(e150[1]['son'])}'da", "B2 · 150 epizotları")
    metinde(f"İkisi de düşük bir tabandan başladı: pencerelerin başlangıç fiyatı {e150[0]['ilk'][:4]}'de en çok "
            f"{sayi(e150[0]['bas_azami'], 2)}, {e150[1]['ilk'][:4]}'da en çok {sayi(e150[1]['bas_azami'], 2)} dolardı",
            "B2 · 150 tabanı")
    dogru(all(e["bas_azami"] < 80 for e in e150), "B2: 150 epizotlarından biri 80 doların üstünden başlıyor")
    e100 = [e for e in sik["125"]["epizotlar"] if e["bas_azami"] >= 100]
    metinde(f"{yz(y150, 1, True)}'lik bir yükseliş hiç görülmedi; {yz(y125, 1, True)}'lük yükseliş yüz doların "
            f"üstünden yalnız {SAYI_AD[len(e100)]} kez başladı, {gun(e100[0]['son'])}'de ve {gun(e100[1]['son'])}'de "
            "biten pencerelerde", "B2 · yüz doların üstü")
    dogru(len(e100) == 2 and all(e["ilk"] == e["son"] for e in e100), "B2: yüz doların üstünden başlayan epizot sayımı")
    metinde("ikisinde de 80 doların altından başlayarak", "tez · 150 tabanı")
    metinde(f"{SAYI_AD[len(e150)]} epizotta ve hiçbiri yüz doların üstünden başlamadı", "tablo · 150 tabanı")
    fz = Y["siklik"]["fiziki_1987"]["150"]
    metinde(f"Fiziki Brent'te bir ayda {yz(y150, 1, True)}'lik yükselişin 1987'den bu yana {SAYI_AD[fz['epizot']]} epizodu "
            "var: Ağustos–Eylül 1990, Mayıs–Haziran 2020, Mart–Nisan 2026 ve Temmuz 2026", "B2")
    dogru([(e["ilk"][:7], e["son"][:7]) for e in fz["epizotlar"]]
          == [("1990-08", "1990-09"), ("2020-05", "2020-06"), ("2026-03", "2026-04"), ("2026-07", "2026-07")],
          "B2: fizikinin 150 epizotları yazıdakiler değil")
    fz125 = Y["siklik"]["fiziki_1987"]["125"]
    metinde(f"{yz(y125, 1, True)} eşiğinde fiziki seride {fz125['epizot']} epizot var, günlerin {yz(fz125['pay'], 2)}'i",
            "B2 · fiziki 125")
    dogru(fz125["pay"] > sik["125"]["pay"], "B2: fiziki seride 125 eşiği vadeliden sık değil")
    metinde(f"takvim boyu {YT['takvim_tavan']} günü aşan pencereler atıldı", "Şekil 03")
    metinde(f"Çubuklar 2,5 puanlık kovalardaki", "Şekil 03 · kova")
    metinde(f"125 dolar için log ölçüde {sayi(Y['senaryo']['125']['log'], 2)}, 150 dolar için "
            f"{sayi(Y['senaryo']['150']['log'], 2)}", "Şekil 03 · eşik")
    metinde(f"OVX 9 Ekim'de {sayi(ov['deger'], 2)}'daydı: 2007'den bu yana günlerin {yz(ov['yuzdelik_2007'], 1)}'ünden "
            f"yüksek, ama 2026 zirvesinin ({gun_ay(ov['zirve_2026_gun'])}, {sayi(ov['zirve_2026'], 2)}) çok altında",
            "B2 · OVX")
    metinde(f"bir aylık standart sapmayı {yz(ov['aylik_sigma'], 1)} yapar", "B2 · OVX")
    metinde(f"Ocak kontratının (bugün {sayi(ov['dayanak'], 2)} dolar) ay sonunda 125'in üstünde olmasına "
            f"{yz(ov['olasilik']['125'], 1)}, 150'nin üstünde olmasına {yz(ov['olasilik']['150'], 1)} olasılık verir; ön "
            "vadenin ay içinde en az bir kez değmesine (30 Ekim'e kadar Aralık, sonra Ocak kontratıyla) "
            f"{yz(ov['dokunma_olasiligi']['125'], 1)} ve {yz(ov['dokunma_olasiligi']['150'], 1)}", "B2 · olasılık")
    dogru(ov["bacak_gun"] == {"aralik": 15, "ocak": 6, "devir_gunu": "2026-11-02"}, "B2: değme olasılığının bacakları değişti")
    metinde(f"son 21 iş günü {yz(Y['gerceklesen_oyn_21g'], 1)}, Mart–Ekim arası {yz(Y['gerceklesen_oyn_mart_ekim'], 1)}",
            "B2 · gerçekleşen oynaklık")
    dogru(Y["gerceklesen_oyn_21g"] < ov["deger"] < Y["gerceklesen_oyn_mart_ekim"],
          "B2: OVX son ayın gerçekleşeninin üstünde ve Mart–Ekim'inkinin altında değil")
    metinde(f"kapanış rekoru {gun(rk['gun'])}'deki {sayi(rk['vadeli_kapanis'], 2)} dolar", "B2 · rekor")
    metinde(f"ABD TÜFE'si o günden {ay_ad(rk['tufe_son_ay'] + '-01')} {rk['tufe_son_ay'][:4]}'ya "
            f"{sayi(rk['tufe_carpani'], 3)} katına çıktı, yani o rekor bugünün dolarıyla {sayi(rk['bugunun_dolariyla'], 2)}",
            "B2 · reel")
    metinde(f"2008 dolarıyla {sayi(rk['senaryo_2008_dolariyla']['125'], 2)} ve "
            f"{sayi(rk['senaryo_2008_dolariyla']['150'], 2)} eder", "B2 · reel")
    alinti("energypolicy_columbia_edu_66a2cb4655", "By 2019 (the last data set before Covid) global oil intensity was 0.43 "
                                                   "barrel per $1,000 of global GDP-a 56% decline",
           "2019'da 0,43 varil kullanılıyordu, %56 daha az (Columbia Üniversitesi)")
    alinti("bostonfed_org_c293fdc06a", "the current conflict has generated a real oil price shock of about 33 percent",
           "Boston Fed'e göre bu savaşın yarattığı reel petrol şoku yaklaşık %33")
    alinti("bostonfed_org_c293fdc06a", "a 33 percent oil shock was associated with an increase in year-ahead (the "
                                       "subsequent 12 months) total PCE inflation of about 2.2 percentage points before the "
                                       "mid-1980s, the estimated effect has gradually declined to approximately 1.5 "
                                       "percentage points today",
           "bugün %33'lük bir şok ABD'de bir sonraki yılın PCE enflasyonunu yaklaşık 1,5 puan artırıyor, 1980'lerin "
           "ortasından önce bu etki 2,2 puandı")

    # ── Bölüm 3
    alinti("aeaweb_org_acb79ef7d1", "Not All Oil Price Shocks Are Alike", "petrol fiyatı şoklarının hepsi aynı değildir")
    ta, tr = TY["ozet"]["once_talep"], TY["ozet"]["once_arz"]
    metinde(f"2026 öncesinin talep baskın yükselişlerinde S&P 500 medyanda {yz(ta['spx']['medyan_yuzde'], 1, True)} "
            f"yükseldi, arz baskın olanlarda {yz(tr['spx']['medyan_yuzde'], 1, True)}", "B3")
    alinti("bulten:2026-09-17", "Fed 16 Eylül'de politika faizini %3,75-%4,00 aralığına çıkardı",
           "Fed 16 Eylül'de politika faizini %3,75–%4,00 aralığına çıkardı")
    metinde(f"{gun(R['ilk_degisim'])} ile {gun(R['son'])} arasında 21 iş günlük değişimi hesaplanabilen {R['n_gun']} işlem "
            f"gününde, Brent'in 21 iş günlük yükselişinin {yz(YT['pencere_esik'], 0)}'i aştığı ve birbirinden {YT['pencere_ara']} takvim gününden fazla "
            f"uzak {SAYI_AD[len(P)]} pencere var", "B3 · pencere seçimi")
    for ad, p in zip(("Mart", "Mayıs", "Temmuz", "Eylül"), P):
        metinde(f"{ad} ({gun_ay(p['bas'])}–{gun_ay(p['son'])}): {sayi(p['brent_bas'], 2)}'den {sayi(p['brent_son'], 2)} "
                f"dolara, {yz(p['brent_yuzde'], 1, True)}", f"B3 · pencere {ad}")
    yak = sorted(range(4), key=lambda i: abs(P[i]["brent_yuzde"] - yd125))[:2]
    dogru(sorted(yak) == [1, 3], f"125 senaryosuna en yakın pencereler Mayıs ve Eylül değil: {yak}")
    dogru(min(range(4), key=lambda i: abs(P[i]["brent_yuzde"] - yd150)) == 0, "150 senaryosuna en yakın pencere Mart değil")

    def liste(k, b=1, birim="yuzde"):
        if birim == "bp":
            xs = [sayi(x, 0, True) for x in V[k]["pencere"]]
            return f"{xs[0]}, {xs[1]}, {xs[2]} ve {xs[3]} bp"
        xs = [yz(x, b, True) for x in V[k]["pencere_yuzde"]]
        return f"{xs[0]}, {xs[1]}, {xs[2]}, {xs[3]}"

    metinde(f"ABD 2 yıllık getirisi ({liste('us2y', birim='bp')})", "B3 · us2y")
    metinde(f"ABD havayolu hisseleri ({liste('JETS')})", "B3 · JETS")
    metinde(f"BIST 100 ({liste('XU100.IS')})", "B3 · BIST 100")
    dogru(all(x < 0 for x in V["HYG"]["pencere"]), "B3: HYG dört pencerede düşmedi")
    metinde(f"USD/TRY ({yz(min(u), 1, True)} ile {yz(max(u), 1, True)} arası)", "B3 · USD/TRY")
    dogru(sum(x > 0 for x in V["^GSPC"]["pencere"]) == 2, "B3: S&P 500 ikisinde artı değil")
    alt = [i for i, x in enumerate(V["GC=F"]["pencere"]) if x > 0]
    dogru(alt == [2], f"B3: altın yalnız Temmuz'da artı değil: {alt}")
    n2 = V["n2y"]["pencere"]
    dogru(sum(x > 0 for x in n2[:3]) == 3, "B3: DİBS ilk üç pencerede artmadı")
    metinde(f"Eylül'de {sayi(n2[3], 0, True)} bp", "B3 · DİBS")
    tl = V["tlref"]["pencere"]
    metinde(f"TLREF (Mart'ta {sayi(tl[0], 0, True)} bp, Eylül'de {sayi(tl[3], 0, True)} bp)", "B3 · TLREF")
    metinde(f"{R['n_gun']} günün bu değişimin pozitif olduğu {nyuk}'ından kestirildi", "B3 · doğru")
    dz = R["yukselis_dizileri"]
    buy = max(dz, key=lambda d: d["gun"])
    metinde(f"bu günler {SAYI_AD[len(dz)]} kesintisiz diziye toplanıyor ve biri ({gun_ay(buy['bas'])}–{gun_ay(buy['son'])}) "
            f"{nyuk} günün {buy['gun']}'sini, Brent'in 30 log puandan fazla yükseldiği {R['x30']['gun']} günün de tamamını "
            "taşıyor", "B3 · diziler")
    dogru(R["yukselis_gunu"] == nyuk and sum(d["gun"] for d in dz) == nyuk, "B3: dizilerin gün toplamı yükseliş günü sayısı değil")
    dogru(buy["bas"] <= R["x30"]["ilk"] and R["x30"]["son"] <= buy["son"], "B3: 30 log puanı aşan günler en büyük dizide değil")
    metinde(f"standart hata {YT['nw_gecikme']} gecikmeli Newey–West", "B3 · NW")
    metinde(f"ABD 2 yıllıkta yükseliş günlerinin eğimi {sayi(V['us2y']['yukselis']['egim'], 2, True)} bp, düşüş "
            f"günlerinde işaret dönüyor ({sayi(V['us2y']['dusus']['egim'], 2, True)})", "B3 · asimetri")
    metinde(f"({YT['loo_once']} iş günü öncesinden {YT['loo_sonra']} iş günü sonrasına)", "B3 · LOO")
    metinde(f"2026 öncesinin {once['n']} büyük yükselişinden", "B3 · OOS")
    metinde(f"Üçüncüsü, uzun tarihçesi olan {n2s} kalemde", "B3 · OOS")
    metinde(f"Üçüncü sınama yalnız {n2s} kalemde yapılabildiği için", "B3 · OOS")
    dogru(TCB["us2y"]["egitimde_kalan_pencereler"][3] == [P[0]["son"], P[1]["son"]],
          "B3: Eylül yalnız Mart ve Mayıs'tan tahmin edilmiyor")
    metinde(f"{len(S)} kalemin {sayim['guclu']}'i güçlü, {sayim['orta']}'u orta, {sayim['zayif']}'sı zayıf", "B3 · sayım")
    egi = sorted(k for k, v in S.items() if "egilim" in v["kanit_ayrinti"]["orta_sebep"])
    dogru(egi == sorted(["us10y", "reel10y", "USDTRY=X", "TUPRS_IS"]),
          f"B3: görüşsüz kıyasın ortaya indirdiği kalemler yazıdakiler değil: {egi}")
    kap = {h: [0, 0] for h in ("guclu", "orta", "zayif")}
    for k, v in S.items():
        if k in TCB:
            kap[v["kanit"]][0] += TCB[k]["kapsanan"]
            kap[v["kanit"]][1] += sum(1 for c in TCB[k]["kapsama"] if c is not None)
    metinde(f"güçlü kalemlerde gerçekleşeni {kap['guclu'][1]} denemenin {kap['guclu'][0]}'inde, zayıf kalemlerde "
            f"{kap['zayif'][1]}'ün {kap['zayif'][0]}'ünde kapsadı", "B3 · kapsama")
    metinde("zayıf satırlarda aralık %90 güven vermez", "B3 · kapsama (yöntem sabiti)")
    dogru(kap["zayif"][0] / kap["zayif"][1] < 0.85 < kap["guclu"][0] / kap["guclu"][1],
          "B3: kapsama hükmü (zayıfta %90'ın altında, güçlüde yakın) tutmuyor")
    x125, x150 = Y["senaryo"]["125"]["log_devirsiz"], Y["senaryo"]["150"]["log_devirsiz"]
    metinde(f"(log ölçüde {sayi(x125, 2)} ve {sayi(x150, 2)})", "B3 · x")
    sp = S["^GSPC"]
    metinde(f"125 dolarda {sayi(sp['125']['petrol_payi'], 1, True)}, 150 dolarda {sayi(sp['150']['petrol_payi'], 1, True)} "
            f"puandır (log ölçü) ve sabit ({sayi(sp['sabit'], 1, True)}) ilkini neredeyse götürüyor; oysa endeksin bu dönemdeki "
            f"ortalama 21 iş günlük değişimi {sayi(sp['ortalama_21g'], 1, True)}, Brent'in bir ayda ±5 log puan içinde kaldığı "
            f"günlerde {sayi(sp['yatay_brent_ortalama'], 1, True)}", "B3 · S&P payı")
    dogru(sp["sabit"] > max(sp["ortalama_21g"], sp["yatay_brent_ortalama"]), "B3: sabit gerçekleşen eğilimden büyük değil")
    up2 = V["us2y"]["pencere"]
    metinde(f"ABD 2 yıllık {bp(S['us2y']['125']['orta'])}, o iki pencerede {sayi(up2[1], 0, True)} ve {bp(up2[3])}",
            "B3 · hücre/pencere")
    ayni = [k for k, v in S.items() if v["pencere_isaret"]["n"] == 4 and max(v["pencere_isaret"]["arti"], v["pencere_isaret"]["eksi"]) == 4]
    kucuk = [k for k in ayni if abs(S[k]["125"]["orta"]) < min(abs(V[k]["pencere"][1]), abs(V[k]["pencere"][3]))]
    dogru(len(kucuk) > len(ayni) / 2, f"B3: 125 hücresi çoğu kalemde Mayıs/Eylül'den küçük değil ({len(kucuk)}/{len(ayni)})")
    metinde(f"Tablodaki {oy('^GSPC', '125')}", "B3 · S&P")

    # ── Bölüm 4
    metinde(f"WTI Brent'i birebir izliyor (eğim {sayi(S['CL=F']['egim'], 2)})", "B4")
    metinde(f"Motorin vadelisi Brent'ten hızlı (eğim {sayi(S['HO=F']['egim'], 2)}): 150 dolarda galonu "
            f"{sayi(S['HO=F']['150']['seviye'], 3)} dolar", "B4")
    metinde(f"2 yıllık getiri 125 dolarda {yz(S['us2y']['125']['seviye'], 2)}'e, 150 dolarda "
            f"{yz(S['us2y']['150']['seviye'], 2)}'e çıkıyor", "B4 · faiz")
    dogru(S["us2y"]["150"]["orta"] > S["us10y"]["150"]["orta"] > S["us30y"]["150"]["orta"], "B4: eğri yassılaşmıyor")
    metinde(f"2 yıllığın bütün günlerdeki ortalama 21 günlük değişimi {bp(S['us2y']['ortalama_21g'], 1)}", "B4 · eğilim")
    metinde(f"(hata {sayi(TCB['us2y']['rmse'], 1)}'ya karşı {sayi(TCB['us2y']['rmse_egilim'], 1)} bp), 10 yıllıkta "
            "iyileştirmiyor; 10 yıllığın kanıtı bu yüzden orta", "B4 · görüşsüz kıyas")
    dogru(S["us10y"]["kanit"] == "orta" and S["reel10y"]["kanit"] == "orta", "B4: 10 yıllık ve reel getiri orta değil")
    metinde(f"10 yıllıktaki artışın çoğu reel faizden geliyor: reel getiri {ob('reel10y', '125')} ve "
            f"{bp(S['reel10y']['150']['orta'])}, nominal getiri {ob('us10y', '125')} ve {bp(S['us10y']['150']['orta'])}; "
            f"5 yıllık başabaş {ob('be5y', '125')} ve {bp(S['be5y']['150']['orta'])}", "B4 · ayrıştırma")
    dogru(all(S["reel10y"][a]["orta"] > 0.5 * S["us10y"][a]["orta"] for a in ("125", "150")),
          "B4: 10 yıllıktaki artışın çoğu reel faizden gelmiyor")
    alinti("bbc_co_uk_fb865641ef", "rates on 10-year government borrowing hitting 5%",
           "bunlardan biri 10 yıllık getirinin %5'e ulaşmasıydı (BBC)")
    kaynakta("bbc_co_uk_fb865641ef", "there would be \"economic red lines\" that the Trump administration would be unwilling to cross")
    metinde(f"10 yıllık 9 Ekim'de zaten {yz(S['us10y']['125']['seviye'] - S['us10y']['125']['orta'] / 100, 2)}'te",
            "B4 · 10y bugün")
    dogru(abs((S["us10y"]["125"]["seviye"] - S["us10y"]["125"]["orta"] / 100) - S["us10y"]["son_deger"]) < 1e-6,
          "B4: 10 yıllığın bugünkü değeri tutarsız")
    dogru(all(x < 0 for x in V["HYG"]["pencere"]), "B4: HYG dördünde düşmedi")
    metinde(f"gelişen ülke dolar tahvilleri 150 dolarda {oy('EMB', '150')}", "B4 · EMB")
    metinde(f"150 dolarda {oy('^STOXX', '150')}, {oy('^FCHI', '150')} ve {oy('^RUT', '150')}", "B4 · hisse")
    dogru(S["^GDAXI"]["kanit"] == "orta", "B4: DAX kanıtı orta değil")
    metinde(f"BAE hisseleri {oy('UAE', '125')} ve {oy('UAE', '150')}", "B4 · BAE")
    metinde(f"Hindistan'ın hisseleri {oy('INDA', '125')} ve {oy('INDA', '150')}", "B4 · Hindistan")
    ks = V["KSA"]["pencere_yuzde"]
    metinde(f"Suudi Arabistan hisseleri dört pencerenin dördünde düştü ({yz(max(ks), 1, True)} ile {yz(min(ks), 1, True)} "
            "arası)", "B4 · KSA")
    dogru(all(x < 0 for x in ks) and S["KSA"]["kanit"] == "zayif", "B4: Suudi Arabistan dördünde düşmedi ya da kanıtı zayıf değil")
    dogru(S["ITA"]["kanit"] == "zayif", "B4: savunma kanıtı zayıf değil")
    metinde(f"(USD/ZAR 150 dolarda {oy('zar', '150')})", "B4 · ZAR")
    metinde(f"USD/CHF {oy('USDCHF=X', '125')} ve {oy('USDCHF=X', '150')}", "B4 · CHF")
    metinde(f"Euro orta kanıtla {oy('EURUSD=X', '125')} ve {oy('EURUSD=X', '150')}", "B4 · EUR")
    dogru(S["EURUSD=X"]["kanit"] == "orta", "B4: euro kanıtı orta değil")
    alinti("eia_gov_5c51486935", "consumers could expect to see a 2.4-cent-per-gallon change in retail gasoline prices",
           "varil başına 1 dolarlık değişim benzinde galon başına yaklaşık 2,4 sent eder")
    alinti("eia_gov_5c51486935", "generally about 50% of the crude oil price change is usually passed on to consumers at "
                                 "the pump within two weeks, and 80% is generally passed on within four weeks",
           "değişimin genellikle %50'si iki haftada, %80'i dört haftada pompaya yansır")
    bz = AE["benzin_pompa_gecis"]
    dogru(bz["ilk_hafta"].startswith("2005"), "B4: pompa geçişinin örneklemi 2005'te başlamıyor")
    mz = AE["motorin_pompa_gecis"]
    metinde(f"(dört haftalık fark, 2005'ten bu yana {sayi(bz['n'], 0)} hafta) benzinde varilin galon karşılığının "
            f"{sayi(bz['galon_basina_dolar_per_galon'], 2)}'i, motorinde {sayi(mz['galon_basina_dolar_per_galon'], 2)}'ü",
            "B4 · pompa")
    metinde(f"bugünkü {sayi(bz['son_fiyat'], 3)} dolarlık benzin 125 dolarda {sayi(AS['125']['benzin']['seviye'], 2)}, "
            f"150 dolarda {sayi(AS['150']['benzin']['seviye'], 2)} dolar/galona çıkar", "B4 · pompa")
    metinde(f"pompa ile vadeli arasındaki bugünkü fark korunursa benzin 125 dolarda "
            f"{sayi(AS['125']['benzin']['seviye_vadeli_yolu'], 2)}, 150 dolarda "
            f"{sayi(AS['150']['benzin']['seviye_vadeli_yolu'], 2)} olur", "B4 · pompa vadeli yolu")
    metinde(f"İki yolda da 150 dolar {bz['rekor_hafta'][:4]}'deki {sayi(bz['rekor'], 3)} dolarlık rekorun üstünde", "B4 · rekor")
    dogru(AS["150"]["benzin"]["seviye_vadeli_yolu"] > bz["rekor"], "B4: vadeli yolunda 150 dolar rekorun üstünde değil")
    dogru(AS["150"]["benzin"]["seviye"] > bz["rekor"] > AS["125"]["benzin"]["seviye"], "B4: benzin rekor kıyası")
    alinti("bbc_co_uk_fb865641ef", "gasoline topping $5 a gallon", "benzinin galonda 5 doları aşmasıydı (BBC)")
    metinde(f"Motorin pompası {sayi(mz['son_fiyat'], 3)} dolarda; {gun_ay(mz['rekor_hafta'])}'de {sayi(mz['rekor'], 3)} "
            f"ile rekor kırmıştı. 150 dolarda ham petrol yoluyla {sayi(AS['150']['motorin']['seviye'], 2)}'a, ürün vadelisi "
            f"yoluyla {sayi(AS['150']['motorin']['seviye_vadeli_yolu'], 2)}'ya çıkar", "B4 · motorin")
    metinde(f"125 dolarda {sayi(AS['125']['tufe_seviye_2000'], 2, True)}, 150 dolarda "
            f"{sayi(AS['150']['tufe_seviye_2000'], 2, True)} puan; 2015'ten bu yana ölçülen esneklikle "
            f"{sayi(AS['125']['tufe_seviye_2015'], 2, True)} ve {sayi(AS['150']['tufe_seviye_2015'], 2, True)}", "B4 · ABD TÜFE")
    alinti("ecb_europa_eu_17891571a8", "In general, the pass-through is fast, within one or two months, and complete",
           "ECB'ye göre ham petrol fiyatının pompaya geçişi hızlı, bir iki ay içinde ve tam")
    alinti("ecb_europa_eu_17891571a8", "an increase of €0.10 per litre in crude oil prices usually translates into an "
                                       "increase of €0.10 per litre in pre-tax pump prices",
           "ham petroldeki litre başına 0,10 avroluk artış vergi öncesi pompa fiyatında genellikle 0,10 avroluk artışa dönüşür")
    alinti("ecb_europa_eu_17891571a8", "By the first week of April, retail diesel prices averaged €2.18 per litre across "
                                       "the euro area compared with €1.63 per litre in late February",
           "Nisan'ın ilk haftasında euro bölgesinde motorinin litresi 2,18 avroydu, Şubat sonunda 1,63")
    alinti("ecb_europa_eu_1fb202a306", "Oil prices are assumed to peak at USD 145 per barrel and gas prices at €106 per MWh "
                                       "in the second quarter of 2026",
           "ağır senaryo petrolün 2026'nın ikinci çeyreğinde 145 dolarda zirve yapmasını varsayıyordu")
    alinti("ecb_europa_eu_1fb202a306", "by 1.8 percentage points in 2026, 2.8 percentage points in 2027",
           "baz senaryoya göre 2026'da 1,8, 2027'de 2,8 puan yukarı taşıyordu")
    alinti("ecb_europa_eu_1fb202a306", "Economic growth would be 0.4-0.5 percentage points lower in 2026-27",
           "GSYH büyümesi 2026–27'de 0,4–0,5 puan aşağı")

    # ── Bölüm 5
    metinde(f"politika faizi {yz(m26['politika_son'], 0)}'de kaldı", "B5")
    alinti("ppk:2026-14-TR", "ağırlıklı ortalama fonlama maliyetinin, Merkez Bankası gecelik vadede borç verme faiz oranı "
                             "olan yüzde 40'ta oluşması sağlanmıştır",
           "ağırlıklı ortalama fonlama maliyeti koridorun tavanı olan %40'ta oluştu")
    kaynakta("ppk:2026-14-TR", "Türk lirası uzlaşmalı vadeli döviz satım")
    ub = T["ust_bant_2026"]
    metinde(f"Repo ihalesi {ub['is_gunu']} iş günü kapalı kaldı ({gun_ay(ub['ara'])}–{gun_ay(ub['acilis'])})", "B5 · ara")
    kaynakta("ppk:2026-42-TR", "23 Ağustos 2026 tarihli duyurusu ile 1 Mart 2026 tarihinde ara verilen bir hafta vadeli "
                               "repo ihalelerine tekrar başlanmasına")
    metinde(f"USD/TRY 21 iş günde {yz(m26['usdtry_tcmb_degisim'], 2, True)}; İstanbul kapanışıyla "
            f"{yz(m26['usdtry_ist18_degisim'], 2, True)}", "B5 · kur")
    dogru(m26["haftalik"][0]["doviz_satisi"] < 0 and m26["ihale_ara_ilk"] <= m26["haftalik"][0]["son"],
          "B5: döviz satışı ve fonlama ilk haftada birlikte başlamadı")
    metinde(f"21 iş günde {sayi(-m26['doviz_satisi_21g'], 2)} milyar dolarlık döviz satışı; swap hariç net rezervdeki "
            f"{sayi(sh, 1)} milyar dolarlık erimenin {sayi(-m26['altin_fiyat_etkisi_21g'], 1)} milyarı ise aynı dönemde düşen "
            f"altının fiyat etkisiydi. Aynı dönemde BIST 100 {yz(m26['xu100_degisim'], 2)} geriledi", "B5 · bedel")
    metinde(f"son gözlem {gun_ay(rz['gun'])}", "Şekil 06")
    metinde(f"{gun_ay(rz['gun'])}'de net rezerv {sayi(rz['net'], 2)}, swap hariç net rezerv {sayi(rz['swap_haric'], 2)}, "
            f"brüt rezerv {sayi(rz['brut'], 2)} milyar dolar", "B5 · bugün")
    dogru(sh > rz["swap_haric"], "B5: Mart erimesi bugünkü stoktan küçük")
    metinde(f"Mart'ın 21 günlük döviz satışını ({sayi(-m26['doviz_satisi_21g'], 2)}) bugünkü swap hariç stok "
            f"({sayi(rz['swap_haric'], 2)}) ancak karşılıyor; altının fiyat etkisiyle birlikte erimeyi ({sayi(sh, 1)}) "
            "karşılamıyor", "B5 · stok")
    dogru(-m26["doviz_satisi_21g"] < rz["swap_haric"] < sh, "B5: stok satışı karşılayıp erimeyi karşılamama hükmü tutmuyor")
    metinde(f"politika faizi {yz(fb['politika'], 0)}, koridor {yz(fb['koridor_alt'], 1)}–{yz(fb['koridor_ust'], 0)}, "
            f"TLREF {gun_ay(fb['gun'])}'da {yz(fb['tlref'], 2)}", "B5 · fonlama")
    metinde(f"yaklaşık {sayi((fb['koridor_ust'] - fb['tlref']) * 100, 0)} baz puan yukarı", "B5 · tavana mesafe")
    up = V["USDTRY=X"]["pencere_yuzde"]
    metinde(f"({yz(up[0], 1, True)}, {yz(up[1], 1, True)}, {yz(up[2], 1, True)} ve {yz(up[3], 1, True)})", "B5 · rejim")
    metinde(f"Senaryo tablosunda 125 dolarda {sv('USDTRY=X', '125')}, 150 dolarda {sv('USDTRY=X', '150')}", "B5 · rejim")
    sw = V["swap_haric_net_rezerv_usd"]
    Ssw, Lsw = S["swap_haric_net_rezerv_usd"], TCB["swap_haric_net_rezerv_usd"]
    metinde(f"{sayi(-sw['yukselis']['egim'], 2)} milyar dolarlık erimeyle eşlik ediyor; doğrunun {sayi(Ssw['sabit'], 1, True)} "
            f"milyar dolarlık sabiti bunun bir bölümünü götürüyor ve hücre 125 dolarda {of('swap_haric_net_rezerv_usd', '125')}, "
            f"150 dolarda {of('swap_haric_net_rezerv_usd', '150')} milyar dolar", "B5 · rezerv eğimi")
    metinde(f"rezervin bu dönemdeki ortalama 21 günlük değişimi {sayi(Ssw['ortalama_21g'], 1)} milyar dolar", "B5 · rezerv eğilim")
    metinde(f"({sayi(Lsw['rmse'], 1)}'e karşı {sayi(Lsw['rmse_sifir'], 1)} milyar dolar); doğru Mart'taki "
            f"{sayi(-Lsw['gercek'][0], 1)} milyar dolarlık erimeyi {sayi(-Lsw['tahmin'][0], 1)} milyar dolar diye tahmin ediyor, "
            "Temmuz'da yönü de tutmuyor", "B5 · rezerv sınama")
    dogru(Ssw["kanit"] == "zayif" and Lsw["isaret_tutan"] == 3 and Lsw["rmse"] >= Lsw["rmse_sifir"]
          and Lsw["tahmin"][2] * Lsw["gercek"][2] < 0 and sw["pencere"][2] > 0, "B5: rezerv kanıtının gerekçesi tutmuyor")
    metinde(f"Mart penceresinde ({gun_ay(P[0]['bas'])}–{gun_ay(P[0]['son'])}) erime {sayi(-sw['pencere'][0], 1)} milyar "
            f"dolarken şokun ilk ayında ({gun_ay(m26['bas'])}–{gun_ay(m26['son'])}) {sayi(sh, 1)} milyar dolar", "B5 · pencere")
    metinde(f"DİBS 2 yıllık 125 dolarda {ob('n2y', '125')}, 150 dolarda {ob('n2y', '150')} baz puan; 3 aylık ve 5 yıllık",
            "B5 · DİBS")
    dogru(S["n3a"]["kanit"] == "guclu" and S["n5y"]["kanit"] == "guclu", "B5: 3 ay/5 yıl güçlü değil")
    dogru(S["be_2y"]["kanit"] == "zayif" and S["r2y"]["kanit"] == "zayif", "B5: başabaş/reel zayıf değil")
    metinde(f"TLREF için tablo {ob('tlref', '125')} ve {bp(S['tlref']['150']['orta'])} diyor", "B5 · TLREF")
    metinde(f"Mart penceresinde {sayi(tl[0], 0, True)} bp, Eylül'de, repo ihalesinin yeniden açılmasıyla, "
            f"{sayi(tl[3], 0, True)} bp", "B5 · TLREF")
    metinde(f"üst ucu ({yz(S['tlref']['150']['seviye_ust'], 2)}) koridorun tavanını aşıyor; bir karar olmadıkça TLREF'in "
            f"tavanı {yz(fb['koridor_ust'], 0)}", "B5 · TLREF tavan")
    y26, y25, gd, s4 = YB["2026-03"], YB["2025-03"], YB["geri_donus_2026"], YB["son_4_hafta"]
    metinde(f"Yurt dışı yerleşikler {gun_ay(y26['bas'])}'tan sonraki {SAYI_AD[y26['hafta']]} haftada DİBS'ten "
            f"{sayi(-y26['dibs'] / 1000, 2)}, hisseden {sayi(-y26['hisse'] / 1000, 2)} milyar dolar çıkardı; ilk dört "
            f"haftada DİBS çıkışı {sayi(-y26['ilk_4_hafta_dibs'] / 1000, 2)} milyar dolar", "B5 · akım")
    metinde(f"aynı çıkış {SAYI_AD[y25['hafta']]} haftada {sayi(-y25['dibs'] / 1000, 2)} milyar dolardı", "B5 · 2025")
    metinde(f"{gun_ay(gd['bas'])}'dan {gun_ay(gd['son'])}'e {gd['hafta']} haftada DİBS'e {sayi(gd['dibs'] / 1000, 2)}, "
            f"hisseye {sayi(gd['hisse'] / 1000, 2)} milyar dolar girdi; Mart'ta çıkanın yarısından biraz fazlası",
            "B5 · geri dönüş")
    dogru(50 < gd["dibs_geri_pay"] < 60, f"B5: geri dönüş payı 'yarısından biraz fazlası' değil: {gd['dibs_geri_pay']:.1f}")
    metinde(f"Son dört haftada DİBS'ten yeniden {sayi(-s4['dibs'] / 1000, 2)} milyar dolar çıktı, hisseye "
            f"{sayi(s4['hisse'] / 1000, 2)} milyar dolar girdi", "B5 · son 4 hafta")

    # ── Bölüm 6
    bo = once["bist100"]
    metinde(f"o {bo['n']} pencerede BIST 100 medyanda {yz(bo['medyan_yuzde'], 1, True)} yükseldi ve "
            f"{yz(bo['arti_pay'], 0)}'inde arttı", "B6")
    metinde(f"yatay ({oy('XU100.IS', '125')})", "B6")
    metinde(f"dolar bazında {oy('bist_usd', '125')} ve {oy('bist_usd', '150')}", "B6")
    metinde(f"{sayi(V['XBANK.IS']['yukselis']['egim'], 2)}'lik log tepki; doğrunun {sayi(S['XBANK.IS']['sabit'], 1, True)}'lik "
            f"sabitiyle birlikte 150 dolarda {oy('XBANK.IS', '150')} (Akbank {oy('AKBNK_IS', '150')}, Garanti BBVA "
            f"{oy('GARAN_IS', '150')})", "B6 · banka")
    metinde(f"Mart'ta fonlama maliyeti {sayi((m26['aofm_zirve'] - m26['aofm_bas']) * 100, 0)} baz puan arttı", "B6 · fonlama")
    metinde(f"Pegasus THY'den duyarlı ({oy('PGSUS_IS', '125')} ve {oy('PGSUS_IS', '150')}'ya karşı {oy('THYAO_IS', '125')} "
            f"ve {oy('THYAO_IS', '150')}); TAV Havalimanları {oy('TAVHL_IS', '125')} ve {oy('TAVHL_IS', '150')}", "B6 · hava")
    tp = V["TUPRS_IS"]["pencere_yuzde"]
    dogru(all(x > 0 for x in tp), "B6: Tüpraş dördünde yükselmedi")
    metinde(f"Tüpraş dört pencerenin dördünde yükseldi ({yz(tp[0], 1, True)}, {yz(tp[1], 1, True)}, {yz(tp[2], 1, True)}, "
            f"{yz(tp[3], 1, True)}) ve senaryoda {oy('TUPRS_IS', '125')} ve {oy('TUPRS_IS', '150')}", "B6 · Tüpraş")
    for k in ("PETKM_IS", "BIMAS_IS", "ASELS_IS"):
        dogru(S[k]["kanit"] == "zayif", f"B6: {k} zayıf değil")
    dogru(S["TUPRS_IS"]["kanit"] == "orta" and "egilim" in S["TUPRS_IS"]["kanit_ayrinti"]["orta_sebep"],
          "B6: Tüpraş'ın kanıtı görüşsüz kıyas yüzünden orta değil")
    pk = V["PETKM_IS"]["pencere_yuzde"]
    metinde(f"Petkim de dört pencerenin dördünde yükseldi ({yz(min(pk), 1, True)} ile {yz(max(pk), 1, True)})", "B6 · Petkim")
    dogru(all(x > 0 for x in pk) and TCB["PETKM_IS"]["isaret_tutan"] >= 3 and TCB["PETKM_IS"]["rmse"] >= TCB["PETKM_IS"]["rmse_sifir"],
          "B6: Petkim'in zayıflığı büyüklük hatasından gelmiyor")

    # ── Bölüm 7
    tg = lambda k: TU[f"vadeli:{k}:2005"]  # noqa: E731
    metinde(f"({tg('tufe')['n']} ay; aynı ay ve bir ay gecikme): motorinin Brent'e esnekliği {sayi(tg('motorin')['brent_0_1'], 2)}, "
            f"benzininki {sayi(tg('benzin')['brent_0_1'], 2)}, akaryakıt grubununki {sayi(tg('akaryakit')['brent_0_1'], 2)}, "
            f"enerjininki {sayi(tg('enerji')['brent_0_1'], 2)}, manşet TÜFE'ninki {sayi(tg('tufe')['brent_0_1'], 3)}", "B7")
    metinde(f"Kur bacağı (TÜFE'de {sayi(tg('tufe')['kur_0_1'], 3)})", "B7 · kur")
    metinde(f"125 dolarda akaryakıt iki ayda {yz(s125['kalem']['akaryakit'], 1, True)}, TÜFE'ye katkı "
            f"{sayi(s125['tufe_2ay_petrol'], 2, True)} puan; 150 dolarda {yz(s150['kalem']['akaryakit'], 1, True)} ve "
            f"{sayi(s150['tufe_2ay_petrol'], 2, True)} puan", "B7 · TÜFE")
    metinde(f"Kurun aynı iki aydaki payı {sayi(s125['tufe_2ay_kur_payi'], 2)} ve {sayi(s150['tufe_2ay_kur_payi'], 2)} puan",
            "B7 · kur payı")
    alinti("aa_com_tr_85ff46ff90", "Brent petrol fiyatında yüzde 10'luk bir artışın tüketici enflasyonunu 12 ay sonunda "
                                   "doğrudan ve dolaylı etkiler kanalıyla nihai olarak 1 puan artırdığına",
           "Brent'te %10'luk artış tüketici enflasyonunu 12 ayda nihai olarak 1 puan")
    alinti("aa_com_tr_85ff46ff90", "Toplam etkiyi ise 24 ay içerisinde yaklaşık 1,2 puan olarak hesaplıyoruz",
           "ayda yaklaşık 1,2 puan artırıyor (TCMB'nin Mart 2026 analizi")
    alinti("tcmbblog_org_81fb3752cd", "nihai olarak 1 puan artırdığına işaret ediyor. Toplam etkinin yaklaşık yarısı ilk "
                                      "çeyrekte gerçekleşirken, bir yılın sonunda yaklaşık 0,8 puanlık bir etki",
           "nihai etkiyi 1 puan, bir yılın sonundaki etkiyi 0,8 puan veriyordu")
    metinde(f"kuralla 125 dolar {sayi(s125['tufe_12ay_tcmb'], 2, True)}, 150 dolar {sayi(s150['tufe_12ay_tcmb'], 2, True)} "
            "puan eder", "B7 · TCMB kuralı")
    dogru(abs(s125["tufe_12ay_tcmb"] - y125 / 10) < 1e-3 and abs(s150["tufe_12ay_tcmb"] - y150 / 10) < 1e-3,
          "B7: TCMB kuralı yüzde değişimin onda biri değil")
    he, ea = TU["haziran_eylul"], TU["eylul_aylik"]
    metinde(f"Haziran'dan Eylül'e TÜFE'de motorin {yz(he['motorin'], 1, True)}, benzin {yz(he['benzin'], 1, True)}, "
            f"akaryakıt {yz(he['akaryakit'], 1, True)} ve manşet TÜFE {yz(he['tufe'], 1, True)} arttı; Eylül'de tek ayda "
            f"motorin {yz(ea['motorin'], 2, True)}, benzin {yz(ea['benzin'], 2, True)}", "B7 · 2026")
    alinti("ppk:2026-42-TR", "Motorin fiyatları üzerinde rafineri marjlarındaki yükselişin yansımaları da hissedilmiştir",
           "TCMB Ağustos için motorin fiyatlarında rafineri marjlarındaki yükselişin yansımalarının da hissedildiğini "
           "yazıyordu (PPK özeti, 17 Eylül)")
    alinti("ppk:2026-14-TR", "eşel mobil uygulamasının ivedilikle devreye alınması, ham petrol fiyatlarındaki artışların "
                             "tüketici enflasyonuna yansımasını önemli ölçüde sınırlamıştır",
           "Mart'ta eşel mobil ivedilikle devreye alındı ve TCMB'ye göre ham petroldeki artışların tüketici enflasyonuna "
           "yansımasını önemli ölçüde sınırladı")
    alinti("ppk:2026-14-TR", "rafineri ürün fiyatlarındaki artışların önemli bir bölümünün maktu ÖTV tutarından karşılanmasıyla",
           "rafineri ürün fiyatlarındaki artışların önemli bir bölümü maktu ÖTV tutarından karşılandı (PPK özeti, 18 Mart)")
    alinti("aa_com_tr_85ff46ff90", "12 aylık bir dönem sonunda yıllık enflasyon tahmini 1,9 puan yukarı yönlü etkileniyor",
           "eşel mobilsiz 1,9")
    alinti("aa_com_tr_85ff46ff90", "bir başka ifadeyle yüzde 0,6 olarak gerçekleşmesini sağlıyor", "eşel mobille 0,6 puan")
    alinti("aa_com_tr_85ff46ff90", "Brent petrol fiyatının ortalama 90 dolar olduğu durumda 3,7 yüzde puana kadar çıkıyor",
           "ortalama 90 dolarda eşel mobilin düşürücü etkisi 3,7 puana kadar çıkabiliyor (Anadolu Ajansı)")
    kaynakta("aa_com_tr_85ff46ff90", "Ortalama Brent petrol fiyatının 70 dolar olduğu")
    kay = otv_kayitlari()
    mot, b95, b98 = kay["motorin"], kay["kurşunsuz benzin 95 oktan"], kay["kurşunsuz benzin 98 oktan"]
    md, b5, b8 = mot["donem"], b95["donem"], b98["donem"]
    kr1, kr2 = mot["karar"], b95["karar"]

    def tl_(x, b=None):
        if b is None:
            b = 0 if float(x).is_integer() else (4 if round(x, 2) != x else 2)
        return sayi(x, b)

    metinde(f"{int(kr1['karar_tarihi'][8:10])} {ay_ad(kr1['karar_tarihi'])} tarihli ve {kr1['karar_sayisi']} sayılı Cumhurbaşkanı "
            f"Kararı (Resmî Gazete, {gun_ay(kr1['rg_tarihi'])}) motorinin litre başına ÖTV'sini 13–31 Ağustos için "
            f"{tl_(md['2026-08-13'])} TL, Eylül için {tl_(md['2026-09-01'])}, Ekim için {tl_(md['2026-10-01'])}, Kasım için "
            f"{tl_(md['2026-11-01'])}, Aralık için {tl_(md['2026-12-01'])} TL ve 1 Ocak 2027'den itibaren "
            f"{tl_(md['2027-01-01'])} TL", "B7 · 11606")
    metinde(f"Benzinde {int(kr2['karar_tarihi'][8:10])} {ay_ad(kr2['karar_tarihi'])} tarihli ve {kr2['karar_sayisi']} sayılı Karar "
            f"(Resmî Gazete, {gun_ay(kr2['rg_tarihi'])}) 95 oktan için Ekim'de {sayi(b5['2026-10-01'], 2)}, Kasım'da "
            f"{sayi(b5['2026-11-01'], 2)} ve 1 Aralık'tan itibaren {sayi(b5['2026-12-01'], 4)} TL belirledi (98 oktan: "
            f"{sayi(b8['2026-10-01'], 2)}, {sayi(b8['2026-11-01'], 2)} ve {sayi(b8['2026-12-01'], 4)} TL)", "B7 · 11822")
    dogru(kr1.get("madde_2", "").find("10995") >= 0, "B7: 11606'nın 10995'e atfı kayıtta yok")
    alinti("bulten:2026-10-06", "petrol fiyatlarının etkisini sınırlamak için mazottan sonra benzinde de eşel mobilden "
                                "kademeli çıkıldığını",
           "Şimşek 5 Ekim'de mazottan sonra benzinde de eşel mobilden kademeli çıkıldığını söyledi (Anadolu Ajansı)")
    metinde(f"varil başına 10 dolarlık bir Brent hareketi bugünkü kurla litrede {sayi(OT['litre_basina_10_dolar'], 2)} TL",
            "B7 · litre")
    metinde(f"Ekim'deki {sayi(om['baz'], 0)} TL'lik motorin ÖTV'si {sayi(om['dolar_karsiligi_baz'], 2)} dolarlık, Kasım'daki "
            f"{sayi(om['kasim'], 0)} TL {sayi(om['dolar_karsiligi_hedef'], 2)} dolarlık", "B7 · tampon")
    metinde(f"benzinde {sayi(ob95['baz'], 2)} ve {sayi(ob95['kasim'], 2)} TL {sayi(ob95['dolar_karsiligi_baz'], 2)} ve "
            f"{sayi(ob95['dolar_karsiligi_hedef'], 2)} dolara denk", "B7 · tampon")
    dogru(om["baz"] == md["2026-10-01"] and om["kasim"] == md["2026-11-01"] and ob95["kasim"] == b5["2026-11-01"],
          "B7: ölçümün ÖTV tutarları kayıtla aynı değil")
    metinde(f"varil başına {sayi(ot125['brent_artis_varil'], 2, True)} dolar demek: ham petrol bacağı litrede "
            f"{sayi(ot125['ham_tl_litre'], 2, True)} TL", "B7 · 125")
    metinde(f"Kasım'ın motorin ÖTV'si bu artışın {sayi(ot125['motorin_tampon_kasim_ham'], 2)} katı", "B7 · 125")
    metinde(f"orantılı, biraz da hızlı yükseldi (eğim {sayi(S['HO=F']['egim'], 2)})", "B7 · ürün")
    metinde(f"125 dolar senaryosu motorinin ürün fiyatını litrede {sayi(ot125['motorin_urun_tl_litre'], 2, True)} TL artırır; "
            f"Kasım ÖTV'si bunun yalnız {yz(ot125['motorin_tampon_kasim_urun'] * 100, 0)}'ini karşılayabilir", "B7 · ürün")
    dogru(1.7 < S["HO=F"]["son_deger"] * 42 / baz < 2.3 and ot125["motorin_urun_tl_litre"] > 2 * ot125["ham_tl_litre"],
          "B7: motorinin varil fiyatı ham petrolün yaklaşık iki katı değil ya da ürün bacağı ham bacağın iki katını aşmıyor")
    metinde(f"ön vadenin bugünkü {sayi(baz, 2)} dolardan hedefe log değişimiyle (125'te {sayi(Y['senaryo']['125']['log'], 2)}, "
            f"150'de {sayi(Y['senaryo']['150']['log'], 2)}) çarpılır", "Şekil 08 · x")
    dogru(abs(s125["tufe_2ay_petrol"] - tg("tufe")["brent_0_1"] * Y["senaryo"]["125"]["log"]) < 1e-3,
          "Şekil 08: TÜFE katkısı ön vadenin değişimiyle kurulmamış")
    metinde(f"150 dolarda ham petrol bacağı {sayi(ot150['ham_tl_litre'], 2, True)}, ürün bacağı "
            f"{sayi(ot150['motorin_urun_tl_litre'], 2, True)} TL; Kasım ÖTV'si bunların "
            f"{yz(ot150['motorin_tampon_kasim_ham'] * 100, 0)}'ünü ve {yz(ot150['motorin_tampon_kasim_urun'] * 100, 0)}'ini",
            "B7 · 150")
    metinde(f"1 Kasım'da motorin ÖTV'si {sayi(om['adim'], 0)}, benzininki {sayi(ob95['adim'], 2)} TL artıyor", "B7 · adım")
    metinde(f"rafineri marjı sabitse {sayi(ot125['motorin_toplam_ham'], 2, True)} TL, marj 2026'daki gibi açılırsa "
            f"{sayi(ot125['motorin_toplam_urun'], 2, True)} TL", "B7 · toplam")
    metinde(f"(125'te {sayi(ot125['brent_artis_varil'], 2, True)}, 150'de {sayi(ot150['brent_artis_varil'], 2, True)} dolar) "
            f"bölü {sayi(YT['litre_varil'], 2)} litre, çarpı senaryonun USD/TRY'si ({sayi(ot125['kur'], 2)} ve "
            f"{sayi(ot150['kur'], 2)})", "Şekil 09")
    metinde(f"bölü {sayi(YT['litre_galon'], 3)} litre", "Şekil 09")
    dogru(abs(ot125["kur"] - S["USDTRY=X"]["125"]["seviye"]) < 1e-6, "Şekil 09: ÖTV kuru senaryo kurundan farklı")
    metinde(f"Son 12 ayda ({ay_ad(EF['son_ay'] + '-01')} {EF['son_ay'][:4]}'ya) enerji ithalatı {sayi(EF['ithalat_12a'], 2)}, "
            f"ihracatı {sayi(EF['ihracat_12a'], 2)}, net enerji faturası {sayi(EF['net_12a'], 2)} milyar dolar; cari açık "
            f"{sayi(-EF['cari_12a'], 2)} milyar dolar, GSYH'nin {yz(-EF['cari_gsyh'], 2)}'u (son dört çeyreğin GSYH'si "
            f"{sayi(EF['gsyh_milyar_usd'], 1)} milyar dolar)", "B7 · cari")
    metinde(f"Bu dönemin Brent ortalaması {sayi(EF['brent_12a_ort_vadeli'], 2)} dolardı; yani bugünkü {sayi(baz, 2)} dolar",
            "B7 · cari")
    k10, kg = EF["kural_2010"], EF["kural_2010_gazli"]
    metinde(f"Avrupa gaz fiyatı sabitken {sayi(kg['milyar_usd_yillik_10_dolar'], 2)} milyar dolar, gaz da petrolle birlikte "
            f"yükselirse {sayi(k10['milyar_usd_yillik_10_dolar'], 2)} milyar dolar artırıyor ({k10['ilk'][:4]}–"
            f"{k10['son'][:4]}, {k10['n']} ay)", "B7 · kural")
    alinti("tcmbblog_org_81fb3752cd", "ham petrol fiyat artışının, petrol ürünleri ithalatını 5,1 milyar ABD doları, "
                                      "ihracatını da 2,2 milyar ABD doları yukarı çekeceği",
           "10 dolarlık artış petrol ürünleri ithalatını 5,1, ihracatını 2,2 milyar dolar artırıyor")
    alinti("tcmbblog_org_81fb3752cd", "12 aylık net etkisini, her 10 ABD dolarlık artışta 2,6 milyar ABD doları civarında",
           "cari açığa 12 aylık net etkisi 2,6 milyar dolar civarında (TCMB blogu)")
    metinde(f"125 dolarda kalırsa ek fatura {sayi(ek['125']['petrol']['ek'], 2)}–{sayi(ek['125']['petrol_gaz']['ek'], 2)} "
            f"milyar dolar ve cari açık/GSYH {yz(-ek['125']['petrol']['cari_gsyh'], 2)}–"
            f"{sayi(-ek['125']['petrol_gaz']['cari_gsyh'], 2)}; 150 dolarda {sayi(ek['150']['petrol']['ek'], 2)}–"
            f"{sayi(ek['150']['petrol_gaz']['ek'], 2)} milyar dolar ve {yz(-ek['150']['petrol']['cari_gsyh'], 2)}–"
            f"{sayi(-ek['150']['petrol_gaz']['cari_gsyh'], 2)}", "B7 · senaryo")
    metinde(f"bir yıl sürmesi bile {yz(-ek['bugun']['petrol']['cari_gsyh'], 2)}–{sayi(-ek['bugun']['petrol_gaz']['cari_gsyh'], 2)}",
            "B7 · bugün")
    bfz = ek["bugun_fiziki"]
    metinde(f"bugünkü fiziki fiyatın ({sayi(fiz, 2)}) bir yıl sürmesi cari açık/GSYH'yi {yz(-bfz['petrol']['cari_gsyh'], 2)}–"
            f"{sayi(-bfz['petrol_gaz']['cari_gsyh'], 2)}'a taşır", "B7 · fiziki")
    dogru(abs(EF["kural_2010_fiziki"]["milyar_usd_yillik_10_dolar"] - k10["milyar_usd_yillik_10_dolar"]) < 0.3
          and abs(EF["kural_2010_gazli_fiziki"]["milyar_usd_yillik_10_dolar"] - kg["milyar_usd_yillik_10_dolar"]) < 0.3,
          "B7: fiziki Brent'le kurulan kural 'neredeyse aynı katsayı' vermiyor")
    t1, t2 = k10["sonraki_ay_tahmin_milyar"], kg["sonraki_ay_tahmin_milyar"]
    metinde(f"Kural Ağustos'un net enerji faturası için {sayi(min(t1, t2), 2)}–{sayi(max(t1, t2), 2)} milyar dolar bekliyor; "
            f"bir yıl önce {sayi(k10['gecen_yil_ayni_ay_milyar'], 2)}'ydi", "B7 · Ağustos")
    dogru(k10["sonraki_ay"] == kg["sonraki_ay"] == "2026-08", "B7: kuralın beklediği ay Ağustos değil")
    k16 = EF["kural_2016"]
    metinde(f"aynı kural {k16['ilk'][:4]}–{k16['son'][:4]} verisiyle 10 dolar için {sayi(k10['milyar_usd_yillik_10_dolar'], 2)} "
            f"değil {sayi(k16['milyar_usd_yillik_10_dolar'], 2)} milyar dolar veriyor", "Şekil 10 · örneklem")
    alinti("sbb_gov_tr_fabb206ad8", "Ham Petrol Fiyatı- (/) 69,1 88,0", "Brent'i 88,0 dolar")
    alinti("sbb_gov_tr_fabb206ad8", "Enerji İthalatı (Milyar Dolar) 62,5 71,0", "enerji ithalatını 71,0 milyar dolar")
    alinti("sbb_gov_tr_fabb206ad8", "işlemler açığının 2026 yılında 47,5 milyar dolar gerçekleşerek GSYH'ya oranının yüzde 2,6",
           "cari açığı 47,5 milyar dolar (GSYH'nin %2,6'sı)")

    # ── Bölüm 8
    alinti("bis_org_4d7a52a482", "Oil prices, after dropping sharply in March on news that the Iraqi oil fields had been secured",
           "petrol fiyatları Irak petrol sahalarının güvenceye alındığı haberleriyle Mart'ta sert düşmüştü")
    alinti("congress_gov_418be75086", "temporarily disrupted 5.7 million barrels per day (mb/d) of oil production, over half "
                                      "of Saudi Arabia's oil production and about 5% of global supply",
           "Suudi Arabistan'ın petrol üretiminin yarısından fazlasını, günde 5,7 milyon varili, dünya arzının yaklaşık "
           "%5'ini geçici olarak durdurdu")
    alinti("nber_org_546e38fafe", "The two countries accounted for nearly 9% of world production",
           "Irak ve Kuveyt dünya üretiminin yaklaşık %9'unu oluşturuyordu")
    kaynakta("nber_org_546e38fafe", "the price of crude oil doubled within the space of a few months")
    kaynakta("nber_org_45b760eccb", "July 1990 (1990Q3) March 1991 (1991Q1)")
    kaynakta("nber_org_546e38fafe", "All but one of the 11 postwar recessions were associated with an increase in the price of oil")
    em = o["emsaller"]
    yuk = [k for k, m in em.items() if (m["deger"].get("us2y") or 0) > 20]
    dogru(yuk == ["1990", "2022", "2026"], f"B8: ABD 2 yıllığın belirgin arttığı olaylar 1990, 2022, 2026 değil: {yuk}")
    metinde(f"ABD 2 yıllık getirisi sekiz olayın üçünde belirgin biçimde yükseldi (1990, 2022, 2026)", "B8")
    dogru(len(em) == 8, "B8: olay sayısı sekiz değil")
    kaynakta("federalreserve_gov_ea0bc3b53d", "in the near term the invasion and related events are likely to create additional "
                                              "upward pressure on inflation and weigh on economic activity")
    kaynakta("federalreserve_gov_ea0bc3b53d", "decided to raise the target range for the federal funds rate")
    kaynakta("ecb_europa_eu_b45b81d09b", "will be increased by 25 basis points to 1.25%")
    kaynakta("ecb_europa_eu_933be96506", "will be increased by 25 basis points to 1.50%")
    metinde("Nisan ve Temmuz'da politika faizini artırdı (%1,25 ve %1,50)", "B8 · ECB")
    tt = [m["deger"].get("try_tcmb") for m in em.values()]
    art = [k for k, m in em.items() if (m["deger"].get("try_tcmb") or 0) > 0]
    azl = [k for k, m in em.items() if (m["deger"].get("try_tcmb") or 0) < 0]
    dogru(all(x is not None for x in tt), "B8: USD/TRY bir olayda eksik")
    tto = once["try_tcmb"]
    metinde(f"USD/TRY sekiz olayın {SAYI_AD[len(art)]}sında yükseldi, {SAYI_AD[len(azl)]}sinde ({', '.join(azl)}) geriledi",
            "B8 · USD/TRY")
    metinde(f"2026 öncesinin {tto['n']} büyük petrol yükselişinde kur pencerelerin yalnız {yz(tto['arti_pay'], 0)}'ünde "
            "yükseldi", "B8 · USD/TRY")
    metinde(f"1988–2025 arasında vadeli Brent'in bir ayda en az {yz(y125, 1, True)} yükseldiği ve birbirinden "
            f"{YT['genis_ara']} takvim gününden fazla uzak {once['n']} pencere var", "B8 · geniş küme")
    metinde(f"{tr['n']}'i arz, {ta['n']}'ü talep baskın", "B8 · ayrıştırma")
    disari = [p for p in TY["pencere"] if p["son"] < "2026-01-01" and not p.get("nyfed")]
    dogru(len(disari) == 1 and disari[0]["son"].startswith("2025-06") and once["n"] == tr["n"] + ta["n"] + 1,
          "B8: ayrıştırmanın dışında kalan pencere Haziran 2025'te biten tek pencere değil")
    metinde(f"2026 öncesinin pencerelerinde ise yalnız {yz(tto['arti_pay'], 0)}'ünde yükselmişti", "B8 · USD/TRY OOS")
    metinde(f"Talep baskın pencerelerde S&P 500 medyanda {yz(ta['spx']['medyan_yuzde'], 1, True)} yükseldi ve "
            f"{yz(ta['spx']['arti_pay'], 0)}'sında arttı, ABD 2 yıllık medyanda {bp(ta['us2y']['medyan'], 1)}; arz baskın "
            f"pencerelerde S&P 500 {yz(tr['spx']['medyan_yuzde'], 1, True)}, ABD 2 yıllık {bp(tr['us2y']['medyan'], 1)}",
            "B8 · arz/talep")
    y2 = TY["ozet"]["y2026"]
    metinde(f"ABD 2 yıllık medyanda {bp(y2['us2y']['medyan'], 1)} ve dördünde artış, BIST 100 dolar bazında medyanda "
            f"{yz(y2['bist_usd']['medyan_yuzde'], 1, True)} ve hiçbirinde artış yok", "B8 · 2026")
    dogru(y2["us2y"]["arti_pay"] == 100 and y2["bist_usd"]["arti_pay"] == 0, "B8: 2026 sayımı")
    for k, n in (("us2y", 4), ("us10y", 4), ("try_tcmb", 4), ("spx", 2), ("bist100", 0)):
        dogru(od[k]["isaret_tutan"] == n, f"B8: örneklem dışı {k} {n} değil")
    kaynakta("nber_org_546e38fafe", "Historical Oil Shocks")

    # ── Bölüm 9
    hf = m26["haftalik"]
    metinde(f"TCMB repo ihalesine {gun_ay(m26['ihale_ara_ilk'])}'ta ara verdi, TLREF aynı gün "
            f"{yz(m26['tlref_ara_ilk'], 2)}'e çıktı, ağırlıklı ortalama fonlama maliyeti {gun_ay(m26['aofm_tavan_ilk'])}'ta "
            f"koridorun tavanına ({yz(m26['aofm_zirve'], 0)}) ulaştı ve ilk haftada {sayi(-hf[0]['doviz_satisi'], 2)} milyar "
            "dolarlık döviz satıldı", "B9 · sıra")
    metinde(f"(2–6 Mart {sayi(-hf[0]['doviz_satisi'], 2)}, 23–27 Mart {sayi(-hf[3]['doviz_satisi'], 2)} milyar dolar)",
            "B9 · haftalar")
    enb = sorted(range(len(hf)), key=lambda i: hf[i]["doviz_satisi"])[:2]
    dogru(hf[0]["ilk"] == "2026-03-02" and hf[3]["ilk"] == "2026-03-23" and sorted(enb) == [0, 3]
          and all(h["swap_haric_degisim"] < 0 for h in hf), "B9: satışın en yoğun iki haftası 2–6 ve 23–27 Mart değil")
    metinde(f"net rezerv {gun_ay(m26['net_rezerv_dip_gun'])}'ta, swap hariç net rezerv {gun_ay(m26['swap_haric_dip_gun'])}'ta "
            f"pencerenin dibine indi (dönemin en düşüğü {gun_ay(m26['swap_haric_donem_dip_gun'])}'da "
            f"{sayi(m26['swap_haric_donem_dip'], 2)})", "B9 · sıra")
    metinde(f"Kur ay boyunca yalnız {yz(m26['usdtry_tcmb_degisim'], 2, True)} kaydı", "B9 · kur")
    metinde(f"Yabancının {SAYI_AD[y26['hafta']]} haftalık DİBS çıkışının {yz(y26['ilk_4_hafta_pay'], 0)}'u ilk dört haftada "
            "geldi", "B9 · sıra")
    alinti("cnbc_com_60ee3c98c3", "The G7 will deploy 100 million barrels of reserves over the next four months \"with a "
                                  "frontloaded substantial diesel release within the first 20 days,\"",
           "G7 2 Ekim'de dört ay içinde 100 milyon varillik stok salımı açıkladı, ilk 20 günde ağırlıklı olarak dizel (CNBC)")
    alinti("tr_euronews_com_f31c4c55cf", "IEA'nın martta başlattığı acil petrol rezervi salımının hızlandırılarak "
                                         "tamamlanmasını öngörüyor. Bu adım, daha önce kararlaştırılan 400 milyon varile ek "
                                         "olarak yeni bir 100 milyon varillik taahhüt anlamına gelmiyor",
           "Mart'ta başlayan 400 milyon varillik salıma ek yeni bir taahhüt değil")
    alinti("oilprice_com_d9d3ba7e96", "stood at 284.6 million barrels for the week ending September 18", "18 Eylül haftasında 284,6 milyon varildi")
    alinti("oilprice_com_d9d3ba7e96", "and 406.0 million a year earlier", "bir yıl önce 406,0")
    alinti("oilprice_com_d9d3ba7e96", "the reserve fell further the following week, to 283.8 million barrels, the lowest level "
                                      "since October 1982",
           "ertesi hafta 283,8 milyon varille Ekim 1982'den bu yana en düşük düzeye indi")
    alinti("bloomberght_com_48e00255eb", "Kızıldeniz'deki ihraç merkezine günlük 5,8 milyon varil petrol pompalama kapasitesine "
                                         "ulaştığını",
           "Kızıldeniz'deki ihraç merkezine günde 5,8 milyon varil pompalama kapasitesine ulaştığını açıkladı (Bloomberg HT, 6")
    alinti("bloomberght_com_48e00255eb", "10-11 Eylül tarihlerinde", "hat 10–11 Eylül'deki saldırının ardından yaklaşık 11 gün kapalı kalmıştı")
    kaynakta("bloomberght_com_48e00255eb", "Söz konusu hat, yaklaşık 11 gün kapalı kalmıştı")
    alinti("tr_euronews_com_d4618a6439", "Kpler'in verilerine göre 1-28 Eylül arasında bölgeden günde en az 16,5 milyon varil "
                                         "(mbd) ham petrol çıktı; bu, İran hariç tutulduğunda savaş öncesi ortalamaya denk",
           "1–28 Eylül'de günde en az 16,5 milyon varille savaş öncesi ortalamaya döndü (Euronews, 5 Ekim)")
    alinti("cnbc_com_5dfd5ea085", "Gulf OPEC+ producers have been pumping well below output targets",
           "Körfez üreticilerinin ihracatı son aylarda normalin %60 ile %80'i arasında")
    kaynakta("cnbc_com_5dfd5ea085", "with exports fluctuating at 60% to 80% of normal levels in recent months")
    alinti("cnbc_com_5dfd5ea085", "yet still roughly 5 million bpd below prewar levels in February",
           "yedi üye Ağustos'ta savaş öncesinin günde yaklaşık 5 milyon varil altında üretti")
    kaynakta("cnbc_com_5dfd5ea085", "OPEC+ agrees to keep November oil output targets steady")
    alinti("bloomberght_com_d832ce5702", "3 Kasım'daki ara seçimlere kadar İran'a saldırı düzenlemeyeceklerini açıkladı",
           "3 Kasım'daki ara seçimlere kadar İran'a saldırı düzenlemeyeceklerini açıkladı (Bloomberg HT, 8 Ekim)")
    alinti("bulten:2026-10-12", "Rusya'nın yeniden motorin tedarik edeceği",
           "Dünya gazetesi düşüşü Rusya'nın yeniden motorin tedarik edeceği beklentisine bağlıyor")
    kaynakta("bulten:2026-10-12", "Zelenskiy'nin saldırıların sürdüğünü açıklaması")
    metinde(f"Brent'ten hızlı yükseldiği için (eğim {sayi(S['HO=F']['egim'], 2)}) bu, Türkiye'nin pompa hesabında", "B9 · dal 5")
    alinti("bulten:2026-10-09", "22 Ekim'deki Para Politikası Kurulu toplantısında değişiklik beklemediklerini ancak bu tahmine "
                                "yönelik risklerin yüksek olduğunu",
           "Goldman Sachs 22 Ekim'de değişiklik beklemediğini ve bu tahmine yönelik risklerin yüksek olduğunu yazdı "
           "(Bloomberg HT, 8 Ekim)")
    alinti("bulten:2026-10-09", "Citi ve Commerzbank 100 baz puan bekliyor - Investing.com Türkiye",
           "Citi ve Commerzbank 100 baz puanlık indirim bekliyor (Investing.com Türkiye, 7 Ekim)")
    alinti("cnbc_com_414cdf1bf9", "the global oil supply would shrink by 6 million to 8 million barrels per day",
           "büyük bir kesintinin (günde 6–8 milyon varil)")
    alinti("cnbc_com_414cdf1bf9", "That would drive prices up by 56% to 75% initially - to between $140 and $157 a barrel",
           "fiyatı başlangıçta %56–75 artırıp 140–157 dolara taşıyacağını yazıyordu (CNBC)")
    alinti("worldbank_org_b9c4f1b4c3", "the largest oil supply shock on record, with an initial reduction in global oil supply "
                                       "of about 10 million barrels per day",
           "Bu savaşın kesintisi başlangıçta günde yaklaşık 10 milyon varildi ve kayıtlardaki en büyük petrol arz şoku oldu")
    alinti("worldbank_org_b9c4f1b4c3", "the Strait of Hormuz, which handles about 35% of global seaborne crude oil trade",
           "Hürmüz deniz yoluyla taşınan ham petrolün yaklaşık %35'ini taşıyor (Dünya Bankası, Nisan 2026)")
    alinti("dallasfed_org_4bb9186006", "in the DSGE model higher oil prices are associated with economic contractions",
           "Dallas Fed'in modelinde yüksek fiyat ekonomik daralmayla birlikte gelir")
    alinti("dallasfed_org_4bb9186006", "The destruction of oil demand associated with these contractions makes it difficult for "
                                       "the quarterly average price of oil to rise to levels of $200 per barrel or more",
           "daralmanın yok ettiği talep, çeyreklik ortalama fiyatın 200 doları aşmasını zorlaştırır")
    alinti("dallasfed_org_4bb9186006", "closing the Strait of Hormuz for 1, 2, or 3 quarters would increase Q4/Q4 headline PCE "
                                       "inflation in 2026 by 0.35, 0.79 and 1.47 percentage points",
           "(dördüncü çeyrekten dördüncü çeyreğe) 0,35, 0,79 ve 1,47 puan artırıyor")
    alinti("bbc_co_uk_fb865641ef", "we simply don't know how to model the endgame",
           "JPMorgan ise bu savaşın sonunu modellemekte zorlandığını açıkça yazdı (BBC)")

    # ── yöntem eki
    dv = R["devir"]
    orn = dv["ornek"]
    metinde(f"{gun(orn['gun'])}'de ön vade {yz(orn['on_vade_yuzde'], 1)} gerilerken WTI {yz(orn['wti_yuzde'], 1)} geriledi; "
            f"aradaki {sayi(-orn['fark_log'], 1)} log puan devrin kendisi", "yöntem · devir")
    metinde(f"pencerede {dv['wti']} devir günü var", "yöntem · devir")
    dogru(all(int(g[8:10]) <= 3 for g in dv["wti_bosluk_2026"]) and len(dv["wti_bosluk_2026"]) == dv["wti"],
          "yöntem: devir günleri ayın ilk iş günü değil")
    metinde(f"Standart hatalar {YT['nw_gecikme']} gecikmeli Newey–West", "yöntem")
    metinde(f"125 için {sayi(x125, 2)}, 150 için {sayi(x150, 2)}", "yöntem · x")
    wt = S["CL=F"]["150"]
    metinde(f"(log {sayi(wt['orta'], 1)}, {yz(wt['orta_yuzde'], 1)} eder)", "yöntem · log/yüzde")
    metinde(f"son gününden {YT['loo_once']} iş günü önce ile {YT['loo_sonra']} iş günü sonra arasındaki günler eğitimden "
            f"çıkarıldı; eğitimde en az {YT['loo_asgari']} gün kaldı", "yöntem · LOO")
    metinde(f"2026 öncesinin {once['n']} penceresinin", "yöntem · OOS")
    metinde(f"Sıklıkta 21 gözlemlik pencerenin takvim boyu {YT['takvim_tavan']} günü aşarsa", "yöntem · sıklık")
    metinde(f"epizotlar en az {YT['ufuk']} iş günü arayla ayrıldı", "yöntem · epizot")
    kd = o["kaynak_duzeltme"]
    metinde(f"2004 sonundaki {kd['try_eski_lira_gun']} gün eski lira ölçeğinde, BIST 100 serisinde 2014'ün "
            f"{kd['bist100_2014_x100_gun']} günü yüz katı ölçekteydi", "yöntem · temizlik")
    metinde(f"Piyasanın kapalı olduğu {kd['yilbasi_bari']} yılbaşı barı atıldı", "yöntem · temizlik")
    metinde(f"varil {sayi(YT['litre_varil'], 2)} litre, galon {sayi(YT['litre_galon'], 3)} litre", "yöntem · ÖTV")

    # ── formüller
    metinde("1,645", "formül · %90", "formul")

    # ── figür gömme başlıkları
    metinde(f"en az {yz(y125, 1, True)} yükseldiği pencerelerde S&P 500 ve ABD 2 yıllık", "Şekil 11 başlığı", "baslik")


# ─────────────────────────────────────────────── 6 · biçim
def bicim(govde: str) -> None:
    g = re.sub(r"`[^`]*`", " ", govde)
    g = re.sub(r"\$\$.*?\$\$", " ", g, flags=re.S)
    g = re.sub(r"\$[^$\n]+\$", " ", g)
    sayac["metin"] += 3
    for x in re.finditer(r"(?<![\w/.\-–])-%?\d", g):
        hatalar.append(f"ASCII tireli eksi sayı: {g[max(0, x.start() - 30):x.end() + 10]!r}")
    for x in re.finditer(r"\d[ \t]*%(?!\w)", g):
        hatalar.append(f"arkaya yazılmış yüzde: {g[max(0, x.start() - 20):x.end() + 5]!r}")
    if "<Deger" in govde:
        hatalar.append("analizde canlı <Deger> etiketi var (analizin sayıları sabittir)")


# ─────────────────────────────────────────────── 7 · figürler
def sekil_listesi() -> list[str]:
    kaynak = (BURASI / "sekil.py").read_text(encoding="utf-8")
    bas = kaynak.index("SEKILLER =")
    return re.findall(r'"(\d\d_[a-z_]+)"', kaynak[bas:kaynak.index("]", bas)])


def _ortak():
    """Başlık genişlik ölçüsü makro dersinin ortak kuralıdır (çizim kütüphanesi istemez); bu
    projenin `sekil_ortak.py`si onu birebir taşır — aşağıda kaynak metinleri karşılaştırılır."""
    yol = KOK / "Aktarılacak Projeler/MakroKurFaiz/sekil_ortak.py"
    spec = importlib.util.spec_from_file_location("brent_dogrula_sekil_ortak", yol)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    a = (BURASI / "sekil_ortak.py").read_text(encoding="utf-8")
    b = yol.read_text(encoding="utf-8")
    for bas, son in (("_TAVAN_PX", "\n\n"), ("_GENISLIK = {", "\n}"), ("def satir_em", "\ndef "),
                     ("def _satirla", "\ndef "), ("def tasan_satirlar", "\n\n")):
        i, j = a.find(bas), b.find(bas)
        dogru(i >= 0 and j >= 0 and a[i:a.index(son, i)] == b[j:b.index(son, j)],
              f"sekil_ortak.py taşma ölçüsü makro dersininkinden ayrışmış: {bas}")
    return m


def figurler(govde: str, o: dict) -> None:
    liste = sekil_listesi()
    oz = _oz(VERI / "olcum.json")
    ortak = _ortak()
    dogru(len(liste) == 11, f"figür listesi {len(liste)} öğe — 11 bekleniyor")
    for i, ad in enumerate(liste, 1):
        sayac["sekil"] += 1
        if not ad.startswith(f"{i:02d}_"):
            hatalar.append(f"figür listesi sıralı numaralı değil: {ad}")
        yol = SEKIL / f"{ad}.html"
        if not yol.exists():
            hatalar.append(f"figür yok: {yol.relative_to(KOK)}")
            continue
        h = yol.read_text(encoding="utf-8")
        x = re.search(r'<meta name="tto-olcum-ozu" content="([0-9a-f]{64})">', h)
        if not x or x.group(1) != oz:
            hatalar.append(f"figür bugünkü ölçüm dosyasından çizilmemiş — sekil.py yeniden koşulmalı: {ad}")
        t = re.search(r'"text":("(?:\\u015e|Ş)ekil \d\d (?:[^"\\]|\\.)*")', h)
        if not t:
            hatalar.append(f"figürün başlığı okunamadı: {ad}")
            continue
        baslik = json.loads(t.group(1))
        if not baslik.startswith(f"Şekil {ad[:2]} —"):
            hatalar.append(f"figürün içindeki başlık 'Şekil {ad[:2]} —' ile açılmıyor: {ad}")
        for s in ortak.tasan_satirlar(baslik):
            hatalar.append(f"figür başlığı telefon çerçevesinde taşıyor: {ad}: {s}")
    fazla = sorted(p.stem for p in SEKIL.glob("*.html") if p.stem not in liste)
    dogru(not fazla, f"yayın dizininde listede olmayan figür var: {fazla}")
    gomulu = re.findall(r'<GrafikEmbed src="/analiz/' + re.escape(SLUG) + r'/(\d\d_[a-z_]+)\.html"[^>]*no="(\d\d)"', govde)
    dogru([a for a, _ in gomulu] == liste, f"gömme sırası figür listesiyle aynı değil: {[a for a, _ in gomulu]}")
    for a, n in gomulu:
        dogru(a.startswith(n + "_"), f"figür dosyasının öneki gömme numarasıyla aynı değil: {a} · no {n}")
    dogru(len(re.findall(r"<GrafikEmbed", govde)) == len(gomulu), "ayrıştırılamayan figür gömmesi var")
    for n in range(1, len(liste) + 1):
        dogru(f"**Şekil {n:02d} nasıl hesaplanıyor.**" in govde, f"Şekil {n:02d} için 'nasıl hesaplanıyor' paragrafı yok")


# ─────────────────────────────────────────────── metin ayrıştırma
def bolumler(m: str) -> tuple[dict, str]:
    _, on, govde = m.split("---", 2)
    alan = {}
    for ad in ("title", "description", "ozet", "kaynak", "guncelleme"):
        x = re.search(rf"^{ad}: '((?:[^']|'')*)'$", on, re.M)
        alan[ad] = x.group(1).replace("''", "'") if x else ""
        if not x:
            hatalar.append(f"ön bilgi alanı okunamadı: {ad}")
    for ad, bek in (("pubDate", "2026-10-12"), ("veriTarihi", "2026-10-09")):
        x = re.search(rf"^{ad}: (\S+)\s*$", on, re.M)
        dogru(bool(x) and x.group(1).strip("'\"") == bek, f"ön bilgi {ad} {bek} değil")
    return alan, govde


def duz_metin(govde: str) -> tuple[str, str, str]:
    """(düz metin, formül metni, gömme başlıkları). Tablolar hücre hücre sınanır; kod, formül ve figür
    gömmeleri düz metinden çıkar (gömmenin `baslik`ı okura basıldığı için ayrı alandır)."""
    g = re.sub(r"^import .*$", " ", govde, flags=re.M)
    g = re.sub(r"`[^`\n]*`", " ", g)
    basliklar = re.findall(r'<GrafikEmbed[^>]*\bbaslik="([^"]*)"', g)
    g = re.sub(r"<GrafikEmbed[^>]*/>", " ", g)
    formul = " ".join(re.findall(r"\$\$.*?\$\$", g, flags=re.S) + re.findall(r"(?<!\$)\$[^$\n]+\$(?!\$)", g))
    g = re.sub(r"\$\$.*?\$\$", " ", g, flags=re.S)
    g = re.sub(r"(?<!\$)\$[^$\n]+\$(?!\$)", " ", g)
    g = "\n".join(s for s in g.splitlines() if not (s.strip().startswith("|") and s.strip().endswith("|")))
    g = re.sub(r"</?[A-Za-z][^>]*>", " ", g)       # etiket harfle ya da "/" ile başlar; "<" işaretine çarpmaz
    return g, formul.replace("{,}", ","), "\n".join(basliklar)


def main() -> int:
    o = arsiv()
    if "--tablo" in sys.argv:
        tablo_bas(o)
        return 0
    kaynak_butunlugu()
    m = MDX.read_text(encoding="utf-8")
    on, govde = bolumler(m)
    duz, formul, gomme = duz_metin(govde)
    ALAN["govde"] = Alan("gövde", duz)
    ALAN["formul"] = Alan("formül", formul)
    ALAN["baslik"] = Alan("gömme başlığı", gomme)
    ALAN["aciklama"] = Alan("açıklama", on["description"])
    ALAN["ozet"] = Alan("kart özeti", on["ozet"])
    ALAN["title"] = Alan("başlık", on["title"])
    ALAN["kaynak"] = Alan("ön bilgi kaynak", on["kaynak"])
    ALAN["guncelleme"] = Alan("ön bilgi güncelleme", on["guncelleme"])
    TABLOLAR.extend(tablolar(govde))
    senaryo_tablolari(o)
    mart_tablosu(o)
    emsal_tablosu(o)
    takvim_tablosu(o)
    izleme_tablosu(o)
    metin(on, o)
    envanter()
    bicim(govde)
    figurler(govde, o)
    if hatalar:
        print(f"✗ Brent senaryosu · {len(hatalar)} hata")
        for h in hatalar:
            print("  ·", h)
        return 1
    print(f"✓ Brent senaryosu · {sayac['arsiv']} arşiv ölçütü, {sayac['hucre']} tablo hücresi, {sayac['metin']} metin "
          f"ölçütü, {sayac['dis']} dış kaynak ifadesi ({sayac['alinti']} kaynak metni sorgusu); {sayac['sayi']} sayının "
          f"hepsi sınanmış ya da kaynağıyla bildirilmiş; {sayac['sekil']} figür")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
