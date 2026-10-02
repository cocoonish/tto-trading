#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND YAZISI (02.10.2026) — yayımlanan metni sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
pandas/numpy/plotly YOK: betik yalnız standart kütüphaneyle çalışır, ağa
çıkmaz, duvar saati okumaz (girdisi depodaki arşiv). Dört soru sorar:

1. ARŞİV — `veri/` altındaki her dosyanın sıkıştırılmamış içeriğinin özü
   künyedekiyle aynı mı, ve ölçüm dosyası bu özlerle mi üretilmiş? Girdi
   değişmişse yazının bütün sayıları gerekçesiz kalır.
2. METİN — yazının tablolarındaki ve cümlelerindeki her ölçülmüş sayı
   `veri/olcum.json` ile aynı mı? Beklenen değerler buraya ELLE yazılmaz;
   ölçüm dosyasından okunur ve yazının tabloları ayrıştırılıp hücre hücre
   karşılaştırılır. İki liste tutulsaydı bir gün sessizce ayrışırdı. Cümle
   aramaları boşluğu tek boşluğa indirir ve sayıdan sonraki eki siler.
3. BİÇİM — gövdede ASCII tire ile yazılmış eksi sayı ya da arkaya yazılmış
   yüzde işareti yok (eksi U+2212, yüzde önde).
4. FİGÜRLER — dokuz figür yayın dizininde var mı, metin her birini sırayla
   gömüyor mu, figürün içindeki "Şekil NN" başlığı gömmenin numarasıyla aynı
   mı, ve Şekil 02'deki her olayın günü metinde anılıyor mu?

Koşum:  python3 dogrula.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
SLUG = "oat-bund-2026-10-02"
MDX = KOK / "site/src/content/analiz" / f"{SLUG}.mdx"
SEKIL = KOK / "site/public/analiz" / SLUG

hatalar: list[str] = []
sayac = {"hucre": 0, "metin": 0, "arsiv": 0}
AY = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
      "Eylül", "Ekim", "Kasım", "Aralık"]


# ─────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 1, arti: bool = False) -> str:
    """Ondalık virgül, binlik nokta, eksi U+2212; sıfıra yuvarlanan değer işaretsiz."""
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if round(x, b) < 0 and float(s.replace(".", "").replace(",", ".")) != 0:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0) else s


def yz(x: float, b: int = 2, arti: bool = False) -> str:
    s = "%" + sayi(abs(x), b)
    sifir = float(sayi(abs(x), b).replace(".", "").replace(",", ".")) == 0
    if round(x, b) < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0 and not sifir) else s


def bp(x: float, b: int = 1, arti: bool = False) -> str:
    return f"{sayi(x, b, arti)} bp"


def gun(iso: str) -> str:
    """'2026-10-01' → '1 Ekim 2026'."""
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]} {iso[:4]}"


def tarih_ga(iso: str) -> str:
    """'2026-01-27' → '27 Ocak' (yılsız)."""
    return f"{int(iso[8:10])} {AY[int(iso[5:7])]}"


def gun_k(iso: str) -> str:
    return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"


# ─────────────────────────────────────────────── tablo ayrıştırma
def tablolar(metin: str) -> list[list[list[str]]]:
    out, blok = [], []
    for satir in metin.splitlines():
        s = satir.strip()
        if s.startswith("|") and s.endswith("|"):
            hucre = [h.strip().replace("**", "") for h in s[1:-1].split("|")]
            if not all(set(h) <= set("-: ") for h in hucre):
                blok.append(hucre)
        elif blok:
            out.append(blok)
            blok = []
    if blok:
        out.append(blok)
    return out


def tablo(tl: list, *baslik: str) -> list[list[str]]:
    """Başlık satırı verilen hücrelerle başlayan ilk tablo."""
    bulunan = [x for x in tl if x and tuple(x[0][:len(baslik)]) == baslik]
    if not bulunan:
        hatalar.append(f"tablo bulunamadı: {baslik!r}")
        return []
    return bulunan[0]


def hucre(t: list, ilk: str, sutun: int, beklenen: str, ad: str) -> None:
    sayac["hucre"] += 1
    for r in t:
        if r[0] == ilk:
            g = r[sutun] if sutun < len(r) else "(yok)"
            if g != beklenen:
                hatalar.append(f"{ad} · '{ilk}' sütun {sutun + 1}: metin {g!r}, ölçüm {beklenen!r}")
            return
    hatalar.append(f"{ad}: satır yok: {ilk!r}")


def _ek_sil(s: str) -> str:
    """Kesme işaretinden sonraki eki siler: "54,9'dan" → "54,9'". Kapı ekin
    doğruluğunu değil sayının kendisini sorar."""
    return re.sub(r"'[a-zçğıöşüâîû]+", "'", s)


def _duz(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("''", "'"))


def metinde(m: str, parca: str, ad: str) -> None:
    sayac["metin"] += 1
    if _ek_sil(_duz(parca)) not in _ek_sil(_duz(m)):
        hatalar.append(f"metinde yok ({ad}): {parca!r}")


def dogru(kosul: bool, mesaj: str) -> None:
    sayac["metin"] += 1
    if not kosul:
        hatalar.append(mesaj)


# ─────────────────────────────────────────────── 1 · arşiv
def arsiv() -> dict:
    kunye = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
    for ad, k in kunye["dosyalar"].items():
        sayac["arsiv"] += 1
        yol = VERI / ad
        if not yol.exists():
            hatalar.append(f"arşiv dosyası yok: {ad}")
            continue
        oz = hashlib.sha256(gzip.decompress(yol.read_bytes())).hexdigest()
        if oz != k["sha256"]:
            hatalar.append(f"arşiv özü künyeyle tutmuyor: {ad}")
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    sayac["arsiv"] += 1
    if o["arsiv"] != {ad: k["sha256"] for ad, k in kunye["dosyalar"].items()}:
        hatalar.append("ölçüm dosyası bu arşivle üretilmemiş (özler ayrışıyor) — olcum.py yeniden koşulmalı")
    return o


# ─────────────────────────────────────────────── 2 · metin
def govde(m: str) -> str:
    return m.split("\n---", 2)[-1] if m.startswith("---") else m


def _cap(o: dict, bas: str, son: str = "2026-10-01") -> dict:
    return next(r for r in o["capraz"] if r["bas"] == bas and r["son"] == son)


def rakamlar(m: str, o: dict) -> None:
    sv, d = o["seviye"], o["duyarlilik"]["2024–2026"]
    ey = _cap(o, "2026-08-31")
    beklenen = [bp(sv["spread"]), bp(o["hiz"]["10y_22"]["degisim"], 1, True), yz(ey["fx"], 2, True),
                yz(ey["eurgbp"], 2, True), yz(d["gbpusd"]["b"]["spr"] * 10, 2, True),
                yz(o["ileri"][0]["daha_acildi_payi"], 1)]
    blok = m[m.index('<ul class="rakamlar">'):m.index("</ul>", m.index('<ul class="rakamlar">'))]
    yazili = re.findall(r"<li><b>([^<]+)</b>", blok)
    sayac["hucre"] += len(beklenen)
    if yazili != beklenen:
        hatalar.append(f"rakam şeridi: metin {yazili}, ölçüm {beklenen}")
    metinde(blok, f"{AY[int(o['hiz']['10y_22']['son_gorulme'][5:7])]} {o['hiz']['10y_22']['son_gorulme'][:4]}",
            "hız son görülme")


