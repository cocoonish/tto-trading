#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kısa serinin ölçüleri (ders_olcum → olcum["kisa"]): stop ve hedef seçimi kazanma oranını ve net sonucu nasıl değiştirir.

Girdi koşunun ızgara sonuçlarıdır (cikti/sonuc/<birim>/<parite>.json → izgara): her kural × parite için ön kayıtta
yazılmış bütün parametre bileşimleri, iki pencerede (2018–2023 · 2024 →) işlem sayısı, kazanma oranı (isabet) ve
işlem başına net R. Kopya satırlar (aynı işlemleri üreten iki bileşim) ve boş bileşimler sayılmaz; bir pencerede
ASGARI işlemden azı olan bileşim o pencerenin ölçüsüne girmez.

Ölçüler betimlemedir: iki pencere de görüldükten sonra kuruldu ve hiçbir kuralın hükmünü değiştirmez (hükümler ön
kayıtlı varsayılanlarındır). Üç soru sorar:
  1. Hedef türüne göre kazanma oranı ve net sonuç (yakın hedef 1R, uzak hedef 2R, hedefsiz çıkış, kurala özgü hedef).
  2. EŞLİ kıyas: aynı kural, aynı parite, öbür bütün parametreler aynıyken YALNIZ hedef (1R ↔ 2R), yalnız stop türü
     (sert ↔ kapanış) ya da yalnız stop yeri (karşı uç ↔ orta) değişince kazanma oranı ve net R ne kadar değişir.
     Gruplar arası kıyas kural karışımına bağlıdır (gün sonu hedefi yalnız kırılım kurallarında var); eşli kıyas değil.
  3. Yüksek kazanma oranı ve "en iyi ayarı seçmek": örneklem dışında kazanma oranı yüksek ayarların net sonucu, ve
     örneklem içinde en iyi çıkan ayarların örneklem dışındaki net sonucu.
  4. Kural kartı (kart): her kuralın stop × hedef tablosu, öbür parametreler varsayılanda, dört parite birlikte.

`suzgec()` ayrı bir çalışmanın dersi okuyan görünüşüdür: ön kayıtlı altı süzgeç (onkayit_suzgec.toml; suzgec.py
ölçer, cikti/suzgec/olcum.json). Onun hükmü (seçim ve hüküm kuralı) ön kayıtlıdır; buradaki türetmeler (iyileştiren
kural sayısı, brüt fark, stop genişliği oranı, parite hücreleri) betimlemedir.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

#: Bir pencerenin ölçüsüne girmek için asgari işlem sayısı (bileşim başına).
ASGARI = 30
#: Hedef türlerinin grupları (okur adı ders motorunda).
HEDEF_GRUP = {"1R": "yakin", "2R": "uzak", "gun_sonu": "hedefsiz", "zaman": "hedefsiz", "yok": "hedefsiz"}
GRUP_SIRA = ("yakin", "uzak", "hedefsiz", "ozel")
#: Eşli kıyasların parametresi ve iki değeri (birinci → ikinci).
ESLI = (("hedef", "1R", "2R"), ("stop_turu", "sert", "kapanis"), ("stop_yeri", "karsi_uc", "orta"))
#: "En iyi ayarı seçmek" kıyasında örneklem içinden alınan ayar sayısı.
SECIM_N = 20
#: Yüksek kazanma oranı eşikleri (örneklem dışı).
ISABET_ESIK = (0.5, 0.6)


def _medyan(x: list[float]) -> float | None:
    s = sorted(v for v in x if v is not None and not math.isnan(v))
    if not s:
        return None
    m = len(s) // 2
    return s[m] if len(s) % 2 else 0.5 * (s[m - 1] + s[m])


def _ort(x: list[float]) -> float | None:
    s = [v for v in x if v is not None]
    return sum(s) / len(s) if s else None


def satirlar(kok: Path, birimler: dict) -> list[dict]:
    """Izgaranın sayılan satırları: kopya ve boş olmayan, iki pencerede de en az ASGARI işlemli bileşimler."""
    out = []
    for b, v in birimler.items():
        for c in v["cift"]:
            s = json.loads((kok / "sonuc" / b / f"{c}.json").read_text(encoding="utf-8"))
            for iz in s.get("izgara") or []:
                if iz.get("kopya") is not None or iz.get("bos"):
                    continue
                i, o = iz.get("is") or {}, iz.get("oos") or {}
                if (i.get("n") or 0) < ASGARI or (o.get("n") or 0) < ASGARI:
                    continue
                if None in (i.get("isabet"), o.get("isabet"), i.get("beklenti_r"), o.get("beklenti_r")):
                    continue
                out.append({"kural": b, "cift": c, "p": {k: str(x) for k, x in iz["p"].items()},
                            "is_isabet": i["isabet"], "is_r": i["beklenti_r"],
                            "oos_isabet": o["isabet"], "oos_r": o["beklenti_r"]})
    return out


