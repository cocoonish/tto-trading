#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dokuzuncu dersin ölçüleri: kurallar neden kaybediyor ve hangi şartla kullanılabilirler.

Bütün ölçüler BETİMLEMEDİR. İki pencere de görüldükten sonra kuruldular (ilk sonuçların görüldüğü an künyede,
`onkayit_ilk_sonuc`) ve hiçbir hükmü değiştirmezler; hüküm yalnız önceden kayıtlı kuralla verilir. Koşu yapılmaz,
ham fiyat arşivi okunmaz. Girdi, koşu çıktısıdır (cikti/sonuc; cikti/islem'in varsayılan ve seçilen işlem dosyaları;
cikti/sonuc/haber) ve ölçümün kendi kayıtlarıdır (havuz, tatil betimlemesi, veri denetimi, ay sonu ailesi). İşlem
dosyasından kurulan her ölçü önce dosyanın sonuç özetini yeniden ürettiğini sınar (işlem sayısı, net ve brüt R);
ayrışırsa ölçüm yazılmaz.

Bölümler (anahtar → dersin bölümü):
  basabas   isabet, başabaş isabeti ve maliyetin iki etkisi; maliyetin pip dağılımı; tuzak payları ve kenarsız tabanı
  ayrisim   kaybın yön, zamanlama ve maliyet payları (ayna işlem: rastgele yön sınamasının ters yön ortalaması)
  olcek     R büyüklüğüne göre üçte birlikler; ızgarada yalnız hedefin, zaman diliminin ya da stop yerinin değiştiği gruplar
  kenar     maliyetten önceki sonuç: t dağılımı, güvenilirlik, kesit eğimi, sıra kalıcılığı, yıl hücreleri
  sans      kenarsız dünyada beklenen "zayıf" sayısı (Poisson-binom), seçimin örneklem dışına taşıdığı kazanç
  esik      başabaş gidiş-dönüş maliyeti c* = E[r_brüt] / E[1/R_pip], maliyet ölçeklemesi, tek kitapta netleşme
  haber     haberin fiyata girme hızı: ilk beş dakikanın yönüne göre ortalama patika
  ay_sonu   fiksing momentumunun ay sonu alt kümesi: parite × pencere, brüt iz, 28 biçimlik aile, büzülme, ölçek
  guc       ileriye dönük bir sınamanın gücü: gereken işlem sayısı, en küçük görülebilir etki, yıllık bakışlar
Her ölçünün tanımı fonksiyonunun kendisinde."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import metrik as mk

#: %95 iki yönlü aralığın z değeri.
Z95 = float(stats.norm.ppf(0.975))
#: Dersin pencereleri: örneklem içi, örneklem dışı ve bütün dönem.
PEN = ("is", "oos", "tum")
#: Üçte birlik ölçüsünün asgari işlem sayısı (bileşim başına, pencerede).
UCTE_BIR_ASGARI = 30
#: Izgara kıyaslarında grubun iki ucunda istenen asgari işlem sayısı.
IZGARA_ASGARI = 100
#: Ayrışımın asgari işlem sayısı: rastgele yön sınaması bunun altında kurulmaz (kosu.ASGARI_RASTGELE ile aynı).
AYNA_ASGARI = 20
#: Tuzak payları: kaybeden işlemin "lehine gitmiş" sayıldığı en iyi nokta ve "hedefe ulaşmış" sayıldığı seviye (R).
TUZAK_LEHINE = 0.5
TUZAK_ULASMA = 1.0
#: Yıl hücreleri: "çoğu yılda brütü artı" eşiği (dokuz yılın en az yedisi).
YIL_ESIK = 7
#: Kenarsız taban benzetimi: sürüklenmesiz rastgele yürüyüş, −1 R stop, ufukta çıkış.
TABAN_SIGMA = (1, 2, 3, 4)
TABAN_YOL = 20000
TABAN_ADIM = 500
TABAN_TOHUM = 20261017
#: Gerçek bir brüt kenarın örneklem dışı aralıkla sıfırdan ayrılma olasılığının sorulduğu büyüklük (R / işlem).
GUC_ORNEK_KENAR = 0.05
#: Güç hesabının düzeyi ve hedef gücü: tek yönlü %5, %80 güç.
GUC_ALFA = 0.05
GUC_HEDEF = 0.80
#: Kalın kuyruklu bir kuralda (Londra ORB) gereken işlem sayısının sorulduğu etki (R / işlem).
ORB_KENAR = 0.10
#: Yıllık bakışlı sıralı sınama: bakış sayısı, benzetim yolu ve tohumu.
BAKIS = 5
BAKIS_YOL = 200000
BAKIS_TOHUM = 20261017
#: Görülmemiş geçmişin (Şubat 2015 → Aralık 2017) ay sonu sayısı: WM/R penceresi 15.02.2015'te beş dakikaya geçti.
GECMIS_AY_SONU = 35
#: En küçük görülebilir etki tablosunun yılda işlem sayıları ve süreleri.
MDE_SIKLIK = (("ayda", 12), ("haftada", 52), ("gunde", 250))
MDE_YIL = (1, 3, 5, 10)
#: Güç eğrisinin net etki ızgarası (R / işlem).
GUC_EGRI_MU = tuple(round(0.05 + 0.025 * i, 3) for i in range(23))
#: Benjamini–Hochberg'in yanlış keşif oranı düzeyi (ay sonu ailesi).
BH_Q = 0.10
#: Fiksing momentumu: ay sonu alt kümesinin kuralı.
FM = "fiks_momentum"


def _f(x, hane: int = 6):
    """Düz Python sayısı ya da None (NaN, sonsuz)."""
    if x is None:
        return None
    x = float(x)
    return round(x, hane) if math.isfinite(x) else None


# ───────────────────────────────────────────── girdiler
def _sonuclar(kok: Path, birimler: dict) -> dict:
    """(birim, parite) → sonuç JSON'u, birimlerin sırasıyla."""
    import json
    out = {}
    for b, v in birimler.items():
        for c in v["cift"]:
            yol = kok / "sonuc" / b / f"{c}.json"
            out[(b, c)] = json.loads(yol.read_text(encoding="utf-8"))
    return out


def islemler(kok: Path, sonuclar: dict, islem_yolu, ic_bitis, hangi: str = "varsayilan") -> pd.DataFrame:
    """Bütün bileşimlerin alınan işlemleri (varsayılan ya da seçilen), pencere etiketiyle. Her bileşimde dosyanın
    sonuç özetini (işlem sayısı, net ve brüt R; üç pencere) yeniden ürettiği sınanır: ayrışırsa ValueError."""
    parca = []
    for (b, c), s in sonuclar.items():
        p = s.get(hangi)
        if p is None:
            continue
        x = mk.alinan(pd.read_parquet(islem_yolu(kok, b, c, p)))
        x = x[["gun", "r", "r_brut", "pnl_pip", "brut_pip", "R_pip", "mfe_r", "yon", "giris_t", "cikis_t"]].copy()
        icm = x["gun"].to_numpy().astype("datetime64[D]") <= np.datetime64(ic_bitis)
        x["pen"] = np.where(icm, "is", "oos")
        x["kural"] = b
        x["cift"] = c
        analiz = s["varsayilan_analiz" if hangi == "varsayilan" else "secilen_analiz"]
        for d in PEN:
            y = x if d == "tum" else x[x["pen"] == d]
            m = analiz[d]
            if len(y) != int(m["n"]) or (len(y) and (abs(y["r"].mean() - m["beklenti_r"]) > 1e-5
                                                    or abs(y["r_brut"].mean() - m["brut_r"]) > 1e-5)):
                raise ValueError(f"basarisiz: {b} {c} {hangi} {d}: işlem dosyası sonuç özetini üretmiyor")
        parca.append(x)
    return pd.concat(parca, ignore_index=True)


def _pencere(t: pd.DataFrame, d: str) -> pd.DataFrame:
    return t if d == "tum" else t[t["pen"] == d]


def izgara_tablosu(sonuclar: dict) -> pd.DataFrame:
    """Izgaranın bütün satırları (kopya ve boş kombinasyon işaretiyle): pencere başına n, net R, net pip, Sharpe,
    isabet ve parametreler (p_<ad>, dizgi)."""
    satir = []
    for (b, c), s in sonuclar.items():
        for iz in s["izgara"]:
            r = {"kural": b, "cift": c, "kopya": iz["kopya"] is not None, "bos": bool(iz["bos"])}
            for d in ("is", "oos"):
                x = iz.get(d) or {}
                for m in ("n", "beklenti_r", "beklenti_pip", "sharpe", "isabet"):
                    r[f"{d}_{m}"] = x.get(m)
            for k, v in iz["p"].items():
                r["p_" + k] = str(v)
            satir.append(r)
    return pd.DataFrame(satir)


