#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KAĞIT VE OIS DERSİ — yayımlanan metni ölçüme karşı sınayan kapı.

Sayfa sınavı (26. ölçüt) bu betiği her yayında koşturur. Yayın koşucusunda
numpy/pandas YOK: betik yalnız standart kütüphaneyle çalışır ve ağa çıkmaz.
Üç soru sorar:

1. ARŞİV: `veri/` altındaki her dosyanın sıkıştırılmamış içeriğinin özü
   (sha256) künyedekiyle aynı mı? Girdi değişmişse dersin bütün sayıları
   gerekçesiz kalır.
2. METİN: dersin tablolarındaki her ölçülmüş sayı `veri/olcum.json` ile aynı
   mı? Beklenen değerler bu dosyaya ELLE yazılmaz; ölçüm dosyasından okunur ve
   metnin tabloları ayrıştırılıp hücre hücre karşılaştırılır. İki liste
   tutulsaydı bir gün sessizce ayrışırdı.
3. FİGÜRLER: on yedi figür yayın dizininde var mı ve metin her birini gömüyor mu?

Koşum:  python3 dogrula.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
MDX = KOK / "site/src/content/arastirma/kagit-ve-ois-trading.mdx"
SEKIL = KOK / "site/public/arastirma/kagit-ve-ois-trading"
SEKILLER = ["01_egri_tasima", "02_durasyon_getiri", "03_tlref_politika", "04_tasima_haritasi",
            "05_getiri_ayrisimi", "06_tasima_kurallari", "07_fonlama_gecis", "08_pca", "09_kadran",
            "10_egim_seviye", "11_rejim_haritasi", "12_fly_agirlik", "13_fly_ayrisim", "14_fly_haritasi",
            "15_barbell_bullet", "16_kalicilik", "17_senaryo_matrisi"]

hatalar: list[str] = []
sayac = {"hucre": 0, "metin": 0}


# ─────────────────────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 0, arti: bool = False) -> str:
    """Ondalık virgül, binlik nokta, eksi U+2212."""
    s = f"{abs(x):,.{b}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if round(x, b) < 0:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0) else s


def yz(x: float, b: int = 2, arti: bool = False) -> str:
    """Yüzde işareti sayının önünde: %37,52 · −%1,25 · +%0,58."""
    s = "%" + sayi(abs(x), b)
    if round(x, b) < 0:
        return "−" + s
    return ("+" + s) if (arti and round(x, b) > 0) else s


def bp(x: float, arti: bool = False, b: int = 0) -> str:
    return sayi(x, b, arti) + " bp"


def ay(s: str) -> str:
    """'2025-03' → '03.2025'."""
    return f"{s[5:7]}.{s[:4]}"


# ─────────────────────────────────────────────────────────────── tablo ayrıştırma
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


def tablo(tl: list, ilk_hucre_iceren: str) -> list[list[str]]:
    """Başlık satırının ya da herhangi bir satırın ilk hücresinde aranan metni
    taşıyan ilk tablo."""
    for t in tl:
        if any(ilk_hucre_iceren in " | ".join(r) for r in t[:1]) or \
           any(r[0] == ilk_hucre_iceren for r in t):
            return t
    hatalar.append(f"tablo bulunamadı: {ilk_hucre_iceren!r}")
    return []


def satir_sina(t: list, ilk: str, beklenen: list[str], ad: str) -> None:
    if not t:
        return
    for r in t:
        if r[0] == ilk:
            for i, b in enumerate(beklenen):
                if b is None:
                    continue
                sayac["hucre"] += 1
                gercek = r[i + 1] if i + 1 < len(r) else "(yok)"
                if gercek != b:
                    hatalar.append(f"{ad} · '{ilk}' sütun {i + 2}: metin {gercek!r}, ölçüm {b!r}")
            return
    hatalar.append(f"{ad}: satır yok: {ilk!r}")


def metinde(m: str, parca: str, ad: str) -> None:
    """Parça düz metinde ya da KaTeX yazımında ('0{,}55') geçmeli."""
    sayac["metin"] += 1
    if parca not in m and parca.replace(",", "{,}") not in m:
        hatalar.append(f"metinde yok ({ad}): {parca!r}")


# ─────────────────────────────────────────────────────────────── 1 · arşiv
def arsiv() -> dict:
    kunye = json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))
    for ad, k in kunye["dosyalar"].items():
        ham = gzip.decompress((VERI / ad).read_bytes())
        if hashlib.sha256(ham).hexdigest() != k["sha256"]:
            hatalar.append(f"arşiv özü tutmuyor: {ad}")
    o = json.loads((VERI / "olcum.json").read_text(encoding="utf-8"))
    if o.get("cipa") != kunye["cipa"]:
        hatalar.append(f"ölçümün çıpası ({o.get('cipa')}) künyeninkiyle ({kunye['cipa']}) aynı değil")
    return o


# ─────────────────────────────────────────────────────────────── 2 · metin
def metin(o: dict) -> None:
    m = MDX.read_text(encoding="utf-8")
    tl = tablolar(m)
    VAD = {"n3a": "3 ay", "n6a": "6 ay", "n1y": "1 yıl", "n2y": "2 yıl", "n3y": "3 yıl",
           "n5y": "5 yıl", "n7y": "7 yıl"}

    # 1.1 ihale
    ih = o["ihale"]
    t = tablo(tl, "Kâğıt türü")
    for ad, satir in (("Sabit Kuponlu Devlet Tahvili", "Sabit kuponlu devlet tahvili"),
                      ("TÜFE'ye Endeksli Devlet Tahvili", "TÜFE'ye endeksli devlet tahvili"),
                      ("Değişken Faizli Devlet Tahvili", "Değişken faizli devlet tahvili"),
                      ("TLREF'e Endeksli Devlet Tahvili", "TLREF'e endeksli devlet tahvili"),
                      ("Hazine Bonosu", "Hazine bonosu"), ("Kuponsuz Devlet Tahvili", "Kuponsuz devlet tahvili")):
        v = ih["tur"][ad]
        satir_sina(t, satir, [str(v), yz(100 * v / ih["n"], 1)], "ihale türleri")
    t = tablo(tl, "Gösterge vade")
    for k, s in (("2y", "2 yıl"), ("5y", "5 yıl"), ("10y", "10 yıl")):
        v = ih["sabit_2024"][k]
        satir_sina(t, s, [str(v["n"]), sayi(v["tso_medyan"], 2)], "teklif/satış")
    for p in (yz(ih["rot_pay_medyan"], 1), yz(ih["rot_py_pay"], 1), yz(ih["rot_kamu_pay"], 1),
              f"{ih['rot_kamu_yok']} ihalede", f"{ih['n']} ihale"):
        metinde(m, p, "ROT")

    # 1.2 taşıma tablosu
    bg = o["bugun"]
    t = tablo(tl, "Vade | Getiri | Mod. durasyon")
    for k, s in (("0.5", "6 ay"), ("1", "1 yıl"), ("2", "2 yıl"), ("3", "3 yıl"), ("5", "5 yıl"), ("7", "7 yıl")):
        v = bg["tasima"][k]
        satir_sina(t, s, [yz(v["getiri"]), sayi(v["mod_dur"], 2), yz(v["tasima_yuzde"], arti=True),
                          yz(v["roll_yuzde"], arti=True), yz(v["toplam_yuzde"], arti=True),
                          bp(v["basabas_bp"])], "taşıma")
    for p in (yz(bg["tlref"]), yz(bg["tlref_etkin"]), yz(bg["basabas_enf_2y"]), yz(bg["r2y"])):
        metinde(m, p, "bugün")
    t = tablo(tl, "Yıllık kupon")
    for v in o["kupon_durasyon"]:
        ilk = "%0 (sıfır kuponlu)" if v["kupon"] == 0 else f"%{v['kupon']}"
        satir_sina(t, ilk, [sayi(v["fiyat"], 2), sayi(v["macaulay"], 2), sayi(v["modifiye"], 2),
                            sayi(v["dv01_100mn"]) + " TL/bp"], "kupon")

    # 1.3 durasyon getirisi
    d = o["durasyon"]
    V3 = ("2y", "5y", "7y")
    t = tablo(tl, "Ortalama fonlama üstü getiri (3 ay)")
    satir_sina(t, "Ortalama fonlama üstü getiri (3 ay)", [yz(d[k]["ort"], arti=True) for k in V3], "durasyon")
    satir_sina(t, "Kazandıran dönem payı", [yz(d[k]["pozitif"], 0) for k in V3], "durasyon")
    satir_sina(t, "Taşıma + roll pozitif başladığında: ortalama",
               [yz(d[k]["cr_pozitif"]["ort"], arti=True) for k in V3], "durasyon")
    satir_sina(t, "Taşıma + roll negatif başladığında: ortalama",
               [yz(d[k]["cr_negatif"]["ort"], arti=True) for k in V3], "durasyon")
    satir_sina(t, "Eğri ters başladığında: ortalama · kazandıran pay",
               [f"{yz(d[k]['ters']['ort'], arti=True)} · {yz(d[k]['ters']['pozitif'], 0)}" for k in V3], "durasyon")
    satir_sina(t, "Eğri ters değilken: ortalama · kazandıran pay",
               [f"{yz(d[k]['duz']['ort'], arti=True)} · {yz(d[k]['duz']['pozitif'], 0)}" for k in V3], "durasyon")
    satir_sina(t, "Gerçekleşen = a + b·(taşıma + roll): b · t",
               [f"{sayi(d[k]['egim'], 2)} · {sayi(d[k]['t_hac'], 2)}" for k in V3], "durasyon")
    metinde(m, sayi(d["5y"]["yarilar"]["2013_2019"], 2), "durasyon yarıları")
    metinde(m, sayi(d["5y"]["yarilar"]["2020_2026"], 2, arti=True), "durasyon yarıları")
    es = o["egim_seviye"]
    metinde(m, yz(es["y2_ilk"]), "2y ilk")
    metinde(m, yz(es["y2_max"][0]), "2y tepe")

    # 1.4 stres
    st = o["stres"]
    t = tablo(tl, "Vade | En büyük aylık yükseliş")
    for k in ("n2y", "n5y", "n7y"):
        v = st[k]
        satir_sina(t, VAD[k], [f"{bp(v['en_buyuk_artis'][0], True)} ({ay(v['en_buyuk_artis'][1])})",
                               f"{bp(v['en_buyuk_dusus'][0])} ({ay(v['en_buyuk_dusus'][1])})",
                               bp(v["p95_mutlak"]), bp(v["p95_mutlak_son36"])], "stres")
    t = tablo(tl, "Vade | Stres = en büyük aylık yükseliş")
    for k in ("n2y", "n5y", "n7y"):
        v = st[k]
        w, p = v["en_buyuk_artis"][0], v["p95_mutlak_son36"]
        satir_sina(t, VAD[k], [bp(w), "≈" + sayi(round(50e6 / w, -2)) + " TL/bp",
                               bp(p), "≈" + sayi(round(50e6 / p, -2)) + " TL/bp"], "stres limiti")
    t = tablo(tl, "Çarpıklık")
    satir_sina(t, "200 bp'yi aşan aylık yükseliş · düşüş (ay sayısı)",
               [f"{st[k]['ay_200_ustu_artis']} · {st[k]['ay_200_ustu_dusus']}" for k in ("n2y", "n5y", "n7y")],
               "asimetri")
    satir_sina(t, "En büyük on yükselişin ortalaması · en büyük on düşüşün",
               [f"{sayi(st[k]['en_buyuk10_artis_ort'], 0, True)} · {bp(st[k]['en_buyuk10_dusus_ort'])}"
                for k in ("n2y", "n5y", "n7y")], "asimetri")
    satir_sina(t, "Çarpıklık", [sayi(st[k]["carpiklik"], 2) for k in ("n2y", "n5y", "n7y")], "asimetri")

    # 2.1–2.6 OIS (temsili)
    ois = o["temsili_ois"]
    t = tablo(tl, "Gecelik fixing (basit)")
    for v, ilk in zip(ois["uc_dil"], ("21.09.2026 fixingi", "politika faizi düzeyi", "temsili eğrinin fixingi")):
        satir_sina(t, f"{yz(v['gecelik'])} — {ilk}", [yz(v["ceyrek_92g"]), yz(v["yillik"])], "üç dil")
    bs = ois["bootstrap"]
    t = tablo(tl, "Dönem | İskonto faktörü")
    for i, ilk in enumerate(("0–3 ay", "3–6 ay", "6–9 ay", "9–12 ay")):
        satir_sina(t, ilk, [sayi(bs["df"][i], 5), yz(bs["forward_yuzde"][i]), yz(bs["gecelik_yuzde"][i])],
                   "bootstrap")
    for p in (yz(bs["ortalama_gecelik_1y"]), yz(bs["forward_3m_9m"]), yz(ois["arac"]["basabas"]),
              bp(ois["basabas_forward"]["fark_bp"]).replace(" bp", ""),
              sayi(ois["basabas_forward"]["fazla_fixing_mn"], 2), yz(ois["fixing_politikada"]["basabas"]),
              yz(ois["gecelik_6m"])):
        metinde(m, p, "OIS okuma")
    sen = ois["senaryo"]
    t = tablo(tl, "Senaryo | İlk çeyreğin yüzen oranı")
    a = sen["forward"]
    satir_sina(t, "A — forward'lar gerçekleşir",
               [None, yz(a["kotasyon_9m"]), sayi(a["tasima_mn"], 2, True), sayi(a["mtm_mn"], 2, True),
                f"≈ 0 ({sayi(a['toplam_mn'], 2, True)})"], "senaryo")
    b = ois["arac"]
    satir_sina(t, "B — eğri ve fixing sabit",
               [f"fixing {yz(ois['tlref'])}", yz(b["S_Th"]), sayi(b["tasima_mn"], 2, True),
                sayi(b["roll_mn"], 2, True), sayi(b["toplam_mn"], 2, True), sayi(-b["toplam_mn"], 2, True)],
               "senaryo")
    c = sen["hizli_normallesme"]
    satir_sina(t, "C — hızlı normalleşme",
               [f"ortalama fixing {yz(c['tlref_ort'])}", yz(c["kotasyon_9m"]), sayi(c["tasima_mn"], 2, True),
                sayi(c["mtm_mn"], 2, True), sayi(c["toplam_mn"], 2, True), sayi(-c["toplam_mn"], 2, True)],
               "senaryo")
    dd = sen["stres"]
    satir_sina(t, "D — tavan sürer, indirim fiyatı silinir",
               [f"fixing {yz(dd['tlref_ort'])}", yz(dd["kotasyon_9m"]), sayi(dd["tasima_mn"], 2, True),
                sayi(dd["mtm_mn"], 2, True), sayi(dd["toplam_mn"], 2, True), sayi(-dd["toplam_mn"], 2, True)],
               "senaryo")
    ornek = ois["ornek"]
    for p in (yz(ornek["F_tavan"]), sayi(ornek["carry_tavan"], 2), sayi(ornek["carry_bugun"], 2),
              sayi(ornek["carry_tavan_basit"], 2), sayi(b["dv01"]), f"{sayi(b['gunluk_bin'])} bin TL"):
        metinde(m, p, "araç vakası")
    t = tablo(tl, "Vade | Sabit oran | DV01 | Fixing taşıması")
    for k, s in (("6m", "6 ay"), ("1y", "1 yıl"), ("2y", "2 yıl"), ("5y", "5 yıl")):
        v = ois["kira"][k]
        satir_sina(t, s, [yz(v["K"]), sayi(v["dv01"]) + " TL/bp", sayi(v["tasima_mn"], 2) + " mn",
                          sayi(v["roll_mn"], 2) + " mn", sayi(v["toplam_mn"], 2) + " mn",
                          bp(v["dv01_basina_bp"])], "kira")
    t = tablo(tl, "Vade | DV01 / 100 mn (temsili)")
    for k, s in (("1y", "1 yıl"), ("2y", "2 yıl"), ("5y", "5 yıl"), ("7y", "7 yıl")):
        v = ois["risk_esdeger"][k]
        satir_sina(t, s, [sayi(v["dv01"]) + " TL/bp", bp(v["sigma_bp_ay"]), sayi(v["risk_1s_mn"], 2) + " mn",
                          sayi(v["esdeger_nominal_mn"]) + " mn"], "risk eşdeğeri")
    vr = ois["vaka_rejim"]
    for p in (yz(vr["F"]), yz(vr["gecelik_esdeger"]), sayi(vr["pay_3m_500mn"], 2),
              sayi(vr["rejim_3ay_surerse_pay_500mn"], 2), sayi(ois["serit"]["dv01_3m_500mn"]),
              sayi(ois["serit"]["dv01_3m9m_500mn"]), yz(ois["serit"]["pay_ilk_bacak"], 0)):
        metinde(m, p, "vaka/şerit")

    # 2.6 PPK günleri
    pg = o["ppk_gunu"]
    t = tablo(tl, "Vade | PPK: medyan")
    for k in ("n3a", "n1y", "n2y", "n5y"):
        x = pg["vade"][k]
        satir_sina(t, VAD[k], [bp(x["ppk_medyan"]), bp(x["ppk_p90"]), bp(x["diger_medyan"]), bp(x["diger_p90"]),
                               sayi(x["oran"], 1), bp(x["degisen_medyan"]), bp(x["sabit_medyan"])], "PPK günleri")
    metinde(m, f"Faizi değiştiren kararlar ({pg['degisen']})", "PPK karar sayısı")
    metinde(m, f"Sabit kararlar ({pg['sabit']})", "PPK karar sayısı")
    metinde(m, f"arasındaki {pg['karar']} PPK kararında", "PPK karar sayısı")
    # 2.5 görüş / oynaklık (türetilmiş: ilk yıl 100 bp görüşü, son 36 ayın oynaklığı)
    t = tablo(tl, "Vade | Görüşün kotasyona etkisi | Aylık oynaklık")
    s36 = bg["sigma36"]
    for k, s, etki in (("n1y", "1 yıl", 100), ("n2y", "2 yıl", 50), ("n5y", "5 yıl", 20), ("n7y", "7 yıl", 100 / 7)):
        satir_sina(t, s, [f"~{sayi(etki)} bp", bp(s36[k]), sayi(etki / s36[k], 2)], "görüş/oynaklık")

    # 2.4 TLREF bazı
    tb = o["tlref_baz"]
    t = tablo(tl, "Dönem | Gün | Baz medyanı")
    for k, s in (("2019_2020", "2019–2020"), ("2021_2022", "2021–2022"), ("2023-06_2024", "Haziran 2023–2024"),
                 ("2025_2026", "2025–2026")):
        v = tb["donem"][k]
        satir_sina(t, s, [str(v["n"]), bp(v["medyan"], True), yz(v["mutlak_100_ustu"], 0),
                          yz(v["tavanda"], 0), yz(v["tabanda"], 0)], "TLREF bazı")
    satir_sina(t, "Tümü", [sayi(tb["n"]), bp(tb["medyan"], True), yz(tb["mutlak_100_ustu"], 0),
                           yz(tb["tavanda"], 0), yz(tb["tabanda"], 0)], "TLREF bazı")
    for p in (bp(tb["p10"]), bp(tb["p90"], True)):
        metinde(m, p, "baz yüzdelikleri")
    t = tablo(tl, "Rejim | Başlangıç")
    tr_ad = {"politika": "Politika faizi", "koridor_ust": "Koridorun üst sınırı (%40,00)"}
    for r in tb["rejim_2026"]:
        gun = lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}"
        ilk = [x for x in t if x[1] == gun(r["bas"])]
        if not ilk:
            hatalar.append(f"rejim satırı yok: {r}")
            continue
        sayac["hucre"] += 3
        x = ilk[0]
        if x[0] != tr_ad[r["cipa"]] or x[2] != gun(r["son"]) or x[3] != str(r["is_gunu"]):
            hatalar.append(f"rejim satırı: metin {x}, ölçüm {r}")
    blok = tb["tavan_blok_2026"]
    for p in (f"{blok['takvim_gunu']} takvim", bp(blok["baz_ort_bp"]).replace(" bp", ""),
              sayi(blok["maliyet_100mn_mn"], 2), sayi(blok["maliyet_basit_100mn_mn"], 2)):
        metinde(m, p, "tavan bloğu")

    # 3.1 PCA
    pc = o["pca"]
    t = tablo(tl, "Düğüm | Seviye yükü")
    for k in ("n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y"):
        y = [pc["yuk"][f"pc{i}"][k] for i in (1, 2, 3)]
        satir_sina(t, VAD[k], [sayi(y[0], 4), sayi(y[1], 4), sayi(y[2], 4)] +
                   [bp(y[i] * pc["sigma_bp_ay"][i]) for i in range(3)], "PCA yükleri")
    satir_sina(t, "Varyans payı", [yz(pc["pay"][0], 1), yz(pc["pay"][1], 1), yz(pc["pay"][2], 1)] +
               [f"σ = {sayi(pc['sigma_bp_ay'][i], 1)} bp" for i in range(3)], "PCA payları")
    fr = o["pca_frekans"]
    t = tablo(tl, "Frekans | Değişim sayısı")
    for k, s in (("gunluk", "Günlük"), ("haftalik", "Haftalık"), ("ay_sonu", "Ay sonu"),
                 ("ay_ortalamasi", "Ay ortalaması")):
        v = fr[k]
        satir_sina(t, s, [sayi(v["n"])] + [yz(x, 1) for x in v["pay"]], "frekans")
    g = o["gurultu"]
    t = tablo(tl, "Dönem | Günlük değişimlerin 1. gecikme otokorelasyonu")
    for k, s in (("2013_2019", "2013–2019"), ("2023-07_2026", "Temmuz 2023 – 2026")):
        v = g[k]
        satir_sina(t, s, [" · ".join(sayi(v[d]["ac1"], 2) for d in ("n2y", "n5y", "n7y")),
                          " · ".join(sayi(v[d]["vr20"], 2) for d in ("n2y", "n5y", "n7y"))], "gürültü")
    yb = o["yapi_bugun"]
    t = tablo(tl, "Yapı | Seviye | Tarihsel yüzdelik")
    for k, s, yuzdeli in (("2y", "2 yıllık getiri", True), ("5y", "5 yıllık getiri", True),
                          ("7y", "7 yıllık getiri", True), ("2s7s", "2s7s (7y − 2y)", False),
                          ("2s5s", "2s5s (5y − 2y)", False), ("fly50", "2y5y7y fly (50:50)", False),
                          ("flyPCA", "2y5y7y fly (PCA-nötr)", False)):
        v = yb[k]
        if yuzdeli:
            sev = yz(v["seviye"] / 100)
            uc = f"{yz(v['en_dusuk'][0] / 100)} ({ay(v['en_dusuk'][1])}) · {yz(v['en_yuksek'][0] / 100)} ({ay(v['en_yuksek'][1])})"
        else:
            sev = bp(v["seviye"], True)
            uc = f"{bp(v['en_dusuk'][0], True)} ({ay(v['en_dusuk'][1])}) · {bp(v['en_yuksek'][0], True)} ({ay(v['en_yuksek'][1])})"
        satir_sina(t, s, [sev, sayi(v["yuzdelik"]), sayi(v["yuzdelik_son36"]), uc], "bugünkü eğri")

    # 3.2 kadranlar
    kd = o["kadran"]
    KAD = ["ayı yataylaşma", "boğa dikleşme", "ayı dikleşme", "boğa yataylaşma"]
    t = tablo(tl, f"Tüm aylar ({kd['n']})")
    satir_sina(t, f"Tüm aylar ({kd['n']})", [yz(kd["pay"][q], 1) for q in KAD], "kadran")
    satir_sina(t, f"Seviye hareketi 100 bp'yi aşan aylar ({kd['buyuk_n']})", [str(kd["buyuk"][q]) for q in KAD],
               "kadran")
    for f, s in (("artırım", "Artırım ayları"), ("indirim", "İndirim ayları"), ("sabit", "Sabit tutulan aylar")):
        v = kd["faz"][f]
        satir_sina(t, f"{s} ({v['n']})", [str(v[q]) for q in KAD], "kadran")
    n_art = len(kd["indirim_seviye_artti"])
    metinde(m, f"26 indirim ayının {n_art}'inde seviye yükseldi", "indirim ayları")
    mart = [x for x in kd["indirim_seviye_artti"] if x[0] == "2025-03"][0]
    metinde(m, bp(mart[2]), "Mart 2025")

    # 3.3 hedge oranı, faktörler, beta dönemleri, spread taşıması
    t = tablo(tl, "Uzun bacak DV01'i / 2y DV01'i")
    v = o["egim_seviye"]
    y1 = pc["yuk"]["pc1"]
    satir_sina(t, "En küçük varyans ($\\beta_{2y\\mid \\text{uzun}}$)",
               [sayi(v["beta_2y_5y"], 2), sayi(v["beta_2y_7y"], 2)], "hedge oranı")
    satir_sina(t, "Simetrik ($1/s_{\\text{TLS}}$)",
               [sayi(1 / v["tls_5y_2y"], 2), sayi(1 / v["tls_7y_2y"], 2)], "hedge oranı")
    satir_sina(t, "PCA seviye-nötr ($v_{1,2y}/v_{1,\\text{uzun}}$)",
               [sayi(y1["n2y"] / y1["n5y"], 2), sayi(y1["n2y"] / y1["n7y"], 2)], "hedge oranı")
    satir_sina(t, "Regresyon, kısa uca göre ($1/\\beta_{\\text{uzun}\\mid 2y}$)",
               [sayi(1 / v["beta_5y_2y"], 2), sayi(1 / v["beta_7y_2y"], 2)], "hedge oranı")
    for p in (sayi(v["beta_7y_2y"], 2), sayi(v["r2_7y_2y"], 2), sayi(v["corr_2y_2s7s"], 2)):
        metinde(m, p, "eğim–seviye")
    fm = o["faktor_maruziyet"]
    t = tablo(tl, "Yapı (10.000 TL/bp)")
    for k, s in (("2y_uzun", "2 yıllık kâğıt, uzun"), ("2s5s_yassi_dv01", "2s5s yassılaştırıcı, DV01-nötr"),
                 ("2s7s_yassi_dv01", "2s7s yassılaştırıcı, DV01-nötr"),
                 ("3a1y_dik_dv01", "3a1y dikleştirici, DV01-nötr"),
                 ):
        satir_sina(t, s, [sayi(x, 0, True) + " TL" for x in fm[k]], "faktör maruziyeti")
    t = tablo(tl, "Dönem | Ay | 2y–2s7s korelasyonu")
    for k, s in (("2013_2019", "2013–2019"), ("2020_2022", "2020–2022"), ("2023-07_2026", "Temmuz 2023 – 2026")):
        x = v["donem"][k]
        satir_sina(t, s, [str(x["n"]), sayi(x["corr_2y_2s7s"], 2), sayi(x["beta_7y_2y"], 2),
                          sayi(x["beta_5y_2y"], 2)], "beta dönemleri")
    ys = o["yapi_tasima"]
    t = tablo(tl, "Yapı (22.09.2026, DV01-nötr)")
    satir_sina(t, "2s5s yassılaştırıcı", [bp(ys["2s5s_yassilastirici_bp"])], "spread taşıması")
    satir_sina(t, "2s7s yassılaştırıcı", [bp(ys["2s7s_yassilastirici_bp"])], "spread taşıması")

    # 3.4 katalog
    kt = o["katalog"]
    t = tablo(tl, "Yapı | Aylık oynaklık | Yarı ömür | Seviye bileşeniyle korelasyon")
    for k, s in (("3a6a1y", "3a6a1y fly"), ("6a1y2y", "6a1y2y fly"), ("1y2y5y", "1y2y5y fly"),
                 ("2y3y5y", "2y3y5y fly"), ("2y5y7y", "2y5y7y fly"), ("3y5y7y", "3y5y7y fly"),
                 ("3a1y", "3a1y spread"), ("1y2y", "1y2y spread"), ("2y5y", "2s5s spread"),
                 ("2y7y", "2s7s spread"), ("5y7y", "5s7s spread")):
        x = kt[k]
        satir_sina(t, s, [bp(x["sigma_bp_ay"]), sayi(x["yari_omur_ay"], 1) + " ay",
                          sayi(x["korelasyon_seviye"], 2), bp(x["seviye"], True), sayi(x["yuzdelik"]),
                          sayi(x["donus_gurultu_3ay"], 2)], "katalog")
    satir_sina(t, "2 yıllık getiri", [None, sayi(kt["2y"]["yari_omur_ay"], 1) + " ay", None, None, None,
                                      sayi(kt["2y"]["donus_gurultu_3ay"], 2)], "katalog")
    metinde(m, f"PCA fly'da bu oran {sayi(kt['2y5y7y_pca']['donus_gurultu_3ay'], 2)}", "PCA fly oranı")

    # 3.5 ağırlıklar
    kl = o["kalicilik"]
    a, b_ = kl["agirlik_pca"]
    metinde(m, f"$a = {sayi(a, 3).replace(',', '{,}')}$, $b = {sayi(b_, 3).replace(',', '{,}')}$", "PCA ağırlığı")
    t = tablo(tl, "| 50:50 fly | PCA-nötr fly")
    satir_sina(t, "Aylık oynaklık", [bp(kl["seri"]["fly50"]["sigma_bp_ay"]), bp(kl["seri"]["flyPCA"]["sigma_bp_ay"])],
               "fly kıyası")
    satir_sina(t, "Yarı ömür", [sayi(kl["seri"]["fly50"]["yari_omur_ay"], 1) + " ay",
                                sayi(kl["seri"]["flyPCA"]["yari_omur_ay"], 1) + " ay"], "fly kıyası")
    for i, s in enumerate(("Seviye bileşeniyle korelasyon", "Eğim bileşeniyle korelasyon",
                           "Büküm bileşeniyle korelasyon")):
        satir_sina(t, s, [sayi(kl["fly50_korelasyon"][i], 2), sayi(kl["flyPCA_korelasyon"][i], 2)], "fly kıyası")
    t = tablo(tl, "Tahmin dönemi")
    for k, s in (("2013_2019", "2013–2019"), ("2020_2026", "2020–2026")):
        satir_sina(t, s, [sayi(kl["agirlik_donem"][k][0], 3), sayi(kl["agirlik_donem"][k][1], 3)], "ağırlık dönemleri")
    satir_sina(t, "Tümü (2013–2026)", [sayi(a, 3), sayi(b_, 3)], "ağırlık dönemleri")
    f1 = o["fly_1y2y5y"]
    t = tablo(tl, "Fly (22.09.2026)")
    satir_sina(t, "2y5y7y (gövde 5 yıl)",
               [f"{bp(yb['fly50']['seviye'], True)} · {sayi(yb['fly50']['yuzdelik'])}",
                f"{bp(yb['flyPCA']['seviye'], True)} · {sayi(yb['flyPCA']['yuzdelik'])}"], "iki hüküm")
    satir_sina(t, "1y2y5y (gövde 2 yıl)",
               [f"{bp(kt['1y2y5y']['seviye'], True)} · {sayi(kt['1y2y5y']['yuzdelik'])}",
                f"{bp(f1['seviye_bp'], True)} · {sayi(f1['yuzdelik'])}"], "iki hüküm")
    for p in (f"{sayi(f1['agirlik_pca'][0], 3)} · {sayi(f1['agirlik_pca'][1], 3)}", bp(f1["tasima_50_bp"], True),
              bp(f1["tasima_pca_bp"], True), sayi(f1["yari_omur_ay"], 1) + " ay", bp(f1["sigma_bp_ay"])):
        metinde(m, p, "1y2y5y")
    # fly taşıması long işaretiyle kontrol_w5'te (5.3, "Long 2y5y7y, ağırlık" tablosu)

    # 3.6 barbell
    bb = o["barbell"]
    t = tablo(tl, "| 2y (kanat) | 5y (bullet)")
    satir_sina(t, "Modifiye durasyon", [sayi(bb["mod_dur"]["2y"], 3), sayi(bb["mod_dur"]["5y"], 3),
                                        sayi(bb["mod_dur"]["7y"], 3), sayi(bb["mod_dur"]["5y"], 3)], "barbell")
    satir_sina(t, "Konveksite", [sayi(bb["konveksite"]["2y"], 2), sayi(bb["konveksite"]["5y"], 2),
                                 sayi(bb["konveksite"]["7y"], 2), sayi(bb["konv_barbell"], 2)], "barbell")
    satir_sina(t, "Üç aylık taşıma + roll", [None, yz(bb["cr_bullet"], arti=True), None,
                                             yz(bb["cr_barbell"], arti=True)], "barbell")
    metinde(m, f"Barbell ({yz(bb['agirlik_2y'] * 100, 1)} 2y + {yz(bb['agirlik_7y'] * 100, 1)} 7y)", "barbell ağırlığı")
    for p in (sayi(bb["konv_fark"], 2, True), yz(bb["konv_deger_3ay"], arti=True), yz(bb["cr_fark"], arti=True),
              bp(bb["kiris_fark_bp"]).replace("−", "−"), yz(bb["kiris_5y"])):
        metinde(m, p, "barbell")
    t = tablo(tl, "Ölçü | Barbell | Bullet | Fark")
    satir_sina(t, "İç verim (nakit akışlarını tek oranla iskonto eden oran)",
               [yz(bb["getiri_barbell_irr"]), yz(bb["getiri_bullet"]),
                bp((bb["getiri_barbell_irr"] - bb["getiri_bullet"]) * 100)], "iç verim")
    satir_sina(t, "Piyasa değeri ağırlıklı getiri (kısa ufukta tahakkukun ölçüsü)",
               [yz(bb["getiri_barbell_pd"]), yz(bb["getiri_bullet"]),
                bp((bb["getiri_barbell_pd"] - bb["getiri_bullet"]) * 100, True)], "iç verim")
    bk = o["barbell_kurallar"]
    t = tablo(tl, "Kural | Kanat nominalleri")
    for k, s in (("nakit", "Nakit + durasyon nötr"), ("5050", "50:50 DV01"), ("pca", "PCA-nötr")):
        x = bk[k]
        nakit = "0" if abs(x["net_nakit_mn"]) < 0.05 else f"{sayi(x['net_nakit_mn'], 1)} mn gerekir"
        fak = [("0" if abs(f) < 0.005 else sayi(f, 2, True) + " mn") for f in x["faktor_mn"]]
        satir_sina(t, s, [f"{sayi(x['kanat_nominal_mn'][0], 1)} · {sayi(x['kanat_nominal_mn'][1], 1)} mn", nakit,
                          f"{sayi(x['tasima_mn'], 2, True)} mn ({yz(x['tasima_yuzde'], arti=True)})",
                          sayi(x["konv_mn"], 2, True) + " mn"] + fak, "barbell kuralları")

    # 3.7 örneklem dışı sınama
    od = o["fly_orneklem_disi"]
    t = tablo(tl, "Sınama | Yapı | Sinyal | İsabet")
    for anahtar, kural, ilk in (("ayrismasiz", "pca", "Sinyal ve giriş aynı ay sonu gözleminden"),
                                ("ayrik", "pca", "Sinyal girişten beş iş günü önce, ağırlıklar bir önceki ay sonuna kadar"),
                                ("ayrik", "5050", "Sinyal girişten beş iş günü önce")):
        x = od[anahtar][kural]
        satir_sina(t, ilk, [None, str(x["n"]), yz(x["isabet_net"], 0), bp(x["net_ort"], True, 1),
                            bp(x["net_medyan"], True, 1), bp(x["yarilar"]["2016_2019"]["net_ort"], True, 1),
                            bp(x["yarilar"]["2020_2026"]["net_ort"], True, 1)], "örneklem dışı")
    for p in (bp(od["ayrik"]["pca"]["net_sd"], b=1), bp(od["ayrik"]["5050"]["net_sd"], b=1)):
        metinde(m, p, "örneklem dışı oynaklık")

    # 3.7 kalıcılık
    t = tablo(tl, "Yapı | Yarı ömür | Aylık oynaklık")
    for k, s in (("2y", "2 yıllık getiri"), ("5y", "5 yıllık getiri"), ("7y", "7 yıllık getiri"), ("2s7s", "2s7s"),
                 ("2s5s", "2s5s"), ("fly50", "2y5y7y fly (50:50)"), ("flyPCA", "2y5y7y fly (PCA-nötr)")):
        x = kl["seri"][k]
        satir_sina(t, s, [sayi(x["yari_omur_ay"], 1) + " ay", bp(x["sigma_bp_ay"])], "kalıcılık")
    # tarihli düzeltme kutuları
    fp = o["fly_pnl_ayrisimi"]["2y5y7y_50"]
    metinde(m, f"Aynı birimde fark {sayi(fp['sigma'])}'e karşı\n  {bp(o['kalicilik']['seri']['flyPCA']['sigma_bp_ay'])}'dir", "düzeltme kutusu")
    metinde(m, f"seviye payı %{sayi(fp['pay']['seviye'])},\n  büküm payı %{sayi(fp['pay']['bukum'])}'dir", "düzeltme kutusu")
    fb = o["fly_tasima_haritasi"]
    for k_ in ("n5y", "n7y"):
        metinde(m, sayi(fb["tasima_bp"]["n2y"] - fb["tasima_bp"][k_], 0), "düzeltme kutusu")
    metinde(m, f"taşıma {sayi(fb['tasima_bp']['n2y'] - fb['tasima_bp']['n5y'])} ve {sayi(fb['tasima_bp']['n2y'] - fb['tasima_bp']['n7y'])} bp, roll\n  {sayi(fb['roll_bp']['n2y'] - fb['roll_bp']['n5y'], 0, True)} ve {sayi(fb['roll_bp']['n2y'] - fb['roll_bp']['n7y'], 0, True)} bp",
            "düzeltme kutusu")
    # genişletme kontrolleri
    kontrol_w12(o, m, tl)
    kontrol_w3(o, m, tl)
    kontrol_w4(o, m, tl)
    kontrol_w5(o, m, tl)
    kontrol_w6(o, m, tl)
    kontrol_w7(o, m, tl)


