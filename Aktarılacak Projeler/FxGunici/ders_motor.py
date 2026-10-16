#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX GÜN İÇİ STRATEJİLER — ders motoru: şablon + ölçüm dosyası → MDX. YALNIZ STANDART KÜTÜPHANE.

Ders metni elle sayı taşımaz: her ölçüm sayısı ölçüm dosyasından (`cikti/ders/olcum.json`) bir yer
tutucuyla basılır. Motor yazıcıda (`ders_yaz.py`) ve kapıda (`dogrula.py`) AYNIDIR: kapı dersi yeniden
üretir ve sayfadaki metinle birebir kıyaslar. Ölçüm değişip ders yeniden üretilmezse kapı düşer; ölçüme
dayanan bir cümlenin dayanağı değişirse (iddia) üretimin kendisi düşer.

ŞABLON SÖZDİZİMİ (`metin/*.md`, `metin/strateji/*.md`)
  {{ yol | biçim }}    ölçümden değer. Yol noktalı anahtar dizisidir; noktalı ya da boşluklu anahtar çift
                       tırnakta ("0.5"), liste sırası köşeli parantezde ([0]). Kök adları: O ölçüm, K künye,
                       ON önceden kayıt; strateji şablonunda ayrıca B birim, BID birimin adı, E/G/J/A dört
                       paritenin birim kaydı (EUR/USD, GBP/USD, USD/JPY, AUD/USD), H havuz.
  {{? koşul }}         İDDİA: metin bir ölçüme dayanıyorsa dayanağı yanına yazılır. Tutmazsa üretim DÜŞER:
                       ölçüm değişmiş, cümle eskimiştir. Çıktıya hiçbir şey yazmaz.
  {{! blok arg … }}    üretilmiş MDX parçası (tablo, figür gömmesi, kontrol listesi) — BLOKLAR'da.
  {{= "metin" }}       BİLDİRİLMİŞ SABİT: ölçümden gelmeyen ama metne yazılan sayı (bir tanımın sabiti,
                       göstergenin standart parametresi). Kapı hepsini adıyla listeler.
  {% if koşul %} … {% elif koşul %} … {% else %} … {% endif %}    (iç içe olabilir)
  Koşul: a op b (== != < <= > >=) · a · not a · and / or (and önce bağlar). Değer: yol, sayı, "dizgi",
  None, True, False, abs(yol), len(yol).

BİÇİMLER (site sözleşmesi, `ortak/bicim`in eşi: ondalık virgül, binlik nokta, eksi U+2212, yüzde önde;
sıfıra yuvarlanan değer işaretsizdir): r · r1 · r3 (işaretli R) · ra (işaretli R, |x| < 0,005 iken üç hane: sıfıra
yuvarlanan bir artı ya da eksi "0,00" okunmasın) · sh (işaretli Sharpe) · s0 … s3 (işaretsiz sayı; eksi yine
yazılır) · p (p değeri: 0,01'in altı "< 0,01", 0,1'in altı üç hane) · p1 (işaretli pip) · yz0 · yz1 (kesirden
yüzde) · yzs1 (işaretli yüzde) · n (tam sayı) · tarih · tarih_uzun · ay_uzun · ay_liste ("YYYY-AA" listesi) ·
saat_tsi (epoch saniye → TSİ ss:dd) · fiyat (nokta → fiyat; parite yolda) · ad · kisa (birim adı) · hukum · deger ·
param · olay · kosul · t (metin) · liste. Biçimin sonundaki "?" ölçülemeyen değeri "—" yazar; "?" yoksa ölçülemeyen
değer üretimi düşürür (ölçülmemiş bir sayıyı sessizce boş basmak yok).

PARİTELER ölçümün künyesinden (`ayar.toml` → `kunye.ciftler`, `kunye.nokta`) kurulur; bu dosyada elle tutulan bir
parite listesi yoktur. Listenin ilk paritesi dersin ana paritesidir (örnekler, alıştırmalar, koşul figürü).
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import adlar

BURASI = Path(__file__).resolve().parent
METIN = BURASI / "metin"
SLUG = "fx-gunici"
SEKIL_YOL = f"/arastirma/{SLUG}"
#: Künyeden doldurulur (`parite_kur`); sıra künyenin sırasıdır.
PARITE: dict[str, str] = {}
NOKTA: dict[str, float] = {}
PIP: dict[str, float] = {}
HANE: dict[str, int] = {}
#: Şablonların dört parite kökü (E/G/J/A). Künyede olmayan parite bağlanmaz (kök None olur).
KISA_AD = {"E": "EURUSD", "G": "GBPUSD", "J": "USDJPY", "A": "AUDUSD"}


def parite_ad(cift: str) -> str:
    """Sembolden okur adı: EURUSD → EUR/USD (altı harfli FX sembolü; öbürleri olduğu gibi)."""
    return f"{cift[:3]}/{cift[3:]}" if len(cift) == 6 and cift.isalpha() else cift


def parite_kur(kunye: dict) -> None:
    """Parite sözlüklerini ölçümün künyesinden kurar. Künyede nokta/pip tanımı olmayan parite ÜRETİMİ DÜŞÜRÜR:
    adı bilinmeyen bir pariteyi sessizce atlamak, tablodan bir satırın habersiz düşmesi olurdu."""
    ciftler = list(kunye.get("ciftler") or [])
    nokta, pip = kunye.get("nokta") or {}, kunye.get("pip") or {}
    eksik = [c for c in ciftler if c not in nokta or c not in pip]
    if not ciftler or eksik:
        raise SablonHatasi(f"künyede parite ya da nokta/pip tanımı yok: {eksik or 'ciftler boş'}")
    PARITE.clear(), NOKTA.clear(), PIP.clear(), HANE.clear()
    for c in ciftler:
        PARITE[c] = parite_ad(c)
        NOKTA[c], PIP[c] = float(nokta[c]), float(pip[c])
        HANE[c] = int(round(-math.log10(float(nokta[c]))))


def ana() -> str:
    """Dersin ana paritesi: künyenin ilk paritesi."""
    return next(iter(PARITE))
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım",
      "Aralık"]
TSI = timezone(timedelta(hours=3))      # Türkiye 2016'dan beri sabit UTC+3


class SablonHatasi(Exception):
    pass


# ─────────────────────────────────────────────────────────────── biçim
def sayi(x: float, b: int = 2, arti: bool = False) -> str:
    s = f"{abs(x):,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not sifir) else s


def yuzde(x: float, b: int = 1, arti: bool = False) -> str:
    s = sayi(abs(x) * 100, b)
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−%" + s
    return ("+%" if (arti and x > 0 and not sifir) else "%") + s


_SON_SOZ = {0: "sıfır", 1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz",
            9: "dokuz", 10: "on", 20: "yirmi", 30: "otuz", 40: "kırk", 50: "elli", 60: "altmış", 70: "yetmiş",
            80: "seksen", 90: "doksan", 100: "yüz", 1000: "bin", 10 ** 6: "milyon"}


def _son_soz(n: int) -> str:
    """Bir tam sayının Türkçe okunuşundaki son sözcük (ek uyumu ona göre kurulur): 11 → bir, 20 → yirmi, 300 → yüz."""
    n = abs(int(n))
    if n == 0:
        return "sıfır"
    for bolen in (10 ** 6, 1000, 100):
        if n % bolen == 0:
            return _SON_SOZ[bolen]
    return _SON_SOZ[n % 10] if n % 10 else _SON_SOZ[n % 100 - n % 10 if n % 100 >= 10 else n % 10]


def ek(n: int, kip: str) -> str:
    """Sayıya gelen ek, kesme işaretiyle: kip "i" (iyelik: 11'i, 20'si), "inde" (iyelik + bulunma: 11'inde,
    20'sinde), "de" (bulunma: 4'te, 20'de), "e" (yönelme: 4'e, 20'ye), "in" (ilgi: 4'ün, 20'nin). Uyum, sayının
    okunuşunun son sözcüğünden."""
    s = _son_soz(n)
    unlu = [h for h in s if h in "aeıioöuü"][-1]
    on = unlu in "eiöü"
    yuvarlak = unlu in "oöuü"
    dar = ("ü" if yuvarlak else "i") if on else ("u" if yuvarlak else "ı")
    genis = "e" if on else "a"
    unluyle = s[-1] in "aeıioöuü"
    sert = s[-1] in "çfhkpsşt"
    if kip == "i":
        e_ = ("s" if unluyle else "") + dar
    elif kip == "inde":
        e_ = ("s" if unluyle else "") + dar + "nd" + genis
    elif kip == "de":
        e_ = ("t" if sert else "d") + genis
    elif kip == "e":
        e_ = ("y" if unluyle else "") + genis
    elif kip == "in":
        e_ = ("n" if unluyle else "") + dar + "n"
    else:
        raise SablonHatasi(f"bilinmeyen ek: {kip}")
    return f"{sayi(n, 0)}'{e_}"


def bas_buyuk(s: str) -> str:
    """Cümle başını büyütür, Türkçe kuralla (i → İ, ı → I); geri kalanına dokunmaz ("NR7", "60 dk" olduğu gibi)."""
    if not s:
        return s
    return {"i": "İ", "ı": "I"}.get(s[0], s[0].upper()) + s[1:]


def tarih(g: str) -> str:
    y, a, d = str(g)[:10].split("-")
    return f"{d}.{a}.{y}"


def tarih_uzun(g: str) -> str:
    y, a, d = str(g)[:10].split("-")
    return f"{int(d)} {AY[int(a)]} {y}"


def ay_uzun(g: str) -> str:
    y, a = str(g)[:7].split("-")
    return f"{AY[int(a)]} {y}"


def saat_tsi(t) -> str:
    return datetime.fromtimestamp(int(t), tz=TSI).strftime("%H:%M")


def _sayisal(v) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SablonHatasi(f"sayı bekleniyordu: {v!r}")
    if not math.isfinite(v):
        raise SablonHatasi("ölçülemeyen değer (NaN/sonsuz)")
    return float(v)


def bicimle(v, bicim: str, yol: str = "") -> str:
    bos = bicim.endswith("?")
    bicim = bicim.rstrip("?")
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        if bos:
            return "—"
        raise SablonHatasi(f"ölçülemeyen değer: {yol} ({bicim})")
    if bicim in ("r", "r1", "r3", "sh"):
        return sayi(_sayisal(v), {"r": 2, "r1": 1, "r3": 3, "sh": 2}[bicim], arti=True)
    if bicim == "ra":
        # İki hanede sıfıra yuvarlanan değer bir hane, üçte de sıfırsa bir hane daha alır: "+0,00" ile "−0,00"
        # okura işaretsiz bir sıfır gibi görünür ve sonucun yönünü saklar.
        x = _sayisal(v)
        return sayi(x, 4 if 0 < abs(x) < 0.0005 else 3 if 0 < abs(x) < 0.005 else 2, arti=True)
    if bicim == "p":
        x = _sayisal(v)
        if x < 0.01:
            return "&lt; 0,01"
        return sayi(x, 3 if x < 0.1 else 2)
    if re.fullmatch(r"s[0-3]", bicim):
        return sayi(_sayisal(v), int(bicim[1]))
    if bicim == "p1":
        return sayi(_sayisal(v), 1, arti=True)
    if bicim in ("yz0", "yz1"):
        return yuzde(_sayisal(v), int(bicim[2]))
    if bicim == "yzs1":
        return yuzde(_sayisal(v), 1, arti=True)
    if bicim == "n":
        return sayi(_sayisal(v), 0)
    if bicim == "tarih":
        return tarih(v)
    if bicim == "tarih_uzun":
        return tarih_uzun(v)
    if bicim == "ay_uzun":
        return ay_uzun(v)
    if bicim == "ay_liste":
        if not isinstance(v, list) or not v:
            raise SablonHatasi(f"boş olmayan ay listesi bekleniyordu: {yol}")
        ay_ = [ay_uzun(x) for x in v]
        return ay_[0] if len(ay_) == 1 else ", ".join(ay_[:-1]) + " ve " + ay_[-1]
    if bicim == "saat_tsi":
        return saat_tsi(v)
    if bicim == "ad":
        return adlar.BIRIM[v][0]
    if bicim == "kisa":
        return adlar.BIRIM[v][1]
    if bicim == "hukum":
        return adlar.HUKUM[v]
    if bicim == "deger":
        return adlar.DEGER.get(str(v), str(v))
    if bicim == "param":
        return adlar.PARAM.get(str(v), str(v))
    if bicim == "olay":
        return adlar.OLAY.get(str(v), str(v))
    if bicim == "kosul":
        return adlar.KOSUL.get(str(v), str(v))
    if bicim == "parite":
        return PARITE.get(str(v), str(v))
    if bicim == "liste":
        if not isinstance(v, list):
            raise SablonHatasi(f"liste bekleniyordu: {yol}")
        return ", ".join(adlar.DEGER.get(str(x), sayi(x, 1) if isinstance(x, float) else str(x)) for x in v)
    if bicim == "t":
        return str(v)
    raise SablonHatasi(f"bilinmeyen biçim: {bicim}")


# ─────────────────────────────────────────────────────────────── yol ve koşul
_PARCA = re.compile(r'\s*(?:"([^"]*)"|\[(\d+)\]|([A-Za-z_çğıöşüÇĞİÖŞÜ0-9]+))\s*\.?')


def yol_coz(yol: str, ctx: dict):
    """Noktalı yol → değer. Yok olan anahtar None döner (biçim karar verir)."""
    yol = yol.strip()
    i, parcalar = 0, []
    while i < len(yol):
        m = _PARCA.match(yol, i)
        if not m or m.end() == i:
            raise SablonHatasi(f"yol okunamadı: {yol!r} (konum {i})")
        parcalar.append(m.group(1) if m.group(1) is not None else (int(m.group(2)) if m.group(2) else m.group(3)))
        i = m.end()
    if not parcalar or parcalar[0] not in ctx:
        raise SablonHatasi(f"bilinmeyen kök: {yol!r}")
    v = ctx[parcalar[0]]
    for p in parcalar[1:]:
        if v is None:
            return None
        if isinstance(p, int):
            v = v[p] if isinstance(v, list) and p < len(v) else None
        elif isinstance(v, dict):
            v = v.get(p)
        else:
            return None
    return v


_SAYI = re.compile(r"^[+-]?\d+(?:\.\d+)?$")


def _deger(s: str, ctx: dict):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if _SAYI.match(s):
        return float(s)
    if s in ("None", "True", "False"):
        return {"None": None, "True": True, "False": False}[s]
    m = re.fullmatch(r"(abs|len)\((.+)\)", s)
    if m:
        v = yol_coz(m.group(2), ctx)
        if v is None:
            return None
        return abs(v) if m.group(1) == "abs" else len(v)
    return yol_coz(s, ctx)


_OP = re.compile(r"\s(==|!=|<=|>=|<|>)\s")


def kosul(ifade: str, ctx: dict) -> bool:
    for parca in re.split(r"\s+or\s+", ifade.strip()):
        if all(_tek(k, ctx) for k in re.split(r"\s+and\s+", parca.strip())):
            return True
    return False


def _tek(s: str, ctx: dict) -> bool:
    s = s.strip()
    if s.startswith("not "):
        return not _tek(s[4:], ctx)
    m = _OP.search(s)
    if not m:
        return bool(_deger(s, ctx))
    a, b = _deger(s[:m.start()], ctx), _deger(s[m.end():], ctx)
    op = m.group(1)
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    if a is None or b is None:
        raise SablonHatasi(f"ölçülemeyen değerle büyüklük kıyası: {s!r}")
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]


# ─────────────────────────────────────────────────────────────── şablon
_ETIKET = re.compile(r"\{\{(.*?)\}\}|\{%(.*?)%\}", re.S)


def _belirtecler(metin: str):
    i = 0
    for m in _ETIKET.finditer(metin):
        if m.start() > i:
            yield ("metin", metin[i:m.start()])
        if m.group(1) is not None:
            yield ("yer", m.group(1).strip())
        else:
            yield ("kip", m.group(2).strip())
        i = m.end()
    if i < len(metin):
        yield ("metin", metin[i:])


def _agac(belirtecler: list) -> list:
    """if/elif/else/endif bloklarını ağaca çevirir."""
    kok: list = []
    yigin = [(kok, None)]
    for tur, deger in belirtecler:
        hedef = yigin[-1][0]
        if tur != "kip":
            hedef.append((tur, deger))
            continue
        if deger.startswith("if "):
            dugum = {"dallar": [(deger[3:].strip(), [])], "degilse": None}
            hedef.append(("if", dugum))
            yigin.append((dugum["dallar"][0][1], dugum))
        elif deger.startswith("elif "):
            dugum = yigin[-1][1]
            if dugum is None or dugum["degilse"] is not None:
                raise SablonHatasi("elif eşsiz")
            dugum["dallar"].append((deger[5:].strip(), []))
            yigin[-1] = (dugum["dallar"][-1][1], dugum)
        elif deger == "else":
            dugum = yigin[-1][1]
            if dugum is None:
                raise SablonHatasi("else eşsiz")
            dugum["degilse"] = []
            yigin[-1] = (dugum["degilse"], dugum)
        elif deger == "endif":
            if yigin[-1][1] is None:
                raise SablonHatasi("endif eşsiz")
            yigin.pop()
        else:
            raise SablonHatasi(f"bilinmeyen kip: {deger!r}")
    if len(yigin) != 1:
        raise SablonHatasi("kapanmamış if")
    return kok


class Uretim:
    """Bir dersin üretimi: şekil sayacı, bildirilmiş sabitler ve iddia sayısı burada birikir."""

    def __init__(self, olcum: dict, onkayit: dict):
        self.O, self.ON = olcum, onkayit
        parite_kur(olcum.get("kunye") or {})
        self.sekil_no = 0
        self.sabitler: list[str] = []
        self.iddia = 0
        self.yer = 0
        self.sekiller: list[str] = []
        self.birimler: list[str] = []       # bu derste işlenen strateji birimleri (sırayla)

    def kok_ctx(self) -> dict:
        if not hasattr(self, "_T"):
            self._T = toplamlar(self.O, self.ON)
        return {"O": self.O, "K": self.O["kunye"], "ON": self.ON, "T": self._T}

    def birim_ctx(self, birim: str) -> dict:
        b = self.O["birim"].get(birim)
        if b is None:
            raise SablonHatasi(f"ölçümde birim yok: {birim}")
        ctx = self.kok_ctx()
        ctx.update({"B": b, "BID": birim, "H": (b.get("havuz") or {}).get("varsayilan"),
                    "STOPSUZ": (b.get("varsayilan") or {}).get("stop_turu") == "yok"})
        for kisa, cift in KISA_AD.items():
            ctx[kisa] = (b.get("cift") or {}).get(cift) if cift in PARITE else None
        # Hüküm sayımı: önceden kayıtlı varsayılanın parite başına hükmü (ön kaydın kuralı) kaç paritede ne.
        hs = {"calisiyor": 0, "zayif": 0, "calismiyor": 0, "olculemedi": 0, "parite": 0, "maliyet": 0,
              "maliyet_oos": 0}
        for c in _ciftler(b):
            v = b["cift"][c].get("varsayilan") or {}
            hs[v.get("hukum") or "olculemedi"] = hs.get(v.get("hukum") or "olculemedi", 0) + 1
            hs["parite"] += 1
            hs["maliyet"] += 1 if v.get("maliyet_yiyor") else 0
            hs["maliyet_oos"] += 1 if v.get("maliyet_yiyor_oos") else 0
        ctx["HS"] = hs
        return ctx

    def isle(self, metin: str, ctx: dict) -> str:
        return self._dugumler(_agac(list(_belirtecler(metin))), ctx)

    def _dugumler(self, dugumler: list, ctx: dict) -> str:
        cikti = []
        for tur, deger in dugumler:
            if tur == "metin":
                cikti.append(deger)
            elif tur == "if":
                for kos, govde in deger["dallar"]:
                    if kosul(kos, ctx):
                        cikti.append(self._dugumler(govde, ctx))
                        break
                else:
                    if deger["degilse"] is not None:
                        cikti.append(self._dugumler(deger["degilse"], ctx))
            else:
                cikti.append(self._yer(deger, ctx))
        return "".join(cikti)

    def _yer(self, s: str, ctx: dict) -> str:
        if s.startswith("?"):
            if not kosul(s[1:], ctx):
                raise SablonHatasi(f"İDDİA TUTMADI: {s[1:].strip()}")
            self.iddia += 1
            return ""
        if s.startswith("="):
            m = re.fullmatch(r'=\s*"([^"]*)"', s)
            if not m:
                raise SablonHatasi(f"sabit tırnaklı yazılır: {s!r}")
            self.sabitler.append(m.group(1))
            return m.group(1)
        if s.startswith("!"):
            # Argümanlar boşlukla ayrılır; çift tırnaklı argüman tek parçadır (tırnak düşer, kesme işareti kalır).
            parca = [a or b for a, b in re.findall(r'"([^"]*)"|(\S+)', s[1:])]
            ad, arg = parca[0], parca[1:]
            if ad not in BLOKLAR:
                raise SablonHatasi(f"bilinmeyen blok: {ad}")
            return BLOKLAR[ad](self, ctx, *arg)
        if "|" not in s:
            raise SablonHatasi(f"biçimsiz yer tutucu: {s!r}")
        yol, bicim = (x.strip() for x in s.rsplit("|", 1))
        self.yer += 1
        if bicim.rstrip("?") == "fiyat":
            v, cift = yol_coz(yol, ctx), ctx.get("CIFT") or ana()
            if v is None:
                raise SablonHatasi(f"ölçülemeyen fiyat: {yol}")
            return sayi(float(v) * NOKTA[cift], HANE[cift])
        return bicimle(yol_coz(yol, ctx), bicim, yol)


# ─────────────────────────────────────────────────────────────── bloklar
def _hucre(v, bicim: str) -> str:
    try:
        return bicimle(v, bicim + "?")
    except SablonHatasi:
        return "—"


def mdx_kacis(s: str) -> str:
    """Üretilen metinde MDX'in sözdizimi sayacağı karakterler: '<' (etiket başlangıcı: "<0,5" derlemeyi
    düşürür), '{' ve '}' (JSX ifadesi). Karakter göndermesine çevrilir; sayfada aynı görünür."""
    return s.replace("<", "&lt;").replace("{", "&#123;").replace("}", "&#125;")


def _tablo(baslik: list[str], satirlar: list[list[str]], hiza: list[str] | None = None) -> str:
    hiza = hiza or ["l"] + ["r"] * (len(baslik) - 1)
    ayrac = ["---:" if h == "r" else ":---" for h in hiza]
    s = ["| " + " | ".join(mdx_kacis(x) for x in baslik) + " |", "| " + " | ".join(ayrac) + " |"]
    s += ["| " + " | ".join(mdx_kacis(x) for x in r) + " |" for r in satirlar]
    return "\n".join(s)


def _ciftler(b: dict) -> list[str]:
    return [c for c in PARITE if (b.get("cift") or {}).get(c)]