def tablolar_sina(tl: list, o: dict) -> None:
    # gün içi saatler
    t = tablo(tl, "saat (Paris)")
    gi, p = o["gun_ici"], o["gun_ici_pencere"]
    noktalar = {"09:00": gi["09:00"], "14:15": gi["14:15"], "17:30": gi["17:30"],
                p["bas"]: {"spr": p["spr"]["bas"], "ispr2": p["ispr2"]["bas"], "rd": p["rd"]["bas"],
                           "eurusd": p["eurusd"]["bas"]}}
    for saat, r in noktalar.items():
        hucre(t, saat, 1, bp(r["spr"]), "gün içi")
        hucre(t, saat, 2, bp(r["ispr2"]), "gün içi")
        hucre(t, saat, 3, bp(r["rd"]), "gün içi")
        hucre(t, saat, 4, sayi(r["eurusd"], 4), "gün içi")
    dogru(abs(gi["17:30"]["spr"] - p["spr"]["son"]) < 1e-9, "gün içi pencere sonu 17:30 noktasıyla aynı değil")
    # bacaklar
    t = tablo(tl, "başlangıç")
    etiket = {"2026-02-25": "25 Şubat 2026 (yılın dibi)", "2026-06-30": "30 Haziran 2026",
              "2026-08-31": "31 Ağustos 2026", "2026-09-28": "28 Eylül 2026"}
    for r in o["bacaklar"]:
        e = etiket[r["bas"]]
        for i, k in enumerate(("fr_bp", "de_bp", "spr_bp", "it_spr_bp", "us10_bp"), 1):
            hucre(t, e, i, bp(r[k], 1, True), "bacaklar")
    # evreler: ülke farkları
    t = tablo(tl, "Bund'a fark, değişim")
    etiket = {"2026-08-31": "birinci evre: 31 Ağustos → 28 Eylül", "2026-09-28": "ikinci evre: 28 Eylül → 1 Ekim"}
    for r in o["evreler"]:
        for i, k in enumerate(("fr", "it", "be", "es", "gr", "pt", "at", "nl", "fr_eksi_it"), 1):
            hucre(t, etiket[r["bas"]], i, bp(r[k], 1, True), "evreler")
    # beta
    t = tablo(tl, "dönem", "Fransa", "İtalya", "Avusturya")
    for r in o["beta"]["donemler"]:
        e = "2026 Eylül (30 Eylül'e kadar)" if r["ad"] == "2026 Eylül" else r["ad"]
        hucre(t, e, 1, sayi(r["fr_b"], 2), "beta")
        hucre(t, e, 2, sayi(r["it_b"], 2), "beta")
        hucre(t, e, 3, sayi(r["at_b"], 2), "beta")
        hucre(t, e, 4, sayi(r["n"], 0), "beta")
    # büyük günler
    t = tablo(tl, "gün")
    for r in o["buyuk_gunler"]:
        e = f"{r['gun'][8:10]}.{r['gun'][5:7]}"
        hucre(t, e, 1, bp(r["spr"], 1, True), "büyük günler")
        for i, k in enumerate(("fr", "de", "us10", "it_spr"), 2):
            hucre(t, e, i, sayi(r[k], 1, True), "büyük günler")
    # çapraz kur ayrıştırması
    t = tablo(tl, "pencere")
    ad = {("2026-02-25", "2026-10-01"): "25 Şubat → 1 Ekim", ("2026-06-30", "2026-08-31"): "30 Haziran → 31 Ağustos",
          ("2026-08-31", "2026-09-28"): "31 Ağustos → 28 Eylül", ("2026-09-28", "2026-10-01"): "28 Eylül → 1 Ekim",
          ("2026-08-31", "2026-10-01"): "31 Ağustos → 1 Ekim"}
    for r in o["capraz"]:
        e = ad.get((r["bas"], r["son"]))
        if e is None:
            continue
        for i, k in enumerate(("fx", "dolar_gbp", "eurgbp", "dolar_chf", "eurchf"), 1):
            hucre(t, e, i, yz(r[k], 2, True), "çapraz")
        hucre(t, e, 6, bp(r["spr"], 1, True), "çapraz")
        hucre(t, e, 7, bp(r["ispr"], 1, True), "çapraz")
        dogru(abs(r["dolar_gbp"] + r["eurgbp"] - r["fx"]) < 1e-5, f"çapraz özdeşlik tutmuyor: {e}")
    # duyarlılık (EUR/USD)
    t = tablo(tl, "dönem", "hafta")
    for ad_, mm in o["duyarlilik"].items():
        f = mm["faiz+fr"]
        hucre(t, ad_, 1, sayi(f["n"], 0), "duyarlılık")
        hucre(t, ad_, 2, yz(f["b"]["spr"] * 10, 2, True), "duyarlılık")
        hucre(t, ad_, 3, sayi(f["t"]["spr"], 1, True), "duyarlılık")
        hucre(t, ad_, 4, yz(f["b"]["rd"] * 10, 2, True), "duyarlılık")
        hucre(t, ad_, 5, sayi(f["t"]["rd"], 1, True), "duyarlılık")
        hucre(t, ad_, 6, sayi(f["r2"], 3), "duyarlılık")
    # yanlışlama: aynı model dört kurda
    t = tablo(tl, "dönem", "EUR/USD", "GBP/USD")
    for ad_, mm in o["duyarlilik"].items():
        for i, k in enumerate(("faiz+fr", "gbpusd", "eurgbp", "eurchf"), 1):
            r = mm[k]
            hucre(t, ad_, i, f"{yz(r['b']['spr'] * 10, 2, True)} (t {sayi(r['t']['spr'], 1, True)})", "yanlışlama")
    # örneklem dışı
    t = tablo(tl, "tahmin dönemi")
    for k, (eg, te) in {"2004_2023": ("2004–2023", "2024–2026"), "2013_2023": ("2013–2023", "2024–2026"),
                        "2004_2019": ("2004–2019", "2020–2026")}.items():
        r = o["orneklem_disi"]["fx"][k]
        hucre(t, eg, 1, te, "örneklem dışı")
        hucre(t, eg, 2, sayi(r["test_n"], 0), "örneklem dışı")
        hucre(t, eg, 3, sayi(r["faiz"]["r2_dis"], 3), "örneklem dışı")
        hucre(t, eg, 4, sayi(r["faiz+fr"]["r2_dis"], 3), "örneklem dışı")
        hucre(t, eg, 5, sayi(r["esli_t"], 2), "örneklem dışı")
        hucre(t, eg, 6, sayi(o["orneklem_disi"]["gbpusd"][k]["esli_t"], 2), "örneklem dışı")
        hucre(t, eg, 7, sayi(o["orneklem_disi"]["eurgbp"][k]["esli_t"], 2), "örneklem dışı")
    # atıf
    t = tablo(tl, "katsayıların tahmin dönemi")
    etiket = {"2024-01-03–2026-06-24": "Ocak 2024 – Haziran 2026", "2004-01-07–2023-12-27": "2004–2023",
              "2013-01-02–2023-12-27": "2013–2023", "2010-01-06–2012-12-26": "2010–2012",
              "2004-01-07–2026-06-24": "2004 – Haziran 2026"}
    ad_ = o["atif_duyarlilik"]
    for i, r in enumerate(ad_["fx"]):
        e = etiket[r["egitim"]]
        hucre(t, e, 1, sayi(r["n"], 0), "atıf")
        hucre(t, e, 2, yz(r["spread_payi"], 2, True), "atıf")
        hucre(t, e, 3, yz(r["faiz_payi"], 2, True), "atıf")
        hucre(t, e, 4, yz(r["sabit_payi"], 2, True), "atıf")
        hucre(t, e, 5, yz(r["artik"], 2, True), "atıf")
        hucre(t, e, 6, yz(ad_["gbpusd"][i]["spread_payi"], 2, True), "atıf")
        hucre(t, e, 7, yz(ad_["eurgbp"][i]["spread_payi"], 2, True), "atıf")
        dogru(ad_["gbpusd"][i]["egitim"] == r["egitim"] == ad_["eurgbp"][i]["egitim"], "atıf satırları hizalı değil")
        dogru(abs(r["spread_payi"] + r["faiz_payi"] + r["sabit_payi"] + r["artik"] - r["kur_gercek"]) < 1e-5,
              f"atıf toplamı ölçülene eşit değil: {e}")
    # epizotlar
    t = tablo(tl, "epizot")
    for r in o["epizotlar"]:
        hucre(t, r["ad"], 1, bp(r["bas_seviye"]), "epizot")
        hucre(t, r["ad"], 2, bp(r["zirve"]), "epizot")
        hucre(t, r["ad"], 3, bp(r["acilma"], 1, True), "epizot")
        hucre(t, r["ad"], 4, sayi(r["is_gunu"], 0), "epizot")
        hucre(t, r["ad"], 5, yz(r["eurusd_yuzde"], 2, True), "epizot")
        hucre(t, r["ad"], 6, "—" if r["eurgbp_yuzde"] is None else yz(r["eurgbp_yuzde"], 2, True), "epizot")
        hucre(t, r["ad"], 7, bp(r["it_bp"], 1, True), "epizot")
        for i, k in ((8, "sonra_1a"), (9, "sonra_3a")):
            hucre(t, r["ad"], i, "—" if r[k] is None else bp(r[k], 1, True), "epizot")
    # olay tepkileri
    t = tablo(tl, "olay")
    for r in o["olay_tepkileri"]:
        hucre(t, r["ad"], 1, gun_k(r["sonra"]), "olay")
        hucre(t, r["ad"], 2, bp(r["spr"], 1, True), "olay")
        hucre(t, r["ad"], 3, bp(r["it"], 1, True), "olay")
        hucre(t, r["ad"], 4, yz(r["fx"], 2, True), "olay")
        hucre(t, r["ad"], 5, "—" if r["eurgbp"] is None else yz(r["eurgbp"], 2, True), "olay")
    # katalizör ve izleme tablolarındaki sayılar
    t = tablo(tl, "tarih", "olay")
    ev = {r["bas"]: r for r in o["evreler"]}
    hucre(t, "Ekim boyunca", 2, "Kurun dolar bacağı: eylülün birinci evresinde ABD 2 yıllığı "
          f"{bp(ev['2026-08-31']['us2y_bp'], 1, True)} yükseldi", "katalizör")
    hucre(t, "15 Ekim 2026", 2, "Komisyon'un değerlendirmesi kasımda; İtalya'nın planı bulaşma tarafı", "katalizör")
    t = tablo(tl, "ne zaman")
    c2 = _cap(o, "2026-09-28")
    hucre(t, "Her gün", 2, "Fark açılırken euro sterline ve franka karşı da düşüyorsa etki euroya özgü; yalnız dolara "
          f"karşı düşüyorsa ortak etken. 28 Eylül → 1 Ekim {yz(c2['eurgbp'], 2, True)} ve {yz(c2['eurchf'], 2, True)}.",
          "izleme")