def _grup(s: dict) -> str:
    return HEDEF_GRUP.get(s["p"].get("hedef", "yok"), "ozel")


def _ozet(sat: list[dict]) -> dict:
    return {"n": len(sat),
            "isabet": _medyan([s["oos_isabet"] for s in sat]),
            "r": _medyan([s["oos_r"] for s in sat]),
            "ikisi_arti": sum(1 for s in sat if s["is_r"] > 0 and s["oos_r"] > 0)}


def esli(sat: list[dict], param: str, a: str, b: str) -> dict:
    """Aynı kural, parite ve öbür parametrelerle yalnız `param` a → b değişen çiftler."""
    def anahtar(s):
        return (s["kural"], s["cift"], tuple(sorted((k, v) for k, v in s["p"].items() if k != param)))
    sol = {anahtar(s): s for s in sat if s["p"].get(param) == a}
    sag = {anahtar(s): s for s in sat if s["p"].get(param) == b}
    ortak = [k for k in sol if k in sag]
    if not ortak:
        return {"n": 0}
    di = [sag[k]["oos_isabet"] - sol[k]["oos_isabet"] for k in ortak]
    dr = [sag[k]["oos_r"] - sol[k]["oos_r"] for k in ortak]
    return {"n": len(ortak), "kural": len({k[0] for k in ortak}),
            "a_isabet": _medyan([sol[k]["oos_isabet"] for k in ortak]),
            "b_isabet": _medyan([sag[k]["oos_isabet"] for k in ortak]),
            "a_r": _medyan([sol[k]["oos_r"] for k in ortak]),
            "b_r": _medyan([sag[k]["oos_r"] for k in ortak]),
            "d_isabet": _medyan(di), "d_r": _medyan(dr),
            "b_iyi_pay": sum(1 for x in dr if x > 0) / len(dr),
            "a_arti": sum(1 for k in ortak if sol[k]["oos_r"] > 0),
            "b_arti": sum(1 for k in ortak if sag[k]["oos_r"] > 0)}


#: Kural kartının stop ve hedef boyutları (kuralın ızgarasında birden çok değeri olanlar tabloya girer).
KART_STOP = ("stop_yeri", "stop_kurali", "stop_turu")
KART_BOYUT = KART_STOP + ("hedef",)


def kart(kok: Path, b: str, v: dict) -> dict:
    """Bir kuralın stop × hedef tablosu: stop ve hedef dışındaki bütün parametreler önceden kayıtlı varsayılanda, dört
    paritenin işlemleri birlikte (işlem ağırlıklı ortalama). Boş bileşim sayılmaz; kopya bileşim (aynı işlemleri
    üreten ikinci yazım) sayılır, çünkü stop/hedef hücresi yine o ayardır. Bir hücre iki pencerede de en az ASGARI
    işlem taşımıyorsa tabloda durur ama seçime girmez.

    `is_en_iyi`: 2018–2023'te en iyi hücre (o günden bakan birinin seçebileceği); `oos_en_iyi`: 2024 →'de en iyi hücre
    (sonradan bakınca; seçilemezdi). İkisi de betimlemedir; hükümler varsayılanındır."""
    vs = {k: str(x) for k, x in v.items()}
    hucre: dict = {}
    for c in sorted(p.stem for p in (kok / "sonuc" / b).glob("*.json")):
        s = json.loads((kok / "sonuc" / b / f"{c}.json").read_text(encoding="utf-8"))
        for iz in s.get("izgara") or []:
            if iz.get("bos"):
                continue
            p = {k: str(x) for k, x in iz["p"].items()}
            if any(p.get(k) != vs[k] for k in p if k not in KART_BOYUT and k in vs):
                continue
            anahtar = tuple((k, p[k]) for k in KART_BOYUT if k in p)
            h = hucre.setdefault(anahtar, {"is": [0, 0.0, 0.0], "oos": [0, 0.0, 0.0], "cift": set(), "parite": {}})
            h["cift"].add(c)
            xo = iz.get("oos") or {}
            if xo.get("n") and xo.get("beklenti_r") is not None:
                h["parite"][c] = {"n": xo["n"], "r": xo["beklenti_r"]}
            for w in ("is", "oos"):
                x = iz.get(w) or {}
                n = x.get("n") or 0
                if n and x.get("beklenti_r") is not None and x.get("isabet") is not None:
                    h[w][0] += n
                    h[w][1] += n * x["beklenti_r"]
                    h[w][2] += n * x["isabet"]
    if not hucre:
        raise ValueError(f"kisa.kart: {b} için varsayılana uyan ızgara satırı yok")
    satir = []
    for anahtar, h in hucre.items():
        d = {"p": dict(anahtar), "cift": len(h["cift"]), "parite": dict(sorted(h["parite"].items())),
             "varsayilan": all(vs.get(k) == x for k, x in anahtar)}
        for w in ("is", "oos"):
            n, r, i = h[w]
            d[w] = {"n": n, "r": r / n if n else None, "isabet": i / n if n else None}
        d["sayilir"] = d["is"]["n"] >= ASGARI and d["oos"]["n"] >= ASGARI
        satir.append(d)
    boyut = [k for k in KART_BOYUT if len({d["p"].get(k) for d in satir}) > 1]
    say = [i for i, d in enumerate(satir) if d["sayilir"]]
    if not any(d["varsayilan"] for d in satir):
        raise ValueError(f"kisa.kart: {b} varsayılan hücresi yok")
    out = {"boyut": boyut, "hucre": satir, "sayilan": len(say),
           "oos_arti": sum(1 for i in say if satir[i]["oos"]["r"] > 0),
           "iki_arti": sum(1 for i in say if satir[i]["oos"]["r"] > 0 and satir[i]["is"]["r"] > 0)}
    if say:
        out["is_en_iyi"] = max(say, key=lambda i: (satir[i]["is"]["r"], -i))
        out["oos_en_iyi"] = max(say, key=lambda i: (satir[i]["oos"]["r"], -i))
    return out