# ───────────────────────────────────────────── başabaş
def _isabet(r: np.ndarray) -> tuple[float, float, float, float]:
    """İsabet (net sonucu artı işlemlerin payı; sıfır kayıptır), ortalama kazanç, ortalama kayıp ve başabaş isabeti
    p* = |L̄| / (W̄ + |L̄|). Özdeşlik: E = p·W̄ + (1 − p)·L̄ = (p − p*)·(W̄ + |L̄|)."""
    r = np.asarray(r, np.float64)
    w = r > 0
    p = float(w.mean())
    kaz = float(r[w].mean()) if w.any() else math.nan
    kay = float(r[~w].mean()) if (~w).any() else math.nan
    return p, kaz, kay, abs(kay) / (kaz + abs(kay))


def basabas(t: pd.DataFrame, birimler: dict, stop_cikis: dict) -> dict:
    """Kural (dört paritenin havuzu) ve bileşim başına isabet ile başabaş isabeti, net ve orta fiyattan (brüt).

    Maliyet başabaş isabetini iki yoldan iter: p*'ı yükseltir (Δp* = p*_net − p*_brüt; kazançlar küçülür, kayıplar
    büyür) ve isabeti düşürür (Δp = p_brüt − p_net; orta fiyatta kazanan bir işlem makastan sonra kaybedebilir).
    m/(W̄ + |L̄|) bu ikisinin yerine geçen tek sayı değildir: (p − p*) açığının maliyetle değişimine eşdeğer isabettir.
    Ayrıca: gidiş-dönüş maliyetinin pip dağılımı ve R karşılığının 1/R ile ilişkisi (2024 →); kaybedenlerin bir an
    lehine gitmiş olma payı ile +1 R'ye ulaşıp zararla kapananların payı ve aynı paylar kenarsız bir piyasada."""
    out: dict = {"havuz": {}, "ozet": {}, "bilesim": {}}
    for d in PEN:
        x = _pencere(t, d)
        satir = {}
        for b in birimler:
            y = x[x["kural"] == b]
            if not len(y):
                continue
            p, w, l, ps = _isabet(y["r"].to_numpy())
            pb, wb, lb, psb = _isabet(y["r_brut"].to_numpy())
            m = float((y["r_brut"] - y["r"]).mean())
            satir[b] = {"n": int(len(y)), "isabet": _f(p), "kazanc": _f(w), "kayip": _f(l), "pstar": _f(ps),
                        "acik": _f(p - ps), "net": _f(y["r"].mean()), "toplam": _f(w + abs(l)),
                        "brut": _f(y["r_brut"].mean()), "brut_isabet": _f(pb), "brut_kazanc": _f(wb),
                        "brut_kayip": _f(lb), "brut_pstar": _f(psb), "brut_acik": _f(pb - psb), "maliyet": _f(m),
                        "dpstar": _f(ps - psb), "dp": _f(pb - p), "acik_esdeger": _f(m / (w + abs(l))),
                        "R_medyan": _f(y["R_pip"].median(), 3),
                        "stopsuz": (birimler[b].get("varsayilan") or {}).get("stop_turu") == "yok"}
            if abs((p - ps) * (w + abs(l)) - y["r"].mean()) > 1e-9:
                raise ValueError(f"basarisiz: başabaş özdeşliği tutmuyor ({b} {d})")
        out["havuz"][d] = satir
        ac = np.array([v["acik"] for v in satir.values()])
        acb = np.array([v["brut_acik"] for v in satir.values()])
        en_kucuk = max(satir, key=lambda k: (satir[k]["acik"], k))
        en_buyuk = min(satir, key=lambda k: (satir[k]["acik"], k))
        out["ozet"][d] = {"kural": len(satir), "net_alti": int((ac < 0).sum()), "net_medyan": _f(np.median(ac)),
                          "brut_alti": int((acb < 0).sum()), "brut_medyan": _f(np.median(acb)),
                          "en_kucuk": en_kucuk, "en_buyuk": en_buyuk}
        alti = n = 0
        for _, y in x.groupby(["kural", "cift"], sort=False):
            if len(y) < 2:
                continue
            p, w, l, ps = _isabet(y["r"].to_numpy())
            n += 1
            alti += p < ps
        out["bilesim"][d] = {"n": n, "alti": int(alti)}
    x = _pencere(t, "oos")
    c_pip = (x["brut_pip"] - x["pnl_pip"]).to_numpy()
    c_r = (x["r_brut"] - x["r"]).to_numpy()
    ters = 1.0 / x["R_pip"].to_numpy()
    egim, kesisim = np.polyfit(ters, c_r, 1)
    out["maliyet_pip"] = {"n": int(len(x)), "medyan": _f(np.median(c_pip), 4), "p10": _f(np.quantile(c_pip, 0.1), 4),
                          "p90": _f(np.quantile(c_pip, 0.9), 4), "ort": _f(c_pip.mean(), 4),
                          "ilinti": _f(np.corrcoef(c_r, ters)[0, 1], 4), "egim": _f(egim, 4), "kesisim": _f(kesisim, 4),
                          "R_medyan": _f(np.median(x["R_pip"]), 3)}
    out["stop_cikis"] = stop_cikis
    tz = {}
    for b in birimler:
        y = x[x["kural"] == b]
        kay = y[y["r"] <= 0]
        ul = y[y["mfe_r"] >= TUZAK_ULASMA]
        tz[b] = {"kaybeden": int(len(kay)), "lehine": _f((kay["mfe_r"] >= TUZAK_LEHINE).mean()) if len(kay) else None,
                 "ulasan": int(len(ul)), "ulasip_zarar": _f((ul["r"] < 0).mean()) if len(ul) else None}
    a = [v["lehine"] for v in tz.values() if v["lehine"] is not None]
    u = [v["ulasip_zarar"] for v in tz.values() if v["ulasip_zarar"] is not None]
    out["tuzak"] = {"kural": tz, "lehine_medyan": _f(np.median(a)), "ulasip_zarar_medyan": _f(np.median(u)),
                    "esik": {"lehine": TUZAK_LEHINE, "ulasma": TUZAK_ULASMA}, "taban": kenarsiz_taban()}
    return out


def kenarsiz_taban(sigma=TABAN_SIGMA, yol: int = TABAN_YOL, adim: int = TABAN_ADIM, tohum: int = TABAN_TOHUM) -> dict:
    """Kenarsız bir piyasada tuzak payları: sürüklenmesiz rastgele yürüyüş (adım sayısı `adim`), −1 R'de sert stop,
    ufukta (σ√T, R cinsinden) çıkış. Kaybeden (sonuç ≤ 0) işlemlerin stoptan önce +0,5 R'ye değme payı ve +1 R'ye
    değen işlemlerin zararla kapanma payı. Sabit tohum; kural kural yapı (hedef, zaman çıkışı) farklıdır, taban yalnız
    büyüklüğü verir."""
    rng = np.random.default_rng(tohum)
    out = {"tohum": tohum, "yol": yol, "adim": adim, "sigma": []}
    for s in sigma:
        x = np.cumsum(rng.normal(0.0, s / math.sqrt(adim), size=(yol, adim)), axis=1)
        vurdu = x <= -1.0
        ilk = np.where(vurdu.any(axis=1), vurdu.argmax(axis=1), adim - 1)
        # stopa kadar (stop dakikası dahil) en yüksek değer
        maske = np.arange(adim)[None, :] <= ilk[:, None]
        maks = np.where(maske, x, -np.inf).max(axis=1)
        son = np.where(vurdu.any(axis=1), -1.0, x[:, -1])
        kay = son <= 0
        ul = maks >= TUZAK_ULASMA
        out["sigma"].append({"sigma": s, "lehine": _f((maks[kay] >= TUZAK_LEHINE).mean(), 4),
                             "ulasip_zarar": _f((son[ul] < 0).mean(), 4)})
    return out