# ─────────────────────────────────────────────────────────────── 4 · genişletme (yazarların kontrolleri)

# W12_dogrula
def kontrol_w12(o, m, tl):
    """Giriş, Bölüm 1 ve 2 eklemeleri."""
    # 1.2 kuponlu kâğıdın taşıması
    k = o["kuponlu_tasima"]
    t = tablo(tl, "Kuponlu 5 yıllık, 100 TL nominal başına (TL)")
    for ilk, anahtar in (("Kupon tahakkuku", "kupon_tahakkuku"), ("Fiyat çekimi", "fiyat_cekimi"),
                         ("Fonlama", "fonlama"), ("Taşıma", "tasima"), ("Roll", "roll"),
                         ("Taşıma + roll", "toplam")):
        satir_sina(t, ilk, [sayi(k["h30"][anahtar], 2), sayi(k["h91"][anahtar], 2)], "kuponlu taşıma")
    satir_sina(t, "Fiyatın %'si olarak", [yz(k["h30"]["toplam_yuzde"]), yz(k["h91"]["toplam_yuzde"])],
               "kuponlu taşıma")
    satir_sina(t, f"Başabaş (modifiye durasyon {sayi(k['mod_dur'], 2)})",
               [bp(k["h30"]["basabas_bp"]), bp(k["h91"]["basabas_bp"])], "kuponlu taşıma")
    bg = o["bugun"]
    for p in (f"(getiri {yz(k['getiri'])}, fiyat {sayi(k['fiyat'], 2)},",
              f"modifiye durasyon {sayi(k['mod_dur'], 2)};",
              f"(3 ayda {sayi(k['h91']['getiri_tahakkuku'], 2)} TL)",
              f"({yz(k['h91']['tasima_yuzde'])}: ikisi de",
              f"({yz(k['h91']['roll_yuzde'])}'e karşı {yz(bg['tasima']['5']['roll_yuzde'])}",
              f"{bp(k['h91']['basabas_bp'])}'ye\nkarşı sıfır kuponluda {bp(bg['tasima']['5']['basabas_bp'])}",
              f"({sayi(k['h30']['basabas_bp'])}'e karşı {bp(k['h91']['basabas_bp'])})",
              f"yaklaşık {sayi(k['h91']['basabas_bp'] / bg['tasima']['5']['basabas_bp'], 1)} kat"):
        metinde(m, p, "kuponlu taşıma")
    if abs(k["h91"]["tasima_yuzde"] - bg["tasima"]["5"]["tasima_yuzde"]) > 0.005:
        hatalar.append("kuponlu ve sıfır kuponlu 5 yıllığın yüzde taşıması artık aynı değil — metin 'aynıdır' diyor")
    # 1.2 düzeltilen örnek: 4,75 yıllık getiri ve forward
    tu = o["tasima_ufuk"]["h91"]["5"]
    metinde(m, f"4,75 yılın getirisi {yz(tu['getiri_Th'])}'tür", "5y örneği")
    metinde(m, f"4,75 yıllık getiri {yz(tu['forward'])}'un altında", "5y örneği")
    metinde(m, f"Son cümledeki {yz(tu['forward'])} kâğıdın", "5y örneği")

    # 1.3 ayrışma ve hep-kısa kıyası
    v = o["tasima_ayristirma"]["vade"]["n5y"]
    z = o["tasima_ayristirma"]["zamanlama"]["n5y"]
    for p in (f"ortalama {yz(v['toplam'])}'lik", f"{yz(v['tasima'])}'i taşıma", f"{yz(v['roll'])}'i\nroll",
              f"{yz(v['fiyat'])}'ü eğrinin", f"%{sayi(v['pay']['fiyat'])}'ü** hareketten",
              f"ortalama **{yz(z['zamanlama']['ort'], 1, True)}**", f"hep kısa durmak da {yz(z['hep_kisa']['ort'], 1, True)}**",
              f"ortalaması {yz(z['zamanlama']['yarilar']['2013_2019']['ort'], 1)}, hep kısanınki "
              f"{yz(z['hep_kisa']['yarilar']['2013_2019']['ort'], 1, True)}"):
        metinde(m, p, "1.3 ayrışma")

    # 1.7 (f) tümsek
    tm = o["tumsek"]
    for p in (f"ortalama **{sayi(tm['ort_sure_ay']['n2y'], 1)} ay**", f"**{tm['bugun_sure_ay']} aydır**",
              f"yalnız %{sayi(tm['roll_pozitif']['n2y'])}'ında", f"1 yıllığınki %{sayi(tm['roll_pozitif']['n1y'])}'sinde"):
        metinde(m, p, "tümsek")
    if tm["bugun"] != "n2y":
        hatalar.append(f"bugünkü tümsek tepesi artık 2 yıl değil: {tm['bugun']}")

    # 2.3 DV01 dili
    r1 = o["ois_roll_haritasi"]["1y"]
    a = o["temsili_ois"]["arac"]
    for p in (f"${sayi(a['toplam_mn'], 2).replace(',', '{,}').replace('−', '-')}\\ \\text{{mn}} / {sayi(a['dv01'])}$",
              f"≈ **{bp(r1['toplam_bp'])}**", f"fixing\ntaşıması {bp(r1['tasima_bp'])}, roll {bp(r1['roll_bp'])}",
              f"**{bp(-r1['toplam_bp'], True)}**'dir"):
        metinde(m, p, "OIS DV01 dili")

    # 2.5 kira × fixing
    kf = o["ois_kira_fixing"]
    t = tablo(tl, "Vade (receive'in fixing taşıması, DV01 başına)")
    for anahtar, ilk in (("3m", "3 ay"), ("6m", "6 ay"), ("1y", "1 yıl"), ("2y", "2 yıl"), ("5y", "5 yıl"),
                         ("10y", "10 yıl")):
        x = kf[anahtar]
        satir_sina(t, ilk, [yz(x["K"]), bp(x["temsili"], True), bp(x["politika"], True), bp(x["bugun"], True)],
                   "kira × fixing")
    for p in (f"{yz(kf['F_temsili'])}, {yz(kf['F_politika'])} ve {yz(kf['F_bugun'])}",):
        metinde(m, p, "kira × fixing")
    if not (kf["3m"]["temsili"] < 0 < kf["3m"]["politika"]):
        hatalar.append("3 aylık receive'in fixing taşıması artık işaret değiştirmiyor — metin 'işaret değiştirir' diyor")

    # 2.7 PPK günü oranı
    pg = o["ppk_gunu"]["vade"]
    lo = min(pg[k_]["oran"] for k_ in ("n3a", "n1y", "n2y"))
    hi = max(pg[k_]["oran"] for k_ in ("n3a", "n1y", "n2y"))
    metinde(m, f"{sayi(lo, 1)}–{sayi(hi, 1)} katıdır", "PPK günü oranı")


