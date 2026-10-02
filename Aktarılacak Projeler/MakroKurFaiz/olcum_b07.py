#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BÖLÜM 7 — Reel efektif kur ve PPP: ölçümler.

YÖN. TCMB REDK'nin ARTIŞI TL'nin REEL DEĞER KAZANCIDIR (ders q'sunun tersi).
Bütün sapmalar log(REDK) cinsindendir; artı sapma "ortalamaya göre pahalı TL".

YARI ÖMÜR. ρ, ortalaması çıkarılmış log REDK'nin AR(1) katsayısıdır; yarı ömür
ln 0,5 / ln ρ ay. Küçük örneklemde OLS ρ aşağı yanlıdır (Andrews 1993), bu
yüzden nokta değil medyan-yansız kestirim ve %90 aralığı verilir; üst uç
1'e dayanırsa yarı ömrün üst sınırı SONSUZDUR ve öyle yazılır.

ADF. Sabitli Dickey–Fuller; gecikme sayısı 0…12 arasında Akaike ölçütüyle,
ortak örneklemde seçilir. Kritik değerler MacKinnon (sabitli, büyük örneklem):
%5 −2,86, %10 −2,57.

BALASSA–SAMUELSON VEKİLİ İKİ TANE. (1) Hizmet/mal göreli fiyatı (TÜFE alt
endeksleri, 2005+). (2) TÜFE bazlı ile Yİ-ÜFE bazlı REDK'nin oranı (1994+):
TÜFE ticarete konu olmayan hizmetleri içerir, ÜFE büyük ölçüde ticarete konu
mallardır; iki reel kurun ayrışması bu yüzden göreli fiyat kanalının izidir.
Verimlilik bacağı ölçülmedi.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo

DONEMLER = (("1994-01", "2001-12", "1994–2001 (sabit kura yakın rejim ve krizler)"),
            ("2002-01", "2017-12", "2002–2017 (dalgalı kur, enflasyon hedeflemesi)"),
            ("2018-01", "2026-08", "2018–2026 (yüksek oynaklık)"))
ADF_KRITIK = {"yuzde5": -2.86, "yuzde10": -2.57}
FAN_AY = 60
BIS_DM = ["US", "XM", "JP", "GB", "CH", "AU", "CA", "NO", "SE"]
BIS_EM = ["TR", "BR", "MX", "ZA", "IN", "ID", "PL", "HU", "CL", "KR"]


def adf(y: pd.Series, azami_gecikme: int = 12) -> dict:
    """Sabitli ADF; gecikme AIC ile (ortak örneklem)."""
    x = np.asarray(y.dropna(), dtype=float)
    dx = np.diff(x)
    n = len(dx)
    p = azami_gecikme
    Y = dx[p:]
    duzey = x[p:-1]
    gecik = np.column_stack([dx[p - j:n - j] for j in range(1, p + 1)]) if p else np.empty((len(Y), 0))
    en_iyi = None
    for k in range(0, p + 1):
        X = np.column_stack([np.ones(len(Y)), duzey] + ([gecik[:, :k]] if k else []))
        b, *_ = np.linalg.lstsq(X, Y, rcond=None)
        e = Y - X @ b
        s2 = (e @ e) / (len(Y) - X.shape[1])
        aic = len(Y) * math.log((e @ e) / len(Y)) + 2 * X.shape[1]
        se = math.sqrt(s2 * np.linalg.inv(X.T @ X)[1, 1])
        aday = {"gecikme": k, "t": float(b[1] / se), "aic": aic}
        if en_iyi is None or aic < en_iyi["aic"]:
            en_iyi = aday
    t = en_iyi["t"]
    return {"t": t, "gecikme": en_iyi["gecikme"], "n": int(len(Y)), "kritik": ADF_KRITIK,
            "birim_kok_red_yuzde5": bool(t < ADF_KRITIK["yuzde5"]),
            "birim_kok_red_yuzde10": bool(t < ADF_KRITIK["yuzde10"])}


def yari_omur_olc(s: pd.Series, tohum: int) -> dict:
    """Log seviye, ortalaması çıkarılmış: OLS ρ, medyan-yansız ρ ve %90 aralığı, ADF."""
    ls = np.log(s.dropna())
    mu = oo.ar1_medyan_yansiz(ls, tohum=tohum)
    out = {"n": mu["n"], "ilk": str(ls.index.min().date()), "son": str(ls.index.max().date()),
           "rho_ols": mu["rho_ols"], "rho_mu": mu["rho_mu"], "rho_alt90": mu["rho_alt90"],
           "rho_ust90": mu["rho_ust90"],
           "yari_omur_ols_ay": mu["yo_ols"], "yari_omur_mu_ay": mu["yo_mu"],
           "yari_omur_alt90_ay": mu["yo_alt90"], "yari_omur_ust90_ay": mu["yo_ust90"],
           "ust_sonsuz": mu["ust_sonsuz"], "adf": adf(ls)}
    for k in ("ols", "mu", "alt90", "ust90"):
        v = out[f"yari_omur_{k}_ay"]
        out[f"yari_omur_{k}_yil"] = None if v is None else v / 12
    return out


def mu_egilimli(ls: pd.Series, tohum: int, deneme: int = 400) -> dict:
    """Doğrusal eğilimi çıkarılmış seride medyan-yansız ρ: benzetimde her yapay seri
    AYNI biçimde (sabit + eğilim) arındırılır, yoksa yanlılık düzeltmesi yanlış kalıba göre olur."""
    x = np.asarray(ls.dropna(), dtype=float)
    n = len(x)
    T = np.column_stack([np.ones(n), np.arange(n)])
    P = np.eye(n) - T @ np.linalg.pinv(T)

    def rho(m: np.ndarray) -> np.ndarray:
        r = m @ P.T
        return np.einsum("ij,ij->i", r[:, 1:], r[:, :-1]) / np.einsum("ij,ij->i", r[:, :-1], r[:, :-1])
    rho_hat = float(rho(x[None, :])[0])
    rng = np.random.default_rng(tohum)
    izgara = np.linspace(0.5, 1.0, 101)
    med, q05, q95 = [], [], []
    for r_ in izgara:
        e = rng.standard_normal((deneme, n))
        y = np.empty((deneme, n))
        y[:, 0] = e[:, 0] / math.sqrt(max(1 - r_ * r_, 1e-6)) if r_ < 1 else e[:, 0]
        for i in range(1, n):
            y[:, i] = r_ * y[:, i - 1] + e[:, i]
        t = rho(y)
        med.append(np.median(t)); q05.append(np.quantile(t, 0.05)); q95.append(np.quantile(t, 0.95))

    def ters(egri):
        egri = np.asarray(egri)
        if rho_hat <= egri[0]:
            return float(izgara[0])
        if rho_hat >= egri[-1]:
            return float(izgara[-1])
        j = int(np.searchsorted(egri, rho_hat))
        a, b = egri[j - 1], egri[j]
        return float(izgara[j - 1] + (rho_hat - a) / (b - a) * (izgara[j] - izgara[j - 1]))
    mu, alt, ust = ters(med), ters(q95), ters(q05)
    egim = float(np.linalg.lstsq(T, x, rcond=None)[0][1]) * 12
    return {"n": n, "egilim_log_yil": egim, "rho_ols": rho_hat, "rho_mu": mu, "rho_alt90": alt, "rho_ust90": ust,
            "yari_omur_mu_yil": None if oo.yari_omur(mu) is None else oo.yari_omur(mu) / 12,
            "yari_omur_alt90_yil": None if oo.yari_omur(alt) is None else oo.yari_omur(alt) / 12,
            "yari_omur_ust90_yil": None if (ust >= 0.9999 or oo.yari_omur(ust) is None) else oo.yari_omur(ust) / 12,
            "ust_sonsuz": bool(ust >= 0.9999)}


def p7a() -> dict:
    r = oo.oku("redk_aylik")
    sonuc = {"yontem": ("Ortalaması çıkarılmış log reel efektif kurun birinci derece özbağlanım katsayısı; "
                        "küçük örneklem yanlılığına karşı benzetimle medyan-yansız kestirim ve %90 aralığı, "
                        "birim kök için Dickey–Fuller sınaması."),
              "kaynak": ["redk_aylik (TCMB, 2003=100; artış TL'nin reel değer kazancı)"]}
    for sut, ad in (("redk_tufe", "tufe"), ("redk_ufe", "ufe")):
        tam = yari_omur_olc(r[sut], tohum=20261002 + (0 if ad == "tufe" else 1))
        alt = {}
        for i, (bas, son, etiket) in enumerate(DONEMLER):
            a = yari_omur_olc(r[sut].loc[bas:son], tohum=20261010 + i + (0 if ad == "tufe" else 10))
            a["etiket"] = etiket
            alt[f"{bas[:4]}_{son[:4]}"] = a
        egilimli = mu_egilimli(np.log(r[sut].dropna()), tohum=20261020 + (0 if ad == "tufe" else 1))
        sonuc[ad] = {"tam": tam, "donemler": alt, "egilimden_arindirilmis": egilimli}
    # Bugünkü sapma: tam örneklem ve 2003+ ortalamasına göre
    ls = np.log(r["redk_tufe"].dropna())
    son = ls.index.max()
    sonuc["sapma"] = {
        "tarih": str(son.date()), "redk_tufe": float(r["redk_tufe"].loc[son]),
        "sapma_tam_log": float(ls.loc[son] - ls.mean()),
        "sapma_2003_log": float(ls.loc[son] - ls.loc["2003":].mean()),
        "yuzdelik_tam": float((ls <= ls.loc[son]).mean() * 100),
        "ortalama_tam_endeks": float(math.exp(ls.mean())),
        "ortalama_2003_endeks": float(math.exp(ls.loc["2003":].mean())),
    }
    return sonuc


def p7b() -> dict:
    e = oo.oku("enflasyon_aylik")
    r = oo.oku("redk_aylik")
    gf = np.log(e["hizmet"] / e["mallar"]).dropna()
    t = (gf.index - gf.index[0]).days / 365.25
    egim = oo.hac(gf.values, np.asarray(t))
    q = np.log(r["redk_tufe"]).dropna()
    d12_gf = gf.diff(12)
    d12_q = q.diff(12).reindex(d12_gf.index)
    birlik = pd.concat([d12_gf.rename("gf"), d12_q.rename("q")], axis=1).dropna()
    # Örtüşen 12 aylık farklar: HAC gecikmesi ufkun üstünde tutulur.
    reg = oo.hac(birlik["q"].values, birlik["gf"].values, gecikme=18)
    oran = np.log(r["redk_tufe"] / r["redk_ufe"]).dropna()
    t2 = (oran.index - oran.index[0]).days / 365.25
    egim2 = oo.hac(oran.values, np.asarray(t2))
    return {
        "yontem": ("Hizmet fiyatlarının mal fiyatlarına oranının ve TÜFE bazlı reel kurun Yİ-ÜFE bazlı reel "
                   "kura oranının logaritmik eğilimi (yıllık), ve göreli fiyatın 12 aylık değişiminin reel "
                   "kurun 12 aylık değişimiyle ilişkisi."),
        "kaynak": ["enflasyon_aylik (hizmet, mallar)", "redk_aylik"],
        "goreli_fiyat": {"ilk": str(gf.index.min().date()), "son": str(gf.index.max().date()), "n": int(len(gf)),
                         "toplam_degisim_log": float(gf.iloc[-1] - gf.iloc[0]),
                         "toplam_degisim_yuzde": float((math.exp(gf.iloc[-1] - gf.iloc[0]) - 1) * 100),
                         "egim_log_yil": egim["b"][1], "egim_t": egim["t"][1]},
        "reel_kur_iliskisi": {"n": reg["n"], "egim": reg["b"][1], "t": reg["t"][1], "r2": reg["r2"],
                              "gecikme": reg["gecikme"],
                              "ilk": str(birlik.index.min().date()), "son": str(birlik.index.max().date())},
        "tufe_ufe_reel_kur_orani": {"ilk": str(oran.index.min().date()), "son": str(oran.index.max().date()),
                                    "n": int(len(oran)),
                                    "toplam_degisim_log": float(oran.iloc[-1] - oran.iloc[0]),
                                    "egim_log_yil": egim2["b"][1], "egim_t": egim2["t"][1]},
        "sinir": "Verimlilik bacağı (ticarete konu sektörde göreli verimlilik artışı) ölçülmedi.",
    }


def p7c() -> dict:
    try:
        df = bulut.bis_reer("R")
    except bulut.VeriYok as e:
        return {"durum": "kurulmadi", "sebep": str(e)}
    out = {"yontem": ("BIS geniş reel efektif kurlarında (aylık) ülke başına medyan-yansız yarı ömür."),
           "kaynak": ["BIS WS_EER (reel, geniş)"], "ulkeler": {}}
    for i, ulke in enumerate(BIS_DM + BIS_EM):
        if ulke not in df.columns:
            out["ulkeler"][ulke] = {"durum": "kurulmadi", "sebep": "BIS dosyasında yok"}
            continue
        s = df[ulke].dropna()
        mu = oo.ar1_medyan_yansiz(np.log(s), tohum=20261100 + i, deneme=300)
        out["ulkeler"][ulke] = {"grup": "DM" if ulke in BIS_DM else "EM", "n": mu["n"],
                                "ilk": str(s.index.min().date()), "son": str(s.index.max().date()),
                                "rho_mu": mu["rho_mu"], "yari_omur_mu_yil": None if mu["yo_mu"] is None else mu["yo_mu"] / 12,
                                "yari_omur_alt90_yil": None if mu["yo_alt90"] is None else mu["yo_alt90"] / 12,
                                "ust_sonsuz": mu["ust_sonsuz"]}
    for g in ("DM", "EM"):
        grup = [u for u in out["ulkeler"].values() if u.get("grup") == g]
        # Sonsuz yarı ömür (ρ_mu = 1) medyandan DÜŞÜRÜLMEZ: düşürülse medyan aşağı yanlı olur.
        mu = [u["yari_omur_mu_yil"] if u.get("yari_omur_mu_yil") is not None else math.inf for u in grup]
        alt = [u["yari_omur_alt90_yil"] for u in grup if u.get("yari_omur_alt90_yil") is not None]
        med = float(np.median(mu)) if mu else None
        out[g.lower()] = {"n": len(grup), "n_mu_sonsuz": int(sum(1 for v in mu if math.isinf(v))),
                          "medyan_mu_yil": None if (med is None or math.isinf(med)) else med,
                          "medyan_mu_sonsuz": bool(med is not None and math.isinf(med)),
                          "medyan_alt90_yil": float(np.median(alt)) if alt else None}
    return out


def vakalar() -> dict:
    r = oo.oku("redk_aylik")["redk_tufe"]
    out = {}
    for yil in (2021, 2023):
        alt = r.loc[str(yil)]
        dip = alt.idxmin()
        sonra = r.loc[dip + pd.DateOffset(months=12)] if (dip + pd.DateOffset(months=12)) in r.index else None
        out[f"tr_dip_{yil}"] = {"tarih": str(dip.date()), "redk_tufe": float(alt.min()),
                               "sonraki_12ay_redk": None if sonra is None else float(sonra),
                               "sonraki_12ay_degisim_yuzde": None if sonra is None else float((sonra / alt.min() - 1) * 100)}
    k = oo.oku("cnbc_kur_gunluk")
    eurchf = (k["eur"] * k["chf"]).dropna()          # EUR/USD × USD/CHF = EUR/CHF
    usdchf = k["chf"].dropna()
    g0, g1 = pd.Timestamp("2015-01-14"), pd.Timestamp("2015-01-15")
    out["isvicre_2015"] = {
        "tarih": "2015-01-15", "saat": "New York 17:00 kapanışları (CNBC)",
        "eurchf_once": float(eurchf.loc[g0]), "eurchf_sonra": float(eurchf.loc[g1]),
        "eurchf_degisim_yuzde": float((eurchf.loc[g1] / eurchf.loc[g0] - 1) * 100),
        "usdchf_degisim_yuzde": float((usdchf.loc[g1] / usdchf.loc[g0] - 1) * 100),
    }
    return out


def sekil_12(a: dict) -> dict:
    r = oo.oku("redk_aylik")["redk_tufe"].dropna()
    ls = np.log(r)
    ort = ls.mean()
    son = ls.index.max()
    sapma = float(ls.loc[son] - ort)
    tam = a["tufe"]["tam"]
    gelecek = pd.date_range(son, periods=FAN_AY + 1, freq="MS")
    yollar = {}
    for ad, rho in (("mu", tam["rho_mu"]), ("alt90", tam["rho_alt90"]), ("ust90", tam["rho_ust90"])):
        h = np.arange(FAN_AY + 1)
        yollar[ad] = [float(math.exp(ort + sapma * rho ** k)) for k in h]
    return {"tarih": [str(t.date()) for t in r.index], "redk_tufe": [float(v) for v in r.values],
            "ortalama_endeks": float(math.exp(ort)),
            "fan_tarih": [str(t.date()) for t in gelecek], "fan": yollar,
            "not": "Fan, bugünkü sapmanın ρ^h ile söndüğü yoldur; tahmin değil, kestirilen kalıcılığın görselidir."}


def arac_redk(a: dict) -> dict:
    tam = a["tufe"]["tam"]
    s = a["sapma"]
    rho = tam["rho_mu"]
    beklenen12 = (rho ** 12 - 1) * s["sapma_tam_log"]
    return {"sapma_log": s["sapma_tam_log"], "rho_aylik": rho, "rho_alt90": tam["rho_alt90"],
            "rho_ust90": tam["rho_ust90"],
            "beklenen_12ay_log": beklenen12,
            "beklenen_12ay_yuzde": (math.exp(beklenen12) - 1) * 100,
            "aciklama": ("Artı sapma ortalamaya göre pahalı TL'dir; ρ<1 ise beklenen yol reel değer "
                         "kaybıdır (REDK düşer). Bu bir çekim terimidir, yön ve zamanlama tahmini değildir.")}


def olc() -> dict:
    a = p7a()
    return oo.yuvarla({"p7a": a, "p7b": p7b(), "p7c": p7c(), "vakalar": vakalar(),
                       "sekil_12": sekil_12(a), "arac_redk": arac_redk(a)}, 6)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps({k: v for k, v in d.items() if k != "sekil_12"}, ensure_ascii=False, indent=1, allow_nan=False)[:6000])
    print(f"süre {time.monotonic() - t0:.1f} sn")
