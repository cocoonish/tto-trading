#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ders ölçümü: koşu çıktılarından dersin ve figürlerin TEK ölçüm dosyası.

Girdi (hepsi depodaki koşu çıktısı ya da arşiv):
  cikti/sonuc/<birim>/<parite>.json     birim × parite koşusu (kosu.py)
  cikti/islem/<birim>/<parite>__*.parquet  varsayılan ve seçilen kombinasyonun işlemleri
  cikti/sonuc/haber/<parite>.json, devam.json   haber analizleri (haber_analiz.py)
  veri/dukascopy/kalite.json, kunye/    veri denetimi ve indirme künyesi
  veri/takvim/olaylar.csv, kunye.json, sinama.json   haber takvimi
  onkayit.toml, ayar.toml               önceden kayıt ve proje ayarı
Çıktı:
  cikti/ders/olcum.json                 figürler (sekil.py), ders metinleri (ders_yaz.py) ve doğrulayıcı
                                        (dogrula.py) yalnız buradan okur

Burada yeni bir ÖLÇÜM yapılmaz, yalnız toplanır; iki istisna adıyla: (1) dört paritenin
HAVUZU — aynı stratejiyi dört paritede birlikte koşmanın işlem başına ortalaması ve günlük
R toplamından Sharpe'ı, kaydedilmiş işlem dosyalarından; (2) stratejiler arası günlük R
korelasyonu. İkisinin tanımı aşağıda, fonksiyonun kendisinde.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import tomllib
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import ayar as ay
import metrik as mk
import saglamlik as sg
import zaman as z

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
ONKAYIT_YOL = BURASI / "onkayit.toml"


def _oku(yol: Path):
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else None


def _oz(yol: Path) -> str | None:
    return hashlib.sha256(yol.read_bytes()).hexdigest() if yol.exists() else None


def _icerik_ozu(d: dict) -> str:
    """Ön kaydın AYRIŞTIRILMIŞ içeriğinin özü: yorum ve biçim değişikliği özü değiştirmez."""
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def onkayit_gecmisi() -> list[dict] | None:
    """Ön kaydın git geçmişi: her commit'te ayrıştırılmış içeriğin özü ve bir öncekine göre değişen
    bölümler. "Hiçbir kural sonuç görüldükten sonra değişmedi" cümlesi bir beyan değil bu listedir.
    Git yoksa (ya da sığ klonda geçmiş eksikse) None: ölçülemeyen geçmiş uydurulmaz."""
    import subprocess
    rel = ONKAYIT_YOL.relative_to(KOK).as_posix()
    try:
        out = subprocess.run(["git", "-C", str(KOK), "log", "--format=%H %cI", "--", rel],
                             capture_output=True, text=True, check=True).stdout.split("\n")
    except (OSError, subprocess.CalledProcessError):
        return None
    kayit, onceki = [], None
    for satir in reversed([s for s in out if s.strip()]):
        h, t = satir.split(" ", 1)
        try:
            metin = subprocess.run(["git", "-C", str(KOK), "show", f"{h}:{rel}"],
                                   capture_output=True, text=True, check=True).stdout
        except subprocess.CalledProcessError:
            return None
        d = tomllib.loads(metin)
        degisen = sorted(set(d)) if onceki is None else sorted(k for k in set(d) | set(onceki) if d.get(k) != onceki.get(k))
        kayit.append({"commit": h[:8], "zaman": t, "icerik_ozu": _icerik_ozu(d), "degisen_bolum": degisen})
        onceki = d
    simdi = tomllib.loads(ONKAYIT_YOL.read_text(encoding="utf-8"))
    if onceki is not None and simdi != onceki:
        kayit.append({"commit": None, "zaman": None, "icerik_ozu": _icerik_ozu(simdi),
                      "degisen_bolum": sorted(k for k in set(simdi) | set(onceki) if simdi.get(k) != onceki.get(k))})
    return kayit