def bolum(kok: Path, birimler: dict) -> dict:
    sat = satirlar(kok, birimler)
    if not sat:
        raise ValueError("kisa: ızgarada sayılan satır yok")
    gruplar = {g: _ozet([s for s in sat if _grup(s) == g]) for g in GRUP_SIRA}
    yuksek = {}
    for e in ISABET_ESIK:
        x = [s for s in sat if s["oos_isabet"] >= e]
        yuksek[f"{e:.1f}"] = {"n": len(x), "r": _medyan([s["oos_r"] for s in x]),
                              "arti": sum(1 for s in x if s["oos_r"] > 0)}
    en_iyi = sorted(sat, key=lambda s: (-s["is_r"], s["kural"], s["cift"], sorted(s["p"].items())))[:SECIM_N]
    return {
        "asgari": ASGARI,
        "grup_sira": list(GRUP_SIRA),
        "toplam": {**_ozet(sat), "kural": len({s["kural"] for s in sat}),
                   "oos_arti": sum(1 for s in sat if s["oos_r"] > 0)},
        "grup": gruplar,
        "esli": {param: esli(sat, param, a, b) for param, a, b in ESLI},
        "yuksek_isabet": yuksek,
        "kart": {b: kart(kok, b, v["varsayilan"]) for b, v in birimler.items()},
        "secim": {"n": len(en_iyi), "is_r": _ort([s["is_r"] for s in en_iyi]),
                  "oos_r": _ort([s["oos_r"] for s in en_iyi]),
                  "oos_arti": sum(1 for s in en_iyi if s["oos_r"] > 0)},
        # Figürün noktaları (örneklem dışı kazanma oranı, net R, hedef grubu); dört haneye yuvarlı.
        "nokta": [[round(s["oos_isabet"], 4), round(s["oos_r"], 4), GRUP_SIRA.index(_grup(s))] for s in sat],
    }


#: Süzgeçlerin sırası (ön kayıttaki liste) ve süzgeçsiz aday.
SUZGEC_SIRA = ("ema20", "trend60", "oynak", "dar", "ema20_oynak", "ema20_dar")


def _al(m: dict) -> dict:
    return {k: m.get(k) for k in ("n", "isabet", "beklenti_r", "brut_r", "ga_alt", "risk_pip")}


