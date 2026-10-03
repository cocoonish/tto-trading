#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE DERSİ — yayımlanan metni sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
pandas/numpy/plotly YOK: betik yalnız standart kütüphaneyle çalışır, ağa
çıkmaz, duvar saati okumaz (girdisi depodaki arşiv ve ölçüm dosyası).

NEDEN BİR YAN DOSYA. Ders ~24 bin kelime ve binlerce sayı taşıyor; her ifadeyi
bu betiğe elle yazmak hem uzun hem kırılgandır. Metnin yazarı her sayıyı
yazarken onun kaynağını bir yan dosyaya yazar (`veri/sayilar/*.json`):
hangi ölçüm yolundan, hangi biçimle, hangi metin parçasında. Kapı yan dosyaya
GÜVENMEZ, onu sınar: parça metinde birebir geçmeli, değeri ölçüm dosyasından
biçimlenip parçanın içinde bulunmalı, ve metindeki HER sayı bir parçanın
içinde durmalıdır (envanter). Sınanmamış bir sayı yazıya girerse kapı düşer.

GİRDİ TÜRLERİ (yan dosya):
  olcum   {"parca", "degerler": [{"yol": "b03.p3a.x", "bicim": "yz", "hane": 2, "carpan"?, "arti"?}]}
  hesap   {"parca", "degerler": [{"ifade": "v('b07.p7a.tufe.tam.rho_mu')**12", "bicim", "hane"}]}
          — ifade kısıtlı değerlendirilir: v(yol), math, araçların Python eşleri.
  kaynak  {"parca", "kaynak": "laubach2009"}   (veri/kaynaklar.json'da DOĞRULANMIŞ olmalı)
  sabit   {"parca", "neden": "..."}             (tanım ya da yöntem sabiti: π* = 5, λ = 1600)
  tablo   {"satir": "<MDX'teki tablo satırının kendisi>", "degerler": [...sayılı hücreler sırayla...]}
          — hücre değeri olcum/hesap biçiminde; sayısız hücre atlanır.
Varsayımsal sayılar `<div class="not sinav-ornek">` kabındadır ve envantere girmez.

SORULAR:
1. ARŞİV — veri/ ve veri/bulut/ dosyalarının özleri künyeyle; ölçüm dosyası bu
   özlerle ve bugünkü ölçüm betikleriyle mi üretilmiş.
2. METİN — yan dosyanın her girdisi (yukarıdaki kurallar).
3. ENVANTER — metindeki her ondalık sayı, yüzde ve bp/puan ifadesi kapsanmış mı.
4. BİÇİM — ASCII tireli eksi yok, yüzde önde.
5. FİGÜRLER — sekil.py'nin listesi, dosyaların varlığı, ölçüm özü, gömme sırası,
   figürün içindeki "Şekil NN" başlığı.
6. ARAÇLAR — arac.json ölçüm dosyasından mı; araç formüllerinin Python eşleri
   bileşenlerdeki formüllerle aynı mı (kaynak metninden).
7. KAYNAKLAR — metinde anılan her kaynak anahtarı doğrulanmış listede mi.
7b. ATIF ENVANTERİ — metindeki HER "Yazar (YYYY)" atfı, yan dosyada bir kaynak
   girdisi olmasa da, doğrulanmış (ya da kısmen doğrulanmış) bir kayda soyadı ve
   yılıyla eşlenmeli. Yan dosya yalnız yazarın bildirdiği atfı sınar; bildirilmemiş
   bir atıf o kapıdan sessizce geçerdi.

Koşum:  python3 dogrula.py                (bütün ders)
        python3 dogrula.py --parca b03    (tek bölüm: metin/b03.mdx + veri/sayilar/b03.json)
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import re
import sys
import unicodedata
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
SLUG = "makro-kur-ve-faiz"
MDX = KOK / "site/src/content/arastirma" / f"{SLUG}.mdx"
SEKIL = KOK / "site/public/arastirma" / SLUG
ARAC = KOK / "site/src/data" / SLUG / "arac.json"
BILESEN = KOK / "site/src/components"
OLCUM_BETIKLERI = ["ortak_olc.py", "bulut.py", "hazirla.py", "hazirla_bulut.py"] + [f"olcum_b{i:02d}.py" for i in range(1, 14)]

hatalar: list[str] = []
sayac = {"arsiv": 0, "metin": 0, "hucre": 0, "kaynak": 0, "sabit": 0, "sayi": 0, "figur": 0, "arac": 0, "atif": 0}
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
      "Eylül", "Ekim", "Kasım", "Aralık"]


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 1, arti: bool = False) -> str:
    """Ondalık virgül, binlik nokta, eksi U+2212; sıfıra yuvarlanan değer işaretsiz."""
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not sifir) else s


