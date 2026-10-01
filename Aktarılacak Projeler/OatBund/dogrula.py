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
   mı, ve Şekil 02'nin olay takvimindeki her gün metinde anılıyor mu?

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


def tablo(tl: list, baslik: str) -> list[list[str]]:
    bulunan = [t for t in tl if t and t[0][0] == baslik]
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


def rakamlar(m: str, o: dict) -> None:
    sv, d = o["seviye"], o["duyarlilik"]["2024–2026"]["faiz+fr"]
    beklenen = [bp(sv["spread"]), bp(o["hiz"]["10y_22"]["degisim"], 1, True),
                bp(o["fransa_italya"]["fr_eksi_it"], 1, True), yz(d["b"]["spr"] * 10, 2, True),
                yz(o["atif"]["2026-08-26"]["kur_gercek"], 2, True), sayi(o["kur"]["son"], 4),
                yz(o["ileri"][0]["daha_acildi_payi"], 1), "%119,0"]
    blok = m[m.index('<ul class="rakamlar">'):m.index("</ul>", m.index('<ul class="rakamlar">'))]
    yazili = re.findall(r"<li><b>([^<]+)</b>", blok)
    sayac["hucre"] += len(beklenen)
    if yazili != beklenen:
        hatalar.append(f"rakam şeridi: metin {yazili}, ölçüm {beklenen}")
    metinde(blok, f"{AY[int(o['kur']['son_gorulme'][5:7])]} {o['kur']['son_gorulme'][:4]}", "kur son görülme")
    metinde(blok, f"{AY[int(sv['son_gorulme'][5:7])]} {sv['son_gorulme'][:4]}", "fark son görülme")
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
    # beta
    t = tablo(tl, "dönem")
    for r in o["beta"]["donemler"]:
        hucre(t, r["ad"], 1, sayi(r["fr_b"], 2), "beta")
        hucre(t, r["ad"], 2, sayi(r["it_b"], 2), "beta")
        hucre(t, r["ad"], 3, sayi(r["n"], 0), "beta")
    # büyük günler
    t = tablo(tl, "gün")
    for r in o["buyuk_gunler"]:
        e = f"{r['gun'][8:10]}.{r['gun'][5:7]}"
        hucre(t, e, 1, bp(r["spr"], 1, True), "büyük günler")
        for i, k in enumerate(("fr", "de", "us10", "it_spr"), 2):
            hucre(t, e, i, sayi(r[k], 1, True), "büyük günler")
    # duyarlılık
    t = [x for x in tl if x and x[0][:2] == ["dönem", "hafta"]]
    t = t[0] if t else (hatalar.append("tablo bulunamadı: duyarlılık") or [])
    for ad, mm in o["duyarlilik"].items():
        f = mm["faiz+fr"]
        hucre(t, ad, 1, sayi(f["n"], 0), "duyarlılık")
        hucre(t, ad, 2, yz(f["b"]["spr"] * 10, 2, True), "duyarlılık")
        hucre(t, ad, 3, sayi(f["t"]["spr"], 1), "duyarlılık")
        hucre(t, ad, 4, yz(f["b"]["rd"] * 10, 2, True), "duyarlılık")
        hucre(t, ad, 5, sayi(f["t"]["rd"], 1), "duyarlılık")
        hucre(t, ad, 6, sayi(f["r2"], 3), "duyarlılık")
    # örneklem dışı
    t = tablo(tl, "tahmin dönemi")
    for k, (eg, te) in {"2004_2023": ("2004–2023", "2024–2026"), "2013_2023": ("2013–2023", "2024–2026"),
                        "2004_2019": ("2004–2019", "2020–2026")}.items():
        r = o["orneklem_disi"][k]
        hucre(t, eg, 1, te, "örneklem dışı")
        hucre(t, eg, 2, sayi(r["test_n"], 0), "örneklem dışı")
        hucre(t, eg, 3, sayi(r["faiz"]["r2_dis"], 3), "örneklem dışı")
        hucre(t, eg, 4, sayi(r["faiz+fr"]["r2_dis"], 3), "örneklem dışı")
        hucre(t, eg, 5, yz(r["kazandigi_hafta_payi"], 1), "örneklem dışı")
        hucre(t, eg, 6, sayi(r["esli_t"], 2), "örneklem dışı")
    # atıf duyarlılığı
    t = tablo(tl, "katsayıların tahmin dönemi")
    etiket = {"2024-01-03–2026-06-24": "Ocak 2024 – Haziran 2026", "2004-01-07–2023-12-27": "2004–2023",
              "2013-01-02–2023-12-27": "2013–2023", "2004-01-07–2026-06-24": "2004 – Haziran 2026"}
    for r in o["atif_duyarlilik"]:
        e = etiket[r["egitim"]]
        hucre(t, e, 1, sayi(r["n"], 0), "atıf duyarlılığı")
        hucre(t, e, 2, yz(r["spread_payi"], 2, True), "atıf duyarlılığı")
        hucre(t, e, 3, yz(r["faiz_payi"], 2, True), "atıf duyarlılığı")
        hucre(t, e, 4, yz(r["artik"], 2, True), "atıf duyarlılığı")
    # epizotlar
    t = tablo(tl, "epizot")
    for r in o["epizotlar"]:
        hucre(t, r["ad"], 1, bp(r["bas_seviye"]), "epizot")
        hucre(t, r["ad"], 2, bp(r["zirve"]), "epizot")
        hucre(t, r["ad"], 3, bp(r["acilma"], 1, True), "epizot")
        hucre(t, r["ad"], 4, sayi(r["is_gunu"], 0), "epizot")
        hucre(t, r["ad"], 5, yz(r["eurusd_yuzde"], 2, True), "epizot")
        hucre(t, r["ad"], 6, bp(r["it_bp"], 1, True), "epizot")
        for i, k in ((7, "sonra_1a"), (8, "sonra_3a")):
            hucre(t, r["ad"], i, "—" if r[k] is None else bp(r[k], 1, True), "epizot")
    # olay tepkileri
    t = tablo(tl, "olay")
    for r in o["olay_tepkileri"]:
        hucre(t, r["ad"], 1, gun_k(r["sonra"]), "olay")
        hucre(t, r["ad"], 2, bp(r["spr"], 1, True), "olay")
        hucre(t, r["ad"], 3, bp(r["it"], 1, True), "olay")
        hucre(t, r["ad"], 4, yz(r["fx"], 2, True), "olay")


