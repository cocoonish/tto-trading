#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ABD'NİN ORTA DOĞU UYARISI (19.10.2026) — yazının bütün sayıları buradan.

Girdiler (hepsi depoda, donmuş):
  veri/ham/elcilik/<ülke>/    on iki ABD temsilciliğinin uyarı LİSTELERİ ve uyarı metinleri (bulut arşivi). Uyarı tarihi
                              listedeki adresten okunur (adres tahmin edilmez); dili uyarının kendi metninden.
  veri/olaylar.json           elle tutulan olgular: ABD'nin İran topraklarını vurduğu günler, iptal edilen saldırılar,
                              tarihsel emsaller, bağlam cümleleri; her olgu kaynağın kendi metninde geçen bir alıntıya
                              bağlı (dogrula.py arar)
  veri/ham/polymarket/        tahmin piyasası fiyat geçmişi (bulut arşivi)
  veri/ham/cnbc/              Mayıs 2025 → kapanışlar (bulut arşivi; Brent analizinin uzun serisiyle örtüşen günde birebir)
  veri/ham/gpr/               jeopolitik risk endeksi (Caldara–Iacoviello, günlük)

Ölçüler:
  1. uyarı takvimi: her temsilciliğin hangi gün uyarı yayımladığı; ortak kapsam (on ikisinin de listesinin ulaştığı ilk
     gün); DALGA = aynı gün en az on temsilcilik. Ardışık dalga günleri (aradaki boşluk ≤ 3 gün) tek dönemdir.
  2. dalganın dili: her temsilciliğin o günkü metnindeki en sert talimat (dört kademe, KADEME). İran ve Yemen kalıcı
     "seyahat etmeyin" altında olduğu için kademeye girmez.
  3. dalga → saldırı: dalgadan önceki son ve sonraki ilk ABD saldırısı (İran toprağına), gün olarak.
  4. 8 Ekim ve 18 Ekim metinlerinin kelime düzeyinde benzerliği ve değişen ifadeler.
  5. tahmin piyasaları: şimdiki fiyatlar, uyarı günlerindeki fiyatlar, geçmiş iki saldırının öncesindeki fiyatlar.
  6. piyasa tepkisi: dalgadan önceki kapanıştan 1 ve 5 işlem günü sonrasına Brent, altın, S&P 500, VIX, ABD 10 yıllık,
     USD/TRY, BIST 100; ve aynı değişimin 2026'daki bütün 5 günlük pencereler içindeki yüzdeliği.
  7. GPR: bugünkü 30 günlük düzeyin tarihteki yeri.