def suzgec(kok: Path, birimler: dict) -> dict:
    """Süzgeç çalışmasının ders görünüşü. Ölçüm dosyasının künyesi bugünkü ağaçla (kod ve koşu çıktısı) aynı değilse
    düşer: koşu ya da süzgeç kodu değişip ölçüm yeniden koşulmadıysa ders eski işlemlerin sonucunu basmaz."""
    import suzgec as sz
    yol = kok / "suzgec" / "olcum.json"
    if not yol.exists():
        raise SystemExit(f"süzgeç ölçümü yok ({yol}); önce suzgec.py")
    d = json.loads(yol.read_text(encoding="utf-8"))
    if d.get("kunye") is None or d["kunye"] != sz.kunye(kok):
        raise SystemExit("süzgeç ölçümü bugünkü kodla ya da koşu çıktısıyla ölçülmemiş; suzgec.py yeniden koşulmalı")
    if set(d["kural"]) != set(birimler):
        raise SystemExit("süzgeç ölçümünün kuralları koşunun kurallarıyla aynı değil")
    if list(d["ozet"]) != list(SUZGEC_SIRA):
        raise SystemExit(f"süzgeç listesi ön kayıttakiyle aynı değil: {list(d['ozet'])}")
    kural = {}
    for b, v in d["kural"].items():
        a = v["aday"]
        sec = v.get("secilen")
        fil = [s_ for s_ in SUZGEC_SIRA if s_ in a]
        en = max(fil, key=lambda s_: (a[s_]["oos"]["beklenti_r"], -fil.index(s_)))
        kural[b] = {"yok": {"is": _al(a["yok"]["is"]), "oos": _al(a["yok"]["oos"])},
                    "aday": {s_: {"is": _al(a[s_]["is"]), "oos": _al(a[s_]["oos"]), "hukum": a[s_]["hukum"],
                                  "rastgele": a[s_].get("rastgele_oos")} for s_ in fil},
                    "secilen": sec,
                    "secilen_hukum": a[sec]["hukum"] if sec else None,
                    "oos_en_iyi": en}
    ozet = {}
    for s_ in SUZGEC_SIRA:
        o = dict(d["ozet"][s_])
        bf = [kural[b]["aday"][s_]["oos"]["brut_r"] - kural[b]["yok"]["oos"]["brut_r"] for b in kural
              if s_ in kural[b]["aday"]]
        ro = [kural[b]["aday"][s_]["oos"]["risk_pip"] / kural[b]["yok"]["oos"]["risk_pip"] for b in kural
              if s_ in kural[b]["aday"] and kural[b]["yok"]["oos"]["risk_pip"]]
        tut = [kural[b]["aday"][s_]["oos"]["n"] / kural[b]["yok"]["oos"]["n"] for b in kural if s_ in kural[b]["aday"]]
        o.update({"brut_fark_oos_medyan": _medyan(bf), "risk_orani_oos_medyan": _medyan(ro),
                  "tutulan_pay_medyan": _medyan(tut)})
        ozet[s_] = o
    # Parite hücreleri (bilgi): kural × parite × süzgeç; iki pencerede de en az ASGARI işlem ve iki pencerede de artı.
    hucre_n = hucre_arti = 0
    for b, v in d["kural"].items():
        for c, p in v["parite"].items():
            for s_ in SUZGEC_SIRA:
                x = p.get(s_)
                if not x:
                    continue
                hucre_n += 1
                i, o_ = x["is"], x["oos"]
                if ((i.get("n") or 0) >= ASGARI and (o_.get("n") or 0) >= ASGARI
                        and (i.get("beklenti_r") or 0) > 0 and (o_.get("beklenti_r") or 0) > 0):
                    hucre_arti += 1
    secili = [b for b in kural if kural[b]["secilen"]]
    hk = d["secim_ozet"]["hukum"]
    return {
        "esik": {"oynak": float(sz.OYNAK), "ema_gun": int(sz.EMA_GUN), "asgari": ASGARI,
                 "asgari_secim": int(sz.OK["secim"]["asgari_islem"]),
                 "asgari_secim_haber": int(sz.OK["secim"]["asgari_islem_haber"]),
                 "bh_q": float(sz.OK["coklu"]["bh_q"])},
        "kural": kural,
        "ozet": ozet,
        "coklu": {**d["coklu"], "bh_n": len(d["coklu"]["bh_gecen"])},
        "suzgec_n": len(SUZGEC_SIRA), "kural_n": len(kural),
        "hukum": hk,
        "secilen_sayim": d["secim_ozet"]["secilen"],
        "secilen_suzgecli": sum(1 for b in secili if kural[b]["secilen"] != "yok"),
        "zayif": [b for b in secili if kural[b]["secilen_hukum"] == "zayif"],
        "ort": {"yok_oos": _ort([kural[b]["yok"]["oos"]["beklenti_r"] for b in kural]),
                "secilen_oos": _ort([kural[b]["aday"][kural[b]["secilen"]]["oos"]["beklenti_r"]
                                     if kural[b]["secilen"] != "yok" else kural[b]["yok"]["oos"]["beklenti_r"]
                                     for b in secili])},
        "herhangi_oos_arti": sum(1 for b in kural if any(x["oos"]["beklenti_r"] > 0 for x in kural[b]["aday"].values())),
        "herhangi_iki_arti": sum(1 for b in kural if any(x["oos"]["beklenti_r"] > 0 and x["is"]["beklenti_r"] > 0
                                                         for x in kural[b]["aday"].values())),
        "hucre": {"n": hucre_n, "iki_arti": hucre_arti},
    }