def cumleler(m: str, o: dict) -> None:
    sv, h, k = o["seviye"], o["hiz"], o["kur"]
    fi, eg, oy = o["fransa_italya"], o["egri"], o["oynaklik"]
    D = o["duyarlilik"]
    d24 = D["2024–2026"]
    b, p = o["beta"], o["gun_ici_pencere"]
    ey, e1c, e2c, yaz_, dip = (_cap(o, "2026-08-31"), _cap(o, "2026-08-31", "2026-09-28"), _cap(o, "2026-09-28"),
                               _cap(o, "2026-06-30", "2026-08-31"), _cap(o, "2026-02-25"))
    ev1, ev2 = o["evreler"]
    # ── tez ve özet
    metinde(m, f"140,9 bp ile {AY[int(sv['son_gorulme'][5:7])]} {sv['son_gorulme'][:4]}'den beri en yüksekte; son 22 iş "
               f"gününde {bp(h['10y_22']['degisim'], 1, True)} açıldı", "tez seviye ve hız")
    dogru(sv["spread"] == 140.91, "tezdeki 140,9 bp ölçümle aynı değil")
    metinde(m, f"EUR/USD 31 Ağustos'tan bu yana {yz(ey['fx'], 2, True)} kaybetti, ama sterlin ve frank da dolara karşı "
               f"−%{sayi(abs(ey['dolar_gbp']), 1)}–{sayi(abs(ey['dolar_chf']), 1)} düştü", "tez dolar bacağı")
    for kol in ("dolar_gbp", "dolar_chf"):
        dogru(0.75 <= ey[kol] / ey["fx"] <= 0.87, f"'kaybın beşte dördü dolar geneliydi' tutmuyor: {kol} {ey[kol] / ey['fx']:.2f}")
    metinde(m, f"(sterline karşı {yz(e2c['eurgbp'], 2, True)}, franka karşı {yz(e2c['eurchf'], 2, True)})", "tez euro bacağı")
    dogru(e1c["eurgbp"] > -0.1 and e1c["eurchf"] > -0.1, "birinci evrede euroya özgü kayıp var")
    dogru(e2c["dolar_chf"] > 0, "ikinci evrede frank dolara karşı yükselmedi")
    metinde(m, f"31 Ağustos → 28 Eylül euro {yz(e1c['fx'], 2, True)}, sterlin {yz(e1c['dolar_gbp'], 2, True)} kaybetti",
            "özet evre 1")
    metinde(m, f"28 Eylül → 1 Ekim euro {yz(e2c['fx'], 2, True)}, sterlin {yz(e2c['dolar_gbp'], 2, True)} kaybetti; frank "
               "dolara karşı yükseldi", "özet evre 2")
    metinde(m, f"EUR/USD'de {yz(d24['faiz+fr']['b']['spr'] * 10, 2, True)} eşlik ediyor (2024–2026), GBP/USD'de de "
               f"{yz(d24['gbpusd']['b']['spr'] * 10, 2, True)}; EUR/GBP'de etki yok", "özet haftalık")
    dogru(abs(d24["eurgbp"]["t"]["spr"]) < 1.96, "EUR/GBP'de fark katsayısı anlamlı ('etki yok' tutmuyor)")
    metinde(m, f"Bund'a duyarlılığı 2026'nın ilk sekiz ayında {sayi(b['donemler'][4]['fr_b'], 2)}, Avusturya'nın "
               f"{sayi(b['donemler'][4]['at_b'], 2)}", "özet beta")
    metinde(m, f"ABD 10 yıllığı %{sayi(sv['us10_son'], 2)}–{sayi(sv['us10_onceki'], 2)}", "özet ABD 10y")
    dogru(sv["us10_onceki_gun"] == "2026-09-30", "ABD 10y önceki gün 30 Eylül değil")
    ep = {r["ad"]: r for r in o["epizotlar"]}
    metinde(m, f"2010 Yunanistan {yz(ep['2010 Yunanistan']['eurgbp_yuzde'], 2, True)}, 2011 "
               f"{yz(ep['2011 euro bölgesi borç krizi']['eurgbp_yuzde'], 2, True)}", "özet epizot EUR/GBP")
    metinde(m, f"2017 seçimi {yz(ep['2017 cumhurbaşkanlığı seçimi']['eurgbp_yuzde'], 2, True)}, 2024 fesih "
               f"{yz(ep['2024 meclisin feshi']['eurgbp_yuzde'], 2, True)}, 2025 Bayrou "
               f"{yz(ep['2025 Bayrou güven oylaması']['eurgbp_yuzde'], 2, True)}", "özet Fransa epizotları")
    notlar = [r["spr"] for r in o["olay_tepkileri"] if r["tur"] == "not" and r["once"] >= "2024-01-01"]
    dogru(len(notlar) == 9, f"2024 sonrası not kararı sayısı {len(notlar)}, metin 'dokuz'")
    metinde(m, f"dokuz not kararının tepki gününde fark {sayi(min(notlar), 1, True)} ile {bp(max(notlar), 1, True)} "
               "arasında değişti", "not aralığı")
    metinde(m, f"günlerin {yz(sv['yuzdelik_2000'], 1)}'inden üstünde", "yüzdelik")
    metinde(m, f"bu serideki tarihî zirve {gun(sv['tarihi_zirve_gun'])}'de {bp(sv['tarihi_zirve'])}", "tarihî zirve")
    metinde(m, f"18 Eylül'de {gun(sv['onceki_100'])}'den beri ilk kez 100 bp'nin üstünde kapandı", "100 eşiği")
    dogru(sv["ilk_100"] == "2026-09-18", f"100 bp ilk aşım günü {sv['ilk_100']}")
    metinde(m, f"İtalya'dan {bp(fi['fr_eksi_it'])} pahalı borçlanıyor", "özet Fransa–İtalya")
    metinde(m, f"2 yıllık fark bir günde {bp(eg['2']['degisim_1g'], 1, True)} açıldı; bunun "
               f"{bp(abs(eg['de2y_1g_bp']))}'si Alman 2 yıllığının düşüşü", "özet 2y")
    kf = o["kaynak"]["fr"]
    metinde(m, f"resmî aylık seriyle {kf['ay']} ayda {sayi(kf['korelasyon'], 3)} korelasyon", "özet kaynak")
    metinde(m, f"Haftalık kur bağı anlamlı (t {sayi(d24['faiz+fr']['t']['spr'], 1)})", "özet t")
    # ── giriş ve Bölüm 1
    metinde(m, f"üçte iki büyüdü ({sayi(sv['seviye_agustos'])} → {bp(sv['spread'])})", "giriş üçte iki")
    dogru(1.6 <= sv["spread"] / sv["seviye_agustos"] <= 1.72, "'üçte iki büyüdü' tutmuyor")
    dogru(sv["spread"] / sv["yil_dibi"] > 2.5, "'iki buçuk katından fazlası' tutmuyor")
    metinde(m, f"Fransa 10 yıllığı %{sayi(sv['fr10'], 3)}, Almanya 10 yıllığı %{sayi(sv['de10'], 3)} kapandı; fark "
               f"({sayi(sv['fr10'], 3)} − {sayi(sv['de10'], 3)}) × 100 = {bp(sv['spread'])}", "tanım hesabı")
    metinde(m, f"{kf['ay']} ayda {sayi(kf['korelasyon'], 3)} korelasyon veriyor; daha zorlu sınama olan aylık "
               f"değişimlerin korelasyonu {sayi(kf['degisim_korelasyonu'], 2)}. Ortalama fark {bp(kf['ort_fark'])} ve "
               f"yıldan yıla {sayi(kf['yillik_fark_min'], 1, True)} ile {bp(kf['yillik_fark_maks'], 1, True)} arasında",
            "kaynak sınaması")
    metinde(m, f"resmî seri {sayi(kf['son_ay_resmi'])}, günlük seriden kurulan ortalama {bp(kf['son_ay_cnbc'])}",
            "kaynak son ay")
    bs = o["bar_saati"]
    avr = max(bs[c]["maks_bp"] for c in ("fr10y", "de10y", "it10y", "fr2y", "de2y"))
    dogru(avr < 0.35, f"Avrupa bacaklarında günlük bar ile 17:30 farkı 0,3 bp'yi aşıyor: {avr}")
    metinde(m, f"medyan {sayi(min(bs['us2y']['medyan_bp'], bs['us10y']['medyan_bp']), 1)}–"
               f"{sayi(max(bs['us2y']['medyan_bp'], bs['us10y']['medyan_bp']), 1)} bp, en çok "
               f"{bp(max(bs['us2y']['maks_bp'], bs['us10y']['maks_bp']))} fark", "ABD bar saati")
    dogru(len(o["gun_ici_bes_gun"]["gunler"]) == 8 and bs["fr10y"]["gun"] == 8, "gün içi gün sayısı sekiz değil")
    gk = o["gun_ici"]["gunluk_kapanis"]
    metinde(m, f"17:30'daki {bp(o['gun_ici']['17:30']['spr'])}, o dakikaya kadarki son kotasyondur "
               f"({o['gun_ici']['zirve']['saat']}); günlük kapanış barı {bp(gk['spr'])}", "17:30 iki sayı")
    metinde(m, f"önceki kapanışa ({bp(o['buyuk_gunler'][-2]['spr_seviye'])}) yakın", "önceki kapanış")
    s15 = o["seriler"]["gun_ici"]
    v1545 = s15["spr"][s15["t"].index("15:45")]
    metinde(m, f"fark 15:45'te {bp(v1545)}'ye çıkmıştı", "15:45")
    metinde(m, f"1 Ekim'in referans kuru ({sayi(k['ecb_son'], 4)})", "ECB kuru")
    metinde(m, f"1 Ekim'in New York kapanışı {sayi(k['son'], 4)}; bu, {gun(k['son_gorulme'])}'ten beri en düşük kapanış "
               f"ve yılın zirvesinden ({tarih_ga(k['yil_zirve_gun'])}, {sayi(k['yil_zirve'], 4)}) {yz(k['zirveden'], 2, True)}",
            "NY kapanışı")
    tz = o["temizlik"]
    metinde(m, f"({tz['tasinmis_atilan']} gün). Seri 3 Ocak 2000'de başlıyor; temizlikten sonra "
               f"{sayi(tz['temiz_gun'], 0)} iş günü kalıyor, iki bacağın birlikte ölçüldüğü gün "
               f"{sayi(len(o['seriler']['spread']['t']), 0)}", "seri uzunluğu")
    bo = o["bosluk"]
    metinde(m, f"Kaynakta 2014'te iki uzun boşluk var ({bo['eksik_is_gunu_2014']} iş günü", "2014 boşluğu")
    # ── Bölüm 2
    metinde(m, f"yıla {bp(sv['seviye_yb'])} ile başladı, 25 Şubat'ta {bp(sv['yil_dibi'])} ile yılın dibini gördü",
            "yıl başı ve dip")
    dogru(sv["epizot_bas_tutarli"], "yılın dibi EPIZOT_BAS ile aynı gün değil")
    metinde(m, f"Yılın dibinden bu yana {bp(sv['epizot_degisim'], 1, True)} açıldı", "epizot")
    metinde(m, f"Haziran sonunda {sayi(sv['seviye_haziran'])}, ağustos sonunda {bp(sv['seviye_agustos'])} idi; 31 "
               f"Ağustos'tan bu yana {bp(sv['degisim_agustos'], 1, True)} açıldı", "haziran-ağustos")
    g18 = [r for r in o["buyuk_gunler"] if r["gun"] == "2026-09-18"][0]
    metinde(m, f"18 Eylül'de {bp(g18['spr_seviye'])} ile", "18 Eylül seviyesi")
    dogru(sv["tarih_1h"] == "2026-09-24" and sv["tarih_1a"] == "2026-09-01", "5/22 iş günü pencereleri kaymış")
    dogru(abs(sv["degisim_1a"] - h["10y_22"]["degisim"]) < 1e-9, "22 iş günü iki yerde iki ayrı ölçü")
    metinde(m, f"Son 5 iş gününde {sayi(sv['degisim_1h'], 1, True)}, son 22 iş gününde {bp(sv['degisim_1a'], 1, True)}",
            "5-22 gün")
    metinde(m, f"Fransa {sayi(ev1['fr10y_bp'], 1, True)} bp, Almanya {sayi(ev1['de10y_bp'], 1, True)} bp, ABD 10 yıllığı "
               f"{sayi(ev1['us10y_bp'], 1, True)} bp, ABD 2 yıllığı {bp(ev1['us2y_bp'], 1, True)} yükseldi. Fark "
               f"{bp(ev1['fr'], 1, True)} açıldı ve bunun {sayi(ev1['fr_eksi_it'], 1)} bp'si", "evre 1")
    metinde(m, f"Almanya 10 yıllığı {bp(ev2['de10y_bp'], 1, True)}, 2 yıllığı {bp(ev2['de2y_bp'], 1, True)} düştü; İtalya "
               f"{sayi(ev2['it'], 1, True)}, Belçika {sayi(ev2['be'], 1, True)}, İspanya {sayi(ev2['es'], 1, True)}, "
               f"Avusturya {bp(ev2['at'], 1, True)} açıldı. Fransa–İtalya farkı yalnız {bp(ev2['fr_eksi_it'], 1, True)}",
            "evre 2")
    dogru(ev2["de2y_bp"] < 2 * ev2["de10y_bp"] * 0.95, "Alman 2 yıllığı 10 yıllığından iki kat hızlı düşmedi")
    dogru(ev1["fr_eksi_it"] > ev2["fr_eksi_it"], "Fransa'ya özgü ayrışma birinci evrede büyük değil")
    bd = {r["ad"]: r for r in b["donemler"]}
    dogru(abs(bd["2010–2012"]["fr_b"] - bd["2010–2012"]["at_b"]) < 0.05 and bd["2010–2012"]["it_b"] < 0,
          "2010–2012: Fransa Avusturya ile aynı / İtalya eksi tutmuyor")
    j26 = bd["2026 Ocak–Ağustos"]
    dogru(abs(j26["fr_b"] - j26["it_b"]) < abs(j26["fr_b"] - j26["at_b"]) or j26["fr_b"] > j26["at_b"] + 0.2,
          "2026: Fransa'nın betası Avusturya'dan ayrılıp İtalya'ya yaklaşmadı")
    e1 = b["evre1"]
    metinde(m, f"Bund'un {bp(e1['de'], 1, True)} yükselişi, Ocak–Ağustos betasıyla ({sayi(e1['beta_once'], 2)}) farkı "
               f"{bp(e1['pay_once'], 1, True)}, evrenin kendi betasıyla ({sayi(e1['beta_ic'], 2)}) {bp(e1['pay_ic'], 1, True)} "
               f"açar; yani birinci evrenin {bp(e1['spr'], 1, True)}'lik", "beta payı")
    dogru(0.18 <= e1["pay_once"] / e1["spr"] <= 0.3 and 0.45 <= e1["pay_ic"] / e1["spr"] <= 0.56,
          "'dörtte biri ile yarısı' tutmuyor")
    metinde(m, f"İkinci evrede Bund {bp(b['evre2']['de'], 1, True)} düşerken Fransa {bp(b['evre2']['fr'], 1, True)} yükseldi",
            "evre 2 imza")
    ak = {r["ad"]: r for r in o["akranlar"]}
    metinde(m, "Fransa " + bp(ak["Fransa"]["degisim_haziran"], 1, True) + ", İtalya "
            + sayi(ak["İtalya"]["degisim_haziran"], 1, True) + ", Belçika " + sayi(ak["Belçika"]["degisim_haziran"], 1, True)
            + ", Yunanistan " + sayi(ak["Yunanistan"]["degisim_haziran"], 1, True) + ", İspanya "
            + sayi(ak["İspanya"]["degisim_haziran"], 1, True) + ", Portekiz " + sayi(ak["Portekiz"]["degisim_haziran"], 1, True)
            + ", Avusturya " + sayi(ak["Avusturya"]["degisim_haziran"], 1, True) + ", Hollanda "
            + bp(ak["Hollanda"]["degisim_haziran"], 1, True), "akran değişimleri")
    metinde(m, f"{bp(ak['Fransa']['spread'])}'ye karşı İtalya {sayi(ak['İtalya']['spread'])}, Yunanistan "
               f"{sayi(ak['Yunanistan']['spread'])} (30 Eylül), Belçika {sayi(ak['Belçika']['spread'])}, İspanya "
               f"{bp(ak['İspanya']['spread'])}", "akran seviyeleri")
    dogru(o["akranlar"][0]["ad"] == "Fransa", "Fransa ölçülen ülkeler içinde en geniş fark değil")
    dogru(len(o["akranlar"]) == 8, "ölçülen ülke sayısı sekiz değil")
    for u in ("Yunanistan", "Portekiz"):
        dogru(ak[u]["gun"] == "2026-09-30", f"{u} son kotasyonu 30 Eylül değil: {ak[u]['gun']}")
    metinde(m, f"İtalya'nınkinin {bp(fi['fr_eksi_it'])} üstünde; bu sıralama 2000'den bu yana ilk kez "
               f"{gun(fi['ilk_pozitif'])}'te oluştu ve {gun(fi['kesintisiz_bas'])}'dan beri her gözlemde sürüyor "
               f"({fi['gun_sayisi']} gözlem; {fi['is_gunu']} iş gününün ikisinde", "Fransa–İtalya")
    dogru(len(fi["eksik_gunler"]) == 2, "Fransa–İtalya penceresinde eksik gün sayısı iki değil")
    metinde(m, f"30 Eylül'deki {bp(fi['tarihce_zirve'], 1, True)}", "Fransa–İtalya zirvesi")
    dogru(fi["tarihce_zirve_gun"] == "2026-09-30", "Fransa–İtalya zirve günü 30 Eylül değil")
    # eğri
    v = ["2", "5", "10", "30"]
    dogru(max(v, key=lambda x: eg[x]["degisim_haziran"]) == "10", "haziran sonundan bu yana en çok açılan 10 yıllık değil")
    metinde(m, f"(+{sayi(eg['10']['degisim_haziran'])} bp; 5 yıllık {sayi(eg['5']['degisim_haziran'], 1, True)}, 30 yıllık "
               f"{sayi(eg['30']['degisim_haziran'], 1, True)}, 2 yıllık {sayi(eg['2']['degisim_haziran'], 1, True)})",
            "haziran eğri")
    metinde(m, f"2 yıllık fark bir günde {bp(eg['2']['degisim_1g'], 1, True)} ile {bp(eg['2']['spread'])}'ye çıktı — "
               f"{bp(eg['2']['spread'])} en son {gun(eg['2']['son_gorulme'])}'de görülmüştü; 30 Haziran'da "
               f"{bp(eg['2']['spread'] - eg['2']['degisim_haziran'])} idi", "eğri 2y")
    metinde(m, f"(2 yıllık {sayi(eg['fr2y_1g_bp'], 1, True)}, 5 yıllık {sayi(eg['fr5y_1g_bp'], 1, True)}, 10 yıllık "
               f"{sayi(eg['fr10y_1g_bp'], 1, True)}, 30 yıllık {bp(eg['fr30y_1g_bp'], 1, True)})", "Fransa getirileri")
    metinde(m, f"2 yıllık {sayi(eg['de2y_1g_bp'], 1)}, 5 yıllık {sayi(eg['de5y_1g_bp'], 1)}, 10 yıllık "
               f"{sayi(eg['de10y_1g_bp'], 1)}, 30 yıllık {bp(eg['de30y_1g_bp'], 1)}", "Almanya getirileri")
    metinde(m, f"sıçramasının {yz(eg['2']['de_payi'] * 100, 0)}'i Alman bacağıdır", "2y Alman payı")
    metinde(m, f"İtalya'nın 2 yıllık farkı da {bp(eg['it2']['degisim_1g'], 1, True)} açıldı; İtalya'nın kendi 2 yıllığı "
               f"{bp(eg['it2y_1g_bp'], 1, True)} yükseldi, yani o sıçramanın da {yz(eg['it2']['de_payi'] * 100, 0)}'u",
            "İtalya 2y")
    sp = [eg[x]["spread"] for x in v]
    dogru(sp == sorted(sp), "fark eğrisi yukarı eğimli değil")
    metinde(m, " / ".join(sayi(x) for x in sp) + " bp ile yukarı eğimli", "eğri seviyeleri")
    # ── Bölüm 3
    metinde(m, "1 Ekim ihalesinde 2036 vadeli gösterge kâğıt ortalama %4,93 getiriyle satıldı", "ihale")
    # büyük günler: ilk dört satırda Bund yükseliyor ya da Fransa'yla birlikte düşüyor, son üçünde Bund düşüyor
    bg = o["buyuk_gunler"]
    dogru(all((r["de"] > 0) or (r["fr"] < 0) for r in bg[:4]) and all(r["de"] < 0 for r in bg[4:]),
          "büyük günler: ilk dört / son üç satır okuması tutmuyor")
    # ── Bölüm 4
    for r in (dip, yaz_, e1c, e2c, ey):
        dogru(abs(r["dolar_gbp"] + r["eurgbp"] - r["fx"]) < 1e-5, "çapraz özdeşlik")
    metinde(m, f"euro dolara karşı {yz(ey['fx'], 2, True)} kaybetti; sterlin {yz(ey['dolar_gbp'], 2, True)}, frank "
               f"{yz(ey['dolar_chf'], 2, True)} kaybetti. Euroya özgü kısım sterline göre {yz(ey['eurgbp'], 2, True)}, "
               f"franka göre {yz(ey['eurchf'], 2, True)}", "eylül ayrıştırması")
    dogru(0.13 <= ey["euro_payi_gbp"] <= 0.25 and 0.13 <= ey["euro_payi_chf"] <= 0.25, "'beşte biri kadar' tutmuyor")
    metinde(m, f"31 Ağustos → 28 Eylül euro {yz(e1c['fx'], 2, True)}, sterlin {yz(e1c['dolar_gbp'], 2, True)} kaybetti; "
               f"euro sterline karşı {yz(e1c['eurgbp'], 2, True)}, franka karşı {yz(e1c['eurchf'], 2, True)} değer kazandı. "
               f"Bu evrede ABD 2 yıllığı {bp(e1c['us2'], 1, True)} yükseldi ve Fransa farkı {bp(e1c['spr'], 1, True)}",
            "evre 1 çapraz")
    metinde(m, f"28 Eylül → 1 Ekim euro {yz(e2c['fx'], 2, True)} kaybederken sterlin yalnız {yz(e2c['dolar_gbp'], 2, True)} "
               f"kaybetti, frank dolara karşı {yz(e2c['dolar_chf'], 2, True)} kazandı. Euro sterline karşı "
               f"{yz(e2c['eurgbp'], 2, True)}, franka karşı {yz(e2c['eurchf'], 2, True)} düştü", "evre 2 çapraz")
    metinde(m, f"Alman 2 yıllığının {bp(e2c['de2'], 1, True)} düştüğü evredir", "evre 2 Schatz")
    metinde(m, f"Yılın dibinden bu yana euro sterline karşı {yz(dip['eurgbp'], 2, True)} kaybetti ama franka karşı "
               f"{yz(dip['eurchf'], 2, True)} kazandı", "uzun pencere")
    dogru(dip["eurgbp"] * dip["eurchf"] < 0 and yaz_["eurgbp"] * yaz_["eurchf"] < 0, "uzun pencerede kıyaslar ayrışmıyor")
    metinde(m, f"ertesi gün İtalya'nın 10 yıllık farkı {bp(eg['it10']['degisim_1g'], 1, True)}, 2 yıllık farkı "
               f"{bp(eg['it2']['degisim_1g'], 1, True)} açıldı", "BBH sonrası")
    f04 = D["2004–2026"]["faiz+fr"]
    metinde(m, f"10 bp'lik açılmaya {yz(f04['b']['spr'] * 10, 2, True)} eşlik ediyor. Rejime bağlı", "tüm örneklem")
    dogru(all(abs(mm["faiz+fr"]["t"]["rd"]) >= abs(mm["faiz+fr"]["t"]["spr"]) for mm in D.values()),
          "'faiz farkı her dönemde en az fark kadar güçlü' tutmuyor")
    metinde(m, f"2024–2026'da 10 bp'lik açılmaya GBP/USD'de {yz(d24['gbpusd']['b']['spr'] * 10, 2, True)} eşlik ediyor",
            "GBP/USD")
    dogru(abs(d24["gbpusd"]["b"]["spr"]) > abs(d24["faiz+fr"]["b"]["spr"]), "GBP/USD katsayısı EUR/USD'dekinden büyük değil")
    ikisi = [ad for ad, mm in D.items() if mm["eurgbp"]["b"]["spr"] < 0 and mm["eurchf"]["b"]["spr"] < 0]
    dogru(ikisi == ["2010–2012"], f"iki kurda da eksi işaret yalnız 2010–2012'de değil: {ikisi}")
    eg10 = D["2010–2012"]["eurgbp_it"]
    metinde(m, f"EUR/GBP'de Fransa'nın katsayısı kayboluyor ({yz(eg10['b']['spr'] * 10, 2, True)}, t "
               f"{sayi(eg10['t']['spr'], 1)}) ve İtalya'nınki kalıyor: İtalya farkındaki 10 bp'lik açılmaya EUR/GBP'de "
               f"{yz(eg10['b']['ispr'] * 10, 2, True)} eşlik ediyor (t {sayi(eg10['t']['ispr'], 1)})", "2010–12 İtalya")
    eg24 = d24["eurgbp_it"]
    metinde(m, f"2024–2026'da aynı katsayı {yz(eg24['b']['ispr'] * 10, 2, True)} (t {sayi(eg24['t']['ispr'], 1, True)})",
            "2024–26 İtalya")
    ec = d24["ecb"]
    metinde(m, f"faiz farkının katsayısı {yz(ec['b']['rd'] * 10, 2, True)}'e (t {sayi(ec['t']['rd'], 1)}) iniyor ve fark kuru "
               f"faiz farkından daha iyi açıklıyor gibi görünüyor ({yz(ec['b']['spr'] * 10, 2, True)}, t "
               f"{sayi(ec['t']['spr'], 1)})", "ECB kuru sağlamlık")
    od = o["orneklem_disi"]
    dogru(all(od["fx"][k]["faiz+fr"]["r2_dis"] > od["fx"][k]["faiz"]["r2_dis"] for k in od["fx"]),
          "EUR/USD örneklem dışı payı üç sınamada da artmıyor")
    dogru(sum(od["fx"][k]["esli_t"] > 1.96 for k in od["fx"]) == 2, "'ikisinde anlamlı' tutmuyor")
    dogru(sum(od["gbpusd"][k]["esli_t"] > od["fx"][k]["esli_t"] for k in od["fx"]) == 2,
          "'GBP/USD'de iki sınamada daha güçlü' tutmuyor")
    dogru(all(od["eurgbp"][k]["esli_t"] < 1.96 for k in od["fx"]), "EUR/GBP'de örneklem dışı iyileşme var")
    kk = o["kayan"]
    metinde(m, f"EUR/USD'nin duyarlılığı {yz(kk['son'], 2, True)} (bant {yz(kk['son_alt'], 2, True)} ile "
               f"{yz(kk['son_ust'], 2, True)}), EUR/GBP'ninki {yz(kk['eurgbp_son'], 2, True)} (bant "
               f"{yz(kk['eurgbp_son_alt'], 2, True)} ile {yz(kk['eurgbp_son_ust'], 2, True)})", "kayan")
    dogru(kk["son_tarih"] == "2026-09-30", "kayan pencerenin son haftası 30 Eylül değil")
    pk = kk["pozitif_kosular"]
    dogru(len(pk) == 2, f"pozitif koşu sayısı {len(pk)}")
    metinde(m, f"{AY[int(pk[0][0][5:7])]} {pk[0][0][:4]} ile {AY[int(pk[0][1][5:7])]} {pk[0][1][:4]} arasında ve "
               f"{AY[int(pk[1][0][5:7])]} {pk[1][0][:4]} ile {AY[int(pk[1][1][5:7])]} {pk[1][1][:4]} arasında", "pozitif koşular")
    at = {y: o["atif"]["eylul"][y] for y in ("fx", "gbpusd", "eurgbp")}
    metinde(m, f"EUR/USD'nin {yz(at['fx']['kur_gercek'], 2, True)}'lık kaybı şöyle ayrışıyor: fark kanalı "
               f"{yz(at['fx']['spread_payi'], 2, True)}, faiz kanalı {yz(at['fx']['faiz_payi'], 2, True)}, sabit "
               f"{yz(at['fx']['sabit_payi'], 2, True)}, kalan {yz(at['fx']['artik'], 2, True)}", "atıf EUR/USD")
    metinde(m, f"\"Fransa kanalı\" GBP/USD'ye {yz(at['gbpusd']['spread_payi'], 2, True)} yazıyor; GBP/USD'nin kendisi "
               f"{yz(at['gbpusd']['kur_gercek'], 2, True)} düştü", "atıf GBP/USD")
    dogru(abs(at["gbpusd"]["spread_payi"]) > abs(at["gbpusd"]["kur_gercek"]), "sterlinin bütün kaybından fazlası değil")
    metinde(m, f"fark kanalına {yz(at['eurgbp']['spread_payi'], 2, True)} yazıyor, gerçekleşen "
               f"{yz(at['eurgbp']['kur_gercek'], 2, True)}", "atıf EUR/GBP")
    eksi = [r["egitim"] for r in o["atif_duyarlilik"]["eurgbp"] if r["spread_payi"] < 0]
    dogru(eksi == ["2010-01-06–2012-12-26"], f"EUR/GBP fark kanalı eksi olan tek dönem 2010–2012 değil: {eksi}")
    dogru(at["fx"]["katsayi"]["son"] < at["fx"]["bas"] and at["fx"]["bas"] == "2026-08-31", "atıf penceresi örneklem içi")
    metinde(m, f"(Ocak 2024 – Haziran 2026, {at['fx']['katsayi']['n']} hafta)", "atıf tahmin penceresi")
    metinde(m, f"ölçülen: EUR/USD {yz(at['fx']['kur_gercek'], 2, True)}, GBP/USD {yz(at['gbpusd']['kur_gercek'], 2, True)}, "
               f"EUR/GBP {yz(at['eurgbp']['kur_gercek'], 2, True)}", "atıf ölçülen")
    # gün içi
    metinde(m, f"Fransa farkı {sayi(p['spr']['bas'])}'dan {bp(p['spr']['son'])}'ye ({sayi(p['spr']['degisim'], 1, True)}), "
               f"İtalya'nın 2 yıllık farkı {sayi(p['ispr2']['bas'])}'dan {bp(p['ispr2']['son'])}'ye "
               f"({sayi(p['ispr2']['degisim'], 1, True)}) çıktı. ABD 2 yıllığı {bp(p['us2y']['degisim_bp'])}, Almanya 2 "
               f"yıllığı {bp(p['de2y']['degisim_bp'])} düştü; ABD–Almanya 2 yıllık farkı {bp(p['rd']['degisim'], 1, True)}",
            "gün içi pencere")
    metinde(m, f"Euro aynı iki saatte {sayi(p['eurusd']['bas'], 4)}'ten {sayi(p['eurusd']['son'], 4)}'e, "
               f"{yz(p['eurusd']['degisim_yuzde'], 2, True)}", "gün içi kur")
    ism, q = o["gun_ici_ism"], o["gun_ici_pencere_1600"]
    metinde(m, f"ABD 2 yıllığı {bp(ism['us2y']['degisim_bp'], 1, True)} yükseldi, faiz farkı {bp(ism['rd']['degisim'], 1, True)}",
            "ISM")
    dogru(ism["rd"]["degisim"] / p["rd"]["degisim"] > 0.85, "'neredeyse tamamı tek çeyrek saatte' tutmuyor")
    metinde(m, f"faiz farkı yalnız {bp(q['rd']['degisim'], 1, True)} oynadı — ABD 2 yıllığı {sayi(q['us2y']['degisim_bp'], 1)}, "
               f"Almanya 2 yıllığı {bp(q['de2y']['degisim_bp'], 1)} düştü — ama Fransa farkı {bp(q['spr']['degisim'], 1, True)} "
               f"açıldı ve euro {yz(q['eurusd']['degisim_yuzde'], 2, True)} geriledi. Bu son açılmanın çoğu Bund'un "
               f"{sayi(q['de10y']['degisim_bp'], 1)} bp'lik düşüşü; Fransa 10 yıllığı yalnız {bp(q['fr10y']['degisim_bp'], 1, True)}",
            "16:00 sonrası")
    c29 = _cap(o, "2026-09-29")
    metinde(m, f"29 Eylül → 1 Ekim euronun sterline karşı {yz(c29['eurgbp'], 2, True)}, franka karşı "
               f"{yz(c29['eurchf'], 2, True)} düştüğünü", "29 Eylül çapraz")
    g5 = o["gun_ici_bes_gun"]
    kt, k1 = g5["kontrollu"], g5["kontrollu_1ekim_haric"]
    metinde(m, f"EUR/USD'de {yz(kt['b']['spr'], 3, True)} eşlik ediyor (t {sayi(kt['t']['spr'], 1)}; {kt['n']} gözlem); "
               f"1 Ekim çıkarılınca {yz(k1['b']['spr'], 3, True)} (t {sayi(k1['t']['spr'], 1)})", "gün içi regresyon")
    pz = {r["kod"]: r for r in o["piyasalar"]}
    dogru(all(r["bas_gun"] == "2026-08-31" for r in o["piyasalar"]), "öbür piyasaların başlangıcı 31 Ağustos değil")
    metinde(m, f"CAC 40 {yz(pz['cac']['degisim'], 2, True)}, DAX {yz(pz['dax']['degisim'], 2, True)}, Euro Stoxx 50 "
               f"{yz(pz['sx5e']['degisim'], 2, True)}; Fransız bankaları BNP Paribas {yz(pz['bnp']['degisim'], 2, True)}, "
               f"Société Générale {yz(pz['socgen']['degisim'], 2, True)}, Crédit Agricole {yz(pz['cagri']['degisim'], 2, True)}",
            "hisseler")
    metinde(m, f"yene karşı {yz(pz['eurjpy']['degisim'], 2, True)}, sterline karşı {yz(pz['eurgbp']['degisim'], 2, True)}, "
               f"franka karşı {yz(pz['eurchf']['degisim'], 2, True)} kaybetti; dolar endeksi {yz(pz['dxy']['degisim'], 2, True)}",
            "çaprazlar")
    dogru(abs(pz["eurgbp"]["degisim"] - ey["eurgbp"]) < 1e-9, "öbür piyasalar EUR/GBP'si ayrıştırmayla aynı değil")
    # ── Bölüm 5
    ay = o["ayrisma"]
    olay_bas = [r["acilma"] for r in o["epizotlar"] if r["ad"] not in ("2011 euro bölgesi borç krizi", "2026")]
    metinde(m, f"olay günüyle başlayan en büyük öbür açılma {bp(max(olay_bas))} (2020)", "olay günlü en büyük")
    dogru(max(olay_bas) == ep["2020 salgın"]["acilma"], "olay günüyle başlayan en büyük açılma 2020 değil")
    metinde(m, f"aynı pencerede İtalya'nın farkı {bp(ep['2011 euro bölgesi borç krizi']['it_bp'], 1, True)} açıldı, bu yıl "
               f"{bp(ep['2026']['it_bp'], 1, True)}", "2011 İtalya")
    metinde(m, f"Euro sterline karşı 2010'da {yz(ep['2010 Yunanistan']['eurgbp_yuzde'], 2, True)}, 2011'de "
               f"{yz(ep['2011 euro bölgesi borç krizi']['eurgbp_yuzde'], 2, True)} kaybetti", "kriz EUR/GBP")
    metinde(m, f"2017 {yz(ep['2017 cumhurbaşkanlığı seçimi']['eurgbp_yuzde'], 2, True)}, 2024 fesih "
               f"{yz(ep['2024 meclisin feshi']['eurgbp_yuzde'], 2, True)}, Barnier "
               f"{yz(ep['2024 Barnier hükümetinin düşüşü']['eurgbp_yuzde'], 2, True)}, Bayrou "
               f"{yz(ep['2025 Bayrou güven oylaması']['eurgbp_yuzde'], 2, True)}", "Fransa epizotları EUR/GBP")
    metinde(m, f"(+%{sayi(ep['2008 küresel finans krizi']['eurgbp_yuzde'], 2)}, +%{sayi(ep['2020 salgın']['eurgbp_yuzde'], 2)})",
            "2008-2020 EUR/GBP")
    metinde(m, f"euro dolara karşı +%{sayi(ay['y2025']['fx'], 2)} kazanırken fark yalnız "
               f"{bp(ay['y2025']['spr_bas'] - ay['y2025']['spr_son'])} daraldı", "2025 ayrışması")
    e24 = ep["2024 meclisin feshi"]
    metinde(m, f"fark {e24['is_gunu']} iş gününde {bp(e24['acilma'], 1, True)} açıldı, bir ayda kısmen geri döndü ve fesih "
               f"öncesindeki {bp(ay['fesih_once'])}'ye bir daha hiç inmedi; ondan sonraki en düşük kapanış bu yılın dibi, "
               f"{bp(ay['fesih_sonrasi_dip'])}", "fesih primi")
    dogru(ay["fesih_sonrasi_dip_gun"] == sv["yil_dibi_gun"], "fesih sonrası dip bu yılın dibi değil")
    oy_ = {r["ad"]: r for r in o["olay_tepkileri"]}
    metinde(m, f"fark bir ayda {bp(ep['2011 euro bölgesi borç krizi']['sonra_1a'], 1, True)} geriledi", "2011 ilk dönüş")
    metinde(m, f"8 Aralık'ta ise {bp(oy_['ECB: üç yıllık LTRO']['spr'], 1, True)} açıldı", "LTRO")
    dr, l17 = oy_['Draghi: "ne gerekiyorsa"'], oy_["2017 ilk tur: Macron–Le Pen"]
    metinde(m, f"farkı bir günde {sayi(dr['spr'], 1)}, İtalya'yı {bp(dr['it'], 1)} daralttı ve euroyu {yz(dr['fx'], 2, True)} "
               f"yükseltti; OMT'nin ayrıntıları {bp(oy_['ECB: OMT' + chr(39) + 'nin ayrıntıları']['spr'], 1)}", "Draghi")
    buyuk = max(o["olay_tepkileri"], key=lambda r: abs(r["spr"]))
    dogru(buyuk["ad"] == "2026: 2027 bütçe tasarısı", f"tablodaki en büyük tek günlük hareket {buyuk['ad']}")
    metinde(m, f"fark {bp(l17['spr'], 1, True)} daraldı, euro dolara karşı {yz(l17['fx'], 2, True)}, sterline karşı "
               f"{yz(l17['eurgbp'], 2, True)} kazandı", "2017")
    bar, bay, lec = (oy_["2024: Barnier gensoruyla düştü"], oy_["2025: Bayrou hükümeti düştü"],
                     oy_["2025: Lecornu istifa etti"])
    metinde(m, f"fark {bp(bar['spr'], 1, True)} daraldı; Bayrou hükümetinin düşüşü {sayi(bay['spr'], 1, True)}, Lecornu'nun "
               f"istifası {bp(lec['spr'], 1, True)} açtı", "hükümet düşüşleri")
    dogru(bay["eurgbp"] < 0 and lec["eurgbp"] < 0, "Bayrou ve Lecornu günlerinde euro sterline karşı düşmedi")
    dogru(oy_["ECB: üç yıllık LTRO"]["eurgbp"] is None and oy_["2026: 2027 bütçe tasarısı"]["eurgbp"] is None,
          "EUR/GBP'nin ölçülemediği iki satır değişti")
    # ── Bölüm 7
    il, il66, ilb = o["ileri"][0], o["ileri"][1], o["ileri"][4]
    metinde(m, f"standart sapması {bp(oy['sigma_gunluk'], 2)}; 2013'ten bu yana standart sapma "
               f"{bp(oy['sigma_2013_temiz'], 2)} (gösterge kâğıt değişimi ve veri boşluğu günleri dışarıda) — "
               f"{sayi(oy['oran_temiz'], 1)} katı", "oynaklık")
    metinde(m, f"±1,96σ bandı ±{bp(oy['bant_1a'])}", "bant")
    alt, ust = oy["spread"] - oy["bant_1a"], oy["spread"] + oy["bant_1a"]
    metinde(m, f"%95 olasılıkla {sayi(alt, 0)} ile {sayi(ust, 0)} bp arasında", "bant uçları")
    metinde(m, f"önceki açılması 30 bp'yi aşan {il['gozlem']} gözlem", "51 gözlem")
    metinde(m, f"ertesi ay medyanda {bp(il['medyan'], 1, True)} geriledi; gözlemlerin {yz(il['daha_acildi_payi'], 1)}'inde "
               f"daha da açıldı, onda birinde {bp(il['p10'], 1, True)}'den fazla daraldı", "ileri dağılım")
    dogru(il["epizot"] == 7 and il["medyani_artida_kume"] == 0, "yedi kümenin her birinin medyanı gerilemedi")
    acilan = round(il["daha_acildi_payi"] * il["gozlem"] / 100)
    dogru(acilan == 7 and il["kriz_disi_daha_acilan"] == 0 and il["kriz_disi_gozlem"] == 11,
          "'daha da açılan yedi gözlemin yedisi 2011–12'den / 11 gözlem' tutmuyor")
    km = il["kumeler"]
    k11 = [c for c in km if c["bas"].startswith("2011-10")][0]
    k12 = [c for c in km if c["bas"].startswith("2012-04")][0]
    metinde(m, f"({k11['n']} gözlemin {k11['daha_acilan']}'sı, o kümenin ilk günlerinde) ve Nisan–Mayıs 2012 "
               f"({k12['n']} gözlemin {k12['daha_acilan']}'i)", "açılan kümeler")
    metinde(m, f"{bp(h['10y_22']['degisim'], 1, True)}'yi aşan açılma yalnız Kasım 2011 ile Ocak 2012 arasında görüldü ve o "
               f"sekiz gözlemin hepsinde fark ertesi ay {sayi(-max(c['ileri_maks'] for c in ilb['kumeler']), 1)} ile "
               f"{sayi(-min(c['ileri_min'] for c in ilb['kumeler']), 1)} bp arasında daraldı", "bugünkü hız")
    dogru(ilb["gozlem"] == 8 and ilb["daha_acildi_payi"] == 0 and all(c["bas"][:4] in ("2011", "2012") for c in ilb["kumeler"]),
          "bugünkü hız eşiği: sekiz gözlem / hiçbiri açılmadı / 2011–12 tutmuyor")
    metinde(m, f"medyan {bp(il66['medyan'], 1, True)}, ama gözlemlerin {yz(il66['daha_acildi_payi'], 1)}'sı daha açık ve "
               f"yedi kümenin üçünde", "66 gün")
    dogru(il66["daha_acilan_kume"] == 3, "66 günde daha açılan küme sayısı üç değil")
    a11 = [c for c in il66["kumeler"] if c["bas"].startswith("2011-08")][0]
    metinde(m, f"{a11['n']} gözlemin dördünde {bp(a11['ileri_min'], 1, True)}'ye" if False else
            f"dört gözlemin dördünde {sayi(a11['ileri_min'], 1, True)} ile {bp(a11['ileri_maks'], 1, True)} daha açıktı "
            f"(medyan {bp(a11['ileri_medyan'], 1, True)})", "Ağustos 2011")
    dogru(a11["n"] == 4 and a11["daha_acilan"] == 4, "Ağustos 2011 kümesi dört/dört değil")
    metinde(m, f"medyan {bp(a11['ileri_medyan'], 1, True)}", "özet Ağustos 2011")
    dogru(ep["2025 Bayrou güven oylaması"]["sonra_3a"] < 0, "Bayrou epizodu daralmadı")
    metinde(m, f"2 yıllık farkın 2011 zirvesi {bp(eg['2']['zirve'])} (bugün {sayi(eg['2']['spread'])})", "2y zirve")
    metinde(m, f"1 Ekim'in New York kapanışı {sayi(k['son'], 4)}.", "kur referans")
    metinde(m, f"(EUR/GBP'de {yz(d24['eurgbp']['b']['spr'] * 10, 2, True)}, t {sayi(d24['eurgbp']['t']['spr'], 1, True)}); "
               f"EUR/USD'deki {yz(d24['faiz+fr']['b']['spr'] * 10, 2, True)} sterlinde de var", "aritmetik yok")
    tah = eg10["b"]["ispr"] * e2c["ispr"]
    metinde(m, f"İtalya farkındaki 10 bp'lik açılmaya EUR/GBP'de {yz(eg10['b']['ispr'] * 10, 2, True)} eşlik ediyordu. "
               f"İkinci evrede İtalya farkı {bp(e2c['ispr'], 1, True)} açıldı; bu katsayıyla {yz(tah, 2, True)}, gerçekleşen "
               f"{yz(e2c['eurgbp'], 2, True)}", "İtalya aritmetiği")
    # ── Yöntem eki
    tz_ = o["temizlik"]
    metinde(m, f"Günlük seri {sayi(tz_['ham_bar'], 0)} kayıt; {sayi(tz_['hafta_sonu_atilan'], 0)} hafta sonu", "temizlik")
    metinde(m, f"{tz_['tasinmis_atilan']} tatil günü atıldı, {sayi(tz_['temiz_gun'], 0)} iş günü kaldı", "temiz gün")
    gc = bo["gecis"]
    metinde(m, f"({bo['eksik_is_gunu_2014']} eksik iş günü); boşluğun iki ucundaki farklar (7 Mart 2014'te "
               f"{bp(gc['2014-03-07']['fark'], 1, True)}, 2 Ocak 2015'te {bp(gc['2015-01-02']['fark'], 1, True)})",
            "boşluk geçişleri")
    metinde(m, f"Hafta içine düşen {bo['target_tatil']} TARGET tatilinin {bo['target_tatil_seride']}'i seride kalıyor",
            "TARGET")
    metinde(m, f"mutlak günlük değişim medyanı {bp(bo['target_tatil_mutlak_medyan'], 1)}", "TARGET medyan")
    g1 = h["10y_1_gercek"]
    metinde(m, f"1 Ekim'in {bp(g1['degisim'], 1, True)}'lik açılması {gun(g1['son_gorulme'])}'den beri en büyük", "tek gün")
    s7, s22 = h["sicrama_2017"], h["sicrama_2022"]
    metinde(m, f"({bp(s22['once'])}'den iki gün sonra {bp(s22['sonra'])})", "2022 sıçrama")
    metinde(m, f"fark {bp(s7['once'])}'den {bp(s7['gun'])}'ye sıçradı, 20 Ekim'de {bp(s7['on_gun_sonra'])}'deydi", "2017 sıçrama")
    dogru(s7["on_gun_sonra_tarih"] == "2017-10-20", "2017 sıçrama sonrası gözlem günü 20 Ekim değil")
    yh = o["yahoo_hiza"]
    metinde(m, f"medyanda {sayi(yh['2010–2026']['medyan_fark'], 4)} farklı (kaydırılmamış seride "
               f"{sayi(yh['kaydirmasiz_2010_2026']['medyan_fark'], 4)})", "Yahoo hizası")
    hz = d24["hazine+fr"]
    metinde(m, f"(fark {yz(hz['b']['spr'] * 10, 2, True)}, faiz farkı {yz(hz['b']['rdT'] * 10, 2, True)})", "Hazine sağlamlık")
    it24, vx = d24["faiz+fr+it"], d24["faiz+fr+vix"]
    metinde(m, f"sırasıyla {yz(it24['b']['spr'] * 10, 2, True)} ve {yz(vx['b']['spr'] * 10, 2, True)} bırakıyor", "sağlamlık")
    metinde(m, f"tek başına {sayi(bd['2026 Eylül']['fr_b'], 2)}'dan {sayi(b['eylul_1ekim']['fr_b'], 2)}'ye indiriyor",
            "Eylül betası")
    dogru(bd["2026 Eylül"]["n"] == 22, "Eylül beta penceresi 22 gün değil")
    # ECB faizleri
    ef = {r["gun"]: r["dfr"] for r in o["ecb_faiz"]}
    dogru(ef.get("2026-06-17") == 2.25 and ef.get("2026-09-16") == 2.5 and ef.get("2025-06-11") == 2.0,
          f"ECB mevduat faizi patikası metinle uyuşmuyor: {ef}")