"""
from __future__ import annotations

import collections
import difflib
import glob
import gzip
import hashlib
import importlib.util
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
HAM = VERI / "ham"
BRENT = BURASI.parent / "BrentSenaryo" / "veri"
CIKTI = VERI / "olcum.json"
#: Yazının adresi (tek tanım: figürler ve kapı buradan okur).
sys.path.insert(0, str(BURASI))
from ayar import SLUG  # noqa: E402  (tek tanım)

POSTLAR = {"sa": "Suudi Arabistan", "ae": "BAE", "kw": "Kuveyt", "jo": "Ürdün", "bh": "Bahreyn", "om": "Umman",
           "ir": "İran", "qa": "Katar", "iq": "Irak", "lb": "Lübnan", "ye": "Yemen", "il": "İsrail"}
#: Kalıcı "seyahat etmeyin" altındaki iki temsilcilik: metinleri her dalgada en sert kademeyi taşır, kademeye girmez.
KALICI = ("ir", "ye")
DALGA_ESIK = 10
DONEM_ARALIK = 3
#: Uyarı dilinin kademeleri: en serti önce. Metinde geçen ilk eşleşme o temsilciliğin o günkü kademesidir.
KADEME = [
    (4, "sığın ya da derhal ayrıl", r"shelter.in.place|depart (?:\w+ )?immediately|leave (?:\w+ )?(?:now|immediately)|immediately depart"),
    (3, "ayrılmayı düşün", r"consider departing|prepared to depart"),
    (2, "seyahati yeniden düşün", r"reconsider (?:any )?travel"),
    (1, "tetikte ol", r"vigilance|caution"),
]
#: Personelin ayrılış statüsü (ordered / authorized departure): metin ya yeni bir ayrılış kararını ya da sürmekte olan
#: statüyü anar. Statü bir tahliye kararıdır, güvenlik uyarısı değil; dalganın tipini ayıran ölçü budur.
AYRILIS = r"ordered (?:the )?departure|authorized (?:the )?departure"
UFUK = (1, 5)
ARAC = {"brent": ("Brent", "yuzde"), "altin": ("Altın", "yuzde"), "spx": ("S&P 500", "yuzde"),
        "vix": ("VIX", "puan"), "us10y": ("ABD 10 yıllık", "bp"), "try": ("USD/TRY", "yuzde"),
        "bist100": ("BIST 100", "yuzde")}
#: Ölçümün günü ve son KAPANMIŞ işlem günü (19 Ekim Pazartesi barı ölçüm anında kapanmamıştı).
BUGUN = date(2026, 10, 19)
SON_KAPANIS = date(2026, 10, 16)
AY = {m: i + 1 for i, m in enumerate("january february march april may june july august september october "
                                      "november december".split())}


def _oz(yol: Path) -> str:
    return hashlib.sha256(yol.read_bytes()).hexdigest()


def jeffreys(k: int, n: int, a: float = 0.05) -> tuple[float, float]:
    """Binom oranı için Jeffreys aralığı (Beta(k+½, n−k+½) yüzdelikleri)."""
    from scipy.stats import beta
    lo = 0.0 if k == 0 else float(beta.ppf(a / 2, k + 0.5, n - k + 0.5))
    hi = 1.0 if k == n else float(beta.ppf(1 - a / 2, k + 0.5, n - k + 0.5))
    return lo, hi


def _normal():
    spec = importlib.util.spec_from_file_location("brent_km", BURASI.parent / "BrentSenaryo" / "kaynak_metin.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.normal


# ─────────────────────────────────────────────────────────────── 1. uyarı takvimi
def _kunye() -> dict:
    out = {}
    for p in sorted(HAM.glob("kunye_*.json")):
        out.update(json.loads(p.read_text(encoding="utf-8")))
    return out


def uyari_listesi() -> tuple[dict, dict]:
    """Temsilcilik → {gün: {adres}}; yalnız uyarı LİSTESİ sayfalarından (category/alert) okunur."""
    kun = _kunye()
    liste: dict = collections.defaultdict(lambda: collections.defaultdict(set))
    sayfa: dict = collections.defaultdict(int)
    for yol, k in kun.items():
        if not yol.startswith("elcilik/") or k.get("durum") != 200 or "category/alert" not in k["url"]:
            continue
        cc = yol.split("/")[1]
        sayfa[cc] += 1
        ham = gzip.decompress((HAM / yol).read_bytes()).decode("utf-8", errors="replace")
        for m in re.finditer(r'href="(https?://' + cc + r'\.usembassy\.gov/[^"#?]*?(' + "|".join(AY) +
                             r')-(\d{1,2})-(20\d\d)[^"#?]*)"', ham):
            g = date(int(m.group(4)), AY[m.group(2)], int(m.group(3)))
            liste[cc][g].add(m.group(1).rstrip("/") + "/")
    return liste, dict(sayfa)


def uyari_metinleri(normal) -> dict:
    """Adres → normalleştirilmiş metin (indirilmiş uyarılar)."""
    idx = json.loads((VERI / "kaynak_metin.json").read_text(encoding="utf-8"))
    out = {}
    for yol, v in idx.items():
        if yol.startswith("elcilik/") or "usembassy.gov" in v["url"]:
            out.setdefault(v["url"].rstrip("/") + "/", gzip.decompress((VERI / v["metin"]).read_bytes()).decode())
    return out


def olay_bolumu(t: str) -> str:
    """Uyarının "Event" bölümü (işlem ve iletişim bilgileri hariç); adresler silinir."""
    i = t.find("Event")
    i = 0 if i < 0 else i
    son = [x for x in (t.find("Actions to Take", i), t.find("Assistance", i)) if x > 0]
    s = t[i:min(son) if son else i + 3000]
    return re.sub(r"https?://\S+", "", s)


def kademe(t: str) -> int:
    for k, _, desen in KADEME:
        if re.search(desen, t, re.I):
            return k
    return 0


# ─────────────────────────────────────────────────────────────── saldırı günleri
def saldiri_gunleri(olaylar: dict) -> list[date]:
    gunler = set()
    for s in olaylar["saldiri"]:
        a, b = date.fromisoformat(s["bas"]), date.fromisoformat(s["bit"])
        while a <= b:
            gunler.add(a)
            a += timedelta(days=1)
    return sorted(gunler)


def dalgalar(liste: dict, metin: dict, saldiri: list[date]) -> dict:
    kapsam = {cc: min(g) for cc, g in liste.items()}
    ortak = max(v for cc, v in kapsam.items() if cc != "ye")   # Yemen listesi 2023'e kadar on uyarı taşır
    gunluk = collections.Counter()
    for cc, g in liste.items():
        for d in g:
            gunluk[d] += 1
    dalga_gun = sorted(d for d, n in gunluk.items() if n >= DALGA_ESIK and d >= ortak)
    donemler: list[list[date]] = []
    for d in dalga_gun:
        if donemler and (d - donemler[-1][-1]).days <= DONEM_ARALIK:
            donemler[-1].append(d)
        else:
            donemler.append([d])
    out = []
    for gun in donemler:
        t0 = gun[0]
        postlar = sorted(cc for cc in liste if t0 in liste[cc])
        kad = {}
        eksik = []
        for cc in postlar:
            if cc in KALICI:
                continue
            ks = [kademe(olay_bolumu(metin[u])) for u in liste[cc][t0] if u in metin]
            if ks:
                kad[cc] = max(ks)
            else:
                eksik.append(cc)
        ayrilis = sorted({cc for cc in postlar for u in liste[cc][t0]
                          if u in metin and re.search(AYRILIS, metin[u], re.I)})
        once = [s for s in saldiri if s < t0]
        sonra = [s for s in saldiri if s > t0]               # öngörü penceresi dalganın ERTESİ günü açılır
        sonraki = (sonra[0] - t0).days if sonra else None
        ayni_gun = t0 in saldiri
        son_gun = (t0 - once[-1]).days if once else None
        atesli = ayni_gun or (son_gun is not None and son_gun <= 7)
        out.append({
            "bas": t0.isoformat(), "bit": gun[-1].isoformat(), "gun_sayisi": len(gun),
            "post_sayisi": max(gunluk[d] for d in gun), "postlar_ilk_gun": postlar,
            "kademe": kad, "kademe_eksik": eksik, "ayrilis_post": ayrilis,
            "kademe_dagilim": {str(k): sum(1 for v in kad.values() if v == k) for k, *_ in KADEME},
            "en_sert": max(kad.values()) if kad else None,
            "son_saldiridan_gun": son_gun, "ayni_gun_saldiri": ayni_gun, "atesli": atesli,
            "sonraki_saldiriya_gun": sonraki,
            "sonraki_saldiri": sonra[0].isoformat() if sonra else None,
            "acik_gun": (BUGUN - t0).days,
        })
    once7 = {}
    for hedef in (date(2026, 2, 28), date(2025, 6, 22)):
        once7[hedef.isoformat()] = {(hedef - timedelta(days=k)).isoformat(): gunluk.get(hedef - timedelta(days=k), 0)
                                   for k in range(7, 0, -1)}
        once7[hedef.isoformat()]["gun"] = gunluk.get(hedef, 0)
    # ateşkesten sonraki saldırı BAŞLANGIÇLARI: önceki ABD saldırısından yediden fazla gün sonra gelen ilk saldırı günü
    # (sakin dalga tanımıyla aynı eşik) · her birinden önceki yedi günde uyarı yayımlayan temsilcilik sayısının en çoğu
    baslangic = {}
    for i, s in enumerate(saldiri):
        if s <= date(2026, 4, 7) or (s - saldiri[i - 1]).days <= 7:
            continue
        pencere = [gunluk.get(s - timedelta(days=k), 0) for k in range(7, 0, -1)]
        baslangic[s.isoformat()] = {"onceki_saldiri": saldiri[i - 1].isoformat(), "once7_en_cok": max(pencere),
                                    "once7_dalga": any(n >= DALGA_ESIK for n in pencere), "gun": gunluk.get(s, 0)}
    seri =[[d.isoformat(), gunluk.get(d, 0)] for d in pd.date_range(ortak, BUGUN).date]
    return {"kapsam_bas": {cc: d.isoformat() for cc, d in sorted(kapsam.items())}, "ortak_kapsam": ortak.isoformat(),
            "esik": DALGA_ESIK, "donem_aralik": DONEM_ARALIK, "donemler": out, "once7": once7, "baslangic": baslangic, "gunluk": seri,
            "uyari_sayisi": {cc: sum(len(v) for v in g.values()) for cc, g in sorted(liste.items())}}


def taban_oran(donemler: list[dict]) -> dict:
    """Dalga → ERTESİ günden başlayarak 7 ve 14 gün içinde ABD saldırısı. Sonucu henüz kapanmamış dalga (açık gün ≤
    ufuk ve saldırı yok) sayılmaz. İki küme: ATEŞLİ (dalga günü ya da önceki 7 günde ABD İran'ı vurmuş) ve SAKİN."""
    out = {}
    for ad, kosul in (("tum", lambda d: True),
                      ("sakin", lambda d: not d["atesli"]),
                      ("atesli", lambda d: d["atesli"])):
        for h in (7, 14):
            kap = [d for d in donemler if kosul(d) and (d["sonraki_saldiriya_gun"] is not None and
                                                        d["sonraki_saldiriya_gun"] <= h or d["acik_gun"] > h)]
            k = sum(1 for d in kap if d["sonraki_saldiriya_gun"] is not None and d["sonraki_saldiriya_gun"] <= h)
            lo, hi = jeffreys(k, len(kap)) if kap else (None, None)
            out[f"{ad}_{h}"] = {"k": k, "n": len(kap), "oran": k / len(kap) if kap else None, "alt": lo, "ust": hi,
                                "donemler": [d["bas"] for d in kap]}
    return out


# ─────────────────────────────────────────────────────────────── 4. metin farkı
def metin_farki(liste: dict, metin: dict) -> dict:
    out = {}
    for cc in POSTLAR:
        a = [u for u in liste[cc].get(date(2026, 10, 8), ()) if u in metin and "update" not in u]
        b = [u for u in liste[cc].get(date(2026, 10, 18), ()) if u in metin and "update" not in u]
        if not a or not b:
            continue
        ta, tb = olay_bolumu(metin[sorted(a)[0]]).split(), olay_bolumu(metin[sorted(b)[-1]]).split()
        sm = difflib.SequenceMatcher(None, ta, tb)
        degisen = [(" ".join(ta[i1:i2]), " ".join(tb[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
        out[cc] = {"benzerlik": sm.ratio(), "kelime_8": len(ta), "kelime_18": len(tb), "degisen": degisen[:12],
                   "eklenen_kelime": sum(j2 - j1 for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("insert", "replace")),
                   "adres_8": sorted(a)[0], "adres_18": sorted(b)[-1]}
    ortak = [cc for cc in out if all(len(x[1]) < 80 for x in out[cc]["degisen"])]
    out["_ozet"] = {"post": len([k for k in out if not k.startswith("_")]),
                    "benzerlik_medyan": float(np.median([v["benzerlik"] for k, v in out.items() if not k.startswith("_")])),
                    "kucuk_degisiklik": ortak}
    return out


# ─────────────────────────────────────────────────────────────── 5. tahmin piyasaları
def _pm(mid: str, ad: str = "gunluk") -> list[tuple[datetime, float]]:
    p = HAM / "polymarket" / f"gecmis_{mid}_{ad}.json.gz"
    if not p.exists():
        return []
    return [(datetime.fromtimestamp(x["t"], timezone.utc), float(x["p"]))
            for x in json.loads(gzip.decompress(p.read_bytes()))["history"]]


def _pm_bilgi(mid: str) -> dict:
    m = json.loads(gzip.decompress((HAM / "polymarket" / f"piyasa_{mid}.json.gz").read_bytes()))
    return {"soru": m["question"], "kapali": bool(m.get("closed")), "sonuc": m.get("outcomePrices"),
            "hacim": float(m.get("volume") or 0), "bitis": (m.get("endDate") or "")[:10]}


def _deger(seri, an: datetime):
    """O anda ya da hemen öncesinde son fiyat."""
    once = [p for t, p in seri if t <= an]
    return once[-1] if once else None


def _gun(seri, gun: str):
    """Günlük seride o TARİHİN noktası (Polymarket günlük noktası günün ilk dakikalarında damgalanır)."""
    x = [p for t, p in seri if t.date().isoformat() == gun]
    return x[0] if x else None


def _saat(seri, an: datetime):
    """Saatlik seride o SAATİN noktası."""
    x = [p for t, p in seri if t.replace(minute=0, second=0, microsecond=0) == an]
    return x[0] if x else None


def tahmin() -> dict:
    out = {}
    s = _pm("4641065", "saatlik")
    g = _pm("4641065")
    out["abd_31ekim"] = {**_pm_bilgi("4641065"), "evet_son": g[-1][1], "son_an": g[-1][0].isoformat(),
                         "saldiri_son": 1 - g[-1][1],
                         "gunluk": [[t.date().isoformat(), 1 - p] for t, p in g],
                         "saatlik_19ekim": [[t.isoformat(), 1 - p] for t, p in s if t.date() >= date(2026, 10, 18)],
                         "ilk_gun": [g[0][0].date().isoformat(), 1 - g[0][1]],
                         "en_yuksek": max((1 - p, t.date().isoformat()) for t, p in g),
                         "19eylul": 1 - _gun(g, "2026-09-19"),
                         "8ekim_once": 1 - _saat(s, datetime(2026, 10, 8, 16, tzinfo=timezone.utc)),
                         "8ekim_sonra": 1 - _saat(s, datetime(2026, 10, 8, 18, tzinfo=timezone.utc)),
                         "18ekim_aralik": [1 - max(p for t, p in s if t.date() == date(2026, 10, 18)),
                                           1 - min(p for t, p in s if t.date() == date(2026, 10, 18))],
                         "19ekim_sicrama": max((1 - p, t.isoformat()) for t, p in s if t.date() == date(2026, 10, 19))}
    gun = {}
    for t, p in g:                                     # aynı güne düşen iki noktadan sonuncusu
        gun[t.date()] = 1 - p
    son10 = [v for d, v in gun.items() if d >= BUGUN - timedelta(days=10)]
    out["abd_31ekim"]["son10_aralik"] = [min(son10), max(son10)]
    out["abd_31ekim"]["son10_bas"] = (BUGUN - timedelta(days=10)).isoformat()
    for ad, mid in (("israil_31ekim", "3399459"), ("israil_30kasim", "3902370"), ("israil_31aralik", "3399468"),
                    ("isgal_2026", "665374"), ("anlasma_31aralik", "2696747"), ("savas_ilani_2026", "1170144"),
                    ("hurmuz_31aralik", "5087228"), ("anlasma_30kasim", "3491438")):
        g2 = _pm(mid)
        out[ad] = {**_pm_bilgi(mid), "evet_son": g2[-1][1], "son_an": g2[-1][0].isoformat()}
    # geçmiş iki saldırının öncesi: piyasa ne diyordu
    gecmis = {}
    for ad, mid, gunler in (("haziran2025", "532741", ["2025-06-09", "2025-06-11", "2025-06-12", "2025-06-20", "2025-06-21"]),
                            ("subat2026", "1198479", ["2026-02-20", "2026-02-23", "2026-02-26", "2026-02-27", "2026-02-28"]),
                            ("ocak2026", "1139942", ["2026-01-14", "2026-01-21", "2026-01-28", "2026-01-31"])):
        g3 = _pm(mid)
        gecmis[ad] = {**_pm_bilgi(mid),
                      "fiyat": {d: _gun(g3, d) for d in gunler},
                      "en_yuksek": max((p, t.date().isoformat()) for t, p in g3),
                      "seri": [[t.date().isoformat(), p] for t, p in g3]}
    out["gecmis"] = gecmis
    out["gunluk_hiz"] = gunluk_hiz(out)
    return out


# vadesi farklı olasılıkları kıyaslamak için: kalan süreye SABİT günlük olasılık (1 − (1 − p)^(1/gün)). Vadeler çözüm
# kuralının kendi saatinden (İran saati 23:59 = 20:29 UTC; ABD doğu saati 23:59 = ertesi gün 03:59/04:59 UTC).
VADE = {"abd_31ekim": datetime(2026, 10, 31, 20, 29, tzinfo=timezone.utc),
        "israil_31ekim": datetime(2026, 10, 31, 20, 29, tzinfo=timezone.utc),
        "israil_30kasim": datetime(2026, 11, 30, 20, 29, tzinfo=timezone.utc),
        "israil_31aralik": datetime(2026, 12, 31, 20, 29, tzinfo=timezone.utc),
        "haziran2025": datetime(2025, 7, 1, 3, 59, tzinfo=timezone.utc),
        "ocak2026": datetime(2026, 2, 1, 4, 59, tzinfo=timezone.utc),
        "subat2026": datetime(2026, 3, 1, 4, 59, tzinfo=timezone.utc)}
HIZ_GUN = {"haziran2025": "2025-06-21", "subat2026": "2026-02-27", "ocak2026": "2026-01-14"}


def _hiz(p: float, gun: float) -> float:
    return 1 - (1 - p) ** (1 / gun)


def gunluk_hiz(T: dict) -> dict:
    out = {}
    a = T["abd_31ekim"]
    an = datetime.fromisoformat(a["son_an"])
    g = (VADE["abd_31ekim"] - an).total_seconds() / 86400
    out["abd_31ekim"] = {"p": a["saldiri_son"], "gun": g, "hiz": _hiz(a["saldiri_son"], g)}
    s = {k: T[k]["evet_son"] for k in ("israil_31ekim", "israil_30kasim", "israil_31aralik")}
    an_i = datetime.fromisoformat(T["israil_31ekim"]["son_an"])
    g1 = (VADE["israil_31ekim"] - an_i).total_seconds() / 86400
    g2 = (VADE["israil_30kasim"] - VADE["israil_31ekim"]).total_seconds() / 86400
    g3 = (VADE["israil_31aralik"] - VADE["israil_30kasim"]).total_seconds() / 86400
    out["israil_ekim"] = {"p": 1 - s["israil_31ekim"], "gun": g1, "hiz": _hiz(1 - s["israil_31ekim"], g1)}
    k2 = 1 - s["israil_30kasim"] / s["israil_31ekim"]          # Ekim'i atlatırsa Kasım'da bozulma
    k3 = 1 - s["israil_31aralik"] / s["israil_30kasim"]
    out["israil_kasim"] = {"p": k2, "gun": g2, "hiz": _hiz(k2, g2)}
    out["israil_aralik"] = {"p": k3, "gun": g3, "hiz": _hiz(k3, g3)}
    for ad, gun in HIZ_GUN.items():
        sr = _pm({"haziran2025": "532741", "subat2026": "1198479", "ocak2026": "1139942"}[ad])
        t, p = next((t, p) for t, p in sr if t.date().isoformat() == gun)
        kal = (VADE[ad] - t).total_seconds() / 86400
        out[ad] = {"tarih": gun, "p": p, "gun": kal, "hiz": _hiz(p, kal)}
    return out


# ─────────────────────────────────────────────────────────────── 6. piyasa tepkisi
def kapanislar() -> pd.DataFrame:
    seriler = {}
    for ad in ARAC:
        j = json.loads(gzip.decompress((HAM / "cnbc" / f"{ad}.json.gz").read_bytes()))
        s = pd.Series({pd.Timestamp(b["tradeTime"][:8]): float(b["close"]) for b in j["barData"]["priceBars"]})
        # Yalnız hafta içi kapanışlar: döviz serisi pazar barı da taşıyor ve "5 işlem günü" o seride 5 takvim
        # barına kayıyordu; bütün araçlar aynı işlem günü ızgarasında ölçülür.
        seriler[ad] = s[(s.index.date <= SON_KAPANIS) & (s.index.dayofweek < 5)]
    return pd.DataFrame(seriler).sort_index()


def _degis(s: pd.Series, i: int, h: int, birim: str):
    if i + h >= len(s):
        return None
    a, b = s.iloc[i], s.iloc[i + h]
    return (b / a - 1) if birim == "yuzde" else (b - a) * (100 if birim == "bp" else 1)


def tepki(df: pd.DataFrame, gunler: list[str]) -> dict:
    out = {}
    for gun in gunler:
        t = pd.Timestamp(gun)
        r = {}
        for c, (_, birim) in ARAC.items():
            s = df[c].dropna()
            i = s.index.searchsorted(t, side="left") - 1          # dalgadan ÖNCEKİ son kapanış
            if i < 0:
                continue
            x = {"baz_tarih": s.index[i].date().isoformat(), "baz": float(s.iloc[i])}
            for h in UFUK:
                v = _degis(s, i, h, birim)
                if v is not None:
                    x[f"d{h}"] = v
                    x[f"t{h}"] = s.index[i + h].date().isoformat()
            # aynı ufkun 2026'daki bütün pencereleri içindeki yüzdelik (mutlak değişim)
            s26 = s[s.index >= "2026-01-01"]
            hepsi = [_degis(s26, j, 5, birim) for j in range(len(s26) - 5)]
            if "d5" in x:
                x["yuzdelik5"] = float(np.mean([abs(v) <= abs(x["d5"]) for v in hepsi]))
            r[c] = x
        out[gun] = r
    return out


def son_hafta(df: pd.DataFrame) -> dict:
    """Uyarıdan önceki hafta: 9 Ekim → 16 Ekim kapanışları."""
    out = {}
    for c, (_, birim) in ARAC.items():
        s = df[c].dropna()
        a, b = s[s.index <= "2026-10-09"].iloc[-1], s.iloc[-1]
        out[c] = {"bas": float(a), "son": float(b), "son_tarih": s.index[-1].date().isoformat(),
                  "degisim": (b / a - 1) if birim == "yuzde" else (b - a) * (100 if birim == "bp" else 1),
                  "gun16": _degis(s, len(s) - 2, 1, birim)}
        # aynı haftanın 2026'daki bütün 5 günlük pencereler içindeki yüzdeliği (mutlak) ve pencerelerin medyanı
        s26 = s[s.index >= "2026-01-01"]
        hepsi = [_degis(s26, j, 5, birim) for j in range(len(s26) - 5)]
        n = int((s.index > s[s.index <= "2026-10-09"].index[-1]).sum())
        out[c]["gun_sayisi"] = n
        out[c]["yuzdelik5"] = float(np.mean([abs(v) <= abs(out[c]["degisim"]) for v in hepsi]))
        out[c]["medyan5_2026"] = float(np.median(hepsi))
    return out


# ─────────────────────────────────────────────────────────────── 7. GPR
def gpr() -> dict:
    """Jeopolitik risk endeksi (Caldara–Iacoviello, günlük). Kaynak bulutun bugün indirdiği dosyadır; endeks geriye
    dönük yeniden hesaplanabildiği için eski bir indirmeyle EKLENMEZ — eski indirme yalnız revizyonun büyüklüğünü ölçer."""
    p = next(iter(sorted((HAM / "gpr").glob("*recent*.gz"))))
    ek = pd.read_excel(gzip.open(p))
    ek["tarih"] = pd.to_datetime(ek["date"])
    g = ek.set_index("tarih")[["GPRD", "GPRD_ACT", "GPRD_THREAT"]].dropna().sort_index()
    eski = pd.read_csv(BRENT / "gpr_gunluk.csv.gz", parse_dates=["tarih"]).set_index("tarih").sort_index()
    ortak = g.index.intersection(eski.index)
    fark = (g.loc[ortak, "GPRD"] - eski.loc[ortak, "GPRD"]).abs()
    fark = {"gun": int(len(ortak)), "azami": float(fark.max()), "ayni_pay": float((fark < 1e-6).mean())}
    r = g.rolling(30, min_periods=30).mean().dropna()
    son = r.iloc[-1]
    tum = r["GPRD"]
    tepe26 = r[r.index >= "2026-01-01"]["GPRD"]
    return {"son_gun": r.index[-1].date().isoformat(), "revizyon": fark, "dosya_ozu": _oz(p),
            "bas_gun": g.index[0].date().isoformat(),
            "gpr30": float(son["GPRD"]), "tehdit30": float(son["GPRD_THREAT"]), "eylem30": float(son["GPRD_ACT"]),
            "yuzdelik": float((tum < son["GPRD"]).mean()), "ortalama_tum": float(g["GPRD"].mean()),
            "tepe_2026": [float(tepe26.max()), tepe26.idxmax().date().isoformat()],
            "gunler": {d: float(r["GPRD"].asof(pd.Timestamp(d))) for d in
                       ("2025-06-22", "2026-02-27", "2026-03-15", "2026-07-17", "2026-08-01", "2026-09-01",
                        "2026-09-19", "2026-10-08")},
            "seri": [[d.date().isoformat(), round(float(v), 1)] for d, v in tum[tum.index >= "2025-01-01"].items()]}


def main() -> int:
    normal = _normal()
    olaylar = json.loads((VERI / "olaylar.json").read_text(encoding="utf-8"))
    liste, sayfa = uyari_listesi()
    metin = uyari_metinleri(normal)
    saldiri = saldiri_gunleri(olaylar)
    dal = dalgalar(liste, metin, saldiri)
    df = kapanislar()
    gunler = [d["bas"] for d in dal["donemler"] if d["bas"] < "2026-10-18"] + ["2025-06-22", "2025-06-11", "2026-02-23"]
    olcum = {
        "kunye": {"olaylar": _oz(VERI / "olaylar.json"), "olcum_py": _oz(Path(__file__)),
                  "kaynak_metin": _oz(VERI / "kaynak_metin.json"),
                  "kunye_dosyalari": {p.name: _oz(p) for p in sorted(HAM.glob("kunye_*.json"))},
                  "cnbc": {p.name: _oz(p) for p in sorted((HAM / "cnbc").glob("*.json.gz"))},
                  "bugun": BUGUN.isoformat(), "son_kapanis": SON_KAPANIS.isoformat()},
        "liste_sayfasi": sayfa,
        "saldiri_gunleri": [d.isoformat() for d in saldiri],
        "saldiri_sonrasi_2026": [d.isoformat() for d in saldiri if d > date(2026, 4, 7)],
        "uyari": dal,
        "taban": taban_oran(dal["donemler"]),
        "metin_farki": metin_farki(liste, metin),
        "tahmin": tahmin(),
        "tepki": tepki(df, gunler),
        "son_hafta": son_hafta(df),
        "gpr": gpr(),
        "tarihsel": [{k: v for k, v in t.items() if k != "kaynaklar"} | {
            "gun": (date.fromisoformat(t["sonraki_abd_saldirisi"]) - date.fromisoformat(t["tarih"])).days
            if t.get("sonraki_abd_saldirisi") else None} for t in olaylar["tarihsel"]],
    }
    CIKTI.write_text(json.dumps(olcum, ensure_ascii=False, indent=1, default=float) + "\n", encoding="utf-8")
    print(f"✓ {CIKTI.relative_to(BURASI)}")
    for d in dal["donemler"]:
        print(f"  {d['bas']}→{d['bit']} post {d['post_sayisi']:>2} kademe {d['kademe_dagilim']} en sert {d['en_sert']} "
              f"önce {d['son_saldiridan_gun']} sonra {d['sonraki_saldiriya_gun']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
