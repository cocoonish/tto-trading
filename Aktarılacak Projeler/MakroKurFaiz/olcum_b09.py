#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BÖLÜM 9 — Finansman, rezerv, dış varlık pozisyonu: ölçümler.

REZERV. TCMB brüt, net ve swap hariç net rezervleri, milyar USD, haftalık
(cuma). Birincil ölçü SWAP HARİÇ NET'tir: brüt rezerv bankaların döviz
yükümlülüğünü ve swapla ödünç alınan dövizi de taşır.

KAPSAMA (vekil payda). Resmî kalan vadeye göre dış borç stoku bulut
arşivinden gelir (`bulut.kalan_vade_borc`); depodaki vekil, haftalık dış
borç anapara ve faiz ödemelerinin son 52 haftalık toplamıdır. Vekil yalnız
ödenmiş borç servisini sayar — özel kesimin bir yıl içinde vadesi dolacak
borcunu değil — bu yüzden oranı yukarı yanlıdır ve adıyla yazılır.

KUR BASKISI ENDEKSİ (Girton–Roper 1977; ağırlıklar Eichengreen–Rose–Wyplosz
1996'daki gibi bileşenin standart sapmasının tersi):
    EMP_t = Δs/σ_s + (−Δr)/σ_r + Δi/σ_i
Δs haftalık log USD/TRY değişimi (%), Δr swap hariç net rezervin haftalık
değişiminin bir önceki haftanın BRÜT rezervine oranı (%; swap hariç net
eksiye düşebildiği için kendisine oranlanamaz), Δi TCMB ağırlıklı ortalama
fonlama maliyetinin haftalık değişimi (puan). Rezerv KAYBI baskıyı artırır.
σ'lar 2013–2026 örnekleminin tamamından — bu bir TARİF ayrışımıdır, gerçek
zamanlı bir sinyal değil. Bileşen payı: cov(bileşen, EMP)/var(EMP); paylar
toplamı 1'dir.

CUMA KURU. Rezerv cuma stokudur ve haftalık kur cuma etiketinden okunur.
18.12.2023 öncesinde Yahoo USD/TRY'nin cuma değeri PAZARTESİ barının başıdır
(hafta sonu açılışından sonraki fiyat; `ortak_olc.usdtry`, cuma tuzağı): o cuma
hafta sonu haberini taşır ve haftalık Δs bir sonraki haftanın pazartesi
sabahını içeri alır. Kur `cuma_dus=True` ile okunur: geçiş öncesi cuma boştur
ve haftanın son değeri PERŞEMBE kapanışıdır (perşembe → perşembe, beş seans);
geçişten sonra cuma İstanbul 18:00 kapanışıdır. Geçiş haftası (14.12 → 22.12.2023)
altı seans kapsar. Bedel bir seanstır (perşembe kapanışı cuma stokundan bir seans
öncedir); kazanç, ölçülen örnekleme gürültüsünün kalkmasıdır: 2013 → geçiş
arasında (572 hafta) haftalık Δs'nin birinci özilintisi cuma değeriyle −0,26,
perşembe kapanışıyla −0,11; σ %3,24 → %2,64 (`p9b.kur_cuma_olcumu`). Hafta başı açılış
fiyatı ince likiditeli bir kotasyondur ve ertesi gün kısmen geri döner.

DÖNEMLER. Yönetilen kur dönemi `ortak_olc.YONETILEN`dan türetilir: dönem
içindeki ilk ve son cuma, ve komşu dönemlerin sınırı bir hafta öncesi/sonrası.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import bulut
import ortak_olc as oo

BAS = "2013-01-04"
_CUMA = pd.offsets.Week(weekday=4)
_YON_ILK_CUMA = _CUMA.rollforward(oo.YONETILEN[0])          # 2021-12-03
_YON_SON_CUMA = _CUMA.rollback(oo.YONETILEN[1])             # 2023-06-30


def _gun(t) -> str:
    return str(pd.Timestamp(t).date())


DONEMLER = (("2013-01-04", "2017-12-29", "2013–2017"),
            ("2018-01-05", "2020-12-25", "2018–2020"),
            ("2021-01-01", _gun(_YON_ILK_CUMA - pd.Timedelta(days=7)), "2021 (Kasım'a kadar)"),
            (_gun(_YON_ILK_CUMA), _gun(_YON_SON_CUMA), f"yönetilen kur ({oo.YON_AY[0]} … {oo.YON_AY[1]})"),
            (_gun(_YON_SON_CUMA + pd.Timedelta(days=7)), "2026-09-25", f"{oo.YON_SONRASI_AY} … 2026-09"))
EPIZOTLAR = (("2018-07-27", "2018-08-17", "Ağustos 2018"),
             ("2021-11-12", "2021-12-17", "Kasım–Aralık 2021"),
             ("2025-03-14", "2025-04-18", "Mart–Nisan 2025"),
             ("2026-08-28", "2026-09-25", "Eylül 2026"))


def haftalik() -> pd.DataFrame:
    r = oo.oku("rezerv_haftalik")
    s, _ = oo.usdtry(cuma_dus=True)               # geçiş öncesi cuma boş: hafta perşembe kapanışıyla biter
    f = oo.oku("fonlama_gunluk")["aofm"].dropna()
    s_h = s.resample("W-FRI").last()
    f_h = f.resample("W-FRI").last()
    df = pd.concat([r, s_h.rename("usdtry"), f_h.rename("aofm")], axis=1).loc[BAS:]
    df = df.dropna(subset=["swap_haric_net_rezerv_usd", "brut_rezerv_usd", "usdtry", "aofm"])
    return df


def p9a() -> dict:
    r = oo.oku("rezerv_haftalik")
    d = oo.oku("dis_borc_odeme_haftalik")["borc_odeme_top"].dropna() / 1000.0   # milyar USD
    pay = d.rolling(52, min_periods=52).sum()
    # Ödeme haftası çarşamba, rezerv cuma: rezerv haftasına en yakın ÖNCEKİ ödeme toplamı.
    pay_c = pay.reindex(r.index, method="ffill")
    df = pd.concat([r, pay_c.rename("odeme_52h")], axis=1).dropna()
    son = df.index.max()
    yillik = {}
    for yil, g in df.groupby(df.index.year):
        o = g["swap_haric_net_rezerv_usd"] / g["odeme_52h"]
        yillik[str(yil)] = {"en_dusuk": float(o.min()), "en_yuksek": float(o.max()), "yil_sonu": float(o.iloc[-1])}
    out = {
        "yontem": ("Swap hariç net, net ve brüt rezervin son 52 haftada ödenen dış borç anapara ve faizine "
                   "oranı; payda vekildir ve özel kesimin vadesi dolacak borcunu kapsamaz."),
        "kaynak": ["rezerv_haftalik (TCMB)", "dis_borc_odeme_haftalik (EVDS)"],
        "n": int(len(df)), "ilk": str(df.index.min().date()), "son": str(son.date()),
        "son_deger": {"swap_haric_net_mlr_usd": float(df.loc[son, "swap_haric_net_rezerv_usd"]),
                      "net_mlr_usd": float(df.loc[son, "net_rezerv_usd"]),
                      "brut_mlr_usd": float(df.loc[son, "brut_rezerv_usd"]),
                      "odeme_52h_mlr_usd": float(df.loc[son, "odeme_52h"]),
                      "kapsama_swap_haric": float(df.loc[son, "swap_haric_net_rezerv_usd"] / df.loc[son, "odeme_52h"]),
                      "kapsama_brut": float(df.loc[son, "brut_rezerv_usd"] / df.loc[son, "odeme_52h"])},
        "yillik": yillik,
    }
    try:
        kv = bulut.kalan_vade_borc() / 1000.0
        k2 = kv.reindex(r.index, method="ffill")
        o = (r["brut_rezerv_usd"] / k2).dropna()
        out["resmi"] = {"yontem": "Brüt rezervin kalan vadeye göre kısa vadeli dış borca oranı (Greenspan–Guidotti oranı).",
                        "n": int(len(o)), "ilk": str(o.index.min().date()), "son": str(o.index.max().date()),
                        "son_oran": float(o.iloc[-1]), "son_kv_borc_mlr_usd": float(k2.dropna().iloc[-1])}
    except bulut.VeriYok as e:
        out["resmi"] = oo.kurulmadi(str(e))
    return out


def emp_bilesenleri() -> pd.DataFrame:
    df = haftalik()
    b = pd.DataFrame(index=df.index)
    b["ds"] = np.log(df["usdtry"]).diff() * 100
    b["dr"] = df["swap_haric_net_rezerv_usd"].diff() / df["brut_rezerv_usd"].shift(1) * 100
    b["di"] = df["aofm"].diff()
    b = b.dropna()
    sig = b.std()
    k = pd.DataFrame({"kur": b["ds"] / sig["ds"], "rezerv": -b["dr"] / sig["dr"], "faiz": b["di"] / sig["di"]})
    k["emp"] = k.sum(axis=1)
    k.attrs["sigma"] = {"ds_yuzde": float(sig["ds"]), "dr_yuzde": float(sig["dr"]), "di_puan": float(sig["di"])}
    return k


def _paylar(k: pd.DataFrame) -> dict:
    v = k["emp"].var()
    return {b: float(k[b].cov(k["emp"]) / v) for b in ("kur", "rezerv", "faiz")}


def _kur_cuma_olcumu() -> dict:
    """Haftalık USD/TRY'yi cuma değerinden (pazartesi barının başı) ve perşembe
    kapanışından örneklemenin farkı, geçiş öncesi dönemde (CUMA KURU)."""
    s, kun = oo.usdtry()
    x = s[s.index < oo.GECIS_YAHOO_CUMA]
    x = x[x.index >= pd.Timestamp(BAS) - pd.Timedelta(days=7)]
    eski = (np.log(x.resample("W-FRI").last()).diff() * 100).dropna()
    yeni = (np.log(x[x.index.dayofweek < 4].resample("W-FRI").last()).diff() * 100).dropna()
    return {"ilk": str(eski.index.min().date()), "son": str(eski.index.max().date()), "n_hafta": int(len(eski)),
            "ozilinti_cuma_degeri": float(eski.autocorr()), "ozilinti_persembe": float(yeni.autocorr()),
            "sigma_cuma_degeri_yuzde": float(eski.std()), "sigma_persembe_yuzde": float(yeni.std()),
            "cuma_pazartesi_barindan": kun["cuma_pazartesi_barindan"], "cuma_gunu": kun["cuma_gunu_gecis_oncesi"],
            "yontem": "Geçiş öncesi haftalarda haftalık log kur değişimi iki örneklemle: haftanın son değeri cuma "
                      "etiketi (pazartesi barının başı) ve perşembe kapanışı; birinci özilinti ve standart sapma."}


def p9b() -> dict:
    k = emp_bilesenleri()
    df = haftalik()
    donem = {}
    for bas, son, ad in DONEMLER:
        g = k.loc[bas:son]
        donem[ad] = {"n_hafta": int(len(g)), "ilk": str(g.index.min().date()), "son": str(g.index.max().date()),
                     "pay": _paylar(g), "emp_oynaklik": float(g["emp"].std())}
    epizot = {}
    for bas, son, ad in EPIZOTLAR:
        a, z = pd.Timestamp(bas), pd.Timestamp(son)
        g = k.loc[a + pd.Timedelta(days=1):z]
        epizot[ad] = {
            "bas": bas, "son": son, "hafta": int(len(g)),
            "kur_degisim_yuzde": float((df.loc[z, "usdtry"] / df.loc[a, "usdtry"] - 1) * 100),
            "swap_haric_net_degisim_mlr_usd": float(df.loc[z, "swap_haric_net_rezerv_usd"] - df.loc[a, "swap_haric_net_rezerv_usd"]),
            "brut_degisim_mlr_usd": float(df.loc[z, "brut_rezerv_usd"] - df.loc[a, "brut_rezerv_usd"]),
            "aofm_degisim_puan": float(df.loc[z, "aofm"] - df.loc[a, "aofm"]),
            "emp_toplam": float(g["emp"].sum()),
            "bilesen_toplam": {b: float(g[b].sum()) for b in ("kur", "rezerv", "faiz")},
        }
    return {
        "yontem": ("Kur baskısı endeksi: haftalık kur değişimi, rezerv kaybı (brüt rezerve oranla) ve fonlama "
                   "maliyeti değişimi, her biri kendi standart sapmasıyla ölçeklenip toplanır; bileşenin payı "
                   "endeksle kovaryansının endeksin varyansına oranıdır."),
        "kaynak": ["rezerv_haftalik", "usdtry (Yahoo)", "fonlama_gunluk (AOFM)"],
        "kur_cuma_notu": ("18.12.2023 öncesinde haftalık kur perşembe kapanışıdır: Yahoo'nun o dönem cuma değeri "
                          "pazartesi barının başıdır ve hafta sonunu taşır; o cumalar boş bırakıldı."),
        "kur_cuma_olcumu": _kur_cuma_olcumu(),
        "n": int(len(k)), "ilk": str(k.index.min().date()), "son": str(k.index.max().date()),
        "sigma": k.attrs["sigma"], "tam_pay": _paylar(k), "donemler": donem, "epizotlar": epizot,
        "sinir": ("Ağırlıklar örneklemin tamamından kurulur (tarif); yönetilen kur döneminde kur bileşeni "
                  "tasarım gereği bastırılmıştır; rezerv bileşeni değerleme etkisini de taşır."),
    }


def p9c() -> dict:
    try:
        u = bulut.uyp()
    except bulut.VeriYok as e:
        return oo.kurulmadi(str(e))
    c = oo.oku("odemeler_aylik")["cari"].dropna()
    c_q = c.resample("QE").sum(min_count=3)
    u = u.copy()
    u.index = u.index.to_period("Q").to_timestamp("Q")
    c_q.index = c_q.index.to_period("Q").to_timestamp("Q")
    # UYP 2005'e kadar YILLIK (yıl sonu), 2006'dan çeyreklik yayımlanır: değişim iki ardışık
    # gözlem arasındaki aralığa, cari denge de AYNI aralığın toplamına yazılır (yıllık aralıkta
    # dört çeyrek; tek çeyreğin cari dengesi yıllık değişimle eşlenmez).
    nuyp = u["net"].dropna().sort_index()
    satir = []
    for onceki, t in zip(nuyp.index[:-1], nuyp.index[1:]):
        q = c_q[(c_q.index > onceki) & (c_q.index <= t)]
        beklenen = len(pd.period_range(onceki.to_period("Q") + 1, t.to_period("Q"), freq="Q"))
        if len(q) != beklenen or q.isna().any():
            continue
        satir.append({"tarih": t, "nuyp": nuyp[t], "d_nuyp": nuyp[t] - nuyp[onceki], "cari": float(q.sum()),
                      "aralik_ceyrek": beklenen})
    df = pd.DataFrame(satir).set_index("tarih")
    df["degerleme"] = df["d_nuyp"] - df["cari"]
    son = df.index.max()
    return {"yontem": ("Net uluslararası yatırım pozisyonunun iki ardışık gözlem arasındaki değişimi (2005'e kadar "
                       "yıllık, 2006'dan çeyreklik), cari dengenin aynı aralıktaki toplamı ve aradaki fark "
                       "(değerleme, net hata ve noksan ile sermaye hesabını birlikte taşır)."),
            "yillik_aralik": int((df["aralik_ceyrek"] > 1).sum()),
            "kaynak": ["EVDS UYP", "odemeler_aylik (cari)"],
            "n": int(len(df)), "ilk": str(df.index.min().date()), "son": str(son.date()),
            "son_nuyp_mlr_usd": float(df.loc[son, "nuyp"] / 1000),
            "toplam_d_nuyp_mlr_usd": float(df["d_nuyp"].sum() / 1000),
            "toplam_cari_mlr_usd": float(df["cari"].sum() / 1000),
            "toplam_degerleme_mlr_usd": float(df["degerleme"].sum() / 1000),
            "seri": {"tarih": [str(t.date()) for t in df.index],
                     "d_nuyp": [float(x / 1000) for x in df["d_nuyp"]],
                     "cari": [float(x / 1000) for x in df["cari"]],
                     "degerleme": [float(x / 1000) for x in df["degerleme"]]}}


def sekil_16() -> dict:
    k = emp_bilesenleri()
    a = k.resample("MS").sum()
    return {"n": int(len(a)), "ilk": str(a.index.min().date()), "son": str(a.index.max().date()),
            "n_hafta": int(len(k)),
            "yontem": "Kur baskısı endeksinin üç bileşeni (σ birimi), haftalık değerlerin ay içi toplamı.",
            "kaynak": ["rezerv_haftalik", "usdtry (Yahoo)", "fonlama_gunluk (AOFM)"],
            "tarih": [str(t.date()) for t in a.index],
            "kur": [float(x) for x in a["kur"]], "rezerv": [float(x) for x in a["rezerv"]],
            "faiz": [float(x) for x in a["faiz"]], "emp": [float(x) for x in a["emp"]],
            "not": "Haftalık bileşenlerin ay içi toplamı (σ birimi)."}


def olc() -> dict:
    return oo.yuvarla({"p9a": p9a(), "p9b": p9b(), "p9c": p9c(), "sekil_16": sekil_16()}, 6)


if __name__ == "__main__":
    import json
    import time
    t0 = time.monotonic()
    d = olc()
    print(json.dumps({k: v for k, v in d.items() if k != "sekil_16"}, ensure_ascii=False, indent=1, allow_nan=False)[:7000])
    print(f"süre {time.monotonic() - t0:.1f} sn")
