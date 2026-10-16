#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resmi kaynakların dondurulmuş ham sayfalarından olay listesi (`veri/takvim/olaylar.csv`).

Ağsız; girdisi `veri/takvim/ham/` (arsiv_takvim*.py). Her satır saatini TARİH BAZINDA
kaynağın kendi metninden alır; metinde saat yoksa satır yazılmaz ve sebebi künyeye
(`veri/takvim/kunye.json`) düşer. Saat sonradan 1 dakikalık fiyattan ayrıca sınanır
(`takvim_sina.py`); ikisi ayrışırsa olay yayımlanmaz.

FOMC. Takvim sayfaları (güncel + 2018–2020 tarihsel) toplantıları bloklar hâlinde
verir: karar metni bağlantısı (`monetaryYYYYMMDDa.htm`, etiketi "Statement") ve basın
toplantısı bağlantısı (`fomcpresconfYYYYMMDD.htm`). "notation vote" ve "cancelled"
bloklar karar sayılmaz; olağanüstü toplantılar ("unscheduled") karar metni varsa
sayılır. Saat, karar metninin kendi satırından: "For release at 2:00 p.m. EDT".
Basın toplantısının saati ne karar metninde ne basın toplantısı sayfasında yazar
(sayfadaki tek saat "Released ... at 2:00 p.m." — KARARIN yayım saati; altı örnekte
ölçüldü). Fed'in aylık etkinlik takvimi basın toplantısını ayrı satırla yalnız
17.09.2025'ten itibaren listeler; öncesinde tek istisna 30.01.2019'un duyurusu
(`fed_takvim`). Öbür tarihlerde saat Fed'in 13.03.2013 KURALINDAN gelir (`fomc_kurali`:
olağan toplantıların kararı 14:00, basın toplantısı "yaklaşık" 14:30) ve kural yalnız
kararı kuralın saatinde yayımlanan olağan toplantıya uygulanır. Olağanüstü toplantının
basın toplantısı (03.03.2020) kaynakta saatsiz: YAZILMAZ, adıyla sayılır.