def bicim(m: str) -> None:
    g = govde(m)
    g = re.sub(r"\$\$.*?\$\$", "", g, flags=re.S)
    g = re.sub(r"\$[^$\n]+\$", "", g)
    g = re.sub(r"`[^`]*`", "", g)
    g = re.sub(r"<GrafikEmbed[^>]*/>", "", g)
    for x in re.finditer(r"(?<![\w/.\-–])-%?\d", g):
        hatalar.append(f"ASCII tireli eksi sayı: {g[max(0, x.start() - 30):x.end() + 10]!r}")
    for x in re.finditer(r"\d[ \t]*%", g):
        hatalar.append(f"arkaya yazılmış yüzde: {g[max(0, x.start() - 20):x.end() + 5]!r}")
    sayac["metin"] += 1


# ─────────────────────────────────────────────── 4 · figürler
def figurler(m: str) -> None:
    kaynak = (BURASI / "sekil.py").read_text(encoding="utf-8")
    bas = kaynak.index("SEKILLER =")
    liste = re.findall(r'"(\d\d_[a-z_]+)"', kaynak[bas:kaynak.index("]", bas)])
    if len(liste) != 9:
        hatalar.append(f"figür listesi {len(liste)} öğe, beklenen 9")
    for ad in liste:
        if not (SEKIL / f"{ad}.html").exists():
            hatalar.append(f"figür yok: {ad}.html")
    gomulu = re.findall(r'<GrafikEmbed src="/analiz/' + SLUG + r'/(\d\d_[a-z_]+)\.html"[^>]*no="(\d\d)"', m)
    if [a for a, _ in gomulu] != liste:
        hatalar.append(f"gömme sırası figür listesiyle aynı değil: {[a for a, _ in gomulu]}")
    if [n for _, n in gomulu] != [f"{i:02d}" for i in range(1, len(gomulu) + 1)]:
        hatalar.append(f"şekil numaraları sıralı değil: {[n for _, n in gomulu]}")
    for ad, no in gomulu:
        yol = SEKIL / f"{ad}.html"
        if not ad.startswith(no + "_"):
            hatalar.append(f"figür dosyasının öneki gömme numarasıyla aynı değil: {ad} · no {no}")
        if yol.exists():
            h = yol.read_text(encoding="utf-8")
            if f"Şekil {no} —" not in h and f"\\u015eekil {no} \\u2014" not in h:
                hatalar.append(f"figürün içindeki başlık 'Şekil {no}' değil: {ad}")
    # Şekil 02'nin olay takvimi metinde anılmalı
    blok = kaynak[kaynak.index("OLAYLAR = ["):kaynak.index("]", kaynak.index("OLAYLAR = ["))]
    for g in re.findall(r'"(\d{4}-\d\d-\d\d)"', blok):
        sayac["metin"] += 1
        if f"{int(g[8:10])} {AY[int(g[5:7])]}" not in _duz(m):
            hatalar.append(f"Şekil 02 olayı metinde anılmıyor: {g}")


def main() -> int:
    o = arsiv()
    m = MDX.read_text(encoding="utf-8")
    rakamlar(m, o)
    tablolar_sina(tablolar(m), o)
    cumleler(m, o)
    bicim(m)
    figurler(m)
    if hatalar:
        print(f"✗ OAT–Bund yazısı · {len(hatalar)} hata")
        for h in hatalar[:120]:
            print("  ·", h)
        return 1
    print(f"✓ OAT–Bund yazısı · {sayac['arsiv']} arşiv ölçütü, {sayac['hucre']} tablo hücresi, "
          f"{sayac['metin']} metin parçası, 9 figür")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
