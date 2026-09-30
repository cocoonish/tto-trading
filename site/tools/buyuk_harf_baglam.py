"""Büyük harf dönüşümünün bozduğu metin — derlenmiş çıktı ve derlenmiş CSS.

Kusur kaynakta ve HTML'de GÖRÜNMEZ: HTML'de "σ" ve "TradingView" durur, CSS
`text-transform: uppercase` ile `lang="tr"` onları çizimde "Σ" (toplam
işareti) ve "TRADİNGVİEW" yapar. Sayfa sınavı 27'nin ilk hâli ham HTML'de
"Σ" ve "TRADİNG" arıyordu; o dizgeler HTML'de hiç oluşmadığı için ölçüt
tanımı gereği sıfır buluyordu (30.09.2026, 14 sayfada kusur dururken
"96 sayfada 0 ihlal"). Bir ölçüt kusurun VEKİLİNİ değil kendisini sormalı:
burada soru "bu metin düğümü çizimde büyük harfe çevriliyor mu" ve cevabı
CSS'in kendisinde.

Tarayıcı yok (yayın koşucusunda Playwright kurulu değil), o yüzden hesap
küçük bir CSS eşleyicisiyle yapılır. Kapsam bilerek dar ve ADIYLA yazılı:

  * Yalnız `text-transform` bildiren kurallar okunur (sitede ~50 kural);
    her öğenin bildirilen değeri özgüllük + sıra ile seçilir, satır içi
    `style` hepsini ezer, bildirmeyen öğe ebeveyninden devralır.
  * Seçici sözdizimi: soy (boşluk) ve çocuk (`>`) birleştiricileri; etiket,
    `*`, `.sınıf`, `#kimlik`, `[nitelik]` / `[nitelik=değer]` (=, ~=, ^=, $=,
    *=, |=), `:first-child`, `:last-child`, `:where()`, `:is()`, `:not()`.
    Kardeş birleştiricileri (`+`, `~`), durum sözde sınıfları (`:hover`…) ve
    sözde öğeler (`::before`) DESTEKLENMEZ: o kurallar atlanır ve sayısı
    döndürülür — atlanan bir kural sessizce "temiz" sayılmasın.
  * `@media` içindeki kurallar her genişlikte geçerli sayılır: telefonda
    büyük harfe dönen bir σ da okura giden bir kusurdur.

Okura giden iki kusur sorulur: büyük harf bağlamında KÜÇÜK YUNAN HARFİ
(σ → Σ, μ → Μ; nicel okur için başka bir büyüklüğün adı) ve `lang="tr"`
altında büyük harfe dönen İNGİLİZCE AD (i → İ: "TRADİNGVİEW", "FİXİNG").
Koruma iki yoldan olur ve ikisi de burada tanınır: öğenin kendi
`text-transform: none`u (`.harf-koru`, `.katex`) ve `lang="en"`.
"""
from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

# Küçük Yunan harfleri (α–ω, son sigma dahil). Büyük harfe çevrilince başka bir
# simgenin adı olurlar; ϵ, ϕ gibi varyantlar da aynı bloktan.
YUNAN_KUCUK = re.compile(r"[α-ωϑϕϵ]")

# `lang="tr"` altında büyük harfe dönünce bozulan İngilizce ÖZEL AD ve
# KISALTMA. Yalnız 'i' taşıyanlar: i'siz bir ad ("Swap", "Brooks") dönüşümden
# sağ çıkar. Ödünç TERİM (fixing, receive, swaption) listede YOK ve bu bilerek:
# Türkçe metnin sözcüğüdür, Türkçe kuralla büyür. Liste TEK tanımdır; site
# tarafı (`src/lib/harf.mjs` → YABANCI) aynı listeyi taşır ve duman sınaması
# ikisini kaynak metninden kıyaslar.
YABANCI = (
    "tradingview", "trading", "pine", "script", "bitcoin", "nikkei",
    "bachelier", "fibonacci", "fib", "ict", "ois",
)
YABANCI_KALIP = re.compile(r"(?<![A-Za-z])(" + "|".join(sorted(YABANCI, key=len, reverse=True)) + r")(?![A-Za-z])", re.I)

_BOS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}
_METIN_DISI = {"script", "style", "template", "noscript"}
_DURUM = {"hover", "focus", "focus-visible", "focus-within", "active", "visited",
          "target", "checked", "disabled", "enabled", "placeholder-shown",
          "open", "fullscreen", "empty"}