def blok_sekil(u: Uretim, ctx: dict, ad: str, *baslik_parca: str) -> str:
    """Figür gömmesi; ad birim şablonunda kısaltılır (ornek → <birim>-ornek). Şekil numarası ders içinde
    sıralıdır. Figür dosyası yoksa üretim düşer: yazılmamış bir figür gömülmez."""
    tam = f"{ctx['BID']}-{ad}" if "BID" in ctx and "-" not in ad else ad
    u.sekil_no += 1
    u.sekiller.append(tam)
    baslik = " ".join(baslik_parca) or tam
    return (f'<GrafikEmbed src="{SEKIL_YOL}/{tam}.html" baslik="{baslik}" no="{u.sekil_no:02d}" '
            f'kaynak="Dukascopy" />')


def _ozet_satirlari(b: dict, d: str) -> list[tuple[str, dict]]:
    sutun = [(PARITE[c], ((b["cift"][c].get("varsayilan") or {}).get(d) or {})) for c in _ciftler(b)]
    havuz = ((b.get("havuz") or {}).get("varsayilan") or {}).get(d)
    if havuz:
        sutun.append(("Havuz", havuz))
    return sutun


def blok_sonuc(u: Uretim, ctx: dict, donem: str = "oos") -> str:
    """Önceden kayıtlı varsayılanın ana sonuç tablosu: dört parite ve havuz, bir dönemde."""
    b = ctx["B"]
    sutun = _ozet_satirlari(b, donem)
    satirlar = [
        ("İşlem", "n", "n"), ("İsabet", "isabet", "yz1"), ("Net beklenti (R)", "beklenti_r", "ra"),
        ("%95 aralığı, alt", "ga_alt", "ra"), ("%95 aralığı, üst", "ga_ust", "ra"),
        ("Brüt beklenti (R)", "brut_r", "ra"), ("Net beklenti (pip)", "beklenti_pip", "p1"),
        ("Sharpe (yıllık)", "sharpe", "sh"),
    ]
    govde = [[ad] + [_hucre(m.get(k), f) for _, m in sutun] for ad, k, f in satirlar]
    return _tablo([""] + [s for s, _ in sutun], govde)


def blok_sonuc_tum(u: Uretim, ctx: dict) -> str:
    """Varsayılanın bütün dönem (2018 →) kısa tablosu. Ön kaydın başlığı varsayılan için bütün dönemi de örneklem
    dışı sayar; hüküm 2024 → penceresinden verilir (şartnamenin örneklem ayrımı), bütün dönemin hükmü bu tabloda."""
    b = ctx["B"]
    sutun = _ozet_satirlari(b, "tum")
    hk = {PARITE[c]: (b["cift"][c].get("varsayilan") or {}).get("hukum_tum") for c in _ciftler(b)}
    satirlar = [("İşlem", "n", "n"), ("Net beklenti (R)", "beklenti_r", "ra"), ("%95 aralığı, alt", "ga_alt", "ra"),
                ("%95 aralığı, üst", "ga_ust", "ra"), ("Brüt beklenti (R)", "brut_r", "ra")]
    govde = [[ad] + [_hucre(m.get(k), f) for _, m in sutun] for ad, k, f in satirlar]
    govde.append(["Hüküm (bütün dönem)"] + [_hucre(hk.get(s), "hukum") if s in hk else "—" for s, _ in sutun])
    return _tablo([""] + [s for s, _ in sutun], govde)


def blok_ayrinti(u: Uretim, ctx: dict, donem: str = "oos") -> str:
    b = ctx["B"]
    sutun = _ozet_satirlari(b, donem)
    birim_satiri = ("R birimi medyanı (pip, girişteki ATR)" if ctx.get("STOPSUZ") else "Stop uzaklığı medyanı (pip)")
    satirlar = [
        ("Ort. kazanç (R)", "ort_kazanc_r", "ra"), ("Ort. kayıp (R)", "ort_kayip_r", "ra"),
        ("Kâr çarpanı (R)", "pf_r", "s2"), ("Kâr çarpanı (pip)", "pf", "s2"),
        ("Azami düşüş (R)", "azami_dusus_r", "s1"),
        ("Ort. süre (dk)", "sure_dk", "s0"), ("MAE medyanı (R)", "mae_r", "ra"), ("MFE medyanı (R)", "mfe_r", "ra"),
        (birim_satiri, "risk_pip", "s1"),
    ]
    govde = [[ad] + [_hucre(m.get(k), f) for _, m in sutun] for ad, k, f in satirlar]
    return _tablo([""] + [s for s, _ in sutun], govde)


def _basabas_hucre(v: dict, son: str = "") -> str:
    """Başabaş kaymanın tablo yazımı (son: "" bütün dönem, "_oos" 2024 →): kesişim (pip) · "sıfırda bile eksi" ·
    "2 pip'te bile artı" (ızgaranın son kademesinde de artı)."""
    k = v.get("basabas_kayma_pip" + son)
    if k is None:
        return "2 pip'te bile artı" if (v.get("oos" if son else "tum") or {}).get("n") else "—"
    if k == 0:
        return "sıfırda bile eksi"
    return "&lt; 0,01" if k < 0.005 else _hucre(k, "s2")


def blok_maliyet(u: Uretim, ctx: dict) -> str:
    """Maliyet merdiveni (örneklem dışı net R), yalnız makas satırı ve iki dönemin başabaşı: dört parite.

    Kademeler dolum başına TEMEL kaymadır; haber penceresindeki dolumlar her kademede ayrıca 1,0 pip haber kayması
    öder. "Yalnız makas" satırında ikisi de sıfırdır: dolumlar yalnız o dakikanın gerçek bid/ask'ından."""
    b = ctx["B"]
    cs = _ciftler(b)
    v_ = {c: (b["cift"][c].get("varsayilan") or {}) for c in cs}
    kademe = sorted({k for c in cs for k in (v_[c].get("maliyet") or {})}, key=float)
    hk = u.O["kunye"]["haber_kayma_pip"]
    govde = [["Yalnız makas"] + [_hucre(((v_[c].get("yalniz_makas") or {}).get("oos") or {}).get("beklenti_r"), "ra")
                                 for c in cs]]
    for k in kademe:
        govde.append([f"{sayi(float(k), 1)} pip"] +
                     [_hucre((((v_[c].get("maliyet") or {}).get(k) or {}).get("oos") or {}).get("beklenti_r"), "ra")
                      for c in cs])
    govde.append(["Başabaş kayma, 2024 → (pip)"] + [_basabas_hucre(v_[c], "_oos") for c in cs])
    govde.append(["Başabaş kayma, bütün dönem (pip)"] + [_basabas_hucre(v_[c]) for c in cs])
    pay = [x for x in ((v_[c].get("haber_payi")) for c in cs) if x is not None and math.isfinite(x)]
    if pay and max(pay) >= 0.005:
        aralik = (yuzde(min(pay), 0) if round(min(pay), 2) == round(max(pay), 2)
                  else f"{yuzde(min(pay), 0)}–{yuzde(max(pay), 0)}")
        pay_ = f" Haber penceresine düşen giriş payı bu kuralda {aralik}."
    else:
        pay_ = " Bu kuralın girişleri haber penceresine düşmüyor." if pay else ""
    return (_tablo(["Dolum başına kayma"] + [PARITE[c] for c in cs], govde) +
            f"\n\n_Örneklem dışı (2024 →) net beklenti, R. Kademeler dolum başına temel kaymadır; haber penceresindeki "
            f"dolumlar her kademede ayrıca {sayi(hk, 1)} pip öder, \"yalnız makas\" satırında o da sıfırdır.{pay_} "
            f"Başabaş: net beklentiyi sıfıra indiren dolum başına kayma._")


#: Saat değerli parametrelerin kısa etiketi: seçilen kombinasyon tek satırda yazılırken "10:00" tek
#: başına okunmaz (son giriş mi, başlangıç mı?).
SAAT_ETIKET = {"son_giris_londra": "son giriş", "son_giris_et": "son giriş", "baslangic_et": "başlangıç",
               "aralik_sonu_londra": "aralık sonu", "cikis_et": "çıkış"}
#: Kombinasyonun tek satırlık yazımında parametrenin kısa adı (okur adı adlar.PARAM'da). Her değer adıyla yazılır:
#: "yok" ya da "60 dk" tek başına okunmaz (stop mu, hedef mi; mum mu, ilk denge mi?).
KOMB_AD = {"stop_yeri": "stop yeri", "hedef": "hedef", "ib_pencere": "ilk denge", "referans": "referans",
           "gecerlilik": "geçerlilik", "seans": "seans", "sure": "sıkışma", "baslangic": "geçerlilik",
           "stop_kurali": "stop", "seviye": "seviye", "pencere": "pencere", "capa": "VWAP çapası", "n": "trend",
           "tur": "tür", "gecikme_mum": "gecikme", "tutma_mum": "tutma", "giris_mumu": "giriş mumu",
           "giris": "giriş", "on_mum": "haber öncesi aralık", "geri_cekilme": "geri çekilme"}
MUM_PARAM = {"gecerlilik", "sure", "pencere", "n", "on_mum", "gecikme_mum", "tutma_mum"}
STOP_TURU = {"sert": "sert stop", "kapanis": "kapanış stopu", "yok": "stop yok"}
#: Ön kaydın "yalnız dönüş" dediği parametreler (onkayit.toml [fiks]): fiksing momentumunda kural onları taşımaz;
#: birim onları kodun istediği sabit değerle (0, 1) koşar, okura yazılmaz.
YALNIZ_TUR = {("fiks", "gecikme_mum"): "donus", ("fiks", "tutma_mum"): "donus"}


def _esik_birimi(aile: str) -> str:
    """'k' parametresinin birimi aileye göre: VWAP bandında σ, haber fade'inde ilk mum hareketinin ATR katı."""
    return "σ" if aile == "vwap_donus" else "×ATR"


def _gorunur(k: str, p: dict, on: dict, aile: str) -> bool:
    """Bir parametre okura yazılır mı: ön kaydın ızgarasında olmalı (fiksing ve momentumda 'hedef' kodun eklediği
    bir yer tutucudur) ve kuralın bu türüne ait olmalı."""
    if k not in (on.get("izgara") or {}):
        return False
    tur = YALNIZ_TUR.get((aile, k))
    return tur is None or p.get("tur") == tur


def _komb_deger(k: str, x, aile: str) -> str:
    if k == "tf":
        return f"{x} dk"
    if k == "stop_turu":
        return STOP_TURU.get(str(x), str(x))
    if k == "ib_pencere":
        return "ilk denge tek mum" if str(x) == "tf" else f"ilk denge {x} dk"
    if k in SAAT_ETIKET:
        return f"{SAAT_ETIKET[k]} {x}"
    if k in MUM_PARAM:
        return f"{KOMB_AD[k]} {x} mum"
    if k == "k":
        return f"eşik {sayi(float(x), 1)}{_esik_birimi(aile)}"
    if k == "geri_cekilme":
        return f"geri çekilme {yuzde(float(x), 1)}"
    if k in ("yon",):
        return _deger_yaz(x, k)
    return f"{KOMB_AD.get(k, adlar.PARAM.get(k, k))} {_deger_yaz(x, k)}"


def kombinasyon_yaz(p: dict, on: dict, sabit: dict | None = None, aile: str = "") -> str:
    """Bir kombinasyonun okur yazımı, önceden kaydın ızgara sırasıyla (zaman dilimi önce). Birimin sabitlediği
    boyutlar (ör. başarısız kırılımda seviye) ve kuralın taşımadığı parametreler yazılmaz."""
    sira = list((on.get("izgara") or {}).keys())
    anahtar = sorted(p, key=lambda k: (sira.index(k) if k in sira else 99, k))
    return " · ".join(_komb_deger(k, p[k], aile) for k in anahtar
                      if k not in (sabit or {}) and _gorunur(k, p, on, aile))


def _r_pip_ayrisan(b: dict, tur: str) -> list[tuple[str, dict]]:
    """Örneklem dışında net R ortalaması ile net pip ortalamasının işareti ayrışan pariteler (tur: varsayilan |
    secilen). R ortalaması her işlemi riskine göre büyüklükler, pip ortalaması aynı büyüklükte işlem yapanın
    sonucudur; işaretleri ayrıştığında R'nin işaretini stopu dar işlemler belirliyor demektir."""
    out = []
    for c in _ciftler(b):
        o = ((b["cift"][c].get(tur) or {}).get("oos")) or {}
        r, p = o.get("beklenti_r"), o.get("beklenti_pip")
        if r is None or p is None:
            continue
        if (r > 0) != (p > 0):
            out.append((c, o))
    return out


def _r_pip_cumle(b: dict, tur: str, ozne: str) -> str:
    """İşareti ayrışan paritelerin cümlesi; ayrışma yoksa boş."""
    ay = _r_pip_ayrisan(b, tur)
    if not ay:
        return ""
    # Sıfıra çok yakın bir pip ortalaması tek haneyle "0,0" okunur ve ayrışmayı göstermez: iki hane.
    parca = [f"{PARITE[c]} {_hucre(o.get('beklenti_r'), 'ra')} R ama "
             f"{_hucre(o.get('beklenti_pip'), 'r' if abs(o.get('beklenti_pip')) < 0.05 else 'p1')} pip "
             f"(pip ortalamasının %95 aralığı {_hucre(o.get('ga_pip_alt'), 'p1')} / {_hucre(o.get('ga_pip_ust'), 'p1')})"
             for c, o in ay]
    return (f"{ozne} örneklem dışında R ile pipin işareti ayrışıyor: {'; '.join(parca)}. R'nin işaretini stopu dar "
            f"işlemler belirliyor (giriş dersi, \"R ve pip\"); hüküm ön kayıt gereği R'den verilir.")


def _yillar_yaz(yillar: list) -> str:
    """Ardışık yılları aralıkla yazar: [2020, 2021, 2022, 2024] → "2020–2022, 2024"."""
    ys = sorted(int(y) for y in yillar)
    if not ys:
        return "—"
    out, bas, son = [], ys[0], ys[0]
    for y in ys[1:] + [None]:
        if y is not None and y == son + 1:
            son = y
            continue
        out.append(str(bas) if bas == son else f"{bas}–{son}")
        if y is not None:
            bas = son = y
    return ", ".join(out)


def blok_secim(u: Uretim, ctx: dict) -> str:
    """Izgaradan örneklem içinde seçilen kombinasyon, iki örneklemde sonucu (R ve pip) ve deflated Sharpe."""
    b = ctx["B"]
    on = u.ON.get(b.get("aile")) or {}
    govde = []
    for c in _ciftler(b):
        v = b["cift"][c]
        s = v.get("secilen") or {}
        p = v.get("secilen_p") or {}
        ic, dis = s.get("is") or {}, s.get("oos") or {}
        govde.append([PARITE[c], kombinasyon_yaz(p, on, b.get("sabit"), b.get("aile") or "") or "—",
                      _hucre(ic.get("beklenti_r"), "ra"), _hucre(ic.get("beklenti_pip"), "p1"),
                      _hucre(dis.get("beklenti_r"), "ra"), _hucre(dis.get("beklenti_pip"), "p1"),
                      _hucre((s.get("dsr") or {}).get("dsr"), "s2"), _hucre(s.get("hukum"), "hukum")])
    tablo = _tablo(["Parite", "Seçilen", "İçi (R)", "İçi (pip)", "Dışı (R)", "Dışı (pip)", "DSR", "Hüküm"], govde,
                   ["l", "l", "r", "r", "r", "r", "r", "l"])
    not_ = _r_pip_cumle(b, "secilen", "Seçilen kombinasyonlarda")
    return tablo + (f"\n\n{not_}" if not_ else "")


def blok_wf(u: Uretim, ctx: dict) -> str:
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        wf = b["cift"][c].get("walk_forward") or {}
        w = wf.get("ozet") or {}
        govde.append([PARITE[c], _yillar_yaz(wf.get("sinanan_yillar") or []), _hucre(w.get("n"), "n"),
                      _hucre(w.get("beklenti_r"), "ra"), _hucre(w.get("ga_alt"), "ra"), _hucre(w.get("sharpe"), "sh")])
    return _tablo(["Parite", "Sınanan yıllar", "İşlem", "Net R", "%95 alt", "Sharpe"], govde,
                  ["l", "l", "r", "r", "r", "r"])


def blok_rejim(u: Uretim, ctx: dict) -> str:
    """Yıl ve oynaklık tercili: dört paritenin işlem başına net R'si (bütün dönem)."""
    b = ctx["B"]
    cs = _ciftler(b)
    yillar = sorted({y for c in cs for y in ((b["cift"][c].get("varsayilan") or {}).get("yil") or {})})
    govde = [[y] + [_hucre(((((b["cift"][c].get("varsayilan") or {}).get("yil") or {}).get(y) or {}).get("beklenti_r")),
                           "ra") for c in cs] for y in yillar]
    for t in ("düşük", "orta", "yüksek"):
        govde.append([f"oynaklık {t}"] + [_hucre((((b["cift"][c].get("varsayilan") or {}).get("oynaklik") or {})
                                                   .get(t) or {}).get("beklenti_r"), "ra") for c in cs])
    return (_tablo([""] + [PARITE[c] for c in cs], govde) +
            "\n\n_Önceden kayıtlı varsayılan, bütün dönem (2018 → 2026), işlem başına net R. Oynaklık tercili: önceki "
            "günlerin ATR(14)'ünün son 252 işlem günündeki yüzdeliği (alt, orta, üst üçte bir); işlem gününü "
            "içermez._")


#: Izgarada birim için tanımsız bileşimlerin gerekçesi (kombinasyon sayısı değer sayılarının çarpımından küçükse).
IZGARA_DISI = {"nyib": "60 dakikalık mumda \"tek mum\" ilk denge ile \"60 dk\" ilk denge aynı penceredir ve bir kez "
                       "sayılır"}


def blok_kural(u: Uretim, ctx: dict) -> str:
    """Birimin ızgarası ve varsayılanı (okur adlarıyla). Değerler birimin GERÇEKTEN koşulan kombinasyonlarından gelir:
    birimin sabitlediği boyut (başarısız kırılımda seviye, NY IB'de başlangıç, fiksingde tür) tek değerle görünür,
    kuralın taşımadığı parametre (fiksing momentumunda gecikme ve tutma) yazılmaz."""
    b = ctx["B"]
    aile = b.get("aile") or ""
    on = u.ON.get(aile) or {}
    izgara = on.get("izgara") or {}
    gercek = b.get("izgara_deger") or {}
    v = b.get("varsayilan") or {}
    onv = b.get("onkayit_varsayilan") or {}
    sabit = b.get("sabit") or {}
    govde, carpim = [], 1
    for k in izgara:
        if not _gorunur(k, v, on, aile):
            continue
        degerler = gercek.get(k) or izgara[k]
        carpim *= len(degerler)
        izg = ", ".join(_deger_yaz(x, k) for x in degerler) + (" (bu birimde sabit)" if k in sabit else "")
        vs = _deger_yaz(v.get(k), k) if k in v else "—"
        if k in onv and onv[k] != v.get(k):
            vs += f" (ön kayıtta {_deger_yaz(onv[k], k)})"
        govde.append([adlar.PARAM.get(k, k) if k != "k" else f"eşik ({_esik_birimi(aile)})", izg, vs])
    n = int(b.get("kombinasyon") or 0)
    not_ = f"_Izgara: {sayi(n, 0)} kombinasyon"
    if n and carpim > n and aile in IZGARA_DISI:
        not_ += f" ({sayi(carpim, 0)} bileşimden; {IZGARA_DISI[aile]})"
    return _tablo(["Parametre", "Izgara", "Varsayılan"], govde, ["l", "l", "l"]) + "\n\n" + not_ + "._"


def _deger_yaz(x, k: str = "") -> str:
    if x is None:
        return "—"
    if k == "tf" or (isinstance(x, int) and k in ("tf",)):
        return f"{x} dk"
    if k == "ib_pencere" and str(x) == "60":
        return "60 dk"
    if k == "geri_cekilme" and isinstance(x, float):
        return yuzde(x, 1)
    if isinstance(x, float):
        return sayi(x, 3 if x != round(x, 1) else 1)
    return adlar.DEGER.get(str(x), str(x))


SAYI_AD = {1: "bir", 2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz",
           10: "on"}
GUN_ADI = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]


def _hukum_hucre(v: dict, d: str, anahtar: str) -> str:
    """Hüküm ve işlem başına net R ("zayıf · +0,18"); az işlemde işlem sayısı da ("zayıf · +0,35 · 12 işlem")."""
    if not v:
        return "—"
    o = v.get(d) or {}
    s = f"{adlar.HUKUM.get(v.get(anahtar) or 'olculemedi')} · {_hucre(o.get('beklenti_r'), 'ra')}"
    if (v.get("az_islem") or {}).get(d):
        s += f" · {sayi(o.get('n') or 0, 0)} işlem"
    return s