def _temiz(x):
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, 6)
    if isinstance(x, (np.floating,)):
        return _temiz(float(x))
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, dict):
        return {str(k): _temiz(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_temiz(v) for v in x]
    return x


# ───────────────────────────────────────────── eğri: günlük birikimli R → haftalık
def haftalik(egri: dict | None) -> dict | None:
    """Günlük birikimli R eğrisinin haftanın son işlem gününe düşen değerleri (figür için).
    Azami düşüş günlük seriden hesaplanır ve ayrıca yazılır: haftalık örnekleme onu küçültürdü."""
    if not egri or not egri.get("gun"):
        return None
    s = pd.Series(egri["r"], index=pd.DatetimeIndex(egri["gun"]))
    h = s.groupby(s.index.to_period("W-FRI")).last()
    gun = s.groupby(s.index.to_period("W-FRI")).apply(lambda x: x.index[-1])
    tepe = np.maximum.accumulate(np.concatenate([[0.0], s.to_numpy()]))[1:]
    dd = tepe - s.to_numpy()
    ddh = pd.Series(dd, index=s.index).groupby(s.index.to_period("W-FRI")).max()
    return {"gun": [g.strftime("%Y-%m-%d") for g in gun], "r": [round(float(v), 3) for v in h],
            "dusus": [round(float(v), 3) for v in ddh], "azami_dusus": round(float(dd.max()), 3)}


def gunluk_seri(egri: dict | None) -> pd.Series:
    """Birikimli eğriden günlük R."""
    if not egri or not egri.get("gun"):
        return pd.Series(dtype=float)
    s = pd.Series(egri["r"], index=pd.DatetimeIndex(egri["gun"]))
    return s.diff().fillna(s.iloc[0])


# ───────────────────────────────────────────── ızgara: ısı haritası ve zaman dilimi kıyası
def isi(s: dict, eksen: tuple[str, str]) -> dict:
    """İki eksenli ızgara kesiti: öbür parametreler önceden kayıtlı varsayılanda."""
    v = s["varsayilan"]
    x_ad, y_ad = eksen
    hucre = {}
    for r in s["izgara"]:
        p = r["p"]
        if any(p.get(k) != v.get(k) for k in v if k not in (x_ad, y_ad)):
            continue
        hucre[(str(p[x_ad]), str(p[y_ad]))] = {"is": r["is"], "oos": r["oos"]}
    xs = sorted({k[0] for k in hucre}, key=lambda t: (len(t), t))
    ys = sorted({k[1] for k in hucre})
    return {"x_ad": x_ad, "y_ad": y_ad, "x": xs, "y": ys,
            "hucre": [[hucre.get((x, y)) for x in xs] for y in ys],
            "varsayilan": [str(v.get(x_ad)), str(v.get(y_ad))]}


def tf_kiyas(s: dict) -> dict:
    """Zaman dilimi kıyası: varsayılan kombinasyonun yalnız `tf`'i değişir.

    New York ilk dengesinde varsayılanın ilk denge penceresi 60 dakikadır; 60 dakikalık mumda o pencere mumun
    kendisidir (ön kayıt: "tf=60'ta ikisi aynıdır, tek sayılır") ve ızgarada `ib_pencere = "tf"` adıyla durur. Kıyas
    60 dakikayı o satırla eşler ve eşlemeyi kayda yazar."""
    v = s["varsayilan"]
    out = {}
    for r in s["izgara"]:
        p = r["p"]
        if all(p.get(k) == v.get(k) for k in v if k != "tf"):
            out[str(p["tf"])] = {"is": r["is"], "oos": r["oos"], "haber_payi": r.get("haber_payi")}
    if s.get("aile") == "nyib" and "60" not in out:
        for r in s["izgara"]:
            p = r["p"]
            if p.get("tf") == 60 and p.get("ib_pencere") == "tf" and \
                    all(p.get(k) == v.get(k) for k in v if k not in ("tf", "ib_pencere")):
                out["60"] = {"is": r["is"], "oos": r["oos"], "haber_payi": r.get("haber_payi"),
                             "esleme": "ib_pencere=tf"}
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def izgara_ozet(s: dict) -> dict:
    """Izgaranın tamamının özeti (bir parite): kaç kombinasyon örneklem içinde, dışında ve ikisinde birden net artı;
    örneklem dışının en iyi ve en kötü kombinasyonu. Isı haritası iki boyutluk bir kesittir; bu sayım bütün ızgarayı
    okur."""
    satir = [r for r in s["izgara"] if (r["is"].get("n") or 0) > 0]
    def arti(r, d):
        x = r[d].get("beklenti_r")
        return x is not None and np.isfinite(x) and x > 0
    dis = [r for r in satir if (r["oos"].get("n") or 0) > 0 and np.isfinite(r["oos"].get("beklenti_r", np.nan))]
    en_iyi = max(dis, key=lambda r: r["oos"]["beklenti_r"]) if dis else None
    en_kotu = min(dis, key=lambda r: r["oos"]["beklenti_r"]) if dis else None
    return {"n": len(s["izgara"]), "islem_acan": len(satir), "is_arti": sum(arti(r, "is") for r in satir),
            "oos_arti": sum(arti(r, "oos") for r in dis), "ikisi_arti": sum(arti(r, "is") and arti(r, "oos") for r in dis),
            "oos_en_iyi": {"p": en_iyi["p"], "r": en_iyi["oos"]["beklenti_r"], "n": en_iyi["oos"]["n"]} if en_iyi else None,
            "oos_en_kotu": {"p": en_kotu["p"], "r": en_kotu["oos"]["beklenti_r"], "n": en_kotu["oos"]["n"]} if en_kotu else None}


#: Derste tablo olarak verilen varyant kıyasları (şartname §5 N1 "1./2./3. mum", N2 "ilk mum kapanışı ↔ teyit";
#: NY IB'de ilk denge penceresi: §3'ün "aralık penceresi = teyit mumu" kuralı ile ön kaydın 60 dakikası).
VARYANT = {"n1": ["giris_mumu"], "n2": ["giris", "k"], "nyib_0800": ["ib_pencere"], "nyib_0930": ["ib_pencere"]}


def varyant(s: dict, param: str) -> dict:
    """Bir parametrenin değerleri, öbür parametreler önceden kayıtlı varsayılanda (ızgaranın kendi satırları)."""
    v = s["varsayilan"]
    out = {}
    for r in s["izgara"]:
        p = r["p"]
        if all(p.get(k) == v.get(k) for k in v if k != param):
            out[str(p[param])] = {"is": r["is"], "oos": r["oos"], "haber_payi": r.get("haber_payi")}
    return out


# ───────────────────────────────────────────── dört paritenin havuzu
def _islem_dosyasi(kok: Path, birim: str, cift: str, p: dict) -> Path:
    ad = "|".join(f"{k}={p[k]}" for k in sorted(p)).replace("|", "__").replace("=", "-").replace(":", "")
    return kok / "islem" / birim / f"{cift}__{ad}.parquet"


def havuz(kok: Path, birim: str, ciftler: list[str], p: dict, egriler: dict, a: ay.Ayar) -> dict | None:
    """Aynı kombinasyonu dört paritede birlikte koşmak: her işlem 1R risk.

    İşlem başına metrikler (beklenti, isabet, %95 aralık) dört paritenin işlemlerinin birleşiminden;
    Sharpe ve azami düşüş, dört paritenin GÜNLÜK R TOPLAMINDAN (aynı gün dört pozisyon taşınır).
    Örneklem dışı ve içi ayrı; günler pariteler arasında birleşim kümesidir."""
    parca = []
    for c in ciftler:
        yol = _islem_dosyasi(kok, birim, c, p)
        if yol.exists():
            x = pd.read_parquet(yol)
            x["cift"] = c
            parca.append(x)
    if not parca:
        return None
    isl = pd.concat(parca, ignore_index=True)
    gunler = sorted(set().union(*[set(e["gun"]) for e in egriler.values() if e]))
    gun = np.array(gunler, dtype="datetime64[D]")
    out = {}
    for ad, m in (("is", gun <= np.datetime64(a.ic_bitis)), ("oos", gun >= np.datetime64(a.dis_baslangic)),
                  ("tum", np.ones(len(gun), bool))):
        g = gun[m]
        gi = isl["gun"].to_numpy().astype("datetime64[D]")
        x = isl[(gi >= g.min()) & (gi <= g.max())] if len(g) else isl.iloc[:0]
        # %95 aralığı GÜN KÜMELİ: aynı günün dört paritedeki işlemleri doların ortak hareketiyle ilintilidir ve
        # birlikte yeniden örneklenir (işlemleri bağımsız sayan aralık fazla dar çıkar). İşlem başına aralık bilgi
        # olarak yanında durur.
        oz = mk.ozet(x, g, kume_sutun="gun")
        al = mk.alinan(x)
        oz["ga_islem_alt"], oz["ga_islem_ust"] = mk.bootstrap_ort(al["r"].to_numpy()) if len(al) else (None, None)
        # günlük R toplamı: dört paritenin günlük R'si toplanır (mk.gunluk_r gün başına toplar)
        oz["pariteler"] = sorted(x["cift"].unique().tolist()) if len(x) else []
        out[ad] = oz
    return out


def _birlesik_islem(kok: Path, birim: str, ciftler: list[str], p: dict) -> pd.DataFrame:
    parca = []
    for c in ciftler:
        yol = _islem_dosyasi(kok, birim, c, p)
        if yol.exists():
            x = pd.read_parquet(yol)
            x["cift"] = c
            parca.append(mk.alinan(x))
    return pd.concat(parca, ignore_index=True) if parca else pd.DataFrame()


def haber_olay(isl: pd.DataFrame, a: ay.Ayar) -> dict:
    """Haber kuralının dört paritelik havuzu, olay ve ilk mum kovası başına. Gözlem birimi OLAYDIR (olay tipi ×
    tarih): işlem sayısı aynı ABD olayının dört paritedeki ölçümünü ayrı sayar, olay sayısı saymaz; %95 aralığı olay
    kümeli bootstrap'tir. N3 ve N4'te haber öncesi aralığın genişliği (pip) olay olay — basın toplantılarında o
    aralık kararın kendi tepkisidir."""
    if not len(isl):
        return {}
    gun = isl["gun"].to_numpy().astype("datetime64[D]")
    kume = isl["olay"].astype(str) + "|" + isl["tarih"].astype(str)
    out: dict = {}
    for boyut in ("olay", "kova"):
        out[boyut] = {}
        for deger, g in isl.groupby(boyut, sort=True):
            m_g = isl.index.isin(g.index)
            satir = {}
            for ad, m in (("tum", np.ones(len(isl), bool)), ("oos", gun >= np.datetime64(a.dis_baslangic))):
                mm = m_g & m
                r = isl["r"].to_numpy()[mm]
                if not len(r):
                    satir[ad] = {"n": 0}
                    continue
                alt, ust = mk.bootstrap_kume_ort(r, kume.to_numpy()[mm])
                satir[ad] = {"n": int(len(r)), "n_olay": int(kume[mm].nunique()), "r": float(r.mean()),
                             "ga_alt": alt, "ga_ust": ust, "isabet": float((isl["pnl_pip"].to_numpy()[mm] > 0).mean())}
            out[boyut][str(deger)] = satir
    if {"ust", "alt"} <= set(isl.columns) and isl["ust"].notna().any():
        pip_nokta = {c: a.nokta_pip(c) for c in isl["cift"].unique()}
        genislik = (isl["ust"] - isl["alt"]) / isl["cift"].map(pip_nokta)
        out["aralik_pip"] = {}
        for olay, g in genislik.groupby(isl["olay"]):
            out["aralik_pip"][str(olay)] = {"medyan": float(g.median()), "n": int(g.notna().sum()),
                                            "cift": {c: float(x.median()) for c, x in g.groupby(isl.loc[g.index, "cift"])}}
    return out


def hedef_uzaklik(isl: pd.DataFrame) -> dict | None:
    """Hedefin girişten uzaklığı, girişteki risk biriminde ((hedef − giriş)·yön / R): R katı hedefte tanımı gereği
    k, seviye hedefinde (VWAP, pivot, haber öncesi fiyat, aralığın öbür ucu) işlemden işleme değişir."""
    if not len(isl) or "hedef" not in isl:
        return None
    x = isl[np.isfinite(isl["hedef"].to_numpy(float))]
    if not len(x):
        return None
    u = (x["hedef"] - x["giris_f"]) * x["yon"] / x["R"]
    out = {"n": int(len(u)), "medyan": float(u.median()), "c1": float(u.quantile(0.25)), "c3": float(u.quantile(0.75)),
           "pay_2r_ustu": float((u > 2).mean()), "cift": {c: float(g.median()) for c, g in u.groupby(x["cift"])}}
    return out


def gun_ici_yogunluk(kok: Path, birim: str, ciftler: list[str], p: dict, a: ay.Ayar) -> dict:
    """Örneklem dışında işlem açılan günlerin kaçında iki ya da daha çok işlem var ve kaç sinyal açık pozisyon
    yüzünden alınmadı (tek pozisyon kuralı)."""
    out = {}
    for c in ciftler:
        yol = _islem_dosyasi(kok, birim, c, p)
        if not yol.exists():
            continue
        x = pd.read_parquet(yol)
        x = x[x["gun"].to_numpy().astype("datetime64[D]") >= np.datetime64(a.dis_baslangic)]
        al = x[x["durum"] == 0]
        sayi = al.groupby("gun").size()
        out[c] = {"islem_gunu": int(len(sayi)), "iki_ve_ustu": int((sayi >= 2).sum()),
                  "pay": float((sayi >= 2).mean()) if len(sayi) else None,
                  "atlanan_sinyal": int((x["durum"] == 1).sum()), "islem": int(len(al))}
    return out


# ───────────────────────────────────────────── birim
def birim_ozet(kok: Path, birim: str, ciftler: list[str], a: ay.Ayar, isi_eksen: tuple[str, str]) -> dict | None:
    import kosu
    sonuc = {c: _oku(kok / "sonuc" / birim / f"{c}.json") for c in ciftler}
    sonuc = {c: s for c, s in sonuc.items() if s}
    if not sonuc:
        return None
    ilk = next(iter(sonuc.values()))
    # Birimin GERÇEK ızgarasının değerleri (koşulan kombinasyonlardan): ders tablosu ailenin ızgarasını değil bunu
    # basar. Birimin sabitlediği boyut tek değerle görünür; tanımsız bileşimler (NY IB'de 60 dk mum + 60 dk ilk denge,
    # pivot kırılımında 'seviye' hedefi) zaten listede yoktur.
    izgara_deger: dict = {}
    for r in ilk["izgara"]:
        for k, v in r["p"].items():
            izgara_deger.setdefault(k, [])
            if v not in izgara_deger[k]:
                izgara_deger[k].append(v)
    out = {"aile": ilk["aile"], "kombinasyon": ilk["kombinasyon"], "varsayilan": ilk["varsayilan"], "cift": {},
           "izgara_deger": izgara_deger,
           # birimin sabitlediği boyutlar ve ön kaydın kendi varsayılanı (birim varsayılanı ondan türetilir: NY IB 08:00)
           "sabit": dict(kosu.BIRIMLER[birim]["sabit"]),
           "onkayit_varsayilan": dict(kosu.ONKAYIT[ilk["aile"]][kosu.BIRIMLER[birim]["varsayilan"]])}
    egri_v, egri_s = {}, {}
    for c, s in sonuc.items():
        va, se, wf = s.get("varsayilan_analiz"), s.get("secilen_analiz"), s.get("walk_forward") or {}
        egri_v[c] = (va or {}).get("egri")
        egri_s[c] = (se or {}).get("egri")
        kirp = lambda d: {k: v for k, v in (d or {}).items() if k not in ("egri", "ornek", "p")} if d else None  # noqa: E731
        out["cift"][c] = {
            "varsayilan": kirp(va), "secilen_p": s.get("secilen"), "secilen": kirp(se),
            "walk_forward": {"secimler": wf.get("secimler"), "ozet": wf.get("ozet"),
                             "sinanan_yillar": wf.get("sinanan_yillar")},
            "isi": isi(s, isi_eksen), "izgara_ozet": izgara_ozet(s),
            "tf": tf_kiyas(s), "tf_haber_kaymasiz": s.get("tf_haber_kaymasiz"),
            "varyant": {pa: varyant(s, pa) for pa in VARYANT.get(birim, [])},
            "egri": {"varsayilan": haftalik(egri_v[c]), "secilen": haftalik(egri_s[c]),
                     "walk_forward": haftalik(wf.get("egri"))},
            "ornek": (va or {}).get("ornek") or [],
        }
    out["havuz"] = {"varsayilan": havuz(kok, birim, list(sonuc), ilk["varsayilan"], egri_v, a)}
    tum_islem = _birlesik_islem(kok, birim, list(sonuc), ilk["varsayilan"])
    if "olay" in tum_islem.columns:
        out["haber_olay"] = haber_olay(tum_islem, a)
    out["hedef_uzaklik"] = hedef_uzaklik(tum_islem)
    out["gun_ici"] = gun_ici_yogunluk(kok, birim, list(sonuc), ilk["varsayilan"], a)
    # Hüküm özeti: parite başına önceden kayıtlı varsayılan ve ızgaradan seçilen
    out["hukum"] = {c: {"varsayilan": (v["varsayilan"] or {}).get("hukum"),
                        "varsayilan_tum": (v["varsayilan"] or {}).get("hukum_tum"),
                        "secilen": (v["secilen"] or {}).get("hukum") if v["secilen"] else None,
                        "maliyet_yiyor": (v["varsayilan"] or {}).get("maliyet_yiyor"),
                        "maliyet_yiyor_oos": (v["varsayilan"] or {}).get("maliyet_yiyor_oos")}
                    for c, v in out["cift"].items()}
    out["_gunluk_varsayilan"] = {c: gunluk_seri(e) for c, e in egri_v.items()}
    return out


def korelasyon(birimler: dict, a: ay.Ayar) -> dict:
    """Stratejiler arası günlük R korelasyonu: her birimin önceden kayıtlı varsayılanı, dört paritenin
    günlük R toplamı (havuz). İşlemsiz günler 0 sayılır (Sharpe ile aynı tanım); bütün dönem ve
    örneklem dışı ayrı. Birlikte işlem görmeyen iki stratejinin korelasyonu tanımsız değil SIFIRA
    yakındır — bu bir çeşitlendirme ölçüsüdür, 'aynı şeyi mi alıyorlar' sorusunun cevabı."""
    seriler = {}
    for b, v in birimler.items():
        g = [s for s in v["_gunluk_varsayilan"].values() if len(s)]
        if g:
            seriler[b] = pd.concat(g, axis=1, sort=True).fillna(0.0).sum(axis=1)
    if len(seriler) < 2:
        return {}
    df = pd.concat(seriler, axis=1, sort=True).fillna(0.0)
    out = {"birimler": list(df.columns)}
    for ad, m in (("tum", np.ones(len(df), bool)), ("oos", df.index >= pd.Timestamp(a.dis_baslangic))):
        c = df[m].corr()
        out[ad] = [[None if not np.isfinite(x) else round(float(x), 3) for x in row] for row in c.to_numpy()]
    return out


# ───────────────────────────────────────────── zaman tablosu (TSİ)
def zaman_tablosu(a: ay.Ayar) -> dict:
    yillar = list(range(a.baslangic.year, a.bitis.year + 1))
    ara = {str(y): [{"ilk": b.isoformat(), "son": s.isoformat(), "rejim": r} for b, s, r in z.ara_donemler(y)]
           for y in yillar}
    # Her rejimden bir temsilci gün (2026): olayların TSİ saati rejime göre değişir.
    temsil = [date(2026, 1, 15), date(2026, 3, 18), date(2026, 6, 17), date(2026, 10, 28)]
    return {"ara_donem": ara, "gecis": {str(y): [(g.isoformat(), t) for g, t in z.gecisler(y)] for y in yillar},
            "tablo": z.tsi_tablosu(temsil), "rejim_adi": z.REJIM_ADI,
            # Ölçüm dosyası anahtarları sıralı yazar; tablonun satır sırası ayrıca taşınır (zaman.OLAYLAR).
            "olay_sira": [ad for ad, _, _ in z.OLAYLAR],
            "tsi_sabit": z.tsi_sabit_mi(a.baslangic, a.bitis)}


# ───────────────────────────────────────────── takvim ve veri
#: Takvim satırının notunda saati bir KURALDAN aldığını söyleyen kalıplar (takvim_kur.py'nin yazdığı notlar):
#: Fed'in 13.03.2013 kuralı, ECB'nin 27.06.2022 karar saati duyurusu, BoE'nin yayım kuralı.
SAAT_KURAL_KALIP = r"kuralından|yayım kuralı|karar saati ECB"


def takvim_ozet() -> dict:
    d = BURASI / "veri" / "takvim"
    out = {"kunye": _oku(d / "kunye.json"), "sinama": None, "sayim": {}}
    if (d / "olaylar.csv").exists():
        df = pd.read_csv(d / "olaylar.csv", dtype=str, keep_default_na=False)
        out["sayim"] = {o: {"toplam": int(len(g)), "yil": {y: int(n) for y, n in g["tarih"].str[:4].value_counts()
                                                           .sort_index().items()},
                            # yerel saat × bölge dağılımı ve kaynağın alan adı (dersin takvim tablosu)
                            "saat": {f"{s} {b}": int(n) for (s, b), n in g.groupby(["yerel_saat", "bolge"]).size().items()},
                            # her yerel saatin ilk ve son tarihi (saat değişikliklerinin günü: ECB 13:45 → 14:15)
                            "saat_aralik": {f"{s} {b}": [x["tarih"].min(), x["tarih"].max()]
                                            for (s, b), x in g.groupby(["yerel_saat", "bolge"])},
                            "olaganustu": [{"tarih": r["tarih"], "saat": r["yerel_saat"], "bolge": r["bolge"]}
                                           for _, r in g.iterrows() if "olağanüstü" in r["not"]],
                            # saatin kaynağı: o tarihin kendi metni (ambargo satırı, karar metninin yayım saati,
                            # duyurunun cümlesi, Fed'in etkinlik takvimi) ya da kurumun yayım KURALI
                            "saat_kaynagi": {"tarih": int((~g["not"].str.contains(SAAT_KURAL_KALIP)).sum()),
                                             "kural": int(g["not"].str.contains(SAAT_KURAL_KALIP).sum())},
                            "kaynak": sorted({u.split("/")[2] for u in g["kaynak"] if u.startswith("http")}),
                            "ilk": g["tarih"].min(), "son": g["tarih"].max()}
                        for o, g in df.groupby("olay")}
        # Fed'in etkinlik takviminin basın toplantısını AYRI SATIRLA listelediği dönem: o dönemin kaç toplantısında satır
        # var ve hangisinde yok (satırsız toplantının saati kuraldan gelir). Metodoloji dersinin "N toplantının M'i"
        # cümlesi buradan; ilk satırlı toplantıdan önceki toplantılar dönemin dışındadır.
        tt = ((((out["kunye"] or {}).get("fomc") or {}).get("basin_saat_tarih")) or {}).get("takvim") or []
        if tt and "FOMC_basin" in set(df["olay"]):
            gb = df[(df["olay"] == "FOMC_basin") & (df["tarih"] >= min(tt))]["tarih"]
            out["fomc_takvim_donemi"] = {"ilk": min(tt), "toplanti": int(len(gb)), "satirli": int(gb.isin(tt).sum()),
                                         "satirsiz": sorted(gb[~gb.isin(tt)].tolist())}
    s = _oku(d / "sinama.json")
    if s:
        # Basın toplantıları fiyattan SINANMAZ (konuşma tek dakikada sıçrama yapmaz); bilgi olarak toplantının ilk
        # 15 dakikasındaki ortalama dakikalık aralığın önceki 15 dakikaya oranı, parite başına.
        bilgi: dict = {}
        for e in s.get("olay") or []:
            if e.get("hukum") != "basin_bilgi":
                continue
            for p, v in (e.get("parite") or {}).items():
                r = (v or {}).get("ilk15_once15_orani")
                if r is not None and np.isfinite(r):
                    bilgi.setdefault(e["olay"], {}).setdefault(p, []).append(float(r))
        out["sinama"] = {"kural": s.get("kural"), "ozet": s.get("ozet"), "celiski": s.get("celiski"),
                         "celiski_olay": [e for e in s.get("olay") or [] if e.get("hukum") == "celiski"],
                         "basin_bilgi": {o: {p: {"n": len(x), "medyan": float(np.median(x)),
                                                 "birden_buyuk": int(sum(r > 1 for r in x))}
                                             for p, x in sorted(v.items())} for o, v in sorted(bilgi.items())}}
    return out


def veri_ozet() -> dict:
    kunye = {}
    for yol in sorted((ay.DUKA / "kunye").glob("*.json")):
        for k, v in (_oku(yol) or {}).get("birimler", {}).items():
            kunye[k] = {x: v.get(x) for x in ("gun", "gun_dolu", "satir", "tam", "istek", "ret", "sha256",
                                               "icerik_ozu", "ilk_gun", "son_gun")}
            kunye[k]["gun_bos"] = len(v.get("gun_bos", []))
            kunye[k]["gun_404"] = len(v.get("gun_404", []))
            # Kaynağın boş ya da "yok" döndürdüğü günler adıyla (az sayıda): dolu gün ile istenen gün arasındaki fark.
            kunye[k]["bos_gunler"] = sorted({str(x)[:10] for x in (v.get("gun_bos") or []) + (v.get("gun_404") or [])})
            kunye[k]["gun_hata"] = len(v.get("gun_hata", []))
    kalite = _oku(ay.DUKA / "kalite.json")
    return {"kalite": kalite, "arsiv": kunye, "tatil_uyum": tatil_uyum(kalite)}


def _fx_gunu(utc: str) -> date:
    """UTC damganın FX günü: New York 17:00'da başlayan gün (17:00 ve sonrası ertesi günün etiketi)."""
    t = pd.Timestamp(utc, tz="UTC").tz_convert(z.NEWYORK)
    return (t + pd.Timedelta(days=1)).date() if t.hour >= 17 else t.date()


def tatil_uyum(kalite: dict | None) -> dict | None:
    """Stratejilerin tatil takvimi (gunluk.TATIL_TAKVIM: 25 Aralık ve 1 Ocak, hafta içine düştüğünde) ile arşivde
    kapsamı %50'nin altında kalan işlem günlerinin (kalite.py) parite parite karşılaştırması. Takvim kuraldır,
    kapsam ölçüdür; ikisinin aynı günleri verdiği bir beyan değil bu kayıttır."""
    from gunluk import TATIL_TAKVIM
    if not kalite:
        return None
    out = {}
    for c, e in sorted(kalite.items()):
        if not isinstance(e, dict) or not e.get("ilk") or not e.get("son"):
            continue
        g0, g1 = _fx_gunu(e["ilk"]), _fx_gunu(e["son"])
        takvim = sorted(g.isoformat() for g in pd.bdate_range(g0, g1).date if (g.month, g.day) in TATIL_TAKVIM)
        kapsam = sorted(x[0] for x in (e.get("kapsam") or {}).get("tatil_gunleri") or [])
        out[c] = {"takvim": len(takvim), "kapsam": len(kapsam), "ayni": takvim == kapsam,
                  "yalniz_takvim": sorted(set(takvim) - set(kapsam)), "yalniz_kapsam": sorted(set(kapsam) - set(takvim)),
                  "ilk_fx_gunu": g0.isoformat(), "son_fx_gunu": g1.isoformat()}
    return out


def ay_sonu_kayan(bas: date, bit: date) -> list[str]:
    """Ayın son hafta içi günü ile ayın son Londra iş günü (ön kaydın ay sonu tanımı) ayrışan aylar, örneklemin
    içinde tamamlanan aylarda: o aylarda ay sonu bir önceki iş gününe kayar."""
    out = []
    ay_ = date(bas.year, bas.month, 1)
    while True:
        sonraki = date(ay_.year + (ay_.month == 12), ay_.month % 12 + 1, 1)
        son = sonraki - pd.Timedelta(days=1).to_pytimedelta()
        if son > bit:
            break
        g = son
        while g.weekday() >= 5:
            g -= pd.Timedelta(days=1).to_pytimedelta()
        if not z.londra_ay_sonu(g):
            out.append(f"{ay_.year:04d}-{ay_.month:02d}")
        ay_ = sonraki
    return out


def ileri_bakma_kapsami() -> dict | None:
    """İleriye bakma sınamasının kapsamı, sınamanın KENDİ dosyasından (testler/test_strateji.py, sentetik.py):
    kesim anları, kesim başına koşulan kombinasyon sayısı ve sentetik serinin uzunluğu. Metodoloji dersi sınamayı bu
    kayıtla anlatır; sınama değişirse ders cümlesi de değişir. Okunamazsa None (ders üretimi iddiada düşer)."""
    import ast
    try:
        t = ast.parse((BURASI / "testler" / "test_strateji.py").read_text(encoding="utf-8"))
        st = ast.parse((BURASI / "testler" / "sentetik.py").read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None
    deger, kesim, sinama = {}, None, []
    for n in t.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            ad = n.targets[0].id
            if ad in ("ORNEK_ILK", "ORNEK_OTEKI") and isinstance(n.value, ast.Constant):
                deger[ad] = int(n.value.value)
            if ad == "KESIMLER":
                kesim = [x.value for x in ast.walk(n.value) if isinstance(x, ast.Constant) and isinstance(x.value, str)
                         and len(x.value) == 16]
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"):
            sinama.append(n.name)
    gun = bas = None
    for n in st.body:
        if isinstance(n, ast.FunctionDef) and n.name == "dakika_uret":
            ad_ = [a.arg for a in n.args.args]
            dv = dict(zip(ad_[len(ad_) - len(n.args.defaults):], n.args.defaults))
            gun = dv["gun"].value if isinstance(dv.get("gun"), ast.Constant) else None
            bas = dv["bas"].value if isinstance(dv.get("bas"), ast.Constant) else None
    if not kesim or set(deger) != {"ORNEK_ILK", "ORNEK_OTEKI"} or gun is None:
        return None
    yerel = []
    for x in kesim:
        u = pd.Timestamp(x, tz="UTC")
        lo, ny = u.tz_convert(z.LONDRA).strftime("%H:%M"), u.tz_convert(z.NEWYORK).strftime("%H:%M")
        # Kesim anının seansı (dersin sözcükleri bu sınıftan okunur): UTC gece yarısının ilk saati, Londra
        # açılışından önce, Londra sabahı (açılış → 12:00), New York sabahı (12:00'ye kadar), öbürü.
        an = ("utc_gece_yarisi_sonrasi" if u.hour == 0 else "londra_acilis_oncesi" if lo < "08:00" else
              "londra_sabahi" if lo < "12:00" else "new_york_sabahi" if ny < "12:00" else "diger")
        yerel.append({"utc": x, "londra": lo, "new_york": ny, "an": an,
                      "tsi": u.tz_convert("Europe/Istanbul").strftime("%H:%M")})
    return {"kesim": yerel, "kesim_n": len(kesim), "ornek_ilk": deger["ORNEK_ILK"],
            "ornek_ilk_rastgele": deger["ORNEK_ILK"] - 1, "ornek_oteki": deger["ORNEK_OTEKI"],
            "ornek_oteki_rastgele": deger["ORNEK_OTEKI"] - 1, "sentetik_gun": int(gun), "sentetik_bas": bas,
            "sinama": sinama}


# ───────────────────────────────────────────── ana
def kur(kok: Path | None = None) -> dict:
    import kosu
    a = ay.oku()
    kok = kok or (BURASI / "cikti")
    ciftler = list(a.ciftler)
    birimler = {}
    for b in kosu.BIRIMLER:
        v = birim_ozet(kok, b, ciftler, a, kosu.ISI[b])
        if v:
            birimler[b] = v
    kor = korelasyon(birimler, a)
    for v in birimler.values():
        v.pop("_gunluk_varsayilan", None)
    haber = {c: _oku(kok / "sonuc" / "haber" / f"{c}.json") for c in ciftler}
    onk = tomllib.loads(ONKAYIT_YOL.read_text(encoding="utf-8"))
    olcum = {
        "kunye": {
            "baslangic": a.baslangic.isoformat(), "bitis": a.bitis.isoformat(),
            "ic_bitis": a.ic_bitis.isoformat(), "dis_baslangic": a.dis_baslangic.isoformat(),
            "ciftler": ciftler, "nokta": {c: a.nokta[c] for c in ciftler}, "pip": {c: a.pip[c] for c in ciftler},
            "zaman_dilimleri": list(a.zaman_dilimleri), "kayma_pip": list(a.kayma_pip),
            "temel_kayma_pip": onk["genel"]["temel_kayma_pip"], "haber_kayma_pip": a.haber_kayma_pip,
            "haber_pencere_dk": list(a.haber_pencere_dk), "gun_sonu_et": a.gun_sonu_et,
            "onkayit_ozu": _oz(ONKAYIT_YOL), "ayar_ozu": _oz(BURASI / "ayar.toml"),
            "onkayit_icerik_ozu": _icerik_ozu(onk), "onkayit_gecmisi": onkayit_gecmisi(),
            "hukum_kurali": onk["hukum"], "secim": onk["secim"], "saglamlik": onk["saglamlik"],
            "kosul": onk["kosul"],
            # Ön kaydın yazmadığı uygulama eşikleri (hüküm kuralının şartları kendi asgarileriyle kurulur): tek
            # tanımları kodda, ders bunları buradan okur.
            "uygulama_esik": {"bootstrap": mk.ASGARI_BOOTSTRAP, "rastgele": sg.ASGARI_RASTGELE,
                              "kosul_oos": sg.ASGARI_KOSUL_OOS, "az_islem": kosu.ASGARI_RASTGELE},
            "ileri_bakma": ileri_bakma_kapsami(),
            "ornek": {"esik": kosu.ORNEK_ESIK, "ek_kayma": kosu.ORNEK_EK_KAYMA},
            # Ön kaydın kural aileleri ve ölçümün birimleri: bir aile birden çok birime bölündüyse adıyla.
            "aile_n": len({v["aile"] for v in kosu.BIRIMLER.values()}),
            "bolunen_aile": sorted({v["aile"] for v in kosu.BIRIMLER.values()
                                    if sum(1 for x in kosu.BIRIMLER.values() if x["aile"] == v["aile"]) > 1}),
            "ay_sonu_kayan": ay_sonu_kayan(a.baslangic, a.bitis),
        },
        "zaman": zaman_tablosu(a),
        "takvim": takvim_ozet(),
        "veri": veri_ozet(),
        "birim": birimler,
        "korelasyon": kor,
        "haber": {"cift": {c: h for c, h in haber.items() if h}, "devam": _oku(kok / "sonuc" / "haber" / "devam.json")},
    }
    return _temiz(olcum)


def main(argv: list[str]) -> int:
    kok = Path(argv[0]) if argv else None
    o = kur(kok)
    hedef = (kok or (BURASI / "cikti")) / "ders" / "olcum.json"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
                     encoding="utf-8")
    print(f"✓ {hedef} · {hedef.stat().st_size / 1e6:.1f} MB · {len(o['birim'])} birim")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
