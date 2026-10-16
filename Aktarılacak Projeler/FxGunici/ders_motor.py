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
sıfıra yuvarlanan değer işaretsizdir): r · r1 · r3 (işaretli R) · s0 … s3 (işaretsiz sayı; eksi yine yazılır)
· p1 (işaretli pip) · yz0 · yz1 (kesirden yüzde) · yzs1 (işaretli yüzde) · n (tam sayı) · tarih · tarih_uzun ·
ay_uzun · saat_tsi (epoch saniye → TSİ ss:dd) · fiyat (nokta → fiyat; parite yolda) · ad · kisa (birim adı)
· hukum · deger · param · olay · kosul · t (metin) · liste. Biçimin sonundaki "?" ölçülemeyen değeri "—"
yazar; "?" yoksa ölçülemeyen değer üretimi düşürür (ölçülmemiş bir sayıyı sessizce boş basmak yok).
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
PARITE = {"EURUSD": "EUR/USD", "GBPUSD": "GBP/USD", "USDJPY": "USD/JPY", "AUDUSD": "AUD/USD"}
NOKTA = {"EURUSD": 1e-5, "GBPUSD": 1e-5, "AUDUSD": 1e-5, "USDJPY": 1e-3}
HANE = {"EURUSD": 5, "GBPUSD": 5, "AUDUSD": 5, "USDJPY": 3}
KISA_AD = {"E": "EURUSD", "G": "GBPUSD", "J": "USDJPY", "A": "AUDUSD"}
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
    if bicim in ("r", "r1", "r3"):
        return sayi(_sayisal(v), {"r": 2, "r1": 1, "r3": 3}[bicim], arti=True)
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
        ctx.update({"B": b, "BID": birim, "H": (b.get("havuz") or {}).get("varsayilan")})
        for kisa, cift in KISA_AD.items():
            ctx[kisa] = (b.get("cift") or {}).get(cift)
        # Hüküm sayımı: önceden kayıtlı varsayılanın parite başına hükmü (ön kaydın kuralı) kaç paritede ne.
        hs = {"calisiyor": 0, "zayif": 0, "calismiyor": 0, "olculemedi": 0, "parite": 0, "maliyet": 0}
        for c in _ciftler(b):
            v = b["cift"][c].get("varsayilan") or {}
            hs[v.get("hukum") or "olculemedi"] = hs.get(v.get("hukum") or "olculemedi", 0) + 1
            hs["parite"] += 1
            hs["maliyet"] += 1 if v.get("maliyet_yiyor") else 0
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
            v, cift = yol_coz(yol, ctx), ctx.get("CIFT", "EURUSD")
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
        ("İşlem", "n", "n"), ("İsabet", "isabet", "yz1"), ("Net beklenti (R)", "beklenti_r", "r"),
        ("%95 aralığı, alt", "ga_alt", "r"), ("%95 aralığı, üst", "ga_ust", "r"),
        ("Brüt beklenti (R)", "brut_r", "r"), ("Net beklenti (pip)", "beklenti_pip", "p1"),
        ("Sharpe (yıllık)", "sharpe", "s2"),
    ]
    govde = [[ad] + [_hucre(m.get(k), f) for _, m in sutun] for ad, k, f in satirlar]
    return _tablo([""] + [s for s, _ in sutun], govde)


def blok_ayrinti(u: Uretim, ctx: dict, donem: str = "oos") -> str:
    b = ctx["B"]
    sutun = _ozet_satirlari(b, donem)
    satirlar = [
        ("Ort. kazanç (R)", "ort_kazanc_r", "r"), ("Ort. kayıp (R)", "ort_kayip_r", "r"),
        ("Kâr çarpanı", "pf", "s2"), ("Azami düşüş (R)", "azami_dusus_r", "s1"),
        ("Ort. süre (dk)", "sure_dk", "s0"), ("MAE medyanı (R)", "mae_r", "r"), ("MFE medyanı (R)", "mfe_r", "r"),
        ("Stop uzaklığı medyanı (pip)", "risk_pip", "s1"),
    ]
    govde = [[ad] + [_hucre(m.get(k), f) for _, m in sutun] for ad, k, f in satirlar]
    return _tablo([""] + [s for s, _ in sutun], govde)


def blok_maliyet(u: Uretim, ctx: dict) -> str:
    """Kayma merdiveni (örneklem dışı net R) ve başabaş: dört parite."""
    b = ctx["B"]
    cs = _ciftler(b)
    kademe = sorted({k for c in cs for k in ((b["cift"][c].get("varsayilan") or {}).get("maliyet") or {})}, key=float)
    govde = []
    for k in kademe:
        govde.append([f"{sayi(float(k), 1)} pip"] + [_hucre(((((b["cift"][c].get("varsayilan") or {}).get("maliyet")
                                                              or {}).get(k) or {}).get("oos") or {}).get("beklenti_r"), "r")
                                                      for c in cs])
    govde.append(["Başabaş kayma (pip, dolum başına, bütün dönem)"] +
                 [_hucre((b["cift"][c].get("varsayilan") or {}).get("basabas_kayma_pip"), "s2") for c in cs])
    return _tablo(["Kayma"] + [PARITE[c] for c in cs], govde)


#: Saat değerli parametrelerin kısa etiketi: seçilen kombinasyon tek satırda yazılırken "10:00" tek
#: başına okunmaz (son giriş mi, başlangıç mı?).
SAAT_ETIKET = {"son_giris_londra": "son giriş", "son_giris_et": "son giriş", "baslangic_et": "başlangıç",
               "aralik_sonu_londra": "aralık sonu", "cikis_et": "çıkış"}


def kombinasyon_yaz(p: dict, on: dict) -> str:
    """Bir kombinasyonun okur yazımı, önceden kaydın ızgara sırasıyla (zaman dilimi önce)."""
    sira = list((on.get("izgara") or {}).keys())
    anahtar = sorted(p, key=lambda k: (sira.index(k) if k in sira else 99, k))
    parca = []
    for k in anahtar:
        v = _deger_yaz(p[k], k)
        parca.append(f"{SAAT_ETIKET[k]} {v}" if k in SAAT_ETIKET else
                     (f"{adlar.PARAM.get(k, k)} {v}" if isinstance(p[k], (int, float)) and k != "tf" else v))
    return " · ".join(parca)


def blok_secim(u: Uretim, ctx: dict) -> str:
    """Izgaradan örneklem içinde seçilen kombinasyon, örneklem dışı sonucu ve deflated Sharpe."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        v = b["cift"][c]
        s = v.get("secilen") or {}
        p = v.get("secilen_p") or {}
        govde.append([PARITE[c], kombinasyon_yaz(p, u.ON.get(b.get("aile")) or {}) or "—",
                      _hucre((s.get("is") or {}).get("beklenti_r"), "r"), _hucre((s.get("oos") or {}).get("beklenti_r"), "r"),
                      _hucre((s.get("dsr") or {}).get("dsr"), "s2"),
                      _hucre(s.get("hukum"), "hukum")])
    return _tablo(["Parite", "Seçilen", "İçi (R)", "Dışı (R)", "DSR", "Hüküm"], govde, ["l", "l", "r", "r", "r", "l"])


def blok_wf(u: Uretim, ctx: dict) -> str:
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        w = ((b["cift"][c].get("walk_forward") or {}).get("ozet")) or {}
        govde.append([PARITE[c], _hucre(w.get("n"), "n"), _hucre(w.get("beklenti_r"), "r"),
                      _hucre(w.get("ga_alt"), "r"), _hucre(w.get("sharpe"), "s2")])
    return _tablo(["Parite", "İşlem", "Net R", "%95 alt", "Sharpe"], govde)


def blok_rejim(u: Uretim, ctx: dict) -> str:
    """Yıl ve oynaklık tercili: dört paritenin işlem başına net R'si (bütün dönem)."""
    b = ctx["B"]
    cs = _ciftler(b)
    yillar = sorted({y for c in cs for y in ((b["cift"][c].get("varsayilan") or {}).get("yil") or {})})
    govde = [[y] + [_hucre(((((b["cift"][c].get("varsayilan") or {}).get("yil") or {}).get(y) or {}).get("beklenti_r")),
                           "r") for c in cs] for y in yillar]
    for t in ("düşük", "orta", "yüksek"):
        govde.append([f"oynaklık {t}"] + [_hucre((((b["cift"][c].get("varsayilan") or {}).get("oynaklik") or {})
                                                   .get(t) or {}).get("beklenti_r"), "r") for c in cs])
    return _tablo([""] + [PARITE[c] for c in cs], govde)


def blok_kural(u: Uretim, ctx: dict) -> str:
    """Önceden kaydın ızgarası ve varsayılanı (okur adlarıyla)."""
    b = ctx["B"]
    aile = b.get("aile")
    on = u.ON.get(aile) or {}
    izgara = on.get("izgara") or {}
    v = b.get("varsayilan") or {}
    govde = []
    for k, degerler in izgara.items():
        govde.append([adlar.PARAM.get(k, k), ", ".join(_deger_yaz(x, k) for x in degerler),
                      _deger_yaz(v.get(k), k) if k in v else "—"])
    return _tablo(["Parametre", "Izgara", "Varsayılan"], govde, ["l", "l", "l"])