# ───────────────────────────────────────────── kaybın ayrışımı
def ayrisim(sonuclar: dict, birimler: dict) -> dict:
    """Kaybın yön, zamanlama ve maliyet payları.

    Ayna işlem gerçek işlemle aynı giriş dakikasında TERS yönde açılır; stop ve hedef girişe aynı R uzaklığında, planlı
    çıkış aynı dakikadadır (rastgele yön sınamasının ters yön ortalaması). Ayrışım simetri VARSAYAR: yön payı y,
    zamanlama (iskelet) payı z ve maliyet c için net = y + z − c, ayna = −y + z − c. Buradan y = (net − ayna)/2 ve
    z = (net + ayna)/2 + c. Aynanın maliyeti gerçek işleminkine eşit sayılır; hedefli kurallarda gerçek işlemin stopu
    (piyasa emri) aynanın hedefine (limit) denk gelir, o asimetri z'ye karışır. c iki parçalıdır: ölçülmüş bid/ask
    makası (brüt − yalnız makas) ve modelin varsaydığı kayma (yalnız makas − net). Ayna yalnız örneklem dışında en az
    AYNA_ASGARI işlemi olan bileşimde kurulur. İç tutarlılık: rastgele yön dağılımının ortalaması (net + ayna)/2'dir."""
    out = {}
    for d in ("oos", "tum"):
        satir = []
        for (b, c), s in sonuclar.items():
            va = s["varsayilan_analiz"]
            m, ym, k0 = va[d], va["yalniz_makas"][d], va["maliyet"]["0.0"][d]
            rg = (va.get("rastgele") or {}).get(d) or {}
            satir.append({"kural": b, "cift": c, "n": int(m["n"]), "net": m["beklenti_r"], "brut": m["brut_r"],
                          "net_pip": m["beklenti_pip"], "brut_pip": m["brut_pip"], "makas": ym["beklenti_r"],
                          "makas_pip": ym["beklenti_pip"], "kayma0": k0["beklenti_r"], "ayna": rg.get("ters_ort"),
                          "rg_ort": rg.get("ort"), "yuzdelik": rg.get("yuzdelik")})
        D = pd.DataFrame(satir)
        D["c"] = D["brut"] - D["net"]
        D["c_makas"] = D["brut"] - D["makas"]
        D["c_kayma"] = D["c"] - D["c_makas"]
        D["c_pip"] = D["brut_pip"] - D["net_pip"]
        D["c_makas_pip"] = D["brut_pip"] - D["makas_pip"]
        D["c_kayma_pip"] = D["c_pip"] - D["c_makas_pip"]
        A = D[D["ayna"].notna()].copy()
        A["y"] = (A["net"] - A["ayna"]) / 2
        A["z"] = (A["net"] + A["ayna"]) / 2 + A["c"]
        kural = {}
        for b in birimler:
            x = A[A["kural"] == b]
            if not len(x):
                continue
            w = x["n"].to_numpy(np.float64)
            kural[b] = {k: _f(np.average(x[k], weights=w)) for k in ("y", "z", "c", "c_makas", "c_kayma", "net", "ayna")}
            kural[b]["n"] = int(w.sum())
            kural[b]["bilesim"] = int(len(x))
        out[d] = {"bilesim": int(len(A)), "dislanan": sorted(f"{r.kural}:{r.cift}" for r in D[D["ayna"].isna()].itertuples()),
                  "ort": {k: _f(A[k].mean()) for k in ("y", "z", "c", "c_makas", "c_kayma", "net", "brut",
                                                         "c_pip", "c_makas_pip", "c_kayma_pip")},
                  "medyan": {k: _f(A[k].median()) for k in ("y", "z", "c")},
                  "y_c": int((A["y"] > A["c"]).sum()), "yz_c": int((A["y"] + A["z"] > A["c"]).sum()),
                  "net_arti": int((A["net"] > 0).sum()), "ayna_eksi": int((A["ayna"] < 0).sum()),
                  "birlikte_eksi": int(((A["ayna"] < 0) & (A["net"] < 0)).sum()),
                  "ic_tutarlilik": _f((A["rg_ort"] - (A["net"] + A["ayna"]) / 2).abs().max()),
                  "kural": kural,
                  "duyarlilik": {"bilesim": int(len(D)), "temel": int((D["net"] > 0).sum()),
                                 "kayma0": int((D["kayma0"] > 0).sum()), "yalniz_makas": int((D["makas"] > 0).sum()),
                                 "yalniz_makas_parite": {c: int(((D["cift"] == c) & (D["makas"] > 0)).sum())
                                                         for c in dict.fromkeys(D["cift"])},
                                 "kayma_payi": _f(D["c_kayma"].mean() / D["c"].mean())}}
        if (A["y"] + A["z"] - A["c"] - A["net"]).abs().max() > 1e-12:
            raise ValueError("basarisiz: ayrışım özdeşliği tutmuyor")
    return out


# ───────────────────────────────────────────── ölçek
def _izgara_fark(G: pd.DataFrame, ad: str, a: str, b: str) -> dict:
    """Izgarada yalnız `ad` parametresi a'dan b'ye değişen (öbür parametreleri aynı) kombinasyon çiftlerinde net R ve
    net pip farkı; iki uçta da pencerede en az IZGARA_ASGARI işlem. Kopya satırlar sayılmaz."""
    U = G[~G["kopya"]]
    pcol = [k for k in U.columns if k.startswith("p_")]
    obur = [k for k in pcol if k != "p_" + ad]
    out = {}
    for d in ("is", "oos"):
        fr, fp = [], []
        for _, x in U.groupby(["kural", "cift"], sort=False):
            if ("p_" + ad) not in x or x["p_" + ad].isna().all():
                continue
            anahtar = x[obur].fillna("—").astype(str).agg("|".join, axis=1)
            for _, y in x.assign(_a=anahtar).groupby("_a", sort=False):
                ya, yb = y[y["p_" + ad] == a], y[y["p_" + ad] == b]
                if len(ya) != 1 or len(yb) != 1:
                    continue
                if (ya[f"{d}_n"].iloc[0] or 0) < IZGARA_ASGARI or (yb[f"{d}_n"].iloc[0] or 0) < IZGARA_ASGARI:
                    continue
                fr.append(yb[f"{d}_beklenti_r"].iloc[0] - ya[f"{d}_beklenti_r"].iloc[0])
                fp.append(yb[f"{d}_beklenti_pip"].iloc[0] - ya[f"{d}_beklenti_pip"].iloc[0])
        fr, fp = np.array(fr), np.array(fp)
        out[d] = {"grup": int(len(fr)), "r_arti": _f((fr > 0).mean()), "r_medyan": _f(np.median(fr)),
                  "pip_arti": _f((fp > 0).mean()), "pip_medyan": _f(np.median(fp))} if len(fr) else {"grup": 0}
    return out


def olcek(t: pd.DataFrame, G: pd.DataFrame) -> dict:
    """Maliyetin R cinsinden payı: c_R = c_pip / R_pip.

    (a) Her bileşimin işlemleri kendi içinde R_pip SIRASINA göre üçe bölünür (rank, ilk gelen önce; bileşimde
    pencerede en az UCTE_BIR_ASGARI işlem): dilim başına net, brüt ve maliyet (R ve pip) ve medyan R; bileşimlerin
    medyanı ve geniş − dar farkının işaret sayımı. Dilim sınırları değerlendirilen pencerenin kendi işlemlerinden alınır:
    bir süzgeç değildir. (b) Izgarada yalnız hedef türünün, yalnız zaman diliminin (5 → 60 dk) ya da yalnız stop yerinin
    (aralığın ortası → karşı ucu) değiştiği gruplar. (c) Bütün kopyasız ızgara satırlarında zaman dilimine göre medyan
    net R."""
    out: dict = {"ucte_bir": {}}
    t = t.assign(cR=t["r_brut"] - t["r"], cpip=t["brut_pip"] - t["pnl_pip"])
    for d in ("oos", "tum"):
        x = _pencere(t, d)
        satir = []
        for _, y in x.groupby(["kural", "cift"], sort=False):
            if len(y) < UCTE_BIR_ASGARI:
                continue
            q = pd.qcut(y["R_pip"].rank(method="first"), 3, labels=False)
            g = y.groupby(q).agg(net=("r", "mean"), brut=("r_brut", "mean"), maliyet=("cR", "mean"),
                                 maliyet_pip=("cpip", "mean"), R=("R_pip", "median"))
            satir.append({f"{k}{i}": g.loc[i, k] for i in range(3) for k in g.columns})
        D = pd.DataFrame(satir)
        out["ucte_bir"][d] = {"bilesim": int(len(D)), "asgari": UCTE_BIR_ASGARI,
                              **{k: [_f(D[f"{k}{i}"].median()) for i in range(3)]
                                 for k in ("net", "brut", "maliyet", "maliyet_pip", "R")},
                              "genis_dar_net": int((D["net2"] > D["net0"]).sum()),
                              "genis_dar_brut": int((D["brut2"] > D["brut0"]).sum()),
                              "genis_dar_maliyet": int((D["maliyet2"] > D["maliyet0"]).sum())}
    out["tf_5_60"] = _izgara_fark(G, "tf", "5", "60")
    out["stop_orta_karsi"] = _izgara_fark(G, "stop_yeri", "orta", "karsi_uc")
    U = G[~G["kopya"]]
    pcol = [k for k in U.columns if k.startswith("p_")]
    obur = [k for k in pcol if k != "p_hedef"]
    hed = {}
    for d in ("is", "oos"):
        ia, ra = [], []
        for _, x in U.groupby(["kural", "cift"], sort=False):
            if "p_hedef" not in x or x["p_hedef"].isna().all():
                continue
            anahtar = x[obur].fillna("—").astype(str).agg("|".join, axis=1)
            for _, y in x.assign(_a=anahtar).groupby("_a", sort=False):
                yy = y[y[f"{d}_n"].fillna(0) >= IZGARA_ASGARI]
                if yy["p_hedef"].nunique() < 2:
                    continue
                ia.append(yy[f"{d}_isabet"].max() - yy[f"{d}_isabet"].min())
                ra.append(yy[f"{d}_beklenti_r"].max() - yy[f"{d}_beklenti_r"].min())
        hed[d] = {"grup": int(len(ia)), "isabet_aralik": _f(np.median(ia)), "r_aralik": _f(np.median(ra)),
                  "r_aralik_p90": _f(np.quantile(ra, 0.9))}
    out["hedef"] = hed
    x = U[(U["kural"] == "orb") & (U["cift"] == "EURUSD") & (~U["bos"])]
    out["orb_eurusd_hedef"] = {h: {"kombinasyon": int(len(y)), "isabet": _f(y["is_isabet"].mean()),
                                   "net": _f(y["is_beklenti_r"].mean())} for h, y in x.groupby("p_hedef")}
    V = U[~U["bos"]]
    out["tf_medyan"] = {d: {str(k): _f(v) for k, v in V.groupby("p_tf")[f"{d}_beklenti_r"].median().items()}
                        for d in ("is", "oos")}
    out["izgara_satir"] = int(len(V))
    out["izgara_asgari"] = IZGARA_ASGARI
    return out


