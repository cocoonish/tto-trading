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
ölçüldü). Saat Fed'in aylık etkinlik takviminden okunur (`fed_takvim`); takvim o gün
için okunamazsa basın toplantısı YAZILMAZ.

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
    adlar = ["manifest.json", "manifest2.json"] + sorted(p.name for p in HAM.glob("manifest3_*.json"))
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


def fed_takvim(man: dict) -> dict[date, list[tuple[str, str, str]]]:
    """Fed'in aylık etkinlik takviminden FOMC etkinlikleri: {gün: [(saat, etkinlik, adres)]}.

    Sayfa biçimi `arsiv_takvim3` koşusunda ölçülür; tanınmayan biçimde boş döner ve
    basın toplantıları yazılmaz (`fomc` sebebi künyeye yazar)."""
    out: dict[date, list[tuple[str, str, str]]] = {}
    for u, v in man.items():
        m = re.search(r"federalreserve\.gov/newsevents/(20\d{2})-([a-z]+)\.htm$", u)
        if not m or m.group(2).capitalize() not in AYLAR:
            continue
        yil, ay = int(m.group(1)), AYLAR[m.group(2).capitalize()]
        s = _duz(_metin(v["dosya"]))
        # Biçim (16.10.2026'da ölçülecek): gün başlığı ve saatli etkinlik satırları.
        for g in re.finditer(r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),? "
                             r"(?:" + "|".join(AY_ADI) + r") (\d{1,2})(.*?)(?=(?:Monday|Tuesday|Wednesday|Thursday"
                             r"|Friday|Saturday|Sunday),? (?:" + "|".join(AY_ADI) + r") \d{1,2}|\Z)", s):
            gun = date(yil, ay, int(g.group(1)))
            for e in re.finditer(r"(\d{1,2}):(\d{2}) ?([ap])\.m\.?\s*([^0-9]{0,120})", g.group(2)):
                ad = e.group(4).strip()
                if re.search(r"(?i)FOMC|Press Conference|Federal Open Market", ad):
                    out.setdefault(gun, []).append((_saat(int(e.group(1)), int(e.group(2)), e.group(3)), ad, u))
    return out


def fomc(man: dict, kunye: dict) -> list[dict]:
    satir, sorun = [], []
    bloklar = []
    for u, v in man.items():
        if "federalreserve.gov/monetarypolicy/fomc" in u and ("calendars" in u or "historical" in u):
            bloklar += _fomc_bloklar(_metin(v["dosya"]))
    takvim = fed_takvim(man)
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
        etk = [e for e in takvim.get(g, []) if re.search(r"(?i)press conference", e[1])]
        if not etk:
            sorun.append(f"{g}: basın toplantısı var, saati Fed'in etkinlik takviminde okunamadı — yazılmadı")
            continue
        if len({e[0] for e in etk}) > 1:
            sorun.append(f"{g}: takvimde birden çok basın toplantısı saati {sorted({e[0] for e in etk})} — yazılmadı")
            continue
        satir.append({"olay": "FOMC_basin", "tarih": g.isoformat(), "yerel_saat": etk[0][0],
                      "bolge": "America/New_York", "kaynak": etk[0][2],
                      "not": "" if olagan else "olağanüstü toplantı"})
    kunye["fomc"] = {"karar": sum(1 for s in satir if s["olay"] == "FOMC_karar"),
                     "basin": sum(1 for s in satir if s["olay"] == "FOMC_basin"),
                     "takvim_gun": len(takvim), "sorun": sorun}
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