# ---------------------------------------------------------------- CSS
def _yorumsuz(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def css_kurallari(css: str) -> list[tuple[str, str]]:
    """(seçici listesi, bildirim bloğu) — @media/@supports/@layer içleri dahil,
    @keyframes/@font-face hariç. Parantez derinliğiyle yürür."""
    css = _yorumsuz(css)
    out: list[tuple[str, str]] = []

    def yuru(s: str) -> None:
        i, n = 0, len(s)
        while i < n:
            j = s.find("{", i)
            if j < 0:
                return
            bas = s[i:j].strip()
            # eşleşen kapanış
            d, k = 1, j + 1
            while k < n and d:
                if s[k] == "{":
                    d += 1
                elif s[k] == "}":
                    d -= 1
                k += 1
            govde = s[j + 1:k - 1]
            if bas.startswith("@"):
                ad = bas[1:].split(None, 1)[0].lower() if len(bas) > 1 else ""
                if ad in ("media", "supports", "layer", "container", "document"):
                    yuru(govde)
            else:
                # bir önceki kuralın ';' ile bitmeyen artığı seçiciye yapışmasın
                bas = bas.split(";")[-1].strip()
                out.append((bas, govde))
            i = k

    yuru(css)
    return out


def _virgulle_bol(s: str) -> list[str]:
    parca, d, bas = [], 0, 0
    for i, c in enumerate(s):
        if c in "([":
            d += 1
        elif c in ")]":
            d -= 1
        elif c == "," and d == 0:
            parca.append(s[bas:i].strip())
            bas = i + 1
    parca.append(s[bas:].strip())
    return [p for p in parca if p]


class _Desteklenmez(Exception):
    pass


def _bilesik_ayristir(t: str) -> dict:
    """'th.sag[data-x]:first-child' → {tag, id, sinif[], nitelik[], sozde[], ozgulluk}"""
    b = {"tag": None, "id": None, "sinif": [], "nitelik": [], "sozde": [], "oz": [0, 0, 0]}
    i, n = 0, len(t)
    m = re.match(r"[A-Za-z][A-Za-z0-9-]*|\*", t)
    if m:
        if m.group(0) != "*":
            b["tag"] = m.group(0).lower()
            b["oz"][2] += 1
        i = m.end()
    while i < n:
        c = t[i]
        if c == ".":
            m = re.match(r"\.(-?[_A-Za-z0-9 -￿\\-][\w -￿\\-]*)", t[i:])
            if not m:
                raise _Desteklenmez(t)
            b["sinif"].append(m.group(1).replace("\\", ""))
            b["oz"][1] += 1
            i += m.end()
        elif c == "#":
            m = re.match(r"#([\w-]+)", t[i:])
            if not m:
                raise _Desteklenmez(t)
            b["id"] = m.group(1)
            b["oz"][0] += 1
            i += m.end()
        elif c == "[":
            k = t.find("]", i)
            if k < 0:
                raise _Desteklenmez(t)
            ic = t[i + 1:k].strip()
            m = re.match(r"([\w:-]+)\s*(?:([~^$*|]?=)\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s\]]+)))?\s*(i)?$", ic)
            if not m:
                raise _Desteklenmez(t)
            deg = m.group(3) if m.group(3) is not None else (m.group(4) if m.group(4) is not None else m.group(5))
            b["nitelik"].append((m.group(1).lower(), m.group(2), deg))
            b["oz"][1] += 1
            i = k + 1
        elif c == ":":
            if t[i:i + 2] == "::":
                raise _Desteklenmez(t)  # sözde öğe: üretilmiş içerik, metin düğümü değil
            m = re.match(r":([\w-]+)", t[i:])
            if not m:
                raise _Desteklenmez(t)
            ad = m.group(1).lower()
            i += m.end()
            arg = None
            if i < n and t[i] == "(":
                d, k = 1, i + 1
                while k < n and d:
                    d += (t[k] == "(") - (t[k] == ")")
                    k += 1
                arg = t[i + 1:k - 1]
                i = k
            if ad in ("first-child", "last-child"):
                b["sozde"].append((ad, None))
                b["oz"][1] += 1
            elif ad in ("where", "is", "not") and arg is not None:
                alt = [secici_ayristir(a) for a in _virgulle_bol(arg)]
                b["sozde"].append((ad, alt))
                if ad != "where":
                    b["oz"] = [x + y for x, y in zip(b["oz"], max((s["oz"] for s in alt), default=[0, 0, 0]))]
            elif ad in _DURUM:
                raise _Desteklenmez(t)  # durum: sayfa açıldığında geçerli değil
            else:
                raise _Desteklenmez(t)
        else:
            raise _Desteklenmez(t)
    return b


def secici_ayristir(sel: str) -> dict:
    """Bileşik zinciri: [(birleştirici, bileşik)], sağdan sola eşleşir."""
    s = re.sub(r"\s*>\s*", " > ", sel.strip())
    if re.search(r"(^|[^\\])[+~](?![=])", re.sub(r"\[[^\]]*\]|\([^)]*\)", "", s)):
        raise _Desteklenmez(sel)
    zincir, birlestirici = [], " "
    for tok in s.split():
        if tok == ">":
            birlestirici = ">"
            continue
        zincir.append((birlestirici, _bilesik_ayristir(tok)))
        birlestirici = " "
    if not zincir:
        raise _Desteklenmez(sel)
    oz = [0, 0, 0]
    for _, b in zincir:
        oz = [x + y for x, y in zip(oz, b["oz"])]
    return {"zincir": zincir, "oz": oz}


def donusum_kurallari(css: str) -> tuple[list[dict], int]:
    """`text-transform` bildiren kurallar → [{secici, deger, oz, sira}], atlanan sayısı."""
    kurallar, atlanan, sira = [], 0, 0
    for secler, govde in css_kurallari(css):
        m = re.search(r"(?:^|;)\s*text-transform\s*:\s*([a-z-]+)\s*(!important)?", govde, re.I)
        if not m:
            continue
        deger, onemli = m.group(1).lower(), bool(m.group(2))
        for sel in _virgulle_bol(secler):
            sira += 1
            try:
                s = secici_ayristir(sel)
            except _Desteklenmez:
                atlanan += 1
                continue
            kurallar.append({"secici": sel, "s": s, "deger": deger, "oz": tuple(s["oz"]),
                             "onemli": onemli, "sira": sira})
    return kurallar, atlanan


# ---------------------------------------------------------------- HTML
class _Oge:
    __slots__ = ("tag", "nitelik", "ebeveyn", "cocuk", "metin", "sinif", "_tt", "_lang")

    def __init__(self, tag, nitelik, ebeveyn):
        self.tag, self.nitelik, self.ebeveyn = tag, nitelik, ebeveyn
        self.cocuk: list = []   # _Oge ya da str
        self.sinif = set((nitelik.get("class") or "").split())
        self._tt = self._lang = None


class _Agac(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.kok = _Oge("#belge", {}, None)
        self.cur = self.kok

    def handle_starttag(self, tag, attrs):
        o = _Oge(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.cur)
        self.cur.cocuk.append(o)
        if tag not in _BOS:
            self.cur = o

    def handle_startendtag(self, tag, attrs):
        o = _Oge(tag, {k.lower(): (v if v is not None else "") for k, v in attrs}, self.cur)
        self.cur.cocuk.append(o)

    def handle_endtag(self, tag):
        o = self.cur
        while o is not None and o.tag != tag:
            o = o.ebeveyn
        if o is not None and o.ebeveyn is not None:
            self.cur = o.ebeveyn

    def handle_data(self, data):
        if data:
            self.cur.cocuk.append(data)


def _kardes(o: _Oge) -> list:
    return [c for c in o.ebeveyn.cocuk if isinstance(c, _Oge)] if o.ebeveyn else [o]


def _bilesik_tutar(o: _Oge, b: dict) -> bool:
    if o.ebeveyn is None:
        return False
    if b["tag"] and o.tag != b["tag"]:
        return False
    if b["id"] and o.nitelik.get("id") != b["id"]:
        return False
    for s in b["sinif"]:
        if s not in o.sinif:
            return False
    for ad, op, deg in b["nitelik"]:
        if ad not in o.nitelik:
            return False
        v = o.nitelik[ad]
        if op is None:
            continue
        if op == "=" and v != deg:
            return False
        if op == "~=" and deg not in v.split():
            return False
        if op == "^=" and not v.startswith(deg):
            return False
        if op == "$=" and not v.endswith(deg):
            return False
        if op == "*=" and deg not in v:
            return False
        if op == "|=" and not (v == deg or v.startswith(deg + "-")):
            return False
    for ad, alt in b["sozde"]:
        if ad == "first-child":
            k = _kardes(o)
            if not k or k[0] is not o:
                return False
        elif ad == "last-child":
            k = _kardes(o)
            if not k or k[-1] is not o:
                return False
        elif ad in ("where", "is"):
            if not any(secici_tutar(o, a) for a in alt):
                return False
        elif ad == "not":
            if any(secici_tutar(o, a) for a in alt):
                return False
    return True


def secici_tutar(o: _Oge, s: dict) -> bool:
    z = s["zincir"]

    def tut(el, i):
        birl, b = z[i]
        if not _bilesik_tutar(el, b):
            return False
        if i == 0:
            return True
        if birl == ">":
            return el.ebeveyn is not None and tut(el.ebeveyn, i - 1)
        a = el.ebeveyn
        while a is not None and a.ebeveyn is not None:
            if tut(a, i - 1):
                return True
            a = a.ebeveyn
        return False

    return tut(o, len(z) - 1)


def _satir_ici(o: _Oge):
    st = o.nitelik.get("style") or ""
    m = re.search(r"(?:^|;)\s*text-transform\s*:\s*([a-z-]+)", st, re.I)
    return m.group(1).lower() if m else None


def _tt(o: _Oge, kurallar) -> str:
    if o._tt is not None:
        return o._tt
    if o.ebeveyn is None:
        o._tt = "none"
        return o._tt
    deger = _satir_ici(o)
    if deger is None:
        eniyi = None
        for k in kurallar:
            if secici_tutar(o, k["s"]):
                anahtar = (k["onemli"], k["oz"], k["sira"])
                if eniyi is None or anahtar > eniyi[0]:
                    eniyi = (anahtar, k["deger"])
        deger = eniyi[1] if eniyi else None
    if deger in (None, "inherit", "unset", "revert"):
        deger = _tt(o.ebeveyn, kurallar)
    elif deger == "initial":
        deger = "none"
    o._tt = deger
    return deger


def _lang(o: _Oge) -> str:
    if o._lang is not None:
        return o._lang
    if o.ebeveyn is None:
        o._lang = ""
    elif "lang" in o.nitelik:
        o._lang = o.nitelik["lang"].lower()
    else:
        o._lang = _lang(o.ebeveyn)
    return o._lang


def sayfa_css(html: str, css_oku) -> str:
    """Sayfanın kendi CSS'i: bağlı dosyalar (`css_oku(href)` ile) + satır içi <style>."""
    parca = []
    for href in re.findall(r"<link\b[^>]*rel=\"stylesheet\"[^>]*href=\"([^\"]+)\"", html) + \
            re.findall(r"<link\b[^>]*href=\"([^\"]+\.css)\"[^>]*rel=\"stylesheet\"", html):
        t = css_oku(href)
        if t:
            parca.append(t)
    parca += re.findall(r"<style\b[^>]*>(.*?)</style>", html, re.S)
    return "\n".join(parca)


def bulgular(html: str, css: str) -> tuple[list[str], int]:
    """Tek sayfa → (bulgu listesi, atlanan kural sayısı)."""
    kurallar, atlanan = donusum_kurallari(css)
    if not kurallar:
        return [], atlanan
    agac = _Agac()
    agac.feed(html)
    out: list[str] = []

    def gez(o: _Oge):
        if o.tag in _METIN_DISI:
            return
        for c in o.cocuk:
            if isinstance(c, _Oge):
                gez(c)
                continue
            if not c.strip() or o.ebeveyn is None:
                continue
            if _tt(o, kurallar) != "uppercase":
                continue
            metin = " ".join(unescape(c).split())
            y = YUNAN_KUCUK.findall(metin)
            if y:
                out.append(f"küçük Yunan harfi büyük harfe dönüyor ({''.join(sorted(set(y)))}"
                           f" → {''.join(sorted(set(y))).upper()}): {metin[:60]!r} <{o.tag}"
                           f"{' .' + ' .'.join(sorted(o.sinif)) if o.sinif else ''}>")
            if _lang(o).startswith("tr"):
                for m in YABANCI_KALIP.finditer(metin):
                    if "i" not in m.group(1):
                        continue  # "OIS": büyük I dönüşümden sağ çıkar
                    out.append(f"İngilizce ad lang=\"tr\" altında büyük harfe dönüyor "
                               f"({m.group(1)} → {m.group(1).upper().replace('I', 'İ')}): {metin[:60]!r}")

    gez(agac.kok)
    return out, atlanan
