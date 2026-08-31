#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VADE PROJEKSİYONU — Hazine'nin ihraç vadesi nereye gidiyor, maliyeti ne?

Neden ayrı modül: `web_cikti_tahmin.py` panonun on üç grafiğini üretiyor ve
sorusu "bugün ne oldu". Buradaki soru başka: strateji dokümanı DEĞİŞTİĞİNDE
ihraç vadesi ve maliyeti nereye gidiyor. Cevap iki takvimin karşılaştırılmasını
gerektiriyor (arşiv), üstelik ikisinin de AYNI yöntemle yeniden hesaplanmasını —
yoksa bizim tahmin yöntemimizdeki bir değişiklik Hazine'nin strateji değişikliği
sanılır.

Kurucu karar — KARŞI OLGU AYNI YÖNTEMLE KURULUR. Arşivdeki eski takvimin
tahmin sütunları o günün (kusurlu) kıyas yöntemiyle üretildi. Bu modül eski
takvimin SATIRLARINI alır, tahminleri BUGÜNKÜ yöntemle yeniden hesaplar ve
öyle karşılaştırır. Aksi halde ölçtüğümüz şey Hazine'nin kararı değil, kendi
düzeltmemiz olurdu.

Kurucu karar — AOV TUTARA DEĞİL PAYA BAKAR. Ağırlıklı ortalama vade bir ay
içindeki GÖRECELİ ağırlıkların fonksiyonudur; ayın toplamı hedefe ölçeklendiği
için ölçek AOV'yi değiştirmez. Böylece "hedef değişti" ile "kompozisyon
değişti" birbirine karışmaz.

Çıktılar: vade_proj.json + dört grafik (vade_patika, vade_kompozisyon,
vade_maliyet, vade_talep).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

KOK = Path(__file__).resolve().parent
sys.path.insert(0, str(KOK))
from main import TreasuryAuctionScraper as T          # noqa: E402
from web_cikti_tahmin import (                        # noqa: E402
    CLARET, CLARET_KOYU, TEAL, GOLD, SLATE, INK, GRI, TIP_RENK, AYLAR,
    ortak_stil, tr,
)

ARSIV = KOK / "takvim_arsiv"
# Nominal maliyet ortalamasına giren türler. TÜFE'ye endeksli senedin bileşik
# faizi REEL'dir (ihalede %5,6 çıkıyor); nominallerle aynı ortalamaya katmak
# maliyeti sistematik olarak aşağı çeker. Değişken faizli ve TLREF'e endeksli
# senetlerin bileşiği ihale günündeki gösterge/TLREF ile kurulur, yani nominal
# ama SABİT DEĞİL — ayrı raporlanır.
NOMINAL_SABIT = {"Hazine Bonosu", "Sabit Kuponlu Devlet Tahvili",
                 "Kuponsuz Devlet Tahvili"}
DEGISKEN = {"TLREF'e Endeksli Devlet Tahvili", "Değişken Faizli Devlet Tahvili"}
REEL = {"TÜFE'ye Endeksli Devlet Tahvili"}
KOVA_SINIR = [0, 1, 3, 6, 100]
KOVA_AD = ["≤1 yıl", "1-3 yıl", "3-6 yıl", "6 yıl+"]
MALIYET_PENCERE_AY = 4        # "güncel maliyet" penceresi


def _vade_yil(terim: str) -> float | None:
    """'5Yıl /1673 Gün' → 4.58. GÜN varsa gün kullanılır: '2Yıl /707 Gün' 1,94'tür,
    2,00 değil — yeniden ihraçta kalan vade yıl etiketinden kısadır ve AOV'yi
    yıl etiketiyle hesaplamak vadeyi sistematik olarak UZUN gösterir."""
    s = str(terim)
    m = re.search(r"/\s*(\d+)\s*Gün", s)
    if m:
        return int(m.group(1)) / 365.0
    m = re.match(r"(\d+)\s*Yıl", s)
    if m:
        return float(m.group(1))
    m = re.match(r"(\d+)\s*Ay", s)
    return float(m.group(1)) / 12.0 if m else None


def _gecmis() -> pd.DataFrame:
    h = pd.read_csv(KOK / "hazine_ihale_verileri.csv", encoding="utf-8-sig")
    for c in ("Toplam(Gerçekleşme)", "Toplam(Teklif)", "Vade (Yıl)",
              "Ortalama Yıllık Bileşik(Gerçekleşme)"):
        h[c] = pd.to_numeric(h[c], errors="coerce")
    h["_d"] = pd.to_datetime(h["İhale Tarihi"], format="%d.%m.%Y", errors="coerce")
    h = h.dropna(subset=["_d", "Toplam(Gerçekleşme)"])
    return h[h["Toplam(Gerçekleşme)"] > 0].sort_values("_d").reset_index(drop=True)