# W3_dogrula
def kontrol_w3(o, m, tl):
    def n0(x):
        return sayi(x, 0, True)

    def iddia(kosul, ad):
        """Metindeki nitel bir hükmün (işaret, sıralama, sayım) ölçümle tutarlılığı."""
        sayac["metin"] += 1
        if not kosul:
            hatalar.append(f"W3 hüküm ölçümle çelişiyor: {ad}")

    def gun(s):
        return f"{s[8:10]}.{s[5:7]}.{s[:4]}"

    bg = o["bugun"]
    tu = o["tasima_ufuk"]
    fh = o["fly_tasima_haritasi"]
    orh = o["ois_roll_haritasi"]
    to = o["tasima_oynaklik"]
    of = o["ois_fly"]
    oy = o["ois_yapilar"]
    ois = o["temsili_ois"]
    ta = o["tasima_ayristirma"]
    fg = o["forward_gerceklesme"]
    zm = ta["zamanlama"]
    st = o["tasima_stratejileri"]
    ff = o["fly_tasima_filtresi"]
    rj = o["rejim_yapi"]
    kf = o["ois_kira_fixing"]
    tm = o["tumsek"]
    fgc = o["fonlama_gecis"]
    V5 = (("n1y", "1 yıl"), ("n2y", "2 yıl"), ("n3y", "3 yıl"), ("n5y", "5 yıl"), ("n7y", "7 yıl"))
    DUG = ("n3a", "n6a", "n1y", "n2y", "n3y", "n5y", "n7y")

    # ───────────────────────── figürler ve genel çerçeve
    for s in ("04_tasima_haritasi", "05_getiri_ayrisimi", "06_tasima_kurallari", "07_fonlama_gecis"):
        metinde(m, f'src="/arastirma/kagit-ve-ois-trading/{s}.html"', "W3 figür")
    for p in (f"fixingi ({yz(bg['tlref'])} basit, bileşik karşılığı {yz(bg['tlref_etkin'])}; politika faizi "
              f"{yz(bg['politika'])}", f"fixing {yz(ois['tlref'])} (koridor tavanı rejimi)"):
        metinde(m, p, "W3 çıpalar")

    # ───────────────────────── 3.1 tanımlar, özdeşlik, beş enstrüman, üç örnek
    ta2, ta5 = bg["tasima"]["2"], bg["tasima"]["5"]
    t = tablo(tl, "Enstrüman ve taraf (taşıma + roll)")
    satir_sina(t, "Fonlanmış kâğıt, uzun",
               [None, None, f"2y {n0(ta2['basabas_bp'])} · 5y {n0(ta5['basabas_bp'])}", "—"], "W3 beş enstrüman")
    satir_sina(t, "OIS receive",
               [None, None, "—", f"2y {n0(orh['2y']['toplam_bp'])} · 5y {n0(orh['5y']['toplam_bp'])}"],
               "W3 beş enstrüman")
    satir_sina(t, "OIS pay",
               [None, None, "—", f"2y {n0(-orh['2y']['toplam_bp'])} · 5y {n0(-orh['5y']['toplam_bp'])}"],
               "W3 beş enstrüman")
    satir_sina(t, "DV01-nötr 2s5s dikleştirici",
               [None, None, n0(to["2y5y_diklestirici"]["tasima_bp"]), n0(oy["2y5y"]["toplam_bp"])],
               "W3 beş enstrüman")
    satir_sina(t, "Long 2y5y7y fly, 50:50",
               [None, None, n0(to["2y5y7y_long50"]["tasima_bp"]), n0(of["2y5y7y"]["5050"]["toplam_bp_govde"])],
               "W3 beş enstrüman")
    iddia(ta2["basabas_bp"] - ta5["basabas_bp"] == to["2y5y_diklestirici"]["tasima_bp"],
          "2s5s dikleştirici = be2y − be5y")

    h91, h30 = tu["h91"], tu["h30"]
    # özdeşlik sağlaması
    for k in ("2", "5"):
        metinde(m, f"{yz(h91[k]['forward'])}", "W3 özdeşlik forward")
        metinde(m, f"{yz(h91[k]['getiri_Th'])}", "W3 özdeşlik getiri")
    metinde(m, f"forward'ı {yz(h91['2']['forward'])}, kısalmış", "W3 özdeşlik 2y")
    metinde(m, f"5 yıllıkta {yz(h91['5']['forward'])} ile", "W3 özdeşlik 5y")
    metinde(m, f"{yz(h91['5']['getiri_Th'])}, fark {bp(h91['5']['basabas_bp'])}", "W3 özdeşlik 5y")
    iddia(round(h91["2"]["forward"] - h91["2"]["getiri_Th"], 2) * 100 == h91["2"]["basabas_bp"],
          "2y forward − getiri = başabaş")
    metinde(m, f"eğrinin 3 aylık getirisi {yz(bg['egri']['n3a'])}", "W3 fonlama ile 3 aylık getiri")
    sen = ois["senaryo"]["forward"]
    metinde(m, f"forward'lar gerçekleşirse {sayi(sen['toplam_mn'], 2, True)} mn", "W3 A senaryosu")
    metinde(m, f"eğri ve fixing sabitse {sayi(ois['arac']['toplam_mn'], 2, True)} mn TL", "W3 B senaryosu")
    orn = ois["ornek"]
    metinde(m, f"{sayi(orn['carry_tavan'], 2, True)} mn yerine {sayi(orn['carry_tavan_basit'], 2, True)} mn",
            "W3 basit fixing")

    # örnek 1 — 2 yıllık kâğıt
    metinde(m, f"Getiri {yz(ta2['getiri'])}, modifiye durasyon {sayi(ta2['mod_dur'], 2)}", "W3 örnek 1")
    metinde(m, f"Taşıma **{yz(ta2['tasima_yuzde'], arti=True)}**", "W3 örnek 1")
    metinde(m, f"**{yz(ta2['roll_yuzde'], arti=True)}**", "W3 örnek 1")
    metinde(m, f"**Toplam** {yz(ta2['toplam_yuzde'], arti=True)}", "W3 örnek 1")
    metinde(m, f"**{bp(ta2['basabas_bp'])}**; forward", "W3 örnek 1")
    metinde(m, f"eğrinin o noktası bugün {yz(h91['2']['getiri_Th'])}", "W3 örnek 1")
    metinde(m, "= \\" + f"{yz(h91['2']['forward'])}$", "W3 örnek 1 forward")
    metinde(m, f"taşıma {bp(fh['tasima_bp']['n2y'], True)}, roll {bp(fh['roll_bp']['n2y'], True)}", "W3 örnek 1 DV01")

    # örnek 2 — temsili OIS receive
    ar = ois["arac"]
    metinde(m, "= \\" + f"{yz(orn['F_tavan'])}$", "W3 örnek 2 F")
    metinde(m, f"**{sayi(ar['tasima_mn'], 2, True)} mn TL**", "W3 örnek 2 taşıma")
    metinde(m, f"**{sayi(ar['roll_mn'], 2, True)} mn TL**", "W3 örnek 2 roll")
    metinde(m, f"**Toplam** {sayi(ar['toplam_mn'], 2, True)} mn TL", "W3 örnek 2 toplam")
    metinde(m, f"kotasyonu {yz(ar['S_Th'])}, annüitesi {sayi(ar['A_Th'], 4)}", "W3 örnek 2 roll girdisi")
    metinde(m, f"{sayi(ar['A_T'], 4)} \\times 500", "W3 örnek 2 annüite")
    metinde(m, f"= {sayi(ar['dv01'])}$", "W3 örnek 2 DV01")
    o1y = orh["1y"]
    metinde(m, f"**{bp(o1y['toplam_bp'], True)}** (taşıma {bp(o1y['tasima_bp'], True)}, roll {bp(o1y['roll_bp'], True)})",
            "W3 örnek 2 DV01 başına")
    iddia(round(ar["toplam_mn"] * 1e6 / ar["dv01"]) == o1y["toplam_bp"], "örnek 2: toplam / DV01 = −282")
    metinde(m, f"Günlük kira ≈ {n0(round(ar['toplam_mn'] * 1e3 / 92))} bin TL", "W3 örnek 2 günlük")
    metinde(m, f"(taşıma {n0(ar['gunluk_bin'])} bin, roll ≈ {n0(round(ar['roll_mn'] * 1e3 / 92))} bin)", "W3 örnek 2 günlük")
    metinde(m, f"kotasyon {yz(ar['basabas'])}'ya inmelidir", "W3 örnek 2 başabaş")
    metinde(m, f"forward'ı ({yz(ois['bootstrap']['forward_3m_9m'])})", "W3 örnek 2 forward")
    metinde(m, f"aradaki {sayi(ois['basabas_forward']['fark_bp'])} bp", "W3 örnek 2 fark")
    metinde(m, f"çeyrekte {sayi(-ar['toplam_mn'], 2, True)} mn TL toplar", "W3 örnek 2 pay")

    # örnek 3 — long 2y5y7y
    be = fh["basabas_bp"]
    f50, fpc = fh["fly"]["2y5y7y_50"], fh["fly"]["2y5y7y_pca"]
    metinde(m, f"2y {n0(be['n2y'])} bp, 5y {n0(be['n5y'])} bp, 7y {n0(be['n7y'])} bp", "W3 örnek 3 bacaklar")
    metinde(m, (f"-\\big({sayi(be['n5y'], 0)} - 0,5 \\times ({sayi(be['n2y'], 0)}) - 0,5 \\times "
                f"({sayi(be['n7y'], 0)})\\big)").replace("−", "-"), "W3 örnek 3 formül")
    metinde(m, f"gövde DV01'i başına **{bp(f50['tasima_long_bp'], True)}**", "W3 örnek 3 50:50")
    metinde(m, f"{bp(o['yapi_tasima']['fly50_long_bp_fly'], True)}); PCA", "W3 örnek 3 kotasyon")
    metinde(m, f"$a = {sayi(fpc['a'], 3)}$", "W3 örnek 3 PCA")
    metinde(m, f"$b = {sayi(fpc['b'], 3)}$) **{bp(fpc['tasima_long_bp'], True)}**", "W3 örnek 3 PCA")
    tb, rb = fh["tasima_bp"], fh["roll_bp"]
    metinde(m, f"2y {n0(tb['n2y'])} · 5y {n0(tb['n5y'])} · 7y {n0(tb['n7y'])} bp", "W3 örnek 3 düğüm taşıması")
    metinde(m, f"roll 2y {n0(rb['n2y'])} · 5y {n0(rb['n5y'])} · 7y {n0(rb['n7y'])} bp", "W3 örnek 3 düğüm roll'u")
    metinde(m, f"**{bp(f50['tasima_parca_bp'], True)}**. Üç bacak", "W3 örnek 3 taşıma parçası")
    metinde(m, f"**{bp(f50['roll_parca_bp'], True)}**. Gövde", "W3 örnek 3 roll parçası")
    metinde(m, f"taşıma parçası {sayi(fpc['tasima_parca_bp'], 0)}, roll parçası {bp(fpc['roll_parca_bp'], True)}",
            "W3 örnek 3 PCA parçaları")
    iddia(abs(f50["roll_parca_bp"]) > 10 * abs(f50["tasima_parca_bp"]), "long 2y5y7y taşıması neredeyse tamamen roll")

    # ───────────────────────── 3.2 roll haritası ve tümsek
    t = tablo(tl, "Vade (kâğıt, 1 ay · 3 ay)")
    for k, s in (("0.5", "6 ay"), ("1", "1 yıl"), ("2", "2 yıl"), ("3", "3 yıl"), ("5", "5 yıl"), ("7", "7 yıl")):
        a, b = h30[k], h91[k]
        satir_sina(t, s, [f"{yz(a['tasima'], arti=True)} · {yz(b['tasima'], arti=True)}",
                          f"{yz(a['roll'], arti=True)} · {yz(b['roll'], arti=True)}",
                          f"{n0(a['basabas_bp'])} · {n0(b['basabas_bp'])}",
                          f"{yz(a['getiri_Th'])} · {yz(b['getiri_Th'])}",
                          f"{yz(a['forward'])} · {yz(b['forward'])}"], "W3 ufuk tablosu")
        iddia(abs(a["getiri_Th"] + a["basabas_bp"] / 100 - a["forward"]) <= 0.015 and
              abs(b["getiri_Th"] + b["basabas_bp"] / 100 - b["forward"]) <= 0.015, f"özdeşlik satırı {s}")
    for k, ad in (("5", "5 yılda"), ("2", "2 yılda")):
        metinde(m, f"{ad} {sayi(h91[k]['basabas_bp'] / h30[k]['basabas_bp'], 1)} katı", "W3 ufuk oranı")
    metinde(m, f"{sayi(h91['1']['basabas_bp'] / h30['1']['basabas_bp'], 1)} katı** ({bp(h30['1']['basabas_bp'])}'ye karşı "
               f"{bp(h91['1']['basabas_bp'])})", "W3 ufuk oranı 1y")
    metinde(m, f"{sayi(h91['1']['tasima'] / h30['1']['tasima'], 1)} kat büyür", "W3 1y taşıma oranı")
    metinde(m, f"({yz(h30['1']['tasima'], arti=True)}'den {yz(h91['1']['tasima'], arti=True)}'ya)", "W3 1y taşıma")
    metinde(m, f"roll yalnız {sayi(h91['1']['roll'] / h30['1']['roll'], 1)} kat", "W3 1y roll oranı")
    metinde(m, f"({yz(h30['1']['roll'], arti=True)}'den {yz(h91['1']['roll'], arti=True)}'e)", "W3 1y roll")
    iddia(h91["1"]["roll"] > 0 and h91["2"]["roll"] > 0 and h91["0.5"]["roll"] < 0 and
          all(h91[k]["roll"] < 0 for k in ("3", "5", "7")), "roll işaretleri: 1–2 yıl artı, 6 ay ve 3 yıl+ eksi")
    eg = bg["egri"]
    for k, ad in (("n3a", "3 ayda"), ("n6a", "6 ayda"), ("n1y", "1 yılda"), ("n2y", "2 yılda"), ("n5y", "5 yılda"),
                  ("n7y", "7 yılda")):
        metinde(m, f"{ad} {yz(eg[k])}", "W3 bugünkü eğri")
    metinde(m, yz(eg["n3y"]), "W3 bugünkü eğri 3y")
    iddia(max(eg, key=eg.get) == "n2y" == tm["bugun"], "tepe 2 yılda")
    t = tablo(tl, "Düğüm (tümsek ölçüleri, 2013–2026)")
    for k, s in (("n3a", "3 ay"), ("n6a", "6 ay"), ("n1y", "1 yıl"), ("n2y", "2 yıl"), ("n3y", "3 yıl"),
                 ("n5y", "5 yıl"), ("n7y", "7 yıl")):
        rp = yz(tm["roll_pozitif"][k], 0) if k in tm["roll_pozitif"] else "—"
        satir_sina(t, s, [yz(tm["pay"][k], 0), yz(tm["pay_son36"][k], 0), sayi(tm["ort_sure_ay"][k], 1), rp],
                   "W3 tümsek")
    metinde(m, f"({tm['n']} ay sonu", "W3 tümsek n")
    metinde(m, f"{ta['n_pencere']} üst üste binen üç aylık pencereden", "W3 tümsek pencere")
    metinde(m, f"%{sayi(tm['pay']['n3a'])}'inde 3 ayda", "W3 tümsek okuma")
    metinde(m, f"%{sayi(tm['pay']['n7y'])}'sında 7", "W3 tümsek okuma")
    metinde(m, f"ayların yalnız %{sayi(tm['pay']['n2y'])}'unda", "W3 tümsek okuma")
    iddia(all(tm["pay_son36"][k] == 0 for k in ("n3y", "n5y", "n7y")), "son 36 ayda tepe 2 yılın ötesinde değil")
    metinde(m, f"ayların %{sayi(tm['pay_son36']['n3a'])}'inde 3 aydaydı", "W3 tümsek son 36")
    metinde(m, f"2 yıllık tepe ortalama {sayi(tm['ort_sure_ay']['n2y'], 1)} ay yerinde kaldı", "W3 tümsek süre")
    metinde(m, f"tepe {tm['bugun_sure_ay']} aydır yerinde", "W3 tümsek bugün")
    metinde(m, f"(7 yılda {sayi(tm['ort_sure_ay']['n7y'], 1)} ay)", "W3 tümsek 7y")
    metinde(m, f"1 yılda %{sayi(tm['roll_pozitif']['n1y'])}, 2 yılda %{sayi(tm['roll_pozitif']['n2y'])}",
            "W3 roll payı")
    rp37 = [tm["roll_pozitif"][k] for k in ("n3y", "n5y", "n7y")]
    metinde(m, f"3–7 yılda %{sayi(min(rp37))}–{sayi(max(rp37))}", "W3 roll payı")
    metinde(m, f"ortalama {sayi(tm['ort_sure_ay']['n2y'], 1)} ay yaşamış", "W3 roll-down bahsi")

    t = tablo(tl, "Vade (temsili OIS receive, 3 ay)")
    for k, s in (("6m", "6 ay"), ("9m", "9 ay"), ("1y", "1 yıl"), ("18m", "18 ay"), ("2y", "2 yıl"), ("3y", "3 yıl"),
                 ("4y", "4 yıl"), ("5y", "5 yıl"), ("7y", "7 yıl"), ("10y", "10 yıl")):
        x = orh[k]
        satir_sina(t, s, [yz(x["K"]), yz(x["S_Th"]), sayi(x["dv01"]), n0(x["tasima_bp"]), n0(x["roll_bp"]),
                          n0(x["toplam_bp"])], "W3 OIS roll haritası")
    iddia(all(x["tasima_bp"] < 0 and x["roll_bp"] < 0 and x["S_Th"] > x["K"] for x in orh.values()),
          "receive her vadede iki bileşeni de öder")
    iddia(min(orh, key=lambda v: orh[v]["roll_bp"]) == "18m", "roll 18 ayda en ağır")
    iddia(min(orh, key=lambda v: orh[v]["tasima_bp"]) == "6m", "taşıma 6 ayda en ağır")
    metinde(m, f"(6 ayda {bp(orh['6m']['tasima_bp'])})", "W3 OIS harita")
    metinde(m, f"Roll 18 ayda en ağırdır ({n0(orh['18m']['roll_bp'])}", "W3 OIS harita")
    metinde(m, f"6 ayda {bp(-orh['6m']['toplam_bp'], True)}, 10 yılda {bp(-orh['10y']['toplam_bp'], True)}",
            "W3 OIS pay")
    metinde(m, f"roll DV01 başına {bp(rb['n2y'], True)} (tümsek)", "W3 iki harita")
    metinde(m, f"OIS'te {bp(orh['2y']['roll_bp'])}. Aynı vade", "W3 iki harita")

    # ───────────────────────── 3.3 DV01 ve oynaklık başına
    t = tablo(tl, "Yapı ve yön (kâğıt, 22.09.2026)")
    YO = [("1 yıl receive", "1y_receive"), ("2 yıl receive", "2y_receive"), ("3 yıl receive", "3y_receive"),
          ("5 yıl receive", "5y_receive"), ("7 yıl receive", "7y_receive"),
          ("1y2y dikleştirici", "1y2y_diklestirici"), ("2s5s dikleştirici", "2y5y_diklestirici"),
          ("2s7s dikleştirici", "2y7y_diklestirici"), ("5s7s dikleştirici", "5y7y_diklestirici")]
    for f in ("1y2y3y", "1y2y5y", "2y3y5y", "2y5y7y", "3y5y7y"):
        YO += [(f"Long {f} 50:50", f"{f}_long50"), (f"Long {f} PCA", f"{f}_longpca")]
    for s, k in YO:
        x = to[k]
        satir_sina(t, s, [n0(x["tasima_bp"]), sayi(x["sigma36_bp_ay"]), sayi(x["oran"], 2, True)], "W3 taşıma/oynaklık")
    metinde(m, f"5 yılda pay\n{bp(-to['5y_receive']['tasima_bp'], True)}", "W3 karşı yön")
    metinde(m, f"kâğıtta gövdeyi al — {bp(-to['1y2y5y_longpca']['tasima_bp'], True)}", "W3 karşı yön")
    metinde(m, f"2s5s {bp(to['2y5y_diklestirici']['tasima_bp'], True)}, 2s7s {bp(to['2y7y_diklestirici']['tasima_bp'], True)}",
            "W3 bugün taşıyanlar")
    iddia(all(to[f"{f}_long{w}"]["tasima_bp"] > 0 for f in ("2y5y7y", "2y3y5y", "3y5y7y") for w in ("50", "pca")) and
          all(to[f"{f}_long{w}"]["tasima_bp"] < 0 for f in ("1y2y3y", "1y2y5y") for w in ("50", "pca")) and
          all(to[f"{v}_receive"]["tasima_bp"] < 0 for v in ("1y", "2y", "3y", "5y", "7y")),
          "taşıyan/ödeyen yapı listesi")
    metinde(m, f"receive'de {sayi(to['1y_receive']['oran'], 2)} ve {sayi(to['2y_receive']['oran'], 2)}",
            "W3 oran 1–2 yıl")
    metinde(m, f"receive'de {sayi(to['5y_receive']['oran'], 2)} ve {sayi(to['7y_receive']['oran'], 2)}",
            "W3 oran 5–7 yıl")
    fo = [abs(x["oran"]) for k, x in to.items() if k != "gun" and "_long" in k]
    metinde(m, f"fly'larda {sayi(min(fo), 2)}–{sayi(max(fo), 2)}", "W3 fly oran aralığı")
    metinde(m, f"fly'larda olduğu gibi {sayi(min(fo), 2)}–{sayi(max(fo), 2)}", "W3 masada oran aralığı")
    iddia(all(min(fo) <= abs(to[k]["oran"]) <= max(fo) for k in ("5y_receive", "7y_receive")), "5–7 yıl oranı aralıkta")
    metinde(m, f"ortalama {yz(zm['n2y']['hep_uzun']['ort'], 1, True)} (t {sayi(zm['n2y']['hep_uzun']['t'], 1)})",
            "W3 outright trendi")
    hl = ff["2y5y7y"]["hep_long"]
    metinde(m, f"çeyrekte ortalama {bp(hl['ort'], True, 1)}, t {sayi(hl['t'], 1)}", "W3 fly yönsüz")

    t = tablo(tl, "Yapı (iki eğride taşıma + roll, 3 ay)")
    IK = [("Long 2y5y7y 50:50", "2y5y7y_long50", "2y5y7y", "5050"), ("Long 2y5y7y PCA", "2y5y7y_longpca", "2y5y7y", "pca"),
          ("Long 1y2y5y 50:50", "1y2y5y_long50", "1y2y5y", "5050"), ("Long 1y2y5y PCA", "1y2y5y_longpca", "1y2y5y", "pca")]
    for s, k, f, w in IK:
        satir_sina(t, s, [n0(to[k]["tasima_bp"]), n0(of[f][w]["toplam_bp_govde"]), n0(of[f][w]["toplam_bugun_bp_govde"])],
                   "W3 iki eğri")
        iddia((to[k]["tasima_bp"] > 0) != (of[f][w]["toplam_bp_govde"] > 0) and
              (of[f][w]["toplam_bp_govde"] > 0) == (of[f][w]["toplam_bugun_bp_govde"] > 0),
              f"{s}: işaret iki eğride ters, fixing %36,49'da da aynı")
    satir_sina(t, "1y2y dikleştirici", [n0(to["1y2y_diklestirici"]["tasima_bp"]), n0(oy["1y2y"]["toplam_bp"]), "—"],
               "W3 iki eğri")
    satir_sina(t, "2s5s dikleştirici", [n0(to["2y5y_diklestirici"]["tasima_bp"]), n0(oy["2y5y"]["toplam_bp"]), "—"],
               "W3 iki eğri")
    satir_sina(t, "2s10s dikleştirici", ["—", n0(oy["2y10y"]["toplam_bp"]), "—"], "W3 iki eğri")
    iddia((to["1y2y_diklestirici"]["tasima_bp"] > 0) != (oy["1y2y"]["toplam_bp"] > 0) and
          (to["2y5y_diklestirici"]["tasima_bp"] > 0) != (oy["2y5y"]["toplam_bp"] > 0), "spread'lerde işaret ters")
    iddia(oy["2y10y"]["toplam_bp"] < oy["2y5y"]["toplam_bp"], "2s10s 2s5s'ten ağır öder")
    L = of["2y5y7y"]["5050"]
    for b_, yon_ in (("2y", "receive"), ("5y", "pay"), ("7y", "receive")):
        metinde(m, f"{yon_} taşıma {sayi(L['tasima_bin'][b_], 0, True)} · roll {sayi(L['roll_bin'][b_], 0, True)}",
                "W3 OIS fly bacakları")
    metinde(m, f"toplam taşıma {sayi(L['tasima_mn'], 2, True)} mn, roll {sayi(L['roll_mn'], 2, True)} mn TL",
            "W3 OIS fly bacakları")
    metinde(m, f"net {sayi(-L['net_yuzen_mn'], 0)} mn TL TLREF öder (3.7)", "W3 net yüzen")
    metinde(m, f"dönmüyor ({bp(L['toplam_bugun_bp_govde'], True)})", "W3 fixing %36,49")
    metinde(m, f"2 yıllık roll {bp(rb['n2y'], True)}.", "W3 eğrinin şekli")
    metinde(m, f"2 yıllık roll {bp(orh['2y']['roll_bp'])}. 2 yıl", "W3 eğrinin şekli")

    # ───────────────────────── 3.4 ayrışma
    metinde(m, f"({ta['ilk']} – {ta['son']} arası {ta['n_pencere']} ay sonu", "W3 pencere tanımı")
    t = tablo(tl, "Vade (uzun kâğıt, 162 pencere, 3 ay)")
    for k, s in V5:
        v = ta["vade"][k]
        satir_sina(t, s, [yz(v["tasima"], arti=True), yz(v["roll"], arti=True), yz(v["fiyat"], arti=True),
                          yz(v["toplam"], arti=True), yz(v["sd"]["toplam"]), yz(v["pay"]["fiyat"], 0),
                          yz(v["pozitif"], 0)], "W3 ayrışma")
    metinde(m, f"Vade (uzun kâğıt, {ta['n_pencere']} pencere", "W3 ayrışma n")
    V = ta["vade"]
    metinde(m, f"1 yılda {yz(V['n1y']['pay']['fiyat'], 0)}, 5 yılda {yz(V['n5y']['pay']['fiyat'], 0)}", "W3 varyans payı")
    metinde(m, f"yılda {yz(V['n7y']['pay']['fiyat'], 0)}; taşımanın payı 1 yılda {yz(V['n1y']['pay']['tasima'], 0)}, "
               f"5 yılda {yz(V['n5y']['pay']['tasima'], 0)}", "W3 varyans payı")
    metinde(m, f"taşıma {yz(V['n5y']['tasima'], arti=True)} ve roll {yz(V['n5y']['roll'], arti=True)}, hareket "
               f"{yz(V['n5y']['fiyat'], arti=True)}", "W3 ortalama")
    iddia((V["n5y"]["tasima"] + V["n5y"]["roll"]) / V["n5y"]["toplam"] > 0.5, "5y kaybın yarısından fazlası kira")
    t = tablo(tl, "Dönem (5 yıllık kâğıt, 3 ay)")
    D = ta["donem"]
    for k, s in (("2013_2019", "2013–2019"), ("2020_2022", "2020–2022"), ("2023_2026", "2023–2026")):
        x = D[k]["n5y"]
        satir_sina(t, s, [str(D[k]["n"]), yz(x["tasima"], arti=True), yz(x["roll"], arti=True), yz(x["fiyat"], arti=True),
                          yz(x["toplam"], arti=True), yz(x["tasima_pozitif"], 0), yz(x["fon_surpriz"], arti=True)],
                   "W3 üç dönem")
    metinde(m, f"taşıma {yz(D['2020_2022']['n2y']['tasima'], arti=True)} ve {yz(D['2020_2022']['n7y']['tasima'], arti=True)}",
            "W3 üç dönem 2y/7y")
    metinde(m, f"2023–2026'da {yz(D['2023_2026']['n2y']['tasima'], arti=True)} ve", "W3 üç dönem 2y")
    metinde(m, yz(D["2023_2026"]["n7y"]["tasima"], arti=True), "W3 üç dönem 7y")
    metinde(m, f"yalnız {yz(D['2023_2026']['n5y']['tasima_pozitif'], 0)}'sinde artı", "W3 taşıma artı payı")
    kira = D["2023_2026"]["n5y"]["tasima"] + D["2023_2026"]["n5y"]["roll"]
    metinde(m, f"kira {yz(kira, arti=True)} (taşıma + roll)", "W3 2023–2026 kira")
    metinde(m, f"çeyrekte\n   {yz(V['n5y']['fon_surpriz'], arti=True)}, en pahalı dönemde "
               f"{yz(D['2023_2026']['n5y']['fon_surpriz'], arti=True)}", "W3 fonlama sürprizi")
    iddia(all(V[k]["fon_surpriz"] == V["n5y"]["fon_surpriz"] for k, _ in V5), "fonlama sürprizi vadeden bağımsız")
    F = ta["faz"]
    metinde(m, f"162 pencerenin {sum(F[f]['n'] for f in ('indirim', 'sabit', 'artırım'))}'sı", "W3 faz kapsamı")
    t = tablo(tl, "PPK fazı (penceredeki kararlar, 3 ay)")
    for f, s in (("indirim", "İndirim fazı"), ("sabit", "Sabit faz"), ("artırım", "Artırım fazı")):
        x = F[f]
        satir_sina(t, s, [str(x["n"]), yz(x["n5y"]["tasima"], arti=True), yz(x["n5y"]["roll"], arti=True),
                          yz(x["n5y"]["fiyat"], arti=True), yz(x["n5y"]["toplam"], arti=True),
                          yz(x["n2y"]["toplam"], arti=True), yz(x["n7y"]["toplam"], arti=True)], "W3 PPK fazı")
    kr = {f: F[f]["n5y"]["tasima"] + F[f]["n5y"]["roll"] for f in F if f != "n" and isinstance(F[f], dict)}
    metinde(m, f"indirimde {yz(kr['indirim'], arti=True)}", "W3 faz kirası")
    metinde(m, yz(kr["sabit"], arti=True), "W3 faz kirası")
    metinde(m, f"artırımda {yz(kr['artırım'], arti=True)}", "W3 faz kirası")
    iddia(-kr["sabit"] / -F["sabit"]["n5y"]["toplam"] > 0.75, "sabit fazda kaybın dörtte üçünden fazlası kira")
    iddia(0.4 < -kr["indirim"] / F["indirim"]["n5y"]["fiyat"] < 0.5, "indirimde kira hareketin yarısına yakın")

    # ───────────────────────── 3.5 forward'lar
    t = tablo(tl, "Vade (forward'ın gerçekleşmesi, 162 pencere)")
    for k, s in V5:
        x = fg[k]
        satir_sina(t, s, [sayi(x["beta"], 2, True), sayi(x["t0"], 1, True), sayi(x["t1"], 1, True), sayi(x["r2"], 2),
                          n0(x["fd_ort"]), n0(x["dy_ort"]), sayi(x["yarilar"]["2013_2019"], 2, True),
                          sayi(x["yarilar"]["2020_2026"], 2, True)], "W3 forward gerçekleşmesi")
    iddia(all(abs(fg[k]["t0"]) < 2 for k, _ in V5), "β sıfırdan ayırt edilemiyor")
    iddia(sum(fg[k]["t1"] <= -2 for k, _ in V5) == 4 and -2 < fg["n7y"]["t1"] < 0, "β = 1 dört vadede reddediliyor")
    t0s = [fg[k]["t0"] for k, _ in V5]
    metinde(m, f"t'ler {sayi(min(t0s), 1)} ile {sayi(max(t0s), 1)} arasında", "W3 β t")
    t1s = [fg[k]["t1"] for k, _ in V5 if fg[k]["t1"] <= -2]
    metinde(m, f"(t {sayi(max(t1s), 1)} …\n   {sayi(min(t1s), 1)}), 7 yılda t {sayi(fg['n7y']['t1'], 1)}", "W3 β = 1")
    dy = [fg[k]["dy_ort"] for k, _ in V5]
    fd = [fg[k]["fd_ort"] for k, _ in V5]
    metinde(m, f"{n0(min(dy))} ile {n0(max(dy))} bp arasında, forward'ın ima ettiği {n0(min(fd))} ile {n0(max(fd))} bp",
            "W3 trend")
    iddia(all(fg[k]["dy_ort"] > 0 for k, _ in V5), "gerçekleşen değişim her vadede artı")
    metinde(m, f"(5 yılda {sayi(fg['n5y']['yarilar']['2013_2019'], 2)}, 7 yılda {sayi(fg['n7y']['yarilar']['2013_2019'], 2)})",
            "W3 β ilk yarı")
    y2 = [fg[k]["yarilar"]["2020_2026"] for k, _ in V5]
    metinde(m, f"({sayi(min(y2), 2, True)} ile {sayi(max(y2), 2, True)} arası)", "W3 β ikinci yarı")
    du = o["durasyon"]
    metinde(m, f"yılda $b$ {sayi(du['2y']['egim'], 2)} iken $1 - \\beta$ {sayi(1 - fg['n2y']['beta'], 2)}", "W3 b ≈ 1 − β")
    iddia(sayi(du["5y"]["egim"], 2) == sayi(1 - fg["n5y"]["beta"], 2), "5y: b = 1 − β")
    metinde(m, f"5 yılda ikisi de {sayi(du['5y']['egim'], 2)}", "W3 b ≈ 1 − β")
    metinde(m, f"7 yılda {sayi(du['7y']['egim'], 2)}'ye karşı {sayi(1 - fg['n7y']['beta'], 2)}", "W3 b ≈ 1 − β")
    metinde(m, f"β {sayi(fg['n5y']['yarilar']['2013_2019'], 2)} iken 1.3'teki", "W3 yarılar aynası")
    metinde(m, f"eğim {sayi(du['5y']['yarilar']['2013_2019'], 2)}.", "W3 yarılar aynası")

    # ───────────────────────── 3.6 kurallar
    t = tablo(tl, "Vade (taşıma işaretiyle zamanlama")
    for k, s in V5:
        Z, K, U = zm[k]["zamanlama"], zm[k]["hep_kisa"], zm[k]["hep_uzun"]
        satir_sina(t, s, [f"{yz(Z['ort'], 1, True)} · {sayi(Z['t'], 1, True)}",
                          f"{yz(K['ort'], 1, True)} · {sayi(K['t'], 1, True)}",
                          yz(U["ort"], 1, True),
                          f"{yz(Z['yarilar']['2013_2019']['ort'], 1, True)} · {yz(Z['yarilar']['2020_2026']['ort'], 1, True)}",
                          f"{yz(K['yarilar']['2013_2019']['ort'], 1, True)} · {yz(K['yarilar']['2020_2026']['ort'], 1, True)}",
                          " · ".join(sayi(zm[k]["gecikme"][g], 1, True) for g in ("1", "5", "10", "21"))],
                   "W3 zamanlama")
    zt = [zm[k]["zamanlama"]["t"] for k, _ in V5]
    metinde(m, f"t {sayi(min(zt), 1)}–{sayi(max(zt), 1)}", "W3 zamanlama t")
    iddia(all(zm[k]["zamanlama"]["ort"] > 0 for k, _ in V5), "zamanlama her vadede artı")
    metinde(m, f"5 yılda ikisi de {yz(zm['n5y']['zamanlama']['ort'], 1, True)}", "W3 zamanlama ≈ hep kısa")
    metinde(m, f"2 yılda {yz(zm['n2y']['zamanlama']['ort'], 1, True)}'ya karşı {yz(zm['n2y']['hep_kisa']['ort'], 1, True)}",
            "W3 zamanlama ≈ hep kısa")
    metinde(m, f"İsabet 2\n  yılda zamanlamada {yz(zm['n2y']['zamanlama']['isabet'], 0)}, hep kısada "
               f"{yz(zm['n2y']['hep_kisa']['isabet'], 0)}", "W3 isabet")
    bpz = [V[k]["be_pozitif"] for k, _ in V5]
    metinde(m, f"{yz(min(bpz), 0)}–{sayi(max(bpz), 0)}", "W3 sinyal artı payı")
    z5 = zm["n5y"]
    metinde(m, f"5 yılda {yz(z5['arti']['ort'], 2, True)} ({z5['arti']['n']} pencere)", "W3 sinyal artı")
    metinde(m, f"eksiyken {yz(z5['eksi']['ort'], 2, True)} kaybetti ({z5['eksi']['n']} pencere)", "W3 sinyal eksi")
    d5 = o["durasyon"]["5y"]
    iddia(abs(d5["cr_pozitif"]["ort"] - z5["arti"]["ort"]) < 0.005 and abs(d5["cr_negatif"]["ort"] - z5["eksi"]["ort"]) < 0.005,
          "zamanlama kolları 1.3 tablosuyla aynı")
    geri = [k for k, _ in V5 if zm[k]["zamanlama"]["yarilar"]["2013_2019"]["ort"] < zm[k]["hep_kisa"]["yarilar"]["2013_2019"]["ort"]]
    ileri = [k for k, _ in V5 if zm[k]["zamanlama"]["yarilar"]["2020_2026"]["ort"] > zm[k]["hep_kisa"]["yarilar"]["2020_2026"]["ort"]]
    iddia(len(geri) == 4 and "n3y" not in geri and len(ileri) == 5, "zamanlama yarılarda: ilk yarıda 4/5 geride, ikinci 5/5 önde")
    g5 = [zm["n5y"]["gecikme"][g] for g in ("1", "5", "10", "21")]
    metinde(m, f"{yz(min(g5), 1, True)} ile {yz(max(g5), 1, True)} arasında", "W3 gecikme 5y")

    eu, es_ = st["en_iyi_uzun"], st["esit_uzun"]
    metinde(m, f"{st['n']} pencere", "W3 strateji kapsamı")
    metinde(m, f"{st['ilk'][:4]}–{st['son'][:4]}). Sonuç", "W3 strateji kapsamı")
    metinde(m, f"{bp(eu['ort'], True, 1)} (medyan {bp(eu['medyan'], True, 1)}, isabet {yz(eu['isabet'], 0)})", "W3 en iyi uzun")
    metinde(m, f"2015–2019'da {sayi(eu['yarilar']['2013_2019']['ort'], 1, True)}, 2020–2026'da\n"
               f"{bp(eu['yarilar']['2020_2026']['ort'], True, 1)}", "W3 en iyi uzun yarılar")
    iddia(eu["yarilar"]["2013_2019"]["ort"] < 0 and eu["yarilar"]["2020_2026"]["ort"] < 0, "en iyi uzun iki yarıda eksi")
    metinde(m, f"{bp(es_['ort'], True, 1)} kaybettirdi", "W3 eşit uzun")
    metinde(m, f"yaklaşık {sayi(round((eu['ort'] - es_['ort']) / 10) * 10)} bp iyileştirdi", "W3 seçim farkı")
    t = tablo(tl, "Eğri kuralı (DV01 başına bp, 3 ay, 2015–2026)")
    for s, k in (("Eğri ticareti", "egri_ticareti"), ("En iyi taşıyan vadeyi tek başına uzun", "en_iyi_uzun"),
                 ("Beş vadeye eşit uzun", "esit_uzun"), ("Sabit 1s7s dikleştirici", "sabit_1s7s_dik"),
                 ("Sabit 2s7s dikleştirici", "sabit_2s7s_dik")):
        x = st[k]
        satir_sina(t, s, [str(x["n"]), sayi(x["ort"], 1, True), sayi(x["medyan"], 1, True), yz(x["isabet"], 0),
                          f"{sayi(x['yarilar']['2013_2019']['ort'], 1, True)} · {yz(x['yarilar']['2013_2019']['isabet'], 0)}",
                          f"{sayi(x['yarilar']['2020_2026']['ort'], 1, True)} · {yz(x['yarilar']['2020_2026']['isabet'], 0)}"],
                   "W3 eğri ticareti")
    et = st["egri_ticareti"]
    metinde(m, f"çeyrekte ortalama {bp(et['ort'], True, 1)}, medyan {bp(et['medyan'], True, 1)}, isabet "
               f"{yz(et['isabet'], 0)}", "W3 eğri ticareti")
    metinde(m, f"Newey–West t {sayi(et['t'], 1)}", "W3 eğri ticareti t")
    iddia(et["yarilar"]["2013_2019"]["ort"] > 0 and et["yarilar"]["2020_2026"]["ort"] > 0, "eğri ticareti iki yarıda artı")
    gc = et["gecikme"]
    metinde(m, f"okununca {sayi(gc['1'], 1, True)}", "W3 eğri ticareti gecikme")
    metinde(m, f"{sayi(gc['5'], 1, True)}", "W3 eğri ticareti gecikme")
    metinde(m, f"{sayi(gc['10'], 1, True)} ve {sayi(gc['21'], 1, True)} bp", "W3 eğri ticareti gecikme")
    metinde(m, f"korelasyonu {sayi(et['seviye_korelasyon'], 2)}", "W3 seviye korelasyonu")
    metinde(m, f"pencerelerin {yz(et['diklestirici_pay'], 0)}'sinde dikleştirici", "W3 dikleştirici payı")
    metinde(m, f"{sayi(st['sabit_1s7s_dik']['ort'], 1, True)} ve {bp(st['sabit_2s7s_dik']['ort'], True, 1)}", "W3 sabit dikleştirici")
    su, sk = st["secim_uzun"], st["secim_kisa"]
    metinde(m, (f"uzun bacak {st['n']} pencerenin {su['n1y']}'sinde 1 yıl, {su['n7y']}'inde 7 yıl,\n  "
                f"{su['n2y']}'inde 2 yıl, {su['n5y']}'sında 5 yıl, {su['n3y']}'ünde 3 yıl"), "W3 seçim uzun")
    metinde(m, (f"kısa bacak {sk['n1y']}'sinde 1 yıl, {sk['n7y']}'inde 7 yıl,\n  {sk['n5y']}'ünde 5 yıl, "
                f"{sk['n2y']}'sında 2 yıl, {sk['n3y']}'unda 3 yıl"), "W3 seçim kısa")
    birlikte_1y, birlikte_7y = su["n1y"] + sk["n1y"], su["n7y"] + sk["n7y"]
    metinde(m, f"1 yıl {st['n']} pencerenin {birlikte_1y}'ünde, 7 yıl {birlikte_7y}'sinde", "W3 uçlar")
    metinde(m, f"en az {birlikte_1y + birlikte_7y - st['n']} pencerede ikisi birlikte", "W3 uçlar")
    metinde(m, f"standart sapması {sayi(et['sd'])} bp — ortalamanın dört katı", "W3 sd")
    iddia(3.5 < et["sd"] / et["ort"] < 4.5, "sd ortalamanın dört katı")
    metinde(m, f"DV01 × {sayi(et['sd'])} bp", "W3 boyut")
    metinde(m, f"pencerenin {yz(100 - et['isabet'], 0)}'i kaybettirdi", "W3 kaybeden pay")

    t = tablo(tl, "Fly ailesi (örneklem dışı PCA, taşıma işaretiyle, bp)")
    for f in ("2y5y7y", "1y2y5y", "3y5y7y", "2y3y5y"):
        T, H = ff[f]["tasima"], ff[f]["hep_long"]
        satir_sina(t, f, [str(T["n"]), sayi(T["ort"], 1, True), sayi(T["medyan"], 1, True), yz(T["isabet"], 0),
                          sayi(T["t"], 1, True),
                          f"{sayi(T['yarilar']['2013_2019']['ort'], 1, True)} · {sayi(T['yarilar']['2020_2026']['ort'], 1, True)}",
                          f"{sayi(H['ort'], 1, True)} · {sayi(H['t'], 1, True)}",
                          " · ".join(sayi(ff[f]["gecikme"][g]["tasima"], 1, True) for g in ("1", "5", "10", "21"))],
                   "W3 fly taşıması")
    metinde(m, f"{ff['2y5y7y']['tasima']['n']} pencere (2016-02'den)", "W3 fly kapsamı")
    iddia(ff["2y5y7y"]["tasima"]["yarilar"]["2013_2019"]["n"] == 47, "örneklem dışı ilk yarı 2016-02 – 2019-12 (47 ay)")
    T1 = ff["1y2y5y"]["tasima"]
    metinde(m, f"{bp(T1['ort'], True, 1)}, t {sayi(T1['t'], 1)}, iki yarıda da artı "
               f"({sayi(T1['yarilar']['2013_2019']['ort'], 1, True)} · {sayi(T1['yarilar']['2020_2026']['ort'], 1, True)})",
            "W3 1y2y5y kenarı")
    iddia(T1["t"] >= 2 and all(abs(ff[f]["tasima"]["t"]) < 2 for f in ("2y5y7y", "3y5y7y", "2y3y5y")),
          "yalnız 1y2y5y'de kenar")
    metinde(m, f"hep long tutmak {bp(ff['1y2y5y']['hep_long']['ort'], True, 1)}", "W3 1y2y5y hep long")
    for f in ("2y5y7y", "3y5y7y", "2y3y5y"):
        T = ff[f]["tasima"]
        metinde(m, f"{sayi(T['ort'], 1, True)}{' bp' if f == '2y5y7y' else ''}, t {sayi(T['t'], 1)})", f"W3 {f} taşıma")
    g1 = ff["1y2y5y"]["gecikme"]
    metinde(m, f"1 gün önceki eğriden {sayi(g1['1']['tasima'], 1, True)}, 5 günden", "W3 1y2y5y gecikme")
    metinde(m, f"{sayi(g1['10']['tasima'], 1, True)}, 21 günden {sayi(g1['21']['tasima'], 1, True)} bp", "W3 1y2y5y gecikme")
    iddia(g1["21"]["tasima"] / g1["1"]["tasima"] < 0.2, "21 günde 1 günlük kenarın beşte birinden azı")
    metinde(m, f"long 1y2y5y PCA çeyrekte {bp(to['1y2y5y_longpca']['tasima_bp'])} öder", "W3 bugünkü kural çıktısı")

    uy_ters = []
    for f, ad in (("2y5y7y", "2y5y7y"), ("1y2y5y", "1y2y5y"), ("3y5y7y", "3y5y7y"), ("2y3y5y", "2y3y5y")):
        u, r = ff[f]["uyumlu"]["ort"], ff[f]["ters"]["ort"]
        ek = "'ye" if sayi(u, 1).endswith(("2", "7")) else "'e"
        metinde(m, f"{sayi(u, 1, True)}{ek} karşı {sayi(r, 1, True)}", f"W3 süzgeç {ad}")
        iddia(u > r and all(ff[f]["gecikme"][g]["uyumlu"] > ff[f]["gecikme"][g]["ters"] for g in ("1", "5", "10", "21")),
              f"süzgeç {ad}: uyumlu her gecikmede önde")
        for y in ("2013_2019", "2020_2026"):
            uy_ters.append(ff[f]["uyumlu"]["yarilar"][y]["ort"] > ff[f]["ters"]["yarilar"][y]["ort"])
    iddia(uy_ters.count(False) == 4, "yarılarda sekiz karşılaştırmanın dördünde ters")
    nk = [ff[f][k]["n"] for f in ff for k in ("uyumlu", "ters")]
    metinde(m, f"her kolda {min(nk)}–{max(nk)} işlem", "W3 süzgeç n")

    t = tablo(tl, "Taşıma kuralı (özet)")
    satir_sina(t, "(i) Taşıma işaretiyle outright zamanlama",
               [f"5 vade, {ta['n_pencere']} pencere, fiyatın %'si",
                f"5 yılda {yz(z5['zamanlama']['ort'], 1, True)}; hep kısa {yz(z5['hep_kisa']['ort'], 1, True)}", None],
               "W3 özet")
    satir_sina(t, "(ii) En iyi taşıyan vadeyi uzun tutmak",
               [f"{st['n']} pencere, DV01 başına", f"{bp(eu['ort'], True, 1)}; iki yarıda eksi", None], "W3 özet")
    satir_sina(t, "(iii) Eğri ticareti",
               [f"{st['n']} pencere, DV01-nötr", f"{bp(et['ort'], True, 1)}, t {sayi(et['t'], 1)}; iki yarıda artı", None],
               "W3 özet")
    satir_sina(t, "(iv) Fly taşıması",
               [f"{len(ff)} fly, {T1['n']} pencere, örneklem dışı", f"yalnız 1y2y5y: {bp(T1['ort'], True, 1)}, t {sayi(T1['t'], 1)}",
                None], "W3 özet")
    satir_sina(t, "(v) Taşıma süzgeç olarak", [f"{len(ff)} fly, dönüş işlemleri", None, None], "W3 özet")

    # ───────────────────────── 3.7 fonlama rejimi
    G = fgc["gecis"]
    metinde(m, f"{fgc['blok_n']} blok arasında {fgc['n']} çıpa geçişi", "W3 geçiş kapsamı")
    t = tablo(tl, "Fonlama çıpası geçişi (ortalama getiri değişimi, bp)")
    for g, ad in (("politika>koridor_ust", "Politika faizinden tavana"), ("koridor_ust>politika", "Tavandan politika faizine")):
        for kol, ek in (("d20", "20 gün"), ("d525", "5.–25. gün")):
            satir_sina(t, f"{ad} · {ek}", [str(G[g]["n"])] + [n0(G[g][kol][d]) for d in DUG], "W3 fonlama geçişi")
        for tr in G[g]["tarih"]:
            metinde(m, gun(tr), "W3 geçiş tarihi")
    pu, up = G["politika>koridor_ust"], G["koridor_ust>politika"]
    iddia(pu["d20_2y_isaret"] == pu["n"] == 4, "tavana çıkışta 2y dört olayın dördünde yükseldi")
    iddia(up["d20_2y_isaret"] == 2 and up["n"] == 4, "tavandan dönüşte 2y dört olayın ikisinde yükseldi")
    metinde(m, f"20 günde 3 ay {n0(pu['d20']['n3a'])}, 2 yıl {n0(pu['d20']['n2y'])}, 7 yıl\n  {n0(pu['d20']['n7y'])} bp",
            "W3 tavana çıkış")
    metinde(m, f"5. günden 25. güne 2 yılda {bp(pu['d525']['n2y'], True)}", "W3 tavana çıkış gecikmeli")
    metinde(m, f"(1 yılda {n0(up['d20']['n1y'])}, 3 ayda {bp(up['d20']['n3a'], True)})", "W3 tavandan dönüş")
    iddia(pu["d20"]["n3a"] > pu["d20"]["n7y"] > 0, "tavana çıkış: kısa uç önde ayı yataylaşma")

    fx = kf["fixing"]
    metinde(m, f"dönem dilinde sırasıyla {yz(kf['F_temsili'])}, {yz(kf['F_politika'])} ve {yz(kf['F_bugun'])}", "W3 dönem dili")
    t = tablo(tl, "Vade (temsili OIS receive, fixing taşıması, bp)")
    metinde(m, f"Fixing {yz(fx['temsili'])} (temsili, tavan) | Fixing {yz(fx['politika'])} (politika faizi) | "
               f"Fixing {yz(fx['bugun'])} (22.09.2026)", "W3 fixing başlıkları")
    for k, s in (("3m", "3 ay"), ("6m", "6 ay"), ("1y", "1 yıl"), ("2y", "2 yıl"), ("5y", "5 yıl"), ("10y", "10 yıl")):
        x = kf[k]
        satir_sina(t, s, [yz(x["K"]), n0(x["temsili"]), n0(x["politika"]), n0(x["bugun"])], "W3 fixing taşıması")
    iddia(kf["3m"]["temsili"] < 0 < kf["3m"]["politika"] < kf["3m"]["bugun"], "3 aylık receive'in işareti döner")
    metinde(m, f"çeyrekte DV01 başına {bp(kf['3m']['temsili'])} öder", "W3 3 ay işaret")
    metinde(m, f"{bp(kf['3m']['politika'], True)}, bugünkü fixingle {bp(kf['3m']['bugun'], True)} toplar", "W3 3 ay işaret")
    metinde(m, f"(10 yılda {sayi(kf['10y']['temsili'])}'ten {sayi(kf['10y']['bugun'])}'e)", "W3 10 yıl")

    t = tablo(tl, "Yapı (temsili OIS, net yüzen bacak)")
    for s, k, u in (("1y2y dikleştirici", "1y2y", "2y"), ("2s5s dikleştirici", "2y5y", "5y"), ("2s10s dikleştirici", "2y10y", "10y")):
        x = oy[k]
        kisa = k[:2]
        satir_sina(t, s, [f"{kisa} receive 100 · {u} pay {sayi(x['nominal_uzun_mn'], 1)}", sayi(x["net_yuzen_mn"], 1, True),
                          sayi(x["tlref_100_etkisi_bin"], 0, True), sayi(x["tasima_mn"], 2, True),
                          sayi(x["tasima_bugun_mn"], 2, True)], "W3 net yüzen")
    for s, f, w in (("Long 2y5y7y 50:50", "2y5y7y", "5050"), ("Long 2y5y7y PCA", "2y5y7y", "pca"),
                    ("Long 1y2y5y 50:50", "1y2y5y", "5050"), ("Long 1y2y5y PCA", "1y2y5y", "pca")):
        x = of[f][w]
        k1, g, k2 = f[:2], f[2:4], f[4:]
        nom = x["nominal_mn"]
        satir_sina(t, s, [f"{g} pay {sayi(nom[g])} · {k1} receive {sayi(nom[k1], 1)} · {k2} receive {sayi(nom[k2], 1)}",
                          sayi(x["net_yuzen_mn"], 1, True), sayi(x["tlref_100_etkisi_bin"], 0, True),
                          sayi(x["tasima_mn"], 2, True), sayi(x["tasima_bugun_mn"], 2, True)], "W3 net yüzen")
    iddia(all(x["net_yuzen_mn"] < 0 for x in oy.values()) and
          all(of[f][w]["net_yuzen_mn"] < 0 for f in ("2y5y7y", "1y2y5y") for w in ("5050", "pca")),
          "yedi yapının yedisi net TLREF öder")
    metinde(m, f"{sayi(oy['1y2y']['tasima_mn'], 2, True)} mn'dan {sayi(oy['1y2y']['tasima_bugun_mn'], 2, True)} mn'a",
            "W3 işaret dönüşü 1y2y")
    metinde(m, f"{sayi(L['tasima_mn'], 2, True)} mn'dan {sayi(L['tasima_bugun_mn'], 2, True)} mn'a", "W3 işaret dönüşü fly")

    cn = rj["cipa_n"]
    metinde(m, f"TLREF 2018 sonundan; {sum(cn.values())} pencere", "W3 çıpa kapsamı")
    metinde(m, f"Politika faizi ({cn['politika']} pencere) | Koridor tavanı ({cn['koridor_ust']} pencere) | "
               f"Koridor tabanı ({cn['koridor_alt']} pencere)", "W3 çıpa n")
    t = tablo(tl, "Yapı (sinyal günü fonlama çıpası, 3 ay, bp): toplam · isabet")
    for s, k in (("2 yıl receive", "2y_receive"), ("5 yıl receive", "5y_receive"), ("2s5s dikleştirici", "2s5s_diklestirici"),
                 ("2s7s dikleştirici", "2s7s_diklestirici"), ("Long 2y5y7y 50:50", "2y5y7y_long50"),
                 ("Long 2y5y7y PCA", "2y5y7y_longpca"), ("Long 1y2y5y 50:50", "1y2y5y_long50"),
                 ("Long 1y2y5y PCA", "1y2y5y_longpca")):
        c = rj["cipa"][k]
        satir_sina(t, s, [f"{n0(c[x]['toplam'])} · {yz(c[x]['isabet'], 0)}" for x in ("politika", "koridor_ust", "koridor_alt")],
                   "W3 çıpa")
    cu = rj["cipa"]
    metinde(m, f"({n0(cu['2s5s_diklestirici']['koridor_ust']['toplam'])}, {n0(cu['2s7s_diklestirici']['koridor_ust']['toplam'])}, "
               f"{bp(cu['2y5y7y_long50']['koridor_ust']['toplam'], True)})", "W3 tavan sonrası")
    metinde(m, f"taşıma {n0(cu['2s5s_diklestirici']['koridor_ust']['tasima'])}, hareket "
               f"{bp(cu['2s5s_diklestirici']['koridor_ust']['hareket'], True)}", "W3 tavan sonrası kaynak")
    metinde(m, f"Taban satırı yalnız on pencere", "W3 küçük n")
    iddia(cn["koridor_alt"] == 10, "taban on pencere")

    # ───────────────────────── 3.8 asansör ve tuzaklar
    ks, kv = rj["kuyruk_sinir_bp"], rj["kuyruk_seviye"]
    metinde(m, f"({bp(ks[1], True)} ve üstü, ortalama {bp(kv['satis'], True)})", "W3 satış kuyruğu")
    metinde(m, f"({bp(ks[0])} ve altı, ortalama {bp(kv['ralli'])})", "W3 ralli kuyruğu")
    kn = {rj["kuyruk"][y][q]["n"] for y in rj["kuyruk"] for q in ("satis", "ralli")}
    iddia(kn == {17}, "her kuyrukta 17 pencere")
    metinde(m, "her birinde 17 pencere", "W3 kuyruk n")
    t = tablo(tl, "Bugün taşıyan yapı (kâğıt eğrisi, 3 ay, bp)")
    AS = (("5 yıl pay (kâğıtta açığa satış)", "5y_receive", "5y_receive", -1),
          ("2s5s dikleştirici", "2s5s_diklestirici", "2y5y_diklestirici", 1),
          ("2s7s dikleştirici", "2s7s_diklestirici", "2y7y_diklestirici", 1),
          ("Short 1y2y5y 50:50 (gövdede receive)", "1y2y5y_long50", "1y2y5y_long50", -1),
          ("Long 2y5y7y 50:50", "2y5y7y_long50", "2y5y7y_long50", 1),
          ("Long 2y5y7y PCA", "2y5y7y_longpca", "2y5y7y_longpca", 1))
    ceyrek = {}
    for s, k, kt, yon in AS:
        kuy = rj["kuyruk"][k]
        q = min(("satis", "ralli"), key=lambda z: yon * kuy[z]["hareket"])
        x = kuy[q]
        tas = yon * to[kt]["tasima_bp"]
        h = yon * x["hareket"]
        p_lo, p_hi = (x["hareket_p25"], x["hareket_p75"]) if yon > 0 else (-x["hareket_p75"], -x["hareket_p25"])
        ceyrek[s] = abs(h) / tas
        satir_sina(t, s, [n0(tas), "satış" if q == "satis" else "ralli", n0(h), f"{n0(p_lo)} · {n0(p_hi)}",
                          sayi(abs(h) / tas, 1) if h < 0 else "—"], "W3 asansör")
        iddia(tas > 0, f"{s}: bugün taşıyor")
    iddia(round(ceyrek["5 yıl pay (kâğıtta açığa satış)"]) == 6, "5 yıl pay: altı çeyrek")
    iddia(ceyrek["2s7s dikleştirici"] > 5, "2s7s: beş çeyreği aşar")
    metinde(m, f"maaşı ({bp(-to['5y_receive']['tasima_bp'], True)})", "W3 asansör metni")
    metinde(m, f"dikleştiricinin ({bp(to['2y7y_diklestirici']['tasima_bp'], True)})", "W3 asansör metni")
    kyr = rj["kuyruk"]
    metinde(m, f"50:50'de {bp(kyr['2y5y7y_long50']['satis']['hareket'])} (satış), PCA'da "
               f"{bp(kyr['2y5y7y_longpca']['ralli']['hareket'])}", "W3 fly kuyruğu")
    metinde(m, f"ortalama {bp(rj['faz']['2y5y7y_long50']['artırım']['toplam'])}, taşıma dahil", "W3 fly artırım")
    metinde(m, f"(500 mn TL'lik 1 yıllık receive'de {sayi(orn['carry_tavan'], 2, True)} yerine "
               f"{sayi(orn['carry_tavan_basit'], 2, True)} mn", "W3 tuzak basit fixing")
    iddia(0.28 < (orn["carry_tavan"] - orn["carry_tavan_basit"]) / orn["carry_tavan"] < 0.36, "basit fixing ≈ üçte bir")
    metinde(m, f"aylığın {sayi(h91['1']['basabas_bp'] / h30['1']['basabas_bp'], 1)} katıdır", "W3 tuzak ufuk")
    metinde(m, f"tavanda\n   {sayi(kf['3m']['temsili'])}, bugünkü fixingle {bp(kf['3m']['bugun'], True)}", "W3 tuzak fonlama")
    metinde(m, f"ortalama {sayi(tm['ort_sure_ay']['n2y'], 1)} ay yaşadı", "W3 tuzak roll haritası")
    metinde(m, f"isabeti {yz(et['isabet'], 0)} ama tek işlemin standart\n   sapması {sayi(et['sd'])} bp; hep kısanın isabeti "
               f"2 yılda {yz(zm['n2y']['hep_kisa']['isabet'], 0)}", "W3 tuzak isabet")
    metinde(m, "Bu bölümün beklenti kartları: K5, K6, K9, K13, K14", "W3 kartlar")

    # ───────────────────────── pratik
    a1, b1 = h30["1"], h91["1"]
    t1y = bg["tasima"]["1"]
    metinde(m, f"getiri {yz(t1y['getiri'])}, modifiye durasyon {sayi(t1y['mod_dur'], 2)}. Bir aylık ufukta taşıma "
               f"{yz(a1['tasima'], arti=True)}, roll {yz(a1['roll'], arti=True)}", "W3 pratik 1")
    metinde(m, f"taşıma {yz(b1['tasima'], arti=True)}, roll {yz(b1['roll'], arti=True)}", "W3 pratik 1")
    metinde(m, f"getirisi {yz(b1['getiri_Th'])}. (a)", "W3 pratik 1")
    metinde(m, f"⇒ **{bp(a1['basabas_bp'])}**", "W3 pratik 1 (a)")
    metinde(m, f"⇒ **{bp(b1['basabas_bp'])}**", "W3 pratik 1 (a)")
    metinde(m, f"**{sayi(b1['basabas_bp'] / a1['basabas_bp'], 1)} kat**", "W3 pratik 1 (b)")
    metinde(m, f"**{yz(b1['forward'])}**", "W3 pratik 1 (c)")
    a5 = h30["5"]
    metinde(m, f"vadenin bugünkü getirisi {yz(a5['getiri_Th'])}, başabaş {bp(a5['basabas_bp'])}", "W3 pratik 2")
    metinde(m, f"**{yz(a5['forward'])}**", "W3 pratik 2 (a)")
    metinde(m, f"P&L = taşıma + roll = {bp(a5['basabas_bp'])}", "W3 pratik 2 (c)")
    metinde(m, f"5 yılda da {yz(z5['hep_kisa']['ort'], 1, True)} kazandırdı (t {sayi(z5['hep_kisa']['t'], 1)}), 3 yılda\n"
               f"{yz(zm['n3y']['hep_kisa']['ort'], 1, True)}", "W3 pratik 3")
    metinde(m, f"zamanlama 5 yılda {yz(z5['zamanlama']['yarilar']['2013_2019']['ort'], 1, True)}, hep kısa\n"
               f"{yz(z5['hep_kisa']['yarilar']['2013_2019']['ort'], 1, True)}", "W3 pratik 3 yarılar")
    metinde(m, f"çeyrekte {bp(et['ort'], True, 1)}, t {sayi(et['t'], 1)}, iki\nyarıda da artı, seviyeyle korelasyonu "
               f"{sayi(et['seviye_korelasyon'], 2)}", "W3 pratik 3 eğri ticareti")
    metinde(m, f"1 yıl {n0(be['n1y'])}, 2 yıl {n0(be['n2y'])}, 3 yıl {n0(be['n3y'])}, 5 yıl {n0(be['n5y'])}, 7\nyıl "
               f"{n0(be['n7y'])} bp", "W3 pratik 4 girdiler")
    for fl in ("2y3y5y_50", "1y2y3y_50", "3y5y7y_50"):
        metinde(m, f"**{bp(fh['fly'][fl]['tasima_long_bp'], True)}**", f"W3 pratik 4 {fl}")
    metinde(m, f"2y5y7y'den ({bp(f50['tasima_long_bp'], True)})", "W3 pratik 4 kıyas")
    metinde(m, f"2y receive taşıma {sayi(L['tasima_bin']['2y'], 0)} · roll {sayi(L['roll_bin']['2y'], 0)}; 5y pay taşıma "
               f"{sayi(L['tasima_bin']['5y'], 0, True)} · roll {sayi(L['roll_bin']['5y'], 0, True)}; 7y\nreceive taşıma "
               f"{sayi(L['tasima_bin']['7y'], 0)} · roll {sayi(L['roll_bin']['7y'], 0)}", "W3 pratik 5 bacaklar")
    metinde(m, f"Gövde DV01'i {sayi(of['2y5y7y']['govde_dv01'])} TL/bp", "W3 pratik 5 DV01")
    ts, rs = sum(L["tasima_bin"].values()), sum(L["roll_bin"].values())
    metinde(m, f"= {ts:.0f}$ bin ≈ **{sayi(L['tasima_mn'], 2, True)} mn TL** ≈ {n0(round(ts * 1e3 / of['2y5y7y']['govde_dv01']))} bp",
            "W3 pratik 5 (a)")
    metinde(m, f"= {rs:.0f}$ bin ≈ **{sayi(L['roll_mn'], 2, True)} mn TL** ≈ {n0(round(rs * 1e3 / of['2y5y7y']['govde_dv01']))} bp",
            "W3 pratik 5 (a)")
    metinde(m, f"Toplam {sayi(L['toplam_mn'], 2, True)} mn TL, gövde DV01'i\nbaşına {bp(L['toplam_bp_govde'], True)}",
            "W3 pratik 5 (a)")
    metinde(m, f"roll parçası {bp(f50['roll_parca_bp'], True)}, OIS'te {n0(round(rs * 1e3 / of['2y5y7y']['govde_dv01']))} bp",
            "W3 pratik 5 (b)")
    metinde(m, f"kâğıtta {bp(f50['tasima_parca_bp'], True)}, OIS'te ≈ {n0(round(ts * 1e3 / of['2y5y7y']['govde_dv01']))} bp",
            "W3 pratik 5 (b)")
    metinde(m, f"toplam {bp(L['toplam_bugun_bp_govde'], True)}. İşareti", "W3 pratik 5 (c)")


