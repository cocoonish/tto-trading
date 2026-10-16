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

    def kok_ctx(self) -> dict:
        return {"O": self.O, "K": self.O["kunye"], "ON": self.ON}

    def birim_ctx(self, birim: str) -> dict:
        b = self.O["birim"].get(birim)
        if b is None:
            raise SablonHatasi(f"ölçümde birim yok: {birim}")
        ctx = self.kok_ctx()
        ctx.update({"B": b, "BID": birim, "H": (b.get("havuz") or {}).get("varsayilan")})
        for kisa, cift in KISA_AD.items():
            ctx[kisa] = (b.get("cift") or {}).get(cift)
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
            parca = s[1:].split()
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


def _tablo(baslik: list[str], satirlar: list[list[str]], hiza: list[str] | None = None) -> str:
    hiza = hiza or ["l"] + ["r"] * (len(baslik) - 1)
    ayrac = ["---:" if h == "r" else ":---" for h in hiza]
    s = ["| " + " | ".join(baslik) + " |", "| " + " | ".join(ayrac) + " |"]
    s += ["| " + " | ".join(r) + " |" for r in satirlar]
    return "\n".join(s)


def _ciftler(b: dict) -> list[str]:
    return [c for c in PARITE if (b.get("cift") or {}).get(c)]


def blok_sekil(u: Uretim, ctx: dict, ad: str, *baslik_parca: str) -> str:
    """Figür gömmesi; ad birim şablonunda kısaltılır (ornek → <birim>-ornek). Şekil numarası ders içinde
    sıralıdır. Figür dosyası yoksa üretim düşer: yazılmamış bir figür gömülmez."""
    tam = f"{ctx['BID']}-{ad}" if "BID" in ctx and "-" not in ad else ad
    u.sekil_no += 1
    u.sekiller.append(tam)
    baslik = " ".join(baslik_parca).strip('"') or tam
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


def blok_secim(u: Uretim, ctx: dict) -> str:
    """Izgaradan örneklem içinde seçilen kombinasyon, örneklem dışı sonucu ve deflated Sharpe."""
    b = ctx["B"]
    govde = []
    for c in _ciftler(b):
        v = b["cift"][c]
        s = v.get("secilen") or {}
        p = v.get("secilen_p") or {}
        govde.append([PARITE[c], " · ".join(adlar.DEGER.get(str(p[k]), str(p[k])) for k in sorted(p)) or "—",
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
        if i.get("sinyal_t") is not None:
            parca.append(f"Sinyal mumu {saat_tsi(i['sinyal_t'])} TSİ'de kapandı;")
        parca.append(f"giriş {saat_tsi(i['giris_t'])} TSİ'de {sayi(i['giris_f'] * NOKTA['EURUSD'], 5)}"
                     + (f", stop {sayi(i['stop'] * NOKTA['EURUSD'], 5)} ({sayi(risk, 1)} pip)" if risk else "")
                     + (f", hedef {sayi(i['hedef'] * NOKTA['EURUSD'], 5)}" if i.get("hedef") is not None else "") + ".")
        parca.append(f"Çıkış {saat_tsi(i['cikis_t'])} TSİ'de {sayi(i['cikis_f'] * NOKTA['EURUSD'], 5)}, "
                     f"{adlar.NEDEN.get(i['neden'], '')}: {sayi(i['r'], 2, arti=True)} R "
                     f"({sayi(i['pnl_pip'], 1, arti=True)} pip, maliyet dahil).")
        satir.append("- " + " ".join(parca))
    return "\n".join(satir) if satir else "_Örneklem dışında işlem yok._"


def blok_zaman(u: Uretim, ctx: dict) -> str:
    """Olayların TSİ saati, dört saat rejiminde (temsilci günler)."""
    z = u.O["zaman"]
    rejimler = z["tablo"]
    olaylar = [k for k in rejimler[0] if k not in ("gun", "londra_ny", "rejim")]
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
        return (f"{PARITE[cift]}'da kayma ızgarasının sonunda (dolum başına 2 pip) bile net beklenti artı: maliyet "
                f"bu kuralın sınırlayıcısı değil.")
    if k == 0:
        return f"{PARITE[cift]}'da sıfır kaymada (yalnız gerçek makasla) bile net beklenti eksi: maliyet ne olursa olsun."
    return (f"{PARITE[cift]}'da makasın üstüne dolum başına {sayi(k, 2)} pip kayma net beklentiyi sıfıra indiriyor "
            f"(bütün dönem). Yürütme maliyetiniz bunun altında değilse kural kâğıt üstünde kalır.")


BLOKLAR = {
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
        return uu.isle(yol.read_text(encoding="utf-8"), uu.birim_ctx(birim))

    BLOKLAR["strateji"] = blok_strateji
    govde = u.isle(sablon, u.kok_ctx())
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
