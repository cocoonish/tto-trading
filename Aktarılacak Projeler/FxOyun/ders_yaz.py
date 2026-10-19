#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oyun planı dersleri: metin/<slug>.md şablonları → site/src/content/arastirma/<slug>.mdx.

Şablonlarda ölçülmüş sayı ELLE yazılmaz: `{{ anahtar }}` ölçüm dosyasından (veri/ders.json) biçimlenmiş değeri,
`{{# blok arg … }}` ölçümden kurulan bir tabloyu ya da figür gömmesini koyar. Kapı (dogrula.py) dersleri yeniden
üretip yayımlanan dosyayla birebir kıyaslar ve şablonda ondalıklı ya da yüzdeli bir sayı kalmışsa düşer.

  python3 ders_yaz.py            # yaz
  python3 ders_yaz.py --uret     # yazmadan üret (kapı kullanır): {slug: metin}
"""
from __future__ import annotations

import json
import re
import shlex
import tomllib
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
METIN = BURASI / "metin"
CIKTI = KOK / "site" / "src" / "content" / "arastirma"
DERS = json.loads((BURASI / "veri" / "ders.json").read_text(encoding="utf-8"))
ON = tomllib.loads((BURASI / "onkayit_oyun.toml").read_text(encoding="utf-8"))

#: Serinin okuma sırası (sitedeki ders grubu aynı sırayı taşır; kapı ikisini kıyaslar).
SIRA = ["fx-oyun-okuma", "fx-oyun-acilislar", "fx-oyun-fiksingler", "fx-oyun-haberler", "fx-oyun-backtest"]
#: Her dersin figürleri (dosya adı öneki = şekil numarası).
SEKIL = {
    "fx-oyun-okuma": ["01_siniflar", "02_yarisi"],
    "fx-oyun-acilislar": ["01_patika", "02_devam_donus"],
    "fx-oyun-fiksingler": ["01_patika", "02_ay_sonu"],
    "fx-oyun-haberler": ["01_patika", "02_bacaklar"],
    "fx-oyun-backtest": ["01_kazanma_net", "02_maliyet", "03_egri"],
}
AILE = ["acilis", "fiksing", "veri", "mb"]
AILE_AD = {"acilis": "Seans açılışları", "fiksing": "Fiksingler", "veri": "ABD verileri", "mb": "Merkez bankası kararları"}
SINIF_AD = {"guclu": "güçlü", "reddedilen": "reddedilen", "normal": "normal", "kucuk": "küçük"}
UYUM_AD = {"trendle": "trend yönünde", "karsi": "trende karşı", "yatay": "trend yatay"}
HUKUM_AD = {"calisiyor": "çalışıyor", "zayif": "zayıf", "calismiyor": "çalışmıyor", "olculemedi": "ölçülemedi"}
TUR_AD = {"katil": "mumun yarısına limitle mumun yönünde", "devam": "mum kapanınca mumun yönünde",
          "kirilim": "küçük mumun kırılan ucundan", "fiks_ver": "fiksingde koşunun tersine"}


# ─────────────────────────────────────────────────────────────── biçim (ortak/bicim sözleşmesi)
def sayi(x: float, b: int = 2, arti: bool = False) -> str:
    s = f"{abs(x):,.{b}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    sifir = float(s.replace(".", "").replace(",", ".")) == 0
    if x < 0 and not sifir:
        return "−" + s
    return ("+" + s) if (arti and x > 0 and not sifir) else s


def yuzde(p: float, b: int = 0) -> str:
    return "%" + sayi(p * 100, b)


def tam(n: int) -> str:
    return sayi(n, 0)


def r(x: float) -> str:
    return sayi(x, 2, arti=True)


SAYI_AD = {2: "iki", 3: "üç", 4: "dört", 5: "beş", 6: "altı", 7: "yedi", 8: "sekiz", 9: "dokuz", 10: "on"}


def pariteler(ciftler: list[str]) -> str:
    ad = [f"{c[:3]}/{c[3:]}" for c in ciftler]
    return ", ".join(ad[:-1]) + " ve " + ad[-1]


# ─────────────────────────────────────────────────────────────── anahtarlar
def anahtarlar() -> dict[str, str]:
    K: dict[str, str] = {}
    M = ("orta", "devam", "donus", "orta_uc", "kapanis")
    for dn, ailes in DERS["aile_davranis"].items():
        for aile, ss in ailes.items():
            for s, v in ss.items():
                K[f"D.{dn}.{aile}.{s}.n"] = tam(v["n"])
                for m in M:
                    if v.get(m) is not None:
                        K[f"D.{dn}.{aile}.{s}.{m}"] = yuzde(v[m])
                if v.get("orta"):
                    K[f"D.{dn}.{aile}.{s}.uc_orta"] = yuzde(v["orta_uc"] / v["orta"])   # yarısına dönenlerden kendi ucuna
    for dn, ans in DERS["davranis"].items():
        for an, ss in ans.items():
            for s, v in ss.items():
                K[f"A.{dn}.{an}.{s}.n"] = tam(v["n_yonlu"])
                for m in M:
                    if m in v:
                        K[f"A.{dn}.{an}.{s}.{m}"] = yuzde(v[m])
    for aile, ss in DERS["trend"].items():
        for s, uu in ss.items():
            for u, v in uu.items():
                K[f"T.{aile}.{s}.{u}.n"] = tam(v["n"])
                for m in M:
                    if v.get(m) is not None:
                        K[f"T.{aile}.{s}.{u}.{m}"] = yuzde(v[m])
    for dn, ans in DERS["kucuk"].items():
        for an, v in ans.items():
            K[f"K.{dn}.{an}.n"] = tam(v["n"])
            if "kirilim_1R" in v:
                K[f"K.{dn}.{an}.ilerle"] = yuzde(v["kirilim_1R"])
    for an, dns in DERS["fiksing_ay_sonu"].items():
        for dn, gg in dns.items():
            for g, ss in gg.items():
                for s, v in ss.items():
                    K[f"F.{an}.{dn}.{g}.{s}.n"] = tam(v["n"])
                    for m in ("orta", "devam", "donus"):
                        K[f"F.{an}.{dn}.{g}.{s}.{m}"] = yuzde(v[m])
    for b in DERS["bacak"]:
        k = f"B.{b['rol']}.{b['aile']}.{b['sinif']}"
        K[f"{k}.hukum"] = HUKUM_AD[b["hukum"]]
        K[f"{k}.ad"] = bacak_ad(b)
        for dn in ("ic", "dis"):
            o = b[dn]
            K[f"{k}.{dn}.n"] = tam(o["n"])
            if o["n"]:
                K[f"{k}.{dn}.kazanma"] = yuzde(o["kazanma"])
                K[f"{k}.{dn}.R"] = r(o["ort_R"])
                K[f"{k}.{dn}.brut"] = r(o["brut_R"])
            if "alt" in o:
                K[f"{k}.{dn}.alt"], K[f"{k}.{dn}.ust"] = r(o["alt"]), r(o["ust"])
            if o["n"]:
                K[f"{k}.{dn}.maliyet"] = sayi(o["brut_R"] - o["ort_R"], 2)
            g = DERS["dagilim"].get(b["bacak"], {}).get(dn)
            if g:
                K[f"{k}.{dn}.risk_pip"] = sayi(g["risk_pip_med"], 0)
                if g["kazanc_ort"] is not None:
                    K[f"{k}.{dn}.kazanc"] = r(g["kazanc_ort"])
                if g["kayip_ort"] is not None:
                    K[f"{k}.{dn}.kayip"] = r(g["kayip_ort"])
                toplam = sum(g["neden"].values())
                for nd in ("stop", "hedef", "zaman"):
                    K[f"{k}.{dn}.{nd}_pay"] = yuzde(g["neden"].get(nd, 0) / toplam)
                if g["kazanc_ort"] is not None and g["kayip_ort"] is not None:
                    K[f"{k}.{dn}.basabas"] = yuzde(-g["kayip_ort"] / (g["kazanc_ort"] - g["kayip_ort"]))
    for a in DERS["an"]:
        for f in ("ad", "bolge", "yerel", "tsi_yaz", "tsi_kis"):
            K[f"AN.{a['an']}.{f}"] = a[f]
        K[f"AN.{a['an']}.tf"], K[f"AN.{a['an']}.pencere"] = str(a["tf"]), str(a["pencere"])
    for k, v in DERS["sabit"].items():
        K[f"S.{k}"] = sayi(v, 2) if isinstance(v, float) else str(v)
        if isinstance(v, float) and v < 1:
            K[f"S.{k}.yuzde"] = yuzde(v)
    ku = DERS["kunye"]
    K["olay_ic"] = tam(ku["olay_ic"])
    K["veri_bitis"] = ".".join(reversed(ku["veri_bitis"].split("-")))
    for s, o in DERS["ornek"].items():
        K[f"O.{s}.gun"] = ".".join(reversed(o["gun"].split("-")))
        K[f"O.{s}.tsi"] = o["tsi"]
    for k in ("kayma_pip", "haber_kayma_pip", "en_az_risk_pip"):
        K[f"ON.{k}"] = sayi(ON["maliyet"][k], 1)
    K["ON.secim_en_az"] = tam(ON["secim"]["en_az_islem"])
    K["ON.hukum_en_az"] = tam(ON["hukum"]["en_az_islem"])
    K["ON.bootstrap"] = tam(ON["hukum"]["bootstrap"])
    K["ON.dis_bitis"] = ".".join(reversed(ON["donem"]["dis"][1].split("-")))
    K["pariteler"] = pariteler(ku["ciftler"])
    K["parite_sayi"] = SAYI_AD[len(ku["ciftler"])]
    K["an_sayi"] = SAYI_AD[len(DERS["an"])]
    # türetilmiş sayımlar
    ref = [b for b in DERS["bacak"] if b["rol"] == "referans"]
    isl = [b for b in DERS["bacak"] if b["rol"] == "islem"]
    K["ref_sayi"], K["islem_sayi"] = str(len(ref)), str(len(isl))
    K["izle_sayi"] = str(len(DERS["plan"]["izle"]))
    adaylar = [x["aday"] for x in DERS["plan"]["islem"] + DERS["plan"]["izle"]]
    K["aday_alt"], K["aday_ust"] = SAYI_AD[min(adaylar)], SAYI_AD[max(adaylar)]
    sik = [b for b in ref if b["aile"] in ("acilis", "fiksing")]
    K["sik_kaz_alt"] = yuzde(min(b["dis"]["kazanma"] for b in sik))
    K["sik_kaz_ust"] = yuzde(max(b["dis"]["kazanma"] for b in sik))
    K["sik_R_alt"] = r(min(b["dis"]["ort_R"] for b in sik))
    K["sik_R_ust"] = r(max(b["dis"]["ort_R"] for b in sik))
    K["sik_brut_alt"] = r(min(b["dis"]["brut_R"] for b in sik))
    K["sik_brut_ust"] = r(max(b["dis"]["brut_R"] for b in sik))
    K["sik_n_dis"] = tam(sum(b["dis"]["n"] for b in sik))
    K["sik_calismiyor"] = str(sum(1 for b in sik if b["hukum"] == "calismiyor"))
    K["sik_sayi"] = str(len(sik))
    K["mb_n_ust"] = tam(max(b["dis"]["n"] for b in DERS["bacak"] if b["aile"] == "mb"))
    say = {h: sum(1 for b in isl if b["hukum"] == h) for h in HUKUM_AD}
    for h, n in say.items():
        K[f"islem_{h}"] = str(n)
    return K


def bacak_ad(b: dict) -> str:
    """Bacağın okunuşu. R = planlanan risk (giriş ile stop arası); stop payı ilk mumun boyu cinsinden."""
    h = b["hedef"]
    hedef = {"uc": "hedef mumun kendi ucu", "orta": "hedef koşunun yarısı"}.get(h) if isinstance(h, str) else \
        f"hedef {sayi(float(h), 1)} R"
    if b["tur"] == "fiks_ver":
        stop = f"stop koşunun ucunun {sayi(b['tampon'], 1)} koşu boyu ötesinde"
    else:
        stop = f"stop öbür ucun {sayi(b['tampon'], 1)} mum boyu ötesinde"
    return f"{TUR_AD[b['tur']]} · {stop} · {hedef}"


# ─────────────────────────────────────────────────────────────── bloklar
def _tablo(bas: list[str], satirlar: list[list[str]]) -> str:
    out = ["| " + " | ".join(bas) + " |", "|" + "|".join(["---"] + ["---:"] * (len(bas) - 1)) + "|"]
    out += ["| " + " | ".join(s) + " |" for s in satirlar]
    return "\n".join(out)


def b_an_tablo(*aileler: str) -> str:
    sat = []
    for a in DERS["an"]:
        if aileler and a["aile"] not in aileler:
            continue
        tsi = a["tsi_yaz"] if a["tsi_yaz"] == a["tsi_kis"] else f"{a['tsi_yaz']} (kışın {a['tsi_kis']})"
        ilk = f"{a['tf']} dk" + (" (fiksinge kadar)" if a["aile"] == "fiksing" else "")
        sat.append([a["ad"], f"{a['bolge']} {a['yerel']}", tsi, ilk, f"{a['pencere']} dk"])
    return _tablo(["An", "Yerel saat", "TSİ", "İlk mum", "İzlenen süre"], sat)


def b_davranis(aile: str) -> str:
    """Bir ailenin anları, üç yönlü sınıf, iki dönem."""
    sat = []
    for a in DERS["an"]:
        if a["aile"] != aile:
            continue
        for s in ("guclu", "normal", "reddedilen"):
            i, o = DERS["davranis"]["ic"][a["an"]].get(s), DERS["davranis"]["dis"][a["an"]].get(s)
            if not i or not o:
                continue
            sat.append([f"{a['ad']} · {SINIF_AD[s]}", tam(i["n_yonlu"]), yuzde(i["orta"]), yuzde(i["devam"]),
                        yuzde(i["donus"]), tam(o["n_yonlu"]), yuzde(o["orta"]), yuzde(o["devam"]), yuzde(o["donus"])])
    orta = "yarısını geri verdi" if aile == "fiksing" else "yarısına döndü"
    ilk = "Fiksing · koşu" if aile == "fiksing" else "An · ilk mum"
    return _tablo([ilk, "2018–23 n", orta, "devam etti", "tersine döndü",
                   "2024 → n", orta, "devam etti", "tersine döndü"], sat)


def b_trend(aile: str) -> str:
    sat = []
    for s in ("guclu", "normal", "reddedilen"):
        for u in ("trendle", "karsi", "yatay"):
            v = DERS["trend"][aile][s][u]
            sat.append([f"{SINIF_AD[s]} · {UYUM_AD[u]}", tam(v["n"]), yuzde(v["devam"]), yuzde(v["donus"]),
                        yuzde(v["orta"])])
    return _tablo(["İlk mum · trend", "n", "devam etti", "tersine döndü", "yarısına döndü"], sat)


def b_kucuk(*aileler: str) -> str:
    sat = []
    for a in DERS["an"]:
        if a["aile"] not in aileler:
            continue
        i, o = DERS["kucuk"]["ic"].get(a["an"]), DERS["kucuk"]["dis"].get(a["an"])
        if i and o:
            sat.append([a["ad"], tam(i["n"]), yuzde(i["kirilim_1R"]), tam(o["n"]), yuzde(o["kirilim_1R"])])
    return _tablo(["An", "2018–23 n", "kırılan tarafta 1 mum boyu gitti", "2024 → n", "kırılan tarafta 1 mum boyu gitti"], sat)


def b_ay_sonu() -> str:
    sat = []
    for an in ("wmr", "tokyo_fiks"):
        ad = next(a["ad"] for a in DERS["an"] if a["an"] == an)
        for g, gad in (("ay_sonu", "ay sonu"), ("diger", "öbür günler")):
            for s in ("guclu", "normal"):
                i = DERS["fiksing_ay_sonu"][an]["ic"][g][s]
                o = DERS["fiksing_ay_sonu"][an]["dis"][g][s]
                sat.append([f"{ad} · {gad} · {SINIF_AD[s]}", tam(i["n"]), yuzde(i["orta"]), yuzde(i["devam"]),
                            tam(o["n"]), yuzde(o["orta"]), yuzde(o["devam"])])
    return _tablo(["Fiksing · gün · koşu", "2018–23 n", "yarısını geri verdi", "devam etti", "2024 → n",
                   "yarısını geri verdi", "devam etti"], sat)


def b_bacaklar(rol: str, *aileler: str) -> str:
    sat = []
    for b in DERS["bacak"]:
        if b["rol"] != rol or (aileler and b["aile"] not in aileler):
            continue
        i, o = b["ic"], b["dis"]
        aralik = f"{r(o['alt'])} … {r(o['ust'])}" if "alt" in o else "—"
        sat.append([f"{AILE_AD[b['aile']]} · {SINIF_AD[b['sinif']]}", bacak_ad(b),
                    tam(i["n"]), yuzde(i["kazanma"]), r(i["ort_R"]),
                    tam(o["n"]), yuzde(o["kazanma"]) if o["n"] else "—", r(o["ort_R"]) if o["n"] else "—", aralik,
                    HUKUM_AD[b["hukum"]]])
    return _tablo(["An ailesi · ilk mum", "Plan", "2018–23 n", "kazanma", "net R", "2024 → n", "kazanma", "net R",
                   "%95 aralık", "hüküm"], sat)


def b_izle() -> str:
    sat = []
    for x in DERS["plan"]["izle"]:
        sat.append([f"{AILE_AD[x['aile']]} · {SINIF_AD[x['sinif']]}", str(x["aday"]), r(x["en_iyi_R"])])
    return _tablo(["An ailesi · ilk mum", "denenen tepki", "en iyisinin 2018–23 net R'si"], sat)


def b_sekil(slug: str, ad: str, *baslik: str) -> str:
    no = ad[:2]
    return f'<GrafikEmbed src="/arastirma/{slug}/{ad}.html" baslik="{" ".join(baslik)}" no="{no}" kaynak="Dukascopy" />'


BLOK = {"an_tablo": b_an_tablo, "davranis": b_davranis, "trend": b_trend, "kucuk": b_kucuk, "ay_sonu": b_ay_sonu,
        "bacaklar": b_bacaklar, "izle": b_izle}

YER = re.compile(r"\{\{\s*(#?)\s*(.*?)\s*\}\}", re.S)


def uret(slug: str, K: dict) -> str:
    ham = (METIN / f"{slug}.md").read_text(encoding="utf-8")

    def coz(m: re.Match) -> str:
        if m.group(1) == "#":
            parca = shlex.split(m.group(2))
            if parca[0] == "sekil":
                return b_sekil(slug, *parca[1:])
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
        if "--uret" in sys.argv:
            continue
        (CIKTI / f"{s}.mdx").write_text(metin, encoding="utf-8")
        print(f"  ✓ site/src/content/arastirma/{s}.mdx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