# W4_dogrula
def kontrol_w4(o: dict, m: str, tl: list) -> None:
    """Bölüm 4 (spread): 4.1–4.3'ün yeni ve yön diliyle değişen satırları, 4.4–4.5'in
    bütün yeni tabloları ve metindeki ölçülmüş sayılar."""
    mn = " ".join(m.split())          # satır kırılmaları metin parçalarını bölmesin

    def baslik(t: list, beklenen: list[str], ad: str) -> None:
        if not t:
            return
        for i, b in enumerate(beklenen):
            sayac["hucre"] += 1
            gercek = t[0][i + 1] if i + 1 < len(t[0]) else "(yok)"
            if gercek != b:
                hatalar.append(f"{ad} · başlık sütun {i + 2}: metin {gercek!r}, ölçüm {b!r}")

    def ti(h: dict) -> str:           # "toplam · isabet"
        return f"{sayi(h['toplam'], 0, True)} · {yz(h['isabet'], 0)}"

    def gun(s: str) -> str:
        return f"{s[8:10]}.{s[5:7]}.{s[:4]}"

    # ───────────────────────────── giriş
    ts = o["tasima_stratejileri"]
    rj = o["rejim_yapi"]
    metinde(mn, f"{sayi(ts['egri_ticareti']['ort'], 1, True)} bp (t {sayi(ts['egri_ticareti']['t'], 1)})", "W4 giriş")
    metinde(mn, f"hep tutmak {bp(ts['sabit_2s7s_dik']['ort'], b=1)} kaybettirdi", "W4 giriş")
    metinde(mn, f"güvercin sürpriz pencerelerinin {yz(rj['kova']['2s7s_diklestirici']['guvercin']['isabet'], 0)}'ünde",
            "W4 giriş")
    metinde(mn, f"pencerelerinin yalnız {yz(rj['kuyruk']['2s7s_diklestirici']['satis']['isabet'], 0)}'ünde", "W4 giriş")

    # ───────────────────────────── 4.1 bugünkü eğri (yeni cümle)
    yb = o["yapi_bugun"]
    metinde(mn, f"2s5s ve 2s7s tam örneklemde {sayi(yb['2s5s']['yuzdelik'])}. yüzdelikte ama son 36 ayda "
                f"{sayi(yb['2s5s']['yuzdelik_son36'])}. ve {sayi(yb['2s7s']['yuzdelik_son36'])}. yüzdelikte",
            "W4 4.1 yüzdelik")
    if yb["2s5s"]["yuzdelik"] != yb["2s7s"]["yuzdelik"]:
        hatalar.append("W4 4.1: 2s5s ve 2s7s tarihsel yüzdeliği artık aynı değil; cümle tek sayı varsayıyor")

    # ───────────────────────────── 4.2 kadran eki
    kd = o["kadran"]
    metinde(mn, f"ayların yalnız {yz(kd['pay']['boğa yataylaşma'], 1)}'i", "W4 4.2 boğa yataylaşma")

    # ───────────────────────────── 4.3 faktör tablosu: long fly satırları (yön dili)
    fm = o["faktor_maruziyet"]
    t = tablo(tl, "Yapı (10.000 TL/bp)")
    for k, s in (("fly50_long", "long 2y5y7y fly (gövdede pay), 50:50"),
                 ("flyPCA_long", "long 2y5y7y fly (gövdede pay), PCA-nötr")):
        satir_sina(t, s, [sayi(x, 0, True) + " TL" for x in fm[k]], "W4 faktör (long fly)")
    for k in ("fly50_long", "flyPCA_long"):          # long = gövdeyi al'ın tam aynası
        eski = "fly50_govde_al" if k == "fly50_long" else "flyPCA_govde_al"
        if any(abs(a + b) > 0.5 for a, b in zip(fm[k], fm[eski])):
            hatalar.append(f"W4 faktör: {k} {eski}'nin aynası değil")
    x = fm["2s7s_yassi_dv01"]
    metinde(mn, f"seviye yükselişinde {sayi(-x[0], 0)} TL, aynı DV01'lük 2 yıllık uzun kâğıdın seviye riskinin "
                f"yaklaşık {yz(100 * x[0] / -fm['2y_uzun'][0], 0)}'si", "W4 faktör dikleştirici")
    metinde(mn, f"dikleştiriciye {sayi(x[2] / 1e6, 1)} mn TL kaybettirir", "W4 faktör dikleştirici")
    metinde(mn, f"yükselişinde {sayi(fm['fly50_long'][0], 0)} TL yazar", "W4 long fly")
    metinde(mn, f"maruziyeti {sayi(fm['flyPCA_long'][0], 0)} TL ve {sayi(fm['flyPCA_long'][1], 0)} TL'ye iner",
            "W4 long fly PCA")
    metinde(mn, f"büküm kalır ({sayi(fm['flyPCA_long'][2], 0)} TL)", "W4 long fly PCA")

    # ───────────────────────────── 4.3 spread'in taşıması (dikleştirici satırları ve taraf)
    ys = o["yapi_tasima"]
    to = o["tasima_oynaklik"]
    t = tablo(tl, "Yapı (22.09.2026, DV01-nötr)")
    satir_sina(t, "2s5s yassılaştırıcı", [None, "öder"], "W4 spread taşıması")
    satir_sina(t, "2s7s yassılaştırıcı", [None, "öder"], "W4 spread taşıması")
    satir_sina(t, "2s5s dikleştirici", [bp(ys["2s5s_diklestirici_bp"], True), "toplar"], "W4 spread taşıması")
    satir_sina(t, "2s7s dikleştirici", [bp(ys["2s7s_diklestirici_bp"], True), "toplar"], "W4 spread taşıması")
    satir_sina(t, "1y2y dikleştirici", [bp(to["1y2y_diklestirici"]["tasima_bp"], True),
                                        "toplar" if to["1y2y_diklestirici"]["tasima_bp"] > 0 else "öder"],
               "W4 spread taşıması")
    satir_sina(t, "5s7s dikleştirici", [bp(to["5y7y_diklestirici"]["tasima_bp"], True),
                                        "toplar" if to["5y7y_diklestirici"]["tasima_bp"] > 0 else "öder"],
               "W4 spread taşıması")
    for a, b_ in (("2s5s_diklestirici_bp", "2y5y_diklestirici"), ("2s7s_diklestirici_bp", "2y7y_diklestirici")):
        if ys[a] != to[b_]["tasima_bp"] or ys[a] != -ys[a.replace("diklestirici", "yassilastirici")]:
            hatalar.append(f"W4 spread taşıması: {a} iki ölçüde ya da yassılaştırıcı aynasında tutarsız")
    bg = o["bugun"]["tasima"]
    for T, s in (("1", "1 yıl"), ("2", "2 yıl"), ("5", "5 yıl"), ("7", "7 yıl")):
        metinde(mn, f"{s} {bp(bg[T]['basabas_bp'])}", "W4 bacak başabaşı")
    fh = o["fly_tasima_haritasi"]
    tb, rb = fh["tasima_bp"], fh["roll_bp"]
    metinde(mn, f"2 yılda {sayi(tb['n2y'])}, 5 yılda {sayi(tb['n5y'])}, 7 yılda {sayi(tb['n7y'])} bp", "W4 taşıma parçası")
    metinde(mn, f"roll 2 yılda {sayi(rb['n2y'], 0, True)}, 5 yılda {sayi(rb['n5y'])}, 7 yılda {sayi(rb['n7y'])} bp",
            "W4 roll parçası")
    for k in ("n5y", "n7y"):
        metinde(mn, f"${int(tb['n2y'])} - ({int(tb[k])}) = {int(tb['n2y'] - tb[k])}$", "W4 taşıma parçası")
        metinde(mn, f"${int(rb['n2y'])} - ({int(rb[k])}) = {int(rb['n2y'] - rb[k]):+d}$", "W4 roll parçası")
        if abs((tb["n2y"] - tb[k]) + (rb["n2y"] - rb[k]) - (bg["2"]["basabas_bp"] - bg[k[1]]["basabas_bp"])) > 1.5:
            hatalar.append(f"W4 taşıma/roll parçaları ({k}) toplamla bir baz puandan fazla ayrışıyor")
    metinde(mn, f"DV01 başına {bp(tb['n1y'])}", "W4 1y taşıma")
    metinde(mn, f"roll'u ({bp(rb['n1y'], True)})", "W4 1y roll")
    oy = o["ois_yapilar"]
    metinde(mn, bp(oy["2y5y"]["toplam_bp"]), "W4 OIS 2s5s")
    metinde(mn, f"2s10s dikleştirici {bp(oy['2y10y']['toplam_bp'])}", "W4 OIS 2s10s")
    metinde(mn, f"1y2y dikleştirici {bp(oy['1y2y']['toplam_bp'], True)} toplar", "W4 OIS 1y2y")
    metinde(mn, f"5 yılda {sayi(oy['2y5y']['nominal_uzun_mn'], 1)} mn TL pay", "W4 OIS nominal")
    metinde(mn, f"({sayi(-oy['2y5y']['net_yuzen_mn'], 1)} mn TL)", "W4 OIS net yüzen")
    metinde(mn, f"net olarak {sayi(-oy['2y5y']['net_yuzen_mn'], 1)} mn TL üzerinden TLREF öder", "W4 OIS net yüzen")
    metinde(mn, f"taşımasından {sayi(-oy['2y5y']['tlref_100_etkisi_bin'])} bin TL götürür", "W4 OIS fixing")
    metinde(mn, f"taşıması {sayi(oy['2y5y']['tasima_mn'], 2)} mn TL, fixing %36,49 varsayımıyla "
                f"{sayi(oy['2y5y']['tasima_bugun_mn'], 2)} mn TL", "W4 OIS fixing")
    if oy["2y5y"]["net_yuzen_mn"] >= 0:
        hatalar.append("W4 OIS: 2s5s dikleştirici artık net yüzen ÖDEYEN değil; metin öyle diyor")

    # ───────────────────────────── 4.4 rejim tanımları ve metin
    metinde(mn, f"{rj['n_pencere']} pencere, üst üste binerek", "W4 4.4 pencere")
    metinde(mn, f"{sum(rj['faz_n'].values())} pencere. **Sürpriz**", "W4 4.4 faz pencere")
    metinde(mn, f"{rj['faz_n']['indirim']} indirim penceresi kabaca on dört", "W4 4.4 bağımsızlık")
    if round(rj["faz_n"]["indirim"] / 3) != 14:
        hatalar.append("W4 4.4: indirim penceresi / 3 artık 14 değil ('on dört' cümlesi)")
    ks, kn = rj["kova_surpriz"], rj["kova_n"]
    metinde(mn, f"ortalama {sayi(-ks['guvercin'])} bp altında, şahin kovada {sayi(ks['sahin'])} bp üstünde, "
                f"orta kovada {sayi(ks['orta'])} bp üstünde", "W4 kova sürprizi")
    metinde(mn, f"(kova sınırları {sayi(rj['kova_sinir_bp'][0])} ve {sayi(rj['kova_sinir_bp'][1], 0, True)} bp)",
            "W4 kova sınırı")
    metinde(mn, f"ortalaması {bp(rj['surpriz_ort'], True)}, medyanı {bp(rj['surpriz_medyan'], True)}", "W4 sürpriz")
    metinde(mn, f"{bp(rj['kuyruk_sinir_bp'][1], True)} (satış; ortalama {bp(rj['kuyruk_seviye']['satis'], True)}) ve "
                f"{bp(rj['kuyruk_sinir_bp'][0])} (ralli; ortalama {bp(rj['kuyruk_seviye']['ralli'])})", "W4 kuyruk sınırı")

    YAP = [("2y_receive", "2 yıl receive"), ("5y_receive", "5 yıl receive"), ("7y_receive", "7 yıl receive"),
           ("2s5s_diklestirici", "2s5s dikleştirici"), ("2s7s_diklestirici", "2s7s dikleştirici")]
    t = tablo(tl, "PPK fazı ve yapı (3 ay, DV01 başına bp)")
    baslik(t, [f"İndirim ({rj['faz_n']['indirim']} pencere)", f"Sabit ({rj['faz_n']['sabit']} pencere)",
               f"Artırım ({rj['faz_n']['artırım']} pencere)"], "W4 PPK fazı")
    for k, s in YAP:
        f = rj["faz"][k]
        satir_sina(t, s, [ti(f["indirim"]), ti(f["sabit"]), ti(f["artırım"])], "W4 PPK fazı")
    t = tablo(tl, "Forward'a göre sürpriz ve kuyruk (3 ay, DV01 başına bp)")
    ku = rj["kuyruk"]["2y_receive"]
    baslik(t, [f"Güvercin ({kn['guvercin']})", f"Orta ({kn['orta']})", f"Şahin ({kn['sahin']})",
               f"Satış kuyruğu ({ku['satis']['n']})", f"Ralli kuyruğu ({ku['ralli']['n']})"], "W4 sürpriz/kuyruk")
    for k, s in YAP:
        f, q = rj["kova"][k], rj["kuyruk"][k]
        satir_sina(t, s, [ti(f["guvercin"]), ti(f["orta"]), ti(f["sahin"]), ti(q["satis"]), ti(q["ralli"])],
                   "W4 sürpriz/kuyruk")
    SEC = [("2y_receive", "faz", "indirim", "2 yıl receive · indirim"),
           ("2y_receive", "kova", "guvercin", "2 yıl receive · güvercin"),
           ("2s5s_diklestirici", "faz", "indirim", "2s5s dikleştirici · indirim"),
           ("2s5s_diklestirici", "kova", "guvercin", "2s5s dikleştirici · güvercin"),
           ("2s5s_diklestirici", "kova", "sahin", "2s5s dikleştirici · şahin"),
           ("2s7s_diklestirici", "faz", "indirim", "2s7s dikleştirici · indirim"),
           ("2s7s_diklestirici", "kova", "guvercin", "2s7s dikleştirici · güvercin"),
           ("2s7s_diklestirici", "faz", "artırım", "2s7s dikleştirici · artırım"),
           ("2s7s_diklestirici", "kuyruk", "satis", "2s7s dikleştirici · satış kuyruğu")]
    t = tablo(tl, "Seçilmiş hücre (3 ay, DV01 başına bp)")
    for k, g, c, s in SEC:
        h = rj[g][k][c]
        satir_sina(t, s, [str(h["n"]), sayi(h["tasima"], 0, True), sayi(h["hareket"], 0, True),
                          f"{sayi(h['hareket_p25'], 0, True)} · {sayi(h['hareket_p75'], 0, True)}",
                          sayi(h["toplam"], 0, True), yz(h["isabet"], 0)], "W4 seçilmiş hücre")
        if abs(h["tasima"] + h["hareket"] - h["toplam"]) > 1.5:
            hatalar.append(f"W4 seçilmiş hücre {s}: toplam ≠ taşıma + hareket")
    r2, g2 = rj["faz"]["2y_receive"]["indirim"], rj["kova"]["2y_receive"]["guvercin"]
    metinde(mn, f"güvercin kovada {yz(g2['isabet'], 0)} isabetle {bp(g2['toplam'], True)} kazandırdı, hareketinin "
                f"alt çeyreği bile {bp(g2['hareket_p25'], True)}; indirim fazında {yz(r2['isabet'], 0)} isabetle "
                f"{bp(r2['toplam'], True)} ve alt çeyrek {bp(r2['hareket_p25'])}", "W4 sürpriz dersi")
    d5, d7 = rj["kova"]["2s5s_diklestirici"], rj["kova"]["2s7s_diklestirici"]
    f5, f7 = rj["faz"]["2s5s_diklestirici"], rj["faz"]["2s7s_diklestirici"]
    metinde(mn, f"2s5s {yz(d5['guvercin']['isabet'], 0)}'e {yz(f5['indirim']['isabet'], 0)}, 2s7s "
                f"{yz(d7['guvercin']['isabet'], 0)}'e {yz(f7['indirim']['isabet'], 0)}", "W4 sürpriz dersi")
    metinde(mn, f"güvercin kovada {sayi(d7['guvercin']['toplam'], 0, True)}, şahin kovada "
                f"{bp(d7['sahin']['toplam'])}; artırım fazında hareketin alt çeyreği "
                f"{bp(f7['artırım']['hareket_p25'])}", "W4 şahin")
    q2, q7 = rj["kuyruk"]["2y_receive"]["satis"], rj["kuyruk"]["2s7s_diklestirici"]["satis"]
    metinde(mn, f"({sayi(q7['toplam'] * -1)} / {sayi(-q2['toplam'])})", "W4 kuyruk oranı")
    if not 0.28 <= q7["toplam"] / q2["toplam"] <= 0.38:
        hatalar.append("W4 kuyruk: 2s7s / 2y oranı artık 'kabaca üçte bir' değil")
    metinde(mn, f"2 yıllık receive −66 bp ({yz(rj['kova']['2y_receive']['orta']['isabet'], 0)})".replace(
        "−66", sayi(rj["kova"]["2y_receive"]["orta"]["toplam"])), "W4 orta kova")

    # ───────────────────────────── 4.4 aylık tablo
    ar = o["aylik_rejim"]
    t = tablo(tl, "Ay türü (aylık ortalama değişim, bp)")
    K5 = ("2y", "5y", "7y", "2s5s", "2s7s")
    for k, s in (("indirim", "İndirim ayları"), ("sabit", "Sabit tutulan aylar"), ("artırım", "Artırım ayları"),
                 ("toplantı yok", "Toplantısız aylar")):
        x = ar["faz"][k]
        satir_sina(t, s, [str(x["n"])] + [sayi(x[c], 0, True) for c in K5], "W4 aylık")
    for k, s in (("stres", "Stres ayları (seviye +200 bp'nin üstünde)"),
                 ("ralli", "Ralli ayları (seviye −200 bp'nin altında)")):
        x = ar[k]
        satir_sina(t, s, [str(x["n"])] + [sayi(x[c], 0, True) for c in K5], "W4 aylık")
    st, ra = ar["stres"], ar["ralli"]
    metinde(mn, f"({sayi(-st['2s7s'])} / {sayi(st['2y'])}, {sayi(ra['2s7s'])} / {sayi(-ra['2y'])})", "W4 aylık oran")
    n23 = sum(1 for a in st["aylar"] if a.startswith("2023"))
    metinde(mn, f"{st['n']} stres ayı 2013'ten 2026'ya dağılıyor ve yedisi 2023'te", "W4 stres ayları")
    if n23 != 7 or not st["aylar"][0].startswith("2013") or not st["aylar"][-1].startswith("2026"):
        hatalar.append("W4 stres ayları: 2023 sayısı ya da uçlar değişti")
    metinde(mn, "son üçü " + ", ".join(ay(a) for a in st["aylar"][-3:-1]) + f" ve {ay(st['aylar'][-1])}",
            "W4 stres ayları")
    metinde(mn, "Ralli aylarının son üçü " + ", ".join(ay(a) for a in ra["aylar"][-3:-1]) +
            f" ve {ay(ra['aylar'][-1])}", "W4 ralli ayları")

    # ───────────────────────────── 4.4 dönüm noktaları
    dn = o["donum_noktalari"]
    t = tablo(tl, "PPK dönüm noktası (bp; 1 ay · 3 ay · 6 ay)")
    for d in dn:
        lab = f"{gun(d['tarih'])} {d['yon']} ({bp(d['adim_bp'], True)})"
        satir_sina(t, lab, [" · ".join(sayi(d["hareket"][a][c], 0, True) for a in ("1a", "3a", "6a"))
                            for c in ("2y", "5y", "2s5s", "2s7s")], "W4 dönüm noktası")
    if not dn[0]["arsiv_basi"] or any(d["arsiv_basi"] for d in dn[1:]):
        hatalar.append("W4 dönüm noktası: arşiv başı dipnotu ilk satıra ait değil")
    metinde(mn, f"{gun(dn[0]['tarih'])} arşivin ilk faiz değişimidir", "W4 dönüm noktası")
    ind = [d for d in dn if d["yon"] == "indirim"]
    art = [d for d in dn if d["yon"] == "artırım"]
    if not all(d["hareket"][a]["2s5s"] > 0 for d in ind for a in ("3a", "6a")):
        hatalar.append("W4 dönüm noktası: 'dört indirim dönüşünün dördünde 2s5s üç ve altı ayda dikleşti' tutmuyor")
    if sum(d["hareket"]["6a"]["2y"] < 0 for d in ind) != 2 or len(ind) != 4:
        hatalar.append("W4 dönüm noktası: '2 yıllık getiri altı ayda yalnız ikisinde düştü' tutmuyor")
    if sum(d["hareket"]["3a"]["2s5s"] < 0 for d in art) != 3 or len(art) != 4:
        hatalar.append("W4 dönüm noktası: 'dört artırım dönüşünün üçünde yataylaştı' tutmuyor")
    d21 = [d for d in dn if d["tarih"] == "2021-09-23"][0]
    d23 = [d for d in dn if d["tarih"] == "2023-06-22"][0]
    d25 = [d for d in dn if d["tarih"] == "2025-04-17"][0]
    metinde(mn, f"23.09.2021'de üç ayda {bp(d21['hareket']['3a']['2s5s'], True)}", "W4 dönüm 2021")
    metinde(mn, f"altı ayda {sayi(d21['hareket']['6a']['2y'])} bp yükselirken 2s5s ilk ayda "
                f"{sayi(d21['hareket']['1a']['2s5s'])} bp dikleşti", "W4 dönüm 2021")
    metinde(mn, f"2s7s ilk ayda {bp(d21['hareket']['1a']['2s7s'], True)} dikleşti, üç ayda "
                f"{bp(d21['hareket']['3a']['2s7s'])}'ye döndü", "W4 dönüm 2021")
    metinde(mn, f"2 yıllık {sayi(-d25['hareket']['3a']['2y'])} bp düştü, 2s5s "
                f"{sayi(d25['hareket']['3a']['2s5s'])} bp dikleşti", "W4 dönüm 2025")
    metinde(mn, f"{sayi(d25['adim_bp'])} bp'lik artırım", "W4 dönüm 2025")
    metinde(mn, f"{sayi(d23['adim_bp'])} bp'lik artırımdan sonraki ilk ayda 2s5s {sayi(d23['hareket']['1a']['2s5s'])} bp "
                f"dikleşti; yassılaşma üç ayda geldi ({bp(d23['hareket']['3a']['2s5s'])}) ve altı ayda "
                f"{bp(d23['hareket']['6a']['2s5s'])}", "W4 dönüm 2023")
    fg = o["fonlama_gecis"]["gecis"]
    pk = fg["politika>koridor_ust"]
    metinde(mn, f"fonlama {gun([x for x in pk['tarih'] if x.startswith('2025')][0])}'te koridorun tavanına", "W4 2025 tavan")
    mart = [x for x in kd["indirim_seviye_artti"] if x[0] == "2025-03"][0]
    metinde(mn, f"seviyesi Mart'ta {bp(mart[2])} yükselmişti", "W4 Mart 2025")

    # ───────────────────────────── 4.4 fonlama çıpası ve karar günü
    d20, d525 = pk["d20"], pk["d525"]
    metinde(mn, f"(dört olay) 20 iş gününde 2 yıllık {sayi(d20['n2y'], 0, True)}, 7 yıllık "
                f"{bp(d20['n7y'], True)} yükseldi: 2s7s {sayi(d20['n2y'] - d20['n7y'])} bp yataylaştı", "W4 tavan geçişi")
    if pk["n"] != 4:
        hatalar.append("W4 tavan geçişi: olay sayısı artık dört değil")
    metinde(mn, f"2 yıllık {sayi(d525['n2y'], 0, True)}, 7 yıllık {bp(d525['n7y'], True)}: 2s7s "
                f"{sayi(d525['n2y'] - d525['n7y'])} bp daha", "W4 tavan geçişi 5–25")
    c7, c5 = rj["cipa"]["2s7s_diklestirici"], rj["cipa"]["2s5s_diklestirici"]
    metinde(mn, f"ortalama {bp(c7['koridor_ust']['toplam'], True)} ({c7['koridor_ust']['n']} pencere, isabet "
                f"{yz(c7['koridor_ust']['isabet'], 0)}), 2s5s {bp(c5['koridor_ust']['toplam'], True)} "
                f"({yz(c5['koridor_ust']['isabet'], 0)})", "W4 çıpa")
    metinde(mn, f"({c7['koridor_alt']['n']} pencere; 2s7s dikleştirici {bp(c7['koridor_alt']['toplam'])})", "W4 çıpa")
    pg = o["ppk_gunu_yapi"]
    t = tablo(tl, "Spread (PPK günü, iki günlük mutlak hareket, bp)")
    for k in ("2s5s", "2s7s"):
        x = pg[k]
        satir_sina(t, k, [sayi(x["ppk_medyan"]), sayi(x["ppk_p90"]), sayi(x["diger_medyan"]), sayi(x["diger_p90"])],
                   "W4 PPK günü")
    p2 = o["ppk_gunu"]["vade"]["n2y"]["ppk_p90"]
    metinde(mn, f"90. yüzdeliği {bp(pg['2s7s']['ppk_p90'])}, **2 yıllık getirinin kendisininkinden ({bp(p2)}) büyük.**",
            "W4 PPK günü")
    if not pg["2s7s"]["ppk_p90"] > p2:
        hatalar.append("W4 PPK günü: 2s7s kuyruğu artık 2 yıllığınkinden büyük değil")

    # ───────────────────────────── 4.5 bugünkü taşıma + rejimin hareketi
    sm = o["senaryo_matrisi"]
    t = tablo(tl, "Dikleştirici, bugünkü taşıma + rejimin hareketi")
    REJ = ("indirim", "sabit", "artırım", "guvercin", "sahin", "satis", "ralli")
    for k, s in (("2s5s_diklestirici", "2s5s dikleştirici"), ("2s7s_diklestirici", "2s7s dikleştirici")):
        x = sm[k]
        satir_sina(t, s, [sayi(x["tasima_bugun"], 0, True)] +
                   [f"{sayi(x[r]['ort'], 0, True)} ({sayi(x[r]['p25'], 0, True)} · {sayi(x[r]['p75'], 0, True)})"
                    for r in REJ], "W4 senaryo")
        karsilik = {"2s5s_diklestirici": "2y5y_diklestirici", "2s7s_diklestirici": "2y7y_diklestirici"}[k]
        if x["tasima_bugun"] != to[karsilik]["tasima_bp"]:
            hatalar.append(f"W4 senaryo: {k} bugünkü taşıması taşıma/oynaklık ölçüsünden farklı")
    s5, s7 = sm["2s5s_diklestirici"], sm["2s7s_diklestirici"]
    metinde(mn, f"tarihte {bp(f7['sabit']['toplam'])} kaybettiren 2s7s dikleştirici, bugünkü "
                f"{bp(s7['tasima_bugun'], True)} taşımayla aynı hareket altında {bp(s7['sabit']['ort'], True)} kazanır; "
                f"2s5s'te {bp(s5['sabit']['ort'], True)}", "W4 senaryo sabit")
    metinde(mn, f"tarihteki {bp(d5['sahin']['toplam'])}'den {bp(s5['sahin']['ort'])}'ye iner ve üst çeyreği "
                f"{bp(s5['sahin']['p75'], True)}", "W4 senaryo şahin")
    metinde(mn, f"tarihteki {bp(-d5['sahin']['toplam'], True)} yerine {bp(-s5['sahin']['ort'], True)} kazanır",
            "W4 senaryo yassılaştırıcı")

    # ───────────────────────────── 4.5 beklenti → spread
    es = o["egim_seviye"]
    w7 = round(1 / es["beta_7y_2y"], 2)
    w5 = round(1 / es["beta_5y_2y"], 2)
    b2, b5, b7 = (bg[T]["basabas_bp"] for T in ("2", "5", "7"))
    c7r = b2 - w7 * b7
    c5r = b2 - w5 * b5
    W7 = sayi(w7, 2)
    t = tablo(tl, "Beklenti (kart) → spread")
    ag, ku7, ku5 = rj["faz"], rj["kuyruk"]["2s7s_diklestirici"], rj["kuyruk"]["2s5s_diklestirici"]
    satir_sina(t, "K1 · Gevşeme fiyatlanandan hızlı (güvercin sürpriz)",
               [None, None, None, None,
                f"2s5s dikleştirici {bp(ys['2s5s_diklestirici_bp'], True)} toplar · 2s7s dikleştirici "
                f"{bp(ys['2s7s_diklestirici_bp'], True)} toplar",
                f"güvercin: 2s5s {ti(d5['guvercin'])} · 2s7s {ti(d7['guvercin'])}", None], "W4 beklenti")
    satir_sina(t, "K2 · Gevşeme fiyatlanandan yavaş ya da duraklama",
               [None, None, None, None, f"2s5s yassılaştırıcı {bp(ys['2s5s_yassilastirici_bp'], True)} öder",
                f"şahin: 2s5s dikleştirici {ti(d5['sahin'])} · orta: {ti(d5['orta'])}",
                f"fiyatlanan indirim gelir; olay tarihine bağla — taşıma çeyrekte {sayi(-ys['2s5s_yassilastirici_bp'])} "
                f"bp yataylaşma ister"], "W4 beklenti")
    satir_sina(t, "K3 · Sıkılaşma, artırım döngüsü",
               [None, None, None, None, f"2s7s yassılaştırıcı {bp(ys['2s7s_yassilastirici_bp'], True)} öder",
                f"artırım fazı: 2s7s dikleştirici {ti(ag['2s7s_diklestirici']['artırım'])} · artırım ayları: 2s7s "
                f"{sayi(ar['faz']['artırım']['2s7s'], 0, True)}",
                f"artırım karardan önce fiyatlanmış ({gun(d25['tarih'])} sonrası üç ayda 2s7s "
                f"{sayi(d25['hareket']['3a']['2s7s'], 0, True)})"], "W4 beklenti")
    satir_sina(t, "K4 · Kur ya da risk şoku (satış kuyruğu)",
               [None, None, None, None, f"2s7s yassılaştırıcı {bp(ys['2s7s_yassilastirici_bp'], True)} öder",
                f"satış kuyruğu: 2s7s dikleştirici {ti(ku7['satis'])} · stres ayları: 2s7s "
                f"{sayi(st['2s7s'], 0, True)}",
                f"fonlama tavana yerleşti; yassılaşmanın çoğu geçişte yaşanır, rejimin içinde 2s7s dikleştirici "
                f"{sayi(c7['koridor_ust']['toplam'], 0, True)}"], "W4 beklenti")
    satir_sina(t, "K7 · Kalıcı dezenflasyon, ralli — kısa uç önde (tipik)",
               [None, None, None, None, f"2s7s dikleştirici {bp(ys['2s7s_diklestirici_bp'], True)} toplar",
                f"ralli kuyruğu: 2s7s dikleştirici {ti(ku7['ralli'])} · ralli ayları: 2s7s "
                f"{sayi(ra['2s7s'], 0, True)}", None], "W4 beklenti")
    satir_sina(t, "K7 · Kalıcı dezenflasyon — uzun uç risk primi önde düşer",
               [None, f"2y pay · 7y receive ({W7} kat DV01)", f"2 yıllığı sat · 7 yıllığı al ({W7} kat DV01)",
                f"regresyon {W7}: seviyeden arındırılmış",
                f"regresyon ağırlıklı 2s7s yassılaştırıcı {bp(-c7r, True)} öder",
                f"boğa yataylaşma ayların {yz(kd['pay']['boğa yataylaşma'], 1)}'i — en seyrek kadran",
                f"uzun uç güncel betanın dışına çıkmaz; beta kayar (son üç yılda "
                f"{sayi(es['donem']['2023-07_2026']['beta_7y_2y'], 2)})"], "W4 beklenti")
    satir_sina(t, "K8 · Vade primi, mali risk yükselir (uzun uç önde satılır)",
               [None, f"2y receive · 7y pay ({W7} kat DV01)", f"2 yıllığı al · 7 yıllığı sat ({W7} kat DV01)",
                f"regresyon {W7}: DV01-nötr hâl satışta seviye bacağıyla kaybeder",
                f"regresyon ağırlıklı 2s7s dikleştirici {bp(c7r, True)} toplar",
                f"ayı dikleşme ayların {yz(kd['pay']['ayı dikleşme'], 1)}'ı · {gun(d21['tarih'])}: bir ayda 5y "
                f"{sayi(d21['hareket']['1a']['5y'], 0, True)}, 2s7s {sayi(d21['hareket']['1a']['2s7s'], 0, True)}",
                f"kısa uç da satılır (ayı yataylaşma, ayların {yz(kd['pay']['ayı yataylaşma'], 1)}'i); beta kayar"],
               "W4 beklenti")
    if min(kd["pay"], key=kd["pay"].get) != "boğa yataylaşma":
        hatalar.append("W4 beklenti: boğa yataylaşma artık en seyrek kadran değil")
    metinde(mn, f"bugünkü taşımayla 2s7s dikleştirici {bp(s7['guvercin']['ort'], True)}, 2s5s "
                f"{bp(s5['guvercin']['ort'], True)}; satış kuyruğunda 2s7s {bp(s7['satis']['ort'])}, 2s5s "
                f"{bp(s5['satis']['ort'])}", "W4 K1 asimetri")
    metinde(mn, f"boğa dikleşme, ayların {yz(kd['pay']['boğa dikleşme'], 1)}'ü", "W4 K7")

    # ───────────────────────────── 4.5 ağırlık tablosu
    y1, s1 = o["pca"]["yuk"]["pc1"], o["pca"]["sigma_bp_ay"][0]

    def seviye_pl(w: float, uzun: str) -> float:
        return -(y1["n2y"] - w * y1[uzun]) * s1 * 1e4

    t = tablo(tl, "Dikleştirici ağırlığı (22.09.2026)")
    satir_sina(t, "2s5s, DV01-nötr", ["1,00", sayi(ys["2s5s_diklestirici_bp"], 0, True),
                                      sayi(-fm["2s5s_yassi_dv01"][0], 0, True) + " TL"], "W4 ağırlık")
    satir_sina(t, "2s5s, regresyon", [sayi(w5, 2), sayi(c5r, 0, True),
                                      "≈ " + sayi(round(seviye_pl(w5, "n5y"), -3), 0, True) + " TL"], "W4 ağırlık")
    satir_sina(t, "2s7s, DV01-nötr", ["1,00", sayi(ys["2s7s_diklestirici_bp"], 0, True),
                                      sayi(-fm["2s7s_yassi_dv01"][0], 0, True) + " TL"], "W4 ağırlık")
    satir_sina(t, "2s7s, regresyon", [sayi(w7, 2), sayi(c7r, 0, True),
                                      "≈ " + sayi(round(seviye_pl(w7, "n7y"), -3), 0, True) + " TL"], "W4 ağırlık")
    metinde(mn, f"${sayi(b2).replace('−', '-')} + {W7.replace(',', '{,}')} \\times {sayi(-b7)} \\approx "
                f"{sayi(c7r, 0, True)}$", "W4 ağırlık taşıma")
    metinde(mn, f"$-({str(y1['n2y']).replace('.', '{,}')} - {W7.replace(',', '{,}')} \\times "
                f"{str(y1['n7y']).replace('.', '{,}')}) \\times {sayi(s1, 1).replace(',', '{,}')} \\times 10.000 "
                f"\\approx {sayi(seviye_pl(w7, 'n7y') / 1e3, 0, True)}$", "W4 ağırlık seviye")
    metinde(mn, f"+48'den {bp(c7r, True)}'ye".replace("+48", sayi(ys["2s7s_diklestirici_bp"], 0, True)), "W4 ağırlık")
    metinde(mn, f"7 yılda receive DV01 başına {bp(to['7y_receive']['tasima_bp'])} öder, pay aynı "
                f"{bp(-to['7y_receive']['tasima_bp'])}'yi toplar", "W4 ağırlık 7y")
    metinde(mn, f"regresyon ağırlıklı 2s7s yassılaştırıcı çeyrekte {bp(-c7r, True)} öder", "W4 ağırlık")
    b42 = es["donem"]["2023-07_2026"]["beta_7y_2y"]
    metinde(mn, f"$\\beta_{{7y\\mid 2y}}$ {sayi(b42, 2)} (4.3); bu betayla oran yaklaşık {sayi(1 / b42, 1)}", "W4 beta")
    metinde(mn, f"2s5s'te {sayi(w5, 2)}, 2s7s'te {W7}", "W4 regresyon oranları")
    metinde(mn, f"seviye riskinin yaklaşık {yz(100 * fm['2s7s_yassi_dv01'][0] / -fm['2y_uzun'][0], 0)}'sini taşır",
            "W4 gizli boğa")

    # ───────────────────────────── 4.5 stres tablosu ve stop
    ysr = o["yapi_stres"]
    t = tablo(tl, "Spread (aylık hareket, bp)")
    for k in ("1y2y", "2s5s", "2s7s", "5s7s"):
        x = ysr[k]
        satir_sina(t, k, [sayi(x["sigma"]), sayi(x["sigma36"]),
                          f"{sayi(x['en_buyuk_artis'][0], 0, True)} ({ay(x['en_buyuk_artis'][1])})",
                          f"{sayi(x['en_buyuk_dusus'][0], 0, True)} ({ay(x['en_buyuk_dusus'][1])})",
                          sayi(x["p95"])], "W4 spread stresi")
    a5, a7, a1, a57 = ysr["2s5s"], ysr["2s7s"], ysr["1y2y"], ysr["5s7s"]
    metinde(mn, f"2s5s'te {sayi(a5['sigma36'])}, 2s7s'te {sayi(a7['sigma36'])} bp — tam örneklemin "
                f"({sayi(a5['sigma'])}, {sayi(a7['sigma'])}) bir buçuk katı", "W4 stres σ")
    for x in (a5, a7):
        if not 1.4 <= x["sigma36"] / x["sigma"] <= 1.65:
            hatalar.append("W4 stres: σ36/σ oranı artık 'bir buçuk kat' değil")
    metinde(mn, f"{sayi(a1['sigma36'])}'e {sayi(a1['sigma'])}, yaklaşık {sayi(a1['sigma36'] / a1['sigma'], 1)} kat",
            "W4 stres 1y2y")
    metinde(mn, f"en büyük aylık düşüşü {bp(a7['en_buyuk_dusus'][0])} ({ay(a7['en_buyuk_dusus'][1])})", "W4 stres 2s7s")
    metinde(mn, f"95. yüzdeliği ({bp(a7['p95'])}) yaklaşık dokuz çeyreği", "W4 stres 2s7s")
    if round(a7["p95"] / ys["2s7s_diklestirici_bp"]) != 9 or int(a7["en_buyuk_dusus"][0] / -ys["2s7s_diklestirici_bp"]) != 10:
        hatalar.append("W4 stres: 'dokuz' ya da 'on çeyreğinden fazlası' artık tutmuyor")
    metinde(mn, f"2s5s'te {bp(a5['en_buyuk_dusus'][0])} ({ay(a5['en_buyuk_dusus'][1])}) ve {bp(a5['p95'])}",
            "W4 stres 2s5s")
    metinde(mn, f"σ {bp(a57['sigma'])}, 95. yüzdelik {bp(a57['p95'])}", "W4 stres 5s7s")
    metinde(mn, f"{ay(a57['en_buyuk_artis'][1])}'te {bp(a57['en_buyuk_artis'][0], True)} dikleşti", "W4 stres 5s7s")
    metinde(mn, f"Bugün 5s7s dikleştirici {bp(to['5y7y_diklestirici']['tasima_bp'])} öder", "W4 5s7s taşıma")
    if not 0.25 < ys["2s5s_diklestirici_bp"] / a5["sigma36"] < 0.33:
        hatalar.append("W4 stop: 2s5s taşıması / σ36 artık 'dörtte birinden biraz fazla' değil")

    # ───────────────────────────── masa ve pratik
    metinde(mn, f"receive'in isabeti {yz(r2['isabet'], 0)}, güvercin sürprizde {yz(g2['isabet'], 0)}", "W4 masa")
    fi7 = f7["indirim"]
    metinde(mn, f"Ortalama **{bp(fi7['toplam'], True)}**, isabet **{yz(fi7['isabet'], 0)}**, "
                f"{fi7['n']} pencere; hareketin çeyrekler arası aralığı {sayi(fi7['hareket_p25'], 0, True)} · "
                f"{sayi(fi7['hareket_p75'], 0, True)} bp", "W4 pratik 2")
    metinde(mn, f"${fi7['n']}/3 \\approx {round(fi7['n'] / 3)}$", "W4 pratik 2")
    metinde(mn, f"2 yıllık receive'in isabeti aynı fazda **{yz(r2['isabet'], 0)}**", "W4 pratik 2")
    metinde(mn, f"Şahin kovada 2s7s dikleştirici **{bp(d7['sahin']['toplam'])}**, isabet "
                f"**{yz(d7['sahin']['isabet'], 0)}**", "W4 pratik 2")
    metinde(mn, f"**{bp(s7['sahin']['ort'])}**'ye indirir (çeyrekler arası {sayi(s7['sahin']['p25'])} · "
                f"{sayi(s7['sahin']['p75'], 0, True)})", "W4 pratik 2")
    metinde(mn, f"2s7s dikleştirici **{bp(d7['guvercin']['toplam'], True)}**, isabet **{yz(d7['guvercin']['isabet'], 0)}**; "
                f"bugünkü taşımayla **{bp(s7['guvercin']['ort'], True)}** ({sayi(s7['guvercin']['p25'], 0, True)} · "
                f"{sayi(s7['guvercin']['p75'], 0, True)})", "W4 pratik 2")
    for k, s, sm_, a_ in (("2s5s_diklestirici", "2s5s", s5, a5), ("2s7s_diklestirici", "2s7s", s7, a7)):
        h = rj["kuyruk"][k]["satis"]
        c = sm_["tasima_bugun"]
        metinde(mn, f"{s} dikleştirici **{bp(c, True)}** toplar; " + ("satış kuyruğunda " if s == "2s5s" else "") +
                f"hareket {bp(h['hareket'])}", "W4 pratik 3")
        metinde(mn, f"${sayi(-h['hareket'])}/{sayi(c)} \\approx {sayi(-h['hareket'] / c, 1)}$ çeyrek", "W4 pratik 3")
        metinde(mn, f"${sayi(-a_['en_buyuk_dusus'][0])}/{sayi(c)} \\approx {sayi(-a_['en_buyuk_dusus'][0] / c, 1)}$ çeyrek",
                "W4 pratik 3")
    metinde(mn, f"Güvercin: 2s5s **{bp(s5['guvercin']['ort'], True)}**, 2s7s **{bp(s7['guvercin']['ort'], True)}**. "
                f"Satış kuyruğu: 2s5s **{bp(s5['satis']['ort'])}**, 2s7s **{bp(s7['satis']['ort'])}**", "W4 pratik 3")
    metinde(mn, f"${sayi(s5['guvercin']['ort'])}/{sayi(-s5['satis']['ort'])} \\approx "
                f"{sayi(s5['guvercin']['ort'] / -s5['satis']['ort'], 1)}$", "W4 pratik 3")
    metinde(mn, f"${sayi(s7['guvercin']['ort'])}/{sayi(-s7['satis']['ort'])} \\approx "
                f"{sayi(s7['guvercin']['ort'] / -s7['satis']['ort'], 1)}$", "W4 pratik 3")
    metinde(mn, f"yassılaştırıcı için büküm {sayi(fm['2s5s_yassi_dv01'][2], 0, True)} TL, seviye "
                f"{sayi(fm['2s5s_yassi_dv01'][0], 0, True)} TL", "W4 pratik 3")
    metinde(mn, f"roll parçası ({sayi(rb['n2y'] - rb['n5y'], 0, True)} bp)", "W4 pratik 3")
    metinde(mn, f"$\\beta_{{2y\\mid 7y}} = {sayi(es['beta_2y_7y'], 2).replace(',', '{,}')}$", "W4 pratik 1")

    # ───────────────────────────── figür
    metinde(mn, 'src="/arastirma/kagit-ve-ois-trading/11_rejim_haritasi.html"', "W4 Şekil 11")
    for eski, yeni in (("04_pca", "08_pca"), ("05_kadran", "09_kadran"), ("06_egim_seviye", "10_egim_seviye")):
        metinde(mn, f'src="/arastirma/kagit-ve-ois-trading/{yeni}.html"', "W4 figür adı")
        if f"{eski}.html" in m:
            hatalar.append(f"W4: eski figür adı kaldı: {eski}")