# ───────────────────────────────────────────── kenar
def _guvenilirlik(ort: pd.Series, se: pd.Series) -> float:
    """Bileşimler arası yayılımın sinyal payı: ρ = (Var(x̂) − ort SE²) / Var(x̂). Negatif tahmin sıfıra kırpılmaz;
    kırpma metinde söylenir."""
    v = float(ort.var(ddof=1))
    return (v - float((se ** 2).mean())) / v


def kenar(t: pd.DataFrame, birimler: dict, sonuclar: dict) -> dict:
    """Maliyetten önce bir kenar var mıydı ve örneklemden örnekleme ne taşındı.

    Bileşim başına brüt ortalama R'nin t istatistiği (pencere başına; kenarsız bir dünyada yaklaşık N(0, 1)),
    güvenilirlik, örneklem içinden dışına kesit eğimi (en küçük kareler ve Theil–Sen), Spearman sıra korelasyonları
    (kural havuzu ve bileşim; net, maliyet, brüt, isabet; yıldan yıla), havuzun net varyansının brüt ve maliyet
    paylarına ayrışması (kovaryans eşit bölünür), yıl hücrelerinin işaret dağılımı ve önceden kayıtlı bootstrap'le brüt
    aralığı sıfırın üstünde kalan bileşimler. Eğim ve güvenilirlik örneklem dışında en az AYNA_ASGARI işlemi olan
    bileşimlerde (dışarıda kalanlar adıyla); 88 bileşimdeki değer duyarlılık olarak yanında. Bileşimler aynı günleri
    paylaşır; p değerleri bilgi içindir."""
    g = {}
    out: dict = {}
    for d in PEN:
        x = _pencere(t, d)
        a = x.groupby(["kural", "cift"], sort=False).agg(n=("r_brut", "size"), brut=("r_brut", "mean"),
                                                        brut_sd=("r_brut", "std"), net=("r", "mean"))
        a["isabet"] = x.assign(_k=x["r"] > 0).groupby(["kural", "cift"], sort=False)["_k"].mean()
        a["maliyet"] = a["brut"] - a["net"]
        a["se"] = a["brut_sd"] / np.sqrt(a["n"])
        a["t"] = a["brut"] / a["se"]
        g[d] = a
        arti = int((a["brut"] > 0).sum())
        out[f"t_{d}"] = {"bilesim": int(len(a)), "ort": _f(a["t"].mean()), "sd": _f(a["t"].std()),
                         "mutlak_196": int((a["t"].abs() > 1.96).sum()), "arti_196": int((a["t"] > 1.96).sum()),
                         "sans_mutlak": _f(len(a) * 2 * stats.norm.sf(1.96), 2),
                         "sans_arti": _f(len(a) * stats.norm.sf(1.96), 2),
                         "brut_arti": arti, "binom_p": _f(stats.binomtest(arti, len(a), 0.5).pvalue)}
    j = g["is"].join(g["oos"], lsuffix="_is", rsuffix="_oos")
    kucuk = j["n_oos"] < AYNA_ASGARI
    jj = j[~kucuk]
    ts = stats.theilslopes(jj["brut_oos"], jj["brut_is"])
    pr = stats.pearsonr(jj["brut_is"], jj["brut_oos"])
    out["dislanan"] = sorted(f"{b}:{c}" for b, c in j.index[kucuk])
    out["guvenilirlik"] = {"is": _f(_guvenilirlik(jj["brut_is"], jj["se_is"])),
                           "oos": _f(_guvenilirlik(jj["brut_oos"], jj["se_oos"])),
                           "is_hepsi": _f(_guvenilirlik(j["brut_is"], j["se_is"])),
                           "oos_hepsi": _f(_guvenilirlik(j["brut_oos"], j["se_oos"]))}
    out["egim"] = {"bilesim": int(len(jj)), "brut": _f(np.polyfit(jj["brut_is"], jj["brut_oos"], 1)[0]),
                   "brut_hepsi": _f(np.polyfit(j["brut_is"], j["brut_oos"], 1)[0]),
                   "pearson": _f(pr[0]), "pearson_p": _f(pr[1]),
                   "theil_sen": _f(ts[0]), "theil_sen_alt": _f(ts[2]), "theil_sen_ust": _f(ts[3]),
                   "maliyet": _f(np.polyfit(jj["maliyet_is"], jj["maliyet_oos"], 1)[0]),
                   "net": _f(np.polyfit(jj["net_is"], jj["net_oos"], 1)[0])}
    # kural havuzu (ölçümün havuz kayıtlarından)
    hv = pd.DataFrame({b: {f"{k}_{d}": (v["havuz"]["varsayilan"][d] or {}).get(alan)
                           for d in PEN for k, alan in (("net", "beklenti_r"), ("brut", "brut_r"))}
                       for b, v in birimler.items()}).T.astype(float)
    for d in PEN:
        hv[f"maliyet_{d}"] = hv[f"brut_{d}"] - hv[f"net_{d}"]
    out["sira_havuz"] = {}
    for ad in ("net", "maliyet", "brut"):
        r = stats.spearmanr(hv[f"{ad}_is"], hv[f"{ad}_oos"])
        out["sira_havuz"][ad] = {"rho": _f(r[0]), "p": _f(r[1])}
    out["sira_bilesim"] = {ad: _f(stats.spearmanr(j[f"{ad}_is"], j[f"{ad}_oos"])[0])
                           for ad in ("net", "maliyet", "brut", "isabet")}
    y = t.assign(yil=t["gun"].dt.year).groupby(["kural", "cift", "yil"], sort=False).agg(
        net=("r", "mean"), brut=("r_brut", "mean"))
    y["maliyet"] = y["brut"] - y["net"]
    yillar = sorted(t["gun"].dt.year.unique().tolist())
    out["sira_yil"] = {}
    for ad in ("net", "maliyet", "brut"):
        P = y[ad].unstack()
        rr = [stats.spearmanr(P[a], P[b], nan_policy="omit")[0] for a, b in zip(yillar[:-1], yillar[1:])]
        out["sira_yil"][ad] = {"medyan": _f(np.median(rr)), "cift": len(rr)}
    out["varyans"] = {}
    for d in ("oos", "tum"):
        n_, b_, c_ = hv[f"net_{d}"].astype(float), hv[f"brut_{d}"].astype(float), hv[f"maliyet_{d}"].astype(float)
        kov = float(np.cov(b_, c_)[0, 1])
        vn = float(n_.var(ddof=1))
        out["varyans"][d] = {"maliyet": _f((c_.var(ddof=1) - kov) / vn), "brut": _f((b_.var(ddof=1) - kov) / vn)}
    Pn, Pb = y["net"].unstack(), y["brut"].unstack()
    hucre = int(Pn.notna().sum().sum())
    pay_b = float((Pb > 0).sum().sum() / Pb.notna().sum().sum())
    k = len(yillar)
    out["yil"] = {"hucre": hucre, "yil": k, "ilk": int(yillar[0]), "son": int(yillar[-1]),
                  "net_arti": _f((Pn > 0).sum().sum() / hucre), "hic_arti": int(((Pn > 0).sum(axis=1) == 0).sum()),
                  "en_cok_arti": int((Pn > 0).sum(axis=1).max()), "brut_arti": _f(pay_b),
                  "esik": YIL_ESIK, "brut_yedi": int(((Pb > 0).sum(axis=1) >= YIL_ESIK).sum()),
                  "beklenen_yari": _f(len(Pb) * stats.binom.sf(YIL_ESIK - 1, k, 0.5)),
                  "beklenen_gozlenen": _f(len(Pb) * stats.binom.sf(YIL_ESIK - 1, k, pay_b))}
    say = {}
    for d in ("oos", "tum"):
        arti = eksi = 0
        for s in sonuclar.values():
            m = s["varsayilan_analiz"][d]
            if m.get("ga_brut_alt") is not None and m["ga_brut_alt"] > 0:
                arti += 1
                eksi += m["beklenti_r"] < 0
        say[d] = {"brut_alt_arti": arti, "net_eksi": int(eksi), "sans": _f(len(sonuclar) * 0.025)}
    out["brut_aralik"] = say
    out["guc_ornek"] = {"kenar": GUC_ORNEK_KENAR,
                        "olasilik": _f(stats.norm.cdf(GUC_ORNEK_KENAR / jj["se_oos"] - Z95).mean())}
    sec = j[j["t_is"] > 1.96]
    mu = float(jj["brut_is"].mean())
    rho = _guvenilirlik(jj["brut_is"], jj["se_is"])
    ongoru = mu + rho * (float(sec["brut_is"].mean()) - mu)
    oos_se = math.sqrt(float((sec["se_oos"] ** 2).mean()) / len(sec))
    out["is_anlamli"] = {"bilesim": int(len(sec)), "is": _f(sec["brut_is"].mean()), "oos": _f(sec["brut_oos"].mean()),
                         "kuculme": _f(1 - sec["brut_oos"].mean() / sec["brut_is"].mean()),
                         "isaret": int((sec["brut_oos"] > 0).sum()), "net_arti": int((sec["net_oos"] > 0).sum()),
                         "mu_is": _f(mu), "rho_is": _f(rho), "ongoru": _f(ongoru), "oos_se": _f(oos_se),
                         "ongoru_z": _f((float(sec["brut_oos"].mean()) - ongoru) / oos_se),
                         "dislanan": int(sum(kucuk[sec.index]))}
    out["nokta"] = [{"kural": b, "cift": c, "brut_is": _f(r.brut_is), "brut_oos": _f(r.brut_oos),
                     "maliyet_is": _f(r.maliyet_is), "maliyet_oos": _f(r.maliyet_oos), "t_is": _f(r.t_is),
                     "n_oos": int(r.n_oos), "dislanan": bool(r.n_oos < AYNA_ASGARI)}
                    for (b, c), r in j.iterrows()]
    return out