def _takvim_aov(yol: Path, hist: pd.DataFrame) -> pd.DataFrame:
    """Bir takvim dosyasının ay bazında AOV'si — tahminler BUGÜNKÜ yöntemle."""
    d = pd.read_csv(yol, encoding="utf-8-sig")
    d = d[d["Yöntem"].astype(str).str.contains("hale", na=False)].copy()
    ham = []
    for _, r in d.iterrows():
        yf = str(r["Yöntem"]).lower().replace("̇", "").replace("ı", "i")
        yen = True if "yeniden" in yf else (False if "ilk" in yf else None)
        ym = re.match(r"(\d+)\s*Yıl", str(r["Vade Terimi"]))
        ty = float(ym.group(1)) if ym else None
        res = T._forecast_from_comparables(r["Senet Tanımı"], r["İtfa Tarihi"],
                                           ty, hist, yeniden=yen)
        ham.append(res["raw_amt"] if res else None)
    d["ham"] = ham
    d["v"] = d["Vade Terimi"].map(_vade_yil)
    d["ay"] = pd.to_datetime(d["İhale Tarihi"], dayfirst=True).dt.to_period("M")
    return d.dropna(subset=["ham", "v"])


def _aov_ay(d: pd.DataFrame) -> dict:
    out = {}
    for ay, g in d.groupby("ay"):
        out[str(ay)] = round(float((g["v"] * g["ham"]).sum() / g["ham"].sum()), 2)
    return out