# ─────────────────────────────────────────────────────────────── tek başına sınama


# W5_dogrula
def kontrol_w5(o, m, tl):
    import math
    import re

    mn = " ".join(m.split())

    def M(parca, ad):
        metinde(mn, parca, "W5 " + ad)

    def iddia(kosul, ad):
        """Metindeki nitel bir hükmün (işaret, sıralama, sayım) ölçümle tutarlılığı."""
        sayac["metin"] += 1
        if not kosul:
            hatalar.append(f"W5 hüküm ölçümle çelişiyor: {ad}")

    def n0(x):
        return sayi(x, 0, True)

    def kx(x, b=3):
        """KaTeX içindeki sayı: eksi ASCII tire (metinde() virgülü {,}'ye kendisi çevirir)."""
        return sayi(x, b).replace("−", "-")

    def kxk(x, b=3):
        """KaTeX yazımı hazır: virgül {,} olarak (parçada başka virgül varsa)."""
        return kx(x, b).replace(",", "{,}")

    def f0(x, b=2):
        return "0" if abs(x) < 0.5 * 10 ** (-b) else sayi(x, b, True)

    fh = o["fly_tasima_haritasi"]
    F = fh["fly"]
    ys = o["yapi_tasima"]
    kl = o["kalicilik"]
    kt = o["katalog"]
    fp = o["fly_pnl_ayrisimi"]
    rj = o["rejim_yapi"]
    ar = o["aylik_rejim"]
    bk = o["barbell_kurallar"]
    bb = o["barbell"]
    of = o["ois_fly"]
    ff = o["fly_tasima_filtresi"]
    ie = o["ihale_etkisi"]
    pc = o["pca"]
    V1, V2, V3 = pc["yuk"]["pc1"], pc["yuk"]["pc2"], pc["yuk"]["pc3"]
    SG = pc["sigma_bp_ay"]
    od = o["fly_orneklem_disi"]["ayrik"]["pca"]
    tm = o["tumsek"]
    f1 = o["fly_1y2y5y"]
    yb = o["yapi_bugun"]

    # ───────────────────────── kapsam: bu parçanın metni (Bölüm 5 başından 5.5'e kadar)
    bas = m.find("## Bölüm 5 —")
    iddia(bas >= 0, "Bölüm 5 başlığı yok")
    sonraki = re.search(r"(?m)^(?:## |### (?!5\.[1-4] ))", m[bas + 1:])
    parca5 = m[bas: bas + 1 + sonraki.start() if sonraki else len(m)]
    for s, no in (("12_fly_agirlik", "12"), ("13_fly_ayrisim", "13"), ("14_fly_haritasi", "14")):
        iddia(f'src="/arastirma/kagit-ve-ois-trading/{s}.html"' in parca5 and f'no="{no}"' in parca5,
              f"figür {s} (no {no}) Bölüm 5.1–5.4'te gömülü değil")
    for bas_, ad in (("### 5.1 ", "5.1"), ("### 5.2 ", "5.2"), ("### 5.3 ", "5.3"), ("### 5.4 ", "5.4")):
        iddia(bas_ in parca5, f"alt başlık {ad} yok")
    iddia("<FlyAgirlikHesaplayici />" in parca5, "fly ağırlık aracı 5.3'te yerinde değil")
    # yön dili: çıplak "fly'ı al/sat", "gövdeyi alan", eski short işaretli taşıma tablosu yok
    iddia(not re.search(r"[Ff]ly'ı\s+(?:al|sat)", parca5), "çıplak 'fly'ı al/sat' ifadesi")
    iddia(not re.search(r"[Gg]övdeyi\s+alan", parca5), "'gövdeyi alan' ifadesi (yön sözlüğü dışı)")
    iddia("Ağırlık | Gövde DV01'i başına taşıma + roll" not in m, "eski short işaretli fly taşıma tablosu duruyor")

    # ───────────────────────── Bölüm 5 girişi
    M(f"varyansının yalnız {yz(pc['pay'][2], 1)}'sı", "giriş büküm payı")
    M(f"yarı ömrü {sayi(kl['seri']['flyPCA']['yari_omur_ay'], 1)} ay, 2 yıllık getirininki "
      f"{sayi(kt['2y']['yari_omur_ay'], 1)} ay", "giriş yarı ömür")
    M(f"işlem başına {bp(od['net_ort'], True, 1)}, tek işlemin standart sapması {bp(od['net_sd'], b=1)}",
      "giriş örneklem dışı")
    l50, lp = F["2y5y7y_50"]["tasima_long_bp"], F["2y5y7y_pca"]["tasima_long_bp"]
    m50, mp = F["1y2y5y_50"]["tasima_long_bp"], F["1y2y5y_pca"]["tasima_long_bp"]
    iddia(l50 == ys["fly50_long_bp_govde_dv01"] and lp == ys["flyPCA_long_bp"], "iki taşıma ölçüsü tutarlı (2y5y7y)")
    iddia(m50 == -f1["tasima_50_bp"] and mp == -f1["tasima_pca_bp"], "iki taşıma ölçüsü tutarlı (1y2y5y)")
    M(f"gövde DV01'i başına {bp(l50, True)} (50:50) ve {bp(lp, True)} (PCA) toplar", "giriş taşıma")
    M(f"long 1y2y5y ise {sayi(m50, 0)} ve {bp(mp)} öder", "giriş taşıma")
    ts = F["2y5y7y_50"]["tasima_sigma"]
    iddia(0.28 <= ts <= 0.38 and 0.28 <= F["2y5y7y_pca"]["tasima_sigma"] <= 0.38, "taşıma = oynaklığın üçte biri")
    t1 = ff["1y2y5y"]["tasima"]
    M(f"({bp(t1['ort'], True, 1)}, t {sayi(t1['t'], 1)}; 3.6)", "giriş taşıma kuralı")
    for f_ in ("2y5y7y", "3y5y7y", "2y3y5y"):
        iddia(abs(ff[f_]["tasima"]["t"]) < 2, f"taşıma kuralı yalnız 1y2y5y'de kenar ({f_})")
    ks = rj["kuyruk"]["1y2y5y_long50"]["satis"]
    M(f"ortalama {bp(ks['toplam'], True)} kazandı", "giriş satış kuyruğu")
    M(f"artırım fazındaki çeyreklerde {bp(rj['faz']['2y5y7y_long50']['artırım']['toplam'])} kaybetti",
      "giriş artırım")
    i5 = ie["5y"]["pca"]
    M(f"ortalama {bp(i5['once_ort'], True, 1)} hareket etti (t {sayi(i5['once_t'], 2)}; 5.10)", "giriş ihale")
    iddia(ie["5y"]["fly"] == "3y5y7y", "ihale fly'ı 3y5y7y")

    # ───────────────────────── 5.1 yön tablosu
    q57 = 2 * V1["n5y"] - V1["n2y"] - V1["n7y"]
    q25 = 2 * V1["n2y"] - V1["n1y"] - V1["n5y"]

    def yon(x):
        return "boğa: faiz düşünce kazanır" if x < 0 else "ayı: faiz yükselince kazanır"

    t = tablo(tl, "Dil (fly'ın iki yönü)")
    satir_sina(t, "2y5y7y, 50:50 ağırlığın gizli yönü", [yon(q57), yon(-q57)], "W5 yön tablosu")
    satir_sina(t, "1y2y5y, 50:50 ağırlığın gizli yönü", [yon(q25), yon(-q25)], "W5 yön tablosu")
    satir_sina(t, "2y5y7y taşıma + roll, 50:50 · PCA (bp)", [f"{n0(l50)} · {n0(lp)}", f"{n0(-l50)} · {n0(-lp)}"],
               "W5 yön tablosu")
    satir_sina(t, "1y2y5y taşıma + roll, 50:50 · PCA (bp)", [f"{n0(m50)} · {n0(mp)}", f"{n0(-m50)} · {n0(-mp)}"],
               "W5 yön tablosu")
    M(f"$-{kx(abs(q57))}$", "5.1 seviye yükü 2y5y7y")
    M(f"$+{kx(q25)}$", "5.1 seviye yükü 1y2y5y")
    iddia(q57 < 0 < q25, "gizli yön işaretleri")

    # birim
    s50 = F["2y5y7y_50"]["sigma_bp_ay"]
    iddia(abs(kt["2y5y7y"]["sigma_bp_ay"] / 2 - s50) <= 1, "kotasyon σ'sı = 2 × P&L σ'sı")
    M(f"aylık oynaklığı kotasyonda {bp(kt['2y5y7y']['sigma_bp_ay'])}, gövde DV01'i başına {bp(s50)}", "5.1 birim σ")
    M(f"gövde DV01'i başına {bp(ys['fly50_long_bp_govde_dv01'], True)}, kotasyon cinsinden "
      f"{bp(ys['fly50_long_bp_fly'], True)} (yuvarlamayla)", "5.1 birim taşıma")
    M(f"$F = y_5 - {kxk(kl['agirlik_pca'][0])}\\,y_2 - {kxk(kl['agirlik_pca'][1])}\\,y_7$", "5.1 PCA F")

    # kâğıt anatomisi
    pv = 100 / (1 + o["bugun"]["egri"]["n5y"] / 100) ** 5
    D = 2 * bk["5050"]["kanat_dv01"][0]
    iddia(abs(D - pv * 1e6 * bb["mod_dur"]["5y"] * 1e-4) < 10, "gövde DV01'i = piyasa değeri × durasyon")
    iddia(abs(sum(bk["nakit"]["kanat_dv01"]) - D) <= 2, "nakit + durasyon nötr: kanat DV01 toplamı = gövde")
    M(f"(piyasa değeri {sayi(pv, 1)} mn TL, DV01'i {sayi(D)} TL/bp)", "5.1 gövde")
    t = tablo(tl, "Long 2y5y7y kâğıtta: kural (100 mn TL 5 yıllık gövde satılır)")
    for k, s in (("nakit", "Nakit + durasyon nötr"), ("5050", "50:50 DV01"), ("pca", "PCA-nötr")):
        x = bk[k]
        nakit = "0" if abs(x["net_nakit_mn"]) < 0.05 else sayi(x["net_nakit_mn"], 1)
        satir_sina(t, s, [f"{sayi(x['kanat_nominal_mn'][0], 1)} · {sayi(x['kanat_nominal_mn'][1], 1)}", nakit,
                          sayi(x["tasima_mn"], 2, True), sayi(x["konv_mn"], 2, True)] +
                   [f0(v) for v in x["faktor_mn"]], "W5 kâğıt anatomisi")
    t50b = round(bk["5050"]["tasima_mn"] * 1e6 / D)
    tpb = round(bk["pca"]["tasima_mn"] * 1e6 / D)
    iddia(t50b == ys["fly50_long_bp_govde_dv01"] and tpb == ys["flyPCA_long_bp"], "mn TL taşıma / gövde DV01 = bp")
    M(f"50:50'nin {sayi(bk['5050']['tasima_mn'], 2, True)} mn'u ≈ {bp(t50b, True)}, PCA'nın "
      f"{sayi(bk['pca']['tasima_mn'], 2, True)} mn'u ≈ {bp(tpb, True)}", "5.1 taşıma çevirisi")
    M(f"şokunda {sayi(bk['nakit']['faktor_mn'][0], 2, True)} mn, taşımasının neredeyse tamamı", "5.1 nakit gizli ayı")
    iddia(0.8 <= bk["nakit"]["faktor_mn"][0] / bk["nakit"]["tasima_mn"] <= 1.0, "seviye ≈ taşımanın tamamı")
    M(f"({sayi(bk['5050']['faktor_mn'][0], 2)} mn) ve bu eğride konveksitesi bile eksidir "
      f"({sayi(bk['5050']['konv_mn'], 2)} mn)", "5.1 50:50 gizli boğa")
    k2 = bb["konveksite"]["2y"] / bb["mod_dur"]["2y"]
    k7 = bb["konveksite"]["7y"] / bb["mod_dur"]["7y"]
    k5 = bb["konveksite"]["5y"] / bb["mod_dur"]["5y"]
    M(f"({sayi(k2, 2)}'e karşı {sayi(k7, 2)})", "5.1 konveksite / durasyon")
    M(f"ortalamaları ({sayi((k2 + k7) / 2, 2)}) bullet'ınkine ({sayi(k5, 2)})", "5.1 konveksite / durasyon")
    iddia((k2 + k7) / 2 < k5 and 0.3 <= k2 / k7 <= 0.37, "50:50 konveksitesi bullet'ın altında; oran üçte bir")
    M(f"kalan risk büküm ({sayi(bk['pca']['faktor_mn'][2], 2)} mn) ve taşıma ({sayi(bk['pca']['tasima_mn'], 2, True)} mn)",
      "5.1 PCA")

    # OIS
    g = of["2y5y7y"]
    x5, xp = g["5050"], g["pca"]
    M(f"(gövde DV01'i {sayi(g['govde_dv01'])} TL/bp)", "5.1 OIS DV01")
    M(f"2 yılda {sayi(x5['nominal_mn']['2y'], 1)} mn, 7 yılda {sayi(x5['nominal_mn']['7y'], 1)} mn receive", "5.1 OIS")
    M(f"{sayi(x5['nominal_mn']['2y'] + x5['nominal_mn']['7y'], 0)} mn receive'e karşı "
      f"{sayi(x5['nominal_mn']['5y'], 0)} mn pay", "5.1 OIS")
    iddia(abs((x5["nominal_mn"]["2y"] + x5["nominal_mn"]["7y"] - x5["nominal_mn"]["5y"]) + x5["net_yuzen_mn"]) < 0.11,
          "net yüzen = kanat nominalleri − gövde")
    M(f"net {sayi(-x5['net_yuzen_mn'], 1)} mn TL TLREF ödemek", "5.1 OIS net yüzen")
    M(f"fly çeyrekte {sayi(-x5['tlref_100_etkisi_bin'])} bin TL kaybeder", "5.1 OIS fixing")
    M(f"kanatlar {sayi(xp['nominal_mn']['2y'], 1)} ve {sayi(xp['nominal_mn']['7y'], 1)} mn, net yüzen bacak "
      f"{sayi(-xp['net_yuzen_mn'], 1)} mn", "5.1 OIS PCA")
    M(f"çeyreklik bedeli {sayi(-xp['tlref_100_etkisi_bin'])} bin TL", "5.1 OIS PCA fixing")
    M(f"50:50'de {sayi(-of['1y2y5y']['5050']['net_yuzen_mn'], 1)}, PCA'da "
      f"{sayi(-of['1y2y5y']['pca']['net_yuzen_mn'], 1)} mn", "5.1 OIS 1y2y5y")
    M(f"(50:50'de {sayi(bk['5050']['net_nakit_mn'], 1)} mn)", "5.1 kâğıt net nakit")

    # günlük P&L: faktör duyarlılığı
    c57 = V1["n5y"] - 0.5 * V1["n2y"] - 0.5 * V1["n7y"]
    iddia(round(c57, 3) == fp["2y5y7y_50"]["c"][0], "c₁ yüklerden türer")
    M(f"{kx(V1['n5y'], 4)} - 0,5 \\times {kx(V1['n2y'], 4)} - 0,5 \\times {kx(V1['n7y'], 4)} = "
      f"{kx(fp['2y5y7y_50']['c'][0])}", "5.1 c₁ türetimi")
    t = tablo(tl, "Long fly'ın faktör duyarlılığı (gövde DV01'i başına)")
    for k, s in (("2y5y7y_50", "2y5y7y 50:50"), ("2y5y7y_pca", "2y5y7y PCA"), ("1y2y5y_50", "1y2y5y 50:50"),
                 ("1y2y5y_pca", "1y2y5y PCA")):
        c = fp[k]["c"]
        sok = [c[i] * SG[i] for i in range(3)]
        satir_sina(t, s, [sayi(c[0], 3), sayi(c[1], 3), sayi(c[2], 3)] +
                   ["0" if abs(round(x)) < 1 else n0(x) for x in sok], "W5 faktör duyarlılığı")
        for i, ad in enumerate(("seviye", "egim", "bukum")):
            iddia(abs(abs(round(sok[i])) - fp[k]["sd"][ad]) <= 1, f"1σ şoku = parça sd'si ({k} {ad})")
    M(f"seviye {sayi(SG[0], 1)} · eğim {sayi(SG[1], 1)} · büküm {sayi(SG[2], 1)} bp", "5.1 faktör σ")
    fm = o["faktor_maruziyet"]["fly50_long"]
    M(f"{sayi(fm[0])} ve {sayi(fm[2])} TL eder", "5.1 faktör TL")
    iddia(abs(fm[0] - fp["2y5y7y_50"]["c"][0] * SG[0] * 1e4) < 2000, "faktör TL = c × σ × 10.000")
    c25 = fp["1y2y5y_50"]["c"]
    M(f"seviyede {n0(c25[0] * SG[0])}, eğimde {n0(c25[1] * SG[1])}, bükümde {n0(c25[2] * SG[2])} bp",
      "5.1 1y2y5y duyarlılık")

    # ───────────────────────── 5.2
    M(f"fly'ı {bp(bb['fly_seviye_bp'])}, ama 5 yıllığın 2–7 yıl kirişine uzaklığı yalnız "
      f"**{bp(bb['kiris_fark_bp'])}**", "5.2 kiriş")
    iddia(bb["fly_seviye_bp"] == yb["fly50"]["seviye"], "kiriş paragrafı: fly seviyesi")
    iddia(all(abs(F[k]["z36"]) < 1 for k in F if k.endswith("_pca")), "bugün hiçbir PCA fly'da |z| ≥ 1 yok")
    M("Bugün hiçbir PCA fly'da |z| ≥ 1 yok", "5.2 z")
    M(f"**{bp(kt['1y2y5y']['seviye'], True)}** — örneklemin %{sayi(kt['1y2y5y']['yuzdelik'])}'inden yüksek",
      "5.2 1y2y5y")
    M(f"artırım fazındaki çeyreklerde ortalama {bp(rj['faz']['1y2y5y_long50']['artırım']['toplam'], True)} kazandı",
      "5.2 1y2y5y artırım")
    M(f"short 1y2y5y çeyrekte gövde DV01'i başına {bp(-m50, True)} (50:50) ve {bp(-mp, True)} (PCA) toplar",
      "5.2 short 1y2y5y taşıma")
    M(f"(teklif/satış {sayi(o['ihale']['sabit_2024']['5y']['tso_medyan'], 2)})", "5.2 teklif/satış")
    M(f"ortalama {bp(i5['once_ort'], True, 1)} (t {sayi(i5['once_t'], 2)}; 5.10)", "5.2 ihale öncesi")
    M(f"ortalama {bp(i5['sonra_ort'], b=1)} (t {sayi(i5['sonra_t'], 2)}; 5.10)", "5.2 ihale sonrası")
    iddia(i5["once_ort"] > 0 > i5["sonra_ort"] and abs(i5["once_t"]) < 2 and abs(i5["sonra_t"]) < 2,
          "ihale: yön destekliyor ama zayıf")
    ob = o["oynaklik_barbell"]
    M(f"ortalama {bp(ob['2y5y7y_long50']['yuksek']['toplam'])} (50:50) ve {bp(ob['2y5y7y_longpca']['yuksek']['toplam'])}"
      f" (PCA) getirdi ({ob['2y5y7y_long50']['yuksek']['n']} pencere; 5.8)", "5.2 oynaklık")
    M(f"kotasyonda {bp(kt['2y5y7y']['sigma_bp_ay'])}, yani gövde DV01'i başına {bp(s50)}; PCA ağırlıklı hâli "
      f"{bp(kl['seri']['flyPCA']['sigma_bp_ay'])} — 2 yıllık getirinin {sayi(kl['seri']['2y']['sigma_bp_ay'])} bp'sine",
      "5.2 fly oynaklığı")
    st = o["yapi_stres"]["1y2y5y_pca"]["en_buyuk_artis"]
    M(f"en kötü ayı gövde DV01'i başına {bp(-st[0])}'ydi ({ay(st[1])})", "5.2 en kötü ay")
    iddia(7 <= st[0] / (-mp) <= 8, "yedi–sekiz çeyreklik taşıma")
    iddia(fh["roll_bp"]["n2y"] > 0 > fh["roll_bp"]["n5y"], "tepe 2 yıl, 5 yıl inen yamaç")

    # ───────────────────────── 5.3
    a, b_ = kl["agirlik_pca"]
    M(f"$a = {sayi(a, 3).replace(',', '{,}')}$, $b = {sayi(b_, 3).replace(',', '{,}')}$", "5.3 PCA ağırlığı")
    M(f"gövde DV01'inin {sayi(0.5 - a, 3)}'sı kadar pay (0,5 − {sayi(a, 3)})", "5.3 kanat düzeltmesi")
    M(f"{sayi(b_ - 0.5, 3)}'i kadar receive ({sayi(b_, 3)} − 0,5)", "5.3 kanat düzeltmesi")
    iddia(abs((0.5 - a) - (b_ - 0.5)) < 0.02, "düzeltme bacağı hemen hemen DV01-nötr")
    t = tablo(tl, "| 50:50 fly | PCA-nötr fly")
    satir_sina(t, "Aylık oynaklık, gövde DV01'i başına (P&L birimi)",
               [bp(fp["2y5y7y_50"]["sigma"]), bp(fp["2y5y7y_pca"]["sigma"])], "W5 fly kıyası")
    iddia(fp["2y5y7y_pca"]["sigma"] == kl["seri"]["flyPCA"]["sigma_bp_ay"], "PCA σ iki ölçüde aynı")
    s50p, spp = fp["2y5y7y_50"]["sigma"], fp["2y5y7y_pca"]["sigma"]
    M(f"aynı birimde fark {sayi(s50p)}'e karşı {sayi(spp)} bp", "5.3 birim farkı")
    iddia(0.2 <= 1 - spp / s50p <= 0.3, "oynaklık dörtte bir azalır")
    M(f"varyansı {yz(100 * (1 - (spp / s50p) ** 2), 0)} azaltır", "5.3 varyans")
    M(f"(${kxk(fp['2y5y7y_50']['c'][2])}$'a karşı ${kxk(fp['2y5y7y_pca']['c'][2])}$, 5.1)", "5.3 büküm duyarlılığı")
    iddia(1.8 <= fp["2y5y7y_50"]["c"][2] / fp["2y5y7y_pca"]["c"][2] <= 2.2, "büküm duyarlılığı iki kat")
    iddia(V3["n2y"] > 0 > V3["n7y"], "2 yıl büküm yukarı, 7 yıl aşağı yüklü")
    M(f"(yarı ömür {sayi(kl['seri']['fly50']['yari_omur_ay'], 1)}'dan {sayi(kl['seri']['flyPCA']['yari_omur_ay'], 1)}"
      f" aya)", "5.3 yarı ömür")

    # geçmiş 60 aylık ağırlık
    p57, p25 = fp["2y5y7y_pca60"], fp["1y2y5y_pca60"]
    M(f"(her ay yeniden tahmin, {p57['n']} ay)", "5.3 60 ay başlık")
    M(f"2018–2026'daki {p57['n']} ayda", "5.3 60 ay")
    iddia(p57["n"] == len(range(60, o["pca"]["n"])), "60 aylık pencere 2018-02'de başlar")
    t = tablo(tl, "Geçmiş 60 ayla kurulan PCA fly (her ay yeniden tahmin")
    for x, x50, s in ((p57, fp["2y5y7y_50"], "2y5y7y, 60 aylık pencere"), (p25, fp["1y2y5y_50"], "1y2y5y, 60 aylık pencere")):
        satir_sina(t, s, [f"{sayi(x['a_aralik'][0], 2)}–{sayi(x['a_aralik'][1], 2)}",
                          f"{sayi(x['b_aralik'][0], 2)}–{sayi(x['b_aralik'][1], 2)}",
                          f"{sayi(x['son'][0], 3)} · {sayi(x['son'][1], 3)}",
                          sayi(x["korelasyon_seviye"], 2), sayi(x["korelasyon_egim"], 2),
                          sayi(x50["korelasyon_seviye_60"], 2)], "W5 60 aylık ağırlık")
    M(f"aylık değişiminin medyanı {sayi(p57['a_aylik_degisim_medyan'], 3)}; ama {p57['n']} ayda "
      f"{sayi(p57['a_aralik'][0], 2)} ile {sayi(p57['a_aralik'][1], 2)} arasında", "5.3 ağırlık kayması")
    v_pca = round(100 * p57["korelasyon_seviye"] ** 2)
    v_50 = round(100 * fp["2y5y7y_50"]["korelasyon_seviye_60"] ** 2)
    M(f"seviyenin açıkladığı varyans %{v_pca}, aynı aylarda 50:50'de %{v_50}", "5.3 örneklem dışı sızıntı")
    iddia(1.5 <= v_50 / v_pca <= 2.5, "sızıntı yarıya iner")
    iddia(v_50 == fp["2y5y7y_50"]["pay"]["seviye"], "50:50 seviye payı = korelasyonun karesi")
    M(f"eğime {sayi(p57['korelasyon_egim'], 2)}'lik yeni bir sızıntı", "5.3 eğim sızıntısı")
    M(f"Seviye korelasyonu {sayi(p25['korelasyon_seviye'], 2)}, ama eğim korelasyonu {sayi(p25['korelasyon_egim'], 2)}"
      f" (50:50'de {sayi(fp['1y2y5y_50']['korelasyon_egim_60'], 2)})", "5.3 1y2y5y eğim")

    # iki hüküm: hüküm sütunları yüzdelikten türer
    def hukum(y):
        return "gövde ucuz: short fly" if y >= 50 else "gövde pahalı: long fly"

    t = tablo(tl, "Fly (22.09.2026)")
    satir_sina(t, "2y5y7y (gövde 5 yıl)", [None, None, hukum(yb["fly50"]["yuzdelik"]), hukum(yb["flyPCA"]["yuzdelik"])],
               "W5 iki hüküm")
    satir_sina(t, "1y2y5y (gövde 2 yıl)", [None, None, hukum(kt["1y2y5y"]["yuzdelik"]), hukum(f1["yuzdelik"])],
               "W5 iki hüküm")
    M(f"$2 \\times {kx(V1['n5y'], 4)} - {kx(V1['n2y'], 4)} - {kx(V1['n7y'], 4)} = -{kx(abs(q57))}$", "5.3 seviye yükü")
    M(f"$2 \\times {kx(V1['n2y'], 4)} - {kx(V1['n1y'], 4)} - {kx(V1['n5y'], 4)} = +{kx(q25)}$", "5.3 seviye yükü")

    # fly'ın taşıması (LONG işaretle)
    t = tablo(tl, "Long 2y5y7y, ağırlık")
    fl50, flf, flp = ys["fly50_long_bp_govde_dv01"], ys["fly50_long_bp_fly"], ys["flyPCA_long_bp"]
    satir_sina(t, "50:50", [f"{bp(fl50, True)} (fly kotasyonu cinsinden {bp(flf, True)})",
                            f"gövde kanatlarına göre çeyrekte {sayi(fl50)} bp'den fazla pahalılaşmazsa (kotasyon "
                            f"{sayi(flf)} bp'den fazla düşmezse) kazanır"], "W5 fly taşıması")
    satir_sina(t, "PCA-nötr", [bp(flp, True), f"PCA $F$'si çeyrekte {sayi(flp)} bp'den fazla düşmezse kazanır"],
               "W5 fly taşıması")
    iddia(fl50 > 0 and flp > 0 and flf > 0, "long 2y5y7y taşır (işaret)")
    be = fh["basabas_bp"]
    M(f"(Gövde 5 yıl, başabaşı {bp(be['n5y'])}; kanatlar 2 yıl {bp(be['n2y'])} ve 7 yıl {bp(be['n7y'])}.", "5.3 başabaşlar")
    iddia(round(-(be["n5y"] - 0.5 * be["n2y"] - 0.5 * be["n7y"])) == fl50, "50:50 taşıma aritmetiği")
    iddia(abs(-(be["n5y"] - a * be["n2y"] - b_ * be["n7y"]) - flp) <= 1, "PCA taşıma aritmetiği")
    M(f"**{bp(m50)}**, PCA ağırlığıyla **{bp(mp)}** öder", "5.3 long 1y2y5y")
    M(f"{bp(-m50, True)} ve {bp(-mp, True)} toplar (1 yıl {bp(be['n1y'])}, 2 yıl {bp(be['n2y'])}, 5 yıl {bp(be['n5y'])}",
      "5.3 short 1y2y5y")
    M(f"aylık oynaklığı {bp(kl['seri']['flyPCA']['sigma_bp_ay'])} (üç aylık ~{sayi(round(kl['seri']['flyPCA']['sigma_bp_ay'] * math.sqrt(3), -1))} bp)",
      "5.3 üç aylık σ")

    # 50:50 yön aracı, PCA göreli değer aracı
    t = tablo(tl, "Aylık hareketin kaynağı (long fly, gövde DV01'i başına)")
    for k, s in (("2y5y7y_50", "2y5y7y 50:50"), ("2y5y7y_pca", "2y5y7y PCA"), ("1y2y5y_50", "1y2y5y 50:50"),
                 ("1y2y5y_pca", "1y2y5y PCA")):
        x = fp[k]
        satir_sina(t, s, [sayi(x["sigma"])] + [yz(x["pay"][p], 0) for p in ("seviye", "egim", "bukum", "artik")],
                   "W5 varyans payları")
    M(f"hareketinin yalnız %{sayi(fp['2y5y7y_50']['pay']['seviye'])}–{sayi(fp['1y2y5y_50']['pay']['seviye'])}'si seviyeden",
      "5.3 seviye payı")
    M(f"aylık hareketinin {yz(fp['2y5y7y_pca']['pay']['artik'], 0)}'ü üç bileşenin dışında", "5.3 artık payı")
    M(f"{rj['n_pencere']} üst üste binen pencerede", "5.3 pencere")
    iddia(rj["n_pencere"] == 162, "pencere sayısı")
    KOL = (("faz", "artırım"), ("faz", "indirim"), ("kova", "sahin"), ("kova", "guvercin"), ("kuyruk", "satis"),
           ("kuyruk", "ralli"))
    bas_ = (f"Artırım fazı ({rj['faz_n']['artırım']}) | İndirim fazı ({rj['faz_n']['indirim']}) | "
            f"Şahin sürpriz ({rj['kova_n']['sahin']}) | Güvercin sürpriz ({rj['kova_n']['guvercin']}) | "
            f"Satış kuyruğu ({rj['kuyruk']['2y5y7y_long50']['satis']['n']}) | "
            f"Ralli kuyruğu ({rj['kuyruk']['2y5y7y_long50']['ralli']['n']})")
    M(bas_, "5.3 rejim başlığı")
    t = tablo(tl, "Long fly'ın rejim ortalaması (3 aylık P&L, gövde DV01'i başına bp, taşıma dahil)")
    tum_pca = []
    for k, s in (("2y5y7y_long50", "2y5y7y 50:50"), ("2y5y7y_longpca", "2y5y7y PCA"),
                 ("1y2y5y_long50", "1y2y5y 50:50"), ("1y2y5y_longpca", "1y2y5y PCA")):
        deg = [rj[gr][k][kv]["toplam"] for gr, kv in KOL]
        satir_sina(t, s, [n0(v) for v in deg], "W5 rejim")
        if k.endswith("pca"):
            tum_pca += [(abs(v), v, k, kv) for v, (_, kv) in zip(deg, KOL)]
    iddia(all(x[0] < 30 for x in tum_pca), "PCA hâllerinin rejim ortalamaları 30 bp'nin altında")
    en = sorted(tum_pca, reverse=True)[:2]
    iddia({(e[2], e[3]) for e in en} == {("1y2y5y_longpca", "indirim"), ("2y5y7y_longpca", "artırım")},
          "PCA'nın en büyük iki rejim sayısı")
    M(f"1y2y5y PCA'nın indirimdeki {sayi(rj['faz']['1y2y5y_longpca']['indirim']['toplam'])} ve 2y5y7y PCA'nın "
      f"artırımdaki {bp(rj['faz']['2y5y7y_longpca']['artırım']['toplam'])}'si", "5.3 PCA en büyükler")
    M(f"(isabet %{sayi(ks['isabet'])})", "5.3 isabet")
    M(f"şahin kovası {bp(rj['kova_sinir_bp'][1], True)}'nin üstü, güvercin {bp(rj['kova_sinir_bp'][0])}'nin altı",
      "5.3 kova sınırı")
    M(f"seviye ortalama {sayi(rj['kuyruk_seviye']['satis'], 0, True)}, rallide {bp(rj['kuyruk_seviye']['ralli'])}",
      "5.3 kuyruk seviyesi")
    r50 = {kv: rj[gr]["2y5y7y_long50"][kv]["toplam"] for gr, kv in KOL}
    r25 = {kv: rj[gr]["1y2y5y_long50"][kv]["toplam"] for gr, kv in KOL}
    iddia(r50["artırım"] < 0 < r50["indirim"] and r50["sahin"] < 0 < r50["guvercin"] and r50["satis"] < 0 < r50["ralli"],
          "long 2y5y7y 50:50: gizli boğa rejim işaretleri")
    iddia(r25["artırım"] > 0 > r25["indirim"] and r25["sahin"] > 0 > r25["guvercin"] and r25["satis"] > 0 > r25["ralli"],
          "long 1y2y5y 50:50: gizli ayı rejim işaretleri")
    st_, ra = ar["stres"], ar["ralli"]
    M(f"{st_['n']} ayda 1y2y5y 50:50 kotasyonu ortalama {bp(st_['1y2y5y'], True)}, PCA $F$'si "
      f"{bp(st_['1y2y5y_pca'], True)} oynadı; 200 bp'den fazla düştüğü {ra['n']} ayda {sayi(ra['1y2y5y'])} ve "
      f"{bp(ra['1y2y5y_pca'])}", "5.3 aylık stres/ralli 1y2y5y")
    M(f"50:50 kotasyonu {sayi(st_['2y5y7y'])} ve {bp(ra['2y5y7y'], True)}, PCA $F$'si {sayi(st_['2y5y7y_pca'])} ve "
      f"{bp(ra['2y5y7y_pca'], True)}", "5.3 aylık stres/ralli 2y5y7y")
    iddia(rj["faz"]["1y2y5y_long50"]["artırım"]["toplam"] > 0 and m50 < 0, "stres hedge'i: artırımda kazanır, beklerken öder")

    # ───────────────────────── 5.4 düğümler
    tb, rb = fh["tasima_bp"], fh["roll_bp"]
    t = tablo(tl, "Düğüm (kâğıt, receive, 3 ay, DV01 başına, bp)")
    for k, s in (("n1y", "1 yıl"), ("n2y", "2 yıl"), ("n3y", "3 yıl"), ("n5y", "5 yıl"), ("n7y", "7 yıl")):
        satir_sina(t, s, [None, n0(tb[k]), n0(rb[k]), n0(be[k])], "W5 düğümler")
        iddia(abs(tb[k] + rb[k] - be[k]) <= 1, f"taşıma + roll = başabaş ({k})")
    eg = o["bugun"]["egri"]
    iddia(max(("n1y", "n2y", "n3y", "n5y", "n7y"), key=lambda k: eg[k]) == "n2y", "tepe 2 yıl")
    iddia(rb["n1y"] > 0 and rb["n2y"] > 0 and all(rb[k] < 0 for k in ("n3y", "n5y", "n7y")), "roll: yükselen yamaç ve tepe artı")
    t27 = [tb[k] for k in ("n2y", "n3y", "n5y", "n7y")]
    M(f"({sayi(max(t27))} ile {bp(min(t27))})", "5.4 taşıma sütunu")
    M(f"1 yılda {bp(tb['n1y'])}", "5.4 1 yıl taşıma")
    r3 = [rb[k] for k in ("n3y", "n5y", "n7y")]
    M(f"tepede (2 yıl) {n0(rb['n2y'])}, inen yamaçta {sayi(max(r3))} ile {sayi(min(r3))}", "5.4 roll sütunu")
    iddia(max(t27) - min(t27) < 0.25 * (max(rb[k] for k in ("n2y", "n3y", "n5y", "n7y")) - min(r3)),
          "2–7 yılda başabaş farkını roll yaratır")
    bes = {k: be[k] for k in ("n1y", "n2y", "n3y", "n5y", "n7y")}
    iddia(min(bes, key=bes.get) == "n5y" and max(bes, key=bes.get) == "n2y", "en kötü 5 yıl, en iyi 2 yıl başabaşı")
    M(f"(5 yıl, {bp(be['n5y'])})", "5.4 en kötü başabaş")
    M(f"(2 yıl, {bp(be['n2y'])})", "5.4 en iyi başabaş")

    # 5.4 haritalar
    ONF = ("1y2y3y", "1y2y5y", "1y2y7y", "1y3y5y", "1y3y7y", "1y5y7y", "2y3y5y", "2y3y7y", "2y5y7y", "3y5y7y")
    iddia(sorted(k.split("_")[0] for k in F if k.endswith("_50")) == sorted(ONF), "on fly")
    t = tablo(tl, "On fly, 50:50 ağırlık (kâğıt, 22.09.2026)")
    for f_ in ONF:
        x = F[f_ + "_50"]
        satir_sina(t, f_, [n0(x["seviye_bp"]), sayi(x["yuzdelik"]), sayi(x["z36"], 2, True), n0(x["tasima_long_bp"]),
                           sayi(x["sigma_bp_ay"]), sayi(x["tasima_sigma"], 2, True), sayi(x["yari_omur_ay"], 1)],
                   "W5 harita 50:50")
    t = tablo(tl, "On fly, PCA-nötr ağırlık (kâğıt, 22.09.2026)")
    for f_ in ONF:
        x = F[f_ + "_pca"]
        satir_sina(t, f_, [f"{sayi(x['a'], 3)} · {sayi(x['b'], 3)}", n0(x["seviye_bp"]), sayi(x["yuzdelik"]),
                           sayi(x["z36"], 2, True), n0(x["tasima_long_bp"]), sayi(x["sigma_bp_ay"]),
                           sayi(x["tasima_sigma"], 2, True), sayi(x["yari_omur_ay"], 1)], "W5 harita PCA")
    M(f"3.3'te long 2y5y7y 50:50 için {sayi(o['tasima_oynaklik']['2y5y7y_long50']['oran'], 2)}", "5.4 36 ay oranı")
    iddia(o["tasima_oynaklik"]["2y5y7y_long50"]["oran"] < F["2y5y7y_50"]["tasima_sigma"], "36 ay oranı küçük")

    # kural
    pos = [k for k in F if F[k]["tasima_long_bp"] > 0]
    neg = [k for k in F if F[k]["tasima_long_bp"] < 0]
    iddia(len(F) == 20 and len(pos) == 12 and len(neg) == 8, "yirmi yapının on ikisi taşır, sekizi öder")
    tepe = [k for k in F if k[2:4] == "2y"]
    yamac = [k for k in F if k[2:4] in ("3y", "5y")]
    iddia(len(tepe) == 6 and all(F[k]["tasima_long_bp"] < 0 for k in tepe), "tepe gövdeli altı yapının altısı öder")
    iddia(max(F[k]["tasima_long_bp"] for k in tepe) == -30 and min(F[k]["tasima_long_bp"] for k in tepe) == -53,
          "tepe gövdeli aralık")
    M(f"({sayi(max(F[k]['tasima_long_bp'] for k in tepe))} ile\n{bp(min(F[k]['tasima_long_bp'] for k in tepe))})"
      .replace("\n", " "), "5.4 tepe aralığı")
    yam_neg = sorted(k for k in yamac if F[k]["tasima_long_bp"] < 0)
    iddia(len(yamac) == 14 and len(yam_neg) == 2 and yam_neg == ["1y3y5y_pca", "1y3y7y_pca"],
          "yamaç gövdeli on dört yapının on ikisi taşır; istisnalar")
    M(f"(1y3y5y {sayi(F['1y3y5y_pca']['tasima_long_bp'])}, 1y3y7y {bp(F['1y3y7y_pca']['tasima_long_bp'])})",
      "5.4 istisnalar")
    t = tablo(tl, "Long fly'ın taşıma + roll'u, parçalarına ayrılmış (3 ay, gövde DV01'i başına, bp)")
    for k, s in (("2y5y7y_50", "2y5y7y 50:50"), ("2y5y7y_pca", "2y5y7y PCA"), ("3y5y7y_50", "3y5y7y 50:50"),
                 ("2y3y5y_50", "2y3y5y 50:50"), ("2y3y7y_pca", "2y3y7y PCA"), ("1y5y7y_50", "1y5y7y 50:50"),
                 ("1y2y5y_50", "1y2y5y 50:50"), ("1y2y5y_pca", "1y2y5y PCA"), ("1y2y3y_pca", "1y2y3y PCA")):
        x = F[k]
        satir_sina(t, s, [None, n0(x["tasima_parca_bp"]), n0(x["roll_parca_bp"]), n0(x["tasima_long_bp"])],
                   "W5 parçalar")
        iddia(abs(x["tasima_parca_bp"] + x["roll_parca_bp"] - x["tasima_long_bp"]) <= 1, f"parçalar toplamı ({k})")
    x = F["2y5y7y_50"]
    M(f"{bp(x['tasima_long_bp'], True)}'sinin {n0(x['roll_parca_bp'])}'sı roll'dan gelir, taşıma parçası "
      f"{n0(x['tasima_parca_bp'])}", "5.4 2y5y7y parçaları")
    x = F["1y5y7y_50"]
    M(f"1y5y7y'de taşıma parçası {n0(x['tasima_parca_bp'])}, roll parçası {n0(x['roll_parca_bp'])}", "5.4 1y5y7y")
    M(f"DV01 başına {bp(tb['n1y'])} taşıma öder ve {bp(rb['n1y'], True)} roll toplar", "5.4 1 yıllık kanat")
    x = F["1y2y5y_50"]
    M(f"gövdenin artı roll'u ({n0(rb['n2y'])}) pay edilir, 1 yıllık kanadın roll'u ({n0(rb['n1y'])}) receive",
      "5.4 tepe roll")
    M(f"roll parçası {n0(x['roll_parca_bp'])}'ye iner; kalan {n0(x['tasima_parca_bp'])}", "5.4 tepe parçaları")
    M(f"tepedeki gövdenin başabaşı ({bp(be['n2y'])})", "5.4 tepe başabaş")
    M(f"çeyrekte {n0(-m50)} (50:50) ve {bp(-mp, True)} (PCA)", "5.4 short 1y2y5y")
    M(f"(5 yılda roll {sayi(rb['n5y'])}, kanatların ortalaması {bp((rb['n2y'] + rb['n7y']) / 2)})", "5.4 yerel eğim")
    iddia(rb["n5y"] < (rb["n2y"] + rb["n7y"]) / 2, "gövdede eğri kanatlardan dik iner")
    M(f"kısa kanat hafifler ({sayi(F['1y2y5y_pca']['a'], 3)}), 1 yıllık kanadın roll desteği azalır ve roll parçası "
      f"da eksiye döner ({bp(F['1y2y5y_pca']['roll_parca_bp'])})", "5.4 tepe PCA roll")
    iddia(all(abs(F[k]["roll_parca_bp"]) <= 3 for k in tepe if k.endswith("_50")), "tepe 50:50 roll parçası ≈ 0")
    # iki taşıma, tek risk: long 2y5y7y ve short 1y2y5y aynı yöne duyarlı
    c3 = {k: fp[k]["c"][2] for k in ("2y5y7y_50", "2y5y7y_pca", "1y2y5y_50", "1y2y5y_pca")}
    iddia(c3["2y5y7y_50"] < 0 and -c3["1y2y5y_50"] < 0 and c3["2y5y7y_pca"] < 0 and -c3["1y2y5y_pca"] < 0,
          "long 2y5y7y ve short 1y2y5y büküm duyarlılığı eksi")
    iddia(fp["2y5y7y_50"]["c"][0] < 0 and -fp["1y2y5y_50"]["c"][0] < 0, "ikisinin 50:50 hâli gizli boğa")
    M(f"(50:50'de long 2y5y7y {sayi(c3['2y5y7y_50'], 3)}, short 1y2y5y {sayi(-c3['1y2y5y_50'], 3)}; PCA'da "
      f"{sayi(c3['2y5y7y_pca'], 3)} ve {sayi(-c3['1y2y5y_pca'], 3)})", "5.4 iki taşıma büküm")
    M(f"long 2y5y7y 50:50 ortalama {sayi(r50['artırım'])}, short 1y2y5y 50:50 {bp(-r25['artırım'])} getirdi",
      "5.4 iki taşıma artırım")
    iddia(r50["artırım"] < 0 and -r25["artırım"] < 0, "ikisi de artırımda kaybeder")
    x = F["1y2y3y_pca"]
    en_oran = max(F, key=lambda k: abs(F[k]["tasima_sigma"]))
    iddia(en_oran == "1y2y3y_pca" and x["tasima_long_bp"] < 0, "haritanın mutlak en büyük oranı short 1y2y3y PCA")
    M(f"çeyrekte {bp(-x['tasima_long_bp'], True)} toplar ve oynaklığa oranı {sayi(abs(x['tasima_sigma']), 2)}",
      "5.4 short 1y2y3y")
    ust = sorted(pos, key=lambda k: -F[k]["tasima_sigma"])[:3]
    iddia(set(ust) == {"2y5y7y_50", "2y5y7y_pca", "2y3y7y_pca"}, "long taraftaki en yüksek üç oran")
    M(f"(50:50 {sayi(F['2y5y7y_50']['tasima_sigma'], 2)}, PCA {sayi(F['2y5y7y_pca']['tasima_sigma'], 2)}) ve 2y3y7y "
      f"PCA'dadır ({sayi(F['2y3y7y_pca']['tasima_sigma'], 2)})", "5.4 long oranlar")

    # sinyaller
    sin = sorted(k for k in F if F[k]["sinyal"] != "yok")
    iddia(sin == ["1y3y5y_50", "1y3y7y_50", "1y5y7y_50"] and all(F[k]["sinyal"] == "short" for k in sin)
          and all(F[k]["tasima_uyumlu"] is False for k in sin), "bugünkü üç sinyal: short, taşımaya ters")
    M(f"1y3y5y (z {sayi(F['1y3y5y_50']['z36'], 2, True)}), 1y3y7y ({sayi(F['1y3y7y_50']['z36'], 2, True)}), 1y5y7y "
      f"({sayi(F['1y5y7y_50']['z36'], 2, True)})", "5.4 sinyaller")
    M(f"({n0(F['1y3y5y_50']['tasima_long_bp'])}, {n0(F['1y3y7y_50']['tasima_long_bp'])}, "
      f"{bp(F['1y5y7y_50']['tasima_long_bp'], True)})", "5.4 sinyal taşımaları")
    M(f"(z {sayi(F['1y3y5y_pca']['z36'], 2, True)}, {sayi(F['1y3y7y_pca']['z36'], 2, True)}, "
      f"{sayi(F['1y5y7y_pca']['z36'], 2, True)})", "5.4 PCA z")
    iddia(F["2y5y7y_50"]["sinyal"] == "yok" and round(F["2y5y7y_50"]["z36"], 2) == 1.0, "2y5y7y 50:50 z sınırda")
    M(f"z'si {sayi(F['2y5y7y_50']['z36'], 2)}'dır", "5.4 2y5y7y z")
    buyuk = [k for k in F if abs(F[k]["z36"]) >= 0.5]
    ters = [k for k in buyuk if (F[k]["z36"] > 0) == (F[k]["tasima_long_bp"] > 0)]
    iddia(len(buyuk) == 14 and len(ters) == 13, "mutlak z ≥ 0,5 olan 14 yapının 13'ünde yön ters")
    M(f"Mutlak z'si en az 0,5 olan {len(buyuk)} yapının {len(ters)}'ünde", "5.4 çatışma")
    yz_ = [k for k in yamac]
    iddia(sum(F[k]["z36"] > 0 for k in yz_) >= 12 and all(F[k]["z36"] < 0 for k in tepe if k.endswith("_pca")),
          "yamaçta z çoğunlukla artı; tepedeki PCA'larda eksi")
    for f_ in ("2y5y7y", "1y2y5y", "3y5y7y", "2y3y5y"):
        u, te = ff[f_]["uyumlu"]["ort"], ff[f_]["ters"]["ort"]
        iddia(u > te, f"uyumlu dönüş işlemleri ters olanlardan iyi ({f_})")
    ters_yari = 0
    for f_ in ("2y5y7y", "1y2y5y", "3y5y7y", "2y3y5y"):
        for yr in ("2013_2019", "2020_2026"):
            ters_yari += ff[f_]["uyumlu"]["yarilar"][yr]["ort"] <= ff[f_]["ters"]["yarilar"][yr]["ort"]
    iddia(ters_yari == 4, "yarılarda sekiz karşılaştırmanın dördünde sıra tersine döner")

    # temsili OIS
    M(f"long 2y5y7y 50:50 **{bp(of['2y5y7y']['5050']['toplam_bp_govde'])}**, PCA {bp(of['2y5y7y']['pca']['toplam_bp_govde'])}; "
      f"long 1y2y5y 50:50 **{bp(of['1y2y5y']['5050']['toplam_bp_govde'], True)}**, PCA "
      f"{bp(of['1y2y5y']['pca']['toplam_bp_govde'], True)}", "5.4 temsili OIS")
    M(f"({sayi(of['2y5y7y']['5050']['toplam_bugun_bp_govde'])}, {sayi(of['2y5y7y']['pca']['toplam_bugun_bp_govde'])}, "
      f"{n0(of['1y2y5y']['5050']['toplam_bugun_bp_govde'])}, {bp(of['1y2y5y']['pca']['toplam_bugun_bp_govde'], True)})",
      "5.4 temsili OIS fixing %36,49")
    M(f"(05.08.2026, fixing {yz(of['tlref'])})", "5.4 temsili fixing")
    M(f"Fixing {yz(of['tlref_bugun'])} varsayılsa", "5.4 bugünkü fixing")
    iddia(of["2y5y7y"]["5050"]["toplam_bp_govde"] < 0 < F["2y5y7y_50"]["tasima_long_bp"] and
          of["1y2y5y"]["5050"]["toplam_bp_govde"] > 0 > F["1y2y5y_50"]["tasima_long_bp"], "iki eğride ters işaret")
    M(f"DV01 başına {bp(o['ois_roll_haritasi']['2y']['roll_bp'])}, kâğıtta {bp(rb['n2y'], True)}", "5.4 2 yıllık roll")

    # seçim yanlılığı ve masa
    M(f"({bp(t1['ort'], True, 1)}, t {sayi(t1['t'], 1)}) ve o kenar sinyal 21 gün gecikince "
      f"{bp(ff['1y2y5y']['gecikme']['21']['tasima'], True, 1)}'ye eridi", "5.4 gecikme")
    M(f"çeyrekte {bp(ff['2y5y7y']['tasima']['ort'], b=1)} (t {sayi(ff['2y5y7y']['tasima']['t'], 1)})", "5.4 2y5y7y kuralı")
    M(f"ortalama {sayi(tm['ort_sure_ay']['n2y'], 1)} ay kaldı (3.2); bugünkü tepe {tm['bugun_sure_ay']} aydır",
      "5.4 tümsek süresi")
    iddia(tm["bugun"] == "n2y", "bugünkü tepe 2 yıl")
    iddia(all(o["yapi_stres"][k]["sigma36"] > o["yapi_stres"][k]["sigma"] for k in
              ("2y5y7y_50", "2y5y7y_pca", "1y2y5y_50", "1y2y5y_pca")), "son 36 ayda oynaklık daha yüksek")