def tek_gun(t: pd.DataFrame, birim: str, birimler: dict) -> dict:
    """Bir kuralın örneklem dışı havuzunu en çok taşıyan gün: o günün işlemleri, gün çıkınca havuzun net R'si ve
    kuralın 22 kural içindeki sırası (büyükten küçüğe)."""
    x = _pencere(t, "oos")
    y = x[x["kural"] == birim]
    gun = y.groupby("gun")["r"].sum().sort_values(ascending=False)
    g0 = gun.index[0]
    haric = float(y[y["gun"] != g0]["r"].mean())
    obur = {b: float(x[x["kural"] == b]["r"].mean()) for b in birimler if b != birim}
    sira = 1 + sum(v > haric for v in obur.values())
    sira0 = 1 + sum(v > float(y["r"].mean()) for v in obur.values())
    return {"birim": birim, "gun": pd.Timestamp(g0).date().isoformat(), "n": int(len(y)),
            "islem": [{"cift": r.cift, "r": _f(r.r)} for r in y[y["gun"] == g0].sort_values("r", ascending=False).itertuples()],
            "net": _f(y["r"].mean()), "haric": _f(haric), "sira": sira0, "sira_haric": sira, "kural": len(obur) + 1}


# ───────────────────────────────────────────── şans ve seçim
def _poisson_binom(p: np.ndarray) -> np.ndarray:
    d = np.array([1.0])
    for q in p:
        d = np.convolve(d, [1.0 - q, q])
    return d


def _sans_tabani(x: pd.DataFrame) -> dict:
    """Brüt kenar SIFIRKEN bir bileşimin örneklem dışı net ortalamasının artı çıkma olasılığı p_i = Φ(−c_i/se_i)
    (c_i ölçülen maliyet, se_i = sd(r)/√n); artı sayısı Poisson-binom dağılır (bileşimler bağımsız sayılır: beklenen
    sayı bağımlılıkla değişmez, dağılım genişler)."""
    o = _pencere(x, "oos").groupby(["kural", "cift"]).agg(n=("r", "size"), net=("r", "mean"), sd=("r", "std"),
                                                          brut=("r_brut", "mean"))
    i = _pencere(x, "is").groupby(["kural", "cift"]).agg(brut_is=("r_brut", "mean"))
    o = o.join(i)
    o = o[o["n"] >= 2]
    c = o["brut"] - o["net"]
    se = o["sd"] / np.sqrt(o["n"])
    p = stats.norm.cdf(-c / se)
    d = _poisson_binom(np.asarray(p))
    gozlenen = int((o["net"] > 0).sum())
    sd = math.sqrt(float((p * (1 - p)).sum()))
    z = (gozlenen - 0.5 - float(p.sum())) / sd          # süreklilik düzeltmesiyle normal yaklaşım (alıştırmanın yolu)
    return {"bilesim": int(len(o)), "beklenen": _f(p.sum()), "sd": _f(sd), "z": _f(z), "p_normal": _f(stats.norm.sf(z)),
            "gozlenen": gozlenen, "p_ustu": _f(d[gozlenen:].sum()),
            "calisiyor_ust": _f(stats.norm.cdf(-c / se - Z95).sum()),
            "is_surseydi": _f(stats.norm.cdf((o["brut_is"] - c) / se).sum()),
            "dagilim": [_f(v) for v in d[: min(len(d), 31)]]}


def sans(t: pd.DataFrame, ts: pd.DataFrame, G: pd.DataFrame, sonuclar: dict, birimler: dict, tatil: dict) -> dict:
    """Şans, seçim ve süzgeç.

    Varsayılan ve örneklem içinde seçilen kombinasyon için kenarsız dünyanın "zayıf" tabanı (_sans_tabani). Seçimin
    taşıdığı kazanç: seçilen ile varsayılanın farkı (yalnız ikisi ayrı olan bileşimler), brüt ve maliyet tasarrufu
    olarak, ortalamalarla. Seçilenin ızgara içindeki örneklem dışı yeri (Sharpe yüzdeliği; kopyasız satırlar) ve
    ızgaranın içinde örneklem içi–dışı Sharpe sıra ilintisi. Geriye dönük en iyi örneklem dışı satır (görülmüş pencerede
    yapılmış bir seçim: yalnız sınır). Yerel tatil günlerini dışlamanın aritmetiği (ölçümün tatil betimlemesinden)."""
    out = {"varsayilan": _sans_tabani(t), "secilen": _sans_tabani(ts)}

    def topla(x):
        a = x.groupby(["kural", "cift", "pen"]).agg(net=("r", "mean"), brut=("r_brut", "mean"), R=("R_pip", "median"))
        a["maliyet"] = a["brut"] - a["net"]
        return a
    j = topla(t).join(topla(ts), lsuffix="_v", rsuffix="_s", how="inner").reset_index()
    ayni = {k: s.get("secilen") == s.get("varsayilan") for k, s in sonuclar.items()}
    j = j[[not ayni[(b, c)] for b, c in zip(j["kural"], j["cift"])]]
    out["kazanc"] = {}
    for d in ("is", "oos"):
        x = j[j["pen"] == d]
        out["kazanc"][d] = {"bilesim": int(len(x)), "net": _f((x["net_s"] - x["net_v"]).mean()),
                            "brut": _f((x["brut_s"] - x["brut_v"]).mean()),
                            "tasarruf": _f((x["maliyet_v"] - x["maliyet_s"]).mean()),
                            "ucuz": _f((x["maliyet_s"] < x["maliyet_v"]).mean()),
                            "R_orani": _f((x["R_s"] / x["R_v"]).median())}
    yer = []
    for (b, c), s in sonuclar.items():
        sec = s.get("secilen")
        if sec is None:
            continue
        x = G[(G["kural"] == b) & (G["cift"] == c) & (~G["bos"])]
        m = np.ones(len(x), bool)
        for k, v in sec.items():
            m &= (x["p_" + k].astype(str) == str(v)).to_numpy()
        if m.sum() != 1:
            raise ValueError(f"basarisiz: seçilen kombinasyon ızgarada bulunamadı ({b} {c})")
        satir = x[m].iloc[0]
        u = x[~x["kopya"]]
        pct = 100.0 * float((u["oos_sharpe"] < satir["oos_sharpe"]).mean()) \
            + 50.0 * float((u["oos_sharpe"] == satir["oos_sharpe"]).mean())
        sa = s["secilen_analiz"]
        yer.append({"pct": pct, "rho": stats.spearmanr(u["is_sharpe"], u["oos_sharpe"], nan_policy="omit")[0],
                    "is_sh": sa["is"]["sharpe"], "oos_sh": sa["oos"]["sharpe"], "oos_r": sa["oos"]["beklenti_r"],
                    "dsr": (sa.get("dsr") or {}).get("dsr")})
    Y = pd.DataFrame(yer)
    out["secilen_yeri"] = {"secim": int(len(Y)), "yuzdelik": _f(Y["pct"].median()), "ust_yari": int((Y["pct"] > 50).sum()),
                           "izgara_sira": _f(Y["rho"].median()), "is_sharpe": _f(Y["is_sh"].median()),
                           "oos_sharpe": _f(Y["oos_sh"].median()), "oos_arti": int((Y["oos_r"] > 0).sum()),
                           "dsr_gecen": int((Y["dsr"] >= 0.95).sum()), "dsr_azami": _f(Y["dsr"].max())}
    out["yuruyen_arti"] = int(sum(((s.get("walk_forward") or {}).get("ozet") or {}).get("beklenti_r", -1) > 0
                                  for s in sonuclar.values()))
    U = G[~G["kopya"] & ~G["bos"]]
    en = U.groupby(["kural", "cift"])["oos_beklenti_r"].max()
    en_is = U.groupby(["kural", "cift"])["is_sharpe"].max()
    out["geriye_donuk"] = {"bilesim": int(len(en)), "arti": int((en > 0).sum()), "medyan": _f(en.median()),
                           "satir": int(len(U)), "satir_arti": int((U["oos_beklenti_r"] > 0).sum()),
                           "is_en_iyi_eksi": int((en_is <= 0).sum())}
    tt = []
    for b in birimler:
        hv = birimler[b]["havuz"]["varsayilan"]["tum"]
        dg = tatil["birim"][b]["diger"]["tum"]
        tt.append({"kural": b, "dis": 1 - dg["n"] / hv["n"], "fark": dg["r"] - hv["beklenti_r"],
                   "doner": hv["beklenti_r"] <= 0 < dg["r"]})
    tt = pd.DataFrame(tt)
    i = int(tt["fark"].idxmax())
    out["tatil"] = {"dislanan": _f(tt["dis"].median()), "en_cok": _f(tt.loc[i, "fark"]), "en_cok_kural": tt.loc[i, "kural"],
                    "medyan": _f(tt["fark"].median()), "donen": int(tt["doner"].sum())}
    return out


