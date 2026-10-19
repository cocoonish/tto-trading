#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Süzgeç çalışması: ön kayıtlı altı süzgeç (onkayit_suzgec.toml) ana koşunun varsayılan işlemlerine.

Yeniden koşu yok: süzgeç bir işlemi ya tutar ya atar ("atla" kipi; o gün yerine başka sinyal aranmaz). Her süzgeç
giriş anında bilinen bilgiden kurulur. Birincil birim kural başına dört parite birlikte. Seçim (2018–2023 havuz
Sharpe'ı) ve hüküm (2024 →; ana ön kaydın [hukum] kuralı) ön kayıttaki gibi.

Çıktı: cikti/suzgec/olcum.json. Kullanım: .venv/bin/python suzgec.py
"""
from __future__ import annotations

import json
import sys
import time
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

import ayar as ay
import kosu as ks
import metrik as mk
import saglamlik as sg
from ozellik import ozellikler

BURASI = Path(__file__).resolve().parent
OK = tomllib.loads((BURASI / "onkayit_suzgec.toml").read_text(encoding="utf-8"))
CIKTI = ks.CIKTI / "suzgec"
SUZGECLER = list(OK["suzgec"]["liste"])
ADAYLAR = ["yok"] + SUZGECLER
OYNAK = float(OK["suzgec"]["oynak_esik"])
EMA_GUN = int(OK["suzgec"]["ema_gun"])
IC_BITIS = np.datetime64(OK["girdi"]["ic"][1])
DIS_BAS = np.datetime64(OK["girdi"]["dis_baslangic"])
RASTGELE_TEKRAR = int(ks.ONKAYIT["hukum"]["rastgele_tekrar"])
RASTGELE_ESIK = float(ks.ONKAYIT["hukum"]["rastgele_esik_yuzdelik"])


def ema_onceki(g) -> np.ndarray:
    """Gün k için: k'den ÖNCEKİ son tatil olmayan güne kadar FX günü kapanışlarının EMA(20)'si (span 20, ilk değer
    ilk kapanış). Önünde 20'den az tatil olmayan gün olan günlerde NaN."""
    idx = np.flatnonzero(~np.asarray(g.tatil, dtype=bool))
    e = pd.Series(g.c[idx]).ewm(span=EMA_GUN, adjust=False).mean().to_numpy()
    n = len(g.gun)
    p = np.searchsorted(idx, np.arange(n), side="left") - 1   # önceki tatil olmayan günün idx sırası
    out = np.where(p >= EMA_GUN - 1, e[np.clip(p, 0, None)], np.nan)
    return out


def maskeler(b, isl: pd.DataFrame, ema: np.ndarray) -> dict[str, np.ndarray]:
    """Altı süzgecin işlem başına tut maskesi (alınmayan satırlar da hesaplanır; ölçüye alinan() süzer)."""
    f = ozellikler(b, isl)
    k = isl["gun_k"].to_numpy(np.int64)
    yon = isl["yon"].to_numpy(np.int64)
    fiyat = isl["giris_f"].to_numpy(np.float64)
    e = ema[k]
    with np.errstate(invalid="ignore"):
        m_ema = np.isfinite(e) & np.isfinite(fiyat) & (np.sign(fiyat - e) * yon > 0)
        m_t60 = (f["trend60"] == "trend yönünde").to_numpy()
        m_oyn = (f["oynaklik_yuzdelik"].to_numpy(np.float64) >= OYNAK)
        ra = f["range_atr"].to_numpy(np.float64)
    gun = isl["gun"].to_numpy()
    alinan = (isl["durum"].to_numpy() == 0)
    ic = alinan & (gun <= IC_BITIS) & np.isfinite(ra)
    if ic.sum() >= 1 and np.isfinite(ra).any():
        med = float(np.median(ra[ic]))
        with np.errstate(invalid="ignore"):
            m_dar = np.isfinite(ra) & (ra <= med)
        dar_var = True
    else:
        med, m_dar, dar_var = None, None, False
    out = {"yok": np.ones(len(isl), bool), "ema20": m_ema, "trend60": m_t60, "oynak": m_oyn,
           "ema20_oynak": m_ema & m_oyn}
    if dar_var:
        out["dar"] = m_dar
        out["ema20_dar"] = m_ema & m_dar
    return out, med


def havuz_ozet(parcalar: list[pd.DataFrame], gunler: np.ndarray) -> dict:
    """Dört paritenin işlemleri birlikte. Sharpe dört paritenin günlük R toplamlarından (ana koşunun tanımı)."""
    if not parcalar:
        return {"n": 0}
    x = pd.concat(parcalar, ignore_index=True)
    o = mk.ozet(x, gunler)
    keep = ("n", "isabet", "beklenti_r", "brut_r", "ga_alt", "ga_ust", "ga_brut_alt", "sharpe", "toplam_r",
            "ort_kazanc_r", "ort_kayip_r", "risk_pip")
    out = {kk: o.get(kk) for kk in keep}
    a = mk.alinan(x)
    if len(a) >= mk.ASGARI_BOOTSTRAP:
        rng = np.random.default_rng(int(ks.ONKAYIT["genel"].get("tohum", 7)))
        r = a["r"].to_numpy(np.float64)
        bs = np.array([r[rng.integers(0, len(r), len(r))].mean() for _ in range(int(ks.ONKAYIT["hukum"]["bootstrap_tekrar"]))])
        out["p_tek"] = float((bs <= 0).mean())
    return out


def _json(x):
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_json(v) for v in x]
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else round(float(x), 6)
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