def blok_hukum(u: Uretim, ctx: dict) -> str:
    """Parite başına hüküm: varsayılan iki dönemde (2024 → birincil, bütün dönem yan sütun), ızgaradan seçilen,
    rastgele yön yüzdeliği ve maliyet bayrağı (iki dönem)."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        v = b["cift"][c].get("varsayilan") or {}
        s = b["cift"][c].get("secilen") or {}
        ras = (v.get("rastgele") or {}).get("oos") or {}
        n = (v.get("oos") or {}).get("n") or 0
        yz = ras.get("yuzdelik")
        rastgele = (_hucre(yz, "s1") if yz is not None and math.isfinite(yz)
                    else f"yapılmadı ({sayi(n, 0)} işlem)")
        maliyet = f"{'evet' if v.get('maliyet_yiyor') else 'hayır'} · {'evet' if v.get('maliyet_yiyor_oos') else 'hayır'}"
        govde.append([PARITE[c], _hukum_hucre(v, "oos", "hukum"), _hukum_hucre(v, "tum", "hukum_tum"),
                      _hukum_hucre(s, "oos", "hukum"), rastgele, maliyet])
    return (_tablo(["Parite", "Varsayılan, 2024 →", "Varsayılan, bütün dönem", "Seçilen, 2024 →",
                    "Rastgele yüzdelik, 2024 →", "Maliyet yiyor (bütün · 2024 →)"], govde,
                   ["l", "l", "l", "l", "r", "l"]) +
            "\n\n_Hücrede hüküm ve işlem başına net R; tanımlar giriş dersinde (\"Hüküm\")._")


def _kosul_ad(k: dict) -> str:
    return adlar.KOSUL.get(k["degisken"], k["degisken"])


def _kova_yaz(kovalar: list) -> str:
    ko = adlar.KOVA_OKUMA
    sira = sorted((str(x) for x in kovalar), key=lambda k: ko.index(k) if k in ko else 50)
    return ", ".join(sira) or "—"


def blok_kosul_ozet(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Koşul değişkenlerinin hükmü (bir paritede): tutan, tutmayan, seçim kurulamayan. Tutanlar kovasıyla, örneklem
    dışı işlem sayısı ve isabetiyle; aynı ölçünün iki adı bir kez sayılır; ters seçimin sonucu yanında."""
    cift = cift or ana()
    b = ctx["B"]
    v = ((b.get("cift") or {}).get(cift) or {}).get("varsayilan") or {}
    ks = v.get("kosul") or []
    if not ks:
        return f"_{PARITE[cift]}: koşul analizi için yeterli işlem yok._"
    es = [k for k in ks if k.get("hukum") == "esdeger"]
    ks = [k for k in ks if k.get("hukum") != "esdeger"]
    tut = [k for k in ks if k.get("hukum") == "tuttu"]
    tutma = [k for k in ks if k.get("hukum") == "tutmadi"]
    sec = [k for k in ks if k.get("hukum") == "secilmedi"]
    hep = [k for k in ks if k.get("hukum") == "hepsi"]
    parca = [f"{sayi(len(tut), 0)} tuttu", f"{sayi(len(tutma), 0)} tutmadı"]
    if sec:
        parca.append(f"{sayi(len(sec), 0)} değişkende hiçbir kova seçilmedi (örneklem içinde en az "
                     f"{u.ON['kosul']['asgari_kova_islem']} işlemle koşulsuz ortalamanın üstünde kalan kova yok)")
    if hep:
        parca.append(f"{sayi(len(hep), 0)} değişkende bütün kovalar seçildi, sınanacak tamamlayan kalmadı")
    satir = [f"{PARITE[cift]}, sınanan {sayi(len(ks), 0)} değişken: {', '.join(parca)}."]
    if es:
        satir[0] += " " + " ".join(f"{_kosul_ad(k)} bu kuralda {adlar.KOSUL.get(k['esdeger'], k['esdeger'])} ile aynı "
                                   f"ölçüdür ve bir kez sayıldı." for k in es)
    for k in tut:
        satir.append(f"- {_kosul_ad(k)}: seçilen kova {_kova_yaz(k.get('secilen') or [])}. Örneklem dışında seçilen "
                     f"kovalarda {sayi(k.get('oos_secilen_n') or 0, 0)} işlem, {_hucre(k.get('oos_secilen_r'), 'ra')} R, "
                     f"isabet {_hucre(k.get('oos_secilen_isabet'), 'yz1')}; tamamlayanında "
                     f"{sayi(k.get('oos_tamamlayan_n') or 0, 0)} işlem, {_hucre(k.get('oos_tamamlayan_r'), 'ra')} R, "
                     f"isabet {_hucre(k.get('oos_tamamlayan_isabet'), 'yz1')}.")
    if tutma:
        satir.append(f"- Tutmayanlar: {', '.join(_kosul_ad(k) for k in tutma)}.")
    ters = [k for k in ks if (k.get("ters_secim") or {}).get("hukum") in ("tuttu", "tutmadi")]
    ters_tut = [k for k in ters if k["ters_secim"]["hukum"] == "tuttu"]
    if ters:
        satir.append(f"- Ters seçim (örneklem içinde koşulsuz ortalamanın altında kalan kovalar seçilseydi): aynı ölçüt "
                     f"{sayi(len(ters), 0)} değişkenin {sayi(len(ters_tut), 0)} tanesinde tutardı"
                     + (f" ({', '.join(_kosul_ad(k) for k in ters_tut)})" if ters_tut else "") +
                     ". Kova farkları yalnız gürültüyse iki seçim aynı sıklıkla tutar.")
    return "\n".join(satir)


def _kosul_parite_durumu(ks_ana: dict, ks_c: dict) -> str:
    """Ana paritede tutan bir değişkenin başka paritedeki durumu: aynı kovayla tuttu · başka kovayla tuttu · tutmadı ·
    seçim kurulamadı."""
    h = ks_c.get("hukum")
    if h == "tuttu":
        if set(ks_c.get("secilen") or []) == set(ks_ana.get("secilen") or []):
            return "aynı kovayla tuttu"
        return f"başka kovayla tuttu ({_kova_yaz(ks_c.get('secilen') or [])})"
    return {"tutmadi": "tutmadı", "secilmedi": "kova seçilmedi", "hepsi": "bütün kovalar seçildi",
            "esdeger": "aynı ölçü"}.get(h, "—")


def _kosul_tablosu(b: dict) -> dict:
    """Parite → değişken → koşul kaydı (varsayılan)."""
    return {c: {x["degisken"]: x for x in ((b["cift"][c].get("varsayilan") or {}).get("kosul") or [])}
            for c in _ciftler(b)}


def kosul_adaylari(b: dict) -> list[dict]:
    """Kontrol listesinin "Ne zaman" adayları: en az İKİ paritede AYNI kovayla tutan değişkenler. Bir paritede tutan
    koşul şansla da tutar; aynı kovanın başka bir paritede de örneklem dışında aynı yönde durması en az ikinci bir
    gözlemdir. Kayıt: değişken, kova ve o kovayla tutan pariteler (kayıtlarıyla)."""
    tab = _kosul_tablosu(b)
    grup: dict = {}
    for c, ks in tab.items():
        for ad, x in ks.items():
            if x.get("hukum") == "tuttu":
                grup.setdefault((ad, frozenset(x.get("secilen") or [])), []).append((c, x))
    sira = list(adlar.KOSUL)
    out = [{"degisken": ad, "kova": sorted(kv), "pariteler": ps} for (ad, kv), ps in grup.items() if len(ps) >= 2]
    return sorted(out, key=lambda a: (sira.index(a["degisken"]) if a["degisken"] in sira else 99, a["kova"]))


def blok_kosul_tek(u: Uretim, ctx: dict, degisken: str) -> str:
    """Tek bir koşul değişkeninin bütün paritelerdeki sonucu: hüküm, seçilen kova, seçilenin ve öbür kovaların örneklem
    dışı R'si. Şablonun "bu kuralın doğal koşulu" cümlesi bir yönü İMA ETMEZ; yönü ölçüm söyler (bu blok)."""
    if degisken not in adlar.KOSUL:
        raise SablonHatasi(f"kosul_tek: bilinmeyen değişken: {degisken}")
    b = ctx["B"]
    tab = _kosul_tablosu(b)
    parca = []
    for c in _ciftler(b):
        x = tab[c].get(degisken)
        if (x or {}).get("hukum") == "esdeger" and x.get("esdeger") in tab[c]:
            x = tab[c][x["esdeger"]]          # aynı ölçünün ilk adı: sonuç onda durur
        h = (x or {}).get("hukum")
        if h in ("tuttu", "tutmadi"):
            parca.append(f"{PARITE[c]} {'tuttu' if h == 'tuttu' else 'tutmadı'} (seçilen {_kova_yaz(x.get('secilen') or [])}: "
                         f"örneklem dışında {_hucre(x.get('oos_secilen_r'), 'ra')} R, "
                         f"{sayi(x.get('oos_secilen_n') or 0, 0)} işlem; öbür kovalar "
                         f"{_hucre(x.get('oos_tamamlayan_r'), 'ra')} R)")
        else:
            parca.append(f"{PARITE[c]} " + {"secilmedi": "kova seçilmedi", "hepsi": "bütün kovalar seçildi",
                                             "esdeger": "aynı ölçü"}.get(h, "ölçülmedi"))
    return "; ".join(parca)


ORNEK_AD = {"kazanan": "Kazanan", "kaybeden": "Kaybeden", "tuzak": "Tuzak"}


def fiyat_yaz(v_nokta: float, cift: str) -> str:
    """Nokta cinsinden fiyatın okur yazımı. Orta fiyat ve yarım makas yarım nokta taşıyabilir: o zaman bir hane fazla
    yazılır, böylece okurun basılan fiyatlardan yaptığı çıkarma kaydın riskini birebir verir."""
    x = float(v_nokta)
    hane = HANE[cift] + (0 if abs(x - round(x)) < 1e-6 else 1)
    return sayi(x * NOKTA[cift], hane)


def _pip(v: float) -> str:
    """Pip yazımı: kayıt 0,05 pip çözünürlüğündedir (yarım nokta); ikinci hane yalnız gerektiğinde."""
    return sayi(v, 1 if abs(v * 10 - round(v * 10)) < 1e-6 else 2)


def _nokta_pip(cift: str) -> float:
    return PIP[cift] / NOKTA[cift]


def _gun_adi(g: str) -> str:
    from datetime import date as _d
    y, a, d = (int(p) for p in g.split("-"))
    return GUN_ADI[_d(y, a, d).weekday()]


def _sinyal_yaz(i: dict, tf: int) -> str:
    """Sinyal mumunun TSİ aralığı ve girişin saati (kayıtta sinyal_t sinyal mumunun KAPANIŞIDIR)."""
    if i.get("sinyal_t") is None:
        return f"giriş {saat_tsi(i['giris_t'])} TSİ"
    st = int(i["sinyal_t"])
    s = f"sinyal mumu {saat_tsi(st - 60 * tf)}–{saat_tsi(st)} TSİ"
    return s + ("; giriş mum kapanınca, sonraki dakikanın açılışında" if st == int(i["giris_t"])
                else f"; giriş {saat_tsi(i['giris_t'])} TSİ'de")


def blok_ornek(u: Uretim, ctx: dict) -> str:
    """Örnek günlerin anlatımı: figürdeki üç işlemin (kazanan, kaybeden, tuzak) saatleri, fiyatları ve sonucu, ana
    paritede. Seçim kuralı giriş dersinde; burada yalnız işlemler."""
    c = ana()
    e = ((ctx["B"].get("cift") or {}).get(c)) or {}
    stopsuz = ctx.get("STOPSUZ")
    satir = []
    for x in e.get("ornek") or []:
        i = x["islem"]
        g = x["gun"]
        yon = "alış" if i["yon"] > 0 else "satış"
        bas = f"{ORNEK_AD.get(x['etiket'], x['etiket'])}" + (" (yedek tanım)" if x.get("secim") == "yedek" else "")
        parca = [f"**{bas}** ({tarih_uzun(g)}, {_gun_adi(g)}; {x['tf']} dk mum): {yon}."]
        if i.get("olay"):
            parca.append(f"Olay: {adlar.OLAY.get(i['olay'], i['olay'])}" +
                         (f", {saat_tsi(i['olay_t'])} TSİ." if i.get("olay_t") else "."))
        sv = _sinyal_yaz(i, int(x["tf"]))
        parca.append(sv[0].upper() + sv[1:] + f", {fiyat_yaz(i['giris_f'], c)} ({'ask' if i['yon'] > 0 else 'bid'}, "
                     f"kayma dahil)")
        if stopsuz or i.get("stop") is None:
            parca[-1] += f"; stop yok, R birimi girişteki ATR: {_pip(i['R_pip'])} pip"
        else:
            parca[-1] += f"; stop {fiyat_yaz(i['stop'], c)} ({_pip(i['R_pip'])} pip)"
        if i.get("hedef") is not None:
            parca[-1] += f"; hedef {fiyat_yaz(i['hedef'], c)}"
        parca[-1] += "."
        parca.append(f"Çıkış {saat_tsi(i['cikis_t'])} TSİ'de {fiyat_yaz(i['cikis_f'], c)}, "
                     f"{adlar.neden_ad(i, u.O['kunye']['gun_sonu_et'])}: {sayi(i['r'], 2, arti=True)} R "
                     f"({sayi(i['pnl_pip'], 1, arti=True)} pip, maliyet dahil). İşlem boyunca en kötü "
                     f"{sayi(i['mae_r'], 2, arti=True)} R, en iyi {sayi(i['mfe_r'], 2, arti=True)} R.")
        satir.append("- " + " ".join(parca))
    return "\n".join(satir) if satir else "_Örneklem dışında işlem yok._"


def blok_zaman(u: Uretim, ctx: dict) -> str:
    """Olayların TSİ saati, dört saat rejiminde (temsilci günler)."""
    z = u.O["zaman"]
    rejimler = z["tablo"]
    olaylar = z.get("olay_sira") or [k for k in rejimler[0] if k not in ("gun", "londra_ny", "rejim")]
    bas = ["Olay"] + [z["rejim_adi"][r["rejim"]].split(" (")[0] + f" ({tarih(r['gun'])[:5]})" for r in rejimler]
    govde = [[o] + [r.get(o, "—") for r in rejimler] for o in olaylar]
    govde.append(["Londra–New York farkı (saat)"] + [str(r["londra_ny"]) for r in rejimler])
    return _tablo(bas, govde)


def blok_dst(u: Uretim, ctx: dict) -> str:
    """Saat değişimi ara dönemleri (Londra–New York farkı 4 saat), yıl yıl."""
    z = u.O["zaman"]
    govde = []
    for y, donemler in sorted(z["ara_donem"].items()):
        govde.append([y] + ["; ".join(f"{tarih(d['ilk'])[:5]}–{tarih(d['son'])[:5]}" for d in donemler)])
    return _tablo(["Yıl", "Ara dönemler (Londra–NY farkı 4 saat)"], govde, ["l", "l"])


def _maliyet_okuma(u: Uretim, v: dict, d: str) -> str:
    """Bir dönemin maliyet okuması (d: tum | oos), brüte bağlı. Sıra: brüt artı değil → yalnız makas bile eksi →
    haber kayması eksiye çeviriyor → başabaş kayma (ya da ızgaranın sonunda da artı)."""
    m = v.get(d) or {}
    brut, net = m.get("brut_r"), m.get("beklenti_r")
    if brut is None or net is None or not m.get("n"):
        return "ölçülemedi (işlem yok)"
    ym = ((v.get("yalniz_makas") or {}).get(d) or {}).get("beklenti_r")
    m0 = (((v.get("maliyet") or {}).get("0.0") or {}).get(d) or {}).get("beklenti_r")
    bb = v.get("basabas_kayma_pip" + ("" if d == "tum" else "_oos"))
    hk = u.O["kunye"]["haber_kayma_pip"]
    tk = u.O["kunye"]["temel_kayma_pip"]
    haber = (v.get("haber_payi") or 0) >= 0.005
    if brut <= 0:
        return f"maliyetten önce de artı değil (brüt {_hucre(brut, 'ra')} R): hiçbir yürütme bu kuralı artıya çevirmez"
    if ym is not None and ym <= 0:
        return (f"brüt artı ({_hucre(brut, 'ra')} R) ama kayma hiç yokken, yalnız gerçek makasla bile eksi "
                f"({_hucre(ym, 'ra')} R): kenar varsa bu makastan küçük")
    if m0 is not None and m0 <= 0:
        return (f"yalnız makasla artı ({_hucre(ym, 'ra')} R); temel kayma sıfırken bile haber penceresindeki "
                f"{sayi(hk, 1)} pip kayma sonucu eksiye çeviriyor ({_hucre(m0, 'ra')} R)")
    if bb is None:
        return f"dolum başına 2 pip kaymada bile artı ({sayi(tk, 1)} pip kaymada net {_hucre(net, 'ra')} R)"
    return (f"makasın üstüne dolum başına {_hucre(bb, 's2')} pip kayma"
            + (f" (haber penceresinde ayrıca {sayi(hk, 1)} pip)" if haber else "") +
            f" net beklentiyi sıfıra indiriyor ({sayi(tk, 1)} pip kaymada net {_hucre(net, 'ra')} R)")