# ───────────────────────────────────────────── maliyet eşiği
def esik(t: pd.DataFrame, birimler: dict, sonuclar: dict, kalite: dict) -> dict:
    """Başabaş gidiş-dönüş maliyeti: maliyet λ katıyla ölçeklenirse net(λ) = brüt − λc; pip cinsinden işlem başına sabit
    bir maliyette başabaş c* = E[r_brüt] / E[1/R_pip] (ilk mertebe: maliyet değişince işlemler aynı kalır). Aralık,
    havuzun gün kümeli brüt aralığının uçlarından (E[1/R_pip] sabit sayılır). Ödenen maliyet ort(brüt pip − net pip).
    Bileşim düzeyinde maliyet λ ile ölçeklenseydi net artı kalan bileşim sayısı. Merdivenle tutarlılık (Londra ORB
    EUR/USD): makasın pip maliyeti + 2 × başabaş kayma. Aynı paritede bütün kuralların işlemleri tek kitapta netleşseydi
    işlem hacminin azalması (eşit nominal ve R ölçekli: her işlem 1 R) ve kitabın kendi gereksinimi (brüt/maliyet)."""
    out: dict = {"havuz": {}}
    for d in ("oos", "tum"):
        x = _pencere(t, d)
        satir = {}
        for b in birimler:
            y = x[x["kural"] == b]
            ters = float((1.0 / y["R_pip"]).mean())
            h = birimler[b]["havuz"]["varsayilan"][d]
            satir[b] = {"n": int(len(y)), "cstar": _f(y["r_brut"].mean() / ters), "alt": _f(h["ga_brut_alt"] / ters),
                        "ust": _f(h["ga_brut_ust"] / ters), "odenen": _f((y["brut_pip"] - y["pnl_pip"]).mean())}
        out["havuz"][d] = satir
    out["ozet"] = {d: {"sifir_alti": sorted(b for b, v in out["havuz"][d].items() if v["cstar"] is not None and v["cstar"] <= 0),
                       "alt_arti": sorted(b for b, v in out["havuz"][d].items() if v["alt"] is not None and v["alt"] > 0),
                       "ustu": sorted(b for b, v in out["havuz"][d].items()
                                      if v["cstar"] is not None and v["cstar"] > v["odenen"]),
                       "odenen_alt": _f(min(v["odenen"] for v in out["havuz"][d].values())),
                       "odenen_ust": _f(max(v["odenen"] for v in out["havuz"][d].values()))}
                   for d in ("oos", "tum")}
    for d in ("oos", "tum"):
        for k in ("sifir_alti", "alt_arti", "ustu"):
            out["ozet"][d][k + "_n"] = len(out["ozet"][d][k])
    out["lambda"] = {}
    for d in ("oos", "tum"):
        br = np.array([s["varsayilan_analiz"][d]["brut_r"] for s in sonuclar.values()])
        net = np.array([s["varsayilan_analiz"][d]["beklenti_r"] for s in sonuclar.values()])
        c = br - net
        arti = br > 0
        out["lambda"][d] = {"kat": {str(k): int((br - k * c > 0).sum()) for k in (1.0, 0.75, 0.5, 0.25, 0.1, 0.0)},
                            "oran": _f(np.median(br[arti] / c[arti])), "brut_arti": int(arti.sum())}
    s = sonuclar[("orb", "EURUSD")]["varsayilan_analiz"]
    y = _pencere(t, "oos")
    y = y[(y["kural"] == "orb") & (y["cift"] == "EURUSD")]
    mak = s["oos"]["brut_pip"] - s["yalniz_makas"]["oos"]["beklenti_pip"]
    out["merdiven"] = {"cstar": _f(y["r_brut"].mean() / (1.0 / y["R_pip"]).mean()), "makas": _f(mak),
                       "kayma": _f(s["basabas_kayma_pip_oos"]), "toplam": _f(mak + 2 * s["basabas_kayma_pip_oos"])}
    out["makas"] = {c: kalite[c]["makas"]["medyan_pip"] for c in kalite}
    out["netlesme"] = {}
    for d in ("oos", "tum"):
        x = _pencere(t, d)
        r_ = {}
        for agirlik in ("esit", "R"):
            tek = net = 0.0
            parite = {}
            for c in dict.fromkeys(x["cift"]):
                y = x[x["cift"] == c]
                w = 1.0 if agirlik == "esit" else 1.0 / y["R_pip"].clip(lower=0.5)
                q = (y["yon"].astype(float) * w).to_numpy()
                ev = pd.DataFrame({"t": np.concatenate([y["giris_t"].to_numpy(), y["cikis_t"].to_numpy()]),
                                   "dq": np.concatenate([q, -q])})
                a_, b_ = float(np.abs(ev["dq"]).sum()), float(ev.groupby("t")["dq"].sum().abs().sum())
                parite[c] = _f(1 - b_ / a_)
                tek += a_
                net += b_
            r_[agirlik] = {"tasarruf": _f(1 - net / tek), "parite": parite}
        r_["kitap_oran"] = _f(x["r_brut"].sum() / (x["r_brut"] - x["r"]).sum())
        r_["kitap_gereken"] = _f(1 - r_["kitap_oran"])
        out["netlesme"][d] = r_
    return out


# ───────────────────────────────────────────── haber patikası
def haber(haber_cift: dict) -> dict:
    """Haberin fiyata girme hızı: ilk beş dakikanın yönüne göre ortalama patika (gün ATR'si cinsinden; haber dersinin
    patikası). Yön simetrisi için yukarı ve aşağı kollarının farkının yarısı; 0 → 5 dakika hareketi tanım gereği artıdır,
    bilgi 5 → 15 ve 5 → 60 dakika devamındadır. Pariteler olay–parite sayısıyla ağırlıklı; parite aralığı yanında."""
    top: dict = {}
    for c, j in haber_cift.items():
        for olay, v in (j.get("patika") or {}).items():
            tau = v["tau"]

            def an(dk):
                i = tau.index(dk)
                return (v["yukari"]["ort"][i] - v["asagi"]["ort"][i]) / 2
            n = v["yukari"]["n"] + v["asagi"]["n"]
            top.setdefault(olay, []).append((c, n, an(5), an(15) - an(5), an(60) - an(5)))
    out = {}
    for olay, L in top.items():
        w = [x[1] for x in L]
        out[olay] = {"n": int(sum(w)), "parite": len(L), "h5": _f(np.average([x[2] for x in L], weights=w)),
                     "d15": _f(np.average([x[3] for x in L], weights=w)),
                     "d60": _f(np.average([x[4] for x in L], weights=w)),
                     "d60_alt": _f(min(x[4] for x in L)), "d60_ust": _f(max(x[4] for x in L))}
    return out


# ───────────────────────────────────────────── ay sonu
def _ay_ozeti(x: pd.DataFrame) -> dict:
    r = x["r"].to_numpy(np.float64)
    n = len(r)
    if n < 2:
        return {"n": n}
    alt, ust = mk.bootstrap_ort(r)
    return {"n": n, "net": _f(r.mean()), "alt": _f(alt), "ust": _f(ust), "brut": _f(x["r_brut"].mean()),
            "maliyet": _f((x["r_brut"] - x["r"]).mean()), "net_pip": _f(x["pnl_pip"].mean()),
            "brut_pip": _f(x["brut_pip"].mean()), "maliyet_pip": _f((x["brut_pip"] - x["pnl_pip"]).mean()),
            "R": _f(x["R_pip"].median()), "sd": _f(r.std(ddof=1)), "carpiklik": _f(stats.skew(r)),
            "basiklik": _f(stats.kurtosis(r)), "isabet": _f((r > 0).mean())}


