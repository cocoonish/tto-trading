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
yuvarlanan bir artı ya da eksi "0,00" okunmasın) · sh (işaretli Sharpe) · s0 … s4 (işaretsiz sayı; eksi yine
yazılır) · p (p değeri: 0,01'in altı "< 0,01", 0,1'in altı üç hane) · p1 (işaretli pip) · yz0 · yz1 (kesirden
yüzde) · yzs1 (işaretli yüzde) · pu (iki kesrin farkı, işaretli puan: 0,084 → +8,4) · n (tam sayı) · tarih · yil ("YYYY-AA-GG" → "YYYY") · tarih_uzun · ay_uzun · ay_liste ("YYYY-AA" listesi) ·
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
from zoneinfo import ZoneInfo

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


#: "zaman" hedefinin mum sayısı, ön kaydın tek tanımından ([genel] desen_zaman_mum, [haber] zaman_mum); Uretim kurar.
ZAMAN_MUM: dict[str, int] = {}
#: Haber kurallarının aileleri (haber dersinin birimleri; haber kurallarında birim adı aile adıdır).
HABER_AILE = set(adlar.DERS_BIRIM["fx-gunici-haber"])


def zaman_kur(onkayit: dict) -> None:
    """Ön kaydın "zaman" hedefi mum sayıları; ön kayıt onları taşımıyorsa (ör. sınamanın küçük ön kaydı) boş kalır ve
    "zaman" yazımı istendiği an üretim adıyla düşer (_zaman_ad)."""
    ZAMAN_MUM.clear()
    g, h = (onkayit.get("genel") or {}).get("desen_zaman_mum"), (onkayit.get("haber") or {}).get("zaman_mum")
    if g is not None:
        ZAMAN_MUM["desen"] = int(g)
    if h is not None:
        ZAMAN_MUM["haber"] = int(h)


def _zaman_ad(aile: str) -> str:
    """"zaman" hedefinin okur yazımı mum sayısıyla: "zaman (12 mum)"."""
    n = ZAMAN_MUM.get("haber" if aile in HABER_AILE else "desen")
    if not n:
        raise SablonHatasi("zaman hedefinin mum sayısı kurulmadı (zaman_kur)")
    return f"zaman ({n} mum)"


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
    20'sinde), "de" (bulunma: 4'te, 20'de), "e" (yönelme: 4'e, 20'ye), "in" (ilgi: 4'ün, 20'nin), "er" (üleştirme:
    33'er, 6'şar). Uyum, sayının okunuşunun son sözcüğünden."""
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
    elif kip == "er":                                   # üleştirme: 33'er, 6'şar
        e_ = ("ş" if unluyle else "") + genis + "r"
    else:
        raise SablonHatasi(f"bilinmeyen ek: {kip}")
    return f"{sayi(n, 0)}'{e_}"


def yuzde_ek(x: float, kip: str) -> str:
    """Tam yüzdeye ek: 0,02 → "%2'si", 0 → "%0'ı" (okunuş "yüzde iki", "yüzde sıfır"; ek sayının okunuşundan)."""
    n = int(round(abs(x) * 100))
    return ("−" if x < 0 and n else "") + "%" + ek(n, kip)


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
    if re.fullmatch(r"s[0-4]", bicim):
        return sayi(_sayisal(v), int(bicim[1]))
    if bicim == "pu":
        # İki kesrin farkı puan olarak (0,084 → +8,4): "%" yazmak farkı bir orana çevirirdi.
        return sayi(100 * _sayisal(v), 1, arti=True)
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
    if bicim == "yil":
        return str(v)[:4]
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
    if bicim == "pariteler":
        # Künyenin parite listesi okur adlarıyla ("EUR/USD, GBP/USD, USD/JPY ve AUD/USD"): elle yazılan liste ayardan
        # bir parite eklendiği ya da çıkarıldığı gün eksik ya da fazla kalırdı.
        if not isinstance(v, list) or not v:
            raise SablonHatasi(f"boş olmayan parite listesi bekleniyordu: {yol}")
        return liste_yaz([PARITE.get(str(x), str(x)) for x in v])
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


_OP = re.compile(r"\s(==|!=|<=|>=|<|>|in)\s")


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
    if op == "in":                                   # "öğe" in liste: ölçümün bir listesinde adıyla duran kayıt
        if not isinstance(b, list):
            raise SablonHatasi(f"'in' sağında liste bekleniyordu: {s!r}")
        return a in b
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
        zaman_kur(onkayit)
        self.sekil_no = 0
        self.sabitler: list[str] = []
        self.iddia = 0
        self.yer = 0
        self.sekiller: list[str] = []
        self.birimler: list[str] = []       # bu derste işlenen strateji birimleri (sırayla)
        self.sinir_basildi: set = set()     # özet tablolarının notunda ayrıntısı basılmış sınır kayıtları (ders içi)

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
    """Markdown tablosu. Hücrede boru karakteri tabloyu sessizce böler (hücre ikiye ayrılır, satır kayar): üretim
    düşer. Satırın hücre sayısı başlığınkinden farklıysa da düşer."""
    for r in [baslik] + list(satirlar):
        if any("|" in str(x) for x in r):
            raise SablonHatasi(f"tablo hücresinde boru karakteri: {r}")
        if len(r) != len(baslik):
            raise SablonHatasi(f"tablo satırının hücre sayısı başlıkla aynı değil: {r}")
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
    govde = [[ad] + [_hucre_havuz(s, m, k, f) for s, m in sutun] for ad, k, f in satirlar]
    return _tablo([""] + [s for s, _ in sutun], govde)


# Pariteler arası pip toplanamaz (USD/JPY'nin pip'i 0,01, öbürlerininki 0,0001): havuz sütunu yalnız R'de dolar.
PIP_ALANLARI = ("beklenti_pip", "pf", "risk_pip", "ort_kazanc_pip", "ort_kayip_pip", "azami_dusus_pip", "mae_pip",
                "mfe_pip")


def _hucre_havuz(sutun: str, m: dict, k: str, f: str) -> str:
    return "—" if sutun == "Havuz" and k in PIP_ALANLARI else _hucre(m.get(k), f)


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
        ("Ort. kazanç (pip)", "ort_kazanc_pip", "p1"), ("Ort. kayıp (pip)", "ort_kayip_pip", "p1"),
        ("Kâr çarpanı (R)", "pf_r", "s2"), ("Kâr çarpanı (pip)", "pf", "s2"),
        ("Azami düşüş (R)", "azami_dusus_r", "s1"), ("Azami düşüş (pip)", "azami_dusus_pip", "s1"),
        ("Ort. süre (dk)", "sure_dk", "s0"), ("MAE medyanı (R)", "mae_r", "ra"), ("MFE medyanı (R)", "mfe_r", "ra"),
        ("MAE medyanı (pip)", "mae_pip", "p1"), ("MFE medyanı (pip)", "mfe_pip", "p1"),
        (birim_satiri, "risk_pip", "s1"),
    ]
    govde = [[ad] + [_hucre_havuz(s, m, k, f) for s, m in sutun] for ad, k, f in satirlar]
    tablo = _tablo([""] + [s for s, _ in sutun], govde)
    if any(s == "Havuz" for s, _ in sutun):
        tablo += "\n\n_Pip satırlarında havuz boştur: pariteler arası pip toplanamaz, havuz yalnız R'de verilir._"
    return tablo


def _makas_payi(v: dict, d: str) -> float | None:
    """Brüt artı ama yalnız makasla bile eksi olan dönemde sonucun sıfıra indiği makas, bu verinin makasının payı
    olarak: brüt / (brüt − yalnız makas). Makasın maliyeti makasla doğrusal ölçeklenir varsayımı; kayma yok."""
    brut = (v.get(d) or {}).get("brut_r")
    ym = ((v.get("yalniz_makas") or {}).get(d) or {}).get("beklenti_r")
    if brut is None or ym is None or brut <= 0 or ym > 0 or brut - ym <= 0:
        return None
    return brut / (brut - ym)


def _basabas_hucre(v: dict, son: str = "") -> str:
    """Başabaş kaymanın tablo yazımı (son: "" bütün dönem, "_oos" 2024 →), maliyet okumasının türüne göre
    (`_maliyet_turu`): kesişim (pip) · "orta fiyattan bile eksi" (brüt artı değil: hiçbir kayma kademesi başabaş
    değildir) · "makas ≤ %X" (yalnız makasla bile eksi: sonucun sıfıra indiği makas, bu verinin makasının payı) ·
    "0,0 pip kademesinde bile eksi" (haber penceresinin kayması eksiye çeviriyor) · "2 pip'te bile artı"."""
    d = "oos" if son else "tum"
    tur = _maliyet_turu(v, d)
    if tur is None:
        return "—"
    if tur == "brut":
        return "orta fiyattan bile eksi"
    if tur == "makas":
        pay = _makas_payi(v, d)
        return f"makas ≤ {yuzde(pay, 0)}" if pay is not None else "—"
    if tur == "haber":
        return "0,0 pip kademesinde bile eksi"
    if tur == "artı":
        return "2 pip'te bile artı"
    k = v.get("basabas_kayma_pip" + son)
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
    # Haber payı tablonun penceresinden (örneklem dışı); "düşmüyor" yalnız pay tam sıfırken.
    pay = []
    for c in cs:
        hp = v_[c].get("haber_payi_donem")
        if hp is None:
            raise SablonHatasi(f"maliyet: {ctx['BID']} {c} dönem başına haber payı ölçümde yok")
        if hp.get("oos") is not None and math.isfinite(hp["oos"]):
            pay.append(hp["oos"])
    def py(x: float) -> str:
        """Pay tam sayıya yuvarlanır; sıfır olmayan ama %0,5'in altındaki pay iki haneyle (tam sıfır "%0" kalır)."""
        return yuzde(x, 2) if 0 < x < 0.005 else yuzde(x, 0)
    if pay and max(pay) >= 0.005:
        aralik = py(min(pay)) if py(min(pay)) == py(max(pay)) else f"{py(min(pay))}–{py(max(pay))}"
        pay_ = f" Örneklem dışında haber penceresine düşen giriş payı bu kuralda {aralik}."
    elif pay and max(pay) > 0:
        pay_ = (f" Örneklem dışında haber penceresine düşen giriş payı bu kuralda %0,5'in altında (en çok "
                f"{yuzde(max(pay), 2)}).")
    else:
        pay_ = " Bu kuralın örneklem dışı girişlerinden hiçbiri haber penceresine düşmüyor." if pay else ""
    tur = {_maliyet_turu(v_[c], d) for c in cs for d in ("oos", "tum")}
    tanim = []
    if "brut" in tur:
        tanim.append("\"orta fiyattan bile eksi\": brüt sonuç artı değil, hiçbir kayma kademesinde başabaş yok")
    if "makas" in tur:
        tanim.append("\"makas ≤ %X\": kayma hiç yokken yalnız makasla bile eksi; sonucun sıfıra indiği makas, bu "
                     "verinin makasının bu payıdır (makasın maliyeti makasla doğrusal ölçeklenir varsayımıyla)")
    if "haber" in tur:
        tanim.append(f"\"0,0 pip kademesinde bile eksi\": yalnız makasla artı, ama temel kayma sıfırken de haber "
                     f"penceresinin {sayi(hk, 1)} pip'i sonucu eksiye çeviriyor")
        # Hangi hücre: parite ve dönem adıyla, iki sayısıyla (bütün dönemin kademeleri tabloda yok).
        hucre = []
        for c in cs:
            for d, dad in (("oos", "2024 →"), ("tum", "bütün dönem")):
                if _maliyet_turu(v_[c], d) != "haber":
                    continue
                ym = ((v_[c].get("yalniz_makas") or {}).get(d) or {}).get("beklenti_r")
                m0 = (((v_[c].get("maliyet") or {}).get("0.0") or {}).get(d) or {}).get("beklenti_r")
                hucre.append(f"{PARITE[c]}, {dad} (yalnız makasla {_hucre(ym, 'ra')} R, 0,0 pip kademesinde "
                             f"{_hucre(m0, 'ra')} R)")
        tanim.append(("Bu hâldeki bileşim" if len(hucre) == 1 else "Bu hâldeki bileşimler") + ": "
                     + "; ".join(hucre))
    return (_tablo(["Dolum başına kayma"] + [PARITE[c] for c in cs], govde) +
            f"\n\n_{bas_buyuk(adlar.varsayilan_ad(b))}, örneklem dışı (2024 →) net beklenti, R. Kademeler dolum başına temel "
            f"kaymadır; haber penceresindeki "
            f"dolumlar her kademede ayrıca {sayi(hk, 1)} pip öder, \"yalnız makas\" satırında o da sıfırdır.{pay_} "
            f"Payı sıfır olan kuralda da 0,0 pip satırı yalnız makastan ayrışabilir: haber penceresine düşen çıkış "
            f"dolumları da {sayi(hk, 1)} pip öder. Başabaş: net beklentiyi sıfıra indiren dolum başına temel kayma; "
            f"haber penceresindeki dolumların {sayi(hk, 1)} pip ek kayması sabit tutulur."
            + ("".join(f" {bas_buyuk(t)}." for t in tanim)) + "_")


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
    """'k' parametresinin birimi aileye göre (tek tanım adlar.esik_birimi; figürler de onu okur)."""
    return adlar.esik_birimi(aile)


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
        return _deger_yaz(x, k, aile)
    return f"{KOMB_AD.get(k, adlar.PARAM.get(k, k))} {_deger_yaz(x, k, aile)}"


def kombinasyon_yaz(p: dict, on: dict, sabit: dict | None = None, aile: str = "") -> str:
    """Bir kombinasyonun okur yazımı, önceden kaydın ızgara sırasıyla (zaman dilimi önce). Birimin sabitlediği
    boyutlar (ör. başarısız kırılımda seviye) ve kuralın taşımadığı parametreler yazılmaz."""
    sira = list((on.get("izgara") or {}).keys())
    anahtar = sorted(p, key=lambda k: (sira.index(k) if k in sira else 99, k))
    return " · ".join(_komb_deger(k, p[k], aile) for k in anahtar
                      if k not in (sabit or {}) and _gorunur(k, p, on, aile))


def _r_pip_ayrisan(b: dict, tur: str) -> list[tuple[str, dict]]:
    """Örneklem dışında net R ortalaması ile net pip ortalamasının işareti ayrışan pariteler (tur: varsayilan |
    secilen). R ortalaması her işlemi riskine göre ölçekler, pip ortalaması aynı büyüklükte işlem yapanın
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
    asgari = int(u.ON["secim"]["asgari_islem_haber" if "haber_olay" in b else "asgari_islem"])
    secilemeyen = []
    for c in _ciftler(b):
        v = b["cift"][c]
        s = v.get("secilen") or {}
        p = v.get("secilen_p") or {}
        ic, dis = s.get("is") or {}, s.get("oos") or {}
        if not p:
            secilemeyen.append((c, (v.get("izgara_ozet") or {}).get("is_azami_n")))
        govde.append([PARITE[c], kombinasyon_yaz(p, on, b.get("sabit"), b.get("aile") or "") or "seçilemedi",
                      _hucre(ic.get("beklenti_r"), "ra"), _hucre(ic.get("beklenti_pip"), "p1"),
                      _hucre(dis.get("beklenti_r"), "ra"), _hucre(dis.get("beklenti_pip"), "p1"),
                      _hucre((s.get("dsr") or {}).get("dsr"), "s2"), _hucre((s.get("dsr") or {}).get("dsr_gurultu"), "s2"),
                      _hucre(s.get("hukum"), "hukum")])
    tablo = _tablo(["Parite", "Seçilen", "İçi (R)", "İçi (pip)", "Dışı (R)", "Dışı (pip)", "DSR (yayılım)",
                    "DSR (gürültü)", "Hüküm"], govde,
                   ["l", "l", "r", "r", "r", "r", "r", "r", "l"])
    not_ = _r_pip_cumle(b, "secilen", "Seçilen kombinasyonlarda")
    # Seçilenin kuyruğu: artı hükümlü (zayıf ya da çalışıyor) seçilenlerde ortalamanın en iyi işlemlere duyarlılığı
    # (betimleyici; hüküm değişmez). Varsayılanın kuyruk tablosunun eşi, seçilen satırı için tek cümle.
    kuy = []
    for c in _ciftler(b):
        s = b["cift"][c].get("secilen") or {}
        k = ((s.get("kuyruk") or {}).get("oos")) or {}
        if s.get("hukum") in ("zayif", "calisiyor") and k.get("r") is not None:
            pah = k.get("r_pahali_haric")
            kuy.append(f"{PARITE[c]} {_hucre(k['r'], 'ra')} R; en iyi işlem hariç {_hucre(k.get('r_tek_haric'), 'ra')}, "
                       f"en iyi üç hariç {_hucre(k.get('r_uc_haric'), 'ra')}"
                       + (f", maliyeti riskin yarısını aşan {sayi(k['n_pahali'], 0)} işlem hariç {_hucre(pah, 'ra')}"
                          if (k.get("n_pahali") or 0) > 0 and pah is not None and math.isfinite(pah) else "")
                       + (f" ({sayi(k['en_iyi_esit'], 0)} işlem en iyi değeri, {_hucre(k.get('en_iyi_r'), 'ra')} R'yi, "
                          f"paylaşıyor)" if (k.get("en_iyi_esit") or 1) > 1 else ""))
    if kuy:
        tablo += ("\n\n_Artı hükümlü seçilenlerin kuyruğu (örneklem dışı, işlem başına net R): " + "; ".join(kuy)
                  + ". Betimleyicidir; hüküm değişmez._")
    # Örneklem içi ortalaması TEK işleme dayanan seçim: en iyi işlem eşsizdir (eşit değerde ikinci işlem yok) ve
    # çıkınca örneklem içi ortalamanın işareti döner. Seçim o işlemin yanında durur; bunu bilmeden seçilenin örneklem
    # içi sütunu okunamaz. (Eşit değerli çok işlemde, ör. 2R hedefinde, tek işlemi çıkarmak sıfıra yakın bir ortalamayı
    # oynatır ama "tek işleme dayanma" değildir; o hâl yazılmaz.)
    tek = []
    for c in _ciftler(b):
        k = (((b["cift"][c].get("secilen") or {}).get("kuyruk") or {}).get("is")) or {}
        if (k.get("r") or 0) > 0 and (k.get("en_iyi_esit") or 0) == 1 and k.get("r_tek_haric") is not None \
                and k["r_tek_haric"] <= 0 and k.get("en_iyi_gun"):
            tek.append(f"{PARITE[c]} {_hucre(k['r'], 'ra')} R, en iyi işlem çıkınca {_hucre(k['r_tek_haric'], 'ra')} "
                       f"({tarih(k['en_iyi_gun'])} işlemi, {_hucre(k.get('en_iyi_r'), 'ra')} R; risk "
                       f"{_pip(round(k.get('en_iyi_R_pip') or 0, 2))} pip)")
    if tek:
        tablo += ("\n\n_Örneklem içi ortalaması tek işleme dayanan seçimler (işlem başına net R; en iyi işlem çıkınca "
                  "işaret dönüyor): " + "; ".join(tek) + ". Betimleyicidir; seçim ve hüküm değişmez._")
    # Gün sonu: seçilenin girişi olay türünün emirlerinin bir kısmında gün sonu çıkışından (New York) sonraya
    # düşüyorsa o olayı (kısmen ya da bütünüyle) işleyemez; olay olay adıyla yazılır (ölçüm: durum_parite).
    gs_et = u.O["kunye"]["gun_sonu_et"]
    gun_sonu, hepsi = [], False
    for c in _ciftler(b):
        d = ((b.get("durum_parite") or {}).get(c) or {}).get("secilen") or {}
        ol = [(o, x) for o, x in (d.get("olay") or {}).items() if x.get("gun_sonu")]
        if ol:
            ol.sort(key=lambda ox: list(adlar.OLAY).index(ox[0]) if ox[0] in adlar.OLAY else 99)
            hepsi = hepsi or any(x["gun_sonu"] == x["toplam"] for _, x in ol)
            gun_sonu.append(f"{PARITE[c]} — " + ", ".join(
                f"{adlar.OLAY.get(o, o)} {sayi(x['toplam'], 0)} emrin "
                + ("hepsi" if x["gun_sonu"] == x["toplam"] else ek(x["gun_sonu"], "i"))
                for o, x in ol))
    if gun_sonu:
        tablo += (f"\n\n_Gün sonu (bütün dönem): girişi gün sonu çıkışına (New York {gs_et}, "
                  f"{adlar.tsi_yaz([f'New York {gs_et}'])}) ya da sonrasına düşen emir alınmaz. Seçilenlerde böyle "
                  "düşen emirler: " + "; ".join(gun_sonu) + "."
                  + (" Emirlerinin hepsi düşen olayı seçilen hiç işlemez." if hepsi else "")
                  + " Sonuç yalnız alınan emirlerden._")
    if secilemeyen:
        tablo += ("\n\n_Seçilemedi: " + "; ".join(
            f"{PARITE[c]}'de örneklem içinde en az {sayi(asgari, 0)} işlemli kombinasyon yok"
            + (f" (en kalabalığı {sayi(int(n), 0)} işlem)" if n is not None else "") for c, n in secilemeyen) + ". Seçim ön kayıtlı asgari işlem sayısını ister; o "
            "paritede ızgaradan seçilen bir kural yoktur ve hüküm yalnız varsayılandan verilir._")
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
    k = u.O["kunye"]
    return (_tablo([""] + [PARITE[c] for c in cs], govde) +
            f"\n\n_{bas_buyuk(adlar.varsayilan_ad(b))}, bütün dönem ({str(k['baslangic'])[:4]} → "
            f"{str(k['bitis'])[:4]}), işlem başına net R. Oynaklık tercili: önceki günlerin ATR(14)'ünün son 252 işlem "
            "günündeki yüzdeliği (alt, orta, üst üçte bir); işlem gününü içermez._")


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
        izg = ", ".join(_deger_yaz(x, k, aile) for x in degerler) + (" (bu kuralda sabit)" if k in sabit else "")
        vs = _deger_yaz(v.get(k), k, aile) if k in v else "—"
        if k in onv and onv[k] != v.get(k):
            vs += f" (ön kayıtta {_deger_yaz(onv[k], k, aile)})"
        govde.append([adlar.PARAM.get(k, k) if k != "k" else f"eşik ({_esik_birimi(aile)})", izg, vs])
    n = int(b.get("kombinasyon") or 0)
    not_ = f"_Izgara: {sayi(n, 0)} kombinasyon"
    if n and carpim > n and aile in IZGARA_DISI:
        not_ += f" ({sayi(carpim, 0)} bileşimden; {IZGARA_DISI[aile]})"
    # Saat değerli parametreler yerel saatle yazılır (kural öyle tanımlı); TSİ karşılığı tablonun altında.
    saat = []
    for k in izgara:
        if k in adlar.SAAT_SEHIR and _gorunur(k, v, on, aile):
            degerler = list(gercek.get(k) or izgara[k])
            if k in onv and onv[k] not in degerler:      # "08:00 (ön kayıtta 09:30)": ön kaydın saati de tabloda
                degerler.append(onv[k])
            for x in degerler:
                saat.append(f"{adlar.PARAM.get(k, k)} {x} → {adlar.tsi_yaz([f'{adlar.SAAT_SEHIR[k]} {x}'])}")
    if saat:
        not_ += ". Saatler kuralın yerel saatidir: " + "; ".join(saat)
    return _tablo(["Parametre", "Izgara", "Varsayılan"], govde, ["l", "l", "l"]) + "\n\n" + not_ + "._"


def _deger_yaz(x, k: str = "", aile: str = "") -> str:
    if x is None:
        return "—"
    if k == "hedef" and str(x) == "zaman":
        return _zaman_ad(aile)
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
#: Sözcükle yazılan sayının iyelik + bulunma hâli ("dört paritenin üçünde").
SAYI_INDE = {1: "birinde", 2: "ikisinde", 3: "üçünde", 4: "dördünde", 5: "beşinde", 6: "altısında"}
GUN_ADI = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]


def _hukum_hucre(v: dict, d: str, anahtar: str) -> str:
    """Hüküm ve işlem başına net R ("zayıf · +0,18"); az işlemde giriş dersinin etiketi ("zayıf · +0,35 · az işlem
    (12)")."""
    if not v:
        return "—"
    o = v.get(d) or {}
    s = f"{adlar.HUKUM.get(v.get(anahtar) or 'olculemedi')} · {_hucre(o.get('beklenti_r'), 'ra')}"
    if (v.get("az_islem") or {}).get(d):
        s += f" · az işlem ({sayi(o.get('n') or 0, 0)})"
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
        # Seçimin kurulamadığı paritede hücre boş tire değil sebebiyle: "seçilemedi" (asgari işlem; seçim tablosu).
        secilen = (_hukum_hucre(s, "oos", "hukum") if b["cift"][c].get("secilen_p") else "seçilemedi")
        govde.append([PARITE[c], _hukum_hucre(v, "oos", "hukum"), _hukum_hucre(v, "tum", "hukum_tum"),
                      secilen, rastgele, maliyet])
    sin = blok_sinirda(u, ctx)
    return (_tablo(["Parite", "Varsayılan, 2024 →", "Varsayılan, bütün dönem", "Seçilen, 2024 →",
                    "Rastgele yüzdelik, 2024 →", "Maliyet bayrağı (bütün · 2024 →)"], govde,
                   ["l", "l", "l", "l", "r", "l"]) +
            "\n\n_Hücrede hüküm ve işlem başına net R; tanımlar giriş dersinde (\"Hüküm\")._"
            + (f"\n\n{sin}" if sin else ""))


UC_AD = {"ga_alt": "net aralığın alt ucu", "ga_brut_alt": "brüt aralığın alt ucu", "ga_ust": "aralığın üst ucu"}
UC_KISA = {"ga_alt": "alt uç", "ga_brut_alt": "brüt alt uç", "ga_ust": "üst uç"}
KIM_AD = {"varsayilan": "varsayılan", "secilen": "seçilen"}
DONEM_AD = {"oos": "örneklem dışı", "tum": "bütün dönem"}


def _sinir_cumle(s: dict) -> str:
    """Sıfıra yakın bir bootstrap ucunun bilgi cümlesi (ölçüm: metrik.sinir_bilgisi)."""
    return (f"{_hucre(s['uc'], 'ra')} R (sıfıra standart hatanın {sayi(abs(s['uzaklik_se']), 2)} katı uzaklıkta); "
            f"{sayi(s['tekrar'], 0)} tekrarla {_hucre(s['kesin'], 'ra')} R, önceden kayıtlı yordam (2.000 tekrar) "
            f"{sayi(s['tohum_sayisi'], 0)} tohumun {yuzde_ek(s['pozitif_pay'], 'inde')} ucu sıfırın üstünde verir")


def sinirda_kayitlar(b: dict, kimler=("varsayilan", "secilen")) -> list[tuple[str, str, str, str, dict]]:
    """Bir birimin sınırdaki uçları: (parite, kim, dönem, uç, kayıt). İşareti tohum gürültüsüne bağlı olanlar."""
    out = []
    for c in _ciftler(b):
        for kim in kimler:
            v = b["cift"][c].get(kim) or {}
            for d in ("oos", "tum"):
                for uc, s in (((v.get(d) or {}).get("sinir")) or {}).items():
                    if s.get("sinirda"):
                        out.append((c, kim, d, uc, s))
    return out


def blok_sinirda(u: Uretim, ctx: dict) -> str:
    """Bir stratejinin hükmünü ya da maliyet bayrağını ayıran bootstrap ucu sıfırdaysa bilgi notu (hüküm değişmez).
    Hükmü ayıran uçta (net aralığın alt ucu) öbür iki şartın durumu ve seçilende deflated Sharpe de yazılır. Aralığın
    üst ucu burada yazılmaz: hükmü de bayrağı da ayırmaz; varsayılanınki "ölçülmüş kayıp" iddiasıyla birlikte kontrol
    listesinin hüküm maddesinde durur, seçilenin üst ucu hiçbir iddiaya girmez."""
    b = ctx["B"]
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    parca = []
    for c, k, d, uc, s_ in sinirda_kayitlar(b):
        if uc == "ga_ust":
            continue                    # üst uç ne hükmü ne bayrağı ayırır; "ölçülmüş kayıp" kontrol listesinde
        cumle = f"{PARITE[c]} {KIM_AD[k]}, {DONEM_AD[d]}, {UC_AD.get(uc, uc)} {_sinir_cumle(s_)}"
        if uc == "ga_alt":
            v = b["cift"][c].get(k) or {}
            yz = ((v.get("rastgele") or {}).get(d) or {}).get("yuzdelik")
            r_ = (v.get(d) or {}).get("beklenti_r")
            if yz is not None and math.isfinite(yz) and yz >= esik and r_ is not None and r_ > 0:
                cumle += (f"; hükmün öbür iki şartı geniş farkla tutuyor (ortalama {_hucre(r_, 'ra')} R, rastgele yön "
                          f"yüzdeliği {sayi(yz, 1)}), üçüncüsü sıfırda")
            dsr = (v.get("dsr") or {}).get("dsr")
            if k == "secilen" and dsr is not None and math.isfinite(dsr):
                cumle += f"; deflated Sharpe {sayi(dsr, 2)}"
        parca.append(cumle)
    if not parca:
        return ""
    return ("_Sınırda: " + "; ".join(parca) + ". Bu uçlarda işaret tohum gürültüsüne bağlıdır; hüküm ve bayrak önceden "
            "kayıtlı 2.000 tekrarla verilir ve değişmez._")


def _paritede(cs) -> str:
    """"EUR/USD paritesinde" · "EUR/USD, GBP/USD paritelerinde": ek, sayılan paritelerin sayısına göre."""
    cs = list(cs)
    return f"{liste_yaz([PARITE[c] for c in cs])} {'paritesinde' if len(cs) == 1 else 'paritelerinde'}"


def _kosul_ad(k: dict) -> str:
    return adlar.KOSUL.get(k["degisken"], k["degisken"])


def _kova_yaz(kovalar: list) -> str:
    ko = adlar.KOVA_OKUMA
    sira = sorted((str(x) for x in kovalar), key=lambda k: ko.index(k) if k in ko else 50)
    return ", ".join(sira) or "—"


# İkili koşul değişkenlerinin iki kovası okunur adlarıyla ("ay sonu, kova ay sonu" ya da "tuttu: değil" yerine):
# (değişken → (evet kovası, evet adı, hayır adı)). Hayır kovası ölçümde "değil" diye yazılır.
IKILI_KOVA = {
    "nr4": ("NR4", "NR4 günleri", "NR4 olmayan günler"),
    "nr7": ("NR7", "NR7 günleri", "NR7 olmayan günler"),
    "haber_gunu": ("haber günü", "büyük olay günleri", "büyük olay günü olmayan günler"),
    "ay_sonu": ("ay sonu", "ay sonu günleri", "ay sonu dışındaki günler"),
    "dst_gecis_haftasi": ("geçiş haftası", "saat değişimi haftaları", "saat değişimi haftası dışı"),
    "dst_ara_donem": ("ara dönem", "ara dönem (Londra–NY farkı 4 saat)", "ara dönem dışı (fark 5 saat)"),
}


def _kova_ifade(degisken: str, kovalar: list) -> str:
    """Seçilen kovaların okunuşu: ikili değişkende kovanın adı değişkenle birleşir, öbürlerinde kova listesi."""
    ik = IKILI_KOVA.get(degisken)
    kv = [str(x) for x in kovalar]
    if ik and len(kv) == 1 and kv[0] in (ik[0], "değil"):
        return ik[1] if kv[0] == ik[0] else ik[2]
    return _kova_yaz(kovalar)


def _kosul_kova(degisken: str, kovalar: list) -> str:
    """"değişken, kova …" ya da ikili değişkende yalnız kovanın okunuşu ("ay sonu günleri")."""
    ik = IKILI_KOVA.get(degisken)
    if ik and len(kovalar) == 1 and str(kovalar[0]) in (ik[0], "değil"):
        return _kova_ifade(degisken, kovalar)
    return f"{adlar.KOSUL.get(degisken, degisken)}, kova {_kova_yaz(kovalar)}"


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
    # Sayım cümlesi sıfırı ve hepsini sayıyla değil sözcükle yazar ("0 tuttu, 14 tutmadı" değil "hiçbiri tutmadı").
    if len(tut) == len(ks):
        parca = ["hepsi tuttu"]
    elif not tut:
        parca = ["hiçbiri tutmadı"] if len(tutma) == len(ks) else ([f"{sayi(len(tutma), 0)} tutmadı"] if tutma else [])
    else:
        parca = [f"{sayi(len(tut), 0)} tuttu"] + ([f"{sayi(len(tutma), 0)} tutmadı"] if tutma else [])
    if sec:
        parca.append(f"{sayi(len(sec), 0)} değişkende hiçbir kova seçilmedi (örneklem içinde en az "
                     f"{u.ON['kosul']['asgari_kova_islem']} işlemle koşulsuz ortalamanın üstünde kalan kova yok)")
    if hep:
        parca.append(f"{sayi(len(hep), 0)} değişkende bütün kovalar seçildi, sınanacak tamamlayan kalmadı")
    satir = [f"{PARITE[cift]}, sınanan {sayi(len(ks), 0)} değişken: {', '.join(parca)}."]
    if es:
        satir[0] += " " + " ".join(bas_buyuk(f"{_kosul_ad(k)} bu kuralda {adlar.KOSUL.get(k['esdeger'], k['esdeger'])} "
                                            f"ile aynı ölçüdür ve bir kez sayıldı.") for k in es)
    for k in tut:
        satir.append(f"- {bas_buyuk(_kosul_ad(k))}: seçilen kova {_kova_ifade(k['degisken'], k.get('secilen') or [])}. "
                     f"Örneklem dışında seçilen "
                     f"kovalarda {sayi(k.get('oos_secilen_n') or 0, 0)} işlem, {_hucre(k.get('oos_secilen_r'), 'ra')} R, "
                     f"isabet {_hucre(k.get('oos_secilen_isabet'), 'yz1')}; tamamlayanında "
                     f"{sayi(k.get('oos_tamamlayan_n') or 0, 0)} işlem, {_hucre(k.get('oos_tamamlayan_r'), 'ra')} R, "
                     f"isabet {_hucre(k.get('oos_tamamlayan_isabet'), 'yz1')}.")
    oos_asg = int(((u.O.get("kunye") or {}).get("uygulama_esik") or {}).get("kosul_oos") or 0)
    tutma_az = [k for k in tutma if int(k.get("oos_secilen_n") or 0) < oos_asg]
    tutma_ol = [k for k in tutma if k not in tutma_az]
    if tutma_ol:
        satir.append(f"- Tutmayanlar: {', '.join(_kosul_ad(k) for k in tutma_ol)}.")
    if tutma_az:
        satir.append(f"- Seçilen kovası örneklem dışında {sayi(oos_asg, 0)} işleme ulaşmadığı için tutmayanlar: "
                     + "; ".join(f"{_kosul_ad(k)}, {sayi(int(k.get('oos_secilen_n') or 0), 0)} işlem" for k in tutma_az)
                     + ".")
    if sec:
        satir.append(f"- Kova seçilemeyenler: {', '.join(_kosul_ad(k) for k in sec)}.")
    if hep:
        satir.append(f"- Bütün kovaları seçilenler: {', '.join(_kosul_ad(k) for k in hep)}.")
    ters = [k for k in ks if (k.get("ters_secim") or {}).get("hukum") in ("tuttu", "tutmadi")]
    ters_tut = [k for k in ters if k["ters_secim"]["hukum"] == "tuttu"]
    if ters:
        satir.append(f"- Ters seçim (örneklem içinde koşulsuz ortalamanın altında kalan kovalar seçilseydi): aynı ölçüt "
                     + ((f"{sayi(len(ters), 0)} değişkenin yalnız birinde tutardı: {_kosul_ad(ters_tut[0])}"
                         if len(ters_tut) == 1 else
                         f"{sayi(len(ters), 0)} değişkenin {tane(len(ters_tut), 'inde')} tutardı: "
                         f"{'; '.join(_kosul_ad(k) for k in ters_tut)}") if ters_tut else
                        f"{sayi(len(ters), 0)} değişkenin hiçbirinde tutmazdı") +
                     ". Kova farkları yalnız gürültüyse iki seçim aynı sıklıkla tutar.")
    return "\n".join(satir)


#: Koşul değişkenlerinin tanımı (ozellik.py ve gunluk.py'nin kurduğu ölçü): değişken → (giriş anında ne ölçer,
#: kovalar). Tanım tablosu değişken listesini künyeden okur; tanımı olmayan bir değişken üretimi düşürür. "{asya}"
#: , "{lon}" ve "{fx}" saat dilimi kurallarından TSİ karşılığıyla doldurulur.
KOSUL_TANIM = {
    "range_atr": ("Kuralın kendi yapısının büyüklüğü bölü günlük ATR. Yapı kurala göre değişir: aralık kırılımlarında "
                  "ve başarısız kırılımlarda kırılan aralığın yüksekliği (PDH/PDL'de önceki günün aralığı, sıkışmada "
                  "kutunun yüksekliği), iç mumda referans mumun aralığı, VWAP ve pivot kurallarında sinyal kapanışının "
                  "stopa uzaklığı, fiksing ve gün içi momentumda ölçüm mumunun gövdesi (kapanışla açılışı arasındaki uzaklık), N1 ve "
                  "N2'de ilk haber mumunun aralığı, N3 ve N4'te olay öncesi aralık, N5'te itkinin boyu (ilk haber "
                  "mumunun açılışından itki ucuna).", "tercil"),
    "asya_atr": ("Londra 00:00–08:00 ({asya}) yüksek − düşük farkı (en az 30 kotasyonlu dakikayla) bölü günlük ATR. "
                 "Yalnız Londra 08:00'den sonra gelen sinyalde tanımlı.", "tercil"),
    "onceki_gun_range_atr": ("Önceki FX işlem gününün (New York 17:00 → 17:00; {fx}) yüksek − düşük farkı bölü "
                             "günlük ATR.", "tercil"),
    "onceki_gun_yon": ("Önceki işlem gününün yönü (kapanış − açılış), işlemin yönüyle karşılaştırılır: önceki gün "
                       "işlem yönünde kapandıysa \"aynı yön\". Değişmeden kapanan gün kovaya girmez.",
                       "aynı yön · ters yön"),
    "nr4": ("Önceki işlem günü, kendisi dahil son dört işlem gününün en dar aralıklısı mı.", "NR4 · değil"),
    "nr7": ("Önceki işlem günü, kendisi dahil son yedi işlem gününün en dar aralıklısı mı.", "NR7 · değil"),
    "acilis_farki_atr": ("Londra 08:00'deki ilk dakikanın orta fiyatı ({lon}) ile önceki işlem gününün kapanışı "
                         "arasındaki fark, bölü günlük ATR, çarpı işlemin yönü: artı değer gece hareketinin işlem "
                         "yönünde olduğunu söyler. Yalnız Londra 08:00'den sonra gelen sinyalde tanımlı.", "tercil"),
    "oynaklik_yuzdelik": ("Günlük ATR'nin son 252 işlem günündeki yerini veren yüzdelik: o günlerin kaçta kaçında "
                          "ATR bugünkünden düşüktü (en az 60 günlük geçmişle).", "tercil"),
    "trend60": ("Sinyalden önce kapanan son 60 dakikalık mumun kapanışı, 60 dakikalık mumların EMA50'sinin üstünde mi "
                "altında mı; işlemin yönüyle karşılaştırılır (en az 50 mumluk geçmiş).",
                "trend yönünde · trend tersine"),
    "hafta_gunu": ("İşlem gününün etiketi. FX günü New York 17:00'de ({fx}) döner: pazartesinin işlem günü pazar "
                   "akşamı başlar.", "Pzt … Cum"),
    "haber_gunu": ("İşlem gününde takvimde o pariteyi ilgilendiren bir olay var mı: ABD olayları (tarım dışı istihdam, "
                   "TÜFE, FOMC kararı ve basın toplantısı) {n_parite} paritede, ECB kararı ve basın toplantısı EUR/USD'de, "
                   "BoE kararı GBP/USD'de. Planlanmış olay günün ilerisinde olsa da sabah bellidir. Önceden "
                   "duyurulmayan olay günün başında bilinmez: günü yalnız FX gününün başında ya da öncesinde olmuşsa "
                   "işaretler, gün içinde gelen olağanüstü karar o günü büyük olay günü yapmaz. FOMC'nin olağanüstü "
                   "kararları: {olaganustu}. {olaganustu_gun_basi}", "haber günü · değil"),
    "ay_sonu": ("Ayın son Londra iş günü (hafta içi ve İngiltere resmî tatili değil).", "ay sonu · değil"),
    "dst_gecis_haftasi": ("ABD ya da Avrupa saatinin değiştiği pazardan sonraki altı gün (pazartesi–cuma haftası).",
                          "geçiş haftası · değil"),
    "dst_ara_donem": ("Londra ile New York arasındaki farkın 5 değil 4 saat olduğu ara dönem: ABD yaz saatine "
                      "Avrupa'dan önce geçtiği mart haftaları ve Avrupa kışa ABD'den önce döndüğü ekim–kasım "
                      "haftaları.", "ara dönem · değil"),
}


def blok_kosul_tanim(u: Uretim, ctx: dict) -> str:
    """Koşul değişkenlerinin tanım tablosu (giriş dersi): değişken listesi künyeden, tanım KOSUL_TANIM'dan, okur adı
    adlar.KOSUL'dan. Üçü ayrışırsa (tanımı ya da adı olmayan değişken) üretim düşer."""
    deg = list(((u.O.get("kunye") or {}).get("kosul") or {}).get("degiskenler") or [])
    if not deg:
        raise SablonHatasi("kosul_tanim: künyede koşul değişkeni yok")
    eksik = [d for d in deg if d not in KOSUL_TANIM or d not in adlar.KOSUL]
    if eksik:
        raise SablonHatasi(f"kosul_tanim: tanımı ya da okur adı olmayan değişken: {eksik}")
    doldur = {"asya": blok_tsi(u, ctx, "", "Londra 00:00–08:00"), "lon": blok_tsi(u, ctx, "", "Londra 08:00"),
              "fx": blok_tsi(u, ctx, "", "New York 17:00"),
              "olaganustu": blok_olaganustu(u, ctx, "FOMC_karar"), "n_parite": _parite_sayisi(u),
              "olaganustu_gun_basi": _olaganustu_gun_basi(u)}
    govde = []
    for d in deg:
        tanim, kova = KOSUL_TANIM[d]
        if "|" in tanim + kova:
            raise SablonHatasi(f"kosul_tanim: {d} tanımı tablo ayracı taşıyor")
        govde.append([bas_buyuk(adlar.KOSUL[d]), tanim.format(**doldur), kova])
    return _tablo(["Değişken", "Giriş anında ne ölçer", "Kovalar"], govde, ["l", "l", "l"])


def _sinir_yaz(degisken: str, sinir: list) -> list[str]:
    """Tercil sınırlarının okunuşu: oynaklık yüzdeliği yüzde, öbürleri ATR katı. İki sınır aynı yazılırsa bir hane
    daha alınır (iki kova aynı sayıyla ayrılıyormuş gibi görünmesin)."""
    for b in (2, 3, 4):
        if degisken == "oynaklik_yuzdelik":
            s = [yuzde(x, b - 2) for x in sinir]
        else:
            s = [sayi(x, b) for x in sinir]
        if s[0] != s[1]:
            return s
    return s


def _kova_satir_ad(degisken: str, kova: str, sinir: list | None) -> str:
    ik = IKILI_KOVA.get(degisken)
    if sinir and kova in ("alt", "orta", "üst"):
        s1, s2 = _sinir_yaz(degisken, sinir)
        return {"alt": f"alt: x < {s1}", "orta": f"orta: {s1} ≤ x < {s2}", "üst": f"üst: x ≥ {s2}"}[kova]
    if ik and kova in (ik[0], "değil"):
        return ik[1] if kova == ik[0] else ik[2]
    return GUN_UZUN.get(kova, kova)


KOSUL_HUKUM_YAZ = {"tuttu": "tuttu", "tutmadi": "tutmadı", "secilmedi": "kova seçilmedi",
                   "hepsi": "bütün kovalar seçildi"}


def blok_kova_tablo(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Koşul kovalarının sayısal ayrıntısı (bir paritede, katlanır): her değişkenin kovaları sınırlarıyla, örneklem içi
    ve dışı işlem sayısı, işlem başına net R ve isabet; seçilen kova kalın, değişkenin satırında hüküm ve seçim eşiği
    (örneklem içi koşulsuz ortalama). Figürün çubukları bu tablonun R sütunlarıdır."""
    cift = cift or ana()
    b = ctx["B"]
    v = ((b.get("cift") or {}).get(cift) or {}).get("varsayilan") or {}
    ks = {k["degisken"]: k for k in (v.get("kosul") or [])}
    if not ks:
        return ""
    deg = list(((u.O.get("kunye") or {}).get("kosul") or {}).get("degiskenler") or adlar.KOSUL)
    ko = adlar.KOVA_OKUMA
    govde, es, olcmedi, tek = [], [], [], []
    for d in deg:
        k = ks.get(d)
        if k is None:
            olcmedi.append(adlar.KOSUL.get(d, d))
            continue
        if k.get("hukum") == "esdeger":
            es.append(f"{adlar.KOSUL.get(d, d)} ({adlar.KOSUL.get(k['esdeger'], k['esdeger'])} ile aynı ölçü)")
            continue
        kovalar = sorted(k.get("kovalar") or [], key=lambda kv: ko.index(kv["kova"]) if kv["kova"] in ko else 50)
        if len(kovalar) < 2:
            tek.append(f"{adlar.KOSUL.get(d, d)} ({_kova_satir_ad(d, kovalar[0]['kova'], None) if kovalar else '—'})")
            continue
        esik = k.get("ic_kosulsuz_r")
        bas = (f"{bas_buyuk(adlar.KOSUL.get(d, d))} — {KOSUL_HUKUM_YAZ.get(k.get('hukum'), '—')}"
               + (f" · eşik {_hucre(esik, 'ra')}" if esik is not None else ""))
        secilen = set(k.get("secilen") or [])
        for i, kv in enumerate(kovalar):
            ad = bas_buyuk(_kova_satir_ad(d, kv["kova"], k.get("sinir")))
            govde.append([bas if i == 0 else "", f"**{ad}**" if kv["kova"] in secilen else ad,
                          _hucre(kv.get("is_n"), "n"), _hucre(kv.get("is_r"), "ra"), _hucre(kv.get("is_isabet"), "yz1"),
                          _hucre(kv.get("oos_n"), "n"), _hucre(kv.get("oos_r"), "ra"),
                          _hucre(kv.get("oos_isabet"), "yz1")])
    if not govde:
        return ""
    K = u.O.get("kunye") or {}
    ic = f"{str(K.get('baslangic'))[:4]}–{str(K.get('ic_bitis'))[:4]}"
    dis = f"{str(K.get('dis_baslangic'))[:4]} →"
    tablo = _tablo(["Değişken", "Kova", "İçi işlem", "İçi R", "İçi isabet", "Dışı işlem", "Dışı R", "Dışı isabet"],
                   govde, ["l", "l"] + ["r"] * 6)
    dip = [f"İçi: örneklem içi ({ic}); dışı: örneklem dışı ({dis}). R: işlem başına net R; isabet: net sonucu artı "
           f"kapanan işlemlerin payı. Kalın kova örneklem içinde seçilendir: en az {u.ON['kosul']['asgari_kova_islem']} "
           f"işlemle eşiğin, yani değişkenin tanımlı olduğu işlemlerin örneklem içi koşulsuz ortalamasının üstünde. "
           f"Sürekli değişkenlerin sınırları örneklem içinin tercilleridir ve örneklem dışına olduğu gibi taşınır; "
           f"örneklem dışında kovalar bu yüzden eşit dolmaz."]
    if es:
        dip.append("Tabloda bir kez: " + "; ".join(es) + ".")
    if tek:
        dip.append("Tek kovalı, kıyas kurulamayan: " + "; ".join(tek) + ".")
    if olcmedi:
        dip.append("Bu kuralda ölçülemeyen: " + ", ".join(olcmedi) + " (tanımsız ya da tercile bölünemedi).")
    return "\n".join(["<details>", f"<summary>Kova ayrıntısı — {PARITE[cift]}: sınırlar, işlem sayısı, net R, "
                      "isabet</summary>", "", '<div class="sayi-tablo">', "", tablo, "", "</div>", "",
                      "_" + " ".join(dip) + "_", "", "</details>"])


def _kosul_parite_durumu(ks_ana: dict, ks_c: dict) -> str:
    """Ana paritede tutan bir değişkenin başka paritedeki durumu: aynı kova seçimiyle tuttu · başka kova seçimiyle tuttu · tutmadı ·
    seçim kurulamadı."""
    h = ks_c.get("hukum")
    if h == "tuttu":
        if set(ks_c.get("secilen") or []) == set(ks_ana.get("secilen") or []):
            return "aynı kova seçimiyle tuttu"
        return f"başka kova seçimiyle tuttu ({_kova_ifade(ks_c.get('degisken', ''), ks_c.get('secilen') or [])})"
    return {"tutmadi": "tutmadı", "secilmedi": "kova seçilmedi", "hepsi": "bütün kovalar seçildi",
            "esdeger": "aynı ölçü"}.get(h, "—")


def _arti_pariteler(b: dict) -> list[str]:
    """Örneklem dışında artı kalan pariteler (tek tanım adlar.arti_pariteler; figürler de onu okur)."""
    return adlar.arti_pariteler(b, _ciftler(b))


def _kosul_tablosu(b: dict) -> dict:
    """Parite → değişken → koşul kaydı (varsayılan)."""
    return {c: {x["degisken"]: x for x in ((b["cift"][c].get("varsayilan") or {}).get("kosul") or [])}
            for c in _ciftler(b)}


def kosul_adaylari(b: dict, ters: bool = False) -> list[dict]:
    """Kontrol listesinin "Ne zaman" adayları: en az İKİ paritede AYNI kovayla tutan değişkenler. Bir paritede tutan
    koşul şansla da tutar; aynı kova seçiminin başka bir paritede de örneklem dışında aynı yönde durması ikinci bir
    gözlemdir, şansı ayıklamaz: `ters` aynı kuralı ters seçime (örneklem içinde koşulsuz ortalamanın ALTINDA kalan
    kovalar) uygular ve kuralın şans tabanını verir. Kayıt: değişken, kova ve o kovayla tutan pariteler (kayıtlarıyla)."""
    tab = _kosul_tablosu(b)
    grup: dict = {}
    for c, ks in tab.items():
        for ad, x in ks.items():
            y = (x.get("ters_secim") or {}) if ters else x
            if y.get("hukum") == "tuttu":
                grup.setdefault((ad, frozenset(y.get("secilen") or [])), []).append((c, y))
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
            parca.append(f"{PARITE[c]} {'tuttu' if h == 'tuttu' else 'tutmadı'} (seçilen {_kova_ifade(x.get('degisken', degisken), x.get('secilen') or [])}: "
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


def _pip_a(v: float) -> str:
    """İşaretli pip yazımı, _pip'in hane kuralıyla: aynı cümlede aynı sonuç iki ayrı yuvarlamayla geçmesin."""
    return sayi(v, 1 if abs(v * 10 - round(v * 10)) < 1e-6 else 2, arti=True)


def _geri(s: str) -> float:
    """Okur yazımındaki bir sayıyı (binlik nokta, ondalık virgül, eksi U+2212, artı) sayıya geri çevirir."""
    return float(s.replace(".", "").replace(",", ".").replace("−", "-").replace("+", ""))


def _oran_yaz(pay: str, payda: str) -> str:
    """"a / b = c" satırında c: okurun gördüğü a ve b yazımlarının oranı, iki haneyle (kayıttaki üç haneli değeri
    yeniden yuvarlamak 0,785 → 0,79 yazar, oysa 22,8 / 29,05 = 0,78)."""
    return sayi(_geri(pay) / _geri(payda), 2, arti=True)


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
        parca.append(bas_buyuk(sv) + f", {fiyat_yaz(i['giris_f'], c)} ({'ask' if i['yon'] > 0 else 'bid'}, "
                     f"kayma dahil)")
        if stopsuz or i.get("stop") is None:
            parca[-1] += f"; stop yok, R birimi girişteki ATR: {_pip(i['R_pip'])} pip"
        else:
            parca[-1] += f"; stop {fiyat_yaz(i['stop'], c)} ({_pip(i['R_pip'])} pip)"
        if i.get("hedef") is not None:
            parca[-1] += f"; hedef {fiyat_yaz(i['hedef'], c)}"
        parca[-1] += "."
        parca.append(f"Çıkış {saat_tsi(i['cikis_t'])} TSİ'de {fiyat_yaz(i['cikis_f'], c)}, "
                     f"{adlar.neden_ad(i, u.O['kunye']['gun_sonu_et'])}: {sayi(adlar.islem_r(i), 2, arti=True)} R "
                     f"({_pip_a(i['pnl_pip'])} pip, maliyet dahil). İşlem boyunca en kötü "
                     f"{_mae_yaz(i, stopsuz)}, en iyi {sayi(i['mfe_r'], 2, arti=True)} R.")
        satir.append("- " + " ".join(parca))
    return "\n".join(satir) if satir else "_Örneklem dışında işlem yok._"


def _mae_yaz(i: dict, stopsuz: bool) -> str:
    """İşlemin en kötü noktası (R). Stoplu ve stopta kapanmamış bir işlemde iki haneli yuvarlama −1,00 yazıyorsa üç
    hane basılır: stopa değmemiş bir işlem stopa değmiş gibi okunmasın."""
    m = float(i["mae_r"])
    if (not stopsuz and i.get("stop") is not None and i.get("neden") not in (1, 4, 5)
            and abs(round(m, 2)) >= 1.0 and abs(m) < 1.0):
        return f"{sayi(m, 3, arti=True)} R (stopun hemen içinde)"
    return f"{sayi(m, 2, arti=True)} R"


def blok_zaman(u: Uretim, ctx: dict) -> str:
    """Olayların TSİ saati, dört saat rejiminde (temsilci günler)."""
    z = u.O["zaman"]
    rejimler = z["tablo"]
    olaylar = z.get("olay_sira") or [k for k in rejimler[0] if k not in ("gun", "londra_ny", "rejim")]
    bas = ["Olay (TSİ saati)"] + [z["rejim_adi"][r["rejim"]].split(" (")[0] + f" ({tarih(r['gun'])})" for r in rejimler]
    govde = [[o] + [r.get(o, "—") for r in rejimler] for o in olaylar]
    govde.append(["Londra–New York farkı (saat)"] + [str(r["londra_ny"]) for r in rejimler])
    return _tablo(bas, govde)


def _tsi(gun: str, saat: str, bolge: str) -> datetime:
    from zoneinfo import ZoneInfo
    y, a, d = (int(x) for x in gun[:10].split("-"))
    hh, mm = (int(x) for x in saat.split(":"))
    return datetime(y, a, d, hh, mm, tzinfo=ZoneInfo(bolge)).astimezone(ZoneInfo("Europe/Istanbul"))


def _tsi_tek(gun: str, saat: str, bolge: str) -> str:
    """Tek bir günün yerel saatinin TSİ karşılığı ("TSİ 15:30"); TSİ'de takvim günü değişiyorsa günüyle birlikte
    ("TSİ 16.03.2020 00:00"). Tarihli her olay saati bu tanımla yazılır (bölge IANA adıyla)."""
    ts = _tsi(gun, saat, bolge)
    ek_gun = "" if ts.strftime("%Y-%m-%d") == gun[:10] else f" {ts:%d.%m.%Y}"
    return f"TSİ{ek_gun} {ts:%H:%M}"


#: TSİ karşılığının üç saat rejimi, temsilci günlerle: iki şehir de yaz saatinde · ikisi de kış saatinde · ara
#: hafta (ABD yaz, İngiltere kış saatinde). Giriş dersinin saat tablosuyla aynı rejimler; yıl metinde geçmez.
TSI_REJIM = adlar.TSI_REJIM
SEHIR_BOLGE = adlar.SEHIR_BOLGE


def blok_tsi(u: Uretim, ctx: dict, birlestir: str, *saatler: str) -> str:
    """Yerel saatlerin TSİ karşılığı: {{! tsi "→" "Londra 08:00" "New York 14:00" }} → "TSİ yazın 10:00 → 21:00,
    kışın 11:00 → 22:00, ara haftalarda 11:00 → 21:00". Her argüman "<şehir> SS:DD" ya da "<şehir> SS:DD–SS:DD";
    birlestir saatleri birbirine bağlar ("→", "ya da", "" tek saat). Tanım adlar.tsi_yaz'da (figürler de onu okur)."""
    try:
        return adlar.tsi_yaz(saatler, birlestir)
    except ValueError as e:
        raise SablonHatasi(str(e)) from None


def blok_gun_sonu_tsi(u: Uretim, ctx: dict) -> str:
    """Gün sonu çıkışının (künye: gun_sonu_et, New York) TSİ karşılığı; saat künyeden okunur, elle yazılmaz."""
    return blok_tsi(u, ctx, "", f"New York {u.O['kunye']['gun_sonu_et']}")


def blok_zaman_diger(u: Uretim, ctx: dict) -> str:
    """Tablonun gösterdiği bugünkü olağan saatlerin dışında kalan, örneklemdeki olay saatleri ve TSİ karşılıkları
    (takvimin kendi kayıtlarından): bir olayın son kullanılan saati olağan sayılır, öbürleri yazılır. Tek günlük
    saatlerde TSİ o günün kendisinden; dönem boyu süren saatlerde kış (15 Ocak) ve yaz (15 Temmuz) karşılığı."""
    sayim = (u.O.get("takvim") or {}).get("sayim") or {}
    parca = []
    for o in [x for x in olay_sira(u) if x in sayim]:
        ar = sayim[o].get("saat_aralik") or {}
        if len(ar) < 2:
            continue
        olagan = max(ar, key=lambda k: (ar[k][1], (sayim[o].get("saat") or {}).get(k, 0)))
        for k in sorted((k for k in ar if k != olagan), key=lambda k: ar[k][0]):
            saat, bolge = k.split(" ", 1)
            n = int((sayim[o].get("saat") or {}).get(k, 0))
            ilk, son = ar[k]
            yer = BOLGE_AD.get(bolge, bolge)
            if ilk == son:
                parca.append(f"{adlar.OLAY.get(o, o)}, {tarih(ilk)} {saat} {yer} ({_tsi_tek(ilk, saat, bolge)})")
            elif n <= 3:
                parca.append(f"{adlar.OLAY.get(o, o)}, {saat} {yer}: {n} olay, {tarih(ilk)} ve {tarih(son)} (TSİ "
                             f"{_tsi(ilk, saat, bolge):%H:%M} ve {_tsi(son, saat, bolge):%H:%M})")
            else:
                parca.append(f"{adlar.OLAY.get(o, o)}, {saat} {yer}: {n} olay, {tarih(ilk)} → {tarih(son)} "
                             f"({blok_tsi(u, ctx, '', f'{yer} {saat}')})")
    if not parca:
        return ""
    return ("Tablo bugünkü olağan saatleri verir. Örneklemde başka saatte yapılan olaylar: " + "; ".join(parca) + ".")


def blok_dst(u: Uretim, ctx: dict) -> str:
    """Saat değişimi ara dönemleri (Londra–New York farkı 4 saat), yıl yıl."""
    z = u.O["zaman"]
    govde = []
    for y, donemler in sorted(z["ara_donem"].items()):
        govde.append([y] + ["; ".join(f"{tarih(d['ilk'])[:5]}–{tarih(d['son'])[:5]}" for d in donemler)])
    return _tablo(["Yıl", "Ara dönemler (Londra–NY farkı 4 saat)"], govde, ["l", "l"])


#: Brüt sonucun "maliyetten önce de eksi" diye kesin yazılabilmesi için asgari işlem (rastgele yön sınamasının asgarisiyle
#: aynı): daha az işlemde aralık kurulsa da kesin bir hüküm kurulmaz.
KESIN_ASGARI = 20


def _brut_alt_tur(m: dict) -> str:
    """Brütü artı olmayan dönemin alt türü: "kesin" (brüt aralığı bütünüyle sıfırın altında, en az KESIN_ASGARI
    işlem) · "az" (daha az işlem) · "ayrismiyor" (aralık sıfırı kapsıyor ya da kurulamadı)."""
    if int(m.get("n") or 0) < KESIN_ASGARI:
        return "az"
    ust = m.get("ga_brut_ust")
    return "kesin" if ust is not None and math.isfinite(ust) and ust < 0 else "ayrismiyor"


def _brut_aralik(m: dict) -> str:
    alt, ust = m.get("ga_brut_alt"), m.get("ga_brut_ust")
    if alt is None or ust is None or not (math.isfinite(alt) and math.isfinite(ust)):
        return "aralık kurulamadı"
    return f"aralık {_hucre(alt, 'ra')} / {_hucre(ust, 'ra')}"


#: Brütü artı olmayan dönemin hükmü, alt türe göre. Ölçülen yürütme makası ödeyen dolumdur; pasif ya da limit emirle
#: makasın bir kısmını kazanan yürütme ölçülmedi (metodoloji, "Ölçülmeyenler"), yani hüküm ondan söz etmez.
BRUT_HUKUM = {
    "kesin": "makası ödeyen bir dolumla artıya dönmez",
    "ayrismiyor": "bu örneklemde makası ödeyen bir dolum onu artıya çevirmez, ama brüt sıfırdan ayrışmıyor",
    "az": "bu örneklemde makası ödeyen bir dolum onu artıya çevirmez; bu kadar işlemle kesin bir hüküm kurulmaz",
}


def _brut_eksi_okuma(m: dict) -> str:
    t = _brut_alt_tur(m)
    bas = "maliyetten önce de eksi" if t == "kesin" else "orta fiyattan orta fiyata da artı değil"
    az = f"; {sayi(int(m.get('n') or 0), 0)} işlem, az işlem" if t == "az" else ""
    return f"{bas} (brüt {_hucre(m.get('brut_r'), 'ra')} R, {_brut_aralik(m)}{az}): {BRUT_HUKUM[t]}"


def _maliyet_okuma(u: Uretim, v: dict, d: str) -> str:
    """Bir dönemin maliyet okuması (d: tum | oos), brüte bağlı. Sıra: brüt artı değil (aralığa ve işlem sayısına göre)
    → yalnız makas bile eksi (sonucun sıfıra indiği makas payıyla) → haber kayması eksiye çeviriyor → başabaş kayma
    (ya da ızgaranın sonunda da artı)."""
    m = v.get(d) or {}
    brut, net = m.get("brut_r"), m.get("beklenti_r")
    if brut is None or net is None or not m.get("n"):
        return "ölçülemedi (işlem yok)"
    ym = ((v.get("yalniz_makas") or {}).get(d) or {}).get("beklenti_r")
    m0 = (((v.get("maliyet") or {}).get("0.0") or {}).get(d) or {}).get("beklenti_r")
    bb = v.get("basabas_kayma_pip" + ("" if d == "tum" else "_oos"))
    hk = u.O["kunye"]["haber_kayma_pip"]
    tk = u.O["kunye"]["temel_kayma_pip"]
    haber = ((v.get("haber_payi_donem") or {}).get(d) or 0) >= 0.005
    if brut <= 0:
        return _brut_eksi_okuma(m)
    if ym is not None and ym <= 0:
        pay = _makas_payi(v, d)
        return (f"brüt artı ({_hucre(brut, 'ra')} R) ama kayma hiç yokken, yalnız gerçek makasla bile eksi "
                f"({_hucre(ym, 'ra')} R): kenar varsa bu makastan küçük"
                + (f"; sonuç makas bu verininkinin {yuzde_ek(pay, 'i')} olduğunda sıfıra iner" if pay is not None
                   else ""))
    if m0 is not None and m0 <= 0:
        return (f"yalnız makasla artı ({_hucre(ym, 'ra')} R); temel kayma sıfırken bile haber penceresindeki "
                f"{sayi(hk, 1)} pip kayma sonucu eksiye çeviriyor ({_hucre(m0, 'ra')} R)")
    if bb is None:
        return f"dolum başına 2 pip kaymada bile artı ({sayi(tk, 1)} pip kaymada net {_hucre(net, 'ra')} R)"
    return (f"makasın üstüne dolum başına {_hucre(bb, 's2')} pip kayma"
            + (f" (haber penceresinde ayrıca {sayi(hk, 1)} pip)" if haber else "") +
            f" net beklentiyi sıfıra indiriyor ({sayi(tk, 1)} pip kaymada net {_hucre(net, 'ra')} R)")


def _maliyet_turu(v: dict, d: str) -> str | None:
    """Maliyet okumasının türü, `_maliyet_okuma` ile aynı sırayla: "brut" (brüt de artı değil) · "makas" (yalnız
    makasla bile eksi) · "haber" (haber penceresinin kayması eksiye çeviriyor) · "artı" (2 pip kaymada bile artı) ·
    "basabas" (başabaş kayma); ölçülemeyen dönem None."""
    m = v.get(d) or {}
    if m.get("brut_r") is None or m.get("beklenti_r") is None or not m.get("n"):
        return None
    if m["brut_r"] <= 0:
        return "brut"
    ym = ((v.get("yalniz_makas") or {}).get(d) or {}).get("beklenti_r")
    if ym is not None and ym <= 0:
        return "makas"
    m0 = (((v.get("maliyet") or {}).get("0.0") or {}).get(d) or {}).get("beklenti_r")
    if m0 is not None and m0 <= 0:
        return "haber"
    return "artı" if v.get("basabas_kayma_pip" + ("" if d == "tum" else "_oos")) is None else "basabas"


def blok_basabas(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Kontrol listesinin maliyet maddesi (ana parite): iki dönemde, brüte bağlı okuma. İki dönemin okuması aynı
    türdeyse (`_maliyet_turu`) tek cümle kurulur ve iki dönemin sayıları yan yana durur; aynı yan cümle iki kez
    yazılmaz. Haber kaymasının çevirdiği tür iki ayrı sayı çifti taşıdığı için dönem dönem yazılır."""
    cift = cift or ana()
    v = (((ctx["B"].get("cift") or {}).get(cift) or {}).get("varsayilan")) or {}
    to, tt = _maliyet_turu(v, "oos"), _maliyet_turu(v, "tum")
    # Bütün dönem 2024 → penceresini de kapsar: iki sayı iki bağımsız örneklem değildir ve öyle yazılmaz.
    iki = "2024 → penceresinde ve onu kapsayan bütün dönemde"
    if to and to == tt and to != "haber":
        if to == "brut":
            ao, at = _brut_alt_tur(v["oos"]), _brut_alt_tur(v["tum"])
            if ao == at:
                bas = "maliyetten önce de eksi" if ao == "kesin" else "orta fiyattan orta fiyata da artı değil"
                az = (f"; {sayi(int(v['oos'].get('n') or 0), 0)} · {sayi(int(v['tum'].get('n') or 0), 0)} işlem, az işlem"
                      if ao == "az" else "")
                return (f"{PARITE[cift]}: {bas}, {iki} (brüt {_hucre(v['oos']['brut_r'], 'ra')} R, "
                        f"{_brut_aralik(v['oos'])} · {_hucre(v['tum']['brut_r'], 'ra')} R, {_brut_aralik(v['tum'])}{az}): "
                        f"{BRUT_HUKUM[ao]}.")
            return (f"{PARITE[cift]}, örneklem dışı (2024 →): {_brut_eksi_okuma(v['oos'])}. Bütün dönem (2024 →'yü "
                    f"kapsar): {_brut_eksi_okuma(v['tum'])}.")
        ym = {d: ((v.get("yalniz_makas") or {}).get(d) or {}).get("beklenti_r") for d in ("oos", "tum")}
        tk = u.O["kunye"]["temel_kayma_pip"]
        net = f"{sayi(tk, 1)} pip kaymada net {_hucre(v['oos']['beklenti_r'], 'ra')} R · {_hucre(v['tum']['beklenti_r'], 'ra')} R"
        if to == "makas":
            po, pt = _makas_payi(v, "oos"), _makas_payi(v, "tum")
            pay = (f"; sonuç makas bu verininkinin {yuzde_ek(po, 'i')} · {yuzde_ek(pt, 'i')} olduğunda sıfıra iner"
                   if po is not None and pt is not None else "")
            return (f"{PARITE[cift]}: brüt artı, {iki} ({_hucre(v['oos']['brut_r'], 'ra')} R · "
                    f"{_hucre(v['tum']['brut_r'], 'ra')} R), ama kayma hiç yokken, yalnız gerçek makasla bile eksi "
                    f"({_hucre(ym['oos'], 'ra')} R · {_hucre(ym['tum'], 'ra')} R): kenar varsa bu makastan küçük{pay}.")
        if to == "basabas":
            haber = (f" (haber penceresinde ayrıca {sayi(u.O['kunye']['haber_kayma_pip'], 1)} pip)"
                     if max(((v.get("haber_payi_donem") or {}).get(d) or 0) for d in ("oos", "tum")) >= 0.005 else "")
            return (f"{PARITE[cift]}: {iki} makasın üstüne dolum başına kayma{haber} net beklentiyi sıfıra "
                    f"indiriyor: 2024 → {_hucre(v.get('basabas_kayma_pip_oos'), 's2')} pip · bütün dönem "
                    f"{_hucre(v.get('basabas_kayma_pip'), 's2')} pip ({net}).")
        if to == "artı":
            return f"{PARITE[cift]}: {iki} dolum başına 2 pip kaymada bile artı ({net})."
    return (f"{PARITE[cift]}, örneklem dışı (2024 →): {_maliyet_okuma(u, v, 'oos')}. Bütün dönem (2024 →'yü kapsar): "
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
    parca = [f"Örneklem dışında ({tarih(k['dis_baslangic'])} → {tarih(k['bitis'])}) {adlar.varsayilan_ad(b)}ın"]
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
        if brut > 0 and net > 0:
            parca.append(f"Maliyetten önce (orta fiyattan orta fiyata) işlem başına {_hucre(brut, 'ra')} R; gerçek "
                         f"makas ve kayma bunun {sayi(brut - net, 2)} R'sini götürüyor.")
        elif brut > 0:
            parca.append(f"Maliyetten önce (orta fiyattan orta fiyata) işlem başına {_hucre(brut, 'ra')} R; gerçek "
                         f"makas ve kayma işlem başına {sayi(brut - net, 2)} R tutuyor, brüt kazancın tamamını siliyor "
                         f"ve sonucu {_hucre(net, 'ra')} R'ye çeviriyor.")
        else:
            parca.append(f"Maliyetten önce de artı değil (orta fiyattan orta fiyata işlem başına "
                         f"{_hucre(brut, 'ra')} R); makas ve kayma işlem başına ayrıca {sayi(brut - net, 2)} R.")
    return " ".join(parca)


def rastgele_duyarlilik_not(v: dict, d: str = "oos") -> str:
    """Rastgele yön yüzdeliğinin duyarlılığı (kosu.derin → saglamlik.rastgele_duyarlilik; yalnız yüzdeliği 90 ve üstü
    olan bileşimde ölçülür): en iyi bir ve üç işlem çıkınca yüzdelik ve sabit bir tohum listesinde eşiği geçme payı.
    Pay %5–95 arasındaysa "sınırda": eşiğin hangi yanında kaldığı tohuma bağlıdır. Ölçülmemişse boş."""
    dy = ((v.get("rastgele_duyarlilik") or {}).get(d)) or {}
    if not dy:
        return ""
    parca = []
    h1, e1 = dy.get("haric_1"), (dy.get("en_iyi_1_r") or [None])[0]
    if h1 is not None and math.isfinite(h1) and e1 is not None:
        parca.append(f"{_hucre(e1, 'ra')} R'lik en iyi işlem çıkınca {sayi(h1, 1)}")
    h3 = dy.get("haric_3")
    if h3 is not None and math.isfinite(h3):
        parca.append(f"en iyi üç işlem çıkınca {sayi(h3, 1)}")
    pay = dy.get("tohum_pay")
    if pay is not None and dy.get("tohum_sayisi"):
        parca.append(f"{sayi(int(dy['tohum_sayisi']), 0)} tohumun {yuzde_ek(pay, 'inde')} eşiği geçer")
    if not parca:
        return ""
    return ("sınırda: " if dy.get("sinirda") else "") + "; ".join(parca)


def blok_rastgele_cumle(u: Uretim, ctx: dict) -> str:
    """Rastgele yön sınaması (tanım giriş dersinde): dört paritenin yüzdeliği; sınama yapılamayan paritede sebebi.
    Yüzdeliği eşiğin kıyısında ya da üstünde olan paritenin yanında duyarlılığı (rastgele_duyarlilik_not)."""
    b = ctx["B"]
    var, yok = [], []
    for c in _ciftler(b):
        v = b["cift"][c].get("varsayilan") or {}
        r = ((v.get("rastgele") or {}).get("oos") or {})
        if r.get("yuzdelik") is not None and math.isfinite(r["yuzdelik"]):
            dn = rastgele_duyarlilik_not(v)
            var.append(f"{PARITE[c]} {sayi(r['yuzdelik'], 1)}" + (f" ({dn})" if dn else ""))
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


#: Deflated Sharpe olasılığının geçme eşiği (Bailey ve López de Prado'nun okuması).
DSR_ESIK = 0.95
#: Yayılım eşiğinin gürültü eşiğine oranı bunu aşınca, yayılım şanstan çok denemelerin sistematik farkını taşır
#: (saf gürültüde iki eşik yaklaşık eşittir); betimleyici bir sınırdır, hükme girmez.
YAYILIM_ORAN = 2.0


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
        s += (f"; {tane(komb - d['n_deneme'], 'i')} hiç işlem açmadığı için Sharpe'ı tanımsız, deflated Sharpe "
              f"{sayi(d['n_deneme'], 0)} deneme üzerinden")
    nt = d.get("n_tekil")
    if nt and nt < d["n_deneme"]:
        s += (f". Denemelerin {tane(nt, 'i')} işlem bakımından birbirinden farklıdır; öbürleri bir başkasıyla birebir "
              f"aynı işlemleri verir (bir parametresi o kombinasyonda hiçbir işlemi değiştirmez). Yayılım eşiğine göre "
              f"deflated Sharpe tekil denemelerle {_hucre(d.get('dsr_tekil'), 's2')}, bütün denemelerle "
              f"{_hucre(d.get('dsr'), 's2')} (tablodaki)")
    s += "."
    sr = d.get("sr_yillik")
    if sr is None:
        return s
    if sr <= 0:
        return (s + f" Seçilen en iyi kombinasyonun bile örneklem içi yıllık Sharpe'ı {_hucre(sr, 'sh')}: deflated "
                f"Sharpe'ın sorusu (en iyi sonuç şansla açıklanır mı) burada sorulmaz, açıklanacak bir artı yok.")
    g, y = d.get("sr0_gurultu_yillik"), d.get("sr0_yillik")
    dg, dy = d.get("dsr_gurultu"), d.get("dsr")
    s += (f" En iyisinin örneklem içi yıllık Sharpe'ı {_hucre(sr, 'sh')}. Bu kadar denemede salt şansın üreteceği "
          f"beklenen en yüksek değer (gürültü eşiği) {_hucre(g, 's2')}; denemelerin kendi Sharpe yayılımından kurulan "
          f"eşik (yayılım eşiği, Bailey–López de Prado) {_hucre(y, 's2')}. Deflated Sharpe olasılığı gürültü eşiğine "
          f"göre {_hucre(dg, 's2')}, yayılım eşiğine göre {_hucre(dy, 's2')}")
    gecen = [ad for ad, x in (("gürültü", dg), ("yayılım", dy)) if x is not None and x >= DSR_ESIK]
    s += (" (ikisi de 0,95'in altında: seçim şansla açıklanabilir)." if not gecen else
          f" ({' ve '.join(gecen)} eşiğine göre 0,95'in üstünde: seçim bu eşikle şansla açıklanmaz).")
    if g and y and g > 0 and y > YAYILIM_ORAN * g:
        s += (f" Yayılım eşiği gürültü eşiğinin {sayi(y / g, 1)} katı: denemelerin Sharpe'ları örnekleme gürültüsünün "
              f"açıklayabileceğinden geniş yayılıyor (maliyet bazı kombinasyonları sistematik olarak eksiye iter); bu "
              f"ızgarada yayılım eşiği şansın değil yayılımın ölçüsüdür ve seçim gürültü eşiğine göre okunur.")
    return s


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
        if (ky.get("en_iyi_esit") or 1) == 1:
            s += (f" En iyi tek işlem ({tarih(ky['en_iyi_gun'])}, {_hucre(ky['en_iyi_r'], 'ra')} R, riski "
                  f"{_pip(round(ky['en_iyi_R_pip'], 2))} pip) çıkarılınca {_hucre(ky['r_tek_haric'], 'ra')} R, en iyi üç "
                  f"işlem çıkarılınca {_hucre(ky['r_uc_haric'], 'ra')} R.")
        else:
            s += (f" En iyi sonuç tek bir işlemin değil: {sayi(ky['en_iyi_esit'], 0)} işlem aynı {_hucre(ky['en_iyi_r'], 'ra')} "
                  f"R ile kapandı (riskleri {_pip(round(ky['en_iyi_R_pip_alt'], 2))}–{_pip(round(ky['en_iyi_R_pip_ust'], 2))} "
                  f"pip). Biri çıkarılınca {_hucre(ky['r_tek_haric'], 'ra')} R, üçü çıkarılınca "
                  f"{_hucre(ky['r_uc_haric'], 'ra')} R.")
    return s


#: Örneklem dışı sonucun büyük olay günlerinde yoğunlaştığını yazma eşiği (betimleyici): işlemlerin en çok dörtte
#: biri, net toplamın en az yarısı. Bütün işlemleri olay günü olan haber kurallarında soru yoktur.
YOGUNLUK_PAY, YOGUNLUK_ISLEM = 0.5, 0.25


def _olay_yogunluk_cumle(u: Uretim, c: str, cv: dict) -> str:
    """Artı kalan bir paritenin örneklem dışı net sonucu büyük olay günlerinde mi toplanıyor (ders_olcum.
    haber_gunu_yogunlugu): pay, iki kümenin işlem başına R'si, aynı kova seçiminin örneklem içi sonucu; en iyi tek işlem bir
    olay günündeyse o çıkarıldığında kalan pay. Koşul tablosunun "tutmadı" hücresi bunu göstermez: örneklem içinde
    olay günleri eksi kaldığı için seçilen kova olay dışı günlerdir."""
    y = cv.get("haber_yogunluk") or {}
    if not y or y.get("islem_payi") is None or y["islem_payi"] >= 1:
        return ""
    if y["pay"] < YOGUNLUK_PAY or y["islem_payi"] > YOGUNLUK_ISLEM:
        return ""
    kova = next((kv for k in ((cv.get("varsayilan") or {}).get("kosul") or []) if k.get("degisken") == "haber_gunu"
                 for kv in (k.get("kovalar") or []) if kv.get("kova") == "haber günü"), None)
    if kova is None:
        raise SablonHatasi(f"olay_yogunluk: {c} koşul kaydında büyük olay günü kovası yok")
    pay = "tamamı" if y["pay"] >= 1 else f"≈{yuzde_ek(y['pay'], 'i')}"
    s = (f"{PARITE[c]}'de örneklem dışı net sonucun {pay} {sayi(y['n_olay'], 0)} büyük olay günü işleminden geliyor "
         f"(işlem başına {_hucre(y['olay_ort'], 'ra')} R); öbür {sayi(y['n'] - y['n_olay'], 0)} işlemde "
         f"{_hucre(y['olay_disi_ort'], 'ra')} R. Aynı kova örneklem içinde {sayi(kova['is_n'], 0)} işlemde "
         f"{_hucre(kova['is_r'], 'ra')} R'ydi.")
    # En iyi değeri birden çok işlem paylaşıyorsa (2R hedefleri) "en iyi tek işlem" yoktur: hangisinin seçildiği sıranın
    # tesadüfüdür ve cümle kurulmaz.
    if y.get("en_iyi_olay_gunu") and y.get("en_iyi_tekil"):
        # Ölçüm katmanı kalan toplam sıfır ya da eksiyse payı yazmaz (None): eksi bir toplamın payı okunmaz.
        p_ = y.get("pay_en_iyi_haric")
        if p_ is None:
            kalan = "kalan net sonuç sıfır ya da eksi"
        elif p_ >= 1:
            kalan = "da kalan sonucun tamamı olay günlerinden geliyor"
        elif p_ > 0:
            kalan = f"da kalan sonucun ≈{yuzde_ek(p_, 'i')} olay günlerinden geliyor"
        else:
            kalan = "olay günlerinin kalan toplamı sıfır ya da eksi"
        s += f" En iyi tek işlem ({tarih(y['en_iyi_gun'])}) de bir büyük olay günündeydi; o çıkarıldığında {kalan}."
    return s


def _varyant_artilari(b: dict) -> list[tuple[str, str, list[str]]]:
    """Varyant tablolarında (bir parametre varsayılan dışı değerde, öbürleri varsayılanda) örneklem dışında artı kalan
    bileşimler: (parametre, değer, pariteler). Varsayılan "çalışmıyor" diye hükmedilince mutlak cümle bunları
    görmeden kurulamaz; hüküm varsayılanın biçimiyle daraltılır ve bu biçimler adıyla yazılır."""
    v = b.get("varsayilan") or {}
    out: dict = {}
    for c in _ciftler(b):
        for pa, vals in ((b["cift"][c].get("varyant") or {}).items()):
            for d, x in (vals or {}).items():
                if str(v.get(pa)) == str(d):
                    continue
                r = (x.get("oos") or {}).get("beklenti_r")
                if r is not None and r > 0:
                    out.setdefault((pa, str(d)), []).append(c)
    return [(pa, d, cs) for (pa, d), cs in out.items()]


def _varyant_arti_cumle(u: Uretim, b: dict, param: str, d: str, arti: list[str]) -> str:
    """Varyantın artı kalan paritesi: örneklem içi ve dışı net R, işlem ve pip; hükmü en çok "zayıf"tır, çünkü bu
    biçimin %95 aralığı ve rastgele yön sınaması hesaplanmadı. Öbür pariteler aynı biçimde sayılarıyla."""
    aile = b.get("aile") or ""
    x = {c: (((b["cift"][c].get("varyant") or {}).get(param) or {}).get(d) or {}) for c in _ciftler(b)}
    parca = []
    for c in arti:
        o, i = x[c].get("oos") or {}, x[c].get("is") or {}
        parca.append(f"{PARITE[c]} örneklem dışında {_hucre(o.get('beklenti_r'), 'ra')} R ({sayi(o.get('n') or 0, 0)} "
                     f"işlem, {_hucre(o.get('beklenti_pip'), 'ra')} pip; örneklem içinde "
                     f"{_hucre(i.get('beklenti_r'), 'ra')} R)")
    obur = [c for c in _ciftler(b) if c not in arti and (x[c].get("oos") or {}).get("beklenti_r") is not None]
    s = (f"{bas_buyuk(_komb_deger(param, d, aile))} olduğunda (öbür parametreler varsayılanda) {'; '.join(parca)}: "
         f"hüküm kuralına göre en çok zayıf, çünkü bu biçimin %95 aralığı ve rastgele yön sınaması hesaplanmadı")
    if obur:
        s += (f"; öbür {SAYI_AD.get(len(obur), sayi(len(obur), 0))} paritede sıfır ya da eksi ("
              + " · ".join(f"{PARITE[c]} {_hucre(x[c]['oos'].get('beklenti_r'), 'ra')}" for c in obur) + ")")
    return s + "."


def _turetme_notu(b: dict) -> str:
    """Türetilmiş varsayılanın kaynağı, ölçümün birim kaydından: ön kaydın tanımladığı ve birimin değiştirdiği
    boyutlar ("başlangıç saati New York 09:30 → 08:00 (TSİ …)"). Saat parametresinin şehri değerin önüne yazılır, adın
    parantezine değil: not bir cümlenin ya da tablo notunun içinde durur ve iç içe parantez kurmamalı; tek parantez
    TSİ karşılığıdır. Türetilmiş değilse boş."""
    if not adlar.turetilmis(b):
        return ""
    s, ov = b.get("sabit") or {}, b.get("onkayit_varsayilan") or {}
    aile = b.get("aile") or ""

    def _bir(k, v):
        sehir = adlar.SAAT_SEHIR.get(k)
        if sehir:
            ad = adlar.param_ad(k, aile).split(" (")[0] + " saati"
            tsi = adlar.tsi_yaz([f"{sehir} {ov[k]}", f"{sehir} {v}"], "→")
            return f"{ad} {sehir} {adlar.deger_yaz(k, ov[k], aile)} → {adlar.deger_yaz(k, v, aile)} ({tsi})"
        return f"{adlar.param_ad(k, aile)} {adlar.deger_yaz(k, ov[k], aile)} → {adlar.deger_yaz(k, v, aile)}"

    deg = [_bir(k, v) for k, v in s.items() if ov.get(k) is not None and ov.get(k) != v]
    return "ön kayıtta yok; ön kayıtlı varsayılandan yalnız " + ", ".join(deg) + " değiştirilerek türetildi"


def blok_hukum_cumle(u: Uretim, ctx: dict) -> str:
    """Hükmün paragrafı: ön kaydın kuralı parite başına uygulanır (kural kosu._hukum'dadır); burada yalnız sayılır ve
    bağlamı yazılır. Birincil pencere 2024 →; bütün dönemin hükmü ayrışıyorsa adıyla. Varsayılanı ön kayıtta olmayan
    birim (adlar.turetilmis) "önceden kayıtlı kural" diye anılmaz: türetildiği yer cümlenin içinde yazılır."""
    hs = ctx["HS"]
    b = ctx["B"]
    if not hs["parite"]:
        return "Hüküm: ölçülemedi (işlem yok)."
    cs = _ciftler(b)
    v_ = {c: (b["cift"][c].get("varsayilan") or {}) for c in cs}
    adlar_ = {h: [PARITE[c] for c in cs if v_[c].get("hukum") == h]
              for h in ("calisiyor", "zayif", "calismiyor", "olculemedi")}
    tn = _turetme_notu(b)
    ozne = "Türetilmiş varsayılan" if tn else "Önceden kayıtlı kural"
    n_ad = SAYI_AD.get(hs["parite"], sayi(hs["parite"], 0))
    if hs["calismiyor"] == hs["parite"]:
        dar = _varyant_artilari(b)
        aile = b.get("aile") or ""
        vv = b.get("varsayilan") or {}
        bicim = (" (" + ", ".join(_komb_deger(pa, vv.get(pa), aile) for pa in dict.fromkeys(pa for pa, _, _ in dar))
                 + ")") if dar else ""
        ana_ = (f"**Çalışmıyor.** {ozne}{bicim}, sınanan {n_ad} paritenin hiçbirinde örneklem dışında "
                f"(2024 →) maliyetten sonra artı değil.")
        for pa, d, arti in dar:
            ana_ += " " + _varyant_arti_cumle(u, b, pa, d, arti)
    elif hs["calisiyor"] == hs["parite"]:
        ana_ = f"**Çalışıyor.** {ozne} {n_ad} paritenin hepsinde hükmün üç şartını sağlıyor."
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
    for c in cs:
        if v_[c].get("hukum") in ("zayif", "calisiyor"):
            yg = _olay_yogunluk_cumle(u, c, b["cift"][c])
            if yg:
                ana_ += " " + yg
    if tn:
        ana_ += f" Bu varsayılan {tn}."
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
    rp = _r_pip_cumle(b, "varsayilan", "Türetilmiş varsayılanda" if tn else "Önceden kayıtlı kuralda")
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
        return (f"Kullanılır: {'türetilmiş varsayılan' if adlar.turetilmis(b) else 'önceden kayıtlı kural'} "
                f"{hs['parite']} paritenin hepsinde hükmün üç şartını sağlıyor (örneklem dışı, 2024 →).")
    if not olcu:
        return "Hüküm verilemedi: örneklem dışında işlem yok."
    en = max(olcu, key=lambda c: r[c])

    # Aralığın 2024 → penceresinde ve onu kapsayan bütün dönemde bütünüyle sıfırın altında kaldığı parite: ölçülmüş
    # bir kayıptır, "sıfır ya da eksi" sonuçlarla aynı cümleye girmez. Üst ucu sıfıra tohum gürültüsü kadar yakın olan
    # dönem (metrik.sinir_bilgisi) bu hükmü taşıyamaz: o parite ayrı cümleyle, uç sınırda diye yazılır (havuzdaki
    # sınır sınamasıyla aynı ölçüt).
    def _ust(c, d):
        m = v_[c].get(d) or {}
        s = ((m.get("sinir") or {}).get("ga_ust")) or {}
        return m.get("ga_ust"), bool(s.get("sinirda")), s

    def _alti(c, d):
        u_, sin, _ = _ust(c, d)
        return u_ is not None and u_ < 0 and not sin

    kayip = [c for c in cs if all(_alti(c, d) for d in ("oos", "tum"))]
    sinirli = [c for c in cs if c not in kayip and any(_ust(c, d)[1] for d in ("oos", "tum"))
               and all(_alti(c, d) or _ust(c, d)[1] for d in ("oos", "tum"))]
    pen = {"oos": "2024 → penceresinde", "tum": "bütün dönemde"}

    def _parca(c, d):
        u_, sin, s = _ust(c, d)
        if sin:
            return f"{pen[d]} üst ucu sıfırda: {_sinir_cumle(s)}"
        return (f"{pen[d]} %95 aralığı bütünüyle sıfırın altında ({_hucre(v_[c][d]['ga_alt'], 'ra')} / "
                f"{_hucre(u_, 'ra')})")

    kayip_s = ("" if not kayip else " " + "; ".join(
        f"{PARITE[c]}: %95 aralığı 2024 → penceresinde ve onu kapsayan bütün dönemde bütünüyle sıfırın altında (2024 → "
        f"{_hucre(v_[c]['oos']['ga_alt'], 'ra')} / {_hucre(v_[c]['oos']['ga_ust'], 'ra')}; bütün dönem "
        f"{_hucre(v_[c]['tum']['ga_alt'], 'ra')} / {_hucre(v_[c]['tum']['ga_ust'], 'ra')})" for c in kayip)
        + ": şansla açıklanmayan, ölçülmüş bir kayıp.")
    for c in sinirli:
        iki_sinir = all(_ust(c, d)[1] for d in ("oos", "tum"))
        kayip_s += (f" {PARITE[c]}: " + "; ".join(_parca(c, d) for d in ("tum", "oos")) + ": "
                    + ("iki pencerede de" if iki_sinir else "üst ucu sıfırda olan pencerede")
                    + " kayıp şanstan güvenle ayırt edilemiyor.")
    if hs["zayif"] or hs["calisiyor"]:
        zy = [c for c in cs if v_[c].get("hukum") in ("zayif", "calisiyor")]
        liste = ", ".join(PARITE[c] + " " + _hucre(r[c], "ra") + " R" for c in zy)
        return (f"Bu biçimiyle kanıtlanmış bir kenarı yok: örneklem dışında (2024 →) {liste}, ama hükmün şartlarını "
                f"sağlamıyor; öbür paritelerde sonuç sıfır ya da eksi." + kayip_s)
    return (f"Bu biçimiyle kullanılmaz: {SAYI_AD.get(len(cs), sayi(len(cs), 0))} paritenin hiçbirinde örneklem dışında "
            f"(2024 →) maliyetten sonra artı değil (en iyisi {PARITE[en]}, {_hucre(r[en], 'ra')} R)." + kayip_s)


def blok_ne_zaman(u: Uretim, ctx: dict) -> str:
    """Kontrol listesinin "Ne zaman" maddesi, koşul analizinden: en az iki paritede aynı kova seçimiyle tutan koşullar aday
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
                "aynı kova seçimiyle tutmadı." + genel)
    parca = []
    for x in ad:
        sonuc = ", ".join(f"{PARITE[c]} {_hucre(k.get('oos_secilen_r'), 'ra')} R "
                          f"({sayi(k.get('oos_secilen_n') or 0, 0)} işlem; tamamlayanı "
                          f"{_hucre(k.get('oos_tamamlayan_r'), 'ra')} R)" for c, k in x["pariteler"])
        parca.append(f"{_kosul_kova(x['degisken'], x['kova'])}: {sonuc}")
    esik = u.O["kunye"]["uygulama_esik"]["kosul_oos"]
    gunler = [str(k) for x in ad if x["degisken"] == "hafta_gunu" for k in x["kova"]] if "haber_olay" in b else []
    vekil = _gun_vekil_notu(u, gunler) if gunler else ""
    # Fiksingde "ay sonu günleri" kovası ön kayıtlı ay sonu alt kümesinin kendisidir ve kendi aralığını taşır; tutup
    # tutmadığı ailenin ölçütüyle okunur (iki ayrık pencere, düzeltilmiş eşik; karşılaştırma dersiyle tek tanım).
    ay_sonu_var = False
    for x in ad:
        if x["degisken"] == "ay_sonu" and [str(k) for k in x["kova"]] == ["ay sonu"]:
            aile, pa = _ay_sonu_aile(u), _pencere_ad(u)
            uye = {y["cift"]: y for y in aile["uye"] if y["birim"] == ctx["BID"] and y["kim"] == "varsayilan"}
            ar, tut = [], []
            for c, _ in x["pariteler"]:
                if c not in uye:
                    continue
                a_ = _ay_sonu_ayrim(u, uye[c])
                ar.append(f"{PARITE[c]} {_ay_sonu_kisa(_ay_sonu_hucre(a_, 'is'), pa['is'])}; "
                          f"{_ay_sonu_kisa(_ay_sonu_hucre(a_, 'oos'), pa['oos'])}")
                if uye[c].get("tutar"):
                    tut.append(c)
            if ar:
                ay_sonu_var = True
                olcut = (f"aralığın alt ucu sıfırın üstünde, fark düzeltilmiş eşiğin altında, eşik {_p4(aile['esik'])}")
                hk = (f"iki ayrık pencerede de tutan ({olcut}): {', '.join(PARITE[c] for c in tut)}" if tut else
                      f"hiçbir paritede iki ayrık pencerede de tutmuyor ({olcut})")
                vekil += ((" " if vekil else "") + "Ay sonu kovası bu kuralda ön kayıtlı ay sonu alt kümesinin "
                          "kendisidir ve kendi güven aralığını taşır: " + " · ".join(ar) + "; " + hk
                          + " (ay sonu bölümü).")
    son = ("; bu sınama hükmün öbür iki şartını (güven aralığı, rastgele yön) taşımaz" if not ay_sonu_var or len(ad) > 1
           else "")
    if ay_sonu_var:
        son += ((" — ay sonu kovasında" if son else "; ay sonu kovasında")
                + " rastgele yön sınaması alt kümeye sonradan uygulandı ve tutma ölçütüne girmez")
    return ("Aday, karar kuralı değil. " + bas_buyuk("; ".join(parca)) + ". " + (vekil + " " if vekil else "")
            + "Aday: örneklem içinde yapılan aynı kova seçiminin "
            f"en az iki paritede örneklem dışında da \"tuttu\" ölçütünü (seçilen kovalarda en az {esik} işlem, ortalama "
            "artı ve tamamlayanının üstünde) geçtiği koşul" + son + "." + genel)


# ───────────────────────────── ay sonu (fiksing; ön kayıt [fiks]: "bütün günler ve ay sonu ayrı")
def _p4(p) -> str:
    """Düzeltilmiş eşikle kıyaslanabilen p: dört hane (eşik 0,05 / ailenin sınama sayısı, binde iki dolayı)."""
    if p is None or not math.isfinite(p):
        return "—"
    return "&lt; 0,0001" if p < 0.0001 else sayi(p, 4)


def _pencere_ad(u: Uretim) -> dict:
    """Pencerelerin okur adı, künyeden: örneklem içi ile dışı ayrıktır, bütün dönem ikisini kapsar."""
    K = u.O["kunye"]
    return {"is": f"{str(K['baslangic'])[:4]}–{str(K['ic_bitis'])[:4]}", "oos": f"{str(K['dis_baslangic'])[:4]} →",
            "tum": "bütün dönem"}


def _ay_sonu_aile(u: Uretim) -> dict:
    """Ay sonu ayrımının çoklu sınama ailesi (ders_olcum.ay_sonu_ailesi; tek tanım)."""
    a = u.O.get("ay_sonu_aile")
    if not a or not a.get("n"):
        raise SablonHatasi("ay sonu ailesi ölçümde yok")
    return a


def _ay_sonu_ayrim(u: Uretim, x: dict) -> dict:
    """Ailenin bir üyesinin ayrımı (ay_sonu · diger · fark), ölçüm dosyasındaki yerinden."""
    v = u.O["birim"][x["birim"]]["cift"][x["cift"]]
    k = x["kim"]
    if k == "varsayilan":
        a = (v.get("varsayilan") or {}).get("ay_sonu")
    elif k == "secilen":
        a = (v.get("secilen") or {}).get("ay_sonu")
    else:
        a = ((v.get("ay_sonu_tf") or {}).get(k[2:]) or {}).get("ayrim")
    if not a:
        raise SablonHatasi(f"ay sonu ayrımı yok: {x['birim']} {x['cift']} {k}")
    return a


def _ay_sonu_bicim(u: Uretim, x: dict, esdeger: bool = True) -> str:
    """Ailenin bir üyesinin okur adı; aynı işlemleri veren öbür biçimler (tek sınama sayıldı) yanında."""
    b = u.O["birim"][x["birim"]]
    ad = {"varsayilan": f"önceden kayıtlı varsayılan, {x.get('tf')} dk",
          "secilen": "örneklem içinde seçilen, " + (kombinasyon_yaz(x.get("p") or {}, u.ON.get(b.get("aile")) or {},
                                                                     b.get("sabit"), b.get("aile") or "") or "—")}
    s = ad.get(x["kim"], f"varsayılanın {x['kim'][2:]} dk biçimi")
    es = [y for y in (x.get("esdeger") or []) if not (x["kim"] == "varsayilan" and y == f"tf{x.get('tf')}")]
    if esdeger and es:
        s += " (aynı işlemler: " + ", ".join("seçilen" if y == "secilen" else f"{y[2:]} dk biçimi" for y in es) + ")"
    return s


def _ay_sonu_hucre(a: dict, d: str) -> dict:
    x, o, f = ((a.get("ay_sonu") or {}).get(d) or {}), ((a.get("diger") or {}).get(d) or {}), \
        ((a.get("fark") or {}).get(d) or {})
    return {"n": x.get("n"), "r": x.get("beklenti_r"), "alt": x.get("ga_alt"), "ust": x.get("ga_ust"),
            "obur": o.get("beklenti_r"), "p": f.get("p"), "ry": (x.get("rastgele") or {}).get("yuzdelik")}


def _ay_sonu_satir(h: dict) -> list[str]:
    return [_hucre(h["n"], "n"), _hucre(h["r"], "ra"), f"{_hucre(h['alt'], 'ra')} / {_hucre(h['ust'], 'ra')}",
            _hucre(h["obur"], "ra"), _p4(h["p"]), _hucre(h["ry"], "s1")]


def _ay_sonu_kisa(h: dict, d_ad: str) -> str:
    """Bir pencerenin ay sonu sonucu tek cümlecikte: R, aralık, fark p."""
    return (f"{d_ad} {_hucre(h['r'], 'ra')} R, aralık {_hucre(h['alt'], 'ra')} / {_hucre(h['ust'], 'ra')}, "
            f"fark p {_p4(h['p'])}")


def blok_ay_sonu(u: Uretim, ctx: dict) -> str:
    """WM/R fiksingi (ön kayıt [fiks]): aynı kuralın ay sonu ve öbür günlerdeki sonucu, parite parite, üç pencerede
    (iki ayrık pencere ve bütün dönem). Ay sonu için ayrı parametre seçilmez; yalnız ayrı raporlanır. Fark Welch t
    ile (iki yönlü p). Ailenin öbür biçimleri (seçilen, zaman dilimleri) katlanır tabloda."""
    b, bid = ctx["B"], ctx["BID"]
    aile = _ay_sonu_aile(u)
    pa = _pencere_ad(u)
    uye = [x for x in aile["uye"] if x["birim"] == bid]
    govde, obur = [], []
    for c in _ciftler(b):
        for x in uye:
            if x["cift"] != c:
                continue
            a = _ay_sonu_ayrim(u, x)
            if x["kim"] == "varsayilan":
                for d in ("is", "oos", "tum"):
                    govde.append([PARITE[c], pa[d]] + _ay_sonu_satir(_ay_sonu_hucre(a, d)))
            else:
                for d in ("is", "oos"):
                    obur.append([PARITE[c], _ay_sonu_bicim(u, x), pa[d]] + _ay_sonu_satir(_ay_sonu_hucre(a, d)))
    if not govde:
        raise SablonHatasi(f"{bid}: ay sonu ayrımı ölçülmemiş")
    bas = ["Ay sonu işlem", "Ay sonu R", "%95 aralığı", "Öbür günler R", "Fark p", "Rastgele yön"]
    s = ('<div class="sayi-tablo">\n\n'
         + _tablo(["Parite", "Pencere"] + bas, govde, ["l", "l"] + ["r"] * len(bas)) + "\n\n</div>\n\n"
         f"_Önceden kayıtlı varsayılan, net R. {pa['is']} ile {pa['oos']} ayrıktır; bütün dönem ikisini birlikte kapsar. "
         "Fark p: ay sonu ile öbür günlerin ortalama farkı, Welch t (iki yönlü); dört hanedir, çünkü ölçüt düzeltilmiş "
         f"eşiktir ({_p4(aile['esik'])}; ay sonu bölümü). Rastgele yön: ay sonu kümesinde yönü yazı turayla seçen "
         "dağılımda sonucun yüzdeliği; ön kayıt alt kümeye bu sınamayı istemez, sınama sonradan eklendi ve tutma "
         "ölçütüne girmez._")
    if obur:
        s += ("\n\n<details>\n<summary>Aynı ayrım bu kuralın öbür biçimlerinde: örneklem içinde seçilen ve "
              "varsayılanın öbür zaman dilimleri</summary>\n\n<div class=\"sayi-tablo\">\n\n"
              + _tablo(["Parite", "Biçim", "Pencere"] + bas, obur, ["l", "l", "l"] + ["r"] * len(bas))
              + "\n\n</div>\n\n_Zaman dilimi biçimlerinde öbür parametreler varsayılandadır. Aynı işlemleri veren "
              "biçimler tek sınama sayılır ve bir kez yazılır._\n\n</details>")
    return s


def _ay_sonu_tutar_sart(x: dict) -> tuple[bool, bool]:
    """(tutar, örneklem dışı aralığın alt ucu sıfırın üstünde mi) — ailenin kayıtlı şartlarından."""
    return bool(x.get("tutar")), bool(((x.get("sart") or {}).get("oos") or {}).get("alt_arti"))


def blok_ay_sonu_cumle(u: Uretim, ctx: dict) -> str:
    """Ay sonu tablosunun okunuşu, veriden ve iki AYRIK pencerede: farkın kaç paritede artı olduğu, hangisinde
    p < 0,05 ve hangisinde ailenin düzeltilmiş eşiğinin altında; ay sonunun kendi sonucu; iki pencerede de tutan."""
    b, bid = ctx["B"], ctx["BID"]
    aile = _ay_sonu_aile(u)
    pa = _pencere_ad(u)
    esik = aile["esik"]
    v_uye = {x["cift"]: x for x in aile["uye"] if x["birim"] == bid and x["kim"] == "varsayilan"}
    cumle = []
    for d, ad in (("is", f"{pa['is']} arasında"), ("oos", f"{pa['oos']} penceresinde")):
        fark, kendi, anlamli, bon = [], [], [], []
        for c in _ciftler(b):
            if c not in v_uye:
                continue
            h = _ay_sonu_hucre(_ay_sonu_ayrim(u, v_uye[c]), d)
            a_ = _ay_sonu_ayrim(u, v_uye[c])
            fr = ((a_.get("fark") or {}).get(d) or {}).get("fark_r")
            if fr is None:
                continue
            fark.append((c, fr))
            kendi.append((c, h["r"], h["alt"]))
            if h["p"] is not None and h["p"] < 0.05:
                anlamli.append(c)
                if h["p"] < esik:
                    bon.append(c)
        if not fark:
            continue
        arti = [c for c, v in fark if v > 0]
        yon = (f"ay sonu ile öbür günlerin farkı {SAYI_AD.get(len(fark), len(fark))} paritenin "
               + ("hepsinde artı" if len(arti) == len(fark) else "hiçbirinde artı değil" if not arti else
                  f"{SAYI_INDE.get(len(arti), tane(len(arti), 'inde'))} artı ({', '.join(PARITE[c] for c in arti)})"))
        s = f"{bas_buyuk(ad)} {yon}"
        s += (f"; p < 0,05 olan: {', '.join(PARITE[c] for c in anlamli)}" if anlamli else "; hiçbirinde p < 0,05 değil")
        if anlamli:
            s += (f" (düzeltilmiş eşiğin, {_p4(esik)}, altında: " + ", ".join(PARITE[c] for c in bon) + ")" if bon
                  else f" (hiçbiri düzeltilmiş eşiğin, {_p4(esik)}, altında değil)")
        art_k = [c for c, r, _ in kendi if r is not None and r > 0]
        alt_k = [c for c, r, g in kendi if g is not None and g > 0]
        s += (". Ay sonunun kendi net sonucu " +
              (f"{_paritede(art_k)} artı" if art_k else "hiçbir paritede artı değil") +
              (f"; %95 aralığının alt ucu sıfırın üstünde kalan: {', '.join(PARITE[c] for c in alt_k)}" if alt_k else "")
              + ".")
        cumle.append(s)
    tut = [c for c, x in v_uye.items() if x.get("tutar")]
    cumle.append(("İki ayrık pencerede de aralığın alt ucu sıfırın üstünde ve fark düzeltilmiş eşiğin altında: "
                  + _paritede(tut) + "." if tut else
                  "Hiçbir paritede iki ayrık pencerede de aralığın alt ucu sıfırın üstünde ve fark düzeltilmiş eşiğin "
                  "altında değil."))
    cumle += [k for k in (_ay_sonu_sinir_cumle(u, v_uye[c], ad=len(tut) > 1) for c in tut) if k]
    n = int(aile["n"])
    cumle.append(f"Bu bir alt küme ölçüsüdür: ön kayıt ay sonunu ayrı raporlamayı ister, ona ayrı hüküm vermez. Ay "
                 f"sonu ayrımı derste {sayi(n, 0)} biçimde ölçüldü (iki fiksing kuralı, {_parite_sayisi(u)} parite; varsayılan, "
                 f"örneklem içinde seçilen ve varsayılanın üç zaman dilimi biçimi; aynı işlemleri veren biçimler bir kez) "
                 f"ve düzeltilmiş eşik 0,05 / {sayi(n, 0)} = {_p4(esik)}'dir. Sınamalar bağımsız olsaydı {sayi(n, 0)} "
                 f"sınamadan en az birinin şansla 0,05'in altına düşme olasılığı {yuzde(1 - 0.95 ** n, 0)} olurdu.")
    return " ".join(cumle)


def _ay_sonu_tutanlar(u: Uretim) -> tuple[dict, list, list]:
    """Ay sonu ailesinin tutan ve tutmayan üyeleri (tek tanım: ders_olcum.ay_sonu_ailesi; özet ve "Ne öğrendik" aynı
    listeyi okur)."""
    aile = _ay_sonu_aile(u)
    tutan = [x for x in aile["uye"] if x.get("tutar")]
    tutmayan = [x for x in aile["uye"] if not x.get("tutar")]
    return aile, tutan, tutmayan


def _ay_sonu_sinir_not(u: Uretim, x: dict, d: str) -> str:
    """Bir ay sonu ayrımının sıfıra yakın %95 alt ucu (ders_olcum.ay_sonu_sinir; havuzun ve parite hükmünün sınır
    notuyla aynı ölçü): işareti tohum gürültüsüne bağlıysa adıyla, değilse boş."""
    s_ = ((x.get("sinir") or {}).get(d)) or {}
    if not s_.get("sinirda"):
        return ""
    return (f"{_pencere_ad(u)[d]} alt ucu sınırda: sıfıra standart hatanın {sayi(abs(s_['uzaklik_se']), 2)} katı "
            f"uzaklıkta, {sayi(s_['tekrar'], 0)} tekrarla {_hucre(s_['kesin'], 'ra')} R; 2.000 tekrarlı yordam "
            f"tohumların {yuzde_ek(s_['pozitif_pay'], 'inde')} sıfırın üstünde verir")


def _ay_sonu_sinir_cumle(u: Uretim, x: dict, ad: bool = True) -> str:
    """Tutan bir ayrımın sınırdaki uçları tek cümlede; tutma ölçütü önceden kayıtlı yordamla kurulur, sınırda olan uç
    tutmanın tohuma bağlı olduğunu söyler (hüküm değişmez)."""
    n_ = [s for s in (_ay_sonu_sinir_not(u, x, d) for d in ("is", "oos")) if s]
    if not n_:
        return ""
    bas = f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]}: " if ad else ""
    return bas_buyuk(bas + "; ".join(n_)) + ". Tutması tohum gürültüsüne bağlıdır; ölçüt önceden kayıtlı yordamla kurulur."


def _ay_sonu_tutan_cumle(u: Uretim, x: dict) -> str:
    pa = _pencere_ad(u)
    a = _ay_sonu_ayrim(u, x)
    i, o = _ay_sonu_hucre(a, "is"), _ay_sonu_hucre(a, "oos")
    return (f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]} ({_ay_sonu_bicim(u, x, esdeger=False)}): "
            f"{_ay_sonu_kisa(i, pa['is'])}; {_ay_sonu_kisa(o, pa['oos'])}; rastgele yön yüzdeliği "
            f"{_hucre(i['ry'], 's1')} ve {_hucre(o['ry'], 's1')}")


def _ay_sonu_kardes(u: Uretim, x: dict, aile: dict) -> str:
    """Tutan bir üyenin aynı kural ve paritedeki öbür biçimleri, örneklem dışında (tutmadıklarını adıyla söylemek
    için): R ve aralık; aralık bütünüyle sıfırın altındaysa adıyla."""
    pa = _pencere_ad(u)
    parca = []
    for y in aile["uye"]:
        if y["birim"] != x["birim"] or y["cift"] != x["cift"] or y["kim"] == x["kim"]:
            continue
        h = _ay_sonu_hucre(_ay_sonu_ayrim(u, y), "oos")
        alt = h["ust"] is not None and h["ust"] < 0
        parca.append(f"{_ay_sonu_bicim(u, y, esdeger=False)}: {_hucre(h['r'], 'ra')} R, aralık "
                     f"{_hucre(h['alt'], 'ra')} / {_hucre(h['ust'], 'ra')}" + (" (bütünüyle sıfırın altında)" if alt else ""))
    if not parca:
        return ""
    return (f"Aynı kuralın aynı paritedeki öbür biçimleri {pa['oos']} penceresinde tutmuyor: " + "; ".join(parca) + ".")


def blok_ay_sonu_ders(u: Uretim, ctx: dict) -> str:
    """Karşılaştırma dersinin "Ne öğrendik"i: ay sonu ayrımının sonucu hüküm değil gözlem olarak, tek paragraf.
    Ayrıntısı (aralıklar, p) yukarıdaki "Hangi koşulda hangisi" bölümünde; burada yinelenmez."""
    aile, tutan, tutmayan = _ay_sonu_tutanlar(u)
    n = int(aile["n"])
    if not tutan:
        return (f"**Ay sonu.** Fiksing kurallarının ay sonu ayrımı {sayi(n, 0)} biçimin hiçbirinde iki ayrık pencerede "
                "de tutmuyor.")
    ad_ = "; ".join(f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]} ({_ay_sonu_bicim(u, x, esdeger=False)})"
                    for x in tutan)
    n_oos = [int(_ay_sonu_hucre(_ay_sonu_ayrim(u, x), "oos")["n"] or 0) for x in tutan]
    sin = [x for x in tutan if _ay_sonu_sinir_cumle(u, x)]
    return (f"**Ay sonu.** Ay sonu ayrımının {sayi(n, 0)} biçiminden iki ayrık pencerede de tutan "
            + ("tek biçim " if len(tutan) == 1 else f"{sayi(len(tutan), 0)} biçim ") + f"{ad_}; ayrıntısı yukarıdaki "
            "bölümde"
            + ((" ve tutması tohum gürültüsüne bağlı (" + "; ".join(
                f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]}: " + "; ".join(
                    s for s in (_ay_sonu_sinir_not(u, x, d) for d in ("is", "oos")) if s) for x in sin) + ")")
               if sin else "") + ". "
            f"Bu bir hüküm değil gözlemdir: alt küme örneklem dışında {sayi(min(n_oos), 0)}"
            + (f"–{sayi(max(n_oos), 0)}" if max(n_oos) != min(n_oos) else "") + " işlem taşır, ön kayıt alt kümeye ayrı "
            "hüküm vermez ve aynı kuralın öbür biçimleri ile öbür pariteleri tutmuyor. Bir sonraki örneklemde ilk "
            "sınanacak sonuç budur.")


def _ilgi(ad: str) -> str:
    """Ünlüyle biten bir adın ilgi hâli: "fiksing momentumu" → "fiksing momentumunun" (ek son ünlüden)."""
    son = ad[-1]
    if son not in "aeıioöuü":
        raise SablonHatasi(f"ilgi eki yalnız ünlüyle biten ad için: {ad!r}")
    dar = {"a": "ı", "ı": "ı", "e": "i", "i": "i", "o": "u", "u": "u", "ö": "ü", "ü": "ü"}[son]
    return f"{ad}n{dar}n"


def blok_ay_sonu_istisna(u: Uretim, ctx: dict) -> str:
    """Özet cümlelerinin istisnası: hüküm kuralının üç şartı (örneklem dışı net R > 0, %95 alt uç > 0, rastgele yön
    ≥ eşik) önceden kayıtlı varsayılanın ay sonu alt kümesinde tutuyorsa, bir önceki cümleye eklenen tek cümle (baştaki
    boşlukla). Alt kümeye ön kayıt ayrı hüküm vermez ve rastgele yön sınaması ona sonradan uygulandı; sınırdaki alt uç
    adıyla. Tutan yoksa boş."""
    aile = _ay_sonu_aile(u)
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    pa = _pencere_ad(u)
    grup: dict = {}
    for x in aile["uye"]:
        if x["kim"] != "varsayilan":
            continue
        h = _ay_sonu_hucre(_ay_sonu_ayrim(u, x), "oos")
        if (h["r"] is not None and h["r"] > 0 and h["alt"] is not None and h["alt"] > 0
                and h["ry"] is not None and h["ry"] >= esik):
            grup.setdefault(x["birim"], []).append((x, int(h["n"] or 0)))
    if not grup:
        return ""
    parca = []
    for bid, xs in grup.items():
        ns = sorted({n for _, n in xs})
        n_ = (f"{sayi(ns[0], 0)} işlem" if len(xs) == 1 else f"{ek(ns[0], 'er')} işlem" if len(ns) == 1 else
              f"{sayi(ns[0], 0)}–{sayi(ns[-1], 0)} işlem")
        sin = [PARITE[x["cift"]] for x, _ in xs if _ay_sonu_sinir_not(u, x, "oos")]
        parca.append(f"{_ilgi(adlar.BIRIM[bid][1].lower())} ay sonu işlemlerinde, "
                     f"{_paritede([x['cift'] for x, _ in xs])} ({n_}"
                     + (f"; alt uç {liste_yaz(sin)}'de sınırda, işareti tohuma bağlı" if sin else "") + ")")
    return (" Tek istisna ön kaydın ayrıca raporlattığı bir alt küme: hüküm kuralının şartları örneklem dışında "
            f"({pa['oos']}) " + " ve ".join(parca) + " tutuyor; ön kayıt alt kümeye ayrı hüküm vermez.")


def blok_ay_sonu_ozet(u: Uretim, ctx: dict) -> str:
    """Karşılaştırma dersi: fiksing kurallarının ay sonu ayrımı, bütün aile. Aday değildir (örneklem içinden seçilmiş
    bir kova değil, ön kaydın ayrıca raporlattığı bir alt küme) ve kendi güven aralığını taşır. Tutma ölçütü iki AYRIK
    pencere ister; bütün dönem örneklem dışını içerdiği için ölçüt olamaz."""
    aile, tutan, tutmayan = _ay_sonu_tutanlar(u)
    pa = _pencere_ad(u)
    n = int(aile["n"])
    s = ("Fiksing kurallarının ay sonu ayrımı (fade ve akış dersleri) adaylardan farklıdır: örneklem içinden seçilmiş "
         "bir kova değil, ön kaydın ayrıca raporlanmasını istediği bir alt kümedir ve kendi güven aralığını taşır. "
         f"Ders ayrımı {sayi(n, 0)} biçimde ölçtü (iki fiksing kuralı, {_parite_sayisi(u)} parite; varsayılan, örneklem içinde seçilen "
         f"ve varsayılanın üç zaman dilimi biçimi; aynı işlemleri veren biçimler bir kez) ve düzeltilmiş eşik "
         f"{_p4(aile['esik'])}. Bir ayrım şu durumda tutar: iki ayrık pencerede de ({pa['is']} ve {pa['oos']}) ay sonu "
         "ortalamasının %95 aralığının alt ucu sıfırın üstünde ve ay sonu ile öbür günlerin farkı düzeltilmiş eşiğin "
         f"altında. Bütün dönem bu ölçüte giremez, çünkü {pa['oos']} penceresini de içerir.")
    if not tutan:
        s += f" {sayi(n, 0)} biçimin hiçbiri tutmuyor."
    else:
        s += (" Tutan: " + "; ".join(_ay_sonu_tutan_cumle(u, x) for x in tutan) + ". "
              + " ".join(k for k in (_ay_sonu_sinir_cumle(u, x) for x in tutan) if k)
              + (" " if any(_ay_sonu_sinir_cumle(u, x) for x in tutan) else "")
              + " ".join(k for k in (_ay_sonu_kardes(u, x, aile) for x in tutan) if k))
    yakin = [x for x in tutmayan if _ay_sonu_tutar_sart(x)[1]]
    if yakin:
        parca = []
        for x in yakin:
            a = _ay_sonu_ayrim(u, x)
            o, i = _ay_sonu_hucre(a, "oos"), _ay_sonu_hucre(a, "is")
            sart = x.get("sart") or {}
            eksik = []
            if not (sart.get("oos") or {}).get("fark_esik"):
                eksik.append(f"{pa['oos']} farkı eşiğin üstünde, p {_p4(o['p'])}")
            if not (sart.get("is") or {}).get("alt_arti"):
                eksik.append(f"{pa['is']} aralığı sıfırı kapsar, {_hucre(i['alt'], 'ra')} / {_hucre(i['ust'], 'ra')}")
            elif not (sart.get("is") or {}).get("fark_esik"):
                eksik.append(f"{pa['is']} farkı eşiğin üstünde, p {_p4(i['p'])}")
            parca.append(f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]}, {_ay_sonu_bicim(u, x, esdeger=False)}: "
                         f"{pa['oos']} {_hucre(o['r'], 'ra')} R, aralık {_hucre(o['alt'], 'ra')} / "
                         f"{_hucre(o['ust'], 'ra')}; eksik kalan: " + " ve ".join(eksik))
        s += (f" {pa['oos']} penceresinde aralığı sıfırın üstünde olup tutmayan: " + " · ".join(parca) + ".")
    s += (" Sınırları adıyla: alt küme örneklem dışında parite başına otuz dolayında işlem taşır; ön kayıt alt kümeye "
          "ayrı hüküm vermez; rastgele yön sınaması alt kümeye sonradan uygulandı ve tutma ölçütüne girmez.")
    return s


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


def blok_tuzak(u: Uretim, ctx: dict, stoplu: str, stopsuz: str) -> str:
    """Tuzak örneğinin anlatısı, ana paritenin tuzak KAYDININ çıkış nedeninden: stopta (sert, kapanış ya da boşlukla)
    kapandıysa birinci metin, başka bir çıkışla (zaman, gün sonu) kapandıysa ikinci; ikincide "{cikis}" çıkışın okur adıyla
    değişir. Sabit bir "stopu alıyor" anlatısı örnek değiştiğinde kaydıyla çelişirdi."""
    x, _ = _ornek_bul(u, ctx["BID"], "tuzak")
    i = x.get("islem") or {}
    n = i.get("neden")
    if n is None:
        raise SablonHatasi(f"tuzak: {ctx['BID']} tuzak kaydının çıkış nedeni yok")
    if n in (1, 4, 5):
        return stoplu
    return stopsuz.replace("{cikis}", adlar.neden_ad(i, u.O["kunye"]["gun_sonu_et"]))


def _cozum_blogu(soru: str, cozum: list[str]) -> str:
    return "\n".join([soru, "", "<details>", "<summary>Çözüm</summary>", ""] + [p + "\n" for p in cozum] +
                     ["</details>"])


def _asim_gerekce(neden: int, uzak_pip: float, sonuc: float, haber_payi: tuple[float, float] | None = None) -> str:
    """Kaybın riskten büyük olmasının sebebi, çıkış nedenine göre (motor.NEDEN): sert stop emir tarafında tetiklenir ve
    stop seviyesinden yalnız kayma kadar öteden dolar (makas tetiklenmeyi öne alır, dolum uzaklığına girmez); kapanış
    stopunda çıkış, mum stopun ötesinde kapandıktan sonra sonraki açılıştadır; boşlukla stopta dolum açılıştandır.
    haber_payi = (temel kayma, haber kayması): çıkış dolumu haber penceresindeyse uzaklık ikisinin toplamıdır ve
    cümle bunu adıyla yazar (uzaklık toplamla tutmuyorsa yazmaz)."""
    if sonuc >= 0 or uzak_pip < 0.05 or neden not in (1, 4, 5):
        return ""
    u_ = _pip(uzak_pip)
    bol = ""
    if neden == 1 and haber_payi and abs(uzak_pip - sum(haber_payi)) < 0.06:
        bol = (f" ({sayi(haber_payi[0], 1)} pip temel kayma + {sayi(haber_payi[1], 1)} pip haber kayması; çıkış haber "
               f"penceresinde)")
    return {1: f" Kayıp riskten büyük, çünkü sert stop emir tarafında tetiklenir ve stop seviyesinden kayma kadar öteden "
               f"dolar: çıkış stopun {u_} pip ötesinde{bol}.",
            4: f" Kayıp riskten büyük, çünkü kapanış stopunda çıkış, mum stopun ötesinde kapandıktan sonra sonraki "
               f"mumun açılışında yapılır: çıkış stopun {u_} pip ötesinde (açılışın stoptan uzaklığı, makasın yarısı "
               f"ve kayma).",
            5: f" Kayıp riskten büyük, çünkü fiyat stopun ötesinde açıldı (boşluk) ve dolum açılıştan yapıldı: çıkış "
               f"stopun {u_} pip ötesinde."}[neden]


def blok_pratik_islem(u: Uretim, ctx: dict, birim: str = "orb", etiket: str = "", tur: str = "kazanan") -> str:
    """Bir stratejinin ana paritedeki örnek işleminden (figürdeki örnek günlerin aynısı; tur: kazanan · kaybeden ·
    tuzak) çözümlü alıştırma: risk, sonuç ve R; dolum başına ek kaymanın etkisi. (c) şıkkının cevabı elle değil
    BACKTEST'TEN gelir: işlem aynı emirle ek kaymayla yeniden koşturulmuştur (kosu.ornek_gunler). R katı hedef ve
    yürütülen girişten konan stop yeni dolumdan yeniden kurulur, sabit seviye hedef kaymaz; ek kayma çıkışı da
    değiştirebilir (uzaklaşan hedefe ulaşılamayabilir ya da geç ulaşılabilir). Çözümün aritmetiği kayıtla
    karşılaştırılır, tutmazsa üretim düşer. Her "a / b = c" satırında c, okurun gördüğü a ve b'den hesaplanır."""
    x, cp = _ornek_bul(u, birim, tur)
    i, ek = x["islem"], x["ek_kayma"]
    if i.get("stopsuz") or i.get("stop") is None:
        raise SablonHatasi(f"pratik_islem: {birim} örneği stopsuz; pratik_atr kullanılır")
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
    # Çıkış dolumu haber penceresinde mi (motorun penceresi: olay anından [önce, sonra) dakika; paritenin takvimi)?
    pen = u.O["kunye"]["haber_pencere_dk"]
    haber_cikis = any(e["t"] + pen[0] * 60 <= i["cikis_t"] < e["t"] + pen[1] * 60 for e in (x.get("takvim") or []))
    haber_payi = ((u.O["kunye"]["temel_kayma_pip"], u.O["kunye"]["haber_kayma_pip"]) if haber_cikis else None)
    yon_ad = "alış" if yon > 0 else "satış"
    ad = adlar.BIRIM[birim][1]
    f = lambda v: fiyat_yaz(v, cp)  # noqa: E731
    soru = (f"**{etiket or 'Alıştırma'} — bir işlemin R'si.** {ad} kuralının {PARITE[cp]}'deki "
            f"{ORNEK_AD[tur].lower()} örneği ({tarih_uzun(x['gun'])}): {yon_ad}, giriş {f(g)} "
            f"({'ask' if yon > 0 else 'bid'}, kayma dahil), stop {f(s)}"
            + (f", hedef {f(i['hedef'])}" if i.get("hedef") is not None else "") +
            f", çıkış {f(c)} ({adlar.neden_ad(i, k_gs)}). (a) Risk kaç pip? (b) İşlem kaç pip ve kaç R getirdi? "
            f"(c) Dolum başına kayma {sayi(dk, 1)} pip daha kötü olsaydı ne olurdu?")
    cozum = [f"(a) Risk, yürütülen giriş fiyatından stopa uzaklıktır: {f(g)} ile {f(s)} arası **{_pip(risk)} pip**.",
             f"(b) Sonuç " + (f"{f(c)} − {f(g)}" if yon > 0 else f"{f(g)} − {f(c)} (satışta giriş eksi çıkış)") +
             f" = **{sayi(sonuc, 2 if abs(sonuc * 10 - round(sonuc * 10)) > 1e-6 else 1, arti=True)} pip**; "
             f"R = sonuç / risk = {_pip(sonuc)} / {_pip(risk)} = **{_oran_yaz(_pip(sonuc), _pip(risk))} R**." +
             _asim_gerekce(i["neden"], abs(c - s) / npip, sonuc, haber_payi)]
    # (c): backtest'in ek kaymalı yeniden koşusu.
    g2, c2, r2 = ek["giris_f"], ek["cikis_f"], ek["r"]
    risk2 = ek["R_pip"]
    ht = i.get("hedef_tur")
    parca = [f"(c) Backtest işlemi aynı emirle, dolum başına {sayi(dk, 1)} pip ek kaymayla yeniden koşturuldu. Yeni "
             f"giriş {f(g2)}; stop seviyesi aynı kaldığı için risk {_pip(risk2)} pip olur."]
    if ht == 1:
        parca.append(f"Hedef girişten {sayi(i['hedef_k'], 0)}R uzakta kurulduğu için o da yeni girişle birlikte "
                     f"uzaklaşır: {f(ek['hedef'])}.")
    ayni_cikis = ek.get("neden") == i["neden"] and ek.get("cikis_t") == i["cikis_t"]
    if ht == 2 and not (ayni_cikis and i["neden"] in (2, 6)):
        parca.append("Hedef sabit bir seviyedir ve limit emirdir: yeri değişmez, dolarken kaymaz.")
    if ayni_cikis:
        if ht == 2 and i["neden"] in (2, 6):
            # Aynı bilgi iki cümlede verilmez: hedef sabit limit ve çıkış oradaysa tek cümle.
            parca.append(f"Hedef sabit bir limit emirdir: yeri değişmez ve dolarken kaymaz; çıkış yine {f(c2)}, sonuç "
                         f"{_pip_a(ek['pnl_pip'])} pip. Yeni R = {_pip(ek['pnl_pip'])} / {_pip(risk2)} = "
                         f"**{_oran_yaz(_pip(ek['pnl_pip']), _pip(risk2))} R**.")
            if i["r"] > 0:
                parca.append("Pay küçülür (giriş kayar, çıkış kaymaz), payda büyür: kazanç R cinsinden, pip "
                             "cinsinden olduğundan hızlı erir; en çok da stopu yakın kurallarda.")
        elif ht == 1 and i["neden"] in (2, 6):
            parca.append(f"Hedef yine değdi: sonuç yine **{sayi(adlar.islem_r(ek), 2, arti=True)} R** ({_pip_a(ek['pnl_pip'])} "
                         f"pip). R katı hedefli bir kuralda kaymanın bedeli kazanan işlemin R'sinde görünmez; hedefin "
                         f"uzaklaşmasıyla daha az işlemin hedefe ulaşmasında ve stopta kapanan işlemin kaybının "
                         f"büyümesinde görünür.")
        else:
            cikis = ("Çıkış limit emirdir, kaymaz" if i["neden"] in (2, 6) else
                     "Çıkış emri de piyasada dolar ve o da kayar")
            parca.append(f"{cikis}: çıkış {f(c2)}, sonuç {_pip_a(ek['pnl_pip'])} pip. Yeni R = "
                         f"{_pip(ek['pnl_pip'])} / {_pip(risk2)} = "
                         f"**{_oran_yaz(_pip(ek['pnl_pip']), _pip(risk2))} R**.")
            if i["r"] > 0:
                parca.append("Pay küçülür, payda büyür: kazanç R cinsinden, pip cinsinden olduğundan hızlı erir; en çok "
                             "da stopu yakın kurallarda.")
            elif r2 < i["r"]:
                parca.append("Kayıp pip olarak büyür; payda da büyüdüğü için R cinsinden daha yavaş büyür.")
            else:
                parca.append("Kayıp pip olarak büyür ama R cinsinden küçülür: risk kayıptan hızlı büyüdü.")
    else:
        hedefte, ek_hedefte = i["neden"] in (2, 6), ek.get("neden") in (2, 6)
        if ht == 1 and hedefte and ek_hedefte:
            fark = int(round((int(ek["cikis_t"]) - int(i["cikis_t"])) / 60))
            not_ = (f" Uzaklaşan hedefe yine ulaşıldı, yalnız {sayi(fark, 0)} dakika sonra ({saat_tsi(i['cikis_t'])} "
                    f"yerine {saat_tsi(ek['cikis_t'])} TSİ): bu işlemde kayma R'de hiçbir şeye mal olmadı, pip "
                    f"sonucu hedefle birlikte uzaklaştı." if fark > 0 else "")
        elif ht == 1 and hedefte:
            not_ = " Uzaklaşan hedefe ulaşılamadı; kaymanın asıl bedeli budur."
        else:
            not_ = ""
        parca.append(f"Bu kez çıkış değişir: işlem {saat_tsi(ek['cikis_t'])} TSİ'de, {f(c2)} fiyatından kapanır "
                     f"({adlar.neden_ad({'neden': ek['neden'], 'cikis_t': ek['cikis_t']}, k_gs)}): "
                     f"**{sayi(adlar.islem_r(ek), 2, arti=True)} R** ({_pip_a(ek['pnl_pip'])} pip)." + not_)
    if abs(ek["pnl_pip"] / risk2 - r2) > 0.0051:
        raise SablonHatasi(f"pratik: ek kaymalı kayıt kendi içinde tutmuyor ({birim})")
    cozum.append(" ".join(parca))
    return _cozum_blogu(soru, cozum)


def blok_pratik_atr(u: Uretim, ctx: dict, birim: str = "momentum", etiket: str = "", tur: str = "kazanan") -> str:
    """Stopsuz bir kuralın (R birimi girişteki ATR) ana paritedeki örnek işleminden çözümlü alıştırma. ATR backtest
    kaydından (R_pip) okunur ve soruda verilir; (c) ek kaymalı yeniden koşudan gelir. Kayma burada paydayı büyütmez:
    R birimi fiyattan değil oynaklıktan gelir."""
    x, cp = _ornek_bul(u, birim, tur)
    i, ek = x["islem"], x["ek_kayma"]
    if not i.get("stopsuz") or i.get("neden") != 3:
        raise SablonHatasi(f"pratik_atr: {birim} örnek işlemi stopsuz bir zaman çıkışı değil")
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
        raise SablonHatasi(f"pratik_atr: ek kaymada R birimi değişti ({birim}) — stopsuz kuralda değişmemeli")
    dk = ek["kayma_pip"] - u.O["kunye"]["temel_kayma_pip"]
    ad = adlar.BIRIM[birim][1]
    f = lambda v: fiyat_yaz(v, cp)  # noqa: E731
    yon_ad = "alış" if yon > 0 else "satış"
    soru = (f"**{etiket or 'Alıştırma'} — stopsuz bir kuralda R.** {ad} kuralının {PARITE[cp]}'deki "
            f"{ORNEK_AD[tur].lower()} örneği ({tarih_uzun(x['gun'])}): {yon_ad}, giriş {saat_tsi(i['giris_t'])} TSİ'de "
            f"{f(g)} ({'ask' if yon > 0 else 'bid'}, kayma dahil), çıkış {saat_tsi(i['cikis_t'])} TSİ'de {f(c)} "
            f"({adlar.neden_ad(i, u.O['kunye']['gun_sonu_et'])}). Kuralda stop yoktur; R birimi girişteki ATR'dir "
            f"(bu işlemde {_pip(atr)} pip). (a) İşlem kaç pip getirdi? (b) Kaç R? (c) Dolum başına kayma "
            f"{sayi(dk, 1)} pip daha kötü olsaydı?")
    cozum = [f"(a) " + (f"{f(c)} − {f(g)}" if yon > 0 else f"{f(g)} − {f(c)} (satışta giriş eksi çıkış)") +
             f" = **{sayi(sonuc, 2 if abs(sonuc * 10 - round(sonuc * 10)) > 1e-6 else 1, arti=True)} pip**.",
             f"(b) R = sonuç / ATR = {_pip(sonuc)} / {_pip(atr)} = **{_oran_yaz(_pip(sonuc), _pip(atr))} R**.",
             f"(c) İki dolum da piyasa emridir ve ikisi de kayar (backtest'in ek kaymalı yeniden koşusu): giriş "
             f"{f(ek['giris_f'])}, çıkış {f(ek['cikis_f'])}, sonuç {_pip_a(ek['pnl_pip'])} pip. Payda "
             f"değişmez, çünkü R birimi stop uzaklığı değil oynaklıktır: yeni R = {_pip(ek['pnl_pip'])} / {_pip(atr)} = "
             f"**{_oran_yaz(_pip(ek['pnl_pip']), _pip(atr))} R**. Stoplu bir kuralda kayma riski de büyütür; burada yalnız sonucu "
             f"küçültür. Stop olmadığı için kayıp 1 R'de durmaz."]
    return _cozum_blogu(soru, cozum)


# ─────────────────────────────────────────────────────────────── veri ve takvim blokları
def _kalite(u: Uretim) -> dict:
    return ((u.O.get("veri") or {}).get("kalite")) or {}


def _kalite_esik(u: Uretim, ad: str) -> float:
    """Veri denetiminin kapsam eşiği ("tatil" · "normal"), raporun kendisinden (kalite.TATIL_ESIK · NORMAL_ESIK);
    paritelerde ayrışırsa ya da rapor eşik taşımıyorsa üretim düşer — eşik elle yazılmaz."""
    v = {(k.get("esik") or {}).get(ad) for k in _kalite(u).values()}
    if len(v) != 1 or None in v:
        raise SablonHatasi(f"kalite_esik: veri denetimi raporu '{ad}' eşiğini taşımıyor ya da paritelerde ayrışıyor")
    return float(v.pop())


def blok_pip_tanimi(u: Uretim, ctx: dict) -> str:
    """{{! pip_tanimi }} → "EUR/USD, GBP/USD ve AUD/USD paritelerinde 0,0001; USD/JPY paritesinde 0,01": pip, künyenin
    parite başına pip büyüklüğünden, künyenin parite sırasıyla gruplanarak (elle yazılan tanım yeni bir paritede eksik
    kalırdı)."""
    k = u.O["kunye"]
    grup: dict[float, list[str]] = {}
    for c in k["ciftler"]:
        grup.setdefault(float(k["pip"][c]), []).append(c)
    parca = []
    for pip, cs in grup.items():
        hane = max(0, round(-math.log10(pip)))
        if abs(pip - 10 ** -hane) > 1e-12:
            raise SablonHatasi(f"pip_tanimi: pip on'un kuvveti değil: {pip}")
        parca.append(f"{_paritede(cs)} {sayi(pip, hane)}")
    return "; ".join(parca)


def blok_kalite_esik(u: Uretim, ctx: dict, ad: str, kip: str = "in") -> str:
    """{{! kalite_esik normal in }} → "%90'ın": veri denetiminin kapsam eşiği, ekiyle."""
    return yuzde_ek(_kalite_esik(u, ad), kip)


def blok_veri(u: Uretim, ctx: dict) -> str:
    """Veri denetiminin parite parite özeti (kalite raporu), üç tablo: kapsam ve boşluklar; makas, sıçrama adayı ve
    çapraz sınama; yerel tatillerin (İngiltere banka tatili, ABD federal tatili) kotasyon kapsamı — o günler işlem
    günüdür, verinin tam olup olmadığı ayrıca sorulur."""
    kap, fiy, tat = [], [], []
    for c in PARITE:
        k = _kalite(u).get(c)
        if not k:
            continue
        yt = k.get("yerel_tatil") or {}
        if yt:
            satir_ = [PARITE[c]]
            for ad in ("ingiltere", "abd"):
                v = yt.get(ad) or {}
                satir_.append(_hucre(v.get("gun"), "n"))
                satir_.append(f"{_hucre(v.get('kapsam_ort_yuzde'), 's1')} · {_hucre(v.get('kapsam_min_yuzde'), 's1')}"
                              if v.get("gun") else "—")
                satir_.append(_hucre(len(v.get("dusuk_gun") or []), "n") if v.get("gun") else "—")
            tat.append(satir_)
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
    if len(tat) != len(kap):
        raise SablonHatasi("yerel tatil kapsamı bir paritede ölçülmemiş")
    alti = yuzde_ek(_kalite_esik(u, "normal"), "in") + " altı"
    return (_tablo(["Parite", "Dakika", "Kapsam, normal gün (%)", "Tatil günü", "Boşluk ≥ 5 dk", "En uzun boşluk"], kap,
                   ["l", "r", "r", "r", "r", "l"]) + "\n\n" +
            _tablo(["Parite", "Makas medyanı (pip)", "Makas p95 (pip)", "Sıfır ya da eksi makas (dakika)",
                    "Sıçrama adayı", "Saatlik çapraz sınama (%)"], fiy, ["l"] + ["r"] * 5) + "\n\n" +
            _tablo(["Parite", "İngiltere tatili (gün)", "Kapsam: ort. · en düşük (%)", f"{alti} (gün)",
                    "ABD tatili (gün)", "Kapsam: ort. · en düşük (%)", f"{alti} (gün)"], tat,
                   ["l", "r", "r", "r", "r", "r", "r"]))


def _ay_listesi(aylar: list[str]) -> str:
    """["2021-01", "2021-07", "2025-01"] → "Ocak ve Temmuz 2021, Ocak 2025"."""
    yil: dict[str, list[str]] = {}
    for a in sorted(aylar):
        yil.setdefault(a[:4], []).append(AY[int(a[5:7])])
    return ", ".join(f"{' ve '.join(v)} {y}" for y, v in yil.items())


TARAF_AD = {"BID": "bid", "ASK": "ask"}


def blok_capraz_kapsam(u: Uretim, ctx: dict) -> str:
    """Saatlik çapraz sınamanın kapsamı, taraf taraf: her yılın saklanan Ocak ve Temmuz aylarında bid ve ask ayrı
    sınanır. Basılan sayılar iki tarafın birlikte sınandığı aylar, taraf başına ay ve kotasyonlu saat payı; iki tarafı
    birlikte sınanamayan aylarda yalnız bir taraf saklıysa o taraf sınanmıştır ve sonucu adıyla yazılır."""
    birlikte, taraf_ay, taraf_pay, eksik, tek = [], {"BID": [], "ASK": []}, {"BID": [], "ASK": []}, [], []
    for c in PARITE:
        cp = (_kalite(u).get(c) or {}).get("capraz") or {}
        if not cp:
            continue
        birlikte.append(len(cp.get("sinanan_aylar") or []))
        tr = cp.get("taraf") or {}
        for t in ("BID", "ASK"):
            v = tr.get(t) or {}
            if not v.get("aylar"):
                raise SablonHatasi(f"çapraz sınamanın {t} tarafı ölçülmemiş: {c}")
            taraf_ay[t].append(len(v["aylar"]))
            if v.get("kapsam_yuzde") is not None:
                taraf_pay[t].append(float(v["kapsam_yuzde"]) / 100)
        if cp.get("eksik_aylar"):
            eksik.append(f"{PARITE[c]} {_ay_listesi(cp['eksik_aylar'])}")
        for ay_, t in sorted((cp.get("tek_taraf_aylar") or {}).items()):
            esit = ((tr.get(t) or {}).get("ay_esit") or {}).get(ay_)
            if not esit:
                raise SablonHatasi(f"tek tarafı sınanan ayın sonucu yok: {c} {ay_} {t}")
            tek.append((f"{PARITE[c]} {_ay_listesi([ay_])} {TARAF_AD[t]}", esit[0] / esit[1] if esit[1] else None))
    if not birlikte:
        raise SablonHatasi("çapraz sınamanın kapsamı ölçülmemiş")
    aralik = lambda xs, f: f(min(xs)) if min(xs) == max(xs) else f"{f(min(xs))}–{f(max(xs))}"  # noqa: E731
    ay_ = lambda xs: aralik(xs, lambda x: sayi(x, 0))  # noqa: E731
    pay_ = lambda xs: aralik(xs, lambda x: yuzde(x, 1))  # noqa: E731
    s = (f"bid ve ask tarafı ayrı ayrı, her yılın saklanan Ocak ve Temmuz aylarında: iki tarafın birlikte sınandığı "
         f"aylar parite başına {ay_(birlikte)}; taraf başına bid {ay_(taraf_ay['BID'])}, ask {ay_(taraf_ay['ASK'])} ay "
         f"(kotasyonlu saatlerin bid tarafında {pay_(taraf_pay['BID'])}, ask tarafında {pay_(taraf_pay['ASK'])})")
    if eksik:
        s += "; iki tarafı birlikte sınanamayan aylar: " + "; ".join(eksik)
        if tek:
            n_ = len(tek)
            kac = {1: "birinde", 2: "ikisinde", 3: "üçünde", 4: "dördünde", 5: "beşinde"}.get(n_, ek(n_, "inde"))
            s += f"; bunların {kac} yalnız bir tarafın saatlik dosyası saklıydı ve o taraf sınandı ("
            if all(p == 1.0 for _, p in tek):
                s += ", ".join(x for x, _ in tek) + ("; %100 eşit)" if n_ == 1 else f"; {kac} de %100 eşit)")
            else:
                s += ", ".join(f"{x} {yuzde(p, 1) if p is not None else '—'} eşit" for x, p in tek) + ")"
    return s


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
            f"\n\n_{PARITE[cift]}, medyan makas (pip), dakika kapanışında._")


def blok_haber_makas_cumle(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Haber makasının tek cümlesi: makasın en geniş hâline açıklamadan önceki son dakikada (−1) ulaşan olay sayısı
    (zirve daha erken başlayıp −1'e kadar düz kalıyorsa o olay adıyla ve zirvenin ilk dakikasıyla yazılır: tablonun
    "Zirve" sütunu o ilk dakikayı gösterir, cümle onunla çelişmesin) ve −1 DAKİKASININ olaysız güne göre katının olaylar arasındaki
    aralığı. Kat zirve dakikasından değil −1'den okunur: cümle "o dakikada" der. Açıklama saniyesinin kendisi bu ölçüde
    görünmez (dakika kapanışı ölçülür)."""
    cift = cift or ana()
    hm = (_kalite(u).get(cift) or {}).get("haber_makasi") or {}
    oran, n1, n, plato = [], 0, 0, []
    for o in olay_sira(u):
        v = hm.get(o) or {}
        dks, med, orn = v.get("dk") or [], v.get("medyan_pip") or [], v.get("oran") or []
        if -1 not in dks:
            continue
        i = dks.index(-1)
        if i >= len(med) or med[i] is None:
            continue
        n += 1
        mx = max(m for m in med if m is not None)
        ilk = dks[med.index(mx)]                         # zirvenin İLK dakikası (tablonun "Zirve" sütunu)
        if med[i] >= mx:
            if ilk == -1:
                n1 += 1
            else:                                          # zirve daha erken başlıyor ve −1'e kadar düz
                plato.append((o, ilk, mx))
        if i < len(orn) and orn[i] is not None:
            oran.append((o, float(orn[i])))
    if not oran:
        return f"{PARITE[cift]} için haber makası ölçülmedi."
    pl = ("; ".join(f"{adlar.OLAY.get(o, o)}, {sayi(d, 0, arti=d != 0)} dakikadan itibaren {sayi(m, 1)} pip"
                    for o, d, m in plato))
    if n1 == n:
        nerede = "açıklamadan önceki son dakikada"
    elif n1 + len(plato) == n:
        nerede = (f"açıklamadan önceki son dakikada (daha erken ulaşıp o dakikaya kadar düz kalan: {pl})")
    elif (n1 + len(plato)) * 2 > n:
        nerede = (f"{n} olayın {ek(n1 + len(plato), 'inde')} açıklamadan önceki son dakikada"
                  + (f" (daha erken ulaşıp o dakikaya kadar düz kalan: {pl})" if plato else ""))
    else:
        nerede = "açıklama çevresinde"
    lo = min(oran, key=lambda kv: kv[1])
    hi = max(oran, key=lambda kv: kv[1])
    return (f"{PARITE[cift]}'de dakika kapanışlarında ölçülen makas en geniş hâline {nerede} ulaşır; açıklamadan önceki "
            f"son dakikada aynı saatin olaysız günlerinin {sayi(lo[1], 1)} katı ({adlar.OLAY.get(lo[0], lo[0])}) ile "
            f"{sayi(hi[1], 1)} katı ({adlar.OLAY.get(hi[0], hi[0])}) arasındadır. Açıklamanın ilk saniyelerindeki "
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
            "\n\n_Zirve makası (pip, dakika kapanışında) ve olayın yerel saatinde aynı dakikada olaysız günlerin "
            "medyanına göre katı._")


BOLGE_AD = {"America/New_York": "New York", "Europe/Berlin": "Frankfurt", "Europe/London": "Londra"}
SINAMA_AD = [("dogrulandi", "doğrulandı"), ("sessiz", "sessiz"), ("celiski", "çelişki"),
             ("degerlendirilemedi", "değerlendirilemedi")]


def _takvim_saat(u: Uretim, ctx: dict, anahtar: str, n: int, aralik) -> str:
    """Takvim tablosunun saat hücresi: "14:00 New York (69 olay; TSİ ABD yaz saatinde 21:00, kış saatinde 22:00)";
    tek günlük saat o günün kendisiyle: "03.03.2020 10:00 New York (1 olay; TSİ 18:00)"."""
    saat, bolge = anahtar.split(" ", 1)
    yer = BOLGE_AD.get(bolge, bolge)
    if aralik and aralik[0] == aralik[1]:
        return f"{tarih(aralik[0])} {saat} {yer} ({sayi(n, 0)} olay; {_tsi_tek(aralik[0], saat, bolge)})"
    return f"{saat} {yer} ({sayi(n, 0)} olay; {blok_tsi(u, ctx, '', f'{yer} {saat}')})"


def blok_takvim(u: Uretim, ctx: dict) -> str:
    """Haber takviminin olay başına özeti: sayı, dönem, yerel saat(ler), saatin kaynağı (tarih tarih ya da kural),
    kaynak, fiyat sınamasının hükmü."""
    t = (u.O.get("takvim") or {})
    sayim = t.get("sayim") or {}
    oz = ((t.get("sinama") or {}).get("ozet")) or {}
    govde = []
    for o in [x for x in olay_sira(u) if x in sayim]:
        v = sayim[o]
        saat = "; ".join(_takvim_saat(u, ctx, k, n, (v.get("saat_aralik") or {}).get(k))
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
    # Ek takvim (kullanıcının ek dosyası, takvim.EK): varsa kaç olayın oradan geldiği olay türüyle yazılır; yoksa
    # bu not hiç basılmaz (sayım resmî sayfalar + ek dosyadır, takvim.tumu).
    oz_ = t.get("ozler") or {}
    ek_not = ""
    if oz_.get("ek"):
        kume = t.get("kume") or {}
        ek_ol = [(o, int((kume.get(o) or {}).get("ek") or 0)) for o in olay_sira(u)]
        ek_ol = [(o, n) for o, n in ek_ol if n]
        ek_not = (f"\n\n_Ek takvim dosyası ({sayi(oz_.get('ek_satir') or 0, 0)} satır): "
                  + ("; ".join(f"{adlar.OLAY.get(o, o)} {sayi(n, 0)} olay" for o, n in ek_ol)
                     + " bu dosyadan geldi, öbürleri resmî sayfalardan" if ek_ol else
                     "takvime yeni olay eklemedi; olayların hepsi resmî sayfalardan") + "._")
    return _tablo(["Olay", "Sayı", "Dönem", "Yerel saat (olay sayısı; TSİ karşılığı)", "Saatin kaynağı", "Kaynak",
                   "Fiyat sınaması"],
                  govde, ["l", "r", "l", "l", "l", "l", "l"]) + ek_not


# ─────────────────────────────────────────────────────────────── metodoloji blokları
BOLUM_AD = {"haber_devam": "haber devam tablosu"}


def blok_onkayit_tablo(u: Uretim, ctx: dict) -> str:
    """Ön kaydın geçmişi: her değişikliğin zamanı ve değişen bölümleri (kaynak deponun geçmişinden, ölçüm anında)."""
    g = (u.O.get("kunye") or {}).get("onkayit_gecmisi") or []
    ilk = ((u.O.get("kunye") or {}).get("onkayit_ilk_sonuc") or {}).get("zaman")
    govde = []
    ilk_yazildi = False
    for i, k in enumerate(g):
        zaman = k.get("zaman")
        if ilk and not ilk_yazildi and k.get("sonuctan_once") is False:
            govde.append([*_utc_tsi(ilk).split(" = "),
                          "*ilk sonuçlar görüldü: koşunun sonuçları ilk kez okundu (ön kaydın bir kaydı değildir)*"])
            ilk_yazildi = True
        z = _utc_tsi(zaman).split(" = ") if zaman else ["işlenmemiş değişiklik", "—"]
        bolum = k.get("degisen_bolum") or []
        if i == 0:
            ne = "ilk kayıt: bütün kurallar, ızgaralar, varsayılanlar ve hüküm kuralı"
        elif bolum:
            ne = "eklenen ya da değişen bölüm: " + ", ".join(BOLUM_AD.get(b_, b_) for b_ in bolum)
        else:
            ne = "yalnız açıklama notu, kuralların içeriği aynı" + (f": {k['aciklama']}" if k.get("aciklama") else "")
        govde.append([*z, ne])
    if not govde:
        return "_Ön kayıt geçmişi okunamadı._"
    return _tablo(["Zaman", "TSİ karşılığı", "Değişiklik"], govde, ["l", "l", "l"])


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
    for kod, ad in (("NFP", "ABD tarım dışı istihdam"), ("CPI", "ABD TÜFE")):
        sy = (k.get(kod) or {}).get("sonraki_yayim") or {}
        if sy.get("durum"):
            satir.append(f"- **{ad}:** {tarih(sy['tarih'])} {sy['saat']} New York "
                         f"({_tsi_tek(sy['tarih'], sy['saat'], 'America/New_York')}) yayımı "
                         f"({ay_uzun(sy['referans'] + '-01')} referans ayı) örneklemin içinde, ama resmî kopyası arşivde yok; takvime girmedi. Tarih son "
                         f"okunan bültenin bir sonraki yayımı duyuran cümlesinden.")
    b_ = k.get("boe") or {}
    sd = b_.get("saat_duyurusu") or {}
    if sd:
        ortak_ = bool(b_.get("saat_duyurusu_gerekce"))
        satir.append("- **BoE:** " + liste_yaz([f"{tarih(g)}" for g in sorted(sd)]) + " kararlarının saati kuraldan "
                     "değil, BoE'nin önceden yayımladığı saat duyurusundan: "
                     + "; ".join(f"{tarih(g)} {v['saat']} Londra ({_tsi_tek(g, v['saat'], 'Europe/London')}; {v['yayim']} "
                                 f"tarihli duyuru)" for g, v in sorted(sd.items()))
                     + (". Ağustos 2020 duyurusunun gerekçesi Para Politikası Raporu'nun Finansal İstikrar Raporu'yla "
                        "ortak yayımıdır." if ortak_ else "."))
    for kod, ad in (("ecb", "ECB"), ("boe", "BoE")):
        for d in (k.get(kod) or {}).get("sorun") or []:
            # Kaynak kaydının cümlesi kuralın saatini yalnız yazar; TSİ karşılığı kuralın kendisinden.
            d = d.replace("kuralın 12:00'si", f"kuralın Londra 12:00'si ({blok_tsi(u, ctx, '', 'Londra 12:00')})")
            satir.append(f"- **{ad}:** {_gun_cevir(d)}.")
    f = k.get("fomc") or {}
    dis = f.get("dislanan") or []
    if dis:
        tur = {"notation vote": "yazılı oylama (notation vote)", "cancelled": "iptal"}
        satir.append("- **FOMC:** toplantı kararı sayılmayan açıklamalar takvimde yok: "
                     + "; ".join(f"{tarih(d['tarih'])}"
                                 + (f" {d['yayim_saati']} New York ({_tsi_tek(d['tarih'], d['yayim_saati'], 'America/New_York')})"
                                    if d.get("yayim_saati") else "")
                                 + f", {tur.get(d.get('sebep'), d.get('sebep'))}" for d in dis) + ".")
    if f.get("basin"):
        ks = f.get("basin_saat_kaynagi") or {}
        yazili = int(ks.get("takvim") or 0) + int(ks.get("duyuru") or 0)
        kural = int(ks.get("kural") or 0)
        if yazili + kural != int(f["basin"]):
            raise SablonHatasi("FOMC basın toplantısı saatlerinin kaynak sayımı toplamla tutmuyor")
        n_s = len(f.get("sorun") or [])
        satir.append(f"- **FOMC:** {sayi(f['basin'], 0)} basın toplantısı takvimde. Saatin kaynağı: kaynakta tarih "
                     f"tarih yazılı {sayi(yazili, 0)}, Fed'in kuralı {sayi(kural, 0)} (yukarıda)."
                     + (f" {sayi(n_s, 0)} olağanüstü toplantının basın toplantısının saati kaynakta yok ve kural yalnız "
                        f"olağan toplantılar için; bu toplantılar takvime girmedi." if n_s else ""))
    elif f.get("sorun"):
        satir.append(f"- **FOMC:** basın toplantılarının saati Fed'in kaynaklarından okunamadı "
                     f"({sayi(len(f['sorun']), 0)} toplantı); basın toplantısı olayları bu ölçümde yok.")
    return "\n".join(satir) if satir else "_Takvimde dışarıda bırakılan kayıt yok._"



NEDEN_OLCU_DISI = {
    "on_pencerede_bosluk": "olaydan önceki pencerede veri boşluğu, yani olay piyasa kapalıyken açıklandı ya da arşivde "
                           "kesinti var",
    "izgara_disi": "olay saati mum ızgarasına düşmüyor", "olay_mumu_yok": "olay anının mumu arşivde yok",
    "veri_kenari": "örneklemin kenarında", "atr_yok": "haber öncesi ATR ölçülemedi", "seyrek_mum": "ilk haber mumu seyrek",
    "tatil": "tatil günü", "tatil_ya_da_atr_yok": "tatil günü ya da günlük ATR yok",
    "pencerede_fiyat_yok": "olay çevresinde fiyatı olmayan dakika var",
    "gunluk_atr_yok": "günlük ATR yok", "sonraki_mum_yok": "ilk haber mumundan sonra mum yok",
    "giris_dakikasi_yok": "giriş dakikasının fiyatı yok", "cikis_fiyati_yok": "çıkış dakikasının fiyatı yok",
}


def _olcu_disi(u: Uretim) -> dict:
    """Haber ölçülerinin düşürmeleri; patikanın yön penceresi künyeden eklenir (sebebin okur yazımı onu okur)."""
    od = (((u.O.get("haber") or {}).get("olcu_disi")) or {})
    return {**od, "patika_yon_sn": ((u.O.get("kunye") or {}).get("haber_sabit") or {}).get("patika_yon_sn")}


def _neden_olcu_disi(n: str, od: dict) -> str:
    """Düşme sebebinin okur yazımı; ilk mumun uzunluğu ölçümün ana mumundan, patikanın yön penceresi ölçümün
    sabitinden (od.patika_yon_sn = strat_haber.PATIKA_YON_SN; künyede haber_sabit)."""
    if n == "ilk_mumda_yon_yok":
        tf = int(od.get("ana_tf") or 5)
        return f"ilk {SAYI_AD.get(tf, sayi(tf, 0))} dakikalık mumda fiyat değişmedi, yön yok"
    if n == "ilk_bes_dakikada_yon_yok":
        if not od.get("patika_yon_sn"):
            raise SablonHatasi("ölçü dışı: patikanın yön penceresi (patika_yon_sn) yok")
        dk = int(od["patika_yon_sn"]) // 60
        return f"ilk {SAYI_AD.get(dk, sayi(dk, 0))} dakikada fiyat değişmedi, yön yok"
    return NEDEN_OLCU_DISI.get(n, n)


def _olcu_disi_kayitlar(od: dict) -> list[dict]:
    """Ölçünün gerçek düşürmeleri olay olay ve parite parite birleşik: (olay, tarih) → parite → [(ölçü, sebep)].
    Ölçüler: olay çerçevesi (devam tablosu ve beş strateji, ana mum), devam tablosu (bütün ufuklarda düşen; bir
    kısmında düşen ufkuyla), günlük ATR'si olmayan gün (devam tablosu) ve ortalama patika. Patikanın "tatil ya da
    günlük ATR yok" sebebi, aynı olay aynı paritede günlük ATR'si olmadığı için devam tablosundan da düştüyse ölçülmüş
    sebebiyle yazılır: günlük ATR yok."""
    kayit: dict = {}

    def ekle(e: dict, c: str, olcu: str, neden: str):
        kayit.setdefault((e["olay"], e["tarih"]), {}).setdefault(c, []).append((olcu, neden))

    atr_var = {(e["olay"], e["tarih"], c) for e in od.get("devam_atr") or [] for c in (e.get("parite") or {})}
    ufuklar = list(od.get("ufuklar") or [])
    for e in od.get("cerceve") or []:
        for c, n in (e.get("parite") or {}).items():
            ekle(e, c, "devam tablosuna ve beş stratejiye", n)
    for e in od.get("devam") or []:
        for c, nedenler in (e.get("parite") or {}).items():
            tum = (e.get("tum_ufuk") or {}).get(c)
            for n in nedenler:
                uf = ((e.get("ufuk") or {}).get(c) or {}).get(n) or ufuklar
                olcu = ("devam tablosuna" if tum else
                        f"devam tablosunun {liste_yaz([sayi(int(x), 0) for x in uf])} dakikalık ufkuna")
                if tum and n == "ilk_mumda_yon_yok" and od.get("n1_ana_mumda"):
                    olcu = "devam tablosuna ve N1'in varsayılanına"
                ekle(e, c, olcu, n)
    for e in od.get("devam_atr") or []:
        for c, n in (e.get("parite") or {}).items():
            ekle(e, c, "devam tablosuna", n)
    for e in od.get("patika") or []:
        for c, n in (e.get("parite") or {}).items():
            if n == "tatil_ya_da_atr_yok" and (e["olay"], e["tarih"], c) in atr_var:
                n = "gunluk_atr_yok"
            ekle(e, c, "ortalama patikaya", n)
    out = []
    for (o, t), par in sorted(kayit.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        out.append({"olay": o, "tarih": t, "parite": par})
    return out


def blok_olcu_disi(u: Uretim, ctx: dict) -> str:
    """Takvimde durup bir haber ölçüsüne girmeyen olaylar, adıyla ve sebebiyle (ölçüm: ders_olcum.olcu_disi — ölçünün
    gerçek düşürmeleri). Bir olayın düştüğü bütün ölçüler tek maddede; aynı ölçüyü aynı sebeple kaybeden pariteler
    birlikte; olay dört paritenin dördüne eşliyse ve hepsinde düşmüşse "dört paritenin hepsinde", öbür hâllerde
    paritelerin adı (tek pariteye eşlenen olay, ör. ECB → EUR/USD, adıyla)."""
    od = _olcu_disi(u)
    esle = {(e["olay"], e["tarih"]) for k in ("cerceve", "devam", "devam_atr", "patika") for e in od.get(k) or []
            if e.get("her_paritede")}
    satir = []
    for k in _olcu_disi_kayitlar(od):
        grup: dict = {}
        for c, lst in k["parite"].items():
            grup.setdefault(tuple(lst), []).append(c)
        for lst, cs in grup.items():
            # "Hepsinde" yalnız olay dört paritenin dördüne eşliyse; tek paritelik olay (ECB → EUR/USD) adıyla.
            kim = (f"{SAYI_AD.get(len(PARITE), sayi(len(PARITE), 0))} paritenin hepsinde"
                   if (k["olay"], k["tarih"]) in esle and len(grup) == 1 and len(cs) == len(PARITE) and len(cs) > 1
                   else liste_yaz([PARITE.get(c, c) for c in cs]))
            neden = {n for _, n in lst}
            if len(neden) == 1:
                govde = (liste_yaz([o for o, _ in lst]) + " girmez — "
                         + _neden_olcu_disi(next(iter(neden)), od))
            else:
                govde = "; ".join(f"{o} girmez — {_neden_olcu_disi(n, od)}" for o, n in lst)
            satir.append(f"- **{adlar.OLAY.get(k['olay'], k['olay'])}, {tarih(k['tarih'])}** ({kim}): {govde}.")
    return "\n".join(satir) if satir else "_Takvimdeki her olay bütün haber ölçülerine girer._"


def blok_devam_takvim(u: Uretim, ctx: dict) -> str:
    """Devam tablosunun olay sayısı ile takvimin farkı, olay olay ve sebebiyle (ölçüm: ders_olcum.olcu_disi). Bir olay
    yalnız eşlendiği her paritede düştüyse olay tablosundan düşer; bir kısmında düşen olay olay sayısını değiştirmez,
    parite tablosunda o paritenin sayısından düşer. Fark takvim sayımıyla tablonun olay sayısı arasında kurulur ve
    düşürmelerin sayısına eşit değilse üretim düşer: cümle sayının kendisinden yazılır."""
    od = _olcu_disi(u)
    sayim = (((u.O.get("takvim") or {}).get("sayim")) or {})
    hucre = {h["deger"]: h for h in _devam(u).get("hucre") or [] if h.get("boyut") == "olay"
             and int(h["ufuk"]) == min(int(x["ufuk"]) for x in _devam(u)["hucre"])}
    if not hucre:
        return ""
    her_paritede = {(e["olay"], e["tarih"]) for kk in ("cerceve", "devam", "devam_atr") for e in od.get(kk) or []
                    if e.get("her_paritede")}
    tum, kismi = {}, []
    for k in _olcu_disi_kayitlar(od):
        devam_ = {c: lst for c, lst in k["parite"].items()
                  if any(o.startswith("devam tablosuna") for o, _ in lst)}
        if not devam_:
            continue
        neden = sorted({n for lst in devam_.values() for o, n in lst if o.startswith("devam tablosuna")})
        if (k["olay"], k["tarih"]) in her_paritede:
            tum.setdefault(k["olay"], []).append((k["tarih"], neden))
        else:
            kismi.append((k["olay"], k["tarih"], sorted(devam_), neden))
    parca = []
    for o in olay_sira(u):
        if o not in hucre or o not in sayim:
            continue
        n_t, n_d = int(sayim[o]["toplam"]), int(hucre[o]["n_olay"])
        if n_t - n_d != len(tum.get(o, [])):
            raise SablonHatasi(f"devam_takvim: {o} takvimde {n_t}, tabloda {n_d}; düşürme kaydı {len(tum.get(o, []))}")
        if n_t != n_d:
            parca.append(f"{adlar.OLAY.get(o, o)} {sayi(n_t, 0)} → {sayi(n_d, 0)} ("
                         + "; ".join(f"{tarih(t)}: " + ", ".join(_neden_olcu_disi(n, od) for n in nd)
                                     for t, nd in tum[o]) + ")")
    if not parca and not kismi:
        return "_Devam tablosundaki olay sayıları takvimdekiyle aynı._"
    s = ("_Takvimle fark: " + "; ".join(parca) + "; öbür olaylar takvimdeki sayısıyla." if parca
         else "_Olay sayıları takvimdekiyle aynı.")
    if kismi:
        tek = all(len(cs) == 1 for _, _, cs, _ in kismi)
        s += (f" Yalnız {'bir paritede' if tek else 'bir kısım paritede'} düşen {sayi(len(kismi), 0)} olay ("
              + "; ".join(f"{adlar.olay_ic(o)} {tarih(t)}, {liste_yaz([PARITE.get(c, c) for c in cs])}"
                          for o, t, cs, _ in kismi)
              + "; " + ", ".join(sorted({_neden_olcu_disi(n, od) for *_, nd in kismi for n in nd}))
              + ") olay sayısını değiştirmez; pariteye göre tabloda o paritenin sayısından düşer.")
    return s + "_"


def blok_uzak_tarama(u: Uretim, ctx: dict) -> str:
    """Fiyat sınamasının ±6 saatlik uzak taraması (yalnız rapor): kaç olayda resmî saatten açıkça büyük bir uzak hareket
    var ve bunların kaçında o saatte takvimin başka bir olayı duruyor."""
    uz = ((((u.O.get("takvim") or {}).get("sinama")) or {}).get("uzak")) or []
    if not uz:
        return ("Altı saatlik tarama hiçbir olayda resmî saatin oranını açıkça aşan uzak bir hareket bulmadı.")
    baska = [e for e in uz if e.get("baska_olay")]
    sayim: dict = {}
    for e in uz:
        sayim[e["olay"]] = sayim.get(e["olay"], 0) + 1
    return (f"Altı saatlik tarama {sayi(len(uz), 0)} olayda resmî saatin oranını açıkça aşan (eşiğin üstünde ve resmî "
            f"saatinkinin en az iki katı) uzak bir hareket raporlar: "
            + ", ".join(f"{adlar.OLAY.get(o, o)} {sayi(n, 0)}" for o, n in sorted(sayim.items(), key=lambda kv: -kv[1]))
            + (f"; {ek(len(baska), 'inde')} o saatte takvimin başka bir olayı var" if baska else "")
            + ". Uzak hareket bir çelişki değildir: aynı gün takvimde olmayan başka bir yayım ya da haber fiyatı "
              "oynatmış olabilir. Saat yalnız resmî bir metinle düzeltilir; tarama yalnız bakılacak günü gösterir.")

def blok_saat_capa(u: Uretim, ctx: dict) -> str:
    """60 dakikalık mumu saat başına çıpalı kurallar, adıyla: zaman dilimi kıyasında 60 dakikası ölçülen ve mumu
    olay dakikasından (haber kuralları) ya da :30'dan (New York ilk dengesi 09:30) başlamayan kurallar."""
    ad = [adlar.BIRIM[bid][1] for bid in _butun_birimler(u)
          if bid not in HABER_AILE and bid != "nyib_0930"
          and any("60" in ((u.O["birim"][bid]["cift"][c].get("tf")) or {}) for c in _ciftler(u.O["birim"][bid]))]
    if not ad:
        raise SablonHatasi("saat_capa: 60 dakikalık mumu ölçülen kural yok")
    return f"{sayi(len(ad), 0)} kural ({liste_yaz(ad)})"


def blok_sessiz(u: Uretim, ctx: dict) -> str:
    """Fiyat sınamasında sessiz kalan olaylar adıyla ve ±6 saatlik uzak taramanın o günlerdeki sonucu (yalnız rapor:
    sessiz bir olay takvimden çıkarılmaz)."""
    s = (((u.O.get("takvim") or {}).get("sinama")) or {})
    ss = s.get("sessiz_olay")
    if ss is None:
        raise SablonHatasi("sessiz olaylar ölçümde yok; ders_olcum.py yeniden koşulmalı")
    if not ss:
        return "Sessiz kalan olay yok."
    uz = {(e["olay"], e["tarih"]): e for e in s.get("uzak") or []}
    grup: dict = {}
    for e in ss:
        grup.setdefault(e["olay"], []).append(e["tarih"])
    sira = [o for o in olay_sira(u) if o in grup] + [o for o in grup if o not in olay_sira(u)]
    metin = (f"Sessiz kalan {sayi(len(ss), 0)} olay: "
             + "; ".join(f"{adlar.OLAY.get(o, o)} " + ", ".join(tarih(x) for x in sorted(grup[o])) for o in sira) + ".")
    uzakli = [(e, uz[(e["olay"], e["tarih"])]) for e in ss if (e["olay"], e["tarih"]) in uz]
    if not uzakli:
        return metin + " Altı saatlik tarama bunların hiçbirinde uzak bir hareket bulmadı."
    dk = lambda v: liste_yaz([sayi(int(d), 0, arti=True) for d in sorted(set(v.get("dk") or []))])
    metin += (f" Bunların {ek(len(uzakli), 'inde')} altı saatlik tarama uzak bir hareket raporlar: "
              + "; ".join(f"{adlar.OLAY.get(e['olay'], e['olay'])} {tarih(e['tarih'])} (resmî saate göre {dk(v)} "
                          f"dakika)" for e, v in uzakli))
    kalan = len(ss) - len(uzakli)
    return metin + (f"; öbür {ek(kalan, 'inde')} resmî saatin altı saat öncesi ve sonrasında uzak bir sıçrama yok."
                    if kalan else ".")


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
        satir.append(f"- **{adlar.OLAY.get(e['olay'], e['olay'])}, {tarih(e['tarih'])} {e['yerel_saat']} {bolge} "
                     f"({_tsi_tek(e['tarih'], e['yerel_saat'], e['bolge'])}):** "
                     f"resmî saatte sıçrama oranı " + "; ".join(par) + ".")
    return "\n".join(satir) if satir else "_Çelişki yok._"


def _parite_sayisi(u: Uretim) -> str:
    """Künyenin parite sayısı okunuşla ("dört"): parite listesi ayarda değişince metin kendiliğinden doğru sayar."""
    n = len((u.O.get("kunye") or {}).get("ciftler") or [])
    if not n:
        raise SablonHatasi("parite_sayisi: künyede parite yok")
    return SAYI_AD.get(n, sayi(n, 0))


def tane(k: int, kip: str = "inde") -> str:
    """Sayımın öznesi ya da yeri: bir için "biri" · "birinde", öbürleri için "N tanesi" · "N tanesinde". Sıfır ve
    "hepsi" çağıranın işidir, çünkü yüklemi değiştirir ("hiçbirinde … değil")."""
    if k == 1:
        return {"i": "biri", "inde": "birinde", "in": "birinin"}[kip]
    son = {"i": "tanesi", "inde": "tanesinde", "in": "tanesinin"}[kip]
    return f"{sayi(k, 0)} {son}"


def liste_yaz(ogeler: list[str]) -> str:
    """"a", "a ve b", "a, b ve c": Türkçe sıralama."""
    ogeler = list(ogeler)
    if len(ogeler) <= 2:
        return " ve ".join(ogeler)
    return ", ".join(ogeler[:-1]) + " ve " + ogeler[-1]


def blok_olaganustu(u: Uretim, ctx: dict, olay: str = "FOMC_karar") -> str:
    """Takvimdeki olağanüstü toplantılar: gün ve yerel saat (kaynağın notundan)."""
    v = (((u.O.get("takvim") or {}).get("sayim")) or {}).get(olay) or {}
    liste = v.get("olaganustu") or []
    if not liste:
        return "olağanüstü toplantı yok"
    return liste_yaz([f"{tarih_uzun(x['tarih'])} {x['saat']} {BOLGE_AD.get(x['bolge'], x['bolge'])} "
                      f"({_tsi_tek(x['tarih'], x['saat'], x['bolge'])})" for x in liste])


def _olaganustu_gun_basi(u: Uretim, olay: str = "FOMC_karar") -> str:
    """Olağanüstü kararlardan FX gününün tam sınırına (künye: fx_gun_siniri_et, New York) düşenler: bunlar yeni günün
    başındadır ve o günü işaretler; öbürleri günün içindedir ve işaretlemez (gunluk._gun_basinda_bilinen)."""
    sinir = (u.O.get("kunye") or {}).get("fx_gun_siniri_et")
    if not sinir:
        raise SablonHatasi("künyede FX gününün sınırı yok (fx_gun_siniri_et)")
    v = (((u.O.get("takvim") or {}).get("sayim")) or {}).get(olay) or {}
    liste = v.get("olaganustu") or []
    if not liste:
        return ""
    bas = [x for x in liste if x["bolge"] == "America/New_York" and x["saat"] == sinir]
    if not bas:
        return "Hiçbiri FX gününün sınırına düşmez; hiçbiri bir günü işaretlemez."
    sonraki = [tarih_uzun((datetime.strptime(x["tarih"], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"))
               for x in bas]
    if len(bas) == len(liste):
        return "Hepsi FX gününün sınırına düşer ve ertesi günü işaretler: " + liste_yaz(sonraki) + "."
    return (liste_yaz([tarih_uzun(x["tarih"]) for x in bas]) + " kararı FX gününün sınırına düşer ve "
            + liste_yaz(sonraki) + " gününü işaretler; öbürleri günün içinde geldiği için işaretlemez.")


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
        parca.append(f"{tarih(g)} ({'bütün pariteler' if set(cs) == set(PARITE) else ', '.join(PARITE[c] for c in cs)})")
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


# ─────────────────────────────────────────────────────────────── karşı olgu (sonuçlardan sonra değişen kurallar)
def _ko(u: Uretim, ad: str) -> dict:
    k = (((u.O.get("karsi_olgu") or {}).get("kosu")) or {}).get(ad)
    if not k:
        raise SablonHatasi(f"karşı olgu ölçümünde '{ad}' yok")
    return k


def _bilesim_ad(x: dict) -> str:
    return f"{adlar.BIRIM[x['birim']][1]}, {PARITE[x['cift']]}"


def _ayrisan_cift(a: float, b: float) -> tuple[str, str]:
    """İki R değeri, ayrıştıkları en az haneyle (iki haneden başlar, en çok dört): fark iki hanede görünmüyorsa
    "−0,16 / −0,16" yazılmasın."""
    for h in (2, 3, 4):
        x, y = sayi(a, h, arti=True), sayi(b, h, arti=True)
        if x != y:
            return x, y
    return x, y


def _bilesim_grup(anahtarlar: list[str]) -> str:
    """"birim|parite" anahtarları kural kural: "Fiksing dönüşü (EUR/USD, GBP/USD ve AUD/USD); …"."""
    grup: dict[str, list[str]] = {}
    for x in anahtarlar:
        b_, c_ = x.split("|")
        grup.setdefault(b_, []).append(PARITE[c_])
    return "; ".join(f"{adlar.BIRIM[b_][1]} ({liste_yaz(cs)})" for b_, cs in grup.items())


def _hukum_ad(h) -> str:
    return adlar.HUKUM[h or "olculemedi"]


def _utc_tsi(z: str, saat_yalniz: bool = False) -> str:
    """Bir UTC anı ve TSİ karşılığı: "16.10.2026 21:09 UTC = TSİ 17.10.2026 00:09" (TSİ'de gün değişiyorsa günüyle);
    saat_yalniz: "14:15 UTC = TSİ 17:15" (tarih aynı paragrafta yazılıysa)."""
    an = datetime.fromisoformat(z)
    an = an.replace(tzinfo=timezone.utc) if an.tzinfo is None else an.astimezone(timezone.utc)
    ts = an.astimezone(TSI)
    gun = "" if saat_yalniz or ts.date() == an.date() else f"{ts:%d.%m.%Y} "
    bas = f"{an:%H:%M}" if saat_yalniz else f"{an:%d.%m.%Y %H:%M}"
    return f"{bas} UTC = TSİ {gun}{ts:%H:%M}"


def blok_karsi_olgu_zaman(u: Uretim, ctx: dict, ad: str, adim: str = "") -> str:
    """Değişikliğin zamanı (commit'in işleyen saati, UTC, TSİ karşılığıyla); iki adımlı değişiklikte iki zaman.
    Yeniden koşuyla ölçülen değişikliklerde karşı olgu kaydından, öbürlerinde sonradan kararların listesinden.
    adim="1"/"2": yalnız o adımın saati (yalnız saat:dakika; tarih aynı paragrafta zaten yazılıdır)."""
    ko = (u.O.get("karsi_olgu") or {})
    kayit = ((ko.get("kosu") or {}).get(ad) or {}).get("zaman") or (ko.get("zaman") or {}).get(ad)
    if not kayit:
        raise SablonHatasi(f"'{ad}' değişikliğinin zamanı ölçümde yok")
    z = [x.get("zaman") for x in kayit]
    if not z or any(x is None for x in z):
        raise SablonHatasi(f"karşı olgu '{ad}': değişikliğin zamanı depoda okunamadı")
    if adim:
        i = int(adim) - 1
        if not 0 <= i < len(z):
            raise SablonHatasi(f"karşı olgu '{ad}': {adim}. adım yok ({len(z)} adım)")
        return _utc_tsi(z[i], saat_yalniz=True)
    return liste_yaz([_utc_tsi(x) for x in z])


def blok_karsi_olgu(u: Uretim, ctx: dict, ad: str) -> str:
    """Sonuçlardan sonra değişen bir kuralın ölçülmüş etkisi: kural tek başına eski hâline döndürülüp koşu yeniden
    yapıldığında (öbür bütün kurallar bugünkü hâliyle) sonuç bugünkü koşudan bileşim bileşim ne kadar ayrışıyor."""
    k = _ko(u, ad)
    if "devam" in k:
        return _ko_devam(k["devam"])
    n = int(k["bilesim"])
    v, s = k["varsayilan"], k["secilen"]
    cumle = []
    hd = ([(x, "2024 →") for x in v["hukum_degisen"]] + [(x, "bütün dönem") for x in v["hukum_tum_degisen"]])
    sd = s["hukum_degisen"]
    if not hd and not sd:
        cumle.append(f"Hüküm {sayi(n, 0)} bileşimin hiçbirinde değişmez (varsayılanın iki penceresi ve seçilen).")
    else:
        parca = [f"{_bilesim_ad(x)}, varsayılan {pen}: bugün {_hukum_ad(x['bugun'])}, eski kuralla "
                 f"{_hukum_ad(x['eski'])}" for x, pen in hd]
        parca += [f"{_bilesim_ad(x)}, seçilen: bugün {_hukum_ad(x['bugun'])}, eski kuralla {_hukum_ad(x['eski'])}"
                  for x in sd]
        cumle.append(f"Hüküm {sayi(len(hd) + len(sd), 0)} yerde değişir: " + "; ".join(parca) + ".")
    pd_ = s["p_degisen"]
    cumle.append("Örneklem içi seçim hiçbir bileşimde değişmez." if not pd_ else
                 f"Örneklem içi seçim {sayi(len(pd_), 0)} bileşimde başka bir kombinasyona düşer: "
                 f"{_bilesim_grup(pd_)}.")
    isl = k.get("islem") or {}
    if isl:
        b_, e_, d_ = int(isl["bugun"]), int(isl["eski"]), int(isl["degisen"])
        ortak = (b_ + e_ - d_) // 2
        yalniz_b, yalniz_e = b_ - ortak, e_ - ortak
        nb = sayi(int(isl["degisen_bilesim"]), 0)
        if d_ == 0:
            cumle.append(f"Varsayılanın {sayi(b_, 0)} işleminin hepsi aynı kalır.")
        elif yalniz_b == 0:
            cumle.append(f"Varsayılanın bugünkü {sayi(b_, 0)} işleminin hepsi eski kuralla da birebir aynıdır; eski "
                         f"kural bunlara ek olarak {sayi(yalniz_e, 0)} işlem açar ({nb} bileşimde).")
        elif yalniz_e == 0:
            cumle.append(f"Varsayılanın bugünkü {sayi(b_, 0)} işleminden {tane(yalniz_b, 'i')} eski kuralla "
                         f"açılmaz; eski kuralın bugün olmayan bir işlemi yok ({nb} bileşimde).")
        else:
            cumle.append(f"Varsayılanın bugünkü {sayi(b_, 0)} işleminden {tane(yalniz_b, 'i')} eski kuralla ya "
                         f"hiç açılmaz ya da başka bir sonuçla kapanır; eski kuralla bugün olmayan {sayi(yalniz_e, 0)} "
                         f"işlem açılır ({nb} bileşimde).")
    r_v, r_s = v["oos_r"], s["oos_r"]
    if not r_v["oynayan"] and not r_s["oynayan"]:
        cumle.append("Örneklem dışı işlem başına net R hiçbir bileşimde değişmez.")
    else:
        p_ = []
        for etiket, r, kim in (("varsayılanda", r_v, v), ("seçilende", r_s, s)):
            if not r["oynayan"]:
                continue
            x_ = f"{etiket} {sayi(int(r['oynayan']), 0)} bileşimde oynar"
            oy = kim.get("oos_r_oynayan") or []
            if oy:
                yuk = sum(1 for o in oy if o["bugun"] > o["eski"])
                hep = "" if len(oy) == 1 else "hepsinde "
                yon = (f"{hep}bugünkü kuralla daha yüksek" if yuk == len(oy) else
                       f"{hep}bugünkü kuralla daha düşük" if yuk == 0 else
                       f"{ek(yuk, 'inde')} bugünkü kuralla daha yüksek, {ek(len(oy) - yuk, 'inde')} daha düşük")
                en = oy[0]
                b_, e_ = _ayrisan_cift(en["bugun"], en["eski"])
                x_ += (f" ({yon}); en büyük fark {_bilesim_ad(en)}: bugün {b_}, eski kuralla {e_}")
            else:
                x_ += f", en çok {sayi(r['azami'], 3)} R"
            p_.append(x_)
        cumle.append("Örneklem dışı işlem başına net R " + "; ".join(p_) + ".")
    kd = int(v["kosul_degisen"]) + int(s["kosul_degisen"])
    if kd:
        x_ = f"Koşul analizinin {sayi(kd, 0)} hükmü değişir (varsayılan ve seçilen birlikte)"
        kt = v.get("kosul_tuttu") or []                    # [bugün, eski kuralla]
        if len(kt) == 2 and int(kt[0]) != int(kt[1]):
            x_ += f"; varsayılanda tutan koşul bugün {sayi(int(kt[0]), 0)}, eski kuralla {sayi(int(kt[1]), 0)}"
        cumle.append(x_ + ".")
    md = int(v["maliyet_degisen"]) + int(v["maliyet_oos_degisen"])
    if md:
        cumle.append(f"Varsayılanın maliyet bayrağı {sayi(md, 0)} yerde değişir (iki dönem birlikte).")
    return " ".join(cumle)


def _ko_devam(d: dict) -> str:
    n = int(d["hucre"])
    if d.get("yalniz_bugun") or d.get("yalniz_eski"):
        raise SablonHatasi("karşı olgu: devam tablosunun hücre kümesi iki kuralda aynı değil")
    nd = int(d["n_degisen"])
    cumle = []
    if not nd:
        cumle.append(f"Devam tablosunun {sayi(n, 0)} hücresinin hiçbirinde olay sayısı değişmez.")
    else:
        cumle.append(f"Devam tablosunun {sayi(n, 0)} hücresinin {tane(nd, 'inde')} olay sayısı değişir: eski kural "
                     f"{'bu hücrede' if nd == 1 else 'bu hücrelerde'} {sayi(int(d['olay_eski']), 0)} olay ölçerdi, "
                     f"bugün {sayi(int(d['olay_bugun']), 0)}.")
    hd = d.get("hukum_degisen") or []
    cumle.append("Hücrelerin hükmü hiçbirinde değişmez." if not hd else
                 f"Hüküm {sayi(len(hd), 0)} hücrede değişir.")
    if nd and d.get("kir_azami_fark") is not None:
        cumle.append(f"Ortalamalar en çok kırılımda {sayi(d['kir_azami_fark'], 1)}, fade'de "
                     f"{sayi(d['fad_azami_fark'], 1)} puan (ATR'nin yüzdesi) oynar.")
    return " ".join(cumle)


def _yorum_hukum(x: dict | None) -> tuple[str | None, float | None]:
    x = x or {}
    return x.get("hukum"), ((x.get("ozet") or {}).get("beklenti_r"))


#: Ön kaydın harfinin okumaları (kosu.YORUM): okura giden ad. Adı olmayan bir okuma üretimi düşürür; kayıtlı olmayan
#: bir okuma kodu okura basılmaz.
OKUMA_AD = {
    ("ilk_saat", "yalniz_sinyal"): "ilk saatte yalnız sinyal verilmez",
    ("bant", "iki_kenar"): "dönüş mumu iki bandın arasında kapanır",
    ("kesis", "iki_yon"): "her seviyenin ilk kesişi iki yönde de işlem verir",
    ("acilis", "acilis_ici"): "pencerenin ilk mumu dışarıda kapanırsa da kırılımdır",
    ("donus", "iki_kenar"): "dönüş mumu aralığın içinde kapanır",
}


def _yorum_satirlari(u: Uretim, bid: str, b: dict, c: str) -> list[dict]:
    """Bir bileşimin harf okumaları, kosu.YORUM sırasıyla (künyeden; ölçüm dosyası anahtarları sıralar). Her okuma
    TEK BAŞINA ölçüldü: öbür okuma bu dersteki kuralda kalır. Kayıtlar künyenin okumalarıyla aynı değilse üretim
    düşer."""
    y = b["cift"][c].get("yorum") or {}
    sira = [tuple(x) for x in (((u.O.get("kunye") or {}).get("yorum") or {}).get(bid) or [])]
    if not y and not sira:
        return []
    if sorted((r.get("param"), r.get("harf")) for r in y.values()) != sorted(sira) or set(y) != {p for p, _ in sira}:
        raise SablonHatasi(f"{bid} {c}: yorum kayıtları künyedeki okumalarla aynı değil")
    v, s = b["cift"][c].get("varsayilan") or {}, b["cift"][c].get("secilen") or {}
    out = []
    for param, harf in sira:
        r = y[param]
        ad = OKUMA_AD.get((param, harf))
        if not ad:
            raise SablonHatasi(f"okumanın okura giden adı yok: {param}={harf}")
        yv, ys = r.get("varsayilan") or {}, r.get("secilen") or {}
        out.append({
            "param": param, "harf": harf, "ad": ad,
            "degisen": int(r.get("degisen") or 0), "kombinasyon": int(r.get("kombinasyon") or 0),
            "bos": int(r.get("bos_kombinasyon") or 0),
            "v": (v.get("hukum"), (v.get("oos") or {}).get("beklenti_r")), "vh": _yorum_hukum(yv.get("oos")),
            "t": (v.get("hukum_tum"), (v.get("tum") or {}).get("beklenti_r")), "th": _yorum_hukum(yv.get("tum")),
            "s": (s.get("hukum") if s else None, (s.get("oos") or {}).get("beklenti_r") if s else None),
            "sh": _yorum_hukum((ys or {}).get("oos")), "secim_ayni": bool(r.get("secim_ayni")),
            "varsayilan_degisti": bool(r.get("varsayilan_degisti")),
            # 2024 → işlem sayısı ve rastgele yön yüzdeliği: bu dersteki okuma → harfin okuması
            "vn": ((v.get("oos") or {}).get("n"), (((yv.get("oos") or {}).get("ozet")) or {}).get("n")),
            "vy": ((((v.get("rastgele") or {}).get("oos")) or {}).get("yuzdelik"),
                   (((yv.get("oos") or {}).get("rastgele")) or {}).get("yuzdelik")),
        })
    return out


def _yorum_okumalari(u: Uretim, bid: str, b: dict) -> list[tuple[str, str, list[tuple[str, dict]]]]:
    """(param, okumanın adı, [(parite, satır)]) — okuma okuma."""
    okuma: dict = {}
    for c in _ciftler(b):
        for x in _yorum_satirlari(u, bid, b, c):
            okuma.setdefault(x["param"], (x["ad"], []))[1].append((c, x))
    return [(p, ad, xs) for p, (ad, xs) in okuma.items()]


_YORUM_KIYAS = (("v", "vh", "varsayılanın 2024 → hükmü", "varsayılan, 2024 →"),
                ("t", "th", "varsayılanın bütün dönem hükmü", "varsayılan, bütün dönem"),
                ("s", "sh", "seçilenin hükmü", "seçilen"))


def blok_yorum(u: Uretim, ctx: dict) -> str:
    """Yorum duyarlılığı (strateji dersi): ön kaydın harfinin her okumasıyla aynı ölçüm, parite parite."""
    b, bid = ctx["B"], ctx["BID"]
    okumalar = _yorum_okumalari(u, bid, b)
    if not okumalar:
        raise SablonHatasi(f"{bid}: yorum duyarlılığı ölçülmemiş")

    def h(p):
        return f"{_hukum_ad(p[0])}, {_hucre(p[1], 'ra')} R" if p[0] else "—"

    def ok(p, hane):
        """Bu dersteki okuma → harfin okuması; ikisinden biri ölçülmemişse "—"."""
        if p[0] is None or p[1] is None or not all(math.isfinite(float(v)) for v in p):
            return "—"
        return f"{sayi(p[0], hane)} → {sayi(p[1], hane)}"
    parca = []
    for _, ad, xs in okumalar:
        govde = [[PARITE[c], f"{sayi(x['degisen'], 0)} / {sayi(x['kombinasyon'], 0)}", h(x["vh"]), ok(x["vn"], 0),
                  ok(x["vy"], 1), h(x["th"]),
                  (h(x["sh"]) + ("" if x["secim_ayni"] else " (başka kombinasyon)")) if x["sh"][0] else "—"]
                 for c, x in xs]
        tablo = _tablo(["Parite", "İşlemi değişen kombinasyon", "Varsayılan, 2024 →", "İşlem, 2024 →",
                        "Rastgele yön, 2024 →", "Varsayılan, bütün dönem", "Seçilen, 2024 →"], govde,
                       ["l", "r", "r", "r", "r", "r", "r"])
        parca.append((f"**Harfin okuması: {ad}.**\n\n" if len(okumalar) > 1 else "") + tablo)
    not_ = ("Her okuma tek başına ölçüldü; öbürü bu dersteki kuralda kaldı. " if len(okumalar) > 1 else "")
    return ("\n\n".join(parca) +
            "\n\n_Ön kaydın harfinin okumasıyla aynı ölçüm: hüküm ve işlem başına net R; işlem sayısında ve rastgele "
            "yön yüzdeliğinde ok bu dersteki okumadan harfin okumasına gider. " + not_ +
            "Bu dersteki okumanın hükmü sonuç tablosundadır. Kombinasyon sayısı ızgaranın bütünüdür; işlem listesi iki "
            "okumada birebir aynı olmayan kombinasyon değişmiş sayılır._")


def blok_yorum_cumle(u: Uretim, ctx: dict) -> str:
    """Harfin okumasıyla hükmün değiştiği bileşimler (strateji dersi), okuma okuma."""
    b, bid = ctx["B"], ctx["BID"]
    okumalar = _yorum_okumalari(u, bid, b)
    if not okumalar:
        raise SablonHatasi(f"{bid}: yorum duyarlılığı ölçülmemiş")
    cumle = []
    for _, ad, xs in okumalar:
        deg = [f"{PARITE[c]}'de {etiket} {_hukum_ad(x[anahtar][0])} yerine {_hukum_ad(x[harf][0])}"
               for c, x in xs for anahtar, harf, etiket, _ in _YORUM_KIYAS
               if x[harf][0] and x[anahtar][0] and x[harf][0] != x[anahtar][0]]
        bas = "Harfin okumasıyla" if len(okumalar) == 1 else f'Harfin "{ad}" okumasıyla'
        cumle.append(f"{bas} hüküm değişir: " + "; ".join(deg) + "." if deg else
                     f"{bas} hiçbir paritede hüküm değişmez.")
    return " ".join(cumle)


def blok_yorum_ozet(u: Uretim, ctx: dict) -> str:
    """Metodoloji dersi: yorum duyarlılığının bütün birimlerdeki özeti, okuma okuma."""
    satir = []
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        okumalar = _yorum_okumalari(u, bid, b)
        for _, ad, xs in okumalar:
            deg = sum(x["degisen"] for _, x in xs)
            komb = sum(x["kombinasyon"] for _, x in xs)
            hk = [f"{PARITE[c]} ({etiket})" for c, x in xs for anahtar, harf, _, etiket in _YORUM_KIYAS
                  if x[harf][0] and x[anahtar][0] and x[harf][0] != x[anahtar][0]]
            secim = sum(1 for _, x in xs if x["sh"][0] and not x["secim_ayni"])
            satir.append(f"  - **{adlar.BIRIM[bid][1]}** ({ad}): {SAYI_AD.get(len(xs), sayi(len(xs), 0))} paritenin "
                         f"{sayi(komb, 0)} kombinasyonundan "
                         + (f"{tane(deg, 'in')} işlemleri değişir; " if deg
                            else "hiçbirinin işlemleri değişmez; ")
                         + (f"hüküm {'; '.join(hk)} değişir" if hk else "hüküm hiçbir paritede değişmez")
                         + ("" if not secim else f"; seçilen {sayi(secim, 0)} paritede başka bir kombinasyon olur")
                         + ".")
    if not satir:
        raise SablonHatasi("yorum duyarlılığı ölçülmemiş")
    return "\n".join(satir)


def blok_ilk_sonuc_zaman(u: Uretim, ctx: dict) -> str:
    """İlk sonuçların görüldüğü an (koşu çıktısını okuyan ilk kodun commit'i, işleyen saati UTC, TSİ karşılığıyla)."""
    z = ((u.O.get("kunye") or {}).get("onkayit_ilk_sonuc") or {}).get("zaman")
    if not z:
        raise SablonHatasi("ilk sonuçların zamanı ölçümde yok")
    return _utc_tsi(z)


def blok_aile_dsr(u: Uretim, ctx: dict) -> str:
    """Birim başına ve aile başına deneme sayısıyla deflated Sharpe (ön kayıt aile başına ister) ve ailenin bütün
    ızgarasından tek seçimin hükmü."""
    a = u.O.get("aile_secim") or {}
    bn, an, bd, ad_, bg, ag = [], [], [], [], [], []
    hukum: dict = {}
    for aile, v in a.items():
        for c, x in (v.get("cift") or {}).items():
            an.append(int(x["n_deneme"]))
            for b, d in (x.get("dsr") or {}).items():
                bn.append(int(d["birim_n"]))
                for liste, alan in ((bd, "birim_dsr"), (ad_, "aile_dsr"), (bg, "birim_dsr_gurultu"),
                                    (ag, "aile_dsr_gurultu")):
                    if d.get(alan) is not None:
                        liste.append(float(d[alan]))
            s = x.get("secim")
            if s:
                hukum[s.get("hukum") or "olculemedi"] = hukum.get(s.get("hukum") or "olculemedi", 0) + 1
    if not an or not bd or not ad_:
        raise SablonHatasi("aile sayımlı deflated Sharpe ölçülmemiş")
    say = ", ".join(f"{sayi(n, 0)} {adlar.HUKUM[h]}" for h, n in sorted(hukum.items(), key=lambda x: -x[1]))
    return (f"Bölünen dört ailede deneme sayısı kural başına {sayi(min(bn), 0)}–{sayi(max(bn), 0)}, aile başına "
            f"{sayi(min(an), 0)}–{sayi(max(an), 0)}. Seçilenlerin deflated Sharpe olasılığı yayılım eşiğiyle kural "
            f"sayımında en çok {sayi(max(bd), 3)}, aile sayımında en çok {sayi(max(ad_), 3)}; gürültü eşiğiyle "
            f"{sayi(max(bg), 3)} ve {sayi(max(ag), 3)}. Hiçbiri hükme girmez. Ailenin bütün ızgarasından tek seçim "
            f"yapılsaydı her paritede seçilen, kurallardan birinin seçileni olurdu; o seçilenlerin hükmü: {say}.")


def sayi_ek(x: float, b: int, kip: str) -> str:
    """Ondalıklı sayıya ek ("0,26'ya", "0,05'e", "1,00'e"): uyum okunuşun son sözcüğünden — kesir sıfır değilse
    kesrin, sıfırsa tam kısmın."""
    s = sayi(x, b)
    kesir = s.split(",", 1)[1] if "," in s else ""
    son = int(kesir) if kesir and int(kesir) else int(abs(round(x)))
    return s + "'" + ek(son, kip).split("'", 1)[1]


def blok_dsr_esik(u: Uretim, ctx: dict) -> str:
    """Seçilenlerde yayılım eşiği ile gürültü eşiğinin sırası (iki eşiğin hangisi daha sıkı). Yayılım eşiği gürültü
    eşiğinin altında kalan seçimlerde tablolardaki değer (yayılım) gürültü eşiğine göre olandan yüksektir; en büyük
    iki fark adıyla."""
    ust = alt = 0
    fark = []
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            d = ((b["cift"][c].get("secilen") or {}).get("dsr")) or {}
            x, y = d.get("sr0_yillik"), d.get("sr0_gurultu_yillik")
            if x is None or y is None:
                continue
            if x > y:
                ust += 1
            else:
                alt += 1
                if d.get("dsr") is not None and d.get("dsr_gurultu") is not None:
                    fark.append((d["dsr"] - d["dsr_gurultu"], bid, c, d["dsr"], d["dsr_gurultu"]))
    if not ust + alt:
        raise SablonHatasi("seçilenlerde iki eşik ölçülmemiş")
    s = (f"{sayi(ust + alt, 0)} seçimin {ek(ust, 'inde')} yayılım eşiği gürültü eşiğinin üstünde (bu seçimlerde "
         f"tabloların \"DSR (yayılım)\" sütunu tutucudur), {ek(alt, 'inde')} altındadır")
    fark.sort(reverse=True)
    ilk = [f for f in fark[:2] if round(f[3], 2) != round(f[4], 2)]
    if ilk:
        s += (": o seçimlerde \"DSR (yayılım)\" sütunu \"DSR (gürültü)\" sütunundan yüksektir (en büyük fark "
              + "; ".join(f"{adlar.BIRIM[bid][1]} {PARITE[c]}, {sayi_ek(dy, 2, 'e')} karşı {sayi(dg, 2)}"
                          for _, bid, c, dy, dg in ilk) + ")")
    return s


def blok_olculemedi_etki(u: Uretim, ctx: dict) -> str:
    """Sonuçtan önceki "ölçülemedi" kuralı (dönemde 20'den az işlem) bugünkü sonuçlara uygulansaydı."""
    o = ((u.O.get("karsi_olgu") or {}).get("olculemedi")) or {}
    if not o:
        raise SablonHatasi("ölçülemedi eşiğinin sayımı yok")
    p_ = []
    for ad, etiket in (("varsayilan", "varsayılanın 2024 → hükmünde"), ("varsayilan_tum", "bütün dönem hükmünde"),
                       ("secilen", "seçilende")):
        deg = o[ad]["degisen"]
        if not deg:
            p_.append(f"{etiket} hiçbir bileşim")
            continue
        birim = sorted({x["birim"] for x in deg})
        ad_ = ", ".join(adlar.BIRIM[b][1] for b in birim)
        hukum = sorted({_hukum_ad(x["bugun"]) for x in deg})
        n1, n2 = min(x["n"] for x in deg), max(x["n"] for x in deg)
        p_.append(f"{etiket} {sayi(len(deg), 0)} bileşim ({ad_}; bugün {' ya da '.join(hukum)}, "
                  + (f"{sayi(n1, 0)} işlem)" if n1 == n2 else f"{sayi(n1, 0)}–{sayi(n2, 0)} işlem)"))
    return "Eski eşikle " + "; ".join(p_) + " ölçülemedi sayılırdı"


def blok_gun_kumeli(u: Uretim, ctx: dict) -> str:
    """Parite başına aralığın gün kümeli duyarlılığı: hüküm ve maliyet bayrağı aynı ölçütle gün kümeli aralıktan da
    soruldu (bilgi; hüküm ön kaydın okumasıyla, işlemleri bağımsız örnekleyen aralıktan verilir)."""
    n = 0
    hukum_deg, bayrak = [], {"oos": [0, 0], "tum": [0, 0]}
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            for taraf, pencereler in (("varsayilan", ("oos", "tum")), ("secilen", ("oos",))):
                v = b["cift"][c].get(taraf) or {}
                g = v.get("gun_kumeli") or {}
                if not g:
                    continue
                if taraf == "varsayilan":
                    n += 1
                for d in pencereler:
                    alan = "hukum" if d == "oos" else "hukum_tum"
                    if (g.get(d) or {}).get("hukum") != v.get(alan):
                        hukum_deg.append(f"{adlar.BIRIM[bid][1]}, {PARITE[c]}")
                if taraf == "varsayilan":
                    for d, alan in (("oos", "maliyet_yiyor_oos"), ("tum", "maliyet_yiyor")):
                        bayrak[d][0] += bool(v.get(alan))
                        bayrak[d][1] += bool((g.get(d) or {}).get("maliyet_yiyor"))
    if not n:
        raise SablonHatasi("gün kümeli aralık ölçülmemiş")
    h = ("hüküm hiçbir bileşimde değişmez" if not hukum_deg else
         f"hüküm {sayi(len(hukum_deg), 0)} yerde değişir ({'; '.join(hukum_deg)})")
    def bay(d: str) -> str:
        a_, g_ = bayrak[d]
        return (f"yine {sayi(a_, 0)} bileşimde" if a_ == g_ else f"{sayi(a_, 0)} yerine {sayi(g_, 0)} bileşimde")
    return (f"{h}; varsayılanın maliyet bayrağı bütün dönemde {bay('tum')}, örneklem dışında (2024 →) {bay('oos')} "
            f"yanar")


def blok_tatil_betimi(u: Uretim, ctx: dict) -> str:
    """Yerel tatillerde varsayılanların sonucu (ölçüm: tatil_betimi; ön kayıt dışı, betimleyici, sınama yok): özet
    cümle ve katlanır tablo. Dört paritenin işlemleri birlikte; iki ülkenin ortak tatili iki sütuna da girer."""
    t = u.O.get("tatil") or {}
    br = t.get("birim") or {}
    if not br or not t.get("ingiltere") or not t.get("abd"):
        raise SablonHatasi("yerel tatil betimi ölçülmemiş")
    govde, alt, n_ = [], {"ingiltere": 0, "abd": 0}, {"ingiltere": [], "abd": []}
    sifir = {"ingiltere": [], "abd": []}            # tatilde hiç işlem açmayan kural: aralığa 0 olarak girer
    kural = 0
    for bid in _butun_birimler(u):
        x = br.get(bid)
        if not x:
            continue
        kural += 1
        satir = [adlar.BIRIM[bid][1]]
        for ad in ("ingiltere", "abd", "diger"):
            for d in ("tum", "oos"):
                v = (x.get(ad) or {}).get(d) or {}
                satir.append(f"{_hucre(v['r'], 'ra')} ({sayi(v['n'], 0)})" if v.get("n") else "—")
        dr = ((x.get("diger") or {}).get("tum") or {}).get("r")
        for ad in ("ingiltere", "abd"):
            v = (x.get(ad) or {}).get("tum") or {}
            n_[ad].append(int(v.get("n") or 0))
            if v.get("n"):
                alt[ad] += int(dr is not None and v["r"] < dr)
            else:
                sifir[ad].append(adlar.BIRIM[bid][1])
        govde.append(satir)
    if not govde:
        raise SablonHatasi("yerel tatil betimi boş")
    aralik = lambda xs: (sayi(min(xs), 0) if min(xs) == max(xs) else f"{sayi(min(xs), 0)}–{sayi(max(xs), 0)}")  # noqa: E731
    k8 = (((t.get("kunye") or {}).get("abd")) or {}).get("fed_kurali")
    def _alti(k: int) -> str:
        return f"{ek(k, 'inde')} öbür günlerinkinin altında" if k else "hiçbirinde öbür günlerinkinin altında değil"
    ikisi = [a for a in sifir["ingiltere"] if a in sifir["abd"]]
    yalniz_abd = [a for a in sifir["abd"] if a not in ikisi]
    yalniz_ing = [a for a in sifir["ingiltere"] if a not in ikisi]
    sifir_ = "; ".join(p for p in (
        (f"{liste_yaz(ikisi)} iki tatil kümesinde de" if ikisi else ""),
        (f"{liste_yaz(yalniz_ing)} İngiltere tatillerinde" if yalniz_ing else ""),
        (f"{liste_yaz(yalniz_abd)} ABD tatillerinde" if yalniz_abd else "")) if p)
    cumle = (f"Örneklemde hafta içine düşen {sayi(len(t['ingiltere']), 0)} İngiltere banka tatili ve "
             f"{sayi(len(t['abd']), 0)} ABD federal tatili var ({sayi(len(t.get('ikisi') or []), 0)} gün ikisi birden). "
             f"Bütün dönemde İngiltere tatillerinin ortalaması {sayi(kural, 0)} kuralın {_alti(alt['ingiltere'])}, ABD "
             f"tatillerininki {_alti(alt['abd'])}. Kümenin büyüklüğü kurala göre değişir ({_parite_sayisi(u)} parite "
             f"birlikte, İngiltere tatillerinde {aralik(n_['ingiltere'])}, ABD tatillerinde {aralik(n_['abd'])} işlem"
             + (f"; {sifir_} hiç işlem açmaz" if sifir_ else "") +
             ") ve hiçbir fark sınanmadı: bu sayım bir bulgu değil, sınanmamış bir sorudur.")
    kaynak = ("İngiltere listesi gov.uk'in banka tatili listesinden (2018'i kapsamadığı için o yıl açık kaynaklı bir tatil "
              "kütüphanesinden; ortak yıllarda iki liste birebir aynı), ABD listesi ABD Personel Yönetimi Ofisi'nin "
              "(OPM) federal tatil listesinden; cumartesiye düşen bir tatilde Federal Reserve Bankaları önceki cuma açık "
              "olduğu için o cuma tatil sayılmaz (Fed'in K.8 kuralı).") if k8 else ""
    return (cumle + "\n\n<details>\n<summary>Yerel tatillerde varsayılanların sonucu, kural kural</summary>\n\n"
            "<div class=\"sayi-tablo\">\n\n"
            + _tablo(["Kural", "İngiltere tatili: bütün dönem", "İngiltere tatili: 2024 →", "ABD tatili: bütün dönem",
                      "ABD tatili: 2024 →", "Öbür günler: bütün dönem", "Öbür günler: 2024 →"], govde,
                     ["l"] + ["r"] * 6)
            + "\n\n</div>\n\n_İşlem başına ortalama net R (parantezde işlem sayısı); " + _parite_sayisi(u) + " paritenin varsayılan işlemleri "
              "birlikte. İşlemin günü FX günüdür (New York 17:00'de başlar; "
              + adlar.tsi_yaz(["New York 17:00"]) + "). " + kaynak + "_\n\n</details>")


def blok_gun_kumeli_yon(u: Uretim, ctx: dict) -> str:
    """Kümelemenin aralığa etkisinin yönü, ölçümden: varsayılanın örneklem dışı net aralığı bağımsız ve gün kümeli
    örneklemeyle genişliğine göre sayılır; maliyet bayrağı iki yordamda ayrışan bileşim adıyla ve uçlarıyla yazılır.
    Günde en çok bir işlem açan bileşimde iki yordam aynı örneklemi kurar ve aralık birebir aynıdır."""
    dar = genis = ayni = 0
    oran, degisen = [], []
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            v = b["cift"][c].get("varsayilan") or {}
            g = v.get("gun_kumeli") or {}
            if not g:
                continue
            a, k = v.get("oos") or {}, g.get("oos") or {}
            if not any(x.get(y) is None for x in (a, k) for y in ("ga_alt", "ga_ust")):
                w1, w2 = a["ga_ust"] - a["ga_alt"], k["ga_ust"] - k["ga_alt"]
                if w1 > 0:
                    r = w2 / w1
                    if abs(r - 1) < 1e-9:
                        ayni += 1
                    else:
                        oran.append(r)
                        dar, genis = (dar + 1, genis) if r < 1 else (dar, genis + 1)
            for d, alan in (("oos", "maliyet_yiyor_oos"), ("tum", "maliyet_yiyor")):
                if bool(v.get(alan)) != bool((g.get(d) or {}).get("maliyet_yiyor")):
                    degisen.append((bid, c, d, v, g))
    toplam = dar + genis + ayni
    if not toplam:
        raise SablonHatasi("gün kümeli aralık ölçülmemiş")
    yon = (f"Kümelemenin aralığa etkisi tek yönlü değil: varsayılanın örneklem dışındaki {sayi(toplam, 0)} net "
           f"aralığının {ek(dar, 'i')} gün kümeli örneklemeyle daha dar, {ek(genis, 'i')} daha geniş, "
           f"{ek(ayni, 'i')} birebir aynı (günde en çok bir işlem açan bileşimde iki yordam aynı örneklemi kurar)")
    if oran:
        yon += f"; genişlik oranı (gün kümeli / bağımsız) {sayi(min(oran), 2)}–{sayi(max(oran), 2)}"
    parca = [yon + "."]
    for bid, c, d, v, g in degisen:
        a_, k_ = (v.get(d) or {}).get("ga_brut_alt"), (g.get(d) or {}).get("ga_brut_alt")
        if a_ is None or k_ is None:
            raise SablonHatasi(f"bayrağı ayrışan bileşimde brüt alt uç yok: {bid} {c} {d}")
        pen = "2024 →" if d == "oos" else "bütün dönem"
        s = (((v.get(d) or {}).get("sinir")) or {}).get("ga_brut_alt")
        cumle = (f"Maliyet bayrağı iki yordamda ayrışan bileşim {adlar.BIRIM[bid][1]} {PARITE[c]} ({pen}): brüt "
                 f"aralığın alt ucu bağımsız örneklemeyle {_hucre(a_, 'ra')} R, gün kümeli {_hucre(k_, 'ra')} R")
        au, ku = (v.get(d) or {}).get("ga_brut_ust"), (g.get(d) or {}).get("ga_brut_ust")
        if au is not None and ku is not None and (ku - k_) != (au - a_):
            yon_ = "daraltıyor" if (ku - k_) < (au - a_) else "genişletiyor"
            cumle += f"; burada kümeleme brüt aralığı {yon_}"
        parca.append(cumle + ".")
        if s:
            parca.append(f"Bağımsız uç sıfırın kıyısında: {_sinir_cumle(s)}.")
    return " ".join(parca)


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


def _dis_yil(u: Uretim) -> str:
    """Örneklem dışının başladığı yıl, künyeden ("2024")."""
    return str(((u.O.get("kunye") or {}).get("dis_baslangic") or "")[:4])


def blok_devam(u: Uretim, ctx: dict, boyut: str = "olay") -> str:
    """Kırılım ↔ fade devam tablosu (ön kayıt [haber_devam]): bir boyutun her değeri × her ufuk. Hücre: olay
    sayısı, iki yönün net ortalaması (günlük ATR'nin yüzdesi), örneklem dışının (2024 →) olay sayısı ve iki yönü —
    ön kayıt onun ayrıca yazılmasını ister, hükmü değiştirmez — ve ön kaydın hükmü (BH q < eşik)."""
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
            kir, fad = h.get("kir") or {}, h.get("fad") or {}
            n_oos = kir.get("oos_n") or 0
            govde.append([_boyut_ad(boyut, d), f"{f} dk", _hucre(h.get("n_olay"), "n"),
                          _hucre(kir.get("ort_atr_yuzde"), "r1"), _hucre(fad.get("ort_atr_yuzde"), "r1"),
                          _hucre(n_oos, "n"),
                          _hucre(kir.get("oos_ort_atr_yuzde"), "r1") if n_oos else "—",
                          _hucre(fad.get("oos_ort_atr_yuzde"), "r1") if n_oos else "—",
                          DEVAM_HUKUM.get(h.get("hukum"), h.get("hukum")) or "—"])
    bas = {"olay": "Olay", "kova": "İlk mum / ATR", "trend_uyum": "Haber öncesi trend", "tf": "Mum",
           "cift": "Parite", "olay_kova": "Olay · ilk mum / ATR"}.get(boyut, boyut)
    y = _dis_yil(u)
    q = sayi(float((_devam(u).get("kural") or {}).get("fdr_q", 0.1)), 2)
    return _tablo([bas, "Ufuk", "Olay sayısı", "Kırılım (ATR'nin %)", "Fade (ATR'nin %)", f"{y} →: olay",
                   f"{y} →: kırılım", f"{y} →: fade", f"Hüküm (q < {q} ile kazanan yön)"], govde,
                  ["l", "l", "r", "r", "r", "r", "r", "r", "l"])


#: Devam hükmünün okur adı. Ön kaydın terimi "ayrışmıyor" her yönü ayrı ayrı sıfıra karşı sınar (net > 0, tek
#: yönlü): iki yön birbiriyle kıyaslanmaz. Okura "kırılım ile fade arasında fark yok" diye okunmasın diye etiket
#: ölçtüğü şeyle yazılır; ön kaydın terimi tablonun dipnotunda adıyla durur.
DEVAM_HUKUM = {"ayrışmıyor": "kazanan yok"}


def blok_devam_okuma(u: Uretim, ctx: dict) -> str:
    """Devam tablosunun iki yönünün birbirine göre okunuşu, bütün hücrelerden: fade'in kırılımdan iyi olduğu hücre
    sayısı (iki yönün maliyeti aynı olduğu için bu, ilk hareketin maliyetten önce geri döndüğü hücrelerin sayısıdır),
    fade'in net ortalamasının artı olduğu hücreler ve iki yönün en küçük düzeltilmiş q değeri. Betimlemedir; hüküm
    ön kaydın kuralıyla tablodadır."""
    d = _devam(u)
    hs = d.get("hucre") or []
    if not hs:
        return ""
    k = d.get("kural") or {}
    esik = float(k.get("fdr_q", 0.1))
    ikisi = [h for h in hs if (h.get("kir") or {}).get("ort_atr_yuzde") is not None
             and (h.get("fad") or {}).get("ort_atr_yuzde") is not None]
    fb = sum(1 for h in ikisi if h["fad"]["ort_atr_yuzde"] > h["kir"]["ort_atr_yuzde"])
    fa = sum(1 for h in hs if ((h.get("fad") or {}).get("ort_atr_yuzde") or 0) > 0)
    qf = [h["fad"]["q"] for h in hs if (h.get("fad") or {}).get("q") is not None]
    qk = [h["kir"]["q"] for h in hs if (h.get("kir") or {}).get("q") is not None]
    kazanan = [h for h in hs if h.get("hukum") in ("kırılım kazanır", "fade kazanır")]
    s = (f"Fade {sayi(len(ikisi), 0)} hücrenin {ek(fb, 'inde')} kırılımdan iyi"
         + (": ilk hareket maliyetten önce hücrelerin çoğunda geri dönüyor." if 2 * fb > len(ikisi) else "."))
    if not qf or not qk:
        return s
    if not kazanan:
        s += (f" {sayi(fa, 0)} hücrede fade'in net ortalaması artı, ama hiçbir hücrede düzeltilmiş q eşiğin "
              f"({sayi(esik, 2)}) altına inmiyor (en küçük q: fade {sayi(min(qf), 2)}, kırılım {sayi(min(qk), 2)}).")
    else:
        s += (f" {sayi(fa, 0)} hücrede fade'in net ortalaması artı; {sayi(len(kazanan), 0)} hücrede bir yön "
              f"düzeltilmiş q {sayi(esik, 2)} altında kazanıyor.")
    return s


GUN_ADI = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]


def blok_saat_rejimi(u: Uretim, ctx: dict, olay: str = "ECB_basin") -> str:
    """Bir olay türünün iki saat rejimi yan yana (ölçüm: ders_olcum.saat_rejimi, kalite.haber_makasi → `saat`):
    toplantı sayısı ve dönemi, New York karşılığı, aynı dakikadaki başka takvim olayı, açıklamadan önceki son
    dakikanın makası (olaysız günlerle ve olaysız AYNI hafta günüyle kıyaslı), devam tablosunun ana mumunda 15 dakikalık
    kırılım ve fade ortalaması, beş haber stratejisinin varsayılanı ve haber öncesi aralık. Bilgi ölçüsüdür: devam
    ailesine girmez, hüküm değiştirmez."""
    sr = ((((u.O.get("haber") or {}).get("saat_rejimi")) or {}).get(olay) or {}).get("rejim") or {}
    if len(sr) < 2:
        raise SablonHatasi(f"saat_rejimi: {olay} için iki rejim yok")
    cift = next((c for c in PARITE if (((_kalite(u).get(c) or {}).get("haber_makasi") or {}).get(olay) or {})
                 .get("saat")), None)
    mk = ((((_kalite(u).get(cift) or {}).get("haber_makasi") or {}).get(olay) or {}).get("saat") or {}) if cift else {}
    bolge = BOLGE_AD.get(((((u.O.get("haber") or {}).get("saat_rejimi")) or {}).get(olay) or {}).get("bolge"), "")
    saatler = sorted(sr)
    bas = ["Ölçü"] + [f"{s} {bolge} ({tarih(sr[s]['ilk'])} → {tarih(sr[s]['son'])}; "
                      f"{blok_tsi(u, ctx, '', f'{bolge} {s}')})" for s in saatler]
    govde = []

    def satir(ad: str, f) -> None:
        govde.append([ad] + [f(sr[s], mk.get(s) or {}) for s in saatler])

    satir("Toplantı (örneklem içi · dışı)", lambda v, m: f"{sayi(v['n'], 0)} ({sayi(v['ic'], 0)} · {sayi(v['dis'], 0)})")
    def ny_saat(s: str, k: str, n: int) -> str:
        # Aynı anın New York saati olağan farktan ayrılıyorsa toplantı ara haftadadır (ABD yaz, Avrupa kış saatinde).
        olagan = {f"{adlar.tsi_an(g, s, adlar.SEHIR_BOLGE[bolge]).astimezone(ZoneInfo('America/New_York')):%H:%M}"
                  for _, g in adlar.TSI_REJIM[:2]}
        return f"{k} New York ({sayi(n, 0)})" if k in olagan else f"ara hafta: {k} New York ({sayi(n, 0)})"
    govde.append(["New York saati (toplantı)"] + [" · ".join(ny_saat(s, k, n) for k, n in sr[s]["ny"].items())
                                                  for s in saatler])
    satir("Hafta günü", lambda v, m: " · ".join(f"{GUN_ADI[int(k)]} ({sayi(n, 0)})" for k, n in v["hafta_gunu"].items()))
    def ayni_dk(v: dict) -> str:
        say: dict = {}
        for x in v["ayni_dakika"]:
            say[x["olay"]] = say.get(x["olay"], 0) + 1
        return "; ".join(f"{adlar.OLAY.get(o, o)}: {sayi(n, 0)} gün" for o, n in sorted(say.items())) or "yok"
    satir("Aynı dakikada takvimde başka olay", lambda v, m: ayni_dk(v))

    def makas(m: dict, anahtar: str) -> str:
        return _hucre(_son_dk(m, anahtar), "s1")
    satir("Makas, açıklamadan önceki son dakika (pip)", lambda v, m: makas(m, "medyan_pip"))
    satir("— aynı dakika, olaysız günler", lambda v, m: makas(m, "kiyas_pip"))
    satir("— aynı dakika, olaysız aynı hafta günü", lambda v, m: makas(m, "kiyas_gun_pip"))
    for uf in ("15", "60"):
        satir(f"Devam, {uf} dk: kırılım · fade (ATR'nin %)",
              lambda v, m, uf=uf: (f"{_hucre((v['devam'].get(uf) or {}).get('kir'), 'r1')} · "
                                   f"{_hucre((v['devam'].get(uf) or {}).get('fad'), 'r1')}"
                                   if v["devam"].get(uf) else "—"))
    for b in HABER_BIRIMLERI:
        satir(f"{adlar.BIRIM[b][1]}: net R (işlem)",
              lambda v, m, b=b: (f"{_hucre((v['strateji'].get(b) or {}).get('r'), 'ra')} "
                                 f"({sayi((v['strateji'].get(b) or {}).get('n') or 0, 0)})"
                                 if (v["strateji"].get(b) or {}).get("n") else "işlem yok"))
    satir("N3: haber öncesi aralık, medyan (pip)",
          lambda v, m: _hucre((v["aralik_pip"].get("n3") or {}).get("medyan"), "s1?"))
    return (_tablo(bas, govde, ["l"] + ["r"] * len(saatler)) +
            f"\n\n_{PARITE.get(cift, cift)}. Makas: dakika kapanışında medyan; kıyaslar olayın kendi bölgesindeki aynı "
            f"yerel dakikadan, takvimde olay olmayan hafta içi günlerinden (ikinci kıyas yalnız toplantıyla aynı hafta "
            f"gününden). Devam: ana mum, olay düzeyinde, yön başına net ortalama. Stratejiler: önceden kayıtlı "
            f"varsayılan, bütün dönem. Bu tablo bilgi içindir; devam tablosunun sınama ailesine girmez._")


def blok_saat_rejimi_aralik(u: Uretim, ctx: dict, olay: str = "ECB_basin", karar: str = "ECB_karar") -> str:
    """Bir haber stratejisinin haber öncesi aralığının medyanı, olayın iki saat rejiminde ayrı ayrı ve aynı dönemlerde
    kararın kendi aralığıyla (ölçüm: ders_olcum.saat_rejimi → aralik_pip). Birim, şablonun birimidir (BID)."""
    bid = ctx["BID"]
    sr = (((u.O.get("haber") or {}).get("saat_rejimi")) or {})
    rb = ((sr.get(olay) or {}).get("rejim")) or {}
    rk = ((sr.get(karar) or {}).get("rejim")) or {}
    if len(rb) < 2:
        raise SablonHatasi(f"saat_rejimi_aralik: {olay} için iki rejim yok")
    parca = []
    for s_b, s_k in zip(sorted(rb), sorted(rk) if len(rk) == len(rb) else [None] * len(rb)):
        x = (rb[s_b].get("aralik_pip") or {}).get(bid) or {}
        k = ((rk.get(s_k) or {}).get("aralik_pip") or {}).get(bid) or {} if s_k else {}
        if not x.get("n"):
            parca.append(f"{s_b} rejiminde bu kuralın işlemi yok")
            continue
        parca.append(f"{s_b} rejiminde {sayi(x['medyan'], 1)} pip ({sayi(x['n'], 0)} işlem)"
                     + (f"; aynı dönemde kararın kendi aralığı {sayi(k['medyan'], 1)} pip" if k.get("n") else ""))
    return "Haber öncesi aralığın medyanı ECB basın toplantısında " + ", ".join(parca) + "."


HABER_BIRIMLERI = ("n1", "n2", "n3", "n4", "n5")


def saat_ek(s: str, kip: str) -> str:
    """Saat yazımına ek: "08:30" → "08:30'da" (otuz), "08:45" → "08:45'te" (kırk beş), "14:00" → "14:00'te" (on dört).
    Uyum okunuşun son sözcüğünden: dakika sıfır değilse dakika, sıfırsa saat."""
    sa, dk = (int(x) for x in s.split(":"))
    return s + "'" + ek(dk or sa, kip).split("'", 1)[1]


def _son_dk(m: dict, anahtar: str):
    dks = m.get("dk") or []
    return (m.get(anahtar) or [None] * len(dks))[dks.index(-1)] if -1 in dks else None


def blok_saat_rejimi_cumle(u: Uretim, ctx: dict, olay: str = "ECB_basin") -> str:
    """Saat rejimi tablosunun okuması: iki rejimin New York karşılığı ve hafta günü, aynı dakikadaki takvim olayları,
    son dakikanın makası olaysız aynı hafta gününe göre ve örneklem bölünmesiyle çakışma. Cümleler sayılardan kurulur."""
    sr = ((((u.O.get("haber") or {}).get("saat_rejimi")) or {}).get(olay) or {}).get("rejim") or {}
    if len(sr) < 2:
        raise SablonHatasi(f"saat_rejimi_cumle: {olay} için iki rejim yok")
    cift = next((c for c in PARITE if (((_kalite(u).get(c) or {}).get("haber_makasi") or {}).get(olay) or {})
                 .get("saat")), None)
    mk = ((((_kalite(u).get(cift) or {}).get("haber_makasi") or {}).get(olay) or {}).get("saat") or {}) if cift else {}
    eski, yeni = sorted(sr)[0], sorted(sr)[-1]
    e, y_ = sr[eski], sr[yeni]
    ny_e = max(e["ny"].items(), key=lambda kv: kv[1])
    ny_y = max(y_["ny"].items(), key=lambda kv: kv[1])
    persembe = int(e["hafta_gunu"].get("3", 0))
    parca = [f"{tarih_uzun(y_['ilk'])} öncesindeki {sayi(e['n'], 0)} toplantının {ek(ny_e[1], 'i')} New York "
             f"saatiyle {saat_ek(ny_e[0], 'e')} ({adlar.tsi_yaz([f'New York {ny_e[0]}'])}), sonraki "
             f"{sayi(y_['n'], 0)} toplantının {ek(ny_y[1], 'i')} {saat_ek(ny_y[0], 'e')} "
             f"({adlar.tsi_yaz([f'New York {ny_y[0]}'])}) denk gelir."]
    if ny_e[0] == "08:30":
        parca.append(f"{ny_e[0]} New York ABD verilerinin dakikasıdır: "
                     f"{eski} rejimindeki toplantıların {ek(persembe, 'i')} perşembe ve ABD haftalık işsizlik "
                     f"başvuruları her perşembe {saat_ek(ny_e[0], 'de')} açıklanır (bu veri takvimde yok).")
    ayni = list(e["ayni_dakika"])
    if ayni:
        olaylar = sorted({x["olay"] for x in ayni})
        parca.append(f"{sayi(len(ayni), 0)} günde " + ", ".join(adlar.OLAY.get(o, o) for o in olaylar)
                     + " de aynı dakikada çıktı.")
    m_e = mk.get(eski) or {}
    h_e, kg_e, k_e = _son_dk(m_e, "medyan_pip"), _son_dk(m_e, "kiyas_gun_pip"), _son_dk(m_e, "kiyas_pip")
    if h_e is not None and kg_e and k_e:
        parca.append(f"Açıklamadan önceki son dakikanın makası {eski} rejiminde {sayi(h_e, 1)} pip; aynı dakikada "
                     f"olaysız günlerin medyanı {sayi(k_e, 1)}, olaysız perşembelerinki {sayi(kg_e, 1)} pip"
                     + (": genişleme basın toplantısından değil, perşembe sabahının ABD veri dakikasından gelir."
                        if h_e <= kg_e * 1.15 else ": toplantı dakikası olaysız perşembelerden de geniştir."))
    parca.append(f"Örneklem içindeki {sayi(e['ic'] + y_['ic'], 0)} basın toplantısının {ek(e['ic'], 'i')} {eski} "
                 f"rejiminde, örneklem dışındaki {sayi(e['dis'] + y_['dis'], 0)} toplantının "
                 + ("hiçbiri o rejimde değil" if e["dis"] == 0 else f"{ek(e['dis'], 'i')} o rejimde") +
                 ": basın toplantısı satırlarında örneklem içi ile örneklem dışının kıyası aynı zamanda iki saatin "
                 "kıyasıdır.")
    return " ".join(parca)


def blok_devam_cumle(u: Uretim, ctx: dict) -> str:
    """Devam tablosunun aile özeti: hücre ve sınama sayısı (tek olaylı hücrede t tanımsızdır), hüküm sayımı, kural,
    ufku gün sonuna taşan gözlemler."""
    d = _devam(u)
    if not d.get("hucre"):
        return "Devam tablosu ölçülemedi."
    k = d.get("kural") or {}
    say = d.get("hukum_sayimi") or {}
    parca = ", ".join(f"{sayi(v, 0)} hücrede {DEVAM_HUKUM.get(ad, ad)}"
                      for ad, v in sorted(say.items(), key=lambda kv: -kv[1]))
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
    sayim = (((u.O.get("takvim") or {}).get("sayim")) or {})

    def _dusen(o: str, n: int) -> str:
        t = (sayim.get(o) or {}).get("toplam")
        ad_ = adlar.OLAY.get(o, o)
        if t is None:
            return f"{ad_} {sayi(n, 0)} olay"
        return (f"{ad_} için {sayi(int(t), 0)} olayın hepsi" if int(t) == n
                else f"{ad_} için {sayi(int(t), 0)} olayın {ek(n, 'i')}")
    for tf, uf in sorted(kirp.items(), key=lambda kv: int(kv[0])):
        for ufuk, olaylar in sorted(uf.items(), key=lambda kv: int(kv[0])):
            if olaylar:
                sira = [o for o in olay_sira(u) if o in olaylar] + [o for o in olaylar if o not in olay_sira(u)]
                s += (f" {tf} dakikalık mumda {ufuk} dakikalık ufuk gün sonunu aşan olaylarda doldurulamaz; o gözlemler "
                      f"hücreye girmez. Bu ufukta düşen olaylar: "
                      + ", ".join(_dusen(o, int(olaylar[o])) for o in sira) + ".")
    return s


def blok_devam_yetersiz(u: Uretim, ctx: dict, boyut: str = "olay_kova") -> str:
    """Bir devam tablosunda olay sayısı eşiğin altında kalan satırların sayımı (her ufukta aynıdır)."""
    d = _devam(u)
    k = d.get("kural") or {}
    asg = int(k.get("asgari_olay", 20))
    hs = [h for h in d.get("hucre") or [] if h.get("boyut") == boyut]
    if not hs:
        return ""
    ufuklar = sorted({int(h["ufuk"]) for h in hs})
    satir = [h for h in hs if int(h["ufuk"]) == ufuklar[0]]
    alt = [h for h in satir if (h.get("n_olay") or 0) < asg]
    alt_tum = [h for h in hs if (h.get("n_olay") or 0) < asg]
    if len(ufuklar) == 1:
        return (f"tablonun {sayi(len(satir), 0)} satırının {ek(len(alt), 'inde')} olay sayısı {ek(asg, 'in')} altında "
                f"(hüküm: \"yetersiz örneklem\")")
    return (f"{sayi(len(satir), 0)} olay–kova bileşiminin {ek(len(alt), 'inde')} (tablonun {sayi(len(hs), 0)} satırının "
            f"{ek(len(alt_tum), 'inde')}; her bileşim {sayi(len(ufuklar), 0)} ufukta bir satırdır) olay sayısı "
            f"{ek(asg, 'in')} altında (hüküm: \"yetersiz örneklem\")")


def _esik_pay(u: Uretim, tf: str, kova: str) -> float:
    toplam = sec = 0
    for c in PARITE:
        kd = (((((u.O.get("haber") or {}).get("cift") or {}).get(c) or {}).get("kova_dagilimi")) or {}).get(str(tf)) or {}
        for o, v in kd.items():
            toplam += sum(int(x) for x in v.values())
            sec += int(v.get(kova) or 0)
    if not toplam:
        raise SablonHatasi("esik_payi: kova dağılımı yok")
    return sec / toplam


def blok_kural_iddia(u: Uretim, ctx: dict, olcu: str, *birimler: str) -> str:
    """Sayı taşımayan bir cümlenin (ör. ön bilgideki kart özeti) dayanağı, birim listesinin bütün paritelerinde ve
    önceden kayıtlı varsayılanın örneklem dışı sonucunda: "calisan_yok" (hiçbir hüküm çalışıyor değil), "hepsi_eksi"
    (işlem başına net R hepsinde eksi), "rastgele_yok" (rastgele yön yüzdeliği hiçbirinde eşiğin üstünde değil).
    Tutmazsa üretim DÜŞER; çıktıya bir şey yazmaz."""
    esik = (u.ON.get("hukum") or {}).get("rastgele_esik_yuzdelik", 95)
    if olcu not in ("calisan_yok", "hepsi_eksi", "rastgele_yok") or not birimler:
        raise SablonHatasi(f"kural_iddia: bilinmeyen ölçü ya da boş birim listesi: {olcu}")
    for bid in birimler:
        b = (u.O.get("birim") or {}).get(bid)
        if not b:
            raise SablonHatasi(f"kural_iddia: {bid} ölçülmedi")
        for c in _ciftler(b):
            v = b["cift"][c].get("varsayilan") or {}
            r = (v.get("oos") or {}).get("beklenti_r")
            y = ((v.get("rastgele") or {}).get("oos") or {}).get("yuzdelik")
            tutar = {"calisan_yok": v.get("hukum") != "calisiyor",
                     "hepsi_eksi": r is not None and r < 0,
                     "rastgele_yok": y is None or not math.isfinite(y) or y < esik}[olcu]
            if not tutar:
                raise SablonHatasi(f"İDDİA TUTMADI: kural_iddia {olcu} — {bid} {PARITE[c]}")
    u.iddia += 1
    return ""


def blok_fade_maliyet(u: Uretim, ctx: dict) -> str:
    """Fade dersinin girişi: dört fade ↔ kırılım eşinde (aynı seviye) ana paritenin örneklem dışı R birimi medyanı
    (stop uzaklığı) ve maliyetin işlem başına R cinsinden ortalaması (brüt R − net R). "Fade'de maliyet daha
    belirleyici" hükmü eş eş bu iki sayıdan kurulur; uymayan eş adıyla yazılır."""
    c = ana()
    esler = [("sahte_orb", "orb"), ("sahte_asya", "asya"), ("sahte_pdhl", "pdhl"), ("pivot_donus", "pivot_kirilim")]
    satir, tutan, uymayan = [], [], []
    for f, k in esler:
        vf = ((((u.O["birim"].get(f) or {}).get("cift") or {}).get(c) or {}).get("varsayilan") or {}).get("oos") or {}
        vk = ((((u.O["birim"].get(k) or {}).get("cift") or {}).get(c) or {}).get("varsayilan") or {}).get("oos") or {}
        if not vf.get("n") or not vk.get("n"):
            raise SablonHatasi(f"fade_maliyet: {f} ya da {k} {PARITE[c]}'de ölçülmedi")
        sf, sk = float(vf["risk_pip"]), float(vk["risk_pip"])
        mf, mk_ = float(vf["brut_r"]) - float(vf["beklenti_r"]), float(vk["brut_r"]) - float(vk["beklenti_r"])
        satir.append(f"{adlar.BIRIM[f][1]} ↔ {adlar.BIRIM[k][1]}: stop {sayi(sf, 1)} ↔ {sayi(sk, 1)} pip, maliyet "
                     f"{sayi(mf, 2)} ↔ {sayi(mk_, 2)} R")
        (tutan if (sf < sk and mf > mk_) else uymayan).append(adlar.BIRIM[f][1])
    s_ = (f"{PARITE[c]}'de örneklem dışında, fade ↔ aynı seviyenin kırılımı, R biriminin (stop uzaklığının) medyanı ve "
          f"maliyetin işlem başına R cinsinden ortalaması (brüt − net): " + "; ".join(satir) + ".")
    if not uymayan:
        return s_ + (f" {sayi(len(esler), 0)} eşin hepsinde fade'in stopu daha dar ve maliyeti R cinsinden daha büyük: "
                     f"fade kurallarında maliyet satırı kırılımlarınkinden daha belirleyicidir.")
    if not tutan:
        return s_ + " Hiçbir eşte fade'in stopu hem daha dar hem maliyeti R cinsinden daha büyük değil."
    return s_ + (f" {sayi(len(esler), 0)} eşin {tane(len(tutan), 'inde')} ({', '.join(tutan)}) fade'in stopu daha "
                 f"dar ve maliyeti R cinsinden daha büyük; {', '.join(uymayan)} bu genellemeye uymuyor.")


def blok_esik_payi(u: Uretim, ctx: dict, tf: str = "5", kova: str = ">2") -> str:
    """İlk haber mumunun bir kovaya düşme payı, bütün paritelerin olay ölçümlerinde (haber analizinin kova dağılımı):
    N2'nin eşiği (2 × ATR) ne kadar seyrek aşılıyor?"""
    return yuzde(_esik_pay(u, tf, kova), 0)


def blok_esik_cumle(u: Uretim, ctx: dict, tf: str = "5", kova: str = ">2") -> str:
    """N2'nin eşiğinin okunuşu, payın kendisinden: eşik haberden önceki oynaklığa göre kurulur; haber mumlarının ne
    kadarının onu aştığı "yüksek eşik" hükmünü verir ya da çürütür."""
    p = _esik_pay(u, tf, kova)
    pay = (f"{_parite_sayisi(u)} paritenin bütün olaylarında {tf} dakikalık ilk haber mumlarının {yuzde_ek(p, 'i')} iki ATR'yi "
           f"aşıyor")
    if p < 0.25:
        return f"Eşik yüksektir: {pay}, yani kural yalnız büyük tepkilerin günlerinde işlem açar."
    if p < 0.5:
        return (f"Eşik haber mumları için orta düzeydedir: {pay}; kural olayların azınlığında tetiklenebilir ve teyit "
                f"mumu ayrıca beklenir.")
    return (f"Eşik haberden önceki oynaklığa göre yüksektir ama haber mumları için seyrek değildir: {pay}; kural "
            f"olayların yarısından fazlasında tetiklenebilir ve teyit mumu ayrıca beklenir.")


#: Hiçbir paritede işleme dönüşmeyen olayın sebebi (ders_olcum.tek_pozisyon; motor.DURUM ve "karma").
OLAY_SEBEP = {"pozisyon_acik": "açık bir pozisyon yüzünden",
              "hedef_gecersiz": "yürütülen giriş seviye hedefine vardığı ya da onu geçtiği için",
              "risk_gecersiz": "giriş dakikasında fiyat stopun ötesinde ya da tam üstünde açıldığı için",
              "gun_sonu": "girişi gün sonundan sonraya düştüğü için",
              "veri_yok": "giriş dakikasının verisi olmadığı için",
              "karma": "paritelerde farklı sebeplerle"}


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
    y = _dis_yil(u)
    k_ = u.O["kunye"]
    basliklar = [bas, "Bütün dönem: işlem (olay)", "Bütün dönem: net R (%95)", f"{y} →: işlem (olay)",
                 f"{y} →: net R (%95)"]
    if aralik:
        basliklar.append("Haber öncesi aralık, medyan (pip)")
    donem = f"Bütün dönem {k_['baslangic'][:4]} → {k_['bitis'][:4]}, örneklem dışı {y} →. "
    not_ = donem + (f"{bas_buyuk(_parite_sayisi(u))} paritenin işlemleri birlikte; %95 aralığı olay kümeli. Satırların her biri ayrı bir "
                    f"sınamadır ({sayi(len(govde), 0)} satır): aralığı sıfırın dışında kalan tek bir satır şansla da "
                    f"çıkabilir." if len(govde) > 1 else f"{bas_buyuk(_parite_sayisi(u))} paritenin işlemleri birlikte; %95 aralığı olay kümeli.")
    if boyut == "olay":
        tp = [(o, v) for o in olay_sira(u) for v in [(b.get("tek_pozisyon") or {}).get(o)]
              if v and v.get("engellenen")]
        if tp:
            def sebepler(v: dict) -> str:
                s = v.get("sebep") or {}
                if not s:              # eski ölçüm dosyası: sebep ayrımı yok
                    raise SablonHatasi("tek pozisyon sayımı sebep taşımıyor; ders_olcum.py yeniden koşulmalı")
                n = int(v.get("engellenen") or 0)
                var = [k for k in OLAY_SEBEP if s.get(k)]
                if len(var) == 1 and int(s[var[0]]) == n:          # tek sebep hepsini kapsıyor: sayım sözcükle
                    return ("tek olay " if n == 1 else f"{sayi(n, 0)} olayın hepsi ") + OLAY_SEBEP[var[0]]
                return f"{sayi(n, 0)} olayın " + ", ".join(f"{ek(s[k], 'i')} {OLAY_SEBEP[k]}" for k in var)
            def acan(v: dict) -> str:
                a = v.get("acik_olay") or {}
                if not a:
                    return ""
                sira = sorted(a.items(), key=lambda kv: (kv[0] in ("karma", "bulunamadı"), -kv[1]))
                ad = {"karma": "paritelere göre farklı", "bulunamadı": "bulunamadı"}
                return "; açık pozisyonu açan olay: " + " · ".join(
                    f"{ad.get(k) or adlar.olay_ic(k)} {sayi(n, 0)}" for k, n in sira)
            not_ += (" Sinyal verip hiçbir paritede işleme dönüşmeyen olay bu tabloda yoktur; satır yalnız işlem açılan "
                     "olayları taşır: "
                     + "; ".join(f"{adlar.OLAY.get(o, o)} takvimde {sayi(v['takvim'], 0)}, sinyal veren "
                                 f"{sayi(v['aday'], 0)}, işlem açılan {sayi(v['alinan'], 0)} olay (alınmayan "
                                 f"{sebepler(v)}{acan(v)})" for o, v in tp) + ".")
            # Basın toplantısının alınmamasının sebebi çoğunlukla aynı günün kararının hâlâ açık işlemiyse satır rastgele
            # bir alt küme değildir: yalnız kararın işleminin toplantıdan önce kapandığı ya da kararın işlem açmadığı
            # toplantılardan oluşur. Cümle yalnız ölçüm bunu söylüyorsa kurulur.
            alt = [o for o, v in tp if o.endswith("_basin")
                   and (v.get("acik_olay") or {}).get(o.replace("_basin", "_karar"), 0) * 2 > (v.get("engellenen") or 0)]
            if alt:
                tek = len(alt) == 1
                not_ += (f" {liste_yaz([adlar.OLAY.get(o, o) for o in alt])} {'satırı' if tek else 'satırları'} bu "
                         "yüzden rastgele bir alt küme değildir: aynı günün kararının işlemi "
                         f"toplantı başladığında hâlâ açıksa toplantı alınmaz, yani {'satır' if tek else 'satırlar'} "
                         "yalnız kararın işleminin toplantıdan önce kapandığı ya da kararın işlem açmadığı "
                         "toplantılardan oluşur.")
    return _tablo(basliklar, govde, ["l"] + ["r"] * (len(basliklar) - 1)) + f"\n\n_{not_}_"


def _fomc_satirlari(u: Uretim, pencere: str):
    for c, h in sorted(((u.O.get("haber") or {}).get("cift") or {}).items(), key=lambda kv: list(PARITE).index(kv[0])
                       if kv[0] in PARITE else 99):
        oz = ((h or {}).get("fomc") or {}).get("ozet") or {}
        bp = oz.get(pencere) or {}
        if bp:
            yield c, oz, bp


def _fomc_saat(u: Uretim) -> dict:
    """FOMC pencerelerinin New York saatleri: karar ve basın toplantısının başlangıcı takvimin kuralından, basın
    pencerelerinin sonu ölçümün sabitinden (haber_sabit.fomc_basin_sn = strat_haber.FOMC_BASIN_SN). Elle yazılan saat
    pencere değiştiği gün yanlış dakikayı anlatırdı. Pencerelerin sözcükle adı ("ilk saatinde", "ilk doksan
    dakikasında": FOMC_SIFIR) yalnız 60 ve 90 dakikada doğrudur; sabit başka bir şey söylüyorsa üretim düşer."""
    kural = ((((u.O.get("takvim") or {}).get("kunye") or {}).get("fomc") or {}).get("kural")) or {}
    sn = ((u.O.get("kunye") or {}).get("haber_sabit") or {}).get("fomc_basin_sn")
    if not kural.get("karar") or not kural.get("basin") or not sn:
        raise SablonHatasi("fomc saatleri: takvimin FOMC kuralı ya da ölçümün basın penceresi yok")
    if [int(x) for x in sn] != [3600, 5400]:
        raise SablonHatasi(f"fomc saatleri: basın pencereleri {sn} sn; pencerelerin adı 60 ve 90 dakikaya yazılı")
    bas = datetime.strptime(kural["basin"], "%H:%M")
    son = [(bas + timedelta(seconds=int(x))).strftime("%H:%M") for x in sn]
    return {"karar": kural["karar"], "basin": kural["basin"], "son60": son[0], "son90": son[1]}


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
    fs = _fomc_saat(u)
    ny_bas, ny_son = f"New York {fs['basin']}", f"New York {fs['son90']}"
    t2 = (f"\n\nBasın penceresi {saat_ek(fs['son90'], 'e')} uzatıldığında ({ny_bas} → {fs['son90']}; "
          f"{adlar.tsi_yaz([ny_bas, ny_son], '→')}):\n\n" +
          _tablo(["Parite", "Toplantı", "Dönüş oranı (%95)", "Korelasyon (%95)"], g2, ["l", "r", "r", "r"])) if g2 else ""
    return t1 + t2


FOMC_SIFIR = {"karar": "kararının ilk yarım saatinde", "basin_60": "basın toplantısının ilk saatinde",
              "basin_90": "basın toplantısının ilk doksan dakikasında"}


def blok_fomc_payda(u: Uretim, ctx: dict) -> str:
    """FOMC tablolarının "Toplantı" sütunu dönüş oranının paydasıdır: iki hareketten biri sıfır olan toplantı
    yönsüzdür ve sayılmaz (strat_haber.fomc_ozet), korelasyon ise bütün toplantılardan. Düşen toplantılar ölçümün
    satırlarından adıyla ve sebebiyle; sayım ölçünün paydasıyla tutmazsa SablonHatasi."""
    cift = (u.O.get("haber") or {}).get("cift") or {}
    dusen = {}
    toplam = {}
    for pencere in ("basin_60", "basin_90"):
        for c, oz, bp in _fomc_satirlari(u, pencere):
            satir = ((cift.get(c) or {}).get("fomc") or {}).get("satir") or []
            toplam[c] = len(satir)
            d = [(r["tarih"], next(ad for ad in ("karar", pencere) if r.get(ad) == 0)) for r in satir
                 if r.get("karar") == 0 or r.get(pencere) == 0]
            if len(satir) - len(d) != (bp.get("donus") or {}).get("n"):
                raise SablonHatasi(f"fomc_payda: {c} {pencere}: {len(satir)} toplantıdan {len(d)} düştü ama payda "
                                   f"{(bp.get('donus') or {}).get('n')}")
            dusen.setdefault(c, {})[pencere] = d
    if not toplam:
        raise SablonHatasi("fomc_payda: FOMC ölçümü yok")
    parca = []
    for c, pen in dusen.items():
        d60, d90 = pen.get("basin_60", []), pen.get("basin_90", [])
        for p, d in (("basin_60", d60), ("basin_90", d90)):
            if not d or (p == "basin_90" and d == d60):
                continue
            sebep = "; ".join(f"{tarih(t)} {FOMC_SIFIR[ad]} hareket sıfır" for t, ad in d)
            kapsam = ("iki pencerede de" if p == "basin_60" and d == d90 else
                      "ilk saatte" if p == "basin_60" else f"{saat_ek(_fomc_saat(u)['son90'], 'e')} uzatılan pencerede")
            parca.append(f"{PARITE[c]}'de {sebep} olduğu için {toplam[c] - len(d)} ({kapsam})")
    n_kor = sorted(set(toplam.values()))
    kor = (f"korelasyon her paritede {n_kor[0]} toplantının hepsinden" if len(n_kor) == 1 else
           "korelasyon her paritede o paritenin bütün toplantılarından")
    if not parca:
        return (f"Toplantı sütunu dönüş oranının paydasıdır; hiçbir toplantıda iki hareketten biri sıfır değil, "
                f"{kor}.")
    return (f"Toplantı sütunu dönüş oranının paydasıdır: iki hareketten biri sıfırsa toplantı yönsüzdür ve sayılmaz. "
            f"{'; '.join(parca)}; {kor}.")


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
            cumle.append(f"Dönüş oranı {_paritede(don)} yazı turadan sık: basın toplantısı kararın ilk hareketini "
                         f"çoğunlukla tersine çeviriyor.")
        if dev:
            cumle.append(f"{_paritede(dev)} dönüş yazı turadan seyrek: basın toplantısı kararın ilk hareketini "
                         f"çoğunlukla sürdürüyor.")
        if yt:
            cumle.append(f"{_paritede(yt)} dönüş oranı yazı turadan ayırt edilemiyor.")
    ayr = [c for c, _, _ in satir if c not in sif]
    if not ayr:
        cumle.append("İki hareketin ilintisi hiçbir paritede sıfırdan ayırt edilemiyor.")
    else:
        isaret = {c: ("artı (basın toplantısı kararın yönünü sürdürüyor)" if b["korelasyon"] > 0 else
                      "eksi (basın toplantısı kararın yönünü tersine çeviriyor)") for c, _, b in satir}
        cumle.append("İki hareketin ilintisi " + "; ".join(f"{PARITE[c]}'de {isaret[c]}" for c in ayr)
                     + (f"; {_paritede(sif)} sıfırdan ayırt edilemiyor." if sif else "."))
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
                     + (f"{(SAYI_AD.get(n, str(n)) + ' paritenin hepsinde').capitalize() if len(alt) == n else _paritede(alt)} oran bunun "
                        f"altında: dakika başına kararın yarım saati basın toplantısının ilk saatinden daha hareketli."
                        if alt else "Oran hiçbir paritede bunun altında değil: basın toplantısı dakika başına da "
                                    "kararın yarım saati kadar hareketli.")
                     + (f" {_paritede([c for c, _ in oran if c not in alt])} değil." if alt and len(alt) < len(oran)
                        else ""))
    s90 = [(c, b90.get("donus") or {}, b90) for c, _, b90 in _fomc_satirlari(u, "basin_90")
           if (b90.get("donus") or {}).get("alt") is not None and b90.get("korelasyon_alt") is not None]
    if s90:
        yt90 = [c for c, dn, _ in s90 if dn["alt"] <= 0.5 <= dn["ust"]]
        sif90 = [c for c, _, b in s90 if b["korelasyon_alt"] <= 0 <= b["korelasyon_ust"]]
        son90 = _fomc_saat(u)["son90"]
        uzat = f"Basın penceresi New York {saat_ek(son90, 'e')} ({adlar.tsi_yaz([f'New York {son90}'])}) uzatıldığında"
        if len(yt90) == len(s90) and len(sif90) == len(s90):
            cumle.append(f"{uzat} da sonuç aynı: dönüş oranı hiçbir paritede yazı turadan, ilinti sıfırdan ayırt "
                         "edilemiyor.")
        else:
            cumle.append(f"{uzat} "
                         "dönüş oranı " +
                         (f"{_paritede(yt90)} yazı turadan ayırt edilemiyor" if yt90 else
                          "her paritede yazı turadan ayırt ediliyor") +
                         ("; ilinti " + (f"{_paritede(sif90)} sıfırdan ayırt edilemiyor" if sif90 else
                                         "her paritede sıfırdan ayırt ediliyor")) + ".")
    return " ".join(cumle)


def hukum_sayim_yaz(b: dict, anahtar: str = "hukum") -> str:
    """Parite başına hükümlerin sayımı: "2 zayıf · 2 çalışmıyor" (sıra: çalışıyor, zayıf, çalışmıyor, ölçülemedi). Az
    işlemle verilen hüküm (kosu az_islem bayrağı) ayrı sayılır: "2 zayıf (az işlem)"; strateji dersi aynı hücreyi
    işlem sayısıyla basar, iki ders aynı hükmü farklı bilgiyle yazmasın."""
    d = "oos" if anahtar == "hukum" else "tum"
    say: dict = {}
    for c in _ciftler(b):
        v = b["cift"][c].get("varsayilan") or {}
        h = v.get(anahtar) or "olculemedi"
        az = bool((v.get("az_islem") or {}).get(d)) and h != "olculemedi"
        say[(h, az)] = say.get((h, az), 0) + 1
    return " · ".join(f"{say[(h, az)]} {adlar.HUKUM[h]}" + (" (az işlem)" if az else "")
                      for h in ("calisiyor", "zayif", "calismiyor", "olculemedi") for az in (False, True)
                      if say.get((h, az))) or "—"


def blok_karsilik(u: Uretim, ctx: dict, *ciftler: str) -> str:
    """Bir kural ile öbür dersteki karşılığı ("a:b" çiftleri): havuzun bütün dönem brüt ve net R'si (aralığıyla) ve
    çiftin günlük R korelasyonu (ders_olcum.korelasyon, havuzun günlük toplamı). Karşılıklar aynı işlemin iki yönü
    değildir — ayrı pencerede ya da ayrı tetikle girerler; tersi olsalardı brütleri ters işaretli, günlük
    korelasyonları eksi bire yakın olurdu. Okuma cümlesi bunu çift çift sayar."""
    kor = u.O.get("korelasyon") or {}
    bs, m = kor.get("birimler") or [], kor.get("tum") or []
    govde, okuma = [], []
    for cift in ciftler:
        a, b_ = cift.split(":")
        satir_ = []
        for bid in (a, b_):
            b = (u.O.get("birim") or {}).get(bid)
            if not b:
                raise SablonHatasi(f"karsilik: {bid} ölçümde yok")
            h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("tum") or {}
            satir_.append((bid, h))
        r = m[bs.index(a)][bs.index(b_)] if a in bs and b_ in bs else None
        for i, (bid, h) in enumerate(satir_):
            govde.append([adlar.BIRIM[bid][1],
                          f"{_hucre(h.get('brut_r'), 'ra')} ({_hucre(h.get('ga_brut_alt'), 'ra')} / "
                          f"{_hucre(h.get('ga_brut_ust'), 'ra')})",
                          f"{_hucre(h.get('beklenti_r'), 'ra')} ({_hucre(h.get('ga_alt'), 'ra')} / "
                          f"{_hucre(h.get('ga_ust'), 'ra')})",
                          _hucre(r, "r")])
        brut = [(h.get("brut_r") or 0) > 0 for _, h in satir_]
        alt = [(h.get("ga_brut_alt") or 0) > 0 for _, h in satir_]
        net = [(h.get("beklenti_r") or 0) <= 0 for _, h in satir_]
        ad = f"{adlar.BIRIM[a][1]} ile {adlar.BIRIM[b_][1]}"
        if all(brut):
            s = (f"{ad}: ikisinin de brütü artı ve aralığı sıfırın üstünde" if all(alt) else
                 f"{ad}: ikisinin de brütü artı, aralığı yalnız birinde sıfırın üstünde" if any(alt) else
                 f"{ad}: ikisinin de brütü artı ama aralıkları sıfırı kapsıyor")
        elif not any(brut):
            s = f"{ad}: ikisinin de brütü sıfır ya da eksi"
        else:
            s = f"{ad}: yalnız birinin brütü artı"
        s += (", ikisini de maliyet eksiye çeviriyor" if all(net) and all(brut) else
              ", ikisi de maliyetten sonra eksi" if all(net) else "")
        s += f"; günlük R korelasyonu {_hucre(r, 'r')}" if r is not None else ""
        okuma.append(s)
    if not govde:
        return ""
    tablo = _tablo(["Kural", "Brüt R, havuz, bütün dönem (%95)", "Net R, havuz, bütün dönem (%95)",
                    "Çiftin günlük R korelasyonu"], govde, ["l", "r", "r", "r"])
    K = u.O.get("kunye") or {}
    return (tablo + f"\n\n_Bütün dönem ({str(K.get('baslangic'))[:4]} →), önceden kayıtlı varsayılanlar, "
            f"{_parite_sayisi(u)} paritenin havuzu; korelasyon havuzun günlük R toplamları arasında (işlemsiz gün "
            "sıfır); korelasyon çiftin iki satırında aynıdır. Bir kural öbürünün tersi olsaydı brütleri ters işaretli, "
            "günlük korelasyonları eksi bire yakın olurdu._"
            "\n\n" + ". ".join(bas_buyuk(x) for x in okuma) + ".")


def blok_ders_ozet(u: Uretim, ctx: dict, *birimler: str) -> str:
    """Dersin stratejileri yan yana: havuzun örneklem dışı net R'si ve aralığı, ana paritenin net pipi, parite
    hükümlerinin sayımı, maliyet bayrağı (iki dönem), ana paritenin başabaş kayması ve R birimi. Birim verilmezse bu
    derste işlenenler."""
    liste = list(birimler) or list(u.birimler)
    if liste == ["hepsi"]:
        liste = _butun_birimler(u)
    c0 = ana()
    govde, havuz_sin = [], []
    for bid in liste:
        b = (u.O.get("birim") or {}).get(bid)
        if not b:
            continue
        h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        cs = _ciftler(b)
        my = sum(1 for c in cs if (b["cift"][c].get("varsayilan") or {}).get("maliyet_yiyor"))
        myo = sum(1 for c in cs if (b["cift"][c].get("varsayilan") or {}).get("maliyet_yiyor_oos"))
        e = ((b.get("cift") or {}).get(c0) or {}).get("varsayilan") or {}
        # Havuzun sıfıra yakın aralık ucu (işareti tohum gürültüsüne bağlı): hücrede † ile, tablonun altında sayısıyla.
        hs = [(uc, s_) for uc, s_ in ((h.get("sinir") or {}).items()) if s_.get("sinirda")]
        havuz_sin += [(("havuz", bid, uc), f"{adlar.BIRIM[bid][1]}: {UC_KISA.get(uc, uc)} {_sinir_cumle(s_)}",
                       adlar.BIRIM[bid][1]) for uc, s_ in hs]
        govde.append([adlar.BIRIM[bid][1], _hucre(h.get("n"), "n"),
                      f"{_hucre(h.get('beklenti_r'), 'ra')} ({_hucre(h.get('ga_alt'), 'ra')} / {_hucre(h.get('ga_ust'), 'ra')})"
                      + (" †" if hs else ""),
                      _hucre((e.get("oos") or {}).get("beklenti_pip"), "p1"), hukum_sayim_yaz(b),
                      f"{sayi(my, 0)} · {sayi(myo, 0)}", _basabas_hucre(e, "_oos"),
                      _hucre((e.get("oos") or {}).get("risk_pip"), "s1")])
    if not govde:
        return "_Özet için strateji yok._"
    p0 = PARITE[c0]
    sin = []
    for bid in liste:
        b = (u.O.get("birim") or {}).get(bid)
        for c, k, d, uc, s_ in (sinirda_kayitlar(b, ("varsayilan",)) if b else []):
            if uc == "ga_brut_alt":
                yanar = bool(((b["cift"][c].get("varsayilan") or {}).get("maliyet_yiyor" if d == "tum"
                                                                           else "maliyet_yiyor_oos")))
                sin.append(((bid, c, d, uc),
                            f"{adlar.BIRIM[bid][1]} {PARITE[c]}, {DONEM_AD[d]} (bayrak "
                            f"{'yanıyor' if yanar else 'yanmıyor'}; 2.000 tekrarla brüt alt uç {_hucre(s_['uc'], 'ra')} R, "
                            f"sıfıra standart hatanın {sayi(abs(s_['uzaklik_se']), 2)} katı uzaklıkta; "
                            f"{sayi(s_['tekrar'], 0)} tekrarla {_hucre(s_['kesin'], 'ra')} R; 2.000 tekrarlı yordam "
                            f"tohumların {yuzde_ek(s_['pozitif_pay'], 'inde')} yakar)",
                            f"{adlar.BIRIM[bid][1]} {PARITE[c]}, {DONEM_AD[d]}"))

    def _not(kayit: list, bas: str) -> str:
        """Sınır notu: ayrıntı dersin ilk tablosunda bir kez; aynı derste sonraki tablo yalnız adını ve atfını yazar."""
        if not kayit:
            return ""
        yeni = [t for k, t, _ in kayit if k not in u.sinir_basildi]
        eski = [a for k, _, a in kayit if k in u.sinir_basildi]
        u.sinir_basildi.update(k for k, _, _ in kayit)
        parca = []
        if yeni:
            parca.append("; ".join(yeni))
        if eski:
            parca.append(("; ".join(eski)) + " (ayrıntı yukarıdaki tablonun notunda)")
        return f"\n\n_{bas}" + "; ".join(parca) + "._"
    return (_tablo(["Strateji", "İşlem (havuz)", "Net R, havuz (%95)", f"Net pip, {p0}", "Parite hükümleri",
                    "Maliyet bayrağı (bütün · 2024 →)", f"Başabaş kayma, {p0} (pip)", f"R birimi medyanı, {p0} (pip)"],
                   govde, ["l", "r", "r", "r", "l", "r", "r", "r"]) +
            "\n\n_Örneklem dışı (2024 →), önceden kayıtlı varsayılan." + _turetilmis_tablo_notu(u, liste)
            + " Tanımlar giriş dersinde._"
            + _not(havuz_sin, "† Havuz aralığının ucu sıfırda (işareti tohum gürültüsüne bağlı; hüküm değişmez): ")
            + _not(sin, "Sınırdaki maliyet bayrakları (yanıp yanmadığı tohum gürültüsüne bağlı): "))


def blok_ozet_olcu(u: Uretim, ctx: dict, *birimler: str) -> str:
    """Özet tablonun ikinci yarısı: havuzun örneklem dışı Sharpe'ı, isabeti, kâr çarpanı (R) ve azami düşüşü (R).
    Ayrı tablo, çünkü on iki sütun telefonda okunmaz; satır sırası ilk tablonunkiyle aynı. Pip karşılıkları havuzda
    yoktur (pariteler arası pip toplanamaz); paritelerinki strateji bölümlerinin anatomi tablosunda."""
    liste = list(birimler) or list(u.birimler)
    if liste == ["hepsi"]:
        liste = _butun_birimler(u)
    govde = []
    for bid in liste:
        b = (u.O.get("birim") or {}).get(bid)
        if not b:
            continue
        h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        govde.append([adlar.BIRIM[bid][1], _hucre(h.get("sharpe"), "sh"), _hucre(h.get("isabet"), "yz1"),
                      _hucre(h.get("pf_r"), "s2"), _hucre(h.get("azami_dusus_r"), "s1"),
                      _hucre(h.get("ort_kazanc_r"), "ra"), _hucre(h.get("ort_kayip_r"), "ra")])
    if not govde:
        return "_Özet için strateji yok._"
    return (_tablo(["Strateji", "Sharpe (yıllık)", "İsabet", "Kâr çarpanı (R)", "Azami düşüş (R)", "Ort. kazanç (R)",
                    "Ort. kayıp (R)"], govde, ["l", "r", "r", "r", "r", "r", "r"])
            + f"\n\n_Örneklem dışı (2024 →), önceden kayıtlı varsayılan, {_parite_sayisi(u)} paritenin işlemleri "
              "birlikte (havuz)." + _turetilmis_tablo_notu(u, liste)
            + " Sharpe ve azami düşüş paritelerin günlük R toplamından; kâr çarpanı 1'in altındaysa "
              "kaybedilen R kazanılandan büyüktür. Tanımlar giriş dersinde, paritelerin pip karşılıkları strateji "
              "bölümlerinin anatomi tablolarında._")


def _turetilmis_tablo_notu(u: Uretim, birimler) -> str:
    """Tablo notu: satırlarından biri türetilmiş varsayılan taşıyorsa, adıyla ve kaynağıyla (bir cümle)."""
    par = []
    for bid in birimler:
        b = (u.O.get("birim") or {}).get(bid) or {}
        tn = _turetme_notu(b)
        if tn:
            par.append(f"{adlar.BIRIM[bid][1]}: varsayılanı {tn}")
    return (" " + bas_buyuk("; ".join(par)) + ".") if par else ""


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
                         + (f" · az işlem ({sayi(o.get('n') or 0, 0)})" if (v.get("az_islem") or {}).get("oos") else "")
                         if v else "—")
        h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        satir.append(_hucre(h.get("beklenti_r"), "ra"))
        govde.append(satir)
    if not govde:
        return "_Strateji yok._"
    tn = _turetilmis_tablo_notu(u, _butun_birimler(u))
    return (_tablo(["Strateji"] + list(PARITE.values()) + ["Havuz"], govde, ["l"] + ["r"] * (len(PARITE) + 1))
            + (f"\n\n_{tn.strip()}_" if tn else ""))


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


def maliyet_sayim(u: Uretim) -> dict:
    """Maliyet bayrağının (brüt aralığın alt ucu > 0, net ≤ 0) varsayılanlardaki sayımı, iki dönemde: önceden kayıtlı
    2.000 tekrarla yayımlanan, büyük tekrarlı kestirimle (metrik.sinir_bilgisi; yalnız sıfıra yakın uçlarda) ve
    sınırdaki bileşimler."""
    out = {d: {"yayim": 0, "kesin": 0, "sinirda": []} for d in ("tum", "oos")}
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            v = b["cift"][c].get("varsayilan") or {}
            for d, alan in (("tum", "maliyet_yiyor"), ("oos", "maliyet_yiyor_oos")):
                m = v.get(d) or {}
                yayim = bool(v.get(alan))
                sn = ((m.get("sinir") or {}).get("ga_brut_alt")) or {}
                kesin = (bool(sn["kesin"] > 0 and (m.get("beklenti_r") or 0) <= 0) if sn else yayim)
                out[d]["yayim"] += yayim
                out[d]["kesin"] += kesin
                if sn.get("sinirda"):
                    out[d]["sinirda"].append({"birim": bid, "cift": c, "yayim": yayim, "kesin": kesin, "kayit": sn})
    return out


def blok_genel_hukum(u: Uretim, ctx: dict) -> str:
    """Bütün kuralların hüküm sayımı (strateji × parite), iki dönemde; havuzda aralığı sıfırın üstünde kalan kurallar;
    maliyet bayrağı iki dönemde."""
    g = _hukum_sayimi_hepsi(u)
    s_, t_, k = g["say"], g["tum"], g["kural"]

    def sayim(d):
        return (f"{sayi(d['calisiyor'], 0)} çalışıyor, {sayi(d['zayif'], 0)} zayıf, {sayi(d['calismiyor'], 0)} çalışmıyor"
                + (f", {sayi(d['olculemedi'], 0)} ölçülemedi" if d["olculemedi"] else ""))
    parca = [f"{sayi(g['birim'], 0)} kural ve {sayi(s_['parite'], 0)} kural–parite bileşiminde varsayılanın hükmü, "
             f"birincil pencerede (2024 →): {sayim(s_)}. Ön kaydın istediği bütün dönemde (varsayılan için o da "
             f"örneklem dışıdır): {sayim(t_)}."]
    esik = ((u.O.get("karsi_olgu") or {}).get("olculemedi") or {}).get("esik")

    def kural_ad(b: str, h: str) -> str:
        """Kuralın adı; hükmü az işlemle verilen pariteleri varsa ("ölçülemedi" eşiğinin altı) hangi paritede ve kaç
        işlemle olduğu yanında. Eşiğin ilk sonuçlardan sonra değiştiği okura sonucuyla söylenir (o bileşimler eski
        eşikle ölçülemedi sayılırdı); değişikliğin kendisi metodoloji dersindedir."""
        bb = u.O["birim"][b]
        az = [(c, int(((bb["cift"][c].get("varsayilan") or {}).get("oos") or {}).get("n") or 0)) for c in _ciftler(bb)
              if (bb["cift"][c].get("varsayilan") or {}).get("hukum") == h]
        az = [(c, n) for c, n in az if esik and 0 < n < esik]
        if not az:
            return adlar.BIRIM[b][1]
        ns = {n for _, n in az}
        kac = (f"{'her birinde ' if len(az) > 1 else ''}{sayi(next(iter(ns)), 0)} işlem" if len(ns) == 1
               else f"en çok {sayi(max(ns), 0)} işlem")
        bu = "bu iki bileşim" if len(az) == 2 else ("bu bileşim" if len(az) == 1 else f"bu {sayi(len(az), 0)} bileşim")
        return (f"{adlar.BIRIM[b][1]} ({liste_yaz([PARITE[c] for c, _ in az])}: örneklem dışında {kac}, \"az işlem\" "
                f"işaretli; ilk sonuçlardan sonra değişen \"ölçülemedi\" eşiğinden önce {bu} ölçülemedi sayılırdı, "
                f"metodoloji dersinde)")
    for h, ad in (("calisiyor", "çalışıyor"), ("zayif", "zayıf")):
        if k[h]:
            parca.append(f"En az bir paritede {ad} (2024 →): " + ", ".join(kural_ad(b, h) for b in _butun_birimler(u)
                                                                       if b in k[h]) + ".")
    pozitif = [b for b in _butun_birimler(u)
               if (((u.O["birim"][b].get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}).get("ga_alt") is not None
               and u.O["birim"][b]["havuz"]["varsayilan"]["oos"]["ga_alt"] > 0]
    parca.append("Havuzda %95 aralığının alt ucu sıfırın üstünde kalan kural: " +
                 (", ".join(adlar.BIRIM[b][1] for b in pozitif) if pozitif else "yok") + ".")
    if s_["maliyet"] or s_["maliyet_oos"]:
        ms = maliyet_sayim(u)

        def say_(d: str) -> str:
            x = ms[d]
            return sayi(x["yayim"], 0) + (f" (büyük tekrarlı kestirimle {sayi(x['kesin'], 0)})" if x["kesin"] != x["yayim"]
                                          else "")
        def yer_(d: str, ek_: str) -> str:
            # sıfır bileşim "0 bileşimde yanıyor" değil "hiçbirinde" diye okunur (iki ölçek de sıfırsa)
            x = ms[d]
            return f"{ek_} hiçbirinde" if x["yayim"] == 0 and x["kesin"] == 0 else f"{ek_} {say_(d)} bileşimde"
        tum_, oos_ = ms["tum"], ms["oos"]
        if tum_["yayim"] or tum_["kesin"]:
            parca.append(f"Maliyet bayrağı (brüt aralığı sıfırın üstünde, net sonuç sıfır ya da altında) "
                         f"{yer_('tum', 'bütün dönemde')} yanıyor, " + yer_('oos', f"{_dis_yil(u)} → penceresinde")
                         + (" yanıyor." if (oos_["yayim"] or oos_["kesin"]) else "."))
        else:
            parca.append(f"Maliyet bayrağı (brüt aralığı sıfırın üstünde, net sonuç sıfır ya da altında) bütün dönemde "
                         f"hiçbir bileşimde yanmıyor, " + yer_('oos', f"{_dis_yil(u)} → penceresinde")
                         + (" yanıyor." if (oos_["yayim"] or oos_["kesin"]) else "."))
        sin = [(d, x) for d in ("tum", "oos") for x in ms[d]["sinirda"]]
        if sin:
            # Ayrıntı tek yerde: özet tablonun notu (blok_ders_ozet). Paragraf yalnız sayar ve atıf verir.
            parca.append(f"Bayrağın yanıp yanmadığı {sayi(len(sin), 0)} bileşimde tohum gürültüsüne bağlı (ayrıntı "
                         f"\"Bütün kurallar tek tabloda\" bölümündeki ilk tablonun notunda); sayım önceden kayıtlı "
                         f"2.000 tekrarla verilir.")
    return " ".join(parca)


GUN_UZUN = {"Pzt": "pazartesi", "Sal": "salı", "Çar": "çarşamba", "Per": "perşembe", "Cum": "cuma"}


def _gun_vekil_notu(u: Uretim, kovalar: list) -> str:
    """Haber kurallarında "haftanın günü" kovası olay türünün vekilidir: takvimin o gündeki olaylarının türlere
    dağılımı (ders_olcum.takvim_ozet → hafta_gunu). Gün takvimde yoksa boş."""
    sayim = (u.O.get("takvim") or {}).get("sayim") or {}
    parca, bas_olay = [], []
    for g in kovalar:
        g = str(g)
        dag = sorted(((o, int((v.get("hafta_gunu") or {}).get(g) or 0)) for o, v in sayim.items()), key=lambda x: -x[1])
        dag = [(o, n) for o, n in dag if n]
        if not dag:
            continue
        top = sum(n for _, n in dag)
        bas_olay.append(dag[0][0])
        parca.append(f"takvimdeki {sayi(top, 0)} {GUN_UZUN.get(g, g)} olayının "
                     + ", ".join(f"{ek(n, 'i')} {adlar.OLAY.get(o, o)}" for o, n in dag))
    if not parca:
        return ""
    ad_ = ", ".join(dict.fromkeys(adlar.OLAY.get(o, o) for o in bas_olay))
    return ("Haber kurallarında haftanın günü olay türünün vekilidir: " + "; ".join(parca) +
            f". Bu kova bir takvim etkisinden çok olayın kendisini (çoğunlukla {ad_}) ölçer; olayın kendi sonucu "
            "haber dersinin olaya göre tablosunda.")


def _stopsuz_birimler(u: Uretim) -> list[str]:
    return [bid for bid in _butun_birimler(u)
            if ((u.O["birim"][bid].get("varsayilan") or {}).get("stop_turu")) == "yok"]


def blok_stopsuz_ad(u: Uretim, ctx: dict) -> str:
    """Önceden kayıtlı varsayılanı stopsuz olan kuralların kısa adları (R'leri girişteki ATR'dir)."""
    ad = [adlar.BIRIM[b][1] for b in _stopsuz_birimler(u)]
    if not ad:
        raise SablonHatasi("stopsuz kural yok; R birimi cümlesi kurulamaz")
    return ad[0] if len(ad) == 1 else ", ".join(ad[:-1]) + " ve " + ad[-1]


def blok_hangi_kosul(u: Uretim, ctx: dict) -> str:
    """Karşılaştırma dersinin "hangi koşulda hangisi" tablosu: bütün kurallarda kontrol listesine aday olarak giren
    koşullar (en az iki paritede aynı kova seçimiyle tutan), her parite için örneklem dışı R'si ve işlem sayısıyla. Bir karar
    tablosu değildir: adayların hiçbiri hükmün öbür iki şartını (güven aralığı, rastgele yön) taşımaz."""
    govde, kural, vekil = [], 0, []
    for bid in _butun_birimler(u):
        ad_ = kosul_adaylari(u.O["birim"][bid])
        if ad_:
            kural += 1
        for x in ad_:
            if x["degisken"] == "hafta_gunu" and "haber_olay" in u.O["birim"][bid]:
                vekil += [str(k) for k in x["kova"] if str(k) not in vekil]
            govde.append([adlar.BIRIM[bid][1], bas_buyuk(_kosul_kova(x['degisken'], x['kova']).replace(", kova ", ": ")),
                          "; ".join(f"{PARITE[c]} {_hucre(k.get('oos_secilen_r'), 'ra')} ({sayi(k.get('oos_secilen_n') or 0, 0)})"
                                    for c, k in x["pariteler"])])
    if not govde:
        return "Hiçbir kuralda iki paritede aynı kova seçimiyle tutan bir koşul yok."
    return (_tablo(["Kural", "Koşul: kova", "Tutan pariteler: örneklem dışı R (işlem)"], govde, ["l", "l", "l"]) +
            f"\n\n_{sayi(len(_butun_birimler(u)), 0)} kuralın {tane(kural, 'inde')} en az bir aday var; toplam "
            f"{sayi(len(govde), 0)} aday. Aday: örneklem içinde seçilip örneklem dışında en az iki paritede aynı kova seçimiyle "
            f"tutan koşul. Şans tabanı: {blok_aday_taban(u, ctx)}._"
            + (f"\n\n_{_gun_vekil_notu(u, vekil)}_" if vekil and _gun_vekil_notu(u, vekil) else ""))


def _aday_say(u: Uretim, ters: bool) -> tuple[int, int]:
    """(aday sayısı, en az bir adayı olan kural sayısı) — gerçek ya da ters seçimle."""
    n = k = 0
    for bid in _butun_birimler(u):
        a = kosul_adaylari(u.O["birim"][bid], ters=ters)
        n += len(a)
        k += 1 if a else 0
    return n, k


def blok_turetilmis_hukum(u: Uretim, ctx: dict, birim: str) -> str:
    """Varsayılanı ön kayıtta olmayan (türetilmiş) bir kuralın iki pencerede hükmü, sayıma girdiği cümlenin sonuna
    yan cümle olarak: " (dört bileşimi iki pencerede de çalışmıyor)" ya da iki pencerenin sayımı."""
    b = (u.O.get("birim") or {}).get(birim)
    if not b:
        raise SablonHatasi(f"turetilmis_hukum: ölçümde birim yok: {birim}")
    cs = _ciftler(b)
    v = [(b["cift"][c].get("varsayilan") or {}) for c in cs]
    if cs and all((x.get("hukum") or "olculemedi") == "calismiyor" == (x.get("hukum_tum") or "olculemedi")
                  for x in v):
        return f" ({SAYI_AD.get(len(cs), sayi(len(cs), 0))} bileşimi iki pencerede de çalışmıyor)"
    return (f" (bileşimlerinin hükmü 2024 → penceresinde {hukum_sayim_yaz(b, 'hukum')}, bütün dönemde "
            f"{hukum_sayim_yaz(b, 'hukum_tum')})")


def blok_aday_taban(u: Uretim, ctx: dict) -> str:
    """Aday ölçütünün (en az iki paritede aynı kova seçimiyle tutan koşul) şans tabanı: aynı ölçüt ters seçimde kaç aday
    verir. Taban sıfırsa ölçüt şansı ayıklıyor görünür; değilse ikinci paritedeki tutuş yalnız bir gözlem ekler.
    "Kural" burada strateji demektir; aday olmanın şartı "ölçüt"tür (iki anlam aynı cümlede karışmasın)."""
    n, k = _aday_say(u, False)
    nt, kt = _aday_say(u, True)
    return (f"aynı ölçüt gerçek seçimde {sayi(k, 0)} kuralda {sayi(n, 0)} aday, **ters seçimde** (örneklem içinde "
            f"koşulsuz ortalamanın altında kalan kovalar seçilseydi) {sayi(kt, 0)} kuralda {sayi(nt, 0)} aday verir")


def blok_maliyet_ozet(u: Uretim, ctx: dict) -> str:
    """Parite parite: örneklem dışında brüt, yalnız makas ve dört kayma kademesinde net beklentisi artı olan kural
    sayısı."""
    kademe = [str(x) for x in (u.O["kunye"].get("kayma_pip") or [0.0, 0.5, 1.0, 2.0])]
    govde = []
    ayrisan = hucre = 0

    def isaret(r, pip):
        """R ile pip ortalamasının işareti ayrışıyor mu (stopu dar işlemler R'yi taşır)."""
        nonlocal ayrisan, hucre
        if r is None or pip is None:
            return
        hucre += 1
        ayrisan += 1 if ((r > 0) != (pip > 0)) else 0
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
            isaret(o.get("brut_r"), o.get("brut_pip"))
            ymo = (v.get("yalniz_makas") or {}).get("oos") or {}
            ym += 1 if (ymo.get("beklenti_r") or 0) > 0 else 0
            isaret(ymo.get("beklenti_r"), ymo.get("beklenti_pip"))
            for kk in kademe:
                mo = ((v.get("maliyet") or {}).get(kk) or {}).get("oos") or {}
                x = mo.get("beklenti_r")
                net[kk] += 1 if (x is not None and x > 0) else 0
                isaret(x, mo.get("beklenti_pip"))
        if n:
            govde.append([PARITE[c], _hucre(n, "n"), _hucre(brut, "n"), _hucre(ym, "n")] +
                         [_hucre(net[kk], "n") for kk in kademe])
    if not govde:
        return "_Maliyet ölçülmedi._"
    return (_tablo(["Parite", "Kural", "Brüt artı (R)", "Yalnız makasla artı (R)"] +
                   [f"Net artı (R), kayma {sayi(float(kk), 1)}" for kk in kademe], govde,
                   ["l"] + ["r"] * (3 + len(kademe))) +
            f"\n\n_Örneklem dışı (2024 →). Sayım işlem başına R'nin işaretinden; pip ortalamasının işareti stopu dar "
            f"işlemler yüzünden ayrışabilir (giriş dersi, R ve pip): tablonun {sayi(hucre, 0)} kural–parite–kademe "
            f"hücresinin {tane(ayrisan, 'inde')} iki işaret ayrışıyor. Kayma kademeleri dolum başına; haber "
            f"penceresindeki dolumlar her kademede ayrıca {sayi(u.O['kunye']['haber_kayma_pip'], 1)} pip öder, "
            f"\"yalnız makas\" sütununda o da sıfırdır._")


def blok_arti_rastgele_ayirt(u: Uretim, ctx: dict) -> str:
    """Örneklem dışında net artı olup yüzdeliği eşiğin üstünde kalan bileşimler, adıyla ve yüzdeliğin duyarlılığıyla.
    Tohumların %5–95'inde eşiği geçen bileşim (saglamlik: "sınırda") ayırt edilebilen sayılmaz, ayrı sayılır: eşiğin
    hangi yanında kaldığı tohuma bağlıdır."""
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    x, s_ = [], []
    for bid in _butun_birimler(u):
        for c in _ciftler(u.O["birim"][bid]):
            v = u.O["birim"][bid]["cift"][c].get("varsayilan") or {}
            r = ((v.get("rastgele") or {}).get("oos")) or {}
            net = (v.get("oos") or {}).get("beklenti_r")
            if net is None or net <= 0 or r.get("yuzdelik") is None or not math.isfinite(r["yuzdelik"]):
                continue
            if r["yuzdelik"] >= esik:
                dn = rastgele_duyarlilik_not(v).removeprefix("sınırda: ")
                ad = f"{adlar.BIRIM[bid][1]} {PARITE[c]} (yüzdelik {sayi(r['yuzdelik'], 1)}" + (f"; {dn}" if dn else "") + ")"
                sinirda = bool((((v.get("rastgele_duyarlilik") or {}).get("oos")) or {}).get("sinirda"))
                (s_ if sinirda else x).append(ad)
    parca = []
    if x:
        parca.append("Ayırt edilebilen " + ("tek bileşim" if len(x) == 1 else f"{sayi(len(x), 0)} bileşim") + ": "
                     + "; ".join(x) + ".")
    if s_:
        parca.append("Sınırda (eşiğin hangi yanında kaldığı tohuma bağlı) "
                     + ("tek bileşim" if len(s_) == 1 else f"{sayi(len(s_), 0)} bileşim") + ": " + "; ".join(s_) + ".")
    return " ".join(parca)


def blok_hukum_secim_etkisi(u: Uretim, ctx: dict) -> str:
    """Metodoloji, hüküm penceresi: varsayılanların iki penceredeki hüküm sayımı. Varsayılanı ön kayıtta olmayan
    (türetilmiş) bileşimler adıyla ayrılır ve yalnız önceden kayıtlı bileşimlerin sayımı ayrıca verilir."""
    T = ctx["T"]
    hs, ho = T["hukum_say"], T["hukum_say_onkayit"]

    def say(d: dict) -> str:
        return f"{sayi(d['calismiyor'], 0)} çalışmıyor ve {sayi(d['zayif'], 0)} zayıf"
    bas = f"varsayılanların {sayi(hs['oos']['toplam'], 0)} bileşiminde"
    if T["turetilmis_bilesim"]:
        ad = liste_yaz([adlar.BIRIM[b][1] for b in T["turetilmis_birim"]])
        bas += (f" (önceden kayıtlı {sayi(ho['oos']['toplam'], 0)}, türetilmiş {sayi(T['turetilmis_bilesim'], 0)}: "
                f"{ad} kuralının pariteleri)")
    metin = f"{bas} 2024 → hükmü {say(hs['oos'])}, bütün dönem hükmü {say(hs['tum'])}"
    if T["turetilmis_bilesim"]:
        metin += (f"; yalnız önceden kayıtlı {sayi(ho['oos']['toplam'], 0)} bileşim sayılınca 2024 → {say(ho['oos'])}, "
                  f"bütün dönem {say(ho['tum'])}")
    return metin


def blok_rastgele_tum(u: Uretim, ctx: dict) -> str:
    """Bütün dönemin rastgele yön sayımı (toplamlar → rastgele_tum): ön kayıt varsayılan için bütün dönemi örneklem dışı
    sayar ve bütün dönem hükmünün girdisi rastgele.tum'dur. Eşiği geçenler adıyla; tohum, en iyi işlem ve net sonuç."""
    T, K = ctx["T"], ctx["K"]
    rt = T["rastgele_tum"]
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    pen = f"Bütün dönemde ({tarih(K['baslangic'])} → {tarih(K['bitis'])})"
    if not rt["ust"]:
        return (f"{pen} {sayi(rt['n'], 0)} bileşimin hiçbiri eşiği geçmiyor: bu pencerede de yön seçimi yazı turadan "
                "ayırt edilemiyor.")
    grup: dict = {}
    for x in rt["ust_liste"]:
        grup.setdefault(x["birim"], []).append(x)
    adlar_ = "; ".join(adlar.BIRIM[b][1] + " " + ", ".join(
        f"{PARITE[x['cift']]} {sayi(x['yuzdelik'], 1)}" for x in xs) for b, xs in grup.items())
    cumle = [f"{pen} {sayi(rt['n'], 0)} bileşimin {tane(rt['ust'], 'i')} eşiği geçiyor ({adlar_}); şansın "
             f"beklediği yaklaşık {sayi(rt['beklenen'], 1)}."]
    if rt["binom_p"] is not None and rt["binom_p"] < 0.05:
        cumle.append(f"Bağımsızlık varsayımıyla binom p {bicimle(rt['binom_p'], 'p')}; sınamalar bağımsız olmadığı "
                     "için (aynı paritenin kuralları aynı günleri paylaşır) gerçek p bundan büyüktür.")
    else:
        cumle.append(f"Bu sayı da şansın beklediğinden ayırt edilemiyor (binom p {bicimle(rt['binom_p'], 'p')}).")
    tohum = int(K["rastgele_duyarlilik"]["tohum"])
    her = rt["her_tohum"]
    cumle.append((f"{'Hepsi' if her == rt['ust'] else bas_buyuk(ek(her, 'i'))} {sayi(tohum, 0)} sabit tohumun her "
                  f"birinde eşiği geçiyor") + (f"; en iyi işlem çıkınca {ek(rt['haric_1_ust'], 'i')} eşiğin üstünde "
                                                f"kalıyor." if rt["haric_1_ust"] != rt["ust"] else
                                                "; en iyi işlem çıkınca da hepsi eşiğin üstünde kalıyor."))
    ne = rt["net_eksi"]
    if ne:
        bn = rt["brut_arti_net_eksi"]
        kim = "Hepsinde" if ne == rt["ust"] else bas_buyuk(ek(ne, "inde"))
        if bn == ne:
            cumle.append(f"{kim} brüt sonuç artı, net sonuç eksi: bu pencerede yön bilgisi var, maliyet onu yiyor.")
        elif bn:
            cumle.append(f"{kim} net sonuç eksi; bunların {ek(bn, 'inde')} brüt sonuç artı: yön bilgisini maliyet "
                         "yiyor.")
        else:
            cumle.append(f"{kim} net sonuç eksi.")
    arti = [x for x in rt["ust_liste"] if x["net"] is not None and x["net"] > 0]
    if arti:
        cumle.append("Net sonucu artı kalan " + ("tek bileşim " if len(arti) == 1 else f"{sayi(len(arti), 0)} bileşim ")
                     + liste_yaz([f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]} ({_hucre(x['net'], 'ra')} R"
                                  + (f"; en iyi işlem çıkınca yüzdelik {sayi(x['haric_1'], 1)}"
                                     if x["haric_1"] is not None and x["haric_1"] < esik else "") + ")"
                                  for x in arti]) + ".")
    return " ".join(cumle)


def blok_rastgele_tum_istisna(u: Uretim, ctx: dict, *birimler: str) -> str:
    """Örneklem dışı rastgele yön cümlesinin (kural_iddia rastgele_yok) bütün dönem istisnası, parantez içinde: ön kayıt
    varsayılan için bütün dönemi de örneklem dışı sayar ve bütün dönem hükmünün girdisi rastgele.tum'dur. Birimlerin
    eşiği bütün dönemde geçen bileşimleri yüzdeliği ve net sonucunun işaretiyle; yoksa boş."""
    if not birimler:
        raise SablonHatasi("rastgele_tum_istisna: boş birim listesi")
    xs = [x for x in ctx["T"]["rastgele_tum"]["ust_liste"] if x["birim"] in birimler]
    if not xs:
        return ""
    ad = liste_yaz([f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]} {sayi(x['yuzdelik'], 1)}" for x in xs])
    eksi = [x for x in xs if x["net"] is not None and x["net"] < 0]
    if len(eksi) == len(xs):
        son = "ama net sonucu eksi" if len(xs) == 1 else "ama hepsinin net sonucu eksi"
    elif eksi:
        son = ("ama " + liste_yaz([f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]}" for x in eksi])
               + " net eksi")
    else:
        son = "ve net sonucu artı" if len(xs) == 1 else "ve hepsinin net sonucu artı"
    return f" (bütün dönemde {ad} yüzdelikle ayrışıyor, {son})"


def blok_rastgele_ozet(u: Uretim, ctx: dict) -> str:
    """Parite parite: rastgele yön dağılımında örneklem dışı sonucu eşiğin (≥ 95. yüzdelik) üstünde kalan kural sayısı."""
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    parca, eksi, dis, duyar = [], [], {}, []
    for c in PARITE:
        n = ust = 0
        adlar_ = []
        for bid in _butun_birimler(u):
            v = ((u.O["birim"][bid].get("cift") or {}).get(c) or {}).get("varsayilan") or {}
            r = ((v.get("rastgele") or {}).get("oos") or {})
            if r.get("yuzdelik") is None or not math.isfinite(r["yuzdelik"]):
                if v:
                    dis.setdefault(bid, []).append(f"{PARITE[c]} {sayi(int((v.get('oos') or {}).get('n') or 0), 0)}")
                continue
            n += 1
            if r["yuzdelik"] >= esik:
                ust += 1
                adlar_.append(f"{adlar.BIRIM[bid][1]} {sayi(r['yuzdelik'], 1)}")
                dn = rastgele_duyarlilik_not(v)
                if dn:
                    duyar.append(f"{adlar.BIRIM[bid][1]} {PARITE[c]}: {dn}")
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
    if duyar:
        s += (" Eşiği geçenlerin duyarlılığı (en iyi işlemler çıkarılınca yüzdelik ve sabit bir tohum listesinde eşiği "
              "geçme payı; pay %5 ile %95 arasındaysa hangi yanda kalındığı tohuma bağlıdır): " + " · ".join(duyar) + ".")
    if dis:
        s += (f" Sınama kurulmayan bileşimler (örneklem dışında {sayi(int(u.O['kunye']['uygulama_esik']['rastgele']), 0)} "
              f"işlemden az): " + "; ".join(f"{adlar.BIRIM[b_][1]} ({', '.join(x)} işlem)" for b_, x in dis.items())
              + ".")
    if eksi:
        s += (" Eşiği geçip net sonucu yine eksi kalan: " + "; ".join(eksi) + ". Rastgele yönlü işlemler de aynı "
              "makası ödediği için dağılımın ortalaması sıfırın altında kalır; o dağılımı yenmek yön seçiminin bir "
              "şey kattığını söyler, maliyeti karşıladığını söylemez.")
    return s


#: Korelasyon özetinin eşiği (|ρ| bu değer ya da daha fazla).
KOR_ESIK = 0.25


def blok_korelasyon_cumle(u: Uretim, ctx: dict, kac: str = "5") -> str:
    """Stratejiler arası günlük R korelasyonunun özeti (bütün dönem): en yüksek |ρ|'lu çiftler ve eşik sayımı."""
    kor = u.O.get("korelasyon") or {}
    if not kor.get("tum"):
        return "Korelasyon ölçülmedi."
    bs, m = kor["birimler"], kor["tum"]
    ciftler = [(abs(m[i][j]), m[i][j], bs[i], bs[j]) for i in range(len(bs)) for j in range(i + 1, len(bs))
               if m[i][j] is not None]
    ciftler.sort(key=lambda x: -x[0])
    esik = sum(1 for x in ciftler if x[0] >= KOR_ESIK)
    ust = "; ".join(f"{adlar.BIRIM[a][1]} × {adlar.BIRIM[b_][1]} {_hucre(v, 'r')}" for _, v, a, b_ in ciftler[:int(kac)])
    k_ = u.O["kunye"]
    s_ = (f"Bütün dönemde ({k_['baslangic'][:4]} → {k_['bitis'][:4]}) {sayi(len(bs), 0)} kuralın {sayi(len(ciftler), 0)} "
          f"çiftinden {tane(esik, 'inde')} günlük R korelasyonu mutlak değerce {sayi(KOR_ESIK, 2)} ya da daha "
          f"fazla. En yüksek {kac} çift: {ust}.")
    mo = kor.get("oos")
    if mo:
        n_o = sum(1 for i in range(len(bs)) for j in range(i + 1, len(bs))
                  if mo[i][j] is not None and abs(mo[i][j]) >= KOR_ESIK)
        s_ += f" Örneklem dışında ({_dis_yil(u)} →) aynı eşiği {sayi(n_o, 0)} çift geçiyor."
    return s_


def blok_korelasyon_tablo(u: Uretim, ctx: dict) -> str:
    """Günlük R korelasyonu mutlak değerce KOR_ESIK ya da fazla olan BÜTÜN çiftler (bütün dönem ya da örneklem dışı):
    figürün hücresi telefonda okunmuyor ve yalnız en güçlü çiftleri yazar; liste burada eksiksiz."""
    kor = u.O.get("korelasyon") or {}
    if not kor.get("tum"):
        return ""
    bs, m, mo = kor["birimler"], kor["tum"], kor.get("oos")
    govde = []
    for i in range(len(bs)):
        for j in range(i + 1, len(bs)):
            a, d = m[i][j], (mo[i][j] if mo else None)
            if (a is not None and abs(a) >= KOR_ESIK) or (d is not None and abs(d) >= KOR_ESIK):
                govde.append((abs(a) if a is not None else 0.0,
                              [f"{adlar.BIRIM[bs[i]][1]} × {adlar.BIRIM[bs[j]][1]}", _hucre(a, "r"), _hucre(d, "r")]))
    if not govde:
        return ""
    govde.sort(key=lambda x: -x[0])
    return ("<div class=\"sayi-tablo\">\n\n" + _tablo(["Çift", "Bütün dönem ρ", f"Örneklem dışı ρ ({_dis_yil(u)} →)"],
                                                       [g for _, g in govde], ["l", "r", "r"])
            + f"\n\n</div>\n\n_Mutlak değerce {sayi(KOR_ESIK, 2)} ya da daha fazla olan bütün çiftler (iki dönemden "
              "birinde); sıra bütün dönemin mutlak değerine göre._")


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
    # "Tuttu" ölçütü %5 düzeyli bir sınama değildir; gürültüde beklenen geçme oranını ters seçim ölçer (kova farkları
    # yalnız gürültüyse iki seçimin geçme oranı aynıdır).
    t["ters_oran"] = t["ters_tuttu"] / t["ters_sinanan"] if t["ters_sinanan"] else None
    t["gurultu_beklenen"] = t["ters_oran"] * t["sinanan"] if t["ters_oran"] is not None else None
    # Ters yön: örneklem içinde KÖTÜ görünen kovalar örneklem dışında daha sık tutuyor — kova sıralaması dönüyor.
    t["ters_ustun"] = bool(t["b"] > t["a"] and t["p"] < 0.05)
    return t


def toplamlar(O: dict, ON: dict) -> dict:
    """Karşılaştırma dersinin sayımları (bütün kural × parite bileşimleri, önceden kayıtlı varsayılan, örneklem
    dışı). Şablonun iddiaları ve koşulları bunları okur: metindeki "çoğu", "az" gibi sözcükler sayıya bağlanır."""
    esik = (ON.get("hukum") or {}).get("rastgele_esik_yuzdelik", 95)
    t = {k: 0 for k in ("bilesim", "brut_arti", "brut_arti_makas_eksi", "brut_arti_sifir_eksi", "brut_arti_net_eksi",
                        "rastgele_n", "rastgele_ust", "rastgele_ust_her_tohum", "rastgele_ust_bir_tohum",
                        "arti_n", "arti_rastgele_n", "arti_rastgele_alt", "dsr_n",
                        "dsr_ust", "dsr_gurultu_ust", "secilen_sr_arti", "calisiyor")}
    oos_ust: list[dict] = []
    for bid, b in (O.get("birim") or {}).items():
        for c, v in (b.get("cift") or {}).items():
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
                if r["yuzdelik"] >= esik:
                    # Örneklem dışında eşiği geçen bileşimler adıyla (net ve brüt sonuçlarıyla): yön seçiminin değeri
                    # ayırt edilebildiği yerde maliyeti karşılıyor mu, istisnasıyla.
                    oos_ust.append({"birim": bid, "cift": c, "yuzdelik": r["yuzdelik"], "net": net, "brut": brut})
                # Tohuma göre aralık: sabit tohum listesinin hepsinde ya da en az birinde eşiği geçen bileşim. Tohum
                # sınaması yalnız yüzdeliği saglamlik.DUYARLILIK_TABAN'ın üstündeki bileşimde koşar; altındaki bileşim
                # iki sayımda da geçmeyen sayılır.
                dy = ((va.get("rastgele_duyarlilik") or {}).get("oos")) or {}
                if dy.get("tohum_min") is not None:
                    t["rastgele_ust_her_tohum"] += dy["tohum_min"] >= esik
                    t["rastgele_ust_bir_tohum"] += dy["tohum_max"] >= esik
                elif r["yuzdelik"] >= esik:
                    raise SablonHatasi("eşiği geçen bileşimin tohum duyarlılığı ölçülmemiş")
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
    # Örneklem dışında eşiği geçenler derslerin kural sırasıyla, parite sırası künyenin.
    sira_b = [x for bl in adlar.DERS_BIRIM.values() for x in bl]
    sira_c = list((O.get("kunye") or {}).get("ciftler") or [])
    t["rastgele_oos_liste"] = sorted(oos_ust, key=lambda x: (sira_b.index(x["birim"]) if x["birim"] in sira_b
                                                             else len(sira_b), x["birim"],
                                                             sira_c.index(x["cift"]) if x["cift"] in sira_c
                                                             else len(sira_c)))
    # Izgaradan seçimin kurulduğu bileşimler (seçim örneklem içinde asgari işlem ister; kurulamayan bileşimin seçilen
    # sütunu boştur).
    t["secilen_n"] = int(sum(1 for b in (O.get("birim") or {}).values() for v in (b.get("cift") or {}).values()
                             if v.get("secilen_p")))
    t["secimsiz"] = t["bilesim"] - t["secilen_n"]
    # Varsayılanların hüküm sayımı iki pencerede (bütün bileşimler; işlemsiz olan "ölçülemedi"). Varsayılanı ön
    # kayıtta olmayan (türetilmiş: adlar.turetilmis) birimler ayrıca sayılır: "önceden kayıtlı varsayılanlar" yalnız ön
    # kaydın kendi varsayılanlarıdır.
    hs: dict = {"oos": {}, "tum": {}}
    hs_on: dict = {"oos": {}, "tum": {}}
    t["turetilmis_bilesim"] = 0
    t["turetilmis_birim"] = []
    for bid, b in (O.get("birim") or {}).items():
        tur = adlar.turetilmis(b)
        if tur and (b.get("cift") or {}):
            t["turetilmis_birim"].append(bid)
        for v in (b.get("cift") or {}).values():
            va = v.get("varsayilan") or {}
            t["turetilmis_bilesim"] += bool(tur)
            for d, alan in (("oos", "hukum"), ("tum", "hukum_tum")):
                h = va.get(alan) or "olculemedi"
                hs[d][h] = hs[d].get(h, 0) + 1
                if not tur:
                    hs_on[d][h] = hs_on[d].get(h, 0) + 1

    def _say(h_):
        return {d: {**{h: int(h_[d].get(h, 0)) for h in ("calisiyor", "zayif", "calismiyor", "olculemedi")},
                    "toplam": int(sum(h_[d].values()))} for d in h_}
    t["hukum_say"] = _say(hs)
    t["hukum_say_onkayit"] = _say(hs_on)
    # Bütün dönemin rastgele yön sayımı (ön kayıt varsayılan için bütün dönemi örneklem dışı sayar; bütün dönem
    # hükmünün girdisi rastgele.tum'dur): eşiği geçen bileşimler adıyla, tohum duyarlılığı, en iyi işlem hariç ve net
    # sonuç.
    rt: dict = {"n": 0, "ust": []}
    for bid in [x for bl in adlar.DERS_BIRIM.values() for x in bl if x in (O.get("birim") or {})] + \
            [x for x in (O.get("birim") or {}) if x not in {y for bl in adlar.DERS_BIRIM.values() for y in bl}]:
        b = O["birim"][bid]
        for c in [x for x in (O.get("kunye") or {}).get("ciftler") or [] if x in (b.get("cift") or {})]:
            va = b["cift"][c].get("varsayilan") or {}
            r = ((va.get("rastgele") or {}).get("tum")) or {}
            if r.get("yuzdelik") is None or not math.isfinite(r["yuzdelik"]):
                continue
            rt["n"] += 1
            if r["yuzdelik"] >= esik:
                dy = ((va.get("rastgele_duyarlilik") or {}).get("tum")) or {}
                if dy.get("tohum_min") is None:
                    raise SablonHatasi("bütün dönemde eşiği geçen bileşimin tohum duyarlılığı ölçülmemiş")
                tm = va.get("tum") or {}
                rt["ust"].append({"birim": bid, "cift": c, "yuzdelik": r["yuzdelik"],
                                  "her_tohum": dy["tohum_min"] >= esik, "haric_1": dy.get("haric_1"),
                                  "net": tm.get("beklenti_r"), "brut": tm.get("brut_r")})
    u_ = rt["ust"]
    t["rastgele_tum"] = {
        "n": rt["n"], "ust": len(u_), "ust_liste": u_,
        "beklenen": rt["n"] * (100 - esik) / 100,
        "binom_p": _binom_ust_p(len(u_), rt["n"], (100 - esik) / 100),
        "her_tohum": sum(1 for x in u_ if x["her_tohum"]),
        "haric_1_ust": sum(1 for x in u_ if x["haric_1"] is not None and x["haric_1"] >= esik),
        "net_eksi": sum(1 for x in u_ if x["net"] is not None and x["net"] <= 0),
        "brut_arti_net_eksi": sum(1 for x in u_ if x["net"] is not None and x["net"] <= 0
                                  and x["brut"] is not None and x["brut"] > 0)}

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
              "secilen_sr_eksi": t["dsr_n"] - t["secilen_sr_arti"],
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
    s1 = (f"Örneklem içinde seçilen kovalar {sayi(t['sinanan'], 0)} sınamanın {tane(t['tuttu'], 'inde')} "
          f"({yuzde(t['tuttu'] / t['sinanan'], 0)}) örneklem dışı ölçütü geçti.")
    if not t["ters_sinanan"]:
        return s1 + " Ters seçim bu ölçümde yok."
    s2 = (f" Örneklem içinde ortalamanın altında kalan kovalar seçilseydi aynı ölçüt {sayi(t['ters_sinanan'], 0)} sınamanın "
          f"{tane(t['ters_tuttu'], 'inde')} ({yuzde(t['ters_tuttu'] / t['ters_sinanan'], 0)}) geçerdi. "
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
    sn = ((oos.get("sinir") or {}).get("ga_alt" if r > 0 else "ga_ust")) or {}
    if sn.get("sinirda") and ((r > 0 and alt is not None and alt > 0) or (r <= 0 and ust is not None and ust < 0)):
        uc_ = "alt" if r > 0 else "üst"
        s = (f"Havuzun örneklem dışı ortalaması sıfırın {'üstünde' if r > 0 else 'altında'} ve aralığının {uc_} ucu "
             f"sıfırda: {_sinir_cumle(sn)}. "
             + ("Kenar bu örneklem büyüklüğünde şanstan güvenle ayırt edilemiyor." if r > 0 else
                "Kayıp şanstan güvenle ayırt edilemiyor; bir kenar yok."))
    elif r > 0 and alt is not None and alt > 0:
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
    for t, x in (b.get("tf_bos") or {}).items():
        s += (f" {t} dakikalık mumda kural hiçbir paritede, iki dönemde de işlem açmadı"
              + (f": {x['neden']}." if x.get("neden") else "."))
    if esleme:
        s += (" 60 dakikalık mumda ilk denge penceresi mumun kendisidir (\"tek mum\" ile \"60 dk\" aynı penceredir); "
              "kıyas o satırla yapıldı.")
    hk = {c: b["cift"][c].get("tf_haber_kaymasiz") or {} for c in _ciftler(b)}
    if any(hk.values()):
        c0 = ana()
        x = hk.get(c0) or {}
        pay = " · ".join(f"{k} dk {yuzde(v.get('haber_payi') or 0, 0)}" for k, v in sorted(x.items(), key=lambda kv: int(kv[0])))
        r = " · ".join(f"{k} dk {_hucre(v.get('oos'), 'ra')}" for k, v in sorted(x.items(), key=lambda kv: int(kv[0])))
        hp = u.O["kunye"]["haber_pencere_dk"]
        s += (f" Haber kayması olaydan {sayi(-int(hp[0]), 0)} dakika önce ile {sayi(int(hp[1]), 0)} dakika sonrası "
              f"arasındaki dolumlara uygulanır; girişlerin haber penceresinde olma payı {PARITE[c0]}'de {pay}. Haber "
              f"kayması sıfırken {PARITE[c0]}'de örneklem dışı net R: {r}.")
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


def _komsu_tablosu(u: Uretim, b: dict, c: str) -> tuple[str, str] | None:
    """Bir paritede seçilenin tek parametre komşuları (ders_olcum.komsular): her serbest parametrenin değerleri, öbür
    parametreler seçilende. (tablo, okuma cümlesi); seçim yoksa None."""
    k = (b["cift"][c].get("komsular") or {})
    if not k or not k.get("parametre"):
        return None
    aile = b.get("aile") or ""
    govde, kopya, tanimsiz = [], False, []
    komsu, arti_is, arti_oos = 0, 0, 0
    for pa, x in k["parametre"].items():
        for i, s in enumerate(x.get("satir") or []):
            d = s.get("deger")
            ad = (_deger_yaz(d, pa, aile) if pa in ("stop_yeri", "hedef") else
                  _komb_deger(pa, d if pa not in ("k", "geri_cekilme") else float(d), aile))
            if s.get("kopya"):
                ad += " †"
                kopya = True
            is_, oos = s.get("is") or {}, s.get("oos") or {}
            hucre = ([_hucre(is_.get("beklenti_r"), "ra"), _hucre(is_.get("n"), "n"), _hucre(oos.get("beklenti_r"), "ra"),
                      _hucre(oos.get("n"), "n")] if not s.get("bos") else ["işlem yok", "—", "—", "—"])
            ad_p = bas_buyuk(adlar.param_ad(pa, aile)) if i == 0 else ""
            govde.append([ad_p, f"**{ad}** (seçilen)" if s.get("secilen") else ad] + hucre)
            if not s.get("secilen") and not s.get("bos"):
                komsu += 1
                arti_is += int((is_.get("beklenti_r") or 0) > 0)
                arti_oos += int((oos.get("beklenti_r") or 0) > 0)
        if x.get("tanimsiz"):
            tanimsiz.append(adlar.param_ad(pa, aile))
    if not govde:
        return None
    K = u.O.get("kunye") or {}
    ic = f"{str(K.get('baslangic'))[:4]}–{str(K.get('ic_bitis'))[:4]}"
    tablo = _tablo(["Parametre", "Değer", "İçi R", "İçi işlem", "Dışı R", "Dışı işlem"], govde,
                   ["l", "l", "r", "r", "r", "r"])
    dip = [f"İçi: örneklem içi ({ic}); dışı: 2024 →. Net R işlem başına; her satırda yalnız o parametre değişir, "
           f"öbürleri seçilen değerlerindedir."]
    if kopya:
        dip.append("†: bu değer ızgarada başka bir kombinasyonla aynı işlemleri üretir.")
    if tanimsiz:
        dip.append("Seçilenle birlikte tanımsız olan değerler satırda yok (" + ", ".join(tanimsiz) + ").")
    if komsu:
        def _pencere(k: int) -> str:
            return ("hiçbiri net artı değil" if not k else "hepsi net artı" if k == komsu and komsu > 1 else
                    f"{tane(k, 'i')} net artı")
        okuma = (f"{PARITE[c]}'de seçilenin {sayi(komsu, 0)} tek adımlık komşusu var: örneklem içinde "
                 f"{_pencere(arti_is)}, örneklem dışında {_pencere(arti_oos)}.")
    else:
        okuma = f"{PARITE[c]}'de seçilenin tek adımlık komşusu yok: ızgaranın bu kesitinde seçilen tek başına durur."
    return ("\n".join(["<details>", f"<summary>Seçilenin çevresi — {PARITE[c]}: tek parametre komşuları</summary>", "",
                       '<div class="sayi-tablo">', "", tablo, "", "</div>", "", "_" + " ".join(dip) + "_", "",
                       "</details>"]), okuma)


def blok_komsular(u: Uretim, ctx: dict) -> str:
    """Seçilen kombinasyonun çevresi (ısı haritası iki boyutluk bir kesittir ve seçilen çoğu zaman o kesitte değildir):
    ana parite ve örneklem dışında artı kalan pariteler için tek parametre komşuları, katlanır tabloyla; okuma
    cümlesi komşuların kaçının iki örneklemde artı olduğunu sayar."""
    b = ctx["B"]
    cs = [ana()] + [c for c in _arti_pariteler(b) if c != ana()]
    parca, okuma = [], []
    for c in cs:
        if c not in (b.get("cift") or {}):
            continue
        t = _komsu_tablosu(u, b, c)
        if t:
            parca.append(t[0])
            okuma.append(t[1])
    if not parca:
        return ""
    return " ".join(okuma) + "\n\n" + "\n\n".join(parca)


def _saat_araligi(h: int) -> str:
    return f"{h:02d}:00–{h:02d}:59 TSİ"


def blok_saat_okuma(u: Uretim, ctx: dict, cift: str = "") -> str:
    """Giriş saati figürünün okunuşu (ana parite, bütün dönem): en az ön kaydın kova eşiği kadar (30) işlemli saatler.
    Kovalar giriş anının TSİ
    saatidir (18 → 18:00–18:59). Tek bir yerel saatte giren kurallarda kova iki tanedir ve ikisi yaz/kış saatidir;
    tanım `adlar.mevsim_kovalari`, giriş saati figürü de onu okur."""
    cift = cift or ana()
    esik = int(u.ON["kosul"]["asgari_kova_islem"])     # bir kova bu sayıyla okunur; figür aynı eşiği soluk çizer
    v = (((ctx["B"].get("cift") or {}).get(cift) or {}).get("varsayilan")) or {}
    st = {int(h): x for h, x in (v.get("saat_tsi") or {}).items() if (x.get("n") or 0) >= esik}
    bas = f"{PARITE[cift]}'de, bütün dönemde"
    if not st:
        return (f"{bas} hiçbir giriş saatinde en az {esik} işlem yok: figürdeki çubuklar betimleyicidir, saat okuması "
                f"kurulmaz.")
    yaz = lambda h: f"{_saat_araligi(h)} ({_hucre(st[h]['beklenti_r'], 'ra')} R, {sayi(st[h]['n'], 0)} işlem)"
    if len(st) == 1:
        h = next(iter(st))
        return f"{bas} yalnız bir giriş saatinde en az {esik} işlem var: {yaz(h)}."
    arti = [h for h in sorted(st) if st[h]["beklenti_r"] > 0]
    if len(st) == 2:
        mevsim = adlar.mevsim_kovalari(v.get("saat_tsi") or {})
        h1, h2 = mevsim if mevsim and set(mevsim) == set(st) else sorted(st)
        isaret_ = ("ikisi de artı" if len(arti) == 2 else "ikisi de eksi" if not arti else
                   f"yalnız {_saat_araligi(arti[0])} artı")
        if mevsim and set(mevsim) == set(st):
            return (f"{bas} giriş iki saate düşer, çünkü kural tek bir yerel saatte girer ve o saatin TSİ karşılığı "
                    f"yaz ve kış saatinde bir saat kayar: yaz saatinde {yaz(h1)}, kış saatinde {yaz(h2)}; {isaret_}. "
                    f"İki kova bir giriş saati seçimi değil, mevsimin kıyasıdır.")
        return f"{bas} en az {esik} işlemli iki giriş saati var: {yaz(h1)} ve {yaz(h2)}; {isaret_}."
    en = max(st, key=lambda h: st[h]["beklenti_r"])
    ek_ = min(st, key=lambda h: st[h]["beklenti_r"])
    say = (f"{sayi(len(st), 0)} saatin hiçbirinde sonuç artı değil" if not arti else
           f"{sayi(len(st), 0)} saatin hepsinde artı" if len(arti) == len(st) else
           f"{sayi(len(st), 0)} saatin {tane(len(arti), 'inde')} artı")
    return (f"{bas} ve en az {esik} işlemli saatlerde: en iyi giriş saati {yaz(en)}, en kötüsü {yaz(ek_)}; {say}. "
            f"Saat kovaları ayrı birer sınamadır; en iyi saat şansla da en iyi çıkar.")


def blok_kuyruk(u: Uretim, ctx: dict) -> str:
    """Ortalama R'nin kuyruğa duyarlılığı (betimleyici; hükmü değiştirmez): örneklem dışı ortalama, en iyi bir ve üç
    işlem çıkarılınca, ve beklenen maliyeti riskin yarısını aşan işlemler çıkarılınca."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        k = (((b["cift"][c].get("varsayilan") or {}).get("kuyruk")) or {}).get("oos") or {}
        if not k.get("n") or k.get("r") is None:
            continue
        pah = k.get("r_pahali_haric")
        en_iyi = (f"{_hucre(k.get('en_iyi_r'), 'ra')} ({_pip(round(k.get('en_iyi_R_pip') or 0, 2))} pip risk)"
                  if (k.get("en_iyi_esit") or 1) == 1 else
                  f"{_hucre(k.get('en_iyi_r'), 'ra')} ({sayi(k['en_iyi_esit'], 0)} eşit işlem; risk "
                  f"{_pip(round(k['en_iyi_R_pip_alt'], 2))}–{_pip(round(k['en_iyi_R_pip_ust'], 2))} pip)")
        npah = k.get("n_pahali")
        if pah is None or not math.isfinite(pah) or npah is None:
            pah_ = "—"
        elif npah == 0:
            pah_ = f"{_hucre(pah, 'ra')} (çıkarılan işlem yok)"
        else:
            pah_ = f"{_hucre(pah, 'ra')} ({sayi(npah, 0)} işlem çıkarıldı, {yuzde(k.get('pay_pahali') or 0, 1)})"
        govde.append([PARITE[c], _hucre(k["r"], "ra"), _hucre(k.get("r_tek_haric"), "ra"),
                      _hucre(k.get("r_uc_haric"), "ra"), pah_, en_iyi])
    if not govde:
        return ""
    # Seçilenin kuyruğu yalnız artı hükümlülerde basılır (blok_secim); gönderme yalnız o satır varsa kurulur.
    sec_kuy = any((b["cift"][c].get("secilen") or {}).get("hukum") in ("zayif", "calisiyor")
                  and (((b["cift"][c].get("secilen") or {}).get("kuyruk") or {}).get("oos") or {}).get("r") is not None
                  for c in _ciftler(b))
    return (_tablo(["Parite", "Net R", "En iyi işlem hariç", "En iyi üç hariç", "Maliyeti riskin yarısını aşanlar hariç",
                    "En iyi işlem"], govde, ["l", "r", "r", "r", "r", "r"]) +
            f"\n\n_{bas_buyuk(adlar.varsayilan_ad(b))}, örneklem dışı (2024 →), işlem başına net R"
            + (" (artı hükümlü seçilenlerin kuyruğu seçim tablosunun altında)" if sec_kuy else "")
            + ". Beklenen maliyet: girişteki makas, iki dolumun temel "
            "kayması ve giriş haber penceresindeyse haber kayması. Betimleyicidir; hüküm değişmez._")


def blok_varyant(u: Uretim, ctx: dict, param: str, dipnot: bool = True) -> str:
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
        # Tablonun başlığı parametrenin adıdır: hücre yalnız değeri taşır ("stop yeri karşı uç" değil "karşı uç").
        ad = (_deger_yaz(d, param, b.get("aile") or "") if param in ("stop_yeri", "hedef") else
              _komb_deger(param, d if param not in ("k", "geri_cekilme") else float(d), b.get("aile") or ""))
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
            ("\n\n_Hücre: örneklem içi · örneklem dışı net R (parantezde örneklem dışı işlem sayısı); öbür parametreler "
             f"{adlar.varsayilan_ad(b)}da._" if dipnot else ""))


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


def blok_stop_cikis(u: Uretim, ctx: dict) -> str:
    """Stopla çıkan işlemlerin net R dağılımı, çıkış türüne göre (ölçüm: stop_cikis — kaydedilmiş bütün işlemler, her
    kuralın her paritedeki varsayılanı ve seçileni, bütün dönem)."""
    s = u.O.get("stop_cikis") or {}
    ad = {"stop": "sert stopla", "bosluk_stop": "boşlukla stopla", "kapanis_stop": "kapanış stopuyla"}
    parca = []
    for k in ("stop", "bosluk_stop", "kapanis_stop"):
        x = s.get(k) or {}
        if not x.get("n"):
            continue
        p_ = (f"{ad[k]} çıkan {sayi(x['n'], 0)} işlemin medyanı {_hucre(x['medyan'], 'ra')} R, en kötüsü "
              f"{_hucre(x['en_kotu'], 'ra')} R")
        if x.get("pay_2r"):
            p_ += f", {yuzde_ek(x['pay_2r'], 'i')} −2 R'nin ötesinde"
        parca.append(p_)
    if not parca:
        raise SablonHatasi("stop çıkışları ölçülmedi")
    return ("Kaydedilmiş işlemlerde (her kuralın her paritedeki varsayılanı ve seçileni, bütün dönem) "
            + "; ".join(parca) + ".")


def blok_alinmayan(u: Uretim, ctx: dict) -> str:
    """Varsayılanın emirlerinden kaçının işleme dönüştüğü ve alınmayanların sebebi (ölçüm: birim → durum), bütün dönem,
    bütün pariteler. Sayısı sıfır olan sebep yazılmaz."""
    d = ctx["B"].get("durum") or {}
    if not d.get("toplam"):
        return ""
    sebep = [("pozisyon_acik", "açık bir pozisyon yüzünden"),
             ("risk_gecersiz", "giriş dakikasında fiyat stopun ötesinde ya da tam üstünde açıldığı için"),
             ("hedef_gecersiz", "yürütülen giriş seviye hedefine vardığı ya da onu geçtiği için"),
             ("veri_yok", "giriş dakikasının verisi olmadığı için"),
             ("gun_sonu", "giriş gün sonundan sonraya düştüğü için")]
    parca = [f"{ek(d[k], 'i')} {ad}" for k, ad in sebep if d.get(k)]
    if not parca:
        cumle = (f"**Alınmayan emirler.** Varsayılanın {sayi(d['toplam'], 0)} emrinin hepsi işleme dönüştü (bütün "
                 f"dönem, bütün pariteler).")
    else:
        cumle = (f"**Alınmayan emirler.** Varsayılanın {sayi(d['toplam'], 0)} emrinin {ek(d['alindi'], 'i')} işleme "
                 f"dönüştü; " + ", ".join(parca) + " alınmadı (bütün dönem, bütün pariteler). Alınmayan emir "
                 "örneklemden çıkar: sonuç yalnız alınan işlemlerden.")
    return cumle + _alinmayan_tablo(ctx["B"], sebep)


SEBEP_KISA = {"pozisyon_acik": "Açık pozisyon", "risk_gecersiz": "Stopta ya da ötesinde açılış",
              "hedef_gecersiz": "Hedefte ya da ötesinde giriş", "veri_yok": "Veri yok", "gun_sonu": "Gün sonundan sonra"}
SEBEP_TANIM = {"pozisyon_acik": "aynı paritede açık bir pozisyon var",
               "risk_gecersiz": "giriş dakikasında fiyat stopun ötesinde ya da tam üstünde",
               "hedef_gecersiz": "yürütülen giriş (kayma dahil) seviye hedefine varmış ya da onu geçmiş",
               "veri_yok": "giriş dakikasının verisi yok",
               "gun_sonu": "giriş gün sonu çıkışına ya da sonrasına düşüyor"}


def _alinmayan_tablo(b: dict, sebep: list) -> str:
    """Parite parite, varsayılan ve seçilen ayrı: emir, işlem ve alınmayanların sebebi (bütün dönem; ölçüm:
    durum_parite). Hiçbir satırda görünmeyen sebep sütunu yazılmaz; seçilen varsayılanla aynıysa satır öyle adlanır.
    Bir sebebi hiç olmayan birimde (hepsi alındı) tablo basılmaz."""
    dp = b.get("durum_parite") or {}
    satirlar = []
    for c in _ciftler(b):
        for kim in ("varsayilan", "secilen"):
            x = (dp.get(c) or {}).get(kim) or {}
            if not x.get("toplam"):
                continue
            ad = KIM_AD[kim]
            if kim == "secilen" and b["cift"][c].get("secilen_p") == b.get("varsayilan"):
                ad = "seçilen (varsayılanla aynı)"
            satirlar.append((c, ad, x))
    sutun = [k for k, _ in sebep if any(x.get(k) for _, _, x in satirlar)]
    if not satirlar or not sutun:
        return ""
    govde = [[PARITE[c], ad, _hucre(x["toplam"], "n"), _hucre(x.get("alindi") or 0, "n")]
             + [_hucre(x.get(k) or 0, "n") for k in sutun] for c, ad, x in satirlar]
    # MDX: <details> ile <summary> ayrı satırda durur; aynı satırda metinle başlayan bir etiket paragrafın içinde
    # kalır ve kapanış etiketini o paragrafta arar (derleme düşer).
    return ("\n\n<details>\n<summary>Alınmayan emirler parite parite: varsayılan ve seçilen</summary>\n\n"
            "<div class=\"sayi-tablo\">\n\n"
            + _tablo(["Parite", "Kural", "Emir", "İşlem"] + [SEBEP_KISA[k] for k in sutun], govde,
                     ["l", "l"] + ["r"] * (2 + len(sutun)))
            + "\n\n</div>\n\n_Bütün dönem. " + "; ".join(f"{SEBEP_KISA[k]}: {SEBEP_TANIM[k]}" for k in sutun)
            + "._\n\n</details>")


def blok_secimsiz(u: Uretim, ctx: dict, ayrinti: str = "") -> str:
    """Izgaradan seçimin kurulamadığı bileşimler, kural kural: "N4 başarısız (GBP/USD, AUD/USD)". ayrinti="n":
    paritenin en kalabalık kombinasyonunun örneklem içi işlem sayısıyla ("GBP/USD, en kalabalığı 29 işlem")."""
    parca = []
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        yok = [c for c in _ciftler(b) if not b["cift"][c].get("secilen_p")]
        if yok and ayrinti == "n":
            ns = [(b["cift"][c].get("izgara_ozet") or {}).get("is_azami_n") for c in yok]
            if None not in ns and len(set(ns)) == 1:
                kim = "" if len(yok) == 1 else ("ikisinde de " if len(yok) == 2 else "hepsinde ")
                parca.append(f"{adlar.BIRIM[bid][1]}, {liste_yaz([PARITE[c] for c in yok])} ({kim}en kalabalık "
                             f"kombinasyon örneklem içinde {sayi(int(ns[0]), 0)} işlem)")
            else:
                parca.append(f"{adlar.BIRIM[bid][1]}, " + "; ".join(
                    f"{PARITE[c]}" + (f" (en kalabalık kombinasyon örneklem içinde {sayi(int(n), 0)} işlem)"
                                      if n is not None else "") for c, n in zip(yok, ns)))
        elif yok:
            parca.append(f"{adlar.BIRIM[bid][1]} ({liste_yaz([PARITE[c] for c in yok])})")
    if not parca:
        raise SablonHatasi("seçimsiz bileşim yok; cümle kurulmamalı")
    return liste_yaz(parca)


def _secim_kapsam(b: dict) -> str:
    """"her paritede" ya da seçimin kurulamadığı pariteler varsa "GBP/USD ve AUD/USD dışında her paritede"."""
    yok = [c for c in _ciftler(b) if not (b["cift"][c].get("secilen_p"))]
    if not yok:
        return "her paritede"
    if len(yok) == len(_ciftler(b)):
        return "hiçbir paritede seçim kurulamadı; kurulsaydı"
    return f"{liste_yaz([PARITE[c] for c in yok])} dışında her paritede"


def blok_sonuclar(u: Uretim, ctx: dict) -> str:
    """Bir stratejinin standart sonuç dizisi: aynı düzen her stratejide, böylece stratejiler yan yana okunur. Tanımlar
    giriş dersindedir; burada yalnız sayılar ve sayıların okunuşu. Yorum bu dizinin ARKASINA strateji şablonunda
    yazılır."""
    b = ctx["B"]
    k = u.O["kunye"]
    kisa = adlar.BIRIM[ctx["BID"]][1]
    va = adlar.varsayilan_ad(b)
    p = [f"**Birikimli sonuç.** {bas_buyuk(va)}ın {len(_ciftler(b))} paritede ve havuzda birikimli net R'si; "
         f"örneklem içi ({k['baslangic'][:4]}–{k['ic_bitis'][:4]}) soluk, örneklem dışı ({tarih(k['dis_baslangic'])} →) "
         f"koyu çizgi.",
         "", blok_sekil(u, ctx, "egri", f"Birikimli net R ve düşüş — {kisa}"), "", blok_oos_cumle(u, ctx), "",
         blok_sonuc(u, ctx, "oos"), "",
         f"_{bas_buyuk(va)}, örneklem dışı. Net: gerçek makas ve dolum başına "
         f"{sayi(k['temel_kayma_pip'], 1)} pip kayma (haber penceresinde ayrıca {sayi(k['haber_kayma_pip'], 1)} pip). "
         f"Havuz: aynı kural bütün paritelerde birlikte; Sharpe havuzda günlük R toplamından; pip satırı havuzda boş "
         f"(pariteler arası pip toplanamaz)._", "",
         blok_havuz_cumle(u, ctx), "",
         f"**Bütün dönem.** Varsayılan veriye bakmadan seçildiği için bütün dönem de ({k['baslangic'][:4]} → "
         f"{k['bitis'][:4]}) onun örneklem dışıdır; hüküm {k['dis_baslangic'][:4]} → penceresinden verilir, bütün dönemin "
         f"hükmü burada.", "",
         blok_sonuc_tum(u, ctx), "",
         "**İşlemlerin anatomisi** (örneklem dışı).", "", blok_ayrinti(u, ctx, "oos"), "", blok_alinmayan(u, ctx), "",
         f"**Mum uzunluğu.** Aynı kural 5, 15 ve 60 dakikalık mumlarla; öbür parametreler {va}da.",
         "", blok_sekil(u, ctx, "tf", f"Zaman dilimi kıyası — {kisa}"), "", blok_tf_okuma(u, ctx), "",
         f"**Izgara ve seçim.** Izgaranın bütün kombinasyonları örneklem içinde ({k['baslangic'][:4]}–"
         f"{k['ic_bitis'][:4]}) denendi; {_secim_kapsam(b)} en yüksek örneklem içi Sharpe'lı kombinasyon seçildi ve "
         f"örneklem dışında sınandı.", "",
         blok_sekil(u, ctx, "izgara", f"Parametre ızgarası — {kisa}"), "", blok_izgara_okuma(u, ctx), "",
         blok_izgara_arti(u, ctx),
         blok_secim(u, ctx), "", blok_komsular(u, ctx), "", blok_dsr_cumle(u, ctx), "", blok_wf_cumle(u, ctx), "", blok_wf(u, ctx), "",
         blok_stop_hedef(u, ctx),
         "**Maliyet.**", "", blok_maliyet(u, ctx), "",
         "**Kuyruk.** R ortalaması her işlemi riskine göre ölçekler; riski küçük tek bir işlem ortalamayı taşıyabilir.",
         "", blok_kuyruk(u, ctx), "",
         "**Yön mü, zamanlama mı?** " + blok_rastgele_cumle(u, ctx), "",
         "**Rejim ve saat.** " + blok_rejim_cumle(u, ctx), "", blok_rejim(u, ctx), "",
         blok_sekil(u, ctx, "saat", f"Giriş saatine göre — {kisa}"), "", blok_saat_okuma(u, ctx), ""]
    return "\n".join(p)


def blok_izgara_arti(u: Uretim, ctx: dict) -> str:
    """Ana paritenin dışında örneklem dışı artı kalan paritelerin ızgarası (aynı dilim; figür sekil.izgara, dosya adı
    paritesiyle). Böyle parite yoksa boş."""
    b = ctx["B"]
    kisa = adlar.BIRIM[ctx["BID"]][1]
    parca = []
    for c in [c for c in _arti_pariteler(b) if c != ana()]:
        v = b["cift"][c].get("varsayilan") or {}
        parca += [f"Örneklem dışında artı kalan {PARITE[c]} (hüküm {adlar.HUKUM.get(v.get('hukum') or 'olculemedi')}, "
                  f"{_hucre((v.get('oos') or {}).get('beklenti_r'), 'ra')} R) için aynı ızgara:", "",
                  blok_sekil(u, ctx, f"{ctx['BID']}-izgara-{c.lower()}", f"Parametre ızgarası — {kisa}, {PARITE[c]}"),
                  ""]
    return "\n".join(parca)


STOP_HEDEF = ("stop_turu", "stop_yeri", "hedef")


def blok_stop_hedef(u: Uretim, ctx: dict) -> str:
    """Izgaranın stop türü, stop yeri ve hedef boyutları tek tek (öbür parametreler önceden kayıtlı varsayılanda):
    sert mi kapanış stopu mu, karşı uç mu orta mı, 1R mi gün sonu mu sorusunun ızgaradaki cevabı. Izgarada tek
    değerli boyut tablo almaz. Boş dönerse dizi bir boş satır bile eklemez."""
    b = ctx["B"]
    var = [p for p in STOP_HEDEF if any(((b["cift"][c].get("varyant") or {}).get(p)) for c in _ciftler(b))]
    if not var:
        return ""
    p = [f"**Stop ve hedef.** Izgaranın stop ve hedef boyutları tek tek; öbür parametreler "
         f"{adlar.varsayilan_ad(b)}da. Bunlar seçim değil karşılaştırmadır: örneklem dışı sütundan en iyi satırı "
         "seçmek, ızgaradan seçimin örneklem içinde yaptığını örneklem dışında yapmaktır.", ""]
    for i, x in enumerate(var):
        p += [blok_varyant(u, ctx, x, dipnot=(i == len(var) - 1)), ""]
    return "\n".join(p) + "\n"


def blok_kosullar(u: Uretim, ctx: dict) -> str:
    """Koşul analizi dizisi: figür (ana parite), tutan/tutmayan özeti, en az bir paritede tutan değişkenlerin dört
    paritedeki durumu (kovasıyla)."""
    b = ctx["B"]
    kisa = adlar.BIRIM[ctx["BID"]][1]
    p = [blok_sekil(u, ctx, "kosul", f"Koşul kovaları — {kisa}"), "", blok_kosul_ozet(u, ctx), ""]
    kt = blok_kova_tablo(u, ctx)
    if kt:
        p += [kt, ""]
    # Örneklem dışında artı kalan (ya da hükmü zayıf/çalışıyor olan) öbür paritelerde de aynı ayrıntı: okurun ilk
    # bakacağı yer orasıdır ve sonucun hangi kovada toplandığı ana paritenin figüründen okunmaz.
    arti = _arti_pariteler(b)
    for c in [x for x in _ciftler(b) if x != ana() and x in arti]:
        v = b["cift"][c].get("varsayilan") or {}
        p += [f"Örneklem dışında artı kalan {PARITE[c]} (hüküm {adlar.HUKUM.get(v.get('hukum'), '—')}, "
              f"{_hucre((v.get('oos') or {}).get('beklenti_r'), 'ra')} R) için aynı ayrıntı:", "",
              blok_kosul_ozet(u, ctx, c), ""]
        kt_c = blok_kova_tablo(u, ctx, c)
        if kt_c:
            p += [kt_c, ""]
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
                ts = x.get("ters_secim") or {}
                if h == "tutmadi" and c in arti and ts.get("hukum") == "tuttu":
                    # Artı kalan paritede "tutmadı" tek başına yanıltır: tersi tuttuysa sonuç o kovada toplanmıştır.
                    satir.append(f"tutmadı; tersi tuttu ({_kova_ifade(d, ts.get('secilen') or [])} "
                                 f"{_hucre(ts.get('oos_secilen_r'), 'ra')} R, "
                                 f"{sayi(int(x.get('oos_tamamlayan_n') or 0), 0)} işlem)")
                    continue
                satir.append(f"tuttu: {_kova_ifade(d, x.get('secilen') or [])}" if h == "tuttu" else
                             {"tutmadi": "tutmadı", "secilmedi": "kova seçilmedi", "hepsi": "bütün kovalar seçildi",
                              "esdeger": "aynı ölçü"}.get(h, "—"))
            govde.append(satir)
        tersi = any("tersi tuttu" in h for s in govde for h in s[1:])
        p += [f"En az bir paritede tutan değişkenler, {_parite_sayisi(u)} paritede (\"tuttu\" hücresinde seçilen kova"
              + ("; \"tersi tuttu\": örneklem dışında artı kalan paritede, örneklem içinde ortalamanın altında kalan "
                 "kova örneklem dışında tuttu, parantezde onun sonucu" if tersi else "") + "):", "",
              _tablo(["Değişken"] + [PARITE[c] for c in _ciftler(b)], govde, ["l"] + ["l"] * len(_ciftler(b))), ""]
    return "\n".join(p)


# ─────────────────────────────────────────────────────────────── dokuzuncu ders: neden başarısız
def _bs(u: Uretim) -> dict:
    """Dokuzuncu dersin ölçüleri (ders_olcum → basarisiz.bolum; hepsi betimleme)."""
    b = u.O.get("basarisiz")
    if not b:
        raise SablonHatasi("dokuzuncu dersin ölçüsü yok (basarisiz)")
    return b


def _puan(x) -> str:
    """Kesirlerin farkı puan olarak, işaretli, bir hane (0,084 → +8,4)."""
    return "—" if x is None or not math.isfinite(x) else sayi(100 * x, 1, arti=True)


def _turetilmis_kurallar(u: Uretim, kurallar) -> str:
    """Tablo notunun parçası: varsayılanı ön kayıtta olmayan (türetilmiş) kurallar adıyla; yoksa boş."""
    t = [adlar.BIRIM[b][1] for b in kurallar if adlar.turetilmis(u.O["birim"].get(b) or {})]
    return f" Türetilmiş varsayılan: {liste_yaz(t)} (ön kayıtlı varsayılandan tek boyutu değiştirilerek)." if t else ""


def _stopsuz_kurallar(u: Uretim, kurallar) -> list[str]:
    return [b for b in kurallar if ((u.O["birim"][b].get("varsayilan") or {}).get("stop_turu")) == "yok"]


def blok_neden_basabas(u: Uretim, ctx: dict, donem: str = "oos") -> str:
    """Kural başına isabet, başabaş isabeti ve maliyetin iki etkisi (basarisiz.basabas; dört paritenin havuzu)."""
    h = _bs(u)["basabas"]["havuz"][donem]
    sira = sorted(h, key=lambda b: (-h[b]["acik"], b))
    govde = [[adlar.BIRIM[b][1], _hucre(h[b]["n"], "n"), _hucre(h[b]["isabet"], "yz1"), _hucre(h[b]["pstar"], "yz1"),
              _puan(h[b]["acik"]), _puan(h[b]["brut_acik"]), _puan(h[b]["dpstar"]), _puan(h[b]["dp"])] for b in sira]
    pen = _pencere_ad(u)[donem]
    return ('<div class="sayi-tablo">\n\n'
            + _tablo(["Kural", "İşlem", "İsabet", "Başabaş isabeti", "Açık (puan)", "Brüt açık (puan)", "Δp* (puan)",
                      "Δp (puan)"], govde) + "\n\n</div>\n\n"
            f"_Tür: betimleme. {bas_buyuk(pen)}, önceden kayıtlı varsayılanlar; {_parite_sayisi(u)} paritenin işlemleri "
            "birlikte. Başabaş "
            "isabeti p* = |ortalama kayıp| / (ortalama kazanç + |ortalama kayıp|); açık = isabet − p*, işlem başına "
            "beklentinin işaretini taşır. Brüt açık aynı ölçünün orta fiyattan orta fiyata hâli. Δp*: maliyetin başabaş "
            "isabetini yükseltmesi (net p* − brüt p*); Δp: maliyetin isabeti düşürmesi (brüt isabet − net isabet). "
            "Özdeşlik: açık = brüt açık − Δp* − Δp." + _turetilmis_kurallar(u, sira) + "_")


def blok_neden_ayrisim(u: Uretim, ctx: dict, donem: str = "oos") -> str:
    """Kaybın yön, zamanlama ve maliyet payları kural başına (basarisiz.ayrisim; ayna işlemle)."""
    a = _bs(u)["ayrisim"][donem]
    k = a["kural"]
    sira = sorted(k, key=lambda b: (-k[b]["net"], b))
    stopsuz = set(_stopsuz_kurallar(u, sira))
    govde = [[adlar.BIRIM[b][1] + (" ‡" if b in stopsuz else ""), _hucre(k[b]["n"], "n"), _hucre(k[b]["y"], "r3"),
              _hucre(k[b]["z"], "r3"), _hucre(-k[b]["c_makas"], "r3"), _hucre(-k[b]["c_kayma"], "r3"),
              _hucre(k[b]["net"], "r3")] for b in sira]
    dis = sorted({x.split(":")[0] for x in a.get("dislanan") or []})
    tamamen, kismen = [b for b in dis if b not in k], [b for b in dis if b in k]
    esik = int(u.O["kunye"]["uygulama_esik"]["rastgele"])
    not_ = (f"_Tür: betimleme. {bas_buyuk(_pencere_ad(u)[donem])}; kural başına paritelerin işlem sayısıyla ağırlıklı "
            "ortalaması, R / "
            "işlem. Net = yön payı + zamanlama payı − makas − kayma (makas ve kayma tabloda eksi işaretle). Makas "
            "ölçülmüş bid/ask makasıdır, kayma modelin dolum başına varsaydığı maliyet.")
    if tamamen:
        not_ += (" Tabloda yok: " + liste_yaz([adlar.BIRIM[b][1] for b in tamamen])
                 + f" (paritelerinin hepsinde örneklem dışında {sayi(esik, 0)} işlemden az; ayna kurulmaz).")
    if kismen:
        not_ += (" Bazı paritesi dışarıda (aynı sebeple): " + liste_yaz([adlar.BIRIM[b][1] for b in kismen]) + ".")
    if stopsuz:
        not_ += " ‡ Stopsuz kural: R girişteki ATR(14), bir risk değil ölçek birimi."
    return ('<div class="sayi-tablo">\n\n'
            + _tablo(["Kural", "İşlem", "Yön payı", "Zamanlama payı", "Makas", "Kayma", "Net"], govde)
            + "\n\n</div>\n\n" + not_ + _turetilmis_kurallar(u, sira).rstrip() + "_")


def blok_neden_esik(u: Uretim, ctx: dict) -> str:
    """Kural başına başabaş gidiş-dönüş maliyeti c* ve ödenen maliyet, iki pencerede (basarisiz.esik; pip)."""
    e = _bs(u)["esik"]["havuz"]
    o, t = e["oos"], e["tum"]
    sira = sorted(o, key=lambda b: (-o[b]["cstar"], b))

    def ar(x):
        return f"{sayi(x['alt'], 2)} / {sayi(x['ust'], 2)}"
    govde = [[adlar.BIRIM[b][1], _hucre(o[b]["n"], "n"), sayi(o[b]["cstar"], 2), ar(o[b]), sayi(o[b]["odenen"], 2),
              sayi(t[b]["cstar"], 2), ar(t[b]), sayi(t[b]["odenen"], 2)] for b in sira]
    pa = _pencere_ad(u)
    return ('<div class="sayi-tablo">\n\n'
            + _tablo(["Kural", f"İşlem ({pa['oos']})", f"c* ({pa['oos']})", "%95 aralığı", "Ödenen",
                      "c* (bütün dönem)", "%95 aralığı", "Ödenen"], govde)
            + "\n\n</div>\n\n_Tür: betimleme. Pip, gidiş-dönüş, işlem başına; önceden kayıtlı varsayılanlar, dört "
            "paritenin işlemleri "
            "birlikte. c* = ortalama brüt R / ortalama (1 / R'nin pip karşılığı): işlem başına sabit bir maliyet c* "
            "olsaydı net R sıfır olurdu (ilk mertebe: işlemler maliyetle değişmez sayılır). Aralık, brüt sonucun önceden "
            "kayıtlı bootstrap aralığının uçlarından. Ödenen: ölçülen makas ve varsayılan kaymanın toplamı."
            + _turetilmis_kurallar(u, sira) + "_")


def blok_neden_ay_sonu(u: Uretim, ctx: dict) -> str:
    """Fiksing momentumunun ay sonu alt kümesi parite × pencere: bugünkü tanımla ve eski tanımla (basarisiz.ay_sonu ve
    karşı olgunun alt küme kaydı)."""
    a = _bs(u)["ay_sonu"]["parite"]
    eski = {u_["cift"]: u_ for u_ in (((u.O.get("karsi_olgu") or {}).get("ay_sonu_alt_kume") or {}).get("uye") or [])
            if u_.get("birim") == "fiks_momentum" and u_.get("kim") == "varsayilan" and u_.get("ay_sonu")}
    pa = _pencere_ad(u)
    govde = []
    for c in PARITE:
        if c not in a:
            continue
        for d in ("is", "oos"):
            x = a[c][d]["ay_sonu"]
            e_ = ((eski.get(c) or {}).get("ay_sonu") or {}).get(d) or {}
            govde.append([PARITE[c], pa[d], _hucre(x.get("n"), "n"), _hucre(x.get("isabet"), "yz1"),
                          _hucre(x.get("brut"), "r3"), _hucre(-x["maliyet"] if x.get("maliyet") is not None else None,
                                                              "r3"),
                          _hucre(x.get("net"), "r3"), f"{_hucre(x.get('alt'), 'r3')} / {_hucre(x.get('ust'), 'r3')}",
                          _hucre(e_.get("beklenti_r"), "r3"),
                          f"{_hucre(e_.get('ga_alt'), 'r3')} / {_hucre(e_.get('ga_ust'), 'r3')}" if e_ else "—"])
    return ('<div class="sayi-tablo">\n\n'
            + _tablo(["Parite", "Pencere", "Ay sonu", "İsabet", "Brüt", "Maliyet", "Net", "%95 aralığı",
                      "Net, eski tanımla", "%95 aralığı (eski)"], govde, ["l", "l"] + ["r"] * 8)
            + "\n\n</div>\n\n_Tür: betimleme. Fiksing momentumu, önceden kayıtlı varsayılan; R / işlem, ayda bir işlem. "
            "Bugünkü tanım "
            "(ön kaydın tanımı): ayın son Londra iş günü; eski tanım: ayın son hafta içi günü. Aralık önceden kayıtlı "
            "bootstrap'tan. Ön kayıt alt kümeye hüküm vermez._")


def blok_neden_haber(u: Uretim, ctx: dict) -> str:
    """Haberin fiyata girme hızı: ilk beş dakikanın yönüne göre devam (basarisiz.haber; günlük ATR'nin yüzdesi)."""
    h = _bs(u)["haber"]
    sira = [o for o in adlar.OLAY if o in h] + sorted(o for o in h if o not in adlar.OLAY)
    govde = []
    for o in sira:
        x = h[o]
        aralik = (f"{yuzde(x['d60_alt'], 1, arti=True)} / {yuzde(x['d60_ust'], 1, arti=True)}" if x["parite"] > 1
                  else "—")
        govde.append([adlar.OLAY.get(o, o), _hucre(x["n"], "n"), sayi(x["parite"], 0), yuzde(x["h5"], 1),
                      yuzde(x["d15"], 1, arti=True), yuzde(x["d60"], 1, arti=True), aralik])
    return ('<div class="sayi-tablo">\n\n'
            + _tablo(["Olay", "Olay × parite", "Parite", "İlk 5 dk", "5 → 15 dk", "5 → 60 dk", "5 → 60 dk, paritelerin "
                      "aralığı"], govde) + "\n\n</div>\n\n"
            "_Tür: betimleme. Olay anındaki orta fiyattan, önceki günlerin ATR'sinin yüzdesi; ilk beş dakikanın yönünde "
            "artı (yukarı ve "
            "aşağı kapanan olaylar simetrik birleştirildi: iki kolun farkının yarısı). İlk beş dakikanın hareketi tanımı "
            "gereği artıdır; devam ya da geri dönüş sonraki iki sütundadır. Paritelerin olay sayısıyla ağırlıklı._")


_HESAP = {"bol": lambda a, b: a / b, "carp": lambda a, b: a * b, "fark": lambda a, b: a - b,
          "topla": lambda a, b: a + b}


def blok_hesap(u: Uretim, ctx: dict, islem: str, yol_a: str, yol_b: str, bicim: str) -> str:
    """İki ölçüm değeriyle tek bir aritmetik işlem (bol · carp · fark · topla), biçimiyle: alıştırmanın çözümü sayıyı
    elle yazmaz, ölçümden hesaplar. İkinci terim bir yol değil sayıysa (ondalık noktayla) sabit olarak okunur."""
    if islem not in _HESAP:
        raise SablonHatasi(f"hesap: bilinmeyen işlem {islem}")

    def deger(y):
        if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", y):
            return float(y)
        v = yol_coz(y, ctx)
        if v is None:
            raise SablonHatasi(f"hesap: ölçülemeyen değer {y}")
        return _sayisal(v)
    return bicimle(_HESAP[islem](deger(yol_a), deger(yol_b)), bicim, f"{islem} {yol_a} {yol_b}")


def _artilar(u: Uretim) -> list[tuple[str, str, dict]]:
    """Örneklem dışında net sonucu artı kalan varsayılan bileşimler (kural sırası derslerin, parite sırası künyenin)."""
    out = []
    for b in _butun_birimler(u):
        for c in PARITE:
            v = (((u.O["birim"][b].get("cift") or {}).get(c) or {}).get("varsayilan") or {})
            r = (v.get("oos") or {}).get("beklenti_r")
            if r is not None and r > 0:
                out.append((b, c, v))
    return out


def blok_neden_kuyruk(u: Uretim, ctx: dict) -> str:
    """Örneklem dışında net artı kalan bileşimlerin kuyruk duyarlılığı: en iyi işlem ve en iyi üç işlem çıkınca işlem
    başına net R, en iyi işlemin günü ve toplam R içindeki payı (ölçümün kuyruk kaydından)."""
    govde, donen = [], 0
    for b, c, v in _artilar(u):
        k = (v.get("kuyruk") or {}).get("oos") or {}
        n, r = k.get("n"), k.get("r")
        esit = int(k.get("en_iyi_esit") or 1)
        # En iyi değeri birden çok işlem paylaşıyorsa (aynı hedefe ulaşan işlemler) tek bir "en iyi gün" yoktur.
        pay = (k["en_iyi_r"] / (r * n)) if (n and r and esit == 1) else None
        donen += bool((k.get("r_tek_haric") is not None and k["r_tek_haric"] <= 0)
                      or (k.get("r_uc_haric") is not None and k["r_uc_haric"] <= 0))
        gun = _hucre(k.get("en_iyi_gun"), "tarih") if esit == 1 else f"{sayi(esit, 0)} işlem eşit"
        govde.append([adlar.BIRIM[b][1], PARITE[c], _hucre(n, "n"), _hucre(r, "r3"), _hucre(k.get("r_tek_haric"), "r3"),
                      _hucre(k.get("r_uc_haric"), "r3"), gun, _hucre(k.get("en_iyi_r"), "r1"), _hucre(pay, "yz0")])
    if not govde:
        raise SablonHatasi("neden_kuyruk: örneklem dışında net artı bileşim yok")
    return ('<div class="sayi-tablo">\n\n'
            + _tablo(["Kural", "Parite", "İşlem", "Net R", "En iyi işlem çıkınca", "En iyi üç çıkınca", "En iyi işlemin "
                      "günü", "O işlem (R)", "Toplam R içindeki payı"], govde, ["l", "l"] + ["r"] * 7)
            + f"\n\n</div>\n\n_Tür: betimleme. {_pencere_ad(u)['oos']}, önceden kayıtlı varsayılan, işlem başına net R. "
            "Toplam R içindeki "
            "pay: en iyi işlemin R'si / bileşimin bütün işlemlerinin R toplamı; %100'ün üstündeki pay, öbür işlemlerin "
            "toplamının eksi olduğunu söyler. En iyi değeri birden çok işlem paylaşıyorsa tek bir en iyi işlem yoktur._")


def blok_neden_kuyruk_cumle(u: Uretim, ctx: dict) -> str:
    """Net artı kalan bileşimlerin sayımı: kaçında en iyi bir ya da üç işlem çıkınca sonuç sıfıra ya da eksiye döner,
    kaçı hangi paritede (tablo neden_kuyruk ile aynı küme)."""
    a = _artilar(u)
    if not a:
        raise SablonHatasi("neden_kuyruk_cumle: örneklem dışında net artı bileşim yok")
    donen = 0
    for _, _, v in a:
        k = (v.get("kuyruk") or {}).get("oos") or {}
        donen += bool((k.get("r_tek_haric") is not None and k["r_tek_haric"] <= 0)
                      or (k.get("r_uc_haric") is not None and k["r_uc_haric"] <= 0))
    par: dict = {}
    for _, c, _ in a:
        par[c] = par.get(c, 0) + 1
    en, kac = max(par.items(), key=lambda kv: (kv[1], kv[0]))
    s = (f"Örneklem dışında net sonucu artı kalan {SAYI_AD.get(len(a), sayi(len(a), 0))} bileşimin "
         + ("hiçbirinde en iyi bir ya da üç işlem çıkınca işaret dönmüyor" if donen == 0 else
            f"{SAYI_INDE.get(donen, tane(donen, 'inde'))} en iyi bir ya da üç işlem çıkınca sonuç sıfıra ya da eksiye "
            "dönüyor"))
    if kac > 1:
        s += f"; {SAYI_AD.get(kac, sayi(kac, 0))} tanesi {PARITE[en]}"
    return s + "."


def blok_neden_mde(u: Uretim, ctx: dict) -> str:
    """En küçük görülebilir etki: yılda işlem sayısı × süre (basarisiz.guc.mde; tek yönlü %5, %80 güç)."""
    m = _bs(u)["guc"]["mde"]
    ad = {"ayda": "Ayda bir", "haftada": "Haftada bir", "gunde": "Her iş günü"}
    sure = sorted(int(x) for x in next(iter(m["tablo"].values())))
    sira = [k for k in ad if k in m["tablo"]] + sorted(k for k in m["tablo"] if k not in ad)  # ölçüm sözlüğü alfabetik
    govde = [[ad.get(k, k)] + [sayi(m["tablo"][k][str(t)], 2) for t in sure] for k in sira]
    return ('<div class="sayi-tablo">\n\n'
            + _tablo(["İşlem sıklığı"] + [f"{t} yıl" for t in sure], govde) + "\n\n</div>\n\n"
            f"_Tür: betimleme (hesap). R / işlem. İşlem başına standart sapma {sayi(m['sigma'], 2)} R (bütün "
            "bileşimlerin örneklem dışı "
            "standart sapmasının medyanı); tek yönlü %5 düzey, %80 güç. Bir yıl 250 iş günü, 52 hafta, 12 ay sayıldı._")


def blok_ay_sonu_eski_tanim(u: Uretim, ctx: dict, kip: str = "uzun") -> str:
    """Ay sonunun eski tanımının (ayın son hafta içi günü) ay sonu alt kümesine etkisi (ders_olcum.ay_sonu_eski_tanim
    → karsi_olgu.ay_sonu_alt_kume). Tek paragraf: metodoloji dersinin sapma maddesine (uzun) ve fiksing momentumunun
    ay sonu bölümüne (kisa) aynı ölçüden. Örneklem dışında ayrışan aylar ölçüden yazılır: o ayda eski tanımın açtığı
    işlem ile bugünkü tanımın işlemi yan yana."""
    k = (u.O.get("karsi_olgu") or {}).get("ay_sonu_alt_kume")
    if not k:
        raise SablonHatasi("ay sonu alt kümesinin eski tanım ölçüsü yok")
    tb, te = k.get("tutan_bugun") or [], k.get("tutan_eski") or []
    if len(tb) != 1:
        raise SablonHatasi("ay_sonu_eski_tanim: bugünkü tanımla tek tutan biçim bekleniyordu")
    olcmedi = [y for y in k["uye"] if not y.get("ay_sonu")]
    if any(not str(y.get("kim", "")).startswith("tf") for y in olcmedi) or len(olcmedi) != int(k["olculemedi"]):
        raise SablonHatasi("ay_sonu_eski_tanim: ölçülemeyen biçimlerin hepsi zaman dilimi biçimi değil")
    t0 = tb[0]
    x = next(y for y in k["uye"] if (y["birim"], y["cift"], y["kim"]) == (t0["birim"], t0["cift"], t0["kim"]))
    pa = _pencere_ad(u)
    a = x["ay_sonu"]

    def pen(d):
        return (f"{pa[d]} penceresinde {sayi(a[d]['beklenti_r'], 3, arti=True)} R (aralık "
                f"{sayi(a[d]['ga_alt'], 3, arti=True)} / {sayi(a[d]['ga_ust'], 3, arti=True)})")
    ad = f"{adlar.BIRIM[x['birim']][1].lower()} ({PARITE[x['cift']]}, önceden kayıtlı varsayılan)"
    dis = u.O["kunye"]["dis_baslangic"]
    aylar: dict = {}
    for g in x.get("degisen") or []:
        if g["gun"] >= dis:
            aylar.setdefault(g["gun"][:7], {})[g["tanim"]] = g
    parca = [f"{AY[int(ay[5:7])]} {ay[:4]}'{ek(int(ay[:4]), 'de').split(chr(39), 1)[1]} eski tanım {tarih(v['eski']['gun'])} günü {sayi(v['eski']['r'], 2, arti=True)} R, "
             f"bugünkü tanım {tarih(v['bugun']['gun'])} günü {sayi(v['bugun']['r'], 2, arti=True)} R"
             for ay, v in sorted(aylar.items()) if "eski" in v and "bugun" in v]
    if not parca:
        raise SablonHatasi("ay_sonu_eski_tanim: örneklem dışında ayrışan ay yok")
    sayi_ad = SAYI_AD.get(len(parca), sayi(len(parca), 0))
    fark = f"o penceredeki fark {sayi_ad} aydan gelir: " + "; ".join(parca)
    if kip == "kisa":
        return (f"Bu sonuç ay sonunun tanımına duyarlıdır: ay sonu ayın son hafta içi günü sayılsaydı {ad} {pen('is')}, "
                f"{pen('oos')} verirdi; ikinci pencerede aralık sıfırı kapsar. İki tanım yalnız son hafta içi gününün bir "
                f"İngiltere tatiline düştüğü aylarda ayrışır ve {fark}. Derslerdeki ay sonu sayılarının hepsi ön kaydın "
                "tanımıyladır.")
    sonuc = (f"eski tanımla da {liste_yaz([adlar.BIRIM[y['birim']][1] + ' ' + PARITE[y['cift']] for y in te])} tutar"
             if te else "eski tanımla ailenin hiçbir biçimi bu ölçütü sağlamaz")
    return (f"Ay sonu alt kümesinde (ailenin {sayi(k['olculen'], 0)} biçimi ölçüldü; {sayi(k['olculemedi'], 0)} zaman "
            "dilimi biçiminin işlem dosyası saklanmadığı için eski tanımla ölçülemez) bugünkü tanımla ailenin tutma "
            "ölçütünü (iki ayrık pencerede alt uç sıfırın üstünde, ay sonu ile öbür günlerin farkı düzeltilmiş eşiğin "
            f"altında) sağlayan tek biçim {ad}; {sonuc}. Eski tanımla o biçim {pen('is')}, {pen('oos')} verir: ikinci "
            f"pencerede aralık sıfırı kapsar ve {fark}. Tanım, alt kümenin ölçümünü koşuya ekleyen değişiklikle aynı anda "
            "ön kaydın tanımına çekildi; alt kümenin eski tanımla sonucu o gün görülmemişti. Derslerdeki ay sonu "
            "sayılarının hepsi ön kaydın tanımıyladır.")


def blok_kurallar(u: Uretim, ctx: dict, yol: str) -> str:
    """Ölçümdeki bir kural listesinin okur adları, derslerin sırasıyla ("Fiksing momentumu, Gün içi momentum ve İç
    mum"). Liste boşsa üretim düşer: boş bir listeyi adıyla anan cümle yazılmaz."""
    v = yol_coz(yol, ctx)
    if not isinstance(v, list) or not v:
        raise SablonHatasi(f"kurallar: boş olmayan kural listesi bekleniyordu: {yol}")
    sira = [b for b in _butun_birimler(u) if b in v] + sorted(b for b in v if b not in _butun_birimler(u))
    return liste_yaz([adlar.BIRIM[b][1] for b in sira])


def blok_neden_yon_cumle(u: Uretim, ctx: dict) -> str:
    """Yön payının işareti ders ailelerine göre (fade dersi · iki kırılım dersi), iki pencerede, ve yön payının
    en büyük olduğu kuralda maliyetin ne kadarını karşıladığı (basarisiz.ayrisim; betimleme, aile hükmü değil)."""
    a = _bs(u)["ayrisim"]

    def say(d, ders):
        k = a[d]["kural"]
        L = [b for b in adlar.DERS_BIRIM[ders] if b in k]
        return len(L), sum(1 for b in L if k[b]["y"] > 0)
    gruplar = (("fx-gunici-fade", "fade dersinin"), ("fx-gunici-seans-kirilimlari", "seans kırılımları dersinin"),
               ("fx-gunici-yapi-kirilimlari", "yapı kırılımları dersinin"))
    k = a["oos"]["kural"]
    en = max(k, key=lambda b: (k[b]["y"], b))
    if k[en]["y"] <= 0:
        raise SablonHatasi("neden_yon_cumle: örneklem dışında yön payı artı kural yok")

    def kac(m, n):
        return "hepsinde" if m == n else ("hiçbirinde" if m == 0 else f"{SAYI_INDE.get(m, tane(m, 'inde'))}")
    pa = _pencere_ad(u)
    parca = []
    sayim = {}
    for ders, ad in gruplar:
        n_, m_ = say("oos", ders)
        _, m_t = say("tum", ders)
        sayim[ders] = (n_, m_)
        parca.append(f"{ad} {SAYI_AD.get(n_, sayi(n_, 0))} kuralının {kac(m_, n_)} artı (bütün dönemde {kac(m_t, n_)})")
    cumle = f"{pa['oos']} penceresinde yön payı " + liste_yaz(parca) + "."
    # Fade (geri dönüşe bahis) ile seans kırılımları (devama bahis) aynı pencerede birlikte artıysa tablo gün içi
    # fiyatın bir yön eğilimini ayırmaz: iki ters bahis birlikte doğru yönü seçmiş görünür.
    (nf, af), (ns, as_) = sayim["fx-gunici-fade"], sayim["fx-gunici-seans-kirilimlari"]
    if af == nf and as_ == ns:
        cumle += (" Geri dönüşe bahis giren fade kuralları ile devama bahis giren seans kırılımları aynı pencerede "
                  "birlikte artı yön payı taşıyor; tablo bu yüzden gün içi fiyatın devam mı geri dönüş mü eğiliminde "
                  "olduğunu ayırmaz.")
    return (cumle + f" Yön payının en büyük olduğu kural {adlar.BIRIM[en][1]} ({sayi(k[en]['n'], 0)} işlem): "
            f"{sayi(k[en]['y'], 3, arti=True)} R, maliyeti {sayi(k[en]['c'], 3)} R; yön payı maliyetin "
            f"{yuzde(k[en]['y'] / k[en]['c'], 0)} kadarını karşılıyor.")


def blok_neden_rastgele(u: Uretim, ctx: dict) -> str:
    """Rastgele yön sınamasının iki penceredeki sayımı ve eşiği geçen bileşimlerin net sonucu (toplamlar:
    rastgele_oos_liste · rastgele_tum). Genelleme sayıdan kurulur, istisnalar adıyla: yön seçiminin değeri ayırt
    edilebildiği bileşimde maliyeti karşılıyor mu."""
    T = ctx["T"]
    pa = _pencere_ad(u)

    def ad(xs):
        return liste_yaz([f"{adlar.BIRIM[x['birim']][1]} {PARITE[x['cift']]}" for x in xs])

    def arti(xs):
        return [x for x in xs if x["net"] is not None and x["net"] > 0]

    def kalan(xs, n):
        a = arti(xs)
        if not xs:
            return ""
        if not a:
            return " ve hepsinin net sonucu eksi" if n > 1 else " ve net sonucu eksi"
        bn = sum(1 for x in xs if x not in a and x["brut"] is not None and x["brut"] > 0)
        s = (f"; bunların {tane(len(a), 'i')} net artı ({ad(a)})" if len(a) < n else "; hepsi net artı")
        if bn:
            s += f", {tane(bn, 'inde')} brüt sonuç artı, net sonuç eksi"
        return s
    o = T["rastgele_oos_liste"]
    if len(o) != T["rastgele_ust"]:
        raise SablonHatasi("neden_rastgele: örneklem dışı liste sayımla tutmuyor")
    rt = T["rastgele_tum"]
    s = (f"Örneklem dışında {sayi(T['rastgele_n'], 0)} bileşimin {tane(T['rastgele_ust'], 'inde')} gerçek işlem rastgele "
         f"yön dağılımının üst %5'inde; hiçbir kenarın olmadığı bir dünyada beklenen yaklaşık "
         f"{sayi(T['rastgele_beklenen'], 0)}{kalan(o, len(o))}. Bütün dönemde bu sayı {sayi(rt['n'], 0)} bileşimde "
         f"{sayi(rt['ust'], 0)} (beklenen {sayi(rt['beklenen'], 1)}){kalan(rt['ust_liste'], rt['ust'])}.")
    a_o, a_t = arti(o), arti(rt["ust_liste"])
    eksi = len(o) - len(a_o) + rt["ust"] - len(a_t)
    if eksi > len(a_o) + len(a_t):
        s += (" Yön seçiminin değeri sıfırdan ayırt edilebildiği bileşimlerin çoğunda maliyetten küçük; net artı kalan "
              "istisnaların hükmü karşılaştırma dersindedir.")
    return s


def blok_kaynaklar(u: Uretim, ctx: dict, slug: str) -> str:
    """Bir dersin kaynakçası, atıf kaydından (atif.ders_kaynaklari: kaydın bu dersi andığı ve atfı doğrulanmış
    kayıtlar, künyenin alfabe sırasıyla). Liste metinde elle yazılmaz: künyesi dondurulmuş kaynağa karşı sınanan kayıt
    tek kaynaktır, metindeki her atfın kaydı olduğunu ve her kaydın metinde anıldığını kapı sorar (dogrula 17).
    Alıntıları yayımlanmış sürüm olarak tanımlanamayan bir metinden gelen kaydın sürümü (kaydın surum alanı) künyenin
    yanında basılır: okur dergi metninin doğrulandığını sanmasın."""
    import atif
    k = atif.ders_kaynaklari(slug)
    if not k:
        raise SablonHatasi(f"kaynaklar: {slug} dersini anan doğrulanmış kayıt yok")
    return "\n".join(f"- {x['kunye']}" + (f" ({x['surum']})" if x.get("surum") else "") for x in k)


# ─────────────────────────────────────────────────────────────── kısa seri (fx-gunici-sonuc · stop-hedef · kontrol)
def _kisa(u: Uretim) -> dict:
    k = u.O.get("kisa")
    if not k:
        raise SablonHatasi("ölçümde kısa serinin kaydı yok (kisa)")
    return k


def blok_kisa_kural_tablo(u: Uretim, ctx: dict) -> str:
    """Kural başına sade sonuç: kazanma oranı, kâra geçmek için gereken kazanma oranı, işlem başına net R (dört
    paritenin işlemleri birlikte, örneklem dışı, maliyetten sonra) ve dört paritedeki hüküm sayımı. Sıra: kazanma
    oranının gerekene en yakın olduğu kural önce."""
    h = (((u.O.get("basarisiz") or {}).get("basabas") or {}).get("havuz") or {}).get("oos") or {}
    if not h:
        raise SablonHatasi("ölçümde başabaş havuzu yok")
    sira = sorted(h, key=lambda b: (-(h[b]["isabet"] - h[b]["pstar"]), b))
    govde, stopsuz = [], False
    for b in sira:
        bb = u.O["birim"][b]
        ss = ((bb.get("varsayilan") or {}).get("stop_turu")) == "yok"
        stopsuz |= ss
        govde.append([adlar.BIRIM[b][1] + (" ‡" if ss else ""), _hucre(h[b]["isabet"], "yz1"),
                      _hucre(h[b]["pstar"], "yz1"), _hucre(h[b]["net"], "ra"), hukum_sayim_yaz(bb)])
    not_ = ("_2024 → dönemi, dört paritenin işlemleri birlikte, makas ve kayma düşülmüş. \"Gereken\" kazanma oranı, "
            "kuralın ortalama kazancı ve kaybının boyundan hesaplanır: kayıp / (kazanç + kayıp). Hüküm sütunu dört "
            "paritenin her biri için ayrı verilen hükmün sayımıdır."
            + (" ‡ Stopsuz kural: R, girişteki oynaklık (ATR) birimidir." if stopsuz else "") + "_")
    return _tablo(["Kural", "Kazanma oranı", "Gereken", "İşlem başına (R)", "Dört paritede hüküm"], govde,
                  ["l", "r", "r", "r", "l"]) + "\n\n" + not_


KISA_HEDEF_AD = {"1R": "Yakın hedef (1R)", "2R": "Uzak hedef (2R)", "gun_sonu": "Hedef yok, gün sonunda çık"}


def blok_kisa_hedef_ornek(u: Uretim, ctx: dict, birim: str) -> str:
    """Tek kural, ana parite: öbür bütün ayarlar sabitken yalnız hedef değişince kazanma oranı ve işlem başına R."""
    c = ana()
    v = ((((u.O["birim"].get(birim) or {}).get("cift") or {}).get(c) or {}).get("varyant") or {}).get("hedef") or {}
    if not v:
        raise SablonHatasi(f"{birim}: {c} için hedef varyantı yok")
    govde = [[KISA_HEDEF_AD.get(h, h), _hucre((x.get("oos") or {}).get("isabet"), "yz1"),
              _hucre((x.get("oos") or {}).get("beklenti_r"), "ra"), _hucre((x.get("oos") or {}).get("n"), "n")]
             for h, x in v.items()]
    return _tablo(["Hedef", "Kazanma oranı", "İşlem başına (R)", "İşlem"], govde) + \
        f"\n\n_{adlar.BIRIM[birim][1]}, {PARITE[c]}, 2024 →; stop, saat ve mum aynı, yalnız hedef değişiyor._"


KISA_GRUP_AD = {"yakin": "Yakın hedef (1R)", "uzak": "Uzak hedef (2R)", "hedefsiz": "Hedefsiz (gün sonu ya da süre)",
                "ozel": "Kurala özgü hedef"}


def blok_kisa_grup_tablo(u: Uretim, ctx: dict) -> str:
    k = _kisa(u)
    govde = [[KISA_GRUP_AD[g], _hucre(k["grup"][g]["n"], "n"), _hucre(k["grup"][g]["isabet"], "yz1"),
              _hucre(k["grup"][g]["r"], "ra"), _hucre(k["grup"][g]["ikisi_arti"], "n")]
             for g in k["grup_sira"] if k["grup"].get(g, {}).get("n")]
    return _tablo(["Hedef türü", "Ayar", "Kazanma oranı", "İşlem başına (R)", "İki dönemde de artı"], govde) + \
        ("\n\n_Kazanma oranı ve R, 2024 → dönemindeki ayarların medyanı. \"İki dönemde de artı\": hem 2018–2023'te hem "
         "2024 →'de işlem başına sonucu sıfırın üstünde olan ayar sayısı._")


KISA_ESLI_AD = {"hedef": ("Hedefi uzat", "1R → 2R"), "stop_turu": ("Stopu kapanışa çevir", "sert → kapanış"),
                "stop_yeri": ("Stopu yaklaştır", "karşı uç → orta")}


def blok_kisa_esli_tablo(u: Uretim, ctx: dict) -> str:
    k = _kisa(u)
    govde = []
    for param, x in k["esli"].items():
        if not x.get("n"):
            continue
        ad, deg = KISA_ESLI_AD[param]
        govde.append([f"{ad} ({deg})", _hucre(x["n"], "n"),
                      f"{_hucre(x['a_isabet'], 'yz1')} → {_hucre(x['b_isabet'], 'yz1')}",
                      f"{_hucre(x['a_r'], 'ra')} → {_hucre(x['b_r'], 'ra')}", _hucre(x["b_iyi_pay"], "yz0")])
    return _tablo(["Değişiklik", "Ayar çifti", "Kazanma oranı", "İşlem başına (R)", "Sonucu iyileşen çift"], govde) + \
        ("\n\n_Her çift aynı kural, aynı parite ve aynı öbür ayarlar; yalnız satırdaki seçim değişiyor. Sayılar 2024 → "
         "dönemindeki çiftlerin medyanı._")


#: Maliyet tablosunun örnek stop uzaklıkları (pip) ve hedefleri (R).
KISA_STOP_PIP = (5, 10, 15, 20, 30)


def blok_kisa_maliyet_stop(u: Uretim, ctx: dict) -> str:
    """Ölçülen medyan maliyetle (pip, gidiş-dönüş) stop uzaklığına göre maliyetin R içindeki payı ve kâra geçmek için
    gereken kazanma oranı, 1R ve 2R hedefte. Gereken = (S + c) / ((k + 1)·S): kazanç kS − c, kayıp S + c."""
    c = float(((u.O["basarisiz"]["basabas"]).get("maliyet_pip") or {})["medyan"])
    govde = []
    for s_ in KISA_STOP_PIP:
        govde.append([f"{s_} pip", _hucre(c / s_, "yz0"), _hucre((s_ + c) / (2 * s_), "yz1"),
                      _hucre((s_ + c) / (3 * s_), "yz1")])
    return _tablo(["Stop uzaklığı", "Maliyetin R'deki payı", "Gereken, 1R hedef", "Gereken, 2R hedef"], govde) + \
        (f"\n\n_Maliyet, serinin işlemlerinde ölçülen medyan gidiş-dönüş maliyeti: {sayi(c, 1)} pip (makas + kayma). "
         "Maliyetsiz bir dünyada gereken oran 1R hedefte %50, 2R hedefte üçte birdir._")


def blok_kisa_parite_maliyet(u: Uretim, ctx: dict) -> str:
    """Parite başına ölçülen medyan makas ve modelin kayması: bir işlemin gidiş-dönüş maliyeti (pip)."""
    k = u.O["kunye"]
    kay = 2 * float(k["temel_kayma_pip"])
    govde = []
    for c in PARITE:
        m = ((((u.O.get("veri") or {}).get("kalite") or {}).get(c) or {}).get("makas") or {}).get("medyan_pip")
        if m is None:
            raise SablonHatasi(f"{c}: makas ölçümü yok")
        govde.append([PARITE[c], _hucre(m, "s1"), _hucre(kay, "s1"), _hucre(m + kay, "s1")])
    return _tablo(["Parite", "Makas (medyan, pip)", "Kayma (iki dolum, pip)", "Bir işlemin maliyeti (pip)"], govde) + \
        (f"\n\n_Makas, 2018 → verisinin dakika dakika ölçülen medyanı; kayma modelin varsayımı: dolum başına "
         f"{sayi(float(k['temel_kayma_pip']), 1)} pip, haber penceresinde ayrıca {sayi(float(k['haber_kayma_pip']), 1)} pip. "
         "Makas haber anında ve gün dönümünde birkaç katına çıkar; tablodaki sakin saatlerin maliyetidir._")


KISA_SIKLIK = {"gunde": "Günde bir işlem", "haftada": "Haftada bir işlem", "ayda": "Ayda bir işlem"}


def blok_kisa_guc_tablo(u: Uretim, ctx: dict) -> str:
    """Kaç yıllık kayıtla ne büyüklükte bir kenar sıfırdan ayırt edilir (tek yönlü %5, %80 güç): basarisiz.guc.mde."""
    m = u.O["basarisiz"]["guc"]["mde"]
    yillar = sorted(next(iter(m["tablo"].values())), key=int)
    govde = [[KISA_SIKLIK.get(s_, s_)] + [_hucre(m["tablo"][s_][y], "s2") for y in yillar] for s_ in KISA_SIKLIK
             if s_ in m["tablo"]]
    return _tablo(["Sıklık"] + [f"{y} yıl" for y in yillar], govde) + \
        (f"\n\n_Hücre: o sıklık ve sürede sıfırdan ayırt edilebilecek en küçük kenar, R / işlem. İşlem sonuçlarının "
         f"oynaklığı serinin ölçülen değeri ({sayi(float(m['sigma']), 2)} R); %80 olasılıkla, tek yönlü %5 düzeyinde._")

#: Kural kartının okur adları (kısa seri; strateji derslerinin adlarından kısa).
KART_DEGER = {"karsi_uc": "karşı uç", "orta": "aralığın ortası", "sinyal_mumu": "sinyal mumunun ucu",
              "atr_yarim": "seviyenin 0,5·ATR içi", "sert": "sert", "kapanis": "kapanış", "yok": "stop yok"}
KART_HEDEF = {"gun_sonu": "gün sonu", "seviye": "karşı pivot seviyesi", "karsi_uc": "aralığın öbür ucu",
              "oncesi": "haber öncesi fiyat", "itki_ucu": "itkinin ucu", "vwap": "VWAP"}


def _kart(u: Uretim, birim: str) -> dict:
    k = (_kisa(u).get("kart") or {}).get(birim)
    if not k:
        raise SablonHatasi(f"{birim}: kural kartı ölçülmedi (kisa.kart)")
    return k


def _kart_stop_ad(p: dict, boyut: list[str]) -> str:
    st = [k for k in ("stop_yeri", "stop_kurali", "stop_turu") if k in boyut]
    if not st:
        return "—"
    return bas_buyuk(" · ".join(KART_DEGER.get(p.get(k), adlar.DEGER.get(p.get(k), p.get(k))) for k in st))


def _kart_hedef_ad(x: str, aile: str) -> str:
    if x == "zaman":
        n = ZAMAN_MUM.get("haber" if aile in HABER_AILE else "desen")
        if not n:
            raise SablonHatasi("zaman hedefinin mum sayısı kurulmadı (zaman_kur)")
        return f"{n} mum sonra çık"
    return KART_HEDEF.get(x) or _deger_yaz(x, "hedef", aile)


def _kart_ayar_ad(p: dict, boyut: list[str], aile: str) -> str:
    """Hücrenin okur adı: "stop karşı uç · sert, hedef 2R"."""
    st = [k for k in ("stop_yeri", "stop_kurali", "stop_turu") if k in boyut]
    par = []
    if st:
        par.append("stopsuz" if p.get("stop_turu") == "yok" and len(st) == 1 else
                   "stop " + " · ".join(KART_DEGER.get(p.get(k), str(p.get(k))) for k in st))
    if "hedef" in boyut:
        par.append("hedef " + _kart_hedef_ad(p.get("hedef"), aile))
    return ", ".join(par) or "tek ayar"


def _secilen_sayim(b: dict) -> tuple[str, list]:
    """Her paritede 2018–2023'ün en iyi ayarı (bütün ızgara) seçildiğinde 2024 → hükümlerinin sayımı."""
    say: dict = {}
    r = []
    for c in _ciftler(b):
        s = b["cift"][c].get("secilen") or {}
        h = s.get("hukum") if b["cift"][c].get("secilen_p") else None
        h = h or "secilemedi"
        say[h] = say.get(h, 0) + 1
        if (s.get("oos") or {}).get("beklenti_r") is not None and h != "secilemedi":
            r.append((c, s["oos"]["beklenti_r"]))
    ad = dict(adlar.HUKUM, secilemedi="seçilemedi (az işlem)")
    return " · ".join(f"{say[h]} {ad[h]}" for h in ("calisiyor", "zayif", "calismiyor", "olculemedi", "secilemedi")
                      if say.get(h)), r


def blok_kisa_kart(u: Uretim, ctx: dict, birim: str) -> str:
    """Bir kuralın kartı: varsayılan sonuç (2024 →, dört parite birlikte), stop × hedef tablosu (öbür ayarlar
    varsayılanda) ve "çalışır hale gelir miydi" cevabı: 2018–2023'te en iyi stop/hedef hücresinin 2024 → sonucu,
    bütün ızgaradan parite parite seçilen ayarın hükmü, ve sonradan bakınca 2024 →'ün en iyi hücresi."""
    k = _kart(u, birim)
    b = u.O["birim"][birim]
    aile = b.get("aile") or ""
    h = (((u.O.get("basarisiz") or {}).get("basabas") or {}).get("havuz") or {})
    ho, hi = (h.get("oos") or {}).get(birim), (h.get("is") or {}).get(birim)
    if not ho or not hi:
        raise SablonHatasi(f"{birim}: başabaş havuzu yok")
    stopsuz = (b.get("varsayilan") or {}).get("stop_turu") == "yok"
    p = [f"**Sonuç (varsayılan ayar, dört parite birlikte).** 2024 →'de {sayi(ho['n'], 0)} işlem, kazanma oranı "
         f"{_hucre(ho['isabet'], 'yz1')}; kâra geçmek için gereken {_hucre(ho['pstar'], 'yz1')}. İşlem başına "
         f"{_hucre(ho['net'], 'ra')} R (2018–2023'te {_hucre(hi['net'], 'ra')} R). Parite parite hüküm: "
         f"{hukum_sayim_yaz(b)}.", ""]
    H = k["hucre"]
    boyut = k["boyut"]
    sira = {kk: [str(x) for x in ((b.get("izgara_deger") or {}).get(kk) or [])] for kk in boyut}

    def siralama(kk, x):
        L = sira.get(kk) or []
        return L.index(x) if x in L else len(L)

    def hucre(d):
        t = f"{_hucre(d['oos']['r'], 'ra')} · {_hucre(d['oos']['isabet'], 'yz0')}"
        if not d["sayilir"]:
            t += " (az)"
        return f"**{t}**" if d["varsayilan"] else t
    st = [kk for kk in ("stop_yeri", "stop_kurali", "stop_turu") if kk in boyut]
    sutun = sorted({tuple(d["p"].get(kk) for kk in st) for d in H},
                   key=lambda t: tuple(siralama(kk, x) for kk, x in zip(st, t)))
    if "hedef" in boyut:
        hedefler = sorted({d["p"]["hedef"] for d in H}, key=lambda x: siralama("hedef", x))
        govde = []
        for hd in hedefler:
            satir = [bas_buyuk(_kart_hedef_ad(hd, aile))]
            for t in sutun:
                d = [x for x in H if x["p"].get("hedef") == hd and tuple(x["p"].get(kk) for kk in st) == t]
                satir.append(hucre(d[0]) if d else "—")
            govde.append(satir)
        bas = ["Hedef / stop"] + [_kart_stop_ad(dict(zip(st, t)), boyut) for t in sutun]
    else:
        govde = [[_kart_stop_ad(d["p"], boyut), hucre(d)] for t in sutun
                 for d in H if tuple(d["p"].get(kk) for kk in st) == t]
        bas = ["Stop", "İşlem başına (R) · kazanma oranı"]
    p += ['<div class="sayi-tablo">', "", _tablo(bas, govde, ["l"] + ["r"] * (len(bas) - 1)), "", "</div>", "",
          "_2024 →, dört parite birlikte, maliyetten sonra. Hücre: işlem başına net R · kazanma oranı. Kalın hücre "
          "kuralın varsayılan ayarı; öbür ayarlar (mum, saat, seviye) varsayılanda. \"az\": bir dönemde "
          f"{sayi(_kisa(u)['asgari'], 0)} işlemden az."
          + (" R birimi girişteki oynaklık (1 ATR); sert ve kapanış stopu girişten 1 ATR uzakta." if stopsuz else "")
          + "_", ""]
    # Çalışır hale gelir miydi?
    v = [d for d in H if d["varsayilan"]][0]
    cumle = []
    if "is_en_iyi" in k:
        ie, oe = H[k["is_en_iyi"]], H[k["oos_en_iyi"]]
        if ie["varsayilan"]:
            cumle.append(f"2018–2023'te en iyi çıkan stop/hedef bileşimi varsayılanın kendisi "
                         f"({_hucre(ie['is']['r'], 'ra')} R).")
        else:
            cumle.append(f"2018–2023'te en iyi çıkan stop/hedef bileşimi ({_kart_ayar_ad(ie['p'], boyut, aile)}) o dönemde "
                         f"{_hucre(ie['is']['r'], 'ra')} R veriyordu; 2024 →'de {_hucre(ie['oos']['r'], 'ra')} R.")
        if k["oos_arti"] == 0:
            cumle.append(f"Sonradan bakınca bile tablodaki {sayi(k['sayilan'], 0)} bileşimin hiçbiri 2024 →'de artıda "
                         f"değil; en iyisi ({_kart_ayar_ad(oe['p'], boyut, aile)}) {_hucre(oe['oos']['r'], 'ra')} R.")
        else:
            g = u.O["basarisiz"]["guc"]
            mde = (float(g["z_alfa"]) + float(g["z_guc"])) * float(g["mde"]["sigma"]) / math.sqrt(oe["oos"]["n"])
            cumle.append(f"Tablodaki {sayi(k['sayilan'], 0)} bileşimin {sayi(k['oos_arti'], 0)} tanesi 2024 →'de artıda; "
                         f"en iyisi ({_kart_ayar_ad(oe['p'], boyut, aile)}) {_hucre(oe['oos']['r'], 'ra')} R, "
                         f"{sayi(oe['oos']['n'], 0)} işlemde (2018–2023'te {_hucre(oe['is']['r'], 'ra')} R). "
                         f"Bu kadar işlemle şanstan ayrılabilecek en küçük sonuç yaklaşık {sayi(mde, 2)} R"
                         + ("; ölçülen sonuç onun altında, yani şanstan ayrılamıyor." if oe["oos"]["r"] < mde else ".")
                         + " Parite parite: " + ", ".join(f"{PARITE[c]} {_hucre(x['r'], 'ra')} R ({sayi(x['n'], 0)} işlem)"
                                                         for c, x in (oe.get("parite") or {}).items()) + ".")
    sec, _ = _secilen_sayim(b)
    cumle.append(f"Bütün ayarlar serbest bırakılıp her paritede 2018–2023'ün en iyisi seçildiğinde 2024 →'de hüküm: "
                 f"{sec}.")
    p.append("**Stop ve hedefle çalışır hale gelir miydi?** " + " ".join(cumle))
    return "\n".join(p)


def blok_kisa_kart_ozet(u: Uretim, ctx: dict, ders: str) -> str:
    """Bir kural dersinin özet tablosu: kural başına varsayılan ayarın 2024 → sonucu, 2018–2023'te en iyi çıkan
    stop/hedef bileşiminin 2024 → sonucu ve sonradan bakınca 2024 →'ün en iyi bileşimi (dört parite birlikte)."""
    L = adlar.KISA_DERS_BIRIM.get(ders)
    if not L:
        raise SablonHatasi(f"kisa_kart_ozet: bilinmeyen ders {ders}")
    govde = []
    for b in L:
        k = _kart(u, b)
        H = k["hucre"]
        v = [d for d in H if d["varsayilan"]][0]
        ie = H[k["is_en_iyi"]] if "is_en_iyi" in k else None
        oe = H[k["oos_en_iyi"]] if "oos_en_iyi" in k else None
        govde.append([adlar.BIRIM[b][1], _hucre(v["oos"]["r"], "ra"),
                      _hucre(ie["oos"]["r"], "ra") if ie else "—", _hucre(oe["oos"]["r"], "ra") if oe else "—",
                      f"{sayi(k['oos_arti'], 0)} / {sayi(k['sayilan'], 0)}"])
    return (_tablo(["Kural", "Varsayılan", "2018–2023'ün en iyisi", "Sonradan en iyi", "Artı bileşim"], govde,
                   ["l", "r", "r", "r", "r"]) +
            "\n\n_İşlem başına net R, 2024 →, dört parite birlikte, maliyetten sonra. \"2018–2023'ün en iyisi\": o "
            "dönemde en iyi çıkan stop/hedef bileşiminin 2024 → sonucu (bir trader'ın o gün seçebileceği). \"Sonradan "
            "en iyi\": 2024 →'e bakarak seçilen bileşim (önceden seçilemezdi). Son sütun: 2024 →'de artıda kalan "
            "stop/hedef bileşimi / tablodaki bileşim._")


NUMARA = "①②③④⑤"


def blok_nasil_ornek(u: Uretim, ctx: dict, birim: str) -> str:
    """Adım adım dersinin örnek gün cümlesi: grafikteki numaralarla aynı sırada (sekil.nasil; numaralar
    adlar.NASIL_ADIM'dan türer): referans (varsa), sinyal ve giriş (aynı andaysa tek adım), çıkış. Ana parite,
    örneklem dışındaki kazanan örnek gün."""
    c = ana()
    b = u.O["birim"][birim]
    x = next((e for e in ((b["cift"].get(c) or {}).get("ornek") or []) if e["etiket"] == "kazanan"), None)
    if x is None:
        raise SablonHatasi(f"nasil_ornek: {birim} için kazanan örnek gün yok")
    ref_ad, sin_ad = adlar.NASIL_ADIM[birim]
    i, tf = x["islem"], int(x["tf"])
    yon = "alış" if i["yon"] > 0 else "satış"
    stopsuz = (b.get("varsayilan") or {}).get("stop_turu") == "yok" or i.get("stop") is None
    no, parca = 0, []
    if ref_ad and any(i.get(k) is not None for k in ("ust", "alt", "seviye")):
        parca.append(f"{NUMARA[no]} {ref_ad}")
        no += 1
    s_t = int(i["sinyal_t"]) if i.get("sinyal_t") else int(i["giris_t"])
    giris = (f"{yon}, {fiyat_yaz(i['giris_f'], c)}"
             + ("" if stopsuz else f"; stop {fiyat_yaz(i['stop'], c)} ({_pip(i['R_pip'])} pip uzakta)")
             + (f"; hedef {fiyat_yaz(i['hedef'], c)}" if i.get("hedef") is not None else ""))
    if int(i["giris_t"]) == s_t:
        parca.append(f"{NUMARA[no]} {saat_tsi(s_t - 60 * tf)}–{saat_tsi(s_t)} TSİ mumu: {sin_ad}; mum kapanınca "
                     f"{giris}")
        no += 1
    else:
        parca.append(f"{NUMARA[no]} {saat_tsi(s_t - 60 * tf)}–{saat_tsi(s_t)} TSİ: {sin_ad}")
        no += 1
        parca.append(f"{NUMARA[no]} {saat_tsi(i['giris_t'])} TSİ'de {giris}")
        no += 1
    parca.append(f"{NUMARA[no]} {saat_tsi(i['cikis_t'])} TSİ'de çıkış ({adlar.neden_ad(i, u.O['kunye']['gun_sonu_et'])}"
                 f"): {_pip_a(i['pnl_pip'])} pip, {sayi(adlar.islem_r(i), 2, arti=True)} R")
    olay = ""
    if i.get("olay"):
        olay = f" Olay: {adlar.OLAY.get(i['olay'], i['olay'])}" + (f", {saat_tsi(i['olay_t'])} TSİ." if i.get("olay_t")
                                                                    else ".")
    return (f"**Grafikteki gün** ({tarih_uzun(x['gun'])}, {_gun_adi(x['gun'])}; {PARITE[c]}, {tf} dakikalık mum)."
            + olay + " " + " · ".join(parca) + "."
            + (" Stopsuz kural: R birimi girişteki oynaklıktır (1 ATR)." if stopsuz else ""))


BLOKLAR = {
    "nasil_ornek": blok_nasil_ornek,
    "kisa_kart_ozet": blok_kisa_kart_ozet,
    "kisa_kart": blok_kisa_kart,
    "kisa_kural_tablo": blok_kisa_kural_tablo, "kisa_hedef_ornek": blok_kisa_hedef_ornek,
    "kisa_grup_tablo": blok_kisa_grup_tablo, "kisa_esli_tablo": blok_kisa_esli_tablo,
    "kisa_maliyet_stop": blok_kisa_maliyet_stop, "kisa_parite_maliyet": blok_kisa_parite_maliyet,
    "kisa_guc_tablo": blok_kisa_guc_tablo,
    "kaynaklar": blok_kaynaklar,
    "kurallar": blok_kurallar, "neden_yon_cumle": blok_neden_yon_cumle, "neden_rastgele": blok_neden_rastgele,
    "neden_basabas": blok_neden_basabas, "neden_ayrisim": blok_neden_ayrisim, "neden_esik": blok_neden_esik,
    "neden_ay_sonu": blok_neden_ay_sonu, "neden_haber": blok_neden_haber, "neden_mde": blok_neden_mde,
    "neden_kuyruk": blok_neden_kuyruk, "neden_kuyruk_cumle": blok_neden_kuyruk_cumle, "hesap": blok_hesap,
    "ay_sonu_eski_tanim": blok_ay_sonu_eski_tanim,
    "sonuclar": blok_sonuclar, "kosul_tanim": blok_kosul_tanim, "kova_tablo": blok_kova_tablo,
    "korelasyon_tablo": blok_korelasyon_tablo,
    "zaman_diger": blok_zaman_diger, "capraz_kapsam": blok_capraz_kapsam, "stop_hedef": blok_stop_hedef,
    "stopsuz_ad": blok_stopsuz_ad, "secimsiz": blok_secimsiz, "stop_cikis": blok_stop_cikis, "ay_sonu_ozet": blok_ay_sonu_ozet, "ay_sonu_ders": blok_ay_sonu_ders, "tsi": blok_tsi, "gun_sonu_tsi": blok_gun_sonu_tsi, "kalite_esik": blok_kalite_esik, "pip_tanimi": blok_pip_tanimi, "kosullar": blok_kosullar, "aday_taban": blok_aday_taban, "kural_iddia": blok_kural_iddia, "fade_maliyet": blok_fade_maliyet, "esik_cumle": blok_esik_cumle, "tuzak": blok_tuzak, "hukum_cumle": blok_hukum_cumle,
    "havuz_cumle": blok_havuz_cumle, "ay_sonu": blok_ay_sonu, "ay_sonu_cumle": blok_ay_sonu_cumle,
    "regresyon": blok_regresyon,
    "devam": blok_devam, "devam_cumle": blok_devam_cumle, "devam_yetersiz": blok_devam_yetersiz,
    "esik_payi": blok_esik_payi, "haber_kirilim": blok_haber_kirilim, "fomc": blok_fomc, "fomc_cumle": blok_fomc_cumle,
    "fomc_payda": blok_fomc_payda, "ozet_olcu": blok_ozet_olcu, "karsilik": blok_karsilik, "komsular": blok_komsular,
    "saat_rejimi": blok_saat_rejimi, "saat_rejimi_cumle": blok_saat_rejimi_cumle,
    "saat_rejimi_aralik": blok_saat_rejimi_aralik,
    "veri": blok_veri, "haber_makas": blok_haber_makas, "haber_makas_ozet": blok_haber_makas_ozet,
    "haber_makas_cumle": blok_haber_makas_cumle,
    "pratik_islem": blok_pratik_islem, "pratik_atr": blok_pratik_atr,
    "ders_ozet": blok_ders_ozet, "takvim": blok_takvim,
    "hukum_matris": blok_hukum_matris, "genel_hukum": blok_genel_hukum, "maliyet_ozet": blok_maliyet_ozet,
    "rastgele_ozet": blok_rastgele_ozet, "arti_rastgele_ayirt": blok_arti_rastgele_ayirt, "korelasyon_cumle": blok_korelasyon_cumle,
    "kosul_genel": blok_kosul_genel, "kosul_genel_cumle": blok_kosul_genel_cumle,
    "onkayit_tablo": blok_onkayit_tablo, "takvim_sorun": blok_takvim_sorun, "celiski": blok_celiski,
    "arsiv_ozet": blok_arsiv_ozet, "olaganustu": blok_olaganustu, "turetilmis_hukum": blok_turetilmis_hukum, "rastgele_tum": blok_rastgele_tum, "rastgele_tum_istisna": blok_rastgele_tum_istisna, "ay_sonu_istisna": blok_ay_sonu_istisna, "hukum_secim_etkisi": blok_hukum_secim_etkisi, "olcu_disi": blok_olcu_disi, "devam_takvim": blok_devam_takvim, "devam_okuma": blok_devam_okuma,
    "uzak_tarama": blok_uzak_tarama, "sessiz": blok_sessiz, "saat_capa": blok_saat_capa,
    "oos_cumle": blok_oos_cumle, "rastgele_cumle": blok_rastgele_cumle, "dsr_cumle": blok_dsr_cumle,
    "wf_cumle": blok_wf_cumle, "rejim_cumle": blok_rejim_cumle,
    "sekil": blok_sekil, "sonuc": blok_sonuc, "sonuc_tum": blok_sonuc_tum, "ayrinti": blok_ayrinti,
    "maliyet": blok_maliyet, "secim": blok_secim, "wf": blok_wf, "rejim": blok_rejim, "kural": blok_kural,
    "hukum": blok_hukum, "kosul_ozet": blok_kosul_ozet, "ornek": blok_ornek, "zaman": blok_zaman, "dst": blok_dst,
    "basabas": blok_basabas, "kontrol_hukum": blok_kontrol_hukum, "ne_zaman": blok_ne_zaman,
    "tf_okuma": blok_tf_okuma, "izgara_okuma": blok_izgara_okuma, "saat_okuma": blok_saat_okuma,
    "kuyruk": blok_kuyruk, "varyant": blok_varyant, "hedef_uzaklik": blok_hedef_uzaklik, "gun_ici": blok_gun_ici,
    "kosul_tek": blok_kosul_tek, "hangi_kosul": blok_hangi_kosul, "pencere_ayrisan": blok_pencere_ayrisan,
    "karsi_olgu": blok_karsi_olgu, "karsi_olgu_zaman": blok_karsi_olgu_zaman, "olculemedi_etki": blok_olculemedi_etki,
    "gun_kumeli": blok_gun_kumeli, "gun_kumeli_yon": blok_gun_kumeli_yon, "tatil_betimi": blok_tatil_betimi,
    "yorum": blok_yorum, "yorum_cumle": blok_yorum_cumle, "yorum_ozet": blok_yorum_ozet,
    "ilk_sonuc_zaman": blok_ilk_sonuc_zaman, "aile_dsr": blok_aile_dsr, "dsr_esik": blok_dsr_esik,
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