def _deger_yaz(x, k: str = "") -> str:
    if x is None:
        return "—"
    if k == "tf" or (isinstance(x, int) and k in ("tf",)):
        return f"{x} dk"
    if isinstance(x, float):
        return sayi(x, 3 if x != round(x, 1) else 1)
    return adlar.DEGER.get(str(x), str(x))


GUN_ADI = ["pazartesi", "salı", "çarşamba", "perşembe", "cuma", "cumartesi", "pazar"]


def blok_hukum(u: Uretim, ctx: dict) -> str:
    """Parite başına hüküm: önceden kayıtlı varsayılan, ızgaradan seçilen, maliyet bayrağı, rastgele yüzdelik."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        v = b["cift"][c].get("varsayilan") or {}
        s = b["cift"][c].get("secilen") or {}
        ras = (v.get("rastgele") or {}).get("oos") or {}
        govde.append([PARITE[c], _hucre(v.get("hukum"), "hukum"), _hucre(s.get("hukum"), "hukum"),
                      _hucre(ras.get("yuzdelik"), "s0"), "evet" if v.get("maliyet_yiyor") else "hayır"])
    return _tablo(["Parite", "Varsayılan", "Seçilen", "Rastgele yüzdelik", "Maliyet yiyor"], govde,
                  ["l", "l", "l", "r", "l"])


def blok_kosul_ozet(u: Uretim, ctx: dict, cift: str = "EURUSD") -> str:
    """Koşul değişkenlerinin hükmü (bir paritede): tutan, tutmayan, seçilmeyen. Tutanlar kovasıyla."""
    b = ctx["B"]
    v = ((b.get("cift") or {}).get(cift) or {}).get("varsayilan") or {}
    ks = v.get("kosul") or []
    if not ks:
        return f"_{PARITE[cift]}: koşul analizi için yeterli işlem yok._"
    tut = [k for k in ks if k.get("hukum") == "tuttu"]
    tutma = [k for k in ks if k.get("hukum") == "tutmadi"]
    sec = [k for k in ks if k.get("hukum") == "secilmedi"]
    satir = [f"{PARITE[cift]}, sınanan {len(ks)} değişken: **{len(tut)} tuttu**, {len(tutma)} tutmadı, "
             f"{len(sec)} değişkende örneklem içinde seçilecek kova çıkmadı."]
    for k in tut:
        satir.append(f"- **{adlar.KOSUL.get(k['degisken'], k['degisken'])}** — seçilen kova: "
                     f"{', '.join(k.get('secilen') or [])}; örneklem dışında seçilen {_hucre(k.get('oos_secilen_r'), 'r')} R, "
                     f"tamamlayanı {_hucre(k.get('oos_tamamlayan_r'), 'r')} R.")
    if tutma:
        satir.append(f"- Tutmayanlar: {', '.join(adlar.KOSUL.get(k['degisken'], k['degisken']) for k in tutma)}.")
    return "\n".join(satir)


def blok_ornek(u: Uretim, ctx: dict) -> str:
    """Örnek günlerin anlatımı: figürdeki iki işlemin saatleri, fiyatları ve sonucu (EUR/USD)."""
    e = ctx.get("E") or {}
    satir = []
    for x in e.get("ornek") or []:
        i = x["islem"]
        g = x["gun"]
        y, a, d = (int(p) for p in g.split("-"))
        from datetime import date as _d
        gun_adi = GUN_ADI[_d(y, a, d).weekday()]
        yon = "alış" if i["yon"] > 0 else "satış"
        risk = abs(i["giris_f"] - i["stop"]) * NOKTA["EURUSD"] / 1e-4 if i.get("stop") is not None else None
        parca = [f"**{'Kazanan' if x['etiket'] == 'kazanan' else 'Kaybeden'}** ({tarih_uzun(g)}, {gun_adi}, "
                 f"{x['tf']} dk mum): {yon}."]
        fiyat = sayi(i['giris_f'] * NOKTA['EURUSD'], 5)
        if i.get("sinyal_t") is not None and int(i["sinyal_t"]) == int(i["giris_t"]):
            parca.append(f"Sinyal mumu {saat_tsi(i['sinyal_t'])} TSİ'de kapandı; giriş sonraki dakikanın açılışında, "
                         f"{fiyat}")
        else:
            parca.append((f"Sinyal mumu {saat_tsi(i['sinyal_t'])} TSİ'de kapandı; " if i.get("sinyal_t") is not None
                          else "") + f"giriş {saat_tsi(i['giris_t'])} TSİ'de, {fiyat}")
        parca[-1] += ((f"; stop {sayi(i['stop'] * NOKTA['EURUSD'], 5)} ({sayi(risk, 1)} pip)" if risk else "")
                      + (f", hedef {sayi(i['hedef'] * NOKTA['EURUSD'], 5)}" if i.get("hedef") is not None else "") + ".")
        parca.append(f"Çıkış {saat_tsi(i['cikis_t'])} TSİ'de {sayi(i['cikis_f'] * NOKTA['EURUSD'], 5)}, "
                     f"{adlar.neden_ad(i, u.O['kunye']['gun_sonu_et'])}: {sayi(i['r'], 2, arti=True)} R "
                     f"({sayi(i['pnl_pip'], 1, arti=True)} pip, maliyet dahil).")
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


def blok_basabas(u: Uretim, ctx: dict, cift: str = "EURUSD") -> str:
    """Kontrol listesinin maliyet maddesi: dolum başına başabaş kayma (bütün dönem)."""
    v = (((ctx["B"].get("cift") or {}).get(cift) or {}).get("varsayilan")) or {}
    k = v.get("basabas_kayma_pip")
    if k is None:
        return (f"{PARITE[cift]} için kayma ızgarasının sonunda (dolum başına 2 pip) bile net beklenti artı: maliyet "
                f"bu kuralın sınırlayıcısı değil.")
    if k == 0:
        return f"{PARITE[cift]} için sıfır kaymada (yalnız gerçek makasla) bile net beklenti eksi: maliyet ne olursa olsun."
    return (f"{PARITE[cift]} için makasın üstüne dolum başına {sayi(k, 2)} pip kayma net beklentiyi sıfıra indiriyor "
            f"(bütün dönem). Yürütme maliyetiniz bunun altında değilse kural kâğıt üstünde kalır.")


def _isaret_say(degerler: list) -> tuple[int, int]:
    d = [x for x in degerler if x is not None]
    return sum(1 for x in d if x > 0), len(d)


def blok_oos_cumle(u: Uretim, ctx: dict) -> str:
    """Örneklem dışının tek paragraflık özeti: havuz ve parite parite net R, aralık, işaret sayımı."""
    b = ctx["B"]
    h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
    cs = _ciftler(b)
    pr = [((b["cift"][c].get("varsayilan") or {}).get("oos") or {}) for c in cs]
    arti, n = _isaret_say([p.get("beklenti_r") for p in pr])
    k = u.O["kunye"]
    parca = [f"Örneklem dışında ({tarih(k['dis_baslangic'])} → {tarih(k['bitis'])}) önceden kayıtlı varsayılanın"]
    if h.get("n"):
        parca.append(f"{len(cs)} paritedeki {sayi(h['n'], 0)} işleminin net ortalaması işlem başına "
                     f"{_hucre(h.get('beklenti_r'), 'r')} R (%95 aralığı {_hucre(h.get('ga_alt'), 'r')} / "
                     f"{_hucre(h.get('ga_ust'), 'r')}; isabet {_hucre(h.get('isabet'), 'yz1')}).")
    else:
        parca.append("örneklem dışında hiç işlemi yok.")
    if n:
        ayri = "; ".join(f"{PARITE[c]} {_hucre(p.get('beklenti_r'), 'r')}" for c, p in zip(cs, pr))
        parca.append(f"Parite parite: {ayri} (artı olan parite: {arti} / {n}).")
    brut = h.get("brut_r")
    if brut is not None and h.get("beklenti_r") is not None:
        parca.append(f"Maliyetten önce (orta fiyattan orta fiyata) işlem başına {_hucre(brut, 'r')} R; gerçek "
                     f"makas ve kayma bunun {sayi(brut - h['beklenti_r'], 2)} R'sini götürüyor.")
    return " ".join(parca)


def blok_rastgele_cumle(u: Uretim, ctx: dict) -> str:
    """Rastgele yön sınaması: aynı işlemler, yön yazı tura (EUR/USD ve dört paritenin yüzdeliği)."""
    b = ctx["B"]
    satir = []
    for c in _ciftler(b):
        r = (((b["cift"][c].get("varsayilan") or {}).get("rastgele") or {}).get("oos") or {})
        if r.get("yuzdelik") is not None:
            satir.append(f"{PARITE[c]} {sayi(r['yuzdelik'], 0)}.")
    if not satir:
        return ""
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    return (f"Rastgele yön sınamasında stratejinin örneklem dışı sonucu, aynı giriş ve çıkış dakikalarında yönü yazı "
            f"turayla seçen {sayi(u.ON.get('hukum', {}).get('rastgele_tekrar', 1000), 0)} denemenin dağılımında şu "
            f"yüzdelikte duruyor: {', '.join(satir)} Hüküm kuralının eşiği {esik}. yüzdelik.")


def blok_dsr_cumle(u: Uretim, ctx: dict) -> str:
    """Izgaradan seçimin çoklu sınama düzeltmesi: deneme sayısı, deflated Sharpe (EUR/USD)."""
    b = ctx["B"]
    e = ((b.get("cift") or {}).get("EURUSD") or {}).get("secilen") or {}
    d = e.get("dsr") or {}
    if not d.get("n_deneme"):
        return ""
    return (f"EUR/USD'de ızgaranın {sayi(d['n_deneme'], 0)} kombinasyonu örneklem içinde denendi; en iyisinin "
            f"yıllık Sharpe'ı şansla beklenen en yüksek değerin ({_hucre(d.get('sr0_yillik'), 's2')}) karşısında "
            f"deflated Sharpe olasılığı {_hucre(d.get('dsr'), 's2')} veriyor (1'e yakınsa seçim şansla "
            f"açıklanamaz; 0,95 altı açıklanabilir).")


def blok_wf_cumle(u: Uretim, ctx: dict) -> str:
    b = ctx["B"]
    satir = []
    for c in _ciftler(b):
        w = ((b["cift"][c].get("walk_forward") or {}).get("ozet")) or {}
        if w.get("n"):
            satir.append(f"{PARITE[c]} {_hucre(w.get('beklenti_r'), 'r')} R ({sayi(w['n'], 0)} işlem)")
    if not satir:
        return ""
    ilk = u.ON.get("saglamlik", {}).get("walk_forward_ilk_test_yili", 2020)
    return (f"Yürüyen pencere (her yıl yalnız önceki yılların verisiyle seçip o yılda sınamak, {ilk} → bugün): "
            + "; ".join(satir) + ".")


def blok_rejim_cumle(u: Uretim, ctx: dict, cift: str = "EURUSD") -> str:
    """Yıl ve oynaklık tercilinin betimleyici özeti (bir parite, bütün dönem)."""
    v = (((ctx["B"].get("cift") or {}).get(cift) or {}).get("varsayilan")) or {}
    yil = {y: x.get("beklenti_r") for y, x in (v.get("yil") or {}).items() if x.get("beklenti_r") is not None}
    terc = {t: (x or {}).get("beklenti_r") for t, x in (v.get("oynaklik") or {}).items()}
    if not yil:
        return ""
    arti = sum(1 for x in yil.values() if x > 0)
    eniyi, enkotu = max(yil, key=yil.get), min(yil, key=yil.get)
    s = (f"{PARITE[cift]} için artı yıl: {arti} / {len(yil)}; en iyi yıl {eniyi} ({_hucre(yil[eniyi], 'r')} R), "
         f"en kötü {enkotu} ({_hucre(yil[enkotu], 'r')} R).")
    if all(terc.get(t) is not None for t in ("düşük", "orta", "yüksek")):
        s += (f" Oynaklık tercillerinde (önceki 14 günün ATR yüzdeliği): düşük {_hucre(terc['düşük'], 'r')}, orta "
              f"{_hucre(terc['orta'], 'r')}, yüksek {_hucre(terc['yüksek'], 'r')} R.")
    return s


def blok_hukum_cumle(u: Uretim, ctx: dict) -> str:
    """Hükmün tek cümlesi: ön kaydın kuralı parite başına uygulanır, cümle yalnız sayar (yeni kural yok)."""
    hs = ctx["HS"]
    b = ctx["B"]
    if not hs["parite"]:
        return "Hüküm: ölçülemedi (işlem yok)."
    adlar_ = {h: [PARITE[c] for c in _ciftler(b) if (b["cift"][c].get("varsayilan") or {}).get("hukum") == h]
              for h in ("calisiyor", "zayif", "calismiyor")}
    if hs["calismiyor"] == hs["parite"]:
        ana = f"**Çalışmıyor.** Önceden kayıtlı kural, sınanan {hs['parite']} paritenin hiçbirinde örneklem dışında artı değil."
    elif hs["calisiyor"] == hs["parite"]:
        ana = f"**Çalışıyor.** Önceden kayıtlı kural {hs['parite']} paritenin hepsinde hüküm kuralının üç şartını sağlıyor."
    else:
        parca = []
        for h, ad in (("calisiyor", "çalışıyor"), ("zayif", "zayıf"), ("calismiyor", "çalışmıyor")):
            if adlar_[h]:
                parca.append(f"{', '.join(adlar_[h])}: {ad}")
        bas = "Parite parite" if not hs["calisiyor"] else "Yalnız bir kısmında"
        ana = f"**{bas}.** " + " · ".join(parca) + "."
    if hs["maliyet"]:
        ana += (f" Maliyet bayrağı {hs['maliyet']} paritede yanıyor: brüt sonuç bütün dönemde sıfırdan ayırt "
                f"edilebiliyor ama net sonuç sıfırın altında — kenar varsa makası ödemeye yetmiyor.")
    return ana


def blok_ay_sonu(u: Uretim, ctx: dict) -> str:
    """WM/R fiksingi (ön kayıt [fiks]): aynı kuralın ay sonu ve öbür günlerdeki sonucu, parite parite.
    Ay sonu için ayrı parametre seçilmez; yalnız ayrı raporlanır. Fark Welch t ile (iki yönlü p)."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        a = (b["cift"][c].get("varsayilan") or {}).get("ay_sonu") or {}
        t, o = (a.get("ay_sonu") or {}).get("tum") or {}, (a.get("ay_sonu") or {}).get("oos") or {}
        d, f = (a.get("diger") or {}).get("tum") or {}, (a.get("fark") or {}).get("tum") or {}
        govde.append([PARITE[c], _hucre(t.get("n"), "n"), _hucre(t.get("beklenti_r"), "r"),
                      f"{_hucre(t.get('ga_alt'), 'r')} / {_hucre(t.get('ga_ust'), 'r')}",
                      _hucre(d.get("beklenti_r"), "r"), _hucre(f.get("p"), "s2"),
                      _hucre(o.get("n"), "n"), _hucre(o.get("beklenti_r"), "r")])
    return _tablo(["Parite", "Ay sonu işlem", "Ay sonu R", "%95 aralığı", "Öbür günler R", "Fark p",
                   "Dışı işlem", "Dışı R"], govde, ["l", "r", "r", "r", "r", "r", "r", "r"])