def ay_sonu(kok: Path, sonuclar: dict, islem_yolu, ic_bitis, aile: dict, ciftler: list[str]) -> dict:
    """Fiksing momentumunun ay sonu alt kümesi (önceden kayıtlı varsayılan; ayın son Londra iş günü).

    Parite × pencere: net R ve önceden kayıtlı bootstrap aralığı, brüt R, maliyet (R ve pip), dağılım ölçüleri; aynı
    kuralın öbür günlerinin brütü. Dört paritenin brüt havuzu ay başına bir gözlemle (ay kümeli t; ön kayıtta tanımlı bir
    ölçü değildir: keşif). 28 biçimlik ailenin (ölçümün ay sonu ailesi) iki penceredeki fark p'lerinde Bonferroni, Holm
    ve Benjamini–Hochberg (q < 0,10). Pariteler arası ilinti (aynı ay sonu, net R). Dört parite arasında ampirik Bayes
    büzülmesi (bütün dönem). GBP/USD'nin ekonomik ölçeği (yılda işlem, pip, Sharpe). Çeyrek sonu için yalnız sayım."""
    D = {}
    for c in ciftler:
        s = sonuclar[(FM, c)]
        x = mk.alinan(pd.read_parquet(islem_yolu(kok, FM, c, s["varsayilan"])))
        icm = x["gun"].to_numpy().astype("datetime64[D]") <= np.datetime64(ic_bitis)
        x = x.assign(pen=np.where(icm, "is", "oos"))
        kayit = s["varsayilan_analiz"]["ay_sonu"]["ay_sonu"]
        a = x[x["ay_sonu"].to_numpy(bool)]
        for d in PEN:
            y = _pencere(a, d)
            if len(y) != int(kayit[d]["n"]) or abs(y["r"].mean() - kayit[d]["beklenti_r"]) > 1e-5:
                raise ValueError(f"basarisiz: ay sonu {c} {d}: işlem dosyası kayıtlı ayrımı üretmiyor")
        D[c] = x
    out: dict = {"parite": {}}
    for c, x in D.items():
        a = x[x["ay_sonu"].to_numpy(bool)]
        b = x[~x["ay_sonu"].to_numpy(bool)]
        out["parite"][c] = {d: {"ay_sonu": _ay_ozeti(_pencere(a, d)), "obur_brut": _f(_pencere(b, d)["r_brut"].mean()),
                                "obur_maliyet": _f((_pencere(b, d)["r_brut"] - _pencere(b, d)["r"]).mean())} for d in PEN}
        yy = a.groupby(a["gun"].dt.year)["r"].mean()
        out["parite"][c]["yil"] = {str(k): _f(v) for k, v in yy.items()}
        out["parite"][c]["uc_haric"] = _f(a["r"].sort_values(ascending=False).iloc[3:].mean())
        out["parite"][c]["medyan"] = _f(a["r"].median())
    br = [out["parite"][c][d]["ay_sonu"]["brut"] for c in D for d in ("is", "oos")]
    ob = [out["parite"][c][d]["obur_brut"] for c in D for d in ("is", "oos")]
    out["brut_arti"] = int(sum(v > 0 for v in br))
    out["brut_hucre"] = len(br)
    out["obur_brut"] = [_f(min(ob)), _f(max(ob))]
    P = pd.DataFrame({c: x[x["ay_sonu"].to_numpy(bool)].set_index("gun")["r_brut"] for c, x in D.items()})
    out["brut_havuz"] = {}
    for d in PEN:
        s_ = P if d == "tum" else P[(P.index <= pd.Timestamp(ic_bitis)) == (d == "is")]
        ay = s_.mean(axis=1)
        mu = float(s_.stack().mean())
        out["brut_havuz"][d] = {"ay": int(len(ay)), "brut": _f(mu), "t": _f(mu / (ay.std(ddof=1) / math.sqrt(len(ay))))}
    Pn = pd.DataFrame({c: x[x["ay_sonu"].to_numpy(bool)].set_index("gun")["r"] for c, x in D.items()})
    cm = Pn.corr()
    out["ilinti"] = [{"a": a_, "b": b_, "rho": _f(cm.loc[a_, b_]), "ay": int(Pn[[a_, b_]].dropna().shape[0])}
                     for i, a_ in enumerate(D) for b_ in list(D)[i + 1:]]
    # Aday iki parite (GBP/USD ve USD/JPY) arasındaki ilinti ile öbür çiftlerinki ayrı: ortak bir dolar akımı iki
    # paritenin ay sonu sonucunu birlikte hareket ettirirdi.
    aday = {"GBPUSD", "USDJPY"}
    ob_ = [x["rho"] for x in out["ilinti"] if {x["a"], x["b"]} != aday]
    gj = [x["rho"] for x in out["ilinti"] if {x["a"], x["b"]} == aday]
    out["ilinti_ozet"] = {"aday": gj[0] if gj else None, "obur_min": _f(min(ob_)) if ob_ else None,
                          "obur_max": _f(max(ob_)) if ob_ else None, "obur_n": len(ob_)}
    # 28 biçimlik aile: üyelerin iki penceredeki fark p'leri (sonuç dosyalarından)
    pv = {"is": [], "oos": []}
    for u_ in aile["uye"]:
        s = sonuclar[(u_["birim"], u_["cift"])]
        if u_["kim"] == "varsayilan":
            a_ = s["varsayilan_analiz"]["ay_sonu"]
        elif u_["kim"] == "secilen":
            a_ = s["secilen_analiz"]["ay_sonu"]
        else:
            a_ = s["ay_sonu_tf"][str(u_["tf"])]["ayrim"]
        for d in ("is", "oos"):
            pv[d].append(a_["fark"][d]["p"])
    m = len(aile["uye"])
    fam: dict = {"n": m, "sans_p05": _f(m * 0.05), "sans_iki": _f(m * 0.05 ** 2), "bh_q": BH_Q}
    for d in ("is", "oos"):
        p = np.array(pv[d], np.float64)
        o = np.argsort(p, kind="stable")
        holm = 0
        for i, jx in enumerate(o):
            if p[jx] > 0.05 / (m - i):
                break
            holm += 1
        tut = p[o] <= BH_Q * np.arange(1, m + 1) / m
        fam[d] = {"p05": int((p < 0.05).sum()), "bonferroni": int((p < 0.05 / m).sum()), "holm": holm,
                  "bh": int(np.where(tut)[0].max() + 1) if tut.any() else 0}
    pi, po = np.array(pv["is"]), np.array(pv["oos"])
    fam["iki_p05"] = int(((pi < 0.05) & (po < 0.05)).sum())
    fam["iki_esik"] = int(((pi < 0.05 / m) & (po < 0.05 / m)).sum())
    out["aile"] = fam
    x_ = np.array([out["parite"][c]["tum"]["ay_sonu"]["net"] for c in D])
    se = np.array([out["parite"][c]["tum"]["ay_sonu"]["sd"] / math.sqrt(out["parite"][c]["tum"]["ay_sonu"]["n"]) for c in D])
    mu = float(x_.mean())
    tau2 = max(0.0, float(x_.var(ddof=1) - (se ** 2).mean()))
    son = mu + tau2 / (tau2 + se ** 2) * (x_ - mu)
    out["buzulme"] = {c: {"gozlenen": _f(x_[i]), "buzulmus": _f(son[i])} for i, c in enumerate(D)}
    out["buzulme_tau2"] = _f(tau2)
    g = out["parite"]["GBPUSD"]["tum"]["ay_sonu"]
    x = D["GBPUSD"]
    yil = (x["gun"].max() - x["gun"].min()).days / 365.25
    out["olcek"] = {"islem_yil": _f(g["n"] / yil), "pip_yil": _f(g["n"] / yil * g["net_pip"]),
                    "sharpe_yil": _f(g["net"] / g["sd"] * math.sqrt(g["n"] / yil))}
    out["ceyrek_sonu"] = {c: int((x["ay_sonu"].to_numpy(bool) & x["gun"].dt.month.isin([3, 6, 9, 12]).to_numpy()).sum())
                          for c, x in D.items()}
    return out


# ───────────────────────────────────────────── güç
def _n_gerek(mu: float, sd: float, alfa: float, iki: bool = False) -> float:
    """Tek örneklem ortalamasının sıfırdan ayrılması için gereken işlem: n = ((z₁₋α + z_güç)·σ/μ)²."""
    za = stats.norm.ppf(1 - alfa / 2) if iki else stats.norm.ppf(1 - alfa)
    return float(((za + stats.norm.ppf(GUC_HEDEF)) * sd / mu) ** 2)