def blok_basabas(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Kontrol listesinin maliyet maddesi (ana parite): iki dönemde, brüte bağlı okuma."""
    cift = cift or ana()
    v = (((ctx["B"].get("cift") or {}).get(cift) or {}).get("varsayilan")) or {}
    return (f"{PARITE[cift]}, örneklem dışı (2024 →): {_maliyet_okuma(u, v, 'oos')}. Bütün dönem: "
            f"{_maliyet_okuma(u, v, 'tum')}.")


def _isaret_say(degerler: list) -> tuple[int, int]:
    d = [x for x in degerler if x is not None]
    return sum(1 for x in d if x > 0), len(d)


def blok_oos_cumle(u: Uretim, ctx: dict) -> str:
    """Örneklem dışının tek paragraflık özeti: havuz ve parite parite net R, aralık, işaret sayımı, brüt."""
    b = ctx["B"]
    h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
    cs = _ciftler(b)
    pr = [((b["cift"][c].get("varsayilan") or {}).get("oos") or {}) for c in cs]
    arti, n = _isaret_say([p.get("beklenti_r") for p in pr])
    k = u.O["kunye"]
    parca = [f"Örneklem dışında ({tarih(k['dis_baslangic'])} → {tarih(k['bitis'])}) önceden kayıtlı varsayılanın"]
    if h.get("n"):
        parca.append(f"{len(cs)} paritedeki {sayi(h['n'], 0)} işleminin net ortalaması işlem başına "
                     f"{_hucre(h.get('beklenti_r'), 'ra')} R (%95 aralığı {_hucre(h.get('ga_alt'), 'ra')} / "
                     f"{_hucre(h.get('ga_ust'), 'ra')}, gün kümeli; isabet {_hucre(h.get('isabet'), 'yz1')}).")
    else:
        parca.append("örneklem dışında hiç işlemi yok.")
    if n:
        ayri = "; ".join(f"{PARITE[c]} {_hucre(p.get('beklenti_r'), 'ra')}" for c, p in zip(cs, pr))
        parca.append(f"Parite parite: {ayri} (artı olan parite: {arti} / {n}).")
    brut, net = h.get("brut_r"), h.get("beklenti_r")
    if brut is not None and net is not None:
        if brut > 0:
            parca.append(f"Maliyetten önce (orta fiyattan orta fiyata) işlem başına {_hucre(brut, 'ra')} R; gerçek "
                         f"makas ve kayma bunun {sayi(brut - net, 2)} R'sini götürüyor"
                         + (" ve sonucu eksiye çeviriyor." if net <= 0 else "."))
        else:
            parca.append(f"Maliyetten önce de artı değil (orta fiyattan orta fiyata işlem başına "
                         f"{_hucre(brut, 'ra')} R); makas ve kayma işlem başına ayrıca {sayi(brut - net, 2)} R.")
    return " ".join(parca)


def blok_rastgele_cumle(u: Uretim, ctx: dict) -> str:
    """Rastgele yön sınaması (tanım giriş dersinde): dört paritenin yüzdeliği; sınama yapılamayan paritede sebebi."""
    b = ctx["B"]
    var, yok = [], []
    for c in _ciftler(b):
        v = b["cift"][c].get("varsayilan") or {}
        r = ((v.get("rastgele") or {}).get("oos") or {})
        if r.get("yuzdelik") is not None and math.isfinite(r["yuzdelik"]):
            var.append(f"{PARITE[c]} {sayi(r['yuzdelik'], 1)}")
        else:
            yok.append(f"{PARITE[c]} ({sayi((v.get('oos') or {}).get('n') or 0, 0)} işlem)")
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    s = ""
    if var:
        s = (f"Örneklem dışı sonucun, yönü yazı turayla seçen {sayi(u.ON.get('hukum', {}).get('rastgele_tekrar', 1000), 0)} "
             f"denemenin dağılımındaki yüzdeliği (hükmün şartı ≥ {esik}): {' · '.join(var)}.")
    if yok:
        s += (" " if s else "") + (f"Sınama yapılmadı: {', '.join(yok)}; örneklem dışında en az 20 işlem ister.")
    return s


def blok_dsr_cumle(u: Uretim, ctx: dict) -> str:
    """Izgaradan seçimin çoklu sınama düzeltmesi (ana parite): deneme sayısı, en iyinin Sharpe'ı, iki eşik ve
    deflated Sharpe olasılığı. En iyi bile eksiyse soru sorulmaz: açıklanacak bir artı yoktur."""
    c = ana()
    b = ctx["B"]
    e = ((b.get("cift") or {}).get(c) or {}).get("secilen") or {}
    d = e.get("dsr") or {}
    if not d.get("n_deneme"):
        return ""
    komb = int(b.get("kombinasyon") or 0)
    s = f"{PARITE[c]}'de ızgaranın {sayi(komb, 0)} kombinasyonu örneklem içinde denendi"
    if komb and d["n_deneme"] < komb:
        s += (f"; {sayi(komb - d['n_deneme'], 0)} tanesi hiç işlem açmadığı için Sharpe'ı tanımsız, deflated Sharpe "
              f"{sayi(d['n_deneme'], 0)} deneme üzerinden")
    s += "."
    sr = d.get("sr_yillik")
    if sr is None:
        return s
    if sr <= 0:
        return (s + f" Seçilen en iyi kombinasyonun bile örneklem içi yıllık Sharpe'ı {_hucre(sr, 'sh')}: deflated "
                f"Sharpe'ın sorusu (en iyi sonuç şansla açıklanır mı) burada sorulmaz, açıklanacak bir artı yok.")
    return (s + f" En iyisinin örneklem içi yıllık Sharpe'ı {_hucre(sr, 'sh')}. Bu kadar denemede salt şansın "
            f"üreteceği beklenen en yüksek değer {_hucre(d.get('sr0_gurultu_yillik'), 's2')}; denemelerin kendi Sharpe "
            f"yayılımından kurulan eşik (Bailey–López de Prado) {_hucre(d.get('sr0_yillik'), 's2')}. Deflated Sharpe "
            f"olasılığı birincisine göre {_hucre(d.get('dsr_gurultu'), 's2')}, ikincisine göre "
            f"{_hucre(d.get('dsr'), 's2')} (0,95'in altı: seçim şansla açıklanabilir).")


def blok_wf_cumle(u: Uretim, ctx: dict) -> str:
    b = ctx["B"]
    satir = []
    for c in _ciftler(b):
        wf = b["cift"][c].get("walk_forward") or {}
        w = wf.get("ozet") or {}
        if w.get("n"):
            satir.append(f"{PARITE[c]} {_hucre(w.get('beklenti_r'), 'ra')} R ({sayi(w['n'], 0)} işlem; "
                         f"{_yillar_yaz(wf.get('sinanan_yillar') or [])})")
    if not satir:
        return ""
    return ("Yürüyen pencere (her yıl yalnız önceki yılların verisiyle seçip o yılda sınamak; seçim şartını geçen "
            "kombinasyon çıkmayan yıl sınanmaz): " + "; ".join(satir) + ".")


def blok_rejim_cumle(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Yıl ve oynaklık tercilinin betimleyici özeti (bir parite, bütün dönem). İki hanede eşit yıllar üç haneyle."""
    cift = cift or ana()
    v = (((ctx["B"].get("cift") or {}).get(cift) or {}).get("varsayilan")) or {}
    yil = {y: x.get("beklenti_r") for y, x in (v.get("yil") or {}).items() if x.get("beklenti_r") is not None}
    terc = {t: (x or {}).get("beklenti_r") for t, x in (v.get("oynaklik") or {}).items()}
    if not yil:
        return ""
    arti = sum(1 for x in yil.values() if x > 0)
    eniyi, enkotu = max(yil, key=yil.get), min(yil, key=yil.get)
    iki = {y: round(x, 2) for y, x in yil.items()}
    es_iyi = [y for y in yil if y != eniyi and iki[y] == iki[eniyi]]
    es_kotu = [y for y in yil if y != enkotu and iki[y] == iki[enkotu]]
    b_ = "r3" if (es_iyi or es_kotu) else "ra"
    s = (f"{PARITE[cift]} için, bütün dönemde, artı yıl: {arti} / {len(yil)}; en iyi yıl {eniyi} "
         f"({_hucre(yil[eniyi], b_)} R)" + (f", hemen ardından {', '.join(es_iyi)} ({', '.join(_hucre(yil[y], 'r3') for y in es_iyi)} R)"
                                          if es_iyi else "") +
         f", en kötü {enkotu} ({_hucre(yil[enkotu], b_)} R)" +
         (f", hemen ardından {', '.join(es_kotu)} ({', '.join(_hucre(yil[y], 'r3') for y in es_kotu)} R)" if es_kotu else "")
         + ".")
    if all(terc.get(t) is not None for t in ("düşük", "orta", "yüksek")):
        s += (f" Oynaklık tercillerinde: düşük {_hucre(terc['düşük'], 'ra')}, orta {_hucre(terc['orta'], 'ra')}, "
              f"yüksek {_hucre(terc['yüksek'], 'ra')} R.")
    return s


def _zayif_baglam(u: Uretim, c: str, v: dict) -> str:
    """'Zayıf' bir paritenin bağlamı: hangi şartın tutmadığı, aynı varsayılanın örneklem içi ve bütün dönem sonucu,
    örneklem dışı artının yıllara ve en iyi işlemlere dağılımı. Hüküm değişmez; okur artının neye dayandığını görür."""
    o, i, t = v.get("oos") or {}, v.get("is") or {}, v.get("tum") or {}
    ras = (v.get("rastgele") or {}).get("oos") or {}
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    eksik = []
    if o.get("ga_alt") is None or not math.isfinite(o.get("ga_alt") or float("nan")):
        eksik.append("%95 aralığı kurulamadı (en az 10 işlem ister)")
    elif o["ga_alt"] <= 0:
        eksik.append(f"%95 aralığının alt ucu {_hucre(o['ga_alt'], 'ra')}")
    yz = ras.get("yuzdelik")
    if yz is None or not math.isfinite(yz):
        eksik.append("rastgele yön sınaması yapılamadı (en az 20 işlem ister)")
    elif yz < esik:
        eksik.append(f"rastgele yön yüzdeliği {sayi(yz, 1)}")
    s = (f"{PARITE[c]} zayıf: örneklem dışında {sayi(o.get('n') or 0, 0)} işlemde {_hucre(o.get('beklenti_r'), 'ra')} R, "
         f"ama {' ve '.join(eksik) or 'şartlardan biri tutmuyor'}; yani kenar kanıtlanmadı. Aynı varsayılan örneklem "
         f"içinde (2018–2023) {_hucre(i.get('beklenti_r'), 'ra')} R, bütün dönemde {_hucre(t.get('beklenti_r'), 'ra')} R.")
    dis_yil = {y: x for y, x in (v.get("yil") or {}).items() if int(y) >= int(u.O["kunye"]["dis_baslangic"][:4])}
    if dis_yil:
        s += " Örneklem dışı yıl yıl: " + " · ".join(f"{y} {_hucre(x.get('beklenti_r'), 'ra')} ({sayi(x.get('n') or 0, 0)} işlem)"
                                                      for y, x in sorted(dis_yil.items())) + "."
    ky = (v.get("kuyruk") or {}).get("oos") or {}
    if ky.get("r_tek_haric") is not None:
        s += (f" En iyi tek işlem ({tarih(ky['en_iyi_gun'])}, {_hucre(ky['en_iyi_r'], 'ra')} R, riski "
              f"{_pip(round(ky['en_iyi_R_pip'], 2))} pip) çıkarılınca {_hucre(ky['r_tek_haric'], 'ra')} R, en iyi üç işlem "
              f"çıkarılınca {_hucre(ky['r_uc_haric'], 'ra')} R.")
    return s


def blok_hukum_cumle(u: Uretim, ctx: dict) -> str:
    """Hükmün paragrafı: ön kaydın kuralı parite başına uygulanır (kural kosu._hukum'dadır); burada yalnız sayılır ve
    bağlamı yazılır. Birincil pencere 2024 →; bütün dönemin hükmü ayrışıyorsa adıyla."""
    hs = ctx["HS"]
    b = ctx["B"]
    if not hs["parite"]:
        return "Hüküm: ölçülemedi (işlem yok)."
    cs = _ciftler(b)
    v_ = {c: (b["cift"][c].get("varsayilan") or {}) for c in cs}
    adlar_ = {h: [PARITE[c] for c in cs if v_[c].get("hukum") == h]
              for h in ("calisiyor", "zayif", "calismiyor", "olculemedi")}
    if hs["calismiyor"] == hs["parite"]:
        ana_ = (f"**Çalışmıyor.** Önceden kayıtlı kural, sınanan {hs['parite']} paritenin hiçbirinde örneklem dışında "
                f"(2024 →) maliyetten sonra artı değil.")
    elif hs["calisiyor"] == hs["parite"]:
        ana_ = f"**Çalışıyor.** Önceden kayıtlı kural {hs['parite']} paritenin hepsinde hükmün üç şartını sağlıyor."
    elif hs["olculemedi"] == hs["parite"]:
        ana_ = "**Ölçülemedi.** Örneklem dışında (2024 →) hiçbir paritede işlem yok."
    else:
        parca = [f"{', '.join(adlar_[h])}: {adlar.HUKUM[h]}" for h in ("calisiyor", "zayif", "calismiyor", "olculemedi")
                 if adlar_[h]]
        bas = "Kanıtlanmış bir kenar yok" if not hs["calisiyor"] else "Yalnız bir kısmında"
        ana_ = f"**{bas}.** " + " · ".join(parca) + "."
        for c in cs:
            if v_[c].get("hukum") == "zayif":
                ana_ += " " + _zayif_baglam(u, c, v_[c])
    ayr = [(c, v_[c]) for c in cs if v_[c].get("hukum_tum") and v_[c].get("hukum_tum") != v_[c].get("hukum")]
    if ayr:
        ana_ += (" Bütün dönemin hükmü (varsayılan için o da örneklem dışıdır) ayrışıyor: " +
                 "; ".join(f"{PARITE[c]} {adlar.HUKUM[v['hukum']]} → {adlar.HUKUM[v['hukum_tum']]} "
                           f"({_hucre((v.get('tum') or {}).get('beklenti_r'), 'ra')} R)" for c, v in ayr) + ".")
    if hs["maliyet"] or hs["maliyet_oos"]:
        bay = [PARITE[c] for c in cs if v_[c].get("maliyet_yiyor")]
        bay_o = [PARITE[c] for c in cs if v_[c].get("maliyet_yiyor_oos")]
        ana_ += (" Maliyet bayrağı (brüt sonucun %95 aralığı sıfırın üstünde, net sonuç sıfır ya da altında) "
                 + "; ".join(x for x in ((f"bütün dönemde {', '.join(bay)}" if bay else ""),
                                         (f"2024 → penceresinde {', '.join(bay_o)}" if bay_o else "")) if x) + ".")
        arti_bay = [PARITE[c] for c in cs if v_[c].get("maliyet_yiyor")
                    and ((v_[c].get("oos") or {}).get("beklenti_r") or 0) > 0]
        if arti_bay:
            ana_ += (f" {', '.join(arti_bay)}: bayrak bütün dönemden yanıyor; aynı paritenin 2024 → net sonucu artı.")
    rp = _r_pip_cumle(b, "varsayilan", "Önceden kayıtlı kuralda")
    if rp:
        ana_ += " " + rp
    return ana_


def blok_kontrol_hukum(u: Uretim, ctx: dict) -> str:
    """Kontrol listesinin ilk maddesi: hüküm, kullanılır mı kullanılmaz mı (şartname §6)."""
    hs = ctx["HS"]
    b = ctx["B"]
    cs = _ciftler(b)
    v_ = {c: (b["cift"][c].get("varsayilan") or {}) for c in cs}
    r = {c: (v_[c].get("oos") or {}).get("beklenti_r") for c in cs}
    olcu = [c for c in cs if r[c] is not None]
    if hs["calisiyor"] == hs["parite"] and hs["parite"]:
        return (f"Kullanılır: önceden kayıtlı kural {hs['parite']} paritenin hepsinde hükmün üç şartını sağlıyor "
                f"(örneklem dışı, 2024 →).")
    if not olcu:
        return "Hüküm verilemedi: örneklem dışında işlem yok."
    en = max(olcu, key=lambda c: r[c])
    if hs["zayif"] or hs["calisiyor"]:
        zy = [c for c in cs if v_[c].get("hukum") in ("zayif", "calisiyor")]
        liste = ", ".join(PARITE[c] + " " + _hucre(r[c], "ra") + " R" for c in zy)
        return (f"Bu biçimiyle kanıtlanmış bir kenarı yok: örneklem dışında (2024 →) {liste}, ama hükmün şartlarını "
                f"sağlamıyor; öbür paritelerde sonuç sıfır ya da eksi.")
    return (f"Bu biçimiyle kullanılmaz: {SAYI_AD.get(len(cs), sayi(len(cs), 0))} paritenin hiçbirinde örneklem dışında "
            f"(2024 →) maliyetten sonra artı değil (en iyisi {PARITE[en]}, {_hucre(r[en], 'ra')} R).")


def blok_ne_zaman(u: Uretim, ctx: dict) -> str:
    """Kontrol listesinin "Ne zaman" maddesi, koşul analizinden: en az iki paritede aynı kovayla tutan koşullar aday
    olarak yazılır (paritelerin örneklem dışı sonuçlarıyla); aday yoksa bunu açıkça söyler."""
    b = ctx["B"]
    ad = kosul_adaylari(b)
    t = kosul_sayim(u.O)
    genel = ""
    if t["ters_sinanan"]:
        genel = (f" Bütün kurallar birlikte sayıldığında gerçek seçim ile ters seçimin tutma sıklığı ayırt edilemiyor "
                 f"(kesin McNemar p {_hucre(t['p'], 'p')}; karşılaştırma dersi)." if not t["ayirt"] else
                 f" Bütün kurallar birlikte sayıldığında gerçek seçim ters seçimden daha sık tutuyor (kesin McNemar p "
                 f"{_hucre(t['p'], 'p')}; karşılaştırma dersi).")
    if not ad:
        return ("Ölçülen koşulların hiçbiri bu kuralın kullanılacağı bir gün tarif etmiyor: hiçbir koşul iki paritede "
                "aynı kovayla tutmadı." + genel)
    parca = []
    for x in ad:
        sonuc = ", ".join(f"{PARITE[c]} {_hucre(k.get('oos_secilen_r'), 'ra')} R "
                          f"({sayi(k.get('oos_secilen_n') or 0, 0)} işlem; tamamlayanı "
                          f"{_hucre(k.get('oos_tamamlayan_r'), 'ra')} R)" for c, k in x["pariteler"])
        parca.append(f"{adlar.KOSUL.get(x['degisken'], x['degisken'])}, kova {_kova_yaz(x['kova'])}: {sonuc}")
    return ("Aday, karar kuralı değil. " + bas_buyuk("; ".join(parca)) + ". Aday, örneklem içinde seçilip örneklem dışında en az iki "
            "paritede aynı yönde duran bir kovadır; bu sınama hükmün öbür iki şartını (güven aralığı, rastgele yön) "
            "taşımaz." + genel)


def blok_ay_sonu(u: Uretim, ctx: dict) -> str:
    """WM/R fiksingi (ön kayıt [fiks]): aynı kuralın ay sonu ve öbür günlerdeki sonucu, parite parite, iki dönemde.
    Ay sonu için ayrı parametre seçilmez; yalnız ayrı raporlanır. Fark Welch t ile (iki yönlü p)."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        a = (b["cift"][c].get("varsayilan") or {}).get("ay_sonu") or {}
        for d, ad in (("tum", "bütün dönem"), ("oos", "2024 →")):
            x, o, f = ((a.get("ay_sonu") or {}).get(d) or {}), ((a.get("diger") or {}).get(d) or {}), \
                ((a.get("fark") or {}).get(d) or {})
            govde.append([PARITE[c], ad, _hucre(x.get("n"), "n"), _hucre(x.get("beklenti_r"), "ra"),
                          f"{_hucre(x.get('ga_alt'), 'ra')} / {_hucre(x.get('ga_ust'), 'ra')}",
                          _hucre(o.get("beklenti_r"), "ra"), _hucre(f.get("p"), "p")])
    return _tablo(["Parite", "Dönem", "Ay sonu işlem", "Ay sonu R", "%95 aralığı", "Öbür günler R", "Fark p"], govde,
                  ["l", "l", "r", "r", "r", "r", "r"])


def _ay_sonu_sinama_sayisi(u: Uretim) -> int:
    """Ay sonu ayrımı yapılan bütün birim × parite bileşimleri (fiksing kuralları): çoklu sınama payının paydası."""
    return sum(1 for bb in (u.O.get("birim") or {}).values() for v in (bb.get("cift") or {}).values()
               if (v.get("varsayilan") or {}).get("ay_sonu"))


def blok_ay_sonu_cumle(u: Uretim, ctx: dict) -> str:
    """Ay sonu tablosunun okunuşu, veriden: farkın kaç paritede aynı yönde olduğu, hangisinde p < 0,05 (ve sınama
    sayısıyla düzeltilmiş eşiğin altında), ay sonunun kendisinin nerede artı ya da eksi kaldığı, iki dönemde."""
    b = ctx["B"]
    cs = _ciftler(b)
    n_sin = _ay_sonu_sinama_sayisi(u)
    bonf = 0.05 / n_sin if n_sin else None
    cumle = []
    for d, ad in (("tum", "Bütün dönemde"), ("oos", "Örneklem dışında (2024 →)")):
        fark, kendi, anlamli, bon = [], [], [], []
        for c in cs:
            a = (b["cift"][c].get("varsayilan") or {}).get("ay_sonu") or {}
            f = ((a.get("fark") or {}).get(d) or {})
            x = ((a.get("ay_sonu") or {}).get(d) or {})
            if f.get("fark_r") is None:
                continue
            fark.append((c, f["fark_r"]))
            kendi.append((c, x.get("beklenti_r"), x.get("ga_alt")))
            if f.get("p") is not None and f["p"] < 0.05:
                anlamli.append(c)
                if bonf and f["p"] < bonf:
                    bon.append(c)
        if not fark:
            continue
        arti = [c for c, v in fark if v > 0]
        yon = (f"ay sonu ile öbür günlerin farkı {SAYI_AD.get(len(fark), len(fark))} paritenin "
               + ("hepsinde artı" if len(arti) == len(fark) else "hiçbirinde artı değil" if not arti else
                  f"{SAYI_AD.get(len(arti), len(arti))} tanesinde artı ({', '.join(PARITE[c] for c in arti)})"))
        s = f"{ad} {yon}"
        s += (f"; p < 0,05 olan: {', '.join(PARITE[c] for c in anlamli)}" if anlamli else "; hiçbirinde p < 0,05 değil")
        if anlamli and bonf:
            s += (f" ({sayi(n_sin, 0)} sınama için düzeltilmiş eşik {sayi(bonf, 4)}; "
                  + (f"{', '.join(PARITE[c] for c in bon)} bunun da altında)" if bon else
                     "hiçbiri bunun altında değil)"))
        art_k = [c for c, r, _ in kendi if r is not None and r > 0]
        alt_k = [c for c, r, g in kendi if g is not None and g > 0]
        s += (". Ay sonunun kendi net sonucu " +
              (f"{', '.join(PARITE[c] for c in art_k)} paritesinde artı" if art_k else "hiçbir paritede artı değil") +
              (f"; %95 aralığının alt ucu sıfırın üstünde kalan: {', '.join(PARITE[c] for c in alt_k)}" if alt_k else "")
              + ".")
        cumle.append(s)
    if n_sin:
        cumle.append(f"Bu bir alt küme ölçüsüdür: ön kayıt ay sonunu ayrı raporlamayı ister, ona ayrı hüküm vermez. "
                     f"Fiksing kurallarında ay sonu ayrımı {sayi(n_sin, 0)} kural–parite bileşiminde yapıldı; "
                     f"birbirinden bağımsız {sayi(n_sin, 0)} sınamada şansın en az birini 0,05'in altına düşürme "
                     f"olasılığı {yuzde(1 - 0.95 ** n_sin, 0)}.")
    return " ".join(cumle)


def blok_regresyon(u: Uretim, ctx: dict) -> str:
    """Gün içi momentum (ön kayıt [momentum]): öğleden sonra getirisi ~ Londra ilk mum getirisi, ikisi de
    girişteki 60 dakikalık ATR(14) biriminde; Newey–West standart hatası. Strateji işlemlerinden bağımsız, maliyetsiz,
    orta fiyat."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        rg = (b["cift"][c].get("varsayilan") or {}).get("regresyon") or {}
        for d, ad in (("is", "içi"), ("oos", "dışı")):
            x = rg.get(d) or {}
            govde.append([PARITE[c], ad, _hucre(x.get("n"), "n"), _hucre(x.get("beta"), "r3"),
                          _hucre(x.get("t_beta"), "r"), _hucre(x.get("p_beta"), "p"), _hucre(x.get("r2"), "s3"),
                          _hucre(x.get("isaret_isabet"), "yz1")])
    return _tablo(["Parite", "Örneklem", "Gün", "Eğim (β)", "t (HAC)", "p", "R²", "İşaret tutturma"], govde,
                  ["l", "l", "r", "r", "r", "r", "r", "r"])


# ─────────────────────────────────────────────────────────────── çözümlü alıştırma
def _ornek_bul(u: Uretim, birim: str, tur: str) -> tuple[dict, str]:
    if tur not in ORNEK_AD:
        raise SablonHatasi(f"pratik: tür {', '.join(ORNEK_AD)} olmalı: {tur}")
    c = ana()
    b = (u.O.get("birim") or {}).get(birim) or {}
    orn = (((b.get("cift") or {}).get(c) or {}).get("ornek")) or []
    x = next((o for o in orn if o.get("etiket") == tur), None)
    if not x:
        raise SablonHatasi(f"pratik: {birim} için {PARITE[c]} {tur} örneği yok")
    return x, c


def _cozum_blogu(soru: str, cozum: list[str]) -> str:
    return "\n".join([soru, "", "<details>", "<summary>Çözüm</summary>", ""] + [p + "\n" for p in cozum] +
                     ["</details>"])


def blok_pratik_islem(u: Uretim, ctx: dict, birim: str = "orb", etiket: str = "", tur: str = "kazanan") -> str:
    """Bir stratejinin ana paritedeki örnek işleminden (figürdeki örnek günlerin aynısı; tur: kazanan · kaybeden ·
    tuzak) çözümlü alıştırma: risk, sonuç ve R; dolum başına ek kaymanın etkisi. (c) şıkkının cevabı elle değil
    BACKTEST'TEN gelir: işlem aynı emirle ek kaymayla yeniden koşturulmuştur (kosu.ornek_gunler). R katı hedef ve
    yürütülen girişten konan stop yeni dolumdan yeniden kurulur, sabit seviye hedef kaymaz; ek kayma çıkışı da
    değiştirebilir (uzaklaşan hedefe ulaşılmaz). Çözümün aritmetiği kayıtla karşılaştırılır, tutmazsa üretim düşer."""
    x, cp = _ornek_bul(u, birim, tur)
    i, ek = x["islem"], x["ek_kayma"]
    if i.get("stopsuz") or i.get("stop") is None:
        raise SablonHatasi(f"pratik_islem: {birim} örneği stop'suz; pratik_atr kullanılır")
    npip = _nokta_pip(cp)
    yon = i["yon"]
    g, s, c = i["giris_f"], i["stop"], i["cikis_f"]
    risk = abs(g - s) / npip
    sonuc = (c - g) * yon / npip
    if abs(risk - i["R_pip"]) > 0.011 or abs(sonuc - i["pnl_pip"]) > 0.011 or abs(sonuc / risk - i["r"]) > 0.0051:
        raise SablonHatasi(f"pratik: elle aritmetik backtest kaydıyla tutmuyor ({sonuc / risk:.3f} ↔ {i['r']:.3f})")
    if ek.get("durum") != 0 or ek.get("r") is None:
        raise SablonHatasi(f"pratik: {birim} ek kaymalı yeniden koşu işlem açmadı")
    k_gs = u.O["kunye"]["gun_sonu_et"]
    dk = ek["kayma_pip"] - u.O["kunye"]["temel_kayma_pip"]
    yon_ad = "alış" if yon > 0 else "satış"
    ad = adlar.BIRIM[birim][1]
    f = lambda v: fiyat_yaz(v, cp)  # noqa: E731
    soru = (f"**{etiket or 'Alıştırma'} — bir işlemin R'si.** {ad} kuralının {PARITE[cp]}'deki "
            f"{ORNEK_AD[tur].lower()} örneği ({tarih_uzun(x['gun'])}): {yon_ad}, giriş {f(g)} "
            f"({'ask' if yon > 0 else 'bid'}, kayma dahil), stop {f(s)}"
            + (f", hedef {f(i['hedef'])}" if i.get("hedef") is not None else "") +
            f", çıkış {f(c)} ({adlar.neden_ad(i, k_gs)}). (a) Risk kaç pip? (b) İşlem kaç pip ve kaç R getirdi? "
            f"(c) Dolum başına kayma {sayi(dk, 1)} pip daha kötü olsaydı ne olurdu?")
    cozum = [f"(a) Risk, yürütülen giriş fiyatından stop'a uzaklıktır: {f(g)} ile {f(s)} arası **{_pip(risk)} pip**.",
             f"(b) Sonuç " + (f"{f(c)} − {f(g)}" if yon > 0 else f"{f(g)} − {f(c)} (satışta giriş eksi çıkış)") +
             f" = **{sayi(sonuc, 2 if abs(sonuc * 10 - round(sonuc * 10)) > 1e-6 else 1, arti=True)} pip**; "
             f"R = sonuç / risk = {_pip(sonuc)} / {_pip(risk)} = **{sayi(i['r'], 2, arti=True)} R**." +
             (f" Kayıp riskten büyük, çünkü çıkış stop seviyesinde değil {_pip(abs(c - s) / npip)} pip ötesinde "
              f"doldu: yürütülen fiyat makası ve kaymayı içerir." if i["neden"] in (1, 4, 5) and abs(c - s) >= 0.5
              and sonuc < 0 else "")]
    # (c): backtest'in ek kaymalı yeniden koşusu.
    g2, c2, r2 = ek["giris_f"], ek["cikis_f"], ek["r"]
    risk2 = ek["R_pip"]
    ht = i.get("hedef_tur")
    parca = [f"(c) Backtest işlemi aynı emirle, dolum başına {sayi(dk, 1)} pip ek kaymayla yeniden koşturuldu. Yeni "
             f"giriş {f(g2)}; stop seviyesi aynı kaldığı için risk {_pip(risk2)} pip olur."]
    if ht == 1:
        parca.append(f"Hedef girişten {sayi(i['hedef_k'], 0)}R uzakta kurulduğu için o da yeni girişle birlikte "
                     f"uzaklaşır: {f(ek['hedef'])}.")
    elif ht == 2:
        parca.append("Hedef sabit bir seviyedir ve limit emirdir: yeri değişmez, dolarken kaymaz.")
    if ek.get("neden") == i["neden"] and ek.get("cikis_t") == i["cikis_t"]:
        if ht == 1 and i["neden"] in (2, 6):
            parca.append(f"Hedef yine değdi: sonuç yine **{sayi(r2, 2, arti=True)} R** ({sayi(ek['pnl_pip'], 1, arti=True)} "
                         f"pip). R katı hedefli bir kuralda kaymanın bedeli kazanan işlemin R'sinde görünmez; hedefin "
                         f"uzaklaşmasıyla daha az işlemin hedefe ulaşmasında ve stop'ta kapanan işlemin kaybının "
                         f"büyümesinde görünür.")
        else:
            cikis = ("Çıkış limit emirdir, kaymaz" if i["neden"] in (2, 6) else
                     "Çıkış emri de piyasada dolar ve o da kayar")
            parca.append(f"{cikis}: çıkış {f(c2)}, sonuç {sayi(ek['pnl_pip'], 1, arti=True)} pip. Yeni R = "
                         f"{_pip(ek['pnl_pip'])} / {_pip(risk2)} = **{sayi(r2, 2, arti=True)} R**.")
            if i["r"] > 0:
                parca.append("Pay küçülür, payda büyür: kazanç R cinsinden, pip cinsinden olduğundan hızlı erir; en çok "
                             "da stop'u yakın kurallarda.")
            elif r2 < i["r"]:
                parca.append("Kayıp pip olarak büyür; payda da büyüdüğü için R cinsinden daha yavaş büyür.")
            else:
                parca.append("Kayıp pip olarak büyür ama R cinsinden küçülür: risk kayıptan hızlı büyüdü.")
    else:
        parca.append(f"Bu kez çıkış değişir: işlem {saat_tsi(ek['cikis_t'])} TSİ'de, {f(c2)} fiyatından kapanır "
                     f"({adlar.neden_ad({'neden': ek['neden'], 'cikis_t': ek['cikis_t']}, k_gs)}): "
                     f"**{sayi(r2, 2, arti=True)} R** ({sayi(ek['pnl_pip'], 1, arti=True)} pip)."
                     + (" Uzaklaşan hedefe ulaşılamadı; kaymanın asıl bedeli budur." if ht == 1 and i["neden"] in (2, 6)
                        else ""))
    if abs(ek["pnl_pip"] / risk2 - r2) > 0.0051:
        raise SablonHatasi(f"pratik: ek kaymalı kayıt kendi içinde tutmuyor ({birim})")
    cozum.append(" ".join(parca))
    return _cozum_blogu(soru, cozum)


def blok_pratik_atr(u: Uretim, ctx: dict, birim: str = "momentum", etiket: str = "", tur: str = "kazanan") -> str:
    """Stop'suz bir kuralın (R birimi girişteki ATR) ana paritedeki örnek işleminden çözümlü alıştırma. ATR backtest
    kaydından (R_pip) okunur ve soruda verilir; (c) ek kaymalı yeniden koşudan gelir. Kayma burada paydayı büyütmez:
    R birimi fiyattan değil oynaklıktan gelir."""
    x, cp = _ornek_bul(u, birim, tur)
    i, ek = x["islem"], x["ek_kayma"]
    if not i.get("stopsuz") or i.get("neden") != 3:
        raise SablonHatasi(f"pratik_atr: {birim} örnek işlemi stop'suz bir zaman çıkışı değil")
    npip = _nokta_pip(cp)
    g, c = i["giris_f"], i["cikis_f"]
    yon = i["yon"]
    sonuc = (c - g) * yon / npip
    atr = i["R_pip"]
    if abs(sonuc - i["pnl_pip"]) > 0.011 or abs(sonuc / atr - i["r"]) > 0.0051:
        raise SablonHatasi(f"pratik_atr: elle aritmetik backtest kaydıyla tutmuyor ({sonuc} ↔ {i['pnl_pip']})")
    if ek.get("durum") != 0 or ek.get("r") is None:
        raise SablonHatasi(f"pratik_atr: {birim} ek kaymalı yeniden koşu işlem açmadı")
    if abs(ek["R_pip"] - atr) > 0.011:
        raise SablonHatasi(f"pratik_atr: ek kaymada R birimi değişti ({birim}) — stop'suz kuralda değişmemeli")
    dk = ek["kayma_pip"] - u.O["kunye"]["temel_kayma_pip"]
    ad = adlar.BIRIM[birim][1]
    f = lambda v: fiyat_yaz(v, cp)  # noqa: E731
    yon_ad = "alış" if yon > 0 else "satış"
    soru = (f"**{etiket or 'Alıştırma'} — stop'suz bir kuralda R.** {ad} kuralının {PARITE[cp]}'deki "
            f"{ORNEK_AD[tur].lower()} örneği ({tarih_uzun(x['gun'])}): {yon_ad}, giriş {saat_tsi(i['giris_t'])} TSİ'de "
            f"{f(g)} ({'ask' if yon > 0 else 'bid'}, kayma dahil), çıkış {saat_tsi(i['cikis_t'])} TSİ'de {f(c)} "
            f"({adlar.neden_ad(i, u.O['kunye']['gun_sonu_et'])}). Kuralda stop yoktur; R birimi girişteki ATR'dir "
            f"(bu işlemde {_pip(atr)} pip). (a) İşlem kaç pip getirdi? (b) Kaç R? (c) Dolum başına kayma "
            f"{sayi(dk, 1)} pip daha kötü olsaydı?")
    cozum = [f"(a) " + (f"{f(c)} − {f(g)}" if yon > 0 else f"{f(g)} − {f(c)} (satışta giriş eksi çıkış)") +
             f" = **{sayi(sonuc, 2 if abs(sonuc * 10 - round(sonuc * 10)) > 1e-6 else 1, arti=True)} pip**.",
             f"(b) R = sonuç / ATR = {_pip(sonuc)} / {_pip(atr)} = **{sayi(i['r'], 2, arti=True)} R**.",
             f"(c) İki dolum da piyasa emridir ve ikisi de kayar (backtest'in ek kaymalı yeniden koşusu): giriş "
             f"{f(ek['giris_f'])}, çıkış {f(ek['cikis_f'])}, sonuç {sayi(ek['pnl_pip'], 1, arti=True)} pip. Payda "
             f"değişmez, çünkü R birimi stop uzaklığı değil oynaklıktır: yeni R = {_pip(ek['pnl_pip'])} / {_pip(atr)} = "
             f"**{sayi(ek['r'], 2, arti=True)} R**. Stop'lu bir kuralda kayma riski de büyütür; burada yalnız sonucu "
             f"küçültür. Stop olmadığı için kayıp 1 R'de durmaz."]
    return _cozum_blogu(soru, cozum)


# ─────────────────────────────────────────────────────────────── veri ve takvim blokları
def _kalite(u: Uretim) -> dict:
    return ((u.O.get("veri") or {}).get("kalite")) or {}


def _utc_tsi(s: str) -> str:
    """'YYYY-AA-GG SS:DD' (UTC) → 'GG.AA.YYYY SS:DD TSİ'."""
    t = datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).astimezone(TSI)
    return t.strftime("%d.%m.%Y %H:%M") + " TSİ"