def blok_regresyon(u: Uretim, ctx: dict) -> str:
    """Gün içi momentum (ön kayıt [momentum]): öğleden sonra getirisi ~ Londra ilk mum getirisi, ikisi de
    ATR biriminde; Newey–West standart hatası. Strateji işlemlerinden bağımsız, maliyetsiz, orta fiyat."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        rg = (b["cift"][c].get("varsayilan") or {}).get("regresyon") or {}
        for d, ad in (("is", "içi"), ("oos", "dışı")):
            x = rg.get(d) or {}
            govde.append([PARITE[c], ad, _hucre(x.get("n"), "n"), _hucre(x.get("beta"), "r3"),
                          _hucre(x.get("t_beta"), "r"), _hucre(x.get("p_beta"), "s2"), _hucre(x.get("r2"), "s3"),
                          _hucre(x.get("isaret_isabet"), "yz1")])
    return _tablo(["Parite", "Örneklem", "Gün", "Eğim (β)", "t (HAC)", "p", "R²", "İşaret tutturma"], govde,
                  ["l", "l", "r", "r", "r", "r", "r", "r"])


# ─────────────────────────────────────────────────────────────── çözümlü alıştırma
def blok_pratik_islem(u: Uretim, ctx: dict, birim: str = "orb", etiket: str = "", tur: str = "kazanan") -> str:
    """Bir stratejinin EUR/USD örnek işleminden (örneklem dışının en son kazanan ya da kaybeden işlemi; figürdeki
    örnek günlerin aynısı) çözümlü alıştırma: risk, sonuç ve R; kaymanın R'yi iki yerden değiştirdiği (giriş
    kötüleşir, risk büyür). Sayılar ölçüm dosyasından; çözümün aritmetiği motorun kaydettiği R ile karşılaştırılır,
    tutmazsa üretim düşer."""
    if tur not in ("kazanan", "kaybeden"):
        raise SablonHatasi(f"pratik: tür kazanan ya da kaybeden olmalı: {tur}")
    b = (u.O.get("birim") or {}).get(birim) or {}
    orn = (((b.get("cift") or {}).get("EURUSD") or {}).get("ornek")) or []
    x = next((o for o in orn if o.get("etiket") == tur), None)
    if not x:
        raise SablonHatasi(f"pratik: {birim} için EUR/USD örnek işlemi yok")
    i = x["islem"]
    nk, pip = NOKTA["EURUSD"], 1e-4
    # Aritmetik okurun gördüğü (beş haneye yuvarlı) fiyatlardan kurulur; orta fiyattan gelen yarım nokta
    # yuvarlamada kaybolabilir, motorun kaydıyla fark varsa adıyla yazılır.
    g, s, c = (round(i[k] * nk, 5) for k in ("giris_f", "stop", "cikis_f"))
    yon = i["yon"]
    risk = round(abs(g - s) / pip, 1)
    sonuc = round((c - g) * yon / pip, 1)
    r = sonuc / risk
    if abs(r - i["r"]) > 0.05 or abs(sonuc - i["pnl_pip"]) > 0.1:
        raise SablonHatasi(f"pratik: elle aritmetik motorla tutmuyor ({r:.3f} ↔ {i['r']:.3f})")
    yuvarlama = abs(round(r, 2) - round(i["r"], 2)) >= 0.01
    k = u.O["kunye"]["temel_kayma_pip"]
    k_gs = u.O["kunye"]["gun_sonu_et"]
    limit = i["neden"] in (2, 6)            # hedef limit emirdir: kayma yalnız giriş tarafında
    ek_c = k * (1 if limit else 2)
    risk2, sonuc2 = risk + k, sonuc - ek_c
    yon_ad = "alış" if yon > 0 else "satış"
    ad = adlar.BIRIM[birim][1]
    f5 = lambda v: sayi(v, 5)  # noqa: E731
    soru = (f"**{etiket or 'Alıştırma'} — bir işlemin R'si.** {ad} kuralının EUR/USD'deki örnek günü "
            f"({tarih_uzun(x['gun'])}): {yon_ad}, giriş {f5(g)} ({'ask' if yon > 0 else 'bid'}, kayma dahil), stop "
            f"{f5(s)}, çıkış {f5(c)} ({adlar.neden_ad(i, k_gs)}). (a) Risk kaç pip? (b) İşlem kaç pip ve kaç R "
            f"getirdi? (c) Dolum başına kayma {sayi(k, 1)} pip daha kötü olsaydı sonuç kaç R olurdu?")
    cozum = [f"(a) Risk, yürütülen giriş fiyatından stop'a uzaklıktır: {f5(g)} ile {f5(s)} arası **{sayi(risk, 1)} pip**.",
             f"(b) Sonuç " + (f"{f5(c)} − {f5(g)}" if yon > 0 else f"{f5(g)} − {f5(c)} (satışta giriş eksi çıkış)") +
             f" = **{sayi(sonuc, 1, arti=True)} pip**; R = sonuç / risk = {sayi(sonuc, 1)} / {sayi(risk, 1)} = "
             f"**{sayi(r, 2, arti=True)} R**" + (f" (motorun kaydı {sayi(i['r'], 2, arti=True)} R: fiyatlar burada beş "
                                                 f"haneye yuvarlı)." if yuvarlama else ".") +
             (f" Kayıp riskten büyük, çünkü çıkış stop seviyesinde değil {sayi(abs(c - s) / pip, 1)} pip ötesinde "
              f"doldu: yürütülen fiyat makası ve kaymayı içerir." if i["neden"] in (1, 4, 5) and abs(c - s) >= 0.5 * 1e-5
              and sonuc < 0 else ""),
             f"(c) Kayma iki yerden işler. Giriş {sayi(k, 1)} pip kötüleşir, bu yüzden risk de {sayi(k, 1)} pip büyür "
             f"({sayi(risk2, 1)} pip). Çıkış " + ("bir limit emirdir (hedef) ve kaymaz; sonuç yalnız giriş tarafında "
             if limit else ("bir stop emridir; tetiklenince piyasa emrine döner ve o da kayar: sonuç iki dolumda "
                            if i["neden"] in (1, 4, 5) else "piyasa emridir ve o da kayar; sonuç iki dolumda ")) +
             f"{sayi(ek_c, 1)} pip azalır ({sayi(sonuc2, 1, arti=True)} pip). Yeni R = {sayi(sonuc2, 1)} / "
             f"{sayi(risk2, 1)} = **{sayi(sonuc2 / risk2, 2, arti=True)} R**. " +
             ("Pay küçülür, payda büyür: kazanç R cinsinden, pip cinsinden olduğundan daha hızlı erir; en çok da "
              "stop'u yakın stratejilerde." if sonuc > 0 else
              "Kayıp pip olarak büyür, ama payda da büyüdüğü için R cinsinden daha az: stop'ta kapanan bir işlemin "
              "kaybı 1 R'nin biraz üstünde kalır. Kaymanın asıl bedeli kazanan işlemlerin erimesidir.")]
    return "\n".join([soru, "", "<details>", "<summary>Çözüm</summary>", ""] + [p + "\n" for p in cozum] +
                     ["</details>"])


def blok_pratik_atr(u: Uretim, ctx: dict, birim: str = "momentum", etiket: str = "") -> str:
    """Stop'suz bir kuralın (R birimi girişteki ATR) EUR/USD örnek işleminden çözümlü alıştırma. ATR, motorun
    kaydından (net pip / R) okunur ve soruda verilir; çözüm sonucu okurun gördüğü fiyatlardan kurar ve motorla
    karşılaştırır. Kayma burada paydayı büyütmez: R birimi fiyattan değil oynaklıktan gelir."""
    b = (u.O.get("birim") or {}).get(birim) or {}
    orn = (((b.get("cift") or {}).get("EURUSD") or {}).get("ornek")) or []
    x = next((o for o in orn if o.get("etiket") == "kazanan"), None)
    if not x:
        raise SablonHatasi(f"pratik: {birim} için EUR/USD örnek işlemi yok")
    i = x["islem"]
    if i.get("hedef") is not None or i.get("neden") != 3:
        raise SablonHatasi(f"pratik_atr: {birim} örnek işlemi stop'suz bir zaman çıkışı değil")
    nk, pip = NOKTA["EURUSD"], 1e-4
    g, c = (round(i[k] * nk, 5) for k in ("giris_f", "cikis_f"))
    yon = i["yon"]
    sonuc = round((c - g) * yon / pip, 1)
    if abs(sonuc - i["pnl_pip"]) > 0.1 or not i.get("r"):
        raise SablonHatasi(f"pratik_atr: elle aritmetik motorla tutmuyor ({sonuc} ↔ {i['pnl_pip']})")
    atr = round(i["pnl_pip"] / i["r"], 1)
    r = sonuc / atr
    if abs(r - i["r"]) > 0.05:
        raise SablonHatasi(f"pratik_atr: R tutmuyor ({r:.3f} ↔ {i['r']:.3f})")
    k = u.O["kunye"]["temel_kayma_pip"]
    sonuc2 = sonuc - 2 * k
    ad = adlar.BIRIM[birim][1]
    f5 = lambda v: sayi(v, 5)  # noqa: E731
    yon_ad = "alış" if yon > 0 else "satış"
    soru = (f"**{etiket or 'Alıştırma'} — stop'suz bir kuralda R.** {ad} kuralının EUR/USD'deki örnek günü "
            f"({tarih_uzun(x['gun'])}): {yon_ad}, giriş {saat_tsi(i['giris_t'])} TSİ'de {f5(g)} "
            f"({'ask' if yon > 0 else 'bid'}, kayma dahil), çıkış {saat_tsi(i['cikis_t'])} TSİ'de {f5(c)} "
            f"({adlar.neden_ad(i, u.O['kunye']['gun_sonu_et'])}). Kuralda stop yoktur; R birimi girişteki ATR'dir "
            f"(bu işlemde {sayi(atr, 1)} pip). (a) İşlem kaç pip getirdi? (b) Kaç R? (c) Dolum başına kayma "
            f"{sayi(k, 1)} pip daha kötü olsaydı?")
    cozum = [f"(a) " + (f"{f5(c)} − {f5(g)}" if yon > 0 else f"{f5(g)} − {f5(c)} (satışta giriş eksi çıkış)") +
             f" = **{sayi(sonuc, 1, arti=True)} pip**.",
             f"(b) R = sonuç / ATR = {sayi(sonuc, 1)} / {sayi(atr, 1)} = **{sayi(r, 2, arti=True)} R**.",
             f"(c) İki dolum da piyasa emridir ve ikisi de kayar: sonuç {sayi(2 * k, 1)} pip azalır "
             f"({sayi(sonuc2, 1, arti=True)} pip). Payda değişmez, çünkü R birimi stop uzaklığı değil oynaklıktır: "
             f"yeni R = {sayi(sonuc2, 1)} / {sayi(atr, 1)} = **{sayi(sonuc2 / atr, 2, arti=True)} R**. Stop'lu bir "
             f"kuralda kayma riski de büyütür; burada yalnız sonucu küçültür."]
    return "\n".join([soru, "", "<details>", "<summary>Çözüm</summary>", ""] + [p_ + "\n" for p_ in cozum] +
                     ["</details>"])


# ─────────────────────────────────────────────────────────────── veri ve takvim blokları
def _kalite(u: Uretim) -> dict:
    return ((u.O.get("veri") or {}).get("kalite")) or {}


def blok_veri(u: Uretim, ctx: dict) -> str:
    """Veri denetiminin parite parite özeti (kalite raporu): kapsam, tatil, makas, sıçrama adayı, çapraz sınama."""
    govde = []
    for c in PARITE:
        k = _kalite(u).get(c)
        if not k:
            continue
        kp, mk_, sc, cp = k.get("kapsam") or {}, k.get("makas") or {}, k.get("sicrama") or {}, k.get("capraz") or {}
        govde.append([PARITE[c], _hucre(k.get("satir"), "n"), _hucre(kp.get("normal_gun_kapsam_yuzde"), "s1"),
                      _hucre(len(kp.get("tatil_gunleri") or []), "n"), _hucre(mk_.get("medyan_pip"), "s1"),
                      _hucre(mk_.get("p95_pip"), "s1"),
                      _hucre((mk_.get("sifir_kapanis") or 0) + (mk_.get("negatif_kapanis") or 0), "n"),
                      _hucre(sc.get("aday"), "n"), _hucre(cp.get("tam_esit_yuzde"), "s1")])
    if not govde:
        return "_Veri denetimi henüz yok._"
    return _tablo(["Parite", "Dakika", "Kapsam, normal gün (%)", "Tatil günü", "Makas medyanı (pip)", "Makas p95",
                   "Sıfır/eksi makas", "Sıçrama adayı", "Saatlik çapraz sınama (%)"], govde,
                  ["l"] + ["r"] * 8)


def blok_haber_makas(u: Uretim, ctx: dict, cift: str = "EURUSD") -> str:
    """Haber dakikalarında makas (bir parite): olay saatine göre seçili dakikalarda medyan kapanış makası, zirve
    dakikası ve zirvenin aynı dakikadaki olaysız günlere göre katı. Dakika, 1 dakikalık mumun BAŞLANGICIDIR ve değer o
    mumun kapanışındaki makastır: −1 açıklamadan önceki son kotasyon, 0 açıklamadan bir dakika sonrası."""
    hm = (_kalite(u).get(cift) or {}).get("haber_makasi") or {}
    if not hm:
        return f"_{PARITE[cift]} için haber makası ölçülmedi._"
    dk_sec = [-5, -2, -1, 0, 1, 5, 15]
    govde = []
    for o in [x for x in OLAY_SIRA if x in hm]:
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
    return _tablo(bas, govde, ["l"] + ["r"] * (len(bas) - 1))


def blok_haber_makas_cumle(u: Uretim, ctx: dict, cift: str = "EURUSD") -> str:
    """Haber makasının tek cümlesi (giriş dersi; tablo haber dersinde): zirve dakikası ve olaysız güne göre katın
    olaylar arasındaki aralığı."""
    hm = (_kalite(u).get(cift) or {}).get("haber_makasi") or {}
    z = [(o, (hm[o].get("zirve") or {})) for o in OLAY_SIRA if o in hm and (hm[o].get("zirve") or {}).get("oran")]
    if not z:
        return f"{PARITE[cift]} için haber makası ölçülmedi."
    dks = {v["dk"] for _, v in z}
    nerede = ("açıklamadan önceki son dakikada" if dks == {-1} else
              "açıklamadan önceki son dakikada (olayların çoğunda)" if
              sum(1 for _, v in z if v["dk"] == -1) * 2 > len(z) else "açıklama çevresinde")
    lo = min(z, key=lambda kv: kv[1]["oran"])
    hi = max(z, key=lambda kv: kv[1]["oran"])
    return (f"{PARITE[cift]}'de makas en geniş hâline {nerede} gelir ve o dakikada aynı saatin olaysız günlerinin "
            f"{sayi(lo[1]['oran'], 1)} katı ({adlar.OLAY.get(lo[0], lo[0])}) ile {sayi(hi[1]['oran'], 1)} katı "
            f"({adlar.OLAY.get(hi[0], hi[0])}) arasındadır.")


def blok_haber_makas_ozet(u: Uretim, ctx: dict) -> str:
    """Bütün pariteler: her olayda zirve makası (pip) ve olaysız güne göre katı."""
    govde, olaylar = [], []
    for c in PARITE:
        hm = (_kalite(u).get(c) or {}).get("haber_makasi") or {}
        olaylar += [o for o in OLAY_SIRA if o in hm and o not in olaylar]
    olaylar = [o for o in OLAY_SIRA if o in olaylar]
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
    return _tablo(["Parite"] + [adlar.OLAY.get(o, o) for o in olaylar], govde, ["l"] + ["r"] * len(olaylar))


BOLGE_AD = {"America/New_York": "New York", "Europe/Berlin": "Frankfurt", "Europe/London": "Londra"}
SINAMA_AD = [("dogrulandi", "doğrulandı"), ("sessiz", "sessiz"), ("celiski", "çelişki"),
             ("degerlendirilemedi", "değerlendirilemedi")]


def blok_takvim(u: Uretim, ctx: dict) -> str:
    """Haber takviminin olay başına özeti: sayı, dönem, yerel saat(ler), kaynak, fiyat sınamasının hükmü."""
    t = (u.O.get("takvim") or {})
    sayim = t.get("sayim") or {}
    oz = ((t.get("sinama") or {}).get("ozet")) or {}
    govde = []
    for o in [x for x in OLAY_SIRA if x in sayim]:
        v = sayim[o]
        saat = "; ".join(f"{k.split(' ', 1)[0]} {BOLGE_AD.get(k.split(' ', 1)[1], k.split(' ', 1)[1])} ({sayi(n, 0)})"
                         for k, n in sorted((v.get("saat") or {}).items(), key=lambda kv: -kv[1]))
        s = oz.get(o) or {}
        sin = " · ".join(f"{s[k]} {ad}" for k, ad in SINAMA_AD if s.get(k)) or (
            "sınanmadı (konuşma tek dakikada sıçrama yapmaz; yalnız bilgi)" if s.get("basin_bilgi") else "—")
        govde.append([adlar.OLAY.get(o, o), _hucre(v.get("toplam"), "n"),
                      f"{tarih(v['ilk'])} → {tarih(v['son'])}" if v.get("ilk") else "—", saat or "—",
                      ", ".join(v.get("kaynak") or []) or "—", sin])
    if not govde:
        return "_Takvim yok._"
    return _tablo(["Olay", "Sayı", "Dönem", "Yerel saat (olay sayısı)", "Kaynak", "Fiyat sınaması"], govde,
                  ["l", "r", "l", "l", "l", "l"])


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
    return _tablo(["Parite", "Yıl", "Tamamlanan yıl", "İşlem günü", "Dolu gün", "İnmeyen gün", "Dakika"], govde,
                  ["l"] + ["r"] * 6)


# ─────────────────────────────────────────────────────────────── haber bloklari
OLAY_SIRA = ["NFP", "CPI", "FOMC_karar", "FOMC_basin", "ECB_karar", "ECB_basin", "BoE_karar"]
KOVA_SIRA = ["<0,5", "0,5–1", "1–2", ">2"]
UYUM_ADI = {"aynı": "öncesi trendle aynı yönde", "ters": "öncesi trende ters", "belirsiz": "belirsiz (trend ya da ilk mum sıfır)"}


def _devam(u: Uretim) -> dict:
    return ((u.O.get("haber") or {}).get("devam")) or {}


def _boyut_sira(boyut: str, degerler: set) -> list[str]:
    if boyut == "olay":
        return [o for o in OLAY_SIRA if o in degerler]
    if boyut == "kova":
        return [k for k in KOVA_SIRA if k in degerler]
    if boyut == "tf":
        return sorted(degerler, key=int)
    if boyut == "cift":
        return [c for c in PARITE if c in degerler]
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
    degerler = _boyut_sira(boyut, {h["deger"] for h in hucre})
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
    return _tablo([bas, "Ufuk", "Olay sayısı", "Kırılım", "Fade", "Hüküm"], govde, ["l", "l", "r", "r", "r", "l"])


def blok_devam_cumle(u: Uretim, ctx: dict) -> str:
    """Devam tablosunun aile özeti: sınama sayısı, hüküm sayımı, kural."""
    d = _devam(u)
    if not d.get("hucre"):
        return "Devam tablosu ölçülemedi."
    k = d.get("kural") or {}
    say = d.get("hukum_sayimi") or {}
    parca = ", ".join(f"{v} hücrede {ad}" for ad, v in sorted(say.items(), key=lambda kv: -kv[1]))
    boyutlar = []
    for h in d["hucre"]:
        if h.get("boyut") not in boyutlar:
            boyutlar.append(h.get("boyut"))
    ad = {"olay": "olay", "kova": "ilk mum büyüklüğü", "trend_uyum": "haber öncesi trend", "tf": "mum uzunluğu",
          "cift": "parite", "olay_kova": "olay × ilk mum büyüklüğü"}
    sira = [b for b in ad if b in boyutlar] + [b for b in boyutlar if b not in ad]
    tablo = ", ".join(ad.get(b, b) for b in sira)
    n_hucre = len(d["hucre"])
    return (f"Aşağıdaki {sayi(len(sira), 0)} tablonun ({tablo}) {sayi(n_hucre, 0)} hücresi ve her hücrenin iki yönü "
            f"tek bir sınama ailesidir: {sayi(d.get('sinama_sayisi', 0), 0)} tek yönlü t sınaması. Hüküm, "
            f"Benjamini–Hochberg ile düzeltilmiş q değeri {sayi(k.get('fdr_q', 0.1), 2)} altında ve hücrede en az "
            f"{k.get('asgari_olay', 20)} olay varsa verilir. Sonuç: {parca}.")


def blok_haber_kirilim(u: Uretim, ctx: dict, boyut: str = "olay") -> str:
    """Bir haber stratejisinin işlemleri olaya (ya da ilk mum kovasına) göre, dört paritenin birleşimi.
    Havuz ortalaması parite ortalamalarının işlem sayısıyla ağırlıklı ortalamasıdır (bütün işlemlerin ortalaması)."""
    b = ctx["B"]
    top: dict = {}
    for c in _ciftler(b):
        hk = ((b["cift"][c].get("varsayilan") or {}).get("haber_kirilim") or {}).get(boyut) or {}
        for deger, x in hk.items():
            for d in ("tum", "oos"):
                y = x.get(d) or {}
                if y.get("n") and y.get("beklenti_r") is not None:
                    t = top.setdefault(deger, {}).setdefault(d, [0, 0.0, set()])
                    t[0] += y["n"]
                    t[1] += y["n"] * y["beklenti_r"]
                    t[2].add(c)
    if not top:
        return "_Olay kırılımı yok._"
    govde = []
    for deger in _boyut_sira(boyut, set(top)):
        tum, oos = top[deger].get("tum"), top[deger].get("oos")
        govde.append([_boyut_ad(boyut, deger), ", ".join(PARITE[c] for c in PARITE if tum and c in tum[2]) or "—",
                      _hucre(tum[0] if tum else None, "n"), _hucre(tum[1] / tum[0] if tum else None, "r"),
                      _hucre(oos[0] if oos else None, "n"), _hucre(oos[1] / oos[0] if oos else None, "r")])
    bas = {"olay": "Olay", "kova": "İlk mum / ATR", "trend_uyum": "Haber öncesi trend"}.get(boyut, boyut)
    return _tablo([bas, "Pariteler", "İşlem", "Net R", "Dışı işlem", "Dışı R"], govde,
                  ["l", "l", "r", "r", "r", "r"])


def blok_fomc(u: Uretim, ctx: dict) -> str:
    """FOMC karar (14:00 → 14:30) ↔ basın toplantısı (14:30 → 15:30) hareketi, parite parite."""
    govde = []
    for c, h in sorted(((u.O.get("haber") or {}).get("cift") or {}).items(), key=lambda kv: list(PARITE).index(kv[0])):
        oz = ((h or {}).get("fomc") or {}).get("ozet") or {}
        b60 = oz.get("basin_60") or {}
        if not b60:
            continue
        dn = b60.get("donus") or {}
        kb = b60.get("karar_buyukluk") or {}
        govde.append([PARITE[c], _hucre(oz.get("n"), "n"),
                      f"{_hucre(dn.get('oran'), 'yz0')} ({_hucre(dn.get('alt'), 'yz0')}–{_hucre(dn.get('ust'), 'yz0')})",
                      f"{_hucre(b60.get('korelasyon'), 'r')} ({_hucre(b60.get('korelasyon_alt'), 'r')} / "
                      f"{_hucre(b60.get('korelasyon_ust'), 'r')})"]
                     + [(f"{_hucre(kb[k].get('oran'), 'yz0')} ({sayi(kb[k].get('n'), 0)})" if (kb.get(k) or {}).get("n")
                         else "—") for k in ("<0,5", "0,5–1", ">1")])
    if not govde:
        return "_FOMC karar ↔ basın toplantısı ölçülemedi (basın toplantısı saati olan toplantı yok)._"
    return _tablo(["Parite", "Toplantı", "Dönüş oranı (%95)", "Korelasyon (%95)", "Karar <0,5 ATR", "0,5–1",
                   ">1"], govde, ["l", "r", "r", "r", "r", "r", "r"])


def blok_fomc_cumle(u: Uretim, ctx: dict) -> str:
    """FOMC tablosunun okunuşu: dönüş oranı yazı turadan, ilinti sıfırdan ayırt ediliyor mu; ve iki pencerenin
    hareket büyüklüğü (pencereler farklı uzunlukta: karar 30 dk, basın 60 dk — rastgele yürüyüşte √2 kat beklenir)."""
    satir = []
    for c, h in sorted(((u.O.get("haber") or {}).get("cift") or {}).items(), key=lambda kv: list(PARITE).index(kv[0])):
        b60 = (((h or {}).get("fomc") or {}).get("ozet") or {}).get("basin_60") or {}
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
             ("Dört paritenin hiçbirinde" if n == 4 else f"{sayi(n, 0)} paritenin hiçbirinde"))
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
        ornek = next((x for x in satir if x[0] == "EURUSD"), satir[0])
        b = ornek[2]
        oran_ornek = b["ort_mutlak_basin_atr"] / b["ort_mutlak_karar_atr"]
        cumle.append(f"Hareketin büyüklüğü: {PARITE[ornek[0]]}'de basın toplantısının ilk saatindeki ortalama mutlak "
                     f"hareket {sayi(b['ort_mutlak_basin_atr'], 2)}, kararın ilk yarım saatindeki "
                     f"{sayi(b['ort_mutlak_karar_atr'], 2)} günlük ATR (oran {sayi(oran_ornek, 2)}). Basın penceresi iki kat uzun "
                     f"olduğu için oran "
                     f"tek başına bir şey söylemez: fiyat rastgele yürüseydi bile iki kat uzun pencerede "
                     f"{sayi(kok2, 2)} kat hareket beklenirdi. "
                     + (f"{'Dört paritenin dördünde' if len(alt) == n == 4 else ad(alt) + ' paritesinde'} oran bunun "
                        f"altında: dakika başına kararın yarım saati basın toplantısının ilk saatinden daha hareketli."
                        if alt else "Oran hiçbir paritede bunun altında değil: basın toplantısı dakika başına da "
                                    "kararın yarım saati kadar hareketli.")
                     + (f" {ad([c for c, _ in oran if c not in alt])} paritesinde değil." if alt and len(alt) < len(oran)
                        else ""))
    return " ".join(cumle)


def hukum_sayim_yaz(b: dict) -> str:
    """Parite başına hükümlerin sayımı: "2 zayıf · 2 çalışmıyor" (sıra: çalışıyor, zayıf, çalışmıyor, ölçülemedi)."""
    say: dict = {}
    for c in _ciftler(b):
        h = (b["cift"][c].get("varsayilan") or {}).get("hukum") or "olculemedi"
        say[h] = say.get(h, 0) + 1
    return " · ".join(f"{say[h]} {adlar.HUKUM[h]}" for h in ("calisiyor", "zayif", "calismiyor", "olculemedi")
                      if say.get(h)) or "—"


def blok_ders_ozet(u: Uretim, ctx: dict, *birimler: str) -> str:
    """Dersin stratejileri yan yana: havuzun örneklem dışı net R'si ve aralığı, parite hükümlerinin sayımı,
    maliyet bayrağı ve EUR/USD'nin başabaş kayması. Birim verilmezse bu derste işlenenler."""
    liste = list(birimler) or list(u.birimler)
    if liste == ["hepsi"]:
        liste = _butun_birimler(u)
    govde = []
    for bid in liste:
        b = (u.O.get("birim") or {}).get(bid)
        if not b:
            continue
        h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        maliyet = sum(1 for c in _ciftler(b) if (b["cift"][c].get("varsayilan") or {}).get("maliyet_yiyor"))
        e = ((b.get("cift") or {}).get("EURUSD") or {}).get("varsayilan") or {}
        govde.append([adlar.BIRIM[bid][1], _hucre(h.get("n"), "n"), _hucre(h.get("beklenti_r"), "r"),
                      f"{_hucre(h.get('ga_alt'), 'r')} / {_hucre(h.get('ga_ust'), 'r')}", hukum_sayim_yaz(b),
                      str(maliyet) if maliyet else "—", _basabas_yaz(e),
                      _hucre((e.get("oos") or {}).get("risk_pip"), "s1")])
    if not govde:
        return "_Özet için strateji yok._"
    return (_tablo(["Strateji", "Dışı işlem (havuz)", "Dışı net R", "%95 aralığı", "Parite hükümleri",
                    "Maliyet yiyor", "Başabaş kayma, EUR/USD (pip)", "R birimi medyanı, EUR/USD (pip)"], govde,
                   ["l", "r", "r", "r", "l", "r", "r", "r"]) +
            "\n\n_Başabaş kayma: net beklentiyi sıfıra indiren dolum başına kayma (bütün dönem); sıfır kaymada bile "
            "eksiyse parantezde sıfır kaymadaki işlem başına net R. R birimi: stop'lu kurallarda girişten stop'a uzaklık, stop'suz "
            "kurallarda girişteki ATR. Maliyet yiyor: brüt sonucu sıfırdan ayırt edilen ama net sonucu eksi olan "
            "parite sayısı._")