def _gucu(mu: float, sd: float, n: float) -> float:
    return float(stats.norm.cdf(mu * math.sqrt(n) / sd - stats.norm.ppf(1 - GUC_ALFA)))


def bakislar(mu_liste: dict, sd: float, siklik: int, bakis: int = BAKIS, yol: int = BAKIS_YOL,
             tohum: int = BAKIS_TOHUM) -> dict:
    """Yıllık bakışlı sıralı sınama (O'Brien–Fleming biçimli sınır c·√(K/k), tek yönlü %5). Sınır sabiti boş varsayımda
    benzetimle bulunur; z_k boş varsayımda bir kez benzetilir ve her etki için kaydırılır: z_k(μ) = z_k(0) + μ√n_k/σ
    (aynı rastgele sayılarla, sabit tohum)."""
    rng = np.random.default_rng(tohum)
    nk = siklik * np.arange(1, bakis + 1)
    # iki bakış arasındaki işlemlerin toplamı N(0, siklik·σ²): bakış başına bir sayı yeter
    adim = rng.normal(0.0, sd * math.sqrt(siklik), size=(yol, bakis))
    z0 = np.cumsum(adim, axis=1) / (sd * np.sqrt(nk))
    oran = np.sqrt(bakis / np.arange(1, bakis + 1))

    def gecme(mu: float, c: float) -> float:
        return float((z0 + mu * np.sqrt(nk) / sd >= c * oran).any(axis=1).mean())
    alt, ust = 1.0, 3.0
    for _ in range(40):
        c = (alt + ust) / 2
        if gecme(0.0, c) > GUC_ALFA:
            alt = c
        else:
            ust = c
    c = (alt + ust) / 2
    return {"c": _f(c), "sinir": [_f(c * o) for o in oran], "bos": _f(gecme(0.0, c)),
            "guc": {k: _f(gecme(v, c)) for k, v in mu_liste.items()}, "yol": yol, "tohum": tohum,
            "sabit_ufuk": {k: _f(_gucu(v, sd, nk[-1])) for k, v in mu_liste.items()}}


def guc(ay: dict, kenar_: dict, t: pd.DataFrame, birimler: dict) -> dict:
    """İleriye dönük bir sınamanın gücü (betimleme; etki görülmüş veriden).

    Birincil: GBP/USD ay sonu tek başına (ayda bir işlem; σ ve μ bütün dönemden; büzülmüş etki ve yarı etki yanında).
    İkincil: GBP/USD + USD/JPY havuzu (görülmüş pencereden seçilmiş iki parite: güç iyimserdir). Bir küçülme senaryosu:
    örneklem içinde anlamlı brüt kenarların ölçülen küçülme oranı ay sonu brütüne uygulanırsa. İlk yılın aralık
    genişliği, gücü ve ölü bir kenarın ilk yıl artı görünme olasılığı. Yıllık beş bakış. En küçük görülebilir etki
    (σ: 88 bileşimin örneklem dışı net R standart sapmasının medyanı). Görülmemiş geçmişin (GECMIS_AY_SONU) gücü."""
    g = ay["parite"]["GBPUSD"]["tum"]["ay_sonu"]
    j = ay["parite"]["USDJPY"]["tum"]["ay_sonu"]
    mu, sd = g["net"], g["sd"]
    esik_ = 0.05 / ay["aile"]["n"]
    buz = ay["buzulme"]["GBPUSD"]["buzulmus"]
    sen = {"gozlenen": mu, "buzulmus": buz, "yari": mu / 2}
    out: dict = {"alfa": GUC_ALFA, "hedef": GUC_HEDEF, "z_alfa": _f(stats.norm.ppf(1 - GUC_ALFA)),
                 "z_guc": _f(stats.norm.ppf(GUC_HEDEF)),
                 "gbp": {"mu": mu, "sd": sd, "siklik": 12, "esik": _f(esik_),
                         "senaryo": {k: {"mu": _f(v), "n": _f(_n_gerek(v, sd, GUC_ALFA)),
                                         "yil": _f(_n_gerek(v, sd, GUC_ALFA) / 12),
                                         "n_esik": _f(_n_gerek(v, sd, esik_, iki=True)),
                                         "yil_esik": _f(_n_gerek(v, sd, esik_, iki=True) / 12)} for k, v in sen.items()}}}
    kuc = kenar_["is_anlamli"]["kuculme"]
    out["gbp"]["kuculme"] = {"oran": kuc, "net": _f(g["brut"] * (1 - kuc) - g["maliyet"])}
    out["gbp"]["ilk_yil"] = {"yari_genislik": _f(Z95 * sd / math.sqrt(12)), "guc": _f(_gucu(mu, sd, 12)),
                             "olu_arti": _f(stats.norm.cdf(-g["maliyet"] * math.sqrt(12) / sd)),
                             "olu_net": _f(-g["maliyet"])}
    mu_h = (g["net"] * g["n"] + j["net"] * j["n"]) / (g["n"] + j["n"])
    sd_h = math.sqrt((g["sd"] ** 2 + j["sd"] ** 2) / 2)
    out["havuz"] = {"mu": _f(mu_h), "sd": _f(sd_h), "n": _f(_n_gerek(mu_h, sd_h, GUC_ALFA)),
                    "yil": _f(_n_gerek(mu_h, sd_h, GUC_ALFA) / 24)}
    out["bakis"] = bakislar({"gozlenen": mu, "buzulmus": buz, "olu": -g["maliyet"]}, sd, 12)
    # en küçük görülebilir etki
    sd_med = float(_pencere(t, "oos").groupby(["kural", "cift"])["r"].std().median())
    katsayi = stats.norm.ppf(1 - GUC_ALFA) + stats.norm.ppf(GUC_HEDEF)
    out["mde"] = {"sigma": _f(sd_med), "tablo": {ad: {str(T): _f(katsayi * sd_med / math.sqrt(f_ * T)) for T in MDE_YIL}
                                                 for ad, f_ in MDE_SIKLIK}}
    orb = _pencere(t, "oos")
    orb = orb[orb["kural"] == "orb"]["r"]
    out["orb"] = {"sigma": _f(orb.std()), "kenar": ORB_KENAR, "n": _f(_n_gerek(ORB_KENAR, float(orb.std()), GUC_ALFA))}
    out["gecmis"] = {"ay": GECMIS_AY_SONU, "guc": _f(_gucu(mu, sd, GECMIS_AY_SONU)),
                     "guc_yari": _f(_gucu(mu / 2, sd, GECMIS_AY_SONU))}
    out["egri"] = [{"mu": m_, "yil": _f(_n_gerek(m_, sd, GUC_ALFA) / 12),
                    "yil_esik": _f(_n_gerek(m_, sd, esik_, iki=True) / 12)} for m_ in GUC_EGRI_MU]
    return out


# ───────────────────────────────────────────── giriş noktası
def bolum(kok: Path, olcum: dict, a, islem_yolu) -> dict:
    """Dersin bütün ölçüleri (betimleme). `olcum`: ölçümün bu ana kadarki kayıtları (birim, tatil, veri, ay sonu ailesi,
    haber, stop çıkışları); `islem_yolu`: ölçümün işlem dosyası adı kuralı (tek tanım ders_olcum'da)."""
    birimler = olcum["birim"]
    ciftler = list(olcum["kunye"]["ciftler"])
    sonuclar = _sonuclar(kok, birimler)
    beklenen = len(birimler) * len(ciftler)
    if len(sonuclar) != beklenen:
        raise ValueError(f"basarisiz: {len(sonuclar)} bileşim, beklenen {beklenen}")
    t = islemler(kok, sonuclar, islem_yolu, a.ic_bitis, "varsayilan")
    ts = islemler(kok, sonuclar, islem_yolu, a.ic_bitis, "secilen")
    G = izgara_tablosu(sonuclar)
    ken = kenar(t, birimler, sonuclar)
    ay = ay_sonu(kok, sonuclar, islem_yolu, a.ic_bitis, olcum["ay_sonu_aile"], ciftler)
    return {
        "kapsam": {"bilesim": len(sonuclar), "kural": len(birimler),
                   "islem": {d: int(len(_pencere(t, d))) for d in PEN},
                   "secilen_bilesim": int(sum(s.get("secilen") is not None for s in sonuclar.values())),
                   "secilen_farkli": int(sum(s.get("secilen") is not None and s["secilen"] != s["varsayilan"]
                                             for s in sonuclar.values()))},
        "basabas": basabas(t, birimler, olcum["stop_cikis"]),
        "ayrisim": ayrisim(sonuclar, birimler),
        "olcek": olcek(t, G),
        "kenar": ken,
        "tek_gun": tek_gun(t, "n4", birimler),
        "sans": sans(t, ts, G, sonuclar, birimler, olcum["tatil"]),
        "esik": esik(t, birimler, sonuclar, olcum["veri"]["kalite"]),
        "haber": haber(olcum["haber"]["cift"]),
        "ay_sonu": ay,
        "guc": guc(ay, ken, t, birimler),
    }