def main() -> int:
    hist = _gecmis()
    yeni_yol = KOK / "hazine_planlanan_ihaleler.csv"
    # KARŞI OLGU İÇİN "ÖNCEKİ" TAKVİM İÇERİKTEN SEÇİLİR, SIRADAN DEĞİL.
    # Arşive aynı stratejinin birden çok kopyası girebilir (hat aynı ay iki kez
    # tam kipte koşarsa) ve o zaman "sondan bir önceki dosya" aynı takvimin
    # kopyası olur; fark sıfır çıkar ve karşılaştırma sessizce ANLAMSIZLAŞIR.
    # Bu yüzden yürürlükteki takvimle AYNI İSKELETİ (tarih+senet+vade üçlüsü)
    # taşıyan arşiv kayıtları elenir; kalanların en yenisi karşı olgudur.
    def _iskelet(y: Path) -> frozenset:
        try:
            t = pd.read_csv(y, encoding="utf-8-sig")
            return frozenset(zip(t["İhale Tarihi"], t["Senet Tanımı"], t["Vade Terimi"]))
        except Exception:
            return frozenset()
    simdiki = _iskelet(yeni_yol)
    adaylar = [y for y in sorted(ARSIV.glob("*.csv")) if _iskelet(y) != simdiki]
    eski_yol = adaylar[-1] if adaylar else None
    if eski_yol is None:
        print("  ! arşivde FARKLI bir takvim yok — karşı olgu kurulamıyor")
    else:
        print(f"  karşı olgu: {eski_yol.name}")

    yeni = _takvim_aov(yeni_yol, hist)
    aov_yeni = _aov_ay(yeni)
    aov_eski, eski_ad = {}, ""
    if eski_yol is not None:
        eski = _takvim_aov(eski_yol, hist)
        aov_eski = _aov_ay(eski)
        eski_ad = eski_yol.stem

    # ── 1) TARİHSEL AOV + PROJEKSİYON ────────────────────────────────────────
    va = pd.read_csv(KOK / "hazine_vade_analizi.csv", encoding="utf-8-sig")
    va["ay"] = pd.PeriodIndex(va["Dönem"], freq="M")
    va = va.sort_values("ay")
    gecmis_aov = {str(r["ay"]): round(float(r["Ağırlıklı Ortalama Vade (Yıl)"]), 2)
                  for _, r in va.iterrows()}
    gecmis_hacim = {str(r["ay"]): float(r["Toplam İhraç (Milyon TL)"])
                    for _, r in va.iterrows()}

    # Plan aylarının hacmi: ozet.json'daki ölçekli tahmin (hedefe tutarlı)
    plan = pd.read_csv(yeni_yol, encoding="utf-8-sig")
    plan["g"] = pd.to_numeric(plan["Tahmini Gerçekleşme (Milyon TL)"], errors="coerce")
    plan["ay"] = pd.to_datetime(plan["İhale Tarihi"], dayfirst=True).dt.to_period("M")
    plan_hacim = {str(a): float(g["g"].sum()) for a, g in plan.dropna(subset=["g"]).groupby("ay")}

    # 3 aylık yuvarlanan AOV: gerçekleşen aylar + plan ayları, hacim ağırlıklı.
    # Hazine'nin kendi raporladığı ölçüt bu; tek ay çok oynak (Kasım 2025'te
    # 1,62 yıl, bir sonraki ay 2,33) ve tek aya bakarak "vade uzadı" demek
    # gürültüyü eğilim sanmaktır.
    seri_aov = dict(gecmis_aov); seri_aov.update(aov_yeni)
    seri_hac = dict(gecmis_hacim); seri_hac.update(plan_hacim)
    aylar = sorted(seri_aov, key=lambda s: pd.Period(s, freq="M"))
    yuv = {}
    for i, a in enumerate(aylar):
        pencere = aylar[max(0, i - 2): i + 1]
        w = sum(seri_hac.get(x, 0) for x in pencere)
        if w > 0:
            yuv[a] = round(sum(seri_aov[x] * seri_hac.get(x, 0) for x in pencere) / w, 2)

    # ── 2) TÜR KOMPOZİSYONU ──────────────────────────────────────────────────
    hist["ay"] = hist["_d"].dt.to_period("M")
    komp = (hist[hist["ay"] >= pd.Period("2025-09", "M")]
            .pivot_table(index="ay", columns="Senet Tanımı",
                         values="Toplam(Gerçekleşme)", aggfunc="sum").fillna(0))
    plan_komp = plan.dropna(subset=["g"]).pivot_table(
        index="ay", columns="Senet Tanımı", values="g", aggfunc="sum").fillna(0)

    # ── 3) MALİYET: vade kovası × tür ────────────────────────────────────────
    hist["kova"] = pd.cut(hist["Vade (Yıl)"], KOVA_SINIR, labels=KOVA_AD)
    pencere_bas = hist["_d"].max() - pd.DateOffset(months=MALIYET_PENCERE_AY)
    son = hist[hist["_d"] >= pencere_bas].dropna(
        subset=["Ortalama Yıllık Bileşik(Gerçekleşme)"])
    maliyet = {}
    for ad, kume in (("sabit", NOMINAL_SABIT), ("degisken", DEGISKEN), ("reel", REEL)):
        g = son[son["Senet Tanımı"].isin(kume)]
        for kova, gg in g.groupby("kova", observed=True):
            if gg["Toplam(Gerçekleşme)"].sum() <= 0:
                continue
            maliyet[f"{ad}|{kova}"] = {
                "maliyet": round(float((gg["Ortalama Yıllık Bileşik(Gerçekleşme)"]
                                        * gg["Toplam(Gerçekleşme)"]).sum()
                                       / gg["Toplam(Gerçekleşme)"].sum()), 2),
                "tutar_mlr": round(float(gg["Toplam(Gerçekleşme)"].sum()) / 1000, 1),
                "n": int(len(gg)),
            }

    # ── 4) TALEP: bid-to-cover, vade kovası × çeyrek ─────────────────────────
    t = hist[hist["_d"] >= pd.Timestamp("2024-07-01")].copy()
    t["ceyrek"] = t["_d"].dt.to_period("Q")
    b = t.pivot_table(index="ceyrek", columns="kova", values="Toplam(Teklif)",
                      aggfunc="sum", observed=True)
    g = t.pivot_table(index="ceyrek", columns="kova", values="Toplam(Gerçekleşme)",
                      aggfunc="sum", observed=True)
    b2c = (b / g).round(2)

    # ── 5) ÖZET ANAHTARLARI ──────────────────────────────────────────────────
    ay_ad = lambda s: f"{AYLAR[pd.Period(s, freq='M').month]} {pd.Period(s, freq='M').year}"
    oz = {
        "vp_gecmis_son_ay": ay_ad(aylar[len(gecmis_aov) - 1]),
        "vp_gecmis_son_aov": gecmis_aov[sorted(gecmis_aov, key=lambda s: pd.Period(s, freq='M'))[-1]],
        "vp_gecmis_yuv_son": yuv[sorted(gecmis_aov, key=lambda s: pd.Period(s, freq='M'))[-1]],
        "vp_plan_aov_toplam": round(float((yeni["v"] * yeni["ham"]).sum() / yeni["ham"].sum()), 2),
        "vp_eski_takvim": eski_ad,
        "vp_karsilastirma_metin": "",
        "vp_yuv_zirve": max(yuv.values()),
        "vp_yuv_zirve_ay": ay_ad(max(yuv, key=yuv.get)),
    }
    for i, a in enumerate(sorted(aov_yeni, key=lambda s: pd.Period(s, freq="M")), start=1):
        oz[f"vp_plan_ay{i}_ad"] = ay_ad(a)
        oz[f"vp_plan_ay{i}_aov"] = aov_yeni[a]
        if a in aov_eski:
            oz[f"vp_plan_ay{i}_eski_aov"] = aov_eski[a]
            oz[f"vp_plan_ay{i}_fark"] = round(aov_yeni[a] - aov_eski[a], 2)
        oz[f"vp_plan_ay{i}_yuv"] = yuv.get(a)
    kars = []
    for i in (1, 2, 3):
        if f"vp_plan_ay{i}_fark" in oz:
            kars.append(f"{oz[f'vp_plan_ay{i}_ad']} {oz[f'vp_plan_ay{i}_eski_aov']:.2f} → "
                        f"{oz[f'vp_plan_ay{i}_aov']:.2f} yıl "
                        f"({oz[f'vp_plan_ay{i}_fark']:+.2f})".replace(".", ","))
    oz["vp_karsilastirma_metin"] = " · ".join(kars) or "önceki takvim arşivde yok"
    for k, v in maliyet.items():
        tip, kova = k.split("|")
        anahtar = f"vp_maliyet_{tip}_" + {"≤1 yıl": "1a", "1-3 yıl": "1_3", "3-6 yıl": "3_6", "6 yıl+": "6p"}[kova]
        oz[anahtar] = v["maliyet"]
        oz[anahtar + "_mlr"] = v["tutar_mlr"]
    if "vp_maliyet_sabit_1a" in oz and "vp_maliyet_sabit_6p" in oz:
        oz["vp_maliyet_makas_1a_6p"] = round(oz["vp_maliyet_sabit_1a"] - oz["vp_maliyet_sabit_6p"], 2)
    oz["vp_maliyet_pencere_ay"] = MALIYET_PENCERE_AY
    oz["vp_bono_son_ay_mlr"] = round(float(
        hist[(hist["Senet Tanımı"] == "Hazine Bonosu")
             & (hist["ay"] == hist["ay"].max())]["Toplam(Gerçekleşme)"].sum()) / 1000, 1)
    oz["vp_bono_12a_mlr"] = round(float(
        hist[(hist["Senet Tanımı"] == "Hazine Bonosu")
             & (hist["_d"] >= hist["_d"].max() - pd.DateOffset(months=12))]
        ["Toplam(Gerçekleşme)"].sum()) / 1000, 1)
    oz["vp_plan_bono_mlr"] = round(float(
        plan[plan["Senet Tanımı"] == "Hazine Bonosu"]["g"].sum() or 0) / 1000, 1)
    uzun = hist[hist["Vade (Yıl)"] > 6].sort_values("_d")
    if len(uzun):
        r = uzun.iloc[-1]
        oz["vp_son_uzun_tarih"] = str(r["İhale Tarihi"])
        oz["vp_son_uzun_vade"] = round(float(r["Vade (Yıl)"]), 2)
        oz["vp_son_uzun_mlr"] = round(float(r["Toplam(Gerçekleşme)"]) / 1000, 1)
        oz["vp_son_uzun_maliyet"] = round(float(r["Ortalama Yıllık Bileşik(Gerçekleşme)"]), 2)
        oz["vp_uzun_onceki_rekor_mlr"] = round(float(uzun.iloc[:-1]["Toplam(Gerçekleşme)"].max()) / 1000, 1)
    # Planın UZUN UÇ arzı ve tür payları. Yazının "bu arz eğriyi kıpırdatır mı"
    # sorusu buradan cevaplanıyor: planın üç aylık 6 yıl+ arzı, tek bir Ağustos
    # ihalesinin yanında ne kadar kalıyor.
    pl = plan.dropna(subset=["g"]).copy()
    pl["v"] = pl["Vade Terimi"].map(_vade_yil)
    uz = pl[pl["v"] > 6]
    oz["vp_plan_uzun_mlr"] = round(float(uz["g"].sum()) / 1000, 1)
    oz["vp_plan_uzun_adet"] = int(len(uz))
    top = float(pl["g"].sum())
    for ad, kume in (("tlref", DEGISKEN), ("sabit", NOMINAL_SABIT)):
        oz[f"vp_plan_{ad}_pay"] = round(
            float(pl[pl["Senet Tanımı"].isin(kume)]["g"].sum()) / top * 100, 1)
    if eski_yol is not None:
        e1 = eski[eski["ay"] == pd.Period("2026-09", "M")]
        b1 = e1[e1["Senet Tanımı"] == "Hazine Bonosu"]
        if len(b1) and e1["ham"].sum() > 0:
            oz["vp_eski_eylul_bono_pay"] = round(
                float(b1["ham"].sum()) / float(e1["ham"].sum()) * 100, 1)
            oz["vp_eski_eylul_bono_vade"] = round(float(b1["v"].iloc[0]), 2)
    # ── 6) YENİDEN FİYATLAMA VADESİ (duration vekili) ────────────────────────
    # Vade "kâğıt ne zaman itfa olur" der; yeniden fiyatlama "kuponu ne zaman
    # değişir" der. TLREF'e endeksli ve değişken faizli senetlerin kuponu üç
    # ayda bir yenilenir, yani vadesi 4 yıl olsa da faiz duyarlılığı ~0,25
    # yıldır. İkisini ayırmadan "vade uzadı, faiz riski arttı" demek YANLIŞTIR.
    # BU BİR VEKİLDİR, ölçülmüş DV01 değil: kupon yapısı ve stok gerekirdi.
    # Vekilin varsayımı tek satırda ve açıkça durur ki okur payını biçebilsin.
    DEGISKEN_REPRICE = 0.25
    def _reprice(v, tip):
        return DEGISKEN_REPRICE if tip in DEGISKEN else v
    for ad, d_ in (("gecmis", None), ("plan", None)):
        pass
    h6 = hist[hist["ay"] >= pd.Period("2025-09", "M")].copy()
    h6["rp"] = [_reprice(v, t) for v, t in zip(h6["Vade (Yıl)"], h6["Senet Tanımı"])]
    oz["vp_reprice_gecmis"] = round(float(
        (h6["rp"] * h6["Toplam(Gerçekleşme)"]).sum() / h6["Toplam(Gerçekleşme)"].sum()), 2)
    oz["vp_vade_gecmis_ayni_pencere"] = round(float(
        (h6["Vade (Yıl)"] * h6["Toplam(Gerçekleşme)"]).sum() / h6["Toplam(Gerçekleşme)"].sum()), 2)
    pl2 = plan.dropna(subset=["g"]).copy()
    pl2["v"] = pl2["Vade Terimi"].map(_vade_yil)
    pl2["rp"] = [_reprice(v, t) for v, t in zip(pl2["v"], pl2["Senet Tanımı"])]
    oz["vp_reprice_plan"] = round(float((pl2["rp"] * pl2["g"]).sum() / pl2["g"].sum()), 2)
    oz["vp_reprice_varsayim"] = DEGISKEN_REPRICE

    # ── 7) İTFA DUVARI ───────────────────────────────────────────────────────
    # DİKKAT — bu ALT SINIRDIR. Elimizdeki tek itfa kaynağı ihale veri setidir;
    # doğrudan satışlar (kira sertifikası, altın/dolar senetleri), 2019 öncesi
    # ihraçlar ve kupon ödemeleri BU TOPLAMDA YOK. Gerçek itfa yükü daha
    # büyüktür. Sayıyı "işte itfa takvimi" diye sunmak uydurma olurdu; kapsamı
    # yazılarak sunuluyor.
    hist["_it"] = pd.to_datetime(hist["İtfa Tarihi"], dayfirst=True, errors="coerce")
    ileri = hist.dropna(subset=["_it"])
    ileri = ileri[ileri["_it"] > hist["_d"].max()]
    itfa = (ileri.groupby(ileri["_it"].dt.to_period("Q"))["Toplam(Gerçekleşme)"]
            .agg(["sum", "count"]))
    itfa_d = {str(i): {"mlr": round(float(r["sum"]) / 1000, 1), "adet": int(r["count"])}
              for i, r in itfa.iterrows()}
    if itfa_d:
        zirve = max(itfa_d, key=lambda k: itfa_d[k]["mlr"])
        oz["vp_itfa_zirve_ceyrek"] = zirve.replace("Q", " · Ç")
        oz["vp_itfa_zirve_mlr"] = itfa_d[zirve]["mlr"]
        oz["vp_itfa_zirve_adet"] = itfa_d[zirve]["adet"]
        oz["vp_itfa_12a_mlr"] = round(sum(
            v["mlr"] for k, v in itfa_d.items()
            if pd.Period(k, freq="Q").to_timestamp() < hist["_d"].max() + pd.DateOffset(months=12)), 1)

    # ── 8) BONO PAYININ TARİHÇESİ ────────────────────────────────────────────
    aylik_top = hist.groupby("ay")["Toplam(Gerçekleşme)"].sum()
    bono_ay = (hist[hist["Senet Tanımı"] == "Hazine Bonosu"]
               .groupby("ay")["Toplam(Gerçekleşme)"].sum())
    pay = (bono_ay / aylik_top * 100).dropna()
    son24 = pay[pay.index >= hist["ay"].max() - 23]
    oz["vp_bono_pay_24a_ort"] = round(float(son24.mean()), 1)
    oz["vp_bono_pay_son_ay"] = round(float(pay.get(hist["ay"].max(), 0.0)), 1)
    sifir = [str(a) for a in aylik_top.index if a not in bono_ay.index
             and a >= hist["ay"].max() - 23]
    oz["vp_bono_sifir_ay_24a"] = len(sifir)

    # ── 9) UZAMANIN TARİHSEL YERİ ────────────────────────────────────────────
    # 3 aylık yuvarlanan vadedeki 3 aylık değişimin dağılımı: bugünkü sıçrama
    # olağan mı, olağandışı mı? "Vade uzadı" cümlesi ancak bu dağılıma göre
    # anlam kazanır.
    ys = pd.Series({pd.Period(k, freq="M"): v for k, v in yuv.items()}).sort_index()
    gecmis_yuv = ys[ys.index <= pd.Period(sorted(gecmis_aov, key=lambda s: pd.Period(s, freq='M'))[-1], freq="M")]
    d3 = gecmis_yuv.diff(3).dropna()
    plan_d3 = float(ys.get(pd.Period(sorted(aov_yeni)[-1], freq="M"), float("nan"))) - float(gecmis_yuv.iloc[-1])
    oz["vp_uzama_3a"] = round(plan_d3, 2)
    oz["vp_uzama_yuzdelik"] = round(float((d3.abs() <= abs(plan_d3)).mean() * 100), 0)
    oz["vp_uzama_n"] = int(len(d3))
    # ── 10) HEDEF NE KADAR TUTAR: revizyon ve gerçekleşme ────────────────────
    # Planın kendisi bir tahmindir ve iki yerden kayar: Hazine hedefi dokümandan
    # dokümana REVİZE eder, sonra da hedefe tam ulaşmaz. İkisi de ölçülebilir ve
    # ikisi de projeksiyonun güven aralığını belirler.
    sh = KOK / ".strategy_history.json"
    if sh.exists():
        H = json.load(open(sh, encoding="utf-8"))
        revler, surumler_n = [], []
        for ay, e in H.items():
            v = [x["target"] for x in (e.get("history") or [])
                 if isinstance(x, dict) and x.get("target") is not None]
            if len(v) >= 2 and v[0] > 0:
                revler.append((v[-1] - v[0]) / v[0] * 100)
                surumler_n.append(len(v))
        if revler:
            import statistics as st
            oz["vp_rev_n"] = len(revler)
            oz["vp_rev_medyan"] = round(st.median(revler), 1)
            oz["vp_rev_yukari_pay"] = round(sum(1 for x in revler if x > 0) / len(revler) * 100, 0)
            oz["vp_rev_mutlak_ort"] = round(sum(abs(x) for x in revler) / len(revler), 1)
            oz["vp_rev_surum_ort"] = round(sum(surumler_n) / len(surumler_n), 1)
        # Plan aylarının kendi revizyon zinciri (ilk hedeften bugüne)
        for i, ad in enumerate([oz.get(f"vp_plan_ay{k}_ad") for k in (1, 2, 3)], start=1):
            if not ad:
                continue
            v = [x["target"] for x in ((H.get(ad) or {}).get("history") or [])
                 if isinstance(x, dict) and x.get("target") is not None]
            if len(v) >= 2:
                oz[f"vp_rev_ay{i}_zincir"] = " → ".join(
                    f"{x:.1f}".replace(".", ",") for x in v)
                oz[f"vp_rev_ay{i}_surum"] = len(v)
                oz[f"vp_rev_ay{i}_ilk"] = round(v[0], 1)

    gerc = pd.read_csv(KOK / "hazine_hedef_gerceklesme.csv", encoding="utf-8-sig")
    ger = gerc[pd.to_numeric(gerc["Gerçekleşen Borçlanma (Milyar TL)"],
                             errors="coerce") > 0]
    oran = pd.to_numeric(ger["Gerçekleşme Oranı (%)"], errors="coerce").dropna()
    s24 = oran.tail(24)
    oz["vp_gerc_24a_ort"] = round(float(s24.mean()), 1)
    oz["vp_gerc_24a_medyan"] = round(float(s24.median()), 1)
    oz["vp_gerc_24a_min"] = round(float(s24.min()), 1)
    oz["vp_gerc_24a_maks"] = round(float(s24.max()), 1)
    oz["vp_gerc_24a_std"] = round(float(s24.std()), 1)
    oz["vp_gerc_alti_pay"] = round(float((s24 < 100).mean() * 100), 0)

    # ── 11) PLANIN BEKLENEN MALİYETİ ─────────────────────────────────────────
    # Planın tür/vade karması, son dönemde ödenen faizlerle fiyatlanırsa ortaya
    # ne çıkar? Bu bir TAHMİN değil, bir KARMA HESABIDIR: "aynı fiyatlar
    # sürerse bu sepet ne kadara mal olur". Faizler değişirse sayı değişir;
    # amacı seviye öngörmek değil, kompozisyonun maliyet imzasını göstermek.
    def _kova_ad(v):
        return ("1a" if v <= 1 else "1_3" if v <= 3 else "3_6" if v <= 6 else "6p")
    pay_top, agir = 0.0, 0.0
    eksik = []
    for _, r in pl2.iterrows():
        tip = "degisken" if r["Senet Tanımı"] in DEGISKEN else (
            "reel" if r["Senet Tanımı"] in REEL else "sabit")
        k = f"vp_maliyet_{tip}_{_kova_ad(r['v'])}"
        if k in oz:
            agir += oz[k] * r["g"]; pay_top += r["g"]
        else:
            eksik.append(f"{r['Senet Tanımı'][:18]} {r['v']:.1f}y")
    if pay_top > 0:
        oz["vp_plan_maliyet"] = round(agir / pay_top, 2)
        oz["vp_plan_maliyet_kapsam"] = round(pay_top / float(pl2["g"].sum()) * 100, 0)
    if eksik:
        oz["vp_plan_maliyet_eksik"] = "; ".join(sorted(set(eksik)))
        print(f"  ! plan maliyetinde kova karşılığı olmayan satır: {eksik}")

    oz["_tarih"] = hist["_d"].max().strftime("%d.%m.%Y")

    json.dump({"ozet": oz, "gecmis_aov": gecmis_aov, "plan_aov": aov_yeni,
               "eski_aov": aov_eski, "yuvarlanan": yuv, "maliyet": maliyet,
               "b2c": {str(i): {str(c): (None if pd.isna(v) else float(v))
                                for c, v in row.items()} for i, row in b2c.iterrows()}},
              open(KOK / "vade_proj.json", "w"), ensure_ascii=False, indent=1)
    print("yazildi:", KOK / "vade_proj.json")

    _grafikler(gecmis_aov, aov_yeni, aov_eski, yuv, komp, plan_komp, maliyet, b2c, oz,
               itfa_d, h6, pl2)
    print(json.dumps(oz, ensure_ascii=False))
    return 0