def main(argv: list[str]) -> int:
    import veri as vr
    from gunluk import baglam_kur
    from takvim import olaylar_oku
    a = ay.oku()
    birimler = [x for x in argv if x in ks.BIRIMLER] or list(ks.BIRIMLER)
    # kural → aday → dönem → [parite parçaları]
    parca = {bi: {s: {"is": [], "oos": []} for s in ADAYLAR} for bi in birimler}
    ters = {bi: {s: [] for s in ADAYLAR} for bi in birimler}       # OOS (r_ayni, r_ters) parite parite
    gun_is, gun_oos = [], []
    parite = {bi: {} for bi in birimler}
    for cift in a.ciftler:
        t0 = time.monotonic()
        d = vr.oku(cift, a)
        b = baglam_kur(d, olaylar_oku(cift), tuple(a.haber_pencere_dk), orneklem=(a.baslangic, a.bitis))
        k_ = ks.Kosucu(b, a)
        gun_is.append(k_.gun_is)
        gun_oos.append(k_.gun_oos)
        ema = ema_onceki(b.g)
        print(f"{cift}: bağlam {time.monotonic() - t0:.0f} sn", flush=True)
        for bi in birimler:
            s = json.loads((ks.CIKTI / "sonuc" / bi / f"{cift}.json").read_text(encoding="utf-8"))
            p = s["varsayilan"]
            ad = ks._anahtar(p).replace("|", "__").replace("=", "-").replace(":", "")
            isl = pd.read_parquet(ks.CIKTI / "islem" / bi / f"{cift}__{ad}.parquet")
            # Kayıtlı varsayılan işlemleri ana koşunun yayımlanmış özetiyle eşleşmeli (girdi doğru dosya mı).
            ois, ooo = k_.bol(isl)
            o_kayit = s["varsayilan_analiz"]["oos"]
            o_ben = mk.ozet(ooo, k_.gun_oos, bootstrap=False)
            if o_ben["n"] != o_kayit["n"] or abs(o_ben["beklenti_r"] - o_kayit["beklenti_r"]) > 1e-5:
                raise AssertionError(f"{bi} {cift}: işlem dosyası yayımlanmış özetle eşleşmiyor")
            ms, med = maskeler(b, isl, ema)
            aile = ks.BIRIMLER[bi]["aile"]
            ofset = None if ks.BIRIMLER[bi].get("haber") else k_.sinyal(aile, p)[1]
            parite[bi][cift] = {"dar_medyan": med}
            for sz in ADAYLAR:
                if sz not in ms:
                    continue
                x = isl[ms[sz]].copy()
                x["cift"] = cift
                xi, xo = k_.bol(x)
                parca[bi][sz]["is"].append(xi)
                parca[bi][sz]["oos"].append(xo)
                po = mk.ozet(xo, k_.gun_oos, bootstrap=False)
                pi = mk.ozet(xi, k_.gun_is, bootstrap=False)
                parite[bi][cift][sz] = {"is": {kk: pi.get(kk) for kk in ("n", "isabet", "beklenti_r")},
                                        "oos": {kk: po.get(kk) for kk in ("n", "isabet", "beklenti_r")}}
                cf = sg._ayni_ters(b, xo, int(p["tf"]), ofset, ks.KAYMA_TEMEL, a.haber_kayma_pip)
                if cf is not None:
                    ters[bi][sz].append(cf)
            print(f"  {bi:14s} tamam", flush=True)
    # Dört paritenin işlem günlerinin birleşimi, kendi dtype'ıyla (günlük R serisi bu dizinle kurulur).
    gi = np.unique(np.concatenate(gun_is))
    go = np.unique(np.concatenate(gun_oos))
    sonuc = {"onkayit": "onkayit_suzgec.toml", "kural": {}}
    for bi in birimler:
        haber = bool(ks.BIRIMLER[bi].get("haber"))
        asg = int(OK["secim"]["asgari_islem_haber" if haber else "asgari_islem"])
        r = {"aday": {}, "parite": parite[bi]}
        for sz in ADAYLAR:
            if not parca[bi][sz]["is"]:
                continue
            h = {"is": havuz_ozet(parca[bi][sz]["is"], gi), "oos": havuz_ozet(parca[bi][sz]["oos"], go)}
            if ters[bi][sz]:
                ra = np.concatenate([c[0] for c in ters[bi][sz]])
                rt = np.concatenate([c[1] for c in ters[bi][sz]])
                h["rastgele_oos"] = sg._karisim(ra, rt, RASTGELE_TEKRAR, 11)["yuzdelik"] if len(ra) >= sg.ASGARI_RASTGELE else None
            else:
                h["rastgele_oos"] = None
            m = h["oos"]
            rr = m.get("beklenti_r")
            if not m.get("n"):
                hk = "olculemedi"
            elif rr is None or not np.isfinite(rr) or rr <= 0:
                hk = "calismiyor"
            elif (m.get("ga_alt") is not None and np.isfinite(m["ga_alt"]) and m["ga_alt"] > 0
                  and h["rastgele_oos"] is not None and h["rastgele_oos"] >= RASTGELE_ESIK):
                hk = "calisiyor"
            else:
                hk = "zayif"
            h["hukum"] = hk
            r["aday"][sz] = h
        uygun = [sz for sz in ADAYLAR if sz in r["aday"] and (r["aday"][sz]["is"].get("n") or 0) >= asg
                 and r["aday"][sz]["is"].get("sharpe") is not None and np.isfinite(r["aday"][sz]["is"]["sharpe"])]
        if uygun:
            en = max(r["aday"][sz]["is"]["sharpe"] for sz in uygun)
            r["secilen"] = next(sz for sz in uygun if r["aday"][sz]["is"]["sharpe"] >= en - 1e-9)
        else:
            r["secilen"] = None
        sonuc["kural"][bi] = r
    # Çoklu sınama (bilgi): 132 süzgeçli havuz, Benjamini–Hochberg
    satir = [(bi, sz, sonuc["kural"][bi]["aday"][sz]["oos"].get("p_tek")) for bi in birimler for sz in SUZGECLER
             if sz in sonuc["kural"][bi]["aday"] and sonuc["kural"][bi]["aday"][sz]["oos"].get("p_tek") is not None]
    ps = np.array([x[2] for x in satir])
    q = float(OK["coklu"]["bh_q"])
    if len(ps):
        sira = np.argsort(ps)
        esik = q * (np.arange(1, len(ps) + 1)) / len(ps)
        gecen = ps[sira] <= esik
        kmax = int(np.max(np.flatnonzero(gecen)) + 1) if gecen.any() else 0
        bh = [satir[i][:2] for i in sira[:kmax]]
    else:
        bh = []
    sonuc["coklu"] = {"sinama": len(satir), "alt_uc_arti": sum(1 for bi, sz, _ in satir
                                                               if (sonuc["kural"][bi]["aday"][sz]["oos"].get("ga_alt") or -1) > 0),
                      "sans_beklenen": round(0.025 * len(satir), 1), "bh_gecen": [list(x) for x in bh]}
    # Betimleme (hüküm değil): süzgeç başına, süzgeçsize göre net R ve kazanma oranı farkı; iki dönemde de iyileştiren
    # kural sayısı; örneklem içi farkın örneklem dışı farkla sıra ilintisi (iyileşme taşınıyor mu).
    ozet = {}
    for sz in SUZGECLER:
        f_is, f_oos, k_is, k_oos = [], [], [], []
        for bi in birimler:
            ad_ = sonuc["kural"][bi]["aday"]
            if sz not in ad_:
                continue
            y, x = ad_["yok"], ad_[sz]
            f_is.append(x["is"]["beklenti_r"] - y["is"]["beklenti_r"])
            f_oos.append(x["oos"]["beklenti_r"] - y["oos"]["beklenti_r"])
            k_is.append(x["is"]["isabet"] - y["is"]["isabet"])
            k_oos.append(x["oos"]["isabet"] - y["oos"]["isabet"])
        fi, fo = np.array(f_is), np.array(f_oos)
        ozet[sz] = {"kural": len(fi), "is_iyi": int((fi > 0).sum()), "oos_iyi": int((fo > 0).sum()),
                    "iki_iyi": int(((fi > 0) & (fo > 0)).sum()),
                    "oos_arti": sum(1 for bi in birimler if sz in sonuc["kural"][bi]["aday"]
                                    and sonuc["kural"][bi]["aday"][sz]["oos"]["beklenti_r"] > 0),
                    "fark_is_medyan": float(np.median(fi)), "fark_oos_medyan": float(np.median(fo)),
                    "isabet_fark_oos_medyan": float(np.median(k_oos)),
                    "sira_ilinti": float(pd.Series(fi).corr(pd.Series(fo), method="spearman")) if len(fi) > 2 else None}
    sonuc["ozet"] = ozet
    sec = [sonuc["kural"][bi]["secilen"] for bi in birimler]
    sonuc["secim_ozet"] = {"hukum": {h: sum(1 for bi in birimler if sonuc["kural"][bi]["secilen"]
                                            and sonuc["kural"][bi]["aday"][sonuc["kural"][bi]["secilen"]]["hukum"] == h)
                                     for h in ("calisiyor", "zayif", "calismiyor")},
                           "secilen": {s_: sec.count(s_) for s_ in set(sec)}}
    CIKTI.mkdir(parents=True, exist_ok=True)
    (CIKTI / "olcum.json").write_text(json.dumps(_json(sonuc), ensure_ascii=False, indent=1), encoding="utf-8")
    print("yazıldı:", CIKTI / "olcum.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
