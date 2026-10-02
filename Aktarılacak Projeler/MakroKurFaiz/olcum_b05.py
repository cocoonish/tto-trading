#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — Bölüm 5 ölçüm katmanı: bütçe açığı I, DM'de faiz
kanalı ve politika bileşimi.

Pratikler
  p5a  ABD 2023 ayılı dikleşmesi (31.07 → 19.10.2023): 2 yıllık, 10 yıllık ve
       2s10s değişimi; NY Fed ACM vade primi paneli (10 yıllık vade primi ile
       risk-nötr getirinin ayrışımı).
  p5b  Türkiye mali impuls vekili: −Δ(faiz dışı denge/GSYH), dört çeyrek fark,
       2007Ç4–2026Ç2; deprem ve KKM dönemleri adıyla; Bölüm 3'ün çıktı açığı
       bandı ve 0,3–0,5 yarı esneklik varsayımıyla yapısal faiz dışı denge ARALIĞI.
  p5c  Türkiye "beklenti dışı fark" (vade primi vekili), günlük → aylık:
       1y1y forward − PKA 12–24 ay patikasının yamuk ortalaması (yıllık bileşiğe
       çevrilmiş); üç kirlilik kalemi (koridor farkı, DİBS–TLREF bazı, anketin ay
       etiketi) ayrı ölçülür.
  sekil_07  DM mali olay kadranı (olay tablosu: Δ2y, Δ10y, Δdolar sepeti, VIX,
            ACM vade primi; İngiltere 2022 gilt ve sterlin).
  sekil_08  Türkiye beklenti dışı farkı, aylık.

Bölüm modülleri: b01'in ABD ortak gün çerçevesi ve kadran kuralı, b03'ün çıktı
açığı ve Türkiye iş günü takvimi içe aktarılır (b01 ve b03 bu modülü içe
aktarmaz; döngü yok). Aynı ölçü iki modülde iki ayrı kodla kurulmaz.

ÖLÇÜM TUZAKLARI (bu modül yazılırken ölçüldü)
1. AYNI GÜNÜN İKİ KAPANIŞI. ABD Hazinesi par getirisi New York öğleden sonra
   kotasyonudur (≈15:30), CNBC kurları New York 17:00. Kapanıştan sonra
   açıklanan bir haberde (2 Nisan 2025 tarife duyurusu 16:00 New York; Moody's
   16.05.2025 cuma hisse kapanışından sonra) başlangıç gününün kur kapanışı ilk
   tepkinin bir kısmını zaten taşıyabilir, getiri taşımaz: 02.04.2025'te dolar
   sepeti bir önceki güne göre −%0,42 iken 10 yıllık +3 bp. Pencerenin başı kurda
   tepkiyi kısmen yutar; olay satırında adıyla yazılır.
2. FITCH TEPKİ GÜNÜ İKİ HABER TAŞIR. Not indirimi 01.08.2023 ABD kapanışından
   sonra geldi, tepki 02.08 kapanışındadır; aynı gün ABD Hazinesi'nin üç aylık
   borçlanma açıklaması da (ihale büyüklüklerinin artırılması) yapıldı. 01.08 →
   02.08 penceresi iki haberi ayrıştıramaz; "Fitch etkisi" olarak okunmaz.
3. ACM GETİRİSİ PAR GETİRİ DEĞİLDİR. ACM sıfır kuponlu bir eğri üzerinde
   kestirilir; 10 yıllık model getirisinin par getiriden farkı pencerede
   küçüktür ama sıfır değildir (satırda yazılı). Vade primi + risk-nötr getiri =
   model getirisi özdeşliği her gün sınanır.
4. TÜRKİYE TAKVİMİ VE DİBS ETİKETİ. DİBS eğrisi tatillerde de satır taşır
   (Bölüm 1, tuzak 1); fark serisi Türkiye iş günlerine (fonlama ∩ DİBS)
   indirilir. DİBS etiketi piyasa gününden iki iş günü öndedir (Bölüm 2) ve bu
   AYLIK ORTALAMADA DA YOK SAYILAMAZ: kaydırmasız seri kaydırılmış seriden ayda
   ortalama 16 bp, en çok 99 bp ayrışıyor (oynak aylarda ay sınırına düşen iki
   günün ağırlığı büyük). Ana seri piyasa gününe kaydırılmış DİBS'le kurulur;
   TLREF ve AOFM zaten piyasa günü tarihlidir. Bu yüzden son ölçüm günü 28.09'dur
   (30.09 etiketi 28.09 piyasasıdır); kaydırmasız seri duyarlılık satırındadır.
5. ANKETİN GÜNLÜK HÂLİ BİR VARSAYIMDIR. Günlük seride anket ayın 20'sinden (ya
   da sonraki ilk iş gününden) itibaren geçerli sayılır; yayım günü arşivde
   yok. Günlük değer, aylık dosyayla 20'sinden sonraki ilk gözlemde
   karşılaştırılır (sınama satırı) ve ay etiketinin kirliliği iki biçimde
   ölçülür: (i) anketi ayın ilk gününden geçerli sayan karşı hizalama, (ii) bir
   aylık kaymanın patikayı ne kadar oynattığı ((24 ay − 12 ay)/12).