def blok_veri(u: Uretim, ctx: dict) -> str:
    """Veri denetiminin parite parite özeti (kalite raporu), iki tablo: kapsam ve boşluklar; makas, sıçrama adayı ve
    çapraz sınama."""
    kap, fiy = [], []
    for c in PARITE:
        k = _kalite(u).get(c)
        if not k:
            continue
        kp, mk_, sc, cp = k.get("kapsam") or {}, k.get("makas") or {}, k.get("sicrama") or {}, k.get("capraz") or {}
        bk = kp.get("bosluk_kovalari") or {}
        uzun = (kp.get("en_uzun_bosluklar") or [None])[0]
        bes = sum(int(v) for kk, v in bk.items() if kk in ("5-14", "15-59", "60+"))
        kap.append([PARITE[c], _hucre(k.get("satir"), "n"), _hucre(kp.get("normal_gun_kapsam_yuzde"), "s1"),
                    _hucre(len(kp.get("tatil_gunleri") or []), "n"), _hucre(bes, "n"),
                    f"{sayi(uzun['uzunluk_dk'], 0)} dk ({_utc_tsi(uzun['baslangic_utc'])})" if uzun else "—"])
        fiy.append([PARITE[c], _hucre(mk_.get("medyan_pip"), "s1"), _hucre(mk_.get("p95_pip"), "s1"),
                    _hucre((mk_.get("sifir_kapanis") or 0) + (mk_.get("negatif_kapanis") or 0), "n"),
                    _hucre(sc.get("aday"), "n"), _hucre(cp.get("tam_esit_yuzde"), "s1")])
    if not kap:
        return "_Veri denetimi henüz yok._"
    return (_tablo(["Parite", "Dakika", "Kapsam, normal gün (%)", "Tatil günü", "Boşluk ≥ 5 dk", "En uzun boşluk"], kap,
                   ["l", "r", "r", "r", "r", "l"]) + "\n\n" +
            _tablo(["Parite", "Makas medyanı (pip)", "Makas p95 (pip)", "Sıfır ya da eksi makas (dakika)",
                    "Sıçrama adayı", "Saatlik çapraz sınama (%)"], fiy, ["l"] + ["r"] * 5))