def cumleler(m: str, o: dict) -> None:
    sv, h, k = o["seviye"], o["hiz"], o["kur"]
    fi, eg, oy = o["fransa_italya"], o["egri"], o["oynaklik"]
    d24 = o["duyarlilik"]["2024–2026"]
    a = o["atif"]["2026-08-26"]
    il, il66, il50 = o["ileri"][0], o["ileri"][1], o["ileri"][3]
    b, p = o["beta"], o["gun_ici_pencere"]
    # seviye ve konum
    metinde(m, f"{gun(sv['son_gorulme'])}'den beri en yüksek ve 2000'den bu yana günlerin "
               f"{yz(sv['yuzdelik_2000'], 1)}'sinden yukarıda", "son görülme ve yüzdelik")
    metinde(m, f"Tarihî zirve {gun(sv['tarihi_zirve_gun'])}'de {bp(sv['tarihi_zirve'])}", "tarihî zirve")
    metinde(m, f"18 Eylül'de {gun(sv['onceki_100'])}'den beri ilk kez 100 bp'nin üstünde kapandı", "100 eşiği")
    dogru(sv["ilk_100"] == "2026-09-18", f"100 bp ilk aşım günü {sv['ilk_100']}")
    g18 = [r for r in o["buyuk_gunler"] if r["gun"] == "2026-09-18"][0]
    metinde(m, f"18 Eylül'de {bp(g18['spr_seviye'])} ile", "18 Eylül seviyesi")
    dogru(sv["us10_onceki_gun"] == "2026-09-30", "ABD 10y önceki gün 30 Eylül değil")
    metinde(m, f"ABD 10 yıllığı %{sayi(sv['us10_son'], 2)}–{sayi(sv['us10_onceki'], 2)}", "özet ABD 10y")
    metinde(m, f"ABD 10 yıllığı 30 Eylül'de %{sayi(sv['us10_onceki'], 2)}\nkapandı", "ABD 10y 30 Eylül")
    dogru(o["kur"]["son"] < 1.1340, "ECB kuru MUFG desteğinin (1,1340) altında değil")
    metinde(m, f"Fransa 10 yıllığı %{sayi(sv['fr10'], 3)}, Almanya 10 yıllığı %{sayi(sv['de10'], 3)} kapandı; fark "
               f"({sayi(sv['fr10'], 3)} − {sayi(sv['de10'], 3)}) × 100 = {bp(sv['spread'])}", "tanım hesabı")
    metinde(m, f"yıla {bp(sv['seviye_yb'])} ile başladı, 25 Şubat'ta {bp(sv['yil_dibi'])} ile yılın dibini gördü",
            "yıl başı ve dip")
    dogru(sv["epizot_bas_tutarli"], "yılın dibi EPIZOT_BAS ile aynı gün değil")
    metinde(m, f"Haziran sonunda {sayi(sv['seviye_haziran'])}, Ağustos sonunda {bp(sv['seviye_agustos'])} idi; 31 "
               f"Ağustos'tan bu yana {bp(sv['degisim_agustos'], 1, True)} açıldı", "haziran-ağustos")
    metinde(m, f"son bir haftada {sayi(sv['degisim_1h'], 1, True)}, son bir ayda {bp(sv['degisim_1a'], 1, True)}",
            "hafta-ay")
    metinde(m, f"Yılın dibinden bu yana {bp(sv['epizot_degisim'], 1, True)} açıldı", "epizot")
    metinde(m, f"140,9 bp ile {AY[int(sv['son_gorulme'][5:7])]} {sv['son_gorulme'][:4]}'den beri en yüksekte; son 22 iş "
               f"gününde {bp(h['10y_22']['degisim'], 1, True)}", "tez seviye ve hız")
    dogru(sv["spread"] == 140.91, "tezdeki 140,9 bp ölçümle aynı değil")
    # kaynak
    kf = o["kaynak"]["fr"]
    metinde(m, f"{kf['ay']} ayda {sayi(kf['korelasyon'], 3)} korelasyon veriyor, ortalama fark {bp(kf['ort_fark'])}",
            "kaynak sınaması")
    metinde(m, f"resmî seri {sayi(kf['son_ay_resmi'])}, günlük seriden kurulan ortalama {bp(kf['son_ay_cnbc'])}",
            "kaynak son ay")
    # temizlik
    tz = o["temizlik"]
    metinde(m, f"Günlük seri {sayi(tz['ham_bar'], 0)} kayıt; {sayi(tz['hafta_sonu_atilan'], 0)} hafta sonu",
            "temizlik")
    metinde(m, f"{sayi(tz['temiz_gun'], 0)} iş günü kaldı", "temiz gün")
    metinde(m, f"({tz['tasinmis_atilan']} gün)", "taşınmış gün")
    g1 = h["10y_1_gercek"]
    metinde(m, f"1 Ekim'in {bp(g1['degisim'], 1, True)}'lik açılması {gun(g1['son_gorulme'])}'den beri en büyük",
            "tek gün")
    # bacaklar ve evreler
    e1, e2 = b["evre1"], b["evre2"]
    metinde(m, f"Fransa {sayi(e1['fr'], 1, True)}\n  bp, Almanya {sayi(e1['de'], 1, True)} bp, ABD 10 yıllığı "
               f"{bp(e1['us10'], 1, True)}; fark {bp(e1['spr'], 1, True)}", "evre 1")
    metinde(m, f"Fransa {sayi(e2['fr'], 1, True)} bp, Almanya {sayi(e2['de'], 1, True)} bp; fark üç\n  günde "
               f"{bp(e2['spr'], 1, True)}", "evre 2")
    metinde(m, f"OAT {bp(e2['fr'], 1, True)} yükselirken Bund {bp(e2['de'], 1, True)} düştü", "tez evre 2")
    metinde(m, f"Bund'un {bp(e1['de'], 1, True)} yükselişi, {sayi(e1['beta_kullanilan'], 2)}'lik betayla farkı yalnız\n"
               f"{bp(e1['beta_payi'], 1, True)} açar", "beta payı")
    metinde(m, f"2013–2019'da {sayi(b['donemler'][0]['fr_b'], 2)} iken 2026'da {sayi(b['donemler'][3]['fr_b'], 2)}",
            "beta özet")
    # akranlar
    ak = {r["ad"]: r for r in o["akranlar"]}
    metinde(m, "Fransa " + bp(ak["Fransa"]["degisim_haziran"], 1, True) + ", İtalya "
            + sayi(ak["İtalya"]["degisim_haziran"], 1, True) + ", Belçika " + sayi(ak["Belçika"]["degisim_haziran"], 1, True)
            + ", Yunanistan " + sayi(ak["Yunanistan"]["degisim_haziran"], 1, True) + ", İspanya "
            + sayi(ak["İspanya"]["degisim_haziran"], 1, True) + ",\nPortekiz " + sayi(ak["Portekiz"]["degisim_haziran"], 1, True)
            + ", Avusturya " + sayi(ak["Avusturya"]["degisim_haziran"], 1, True) + ", Hollanda "
            + bp(ak["Hollanda"]["degisim_haziran"], 1, True), "akran değişimleri")
    metinde(m, f"{bp(ak['Fransa']['spread'])}'ye karşı İtalya {sayi(ak['İtalya']['spread'])}, Belçika "
               f"{sayi(ak['Belçika']['spread'])}, İspanya {bp(ak['İspanya']['spread'])}", "akran seviyeleri")
    dogru(o["akranlar"][0]["ad"] == "Fransa", "Fransa sepetteki en geniş fark değil")
    for u in ("Yunanistan", "Portekiz"):
        dogru(ak[u]["gun"] == "2026-09-30", f"{u} son kotasyonu 30 Eylül değil: {ak[u]['gun']}")
    metinde(m, f"İtalya'nınkinin {bp(fi['fr_eksi_it'])} üstünde; bu sıralama 2000'den bu yana ilk kez "
               f"{gun(fi['ilk_pozitif'])}'te oluştu ve {gun(fi['kesintisiz_bas'])}'dan beri kesintisiz sürüyor "
               f"({fi['gun_sayisi']} iş günü)", "Fransa–İtalya")
    metinde(m, f"30 Eylül'deki\n{bp(fi['tarihce_zirve'], 1, True)}", "Fransa–İtalya zirvesi")
    dogru(fi["tarihce_zirve_gun"] == "2026-09-30", "Fransa–İtalya zirve günü 30 Eylül değil")
    # eğri
    metinde(m, f"2\nyıllık fark bir günde {bp(eg['2']['degisim_1g'], 1, True)} ile {bp(eg['2']['spread'])}'ye çıktı "
               f"(30 Haziran'da {bp(eg['2']['spread'] - eg['2']['degisim_haziran'])} idi; bu seviye\nen son "
               f"{gun(eg['2']['son_gorulme'])}'de görülmüştü)", "eğri 2y")
    metinde(m, f"5 yıllık {sayi(eg['5']['spread'])}, 30 yıllık {bp(eg['30']['spread'])}", "eğri 5-30")
    metinde(m, f"İtalya'nın 2 yıllık farkı da {bp(eg['it2']['degisim_1g'], 1, True)} ile {bp(eg['it2']['spread'])}'ye çıktı",
            "İtalya 2y")
    metinde(m, f"Almanya 2 yıllığı {bp(eg['de2y_1g_bp'])}, ABD 2 yıllığı {bp(eg['us2y_1g_bp'])} düştü", "2y bacaklar")
    metinde(m, f"2 yıllık farkın 2011 zirvesi\n{bp(eg['2']['zirve'])} (bugün {sayi(eg['2']['spread'])})", "2y zirve")
    # duyarlılık cümleleri
    f24, f04 = d24["faiz+fr"], o["duyarlilik"]["2004–2026"]["faiz+fr"]
    metinde(m, f"−%{sayi(abs(f24['b']['spr'] * 10), 2)} (t {sayi(f24['t']['spr'], 1)}), 2004–2026'da "
               f"{yz(f04['b']['spr'] * 10, 2, True)} eşlik ediyor", "özet duyarlılık")
    it10 = o["duyarlilik"]["2010–2012"]["faiz+fr+it"]
    metinde(m, f"Fransa'nın katsayısı\nkayboluyor ({yz(it10['b']['spr'] * 10, 2, True)}, t {sayi(it10['t']['spr'], 1)}), "
               f"İtalya'nınki {yz(it10['b']['ispr'] * 10, 2, True)} (t {sayi(it10['t']['ispr'], 1)})", "2010–12 İtalya")
    it24 = d24["faiz+fr+it"]
    metinde(m, f"({yz(it24['b']['spr'] * 10, 2, True)},\nt {sayi(it24['t']['spr'], 1)}), İtalya'nınki anlamsız "
               f"(t {sayi(it24['t']['ispr'], 1)})", "2024–26 İtalya")
    vx = d24["faiz+fr+vix"]
    metinde(m, f"sırasıyla {yz(it24['b']['spr'] * 10, 2, True)} ve {yz(vx['b']['spr'] * 10, 2, True)} bırakıyor",
            "sağlamlık")
    kk = o["kayan"]
    metinde(m, f"değer {yz(kk['son'], 2, True)}, bant {yz(kk['son_alt'], 2, True)} ile {yz(kk['son_ust'], 2, True)}; "
               f"2013–2019 ortalaması {yz(kk['ort_2013_2019'], 2, True)},\n2024'ten sonraki ortalama "
               f"{yz(kk['ort_2024_sonra'], 2, True)}", "kayan")
    dogru(kk["son_tarih"] == "2026-09-30", "kayan pencerenin son haftası 30 Eylül değil")
    od = o["orneklem_disi"]["2004_2023"]
    metinde(m, f"açıklanan payı {sayi(od['faiz']['r2_dis'], 3)}'dan {sayi(od['faiz+fr']['r2_dis'], 3)}'ye çıkarıyor",
            "özet örneklem dışı")
    # atıf
    metinde(m, f"kur {yz(a['kur_gercek'], 2, True)} kaybetti; fark {bp(a['spr_toplam'], 1, True)}, faiz farkı "
               f"{bp(a['rd_toplam'], 1, True)}\naçıldı. Fark kanalı {yz(a['spread_payi'], 2, True)}, faiz kanalı "
               f"{yz(a['faiz_payi'], 2, True)}, kalan {yz(a['artik'], 2, True)}", "atıf 26 Ağustos")
    metinde(m, f"30 Haziran'dan bakıldığında kalan {yz(o['atif']['2026-06-30']['artik'], 2, True)}", "atıf haziran")
    metinde(m, f"(25 Şubat) bakıldığında kalan yine küçük ({yz(o['atif']['2026-02-25']['artik'], 2, True)})",
            "atıf şubat")
    k_ = a["katsayi"]
    metinde(m, f"Katsayılar 10 bp fark için {yz(k_['b']['spr'] * 10, 2, True)},\n10 bp faiz farkı için "
               f"{yz(k_['b']['rd'] * 10, 2, True)}", "atıf katsayı")
    metinde(m, f"(Ocak 2024 – Haziran\n2026, {k_['n']} hafta)", "atıf tahmin penceresi")
    ad = o["atif_duyarlilik"]
    en_kucuk = min(abs(r["spread_payi"]) for r in ad)
    dogru(all(abs(r["spread_payi"]) > abs(r["faiz_payi"]) for r in ad), "her tahmin döneminde fark kanalı > faiz kanalı değil")
    dogru(en_kucuk / abs(a["kur_gercek"]) >= 0.5, "fark kanalı kurun kaybının en az yarısı değil")
    metinde(m, f"katsayının tahmin dönemine göre {yz(-en_kucuk, 2, True)} ile {yz(a['spread_payi'], 2, True)} arası",
            "özet atıf aralığı")
    # gün içi pencere
    metinde(m, f"Fransa farkı {sayi(p['spr']['bas'])}'dan {bp(p['spr']['son'])}'ye ({sayi(p['spr']['degisim'], 1, True)}), "
               f"İtalya'nın 2 yıllık farkı {sayi(p['ispr2']['bas'])}'dan {bp(p['ispr2']['son'])}'ye\n"
               f"({sayi(p['ispr2']['degisim'], 1, True)}) çıktı; ABD 2 yıllığı {bp(p['us2y']['degisim_bp'])}, Almanya 2 "
               f"yıllığı {bp(p['de2y']['degisim_bp'])} düştü", "gün içi pencere")
    metinde(m, f"yıllık farkı yalnız {bp(p['rd']['degisim'], 1, True)} açıldı. Euro aynı iki saatte "
               f"{sayi(p['eurusd']['bas'], 4)}'ten {sayi(p['eurusd']['son'], 4)}'e, {yz(p['eurusd']['degisim_yuzde'], 2, True)}",
            "gün içi kur")
    g5 = o["gun_ici_bes_gun"]
    metinde(m, f"korelasyon {sayi(g5['korelasyon'], 2)} ({g5['n']} gözlem)", "beş gün korelasyon")
    dogru(len(g5["gunler"]) == 8, f"gün içi arşivdeki gün sayısı {len(g5['gunler'])}, metin 'sekiz'")
    # öbür piyasalar
    pz = {r["kod"]: r for r in o["piyasalar"]}
    metinde(m, f"CAC 40 {yz(pz['cac']['degisim'], 2, True)},\nDAX {yz(pz['dax']['degisim'], 2, True)}, Euro Stoxx 50 "
               f"{yz(pz['sx5e']['degisim'], 2, True)}; Fransız bankaları BNP Paribas {yz(pz['bnp']['degisim'], 2, True)}, "
               f"Société Générale\n{yz(pz['socgen']['degisim'], 2, True)}, Crédit Agricole {yz(pz['cagri']['degisim'], 2, True)}",
            "hisseler")
    metinde(m, f"İsviçre frangına karşı yalnız\n{yz(pz['eurchf']['degisim'], 2, True)}, sterline karşı "
               f"{yz(pz['eurgbp']['degisim'], 2, True)} kaybetti; yene karşı {yz(pz['eurjpy']['degisim'], 2, True)}. "
               f"Dolar endeksi {yz(pz['dxy']['degisim'], 2, True)}", "çaprazlar")
    # kur
    metinde(m, f"1 Ekim'in resmî\nkuru ({sayi(k['son'], 4)})", "resmî kur")
    # geçmiş
    ay = o["ayrisma"]
    metinde(m, f"+%{sayi(ay['y2025']['fx'], 2)} kazanırken Fransa farkı {sayi(ay['y2025']['spr_bas'])}'den "
               f"{bp(ay['y2025']['spr_son'])}'ye", "2025 ayrışması")
    metinde(m, f"fesih\n  öncesindeki {bp(ay['fesih_once'])}'ye bir daha hiç inmedi; ondan sonraki en düşük kapanış bu yılın\n"
               f"  dibi, {bp(ay['fesih_sonrasi_dip'])}", "fesih primi")
    dogru(ay["fesih_sonrasi_dip_gun"] == sv["yil_dibi_gun"], "fesih sonrası dip bu yılın dibi değil")
    ep = {r["ad"]: r for r in o["epizotlar"]}
    e11, e24 = ep["2011 euro bölgesi borç krizi"], ep["2024 meclisin feshi"]
    metinde(m, f"2011: {e11['is_gunu']} iş gününde {bp(e11['acilma'], 1, True)}, EUR/USD {yz(e11['eurusd_yuzde'], 1, True)}",
            "özet 2011")
    metinde(m, f"fark {e24['is_gunu']} iş günü içinde {bp(e24['acilma'], 1, True)} açıldı ve fesih öncesi seviyeye "
               f"({bp(ay['fesih_once'])})", "özet 2024")
    metinde(m, f"aynı pencerede İtalya'nın farkı {bp(e11['it_bp'], 1, True)}\n  açıldı, bu yıl "
               f"{bp(ep['2026']['it_bp'], 1, True)}", "2011 İtalya")
    oy_ = {r["ad"]: r for r in o["olay_tepkileri"]}
    notlar = [r["spr"] for r in o["olay_tepkileri"] if r["tur"] == "not" and not r["once"].startswith("2012")]
    dogru(len(notlar) == 7, f"2012 sonrası not kararı sayısı {len(notlar)}, metin 'yedi'")
    metinde(m, f"değişim {bp(min(notlar))[:-3]} ile {bp(max(notlar), 1, True)} arası", "özet not aralığı")
    metinde(m, f"tepki gününde fark {sayi(min(notlar), 1, True)} ile {bp(max(notlar), 1, True)}\n  arasında değişti",
            "not aralığı")
    dr, l17 = oy_['Draghi: "ne gerekiyorsa"'], oy_["2017 ilk tur: Macron–Le Pen"]
    metinde(m, f"konuşması günü fark {bp(dr['spr'], 1, True)}, euro {yz(dr['fx'], 2, True)}", "özet Draghi")
    metinde(m, f"fark bir günde {bp(l17['spr'], 1, True)}, euro {yz(l17['fx'], 2, True)}", "özet 2017")
    # ileri
    metinde(m, f"ertesi ay medyanda\n{bp(il['medyan'], 1, True)} geriledi; gözlemlerin {yz(il['daha_acildi_payi'], 1)}'inde "
               f"daha da açıldı, onda birinde {bp(il['p10'], 1, True)}'den fazla\ndaraldı", "ileri dağılım")
    km = il["kumeler"]
    dogru(il["epizot"] == 7 and il["daha_acilan_kume"] == 2, "ileri dağılım: 7 küme / 2 açılan küme değil")
    k11 = [c for c in km if c["bas"].startswith("2011-10")][0]
    k12 = [c for c in km if c["bas"].startswith("2012-04")][0]
    metinde(m, f"({k11['n']} gözlemin {k11['daha_acilan']}'sı) ve Nisan–Mayıs 2012 ({k12['n']} gözlemin "
               f"{k12['daha_acilan']}'i)", "açılan kümeler")
    metinde(m, f"Üç aylık ufukta medyan {bp(il66['medyan'], 1, True)} ve\ngözlemlerin {yz(il66['daha_acildi_payi'], 1)}'i",
            "66 gün")
    metinde(m, f"o iki kümenin {il50['gozlem']}\ngözleminde ertesi ayın medyanı {bp(il50['medyan'], 1, True)}", "50 bp")
    dogru(il50["epizot"] == 2 and all(c["bas"][:4] in ("2011", "2012") for c in il50["kumeler"]),
          "50 bp eşiğinin kümeleri 2011–12 dışında")
    dogru(il["gozlem"] == 51, f"30 bp eşiğinde gözlem {il['gozlem']}, metin 51")
    metinde(m, f"standart sapması {bp(oy['sigma_gunluk'], 2)}; 2013'ten\nbu yana ortalama {bp(oy['sigma_2013_sonrasi'], 2)}"
               f" — {sayi(oy['oran'], 1)} katı", "oynaklık")
    metinde(m, f"±1,96σ bandı ±{bp(oy['bant_1a'])}", "bant")
    alt, ust = oy["spread"] - oy["bant_1a"], oy["spread"] + oy["bant_1a"]
    metinde(m, f"{sayi(alt, 0)} ile {sayi(ust, 0)} bp arasında", "bant uçları")
    # kur aritmetiği
    c24, c04 = f24["b"]["spr"], f04["b"]["spr"]
    metinde(m, f"+20 bp daha açılması kurda yaklaşık {yz(c24 * 20, 1, True)}, 2004–2026 katsayısıyla "
               f"({yz(c04 * 10, 2, True)}) {yz(c04 * 20, 1, True)} demek", "aritmetik +20")
    metinde(m, f"aynı katsayılarla {yz(-c24 * 50, 1, True)} ve {yz(-c04 * 50, 1, True)}", "aritmetik −50")
    metinde(m, f"+20 bp, öbür her şey sabitken {yz(c24 * 20, 1, True)} demek", "özet aritmetik")
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