# W6_dogrula
def kontrol_w6(o, m, tl):
    FLY5 = ("1y2y3y", "1y2y5y", "2y3y5y", "2y5y7y", "3y5y7y")
    W2 = (("50", "50:50"), ("pca", "PCA"))
    R = o["rejim_yapi"]
    H = o["fly_tasima_haritasi"]["fly"]
    S = o["yapi_stres"]
    FT = o["fly_tasima_filtresi"]
    OF = o["ois_fly"]
    gun = lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}"

    # ── 5.5 rejimlerde fly: faz, sürpriz + kuyruk, çıpa
    t = tablo(tl, "Long fly · PPK fazı (3 ay, gövde DV01'i başına bp)")
    n = R["faz_n"]
    if t:
        bas = t[0]
        sayac["hucre"] += 3
        if bas[1:4] != [f"İndirim ({n['indirim']} pencere)", f"Sabit ({n['sabit']})", f"Artırım ({n['artırım']})"]:
            hatalar.append(f"rejim fazı başlığı: {bas}")
    for f in FLY5:
        for w, ad in W2:
            x = R["faz"][f"{f}_long{w}"]
            satir_sina(t, f"long {f} ({ad})", [sayi(x[k]["toplam"], 0, True) for k in ("indirim", "sabit", "artırım")],
                       "rejim fazı")
    t = tablo(tl, "Long fly · sürpriz ve kuyruk (3 ay, gövde DV01'i başına bp)")
    kn, qn = R["kova_n"], R["kuyruk"]["2y5y7y_long50"]
    if t:
        sayac["hucre"] += 5
        if t[0][1:6] != [f"Güvercin sürpriz ({kn['guvercin']})", f"Orta ({kn['orta']})", f"Şahin sürpriz ({kn['sahin']})",
                         f"Satış kuyruğu ({qn['satis']['n']})", f"Ralli kuyruğu ({qn['ralli']['n']})"]:
            hatalar.append(f"sürpriz/kuyruk başlığı: {t[0]}")
    for f in FLY5:
        for w, ad in W2:
            k = f"{f}_long{w}"
            satir_sina(t, f"long {f} ({ad})",
                       [sayi(R["kova"][k][x]["toplam"], 0, True) for x in ("guvercin", "orta", "sahin")] +
                       [sayi(R["kuyruk"][k][x]["toplam"], 0, True) for x in ("satis", "ralli")], "sürpriz/kuyruk")
    t = tablo(tl, "Seçilmiş rejim hücresi (long fly, bp)")
    for ad, k, g, h in (("1y2y5y 50:50 · artırım", "1y2y5y_long50", "faz", "artırım"),
                        ("1y2y5y 50:50 · şahin sürpriz", "1y2y5y_long50", "kova", "sahin"),
                        ("1y2y5y 50:50 · satış kuyruğu", "1y2y5y_long50", "kuyruk", "satis"),
                        ("1y2y5y 50:50 · güvercin sürpriz", "1y2y5y_long50", "kova", "guvercin"),
                        ("1y2y5y PCA · indirim", "1y2y5y_longpca", "faz", "indirim"),
                        ("2y5y7y 50:50 · indirim", "2y5y7y_long50", "faz", "indirim"),
                        ("2y5y7y 50:50 · artırım", "2y5y7y_long50", "faz", "artırım"),
                        ("2y5y7y PCA · artırım", "2y5y7y_longpca", "faz", "artırım"),
                        ("2y5y7y PCA · satış kuyruğu", "2y5y7y_longpca", "kuyruk", "satis"),
                        ("2y3y5y 50:50 · satış kuyruğu", "2y3y5y_long50", "kuyruk", "satis"),
                        ("3y5y7y PCA · indirim", "3y5y7y_longpca", "faz", "indirim")):
        x = R[g][k][h]
        satir_sina(t, ad, [str(x["n"]), sayi(x["toplam"], 0, True), sayi(x["tasima"], 0, True),
                           sayi(x["hareket"], 0, True),
                           f"{sayi(x['hareket_p25'], 0, True)} · {sayi(x['hareket_p75'], 0, True)}",
                           yz(x["isabet"], 0)], "seçilmiş rejim hücresi")
    t = tablo(tl, "Long fly · fonlama çıpası (3 ay, gövde DV01'i başına bp)")
    cn = R["cipa_n"]
    if t:
        sayac["hucre"] += 3
        if t[0][1:4] != [f"Politika faizi ({cn['politika']})", f"Koridor üstü ({cn['koridor_ust']})",
                         f"Koridor altı ({cn['koridor_alt']})"]:
            hatalar.append(f"çıpa başlığı: {t[0]}")
    for f in FLY5:
        for w, ad in W2:
            x = R["cipa"][f"{f}_long{w}"]
            satir_sina(t, f"long {f} ({ad})", [sayi(x[c]["toplam"], 0, True) for c in ("politika", "koridor_ust", "koridor_alt")],
                       "fonlama çıpası")
    ar = o["aylik_rejim"]
    t = tablo(tl, "Ay türü (aylık hareket, bp)")
    for ad, g, h in (("PPK ayı: indirim", "faz", "indirim"), ("PPK ayı: sabit", "faz", "sabit"),
                     ("PPK ayı: artırım", "faz", "artırım"), ("Toplantısız ay", "faz", "toplantı yok"),
                     ("Stres ayı (seviye +200 bp üstü)", "stres", None), ("Ralli ayı (seviye −200 bp altı)", "ralli", None)):
        x = ar[g][h] if h else ar[g]
        satir_sina(t, ad, [str(x["n"])] + [sayi(x[k], 0, True) for k in ("2y", "1y2y5y", "1y2y5y_pca", "2y5y7y", "2y5y7y_pca")],
                   "aylık rejim")
    t = tablo(tl, "Döngü dönüşü (karar günü)")
    for e in o["donum_noktalari"]:
        ad = gun(e["tarih"]) + (" (arşivin ilk değişimi)" if e["arsiv_basi"] else "")
        hh = e["hareket"]
        satir_sina(t, ad, [f"{e['yon']} · {sayi(e['adim_bp'], 0, True)}"] +
                   [" · ".join(sayi(hh[p][k], 0, True) for p in ("1a", "3a", "6a")) for k in ("2y", "2y5y7y_pca", "1y2y5y_pca")],
                   "dönüm noktaları")
    t = tablo(tl, "PCA fly · iki günlük mutlak hareket (bp)")
    for f in ("1y2y3y", "1y2y5y", "2y5y7y", "3y5y7y"):
        x = o["ppk_gunu_yapi"][f + "_pca"]
        satir_sina(t, f, [sayi(x["ppk_medyan"]), sayi(x["ppk_p90"]), sayi(x["diger_medyan"]), sayi(x["diger_p90"])],
                   "PPK günü fly")
    # 5.5 metin
    for p in (f"{R['n_pencere']} pencere", f"{sum(R['faz_n'].values())} pencereye",
              f"{bp(R['kova_sinir_bp'][0])[:-3]} ve {bp(R['kova_sinir_bp'][1], True)}",
              f"{sayi(R['kova_surpriz']['guvercin'])}, {sayi(R['kova_surpriz']['orta'], 0, True)} ve "
              f"{bp(R['kova_surpriz']['sahin'], True)}",
              f"{bp(R['kuyruk_sinir_bp'][0])}'nin altı", f"{bp(R['kuyruk_sinir_bp'][1], True)}'nin üstü",
              f"ortalaması {bp(R['kuyruk_seviye']['ralli'])}", f"ortalaması\n  {bp(R['kuyruk_seviye']['satis'], True)}"):
        metinde(m, p, "5.5 tanım")
    y1 = o["pca"]["yuk"]["pc1"]
    yuk = lambda g_, k1_, k2_: 2 * y1[g_] - y1[k1_] - y1[k2_]
    katex = lambda x_: "= " + sayi(x_, 3, True).replace("−", "-") + "$"
    metinde(m, f"{sayi(y1['n2y'], 4)} - {sayi(y1['n1y'], 4)} - {sayi(y1['n5y'], 4)} {katex(yuk('n2y', 'n1y', 'n5y'))}",
            "1y2y5y seviye yükü")
    metinde(m, f"seviye yükü {sayi(yuk('n5y', 'n2y', 'n7y'), 3)}", "2y5y7y seviye yükü")
    metinde(m, f"{sayi(y1['n3y'], 4)} - {sayi(y1['n2y'], 4)} - {sayi(y1['n5y'], 4)} {katex(yuk('n3y', 'n2y', 'n5y'))}",
            "2y3y5y seviye yükü")
    metinde(m, f"{sayi(y1['n5y'], 4)} - {sayi(y1['n3y'], 4)} - {sayi(y1['n7y'], 4)} {katex(yuk('n5y', 'n3y', 'n7y'))}",
            "3y5y7y seviye yükü")
    k = R["faz"]["1y2y5y_longpca"]["indirim"]
    metinde(m, f"long 1y2y5y PCA {bp(k['toplam'])}** (isabet {yz(k['isabet'], 0)})", "1y2y5y indirim")
    k = R["kuyruk"]["2y5y7y_longpca"]["satis"]
    metinde(m, f"long 2y5y7y PCA {sayi(k['toplam'], 0, True)} bp** (isabet {yz(k['isabet'], 0)}, {k['n']} pencere)",
            "2y5y7y satış")
    metinde(m, f"isabeti indirim fazında {yz(R['faz']['2y5y7y_long50']['indirim']['isabet'], 0)}, güvercin sürpriz\n"
               f"kovasında {yz(R['kova']['2y5y7y_long50']['guvercin']['isabet'], 0)}", "sürpriz kovası")
    st, ra = ar["stres"], ar["ralli"]
    metinde(m, f"; {st['n']} ay)", "stres ayı sayısı")
    metinde(m, f"; {ra['n']} ay)", "ralli ayı sayısı")
    metinde(m, f"ayında {sayi(st['1y2y5y'], 0, True)}, rallide {sayi(ra['1y2y5y'], 0, True)}", "stres/ralli 1y2y5y")
    metinde(m, f"Artırım aylarında ({ar['faz']['artırım']['n']} ay) 2 yıllık getiri ortalama "
               f"{bp(ar['faz']['artırım']['2y'], True)}", "artırım ayları")
    ku = R["cipa"]["2y5y7y_long50"]["koridor_ust"]
    metinde(m, f"50:50 {sayi(ku['toplam'], 0, True)} (isabet {yz(ku['isabet'], 0)})", "koridor üstü")
    ku = R["cipa"]["1y2y3y_longpca"]["koridor_ust"]
    metinde(m, f"long 1y2y3y PCA {sayi(ku['toplam'], 0, True)}\n(isabet {yz(ku['isabet'], 0)})", "koridor üstü 1y2y3y")
    dn = {e["tarih"]: e for e in o["donum_noktalari"]}
    ind = [e for e in o["donum_noktalari"] if e["yon"] == "indirim"]
    kaz = [sayi(e["hareket"]["3a"]["2y5y7y_pca"], 0, True) for e in ind if e["hareket"]["3a"]["2y5y7y_pca"] > 20]
    metinde(m, f"({kaz[0]},\n{kaz[1]}, {kaz[2]})", "dönüm: 2y5y7y indirim")
    e21 = dn["2021-09-23"]
    metinde(m, f"{bp(e21['hareket']['3a']['2y'], True)} yükseldiği\n{gun(e21['tarih'])} indirimidir "
               f"({sayi(e21['hareket']['3a']['2y5y7y_pca'], 0, True)})", "dönüm: 2021")
    e25 = dn["2025-04-17"]
    metinde(m, f"long 2y5y7y PCA {sayi(e25['hareket']['3a']['2y5y7y_pca'], 0, True)}\nbp kazandı ve aynı üç ayda 2 yıllık "
               f"getiri {bp(e25['hareket']['3a']['2y'])} düştü", "dönüm: 2025")
    pg = o["ppk_gunu_yapi"]
    metinde(m, f"PPK gününün 90. yüzdeliği {bp(pg['1y2y5y_pca']['ppk_p90'])} (diğer günler "
               f"{pg['1y2y5y_pca']['diger_p90']:.0f})", "PPK günü 1y2y5y")

    # ── 5.6 özet ve beş kart
    t = tablo(tl, "Fly (beş kart özeti)")
    for f in FLY5:
        x = H[f + "_pca"]
        tas = x["tasima_long_bp"]
        yon = f"long {sayi(tas, 0, True)}" if tas > 0 else f"short {sayi(-tas, 0, True)}"
        satir_sina(t, f, [None, None, None, yon, sayi(x["sigma_bp_ay"]), sayi(x["yari_omur_ay"], 1), None], "kart özeti")
    for f in FLY5:
        t = tablo(tl, f"{f} kartı (22.09.2026 kâğıt eğrisi)")
        a, b = H[f + "_pca"]["a"], H[f + "_pca"]["b"]
        satir_sina(t, "Kanat ağırlıkları (a · b)", [f"{sayi(0.5, 1)} · {sayi(0.5, 1)}", f"{sayi(a, 3)} · {sayi(b, 3)}"],
                   f"kart {f}")
        g = lambda ad, fn: satir_sina(t, ad, [fn(H[f"{f}_{w}"], S[f"{f}_{w}"]) for w in ("50", "pca")], f"kart {f}")
        g("Seviye (bp)", lambda h, s: sayi(h["seviye_bp"], 0, True))
        g("Tarihsel yüzdelik", lambda h, s: sayi(h["yuzdelik"]))
        g("z (son 36 ay sonuna göre)", lambda h, s: sayi(h["z36"], 2, True))
        g("Long fly taşıma + roll (bp, 3 ay)", lambda h, s: sayi(h["tasima_long_bp"], 0, True))
        g("Taşıma · roll (bp)", lambda h, s: f"{sayi(h['tasima_parca_bp'], 0, True)} · {sayi(h['roll_parca_bp'], 0, True)}")
        g("Taşıma / 3 aylık σ", lambda h, s: sayi(h["tasima_sigma"], 2, True))
        g("Aylık σ, tam örneklem (bp)", lambda h, s: sayi(s["sigma"]))
        g("Aylık σ, son 36 ay (bp)", lambda h, s: sayi(s["sigma36"]))
        g("Yarı ömür (ay)", lambda h, s: sayi(h["yari_omur_ay"], 1))
        g("En büyük aylık yükseliş (bp)",
          lambda h, s: f"{sayi(s['en_buyuk_artis'][0], 0, True)} ({ay(s['en_buyuk_artis'][1])})")
        g("En büyük aylık düşüş (bp)",
          lambda h, s: f"{sayi(s['en_buyuk_dusus'][0], 0, True)} ({ay(s['en_buyuk_dusus'][1])})")
        g("Mutlak aylık hareketin p95'i (bp)", lambda h, s: sayi(s["p95"]))
        if f in OF:
            satir_sina(t, "Temsili OIS: long taşıma + roll (bp, 3 ay)",
                       [sayi(OF[f][kk]["toplam_bp_govde"], 0, True) for kk in ("5050", "pca")], f"kart {f}")
            satir_sina(t, f"Temsili OIS, fixing {yz(OF['tlref_bugun'])} ile (bp)",
                       [sayi(OF[f][kk]["toplam_bugun_bp_govde"], 0, True) for kk in ("5050", "pca")], f"kart {f}")
    # kart metinleri: 2σ stopları (son 36 ay σ'sının iki katı), taşıma parçaları, bacak başabaşları
    for f in FLY5:
        metinde(m, f"2σ = {sayi(2 * S[f + '_pca']['sigma36'])} bp", f"kart {f} stop")
    fb = o["fly_tasima_haritasi"]
    metinde(m, f"(DV01 başına {bp(fb['tasima_bp']['n1y'])})", "1y taşıma")
    metinde(m, f"Long fly'ın PCA parçaları: taşıma {sayi(H['1y2y3y_pca']['tasima_parca_bp'], 0, True)}, roll "
               f"{sayi(H['1y2y3y_pca']['roll_parca_bp'], 0, True)}", "1y2y3y parçalar")
    metinde(m, f"artı roll'u ({sayi(fb['roll_bp']['n2y'], 0, True)})", "2y roll")
    metinde(m, f"eksi roll'u ({sayi(fb['roll_bp']['n3y'], 0, True)})", "3y roll")
    metinde(m, f"roll'da kaybeder ({sayi(fb['roll_bp']['n5y'], 0, True)})", "5y roll")
    metinde(m, f"eksi roll'unu ({sayi(fb['roll_bp']['n7y'], 0, True)})", "7y roll")
    x = H["2y5y7y_50"]
    metinde(m, f"(long fly'ın 50:50 parçaları: taşıma {sayi(x['tasima_parca_bp'], 0, True)}, roll {sayi(x['roll_parca_bp'], 0, True)})",
            "2y5y7y parçalar")
    metinde(m, f"Long fly'ın PCA parçaları: taşıma {sayi(H['1y2y5y_pca']['tasima_parca_bp'], 0, True)}, roll "
               f"{sayi(H['1y2y5y_pca']['roll_parca_bp'], 0, True)}", "1y2y5y parçalar")

    # ── 5.7 OIS biletleri
    for f in ("2y5y7y", "1y2y5y"):
        t = tablo(tl, f"Long {f} OIS bileti · bacak")
        k1, g_, k2 = f[:2], f[2:4], f[4:]
        for kural, ad in (("5050", "50:50"), ("pca", "PCA")):
            x = OF[f][kural]
            for v, rol in ((k1, "kısa kanat"), (g_, "gövde"), (k2, "uzun kanat")):
                satir_sina(t, f"{v[:-1]} yıl ({rol}) · {ad}",
                           ["pay" if v == g_ else "receive", sayi(x["nominal_mn"][v], 1), yz(x["K"][v]), yz(x["S_Th"][v]),
                            sayi(x["tasima_bin"][v], 0, True), sayi(x["roll_bin"][v], 0, True)], f"OIS bileti {f}")
    t = tablo(tl, "Long fly OIS bileti · toplam (temsili eğri, 92 gün)")
    kol = [OF["2y5y7y"]["5050"], OF["2y5y7y"]["pca"], OF["1y2y5y"]["5050"], OF["1y2y5y"]["pca"]]
    tlr, tlb = yz(OF["tlref"]), yz(OF["tlref_bugun"])
    for ad, fn in ((f"Taşıma, fixing {tlr} (mn TL)", lambda x: sayi(x["tasima_mn"], 2, True)),
                   ("Roll (mn TL)", lambda x: sayi(x["roll_mn"], 2, True)),
                   ("Toplam (mn TL)", lambda x: sayi(x["toplam_mn"], 2, True)),
                   ("Gövde DV01'i başına (bp)", lambda x: sayi(x["toplam_bp_govde"], 0, True)),
                   ("Net yüzen nominal (mn TL; eksi = net yüzen öder)", lambda x: sayi(x["net_yuzen_mn"], 1, True)),
                   ("TLREF +100 bp'nin çeyreklik taşımaya etkisi (bin TL)", lambda x: sayi(x["tlref_100_etkisi_bin"], 0, True)),
                   (f"Taşıma, fixing {tlb} (mn TL)", lambda x: sayi(x["tasima_bugun_mn"], 2, True)),
                   (f"Toplam, fixing {tlb} (mn TL)", lambda x: sayi(x["toplam_bugun_mn"], 2, True)),
                   (f"Gövde DV01'i başına, fixing {tlb} (bp)", lambda x: sayi(x["toplam_bugun_bp_govde"], 0, True))):
        satir_sina(t, ad, [fn(x) for x in kol], "OIS bileti toplam")
    a5 = OF["2y5y7y"]["5050"]
    for p in (f"{sayi(OF['2y5y7y']['govde_dv01'])} TL/bp", f"{sayi(OF['1y2y5y']['govde_dv01'])} TL/bp",
              f"{sayi(OF['2y5y7y']['fly_10bp_bin'])} bin TL", f"{sayi(OF['1y2y5y']['fly_10bp_bin'])} bin TL",
              f"{sayi(a5['nominal_mn']['2y'], 1)} + {sayi(a5['nominal_mn']['7y'], 1)} = "
              f"{sayi(a5['nominal_mn']['2y'] + a5['nominal_mn']['7y'])} mn TL",
              f"{sayi(-a5['net_yuzen_mn'])} mn TL'lik", f"{sayi(a5['tlref_100_etkisi_bin'], 0, True)} bin TL",
              f"{sayi(a5['toplam_mn'], 2, True)} mn'dan {sayi(a5['toplam_bugun_mn'], 2, True)} mn TL'ye",
              f"({sayi(a5['toplam_bugun_bp_govde'], 0, True)} bp)",
              f"{sayi(a5['tasima_mn'], 2, True)}'dan\n{sayi(a5['tasima_bugun_mn'], 2, True)}'ye",
              f"1 yıl {yz(OF['1y2y5y']['5050']['K']['1y'])} · 2 yıl {yz(a5['K']['2y'])} · 5 yıl {yz(a5['K']['5y'])} · "
              f"7 yıl {yz(a5['K']['7y'])}",
              f"{sayi(o['kalicilik']['agirlik_pca'][0], 3)} · {sayi(o['kalicilik']['agirlik_pca'][1], 3)}; 1y2y5y için "
              f"{sayi(o['fly_1y2y5y']['agirlik_pca'][0], 3)} · {sayi(o['fly_1y2y5y']['agirlik_pca'][1], 3)}"):
        metinde(m, p, "5.7 metin")
    metinde(m, f"{sayi(o['barbell_kurallar']['5050']['net_nakit_mn'], 1)} mn TL nakit ister", "50:50 barbell nakdi")

    # ── 5.8 oynaklık ve barbell (eski tablolar dogrula.py'de; yeni kanıt burada)
    ob = o["oynaklik_barbell"]
    t = tablo(tl, "Gerçekleşen oynaklık kovası (long 2y5y7y, 3 ay)")
    for kk, ad in (("dusuk", "Düşük"), ("orta", "Orta"), ("yuksek", "Yüksek")):
        a_, b_ = ob["2y5y7y_long50"][kk], ob["2y5y7y_longpca"][kk]
        satir_sina(t, ad, [sayi(a_["oynaklik_bp_gun"]), str(a_["n"]), sayi(a_["toplam"], 0, True),
                           sayi(a_["tasima"], 0, True), sayi(b_["toplam"], 0, True), sayi(b_["tasima"], 0, True)],
                   "oynaklık kovası")
    yk, ykp = ob["2y5y7y_long50"]["yuksek"], ob["2y5y7y_longpca"]["yuksek"]
    metinde(m, f"50:50 ile {sayi(yk['toplam'], 0, True)}, PCA ile {sayi(ykp['toplam'], 0, True)} bp", "yüksek oynaklık")
    metinde(m, f"(+{sayi(yk['tasima'])} ve +{sayi(ykp['tasima'])})", "yüksek oynaklık taşıması")
    bk = o["barbell_kurallar"]
    metinde(m, f"klasik ağırlıkla {sayi(bk['nakit']['konv_mn'], 2, True)} mn, PCA ağırlıkla "
               f"{sayi(bk['pca']['konv_mn'], 2, True)} mn", "konveksite değeri")
    metinde(m, f"(PCA ile {sayi(o['yapi_tasima']['flyPCA_long_bp'], 0, True)} bp", "long 2y5y7y taşıma")

    # ── 5.9 taşıma süzgeci
    F4 = ("2y5y7y", "1y2y5y", "3y5y7y", "2y3y5y")
    t = tablo(tl, "Süzgeç kolu (örneklem dışı PCA fly; ortalama bp · işlem · isabet)")
    for kk, ad in (("donus", "Dönüş: z ≥ +1 ya da z ≤ −1, ortalamaya doğru"),
                   ("uyumlu", "Uyumlu: dönüş işlemi, taşıma aynı yönde"),
                   ("ters", "Ters: dönüş işlemi, taşıma karşı yönde"),
                   ("tasima", "Taşıma: her ay taşımanın gösterdiği tarafta"), ("hep_long", "Hep long (kıyas)")):
        satir_sina(t, ad, [f"{sayi(FT[f][kk]['ort'], 1, True)} · {FT[f][kk]['n']} · {yz(FT[f][kk]['isabet'], 0)}" for f in F4],
                   "taşıma süzgeci")
    satir_sina(t, "Medyan: uyumlu · ters",
               [f"{sayi(FT[f]['uyumlu']['medyan'], 1, True)} · {sayi(FT[f]['ters']['medyan'], 1, True)}" for f in F4],
               "taşıma süzgeci")
    satir_sina(t, "t: taşıma kolu · hep long",
               [f"{sayi(FT[f]['tasima']['t'], 1, True)} · {sayi(FT[f]['hep_long']['t'], 1, True)}" for f in F4],
               "taşıma süzgeci")
    t = tablo(tl, "Uyumlu ve ters, iki yarıda (PCA fly; ortalama bp · işlem)")
    ters_say = 0
    for f in F4:
        c, tersine = [], []
        for kk in ("uyumlu", "ters"):
            for y in ("2013_2019", "2020_2026"):
                x = FT[f][kk]["yarilar"][y]
                c.append(f"{sayi(x['ort'], 1, True)} · {x['n']}")
        for y, ad in (("2013_2019", "2016–2019"), ("2020_2026", "2020–2026")):
            if FT[f]["uyumlu"]["yarilar"][y]["ort"] < FT[f]["ters"]["yarilar"][y]["ort"]:
                tersine.append(ad)
        ters_say += len(tersine)
        satir_sina(t, f, c + [" ve ".join(tersine) if tersine else "yok"], "süzgeç yarıları")
    metinde(m, f"sekiz karşılaştırmanın {['sıfırında', 'birinde', 'ikisinde', 'üçünde', 'dördünde', 'beşinde', 'altısında', 'yedisinde', 'sekizinde'][ters_say]}",
            "yarılarda tersine dönme sayısı")
    t = tablo(tl, "Gecikme profili (fly · kol; ortalama bp)")
    iyi = 0
    for f in F4:
        for kk, ad in (("donus", "dönüş"), ("uyumlu", "uyumlu"), ("ters", "ters"), ("tasima", "taşıma")):
            satir_sina(t, f"{f} · {ad}", [sayi(FT[f]["gecikme"][L][kk], 1, True) for L in ("1", "5", "10", "21")],
                       "gecikme profili")
        iyi += sum(FT[f]["gecikme"][L]["uyumlu"] > FT[f]["gecikme"][L]["ters"] for L in ("1", "5", "10", "21"))
    metinde(m, f"16 karşılaştırmanın {iyi}'sında", "uyumlu > ters sayısı")
    g1 = FT["1y2y5y"]["gecikme"]
    metinde(m, f"+{sayi(g1['1']['donus'], 1)}, beş günle +{sayi(g1['5']['donus'], 1)}, on günle +{sayi(g1['10']['donus'], 1)}, "
               f"yirmi bir günle +{sayi(g1['21']['donus'], 1)} bp", "1y2y5y gecikme")
    tk, hl = FT["1y2y5y"]["tasima"], FT["1y2y5y"]["hep_long"]
    metinde(m, f"{sayi(tk['ort'], 1, True)} bp, t {sayi(tk['t'], 1)}, iki yarıda\n   artı "
               f"({sayi(tk['yarilar']['2013_2019']['ort'], 1, True)} ve {sayi(tk['yarilar']['2020_2026']['ort'], 1, True)})",
            "1y2y5y taşıma kolu")
    metinde(m, f"hep long {sayi(hl['ort'], 1)} bp", "1y2y5y hep long")
    metinde(m, f"hep short'a üstünlüğü {sayi(tk['ort'] + hl['ort'], 1)} bp", "taşıma − hep short")
    metinde(m, f"{sayi(FT['1y2y5y']['tasima']['n'])} aylık giriş", "süzgeç giriş sayısı")

    # ── 5.10 ihale
    ie = o["ihale_etkisi"]
    t = tablo(tl, "İhale edilen vade → gövdesi o vade olan fly")
    for v, vad in (("2y", "2 yıl"), ("5y", "5 yıl")):
        for w, ad in (("50", "50:50 (kotasyon)"), ("pca", "PCA")):
            x = ie[v][w]
            satir_sina(t, f"{vad} → {ie[v]['fly']} {ad}",
                       [str(x["n"]), sayi(x["once_ort"], 1, True), sayi(x["once_medyan"], 1, True), sayi(x["once_t"], 2, True),
                        sayi(x["sonra_ort"], 1, True), sayi(x["sonra_medyan"], 1, True), sayi(x["sonra_t"], 2, True),
                        sayi(x["taban_sd"])], "ihale etkisi")
    x2, x5 = ie["2y"]["50"], ie["5y"]["pca"]
    metinde(m, f"{sayi(x2['once_ort'], 1, True)} bp (medyan {sayi(x2['once_medyan'], 1, True)}, t {sayi(x2['once_t'], 2)})",
            "ihale 2y önce")
    metinde(m, f"σ'sı {sayi(x2['taban_sd'])} bp", "ihale 2y σ")
    metinde(m, f"{sayi(x5['sonra_ort'], 1, True)}, σ {sayi(x5['taban_sd'])} bp", "ihale 5y PCA σ")
    metinde(m, f"(PCA {sayi(ie['5y']['pca']['once_ort'], 1, True)} bp, t {sayi(ie['5y']['pca']['once_t'], 2)})",
            "ihale 5y önce (alıştırma)")

    # ── 5.11 boyut, stop, dosyalar, karar ağacı
    # bütçe bir ölçüm değil, metnin varsayımsal kutusunda duran bir varsayım: tablo başlığından okunur
    t = tablo(tl, "Yapı (aylık 1σ bütçesi")
    butce = float(t[0][0].split("bütçesi ")[1].split(" mn TL")[0].replace(",", ".")) * 1e6 if t else 0.0
    if t and f"aylık 1σ risk bütçesi {sayi(butce / 1e6)} mn TL olsun" not in m:
        hatalar.append("boyut: varsayımsal bütçe kutuda yazılı değil ya da başlıkla aynı değil")
    dv = lambda s_: "≈ " + sayi(round(butce / s_, -2)) + " TL/bp"
    for ad, kk in (("2 yıllık outright", None), ("2s7s spread", "2s7s"), ("2y5y7y fly (50:50)", "2y5y7y_50"),
                   ("2y5y7y fly (PCA)", "2y5y7y_pca"), ("1y2y5y fly (50:50)", "1y2y5y_50"), ("1y2y5y fly (PCA)", "1y2y5y_pca"),
                   ("1y2y3y fly (PCA)", "1y2y3y_pca"), ("2y3y5y fly (PCA)", "2y3y5y_pca"), ("3y5y7y fly (PCA)", "3y5y7y_pca")):
        if kk is None:
            s_, s36, p95 = (o["kalicilik"]["seri"]["2y"]["sigma_bp_ay"], o["bugun"]["sigma36"]["n2y"],
                            o["stres"]["n2y"]["p95_mutlak"])
        else:
            s_, s36, p95 = S[kk]["sigma"], S[kk]["sigma36"], S[kk]["p95"]
        satir_sina(t, ad, [sayi(s_), sayi(s36), sayi(p95), dv(s_), dv(s36)], "boyut")
    sp = S["2y5y7y_pca"]
    metinde(m, f"2y5y7y'de {sayi(round(butce / sp['sigma'], -2))} yerine {sayi(round(butce / sp['sigma36'], -2))} TL/bp",
            "boyut son 36 ay")
    metinde(m, f"aylık 2σ tam örneklemle {sayi(2 * sp['sigma'])} bp, son 36 ayla {sayi(2 * sp['sigma36'])} bp", "stop 2σ")
    metinde(m, f"{sayi(2 * sp['sigma'] / o['yapi_tasima']['flyPCA_long_bp'], 1)} ile "
               f"{sayi(2 * sp['sigma36'] / o['yapi_tasima']['flyPCA_long_bp'], 1)} katıdır", "stop / taşıma")
    metinde(m, f"{sayi(sp['p95'])}'e karşı {sayi(sp['en_buyuk_dusus'][0], 0, True)}", "stres uç 2y5y7y")
    metinde(m, f"{sayi(S['1y2y5y_pca']['p95'])}'e karşı {sayi(S['1y2y5y_pca']['en_buyuk_dusus'][0], 0, True)}", "stres uç 1y2y5y")
    fp = o["fly_pnl_ayrisimi"]
    metinde(m, f"{yz(fp['2y5y7y_pca']['pay']['artik'], 0)}'ü artıktır", "artık payı")
    metinde(m, f"seviye korelasyonu {sayi(fp['2y5y7y_pca60']['korelasyon_seviye'], 2)}", "60 aylık sızıntı")
    t = tablo(tl, "Satır (doldurulmuş iki işlem dosyası)")
    satir_sina(t, "Ağırlık", [f"{sayi(H['2y5y7y_pca']['a'], 3)} · {sayi(H['2y5y7y_pca']['b'], 3)}",
                              f"{sayi(H['1y2y5y_pca']['a'], 3)} · {sayi(H['1y2y5y_pca']['b'], 3)}"], "dosyalar")
    satir_sina(t, "Boyut (son 36 ay σ)", [f"aylık σ {bp(S['2y5y7y_pca']['sigma36'])}", f"aylık σ {bp(S['1y2y5y_pca']['sigma36'])}"],
               "dosyalar")
    for p in (f"+{sayi(H['2y5y7y_pca']['tasima_long_bp'])} bp toplar, neredeyse tamamı roll",
              f"+{sayi(-H['1y2y5y_pca']['tasima_long_bp'])} bp toplar (short taraf)",
              f"seviye {bp(H['2y5y7y_pca']['seviye_bp'], True)}, yüzdelik {sayi(H['2y5y7y_pca']['yuzdelik'])}, z "
              f"{sayi(H['2y5y7y_pca']['z36'], 2, True)}",
              f"seviye {bp(H['1y2y5y_pca']['seviye_bp'])}, yüzdelik {sayi(H['1y2y5y_pca']['yuzdelik'])}",
              f"temsili eğride {sayi(OF['2y5y7y']['pca']['toplam_bp_govde'], 0, True)} bp öder",
              f"OIS'te {sayi(OF['1y2y5y']['pca']['toplam_bp_govde'], 0, True)} bp toplar",
              f"({sayi(R['cipa']['2y5y7y_longpca']['koridor_alt']['toplam'], 0, True)}, {R['cipa']['2y5y7y_longpca']['koridor_alt']['n']} pencere)",
              f"(long {sayi(R['cipa']['1y2y5y_longpca']['koridor_alt']['toplam'], 0, True)}, {R['cipa']['1y2y5y_longpca']['koridor_alt']['n']} pencere)"):
        metinde(m, p, "dosya metni")
    yt = o["yapi_tasima"]
    for p in (f"2s5s dikleştirici {bp(yt['2s5s_diklestirici_bp'], True)} toplar",
              f"2s5s yassılaştırıcı {bp(yt['2s5s_yassilastirici_bp'])} öder",
              f"short fly {bp(-yt['flyPCA_long_bp'])} öder", f"short fly {bp(-H['1y2y5y_pca']['tasima_long_bp'], True)} toplar",
              f"(2s7s {sayi(yt['2s7s_yassilastirici_bp'])}, 2s5s {bp(yt['2s5s_yassilastirici_bp'])})"):
        metinde(m, p, "karar ağacı ve alıştırma taşıması")

    # ── Pratik — Bölüm 5
    kl, kt = o["kalicilik"], o["katalog"]
    for p in (f"korelasyonu {sayi(kl['fly50_korelasyon'][0], 2)}", f"{sayi(o['kalicilik']['seri']['fly50']['sigma_bp_ay'] / 2)} bp'den (50:50; kotasyon biriminde\n"
              f"{sayi(kl['seri']['fly50']['sigma_bp_ay'])} bp) {sayi(kl['seri']['flyPCA']['sigma_bp_ay'])} bp'ye",
              f"({sayi(kl['agirlik_donem']['2013_2019'][0], 3)} · {sayi(kl['agirlik_donem']['2013_2019'][1], 3)})",
              f"ortalama −{sayi(-R['faz']['2y5y7y_long50']['artırım']['toplam'])} bp, yani short\ntaraf +"
              f"{sayi(-R['faz']['2y5y7y_long50']['artırım']['toplam'])} bp",
              f"(beta\n{sayi(o['egim_seviye']['donem']['2023-07_2026']['beta_7y_2y'], 2)})",
              f"+{sayi(o['fly_orneklem_disi']['ayrik']['pca']['net_ort'], 1)} bp'ye, 2020–2026'da "
              f"+{sayi(o['fly_orneklem_disi']['ayrik']['pca']['yarilar']['2020_2026']['net_ort'], 1)} bp'ye",
              f"{sayi(fb['fly']['1y3y5y_50']['tasima_long_bp'], 0, True)}, {sayi(fb['fly']['1y3y7y_50']['tasima_long_bp'], 0, True)} ve "
              f"{sayi(fb['fly']['1y5y7y_50']['tasima_long_bp'], 0, True)} bp",
              f"1y3y5y {sayi(fb['fly']['1y3y5y_50']['z36'], 2, True)}, 1y3y7y {sayi(fb['fly']['1y3y7y_50']['z36'], 2, True)}, 1y5y7y\n"
              f"{sayi(fb['fly']['1y5y7y_50']['z36'], 2, True)}",
              f"1y3y5y PCA z {sayi(fb['fly']['1y3y5y_pca']['z36'], 2)}; 50:50 yüzdeliği {sayi(fb['fly']['1y3y5y_50']['yuzdelik'])}, "
              f"PCA yüzdeliği\n{sayi(fb['fly']['1y3y5y_pca']['yuzdelik'])}",
              f"için {sayi(o['tasima_oynaklik']['5y_receive']['oran'], 2)})",
              f"taşıma/oynaklık oranı {sayi(H['2y5y7y_pca']['tasima_sigma'], 2, True)}",
              f"= {sayi(-(fb['basabas_bp']['n2y'] - 0.5 * fb['basabas_bp']['n1y'] - 0.5 * fb['basabas_bp']['n5y']), 0)}$ bp".replace("−", "-"),
              f"çeyrekte **{sayi(fb['basabas_bp']['n2y'] - 0.5 * fb['basabas_bp']['n1y'] - 0.5 * fb['basabas_bp']['n5y'], 0, True)} bp** toplar",
              f"kanatlar {sayi(OF['2y5y7y']['pca']['nominal_mn']['2y'], 1)} ve {sayi(OF['2y5y7y']['pca']['nominal_mn']['7y'], 1)} mn",
              f"yüzen {sayi(OF['2y5y7y']['pca']['net_yuzen_mn'], 1)} mn, TLREF +100 bp'nin çeyreklik etkisi\n"
              f"{sayi(OF['2y5y7y']['pca']['tlref_100_etkisi_bin'])} bin TL"):
        if p:
            metinde(m, p, "pratik")
    # bileşik duyarlılık: (1 + r/365)^91 ve basit hesap
    r = OF["tlref"] / 100
    metinde(m, f"≈ {sayi((1 + r / 365) ** (OF['gun'] - 1), 2)}", "bileşik duyarlılık")
    basit = -a5["net_yuzen_mn"] * 0.01 * OF["gun"] / 365
    metinde(m, f"\\approx {sayi(basit, 3)}$ mn TL", "basit fixing etkisi")