def _basabas_yaz(e: dict) -> str:
    """Başabaş kaymanın okur yazımı: ızgarada kesişim · sıfırda bile eksi (sıfır kaymada işlem başına net R) ·
    ızgaranın üstünde."""
    k = e.get("basabas_kayma_pip")
    if k is None:
        return "ızgaranın üstünde" if e.get("oos") else "—"
    if k == 0:
        ek = e.get("basabas_sifir_r")
        return f"sıfırda bile eksi ({_hucre(ek, 'r')} R)" if ek is not None else "sıfırda bile eksi"
    if k < 0.005:
        return "&lt;0,01"
    return _hucre(k, "s2")


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
            satir.append(f"{_hucre(o.get('beklenti_r'), 'r')} · {adlar.HUKUM.get(v.get('hukum') or 'olculemedi')}"
                         if v else "—")
        h = ((b.get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}
        satir.append(_hucre(h.get("beklenti_r"), "r"))
        govde.append(satir)
    if not govde:
        return "_Strateji yok._"
    return _tablo(["Strateji"] + list(PARITE.values()) + ["Havuz"], govde, ["l"] + ["r"] * (len(PARITE) + 1))


def _hukum_sayimi_hepsi(u: Uretim) -> dict:
    say = {"calisiyor": 0, "zayif": 0, "calismiyor": 0, "olculemedi": 0, "maliyet": 0, "parite": 0}
    kural = {"calisiyor": set(), "zayif": set()}
    for bid in _butun_birimler(u):
        b = u.O["birim"][bid]
        for c in _ciftler(b):
            v = (b["cift"][c].get("varsayilan") or {})
            h = v.get("hukum") or "olculemedi"
            say[h] = say.get(h, 0) + 1
            say["parite"] += 1
            say["maliyet"] += 1 if v.get("maliyet_yiyor") else 0
            if h in kural:
                kural[h].add(bid)
    return {"say": say, "kural": kural, "birim": len(_butun_birimler(u))}


def blok_genel_hukum(u: Uretim, ctx: dict) -> str:
    """Bütün kuralların hüküm sayımı (strateji × parite) ve havuzda aralığı sıfırın üstünde kalan kurallar."""
    g = _hukum_sayimi_hepsi(u)
    s_, k = g["say"], g["kural"]
    parca = [f"{sayi(g['birim'], 0)} kural ve {sayi(s_['parite'], 0)} kural–parite bileşiminde önceden kaydın "
             f"hükmü: {sayi(s_['calisiyor'], 0)} çalışıyor, {sayi(s_['zayif'], 0)} zayıf, "
             f"{sayi(s_['calismiyor'], 0)} çalışmıyor" +
             (f", {sayi(s_['olculemedi'], 0)} ölçülemedi" if s_["olculemedi"] else "") + "."]
    for h, ad in (("calisiyor", "çalışıyor"), ("zayif", "zayıf")):
        if k[h]:
            parca.append(f"En az bir paritede {ad}: " + ", ".join(adlar.BIRIM[b][1] for b in _butun_birimler(u)
                                                              if b in k[h]) + ".")
    pozitif = [b for b in _butun_birimler(u)
               if (((u.O["birim"][b].get("havuz") or {}).get("varsayilan") or {}).get("oos") or {}).get("ga_alt") is not None
               and u.O["birim"][b]["havuz"]["varsayilan"]["oos"]["ga_alt"] > 0]
    parca.append("Havuzda %95 aralığının alt ucu sıfırın üstünde kalan kural: " +
                 (", ".join(adlar.BIRIM[b][1] for b in pozitif) if pozitif else "yok") + ".")
    if s_["maliyet"]:
        parca.append(f"Maliyet bayrağı {sayi(s_['maliyet'], 0)} bileşimde yanıyor: brüt sonuç sıfırdan ayırt "
                     f"ediliyor, net sonuç eksi.")
    return " ".join(parca)


def blok_maliyet_ozet(u: Uretim, ctx: dict) -> str:
    """Parite parite: örneklem dışında brüt ve dört kayma kademesinde net beklentisi artı olan kural sayısı."""
    kademe = [str(x) for x in (u.O["kunye"].get("kayma_pip") or [0.0, 0.5, 1.0, 2.0])]
    govde = []
    for c in PARITE:
        n = brut = 0
        net = {kk: 0 for kk in kademe}
        for bid in _butun_birimler(u):
            v = ((u.O["birim"][bid].get("cift") or {}).get(c) or {}).get("varsayilan") or {}
            o = v.get("oos") or {}
            if not o.get("n"):
                continue
            n += 1
            brut += 1 if (o.get("brut_r") or 0) > 0 else 0
            for kk in kademe:
                x = (((v.get("maliyet") or {}).get(kk) or {}).get("oos") or {}).get("beklenti_r")
                net[kk] += 1 if (x is not None and x > 0) else 0
        if n:
            govde.append([PARITE[c], _hucre(n, "n"), _hucre(brut, "n")] + [_hucre(net[kk], "n") for kk in kademe])
    if not govde:
        return "_Maliyet ölçülmedi._"
    return _tablo(["Parite", "Kural", "Brüt artı"] + [f"Net artı, kayma {sayi(float(kk), 1)}" for kk in kademe],
                  govde, ["l"] + ["r"] * (2 + len(kademe)))


def blok_rastgele_ozet(u: Uretim, ctx: dict) -> str:
    """Parite parite: rastgele yön dağılımında örneklem dışı sonucu eşiğin (95. yüzdelik) üstünde kalan kural sayısı."""
    esik = u.ON.get("hukum", {}).get("rastgele_esik_yuzdelik", 95)
    parca, eksi = [], []
    for c in PARITE:
        n = ust = 0
        adlar_ = []
        for bid in _butun_birimler(u):
            v = ((u.O["birim"][bid].get("cift") or {}).get(c) or {}).get("varsayilan") or {}
            r = ((v.get("rastgele") or {}).get("oos") or {})
            if r.get("yuzdelik") is None:
                continue
            n += 1
            if r["yuzdelik"] >= esik:
                ust += 1
                adlar_.append(adlar.BIRIM[bid][1])
                net = (v.get("oos") or {}).get("beklenti_r")
                if net is not None and net <= 0:
                    ort = r.get("ort")
                    eksi.append(f"{adlar.BIRIM[bid][1]} ({PARITE[c]}: kendisi {sayi(net, 2, arti=True)} R"
                                + (f", rastgele yönün ortalaması {sayi(ort, 2, arti=True)} R" if ort is not None else "")
                                + ")")
        if n:
            parca.append(f"{PARITE[c]}: {sayi(ust, 0)} / {sayi(n, 0)}" + (f" ({', '.join(adlar_)})" if adlar_ else ""))
    if not parca:
        return ""
    s = (f"Örneklem dışı sonucu rastgele yön dağılımının {esik}. yüzdeliğinin üstünde kalan kural sayısı — "
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
    govde.append(["**Toplam**", _hucre(top["sinanan"], "n"), _hucre(top["tuttu"], "n")] +
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
    t = {k: 0 for k in ("bilesim", "brut_arti", "brut_arti_sifir_eksi", "brut_arti_net_eksi", "rastgele_n",
                        "rastgele_ust", "arti_n", "arti_rastgele_alt", "dsr_n", "dsr_ust")}
    for b in (O.get("birim") or {}).values():
        for v in (b.get("cift") or {}).values():
            va = v.get("varsayilan") or {}
            o = va.get("oos") or {}
            if not o.get("n"):
                continue
            t["bilesim"] += 1
            brut, net = o.get("brut_r"), o.get("beklenti_r")
            m0 = ((((va.get("maliyet") or {}).get("0.0") or {}).get("oos")) or {}).get("beklenti_r")
            if brut is not None and brut > 0:
                t["brut_arti"] += 1
                t["brut_arti_sifir_eksi"] += m0 is not None and m0 <= 0
                t["brut_arti_net_eksi"] += net is not None and net <= 0
            r = ((va.get("rastgele") or {}).get("oos")) or {}
            if r.get("yuzdelik") is not None:
                t["rastgele_n"] += 1
                t["rastgele_ust"] += r["yuzdelik"] >= esik
                if net is not None and net > 0:
                    t["arti_n"] += 1
                    t["arti_rastgele_alt"] += r["yuzdelik"] < esik
            d = (((v.get("secilen") or {}).get("dsr")) or {}).get("dsr")
            if d is not None:
                t["dsr_n"] += 1
                t["dsr_ust"] += d >= 0.95
    t = {k: int(v) for k, v in t.items()}

    def oran(a: str, b_: str):
        return t[a] / t[b_] if t[b_] else None
    t.update({"makas_brut_oran": oran("brut_arti_sifir_eksi", "brut_arti"),
              "net_eksi_brut_oran": oran("brut_arti_net_eksi", "brut_arti"),
              "rastgele_ust_oran": oran("rastgele_ust", "rastgele_n"),
              "rastgele_beklenen": round(t["rastgele_n"] * (100 - esik) / 100),
              "rastgele_binom_p": _binom_ust_p(t["rastgele_ust"], t["rastgele_n"], (100 - esik) / 100),
              "arti_rastgele_alt_oran": oran("arti_rastgele_alt", "arti_n"),
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
          f"(%{sayi(100 * t['tuttu'] / t['sinanan'], 0)}) örneklem dışı ölçütü geçti.")
    if not t["ters_sinanan"]:
        return s1 + " Ters seçim bu ölçümde yok."
    p_ = t["p"]
    s2 = (f" Örneklem içinde en kötü kovalar seçilseydi aynı ölçüt {sayi(t['ters_sinanan'], 0)} sınamanın "
          f"{sayi(t['ters_tuttu'], 0)} tanesinde (%{sayi(100 * t['ters_tuttu'] / t['ters_sinanan'], 0)}) geçerdi. "
          f"İki seçimden yalnız birinin tuttuğu bileşimlerde gerçek seçim {sayi(t['a'], 0)}, ters seçim "
          f"{sayi(t['b'], 0)} kez tuttu (kesin McNemar p {sayi(p_, 2)}).")
    if t["ayirt"]:
        s3 = (" Gerçek seçim ters seçimden daha sık tutuyor: örneklem içinde iyi görünen kovaların bir kısmı örneklem "
              "dışında da iyi. Hangisinin tuttuğu yine tek tek okunmalıdır.")
    elif t["ters_ustun"]:
        s3 = (" Ters seçim gerçek seçimden daha sık tutuyor: örneklem içindeki kova sıralaması örneklem dışında "
              "sistematik olarak tersine dönüyor. Bu kurallarda bir koşula göre işlem seçmek, toplu olarak, örneklem "
              "dışında daha kötü kovayı seçmek demekti; tek tek 'tuttu' hücreleri bir karar kuralı değildir. "
              "Bileşimler bağımsız değildir (aynı kuralın değişkenleri aynı işlemleri paylaşır), p bir ölçüdür.")
    else:
        s3 = (" Gerçek seçim ters seçimden ayırt edilemiyor: tutan koşulların çoğu, gürültünün örneklem dışında da "
              "sıfırın üstünde kalabilmesiyle açıklanır. Tek tek 'tuttu' hücreleri bir karar kuralı değildir.")
    return s1 + s2 + s3


def blok_havuz_cumle(u: Uretim, ctx: dict) -> str:
    """Havuzun (aynı kural bütün paritelerde birlikte) örneklem dışı hükmü ve örneklem içi karşılığı.
    Hüküm kuralı değil, aralığın okunuşu: aralık sıfırın üstünde mi, sıfırı kapsıyor mu, ortalama eksi mi."""
    b = ctx["B"]
    h = ctx.get("H") or {}
    oos, ic = h.get("oos") or {}, h.get("is") or {}
    n_p = len(_ciftler(b))
    r, alt = oos.get("beklenti_r"), oos.get("ga_alt")
    if r is None or not oos.get("n"):
        return "Havuz örneklem dışında ölçülemedi (işlem yok)."
    if r > 0 and alt is not None and alt > 0:
        s = (f"Havuzun örneklem dışı aralığı sıfırın üstünde: kuralın {n_p} paritede birlikte, maliyetten sonra "
             f"bir kenarı var.")
    elif r > 0:
        s = (f"Havuzun örneklem dışı ortalaması sıfırın üstünde ama aralığı sıfırı kapsıyor: ortalama bu örneklem "
             f"büyüklüğünde şanstan ayırt edilemiyor.")
    else:
        s = f"Havuzun örneklem dışı ortalaması sıfırın altında: kural maliyetten sonra {n_p} paritede birlikte kaybettiriyor."
    if ic.get("n"):
        k = u.O["kunye"]
        s += (f" Örneklem içinde ({k['baslangic'][:4]}–{k['ic_bitis'][:4]}) {sayi(ic['n'], 0)} işlemde işlem başına {_hucre(ic.get('beklenti_r'), 'r')} R "
              f"(%95 aralığı {_hucre(ic.get('ga_alt'), 'r')} / {_hucre(ic.get('ga_ust'), 'r')}).")
    return s


def blok_sonuclar(u: Uretim, ctx: dict) -> str:
    """Bir stratejinin standart sonuç dizisi: aynı düzen her stratejide, böylece stratejiler yan yana okunur.
    Yorum bu dizinin ARKASINA strateji şablonunda yazılır."""
    b = ctx["B"]
    k = u.O["kunye"]
    kisa = adlar.BIRIM[ctx["BID"]][1]
    p = [f"**Birikimli sonuç.** Önceden kayıtlı varsayılanın {len(_ciftler(b))} paritede ve havuzda birikimli net R'si; gri alan "
         f"örneklem dışı ({tarih(k['dis_baslangic'])} →).",
         "", blok_sekil(u, ctx, "egri", f"Birikimli net R ve düşüş — {kisa}"), "", blok_oos_cumle(u, ctx), "",
         blok_sonuc(u, ctx, "oos"), "",
         f"_Önceden kayıtlı varsayılan, örneklem dışı. Net: gerçek makas ve dolum başına "
         f"{sayi(k['temel_kayma_pip'], 1)} pip kayma dahil. Havuz: aynı kural dört paritede birlikte; Sharpe "
         f"havuzda günlük R toplamından._", "",
         "**İşlemlerin anatomisi.** Kazanç ve kayıpların büyüklüğü, işlemin süresi ve işlem sırasında gidilen en kötü "
         "(MAE) ve en iyi (MFE) nokta; ikisi de girişteki risk biriminde.", "", blok_ayrinti(u, ctx, "oos"), "",
         "**Mum uzunluğu.** Aynı kural 5, 15 ve 60 dakikalık mumlarla; öbür parametreler önceden kayıtlı varsayılanda.",
         "", blok_sekil(u, ctx, "tf", f"Zaman dilimi kıyası — {kisa}"), "",
         f"**Izgara ve seçim.** Önceden kaydın bütün kombinasyonları örneklem içinde ({k['baslangic'][:4]}–"
         f"{k['ic_bitis'][:4]}) denendi; her paritede "
         "en yüksek örneklem içi Sharpe'lı kombinasyon seçildi ve örneklem dışında sınandı.", "",
         blok_sekil(u, ctx, "izgara", f"Parametre ızgarası — {kisa}"), "", blok_secim(u, ctx), "",
         blok_dsr_cumle(u, ctx) + " " + blok_wf_cumle(u, ctx), "", blok_wf(u, ctx), "",
         "**Maliyet.** Örneklem dışında net beklenti, dolum başına kaymanın dört kademesinde (makas her kademede "
         "gerçek bid/ask).", "", blok_maliyet(u, ctx), "", blok_basabas(u, ctx), "",
         "**Yön mü, zamanlama mı?** " + blok_rastgele_cumle(u, ctx), "",
         "**Rejim ve saat.** " + blok_rejim_cumle(u, ctx), "", blok_rejim(u, ctx), "",
         blok_sekil(u, ctx, "saat", f"Giriş saatine göre — {kisa}"), ""]
    return "\n".join(p)


def blok_kosullar(u: Uretim, ctx: dict) -> str:
    """Koşul analizi dizisi: figür (EUR/USD), tutan/tutmayan özeti, öbür paritelerde aynı değişkenlerin hükmü."""
    b = ctx["B"]
    kisa = adlar.BIRIM[ctx["BID"]][1]
    p = [blok_sekil(u, ctx, "kosul", f"Koşul kovaları — {kisa}"), "", blok_kosul_ozet(u, ctx, "EURUSD"), ""]
    tut = [k["degisken"] for k in (((b.get("cift") or {}).get("EURUSD") or {}).get("varsayilan") or {}).get("kosul") or []
           if k.get("hukum") == "tuttu"]
    if tut:
        govde = []
        for d in tut:
            satir = [adlar.KOSUL.get(d, d)]
            for c in _ciftler(b):
                ks = {x["degisken"]: x for x in ((b["cift"][c].get("varsayilan") or {}).get("kosul") or [])}
                h = (ks.get(d) or {}).get("hukum")
                satir.append({"tuttu": "tuttu", "tutmadi": "tutmadı", "secilmedi": "seçilmedi"}.get(h, "—"))
            govde.append(satir)
        p += ["EUR/USD'de tutan değişkenler öbür paritelerde:", "",
              _tablo(["Değişken"] + [PARITE[c] for c in _ciftler(b)], govde, ["l"] + ["l"] * len(_ciftler(b))), ""]
    return "\n".join(p)


BLOKLAR = {
    "sonuclar": blok_sonuclar, "kosullar": blok_kosullar, "hukum_cumle": blok_hukum_cumle,
    "havuz_cumle": blok_havuz_cumle, "ay_sonu": blok_ay_sonu, "regresyon": blok_regresyon,
    "devam": blok_devam, "devam_cumle": blok_devam_cumle, "haber_kirilim": blok_haber_kirilim, "fomc": blok_fomc, "fomc_cumle": blok_fomc_cumle,
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
    "sekil": blok_sekil, "sonuc": blok_sonuc, "ayrinti": blok_ayrinti, "maliyet": blok_maliyet,
    "secim": blok_secim, "wf": blok_wf, "rejim": blok_rejim, "kural": blok_kural, "hukum": blok_hukum,
    "kosul_ozet": blok_kosul_ozet, "ornek": blok_ornek, "zaman": blok_zaman, "dst": blok_dst,
    "basabas": blok_basabas,
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