def yz(x: float, b: int = 2, arti: bool = False) -> str:
    s = "%" + sayi(abs(x), b)
    sifir = float(sayi(abs(x), b).replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not sifir) else s


def bicimle(deger, bicim: str, hane: int = 2, arti: bool = False) -> str:
    if bicim == "sayi":
        return sayi(float(deger), hane, arti)
    if bicim == "yz":
        return yz(float(deger), hane, arti)
    if bicim == "bp":
        return f"{sayi(float(deger), hane, arti)} bp"
    if bicim == "puan":
        return f"{sayi(float(deger), hane, arti)} puan"
    if bicim == "kat":
        return f"{sayi(float(deger), hane, arti)}×"
    if bicim == "tam":
        return sayi(float(deger), 0, arti)
    if bicim == "tarih":
        s = str(deger)
        return f"{s[8:10]}.{s[5:7]}.{s[:4]}"
    if bicim == "ay":
        s = str(deger)
        return f"{s[5:7]}.{s[:4]}"
    if bicim == "gun":
        s = str(deger)
        return f"{int(s[8:10])} {AY[int(s[5:7])]} {s[:4]}"
    if bicim == "metin":
        return str(deger)
    raise ValueError(f"tanınmayan biçim: {bicim}")


# ─────────────────────────────────────────────── metin hazırlığı
def _ek_sil(s: str) -> str:
    """Kesme işaretinden sonraki eki siler: "54,9'dan" → "54,9'"."""
    return re.sub(r"'[a-zçğıöşüâîû]+", "'", s)


def _norm(s: str) -> str:
    s = s.replace("{,}", ",").replace("\\%", "%").replace("\\,", " ").replace("~", " ")
    s = s.replace("’", "'")
    s = re.sub(r"(?<![\w.,)\]])-(?=\d)", "−", s)   # KaTeX içindeki ASCII eksi (biçim sınaması formülü taramaz)
    return _ek_sil(re.sub(r"\s+", " ", s))


# Envanter: ondalık sayı, yüzde (tam sayı dahil), bp ve puan ifadeleri.
ONDALIK = re.compile(r"(?<![\d.,])\d{1,3}(?:\.\d{3})*,\d+|(?<![\d.,])\d+,\d+")
BIRIMLI = re.compile(r"%\s?\d+(?:[.,]\d+)*|(?<![\d.,])\d+(?:[.,]\d+)*\s?(?:bp|puan)\b")


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
                    out.append(f"{self.ad}: …{self.n[max(0, x.start() - 60):x.end() + 25]}…")
        return out

    def sayi_adedi(self) -> int:
        return len(ONDALIK.findall(self.n)) + len(BIRIMLI.findall(self.n))


ALAN: dict[str, Alan] = {}


def bolumler(m: str) -> tuple[dict, str]:
    _, on, govde = m.split("---", 2)
    alan = {}
    for ad in ("title", "description", "ozet"):
        x = re.search(rf"^{ad}: (['\"])(.*)\1\s*$", on, re.M)
        alan[ad] = x.group(2).replace("''", "'") if x else ""
        if not x:
            hatalar.append(f"ön bilgi alanı okunamadı: {ad}")
    return alan, govde


ETIKET = re.compile(r"</?[A-Za-z][^>]*>")