6. 2018 HAZİRAN ÖNCESİ BİR HAFTA VADELİ REPO ETKİN FAİZ DEĞİLDİ (Bölüm 3, tuzak
   5): anket politika faizini (bir hafta vadeli repo) sorar, piyasa ise etkin
   fonlama maliyetini fiyatlar. Koridor farkı (AOFM − politika) bu yüzden ayrı
   kirlilik kalemidir; 2018-09 öncesinde politika faizi BIS'in ay sonu
   değeridir (günlük seri 14.09.2018'de başlar).
7. TLREF BASİT, DİBS BİLEŞİK. TLREF basit faiz (ACT/365) olarak yayımlanır;
   3 aylık sıfır kuponlu getiri yıllık bileşiktir. Baz, TLREF günlük bileşiğe
   çevrildikten sonra alınır. 3 aylık vade kendi içinde üç aylık politika
   beklentisini de taşır: baz saf bir fiyat farkı değildir. Üstelik 3 aylık
   düğüm eğrinin en gürültülü noktasıdır: 2024'te günlük değişiminin σ'sı
   TLREF'inkinin iki katından fazla, düğüm haftalarca aynı değerde donup tek
   günde yüzlerce baz puan sıçrıyor (02.09 → 03.09.2024 etiketinde 39,99'dan
   56,67'ye). Baz, fiyat farkıyla birlikte düğümün kuruluş artefaktını taşır.
   Ayrıca 2025-01…2026-09'da düğümün BİLEŞİK değeri TLREF'in BASİT değerini
   neredeyse birebir izliyor (ortalama fark birkaç on baz puan; bileşiğe göre
   ≈ −10 puan). Bu ya gerçek bir fiyat farkıdır ya kısa düğümün sözleşmesinde bir
   sorundur; bu arşivden ayırt edilemez, satırda tanı olarak durur.
8. MALİ İMPULS VEKİLİ MERKEZİ YÖNETİM NAKİT DENGESİDİR (genel yönetim değil;
   tahakkuk değil). 2023 deprem dönemi, Mayıs 2023 seçimleriyle aynı yıla
   düşer: impulsun deprem harcamasına ayrılan kısmı bu arşivden ölçülemez,
   dönem yalnız işaretlenir. KKM'nin bütçe maliyeti de ayrı kalem değildir.
9. YARI ESNEKLİK BİR KAYNAK İDDİASIDIR (0,3–0,5). Ölçüm katmanı onu yeniden
   kestirmez; yapısal denge, iki çıktı açığı sürümü × iki esneklik ucunun
   oluşturduğu bir ARALIK olarak yazılır.
"""
from __future__ import annotations

import math
import warnings

import numpy as np
import pandas as pd

import bulut
import olcum_b01 as b01
import olcum_b03 as b3
import ortak_olc as oo

warnings.filterwarnings("ignore", category=FutureWarning)
try:
    warnings.filterwarnings("ignore", category=pd.errors.Pandas4Warning)  # type: ignore[attr-defined]
except AttributeError:
    pass

# ───────────────────────────────────────────────────────── sabitler (adlı)
P5A_BAS, P5A_SON = "2023-07-31", "2023-10-19"

# Olay penceresi: "baslangic" olay öncesi kapanış günüdür (işlem günü değilse ondan
# önceki son işlem günü), "bitis" pencerenin son kapanışıdır (işlem günü değilse
# sonraki ilk işlem günü). Haber kapanıştan sonra geldiyse başlangıç o günün kendisidir.
OLAYLAR_ABD = [
    {"kimlik": "abd_2016_secim", "ad": "ABD 2016 seçimi → Aralık FOMC artırımı",
     "baslangic": "2016-11-08", "bitis": "2016-12-15",
     "saat_notu": "Seçim sonuçları 08.11 ABD kapanışından sonra geldi; pencere 08.11 kapanışından başlar."},
    {"kimlik": "abd_2017_vergi", "ad": "ABD 2017 vergi yasası (karşı örnek)",
     "baslangic": "2017-11-01", "bitis": "2017-12-22",
     "saat_notu": "Tasarı 02.11 seans içinde açıklandı; pencere bir önceki kapanıştan (01.11) yasanın "
                  "imzalandığı 22.12'ye kadardır."},
    {"kimlik": "abd_2023_agustos", "ad": "ABD Ağustos 2023: borçlanma duyuruları ve Fitch",
     "baslangic": "2023-07-31", "bitis": "2023-08-04",
     "saat_notu": "Pencere 31.07 kapanışından başlar; Fitch not indirimi 01.08 ABD kapanışından sonra "
                  "açıklandı, tepkisi 02.08 kapanışındadır."},
    {"kimlik": "abd_2023_fitch_gunu", "alt": True, "ad": "ABD 02.08.2023 tepki günü (Fitch + üç aylık borçlanma açıklaması)",
     "baslangic": "2023-08-01", "bitis": "2023-08-02",
     "saat_notu": "Fitch'in tepki günü aynı zamanda ABD Hazinesi'nin üç aylık borçlanma açıklamasının "
                  "günüdür: iki haber tek pencerede, ayrıştırılamaz."},
    {"kimlik": "abd_2025_tarife", "ad": "ABD Nisan 2025 tarife duyurusu",
     "baslangic": "2025-04-02", "bitis": "2025-04-11",
     "saat_notu": "Duyuru 02.04 16:00 New York: getiri kapanışından sonra, CNBC 17:00 kur kapanışından "
                  "önce. Başlangıç günü kur kapanışı ilk tepkinin bir kısmını taşır; kur değişimi tepkiyi "
                  "eksik ölçer."},
    {"kimlik": "abd_2025_moodys_1g", "ad": "ABD Moody's not indirimi (16.05.2025) → ilk iş günü",
     "baslangic": "2025-05-16", "bitis": "2025-05-19",
     "saat_notu": "Not indirimi 16.05 cuma hisse kapanışından sonra açıklandı; getiri kapanışı "
                  "açıklamadan öncedir. CNBC 17:00 kur kapanışının açıklamadan önce mi sonra mı olduğu "
                  "bu arşivden ölçülemez."},
    {"kimlik": "abd_2025_moodys_3g", "alt": True, "ad": "ABD Moody's not indirimi (16.05.2025) → üçüncü iş günü",
     "baslangic": "2025-05-16", "bitis": "2025-05-21",
     "saat_notu": "Aynı başlangıç; pencere 21.05 kapanışına uzatıldı (aynı hafta 20 yıllık tahvil "
                  "ihalesi de bu pencereye düşer)."},
]
OLAYLAR_IGB = [
    {"kimlik": "igb_2022_mini_butce", "ad": "İngiltere Eylül 2022 mini bütçe → BoE müdahalesi",
     "baslangic": "2022-09-22", "bitis": "2022-09-28",
     "saat_notu": "Gilt getirileri Londra kapanışı (CNBC), sterlin CNBC New York 17:00: aynı günün iki "
                  "kapanışı arasında beş saat var. 28.09 BoE'nin uzun vadeli gilt alım duyurusunu taşır."},
    {"kimlik": "igb_2022_zirve", "alt": True, "ad": "İngiltere Eylül 2022 → BoE müdahalesinden önceki son kapanış",
     "baslangic": "2022-09-22", "bitis": "2022-09-27",
     "saat_notu": "Aynı başlangıç; bitiş BoE müdahalesinden önceki son kapanış."},
]

# 06.02.2023 depremi: depremin ardından iki takvim yılı işaretlenir (dönem işareti;
# harcamanın zaman profili bu arşivde ölçülemez).
DEPREM_DONEM = (pd.Period("2023Q1", "Q"), pd.Period("2024Q4", "Q"))
YARI_ESNEKLIK = (0.3, 0.5)          # kaynak iddiası, ölçüm değil
ANKET_HAFTA = 52                     # bir hafta vadeli repo (basit) → yıllık bileşik: (1 + r/52)^52 − 1
AYLIK_ASGARI_GUN = 5                 # aylık ortalamaya giren ay için asgari gün
POLITIKA_GUNLUK_ILK = pd.Timestamp("2018-09-14")

KAYNAK_ABD = ["abd_hazine_gunluk", "cnbc_kur_gunluk", "yahoo_dxy_vix_gunluk"]


# ───────────────────────────────────────────────────────── küçük yardımcılar
def _iso(t) -> str | None:
    if t is None:
        return None
    if isinstance(t, pd.Period):
        return str(t)
    try:
        return str(pd.Timestamp(t).date())
    except (ValueError, TypeError):
        return str(t)


def _f(x) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def kurulmadi(sebep: str, **ek) -> dict:
    return b3.kurulmadi(sebep, **ek)


def _bas_gun(idx: pd.DatetimeIndex, t) -> pd.Timestamp | None:
    """Olay öncesi kapanış: t'ye eşit ya da ondan önceki son işlem günü."""
    j = idx.searchsorted(pd.Timestamp(t), side="right") - 1
    return idx[j] if j >= 0 else None


def _son_gun(idx: pd.DatetimeIndex, t) -> pd.Timestamp | None:
    """Pencere sonu: t'ye eşit ya da ondan sonraki ilk işlem günü."""
    j = idx.searchsorted(pd.Timestamp(t), side="left")
    return idx[j] if j < len(idx) else None


def _kadran(dfaiz: float, dpara_deger: float) -> str:
    """Bölüm 1'in kadran kuralı (DM): politika · prim · gevşeme · güvenli liman."""
    return str(b01._kadran(pd.Series([dfaiz]), pd.Series([dpara_deger]), "guvenli_liman").iloc[0])


# ═══════════════════════════════════════════════════════════════ p5a
def p5a() -> dict:
    a = oo.oku("abd_hazine_gunluk")[["us2", "us10"]].dropna()
    a = a[a.index.dayofweek < 5]
    b, s = _bas_gun(a.index, P5A_BAS), _son_gun(a.index, P5A_SON)
    w = a.loc[b:s]
    d2 = (a.loc[s, "us2"] - a.loc[b, "us2"]) * 100
    d10 = (a.loc[s, "us10"] - a.loc[b, "us10"]) * 100
    egim_b = (a.loc[b, "us10"] - a.loc[b, "us2"]) * 100
    egim_s = (a.loc[s, "us10"] - a.loc[s, "us2"]) * 100
    j_zirve = w["us10"].idxmax()
    out = {
        "n": int(len(w)), "ilk": _iso(b), "son": _iso(s),
        "yontem": "ABD Hazinesi'nin 2 ve 10 yıllık par getirisinin 31 Temmuz 2023 kapanışından 19 Ekim 2023 "
                  "kapanışına değişimi baz puan olarak alındı; eğim 10 yıllık eksi 2 yıllıktır.",
        "kaynak": ["abd_hazine_gunluk"],
        "us2_bas": _f(a.loc[b, "us2"]), "us2_son": _f(a.loc[s, "us2"]),
        "us10_bas": _f(a.loc[b, "us10"]), "us10_son": _f(a.loc[s, "us10"]),
        "d_us2_bp": _f(d2), "d_us10_bp": _f(d10),
        "egim_2s10s_bas_bp": _f(egim_b), "egim_2s10s_son_bp": _f(egim_s),
        "d_2s10s_bp": _f(egim_s - egim_b),
        "us10_zirve": _f(w["us10"].max()), "us10_zirve_gunu": _iso(j_zirve),
        "diklesme_turu": ("ayılı dikleşme" if d10 > 0 and egim_s > egim_b else
                          "boğa dikleşme" if d10 < 0 and egim_s > egim_b else "dikleşme değil"),
    }
    try:
        m = bulut.acm()
    except bulut.VeriYok as e:
        out["vade_primi"] = kurulmadi(f"NY Fed ACM vade primi: {e}")
        return out
    m = m[m.index.dayofweek < 5]
    bm, sm = _bas_gun(m.index, b), _son_gun(m.index, s)
    if bm is None or sm is None or bm != b or sm != s:
        out["vade_primi"] = kurulmadi("ACM serisi pencerenin uç günlerini taşımıyor")
        return out
    wm = m.loc[bm:sm]
    ozdes = (m["acmy10"] - m["acmrny10"] - m["acmtp10"]).loc["2000":].abs().max() * 100
    dtp10 = (m.loc[sm, "acmtp10"] - m.loc[bm, "acmtp10"]) * 100
    drn10 = (m.loc[sm, "acmrny10"] - m.loc[bm, "acmrny10"]) * 100
    dy10 = (m.loc[sm, "acmy10"] - m.loc[bm, "acmy10"]) * 100
    dtp2 = (m.loc[sm, "acmtp02"] - m.loc[bm, "acmtp02"]) * 100
    dtp5 = (m.loc[sm, "acmtp05"] - m.loc[bm, "acmtp05"]) * 100
    ortak = pd.concat([a["us10"], m["acmy10"]], axis=1, sort=True).dropna().loc[bm:sm]
    par_model = (ortak["us10"] - ortak["acmy10"]) * 100
    out["vade_primi"] = {
        "n": int(len(wm)), "ilk": _iso(bm), "son": _iso(sm),
        "yontem": "NY Fed'in Adrian–Crump–Moench modeli 10 yıllık getiriyi risk-nötr getiri (beklenen kısa faiz "
                  "patikası) ile vade primine ayırır; iki bileşenin aynı pencerede değişimi baz puan olarak alındı.",
        "kaynak": ["bulut: acm"],
        "acmtp10_bas": _f(m.loc[bm, "acmtp10"]), "acmtp10_son": _f(m.loc[sm, "acmtp10"]),
        "d_acmtp10_bp": _f(dtp10), "d_acmrny10_bp": _f(drn10), "d_acmy10_bp": _f(dy10),
        "d_acmtp02_bp": _f(dtp2), "d_acmtp05_bp": _f(dtp5),
        "vade_primi_payi": _f(dtp10 / dy10) if dy10 else None,
        "ozdeslik_azami_sapma_bp": _f(ozdes),
        "par_eksi_model_10y_ort_bp": _f(par_model.mean()),
        "par_eksi_model_10y_azami_mutlak_bp": _f(par_model.abs().max()),
        "not": "Model getirisi sıfır kuponlu eğriden gelir; par getiriyle farkı ayrıca yazılı (tuzak 3).",
    }
    seri = pd.concat([w, m[["acmtp10", "acmrny10"]]], axis=1, sort=True).loc[b:s].dropna()
    out["seri"] = {"tarih": [_iso(t) for t in seri.index],
                   "us2": [_f(v) for v in seri["us2"]], "us10": [_f(v) for v in seri["us10"]],
                   "acmtp10": [_f(v) for v in seri["acmtp10"]], "acmrny10": [_f(v) for v in seri["acmrny10"]]}
    return out


# ═══════════════════════════════════════════════════════════════ sekil_07
def _acm_degisim(b: pd.Timestamp, s: pd.Timestamp) -> dict:
    try:
        m = bulut.acm()
    except bulut.VeriYok as e:
        return {"vade_primi": kurulmadi(f"NY Fed ACM vade primi: {e}")}
    m = m[m.index.dayofweek < 5]
    if b not in m.index or s not in m.index:
        return {"vade_primi": kurulmadi("ACM serisi pencerenin uç günlerini taşımıyor")}
    return {"d_acmtp10_bp": _f((m.loc[s, "acmtp10"] - m.loc[b, "acmtp10"]) * 100),
            "d_acmrny10_bp": _f((m.loc[s, "acmrny10"] - m.loc[b, "acmrny10"]) * 100)}


def _olay_abd(o: dict, f: pd.DataFrame) -> dict:
    b, s = _bas_gun(f.index, o["baslangic"]), _son_gun(f.index, o["bitis"])
    w = f.loc[b:s]
    d2 = (f.loc[s, "us2"] - f.loc[b, "us2"]) * 100
    d10 = (f.loc[s, "us10"] - f.loc[b, "us10"]) * 100
    ddol = (f.loc[s, "sepet"] - f.loc[b, "sepet"]) * 100
    r = {
        "kimlik": o["kimlik"], "ad": o["ad"], "ulke": "ABD",
        "ilk": _iso(b), "son": _iso(s), "n_gun": int(len(w) - 1),
        "tepki_gunu": _iso(f.index[f.index > b][0]),
        "d_us2_bp": _f(d2), "d_us10_bp": _f(d10), "d_2s10s_bp": _f(d10 - d2),
        "d_dolar_yuzde": _f(ddol),
        "vix_bas": _f(f.loc[b, "vix"]), "vix_son": _f(f.loc[s, "vix"]),
        "d_vix_puan": _f(f.loc[s, "vix"] - f.loc[b, "vix"]), "vix_azami": _f(w["vix"].max()),
        "kadran": _kadran(d10, ddol),
        "uzun_uc_baskin": bool(abs(d10) > abs(d2)),
        "alt_pencere": bool(o.get("alt", False)),
        "saat_notu": o["saat_notu"],
    }
    r.update(_acm_degisim(b, s))
    return r


def _olay_igb(o: dict) -> dict:
    try:
        g = bulut.gilt()
    except bulut.VeriYok as e:
        return {"kimlik": o["kimlik"], "ad": o["ad"], **kurulmadi(f"gilt getirileri: {e}")}
    k = oo.oku("cnbc_kur_gunluk")["gbp"]
    v = oo.oku("yahoo_dxy_vix_gunluk")["vix"]
    a = oo.oku("abd_hazine_gunluk")["us10"]
    f = pd.concat([g[["gb2y", "gb10y", "gb30y"]], np.log(k).rename("lgbp")], axis=1, sort=True).dropna()
    f = f[f.index.dayofweek < 5]
    b, s = _bas_gun(f.index, o["baslangic"]), _son_gun(f.index, o["bitis"])
    d = {c: (f.loc[s, c] - f.loc[b, c]) * 100 for c in ("gb2y", "gb10y", "gb30y")}
    dgbp = (f.loc[s, "lgbp"] - f.loc[b, "lgbp"]) * 100
    w = f.loc[b:s]
    return {
        "kimlik": o["kimlik"], "ad": o["ad"], "ulke": "İngiltere",
        "ilk": _iso(b), "son": _iso(s), "n_gun": int(len(w) - 1),
        "d_gb2y_bp": _f(d["gb2y"]), "d_gb10y_bp": _f(d["gb10y"]), "d_gb30y_bp": _f(d["gb30y"]),
        "gb30y_azami": _f(w["gb30y"].max()), "gb30y_azami_gunu": _iso(w["gb30y"].idxmax()),
        "d_sterlin_yuzde": _f(dgbp),
        "d_us10_bp": _f((a.asof(s) - a.asof(b)) * 100),
        "vix_bas": _f(v.asof(b)), "vix_son": _f(v.asof(s)),
        "kadran": _kadran(d["gb10y"], dgbp),
        "uzun_uc_baskin": bool(abs(d["gb10y"]) > abs(d["gb2y"])),
        "alt_pencere": bool(o.get("alt", False)),
        "saat_notu": o["saat_notu"],
    }


def sekil_07() -> dict:
    f = b01._abd_gunluk()
    satirlar = [_olay_abd(o, f) for o in OLAYLAR_ABD] + [_olay_igb(o) for o in OLAYLAR_IGB]
    gecerli = [r for r in satirlar if "kadran" in r]
    ana = [r for r in gecerli if not r["alt_pencere"]]
    say = {}
    for r in ana:
        say[r["kadran"]] = say.get(r["kadran"], 0) + 1
    return {
        "n": int(len(ana)), "n_satir": int(len(gecerli)),
        "ilk": min(r["ilk"] for r in gecerli), "son": max(r["son"] for r in gecerli),
        "durum": "vaka tablosu",
        "not": "On olaydan az bağımsız gözlem: test istatistiği yazılmaz; satırlar kadrana yerleştirilir. Alt "
               "pencereler (aynı olayın tek gün ya da uzatılmış hâli) kadran sayımına girmez.",
        "uzun_uc_kurali": "Uzun uç baskın: 10 yıllık getirinin mutlak değişimi 2 yıllığınkini aşıyor.",
        "saat_sozlesmesi": "ABD getirisi New York öğleden sonra kotasyonu (≈15:30), G10 kurları New York 17:00, VIX "
                           "New York kapanışı; gilt Londra kapanışı. Kapanıştan sonra gelen haberde ilk gün kuru "
                           "tepkinin bir kısmını taşıyabilir (satırdaki saat notu).",
        "yontem": "Her olayda olay öncesi kapanıştan pencerenin son kapanışına 2 ve 10 yıllık getiri değişimi "
                  "(baz puan), altı G10 kurunun dolar yönünde eşit ağırlıklı ortalamasının değişimi (yüzde) ve "
                  "VIX alındı; kadran uzun faizin ve paranın değerinin birlikte yönüdür (politika: faiz ↑ para ↑, "
                  "prim: faiz ↑ para ↓, güvenli liman: faiz ↓ para ↑, gevşeme: faiz ↓ para ↓).",
        "kaynak": KAYNAK_ABD + ["bulut: acm", "bulut: gilt"],
        "kadran_sayisi": say,
        "olaylar": satirlar,
        "pencere_tablosu": [{"kimlik": o["kimlik"], "baslangic": o["baslangic"], "bitis": o["bitis"]}
                            for o in OLAYLAR_ABD + OLAYLAR_IGB],
    }


# ═══════════════════════════════════════════════════════════════ p5b
def _impuls_cercevesi() -> pd.DataFrame:
    c = oo.oku("butce_ceyreklik")
    fdd = c["fdd_gsyh"].dropna()
    fdd.index = pd.PeriodIndex(fdd.index, freq="Q")
    q = pd.period_range(fdd.index.min(), fdd.index.max(), freq="Q")
    fdd = fdd.reindex(q)
    gap = b3.cikti_acigi()
    gap4 = gap.rolling(4).mean().reindex(q)          # 12 aylık akımla aynı dört çeyrek
    df = pd.DataFrame({"fdd": fdd, "impuls": -(fdd - fdd.shift(4)),
                       "acik_tam": gap4["tam"], "acik_rt": gap4["gercek_zamanli"]}, index=q)
    yap, imp = [], []
    for e in YARI_ESNEKLIK:
        for g in ("acik_tam", "acik_rt"):
            ad = f"yfdd_{g}_{e}"
            df[ad] = df["fdd"] - e * df[g]
            df[f"yimp_{g}_{e}"] = -(df[ad] - df[ad].shift(4))
            yap.append(ad)
            imp.append(f"yimp_{g}_{e}")
    df["yfdd_alt"], df["yfdd_ust"] = df[yap].min(axis=1), df[yap].max(axis=1)
    df["yimp_alt"], df["yimp_ust"] = df[imp].min(axis=1), df[imp].max(axis=1)
    kkm = oo.oku("kkm_aylik")
    kkm_q = set(pd.PeriodIndex(kkm.index, freq="Q"))
    df["deprem"] = [(DEPREM_DONEM[0] <= p <= DEPREM_DONEM[1]) for p in q]
    df["kkm"] = [p in kkm_q for p in q]
    return df


def p5b() -> dict:
    df = _impuls_cercevesi()
    x = df.dropna(subset=["impuls"])
    kkm = oo.oku("kkm_aylik")
    son = x.index.max()

    def satir(p) -> dict:
        r = df.loc[p]
        return {"ceyrek": str(p), "fdd_gsyh": _f(r["fdd"]), "impuls_puan": _f(r["impuls"]),
                "acik_tam": _f(r["acik_tam"]), "acik_gercek_zamanli": _f(r["acik_rt"]),
                "yapisal_fdd_alt": _f(r["yfdd_alt"]), "yapisal_fdd_ust": _f(r["yfdd_ust"]),
                "yapisal_impuls_alt_puan": _f(r["yimp_alt"]), "yapisal_impuls_ust_puan": _f(r["yimp_ust"]),
                "deprem_donemi": bool(r["deprem"]), "kkm_donemi": bool(r["kkm"])}

    yillik = [satir(p) for p in x.index if p.quarter == 4]
    if son.quarter != 4:
        yillik.append(satir(son))
    dep = x[x["deprem"]]
    kk = x[x["kkm"]]
    diger = x[~x["deprem"] & ~x["kkm"]]
    return {
        "n": int(len(x)), "ilk": str(x.index.min()), "son": str(son),
        "yontem": "Mali impuls, merkezi yönetimin 12 aylık faiz dışı dengesinin GSYH'ye oranının dört çeyrek "
                  "önceki değerinden farkının eksisidir (artı değer genişleme); yapısal denge, faiz dışı dengeden "
                  "yarı esneklik çarpı aynı dört çeyreğin ortalama çıktı açığı düşülerek kurulur ve iki çıktı açığı "
                  "sürümü ile iki esneklik ucunun verdiği dört değerin en küçüğü ile en büyüğü aralık olarak yazılır.",
        "kaynak": ["butce_ceyreklik", "gsyh_ceyreklik (Bölüm 3 çıktı açığı)", "kkm_aylik (dönem işareti)"],
        "varsayim": {"yari_esneklik": list(YARI_ESNEKLIK),
                     "nitelik": "kaynak iddiası, ölçüm değil; bu katman yarı esnekliği yeniden kestirmez",
                     "cikti_acigi": "Bölüm 3: tam örneklem HP ve gerçek zamanlı HP (λ = 1600), dört çeyrek ortalaması"},
        "tek_seferlik": {
            "deprem": {"ilk": str(DEPREM_DONEM[0]), "son": str(DEPREM_DONEM[1]),
                       "not": "06.02.2023 depremi; harcamanın tutarı bu arşivde ayrı kalem değil, Mayıs 2023 "
                              "seçimleriyle aynı yıla düşer. Dönem yalnız işaretlenir.",
                       "n": int(len(dep)), "impuls_ort_puan": _f(dep["impuls"].mean()),
                       "impuls_azami_puan": _f(dep["impuls"].max()),
                       "impuls_azami_ceyrek": str(dep["impuls"].idxmax()) if len(dep) else None},
            "kkm": {"ilk_ay": _iso(kkm.index.min())[:7], "son_ay": _iso(kkm.index.max())[:7],
                    "ilk": str(kk.index.min()) if len(kk) else None, "son": str(kk.index.max()) if len(kk) else None,
                    "not": "Kur korumalı mevduat stokunun bulunduğu aylar; KKM'nin bütçe maliyeti bu arşivde ayrı "
                           "kalem değil.",
                    "n": int(len(kk)), "impuls_ort_puan": _f(kk["impuls"].mean())},
            "diger_ceyrekler_impuls_ort_puan": _f(diger["impuls"].mean()),
            "diger_ceyrekler_n": int(len(diger)),
        },
        "son_durum": satir(son),
        "impuls_azami": {"ceyrek": str(x["impuls"].idxmax()), "puan": _f(x["impuls"].max())},
        "impuls_asgari": {"ceyrek": str(x["impuls"].idxmin()), "puan": _f(x["impuls"].min())},
        "dongusel_pay_son": {
            "alt_puan": _f(df.loc[son, "impuls"] - df.loc[son, "yimp_ust"]),
            "ust_puan": _f(df.loc[son, "impuls"] - df.loc[son, "yimp_alt"]),
            "not": "Ölçülen impuls ile yapısal impuls aralığının farkı: impulsun konjonktüre düşen kısmı."},
        "yillik": yillik,
        "seri": [satir(p) for p in x.index],
    }


# ═══════════════════════════════════════════════════════════════ p5c
def _bilesik_haftalik(r_yuzde: pd.Series) -> pd.Series:
    return ((1 + r_yuzde / 100 / ANKET_HAFTA) ** ANKET_HAFTA - 1) * 100


def _bilesik_gunluk(r_yuzde: pd.Series) -> pd.Series:
    return ((1 + r_yuzde / 100 / 365) ** 365 - 1) * 100


def _patika_tam(r12: pd.Series, r24: pd.Series) -> pd.Series:
    """Sınama: 12'den 24'üncü aya doğrusal patikanın 52 haftada haftalık bileşiği."""
    w = (np.arange(ANKET_HAFTA) + 0.5) / ANKET_HAFTA
    R12, R24 = r12.values[:, None] / 100, r24.values[:, None] / 100
    yol = R12 + (R24 - R12) * w[None, :]
    return pd.Series((np.prod(1 + yol / ANKET_HAFTA, axis=1) - 1) * 100, index=r12.index)


def _politika_gunluk(tk: pd.DatetimeIndex) -> pd.Series:
    f = oo.oku("fonlama_gunluk")["politika"].dropna()
    e = oo.oku("em_politika_aylik")["tur"].dropna()
    e.index = pd.PeriodIndex(e.index, freq="M")
    ay = pd.PeriodIndex(tk, freq="M")
    bis = pd.Series(e.reindex(ay).values, index=tk)
    gun = f.reindex(tk)
    return gun.where(tk >= POLITIKA_GUNLUK_ILK, bis)


def _anket_ay_degeri(d: pd.DataFrame) -> pd.DataFrame:
    """Günlük seriden her ayın anket değeri (20'sinden sonraki ilk gözlem)."""
    x = d[["pka_faiz_12a", "pka_faiz_24a"]].dropna()
    x = x[x.index.day >= 20]
    g = x.groupby(pd.PeriodIndex(x.index, freq="M")).first()
    return g


def _p5c_gunluk(kayma: int = b01.DIBS_ETIKET_ONCU) -> pd.DataFrame:
    """Türkiye iş günü çerçevesi. DİBS sütunları `kayma` iş günü geri alınır:
    etiket t+k'deki değer piyasa günü t'ye yazılır (Bölüm 2'nin tarih sözleşmesi)."""
    tk = b3.tr_takvim()
    d = oo.oku("dibs_egri_gunluk").reindex(tk)
    if kayma:
        dib = d[["f_1y1y", "n3a"]].shift(-kayma)
        d = d.assign(f_1y1y=dib["f_1y1y"], n3a=dib["n3a"])
    fon = oo.oku("fonlama_gunluk").reindex(tk)
    r_ort = (d["pka_faiz_12a"] + d["pka_faiz_24a"]) / 2
    anket = _bilesik_haftalik(r_ort)
    pol = _politika_gunluk(tk)
    out = pd.DataFrame({
        "f_1y1y": d["f_1y1y"], "anket_basit": r_ort, "anket_bilesik": anket,
        "fark_bp": (d["f_1y1y"] - anket) * 100,
        "koridor_bp": (fon["aofm"] - pol) * 100,
        "baz_bp": (d["n3a"] - _bilesik_gunluk(fon["tlref"])) * 100,
        "r12": d["pka_faiz_12a"], "r24": d["pka_faiz_24a"],
    }, index=tk)
    return out[out.index <= oo.CIPA_GUN]


def _aylik(g: pd.DataFrame) -> pd.DataFrame:
    ay = pd.PeriodIndex(g.index, freq="M")
    m = g.groupby(ay).mean()
    sayi = g["fark_bp"].groupby(ay).count()
    return m[sayi.reindex(m.index) >= AYLIK_ASGARI_GUN]


def _ozet(s: pd.Series) -> dict:
    s = s.dropna()
    if not len(s):
        return {"n": 0}
    return {"n": int(len(s)), "ilk": str(s.index.min()), "son": str(s.index.max()),
            "ort": _f(s.mean()), "medyan": _f(s.median()), "asgari": _f(s.min()), "azami": _f(s.max()),
            "asgari_ay": str(s.idxmin()), "azami_ay": str(s.idxmax()), "son_deger": _f(s.iloc[-1])}


def _n3a_tanisi() -> dict:
    """3 aylık düğümün gürültüsü ve konvansiyon tanısı (etiket günü, kaydırmasız)."""
    tk = b3.tr_takvim()
    d = oo.oku("dibs_egri_gunluk")["n3a"].reindex(tk)
    t = oo.oku("fonlama_gunluk")["tlref"].reindex(tk)
    x = pd.DataFrame({"n3a": d, "tlref": t}).dropna()
    dn = x["n3a"].diff() * 100
    dt = x["tlref"].diff() * 100
    j = dn.abs().idxmax()
    w = x.loc["2025-01":"2026-09"]
    return {
        "yontem": "3 aylık düğümün günlük değişim oynaklığı TLREF'inkiyle kıyaslandı; düğümün yıllık bileşik değeri "
                  "TLREF'in hem basit hem bileşiğe çevrilmiş değeriyle karşılaştırıldı.",
        "n": int(len(x)), "ilk": _iso(x.index.min()), "son": _iso(x.index.max()),
        "n3a_gunluk_sd_bp_2024": _f(dn.loc["2024"].std()), "tlref_gunluk_sd_bp_2024": _f(dt.loc["2024"].std()),
        "n3a_gunluk_sd_bp_tum": _f(dn.std()), "tlref_gunluk_sd_bp_tum": _f(dt.std()),
        "en_buyuk_gunluk_degisim_bp": _f(dn.loc[j]), "en_buyuk_gunluk_degisim_gunu": _iso(j),
        "donem_2025_2026": {"n": int(len(w)), "ilk": _iso(w.index.min()), "son": _iso(w.index.max()),
                            "n3a_eksi_tlref_basit_ort_bp": _f((w["n3a"] - w["tlref"]).mean() * 100),
                            "n3a_eksi_tlref_basit_ort_mutlak_bp": _f((w["n3a"] - w["tlref"]).abs().mean() * 100),
                            "n3a_eksi_tlref_bilesik_ort_bp": _f((w["n3a"] - _bilesik_gunluk(w["tlref"])).mean() * 100)},
        "not": "Düğümün bileşik değeri TLREF'in basit değerine bileşiğinden çok daha yakın: ya gerçek bir fiyat farkı "
               "ya kısa düğümün sözleşmesinde bir sorun; bu arşivden ayırt edilemez.",
    }


def p5c() -> dict:
    g = _p5c_gunluk()
    gg = g.dropna(subset=["fark_bp"])
    m = _aylik(g)
    m["fark_arinmis_bp"] = m["fark_bp"] - m["koridor_bp"] - m["baz_bp"]
    fark = m["fark_bp"].dropna()

    # sınama 1: günlük anket ↔ aylık dosya
    d = oo.oku("dibs_egri_gunluk")
    av = _anket_ay_degeri(d)
    ay_dosya = oo.oku("pka_faiz_aylik")
    ay_dosya.index = pd.PeriodIndex(ay_dosya.index, freq="M")
    ortak = av.join(ay_dosya, how="inner", lsuffix="_g", rsuffix="_a")
    esit = ((ortak["pka_faiz_12a_g"] - ortak["pka_faiz_12a_a"]).abs() < 1e-9) & \
           ((ortak["pka_faiz_24a_g"] - ortak["pka_faiz_24a_a"]).abs() < 1e-9)
    gecis = d["pka_faiz_12a"].ne(d["pka_faiz_12a"].shift()) | d["pka_faiz_24a"].ne(d["pka_faiz_24a"].shift())
    gecis = d.index[gecis & d["pka_faiz_12a"].notna() & d["pka_faiz_12a"].shift().notna()]
    gecis_gunu = pd.Series(gecis.day).value_counts().sort_index()

    # sınama 2: yamuk-ortalamanın bileşiği ↔ doğrusal patikanın haftalık bileşiği;
    # (1 + r/52)^52 ↔ DİBS panosunun (1 + r·7/365)^(365/7) çevrimi
    ga = gg.dropna(subset=["r12", "r24"])
    tam = _patika_tam(ga["r12"], ga["r24"])
    yaklasim_fark = (ga["anket_bilesik"] - tam) * 100
    pano = ((1 + ga["anket_basit"] / 100 * 7 / 365) ** (365 / 7) - 1) * 100
    cevrim_fark = (ga["anket_bilesik"] - pano) * 100

    # kirlilik 3: anketin ay etiketi — anket ayın İLK gününden geçerli sayılırsa
    ay_idx = pd.PeriodIndex(gg.index, freq="M")
    alt12 = pd.Series(av["pka_faiz_12a"].reindex(ay_idx).values, index=gg.index)
    alt24 = pd.Series(av["pka_faiz_24a"].reindex(ay_idx).values, index=gg.index)
    fark_alt = (gg["f_1y1y"] - _bilesik_haftalik((alt12 + alt24) / 2)) * 100
    alt_m = fark_alt.groupby(ay_idx).mean().reindex(fark.index)
    hiza_fark = (alt_m - fark).dropna()
    egim_ay = ((av["pka_faiz_24a"] - av["pka_faiz_12a"]) / 12 * 100).abs()

    # DİBS etiket kayması duyarlılığı: kaydırmasız seri
    m0 = _aylik(_p5c_gunluk(kayma=0))
    kayma_fark = (m0["fark_bp"] - m["fark_bp"]).dropna()
    kayma_baz = (m0["baz_bp"] - m["baz_bp"]).dropna()

    son_gun = gg.index.max()
    sg = g.loc[son_gun]
    kir = {}
    for ad, kol in (("koridor_farki", "koridor_bp"), ("dibs_tlref_bazi", "baz_bp")):
        s = m[kol].dropna()
        kir[ad] = {**_ozet(s), "fark_ile_korelasyon": _f(pd.concat([s, fark], axis=1).dropna().corr().iloc[0, 1])}
    kir["koridor_farki"]["yontem"] = ("TCMB ağırlıklı ortalama fonlama maliyetinin politika faizinden farkının "
                                      "aylık ortalaması (baz puan); 14.09.2018 öncesinde politika faizi BIS'in ay "
                                      "sonu değeridir.")
    kir["koridor_farki"]["not"] = ("2018-09 öncesinin karar aylarında ay sonu politika faizi ay ortalaması fonlama "
                                   "maliyetiyle kıyaslanır: 2014-01'in eksi değeri 28.01.2014 artırımının ay sonuna "
                                   "yazılmasından gelir.")
    kir["dibs_tlref_bazi"]["yontem"] = ("3 aylık sıfır kuponlu DİBS getirisi ile günlük bileşiğe çevrilmiş TLREF "
                                        "arasındaki farkın aylık ortalaması (baz puan; DİBS panosundaki 3 ay − TLREF "
                                        "taşımasıyla aynı tanım); TLREF 28.12.2018'de başlar.")
    kir["dibs_tlref_bazi"]["dugum_tanisi"] = _n3a_tanisi()
    kir["anket_ay_etiketi"] = {
        "yontem": "Anketin ayın 20'sinden değil ilk gününden geçerli sayıldığı karşı hizalamanın aylık farka etkisi "
                  "ile 12 ve 24 ay beklentisi arasındaki eğimin bir aylık kaymada patikayı oynattığı miktar.",
        "karsi_hiza_n": int(len(hiza_fark)),
        "karsi_hiza_ort_mutlak_bp": _f(hiza_fark.abs().mean()),
        "karsi_hiza_azami_mutlak_bp": _f(hiza_fark.abs().max()),
        "karsi_hiza_azami_ay": str(hiza_fark.abs().idxmax()) if len(hiza_fark) else None,
        "bir_ay_kayma_medyan_bp": _f(egim_ay.median()), "bir_ay_kayma_azami_bp": _f(egim_ay.max()),
        "bir_ay_kayma_azami_ay": str(egim_ay.idxmax()),
    }
    donem = {}
    for ad, a, b in b01.DONEMLER_TR:
        x = m.loc[pd.Period(a[:7], "M"):pd.Period(b[:7], "M")]
        if not len(x):
            continue
        donem[ad] = {"n": int(x["fark_bp"].notna().sum()), "ilk": str(x.index.min()), "son": str(x.index.max()),
                     "fark_ort_bp": _f(x["fark_bp"].mean()), "fark_medyan_bp": _f(x["fark_bp"].median()),
                     "koridor_ort_bp": _f(x["koridor_bp"].mean()), "baz_ort_bp": _f(x["baz_bp"].mean()),
                     "baz_n": int(x["baz_bp"].notna().sum())}
    return {
        "n": int(len(fark)), "ilk": str(fark.index.min()), "son": str(fark.index.max()),
        "n_gun": int(len(gg)), "ilk_gun": _iso(gg.index.min()), "son_gun": _iso(son_gun),
        "yontem": "DİBS eğrisinden 1 yıl sonrası 1 yıllık forward (yıllık bileşik) ile Piyasa Katılımcıları "
                  "Anketi'nin 12 ve 24 ay sonrası politika faizi beklentilerinin ortalaması (yamuk yaklaşımı; bir "
                  "hafta vadeli repo basit faiz olduğu için (1 + r/52)^52 − 1 ile yıllık bileşiğe çevrildi) "
                  "arasındaki fark, DİBS etiketi iki iş günü geri alınarak Türkiye iş günlerinde günlük alındı ve "
                  "aylık ortalamaya çevrildi.",
        "kaynak": ["dibs_egri_gunluk", "pka_faiz_aylik (sınama)", "fonlama_gunluk", "em_politika_aylik"],
        "fark": _ozet(fark),
        "donem": donem,
        "fark_arinmis": {**_ozet(m["fark_arinmis_bp"]),
                         "not": "Duyarlılık, ölçüm değil: koridor farkı ve 3 aylık düğümdeki DİBS–TLREF bazı 1y1y "
                                "noktasında da aynı büyüklükte kalıcı varsayılarak düşüldü; bu varsayım ölçülmedi. "
                                "2018-12 öncesinde baz ölçülmediği için seri boştur."},
        "son_gun_degerleri": {"tarih": _iso(son_gun), "f_1y1y": _f(sg["f_1y1y"]),
                              "anket_12a": _f(sg["r12"]), "anket_24a": _f(sg["r24"]),
                              "anket_basit_ort": _f(sg["anket_basit"]), "anket_bilesik": _f(sg["anket_bilesik"]),
                              "fark_bp": _f(sg["fark_bp"]), "koridor_bp": _f(sg["koridor_bp"]),
                              "baz_bp": _f(sg["baz_bp"]),
                              "not": "Piyasa günü; DİBS değeri iki iş günü sonraki etiketten gelir."},
        "kirlilik": kir,
        "sinama": {
            "gunluk_anket_aylik_dosya": {"ortak_ay": int(len(ortak)), "birebir": int(esit.sum()),
                                         "ilk": str(ortak.index.min()), "son": str(ortak.index.max())},
            "anket_gecis_gunu_dagilimi": {str(k): int(v) for k, v in gecis_gunu.items()},
            "yamuk_ve_dogrusal_patika_azami_fark_bp": _f(yaklasim_fark.abs().max()),
            "yamuk_ve_dogrusal_patika_ort_fark_bp": _f(yaklasim_fark.mean()),
            "haftalik_cevrim_52_ve_7_365_azami_fark_bp": _f(cevrim_fark.abs().max()),
            "dibs_etiket_kaymasi_is_gunu": int(b01.DIBS_ETIKET_ONCU),
            "kaydirmasiz_aylik_fark_azami_bp": _f(kayma_fark.abs().max()),
            "kaydirmasiz_aylik_fark_ort_mutlak_bp": _f(kayma_fark.abs().mean()),
            "kaydirmasiz_aylik_baz_azami_bp": _f(kayma_baz.abs().max()),
        },
    }


def sekil_08() -> dict:
    m = _aylik(_p5c_gunluk()).dropna(subset=["fark_bp"])
    return {
        "n": int(len(m)), "ilk": str(m.index.min()), "son": str(m.index.max()),
        "yontem": "Türkiye beklenti dışı farkı (1y1y forward eksi anket patikası, ikisi de yıllık bileşik) ve iki "
                  "kirlilik kalemi (koridor farkı, DİBS–TLREF bazı), aylık ortalama, baz puan.",
        "kaynak": ["dibs_egri_gunluk", "fonlama_gunluk", "em_politika_aylik"],
        "ay": [str(p) for p in m.index],
        "fark_bp": [_f(v) for v in m["fark_bp"]],
        "f_1y1y": [_f(v) for v in m["f_1y1y"]],
        "anket_bilesik": [_f(v) for v in m["anket_bilesik"]],
        "koridor_bp": [_f(v) for v in m["koridor_bp"]],
        "baz_bp": [_f(v) for v in m["baz_bp"]],
        "yonetilen_kur_donemi": [str(b01.YONETILEN[0].to_period("M")), str(b01.YONETILEN[1].to_period("M"))],
    }


# ═══════════════════════════════════════════════════════════════ giriş
def olc() -> dict:
    return oo.yuvarla({
        "p5a": p5a(),
        "p5b": p5b(),
        "p5c": p5c(),
        "sekil_07": sekil_07(),
        "sekil_08": sekil_08(),
    }, 4)


if __name__ == "__main__":
    import json
    import time
    t0 = time.time()
    d = olc()
    print(json.dumps(d, ensure_ascii=False)[:4000])
    print(f"süre {time.time() - t0:.1f} sn")