# W7_dogrula
def kontrol_w7(o, m, tl):
    bg = o["bugun"]
    T = bg["tasima"]
    yb = o["yapi_bugun"]
    fh = o["fly_tasima_haritasi"]["fly"]
    tm = o["tumsek"]
    tb = o["tlref_baz"]
    sm = o["senaryo_matrisi"]
    rj = o["rejim_yapi"]
    to = o["tasima_oynaklik"]
    ts = o["tasima_stratejileri"]
    ta = o["tasima_ayristirma"]
    fg = o["fonlama_gecis"]["gecis"]
    ft = o["fly_tasima_filtresi"]
    ie = o["ihale_etkisi"]
    fm = o["faktor_maruziyet"]
    pc = o["pca"]
    fp = o["fly_pnl_ayrisimi"]
    ar = o["aylik_rejim"]
    dn = {x["tarih"]: x for x in o["donum_noktalari"]}
    ofly = o["ois_fly"]
    oy = o["ois_yapilar"]
    orh = o["ois_roll_haritasi"]
    okf = o["ois_kira_fixing"]
    fw = o["forward_gerceklesme"]
    kt = o["katalog"]
    s3 = math.sqrt(3)

    def gun(s):
        return f"{s[8:10]}.{s[5:7]}.{s[:4]}"

    def gunk(s):
        return f"{s[8:10]}.{s[5:7]}"

    # ── 6.1 teşhis tablosu
    t = tablo(tl, "Teşhis ölçüsü (22.09.2026 kâğıt eğrisi)")
    satir_sina(t, f"Taşıma + roll (3 ay, fonlama TLREF bileşik {yz(bg['tlref_etkin'])})",
               [f"6 ay {yz(T['0.5']['toplam_yuzde'], arti=True)} · 2 yıl {yz(T['2']['toplam_yuzde'], arti=True)} · "
                f"5 yıl {yz(T['5']['toplam_yuzde'], arti=True)} · 7 yıl {yz(T['7']['toplam_yuzde'], arti=True)}"],
               "W7 teşhis")
    satir_sina(t, "Başabaş (3 ay)",
               [f"1 yıl {bp(T['1']['basabas_bp'])} · 2 yıl {bp(T['2']['basabas_bp'])} · "
                f"5 yıl {bp(T['5']['basabas_bp'])} · 7 yıl {bp(T['7']['basabas_bp'])}"], "W7 teşhis")
    if tm["bugun"] != "n2y":
        hatalar.append(f"W7 teşhis: tümsek artık 2 yılda değil ({tm['bugun']})")
    satir_sina(t, "Tümsek (en yüksek getirili düğüm)",
               [f"2 yıl, {tm['bugun_sure_ay']} aydır tepede (tarihte ayların {yz(tm['pay']['n2y'], 0)}'unda tepe "
                f"2 yıldaydı ve ortalama {sayi(tm['ort_sure_ay']['n2y'], 1)} ay kaldı)"], "W7 teşhis")
    r26 = tb["rejim_2026"]
    pol = [r for r in r26 if r["cipa"] == "politika"][-1]
    tav = [r for r in r26 if r["cipa"] == "koridor_ust"][-1]
    satir_sina(t, "Fonlama çıpası (TLREF)",
               [f"politika faizi: fixing {yz(bg['tlref'])}, politika {yz(bg['politika'], 0)}; {gun(pol['bas'])}'dan "
                f"beri (tavan bloğu {gunk(tav['bas'])}–{gun(tav['son'])}, {tav['is_gunu']} iş günü)"], "W7 teşhis")
    satir_sina(t, "Seviye yüzdeliği (2013–2026 / son 36 ay)",
               [" · ".join(f"{a} {sayi(yb[k]['yuzdelik'])} / {sayi(yb[k]['yuzdelik_son36'])}"
                           for k, a in (("2y", "2 yıl"), ("5y", "5 yıl"), ("7y", "7 yıl")))], "W7 teşhis")
    satir_sina(t, "Spread (seviye; yüzdelik tam / son 36 ay)",
               [" · ".join(f"{k} {bp(yb[k]['seviye'], True)} ({sayi(yb[k]['yuzdelik'])} / "
                           f"{sayi(yb[k]['yuzdelik_son36'])})" for k in ("2s5s", "2s7s"))], "W7 teşhis")
    f1, f2 = fh["2y5y7y_pca"], fh["1y2y5y_pca"]
    satir_sina(t, "Fly (PCA; yüzdelik, z: son 36 ay sonuna göre)",
               [f"2y5y7y {bp(f1['seviye_bp'], True)} (yüzdelik {sayi(f1['yuzdelik'])}, z {sayi(f1['z36'], 2, True)}) · "
                f"1y2y5y {bp(f2['seviye_bp'], True)} (yüzdelik {sayi(f2['yuzdelik'])}, z {sayi(f2['z36'], 2, True)})"],
               "W7 teşhis")
    # "on PCA fly'ın hiçbirinde |z| ≥ 1 yok" iddiası ölçüme karşı
    pca_z = [v["z36"] for k, v in fh.items() if k.endswith("_pca")]
    sayac["metin"] += 1
    if len(pca_z) != 10 or any(abs(z) >= 1 for z in pca_z):
        hatalar.append(f"W7: 'on PCA fly'da |z| ≥ 1 yok' iddiası tutmuyor: {pca_z}")

    # ── 6.1 metin
    metinde(m, f"**{yz(o['tasima_ufuk']['h91']['2']['forward'])}**", "W7 2y forward")
    rjk = rj
    metinde(m, f"ortalama sürpriz **{bp(rjk['surpriz_ort'], True)}**, medyanı **{bp(rjk['surpriz_medyan'], True)}**",
            "W7 sürpriz")
    metinde(m, f"temsili OIS eğrisinde 1 yıllık receive **{bp(orh['1y']['toplam_bp'])} öder**", "W7 OIS kira")

    # ── 6.2 senaryo matrisi (Şekil 17'nin sayısal hâli)
    metinde(m, "17_senaryo_matrisi.html", "W7 Şekil 17")
    R = ("indirim", "sabit", "artırım", "guvercin", "orta", "sahin", "satis", "ralli")
    YAPI = (("2y_receive", "2y receive"), ("5y_receive", "5y receive"), ("7y_receive", "7y receive"),
            ("2s5s_diklestirici", "2s5s dikleştirici"), ("2s7s_diklestirici", "2s7s dikleştirici"),
            ("1y2y3y_longpca", "long 1y2y3y (PCA)"), ("1y2y5y_long50", "long 1y2y5y (50:50)"),
            ("1y2y5y_longpca", "long 1y2y5y (PCA)"), ("2y3y5y_longpca", "long 2y3y5y (PCA)"),
            ("2y5y7y_long50", "long 2y5y7y (50:50)"), ("2y5y7y_longpca", "long 2y5y7y (PCA)"),
            ("3y5y7y_longpca", "long 3y5y7y (PCA)"))
    t = tablo(tl, "Yapı (senaryo matrisi, 3 ay, DV01 başına bp)")
    for k, ad in YAPI:
        satir_sina(t, ad, [sayi(sm[k]["tasima_bugun"], 0, True)] + [sayi(sm[k][r]["ort"], 0, True) for r in R],
                   "W7 senaryo")
    t = tablo(tl, "Çeyrekler arası aralık (senaryo, p25 · p75, DV01 başına bp)")
    for k, ad in (("2y_receive", "2y receive"), ("2s5s_diklestirici", "2s5s dikleştirici"),
                  ("2s7s_diklestirici", "2s7s dikleştirici"), ("1y2y5y_long50", "long 1y2y5y (50:50)"),
                  ("1y2y5y_longpca", "long 1y2y5y (PCA)"), ("2y3y5y_long50", "long 2y3y5y (50:50)"),
                  ("2y5y7y_longpca", "long 2y5y7y (PCA)")):
        satir_sina(t, ad, [f"{sayi(sm[k][r]['p25'], 0, True)} · {sayi(sm[k][r]['p75'], 0, True)}" for r in R],
                   "W7 senaryo aralığı")
    fn = rj["faz_n"]
    metinde(m, f"126 pencerenin {fn['indirim']}'i indirim", "W7 faz n")
    sayac["metin"] += 1
    if sum(fn.values()) != 126:
        hatalar.append(f"W7: faz pencere toplamı 126 değil ({sum(fn.values())})")
    metinde(m, f"{fn['artırım']}'ü artırım", "W7 faz n")
    ks, kv = rj["kova_sinir_bp"], rj["kova_surpriz"]
    metinde(m, f"sınırlar {bp(ks[0])} ve {bp(ks[1], True)}, kova ortalamaları {bp(kv['guvercin'])}, "
               f"{bp(kv['orta'], True)} ve {bp(kv['sahin'], True)}", "W7 kova")
    metinde(m, f"{rj['kova_n']['guvercin']}'er pencere", "W7 kova n")
    qs, qv = rj["kuyruk_sinir_bp"], rj["kuyruk_seviye"]
    metinde(m, f"sınırlar {bp(qs[0])} ve {bp(qs[1], True)}, ortalamalar {bp(qv['ralli'])} ve {bp(qv['satis'], True)}",
            "W7 kuyruk")
    metinde(m, f"{rj['kuyruk']['2y_receive']['satis']['n']}'şer pencere", "W7 kuyruk n")
    metinde(m, f"tam örneklemde {sayi(o['kalicilik']['seri']['2y']['sigma_bp_ay'])} bp, son 36 ayda "
               f"{sayi(bg['sigma36']['n2y'])} bp", "W7 2y oynaklık")

    # ── 6.3 özet karar matrisi: taşıma sütunu
    t = tablo(tl, "Kart (beklenti)")
    p2 = bp(-to["2y_receive"]["tasima_bp"], True)
    tas = {
        "K1 Gevşeme fiyatlanandan hızlı": f"evet: 2s5s dikleştirici {bp(to['2y5y_diklestirici']['tasima_bp'], True)}",
        "K2 Gevşeme fiyatlanandan yavaş": f"evet: 2 yıllık pay {p2}",
        "K3 Sıkılaşma, artırım": f"evet: 2 yıllık pay {p2}",
        "K4 Kur ya da risk şoku": f"evet: 2 yıllık pay {p2}",
        "K5 Fonlama tavana çıkar": f"evet: 2 yıllık kısa kâğıt {p2}",
        "K7 Kalıcı dezenflasyon, ralli": f"hayır: 2 yıllık {bp(to['2y_receive']['tasima_bp'])}, "
                                         f"7 yıllık {bp(to['7y_receive']['tasima_bp'])}",
        "K8 Vade primi yükselir": f"evet: 7 yıllık pay {bp(-to['7y_receive']['tasima_bp'], True)}",
        "K9 Tümsek çöker": f"evet: short 1y2y5y (PCA) {bp(-to['1y2y5y_longpca']['tasima_bp'], True)}",
        "K11 Arz bir vadeye yığılır": f"evet: long 2y5y7y (PCA) {bp(to['2y5y7y_longpca']['tasima_bp'], True)}",
        "K12 Oynaklık artar": f"long 2y5y7y (PCA) {bp(to['2y5y7y_longpca']['tasima_bp'], True)}, "
                              f"oynaklıktan değil taşımadan",
    }
    for ilk, v in tas.items():
        satir_sina(t, ilk, [None, None, None, None, v], "W7 özet matrisi")

    # ── 6.3 kartlar: metin parçaları (ölçülmüş)
    fz, kv_, ku, cp = rj["faz"], rj["kova"], rj["kuyruk"], rj["cipa"]

    def rb(x, arti=True):
        return bp(x["toplam"], arti)

    # K1
    metinde(m, f"{rb(kv_['2y_receive']['guvercin'])}, isabet {yz(kv_['2y_receive']['guvercin']['isabet'], 0)}",
            "W7 K1")
    metinde(m, f"{rb(kv_['2s5s_diklestirici']['guvercin'])}, isabet "
               f"{yz(kv_['2s5s_diklestirici']['guvercin']['isabet'], 0)}", "W7 K1")
    metinde(m, f"{rb(fz['2y_receive']['indirim'])} ve {yz(fz['2y_receive']['indirim']['isabet'], 0)}", "W7 K1")
    metinde(m, f"(1 yılda {sayi(fh['1y2y5y_pca']['a'], 3)}, 5 yılda {sayi(fh['1y2y5y_pca']['b'], 3)})", "W7 K1")
    metinde(m, f"fixing %36,49 varsayımıyla {bp(okf['1y']['bugun'])} fixing ve {bp(orh['1y']['roll_bp'])}", "W7 K1")
    sayac["metin"] += 1
    if abs(okf["fixing"]["bugun"] - bg["tlref"]) > 1e-9:
        hatalar.append("W7: OIS kira fixingi ile bugünkü TLREF ayrışmış")
    # K2
    metinde(m, f"isabet {yz(kv_['2y_receive']['orta']['isabet'], 0)}: pay tarafı", "W7 K2")
    metinde(m, f"{rb(fz['2y_receive']['sabit'])}, isabet {yz(fz['2y_receive']['sabit']['isabet'], 0)}", "W7 K2")
    metinde(m, f"{sayi(sm['2y_receive']['orta']['p25'], 0, True)} · {sayi(sm['2y_receive']['orta']['p75'], 0, True)} bp",
            "W7 K2")
    st = o["stres"]
    metinde(m, f"{bp(st['n2y']['en_buyuk_dusus'][0])} ({ay(st['n2y']['en_buyuk_dusus'][1])})", "W7 K2 stres")
    metinde(m, f"%39,95'te {bp(okf['3m']['temsili'])} iken %36,49'da {bp(okf['3m']['bugun'], True)}", "W7 K2 3m")
    # K3
    metinde(m, f"{rb(kv_['2y_receive']['sahin'])} (isabet {yz(kv_['2y_receive']['sahin']['isabet'], 0)})", "W7 K3")
    metinde(m, f"{rb(kv_['2s7s_diklestirici']['sahin'])} ({yz(kv_['2s7s_diklestirici']['sahin']['isabet'], 0)})",
            "W7 K3")
    metinde(m, f"{rb(kv_['1y2y5y_long50']['sahin'])} ({yz(kv_['1y2y5y_long50']['sahin']['isabet'], 0)})", "W7 K3")
    metinde(m, f"{rb(kv_['2y3y5y_long50']['sahin'])}", "W7 K3")
    metinde(m, f"{rb(fz['2y_receive']['artırım'])} ({yz(fz['2y_receive']['artırım']['isabet'], 0)})", "W7 K3")
    art = ar["faz"]["artırım"]
    metinde(m, f"{art['n']} artırım ayında 2 yıllık", "W7 K3 aylık")
    metinde(m, f"ortalama {bp(art['2y'], True)}, 2s5s {bp(art['2s5s'])}", "W7 K3 aylık")
    sayac["metin"] += 1
    if o["kadran"]["faz"]["artırım"]["boğa dikleşme"] != 0:
        hatalar.append("W7 K3: artırım aylarında boğa dikleşme artık sıfır değil")
    d25 = dn["2025-04-17"]
    metinde(m, f"{sayi(d25['adim_bp'])} bp'lik artırımdan sonra 2 yıllık üç ayda "
               f"{sayi(-d25['hareket']['3a']['2y'])} bp", "W7 K3 dönüm")
    art_don = [x for x in o["donum_noktalari"] if x["yon"] == "artırım"]
    ind_don = [x for x in o["donum_noktalari"] if x["yon"] == "indirim"]
    sayac["metin"] += 2
    if (len(art_don), sum(x["hareket"]["3a"]["2y"] > 0 for x in art_don)) != (4, 3):
        hatalar.append("W7: 'artırıma dönülen dört kararın üçünde 2 yıllık yükseldi' tutmuyor")
    if (len(ind_don), sum(x["hareket"]["3a"]["2y"] > 0 for x in ind_don)) != (4, 3):
        hatalar.append("W7: 'indirime dönülen dört kararın üçünde 2 yıllık yükseldi' tutmuyor")
    # K4
    metinde(m, f"{rb(ku['2y_receive']['satis'])} (isabet {yz(ku['2y_receive']['satis']['isabet'], 0)})", "W7 K4")
    for k in ("1y2y5y_long50", "2y3y5y_long50", "2y5y7y_longpca"):
        metinde(m, f"{rb(ku[k]['satis'])} ({yz(ku[k]['satis']['isabet'], 0)})", "W7 K4")
    sr = ar["stres"]
    metinde(m, f"{sr['n']} stres ayında 2", "W7 K4 stres")
    metinde(m, f"ortalama {bp(sr['2y'], True)}, 7 yıllık {bp(sr['7y'], True)}, 2s7s {bp(sr['2s7s'])}", "W7 K4 stres")
    metinde(m, f"1y2y5y 50:50 kotasyonu {bp(sr['1y2y5y'], True)}", "W7 K4 stres")
    metinde(m, f"2y5y7y 50:50 kotasyonu {bp(sr['2y5y7y'])}", "W7 K4 stres")
    metinde(m, f"{rb(ku['2s7s_diklestirici']['satis'])} (isabet {yz(ku['2s7s_diklestirici']['satis']['isabet'], 0)})",
            "W7 K4")
    # K5
    g = fg["politika>koridor_ust"]
    for x in g["tarih"]:
        metinde(m, gun(x), "W7 K5 tarihler")
    metinde(m, f"1 yıllık {bp(g['d20']['n1y'], True)}, 2 yıllık {bp(g['d20']['n2y'], True)}", "W7 K5")
    sayac["metin"] += 1
    if g["d20_2y_isaret"] != g["n"] or g["n"] != 4:
        hatalar.append("W7 K5: '2 yıllık dördünün dördünde yükseldi' tutmuyor")
    metinde(m, f"2 yıllık {bp(g['d525']['n2y'], True)}", "W7 K5 d525")
    metinde(m, f"2 yılda {bp(g['d20']['n2y'], True)}, 5\n  yılda {bp(g['d20']['n5y'], True)}, 7 yılda "
               f"{bp(g['d20']['n7y'], True)}", "W7 K5 spread")
    metinde(m, f"2s5s {bp(g['d20']['n5y'] - g['d20']['n2y'])}, 2s7s {bp(g['d20']['n7y'] - g['d20']['n2y'])}",
            "W7 K5 spread")
    metinde(m, f"yalnız {bp(2 * g['d20']['n2y'] - g['d20']['n1y'] - g['d20']['n5y'], True)} oynadı", "W7 K5 fly")
    bl = tb["tavan_blok_2026"]
    metinde(m, f"ortalama {sayi(bl['baz_ort_bp'])} bp üstündeydi", "W7 K5 tavan")
    metinde(m, f"{bl['takvim_gunu']}\n  takvim gününde {sayi(bl['maliyet_100mn_mn'], 2)} mn TL", "W7 K5 tavan")
    metinde(m, f"net {sayi(-oy['2y5y']['net_yuzen_mn'], 1)} mn TL yüzen öder", "W7 K5 OIS")
    metinde(m, f"{sayi(-oy['2y5y']['tlref_100_etkisi_bin'])} bin TL azaltır", "W7 K5 OIS")
    metinde(m, f"net {sayi(-ofly['2y5y7y']['5050']['net_yuzen_mn'], 1)} mn TL yüzen öder "
               f"({sayi(ofly['2y5y7y']['5050']['tlref_100_etkisi_bin'])} bin TL)", "W7 K5 OIS")
    metinde(m, f"%36,49'da\n  {bp(okf['1y']['bugun'])}, %39,95'te {bp(okf['1y']['temsili'])}", "W7 K5 kira")
    metinde(m, f"DV01 başına {sayi(okf['1y']['bugun'] - okf['1y']['temsili'])} bp ek", "W7 K5 kira farkı")
    metinde(m, f"onda\n  biri {sayi(o['ppk_gunu']['vade']['n3a']['ppk_p90'])} bp'yi aşıyor", "W7 K5 PPK")
    # K6
    g6 = fg["koridor_ust>politika"]
    metinde(m, f"({gun(g6['tarih'][0])},\n  " + ", ".join(gun(x) for x in g6["tarih"][1:]) + ")", "W7 K6 tarihler")
    metinde(m, f"1 yıllık {bp(g6['d20']['n1y'])}, 2 yıllık {bp(g6['d20']['n2y'])}, 5\n  yıllık "
               f"{bp(g6['d20']['n5y'], True)}", "W7 K6")
    sayac["metin"] += 1
    if g6["d20_2y_isaret"] != 2 or g6["n"] != 4:
        hatalar.append("W7 K6: '2 yıllık dördün ikisinde yükseldi' tutmuyor")
    sayac["metin"] += 1
    if any(x >= "2026-08-24" for x in g6["tarih"]):
        hatalar.append("W7 K6: 24.08.2026 geçişi artık ölçümde — metin 'girmedi' diyor")
    c2 = cp["2s5s_diklestirici"]["koridor_ust"]
    metinde(m, f"{rb(c2)} kazandı ({c2['n']} pencere, isabet {yz(c2['isabet'], 0)})", "W7 K6")
    metinde(m, f"%39,95'te {bp(okf['3m']['temsili'])}, %37'de {bp(okf['3m']['politika'], True)}", "W7 K6 3m")
    # K7
    metinde(m, f"{rb(ku['2y_receive']['ralli'])} (isabet {yz(ku['2y_receive']['ralli']['isabet'], 0)})", "W7 K7")
    metinde(m, f"{rb(ku['7y_receive']['ralli'])} ({yz(ku['7y_receive']['ralli']['isabet'], 0)})", "W7 K7")
    metinde(m, f"{rb(ku['2s7s_diklestirici']['ralli'])}\n  ({yz(ku['2s7s_diklestirici']['ralli']['isabet'], 0)})",
            "W7 K7")
    rl = ar["ralli"]
    metinde(m, f"{rl['n']} ralli ayında 2", "W7 K7 aylık")
    metinde(m, f"ortalama {bp(rl['2y'])}, 7 yıllık {bp(rl['7y'])}, 2s7s {bp(rl['2s7s'], True)}", "W7 K7 aylık")
    metinde(m, f"ayların yalnız {yz(o['kadran']['pay']['boğa yataylaşma'], 1)}'i", "W7 K7 kadran")
    metinde(m, f"long 1y2y5y (50:50) {rb(ku['1y2y5y_long50']['ralli'], False)}", "W7 K7 fly")
    metinde(m, f"receive {bp(orh['1y']['toplam_bp'])}, 5 yıllık {bp(orh['5y']['toplam_bp'])}, 7 yıllık "
               f"{bp(orh['7y']['toplam_bp'])}", "W7 K7 OIS")
    r7 = [sm[k]["ralli"]["ort"] / (to[k.replace("_receive", "_receive")]["sigma36_bp_ay"] * s3)
          for k in ("2y_receive", "5y_receive", "7y_receive")]
    metinde(m, f"(2 yıl {sayi(r7[0], 2)} · 5 yıl {sayi(r7[1], 2)} · 7 yıl {sayi(r7[2], 2)})", "W7 K7 oran")
    metinde(m, f"eğim\n  {sayi(fw['n7y']['beta'], 2)}", "W7 K7 forward")
    metinde(m, f"({bp(st['n2y']['en_buyuk_artis'][0], True)}, {ay(st['n2y']['en_buyuk_artis'][1])})", "W7 K7 stres")
    # K8
    metinde(m, f"ayların {yz(o['kadran']['pay']['ayı dikleşme'], 1)}'sidir", "W7 K8")
    ia = o["kadran"]["indirim_seviye_artti"]
    metinde(m, f"{len(ia)} indirim\n  ayının {sum(1 for x in ia if x[1] == 'ayı dikleşme')}'i ayı dikleşmedir",
            "W7 K8")
    es = o["egim_seviye"]
    metinde(m, f"tam örneklemde {sayi(es['beta_7y_2y'], 2)}, Temmuz 2023 sonrasında "
               f"{sayi(es['donem']['2023-07_2026']['beta_7y_2y'], 2)}", "W7 K8 beta")
    d21 = dn["2021-09-23"]["hareket"]["1a"]
    metinde(m, f"5 yıllık {bp(d21['5y'], True)}, 2s7s {bp(d21['2s7s'], True)}", "W7 K8 2021")
    metinde(m, f"{bp(st['n7y']['en_buyuk_dusus'][0])} ({ay(st['n7y']['en_buyuk_dusus'][1])})", "W7 K8 stres")
    # K9
    f9 = ft["1y2y5y"]
    metinde(m, f"{f9['tasima']['n']} ay): ortalama {bp(f9['tasima']['ort'], True, 1)}, t = "
               f"{sayi(f9['tasima']['t'], 1)}", "W7 K9")
    metinde(m, f"({sayi(f9['tasima']['yarilar']['2013_2019']['ort'], 1, True)} ve "
               f"{bp(f9['tasima']['yarilar']['2020_2026']['ort'], True, 1)})", "W7 K9 yarılar")
    metinde(m, f"okunursa {bp(f9['gecikme']['1']['tasima'], True, 1)}", "W7 K9 gecikme")
    metinde(m, f"eğriden {bp(f9['gecikme']['21']['tasima'], True, 1)}", "W7 K9 gecikme")
    metinde(m, f"hep long o yarıda {bp(f9['hep_long']['yarilar']['2020_2026']['ort'], False, 1)}, kural "
               f"{bp(f9['tasima']['yarilar']['2020_2026']['ort'], True, 1)}", "W7 K9 hep")
    metinde(m, f"{bp(ofly['1y2y5y']['5050']['toplam_bp_govde'], True)} (50:50) / "
               f"{bp(ofly['1y2y5y']['pca']['toplam_bp_govde'], True)} (PCA)", "W7 K9 OIS")
    metinde(m, f"(taşıma {sayi(-fh['1y2y5y_pca']['tasima_parca_bp'], 0, True)}, roll "
               f"{sayi(-fh['1y2y5y_pca']['roll_parca_bp'], 0, True)})", "W7 K9 parça")
    metinde(m, f"yarı ömür {sayi(o['fly_1y2y5y']['yari_omur_ay'], 1)} ay", "W7 K9 yarı ömür")
    sayac["metin"] += 1
    if sum(x["hareket"]["3a"]["1y2y5y_pca"] < 0 for x in ind_don) != 3:
        hatalar.append("W7 K9: 'indirime dönülen dört kararın üçünde 1y2y5y PCA düştü' tutmuyor")
    # K10
    od = o["fly_orneklem_disi"]["ayrik"]["pca"]
    metinde(m, f"{bp(od['net_ort'], True, 1)}\n  kazandırdı ({od['n']} işlem, isabet {yz(od['isabet_net'], 0)}; "
               f"2016–2019 {sayi(od['yarilar']['2016_2019']['net_ort'], 1, True)}, 2020–2026 "
               f"{bp(od['yarilar']['2020_2026']['net_ort'], True, 1)})", "W7 K10")
    metinde(m, bp(od["net_sd"], b=1), "W7 K10 sd")
    metinde(m, f"(2y5y7y {sayi(ft['2y5y7y']['uyumlu']['ort'], 1, True)}'e karşı "
               f"{bp(ft['2y5y7y']['ters']['ort'], True, 1)}; 1y2y5y {sayi(ft['1y2y5y']['uyumlu']['ort'], 1, True)}'e "
               f"karşı {bp(ft['1y2y5y']['ters']['ort'], True, 1)})", "W7 K10 süzgeç")
    ters_sayi = sum(
        (ft[f]["uyumlu"]["yarilar"][y]["ort"] < ft[f]["ters"]["yarilar"][y]["ort"])
        for f in ("2y5y7y", "1y2y5y", "3y5y7y", "2y3y5y") for y in ("2013_2019", "2020_2026"))
    sayac["metin"] += 1
    if ters_sayi != 4:
        hatalar.append(f"W7 K10: 'sekiz karşılaştırmanın dördünde sıra tersine dönüyor' tutmuyor ({ters_sayi})")
    sig50 = [(k, fh[k]) for k in ("1y3y5y_50", "1y3y7y_50", "1y5y7y_50")]
    sayac["metin"] += 1
    if any(v["sinyal"] != "short" or v["tasima_uyumlu"] for _, v in sig50):
        hatalar.append("W7 K10: 50:50 short sinyalleri değişti")
    metinde(m, f"1y3y5y\n  (z {sayi(fh['1y3y5y_50']['z36'], 2, True)}), 1y3y7y ({sayi(fh['1y3y7y_50']['z36'], 2, True)}) "
               f"ve 1y5y7y ({sayi(fh['1y5y7y_50']['z36'], 2, True)})", "W7 K10 z")
    metinde(m, "(" + ", ".join(sayi(v["tasima_long_bp"], 0, True) for _, v in sig50) + " bp)", "W7 K10 taşıma")
    metinde(m, f"tam örneklemde {sayi(o['kalicilik']['seri']['flyPCA']['sigma_bp_ay'])} bp", "W7 K10 σ")
    metinde(m, f"(2y5y7y PCA {sayi(kt['2y5y7y_pca']['yari_omur_ay'], 1)} ay)", "W7 K10 yarı ömür")
    # K11
    i5 = ie["5y"]["pca"]
    metinde(m, f"({i5['n']} ihale)", "W7 K11")
    metinde(m, f"ortalama {bp(i5['once_ort'], True, 1)} (medyan {sayi(i5['once_medyan'], 1, True)}, t = "
               f"{sayi(i5['once_t'], 2)})", "W7 K11")
    metinde(m, f"{bp(i5['sonra_ort'], False, 1)}\n  (t = {sayi(i5['sonra_t'], 2)})", "W7 K11")
    metinde(m, f"standart sapması {sayi(i5['taban_sd'])} bp", "W7 K11 taban")
    i2 = ie["2y"]["50"]
    metinde(m, f"{bp(i2['once_ort'], True, 1)}\n  (medyan {sayi(i2['once_medyan'], 1, True)}, t = {sayi(i2['once_t'], 2)})",
            "W7 K11 2y")
    metinde(m, f"teklif/satış medyanı {sayi(o['ihale']['sabit_2024']['5y']['tso_medyan'], 2)}", "W7 K11 talep")
    sayac["metin"] += 1
    if abs(fh["2y5y7y_pca"]["tasima_parca_bp"]) > 0.5:
        hatalar.append("W7 K11: 'long 2y5y7y PCA taşımasının tamamı roll' artık tutmuyor")
    # K12
    ob = o["oynaklik_barbell"]
    metinde(m, f"(günlük ortalama {sayi(ob['2y5y7y_long50']['yuksek']['oynaklik_bp_gun'])} bp)", "W7 K12")
    metinde(m, f"ortalama\n  {bp(ob['2y5y7y_long50']['yuksek']['toplam'])}, PCA {bp(ob['2y5y7y_longpca']['yuksek']['toplam'])}",
            "W7 K12")
    metinde(m, f"{sayi(ob['2y5y7y_long50']['orta']['toplam'], 0, True)} ve "
               f"{bp(ob['2y5y7y_longpca']['orta']['toplam'], True)}", "W7 K12")
    pg = o["ppk_gunu_yapi"]["2y5y7y_pca"]
    metinde(m, f"medyanı {sayi(pg['ppk_medyan'])} bp (diğer günler {sayi(pg['diger_medyan'])} bp)", "W7 K12 PPK")
    # K13 ve 6.4
    et = ts["egri_ticareti"]
    metinde(m, f"{bp(et['ort'], True, 1)}, t = {sayi(et['t'], 1)}", "W7 K13")
    metinde(m, f"{sayi(et['sd'])} bp", "W7 K13 sd")
    # K14
    f2y = fw["n2y"]
    metinde(m, f"eğim {sayi(f2y['beta'], 2, True)} (β = 1 sınamasının t'si\n  {sayi(f2y['t1'], 1)})", "W7 K14")
    metinde(m, f"ima edilen değişim {bp(f2y['fd_ort'])}, gerçekleşen {bp(f2y['dy_ort'], True)}", "W7 K14")
    # K15
    metinde(m, f"yarı\n  ömrü {sayi(kt['3a6a1y']['yari_omur_ay'], 1)} ay, dönüşün gürültüye oranı "
               f"{sayi(kt['3a6a1y']['donus_gurultu_3ay'], 2)}", "W7 K15")
    n3 = o["ppk_gunu"]["vade"]["n3a"]
    metinde(m, f"medyanı {sayi(n3['ppk_medyan'])} bp, 90. yüzdeliği {sayi(n3['ppk_p90'])} bp", "W7 K15")

    # ── 6.4 taşıma defteri tablosu
    t = tablo(tl, "Taşıma defteri adayı (22.09.2026)")
    DEF = (("short 1y2y3y (PCA)", "1y2y3y_longpca", -1), ("7 yıllık pay", "7y_receive", -1),
           ("5 yıllık pay", "5y_receive", -1), ("short 1y2y5y (PCA)", "1y2y5y_longpca", -1),
           ("long 2y5y7y (PCA)", "2y5y7y_longpca", 1), ("long 2y5y7y (50:50)", "2y5y7y_long50", 1),
           ("long 2y3y5y (50:50)", "2y3y5y_long50", 1), ("3 yıllık pay", "3y_receive", -1),
           ("short 1y2y3y (50:50)", "1y2y3y_long50", -1), ("2s5s dikleştirici", "2y5y_diklestirici", 1),
           ("long 2y3y5y (PCA)", "2y3y5y_longpca", 1), ("short 1y2y5y (50:50)", "1y2y5y_long50", -1),
           ("long 3y5y7y (PCA)", "3y5y7y_longpca", 1), ("2s7s dikleştirici", "2y7y_diklestirici", 1))
    for ad, k, y in DEF:
        v = to[k]
        satir_sina(t, ad, [sayi(y * v["tasima_bp"], 0, True), sayi(v["sigma36_bp_ay"]), sayi(y * v["oran"], 2)],
                   "W7 taşıma defteri")
    oran = [y * to[k]["oran"] for _, k, y in DEF]
    sayac["metin"] += 1
    if any(a < b for a, b in zip(oran, oran[1:])):
        hatalar.append("W7 taşıma defteri: sıra taşıma/σ'ya göre azalan değil")
    # zamanlama ≈ hep kısa (5 yıl)
    z5 = ta["zamanlama"]["n5y"]
    metinde(m, f"ortalama {yz(z5['zamanlama']['ort'], 1, True)} (t = {sayi(z5['zamanlama']['t'], 1)})", "W7 6.4")
    metinde(m, f"{yz(z5['hep_kisa']['ort'], 1, True)} (t = {sayi(z5['hep_kisa']['t'], 1)})", "W7 6.4")
    metinde(m, f"2013–2019'da kural {yz(z5['zamanlama']['yarilar']['2013_2019']['ort'], 1, True)}, hep kısa "
               f"{yz(z5['hep_kisa']['yarilar']['2013_2019']['ort'], 1, True)}", "W7 6.4 yarılar")
    metinde(m, f"2020–2026'da kural {yz(z5['zamanlama']['yarilar']['2020_2026']['ort'], 1, True)}, hep kısa "
               f"{yz(z5['hep_kisa']['yarilar']['2020_2026']['ort'], 1, True)}", "W7 6.4 yarılar")
    metinde(m, f"{yz(es['y2_ilk'])}'dı, {ay(es['y2_max'][1])}'te {yz(es['y2_max'][0])}", "W7 6.4 seviye")
    metinde(m, f"{et['n']} çeyrekte ortalama {bp(et['ort'], True, 1)}, medyan {bp(et['medyan'], True, 1)}, isabet "
               f"{yz(et['isabet'], 0)}, t = {sayi(et['t'], 1)}", "W7 6.4 eğri ticareti")
    metinde(m, f"(2015–2019 {bp(et['yarilar']['2013_2019']['ort'], True, 1)}, 2020–2026 "
               f"{bp(et['yarilar']['2020_2026']['ort'], True, 1)})", "W7 6.4 yarılar")
    metinde(m, "(" + " · ".join(sayi(et["gecikme"][L], 1) for L in ("1", "5", "10", "21")) + " bp)", "W7 6.4 gecikme")
    metinde(m, f"korelasyonu {sayi(et['seviye_korelasyon'], 2)}", "W7 6.4 seviye kor.")
    metinde(m, f"tutmak {bp(ts['en_iyi_uzun']['ort'], False, 1)}, sabit 2s7s dikleştirici "
               f"{bp(ts['sabit_2s7s_dik']['ort'], False, 1)}", "W7 6.4 kıyas")
    rec = {k: to[f"{k}_receive"]["oran"] for k in ("1y", "2y", "3y", "5y", "7y")}
    hi, lo = max(rec, key=rec.get), min(rec, key=rec.get)
    sayac["metin"] += 1
    if (hi, lo) != ("2y", "7y"):
        hatalar.append(f"W7 6.4: eğri ticaretinin bugünkü seçimi artık 2y/7y değil ({hi}/{lo})")
    metinde(m, f"2 yılı uzun (taşıma/σ {sayi(rec['2y'], 2)}), 7 yılı kısa ({sayi(rec['7y'], 2)})", "W7 6.4 seçim")
    metinde(m, f"2y5y7y'de {bp(ft['2y5y7y']['tasima']['ort'], False, 1)} (t = {sayi(ft['2y5y7y']['tasima']['t'], 1)}), "
               f"3y5y7y'de {bp(ft['3y5y7y']['tasima']['ort'], True, 1)}, 2y3y5y'de "
               f"{bp(ft['2y3y5y']['tasima']['ort'], True, 1)}", "W7 6.4 fly taşıması")
    metinde(m, f"{rb(ku['2s7s_diklestirici']['satis'])} (isabet {yz(ku['2s7s_diklestirici']['satis']['isabet'], 0)}), "
               f"ralli kuyruğunda\n{rb(ku['2s7s_diklestirici']['ralli'])}", "W7 6.4 kuyruk")
    metinde(m, f"satışta {rb(ku['2y5y7y_longpca']['satis'])}, rallide {rb(ku['2y5y7y_longpca']['ralli'], False)}",
            "W7 6.4 kuyruk")
    metinde(m, f"satışta {rb(ku['1y2y5y_longpca']['satis'], False)}, rallide {rb(ku['1y2y5y_longpca']['ralli'], False)}",
            "W7 6.4 kuyruk")
    metinde(m, f"korelasyonu {sayi(fp['2y5y7y_pca60']['korelasyon_seviye'], 2)}", "W7 6.4 pca60")

    # ── 6.5 faktör yükleri
    y1 = pc["yuk"]["pc1"]
    metinde(m, f"$2 \\times {sayi(y1['n2y'], 4)} - {sayi(y1['n1y'], 4)} - {sayi(y1['n5y'], 4)} = "
               f"+{sayi(2 * y1['n2y'] - y1['n1y'] - y1['n5y'], 3)}$".replace(",", "{,}"), "W7 6.5 seviye yükü")
    metinde(m, f"P&L'i {sayi(fm['2s5s_yassi_dv01'][0], 0, True)} TL", "W7 6.5")
    metinde(m, f"pay'inki {sayi(-fm['2y_uzun'][0], 0, True)} TL", "W7 6.5")
    metinde(m, f"%{sayi(100 * fm['2s5s_yassi_dv01'][0] / -fm['2y_uzun'][0])}'i kadar", "W7 6.5 oran")
    metinde(m, f"(2s7s'de %{sayi(100 * fm['2s7s_yassi_dv01'][0] / -fm['2y_uzun'][0])})", "W7 6.5 oran")
    c = fp["1y2y5y_pca"]["c"]
    s_buk = pc["sigma_bp_ay"][2]
    metinde(m, f"$-{sayi(c[2], 3)} \\times {sayi(s_buk, 1)} \\times 10.000 \\approx "
               f"{sayi(round(-c[2] * s_buk * 1e4, -3))}$".replace(",", "{,}").replace("−", "-"), "W7 6.5 short 1y2y5y")
    # long 2y3y5y (PCA): büküm katsayısı yüklerden ve ağırlıklardan
    y3 = pc["yuk"]["pc3"]
    f235 = fh["2y3y5y_pca"]
    c235 = y3["n3y"] - f235["a"] * y3["n2y"] - f235["b"] * y3["n5y"]
    metinde(m, f"ağırlıklardan ({sayi(f235['a'], 3)} · {sayi(f235['b'], 3)})", "W7 6.5 2y3y5y")
    metinde(m, f"$c = {sayi(y3['n3y'], 4)} - {sayi(f235['a'], 3)} \\times {sayi(y3['n2y'], 4)} + "
               f"{sayi(f235['b'], 3)}".replace(",", "{,}").replace("−", "-"), "W7 6.5 2y3y5y")
    metinde(m, "\\approx " + sayi(c235, 3).replace(",", "{,}") + "$, yük", "W7 6.5 2y3y5y")
    metinde(m, f"$0{{,}}062 \\times 142{{,}}8 \\approx {sayi(c235 * s_buk)}$ bp", "W7 6.5 2y3y5y payı")
    sayac["metin"] += 1
    if not (f235["tasima_long_bp"] > 0 and c235 > 0 and sayi(c235, 3) == "0,062"):
        hatalar.append("W7 6.5: long 2y3y5y (PCA) istisnası (lehte taşıma + ters büküm) artık tutmuyor")
    t = tablo(tl, "Faktör yükü (+1σ aylık şok, 10.000 TL/bp başına, TL)")
    for ad, v in (("2 yıllık kâğıt, uzun", fm["2y_uzun"]),
                  ("2s5s dikleştirici, DV01-nötr", [-x for x in fm["2s5s_yassi_dv01"]]),
                  ("2s7s dikleştirici, DV01-nötr", [-x for x in fm["2s7s_yassi_dv01"]]),
                  ("long 2y5y7y (50:50)", fm["fly50_long"]), ("long 2y5y7y (PCA)", fm["flyPCA_long"]),
                  ("short 1y2y5y (PCA)", [round(-ci * pc["sigma_bp_ay"][k] * 1e4, -3) + 0.0
                                          for k, ci in enumerate(c)]),
                  ("long 2y3y5y (PCA)", [0.0, 0.0, round(c235 * s_buk * 1e4, -3)])):
        satir_sina(t, ad, [sayi(x, 0, True) for x in v], "W7 faktör yükü")

    # ── 6.6 Vaka A tablosu
    t = tablo(tl, "Vaka A adayı (kâğıt eğrisi, DV01 başına bp)")
    for ad, k, sgk, y in (("2 yıllık kâğıt uzun", "2y_receive", "2y_receive", 1),
                          ("2s5s dikleştirici", "2s5s_diklestirici", "2y5y_diklestirici", 1),
                          ("short 1y2y5y (PCA)", "1y2y5y_longpca", "1y2y5y_longpca", -1)):
        s = sm[k]
        sig = to[sgk]["sigma36_bp_ay"]
        gv, sh = y * s["guvercin"]["ort"], y * s["sahin"]["ort"]
        lo_, hi_ = sorted((y * s["guvercin"]["p25"], y * s["guvercin"]["p75"]))
        satir_sina(t, ad, [sayi(y * s["tasima_bugun"], 0, True), sayi(gv, 0, True),
                           f"{sayi(lo_, 0, True)} · {sayi(hi_, 0, True)}", sayi(sh, 0, True), sayi(sig),
                           sayi(gv / (sig * s3), 2), sayi(sh / (sig * s3), 2)], "W7 Vaka A")
    metinde(m, f"toplam {bp(okf['1y']['bugun'] + orh['1y']['roll_bp'])}", "W7 Vaka A OIS")
    dA = [dn[x] for x in ("2019-07-25", "2021-09-23", "2024-12-26", "2025-07-24")]
    metinde(m, f"25.07.2019 {bp(dA[0]['hareket']['3a']['2y'])}, 23.09.2021 {bp(dA[1]['hareket']['3a']['2y'], True)}, "
               f"26.12.2024 {bp(dA[2]['hareket']['3a']['2y'], True)}", "W7 Vaka A dönüm")
    metinde(m, f"24.07.2025\n{bp(dA[3]['hareket']['3a']['2y'], True)}", "W7 Vaka A dönüm")
    metinde(m, f"(6.5: {sayi(fm['2s5s_yassi_dv01'][2] * -1)} ve {sayi(round(-c[2] * s_buk * 1e4, -3))} TL)",
            "W7 Vaka A büküm")
    # Vaka B
    metinde(m, f"fixing taşıması {bp(-okf['1y']['temsili'], True)}'ye yükselir", "W7 Vaka B")
    metinde(m, f"2 yıllık {sayi(g['d20']['n2y'])}/{sayi(bg['sigma36']['n2y'] * s3)} ≈ "
               f"{sayi(g['d20']['n2y'] / (bg['sigma36']['n2y'] * s3), 2)}", "W7 Vaka B oran")
    s27 = to["2y7y_diklestirici"]["sigma36_bp_ay"]
    metinde(m, f"{sayi(g['d20']['n2y'] - g['d20']['n7y'])}/{sayi(s27 * s3)} ≈ "
               f"{sayi((g['d20']['n2y'] - g['d20']['n7y']) / (s27 * s3), 2)}", "W7 Vaka B oran")
    # Vaka C
    metinde(m, f"günde {bp(i5['once_ort'], True, 1)} (t = {sayi(i5['once_t'], 2)}), sonraki beş günde "
               f"{bp(i5['sonra_ort'], False, 1)} (t = {sayi(i5['sonra_t'], 2)})", "W7 Vaka C")

    # ── 6.7 rutin tablosu
    t = tablo(tl, "Rutin (sıklık)")
    satir_sina(t, "Sabah: takvim", [None, None,
                                    f"olay öncesi boyut: 3 ayda karar günlerinin 90. yüzdeliği "
                                    f"{sayi(n3['ppk_p90'])} bp"], "W7 rutin")
    satir_sina(t, "Aylık: ağırlıklar", [None, f"ağırlıkların yeniden tahmini; gerçekleşen seviye korelasyonu "
                                              f"(2y5y7y'de {sayi(fp['2y5y7y_pca60']['korelasyon_seviye'], 2)})"],
               "W7 rutin")

    # ── Pratik (çözümlerdeki ölçülmüş girdiler)
    ob_ = o["oynaklik_barbell"]
    metinde(m, f"{bp(-sm['2y_receive']['sahin']['ort'], True)} ({sayi(to['2y_receive']['sigma36_bp_ay'])} bp)",
            "W7 pratik 2")
    metinde(m, f"long 2y3y5y (50:50)\n+{sayi(sm['2y3y5y_long50']['sahin']['ort'])} bp "
               f"({sayi(to['2y3y5y_long50']['sigma36_bp_ay'])} bp)", "W7 pratik 2")
    metinde(m, f"{sayi(oy['2y5y']['net_yuzen_mn'], 1)}; {sayi(ofly['2y5y7y']['5050']['net_yuzen_mn'], 1)}; "
               f"{sayi(ofly['1y2y5y']['pca']['net_yuzen_mn'], 1)} mn TL", "W7 pratik 4")
    metinde(m, f"{sayi(oy['2y5y']['tlref_100_etkisi_bin'])}, {sayi(ofly['2y5y7y']['5050']['tlref_100_etkisi_bin'])}, "
               f"{sayi(ofly['1y2y5y']['pca']['tlref_100_etkisi_bin'])} bin TL", "W7 pratik 4")
    y5 = o["yapi_stres"]["2y5y7y_pca"]
    metinde(m, f"en büyük aylık\ndüşüşü {bp(y5['en_buyuk_dusus'][0])} ({ay(y5['en_buyuk_dusus'][1])})", "W7 pratik 5")
    metinde(m, f"son 36 aylık aylık σ {sayi(y5['sigma36'])} bp", "W7 pratik 5")
    i2p = ie["2y"]["pca"]
    metinde(m, f"önce {bp(i2p['once_ort'], True, 1)} (t = {sayi(i2p['once_t'], 2)}), sonra "
               f"{bp(i2p['sonra_ort'], False, 1)}", "W7 pratik 6")
    metinde(m, f"sapması {sayi(i2['taban_sd'])} bp", "W7 pratik 6")
    metinde(m, f"fly {bp(i2['sonra_ort'], True, 1)} (t = {sayi(i2['sonra_t'], 2)})", "W7 pratik 6")
    metinde(m, f"50:50 kotasyonda {bp(fh['1y2y3y_50']['seviye_bp'], True)} (yüzdelik "
               f"{sayi(fh['1y2y3y_50']['yuzdelik'])})", "W7 pratik 6")


# ─────────────────────────────────────────────────────────────── 4 · genişletme sonu


# ─────────────────────────────────────────────────────────────── 3 · figürler
def sekiller() -> None:
    m = MDX.read_text(encoding="utf-8")
    for s in SEKILLER:
        if not (SEKIL / f"{s}.html").exists():
            hatalar.append(f"figür yok: {s}.html")
        no = s[:2]
        if f'src="/arastirma/kagit-ve-ois-trading/{s}.html"' not in m or f'no="{no}"' not in m:
            hatalar.append(f"figür metinde gömülü değil ya da numarası tutmuyor: {s}")


def main() -> int:
    o = arsiv()
    metin(o)
    sekiller()
    if hatalar:
        print(f"DÜŞTÜ: {len(hatalar)} bulgu")
        for h in hatalar:
            print("  ✗", h)
        return 1
    print(f"GEÇTİ: arşiv özleri tutuyor · {sayac['hucre']} tablo hücresi ve {sayac['metin']} metin "
          f"parçası ölçümle aynı · {len(SEKILLER)} figür yerinde")
    return 0


if __name__ == "__main__":
    sys.exit(main())
