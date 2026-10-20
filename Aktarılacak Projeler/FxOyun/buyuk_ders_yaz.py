#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mum dersleri (serinin 6–9. dersleri): metin/<slug>.md şablonları → site/src/content/arastirma/<slug>.mdx.

Şablon dili ders_yaz.py ile aynı: `{{ anahtar }}` ölçüm dosyasından (veri/buyuk_ders.json) biçimlenmiş değer,
`{{# blok arg … }}` ölçümden kurulan tablo ya da figür. Şablonda ondalıklı ya da yüzdeli sayı ELLE yazılmaz; kapı
(dogrula.py → buyuk_dogrula.py) dersleri yeniden üretip yayımlanan dosyayla birebir kıyaslar.

  python3 buyuk_ders_yaz.py            # yaz
"""
from __future__ import annotations

import json
import re
import shlex
import sys
import tomllib
from pathlib import Path

from datetime import date, timedelta

BURASI = Path(__file__).resolve().parent
sys.path.insert(0, str(BURASI))
import ders_yaz as dy  # noqa: E402
import masa  # noqa: E402
from ders_yaz import _tablo, sayi, tam, yuzde  # noqa: E402

METIN = BURASI / "metin"
CIKTI = dy.CIKTI
D = json.loads((BURASI / "veri" / "buyuk_ders.json").read_text(encoding="utf-8"))
ON = tomllib.loads((BURASI / "onkayit_buyuk.toml").read_text(encoding="utf-8"))

SIRA = dy.BUYUK_SIRA
SEKIL = {
    "fx-buyuk-mum": ["01_ornek", "02_yol", "03_geri"],
    "fx-buyuk-suzgec": ["01_net", "02_yarisi"],
    "fx-buyuk-giris": ["01_izgara", "02_ters_secim", "03_maliyet"],
    "fx-buyuk-plan": ["01_bacaklar", "02_egri"],
}
TF = ["5", "15", "60"]
TF_AD = {"5": "5 dakika", "15": "15 dakika", "60": "1 saat"}
DONEM_AD = {"ic": "2018–23", "dis": "2024 →"}
HUKUM_AD = dy.HUKUM_AD
SUZ_AD = {"kova": "Büyüklük", "kapanis": "Kapanışın yeri", "seans": "Seans", "haber": "Takvimdeki büyük haber",
          "trend": "Günlük trend (EMA20)", "kosu": "Mumdan önceki 12 mum", "gun_ucu": "Mum günün yeni ucunu yaptı",
          "oynaklik": "Günlük oynaklık", "ardisik": "Önceki 4–24 mumda başka büyük mum"}
DEGER_AD = {"uc": "uca yakın (≥ %75)", "orta": "ortada (%50–75)", "geri": "geri verilmiş (< %50)",
            "asya": "Asya", "londra": "Londra", "ortusme": "Londra–New York örtüşmesi", "ny": "New York öğleden sonra",
            "haber": "var", "haber_yok": "yok", "trendle": "trend yönünde", "karsi": "trende karşı", "yatay": "yatay",
            "ayni": "aynı yönde koşu", "ters": "ters yönde koşu", "sakin": "sakin", "evet": "evet", "hayir": "hayır",
            "dusuk": "düşük", "orta_o": "orta", "yuksek": "yüksek",
            "2-3": "2–3 ATR", "3-4": "3–4 ATR", "4-5": "4–5 ATR", "5+": "5 ATR ve üstü"}
EMIR_AD = {"piyasa": "kapanışta piyasa", "limit_0.25": "%25 geri çekilmeye limit", "limit_0.5": "%50 geri çekilmeye limit",
           "limit_0.62": "%62 geri çekilmeye limit", "stop": "ucun kırılmasına stop", "onayli": "onay mumundan sonra piyasa",
           "limit_uc": "mumun ucuna limit", "limit_ote": "ucun yarım ATR ötesine limit"}
EMIR_AD_TERS = {"stop": "mumun yarısının kırılmasına stop"}
YON_AD = {"devam": "mumun yönünde", "ters": "mumun tersine"}
ORNEK_PIP_NOKTA = 10          # örnek mumlar EUR/USD (buyuk_ders_olcum.ORNEK_CIFT); bir pip on nokta


def deger_ad(f: str, v: str) -> str:
    return "orta" if (f == "oynaklik" and v == "orta") else DEGER_AD[v]


def emir_ad(y: str, e: str) -> str:
    return (EMIR_AD_TERS.get(e) if y == "ters" else None) or EMIR_AD[e]


def giris_ad(g: str) -> str:
    y, e, s, h = g.split(":")
    return f"{YON_AD[y]}, {emir_ad(y, e)}, stop {s[1:]} ATR, hedef {h[1:]} R"


def a(x: float) -> str:
    """ATR cinsinden hareket: iki ondalık, işaretli."""
    return sayi(x, 2, arti=True)


def r(x: float) -> str:
    return sayi(x, 2, arti=True)


def puan(x: float) -> str:
    return sayi(x * 100, 0, arti=True)


def puan1(x: float) -> str:
    """Aralık uçları için tek ondalık: tam sayıya yuvarlanan bir uç (+0,2 → "0") sıfırı kapsıyormuş gibi okunur."""
    return sayi(x * 100, 1, arti=True)


def tarih(iso: str) -> str:
    return ".".join(reversed(iso[:10].split("-")))


def is_gunu(dn: str) -> int:
    """Dönemin hafta içi gün sayısı (iki ucu dahil): "günde kaç büyük mum" bütün işlem günlerine bölünür,
    yalnız büyük mum görülen günlere değil."""
    bas, bit = D["kunye"]["donem"][dn]
    if dn == "dis":
        bit = min(bit, D["kunye"]["veri_bitis"])
    # Standart kütüphaneyle: yayın kapısı (sayfa sınavı 26) bu modülü numpy/pandas kurulu olmayan koşucuda içe aktarır.
    g, son = date.fromisoformat(bas[:10]), date.fromisoformat(bit[:10])
    n = 0
    while g <= son:
        n += g.weekday() < 5
        g += timedelta(days=1)
    return n


def bacak_kisa(b: dict) -> str:
    k = f"{b['rol']}.{b['tf']}.{b['giris']}"
    return k + (f".{b['suzgec']}={b['deger']}" if b["suzgec"] else "")


# ─────────────────────────────────────────────────────────────── anahtarlar
def anahtarlar() -> dict[str, str]:
    K: dict[str, str] = {}
    OR = ["sim_0.5", "sim_1.0", "sim_2.0", "geri_0.25", "geri_0.5", "geri_0.62", "geri_1.0", "geri_50_uc", "uc_asma",
          "uc_asma_05A"]
    for tf in TF:
        for dn in ("ic", "dis"):
            v = D["davranis"][tf][dn]
            p = f"D.{tf}.{dn}"
            K[f"{p}.n"] = tam(v["n"])
            K[f"{p}.gun_n"] = tam(v["gun_n"])
            for m in OR:
                K[f"{p}.{m}"] = yuzde(v[m], 1 if m.startswith("sim") else 0)
                K[f"{p}.ayna_{m}"] = yuzde(v[f"ayna_{m}"])
                # fark, okurun gördüğü yuvarlanmış iki paydan: "%85 · %82" yanında "+3 puan" okunmalı
                K[f"{p}.{m}_fark"] = sayi(round(v[m] * 100) - round(v[f"ayna_{m}"] * 100), 0, arti=True)
            K[f"{p}.sim_1.0_ters"] = yuzde(1 - v["sim_1.0"], 1)
            K[f"{p}.geri_fark1"] = puan1(v["geri_0.5_fark"]["ort"])
            for H in (1, 3, 6, 12, 24):
                K[f"{p}.net_{H}"] = a(v[f"net_{H}_ort"])
            for x in ("alt", "ust"):
                K[f"{p}.net_24_{x}"] = a(v["net_24"][x])
                K[f"{p}.geri_fark_{x}"] = puan1(v["geri_0.5_fark"][x])
                K[f"{p}.sim_{x}"] = yuzde(v["sim_1.0_ci"][x], 1)
            K[f"{p}.net24_pip"] = sayi(v["net24_pip_ort"], 2, arti=True)
            K[f"{p}.gunde"] = sayi(v["n"] / is_gunu(dn) / len(D["kunye"]["ciftler"]), 1)
            # yarısına dönenler içinde yeniden uca gidenlerin payı (koşullu)
            K[f"{p}.geri_50_uc_kosul"] = yuzde(v["geri_50_uc"] / v["geri_0.5"])
            K[f"{p}.ayna_geri_50_uc_kosul"] = yuzde(v["ayna_geri_50_uc"] / v["ayna_geri_0.5"])
            K[f"{p}.mfe"] = sayi(v["mfe_med"], 1)
            K[f"{p}.mae"] = sayi(v["mae_med"], 1)
            K[f"{p}.geri_dk"] = tam(round(v["geri_0.5_dk_med"]))
            K[f"{p}.A_pip"] = sayi(v["A_pip_med"], 1)
            K[f"{p}.R_pip"] = sayi(v["R_pip_med"], 1)
            K[f"{p}.makas_once"] = sayi(v["makas_once_pip_med"], 1)
            for k in ("mum", "1", "5", "15", "30"):
                K[f"{p}.makas_{k}_kat"] = sayi(v[f"makas_{k}_kat_ort"], 2)
                K[f"{p}.makas_{k}_iki"] = yuzde(v[f"makas_{k}_iki_kat"])
            o = D["olay"][tf][dn]
            for kv, n in o["kova"].items():
                K[f"{p}.kova_{kv}"] = tam(n)
                K[f"{p}.kova_{kv}_pay"] = yuzde(n / o["n"]) if o["n"] else "—"
        s = D["sayim_ic"][tf]
        for x, n in s.items():
            K[f"SAY.{tf}.{x}"] = tam(n)
        for x, n in D["sayim_tum"][tf].items():
            K[f"SAYT.{tf}.{x}"] = tam(n)
        for dn in ("ic", "dis"):
            t = D["tek"][tf][dn]
            K[f"TEK.{tf}.{dn}.pay"] = yuzde(t["pay"])
            K[f"TEK.{tf}.{dn}.makas_ici_kat"] = sayi(t["makas_ici_kat_med"], 1)
            for alt_k in ("tum", "asya"):
                x, q = t[alt_k], f"TEK.{tf}.{dn}.{alt_k}"
                if not x["n"]:
                    continue
                K[f"{q}.n"] = tam(x["n"])
                K[f"{q}.sim"] = yuzde(x["sim_1.0"], 1)
                K[f"{q}.sim_alt"], K[f"{q}.sim_ust"] = yuzde(x["sim_1.0_ci"]["alt"], 1), yuzde(x["sim_1.0_ci"]["ust"], 1)
                K[f"{q}.net"] = a(x["net_24"]["ort"])
                K[f"{q}.net_alt"], K[f"{q}.net_ust"] = a(x["net_24"]["alt"]), a(x["net_24"]["ust"])
                K[f"{q}.geri_fark"] = puan1(x["geri_0.5_fark"]["ort"])
                K[f"{q}.geri_fark_alt"] = puan1(x["geri_0.5_fark"]["alt"])
                K[f"{q}.geri_fark_ust"] = puan1(x["geri_0.5_fark"]["ust"])
        K[f"SAY.{tf}.kararsiz"] = tam(D["kararsiz_ic"][tf])
        for f, vals in D["suzgec"][tf].items():
            for v, dd in vals.items():
                for dn, x in dd.items():
                    p = f"S.{tf}.{f}.{v}.{dn}"
                    K[f"{p}.n"] = tam(x["n"])
                    if not x["n"]:
                        continue
                    K[f"{p}.sim"] = yuzde(x["sim_1.0"], 1)
                    K[f"{p}.net"] = a(x["net_24"]["ort"])
                    if x["net_24"]["alt"] is not None:
                        K[f"{p}.net_alt"], K[f"{p}.net_ust"] = a(x["net_24"]["alt"]), a(x["net_24"]["ust"])
                    K[f"{p}.geri_fark"] = puan(x["geri_0.5"] - x["ayna_geri_0.5"])
                    K[f"{p}.geri"] = yuzde(x["geri_0.5"])
        for dn in ("ic", "dis"):
            for x in D["izgara"][tf][dn]:
                p = f"G.{tf}.{dn}.{x['giris']}"
                K[f"{p}.n"] = tam(x["n"])
                if x.get("dolum") is not None:
                    K[f"{p}.dolum"] = yuzde(x["dolum"])
                if x["n"]:
                    K[f"{p}.kazanma"] = yuzde(x["kazanma"])
                    K[f"{p}.R"] = r(x["ort_R"])
                    if x.get("brut_R") is not None:
                        K[f"{p}.brut"] = r(x["brut_R"])
                        K[f"{p}.maliyet"] = sayi(x["maliyet_R"], 2)
                    K[f"{p}.risk"] = sayi(x["risk_pip_med"], 1)
    for dn in ("ic", "dis"):
        for x in D["ters_secim"][dn]:
            p = f"T.{dn}.{x['tf']}.{x['giris']}"
            K[f"{p}.dolan_n"], K[f"{p}.kacan_n"] = tam(x["dolan_n"]), tam(x["kacan_n"])
            for k in ("dolan", "kacan"):
                if x[f"piyasa_R_{k}"] is not None:
                    K[f"{p}.{k}_R"] = r(x[f"piyasa_R_{k}"])
                    K[f"{p}.{k}_kaz"] = yuzde(x[f"piyasa_kazanma_{k}"])
                    K[f"{p}.{k}_brut"] = r(x[f"piyasa_brut_{k}"])
    for b in D["bacak"]:
        p = f"B.{bacak_kisa(b)}"
        K[f"{p}.hukum"] = HUKUM_AD[b["hukum"]]
        for dn in ("ic", "dis"):
            o = b[dn]
            K[f"{p}.{dn}.n"] = tam(o["n"])
            if o["n"]:
                K[f"{p}.{dn}.kazanma"] = yuzde(o["kazanma"])
                K[f"{p}.{dn}.R"] = r(o["ort_R"])
                if o.get("brut_R") is not None:
                    K[f"{p}.{dn}.brut"] = r(o["brut_R"])
                K[f"{p}.{dn}.gun_n"] = tam(o["gun_n"])
            if o.get("alt") is not None:
                K[f"{p}.{dn}.alt"], K[f"{p}.{dn}.ust"] = r(o["alt"]), r(o["ust"])
        h = D["bacak_hafta"][b["bacak"]]
        if h["alt"] is not None:
            K[f"{p}.dis.hafta_alt"], K[f"{p}.dis.hafta_ust"] = r(h["alt"]), r(h["ust"])
    for x in (0.25, 0.5, 0.62, 0.95, 0.2):
        K[f"Y.{int(round(x * 100))}"] = yuzde(x)
    u = {x["giris"]: x for x in D["izgara"]["5"]["ic"]}
    K["G.5.taban_pay"] = yuzde(1 - u["devam:piyasa:s1:h1"]["uygun"] / u["devam:piyasa:s2:h1"]["uygun"])
    P = D["plan"]
    K["plan.aday"] = tam(P["aday_toplam"])
    K["plan.islem_sayi"] = tam(len(P["islem"]))
    K["plan.yok_sayi"] = tam(len(P["islem_yok"]))
    K["plan.ref_sayi"] = tam(len(P["referans"]))
    K["plan.bacak_sayi"] = tam(len(D["bacak"]))
    for x in P["islem"]:
        K[f"P.{x['tf']}.{x['yon']}.uygun"] = tam(x["uygun"])
        K[f"P.{x['tf']}.{x['yon']}.y1"] = r(x["ic"]["y1_R"])
        K[f"P.{x['tf']}.{x['yon']}.y2"] = r(x["ic"]["y2_R"])
    for x in P["islem_yok"]:
        K[f"P.{x['tf']}.{x['yon']}.en_iyi_R"] = r(x["en_iyi_R"])
    say = {h: sum(1 for b in D["bacak"] if b["hukum"] == h) for h in HUKUM_AD}
    for h, n in say.items():
        K[f"hukum_{h}"] = tam(n)
    toplam = len(D["bacak"])
    K["hukum_cumle"] = (f"{tam(toplam)} girişin hepsi çalışmıyor" if say["calismiyor"] == toplam
                        else f"{tam(toplam)} girişten çalışmayanların sayısı {tam(say['calismiyor'])}")
    ku = D["kunye"]
    K["pariteler"] = dy.pariteler(ku["ciftler"])
    K["parite_sayi"] = dy.SAYI_AD[len(ku["ciftler"])]
    K["veri_bitis"] = tarih(ku["veri_bitis"])
    for k, v in ku["sabit"].items():
        K[f"SB.{k}"] = sayi(v, 1) if isinstance(v, float) and v != int(v) else str(int(v)) if isinstance(v, (int, float)) else str(v)
    for k in ("kayma_pip", "haber_kayma_pip", "en_az_risk_pip"):
        K[f"ON.{k}"] = sayi(ON["maliyet"][k], 1)
    K["ON.secim_en_az"] = tam(ON["secim"]["en_az_islem"])
    K["ON.hukum_en_az"] = tam(ON["hukum"]["en_az_islem"])
    K["ON.bootstrap"] = tam(ON["hukum"]["bootstrap"])
    K["ON.dis_bitis"] = tarih(ON["donem"]["dis"][1])
    from datetime import datetime, timedelta, timezone
    tsi = timezone(timedelta(hours=3))
    for tf in TF:
        o = D["ornek"][tf]
        K[f"O.{tf}.gun"] = tarih(o["gun"])
        K[f"O.{tf}.kat"] = sayi(o["kat"], 1)
        nokta = ORNEK_PIP_NOKTA
        K[f"O.{tf}.R_pip"] = sayi((o["h"] - o["l"]) / nokta, 1)
        K[f"O.{tf}.A_pip"] = sayi(o["A"] / nokta, 1)
        K[f"O.{tf}.saat"] = datetime.fromtimestamp(o["bt"], tsi).strftime("%H:%M")
        K[f"O.{tf}.yon"] = "yukarı" if o["yon"] > 0 else "aşağı"
        m = o["mumlar"]
        i = next(k for k, x in enumerate(m) if x[0] == o["bt"])
        sonra = m[i + 1:i + 1 + 24]
        y, orta = o["yon"], (o["h"] + o["l"]) / 2
        lo, hi = min(x[3] for x in sonra), max(x[2] for x in sonra)
        K[f"O.{tf}.geri50"] = "döndü" if (lo <= orta if y > 0 else hi >= orta) else "dönmedi"
        K[f"O.{tf}.uc"] = "aştı" if (hi > o["h"] if y > 0 else lo < o["l"]) else "aşmadı"
        K[f"O.{tf}.net24"] = a(y * (sonra[-1][4] - o["c"]) / o["A"])
        kc = ((o["c"] - o["l"]) if y > 0 else (o["h"] - o["c"])) / (o["h"] - o["l"])
        K[f"O.{tf}.kapanis"] = "ucuna yakın" if kc >= 0.75 else ("ortasında" if kc >= 0.5 else "yarısının gerisinde")
    return K


# ─────────────────────────────────────────────────────────────── bloklar
def b_davranis() -> str:
    sat = []
    for tf in TF:
        for dn in ("ic", "dis"):
            v = D["davranis"][tf][dn]
            sat.append([f"{TF_AD[tf]} · {DONEM_AD[dn]}", tam(v["n"]), yuzde(v["sim_1.0"], 1),
                        f"{yuzde(v['geri_0.5'])} · {yuzde(v['ayna_geri_0.5'])}",
                        f"{yuzde(v['geri_1.0'])} · {yuzde(v['ayna_geri_1.0'])}",
                        a(v["net_6_ort"]), f"{a(v['net_24']['ort'])} ({a(v['net_24']['alt'])} … {a(v['net_24']['ust'])})"])
    return _tablo(["Dilim · dönem", "olay", "+1 ATR önce mumun yönünde", "yarısına döndü (gerçek · ayna)",
                   "öbür ucuna döndü (gerçek · ayna)", "6 mum sonra, ATR", "24 mum sonra, ATR (%95 aralık)"], sat)


def b_kova() -> str:
    sat = []
    for tf in TF:
        for kv in ("2-3", "3-4", "4-5", "5+"):
            i, o = D["suzgec"][tf]["kova"][kv]["ic"], D["suzgec"][tf]["kova"][kv]["dis"]
            sat.append([f"{TF_AD[tf]} · {DEGER_AD[kv]}", tam(i["n"]), yuzde(i["sim_1.0"], 1), a(i["net_24"]["ort"]),
                        tam(o["n"]), yuzde(o["sim_1.0"], 1), a(o["net_24"]["ort"])])
    return _tablo(["Dilim · büyüklük", "2018–23 olay", "+1 ATR önce mumun yönünde", "24 mum sonra, ATR",
                   "2024 → olay", "+1 ATR önce mumun yönünde", "24 mum sonra, ATR"], sat)


def b_makas() -> str:
    sat = []
    for tf in TF:
        for dn in ("ic", "dis"):
            v = D["davranis"][tf][dn]
            sat.append([f"{TF_AD[tf]} · {DONEM_AD[dn]}", sayi(v["makas_once_pip_med"], 1), sayi(v["makas_mum_kat_ort"], 2),
                        yuzde(v["makas_mum_iki_kat"]), sayi(v["makas_1_kat_ort"], 2), sayi(v["makas_5_kat_ort"], 2),
                        yuzde(v["makas_5_iki_kat"])])
    return _tablo(["Dilim · dönem", "önceki 60 dk makas, medyan pip", "mum kapanışında, kat", "iki katını aştı",
                   "1 dk sonra, kat", "5 dk sonra, kat", "5 dk sonra iki katını aştı"], sat)


def b_suzgec(tf: str, *suz: str) -> str:
    sat = []
    for f in suz or D["suzgec"][tf]:
        for v, dd in D["suzgec"][tf][f].items():
            i, o = dd["ic"], dd["dis"]
            if not i["n"]:
                continue
            hucre = lambda x: [tam(x["n"]), yuzde(x["sim_1.0"], 1), puan(x["geri_0.5"] - x["ayna_geri_0.5"]),
                               a(x["net_24"]["ort"])] if x["n"] else ["0", "—", "—", "—"]
            sat.append([f"{SUZ_AD[f]} · {deger_ad(f, v)}"] + hucre(i) + hucre(o))
    return _tablo(["Süzgeç · değer", "2018–23 olay", "+1 ATR önce mumun yönünde", "yarısına dönüş − ayna, puan",
                   "24 mum, ATR", "2024 → olay", "+1 ATR önce mumun yönünde", "yarısına dönüş − ayna, puan",
                   "24 mum, ATR"], sat)


def b_izgara(tf: str, stop: str = "s2", hedef: str = "h1") -> str:
    ic = {x["giris"]: x for x in D["izgara"][tf]["ic"]}
    dis = {x["giris"]: x for x in D["izgara"][tf]["dis"]}
    sat = []
    for g in sorted(ic, key=lambda g: (g.split(":")[0] != "devam", g)):
        y, e, s, h = g.split(":")
        if s != stop or h != hedef:
            continue
        i, o = ic[g], dis.get(g, {"n": 0})
        hucre = lambda x: [tam(x["n"]), yuzde(x["dolum"]) if x.get("dolum") is not None else "—",
                           yuzde(x["kazanma"]), r(x["brut_R"]) if x.get("brut_R") is not None else "—",
                           r(x["ort_R"])] if x["n"] else ["0", "—", "—", "—", "—"]
        sat.append([f"{YON_AD[y]} · {emir_ad(y, e)}"] + hucre(i) + hucre(o))
    return _tablo(["Yön · emir", "2018–23 işlem", "dolum", "kazanma", "maliyetsiz R", "net R",
                   "2024 → işlem", "dolum", "kazanma", "maliyetsiz R", "net R"], sat)


def b_ters_secim(stop: str = "s2", hedef: str = "h1") -> str:
    sat = []
    for x in D["ters_secim"]["ic"]:
        y, e, s, h = x["giris"].split(":")
        if s != stop or h != hedef:
            continue
        o = next(z for z in D["ters_secim"]["dis"] if z["tf"] == x["tf"] and z["giris"] == x["giris"])
        sat.append([f"{TF_AD[str(x['tf'])]} · {YON_AD[y]} · {emir_ad(y, e)}",
                    yuzde(x["dolan_n"] / (x["dolan_n"] + x["kacan_n"])),
                    yuzde(x["piyasa_kazanma_dolan"]), yuzde(x["piyasa_kazanma_kacan"]),
                    yuzde(o["dolan_n"] / (o["dolan_n"] + o["kacan_n"])),
                    yuzde(o["piyasa_kazanma_dolan"]), yuzde(o["piyasa_kazanma_kacan"])])
    return _tablo(["Dilim · emir", "2018–23 limit doldu", "doldu · piyasa girişi kazandı",
                   "dolmadı · piyasa girişi kazandı", "2024 → limit doldu", "doldu · piyasa girişi kazandı",
                   "dolmadı · piyasa girişi kazandı"], sat)


def b_bacaklar(rol: str) -> str:
    sat = []
    for b in D["bacak"]:
        if b["rol"] != rol:
            continue
        i, o = b["ic"], b["dis"]
        suz = f" · {SUZ_AD[b['suzgec']].lower()}: {deger_ad(b['suzgec'], b['deger'])}" if b["suzgec"] else ""
        aralik = f"{r(o['alt'])} … {r(o['ust'])}" if o.get("alt") is not None else "—"
        h = D["bacak_hafta"][b["bacak"]]
        hafta = f"{r(h['alt'])} … {r(h['ust'])}" if h["alt"] is not None else "—"
        sat.append([f"{TF_AD[str(b['tf'])]}{suz}", giris_ad(b["giris"]), tam(i["n"]), yuzde(i["kazanma"]), r(i["ort_R"]),
                    tam(o["n"]), yuzde(o["kazanma"]) if o["n"] else "—", r(o["ort_R"]) if o["n"] else "—",
                    r(o["brut_R"]) if o.get("brut_R") is not None else "—", aralik, hafta, HUKUM_AD[b["hukum"]]])
    return _tablo(["Dilim · süzgeç", "Giriş", "2018–23 n", "kazanma", "net R", "2024 → n", "kazanma", "net R",
                   "2024 → maliyetsiz R", "2024 → %95 aralık (gün)", "aralık (hafta)", "hüküm"], sat, sol=[0, 1, 11])


def b_yok() -> str:
    sat = []
    for x in D["plan"]["islem_yok"]:
        suz = f"{SUZ_AD[x['en_iyi_suzgec']].lower()}: {deger_ad(x['en_iyi_suzgec'], x['en_iyi_deger'])}" \
            if x["en_iyi_suzgec"] else "süzgeçsiz"
        y1 = r(x["en_iyi_y1"]) if x["en_iyi_y1"] is not None else "—"
        y2 = r(x["en_iyi_y2"]) if x["en_iyi_y2"] is not None else "—"
        sat.append([f"{TF_AD[str(x['tf'])]} · {YON_AD[x['yon']]}", tam(x["aday"]), giris_ad(x["en_iyi"]), suz,
                    tam(x["en_iyi_n"]), r(x["en_iyi_R"]), f"{y1} · {y2}"])
    return _tablo(["Dilim · yön", "aday", "en iyi aday", "süzgeç", "işlem", "net R", "iki yarı"], sat, sol=[0, 2, 3])


def b_sekil(slug: str, ad: str, *baslik: str) -> str:
    return dy.b_sekil(slug, ad, *baslik)


BLOK = {"davranis": b_davranis, "kova": b_kova, "makas": b_makas, "suzgec": b_suzgec, "izgara": b_izgara,
        "ters_secim": b_ters_secim, "bacaklar": b_bacaklar, "yok": b_yok}
YER = dy.YER


def uret(slug: str, K: dict) -> str:
    ham = (METIN / f"{slug}.md").read_text(encoding="utf-8")

    sayac = [0]

    def coz(m: re.Match) -> str:
        if m.group(1) == "#":
            parca = shlex.split(m.group(2))
            if parca[0] == "sekil":
                return b_sekil(slug, *parca[1:])
            if parca[0] == "atif":
                return masa.atif(ham, parca[1], parca[2])
            if parca[0] in masa.BLOKLAR:
                sayac[0] += parca[0] in masa.NUMARALI
                return masa.blok(slug, parca[0], parca[1], f"M{sayac[0]}")
            return BLOK[parca[0]](*parca[1:])
        if m.group(2) not in K:
            raise KeyError(f"{slug}: tanımsız anahtar {m.group(2)!r}")
        return K[m.group(2)]

    return YER.sub(coz, ham)


def hepsi() -> dict[str, str]:
    K = anahtarlar()
    return {s: uret(s, K) for s in SIRA}


def main() -> int:
    for s, metin in hepsi().items():
        if "--uret" in sys.argv:                 # yalnız üret (şablon sınaması), yazma
            continue
        (CIKTI / f"{s}.mdx").write_text(metin, encoding="utf-8")
        print(f"  ✓ site/src/content/arastirma/{s}.mdx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