def blok_haber_makas(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Haber dakikalarında makas (bir parite): olay saatine göre seçili dakikalarda medyan kapanış makası, zirve
    dakikası ve zirvenin aynı dakikadaki olaysız günlere göre katı. Dakika, 1 dakikalık mumun BAŞLANGICIDIR ve değer o
    mumun kapanışındaki makastır: −1 açıklamadan önceki son kotasyon, 0 açıklamadan bir dakika sonrası."""
    cift = cift or ana()
    hm = (_kalite(u).get(cift) or {}).get("haber_makasi") or {}
    if not hm:
        return f"_{PARITE[cift]} için haber makası ölçülmedi._"
    dk_sec = [-5, -2, -1, 0, 1, 5, 15]
    govde = []
    for o in [x for x in olay_sira(u) if x in hm]:
        v = hm[o]
        dks = v.get("dk") or []
        med = v.get("medyan_pip") or []
        satir = [adlar.OLAY.get(o, o), _hucre(v.get("n_olay"), "n")]
        for d in dk_sec:
            satir.append(_hucre(med[dks.index(d)] if d in dks and dks.index(d) < len(med) else None, "s1"))
        z = v.get("zirve") or {}
        satir.append(_hucre(z.get("kiyas_pip"), "s1"))
        satir.append(f"{sayi(z['dk'], 0, arti=True)} dk · {sayi(z['oran'], 1)} kat" if z.get("oran") else "—")
        govde.append(satir)
    bas = ["Olay", "Olay sayısı"] + [f"{sayi(d, 0, arti=d != 0)} dk" for d in dk_sec] + \
          ["Olaysız gün, zirve dakikası", "Zirve"]
    return (_tablo(bas, govde, ["l"] + ["r"] * (len(bas) - 1)) +
            f"\n\n_{PARITE[cift]}, medyan makas (pip), dakika kapanışında. Dakika olay saatine göre 1 dakikalık mumun "
            f"başlangıcıdır: −1 açıklamadan önceki son kotasyon, 0 açıklamanın ilk dakikasının kapanışı._")


def blok_haber_makas_cumle(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Haber makasının tek cümlesi: dakika kapanışında ölçülen zirve dakikası ve olaysız güne göre katın olaylar
    arasındaki aralığı. Açıklama saniyesinin kendisi bu ölçüde görünmez (dakika kapanışı ölçülür)."""
    cift = cift or ana()
    hm = (_kalite(u).get(cift) or {}).get("haber_makasi") or {}
    z = [(o, (hm[o].get("zirve") or {})) for o in olay_sira(u) if o in hm and (hm[o].get("zirve") or {}).get("oran")]
    if not z:
        return f"{PARITE[cift]} için haber makası ölçülmedi."
    n1 = sum(1 for _, v in z if v["dk"] == -1)
    nerede = ("açıklamadan önceki son dakikada" if n1 == len(z) else
              f"{len(z)} olayın {ek(n1, 'inde')} açıklamadan önceki son dakikada" if n1 * 2 > len(z) else
              "açıklama çevresinde")
    lo = min(z, key=lambda kv: kv[1]["oran"])
    hi = max(z, key=lambda kv: kv[1]["oran"])
    return (f"{PARITE[cift]}'de dakika kapanışlarında ölçülen makas en geniş hâline {nerede} ulaşır; o dakikada aynı "
            f"saatin olaysız günlerinin {sayi(lo[1]['oran'], 1)} katı ({adlar.OLAY.get(lo[0], lo[0])}) ile "
            f"{sayi(hi[1]['oran'], 1)} katı ({adlar.OLAY.get(hi[0], hi[0])}) arasındadır. Açıklamanın ilk saniyelerindeki "
            f"makas bu ölçünün dışında kalır: kayıt dakika kapanışlarından oluşur.")


def blok_haber_makas_ozet(u: Uretim, ctx: dict) -> str:
    """Bütün pariteler: her olayda zirve makası (pip) ve olaysız güne göre katı."""
    govde, olaylar = [], []
    for c in PARITE:
        hm = (_kalite(u).get(c) or {}).get("haber_makasi") or {}
        olaylar += [o for o in olay_sira(u) if o in hm and o not in olaylar]
    olaylar = [o for o in olay_sira(u) if o in olaylar]
    for c in PARITE:
        hm = (_kalite(u).get(c) or {}).get("haber_makasi") or {}
        if not hm:
            continue
        satir = [PARITE[c]]
        for o in olaylar:
            z = (hm.get(o) or {}).get("zirve") or {}
            satir.append(f"{sayi(z['pip'], 1)} ({sayi(z['oran'], 1)} kat)" if z.get("oran") else "—")
        govde.append(satir)
    if not govde:
        return "_Haber makası ölçülmedi._"
    return (_tablo(["Parite"] + [adlar.OLAY.get(o, o) for o in olaylar], govde, ["l"] + ["r"] * len(olaylar)) +
            "\n\n_Zirve makası (pip, dakika kapanışında) ve aynı dakikada olaysız günlerin medyanına göre katı._")


BOLGE_AD = {"America/New_York": "New York", "Europe/Berlin": "Frankfurt", "Europe/London": "Londra"}
SINAMA_AD = [("dogrulandi", "doğrulandı"), ("sessiz", "sessiz"), ("celiski", "çelişki"),
             ("degerlendirilemedi", "değerlendirilemedi")]


def blok_takvim(u: Uretim, ctx: dict) -> str:
    """Haber takviminin olay başına özeti: sayı, dönem, yerel saat(ler), saatin kaynağı (tarih tarih ya da kural),
    kaynak, fiyat sınamasının hükmü."""
    t = (u.O.get("takvim") or {})
    sayim = t.get("sayim") or {}
    oz = ((t.get("sinama") or {}).get("ozet")) or {}
    govde = []
    for o in [x for x in olay_sira(u) if x in sayim]:
        v = sayim[o]
        saat = "; ".join(f"{k.split(' ', 1)[0]} {BOLGE_AD.get(k.split(' ', 1)[1], k.split(' ', 1)[1])} ({sayi(n, 0)})"
                         for k, n in sorted((v.get("saat") or {}).items(), key=lambda kv: -kv[1]))
        sk = v.get("saat_kaynagi") or {}
        kay = " · ".join(x for x in ((f"tarih tarih ({sayi(sk['tarih'], 0)})" if sk.get("tarih") else ""),
                                     (f"kuraldan ({sayi(sk['kural'], 0)})" if sk.get("kural") else "")) if x) or "—"
        s = oz.get(o) or {}
        sin = " · ".join(f"{s[k]} {ad}" for k, ad in SINAMA_AD if s.get(k)) or (
            "sınanmadı (konuşma tek dakikada sıçrama yapmaz; yalnız bilgi)" if s.get("basin_bilgi") else "—")
        govde.append([adlar.OLAY.get(o, o), _hucre(v.get("toplam"), "n"),
                      f"{tarih(v['ilk'])} → {tarih(v['son'])}" if v.get("ilk") else "—", saat or "—", kay,
                      ", ".join(v.get("kaynak") or []) or "—", sin])
    if not govde:
        return "_Takvim yok._"
    return _tablo(["Olay", "Sayı", "Dönem", "Yerel saat (olay sayısı)", "Saatin kaynağı", "Kaynak", "Fiyat sınaması"],
                  govde, ["l", "r", "l", "l", "l", "l", "l"])


# ─────────────────────────────────────────────────────────────── metodoloji blokları
BOLUM_AD = {"haber_devam": "haber devam tablosu"}


def blok_onkayit_tablo(u: Uretim, ctx: dict) -> str:
    """Ön kaydın geçmişi: her değişikliğin zamanı ve değişen bölümleri (kaynak deponun geçmişinden, ölçüm anında)."""
    g = (u.O.get("kunye") or {}).get("onkayit_gecmisi") or []
    govde = []
    for i, k in enumerate(g):
        zaman = k.get("zaman")
        z = (f"{tarih(zaman[:10])} {zaman[11:16]}" if zaman else "işlenmemiş değişiklik")
        bolum = k.get("degisen_bolum") or []
        ne = ("ilk kayıt: bütün kurallar, ızgaralar, varsayılanlar ve hüküm kuralı" if i == 0 else
              ("yalnız açıklama notu; kuralların içeriği aynı" if not bolum else
               "eklenen ya da değişen bölüm: " + ", ".join(BOLUM_AD.get(b_, b_) for b_ in bolum)))
        govde.append([z, ne])
    if not govde:
        return "_Ön kayıt geçmişi okunamadı._"
    return _tablo(["Zaman (UTC)", "Değişiklik"], govde, ["l", "l"])


def _gun_cevir(metin: str) -> str:
    """Kaynak kaydındaki ISO tarihleri okur yazımına (GG.AA.YYYY) çevirir."""
    return re.sub(r"(\d{4})-(\d{2})-(\d{2})", lambda m: f"{m.group(3)}.{m.group(2)}.{m.group(1)}", metin)


def blok_takvim_sorun(u: Uretim, ctx: dict) -> str:
    """Takvimin dışarıda bıraktığı ya da düzelttiği kayıtlar ve yayımı olmayan referans ayları (kaynak künyesi)."""
    k = ((u.O.get("takvim") or {}).get("kunye")) or {}
    satir = []
    for kod, ad in (("NFP", "ABD tarım dışı istihdam"), ("CPI", "ABD TÜFE")):
        v = k.get(kod) or {}
        for ay_ in v.get("yayimi_olmayan_referans_ayi") or []:
            satir.append(f"- **{ad}:** {ay_uzun(ay_ + '-01')} referans ayının ayrı bir yayımı yok.")
        for d in v.get("duzeltme") or []:
            satir.append(f"- **{ad}:** {_gun_cevir(d)}.")
        n_ok = len(v.get("referansi_okunamayan_yayim") or [])
        if n_ok:
            satir.append(f"- **{ad}:** {sayi(n_ok, 0)} yayımda referans ayı okunamadı; yayım günü ve saati "
                         f"okunduğu için olay takvimde.")
    for kod, ad in (("ecb", "ECB"), ("boe", "BoE")):
        for d in (k.get(kod) or {}).get("sorun") or []:
            satir.append(f"- **{ad}:** {_gun_cevir(d)}.")
    f = k.get("fomc") or {}
    if f.get("basin"):
        satir.append(f"- **FOMC:** {sayi(f['basin'], 0)} basın toplantısının saati okundu; "
                     f"{sayi(len(f.get('sorun') or []), 0)} toplantının saati okunamadı ve yazılmadı.")
    elif f.get("sorun"):
        satir.append(f"- **FOMC:** basın toplantılarının saati Fed'in kaynaklarından okunamadı "
                     f"({sayi(len(f['sorun']), 0)} toplantı); basın toplantısı olayları bu ölçümde yok.")
    return "\n".join(satir) if satir else "_Takvimde dışarıda bırakılan kayıt yok._"


def blok_celiski(u: Uretim, ctx: dict) -> str:
    """Fiyat sınamasının çelişki verdiği olaylar: resmî saatteki sıçrama oranı ve en iyi aday saat, parite parite."""
    c = (((u.O.get("takvim") or {}).get("sinama")) or {}).get("celiski_olay") or []
    satir = []
    for e in c:
        bolge = BOLGE_AD.get(e.get("bolge"), e.get("bolge"))
        par = []
        for cift, v in (e.get("parite") or {}).items():
            if v.get("durum") != "celiski":
                continue
            dk = int(v["en_iyi_aday_dk"])
            par.append(f"{PARITE.get(cift, cift)} {sayi(v['oran'], 2)} (en iyi aday {sayi(abs(dk), 0)} dakika "
                       f"{'sonra' if dk > 0 else 'önce'}: {sayi(v['aday'][str(dk)], 2)})")
        satir.append(f"- **{adlar.OLAY.get(e['olay'], e['olay'])}, {tarih(e['tarih'])} {e['yerel_saat']} {bolge}:** "
                     f"resmî saatte sıçrama oranı " + "; ".join(par) + ".")
    return "\n".join(satir) if satir else "_Çelişki yok._"


def blok_olaganustu(u: Uretim, ctx: dict, olay: str = "FOMC_karar") -> str:
    """Takvimdeki olağanüstü toplantılar: gün ve yerel saat (kaynağın notundan)."""
    v = (((u.O.get("takvim") or {}).get("sayim")) or {}).get(olay) or {}
    liste = v.get("olaganustu") or []
    if not liste:
        return "olağanüstü toplantı yok"
    return " ve ".join(f"{tarih_uzun(x['tarih'])} {x['saat']} {BOLGE_AD.get(x['bolge'], x['bolge'])}" for x in liste)


def blok_arsiv_ozet(u: Uretim, ctx: dict) -> str:
    """Fiyat arşivinin parite başına özeti: yıl birimleri, tamamlanan birim, işlem günü, eksik gün, dakika."""
    a = ((u.O.get("veri") or {}).get("arsiv")) or {}
    govde = []
    for c in PARITE:
        bs = {k: v for k, v in a.items() if k.split("/")[0] == c}
        if not bs:
            continue
        govde.append([PARITE[c], _hucre(len(bs), "n"), _hucre(sum(1 for v in bs.values() if v.get("tam")), "n"),
                      _hucre(sum(v.get("gun") or 0 for v in bs.values()), "n"),
                      _hucre(sum(v.get("gun_dolu") or 0 for v in bs.values()), "n"),
                      _hucre(sum(v.get("gun_hata") or 0 for v in bs.values()), "n"),
                      _hucre(sum(v.get("satir") or 0 for v in bs.values()), "n")])
    if not govde:
        return "_Arşiv künyesi yok._"
    tablo = _tablo(["Parite", "Yıl", "Tamamlanan yıl", "İstenen gün (UTC dosyası)", "Dolu gün", "İnmeyen gün", "Dakika"],
                   govde, ["l"] + ["r"] * 6)
    # İstenen ile dolu gün arasındaki fark: kaynağın kotasyonsuz döndürdüğü günler, gün gün ve hangi paritede.
    bos: dict = {}
    for k, v in a.items():
        c = k.split("/")[0]
        if c in PARITE:
            for g in v.get("bos_gunler") or []:
                bos.setdefault(g, []).append(c)
    if not bos:
        return tablo
    parca = []
    for g in sorted(bos):
        cs = [c for c in PARITE if c in bos[g]]
        parca.append(f"{tarih(g)} ({'dört parite' if len(cs) == len(PARITE) == 4 else ', '.join(PARITE[c] for c in cs)})")
    return (tablo + "\n\n_Dolu gün ile istenen gün arasındaki fark, kaynağın kotasyonsuz döndürdüğü günlerdir: "
            + "; ".join(parca) + "._")


def blok_pencere_ayrisan(u: Uretim, ctx: dict) -> str:
    """Hüküm penceresinin seçimiyle hükmü değişen bileşimler: önceden kayıtlı varsayılanın 2024 → hükmü ile bütün
    dönem hükmü ayrışan kural–parite bileşimleri, iki hükümle ve iki dönemin işlem başına net R'siyle."""
    satir = []
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            v = b["cift"][c].get("varsayilan") or {}
            h, ht = v.get("hukum") or "olculemedi", v.get("hukum_tum") or "olculemedi"
            if h == ht:
                continue
            o, t = v.get("oos") or {}, v.get("tum") or {}
            satir.append(f"{adlar.BIRIM[bid][1]}, {PARITE[c]}: 2024 → {adlar.HUKUM[h]} "
                         f"({_hucre(o.get('beklenti_r'), 'ra')} R, {sayi(o.get('n') or 0, 0)} işlem), bütün dönem "
                         f"{adlar.HUKUM[ht]} ({_hucre(t.get('beklenti_r'), 'ra')} R, {sayi(t.get('n') or 0, 0)} işlem)")
    if not satir:
        return "hiçbir bileşimde ayrışmıyor"
    return f"{sayi(len(satir), 0)} bileşimde ayrışıyor: " + "; ".join(satir)


# ─────────────────────────────────────────────────────────────── haber bloklari
KOVA_SIRA = ["<0,5", "0,5–1", "1–2", ">2"]
UYUM_ADI = {"aynı": "öncesi trendle aynı yönde", "ters": "öncesi trende ters", "belirsiz": "belirsiz (trend ya da ilk mum sıfır)"}


def olay_sira(u: Uretim) -> list[str]:
    """Olayların okuma sırası: ön kaydın listesi ([haber] olaylar), sonra takvime ek dosyadan gelen olaylar
    (görüldükleri sırayla). Elle tutulan ikinci bir liste yok."""
    on = list(((u.ON.get("haber") or {}).get("olaylar")) or [])
    ek_ = [o for o in (((u.O.get("takvim") or {}).get("sayim")) or {}) if o not in on]
    return on + ek_


def _devam(u: Uretim) -> dict:
    return ((u.O.get("haber") or {}).get("devam")) or {}


def _boyut_sira(u: Uretim, boyut: str, degerler: set) -> list[str]:
    if boyut == "olay":
        return [o for o in olay_sira(u) if o in degerler]
    if boyut == "kova":
        return [k for k in KOVA_SIRA if k in degerler]
    if boyut == "tf":
        return sorted(degerler, key=int)
    if boyut == "cift":
        return [c for c in PARITE if c in degerler]
    if boyut == "olay_kova":
        sira = olay_sira(u)
        return sorted(degerler, key=lambda d: (sira.index(d.split("|")[0]) if d.split("|")[0] in sira else 99,
                                               KOVA_SIRA.index(d.split("|")[1]) if d.split("|")[1] in KOVA_SIRA else 9))
    return sorted(degerler)


def _boyut_ad(boyut: str, deger: str) -> str:
    if boyut == "olay":
        return adlar.OLAY.get(deger, deger)
    if boyut == "trend_uyum":
        return UYUM_ADI.get(deger, deger)
    if boyut == "tf":
        return f"{deger} dk mum"
    if boyut == "cift":
        return PARITE.get(deger, deger)
    if boyut == "olay_kova":
        o, k = deger.split("|", 1)
        return f"{adlar.OLAY.get(o, o)} · {k}"
    return deger


def blok_devam(u: Uretim, ctx: dict, boyut: str = "olay") -> str:
    """Kırılım ↔ fade devam tablosu (ön kayıt [haber_devam]): bir boyutun her değeri × her ufuk. Hücre: olay
    sayısı, iki yönün net ortalaması (günlük ATR'nin yüzdesi) ve ön kaydın hükmü (BH q < eşik)."""
    hucre = [h for h in _devam(u).get("hucre") or [] if h.get("boyut") == boyut]
    if not hucre:
        return "_Devam tablosu bu boyutta ölçülemedi (olay yok)._"
    degerler = _boyut_sira(u, boyut, {h["deger"] for h in hucre})
    ufuklar = sorted({int(h["ufuk"]) for h in hucre})
    idx = {(h["deger"], int(h["ufuk"])): h for h in hucre}
    govde = []
    for d in degerler:
        for f in ufuklar:
            h = idx.get((d, f))
            if not h:
                continue
            govde.append([_boyut_ad(boyut, d), f"{f} dk", _hucre(h.get("n_olay"), "n"),
                          _hucre((h.get("kir") or {}).get("ort_atr_yuzde"), "r1"),
                          _hucre((h.get("fad") or {}).get("ort_atr_yuzde"), "r1"), h.get("hukum") or "—"])
    bas = {"olay": "Olay", "kova": "İlk mum / ATR", "trend_uyum": "Haber öncesi trend", "tf": "Mum",
           "cift": "Parite", "olay_kova": "Olay · ilk mum / ATR"}.get(boyut, boyut)
    return _tablo([bas, "Ufuk", "Olay sayısı", "Kırılım (ATR'nin %)", "Fade (ATR'nin %)", "Hüküm"], govde,
                  ["l", "l", "r", "r", "r", "l"])


def blok_devam_cumle(u: Uretim, ctx: dict) -> str:
    """Devam tablosunun aile özeti: hücre ve sınama sayısı (tek olaylı hücrede t tanımsızdır), hüküm sayımı, kural,
    ufku gün sonuna taşan gözlemler."""
    d = _devam(u)
    if not d.get("hucre"):
        return "Devam tablosu ölçülemedi."
    k = d.get("kural") or {}
    say = d.get("hukum_sayimi") or {}
    parca = ", ".join(f"{sayi(v, 0)} hücrede {ad}" for ad, v in sorted(say.items(), key=lambda kv: -kv[1]))
    boyutlar = []
    for h in d["hucre"]:
        if h.get("boyut") not in boyutlar:
            boyutlar.append(h.get("boyut"))
    ad = {"olay": "olay", "kova": "ilk mum büyüklüğü", "trend_uyum": "haber öncesi trend", "tf": "mum uzunluğu",
          "cift": "parite", "olay_kova": "olay × ilk mum büyüklüğü"}
    sira = [b for b in ad if b in boyutlar] + [b for b in boyutlar if b not in ad]
    tablo = ", ".join(ad.get(b, b) for b in sira)
    n_hucre = len(d["hucre"])
    tanimsiz = sum(1 for h in d["hucre"] for y in ("kir", "fad") if (h.get(y) or {}).get("p_tek") is None)
    s = (f"Aşağıdaki {sayi(len(sira), 0)} tablonun ({tablo}) {sayi(n_hucre, 0)} hücresi ve her hücrenin iki yönü "
         f"tek bir sınama ailesidir: {sayi(n_hucre, 0)} × 2 = {sayi(2 * n_hucre, 0)}"
         + (f"; tek olaylı hücrelerde t tanımsız olduğu için {sayi(tanimsiz, 0)} yön düşer ve "
            f"{sayi(d.get('sinama_sayisi', 0), 0)} tek yönlü t sınaması kalır" if tanimsiz else " tek yönlü t sınaması")
         + f". Hüküm, Benjamini–Hochberg ile düzeltilmiş q değeri {sayi(k.get('fdr_q', 0.1), 2)} altında ve hücrede en "
         f"az {k.get('asgari_olay', 20)} olay varsa verilir. Sonuç: {parca}.")
    kirp = ((((u.O.get("haber") or {}).get("cift") or {}).get(ana()) or {}).get("devam_kirpilan")) or {}
    for tf, uf in sorted(kirp.items(), key=lambda kv: int(kv[0])):
        for ufuk, olaylar in sorted(uf.items(), key=lambda kv: int(kv[0])):
            if olaylar:
                s += (f" {tf} dakikalık mumda {ufuk} dakikalık ufuk gün sonunu aşan olaylarda doldurulamaz; o gözlemler "
                      f"hücreye girmez (" + ", ".join(f"{adlar.OLAY.get(o, o)} {sayi(n, 0)}" for o, n in olaylar.items())
                      + " olay).")
    return s


def blok_devam_yetersiz(u: Uretim, ctx: dict, boyut: str = "olay_kova") -> str:
    """Bir devam tablosunda olay sayısı eşiğin altında kalan satırların sayımı (her ufukta aynıdır)."""
    d = _devam(u)
    k = d.get("kural") or {}
    asg = int(k.get("asgari_olay", 20))
    hs = [h for h in d.get("hucre") or [] if h.get("boyut") == boyut]
    if not hs:
        return ""
    uf = min(int(h["ufuk"]) for h in hs)
    satir = [h for h in hs if int(h["ufuk"]) == uf]
    alt = [h for h in satir if (h.get("n_olay") or 0) < asg]
    return (f"tablonun {sayi(len(satir), 0)} satırının {ek(len(alt), 'inde')} olay sayısı {ek(asg, 'in')} altında "
            f"(hüküm: \"yetersiz örneklem\")")


def blok_esik_payi(u: Uretim, ctx: dict, tf: str = "5", kova: str = ">2") -> str:
    """İlk haber mumunun bir kovaya düşme payı, bütün paritelerin olay ölçümlerinde (haber analizinin kova dağılımı):
    N2'nin eşiği (2 × ATR) ne kadar seyrek aşılıyor?"""
    toplam = sec = 0
    for c in PARITE:
        kd = (((((u.O.get("haber") or {}).get("cift") or {}).get(c) or {}).get("kova_dagilimi")) or {}).get(str(tf)) or {}
        for o, v in kd.items():
            toplam += sum(int(x) for x in v.values())
            sec += int(v.get(kova) or 0)
    if not toplam:
        raise SablonHatasi("esik_payi: kova dağılımı yok")
    return yuzde(sec / toplam, 0)


def blok_haber_kirilim(u: Uretim, ctx: dict, boyut: str = "olay") -> str:
    """Bir haber stratejisinin işlemleri olaya (ya da ilk mum kovasına) göre, dört paritenin birleşimi. Gözlem birimi
    olaydır: parantezde olay sayısı (aynı ABD olayı dört paritede ölçülür) ve %95 aralığı olay kümeli bootstrap. N3 ve
    N4'te haber öncesi aralığın genişliği (pip, medyan) ayrı sütunda."""
    b = ctx["B"]
    ho = (b.get("haber_olay") or {}).get(boyut) or {}
    if not ho:
        return "_Olay kırılımı yok._"
    aralik = (b.get("haber_olay") or {}).get("aralik_pip") if boyut == "olay" else None
    govde = []
    for deger in _boyut_sira(u, boyut, set(ho)):
        satir = [_boyut_ad(boyut, deger)]
        for d in ("tum", "oos"):
            x = ho[deger].get(d) or {}
            if not x.get("n"):
                satir += ["—", "—"]
                continue
            satir += [f"{sayi(x['n'], 0)} ({sayi(x.get('n_olay') or 0, 0)})",
                      f"{_hucre(x.get('r'), 'ra')} ({_hucre(x.get('ga_alt'), 'ra')} / {_hucre(x.get('ga_ust'), 'ra')})"]
        if aralik:
            satir.append(_hucre((aralik.get(deger) or {}).get("medyan"), "s1"))
        govde.append(satir)
    bas = {"olay": "Olay", "kova": "İlk mum / ATR", "trend_uyum": "Haber öncesi trend"}.get(boyut, boyut)
    basliklar = [bas, "İşlem (olay)", "Net R (%95)", "2024 →: işlem (olay)", "2024 →: net R (%95)"]
    if aralik:
        basliklar.append("Haber öncesi aralık, medyan (pip)")
    return (_tablo(basliklar, govde, ["l"] + ["r"] * (len(basliklar) - 1)) +
            f"\n\n_Dört paritenin işlemleri birlikte; %95 aralığı olay kümeli. {sayi(len(govde), 0)} satırın her biri ayrı "
            f"bir sınamadır: aralığı sıfırın dışında kalan tek bir satır şansla da çıkabilir._")


def _fomc_satirlari(u: Uretim, pencere: str):
    for c, h in sorted(((u.O.get("haber") or {}).get("cift") or {}).items(), key=lambda kv: list(PARITE).index(kv[0])
                       if kv[0] in PARITE else 99):
        oz = ((h or {}).get("fomc") or {}).get("ozet") or {}
        bp = oz.get(pencere) or {}
        if bp:
            yield c, oz, bp


def blok_fomc(u: Uretim, ctx: dict) -> str:
    """FOMC karar (14:00 → 14:30 ET) ↔ basın toplantısı (14:30 → 15:30 ET) hareketi, parite parite; ön kaydın ikinci
    penceresi (14:30 → 16:00 ET) ikinci tabloda. Toplantı sayısı dönüş oranının paydasıdır (hareketi sıfır olan
    toplantı yönsüzdür ve sayılmaz)."""
    govde = []
    for c, oz, b60 in _fomc_satirlari(u, "basin_60"):
        dn = b60.get("donus") or {}
        kb = b60.get("karar_buyukluk") or {}
        govde.append([PARITE[c], _hucre(dn.get("n"), "n"),
                      f"{_hucre(dn.get('oran'), 'yz0')} ({_hucre(dn.get('alt'), 'yz0')}–{_hucre(dn.get('ust'), 'yz0')})",
                      f"{_hucre(b60.get('korelasyon'), 'r')} ({_hucre(b60.get('korelasyon_alt'), 'r')} / "
                      f"{_hucre(b60.get('korelasyon_ust'), 'r')})"]
                     + [(f"{_hucre(kb[k].get('oran'), 'yz0')} ({sayi(kb[k].get('n'), 0)})" if (kb.get(k) or {}).get("n")
                         else "—") for k in ("<0,5", "0,5–1", ">1")])
    if not govde:
        return "_FOMC karar ↔ basın toplantısı ölçülemedi (basın toplantısı saati olan toplantı yok)._"
    t1 = _tablo(["Parite", "Toplantı", "Dönüş oranı (%95)", "Korelasyon (%95)", "Karar <0,5 ATR", "0,5–1", ">1"],
                govde, ["l", "r", "r", "r", "r", "r", "r"])
    g2 = []
    for c, oz, b90 in _fomc_satirlari(u, "basin_90"):
        dn = b90.get("donus") or {}
        g2.append([PARITE[c], _hucre(dn.get("n"), "n"),
                   f"{_hucre(dn.get('oran'), 'yz0')} ({_hucre(dn.get('alt'), 'yz0')}–{_hucre(dn.get('ust'), 'yz0')})",
                   f"{_hucre(b90.get('korelasyon'), 'r')} ({_hucre(b90.get('korelasyon_alt'), 'r')} / "
                   f"{_hucre(b90.get('korelasyon_ust'), 'r')})"])
    t2 = ("\n\nBasın penceresi 16:00'ya uzatıldığında (14:30 → 16:00 ET):\n\n" +
          _tablo(["Parite", "Toplantı", "Dönüş oranı (%95)", "Korelasyon (%95)"], g2, ["l", "r", "r", "r"])) if g2 else ""
    return t1 + t2


def blok_fomc_cumle(u: Uretim, ctx: dict) -> str:
    """FOMC tablosunun okunuşu: dönüş oranı yazı turadan, ilinti sıfırdan ayırt ediliyor mu; ve iki pencerenin
    hareket büyüklüğü (pencereler farklı uzunlukta: karar 30 dk, basın 60 dk — rastgele yürüyüşte √2 kat beklenir)."""
    satir = []
    for c, _, b60 in _fomc_satirlari(u, "basin_60"):
        dn = b60.get("donus") or {}
        if dn.get("alt") is None or b60.get("korelasyon_alt") is None:
            continue
        satir.append((c, dn, b60))
    if not satir:
        return ""
    n = len(satir)
    yt = [c for c, dn, _ in satir if dn["alt"] <= 0.5 <= dn["ust"]]
    don = [c for c, dn, _ in satir if dn["alt"] > 0.5]
    dev = [c for c, dn, _ in satir if dn["ust"] < 0.5]
    sif = [c for c, _, b in satir if b["korelasyon_alt"] <= 0 <= b["korelasyon_ust"]]
    def ad(cs):
        return ", ".join(PARITE[c] for c in cs)
    hepsi = (f"{PARITE[satir[0][0]]}'de" if n == 1 else
             f"{SAYI_AD.get(n, sayi(n, 0)).capitalize()} paritenin hiçbirinde")
    if len(yt) == n:
        cumle = [f"{hepsi} dönüş oranının %95 aralığı %50'yi dışarıda bırakmıyor: basın toplantısının ilk "
                 f"saati kararın ilk yarım saatini ne sistematik olarak tersine çeviriyor ne de sürdürüyor."]
    else:
        cumle = []
        if don:
            cumle.append(f"Dönüş oranı {ad(don)} paritesinde yazı turadan sık: basın toplantısı kararın ilk hareketini "
                         f"çoğunlukla tersine çeviriyor.")
        if dev:
            cumle.append(f"{ad(dev)} paritesinde dönüş yazı turadan seyrek: basın toplantısı kararın ilk hareketini "
                         f"çoğunlukla sürdürüyor.")
        if yt:
            cumle.append(f"{ad(yt)} paritesinde dönüş oranı yazı turadan ayırt edilemiyor.")
    ayr = [c for c, _, _ in satir if c not in sif]
    if not ayr:
        cumle.append("İki hareketin ilintisi hiçbir paritede sıfırdan ayırt edilemiyor.")
    else:
        isaret = {c: ("artı (basın toplantısı kararın yönünü sürdürüyor)" if b["korelasyon"] > 0 else
                      "eksi (basın toplantısı kararın yönünü tersine çeviriyor)") for c, _, b in satir}
        cumle.append("İki hareketin ilintisi " + "; ".join(f"{PARITE[c]}'de {isaret[c]}" for c in ayr)
                     + (f"; {ad(sif)} paritesinde sıfırdan ayırt edilemiyor." if sif else "."))
    kok2 = math.sqrt(2)
    oran = [(c, b["ort_mutlak_basin_atr"] / b["ort_mutlak_karar_atr"]) for c, _, b in satir
            if b.get("ort_mutlak_karar_atr")]
    if oran:
        alt = [c for c, r in oran if r < kok2]
        ornek = next((x for x in satir if x[0] == ana()), satir[0])
        b = ornek[2]
        oran_ornek = b["ort_mutlak_basin_atr"] / b["ort_mutlak_karar_atr"]
        cumle.append(f"Hareketin büyüklüğü: {PARITE[ornek[0]]}'de basın toplantısının ilk saatindeki ortalama mutlak "
                     f"hareket {sayi(b['ort_mutlak_basin_atr'], 2)}, kararın ilk yarım saatindeki "
                     f"{sayi(b['ort_mutlak_karar_atr'], 2)} günlük ATR (oran {sayi(oran_ornek, 2)}). Basın penceresi iki kat uzun "
                     f"olduğu için oran "
                     f"tek başına bir şey söylemez: fiyat rastgele yürüseydi bile iki kat uzun pencerede "
                     f"{sayi(kok2, 2)} kat hareket beklenirdi. "
                     + (f"{(SAYI_AD.get(n, str(n)) + ' paritenin hepsinde').capitalize() if len(alt) == n else ad(alt) + ' paritesinde'} oran bunun "
                        f"altında: dakika başına kararın yarım saati basın toplantısının ilk saatinden daha hareketli."
                        if alt else "Oran hiçbir paritede bunun altında değil: basın toplantısı dakika başına da "
                                    "kararın yarım saati kadar hareketli.")
                     + (f" {ad([c for c, _ in oran if c not in alt])} paritesinde değil." if alt and len(alt) < len(oran)
                        else ""))
    s90 = [(c, b90.get("donus") or {}, b90) for c, _, b90 in _fomc_satirlari(u, "basin_90")
           if (b90.get("donus") or {}).get("alt") is not None and b90.get("korelasyon_alt") is not None]
    if s90:
        yt90 = [c for c, dn, _ in s90 if dn["alt"] <= 0.5 <= dn["ust"]]
        sif90 = [c for c, _, b in s90 if b["korelasyon_alt"] <= 0 <= b["korelasyon_ust"]]
        if len(yt90) == len(s90) and len(sif90) == len(s90):
            cumle.append("Basın penceresi 16:00'ya uzatıldığında da sonuç aynı: dönüş oranı hiçbir paritede yazı "
                         "turadan, ilinti sıfırdan ayırt edilemiyor.")
        else:
            cumle.append("Basın penceresi 16:00'ya uzatıldığında dönüş oranı " +
                         (f"{ad(yt90)} paritesinde yazı turadan ayırt edilemiyor" if yt90 else
                          "hiçbir paritede yazı turadan ayırt edilemez değil") +
                         ("; ilinti " + (f"{ad(sif90)} paritesinde sıfırdan ayırt edilemiyor" if sif90 else
                                         "her paritede sıfırdan ayırt ediliyor")) + ".")
    return " ".join(cumle)


def hukum_sayim_yaz(b: dict, anahtar: str = "hukum") -> str:
    """Parite başına hükümlerin sayımı: "2 zayıf · 2 çalışmıyor" (sıra: çalışıyor, zayıf, çalışmıyor, ölçülemedi)."""
    say: dict = {}
    for c in _ciftler(b):
        h = (b["cift"][c].get("varsayilan") or {}).get(anahtar) or "olculemedi"
        say[h] = say.get(h, 0) + 1
    return " · ".join(f"{say[h]} {adlar.HUKUM[h]}" for h in ("calisiyor", "zayif", "calismiyor", "olculemedi")
                      if say.get(h)) or "—"


def blok_ders_ozet(u: Uretim, ctx: dict, *birimler: str) -> str:
    """Dersin stratejileri yan yana: havuzun örneklem dışı net R'si ve aralığı, ana paritenin net pipi, parite
    hükümlerinin sayımı, maliyet bayrağı (iki dönem), ana paritenin başabaş kayması ve R birimi. Birim verilmezse bu
    derste işlenenler."""
    liste = list(birimler) or list(u.birimler)
    if liste == ["hepsi"]:
        liste = _butun_birimler(u)
    c0 = ana()
    govde = []
    for bid in liste:
        b = (u.O.get("birim") or {}).get(bid)
        if not b:
            continue
        h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        cs = _ciftler(b)
        my = sum(1 for c in cs if (b["cift"][c].get("varsayilan") or {}).get("maliyet_yiyor"))
        myo = sum(1 for c in cs if (b["cift"][c].get("varsayilan") or {}).get("maliyet_yiyor_oos"))
        e = ((b.get("cift") or {}).get(c0) or {}).get("varsayilan") or {}
        govde.append([adlar.BIRIM[bid][1], _hucre(h.get("n"), "n"),
                      f"{_hucre(h.get('beklenti_r'), 'ra')} ({_hucre(h.get('ga_alt'), 'ra')} / {_hucre(h.get('ga_ust'), 'ra')})",
                      _hucre((e.get("oos") or {}).get("beklenti_pip"), "p1"), hukum_sayim_yaz(b),
                      f"{sayi(my, 0)} · {sayi(myo, 0)}", _basabas_hucre(e, "_oos"),
                      _hucre((e.get("oos") or {}).get("risk_pip"), "s1")])
    if not govde:
        return "_Özet için strateji yok._"
    p0 = PARITE[c0]
    return (_tablo(["Strateji", "İşlem (havuz)", "Net R, havuz (%95)", f"Net pip, {p0}", "Parite hükümleri",
                    "Maliyet yiyor (bütün · 2024 →)", f"Başabaş kayma, {p0} (pip)", f"R birimi medyanı, {p0} (pip)"],
                   govde, ["l", "r", "r", "r", "l", "r", "r", "r"]) +
            "\n\n_Örneklem dışı (2024 →), önceden kayıtlı varsayılan. Tanımlar giriş dersinde._")


def _butun_birimler(u: Uretim) -> list[str]:
    """Ölçülen bütün birimler, derslerin sırasıyla (seans, yapı, fade, haber, akış)."""
    var = (u.O.get("birim") or {})
    sira = [b for bl in adlar.DERS_BIRIM.values() for b in bl if b in var]
    return sira + [b for b in var if b not in sira]


def blok_hukum_matris(u: Uretim, ctx: dict) -> str:
    """Strateji × parite: önceden kayıtlı varsayılanın örneklem dışı net R'si ve hükmü; son sütun havuz."""
    govde = []
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        satir = [adlar.BIRIM[bid][1]]
        for c in PARITE:
            v = ((b.get("cift") or {}).get(c) or {}).get("varsayilan") or {}
            o = v.get("oos") or {}
            satir.append(f"{_hucre(o.get('beklenti_r'), 'ra')} · {adlar.HUKUM.get(v.get('hukum') or 'olculemedi')}"
                         if v else "—")
        h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        satir.append(_hucre(h.get("beklenti_r"), "ra"))
        govde.append(satir)
    if not govde:
        return "_Strateji yok._"
    return _tablo(["Strateji"] + list(PARITE.values()) + ["Havuz"], govde, ["l"] + ["r"] * (len(PARITE) + 1))


def _hukum_sayimi_hepsi(u: Uretim) -> dict:
    say = {"calisiyor": 0, "zayif": 0, "calismiyor": 0, "olculemedi": 0, "maliyet": 0, "maliyet_oos": 0, "parite": 0}
    tum = {"calisiyor": 0, "zayif": 0, "calismiyor": 0, "olculemedi": 0}
    kural = {"calisiyor": set(), "zayif": set()}
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            v = (b["cift"][c].get("varsayilan") or {})
            h = v.get("hukum") or "olculemedi"
            say[h] = say.get(h, 0) + 1
            say["parite"] += 1
            say["maliyet"] += 1 if v.get("maliyet_yiyor") else 0
            say["maliyet_oos"] += 1 if v.get("maliyet_yiyor_oos") else 0
            ht = v.get("hukum_tum") or "olculemedi"
            tum[ht] = tum.get(ht, 0) + 1
            if h in kural:
                kural[h].add(bid)
    return {"say": say, "tum": tum, "kural": kural, "birim": len(_butun_birimler(u))}


def blok_genel_hukum(u: Uretim, ctx: dict) -> str:
    """Bütün kuralların hüküm sayımı (strateji × parite), iki dönemde; havuzda aralığı sıfırın üstünde kalan kurallar;
    maliyet bayrağı iki dönemde."""
    g = _hukum_sayimi_hepsi(u)
    s_, t_, k = g["say"], g["tum"], g["kural"]

    def sayim(d):
        return (f"{sayi(d['calisiyor'], 0)} çalışıyor, {sayi(d['zayif'], 0)} zayıf, {sayi(d['calismiyor'], 0)} çalışmıyor"
                + (f", {sayi(d['olculemedi'], 0)} ölçülemedi" if d["olculemedi"] else ""))
    parca = [f"{sayi(g['birim'], 0)} kural ve {sayi(s_['parite'], 0)} kural–parite bileşiminde önceden kaydın hükmü, "
             f"örneklem dışında (2024 →): {sayim(s_)}. Bütün dönemde (varsayılan için o da örneklem dışıdır): "
             f"{sayim(t_)}."]
    for h, ad in (("calisiyor", "çalışıyor"), ("zayif", "zayıf")):
        if k[h]:
            parca.append(f"En az bir paritede {ad} (2024 →): " + ", ".join(adlar.BIRIM[b][1] for b in _butun_birimler(u)
                                                                       if b in k[h]) + ".")
    pozitif = [b for b in _butun_birimler(u)
               if (((u.O["birim"][b].get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}).get("ga_alt") is not None
               and u.O["birim"][b]["havuz"]["varsayilan"]["oos"]["ga_alt"] > 0]
    parca.append("Havuzda %95 aralığının alt ucu sıfırın üstünde kalan kural: " +
                 (", ".join(adlar.BIRIM[b][1] for b in pozitif) if pozitif else "yok") + ".")
    if s_["maliyet"] or s_["maliyet_oos"]:
        parca.append(f"Maliyet bayrağı (brüt aralığı sıfırın üstünde, net sonuç sıfır ya da altında) bütün dönemde "
                     f"{sayi(s_['maliyet'], 0)}, 2024 → penceresinde {sayi(s_['maliyet_oos'], 0)} bileşimde yanıyor.")
    return " ".join(parca)


def blok_hangi_kosul(u: Uretim, ctx: dict) -> str:
    """Karşılaştırma dersinin "hangi koşulda hangisi" tablosu: bütün kurallarda kontrol listesine aday olarak giren
    koşullar (en az iki paritede aynı kovayla tutan), her parite için örneklem dışı R'si ve işlem sayısıyla. Bir karar
    tablosu değildir: adayların hiçbiri hükmün öbür iki şartını (güven aralığı, rastgele yön) taşımaz."""
    govde, kural = [], 0
    for bid in _butun_birimler(u):
        ad_ = kosul_adaylari(u.O["birim"][bid])
        if ad_:
            kural += 1
        for x in ad_:
            govde.append([adlar.BIRIM[bid][1], f"{adlar.KOSUL.get(x['degisken'], x['degisken'])}: {_kova_yaz(x['kova'])}",
                          "; ".join(f"{PARITE[c]} {_hucre(k.get('oos_secilen_r'), 'ra')} ({sayi(k.get('oos_secilen_n') or 0, 0)})"
                                    for c, k in x["pariteler"])])
    if not govde:
        return "Hiçbir kuralda iki paritede aynı kovayla tutan bir koşul yok."
    return (_tablo(["Kural", "Koşul: kova", "Tutan pariteler: örneklem dışı R (işlem)"], govde, ["l", "l", "l"]) +
            f"\n\n_{sayi(len(_butun_birimler(u)), 0)} kuralın {sayi(kural, 0)} tanesinde en az bir aday var; toplam "
            f"{sayi(len(govde), 0)} aday. Aday: örneklem içinde seçilip örneklem dışında en az iki paritede aynı kovayla "
            f"tutan koşul._")


def blok_maliyet_ozet(u: Uretim, ctx: dict) -> str:
    """Parite parite: örneklem dışında brüt, yalnız makas ve dört kayma kademesinde net beklentisi artı olan kural
    sayısı."""
    kademe = [str(x) for x in (u.O["kunye"].get("kayma_pip") or [0.0, 0.5, 1.0, 2.0])]
    govde = []
    for c in PARITE:
        n = brut = ym = 0
        net = {kk: 0 for kk in kademe}
        for bid in _butun_birimler(u):
            v = ((u.O["birim"][bid].get("cift") or {}).get(c) or {}).get("varsayilan") or {}
            o = v.get("oos") or {}
            if not o.get("n"):
                continue
            n += 1
            brut += 1 if (o.get("brut_r") or 0) > 0 else 0
            ym += 1 if ((((v.get("yalniz_makas") or {}).get("oos") or {}).get("beklenti_r")) or 0) > 0 else 0
            for kk in kademe:
                x = (((v.get("maliyet") or {}).get(kk) or {}).get("oos") or {}).get("beklenti_r")
                net[kk] += 1 if (x is not None and x > 0) else 0
        if n:
            govde.append([PARITE[c], _hucre(n, "n"), _hucre(brut, "n"), _hucre(ym, "n")] +
                         [_hucre(net[kk], "n") for kk in kademe])
    if not govde:
        return "_Maliyet ölçülmedi._"
    return (_tablo(["Parite", "Kural", "Brüt artı", "Yalnız makasla artı"] +
                   [f"Net artı, kayma {sayi(float(kk), 1)}" for kk in kademe], govde, ["l"] + ["r"] * (3 + len(kademe))) +
            f"\n\n_Örneklem dışı (2024 →). Kayma kademeleri dolum başına; haber penceresindeki dolumlar her kademede "
            f"ayrıca {sayi(u.O['kunye']['haber_kayma_pip'], 1)} pip öder, \"yalnız makas\" sütununda o da sıfırdır._")


def blok_rastgele_ozet(u: Uretim, ctx: dict) -> str:
    """Parite parite: rastgele yön dağılımında örneklem dışı sonucu eşiğin (≥ 95. yüzdelik) üstünde kalan kural sayısı."""
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    parca, eksi = [], []
    for c in PARITE:
        n = ust = 0
        adlar_ = []
        for bid in _butun_birimler(u):
            v = ((u.O["birim"][bid].get("cift") or {}).get(c) or {}).get("varsayilan") or {}
            r = ((v.get("rastgele") or {}).get("oos") or {})
            if r.get("yuzdelik") is None or not math.isfinite(r["yuzdelik"]):
                continue
            n += 1
            if r["yuzdelik"] >= esik:
                ust += 1
                adlar_.append(f"{adlar.BIRIM[bid][1]} {sayi(r['yuzdelik'], 1)}")
                net = (v.get("oos") or {}).get("beklenti_r")
                if net is not None and net <= 0:
                    ort = r.get("ort")
                    eksi.append(f"{adlar.BIRIM[bid][1]} ({PARITE[c]}: kendisi {_hucre(net, 'ra')} R"
                                + (f", rastgele yönün ortalaması {_hucre(ort, 'ra')} R" if ort is not None else "")
                                + ")")
        if n:
            parca.append(f"{PARITE[c]}: {sayi(ust, 0)} / {sayi(n, 0)}" + (f" ({', '.join(adlar_)})" if adlar_ else ""))
    if not parca:
        return ""
    s = (f"Örneklem dışı sonucu rastgele yön dağılımında ≥ {esik}. yüzdelikte kalan kural sayısı — "
         + "; ".join(parca) + ". Hiçbir şeyin çalışmadığı bir dünyada bile her yirmi sınamadan biri bu eşiği "
         "şansla geçer.")
    if eksi:
        s += (" Eşiği geçip net sonucu yine eksi kalan: " + "; ".join(eksi) + ". Rastgele yönlü işlemler de aynı "
              "makası ödediği için dağılımın ortalaması sıfırın altında kalır; o dağılımı yenmek yön seçiminin bir "
              "şey kattığını söyler, maliyeti karşıladığını söylemez.")
    return s


def blok_korelasyon_cumle(u: Uretim, ctx: dict, kac: str = "5") -> str:
    """Stratejiler arası günlük R korelasyonunun özeti (bütün dönem): en yüksek |ρ|'lu çiftler ve eşik sayımı."""
    kor = u.O.get("korelasyon") or {}
    if not kor.get("tum"):
        return "Korelasyon ölçülmedi."
    bs, m = kor["birimler"], kor["tum"]
    ciftler = [(abs(m[i][j]), m[i][j], bs[i], bs[j]) for i in range(len(bs)) for j in range(i + 1, len(bs))
               if m[i][j] is not None]
    ciftler.sort(key=lambda x: -x[0])
    esik = sum(1 for x in ciftler if x[0] >= 0.25)
    ust = "; ".join(f"{adlar.BIRIM[a][1]} × {adlar.BIRIM[b_][1]} {_hucre(v, 'r')}" for _, v, a, b_ in ciftler[:int(kac)])
    return (f"{sayi(len(bs), 0)} kuralın {sayi(len(ciftler), 0)} çiftinden {sayi(esik, 0)} tanesinde günlük R "
            f"korelasyonu mutlak değerce 0,25'i aşıyor. En yüksek {kac} çift: {ust}.")


def blok_kosul_genel(u: Uretim, ctx: dict) -> str:
    """Koşul analizinin bütün kural × parite bileşimlerinde değişken değişken sayımı: gerçek seçimin ve ters seçimin
    (örneklem içinde ortalamanın altındaki kovalar) örneklem dışı ölçütü geçme sayısı."""
    say: dict = {}
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            for k in ((b["cift"][c].get("varsayilan") or {}).get("kosul") or []):
                d = say.setdefault(k["degisken"], {"sinanan": 0, "tuttu": 0, "ters_sinanan": 0, "ters_tuttu": 0})
                if k.get("hukum") in ("tuttu", "tutmadi"):
                    d["sinanan"] += 1
                    d["tuttu"] += 1 if k["hukum"] == "tuttu" else 0
                t = k.get("ters_secim") or {}
                if t.get("hukum") in ("tuttu", "tutmadi"):
                    d["ters_sinanan"] += 1
                    d["ters_tuttu"] += 1 if t["hukum"] == "tuttu" else 0
    if not say:
        return "_Koşul analizi yok._"
    ters_var = any(d["ters_sinanan"] for d in say.values())
    sira = [k for k in adlar.KOSUL if k in say] + [k for k in say if k not in adlar.KOSUL]
    govde = []
    for k in sira:
        d = say[k]
        satir = [adlar.KOSUL.get(k, k), _hucre(d["sinanan"], "n"), _hucre(d["tuttu"], "n")]
        if ters_var:
            satir += [_hucre(d["ters_sinanan"], "n"), _hucre(d["ters_tuttu"], "n")]
        govde.append(satir)
    top = {kk: sum(d[kk] for d in say.values()) for kk in ("sinanan", "tuttu", "ters_sinanan", "ters_tuttu")}
    govde.append(["Toplam", _hucre(top["sinanan"], "n"), _hucre(top["tuttu"], "n")] +
                 ([_hucre(top["ters_sinanan"], "n"), _hucre(top["ters_tuttu"], "n")] if ters_var else []))
    bas = ["Değişken", "Sınanan (seçim)", "Tuttu"] + (["Sınanan (ters seçim)", "Tuttu (ters seçim)"] if ters_var else [])
    return _tablo(bas, govde, ["l"] + ["r"] * (len(bas) - 1))


def kosul_sayim(O: dict) -> dict:
    """Koşul analizinin bütün kural × parite × değişken bileşimlerinde gerçek ve ters seçimin sayımı; eşli kıyas
    için yalnız birinin tuttuğu bileşimler (a: gerçek tuttu, ters tutmadı · b: tersi)."""
    t = {"sinanan": 0, "tuttu": 0, "ters_sinanan": 0, "ters_tuttu": 0, "a": 0, "b": 0}
    for b in (O.get("birim") or {}).values():
        for v in (b.get("cift") or {}).values():
            for k in ((v.get("varsayilan") or {}).get("kosul") or []):
                g = k.get("hukum")
                ts = (k.get("ters_secim") or {}).get("hukum")
                if g in ("tuttu", "tutmadi"):
                    t["sinanan"] += 1
                    t["tuttu"] += g == "tuttu"
                if ts in ("tuttu", "tutmadi"):
                    t["ters_sinanan"] += 1
                    t["ters_tuttu"] += ts == "tuttu"
                if g in ("tuttu", "tutmadi") and ts in ("tuttu", "tutmadi"):
                    t["a"] += g == "tuttu" and ts == "tutmadi"
                    t["b"] += g == "tutmadi" and ts == "tuttu"
    t["p"] = _mcnemar_p(t["a"], t["b"])
    t["ayirt"] = bool(t["a"] > t["b"] and t["p"] < 0.05)
    # Ters yön: örneklem içinde KÖTÜ görünen kovalar örneklem dışında daha sık tutuyor — kova sıralaması dönüyor.
    t["ters_ustun"] = bool(t["b"] > t["a"] and t["p"] < 0.05)
    return t


def toplamlar(O: dict, ON: dict) -> dict:
    """Karşılaştırma dersinin sayımları (bütün kural × parite bileşimleri, önceden kayıtlı varsayılan, örneklem
    dışı). Şablonun iddiaları ve koşulları bunları okur: metindeki "çoğu", "az" gibi sözcükler sayıya bağlanır."""
    esik = (ON.get("hukum") or {}).get("rastgele_esik_yuzdelik", 95)
    t = {k: 0 for k in ("bilesim", "brut_arti", "brut_arti_makas_eksi", "brut_arti_sifir_eksi", "brut_arti_net_eksi",
                        "rastgele_n", "rastgele_ust", "arti_n", "arti_rastgele_n", "arti_rastgele_alt", "dsr_n",
                        "dsr_ust", "dsr_gurultu_ust", "secilen_sr_arti", "calisiyor")}
    for b in (O.get("birim") or {}).values():
        for v in (b.get("cift") or {}).values():
            va = v.get("varsayilan") or {}
            o = va.get("oos") or {}
            if not o.get("n"):
                continue
            t["bilesim"] += 1
            t["calisiyor"] += va.get("hukum") == "calisiyor"
            brut, net = o.get("brut_r"), o.get("beklenti_r")
            m0 = ((((va.get("maliyet") or {}).get("0.0") or {}).get("oos")) or {}).get("beklenti_r")
            ym = (((va.get("yalniz_makas") or {}).get("oos")) or {}).get("beklenti_r")
            if brut is not None and brut > 0:
                t["brut_arti"] += 1
                t["brut_arti_makas_eksi"] += ym is not None and ym <= 0
                t["brut_arti_sifir_eksi"] += m0 is not None and m0 <= 0
                t["brut_arti_net_eksi"] += net is not None and net <= 0
            if net is not None and net > 0:
                t["arti_n"] += 1
            r = ((va.get("rastgele") or {}).get("oos")) or {}
            if r.get("yuzdelik") is not None and math.isfinite(r["yuzdelik"]):
                t["rastgele_n"] += 1
                t["rastgele_ust"] += r["yuzdelik"] >= esik
                if net is not None and net > 0:
                    t["arti_rastgele_n"] += 1
                    t["arti_rastgele_alt"] += r["yuzdelik"] < esik
            d = ((v.get("secilen") or {}).get("dsr")) or {}
            if d.get("dsr") is not None and math.isfinite(d["dsr"]):
                t["dsr_n"] += 1
                t["dsr_ust"] += d["dsr"] >= 0.95
                t["dsr_gurultu_ust"] += (d.get("dsr_gurultu") or 0) >= 0.95
                t["secilen_sr_arti"] += (d.get("sr_yillik") or 0) > 0
    t = {k: int(v) for k, v in t.items()}

    def oran(a: str, b_: str):
        return t[a] / t[b_] if t[b_] else None
    t.update({"makas_brut_oran": oran("brut_arti_makas_eksi", "brut_arti"),
              "sifir_brut_oran": oran("brut_arti_sifir_eksi", "brut_arti"),
              "net_eksi_brut_oran": oran("brut_arti_net_eksi", "brut_arti"),
              "rastgele_ust_oran": oran("rastgele_ust", "rastgele_n"),
              "rastgele_beklenen": round(t["rastgele_n"] * (100 - esik) / 100),
              "rastgele_binom_p": _binom_ust_p(t["rastgele_ust"], t["rastgele_n"], (100 - esik) / 100),
              "arti_rastgele_alt_oran": oran("arti_rastgele_alt", "arti_rastgele_n"),
              "dsr_ust_oran": oran("dsr_ust", "dsr_n"),
              "kosul": kosul_sayim(O),
              "kombinasyon": int(sum(len(b.get("kombinasyon") or []) if isinstance(b.get("kombinasyon"), list)
                                     else int(b.get("kombinasyon") or 0) for b in (O.get("birim") or {}).values())),
              "birim": len(O.get("birim") or {}),
              "fomc_basin": int(((((O.get("takvim") or {}).get("sayim")) or {}).get("FOMC_basin") or {})
                                .get("toplam") or 0),
              "inmeyen_gun": int(sum((v.get("gun_hata") or 0) for v in (((O.get("veri") or {}).get("arsiv")) or {})
                                     .values())),
              "eksik_birim": int(sum(1 for v in (((O.get("veri") or {}).get("arsiv")) or {}).values()
                                     if not v.get("tam")))})
    return t


def _binom_ust_p(k: int, n: int, q: float) -> float | None:
    """P(X ≥ k), X ~ Binom(n, q): n sınamada şansla en az k geçiş."""
    if not n:
        return None
    return float(sum(math.comb(n, i) * q ** i * (1 - q) ** (n - i) for i in range(k, n + 1)))


def _mcnemar_p(a: int, b: int) -> float:
    """Kesin McNemar (iki yönlü binom, p = 1/2): uyuşmayan çiftlerde a ↔ b."""
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def blok_kosul_genel_cumle(u: Uretim, ctx: dict) -> str:
    """Gerçek seçim ile ters seçimin (örneklem içinde ortalamanın altındaki kovalar) geçme oranları ve eşli kıyası.
    Kova farkları yalnız gürültüyse iki seçim aynı sıklıkla tutar. Kıyas eşlidir: aynı kural, parite ve değişkende
    iki seçimden yalnız birinin tuttuğu bileşimler sayılır (kesin McNemar). Bileşimler bağımsız değildir (aynı
    kuralın değişkenleri aynı işlemleri paylaşır); p bir ölçüdür, bir eşik kuralı değil."""
    t = kosul_sayim(u.O)
    if not t["sinanan"]:
        return "Koşul analizi yok."
    s1 = (f"Örneklem içinde seçilen kovalar {sayi(t['sinanan'], 0)} sınamanın {sayi(t['tuttu'], 0)} tanesinde "
          f"({yuzde(t['tuttu'] / t['sinanan'], 0)}) örneklem dışı ölçütü geçti.")
    if not t["ters_sinanan"]:
        return s1 + " Ters seçim bu ölçümde yok."
    s2 = (f" Örneklem içinde en kötü kovalar seçilseydi aynı ölçüt {sayi(t['ters_sinanan'], 0)} sınamanın "
          f"{sayi(t['ters_tuttu'], 0)} tanesinde ({yuzde(t['ters_tuttu'] / t['ters_sinanan'], 0)}) geçerdi. "
          f"İki seçimden yalnız birinin tuttuğu bileşimlerde gerçek seçim {sayi(t['a'], 0)}, ters seçim "
          f"{sayi(t['b'], 0)} kez tuttu (kesin McNemar p {_hucre(t['p'], 'p')}).")
    if t["ayirt"]:
        s3 = (" Gerçek seçim ters seçimden daha sık tutuyor: örneklem içinde iyi görünen kovaların bir kısmı örneklem "
              "dışında da iyi. Hangisinin tuttuğu yine tek tek okunmalıdır.")
    elif t["ters_ustun"]:
        s3 = (" Ters seçim gerçek seçimden daha sık tutuyor: örneklem içindeki kova sıralaması örneklem dışında "
              "sistematik olarak tersine dönüyor. Bu kurallarda bir koşula göre işlem seçmek, toplu olarak, örneklem "
              "dışında daha kötü kovayı seçmek demekti; tek tek \"tuttu\" hücreleri bir karar kuralı değildir. "
              "Bileşimler bağımsız değildir (aynı kuralın değişkenleri aynı işlemleri paylaşır), p bir ölçüdür.")
    else:
        s3 = (" Gerçek seçim ters seçimden ayırt edilemiyor: tutan koşulların çoğu, gürültünün örneklem dışında da "
              "sıfırın üstünde kalabilmesiyle açıklanır. Tek tek \"tuttu\" hücreleri bir karar kuralı değildir.")
    return s1 + s2 + s3


def blok_havuz_cumle(u: Uretim, ctx: dict) -> str:
    """Havuzun (aynı kural bütün paritelerde birlikte) örneklem dışı okunuşu ve örneklem içi karşılığı. Hüküm kuralı
    değil, aralığın okunuşu: aralık sıfırın üstünde mi, altında mı, sıfırı kapsıyor mu. Aralık gün kümelidir."""
    b = ctx["B"]
    h = ctx.get("H") or {}
    oos, ic = h.get("oos") or {}, h.get("is") or {}
    n_p = len(_ciftler(b))
    r, alt, ust = oos.get("beklenti_r"), oos.get("ga_alt"), oos.get("ga_ust")
    if r is None or not oos.get("n"):
        return "Havuz örneklem dışında ölçülemedi (işlem yok)."
    if r > 0 and alt is not None and alt > 0:
        s = (f"Havuzun örneklem dışı aralığı sıfırın üstünde: kuralın {n_p} paritede birlikte, maliyetten sonra "
             f"bir kenarı var.")
    elif r > 0:
        s = ("Havuzun örneklem dışı ortalaması sıfırın üstünde ama aralığı sıfırı kapsıyor: ortalama bu örneklem "
             "büyüklüğünde şanstan ayırt edilemiyor.")
    elif ust is not None and ust >= 0:
        s = ("Havuzun örneklem dışı ortalaması sıfırın altında ama aralığı sıfırı kapsıyor: kayıp da bu örneklem "
             "büyüklüğünde şanstan ayırt edilemiyor; bir kenar yok.")
    else:
        s = (f"Havuzun örneklem dışı aralığı bütünüyle sıfırın altında: kural maliyetten sonra {n_p} paritede birlikte "
             f"kaybettiriyor.")
    if ic.get("n"):
        k = u.O["kunye"]
        s += (f" Örneklem içinde ({k['baslangic'][:4]}–{k['ic_bitis'][:4]}) {sayi(ic['n'], 0)} işlemde işlem başına "
              f"{_hucre(ic.get('beklenti_r'), 'ra')} R (%95 aralığı {_hucre(ic.get('ga_alt'), 'ra')} / "
              f"{_hucre(ic.get('ga_ust'), 'ra')}).")
    return s


def blok_tf_okuma(u: Uretim, ctx: dict) -> str:
    """Zaman dilimi figürünün okunuşu: örneklem dışında her paritede en iyi ve en kötü mum uzunluğu. NY IB'de 60
    dakikalık mumda ilk denge penceresi mumun kendisidir; haber kurallarında haber kayması yalnız ilk 15 dakikada
    uygulandığı için kıyas haber kayması olmadan da verilir."""
    b = ctx["B"]
    satir, esleme = [], False
    for c in _ciftler(b):
        tf = b["cift"][c].get("tf") or {}
        d = {k: (v.get("oos") or {}).get("beklenti_r") for k, v in tf.items()
             if (v.get("oos") or {}).get("beklenti_r") is not None}
        esleme = esleme or any(v.get("esleme") for v in tf.values())
        if d:
            en = max(d, key=d.get)
            satir.append(f"{PARITE[c]} " + " · ".join(f"{k} dk {_hucre(d[k], 'ra')}" for k in sorted(d, key=int))
                         + f" (en iyi {en} dk)")
    if not satir:
        return ""
    s = "Örneklem dışında, işlem başına net R: " + "; ".join(satir) + "."
    if esleme:
        s += (" 60 dakikalık mumda ilk denge penceresi mumun kendisidir (\"tek mum\" ile \"60 dk\" aynı penceredir); "
              "kıyas o satırla yapıldı.")
    hk = {c: b["cift"][c].get("tf_haber_kaymasiz") or {} for c in _ciftler(b)}
    if any(hk.values()):
        c0 = ana()
        x = hk.get(c0) or {}
        pay = " · ".join(f"{k} dk {yuzde(v.get('haber_payi') or 0, 0)}" for k, v in sorted(x.items(), key=lambda kv: int(kv[0])))
        r = " · ".join(f"{k} dk {_hucre(v.get('oos'), 'ra')}" for k, v in sorted(x.items(), key=lambda kv: int(kv[0])))
        s += (f" Haber kayması yalnız olaydan sonraki 15 dakikadaki dolumlara uygulanır; girişlerin haber penceresinde "
              f"olma payı {PARITE[c0]}'de {pay}. Haber kayması sıfırken {PARITE[c0]}'de örneklem dışı net R: {r}.")
    return s


def blok_izgara_okuma(u: Uretim, ctx: dict) -> str:
    """Izgaranın tamamının okunuşu (ısı haritası iki boyutluk bir kesittir): her paritede kaç kombinasyon örneklem
    içinde, dışında ve ikisinde birden net artı."""
    b = ctx["B"]
    satir = []
    for c in _ciftler(b):
        z = b["cift"][c].get("izgara_ozet") or {}
        if not z.get("n"):
            continue
        satir.append(f"{PARITE[c]} {sayi(z['is_arti'], 0)} · {sayi(z['oos_arti'], 0)} · {sayi(z['ikisi_arti'], 0)}")
    if not satir:
        return ""
    n = int(b.get("kombinasyon") or 0)
    return (f"Izgaranın {sayi(n, 0)} kombinasyonundan net beklentisi artı olanlar (örneklem içi · dışı · ikisi birden): "
            + "; ".join(satir) + ".")


def blok_saat_okuma(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Giriş saati figürünün okunuşu (ana parite, bütün dönem): en az 30 işlemli saatlerde en iyi ve en kötü saat."""
    cift = cift or ana()
    v = (((ctx["B"].get("cift") or {}).get(cift) or {}).get("varsayilan")) or {}
    st = {int(h): x for h, x in (v.get("saat_tsi") or {}).items() if (x.get("n") or 0) >= 30}
    if len(st) < 2:
        return ""
    en = max(st, key=lambda h: st[h]["beklenti_r"])
    ek_ = min(st, key=lambda h: st[h]["beklenti_r"])
    arti = sum(1 for x in st.values() if x["beklenti_r"] > 0)
    return (f"{PARITE[cift]}'de, bütün dönemde ve en az 30 işlemli saatlerde: en iyi giriş saati {en:02d}:00 TSİ "
            f"({_hucre(st[en]['beklenti_r'], 'ra')} R, {sayi(st[en]['n'], 0)} işlem), en kötüsü {ek_:02d}:00 TSİ "
            f"({_hucre(st[ek_]['beklenti_r'], 'ra')} R, {sayi(st[ek_]['n'], 0)} işlem); {sayi(len(st), 0)} saatin "
            f"{sayi(arti, 0)} tanesinde artı. Saat kovaları ayrı birer sınamadır; en iyi saat şansla da en iyi çıkar.")


def blok_kuyruk(u: Uretim, ctx: dict) -> str:
    """Ortalama R'nin kuyruğa duyarlılığı (betimleyici; hükmü değiştirmez): örneklem dışı ortalama, en iyi bir ve üç
    işlem çıkarılınca, ve beklenen maliyeti riskin yarısını aşan işlemler çıkarılınca."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        k = (((b["cift"][c].get("varsayilan") or {}).get("kuyruk")) or {}).get("oos") or {}
        if not k.get("n") or k.get("r") is None:
            continue
        govde.append([PARITE[c], _hucre(k["r"], "ra"), _hucre(k.get("r_tek_haric"), "ra"),
                      _hucre(k.get("r_uc_haric"), "ra"),
                      f"{_hucre(k.get('r_pahali_haric'), 'ra')} ({yuzde(k.get('pay_pahali') or 0, 0)} çıktı)",
                      f"{_hucre(k.get('en_iyi_r'), 'ra')} ({_pip(round(k.get('en_iyi_R_pip') or 0, 2))} pip risk)"])
    if not govde:
        return ""
    return (_tablo(["Parite", "Net R", "En iyi işlem hariç", "En iyi üç hariç", "Maliyeti riskin yarısını aşanlar hariç",
                    "En iyi işlem"], govde, ["l", "r", "r", "r", "r", "r"]) +
            "\n\n_Örneklem dışı (2024 →), işlem başına net R. Beklenen maliyet: girişteki makas, iki dolumun temel "
            "kayması ve giriş haber penceresindeyse haber kayması. Betimleyicidir; hüküm değişmez._")


def blok_varyant(u: Uretim, ctx: dict, param: str) -> str:
    """Bir parametrenin değerleri (öbür parametreler önceden kayıtlı varsayılanda), dört parite, iki örneklem: ızgaranın
    kendi satırları."""
    b = ctx["B"]
    v = b.get("varsayilan") or {}
    degerler: list = []
    for c in _ciftler(b):
        for d in ((b["cift"][c].get("varyant") or {}).get(param) or {}):
            if d not in degerler:
                degerler.append(d)
    sira = [str(x) for x in ((b.get("izgara_deger") or {}).get(param) or [])]
    degerler = [d for d in sira if d in degerler] + [d for d in degerler if d not in sira]
    govde = []
    for d in degerler:
        ad = _komb_deger(param, d if param not in ("k", "geri_cekilme") else float(d), b.get("aile") or "")
        ad += " (varsayılan)" if str(v.get(param)) == d else ""
        satir = [ad]
        for c in _ciftler(b):
            x = ((b["cift"][c].get("varyant") or {}).get(param) or {}).get(d) or {}
            satir.append(f"{_hucre((x.get('is') or {}).get('beklenti_r'), 'ra')} · "
                         f"{_hucre((x.get('oos') or {}).get('beklenti_r'), 'ra')} ({sayi((x.get('oos') or {}).get('n') or 0, 0)})")
        govde.append(satir)
    if not govde:
        return f"_{adlar.PARAM.get(param, param)} varyantları ölçülmedi._"
    return (_tablo([bas_buyuk(adlar.PARAM.get(param, param))] + [PARITE[c] for c in _ciftler(b)], govde,
                   ["l"] + ["r"] * len(_ciftler(b))) +
            "\n\n_Hücre: örneklem içi · örneklem dışı net R (parantezde örneklem dışı işlem sayısı); öbür parametreler "
            "önceden kayıtlı varsayılanda._")


def blok_hedef_uzaklik(u: Uretim, ctx: dict, birim: str = "") -> str:
    """Hedefin girişten uzaklığı, R biriminde (dört paritenin işlemleri): medyan ve çeyrekler."""
    b = (u.O.get("birim") or {}).get(birim) if birim else ctx["B"]
    h = (b or {}).get("hedef_uzaklik") or {}
    if not h.get("n"):
        return "ölçülmedi"
    return (f"medyan {sayi(h['medyan'], 2)} R (çeyrekler {sayi(h['c1'], 2)}–{sayi(h['c3'], 2)}; işlemlerin "
            f"{yuzde(h['pay_2r_ustu'], 0)} kadarında 2 R'nin ötesinde)")


def blok_gun_ici(u: Uretim, ctx: dict, birim: str = "", cift: str = "") -> str:
    """Örneklem dışında işlem açılan günlerin kaçında iki ya da daha çok işlem var; tek pozisyon kuralı yüzünden kaç
    sinyal alınmadı (bir birim, ana parite)."""
    cift = cift or ana()
    b = (u.O.get("birim") or {}).get(birim) if birim else ctx["B"]
    g = ((b or {}).get("gun_ici") or {}).get(cift) or {}
    if not g.get("islem_gunu"):
        return "ölçülmedi"
    return (f"{PARITE[cift]}'de örneklem dışında işlem açılan {sayi(g['islem_gunu'], 0)} günün "
            f"{yuzde(g['pay'], 0)} kadarında iki ya da daha çok işlem var ve açık pozisyon yüzünden "
            f"{sayi(g['atlanan_sinyal'], 0)} sinyal alınmadı")


def blok_sonuclar(u: Uretim, ctx: dict) -> str:
    """Bir stratejinin standart sonuç dizisi: aynı düzen her stratejide, böylece stratejiler yan yana okunur. Tanımlar
    giriş dersindedir; burada yalnız sayılar ve sayıların okunuşu. Yorum bu dizinin ARKASINA strateji şablonunda
    yazılır."""
    b = ctx["B"]
    k = u.O["kunye"]
    kisa = adlar.BIRIM[ctx["BID"]][1]
    p = [f"**Birikimli sonuç.** Önceden kayıtlı varsayılanın {len(_ciftler(b))} paritede ve havuzda birikimli net R'si; "
         f"örneklem içi (2018–{k['ic_bitis'][:4]}) soluk, örneklem dışı ({tarih(k['dis_baslangic'])} →) koyu çizgi.",
         "", blok_sekil(u, ctx, "egri", f"Birikimli net R ve düşüş — {kisa}"), "", blok_oos_cumle(u, ctx), "",
         blok_sonuc(u, ctx, "oos"), "",
         f"_Önceden kayıtlı varsayılan, örneklem dışı. Net: gerçek makas ve dolum başına "
         f"{sayi(k['temel_kayma_pip'], 1)} pip kayma (haber penceresinde ayrıca {sayi(k['haber_kayma_pip'], 1)} pip). "
         f"Havuz: aynı kural bütün paritelerde birlikte; Sharpe havuzda günlük R toplamından._", "",
         blok_havuz_cumle(u, ctx), "",
         "**Bütün dönem.** Varsayılan veriye bakmadan seçildiği için 2018 → 2026 da onun örneklem dışıdır; hüküm 2024 → "
         "penceresinden verilir, bütün dönemin hükmü burada.", "", blok_sonuc_tum(u, ctx), "",
         "**İşlemlerin anatomisi** (örneklem dışı).", "", blok_ayrinti(u, ctx, "oos"), "",
         "**Mum uzunluğu.** Aynı kural 5, 15 ve 60 dakikalık mumlarla; öbür parametreler önceden kayıtlı varsayılanda.",
         "", blok_sekil(u, ctx, "tf", f"Zaman dilimi kıyası — {kisa}"), "", blok_tf_okuma(u, ctx), "",
         f"**Izgara ve seçim.** Izgaranın bütün kombinasyonları örneklem içinde ({k['baslangic'][:4]}–"
         f"{k['ic_bitis'][:4]}) denendi; her paritede en yüksek örneklem içi Sharpe'lı kombinasyon seçildi ve örneklem "
         f"dışında sınandı.", "",
         blok_sekil(u, ctx, "izgara", f"Parametre ızgarası — {kisa}"), "", blok_izgara_okuma(u, ctx), "",
         blok_secim(u, ctx), "", blok_dsr_cumle(u, ctx), "", blok_wf_cumle(u, ctx), "", blok_wf(u, ctx), "",
         "**Maliyet.**", "", blok_maliyet(u, ctx), "",
         "**Kuyruk.** R ortalaması her işlemi riskine göre büyüklükler; riski küçük tek bir işlem ortalamayı taşıyabilir.",
         "", blok_kuyruk(u, ctx), "",
         "**Yön mü, zamanlama mı?** " + blok_rastgele_cumle(u, ctx), "",
         "**Rejim ve saat.** " + blok_rejim_cumle(u, ctx), "", blok_rejim(u, ctx), "",
         blok_sekil(u, ctx, "saat", f"Giriş saatine göre — {kisa}"), "", blok_saat_okuma(u, ctx), ""]
    return "\n".join(p)


def blok_kosullar(u: Uretim, ctx: dict) -> str:
    """Koşul analizi dizisi: figür (ana parite), tutan/tutmayan özeti, en az bir paritede tutan değişkenlerin dört
    paritedeki durumu (kovasıyla)."""
    b = ctx["B"]
    kisa = adlar.BIRIM[ctx["BID"]][1]
    p = [blok_sekil(u, ctx, "kosul", f"Koşul kovaları — {kisa}"), "", blok_kosul_ozet(u, ctx), ""]
    tab = _kosul_tablosu(b)
    tutan = []
    for c in _ciftler(b):
        for ad, x in tab[c].items():
            if x.get("hukum") == "tuttu" and ad not in tutan:
                tutan.append(ad)
    sira = list(adlar.KOSUL)
    tutan.sort(key=lambda a: sira.index(a) if a in sira else 99)
    if tutan:
        govde = []
        for d in tutan:
            satir = [adlar.KOSUL.get(d, d)]
            for c in _ciftler(b):
                x = tab[c].get(d) or {}
                h = x.get("hukum")
                satir.append(f"tuttu: {_kova_yaz(x.get('secilen') or [])}" if h == "tuttu" else
                             {"tutmadi": "tutmadı", "secilmedi": "kova seçilmedi", "hepsi": "bütün kovalar seçildi",
                              "esdeger": "aynı ölçü"}.get(h, "—"))
            govde.append(satir)
        p += ["En az bir paritede tutan değişkenler, dört paritede (\"tuttu\" hücresinde seçilen kova):", "",
              _tablo(["Değişken"] + [PARITE[c] for c in _ciftler(b)], govde, ["l"] + ["l"] * len(_ciftler(b))), ""]
    return "\n".join(p)


BLOKLAR = {
    "sonuclar": blok_sonuclar, "kosullar": blok_kosullar, "hukum_cumle": blok_hukum_cumle,
    "havuz_cumle": blok_havuz_cumle, "ay_sonu": blok_ay_sonu, "ay_sonu_cumle": blok_ay_sonu_cumle,
    "regresyon": blok_regresyon,
    "devam": blok_devam, "devam_cumle": blok_devam_cumle, "devam_yetersiz": blok_devam_yetersiz,
    "esik_payi": blok_esik_payi, "haber_kirilim": blok_haber_kirilim, "fomc": blok_fomc, "fomc_cumle": blok_fomc_cumle,
    "veri": blok_veri, "haber_makas": blok_haber_makas, "haber_makas_ozet": blok_haber_makas_ozet,
    "haber_makas_cumle": blok_haber_makas_cumle,
    "pratik_islem": blok_pratik_islem, "pratik_atr": blok_pratik_atr,
    "ders_ozet": blok_ders_ozet, "takvim": blok_takvim,
    "hukum_matris": blok_hukum_matris, "genel_hukum": blok_genel_hukum, "maliyet_ozet": blok_maliyet_ozet,
    "rastgele_ozet": blok_rastgele_ozet, "korelasyon_cumle": blok_korelasyon_cumle,
    "kosul_genel": blok_kosul_genel, "kosul_genel_cumle": blok_kosul_genel_cumle,
    "onkayit_tablo": blok_onkayit_tablo, "takvim_sorun": blok_takvim_sorun, "celiski": blok_celiski,
    "arsiv_ozet": blok_arsiv_ozet, "olaganustu": blok_olaganustu,
    "oos_cumle": blok_oos_cumle, "rastgele_cumle": blok_rastgele_cumle, "dsr_cumle": blok_dsr_cumle,
    "wf_cumle": blok_wf_cumle, "rejim_cumle": blok_rejim_cumle,
    "sekil": blok_sekil, "sonuc": blok_sonuc, "sonuc_tum": blok_sonuc_tum, "ayrinti": blok_ayrinti,
    "maliyet": blok_maliyet, "secim": blok_secim, "wf": blok_wf, "rejim": blok_rejim, "kural": blok_kural,
    "hukum": blok_hukum, "kosul_ozet": blok_kosul_ozet, "ornek": blok_ornek, "zaman": blok_zaman, "dst": blok_dst,
    "basabas": blok_basabas, "kontrol_hukum": blok_kontrol_hukum, "ne_zaman": blok_ne_zaman,
    "tf_okuma": blok_tf_okuma, "izgara_okuma": blok_izgara_okuma, "saat_okuma": blok_saat_okuma,
    "kuyruk": blok_kuyruk, "varyant": blok_varyant, "hedef_uzaklik": blok_hedef_uzaklik, "gun_ici": blok_gun_ici,
    "kosul_tek": blok_kosul_tek, "hangi_kosul": blok_hangi_kosul, "pencere_ayrisan": blok_pencere_ayrisan,
}


# ─────────────────────────────────────────────────────────────── ders
def ders_uret(sablon: str, olcum: dict, onkayit: dict, strateji_dizini: Path | None = None) -> tuple[str, Uretim]:
    """Bir dersin şablonunu MDX'e çevirir. `{{! strateji <birim> }}` alt şablonu birim bağlamıyla işler."""
    u = Uretim(olcum, onkayit)
    sd = strateji_dizini or (METIN / "strateji")

    def blok_strateji(uu: Uretim, ctx: dict, birim: str) -> str:
        yol = sd / f"{birim}.md"
        if not yol.exists():
            raise SablonHatasi(f"strateji şablonu yok: {birim}")
        uu.birimler.append(birim)
        return uu.isle(yol.read_text(encoding="utf-8"), uu.birim_ctx(birim))

    BLOKLAR["strateji"] = blok_strateji
    govde = u.isle(sablon, u.kok_ctx())
    # Boş kalan koşullu bloklar ardışık boş satır bırakır; MDX onları yutar ama üretilen dosya okunur kalsın.
    govde = re.sub(r"\n{3,}", "\n\n", govde)
    if "<GrafikEmbed" in govde:
        on, son = _onbilgi_ayir(govde)
        govde = on + "\nimport GrafikEmbed from '../../components/GrafikEmbed.astro';\n" + son
    return govde, u


def _onbilgi_ayir(metin: str) -> tuple[str, str]:
    if not metin.startswith("---\n"):
        raise SablonHatasi("ön bilgi yok")
    j = metin.index("\n---\n", 4) + 5
    return metin[:j], metin[j:]


def olcum_oku(yol: Path) -> dict:
    return json.loads(yol.read_text(encoding="utf-8"))
