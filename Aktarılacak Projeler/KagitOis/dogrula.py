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
3. FİGÜRLER: dokuz figür yayın dizininde var mı?

Koşum:  python3 dogrula.py
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
VERI = BURASI / "veri"
MDX = KOK / "site/src/content/arastirma/kagit-ve-ois-trading.mdx"
SEKIL = KOK / "site/public/arastirma/kagit-ve-ois-trading"
SEKILLER = ["01_egri_tasima", "02_durasyon_getiri", "03_tlref_politika", "04_pca", "05_kadran",
            "06_egim_seviye", "07_kalicilik", "08_fly_agirlik", "09_barbell_bullet"]

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
                 ("fly50_govde_al", "2y5y7y gövdeyi al, 50:50"), ("flyPCA_govde_al", "2y5y7y gövdeyi al, PCA-nötr")):
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
    t = tablo(tl, "Ağırlık | Gövde DV01'i başına taşıma + roll")
    satir_sina(t, "50:50", [f"{bp(ys['fly50_govde_al_bp_govde_dv01'])} (fly seviyesi cinsinden "
                            f"{bp(ys['fly50_govde_al_bp_fly'])})"], "fly taşıması")
    satir_sina(t, "PCA-nötr", [bp(ys["flyPCA_govde_al_bp"])], "fly taşıması")

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


# ─────────────────────────────────────────────────────────────── 3 · figürler
def sekiller() -> None:
    for s in SEKILLER:
        if not (SEKIL / f"{s}.html").exists():
            hatalar.append(f"figür yok: {s}.html")


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