NFP · CPI (BLS). Tarih ve saat her yayımın kendi ambargo satırından: "Transmission of
material in this release is embargoed until 8:30 a.m. (ET) Friday, February 2, 2018".
Satır Internet Archive'daki kopyadan okunur (bls.gov'a istek atılmaz). Ambargo
tarihi dosya adındaki tarihle aynı olmalı; referans ayı sayfa başlığından ("The
Employment Situation - January 2018"); bir referans ayına iki yayım düşerse ilki
alınır, ikincisi künyeye yazılır.

ECB. Karar listesi yıllık include dosyalarından, tarih duyurunun dosya adından
(`ecb.mpYYMMDD`; include'daki isoDate alanı birkaç kayıtta yanlış ölçüldü). Basın
toplantısı saati duyurunun kendi cümlesinden ("press conference starting at 14:45
CET today"); karar saati ECB'nin 27.06.2022 duyurusundan: 21.07.2022'den itibaren
14:15, önce 13:45 — ve basın toplantısı saatiyle eşleşmesi (13:45 ↔ 14:30,
14:15 ↔ 14:45) her tarih için ayrıca sınanır. "CET" ECB dilinde Frankfurt yerel
saatidir; yaz saati `Europe/Berlin` ile.

BoE. Tarih her MPC özetinin "Published on …" satırından; saat BoE'nin yayım
kuralından ("published at 12 noon on a Thursday eight times a year" — liste sayfası).
Perşembe olmayan tarih künyeye düşer. Bank Rate değişiklik listesinde olup MPC özet
listesinde olmayan olağanüstü kararların saati kaynakta yok: yazılmaz, adıyla sayılır.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

BURASI = Path(__file__).resolve().parent
HAM = BURASI / "veri" / "takvim" / "ham"
CIKTI = BURASI / "veri" / "takvim" / "olaylar.csv"
KUNYE = BURASI / "veri" / "takvim" / "kunye.json"
NY = ZoneInfo("America/New_York")
AY_ADI = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
AYLAR = {a: i + 1 for i, a in enumerate(AY_ADI)}
BAS, BIT = date(2018, 1, 1), date(2026, 10, 15)
# Basın toplantısı bağlantısı: Fed sayfasında iki düzensiz yazım ölçüldü — mutlak adres
# (2022-03-16) ve "fomcpressconf" (2026-01-28, çift s). Kalıp ikisini de tanır.
PRESCONF = r'href="(?:https://www\.federalreserve\.gov)?(/monetarypolicy/fomcpress?conf(\d{8})\.htm)"'
ECB_KURAL = "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.pr220627~73acedf868.en.html"
ECB_GECIS = date(2022, 7, 21)
BOE_KURAL = "https://www.bankofengland.co.uk/monetary-policy-summary-and-minutes/monetary-policy-summary-and-minutes"
BOE_ORAN = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"


def _manifest() -> dict:
    m = {}
    adlar = (["manifest.json", "manifest2.json"] + sorted(p.name for p in HAM.glob("manifest3_*.json"))
             + sorted(p.name for p in HAM.glob("manifest5_*.json")))
    for ad in adlar:
        yol = HAM / ad
        if yol.exists():
            for u, v in json.loads(yol.read_text(encoding="utf-8")).items():
                if not u.startswith("_") and v.get("dosya"):
                    m[u] = v
    return m


def _metin(dosya: str) -> str:
    return (HAM / dosya).read_text(encoding="utf-8", errors="replace")


def _duz(t: str) -> str:
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))


def _saat(sa: int, dk: int, ap: str) -> str:
    ap = ap.lower()
    if ap == "p" and sa != 12:
        sa += 12
    if ap == "a" and sa == 12:
        sa = 0
    return f"{sa:02d}:{dk:02d}"


def _yaz_saati_mi(g: date, bolge: str = "America/New_York") -> bool:
    return bool(pd.Timestamp(f"{g} 12:00").tz_localize(ZoneInfo(bolge)).dst())


# ───────────────────────────────────────────── FOMC
def _fomc_bloklar(t: str) -> list[dict]:
    """Takvim sayfasındaki toplantı blokları: başlık, karar metni, basın toplantısı."""
    out = []
    # Tarihsel sayfa: <h5 ...>March 2 (unscheduled) Meeting - 2020</h5> ... sonraki <h5'e kadar
    for m in re.finditer(r"<h5[^>]*>([^<]*?Meeting - (\d{4}))</h5>(.*?)(?=<h5|\Z)", t, re.S):
        baslik, yil, govde = m.group(1).strip(), m.group(2), m.group(3)
        st = re.search(r'href="(?:https://www\.federalreserve\.gov)?/newsevents/pressreleases/monetary(\d{8})a\.htm">Statement<', govde)
        pc = re.search(PRESCONF, govde)
        out.append({"baslik": baslik, "yil": int(yil), "karar": st.group(1) if st else None,
                    "basin": pc.group(2) if pc else None, "basin_yol": pc.group(1) if pc else None})
    # Güncel sayfa: <div class="... fomc-meeting"> blokları, yıl başlığı <h4>YYYY FOMC Meetings</h4>
    for py in re.finditer(r"<h4><a[^>]*>(\d{4}) FOMC Meetings</a></h4>(.*?)(?=<h4><a|\Z)", t, re.S):
        yil, panel = int(py.group(1)), py.group(2)
        for b in re.finditer(r'<div class="[^"]*\bfomc-meeting"[^>]*>(.*?)(?=<div class="[^"]*\bfomc-meeting"|\Z)',
                             panel, re.S):
            govde = b.group(1)
            ay = re.search(r"fomc-meeting__month[^>]*><strong>([^<]+)</strong>", govde)
            gun = re.search(r'fomc-meeting__date[^>]*>([^<]+)<', govde)
            st = re.search(r'href="(?:https://www\.federalreserve\.gov)?/newsevents/pressreleases/monetary(\d{8})a\.htm"', govde)
            pc = re.search(PRESCONF, govde)
            out.append({"baslik": f"{ay.group(1) if ay else '?'} {gun.group(1).strip() if gun else '?'} - {yil}",
                        "yil": yil, "karar": st.group(1) if st else None, "basin": pc.group(2) if pc else None,
                        "basin_yol": pc.group(1) if pc else None})
    return out


def _yayim_saati(t: str) -> tuple[str, str] | None:
    """'For release at 2:00 p.m. EDT' → ('14:00', 'EDT')."""
    s = _duz(t)
    m = re.search(r"For release at (\d{1,2}):(\d{2}) ?([ap])\.m\.? ?(EST|EDT|E\.S\.T\.|E\.D\.T\.)", s, re.I)
    if not m:
        return None
    return _saat(int(m.group(1)), int(m.group(2)), m.group(3)), m.group(4).replace(".", "").upper()


_SAAT = re.compile(r"(\d{1,2}):(\d{2}) ?([ap])\.m\.")
#: Duyuru satırında basın toplantısı saati (30.01.2019: "the Chairman's news conference will start at 2:30 p.m. EST").
_DUYURU_BASIN = re.compile(r"(?i)(?:news|press) conference will (?:start|begin) at (?:approximately )?"
                           r"(\d{1,2}):(\d{2}) ?([ap])\.m\.(?:\s*(EST|EDT|ET))?")


def _satirlar(t: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Aylık etkinlik sayfasının satırları: [(bölüm başlığı, [(sütun sınıfı, sütun HTML'i), …])].

    Biçim 16.10.2026'da 103 sayfada ölçüldü (2018–2026 aynı): bölümler `<h4 class="col-md-12">` başlığıyla
    açılır; her etkinlik bir `panel-body` içinde üç sütundur — `col-xs-2` saat, `col-xs-7` etkinliğin adı
    (ilk paragraf) ve açıklaması, `col-xs-3` gün. Duyurular bölümünde iki sütun: metin ve gün (`col-xs-2`)."""
    out = []
    for p in re.split(r'<h4 class="col-md-12">', t)[1:]:
        bas, _, govde = p.partition("</h4>")
        bolum = _duz(bas).strip()
        for pb in re.split(r'<div class="panel-body">', govde)[1:]:
            out.append((bolum, re.findall(r'<div class="(col-xs-[^"]*)">(.*?)</div>', pb, re.S)))
    return out


def fed_takvim(man: dict) -> dict[date, list[dict]]:
    """Fed'in aylık etkinlik sayfalarından FOMC etkinlikleri, gün gün: {gün: [{saat, tur, ad, kaynak}]}.

    tur: "basin" — ayrı satırı olan basın toplantısı ("FOMC Press Conference · 2:30 p.m.", 17.09.2025'ten
    itibaren); "duyuru" — duyurular bölümünde basın toplantısının saatini veren cümle; "toplanti" — "FOMC
    Meeting" satırı. Sonuncusunun saati KARARIN yayım saatidir: açıklamada "Press Conference" geçmesi o saatin
    basın toplantısına ait olduğunu söylemez (ölçüldü: 2018–2025 sayfalarının hepsinde aynı satır 2:00 p.m.)."""
    out: dict[date, list[dict]] = {}
    for u, v in man.items():
        m = re.search(r"federalreserve\.gov/newsevents/(20\d{2})-([a-z]+)\.htm$", u)
        if not m or m.group(2).capitalize() not in AYLAR:
            continue
        yil, ay = int(m.group(1)), AYLAR[m.group(2).capitalize()]
        for bolum, kol in _satirlar(_metin(v["dosya"])):
            sinif = [c for c, _ in kol]
            if bolum == "FOMC Meetings" and sinif[:1] == ["col-xs-2"] and len(kol) >= 3:
                s = _SAAT.search(_duz(kol[0][1]))
                ilk = re.search(r"<p>(.*?)</p>", kol[1][1], re.S)
                ad = _duz(ilk.group(1)).strip() if ilk else ""
                gun = re.fullmatch(r"\s*(\d{1,2})\s*", _duz(kol[-1][1]))
                if not (s and gun):
                    continue
                tur = ("basin" if re.fullmatch(r"(?i)FOMC Press Conference", ad) else
                       "toplanti" if re.fullmatch(r"(?i)FOMC Meeting", ad) else None)
                if tur:
                    out.setdefault(date(yil, ay, int(gun.group(1))), []).append(
                        {"saat": _saat(int(s.group(1)), int(s.group(2)), s.group(3)), "tur": tur, "ad": ad,
                         "kaynak": u})
            elif bolum == "Announcements" and len(kol) >= 2:
                metin = _duz(kol[0][1])
                b = _DUYURU_BASIN.search(metin)
                gun = re.fullmatch(r"\s*(\d{1,2})\s*", _duz(kol[-1][1]))
                if b and gun:
                    # Duyurunun günü YAYIM günüdür, toplantınınki olmayabilir (ölçüldü: 27.01.2026 duyurusu
                    # 28 Ocak'taki basın toplantısını anlatıyor). Metnin adını verdiği günler de anahtar olur.
                    gunler = {date(yil, ay, int(gun.group(1)))} | {
                        date(yil, AYLAR[a], int(d)) for a, d in re.findall(r"(" + "|".join(AY_ADI) + r") (\d{1,2})\b",
                                                                           metin) if AYLAR[a] == ay}
                    for g in sorted(gunler):
                        out.setdefault(g, []).append(
                            {"saat": _saat(int(b.group(1)), int(b.group(2)), b.group(3)), "tur": "duyuru",
                             "ad": b.group(0), "kaynak": u, "dilim": (b.group(4) or "").upper()})
    return out


FED_KURAL = "https://www.federalreserve.gov/newsevents/pressreleases/monetary20130313a.htm"
_KURAL_KARAR = re.compile(r"(?i)policy statements for all regularly scheduled meetings will now be released at "
                          r"(\d{1,2})(?::(\d{2}))? ?([ap])\.m\. Eastern Time")
_KURAL_BASIN = re.compile(r"(?i)news conference will begin at approximately (\d{1,2}):(\d{2}) ?([ap])\.m\. "
                          r"Eastern Time")
#: Toplantı takvimi duyurularında kuralın yinelenmesi: saat "at"/"for" ile basın toplantısına bağlı olmalı
#: ("press conference at 2:30 p.m."); "press conference following the 2:00 p.m. statement" gibi bir cümle
#: KARARIN saatini taşır ve yineleme sayılmaz.
_YINELEME = re.compile(r"(?i)(?:news|press) conference\b[^.:]{0,40}?\b(?:at|for)\s+(?:approximately\s+|about\s+)?"
                       r"(\d{1,2}):(\d{2})\s?([ap])\.m\.")


def fomc_kurali(man: dict) -> dict:
    """Fed'in 13.03.2013 duyurusundaki saat kuralı ve toplantı takvimi duyurularındaki yinelemeleri.

    Döner: {"karar": "14:00" | None, "basin": "14:30" | None, "kaynak": adres, "son_gecerli": tarih | None,
    "yineleme": [...], "sorun": [...]}. Kural yalnız OLAĞAN toplantılar içindir ("all regularly scheduled
    meetings"). Bir duyuru basın toplantısına başka bir saat yazıyorsa kural o duyurunun tarihinden sonraki
    toplantılara uygulanmaz (`son_gecerli`): yeni saat ancak kendi tarih tarih kaynağıyla yazılır."""
    k: dict = {"karar": None, "basin": None, "kaynak": FED_KURAL, "son_gecerli": None, "yineleme": [], "sorun": []}
    v = man.get(FED_KURAL)
    if not v:
        k["sorun"].append("13.03.2013 saat duyurusu arşivde yok (beşinci geçiş koşmadı)")
        return k
    s = _duz(_metin(v["dosya"]))
    kk, kb = _KURAL_KARAR.search(s), _KURAL_BASIN.search(s)
    if not (kk and kb):
        k["sorun"].append("13.03.2013 duyurusunun metni beklenen cümleleri taşımıyor — kural kurulmadı")
        return k
    k["karar"] = _saat(int(kk.group(1)), int(kk.group(2) or 0), kk.group(3))
    k["basin"] = _saat(int(kb.group(1)), int(kb.group(2)), kb.group(3))
    for u, x in sorted(man.items()):
        t = re.search(r"/newsevents/pressreleases/[a-z]+(\d{8})[a-z]?\.htm$", u)
        if u == FED_KURAL or not t or not x.get("dosya"):
            continue
        g = date(int(t.group(1)[:4]), int(t.group(1)[4:6]), int(t.group(1)[6:]))
        for y in _YINELEME.finditer(_duz(_metin(x["dosya"]))):
            saat = _saat(int(y.group(1)), int(y.group(2)), y.group(3))
            k["yineleme"].append({"kaynak": u, "tarih": g.isoformat(), "saat": saat, "metin": y.group(0)[:160]})
            if saat != k["basin"]:
                k["sorun"].append(f"{g}: {u.rsplit('/', 1)[-1]} basın toplantısını {saat} diye yazıyor, kural "
                                  f"{k['basin']} — kural bu tarihten sonraki toplantılara uygulanmaz")
                if k["son_gecerli"] is None or g.isoformat() < k["son_gecerli"]:
                    k["son_gecerli"] = g.isoformat()
    return k


def fomc(man: dict, kunye: dict) -> list[dict]:
    satir, sorun = [], []
    bloklar = []
    for u, v in man.items():
        if "federalreserve.gov/monetarypolicy/fomc" in u and ("calendars" in u or "historical" in u):
            bloklar += _fomc_bloklar(_metin(v["dosya"]))
    takvim = fed_takvim(man)
    kural = fomc_kurali(man)
    sorun += [f"kural: {s}" for s in kural["sorun"]]
    kaynak_say = {"takvim": 0, "duyuru": 0, "kural": 0}
    kaynak_tarih: dict[str, list[str]] = {"takvim": [], "duyuru": []}
    kuraldan_farkli = 0
    gorulen = set()
    for b in bloklar:
        bas = b["baslik"].lower()
        if "notation vote" in bas or "cancelled" in bas or not b["karar"]:
            continue
        if b["karar"] in gorulen:
            continue
        gorulen.add(b["karar"])
        g = date(int(b["karar"][:4]), int(b["karar"][4:6]), int(b["karar"][6:]))
        if not BAS <= g <= BIT:
            continue
        u = f"https://www.federalreserve.gov/newsevents/pressreleases/monetary{b['karar']}a.htm"
        if u not in man:
            sorun.append(f"{g}: karar metni arşivde yok")
            continue
        ys = _yayim_saati(_metin(man[u]["dosya"]))
        if ys is None:
            sorun.append(f"{g}: karar metninde yayım saati okunamadı")
            continue
        saat, kisa = ys
        beklenen = "EDT" if _yaz_saati_mi(g) else "EST"
        if kisa != beklenen:
            sorun.append(f"{g}: metin {kisa} diyor, o gün New York'ta {beklenen} geçerli")
            continue
        olagan = "unscheduled" not in bas
        satir.append({"olay": "FOMC_karar", "tarih": g.isoformat(), "yerel_saat": saat, "bolge": "America/New_York",
                      "kaynak": u, "not": "" if olagan else "olağanüstü toplantı"})
        if not b["basin"]:
            continue
        # Basın toplantısının saati: önce o günün KENDİ kaydı (aylık takvimin ayrı satırı ya da duyurusu), yoksa
        # Fed'in 13.03.2013 kuralı. Kural yalnız olağan toplantıya ve kararı kuralın saatinde yayımlanan güne
        # uygulanır (kuralın eşi: karar 14:00 ↔ basın toplantısı 14:30, ECB'deki sınamanın aynısı).
        etk = sorted((e for e in takvim.get(g, []) if e["tur"] in ("basin", "duyuru")), key=lambda e: e["tur"])
        saatler = sorted({e["saat"] for e in etk})
        if len(saatler) > 1:
            sorun.append(f"{g}: takvim kayıtları basın toplantısına iki saat veriyor {saatler} — yazılmadı")
            continue
        if etk:
            e = etk[0]
            dilim = e.get("dilim")
            if dilim and dilim != "ET" and dilim != kisa:
                sorun.append(f"{g}: duyuru {dilim} diyor, o gün New York'ta {kisa} geçerli — yazılmadı")
                continue
            if kural["basin"] and e["saat"] != kural["basin"]:
                sorun.append(f"{g}: takvim {e['saat']} diyor, kural {kural['basin']} — takvimin kendi kaydı alındı")
                kuraldan_farkli += 1
            kaynak_say["takvim" if e["tur"] == "basin" else "duyuru"] += 1
            kaynak_tarih["takvim" if e["tur"] == "basin" else "duyuru"].append(g.isoformat())
            satir.append({"olay": "FOMC_basin", "tarih": g.isoformat(), "yerel_saat": e["saat"],
                          "bolge": "America/New_York", "kaynak": e["kaynak"],
                          "not": ("saat Fed'in aylık etkinlik takviminden (ayrı satır)" if e["tur"] == "basin" else
                                  "saat Fed'in aylık etkinlik takvimindeki duyurudan") +
                                 ("" if olagan else "; olağanüstü toplantı")})
            continue
        if not olagan:
            sorun.append(f"{g}: olağanüstü toplantının basın toplantısı — saati kaynakta yok ve kural yalnız olağan "
                         f"toplantılar için; yazılmadı")
            continue
        if not kural["basin"]:
            sorun.append(f"{g}: basın toplantısının saati takvimde yok ve kural kurulamadı — yazılmadı")
            continue
        if kural["son_gecerli"] and g.isoformat() > kural["son_gecerli"]:
            sorun.append(f"{g}: kural {kural['son_gecerli']} tarihli duyurudan sonra geçerli değil — yazılmadı")
            continue
        if saat != kural["karar"]:
            sorun.append(f"{g}: karar {saat}'te yayımlandı, kuralın karar saati {kural['karar']} — basın toplantısı "
                         f"kuraldan kurulamaz, yazılmadı")
            continue
        kaynak_say["kural"] += 1
        satir.append({"olay": "FOMC_basin", "tarih": g.isoformat(), "yerel_saat": kural["basin"],
                      "bolge": "America/New_York", "kaynak": kural["kaynak"],
                      "not": f"saat Fed'in 13.03.2013 kuralından (karar {kural['karar']}, basın toplantısı yaklaşık "
                             f"{kural['basin']}); bu tarih için ayrı kayıt kaynakta yok"})
    kunye["fomc"] = {"karar": sum(1 for s in satir if s["olay"] == "FOMC_karar"),
                     "basin": sum(1 for s in satir if s["olay"] == "FOMC_basin"),
                     "basin_saat_kaynagi": kaynak_say,
                     "basin_saat_tarih": {k_: sorted(v_) for k_, v_ in kaynak_tarih.items()},
                     "kuraldan_farkli": kuraldan_farkli, "takvim_gun": len(takvim),
                     "kural": {x: kural[x] for x in ("karar", "basin", "kaynak", "son_gecerli", "yineleme")},
                     "sorun": sorun}
    return satir


# ───────────────────────────────────────────── BLS: NFP · CPI
AMBARGO = re.compile(r"embargoed until (?:USDL[-\s]?\d{2}-\d{3,4}\s+)?(\d{1,2}):(\d{2})\s*([ap])\.m\.\s*"
                     r"\((EST|EDT|ET)\)\s*(?:[A-Za-z]+,\s*)?([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})")
BLS_BASLIK = {"empsit": r"Employment Situation\s*[-–—]\s*([A-Za-z]+)\s+(\d{4})",
              "cpi": r"Consumer Price Index\s*[-–—]\s*([A-Za-z]+)\s+(\d{4})"}


BLS_MANSET = {"empsit": r"EMPLOYMENT SITUATION\s*[-–—]+\s*([A-Za-z]+)\s+(\d{4})",
              "cpi": r"CONSUMER PRICE INDEX\s*[-–—]+\s*([A-Za-z]+)\s+(\d{4})"}


def _bls_referans(seri: str, k: dict) -> str:
    """Yayımın referans ayı, yayımın KENDİ metninden: önce ambargo parçasındaki manşet ("THE EMPLOYMENT
    SITUATION -- MARCH 2024"), sonra sayfa başlığı ("… - 2021 M12 Results" ya da "… - December 2020").
    Yayım tarihinden türetilmez: 2025 hükümet kapanışında referans ayı ile yayım ayı ayrıştı."""
    for metin, kalip in ((k.get("ambargo", ""), BLS_MANSET[seri]), (k.get("baslik", ""), BLS_BASLIK[seri])):
        r = re.search(kalip, metin, re.I)
        if r and r.group(1).capitalize() in AYLAR:
            return f"{r.group(2)}-{AYLAR[r.group(1).capitalize()]:02d}"
    # Başlığın "2021 M12 Results" kodu: M01–M12 ay, M13 yıllık ortalama (ay değil), Q çeyrek (ay değil)
    r = re.search(r"(\d{4})\s+M(0[1-9]|1[0-2])\s+Results", k.get("baslik", ""))
    return f"{r.group(1)}-{r.group(2)}" if r else "?"


def bls(seri: str, olay: str, kunye: dict) -> list[dict]:
    yol = HAM / f"bls_{seri}_ambargo.json"
    sorun: list[str] = []
    if not yol.exists():
        kunye[olay] = {"yayim": 0, "sorun": [f"{yol.name} yok — üçüncü arşiv geçişi koşmadı"]}
        return []
    defter = json.loads(yol.read_text(encoding="utf-8"))
    duzeltme: list[str] = []
    aday: list[tuple[date, str, str, dict]] = []
    for gs, k in sorted(defter.items()):
        g = date.fromisoformat(gs)
        if not BAS <= g <= BIT:
            continue
        if not k.get("ambargo"):
            sorun.append(f"{gs}: ambargo satırı yok ({k.get('durum')})")
            continue
        m = AMBARGO.search(k["ambargo"])
        if not m or m.group(5) not in AYLAR:
            sorun.append(f"{gs}: ambargo satırı okunamadı: {k['ambargo'][:90]}")
            continue
        g2 = date(int(m.group(7)), AYLAR[m.group(5)], int(m.group(6)))
        if g2 != g:
            # Ambargo satırındaki YIL dizgi hatası (ölçüldü: 13.01.2021 TÜFE yayımı "January 13, 2020" diyor).
            # Kabul ancak iki bağımsız işaret aynı yılı gösterirse: dosya adının yılı ve AYNI satırdaki
            # yayım numarasının yılı (USDL-21-0024). Ay ve gün birebir tutmalı; tek işaret yetmez.
            usdl = re.search(r"USDL-(\d{2})-\d{3,4}", k["ambargo"])
            if (g2.replace(year=g.year) == g and usdl and 2000 + int(usdl.group(1)) == g.year):
                duzeltme.append(f"{gs}: ambargo satırı yılı {g2.year} yazıyor; dosya adı ve aynı satırdaki yayım "
                                f"numarası (USDL-{usdl.group(1)}) {g.year} diyor — {g.year} alındı")
            else:
                sorun.append(f"{gs}: dosya adı {g}, ambargo tarihi {g2} — yazılmadı")
                continue
        if m.group(4) != "ET" and m.group(4) != ("EDT" if _yaz_saati_mi(g) else "EST"):
            sorun.append(f"{gs}: ambargo {m.group(4)} diyor, o gün New York'ta öbürü geçerli — yazılmadı")
            continue
        ref = _bls_referans(seri, k)
        aday.append((g, _saat(int(m.group(1)), int(m.group(2)), m.group(3)), ref, k))
    satir, gorulen = [], {}
    for g, saat, ref, k in sorted(aday):
        if ref != "?" and ref in gorulen:
            sorun.append(f"{g}: referans ayı {ref} için ikinci yayım (ilki {gorulen[ref]}) — yazılmadı")
            continue
        gorulen[ref] = g
        satir.append({"olay": olay, "tarih": g.isoformat(), "yerel_saat": saat, "bolge": "America/New_York",
                      "kaynak": k["orijinal"], "not": f"referans ayı {ref}; ambargo satırı Internet Archive "
                                                      f"kopyasından ({k['wayback']})"})
    # Kapsam: referans ayı başına bir yayım beklenir; eksik aylar adıyla.
    refler = sorted(r for r in gorulen if r != "?")
    eksik = []
    if refler:
        y, a = map(int, refler[0].split("-"))
        while f"{y}-{a:02d}" <= refler[-1]:
            if f"{y}-{a:02d}" not in gorulen:
                eksik.append(f"{y}-{a:02d}")
            y, a = (y + 1, 1) if a == 12 else (y, a + 1)
    # Referans ayı metinden okunamayan yayım (ör. yeniden basılmış kopyada manşet ambargo parçasının dışında
    # kalıyor: 06.12.2019 ve 10.01.2020 NFP) bir boşluğun ardındaki ayda yayımlanmışsa o boşluk "yayım yok"
    # değil "ayı okunamadı"dır; ikisi ayrı yazılır.
    bilinmeyen = [g for g, _, ref, _ in aday if ref == "?"]
    okunamadi = []
    for e in list(eksik):
        y, a = map(int, e.split("-"))
        y2, a2 = (y + 1, 1) if a == 12 else (y, a + 1)
        if any(g.year == y2 and g.month == a2 for g in bilinmeyen):
            okunamadi.append(e)
            eksik.remove(e)
    kunye[olay] = {"yayim": len(satir), "ilk_referans": refler[0] if refler else None,
                   "son_referans": refler[-1] if refler else None, "yayimi_olmayan_referans_ayi": eksik,
                   "referansi_okunamayan_ay": okunamadi,
                   "referansi_okunamayan_yayim": [g.isoformat() for g in bilinmeyen],
                   "saatler": sorted({s["yerel_saat"] for s in satir}), "sorun": sorun,
                   "duzeltme": duzeltme}
    return satir


# ───────────────────────────────────────────── ECB
ECB_BASIN = re.compile(r"(?i)press conference (?:starting|beginning|which will (?:start|begin)) at (\d{1,2})[:.](\d{2}) "
                       r"?(?:CET|CEST)")


def ecb(man: dict, kunye: dict) -> list[dict]:
    satir, sorun = [], []
    kural = man.get(ECB_KURAL)
    if not kural or "monetary policy decisions will be published at 14:15 CET (instead of 13:45)" not in \
            _duz(_metin(kural["dosya"])):
        kunye["ecb"] = {"karar": 0, "sorun": ["27.06.2022 saat duyurusu arşivde yok ya da metni değişmiş"]}
        return []
    gorulen = set()
    for u, v in sorted(man.items()):
        m = re.search(r"/press/pr/date/\d{4}/html/ecb\.mp(\d{2})(\d{2})(\d{2})[^/]*\.en\.html$", u)
        if not m:
            continue
        g = date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if not BAS <= g <= BIT or g in gorulen:
            continue
        gorulen.add(g)
        b = ECB_BASIN.search(_duz(_metin(v["dosya"])))
        if not b:
            sorun.append(f"{g}: duyuruda basın toplantısı saati okunamadı — yazılmadı")
            continue
        basin = f"{int(b.group(1)):02d}:{b.group(2)}"
        karar, eslesen = ("14:15", "14:45") if g >= ECB_GECIS else ("13:45", "14:30")
        if basin != eslesen:
            sorun.append(f"{g}: basın toplantısı {basin}, kuralın eşi {eslesen} — karar saati kuraldan "
                         f"kurulamaz, yazılmadı")
            continue
        satir.append({"olay": "ECB_karar", "tarih": g.isoformat(), "yerel_saat": karar, "bolge": "Europe/Berlin",
                      "kaynak": u, "not": "karar saati ECB'nin 27.06.2022 duyurusundan (21.07.2022'den itibaren "
                                          "14:15, önce 13:45); basın toplantısı saati bu duyurudan"})
        satir.append({"olay": "ECB_basin", "tarih": g.isoformat(), "yerel_saat": basin, "bolge": "Europe/Berlin",
                      "kaynak": u, "not": ""})
    # Olağanüstü duyurular (ör. 18.03.2020 PEPP): metin yayım saati vermiyorsa yazılmaz.
    for u, v in sorted(man.items()):
        m = re.search(r"/press/pr/date/\d{4}/html/ecb\.pr(\d{2})(\d{2})(\d{2})_1[^/]*\.en\.html$", u)
        if m:
            g = date(2000 + int(m.group(1)), int(m.group(2)), int(m.group(3)))
            if g not in gorulen and BAS <= g <= BIT:
                sorun.append(f"{g}: karar listesinde olağan toplantı dışı duyuru; yayım saati metinde yok — yazılmadı")
    kunye["ecb"] = {"karar": sum(1 for s in satir if s["olay"] == "ECB_karar"),
                    "basin": sum(1 for s in satir if s["olay"] == "ECB_basin"), "sorun": sorun}
    return satir


# ───────────────────────────────────────────── BoE
def boe(man: dict, kunye: dict) -> list[dict]:
    satir, sorun = [], []
    kural = man.get(BOE_KURAL)
    if not kural or "published at 12 noon on a Thursday" not in _duz(_metin(kural["dosya"])):
        kunye["boe"] = {"karar": 0, "sorun": ["BoE yayım kuralı (12 noon) arşivde yok ya da metni değişmiş"]}
        return []
    tarihler = {}
    for u, v in sorted(man.items()):
        if not re.search(r"bankofengland\.co\.uk/monetary-policy-summary-and-minutes/\d{4}/[a-z]+-\d{4}$", u):
            continue
        p = re.search(r"Published on (\d{1,2}) ([A-Za-z]+) (\d{4})", _duz(_metin(v["dosya"])))
        if not p or p.group(2) not in AYLAR:
            sorun.append(f"{u.rsplit('/', 1)[-1]}: yayım tarihi okunamadı")
            continue
        g = date(int(p.group(3)), AYLAR[p.group(2)], int(p.group(1)))
        if not BAS <= g <= BIT:
            continue
        if g.weekday() != 3:
            sorun.append(f"{g}: perşembe değil — kural (perşembe 12:00) bu tarihe uygulanamaz, yazılmadı")
            continue
        tarihler[g] = u
    for g, u in sorted(tarihler.items()):
        satir.append({"olay": "BoE_karar", "tarih": g.isoformat(), "yerel_saat": "12:00", "bolge": "Europe/London",
                      "kaynak": u, "not": "saat: BoE'nin yayım kuralı (MPC özeti perşembe 12:00)"})
    # Bank Rate değişiklik listesinde olup MPC özetleri arasında olmayan kararlar.
    oran = man.get(BOE_ORAN)
    if oran:
        ay3 = {a[:3]: i + 1 for i, a in enumerate(AY_ADI)}
        for gg, aa, yy in re.findall(r"\b(\d{2}) ([A-Z][a-z]{2}) (\d{2})\b", _duz(_metin(oran["dosya"]))):
            if aa not in ay3:
                continue
            g = date(2000 + int(yy), ay3[aa], int(gg))
            if BAS <= g <= BIT and g not in tarihler:
                sorun.append(f"{g}: Bank Rate değişti, MPC özet listesinde yok (olağanüstü karar); saat kaynakta "
                             f"yok — yazılmadı")
    kunye["boe"] = {"karar": len(satir), "sorun": sorun}
    return satir


def main() -> int:
    man = _manifest()
    kunye: dict = {}
    satir = fomc(man, kunye) + bls("empsit", "NFP", kunye) + bls("cpi", "CPI", kunye) + ecb(man, kunye) \
        + boe(man, kunye)
    df = pd.DataFrame(satir, columns=["olay", "tarih", "yerel_saat", "bolge", "kaynak", "not"])
    df = df.sort_values(["tarih", "yerel_saat", "olay"]).reset_index(drop=True)
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CIKTI, index=False)
    KUNYE.write_text(json.dumps(kunye, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(df["olay"].value_counts().to_string())
    for k, v in kunye.items():
        for s in v.get("sorun", []):
            print(f"  {k}: {s}")
        if v.get("yayimi_olmayan_referans_ayi"):
            print(f"  {k}: yayımı olmayan referans ayı {v['yayimi_olmayan_referans_ayi']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
