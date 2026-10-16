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
  cikti/ders/olcum.json                 figürler (sekil.py) ve ders metni (ders.py) buradan okur
  site/src/data/fx_gunici.json          tablo bileşeninin verisi: olcum.json'un eğri, örnek gün
                                        ve patika dizileri çıkarılmış hâli (sayfa derlemesi küçük kalsın)

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
import zaman as z

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
SITE_VERI = KOK / "site" / "src" / "data" / "fx_gunici.json"
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
    """Zaman dilimi kıyası: varsayılan kombinasyonun yalnız `tf`'i değişir."""
    v = s["varsayilan"]
    out = {}
    for r in s["izgara"]:
        p = r["p"]
        if all(p.get(k) == v.get(k) for k in v if k != "tf"):
            out[str(p["tf"])] = {"is": r["is"], "oos": r["oos"]}
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


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
        oz = mk.ozet(x, g)
        # günlük R toplamı: dört paritenin günlük R'si toplanır (mk.gunluk_r gün başına toplar)
        oz["pariteler"] = sorted(x["cift"].unique().tolist()) if len(x) else []
        out[ad] = oz
    return out


# ───────────────────────────────────────────── birim
def birim_ozet(kok: Path, birim: str, ciftler: list[str], a: ay.Ayar, isi_eksen: tuple[str, str]) -> dict | None:
    sonuc = {c: _oku(kok / "sonuc" / birim / f"{c}.json") for c in ciftler}
    sonuc = {c: s for c, s in sonuc.items() if s}
    if not sonuc:
        return None
    ilk = next(iter(sonuc.values()))
    out = {"aile": ilk["aile"], "kombinasyon": ilk["kombinasyon"], "varsayilan": ilk["varsayilan"], "cift": {}}
    egri_v, egri_s = {}, {}
    for c, s in sonuc.items():
        va, se, wf = s.get("varsayilan_analiz"), s.get("secilen_analiz"), s.get("walk_forward") or {}
        egri_v[c] = (va or {}).get("egri")
        egri_s[c] = (se or {}).get("egri")
        kirp = lambda d: {k: v for k, v in (d or {}).items() if k not in ("egri", "ornek", "p")} if d else None  # noqa: E731
        out["cift"][c] = {
            "varsayilan": kirp(va), "secilen_p": s.get("secilen"), "secilen": kirp(se),
            "walk_forward": {"secimler": wf.get("secimler"), "ozet": wf.get("ozet")},
            "isi": isi(s, isi_eksen), "tf": tf_kiyas(s),
            "egri": {"varsayilan": haftalik(egri_v[c]), "secilen": haftalik(egri_s[c]),
                     "walk_forward": haftalik(wf.get("egri"))},
            "ornek": (va or {}).get("ornek") or [],
        }
    out["havuz"] = {"varsayilan": havuz(kok, birim, list(sonuc), ilk["varsayilan"], egri_v, a)}
    # Hüküm özeti: parite başına önceden kayıtlı varsayılan ve ızgaradan seçilen
    out["hukum"] = {c: {"varsayilan": (v["varsayilan"] or {}).get("hukum"),
                        "secilen": (v["secilen"] or {}).get("hukum") if v["secilen"] else None,
                        "maliyet_yiyor": (v["varsayilan"] or {}).get("maliyet_yiyor")}
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
            seriler[b] = pd.concat(g, axis=1).fillna(0.0).sum(axis=1)
    if len(seriler) < 2:
        return {}
    df = pd.concat(seriler, axis=1).fillna(0.0)
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
            "tsi_sabit": z.tsi_sabit_mi(a.baslangic, a.bitis)}


# ───────────────────────────────────────────── takvim ve veri
def takvim_ozet() -> dict:
    d = BURASI / "veri" / "takvim"
    out = {"kunye": _oku(d / "kunye.json"), "sinama": None, "sayim": {}}
    if (d / "olaylar.csv").exists():
        df = pd.read_csv(d / "olaylar.csv", dtype=str, keep_default_na=False)
        out["sayim"] = {o: {"toplam": int(len(g)), "yil": {y: int(n) for y, n in g["tarih"].str[:4].value_counts()
                                                           .sort_index().items()}}
                        for o, g in df.groupby("olay")}
    s = _oku(d / "sinama.json")
    if s:
        out["sinama"] = {"kural": s.get("kural"), "ozet": s.get("ozet"), "tutmayan": s.get("tutmayan")}
    return out


def veri_ozet() -> dict:
    kunye = {}
    for yol in sorted((ay.DUKA / "kunye").glob("*.json")):
        for k, v in (_oku(yol) or {}).get("birimler", {}).items():
            kunye[k] = {x: v.get(x) for x in ("gun", "gun_dolu", "satir", "tam", "istek", "ret", "sha256",
                                               "icerik_ozu", "ilk_gun", "son_gun")}
            kunye[k]["gun_bos"] = len(v.get("gun_bos", []))
            kunye[k]["gun_404"] = len(v.get("gun_404", []))
            kunye[k]["gun_hata"] = len(v.get("gun_hata", []))
    return {"kalite": _oku(ay.DUKA / "kalite.json"), "arsiv": kunye}


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
            "ciftler": ciftler, "zaman_dilimleri": list(a.zaman_dilimleri), "kayma_pip": list(a.kayma_pip),
            "temel_kayma_pip": onk["genel"]["temel_kayma_pip"], "haber_kayma_pip": a.haber_kayma_pip,
            "haber_pencere_dk": list(a.haber_pencere_dk), "gun_sonu_et": a.gun_sonu_et,
            "onkayit_ozu": _oz(ONKAYIT_YOL), "ayar_ozu": _oz(BURASI / "ayar.toml"),
            "onkayit_icerik_ozu": _icerik_ozu(onk), "onkayit_gecmisi": onkayit_gecmisi(),
            "hukum_kurali": onk["hukum"], "secim": onk["secim"], "saglamlik": onk["saglamlik"],
            "kosul": onk["kosul"],
        },
        "zaman": zaman_tablosu(a),
        "takvim": takvim_ozet(),
        "veri": veri_ozet(),
        "birim": birimler,
        "korelasyon": kor,
        "haber": {"cift": {c: h for c, h in haber.items() if h}, "devam": _oku(kok / "sonuc" / "haber" / "devam.json")},
    }
    return _temiz(olcum)


def site_kesiti(o: dict) -> dict:
    """Tablo bileşeninin verisi: büyük diziler (eğri, örnek gün, patika) çıkarılır."""
    k = json.loads(json.dumps(o))
    for v in k.get("birim", {}).values():
        for c in v.get("cift", {}).values():
            c.pop("egri", None)
            c.pop("ornek", None)
    for h in k.get("haber", {}).get("cift", {}).values():
        h.pop("patika", None)
    return k


def main(argv: list[str]) -> int:
    kok = Path(argv[0]) if argv else None
    o = kur(kok)
    hedef = (kok or (BURASI / "cikti")) / "ders" / "olcum.json"
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(json.dumps(o, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
                     encoding="utf-8")
    print(f"✓ {hedef} · {hedef.stat().st_size / 1e6:.1f} MB · {len(o['birim'])} birim")
    if not argv:
        SITE_VERI.write_text(json.dumps(site_kesiti(o), ensure_ascii=False, separators=(",", ":"),
                                        sort_keys=True) + "\n", encoding="utf-8")
        print(f"✓ {SITE_VERI.relative_to(KOK)} · {SITE_VERI.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