def duz_metin(govde: str) -> str:
    """Envanterin taradığı metin: import satırları, kod, figür/araç etiketleri ve
    varsayımsal kutular dışarıda; formüller ve tablolar İÇERİDE (çözümlerdeki
    aritmetik de sınanır)."""
    g = re.sub(r"^import .*$", " ", govde, flags=re.M)
    g = re.sub(r"```.*?```", " ", g, flags=re.S)
    g = re.sub(r"`[^`]*`", " ", g)
    g = re.sub(r"<GrafikEmbed[^>]*/>", " ", g)
    g = re.sub(r"<Makro[A-Za-z]+[^>]*/>", " ", g)
    g = re.sub(r'<div class="not sinav-ornek">.*?</div>', " ", g, flags=re.S)
    # kalan etiketler (details, summary, span). Etiket harfle ya da "/" ile başlar: formüldeki
    # "$x < 0$" bir etiket değildir; "<[^>]+>" onu bir sonraki ">"e kadar uzatıp aradaki
    # metni (bir sonraki bölümün başı dahil) eşlemeden ve sayı envanterinden düşürüyordu.
    g = re.sub(ETIKET, " ", g)
    return g


# ─────────────────────────────────────────────── 1 · arşiv
def _oz(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def arsiv() -> dict:
    ozler = {}
    for dizin in (VERI, VERI / "bulut"):
        kp = dizin / "kunye.json"
        if not kp.exists():
            hatalar.append(f"künye yok: {kp.relative_to(BURASI)}")
            continue
        kunye = json.loads(kp.read_text(encoding="utf-8"))
        for ad, k in kunye["dosyalar"].items():
            sayac["arsiv"] += 1
            yol = dizin / ad
            if not yol.exists():
                hatalar.append(f"arşiv dosyası yok: {dizin.name}/{ad}")
                continue
            oz = hashlib.sha256(gzip.decompress(yol.read_bytes())).hexdigest()
            if oz != k["sha256"]:
                hatalar.append(f"arşiv özü künyeyle tutmuyor: {dizin.name}/{ad}")
            ozler[f"{dizin.name}/{ad}"] = k["sha256"]
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    sayac["arsiv"] += 2
    if o.get("arsiv_ozleri") != dict(sorted(ozler.items())):
        hatalar.append("ölçüm dosyası bu arşivle üretilmemiş (özler ayrışıyor) — olcum.py yeniden koşulmalı")
    for ad in OLCUM_BETIKLERI:
        p = BURASI / ad
        if p.exists() and o.get("betik_ozleri", {}).get(ad) != _oz(p):
            hatalar.append(f"ölçüm dosyası bugünkü {ad} ile üretilmemiş — olcum.py yeniden koşulmalı")
    if o.get("eksik_modul"):
        hatalar.append(f"ölçüm dosyasında eksik bölüm modülü: {o['eksik_modul']}")
    return o


# ─────────────────────────────────────────────── araçların Python eşleri
# Bileşenlerdeki formüllerin birebir karşılığı (6. soru kaynak metninden sınar).
def taylor_kural(rs, pi, hedef, phipi, phiy, acik):
    return rs + pi + (phipi - 1) * (pi - hedef) + phiy * acik


def reel(i, pi):
    return ((1 + i / 100) / (1 + pi / 100) - 1) * 100


def haftalik_bilesik(i):
    """Bir haftalık repo kotasyonu → yıllık bileşik."""
    return ((1 + i / 100 / 52) ** 52 - 1) * 100


def gecelik_bilesik_360(i):
    """Dolar gecelik (ACT/360) kotasyonu → yıllık bileşik."""
    return ((1 + i / 100 / 360) ** 365 - 1) * 100


def taylor_R(pol, pi, i_yabanci, pi_yabanci):
    """Taylor aracının B bloğu: bileşik reel faiz farkı."""
    return reel(haftalik_bilesik(pol), pi) - reel(gecelik_bilesik_360(i_yabanci), pi_yabanci)


def borc_adim(d, i, g, alfa, e, pb):
    kartopu = d * (i - g) / (1 + g)
    kur = alfa * d * e / (1 + g)
    return d + kartopu + kur - pb


def pb_yildiz(d, i, g, alfa, e):
    return d * (i - g + alfa * e) / (1 + g)


def redk_sapma(redk, denge):
    return math.log(redk / denge) * 100


def yari_omur(rho):
    return math.log(0.5) / math.log(rho) if 0 < rho < 1 else math.inf


def a_blok(rho, sapma):
    return -(rho ** 12 - 1) * sapma


def tasima(i, i_yabanci):
    return ((1 + i / 100) / (1 + i_yabanci / 100) - 1) * 100


def tasima3(i, i_yabanci):
    return (((1 + i / 100) / (1 + i_yabanci / 100)) ** 0.25 - 1) * 100


def ima_prim(q_fark, R, tb, tc):
    return (q_fark + R * tb) / tc


ESLER = {"taylor_kural": taylor_kural, "reel": reel, "haftalik_bilesik": haftalik_bilesik,
         "gecelik_bilesik_360": gecelik_bilesik_360, "taylor_R": taylor_R, "borc_adim": borc_adim, "pb_yildiz": pb_yildiz,
         "redk_sapma": redk_sapma, "yari_omur": yari_omur, "a_blok": a_blok, "tasima": tasima,
         "tasima3": tasima3, "ima_prim": ima_prim}


# ─────────────────────────────────────────────── 2 · yan dosya
def yol_al(o: dict, yol: str):
    x = o
    for p in yol.split("."):
        if isinstance(x, list):
            x = x[int(p)]
        else:
            x = x[p]
    return x


def deger(o: dict, d: dict, arac: dict):
    if "yol" in d:
        v = yol_al(o, d["yol"])
    elif "ifade" in d:
        ortam = {"__builtins__": {"abs": abs, "min": min, "max": max, "round": round, "sum": sum, "len": len}}
        ortam.update(ESLER)
        ortam.update({"v": lambda y: yol_al(o, y), "a": lambda y: yol_al(arac, y), "math": math})
        v = eval(d["ifade"], ortam)  # noqa: S307 — kısıtlı ortam, depodaki yan dosya
    else:
        raise KeyError("değerin yolu ya da ifadesi yok")
    if v is None:
        raise ValueError(f"ölçüm değeri boş: {d}")
    if isinstance(v, (int, float)) and "carpan" in d:
        v = v * d["carpan"]
    return v


def yan_dosya(o: dict, arac: dict, kaynaklar: dict, yollar: list | None = None) -> None:
    yollar = sorted((VERI / "sayilar").glob("*.json")) if yollar is None else yollar
    if not yollar:
        hatalar.append("yan dosya yok: veri/sayilar/*.json")
    for yp in yollar:
        y = json.loads(yp.read_text(encoding="utf-8"))
        for g in y.get("girdiler", []):
            tur = g.get("tur")
            yer = g.get("yer", "govde")
            if yer not in ALAN:
                hatalar.append(f"{yp.name}: bilinmeyen yer {yer!r}")
                continue
            if tur == "tablo":
                tablo_sina(yp.name, g, o, arac)
                continue
            parca = g.get("parca", "")
            sayac["metin"] += 1
            if not ALAN[yer].isaretle(parca):
                hatalar.append(f"{yp.name} · {yer} · metinde yok: {parca!r}")
                continue
            if tur in ("olcum", "hesap"):
                for d in g.get("degerler", []):
                    try:
                        v = deger(o, d, arac)
                        s = bicimle(v, d.get("bicim", "sayi"), d.get("hane", 2), d.get("arti", False))
                    except Exception as e:  # noqa: BLE001
                        hatalar.append(f"{yp.name} · değer okunamadı ({d}): {e}")
                        continue
                    if _norm(s) not in _norm(parca):
                        hatalar.append(f"{yp.name} · {yer} · ölçüm {s!r} parçada yok: {parca!r}")
            elif tur == "kaynak":
                sayac["kaynak"] += 1
                k = kaynaklar.get(g.get("kaynak"))
                if not k:
                    hatalar.append(f"{yp.name} · kaynak listede yok: {g.get('kaynak')!r} ({parca!r})")
                elif k.get("durum") not in ("dogrulandi", "kismen"):
                    hatalar.append(f"{yp.name} · kaynak doğrulanmamış ({k.get('durum')}): {g.get('kaynak')}")
            elif tur == "sabit":
                sayac["sabit"] += 1
                if not g.get("neden"):
                    hatalar.append(f"{yp.name} · sabitin nedeni yazılmamış: {parca!r}")
            else:
                hatalar.append(f"{yp.name} · bilinmeyen girdi türü: {tur!r}")


SATIRLAR: list[str] = []
SATIR_KAPSAM: list[list[bool]] = []


def tablo_sina(ad: str, g: dict, o: dict, arac: dict) -> None:
    hedef = _norm(g["satir"]).strip()
    for i, s in enumerate(SATIRLAR):
        if _norm(s).strip() == hedef:
            break
    else:
        hatalar.append(f"{ad} · tablo satırı metinde yok: {g['satir']!r}")
        return
    hucre = [h.strip().replace("**", "") for h in SATIRLAR[i].strip()[1:-1].split("|")]
    sayili = [j for j, h in enumerate(hucre) if ONDALIK.search(_norm(h)) or BIRIMLI.search(_norm(h))]
    degerler = g.get("degerler", [])
    if len(degerler) != len(sayili):
        hatalar.append(f"{ad} · tablo satırında {len(sayili)} sayılı hücre, yan dosyada {len(degerler)} değer: {g['satir']!r}")
    for j, d in zip(sayili, degerler):
        sayac["hucre"] += 1
        if d.get("tur") == "kaynak" or d.get("kaynak"):
            SATIR_KAPSAM[i][j] = True
            continue
        try:
            s = bicimle(deger(o, d, arac), d.get("bicim", "sayi"), d.get("hane", 2), d.get("arti", False))
        except Exception as e:  # noqa: BLE001
            hatalar.append(f"{ad} · tablo değeri okunamadı ({d}): {e}")
            continue
        if _norm(s) != _norm(hucre[j]) and _norm(s) not in _norm(hucre[j]):
            hatalar.append(f"{ad} · tablo hücresi: metin {hucre[j]!r}, ölçüm {s!r} ({hucre[0]!r})")
        else:
            SATIR_KAPSAM[i][j] = True
    SATIR_KAPSAM[i][0] = True


# ─────────────────────────────────────────────── 3 · envanter
def envanter() -> None:
    for a in ALAN.values():
        for k in a.kapsanmayan():
            hatalar.append(f"kapsanmayan sayı · {k}")
        sayac["sayi"] += a.sayi_adedi()
    for i, s in enumerate(SATIRLAR):
        hucre = [h.strip().replace("**", "") for h in s.strip()[1:-1].split("|")]
        for j, h in enumerate(hucre):
            n = _norm(h)
            if ONDALIK.search(n) or BIRIMLI.search(n):
                sayac["sayi"] += 1
                if not SATIR_KAPSAM[i][j]:
                    hatalar.append(f"kapsanmayan tablo hücresi · {hucre[0]!r} · sütun {j + 1}: {h!r}")


# ─────────────────────────────────────────────── 4 · biçim
def bicim_sina(govde: str) -> None:
    g = re.sub(r"\$\$.*?\$\$", "", govde, flags=re.S)
    g = re.sub(r"\$[^$\n]+\$", "", g)
    g = re.sub(r"`[^`]*`", "", g)
    g = re.sub(ETIKET, "", g)
    for x in re.finditer(r"(?<![\w/.\-–])-%?\d", g):
        hatalar.append(f"ASCII tireli eksi sayı: {g[max(0, x.start() - 30):x.end() + 10]!r}")
    for x in re.finditer(r"\d[ \t]*%", g):
        hatalar.append(f"arkaya yazılmış yüzde: {g[max(0, x.start() - 20):x.end() + 5]!r}")
    sayac["metin"] += 1


# ─────────────────────────────────────────────── 5 · figürler
def _figur_basliklari(h: str, no: str) -> list[str]:
    """Figür dosyasındaki 'Şekil NN —' ile başlayan başlık metinleri (Plotly düzeninin JSON'undan)."""
    out = []
    for m in re.finditer(r'"text":"((?:[^"\\]|\\.)*)"', h):
        try:
            t = json.loads('"' + m.group(1) + '"')
        except ValueError:
            continue
        if t.startswith(f"Şekil {no} —"):
            out.append(t)
    return out


def figurler(govde: str) -> None:
    sys.path.insert(0, str(BURASI))
    from sekil_ortak import tasan_satirlar   # çizim kütüphanesi olmadan da içe aktarılır
    kaynak = (BURASI / "sekil.py").read_text(encoding="utf-8")
    bas = kaynak.index("SEKILLER = {")
    blok = kaynak[bas:kaynak.index("}", bas)]
    numaralar = re.findall(r'"(\d\d)":', blok)
    oz = _oz(VERI / "olcum.json")
    gomulu = re.findall(r'<GrafikEmbed src="/arastirma/' + SLUG + r'/((\d\d)_[a-z0-9_]+)\.html"[^>]*no="(\d\d)"', govde)
    if [n for _, n, _ in gomulu] != [f"{i:02d}" for i in range(1, len(gomulu) + 1)]:
        hatalar.append(f"gömülen figürler sıralı değil: {[n for _, n, _ in gomulu]}")
    if sorted(numaralar) != [n for _, n, _ in gomulu]:
        hatalar.append(f"sekil.py listesi ({sorted(numaralar)}) ile gömülen figürler ({[n for _, n, _ in gomulu]}) aynı değil")
    for ad, on, no in gomulu:
        sayac["figur"] += 1
        if on != no:
            hatalar.append(f"figür dosyasının öneki gömme numarasıyla aynı değil: {ad} · no {no}")
        yol = SEKIL / f"{ad}.html"
        if not yol.exists():
            hatalar.append(f"figür yok: {ad}.html")
            continue
        h = yol.read_text(encoding="utf-8")
        x = re.search(r'<meta name="tto-olcum-ozu" content="([0-9a-f]{64})">', h)
        if not x or x.group(1) != oz:
            hatalar.append(f"figür bugünkü ölçüm dosyasından çizilmemiş — sekil.py yeniden koşulmalı: {ad}")
        if f"Şekil {no} —" not in h and f"\\u015eekil {no} \\u2014" not in h:
            hatalar.append(f"figürün içindeki başlık 'Şekil {no}' değil: {ad}")
        # Başlık bloğu telefonun gömme çerçevesine sığmalı (Plotly başlığı sarmaz, sağ ucu kırpılır).
        # Ölçü çizim katmanının KENDİ tanımıdır (sekil_ortak.tasan_satirlar); orada yalnız uyarıydı ve
        # elle satırlanmış dört figür ekrana basılan uyarıyla yayına gitmişti.
        for b in _figur_basliklari(h, no):
            for t in tasan_satirlar(b):
                hatalar.append(f"figür başlığı telefonun gömme çerçevesinde taşar: {ad} · {t}")


# ─────────────────────────────────────────────── 6 · araçlar
ARAC_KAYNAK = {
    "MakroTaylorHesaplayici.astro": ["rs + pi + (phipi - 1) * (pi - hedef) + phiy * acik",
                                     "((1 + i / 100) / (1 + pi / 100) - 1) * 100",
                                     "(Math.pow(1 + i / 100 / 52, 52) - 1) * 100",
                                     "(Math.pow(1 + i / 100 / 360, 365) - 1) * 100",
                                     "reel(haftalikBilesik(pol), pi), ry = reel(gecelikBilesik360(iy), piy)"],
    "MakroBorcHesaplayici.astro": ["(d * (i - g)) / (1 + g)", "(alfa * d * e) / (1 + g)",
                                   "d + kartopu + kur - pb", "(d * (i - g + alfa * e)) / (1 + g)"],
    "MakroRedkHesaplayici.astro": ["Math.log(redk / denge) * 100", "Math.log(0.5) / Math.log(rho)",
                                   "-(Math.pow(rho, 12) - 1) * sapma"],
    "MakroKurBloklari.astro": ["((1 + i / 100) / (1 + is / 100) - 1) * 100",
                               "(Math.pow((1 + i / 100) / (1 + is / 100), 0.25) - 1) * 100",
                               "(qFark + R * tb) / tc"],
}


def araclar(o: dict, arac: dict) -> None:
    for dosya, ifadeler in ARAC_KAYNAK.items():
        p = BILESEN / dosya
        if not p.exists():
            hatalar.append(f"araç bileşeni yok: {dosya}")
            continue
        t = p.read_text(encoding="utf-8")
        for ifade in ifadeler:
            sayac["arac"] += 1
            if ifade not in t:
                hatalar.append(f"{dosya}: Python eşinin formülü bileşende yok (iki tanım ayrışmış): {ifade!r}")
    if arac.get("gecici"):
        hatalar.append("arac.json geçici: ölçüm dosyasından üretilmemiş (arac_veri.py koşulmalı)")
    beklenen = arac_beklenen(o)
    if beklenen is not None:
        sayac["arac"] += 1
        if beklenen != arac:
            hatalar.append("arac.json ölçüm dosyasının bugünkü hâliyle aynı değil (arac_veri.py yeniden koşulmalı)")


def arac_beklenen(o: dict):
    """arac_veri.py ile aynı eşleme (o dosya içe aktarılır; pandas istemez)."""
    p = BURASI / "arac_veri.py"
    if not p.exists():
        hatalar.append("arac_veri.py yok")
        return None
    sys.path.insert(0, str(BURASI))
    import arac_veri  # noqa: E402
    return arac_veri.kur(o)


# ─────────────────────────────────────────────── 7 · kaynaklar
def kaynak_listesi() -> dict:
    p = VERI / "kaynaklar.json"
    if not p.exists():
        hatalar.append("kaynak listesi yok: veri/kaynaklar.json")
        return {}
    k = json.loads(p.read_text(encoding="utf-8"))
    out = {}
    for x in k.get("iddialar", []):
        out[x["anahtar"]] = x
        if x.get("durum") in ("dogrulandi", "kismen") and not x.get("url"):
            hatalar.append(f"doğrulanmış kaynakta adres yok: {x['anahtar']}")
    return out


def _sade(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower().replace("ı", "i"))
    return "".join(c for c in s if not unicodedata.combining(c))


_AD = r"[A-ZÇĞİÖŞÜ][A-Za-zÀ-ÿçğıöşüÇĞİÖŞÜ'’\-]+"
ATIF = re.compile(rf"({_AD})(?:,? (?:ve|vd\.|and|&) {_AD}| ve diğerleri|, {_AD})*['’]?,? "
                  rf"\((\d{{4}})[a-z]?(?:[;,] ?\d{{4}}[a-z]?)*\)")


# Parantez içi biçim de atıftır: "(Fischer 1993)". Ay adları atıf değildir ("(Eylül 2018)").
ATIF_PARANTEZ = re.compile(rf"\(({_AD})(?:,? (?:ve|vd\.|and|&) {_AD}| ve diğerleri)*,? (\d{{4}})[a-z]?[;)]")


def atif_dizini(kaynaklar: dict) -> dict:
    """(ilk yazarın soyadı ya da kayıt anahtarının harf kökü, yıl) → kayıt durumları."""
    d: dict = {}
    for k, x in kaynaklar.items():
        yil = re.search(r"\((\d{4})[a-z]?[),]", x.get("kunye", ""))
        if yil:
            ilk = re.split(r"[,(]", x["kunye"])[0].strip()
            if ilk:
                d.setdefault((_sade(ilk.split()[-1]), yil.group(1)), []).append(x.get("durum"))
        a = re.match(r"([a-z_]+?)_?(\d{4})", k)
        if a:
            d.setdefault((a.group(1).split("_")[0], a.group(2)), []).append(x.get("durum"))
    return d


def atif_envanteri(metin: str, kaynaklar: dict) -> None:
    dizin = atif_dizini(kaynaklar)
    n = _norm(metin)
    adaylar = list(ATIF.finditer(n)) + [x for x in ATIF_PARANTEZ.finditer(n) if x.group(1) not in AY]
    for x in adaylar:
        sayac["atif"] += 1
        durum = dizin.get((_sade(x.group(1).rstrip("'’")), x.group(2)), [])
        if not any(du in ("dogrulandi", "kismen") for du in durum):
            neden = "kayıtta yok" if not durum else f"kayıt doğrulanmamış ({', '.join(map(str, durum))})"
            hatalar.append(f"atıf {neden}: {x.group(0)!r}")


def parca_figurler(govde: str) -> None:
    """Parça kipinde figür sırası sınanmaz (bütün ders birleşince sınanır); yalnız
    gömme biçimi ve numara–dosya öneki eşliği."""
    for ad, on, no in re.findall(r'<GrafikEmbed src="/arastirma/' + SLUG + r'/((\d\d)_[a-z0-9_]+)\.html"[^>]*no="(\d\d)"', govde):
        sayac["figur"] += 1
        if on != no:
            hatalar.append(f"figür dosyasının öneki gömme numarasıyla aynı değil: {ad} · no {no}")
    for x in re.findall(r"<GrafikEmbed[^>]*/>", govde):
        if f'src="/arastirma/{SLUG}/' not in x or 'no="' not in x:
            hatalar.append(f"gömme biçimi tanınmıyor: {x[:120]}")


def parca(ad: str) -> int:
    """Bir bölüm parçasını tek başına sınar: `metin/<ad>.mdx` + `veri/sayilar/<ad>.json`.
    Yazar bölümünü bitirince bunu koşturur; bütün ders `python3 dogrula.py` ile sınanır."""
    o = arsiv()
    arac = json.loads(ARAC.read_text(encoding="utf-8")) if ARAC.exists() else {}
    kaynaklar = kaynak_listesi()
    mdx = BURASI / "metin" / f"{ad}.mdx"
    yan = VERI / "sayilar" / f"{ad}.json"
    if not mdx.exists() or not yan.exists():
        hatalar.append(f"parça ya da yan dosyası yok: {mdx.relative_to(BURASI)} · {yan.relative_to(BURASI)}")
        return rapor()
    govde = mdx.read_text(encoding="utf-8")
    duz = duz_metin(govde)
    for s in duz.splitlines():
        if s.strip().startswith("|") and s.strip().endswith("|") and not set(s.replace("|", "").strip()) <= set("-: "):
            SATIRLAR.append(s)
            SATIR_KAPSAM.append([False] * len(s.strip()[1:-1].split("|")))
    duz_tablosuz = "\n".join(s for s in duz.splitlines() if not (s.strip().startswith("|") and s.strip().endswith("|")))
    ALAN["govde"] = Alan("gövde", duz_tablosuz)
    for k, ad_ in (("description", "açıklama"), ("ozet", "kart özeti"), ("title", "başlık")):
        ALAN[k] = Alan(ad_, "")
    yan_dosya(o, arac, kaynaklar, [yan])
    envanter()
    bicim_sina(govde)
    parca_figurler(govde)
    atif_envanteri(duz, kaynaklar)
    return rapor()


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "--parca":
        return parca(sys.argv[2])
    o = arsiv()
    arac = json.loads(ARAC.read_text(encoding="utf-8")) if ARAC.exists() else {}
    if not arac:
        hatalar.append("arac.json yok")
    kaynaklar = kaynak_listesi()
    if not MDX.exists():
        hatalar.append(f"ders metni yok: {MDX.relative_to(KOK)}")
        return rapor()
    m = MDX.read_text(encoding="utf-8")
    sys.path.insert(0, str(BURASI))
    import birlestir  # noqa: E402 — ders metni bölüm parçalarından kurulur, elle düzenlenmez
    try:
        if birlestir.kur() != m:
            hatalar.append("ders metni bölüm parçalarıyla aynı değil (birlestir.py yeniden koşulmalı)")
    except SystemExit as e:
        hatalar.append(str(e))
    on, govde = bolumler(m)
    duz = duz_metin(govde)
    for s in duz.splitlines():
        if s.strip().startswith("|") and s.strip().endswith("|") and not set(s.replace("|", "").strip()) <= set("-: "):
            SATIRLAR.append(s)
            SATIR_KAPSAM.append([False] * len(s.strip()[1:-1].split("|")))
    duz_tablosuz = "\n".join(s for s in duz.splitlines() if not (s.strip().startswith("|") and s.strip().endswith("|")))
    ALAN["govde"] = Alan("gövde", duz_tablosuz)
    ALAN["description"] = Alan("açıklama", on["description"])
    ALAN["ozet"] = Alan("kart özeti", on["ozet"])
    ALAN["title"] = Alan("başlık", on["title"])
    yan_dosya(o, arac, kaynaklar)
    envanter()
    bicim_sina(govde)
    figurler(govde)
    araclar(o, arac)
    atif_envanteri(duz, kaynaklar)
    return rapor()


def rapor() -> int:
    if hatalar:
        print(f"✗ Makrodan Kura ve Faize dersi · {len(hatalar)} hata")
        for h in hatalar[:400]:
            print("  ·", h)
        if len(hatalar) > 400:
            print(f"  … ve {len(hatalar) - 400} hata daha")
        return 1
    print(f"✓ Makrodan Kura ve Faize dersi · {sayac['arsiv']} arşiv ölçütü, {sayac['metin']} metin ölçütü, "
          f"{sayac['hucre']} tablo hücresi, {sayac['kaynak']} kaynaklı, {sayac['sabit']} sabit; {sayac['sayi']} sayının "
          f"hepsi sınanmış ya da kaynağıyla bildirilmiş; {sayac['atif']} atıf doğrulanmış kayda eşlendi; "
          f"{sayac['figur']} figür, {sayac['arac']} araç ölçütü")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
