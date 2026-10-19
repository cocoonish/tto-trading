#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABD'NİN ORTA DOĞU UYARISI (19.10.2026) — yayımlanan metni sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda pandas/numpy/plotly YOK: betik yalnız
standart kütüphaneyle çalışır, ağa çıkmaz, duvar saati okumaz (girdisi depodaki arşiv). Altı soru sorar:

1. ARŞİV — her ham dosyanın sıkıştırılmamış özü bulut künyesiyle, her donmuş kaynak metninin özü dizinle aynı mı;
   ölçüm dosyası bugünkü `olcum.py`, bugünkü olgu tablosu, bugünkü künyeler ve kapanış dosyalarıyla mı üretilmiş?
2. KAYNAKLAR — olgu tablosunun (`veri/olaylar.json`) her alıntısı ve yazının atıf verdiği her dış ifade kaynağın
   KENDİ dondurulmuş metninde geçiyor mu? (Tahmin piyasası çözüm kuralı piyasanın kendi kaydından okunur.)
3. TABLOLAR — dalga tablosu, tarihsel emsal tablosu ve piyasa tablosunun her hücresi ölçümden kurulur ve yayımlanan
   tabloyla hücre hücre kıyaslanır.
4. METİN — yazının cümlelerindeki her ölçülmüş sayı ölçümden kurulmuş bir ifadenin içinde mi; sayıyı doğru yazıp hükmü
   yanlış kuran cümleler (sayımlar, yönler, sıralamalar) ölçümden ayrıca hesaplanır (`dogru`).
5. ENVANTER — metindeki HER ondalık sayı ve yüzde / baz puan / puan taşıyan HER tam sayı sınanmış bir ifadenin ya da
   adıyla bildirilmiş bir dış kaynak ifadesinin içinde durmalı. Ön bilgi (başlık, açıklama, kart özeti) gövdeden AYRI
   sınanır.
6. FİGÜRLER — beş figür yayın dizininde, metin onları sırayla gömüyor, figürün "Şekil NN" başlığı gömmenin numarasıyla
   aynı, başlık satırları telefonun gömme çerçevesine sığıyor ve figür bugünkü ölçümden çizilmiş.

Koşum:  python3 dogrula.py
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
sys.path.insert(0, str(BURASI))
sys.dont_write_bytecode = True
from ayar import SLUG  # noqa: E402
import sekil_ortak as so  # noqa: E402  (çizim kütüphanesi olmadan da içe aktarılır)

# arıza enjeksiyonu sınaması başka bir kopyayı okutabilir (yalnız sınama içindir)
MDX = Path(os.environ.get("ODU_DOGRULA_MDX") or KOK / "site/src/content/analiz" / f"{SLUG}.mdx")
SEKIL = KOK / "site/public/analiz" / SLUG
BRENT_MDX = KOK / "site/src/content/analiz/brent-senaryo-2026-10-12.mdx"
SEKILLER = ["01_takvim", "02_dalgalar", "03_tepki", "04_piyasa", "05_gecmis"]

hatalar: list[str] = []
sayac = {"hucre": 0, "metin": 0, "arsiv": 0, "dis": 0, "sayi": 0, "alinti": 0, "sekil": 0}
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
KADEME_AD = {4: "sığın ya da derhal ayrıl", 3: "ayrılmayı düşün", 2: "seyahati yeniden düşün", 1: "tetikte ol"}


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def _sifir(s: str) -> bool:
    return float(s.replace(".", "").replace(",", ".")) == 0


def sayi(x: float, b: int = 1, arti: bool = False) -> str:
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if x < 0 and not _sifir(s):
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not _sifir(s)) else s


def yz(x: float, b: int = 1, arti: bool = False) -> str:
    """Yüzde işareti önde, işaret yüzdeden de önce: −%0,9 · +%1,8 (x yüzde biriminde)."""
    s = sayi(abs(x), b)
    if x < 0 and not _sifir(s):
        return "−%" + s
    return ("+%" if (arti and x > 0 and not _sifir(s)) else "%") + s


def ol(p: float, b: int = 1) -> str:
    """Olasılık (0–1) → yüzde yazımı."""
    return yz(p * 100, b)


def gun(iso: str) -> str:
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]}"


# ─────────────────────────────────────────────── metin alanları ve kapsam
def _norm(s: str) -> str:
    s = re.sub(r"\s+", " ", s.replace("''", "'").replace(" ", " "))
    return re.sub(r"'[a-zçğıöşüâîû]+", "'", s)


ONDALIK = re.compile(r"(?<![\d.,])\d{1,3}(?:\.\d{3})*,\d+|(?<![\d.,])\d+,\d+")
BIRIMLI = re.compile(r"%\d+(?![\d,.])|(?<![\d.,])\d+(?= (?:bp|baz puan|puan)\b)")


class Alan:
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
                    out.append(f"{self.ad}: …{self.n[max(0, x.start() - 70):x.end() + 30]}…")
        return out

    def say(self) -> int:
        return len(ONDALIK.findall(self.n)) + len(BIRIMLI.findall(self.n))


ALAN: dict[str, Alan] = {}


def metinde(parca: str, ad: str, yer: str = "govde") -> None:
    sayac["metin"] += 1
    if not ALAN[yer].isaretle(parca):
        hatalar.append(f"{yer} · metinde yok ({ad}): {parca!r}")


def her_yerde(parca: str, ad: str, yerler: tuple[str, ...]) -> None:
    for y in yerler:
        metinde(parca, ad, y)


def dogru(kosul: bool, mesaj: str) -> None:
    sayac["metin"] += 1
    if not kosul:
        hatalar.append(mesaj)


# ─────────────────────────────────────────────── tablolar
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
            h = [x.strip().replace("**", "") for x in s[1:-1].split("|")]
            if not all(set(x) <= set("-: ") for x in h):
                blok.append(h)
        elif blok:
            out.append(Tablo(blok))
            blok = []
    if blok:
        out.append(Tablo(blok))
    return out


def tablo(*baslik: str) -> Tablo:
    bulunan = [x for x in TABLOLAR if x and tuple(x[0][:len(baslik)]) == baslik]
    if len(bulunan) != 1:
        hatalar.append(f"tablo bulunamadı ya da tekil değil ({len(bulunan)}): {baslik!r}")
        return Tablo([])
    t = bulunan[0]
    t.kapsam[0] = [True] * len(t[0])
    return t