def _x(aylar):
    return [pd.Period(a, freq="M").to_timestamp() for a in aylar]


def _grafikler(gecmis, plan_aov, eski_aov, yuv, komp, plan_komp, maliyet, b2c, oz,
               itfa_d=None, h6=None, pl2=None):
    # (1) VADE PATİKASI
    fig = go.Figure()
    ga = sorted(gecmis, key=lambda s: pd.Period(s, freq="M"))
    fig.add_trace(go.Bar(x=_x(ga), y=[gecmis[a] for a in ga], name="Gerçekleşen (aylık)",
                         marker_color=GRI, opacity=0.55,
                         hovertemplate="Gerçekleşen: %{y:.2f} yıl<extra></extra>"))
    pa = sorted(plan_aov, key=lambda s: pd.Period(s, freq="M"))
    fig.add_trace(go.Bar(x=_x(pa), y=[plan_aov[a] for a in pa], name="Planlı (yeni strateji)",
                         marker_color=CLARET,
                         hovertemplate="Plan: %{y:.2f} yıl<extra></extra>"))
    if eski_aov:
        ea = sorted(eski_aov, key=lambda s: pd.Period(s, freq="M"))
        fig.add_trace(go.Scatter(x=_x(ea), y=[eski_aov[a] for a in ea], mode="markers",
                                 name="Önceki stratejinin aynı ayı",
                                 marker=dict(color=GOLD, size=13, symbol="diamond-open",
                                             line=dict(width=2.4)),
                                 hovertemplate="Önceki strateji: %{y:.2f} yıl<extra></extra>"))
    ya = sorted(yuv, key=lambda s: pd.Period(s, freq="M"))
    fig.add_trace(go.Scatter(x=_x(ya), y=[yuv[a] for a in ya], mode="lines",
                             name="3 aylık yuvarlanan (hacim ağırlıklı)",
                             line=dict(color=TEAL, width=2.6),
                             hovertemplate="3 aylık: %{y:.2f} yıl<extra></extra>"))
    fig.add_vline(x=pd.Timestamp("2026-09-01"), line=dict(color=INK, width=1, dash="dot"))
    fig.add_annotation(x=pd.Timestamp("2026-09-01"), y=1.02, yref="paper",
                       text="plan başlıyor", showarrow=False, font=dict(size=11, color=GRI),
                       xanchor="left")
    ortak_stil(fig, "Ağırlıklı ortalama ihraç vadesi: gerçekleşen, plan ve karşı olgu")
    fig.update_yaxes(title_text="Yıl")
    fig.write_html(KOK / "vade_patika.html", include_plotlyjs="cdn")

    # (2) KOMPOZİSYON
    fig = go.Figure()
    tum = list(dict.fromkeys(list(komp.columns) + list(plan_komp.columns)))
    xs = _x([str(a) for a in komp.index]) + _x([str(a) for a in plan_komp.index])
    for tip in tum:
        y = ([float(komp[tip].get(a, 0)) / 1000 if tip in komp.columns else 0 for a in komp.index]
             + [float(plan_komp[tip].get(a, 0)) / 1000 if tip in plan_komp.columns else 0
                for a in plan_komp.index])
        fig.add_trace(go.Bar(x=xs, y=y, name=tip, marker_color=TIP_RENK.get(tip, GRI),
                             hovertemplate=tip + ": %{y:.1f} mlr TL<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.add_vline(x=pd.Timestamp("2026-09-01"), line=dict(color=INK, width=1, dash="dot"))
    ortak_stil(fig, "İhraç kompozisyonu: gerçekleşen aylar ve planlı takvim (milyar TL)")
    fig.update_yaxes(title_text="Milyar TL")
    fig.write_html(KOK / "vade_kompozisyon.html", include_plotlyjs="cdn")

    # (3) MALİYET EĞRİSİ
    fig = go.Figure()
    for tip, ad, renk in (("sabit", "Nominal sabit (bono + sabit kuponlu)", CLARET),
                          ("degisken", "Değişken/TLREF endeksli", TEAL)):
        ks = [k for k in maliyet if k.startswith(tip + "|")]
        ks.sort(key=lambda k: KOVA_AD.index(k.split("|")[1]))
        if not ks:
            continue
        fig.add_trace(go.Bar(
            x=[k.split("|")[1] for k in ks], y=[maliyet[k]["maliyet"] for k in ks],
            name=ad, marker_color=renk,
            text=[f"%{tr(maliyet[k]['maliyet'], 2)}<br>{tr(maliyet[k]['tutar_mlr'], 0)} mlr"
                  for k in ks], textposition="outside",
            hovertemplate="%{x}: %%%{y:.2f} · <extra></extra>"))
    fig.update_layout(barmode="group")
    ortak_stil(fig, f"Hazine'nin ÖDEDİĞİ bileşik faiz, vade kovasına göre "
                    f"(son {MALIYET_PENCERE_AY} ay, tutar ağırlıklı)", hovermode="closest")
    fig.update_yaxes(title_text="Yıllık bileşik %")
    fig.write_html(KOK / "vade_maliyet.html", include_plotlyjs="cdn")

    # (4) TALEP
    fig = go.Figure()
    for kova, renk in zip(KOVA_AD, (GOLD, SLATE, TEAL, CLARET)):
        if kova not in b2c.columns:
            continue
        fig.add_trace(go.Scatter(x=[p.to_timestamp() for p in b2c.index],
                                 y=b2c[kova], mode="lines+markers", name=kova,
                                 line=dict(color=renk, width=2.4),
                                 hovertemplate=kova + ": %{y:.2f}x<extra></extra>"))
    fig.add_hline(y=2.0, line=dict(color=GRI, width=1, dash="dash"))
    ortak_stil(fig, "Talep derinliği: bid-to-cover, vade kovası × çeyrek")
    fig.update_yaxes(title_text="Teklif / Satış (x)")
    fig.write_html(KOK / "vade_talep.html", include_plotlyjs="cdn")

    # (5) İTFA DUVARI
    if itfa_d:
        ks = sorted(itfa_d, key=lambda k: pd.Period(k, freq="Q"))[:8]
        fig = go.Figure(go.Bar(
            x=[pd.Period(k, freq="Q").to_timestamp() for k in ks],
            y=[itfa_d[k]["mlr"] for k in ks], marker_color=SLATE,
            text=[f"{itfa_d[k]['adet']} kâğıt" for k in ks], textposition="outside",
            hovertemplate="%{y:.1f} mlr TL<extra></extra>"))
        ortak_stil(fig, "İtfa duvarı — çeyreklik (YALNIZ ihale ihraçları; alt sınır)",
                   hovermode="closest")
        fig.update_yaxes(title_text="Milyar TL")
        fig.write_html(KOK / "vade_itfa.html", include_plotlyjs="cdn")

    # (6) VADE vs YENİDEN FİYATLAMA
    if h6 is not None and pl2 is not None:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["Son 12 ay (gerçekleşen)", "Planlı takvim"],
                             y=[oz["vp_vade_gecmis_ayni_pencere"], oz["vp_plan_aov_toplam"]],
                             name="Ağırlıklı ortalama VADE", marker_color=CLARET,
                             text=[f"{tr(oz['vp_vade_gecmis_ayni_pencere'], 2)} yıl",
                                   f"{tr(oz['vp_plan_aov_toplam'], 2)} yıl"],
                             textposition="outside"))
        fig.add_trace(go.Bar(x=["Son 12 ay (gerçekleşen)", "Planlı takvim"],
                             y=[oz["vp_reprice_gecmis"], oz["vp_reprice_plan"]],
                             name="Ağırlıklı YENİDEN FİYATLAMA vadesi (vekil)",
                             marker_color=TEAL,
                             text=[f"{tr(oz['vp_reprice_gecmis'], 2)} yıl",
                                   f"{tr(oz['vp_reprice_plan'], 2)} yıl"],
                             textposition="outside"))
        fig.update_layout(barmode="group")
        ortak_stil(fig, "Vade uzuyor, faiz duyarlılığı uzamıyor "
                        "(değişken kuponlular 0,25 yıl sayıldı)", hovermode="closest")
        fig.update_yaxes(title_text="Yıl")
        fig.write_html(KOK / "vade_reprice.html", include_plotlyjs="cdn")
    print("grafikler yazildi: vade_patika, vade_kompozisyon, vade_maliyet, vade_talep, "
          "vade_itfa, vade_reprice")


if __name__ == "__main__":
    raise SystemExit(main())