def satir(t: Tablo, ilk: str, beklenen: list[str], ad: str) -> None:
    """Satırın bütün hücreleri beklenenle birebir aynı olmalı."""
    sayac["hucre"] += len(beklenen)
    bul = [i for i, r in enumerate(t) if r and r[0] == ilk]
    if len(bul) != 1:
        hatalar.append(f"{ad}: satır yok ya da tekil değil ({len(bul)}): {ilk!r}")
        return
    i = bul[0]
    r = t[i]
    if r[1:] != beklenen:
        hatalar.append(f"{ad} · '{ilk}': metin {r[1:]!r}, ölçüm {beklenen!r}")
    t.kapsam[i] = [True] * len(r)


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
                elif not t.kapsam[i][j] and re.search(r"\d", h):
                    hatalar.append(f"sınanmamış tablo hücresi · {t[0][0]!r} · {r[0]!r} · sütun {j + 1}: {h!r}")


# ─────────────────────────────────────────────── 1 · arşiv
def _oz(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def _kunye() -> dict:
    out = {}
    for p in sorted(HAM.glob("kunye_*.json")):
        out.update(json.loads(p.read_text(encoding="utf-8")))
    return out


KUNYE: dict = {}
DIZIN: dict = {}


def arsiv() -> dict:
    global KUNYE, DIZIN
    KUNYE = _kunye()
    DIZIN = json.loads((VERI / "kaynak_metin.json").read_text(encoding="utf-8"))
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    k = o["kunye"]
    for ad, beklenen, yol in (("olaylar", k["olaylar"], VERI / "olaylar.json"),
                              ("olcum.py", k["olcum_py"], BURASI / "olcum.py"),
                              ("kaynak metin dizini", k["kaynak_metin"], VERI / "kaynak_metin.json")):
        sayac["arsiv"] += 1
        if _oz(yol) != beklenen:
            hatalar.append(f"ölçüm dosyası bugünkü {ad} ile üretilmemiş — olcum.py yeniden koşulmalı")
    sayac["arsiv"] += 2
    if k["kunye_dosyalari"] != {p.name: _oz(p) for p in sorted(HAM.glob("kunye_*.json"))}:
        hatalar.append("ölçüm dosyası bugünkü bulut künyeleriyle üretilmemiş — olcum.py yeniden koşulmalı")
    if k["cnbc"] != {p.name: _oz(p) for p in sorted((HAM / "cnbc").glob("*.json.gz"))}:
        hatalar.append("ölçüm dosyası bugünkü kapanış dosyalarıyla üretilmemiş — olcum.py yeniden koşulmalı")
    # ölçümün okuduğu her ham dosya künyedeki özüyle
    for yol, kk in KUNYE.items():
        if kk.get("durum") != 200 or not (yol.startswith("elcilik/") or yol.startswith("cnbc/")
                                          or yol.startswith("polymarket/")):
            continue
        p = HAM / yol
        sayac["arsiv"] += 1
        if not p.exists():
            hatalar.append(f"ham dosya yok: {yol}")
        elif hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest() != kk["sha256"]:
            hatalar.append(f"ham dosyanın özü künyeyle tutmuyor: {yol}")
    for yol, v in DIZIN.items():
        sayac["arsiv"] += 1
        p = HAM / yol
        if not p.exists():
            hatalar.append(f"kaynağın ham dosyası yok: {yol}")
            continue
        oz = hashlib.sha256(gzip.decompress(p.read_bytes())).hexdigest()
        if oz != v["kaynak_sha256"] or oz != KUNYE.get(yol, {}).get("sha256"):
            hatalar.append(f"kaynağın ham dosyası künyeyle tutmuyor: {yol}")
        m = VERI / v["metin"]
        if not m.exists() or hashlib.sha256(gzip.decompress(m.read_bytes())).hexdigest() != v["metin_sha256"]:
            hatalar.append(f"donmuş kaynak metni dizindeki özle tutmuyor: {v['metin']}")
    return o


# ─────────────────────────────────────────────── 2 · kaynaklar
def _km():
    spec = importlib.util.spec_from_file_location("brent_kaynak_metin", BURASI.parent / "BrentSenaryo" / "kaynak_metin.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


KM = _km()


def normal(s: str) -> str:
    return re.sub(r"\s+", " ", "".join(ch for ch in KM.normal(s)
                                       if unicodedata.category(ch) not in ("Cc", "Cf", "Co"))).strip()


_KAYNAK: dict[str, str] = {}


def kaynak_metni(yol: str) -> str:
    if yol in _KAYNAK:
        return _KAYNAK[yol]
    if yol.startswith("polymarket/"):
        d = json.loads(gzip.decompress((HAM / yol).read_bytes()))
        t = normal(d.get("description") or "")
    elif yol.startswith("mdx:"):
        t = normal(Path(yol[4:]).read_text(encoding="utf-8"))
    else:
        v = DIZIN.get(yol)
        if v is None:
            hatalar.append(f"kaynak metni dizinde yok: {yol}")
            t = ""
        else:
            t = normal(gzip.decompress((VERI / v["metin"]).read_bytes()).decode("utf-8"))
    _KAYNAK[yol] = t
    return t


def kaynakta(yol: str, parca: str) -> None:
    sayac["alinti"] += 1
    if normal(parca) not in kaynak_metni(yol):
        hatalar.append(f"kaynakta yok ({yol}): {parca!r}")


def olgu_alintilari(olaylar: dict) -> None:
    def gez(x):
        if isinstance(x, dict):
            if "yol" in x and "alinti" in x:
                kaynakta(x["yol"], x["alinti"])
            for v in x.values():
                gez(v)
        elif isinstance(x, list):
            for v in x:
                gez(v)
    gez(olaylar)


def alinti(yol: str, kaynak_parca: str, mdx_parca: str, yer: str = "govde") -> None:
    """Dış kaynağın ifadesi kaynağın kendi metninde geçmeli VE yazıda adıyla durmalı (envanterde kapsanmış sayılır)."""
    sayac["dis"] += 1
    kaynakta(yol, kaynak_parca)
    if not ALAN[yer].isaretle(mdx_parca):
        hatalar.append(f"{yer} · dış kaynak ifadesi metinde yok ({yol}): {mdx_parca!r}")


def uyari_yolu(adres: str) -> str:
    """Bir uyarı adresinin donmuş kaynak metni yolu (dizinden çözülür, elle yazılmaz)."""
    bul = [y for y, v in DIZIN.items() if v["url"].rstrip("/") + "/" == adres]
    if not bul:
        hatalar.append(f"uyarının donmuş metni yok: {adres}")
        return ""
    return sorted(bul)[0]


def bag(o: dict, kimlik: str) -> dict:
    return next(x for x in OLAY["baglam"] if x["id"] == kimlik)


# ─────────────────────────────────────────────── 3 · tablolar
def dalga_ad(d: dict) -> str:
    if d["bas"] == d["bit"]:
        return gun(d["bas"])
    return f"{int(d['bas'][8:10])}–{gun(d['bit'])}"


def dalga_tablosu(o: dict) -> None:
    t = tablo("Dalga", "Temsilcilik", "En sert talimat")
    for d in o["uyari"]["donemler"]:
        kad = d["kademe_dagilim"]
        sert = KADEME_AD[d["en_sert"]]
        if d["en_sert"] == 2 and kad["1"] > kad["2"]:      # çoğunluk yumuşak, tek metin sert: ikisi de yazılır
            sert = f"tetikte ol (bir metinde {KADEME_AD[2]})" if kad["2"] == 1 else None
        if d["ayni_gun_saldiri"]:
            son = f"{d['son_saldiridan_gun']} gün (aynı gün saldırı)"
        else:
            son = f"{d['son_saldiridan_gun']} gün"
        if d["sonraki_saldiriya_gun"] is not None:
            sonra = f"{d['sonraki_saldiriya_gun']} gün"
        else:
            sonra = "açık" if d["acik_gun"] <= 7 else "yok"
        satir(t, dalga_ad(d), [str(d["post_sayisi"]), sert, str(len(d["ayrilis_post"])), son, sonra],
              "dalga tablosu")
    dogru(len(t) - 1 == len(o["uyari"]["donemler"]), f"dalga tablosu {len(t) - 1} satır, ölçüm {len(o['uyari']['donemler'])} dalga")


TARIH_AD = {"1998": "7 Ağustos 1998", "2003": "16 Mart 2003", "2013": "4 Ağustos 2013", "2019": "15 Mayıs 2019",
            "2020": "3 Ocak 2020", "2023": "19 Ekim 2023", "2024": "14 Nisan 2024", "2025a": "11 Haziran 2025",
            "2025b": "22 Haziran 2025", "2026a": "23 Şubat 2026", "2026b": "2 Mart 2026"}
TUR_AD = {"ayrilis": "ayrılış kararı", "olay_sonrasi": "olaydan sonra", "tehdit": "tehdit"}


def tarih_tablosu(o: dict) -> None:
    t = tablo("Tarih", "Olay", "Uyarının tipi", "Sonra ne oldu")
    dogru(len(t) - 1 == len(o["tarihsel"]), f"tarih tablosu {len(t) - 1} satır, kayıt {len(o['tarihsel'])}")
    for x in o["tarihsel"]:
        bul = [i for i, r in enumerate(t) if r and r[0] == TARIH_AD[x["id"]]]
        sayac["hucre"] += 1
        if len(bul) != 1:
            hatalar.append(f"tarih tablosu: satır yok: {TARIH_AD[x['id']]}")
            continue
        r = t[bul[0]]
        t.kapsam[bul[0]] = [True] * len(r)
        if not r[2].startswith(TUR_AD[x["tur"]]):
            hatalar.append(f"tarih tablosu · {r[0]}: tip {r[2]!r}, kayıt {TUR_AD[x['tur']]!r}")
        if x["gun"] and x["gun"] > 0 and f"{x['gun']} gün sonra" not in r[3]:
            hatalar.append(f"tarih tablosu · {r[0]}: '{x['gun']} gün sonra' yok: {r[3]!r}")
        if x["sonraki_abd_saldirisi"] and x["gun"] and x["gun"] > 0:
            dogru(f"({gun(x['sonraki_abd_saldirisi'])})" in r[3], f"tarih tablosu · {r[0]}: saldırı günü yok")


def piyasa_tablosu(o: dict) -> None:
    t = tablo("Piyasa", "Olasılık, 19 Ekim")
    T = o["tahmin"]
    bek = [("ABD'nin 31 Ekim'e kadar İran toprağını vurması", T["abd_31ekim"]["saldiri_son"]),
           ("İsrail–İran ateşkesinin 31 Ekim'e kadar bozulması", 1 - T["israil_31ekim"]["evet_son"]),
           ("İsrail–İran ateşkesinin 30 Kasım'a kadar bozulması", 1 - T["israil_30kasim"]["evet_son"]),
           ("İsrail–İran ateşkesinin 31 Aralık'a kadar bozulması", 1 - T["israil_31aralik"]["evet_son"]),
           ("ABD'nin 2027'den önce İran toprağını kontrol etmeye yönelik bir harekât başlatması", T["isgal_2026"]["evet_son"]),
           ("ABD'nin 2026'da İran'a resmen savaş ilan etmesi", T["savas_ilani_2026"]["evet_son"]),
           ("30 Kasım'a kadar nihai ABD–İran nükleer anlaşması", T["anlasma_30kasim"]["evet_son"]),
           ("31 Aralık'a kadar nihai ABD–İran nükleer anlaşması", T["anlasma_31aralik"]["evet_son"]),
           ("31 Aralık'a kadar ABD–İran Hürmüz anlaşması", T["hurmuz_31aralik"]["evet_son"])]
    for ad, p in bek:
        satir(t, ad, [ol(p)], "piyasa tablosu")
    dogru(len(t) - 1 == len(bek), "piyasa tablosu satır sayısı ölçümle aynı değil")
    # piyasaların soruları kayıttaki sorularla
    for k, s in (("abd_31ekim", "US x Iran ceasefire continues through October 31?"),
                 ("israil_30kasim", "Israel x Iran ceasefire continues through November 30?"),
                 ("isgal_2026", "Will the U.S. invade Iran before 2027?")):
        dogru(T[k]["soru"] == s, f"piyasa sorusu kayıtla tutmuyor: {k}")


def izleme_tablosu(o: dict) -> None:
    t = tablo("tarih", "veri", "neyi doğrular / çürütür")
    T = o["tahmin"]
    son = o["uyari"]["donemler"][-1]["bas"]
    from datetime import date, timedelta
    yedi = (date.fromisoformat(son) + timedelta(days=7)).strftime("%d.%m.%Y")
    bek = {"20.10.2026 →": None, yedi: None, "27.10.2026": None,
           "31.10.2026": ol(T["abd_31ekim"]["saldiri_son"]), "03.11.2026": None,
           "30.11.2026": ol(1 - T["israil_30kasim"]["evet_son"])}
    for i, r in enumerate(t[1:], start=1):
        sayac["hucre"] += 1
        if r[0] not in bek:
            hatalar.append(f"izleme listesi: beklenmeyen tarih {r[0]!r}")
            continue
        if bek[r[0]] and bek[r[0]] not in r[2]:
            hatalar.append(f"izleme listesi · {r[0]}: {bek[r[0]]!r} yok")
        t.kapsam[i] = [True] * len(r)
    dogru(len(t) - 1 == len(bek), "izleme listesi satır sayısı beklenenle aynı değil")


# ─────────────────────────────────────────────── 4 · metin
def metin(o: dict) -> None:
    U, T, M, G = o["uyari"], o["tahmin"], o["metin_farki"], o["gpr"]
    D = U["donemler"]
    A = T["abd_31ekim"]
    gl = {}
    for d_, p in A["gunluk"]:
        gl[d_] = p
    son = D[-1]
    on = ("govde", "aciklama", "ozet")

    # ── uyarı ve dalgalar
    metinde(ol(M["_ozet"]["benzerlik_medyan"]), "8 ve 18 Ekim metinlerinin benzerlik medyanı", "govde")
    metinde(f"kelime düzeyinde {ol(M['_ozet']['benzerlik_medyan'])} aynı", "benzerlik", "aciklama")
    metinde(f"(benzerlik {ol(M['sa']['benzerlik'])})", "Suudi Arabistan benzerliği")
    dogru(M["_ozet"]["post"] == 12 and len(M["_ozet"]["kucuk_degisiklik"]) == 11,
          "metin farkı: on iki temsilciliğin on birinde küçük değişiklik iddiası tutmuyor")
    for cc in M["_ozet"]["kucuk_degisiklik"]:
        dg = [b for a, b in M[cc]["degisen"]]
        dogru(any("severe travel disruptions" in b for b in dg) and any("beyond that immediate area" in b for b in dg)
              and any("contingency plans in advance" in b for b in dg), f"metin farkı: {cc} üç ifadeyi taşımıyor")
    dogru(son["bas"] == "2026-10-18" and son["post_sayisi"] == 12, "son dalga 18 Ekim ve on iki temsilcilik değil")
    dogru(next(d for d in D if d["bas"] == "2026-10-08")["post_sayisi"] == 12, "8 Ekim dalgası on iki temsilcilik değil")
    dogru(len(D) == 9, f"dalga sayısı dokuz değil: {len(D)}")
    eyl = [d for d in D if d["bas"] >= "2026-09-01"]
    dogru(len(eyl) == 4 and all(d["post_sayisi"] >= 11 for d in eyl), "1 Eylül'den beri dört 11–12 temsilcilikli dalga değil")
    dogru(son["kademe_dagilim"]["1"] == 10 and sum(son["kademe_dagilim"].values()) == 10,
          "18 Ekim: talimatı okunabilen on metnin onu 'tetikte ol' değil")
    dogru(all(not d["ayrilis_post"] for d in eyl), "Eylül'den beri ayrılış statüsü anan metin var")
    yaz = [len(d["ayrilis_post"]) for d in D if "2026-07-01" <= d["bas"] <= "2026-08-31"]
    dogru(min(yaz) == 6 and max(yaz) == 7, f"Temmuz–Ağustos ayrılış statüsü altı ya da yedi değil: {yaz}")
    dogru(U["ortak_kapsam"] == "2026-01-14" and U["kapsam_bas"]["sa"] == "2026-01-14", "ortak kapsam 14 Ocak değil")
    dogru(len(U["gunluk"]) == 279 and sum(n for _, n in U["gunluk"]) == 423, "279 gün / 423 temsilcilik-gün tutmuyor")
    dogru(U["kapsam_bas"]["il"].startswith("2025-09"), "İsrail listesi Eylül 2025'te başlamıyor")
    dogru(son["son_saldiridan_gun"] == 47 and o["saldiri_gunleri"][-1] == "2026-09-01", "son saldırı 1 Eylül / 47 gün değil")

    # ── dalgalardan sonra
    tb = o["taban"]
    at, sk = tb["atesli_7"], tb["sakin_7"]
    dogru(at["k"] == 4 and at["n"] == 6 and sk["k"] == 0 and sk["n"] == 2, "ateşli 4/6, sakin 0/2 tutmuyor")
    metinde(f"(Jeffreys %95 aralığı {ol(at['alt'])}–{ol(at['ust'])})", "ateşli Jeffreys aralığı")
    metinde(f"{ol(sk['alt'], 0)} ile {ol(sk['ust'])} arasında", "sakin Jeffreys aralığı")
    o7f, o7h = U["once7"]["2026-02-28"], U["once7"]["2025-06-22"]
    vf = [v for k, v in o7f.items() if k != "gun"]
    vh = [v for k, v in o7h.items() if k != "gun"]
    dogru(max(vf) == 1 and vf.count(0) == 6 and o7f["gun"] == 10, "28 Şubat öncesi yedi gün iddiası tutmuyor")
    dogru(min(vh) == 1 and max(vh) == 3 and o7h["gun"] == 9, "22 Haziran 2025 öncesi yedi gün iddiası tutmuyor")
    # dil düzenli bir sıra vermiyor: 3. kademe 29 gün, 2. kademe 1 ve 5 gün; 1 Eylül'de 1. kademe saldırıyla aynı gün
    dd = {d["bas"]: d for d in D}
    dogru(dd["2026-08-01"]["en_sert"] == 3 and dd["2026-08-01"]["sonraki_saldiriya_gun"] == 29,
          "1 Ağustos: 'ayrılmayı düşünün' / 29 gün tutmuyor")
    dogru({dd[g]["sonraki_saldiriya_gun"] for g in ("2026-07-17", "2026-07-24")} == {1, 5}
          and all(dd[g]["en_sert"] == 2 for g in ("2026-07-17", "2026-07-24")), "Temmuz dalgaları 2. kademe / 1 ve 5 gün değil")
    dogru(all(dd[g]["en_sert"] == 4 and dd[g]["sonraki_saldiriya_gun"] == 1 for g in ("2026-02-28", "2026-03-05")),
          "en sert iki dalga / bir gün tutmuyor")
    e1 = dd["2026-09-01"]
    dogru(e1["ayni_gun_saldiri"] and e1["kademe_dagilim"]["1"] == 10 and sum(e1["kademe_dagilim"].values()) == 10,
          "1 Eylül: on metnin onu 'tetikte ol' ve aynı gün saldırı tutmuyor")
    dogru("2026-08-02" == OLAY["iptal"][0]["tarih"] if isinstance(OLAY["iptal"], list) else True, "iptal günü 2 Ağustos değil")
    # ateşkesten sonraki saldırı başlangıçları
    BS = U["baslangic"]
    dogru(list(BS) == ["2026-05-07", "2026-05-25", "2026-06-09", "2026-06-26", "2026-07-08", "2026-08-30"],
          f"saldırı başlangıçları metindeki altı gün değil: {list(BS)}")
    metinde("(7 Mayıs, 25 Mayıs, 9 Haziran, 26 Haziran, 8 Temmuz, 30 Ağustos)", "başlangıç günleri")
    dogru(not any(v["once7_dalga"] for v in BS.values()), "bir başlangıçtan önceki yedi günde dalga var")
    dogru(BS["2026-06-09"]["once7_en_cok"] == 7 and max(v["once7_en_cok"] for k, v in BS.items() if k != "2026-06-09") == 3,
          "başlangıç öncesi en çok yedi / üç tutmuyor")
    dogru(max(v["gun"] for v in BS.values()) == 2, "saldırı günlerinde en çok iki temsilcilik tutmuyor")
    dogru(sum(1 for v in BS.values() if not v["once7_dalga"]) == 6, "şerit: 0 / 6 tutmuyor")
    metinde("<b>0 / 6</b>", "şerit: başlangıç")

    # ── tarih
    tip = {}
    for x in o["tarihsel"]:
        tip.setdefault(x["tur"], []).append(x)
    ay = tip["ayrilis"]
    dogru(len(ay) == 4 and sum(1 for x in ay if x["gun"] and 4 <= x["gun"] <= 11) == 3
          and [x["id"] for x in ay if not x["gun"]] == ["2019"],
          "ayrılış kararı içeren dört olayın üçü 4–11 gün, 2019 değil iddiası tutmuyor")
    dogru(len(tip["tehdit"]) == 2 and all(x["sonraki_abd_saldirisi"] is None for x in tip["tehdit"]),
          "ayrılış içermeyen iki tehdit uyarısı iddiası tutmuyor")
    dogru(len(tip["olay_sonrasi"]) == 5, "olaydan sonra gelen beş uyarı değil")

    # ── piyasa tepkisi
    TP, H = o["tepki"], o["son_hafta"]
    w = {d["bas"]: TP[d["bas"]] for d in D if d["bas"] in TP}
    for g, a, b in (("2026-02-28", "brent", 1), ("2026-03-05", "brent", 1), ("2026-07-17", "brent", 1),
                    ("2026-07-24", "brent", 1), ("2026-08-01", "brent", 1), ("2026-09-19", "brent", 1),
                    ("2026-10-08", "brent", 1), ("2026-02-28", "bist100", 1), ("2026-07-24", "bist100", 1),
                    ("2026-09-19", "bist100", 1), ("2026-10-08", "bist100", 1)):
        metinde(yz(w[g][a]["d5"] * 100, b, arti=a == "brent" and w[g][a]["d5"] > 0 and g in ("2026-02-28", "2026-03-05", "2026-07-17")),
                f"{a} {g} beş günlük")
    metinde(f"{sayi(w['2026-02-28']['us10y']['d5'], 1)} bp yükseldi", "ABD 10y savaşın ilk haftası")
    metinde(f"{sayi(w['2026-10-08']['us10y']['d5'], 1)} bp düştü", "ABD 10y 8 Ekim")
    tr = [x["try"]["d5"] * 100 for x in w.values()]
    ty = {g: x["try"]["yuzdelik5"] for g, x in w.items()}
    yedi = [v for g, v in ty.items() if g != "2026-09-01"]
    dogru(len(ty) == 8 and max(yedi) < 0.9 and ty["2026-09-01"] > 0.95, "USD/TRY: yedi olağan, 1 Eylül istisna tutmuyor")
    metinde(f"değişimlerinin {ol(min(yedi))}–{ol(max(yedi))}'ünden büyüktü", "USD/TRY dalga yüzdelik aralığı")
    metinde(f"istisna 1 Eylül haftası ({ol(ty['2026-09-01'])})", "USD/TRY 1 Eylül yüzdelik")
    metinde(f"1 Eylül haftasında değişimlerin {ol(ty['2026-09-01'])}'ından büyüktü", "USD/TRY 1 Eylül (özet)")
    metinde(f"haftası ise {ol(TP['2025-06-11']['try']['yuzdelik5'])}'ten büyüktü", "USD/TRY Haziran 2025")
    metinde(f"{yz(min(tr))} ile {yz(max(tr))} arasında", "USD/TRY dalga aralığı")
    metinde(f"beş günde {yz(min(tr))}–{yz(max(tr))}", "USD/TRY dalga aralığı (özet)")
    metinde(f"medyanı {yz(H['try']['medyan5_2026'] * 100, 2)}", "USD/TRY 2026 medyanı")
    for k, b in (("brent", 2),):
        metinde(f"{sayi(H[k]['bas'], b)}'den {sayi(H[k]['son'], b)} dolara {yz(H[k]['degisim'] * 100)}", "Brent hafta")
    metinde(f"(yüzdelik sırası {ol(H['brent']['yuzdelik5'])})", "Brent yüzdelik")
    metinde(f"VIX {sayi(H['vix']['bas'], 2)}'ten {sayi(H['vix']['son'], 2)}'a, {sayi(H['vix']['degisim'], 2, arti=True)} puan",
            "VIX hafta")
    metinde(f"değişimlerinin {ol(H['vix']['yuzdelik5'])}'inden büyük", "VIX yüzdelik")
    metinde(f"S&P 500 {yz(H['spx']['degisim'] * 100)}", "S&P hafta")
    metinde(f"BIST 100 {yz(H['bist100']['degisim'] * 100)} ({sayi(H['bist100']['bas'], 2)}'den {sayi(H['bist100']['son'], 2)}'ye)",
            "BIST hafta")
    metinde(f"USD/TRY {sayi(H['try']['bas'], 2)}'dan {sayi(H['try']['son'], 2)}'e {yz(H['try']['degisim'] * 100)}", "USD/TRY hafta")
    metinde(f"değişimlerinin {ol(H['try']['yuzdelik5'])}'inden büyük; medyanı {yz(H['try']['medyan5_2026'] * 100, 2)}",
            "USD/TRY yüzdelik")
    metinde(f"%{sayi(H['us10y']['bas'], 3)}'ten %{sayi(H['us10y']['son'], 3)}'e {sayi(H['us10y']['degisim'], 1)} bp", "ABD 10y hafta")
    metinde(f"altın {yz(H['altin']['degisim'] * 100)}", "altın hafta")
    metinde(f"hafta {yz(H['try']['degisim'] * 100)} ile 2026'nın beş günlük değişimlerinin {ol(H['try']['yuzdelik5'])}'inden",
            "USD/TRY özet")
    metinde(f"BIST 100 aynı hafta {yz(H['bist100']['degisim'] * 100)}", "BIST özet")
    for g in ("2026-07-24", "2026-08-01"):
        dogru(w[g]["brent"]["d5"] < 0, f"{g} Brent eksi değil")

    # ── olasılık
    s = ol(A["saldiri_son"])
    her_yerde(s, "31 Ekim ABD saldırısı", on)
    a18 = A["18ekim_aralik"]
    metinde(f"{ol(a18[0])} ile {ol(a18[1])} arasında", "18 Ekim aralığı")
    metinde(f"{ol(a18[0])} ile {ol(a18[1])}", "18 Ekim aralığı (gövde)")
    lo, hi = A["son10_aralik"]
    metinde(f"son on günün günlük fiyatları {ol(lo)}–{ol(hi)}", "son on gün (özet)")
    metinde(f"{ol(lo)} ile {ol(hi)} arasında kaldı", "son on gün")
    metinde(f"{ol(lo)}–{ol(hi)} bandına", "bant")
    metinde(f"{ol(lo)}–{ol(hi)} bandından", "bant (izleme)")
    metinde(f"{sayi(A['hacim'] / 1e6, 1)} milyon dolarlık işlem", "hacim")
    metinde(f"18 Eylül'de piyasa {ol(A['ilk_gun'][1])}", "ilk gün")
    dogru(A["ilk_gun"][0] == "2026-09-18", "ilk gün 18 Eylül değil")
    metinde(f"günü {ol(A['19eylul'])}", "19 Eylül")
    metinde(f"ertesi gün {ol(A['en_yuksek'][0])} oldu", "20 Eylül")
    dogru(A["en_yuksek"][1] == "2026-09-20", "tepe 20 Eylül değil")
    metinde(f"8 Ekim'de {ol(gl['2026-10-08'])} olan fiyat 9 Ekim'de {ol(gl['2026-10-09'])}", "8→9 Ekim")
    metinde(f"bugün 19:00 UTC'de {ol(A['saldiri_son'])}", "bugün")
    sa = {a[:13]: p for a, p in A["saatlik_19ekim"]}
    p15 = sa["2026-10-19T15"]
    metinde(f"fiyat 15:00 UTC'de {ol(p15)}'ti, 16:00'da {ol(A['19ekim_sicrama'][0])}'ya sıçradı ve üç\nsaatte {s}'e indi"
            .replace("\n", " "), "19 Ekim sıçrama")
    dogru(round((A["saldiri_son"] - p15) * 100) == 6 and sa["2026-10-19T19"] == A["saldiri_son"], "altı puan tutmuyor")
    metinde("altı puan üstünde", "altı puan")
    metinde(f"gün içinde {ol(min(sa[k] for k in sa if k.startswith('2026-10-19')))}–{ol(A['19ekim_sicrama'][0])}", "gün içi aralık (tez)")
    metinde(f"16:00 UTC'deki {ol(A['19ekim_sicrama'][0])}'lik sıçramanın", "sıçrama (ne ölçmedik)")
    dogru(A["19ekim_sicrama"][1].startswith("2026-10-19T16:00"), "sıçrama 16:00 UTC'de değil")
    i31, i30, i12 = (1 - T[k]["evet_son"] for k in ("israil_31ekim", "israil_30kasim", "israil_31aralik"))
    metinde(f"İsrail bacağı 30 Kasım'a kadar {ol(i30)}, yıl sonuna kadar {ol(i12)}", "İsrail merdiveni (özet)")
    metinde(f"31 Ekim'e kadar {ol(i31)}'ten bir ay sonra {ol(i30)}", "İsrail merdiveni (gövde)")
    metinde(f"30 Kasım'a kadar {ol(i30)}, yıl sonuna kadar {ol(i12)}. ABD", "İsrail merdiveni (okuma)")
    # ── günlük olasılık çevirisi
    HZ = T["gunluk_hiz"]
    sb, oc = T["gecmis"]["subat2026"]["fiyat"], T["gecmis"]["ocak2026"]["fiyat"]
    ha, hh, hs, ho = (HZ[k]["hiz"] for k in ("abd_31ekim", "haziran2025", "subat2026", "ocak2026"))
    dogru(ha < min(hh, hs, ho), "bugünkü günlük olasılık üç geçmiş günden düşük değil")
    dogru(1.9 <= hs / ha <= hh / ha <= 2.6, f"iki ila iki buçuk kat tutmuyor: {hs / ha:.2f}, {hh / ha:.2f}")
    dogru([round(HZ[k]["gun"]) for k in ("abd_31ekim", "haziran2025", "subat2026", "ocak2026")] == [12, 10, 2, 18],
          "kalan gün sayıları (on iki, on, iki, on sekiz) tutmuyor")
    dogru([HZ[k]["tarih"] for k in ("haziran2025", "subat2026", "ocak2026")] == ["2025-06-21", "2026-02-27", "2026-01-14"],
          "günlük olasılık günleri tutmuyor")
    metinde(f"günde {ol(ha)} ediyor; kapanmış üç piyasada ölçtüğümüz günlerin hepsinden (günde\n{ol(min(hh, hs, ho))}–{ol(max(hh, hs, ho))}) düşük"
            .replace("\n", " "), "tez: günlük olasılık")
    metinde(f"<b>{ol(ha)}</b>", "şerit: günlük olasılık")
    metinde(f"kapanmış üç piyasada günde {ol(min(hh, hs, ho))}–{ol(max(hh, hs, ho))}", "şerit: geçmiş aralık")
    metinde(f"%41,3 diyordu (on gün kala, günde {ol(hh)}), Şubat savaşından bir gün önce {ol(sb['2026-02-27'])} (iki gün kala, günde {ol(hs)})", "özet: geçmiş günlük")
    metinde(f"(on sekiz gün kala, günde {ol(ho)}). Bugünkü fiyat günde {ol(ha)} ile", "özet: Ocak ve bugün")
    metinde(f"%41,3 (on gün\nkala) günde {ol(hh)}, Şubat arifesindeki {ol(sb['2026-02-27'])} (iki gün kala) günde {ol(hs)}, Ocak'taki {ol(oc['2026-01-14'])} (on sekiz gün kala) günde {ol(ho)}"
            .replace("\n", " "), "gövde: geçmiş günlük")
    metinde(f"on iki gün kala günde {ol(ha)}", "gövde: bugün günlük")
    metinde(f"iki gün kalan bir sorudaki {ol(sb['2026-02-27'])} ile on sekiz gün kalan bir sorudaki {ol(oc['2026-01-14'])}", "gövde: vade kıyası")
    metinde(f"Ocak'taki {ol(oc['2026-01-14'])} de \"neredeyse kesin\"", "gövde: Ocak")
    metinde(f"toprak kontrolüne yönelik harekât piyasası ({ol(T['isgal_2026']['evet_son'])})", "gövde: işgal piyasası")
    metinde("Jeffreys %95 güven aralığı", "Jeffreys düzeyi")
    metinde(f"günde {ol(ho)}'lik bir olasılık", "gövde: Ocak günlük")
    ie, ik, ia = (HZ[k]["hiz"] for k in ("israil_ekim", "israil_kasim", "israil_aralik"))
    dogru(round(ie * 1000) in (round(ik * 1000) - 1, round(ik * 1000)) and ia < ie, "İsrail: Ekim ≈ Kasım, Aralık düşük tutmuyor")
    metinde(f"(Ekim'in kalanı günde {ol(ie)}, Kasım {ol(ik)}, Aralık {ol(ia)})", "özet: İsrail günlük")
    metinde(f"Ekim'in kalanı günde {ol(ie)}, Ekim'i atlatırsa Kasım günde {ol(ik)}, Aralık günde {ol(ia)}", "gövde: İsrail günlük")
    metinde(f"günde {ol(ha)} ile İsrail bacağından yüksek", "gövde: ABD günlük")
    metinde(ol(i30), "İsrail 30 Kasım (izleme)")

    # ── geçmiş piyasalar
    gc = T["gecmis"]
    hz, sb, oc = gc["haziran2025"]["fiyat"], gc["subat2026"]["fiyat"], gc["ocak2026"]["fiyat"]
    her_yerde(ol(sb["2026-02-27"]), "Şubat bir gün önce", ("govde",))
    metinde(f"9 Haziran'da {ol(hz['2025-06-09'])}", "Haz 9")
    metinde(f"(11 Haziran) {ol(hz['2025-06-11'])}'e, ertesi gün {ol(hz['2025-06-12'])}'ya", "Haz 11–12")
    metinde(f"iki gün önce {ol(hz['2025-06-20'])}, bir gün önce {ol(hz['2025-06-21'])} ve saldırının günü {ol(gc['haziran2025']['en_yuksek'][0])}",
            "Haz 20–22")
    dogru(gc["haziran2025"]["en_yuksek"][1] == "2025-06-22", "Haziran tepesi 22 Haziran değil")
    metinde(f"Ocak sonunda {ol(gc['subat2026']['en_yuksek'][0])}", "Şubat piyasası Ocak tepesi")
    metinde(f"(20 Şubat) {ol(sb['2026-02-20'])}", "Şub 20")
    metinde(f"(23 Şubat) {ol(sb['2026-02-23'])}, iki gün kala {ol(sb['2026-02-26'])} ve **bir gün kala {ol(sb['2026-02-27'])}**", "Şub 23–27")
    metinde(f"14 Ocak'ta {ol(oc['2026-01-14'])}", "Oca 14")
    metinde(f"bir hafta sonra {ol(oc['2026-01-21'])}, iki hafta sonra {ol(oc['2026-01-28'])},\n31 Ocak'ta {ol(oc['2026-01-31'])}"
            .replace("\n", " "), "Oca 21–31")
    metinde(f"Haziran 2025 saldırısından bir gün önce piyasa {ol(hz['2025-06-21'])}", "Haz özet")
    metinde(f"hiç gelmeyen saldırıya {ol(gc['ocak2026']['en_yuksek'][0])}", "Ocak özet")
    metinde(f"Şubat savaşından bir gün önce {ol(sb['2026-02-27'])}", "Şubat özet")
    dogru(dict(U["gunluk"])["2026-01-14"] == 3, "14 Ocak'ta üç temsilcilik değil")
    for k, v in (("haziran2025", '["1", "0"]'), ("subat2026", '["1", "0"]'), ("ocak2026", '["0", "1"]')):
        dogru(gc[k]["kapali"] and gc[k]["sonuc"] == v, f"geçmiş piyasa sonucu tutmuyor: {k}")

    # ── jeopolitik risk endeksi
    metinde(f"ortalaması bugün {sayi(G['gpr30'], 1)}", "GPR30")
    metinde(f"günlük\nortalaması {sayi(G['ortalama_tum'], 1)}".replace("\n", " "), "GPR uzun ortalama")
    metinde(f"ortalamaların {ol(G['yuzdelik'])}'sinden yüksek", "GPR yüzdelik")
    metinde(f"aynı ölçü {sayi(G['gunler']['2026-02-27'], 1)}'ydı", "GPR Şubat")
    metinde(f"saldırısının günü {sayi(G['gunler']['2025-06-22'], 1)}", "GPR Haziran 2025")
    metinde(f"31 Mart'ta {sayi(G['tepe_2026'][0], 1)}", "GPR tepe")
    dogru(G["tepe_2026"][1] == "2026-03-31" and G["bas_gun"] == "1985-01-01", "GPR tepe günü ya da başlangıç tutmuyor")
    for y in ("govde",):
        metinde(ol(G["yuzdelik"]), "GPR yüzdelik (şerit)", y)

    # ── yönetici özeti şeridi ve ön bilgi
    metinde(f"<b>{ol(A['saldiri_son'])}</b>", "şerit: 31 Ekim", "govde")
    metinde(f"<b>{ol(M['_ozet']['benzerlik_medyan'])}</b>", "şerit: benzerlik")
    metinde(f"<b>{ol(G['yuzdelik'])}</b>", "şerit: GPR")


def dis_kaynaklar(o: dict) -> None:
    """Yazının dış kaynaklara dayanan sayıları ve ifadeleri."""
    b = {x["id"]: x for x in OLAY["baglam"]}
    alinti(b["nadir"]["yol"], "rare measure to issue a red alert to US citizens in 12 countries",
           "\"Orta Doğu'da 12 ülkedeki\nABD vatandaşlarına kırmızı alarm vermek gibi nadir bir önlem\"".replace("\n", " "))
    son18 = o["metin_farki"]["ae"]["adres_18"]
    alinti(uyari_yolu(son18), "Americans currently in the Middle East should exercise heightened vigilance due to the complex security environment",
           "\"Orta Doğu'da bulunan Amerikalılar karmaşık\ngüvenlik ortamı nedeniyle tetikte olmalı.\"".replace("\n", " "))
    sa18 = uyari_yolu(o["metin_farki"]["sa"]["adres_18"])
    kaynakta(sa18, "Operations at King Khalid International Airport in Riyadh remain suspended.")
    kaynakta(sa18, "require special authorization from Chief of Mission to use any airport in Saudi Arabia")
    jo8 = uyari_yolu(o["metin_farki"]["jo"]["adres_8"])
    kaynakta(jo8, "Iran has attacked civilian and critical infrastructure across the Middle East, including hotels, airports")
    kaynakta("polymarket/piyasa_4641065.json.gz", "Iran’s maritime territory and airspace are not encompassed.")
    alinti(b["trump_secim"]["yol"], "The US president said late on Thursday", "Perşembe geç saatte")
    kaynakta(b["pentagon"]["yol"], "the Pentagon instructed U.S. Central Command (CENTCOM) several days ago to prepare for the potential resumption of large-scale combat operations targeting Iran")
    kaynakta(b["pentagon"]["yol"], "American and Israeli sources informed the outlet")
    kaynakta(b["moab"]["yol"], "The US military has developed new strike plans")
    alinti("mdx:" + str(BRENT_MDX), "swap hariç net rezervi 60,5 milyar dolar eritti", "60,5 milyar dolar erimesi")
    kaynakta(b["tanker_baski"]["yol"], "applying political pressure on Trump ahead of the U.S. midterm elections")
    kaynakta("wiki/en_wikipedia_org_b90d63d07c.html.gz", "firing 49 Tomahawk missiles")
    # inceleme turunun düzelttiği olgular
    alinti(uyari_yolu("https://ir.usembassy.gov/security-alert-iran-october-18-2026/"), "U.S. citizens should leave Iran now",
           "\"ABD vatandaşları İran'dan şimdi ayrılmalı\"")
    alinti(uyari_yolu("https://ae.usembassy.gov/security-alert-u-s-embassy-abu-dhabi-and-u-s-consulate-general-dubai-august-1-2026/"),
           "remain on ordered departure status", "\"zorunlu ayrılış statüsünde kalmaya devam ettiğini\"")
    npr = [y for y, v in DIZIN.items() if "npr.org/2026/08/02" in v["url"]]
    dogru(len(npr) == 1, "NPR 2 Ağustos 2026 kaynağı dizinde yok")
    if npr:
        alinti(npr[0], "President Trump said on social media late Saturday", "(ABD saatiyle 1 Ağustos gecesi)")
    from datetime import date as _d
    dogru(_d(2026, 8, 1).weekday() == 5 and _d(2026, 10, 8).weekday() == 3, "1 Ağustos cumartesi / 8 Ekim perşembe değil")
    dogru(b["rubio"]["tarih"] == "2026-08-25", "Ağustos beyanı 25 Ağustos değil")
    metinde("25 Ağustos'ta ABD'li yetkililer", "Ağustos beyanı günü")
    metinde("Trump 8 Ekim gecesi (ABD saatiyle)", "Trump sözü günü")
    alinti([y for y, v in DIZIN.items() if "us-orders-non-emergency-personnel-to-leave-beirut" in v["url"]][0],
           "President Donald Trump threatening to attack Iran almost daily", "\"neredeyse her gün\" saldırıyla tehdit ederken")
    kaynakta("polymarket/piyasa_532741.json.gz", "on Iranian soil, airspace, or maritime territory")
    kaynakta("polymarket/piyasa_665374.json.gz", "commences a military offensive intended to establish control over any portion of Iran")
    for y, parca in (("Mission Israel", "İsrail'den izinli ayrılış (27 Şubat)"),
                     ("family members from Bahrain and Kuwait", "Bahreyn ve Kuveyt'ten izinli ayrılış")):
        dogru(any(parca in " ".join(r) for t in TABLOLAR for r in t), f"tarih tablosunda yok: {parca}")


# ─────────────────────────────────────────────── 5 · biçim
def bicim(govde: str) -> None:
    for m in re.finditer(r"(?<![\w/-])-\d", govde):
        hatalar.append(f"biçim: ASCII tireyle eksi: …{govde[max(0, m.start() - 30):m.end() + 10]}…")
    for m in re.finditer(r"\d(?:,\d+)? ?%(?!\w)", govde):
        hatalar.append(f"biçim: yüzde işareti sayının arkasında: …{govde[max(0, m.start() - 30):m.end() + 10]}…")
    if "<Deger" in govde:
        hatalar.append("biçim: analizde canlı <Deger> etiketi")


# ─────────────────────────────────────────────── 6 · figürler
def figurler(govde: str, o_oz: str) -> None:
    gom = re.findall(r'<GrafikEmbed src="/analiz/' + re.escape(SLUG) + r'/([^"]+)\.html"[^>]*no="(\d\d)"', govde)
    dogru([g for g, _ in gom] == SEKILLER, f"figür gömme sırası {[g for g, _ in gom]}, beklenen {SEKILLER}")
    for ad, no in gom:
        sayac["sekil"] += 1
        dogru(ad[:2] == no, f"figür {ad}: gömme numarası {no}")
        p = SEKIL / f"{ad}.html"
        if not p.exists():
            hatalar.append(f"figür yok: {p.relative_to(KOK)}")
            continue
        h = p.read_text(encoding="utf-8")
        m = re.search(r'<meta name="tto-olcum-ozu" content="([0-9a-f]{64})">', h)
        dogru(bool(m) and m.group(1) == o_oz, f"figür {ad} bugünkü ölçümden çizilmemiş — sekil.py yeniden koşulmalı")
        adaylar = [json.loads(f'"{x}"') for x in re.findall(r'"text":"((?:[^"\\]|\\.)*)"', h)]
        adaylar = [x for x in adaylar if x.startswith("Şekil ")]
        if not adaylar:
            hatalar.append(f"figür {ad}: başlık bulunamadı")
            continue
        metin_ = adaylar[0]
        dogru(metin_.startswith(f"Şekil {no} —"), f"figür {ad}: başlık 'Şekil {no} —' ile başlamıyor")
        for t in so.tasan_satirlar(metin_):
            hatalar.append(f"figür {ad}: başlık satırı telefonda taşar — {t}")


# ─────────────────────────────────────────────── ana akış
def bolumler(m: str) -> tuple[dict, str]:
    _, on, govde = m.split("---", 2)
    alan = {}
    for k in ("title", "description", "ozet"):
        x = re.search(rf"^{k}: '((?:[^']|'')*)'", on, re.M)
        alan[k] = x.group(1).replace("''", "'") if x else ""
    return alan, govde


def duz(govde: str) -> str:
    """Gövdenin düz metni: tablo satırları (ayrı sınanır), içe aktarma ve bileşen satırları hariç; etiketler korunur
    (şerit <b> değerleri etiketle aranır)."""
    satirlar = [s for s in govde.splitlines() if not s.strip().startswith("|") and not s.startswith("import ")
                and not s.strip().startswith("<GrafikEmbed")]
    return "\n".join(satirlar)


OLAY: dict = {}


def main() -> int:
    global OLAY, TABLOLAR
    o = arsiv()
    OLAY = json.loads((VERI / "olaylar.json").read_text(encoding="utf-8"))
    olgu_alintilari(OLAY)
    m = MDX.read_text(encoding="utf-8")
    on, govde = bolumler(m)
    ALAN["govde"] = Alan("govde", duz(govde))
    ALAN["aciklama"] = Alan("aciklama", on["description"])
    ALAN["ozet"] = Alan("ozet", on["ozet"])
    ALAN["baslik"] = Alan("baslik", on["title"])
    TABLOLAR = tablolar(govde)
    dalga_tablosu(o)
    tarih_tablosu(o)
    piyasa_tablosu(o)
    izleme_tablosu(o)
    metin(o)
    dis_kaynaklar(o)
    bicim(govde)
    figurler(govde, so.olcum_ozu())
    envanter()
    print(f"ORTA DOĞU UYARISI · {sayac['arsiv']} arşiv · {sayac['alinti']} alıntı · {sayac['dis']} dış ifade · "
          f"{sayac['hucre']} tablo hücresi · {sayac['metin']} metin ölçütü · {sayac['sayi']} sayı · {sayac['sekil']} figür")
    if hatalar:
        for h in hatalar:
            print("  ✗", h)
        print(f"DÜŞTÜ: {len(hatalar)} hata")
        return 1
    print("GEÇTİ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
